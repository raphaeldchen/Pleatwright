# Cross-section oracle: does `layer_certify`'s `taco` clause check mean what it says?

**Date:** 2026-10-05
**Subject:** the SAT-certified dense `lizard` witness (380 faces, 745 creases)
**Predecessor:** `docs/superpowers/specs/2026-10-04-pointwise-oracle-design.md`
**Status:** design, approved in three sections

---

## 0. Prior art (CLAUDE.md §0)

### 0.1 What was found

**Ku & Demaine, "Folding Flat Crease Patterns with Thick Materials"
(arXiv:1601.05747, 2016)** is the instrument the predecessor spec named as this
slice's successor. **Reading it refutes it, twice, and that refutation is the
reason this slice exists in its present form.**

1. **It assumes what we want to check, with the same blind spot.** Their input
   is a "flat folded state" defined verbatim as:

   > "for any crease ξ bounding faces A and B and a third face C which
   > **strictly** intersects ξ, no directed path exists in the reduced layer
   > ordering graph Γ between faces A and B visits face C"

   That is the predecessor's pointwise rule, including the `strictly` that
   **is** the blind spot. Their definition of a valid folded state never
   mentions the crease-crease (`taco`) condition at all, and the thickening
   algorithm **consumes** a layer ordering graph rather than verifying one. It
   is not a verifier.

2. **Its precondition forbids our configuration outright.** The algorithm
   requires a **non-wrapping** input — verbatim, "no crease or boundary edge
   point of the input touches the inside of another crease", where the "inside"
   is the convex side of a creased surface. Two collinear creases folding back
   on the same side of a line is precisely one crease touching the inside of
   another. Their Figure 6 shows the failure: the widened creases intersect out
   to infinity. Box-pleated patterns are saturated with exactly this.

3. **An observation about the wrapping case — NOT an independent third
   ground.** ⚠ **Qualified 2026-10-05 by the final whole-branch review, which
   was right to push on it.** This item originally read: "thickness is a
   strictly stronger property than flat-foldability … this kills the route for
   any implementation, not just theirs." That **overclaimed**, twice over.

   It rested on the premise that a nested pleat "admits **no** thick
   realization at all", which was asserted with no construction and no
   citation. And nested U-turns on one line **is** the wrapping configuration
   that refutation (2) already excludes — so (3) restated (2) as a universal
   rather than adding a ground.

   What survives, confined to the wrapping case: where creases nest on one
   line, a thick realization has to give each fold ribbon width on the same
   side, and it is **not obvious that one exists** — which is consistent with
   their Figure 6. Treat that as a conjecture about wrapping inputs, not a
   theorem about flat-folded states.

   **(1) and (2) carry the conclusion for this subject without (3).** ⚠ Do not
   cite this item to reject a thickness instrument on a **non-wrapping**
   subject: there (2) does not apply, and (3)'s premise is unsupported.

**Arkin, Bender, Demaine, Demaine, Mitchell, Sethia & Skiena, "When Can You
Fold a Map?"** (*Computational Geometry: Theory and Applications* 29(1):23–46,
2004; `erikdemaine.org/papers/MapFolding/paper.pdf`) is the source for the
one-dimensional side of this design. It establishes the validity notion for
1-D folded states and is a body of theory **independent of ADK**, which is what
keeps the two arms of the comparison independent.

**Akitaya, Demaine & Ku, "Computing Flat-Folded States" (OSME 2024)** remains
the thing **under test**, never a source for the oracle. Note the author
overlap: the Ku of ADK is the Ku of arXiv:1601.05747. Had the thickened route
survived, that overlap would itself have weakened its independence claim.

### 0.2 What was adapted

