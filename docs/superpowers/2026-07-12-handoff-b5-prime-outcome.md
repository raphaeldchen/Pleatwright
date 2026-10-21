# B5-PRIME outcome handoff — whole-pose fit on the served compiled dog

**Date:** 2026-07-12 · **Branch:** `feat/b5-prime-whole-pose` · **Spec:**
`docs/superpowers/specs/2026-07-11-b5-prime-whole-pose-design.md` · **Plan:**
`docs/superpowers/plans/2026-07-12-b5-prime-whole-pose.md`

## ROUTING VERDICT: (a) — B5 REOPENED

Whole-pose shaping on the served compiled dog **works and passed every
gate**: coupling is exploitable (one tip-local op cuts the whole-pose error
from 272.49° to a re-measured 119.14°, −56%) and the search converged well
under budget. The winning recipe is a SINGLE product-applicable op —
`outside:0.0,0.46801304:0.12398308661620648:142.5` on the front-left leg
tip (site `front_v18`, θ=142.5, d=0.5·axial) — directly usable via the
display pipeline's `ide_shape_ops`.

**Named next slice:** *B5-prime-2 — front-residual steering.* The measured
ceiling of the current vocabulary is the FRONT group (−81.6° residual, see
payoff): the op×group response matrix is ~rank-1 (share 0.915 — every op
swings back+head together while front barely moves), and composition is
anti-additive (see Gate 2), so no sequence of tip-local ops reaches the
front target. The next slice asks whether ANY intervention moves front
without unwinding back/head — candidate levers: deep ops at the rear hub,
symmetric front-pair units treated as atomic actuators, moderated
amplitudes, and the rigid-fold instrument (`feat/b5-rigid-fold-slice5`,
still read-only) as the analysis tool for *why* the equilibrium re-land
pins the front group. This routing gives the gated rigid instrument its
measured case as an analysis tool inside a reopened B5, not as a rescue.

## Payoff table (winner ×3 re-measurement, Gate 3)

Winner: `front_v18 | outside | θ=142.5 | frac=0.5` (Gate-1 cell, unbeaten
by any measured composition or refinement).

| group | achieved (mean of 3) | fox target | gap |
|---|---|---|---|
| front | 53.24 (57.98 / 50.86 / 50.89) | 134.8316 | **−81.59** |
| back  | 145.50 (148.20 / 144.55 / 143.75) | 138.6544 | +6.85 |
| head  | 107.01 (112.70 / 102.28 / 106.06) | 137.7186 | −30.71 |

Totals: **119.14 mean** (111.41 / 125.30 / 120.69) vs unshaped **272.49**
(Gate-0 mean, 3 reads within ±0.28) vs the recorded Gate-3 single-op datum
**154.34** vs the Gate-2 pass bar **144.34**. Every individual re-read
passes the bar.

⚠ **New drift datum:** shaped-fold re-reads spread ~±7° (111.4–125.3)
versus the unshaped baseline's ±0.28 — the equilibrium re-land is itself
noisy. Single-capture cell deltas in the Gate-1 table carry this
uncertainty; the slice's 10° margins and the 100°+-scale headline deltas
dwarf it, but future gates comparing shaped reads at <10° resolution must
re-measure ×3.

## Gate-by-gate record (all numbers in the uncommitted probe outputs)

- **Gate 0 (PASS):** tripwire probe_dog_folds dog 1.5931 attempt 1/3;
  naming ambiguity 0 (grouping == recorded Gate-3 exactly); fox targets
  live-extracted; baseline ×3 = 272.5182/272.7141/272.2418 → mean
  272.4914. Quad dry naming **DISARMED** Gate 2b (3 border corners vs 6
  expected leaves AND 0 clean mirror axes — two independent guards).
- **Gate 1 (PASS, decisively):** full 162-cell matrix terminal — 114
  scored / 12 refused / 36 parked / **0 errors** (the summary json's
  `error: 1` is the gate0 quad-disarm marker row, which `_summarize`
  counted across all gates; final-review correction). 99 cells
  |Δtotal| ≥ 10° (bar
  8); 85 improvers ≤ −10° (bar 1). Best single −165.03°
  (`front_v18|outside|142.5|0.5`). rank-1 share **0.915**. Drift datum
  cell re-measured within ~1.5° of the recorded PR-#35 numbers
  (cross-session). Mid-matrix challenger 273.44 vs 272.49 (+0.95, inside
  the ±1.0 band — tight; cross-session baseline drift ~1°).
- **Gate 2 (PASS):** additivity calibration median |pred−meas| =
  **127.11°** (7 pairs) ≫ 15 → the pre-pinned DESCENT DOWNGRADE fired.
  Measured mechanism: pairs OVERSHOOT (best-predicted pair measured 204.7
  vs predicted 95.5) — each single op re-lands the global equilibrium
  nearly fully, so a second op pushes back/head past target. Descent (19
  scored, 5 parked) + half-step refinement (3 off-grid cells + 3 seqs)
  found nothing beating the single op. 38 captures of the 130 ceiling.
- **Gate 2b:** unmeasurable on quad (disarmed at Gate 0; no captures).
- **Gate 3:** winner ×3 above; verdict (a).

## Measured findings beyond the gates

1. **Kick mirror-asymmetry (escalates the PR-#35 m16 tripwire):**
   `back_v12` parked 3/3 on 25/27 tip-local cells (zero scored) while its
   EXACT mirror twin `back_v16` scored 23/27. Discriminated against
   session death by a fresh-session re-read (anchor healthy at 1.309;
   back_v12 still parks). The deterministic 2e-4 bridge kick pattern is
   not mirror-symmetric; back_v12-shaped folds are park-degenerate.
   Consequence: one of six actuator sites is invisible to the search.
   Kick-hardening remains its own (already-chartered) follow-up; this is
   its strongest datum yet.
2. **Anti-additive composition** is the headline negative: on a compiled
   base the global re-land SATURATES — one op captures nearly all
   reachable improvement; sequences overshoot. "Search over sequences" is
   the wrong frame for this substrate; "pick the best single recipe, then
   steer the residual" is the measured frame.
3. **Budget:** ~285 sim reads total across all gates (incl. park retries
   ×3), vs the ~400 ceiling.

## Process notes

- Mid-slice, a parallel Codex session shared the main checkout and
  switched its branch; B5′ moved to the git worktree
  `.claude/worktrees/b5-prime` (user-approved). Nothing was lost; Task 7's
  commit was cherry-picked; all later work lives in the worktree. Copies
  needed in a worktree: `web/frontend/dist` (gitignored, load-bearing),
  `headless_treemaker*.so`, gate JSONLs, `.venv` symlink.
- One plan-authored Critical caught in review before it could burn a run:
  the descent path fed categorical (cell-key/None) axes into
  `pose_search.refine`'s float cast → fixed as index-space descent
  (commit `8cafce4`), verified against the real Gate-1 table sim-free.
- Suite: 481 passed / 4 skipped clean in the worktree (main checkout
  counts are contaminated by the parallel session's untracked tests).

## Follow-ups carried

- Kick hardening (existing charter; back_v12 asymmetry is new evidence).
- B5-prime-2 (front-residual steering) — the named next slice.
- Minors m1–m8 recorded in `.superpowers/sdd/progress.md` for the final
  review's triage.
