# F.3 at variable level: two of its three rules are already in our code, or inert

Script: `f3_rules.py` · Artifact: `f3-rules.json` · Measured 2026-09-27

Follows `../2026-09-27-f3-anchors/`, which refuted the doubt about F.3's
*anchors* and named this as the next question: do F.3's rules -- "X-shape same,
parallel opposite, perpendicular same" -- determine our ridge variables?

## The table

| subject | ridge vars | **multi-orientation** | % | par | perp | oblique | pairs skipped | **conflicts** |
|---|---|---|---|---|---|---|---|---|
| `starfish` | 18 | 12 | 66.7 | 5 | 1 | 0 | 26 | **0** |
| `lizard` | 88 | 68 | 77.3 | 18 | 0 | 0 | 134 | **0** |
| `frog` | 114 | 74 | 64.9 | 61 | 0 | 0 | 151 | **0** |
| `horse` | 182 | 126 | 69.2 | 87 | 0 | 0 | 265 | **0** |
| `bird` | 238 | 186 | 78.2 | 100 | 0 | 0 | 383 | **0** |
| `guinea_pig` | 204 | 126 | 61.8 | 115 | 0 | 0 | 255 | **0** |
| `octopus` | 364 | 276 | 75.8 | 149 | 0 | 0 | 568 | **0** |
| `dog` | 424 | 244 | 57.6 | 300 | 0 | 0 | 513 | **0** |

## What the orientation classes show, which is the whole result

The breakdown is startlingly clean. `lizard`:
`{((1,-1),(1,1)): 68, ((0,1),): 20}`. `dog`:
`{((1,-1),(1,1)): 244, ((1,0),): 130, ((0,1),): 50}`.

* **Every multi-orientation variable is exactly `{(1,1), (1,-1)}`** -- a
  mirror-merged pair of the two diagonals. There is not one other combination
  anywhere in the corpus.
* **Every orientation-coherent variable is axis-aligned.** There are **no
  coherent diagonal variables at all.**

So F.3's orientation-based rules, applied at variable level, can only ever speak
about the axis-aligned minority (23% of ridge variables on `lizard`, 42% on
`dog`). The diagonal majority -- which is what box-pleat ridges mostly ARE --
sits inside merged variables with no single orientation: on `lizard`, **68 of 88**
ridge variables span `{(1,1), (1,-1)}` (77.3%), and on `dog` **244 of 424**
(57.6%).

⚠ *Corrected 2026-09-27: this sentence read "(136 of `lizard`'s 156 ridge
pieces)". That count is not derivable from `f3-rules.json`, which carries no
piece-level orientation data at all — `orientation_class_hist` is over
**variables**. 136 was 156 **pieces** minus 20 **variables**: a subtraction across
two different columns, sound only if every orientation-coherent variable held
exactly one piece, where this subject averages 156/88 = **1.77 pieces per
variable**. The underlying claim is probably true, but the figure was assembled,
so it is restated at variable level — the level the artifact actually measures.
This is the same "observation assembled from two different columns" pattern that
`../2026-09-27-f3-anchors/` names as "the wrong statistic" and that was also
found in `../2026-09-27-nogood-core/`'s cone-scale comparison.*

## The finding: our mirror merge ALREADY implements "perpendicular same"

Mirroring across the symmetry axis maps a `(1,1)` ridge to a `(1,-1)` ridge, and
those two directions are **perpendicular**. F.3's rule for a perpendicular pair
is *same label*. `assign`'s mirror merge forces a ridge and its mirror onto one
variable, i.e. **the same label**.

**The rule and the merge agree, so the merge is F.3's "perpendicular same" for
every mirrored diagonal pair, already in the code by a different mechanism.**
That is why those variables span two orientations: not a defect, but the merge
having already consumed exactly the relationship F.3 would impose.

This is the second time this pattern has appeared. `../2026-09-27-pleat-filter/`
found F.1.1 step 3's filtering already done upstream by `contours.py`' elevation
field. Here F.3's perpendicular rule is already done by mirror-merging. **Twice
now, a COrigami mechanism has turned out to be present in this pipeline under a
different name** -- which is a fact about how much of the paper this codebase has
independently arrived at, not a fact about the paper.

## What is left of F.3 here

