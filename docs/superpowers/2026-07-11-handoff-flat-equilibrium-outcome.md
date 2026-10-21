# Handoff: flat-equilibrium root cause (Pillar B capstone) — outcome

**Spec:** docs/superpowers/specs/2026-07-10-flat-equilibrium-root-cause-design.md
**Predecessor:** docs/superpowers/2026-07-09-handoff-b5-slice4-outcome.md

## What shipped

- `mcp_harness/sim_instrument.py` — the Gate-0 instrument pack (in-page
  `{type:'error'}` channel, console harvest, load/vertex-parity
  verification, crease-build audit via `setFoldData(fold, true, true)`
  returnCreaseParams, displacement time-series at ~1s/5s/20s, offline
  per-crease achieved angles, face-quality stats) + the mechanism
  classifier (IMPORT-DEAD / ACTUATION-DEAD / SOLVER-PARKED /
  PHYSICS-PINNED / FOLDS, decision-ordered) — 5 new tests.
- `mcp_harness/probe_flat_eq_matrix.py` — Gate 0: the full 9-fixture
  instrumented matrix in one SimSession (motion floor measured-then-pinned
  on the star-4 control; anchor gate 1.0..1.6).
- `mcp_harness/fold_mutate.py` — Gate-1 mutation library, six pure-python
  fold-dict transforms: `to_3d` / `z_jitter` (controls), `interior_faces`
  (2D face derivation, exact-equal to the browser's), `pre_triangulate`,
  `weld_short_chords` (tol 0.012 pinned from measured dog chords 7.94e-3),
  `frame_F_to_B` (controller-added, assignment-only) — 6 new tests.
- `mcp_harness/probe_flat_eq_bisect.py` — Gate 1: the mutation-ladder
  driver (8 rungs + quad witness, one-variable-at-a-time discipline).
- `web/frontend/public/simulator/js/ide-bridge.js` — **THE fix**: a
  deterministic flat-tie break in `loadFoldObject` — all-2-coord vertex
  lists are lifted to the solver's y-up frame `[x, h_i, y]` with a
  per-vertex Knuth-multiplicative-hash height, amplitude **2e-4** (the
  1e-4→2e-4 contingency was fired and measured, see Gate 2), inserted
  after the existing 2D face derivation so faces/edges_foldAngle synthesis
  is untouched. Mirrored byte-identical public → dist (dist is gitignored;
  SimSession serves dist). The download/lint `json` frame and
  `display_json` stay pure 2D FOLD — the kick lives only inside the sim's
  own load path.
- `mcp_harness/sim_capture.py` — `check_capture(cap, expect_verts=None)`
  vertex-parity hygiene: a stale/silent failed load now reports as stale
  instead of "did not fold" (+1 unit test).
- `mcp_harness/tests/test_sim_regression.py` — opt-in sim regression,
  env-gated `RUN_SIM_REGRESSION=1` (headed sim required; skipped in the
  normal suite): served dog through the exact product path folds > 0.10
  with vertex parity, within 3 bounded logged capture attempts
  (persistent park = fail), after a public↔dist ide-bridge byte-equality
  preamble.
- `mcp_harness/probe_dog_folds.py` — the permanent tripwire probe: served
  dog gated (disp > 0.1, 0 NaN, within 3 bounded logged attempts —
  persistent park = FAIL), quad secondary reported-not-gated.
- `mcp_harness/probe_dog_pose.py` — Gate 3 payoff probe: leaf grouping
  with positive classification guards, fox-target comparison, single-op
  actuation datum (all informational, no gate).
- `mcp_harness/tests/goldens/dog.fold` was already tracked (since 17c5348)
  and byte-identical to `docs/dog.fold` — the plan's promotion step was a
  zero-diff no-op.
- Full backend suite (`cd mcp_harness && .venv/bin/python -m pytest tests
  -q`): **454 passed / 4 skipped in 514.64s (0:08:34)** — final
  handoff-time run; count identical to Task-5's run (454 / 4 in 499.93s).
  Opt-in sim regression: 1 passed in 22.02s.

## Findings

**Gate 0 (instrumented 9-fixture matrix):** motion floor 1e-06 (rest
jitter measured exactly 0.0 after driver fix 2, floor pinned at the lower
bound); anchor star-4 1.310909140682583 PASS (band 1.0..1.6). Verdicts
(probe_flat_eq_matrix.out.json):

| fixture        | class         | final_disp | droppedMV/exp | load_errs | achieved_max (deg) | min_tri_area |
|----------------|---------------|------------|---------------|-----------|--------------------|--------------|
| star4          | FOLDS         | 1.3109091  | 0/8           | 0         | 179.99999517       | 6.25e-02     |
| dog_served     | SOLVER-PARKED | 0.0        | 0/38          | 0         | 1.2074e-06         | 3.05e-11     |
| dog_raw        | FOLDS         | 1.1160661  | 0/38          | 0         | 179.96830240       | 1.70e-04     |
| quad_squared   | SOLVER-PARKED | 0.0        | 0/8           | 0         | 1.2074e-06         | 5.34e-10     |
| quad_raw       | FOLDS         | 0.9605908  | 0/8           | 0         | 179.99995050       | 1.20e-02     |
| hshape_squared | FOLDS         | 1.5165240  | 0/9           | 0         | 177.64564498       | 2.20e-10     |
| hshape_raw     | FOLDS         | 1.1434407  | 0/9           | 0         | 179.99962984       | 1.74e-02     |
| bear           | FOLDS         | 1.2543472  | 0/52          | 0         | 179.63957882       | 1.98e-11     |
| winner_star    | FOLDS         | 1.2848618  | 0/26          | 0         | 178.58064697       | 2.10e-04     |

- dog_served + quad_squared park at EXACTLY 0.0 across all samples with
  ALL M/V creases built, 0 load errors, vertex parity OK → import and
  actuation are healthy; the solver never leaves the flat equilibrium:
  **SOLVER-PARKED**.
- **dog_raw FOLDS 1.1161 — the "dog never folds in sim" lore is STALE for
  the raw variant**: the freeze is introduced by the display/squaring
  path, not by the TreeMaker compile. (The lore stays true for the served
  artifact, which is the success bar.)
- hshape_squared FOLDS 1.5165 → squaring does NOT universally park; and
  sliver min_tri_area alone cannot be the discriminator (hshape_squared
  2.2e-10 and bear 1.98e-11 both fold).
- b2/b3 bent-dog puzzle resolved: dog_served achieved_max 1.2074e-06 deg
  → NO crease actuates at all (dog_served and quad_squared share the
  IDENTICAL float 1.2074182791366184e-06 = the angle-metric quantization
  floor on a bit-still mesh); the tracer-era bent-dog screenshots came
  from folds with shaping ops applied — lore imprecise, not wrong.
- Two DRIVER bugs were found and fixed before any verdict was trusted:
  (fix 1) the crease audit called `setFoldData` with a bare TreeMaker fold
  and crashed at pattern.js:991 triangulatePolys (undefined
  faces_vertices) → 9/9 PROBE-ERROR on run 1; the audit now replicates
  ide-bridge.js loadFoldObject's derivation so audit input == real-load
  input. (fix 2) the sim boots at creasePercent 0.6 (globals.js:49) and
  seeds the solver from it → the "rest" read was a 60% fold (measured
  0.5865 on star-4 → motion_floor 5.865, ~4.5x the anchor!); the driver
  now posts setFold percent:0 BEFORE loadFold; rest jitter then measured
  exactly 0.0.

**Gate 1 (mutation ladder → root cause):** rows verbatim from
probe_flat_eq_bisect.out.json:

| rung | class | final_disp | droppedMV | motion (disp @ t) |
|---|---|---|---|---|
| baseline_served | SOLVER-PARKED | 0.0 | 0 | 0.0 @ 1s/5s/20s |
| to_3d_control | SOLVER-PARKED | 0.0 | 0 | 0.0 @ 1s/5s/20s |
| z_jitter_1e-4 | FOLDS | 1.3148632368455098 | 0 | 0.7798 @1s → 1.2595 @5s → 1.3149 @20s |
| percent_ramp | SOLVER-PARKED | 0.0 | 0 | 0.0 @ 8s/16s/36s (20/50/100% stages) |
| frame_F_to_B | SOLVER-PARKED | 0.0 | 0 | 0.0 @ 1s/5s/20s |
| pre_triangulate | SOLVER-PARKED | 0.0 | 0 | 0.0 @ 1s/5s/20s |
| weld_0.012 | SOLVER-PARKED | 0.0 | 0 | 0.0 @ 1s/5s/20s |
| raw_no_frame | FOLDS | 1.1178476328482785 | 0 | 0.7732 @1s → 1.0590 @5s → 1.1178 @20s |
| quad+z_jitter_1e-4 (witness) | FOLDS | 0.9364976291908949 | 0 | 1.3583 @1s → 1.3290 @5s → 0.9365 @20s |

**ROOT CAUSE (named at Checkpoint B):** the served/squared dog and quad
reach the GPU solver EXACTLY flat in exact ±z force balance at the flat
bifurcation — crease torques cancel to float zero, so `setFold(100)`
never produces motion. A 1e-4 out-of-plane jitter breaks the tie and the
solver follows the fold path to a full fold (dog 1.3149, on par with the
star-4 anchor 1.3109); the SAME rung unfreezes quad_squared (0.9365) —
two independent frozen bases, same minimal mutation (the spec's
substitution rule: the pathology is not injectable into star-4, which is
already exactly flat and FOLDS). All four cleanup rungs
(percent_ramp / frame_F_to_B / pre_triangulate / weld_0.012) plus the
to_3d control park at exactly 0.0 → not the fold-percent protocol, not
frame assignment semantics, not the sim's face-split choices, not
sub-0.01 chords, not the 3-coord code path: every mutation that leaves
the exact flat symmetric configuration intact stays frozen. Bounding
control raw_no_frame FOLDS 1.1178 vs Gate-0 dog_raw 1.1161 (drift 1.8e-3,
healthy reproduction). External first-order evidence is consistent: a
sim-free rigidity classifier (separate branch, user-relayed) measures 3
first-order folding DOF on the served dog — the fold path exists, the
solver just never actuates it.

**OPEN (labeled hypothesis, NOT measured):** why raw dog/quad self-start
while served park — plausibly the symmetric square frame completes the ±z
cancellation that the raw hull's asymmetric boundary leaves broken
(hshape_squared retains enough asymmetry to self-start). Recorded as
hypothesis only; not load-bearing for the fix.

Driver findings worth keeping (probe-side only, sim untouched): (d1)
fold.js `sort_vertices_vertices` is 2D-ONLY and both load paths derive
faces through it for bare folds → a bare 3-coord fold can never load; the
3D rungs pre-derive faces_vertices while still 2D via
`fold_mutate.interior_faces`, verified exact-equal to the browser
derivation (dog 32 faces, quad 13). (d2) pattern.js processFold maps
2-coord (x,y)→(x,0,y) [sim is y-up] but consumes 3-coord vertices AS-IS →
FOLD-spec `[x,y,z]` must be permuted to sim-frame `[x,z,y]` at the driver
boundary.

**Gate 2 (the fix, bridge layer): CONTINGENCY FIRED AND RESOLVED.** The
pinned Knuth hash at the Gate-1-proven amplitude 1e-4 PARKED the dog
(0.0000; quad folded 0.4341) while a diagnostic session isolated the
variable: the bridge jitter demonstrably reached the model (flat-y-extent
2.73e-4), Gate-1's Mersenne z_jitter@1e-4 replicated (1.312409 vs
recorded 1.3149, within drift), and the bridge's exact Knuth values
applied Python-side ALSO parked (0.000000) → the hash PATTERN itself is
dog-degenerate at 1e-4, independent of where it is applied. The single
sanctioned amplitude retry shipped **2e-4: dog 1.5910 PASS, quad 0.8057**
(still sub-visual, 2 parts in 10^4 of paper size). Opt-in regression
(`RUN_SIM_REGRESSION=1`): 1 passed in 22.02s; without the env var it
skips with the verified reason string. What is proven is the MECHANISM
(generic out-of-plane symmetry break); the shipped pattern's efficacy is
measured by probe_dog_folds, and its margin is thin — see the tripwire
section below.

