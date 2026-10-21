# Handoff: §15 Integration — U4 is wired, and the LLM half of the design is not

## 1. What shipped

`WIDE_VOXEL_GRID`, `wide_grid_budget` and `spec_distance` had, until now,
**exactly one reference each in `mesh_to_tree.py`: their own definition.** The
P3 handoff called that "the single largest open item in the design… plumbing
whose blast radius has never been costed." This wave costs it and wires two of
the three.

| piece | state |
|---|---|
| `wide_grid_enabled(reference_count)` — flag **and** safety condition | **new, wired** |
| `resolve_voxel_grid(voxel_grid, reference_count)` | **new, wired** |
| widened grid swept by `auto_mesh_to_metric_tree` | **wired** |
| drain budget derived from the swept grid | **wired, wide path only** |
| `spec_distance` cell ranking | **deliberately NOT wired — see §4** |

Flag: `IDE_WIDE_VOXEL_GRID=1`. **Default OFF.**

## 2. The safety condition is the design, not a guard rail

`WIDE_VOXEL_GRID`'s own docstring states that sweeping it is safe **only**
alongside an external `reference_count`: without one, a coarse cell whose leaf
count plateaus early scores a self-consistent `fid >= 1.0` against its **own
degraded R** and takes the terminal exit before a finer cell is ever built,
amputating anatomy. That is measured, on the lizard.

So `wide_grid_enabled` requires **both** the flag and a non-`None`
`reference_count`. The flag alone does nothing.

**This bounds the blast radius sharply and by construction:** the wide grid can
only ever activate for prompts carrying an external R. Four of the five
committed fixtures (`fish`, `insect`, `quadruped`, `humanoid`) are **not in
`anatomy_expectation.json`**, so production passes `reference_count=None` and
the flag is inert for them — not by luck, by the condition.

An **explicit** `voxel_grid=` always wins over the flag, so every pinned-grid
call site and test keeps its exact meaning.

## 3. Measured: no harm on the five committed fixtures

`probe_s15_fixture_harm.py`, bar pre-registered and mutation-verified (all four
HARM modes shown reachable) before either arm ran.

| fixture | R | leaves | stubs | pairs | confirmed | cell | wall |
|---|---|---|---|---|---|---|---|
| bird | 6 (authored) | 6→6 | 0→0 | **1→2** | ✓→✓ | [64,0.30]→[24,0.40] | 59.2s→**2.8s** |
| fish | 8 (forced) | 8→8 | 0→0 | 3→3 | ✓→✓ | unchanged | 8.2s→26.1s |
| insect | 8 (forced) | 8→8 | 0→0 | 4→4 | ✓→✓ | [96,0.50]→[24,0.40] | 10.7s→**1.4s** |
| quadruped | 6 (forced) | 6→6 | 0→0 | 2→2 | ✓→✓ | [96,0.40]→[24,0.55] | 133.6s→**5.4s** |
| humanoid | 5 (forced) | 5→5 | 0→0 | 2→2 | ✓→✓ | [96,0.30]→[24,0.55] | 3.5s→3.0s |

**VERDICT: NO HARM. Total wall 215s → 39s.**

⚠ **COST IS POPULATION-DEPENDENT; DO NOT GENERALISE FROM THIS TABLE.** Here
four of five resolve at voxel 24 and the search exits before building
128/192/256, so wall clock FALLS 215s -> 39s. On the large generated meshes of
section 7 it RISES, 1054s -> 1403s. U4's spec predicted a uniform "~2.3x today's
skeleton builds"; neither measurement matches it, and they disagree in SIGN with
each other. Quote the population with the number or do not quote it.

⚠ **READ THE `forced` LABEL BEFORE QUOTING THIS TABLE.** Only `bird` carries an
authored R. The other four were given `R = the shipped arm's own served count`
— a neutral "hit what you already hit" target, deliberately more exposure than
production can create. "Leaves unchanged" on those rows is partly what was
*asked for*; it is evidence of **no harm**, never of benefit. `bird` is the one
authored row, and it gained a pair at 21x the speed.

