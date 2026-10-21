# Pointwise oracle: does `layer_certify`'s clause check mean what it says?

**Date:** 2026-10-04 · **Status:** design, approved in brainstorming
**Subject:** dense `lizard`, the SAT-certified witness
**Kind:** evidence probe. Nothing under `mcp_harness/` is modified.

---

## 0. Prior art (CLAUDE.md §0)

### 0.1 What was found

**Akitaya, Demaine & Ku, "Computing Flat-Folded States" (OSME 2024)** is the
source `layer_certify` already implements: the *facewise* formulation that
replaces the classical continuous *pointwise* non-self-intersection condition
with a finite constraint-satisfaction problem over pairs of overlapping convex
faces. Their contribution is the **equivalence** of the two formulations.
`layer_certify` implements the facewise side; this probe tests that
implementation against the pointwise side.

**COrigami (arXiv:2606.26299, Google DeepMind), reviewed 2026-10-04.** Three
findings, all load-bearing for this design.

1. **Their global-foldability check is our algorithm.** Appendix D, verbatim:

   > In our Python reimplementation, initial face-pair assignments are derived
   > from the mountain–valley crease labels and propagated through pre-computed
   > implication tables. The remaining unassigned variables are partitioned
   > into connected components, each solved independently via depth-first
   > backtracking with constraint propagation.

   That is `layer_order._propagate` (seeds from `cons.direct`, i.e. the M/V
   labels, then propagates) plus `layer_certify.decide` (components, DFS with
   propagation — whose docstring already names "starfish's single 114-variable
   component"). **Consequence: there is no independent collision verifier in
   COrigami to adapt, and the gap this probe targets is COrigami's gap too.**
   Appendix D does not close it. Building this goes *beyond* published prior
   art rather than catching up to it. Their one genuine difference is
   **pre-computed implication tables** against our per-pair propagation — a
   performance idea, not a correctness one, and out of scope here.

2. **Their simulator is purely geometric, and we already have its equivalent.**
   §3.7 and Appendix H: a BFS over the face-adjacency graph composing a 4×4
   affine per face. `mcp_harness/flat_fold.py:135` composes reflections (3×3
   homogeneous, 2D) for the 100% flat state. Appendix H reports ~1e-5 vertex
   error; `../evidence/2026-10-04-exact-arrangement` measured our folded
   box-pleat coordinates at **2.33e-15**, because the flat state needs only
   reflections and no trigonometry. Theirs covers *partial* folds and 3-D,
   which ours does not — irrelevant to the flat state, which is all this probe
   concerns.

   One divergence worth recording: COrigami resolves each vertex by *"averaging
   its transformed positions across all faces containing it to mitigate
   floating-point inaccuracies."* `flat_fold` keeps `folded_vertices`
   **per-face** and reports the disagreement as `closure` error
   (`CLOSURE_EPS = 1e-6`). They average away the quantity we use as the defect
   signal — the same quantity that identifies hull-frontier bases as having no
   consistent flat-folded state. We keep ours.

3. **Appendix H, Figure 15 is an external indictment of our simulator.** On 87
   box-pleated crease patterns with thousands of creases, their deterministic
   folder against *Origami Simulator* (Ghassaei et al. 2018 — the simulator
   this project vendored): vertex reconstruction error **~1e-5 against ~1e-1**,
   *"up to five orders of magnitude"*. This corroborates
   `../evidence/2026-10-03-dense-fold-simulation`, whose dense `lizard`
   planarity stalled at **0.065** against an anchor at 0.00002. Different
   metric, so not a numerical identity — but the 10-03 negative result is now
   externally supported rather than locally unexplained.

### 0.2 What was adapted

| source | adapted |
|---|---|
| ADK 2024 | the pointwise/facewise distinction, which *is* the test's axis |
| ADK 2024 | the physical reading of the taco families — a crease joins two faces, so nothing may lie between them |
| `../evidence/2026-10-04-exact-arrangement` | `kernel.py`, `geom.py` and `layer_order._polys_of` via its `load()`, reused rather than re-transcribed (§3.2) |

### 0.3 What was rejected, with the reason

| rejected | reason |
|---|---|
| **`mcp_harness/rigid/collision_geometry.py` face-pair collision testing** | **Structurally vacuous, not merely capped at `COLLISION_MAX_FACES = 256`.** Any injection of faces into distinct z-levels is intersection-free, so face-face intersection can never detect a bad layer order. The constraint lives in the *creases*: the violation is a face passing through a fold ribbon, not through a face. A check that sees only faces has discarded the only geometry carrying the constraint. This retracts the lift-by-rank direction entirely. |
| **Thickened/offset realization** (**Ku & Demaine**, arXiv:1601.05747) | ⚠ **CORRECTED 2026-10-05, on both the attribution and the reason.** Cited here as "Tachi & Hull" without being read; it is Ku & Demaine, *Folding Flat Crease Patterns with Thick Materials*. The reason given was also wrong — not "risk" from the near-degenerate regime, but three hard refutations: (a) its input *definition* of a flat folded state carries the same `strictly` blind spot and never mentions the crease-crease condition, so it **consumes** a layer order rather than verifying one; (b) its `non-wrapping` precondition forbids one crease touching the inside of another, which is exactly our collinear case; and (c), claimed here on 2026-10-05 and since **QUALIFIED**, that thickness is strictly stronger than flat-foldability. (c) restated (b) as a universal on an unsupported premise — a nested pleat IS the wrapping (b) already excludes — so it is **not** an independent ground. (a) and (b) suffice for a box-pleated subject, which is saturated with wrapping; nothing rules the route out on a non-wrapping one. The successor actually built is the cross-section oracle: `../specs/2026-10-05-cross-section-oracle-design.md`. |
| **Comparison against published counts of globally flat-foldable MV assignments** | **No such counts exist.** Hull (*J. Integer Sequences* 17, Art. 14.10.8, 2014) and the survey (arXiv:1307.1065) state that enumerating globally valid MV assignments for multi-vertex patterns is an **open problem**. Published counts cover *locally* flat-foldable Miura assignments only (equivalent to proper 3-vertex-colourings of the m×n grid graph with one vertex pre-coloured). That is an exact external integer, but it validates `cp_audit`, not `layer_certify`, so it is out of scope. |
| **Oriedita as the independent global check** | `OrieditaValidator.java` calls `Check4` / `FlatFoldabilityViolation` — per-vertex **local** foldability. It never checked layer order, so its Pass was never evidence about global foldability. No shortcut available. |
| **Re-implementing ADK's enumerator** | Both arms would then derive from ADK, so it tests transcription rather than the clause set. Catches less for more work. |
| **COrigami's crimping algorithm (Appendix D, Algorithm 1)** | A *local* sufficient test (generalised Big-Little-Big handling equal angles, Demaine & O'Rourke). This project already has a BLB oracle inside the CSP. Not this slice's layer. |
| **COrigami's mean axial strain** | A genuine gap — word-boundary grep confirms all 73 `strain` hits in `mcp_harness/` are TreeMaker's *packing* strain optimizer, a different quantity. But it measures edge-length consistency, not layer order, so it does not serve this question. Recorded as a separate cheap win. |

