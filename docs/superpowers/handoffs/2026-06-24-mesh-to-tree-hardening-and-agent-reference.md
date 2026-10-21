# Handoff: 3D Model → Tree — Harden Extractor (#2) then Agent-Reference Layer (#1)

**Date:** 2026-06-24
**Branch:** `feat/mesh-to-tree-hardening` (both slices land here, sequentially)
**Owner:** picks up where PR #11 (mesh acquisition, Stage [A]) left off.

> **For whoever executes this:** Each slice is its own brainstorm → spec → plan →
> subagent-driven-development cycle. Do NOT skip brainstorming — both slices have
> open design decisions called out below. Do Slice #2 fully (merge-ready) before
> starting Slice #1, since #1 builds on a trustworthy extractor.

---

## Where this fits

Full pipeline:

```
query → [A] acquire mesh ──────────────── DONE  (PR #11, mcp_harness/mesh_acquire.py)
      → [user preview] ────────────────── DEFERRED (needs frontend tier; NOT in this branch)
      → [B] extract skeleton ──────────── BUILT (mesh_to_tree.extract_skeleton)
      → [C] skeleton → Metric Tree ────── BUILT (simplify_to_tree → detect_symmetry → to_metric_tree)
      → [agent reviews/corrects anatomy] ─ SLICE #1 (this branch — the gap)
      → [D] compile → lint → fold ─────── BUILT
```

This branch covers **#2 (harden B+C so the metrics are trustworthy)** then
**#1 (agent-reference layer so the agent can apply semantics on top)**.

**Founding invariant (do not break):** the AI only ever edits the abstract Metric
Tree (nodes/edges/symmetry), never `.fold` geometry. Slice #1 must route every
agent correction through the existing tree-drafting MCP tools.

**Architecture principle for #1:** *deterministic code supplies metrics
(proportions, topology, symmetry); the agent supplies semantics (what's a head, a
spurious twig, the right flap count).*

---

## Key files

- `mcp_harness/mesh_to_tree.py` — the deterministic extractor (B+C) + the
  closed-loop `auto_mesh_to_metric_tree` search. **Primary file for #2.**
- `mcp_harness/mesh_acquire.py` — Stage [A]; `query_to_metric_tree` is the
  end-to-end entry that chains [A]→B+C.
- `mcp_harness/feasibility/` — the gate (`gate.py`), training (`train_model.py`),
  corpora (`corpus_wide.jsonl` is the live one, 2600 rows after PR #9).
- `mcp_harness/agent_loop.py` — the Tier 2 orchestrator. **Primary integration
  point for #1** (it currently does NOT call mesh_to_tree at all).
- `mcp_harness/fixtures/*.glb` — the 5 real meshes (quadruped/bird/humanoid/
  fish/insect), the test yardstick.
- Relevant prior specs: `docs/superpowers/specs/2026-06-16-mesh-to-tree-poc-design.md`,
  `2026-06-23-auto-constant-selection-design.md`,
  `2026-06-24-gate-mesh-region-recalibration-design.md`,
  `2026-06-20-feasibility-gate-agent-wiring-design.md`.

---

## SLICE #2 — Harden the deterministic extractor (do first)

**Goal:** Make the metrics the agent will later trust actually trustworthy, and
retire the interim debt that the (now-fixed) OOD problem forced.

**Background / what changed:** PR #8 found all 5 real meshes read **OOD**, making
the gate "decorative" — so two workarounds were added in
`auto_mesh_to_metric_tree`:
- `SEARCH_K = 4` (mesh_to_tree.py:36) — try 4 candidates not 2, because the OOD
  gate's `p_pack` ranking couldn't be trusted.
- `PRUNE_GRID` capped at 0.60 (mesh_to_tree.py:31, 0.70 omitted) — because the
  uncalibrated gate ranked over-compact trees above faithful ones.

PR #9 then recalibrated the gate (added a `mesh_like` corpus family; commit
`03cc183` "mesh fixtures now in-distribution") — fixtures moved OOD→feasible. **But
the two workarounds above were never reverted.**

**Scope:**
1. **Verify** PR #9's recalibration end-to-end on the real meshes through the
   *actual* path (`auto_mesh_to_metric_tree`, and ideally `query_to_metric_tree`
   with `FakeMeshProvider`/fixtures): are the 5 fixtures now in-distribution and
   does the gate's `p_pack` ranking pick the faithful tree first?
2. **Retire the debt the recalibration unblocked**, guarded by tests:
   - `SEARCH_K` 4 → 2 (if rank-1 candidate now compiles for the fixtures).
   - Restore `PRUNE_GRID` to include 0.70 (if the calibrated gate no longer
     over-ranks compact trees).
   Keep whichever the evidence says must stay; document why in the spec.
3. **Pin the result:** a fixture-level test asserting each body plan extracts a
   plausible leaf count AND that the gate now ranks it feasible/in-distribution,
   so a future gate change can't silently regress it back to OOD.

