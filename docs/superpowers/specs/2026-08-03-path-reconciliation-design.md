# Path reconciliation — give a declared bilateral pair the hub it folds from

**Status:** phases A, B and **C shipped**; §4.9's scale rung **NOT SHIPPED —
falsified a third time, by its own gate** (§4.9)
**Date:** 2026-08-03 (rev. 6)
**Predecessor:** [pair equalization](2026-08-02-pair-equalization-design.md)
(shipped `f5787b9`, disclosed `f72d8b8`)

> **What the first review changed.** The mechanism survived; the operation did
> not, quite. Re-parenting alone strands junctions, and a stranded junction is
> a **flap the mesh never had** — 12 across the corpus, causing the `fish`
> crease-pattern regression this spec previously reported as unexplained, plus
> two outright packing regressions the serve-default sample structurally could
> not see (§2.6.1, §2.6.2). §4.1 now removes them, which makes the slice
> strictly better than the first draft rather than merely safe. Also corrected:
> the packing risk was understated 2× (§7), `pair_gap_max` silently stops
> measuring the extractor (§4.6), a negative control that failed was omitted
> from §2.8, a missing null control makes §2.2 much stronger than it claimed,
> the reach property is exact rather than 5e-07, and the `apply_symmetry`
> citation named the wrong function.

> **What the second review changed.** Every remaining defect was in an
> *argument*, not in the mechanism — which is why the first review's numbers
> all still stand while three of its justifications do not.
>
> 1. **The deletion safety argument named a quantity the engine ignores.**
>    "Survivors keep their ids" is true and irrelevant: placement is seeded
>    from **list index** (`TreemakerWrapper.cpp:234-253`). Controlled —
>    renumbering ids is byte-neutral 5/5, reordering the list changes the fold
>    5/5. Deletion re-indexes survivors, worst seed displacement 1.2210 on a
>    1×1 paper. The mitigation is now the three-arm compile sweep, which is a
>    measurement rather than a proxy (§2.6.1, §4.5, §7). This also retires
>    "contraction would renumber" as a reason for anything (open question 4).
> 2. **The operation tripped the extractor's own admission guard** and no
>    pack-rate gate could have seen it, because the affected candidates compile.
>    Root degree rises in 40/50 configurations and flips `structural_prefilter`
>    on 3 — which are *all* of `insect`'s admissible configurations, 3 → 0, on
>    the subject the operation rescues. **§4.6 decides it**: the root-degree
>    term is evaluated on the pre-operation tree, the same discipline
>    `pair_gap_max` already requires (§2.6.3).
> 3. **The test list was wrong in both directions.** The "cascade" test was not
>    a cascade, so the real one had no test at all (§6.11–6.12, both trees
>    verified, including a 3-level case that defeats a two-pass implementation);
>    one test is **already red at HEAD** from the shipped predecessor, proven
>    arithmetically; and §6 now names every item so the next renumber cannot
>    rot the cross-references, as it twice did.
> 4. §2.8's `bird` conclusion was rescued on a false premise (`bird` has 4
>    leaves, not "enough"). It survives on a stronger one — the vertex residual
>    is one-sided, so a positive reading is a witness degeneracy cannot fake —
>    and applying that consistently qualifies the `humanoid` bullet, which the
>    previous draft left unqualified. The stated *cause* of the `QUAD` control
>    failure was also wrong.
> 5. Six code citations pointed at the wrong line.
>
> Every number below is reproducible from `mcp_harness/probe_*.py` and the
> committed `fixtures/`.

> **What phase A and the 45-configuration sweep changed.** Phase A shipped
> unchanged from §4.1's pseudocode and survived a 21-agent adversarial review
> with **zero** confirmed defects — 13 of its 14 tests are killed by at least
> one deliberate mutation, and `cascade-fixpoint` demonstrably defeats both a
> one-pass and a two-pass removal. Two things moved anyway:
>
> 1. **§4.3's refusal sentence was wrong, and the code was right.** It claimed
>    a refused pair keeps "its declared pairing", citing a precedent that
>    provably drops it. Two reviewers filed the divergence as a HIGH *code*
>    defect; the prose was the broken side. Carrying a refused pairing forward
>    would give the root a phantom length and break §6.6 and §6.9 downstream.
> 2. **§4.9's clamp is now a rescue rung, not a normalization.** The sweep
>    (45 configs × 4 arms) showed the unconditional clamp modifies 22 trees to
>    buy **4** rescues, with **18** firing on trees that already packed — one
>    of which, `humanoid` v64, loses a bit-exact mirror crease pattern for it.
>    As a `rescue_ladder` rung it reaches the same **43/45** while touching 18
>    fewer trees, and it is proportion-preserving, so it may sit ahead of
>    jitter rather than beside it. The accepted cost is that 22 trees stay
>    outside the Tier 2.5 gate's length regime.
>
> **Phase B steps 1–2 shipped (`8894d95`, `523dbce`); both gates are green.**
>
> | gate | result |
> |---|---|
> | pack rate over §6.19's 45 configs | **39/45**, reproducing the `+drop` arm exactly; misses are `insect` v64 ×4 (§4.9's rescues) and `bird` v128 ×2 (rescued by nothing). No config that packed at `+drop` regressed. |
> | §2.6.3 prefilter-admission table | **0 mismatches** against `prefilter_before` on all 50. `insect` holds at **3**; with the root-degree term left unpinned it measures **0**, so §4.6's decision is load-bearing, not precautionary. |
> | full suite vs the `460ee32` baseline | 6 failed / 2176 passed / 11 skipped — the **same count and the same set**, with item 2 moved `humanoid` → `insect`. Zero unexplained. |
>
> ★ The leaf-set invariant is now verified on **production** data, which is
> worth more than the hand-built fixtures: re-blessing the snapshot shows
> `insect` deleting two interior junctions (10 → 8 nodes, dropped `[1, 7]`)
> with its leaf set **identical** before and after, as with all four other
> subjects. The invented-flap failure mode does not occur on any real subject.
>
> **§4.9's rung is NOT SHIPPED, and the section has now been wrong three
> times — the third time falsified by the very measurement it asked for.** The
> *(variant, scale)* grid it demanded was run on 2026-08-03 and says the clamp
> factor is **arbitrary with respect to packing**. Full detail in §4.9; the
> one-line version is that `LONGEST_LIMB_TARGET / longest` = **0.9486** on all
> four rescues, and at exactly that scale **0 of 8 variants pack**, while 0.96
> and 0.90 both do. Its apparent "rescue" was bought by **jitter**: the served
> base at 0.9486 carries the `did not pack exactly` note, which
> `agent_loop.py:318` defines as *"the backend nudged your EDGE LENGTHS"*. So
> the section's own justification — *"proportion-preserving, which is why it may
> sit ahead of jitter"* — is backwards for the factor it specifies. Steps 1–2
> do not depend on it: they carry 12 of the 16 rescues.
>
> One phase-A test-quality item is left open on purpose:
> `test_no_caller_mutation` passes vacuously in a full run because the
> module-level fixtures are shared mutable state and the operation is
> idempotent. The property stays covered by `shared-strand`/`cascade-fixpoint`;
> the fix is to make the fixtures functions.

> **What phase C changed.** The three owed pins landed (§6.15/§6.17/§6.18),
> each mutation-checked against the specific line it guards, and §6.18 grew a
> companion: **the count test alone is not a pin.** It calls
> `structural_prefilter` itself, so deleting `root_children=` from the one
> production call site leaves it green — measured, not assumed. §6.18b runs the
> real search and watches the real call, and the mutation now fails with
> `{'passed': None, 'counted': 6, 'verdict': False}`. §6.17 gained a companion
> for the same reason: a *refused* pair never reaches `reconcile_pairs`, so its
> gap must ride the re-parent record or it is lost, and the two arms kill
> different mutations.
>
> The disclosure block shipped, and with it three agent-facing statements this
> slice had made **false**: §3's predicted collision (*"reworking STRUCTURE is
> the sanctioned lever WHEN PACKING FAILS"* — this slice reworks hub grouping on
> trees that pack fine); *"edges normalized so the longest limb == 0.40"*; and
> `hubs (root's children)`, which listed re-parented **flaps** as hubs owning no
> flaps (`1->[], 7->[], 8->[]`).
>
> **`pair_path_gap_max` reads 0.0 on all five subjects** and on every
> (subject, voxel, prune) the live test sweeps — §4.8's stated expectation, met.
>
> ★★ **The scorecard re-bless found a regression no phase-B gate could see, and
> attribution was required to find it.** The committed baseline was 2026-07-28,
> six days and *two* slices old, so its 16 moved axes were attributed by
> counterfactual — re-running at this commit with the re-parent monkeypatched to
> identity, the method the S7 baseline itself established. Ours: `bird` 5 → 4
> served leaves (a **gain** — `unclamped_fidelity` is distance to the true
> reference in both directions and bird's reference is 4, so the old serve
> carried one flap too many), `fish` 7 → 8, `insect` 7 → 8 with
> `nudge_marker` True → False. And **`quadruped` jitter → stub, `stub_flaps`
> 0 → 3**: the re-parented tree no longer packs under jitter, so the ladder
> falls through to Lang's stub remedy and the serve trades nudged proportions
> for three engine-invented flaps. `rescue_ladder` ranks `invents_anatomy`
> first, so that is a downgrade in admissibility class — invisible to pack rate
> (it packs) and to admission (quadruped holds at 5). §7 carries it.
>
> **Full suite at phase C: 6 failed / 2194 passed / 11 skipped (20:30)** — the
> **same six** as the `460ee32` baseline, item 2 still `humanoid` → `insect`,
> and `+18` passing from the tests this phase added. Zero unexplained.
>
> §7's visual check is paid — `docs/superpowers/evidence/2026-08-03-reparented-bases/`.
> No pathology: all three reconciled bases are well-formed uniaxial bases, and
> `humanoid` is an **exact** mirror (1.04e-01 → 0.00e+00) on a markedly simpler
> pattern (33 → 21 vertices). Two limits are recorded with it: a flat-folded
> silhouette shows layer structure, not limb placement, and the mirror residual
> is one-sided.

---

## 1. What this fixes

Pair equalization made the two flaps of a declared bilateral pair the same
length. Measured afterwards, that fixed **34 of 117** real declared pairs. The
other **83 still fold apart**, and equal lengths are why it is not obvious: the
lengths agree, the reach does not.

A flap's tip lands, in the folded uniaxial base, at its **root-to-tip path
length** — not at its last edge length. Two leaves with identical edges but
different parents sit at different depths on the spine, so their tips land at
different distances from the centre and the model folds lopsided in exactly the
way the user reported.

This slice makes every declared pair share a hub, which is the precondition
that makes equalizing its two lengths *sufficient* — and then removes the
junctions that move leaves behind, because a junction with no children left is
a flap (§2.6.1).

---

## 2. What was measured (2026-08-03, reproducible)

All figures: **117 declared pairs**, 5 committed meshes × 3 voxel resolutions ×
4 prune fractions (50 configurations that emit at least one pair). Probes in
`mcp_harness/probe_*.py`; raw rows under `fixtures/`.

### 2.1 The shipped fix is exact — and only for sibling pairs

| | pairs | path gap (÷ span) |
|---|---|---|
| siblings (share a parent) | 34 | min 0.0000, median 0.0000, **max 0.0000** |
| non-siblings | 83 | min 0.0325, median 0.1109, max 0.5943 |

Every sibling pair is *exactly* congruent. Every non-sibling pair misses, and
none by less than 3.25% of the model's own length.

Per subject, non-sibling share: `fish` 22/22, `quadruped` 14/17, `insect`
31/45, `humanoid` 10/21, `bird` 6/12.

### 2.2 The 83 are real mirror pairs, not detector mistakes

The first hypothesis — that the matcher had paired the wrong limbs — is
**falsified**. Reflecting each leaf's 3-D position across the chosen mirror
plane and measuring the distance to its declared partner:

| | mirror residual (÷ mesh scale) | straddle the plane |
|---|---|---|
| siblings | median 0.0106 | 28/34 |
| non-siblings | median 0.0178 | 78/83 |
| **every leaf pair in the same tree (null)** | **median 0.4627** | — |

The null is what makes this an argument rather than an assertion. "0.0178 is
small" is unanchored on its own — small compared to *what*? Compared to the
score a **wrong** pairing gets: re-pair the same leaves any other way and the
residual is **26× worse** (44× for the siblings). Both declared groups sit well
over an order of magnitude below the null, and 78 of 83 sit on *opposite* sides
of the mirror plane, which is what left/right means. The pairing is right. The
graph is wrong.

Note the two declared groups are *not* identical — 0.0178 is 68% above 0.0106,
and an earlier draft of this section called them "geometrically
indistinguishable", which overstated it. They are the same order of magnitude
and both are nowhere near the null. That is the claim, and it is sufficient.

> **Caveat.** Both the straddle column *and* `mirror_residual` were computed
> against the centroid-anchored plane (`offset = 0`), while
> `_symmetry_pairs_and_axis` escalates to *offset* planes in some
> configurations. The error direction is knowable, though, and it is
> favourable: the escalation is additive over unpaired leaves only and passes
> `require_straddle=True` (`mesh_to_tree.py:521`), so every pair it adds
> straddles *its own* plane by construction. Measuring against offset 0 can
> therefore only **under**-count straddle, never inflate it. Nothing in this
> design depends on the column either way — see §4.4 — and §7 keeps the exact
> re-measurement as an open question.

