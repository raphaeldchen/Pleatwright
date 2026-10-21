# B5-PRIME: whole-pose fit on the served compiled dog — design

**Status:** COMPLETE 2026-07-12 — ALL GATES PASSED; routing verdict (a)
**B5 REOPENED**. Winner = ONE product-applicable op
(`outside:0.0,0.46801304:0.12398308661620648:142.5` on front_v18):
whole-pose error 272.49 → 119.14 (re-measured ×3) vs bar 144.34. Gate 2
measured composition ANTI-ADDITIVE (calibration median 127° → the
pre-pinned descent downgrade fired; no sequence beat the single op); front
group −81.6° residual = the vocabulary ceiling → next slice = B5-prime-2
front-residual steering. Gate 2b unmeasurable on quad (naming disarmed at
Gate 0). New kick-tripwire evidence: back_v12 park-degenerate under the
2e-4 kick while its mirror twin scores. Full record:
`docs/superpowers/2026-07-12-handoff-b5-prime-outcome.md`.
(Original banner: APPROVED 2026-07-11 — brainstorm gates answered by the
user; all constants below are pinned unless marked informational.)
**Branch:** `feat/b5-prime-whole-pose` off main `3d2963d` (PR #35 merge —
verified before branching). Never named "slice5" (that name belongs to the
unmerged rigid-fold spec on `feat/b5-rigid-fold-slice5`, which stays
READ-ONLY reference for this slice).
**Predecessors:**
`docs/superpowers/2026-07-11-handoff-flat-equilibrium-outcome.md` (Gate-3
payoff table, marginal-kick tripwire),
`docs/superpowers/2026-07-09-handoff-b5-slice4-outcome.md` (the B5 cap,
resume-regression lesson, drift band).

## 1. Mission and reopen thesis

Reopen B5 — pose-fitting a base toward the fox skeleton — on the SERVED
compiled dog with a WHOLE-POSE objective that exploits global coupling.

The slice-4 cap was measured on hand-built star bases with a
per-group/tip-local search. PR #35 changed both premises:

1. The served compiled dog now folds in the sim (flat-equilibrium root
   cause fixed via the bridge z-lift; disp 1.5910).
2. Its Gate-3 actuation datum showed a tip-local op barely moves its own
   joint (−1.11°) while global re-equilibration swings OTHER groups
   massively toward target (back +74.05°, head +47.15° from ONE front-leg
   reverse).

**The thesis in one number:** unshaped served-dog whole-pose error vs fox
targets = **272.52°** total (front |134.8316−64.8289| = 70.00, back
|138.6544−36.4591| = 102.20, head |137.7186−37.4003| = 100.32; tail
EXCLUDED by the pinned fox tail-drop rule). The single un-optimized Gate-3
op (`reverse θ=105, d=0.5·axial` on v18) moved the total to **154.34°** —
−118° from one accidental op. Slices 3/4 treated cross-coupling as the
failure mode; on a compiled base it is the mechanism. A search scored on
TOTAL error should exploit it deliberately.

## 2. Decisions already made (not relitigated here)

- **Substrate** = the SERVED display dog, exact product path:
  `raw = tests/goldens/dog.fold` (byte-identical to `docs/dog.fold`) →
  `square_complete.complete_square(raw, 1.0, 1.0)` →
  `shaping.apply_display_ops(sq, ops, raw=raw)`. Never the raw hull.
- **Objective** = whole-pose TOTAL angle error across {front, back, head}
  vs fox targets: `pose_target.angle_error(achieved, targets)`, the
  `pose_target.angles_from_bones` 3-angle representation, bone vector =
  folded tip − folded NEAREST hub (the probe_dog_pose construction). Fox
  targets by live `starhead.fox_targets()` extraction with the recorded
  fallback (front 134.8316 / back 138.6544 / head 137.7186). Tail dropped
  on the target side by the pinned rule; the tail FLAP remains a legal
  actuator (an unscored control input).
- **Op vocabulary** = existing tool layer only: `reverse`, `outside`,
  `reverse_deep`, crimp (= the `shaping.crimp_ops` reverse+outside pair —
  a measured OFFSET knob, direction-neutral by slice-4 measurement). No
  new fold primitives, no new MCP tools, no agent-prompt or UI work.
- **Reach** = probe/harness/data layer ONLY. No `ide-bridge.js` or
  vendored-sim edits; if a bridge change ever looks necessary, HALT and
  ask (that is kick-hardening scope, a different slice).