---

## 1. The question

`mcp_harness/layer_certify.py:17-21` says CERTIFIED is not flat-foldable
because `AREA_EPS` may drop sliver cells.
`../evidence/2026-10-04-exact-arrangement` **closed that** for this subject
across all three epsilons, and recorded what remains:

> The remaining distance to a flat-foldability proof is not arithmetic: it is
> `layer_certify`'s clause check meaning what it says.

This probe addresses that sentence. The arithmetic is settled; the question is
whether the **clause set is the right set**.

The sharp form. Production derives "nothing lies between a joined pair"
through **five separate geometric branches**, each with its own side
bookkeeping:

1. `_spanning` over creases — taco-tortilla (`layer_order.py:547`, called `:580`)
2. `_spanning` over tortillas — tortilla-tortilla (`:583`)
3. crease × tortilla collinear overlap — taco-tortilla along a flat edge (`:590`)
4. tortilla × tortilla collinear overlap (`:613`)
5. the crease × crease `taco` family

Correctness requires the case analysis to **miss no case**. A single uniform
rule, applied at every segment, reaches the same condition. Agreement between
the two is a **completeness test of the case split** — which no existing test
in this repository performs.

⚠ **Narrowed 2026-10-05: the uniform rule reaches the same condition on four
of those five branches, not all five.** It does **not** reach branch 5's
*collinear* arm, where a strict-interior test is `False` by construction, so
`taco` is enumerated but **not independently checked** here. §9's limitation 12
carries the measurement (164 of 164) and the argument; §2.2's bullet and §5.2's
scope table carry the same correction in place.

`../evidence/2026-10-04-exact-arrangement` measured branches 2, 3 and 4 as
**vacuous on box-pleat** (`box_pleat/emit.py:31` drops every `F` piece, so
`tortillas` is empty). The oracle therefore also tests whether "vacuous" means
"nothing there to find".

---

## 2. The oracle

Given a face subset `S`, the folded state, and a candidate relation
`rel[(lo, hi)] -> bool` meaning *"lo above hi"* (`layer_certify._satisfied`'s
own convention, `:143`):

1. For each crease `(fa, fb)` with both faces in `S`, take its folded segment.
2. Cut that segment by every other face in `S` with `geom.clip_seg`. Collect
   all resulting interval endpoints as **breakpoints**.
3. Between consecutive breakpoints the covering face set is **constant**. Take
   each sub-segment's exact rational midpoint and collect the faces whose
   **strict interior** contains it (`geom.strictly_inside`).
4. **Reject if any such face lies strictly between `fa` and `fb`** in the
   stack that `rel` induces on that covering set.
5. No violation at any sub-segment of any crease → **accept**.

### 2.1 Why one sample per sub-segment is exhaustive, not approximate

