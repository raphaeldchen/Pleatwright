# Is `layer_order`'s float arrangement correct? An exact-rational re-derivation

**Date:** 2026-10-04 · **Subject:** dense `lizard`, the SAT-certified witness ·
**Spec:** [`../../specs/2026-10-04-exact-arrangement-design.md`](../../specs/2026-10-04-exact-arrangement-design.md)

**Answer: on this subject, yes — `direction: identical`.** Exact rational
arithmetic derives the same 53,754 `pairs`, 28,192 `equalities` and 74,602
`tacos` the shipped float path derives — and the same 4,614,726-clause set
`layer_certify.clauses` builds out of them — with zero constraints and zero
clauses on either side that the other lacks, and the tightest margin any float
comparison left in either direction was 1.08e+04× its threshold. **One subject,
one platform, box-pleat only, five code paths never reached, two input
populations empty, and two safety nets this probe's own code claimed and did
not have** — §6 is the part of this document that constrains what may be cited.

Every figure below is a field of [`exact-arrangement.json`](exact-arrangement.json),
written by `exact_arrangement.py` in the run this README describes
(`sys_platform` `darwin`, Python `3.14.3`, `total_secs` 55.0,
`peak_rss_mb` 1330.6). Figures that are *not* in that file are either marked
**derived** with their operands shown, or fenced in the one block labelled
**README record**.

Reproduce:

```bash
cd docs/superpowers/evidence/2026-10-04-exact-arrangement
../../../../.venv/bin/python3 exact_arrangement.py --selftest   # the guards
../../../../.venv/bin/python3 exact_arrangement.py              # the run
```

The second command **overwrites** `exact-arrangement.json`. Every count,
margin and bound is deterministic and will come back identical; the wall-clock
fields will not, so the runtimes quoted below are the committed run's.

---

## 1. Why this exists

`mcp_harness/layer_certify.py:17-21` states the limit of its own verdict, in
capitals:

> ⚠ CERTIFIED IS NOT FLAT-FOLDABLE. `layer_order.AREA_EPS` drops sliver
> arrangement cells before `cons.pairs` is built, and a dropped cell REMOVES
> constraints and can never add one. So CERTIFIED means "certified against the
> constraint set that survived AREA_EPS", which is strictly weaker than a
> proof. Closing that is separate work.

This is that work, in its smallest useful form.

**The caveat names one epsilon. The arrangement rests on three** (sites are
code citations, not figures):

| constant | value | where it decides | measured before this? |
|---|---|---|---|
| `AREA_EPS` | 1e-9 | drops sliver cells in `_split_convex` | yes — `../2026-10-02-witness-identity-113` §16: 0 drops at any threshold down to 0 |
| `GEOM_EPS` | 1e-9 | sign classification in `_clip_half`, `_dedupe_ring`, `_clip_seg`, `_segs_interact`, `_collinear_overlap`, `_side_of` | **no** |
| `INTERIOR_EPS` | 1e-8 (`mcp_harness/layer_order.py:199`) | `_strictly_inside`, gating `_spanning`'s equality constraints | **no** |

Those values are `epsilons` in the JSON, which publishes **the probe's own
copies** — `kernel.py` copies the three constants rather than importing them,
so the float control stays fixed while production is free to move. That makes
them production's values only if something says so, and `epsilon_parity` is
what says so: it compares all three against the imported `layer_order` values
and **refuses** on divergence (`epsilon_parity` in the JSON, `identical` true;
it also reads `_dedupe_ring`'s `atol=1e-9` off its own source, because
production writes that one as a literal rather than as `GEOM_EPS`). An earlier
revision of `kernel.py` claimed a divergence would surface as a fidelity-gate
failure; §4 of this document measures that it would not — the slack around
`GEOM_EPS` is four to five orders of magnitude, so a retuned constant anywhere
inside it would leave both gates green while the float arm measured a
predicate production no longer uses.

`INTERIOR_EPS` carries a recorded incident: it was split out of `GEOM_EPS`
because at 1e-9 it *"MADE THE ORACLE FABRICATE CONSTRAINTS ON LINUX"* — the one
error direction `layer_order` says it rules out. Its own documentation warns
that dense pools carry constraints continuously from ~1e-9 upward, and dense
`lizard` is exactly the dense regime that warning is about.

Exact arithmetic dissolves the question instead of tuning it: a cross product
is either zero or it is not.

---

## 2. Method, and what licenses it

The probe is a **transcription** of the shipped algorithm — `_polys_of` →
`_cells` → `pairs`, then `_spanning`, `tacos`, `equalities` — written once and
parameterized over its numeric type (`kernel.py`), so it can be instantiated
with `float` or with `Fraction`. One variable changes between the two arms, so
any difference between them is attributable to arithmetic alone. That is the
whole design: a probe that *re-implements* production answers a question about
the probe, which this project has paid for before.

Folded coordinates arrive from `flat_fold` carrying float rounding, so the
exact arm snaps them with `Fraction(x).limit_denominator(10**6)` and **refuses**
if any snap moved a coordinate by more than `SNAP_TOL` = 1e-12 — rationalizing
noise would mean measuring a geometry production never used.