- **Rigid-fold instrument** (`feat/b5-rigid-fold-slice5`): read-only
  reference. Do not merge, import, or build `solve_closure`/`tip_vectors`
  — the rigid engine is gated on THIS slice's Gate-3 verdict.

## 3. Architecture (approved approach A)

Two new pytest-covered pure modules + the named `sim_capture` port +
three thin probe drivers. This mirrors the repo's proven layering:
`pose_target`/`pose_search` are pure+pytest-covered, `starhead`/
`sim_capture` are probe support — that boundary survived four B5 slices.

### 3a. `mcp_harness/pose_base.py` (new, pytest-covered, no sim imports)

`NamedBase` — guarded naming + op construction for compiled
multi-molecule bases (the `StarHeadBase` idea, generalized). Built from
`(raw_fold, squared_fold, config)`:

- **Naming pipeline** (extracted from `probe_dog_pose.py`, semantics
  preserved): border-cycle corners → per-corner tangency radii → head
  naming → exact mirror pairs (tol 1e-6) → nearest-hub association
  (margin ≥ 2×) → `pose_target.group_tips_by_head` cross-check. EVERY
  guard failure appends an ambiguity flag; naming never guesses.
- **Head rules** (config-selected):
  - `radius_band` (dog): tree-frame radius (paper radius /
    `frame_title` scale) in 0.4 ± 10% band, all others ≤ 0.35 — the
    recorded Gate-3 rule, unchanged.
  - `relative_radius` (quad — it has NO `frame_title` scale): with
    m = median paper radius over leaves, head candidates = leaves with
    r ≥ 1.2·m; PASS iff exactly one candidate AND every other leaf
    ≤ 1.1·m; anything else → head AMBIGUOUS (2b disarmed, honestly).
- **Mirror axes are per-base config**: dog = [diagonal x↔y,
  anti-diagonal] (frozen — parity with the recorded Gate-3 grouping);
  quad = the four canonical square symmetries (x↔y, anti-diagonal,
  x→1−x, y→1−y). Guard unchanged: exactly ONE axis yields a clean
  2-pairs+rest split, else AMBIGUOUS.
- **Sites**: named actuator sites keyed `role_vN` (e.g. `front_v18`),
  each carrying flat xy (squared-frame 8dp-snapped), first-axial-segment
  length (`starhead._tip_axial_len` semantics), role, nearest hub.
- **Op construction**: `site_op(site, kind, theta, frac[, f2]) → [op
  strings]` with d = frac × that site's first axial segment; crimp emits
  the `shaping.crimp_ops` pair; θ=90 structurally excluded (grids never
  contain it; `crimp_ops` guard untouched).
- **Strict apply**: one op at a time with object-identity refusal
  detection (the `starhead.apply_ops` pattern); a crimp unit is atomic —
  either half refused ⇒ the unit is refused.

Dog parity requirement (pytest, no sim): `NamedBase` on the tracked
golden must reproduce the recorded Gate-3 grouping EXACTLY — corners
{v12, v13, v14, v16, v18, v25}, head v25, front {v13, v18}, back
{v12, v16}, tail v14, hubs raw v5/v11, ambiguity_count 0. If the 4-axis
quad config would break dog parity, the dog keeps its 2-axis config
(axes are per-base precisely so parity is never at risk).

### 3b. `mcp_harness/pose_coupling.py` (new, pytest-covered, sim-free)

Evaluators are injected callables, exactly the `pose_search.py`
philosophy:

- `CouplingRow` / `CouplingTable`: one row per Gate-1 cell — cell key
  (site, kind, θ, frac[, f2]), op strings, verdict
  (`scored | refused | parked | error`), per-leaf angles, group angles,
  total error, Δtotal vs baseline, disp, attempt trail, session id.
  JSONL append + round-trip; `resume_keys()` so a restarted run skips
  already-scored cells.
- `predict(table, seq) → predicted Δgroups/Δtotal`: ADDITIVE composition
  over measured single-op rows (superposition hypothesis; no off-grid
  interpolation).
- `propose(table, incumbents, width, depth_cap, base) → candidate
  sequences`: beam expansion ranked by predicted total, structurally
  enforcing the sequencing law (≤ 1 deep op per sequence, deep op always
  placed FIRST; extensions append tip-local ops, prepend a deep op only
  when none exists), then geometry-prefiltered by actually applying the
  ops in pure Python (refused sequences never reach the sim).
