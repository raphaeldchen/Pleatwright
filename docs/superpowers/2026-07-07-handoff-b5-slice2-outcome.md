# Handoff: B5 slice 2 (joint-angle pose fit) — outcome: HALTED at the Task-3 gate

**Spec:** docs/superpowers/specs/2026-07-07-b5-pose-fit-slice2-design.md
**Plan:** docs/superpowers/plans/2026-07-07-b5-pose-fit-slice2.md
**Verdict:** HALT before any sim fitting — the star4-head-0.5 base's measured
geometry breaks the spec's fit-side assumptions. No probe_angle_range /
probe_pose_fit runs happened; gates 1–3 were never reached.

## What shipped

- `mcp_harness/pose_target.py` + 10 tests (commit a7bbace) — pure 3-angle
  representation {front, back, head}, shared by target and fit sides.
  Unaffected by the halt; correct and reusable as-is.
- `mcp_harness/sim_capture.py` — `axial_hub` + `tracked_points`
  (commit 037276b). `tracked_points` is INDEX-based: targets located by 8dp
  (x, y) match in the FOLD's own `vertices_coords`, captured arrays read by
  index, with a pairwise-distance uniform-scale integrity check. Anchor run
  2026-07-07: maxDisplacement 1.3088 PASS; hub (0.5, 0.5); 4 star-4 tips
  coincident at the folded stack (-0.3907, -0.0885, z≈0), hub tracked at
  (+0.2982, +0.6363, 0). The tracking approach itself WORKS.
- `mcp_harness/starhead.py` (commit c77e8b9) — probe support whose
  constructor self-check is the halt reproducer
  (`cd mcp_harness && .venv/bin/python starhead.py`).

## The halt: measured facts (2026-07-07/08 self-check)

star4-head-0.5 compiles with legs at the 4 corners (4/4, matching slice 1's
probe_hull_quad) but the head leaf (node 5) packs at the paper CENTER
(0.5, 0.5) — NOT on a paper edge as the plan's gate text assumed. The
h=0.5 packing is exactly 4-fold symmetric: 4 unit leg circles at the
corners, the 0.5 head circle tangent to all four at the center (leg circle
radius m = 0.4714, corner→center 0.7071 = 1.5 m).

Two independent spec-breaking consequences:

1. **Head tip == axial hub.** The raw fold has ONE vertex (v2) at
   (0.5, 0.5) with total degree 8 and axial (M/V) degree 8 — the head
   flap's tip IS the hub vertex. So:
   - the head bone vector (folded tip − folded hub) is identically ZERO on
     every capture → `angles_from_bones` raises `PoseTargetError` always;
     the head angle is unmeasurable as specced;
   - `reverse:0.5,0.5:d:θ` would target the hub (8 axial edges meet there,
     `_tip_axial_len` would pick one arbitrarily), not a head flap → the
     head group is unactuatable as specced too.
2. **Front/back split is a true tie.** All 4 leg tips are exactly
   0.70710678 from the head tip, so "front = the 2 corners nearest the
   head" cannot select. `StarHeadBase.__init__`'s ambiguity guard raises
   `front/back split ambiguous` by design.

Slice-1 context that explains it: probe_hull_quad's own commit body noted
"a small head circle re-optimizes the packing so the 4 unit legs slide onto
edges … at h=0.5 the layout snaps back to corner-symmetric". The
corner-symmetric snap is precisely WHY h=0.5 is the only hull-filler — and
that same symmetry puts the head at the center. Hull-filling and an
off-center head are in direct tension in this 5-leaf star family.

## Findings

- The fit machinery built so far is sound: index-based tracked_points
  passed its live anchor with a hand-checked readout, and pose_target's
  pure math is pinned by 10 hand-derived tests (20 total with
  test_pose_search).
- The blocker is BASE GEOMETRY, not search or measurement code. Any base
  whose head circle packs concentric with the hub can never express a head
  angle through tip tracking or tip-targeted reverse ops.
- The spawn-isolated compile worker cannot run from stdin heredocs
  (`FileNotFoundError: <stdin>` from multiprocessing spawn re-import) —
  debug drivers must be real files.

## Slice 3 entry point

The cheapest probe to un-stick the pose fit (pick one, brainstorm first):

1. **Asymmetric star family probe** (recommended, ~probe_hull_quad cost, no
   sim until a hull-filler appears): sweep 5-leaf stars with unequal leg
   lengths (e.g., front legs 1.0, back legs 0.8–0.95) and/or head lengths
   near 0.5. Any asymmetry that survives hull-filling moves the head circle
   off-center → distinct head tip vertex + a real front/back distance
   split. Reuses probe_hull_quad's corner/no-op checks verbatim.
2. **Legs-only fit on star4-head-0.5** (spec amendment): drop the head
   group, fit {front, back} with an ARBITRARY but pinned corner labeling
   (the base is 4-fold symmetric, so the labeling is a gauge choice; the
   ops themselves break the symmetry). Loses the head angle — accepts a
   2-angle objective.
3. **Ridge-vertex head tracking** (measurement-side fix only): measure the
   head bone via the head flap's ridge vertices instead of its tip. Does
   NOT fix actuation (no tip to reverse-fold), so only useful combined
   with (2)-style scope cuts.

## Gotchas carried forward

- All slice-1 gotchas still hold (headed SimSession, deterministic solver
  — never 0.0 tolerances, nohup for subagent-launched probes, playwright
  in mcp_harness/.venv only, probe outputs uncommitted).
- The sim bridge's `flat_coords` are SCENE-frame (hub at origin, corners
  ±0.7071 in X-Z) — never value-match fold-frame coordinates against them;
  index alignment is what the bridge guarantees (tracked_points enforces
  it with a uniform-scale integrity check).
- multiprocessing spawn workers (server._run_isolated) need a real script
  file as __main__ — stdin heredocs crash on re-import.
- probe_hull_quad's "head on a paper edge" applies to the NON-hull-filling
  h=0.15/0.3 candidates only; h=0.5 has the head at the center.