**Gate 3 (payoff, informational): first fox-target comparison on a
compiled base.** Leaf grouping passed every guard (ambiguity_count 0):
the 16 raw / 8 served border candidates vs 6 tree leaves are POSITIVELY
explained (10 extras = collinear border subdivision points, corner-vs-
collinear turn-sin margin 0.652 vs 2.4e-8); head = v25 by radius band
(0.3890 in 0.4±10%, all others ≤ 0.3245); leg pairs are EXACT diagonal
mirror pairs ≤ 1e-6 — front {v13,v18}, back {v12,v16}; tail v14; two
M/V-degree-6 hubs (raw v5 front / v11 rear), bone origin = nearest hub
(margins ≥ 2.4x, stated never silently picked).

| group | unshaped | fox target | gap | shaped (post-op) | delta |
|---|---|---|---|---|---|
| front | 64.8289 | 134.8316 | -70.0027 | 61.8116 | -3.0172 |
| back | 36.4591 | 138.6544 | -102.1953 | 110.5045 | +74.0454 |
| head | 37.4003 | 137.7186 | -100.3183 | 84.5526 | +47.1523 |
| tail | 46.2640 | (none — fox tail dropped by pinned rule) | — | 49.4388 | +3.1748 |

Actuation datum: `reverse:0.0,0.46801304:0.12398308661620648:105.0` on
v18 (front leg, longest named-leg axial 0.247966; θ=105 per the 90-guard;
d = 0.5·axial). Op ACCEPTED; unshaped disp 1.5885, shaped disp 1.1920.
The actuated tip's OWN angle-vs-head delta: **-1.1093 deg** (~12x the
~0.09 derived-quantity drift band — real, but ~1% of the 70–102 deg
gaps). The NON-actuated back legs jumped +61.5853 / +86.5055 → the back
GROUP moved **+74.0454 deg TOWARD its fox target (gap -102.20 → -28.15)**
from a single front-leg op.