The covering set changes only at a breakpoint, and the breakpoints are exactly
the clip endpoints. Within a sub-segment the set of faces covering the crease
is invariant, so the adjacency question has the same answer at every point of
it. One exact rational sample per sub-segment therefore decides the whole
segment. **There is no sampling density parameter and no sampling error.**

This is the design's load-bearing claim and Task 1's gate must demonstrate it
(§6.1), not assert it.

### 2.2 In what sense this is independent — and in what sense it is not

⚠ **Corrected 2026-10-04 by the Task 1 review, which caught this section
overclaiming.** The heading used to read *"Why this is independent of the thing
under test"*, flatly. That is wrong as stated, and the correction is recorded
here rather than quietly rewritten because the distinction decides what the
result can be cited for.

**The predicates are NOT independent. They are production's, on purpose.**
`geom.clip_seg` and `geom.strictly_inside` are documented transcriptions of
`layer_order._clip_seg` and `_strictly_inside` (`geom.py:251`, `:277`), and
§3.2 reuses them deliberately: re-transcribing would reopen the bitwise
fidelity risk the previous slice closed, and a difference would then be
ambiguous between arithmetic and a divergent rewrite. The consequence is
unavoidable and must be stated wherever this probe is cited — **a bug inside
`clip_seg` or `strictly_inside` is common-mode across both arms, and this
comparison cannot see it.**

**What IS independent is the case analysis.** Production assembles those
predicates into constraints through the five branches §1 lists, each with its
own side bookkeeping; the oracle assembles them through one uniform rule. That
is the axis the comparison measures, and §1's "completeness test of the case
split" was always the accurate description of it.

**A second shared assumption, also found by running it rather than reading
it: convexity.** Both predicates are half-plane tests, so both are correct only
for convex faces. On an L-shaped face the Task 1 reviewer measured `covering`
returning `False` at points plainly inside it — which would make the oracle
**miss intruders and therefore accept bad orders**, silent failure in the
dangerous direction. Production carries the same assumption through the same
predicates. `stacks.is_convex` exists so a caller discharges it instead of
assuming it, and §6 gains a gate: the driver refuses on a non-convex face.

With that scoping, the *independence* claim above stands. **The subsumption
claim below does not** — one of its three bullets was measured false on
2026-10-05 and is corrected in place beneath, which is why this sentence no
longer says "the rest of this section stands".

The oracle derives its rule from **physical connectivity** — a crease joins two
faces, so the paper is continuous across it and nothing can pass between them —
not from ADK's family taxonomy. It subsumes ~~all three~~ **two of the three**
families:

- a face between a crease's two halves **is** taco-tortilla;
- two creases interleaving **is** taco-taco — ⚠ **but only when they cross
  TRANSVERSALLY. MEASURED FALSE FOR THE COLLINEAR ARM, 2026-10-05.** For a
  transversal crossing the claim holds as stated: interleaving places part of
  each crease's segment strictly inside the other's faces, so the uniform rule
  sees it. When two creases lie on **one line and share a segment**, every
  face's boundary runs along that segment, so a strict-interior test is `False`
  **by construction** and the oracle cannot see the configuration at all.
  Production says so itself, in `_collinear_overlap`'s own docstring
  (`layer_order.py:415-423`): a transversal crossing *"is therefore already
  covered by the spanning-face rule, whereas a shared segment is not (each
  face's boundary runs along it, so `_strictly_inside` is False by
  construction)"*. Consequence: the `taco` family is **not independently
  checked** by this instrument — **164 of 164** clauses that rejected an order
  the oracle admitted were tacos over a collinear-overlapping crease pair. The
  `equality` family **is** checked, and agrees exactly (§4A). The same
  correction is carried in `stacks.py`'s module docstring (`:39-51`), and the
  scope consequence in §5.2 and §9's limitation 12;
- `tortilla-tortilla` (order consistency across an overlap region) is
  structural here: `layer_order` carries **one variable per face pair**, not
  per cell, so a pair's order cannot vary across its overlap by construction.

The oracle never reads `cons.direct`, `cons.slots`, or the M/V labels. It takes
an order and asks whether the geometry permits it.

### 2.3 Two decisions taken on their own merits, not copied

- **Strict interior, not closure.** A face whose *boundary* runs along the
  crease is not threading the fold. Production agrees
  (`_strictly_inside`, `layer_order.py:563`), but the reason here is physical,
  and under exact rational arithmetic "strictly inside" has exactly one
  meaning, so no epsilon judgement is imported with it.
- **The candidate order is a free variable.** The oracle is a predicate on
  orders, which is what makes the set-equality comparison in §5 possible.

---

## 3. Architecture

### 3.1 Files

Location: `docs/superpowers/evidence/2026-10-04-pointwise-oracle/`

