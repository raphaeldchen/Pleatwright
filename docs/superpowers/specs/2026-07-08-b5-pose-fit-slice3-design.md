# B5 slice 3 — asymmetric star probe + pose fit (design)

**Date:** 2026-07-08
**Status:** IMPLEMENTED — FIT FAIL on star(b=0.95, h=0.40) (back-group cross-coupling MISS; front+head within bounds; total error improved 285.9→276.2) (handoff: docs/superpowers/2026-07-08-handoff-b5-slice3-outcome.md)
**Predecessor:** docs/superpowers/specs/2026-07-07-b5-pose-fit-slice2-design.md
(HALTED at the Task-3 gate; handoff
docs/superpowers/2026-07-07-handoff-b5-slice2-outcome.md)
**Branch:** feat/b5-pose-fit-slice3 off main (3b55531, PR #32 merged)

## Goal

Un-stick the joint-angle pose fit after slice 2's halt. Slice 2 proved the
fit machinery (pose_target angle math, index-based tracked_points,
grid/refine search) but halted because star4-head-0.5 — the only known
hull-filler — packs its head tip AT the axial hub (head angle unmeasurable
and unactuatable) with a true 4-fold front/back tie.

Slice 3 does two things in one slice (user decision: probe + fit, not
probe-only):

1. **Probe:** sweep an asymmetric 5-leaf star family for a base whose head
   tip is a DISTINCT vertex from the axial hub and whose front/back legs
   are distance-separable, while still folding in the sim.
2. **Fit:** run the slice-2 pose fit — unchanged spec, 3-angle objective
   {front, back, head} vs the fox skeleton — on the winning base.

## Decisions (all user-approved)

| Question | Decision | Why |
|---|---|---|
| Slice scope | Probe + fit in ONE slice | Fit machinery already exists (~90% reusable); probe screening is cheap, so a wasted-slice risk is low; a halt at any gate ends the slice as a documented outcome |
| Fittable-base criterion | Two-stage screen: geometric stage 1 over the whole sweep; sim-fold stage 2 rescue for near-misses only if stage 1 finds nothing | "Squared folds don't fold" came from specific quad/dog bases — a measured hazard to test on borderline candidates, not a proven law; testing the thing we actually care about (sim displacement) is cheap for a handful of near-misses |
| Sweep family | Full 2D grid: back-leg b ∈ {0.80, 0.85, 0.90, 0.95} × head h ∈ {0.40, 0.45, 0.50, 0.55, 0.60} (front legs pinned 1.0), 20 compiles, no sim | Slice-1 proved the packable region is knife-edge and NON-monotonic — a 1D slice at h=0.5 could walk past the good pocket; 20 compiles is minutes; the printed 20-cell map is a deliverable even on a halt |
| Branch base | main after PR #32 merged (done: 3b55531) | Slice 3 depends hard on #32's code; avoids the known stacked-PR merge gotcha |

## Architecture

Two stages, same shape as slice 2 but with a base-finding probe in front:

```
probe_star_asym.py  (20 compiles, geometric map + stage-1 gate)
        │ stage 1 empty? → stage-2 sim rescue on best near-misses
        ▼
winning (b, h) base ──► starhead.py generalized to (b, h)
        ▼
probe_angle_range.py  (per-group achievable-angle gate — slice-2 design)
        ▼
probe_pose_fit.py     (sequential 3-group coordinate descent — slice-2 design)
```

The fit side reuses **verbatim, zero changes**: `pose_target.py`,
`sim_capture.py` (`axial_hub`, `tracked_points`), `pose_search.py`,
`web/server.py`, the lint path, the raw `json` frame. `playwright` stays in
`mcp_harness/.venv` ONLY.

## Components

### `probe_star_asym.py` (NEW probe — NOT in pytest)

Tree family: root + 4 legs + head off root; front legs pinned 1.0; knobs
(b, h) from the grid above. For every cell, compile via
`server._run_isolated(server._worker_compile_and_regions, ...)` and print a
map row:

- head-leaf flat position and its distance from paper center (0.5, 0.5);
- hull-vs-square gap: max distance of any square corner from the leaf hull
  (0 ⇔ squaring is a geometric no-op — same construction as
  probe_hull_quad);
- front/back distance split: sorted leg-tip distances from the head tip,
  reported as (d_near_pair, d_far_pair) and their difference;
- whether the head tip is a distinct fold vertex from `axial_hub(fold)`.

**Stage 1 gate (geometric, all 20 cells):** squaring is a no-op AND head
tip ≠ hub vertex AND front/back split unambiguous. The numeric thresholds
for "off-center enough" and "split enough" are pinned from the printed map
after hand-check (measure-then-pin) — not invented up front.

**Stage 2 rescue (ONLY if stage 1 passes nothing):** take the best
near-misses ranked by hull-vs-square gap (up to 3), apply
`square_complete.complete_square`, and sim-test directly in a headed
`SimSession`: displacement > DISP_GATE (0.10) and 0 NaN. A near-square hull
that folds is an acceptable base.

**Both stages empty → HALT** as a documented outcome. The 20-cell map is
the deliverable for a future base-geometry slice; the documented
escalations (vary front-leg length; head attached to a non-root node) are
explicitly out of scope for this slice.

### `starhead.py` (MODIFY — generalize)

Parameterize `compile_starhead` / `StarHeadBase` over `(b, h)` (defaults
preserve the slice-2 reproducer at b=1.0, h=0.5). Front/back grouping stays
distance-to-head-tip based; the ambiguity guard STAYS and must NOT fire on
the winning base — that non-firing is a hand-checked gate. Mapping matches
the fox convention: front = the leg pair nearer the head tip.

### `probe_angle_range.py`, `probe_pose_fit.py` (NEW probes — slice-2 design, unchanged)

Exactly as specified in the slice-2 spec (which they never got to run):
per-group θ sweep at mid-fraction with a 3×-smallest-signal HALT rule, then
sequential front → back → head coordinate descent using
`pose_search.grid_search` + `refine` (θ ∈ {60, 87.5, 115, 142.5, 170},
f ∈ {0.2, 0.35, 0.5, 0.65, 0.8}, 5×5 coarse + one 5×5 refine), JSONL
incremental log per evaluation, unshaped-baseline first.

**PASS rule (inherited word-for-word):** search lands within one
refine-grid step of measured best-achievable per group AND total angle
error strictly < unshaped baseline.

**Angle definition (unchanged, both sides computed by `pose_target`):**
leg angle = angle(leg bone, HEAD bone), pair-averaged; head angle =
angle(head bone, MEAN of the 4 leg vectors).

## Error handling

All slice-2 semantics carry over:

- Evaluator failures (op refused/identity fold, capture failure,
  disp < gate, NaN) → raise inside the evaluator; `pose_search._score_one`
  converts to `inf`.
- Degenerate fox skeleton → `PoseTargetError` at probe start (reportable
  target-side finding).
- Solver is exactly deterministic on this machine — never 0.0 tolerances;
  tolerances come from grid spacing or measured signals.
- `SimSession` HEADED by default (`PW_HEADLESS=1` opts in).
- multiprocessing spawn workers need a real script file as `__main__` —
  no stdin heredocs.
- Sim bridge `flat_coords` are SCENE-frame — never value-match fold-frame
  coordinates; `tracked_points` index alignment + uniform-scale integrity
  check is the guarantee.

## Testing

- `starhead.py`'s parameterized grouping gets hand-derived pytest coverage:
  synthetic layouts (asymmetric leaf positions with front/back known by
  construction), ambiguity-guard firing on the symmetric layout, guard NOT
  firing on a separable one. Pure and fast; no sim, no compile.
- `pose_target` tests (10) unchanged; probes stay OUT of pytest — their
  printed maps, verdicts, and JSONL logs are the evidence.
- Probe outputs (`*.out.log`, `*.out.jsonl`, `*.out.json`) stay
  uncommitted.
- Full backend suite (`cd mcp_harness && .venv/bin/python -m pytest tests
  -q`) must stay green.

## Execution gates (each can end the slice as a documented outcome)

1. **Base gate (`probe_star_asym`):** stage-1 (or stage-2 rescue) yields a
   base, hand-checked on the printed map; `StarHeadBase(b, h)` constructs
   without the ambiguity guard firing.
2. **Fox skeleton gate:** extraction yields 1 unpaired head leaf + 2 leg
   pairs and the printed target angles survive a hand sanity check vs the
   fox's anatomy (slice-2 gate 1, never reached — re-verified here).
3. **Angle-range gate (`probe_angle_range`):** HALT if any group's
   achievable range < 3× the smallest measurable signal.
4. **Fit gate (`probe_pose_fit`):** PASS/FAIL per the inherited PASS rule.

## Carried constraints (standing)

- Measure-then-pin: no pinned value that wasn't first printed by a
  committed probe and hand-checked.
- Anti-vacuous guard: every capture asserts displacement > 0.10 and 0 NaN.
- Long probe runs launched from subagent shells MUST use `nohup`.
- Human merges every PR; ask before push/PR.
- Op vocabulary: `reverse:{x},{y}:{d}:{theta}` ONLY.
- No new MCP tools, agent/prompt changes, or UI work in this slice.

## Out of scope (explicitly deferred)

- Varying front-leg length or head-attachment topology (documented
  escalation if the 2D grid comes up empty — its own probe cycle).
- Spined-quadruped bases; richer op vocabulary (crimp/reverse_deep/sink)
  in the search; chamfer-vs-mesh with registration.
- Any agent/MCP wiring of the pose-fit loop.