That is the first of the two assertions the spec requires of the snap. The
second — **that every denominator divides the observed grid** — cannot live in
`_snap`, which sees one coordinate at a time, so it is a driver gate
(`input_grid` in the JSON). It matters because a snap can be tiny and still
land on an arbitrary denominator: `limit_denominator` will happily return a
fraction with denominator 999983 for a coordinate it barely moves, and the
whole structural
argument in §3 rests on the denominators being small *and shared*. The gate is
deliberately not `L = lcm(everything); assert everything divides L`, which is
true by construction and asserts nothing: it takes the grid over **one**
population and requires every denominator of a **second** one to divide it.

### What licenses every number here: four gates

Each runs before the result it licenses, and all four are in the JSON. (Not
all before *any* exact result: `arrangement_result` computes the exact
arrangement before `constraint_fidelity_gate` runs. The gate that licenses the
cell and `pairs` comparison precedes it; the gate that licenses the constraint
comparison precedes *that*.)

| gate | asserts | result |
|---|---|---|
| `epsilon_parity` | `kernel`'s copied `AREA_EPS`/`GEOM_EPS`/`INTERIOR_EPS` still equal the imported `layer_order` values, and `geom.DEDUPE_ATOL` equals the `atol=` literal in `_dedupe_ring`'s own source | `identical` true; `dedupe_atol_production` 1e-9 |
| `input_grid` | the grid of the clipping polygons (`_polys_of`) divides every denominator of the `_seg_of` vertices, and is coarse — below `GRID_DEN_CEILING` | `grid_denominator` 68, denominators 1, 2, 4, 17, 34, 68 in **both** populations |
| `fidelity` | float-mode `cells` reproduces production's `_cells` **bitwise** — same count, same order, same cover, same vertex count, every coordinate equal under `==` | `production_cells` 26, `transcription_cells` 26, `bitwise_identical` true |
| `constraint_fidelity` | float-mode `build` reproduces production's `_build_constraints`, as **sets and as sequences element for element** | `pairs` 53,754, `eqs` 28,192, `tacos` 74,602 |

The sequence half matters: set equality alone would also be satisfied by a
transcription that enumerated the families differently and happened to land on
the same set, which is the class of rewrite the gate exists to catch.

Note what `input_grid` does **not** cover, because it is where §3's structural
argument stops: the two *derived* quantities the predicates also see — a
clipped span's parameter `t` and `_spanning`'s midpoint `mid` — are not points
on that grid and get no floor from it. `constraints.quantum_scope.excludes`
names them, and the second of the two carries this run's tightest margin.

The transcription needed judgement in four places, documented in-file:
`_seg_of`'s source array, `unit`'s normalization, `_overlap_tail`'s two forms
and `_side_of`'s centroid. The last three are the three places `geom` branches
on the kernel's name, each for the same reason — a predicate that compares a
norm-normalized value against an **absolute** `GEOM_EPS`, where removing the
square root (which exact arithmetic must) would silently change the threshold's
meaning, so the float branch stays verbatim and only the exact branch rescales.
**Only the first of the four is attested by a control that fired** (see limit 2
in §6).

The witness shows why `_seg_of` is the dangerous one: `_polys_of` reverses any
face whose signed area is negative, and **190 of the 380 faces here are
reversed** (`witness.faces_reversed_by_polys_of` / `witness.folded_faces`), so
the reversed polygons are *not* index-parallel to `result.faces`. `_seg_of`
must therefore read `folded_vertices`. Getting that wrong is what the
constraint gate caught during development.

### The guards, each demonstrated to refuse

`--selftest` runs nine checks, all PASS: four run a gate or a spec §5 guard for
real and five are required-fail controls, because *a guard never shown to
refuse is not a guard*. All six refusal records are also kept in the full run,
under `guards` in the JSON, so the demonstration is committed and not just
printed.

| # | guard | shown to refuse by |
|---|---|---|
| 1 | `fidelity_gate` | `fidelity_gate_refuses` — hand it a transcription one cell short; it exits with "cell count: production 26, transcription 25" |
| 2 | `require_nonempty` | `require_nonempty(demo=0)` exits; two empty sets compare equal and prove nothing |
| 3 | `seeded_disagreement` | see below |
| 4 | `constraint_fidelity_gate` | two controls: `constraint_gate_refuses` drops one taco and it exits naming `tacos` 74,602 vs 74,601; `pairs_gate_refuses` drops one pair and it exits naming `pairs` 53,754 vs 53,753 (and that control *asserts* the message names `pairs`, so a refusal arriving from another row would not satisfy it) |
| 5 | `grid_gate` | `grid_gate_refuses` — hand it a population whose denominator 999983 does not divide the grid observed on the first; it exits naming the stray denominator |
| 6 | `clause_comparison` | `clause_comparator_refuses` — see below |

**Guard 3, and its limit.** Perturbing one coordinate by 0.05 — 3.4× the 1/68
grid step (`seeded_disagreement.perturbation`,
`perturbation_over_grid_step`) — is detected: the arrangement goes from 26 to
28 cells and the cell comparison reports a difference
(`cells_comparison_detected_it`). Run through the *same* family-comparison
operator the verdict uses, it is detected by `eqs` (28,192 → 28,359;
`only_perturbed` 167) and **invisible to `pairs` and `tacos`**
(`families_blind_to_it`), both unchanged at 53,754 and 74,602.

