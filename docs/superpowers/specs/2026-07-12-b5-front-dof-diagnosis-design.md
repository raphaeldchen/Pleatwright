# B5-prime-2 — front-residual steering via rigidity diagnosis (Phase D)

**Status:** Phase D EXECUTED 2026-07-13 — verdict SEARCH GAP at first order
(r\* = 1.76, D2 calibrated (corrected truncated-span captured 0.904,
effective rank 2, falsifiable)) with reachability
UNCONFIRMED (pilot inconclusive as composed: the dominant hub_front context's
candidates all refused; 16/40 reads). Phase S scoping awaits the user
checkpoint — see `docs/superpowers/2026-07-13-checkpoint-b5-front-dof-phase-d.md`.
**Branch:** `feat/b5-front-dof`.
**Predecessor:** `docs/superpowers/specs/2026-07-11-b5-prime-whole-pose-design.md`
(B5-prime, merged PR #37 — verdict (a) B5 REOPENED; single-op winner
272.49° → 119.14°; front residual −81.6° is the vocabulary ceiling).
**Instrument lineage:** `docs/superpowers/specs/2026-07-10-b5-rigid-fold-solver-slice5-design.md`
(`feat/b5-rigid-fold-slice5`, promoted into this branch — see §2).
**Handoff:** `docs/superpowers/2026-07-12-handoff-b5-prime-outcome.md`.

## 1. The question this slice answers

B5-prime measured that the served/squared compiled dog's pose response to the
entire tip-local op vocabulary is near rank-1 (energy share 0.915): every op
swings back+head together while the front group barely moves, and composition
is anti-additive (calibration median |pred−meas| = 127° vs a 15° bar). The
front residual (−81.6° vs the fox target) is the measured ceiling.

**Is that residual a SEARCH gap (the right op/sequence exists in a wider
vocabulary and wasn't tried) or a STRUCTURAL one (this crease pattern has no
first-order folding freedom that moves front independently, so no op ever
could)?**

Two phases:

- **Phase D (diagnosis)** — sim-free except one conditional pilot gate —
  produces a CONFIRMED verdict. Fully specified here (§4).
- **Phase S (steering)** — branch-dependent; chartered (§5) but deliberately
  NOT detail-planned until Phase D's verdict is in. Scoped at the mid-slice
  checkpoint (§4, after Gate D3).

**Honest-outcome rule (carried from B5-prime verbatim):** both verdicts are
successful slice outcomes. A structural lock finding is a win, not a failure.

## 2. Decisions made during brainstorming (pinned)