**READING (the global-coupling finding):** on a compiled base, a
tip-local op barely moves its own joint — the dominant, frame-invariant
effect is a GLOBAL re-land of the folded equilibrium (the shared head
reference bone itself swings; slice-3's cross-coupling amplified ~100x on
a multi-molecule base). Pose control on compiled bases is a
global-coupling problem, not tip-local reachability — **B5's tip-local
reachability wall may be the wrong abstraction on real bases**; a fit
driven by whole-pose deltas could exploit the coupling instead of
fighting it.

## ⚠ Standing tripwire: the shipped 2e-4 kick is MARGINAL

The Gate-3 session measured TRANSIENT PARKS at the shipped amplitude: the
unshaped served-dog capture parked at 0.0000 twice, then folded 1.5885 on
attempt 3 (attempt trail first-class in probe_dog_pose.out.json
`capture_attempts`; 4 page-load bursts in the log corroborate) — while
probe_dog_folds PASSed (1.5885 / 0.8057) interleaved in the same session.
Parked reads at 2e-4 are REAL and intermittent, not a one-off.

- **probe_dog_folds.py is the standing tripwire** — run it whenever the
  served path, the bridge, or a new compiled pattern is touched; a SINGLE
  parked read at 2e-4 is expected noise, a PERSISTENT park (all 3 bounded
  attempts parked) is the regression signal.
