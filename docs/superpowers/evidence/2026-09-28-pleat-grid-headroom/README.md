# `pleat_grid.fill` cannot act: the headroom is zero on all seven censused subjects

**Verdict: DO NOT BUILD** (spec §6 row 3), printed by `headroom.py` from
`lizard`'s row. Every figure below is read from `headroom.json` in this
directory; figures quoted from elsewhere are labelled with their source.

Spec: [`../../specs/2026-09-28-pleat-grid-headroom-design.md`](../../specs/2026-09-28-pleat-grid-headroom-design.md).
Read its **§9** (the coverage figures this slice was built on are unreproducible;
there is no `starfish` control) and **§10** (there are **five** buckets, not
four) before citing anything here.

## 1. The question

Gap 1's architecture had three components; two shipped and the third —
component 1, `pleat_grid.py`, COrigami F.1.1 step 5's `fill` — was never built.
It is the leading untested hypothesis for why dense layer-ordering does not
converge: the pattern handed to the layer stage is roughly half-covered and
non-contiguous, where COrigami's is contiguous by construction. Four of the six
slices that attacked the wall (spec §1's tally) were solver-side and
structurally could not have found a geometry-side cause; the one that touched
geometry built steps 3-4 (the
*filter*) and explicitly not step 5 (the *fill*). This census does not build
`fill`. It measures **whether `fill` can act at all** under its own
no-invention contract — not whether acting would help. Because the census is
exact rather than an estimate (spec §4: the predicate needs both endpoints
already known, so injection cannot cascade and one pass is the fixpoint; and
point elevations are single-valued, so it is order-independent), a small number
here is decisive rather than suggestive.

**Why a sparse census bears on a dense wall.** The census runs the cheap
**sparse** `compile_tree`, not the dense path the wall is actually about. That
is relevant because the two paths share the field this census reads:
`compile.py:228` sets `res.stage_reached = "contours"` before the sparse/dense
branch runs, and `compile.py:401-403` passes `dense=dense` to `assign()`
**alone** — so `res.contours` and `layout.boundary_elev` are identical whether
the compile that follows is sparse or dense. The census therefore measures
exactly the field the dense pipeline consumes, at a fraction of the cost of a
dense compile.

## 2. Both guards (spec §5): expected beside measured

`headroom.json` records `"cap_secs": 300` and
`"occupied_expected": {"lizard": 4488, "bird": 11534}`.

### §5.1 enumeration completeness

`set(res.contours) <= set(half_grid_segments(N))` — that no contour key falls
outside the census's own enumeration. A reimplemented sorted-endpoint key would
make every lookup miss, read `occupied` as 0, and produce a spectacular false
positive for BUILD, so the census reuses production's `contours._key`,
`contours.is_boundary_seg` and `contours._seg_owners` rather than
reimplementing them.

| subject | expected | measured |
|---|---|---|
| `starfish` | no stray keys | **pass** — `guard_failures: []` |
| `lizard` | no stray keys | **pass** — `guard_failures: []` |
| `frog` | no stray keys | **pass** — `guard_failures: []` |
| `horse` | no stray keys | **pass** — `guard_failures: []` |
| `bird` | no stray keys | **pass** — `guard_failures: []` |
| `guinea_pig` | no stray keys | **pass** — `guard_failures: []` |
| `octopus` | no stray keys | **pass** — `guard_failures: []` |
| `dog` | — | **not evaluated**: no row (see §3) |

### §5.2 occupancy calibration

Two counts, not percentages, each recorded by a slice that had no coverage
figure in view — `lizard` **4,488** from
[`../2026-09-27-pleat-filter/README.md`](../2026-09-27-pleat-filter/README.md)'s
dense-candidate count, and `bird` **11,534** from
`2026-09-24-dense-pleats-design.md` §2's dense free-variable figure (both
labelled as *their* figures; both also appear in `headroom.json` as
`occupied_expected`).

| subject | expected `occupied` | measured `occupied` | outcome |
|---|---|---|---|
| `lizard` | 4,488 | **4,488** | exact match |
| `bird` | 11,534 | **11,534** | exact match |

**§5.1 passed on every subject that produced a row, and §5.2 passed on the two
subjects it has an expectation for (`lizard` and `bird`)** — the other five
have no `occupied_expected` entry, so §5.2 is vacuous rather than passing on
them. Buckets and a verdict may still be reported. The stdout line for each
subject ends `guards=PASS`,
and `guard_verdict` — which suppresses the verdict on *any* subject's failure,
not only `lizard`'s — found nothing to suppress.

