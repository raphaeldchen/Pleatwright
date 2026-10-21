# Handoff: B5 slice 4 (second descent pass + crimp reachability) — outcome

**Spec:** docs/superpowers/specs/2026-07-09-b5-pose-fit-slice4-design.md
**Predecessor:** docs/superpowers/2026-07-08-handoff-b5-slice3-outcome.md

## What shipped
- `mcp_harness/pose_search.py` — `coordinate_descent(evaluator_factory,
  schedule, initial=None) -> DescentResult` (explicit-schedule multi-pass
  descent, resumable via `initial`) + `grid_step_tol(angles, best_index)`
  (grid-adjacent one-step tolerance, fixes the slice-3 bug where a failed
  cell let "adjacent" span 2+ grid steps) — 10 new tests (5 + 5).
- `mcp_harness/shaping.py` — `crimp_ops(tip_xy, axial_len, theta, fraction,
  fraction2) -> [reverse_op, outside_op]`, mirrors the tool-layer crimp
  composition (`d1 = fraction * axial_len`, `d2 = fraction2 * d1`), carries
  the theta != 90 guard — 4 new tests.
- `mcp_harness/pose_target.py` — `head_among_unpaired(leaf_ys) -> (head,
  dropped)`, the fox tail-drop tie guard (never guess on a y-tie within
  1e-6) — 4 new tests; wired into `starhead.fox_targets()` (Task 4).
- `mcp_harness/starhead.py` — `make_ops` extended: a group spec can be a
  bare `(theta, fraction)` (unchanged, reverse-only) or `("crimp", theta,
  fraction, fraction2)` (emits a `shaping.crimp_ops` pair per tip); new
  `_self_check_winner` mode (`starhead.py winner <theta> <f2>`) prints the
  winner base's hub/tips/axial lengths and self-checks a sample back-group
  crimp with no sim. Pinned numbers (from the Task-5 commit body,
  `git log -1 --format=%B ecce5a6`, theta=105 f=0.5 f2=0.5, winner
  b=0.95/h=0.40):
  ```
  back tip (0.0, 0.78270962) axial 0.381433: d1=0.19071639508022356
    d2=0.09535819754011178  (d2/d1 == 0.5 exactly, bit-for-bit 2*d2==d1)
  back tip (0.0, 0.0)       axial 0.539268: d1=0.26963400800663573
    d2=0.13481700400331786  (d2/d1 == 0.5 exactly, bit-for-bit 2*d2==d1)
  crimp pair applied: 36 verts (base 22)
  ```
  theta=105 applied clean on the first grid try (no retry to 75/142.5
  needed); both op pairs parsed via `shaping.parse_op` and neither was
  refused.
- `mcp_harness/probe_angle_range.py` — task-zero fix: `angle_tol` now
  computed via `pose_search.grid_step_tol` over the FULL theta grid
  (`None` = failed cell) instead of the successful-only list, plus a
  gate-3 HALT branch when `grid_step_tol` returns `None`. Re-run: fox
  targets front 134.8316 / back 138.6544 / head 137.7186 deg (exact match
  to slice 3); best-achievable front 49.4863@θ87.5 (gap 85.3453, tol
  13.7617), back 62.8255@θ142.5 (gap 75.8289, tol 2.4550), head
  27.1291@θ170.0 (gap 110.5895, tol 2.0842); verdict PROCEED.
