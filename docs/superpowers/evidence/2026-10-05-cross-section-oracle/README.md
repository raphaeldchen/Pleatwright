# Cross-section oracle: does the `taco` clause check mean what it says?

Spec: `../../specs/2026-10-05-cross-section-oracle-design.md`.
Artifact: `cross-section-oracle.json` (every figure below is read from it).
Subject: the SAT-certified dense `lizard` witness. One subject, no breadth claim.

## 1. The question

`layer_certify._satisfied` evaluates the `taco` family as

```python
if family == "taco":
    return (vals[0] != vals[1]) == (vals[2] != vals[3])
```

The four literals are built at `layer_certify.py:98` from creases `(p, q)` and
`(r, s)`. The predicate says: crease two's two faces are either both between
crease one's faces, or neither is. Its producer is the crease-by-crease loop at
`layer_order.py:633-646`.

The predecessor slice (`../2026-10-04-pointwise-oracle/`) established the
`equality` family exhaustively and left `taco` untested, because its oracle's
`covering` is a strict-interior test and a collinear crease's faces meet the
line only on their boundary. This slice asks whether the `taco` predicate and
its producing branch mean what they say, by slicing the folded state
perpendicular to each collinear crease line and comparing the constraints that
one-dimensional picture imposes against `cons.tacos`.

## 2. The verdict

**`identical`.**

| quantity | value |
|---|---|
| oracle taco pairs (unordered) | 37,301 |
| production taco pairs (unordered) | 37,301 |
| `only_oracle` (production incomplete) | 0 |
| `only_production` (production over-constrains) | 0 |
| anomalies (faces on opposite sides, or a THROUGH face at a crease) | 0 (the run refuses otherwise) |

The comparison is **order-free on both sides**. The oracle's elements come from
folded geometry alone and production's from `cons.tacos`, so no candidate layer
order enters and there is no sampled population that could be empty. A
comparator that always said "identical" would reproduce this result, which is
why `selftest` checks that `compare` detects both a difference and an identity.

Two units appear in this artifact and both are real. `taco_entries_ordered`
counts entries of `cons.tacos`, which the builder emits in both orders
(`layer_order.py:641` and `:644`); `taco_pairs_unordered` counts distinct
unordered pairs. The artifact reports taco_entries_ordered 74,602 and
taco_pairs_unordered 37,301. Gate 7 counts the first; the comparison counts the
second. Nothing went missing between them.

Clause census for scale: `equality` 28,192, `taco` 74,602, `transitivity`
4,511,932, total 4,614,726. The `taco` share of the geometric clauses
(`equality` plus `taco`, 102,794 of them) is 0.7257. `transitivity` is vacuous
on any total order and is out of scope.

**What the verdict is not.** Agreement is a completeness-and-soundness test of
production's case split over a shared input geometry. It is not a proof of the
geometry, and it never upgrades CERTIFIED to a proof of flat-foldability:
`layer_order.AREA_EPS` drops sliver cells before `cons.pairs` is built, which
can only remove constraints.

### The scope this result is bounded by

* **This witness has zero flat (`F`) edges.** The 745 edges are 384 `M` and 361
  `V` (`input_census.edge_assignments`; gate 5 reports `flat_edges` 0).
  Production's tortilla branches (`layer_order.py:583` and `:613-632`) are
  therefore **structurally vacuous on this subject**, and the `F` handling in
  `load_all` and `walk_line` is **unexercised**. The result says nothing about
  them, and it bounds every sentence above.
* **Only the crease-crease branch is tested.** The sibling collinear branch
  at `:590-611` is not independently checked here except through the
  cross-validation of `equality` (gate 9).

## 3. Why the named successor was not built

The predecessor spec named Ku & Demaine, *Folding Flat Crease Patterns with
Thick Materials* (arXiv:1601.05747, 2016), as the successor instrument. Reading
the paper refutes it three ways.

**Correction owed to the record: the predecessor cited this paper as "Tachi &
Hull" without having read it. The authors are Ku and Demaine.** The stated
rejection reason ("risk: thin offsets land in the near-degenerate regime") was
also wrong, and it implied the route was still available later. It never was.

