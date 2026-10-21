# B5 slice 2 — joint-angle pose fit vs the mesh skeleton (design)

**Date:** 2026-07-07
**Status:** IMPLEMENTED — HALTED at the Task-3 gate: star4-head-0.5's head
tip packs AT the axial hub (one vertex), so the head angle is unmeasurable
and unactuatable as specced, and the front/back split is a true 4-fold tie
(handoff: docs/superpowers/2026-07-07-handoff-b5-slice2-outcome.md)
**Predecessor:** docs/superpowers/specs/2026-07-07-b5-pose-search-slice1-design.md
(recovery PASS; handoff docs/superpowers/2026-07-07-handoff-b5-slice1-outcome.md)

## Goal

Fit the star4-head-0.5 foldable base's flap shaping parameters to the joint
angles of a REAL target mesh's skeleton (the committed CC0 fox,
`mcp_harness/fixtures/quadruped.glb`), using slice 1's proven grid/refine
search and sim-capture primitives with a new frame-invariant angle objective.
This is the first exercise of (a) a target that is not self-generated and
(b) multi-flap search.

## Decisions (all user-approved)

| Question | Decision | Why |
|---|---|---|
| Target source | Real mesh fixture (`fixtures/quadruped.glb`) via `extract_skeleton` + `simplify_to_tree` | Proves the real pipeline end-to-end; the fixture is committed and deterministic (SKELETOR_SEED) |
| Objective | Joint ANGLES, not chamfer-vs-mesh | Angles are frame-invariant → no registration problem; chamfer worked in slice 1 only because both clouds shared the sim frame |
| Achieved-angle measurement | Approach A: tracked-vertex bone vectors (tip − center from captured geometry) | Near-zero cost on data the capture already returns; tip re-location through ops has a proven in-repo pattern (`build_star4_shaped`) |
| Flap scope | Symmetry-reduced sequential: one (θ, f) per group {front legs, back legs, head} — 3 sequential 2-param grid/refine searches (coordinate descent) | First multi-flap exercise without a 10-D search; matches the fox's bilateral symmetry; ~3× slice-1 sim cost |
| Op vocabulary | `reverse:{x},{y}:{d}:{theta}` ONLY | Parameter space identical to what slice 1 proved unimodal; the objective is the only new variable |
| PASS rule | Best-achievable, measured: de-risk probe sweeps each group's achievable angle range FIRST; PASS = search lands within one refine-grid step of measured best-achievable per group AND total angle error strictly < unshaped baseline | Separates "search works" from "base can't reach the pose" — a reverse fold has a bounded bend |

## Architecture & data flow

Two sides meet at a shared angle representation computed by ONE function:

**Target side (runs once, at probe start):**
`fixtures/quadruped.glb` → `load_mesh` → `extract_skeleton` →
`simplify_to_tree` → `detect_symmetry` → group leaf bones (head = the
unpaired leaf; leg pairs ordered front/back by projection onto the head-bone
direction) → `angles_from_bones` → 3 target angles
`{front, back, head}` in degrees (leg pairs averaged bilaterally). The
angles are PRINTED and hand-checked against the fox's visible anatomy before
any sim work (measure-then-pin).

