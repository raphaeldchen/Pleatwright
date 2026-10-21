# S2 — a mirror-equivariant facet-ordering cut

**Date:** 2026-08-04
**Status:** design, awaiting review
**Slice:** 2 of the Goal 2 decomposition. See `docs/superpowers/goals/goal-2-symmetry/PROGRESS.md`.
**Base commit:** `1c9abe0`

> **The mechanism is established, not hypothesised.** A crease pattern whose
> geometry mirrors exactly comes out with mirror-image creases folding opposite
> ways **iff the crease where TreeMaker cuts the facet-ordering cycle is not
> fixed by the mirror.** 192 evaluations, zero exceptions — and one controlled
> test in which nothing varies but the axis you read against.

---

## 1. What is broken, and where

`tmCrease::CalcFold` is the **sole writer** of the M/V label
(`treemaker/Source/tmModel/tmTreeClasses/tmCrease.cpp`); `ExportFold` in
`TreemakerWrapper.cpp` is the sole reader. Its four branches collapse
algebraically to one rule:

> **M ⟺ order(COLOR_UP facet) > order(WHITE_UP facet)**

verified `bad = 0` on every non-border crease of every pattern compiled. The
`mFwdFacet`/`mBkdFacet` distinction cancels, so crease construction order cannot
matter. Facet **colour** is perfectly anti-equivariant under the mirror σ
(24/24, 26/26, 50/50 — no exceptions), because `CalcColor` flips at every folded
crease and every self-mapped on-axis crease measured is folded.

**Both orientation-dependent halves flip together and cancel. The defect is
entirely in the facet ORDER.**

`tmPoly::CalcLocalFacetOrder` builds a directed **cycle** per polygon. Lang's own
comment says *"Breaking the axial loop at any local root vertex gives a valid
facet ordering graph"* — **the cut is an acknowledged free choice.**
`tmFacet::CalcOrder` then numbers the cut path 0…n−1.

### 1.1 The predicate

> **The M/V assignment is mirror-perfect ⟺ the CUT CREASE is σ-FIXED**
> (both endpoints on the mirror axis).

| sample | cut σ-fixed → symmetric | cut not σ-fixed → asymmetric | exceptions |
|---|---|---|---|
| first recon, 58 patterns | 16 / 16 | 38 / 38 | **0** |
| root sweep, 192 evaluations (serve + pinned-seed arms, 45° and 135°) | 40 | 152 | **0** |

Clean patterns achieve a *perfect* global order reversal `ord(σF) = n−1−ord(F)`;
defective ones achieve **0/24** global reversal while still getting **32 of 34**
pairwise comparisons right — a DAG whose forced comparisons are symmetric but
whose linear extension is not.

On `TEMPLATE_QUADRUPED` the cut crease is `v13–v15` (facets 23, 0) and its mirror
`v22–v15` (facets 11, 12): **those two creases ARE the single offending pair.**

### 1.2 The controlled test — why this is established rather than correlational

192 correlational evaluations could in principle survive a confound in packing
basin, label convention or geometry. One measurement holds all three fixed by
construction.

`star-4` re-rooted at 1–4 produces **one crease pattern** with **one** cut crease
(`v3–v0`, RIDGE, 8 facets). Vary nothing but which σ it is read against:

| axis read against | is the cut σ-fixed? | is the assignment mirror-perfect? |
|---|---|---|
| 45° (main diagonal) | **no** | **no** — 0 swapped / 4 mismatched |
| 135° (anti-diagonal) | **yes** | **yes** — 0 / 0 |

Same geometry, same labels, same cut. **Both sides of the biconditional flip
together.** Packing basin, convention and geometry are identical across the two
readings, so none of them can be the cause.

### 1.3 Two cut sites, and a third cut kind

| root node kind | cut crease kind | count | site (`tmTree_FacetOrder.cpp`) |
|---|---|---|---|
| BRANCH | fHINGE | 37 | `tmRootNetwork::BreakOneLink` (`mCC1.front()` / `mCC2ST1.front()`) |
| LEAF | RIDGE | 17 | `tmRootNetwork::ConnectFacetGraph`, `mCC0.size() == 1` branch |