| file | responsibility | imports production? |
|---|---|---|
| `stacks.py` | the oracle: `breakpoints`, `sites`, `stack_at`, `violations` | **no** — this is the independent arm |
| `restrict.py` | subset selection; restriction of `layer_certify.clauses(cons)` and of the SAT relation to `S` | yes — this *is* the thing under test |
| `enumerate_orders.py` | all total orders of `S`; both verdicts per order; set comparison | no |
| `pointwise_oracle.py` | driver: load once, run both populations, gates, JSON, `--selftest`, `main` | via `restrict` |
| `pointwise-oracle.json` | the artifact | — |
| `README.md` | the write-up, including every limitation in §9 | — |

`stacks.py` importing no production module is a **structural** guarantee of
independence, enforced by a test (§10), not a convention.

### 3.2 Reuse, not re-transcription

`kernel.py` and `geom.py` are imported from
`../2026-10-04-exact-arrangement/` by sibling path insertion. Two reasons:

1. Those modules passed **bitwise** fidelity gates against production.
   Re-transcribing them would reopen exactly the risk those gates closed —
   including the recorded defect where an independently written build indexed
   `polys` where production's `_seg_of` indexes `result.folded_vertices`, and
   `layer_order._polys_of` reverses negative-area faces for **190 of 380**
   faces on this subject.
2. Evidence directories are immutable records, so the import target cannot
   drift under us.

`exact_arrangement.load()` (`:44`) is also reused; it returns
`(ff, layer_order._polys_of(ff))`, so the clipping polygons are production's
own. **Known coupling, accepted:** that module hardcodes the subject at `:38`
and `GRID_STEP = 1.0/68`. This slice is single-subject by design (§9), so the
coupling costs nothing here and is not worked around — working around it would
add untested generality.

### 3.3 Data flow

1. `ff, polys = exact_arrangement.load()` — the folded state and production's
   clipping polygons.
2. `cells_list = geom.cells(as_tuples(polys, K), K)` with `K = kernel.EXACT`.
3. `cons, slots = layer_order.constraints_for(ff)` — **returns a 2-tuple**, not
   a bare `cons`.
4. `sat = sat_order.solve(cons, slots)` → `SatResult.relation`, a
   `{(lo, hi): bool}` that the dataclass documents as **COMPLETE**
   (`sat_order.py:131`).
5. `restrict.populations(...)` → subsets, labelled A or B (§4).
6. Per subset: `stacks.sites(...)` once (exact), then
   `enumerate_orders.compare(...)` over all `|S|!` orders (combinatorial).
7. Gates (§6), then JSON and README.

---

## 4A. The triple comparison — added 2026-10-04, and now the headline

⚠ **The subset-sampling design in §4 below was MEASURED VACUOUS by the Task 2
review, and this section replaces it as the primary comparison.** §4 is kept
beneath, annotated, because the reason it failed is the reason this works.

### 4A.1 What was wrong with §4

Against the real witness at the plan's own `MAX_SUBSET = 8`, population B came
out **empty**: 728 candidate subsets, 728 classified A, 0 classified B. At
`max_size = 4` it was non-empty (337 subsets) but **vacuous** — 0 of 19 sampled
B subsets had any active oracle site, so both arms accept every order and the
comparison examines nothing. Both figures reproduced independently.

The mechanism is the damning part. `candidate_subsets` grows a subset from
faces sharing a cell with the seed, which **satisfies production's
`(x,fa) ∈ pairs ∧ (x,fb) ∈ pairs` guard (`layer_order.py:555-558`) by
construction** — and that guard is the one structural gap the probe could
expose. The sampling was steering away from the only thing it existed to find,
and gate 6.3 would then have refused for precisely the artifact §4's
restricted-set definition was introduced to avoid.

### 4A.2 The replacement: exhaustive, not sampled

Compare **triples** instead of subsets. A triple is `(x, {fa, fb})`: face `x`
against the crease joining `fa` and `fb`.

* **Oracle side.** The triple is present iff the crease image crosses `x`'s
  **strict interior**. No `pairs` guard, no cell membership — geometry only.
* **Production side.** Recover it from each `equality` clause: the two
  variables are `_lit(x, fa)` and `_lit(x, fb)`, so `x` is the face common to
  both pairs and `{fa, fb}` is what remains.

Compare as sets, reporting both directions:

* **only-oracle** → the geometry crosses a face but production emitted no
  constraint: **production missed one** (completeness failure);
* **only-production** → a constraint with no geometric support (soundness
  failure).

Exhaustive over all 380 faces and all 745 creases — no sampling and nothing to
steer. About 7 seconds.

### 4A.3 Measured result

| quantity | value |
|---|---|
| production `equality` triples | **28,192** |
| oracle triples | **28,192** |
| only-oracle (production missed) | **0** |
| only-production (unsupported) | **0** |
| oracle triples blocked by the `pairs` guard | **0** |

The last row is a **separate measurement, not a corollary of the row above
it.** Zero only-oracle already implies the guard blocked nothing, but the guard
census is a statement about production's structure in its own right — it says
the one branch the sampling design could never reach is empty here — so §6
requires the driver to count it directly rather than infer it.