| F.3 rule | status on our geometry |
|---|---|
| **X-shape same** | **inert** -- 0 or 1 X-shape vertices corpus-wide (straight-skeleton ridges meet at nodes, they do not cross) |
| **perpendicular same** | **already implemented** by the mirror merge, for every mirrored diagonal pair |
| **parallel opposite** | the only rule with residual work: **6-300** governed pairs per subject, all among axis-aligned variables |
| Y-shape anchors | adequate (`../2026-09-27-f3-anchors/`): 1-2 components, reach 100% on 5 of 8 |

*The 6-300 range was corrected 2026-09-27 from "18-300", which silently dropped
`starfish`'s 6 governed pairs (`pairs_parallel` 5 + `pairs_perpendicular` 1 +
`pairs_oblique` 0) — the smallest subject and the only one where the perpendicular
rule fires at all. Per-subject governed totals: 6, 18, 61, 87, 100, 115, 149, 300.*

**`conflicts` is 0 over the coherent subgraph** -- a minority of pairs, with **one**
perpendicular constraint corpus-wide -- **so F.3 is not REFUTED, but this is a weak
test rather than a clean bill.** The parity union-find skips every pair touching a
multi-orientation variable, and `pairs_skipped_incoherent_variable` **exceeds the
governed count on all eight subjects** (26 vs 6, 134 vs 18, 151 vs 61, 265 vs 87,
383 vs 100, 255 vs 115, 568 vs 149, 513 vs 300); and `pairs_perpendicular` is **0
on seven of eight subjects**, summing to **1** across the whole corpus, so the
"perpendicular same" half of the rule set contributed exactly one constraint.
Zero conflicts over that subgraph is close to vacuous — which is Limit 1 below,
now carried in the conclusion sentence instead of only in the caveats. What the
measurement does support is that F.3 is **degenerate**: two of three rules have
nothing to do here, and the third addresses a minority of ridge variables.

*Corrected 2026-09-27: this paragraph read "**No contradictions anywhere:
`conflicts` is 0 on all eight subjects.** So F.3 is NOT refuted -- nothing in our
geometry makes its rules inconsistent." The `conflicts` readings are unchanged and
correct; the scope claim ("anywhere", "nothing in our geometry") was not, because
the test never examined the majority of pairs.*

## What this does and does not establish

**Establishes:** a faithful variable-level port of F.3 would determine
substantially less than the original spec assumed when it called F.3 "likely the
largest cost lever available". Ridge variables are 20-23% of all CSP variables
(`../2026-09-26-gap1-phase0/`), and F.3's residual rule addresses 23-42% of
those -- so roughly **5-10% of the CSP**, not the bulk of it.

**Does NOT establish that F.3 is worthless, and does not settle it.** Two limits
on this measurement, stated because the framing itself is the weak part:

1. **This is the variable-level reading, and it is partly ill-posed** -- 58-78%
   of variables have no single orientation, and the script SKIPS those pairs
   (the `pairs skipped` column, which is larger than the governed count on every
   subject). A better-posed formulation would derive the constraints at
   **collinear-run** level, where orientation is always defined, and then check
   them against the mirror-merge equalities rather than skipping past them.
2. **A merge relating two variables is not the same as determining a value.**
   "Perpendicular same" being pre-implemented fixes diagonal ridges *equal to
   their mirrors*; it does not say M or V. Values still have to propagate from
   anchors, and at variable level the rules do not govern diagonal-to-diagonal
   propagation -- so the diagonal majority stays undetermined.

**Recommendation on the evidence:** F.3 is viable but thin, and its
attractiveness rested on an assumption (largest cost lever) this measurement
does not support. **Minimal unsat cores are now the better-supported lever** --
they rest on a direct measurement with no interpretation dependency (the clause
never tightens across 5.17x more experience,
`../2026-09-24-dense-pleats/README.md` §4b/4c), whereas every COrigami mechanism
tried so far has turned out to be either already present here or inert on this
geometry.

## Reproduce

```bash
# from mcp_harness
PYTHONPATH=. ../.venv/bin/python3 -u \
    ../docs/superpowers/evidence/2026-09-27-f3-rules/f3_rules.py \
    ../docs/superpowers/evidence/2026-09-27-f3-rules/f3-rules.json
```

`var_of` is read from production by patching `assign.py` in memory and asserting
the diff added only the probe line -- never a committed fork.