Why those two are blind is worth stating, because the rows look wrong at first
glance.

* **`pairs`.** The arrangement really did change — 26 cells to 28 — yet the
  pair set came back identical in both directions (`only_clean` 0,
  `only_perturbed` 0). `pairs` records *which* faces overlap, not how the
  overlap is partitioned into cells, and the perturbation refined the
  partition without adding or removing an overlapping face pair.
* **`tacos`.** It reads no perturbed coordinate at all. `perturbed()` edits a
  copy of `polys`; the crease segments the taco–taco loop tests come from
  `result.folded_vertices`, which the perturbed run passes through untouched,
  and its only other input is `pairs` — unchanged, per the row above. The
  `side_of` calls that *do* read the perturbed polygons feed only the
  taco–tortilla equality sub-family, whose tortilla population is empty here
  (§6 limit 1); and `GEOM_EPS/side_of#kept` sits at 3.47e+06× its threshold,
  so a move of this size could not flip one of those readings either.

So guard 3 proves the cell comparison and the equality comparison can fail; it
does **not** establish that `pairs` or `tacos` set equality would notice a
one-vertex move. What covers those is guard 4's **two** controls, which
perturb the comparison's *input* rather than the geometry: one moves `tacos`,
the other moves `pairs`, and each is required to produce a refusal naming its
own family. Before the `pairs` control existed, the `pairs` set difference —
the first family in the headline — had never been shown to report a difference
at all: guard 3 records it blind, and guard 1's control aborts at the cell
count before any family is compared.

Between them, **each of the three families' set comparators is now
demonstrated to fire**: `eqs` by guard 3 on perturbed geometry, `tacos` and
`pairs` by guard 4's two controls.

**Guard 6, and why the clause comparison needed its own.** None of the four
controls above touches `clause_comparison`. An earlier revision of this
document conceded that and then softened it — *"which inherits its families
from these three"* — which is **wrong for 97.8% of the clause set** (**derived**, operands 4,511,932 / 4,614,726).
The 4,511,932 transitivity clauses are built from `covers` inside
`layer_certify._iter_clauses` (`mcp_harness/layer_certify.py:90-97`), not from
`pairs`, `eqs` or `tacos`. The key-collision checks (§3) establish that
`clause_key` is injective, which is a different claim from "the set-difference
operator reports a difference".

`clause_comparator_refuses` is that control. It drops one clause from one arm
and requires the comparison to report it, in **two** sub-cases: a `taco`
clause (`clauses_only_float` 1) and a `transitivity` clause
(`clauses_only_float` 3 — removing one face from a cover removes the triples
it took part in). It asserts not only that a difference is reported but that
the clauses it reports belong to the family that was removed, so a difference
arriving from elsewhere would not satisfy it. It runs on four-face synthetic
arms, deliberately: `clause_comparison` streams `_iter_clauses`, packs with
`clause_key` and takes a two-directional set difference, none of which depends
on the data, so the synthetic arms exercise exactly the code the real
4,614,726-clause comparison runs — at no cost, and reaching the family the
real arms' *only* uninstrumented route would have left untested.

### Margins: why an expected result is not a coincidence

"Identical" is the expected outcome, and expected outcomes are where vacuity
hides. For every tolerance comparison the float arm makes, `MarginLog` records
the compared scalar's distance from its threshold, split three ways by the
predicate's *outcome*: `#kept` (|x| ≥ EPS — how far above the tolerance the
smallest value it kept sat), `#absorbed` (0 < |x| < EPS — the tolerance's
headroom over the worst rounding noise it absorbed), and `#exact-zero`, where
float `|x| < EPS` and exact `x == 0` agree and there is no margin to report.
Together the first two bound how far each epsilon could move **in either
direction** without changing a single decision.

---

## 3. The result

Cells and `pairs` (`arrangement`), then the constraint families
(`constraints`). `max_denominator` 68 with cuts accumulated per cell: the
feasibility risk of exact arithmetic is denominator growth, and **there is
none** — box-pleat creases are axis-aligned or diagonal, so intersections land
back on the input grid.

| compared | float | exact | identical | only-float | only-exact |
|---|---|---|---|---|---|
| arrangement cells | 26 | 26 | covers: true | — | — |
| `pairs` (from covers) | 53,754 | 53,754 | true | 0 | 0 |
| `pairs` (constraint build) | 53,754 | 53,754 | true | 0 | 0 |
| `equalities` | 28,192 | 28,192 | true | 0 | 0 |
| `tacos` | 74,602 | 74,602 | true | 0 | 0 |
| **`layer_certify.clauses(cons)`** | **4,614,726** | **4,614,726** | **true** | **0** | **0** |

**`direction: identical`.** Zero only-float and zero only-exact in every
family, so neither error direction occurs. Had they differed, the direction
would have been the finding: only-float > 0 means the float path **fabricated**
constraints (the `INTERIOR_EPS`-on-Linux direction the module rules out), and
only-exact > 0 means it **under-refuted** (the direction it documents as safe).