1. **It assumes what we want to check, with the same blind spot.** Its input,
   a flat folded state, is defined so that for a crease bounding faces A and B
   and a third face C which **strictly** intersects the crease, no path in the
   reduced layer-ordering graph between A and B visits C. That is the
   predecessor's pointwise rule including the `strictly` that is the blind
   spot. Its definition never mentions the crease-crease condition, and the
   thickening algorithm consumes a layer ordering rather than verifying one.
2. **Its precondition forbids our configuration.** The algorithm requires a
   non-wrapping input, in the paper's words "no crease or boundary edge point
   of the input touches the inside of another crease". Two collinear creases
   folding back on the same side of a line is exactly one crease touching the
   inside of another, and box-pleated patterns are saturated with it.
3. **An observation about the wrapping case, not a third ground.** ⚠ This
   item originally claimed thickness is "strictly stronger than
   flat-foldability", killing the route "for any implementation". The final
   whole-branch review rejected that, correctly: the premise — that a nested
   pleat admits **no** thick realization at all — was asserted with no
   construction and no citation, and nested U-turns on one line **is** the
   wrapping case item 2 already excludes. So item 3 restated item 2 as a
   universal.

   What stands, for wrapping inputs only: where creases nest on one line, each
   fold ribbon needs width on the same side and it is not obvious a thick
   realization exists, which is consistent with the paper's Figure 6. That is a
   conjecture, not a theorem. **Items 1 and 2 carry the conclusion for this
   subject without it**, and nothing here rules out the thickened route on a
   non-wrapping subject.

The one-dimensional side of the design instead adapts the folded-strip
validity notion of Arkin, Bender, Demaine, Demaine, Mitchell, Sethia and
Skiena, "When Can You Fold a Map?" (*Computational Geometry* 29(1), 2004), an
independent body of theory. Also rejected: perturbing to break collinearity
(box-pleat collinearity is exact and structural, so a perturbed instance is a
different instance) and re-implementing the Akitaya-Demaine-Ku enumerator (both
arms would derive from the thing under test).

## 4. The oracle

For each of the collinear lines carrying creases (`collinear_lines` 29 in the
artifact):

1. **Bundle** every crease whose folded image lies on the line, by an exact
   canonical line key.
2. **Breakpoints.** Walk the line by exact rational breakpoints: every crease
   endpoint and every point where a face's span along the line starts or ends.
   Between breakpoints the configuration is constant, so one exact rational
   sample per sub-segment decides it. There is no sampling-density parameter.
3. **Cross-section at the sample.** Clip the perpendicular line against every
   face meeting the sample and read each face's strand:

   | clip of the perpendicular | strand |
   |---|---|
   | spans both sides of the sample | THROUGH (one layer, both sides) |
   | starts at the sample, extends one way | that side only |
   | degenerate touch | refuse, never guess |

4. **U-turns.** Each M/V crease containing the sample becomes a U-turn joining
   its two faces, which lie on the same side by definition.

Two conditions follow in the cross-section plane (`x` across, `z` the layer),
and nothing else does:

* **Condition 1: no arc may be pierced.** No THROUGH strand may sit strictly
  between a U-turn's two layers. This is the `equality` family.
* **Condition 2: no two arcs on the same side may interleave.** Arcs spanning
  layers a < c < b < d cross. This is the `taco` family, and the oracle's taco
  pairs are exactly the same-side U-turn pairs, emitted from geometry alone.

Arcs on opposite sides bulge opposite ways and cannot meet.

**The face-detection branch in `walk_line` is load-bearing, and measured so.**
Every THROUGH strand comes from it. Over each line's bundle faces alone, the
artifact's `face_contribution.bundle_faces_only` reports 0 of 53 samples holding
a THROUGH face; over `walk_line`'s full face set, `samples_with_a_through_face`
is 25 of 53. The clip adds 4,994 face incidences on top of the 1,490 reached
through bundle edges, and adds no new breakpoints on this witness. Without the
branch there would be no THROUGH strand, `pierce_pairs` would be empty, and the
cross-validation of gate 9 would be vacuous.

**The two-array trap was live.** `load()` returns the unreversed
`folded_vertices` and the counter-clockwise `polys`. Crease segments are read
from the first and clipping uses the second. The artifact's `input_census`
shows 190 of 380 faces with clockwise `folded_vertices` and 0 of `polys` not
counter-clockwise. Reading the wrong array would have inverted half the
windings and silently lost constraints, and a clockwise ring makes every
interior test read empty.