## 4. Why `spec_distance` is NOT wired

Its **count** axis duplicates ranking the search already does —
`rank_by_fidelity` orders phase 1 by `-fidelity_score(leaf_count,
reference_count)`, the same cell-vs-R quantity. Its **pair** axis, the only
genuinely new one, has no input: **0 of 14 authored rows carry
`expected_pairs`**, and `spec_distance`'s own docstring says so.

Wiring a key nothing exercises is this project's named vacuity failure — the
reason `hull_coverage` is deliberately absent from `order_rank.rank_key`.
Pinned by `test_no_authored_row_supplies_a_pair_target`, which goes RED the
moment a row gains a pair target. **That is exactly when wiring it becomes
worth measuring.**

## 5. A real design bug, caught by an existing test

The first version derived the drain budget **unconditionally**. That looks
inert — `wide_grid_budget([96, 64, 128]) == 6 == DRAIN_BUDGET` — and is not:
`test_drain_before_downgrade.py::test_drain_budget_is_bounded` passes an
explicit **9-voxel** grid and drained **8** instead of 6. A behaviour change on
a **flag-off path**, which is precisely what §15's byte-identity contract
forbids.

Now scoped to the wide path. **The pre-existing `DRAIN_BUDGET` defect for long
EXPLICIT grids is reported, not silently repaired** — `DRAIN_BUDGET = 6`
encodes `FIDELITY_K1 x len(VOXEL_GRID)` and its documented meaning is false for
any grid that is not 3 long. That remains open, and is now pinned by
`test_an_explicit_LONG_grid_keeps_the_shipped_bound_when_the_flag_is_off`.

## 6. Verification

* **495 passed, 0 failed** across 21 extraction-path suites.
* The 19 failures in `test_book_axis_projection` / `test_edge_optimization` /
  `test_projection_guards` are **pre-existing macOS/.so divergence**, proved not
  asserted: all three files contain **zero** references to `mesh_to_tree`, the
  only production file touched.
* 15 new tests in `tests/test_section15_integration.py`, each watched failing
  first. The seam test is **differential** (`off[0] == 96`, `on[0] == 24`) so it
  cannot pass vacuously.

## 7. The benefit probe RAN, and the bar REFUSED it

`probe_s15_wide_grid.py`, bar pre-registered and mutation-verified before the
meshes existed. Fresh 12-subject batch, `hf2` (FLUX -> Hunyuan3D), both arms
supplied the external R exactly as `server.py` does.

| subject | T | shipped | err | wide | err | stubs | pairs |
|---|---|---|---|---|---|---|---|
| bird | 6 | 8 | 2 | 5 | 1 | 0->0 | 2->1 |
| **cat** | 6 | **0** | 6 | 6 | 0 | **0->1** | 0->2 |
| dog | 6 | 7 | 1 | 6 | 0 | 0->0 | 3->1 |
| frog | 5 | 12 | 7 | 5 | 0 | 0->0 | 5->1 |
| horse | 6 | 9 | 3 | 6 | 0 | 0->0 | 3->2 |
| human | 5 | 5 | 0 | 5 | 0 | 0->0 | 1->1 |
| lizard | 6 | 5 | 1 | 6 | 0 | 0->0 | 1->2 |
| lizard, long tail | 6 | 6 | 0 | 6 | 0 | 0->0 | 2->2 |
| octopus | 9 | 10 | 2 | 8 | 0 | 0->0 | 2->3 |
| person | 5 | 5 | 0 | 5 | 0 | 0->0 | 1->1 |
| spider | 9 | 8 | 0 | 8 | 0 | 0->0 | 2->2 |
| starfish | 5 | 5 | 0 | 5 | 0 | 0->0 | 1->2 |

