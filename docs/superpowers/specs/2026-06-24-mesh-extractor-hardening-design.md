# Mesh Extractor Hardening (Slice #2) — Design

**Date:** 2026-06-24
**Branch:** `feat/mesh-to-tree-hardening`
**Status:** approved (brainstorm), pending spec review
**Slice:** #2 of the mesh→tree hardening + agent-reference branch (see
`docs/superpowers/handoffs/2026-06-24-mesh-to-tree-hardening-and-agent-reference.md`).
Slice #1 (agent-reference layer) follows on the same branch.

---

## 1. Purpose

Make the deterministic mesh→tree extractor *provably* trustworthy so Slice #1 can
build the agent-reference layer on metrics it can rely on. This slice adds **no
runtime logic** — it corrects false documentation, pins the (now-verified)
recalibration against regression with fast tests, and removes stale test data and
stale "expected-fail" claims.

## 2. Background & the evidence that reframed the scope

The handoff hypothesized Slice #2 would *retire* two interim-debt constants in
`auto_mesh_to_metric_tree` that the earlier OOD problem (PR #8) had forced:
`SEARCH_K = 4` (try 4 candidates, not 2) and `PRUNE_GRID` capped at 0.60. The
premise was that PR #9's gate recalibration (added a `mesh_like` corpus family;
fixtures moved OOD→in-distribution) made them unnecessary.

A live-path verification on 2026-06-24 ran the **real** `auto_mesh_to_metric_tree`
(real gate + real TreeMaker compiler, seed-pinned, deterministic) against all 5
committed fixtures. Findings:

| fixture | in-distribution? | compiles? | chosen (vr, prune) | leaves | rank-depth to first compile |
|---|---|---|---|---|---|
| quadruped | yes (all `feasible`) | yes | (96, 0.55) | 5 | **4th** (ranks 1–3 are 6-leaf, fail) |
| humanoid | yes | yes | (96, 0.30) | 5 | **4th** (ranks 1–3 fail) |
| fish | yes | yes | (64, 0.40) | 6 | 1st at vr=64 (after vr=96 escalation) |
| bird | yes | yes | (96, 0.25) | 4 | 1st |
| insect | yes | yes | (96, 0.55) | 6 | 1st |

Two facts reframe the slice:

1. **PR #9's recalibration holds on the live path.** Zero `compile_anyway`/OOD
   verdicts; every fixture reads in-distribution AND compiles to FOLD — including
   `insect`, which memory/handoff/POC-doc still call expected-fail.
2. **The debt is NOT retire-able.** The gate is no longer OOD, but its
   in-distribution `p_pack` still mis-ranks by leaf count: it ranks unpackable
   6-leaf trees (p_pack 0.66–0.71) **above** the packable 5-leaf tree (lower
   p_pack), so the packable candidate is **rank-4** for quadruped and humanoid.
   Dropping `SEARCH_K` to 2 would drop both. The constants must stay; what is
   actually wrong is (a) the comments justifying them cite OOD, which no longer
   applies, and (b) PR #9 pinned the recalibration against **stored snapshots**,
   not the live extraction path.

Additional finding: the stored snapshots in
`tests/fixtures/mesh_validation_trees.json` have **drifted** from live extraction.
At the documented constants, 4/5 fixtures match the live tree exactly;
**humanoid** does not (same topology and bilateral pairs, but ~3% different edge
lengths and a different edge normalized to the 0.40 target) — proving the
snapshots were generated from a now-superseded code/constant state and have no
committed provenance tying them to the live path.

## 3. Scope

### In scope
1. **Correct the false debt-justification comments** on `SEARCH_K` and
   `PRUNE_GRID` in `mesh_to_tree.py` to state the real, measured reason.
2. **Add a fast live-path in-distribution pin** — a regression guard that each
   fixture, through live extraction + `gate.predict`, reads `ood is False` and
   `verdict != "infeasible"`.
3. **Regenerate `mesh_validation_trees.json` from a committed generator** and add
   a test asserting the snapshot equals live extraction at documented constants
   (fixes humanoid drift; prevents future drift).
4. **Reclassify `insect` as expected-pass** in the memory, the POC design doc, and
   the handoff (the code already treats it as a pass).

### Out of scope (explicitly)
- Changing `SEARCH_K`, the `PRUNE_GRID` cap, or `VOXEL_GRID` — evidence says they
  are load-bearing.
- Touching the gate model, corpus, or `rank()` to fix the p_pack mis-ranking. That
  is the deeper root cause and is deferred (see §7). The user chose the
  "Document & pin" scope over "Also fix gate ranking".
- Adding any new compile-based test (the existing slow E2E already pins
  `confirmed=True`).

## 4. The documented constants table

Single source of truth, shared by the generator and both new tests. Taken from the
2026-06-24 live verification run.