**Open decisions for the brainstorm (resolve before coding):**
- If verification shows some fixtures are STILL OOD despite PR #9, branch:
  (a) extend the `mesh_like` corpus further, (b) adjust extraction so trees land
  in-distribution, or (c) accept residual OOD and make `rank()` robust to it.
  Pick based on the measured gap — don't assume.
- Whether `insect` stays an expected-fail (it packs 0% under jitter per the POC
  design — hardening is NOT expected to fix the inherent TreeMaker packing wall;
  see memory `polys-multiple-ibps-is-inherent`). Keep it pinned as expected.
- `VOXEL_GRID` order/escalation — leave alone unless verification implicates it.

**Success criteria:** debt constants reduced to their principled values (or the
residual justified in writing), fixtures pinned in-distribution, full suite green.

> **Correction (2026-06-24 live verification):** two assumptions above were
> refuted by evidence. (1) The debt is NOT retire-able: fixtures are now
> in-distribution AND compile, but the in-distribution gate still mis-ranks by
> leaf count, so SEARCH_K=4 stays load-bearing (quadruped/humanoid reach the
> packable tree only at rank-4); the PRUNE 0.60 cap stays too. The slice instead
> corrects the now-false justification comments and pins the behavior. (2) The
> live-path confirm test was not missing — test_auto_selection_confirms_each_body_plan
> already pins confirmed=True for all five fixtures incl. insect; insect is
> expected-PASS, not expected-fail. Implemented per
> docs/superpowers/specs/2026-06-24-mesh-extractor-hardening-design.md.

---

## SLICE #1 — Agent-reference layer (do second)

**Goal:** Let the agent use the generated 3D model + the deterministic extraction
as a *reference*, applying semantic corrections the geometry can't make — the
"agent uses the 3D model as a reference when making trees" half of the original
intent.

**Planned shape:**
```
generated .glb
  → mesh_to_tree produces a CANDIDATE Metric Tree + a structured REPORT
      (leaf count, hub/junction structure, symmetry pairs, the
       voxel_res/prune_fraction trace, gate verdict)
  → agent inspects { candidate tree + reference + report }
  → agent issues SEMANTIC edits via existing tree-drafting MCP tools
      (add_node / add_edge / set_symmetry — Metric Tree is the only editable surface)
  → existing compile → perturb → lint → fold path validates (unchanged)
```

**Scope (likely):**
- A "candidate + report" surface from `mesh_to_tree` the agent can consume
  (the `MeshTreeResult.trace` already carries much of this — formalize it).
- Wire mesh→tree into `agent_loop.py` as a real tool/entry (today nothing in the
  agent calls it — only `experiment_tune.py` and `mesh_acquire.py` do).
- A prompt/flow teaching the agent the semantics-vs-metrics split: trust the
  extracted proportions/symmetry; only correct anatomy (naming, flap count,
  spurious twigs).

**Open decisions for the brainstorm (resolve before coding):**
- **What "reference" does the agent see?** The candidate tree + textual report
  only, or also a rendered image of the mesh (multimodal)? Image needs a render
  step; this provider/backend currently runs on Groq llama (text-only) because the
  Anthropic key is out of credits (see memory `pluggable-llm-backend`) — a vision
  step may be blocked on backend/credits. Decide the fidelity bar.
- **MCP tool surface:** reuse `add_node`/`add_edge`/`set_symmetry` as-is, or add a
  higher-level "adjust_candidate_tree" tool? Prefer reuse (YAGNI) unless the
  brainstorm finds a real gap.
- **Evaluation:** how do we prove the agent *improved* the tree vs. just churned
  it? Need a yardstick (e.g., the hand-made body-plan templates in agent_loop.py;
  see memory `body-plan-templates-and-node-order`).
- **Guardrails:** prevent the agent from undoing trustworthy metrics (e.g.
  rescaling proportions). The semantics/metrics boundary needs enforcement, not
  just prompting.

**Success criteria:** agent takes a generated mesh → candidate tree → applies ≥1
correct semantic correction → compiles to a foldable base, demonstrated live
(smoke trace) on at least one body plan.

---

## Execution order & branch strategy

1. Brainstorm Slice #2 → spec → plan → SDD → review. Keep committing to
   `feat/mesh-to-tree-hardening`.
2. Only when #2 is merge-ready, brainstorm Slice #1 → spec → plan → SDD → review,
   same branch.
3. Finish the branch (PR) covering both slices. (If #1's scope balloons during its
   brainstorm, consider splitting it to its own branch then — flag to the user.)

Each slice gets its own dated spec in `docs/superpowers/specs/` and plan in
`docs/superpowers/plans/`, per project convention.

## Constraints carried over (apply to both slices)
- Tests in `mcp_harness/tests/`, run from inside `mcp_harness/` via
  `.venv/bin/python -m pytest`. Full suite currently 163 passed, 1 skipped.
- No new heavy dependencies without justification.
- Fail loud with specific messages; defensive on the serve path.
- TreeMaker/Oriedita engine behavior is fixed and partly inherent (hull-vs-square
  FAIL-LINT and POLYS_MULTIPLE_IBPS are expected, not bugs) — fixes are agent/
  extraction-side, never engine-side.