This document uses `direction` as the headline answer for the clause row as
well as the three families, so `direction` is now computed over **all four**:
`constraints.direction_inputs` lists what it covers and the family and clause
differences it is built from. Until the final review it was the family sums
alone and would have read `identical` even with `clauses_identical` false —
which, given that the clause set's dominant family comes from `covers` and not
from the three families, was a real gap rather than a pedantic one.

### The last row is spec §4's designated target, and it is not a sum

The spec names a fourth comparison beyond the three families — *"the clause set
from `layer_certify.clauses(cons)`: set equality — the real target, consumed by
`verify`, `decide` and the SAT encoder alike"*. That is the bottom row, built
by handing each arm's families to a real `layer_order._Constraints` and
comparing what `layer_certify` emits from it, in both directions.

It is **not** the three rows added up, and the numbers show why: `clauses`
turns each equality and each taco into one clause, but turns `covers` into one
**transitivity** clause per distinct face triple, and it never reads `pairs` at
all — `pairs` are the clause *variables*. `clauses_float_by_family`:
**4,511,932 transitivity** + 28,192 equality + 74,602 taco. So 97.8% of the
clause set is a family none of the rows above it contains
(**derived**, operands 4,511,932 / 4,614,726), and agreement on the three
families does not imply agreement here.

Three mechanics of that comparison, all deliberate:

* It compares the clause's **semantic content** — `(family, variables, flips)`,
  exactly what `layer_certify._satisfied` reads — and not the `prov` string.
  This probe does not transcribe production's provenance sites, so both arms
  get the same placeholder; `prov` can therefore neither mask a difference nor
  manufacture one.
* Holding a clause set this size as `Clause` instances costs gigabytes per arm,
  so each clause is packed into one integer and the arms are compared as
  integer sets. The packing is injective by fixed bit-width per family, and
  that is *checked*, not argued: arity against `CLAUSE_ARITY`, every face index
  against `CLAUSE_ID_BITS`, and `clauses_float_streamed` /
  `clauses_exact_streamed` against the two set sizes — all four read 4,614,726,
  so no two clauses collided into one key.
* `clauses` reads only `equalities`, `covers` and `tacos`. It does **not** read
  `direct`, so this probe's exclusion of `direct` (§6 limit 5) costs the
  comparison nothing and no `direct` had to be fabricated to run it.

**One declared deviation from spec §4.** The spec lists the cover multiset as
*"reported, not gated"*; the printed verdict **gates** on it
(`arrangement.covers_identical` is one of the flags the unqualified verdict
`and`s over). Deliberate and conservative: a `pairs` difference is something a
cover difference would be *downstream of*, so a run that disagreed on covers
while agreeing on pairs should not print the unqualified verdict. It does not
affect this run — every flag it ands over is true — and the cover multiset is
still reported in the JSON either way. The same flag list now also includes
`clauses_identical`, for the same reason (see the `direction` note below).

Runtime, in the committed run: `constraints.secs` float 1.62 s, exact 9.11 s.
**Derived:** exact mode is 5.6× slower here (operands 9.11 / 1.62) — fine for one subject, but it is
`Fraction` arithmetic over 200,394 `clip_seg` and 277,140 `segs_interact` calls
and will not scale to a corpus run unchanged. The clause comparison itself is
arithmetic-free and costs the same in both arms; it runs after the two builds,
so `constraints.secs` does not include it and `total_secs` 55.0 does.

### Why the agreement is not luck — and for exactly which predicates

From `constraints.coord_denominator_lcm`, `exact_cross_quantum`,
`exact_area_quantum`, over the two populations `input_grid` certifies:

> every coordinate of the **clipping polygons** and of the **`_seg_of`
> vertices** has denominator dividing **68** — asserted, not noticed in
> passing — so a cross product of differences of *those* coordinates is either
> exactly 0 or at least 1/68² = **2.163e-04**, a plain coordinate difference is
> 0 or at least 1/68 = **1.471e-02**, and a shoelace area is 0 or at least
> 1/(2·68²) = **1.081e-04**.

**That covers most of the tolerance comparisons but not all of them, and the
run's tightest margin is at one it does not cover.** An earlier revision of
this section claimed the cross-product floor for *"every quantity the
tolerances test"*, and this run's own `closest_call` refutes it:
`INTERIOR_EPS/strictly_inside#kept` reads **1.081e-04**, exactly **half** the
asserted 2.163e-04 floor. `constraints.quantum_scope.classification` files
every `#kept` row:

| floor | derived from the grid? | rows |
|---|---|---|
| 1/68² = 2.163e-04 — a cross product of grid coordinates | yes | `clip_half_signed_dist#kept`, `clip_seg_denom#kept`, `clip_seg_parallel_num#kept`, `segs_interact_o#kept` |
| 1/68 = 1.471e-02 — a difference of grid coordinates | yes | `dedupe_same_point#kept` |
| 1/(2·68²) = 1.081e-04 — a shoelace area over grid coordinates | yes | `AREA_EPS/intersection`, `AREA_EPS/outside` (both unsuffixed) |
| none | **no — measured only** | `INTERIOR_EPS/strictly_inside#kept`, `GEOM_EPS/clip_seg_span#kept`, `unit_length#kept`, `overlap_length#kept`, `overlap_span#kept`, `side_of#kept` |