## 5. Independence, bounded

No oracle predicate is a transcription. `lines.py` and `strip.py` import
nothing from production, from the predecessor's modules or from `geom.py`, and
that is enforced mechanically by an AST allowlist plus a raw-source ban
(`test_allowlist.py`, with a positive control). The canonical line key, 1-D
interval overlap, the line-versus-polygon clip, side derivation, U-turn
extraction and both validity conditions are written fresh. `geom.py` is a
transcription of production (its `side_of` derives the side from the polygon
centroid, exactly the derivation condition 2 would otherwise call independent),
so using it would make bundling and side determination common-mode. The driver
calls `geom.collinear_overlap` only as a cross-check (gate 8).

What remains common-mode is **the input geometry both arms necessarily read**:
the folded coordinates and the clipping polygons, reached through
`exact_arrangement.load()`, plus the arrangement cells behind production's
`pairs` guard, which the driver reports but does not re-derive. A defect in how
a face is built is invisible to any comparison between two readings of it. So:
agreement is a completeness test of production's case split over a shared input,
and cannot be stated more strongly.

## 6. The scoping measurement

Every `taco` clause is over a **collinear** crease pair: gate 7 reports
`collinear` 74,602 of `taco_clauses` 74,602, `transversal` 0, `unresolved` 0, on
29 lines. Box-pleating puts every crease image on a grid line; two creases on
the same line overlap collinearly, and two on different lines meet at a point
that `_segs_interact`'s strict double-straddle test rejects.

Three controls were run during design, because a predicate returning `True`
unconditionally reproduces the headline: the exact predicate discriminates
transversal, parallel-offset, collinear-overlap, collinear-disjoint and
endpoint-touching cases; production's own float `_collinear_overlap` gives the
same count independently; and every pair passes `_segs_interact`. In the
driver, gate 8's cross-check reports `bundling_cross_check_agree` 74,602 with
`bundling_cross_check_disagree` 0.

The predecessor oracle therefore covered none of the `taco` clauses, not most of
them. Its remark that "subsumption holds for the transversal arm" is **true and
vacuous here**: the transversal arm is empty on this subject.

## 7. The pre-registered prediction, and its outcome

The design spec registered, before any code existed, that
`layer_order.py:633-646` applies no side test (it runs `_segs_interact`, then
the quad `pairs` guard, then emits), while its sibling at `:590-611` does. The
**prediction** was that two collinear creases folding back on **opposite** sides
of the line would yield a production `taco` clause with no geometric basis and
would surface in `only_production`. The **rival hypothesis** was that the quad
`pairs` guard at `:638-640` already excludes them.

**The prediction is FALSIFIED.** Gate 8 measured `same_side` 74,602,
`opposite_side` 0, `indeterminate` 0 over production's own taco pairs, and
`only_production` is 0. The data support the rival hypothesis. The prediction
stands recorded as it was registered and has not been reworded to fit.

The census covers production's *emitted* pairs: it shows no opposite-side pair
was emitted, which is what the rival hypothesis predicts. It does not isolate
the `pairs` guard as the mechanism by an ablation.

## 8. Gates

All gates refuse loudly; none logs and continues. Figures are from the
artifact's `gates` block. Gates 11 and 12 were added during review.