- `calibration(pairs) → median |predicted − measured| Δtotal` + the
  pinned decision: median ≤ 15° keeps the beam; else DOWNGRADE to
  descent (documented in the probe output).
- `descent_schedule(table, base, incumbent) → pose_search
  coordinate_descent schedule`: 6 site-stages, axes = that site's top-6
  table ops + `none` + the incumbent's current op for that site — the
  incumbent is IN the axes, so a pass can only improve (the slice-4
  resume-regression lesson made structural).
- Reported summaries (informational): |Δgroup| heatmap by (site, kind);
  SVD rank-1 energy share of the op×group response matrix.

### 3c. `sim_capture.py` additions (probe support, the named follow-up)

Port from `probe_dog_pose.py`: `tracked_points_lifted(fold, cap,
targets)` (lift-axis verification + scene X-Z projection + ABSOLUTE
residual bound 1e-4 — the z-lift breaks the coplanar relative-ratio
check) and `capture_checked(sim, fold, attempts_log, attempts=3)`
(bounded retry scoped to "did not fold" ONLY, EVERY attempt logged —
re-measurement, never pass-fudge). Unit-testable with mock captures.
`probe_dog_pose.py` switches to the shared versions ONLY after a dry-run
parity check reproduces its recorded naming/targets output; if parity
fails, it keeps its private copies and the failure is recorded.

### 3d. Probe drivers (thin, report-only, outputs uncommitted)

- `probe_dog_coupling.py` — Gate 0 baseline mode (`--gate0`) + Gate 1
  matrix; incremental JSONL, resumable by cell key, chunked runs.
- `probe_dog_beam.py` — Gate 2 (calibration wave, beam waves,
  refinement, or the descent fallback).
- `probe_quad_recipe.py` — Gate 2b (conditional).
- `probe_dog_folds.py` — existing tripwire, re-run UNTOUCHED in Gate 0.

Name note: `probe_pose_sensitivity.py` already exists (slice-1 star-4
chamfer probe) — Gate 1 deliberately does not reuse that name.

## 4. Gate structure (all constants pinned)

### Gate 0 — preflight (MANDATORY FIRST; ~10 captures)

1. Verify main tip `3d2963d`; work on `feat/b5-prime-whole-pose`.
2. Re-run `probe_dog_folds.py` under the merged bridge (dog gated ×3
   bounded attempts, quad secondary). PERSISTENT park (3/3) on the dog →
   **slice HALT** — reroutes the roadmap to kick hardening.
3. Unshaped served-dog pose baseline **×3** (grouping + angles via
   `pose_base` + the ported capture helpers). Requirements:
   ambiguity_count == 0 (else HALT — never search on misnamed groups);
   expected total ≈ 272.52 within the derived-quantity drift band. The
   MEAN of the 3 totals becomes THE baseline for every Δtotal in this
   slice.
4. **Dry quad naming feasibility (0 captures)**: `NamedBase` on
   `quad.fold` with the `relative_radius` head rule + 4-axis mirror
   config → arms or disarms Gate 2b. Recorded either way.
5. Star-4 anchor opens EVERY sim session (disp in 1.0..1.6); a failed
   anchor refuses all verdicts from that session (rows tagged).

### Gate 1 — empirical coupling map + sensitivity model (~170 captures)

The approved single-op matrix, per site × 6 sites (head_v25, front_v13,
front_v18, back_v12, back_v16, tail_v14 — tail is an unscored actuator):

| kind         | θ grid                  | depth grid            | cells/site |
|--------------|-------------------------|-----------------------|------------|
| reverse      | {60, 105, 142.5, 170}   | frac {0.35, 0.5, 0.65} | 12        |
| outside      | {60, 105, 142.5}        | frac {0.35, 0.5, 0.65} | 9         |
| reverse_deep | {105, 170}              | frac {0.5, 1.25}       | 4         |
| crimp        | {105} (f = 0.5)         | f2 {0.35, 0.65}        | 2         |