**Total |served - min(T,8)|: 22 -> 1.** Eleven of twelve exactly on target.
W1 (1 < 22) passes, W3 (nothing killed) passes, W4 (net +7, zero worse) passes.

### VERDICT: DO NOT SHIP -- W2, `stub_flaps` rose on `cat` (0 -> 1)

**READ THIS BEFORE PROPOSING THE FLIP AGAIN.** 22 -> 1 is the most flattering
headline this work has produced, and it is refused by ONE subject inventing ONE
flap. That is CLAUDE.md 1.1 item 4 exactly as written -- `stub_flaps` is K1,
above every count -- encoded into the bar BEFORE any number existed. A bar
written after seeing 22 -> 1 would very likely not have made stubs terminal.
**Do not relax W2 to reach the headline; that is this project's named recurring
failure mode.**

Note what `cat` is: the subject the wide grid RESCUES from serving nothing. The
rescue is real and it is bought with invented anatomy. Both halves are true.

### Two signals no bar term covers, reported not scored

* **Pairs FALL on three subjects** -- bird 2->1, dog 3->1, frog 5->1. On frog
  that tracks the drop from an over-segmented 12 leaves; on **bird** it does
  not: bird ends BELOW target (5 against T=6) with a pair lost, which is
  under-extraction, not cleanup. W1-W4 carry no pair term, so this is recorded
  for the next bar rather than scored in this one.
* **Cost is population-dependent and the earlier claim in this document was
  over-generalised.** Wall clock here: shipped 1054s, wide **1403s (1.33x
  SLOWER)**. On the five small committed fixtures it was 215s -> 39s (5.5x
  FASTER). Neither is the spec's predicted 2.3x. Quote the population with the
  number or do not quote it.

### The earlier H2 evidence remains void

The `frog` 0->8 / `horse` 0->5 readings ran with `reference_count=None`, the
configuration `WIDE_VOXEL_GRID`'s docstring names unsafe, and those meshes were
deleted. This batch is a NEW SAMPLE, not a reproduction -- the generators are
stochastic and unseeded, and the failure is per-mesh, not per-subject. Visible
right here: the previous batch's `frog` served **0**; this batch's serves
**12**. Same prompt, same pipeline, opposite failure.

## 8. What a successor should do, in order

1. **Do NOT flip the default, and do NOT relax W2.** The count evidence is
   spectacular (22 -> 1, eleven of twelve exact) and the bar refuses it on one
   invented flap. Relaxing a gate to reach a headline is the named failure mode;
   the whole value of a pre-registered bar is that it binds when the headline is
   good.
2. **Investigate `cat`'s stub instead.** It is ONE flap on ONE subject and it is
   the only thing between this flag and a default-on argument. If the stub can
   be eliminated -- or shown to be a labelling artefact rather than invented
   anatomy -- rerun the bar UNCHANGED and it passes on its own terms.
3. **Add a PAIR term to the next bar.** Pairs fell on bird, dog and frog, and
   W1-W4 could not see it. `bird` is the clearest case: below target at 5 with a
   pair lost. A count-only bar cannot distinguish "cleaned up over-segmentation"
   from "lost a limb".
4. **Re-measure U2 with the wide grid ON.** `probe_u2_integrated` returned SHIP
   but resolved on ONE subject of twelve (`spider`); on the other eleven U2's R
   and a constant 6 served byte-identical trees. The likely mechanism is now
   visible: with the shipped 3-voxel grid the leaf window was reachable at
   essentially one corner cell (`lizard` passed on 1 of 24), so R had nothing to
   steer between. This integration may be U2's PRECONDITION rather than its
   competitor.
5. **The freeze default remains as shipped.** It zeroes `horse` on one measured
   mesh, but on the metric it was scored against (pair count, `stub_flaps`) it
   has not been re-run. Reverting it on a leaf-count metric would repeat the
   failure mode in item 1.
6. **`spec_distance` stays unwired** until an authored row carries
   `expected_pairs`. The test that pins this goes RED at exactly that moment.
