# How close does `AREA_EPS` come to firing?

**Date:** 2026-10-05
**Status:** measurement only. No production file is modified, no spec is
written, and no change to `AREA_EPS` is proposed here.

---

## 1. The question

`layer_certify.py:17-21`:

> ⚠ CERTIFIED IS NOT FLAT-FOLDABLE. `layer_order.AREA_EPS` drops sliver
> arrangement cells before `cons.pairs` is built, and a dropped cell REMOVES
> constraints and can never add one. So CERTIFIED means "certified against the
> constraint set that survived `AREA_EPS`", which is strictly weaker than a
> proof. Closing that is separate work.

Two things turned out to be true, and they point in opposite directions.

---

## 2. On box-pleat geometry the caveat is already CLOSED — and nobody wrote it down

`geom.cells` calls `K.area_nonzero` at the two sites that mirror production's
`_split_convex` (`layer_order.py:307` and `:311`), and the two kernels differ
exactly there:

```python
FLOAT.area_nonzero = lambda a: abs(a) > AREA_EPS   # 1e-9
EXACT.area_nonzero = lambda a: a != 0              # no epsilon at all
```

**The exact arm IS the `AREA_EPS = 0` run.** On the dense `lizard`, the
2026-10-04 exact-arrangement slice already established the whole chain:

| step | result |
|---|---|
| FLOAT transcription vs production `_cells` | **bitwise identical**, 26 cells |
| EXACT (epsilon-free) vs FLOAT | 26 = 26 cells, covers identical |
| `cons.pairs` exact vs float | **53,754 = 53,754**, 0 either way |
| closest `AREA_EPS` decision | **108,131×** above the threshold |

So for that subject `AREA_EPS` costs exactly nothing, and this is a
*recomputation with the epsilon removed*, not a margin argument. The caveat
was closed four days before this measurement and the finding never propagated
back into `layer_certify`'s docstring.

---

## 3. On TreeMaker geometry the caveat cannot be settled at all

**The exact arm is unavailable.** `kernel._snap` refuses when rationalizing
moves a coordinate more than `SNAP_TOL = 1e-12`. Measured over the 28
committed `.fold` files: **4 rationalize, 24 do not.** The four are exactly
the box-pleat subjects, which sit on coarse rational grids (max denominators
68, 108, 34, 8). Every TreeMaker-derived subject refuses, because its
coordinates come out of a nonlinear packer.

In exact arithmetic a cell either has positive area or it does not, and no
threshold is needed. Without it there is **no arbiter** for these subjects,
and there cannot be one without changing how TreeMaker emits coordinates.

---

## 4. What CAN be measured: the margin

The smallest area that *survives* `AREA_EPS` is, by definition, the threshold
at which the first drop would occur. So `min_kept / AREA_EPS` is a per-subject
safety factor that needs no arbitrary second threshold.

**Corpus:** the 17 authored trees in
`../2026-09-08-vlm-tree-authoring/data/rule6_serve.json`, compiled through
TreeMaker (`server.draft_and_compile_full_base`). All 17 compiled; **14 are
`cp_audit` clean**. The three that are not — `crab` (10 flaps), `spider` (9),
`scorpion` (11) — are the known >8-flap wall.

**Result: every one of the 17 drops pieces in the grey band, and no margin
exceeds 5×.**

| subject | clean | faces | cells | dropped | grey | margin |
|---|---|---|---|---|---|---|
| starfish | yes | 18 | 13 | 13 | 13 | **1.0000000203×** |
| cat | yes | 82 | 142 | 213 | 212 | 1.0060× |
| bird | yes | 40 | 34 | 117 | 103 | 1.0190× |
| horse | yes | 148 | 301 | 241 | 215 | 1.0206× |
| scorpion | no | 222 | 188 | 527 | 507 | 1.0349× |
| ant | yes | 44 | 60 | 112 | 99 | 1.0478× |
| crab | no | 430 | 925 | 617 | 540 | 1.0566× |
| dog | yes | 68 | 50 | 92 | 90 | 1.1233× |
| octopus | yes | 76 | 109 | 120 | 105 | 1.1289× |
| spider | no | 66 | 88 | 94 | 85 | 1.2126× |
| bat | yes | 34 | 50 | 38 | 38 | 1.2774× |
| dolphin | yes | 44 | 67 | 22 | 17 | 1.2793× |
| lizard | yes | 88 | 56 | 18 | 18 | 1.4195× |
| elephant | yes | 58 | 36 | 51 | 51 | 2.5810× |
| frog | yes | 42 | 21 | 21 | 21 | 3.9079× |
| guinea_pig | yes | 42 | 22 | 21 | 21 | 4.3242× |
| rabbit | yes | 52 | 40 | 18 | 18 | 4.9786× |