- Root cause is DEFERRED: why the Knuth/Weyl pattern is dog-degenerate at
  1e-4 and flaky at 2e-4 is not understood (quasi-periodic hash structure
  interacting with TreeMaker vertex ordering is the suspect). The
  diagnostic recipe (pattern-vs-path isolation via flat-y-extent +
  Python-side replay) is in `.superpowers/sdd/task-5-report.md`.
- Named follow-up options: amplitude bump (margin the kick well past the
  degeneracy), a different hash/jitter pattern (Mersenne folded the dog
  at 1e-4 where Knuth did not), or a bridge-side re-kick-on-park (detect
  zero displacement after load and re-lift).
- Consumers of captures at this amplitude should use the Gate-3 pattern:
  bounded 3-attempt retry scoped to "did not fold", EVERY attempt logged
  (re-measurement, not pass-fudge). probe_dog_folds and
  test_sim_regression now build this retry in.

## Next-slice entry points (cheapest first)

1. **Kick robustness hardening.** Root-cause the Knuth 1e-4 dog-degeneracy
   / margin the amplitude, or ship one of the named alternatives
   (different pattern, re-kick-on-park). Small, fully instrumented
   already (probe_dog_folds + the task-5 diagnostic recipe), and it
   retires the one ⚠ this slice ships with. The case for it: the fix is
   product-path (every served model crosses it) and the measured
   transient parks mean "served model didn't fold" WILL recur
   intermittently until the margin is real.