| source | adapted |
|---|---|
| Arkin et al. 2004 | the 1-D folded-strip validity notion — that the cross-section of a valid folded state is itself a valid folded state |
| predecessor slice | the exhaustive-breakpoint architecture (no sampling-density parameter), the set-comparison shape of §4A, and the gate set that survived review |
| predecessor **README §5.3, candidate A** | **the comparison itself.** That section already proposed "a taco-triple census … enumerate collinear crease pairs geometrically and compare against `cons.tacos`, the way §4A does for `equality`", and noted it "needs a side-bookkeeping rule the oracle does not currently have". This design takes that candidate and supplies the missing rule by **derivation** (§2.2) rather than assertion — which is its only contribution over the candidate as written |
| `../evidence/2026-10-04-exact-arrangement` | `kernel.py` and `exact_arrangement.load()` for the exact kernel and the folded state. **`geom.py` is deliberately NOT used by the oracle** — see §2.3; it is a transcription of production, and the oracle's predicates are written fresh so that side determination and crease bundling stay independent. The driver may call it as a cross-check |

### 0.3 What was rejected, with the reason

| rejected | reason |
|---|---|
| **Thickened/offset realization** (Ku & Demaine, arXiv:1601.05747) | §0.1(1) and §0.1(2), which suffice: it **consumes** a layer order rather than verifying one, and its definition of a valid folded state carries the same `strictly` blind spot; and its `non-wrapping` precondition excludes our input outright. ⚠ §0.1(3) is **not** a third ground — see the qualification there. |
| **Generic perturbation to break collinearity**, then run the predecessor oracle unchanged | Unsound. Which way you perturb decides the answer, and box-pleat collinearity is exact and structural — it is the pattern, not a coincidence of coordinates. A perturbed instance is a different instance. |
| **Comparing restrictions of the certified order** (the predecessor's §5 design) | **Measured vacuous there** (728 candidates, 728 in population A, 0 in B), because growth inside a shared cover satisfies production's own `pairs` guard by construction. Superseded by the set comparison in §3. |
| **Re-implementing ADK's enumerator** | Both arms would derive from ADK, testing transcription rather than the clause set. Carried forward from the predecessor. |
| **Oriedita, COrigami Appendix D, `rigid/collision_geometry.py`** | Rejected in the predecessor spec §0.3 for reasons unchanged here: local-only, our own algorithm, and structurally vacuous respectively. |

### 0.4 Corrections owed to the predecessor's record

Two defects in `2026-10-04-pointwise-oracle-design.md`, both to be fixed in
this slice:

1. **§0.3 and §12 attribute arXiv:1601.05747 to "Tachi & Hull".** It is **Ku &
   Demaine**. The paper was cited without being read.
2. **The stated rejection reason is wrong.** §0.3 says the route was rejected
   "for this slice on risk: thin offsets land in the near-degenerate regime".
   The real reason is §0.1 — a violated precondition and an unfaithful
   property. The risk framing implied the route was still available later,
   which is what made it the named successor. It never was.

---

## 1. The question

`layer_certify._satisfied`'s `taco` predicate is

```python
if family == "taco":
    return (vals[0] != vals[1]) == (vals[2] != vals[3])
```

with the four literals built at `layer_certify.py:98` as
`(_lit(r, p), _lit(r, q), _lit(s, p), _lit(s, q))` for creases `(p, q)` and
`(r, s)`. It reads: crease 2's two faces are either **both** between crease 1's
faces, or **neither** is. Its producer is the crease×crease loop at
`layer_order.py:633-646`.

The predecessor slice established the `equality` family exhaustively
(28,192 = 28,192, zero in either direction) and left `taco` untested, because
its oracle's `covering` is a strict-interior test and a collinear crease's
faces meet the line only on their boundary. This slice asks whether the `taco`
predicate and its producing branch mean what they say.

### 1.1 What the scoping measurement changed

The predecessor spec recorded that the subsumption argument "was true for the
transversal arm and false for the collinear one". That is still true and
**vacuous on this subject**:

| population | count |
|---|---|
| `taco` clauses, total | **74,602** |
| over **collinear** crease pairs | **74,602** |
| over **transversal** crease pairs | **0** |
| distinct lines carrying them | **29** |

So the predecessor oracle covers **0 of 74,602** `taco` clauses, not most of
them. The blindness is total, not partial. **This narrows a claim of mine that
read as partial coverage.**

The mechanism: box-pleating puts every crease image on a grid line. Two creases
on the **same** grid line overlap collinearly; two on **different** grid lines
meet at a point that `_segs_interact`'s strict double-straddle test rejects.
Hence no transversal `taco` arises at all.

### 1.2 Controls on that measurement

A predicate returning `True` unconditionally reproduces the headline exactly,
so three controls ran. All passed.

| control | result |
|---|---|
| **C1** the exact predicate discriminates: transversal crossing / parallel offset / collinear overlap / collinear disjoint / endpoint-touching | `False` / `False` / `True` / `False` / `False` |
| **C2** production's own float `layer_order._collinear_overlap` over the same 74,602 pairs — an independent second count | **74,602**, exact agreement |
| **C3** all pairs pass production's `_segs_interact`, so C2 splits that gate rather than measuring a different population | **74,602 of 74,602** |

### 1.3 Clause census for scale

| family | count | share of geometric | share of all |
|---|---|---|---|
| `equality` | 28,192 | 27.4% | 0.6% |
| `taco` | 74,602 | **72.6%** | 1.6% |
| `transitivity` | 4,511,932 | — | 97.8% |
| **TOTAL** | 4,614,726 | | |

Geometric total 102,794. `transitivity` is vacuous on any total order and stays
out of scope (§7).

---

## 2. The oracle

### 2.1 Construction

For each of the 29 lines `L` carrying collinear creases:

1. **Bundle.** Collect every crease whose folded image lies on `L`, and every
   face whose closure meets `L`.
2. **Breakpoints.** Walk `L` by exact rational breakpoints: every crease
   endpoint, and every point where a face's span along `L` starts or ends.
   Between consecutive breakpoints the configuration is constant, so **one
   exact rational sample per sub-segment decides the whole sub-segment.** There
   is no sampling-density parameter, as in the predecessor.
3. **Cross-section at the sample `p`.** Clip the **perpendicular line** through
   `p` against each face whose closure meets `p`, giving a span `[t_lo, t_hi]`
   in the perpendicular parameter with `t = 0` at `p`. One quantity yields the
   whole classification:

   | reading | strand |
   |---|---|
   | `t_lo < 0 < t_hi` | **through** — spans both sides at one layer |
   | `t_lo = 0 < t_hi` | **right** |
   | `t_lo < 0 = t_hi` | **left** |
   | `t_lo = t_hi = 0` | degenerate vertex touch → **refuse, never guess** |

4. **U-turns.** Each M/V crease on `L` whose segment contains `p` becomes a
   **U-turn** joining its two faces, which lie on the **same** side — that is
   what folding over means. Each flat (uncreased) edge on `L` becomes a
   through-strand realized as two faces, one each side.
5. **Order.** Order the strands by the candidate layer order. The result is a
   one-dimensional folded strip.

### 2.2 The validity rule

Derived in the cross-section plane with `x` the perpendicular coordinate and
`z` the layer. A U-turn between layers `z_a` and `z_b` is an arc at `x = 0`
sweeping every layer between them. Two conditions follow, and nothing else
does:

1. **No arc may be pierced.** No *through*-strand may sit strictly between a
   U-turn's two layers — the arc passes through `(0, z_c)` and the
   through-strand occupies it. This is the `equality` family (taco-tortilla).
2. **No two arcs on the same side may interleave.** Arcs spanning layers
   `a < c < b < d` cross. This is the `taco` family.

Arcs on **opposite** sides bulge opposite ways in `x` and cannot meet. That is
the geometric content of production's side bookkeeping at `:590-611`.

Tortilla-tortilla along `L` (`:613-632`) needs no third condition: each flat
edge is one strand at one layer, so "the relation on the left equals the
relation on the right" holds by construction in this model.

**A face terminating exactly at `L` is a free end.** Its endpoint lies *on* the
arc but does not pierce it — a measure-zero touch, not a penetration, which is
why production's `_spanning` requires `_strictly_inside` (`:547-566`). **This
modelling choice is shared with production, not independent**, and is recorded
as a limitation (§8).

### 2.3 Independence, bounded up front

The predecessor spec initially overclaimed independence and had to be corrected
under review. The bound is stated here before any code exists.

⚠ **Revised 2026-10-05 after reading `geom.py`, and the revision TIGHTENS the
boundary rather than loosening it.** The predecessor reused `geom.clip_seg` and
`geom.strictly_inside` deliberately, and this spec first conceded the same for
the clipping primitive. Three facts changed that:

- `geom.side_of` **is** production's `_side_of`, and it derives the side from
  the polygon **centroid** — which is precisely the derivation §2.2 would
  otherwise have called independent. Using it makes side determination
  common-mode.
- `geom.collinear_overlap` and `geom.segs_interact` are likewise
  transcriptions. Bundling creases with them would make the **bundling**
  common-mode, and a shared defect there means both arms miss the same bundles
  and **agree silently** — the worst available failure.
- The oracle needs a **line**-vs-convex-polygon clip returning an **unclamped**
  parametric interval. Production has no such routine: `_clip_seg` clamps to
  `[0, 1]` and carries its own parallel-case epsilon logic. So there is nothing
  to re-transcribe, and therefore **no bitwise-fidelity risk to reopen** —
  which was the entire reason the predecessor reused `geom`.

**Therefore `strip.py` and `lines.py` import nothing from `geom`.** Every
predicate they use — the canonical line key, 1-D interval overlap, the
line/polygon clip, the side derivation, U-turn extraction, and both validity
conditions — is written for this slice and is not a transcription of anything.
The AST allowlist bans `geom` from both files alongside the production modules.

What remains common-mode is **irreducible and must be named**:

- **The folded coordinates** (`flat_fold`) and **the clipping polygons**
  (`layer_order._polys_of`), reached through `exact_arrangement.load()`. Both
  arms read the same geometry; a defect in how a face is *built* is invisible
  to any comparison between two readings of it.
- **The arrangement cells** behind production's `pairs` guard, which the driver
  reports on but the oracle does not re-derive.

What is independent:

- **Every predicate in the oracle arm**, per the paragraph above.
- **The case analysis.** Production reaches these constraints through three
  collinear branches — crease×tortilla (`:590-611`), tortilla×tortilla
  (`:613-632`), crease×crease (`:633-646`) — each with its own side
  bookkeeping. The oracle reaches them through one uniform strip rule.

**Therefore.** Agreement is a **completeness test of production's case split**
over a shared input geometry, not a proof of that geometry. It cannot be stated
more strongly. The predecessor's `geom` transcriptions are kept available to
the **driver** as a cross-check only — gate 8 compares the oracle's bundling
against `geom.collinear_overlap`, which is control C2 of §1.2 promoted to a
gate — never as the oracle's own machinery.

---

## 3. What is compared

Not restrictions of the certified order — that design measured vacuous in the
predecessor (§0.3). Instead the §4A set-comparison shape that worked, lifted
from triples to crease pairs. This is candidate A of the predecessor README §5.3,
not a new idea; what §2 adds is a *derived* side rule in place of the ad-hoc one
that candidate was missing.

**Oracle side.** From condition 2 alone: for every line, every sub-segment
sample, and every side, every unordered pair of distinct same-side U-turns
yields one canonical object

```
(frozenset({fa1, fb1}), frozenset({fa2, fb2}))
```

as a `frozenset` of the two crease-face-pairs, so the object is orientation-free.

**Production side.** `cons.tacos` holds two ordered entries per unordered pair
(`:641` and `:644`); both canonicalize to the same object.

**Verdicts.**

| outcome | meaning |
|---|---|
| sets identical | production's `taco` branch is **complete and sound** on this subject's collinear population |
| `only_oracle` non-empty | the physical picture demands a non-interleaving constraint production **never emits** → **production incomplete** |
| `only_production` non-empty | production emits a constraint the geometry does not support → **production over-constrains** |

Every non-empty difference carries bounded witnesses in the artifact.

---

## 4. Architecture

### 4.1 Files

New evidence directory `docs/superpowers/evidence/2026-10-05-cross-section-oracle/`.

| file | responsibility |
|---|---|
| `lines.py` | the exact canonical line key; grouping 745 creases into the 29 collinear bundles; the controlled `collinear_overlap` predicate of §1.2 |
| `strip.py` | `perp_span`, strand classification, U-turn extraction, conditions 1 and 2, `taco_pairs`, `accepts`. **No production imports** |
| `cross_section_oracle.py` | driver: `load_all`, the gates of §5, the set comparison of §3, `selftest`, `main`, artifact emission |
| `test_strip.py` | unit tests, hand-derived fixtures |
| `test_lines.py` | unit tests, hand-derived fixtures |
| `cross-section-oracle.json` | the artifact |
| `README.md` | the write-up |

`strip.py`'s no-production-imports rule is enforced mechanically, exactly as in
the predecessor: an AST allowlist on its import nodes plus a **raw-source** ban
on the production module names. The predecessor's test was once *relaxed to fit
a docstring that named a banned module*; here the docstring cites `geom.py` by
file and line instead, and the scan runs on raw source with no
docstring-stripping step.

### 4.2 Reuse

`kernel.py`, `geom.py` and `exact_arrangement.load()` from the 10-04 evidence
directories, imported rather than copied. Production entry points
(`layer_order.constraints_for`, `layer_certify.clauses`, `sat_order.solve`) are
called by the **driver** only, never by `strip.py`, and are **injected as
arguments** into the comparison function so the comparison is unit-testable
without a production import.

### 4.3 Data flow

```
exact_arrangement.load()  ->  folded state + exact convex polys
layer_order.constraints_for  ->  cons  ->  cons.tacos          (production arm)
sat_order.solve  ->  CERTIFIED relation                         (the order)
lines.bundles  ->  29 lines
  per line: strip.breakpoints -> exact samples
    per sample: strip.perp_span -> strands -> U-turns
      strip.taco_pairs                                          (oracle arm)
compare(oracle_pairs, production_pairs)  ->  verdict + witnesses
```

---

## 5. Gates

Six carried forward from the predecessor because they earned their place, and
four new. Every gate refuses loudly; none logs a warning and continues.

**Carried forward.**

1. **Geometry fidelity** — the transcription's arrangement cells must be
   bitwise identical to production's (26 cells). This gate once tested a dict
   for falsiness and was dead code wearing a gate's name; it must assert on the
   returned figures.
2. **Faces usable** — every face convex and rational. `is_convex` must be the
   **corrected half-plane form**: `len(poly) >= 3`, strictly positive shoelace
   area, and for every directed edge every vertex `cross >= 0`. The earlier
   turn-sign version admitted a clockwise square, a pentagram, an all-collinear
   ring and an empty list — and a clockwise face makes `covering` return the
   empty set where a CCW one returns a non-empty cover.
3. **Sub-segment constancy** — within each sub-segment the strand
   classification must be constant, probed at three interior points, **with a
   positive control** that the classification *can* vary across a breakpoint.
   Without the control this gate reads "constant" when all probes land off the
   face, which is exactly how it failed in the predecessor.
4. **Oracle refuses** — a seeded interleaving must be rejected, and an intruder
   face must be rejected. Positive and negative control both required.
5. **Exhaustive accounting** — every one of the 29 lines visited; every crease
   on each line classified; counts reconciled against the 745 total.
6. **Artifact reproducibility** — a second run must be bit-identical except
   `elapsed_secs`.

**New.**

7. **G-transversal** — refuse if any `taco` clause is over a non-collinear
   crease pair. The oracle cannot see those. Today's measurement says there are
   none; if that changes the probe must **stop**, not silently under-report.
8. **G-sides** — census production's taco crease pairs as same-side versus
   opposite-side, and separately report how many opposite-side pairs the quad
   `pairs` guard at `:638-640` already excludes. This measures §6 either way.
9. **G-crossvalidate** — the strip's **condition 1**, restricted to these 29
   lines, must reproduce the predecessor oracle's `equality` triples on the same
   creases. The new instrument proves itself against an already-established
   result before its condition-2 verdict is believed. **Gated non-vacuous: the
   reproduced count must be > 0**, or the control has established nothing.
10. **G-untouched** — `git diff` over `mcp_harness/` must be empty, and
    `grep -c box_pleat mcp_harness/server.py` must stay 0.

---

## 6. A pre-registered prediction

`layer_order.py:633-646` applies **no side test**: `_segs_interact`, then the
quad `pairs` guard, then emit. Its sibling collinear branch at `:590-611` *does*
check sides (`sa == sb`, then `_side_of(polys[x], ...) == sa`).

**Prediction:** two collinear creases folding back on **opposite** sides of `L`
yield a production `taco` clause with no geometric basis, and so appear in
`only_production`.

**Rival hypothesis:** the quad `pairs` guard already excludes them, because
`pairs` is built from positive-area cell co-occupancy and opposite-side faces
meet only within the line. The predecessor discharged this same rival for a
different branch; here it is **measured, not asserted**, by gate 8.

Recording the prediction before the run is deliberate: it makes the result
falsifiable rather than a story assembled afterwards.

---

## 7. Scope and non-goals

- **One subject**: the SAT-certified dense `lizard`. No breadth claim.
- **`transitivity` stays out of scope** — 97.8% of all clauses, vacuous on any
  total order.
- **The transversal `taco` arm is out of scope** because it is **empty** here
  (§1.1), not because it is uninteresting. Gate 7 enforces that.
- **No production file is modified.** `layer_order.py`, `layer_certify.py`,
  `box_pleat/layers.py` and `box_pleat/cores.py` are read-only by standing
  constraint.
- **Agreement never upgrades CERTIFIED to a proof.** `layer_order.AREA_EPS`
  drops sliver arrangement cells before `cons.pairs` is built, and a dropped
  cell removes constraints and can never add one. This slice verifies the
  **clause set**, not flat-foldability.

---

## 8. Limitations

1. **The input geometry is common-mode** (§2.3): both arms read the same folded
   coordinates from `flat_fold` and the same clipping polygons from
   `layer_order._polys_of`. A defect in how a face is *built* is invisible to any
   comparison between two readings of it. The oracle's own predicates are not
   transcriptions, so this is the irreducible residue rather than a choice.
2. The **free-end modelling choice** — a face terminating exactly on `L` touches
   but does not pierce — is **shared with production**, so this slice does not
   test it. It is the degenerate neighbour of the collinear overlap and belongs
   in any successor's test matrix.
3. One subject, one certified order. The comparison is exhaustive over that
   subject's collinear population and says nothing about others.
4. `transitivity` is untested by any instrument in this arc.
5. The oracle tests the **flat** (100%) state only. Nothing here concerns
   partial folds.
6. Convexity is required of every face and is **shared** with production's own
   assumption, so a non-convex face would break both arms identically rather
   than being caught.
7. A shared span **endpoint** between two faces is a degenerate configuration
   this design samples only in sub-segment interiors; it is covered by gate 3's
   breakpoint accounting but not by a dedicated case.
8. Peak memory on the predecessor reached 2,454 MB and may not reproduce on a
   smaller machine. The clause census here is of the same order.

---

## 9. Successor

If §3 reports `only_oracle` non-empty, the finding is that production's `taco`
branch is incomplete, and the next work is a **repair** in `layer_order.py`
under its own spec and a serve-path scorecard run — not another oracle.

If §3 reports `only_production` non-empty and gate 8 confirms the side
mechanism of §6, the finding is a spurious-constraint class, and the next work
is likewise a repair.

If the sets are identical, the remaining untested families are `transitivity`
(vacuous) and the shared modelling choices of §8.1/§8.2/§8.6 — all
**common-mode**, none reachable by a second reading of the same geometry. The
honest next instrument would then have to be an independently implemented
arrangement kernel, which is a far larger piece of work and explicitly a human
call, not a default.

**No thickness-based successor is available for a subject like this one** —
box-pleated, and therefore saturated with wrapping — because §0.1(2) excludes
it by the construction's own stated precondition. ⚠ That is **not** a claim
about every flat-folded state: §0.1(3), which would have made it one, is
qualified there as an unproven observation about the wrapping case. On a
non-wrapping subject the thickened route is still on the table and would have
to be judged on its merits.
