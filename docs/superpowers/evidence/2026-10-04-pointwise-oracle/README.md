# Does `layer_certify`'s clause check mean what it says? A pointwise oracle

**Date:** 2026-10-04/05 · **Subject:** dense `lizard`, the SAT-certified
witness (`sat_verdict` `CERTIFIED`) ·
**Spec:** [`../../specs/2026-10-04-pointwise-oracle-design.md`](../../specs/2026-10-04-pointwise-oracle-design.md)

**Answer, in two parts, and the second part is not what the spec expected.**

**The designated headline — §4A's exhaustive triple comparison — is
`identical`.** Over all 380 faces and all 745 creases, with no sampling: the
geometry yields **28,192** `(x, {fa, fb})` triples, production's `equality`
clauses yield **28,192**, **0** only-oracle (production missed nothing), **0**
only-production (no constraint without geometric support), and **0** oracle
triples that production's `pairs` guard would have blocked.

**The secondary order-set comparison (§5.1) `DISAGREEMENT`s on all 25 sampled
subsets**, and that disagreement is reported here as the result rather than
adjusted away. It runs in **one direction only**: the restricted clause set
admits strictly *fewer* orders than the oracle on every subset
(`rows_with_only_clauses` **0** of 25 — the oracle rejects no order production
admits), the gap localises **entirely to the `taco` family** (on `equality`
alone the two arms are identical on **25 of 25** subsets, with
`clauses_admit == oracle_admits` exactly), and **every** clause that rejects an
only-oracle witness order is a `taco-taco` whose crease pair is
**collinear-overlapping** (**164 of 164**, `rejecting_taco_crease_pairs`
`{"collinear": 164}`). That is precisely the configuration
`layer_order._collinear_overlap`'s own docstring (`layer_order.py:415-423`)
says the spanning-face rule cannot see.

So the secondary disagreement is evidence about **this probe's oracle**, not
about production: it shows the uniform rule does **not** subsume the collinear
taco-taco case, which production reaches through a fifth, separately
book-kept branch. Adjudication beyond that is a human call (§8); this document
reports both verdicts and the witnesses.

Both verdicts live in the artifact as `headline_verdict` (`identical`) and
`secondary_verdict` (`DISAGREEMENT`). Note the artifact also carries a
top-level **`verdict`**, which is the **conservative conjunction** of the two —
`identical` only if *both* are, so it reads **`DISAGREEMENT`** on this run. A
consumer reading `verdict` alone therefore sees the disagreement, never the
clean headline on its own; the two component keys are the ones to read when the
distinction matters.

The validation reading (§5.3) is clean: the shipped certified order restricted
to each subset is pointwise-accepted by the oracle on **25 of 25** subsets,
`validation_failures` **0**.

**A clean headline does NOT make dense `lizard` flat-foldable.** §9 below is
the part of this document that constrains what may be cited — in particular
that `transitivity` is **97.8%** of the clause set and is **not under test**,
that the geometric predicates are **common-mode** with production, and that an
empty population B is **evidence of absence, not a test performed**.

Every figure in this document is a field of
[`pointwise-oracle.json`](pointwise-oracle.json), written by
`pointwise_oracle.py` in the run described here (`sys_platform` `darwin`,
Python `3.14.3`, `kernel` `exact`, `elapsed_secs` 72.1).
Figures that are *not* in that file are either marked **derived** with their
operands shown, or are one of exactly three **README records** from the same
run's console output: the `--selftest` pass count (16 of 16), the wall clock
(72.17 s) and the peak resident set size (2,454 MB), the latter two from
`/usr/bin/time -l`.

⚠ **Those three timing/memory numbers, and `elapsed_secs` itself, are records
of a machine, not measurements of the subject — they are the only values here
that do not reproduce.** The artifact was regenerated on 2026-10-05 when
`families_under_test` was renamed (§9.12), and every other field came back
**bit-identical** to the previous run (97,935 bytes vs 97,935, zero differing
values across all nested structures); only `elapsed_secs` moved, 129.2 → 72.1,
with the wall clock 129.52 s → 72.17 s and peak RSS 2,122 MB → 2,454 MB on a
differently loaded host. Cite the figures, never the clock.

Reproduce:

```bash
cd docs/superpowers/evidence/2026-10-04-pointwise-oracle
../../../../.venv/bin/python3 pointwise_oracle.py --selftest   # 16 guards
../../../../.venv/bin/python3 pointwise_oracle.py              # the run
../../../../.venv/bin/python3 -m pytest test_stacks.py test_restrict.py -v
```

---

## 1. Why this exists

`mcp_harness/layer_certify.py:17-21` states the limit of its own verdict:

> ⚠ CERTIFIED IS NOT FLAT-FOLDABLE. `layer_order.AREA_EPS` drops sliver
> arrangement cells before `cons.pairs` is built, and a dropped cell REMOVES
> constraints and can never add one. So CERTIFIED means "certified against the
> constraint set that survived AREA_EPS", which is strictly weaker than a
> proof. Closing that is separate work.

[`../2026-10-04-exact-arrangement`](../2026-10-04-exact-arrangement/README.md)
closed the **arithmetic** half of that on this subject, across all three
epsilons, and recorded what remained:

> The remaining distance to a flat-foldability proof is not arithmetic: it is
> `layer_certify`'s clause check meaning what it says.

This probe addresses that sentence. The arithmetic is settled; the question
here is whether the **clause set is the right set**.

---

## 2. What the oracle is

One rule, applied everywhere:

> A crease **joins** two faces. The paper is continuous across it, so nothing
> can pass between them. Therefore at **every point** of a folded crease image,
> the crease's two faces must be **adjacent** in the stack of faces covering
> that point.

Operationally (`stacks.py`): take a crease's folded segment; cut it with
`geom.clip_seg` against every other face and collect the clip endpoints as
**breakpoints**; at each sub-segment's exact rational midpoint collect the
faces whose **strict interior** contains it; reject if any of them sits
strictly between the crease's two faces in the stack the candidate order
induces.

**Why it is an independent reading.** The rule is derived from physical
connectivity, not from Akitaya–Demaine–Ku's family taxonomy. It never reads
`cons.direct`, `cons.slots`, or the M/V labels: it takes an order and asks
whether the geometry permits it. `stacks.py` imports no production module, and
`test_stacks.py::test_imports_are_allowlisted` pins that structurally with an
AST allowlist rather than by convention.

**⚠ The independence is scoped, and the scope matters (§2.2 of the spec).** The
*predicates* are **not** independent and are production's on purpose:
`geom.clip_seg` and `geom.strictly_inside` are documented transcriptions of
`layer_order._clip_seg` and `_strictly_inside`, reused so that a difference
cannot be ambiguous between arithmetic and a divergent rewrite. The consequence
must be stated wherever this probe is cited: **a bug inside `clip_seg` or
`strictly_inside` is common-mode across both arms and this comparison cannot
see it.** What *is* independent is the **case analysis**.

**Why one sample per sub-segment is exhaustive, not approximate.** The covering
set changes only where some face's clip span starts or ends, and the
breakpoints are exactly those parameter values. Within a sub-segment the
covering set is invariant, so one exact rational sample decides the whole
interval. There is no sampling density parameter and no sampling error. This is
the design's load-bearing claim, so it is **measured rather than asserted**:
the driver's `gate_breakpoints_constant` evaluated the cover at three distinct
interior points of **363** real sub-segments and required all three to agree.

---

## 3. The five branches, and what agreement tests

Production derives "nothing lies between a joined pair" through **five separate
geometric branches**, each with its own side bookkeeping:

| # | branch | site |
|---|---|---|
| 1 | `_spanning` over creases — taco-tortilla | `layer_order.py:547`, called `:580` |
| 2 | `_spanning` over tortillas — tortilla-tortilla | called `:583` |
| 3 | crease × tortilla collinear overlap — taco-tortilla along a flat edge | `:590-612` |
| 4 | tortilla × tortilla collinear overlap | `:613-631` |
| 5 | crease × crease — the `taco` family | `:633-646` |

Correctness requires the case analysis to **miss no case**. A single uniform
rule reaches the same condition at every segment, so agreement between the two
is a **completeness test of the case split** — which no existing test in this
repository performs.

