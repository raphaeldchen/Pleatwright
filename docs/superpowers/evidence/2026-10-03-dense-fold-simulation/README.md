# The dense lizard CP in the simulator: it folds, and it does not fold flat

**Date:** 2026-10-03
**Instrument:** `probe.js` · **Artifact:** `sim-planarity.json`
**Subject under test:** the dense `lizard` SAT witness from
`../2026-10-02-witness-identity-113/witness.fold`

## 1. Why this run exists

Five slices attacked the dense path's CEGAR search and all returned negative.
`../2026-10-02-witness-identity-113` then showed the crease set **is**
satisfiable (SAT in 0.2 s), that the witness passes four independent validators
plus the Oriedita linter, and `../2026-10-02-sat-layer-stage` shipped the query
as a `compile_tree` stage that emits CERTIFIED in 28.6 s.

Every one of those gates is static. Tier 1 of this project's architecture says
the Origami Simulator is what "proves physical foldability", and **no dense CP
had ever been run through it**. This run closes that.

## 2. Method, and what licenses the numbers

`probe.js` replicates `mcp_harness/sim_capture.py`'s `SimSession.capture`
protocol — `loadFold` → `setFold` → settle → `getFoldedGeometry` — in a headed
browser pane. Playwright is not installed in this venv and no browser cache
exists, so the committed Python harness could not be run directly.

**The control is what makes the rest citable.** The anchor star-4 base
reproduced `sim_capture.ANCHOR_DISP = 1.3109` **exactly** through this path.

`planarity` = smallest / largest principal standard deviation of the folded
vertex cloud. A flat-folded sheet is a plane, so this goes to ~0. The solver has
**no self-collision** (`thickenModel` / `thickenOffset` are rendering options),
so a residual is **not** paper thickness — layers pass through each other freely
and the solver would collapse to a plane if that were its local minimum. A
residual means it is stuck.

Renderer: WebGL 1.0, ANGLE (Apple, ANGLE Metal Renderer: Apple M4). Solver:
`axialStiffness` 20, `creaseStiffness` 0.7, `faceStiffness` 0.2,
`panelStiffness` 0.7, `percentDamping` 0.45, `numSteps` 100.

## 3. The result

Every figure from `sim-planarity.json`.

| subject | creases | maxDisp | planarity | third principal sd | reads as |
|---|---|---|---|---|---|
| anchor star-4 | 8 | **1.3109** (recorded 1.3109) | **0.00002** | 0.00001 | flat |
| sparse `lizard` | 27 | 1.1683 | **0.00586** | 0.00128 | essentially flat |
| dense `lizard`, jumped | 745 | 1.1829 | **0.06482** | 0.01351 | **not flat** |
| dense `lizard`, ramped | 745 | 0.8293 | **0.07254** | 0.02269 | **not flat** |

**It folds.** maxDisp 0.83–1.18 clears `sim_capture.DISP_GATE` (0.10) by an
order of magnitude, zero non-finite coordinates, all 380 vertices present, and
the rendered shape is recognisable limbed anatomy rather than a tangle.

**It converges.** Three reads 30 s apart are identical to 5 significant figures
(planarity 0.06484 / 0.06481 / 0.06482; `maxDisp` 1.1829 at all three). This is
a stable equilibrium, not a run still relaxing.

**It does not fold flat.** 0.065 against the same subject's sparse CP at 0.0059
and the reference base at 0.00002 — about 11x less flat than sparse and 3,200x
less than the anchor.

**The drive is not the cause.** Project memory records clean bases jamming when
driven straight to 100%, so the documented crease-percent ramp was run as well
(10→100 in steps of 10, 4 s each). It made it slightly *worse*, not better.

## 4. What this does NOT establish

**It is not a refutation of flat-foldability.** This simulator is a mass-spring
relaxation with no self-collision and **no knowledge of the layer ordering**.
The SAT result proves a valid ordering *exists*; the solver never consults it
and descends elastic energy locally. A 745-crease pattern failing to reach flat
is evidence about **the solver's ability to find the flat state**, not about
whether that state exists.

**The complexity confound is not removed.** Dense has 27x more creases than
sparse (745 vs 27) and 17x more vertices (380 vs 22). Complexity alone could
account for the difference; this run cannot separate "the dense labelling is
wrong" from "local relaxation cannot solve a 745-crease pattern".

**One subject, one host, one run per configuration.** No variance is estimated.

## 5. Where this leaves gap 1

The wall **moved**, which is the useful part of a negative result. It was
*"we cannot find an M/V labelling"* — solved: SAT answers in 0.185 s what
500,000 search nodes could not. It is now *"the simulator cannot drive a
745-crease CP to the flat state we proved exists."*

Those are different problems. The second has a lever this project already owns
and has never pointed at a dense CP: the `seedTheta` / `setTargets` bridge
messages in `.claude/worktrees/origami-animal-models-a131b6`, which seed each
crease's unwrapped angle **at its target** instead of letting all 745 start at
zero. Not merged to this branch.

## 6. A defect found in a committed artifact

`../2026-10-02-witness-identity-113/witness.fold` carries an
`edges_foldAngle` array that is **stale from the refuted candidate**:
`seed_witness.py` rewrote only `edges_assignment`. **352 of its 745 creases
contradict** the labelling the file claims.