**`strictly_inside` has no derived floor at all, and it is the site that
matters most.** It is evaluated at `mid`, the clipped span's *midpoint*
(`build.py:119-121`), and a midpoint is off the 1/68 grid; `coord_quantum`
takes its lcm over the folded faces and the `_seg_of` vertices and never sees
`mid`. Nor does the span parameter help: for a genuinely clipped span
`t = -num/denom` is a ratio of two grid multiples, i.e. an arbitrary rational
with no bounded denominator. So the structural argument supplies **nothing**
for the predicate that carries all 28,192 equalities and the run's tightest
margin — its 1.081e-04 is a **measurement**, and the value it happens to equal
is 1/9248 = 1/(2·68²). It is *not* filed with the two `AREA_EPS` rows it
numerically matches: that match is a coincidence of two different halvings,
the shoelace's ½ in one case and the midpoint's ½ in the other.

The other five measured-only rows are not cross products of grid coordinates
either. `clip_seg_span` is a difference of span *parameters* (observed
4.167e-02, which is not a multiple of either quantum);
`unit_length`, `overlap_length` and `overlap_span` are lengths or
norm-normalized projections (observed 1/68); `side_of` is a cross product
against a norm-**normalized** direction. A norm is irrational in general, so
none of these lies on the grid — which is also why the float branch keeps the
square root (§2).

What survives is the useful half, and it is the half that decides the cells:
for the four cross-product rows, the coordinate-difference row and the two area
rows, **the epsilon band is empty by construction of the input**, the observed
minima land on the quanta to the digit, and the agreement follows from the
input class — which is also why it does not generalise (§6). At the remaining
six sites the agreement is measured and nothing here explains it structurally.

---

## 4. The margins: how far each epsilon could move

`epsilon_bounds` in the JSON. A **grow** factor is the smallest kept value
divided by the epsilon — how much larger the epsilon could get before it would
start dropping something the run kept. A **shrink** factor is the epsilon
divided by the largest noise it absorbed — how much smaller it could get before
that noise would survive.

| epsilon | can shrink by | can grow by | binding site |
|---|---|---|---|
| `AREA_EPS` (1e-9) | *unbounded below* — no area it compared fell under it | 1.08e+05× | `AREA_EPS/intersection` — closest kept area 1.081e-04 |
| `GEOM_EPS` (1e-9) | 1.66e+04× | 2.16e+05× | shrink: `clip_seg_span#absorbed` (worst absorbed noise 6.040e-14); grow: `clip_half_signed_dist#kept` |
| `INTERIOR_EPS` (1e-8) | 1.02e+07× | 1.08e+04× | both at `strictly_inside` (`#absorbed` noise 9.796e-16, `#kept` value 1.081e-04) |

### What the `GEOM_EPS` row does, and does not, bound

This matters because the verdict says all three epsilons are inert, and until
this revision the `GEOM_EPS` row could not support that. §1 lists six
`GEOM_EPS` sites; the row was taken over four of them — `_clip_seg`,
`_segs_interact`/`_overlap_tail`, `_side_of` and `_unit` — because
`geom.clip_half` and `geom.dedupe_ring` took no margin log and made no
recording call. Those two decide the 26 cells, and therefore `covers`, `pairs`
and 97.8% of the clause set (**derived**, operands 4,511,932 / 4,614,726), so
the inertness claim rested on the two sites it had *not* measured. This is the
failure mode this section's own `closest_call` note warns about (below), missed
in its symmetric case: spanning all three epsilons is not spanning all their
sites.

**Both are now instrumented**, in float mode, exactly as the segment helpers
already were, and the bitwise gate still reads 26 cells with every coordinate
equal (logging changes no behaviour). The new rows:

| row | ratio | value |
|---|---|---|
| `GEOM_EPS/clip_half_signed_dist#kept` | 2.16e+05× | 2.163e-04 (= 1/68², on the grid) |
| `GEOM_EPS/clip_half_signed_dist#absorbed` | 2.36e+05× | absorbs worst noise 4.232e-15 |
| `GEOM_EPS/clip_half_signed_dist#exact-zero` | — | present; both kernels read a bit-exact 0 as zero |
| `GEOM_EPS/dedupe_same_point#kept` | 1.47e+07× | 1.471e-02 (= 1/68, a coordinate difference) |
| `GEOM_EPS/dedupe_same_point#absorbed` | 1.29e+05× | absorbs worst noise 7.772e-15 |
| `GEOM_EPS/dedupe_same_point#exact-zero` | — | present |

**The revised `GEOM_EPS` bound is numerically the same — shrink 1.66e+04×,
grow 2.16e+05× — and now covers five of the six sites.** No new row is tighter
than the bound that already held: both `#absorbed` rows (2.36e+05×, 1.29e+05×)
sit far above the 1.66e+04× that binds the shrink direction, and
`clip_half_signed_dist#kept` lands on the *same* 2.163e-04 quantum as the three
rows already tied for the grow bound. The previously-unmeasured decisions were
therefore never the tight ones; what changes is that the inertness claim is now
supported rather than extrapolated. The grow bound's *binding site* moved to
`clip_half_signed_dist#kept` only because its float ratio is marginally the
smallest of that four-way tie (below). The sixth site, `_collinear_overlap`, is
still unmeasured — not for want of instrumentation but because it is **never
called** on this witness (§6 limit 1).