### 4A.4 Why one sample per (crease, face) suffices

The oracle's general rule samples every sub-segment; production samples once at
the midpoint of the face's own clip span. For a **convex** face these are
provably equivalent — the clip span is the intersection of the crease line with
the face, so its whole open interior lies inside, and any sub-segment midpoint
within the span does too. All 380 faces are measured convex (§6.5), so they
agree by argument as well as by measurement. The driver still enumerates
triples through `stacks.triples`, which reuses the oracle's own
`breakpoints` and `covering` rather than taking a shortcut, so the agreement is
measured rather than assumed. (`stacks.triples` is a separate entry point
from `stacks.sites`; an earlier revision of this sentence named `sites`, which
was wrong.)

### 4A.5 What becomes of §4's populations

They survive, demoted, as the input to §5.1's **order-set** comparison:

* **Population A** — subsets around a triple both arms carry, testing that the
  clause *semantics* admit the same orders the geometry does;
* **Population B** — subsets around an **only-oracle** triple.

Because only-oracle is **0**, population B is **empty, and that is the RESULT
rather than a gate failure**: production missed nothing, so there is no ignored
neighbourhood to build a subset around. Gate 6.3 changes accordingly.

---

## 4. The two populations

⚠ **Superseded as the primary comparison by §4A.** Retained because §5.1's
order-set comparison still runs over these populations, and because the record
of why it failed is load-bearing.


A single population would confirm soundness forever and never detect a missing
case. Both are required, and both must be non-empty (§6.3).

| population | subsets chosen from | tests | direction |
|---|---|---|---|
| **A** | the `Prov.faces` of existing `equality` and `taco` clauses — neighbourhoods where production **did** emit a constraint | is every constraint production emits real? | **soundness** |
| **B** | cell cover-sets whose faces appear in **no** clause provenance — neighbourhoods where production emitted **nothing** | is there a constraint production **missed**? | **completeness** |

Population B is the reason this probe exists. A missing case is how a clause
set fails to mean what it says, and only B can find one.

Selection rules, so a subset is never trivial:

- every subset contains **at least one crease** with both faces inside it,
  otherwise the oracle has nothing to evaluate — and a subset without one is a
  **refusal**, not a skip (§8);
- every subset's faces are drawn from a common cell cover where possible, so
  they genuinely overlap;
- `|S| <= 8`, with most at 6-7 (§7).

---

## 5. The comparison

Two readings from one instrument.

### 5.1 Equivalence (the SECONDARY reading — §4A replaced it as the headline)

⚠ This section was titled *"Equivalence (the headline)"* until §4A was added.
§4A's exhaustive triple comparison is the headline; the order-set comparison
below is reported **second**, because it tests a different thing (clause
*semantics* rather than clause *presence*). The retitle is recorded rather than
silently applied, since "the headline" is exactly the phrase a citation leans
on.

Per subset, compare as **sets**:

```
{ orders the restricted clause set admits }  vs  { orders the oracle admits }
```

Set equality, with both only-clause and only-oracle differences reported
separately and counted. Not "do both say foldable" — `../evidence/2026-10-04-exact-arrangement`
records the cost of substituting a weaker comparison for the designated one,
and an existence-only comparison would pass a wrong clause set whenever at
least one valid order survived.

Both arms see the same sub-arrangement, so the comparison is well-posed:
restriction drops constraints involving faces outside `S` from **both** sides
identically.

### 5.2 Scope: which families are actually under test

⚠ **`equality` ONLY — corrected 2026-10-05.** This section used to open
*"`equality` and `taco` only"*, and **§9's limitation 12 retracts that**: the
oracle decides from strict-interior geometry, so it is **blind to
collinear-overlapping crease pairs**, and `taco` is therefore *enumerated* but
**not independently checked** by this instrument (measured: 164 of 164
rejecting clauses are tacos over a collinear-overlapping crease pair). **Read
limitation 12 before citing any scope claim from this section** — it carries
the measurement and the argument; this paragraph only states the conclusion.

By clause count that leaves (**derived**, operands from the clause census,
`equality` 28,192 and `taco` 74,602 of **102,794** geometric clauses,
`transitivity` 4,511,932 of **4,614,726** total):

| family | share | under test here? |
|---|---|---|
| `equality` | **27.43%** of the geometric clauses | yes — the only one |
| `taco` | **72.57%** of the geometric clauses | **no** (limitation 12) |
| `transitivity` | **97.77%** of the whole clause set | no (vacuous; see below) |

`transitivity` is **vacuously satisfied** by
every total order — `_satisfied`'s predicate
`not (rab == rbc and rac != rab)` cannot fail on an acyclic total relation — so
enumerating total orders leaves it nothing to do. Its purpose is to force a
*partial* relation to become an order during search, not to reject a complete
one.

Enumerating relations instead would put it under test, but `|S| = 8` gives 28
pair variables and 2^28 ≈ 268M assignments, which is out of budget. So
`transitivity` gets a correctly-sized **unit test** instead: a deliberately
cyclic relation on three mutually-overlapping faces, which the clause checker
must reject (§6.2).

