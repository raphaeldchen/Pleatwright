# GOAL 2 — mirror-symmetric crease patterns. PROGRESS.

> ## ✅ THIS GOAL IS CLOSED. **Read the CLOSING RECORD (2026-08-15) at the
> ## bottom of this file first.** Everything above it is the working history
> ## that led there, kept with its refutations attached rather than deleted.
>
> **The one-line answer:** **3 of 5** scorecard subjects now compile to a
> mirror-symmetric crease pattern (`humanoid`, `insect`, `quadruped`), from
> **0 of 5** at goal start — ⚠ **and it is 4 of 5 as of 2026-08-17: `bird`
> joined them under #129.** See the footnote at "Goal 2 closes at 3 of 5"
> below; this headline is a snapshot of `153f9c7` and is kept as written
> because every number under it was measured there — and the proof that said
> this was impossible was
> *correct about the wrong object*. The FOG's "exactly one linear extension /
> 225 of 225 creases forced" reproduces exactly; it measures **one**
> facet-ordering graph, the one built from the **dangle root**, and every
> compile in this project's history emitted the same root. Re-rooting builds a
> different graph. The lever is the **ROOT**, and it was never a tie-break.
>
> ✅ **THE PENDING CELL IS DISCHARGED** — it read **2 of 5** while
> `quadruped`'s `cp_symmetric` / `cp_mv_broken` awaited a `MAX_ORBITS` ruling.
> **The ceiling rose 40 → 45, and the reason is a second wrong object:**
> `MAX_ORBITS` is named and derived as a bound on *search size*, and the 2⁴⁵
> DFS costs **≤ 2 s**. The 22 s that failed PR #124's budget gate was spent
> validating all 288 audit-clean survivors **so they could be ranked**. Stop at
> the first one that passes all four conjuncts and the same subject costs
> **1.336 s**. Exactly the two promised cells moved; nothing else in this
> record did.

**Planning session's recovery map.** Assume this file is all that survives a
context compaction. Base commit for everything: `1c9abe0`.

**Planning worktree:** `goal-2-mirror-metric-planning-e2fc65`
**Branch:** `claude/goal-2-mirror-metric-planning-e2fc65`

---

## 0. Status

⚠ **SUPERSEDED — this table is the 2026-08-05 state.** Kept because §0.3's
argument is built on it and because the *shape* of the error is the lesson.
Live status is the CLOSING RECORD at the bottom.

| | |
|---|---|
| **Phase** | §A SHIPPED and INDEPENDENTLY VERIFIED. **Both C++ branches are now falsified — see §0.3.** Re-spec pending |
| **Approach** | ⚠ **(A) IS DEAD.** The engine provably cannot express the target. See §0.3 |
| **Spec** | [`docs/superpowers/specs/2026-08-04-mirror-equivariant-facet-cut-design.md`](../../specs/2026-08-04-mirror-equivariant-facet-cut-design.md) — §4.2/§4.3 SUPERSEDED by §0.3 below |
| **Next slice** | σ-symmetric M/V search **on the `.fold`**, gated by a non-crossing oracle. NOT in the C++ |
| **Committed so far** | `74d3483` `COORDINATION.md` · `c084cbf` spec · `822497b` (S2a FOG dump, branch `claude/goal-2-s2a-fog-dump`) |

### 0.5 ♻ RECOVERED from the unmerged planning branch (2026-08-09)

⚠ **This subsection is SALVAGE, and it too is superseded.** It was written at
`fd7a210` on `claude/goal-2-mirror-metric-planning-e2fc65` — a branch that
**never merged**, so `main`'s copy of this file sat at `a81708e` (2026-08-06)
for nine days and would have misled anyone who read it. The branch still
exists on `origin` and the commit is reachable; this is its content, preserved
rather than silently discarded. **Its §0.4 status table is wrong now** — see
the closing record — but its two *findings* are durable and one of them is
load-bearing for every count in this file.