One tag covers both of `clip_half`'s predicates, and that is exact rather than
convenient: `side_keep` reads `s[i]`, `strict_cross` reads `s[i]` and
`s[(i+1) % n]`, so over the loop they read the same multiset — the whole of
`s` — and both compare it against ±`GEOM_EPS` only. Float and exact can
disagree at either one only when some `|s| <` `GEOM_EPS`, which is precisely
what the `#absorbed` row bounds. For `dedupe_ring` both coordinate deltas are
recorded at every comparison, matching production's `np.allclose` (which
evaluates both) rather than the kernel's short-circuiting `and`.

Notes on reading the bounds table honestly:

* `AREA_EPS`'s rows predate the three-way split, so they record *every* area it
  compared, kept or not. Their minimum ratio is 1.08e+05×, which means **no
  area fell below the tolerance at all** — so lowering it to 0 would change
  nothing, consistent with the independently measured 0 drops at any threshold
  in `../2026-10-02-witness-identity-113` §16.
* The `GEOM_EPS` grow bound is a **four-way tie** at 2.16e+05×:
  `clip_half_signed_dist#kept`, `clip_seg_denom#kept`,
  `clip_seg_parallel_num#kept` and `segs_interact_o#kept` all sit on the
  2.163e-04 quantum and differ only in the last bits of their float ratios,
  which is why `epsilon_bounds` names the first.
* The **tightest margin left in either direction** anywhere in the run is
  `closest_call`: **1.08e+04× at `INTERIOR_EPS/strictly_inside#kept`**. That is
  what the verdict is keyed on, deliberately spanning all three epsilons —
  quoting only the arrangement's `AREA_EPS` rows would let a knife-edge
  `GEOM_EPS` or `INTERIOR_EPS` decision pass unexamined while the verdict
  claimed all three were inert.

  That warning had a symmetric case, and this document missed it until the
  final review: spanning all three *epsilons* is not the same as spanning all
  their *sites*, and `clip_half` and `dedupe_ring` were uninstrumented. The
  subsection above is the repair. The number is unchanged — the new rows are
  looser than 1.08e+04× in both directions — but it was unestablished before,
  not merely unstated.

  "In either direction" is the precise reading, and the imprecise one would be
  "the smallest value any comparison kept". `closest_call` minimises over two
  **incommensurable** ratio families: a `#kept` row's ratio is |value|/EPS (a
  *grow* headroom) and an `#absorbed` row's is EPS/|noise| (a *shrink*
  headroom, recorded with the arguments swapped). Both are factors by which a
  decision clears its threshold, which is what the verdict's
  orders-of-magnitude branch needs, but the winner's direction depends on which suffix won it. Here it is
  a `#kept` row, so this particular number *is* a smallest-kept-value margin —
  read the `site` field to know that, not the sentence. §4's table above is the
  per-direction view and is the one to cite for a shrink or a grow bound.

### A secondary result, and what it does *not* retire

**Derived** from `epsilon_bounds.INTERIOR_EPS.shrink` (operands: epsilon 1e-8,
worst absorbed noise 9.796e-16, factor 1.02e+07): `INTERIOR_EPS` could fall to
≈9.8e-16 before any decision in this run changed. **So lowering it to 1e-9 —
the value whose recorded incident "MADE THE ORACLE FABRICATE CONSTRAINTS ON
LINUX" — would change nothing here**: 1e-9 sits ~1e+06 above that floor
(**derived**, operands 1e-9 / 9.796e-16 ≈ 1.0e+06).

That **localises** the incident to the TreeMaker-packed geometry it was
calibrated on; it does **not** retire it. Either the Linux noise there was
≥ 1e-9 — six orders above anything measured on this witness — or it was a
different subject. Nothing in this run licenses moving `INTERIOR_EPS`, and this
probe changes no production default.

---

## 5. The verdict and its consequence

The probe's printed verdict, keyed on `closest_call` and the family flags:

> **THE FLOAT PATH IS CORRECT HERE, AND NOT BY LUCK.** Exact and float agree on
> pairs, equalities and tacos (0 only-float and 0 only-exact) and on the
> 4,614,726-clause set `layer_certify.clauses` derives from them (0 only-float,
> 0 only-exact), and the tightest margin any float comparison left in either
> direction was 1.08e+04x its threshold
> (`INTERIOR_EPS/strictly_inside#kept`). On dense `lizard` the three epsilons
> are inert and CERTIFIED is not weakened by them. One subject, box-pleat only
> -- see the README's limits.

That is row 1 of the spec's §6 outcome table — *identical, margins ≫
threshold* — and its stated consequence is:

> the caveat is closed for this subject across all three epsilons → a
> production exact path is **not** urgent for box-pleat; breadth becomes the
> next question.