This is stated here because an earlier draft of this design carried a gate
requiring the oracle's cyclic-rejection path to fire, which is **unreachable by
construction** when enumerating total orders. A gate that can never pass is
worse than no gate.

### 5.3 Validation (the second reading)

`sat.relation` restricted to each subset must be **accepted by the oracle** in
every subset of both populations. A single rejection is a defect in the shipped
dense `lizard` certification.

Sound in the direction that matters: every ADK condition is local to a pair or
triple of overlapping faces, so **a violation found in a subset is a violation
in the whole arrangement**. The converse fails — foldability does not compose
upward — which §9 records.

---

## 6. Gates

Each must be **demonstrated to fire**, in the `--selftest`, not merely present.

### 6.1 Breakpoint completeness

Assert on a hand-built case with known geometry that the covering set is
constant across each sub-segment: evaluate the covering set at the midpoint and
at two further interior points of the same sub-segment and require all three to
be equal. This is §2.1's load-bearing claim, measured rather than asserted.
Refusal demonstrated by injecting a deliberately coarsened breakpoint list and
requiring the gate to fail.

### 6.2 Transitivity unit test

A cyclic relation on three mutually-overlapping faces must be rejected by
`layer_certify`'s `transitivity` family. Three faces, no enumeration.

### 6.3 Non-empty populations — restated for §4A

⚠ **Changed 2026-10-04.** This gate used to require populations A and B both
non-empty. Under §4A that is **wrong**: B is built from only-oracle triples, so
an empty B means production missed nothing, and refusing on it would turn the
probe's best possible outcome into a failure.

What must be non-empty is what the comparison is taken **over**:

* the **oracle triple** and **production triple** populations — two empty sets
  compare equal and prove nothing (`exact_arrangement.require_nonempty`);
* population **A**, since the order-set comparison needs at least one subset
  carrying a real constraint;
* the count of **active sites** per population, reported, so no reader can
  mistake a subset with no candidate intruder for one that was examined. That
  missing number is what let §4's population B be vacuous without saying so.

Population **B** empty is reported as a result, beside the only-oracle count
that explains it.

### 6.4 Oracle refuses

Two independent demonstrations:

- **seeded inversion** — invert one pair of the shipped order inside a subset
  where production emitted an `equality`; the oracle must reject it;
- **hand-built intruder** — a synthetic three-face configuration with a face
  forced between a crease's halves; the oracle must reject it and name the
  intruder.

### 6.5 Convexity, and rational coordinates

Both added 2026-10-04 by the Task 1 review; see the correction in §2.2.

**Convexity.** The driver calls `stacks.is_convex` on every face of every
chosen subset and **refuses** on a non-convex one. Without it the oracle fails
silently in the direction that matters: a non-convex face is invisible to
`covering`, so an intruder goes unseen and a bad order is accepted. This is a
shared assumption with production rather than one this probe introduces, which
is exactly why it must be discharged rather than inherited.

**Rational coordinates.** Exactness is a caller precondition that `stacks.py`
cannot enforce: with plain `int` coordinates `clip_seg`'s `-num / denom`
returns a `float` and the exactness guarantee is lost with no error. The driver
asserts every coordinate it passes is a `Fraction`, since it is the component
that knows the kernel is `EXACT`.

### 6.6 Geometry fidelity

`polys` and `cells` asserted identical to production's own, so any disagreement
reported by §5 is about the clause set and not about the arrangement. This
reuses the mechanism `../2026-10-04-exact-arrangement/exact_arrangement.py`'s
`fidelity_gate` already established.

---

## 7. Scale

The oracle **factors**, which is what makes this affordable:

| stage | depends on the order? | cost |
|---|---|---|
| breakpoints, covering sets → `sites` | **no** | exact rational, once per subset |
| per-order adjacency check | yes | integer position comparisons only |

So the expensive exact arithmetic runs ~40-60 times total, not once per order.
Each subset reduces to a compact list of sites `(fa, fb, frozenset C)`, and
each of the `|S|!` orders is then checked with integer comparisons:
`|S| = 8` → 40,320 orders × a handful of sites × O(8).

Budget: `|S| <= 8` (40,320 orders), most subsets at 6-7 (720-5,040), 40-60
subsets across both populations.

---

## 8. Error handling: refuse, never skip

Any structural surprise **raises**:

- a subset containing no crease with both faces inside it;
- a crease whose faces are not both in `S` reaching the site builder;
- a face named by a clause variable but absent from the arrangement;
- a `rel` missing a pair the oracle needs.

The recorded failure mode in this repository is a probe that silently skips and
reports clean — `box_pleat/sat_order.py`'s `SatOrderError` guard exists because
an unguarded lookup escaped `compile_tree` as a bare `KeyError`.

On a genuine disagreement the probe reports **both verdicts and the minimal
witness** — crease, intruder face, sub-segment, offending order — and does
**not** declare production wrong. Adjudication is a human call, and a probe
that concludes is a probe that can be wrong loudly.