**A reader can extend that corroboration to six subjects without re-running
anything.**
`docs/superpowers/evidence/2026-09-26-gap1-phase0/phase0.json` records
`dense_candidate_pieces` per subject, and it matches this run's `occupied`
exactly on every one of the six subjects the two files share:

| subject | `phase0.json` `dense_candidate_pieces` | `headroom.json` `occupied` |
|---|---:|---:|
| `starfish` | 54 | 54 |
| `lizard` | 4,488 | 4,488 |
| `frog` | 5,638 | 5,638 |
| `horse` | 8,330 | 8,330 |
| `bird` | 11,534 | 11,534 |
| `guinea_pig` | 16,174 | 16,174 |

`lizard` and `bird` are the two the shipped guard actually enforces (`headroom.py`
refuses to report a verdict if either mismatches); `starfish`, `frog`, `horse`
and `guinea_pig` are corroboration recorded after the fact, from a slice that
had no coverage figure in view, not a guard that fired. The `headroom.py`
instrument was not touched to add this — checking it does not require editing
or re-running the census, only reading the two already-committed JSON files.

## 3. The five-bucket table

Eight subjects were attempted; **seven produced a row and `dog` did not.**
`dog` has `"outcome": "sparse compile exceeded 300s"` — a timeout against the
300 s cap, recorded as that subject's outcome rather than aborting the run.
`dog` is not an unmeasured subject: `docs/superpowers/evidence/2026-09-20-box-pleat/oracle-census/certify.json`
records it `stage_reached: "emit"`, `kind: "CERTIFIED"`, `secs: 537.3`, and
`docs/superpowers/evidence/2026-09-20-box-pleat/results.json` records
`N: 74`, `stage_reached: "emit"`, `flat_fold_ok: true`, `lint_class: "PASS"`,
`pack_ms: 21083.8` — `dog` is one of the better-measured subjects in this
subproject. At ~537 s its compile was already known, before this census ran,
to be roughly **1.8×** the 300 s cap this script borrowed from
`gap1-phase0`'s *dense* arm, so the timeout here was a foreseeable consequence
of reusing that cap on `dog`'s sparse path, not a discovery. Raising the cap
for `dog` alone would likely have made this corpus eight subjects rather than
seven.

**`outcome: "ok"` means "census computable", not "compiled to emit"** — the row
gates on `res.contours` being populated and `res.layout` being present, both of
which `compile_tree` sets well before the emit stage. `stage_reached` preserves
the difference, and on this run all seven `ok` rows read
`"stage_reached": "emit"`, so here the two happen to coincide. That is a
measured coincidence, not what `ok` asserts.

| subject | N | total | occupied | level_injectable | slope | unreached | hinge | coverage | coverage after |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `starfish` | 4 | 112 | 54 | **0** | 56 | 2 | 0 | 48.2% | 48.2% |
| `lizard` | 34 | 9,112 | 4,488 | **0** | 4,624 | 0 | 0 | 49.3% | 49.3% |
| `frog` | 38 | 11,400 | 5,638 | **0** | 5,762 | 0 | 0 | 49.5% | 49.5% |
| `horse` | 46 | 16,744 | 8,330 | **0** | 8,414 | 0 | 0 | 49.7% | 49.7% |
| `bird` | 54 | 23,112 | 11,534 | **0** | 11,578 | 0 | 0 | 49.9% | 49.9% |
| `guinea_pig` | 64 | 32,512 | 16,174 | **0** | 16,338 | 0 | 0 | 49.7% | 49.7% |
| `octopus` | 74 | 43,512 | 21,704 | **0** | 21,804 | 4 | 0 | 49.9% | 49.9% |
| `dog` | — | — | — | — | — | — | — | — | — |

The five buckets sum to `total` on every row, which is what makes the table a
partition rather than seven independent counts. That holds **by construction
of `classify`**, not by a runtime check: for each segment in the enumerated
set, `classify` tests `occupied` first (`continue`s on a match), then
`unreached`, then, among the remaining known-and-equal-or-unequal segments,
`hinge` versus `level_injectable` versus `slope` — one `if`/`elif`/`else`
chain per segment, so every segment lands in exactly one of the five sets and
none is skipped or double-counted. (The plan's verification step computes a
`partition_ok = sum(buckets) == total` flag, but that field exists in neither
`headroom.py` nor `headroom.json`, and since `headroom.py` itself defines
`total = sum(len(v) for v in buckets.values())`, that check is `sum == sum` —
tautologically true and incapable of failing. It is not evidence of a
partition; the code structure is.)