Scoped to what was actually exercised (§6), the claim this document supports is:
**on a fully-creased box-pleat CP, over `_spanning` and taco-taco, the float
constraint build is exactly the one exact rational arithmetic derives — and so
is the clause set `layer_certify` reads off it — and `layer_certify`'s
`AREA_EPS` caveat does not bite on this subject.** The
remaining distance to a flat-foldability proof is not arithmetic: it is
`layer_certify`'s clause check meaning what it says.

---

## 6. What this does **not** establish

This is the part of the document that constrains citation. All of it is
measured or structural, none of it is hedging.

**1. Seven census rows contributed nothing — five code paths plus two empty
input populations — and the tortilla ones are unreachable by construction, not
merely unexercised.** The five paths are `collinear_overlap_calls`,
`eq_from_taco_tortilla_along_flat_edge`, `eq_from_tortilla_tortilla`,
`unit_returned_None` and `side_of_returned_0`; the two populations are
`tortillas` (tortilla shared edges) and `tortilla_pairs` (iterations of the
tortilla–tortilla loop), which are counts of *input*, not branches of code.
`constraints.vacuous`:

```
['collinear_overlap_calls', 'eq_from_taco_tortilla_along_flat_edge',
 'eq_from_tortilla_tortilla', 'side_of_returned_0', 'tortilla_pairs',
 'tortillas', 'unit_returned_None']
```

`constraints.census` shows why: of 745 shared edges, `tortillas` is **0** — all
745 are M or V. The witness FOLD carries **759 edges, 384 M + 361 V + 14 B, and
no `F` assignment at all** (`witness.edges`, `witness.edges_by_assignment`). And
that is structural to the emit path, not a quirk of one file:
`mcp_harness/box_pleat/emit.py:31` opens `_merge_runs` by dropping every `F`
piece, so **no box-pleat-emitted CP can carry an `F` assignment**. Consequently
both tortilla equality sub-families contribute 0 and `geom.collinear_overlap` is
**never called**, so its `GEOM_EPS` comparisons are untested here; `unit` never
returned `None` and `side_of` never returned 0, so both degenerate branches are
untested. All 28,192 equalities come from `_spanning` (`eq_from_spanning`) and
all 74,602 tacos from the taco-taco loop (`taco_from_taco_taco`).

Every one of those zeros is an **observed** zero. The census dict is seeded
with a 0 for each of the fifteen `bump` tags before `build` runs, and
`seeded_census` refuses unless that seed list and the `bump(...)` literals in
`build.py` match in both directions — so a row reading 0 means the site was
reached zero times, not that a key was missing and `dict.get` supplied a
default. `collinear_overlap` has a second, independent witness: it is the only
function that writes the `GEOM_EPS/collinear_o` margin tag, and **no
`collinear_o` row exists in `constraints.margins`** — the same zero recorded by
the absence of instrumentation output rather than by a counter.

**"The constraint build is exact" would overclaim.** The defensible scope is
the paths a box-pleat CP actually reaches: 200,394 `clip_seg` calls, 179,562
`strictly_inside` calls, 277,140 `segs_interact` calls, 1,490 `side_of` and 745
`unit` calls. Covering the tortilla families needs a subject with `F`-type
shared edges, which the box-pleat path cannot produce.

(`_overlap_tail` — the one place the exact arm legitimately rescales a
norm-normalized predicate — **is** exercised, via `segs_interact`'s collinear
branch. The evidence is its own margin rows, not a call count: it is the only
writer of `GEOM_EPS/overlap_length` and `GEOM_EPS/overlap_span`, and
`constraints.margins` carries `overlap_length#kept` (1.471e-02) plus
`overlap_span` in **all three** outcome classes — `#kept` 1.471e-02,
`#absorbed` 1.055e-15, `#exact-zero`. Three populated outcome classes means at
least three calls (**derived**, operands: the three `overlap_span` suffixes),
and a float/exact disagreement at this site would have had to pass through
those rows. There is no `overlap_tail` counter, so the true call count is
unmeasured — it is strictly less than `segs_interact_calls`, since
`_overlap_tail` is reached only on the collinear branch. It is not in the
vacuous list.)

**2. Two of the transcription's corrections are principled but inert here.**
The `unit`/`side_of` normalization fix and `_overlap_tail`'s split float form
were both run as required-fail controls during Task 3 and **neither fired**, so
the fidelity gate attests only the `_seg_of` correction. The margins say why:
`GEOM_EPS/side_of#kept` sits at 3.47e+06× the threshold, so a segment-length
factor in [1/68, 1] cannot reach it. They are latent fidelity hazards that this
subject does not expose — they would matter on an input off a coarse rational
grid.

**3. The epsilon-band boundary was never located.** The margins are a *report*,
not a *prediction*: no run here found the threshold at which a decision flips.