The result is that branch 1 passes that test exactly (§4) and branch 5's
**collinear arm does not**, in the direction that the *oracle* is the
incomplete one (§5). Branches 2–4 remain **vacuous on this subject**:
`box_pleat/emit.py:31` drops every `F` piece, so `tortillas` is empty, and the
measured `shared_edges_by_assignment` here is **384 M, 361 V, no F edges** out
of 745.

---

## 4. The headline: the triple comparison (§4A)

A triple is `(x, {fa, fb})`: face `x` against the crease joining `fa` and `fb`.
The oracle emits it iff the crease image crosses `x`'s **strict interior** — no
`pairs` guard, no cell membership, geometry only. Production's side is
recovered from each `equality` clause, whose two variables are `_lit(x, fa)`
and `_lit(x, fb)`.

Exhaustive over all **380** faces and all **745** creases. Nothing is sampled,
so nothing can be steered.

| quantity | measured |
|---|---|
| oracle triples | **28,192** |
| production `equality` triples | **28,192** |
| production `equality` clauses | 28,192 |
| **only-oracle** (production missed a constraint) | **0** |
| **only-production** (a constraint with no geometric support) | **0** |
| oracle triples blocked by production's `pairs` guard (`layer_order.py:555-558`) | **0** |
| `identical` | **true** |

The last row is a **separate measurement, not a corollary** of only-oracle
being 0. Zero only-oracle already implies the guard blocked nothing, but the
guard census is a statement about production's structure in its own right — it
says the one branch the earlier subset-sampling design could never reach is
empty here — so the driver counts it directly.

**Why this is the headline rather than §5.1.** The subset sampling §5.1 runs
over was measured **vacuous** by the Task 2 review: `candidate_subsets` grows a
subset from faces sharing a cell with the seed, which satisfies production's
`(x,fa) ∈ pairs ∧ (x,fb) ∈ pairs` guard **by construction** — it steers away
from the one structural gap the probe existed to expose. This run reproduces
that: **728** candidate subsets, **728** classified A, **0** classified B.

---

## 5. The secondary comparison disagrees — on every subset

Per subset, the designated comparison is set equality between *the orders the
restricted clause set admits* and *the orders the oracle admits*, both counts
and both difference directions reported (not "do both say foldable").

### 5.1 The table

25 subsets, all population A, all of size 8 (**40,320** orders each).
`eq-only` is the same comparison against the `equality` family alone — a
diagnostic, not a substitute: each row's `identical` is taken over the full
restricted geometric clause set.

| # | pop | \|S\| | creases | clauses (eq/taco) | orders | sites act/tot | oracle_admits | clauses_admit | identical | eq-only identical | shipped order ok |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | A | 8 | 10 | 22 (12/10) | 40320 | 3/14 | 1680 | 154 | false | true | true |
| 2 | A | 8 | 9 | 18 (6/12) | 40320 | 2/17 | 6720 | 592 | false | true | true |
| 3 | A | 8 | 10 | 22 (8/14) | 40320 | 2/16 | 4608 | 224 | false | true | true |
| 4 | A | 8 | 9 | 20 (8/12) | 40320 | 2/16 | 4608 | 388 | false | true | true |
| 5 | A | 8 | 9 | 18 (6/12) | 40320 | 2/17 | 6720 | 592 | false | true | true |
| 6 | A | 8 | 10 | 22 (8/14) | 40320 | 2/16 | 4608 | 224 | false | true | true |
| 7 | A | 8 | 9 | 18 (8/10) | 40320 | 2/15 | 4608 | 604 | false | true | true |
| 8 | A | 8 | 9 | 20 (8/12) | 40320 | 2/16 | 4608 | 388 | false | true | true |
| 9 | A | 8 | 9 | 20 (6/14) | 40320 | 2/14 | 6720 | 484 | false | true | true |
| 10 | A | 8 | 9 | 18 (6/12) | 40320 | 2/17 | 6720 | 596 | false | true | true |
| 11 | A | 8 | 9 | 20 (6/14) | 40320 | 2/14 | 6720 | 484 | false | true | true |
| 12 | A | 8 | 9 | 24 (10/14) | 40320 | 2/13 | 3360 | 320 | false | true | true |
| 13 | A | 8 | 9 | 20 (6/14) | 40320 | 2/14 | 6720 | 484 | false | true | true |
| 14 | A | 8 | 10 | 22 (12/10) | 40320 | 3/14 | 1680 | 154 | false | true | true |
| 15 | A | 8 | 9 | 20 (6/14) | 40320 | 2/14 | 6720 | 484 | false | true | true |
| 16 | A | 8 | 9 | 18 (6/12) | 40320 | 2/17 | 6720 | 596 | false | true | true |
| 17 | A | 8 | 8 | 20 (12/8) | 40320 | 3/12 | 1680 | 308 | false | true | true |
| 18 | A | 8 | 8 | 14 (6/8) | 40320 | 2/15 | 6720 | 1232 | false | true | true |
| 19 | A | 8 | 8 | 20 (8/12) | 40320 | 2/12 | 4608 | 384 | false | true | true |
| 20 | A | 8 | 8 | 18 (6/12) | 40320 | 2/15 | 6720 | 596 | false | true | true |
| 21 | A | 8 | 8 | 14 (6/8) | 40320 | 2/15 | 6720 | 1232 | false | true | true |
| 22 | A | 8 | 8 | 18 (10/8) | 40320 | 2/11 | 3360 | 600 | false | true | true |
| 23 | A | 8 | 8 | 20 (8/12) | 40320 | 2/12 | 4608 | 384 | false | true | true |
| 24 | A | 8 | 8 | 14 (6/8) | 40320 | 2/15 | 6720 | 1232 | false | true | true |
| 25 | A | 8 | 8 | 20 (12/8) | 40320 | 3/12 | 1680 | 308 | false | true | true |

