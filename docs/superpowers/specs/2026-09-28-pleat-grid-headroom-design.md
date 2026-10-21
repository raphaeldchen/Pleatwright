# Can `pleat_grid.fill` act at all? A headroom census before component 1 is built

**Status:** design, not yet planned.
**Gates:** `2026-09-24-dense-pleats-design.md` **component 1** (`pleat_grid.py`,
COrigami F.1.1 step 5) — the one piece of gap 1's architecture never built.
**Scope:** a read-only census across all 8 box-pleat subjects. No production
code changes; nothing under `mcp_harness/` is touched.

## 1. Why now

Gap 1 (`2026-09-24-dense-pleats-design.md`) specified three components. Two
shipped and work: dense construction plus F.2 interleaving produce a complete,
locally flat-foldable labelling of `lizard` in 0.76 s — 4,868 M/V pieces against
476 sparse, every interior vertex satisfying Maekawa, Kawasaki and `cp_audit`'s
arrangement oracle. §6.3 is the outcome the spec ended on: **dense labelling
works; dense layer-consistency does not.** `compile_tree(dense=True)` exhausts a
500,000-node budget having refused 113 candidate labellings.

Six slices have attacked that since, and five came back negative:

| slice | lever | outcome |
|---|---|---|
| `2026-09-26-nogood-indexing` | index the no-good scan | **withdrawn** — the scan is 1.28% of runtime (`wtg-lizard-500k.json`) |
| `2026-09-26-gap1-phase0` | "the crease set is too dense" | **withdrawn** — wrong-unit error, piece vs segment |
| `2026-09-27-pleat-filter` | F.1.1 steps 3-4 as a filter | **HALTED** — no-op at segment granularity, destructive below it |
| `2026-09-27-nogood-core` | measure the clause's true cause | cause is ~5 creases against a median 2,069-crease cone |
| `2026-09-27-core-in-loop` | narrow the clause in the loop | clause 25.2x narrower; **terminal outcome unmoved** |
| `2026-09-28-witness-identity` | is the loop re-deriving? | **no** — three distinct facts, weak at n=3 |

**Four of six were solver-side, and none of those could have found a
geometry-side cause.** They are all downstream of the crease set. The one that
touched geometry implemented steps 3-4 (the *filter*) and explicitly not step 5
(the *fill*) — and step 5 is the step gap 1's own prior-art section identified as
the fix for the deficit it accepted.

That deficit, recorded when F.1.1 steps 1-4 were consciously rejected
(`2026-09-24-dense-pleats-design.md` §3):

> Rejected because `contours.py` produces a global *elevation field*, and both
> the Maekawa CSP and the layer stage consume it. The paper's filter produces
> segments, not elevations, and specifies no replacement for the field.
> **Measured cost of the rejection: our candidate coverage is 54.7% of the
> half-grid rather than contiguous, which step 5 is adopted to close.**

⚠ Those coverage figures are **unreproducible and wrong** (§9). Measured
2026-09-28 over non-boundary half-grid unit segments: `starfish` **48.2%**,
`lizard` **49.3%**, `bird` **49.9%**. The correction makes the gap *larger*, not
smaller, so §1's motivation is unaffected in direction — but the figure this
slice extends is the measured one, not the quoted one.

**So the leading hypothesis for gap 1's wall has gone untested**: that no
stackable labelling exists because the pattern handed to the layer stage is
roughly half-covered (§9) and non-contiguous, where COrigami's is contiguous by
construction. Testing it requires component 1. This spec does not build
component 1 — it measures whether component 1 *can act*, which is cheap, exact
(§4), and decides whether the build is worth a slice.

## 2. Prior art (CLAUDE.md §0)

**Verified against the paper this session, not quoted from our own specs.**
COrigami, *An AI Pipeline for Co-Designing Flat-Foldable Visually Recognisable
Origami* (arXiv:2606.26299, Google DeepMind, submitted 2026-06-24).

Three findings change how gap 1 should be read, and all three are corrections to
assumptions this project has been carrying:

1. **COrigami is not a solved pipeline.** Figure 6 reports **packing 55.3%,
   solving 79.2%** — so roughly one subject in five that packs still fails to
   solve. The abstract reports **27,869 viable models from 560,000 candidates**,
   about 5% end to end. Any argument of the form "COrigami proved this works, so
   ours should" is unsupported by the paper's own funnel.
2. **COrigami does solve global foldability, with our exact mechanism.** The
   paper: *"Global foldability—verifying the absence of continuous
   self-intersections—is strictly NP-hard, but can be practically resolved by
   mapping overlapping convex faces to a finite constraint-satisfaction graph"*,
   using Taco-Taco / Taco-Tortilla constraints in polynomial time. That is what
   `layers.py` is: its `_KIND` table holds `taco_tortilla`, `taco_taco`,
   `tortilla_tortilla`. **The solver is therefore not the divergence.**
   ⚠ `2026-09-20-box-pleat-compiler-design.md` §6 reads *"self-intersection is
   the acknowledged v1 gap (COrigami's global-foldability step is not built)"*.
   That sentence is about **what v1 of THIS project had not built**, not about
   what COrigami lacks, and it is now stale in that respect: `layer_order` and
   `layers.py` exist and are exactly the constraint graph the paper describes.
   Quoting it as a live difference from COrigami would be a misreading in two
   ways at once.
3. **Their hinge search is score-guided where ours is exhaustive.** The paper
   scores *"a global score, defined as the sum of individual vertex scores that
   quantify how close the pattern is to complete local flat-foldability"*, ties
   broken by hinge length and symmetry. We consciously rejected that for exact
   DFS on Maekawa plus CEGAR. They hill-climb to one satisfying assignment and
   accept it; we enumerate complete candidates and refute them. On a pattern
   where stackable labellings are rare, a lucky heuristic and an exhausted
   exhaustive search are indistinguishable from outside.

**Adapted: step 5's purpose, not its mechanism.** The paper's step 5 is *"an
iterative pass over remaining unoccupied grid coordinates, injecting
structurally valid non-intersecting segments to guarantee comprehensive axial
coverage and a fully contiguous fundamental grid."* We adopt the *objective*
(coverage and contiguity) and cannot adopt the *mechanism*, because **their
injected segments carry no elevation and ours must**: `assign.profiles`,
`label_from_profile` and the layer stage all consume the field. That asymmetry
is the reason this component was hard enough to defer, and it is what the census
quantifies.

**Consciously NOT adapted: constraint-propagation machinery.** The natural
framing — completing a partial field as the fixpoint of a monotone operator over
a lattice — would invite arc-consistency or fixpoint-iteration prior art. It is
not needed: §4 proves the fixpoint is reached in **one pass** and is
**order-independent**, so there is nothing to iterate and no propagation order to
choose. Importing CP machinery here would be architecture for a problem that
does not exist.

**Adapted from this project's own failures, because the class repeats.**

* **Phase A (`2026-09-27-pleat-filter`) was implemented through Task 3 and then
  halted**, because at segment granularity the filter retained 365 of 365
  candidates — a no-op. Nobody had measured its retention rate first. This spec
  is that measurement, taken before the build rather than during it.
* **Phase 0 (`2026-09-26-gap1-phase0`) had its headline withdrawn** for a
  wrong-unit error (unit piece versus segment) that ran in the direction
  favouring the hypothesis under test. §5's calibration guard exists to catch
  exactly that.

## 3. What is measured

Per subject: a **sparse** `compile_tree` (the cheap path, and how
`gap1-phase0/phase0.py:210` reached this geometry), then a read of
`res.contours` (`SegKey -> Fraction`) and `layout.boundary_elev`
(`point -> Fraction`). A sparse census is relevant to the dense wall because
the two paths share the field it reads: `compile.py:228` sets
`res.stage_reached = "contours"` **before** the sparse/dense branch, and
`compile.py:401-403` passes `dense=dense` to `assign()` **alone** — so
`res.contours` and `layout.boundary_elev` are identical under sparse and dense
compilation, and the census measures exactly the field the dense pipeline
consumes. Every in-paper half-grid unit segment falls in exactly
one bucket:

| bucket | test | meaning |
|---|---|---|
| **occupied** | key present in `contours` | today's coverage |
| **level-injectable** | both endpoints' elevations known, known elevations **equal**, and the segment is **not a hinge** | headroom `fill` can legitimately take |
| **slope** | both endpoints known, elevations **differ** | can never be a contour segment at any elevation |
| **unreached** | one or both endpoints not known | outside the field's reach |
| **hinge** | the segment's adjacent cells have different owners | structurally ineligible: `contours.py:233-234` refuses a contour on a hinge (**added 2026-09-28, see §10**) |

That is the three clauses actually implemented (known, known, equal, not-hinge
— known-and-known is one test per endpoint); the "collides with nothing" phrase
in the original cell named a fourth clause that nothing in `classify` checks.
The gap is conservative, not a defect: an unchecked collision clause can only
inflate `level_injectable` (it never removes a segment that should have been
excluded), and `level_injectable` measured **0** everywhere (§10), so the
verdict is untouched. This is the same missing-clause class §10 exists to
record — a predicate's prose running ahead of what the code actually tests.

**Why `slope` is structural and not a limitation of `fill`.** `contours.py`'s
module docstring: contours *"live on half-grid lines as unit segments keyed by
their sorted endpoints, each carrying an elevation"* — one elevation per segment
— and *"within one face of the ridge subdivision the elevation is linear and its
contours are parallel"*. A contour is a level line. A segment whose endpoints sit
at different elevations is therefore not a level line anywhere, at any
elevation. `fill` does not decline to invent a value for it; **there is no level
segment there to find.** If the coverage gap is mostly `slope`, COrigami's fully
contiguous grid is unreachable from an elevation field, and that is an
architectural consequence of rejecting F.1.1 steps 1-4 — a finding, not a defect.

**Why headroom might be non-zero at all.** Contours stop *"on the paper edge or
on an existing contour of the same elevation"*, a contour on a hinge is a
refusal, and each `(point, direction)` is traced at most once. So a level line can
terminate early and leave its continuation unoccupied while both its endpoints
remain known. Whether that happens often is the empirical question.

**Second, independent reading: contiguity.** Coverage is a count; the paper asks
for coverage **and** a fully contiguous grid. The census therefore also reports
the number of connected components over the candidate segments (as a graph on
half-grid points), before and after injecting the level-injectable set. If
injection raises coverage without reducing components, it does not buy
contiguity — and contiguity is the property §1's hypothesis rests on.

## 4. Why the census is exact, not an estimate

This is what makes a small result decisive rather than merely suggestive, so it
is stated as an argument and tested (§7) rather than asserted.

**One pass is the fixpoint.** The predicate requires **both** endpoints to
already carry known elevations. Injecting `(p, q)` therefore makes no new point
known — `p` and `q` were known before it. So no injection can unlock any further
injection, and the set of level-injectable segments after one pass is empty.

**The result is order-independent.** A point's elevation is single-valued
(`contours.py`: *"a segment or a point … seen at two elevations is
`ContourFail("collision")`"*). Two candidate injections each take the elevation
both their endpoints already carry, so no injection can invalidate another, and
no ordering changes the outcome.

**Consequence:** the census does not approximate what `pleat_grid.fill` would
inject under the spec's no-invention constraint — it **is** what `fill` would
inject. Contrast `2026-09-27-nogood-core`'s QuickXplain cores, which are
order-*dependent* and required a sort to be reproducible. Nothing here needs one.

**The scope of that claim.** It holds for the predicate gap 1's component 1
specifies, which forbids invented elevations. A *weaker* predicate — inferring an
unknown endpoint from the field's 1/2-Lipschitz bound along runs — would create
newly known points and therefore would cascade, and the census would then be a
lower bound. Such a predicate is out of scope (§11): it invents field values,
which the component's own contract forbids.

## 5. Two guards, fixed before the data

Both realistic failure modes here produce a confident wrong number rather than an
error, so each is a hard precondition. **If either fails, no bucket and no
verdict may be reported.**

### 5.1 Enumeration completeness

`assert set(res.contours) <= set(half_grid_segments(N))`.

`contours._key` sorts a segment's endpoints to form its key. A reimplemented key
with a different sort would make every lookup miss, read `occupied` as **0**, and
show an enormous gap — a spectacular false positive for BUILD. The census
therefore **reuses `contours._key` and `contours.is_boundary_seg`** rather than
reimplementing them, and this guard proves the enumeration covers the field the
subject actually holds.

### 5.2 Occupancy calibration

⚠ **Re-targeted 2026-09-28 before any bucket was measured — see §9.** This
guard originally required reproducing `lizard` 54.8%, `bird` 54.7%,
`starfish` 94.4% from `2026-09-24-dense-pleats-design.md` §2. Those figures are
**unreproducible** (§9), so the guard now calibrates against the quantity that
*is* independently corroborated: the **occupied count**.

The census must reproduce, exactly:

| subject | occupied contour segments | corroborated by |
|---|---|---|
| `lizard` | **4,488** | `../evidence/2026-09-27-pleat-filter/README.md`'s "4,488 dense candidates" |
| `bird` | **11,534** | `2026-09-24-dense-pleats-design.md` §2's dense free-variable figure "~11,534" |

Counts, not percentages, because a count has no denominator to disagree about
and both values were recorded by slices that had no coverage figure in view.
A contour segment **is** a dense candidate, so this pins that the census is
counting the right population.

**Note: the corroboration extends to six subjects, not just the two guarded.**
`docs/superpowers/evidence/2026-09-26-gap1-phase0/phase0.json` records
`dense_candidate_pieces` per subject, and against `headroom.json`'s `occupied`
these match exactly on all six subjects both files cover: `starfish` 54,
`lizard` 4,488, `frog` 5,638, `horse` 8,330, `bird` 11,534, `guinea_pig`
16,174. That artifact satisfies this section's own stated criterion —
recorded by a slice that had no coverage figure in view — on four subjects
beyond the two the guard enforces. The guard itself stays as shipped, enforcing
only `lizard` and `bird`: extending `OCCUPIED_EXPECTED` would mean editing the
instrument after its run, which would destroy the blob-identity provenance the
result depends on. The other four are recorded here as corroboration, not as an
enforced guard, and a future slice extending `OCCUPIED_EXPECTED` to cover them
would strengthen the guard at no cost.

The census additionally **reports** coverage over non-boundary half-grid unit
segments (measured 2026-09-28: `starfish` 48.2%, `lizard` 49.3%, `bird` 49.9%)
and commits the script that computes it, so this figure never becomes
unreproducible the way its predecessor did. Coverage is reported, never guarded:
the guard is the count.

**No tolerances anywhere.** Elevations are `Fraction`, so equality is exact. An
epsilon would be a defect, not a safeguard.

## 6. The bar, fixed before the data

Evaluated on `lizard`, which is the subject the hypothesis is about and the only
one that produces a dense labelling to test against. Other subjects are reported
and inform the reading; they do not select the row.

1. **level-injectable >= 25% of the gap AND components fall** — **BUILD
   component 1.** Real headroom, and it buys contiguity. "Fall" means *strictly
   fewer* connected components after injection than before, on `lizard`; any
   strict reduction counts, because the question is whether injection connects
   anything at all, not how much.
2. **level-injectable >= 25% AND components do not fall** — **BUILD, NARROWED.**
   Coverage without contiguity. Component 1's spec must then state which property
   it claims, because §1's hypothesis rests on contiguity.
3. **level-injectable < 5% of the gap** — **DO NOT BUILD.** A no-op, like the
   pleat filter. The `slope`/`unreached` split becomes the finding, and if
   `slope` dominates, §3's structural reading applies.
4. **5% to 25%** — **REPORT AND DECIDE.** No pre-commitment, because no
   threshold in that range can be honestly justified in advance. Deciding it
   after the data is legitimate only because this row pre-commits to having no
   rule, rather than inventing one later.

"Gap" means `total - occupied`. Note that `coverage_after` and
`injectable_fraction_of_gap` are **the same quantity rearranged**, since the four
buckets partition the total; both are reported, neither is treated as independent
corroboration of the other. (`2026-09-27-core-in-loop-design.md` §7.3 records the
cost of missing that kind of identity.)

~~**`starfish` is the control.** At 94.4% it has little gap.~~ — **STRUCK
2026-09-28, see §9. There is no high-coverage control, because there is no
high-coverage subject.** Measured coverage is 48.2% (`starfish`, N=4), 49.3%
(`lizard`, N=34) and 49.9% (`bird`, N=54) — a band under two points wide across
a 13x range in N. The census should therefore report whether that near-constant
~49% also holds for the remaining five subjects, since a quantity that barely
moves with problem size is itself a finding about the elevation field, and it
replaces the cross-subject contrast this bar was going to lean on.

## 7. What this cannot say

**Nothing here tests whether higher coverage makes dense layer-ordering
converge.** A BUILD verdict licenses building `fill`; it does not predict
convergence, and the README must say so. This limit is stated explicitly because
`2026-09-28-witness-identity-design.md` §3.3 records the same overclaim being
made and corrected one slice ago: a bar's threshold and the inferences attached
to it are different things.

Two further limits:

* **Coverage is not the only difference from COrigami.** §2.3's search-strategy
  divergence (score-guided versus exhaustive) is untouched by this census and
  unaffected by its result.
* **`layer_order._propagate` is not confluent**, so `consistent` is never a
  foldability proof. That costs completeness, not soundness: the 113 refusals are
  real contradictions. The census does not change this either way, and no result
  here may be read as strengthening a `consistent` verdict.

## 8. Interfaces, error handling, testing

### 8.1 Files

```
docs/superpowers/evidence/2026-09-28-pleat-grid-headroom/
  headroom.py     # the census, with a --selftest mode
  headroom.json   # per-subject buckets + run metadata
  README.md
```

Nothing under `mcp_harness/` changes. `grep -c box_pleat mcp_harness/server.py`
stays 0.

### 8.2 Pure functions

```python
def half_grid_segments(N) -> set          # in-paper unit segments, via contours.is_boundary_seg
def known_elevations(contours, boundary_elev) -> dict    # point -> Fraction
def classify(N, contours, boundary_elev) -> dict         # bucket name -> set(SegKey)
def components(segs) -> int               # connected components over half-grid points
def verdict(rows) -> tuple                # (§6 row, the figures that selected it)
```

`classify` is the load-bearing unit and the only one with non-obvious logic;
everything else is a count or a graph walk.

### 8.3 Error handling

* A subject whose sparse compile fails records its typed failure in the row and
  the census continues to the next. The census never raises on a subject.
* `dog` and `octopus` are the largest; a **300 s** per-subject cap on the
  sparse compile records a timeout as that subject's outcome rather than
  aborting the run. 300 s is the cap `gap1-phase0/phase0.py` used for its dense
  arm, reused so the two are comparable; the sparse path is far cheaper, so a
  timeout here is itself a finding.
* Either §5 guard failing sets the verdict to `GUARD FAILED` and returns before
  any bucket is reported, in either direction.
* JSON is flushed after each subject, so a partial run still leaves a record.

### 8.4 Testing

`--selftest`, on synthetic fields small enough to count by hand. No pytest file
is added, because no production code changes; the census's own logic is what
needs covering.

1. All five buckets on a synthetic `contours` + `boundary_elev`, hand-counted,
   including a segment that lands in `hinge` under a split owner map and in
   `level_injectable` under a single-owner one — the same segment both ways, so a
   `classify` that put everything in `hinge` could not pass.
2. Endpoints known but **unequal** classifies as `slope` and specifically not as
   level-injectable.
3. One endpoint unknown classifies as `unreached`.
4. **§4's fixpoint claim, exercised rather than argued:** classify, inject the
   level-injectable set into a copy of the field, re-classify, assert the new
   level-injectable set is **empty**. The gate's decisiveness rests on this, so
   it is a test and not a paragraph.
5. **§4's order-independence, exercised:** injecting the set in two different
   orders yields identical fields.
6. `components()` on a hand-drawn set with a known number of components.
7. The §6 bar: all four rows reachable, including the 5-25% no-commitment band,
   and the guard-failure path returning before any verdict.

### 8.5 Evidence

`README.md` states, in this order: both §5 guards with expected beside measured;
the five-bucket table for all 8 subjects; the contiguity reading (components
before and after); the §6 row reached and why that row and not its neighbours;
and §7's limits, whichever way the result falls.

`headroom.json` carries a **timestamp and the commit SHA the run was made from**.
`2026-09-28-witness-identity-design.md` §10 recorded that deferral and named the
next evidence script in this subproject as the place to close it, after the same
advice sat unactioned in two prior READMEs. This is that script.

## 9. Correction: the coverage figures this slice was built on are unreproducible

**Found 2026-09-28 while writing the implementation plan — before any bucket was
measured, and before a line of the census was written.** Recorded here rather
than applied silently, on the same grounds as
`2026-09-28-witness-identity-design.md` §3.3.

**What is wrong.** `2026-09-24-dense-pleats-design.md` §2 reports *"candidate
coverage of the half-grid (unit segments occupied / total): `starfish` 94.4%,
`lizard` 54.8%, `bird` 54.7%"*. Those three figures entered the repository in
commit `42ae862` (the original gap-1 spec) and **no committed script computes
them.** They are quoted in three later documents —
`2026-09-27-pleat-filter-design.md`, `evidence/2026-09-26-gap1-phase0/README.md`
and its `phase0.py` — always as a quotation of the spec, never recomputed.

**Measured 2026-09-28**, over unit segments on the integer half-grid `[0, 2N]`
excluding those lying along the paper boundary (`contours.is_boundary_seg`), keyed
with `contours._key`:

| subject | N | non-boundary segments | occupied | coverage | spec §2 claimed |
|---|---|---|---|---|---|
| `starfish` | 4 | 112 | 54 | **48.2%** | 94.4% |
| `lizard` | 34 | 9,112 | 4,488 | **49.3%** | 54.8% |
| `bird` | 54 | 23,112 | 11,534 | **49.9%** | 54.7% |

Zero contour segments lie on the paper boundary on any of the three, which
matches `contours.py`'s *"nothing is ever registered on the paper boundary"*.

**Why the measurement is trusted over the quotation.** The `occupied` column is
independently corroborated by two figures recorded by slices that had no coverage
number in view: `lizard` **4,488** is `evidence/2026-09-27-pleat-filter/README.md`'s
count of dense candidates, and `bird` **11,534** is `2026-09-24-dense-pleats-design.md`
§2's own dense free-variable figure. A contour segment is a dense candidate, so
`occupied` is the right population, counted correctly. What the old percentages
disagree about is the denominator, and `starfish`'s 94.4% implies a denominator of
about 57 against an actual 112 — not a variant convention but a different
quantity.

**The direction matters and does not favour the hypothesis.** Real coverage is
*lower* than claimed, so the gap component 1 would close is *larger* (~51% of the
grid rather than ~45%). The correction strengthens §1's motivation slightly; it
was not made to.

**What this changes in this spec.**

1. **§5.2 is re-targeted** from percentages to the two corroborated counts, and
   the script that computes coverage ships with the slice so the figure cannot go
   unreproducible again.
2. **§6's `starfish` control is struck.** The bar was going to lean on a contrast
   between a 94.4% subject and a 54.8% one. Measured, coverage is 48.2%–49.9%
   across a 13x range in N — a band under two points wide. **There is no
   high-coverage subject, so there is no control on that axis.** The census
   instead reports whether ~49% holds across all eight, because a quantity that
   barely moves with problem size is a finding about the elevation field in its
   own right.

**What this does NOT change.** ~~The four buckets (§3)~~ — the buckets became
**five** on 2026-09-28 for an unrelated reason (§10); that change is not part of
this correction. The exactness argument
(§4), guard §5.1, the bar's thresholds (§6) and the limits (§7) are all
untouched. §6's thresholds are fractions *of the gap*, so they are
self-normalising: a larger gap does not move them.

**The class of the error, named because it repeats.** This is the third
unreproducible figure found on this branch — after the pleat-filter halt table
(no committed script) and Phase 0's withdrawn retention headline (wrong unit).
All three were numbers quoted forward into later documents without ever being
recomputed. The habit that catches it is cheap: **recompute the figure you are
about to build on, before you build on it.**

## 10. Correction: a fifth bucket, `hinge` (2026-09-28)

**Found by Task 1's code review, before the census was run.** Recorded here
rather than applied silently, as §9 was.

**What was wrong.** §3's `level_injectable` predicate read "both endpoints known
and equal". That is **two of three clauses.** `contours.py:233-234` refuses a
contour on a hinge:

```python
owners = _seg_owners(k, owner, N)
if len(owners) > 1:
    return ContourFail("contour_on_hinge", k)
```

A segment whose adjacent cells have different owners therefore can **never**
legitimately carry a contour, whatever its endpoints' elevations say. COrigami's
own wording for step 5 is *"injecting structurally **valid** non-intersecting
segments"* (§2), so the validity clause was always part of the thing being
measured.

**Why it mattered.** The omission inflated `level_injectable` — the headline
bucket — and `components_fell`, both **in the direction favouring BUILD.** That
is the error class §9 names, arriving from a different direction: not a figure
quoted forward, but a predicate missing a clause its own source states.

**The fix.** Exclude hinge segments using production's own
`contours._seg_owners(key, owner, N)`, with `owner` from `layout.cell_owner()`.
Hinge-rejected segments go in a **fifth bucket, `hinge`**, appended last, rather
than folded into `slope` or `unreached`: `slope` is the census's headline and must
keep meaning exactly "endpoints known but unequal", and a separate count tells a
reader how much of the grid is structurally ineligible rather than merely
unoccupied.

**Conservative by construction.** `hinge` segments stay in `gap = total -
occupied`, i.e. in the **denominator** of the injectable fraction, so the fix can
only ever *lower* the fraction that selects BUILD. The bar cannot be made easier
to pass by this change.

**Measured effect: none on the verdict.** `hinge` reads **0** on both `starfish`
and `lizard`, so nothing was actually inflated and §6's row is unaffected. The fix
protects the other subjects' reported table, where it was never checked.

**§8.4's test is two-directional.** The same segment must land in `hinge` under a
split owner map and in `level_injectable` under a single-owner one. A
one-directional test would pass against a `classify` that put *everything* in
`hinge`, which would silently zero the headline bucket.

**Superseded 2026-09-28, after the run.** `hinge` reads **0 on all seven
censused subjects across 136,504 segments** — not merely on `starfish` and
`lizard`, the two this section originally checked by hand before the census
existed.

## 11. Out of scope

* **Building `pleat_grid.fill`.** That is component 1, gated on §6.
* **A weaker injection predicate** that infers unknown endpoints from the
  1/2-Lipschitz bound. It invents field values, which component 1's contract
  forbids, and it would make §4's exactness argument false. If §6 reaches row 3
  and `unreached` dominates, such a predicate is the obvious follow-on — and
  would need its own spec and its own soundness argument.
* **Any change to `contours.py`, `assign.py`, `layers.py`, `cores.py`,
  `layer_order.py`, or the serve path.**
* **The search-strategy divergence** (§2.3, score-guided versus exhaustive).
  Its own question, untouched here.
* **Re-opening `2026-09-27-pleat-filter`** (F.1.1 steps 3-4). Halted on measured
  grounds; this spec is about step 5 only.
* **The dense-beside-sparse CP gallery** (`2026-09-24-dense-pleats-design.md`
  §10), still owed by gap 1 and still gated on dense converging.