### 2.3 The tree is not mirror-symmetric — 82 of 83 differ in depth

A true reflection maps the tree to itself and fixes the root (the root lies on
the spine), so it **preserves depth**. Measured: only **1 of 83** non-sibling
pairs has its two members at equal depth.

This is disqualifying on its own. No assignment of edge lengths makes a tree
symmetric when left-leg is 2 hops from the root and right-leg is 4. It is also
why the literal reading of "path reconciliation" — a constrained least-squares
solve over edge lengths subject to `P_a == P_b` — was **rejected**. It can force
the two reaches to agree while leaving a structurally asymmetric tree, and the
displacement it demands is not small: on `fish` at voxel 64 / prune 0.30, leaf 3
reaches 0.1686 while its declared partner leaf 10 reaches 0.5537, so meeting in
the middle means removing ~0.19 of *interior* path — edges shared with leaves 9
and 11, which are not in the pair and would be dragged with it.

### 2.4 The cause: one junction smeared into two along the spine

For **76 of 81** non-sibling pairs, *both* attachment junctions sit within 0.05
of the mirror plane — both correctly on the spine, where anatomy puts them.
(81, not 83: the two degenerate `fish` rows of §2.6 have a member with no
parent, so they have no junction to measure.) Their separation decomposes as:

| | median (÷ mesh scale) |
|---|---|
| total junction separation | 0.0827 |
| ...its lateral component | 0.0255 |
| ...its along-body component | **0.0787** |

The junctions are offset **along the body**, not across it. And the bones
themselves confirm it: the limb vectors of a sibling pair reflect onto each
other with median residual 0.0107, while a non-sibling pair's manage only
0.0868 — 8× worse — because they reach a mirrored tip from different origins.

One anatomical junction — a shoulder — was split by voxel skeletonization into
two spine nodes about 8% of the mesh apart, and each limb kept its own copy.

Topologically: **68 of 83** have one junction as an *ancestor* of the other
(the smeared-spine case); **13** are cousins, branching apart above; and **2**
have a member with no parent at all (§2.6).

### 2.5 Searching for a clean extraction does not work

The extractor already sweeps voxel × prune and ranks candidates, so the cheap
question is whether some configuration is simply symmetric already.

| subject | configs emitting pairs | all-sibling |
|---|---|---|
| bird | 9 | 3 |
| humanoid | 11 | 1 |
| fish | 9 | **0** |
| insect | 12 | **0** |
| quadruped | 9 | **0** |

`fish`, `insect` and `quadruped` are non-sibling at *every* setting. And 3 of
the 4 "clean" configurations are clean only because they found **fewer pairs**
(bird v128/p0.6 drops from 2 pairs to 1; humanoid the same). Searching harder
buys nothing; it just loses anatomy.

### 2.6 The operation was measured end to end before being specced

Applying §4.1 to all 50 configurations and then re-running the shipped
equalization:

```
path gap > 1e-9   BEFORE  83/117      AFTER  2/117
```

The two survivors are the **same degenerate extraction** — `fish` at voxel 64,
prune 0.5 and 0.6 prunes down to a *two-node tree*, and `detect_symmetry`
declares `[[0, 1]]`, pairing the root with its only child. (`_bfs_remap` falls
back to `list(tree.nodes)` when no node has degree > 1, so a leaf becomes the
root.) §4.3 refuses it explicitly.

**On hand-authored trees the operation is a byte-level no-op** — verified on
`HSHAPE`, all four templates, `DOG_RAW` and `DOG_REPAIRED`: 0 pairs moved, 0
refused, **0 dropped**, node lists identical. Every committed golden is a
sibling-pair tree, so nothing moves and nothing can be stranded. Note this also
means the golden suite is **structurally incapable** of catching a removal
defect — see §6's negative controls.

**Reach is preserved to float precision — not exactly.** Root-to-tip path
length of every node, before vs after the re-parent, across all 50
configurations: worst drift **1.1e-16**. Of the 162 re-parented leaves,
**14 carry a nonzero residue**, all at that same 1.1e-16 — one ULP on values of
order 1, from re-associating a sum of floats.

An earlier draft rounded the new lengths to 6 dp, measured 5.0e-07, and
explained it away as "the rounding the module already applies". That was wrong
twice: `pair_reconcile` does not round at all (only `to_metric_tree` does, at
emission), and the rounding was therefore the *sole* source of drift above
epsilon. So §4.1 does not round.

> A **second** draft then over-corrected and claimed the moved leaves drift by
> *exactly* zero. That was an artifact of this probe's own reporting, which
> rounded the per-pair drift to 9 dp and printed 1.1e-16 as `0.0` — the same
> mistake as the first draft, one layer down, in the measurement rather than the
> operation. The field is now stored raw. The lesson is worth keeping in the
> document: **do not round a measurement whose purpose is to detect rounding.**
> §6.4 `reach-preserved` therefore asserts a 1e-12 bound, not equality — tight enough that a
> re-introduced `round(..., 6)` (5.0e-07) fails it by five orders of magnitude,
> loose enough to be true.

### 2.6.1 The operation must remove the junctions it empties

The first draft of §4.1 stopped at the re-parent and left the vacated junction
alone, on the reasoning recorded in §4.5: it becomes a degree-2 interior node,
a subdivided edge, metrically identical. **That is only true when the junction
keeps another child**, and measurement says it often does not:

```
configs where the leaf set GROWS   10/50        invented flaps  12
```

`fish` v64/p0.3 — *the serve default* — goes 7 leaves → 8. `fish` v96/p0.3 goes
11 → 13, and both invented leaves sit **off the mirror plane** (0.229 and 0.191
of mesh scale). A childless non-root node is a leaf by the project's own
definition (`tree_contract.py:211-213`), a leaf is a flap, and a flap is a limb the
mesh never had. Two of them are precisely the *unpaired lateral leaf* that §2.7
calls the residual an automorphism cannot see — and §2.7's count of "3 leaves
total" cannot see them either, because `_unpaired_laterals` runs on the
**skeleton graph**, which this operation never touches.

It is not a cosmetic accounting problem. `benchmark_subjects.py:93,167` computes
`served_leaves` from the served tree and derives `served_fidelity` from it,
while `stub_flaps` — the column that exists to keep invented anatomy out of the
fidelity number — is sourced from the compiled fold's `STUB_MARKER` and is
structurally blind to a flap invented upstream in the tree. The scorecard's own
comment names this failure: *"the scorecard reports a byte-clean attempt-0
exact serve for a base carrying a flap the engine invented. Nothing goes red."*

**So §4.1 removes them.** Deleting a childless junction is reach-preserving by
construction — nothing hangs below it, so no other node's root-to-tip path can
move. With removal, the leaf set is unchanged in **50/50** configurations.

Removal **cascades**, and the numbers are not the same number:

| | |
|---|---|
| invented flaps (leaf-set growth) | **12**, in 10 configs |
| **nodes actually removed** | **17**, in the same 10 configs |
| configs where the cascade went deeper than one level | 4 |
| deepest cascade | 2 levels (`fish` v96/p0.3 removes `[8, 10, 11, 13]` of 19 nodes) |

Deleting a stranded junction can strand *its* parent, so the loop runs to a
fixpoint. That is correct rather than alarming — a chain of junctions holding
nothing up is a chain of invented flaps waiting to happen — but it means "12"
is the anatomy figure and "17" is the edit figure, and §7 must quote the second
when it talks about node count. The cascade cannot reach anatomy: everything
that was a leaf before, and every pair member, is in `keep`.

**Removal is not free, and the first draft's reason for thinking it was is
wrong.** That draft argued removal is safe for packing because *"survivors keep
their ids, so the node-list order that packing is knife-edge sensitive to is
untouched"*. The engine does not read ids. `TreemakerWrapper.cpp:234-253` seeds
every node's initial placement from `order` — the loop counter over the
incoming list — and uses the id only as a key into `mNodeMap`:

```cpp
double r = 0.10 + 0.03 * double(order);
double a = 2.39996 * double(order);            // golden-angle spread
```

That branch always fires here, because `to_metric_tree` emits no `x`/`y`.
`tree_contract.py:169` already says so in committed prose: *"the engine reads
the list in order and seeds placement from list position."* Controlled on five
committed golden trees:

| control | .fold byte-identical |
|---|---|
| every id rewritten, **list order fixed** | **5/5** |
| ids fixed, **two siblings swapped in the list** | **0/5** |

So the quantity the argument invoked is exactly the one the engine ignores, and
the quantity deletion actually moves is the one it reads. Deleting an entry
shifts the index of every survivor after it, which re-seeds them:

| | |
|---|---|
| configs where at least one survivor is re-indexed | **10/50** (the 10 that delete) |
| worst re-indexing | **9 of 14 nodes** (`insect` v96/p0.5) |
| worst seed displacement | **1.2210** on a 1×1 paper (`fish` v128/p0.3) |

A displaced seed is not a displaced flap — ALM optimizes from there — but it is
the documented basin lever on this packer, and this document measures it twice
independently: the control table above (a sibling swap changes the fold 5/5),
and §2.8's `bird` check, where three node orderings of one tree produce two
visibly different vertex sets. So it cannot be waved off.

**The real mitigation is §2.6.2's three-arm compile sweep**, which runs the
removal arm through the actual engine on every configuration where deletion
fires and finds 13/14 against raw's 6/14. That is a measurement of the thing
itself rather than a proxy argument about it, and it is the only reason removal
is claimed safe.

### 2.6.2 Packing, and why the serve default was not a sufficient gate

Measured through the real serve path (`draft_and_compile_full_base`) on the
serve default plus every configuration where the operation strands a junction —
three arms: raw, re-parent only, re-parent + removal.

At the extractor's default voxel 64 / prune 0.30:

| subject | re-parented | raw | re-parent | + removal | |
|---|---|---|---|---|---|
| bird | 0 | ✅ | ✅ | ✅ | no-op |
| fish | 2 | ✅ | ✅ | ✅ | |
| humanoid | 1 | ✅ | ✅ | ✅ | |
| insect | 2 | ❌ | ❌ | ❌ | scale 0.5076 → 0.5235 |
| quadruped | 2 | ❌ | **✅** | **✅** | **rescued** |

3/5 → 4/5, which is what the first draft reported and stopped at. Widening to
the other nine configurations whose leaf set changes shows what that missed
(`probe_pair_topology.py --compile`, all 14 rows):

| config | raw | re-parent only | + removal |
|---|---|---|---|
| fish v96/p0.3 | ❌ | ✅ | ✅ |
| fish v128/p0.3 | ❌ | ❌ | **✅** |
| fish v128/p0.4 | ✅ | **❌ regression** | ✅ |
| insect v96/p0.5 | ❌ | ❌ | **✅** |
| insect v96/p0.6 | ✅ | **❌ regression** | ✅ |
| insect v128/p0.3 | ❌ | ✅ | ✅ |
| insect v128/p0.4 | ❌ | ✅ | ✅ |
| insect v128/p0.5 | ❌ | ✅ | ✅ |
| insect v128/p0.6 | ✅ | ✅ | ✅ |
| **these nine** | **3** | **5** | **9** |
| **all 14 incl. serve default** | **6** | **9** | **13** |

**Re-parenting alone causes two outright packing regressions** — trees that
packed before the slice and do not after — and both are configurations where it
invented a flap. Removing the orphan eliminates both and additionally rescues
two configurations that packed under neither other arm (`fish` v128/p0.3,
`insect` v96/p0.5). Only `insect` at the serve default fails in all three arms.

> A draft of this table claimed **three** regressions, the third being `insect`
> v128/p0.6. That measurement was taken before §2.6's rounding was removed, and
> the row does not reproduce without it: at `do_round=False` the config packs in
> all three arms. The rounding was load-bearing for a *packing* outcome, which
> is a sharper argument for dropping it than §2.6 makes on reach alone — and a
> reminder that any number in this document measured under the old arithmetic
> has to be re-taken rather than carried over.

This is the risk the design was most exposed to (§7). The first draft measured
five subjects at one configuration, found no regression, and concluded the
operation makes trees *easier* to pack. The direction is right — a shared hub
is the template shape, which is what packs attempt-0 — but the conclusion was
drawn from a sample that structurally excluded the failure mode, because at
voxel 64 / prune 0.30 only `fish` strands a junction and `fish` packs anyway.

The rescues are **not** claimed as a general result. They bound the risk; they
are not a feature.

### 2.6.3 It packs — and the search then refuses to compile it

§2.6.2 measures the **compiler**. The extractor does not hand every tree to the
compiler; `structural_prefilter` (`mesh_to_tree.py:1357`) runs first, on the
tree `to_metric_tree` returns (`:1345`), and a rejected candidate is never
gated and never compiled. §4.6 puts the operation *inside* `to_metric_tree`, so
the prefilter judges the re-parented tree — and one of its two terms is
exactly the quantity this operation moves.

The LCA hub is usually the root, and every pair moved onto it adds a child:

| | configs |
|---|---|
| root degree rises | **40/50** |
| root degree ends above `MAX_ROOT_CHILDREN = 4` | **15/50** |
| `structural_prefilter` flips **ACCEPT → REJECT** | **3/50** |
| gate verdict changes | 12/50 |