### 5.2 The diagnosis, measured

`secondary_diagnosis` from the artifact:

| quantity | measured |
|---|---|
| rows | 25 |
| `rows_identical` | **0** |
| `rows_with_only_oracle` (oracle admits, clauses reject) | **25** |
| `rows_with_only_clauses` (clauses admit, oracle rejects) | **0** |
| `rows_oracle_admits_superset` | **25** |
| `rows_identical_on_equality_only` | **25** |
| `rejecting_clauses_by_family` | `{"taco": 164}` |
| `rejecting_taco_crease_pairs` | `{"collinear": 164}` |

Read in order, those rows say:

1. The disagreement is **one-directional**. `only_clauses` is empty on every
   row, so the oracle never rejects an order production admits. On these
   subsets the restricted clause set is **strictly stronger** than the oracle.
2. The gap is **not** in the `equality` family. On `equality` alone the arms
   are identical on all 25 subsets, and `clauses_admit == oracle_admits`
   exactly — which is the subset-level echo of §4's 0 / 0.
3. Every clause that rejects an only-oracle witness order is a **`taco-taco`**
   (`rejecting_clauses_by_family` names no other family), and every one of
   their crease pairs is **collinear-overlapping** (164 of 164). Sample
   provenances for subset 1: `taco-taco (4, 5)x(4, 89)`,
   `taco-taco (4, 89)x(4, 5)`, `taco-taco (4, 5)x(5, 6)`.

The mechanism is the **oracle's**, and production documents it. Branch 5
handles crease × crease through `_segs_interact`, which has two arms: a
transversal crossing and a collinear overlap.
`layer_order._collinear_overlap`'s docstring (`layer_order.py:415-423`) draws
exactly the distinction that decides whether the oracle can see the
configuration at all —

> a transversal crossing puts part of each segment strictly inside the other's
> faces and is therefore already covered by the spanning-face rule, whereas a
> shared segment is not (each face's boundary runs along it, so
> `_strictly_inside` is False by construction)

— and the oracle's `covering` is a **strict-interior** test by design (§2.3: a
face whose *boundary* runs along the crease is not threading the fold). So two
creases that fold back along a **shared segment** produce no oracle site at
all, while production emits a `taco` clause for them.

**Consequence for citation, and it is carried in the code.** The claim this run
falsified was `stacks.py`'s subsumption bullet, and that bullet **was corrected
in place, with the measurement** — `stacks.py:39-51` now reads

> two creases interleaving IS taco-taco -- BUT ONLY WHEN THEY CROSS
> TRANSVERSALLY. ⚠ MEASURED FALSE FOR THE COLLINEAR ARM, 2026-10-05.

and closes

