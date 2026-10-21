# Design: B5 slice 1 — pose-search recovery loop on star-4

**Status:** Implemented 2026-07-07 — recovery PASS (refined argmin (101.25, 0.425),
chamfer 0.014271, within one refine-grid step of target (100.0, 0.45)), hull-quad
UNBLOCKED (1/5 candidates fold: star4-head-0.5, maxDisp 1.5241, full B5 unblocked
on star-topology bases); see 2026-07-07-handoff-b5-slice1-outcome.md.
**Date:** 2026-07-07
**Parent docs:** `2026-06-30-finished-model-view-research.md` (B5 at the roadmap
table; open questions §6.7), `2026-07-07-handoff-folded-state-slice4-outcome.md`
(tip-local primitive family proven complete; "weigh B5 now" recommendation),
`2026-07-02-strain-oracle-loop-design.md` (sim-as-oracle stance this builds on).

---

## 1. Goal

Prove the automated pose-search loop — **apply shaping ops → sim relax →
score against a target → iterate** — closes end-to-end on ONE model, by
recovering a known pose from cold search. This is B5's load-bearing
identifiability test: if search cannot recover a *self-generated* target,
matching an *external* reference mesh was never possible.

Concretely: apply a known `reverse:X,Y:d*:θ*` op to one star-4 flap, capture
its sim-folded geometry as the target, then search a `(θ, d)` grid from cold
and recover `(θ*, d*)` by chamfer distance.

A side probe tests whether a **hull-filling quadruped base** exists — the
gate on full B5 (mesh-guided posing of an animal), since the squared dog and
quad relax FLAT in the sim and cannot be posed at all.

## 2. Decisions made in this cycle

| Question | Decision |
|---|---|
| Objective function (roadmap §6.7) | **Chamfer distance on captured 3D vertex sets**, not silhouette IoU. Target and candidates are the same base in the same sim frame, so no registration is needed. Joint-angle fit against the mesh skeleton is the slice-2 direction. |
| Search method (roadmap §6.7) | **Coarse grid (5×5) + one local refinement pass.** ~25 sim evals at ~20 s each. No CMA-ES / Bayesian machinery for a 2-D problem. |
| Search space | **One flap, 2 params `(θ, d)`.** Smallest space that proves the search composes rather than line-scans; `d` gives a strong geometric signal even if θ-sensitivity is weak. Two-flap independence is slice-2 territory. |
| Smallest honest slice | **Parameter recovery on star-4**, offline, no agent/UI. Star-4 is the only base proven to fold (squared dog/quad: displacement exactly 0.0); pretending to match a dog mesh would be vacuous. |
| Deliverable shape | **Tested module + probe drivers** (approach A). The search/objective logic is pure and pytest-covered with a mocked evaluator; the Playwright runs live in committed probes. Slice 2 inherits the module verbatim. |
| Sequencing | **Agent-wiring mini-PR first** (`reverse_deep` + `sink` into SYSTEM_PROMPT / strain-oracle vocabulary — the slice-4 leftover), as its own quick cycle before this slice's implementation. |
| Full B5 gating | Full B5 (real mesh objective on an animal base) is **gated on a foldable animal base**. The hull-quad probe here is the cheap direction; molecule corner-creasing is the expensive one and stays out of scope. |

## 3. Components

### 3a. `mcp_harness/pose_search.py` — pure module (tested)

No sim, Playwright, or web imports. Two responsibilities:

- `chamfer(A, B)` — symmetric mean nearest-neighbor distance between two
  `(N,3)` vertex arrays. Deliberately no alignment/registration step: same
  base, same sim coordinate frame.
- `grid_search(evaluate, axes)` and `refine(evaluate, best, ...)` —
  `evaluate` is an injected callable `params → score`; grid search returns
  the argmin cell plus all scores (for landscape printing); refine runs one
  local pass around the argmin. Evaluations that raise or return
  non-finite are recorded as `inf` and skipped, never fatal.

### 3b. `probe_pose_sensitivity.py` — the de-risk gate (runs FIRST)