- `mcp_harness/probe_pose_fit.py` — rebuilt as a thin driver over
  `coordinate_descent`, two modes: `r2` (reverse-only resume, seeded from
  slice-3's pinned fitted params, schedule `[front, back]`) and `x`
  (extended 5-stage crimp fit — not run this slice, gated OUT by gate 2's
  HALT).
- `mcp_harness/probe_crimp_range.py` — new gate-2 probe: back group only,
  fraction fixed 0.5, grid theta ∈ {60, 75, 105, 142.5, 170} × f2 ∈ {0.35,
  0.5, 0.65} (15 cells), reports best cell / f2 sensitivity / extension
  past the reverse-only ceiling / PROCEED-or-HALT verdict.
- Full backend suite: 442 passed / 3 skipped (424 slice-3 baseline + 18
  new tests from this slice's Tasks 1-4; count identical across both of
  this slice's runs).

## Findings

**Gate 0 (cleanups + re-run):** the `angle_tol` grid-adjacency fix landed
and the `probe_angle_range` re-run reproduced slice 3's tols within drift
(front 13.7617, back 2.4550, head 2.0842) because every sweep cell
happened to succeed this run — grid-adjacent == successful-adjacent, so
the fix's behavioral difference is armed only for future runs with failed
cells. Fox targets matched slice 3 exactly (deterministic extraction).
Suite 442 passed / 3 skipped. Verdict PROCEED.

**Gate 1 (r2, reverse-only second pass):** the resume schedule
`[front, back]` (head untouched from the seed) produced final total error
**279.2709**, which IS an improvement over the unshaped baseline
**285.9108**, but a **REGRESSION** against the slice-3 seed
**276.1833** (re-measured in this session from the same fitted params).
Per-group: front achieved 44.2928 (gap 90.5388, bound 99.1069) OK; back
achieved 51.7584 (gap 86.8960, bound 78.2838) **MISS**; head (unchanged
from seed) achieved 35.8825 (gap 101.8361, bound 112.6737) OK.

Mechanism (root-caused, not guessed): the resume re-search runs each
group's stage on the coarse THETAS/fraction grid, which cannot represent
a refined off-grid seed point — the slice-3 seed's front fraction is
0.575, off the coarse grid entirely. Re-fitting front on the coarse grid
therefore forfeits the refined seed (front's coarse/fine stage score
303.45 is far worse than the seed context implies), and while the back
re-fit to (115.0, 0.2) recovers most of the loss (279.1776), the total
still lands above the seed's 276.1833. `coordinate_descent` has no
"keep the incumbent if the re-fit is worse" comparison — a resume pass
can only ever help if the seed itself is representable on the search
grid, which it isn't here.

Back is still MISS: back-stage achieved (in isolation, at the resumed
fit) 51.7584, gap 86.8960 vs bound 78.2838. The reverse-only back
ceiling — max(sweep best-achievable 62.8255, r2 final back 51.7584) — is
pinned at **62.8255**; this is the number gate 2's crimp probe had to
beat by >= 10.

**Gate 2 (crimp range, back group): HALT.** Best crimp cell: back
**62.9182** @ theta=60.0, f2=0.65 (gap to target 75.7361, tol 2.2027).
Extension past the reverse-only ceiling: **62.9182 − 62.8255 = 0.0927
deg**, required >= 10.0 deg. All 15 grid cells captured cleanly (disp
0.9023–0.9968, zero failed/refused/flat-equilibrium holes). f2
sensitivity at the best theta (60.0): angles over f2 {0.35, 0.5, 0.65} =
[52.0549, 57.3309, 62.9182] → spread **10.8634 deg** — the f2 (offset)
knob clearly moves the achieved angle. But the *extension* over the
reverse ceiling (0.0927 deg) is **within the ~0.09-deg identical-params
capture-drift band measured in Task 7** (back's fine_score 279.1776 vs
the final joint re-capture 279.2709 at the SAME fitted params differed by
0.0934, from the unrounded 279.27091 − 279.17755) — i.e., crimp's
apparent edge over the reverse-only ceiling is
indistinguishable from capture noise. Mechanism: crimp (reverse + outside,
zigzag) preserves the flap's overall DIRECTION by construction — f2
trades the fold's offset/depth, not its terminal bearing — so a
direction-based joint-angle objective cannot be moved by a crimp the way
it can by a reverse (which does change direction). Per the plan's gate
rule, Task 9 (gate 3, extended multi-pass fit) is correctly SKIPPED.

**Overall:** both slice-4 hypotheses are now measured dead on this base.
Iteration (a second coordinate-descent pass) regressed rather than
improved, because the coarse resume grid cannot hold the refined seed.
The crimp op cannot extend directional reach, because it is
direction-neutral by design. Neither avenue closes the ~76–111 deg gap to
the fox targets on the winner base (b=0.95, h=0.40).

## Slice 5 entry point

Present both candidates, cheapest first:

1. **Cheapest un-stick — fix the resume mechanism.** Include each group's
   seed value explicitly in its stage axes (or re-refine around the seed
   before searching) so a resume pass can only improve on 276.1833, never
   regress by forfeiting an off-grid refined point. This is a small change
   to the schedule/axes construction in `probe_pose_fit.py`'s r2 mode (or
   a `coordinate_descent` option to snap the incumbent into the grid); it
   reuses everything else built this slice. It fixes the measured
   cross-group coupling regression but does **not** address reachability
   — even a perfect resume tops out at the slice-3 seed's 276.1833 (back
   still MISS in isolation-vs-final terms).