27/site × 6 = **162 accepted-capture ceiling**. frac = d / (site's first
axial segment). reverse_deep frac 1.25 is the beyond-segment
through-layers regime (plain reverse refuses there) — deliberately
included; the op is untried in the pose context. Refusals are recorded
rows and cost NO capture. Every accepted cell records per-leaf angles,
group angles, total, Δtotal vs the Gate-0 baseline mean, disp, attempt
trail. Cell verdicts: `scored | refused | parked (3/3) | error` — a
parked or errored CELL is recorded and skipped, never scored and never a
slice halt (only the unshaped dog's persistent park is the tripwire).

Cross-session drift datum: the Gate-3 accidental op is the in-grid cell
(front_v18, reverse, 105, 0.5) — its re-measured Δ vs the recorded
+74.05/−1.11 numbers is reported (informational).

Budget: ≤162 matrix + session anchors + 1 mid-matrix unshaped baseline
challenger ≈ 170. Chunked into ~4 resumable runs.

**Gate-1 PASS (pinned):** ≥ 8 accepted ops with |Δtotal| ≥ 10° AND ≥ 1
op with Δtotal ≤ −10° (an improver must exist). Else **HALT** → B5
re-capped with compiled-base evidence (a successful slice outcome).
The sensitivity model (table + heatmap + SVD share) is REPORTED either
way; its quality is informational and never a Gate-1 pass criterion.

### Gate 2 — whole-pose search (~130 captures)

- **Wave 0 = additivity calibration**: the top-8 predicted PAIRS
  (geometry-accepted) are measured; median |predicted − measured| Δtotal
  ≤ 15° keeps the coupling-guided beam; worse fires the pre-pinned
  DOWNGRADE to incumbent-safe coordinate descent (schedule per 3b;
  1–2 passes ≈ 48–96 captures; which path ran and why is documented).
  Wave 0's captures double as the first search wave.
- **Beam loop**: width 4 incumbents; each wave measures ~10 new
  geometry-accepted sequences ranked by predicted total; depth cap 3,
  **depth 4 pre-authorized** if the latest wave improved the best total
  by ≥ 10°; pair-symmetric ops need no special casing (a symmetric pair
  is a depth-2 sequence — the pre-authorized mirrored-pair extension
  arises naturally). An incumbent is a MEASURED sequence with its score;
  waves can replace it only with something measured-better — nothing is
  ever re-searched on a grid that cannot represent it.
- **Stop**: wave gain < 10° or the budget line.
- **Refinement**: ±half-grid-step on θ and frac for each op of the best
  sequence, coordinate-wise, incumbent always in the axes (~18 captures).
- Budget: 8 calibration + ~4 waves × 10 + ~18 refinement + 2 baseline
  challengers + session anchors ≈ 130.

**Gate-2 PASS (pinned):** best measured total < **144.34** (= the
recorded Gate-3 single-op datum 154.34 − the 10° readability margin;
per-capture drift ~0.09 is negligible against it). Reported alongside
(informational): delta vs the best Gate-1 single (did composition beat
the best single op or only tie it?), vs unshaped 272.52, per-group
residual gaps.

### Gate 2b — generalization check on quad_squared (informational; ~45)

Conditional on the Gate-0 dry naming check; if disarmed, reports
"unmeasurable on quad" and its budget returns to Gate 2.

- Mini-matrix: reverse-only, θ {60, 105, 170} × frac {0.35, 0.65} ×
  ≤ 6 nameable sites ⇒ ≤ 36 accepted ceiling.
- One beam wave: top-6 predicted pairs; ONE more wave pre-authorized if
  wave 1 improved total by ≥ 10°.
- Quad unshaped baseline ×2; same fox targets, same tail-drop rule if a
  tail names.
- Report (no hard gate): quad coupling table, best sequence, Δtotal,
  and whether the coupling structure resembles the dog's — verdict
  `generalizes | dog-specific | unmeasurable`.

### Gate 3 — payoff + routing verdict (~5 captures + reserve)

- Winner re-measured **×3** (challenger discipline — the payoff table
  rests on re-measurement, not the search-time read).
- Payoff table: best sequence (op strings — directly product-applicable
  via the display pipeline's `ide_shape_ops`), per-group
  achieved/target/gap, totals vs 272.52 / 154.34 / 144.34.
- **Routing verdict** (exactly one, with the measured case):
  (a) coupling exploitable + search converging → **B5 REOPENED**, name
  the next slice;
  (b) coupling exploitable but the search plateaus above the bar or the
  model implies unreached improvements → the measured case for the
  rigid-fold instrument (the gated `feat/b5-rigid-fold-slice5`
  proposal);
  (c) ceiling measured below target → **B5 re-capped** with
  compiled-base evidence, stronger than the star-base wall.
  All three are successful slice outcomes (honest-outcome rule).

## 5. Capture budget (25 s/capture; ceilings — refusals cost nothing)

| gate    | ceiling | content                                            |
|---------|---------|----------------------------------------------------|
| Gate 0  | ~10     | anchor + tripwire re-run + unshaped baseline ×3    |
| Gate 1  | ~170    | matrix ≤162 + anchors + mid-matrix challenger      |
| Gate 2  | ~130    | calibration 8 + ~4×10 waves + refine ~18 + extras  |
| Gate 2b | ~45     | mini-matrix ≤36 + beam wave(s) + quad baseline ×2  |
| Gate 3  | ~5      | winner ×3 + baseline                               |
| reserve | ~40     | parked-read retries, contingencies                 |
| **total** | **~400** | ≈ 250–330 expected after refusals; ~3–3.5 h headed sim |

## 6. Data flow and instrument-grade bookkeeping

- Every capture appends ONE JSONL row (gate, cell key or sequence id, op
  strings, attempt trail, disp, angles, totals, session id, anchor
  status). Probe outputs (`*.out.json` / `*.out.jsonl` / `*.out.log`)
  stay UNCOMMITTED.
- Resume-by-key: restarted runs skip scored cells; a killed run loses
  nothing.
- Long sim runs are CONTROLLER-launched (nohup, or foreground with an
  explicit timeout) — subagent-launched background processes are
  orphan-killed at turn end (twice proven).
- Baseline challenger cadence: Gate-0 ×3, mid-Gate-1 ×1, Gate-2 ×2,
  winner ×3.
- Durable progress in `.superpowers/sdd/progress.md` (uncommitted).

## 7. Error handling and HALT semantics

- Failed naming guard → ambiguity flag → HALT before any search
  (Gate 0 requires ambiguity_count == 0 on the dog).
- Persistent park (3/3): on the UNSHAPED dog → slice HALT (probe_dog_folds
  tripwire territory / kick-hardening reroute). On a SHAPED cell → the
  cell is recorded `parked` and skipped.
- Refused ops: recorded rows, never scored, zero capture cost.
- Margins: every strict comparison carries the 10° margin (≫ the ~0.09
  derived-quantity drift band); additivity threshold 15°; NO 0.0
  tolerances anywhere; measure-then-pin any new constant.
- Anti-vacuous guard on every sim assertion (disp > 0.1, 0 NaN, vertex
  parity via `expect_verts`).
- θ=90 excluded by grid construction; the `crimp_ops` guard untouched.
- Any apparent need to touch ide-bridge/vendored sim → HALT and ask.
- `dist/` is gitignored: nothing in this slice touches simulator/public,
  but if any such file ever changes, the public→dist cp is load-bearing.

## 8. Testing

- **pose_base (pytest, no sim)**: dog-golden parity (the exact recorded
  Gate-3 grouping, ambiguity 0); quad naming outcome pinned from the
  Gate-0 dry check; synthetic guard-failure fixtures (each guard fires);
  site_op strings parse via `shaping.parse_op`; strict-apply refusal
  detection; crimp atomicity.
- **pose_coupling (pytest, mock evaluators)**: JSONL round-trip + resume
  keys; additive predictor on synthetic rows; proposal generator honors
  deep-op-first/≤1-deep and width/depth caps and geometry prefiltering
  (injected apply); calibration stats + the 15° downgrade decision;
  descent schedule includes incumbent + none; an end-to-end mock beam
  run finds the known optimum of a synthetic coupling world.
- **sim_capture ports**: unit tests with mock captures (lift-axis
  violation, absolute-residual failure, retry logging, fail-fast on
  non-park errors).
- Full backend suite stays green: baseline **454 passed / 4 skipped**;
  new tests are additive. Opt-in `RUN_SIM_REGRESSION` untouched.

## 9. Process and house rules (binding)

- Human merges every PR — ASK before any push.
- SimSession is HEADED (headless WebGL dead on this machine); playwright
  lives in `mcp_harness/.venv` ONLY.
- Gate-per-package task sizing in the plan; controller checkpoints
  between gates; the pre-authorized contingencies are ONLY those named
  here (pair-symmetric sequences, beam depth 4, the extra 2b wave, the
  descent downgrade) — anything else returns to the user.
- Handoff doc at slice end; spec status banner updated with the outcome.
- Honest-outcome rule: a measured NO at any gate, written up, is a
  successful slice.