It hides well. The histograms nearly agree — 388 entries at −180 against 384
`M`, and 357 at +180 against 361 `V` — so a count-based sanity check passes and
only a per-edge comparison finds it. Since the sim bridge uses `edges_foldAngle`
when present, feeding the file unmodified would have folded 352 creases the
wrong way: a guaranteed false negative. This run drops the field so the bridge
derives angles from `edges_assignment`.

**That open question is now closed (2026-10-04): the §15.3 Oriedita Pass
stands.** Oriedita reads `edges_assignment`, not `edges_foldAngle`. Measured
three ways: the file as committed → **Pass**; `edges_foldAngle` regenerated from
the assignment → **Pass**; and a probe inverting *every* creased angle while
leaving the assignment correct → **Pass**. The negative control rules out a
vacuous instrument — flipping a *single* assignment gives `Flat-foldability
FAILED [REAL] … MAEKAWA`, which `cp_audit` independently confirms.

`witness.fold` has been repaired (only `edges_foldAngle` changed; cp_audit
0/0/0 and Oriedita Pass re-verified on the repaired file), and
`seed_witness.py` now rewrites both arrays and refuses if any contradiction
survives. The defect's blast radius was the **simulator only**.

## 7. A trap worth recording

The first dense run returned **no folded geometry at all**, which reads exactly
like "the dense CP does not fold". The cause was the solver parked while the
browser pane was not fronted — with **no exception, no warning on any channel**,
and a geometry pipeline that visibly *had* run (it triangulated 364 quads in
place). Only the anchor control distinguished a broken harness from a real
refusal.

`document.visibilityState` is **not** the signal: it read `"hidden"` on both the
failed and the successful run. The reliable signal is `model.getNodes().length`
going 0 → N.

## 8. The seeding attempt: no effect on the attractor

§5 named the lever: `seedTheta` from
`.claude/worktrees/origami-animal-models-a131b6`, which puts each crease's
unwrapped angle **on the branch of its target** instead of letting all 745
start at zero, where the sign is decided by sub-precision noise. It is not in
this branch's shipped bridge (which has only `loadFold` / `setFold` /
`getFoldedGeometry`), so the logic was injected in-page verbatim; no file here
was modified.

It applied cleanly: **1,109 creases seeded, 745 with non-zero targets** —
exactly the fold's crease count, the other 364 being triangulation diagonals at
target 0.

| t | 10 s | 30 s | 60 s | 90 s | 120 s | 150 s |
|---|---|---|---|---|---|---|
| planarity | 0.1155 | 0.0776 | 0.06765 | 0.06283 | 0.06302 | 0.06395 |

**It converges to the same place.** ~0.063–0.064 seeded against 0.06482
unseeded: a different trajectory to the same destination. So the non-flatness is
**not** the solver starting creases on the wrong angular branch.

### Why this was always a proxy, and what it rules out

Seeding crease **angle branches** is not seeding the **layer order**. This
solver has no self-collision, so layer order has no physical effect in it and
**no degree of freedom represents it**. The thing the SAT stage proves — that a
valid non-crossing ordering exists — is not expressible in a collision-free
mass-spring model.

That is the structural result of this run: **the simulator cannot consume the
SAT result**, not for want of effort but because the state it constrains does
not exist in this model. Validating dense CPs physically therefore needs one of:

1. a collision-aware or rigid-origami solver that can represent layer order;
2. accepting the mathematical certification (complete layer order + local laws +
   static linter) as the proof, and treating this simulator as visualisation
   only; or
3. folding one by hand.

Nothing here argues the dense CP is not flat-foldable. It argues that this
simulator is the wrong instrument to decide it.

## 9. Solver parameters: no help, and a retracted claim

`faceStiffness` defaults to **0.2**, which is soft for paper — real paper facets
do not stretch — so raising it is the obvious third lever.

**It does not help. It hurts.** Clean method (full page reload per run, config
set before `loadFold`):

| config | planarity | maxDisp |
|---|---|---|
| `faceStiffness` 0.2 (baseline) | 0.06591 | 1.1757 |
| `faceStiffness` 1.0 | **0.08354** | 0.8515 |

### The retraction, and why it matters

A first sweep reported `faceStiffness` 1.0 at **0.03559** — a 45% improvement.
**That number was an artifact and is withdrawn.** The sweep helper called
`loadFold` but never reloaded the page, so each run began from the *previous
config's* relaxed positions: it measured config **plus history**.

What made it convincing is worth recording. This solver is **deterministic** —
its flat-tie jitter is a Knuth multiplicative hash, not `Math.random` — so
re-running an identical sequence reproduces bit-identical numbers. Two repeat
runs agreed to four decimals (0.05556 / maxDisp 1.0791 both times), and that
stability read as validity. The contamination only surfaced because the *same*
config gave 0.03559 after one predecessor and 0.05556 after another.

The clean retest inverts the sign of the original claim.

## 10. Three levers, one attractor

| lever | effect on the attractor |
|---|---|
| drive protocol (jump vs documented ramp) | none — 0.0648 vs 0.0725 |
| theta branch seeding (`seedTheta`) | none — converges to ~0.063–0.064 |
| solver stiffness (`faceStiffness` 0.2 → 1.0) | **worse** — 0.06591 → 0.08354 |

Baseline across clean runs: **0.06482 / 0.06591 / 0.06608**. Against sparse
`lizard` at 0.00586 and the anchor at 0.00002.

Three independent levers, none of which moves it. Combined with §8's structural
point — this solver has no self-collision and no degree of freedom representing
layer order — the conclusion is that **the instrument, not the tuning, is the
limit**.