⚠ **A third kind exists and falsifies "hinge or ridge" as stated.** The root
sweep found 5 **AXIAL** cuts (`star-5` roots 1–5, in the 33/64 middle-flap pack,
cut `v0–v2`, multiplicity 1). All 5 are σ-fixed and all 5 are symmetric, so the
*predicate* is untouched — but the kind tracks the root class only within a
single pack topology. `BreakOneLink` returns immediately when `mCC0` is
non-empty, so the two named sites are mutually exclusive per compile.

### 1.4 ⚠ Locating the cut from an exported `.fold` is UNRELIABLE

The read-off used throughout this investigation — *"the cut is the crease
separating facet `mOrder 0` from facet `mOrder n−1`"* — fails on
pseudohinge-bearing patterns, and the dog is one of them.

`BreakOneLink`'s `mCC1` branch calls
`Unlink(theCrease->GetLeftNonPseudohingeFacet(), theCrease->GetRightNonPseudohingeFacet())`,
and both accessors **walk past pseudohinge facets**
(`for (; theFacet->IsPseudohingeFacet(); theFacet = theFacet->GetLeftFacet());`).
When a pseudohinge sits beside the chosen hinge crease, the two unlinked facets
are not that crease's own, and no crease separates them.

| | PSEUDO creases > 0 | PSEUDO == 0 |
|---|---|---|
| cut identifiable | 3 | **18** |
| cut NOT identifiable | **14** | **0** |

**`PSEUDO == 0 ⟹ cut identifiable`, 18/18, zero exceptions.** The dog has 2
pseudohinge creases and 0 unordered facets.

**Consequence: the cut is still being made — our read-off instrument fails, not
the mechanism.** A fix inside `BreakOneLink` sits where the choice happens and
does not need the crease to be locatable from the `.fold`. **This invariant is
recorded in a comment at the read-off site** (§5, Task 6) so it is not
re-derived in three months.

---

## 2. Prior art (CLAUDE.md §0)