**`coverage_after` and the injectable fraction of the gap are the same quantity
rearranged**, not independent corroboration of each other: the buckets
partition the total, so
`coverage_after = (occupied + level_injectable) / total` and
`injectable_fraction_of_gap = level_injectable / (total − occupied)` are two
readings of the same `level_injectable` count. Both are reported because spec §6
asks for both; neither confirms the other. On this run both are zero, and
`coverage_after` equals `coverage` on all seven rows for that single reason.

**The gap is `slope`, essentially entirely.** With `gap = total − occupied`:

| subject | gap | `level_injectable` / gap | `slope` / gap | `unreached` / gap | `hinge` / gap |
|---|---:|---:|---:|---:|---:|
| `starfish` | 58 | **0.0%** | 96.55% | 3.45% | 0% |
| `lizard` | 4,624 | **0.0%** | 100.00% | 0.00% | 0% |
| `frog` | 5,762 | **0.0%** | 100.00% | 0.00% | 0% |
| `horse` | 8,414 | **0.0%** | 100.00% | 0.00% | 0% |
| `bird` | 11,578 | **0.0%** | 100.00% | 0.00% | 0% |
| `guinea_pig` | 16,338 | **0.0%** | 100.00% | 0.00% | 0% |
| `octopus` | 21,808 | **0.0%** | 99.98% | 0.02% | 0% |

Across the whole censused corpus — 136,504 segments (the sum of the `total`
column) — `level_injectable` is **0**, `hinge` is **0**, and `unreached` is
**6** (2 on `starfish`, 4 on `octopus`). The gap is `slope` and nothing else,
to within six segments.

`hinge` reading 0 everywhere is worth stating for its own sake: spec §10 added
that bucket because the `level_injectable` predicate was missing its validity
clause, and the omission ran *in the direction favouring BUILD*. Measured, it
turns out nothing was inflated — but the fix was still necessary, because on
five of these seven subjects nobody had checked.

## 4. The contiguity reading

Connected components over half-grid points, on `occupied` before and on
`occupied | level_injectable` after:

| subject | components before | components after | fell? |
|---|---:|---:|---|
| `starfish` | 6 | 6 | no |
| `lizard` | 34 | 34 | no |
| `frog` | 31 | 31 | no |
| `horse` | 54 | 54 | no |
| `bird` | 91 | 91 | no |
| `guinea_pig` | 71 | 71 | no |
| `octopus` | 134 | 134 | no |

**This reading carries no independent weight on this run, and it would be
dishonest to present it as a second finding.** `level_injectable` is empty on
every subject, so the "after" set is *identical* to the "before" set and the
counts are equal by construction rather than by measurement. `components_fell:
False` in `verdict_figures` is true but vacuous. The contiguity reading was
designed to separate spec §6 row 1 from row 2 — both of which require ≥25%
injectable — and neither row is in play. **The verdict below rests on the
fraction alone.**

The before-counts are still informative as a description of today's pattern:
the occupied candidate set is in 34 pieces on `lizard` and 134 on `octopus`, so
the pattern really is far from COrigami's "fully contiguous fundamental grid".
What this census establishes is that `fill`, under its own contract, cannot
reduce those numbers by one.

## 5. The verdict (spec §6): row 3, DO NOT BUILD

Evaluated on `lizard`, the subject the hypothesis is about and the only one that
produces a dense labelling to test against. The script printed:

```
VERDICT (lizard): DO NOT BUILD
  gap 4624, injectable 0.0% of it, components fell: False
  A no-op, like the pleat filter. The slope/unreached split is the finding; if
  slope dominates, COrigami's contiguous grid is unreachable from an elevation
  field (spec §3).
```

`verdict_figures` in the artifact: `{"gap": 4624,
"injectable_fraction_of_gap": 0.0, "components_fell": false}`.

**Why row 3 and not its neighbours.** The bar's thresholds are fractions of the
gap, and `lizard`'s gap is 4,624 segments:

* **Rows 1 and 2 (BUILD / BUILD NARROWED)** need `level_injectable / gap ≥ 0.25`,
  i.e. **≥ 1,156** injectable segments. Measured: **0**.
* **Row 4 (REPORT AND DECIDE, the 5–25% band)** needs the fraction at or above
  0.05, i.e. **≥ 232** injectable segments (0.05 × 4,624 = 231.2). Measured:
  **0**.
* **Row 3 (DO NOT BUILD)** is the strict `< 0.05` case. Measured fraction
  **0.0000**.

This is not a boundary case and does not turn on where a threshold was drawn.
**Zero is the floor**, 232 segments below the nearest other row, and the same
zero recurs on all six other subjects independently. Had the bar's thresholds
been set anywhere in (0, 1], the row would be the same. That matters because
the point of pre-registering a bar is to be held to it, and the honest report
here is that the data did not come near needing the bar's precision.