The leaf-count term never moves (the leaf set is invariant, §2.6.1), so all
three flips are root degree alone:

| config | root | leaves | packs after the operation? |
|---|---|---|---|
| `insect` v96/p0.5 | 3 → **6** | 8 → 8 | ✅ — and it is one of §2.6.2's two **rescues** |
| `insect` v96/p0.6 | 3 → **5** | 6 → 6 | ✅ |
| `insect` v128/p0.6 | 3 → **5** | 5 → 5 | ✅ |

**All three compile. All three would be discarded before compiling.** And they
are not scattered — they are every prefilter-accepted `insect` configuration
there is:

| subject | prefilter-accepted configs, before → after |
|---|---|
| bird | 6 → 6 |
| fish | 2 → 2 |
| humanoid | 11 → 11 |
| quadruped | 5 → 5 |
| **insect** | **3 → 0** |

`insect` is the subject that fails at the serve default in all three arms
(§2.8) and whose *only* packing wins in this whole document are at v96/p0.5 and
v128/p0.3–0.6. Wired as drafted, the slice would make `insect` packable and
simultaneously make the search unable to reach it. That is a product
regression, not a disclosure item, and §4.6 resolves it.

Three things make the resolution evidence-led rather than a convenience:

1. **The guard is wrong on every case it newly rejects** — 3/3 compile. This
   corpus cannot give a cleaner falsification than that.
2. **The repo already falsified the rule at exactly these degrees.**
   `tree_contract.py:23-59` records the committed packability control
   (`fixtures/s5_engine_repair_evidence.json → packability_control`), the
   compile rate of a k-leaf star — which *is* a k-child root — under length
   jitter: `k=5` 3/3 at 0% and 16/20 at 30%; `k=6` 3/3 and 15/20; `k=8` 3/3 and
   7/20. It also records a captured live agent quoting the rule verbatim to
   **refuse** a dog candidate that was then served 6/6. The conclusion drawn
   there is the one this section needs: root degree is *reported as an
   observation*, not enforced as doctrine.
3. **`structural_admission` already declines to look at root degree** and says
   why in its docstring (`mesh_to_tree.py:1611`): *"Coding a root-degree cap
   here would freeze a refuted number into a second place."*

> **The codebase named this trigger in advance.** `mesh_to_tree.py:985-990`
> explains why prefilter root>4 rejects are *not* routed to the phase-3
> normalizer: *"no committed fixture anywhere has root > 4, and there is no
> evidence live extraction produces one — so that branch would be built blind
> and is left out until such a case is measured."* Half of that is already
> stale at HEAD — `quadruped` at voxel 64 emits a 6-child root at three prunes
> and a 5-child root at the fourth, though those candidates are rejected on
> leaf count first, so the branch has still never fired. This operation takes
> root > 4 to 15/50 and makes it decisive on 3. The stated precondition —
> *"until such a case is measured"* — is now met, which is why §4.6 decides it
> here instead of deferring it again.

**A corollary for §2.6.1's invariant.** "The leaf set is unchanged in 50/50"
is true and load-bearing, but it does **not** mean the search is unchanged.
Admission moves on 3 configurations and the gate verdict on 12, with the leaf
set identical throughout. `benchmark_subjects.served_leaves` will therefore
look untouched while what actually got served differs — so the phase-B gate
(§6.19 `pack-rate-no-regression`) must be a *pack-rate* measurement through the search, not a leaf-count
diff.

### 2.7 The slice also leaves the graph symmetric — but read that narrowly

The acceptance bar chosen for this work was congruent tips. The operation also
clears a formally stronger bar, and the reason it does is worth stating
precisely, because it is nearly definitional rather than a discovery.

Define σ: swap the two members of each declared pair, fix every other node.
σ is a **tree automorphism** — the tree literally maps onto itself — when

```
parent(σ(x)) == σ(parent(x))   and   length(σ(x)) == length(x)   for every x
```

| | configs |
|---|---|
| σ is already an automorphism | 4/50 |
| σ is an automorphism **after this slice** | **48/50** |

The two exceptions are the degenerate two-node `fish` of §2.6, which §4.3
refuses.

**Read that narrowly — it is close to a tautology, and stating it as a
discovery would be dishonest.** The two automorphism conditions reduce to
"every declared pair is a sibling pair with equal length", which is exactly
what the re-parent plus the shipped equalization enforce *by construction*. So
48/50 is a consistency check confirming the implementation does what it says,
not evidence about anatomy. What it legitimately retires is the *separate
slice* the original §8 proposed: there is nothing left for a "make the graph
symmetric" slice to do, because every pair the operation accepts is a pair of
**leaves** — the one corpus case where a member is not a leaf is the degenerate
two-node `fish`, and §4.3 refuses it rather than moving a subtree — and no
interior node's parent or length is ever rewritten.

Two limits of this notion of symmetry, both structural: σ fixes every interior
node, so it cannot detect asymmetry in an off-spine interior node at all; and
it is a statement about the *tree*, which §2.8 measures to be insufficient for
the thing a user looks at.

**What an automorphism still does not buy, and neither does this slice:**

1. **Unpaired lateral leaves.** A limb with no mirror twin that sits *off* the
   mirror plane. σ fixes it, so the map stays an automorphism while the model
   stays visibly one-sided. Measured across the corpus: **3 leaves total**,
   in 3 of 50 configurations (2 `fish`, 1 `humanoid`), one leaf each. Unpaired
   leaves are otherwise common — up to 6 on `bird` — but they sit *on* the
   plane, which is what a head, tail or dorsal fin is supposed to do.
   `_unpaired_laterals` already detects the off-plane case. Removing one would
   delete a limb the mesh has; adding a twin would invent one it does not.
   Neither is an improvement, so this is left alone deliberately.

   > That count is measured on the **skeleton graph**, which this operation
   > does not touch — so it is a count of the laterals the *extractor*
   > produced, and it would be blind to any the operation produced itself.
   > That mattered: without §2.6.1's orphan removal the operation invented two
   > more (`fish` v96/p0.3, off-plane by 0.229 and 0.191) and this number would
   > have stayed at 3 while the real figure was 5. With removal the leaf set is
   > invariant, so the skeleton count is the metric-tree count and 3 is right.

2. **Crease-pattern symmetry — measured, and NOT delivered.** See §2.8. This
   is the gap between "the tree is symmetric" and "the model looks symmetric",
   and it is the one a user actually sees.

### 2.8 A symmetric tree does NOT give a symmetric crease pattern