| fixture | voxel_res | prune_fraction | leaves | pairs |
|---|---|---|---|---|
| quadruped | 96 | 0.55 | 5 | 1 |
| humanoid | 96 | 0.30 | 5 | 2 |
| fish | 64 | 0.40 | 6 | 1 |
| bird | 96 | 0.25 | 4 | 1 |
| insect | 96 | 0.55 | 6 | 3 |

These are the `(voxel_res, prune)` pairs that `auto_mesh_to_metric_tree` actually
selects on the live path; they are NOT the hand-tuned `_DEMO_BODY_PLANS` constants
(which differ for fish/bird). Using the auto-selected pair keeps the snapshot tied
to what the production search produces.

## 5. Architecture / files

This slice adds no runtime code paths. Changes are comments, regenerated data, a
generator script, and tests.

- `mcp_harness/mesh_to_tree.py` (lines 31–39) — rewrite the `PRUNE_GRID` and
  `SEARCH_K` justification comments. Real rationale: the in-distribution gate's
  p_pack mis-ranks by leaf count (ranks 6-leaf above the packable 5-leaf tree), so
  the packable candidate is rank-4 for quadruped/humanoid (measured 2026-06-24);
  `K=4` reaches it and `K=2` would drop both. `PRUNE_GRID` stays capped at 0.60
  because 0.70 yields over-compact trees that would win on p_pack and displace the
  faithful flap count.
- `mcp_harness/tests/fixtures/gen_mesh_validation_trees.py` (new) — regenerates
  `mesh_validation_trees.json` by calling `mesh_to_metric_tree(fixture, vr, prune)`
  over the §4 constants table. Header comment records the table for reproducibility.
- `mcp_harness/tests/fixtures/mesh_validation_trees.json` (regenerated) —
  overwritten from the generator (humanoid corrected; others unchanged).
- `mcp_harness/tests/test_gate_mesh_region.py` (modify) — add
  `test_snapshots_match_live_extraction`: for each fixture, assert
  `mesh_to_metric_tree(fixture, vr, prune) == snapshot` at the §4 constants. Fast
  (extraction only). Existing two tests unchanged.
- `mcp_harness/tests/test_mesh_recalibration_live.py` (new) —
  `test_fixtures_in_distribution_on_live_path`: per fixture, run extraction +
  `gate.predict`, assert `ood is False` and `verdict != "infeasible"`. Fast (no
  compile). Trains the gate from the committed corpus the same way the existing
  region test does, so it runs on a fresh checkout.

### Doc/memory updates
- `docs/superpowers/specs/2026-06-16-mesh-to-tree-poc-design.md` — update the
  insect expected-fail/0%-packable claim to note auto-selection confirms it at
  (96, 0.55), 6 leaves / 3 pairs.
- Memory `mesh-auto-constant-selection.md` + `MEMORY.md` hook — correct the
  "all 5 real meshes OOD → gate decorative" claim: as of 2026-06-24 the live path
  reads all 5 in-distribution and confirms all 5 incl. insect; SEARCH_K=4 / PRUNE
  cap 0.60 remain, not as OOD debt but because the in-distribution gate still
  mis-ranks by leaf count.
- The handoff doc's Slice #2 "expected-fail insect" and "missing live-path test"
  assumptions get a short correction note (both refuted by evidence; the live
  confirm test `test_auto_selection_confirms_each_body_plan` already exists).

### Scratch cleanup
- Delete the untracked investigation harness `mcp_harness/verify_recalibration.py`
  and `mcp_harness/verify_recalibration_out.json` before finishing the branch.

## 6. Testing

- All new tests are extraction+gate only (seconds); no new compile cost. The
  existing slow compile-based E2E (`test_auto_selection_confirms_each_body_plan`)
  already pins `confirmed=True` for all 5 fixtures incl. insect.
- Determinism: extraction is seed-pinned (`SKELETOR_SEED = 0`); the snapshot
  equality test relies on this.
- Success: full suite green (was 163 passed, 1 skipped; expect +2 tests), snapshot
  regenerated with provenance, comments corrected, insect documented as a pass.

## 7. Known limitation (deferred)

The gate's in-distribution `p_pack` does not track ground-truth packability by leaf
count — that is the reason `SEARCH_K = 4` is still required. This slice documents
the limitation rather than fixing it. It is carried into Slice #1's report surface
as a caveat and is a candidate future sub-project (retrain/recalibrate the gate's
ranking so the packable candidate ranks first and the search can shrink).

## 8. Constraints carried over

- Tests in `mcp_harness/tests/`, run from inside `mcp_harness/` via
  `.venv/bin/python -m pytest`.
- No new heavy dependencies.
- Fail loud with specific messages.
- TreeMaker/Oriedita engine behavior is fixed and partly inherent — fixes are
  extraction/agent-side, never engine-side.