The slice-3/4 sim smokes only exercised θ=180, which relaxes at zero strain.
Nothing yet proves the mass-spring solver's equilibrium *varies detectably
with θ* for θ<180. This probe measures that before anything is pinned:

- Capture star-4 + `reverse:` at θ ∈ {60, 90, 120, 150} (fixed d), plus one
  **repeat capture** at a single θ to measure the capture noise floor.
- Every capture must pass the anti-vacuous guards: displacement > 0, 0 NaN.
- **Gate:** adjacent-θ chamfer distances must clearly exceed the repeat-
  capture noise floor.
- **Decision rule:** θ signal ≫ noise → proceed as designed. θ flat but d
  strong → proceed with a widened, stated θ-recovery tolerance. Both flat →
  **the slice halts** and the finding is written up (B5 dies cheaply here,
  by design).

### 3c. `probe_pose_recovery.py` — the deliverable

- Pick `(θ*, d*)` **after** the sensitivity probe (measure-then-pin), capture
  its folded geometry as the target.
- Search a 5×5 `(θ, d)` grid from cold; each eval = apply op (pure Python) →
  Playwright capture → chamfer vs target. One refinement pass.
- **Success:** the grid argmin lands in the cell containing `(θ*, d*)`, and
  the refined estimate is within a tolerance pinned from the printed
  objective landscape. Failed candidate captures score `inf` (logged); a
  failed *target* capture aborts the run.
- Capture mechanics reuse the proven `probe_deep_sim_smoke.py` pattern:
  write fold to `web/frontend/dist/`, load `simulator/index.html?embed=1`
  under Playwright, `setFold(100)`, wait for the GPU solver, capture
  `getFoldedGeometry`.

### 3d. `probe_hull_quad.py` — hull-filling quadruped side probe

Star-4 folds because its leaf hull already fills the square, making
`complete_square` a no-op — no flat "F" corner faces pin the sheet. This
probe tests whether an *animal-shaped* tree can share that property:

- Construct 5-leaf quadruped-labeled trees with corner-pinned leaves,
  iterating the tree geometry until the compiled leaf hull fills the square
  exactly (the no-op check below is the pass/fail, not a visual judgment).
- Verify: `complete_square` is a no-op (raw == squared) → compile via
  TreeMaker → lint → sim-fold under Playwright → **displacement > 0**.
- The output is a **written finding** (in the slice handoff), not a shipped
  feature: it either unblocks full B5's slice 2 or confirms the foldable-
  animal-base problem needs its own brainstorm.

## 4. Testing

- **pytest** (in the backend suite): `chamfer` against hand-derived
  point-set fixtures; `grid_search`/`refine` against a mocked deterministic
  evaluator (quadratic bowl → known argmin; `inf`/raising evaluations
  skipped). No sim, no Playwright in the suite.
- **Probes** (committed, run manually): the sensitivity gate, the recovery
  run, the hull-quad probe. Their printed numbers are the evidence the
  handoff records; per measure-then-pin, no test value is pinned before its
  probe has printed it and it has been checked against hand reasoning.
- Full backend suite (`cd mcp_harness && .venv/bin/python -m pytest tests
  -q`) must stay green (~396 passed / 3 skipped at slice 4).

## 5. Error handling

- Candidate-capture failures (NaN, empty geometry, non-convergence) →
  `inf` score with a logged reason; the search continues.
- Target-capture failure → abort with a clear message (no target, no run).
- Any capture with displacement == 0 is treated as a FAILED capture (the
  vacuous-pass trap), not a valid low-chamfer candidate.

## 6. Out of scope (deferred, on purpose)

- Real-mesh objective (joint-angle fit vs the `mesh_to_tree` skeleton) —
  slice 2, gated on the hull-quad finding.
- Two-flap / higher-dimensional search.
- Any search-method machinery beyond grid + refine.
- Agent / MCP / SYSTEM_PROMPT exposure of the search (the mini-PR wires the
  slice-4 vocabulary only; search wiring is a later decision).
- Any UI or `web/server.py` change — the provenance contract is untouched;
  probes run offline on locally built folds.
- Fixing squared-base flat relaxation (molecule corner-creasing) — only
  *probed around* via 3d.