**What the finding is, since `slope` dominates (spec §3).** A contour is a
*level line* carrying **one** elevation — `contours.py` keys segments "each
carrying an elevation", and within one face of the ridge subdivision "the
elevation is linear and its contours are parallel". A segment whose two
endpoints sit at *different* elevations is therefore not a level line anywhere,
at any elevation. `fill` is not declining to invent a value for such a segment:
**there is nothing there to find.** The gap is 96.55%–100.00% `slope` on every
censused subject, so the gap is not headroom that a better `fill` could take —
it is structurally not contour-shaped.

The consequence for the architecture: **COrigami's "fully contiguous
fundamental grid" is not reachable from the elevation fields measured here.**
Their injected
segments carry no elevation; ours must, because `assign.profiles`,
`label_from_profile` and the layer stage all consume the field. So the coverage
deficit is **a consequence of consciously rejecting F.1.1 steps 1-4** (spec §2:
the paper's filter produces segments, not elevations, and specifies no
replacement for the field) and **not a defect in `contours.py`, in `fill`'s
absence, or in this pipeline's implementation of anything.** The half-covered
half-grid is what the elevation fields measured here produce. Closing it
looks, on this evidence, like a change of formulation rather than a missing
component.

`unreached` is the bucket that a weaker predicate could in principle reach —
one inferring an unknown endpoint from the field's 1/2-Lipschitz bound, which
spec §11 puts out of scope because it invents field values. It is worth
recording that this escape hatch is also empty in practice: `unreached` totals
**6** segments across 136,504. Even granted a predicate the component's
contract forbids, there is nothing to gain.

## 6. Does ~49% coverage hold across the corpus?

Spec §9 struck the `starfish` control, because measured coverage sat in a
48.2%–49.9% band across what was then a 13× range in N. **There is no
high-coverage subject, so there is no control on that axis** and none is
written here. The replacement question is whether the near-constant figure
holds corpus-wide.

**It does, and more tightly than the three subjects it was inferred from.**
Coverage on the seven censused subjects: 48.2, 49.3, 49.5, 49.7, 49.9, 49.7,
49.9 — a band **1.7 points wide** (48.2% to 49.9%) across **N = 4 to 74**, an
**18.5× range** in problem size, and over a segment count running from 112 to
43,512. The four subjects §9 had never measured (`frog`, `horse`,
`guinea_pig`, `octopus`) all land inside the band the first three defined;
`starfish` at N=4 is the low outlier and the only subject below 49%.

A quantity that barely moves over an 18.5× range in problem size is a finding
about the elevation field in its own right, not a coincidence of three
subjects: the field occupies just under half the non-boundary half-grid
essentially regardless of size. Read beside §3's structural argument, the two
fit: `occupied` and `slope` are near-equal partners on every subject
(`lizard` 4,488 vs 4,624; `bird` 11,534 vs 11,578; `octopus` 21,704 vs
21,804), with `slope` consistently the slightly larger. The ~49% is not a
shortfall against an achievable 100%; it is what a linear elevation field on
this grid looks like.

## 7. What this cannot say (spec §7)

**Nothing here tests whether higher coverage would make dense layer-ordering
converge.** The limit is symmetric and is stated in the direction this result
actually fell: a BUILD verdict would have licensed *building* `fill` and would
**not** have predicted convergence — and equally, **DO NOT BUILD does not show
that dense layer-ordering cannot be made to converge.** It shows that *this
lever cannot act*. The §1 hypothesis (that the wall is caused by low coverage
and non-contiguity) is **not refuted by this census**; what is established is
that component 1 is not the instrument that could test it, because component 1
has nothing to inject. Anyone reading this as "coverage is not the problem"
would be overclaiming in exactly the way
`2026-09-28-witness-identity-design.md` §3.3 records being corrected one slice
ago: a bar's threshold and the inferences attached to it are different things.

Two further limits, unchanged by the result:

* **Coverage is not the only difference from COrigami.** The search-strategy
  divergence (spec §2.3 — their hinge search is score-guided, ours is exhaustive
  DFS on Maekawa plus CEGAR) is **untouched by this census and unaffected by
  its outcome.** On a pattern where stackable labellings are rare, a lucky
  heuristic and an exhausted exhaustive search are indistinguishable from
  outside, and nothing measured here speaks to that.