> **README record** (not from this run's JSON, and not reproduced by it). Two
> attempts to scan `GEOM_EPS` upward were killed at their background time
> limit — a loosened zero test makes `clip_seg` treat more edges as parallel and
> the run inflates. Only control points completed: `GEOM_EPS` = 1e-9 unchanged,
> and the one surviving datapoint, `GEOM_EPS` = 1e-3 (above the 2.163e-04
> quantum) changing `tacos` by **+8,420**.
>
> **That figure is not recoverable from this repository.** Its source is the
> Task 3 negative-control table in the task report under the gitignored
> `.superpowers/` tree, and no committed file at any revision contains it —
> this block is the only place in the repo it appears. An earlier revision of
> this README cited commit `550942dd` for it, which is wrong: that commit does
> not contain the table. It is quoted here as this document's own record and
> nothing in §3 or §4 leans on it — the quantum argument stands on
> `coord_denominator_lcm` and the shrink/grow factors come from the margin
> table alone. It is consistent with the quantum argument but it is **not** a
> located boundary.

**4. One subject, one platform.** Every figure is `witness.fold` on `darwin`
(`platform` in the JSON). The 1/68-grid argument that *explains* the agreement
is a property of **this input class**: a subject whose folded coordinates do not
land on a coarse grid would have a far smaller quantum and genuinely narrower
margins. Box-pleat is a favourable input class, and exact arithmetic is cheap
here for the same reason it is conclusive. `INTERIOR_EPS` was calibrated on
TreeMaker-packed bases whose ALM optimizer agrees across platforms only to
~1e-9; a clean result here says nothing about that path.

**5. `direct` and `slots` are excluded by design.** `direct` is
label-dependent — the order relations forced by one fixed labelling — and the
joint query ignores it; `slots` is not a constraint family. Neither is ported,
so neither is compared. This costs the §3 clause comparison nothing:
`layer_certify._iter_clauses` reads `equalities`, `covers` and `tacos` only, so
the clause set is the same whether `direct` is empty or not. What it does cost
is anything downstream of `direct` — `verify`'s own docstring warns that a
clean `verify` has not checked `direct`, and that warning is untouched here.

**6. An identical result closes the arithmetic caveat for this geometry, not
for `layer_order` generally**, and it does not by itself make the stage a
flat-foldability proof.

**7. Two "safety nets" this probe's own code claimed, neither of which holds.**
Both were asserted in a docstring and both are now replaced by a measurement,
because an unenforced claim in a comment is worse than no claim.

* **`kernel`'s copied epsilons.** The comment said a divergence from production
  "shows up as a fidelity-gate failure — loudly". §4 measures that `GEOM_EPS`
  can move 1.66e+04× down or 2.16e+05× up changing no decision, so any retune
  inside that band leaves both gates green while the float arm measures a
  predicate production no longer uses. Replaced by `epsilon_parity`, which
  refuses (§1). The copies are kept — the reason for not importing is sound.
* **`geom.area`'s shoelace.** The comment said the bitwise gate "is what makes
  an n ≥ 8 cell fail loudly" if `np.sum`'s pairwise summation diverged from the
  plain loop above numpy's block size. It cannot: this value is consumed only
  through `K.area_nonzero` and is never written into a cell coordinate, so a
  last-bit difference is invisible to `bitwise_diff` unless it flips an
  `AREA_EPS` decision, and that margin is 1.08e+05×. Measured instead:
  `area_vertices_max` is **6**, taken over *every* intermediate
  `outside`/`remaining` polygon across every clip — not just the 26 final cells
  — and so below the block size (`geom.area`'s docstring cites it) that the
  pairwise branch is never taken and the plain loop is bit-identical
  throughout. That is a measurement about this subject, not a property of the
  code: a subject whose clips produced a larger polygon would need the
  comparison re-derived, and nothing would announce it.

**8. Second-subject hazards, recorded now so they are not rediscovered.** None
of these affects this run; all four would have to be dealt with before the
probe is pointed at a second subject.

* `WITNESS` is hardcoded (`exact_arrangement.py:40`). There is no subject
  argument.
* `GRID_STEP = 1.0/68` is hardcoded (`exact_arrangement.py:792`) rather
  than read from `coord_denominator_lcm`. Guard 3's reported 3.4× ratio and its
  refusal message would both be wrong on a subject with a different grid, and
  `PERTURBATION = 0.05` could silently fall *below* another subject's grid
  step while the guard still passed. `input_grid` now measures the real grid,
  so the fix is to derive both from it.
* Cost: `peak_rss_mb` **1330.6** at 380 faces, `total_secs` 55.0, and the
  exact arm costs several times the float arm (§3 quotes the ratio). The clause
  comparison holds two multi-million-element key sets; that is what the peak is.
* `GRID_DEN_CEILING` is 10³, three orders below `kernel.MAX_DEN`. A subject off
  a coarse grid will refuse at `input_grid` rather than quietly publish a
  vacuous quantum — which is the intended behaviour, but it means "the probe
  refused" is the expected first result on a TreeMaker-packed base, not a bug.

---

## Files

| file | what it is |
|---|---|
| `exact_arrangement.py` | the instrument: the four gates, the guards and their required-fail controls, `--selftest`, the driver |
| `kernel.py` | the numeric policy the transcription is parameterized over (`FLOAT`, `EXACT`, `MarginLog`) |
| `geom.py` | `_cells` and the segment helpers, transcribed |
| `build.py` | the three constraint families, transcribed |
| `exact-arrangement.json` | every figure this README cites |

It **reads** `mcp_harness/layer_order`, `mcp_harness/layer_certify` and
`mcp_harness/flat_fold` and modifies nothing. No production default moves;
nothing enters the PR gate.