> ⚠ **SUPERSEDED MEASUREMENT LAYER, 2026-08-04.** The structural finding this
> section establishes — a symmetric tree does not give a symmetric crease
> pattern — stands. The *instrument* it was measured with does not: every
> `vertex_residual_max` / crease-match-fraction number below came from
> `probe_cp_symmetry.cp_symmetry`, which read vertices only and ignored M/V
> assignment (the same two defects `docs/superpowers/specs/
> 2026-08-04-cp-mirror-metric-design.md` §1.1 documents). That function is
> **deleted**; its citation below to `probe_cp_symmetry.py:103-105` no longer
> resolves to that logic (the directed-Hausdorff computation it named now
> lives in `cp_mirror._directed_hausdorff`, cite by name, not line — this
> project's own recorded lesson is that a citation goes stale by being
> fixed). `fixtures/cp_symmetry_evidence.json`'s columns changed too:
> `vertex_residual_max` and `crease_match_frac` are gone, replaced by
> `cp_mirror.mirror_verdict`'s `symmetric` / `residual` / `is_bijection` /
> `mv_swapped` / `mv_mismatched`. Two concrete numbers below are now stale in
> a way worth flagging explicitly: the §2.8 table's `fish (re-parent only)`
> reading of `3.73e-01` is, under the current metric and fixture,
> **0.114566**, and `quadruped (re-parent only)`'s `3.86e-01` is **0.201999**
> (both `residual`, both still `symmetric: False`, both still failing on
> geometry — `is_bijection` False — so the qualitative story this section
> tells is unchanged). The raw / re-parent-only / +orphan-removal column
> split below is *also* moot on the current fixture: `mesh_to_tree` has
> reconciled unconditionally since `8894d95`, so all three arms now read
> identically (see `probe_cp_symmetry.py`'s own staleness banner). Treat
> everything below as a historical record of how the finding was first
> established, not as current numbers to cite forward — cite
> `2026-08-04-cp-mirror-metric-design.md` and the evidence it re-blessed
> instead.

Symmetry reaches the geometry at **two** sites, and the next slice needs both
named correctly. `apply_symmetry` (`TreemakerWrapper.cpp:399`) attaches a
`tmConditionNodesPaired` to the pair and hands it to the optimizer
(`:413`). Separately, the post-optimization active-path projection adds two
linear rows per pair — `b.x - a.y = 0`, `b.y - a.x = 0` — pinning **paired leaf
positions** to reflect about `y = x` through `(0.5, 0.5)` (`:1139`, and its own
comment says why: *"free projection would drift it asymmetric"*). An earlier
draft attributed the linear rows to `apply_symmetry`; they belong to the
projection, and only paired leaves appear in either. Nothing constrains
anything else. Measured by reflecting every `.fold` vertex about that axis and
taking the distance to the nearest actual vertex:

| tree | role | vertex residual | creases matched |
|---|---|---|---|
| star-4 + pairs | positive control | **0.00e+00** | 1.000 |
| `HSHAPE` | positive control | **0.00e+00** | 1.000 |
| `TEMPLATE_QUADRUPED` | positive control | **0.00e+00** | 1.000 |
| lopsided-5, no pairs | negative control | 1.83e-01 | 0.639 |
| **`QUAD`, no pairs** | **negative control** | **0.00e+00** | **1.000** |
| | | | |
All three arms at the serve default (voxel 64 / prune 0.30), from
`fixtures/cp_symmetry_evidence.json`:

| subject | raw | re-parent only | + orphan removal |
|---|---|---|---|
| `bird` (0 moved, 0 dropped) | 3.19e-01 / 0.485 | 3.19e-01 / 0.485 | 3.19e-01 / 0.485 |
| `humanoid` (1 moved, 0 dropped) | 8.90e-02 / 0.854 | **0.00e+00 / 1.000** | **0.00e+00 / 1.000** |
| `fish` (2 moved, 1 dropped) | 1.04e-01 / 0.642 | **3.73e-01 / 0.521** | 1.15e-01 / **0.748** |
| `quadruped` (2 moved, 0 dropped) | did not pack | 3.86e-01 / 0.707 | 3.86e-01 / 0.707 |
| `insect` (2 moved, 0 dropped) | did not pack | did not pack | did not pack |

> **One negative control FAILS, and it bounds this section — but in one
> direction only, and getting that direction right is what makes the rest
> usable.** `QUAD` is a 3-leaf caterpillar with root-to-tip reaches 0.5 / 0.9 /
> 1.3 — unambiguously asymmetric — and it scores a *perfect* 0.0 with 100% of
> creases matched, identical to the positive controls.
>
> An earlier draft explained this as leaf vertices parking at the square's
> corners, "and a corner set like {(0,0),(1,0),(0,1)} maps onto itself under
> `y = x`". **That explanation is measurably false.** `QUAD`'s compiled pattern
> has 13 vertices and occupies exactly **one** of the four bounding-box
> corners. Three vertices sit on the diagonal and the other ten pair up exactly
> under `y = x` — (0.031213, 0.357143) ↔ (0.357143, 0.031213), (0.056184,
> 0.642857) ↔ (0.642857, 0.056184), (0.087397, 1.0) ↔ (1.0, 0.087397),
> (0.222703, 0.628304) ↔ (0.628304, 0.222703), (0.340898, 0.746499) ↔
> (0.746499, 0.340898). The invariance comes from that pairing, not from corner
> occupancy. The real mechanism is broader and less tidy: **a small packing can
> simply land in a configuration that happens to be globally `y = x`-invariant**,
> whatever tree produced it.
>
> > A note on how that number was checked, because it nearly went in wrong.
> > A first count said *zero* corners. The `.fold` writer quantizes coordinates
> > to 9 dp and stores the origin as `(1e-9, 1e-9)`, so a corner test with a
> > 1e-9 tolerance rejects the vertex that *is* the corner, and a `%.6f` print
> > displays it as `0.000000` while the test disagrees. §2.6's lesson —
> > **do not round a measurement whose purpose is to detect rounding** —
> > generalizes: do not choose a tolerance at the scale of the thing you are
> > measuring.
>
> **The direction is what matters.** `vertex_residual_max` is a one-sided
> Hausdorff distance from `reflect(V)` to `V` — for each reflected vertex, the
> distance to the *nearest* actual vertex (`probe_cp_symmetry.py:103-105`). It is
> 0 exactly when `reflect(V) ⊆ V`. Coincidental invariance can only *add*
> members to `V` that happen to complete the inclusion, so it can only push the
> value **toward** 0. It cannot manufacture a vertex whose mirror image is far
> from every actual vertex. So:
>
> * a **≈0.0** reading on a small tree is uninformative — it may be degeneracy;
> * a **positive** reading is an existential witness that degeneracy cannot
>   fabricate.
>
> An earlier draft of this document wrote that the metric is "unreliable in
> both directions" and inherited that phrasing from the probe. It is not
> supported by any measured mechanism, and it is the sentence that made the
> `bird` reading below look like it needed rescuing.
>
> **Applied consistently, this costs more than `QUAD`.** Every 0.0 in the
> table above is on a tree of 3–6 leaves: the three positive controls (4, 4 and
> 6) and `humanoid` (5). None of them is *proof* of symmetry. That does not
> make them worthless — a positive control that came out asymmetric would still
> have falsified the whole approach — but the second bullet below is qualified
> accordingly, and an earlier draft left it unqualified while qualifying a
> bullet that did not need it.

With that caveat carried, three readings follow. The first survives it on the
**direction** argument — not, as an earlier draft claimed, because "`bird` has
enough leaves". `bird` at the serve default has **4** leaves, half the probe's
own cutoff and one more than `QUAD` itself; the claim contradicted a count this
same section prints twenty lines later.

* **`bird` is the proof.** Its tree at the serve default has both members of
  its one pair as equal-length siblings, needs zero re-parents, and makes σ an
  automorphism — and its crease pattern is still **0.319** off with barely half
  its creases matched. That is a positive reading, so the degeneracy artifact
  cannot have produced it, and the witness is concrete: vertex
  (0.30343, 1.0) reflects to (1.0, 0.30343), whose nearest actual vertex is
  0.3189 away, with 14 of 18 vertices unmatched. It is also not a solver-basin
  accident, and that is a committed control rather than an assertion:
  `probe_cp_symmetry.py` re-emits the same tree in three topologically valid
  node orders and records a hash of each packing. Two *distinct* packings come
  out (`ed40a2ed207f`, `86302279e7e7` ×2) with **byte-identical** symmetry
  statistics — 3.19e-01 max, 6.78e-02 median, 0.485 matched, every time. Node
  order is the documented basin lever on this packer (§2.6.1), so this is the
  control that matters. **Tree symmetry is necessary but not sufficient.**

  (Read "symmetric" narrowly here, per §2.7: σ is a *graph* automorphism, and
  it fixes `bird`'s two unpaired leaves, which have unequal lengths 0.4 and
  0.158. They sit *on* the mirror plane — `_unpaired_laterals` finds no lateral
  orphan on `bird` — so a mirror-symmetric packing is available. The packer
  simply is not required to find it, which is the point.)
* **The re-parent can deliver exact CP symmetry — on a 5-leaf tree, so read it
  as suggestive.** `humanoid` reaches **0.00e+00** with a 100% crease match.
  (An earlier draft reported 2.83e-09 here; that residue was the 6-dp rounding
  §2.6 removed.) Three things keep this from being clean: 5 leaves is inside
  the range where a 0.0 may be degeneracy; the pattern also *shrinks*, 48
  creases → 38 and 27 vertices → 21, and a simpler pattern is easier to be
  symmetric; and the direction of the artifact is exactly the one that would
  manufacture this result. It is the best evidence in the table that the
  operation *can* help the crease pattern, and it is not proof.
* **The `fish` regression was the invented flap, not the re-parent.** Re-parent
  only: 0.104 → 0.373. Re-parent *with* §2.6.1's orphan removal: 0.104 → 0.115
  with the crease match *improving* on raw, 0.642 → 0.748, and half the
  vertices acquiring exact mirror twins (median residual 0.000). The mechanism
  is the one this section already names — an unconstrained unpaired leaf — and
  the operation was manufacturing one. Counts at the serve default put `fish`
  at 3 of 7 leaves unpaired; re-parenting alone made it 4 of 8.

**The mechanism is unconstrained unpaired leaves.** A leaf that is neither in a
declared pair nor on the symmetry axis is free, and the packer has no symmetry
preference. Counts at the serve default: `bird` 2 of 4 leaves unpaired, `fish`
3 of 7, `quadruped` 5 of 9, `humanoid` 1 of 5, `insect` 1 of 9. It is *not* a
clean function of that count — `TEMPLATE_QUADRUPED` has 2 unpaired leaves and
is exactly symmetric — because a symmetric tree always *has* a symmetric
optimum; the solver is simply not required to find it.

**The lever is NOT the Combo binding.** `set_node_at` / `set_node_on_x` /
`set_node_on_y` over `tmConditionNodeCombo` (committed `e0761bc`) pin a node to
a fixed **coordinate** — a point, or the line `x = const` / `y = const`. They
cannot express *"lies on `y = x`"*, and faking it by pinning an exact point on
the diagonal over-constrains the node and would cost scale.

The right class is **`tmConditionNodeSymmetric`** — Lang's own, already
vendored, *"A condition for fixing a tmNode to the symmetry line"*
(`tmConditionNodeSymmetric.h:29`) — and it has **no binding**. Slice 2 therefore
needs a small additive wrapper method following the exact pattern of
`set_node_at`, plus a `.so` rebuild. **That is the next slice, and this one does
not substitute for it.**

Two things slice 2 must answer that this spec does not:

* **Which unpaired leaves belong on the axis?** `_unpaired_laterals` names the
  ones that are *off* the mirror plane (3 corpus-wide — those must NOT be
  pinned). The complement is the pin candidate set, but "near the mirror plane
  in mesh space" is not the same claim as "belongs on the diagonal in paper
  space", and that inference needs its own justification.
* **Does pinning cost scale?** Every added constraint can only lower the design
  scale, which is the primary objective (CLAUDE.md §1.1 consequence 4). A CP
  that is symmetric but folds smaller is a trade to argue, not a free win.

Two further caveats on the metric, on top of the `QUAD` one above. **The
crease-match fraction is the weaker of the two numbers, and unlike the vertex
residual its error really does run in both directions.** It maps each reflected
vertex to its nearest actual vertex, so collapsing several reflected vertices
onto one makes the reflected crease a self-loop, which is skipped and lowers the
fraction (overstating asymmetry), while a reflected vertex far from any real one
still gets a nearest neighbour and can spuriously complete a match (understating
it). An earlier draft claimed the fraction "understates rather than overstates
asymmetry"; that is not established. This is the reason the vertex residual is
the primary signal — it is one-sided, so a positive value is a witness, which is
exactly the property the `bird` reading rests on. And `insect` does not pack in
**any** of the three arms at the serve
default, so it contributes no CP row at all: at voxel 64 / prune 0.30 the
operation strands nothing on `insect`, so removal is a no-op there and cannot
rescue it. (`insect` does pack with removal at v96/p0.5, v128/p0.3-0.6 —
§2.6.2 — so those are the rows a follow-up should collect. A draft of this
sentence claimed the serve-default row was rescued, which is false.)

**Orphan removal is not uniformly better on this metric, and the pack win must
not be allowed to imply that it is.** It is a large improvement on `fish`
(0.373 → 0.115, crease match 0.521 → 0.748, and better than raw), neutral on
`bird`, `humanoid` and `quadruped` — and at `insect` v128/p0.6, which packs in
all three arms, the removal arm measures **0.294 against raw's 0.116**, i.e.
2.5× worse. The first draft carried an honest "and it can make it worse"
bullet; the evidence for it moved from `fish` to `insect`, but it did not go
away, and this section keeps it.

---

## 3. Prior art (CLAUDE.md §0)

| Source | What it does | Adapted / rejected |
|---|---|---|
| [Zheng et al., *Skeleton-Intrinsic Symmetrization of Shapes*, EG 2015](https://www.cs.sfu.ca/~haoz/pubs/zheng_eg15_intsym.pdf) | Extract the backbone, establish correspondence **between junction nodes**, symmetrize the skeleton, discard branches with no counterpart. | **Adapted.** Their central move — correspondence at the *junction* level, not the leaf level — is exactly §4.1. Their discard rule is not adopted: we refuse rather than delete (§4.3), because a dropped leaf is a dropped limb. |
| [Baran & Popović, *Automatic Rigging and Animation of 3D Characters* (Pinocchio), SIGGRAPH 2007](https://www.cs.toronto.edu/~jacobson/seminar/baran-and-popovic-2007.pdf) | Embed a **known symmetric template skeleton** into a mesh rather than extracting a free-form one. | **Rejected as the primary mechanism**, kept as the existing fallback. Guarantees symmetry but only for body plans we have templates for; the whole point of mesh extraction is to handle a tardigrade we never templated. |
| Curve-skeleton **junction/branch-point regularization** — the standard remedy for exactly the diagnosed defect (Au et al., *Skeleton Extraction by Mesh Contraction*, SIGGRAPH 2008, and the node-merge / clean-up passes `skeletor` exposes downstream of it) | Merge spurious nearby branch points **in the skeleton**, before a metric tree is ever built, so the shoulder is one node. | **Considered and not adopted as the primary fix, for a concrete reason.** Merging two spine nodes contracts the edge between them, which shortens the root-to-tip path of *everything distal* to the junction — every limb further down the body gets shorter, including limbs not in any pair. The LCA re-parent is the same correction expressed so that it is **exactly reach-preserving** (§4.2): the flap's own edge absorbs the distance instead of the rest of the anatomy paying for it. Fixing it at source remains the better long-term answer if the extractor is ever reworked; that is open question 4, and it sits alongside question 3. Note also that it would make orphan removal (§2.6.1) unnecessary rather than merely safe, since a junction that was never split cannot be stranded. |
| `mcp_harness/body_plans.py` (this repo) | All four templates are hub-symmetric by construction: every declared pair is a sibling pair off a shared hub. | **Adopted as the target shape.** The operation makes an extracted tree look like a template, which is the shape already measured to pack. |
| `mesh_report.py:214` (this repo) | The served report already tells the agent: *"STRUCTURE — node list order, hub grouping, sliver topology — is extraction bookkeeping, NOT a measurement: reworking it is the sanctioned lever **when packing fails**."* | **Adopted, with its scope corrected — see below.** Hub grouping is explicitly not a measurement, which is the licence this slice needs. But the sentence scopes rework to *packing failure*, and this slice reworks hub grouping on trees that pack fine. §4.7 must therefore justify the rework on its own terms (removing a contradiction, not buying a pack) and the report sentence should be widened to match, or the two will contradict each other in the same document the agent reads. |
| Data reconciliation / gross-error detection | Adjust conflicting observations by orthogonal projection onto the constraint. | Already adopted by the predecessor slice for lengths; this slice adds the topological precondition that makes the projection meaningful. |

---

## 4. Design

### 4.1 The operation

One pure function on `(nodes, pairs)`:

```
keep = leaves(nodes) | {every pair member}      # the anatomy that exists NOW

for each declared pair (a, b):
    ja, jb = parent(a), parent(b)
    if ja is None or jb is None:      refuse   # a member is the root
    if a is an ancestor of b, or b of a: refuse
    if ja == jb:                      skip     # already siblings
    h = LCA(ja, jb)
    length(a) += tree_dist(ja, h)
    length(b) += tree_dist(jb, h)
    parent(a) = parent(b) = h

# clean up after ourselves -- see 2.6.1
while some node x is childless, not the root, and not in `keep`:
    delete x
```

No rounding: the lengths arriving from `to_metric_tree` are already 6-dp, and
re-rounding the sum is the only thing that stops §4.2 being exact.

The shipped `reconcile_pairs` then equalizes the two lengths as it already
does. This slice does not change that function's behaviour.

The removal loop is not an optimization or a tidy-up — it is what makes the
operation's contract *"the leaf set is invariant"* true, and §2.6.1 measures
what it costs to omit it (12 invented flaps, two packing regressions). It
**cascades** to a fixpoint because deleting one node can empty its parent (17
nodes removed across the corpus for 12 invented flaps; deepest 2 levels, and
§6.12 shows a 3-level case a two-pass implementation would miss). It can never
touch anatomy, because everything that was a leaf before — and every pair
member, including a *refused* pair's — is in `keep`. And it is reach-preserving
for the same reason the re-parent is: nothing hangs below a childless node, so
no surviving path can change.

**`keep` is computed once, before any pair moves, and that is the load-bearing
detail.** Removal itself is order-insensitive — running it after every pair
gives the identical result to running it once at the end, because a childless
node lies on no other node's root path and so deleting it cannot change any
LCA, any reach, or any later refusal. (A draft of this paragraph justified
"once at the end" as order protection; measurement says the two are equivalent,
so that was not the reason.) What is *not* order-insensitive is `keep`:
recompute it inside the loop and a junction stranded by an earlier pair is a
leaf by the time the later pair looks, so `keep` protects the very node the
pass exists to delete, and removal drops nothing at all (§6.11). Running once
at the end is specified because it is the simplest form that cannot get this
wrong, not because per-pair would give a different answer.

### 4.2 Why re-parenting is reach-preserving

Moving a leaf to an ancestor `h` and adding `tree_dist(j, h)` to its edge leaves
its root-to-tip distance **exactly** unchanged:

```
P_new = P_h + (length + dist(j, h)) = P_h + dist(j, h) + length = P_j + length = P_old
```

So the re-parent on its own changes **nothing observable about the model**. It
is not a repair; it is a change of coordinates. All it does is establish the
shared prefix `P_h` that makes equalizing the two lengths equivalent to
equalizing the two reaches — which is what the predecessor slice already
assumed and, for 83 pairs, was wrong to.

Five consequences worth stating because they remove whole classes of design
question — and the fourth is the one an earlier draft got wrong:

* **Total.** Edges only ever grow, so no length can go negative and no case
  needs a fallback. The LCA always exists.
* **Uniform.** The ancestor case (68/83) has `LCA == ja`, so only the deeper
  flap moves. The cousin case (13/83) moves both. Same rule.
* **Pairs are independent.** Only *leaves* move; no interior node's parent or
  length is ever rewritten. So one pair's re-parenting cannot change another
  pair's LCA, and there is no ordering question and no conflict resolution.
  Removal inherits the same independence for the same reason — a childless node
  is on no other node's root path — so *when* it runs does not matter. The one
  thing that does is when `keep` is sampled (§4.1).
* **The leaf set is invariant, but only because removal makes it so.** "Only
  leaves move" is true of *parent pointers* and was mistaken in an earlier
  draft for "the set of leaves is unchanged". It is not the same statement: a
  node that keeps its parent and its length can still change from interior to
  leaf, which is a change of *kind*, and in TreeMaker a change of kind is a
  change of anatomy. §2.6.1.
* **Pure data.** No mesh, no numpy, no engine — testable against hand-written
  trees, the same discipline as `pair_reconcile.py`, `free_paper.py` and
  `flap_fill.py`.

### 4.3 Refusals

Two, both structural, neither a tunable:

| condition | why | fires on the measured corpus |
|---|---|---|
| a member is the root | the root has no parent, so there is no junction to reconcile | **2/117** — the degenerate two-node `fish` of §2.6 |
| one member is an ancestor of the other | there is no hub that leaves *both* as leaves; such a pair is not a bilateral pair at all | **0/117** |

The second guard never fires today and is kept anyway: it is a structural
impossibility, not a tuning choice, and the operation would silently produce a
nonsense tree without it. Its test is written against a hand-built tree, not
against the corpus.

A refused pair keeps both original lengths and is reported, and its declared
pairing is **withdrawn** from `kept` — exactly as `reconcile_pairs`'s existing
`"unresolvable"` action does (`pair_reconcile.py:106`: *"the pair is dropped"*).

*An earlier draft of this sentence said the pairing was kept, and cited that
same precedent for it. It was wrong in both halves, and phase A's review filed
the divergence twice as a HIGH code defect before the prose was identified as
the broken side.* Carrying a refused pairing forward hands `reconcile_pairs` a
pair it will equalize: on the degenerate two-node `fish` that gives the **root**
a phantom length and halves the only real flap, breaking §6.6
`refuse-root-member` ("both lengths survive"); on the ancestor refusal it
rewrites an interior node's length, breaking §6.9 `interior-untouched`. Both
refusal conditions are also precisely what `tree_contract.check` rejects
(`tree_contract.py:232-235`, *"names N, which is not a LEAF"*), so withdrawing
the pairing drops an **invalid** pair rather than losing a valid one.

### 4.4 There is no cap, and that is deliberate

The obvious knob is a ceiling on how far a junction may move — the design's
first draft had one. It is **wrong**, and rejecting it is the point of this
section.

A large junction separation means the *extractor* was badly wrong. But the fix
direction is unchanged: both limbs of a genuine bilateral pair *should* emerge
from one point, and the further apart the extractor put them, the more the
model needs the fix. A cap would refuse exactly the worst cases.

The pairs that genuinely should not be reconciled are **false pairings**, and
that is a different test — geometric, at detection time, not here. §2.2's
straddle signal is the candidate, and §2.2's caveat is why it is not in this
slice.

This also avoids inventing a second unanchored constant. The predecessor's
`MAX_PAIR_GAP` is still unwired for precisely this reason, and its recorded
lesson applies verbatim: *a length gap alone cannot separate a noisy real pair
from a wrong pairing.*

The real cost of "no cap" is packability, and that is a measurement (§2.6.2,
§6.19 `pack-rate-no-regression`), not a threshold. Its cost in *admission* is §2.6.3, and that one is
resolved in §4.6 rather than measured and accepted.

### 4.5 Orphaned junctions: subdivisions stay, stranded ones go

Losing a child does one of two things to a junction, and the difference is the
whole of §2.6.1:

| after the move the junction has… | what it is | what we do |
|---|---|---|
| ≥ 1 remaining child | a degree-2 interior node — a subdivided edge, metric identical | **leave it** |
| no children | **degree 1, i.e. a LEAF — a flap nobody measured** | **delete it** |

An earlier draft asserted the first row for *both* cases, and justified leaving
subdivisions alone by saying that contracting one *"would renumber every node,
and node list order is load-bearing for packing"*. **That justification is
void**: renumbering and reordering are different edits, and §2.6.1 measures
them apart — renumbering every id leaves the compiled `.fold` byte-identical
5/5, while reordering the list changes it 5/5. Contraction was being refused
for a cost it does not have.

The correct reason to leave subdivisions is simpler, and it is a scope
argument rather than a safety one. **A degree-2 interior node is not the
defect.** It is metrically inert — `QUAD` in `tests/cases.py` carries one
(node 2 has parent 1 and the single child 5) and is a committed geometry
golden, so the shape is proven to compile — and contracting it would cost the
*same* list-index churn that deleting a stranded junction costs (§2.6.1),
while fixing nothing. This slice makes exactly the edits that remove an
invented flap. Contraction removes none, so it is not in scope.

The second row *is* the defect: a childless junction is a leaf, and a leaf is a
flap. Deleting it is reach-preserving by construction, it restores the leaf-set
invariant (50/50), and its cost — re-indexing the survivors — is bounded by
direct compile measurement rather than by argument (§2.6.2, §7).

> **A consequence worth stating, because it changes an open question.** With
> "contraction renumbers" removed, nothing in this document objects to
> contraction *on node-order grounds*. Open question 4 — fixing the split
> junction at source, in skeletonization — therefore rests on its remaining
> objection alone: merging two branch points shortens the root-to-tip path of
> everything distal to them, while the LCA re-parent preserves reach exactly
> (§3). That objection is untouched and still stands, but it is now the *only*
> one, and it is about metric fidelity rather than about bookkeeping.

### 4.6 Where it lives

`mcp_harness/pair_reconcile.py`, called from `to_metric_tree` immediately
**before** the existing `reconcile_pairs` — the same place, for the same
reason the predecessor gives: it is where lengths and pairs first coexist, so
no downstream consumer (engine, `tree_contract`, scorecard, feasibility gate)
can ever observe an unreconciled tree.

Evidence rides out on the existing `_last_pair_evidence` channel, extended with
the re-parent and removal records rather than given a second one.

**One rule covers both warnings below.** Putting the operation inside
`to_metric_tree` is right — it is the only place that guarantees nothing
downstream sees an unreconciled tree — but it means every quantity whose
*meaning* is "what the extractor produced" is now measured on a tree the
extractor did not produce. Two such quantities exist, and both must be
**sampled before the operation runs** and carried forward:

| quantity | why it is an extractor measurement | measured contamination |
|---|---|---|
| `pair_gap_max` | the predecessor's only mitigation for "this hides a real extractor bug" | inflates on **37/50** |
| `structural_prefilter`'s root-degree term | an overloaded root means skeletonization dumped every limb on one node | flips ACCEPT→REJECT on **3/50**, `insect` 3 → 0 |

Nothing else qualifies. The prefilter's *leaf-count* term is deliberately left
on the post-operation tree: the leaf set is invariant (50/50), so it reads the
same either way, and pinning it to the pre-operation tree would hide a future
removal defect — which is the exact failure §2.6.1 exists to prevent.

> **⚠ Running before `reconcile_pairs` breaks `pair_gap_max` unless the gap is
> captured first.** `reconcile_pairs` records `gap = relative_gap(La, Lb)` on
> the lengths it is handed. Today that is pure extractor noise, which is the
> *entire* mitigation the predecessor spec offers for its risk R3 — *"it hides
> a real extractor bug… `pair_gap_max` records the pre-reconciliation gap, so
> the noise stays visible after the symptom is fixed."* After the re-parent
> runs first, the lengths it is handed already carry the junction distance, and
> the number stops being a measurement of the extractor. Measured: it inflates
> on **37 of 50** configurations (`fish` v128/p0.3: 0.2538 → 0.7298; `quadruped`
> v64/p0.3: 0.2790 → 0.4969).
>
> So the gap must be sampled **before** the re-parent and carried into the
> evidence, not recomputed after it. `test_scorecard_reports_the_pre_reconciliation_gap`
> will not catch this — it runs off a fixed evidence fixture and stays green
> while the production number changes meaning underneath it.

> **⚠ `structural_prefilter`'s root-degree term must be evaluated on the
> pre-operation tree, or `insect` loses every admissible candidate.** §2.6.3
> is the measurement: root degree rises in 40/50 configurations, and on three
> of them it crosses `MAX_ROOT_CHILDREN = 4` and flips the prefilter to
> reject — all three of which compile successfully, and which between them are
> all of `insect`'s prefilter-accepted configurations.
>
> **The decision: `to_metric_tree` records the pre-operation root degree on
> `_last_pair_evidence`, and the single production call site
> (`mesh_to_tree.py:1357`) passes it in.** `structural_prefilter` gains one
> keyword-only parameter, `root_children=None`, which supplies the *counted*
> value; when it is `None` the function counts the tree it was given, exactly
> as today. The cap (`max_root_children`) is not touched.
>
> The blast radius is one line, and that is checkable rather than hopeful:
> `structural_prefilter` has exactly **one** production caller and **six**
> direct test calls (`test_leaf_admission.py:82,189`,
> `test_auto_mesh_to_tree.py:35,39,43,48`), all of which pass `nodes`
> positionally and nothing else. A keyword-only parameter with a `None` default
> cannot reach them.
>
> Phrasing matters here. `max_root_children=MAX_ROOT_CHILDREN + n_added` would
> be arithmetically identical and is the smaller diff, and it is still the
> wrong shape: it reads as *"we raised the cap"*, which is the claim this
> design is careful **not** to make. Overriding the count reads as *"we
> measured the extractor's tree"*, which is what actually happens.
>
> Three alternatives were considered and rejected:
>
> * **Accept the rejections.** This is the status quo of the first draft and it
>   is the one option measurement rules out: it costs `insect` all three of its
>   candidates, on the subject the operation exists to help.
> * **Raise `MAX_ROOT_CHILDREN`.** It would change admission for trees that
>   never went through this operation, on no evidence gathered here. Out of
>   scope, and it is the "freeze a refuted number into a second place" move
>   `structural_admission` warns against — in the opposite direction.
> * **Route root>4 prefilter rejects to the phase-3 normalizer**, the branch
>   `mesh_to_tree.py:985-990` left unbuilt pending exactly this evidence. It is
>   the more ambitious answer and may be the right one eventually, but it adds
>   a compile path this slice has not measured, and phase 3 exists to repair
>   *compile failures* — these candidates do not fail to compile.
>
> **What must NOT be lost: the observation.** Suppressing the *rejection* is
> not the same as suppressing the *number*, and `fish` v96/p0.3 reaches a
> 10-child root where the packability control stops at k=8. The
> post-operation root degree therefore rides out on `_last_pair_evidence` and
> is surfaced by `mesh_report` (§4.7) as an observation with its measurement
> attached — which is precisely the stance `tree_contract.py:23-59` already
> takes on root degree, and the reason it takes it.

### 4.7 Disclosure

`mesh_report._pair_reconcile_lines` gains a re-parent block. The distinction it
must carry, because the same report tells the agent to trust proportions:

> The **edge length** changes. The **re-parent** does not move the tip.

A re-parented flap's number is larger, but the re-parent on its own leaves its
tip in exactly the same place (§4.2). This is not a nudge, and it is not a
rescaling to buy a pack — it is the same measurement expressed from a different
attachment point. The report must say which hub the pair was moved onto and by
how much each edge grew.

**Two more things belong in the block, both because §4.6 suppressed a signal
and owes the agent the number instead.**

* **The hub's degree after the move**, whenever it exceeds
  `MAX_ROOT_CHILDREN`. The prefilter no longer rejects on it (§4.6), so this
  is the only place it surfaces. Report it the way `tree_contract` already
  reports root degree — as an observation with its measurement attached, not
  as a verdict — and name the k-star control (`tree_contract.py:23-59`) so the
  agent can see that k=5 and k=6 pack while k=8 degrades, and that above k=8
  there is no data at all.
* **The nodes removed**, by id, and that they were junctions the operation
  itself emptied rather than anatomy. The existing closing claim — *"Nothing
  was invented and no flap was dropped"* — is about *flaps*, and it stays
  true; an unexplained drop in node count next to it would read as a
  contradiction.

**Be precise about which step moves what, because the pipeline as a whole
does move reach.** An earlier draft wrote *"the measured reach does not
change"*, full stop. That is true of the re-parent (drift 0.0) and false of the
slice: the equalization that runs immediately after it shifts reach by up to
**0.2457** — that is reconciliation doing its job, and it is the predecessor's
disclosure to make, not this one's. The report must not let the exactness of
step one launder the displacement of step two. `_pair_reconcile_lines`'
existing closing claim — *"Nothing was invented and no flap was dropped"* —
stays true only because of §2.6.1; without orphan removal the block would be
asserting the opposite of what happened, in the document the agent is told to
trust.

### 4.8 Scorecard

`benchmark_subjects._COLS` gains **`pair_path_gap_max`** — the worst
*post*-reconciliation path gap, as a fraction of span. It sits beside
`pair_gap_max` (the worst *pre*-reconciliation **length** gap, i.e. extractor
noise — which stays that number only if §4.6's warning is honoured) and answers
the different question: *did the model actually come out symmetric?*

Expected value after this slice: `0.0` everywhere the pair was kept. ⚠
CORRECTED: an earlier revision of this line said "everywhere except a
refused pair," implying a refusal shows up as a nonzero reading. It does
not — a refused pair never reaches `kept`, so the column reads `None` for
it, never a nonzero (see `benchmark_subjects.py`'s corrected docstring and
the committed `bird` row: `pairs_expected 2 / pairs_kept 1 /
pair_path_gap_max 0.0`, not a nonzero flagging the refusal).

**What this column does and does not certify.** Equal root-to-tip path is
**necessary but not sufficient** for two flaps to be congruent in the folded
base: two leaves equidistant from the root can still sit at different tree
distances from a third leaf, and it is the full leaf-to-leaf metric that
circle packing consumes. The sufficient statement is §2.7's — σ is an
automorphism, which makes the whole metric invariant — and it is delivered by
the same operation. `pair_path_gap_max` is the cheap scalar; if one number has
to carry the claim, prefer `max |d(σx, σy) − d(x, y)|` over leaf pairs, which
is what the packer actually sees. Stated here rather than silently relying on
the weaker number.

### 4.9 The length clamp — a rescue rung, not a normalization

The re-parent grows edges, so `to_metric_tree` stops satisfying its own
docstring — *"scaled so the longest == `LONGEST_LIMB_TARGET`"* — on 22 of 50
configurations, worst 2.02× (§7). The slice introduces that: at HEAD every
configuration is at or under 0.40.

**The first draft of this section clamped unconditionally inside
`to_metric_tree`. The 45-configuration sweep falsified it.** Measured over
every configuration whose leaf set the operation changes:

| | count |
|---|---|
| clamp **rescues** — fails at `+drop`, packs clamped | **4** (all `insect` v64, *including the serve default* `v64 p0.3`) |
| clamp **regressions** — packs at `+drop`, fails clamped | **0** |
| clamp fires on a tree **that already packed** | **18** |

Eighteen of the twenty-two applications buy nothing — and they are not free.
At `humanoid` v64 the clamp (factor 0.9130) takes the compiled crease pattern
from a bit-exact mirror — residual `0.00e+00` over 21 vertices — to residual
`4.00e-01` over 31, and `humanoid` packs in **all four** arms. Crease-pattern
symmetry is what §2.8 establishes this slice is ultimately for, so spending it
on a pack that had already succeeded is exactly the wrong trade.

**The second draft made it a rescue-ladder rung.**

```
scale = LONGEST_LIMB_TARGET / longest    # only reached when the tree failed to pack
```

That draft rested on three claims. The third — *"the pack arithmetic carries
over unchanged, so no re-measurement is owed"* — is the one that mattered, and
it was wrong: the sweep's "packs" came from `draft_and_compile_full_base`, the
**full ladder**, so it could not distinguish what the clamp bought from what the
ladder was going to buy anyway. The re-measurement it declared unnecessary is
exactly the measurement that falsified it.

### 4.9.1 The grid, and what it says (measured 2026-08-03)

Run on the four `insect` v64 rescues, compiling each *(variant, scale)* cell
directly — which is attempt-0 for that node list — instead of letting the ladder
choose. Variants are `exact` plus every `order_variants` and
`placement_variants` candidate: 8 cells per scale.

`longest = 0.4217` on all four, so the clamp factor is **0.9486**. Identical
pattern on all four configurations:

| scale | cells packing | which |
|---|---|---|
| 1.0000 | 0 / 8 | — |
| 0.9800 | 0 / 8 | — |
| **0.9600** | **1 / 8** | `order:seeded_0` |
| **0.9486 ← THE CLAMP** | **0 / 8** | **—** |
| 0.9400 | 0 / 8 | — |
| 0.9200 | 0 / 8 | — |
| 0.9000 | 1 / 8 | `order:seeded_0` |
| 0.8500 | 1 / 8 | `order:seeded_2` |
| 0.8000 | 2 / 8 | **`exact:caller`**, `order:seeded_2` |

Three things follow, and the first is fatal to the specified design.

1. **The clamp factor lands in a dead band.** Nothing packs at 0.9486 — not
   attempt-0, not any order variant, not any placement seed — while 0.96 (a 4%
   shrink) and 0.90 both do. `LONGEST_LIMB_TARGET / longest` is derived from a
   *packing-regime convention*, not from this tree's geometry, so where it lands
   on the pack/fail structure is a coincidence. Here the coincidence is bad.
2. **The pack/fail structure over scale is non-monotone and pitted** — ✓ at
   0.96, ✗ at 0.9486/0.94/0.92, ✓ at 0.90/0.85/0.80. "Shrink until it fits" is
   not how this behaves, so **any single derived factor is a lottery ticket**.
   A rung must *search* a small ladder of factors, exactly as `order` searches
   restarts.
3. **The rescue it claimed was bought with jitter.** Through the real serve
   path, the clamped tree does pack — and its `frame_title` carries
   `did not pack exactly`, which `agent_loop.py:318` defines as *"the backend
   nudged your EDGE LENGTHS"*:

   | scale | serve result | via |
   |---|---|---|
   | 1.0000 | FAILED | — |
   | **0.9486 (clamp)** | packed | node-order restart **+ jitter** |
   | **0.9600** | packed | node-order restart — **no jitter** |
   | **0.8000** | packed | **attempt-0 exact** |

   So the second draft's central justification — *"it is proportion-preserving,
   which is why it may sit ahead of jitter"* — is **backwards for the factor it
   specifies**. At 0.9486 the serve still needs jitter, so the clamp adds a
   uniform shrink on top of the proportion trade it was supposed to avoid.

**This is the same error a third time**, and naming it precisely is the point:
the first draft treated the clamp as a property of the *tree*; the second as a
property of the tree crossed with the *ladder*; both times the fix was assumed
rather than measured. What the grid shows is that it is a property of the tree
crossed with the ladder crossed with **the particular factor** — and the factor
the section derives is the one value in its own neighbourhood that fails.

### 4.9.2 What a fourth attempt would have to be

Not a clamp. A **searched uniform-scale rung**: a small descending ladder of
factors (the grid's 0.96 / 0.90 / 0.85 / 0.80 is the measured shape), each
composed with the order variants, stopping at the first that packs. On this
corpus that reaches all four rescues, and at 0.96 it does so **proportion-
preserving** — one order restart, no jitter note — which is strictly better than
the shipped alternative on every axis: less shrink than the clamp, and no
proportion trade at all.

It is **not shipped here**, for three reasons that are design decisions rather
than work:

1. **It needs a new stage and an honesty rank.** `PRESERVING_STAGES` means the
   exact `(id, length)` multiset (`rescue_ladder.py:63-87`), which a uniform
   scale fails while preserving every *ratio*. `STAGE_HONESTY` is a small
   integer scale whose ordering the ladder's proportion barrier is monotone in
   and whose values are test-pinned, so inserting a rank between `order` (2) and
   `normalize` (1) is a change to load-bearing ladder semantics, not an addition
   to it.
2. **PR #70 named margin-to-cliff as a pre-ship gate** for anything that moves
   achievable scale, and this moves it in the *risky* direction: the 0.80 serve
   reaches packing scale 0.6128 against the clamp's 0.5409, and larger scale
   sits nearer tangency where 1-ULP platform differences flip outcomes. One of
   these four configurations is the serve default.
3. **The factor ladder above is fitted to four configurations of one subject.**
   Generalising it needs the other misses (`bird` v128 ×2, which no arm rescues)
   and ideally a corpus that is not `insect`.

**Two consequences, and the first is now permanent rather than transitional.**

1. **SHIPPED.** `to_metric_tree`'s docstring was false for the 22 over-target
   configurations, because nothing re-normalizes them. It now states the
   post-condition that is actually true, in both directions — equalization can
   only *lower* the longest edge (`humanoid` 0.400000 → 0.349099, which reads
   OOD to the Tier 2.5 gate), the re-parent can only *raise* it (worst 0.8085,
   2.02×) — and records that restoring the old sentence with an unconditional
   clamp is the option §4.9 measured and rejected. With the rung unshipped this
   is not a temporary state: nothing re-normalizes, and the contract says so.
   `mesh_report` carried the same false claim to the *agent*
   (*"edges normalized so the longest limb == 0.40"*) and now prints the emitted
   value instead.
2. Any future rung lives in `rescue_ladder`, **not** in `pair_reconcile`, so the
   operation stays a pure `(nodes, pairs) → (nodes, pairs)` function and §6.15's
   hand-authored no-op property is untouched.

**One thing this choice forgoes, stated plainly.** The Tier 2.5 feasibility
gate consumes edge lengths and its training corpus was built in the 0.40
regime, so the 22 over-target trees are mildly out of distribution in a way
nothing else in this slice is — and an unconditional clamp *would* have put
them back. A ladder rung cannot, because the gate runs before the packer. So
§2.6.3's measured gate-verdict movement (12/50) is a number phase B must
**record**, not one it may expect to shrink. It is still the right cost: the
gate is a speed heuristic the compiler overrules, while the crease pattern is
the artifact the user actually receives.

---

## 5. Phasing

| phase | content | ships when |
|---|---|---|
| **A** | `reparent_pairs_to_shared_hub` in `pair_reconcile.py` — re-parent **and** orphan removal, one function — plus unit tests. Pure data, no caller. | tests green, including leaf-set invariance |
| **B** | Wire into `to_metric_tree` ahead of `reconcile_pairs`. Sample **both** pre-operation quantities of §4.6 — the pair gap for `pair_gap_max`, and the root degree for `structural_prefilter` — and extend `_last_pair_evidence` with them plus the re-parent/removal records. Add `root_children=` to `structural_prefilter` and pass it at `mesh_to_tree.py:1357`. Add §4.9's uniform-scale rung to `rescue_ladder` beside `order`/`placement`, and correct `to_metric_tree`'s docstring. | pack rate measured over §6.19 `pack-rate-no-regression`'s config set, no regression against `+drop`'s **39/45**; **and** the per-subject prefilter-admission table of §2.6.3 unchanged. The scale rung is expected to reach **43/45** — if it does not, the rung is wrong, not the gate |
| **C** | Disclosure block (including the post-operation root degree as an observation, §4.6/§4.7) + `pair_path_gap_max` scorecard column + baseline re-bless. | scorecard diff reviewed |

**All three phases shipped.** Phase B shipped *without* §4.9's rung, which the
gate condition itself falsified (§4.9.1); the "expected to reach 43/45" clause
is retired rather than deferred, because the 43 was measured through jitter.

Phase C's *"scorecard diff reviewed"* turned out to be the load-bearing gate of
the whole slice, and reviewing it required a step the row does not name:
**attribution**. The committed baseline was two slices old, so 16 axes had
moved and the diff alone could not say which slice moved what. Re-running the
benchmark with the re-parent monkeypatched to identity — the method the S7
baseline's own `_meta` established — split it cleanly, and only then did
`quadruped`'s stub regression (§7) become visible as *ours* rather than
inherited. **A re-bless without attribution would have silently absorbed it.**

Phase A is independently useful and independently reviewable; B is the only
phase that can regress anything.

**Phase B's gate is not the serve default.** Five subjects at voxel 64 / prune
0.30 is the sample that missed two packing regressions (§2.6.2), and it
missed them structurally rather than by bad luck: at that one configuration
only `fish` strands a junction, and `fish` packs either way. The gate must
cover every configuration whose leaf set the operation changes.

**And a pack-rate gate alone is still not sufficient**, because §2.6.3's
regression is invisible to one: those candidates pack. The second gate is
admission — the count of prefilter-accepted configurations per subject must
not fall. Both gates are needed because they fail in different places: one
catches a tree the compiler rejects, the other a tree the compiler never sees.

---

## 6. Testing

TDD throughout. The behaviours that must have a failing test first.

> **Every item carries a short name as well as a number, and cross-references
> use both.** Two revisions of this document renumbered §6 and left four
> references pointing at the wrong item — the phase-B gate was cited as
> "§6.13's config set" after §6.13 had become something else entirely. A name
> does not renumber.

**Unit (`tests/test_pair_reconcile.py`)**
1. **`sibling-noop`** — A sibling pair is untouched (no move, lengths unchanged).
2. **`ancestor-pair`** — An ancestor pair re-parents only the deeper member,
   growing its edge by the junction distance.
3. **`cousin-pair`** — A cousin pair re-parents both onto the LCA.
4. **`reach-preserved`** — **Reach is preserved** for every re-parented leaf,
   asserted as root-to-tip path length before vs after on a hand-built tree.
   This is the property the whole design rests on. Assert
   `abs(after - before) < 1e-12` — **not** equality (14 of 162 moved leaves
   carry one ULP, §2.6) and **not** a loose tolerance. 1e-12 is chosen against
   the failure it has to catch: a re-introduced `round(..., 6)` produces
   5.0e-07 and misses the bound by five orders of magnitude, while genuine
   float re-association (1.1e-16) passes by four. Build it on a tree where the
   naive implementation gives a *visibly* different answer, so the bound cannot
   pass by accident — `cascade-fixpoint`'s tree below is one (it drifts
   2.22e-16, one ULP at its own magnitude, against the corpus's 1.11e-16).
5. **`equalize-after-reparent`** — After re-parent + equalize, both members
   have equal path length.
6. **`refuse-root-member`** — A pair whose member is the root is refused, both
   lengths survive.
7. **`refuse-ancestor-member`** — A pair where one member is an ancestor of the
   other is refused.
8. **`leaf-set-unchanged`** — **The leaf set is unchanged**: same ids, same
   count, before and after. This is the load-bearing structural test, and
   `interior-untouched` below is why it has to be stated this way.
9. **`interior-untouched`** — No interior node's `parent_id` or `length` is
   rewritten. **This is not a restatement of `leaf-set-unchanged` and does not
   imply it**: a stranded junction keeps both its parent and its length and
   still becomes a leaf. An earlier draft listed only this one, which is
   exactly why the defect in §2.6.1 survived to be measured rather than caught.
10. **`subdivision-kept`** — A junction that keeps another child is left in
    place as a degree-2 subdivision (§4.5 row 1) — removal must not over-reach.
11. **`shared-strand`** — A junction emptied by *two different pairs between
    them* is removed. This resolves in a **single round**. An earlier draft
    called this test "the cascade"; it is not one, and labelling it that way
    left the real cascade with no test at all. Verified tree:

    ```python
    SHARED_STRAND = (
        [N(0, None, 0.0),
         N(1, 0, 0.30),                    # split shoulder, left copy
         N(2, 1, 0.70), N(3, 1, 0.50),     # both left limbs hang off it
         N(4, 0, 0.40),                    # tail, on the axis
         N(5, 0, 1.00), N(6, 0, 0.80)],    # both right limbs, already on root
        [[2, 5], [3, 6]])
    # both hubs = 0; removal drops [1]; leaves [2,3,4,5,6] before and after
    ```

    Either pair *alone* leaves junction 1 with a child; only the final state
    strands it. Lengths are chosen so the equalization that follows is a
    **no-op** (leaf 2 grows 0.70 → 1.00, which is already leaf 5's length),
    isolating removal as the only variable.

    > **What this test does and does not pin.** It does **not** discriminate
    > "removal runs once at the end" from "removal runs after each pair" —
    > measured, those give the identical dropped list `[1]`, and §4.1 explains
    > why they must. What it pins is the thing that actually matters:
    > computing `keep` **once, before any pair moves**. Refresh `keep` inside
    > the loop and removal drops *nothing* on this tree, because by then the
    > stranded junction is itself a leaf and `keep` protects it. An earlier
    > draft of this item claimed the stronger property; it is not true.
12. **`cascade-fixpoint`** — Deleting a stranded junction empties *its* parent,
    and that one's parent. Removal must run to a **fixpoint**. This is the item
    a fixed-depth implementation fails, and it must be written so that it does:

    ```python
    CASCADE = (
        [N(0, None, 0.0),
         N(1, 0, 0.20), N(2, 1, 0.20), N(3, 2, 0.20),   # 3-node spine chain
         N(4, 3, 0.60),                                 # left limb, deep
         N(5, 0, 1.00),                                 # right limb, on root
         N(6, 0, 0.50)],                                # tail, on the axis
        [[4, 5]])
    # fixpoint  drops [1, 2, 3] -> leaves [4, 5, 6]     (unchanged)
    # 1 pass    drops [3]       -> leaves [2, 4, 5, 6]  INVENTS flap 2
    # 2 passes  drops [2, 3]    -> leaves [1, 4, 5, 6]  INVENTS flap 1
    ```

    **It defeats a two-pass implementation as well as a one-pass one**, which
    the corpus cannot: the deepest real cascade is 2 levels, so a 2-pass bug
    would ship green against every mesh and red only here.

    Do **not** "simplify" the lengths. At 0.20 × 3 the tree drifts 2.22e-16 —
    one ULP, the same residue §2.6 documents — which is what makes it a valid
    `reach-preserved` fixture too. Binary-exact lengths (0.25, 0.25, 0.25,
    0.50, 1.25, 0.50) produce drift of exactly 0.0 and the identical drop
    sequence, and would let someone write `assert ==` and pass.

    Both trees are measured, not sketched, and the corpus agrees:
    `fish` v96/p0.3 drops `[8, 10, 11, 13]` over **two** rounds (`[11, 13]`
    then `[8, 10]`), where a single pass drops only `[11, 13]` and invents
    flaps 8 and 10; `insect` v128/p0.4 is `[5, 12]` under fixpoint against
    `[12]` under a single pass. `fish` v64/p0.3 — the serve default — is `[8]`
    either way, which is why the serve default cannot be the test.

    > **Assert the dropped-id list, not just the leaf count.** The two failing
    > arms invent *different* flaps (2 under one pass, 1 under two), so a
    > `len(leaves) == 3` assertion names neither. `dropped == [1, 2, 3]` names
    > the defect. And one more arm is worth a test of its own: computing `keep`
    > **inside** the pair loop instead of once up front makes removal drop
    > *nothing* on both trees, because a freshly stranded junction is a leaf by
    > the time `keep` is refreshed, and `keep` then protects it. That is the
    > plausible refactor §4.1's "runs once, after every pair" is guarding
    > against, and `shared-strand` catches it.
13. **`pair-order-independent`** — Pair order does not affect the result
    (independence, §4.2).
14. **`no-caller-mutation`** — The caller's node list is never mutated.

**Regression**
15. **`hand-trees-byte-identical`** — **SHIPPED.** All four templates + `HSHAPE` +
    `DOG_RAW` + `DOG_REPAIRED` are unchanged by the operation. (Measured true,
    §2.6 — this pins it.)
16. **`goldens-byte-identical`** — Every committed geometry golden still
    compiles byte-identically.
17. **`pair-gap-max-preserved`** — **SHIPPED**, with a companion 17b (a refused pair never reaches `reconcile_pairs`, so its gap must ride the re-parent record; `fish` v64/p0.5 is the degenerate tree whose 100% disagreement would otherwise vanish). The two arms kill different mutations. `pair_gap_max` on a fixed extracted tree is
    **unchanged** by wiring the re-parent in — the first §4.6 warning, pinned.
    Must be written against a tree where the naive ordering visibly inflates it
    (`fish` v128/p0.3 moves 0.2538 → 0.7298), or it passes vacuously.
18. **`prefilter-admission-preserved`** — **SHIPPED**, with a companion 18b that is the actual pin: 18 calls `structural_prefilter` directly, so deleting `root_children=` from the production call site leaves it GREEN (measured). 18b runs the real search and watches the real call. The per-subject count of
    prefilter-accepted configurations is unchanged by wiring the re-parent in —
    the second §4.6 warning, pinned. Must be written against `insect`, the only
    subject where it moves (3 → 0 without the fix), and must assert the count
    rather than a boolean on one config, because the failure is that *all three
    disappear*. A pack-rate test cannot substitute: all three candidates
    compile.

**Cohort (phase B gate)**
19. **`pack-rate-no-regression`** — Pack rate does not regress over
    `probe_pair_topology.pack_configs()`. This is the one number that can stop
    the slice.

    **The config set is derived, not listed, and the rule is deliberately the
    broad one:** every configuration where a pair **moves at all**, plus the
    serve default whether it moves or not — **45 of 50**: the 44 where a pair
    moves, plus `bird` v64/p0.3, the one serve-default row where nothing does.

    That breadth was arrived at by getting it wrong twice, and both mistakes
    are worth keeping because they are the same mistake at different scales:

    | version | rule | covered | what it missed |
    |---|---|---|---|
    | 1 | the serve default | 5 | two outright packing regressions (§2.6.2) |
    | 2 | hand list: serve default + flap-inventing configs | 14 | the 14 configs the **clamp** later put in scope (§4.9) |
    | 3 | derived: deleted ∨ prefilter-flipped ∨ clamped | 28 | **17 configs where a pair moves and none of the three fires** |
    | **4** | **derived: any pair moved ∨ serve default** | **45** | — |

    Version 3 is the instructive one, because it *looks* principled: it
    triggers on every **structural** effect. But a plain re-parent with no
    deletion, no flip and no clamp still grows leaf-to-leaf tree distance — by
    **2× the edge growth** for every leaf in the old subtree (§7) — and
    leaf-to-leaf distance is exactly what circle packing must fit. The stated
    rule said "anything the packer can see"; the implementation tested three
    proxies for it. **When a gate's rule and its implementation disagree, the
    implementation is the gate**, and the six configs excluded from version 4
    are excluded because nothing moves in them at all.

    Compiling 45 × 4 arms is hours, so identical arms compile once: where
    nothing is dropped and the clamp does not fire, the last three arms are the
    same tree.

    **Measured, 2026-08-03 — this is the baseline phase B is gated against:**

    | arm | packs |
    |---|---|
    | raw (HEAD) | 27 / 45 |
    | + re-parent | 35 / 45 |
    | + orphan removal | **39 / 45** ← *phase B must not regress this* |
    | + uniform scale | 43 / 45 ← *the §4.9 rung's target* |

    Read the last two rows together with §4.9: the scale arm is measured
    **unconditionally**, but ships as a ladder rung, so what phase B must
    reproduce is 39 at stage 0 and 43 once the rung runs. Any configuration
    that packs at `+drop` and fails after the rung is added means the rung is
    firing when it should not.

**Deliberate re-bless, not a break**
20. **`rebless-list`** — see below.

### What goes red, and why the list has to be captured before phase B starts

An earlier draft named exactly one test here and implied the suite was
otherwise green. **It is wrong in both directions**, and both errors are the
same mistake: assuming the baseline rather than measuring it.

**One test is already red at HEAD, before this slice touches anything.**
`tests/test_gate_mesh_region.py::test_snapshots_match_live_extraction` fails
on `quadruped`:

```
At index 1 diff: length 0.28637599999999996 != 0.299635
```

That is not a mystery and not this slice. The snapshot records
`pairs: [[1, 5]]` with lengths 0.299635 and 0.273117, and
`(0.299635 + 0.273117) / 2 = 0.286376` exactly — it is the **shipped**
predecessor's equalization, against a snapshot generated before it
(`2f3523c`, predating `f5787b9`). The fixture needs regenerating regardless of
this slice.

**And that same test will move again at phase B**, because `[[1, 5]]` is a
*non-sibling* pair — node 1 hangs off the root, node 5 off node 2 — which is
exactly the case this slice re-parents. So it will drift in structure as well
as in length.

Therefore, phase B's procedure, not just its list:

1. **Capture the HEAD baseline first** — the full set of failing node ids,
   recorded, before a single line of phase B lands. A red suite with an
   unenumerated cause is indistinguishable from a regression, and this suite is
   already red.
2. **Diff against that baseline**, never against "green".
3. Every test that moves must land in exactly one bucket: *already red at
   HEAD* / *deliberately re-blessed* / **unexplained** — and an unexplained
   entry stops the phase.

The deliberate re-bless is the predecessor's pinned limit:
`test_non_sibling_pairs_are_not_fixed_by_equal_leaf_lengths` asserts
`insect.glb` still emits a non-sibling pair. Eliminating those is this slice's
entire purpose, so the test *must* fail at phase B. Re-point it at the
pre-re-parent tree so it keeps pinning that limit rather than deleting the
evidence for it.

The snapshot fixtures (`tests/fixtures/mesh_validation_trees.json`, via
`gen_mesh_validation_trees.py`) are a **regeneration**, not a re-bless: they
are a drift tripwire whose reference is stale for a reason that is already in
`main`. Regenerate them in their own commit, *before* phase B, so that the
phase-B diff starts from a green tripwire and any later movement is
attributable.

**THE MEASURED BASELINE — `460ee32`, phase B diffs against this and nothing
else.** `cd mcp_harness && PYTHONPATH=.:tests pytest tests/ --timeout=420`
→ **6 failed, 2176 passed, 11 skipped** (16:50).

| # | test | bucket |
|---|---|---|
| 1 | `test_feasibility_dataset::test_perturb_pack_is_persisted_to_disk` | red at HEAD — macOS perturb wedge (PR #68) |
| 2 | `test_mesh_recalibration_live::test_fixtures_in_distribution_on_live_path[humanoid]` | red at HEAD — the OOD defect below, on the **live** path |
| 3 | `test_rigid_compiler::test_representative_full_artifact_hash_vector_is_frozen` | red at HEAD — frozen-hash platform divergence (PR #67), cannot be green on both platforms |
| 4 | `test_rigid_miura_compiler::test_representative_miura_artifact_hash_vector_is_frozen` | red at HEAD — same family |
| 5 | `test_rigid_phase3_oracle_fixture::test_phase3_oracle_regenerates_byte_identically` | red at HEAD — degree-4 deferred (PR #68) |
| 6 | `test_gate_mesh_region::test_mesh_fixtures_are_in_distribution` | **introduced by `460ee32`, deliberately** |

**Unexplained: zero.** Phase B may proceed.

Item 6 is not a new defect, it is the same defect as item 2 becoming visible.
`test_fixtures_in_distribution_on_live_path` calls `mesh_to_metric_tree`
directly and never reads the snapshot, so it has been failing on this branch
all along; `test_mesh_fixtures_are_in_distribution` reads the snapshot, which
predated equalization and therefore still showed every fixture at a longest
edge of exactly `0.400000`. Two tests, one property, and the snapshot one was
lying. Regenerating made them agree.

> **⚠ The cause is upstream of this slice and the clamp cannot fix it.**
> `to_metric_tree` normalizes the longest edge to `LONGEST_LIMB_TARGET`, then
> `reconcile_pairs` runs **after** and replaces two lengths with their mean —
> and a mean never exceeds the larger. So whenever the longest edge is a pair
> member the tree lands *below* the regime the Tier 2.5 gate's corpus was
> trained in: `humanoid` 0.400000 → 0.349099 (OOD score 1.008 > 0.863),
> `insect` 0.400000 → 0.385580. §4.9's rung scales **down** only, so it is
> powerless here by construction. Verdict is `compile_anyway`, not
> `infeasible` — a lost fast-path, not a wrong answer. Fixing it means
> retraining the gate corpus, which is separately parked; phase B records it
> and does not touch it.

> **⚠ A worktree needs three build artifacts git does not carry.** The first
> attempt at this baseline read `41 failed` and was entirely wrong. Besides
> the engine `.so`, `mcp_harness/oriedita/oriedita-1.1.3.jar` and
> `mcp_harness/OrieditaValidator.class` are gitignored build products; without
> the second, `linter_server` reports *"The Oriedita validator is not built"*
> and **every** compile verdict becomes `FAIL-LINT`, reddening `test_verdicts`
> (21), `test_lint_classification` (8), `test_fold_handles` (5) and
> `test_scaffold` at once. Fix with `cd mcp_harness && ./build_linter.sh`, and
> verify with a three-case probe (`star-4` and `quad` must be `PASS`) before
> paying for a 17-minute suite. Run pytest the way `runner.py` documents —
> from `mcp_harness/`, `PYTHONPATH=.:tests` — or the build hint is swallowed
> and only the symptom shows.

### The negative controls

A test that would pass whether or not the code works is worthless here. Four
of the items above are written specifically to be falsifiable:

* **`reach-preserved`** must be built on a tree where the naive implementation
  (re-parent without adjusting the length) gives a *visibly different* answer.
* **`leaf-set-unchanged`** must be built on a tree where a junction really is
  stranded — a sibling-paired tree cannot fail it, which is why
  `hand-trees-byte-identical` is blind to §2.6.1 and cannot substitute. Note
  the *existing* hand trees in `tests/test_pair_reconcile.py` are flat stars
  with every flap on `parent_id 0`; none of them can strand a junction, so
  none of them can serve here. `shared-strand` and `cascade-fixpoint` above
  are the trees this test needs, and they did not exist before this spec.
* **`cascade-fixpoint`** must fail under a single-pass implementation. The
  tree above does; a tree whose stranding resolves in one round does not, and
  that mistake is what item 11's history records.
* **`pair-gap-max-preserved`** and **`prefilter-admission-preserved`** must
  each be built on a config where the naive ordering really does move the
  number — `fish` v128/p0.3 and `insect` v96/p0.5 respectively.

---

## 7. Risks and open questions

| risk | why it is real | mitigation |
|---|---|---|
| **Packing regresses.** | Growing a flap's edge grows its tree distance to other leaves on the same side, and leaf-to-leaf tree distance is exactly what circle packing must fit. Re-parenting `a` from `ja` up to `h` grows `d(a, x)` by **2·dist(ja, h)** for every leaf `x` inside `ja`'s old subtree. Measured: worst edge growth 0.5020, **worst leaf-to-leaf growth 1.0040** — exactly 2×, and **2.5× `LONGEST_LIMB_TARGET = 0.40`**. An earlier draft quoted the edge figure while naming the leaf-to-leaf quantity, understating its own headline risk by a factor of two. | **Measured, over 45 configurations and four arms.** raw **27** → re-parent **35** → + orphan removal **39** → + uniform scale **43**. Re-parent alone regresses two configurations (§2.6.2); removal recovers both and adds four more; the scale rung adds four further rescues with **zero** regressions. The residual risk is real but bounded — the max-case growth is exercised in that config set. |
| **The emitted tree stops honouring `LONGEST_LIMB_TARGET`.** | `to_metric_tree`'s stated contract (`mesh_to_tree.py:565`) is *"scaled so the longest == `LONGEST_LIMB_TARGET`"* (0.40, annotated *"packing regime"*). Measured after re-parent + removal + equalization: **22 of 50 configurations** have a longest edge above 0.40, worst **0.8085 — 2.02× the target** (`fish` v96/p0.3). The slice **introduces** this: at HEAD the longest edge is 0.40 or below on **50/50** (range 0.20–0.40), because equalization replaces two lengths with their mean and a mean never exceeds the larger. The re-parent *grows* edges, so it can and does. Trees also move relative to the length regime the feasibility gate's corpus was built in. | **Disclosed, not clamped away — see §4.9.** The first draft resolved this with an unconditional clamp in `to_metric_tree`. The 45-configuration sweep falsified that: **18 of the 22** applications fire on trees that already packed, and one of them (`humanoid` v64, factor 0.9130) takes the compiled crease pattern from a bit-exact mirror to residual `4.00e-01`. The clamp is now a `rescue_ladder` rung reached **only on pack failure**, so these 22 configurations stay over target in the emitted tree and the docstring is corrected to say so. Accepted cost: they remain mildly outside the length regime the Tier 2.5 gate's corpus was built in — which is exactly why §2.6.3's 12/50 gate-verdict movement is a number phase B records rather than expects to shrink. |
| **Node LIST POSITION shifts, and that is what the engine seeds from.** | Not ids — `TreemakerWrapper.cpp:234-253` computes each node's initial placement from `order`, the loop counter over the incoming list, and uses the id only as a map key. Controlled: renumbering every id leaves the fold byte-identical **5/5**; swapping two siblings in the list changes it **5/5**. The re-parent itself moves nothing (it rewrites `parent_id` and `length` in place), but **removal deletes entries**, which re-indexes every survivor after the deletion point — 10/50 configs, worst 9 of 14 nodes, worst seed displacement **1.2210** on a 1×1 paper. An earlier draft claimed this row was mitigated by ids being stable; that named the wrong quantity. | **The compile sweep is the mitigation, not an argument.** §2.6.2 runs the removal arm through the real engine on the serve default plus **every** configuration where deletion fires: 13/14 versus raw's 6/14, no regression anywhere. Node count drops by **17** across the corpus, at most 4 in any one tree, and that is the point rather than a side effect. Residual risk: a mesh outside this corpus can re-index differently, and only a compile will say. §6.19 `pack-rate-no-regression` is the standing gate. |
| **The straddle signal is measured against the wrong plane.** | §2.2 caveat. | Nothing in this design uses it, and the error direction is bounded and favourable (offset-0 can only under-count). False-pair rejection is explicitly out of scope. |
| **The operation trips `structural_prefilter`'s root-degree guard.** | The LCA hub is usually the root, so root degree rises in **40/50** configurations and ends over `MAX_ROOT_CHILDREN = 4` in **15/50**. On **3** it flips the prefilter ACCEPT → REJECT, and those three are *all* of `insect`'s admissible configurations (3 → 0) — on the one subject this operation rescues. A pack-rate gate cannot see it: all three compile. | **Resolved in §4.6, not merely disclosed**: the root-degree term is evaluated on the pre-operation tree, which is the same discipline `pair_gap_max` already requires and is supported by three independent pieces of committed evidence (3/3 of the rejects compile; `tree_contract.py:23-59`'s k-star packability control; `structural_admission`'s refusal to encode root degree at all). The post-operation degree is still **reported** so a genuinely overloaded hub stays visible — `fish` v96/p0.3 reaches a 10-child root, past the k=8 edge of the control. §6.18 `prefilter-admission-preserved` pins the admission table; §5's phase-B gate re-checks it. |
| **`pair_gap_max` silently changes meaning.** | It is the predecessor's *only* mitigation for "this hides a real extractor bug", and running the re-parent first contaminates it on 37/50 configs. Its existing test stays green throughout. | §4.6 requires the gap to be sampled before the re-parent; §6.17 `pair-gap-max-preserved` pins it on a config where the naive ordering visibly moves the number. |
| **`MAX_PAIR_GAP` becomes more destructive if it is ever wired.** | The constant is deliberately unwired (`pair_reconcile.py:64-77`). With the re-parent running first, pairs over the 0.20 cutoff go **29/117 → 42/117**, so wiring it later would silently withdraw 45% more pairings than the analysis that set it assumed. | Record the interaction in the constant's docstring now, while the two are being changed together. This slice does not wire it. |
| **Non-sibling pairs may include genuinely different body positions.** | The junctions really are ~8% of the mesh apart along the body. Merging asserts they are one point. | This is the design's central claim, and §2.2/§2.4 are the evidence for it: the tips reflect, the junctions are both on the spine, and the offset is along-body — the signature of a split junction, not of two different body segments. **The visual check is PAID** (`docs/superpowers/evidence/2026-08-03-reparented-bases/`): all three reconciled bases are well-formed uniaxial bases — closed hulls, no holes, no degenerate faces — and `humanoid`'s pattern becomes **geometrically exact** (1.04e-01 → 0.00e+00: every vertex has a mirror image and the edge set carries onto itself) while getting simpler (33 → 21 vertices) — ⚠ CORRECTED: this cell used to call it an "exact mirror" outright, the same overclaim already fixed in the evidence README once `cp_mirror.mirror_verdict` (2026-08-04-cp-mirror-metric-design.md) replaced the vertex-only residual. Measured, `humanoid` reconciled carries 2 swapped creases (mirror-image creases that fold opposite ways), so `symmetric` reads False even at residual 0.0 — geometry exact, pattern not symmetric. Two limits recorded with it: a flat-folded silhouette shows layer structure rather than limb placement, so "both front legs now reach equally" rests on `pair_path_gap_max` = 0.0, not on the picture; and the residual is directed, so a 0.0 on 21 vertices was never proof of symmetry by itself, only of geometry — `is_bijection` / `mv_swapped` are what settle it. |
| **⚠ The re-parent can push a serve down an admissibility class — measured on `quadruped`, and no phase-B gate can see it.** | Phase C's re-bless, attributed by counterfactual, found `quadruped` moving `rescue_stage` **jitter → stub** and `stub_flaps` **0 → 3**. The re-parented tree no longer packs under jitter, so the ladder falls through to Lang's stub remedy: the serve stops nudging proportions and starts carrying **three flaps the engine invented**. `rescue_ladder`'s admissibility key ranks `invents_anatomy` FIRST, so by the ladder's own ordering this is a downgrade, even though `served_fidelity` reads flat and `nudge_marker` reads *better*. Pack rate cannot see it (it packs); the admission table cannot see it (`quadruped` holds at 5); `served_leaves` cannot see it (stubs ride their own axis by charter rule). | **Recorded, not fixed.** It is a genuine trade rather than a plain regression — exact proportions bought with invented anatomy — and which side is worse is a product judgement this slice should not make silently. The three surfaces that make it visible now exist: `stub_flaps` in the scorecard, the STUB provenance block in the served report, and the attributed `_meta` in `fixtures/scorecard_baseline.jsonl`. The natural follow-up is §2.8's axis-pinning slice, which targets the same freedom the stub is compensating for — but note §2.8's own correction: the lever is **`tmConditionNodeSymmetric`**, which has no binding yet, *not* the `set_node_at` Combo, which cannot express `y = x` at all. So the follow-up is a C++ slice, not a cheap one. |

**Open questions, deliberately not answered here**

1. Re-measure straddle against the offset plane each configuration actually
   used, then decide whether false-pair rejection belongs at detection time.
2. `_bfs_remap` making a leaf the root on a degenerate two-node tree is a
   separate defect. Refused here; not fixed here.
3. Whether the extractor should *prefer* candidates needing fewer re-parents.
   Cheap to add to the existing rank, but it is a search change, not a
   correctness change.
4. Whether the split junction should be fixed **at source**, by merging nearby
   branch points during skeletonization (§3). That is the standard remedy and
   it would make this slice a no-op. One objection survives §4.5's correction
   and it is the only one: merging shortens the root-to-tip path of everything
   distal to the junction, while the re-parent preserves reach exactly. The
   *other* objection an earlier draft leaned on — that contraction renumbers
   nodes and node numbering is load-bearing — is **measured false** (§2.6.1:
   renumbering is byte-neutral 5/5), so it must not be repeated. Worth
   revisiting whenever the extractor is next reworked.
*(A fifth question — whether `LONGEST_LIMB_TARGET` should be re-applied after
reconciliation or its contract narrowed — is no longer open. §4.9 decides it:
a clamp, provably a no-op on the corpus as it stands. What remains is a gate
condition on phase B, not a question.)*

---

## 8. Out of scope

* **False-pair detection** (§4.4, open question 1).
* ~~**Full graph symmetry**~~ — **this slice already delivers it; see §2.7.**
  The original entry here claimed it was a strictly stronger, separate goal.
  That was wrong and the measurement says so.
* **R5 / the feasibility gate's inverted `n_sym_pairs`.** Confirmed defect,
  latent, needs corpus regeneration — unrelated to this mechanism.
* **`_bfs_remap`'s degenerate-root fallback.**