* **`layer_order._propagate` is not confluent**, so `consistent` is never a
  foldability proof. That costs completeness, not soundness — the 113 refusals
  (`2026-09-24-dense-pleats-design.md` §6.3) are real contradictions. This
  census does not change it in either direction,
  and **no result here may be read as strengthening a `consistent` verdict.**

## 8. Spec §9's correction, restated

The coverage figures this slice was originally built on are **unreproducible**.
`2026-09-24-dense-pleats-design.md` §2 claimed candidate coverage of the
half-grid at `starfish` 94.4%, `lizard` 54.8%, `bird` 54.7% (those three
figures are quoted from *that spec*, as the claim under correction — not
measured here). They entered the repository in commit `42ae862` and no
committed script computes them; they were quoted forward into three later
documents, always as a quotation, never recomputed.

Measured by this run, over non-boundary half-grid unit segments keyed with
`contours._key`:

| subject | claimed by `2026-09-24-dense-pleats-design.md` §2 | measured here |
|---|---|---|
| `starfish` | 94.4% | **48.2%** (54 / 112) |
| `lizard` | 54.8% | **49.3%** (4,488 / 9,112) |
| `bird` | 54.7% | **49.9%** (11,534 / 23,112) |

**The direction does not favour the hypothesis.** Real coverage is *lower* than
claimed, so the gap component 1 would have closed is *larger*, which slightly
strengthens §1's motivation rather than weakening it — and that gap then turned
out to be `slope`, which no `fill` can take. The measurement is trusted over
the quotation because the `occupied` column is independently corroborated by
§2's two counts above, recorded by slices with no coverage figure in view; what
the old percentages disagree about is the denominator (spec §9: `starfish`'s
94.4% implies a denominator near 57 against an actual 112 — a different
quantity, not a variant convention).

This is the third unreproducible figure found on this branch. **The script that
computes these figures now ships with the slice** (`headroom.py`, committed
beside this README) and its output is committed as `headroom.json`, so the
figure cannot go unreproducible again the way its predecessor did.

A single-subject probe run during Task 1's code review read `lizard` as
occupied 4,488 / level_injectable 0 / slope 4,624 / unreached 0 / hinge 0,
total 9,112. Of those six figures, three are checkable against committed
records — `occupied` 4,488 and `total` 9,112 against spec §9's table, and
`hinge` 0 against spec §10 — and **this run reproduces those three exactly**.
The probe itself was recorded in a review report that lived under
`.superpowers/`, which `git ls-files .superpowers` shows is untracked, so the
remaining three figures (`level_injectable` 0, `slope` 4,624, `unreached` 0)
are **not independently verifiable** and are not offered here as
corroboration.

## 9. Run metadata

Recorded **in `headroom.json` itself**, not only in this prose — spec §8.5
named this script as the place to close a deferral that had sat unactioned in
two prior READMEs:

* `"commit": "d5a74dbb35f5eb1c8787dc9e5a7133ed9e75b301"`
* `"measured_utc": "2026-09-29T01:00:41+00:00"`
* `"cap_secs": 300`

Sparse `compile_secs` per subject, from the artifact: `starfish` 0.1,
`bird` 3.5, `lizard` 6.5, `horse` 14.4, `octopus` 34.6, `frog` 53.2,
`guinea_pig` 274.1; `dog` exceeded the 300 s cap. Note that compile time does
not track N — `bird` (N=54) compiles in 3.5 s while `frog` (N=38) takes 53.2 s
and `guinea_pig` (N=64) takes 274.1 s, within 26 s of the cap.

**The corpus size is timing-dependent, not just close to the cap.**
`guinea_pig` read 274.1 s here against 283.5 s in
`docs/superpowers/evidence/2026-09-26-gap1-phase0/phase0.json` — two
measurements of the same subject on (presumably) different runs, 9.4 s apart.
A host running roughly 10% slower than this one would push `guinea_pig` past
300 s the way `dog` already is, and the headline in §3 would then be six rows,
not seven. The 26 s margin noted above is the same fact stated as a gap
instead of a risk.

`headroom.py` was not modified during or after the run: its git blob hash is
`cebe76134da1d35f48f3d60668d682244d34aeb2` both before and after, and
`git status --porcelain` is clean for it. Nothing under `mcp_harness/` changed
across this slice. `git diff --stat HEAD -- mcp_harness/` alone only shows
**uncommitted** drift and would read empty even if the slice had rewritten and
committed changes there, so the range-scoped check is
`git diff --stat 811cd77..cfa6089 -- mcp_harness/` (empty, across the plan
commit through the last commit of this slice) and `grep -c box_pleat
mcp_harness/server.py` (**0**), as spec §8.1 requires.
