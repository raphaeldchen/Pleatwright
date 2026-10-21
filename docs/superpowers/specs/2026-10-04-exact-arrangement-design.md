# Exact-rational arrangement: is the float path correct?

**Date:** 2026-10-04
**Status:** design, approved section by section
**Subject:** dense `lizard`, the SAT-certified witness

## 1. Why this exists

`layer_certify.py:17-21` states the limit of its own verdict, in capitals:

> ⚠ CERTIFIED IS NOT FLAT-FOLDABLE. `layer_order.AREA_EPS` drops sliver
> arrangement cells before `cons.pairs` is built, and a dropped cell REMOVES
> constraints and can never add one. So CERTIFIED means "certified against the
> constraint set that survived AREA_EPS", which is strictly weaker than a
> proof. **Closing that is separate work.**

This is that work, in its smallest useful form: an evidence probe that
re-derives the arrangement and its constraints in exact rational arithmetic and
compares the result against the shipped float path.

**The caveat names one epsilon. The arrangement rests on three.**

| constant | value | where | measured? |
|---|---|---|---|
| `AREA_EPS` | 1e-9 | drops sliver cells in `_split_convex` | yes — `../evidence/2026-10-02-witness-identity-113` §16: **0 drops** at every threshold down to 0 on dense `lizard` |
| `GEOM_EPS` | 1e-9 | sign classification in `_clip_half`, `_dedupe_ring` | **no** |
| `INTERIOR_EPS` | **1e-8** (`layer_order.py:199`) | `_strictly_inside`, gating `_spanning`'s taco-tortilla / tortilla-tortilla constraints | **no** |

`INTERIOR_EPS` carries a recorded incident. It was split out of `GEOM_EPS`
because at 1e-9 it *"MADE THE ORACLE FABRICATE CONSTRAINTS ON LINUX"* —
breaking the module's stated under-refute direction *"in the one direction the
docstring rules out."* Its own documentation then warns that there is no safe
threshold on dense inputs: on the calibration base the noise ceiling was
3.238e-09 and the signal floor 8.365e-04, a 258,000× gap — but *"ONE BASE IS
NOT A SIGNAL FLOOR"*, and denser pools *"carry constraints continuously from
~1e-9 upward"*, losing 17–95 constraints per arm at 5e-9 alone. It sits at 1e-8,
inside that contested band, and dense `lizard` is the dense regime the warning
is about.

Exact arithmetic dissolves the question rather than tuning it: a cross product
is either zero or it is not.

### Why this is tractable here, and not a research project

Measured on the witness before this design was written:

* CP coordinates are **exactly rational** — denominators {1, 2, 4, 17, 34, 68},
  max |float − rational| = **0.00e+00**.
* Folded coordinates carry only float rounding — denominators {2, 4, 17, 34,
  68}, max error **2.33e-15**, five distinct denominators in total.
* Exact Sutherland–Hodgman clipping over 40 faces held the **max denominator at
  68** with **no growth**, in **0.011 s**. Box-pleat creases are axis-aligned or
  45°, so intersections land back on the grid.
* The arrangement is only **26 cells** (§16). The 53,754 pairs come from large
  per-cell covers, not from many cells.

### What was rejected, and why

**Exact 3-D collision checking of the fold, lifted by layer rank**, using
`mcp_harness/rigid/collision_geometry.py`. Rejected: **measured vacuous.** Two
exactly-overlapping faces give `collision` when coplanar, but once lifted to
distinct z the broad phase prunes them and the checker returns `pass` with
**zero candidate pairs** — identically for a correct layer order and an
inverted one. Lifting destroys the coincidence that makes the question hard. A
flat folding is planar, so layer order is combinatorial, and
`layer_certify`'s taco/tortilla clauses already are its verification.
`rigid/collision_geometry` also requires exactly four unique, exactly planar,
strictly convex vertices per face (our fold has 16 triangles) and caps at
`COLLISION_MAX_FACES = 256` against our 380.

## 2. Scope and placement

A **standalone evidence probe**, not a production module.

```
docs/superpowers/evidence/2026-10-04-exact-arrangement/
    exact_arrangement.py     the instrument (with --selftest)
    exact-arrangement.json   every figure the README cites
    README.md                method, result, limits
```

It **reads** `layer_order` and `flat_fold` and **modifies nothing**.

**Off-limits:** `mcp_harness/layer_order.py` (four shipped callers —
`mv_symmetrize._LayerGate`, `mv_repair`, `root_rank`, `server.py`'s serve
gate), `layer_certify.py`, `box_pleat/layers.py`, `box_pleat/cores.py`. No
production default moves. Nothing enters the PR gate.

**The question:** on dense `lizard`, does an exact re-derivation produce the
same `cons` as the shipped float path?

One subject, deliberately. Breadth is the obvious follow-on and is worth
building only once the exact path is known to agree on the subject already
certified.

## 3. The port

**Ported:** `_polys_of` → `_cells` (via `_split_convex`, `_clip_half`, `_area`,
`_dedupe_ring`) → `pairs` / `covers`; then `_spanning` (via `_clip_seg`,
`_strictly_inside`), `tacos`, `equalities`.

**Not ported:** `direct`. It is label-dependent — the order relations forced by
one fixed labelling — and the joint query ignores it by design.