| | |
|---|---|
| **Phase** (as of 2026-08-09) | S2′a and A-0 SHIPPED. S3 REFUTED before dispatch; the ordering slice HANDED TO GOAL 1. S2′b was believed to be the only slice left |
| **Approach** | The M/V fix is **post-hoc on the `.fold`**, never in the C++ (§0.3). Goal 2 holds **no** claim on `TreemakerWrapper.cpp` |
| **Live spec** | [`2026-08-06-mv-symmetrize-design.md`](../../specs/2026-08-06-mv-symmetrize-design.md) — S2′b. §2 satisfied by S2′a |
| **Dead specs** | [`2026-08-04-mirror-equivariant-facet-cut-design.md`](../../specs/2026-08-04-mirror-equivariant-facet-cut-design.md) 🛑 · [`2026-08-06-axial-leaf-pin-design.md`](../../specs/2026-08-06-axial-leaf-pin-design.md) 🛑 · [`2026-08-06-order-rank-attempt0-design.md`](../../specs/2026-08-06-order-rank-attempt0-design.md) → **Goal 1 owns** |
| **On main** | `1e4182c` S2′a (#93) · `f01a292` A-0 (#92) · `d035943` specs (#88) · `76ded05` (#86) |

**Three slices were stopped by measurement and that was right each time.**
S2 (mirror-equivariant facet cut) — the engine cannot express the target.
S3 (axial leaf pin) — its wins were the node-order lever, not the pin.
The ordering slice — real, but its criterion is the coverage/scale trade, so
**Goal 1 owns it**. **Two shipped:** S2′a closed a `layer_order` gap that
turned out to be **three** ADK families, not one; A-0 added the serve-path byte
pin for attempt-0 packers.

⚠ **Its per-subject table read `mesh-dog` ❌ 0 PROVEN, `template-quadruped` ❌ 0,
`mesh-insect` ❌ 0, and `mesh-bird`/`mesh-humanoid` ✅-pending-the-ordering-slice.
Every one of those numbers still reproduces on the fold it names. Three of the
five now describe a fold the serve no longer produces.** See the closing
record's per-subject section.

**★★ DURABLE FINDING 1 — MY OWN TOOLING WAS WRONG; do not reuse the counts in
spec §9.2.** The enumeration gave a SWAPPED orbit one bit meaning *"flip member
A or don't"*. A swapped pair has **TWO** valid symmetric resolutions — flip A
**or** flip B — so half the space went unexplored and **every count was
halved**. S2′a's pruned DFS is the trustworthy tool; its `template-bird` = 8
stands. The 4 was wrong, and it matched S2′a's *four-conjunct* figure by
**coincidence**, not because it was measuring that gate. ⚠ This is why the
gate-naming rule below matters: two different gates produced two numbers that
happened to agree. The bug is now an *assertion* rather than a memory —
`_assert_two_resolutions` raises on any orbit one of whose options leaves the
pair swapped, which makes the 2ⁿ symmetry claim O(n) instead of O(2ⁿ). It was
invisible to a count check because *"flip A, or don't"* still has arity 2: the
enumeration is still 2ⁿ points, what halves is how many of them are symmetric.

**★ DURABLE FINDING 2 — the Lang (A-20)/(A-21) sin/cos defect is DORMANT, not
retired.** S4b₀ builds book/90° rows directly from geometry and never calls
`StickToLineFn`, which has **zero** binding in the wrapper. It goes live only
if someone binds `SetToSymmetryLine`, i.e. only if S3 is revived. Keep as a
conditional.

### 0.3 ★★★ §A's OUTCOME — the fix CANNOT live in the facet ordering (2026-08-05)

⚠ **SUPERSEDED 2026-08-15 — AND NOT BY BEING WRONG.** Every number below
reproduces. What is wrong is the **scope** of the object they describe: the
FOG they measure is the one built from the **dangle root**, and the root was a
constant nobody had varied. Re-rooting builds a different FOG with a different
linear-extension count and a different forced set. "225/225 forced" is a true
statement about one graph and says nothing about the others. **Read this whole
subsection as `∀ facet-ordering graph G(root = mNodes.front())`, and note that
that quantifier was never written down.** See the closing record.

Independently verified by a 13-agent re-derivation plus my own measurements.
**No number in the S2a report failed to reproduce.** What changed is what the
numbers are allowed to mean, and the remedy.

**1. The target state EXISTS.** A mirror-symmetric M/V assignment that survives
the non-crossing oracle (`flat_fold` + `layer_order`) exists on **6 of 7**
subjects searched. Measured directly on the served `.fold`;
`scratchpad/own/own_exists{2,3}.py`. Mirror symmetry is **not** physically
unreachable — an earlier reading that it might be is wrong.

| subject | swapped pairs | valid target | flips needed |
|---|---|---|---|
| template-quadruped | 1 | ✅ | offending pair member 17 **+ σ-fixed 27** |
| template-bird | 1 | ✅ | 17 **+ σ-fixed 27** (identical combinatorics to quadruped) |
| **mesh-insect** | 3 | ✅ | 0, 10, 25 **+ σ-fixed 13** |
| **star-5** | 1 | ✅ | 8 only |
| star-4 | 1 | ✅ | 0 + preserved pair (2,3) |
| two-level-tree | 1 | ✅ | 1 + preserved pair (4,7) |
| **mesh-dog** | 5 | ⏳ **not yet found** | search bounded, inconclusive |

**★ The search space has three independent axes**, and getting this wrong is
easy: a SWAPPED pair needs exactly ONE member flipped (flipping *both* preserves
the swap — a first attempt searched only orbit-flips and reported NONE
everywhere); a PRESERVED pair takes both-or-neither; a σ-FIXED crease is a free
binary choice. Most valid targets need a **σ-fixed crease flip**, which is
exactly the degree of freedom the FOG has already spent.

**★ This proves the σ-aware cut lever is SUBSUMED, rather than assuming it.**
The lever could only ever have covered `insect` and `star-5` (the only subjects
with an unchosen σ-fixed candidate). Both are reached by the `.fold` approach —
insect in 196 candidates / 16 s, star-5 in 1. Discarding the lever costs nothing.

> ⚠ **THE DOG HAS NO VALID TARGET YET.** Its space is characterised (5 swapped
> pairs, 21 preserved, 9 σ-fixed) and its SYMFIX is refuted `taco-taco
> (10,12)x(12,19)`, but no symmetric-and-foldable assignment has been exhibited.
> **The honesty constraint therefore reads exactly as before:** the dog's status
> goes in the first line of any PR or summary, and it is a goal, not a gate.

**2. The FOG cannot reach it.** The post-cut FOG for quadruped and bird admits
**exactly ONE linear extension** (276/276 facet pairs comparable); insect and
dog sample hundreds of distinct extensions that all reconstruct a byte-identical
`edges_assignment`. Corpus-wide, **225/225 M/V-bearing creases have comparable
facet pairs** — every label is forced. No tie-break rule of any kind, under any
iteration order, can move one M/V label on any target.

**3. Symmetric cutting makes the metric green and the paper unfoldable.**
Measured two independent ways — the agents' engine-level symmetric cut, and my
own direct label flip on the `.fold`. Both drive `mv_swapped` 2/2/6/10 → 0 and
`symmetric` → True on all four targets, and both are then REFUTED by
`layer_order`: quadruped and bird `taco-taco (13,15)x(15,22)` — **the offending
mirror pair itself** — dog `(10,12)x(12,19)`. **STOCK passes on all 8 subjects**,
so the oracle discriminates and this is not a saturated veto.
`scratchpad/own/own_phys.py`.

**★★★ WHY THE STOP IS STRUCTURAL, not a search limitation.** The FOG *encodes
the physical layer constraints*. Deleting links until the answer comes out
symmetric is **discarding physics**, which is precisely how you get paper that
cannot fold — and it is exactly what the taco-taco refutations are reporting.
**Symmetry was never a free parameter of that graph.** So the stop is not "we
could not reach it"; it is **"this was never the site."**

This also closes the earlier (A)-vs-(B) fork cleanly. (A) was preferred because
*every engine output is foldable by construction*. That premise is now
falsified in the only place it mattered: **the engine's symmetric outputs are
not foldable.** The guarantee only ever covered what the engine actually
produces, and it cannot produce the target. The original brief's site call
(`mv_repair`, pure Python) was right **by accident** — the reason given for it
was false, and the reason it is true is one neither session had.

⇒ **Row 3's ACTION (stop) is right. Its REASON and REMEDY are both wrong.**
The FOG is *perfectly σ-antisymmetric before the cut* (0 violations on
quadruped/bird/insect/star-5) — but the pre-cut graph is **cyclic on all 11
subjects**, so it cannot be left uncut. The whole defect is pinned on one
unavoidable symmetry-breaking deletion, and no bounded amount of extra deletion
reaches a valid target.

> ⚠ **`mv_swapped == 0` is a VACUOUS acceptance criterion.** It is exactly what
> the invalid patterns above score. Never gate on it alone. `quad` also passes
> it today for the wrong reason (its offending pairs are `fHINGE↔uHINGE`, and a
> `uHINGE` is FLAT *before* `mOrder` is ever read).

### 0.1 ★ THE MECHANISM, established (not a hypothesis §A tests)

> **The M/V assignment is mirror-perfect ⟺ the crease where TreeMaker CUTS the
> facet-ordering cycle is σ-FIXED.** 192 evaluations, zero exceptions.

The **controlled** test, which is what promotes this from correlational: `star-4`
re-rooted at 1–4 gives one CP with one cut crease (`v3–v0`, RIDGE). Vary nothing
but which σ you read it against — at 45° the cut is not σ-fixed **and** the
pattern is asymmetric (0/4); at 135° the *same crease* is σ-fixed **and** the
*same assignment* is mirror-perfect (0/0). Packing basin, label convention and
geometry are all held fixed by construction, so none of them can be the cause.

### 0.2 ✅ The frozen baseline is SOUND — axis sweep, 2026-08-04

All five committed subjects re-served and read at {0°, 45°, 90°, 135°}
(measurement, not a re-bless; `--out` never passed). **45° dominates on every
subject** — cardinality 25/145, 4/16, 8/31, 40/89, 45/45 versus **0** at every
other axis (fish: 2 at 135°). All five 45° residuals reproduce the committed
values exactly. `cp_symmetric False` is a real reading, not an axis artifact.
The D4 false-negative risk is confined to **re-rooted variants**, constraining
any future root-search policy rather than the baseline. Full table:
`../COORDINATION.md` §4.2. Raw: `scratchpad/axis_sweep_committed.json`.

---

## 1. The goal

The trigger was *"the dog I generated looks a little asymmetric"* — about a model
that **compiled successfully**. Pack rate is not the target. Done means: a tree
the user asked to be bilaterally symmetric compiles to a mirror-symmetric crease
pattern, and the scorecard proves it with a graded number.

Goal 2 is **two independent defects**:

* **G2a — leaf placement.** Geometry does not mirror (`is_bijection` False).
  Unpaired leaves land off the axis. Owned by **S3**.
* **G2b — M/V assignment.** Geometry mirrors *exactly*; mirror-image creases
  carry opposite fold directions. Owned by **S2**. **This is the dog's defect.**

---

## 2. Measured facts. Do not re-derive; do flag any contradiction.

### 2.1 The dog reading — CONFIRMED, three independent routes (2026-08-04)

The scorecard `_meta`'s uncommitted `dog_row` reproduced **byte-identically on
all 21 fields**: `hull_coverage 0.527, cp_symmetric false, cp_mirror_residual
0.0, cp_mv_broken 10`. Routes: (a) the documented `IDE_BENCH_DOG=1 … --baseline`
command, (b) an independent extraction→serve→verdict script, (c) a third
instrumented serve. **No committed subject moved** (`no axis moved` on all five).

The dog is a **pure G2b defect**: 50 vertices, 99 edges, exact vertex-and-edge
bijection, residual exactly `0.0`, `mv_swapped 10`, `mv_mismatched 0`.

### 2.2 The offender counts are DOUBLE COUNTS

A **self-mapped** crease can never be an offender — `cp_mirror.mirror_verdict`
looks up its own label in `have` and scores it `preserved`. So every offender is
one half of a mirror **pair**, counted once from each side.

| pattern | verts | edges | `mv_swapped` | real crease **pairs** | defect components |
|---|---|---|---|---|---|
| TEMPLATE_QUADRUPED | 27 | 50 | 2 | **1** | 1 |
| TEMPLATE_BIRD | 27 | 50 | 2 | **1** | 1 |
| insect | 28 | 53 | 6 | **3** | 1 |
| dog | 50 | 99 | 10 | **5** | 2 |
| star-4+pairs | 9 | 16 | 0 | — | — (control) |
| HSHAPE | 12 | 21 | 0 | — | — (control) |

Every defect component contains an **on-axis, σ-fixed vertex**. Across the four
defective patterns, counting incident mirror-PAIRS at σ-fixed vertices: **27
agree, 5 disagree** — the engine gets 27 of 32 on-axis choices right.

TEMPLATE_QUADRUPED's is v15 = `(0.503885, 0.503885)`, degree 4, M=1 V=3, two
self-mapped creases (both V), disagreeing pair `{13,15}='V'` / `{15,22}='M'`.

### 2.3 ⚠ `mv_repair` is the WRONG SITE — this corrects the original brief

The brief said *"S2 — G2b, in mv_repair. Pure Python. Zero contact with the C++
file"* and *"The M/V solver is OURS (mv_repair, a T-join solver), not Lang's."*
**Both are false.** Measured with a call spy plus two live positive controls
(fish, quadruped mesh — where it DOES run):

```
TEMPLATE_QUADRUPED serve -> _repair_and_annotate: 0, solve_mv_repair: 0
                            served cp_audit: clean=true, summed=0
```

`mv_repair` is a **defect reducer** gated on `cp_audit`-dirty folds. These
swapped creases appear precisely on folds that pack **clean**, so it is
short-circuited at the attempt-0 return (TEMPLATE_QUADRUPED, bird, humanoid) or
at `if meta["clean"] is False` (insect, dog). Measured 6/6.
**The swapped assignments are raw TreeMaker output.**

### 2.4 Post-hoc relabelling is expensive — and that is why it is rejected

Own measurement on TEMPLATE_QUADRUPED (30 M/V creases → 8 self-mapped, 11 mirror
pairs, exactly 1 disagreeing), searched by increasing weight:

| target | min weight | audit state |
|---|---|---|
| symmetric + Maekawa-clean | **5** | `arrangement: 2` — still dirty |
| symmetric + fully `cp_audit`-clean | **11** of 30 M/V labels (37%) | clean |

Corroborated independently at 11. Subagent-measured on the others: insect **9**,
dog **14**; dog's exhaustive search cost **101.9 s** against a 5 s
`REPAIR_DEADLINE_S`.

⚠ **What this number does and does not argue.** It prices *post-hoc repair*,
where each flip breaks Maekawa at its far endpoint and the correction cascades
through an already-committed assignment. It is evidence **against approach (B)**.
It says nothing about the difficulty of making the compiler choose differently —
at source there is no cascade, because the engine recomputes every downstream
choice consistently. Do not cite 11 as a cost estimate for S2.

### 2.5 `cp_audit` IS mirror-equivariant

Reflecting the geometry while keeping the labels reproduces the audit verdict
exactly (`clean: true`, maekawa/kawasaki/arrangement/closure_bad_edges all 0),
differing only in `closure_max_error` at the ~1e-17 level — float noise from
`cos/sin(45°)`. **So the extra violations a symmetrizing relabel provokes are
real geometric failures, not artifacts of a biased auditor.** That escape hatch
is closed; do not reopen it.

### 2.6 The defect is deterministic

Identical output under: reversing the declared-pair list; swapping the members
inside each declared pair. Under node-order reversal it reappears with the same
structure at relabelled vertices (offenders move `13,15/22,15` → `17,19/25,19`,
same scale `0.667979`, same counts).

### 2.7 The exported `.fold` discards the facet ordering

Frame keys are exactly: `vertices_coords`, `edges_vertices`, `edges_assignment`,
`frame_title`, `frame_attributes`, `frame_classes`, `file_classes`,
`file_creator`, `file_spec`. **No `faces_vertices`, no `faceOrders`.**

Lang & Demaine (*Facet Ordering and Crease Assignment in Uniaxial Bases*,
Origami-4/OSME 2006) state the assignment is **derived** from a facet ordering
and call *"the primacy of the ordering relationship, rather than the crease
assignment, ... the fundamental mathematical description."* So the artifact
throws away the primary object and keeps the shadow. **Named as a candidate
follow-on slice (FOLD supports `faceOrders`); explicitly NOT part of S2.**

### 2.8 ★★★ THE MECHANISM — perfect separator over 58 patterns

`tmCrease::CalcFold` (`treemaker/Source/tmModel/tmTreeClasses/tmCrease.cpp`) is
the **sole writer** of the M/V label; `ExportFold` in `TreemakerWrapper.cpp` is
the sole reader. Its four branches collapse algebraically to one rule:

> **M ⟺ order(COLOR_UP facet) > order(WHITE_UP facet)**

Verified `bad=0` on every non-border crease of every pattern compiled. The
`mFwdFacet`/`mBkdFacet` distinction cancels, so crease construction order cannot
matter. Facet **colour** is *perfectly anti-equivariant* under the mirror (24/24,
26/26, 50/50 — no exceptions), because `CalcColor` flips at every folded crease
and every self-mapped on-axis crease measured is folded. **Both
orientation-dependent halves flip together and cancel. The defect is entirely in
the facet ORDER.**

`tmPoly::CalcLocalFacetOrder` builds a directed **cycle** per polygon. Lang's own
comment: *"Breaking the axial loop at any local root vertex gives a valid facet
ordering graph"* — **the cut is an acknowledged free choice.**
`tmFacet::CalcOrder` numbers the cut path 0…n−1, so facet 0 and facet n−1 are the
two ends of the removed link.

> **THE PREDICATE: the M/V assignment is mirror-perfect ⟺ the CUT CREASE is
> σ-FIXED (both endpoints on the axis).**
>
> cut σ-fixed: **16 patterns → 16 symmetric.**
> cut not σ-fixed: **38 patterns → 0 symmetric.** Zero exceptions.
> (4 further patterns: cut not identifiable.)

Clean patterns achieve a *perfect* global order reversal `ord(σF) = n−1−ord(F)`;
defective ones achieve **0/24** global reversal while still getting 32 of 34
pairwise comparisons right — a DAG whose forced comparisons are symmetric but
whose linear extension is not.

On TEMPLATE_QUADRUPED the cut crease is `v13–v15` (facets 23, 0) and its mirror
`v22–v15` (facets 11, 12): **those two creases ARE the single offending pair.**

**Two cut sites, mutually exclusive per compile**, both in `tmTree_FacetOrder.cpp`:

| root node kind | cut crease kind | count | site |
|---|---|---|---|
| BRANCH | fHINGE | 37 | `tmRootNetwork::BreakOneLink` (`mCC1.front()` / `mCC2ST1.front()`) |
| LEAF | RIDGE | 17 | `tmRootNetwork::ConnectFacetGraph`, the `mCC0.size() == 1` branch |

**Interventional, both directions.** `tmTree::GetRootNode` returns
`mNodes.front()` — **TreeMaker's root is the first entry of our JSON node list**.
Re-rooting TEMPLATE_QUADRUPED at node 8 (edges and lengths asserted preserved)
moves the cut onto the axis → `symmetric True`, `mv_swapped 0`, still 27/50.
Re-rooting `star-4+pairs` and `HSHAPE` breaks them the other way; on `star-4` the
re-rooted CP is geometrically identical to 1e-6, differing **only** in assignment.

### 2.9 ⚠ THE GATE FRAMING IS FALSIFIED — corrects the plan of record

The plan said *"gate on `mSymPairs` non-empty, or every asymmetric golden moves."*
Measured:

* **`mSymPairs` does not exist in the engine.** It is a `HeadlessTreemaker`
  member in `TreemakerWrapper.cpp`, used only for pair projection. Zero hits in
  vendored source. Every file on the assignment chain — `tmTree_FacetOrder.cpp`,
  `tmCrease.cpp`, `tmFacet.cpp`, `tmVertex.cpp`, `tmPoly.cpp`,
  `tmTreeCleaner.cpp` — contains **zero** symmetry tokens. **General path.**
* **`HasSymmetry()` is neither sound nor complete** — 26 corpus cases, **5 false
  negatives and 5 false positives**:

  | zero declared pairs, IS a mirror bijection, IS defective | swapped | mismatched |
  |---|---|---|
  | **star-4** (committed golden) | 2 | 0 |
  | star-5 / star-6 / two-level-tree | 2 each | 0 |
  | **quad** (committed golden) | 0 | **6** |

* **Declared pairs are not the operative variable.** `star-4` vs `star-4-sym`
  have byte-identical node lists; the pairs change the **packing** (different
  coords, different edges), not the assignment. `star-6` goes from 2 swapped to
  **6** when pairs are declared.

⇒ Acceptance criterion *"no golden moves for any tree without declared pairs"*
**cannot hold** — two committed goldens have no declared pairs and *should* move.
The gate must be a **local geometric predicate at the choice point** ("are these
two options genuinely tied and mirror images of each other?"), which needs
**zero plumbing**: `tmPart::GetTree()` is public and every arbitrary-choice site
already holds a `tmPart`-derived object. **Zero function signatures change.**

**ODR status refined** (corrects memory `treemaker-odr-tmtree-header`): measured
with `clang++ -E -H` under build.sh's exact flags — **0 of 53 TUs resolve the
stale `Source/tmTree.h`**; all 10 direct includes live inside `tmTreeClasses/`,
where the including file's own directory wins. The hazard is **dormant**, not
absent: `-I"${TM_SRC}"` is listed first, so any new `.cpp` **outside**
`tmTreeClasses/` that writes `#include "tmTree.h"` gets the stale copy, and the
shared `_TMTREE_H_` guard then silently shifts `mHasSymmetry`/`mSymLoc`/
`mSymAngle` by 8 bytes. Since the recommended fix needs **zero** `tmTree`
changes, this need not be touched — but any new probe TU outside
`tmTreeClasses/` must include `"tmModel.h"` or `"tmTreeClasses/tmTree.h"`.

### 2.10 The oracle: NOT unique, so criterion is set MEMBERSHIP

⚠ **The counts below are PER-ROOT and were all taken at the one root the
project ever emitted.** They reproduce on the folds they name. They are not
properties of the *subject* — `insect` roots 6 and 10 are the same geometry with
**12 vs 24** targets (§10.1). Quote a row here only together with its root.

Exhaustive, validated two independent ways (full real-`cp_audit` enumeration of
the entire symmetric space returned the identical set):

| pattern | orbits | symmetric space | fully `cp_audit`-clean | min weight | # at min |
|---|---|---|---|---|---|
| TEMPLATE_QUADRUPED | 19 | 524 288 | **8** | 11 | 2 |
| TEMPLATE_BIRD | 19 | 524 288 | **8** | 11 | 2 |
| insect | 18 | 262 144 | **36** | 4 | 1 |
| dog | 35 | 34 359 738 368 | **144** | 14 | 2 |
| star-4+pairs *(already clean)* | 5 | 32 | **12** | 0 | 1 |
| HSHAPE *(already clean)* | 6 | 64 | **4** | 0 | 1 |

The two patterns the engine already gets **right** still have 12 and 4 solutions
— so non-uniqueness is not an artefact of the broken cases.

⇒ **The criterion is "the engine's answer ∈ the solution set", never equality.**
And **min weight is measured from the current buggy labels**, so it stops meaning
anything once the fix lands: the solution *set* is label-independent (proven — 
rebuilding the oracle from a different member of its own set returns the identical
set), the min-weight *subset* is not.

Key structural facts that make the oracle cheap (~0.4 ms for the quadruped,
~20 ms for the dog, both CI-affordable): a symmetric assignment carries one label
per σ-**orbit**; and `cp_audit.clean` **factorises per interior vertex** under
M↔V relabelling, because closure and Kawasaki are provably invariant under any
M↔V flip (`flat_fold.edge_transform` reflects for both) — measured bit-unmoved
across 160 random relabels.

**What the oracle CANNOT certify** (must not be over-claimed): `cp_audit` has no
global check with discriminating power over relabels — the entire certification
is **local**, and local flat-foldability does not imply global. It never sees
layer order, and it never sees the tree. **Nothing in it says the pattern folds
to the intended uniaxial base.**

### 2.11 Two live bugs found in passing — SEPARATE TICKETS, filed 2026-08-04

1. **Unordered facets emitting M/V from `SIZE_MAX`.** `mOrder` stays
   `size_t(-1)` and `CalcFold` compares the sentinel. TEMPLATE_INSECT **131 of
   145** creases, star-8+pairs 24/82, quadruped v128/p0.30 (a stub rescue)
   **243 of 308**. Passes `HasFullCP()` and ships. ⚠ **May be UPSTREAM of S2**,
   not parallel: the cut predicate locates the cut as "the crease separating
   facet 0 from facet n−1", which presupposes `CalcOrder` numbered the whole
   path. Under measurement (§6.4).
2. **`mv_mismatched` (folded ↔ flat)** — a different chain: crease *kind* via
   `CalcBend`, driven by vertex depths from the root. QUAD's 6. Not S2.

---

## 3. The approach decision (settled 2026-08-04)

**(A) Fix the choice at source in the vendored TreeMaker C++.** Targets are
`mcp_harness/treemaker/Source/tmModel/tmTreeClasses/` — `tmCrease.cpp`,
`tmFacet.cpp`, `tmTree_FacetOrder.cpp` — **not** `mcp_harness/TreemakerWrapper.cpp`,
so this does **not** collide with the serial C++ schedule in COORDINATION.md §2.

**(B) Post-hoc symmetric relabel in Python — REJECTED.** Three reasons:

1. **It ships a claim it cannot support.** `cp_audit` checks local
   flat-foldability necessary conditions plus arrangement. It does **not** check
   *"folds to the intended base."* A crease pattern admits many valid flat-fold
   assignments and most are not the target uniaxial base. With 37% of the labels
   ours, (B) would assert foldability-to-target on an instrument blind to the
   failure that matters — the same error as the three metrics that scored a
   lopsided pattern `0.000000`, relocated. The repo has a standing rule against
   exactly this.
2. **The 11-of-30 distance says the symmetric answer is not a nearby
   perturbation** of the engine's, but a structurally different pattern.
3. **Its "no C++ build" advantage is nearly worthless** — Goal 2's S3 needs a
   build regardless, and the targets do not collide with the serial schedule.

**(C) Do both and gate on agreement — REJECTED.** Costs (A) in full and adds a
second implementation to maintain.

---

## 4. Slice map

⚠ **SUPERSEDED — every "state" cell below is 2026-08-05.** S2 was closed by
§0.3; S3 was REFUTED before dispatch (its wins were the node-order lever, not
the pin); what actually shipped is S2′a (#93), S2′b (#97/#119), root-rank
(#107) and the ranking-key fix (#108). The `faceOrders` export row is the one
line still live, and it is still unscoped. See §10.

| slice | what | site | depends on | state |
|---|---|---|---|---|
| S1 | the CP-mirror metric | `cp_mirror.py` | — | **SHIPPED** at 1c9abe0 |
| **S2** | **G2b — M/V mirror symmetry at source** | **vendored `tmModel`** | nothing | recon in flight |
| S3 | G2a — bind `SetToSymmetryLine`, `axis_nodes` on the tree contract | `TreemakerWrapper.cpp` + plumbing | **Goal 1's S4a** | blocked |
| — | export `faces_vertices` / `faceOrders` | wrapper | — | candidate follow-on, not scoped |

S2 stays first: it is the only slice in either goal that touches the dog, and
the dog is the complaint that started this.

---

## 5. S2 acceptance criteria (agreed, not yet spec'd)

⚠ **SUPERSEDED — criterion 1 is now known VACUOUS as written.** It gates on
`mv_swapped == 0` alone, and §10.3.1 exhibits **six** live packs that satisfy it
while not being symmetric. The correct predicate is `cp_mirror.py:326-329`'s
conjunction with `mv_mismatched`. Criteria 2–4 stand. ⚠ Criterion 1's *subject
list* is also stale: `TEMPLATE_QUADRUPED` reached `mv_swapped == 0` at
**identical scale** via root selection in #118 — the RED pin
`tests/test_cp_mirror_serve.py:54` was inverted to
`test_template_quadruped_is_now_GREEN_on_mv_via_root_selection` — and **it was
not S2 that did it.**

1. `mirror_verdict(...)["mv_swapped"] == 0` on all four G2b patterns —
   TEMPLATE_QUADRUPED, TEMPLATE_BIRD, insect, dog. **This is the GOAL, not the
   ship gate** — see §5.1 on the dog.
2. `star-4 + pairs` and `HSHAPE` stay at `mv_swapped == 0` / `symmetric True`.
3. ⚠ **SUPERSEDED — the original wording is falsified (§2.9).** It read *"no
   golden moves for any tree without declared pairs"*; `star-4` and `quad` have
   zero declared pairs, ARE mirror bijections, and DO carry the defect, so they
   must move. Replacement: **the blast radius is bounded by a local geometric
   predicate, and every golden that moves is attributed.** Golden movement is
   its own attribution event — same discipline as the frozen scorecard, separate
   ledger.
4. **The engine's answer ∈ the oracle's solution set** — never equality (§2.10).

### 5.1 The dog: goal, not gate — and the honesty constraint is STRUCTURAL

Decision 2026-08-04: **(C) disambiguate first, then (A) ship on what is
reached.** Blocking S2 on the dog, when the dog may be unreachable for reasons
that are not S2's, means the mechanism never lands *and* the dog stays broken —
strictly worse. But the constraint that made blocking tempting is built in
rather than promised:

* **S2's PR title and summary state the dog's status in the first line.** If the
  dog is open, *"symmetry fixed"* is not an available phrasing.
* **The follow-on slice opens WITH S2, not after it.**
* **Criterion 1 stands as the goal, not the ship gate.**

This encodes the failure this project has recorded twice: reporting a scorecard
win as the fix the user asked for. Three green templates the user never
mentioned is a scorecard win, not a fix.

⚠ `tests/test_cp_mirror_serve.py::test_template_quadruped_is_pinned_red_on_mv_and_is_S2s_target`
is an **exact-equality RED pin** (`mv_swapped == 2`, `symmetric is False`, plus a
set-equality on the offender edges `{frozenset((13,15)), frozenset((22,15))}`).
S2 **must edit it** — an acceptance criterion worded *"all existing tests stay
green"* is unsatisfiable. It has to be *"this test is inverted to its green form,
and the two controls stay green untouched."* When inverting, keep equivalent
strength: pair `mv_swapped == 0` with `mv_preserved == 50` so a "fix" that
achieves symmetry by deleting creases cannot pass.

---

## 6. Open items carried into the spec

⚠ **SUPERSEDED — items 1–4 and 6 are all ANSWERED; item 5 turned out to be the
whole goal.** Item 5 asked *"is the dog reachable by RE-ROOTING?"*, noted that
the root is `mNodes.front()`, and reasoned correctly that *"every re-rooted
compile is a genuine TreeMaker output, so foldability is guaranteed by
construction"* — the exact property whose absence killed post-hoc relabelling.
**It was filed as an open question about the dog and never run on any subject.**
Running it on the other five is what closed this goal (§10.1), and **it still
has not been run on the dog** (§10.5 item 4). The live list is §10.5.

1. **Recon before implementing** (in flight, workflow `wf_a2ebb941-00a`). Is the
   tie-break site reachable only under declared symmetry, or on the general
   path? If general, the fix must be gated on symmetry-declared or every
   asymmetric golden moves. Also: is "27 right / 5 wrong" **one** arbitrary
   choice going both ways, or **several** distinct sites?
2. **The exhaustive search becomes the ORACLE, not the fix.** 101.9 s vs a 5 s
   `REPAIR_DEADLINE_S` rules it out of production; under (A) it does not need to
   be production. It is the offline instrument that says what symmetric-and-clean
   looks like, so we can verify the engine now produces it. Open question under
   recon: is that answer **unique**? If not, the criterion is "the engine's
   answer is in the oracle's solution set", not "equals the oracle's answer".
   Reference implementation: `scratchpad/planner_verify2.py`.
3. **`faces`/`faceOrders` export** — candidate follow-on slice, named in the
   spec, not folded into S2.
4. **Is the SIZE_MAX defect UPSTREAM of S2?** (measurement in flight, workflow
   `wf_3bff72dd-c30`). The cut predicate locates the cut as "the crease
   separating facet 0 from facet n−1", which presupposes complete numbering.
   Nobody has counted unordered facets on the four criterion-4a patterns. If the
   dog has them, that is a **single explanation for two symptoms** — its
   unlocatable cut *and* its 0-of-144 layer-inconsistent oracle solutions —
   rather than evidence of a packing wall.
5. **Is the dog reachable by RE-ROOTING?** (in flight, same workflow). The root
   is `mNodes.front()`, i.e. the first entry of the JSON node list we control
   from Python. Every re-rooted compile is a genuine TreeMaker output, so
   **foldability is guaranteed by construction** — which is exactly the property
   whose absence killed post-hoc relabelling. A relabel asks us to vouch for a
   folded state; a re-root asks the compiler for a different one. This is a
   better disambiguator than adjudicating `layer_order`, which has a recorded
   defect (shared-edge clipping fabricates silent holes) and is being asked
   about the dog's larger folded state — the regime where it would fail.
   ⚠ Two caveats: **node list order flips packability** (recorded), so every
   candidate root needs a pack check; and a sweep measures the ceiling **for
   this lever**, not for the C++ fix, which can reach cuts no root selects.
6. **Experiment FOG-DUMP** — named by recon as the decisive <1 h experiment
   (rebuild allowed). Guard on `getenv("TM_DUMP_FOG")` and dump, from
   `tmTree_FacetOrder.cpp`: every facet's `mOrder`/`mColor`/centroid plus its
   `mHeadFacets`; which `BreakOneLink` branch fired and the chosen vertex's
   `mLoc` with `|x−y|`; `ConnectFacetGraph`'s `mCC0` unlink/skip choices; and
   the absorb loop's vertices. It answers the **single most decision-relevant
   unknown**: are the offending facet pairs FOG-**incomparable** (⇒ fix the
   linearization tie-break) or **comparable** (⇒ the graph itself must change)?
   ⚠ Recon also flagged a feasibility gap: at quadruped's cut vertex v15 the
   *only* two hinge creases are a mirror pair, so **no σ-fixed hinge is
   available there to cut** — the fix may have to be "cut symmetrically" (break
   both members, or re-link compensatingly), not "cut at an axis crease".

---

## 7. Environment and traps

* Python `mcp_harness/.venv/bin/python` (3.14.3). Tests:
  `cd mcp_harness && PYTHONPATH=.:tests <python> -m pytest tests/ --timeout=420`.
  A bare `make test` NEVER terminates here. ~14 min; looks stalled early at
  near-zero CPU — **do not kill it**. Baseline at 1c9abe0: **2241 passed, 11
  skipped, 0 failed**.
* A worktree needs THREE gitignored build artifacts or every verdict fakes
  FAIL-LINT: the engine `.so` (`cd mcp_harness && ./build.sh`), the oriedita jar,
  and `OrieditaValidator.class` (`./build_linter.sh`). **Build the `.so` IN
  PLACE** — a borrowed one from main inflates failures to ~27.
* A bare `HeadlessTreemaker` compile is **NOT** the serve path. Use
  `server.draft_and_compile_full_base`, and put any script that calls it under
  `if __name__ == "__main__":`. This has bitten the project five times.
* **QUAD has two packing basins and they change the SYMMETRY VERDICT**, not just
  coordinates: macOS reaches an exact 13/13 bijection, Linux reaches a basin
  where `is_bijection` is False. Any new QUAD test needs the accommodation
  `goldens/basins/quad.json` already has. QUAD's defect is `mv_mismatched 6`
  (M/V↔F), a *different and harder* class than the pure M↔V swaps S2 targets —
  do not scope it into S2 without saying so.
* **FISH root 4 has two packings too** (U19, 2026-08-16) — the same class as
  QUAD above, found on the `mesh_validation_trees` fish. macOS/Accelerate and
  Linux/OpenBLAS agree on the admissible roots, the winning index, the FULL
  `rank_key` of all 8 arms, `oracles_ok` on all 8, `design_scale` (0.797133),
  the topology and the whole mirror verdict — and the WINNER's residual differs
  by 2e-3 (0.237240 vs 0.239303) while the other seven arms agree to ~1e-8.
  `test_cp_mirror_serve.py` names both under `alt_residuals`, guarded so a
  second residual may only be named where `is_bijection` is False (there the
  residual is the GAMEABLE partial-match statistic and pins nothing).
* **`layer_order`'s interior epsilon was below its own cross-platform noise
  floor, and it FABRICATED constraints on Linux** (U19; the third instance of
  the epsilon class after `free_paper._TOL` and `flex_extension.QNORM_FLOOR`,
  which project memory predicted). `_strictly_inside` compared a CROSS PRODUCT
  (an area) against the shared `GEOM_EPS = 1e-9`; measured on
  `template-quadruped`'s root-8 winner, Linux emitted **91** taco-tortilla
  constraints where macOS emitted **64**. That inverts this module's stated
  UNDER-refute error direction and made `root_rank.oracles_ok` refuse a winner
  the ranking had chosen IDENTICALLY on both platforms. Split out as
  `INTERIOR_EPS = 1e-8` and mutation-proved both ways.
* ⚠ **THAT CONSTANT SHIPPED AS `1e-6` FIRST AND IT WAS WRONG — the lesson is
  worth more than the fix.** Its "258,000x empty gap" (noise 3.238e-09, signal
  floor 8.365e-04) came from ONE base, and that base loses no constraint at any
  threshold up to 1e-6, which is precisely why its gap looked empty.
  `probe_interior_window.py` re-measured across four bases: the far denser
  `COMPOSED_NODES` pool carries constraints continuously from ~1e-9 upward, and
  at 1e-6 `root_rank.oracles_ok` flips refuse → **accept** on 5 of 6 arms that a
  NAMED contradiction had refused — this gate going vacuous on the platform that
  never had the bug. The real window is **one order wide** (3.238e-09 noise
  below, a real 3.21e-08 constraint above); 1e-8 is its centre. **A single base
  cannot establish a signal floor.**
* ⚠ **The `INTERIOR_EPS` fix does NOT buy determinism, and must not be cited as
  if it did.** The number of triples `_spanning` even CONSIDERS still differs by
  platform (`template-quadruped` arm0 316 vs 308, `template-bird` arm2 700 vs
  688, COMPOSED arm1 2775 vs 2215) — that is `pairs`/`_cells`/`_clip_seg`,
  UPSTREAM of the interior test, driven by the packer's own ~1e-9 divergence. A
  scale-RELATIVE interior predicate (margin against |edge| × diameter rather
  than an absolute area) is the principled follow-up; it needs its own
  corpus-wide validation and was deliberately not attempted here.
* ⚠ **`AREA_EPS = 1e-9` IS THE SAME SHAPE AND IS NOT YET FIXED.** Measured
  (U19) minimum arrangement-cell areas: `star-4-sym` 1.75e-09, `hshape`
  1.18e-09, `star-6` 1.07e-09 — **under 2x margin** against the constant that
  drops them, versus the same ~1e-9 packing noise. Dropping a cell removes
  `pairs` membership and therefore removes constraints, which
  `mv_symmetrize._AuditOracle` propagates. With `IDE_MV_SYMMETRIZE=1` and the
  `INTERIOR_EPS` fix in place, 4 of 6 subjects' symmetrized M/V agree across
  platforms and **`star-4-sym` and `template-bird` still differ** — this is the
  outstanding suspect for that, and it is deliberately NOT widened blind: sizing
  it needs the same noise-vs-signal separation study `INTERIOR_EPS` got.
* **ODR hazard:** two vendored `tmTree.h` share the guard `_TMTREE_H_` with
  different member order. Live risk for any S2 change that adds a member or
  changes a signature in `tmTree`. Under recon.
* Verify C++ on Linux in the `ci-amd64-run` container **before** merge, not
  push-and-wait. Check host CPU load first.
* `server.py` does not import `pair_reconcile`, so agent-authored trees bypass it
  entirely; `tree_contract.check` validates pair *structure* but has **no
  pair-geometry check**. Scope decision owed in the spec (S3-adjacent).

---

## 8. The frozen scorecard

✅ **THE FREEZE IS LIFTED (2026-08-16) AND THE ONE COMBINED RE-BLESS HAS
HAPPENED — exactly as this section specified.** `scorecard_baseline.jsonl` now
measures `1c9abe0..153f9c7` and carries a per-cell attribution table in its own
`_meta`: **36 cells, 6 owning slices, 31 bisected + 5 structural, zero
unattributed**, with **four zero-row segments verified rather than asserted**.
Goal 2's own contributions are attributed there as `#107 root-rank` (13 cells),
`#118 leaf-root` (3), `#119 symmetrizer-on` (3) and `#125 early-exit` (2).
**Still binding after the freeze: never pass `--out`, and never re-bless
without the attribution table.**

`mcp_harness/fixtures/scorecard_baseline.jsonl` was **FROZEN at 1c9abe0** for the
duration of both goals. See `../COORDINATION.md` §1 for the full protocol. Never
pass `--out`. One combined re-bless at the very end of both goals.

⚠ **SUPERSEDED, and this is one of the goal's real wins — see §10.0.** The
paragraph below correctly diagnosed a hard limit (`cp_mv_broken` measurable on
one subject only) and that limit is **gone**: four of five subjects now carry an
exact mirror bijection, so three that could not report the M/V defect at all now
do. The freeze protocol itself is unchanged and still binding — **never pass
`--out`; one combined re-bless at the very end of both goals**, owned by a
separate unit, not by this record.

⚠ **S2's scorecard-visible effect is ONE row.** `cp_mv_broken` is `None`
wherever the bijection fails, which is four of five committed subjects. Only
`insect` (currently 6) is measurable today. TEMPLATE_QUADRUPED, TEMPLATE_BIRD and
the dog are **not** committed scorecard subjects, and
`test_the_committed_scorecard_baseline_is_read_by_something` pins the subject set
as an exact equality — so S2 cannot add a dog row to demonstrate itself.

---

## 9. Log

| date | entry |
|---|---|
| 2026-08-04 | Session opened. Read S1 spec, frozen `_meta`, handoff, memory. |
| 2026-08-04 | Dog reading verified 3× — holds exactly. Offender counts shown to be double counts of crease PAIRS. |
| 2026-08-04 | `mv_repair` measured to never run on any G2b subject → the briefed S2 site is wrong. |
| 2026-08-04 | Post-hoc relabel priced at 11/30 labels on the smallest case → approach (B) rejected; **(A) chosen**. |
| 2026-08-04 | `COORDINATION.md` committed standalone as `74d3483`; needs to land on `main`. |
| 2026-08-04 | Source recon dispatched (`wf_a2ebb941-00a`): assignment trace, gating surface, one-site-or-many, blast radius, oracle uniqueness. |
| 2026-08-05 | **§A SHIPPED** as `822497b` (env-guarded FOG dump, +305/−5, one file). Routed to spec §4.2 row 3 = STOP. |
| 2026-08-05 | §A independently verified (13 agents + own measurements). Every number reproduces; **the remedy is refuted**. See §0.3. |
| 2026-08-05 | Measured: a valid symmetric target EXISTS (quadruped = offending flip + one σ-fixed crease) but is unreachable from the FOG. **Approach (A) closed.** |

---

# 10. ★★★ THE CLOSING RECORD — 2026-08-15

## 10.0 What closed

The charter, verbatim from §1 above and unchanged: *the trigger was "the dog I
generated looks a little asymmetric" — about a model that **compiled
successfully**. Pack rate is not the target. Done means: a tree the user asked
to be bilaterally symmetric compiles to a mirror-symmetric crease pattern, and
the scorecard proves it with a graded number.*

**Goal 2 closes at 3 of 5 measured symmetric — `humanoid`, `insect` and
`quadruped` ‡ — from 0 of 5 at goal start.**

> ⚠ **SUPERSEDED BY MEASUREMENT, 2026-08-17 (U21): it is 4 of 5. `bird` is
> mirror-symmetric.** This section's table was measured at `153f9c7`, which
> predates **#128** and **#129** — the two Linux-CI fixes that landed after the
> closing records were written. #129 collapsed `Pass` and `BENIGN` in
> `mv_symmetrize.serve_rank` (because U20 measured that which of the two a
> candidate gets is decided by its ninth decimal and *inverts* between macOS
> and Linux), and that collapse admits a conjunct-4 survivor the old filter
> rejected. On `bird` that survivor is symmetric:
>
> | cell | closing record (`153f9c7`) | 2026-08-17 | holds on |
> |---|---|---|---|
> | `bird` `cp_symmetric` | False | **True** | both platforms |
> | `bird` `cp_mv_broken` | 4 | **0** | both platforms |
> | `bird` `lint_class` | PASS | BENIGN | **macOS only** † |
> | `insect` `lint_class` | PASS | BENIGN | **macOS only** † |
>
> **Nothing else moved on any subject, on either platform.** The `lint_class`
> moves are the named price and not a foldability regression: `BENIGN` means
> `real == 0` (`lint_verdict.py:237` returns it exactly when no REAL defect
> exists), which is the basis on which #129 argued the two are the same claim.
>
> † ⚠ **AND THE PRICE IS PAID ON macOS ONLY — an earlier revision of this
> section stated it unqualified, and a reader took it for a portable cost.**
> Re-measured on both platforms by **U22** (PR #131, 2026-08-17): on
> linux/amd64 — *the platform CI runs on* — `bird` **already read BENIGN before
> #129 existed**, so no PASS was ever given up there and #129 is a no-op for
> both subjects' lint class. The PASS being priced against is a one-platform
> reading of the **same fold**: bird's two arms share `geometry_sha`,
> `design_scale` 1.515998 and `hull_coverage` 0.9848, and differ only in
> `edges_assignment`. `real == 0` on **all 18** ranked candidates, both arms,
> both platforms, `unlocated == 0` throughout. The single macOS violation is
> `ANGLES` at **v2 = (0.504707669, 0.504707669) — exactly on the 45° mirror
> axis** — whose Kawasaki residual our own re-audit measures at **exactly 0.0**,
> parity `|M−V| = 2` and arrangement both OK, and on which Oriedita's own
> closing line reads *"flat-foldable as-is. ACCEPT."*
>
> †† **`bird` and `insect` moved by DIFFERENT MECHANISMS. Do not read them as
> one story.** `bird` is an **admission**: pre-#129 every symmetric candidate
> was rejected by conjunct 4 and the raw asymmetric pack shipped, and the
> collapse let a symmetric one through. There is **no symmetric-AND-PASS bird
> candidate to prefer instead** — all 6 ranked candidates on both platforms read
> `cp_symmetric True`, `cp_mv_broken 0`, `lint_class BENIGN`, with
> `rejected_by_lint` empty — so bird's trade is **forced**, not chosen.
> `insect` is a **re-ranking**: already symmetric, already relabelled on both
> arms, and what changed is *which candidate wins* — on macOS from candidate 3
> (relabel weight 17, PASS) to candidate 0 (relabel weight 5, BENIGN). It
> gained no symmetry; it bought a **3.4× lighter relabel** and paid a PASS.
> ⚠ **That trade was never separately argued when #129 landed** — it was
> ratified after the fact (user ruling, 2026-08-17) on the evidence that
> insect's four macOS PASS candidates (weights 17/21/27/31) all read **BENIGN
> on Linux at byte-identical `assignment_sha`**, so restoring that PASS by
> ranking on the raw class would serve a **different `.fold` per platform** —
> precisely the defect `serve_rank` exists to remove.
>
> **BISECTED over four arms with the `.so` rebuilt at each** — #128 alone does
> not move these cells, and neither does current `main` (which had to be
> excluded on its merits: **#127** changes the mesh extractor that produces
> these very trees). The control is that arm `9f6e0d5` reproduces this table's
> values exactly, so the closing measurement is independently reproducible.
> Full per-cell attribution lives in `fixtures/scorecard_baseline.jsonl`'s own
> `_meta`, which is authoritative over this prose.
>
> **The section below is kept as written rather than restated**, per this
> document's supersede-never-delete rule: every number in it is true of
> `153f9c7`, and a reader tracing why `bird` was called a located negative
> needs the original reasoning intact. What changed is not the analysis — the
> ROOT is still the lever — but one downstream filter's tie-handling.
>
> ⚠ **`fish` remains the honest miss**, at 4 of 5 exactly as it was at 3 of 5.
> Nothing here reaches it: it has no vertex bijection on either arm, so its
> `cp_mirror_residual` is the partial-match statistic COORDINATION.md forbids
> reading as an improvement.

Measured on the real serve path (`server.draft_and_compile_full_base`) at
PR #120, `--out` never passed, against the frozen baseline `1c9abe0`; the
`quadruped` row re-measured at U6' (PR #125) on the same serve path:

| subject | `hull_coverage` | `design_scale` | `lint_class` | `cp_symmetric` | `cp_mv_broken` | `stub_flaps` |
|---|---|---|---|---|---|---|
| `bird` | 0.9848 | 1.515998 | PASS | False | 4 | 0 |
| `fish` | 0.9077 | 0.653249 | BENIGN | False | *null* — no bijection | 0 |
| `insect` | 0.8595 | 0.582125 | **PASS** | **True** | **0** | 0 |
| `quadruped` | 0.8797 | 0.724628 | BENIGN | **True** ‡ | **0** ‡ | 0 |
| `humanoid` | 0.6638 | 0.775554 | PASS | **True** | **0** | 0 |

> ‡ **RULED, AND MEASURED — the pending footnote is discharged.** This cell
> read `False` / `8` behind a *PENDING* marker while a sibling unit measured
> whether `mv_symmetrize.MAX_ORBITS` should rise to admit `quadruped`'s
> **45**-orbit search. **It rose, to 45 — but not for the reason the question
> assumed.**
>
> PR #124 costed the exhaustive search at **22.145 s** against a pre-registered
> 10 s bar and correctly declined. Its phase split then located the cost: the
> 2⁴⁵ DFS is **≤ 2 s** for 1,382,884 nodes, and ~17 s is spent gating all 288
> audit-clean points **so the survivors can be ranked**. `MAX_ORBITS` — a
> constant named and derived as a bound on *search size* — was rationing
> *validation*. U6' stops at the first point passing all four conjuncts:
> the same subject, the same bar, the same fold (`bf7dd0900c1a5587`),
> **1.336 s** median over 7 runs.
>
> **Exactly these two cells moved, as promised.** `hull_coverage` 0.8797,
> `design_scale` 0.724628, `lint_class` BENIGN and `stub_flaps` 0 are
> unchanged, and no other subject moved — `bird` and `fish` stand, `humanoid`
> and `insect` stay `True`. The relabel is 6 creases of 137, crease-count
> preserving, `cp_audit`-clean, `layer_order`-consistent, lint BENIGN → BENIGN,
> and `cp_symmetric` is `cp_mirror.py:326-329`'s conjunction
> (`mv_swapped == 0` **and** `mv_mismatched == 0`), never `mv_swapped` alone.
>
> ⚠ **`quadruped` is symmetric on a WEAKER guarantee than `humanoid` and
> `insect`, and the difference is worth carrying.** Those two are served the
> `rank_key` **best** of a fully enumerated candidate set. `quadruped` is
> served the **first valid candidate in enumeration order** — here they happen
> to coincide (verified against the exhaustive run: both
> `[50,54,80,88,104,118]`, weight 6), but that is a measured fact about this
> fold, not a property of the mode. On `mesh-humanoid__seeded_1` the two
> winners differ, 5 creases against 7. The serve therefore **ranks at or below
> `MAX_RANKED_ORBITS = 40` and early-exits only above it**, so no fold that is
> ranked today lost its ranking to this change.
>
> §10.2's disposition changes from *budget-bounded* to **solved, at
> first-valid strength**.

### The graded number the charter asked for — where it actually moved

`cp_symmetric` / `cp_mirror_residual` / `cp_mv_broken` are Goal 2's own
scorecard columns. Their movement against the frozen baseline:

| subject | `cp_symmetric` | `cp_mirror_residual` | `cp_mv_broken` |
|---|---|---|---|
| `bird` | False → False | 0.053492 → **0.0** | *null* → **4** |
| `fish` | False → False | 0.121893 (unmoved) | *null* → *null* |
| `insect` | **False → True** | 0.0 (unmoved) | **6 → 0** |
| `quadruped` | **False → True** ‡ | 0.374146 → **0.0** | *null* → **0** ‡ |
| `humanoid` | **False → True** | 0.378336 → **0.0** | *null* → **0** |

⚠ **Read the `null → n` cells correctly: they are a WIN, not a regression.**
`cp_mv_broken` is `None` wherever the vertex bijection fails, and §8 of this
file recorded the consequence as a hard limit — *"S2's scorecard-visible effect
is ONE row… only `insect` (currently 6) is measurable today"*. That limit is
gone. **Four of five subjects now have an exact mirror bijection (residual
`0.0`) where one did**, so the M/V defect became *measurable* on three subjects
that previously could not report it at all. **The metric going from
unmeasurable to 8 is progress; the 8 is the newly visible work, not new
breakage.**

⚠ **And the bijections were not bought by this goal.** They arrived with Goal
1's coverage work — S6 order-ranking (PR #94) and U1′ root-ranking (PR #107) —
which changed which pack is served. Goal 2 supplied the instrument (S1's
bijection reformulation) and the relabeller; the geometry that made three
subjects measurable came from the other goal. Recording it the other way round
would be the "scorecard win reported as the fix" failure §5.1 exists to
prevent.

---

## 10.1 ★★★★ THE CEILING WAS BROKEN, AND THE REASON IS THE WHOLE LESSON

This goal had stopped on what looked like a proof. §0.3 says the post-cut FOG
admits **exactly one** linear extension on quadruped and bird, that **225 of
225** M/V-bearing creases have comparable facet pairs — *every label forced* —
and therefore that reaching `mv_swapped == 0` needs a different **pack**, not a
relabel. An exhaustive σ-orbit census then measured **0** valid symmetric
relabel targets for `template-quadruped`, `mesh-insect` and `mesh-dog`, the dog
proven in **1.7 s**.

**Every one of those numbers reproduced. None was wrong. They were SCOPED.**

### The single cleanest piece of evidence

`mcp_harness/fixtures/sigma_census_rerooted.json` (PR #109), `insect`, two rows:

| root | geometry fingerprint | verts | edges | `design_scale` | `hull_coverage` | sw / mm | σ-orbits | **targets (3-conj)** | **targets (4-conj)** |
|---|---|---|---|---|---|---|---|---|---|
| **6** | `109bba7008f904ad` | 45 | 84 | 0.582125 | 0.8595 | 2 / 0 | 28 | **12** | **12** |
| **10** | `109bba7008f904ad` | 45 | 84 | 0.582125 | 0.8595 | 2 / 0 | 28 | **24** | **24** |

**Same fingerprint. Same pack, same vertices, same edges, same scale, same
coverage, same orbit count — and twice the symmetric targets.** The fingerprint
is `mv_repair.fold_fingerprint` (`mv_repair.py:198-206`), a sha256 over
`vertices_coords` + `edges_vertices` with labels **deliberately excluded**, so
two rows sharing it are the same geometry by construction. The two rows differ
in exactly one thing: their `mv_fingerprint` (`a6666ceed07df3d6` vs
`18d85563de15b8c6`) — the **M/V colouring**.

That is Lang's own statement, measured on a production subject. TreeMaker 5's
help for `Action->Build Crease Pattern` says the M/V colouring *"depends on the
particular arrangement of flaps in the flattened base, and so there are **many
possible MVF colorings**"*, selected by the **dangle root**.

### Why the project had never seen it

The required prior-art pass (CLAUDE.md §0) found the root, and it is a
constant:

* `tmTree::GetRootNode()` returns `mNodes.front()` —
  `mcp_harness/treemaker/Source/tmModel/tmTreeClasses/tmTree.cpp:260-263`.
  `TreemakerWrapper.cpp` calls `AddNode` in JSON list order with the
  `parent_id: null` node first, so **the root is whatever our Python put at
  index 0**.
* `rescue_ladder.canonical_order` (`rescue_ladder.py:350`, seeding at `:364`)
  and `rescue_ladder.random_topo_order` (`:386`, seeding at `:391`) both begin
  from `root_id(nodes)`.

⇒ **Every order variant, every rescue rung, every subject, for this project's
entire history, emitted the SAME ROOT.** §0.3's "225/225 forced" measured the
linear extensions of **one** facet-ordering graph. Re-rooting does not
tie-break that graph — it **builds a different one**, a different problem
instance with a different forced set.

> ### ★★★★ A CORRECT MEASUREMENT OF THE WRONG OBJECT HAD CLOSED THE GOAL.
>
> Not a bug, not a sloppy number, not a metric that could not express its
> defect — those failure modes are all catalogued elsewhere in this repo and
> this was none of them. The measurement was sound, exhaustive, independently
> re-derived by 13 agents, and *silently universally quantified over a variable
> nobody knew was a variable*. **The quantifier was the defect.** When a result
> says "no X exists", the durable question is not "is the search right?" but
> **"over what set did it search, and what is being held fixed to define that
> set?"**

### What that unlocked, in order

| PR | unit | what it established |
|---|---|---|
| #104 | U1 root search | Read-only sweep of every root of all five scorecard subjects through the REAL serve path. Pre-registered gate **FIRED on `humanoid` root 2** |
| #107 | U1′ root-rank | The measurement turned into a shipped policy (`root_rank.py`) |
| #108 | U2′ | Closed the vacuous `mv_swapped` ranking key — see §10.4 |
| #109 | U2 census | σ-orbit census **on the re-rooted packs**: targets EXIST where the old census read 0 |
| #118 | U4′ | Leaf roots are admissible — the engine never lost the flap; `MAX_CANDIDATES` 8 → 12 (`root_rank.py:208`) |
| #119 | U4′ | `mv_symmetrize` ships **ON** by default |
| #120 | — | #118 + #119 measured together |

### ⚠⚠ THE SHARPEST PART: THIS FILE ALREADY HAD THE ANSWER, ON 2026-08-04

**§6 open item 5, written eleven days before the goal closed, verbatim:**

> *"**Is the dog reachable by RE-ROOTING?** … The root is `mNodes.front()`, i.e.
> the first entry of the JSON node list we control from Python. Every re-rooted
> compile is a genuine TreeMaker output, so **foldability is guaranteed by
> construction** — which is exactly the property whose absence killed post-hoc
> relabelling. A relabel asks us to vouch for a folded state; a re-root asks the
> compiler for a different one."*

Every clause is right. It names the mechanism, the Python-side lever, and the
precise reason a re-root is a **stronger** move than a relabel. It even carries
the correct caveat that node order flips packability.

**It was never run on any subject.** It was filed as a question about *the dog*
— then §0.3 landed a proof that looked like it closed the whole question, and
an item scoped to one subject went down with it. Running exactly that experiment
on the other five subjects is what closed this goal, and **it still has not been
run on the dog** (§10.5 item 4).

⇒ **A correct idea, correctly written down, scoped one subject too narrowly, and
then buried by a proof that did not actually cover it.** When a proof arrives
that seems to close a question, re-read the open items it supposedly closed and
check each one *individually* — §0.3 never mentioned re-rooting at all, so it
never refuted item 5; item 5 was simply assumed to be downstream of it.

⚠ **The re-rooting lever is bounded and the bound is stated in the code.**
`root_rank.MAX_CANDIDATES = 12` (`root_rank.py:208`) is derived from the widest
admissible set (`fish`, 9) plus three, and **exceeding it makes the stage
decline whole rather than truncate** — a searched prefix would let the stage
claim "the best root" having looked at the first *n* in node-list order, with
no channel to say otherwise.

---

## 10.2 PER-SUBJECT DISPOSITION — every one closed on evidence

### `humanoid` — ✅ SOLVED, and it cost NOTHING

Root **2**, an **interior σ-fixed hub** (degree 3, not a leaf; `sigma_fixed_ids
= [0, 1, 2, 5]`). Control (root 0) against winner (root 2), from
`fixtures/root_search.json` (PR #104):

| axis | control (root 0) | **winner (root 2)** |
|---|---|---|
| `cp_symmetric` | False | **True** |
| `mv_swapped` / `mv_mismatched` | 2 / 0 | **0 / 0** |
| `design_scale` | 0.775554 | 0.775554 |
| `hull_coverage` | 0.6638 | 0.6638 |
| `lint_class` | PASS | PASS |
| rescue `stage` | `none` | `none` |
| `stub_flaps` | 0 | 0 |
| leaf set | `[3, 4, 5, 6, 7]` | `[3, 4, 5, 6, 7]` |
| `cp_residual` | 0.0 | 0.0 |
| `attempt0_pack` | True | True |

**Every other axis is byte-identical.** Symmetry was not bought with scale,
coverage, anatomy or a deeper rescue rung, so CLAUDE.md §1.1(4)'s
coverage-versus-scale rule has **no trade to arbitrate here**. The winner needs
no relabel at all: the σ-orbit search's lightest winner on this fold is the
**empty flip set**, and the bytes are returned untouched.

### `insect` — ✅ SOLVED, and the winner lints STRICTLY BETTER

Root **6** carries **12** targets under both the three- and four-conjunct
gates, exhaustively enumerated (28 orbits, 2²⁸, mode `EXHAUSTED`). The
symmetrizer — default **ON** as of PR #119 — ships a **17-crease** relabel.

| | before | after |
|---|---|---|
| `cp_symmetric` | False | **True** |
| `cp_mv_broken` | 2 | **0** |
| `lint_class` | BENIGN | **PASS** |

⚠ **The `lint_class` movement is the load-bearing detail: BENIGN → PASS is the
linter getting STRICTLY HAPPIER.** Nothing was loosened, no gate was relaxed to
make a headline true, and the relabelled pattern satisfies Oriedita where the
packer's own output did not. A symmetrization that had *cost* lint would be the
trade §10.3 records the user declining on `bird`; this one is free in that
currency too.

### `quadruped` — ✅ SOLVED at first-valid strength ‡ (was ◐ budget-bounded)

The target **exists and has been counted**. Root **8**: **24** valid targets
under **both** gates, space 2⁴⁵, mode `EXHAUSTED` — enumerated **offline** by
PR #109 on a layer-consistent, `cp_audit`-clean base.

⚠ **THE REST OF THIS SECTION IS THE STATE AT PR #123 AND IS SUPERSEDED BY U6'
(PR #125) — it is kept because the reasoning is what the ruling was decided
against, and because its central distinction still governs every OTHER refused
fold.** What changed: the serve now **does** run that search. See the ‡
footnote at the top of this file for the measurement, and §15 of
`docs/superpowers/evidence/2026-08-07-mv-symmetrize/README.md` for the phase
split that reversed the premise. Read below for the mechanism, not for the
current disposition.

The serve did **not** run that search. `mv_symmetrize.MAX_ORBITS = 40`
(`mv_symmetrize.py:149`) and the served fold carries **45** orbits, so `search`
refused **by name** — `orbit_space_too_large` (`mv_symmetrize.py:663`) — before
any DFS started.

⚠ **THE REFUSAL IS NOT A ZERO, AND THE FOLD SAYS SO IN WORDS.** This is the
single design decision that keeps this subject honest.
`UNSEARCHED_REFUSALS = {"orbit_space_too_large", "search_truncated"}`
(`mv_symmetrize.py:166`) separates *"we did not look"* from *"we looked and
there is nothing"*, and only the former gets
`MV_SYMMETRIZE_SKIP_MARKER` (`server.py:1159`) written into `frame_title`:
*"…this base's mountain/valley assignment is therefore the packer's, unexamined
for mirror symmetry — it is **NOT** a finding that no symmetric relabelling
exists, and it must not be quoted as one"*. An empty candidate list looks
exactly like an exhausted search finding nothing; that is precisely the
confusion this marker refuses to allow.

**Root 8 was not free — but the price was paid in the other direction.**
Widening the admissible set in PR #118 also moved `quadruped` on five axes at
once: `hull_coverage` 0.7559 → 0.8797, `design_scale` 0.714351 → 0.724628,
M/V defects 10 → 8, both arms zero-stub and both layer-consistent. Root 8
**dominates** the previously shipped root 5 on every measured axis.

‡ **The `MAX_ORBITS` ruling, taken.** This section framed the raise as a
**serve-budget** question rather than a question about whether a target exists,
and that framing was right — but it left one premise unexamined, and the
premise was false. `MAX_ORBITS` is named and derived as a bound on **search
size**; PR #124's phase split measured the 2⁴⁵ DFS at **≤ 2 s** and the
remaining ~17 s as gating all 288 audit-clean points **so they could be
ranked**. The ceiling was rationing *validation*.

U6' (PR #125) short-circuits on the first point passing all four conjuncts:
**1.336 s** median over 7 runs against the same 10 s bar, deterministic across
9 samples and 2 `PYTHONHASHSEED` values, admitting **only** this fold
(`MAX_ORBITS` 40 → **45**, no margin; `template-insect` at 66 and root 5 at 64
stay refused). `MAX_RANKED_ORBITS = 40` keeps every narrower fold on the
exhaustive **ranked** gate, so nothing that is ranked today lost its ranking.

**The distinction this section is really about survives the ruling intact.**
`UNSEARCHED_REFUSALS` and `MV_SYMMETRIZE_SKIP_MARKER` still separate *"we did
not look"* from *"we looked and there is nothing"*, and they still govern
`template-insect`, root 5, and every future fold above 45. U6' additionally
closed a hole on the same axis it did not inherit: a first-valid walk whose
`_LayerGate` is **unavailable** refuses every point for a *geometry* reason,
finishes the space, and would have reported that zero as a proof. It now
reports `counts_are_census: False` and says so in words.

### `bird` — ⛔ CLOSED as a LOCATED NEGATIVE, by explicit user ruling

Not "we could not find one". **Enumerated, exhaustively, and the answer is
zero at the shipped gate:**

| root | bijection | σ-orbits | 3-conjunct | 4-conjunct | mode |
|---|---|---|---|---|---|
| **0** (served) | yes | 12 | **6** | **0** | `EXHAUSTED` |
| 1 | yes | 12 | 0 | 0 | `EXHAUSTED` |
| 2, 3, 4, 5 | **no** | — | — | — | `NOT-POSED` |

**No root improves it.** Root 1 gives 0/0; roots 2–5 have no vertex bijection,
so no orbit structure exists to relabel.

The six three-conjunct targets are real, foldable and `cp_audit`-clean. They
die on conjunct 4 — *"the shipped Oriedita lint class is not worsened"* — and
all six die identically, at **one vertex**:

> `v2` at paper `(0.504707669, 0.504707669)` — **exactly on the 45° axis**, so
> σ **fixes** it. Symmetrizing inverts its ring from **M3/V1 to M1/V3**.
> Oriedita calls that `ANGLES (Kawasaki)` at **~1e-6°**. Our own re-audit
> measures that vertex's Kawasaki residual at **exactly 0.0**, with parity and
> arrangement both OK, on the base and on every candidate. The lint classifier
> scores it `1 vertex violation (0 M/V-fixable, 1 geometry; 0 hull-boundary,
> **1 numeric-noise, 0 real-interior**)` and closes with *"The pattern is
> flat-foldable as-is. ACCEPT."*

⇒ **THE USER WAS OFFERED THE LOOSENING AND DECLINED IT.** Conjunct 4 could rank
on the `real` count (as `mv_repair.jvm_improving` already does) instead of on
lint **class**, and on that axis all six bird targets are non-worsening and
bird would read **6**. **The decision was to keep the gate strict.**

**The price is named, not hidden: `bird` stays asymmetric rather than trade
`lint_class` PASS → BENIGN.** All six targets flip Oriedita Pass →
FAIL-LINT[BENIGN]. That is one scorecard subject, knowingly not taken, because
loosening a gate to make a headline come true is the failure mode this project
keeps recording. **This is a ruling, not an open question — do not re-litigate
it without new evidence about the vertex, and do not "fix" bird by moving the
gate.**

### `fish` — ⛔ OUT OF REACH, on two independent grounds

**No vertex bijection at any root.** All 14 roots enumerated: `roots_with_
bijection: []`. Ten roots pose the census and every one refuses `no_bijection`
(σ has no vertex map, so there is no orbit to relabel — an *answer*, not a
non-answer). **Four roots — 2, 3, 5, 6 — fail to serve at all** (`could not
build a full crease pattern` / `polygon network is not valid`), so the census
verdict is recorded as `NOT CREATED (incomplete: roots [2, 3, 5, 6] did not
serve)` rather than as a clean negative.

**And separately (PR #103), fish is unreachable by selection of any kind.**
The S7 record implied fish had order variants that were never built. Measured
directly: the never-built set is **empty** — all five variants (`canonical`,
`seeded_0..3`) **were built**, and all five died `POLYS_NOT_VALID` at the
molecule stage, at scales 0.471786 / 0.498340 / 0.583904 / 0.536191 / 0.556913.

⚠ **The instrumentation lesson generalises: the S7 Task-0 fixture records only
PACKS, so it cannot distinguish "variant never built" from "variant built and
failed to pack".** S7's own arithmetic stands (ranking zero clean packs is
byte-identical either way); what its log cannot support is any claim about what
the ladder **attempted**.

### `dog` — ⚠ NOT RE-MEASURED. Stated plainly rather than implied.

The dog is the model that started this project and the whole reason Goal 2
exists. Its `0` — 2³⁵ exhausted in 1.7 s, a genuine proof — **was measured on
the OLD pack, at the old root.**

**It has NOT been re-measured since re-rooting.** Verified directly: the token
`dog` appears **zero** times in `fixtures/root_search.json` (PR #104) and
**zero** times in `fixtures/sigma_census_rerooted.json` (PR #109). Both probes
enumerate exactly the five scorecard subjects (`quadruped`, `bird`, `humanoid`,
`fish`, `insect`); the dog is not a committed scorecard subject and was not in
either subject list.

⇒ **The honest statement is: the dog's proven 0 is a true statement about a
fold that may no longer be the one we would serve, and nobody has checked.**
Given that re-rooting created targets on two of the three subjects whose 0 had
been "proven" the same way, the dog's status is **open, not negative**. It is
the most obvious remaining experiment in this goal and §10.5 files it as such.
**Do not cite the dog's 0 as a current result.**

---

## 10.3 ★★★ THE VACUITY FINDINGS — the durable engineering content

These outlive every number above. The subjects will move; these will not.

### 10.3.1 `mv_swapped == 0` is MEASURABLY vacuous — six live counterexamples

§0.3 already warned that `mv_swapped == 0` is *"exactly what the invalid
patterns score"*, and `COORDINATION.md:200` lists it among four metrics that
*"could not express the defect they were named after"*. That warning was
argued. It is now **measured**, on the scorecard's own trees:

| subject | root | `mv_swapped` | `mv_mismatched` | `cp_symmetric` |
|---|---|---|---|---|
| `insect` | 5 | **0** | 6 | **False** |
| `insect` | 9 | **0** | 6 | **False** |
| `insect` | 12 | **0** | 2 | **False** |
| `insect` | 13 | **0** | 2 | **False** |
| `humanoid` | 6 | **0** | 2 | **False** |
| `humanoid` | 7 | **0** | 2 | **False** |

**Six packs read `mv_swapped == 0` and are not symmetric.** The defect did not
go away; it **relocated into `mv_mismatched`** (M/V ↔ F).

**Provenance, since the two fixtures carry different things and conflating them
is easy** — the six rows are *measured* in `fixtures/root_search.json` (PR #104,
where filtering on `sw == 0 ∧ mm > 0 ∧ symmetric is False` returns **exactly
these six and nothing else**); the *named boolean* `vacuous_mv_swapped_row:
true` was added later by `fixtures/sigma_census_rerooted.json` (PR #109), whose
`roots_with_vacuous_mv_swapped` summary lists `insect [5, 9, 12, 13]` and
`humanoid [6, 7]`. The flag does not exist in the #104 fixture.

**These six are now the required-fail input for both ranking keys** (PR #108) —
the discipline `COORDINATION.md` §4.1 demands, and which four earlier metrics in
this repo shipped without.

⇒ **Use `cp_mirror.py:326-329`'s conjunction — `symmetric = mv_swapped == 0
and mv_mismatched == 0` — never `mv_swapped` alone.** It was always there; two
shipped keys did not use it.

### 10.3.2 The SHIPPED ranking key had the same defect, and the fix measured ZERO

`order_rank.rank_key` (S6, PR #94) keyed **K4 on `mv_swapped` alone** and
coerced a missing value to `0`. Same vacuity, live on the serve path. PR #108
fixed it (`order_rank.py:143-202`):

* **K4 is now `-(mv_swapped + mv_mismatched)`** (`order_rank.py:150`) — both
  defect kinds, delegating to one shared `mv_defects` (`:115`) so the order and
  root stages cannot drift on what counts as a defect;
* **`None` sorts WORST, never 0** — `UNMEASURED_DEFECTS = 10**6`
  (`order_rank.py:56`);
* graded rather than boolean, deliberately: the boolean cannot separate
  `insect`'s 6-defect control from its 2-defect re-rooted sibling, and that is
  the only movement `insect` has ever shown.

⚠ **MEASURED CONSEQUENCE: ZERO.** Across **9** S6 invocations on the committed
fixtures and scorecard subjects, **no winner disagreed** with the old key — no
live S6 pool contains an impostor.

> ### ★★★ AND THAT IS THE POINT WORTH KEEPING.
>
> The fix was made for a reason that **was recorded nowhere**: the old `0`
> coercion was safe **only by way of K3 (`is_bijection`) sitting in front of
> it**. A `None` defect count arises exactly when there is no bijection, and K3
> had already demoted that arm — so the vacuous K4 could never be reached in a
> state where it mattered. **Nothing said so.** Delete or reorder K3 and the
> coercion silently becomes wrong, with a zero-diff test suite. A key that is
> correct only because of an adjacent key's ordering is a latent defect whether
> or not it has fired yet, and *"we measured no disagreement"* is not the same
> claim as *"it cannot disagree"*.
>
> ⚠ Also corrected in #118: the argument that #108's change was *"strictly
> stricter, never looser"* is **unsound**. `rank` is an **ARGMAX over a pool in
> which every arm is already admitted** — nothing is ever refused, so
> "stricter" has no referent. Lowering each arm by its own `mm` is a
> **non-uniform** shift, which is exactly what changes relative order, and the
> winner can move in **either** direction. #108's measured result is untouched;
> its justification was not a proof. **No monotonicity argument can make a
> ranking key safe the way it can make an admission test safe.**

### 10.3.3 ★★★ A census "0" HAS TWO KINDS. Always state the regime.

Both of these were published as `0`. They are **not the same object**, and the
difference is invisible in the number:

| fold | base `layer_order` status | audit-clean pts | targets (ABSOLUTE) | targets (RELATIVE) | regime |
|---|---|---|---|---|---|
| `mesh-insect__CONTROL` | **contradiction: taco-tortilla crease (4, 18) through face 3** | 72 | **0** | **72** | **non-discriminating** |
| `template-quadruped__CONTROL` | **consistent** | 8 | **0** | 0 | **discriminating** |

*(Base statuses measured directly off the committed fixtures in
`mcp_harness/tests/fixtures/mv_symmetrize/` via `mv_repair._layer_status`;
`cp_audit.audit_fold(...).clean` is True on both.)*

* **`mesh-insect`'s 0 was scored under an ABSOLUTE `layer_order` conjunct on a
  base that `layer_order` ALREADY REFUTES.** Every candidate inherits the
  base's contradiction, so all 72 audit-clean points fail a check **no relabel
  can affect**. Under the RELATIVE reading — *not worsened versus the base* —
  the same fold reads **72**. Its 0 measured the base, not the search.
* **`template-quadruped`'s 0 is genuine.** Its base is layer-consistent, so the
  conjunct discriminates: 8 symmetric, flat-foldable-at-every-vertex relabels
  exist and **every one is refuted by the non-crossing oracle**.

⇒ **The true claim in the second case is narrower and located than "0 targets"
suggests.** Record the intermediate (the audit-clean count) and the base's
layer status, never just the 0 — `mv_symmetrize` now does exactly this, which
is why `insect` was recoverable at all.

### 10.3.4 GATE-NAMING COLLISIONS ARE REAL — always say WHICH gate

The **three-conjunct** gate is `cp_mirror.symmetric ∧ cp_audit.clean ∧
layer_order consistent`. The **four-conjunct** gate additionally requires *the
shipped Oriedita lint class is not worsened*. They are **different numbers for
the same fold**:

| fold | 3-conjunct | 4-conjunct |
|---|---|---|
| `template-bird__CONTROL` | **8** | **4** |
| `mesh-bird__seeded_3` | **6** | **0** |
| `mesh-humanoid__seeded_1` | 8 | 8 |

⚠ **And this has already caused one false agreement.** §0.5's halving bug
produced `template-bird` = 4, which **matched the four-conjunct figure exactly
— by coincidence**, while actually measuring the three-conjunct gate wrongly. A
wrong number agreeing with a right number from a different gate is the worst
possible failure signature: it reads as corroboration. **Every count in this
file names its gate; any that does not is unusable.**

---

## 10.4 THE COMPOSITION IS A CHAIN, AND IT IS PINNED BY A SPY

Three stages now touch the served fold, in this order:

    root (U1′, #107)  →  order (S6, #94)  →  relabel (S2′b, #97/#119, ONCE, last)

⚠ **A WRONGLY-ORDERED HOOK READS AS *INERT*, NOT AS BROKEN — which is why this
is a test and not a comment.** `mv_repair.apply_flips` (`mv_repair.py:209`)
takes a `fingerprint` and raises on mismatch (`:217`); `fold_fingerprint`
(`:198-206`) is a sha256 over geometry only. So flips computed against a fold
that is subsequently discarded are **refused**, and the stage does nothing at
all — no error, no crash, no diff. A reviewer sees a feature that "did not
help" rather than a feature wired up backwards.

**It has already gone wrong once, exactly this way.** When the relabeller
defaulted ON while still living inside `_compile_with_perturb` — which the root
stage calls once per candidate — `root_rank` was handed folds it had already
relabelled. Measured consequences: `template-bird` **stopped calling
`root_rank.rank` at all** (the stage skips when the control is already
symmetric, and that gate fired on symmetry the relabeller had just installed,
switching the whole rooting search off), and `humanoid` and `template-quadruped`
changed which rooting they serve, because K4 measures the **packer's** M/V
defect and pre-symmetrizing zeroes it.
`server.mv_symmetrize_suppressed()` (`server.py:1272`) closes it;
`server.root_rank_suppressed()` (`server.py:1364`) is the matching
context-scoped suppressor for callers that discard the fold.

Pinned by two tests that **spy on call order** rather than asserting an outcome:

* `tests/test_mv_symmetrize.py:1116` — `test_THREE_hooks_compose_in_the_documented_order`
* `tests/test_composition_order.py:141` — `test_the_three_stages_fire_in_the_documented_order`,
  measured across all 25 `tests/cases.py` subjects: `mv_symmetrize.symmetrize`
  is called exactly **once** on every one of the 24 that serve, always **last**,
  and every `order_rank.rank` call precedes the single `root_rank.rank` call.

---

## 10.5 WHAT IS HONESTLY **NOT** DONE

Stated as a list so nothing here can be read off as finished.

1. **`bird` is asymmetric BY RULING.** Six targets exist and are not taken.
   Reversible only by a decision about conjunct 4, not by more search. §10.2.
2. **`fish` is unreachable**, on two independent grounds, and 4 of its 14 roots
   do not serve at all — so even its negative is recorded as *incomplete*.
3. **`quadruped` is PENDING** the `MAX_ORBITS` ruling. Its target is counted
   (24) and its space is exhausted **offline**; only the serve budget is open.
4. **The `dog` has not been re-measured post-re-rooting.** Its 0 is a proof
   about a fold we may no longer serve. **This is the most obvious remaining
   experiment in the goal.** §10.2.
5. **⚠ THREE SOURCE COMMENTS ARE STALE AND SAY 2⁶⁴ WHERE THE SERVED VALUE IS
   2⁴⁵.** All three describe `quadruped` at its **pre-#118 root 5**; #118 moved
   it to root 8, whose space is 2⁴⁵ — a factor of roughly **524,000** in search
   space, and enough to flip the `MAX_ORBITS` decision that reads them:

   | file:line | what the comment says |
   |---|---|
   | `mcp_harness/server.py:1186` | quadruped 64 orbits (`2**64`) — REFUSED `orbit_space_too_large` |
   | `mcp_harness/mv_symmetrize.py:140` | quadruped "at its shipped root carries 64 orbits (`2**64`, 5 swapped / 49 preserved / 10 fixed)" — the stated basis for `MAX_ORBITS = 40` |
   | `mcp_harness/mv_symmetrize.py:788` | "Measured on the served quadruped (`2**64`): AssertionError…" |

   **A task is filed. This record does NOT fix them** — it is a documentation
   unit, and another unit may be live in those files. Anyone reading
   `MAX_ORBITS`'s "WHY 40" rationale should know it was calibrated against 64
   and is now being asked about 45.
6. **`mv_symmetrize`'s open question from §8 of its own spec is still open**:
   is relabelling 25–37% of a crease pattern what a human folder wants? The
   default flipped ON because it buys a real scorecard subject, **not** because
   that question was answered. `IDE_MV_SYMMETRIZE=0` remains byte-identical to
   the pre-S2′b serve and is pinned by test.
7. **The `faces_vertices` / `faceOrders` export** (§2.7) was named as a
   candidate follow-on in 2026-08-04 and never scoped. The exported `.fold`
   still discards the facet ordering — *the primary object*, per Lang &
   Demaine — and keeps only its shadow.
8. **⚠ REFERRED, NOT FIXED — an independent code review of the merged
   #118/#119/#120 stack surfaced 14 findings.** **None is in this record's
   file** — this unit changed exactly one file, this one, and no production
   code — and none is fixed here. Three are recorded because they bear on
   Goal 2's own claims:

   * **Item 5 above was independently corroborated.** The review flagged the
     stale `2**64` constants without being told about them, and reached the
     same conclusion: the stated margin for `MAX_ORBITS = 40` and its claim to
     refuse *"the one measured space that is not answerable at all"* are both
     **false as shipped**, because they describe root 5.
   * **`agent_loop.py`'s SYSTEM_PROMPT never learned about re-rooting.** It
     says *"Send tree_nodes UNCHANGED"* (`:232`) and *"apply_shaping_ops(
     tree_nodes=<the SAME tree you compiled>"* (`:478`), while `ROOT_MARKER`'s
     own note instructs that recompiling tools be given `served_tree`.
     Verified: `served_tree`, `re-rooted`, `root_rank` and `ROOT_MARKER` have
     **zero** occurrences in `agent_loop.py`. So on any subject where the root
     stage wins, follow-up shaping ops silently rebuild a *different* crease
     pattern. **Filed as its own task.**
   * **`tests/test_serve_attempt0_pin.py:327-328` closes with two assertions
     that read only from the frozen `_MOVED` literal** — the tautological
     shape §10.3 is about. ⚠ **Weaker than it first looks, and worth stating
     precisely:** `:323-324` already assert `_measure(ctrl_str, …) ==
     exp["control"]`, which pins `exp` to the run, so the trailing two are
     **redundant rather than vacuous**. They add no constraint; they do not
     remove one. *Recorded with that correction rather than as a clean hit —
     a vacuity finding that is itself overstated is exactly what this section
     warns against.*

---

## 10.6 ★★★★ WHY THIS FILE SUPERSEDES INSTEAD OF DELETING

Every stale section above carries an inline ⚠ naming what refuted it, and none
was removed. **That convention is why this wave succeeded, and it is the single
most transferable thing in this record.**

The mechanism is concrete, not sentimental. §0.3 did not merely assert "the FOG
cannot reach it" — it **preserved the premise it was reasoning from**: 225 of
225 creases forced, in *one* graph, built from *the* root, with `GetRootNode`
named in §2.8's table. Keeping that visible is what made the gap findable. A
tidied-up version reading *"MEASURED: no relabel-only fix exists"* would have
been **just as true**, one tenth the length, and **unfalsifiable** — the
quantifier that turned out to be the whole defect would have been the first
thing an editor cut, because it looked like background.

⇒ **The refutation lives next to the claim, so the claim's assumptions stay
readable.** A deleted premise cannot be re-examined, and this goal's entire
result came from re-examining one.

Two corollaries this wave paid for directly:

* **A stale record is worse than no record.** `main`'s copy of this file sat at
  `a81708e` for nine days saying *"S2 recon in flight / S3 blocked"* while five
  slices shipped past it. The refresh existed the whole time — on the unmerged
  branch `claude/goal-2-mirror-metric-planning-e2fc65` at `fd7a210` — and was
  **recovered rather than rewritten** (§0.5). A sibling unit this wave found
  the mirror-image defect: artifacts cited in a PROGRESS.md as *committed* that
  were never on `main` at all (landed as PR #102). **Check that what a progress
  file cites actually exists, in both directions.**
* **"Every number reproduced" is compatible with "the conclusion was wrong."**
  Thirteen agents independently re-derived §0.3 and confirmed it. Reproducibility
  audits the *measurement*; it does not audit the *quantifier*. Ask what was
  held fixed.

---

## 10.7 VERIFICATION FOR THIS RECORD

Documentation-only unit; **no production code changed** and the frozen baseline
was **NOT** re-blessed (`--out` never passed).

* **Scorecard** — `benchmark_subjects.py --baseline fixtures/scorecard_baseline.jsonl`
  re-run on this branch. All five rows reproduce PR #120/#121 **exactly**:
  `bird` 0.9848/1.515998/PASS/False/4, `fish` 0.9077/0.653249/BENIGN/False/`?`,
  `insect` 0.8595/0.582125/PASS/**True**/0, `quadruped`
  0.8797/0.724628/BENIGN/False/8, `humanoid` 0.6638/0.775554/PASS/**True**/0;
  `stub_flaps` 0 on all five.
* **No test reads this file**, so the suite result is valid for its final state.
* **Every `file:line` citation in §10 was verified by reading the file**, and
  the third stale `2**64` (`mv_symmetrize.py:788`) was found during that audit
  rather than supplied.

---

## 11. Log (closing)

| date | entry |
|---|---|
| 2026-08-07 | S2′a ships (#93); the ordering slice handed to Goal 1. Recorded on the planning branch only — **never merged**; see §0.5. |
| 2026-08-09 | Planning branch `fd7a210`: the halving bug found in Goal 2's own enumeration — **every target count it had published was halved**. S2′a's pruned DFS becomes the trustworthy tool. |
| 2026-08-15 | Prior-art pass (CLAUDE.md §0) finds Lang's *"many possible MVF colorings"* and the dangle root. **`GetRootNode` returns `mNodes.front()` — the root was a project-wide constant.** §0.3's proof is re-scoped, not refuted. |
| 2026-08-15 | **#104** root search: the pre-registered gate FIRES on `humanoid` root 2 — symmetric, with every other axis byte-identical. |
| 2026-08-15 | **#107** root-rank ships. **#108** closes the vacuous `mv_swapped` key in `order_rank.rank_key`; measured winner disagreement **zero**. |
| 2026-08-15 | **#109** σ-orbit census on the re-rooted packs: targets EXIST where the old census read 0. `insect` roots 6/10 share a geometry fingerprint and carry 12 vs 24 targets. |
| 2026-08-15 | **#103** fish closes negative: all five order variants were BUILT and all five died `POLYS_NOT_VALID`. The S7 log could not have said so. |
| 2026-08-15 | **#118 + #119 + #120**: leaf roots admissible, `mv_symmetrize` default ON. `insect` `cp_symmetric` False→True, `lint_class` BENIGN→**PASS**. |
| 2026-08-15 | **GOAL 2 CLOSED at 2 of 5 measured symmetric**, from 0 of 5. `bird` closed as a located negative by user ruling; `fish` out of reach; `quadruped` located and PENDING on `MAX_ORBITS`; **the dog not re-measured**. |
| 2026-08-16 | **PENDING DISCHARGED — 3 of 5.** `MAX_ORBITS` 40 → 45: the ceiling was rationing VALIDATION, not search (2⁴⁵ DFS ≤ 2 s; ~17 s was ranking 288 survivors). Early-exit costs **1.336 s** vs a 10 s bar, deterministic across 9 samples / 2 hash seeds. `quadruped` `cp_symmetric` **False → True**, `cp_mv_broken` **8 → 0**; every other cell and every other subject unmoved. New tier `MAX_RANKED_ORBITS = 40` keeps narrower folds on the ranked gate. |
| 2026-08-17 | **4 of 5 — `bird` JOINED, and it was a SIDE EFFECT of a CI fix.** #129's `serve_rank` collapse (Pass == BENIGN, because U20 measured that the choice between them inverts across platforms) admits a conjunct-4 survivor the old filter rejected; on `bird` that survivor is symmetric. `bird` `cp_symmetric` **False → True**, `cp_mv_broken` **4 → 0**, `lint_class` PASS → BENIGN; `insect` `lint_class` PASS → BENIGN — ⚠ **both lint moves are macOS-ONLY and `insect`'s is a WINNER SWAP, not a relabel of one winner; see §"the price is paid on macOS only" above before quoting either.** Nothing else moved, either platform. BISECTED over four arms with the `.so` rebuilt at each — #128 innocent, `main` innocent (including #127, which moves the extractor that builds these trees). ⚠ **The lesson: a determinism fix can MOVE THE RESULT, so a re-bless measured before it is stale by construction.** #126 blessed at `153f9c7` and four cells had already moved. |
| 2026-08-17 | **THE CONJUNCT-4 LOOSENING IS RATIFIED, AND IT HAD BEEN SHIPPED THROUGH A SIDE DOOR.** U22 (PR #131) re-measured the price on both platforms and reported, unprompted, that #129 contradicted a standing user ruling: the ruling was *"keep conjunct 4 strict; do not fix `bird` by moving the gate"*, and #129 — a PR about **numeric epsilons** — routed the conjunct-4 **filter** through `serve_rank` in all four places (`gate()` `:647`, `Candidate.rank_key` `:712`, `_FirstValidGate` `:824`, exhaustive path `:1319`), its own docstring saying *"⚠ THIS IS A DELIBERATE LOOSENING OF CONJUNCT 4 AND IT HAS A PRICE, PAID KNOWINGLY."* **Ratified by the user on the new evidence**, which met the ruling's own reopening condition: `real == 0` on both sides on both platforms, and the Pass/BENIGN split **inverts** across platforms (all 8 `template-bird` survivors), so a strict conjunct 4 does not preserve a standard — it **names a different winner on each machine while claiming to name the better one**. ⚠ **Strictness and platform-deterministic serving are MUTUALLY EXCLUSIVE here**, because the quantity conjunct 4 filters on is itself platform-dependent. **Do not re-litigate; do not "restore" the strict filter without first refuting the inversion measurement.** |