---

## 9. What this does not establish

Stated here so the README cannot overclaim.

1. **Not completeness over the full arrangement.** Sampled subsets of 380
   faces. Foldability does not compose upward, so subset agreement does not
   certify the whole.
2. **Not a flat-foldability proof for dense `lizard`.** A clean result raises
   confidence that CERTIFIED means what it says on sampled neighbourhoods. It
   is not the proof.
3. **Not ADK's theorem.** This tests *our implementation* of the facewise
   formulation against *our implementation* of the pointwise condition. Both
   could share a misreading of the theorem.
4. **`transitivity` is not under test** (§5.2) — vacuous on total orders,
   separately unit-tested.
5. **One subject, one platform, one grid.** Dense `lizard` on the 1/68
   box-pleat grid. Says nothing about TreeMaker-packed geometry, whose
   `INTERIOR_EPS` was calibrated on a path that agrees across platforms only
   to ~1e-9.
6. **Branches 2-4 of §1 remain vacuous**, because `tortillas` is empty on
   box-pleat. The oracle confirms there is nothing there to find on *this*
   subject; it does not exercise that code.
7. **The geometric predicates are common-mode.** `clip_seg` and
   `strictly_inside` are shared with production by design (§2.2, §3.2), so a
   defect inside either is invisible to this comparison. What is tested is the
   case analysis built on them, not the primitives. The previous slice's
   exact-rational re-derivation is what covers the primitives, and it covers
   them for arithmetic, not for logic.
8. **`cons.direct` and `cons.slots` are not compared.** The oracle deliberately
   ignores the labelling (§2.2). On the SAT path `direct` is replaced by
   `DirectSlot` biconditionals (`box_pleat/sat_order.py:232-239`), so the
   labelling is pinned there — but that is a separate argument, not something
   this probe measures.
9. **An empty population B is evidence of absence, not a test performed.**
   §4A measures only-oracle at 0, so no subset could be built where production
   ignored a crossing. That is a strong result for this subject, but it means
   §5.1's order-set comparison ran on population A alone. The completeness
   claim therefore rests on §4A's exhaustive triple comparison, not on §5.1.

10. **What §4A's 0 / 0 independently tests is narrower than it looks.**
    `stacks.triples` reuses the transcribed `geom.clip_seg` and
    `strictly_inside`, so the predicates are common-mode (item 7). What the
    triple comparison genuinely tests on its own is three things: production's
    **float epsilons** against exact rationals, production's **`pairs` guard**
    (`layer_order.py:555-558`), and production's **single span-midpoint sampling**
    against per-sub-segment sampling. It is silent on the predicates
    themselves.
11. **§4A covers M/V creases only, so two of production's three equality
    branches are untested.** Production emits equalities from the crease
    `_spanning` branch (which the oracle mirrors), the tortilla-tortilla
    flat-edge branch, and the tortilla `_spanning` branch. This witness has
    **no `F` edges at all** — measured: 745 shared edges, **384 M and 361 V** —
    so the latter two cannot fire. A tortilla-tortilla equality names four
    distinct faces and would make `equality_triples` **raise** (loud and
    correct); a tortilla `_spanning` equality would surface as a false
    only-production alarm. The 0 / 0 result says nothing about either.