| Source | Finding | Adopted / rejected |
|---|---|---|
| Lang & Demaine, *Facet Ordering and Crease Assignment in Uniaxial Bases*, Origami⁴/OSME 2006 ([PDF](https://erikdemaine.org/papers/TreeMaker_OSME2006/paper.pdf)) | The M/V assignment is **derived** from a facet ordering: *"the primacy of the ordering relationship, rather than the crease assignment, as the fundamental mathematical description."* The only degeneracy acknowledged is the **global** M↔V swap. The word "symmetry" appears once in the chapter, in a reference's journal name | **ADOPTED as the authoritative statement of what the compiler does; REJECTED as a source of a fix.** It licenses intervening on the *ordering* rather than the labels, and confirms the global swap is irrelevant here (it flips every crease, so it cannot repair a *pair* that disagrees) |
| Lang's own in-source comment, `tmPoly::CalcLocalFacetOrder` | *"Breaking the axial loop at any local root vertex gives a valid facet ordering graph"* | **ADOPTED as the licence.** The cut is an acknowledged free choice, so constraining it does not violate the algorithm's contract — this is the single most load-bearing citation in the spec |
| Bowers & Streinu, *Lang's universal molecule algorithm*, AMAI 74 (2015) ([Springer](https://link.springer.com/article/10.1007/s10472-014-9437-3)) | Formalises and proves the universal molecule's **geometry**; says nothing about M/V or facet order | **REJECTED, with one caveat kept:** there is no published theorem that the universal molecule is equivariant, so *"the CP geometry is exactly symmetric"* is an empirical observation in this repo, not a guarantee |
| COrigami, [arXiv:2606.26299](https://arxiv.org/abs/2606.26299) §3.3 | Treats "symmetric" as a first-class M/V motif and *"scoring ties are resolved by evaluating hinge length and symmetry"*; threads symmetry through four pipeline stages | **ADOPTED as precedent and as a caution.** Resolving assignment ties by symmetry is **well-trodden, not novel** — so this slice is low-risk, and its contribution is the *measurement*, not the idea. That they thread symmetry through four stages while we thread it through one is a reason to expect a tie-break alone may not carry the whole load |
| Crawford, Ginsberg, Luks & Roy, *Symmetry-breaking predicates*, KR 1996 ([PDF](https://ix.cs.uoregon.edu/~luks/symmetrybreaking.pdf)); Anders et al., CP 2024 ([LIPIcs](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.CP.2024.3)) | Lex-leader and its complexity; choosing *any* canonical representative among symmetric solutions is permissible | **LICENCE ADOPTED, MACHINERY REJECTED.** It licenses a canonical tie-break as legitimate; but lex-leader machinery shrinks a search tree over a large group, and |⟨σ⟩| = 2 |
| McKay & Piperno (nauty/Traces), *J. Symb. Comp.* 60 (2014); bliss; saucy | Canonical labelling / automorphism detection | **REJECTED as the formulation.** Our graph is fixed and σ is handed to us geometrically by `cp_mirror.mirror_bijection`. Running nauty to rediscover a mirror we can read off the coordinates is more machinery for less information. Kept as the right tool only if a future slice needs the *full* automorphism group |
| Herr & Bödi, *Symmetries in linear and integer programs* ([arXiv:0908.3329](https://arxiv.org/abs/0908.3329)); Waterhouse, *Do symmetric problems have symmetric solutions?*, AMM 1983 | A symmetric problem need not have a symmetric optimum without convexity | **ADOPTED as a caution on the acceptance wording** (§6): do not write a criterion asserting `mv_swapped == 0` is always achievable; distinguish *fixed*, *no symmetric choice available*, and *refused* |
| Tachi, Freeform Origami ([software](https://origami.c.u-tokyo.ac.jp/~tachi/software/)) | `Tool→EqLen` / `Tool→EqAngle` constrain an edge group to equal fold angle | **ADAPTED as precedent for the constraint, not the method** — the only shipped mechanism found anywhere expressing "these two creases must agree". Manual, continuous, and in a rigid-origami solver |
| Oriedita, ORIPA, Origami Simulator, Flat-Folder, GamiBench, Origamizer | None offers a symmetric-solve or assignment-symmetrising mode | **REJECTED.** Recorded because absence is a citable finding here |
| Sareh & Guest, symmetric Miura descendants, *SMS* 24:8 (2015) | Group-theoretic origami design by **reducing** a wallpaper symmetry group | **REJECTED with reason.** Generative and tessellation-only; a uniaxial base has one finite mirror, and we need selection among assignments, not generation of patterns |

**Honest negative, recorded with its search terms so it is not repeated:** no
publication, tool, or open-source implementation was found that constrains or
tie-breaks a facet-ordering / topological-sort choice by a graph automorphism,
in origami or in general combinatorial optimization. The nearest hits are all
partial (above). This follows the precedent of `polys-multiple-ibps-is-inherent`
and `molecule-mobility-outcome`.

---

## 3. What was rejected, and why it stays rejected

**Post-hoc symmetric relabelling in Python (`mv_repair` or a new pass).**

* `mv_repair` **never runs** on any subject carrying this defect — measured 6/6
  with a call spy and two live positive controls. It is a defect reducer gated
  on `cp_audit`-dirty folds, and these swaps appear only on folds that pack
  **clean**. The swapped assignments are raw TreeMaker output.
* Reaching a `cp_audit`-clean symmetric assignment costs **11 of 30 M/V labels
  (37%)** on the smallest case, 9 on insect, 14 on the dog.
* ⚠ **That number prices post-hoc repair, not the source fix.** Post-hoc, each
  flip breaks Maekawa at its far endpoint and the correction cascades through an
  already-committed assignment. At source there is no cascade — the engine
  recomputes every downstream choice consistently. **Do not cite 11 as a cost
  estimate for this slice.**
* The decisive objection is different: `cp_audit` checks **local**
  flat-foldability conditions only. It does not check *"folds to the intended
  uniaxial base."* With 37% of the labels ours, a relabel asserts
  foldability-to-target on an instrument blind to that failure — the same error
  as the three metrics that scored a lopsided pattern `0.000000`, relocated.
  **A relabel asks us to vouch for a folded state; a source fix asks the
  compiler for one.**

**Re-rooting as the fix.** `tmTree::GetRootNode` returns `mNodes.front()`, so the
root — and the cut — is selected by the JSON node list we control from Python,
and every re-rooted compile is a genuine TreeMaker output. Measured as an
**assignment-only lever**: at a pinned placement seed, 48 of 68 variants are
geometrically identical with 2–8 labels changed, **0** have different counts, and
design scale is identical to ~1e-8. Rejected as the fix on three measurements:

1. **It does not reach the dog** — 0 of 10 roots, plus 10 more under forced
   placement. 0 of 20.
2. **The committed defaults are load-bearing.** `star4pairs` root 0 is its only
   symmetric root (4 of 5 alternatives break it); `HSHAPE` root 0 likewise (5 of
   6). A symmetric root exists for only 6 of 10 patterns, is rare (13 of 68), and
   is not predictable from node degree.
3. **The serve path re-seeds.** `build_tree_from_json` seeds node positions from
   **list index**, so a re-rooted list starts the packer elsewhere; `TEMPLATE_BIRD`
   roots 7/8 are symmetric under a pinned seed and lose the bijection on the
   serve path. A re-rooting policy that does not also control the seed will not
   deliver the roots it selects.

Kept as a **diagnostic**, and its by-product handed to Goal 1 (§8).

---

## 4. Architecture

### 4.1 §A — the FOG-DUMP experiment. Gated; it reports before §B is written.

Env-guarded (`TM_DUMP_FOG`), read-only, no behaviour change. From
`tmTree_FacetOrder.cpp`, dump: every facet's `mOrder`, `mColor`, centroid and
`mHeadFacets`; which `BreakOneLink` branch fired and the chosen vertex's `mLoc`
with `|x−y|`; `ConnectFacetGraph`'s `mCC0` unlink/skip choices; and the absorb
loop's vertices.

**The gate is ONE cross-tab, and everything else in the dump is diagnosis:**

> On `TEMPLATE_QUADRUPED`, whose ordering gets **32 of 34** pairwise comparisons
> right and **0 of 24** globally: **are the 2 pairwise misses the offending
> mirror pair, or unrelated creases?**

Forced comparisons that were themselves asymmetric would surface as pairwise
*failures*, not pairwise successes — so the existing 32/34 signature already
predicts "incomparable". This measures it.

### 4.2 Routing, pre-committed — the report-back is a lookup, not a round trip

| §A finds | §B does |
|---|---|
| offending pairs FOG-**incomparable** (the 2 misses are unrelated) | proceed to the **tie-break fix**, no round trip |
| **mixed** across the four patterns | proceed on the incomparable subset; report the rest as a separate finding |
| offending pairs **comparable-and-wrong** (the 2 misses *are* the offending pair) | **STOP and report.** The FOG itself is asymmetric — graph surgery, a different slice |
| orthogonally: **no σ-fixed hinge available** at the cut vertex | the **symmetric-cut** variant (break both members of the mirror pair, or re-link compensatingly), proceed |

The last row is real, not hypothetical: at `TEMPLATE_QUADRUPED`'s cut vertex
`v15 = (0.503885, 0.503885)` the *only* two hinge creases **are** a mirror pair
of each other, so there is no σ-fixed hinge there to cut.

The branches are not peers. The tie-break fix is local and reversible; changing
the FOG is graph surgery whose blast radius crosses every pattern that orders
facets at all. **Speccing the expensive branch blind is the most costly thing
this document could contain if it turns out unnecessary** — and the 32/34
signature says it probably is. The space is at least 2×2 (branch × hinge
availability), "mixed" is likely across four patterns, and neither typechecks as
a runtime choice a single session could make without inventing scope. Hence two
sessions with a pre-routed gate.

### 4.3 §B — the fix

Prefer a σ-fixed cut where the choice is genuinely tied, at whichever site §A
identifies.

**The gate is a LOCAL GEOMETRIC PREDICATE at the choice point**, never
`HasSymmetry()`:

* `mSymPairs` **does not exist in the engine** — it is a `HeadlessTreemaker`
  member in the wrapper. Zero hits in vendored source. Every file on the
  assignment chain contains zero symmetry tokens: **general path**.
* `HasSymmetry()` is **neither sound nor complete** — 26 corpus cases, **5 false
  negatives and 5 false positives**. `star-4` and `quad` are committed goldens
  with zero declared pairs that ARE mirror bijections and DO carry the defect.
* Declared pairs are not the operative variable: `star-4` vs `star-4-sym` have
  byte-identical node lists, and the pairs change the **packing**, not the
  assignment. `star-6` goes from 2 swapped to **6** when pairs are declared.

**Reachability costs nothing.** `tmPart` exposes `tmTree* GetTree() const`
publicly, and every arbitrary-choice site already holds a `tmPart`-derived
object (`BreakOneLink`'s `mCC1.front()` / `mCC2ST1.front()` are `tmVertex*`).
**Zero function signatures change** — which also keeps the ODR trap dormant.

⚠ **ODR status, refined** (this corrects memory `treemaker-odr-tmtree-header`):
measured with `clang++ -E -H` under `build.sh`'s exact flags, **0 of 53 TUs
resolve the stale `Source/tmTree.h`** — all 10 direct includes live inside
`tmTreeClasses/`, where the including file's own directory wins. **Dormant, not
absent:** `-I"${TM_SRC}"` is listed first, so any new `.cpp` **outside**
`tmTreeClasses/` writing `#include "tmTree.h"` gets the stale copy, and the
shared `_TMTREE_H_` guard silently shifts `mHasSymmetry` / `mSymLoc` /
`mSymAngle` by 8 bytes. Any new probe TU outside `tmTreeClasses/` must include
`"tmModel.h"` or `"tmTreeClasses/tmTree.h"` explicitly.

### 4.4 §C — the oracle, `mcp_harness/cp_mirror_oracle.py`

Verifier, not fix. Pure Python, spawn-safe, no engine/JVM imports.

```
symmetric_and_clean(fold, *, axis_degrees, tol=1e-6) -> dict
    ~1-3 ms. mirror_verdict AND cp_audit.audit_fold(...).clean, one boolean
    plus a renderable reason. What a CI assertion calls.

solution_set(fold, *, axis_degrees, tol=1e-6, max_solutions=100_000)
    -> OracleResult
    ~0.4 ms (quadruped) to ~20 ms (dog). The full enumerated set, for
    diagnosis and for membership.
contains(result, fold) -> bool          fingerprint-checked
to_fixture / from_fixture
```

**★ `axis_degrees` is a REQUIRED parameter on both tiers, and every assertion
names the axis it asserts at.** `mirror_verdict`'s hard-pinned 45° was measured
to manufacture **false negatives** on D4-displaced packs — `quad` re-rooted at 0
or 2 is the committed CP carried by `rot270` / `flip_v` and reads
`no-bijection` at 45° while being a clean bijection at 135°; re-rooted `star-4`
is mirror-perfect about the **anti-diagonal**. A CI assertion built on a
45°-only reading will fail a legitimate fix. **§A's own dump records
σ-fixedness against all four candidate axes** for the same reason — otherwise it
inherits the defect it just found.

**Membership, never equality.** The clean symmetric assignment is **not
unique** — 8 solutions for `TEMPLATE_QUADRUPED`, 36 for insect, 144 for the dog,
and **12 for `star-4+pairs` and 4 for `HSHAPE`, which the engine already gets
right**, so non-uniqueness is not an artefact of the broken cases. And **minimum
weight is measured from the current buggy labels**, so it stops meaning anything
the moment the fix lands: the solution *set* is label-independent (proven — 
rebuilding the oracle from a different member of its own set returns the
identical set), the min-weight *subset* is not.

Two structural facts make it cheap enough for CI: a symmetric assignment carries
one label per σ-**orbit**, and `cp_audit.clean` **factorises per interior
vertex** under M↔V relabelling, because closure and Kawasaki are provably
invariant under any M↔V flip (`flat_fold.edge_transform` reflects for both) —
measured bit-unmoved across 160 random relabels.

**The limit, stated in the module docstring so it cannot be over-claimed.**
`cp_audit` has no global check with discriminating power over relabels; the
entire certification is **local**, and local flat-foldability does not imply
global. It never sees layer order and never sees the tree. **Nothing in it says
the pattern folds to the intended uniaxial base.** The one claim this slice is
entitled to make: *"the served crease pattern is exactly mirror-symmetric about
the stated axis and satisfies every local flat-foldability condition this repo
can check."*

### 4.5 §D — golden movement, attributed, with `hshape` as the stop condition

`star-4` is **expected to move** — zero declared pairs, mirror bijection,
defective. Movement gets **its own ledger**, separate from the frozen scorecard,
one row per moved golden with a cause.

> ⚠ **CORRECTED 2026-08-05 — `quad` is REMOVED from the expected-to-move list
> and becomes a STOP SIGNAL, like `hshape`.** Its colour is **not**
> anti-equivariant (6/10, versus 24/24 · 24/24 · 26/26 · 50/50 on the four
> targets), so "the order comparison must reverse" measures the wrong thing
> there. Its only defect reading is `mv_mismatched = 6` through the separate
> `CalcBend` chain, with `mv_swapped = 0` — and it passes an `mv_swapped == 0`
> gate today for the wrong reason (its offending pairs are `fHINGE↔uHINGE`, and
> a `uHINGE` is `FLAT` *before* `mOrder` is ever read). An artifact that is
> uninformative about the mechanism cannot be *expected* to move for it.
> **`quad` movement is a stop signal.** It also has two packing basins that
> change the symmetry verdict itself, so movement there is doubly ambiguous.

**★ `hshape` is the NEGATIVE CONTROL, not a fixture footnote.** `HSHAPE` root 0
is its only symmetric root and 5 of 6 alternatives break it. It is currently
correct and must stay correct: **if `hshape.fold` moves at all, §B's blast radius
is wrong and the run stops.** Same for `star-4+pairs`.

⚠ **Each ledger row carries the before/after verdict of every consumer test.**
`star-4.fold`, `hshape.fold`, `quad.fold` and `dog.fold` are read as *input*
fixtures by `test_flat_fold` (`CLEAN_RAW`), `test_layer_order`
(`CONSISTENT_FIXTURES`), `test_rigid_fold`, `test_shaping_deep` and
`test_fold_mutate`. A re-bless is a re-verification of the flat-fold and
layer-order tiers, not a one-file diff — and `layer_order` has a recorded
shared-edge-clipping defect, so a re-bless there **can mask a real failure as
easily as introduce one**.

---

## 5. Test surface

| tier | what |
|---|---|
| CI, serve path | `star-4+pairs` and `HSHAPE` assert `symmetric is True` at 45° with `mv_preserved > 0` — **unchanged, untouched** |
| CI, serve path | `TEMPLATE_QUADRUPED`, `TEMPLATE_BIRD`, mesh `insect` assert `mv_swapped == 0` **paired with `mv_preserved == <full edge count>`**, so a "fix" achieving symmetry by deleting creases cannot pass |
| CI, serve path | `star-4` and `quad` — new assertions at whatever §B delivers, at a **named axis** |
| CI | the oracle's cheap tier on each of the above; `contains(solution_set(fold), fold)` on at least one |
| manual | the oracle's solution-set tier; the real-auditor whole-space control (5–10 min/pattern) |
| golden ledger | every moved golden, with all consumer-test verdicts before and after |

⚠ **`test_cp_mirror_serve.py::test_template_quadruped_is_pinned_red_on_mv_and_is_S2s_target`
MUST be edited.** It is an exact-equality **red** pin asserting the defect —
`mv_swapped == 2`, `symmetric is False`, and set-equality on the offender edges
`{frozenset((13,15)), frozenset((22,15))}`. An acceptance criterion worded *"all
existing tests stay green"* is unsatisfiable. The correct wording is *"this test
is inverted to its green form at equivalent strength, and the two controls stay
green untouched."*

**Task 6 — the durable comment.** The pseudohinge invariant (§1.4) goes in a
comment **at the read-off site**, wherever "the crease separating facet 0 from
facet n−1" is computed, with the 18/18 measurement. It is the kind of fact this
repo re-derives if it is not written down where it is used.

---

## 6. Acceptance criteria

1. `mirror_verdict(..., axis_degrees=<named>)["mv_swapped"] == 0` on
   `TEMPLATE_QUADRUPED`, `TEMPLATE_BIRD`, mesh `insect`, and the **dog**.
   **This is the GOAL, not the ship gate** — see §7.
2. `star-4+pairs` and `HSHAPE` stay `symmetric True` / `mv_swapped 0`.
   **`hshape.fold` must not move at all** (§4.5).
3. Every golden that moves is attributed in the ledger, with all consumer-test
   verdicts before and after.
4. The engine's answer is a **member** of the oracle's solution set — never
   equality (§4.4).
5. No scorecard re-bless. Report the `--baseline` delta table and attribute every
   moved row; an unattributable row is a **finding**.
6. Verified on Linux in the `ci-amd64-run` container before merge.

⚠ Per Waterhouse / Herr & Bödi (§2), do not assume `mv_swapped == 0` is always
achievable. Where it is not, the outcome must distinguish **fixed**, **no
σ-fixed choice was available**, and **refused** — never silently pass.

---

## 7. The dog: goal, not gate — and the honesty constraint is structural

**Decision:** disambiguate first, then ship on what is reached. Blocking S2 on
the dog, when the dog may be unreachable for reasons that are not S2's, means the
mechanism never lands **and** the dog stays broken — strictly worse.

The re-rooting lever does **not** reach the dog (0 of 20). The pseudohinge
finding (§1.4) explains why the dog's cut is invisible in the `.fold`; **it says
nothing about whether §B can reach it.** §A's engine-internal print is what will
tell us.

The constraint that makes blocking tempting is **built in, not promised**:

* **S2's PR title and summary state the dog's status in the first line.** If the
  dog is open, *"symmetry fixed"* is not an available phrasing.
* **The follow-on slice opens WITH S2, not after it.**
* **Criterion 1 stands as the goal, not the ship gate.**

This encodes the failure recorded twice on this project: reporting a scorecard
win as the fix the user asked for. Three green templates nobody mentioned is a
scorecard win, not a fix.

---

## 8. Explicitly NOT in this slice

* **The `SIZE_MAX` / unordered-facet defect.** Ticketed. Measured off this
  slice's path: **0 unordered facets** on all four target patterns and the dog;
  only 4 of 85 patterns have any. ⚠ Two caveats kept: the cut predicate has
  **never been tested** on a pattern with unordered facets (both such patterns
  carrying a bijection have non-identifiable cuts — an untested stratum, not
  robustness); and `unordered > 0 ⟹ served `_layer_status` = contradiction`,
  4/4, against 30/31 consistent when fully ordered — the bug genuinely wrecks
  output, just never here.
* **`mv_mismatched` (folded ↔ flat).** Ticketed. A different chain — crease kind
  via `CalcBend`, driven by vertex depths from the root. QUAD's 6.
* **Exporting `faces_vertices` / `faceOrders`.** Candidate follow-on. Lang calls
  the ordering the fundamental description and the served `.fold` discards it;
  FOLD supports `faceOrders`, and exporting it is how any future verification of
  a folded state gets real footing.
* **Changing `mirror_verdict`'s axis policy.** §C parameterizes its *callers*;
  changing the metric itself is cross-goal — see COORDINATION.md §4.2.
* **The placement-seed coverage lever.** Handed to Goal 1: star-5 goes
  0.323556 → **0.353553** scale and 0.7039 → **1.0000** coverage, reproducing
  CLAUDE.md §1.1's cited Lang numbers to three decimals, with the mover being the
  index-based placement seed, reachable from Python. It may dominate Goal 1's
  S4b₀ on cost and is worth a **re-rank, not just an announcement**.
  ★ `star-5` is now load-bearing for **both** goals at once: Goal 1's headline
  coverage case is this slice's AXIAL third-cut-kind case (§1.3).

---

## 9. Risks

| risk | mitigation |
|---|---|
| §A finds "comparable" and §B is a different slice | Pre-routed (§4.2): stop and report. The cost is one experiment, not a wasted fix |
| The fix helps the four targets and breaks an untested pattern | `hshape` is a hard stop (§4.5); the golden ledger carries consumer-test verdicts; the full suite runs (2241/11/0 at `1c9abe0`) |
| Platform divergence | Boolean verdicts at `tol = 1e-6`, not frozen hashes over roundoff-bearing floats. Verify in `ci-amd64-run` before merge. ⚠ QUAD has two packing basins that change the **symmetry verdict**, not just coordinates — any new QUAD test needs the accommodation `goldens/basins/quad.json` already carries |
| The oracle over-claims | Its limit is in the module docstring and in every assertion's wording (§4.4) |
| `cp_audit.mv_arrangement_ok` is conservative and could shrink the solution set below the engine's answer | Measured: on all six patterns every non-exact sector tie is ≤ 2.8e-6 deg, three orders below the 1e-3 slack. Not a proof; the documented stall mechanism has no room to fire here |