| # | gate | reported | the defect that made it necessary |
|---|---|---|---|
| 1 | `fidelity` | `bitwise_identical` true, 26 cells = 26 | the predecessor's version tested a dict for falsiness and was dead code; this one asserts on returned figures. It re-folds through its own `load()` and takes no argument |
| 2 | `faces_usable` | 380 checked, `non_convex` 0, `non_rational` 0 | a turn-sign `is_convex` admitted a clockwise square, a pentagram and an empty ring; a clockwise face makes every interior test read empty |
| 3 | `constancy` | `sub_segments_constant` 53, `boundaries_that_varied` 24 | the predecessor's probes all landed off the face and read "constant"; the positive control must observe a change. The gate reads the same partition and full face set as `walk_line` (shared `line_partition`; 25 of 53 samples hold a THROUGH face). It first read bundle-edge faces only (0 of 53), under a "coarse partition is a subset" rationale that was wrong as applied; constancy holds by face convexity (gate 2) |
| 4 | `refuses` | seeded interleaving rejected, intruder rejected, both true | an oracle that cannot reject a planted fault proves nothing |
| 5 | `accounting` | 745 edges, 745 placed, 29 lines, 745 creases, `flat_edges` 0 | an edge lost in bundling shrinks the oracle arm, and a smaller arm reads as agreement; the line count is a hard-coded expectation, never adopted from the code |
| 6 | reproducibility | verified by running the probe twice and diffing | a non-deterministic artifact cannot be audited |
| 7 | `transversal` | `collinear` 74,602, `transversal` 0 | the oracle cannot see transversal pairs, so it must stop rather than under-report |
| 8 | `sides` | `same_side` 74,602, `opposite_side` 0, `indeterminate` 0 | a `ValueError` turning every pair indeterminate would leave an empty census that reads as success, so any indeterminate pair refuses |
| 9 | `crossvalidate` | `oracle_condition1` 28,192 against `production_equality_on_these_lines` 28,192, `reproduced` 28,192, zero either way | a new instrument must reproduce an established result before its new verdict is read; gated non-vacuous |
| 10 | `untouched` | `mcp_harness_diff_empty` true, `server_box_pleat_mentions` 0 | the standing constraint, asserted in code |
| 11 | `relation_scope` | `relation_pairs` 53,754 = `cons_pairs` 53,754 of `possible_pairs` 72,010 | the certified relation spans only `cons.pairs`, since non-overlapping faces carry no order variable; an earlier design built a total order over all faces and could never work. No order is consumed anywhere in this slice |
| 12 | `face_contribution` | 1,490 face incidences via bundle edges, 4,994 added by the line clip, 25 samples with a THROUGH face of 53; bundle-faces-only control reads 0 of 53 | the clip branch adds faces, not breakpoints; if it added none there would be no THROUGH strand and gate 9 would be vacuous |

Gate 9 is the credibility of the new instrument: condition 1 of the strip, a
second formulation, reproduces the predecessor's exhaustive `equality` result on
the creases it shares. It is a cross-validation and not an independent check of
`equality`: that family was established by the predecessor.

## 9. Limitations

Carried over from the design spec without softening.

1. **The input geometry is common-mode.** Both arms read the same folded
   coordinates and the same clipping polygons. A defect in how a face is built
   is invisible to any comparison between two readings of it.
2. **The free-end modelling choice is shared with production.** A face
   terminating exactly on the line touches but does not pierce; production's
   `_spanning` requires `_strictly_inside`. This slice does not test it.
3. **One subject, one certified order.** The comparison is exhaustive over this
   subject's collinear population and says nothing about others. Whether the
   certified order passes this oracle pointwise is a separate question this
   slice does not ask.
4. **`transitivity` is untested by any instrument in this arc.**
5. **The flat (fully folded) state only.** Nothing here concerns partial folds.
6. **Convexity is shared with production's assumption.** A non-convex face would
   break both arms identically rather than being caught.
7. **A shared span endpoint between two faces** is a degenerate configuration
   sampled only in sub-segment interiors; it is covered by gate 3's breakpoint
   accounting, not by a dedicated case.
8. **Peak memory.** The predecessor's README records its measured peak, and this
   driver holds the same clause census, so it may not reproduce on a smaller
   machine. This run did not re-measure memory.

Added by this run: **zero flat edges** (section 2), so the tortilla branches
and the `F` handling here are unexercised.

## 10. Successor

With the sets identical, the remaining untested families are `transitivity`
(vacuous) and the shared modelling choices of limitations 1, 2 and 6. All are
common-mode, and none is reachable by a second reading of the same geometry. The
honest next instrument would be an independently implemented arrangement
kernel, which is a far larger piece of work and a human decision. No
thickness-based successor is available; section 3 rules out the whole class.

## 11. Reproducing

```bash
cd docs/superpowers/evidence/2026-10-05-cross-section-oracle
../../../../.venv/bin/python3 -m pytest test_allowlist.py test_lines.py test_strip.py
../../../../.venv/bin/python3 -c "import cross_section_oracle as P; print(P.selftest())"
../../../../.venv/bin/python3 cross_section_oracle.py
```

The probe writes `cross-section-oracle.json`, takes about a minute, and holds
the full clause census in memory. Two runs are bit-identical except
`elapsed_secs`. Run it with `mcp_harness/` untouched relative to `origin/main`;
gate 10 refuses otherwise.