12. **⚠ THE `taco` FAMILY IS NOT INDEPENDENTLY CHECKED — measured 2026-10-05,
    and it narrows this document's central claim.** §1 and §2.2 assert that the
    oracle's one uniform rule subsumes all three ADK families. That is **true
    for the transversal arm and FALSE for the collinear one.** When two creases
    lie on one line and share a segment, every face's boundary runs along that
    segment, so a strict-interior test is `False` **by construction** — and the
    oracle is built entirely on strict interior. Production documents exactly
    this in `_collinear_overlap`'s own docstring (`layer_order.py:415-423`): a
    transversal crossing *"is therefore already covered by the spanning-face
    rule, whereas a shared segment is not (each face's boundary runs along it,
    so `_strictly_inside` is False by construction)"*.

    Measured consequence: §5.1's order-set comparison disagrees on **25 of 25**
    subsets, **one-directionally** — `only_clauses` is 0 on every row, so
    production is strictly stronger and the oracle rejects no order production
    admits. The gap localises completely: on `equality` alone the two arms are
    identical on **25 of 25** rows with admit counts equal exactly, and **164
    of 164** clauses that rejected an order the oracle admitted are `taco`
    clauses over a collinear-overlapping crease pair.

    So what this probe establishes is about **`equality` only** — 27.43% of the
    geometric clauses. `taco` is **72.57%** of them and is untested here;
    `transitivity` is 97.77% of the whole set and is untested (item 4). This
    retraction also corrects **§1**, **§2.2** and **§5.2**, each of which stated
    the pre-narrowing scope; all three now carry it in place.

    **Why "the oracle is blind" rather than "production over-constrains" —
    derived in the whole-branch review of 2026-10-05, and verified line by
    line against `mcp_harness/layer_order.py` before being written here.** The
    measured signature (`only_oracle > 0`, `only_clauses = 0`) is **identical
    under both hypotheses** and so cannot distinguish them; "every rejecting
    clause is stronger than, not inconsistent with, the oracle" is therefore
    not an argument. The argument that does discharge the rival hypothesis is
    structural:

    Production's taco-taco branch (`:633-646`) does **no side bookkeeping**,
    unlike its collinear siblings — branch 3 (`:590-612`) requires `sa == sb`
    at `:596-597`, commented *"not a fold-back onto one side: no taco here"*, and
    branch 4 requires `set(A) == {1, -1}` at `:622`. So the concrete
    over-constraining mechanism to rule out is this: two collinear tacos that
    fold back onto **opposite** sides of the shared line occupy **disjoint**
    half-planes, and a taco-taco clause relating them would be **spurious**.

    It is nevertheless discharged — by the **quad guard at `:639`**, which
    requires all four cross-pairs `(fa2,fa1)`, `(fa2,fb1)`, `(fb2,fa1)`,
    `(fb2,fb1)` to be in `pairs`. `pairs` (`:523-524`) is built from
    co-occupancy of **positive-area** arrangement cells — `_cells`/
    `_split_convex` drop every piece with `|area| <= AREA_EPS` (`:307`,
    `:310-311`), so a pair enters `pairs` only via a cell of positive area
    lying inside both faces. And each crease face carries the crease segment as
    a **full polygon edge** (`_seg_of`, `:527-531`, indexes the shared edge's
    two vertices in the face's own ring) and is **convex** (gate §6.5: 380
    faces, 0 non-convex), so that edge's line is a supporting line and the face
    lies entirely within **one closed half-plane** of it. Two faces in opposite
    closed half-planes intersect only *within the line* — zero area — so they
    can never co-occupy a positive-area cell and never enter `pairs`.
    **The `pairs` guard silently discharges the side condition branch 5
    omits.** Hence no spurious opposite-side taco-taco clause can be emitted,
    and the one-directional disagreement is attributable to the oracle's blind
    spot rather than to production.

    The disagreement is **not** evidence against production; it is evidence that
    the instrument is blind to one configuration, and §12's trigger is met.


---

## 10. Testing

| unit | tests |
|---|---|
| `stacks.py` | hand-computed breakpoints on a known 3-face configuration; `stack_at` ordering under a given `rel`; between-detection positive and negative; **a test asserting `stacks.py` imports no `mcp_harness` module**, so independence is structural |
| `restrict.py` | property test: restriction keeps exactly those clauses all of whose `variables` lie within pairs of `S` — both that none is dropped and none is admitted. This is where an off-by-one silently weakens the comparison |
| `enumerate_orders.py` | `|S|!` orders generated exactly once each; set comparison symmetric and reporting both difference directions |
| driver | every gate in §6 demonstrated to refuse |

Unit tests live beside the probe and are run directly, not added to
`mcp_harness/tests/`: this is evidence, and it must not enter the PR gate.

---

## 11. Global constraints

- **Do not modify** `mcp_harness/layer_order.py`, `layer_certify.py`,
  `box_pleat/layers.py`, `box_pleat/cores.py`. The thing under test must not
  move.
- `git diff --stat -- mcp_harness/` must be **empty** for the whole branch.
- `grep -c box_pleat mcp_harness/server.py` must stay **0**.
- Run from the worktree root; never `cd` to the original repository root.
- `../.venv/bin/python3` from inside `mcp_harness`. Never pass `--timeout`.
- Never run `pytest tests/`. Name files, and run **full** named files.
- Commit messages end with
  `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- Commit messages are written to a file **outside** the repo and used with
  `git commit -F`.
- `kernel.EXACT` is the numeric kernel. Float mode is not needed here: the
  arithmetic question was settled by
  `../evidence/2026-10-04-exact-arrangement`, and this probe is about logic.

---

## 12. Successor, if this disagrees

⚠ **SUPERSEDED 2026-10-05.** §5.1 did report a difference, so this trigger fired — but the instrument named here is refuted, and by its own paper. arXiv:1601.05747 is **Ku & Demaine** (not Tachi & Hull; it was cited unread), its input definition shares this oracle's `strictly` blind spot and never checks the crease-crease condition, its `non-wrapping` precondition forbids exactly our collinear configuration, No thickness-based successor exists for a box-pleated subject, which is saturated with the wrapping that precondition forbids. ⚠ A broader claim — that thickness is strictly stronger than flat-foldability, killing the route for every subject — was made here on 2026-10-05 and has since been qualified as an unproven observation about the wrapping case.

The successor actually built is the **cross-section oracle** — a perpendicular slice reducing each collinear crease bundle to a one-dimensional folded strip, which is option A of README §5.3 given a derivation rather than an ad-hoc side rule. See `../specs/2026-10-05-cross-section-oracle-design.md`.