> Consequence: the `taco` family is NOT independently checked by this module --
> 164 of 164 clauses that rejected an order this module admitted were tacos over
> a collinear-overlapping crease pair. The `equality` family IS checked, and
> agrees exactly

The spec's parallel bullet in **§2.2** carries the same correction in place, and
spec **§1**, **§5.2** and limitation **12** carry the scope consequence.

One residual, stated rather than glossed: `stacks.py:37`'s *lead-in* still says
*"It subsumes all three families:"*, which the bullet three lines below it
immediately narrows. The lead-in was left as-is because `stacks.py` is the
module whose import surface is pinned structurally and this slice touches it as
little as possible; the spec's equivalent lead-in **was** narrowed (to "two of
the three"). A reader of `stacks.py` reaches the correction within the same
docstring, but the sentence on its own over-reads.

**What this does and does not license.** It does **not** show production
emitted a constraint it should not have — but the reason is *not* the signature
`only_clauses = 0`, which is **identical under both hypotheses** ("the oracle is
blind" and "production over-constrains") and therefore distinguishes neither.
What discharges the rival hypothesis is structural, and was **derived in the
whole-branch review of 2026-10-05** and verified line by line against
`mcp_harness/layer_order.py`:

Production's taco-taco branch (`layer_order.py:633-646`) does **no side
bookkeeping**, unlike its collinear siblings — branch 3 (`:590-612`) requires
`sa == sb` (`:596-597`, commented *"not a fold-back onto one side: no taco
here"*) and branch 4 requires `set(A) == {1, -1}` (`:622`). So there is a
concrete over-constraining mechanism to rule out: two collinear tacos folding
back onto **opposite** sides of the shared line occupy **disjoint** half-planes,
and a taco-taco clause relating them would be **spurious**.

It is discharged anyway, by the **quad guard at `:639`**, which requires all
four cross-pairs to be in `pairs`. `pairs` (`:523-524`) is built from
co-occupancy of **positive-area** arrangement cells — `_cells` / `_split_convex`
drop every piece with `|area| <= AREA_EPS` (`:307`, `:310-311`) — and each
crease face carries the crease segment as a **full polygon edge** (`_seg_of`,
`:527-531`) and is **convex** (gate §6.5: 380 faces, **0** non-convex), so it
lies entirely within **one closed half-plane** of that line. Two faces in
opposite closed half-planes meet only *within the line* — zero area — so they
can never co-occupy a positive-area cell and never enter `pairs`. **The `pairs`
guard silently discharges the side condition branch 5 omits**, so no spurious
opposite-side taco-taco clause can be emitted, and the one-directional
disagreement is attributable to the **oracle's** blind spot.

What this run does show positively is that **§5.1's comparison validates the
`equality` family only**, and that the `taco` family on this subject is **not
independently checked by this instrument**.

### 5.3 Successor

Spec §12's trigger condition is met literally: §5.1 reported a difference, and
§12 names the **thickened/offset realization** as the next instrument. Two
candidates now exist and the choice is a human call:

⚠ CORRECTED 2026-10-05: this paper is **Ku & Demaine**, *Folding Flat Crease Patterns with Thick Materials* — it was cited here as "Tachi & Hull" without being read. And the rejection reason below was wrong. See `../specs/2026-10-05-cross-section-oracle-design.md` §0.1/§0.4.

⚠ **RESOLVED 2026-10-05: candidate A was taken, and candidate B is refuted.**
The thickened route is dead for any implementation — see the correction note
above. Candidate A was built, with the side rule *derived* from a perpendicular
cross-section rather than asserted.

* **A taco-triple census**, the cheaper and more targeted one, because the
  oracle's blind spot is *identified* rather than mysterious: enumerate
  collinear crease pairs geometrically and compare against `cons.tacos`, the
  way §4A does for `equality`. This needs a side-bookkeeping rule the oracle
  does not currently have, so it is no longer a *uniform*-rule check.
* **The thickened/offset realization**, the only remaining route that is
  independently *geometric* rather than another reading of the same
  combinatorial conditions — and the one §0.3 rejected for this slice on risk,
  since thin offsets land in the near-degenerate regime the previous slice
  spent a slice characterising.

---

## 6. The gates, each with its measured number

Every gate is **demonstrated to refuse** in `--selftest` (16 of 16 checks
pass), not merely present.

| gate | spec | measured |
|---|---|---|
| **Geometry fidelity** | §6.6 | `bitwise_identical` **true**; production **26** cells, transcription **26**. So any difference reported above is about the clause set, not the arrangement. |
| **Faces usable** — convex, CCW, rational | §6.5 | **380** faces checked, **0** non-convex, **0** non-rational, **0** duplicate-vertex rings. Faces: 16 triangles, 364 quads. Passes rather than refuses on this witness, and refuses a deliberately clockwise-wound face in `--selftest`. |
| **Breakpoint completeness** | §6.1 | **363** real sub-segments, each with its cover verified identical at three distinct interior points. Refusal demonstrated by coarsening the cut list, and the gate also refuses a **vacuous** pass of zero sub-segments. |
| **Transitivity unit test** | §6.2 | `layer_certify._satisfied("transitivity", (True, True, False))` is **False** — the cyclic triple is rejected. |
| **Non-empty populations** | §6.3 | `require_nonempty` asserted over `oracle_triples` **28,192**, `production_triples` **28,192**, `population_A` **25**, `active_sites_A` **25**. Population **B** is **0** and `active_sites_B` is **0**, reported as a **result** beside the only-oracle count that explains it — see §9.9. |
| **Oracle refuses** | §6.4 | `intruder_rejected` **true** (hand-built three-face fixture, face 7 threaded between a crease's halves); `seeded_inversion_rejected` **1** on real geometry — subset `[0,1,2,5,6,7,10,11]`, certified order `[0,1,2,7,6,5,10,11]`, adjacent transposition `[0,2,1,7,6,5,10,11]` rejected. |

Also measured, for the record:

* **Clause census:** **4,614,726** total — **4,511,932** `transitivity`,
  **74,602** `taco`, **28,192** `equality`. `restrict.geometric` leaves
  **102,794**. (**Derived:** 4,511,932 / 4,614,726 = **97.8%** transitivity.)
* **Cover-fallback seeds:** **0**. `candidate_subsets`' intersecting-cover
  fallback is **unexercised on this witness** — no crease has two faces
  sharing no cell cover — so that branch is kept because it is cheap, not
  because it ran.
* **`shared_edges` by assignment:** **384 M, 361 V, 745 total, no `F`**, which
  is *why* §9.11 holds.
* Arrangement: **26** cells (artifact
  `gates.geometry_fidelity.production_cells`), cover sizes **168–224** faces.
  (**Derived**, and the only figure here outside the artifact and the three
  declared README records: the cover sizes are not an artifact field. Operands
  are the 26 cover sets `load_all()` threads as `covers`, i.e.
  `min/max(len(c) for _poly, c in geom.cells(polys_k, K))` on the same state —
  measured `[168, 168, 172, …, 224, 224]`, min **168**, max **224**.)

---

## 7. Prior art (CLAUDE.md §0, condensed from spec §0)

**Akitaya, Demaine & Ku, "Computing Flat-Folded States" (OSME 2024)** is the
source `layer_certify` already implements: the *facewise* formulation that
replaces the classical continuous *pointwise* non-self-intersection condition
with a finite CSP over pairs of overlapping convex faces. Their contribution is
the **equivalence** of the two formulations. `layer_certify` implements the
facewise side; this probe tests that implementation against the pointwise side.

**COrigami (arXiv:2606.26299, Google DeepMind) — its global-foldability check
is our algorithm.** Appendix D describes deriving initial face-pair assignments
from the M/V labels, propagating them through implication tables, partitioning
the remainder into connected components, and solving each by DFS with
constraint propagation. That is `layer_order._propagate` plus
`layer_certify.decide`. **So there is no independent collision verifier in
COrigami to adapt, and the gap this probe targets is COrigami's gap too** —
Appendix D does not close it. Building this goes **beyond** published prior art
rather than catching up to it. Their one genuine difference, pre-computed
implication tables against our per-pair propagation, is a performance idea and
out of scope.

**Rejected, with the reason:**

* **Face-pair collision testing** (`mcp_harness/rigid/collision_geometry.py`) —
  **structurally vacuous**, not merely capped at `COLLISION_MAX_FACES = 256`.
  Any injection of faces into distinct z-levels is intersection-free, so
  face–face intersection can never detect a bad layer order. The constraint
  lives in the **creases**: the violation is a face passing through a fold
  ribbon, not through a face. A check that sees only faces has discarded the
  only geometry carrying the constraint.
* **Published counts of globally flat-foldable MV assignments** — **no such
  counts exist.** Hull (*J. Integer Sequences* 17, Art. 14.10.8, 2014) and the
  survey (arXiv:1307.1065) state that enumerating globally valid MV
  assignments for multi-vertex patterns is an **open problem**. Published
  counts cover *locally* flat-foldable Miura assignments only, which would
  validate `cp_audit` rather than `layer_certify`.
* **Oriedita as the independent global check** — `OrieditaValidator.java` calls
  `Check4` / `FlatFoldabilityViolation`, i.e. per-vertex **local**
  foldability. It never checked layer order, so its Pass was never evidence
  about global foldability.
* **Re-implementing ADK's enumerator** — both arms would then derive from ADK,
  testing transcription rather than the clause set.
* **COrigami's crimping algorithm** — a *local* sufficient test (generalised
  Big-Little-Big); this project already has a BLB oracle inside the CSP.
* **Thickened/offset realization** (**Ku & Demaine**, arXiv:1601.05747) — ⚠ both
  the attribution and the reason here were wrong; corrected 2026-10-05. It is
  Ku & Demaine, not Tachi & Hull, and it was not rejected on risk: it consumes a
  layer order rather than verifying one, and its `non-wrapping` precondition
  forbids our collinear case. ⚠ A third ground — that thickness is strictly
  stronger than flat-foldability — was claimed here on 2026-10-05 and has since
  been QUALIFIED: it restated the precondition argument as a universal on an
  unsupported premise. The two grounds above suffice for a box-pleated subject.
  See `../../specs/2026-10-05-cross-section-oracle-design.md` §0.1.

**Adapted:** ADK's pointwise/facewise distinction (which *is* this test's
axis) and the physical reading of the taco families; and
`../2026-10-04-exact-arrangement`'s `kernel.py`, `geom.py` and its `load()`,
reused rather than re-transcribed, because re-transcribing would reopen the
bitwise fidelity risk that slice closed.

---

## 8. Scope of the instrument

* Kernel `exact` (`fractions.Fraction`) throughout. Float mode is not used: the
  arithmetic question was settled by the previous slice, and this probe is
  about **logic**.
* The oracle **factors**, which is what makes the enumeration affordable: the
  exact rational arithmetic runs once per subset and reduces it to a list of
  sites; each of the `|S|!` orders is then decided by integer index
  comparison. `|S| = 8` → 40,320 orders per subset.
* Nothing under `mcp_harness/` was modified. `git diff --stat -- mcp_harness/`
  is empty and `grep -c box_pleat mcp_harness/server.py` is `0`.

---

## 9. What this does **not** establish

All eleven items of spec §9, in substance. This is the section that constrains
what may be cited.

1. **Not completeness over the full arrangement.** §5.1 ran over sampled
   subsets of 380 faces, and foldability does **not** compose upward, so
   subset agreement does not certify the whole. §4's triple comparison *is*
   exhaustive, but it compares constraint **sets**, not foldability.
2. **Not a flat-foldability proof for dense `lizard`.** A clean headline raises
   confidence that CERTIFIED means what it says about which constraints exist.
   It is **not** the proof.
3. **Not ADK's theorem.** This tests *our implementation* of the facewise
   formulation against *our implementation* of the pointwise condition. Both
   could share a misreading of the theorem.
4. **`transitivity` is not under test.** It is **4,511,932** of **4,614,726**
   clauses — **97.8%** (derived) — and is **vacuously satisfied by every total
   order**: `_satisfied`'s predicate `not (rab == rbc and rac != rab)` cannot
   fail on an acyclic total relation. Enumerating total orders therefore leaves
   it nothing to do. Its purpose is to force a *partial* relation to become an
   order during search, not to reject a complete one. It gets a
   correctly-sized unit test instead (§6), and enumerating relations rather
   than orders would cost 2^28 ≈ 268M assignments at `|S| = 8`.
5. **One subject, one platform, one grid.** Dense `lizard` on the 1/68
   box-pleat grid, `darwin`, Python 3.14.3. Says nothing about
   TreeMaker-packed geometry, whose `INTERIOR_EPS` was calibrated on a path
   that agrees across platforms only to ~1e-9.
6. **Branches 2–4 remain vacuous.** `tortillas` is empty on box-pleat
   (`box_pleat/emit.py:31` drops every `F` piece), and the measured
   `shared_edges_by_assignment` confirms it: 384 M, 361 V, **no F**. The
   oracle confirms there is nothing there to find on *this* subject; it does
   not exercise that code.
7. **The geometric predicates are common-mode.** `clip_seg` and
   `strictly_inside` are shared with production by design (§2), so **a defect
   inside either is invisible to this comparison.** What is tested is the case
   analysis built on them, not the primitives. The previous slice's
   exact-rational re-derivation covers the primitives for **arithmetic**, not
   for **logic**.
8. **`cons.direct` and `cons.slots` are not compared.** The oracle deliberately
   ignores the labelling. On the SAT path `direct` is replaced by `DirectSlot`
   biconditionals (`box_pleat/sat_order.py:232-239`), so the labelling is
   pinned there — a separate argument, not something this probe measures.
9. **An empty population B is evidence of absence, not a test performed.**
   §4 measures only-oracle at **0**, so no subset could be built where
   production ignored a crossing: `population_B` **0**, `active_sites_B`
   **0**. That is a strong result for this subject, but it means §5.1's
   order-set comparison ran on **population A alone**. The completeness claim
   therefore rests on §4's exhaustive triple comparison, **not** on §5.1.
   (Note the two senses of "population B": `restrict.classify`'s `"B"` means
   only "production emits no geometric constraint inside this subset" — 728
   subsets classified A and 0 B here — and is **not** §4A.5's population B.)
10. **What §4's 0 / 0 independently tests is narrower than it looks.**
    `stacks.triples` reuses the transcribed `clip_seg` and `strictly_inside`,
    so the predicates are common-mode (item 7). What the triple comparison
    genuinely tests **on its own** is three things: production's **float
    epsilons** against exact rationals, production's **`pairs` guard**
    (`layer_order.py:555-558`, census **0** blocked), and production's
    **single span-midpoint sampling** against per-sub-segment sampling. It is
    **silent on the predicates themselves**.
11. **§4 covers M/V creases only, so two of production's three equality
    branches are untested.** Production emits equalities from the crease
    `_spanning` branch (which the oracle mirrors), the tortilla-tortilla
    flat-edge branch, and the tortilla `_spanning` branch. This witness has
    **no `F` edges at all** — 745 shared edges, **384 M and 361 V** — so the
    latter two **cannot fire**. A tortilla-tortilla equality names four
    distinct faces and would make `restrict.equality_triples` **raise** (loud
    and correct, and demonstrated in `--selftest`); a tortilla `_spanning`
    equality would surface as a false only-production alarm. The 0 / 0 result
    says nothing about either.

**Added by this run, and the limitation most likely to be over-read:**

12. **The `taco` family is not independently checked by this instrument.** §5
    measured the oracle **blind** to collinear taco-taco (164 of 164 rejecting
    clauses), so on that family the comparison has **no power**, in either
    direction. `taco` is **74,602** clauses — (**derived:** 74,602 / 102,794 =
    **72.6%** of the geometric clause set). The order-set comparison's clean
    `equality` reading therefore covers the minority of the geometric clauses
    by count, and the one family §4 already covered exhaustively. The
    artifact says this in machine-readable form: `families_enumerated`
    `["equality", "taco"]` is a **declaration** derived from the enumeration's
    filter constant, while `families_independently_checked` `["equality"]` is
    the **measured** scope. (The field was named `families_under_test` with the
    value `["equality", "taco"]` until 2026-10-05, which handed a consumer
    exactly what this limitation forbids.) **Why this is the oracle's blind
    spot and not production over-constraining is argued in §5.2** — the
    measured `only_clauses = 0` signature does *not* settle it, and the
    argument that does is the `pairs` guard discharging the side condition
    production's branch 5 omits.
