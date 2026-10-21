# Agent-Reference Layer (Slice #1) — Design

**Date:** 2026-06-24
**Branch:** `feat/mesh-to-tree-hardening` (Slice #1 follows the now-complete Slice #2)
**Status:** approved (brainstorm), pending spec review
**Slice:** #1 of the mesh→tree hardening + agent-reference branch (see
`docs/superpowers/handoffs/2026-06-24-mesh-to-tree-hardening-and-agent-reference.md`).

---

## 1. Purpose

Let the AI agent use a generated 3-D model of the requested subject as a *reference*
when drafting the Metric Tree — the "the agent uses the 3-D model it generated as a
reference when making trees" half of the original intent. The deterministic
extractor supplies **metrics** (measured proportions, topology, bilateral
symmetry); the agent supplies **semantics** (what is a head, the right flap count,
which twigs are spurious). End to end: user query → agent acquires a generated mesh
→ extracts a candidate tree + textual report → applies semantic corrections →
compiles and lints through the existing path.

Founding invariant (unchanged): the agent only ever edits the abstract Metric Tree
(nodes/edges/symmetry), never `.fold` geometry.

## 2. Background

The compile→gate→lint half is built and unchanged. The agent
(`mcp_harness/agent_loop.py`) is an interactive REPL that, today, drafts a whole
tree from hand-made KNOWN-GOOD body-plan templates baked into the system prompt and
submits it via `draft_and_compile_full_base(tree_nodes, symmetric_pairs, ...)`,
gated by `predict_tree_feasibility` and linted by `validate_flat_foldability`. The
actual tool surface is whole-tree drafting (NOT incremental add_node/add_edge — the
handoff's wording was conceptual).

Nothing in `agent_loop.py`/`server.py` calls `mesh_to_tree` today. The mesh→tree
extractor (`auto_mesh_to_metric_tree`) and the query→mesh acquisition front
(`mesh_acquire.query_to_metric_tree`, PR #11) exist but have no live caller.

**Decisions taken during brainstorming:**
- **Mesh source:** full query→mesh→tree. PR #11 (`feat/mesh-acquisition`) is merged
  into this branch as a prerequisite so `mesh_acquire.py` is present.
- **Candidate vs templates:** the mesh-derived candidate is the PRIMARY starting
  point; templates are demoted to fallback/rescue. (Long-term intent: templates
  disappear once mesh generation is the real source — out of scope this slice.)
- **Reference fidelity:** text-only. The backend runs Groq llama (text-only; the
  Anthropic key is out of credits) and there is no render step, so a multimodal/
  vision reference is out of scope. The agent's reference is the candidate tree +
  a textual report.
- **Test/demo provider:** offline `FakeMeshProvider` by default, extended with a
  keyword→fixture mapping so the offline smoke is query-specific and free; real
  Meshy stays available behind `MESHY_API_KEY`.
- **Integration shape:** a single MCP tool (`reference_tree_from_query`) + system
  prompt redesign (chosen over two-tool or pre-loop-injection alternatives).

## 3. Architecture & components

Data flow:

```
user query → reference_tree_from_query(prompt)        [new MCP tool, server.py]
   → mesh_acquire.query_to_metric_tree(prompt, provider=<env>)
        [acquire generated mesh → auto_mesh_to_metric_tree]
   → MeshTreeResult (candidate nodes/pairs + gate verdict + trace + confirmed)
   → mesh_report.format_reference_report(...)   → text report returned to agent
agent reviews report → applies SEMANTIC edits → predict_tree_feasibility
   → draft_and_compile_full_base → validate_flat_foldability    [unchanged]
```

The compile/gate/lint half is untouched. This slice adds the front
(mesh→candidate→report) and rewrites the prompt around it.

### Prerequisite — merge PR #11
Merge `feat/mesh-acquisition` into `feat/mesh-to-tree-hardening`. Clean merge: PR #11
added a standalone module + tests; this branch only changed `mesh_to_tree.py`
comments and test files, so no overlap. The combined suite (this branch's 155 +
PR #11's tests) must be green before any Slice #1 code.

### Components

- `mcp_harness/mesh_acquire.py` — arrives via the merge; gains a `FakeMeshProvider`
  prompt→fixture mapping (§6).
- `mcp_harness/mesh_report.py` (new, small) — a pure function
  `format_reference_report(result: MeshTreeResult, *, prompt: str, mesh_path: str) -> str`.
  No engine, no I/O — fully unit-testable.
- `mcp_harness/server.py` — new MCP tool `reference_tree_from_query(prompt: str) -> str`.
- `mcp_harness/agent_loop.py` — `SYSTEM_PROMPT` rewrite (candidate-primary flow,
  templates demoted, guardrails).

## 4. The tool and the report

### `reference_tree_from_query(prompt: str) -> str` (server.py)
Defensive, like the other tools (returns `"ERROR: ..."` strings, never raises across
the MCP boundary):
1. `result = mesh_acquire.query_to_metric_tree(prompt, provider_name=os.environ.get("MESH_PROVIDER", "fake"))`.
   The agent-tool default provider is `fake` (offline, no cost); set
   `MESH_PROVIDER=meshy` for real generation. (`query_to_metric_tree` returns the
   mesh path alongside the `MeshTreeResult`; if it does not today, thread the cached
   path through so the report can cite provenance.)
2. `report = mesh_report.format_reference_report(result, prompt=prompt, mesh_path=<path>)`.
3. Return `report`; any exception → `"ERROR: reference extraction failed: <msg>"`.

### `format_reference_report(...) -> str` (mesh_report.py)
Plain text, containing:
- **Candidate tree** — the exact `tree_nodes` JSON and `symmetric_pairs`, ready to
  pass to `draft_and_compile_full_base` verbatim or after edits.
- **Measured metrics** — leaf count; hub/junction structure (root's children =
  hubs, children-per-hub); the bilateral `symmetric_pairs`; the longest-edge
  normalization. Framed as "measured from the reference mesh — trust these
  proportions, topology, and symmetry."
- **Search provenance** — chosen `voxel_res`/`prune_fraction`, gate verdict +
  `p_pack` + `ood`, the `confirmed` flag (did it compile to FOLD during search?),
  and the mesh path.
- **Semantic-correction guidance** — an explicit short list of what the agent MAY
  change (node naming/anatomy, flap count: drop a spurious twig / flag a missing
  limb) and MUST NOT change (rescale proportions, re-invent symmetry).
- If `confirmed=False`: a note that the extraction is best-effort and may need a
  semantic/topology fix or a fallback to a template.

`query_to_metric_tree` already chains acquire→`auto_mesh_to_metric_tree`, so the
tool is a thin wrapper + formatting.

## 5. System prompt redesign (agent_loop.py)

Surgical reorder; the gate/compile/lint machinery is unchanged.

- **New top section "START FROM THE REFERENCE MESH":** for any creature/subject
  request the agent's FIRST action is `reference_tree_from_query(<request>)`; it
  then starts from the returned candidate `tree_nodes`/`symmetric_pairs`. The
  agent's job is **semantic correction only** — interpret/name anatomy, fix flap
  count (drop a spurious twig; flag a clearly-missing limb), confirm symmetry
  pairing reads correctly — then run the existing
  `predict_tree_feasibility` → `draft_and_compile_full_base` →
  `validate_flat_foldability` path on the (possibly edited) candidate.
- **Guardrails:** trust the measured metrics — do not rescale proportions or
  re-invent symmetry to "make it pack." Pre-compile length tweaks remain allowed
  ONLY at the gate's `infeasible` stage (as today); post-compile errors remain a
  TOPOLOGY signal (as today).
- **Templates demoted to fallback:** kept in the prompt but used only when (a)
  `reference_tree_from_query` errors or returns an unusable `confirmed=False`
  candidate, or (b) the candidate exhausts the compile budget and needs a
  known-good structure to rescue it. The five packing rules remain as sanity
  checks applied to the candidate.

## 6. FakeMeshProvider prompt→fixture mapping (mesh_acquire.py)

Extend `FakeMeshProvider` with an ordered, case-insensitive substring table mapping
keywords to committed fixtures:
- `insect|bug|beetle|spider|ant → insect.glb`
- `bird|eagle|owl|sparrow → bird.glb`
- `fish|shark|trout → fish.glb`
- `human|person|humanoid|man|woman → humanoid.glb`
- default → `quadruped.glb`

Deterministic per prompt, so PR #11's `cache_key = (provider_name, prompt)` stays
correct. Backwards-compatible: unmatched prompts still yield `quadruped.glb`. If any
existing PR #11 FakeMeshProvider test asserts quadruped for a prompt that now maps
elsewhere, update that test.

## 7. Testing

**Offline (no engine, no network, no LLM):**
- `format_reference_report` over hand-built `MeshTreeResult`s (both `confirmed=True`
  and `confirmed=False`): assert the report contains the candidate nodes/pairs, leaf
  count, hub structure, symmetry pairs, gate verdict, the `confirmed` note, and the
  semantic-correction guidance.
- `FakeMeshProvider` mapping: each keyword class resolves to the right fixture;
  default → quadruped; deterministic; cache-key stable.
- `reference_tree_from_query`: with `query_to_metric_tree` stubbed (injected
  provider + stub gate/compile_fn), assert it returns the formatted report and that
  a raised exception becomes `"ERROR: ..."`.

**Live smoke (opt-in, mirrors the existing agent smoke):** a query like
`"design a beetle"` → Fake(mapped)→insect mesh → candidate → agent applies ≥1
semantic correction → `draft_and_compile_full_base` → `validate_flat_foldability` =
Pass, on ≥1 body plan. Skips without LLM creds. A second opt-in smoke behind
`MESHY_API_KEY` exercises real generation.

## 8. Error handling

- The tool is defensive: acquisition/extraction failure → `"ERROR: ..."` (the
  agent treats `ERROR:` as a recoverable signal and falls back to a template).
- `confirmed=False` is NOT an error: the report flags best-effort; the agent
  proceeds or falls back.
- Defensive on the serve path, matching the other `server.py` tools.

## 9. Success criteria

1. **Mechanism (offline, must-pass):** the tool returns a correct candidate +
   report; the mapping works; full suite green.
2. **Behavior (live smoke):** the agent takes query→candidate→≥1 correct semantic
   correction→foldable base→lint Pass on ≥1 body plan. Honest caveat — llama is the
   weak link; if it cannot reliably perform the semantic step, that is recorded as a
   finding, but criterion 1 still stands.

## 10. Out of scope

- Removing templates entirely (kept as fallback this slice).
- Multimodal/vision reference (text-only, forced by backend/credits/no-render).
- Any frontend/preview UI (no frontend tier exists yet).
- Improving the gate's in-distribution ranking (the Slice #2 deferred limitation).

## 11. Constraints carried over

- Tests in `mcp_harness/tests/`, run from inside `mcp_harness/` via
  `.venv/bin/python -m pytest`.
- No new heavy dependencies (PR #11's `mesh_acquire` uses stdlib `urllib` only).
- Fail loud with specific messages; defensive on the serve path.
- The paper is a fixed unit square; TreeMaker/Oriedita behavior is fixed/partly
  inherent — fixes are agent/extraction-side, never engine-side.
- Money is spent only when `MESH_PROVIDER=meshy` with a real key; default is offline.
