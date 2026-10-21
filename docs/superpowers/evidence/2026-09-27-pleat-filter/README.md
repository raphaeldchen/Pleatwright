# Phase A HALTED: F.1.1 step 3 cannot discriminate on our geometry

Measured 2026-09-27, during implementation of
`docs/superpowers/plans/2026-09-27-pleat-filter.md` Task 4 (the activation).
Tasks 1-3 are committed and inert; **Task 4 was not committed** and its work is
**not preserved in this repository** -- it exists only as
`.superpowers/sdd/task-4-wip.diff` in the author's local scratch directory, which
is git-ignored and tracked nowhere (`git ls-files .superpowers/sdd/` returns
nothing), so no other clone has it. Treat the activation as unavailable.

## The result

**At the granularity COrigami intends, the filter retains 100% of our dense
candidates. It is a no-op.** At unit-piece granularity it retains 9.6% but
produces a crease pattern that is **not flat-foldable at all**.

Measured on `lizard` (4,488 dense candidates):

| granularity | retained | % | fully-bound interior vertices | **odd crease degree** |
|---|---|---|---|---|
| **unit piece** (what Phase 0 measured) | 432 | 9.6% | 454 | **408** |
| connected pleat path (`pleat_paths`' 365 groups) | 4,488 | **100%** | 4,078 | 0 |
| **maximal collinear run** (the paper's "segment") | 4,488 | **100%** | 4,078 | 0 |

The collinear-run decomposition yields **365 runs — exactly `pleat_paths`' 365
groups**, so on this geometry a path and a segment are the same object, and
**365 of 365 are retained**.

## Why unit-piece granularity is not merely wrong but destructive

`assign(dense=True, filter_pleats=True)` fails as
`AssignFail(kind='maekawa_fixed', site=(1, 21))` — before the search starts.
Vertex `(1, 21)` carries exactly two collinear `elev` pieces, one running to
`(1, 20)` and one to `(1, 22)`. The per-piece filter **retained one and rejected
the other**, leaving the vertex with a single crease. Maekawa needs `|M - V| = 2`,
so an odd degree is unsatisfiable by any labelling.

That is systematic, not an edge case: **408 of 454** fully-bound interior
vertices come out odd. A pleat is a chain of collinear unit pieces, and a
per-piece predicate keyed on "touches a hinge" keeps only the chain's
hinge-adjacent end, truncating the pleat mid-sheet.

## Why segment granularity is vacuous

COrigami step 3 retains a segment "strictly perpendicular to an intersecting
hinge". **Every one of our segments satisfies that by construction**, because
`pleat_paths` splits candidate runs exactly where a ridge or hinge lands — so a
segment's endpoint IS a hinge or ridge vertex. There are no segments for the
criterion to discard.

**The structural reason, which is the transferable finding.** COrigami lays a
blind dense orthogonal grid across the sheet and then discards the segments that
do not meet structure; most of its grid is spurious, so its filter does real
work. Ours comes from `contours.py`' elevation field, which only ever emits
pieces along that field and already splits them at structural creases. **The
filtering work COrigami does in F.1.1 step 3 was already done upstream here, by
a different mechanism.** There is nothing left to filter.

## What this retracts

**Phase 0's headline — "the filter would reject ~90% of what dense mode creases"
(`evidence/2026-09-26-gap1-phase0/`) — is WITHDRAWN.** It measured retention at
**unit-piece** granularity, which is the wrong unit: the paper's step 2 splits
the grid "into candidate segments at every intersection with hinges and ridges",
so its unit of selection is a segment, not a half-grid unit. At the right unit
the figure is 100%, not 10%.

The Phase 0 numbers themselves are correct arithmetic; the conclusion drawn from
them was a unit error. **This is the same class of mistake as the crease-vs-
variable unit error in the dense-pleats wave, and it again ran in the direction
that favoured the hypothesis being tested.**

## What it means for gap 1

**The crease-set hypothesis is refuted in the specific form Phase A tested it.**
Dense mode's crease set is not over-dense by COrigami's own criterion — it is
very nearly exactly what that criterion would keep. So the reason no dense
pattern certifies is not that we crease segments the paper would have discarded.

Consequences for the remaining levers:

* **F.1.1 step 5 (the fill, "Component 1")** is now the only part of F.1.1 with
  anything to do here, and it would make the pattern DENSER, not sparser.
* **F.3 ridge assignment** remains, but is in doubt on the same
  geometry-mismatch grounds: it anchors on Y-shape and X-shape ridge vertices,
  and `lizard` has **2** Y-shapes and **0** X-shapes against 88 ridge variables
  (`evidence/2026-09-26-gap1-phase0/README.md` §2.1). Before Phase B is planned,
  that anchor count should be measured the way this filter's discrimination was.

  ⚠ **That measurement was made the next day and it REFUTED this doubt — see
  `../2026-09-27-f3-anchors/`.** What governs propagation from anchors is not how
  many anchors there are but **whether they reach the ridge graph**, and the ridge
  graph turns out to have only **1 or 2 components on all eight subjects**
  (`f3-anchors.json`, `ridge_components`), so `reach_pct` is **100% on five of
  eight** (`starfish`, `lizard`, `horse`, `octopus`, `dog`) and **≥ 71.7%** on the
  other three (`frog` 71.7, `guinea_pig` 78.38, `bird` 87.39). `lizard`'s 2
  Y-shapes reach **100%** of its 156 ridge pieces. **This bullet also commits the
  error `f3-anchors` names as "the wrong statistic"** — comparing 2 anchor
  *vertices* against 88 ridge *variables*, two different populations, which is
  the same cross-column comparison this file's own retraction above is about.
  (F.3 was later closed as *degenerate* for an unrelated reason —
  `../2026-09-27-f3-rules/` — not for this one.) Left visible, unerased.
* **Minimal unsat cores** are untouched by this finding and remain supported by
  the large-budget run's reading 2 (the clause never tightens).

## Reproduce

The three-granularity comparison is not a committed script: it was run inline
against `pleat_filter.retain` (committed, `8ae7821`) plus `pleat_paths`' own
grouping. To redo it, retain whole `pleat_paths(dense=True)` groups whenever any
member piece is in `pleat_filter.retain(pieces, N)`, then count interior
vertices whose bound folded-piece count is odd.