Bands: *noise* `< 1e-14` (machine-epsilon clipping residue), *grey*
`1e-14 … 1e-9` (below the threshold but above roundoff), *kept* `> 1e-9`.

`AREA_EPS = 1e-9` sits **inside** the cell-size distribution on every TreeMaker
subject measured, rather than safely below it.

---

## 5. `starfish`, and a conclusion in `layer_order.py` that was tested where it
could not fire

`starfish`'s smallest surviving cell:

| | |
|---|---|
| float area | 1.00000002029032586e-09 |
| **exact area** (rational shoelace over the same float coords) | 1.00000000734120298e-09 |
| float − exact | 1.295e-17 |
| rotating the vertex order shifts it by | **0** |
| headroom above `AREA_EPS` | 2.029e-17 |

⚠ **A claim made during this work and then measured false.** It was asserted
that the area's own roundoff would be ~1e-16, "roughly 5,000× the headroom",
making the cell's survival roundoff-determined. **Measured: 1.295e-17, which
is 0.64× the headroom** — an eightfold overestimate. The float computation
does *not* flip this decision, rotating the summation order does not move it
at all, and the **exact** area is above the threshold. The cell genuinely
survives.

What stands after the correction is narrower and still notable: the exact area
clears the threshold by **7.3e-18** (relative margin 7.3e-9), and this
platform's own float error on it is **64% of that headroom**.

**This bears on `layer_order.py:55-62`**, which records the threshold-straddling
hypothesis — "a cell survives on one platform and is dropped on another" — as

> falsified in the strongest available way: it fires HARDEST exactly where the
> outcome does not move, and NOT AT ALL (23/23 cells, min area 1.378e-06 -- a
> thousand times this threshold) on `template-bird`

`template-bird`'s margin is **1,378×**. A subject at that margin cannot exhibit
the failure, so the test could not have come back any other way. `starfish` is
at **1.0000000203×**. The hypothesis is not falsified; it was tested on a
subject where it was unable to fire. It is also **not confirmed here** — on
this platform the cell survives — but the headroom is within a factor of 1.6 of
this platform's own error.

---

## 6. What this does NOT establish

- **The cost in `cons.pairs` is NOT reported here, deliberately.** A
  fine-threshold comparison (1e-9 against 1e-14) measured 10 of 12 clean
  subjects losing constraint pairs, 643 in total. That figure is an **upper
  bound on a quantity these tools cannot pin down**: the fine arrangement is
  dominated by debris — `cat` goes 142 → **130,071** cells, ten orders of
  magnitude below a legitimate cell — and the arbiter that would separate real
  slivers from clipping residue is the exact arm, which §3 shows is
  unavailable. The margin in §4 needs no such threshold and is reported
  instead.
- **Monotonicity was supported, not proven.** `gained = 0` on all 12 subjects
  that completed the fine comparison — the first empirical test of a claim
  asserted in `layer_order.py:17`, `layer_certify.py:17`,
  `box_pleat/layers.py:8` and `box_pleat/compile.py:660`, and never checked.
  12 subjects is not a proof.
- **Three subjects were never fine-compared**: `spider`, `scorpion`, `ant` (the
  run hit a time limit); `octopus` and `crab` exceeded a 180 s per-subject
  budget. The margin census in §4 covers all 17.
- **One platform, one machine.** Everything here is darwin/arm64.

---

## 7. Reproducing

```bash
# corpus: 17 authored trees -> TreeMaker
python3 build_tm_corpus.py <outdir>
# margins
python3 census.py <outdir> census.json
```

⚠ **Two environment notes, because they affected this run.**

1. `server.py:57` imports the feasibility gate, which imports `sklearn` at
   module level. `scikit-learn==1.9.0` is pinned in `ci.yml:168` but is
   **absent from the local `.venv`** (as are `scikit-image==0.26.0` and
   `pybind11==3.0.4`). This corpus was built with a stub on `PYTHONPATH` whose
   every symbol **raises** if called, so it can satisfy the import and nothing
   else. The gate is reached only from `predict_tree_feasibility`
   (`server.py:4170`) and is not on the compile path; `_GATE` was confirmed
   unloaded. Installing the pinned versions is the real fix.
2. `build_tm_corpus.py` needs its `if __name__ == "__main__":` guard. The
   compile path **spawns**, and without the guard each child re-imported the
   script and re-ran the whole corpus loop — one child overwrote the parent's
   manifest with `compiled 0 of 17` a minute after a successful run wrote it.
   The corpus `.fold` files are not committed: they are regenerable, and
   TreeMaker output is exactly the kind of roundoff-bearing artifact this
   project has already found to diverge across platforms.