Each tolerance becomes an exact predicate:

| float | exact |
|---|---|
| `abs(_area(c)) > AREA_EPS` | `area != 0` |
| `sp >= -GEOM_EPS` | `sp >= 0` |
| `sp > GEOM_EPS and sq < -GEOM_EPS` | `sp > 0 and sq < 0` |
| `_dedupe_ring` within `GEOM_EPS` | exact `!=` |
| `_strictly_inside` via `INTERIOR_EPS` | exact `> 0` |

### The fidelity rule

The port is a **transcription** of the shipped algorithm differing **only** in
arithmetic — never a fresh implementation of what the arrangement ought to be.

This project has already paid for the alternative. Memory records: *"a probe
that RE-IMPLEMENTS production reads 0 moved while a direct call moves octopus
4→8."* A re-implemented probe answers a question about the probe.

So the port is written **parameterized over its numeric type**: one code path,
instantiated with `float` or with `Fraction`. **In float mode it must reproduce
the production arrangement element for element.** That check runs first and
gates everything else.

This is what makes the final comparison interpretable. Same code, same
algorithm, one variable changed — so any difference between float mode and
exact mode is attributable to arithmetic alone, which is exactly the claim the
probe wants to make.

### Rationalizing the input

Folded coordinates arrive from `flat_fold` as floats carrying ≤2.33e-15 of
rounding. The probe snaps with `Fraction(x).limit_denominator(10**6)` and then
**asserts** that the snap moved each coordinate by less than 1e-12 and that
every denominator divides the observed grid. A coordinate failing either test
makes the probe refuse: silently rationalizing noise would mean measuring a
geometry production never used.

## 4. The comparison

Gate on what consumers read, not on internal representations — cell polygons
and their ordering can differ without semantic difference, and gating on them
would manufacture false findings.

| compared | semantics |
|---|---|
| `pairs` | set equality, **both directions** |
| `equalities` | set equality, canonicalized |
| `tacos` | set equality |
| the clause set from `layer_certify.clauses(cons)` | set equality — the real target, consumed by `verify`, `decide` and the SAT encoder alike |
| cell count, cover multiset | **reported, not gated** |

**Both directions, never containment.** A subset check passes on equality,
which is the regression it exists to catch.

### The direction of a difference is the finding

* **Exact has MORE** → the float path was **under-refuting**: real constraints
  dropped. AREA_EPS biting, the direction `layer_order` says is safe by design.
* **Exact has FEWER** → the float path **fabricated** constraints. The
  `INTERIOR_EPS`-on-Linux direction, which the module says is ruled out. This
  would mean CERTIFIED rests on constraints that do not exist, and it reaches
  every `layer_order` caller, not just box-pleat.

### Margins

For every epsilon comparison the float path makes, record the compared
scalar's distance from its threshold and report the **minimum** per epsilon. A
closest call clearing by orders of magnitude is what *explains* an identical
result instead of leaving it a coincidence.

## 5. Guards against a vacuous pass

"Identical" is the expected outcome, and expected outcomes are where vacuity
hides.

1. **Fidelity gate** — float mode must reproduce production exactly, or the run
   aborts before any exact result is computed.
2. **Non-empty population** — assert `pairs`, `tacos`, `equalities` and the
   clause set are each non-zero before comparing. Two empty sets compare equal
   and prove nothing; this project has a recorded instance of exactly that.
3. **Seeded disagreement** — perturb one coordinate by more than the grid
   resolution and confirm the comparison **fails**. An equality check never
   shown to fail is not a check.

The probe refuses loudly, with a count, rather than reporting a verdict it
cannot support — following `area_eps.py`'s `SystemExit("REFUSED: …")` pattern.

## 6. Outcomes and their consequences

| outcome | meaning | what follows |
|---|---|---|
| **Identical**, margins ≫ threshold | the caveat is closed for this subject across all three epsilons | a production exact path is **not** urgent for box-pleat; breadth becomes the next question |
| **Identical**, margins ≈ threshold | agreement is luck; the float path is on a knife-edge | a production exact path **is** urgent; publish the near-misses |
| Exact has **more** | CERTIFIED was certified against an incomplete set | the SAT result must be re-run against exact `cons` before being cited |
| Exact has **fewer** | the float path fabricated constraints | most serious; refutations may be unsound, and it reaches beyond box-pleat |

## 7. Validation

An evidence probe has no pytest suite, so its guards are its tests. `--selftest`
runs all three without the full build, following `identity113.py`'s pattern.
Runtime is recorded; for reference the float build took 15.6 s at the shipped
epsilon and 49.2 s at zero (§16).

## 8. What this does not establish

* **One subject.** Dense `lizard` only.
* **Box-pleat only, and that is a favourable input class.** Its exact
  1/68-grid rationals are why exact arithmetic is cheap here. `INTERIOR_EPS`
  was calibrated on TreeMaker-packed bases whose ALM optimizer agrees across
  platforms only to ~1e-9; a clean result here says nothing about that path.
* **`direct` is excluded** by design.
* An identical result closes the caveat for **this geometry**, not for
  `layer_order` generally.
* It does not make the stage a flat-foldability proof on its own: it removes
  the arithmetic caveat from the constraint set, leaving `layer_certify`'s
  clause check to mean what it says.