2. **The reachability wall** (76–111 deg gaps to target; back's
   single-fold ceiling ~63 deg) is now measured to be **op-vocabulary-
   independent for direction**: reverse is the only direction-changing op
   tried so far, and crimp — proven direction-neutral (0.09 deg extension
   vs a 10.86 deg offset-sensitivity) — cannot help. Remaining candidates,
   all bigger bets, to brainstorm before committing:
   - direction-changing deep ops (`reverse_deep` folds a flap THROUGH its
     layers at a non-tip depth, per the at-depth-reverse-fold slice-3
     engine work — untried in the pose-fit context);
   - base-geometry changes (the flap's axial orientation on the winner
     base bounds what ANY tip-local fold can reach; a different (b, h) or
     a different base family might reorient the flap toward the target);
   - changing the objective (silhouette/chamfer match against the mesh
     instead of joint angles) — sidesteps the reachability question by
     scoring a different, possibly more permissive, target shape.

## Gotchas carried forward

- All slice-1/2/3 gotchas still hold (headed SimSession, deterministic-
  ish solver — never 0.0 tolerances, nohup for subagent probes,
  playwright venv-only, scene-frame flat_coords / index-based tracking,
  spawn workers need real script files, probe outputs uncommitted,
  StarHeadBase keys tips/hub off the squared frame not raw, stage-2
  squared bases DO fold, head-flap f-viability is narrow, sequential
  coordinate descent is unsafe against cross-group coupling without a
  re-pass or joint optimization).
- **Drift band is WIDER for derived quantities than for a single angle.**
  Per-capture drift is ~1e-5–0.02 deg, but this slice measured: a
  multi-angle total-error drift of 0.0298 (seed vs re-measured seed, three
  angles compounding); a max−min RANGE drift of 0.069 (head range, Task 6
  hand-check, vs slice-3's 13.3707); and an **identical-params
  eval-vs-recapture drift of 0.0934 total-error units** (back's
  fine_score 279.17755 vs the final joint capture 279.27091 at the same
  fitted params, Task 7). Any future
  strictly-less-than comparison on a derived/summed quantity (e.g. a
  `beats_r2` or `beats_ceiling` gate) needs a margin >> 0.1, not the raw
  per-capture band — the crimp gate's 10.0 deg margin was chosen
  precisely because a smaller number (e.g. 3 deg) would have been
  unreadable against this noise floor, and even so the measured 0.0927
  deg extension landed inside the 0.09-deg noise band, not just short of
  the 10 deg bar.
- **Resume-seeding a coordinate descent with REFINED (off-grid) params
  loses them for the re-fitted group.** The coarse grid can only
  represent its own grid points; if the seed's fraction/theta is off-grid
  (e.g. front's seeded fraction 0.575, off the {0.2, 0.35, 0.5, 0.65, 0.8}
  grid), re-searching that group on the coarse grid cannot recover the
  seed and can only do as well as the best on-grid cell — which was
  measurably worse here. Fix for any future resume pass: seed the stage's
  own axes with the seed value included, or re-refine around the seed
  before trusting a resume pass to only improve.
- **`probe_crimp_range`'s two early `_halt()` paths (all-cells-failed /
  `angle_tol is None`) write a HALT json WITHOUT the `f2_star`/`best`/
  `angle_tol`/`extension` keys** (latent — neither path fired this run,
  all 15 cells succeeded and `grid_step_tol` returned a real tolerance —
  but any future consumer of `probe_crimp_range.out.json` must check
  `verdict` before assuming those keys exist).
- **Crimp is an offset op, not a direction op:** measured f2 spread was
  10.8634 deg (the offset/depth knob clearly works) while the direction
  change over the reverse-only ceiling was only 0.0927 deg (noise-level).
  Any future op-vocabulary choice for closing a large directional gap
  should not expect a crimp/zigzag composition to help — it needs an op
  that actually reorients the flap's terminal bearing (e.g. `reverse_deep`
  or a base-geometry change), not one that reshapes the fold's profile
  along the same bearing.