**Fit side (the search loop):**
star4-head-0.5 base (4 unit corner legs + 0.5 head off one center node;
squaring is a geometric no-op — from slice 1's hull-quad probe) → for each
group in order front → back → head: `pose_search.grid_search` + `refine`
over that group's shared (θ, fraction), holding previously fitted groups at
their best values. Grid axes reuse slice 1's proven ranges: θ ∈
{60, 87.5, 115, 142.5, 170}, f ∈ {0.2, 0.35, 0.5, 0.65, 0.8} (5×5 coarse +
one 5×5 refine; refine-step tolerance θ ±13.75°, f ±0.075). Each evaluation: apply one reverse op per flap in the
group (mirrored placement for the leg pair) via `shaping.apply_display_ops`
→ `SimSession.capture` → `check_capture` (disp gate, NaN guard) →
`tracked_points` → `angles_from_bones` (SAME function as target side) →
score = `angle_error` (sum of |achieved − target| over the 3 angles).

**Angle definition (frame-invariant, both sides identical):**
- each leg angle = angle between the leg bone vector and the HEAD bone
  vector (junction→tip unit vectors);
- head angle = angle between the head bone vector and the MEAN of the four
  leg vectors.

## Components

All under `mcp_harness/`. Reused **verbatim, zero changes**:
`pose_search.py` (evaluator-injected), `web/server.py`, the lint path, the
raw `json` frame. `playwright` stays in `mcp_harness/.venv` ONLY — never in
`requirements*.txt`, `ci.yml`, or any pinned dep list.

### `pose_target.py` (NEW — pure, pytest-tested, no sim/mesh deps at import)
- `PoseTargetError(ValueError)`
- `bone_vectors(tree)` → `{leaf_id: np unit vector}` (junction→leaf) from a
  positioned `nx.Graph` (nodes carry `pos`). Zero-length bone → raise.
- `group_legs(tree, sym_pairs)` → `(head_leaf, front_pair, back_pair)`.
  Head = the leaf in no symmetry pair; exactly 2 pairs and exactly 1
  unpaired leaf required, else `PoseTargetError`. Front pair = the pair
  whose mean leaf position (relative to the junction) has the larger scalar
  projection onto the head bone's unit vector.
- `angles_from_bones(head_vec, leg_vecs)` → `{"front": deg, "back": deg,
  "head": deg}` per the angle definition above. Called on BOTH sides.
- `angle_error(achieved, target)` → sum of absolute differences (degrees).

### `sim_capture.py` (MODIFY — small addition)
- `tracked_points(fold, cap)` → dict of folded 3D positions for the 5 flap
  tips + the center vertex. Tip vertices re-located in the (possibly
  op-split) fold's `vertices_coords` by exact flat-coordinate match with
  8dp snap (the slice-4 sliver lesson); no match → `CaptureError`.
- `__main__` anchor path extended to print the 6 tracked points on the
  unshaped base (hand-check: 4 tips near the 4 corners, symmetric).

### `probe_angle_range.py` (NEW probe — the de-risk gate, NOT in pytest)
For each flap group, sweep θ across the search grid at mid-fraction on the
star4-head-0.5 base; print each group's achieved-angle range next to the
fox's target angle for that group. Verdict: HALT if any group's achievable
range < 3× the smallest measurable angle signal (threshold pinned from the
probe's own printed numbers, hand-checked — not invented up front).
PROCEED otherwise. Also records per-group best-achievable angle (the value
the PASS rule compares against).

### `probe_pose_fit.py` (NEW probe — the main event, NOT in pytest)
Sequential 3-group coordinate descent as described; JSONL incremental log
(every evaluation: group, θ, f, disp, achieved angles, score); baseline =
unshaped base's angle error, captured first. PASS = per-group fitted angle
within ONE refine-grid step of that group's measured best-achievable AND
total error strictly < baseline.

## Error handling
- Evaluator failures (op refused → identity fold detected via `shaped is
  sq`, capture failure, disp < gate, NaN) → raise inside the evaluator;
  `pose_search._score_one` converts to `inf` (slice-1 semantics, unchanged).
- Degenerate skeleton (no unpaired head leaf, ≠2 sym pairs, zero-length
  bone) → `PoseTargetError` at probe start; that is a reportable target-side
  finding, not something to work around silently.
- Solver is exactly deterministic on this machine — never use 0.0 as a
  tolerance; tolerances come from grid spacing or measured signals.
- `SimSession` stays HEADED by default (`PW_HEADLESS=1` opts in); headless
  WebGL does not advance the GPU solver on this machine.

## Testing
- `tests/test_pose_target.py`: hand-derived fixtures only — synthetic
  positioned graphs with angles known by construction (e.g., legs exactly
  90° to the head bone), symmetry grouping, front/back ordering, every
  degenerate-input raise. Pure and fast; no sim, no skeletor.
- Probes are probes: no pytest coverage; their verdicts and JSONL logs are
  the evidence.
- `tracked_points` exercised by the extended `sim_capture.__main__` anchor
  run (hand-checkable output), not by pytest.
- Full backend suite (`cd mcp_harness && .venv/bin/python -m pytest tests
  -q`) must stay green.

## Execution gates (each can end the slice as a documented outcome)
1. **Fox skeleton gate:** extraction must yield 1 unpaired head leaf + 2
   leg pairs at reasonable prune settings, and the printed target angles
   must survive a hand sanity check vs the fox's anatomy. Else stop and
   report (target-side blocker; slice dies cheap).
2. **Angle-range gate (`probe_angle_range`):** HALT if any group's
   achievable angle range is below 3× the smallest measurable signal.
3. **Fit gate (`probe_pose_fit`):** PASS/FAIL per the PASS rule.

## Carried constraints (from slice 1 / standing)
- Measure-then-pin: no pinned value that wasn't first printed by a
  committed probe and hand-checked.
- Anti-vacuous guard: every capture asserts displacement > DISP_GATE
  (0.10) and 0 NaN.
- Long probe runs launched from subagent shells MUST use `nohup`.
- Human merges every PR; ask before push/PR.
- No new MCP tools, agent/prompt changes, or UI work in this slice.

## Out of scope (explicitly deferred)
- Spined-quadruped foldable bases (hull-filling failed for both 2-spine
  candidates in slice 1's probe; needs its own probe cycle).
- Richer op vocabulary (crimp/reverse_deep/sink) in the search.
- Chamfer-vs-mesh with registration.
- Any agent/MCP wiring of the pose-fit loop.