2. **Reopen B5 on the compiled dog, exploiting global coupling.** The
   Gate-3 datum (single front-leg op moved the back group 74.05 deg
   toward target) says pose-relevant angles on a compiled base ARE
   reachable — just not locally/independently. A whole-pose objective
   (score all groups jointly per op, not per-tip stages) inverts the
   slice-3/4 failure mode into the mechanism that does the work. All
   machinery exists (coordinate_descent, pose_target grouping,
   probe_dog_pose's guards + retry pattern). The case for it: this is
   the actual product payoff (posing real compiled animals), and the
   B5 cap was explicitly conditioned on the star toy's wall — which
   Gate 3 just undermined.
3. **The raw-vs-served asymmetry question.** Why does the raw hull
   self-start while the completed square parks? Pure curiosity, cheap
   probe (e.g. measure initial per-vertex force imbalance or boundary
   asymmetry across the existing 9-fixture matrix; hshape_squared is the
   folding-squared control). The case for it: it is the one OPEN
   hypothesis in the root-cause story, and confirming it would predict
   WHICH future patterns park (symmetric frames) instead of finding out
   at capture time.

## Gotchas carried forward

- **Standing (all prior slices, still true):** SimSession is HEADED
  (headless WebGL dead on this machine); playwright lives in
  `mcp_harness/.venv` ONLY; probe outputs (`*.out.json` / `*.out.log` /
  suite logs) stay uncommitted; crimp θ=90 silently mis-targets (guard
  untouched — use 75/105); solver drift per-capture ~1e-5–0.02 deg and
  up to ~0.09 on derived quantities → no 0.0 tolerances, strict-< gates
  need margin >> 0.1, measure-then-pin every constant.
- **Process discipline (now TWICE-proven this slice, Tasks 2 and 4):**
  subagent-launched BACKGROUND processes are orphan-killed when the
  subagent turn ends; long sim runs must be controller-launched nohup or
  run foreground with an explicit timeout. Run-2 rows observed before
  the kill matched the surviving run verbatim — the kill loses the run,
  not the physics.
- **dist is gitignored → the public→dist cp is load-bearing.** Only
  `web/frontend/public/simulator/js/ide-bridge.js` is tracked; SimSession
  serves `dist`. A stale dist fails as "did not fold" — implicating
  physics when the cause is a missing copy. Re-cp after EVERY bridge
  edit; test_sim_regression's byte-equality preamble now guards this
  (m15, shipped).
- **The z-lift breaks 3D scale-ratio integrity checks downstream.**
  Capture flat_coords are no longer coplanar (measured spread 3.5e-4 on
  a 0.0079-apart vertex pair); the pattern is: verify the lift axis is
  small, then project to scene X-Z (the recorded paper plane) before any
  ratio/registration check — see probe_dog_pose (i1). Even projected,
  float32 GPU coords add ~1e-7 absolute quantization that breaks
  RELATIVE 1e-6 ratio rules on close pairs — use an ABSOLUTE residual
  bound with the correct null model (i2).
- **fold.js `sort_vertices_vertices` is 2D-only** — a bare 3-coord fold
  can never load through the bridge (audit throws; real path posts
  {type:'error'} = IMPORT-DEAD). Pre-derive faces_vertices while still
  2D (`fold_mutate.interior_faces` is verified exact-equal to the
  browser derivation).
- **pattern.js is y-up and consumes 3-coord folds AS-IS** ((x,y)→(x,0,y)
  for 2-coord): any FOLD-spec `[x,y,z]` handed to the sim must be
  permuted to `[x,z,y]` or the paper is rotated into the wrong plane.
- **Marginal-kick captures need the retry pattern** (bounded, scoped to
  "did not fold", every attempt logged) — see the tripwire section; a
  single parked read at 2e-4 is expected noise, a persistent park is a
  regression.