1. **Codex coexistence.** The parallel Codex rigid-origami track (PR #36,
   `mcp_harness/rigid/`, gates R1–R4 pending) is active or likely active on
   the main checkout. Consequences: (a) this slice's gates are named
   **D0–D3** (no collision with Codex's R1–R4); (b) shared-checkout posture —
   never write to the main checkout; uncommitted inputs are COPIED into this
   worktree; (c) `rigid_fold.py` documents the Codex `rigid/` kernel as the
   eventual home for this math and flags the convention divergence.
2. **Instrument promoted.** `feat/b5-rigid-fold-slice5` (`rigid_fold.py`,
   `probe_folding_dof.py`, `test_rigid_fold.py`, its spec) merges into
   `feat/b5-front-dof` and rides this slice's PR. What exists is the
   *diagnostic subset* of the slice-5 spec (forward pass + first-order DOF
   count, math-anchored; the closure solve, `tip_vectors`, and the
   sim-anchored ladder step were never built). For DOF/direction analysis the
   math anchors are the right anchors — the compliant sim cannot validate
   rigid DOF anyway.
3. **Verdict asymmetry is pinned.** "Structural lock" (no front-selective
   first-order flex) is decisive: the null space is complete — every finite
   rigid motion's tangent is a first-order flex — and the 162-cell empirical
   map independently shows the compliant sim doesn't move front under
   tip-local ops either. "Search gap" (a front-moving flex exists) is only
   suggestive: flexes at the flat bifurcation may not extend to finite folds
   (a degree-4 vertex reads first-order dof 2 but folds with 1 finite DOF),
   and the display pipeline can only excite directions through ops. Hence the
   pilot gate (D3).
4. **Pilot gate, closure solve deferred.** No closure solver is built in this
   slice on any path where the pilot resolves cleanly. The Gauss-Newton
   closure solve (slice-5 spec Component 2) is the documented ESCALATION if
   the pilot dead-heats (front-moving flex exists, no pilot op excites it,
   and we cannot tell non-extension from unreachability apart). It is
   proposed at the checkpoint, never built unilaterally, and consuming
   Codex's R3 closure kernel is preferred over building a duplicate.
5. **Checkpoint after pilot.** Phase D ends with a confirmed verdict; the
   single user checkpoint presents verdict + evidence + proposed Phase S
   scope. Pilot sim spend before the checkpoint is small and pre-budgeted.
6. **Branch name** `feat/b5-front-dof` (fresh; no "b5-prime", no "slice5").

## 3. Approach (chosen over alternatives)

**Flex-space tip-coupling analysis.** Extract the null-space BASIS of the
rigidity Jacobian at the flat state on the served/squared dog (recorded DOF
count: 3 — `probe_folding_dof.out.json`, `rigid-fold` worktree), map each
basis direction to first-order tip motion, and ask directly: what is the most
front-selective direction the flex space contains? The flex space is complete,
so unlike the empirical matrix (which only sees directions the current
vocabulary happens to excite), a negative answer here closes the question for
ALL vocabularies of rigid folding ops.

Rejected alternatives: (a) empirical widened op matrix without rigidity —
100+ captures and a negative still can't distinguish search from structure;
(b) modal analysis of the compliant sim — ±7° re-read noise, headed captures
per data point, black-box mode extraction is its own research project. The
compliant-mobility concern both alternatives address is handled structurally:
D2 (cross-validation against measured data) and D3 (pilot) are where the
compliant world can overrule the rigid prediction.

## 4. Phase D gates (verdict rules pinned BEFORE measurement)

### Gate D0 — preflight

- Merge `feat/b5-rigid-fold-slice5`; full `make test` green. Baseline on main
  is 557 passed / 4 skipped (post PR #36); the merge adds the instrument's
  tests; new tests land on top of that.
- Re-run `probe_folding_dof.py`: instrument anchors must PASS (the probe
  refuses verdicts otherwise), and dog-squared must still read **dof = 3**
  (pinned regression vs the recorded output).
- COPY `probe_dog_coupling.out.jsonl` from the main checkout
  (`mcp_harness/probe_dog_coupling.out.jsonl`) into this worktree; it must
  reconcile to the handoff tallies: 162 gate-1 rows = 114 scored + 12 refused
  + 36 parked + 0 errors, and carry the fields D2 needs (per-group deltas).
- NamedBase naming parity on the served dog: grouping identical to B5-prime's
  recorded grouping, ambiguity 0 (existing `pose_base` guards).
- FAIL of any item → fix or HALT; no verdict work on a failed preflight.

### Gate D1 — flex-space tip coupling (sim-free verdict core)

New analysis on top of `rigid_fold.py` (see §6):

- `null_space_basis(fold)` — the flex basis from the SVD `folding_dof`
  already computes (expect 3 vectors on dog-squared).
- Per-direction first-order tip motion by CENTRAL finite differences of
  `fold_to_3d` along each basis vector. At the flat state a flex produces
  pure out-of-plane motion, so the observable is the **z-velocity of each
  named pose tip relative to its hub** (mirroring how `pose_target` builds
  bone vectors as leaf-minus-hub). Two step sizes, h = 1e-5 and h = 1e-6
  (radians along the unit flex direction); the two velocity estimates must
  agree within relative tolerance **1e-4** (generous vs expected ~1e-6
  numerical noise; never 0.0) or the gate FAILS as an instrument error.
- Group aggregation: front(w) = RMS of relative tip z-velocities over the
  front tips; likewise back(w), head(w). Tips/groups are exactly the
  B5-prime pose tips (front ×2, back ×2, head ×1); the sixth actuator site
  is not part of the pose objective and is excluded from signatures.
- **Front selectivity:** maximize r(w) = front(w) / sqrt(back(w)² + head(w)²)
  over unit w in the flex subspace — a closed-form generalized eigenproblem
  on 3×3 restricted quadratic forms (pure numpy: Cholesky reduction +
  `numpy.linalg.eigh`, no iteration, preserving `rigid_fold.py`'s numpy-only
  discipline). Report r* and the optimal direction w*.

**Pinned verdict rule:**

| reading | rule | meaning |
|---|---|---|
| SEARCH-GAP candidate | r* ≥ 1.0 | a direction exists whose front motion ≥ back+head combined; proceed to D2/D3 |
| STRUCTURAL LOCK | r* ≤ 0.2 | even the optimal direction moves back+head ≥ 5× more than front; the mechanism slaves front (decisive — flex space is complete) |
| GRAY | 0.2 < r* < 1.0 | weak candidate; proceed to D2/D3; checkpoint presents it explicitly as gray |

Degenerate guard: if front(w) < 1e-9 × total motion norm for ALL basis
directions → hard STRUCTURAL LOCK; D2's search-gap readouts are skipped.

Threshold rationale (recorded so the numbers aren't cargo-culted later): the
needed steering is front +81.6° while back (already on target, +6.85) stays
within the ±7° re-read noise; r* ≥ 1.0 means front-dominant actuation exists
that could plausibly be composed against the known global mode; r* ≤ 0.2
reproduces, from the mechanism side, the empirically measured slaving.

### Gate D2 — empirical cross-validation (sim-free, zero capture cost)

Calibrates the instrument against the world using data already paid for.

- Build the measured response matrix from the coupling table's 114 scored
  rows (signed per-group deltas); take its dominant mode m ∈ R³ (this is the
  recorded rank-1, share-0.915 mode).
- Predicted group-signature vectors ŝ_i ∈ R³ (one per flex basis vector,
  unsigned RMS aggregation as in D1). Compare sign-free: reduce m to
  elementwise absolute value; PASS if the fraction of |m|'s norm captured by
  the span of {ŝ_i} is ≥ **0.8** (|cos| between |m| and its projection).
- **Vacuity guard (pinned honesty trap):** if the 3×3 matrix of signatures is
  well-conditioned (smallest/largest singular value > 0.2 — the span is
  essentially all of R³), the test cannot fail by construction. The probe
  must detect and report **VACUOUS**: counts as not-failing, is flagged at
  the checkpoint, and D3 becomes the only real-world check.
- **Non-vacuous FAIL** → the flat-state proxy does not track the folded
  world → HALT to checkpoint with an "instrument uncalibrated" finding; no
  pilot capture is spent without user approval.
- Search-gap readout: project each measured row onto the predicted front
  direction w*'s signature; ops that already couple weakly rank the D3
  candidate list.

### Gate D3 — conditional pilot (fires ONLY on SEARCH-GAP or GRAY)

- Translate w* into candidate excitations: w* is a per-crease fold-rate
  vector; its large-magnitude components identify which creases must fold and
  in which sense. Candidates are ops from the EXISTING vocabulary
  (reverse/outside/reverse_deep/sink/crimp, incl. hub-deep and symmetric
  front-pair units treated as one recipe) whose crease sets overlap that
  support. **≤ 8 candidate recipes**, ranked by D2's coupling readout.
- Measured STANDALONE from the unshaped base (avoids the anti-additivity
  confound). The pilot re-reads its own unshaped baseline ×3 first (defines
  "toward target" signs from its own data, not stale numbers).
- **Budget: ≤ 40 sim reads total** (baseline ×3 + candidates ×3 re-reads +
  park retries ×3 under the persistent-park rule).
- **Pinned bar: CONFIRM = front group moves ≥ 20° toward the fox front
  target (mean of 3 reads)** — ~3× the ±7° shaped-re-read noise. Back/head
  co-motion (selectivity) is reported but not verdict-bearing: the known
  global mode barely moves front, so any ≥20° front motion is a new lever.
- No candidate confirms → verdict: **structural for practical purposes**
  (front-moving flex exists first-order but is unreachable by the vocabulary
  or does not extend); the closure-solve escalation goes on the checkpoint
  table.
- Controller-only sim runs (HARD rule — subagent-launched background sim
  processes get orphan-killed). `back_v12`-adjacent candidates carry the
  park-degeneracy caveat (one actuator site is invisible; see §5 triggers).

### Checkpoint (mid-slice, user-facing)

Presents: the confirmed verdict with the full gate record, D2 calibration
status (incl. VACUOUS if so), pilot table if run, and a PROPOSED Phase S
scope for the verdict's branch. Phase S work begins only on user approval.
If escalation (closure solve) is proposed, the consume-Codex-R3-vs-build
decision is made here.

## 5. Phase S charters (thin by design; detail-scoped at the checkpoint)

**Structural branch — give front a DOF at compile time.** Find the minimal
Metric-Tree/TreeMaker intervention (new flap, edge reweight, packing seed
change) whose compiled+squared output HAS a front-selective flex direction.
The promoted classifier is the pre-gate: a candidate tree must pass
`folding_dof` + D1 front-selectivity BEFORE compile-heavy iteration or sim
capture is spent on it (the Tier-2.5 "shielded compiler" pattern applied to
poseability). Honest scope note: this reaches into tree-drafting territory;
if compile-side work balloons beyond a small probe-driven search, the
checkpoint decision is to charter it as its own slice.

**Search branch — build the op that excites the confirmed direction.**
Vocabulary/coordination work targeted at w* (deep ops at the rear hub,
symmetric front-pair atomic units, moderated amplitudes), run with B5-prime's
proven structure: matrix → search → payoff, honest-outcome rule intact,
whole-pose objective unchanged (fox targets; 119.14 is the number to beat).
Budget set at the checkpoint (~400-read precedent).

**Named dependency triggers (either branch):**

- If pilot/Phase-S candidates need `back_v12` or get blinded by kick
  asymmetry on a front pair → kick-hardening graduates from parked follow-up
  to prerequisite; raise at the checkpoint, don't absorb silently.
- If excitation needs per-crease fold-angle targets the display pipeline
  cannot express → that is a bridge change → **HALT and ask** (house rule;
  the bridge should NOT need touching in this slice).

## 6. Code layout

- **Merged in:** `mcp_harness/rigid_fold.py`, `mcp_harness/probe_folding_dof.py`,
  `mcp_harness/tests/test_rigid_fold.py`, the slice-5 spec (status banner
  updated: promoted here).
- **Extended `mcp_harness/rigid_fold.py`:** `null_space_basis()`,
  `tip_flex_signatures()` (central FD, dual step-size guard),
  `front_selectivity()` (generalized eigenproblem). Docstring paragraph:
  Codex `rigid/` kernel named as the eventual home; convention divergence
  (mm/radians/hinge orientation there vs this module's) flagged.
- **New `mcp_harness/probe_front_flex.py`:** D0 anchor re-checks + D1 + D2 in
  one sim-free run; refuses verdicts on anchor failure (pattern from
  `probe_folding_dof`); writes `probe_front_flex.out.json` (uncommitted).
- **New `mcp_harness/probe_front_pilot.py`** (only if D3 fires): pilot driver
  on `pose_base`/`pose_coupling`/`sim_capture` — reuse, don't rebuild;
  controller-run, headed SimSession.

## 7. Testing

Pure numpy pytest for all sim-free work:

- `null_space_basis` on the degree-4 single vertex (known 2-dim flex
  structure) and star-4.
- Finite-difference signatures on a hand-derivable single-crease strip (tip
  z-velocity computable by hand — pins the sign convention the way strip
  fixtures pinned `flat_fold`'s M/V sign in layer-order slice 2).
- `front_selectivity` on synthetic flex spaces with known optimal ratios
  (eigenproblem must recover them).
- D2 alignment math on synthetic data INCLUDING the vacuous-span case and
  the non-vacuous fail case.
- The dual-step-size disagreement guard actually firing on a corrupted input.
- Dog-squared dof = 3 pinned as a regression test (data-layer, no sim).

No 0.0 tolerances anywhere; numerical tolerances pinned with margins ≫
observed noise. Full `make test` green before the checkpoint.

## 8. Process & logistics

- SDD as the merged slice: writing-plans → subagent-driven development,
  gate-per-package task sizing, fresh subagent per task with independent
  spec+quality review; **controller-only for any headed-sim run**.
- Worktree: `.claude/worktrees/b5-front-residual-rigidity-e47903` (this one).
  Copies needed: `probe_dog_coupling.out.jsonl` now; `web/frontend/dist`,
  `headless_treemaker*.so`, `.venv` symlink only if D3 fires.
- Shared-checkout posture throughout (Codex active): read-only access to the
  main checkout, never write there.
- Probe outputs (`*.out.json`/`.jsonl`/`.log`) and suite logs stay
  uncommitted. Playwright lives in `mcp_harness/.venv` only; SimSession is
  HEADED. `dist/` is gitignored; `cp public→dist` is load-bearing if the
  bridge is ever touched (it should not be — HALT and ask if it looks
  necessary).
- Human merges every PR; ask before push.

## 9. Out of scope

- The Gauss-Newton closure solve (escalation-only, §2.4; prefer consuming
  Codex R3).
- Analytic Jacobians, reachability IK, thick-panel work (slice-5 spec OUT
  list carries over).
- Any bridge/ide-bridge change (HALT trigger, §5).
- Phase S implementation detail (checkpoint-scoped by design).
- Kick hardening (own charter; trigger named in §5).
