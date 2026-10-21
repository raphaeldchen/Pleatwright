# S3 — the axial leaf pin. Design spec.

> # 🛑 DO NOT DISPATCH — REFUTED BY MEASUREMENT, 2026-08-06
>
> **The wins this spec is built on are NOT attributable to the axial pin.** They
> are reachable today, unpinned, with **zero C++**, by a shipped function the
> serve path never calls.
>
> Verified by the planning session directly, stock engine, no pin anywhere:
>
> ```
> bird     seeded_3   bij=True  res=0.000000  card=18/18  mv_sw=4  scale=1.515998
> humanoid seeded_1   bij=True  res=0.000000  card=21/21  mv_sw=2  scale=0.775554
> humanoid seeded_2   bij=True  res=0.000000  card=21/21  mv_sw=2  scale=0.775554
> ```
>
> These match the *pinned* arms to six digits; at vertex level the folds are
> identical at 1e-5 (bird under the identity map, humanoid under rot180 /
> anti-diagonal reflection). **Humanoid is §7.1's named acceptance subject, and
> its win is not the pin's.** On quadruped, `seeded_2` unpinned also reaches
> bijection, eliminates all 3 invented stub flaps, and gains +19.7% scale —
> **only the coverage figure (0.7409 → 1.0000) is pin-unique, and that is a
> Goal-1 column.**
>
> **The mechanism, confirmed in source** (`server.py:1516`): when attempt-0
> packs, the serve returns *"untouched (deterministic); no ladder ran"*. Bird and
> humanoid pack attempt-0, so **the serve never tries an order variant.** The
> pin's causal role was only to knock attempt-0 out so the ladder would run.
>
> **The real defect this exposes is FIRST-CLEAN-WINS.** Bird's and humanoid's
> served folds are strictly dominated — bijection, +38.3% / +10.6% scale,
> +97.0% / +5.0% coverage — by a fold one already-implemented
> `rescue_ladder.order_variants` call away that the serve path never looks at.
> Project memory already records this lever as unexploited: *"ladder never ranks
> by scale → dog-raw discards +12.7% on the path it already runs."*
>
> ⚠ **And it must RANK, not take the first.** Planning session measured a case
> the refutation missed: humanoid `canonical` **also** reaches bijection, at
> cardinality 50/50, `mv_swapped` **26**, scale **0.598** — a markedly worse
> bijective basin than `seeded_1`'s 21/21 / 2 / 0.776. A "first bijection wins"
> rule would ship the bad one.
>
> **What survives from this document:** §2 (Lang's `SetToSymmetryLine` exists and
> is unbound) is still true and still the right binding if a pin is ever needed.
> §3.1's vacuous-telemetry finding stands on its own. §9's prior art —
> especially the **REJECT** on Lang's published (A-20)/(A-21) disagreeing with
> his own code — is independent of the routing. §11's cross-goal corrections
> stand.
>
> **Superseded by:** the order-stage slice (Python-only). `TreemakerWrapper.cpp`
> is **released** — see `../goals/COORDINATION.md` §2.

**Goal 2 / G2a — leaf placement.** Status: **REFUTED, not dispatched.**
Base for implementation: `main` at or after `e100cf1`.
Supersedes nothing; the sibling spec
[`2026-08-04-mirror-equivariant-facet-cut-design.md`](2026-08-04-mirror-equivariant-facet-cut-design.md)
owns **G2b** and was **stopped by measurement** — see its §4.2 and
`../goals/goal-2-symmetry/PROGRESS.md` §0.3.

> ## ⚠ READ THIS FIRST — three things that will otherwise be got wrong
>
> 1. **This is NOT "bind a constraint, ~5 lines."** `COORDINATION.md`'s
>    "~5 lines of C++ plus plumbing" estimate is **wrong**. It is ~40 lines of
>    C++ across **three** sites, a selector, and plumbing through **seven**
>    independent call sites.
> 2. **The shipping mechanism went 1 WIN / 1 no-op / 2 HARD FAILS out of 4**
>    when actually built and run. S3 is a **gated rescue rung with the unpinned
>    compile as fallback**, never an unconditional bind. Specced any other way
>    it converts two currently-serving subjects into failures.
> 3. **`cp_symmetric` will NOT go True on any subject** — 22 of 22 measured
>    arms stayed False. An acceptance criterion written as `cp_symmetric is
>    True` **fails on S3's own showcase subject.**

---

## 1. The mechanism, at the strength the evidence supports

A leaf earns a mirror partner **three** ways:

1. **a declared pair**, which `apply_symmetry` *forces* — all 13 declared pairs
   across 5 mesh subjects + 4 templates measure `pack_mirror_gap` exactly `0.0`;
2. **landing ON the axis**, self-mirroring;
3. **two undeclared equal-length leaves related by a tree automorphism** landing
   mirror-image by optimizer luck.

**S3 acts on route 2 only.** "Unpaired leaves off the axis" is route 2 failing.
Write it that way — the earlier shorthand *"CP asymmetry is unpaired leaves off
the axis"* is **under-scoped, not false**: route 3 produces trees with unpaired
leaves far off the axis that are nonetheless exact bijections (`quad`, `star-3`,
`star-4`, `star-5`, `two-level-tree` — **all five have `pairs == []`**), and
those are not counterexamples.

Direction is never contradicted across all 25 `cases.CASES`: no row where a leaf
lacks a partner and the CP still mirrors, none where every leaf has a partner
and the CP fails.

**S3's exact domain — has pairs AND ≥1 unpaired leaf: 7 of 25 cases.**
`dog-raw` [4,6] · `dog-repaired` [6,4] · `template-quadruped` [7,8] ·
`template-bird` [7,8] · `template-humanoid` [5] · `template-insect` [0,10,11] ·
`insect-knife-024` [0,10,11]. Zero-unpaired: `hshape`, `star-4-sym`,
`star-6-sym`. Everything else has no axis.

### 1.1 The interventional result — it is the axis, not the act of pinning

`template-humanoid`, node 5 pinned on-axis:

| | unpinned | pinned on-axis |
|---|---|---|
| `is_bijection` | False | **True** |
| residual | 0.267053 | **0.000000** |
| cardinality | 8/33 | **21/21** |
| scale | 0.629445 | 0.682489 (**+8.4%**) |

**Attribution is clean and this is what makes it a mechanism rather than a
correlation.** Pinning node 5 *at its own current off-axis spot* reproduces the
unpinned control **byte-for-byte** (residual 0.267053, cardinality 8/33, scale
0.629445); a *different* off-axis point (1.0, 0.6) stays broken (residual
0.177915). Two agents ran it independently and agree to six digits.

Nothing in the repository had tested this premise before.

---

## 2. The binding site — Lang already wrote it

**An existing constraint is reused. No new condition class, no new constraint
function, no vendored file changes, no signature changes.**

**This is CLAUDE.md §0 paying for itself a third time.** The vendored source
already contains the facility; it has simply never been exposed.

| piece | location |
|---|---|
| the constraint function | `tmOptimizers/tmConstraintFns.h:207-224` — `class StickToLineFn`, *"constrain a node to lie on a line (e.g. a line of symmetry)"*. Impl `.cpp:592-624`: `Func = (-u[ix]+p.x)*sa + (u[iy]-p.y)*ca`, `Grad` two constants. **One linear row, fully general in `mSymAngle`.** |
| the flag | `tmTreeClasses/tmConditionNodeCombo.h:43/53/69` — `GetToSymmetryLine` / `SetToSymmetryLine(bool)` / `mToSymmetryLine` |
| emission | `tmConditionNodeCombo.cpp:168, 206, 233, 260` — all four read `if (mTree->HasSymmetry() && mToSymmetryLine)`, covering scale, edge and both strain optimizers |
| Lang's own driver | `tmTree.cpp:1498` `c->SetToSymmetryLine(true)` inside `SetNodesFixedToSymmetryLine` |
| already compiled in | `nm headless_treemaker…so \| c++filt` → `tmConditionNodeCombo::SetToSymmetryLine(bool)` and `tmTree::SetNodesFixedToSymmetryLine(...)`. **No pybind binding exists.** |

`set_node_at` **already instantiates the exact condition object** and simply
never touches the flag (`TreemakerWrapper.cpp:375-384`):

```cpp
tmConditionNodeCombo* c =
    mTree->GetOrMakeOnePartCondition<tmConditionNodeCombo, tmNode>(n);
c->SetXFixed(true);  c->SetXFixValue(x);
c->SetYFixed(true);  c->SetYFixValue(y);
```

The new method is a **sibling of those three**, reusing `PinTarget(node_id, who)`
(`:357-373`) verbatim — it already refuses non-leaves (*"a boundary condition on
a non-leaf is a SILENT no-op in the engine"*) and refuses after `mStubApplied`.

### 2.1 ★ Why `set_node_at` is not a substitute — and why every recon number is a proxy

`set_node_at` fixes a **POINT** (two equalities, 0 DOF) where "lies on the axis"
is a one-equality **SLIDE** (1 DOF). It over-determines the leaf, making the
position a **lottery**: 2 of 25 on-axis positions build on the voxel-64 bird,
2 of 25 on the served bird, 2 of 9 on `template-humanoid`, 0 of 9 on fish. The
23 failures split four ways — `scale optimization did not converge (reason code
1)` (5), `polygon network is not valid after optimization` (10),
`POLYS_MULTIPLE_IBPS` (5), `NOT_LOCAL_ROOT_CONNECTABLE` (3).

⚠ **Consequence for how this spec must be read: almost every number below came
from the 0-DOF proxy.** The 1-DOF constraint is strictly weaker, so **proxy pack
failures do NOT transfer** — do not cite fish 0/9 or `template-insect` 0/9 as
negative results.

---

## 3. The projection question — and the second C++ change

**Structurally: nothing stops `ProjectActivePaths` moving a pinned leaf off the
axis. Empirically it doesn't, at ~1e-9. And the instrument that would tell you
reports a perfect pass either way.**

`ProjectActivePaths` (`TreemakerWrapper.cpp:1119-1307`) builds its least-squares
system from exactly two row classes — active axis-parallel leaf-path equalities
(`:1143-1153`) and mirror rows from `mSymPairs` **only** (`:1163-1170`). **There
is no stick-to-line row.** Its own comment (`:1283-1289`) is explicit:

> *"…a pin at exactly 0 or w sits ON the clamp… It does NOT generalize to
> interior pins, and emphatically not to 'the projection preserves constraints':
> the mirror rows above preserve the WRONG mirror perfectly. Hence: report, do
> not assume."*

Measured drift: **7.18e-10** max displacement, post-projection axial residual
**5.55e-17** at 45°, against `cp_mirror.mirror_bijection`'s `tol = 1e-6`. Four
orders inside tolerance. **Latent, not live.**

### 3.1 ⚠ The vacuous-pass trap — this is the standing rule's exact failure shape

`struct Pin { bool xFixed, yFixed; double x, y; }` (`:1438`) has **no
symmetry-line field**, and the verification loop (`:1290-1300`) reads only
`xFixed`/`yFixed`. **A `SetToSymmetryLine` pin would report `n_pins = 0` and
`pin_max_displacement = 0.0`**, and
`test_projection_guards.py::test_no_pins_reports_zero_pins` **stays green**.

That is `mv_swapped == 0` and `pair_path_gap_max = 0.0` all over again. Per
`COORDINATION.md` §4.1 this alone disqualifies the telemetry from shipping.

### 3.2 The fix: push each axial-pinned leaf into `syms` as a SELF-PAIR (`a == b`)

Algebra verified against `:1242-1251`:

```
row1 = {2b, 2a+1}, c1 = {1,-1}, r1 = x[b] - y[a]
row2 = {2b+1, 2a}, c2 = {1,-1}, r2 = y[b] - x[a]
```

Substituting `b := a` collapses both to `x[a] - y[a] = 0` — **exactly "leaf a
lies on y=x"**. The duplicate row doubles that equation's least-squares weight
(harmless), and `maxr` (`:1252`) then includes the axis residual, so the loop
will not exit until it is under `tol = 1e-13`.

**Three wins from one edit:**

1. the projection **represents** the axial pin instead of tolerating it;
2. `*outCons = cons.size() + 2*syms.size()` (`:1171`) surfaces it — **no longer
   vacuous**;
3. it **automatically closes the silent-wrong-axis hole**. Measured: `star-4`
   with one axial pin and zero pairs **builds silently at 0° and 30°**. That is
   not a pre-existing bug — the gate `if (!syms.empty())` was deliberate, with a
   written rationale (`:1187-1190`): *"Gating on `HasSymmetry()` would be a false
   positive on every unpaired tree that sets an axis."* **S3 invalidates that
   premise**, because an axial pin *is* a mirror-bearing constraint. Self-pairs
   in `syms` make the existing refusal fire correctly with **no change to the
   gate**.

---

## 4. ★ THE MEASURED RISK — the shipping mechanism is 1-for-4

A prototype `.so` was actually built with `SetToSymmetryLine` (scratchpad only;
checkout untouched) and run:

| subject | axial offset | result |
|---|---|---|
| `TEMPLATE_HUMANOID` (node 5) | 0.487357 | **WIN** — 8/33 → 21/21, residual 0.267 → 0.0, scale **+8.4%**, coverage −1.3% |
| `TEMPLATE_BIRD` (nodes 7,8) | 0.0 (already axial) | benign **no-op** — scale unchanged 0.652542, residual 0.0 → 2.40e-08 |
| `TEMPLATE_QUADRUPED` (nodes 7,8) | 0.0 (already axial) | **HARD FAIL** — `POLYS_MULTIPLE_IBPS`, scale 0.667979 → 0.544634 (**−18.5%**) |
| `TEMPLATE_INSECT` (node 10) | 0.707107 | **HARD FAIL** — `polygon network is not valid`; with (0,10,11) → `POLYS_MULTIPLE_IBPS` |

**All four currently pack attempt-0 exact.**

**Mechanism:** adding a linear equality changes the ALM problem *from the seed
positions*, so it can land a different local optimum **even when the constraint
is already satisfied at the unpinned optimum.** **Pinning an already-on-axis leaf
is not free.**

⇒ **Two mandatory shape requirements, and S3 is unsafe without both:**

* **Gate on a materially nonzero RAW paper-space axial offset.** This alone
  skips `QUADRUPED` and `BIRD` entirely, leaving them byte-identical.
* **Treat the pinned compile as a RUNG with the unpinned compile as FALLBACK.**

### 4.1 The feasibility band is NON-CONVEX in the pin parameter

Mesh humanoid packs on `t ∈ [0.20,0.40]` and `[0.60,1.00]`, and **FAILS** on
`[0.00,0.15]` (`NOT_LOCAL_ROOT_CONNECTABLE`) and `[0.45,0.55]` (`polygon network
not valid`). **The ALM chooses `t`, and it can converge into a hole a fixed-`t`
solve would have stepped over.** `cp_mv_broken` also moves with `t` (6 on
`[0.20,0.85]`, 2 on `[0.90,1.00]`).

---

## 5. Architecture

### 5.1 The selector — raw paper-space axial offset, post-remap

Fire the pin on leaf `n` iff `n` is unpaired **and** its raw paper-space
distance from the symmetry axis exceeds a named threshold.

> ### ⚠ `_unpaired_laterals` IS A TRAP as the selector — five independent reasons
>
> **(a) It returns the EMPTY LIST on all five committed subjects** at its
> production call site (`mesh_to_tree.py:508`, pre-escalation). Gating on it
> makes S3 **a total no-op on the entire scorecard.**
> **(b) Wrong SPACE** — it measures distance from the *mesh's* PCA bilateral
> plane (`SYMMETRY_TOL = 0.10` of mesh scale, 146.4 on quadruped), not the
> paper's diagonal.
> **(c) Mesh-side only** — unavailable on the template path;
> `template-humanoid` and `template-insect` would silently get no pin.
> **(d) WRONG SET by its own docstring** (`:434-437`): *"An unpaired leaf ON the
> plane is a head or a tail and is expected. An unpaired leaf well OFF it is a
> limb whose twin the matcher failed to find."* **S3 wants the complement.**
> Pinning quadruped's n8/n9 (siblings at 0.246089/0.269426, a missed left/right
> pair) would **turn two legs into two head flaps.**
> **(e) Stale + wrong id space** — computed pre-escalation, returns original
> skeleton ids while `to_metric_tree.py:619` remaps via `_bfs_remap`.
>
> `tree_contract.py:313-330` has the midline concept and **currently mislabels
> the hardest case**: `template-insect` node 10 passes its *"one unpaired leaf
> alone on a hub is a head or tail"* heuristic yet lands at (1.0, 0.0),
> d = **−0.707107**, maximally off-axis.

### 5.2 Order is load-bearing and silent if wrong

`tmScaleOptimizer::Initialize` walks conditions **exactly once**
(`tmScaleOptimizer.cpp:90-92`), inside `run_scale_optimization`
(`TreemakerWrapper.cpp:464`). **Bound after, the pin is a total no-op that
reports nothing** — every `pin_after` arm measured byte-identical to base.

```
init_paper → build_tree_from_json → [symmetry loop] → ★ PIN HERE
           → run_scale_optimization → _apply_stub_repair → build_and_export
```
(`server.py:180-192`)

### 5.3 The plumbing is the real cost — SEVEN call sites

An `axis_nodes` list must reach every `for a, b in pairs: engine.apply_symmetry(...)`
loop:

| site | note |
|---|---|
| `server.py:185` `_worker_full_base` | parent path |
| `server.py:227` `_worker_compile_recipe` | recipe dict; keys `:77`, built `:2720` |
| `server.py:274` `_worker_free_paper` | |
| `server.py:338` `_run_ladder_child._try_once` | **the real serve for anything not packing attempt-0** |
| `server.py:1802` | the `apply_symmetry` MCP tool |
| `structural_search.py:107` | |
| **`tests/runner.py:24`** | **the GOLDEN and verdict path. Miss it and the scorecard moves while the goldens do not.** |

Plus `draft_and_compile_full_base` (`:1701-1756`) threaded through
`_run_isolated` → `_worker_full_base` and `_compile_with_perturb` →
`_run_ladder_child` (four sites: `:1870, :1895, :1981, :2233`).

**Latent adjacency to inherit:** `mPinned` is cleared in `build_tree_from_json`
(`:226`) but **NOT** in `load_and_export_tmd` (`:1011-1015`, which does
`delete mTree`), leaving raw `tmNode*` into freed memory. Not live today; a new
axial-pin ledger has the same shape — **clear it in both places.**

---

## 6. Pre-declared movement — read before calling anything a regression

### 6.1 `cp_mv_broken` goes `None → NON-ZERO`. Guaranteed, not likely.

22 of 22 measured arms returned 2, 4 or 6. **Zero arms returned 0.**
Distribution `{6: 14, 2: 6, 4: 2}`. This is **G2b becoming *evaluable*** where
`is_bijection False` currently forces `None`
(`benchmark_subjects.py:242-243`) — the defect S2a proved the engine cannot fix.
**It is S3 working correctly.**

| subject | today | S3 prediction | basis |
|---|---|---|---|
| **bird** | `None`, res 0.053492 | `cp_mv_broken` **→ 4**, res → 0.0 | measured, both packing arms |
| **humanoid** | `None`, res 0.378336 | **→ 2 or 6** (6 on 11 arms, 2 on 3; **2** at the scale-maximising pin) | measured, position-dependent |
| **fish** | `None`, res 0.121893 | **UNKNOWN — measure, do not predict.** Needs ONE interior pin (n12, axis_d 0.141848); n3/n8/n11 already axial, both diagonal corners taken. Its 0/9 proxy failure is **uninformative** — the no-pin control on the same path also fails. Only packs via the PLACEMENT rung. | |
| **quadruped** | `None`, res 0.374146 | **expected NO CHANGE, with a real risk of going UNSERVED** — §10 #3 | |
| **insect** | `6`, res 0.0 | **NO-OP. Must not move.** Zero unpaired leaves (4 declared pairs cover all 8 served leaves). | |

### 6.2 Goal-1-owned columns

`hull_coverage` is a pure function of the served fold
(`benchmark_subjects.py:226`), so it moves wherever geometry moves: **bird,
fish, humanoid, quadruped**; insect unmoved. `design_scale` (not yet in `_COLS`)
moves on the same four.

⚠ **Do NOT predict the sign.** Measured both directions on one subject: humanoid
scale ranges 0.668467 (−4.7%) to 0.775554 (+10.6%) across pin positions, with
**11 of 14 packing arms BELOW the served scale**. `template-humanoid` coverage
went **DOWN** 0.558981 → 0.551916 while scale rose 8.4%. Per CLAUDE.md §1.1(4)
the trade is argued **per subject and per pin position**, and the spec names the
expected position **before** reading the sign.

---

## 7. Acceptance criteria — measurements, on axes measurable at this point

1. **`is_bijection` → True** and **`cp_mirror_residual` → 0.0** at
   `axis_degrees=45.0` on **at least `humanoid`**, which is the measured win.
2. **`cp_mv_broken` stops being `None`** on every subject whose bijection is
   created, and the value **matches §6.1's pre-declared prediction** or the
   deviation is reported as a finding.
3. **`insect` byte-identical.** Zero unpaired leaves; any movement is a defect.
4. **`quadruped` and `bird` byte-identical** — the offset gate must skip them
   (both already axial at 0.0). **A non-byte-identical result here means the
   gate is wrong**, not that the pin helped.
5. **No subject goes UNSERVED.** Explicit gate; §10 #3.
6. **Telemetry is non-vacuous**: with an axial pin bound, `n_pins > 0` and the
   report carries a real axial residual. **Assert a known-bad input**
   (`COORDINATION.md` §4.1): bind an axial pin, perturb the leaf off-axis, and
   assert the instrument **reports the violation**. Without that, §3.1 ships.
7. **A constraint-level unit test at ≥1 NON-45 angle** asserting
   `StickToLineFn::Func == 0` for an on-axis point — see §9's REJECT row on
   Lang's published equations. Cheap insurance against a defect that is
   invisible at 45°.
8. Full suite at the `e100cf1` baseline **2386 passed / 10 skipped / 0 failed**
   (⚠ that run took 24:03 against an expected ~15 min because of a 15.1h-CPU
   orphan since killed — re-baseline the timing).
9. `benchmark_subjects.py --baseline fixtures/scorecard_baseline.jsonl`, every
   moved row attributed. **Never `--out`.**

> ⚠ **NOT an acceptance criterion: `cp_symmetric is True`.** Measured False on
> 22 of 22 pin arms and on insect as served today. It **fails on S3's own
> showcase subject**, because G2b is untouched and unfixable in the engine.

---

## 8. Test surface

**INVERT — 4 params**, `tests/test_cp_mirror_serve.py:181-207`:
`test_mesh_validation_tree_verdicts_are_pinned[bird|fish|humanoid|quadruped]`,
each asserting `is_bijection False`, an exact residual, and
`mv_swapped/mv_mismatched IS None`. These are **red pins on the defect**; an
acceptance wording of *"all existing tests stay green"* is unsatisfiable.

**PROTECT — S3's regression canaries:**
`[insect]` (already bijective, must not move) ·
`test_quad_the_negative_control_the_shipped_metric_scored_perfect` (QUAD has
`pairs == []`, structurally unreachable) ·
`test_template_quadruped_is_pinned_red_on_mv_and_is_S2s_target` — **its
`offender_edges` assertion pins exact vertex indices
`{frozenset((13,15)), frozenset((22,15))}`, the most brittle thing in the blast
radius**, and `TEMPLATE_QUADRUPED` IS in S3's exposed set.

**Goldens: exactly ONE moves — `dog-repaired.fold`.** `bless.py:58-82`
regenerates only `[star-4, hshape, quad, dog-repaired]`; star-4 and quad have no
axis, hshape has zero unpaired leaves. All five files named in the original
brief (`test_flat_fold`, `test_layer_order`, `test_rigid_fold`,
`test_shaping_deep`, `test_fold_mutate`) are **SAFE — none reads it.**

**Its three consumers, two invisible to a grep for `dog-repaired`:**
`test_geometry.py::test_geometry_matches_golden[dog-repaired]` ·
`test_mv_repair.py:815-824` (`glob`, `assert seen == 9`) ·
`test_paper_coverage.py:282-291` (`glob`, `assert len(golden_paths) == 9`,
asserts `source == "boundary_cycle"`).

**Also at risk:** `test_verdicts.py::test_verdict_matches_baseline` ×7 ·
`test_templates_attempt0.py` ×5 + `test_raw_dog_still_fails_clean` ·
`test_read_base.py::test_attempt0_unchanged[dog-repaired]` ·
`test_template_distinctness.py` · `test_dog_ladder_rescue.py` (6) ·
`test_perturb_symmetry.py` (its `QUAD_NODES` is `TEMPLATE_QUADRUPED`) ·
`test_pair_reconcile.py:1249`.

---

## 9. Prior art (CLAUDE.md §0)

| verdict | item | citation | why |
|---|---|---|---|
| **ADOPT** | `tmConditionNodeCombo::SetToSymmetryLine(true)` → `StickToLineFn` | `tmConditionNodeCombo.cpp:168/206/233/260`; `tmConstraintFns.cpp:592-624`; `tmTree.cpp:1498` | Lang wrote S3's constraint. Already compiled into the shipped `.so`. A flag on an already-bound class. |
| **ADOPT** | Lang's two-class taxonomy and the UI precedent | `TreeMkr40.pdf` §2.2 (pp.15-24), §4.5.32, §6.6; ODS appendix A.6 | Conditions ▸ *"Node fixed to symmetry line"*. **Tutorial 2.2 works this exact problem** — the head node of a bilaterally-symmetric figure. A node *"can actually lie on the line of symmetry… or it can be one of a pair."* **We ship only the pair class.** |
| **ADOPT** | Lang's *"spontaneous symmetry-breaking"* as vocabulary **and expectation** | `TreeMkr40` §2.2: scale 0.277 unconstrained → 0.272 book (−1.8%) → 0.2626 diagonal; *"when you add constraints to a pattern, you will reduce the scale"* | Names our phenomenon exactly, and sets the prior that S3 **costs** scale. |
| **ADAPT** | Analog-IC placement: symmetry pairs vs **self-symmetric modules** centred ON the axis | Lin/Chang/Lin, *Analog Placement Based on Symmetry-Island Formulation*, TCAD 2009, Def. 3; corroborated US7873928B2 | Independently arrives at **Lang's identical taxonomy**; the self-symmetric class is precisely our missing constraint. Adopt the taxonomy, **reject the technique** (below). |
| **ADAPT (weakened)** | *"linear equality is cheaper"* | `tmNLCO_alm.cpp:82-96` vs `tmNLCO_cfsqp.cpp:113-129` | **Buys nothing here** — `AddLinearEquality` and `AddNonlinearEquality` have **byte-identical bodies** pushing to the same `mEqns`; only the `#undef`'d CFSQP separates them. The real win over corner/edge flags is a *constant* gradient vs `CornerFn`'s quartic — **conditioning, not constraint handling.** |
| **REJECT** | **Lang's published equations (A-20)/(A-21)** as an implementation source | ODS appendix + `TreeMkr40` §6.6, vs `tmConstraintFns.cpp:606-610` | **They disagree with his own working code — a sin/cos SWAP.** For a point exactly ON the axis, (A-20) gives **+0.310** at 0°, +0.155 at 30°, −0.310 at 90°, and 0 **only at 45°**; the code gives 0.000000000 at all four. **They coincide with the code at exactly the 45° this engine hard-codes**, so a manual-derived implementation is right today and **silently wrong the instant Goal 1 enables the book axis.** Recorded nowhere in this repo. → acceptance criterion §7.7. |
| **REJECT** | packing literature's *"symmetry-breaking constraints"* | Costa/Hansen/Liberti, *Discrete Applied Math* 2013 | **Category error** — they prune equivalent optima to shrink a B&B tree, constraining the SEARCH SPACE; S3 constrains the ANSWER. One transferable warning, negative: *"seemingly reasonable symmetry-breaking constraints may, in fact, degrade performance."* Also confirms optimal packings are frequently asymmetric. |
| **REJECT** | variable elimination (the theoretically cleaner answer) | `tmConditionNodeCombo.cpp:200-202`, `tmConditionNodeSymmetric.cpp:95-98` | Every condition opens with `GetBaseOffset(mNode)` into one shared vector; eliminating a coordinate **shifts every downstream index** the pair rows and all other conditions key on. Equality-constraint is correct here because it is **index-preserving and additive.** |
| **REJECT** | CAD over-constraint diagnosis by DOF counting | Demaine/Fekete/Lang, *Circle Packing for Origami Design Is Hard* | The binding constraints are **quadratic path inequalities**, not a countable DOF balance. Transferable part is only vocabulary: **REDUNDANT** pin (consistent, no scale change) vs **INCONSISTENT** pin (kills the pack) — and report which. |
| **HONEST NEGATIVE** | **No second, independent implementation of a tree-method on-axis node condition exists.** | ORIPA / Oriedita / Orihime are CP editors and flat-foldability checkers, not tree-method optimizers. Every search hit traced back to Lang. The one adjacent computational-origami hit is **axisymmetric** (rotational), not bilateral. | **There is NO external oracle for this constraint's semantics — the vendored C++ is the only ground truth.** That is exactly why the (A-20)/(A-21) defect went undetected for years, and why the plan must diff against **code, never prose.** |

---

## 10. Risks, ranked

**#1 — the shipping mechanism is 1-for-4.** §4. Mitigation is structural: offset
gate + rung-with-fallback. Without both, S3 breaks two serving subjects.

**#2 — ALM CANNOT REPORT INFEASIBILITY.** `tmNLCO_alm.cpp:186
ITER_OUTER_MAX = 50`; `:342-343` *"If we got here, we never found a feasible
solution"* → `ERROR_TOO_MANY_ITERATIONS`. **An over-constraining pin is
indistinguishable from slow convergence.** Attribution for any new pack failure
must come from an explicit pinned-vs-unpinned A/B, **never the return code**.
Precedent: a scorecard re-bless without attribution previously absorbed a
quadruped jitter→stub regression invisible to both phase-B gates.

**#3 — QUADRUPED is the subject most likely to be mis-specced, and it can go
UNSERVED.** Three blockers stack: **(a)** it serves at `rescue_stage='stub'`
with **three engine-made flaps at `json_id -1`** (two off-axis, no mirror
partner) and a stub is structurally absent from any Python node list, so **S3
has no id to pin**; **(b)** `PinTarget` **throws** when `mStubApplied`;
**(c)** the no-pin direct control already fails. Pre-declare expected-no-change
**plus an explicit must-not-go-unserved gate**.

**#4 — the vacuous-pass trap.** §3.1. Extend `struct Pin` **in the same commit
as the flag**, or the telemetry actively lies.

**#5 — `_unpaired_laterals` as the selector.** §5.1, five reasons.

**#6 — SILENT NO-OP ON ZERO-PAIR TREES, and v5 reports it FEASIBLE.**
`tmConditionNodeCombo.cpp:169` gates on `HasSymmetry()` with no `else`;
`CalcFeasibility` **skips** the check when `HasSymmetry()` is false, leaving
`mIsFeasibleCondition = true` — **it reports an unenforceable condition as
satisfied.** Lang's v4 `tmConditionNodeSymmetric.cpp:78-80` does the opposite.
This qualifies *"v5 is strictly better"* in project memory: **v5 is cheaper to
bind, v4 is honest when the axis is missing.** Engine default is
`mSymAngle = 90` (`tmTree.cpp:1904-1910`), **not 45**. **The binding must set
the axis itself or refuse loudly** — and a tree whose only asymmetry is one
unpaired axial leaf is exactly the tree most likely to have no pairs.

**#7 — order.** §5.2. Bound after `run_scale_optimization`, the pin is a silent
total no-op.

**#8 — DO NOT CROSS-CITE THE TWO "SAME-NAMED" TREES.**
`fixtures/scorecard_baseline.jsonl` and `mesh_validation_trees.json` are
**different trees**: fish 0.121893 vs 0.20771, quadruped 0.374146 vs 0.09055,
insect cardinality 45/45 vs 28/28. **Only bird and humanoid are the same tree
under two names.**

**#9 — QUAD's basins flip the VERDICT, not just coordinates.** macOS →
`is_bijection True, 13/13, residual 0.0, mv_mismatched 6`; the committed Linux
basin coords → `is_bijection FALSE, 0/13, residual 0.191534`. **The basin note's
claim that the two agree on M/V is true of edges but FALSE of the mirror
verdict — that note may itself need correcting.** QUAD is unreachable by S3, but
`template-quadruped`'s −18.5% collapse is exactly the shape a basin flip takes.

**#10 — macOS only, one machine.** Treat every exact scale figure and the
pack/no-pack boundary as platform-local until reproduced in `ci-amd64-run`. The
bird arm's `proj_iters` **saturates at `maxIters = 50`**, so the margin-to-cliff
proxy is censored on the arm the headline rests on.

---

## 11. ⚠ Cross-goal — two corrections Goal 1 needs

### 11.1 The bird figures are real but describe the WRONG TREE

`COORDINATION.md`'s S5 gate and
`2026-08-04-whole-square-axis-projection-design.md:515` cite *"bird coverage
0.5206 → 0.6612 and scale 1.3093 → 1.3518"*. **All four numbers reproduce to
every printed digit** — on `mesh_to_metric_tree(bird.glb, voxel_res=64,
prune_fraction=0.3)`. **That is not the scorecard bird**, which is
`auto_mesh_to_metric_tree` (voxel 96 / prune 0.25):

| | cited bird | served (scorecard) bird |
|---|---|---|
| n_vertices | 18 | 16 |
| pre-pin residual | 0.31888046266041714 | 0.053492 |
| pre-pin scale | 1.3093489151225457 | 1.0958851613085505 |
| pre-pin coverage | 0.520584140723775 | 0.4999519236548833 |
| post-pin | 19/19, res 0.0, scale 1.3517822643596629, cov 0.6612153075406755 | 18/18, res 0.0, scale 1.5159976, cov 0.9847830 |

**`COORDINATION.md` must name the extraction config or be restated with the
served bird's own figures.** As written it argues against numbers that were
never the scorecard's.

✅ **The convexity concern Goal 2 raised on 2026-08-06 is CLOSED — no correction
needed.** The post-pin outline **is convex**: `hull_area − poly_area = 3.809e-10`
(relative 5.76e-08 %), no boundary vertex more than 5.42e-10 inside the hull,
worst turn −4.34e-09. Both readings are `source = "boundary_cycle"`. Running the
pre-0b convex-hull instrument on the same fold gives 0.661215307922 vs the 0b
true-polygon 0.661215307541. **The old instrument overstated 0.6612 by nothing.**

Also: **`benchmark_subjects.py:229-231` says the served bird fails on 4 of 18
vertices. It is 4 of 16.** Same conflation at
`2026-08-04-cp-mirror-metric-design.md:72`.

### 11.2 ⚠ On the served bird, S3 and Goal 1's S5 measure the SAME intervention

The only on-axis pins that build on the served bird put the unpaired leaves on
the two diagonal **CORNERS** (node 3 → (0,0), node 5 → (1,1)); corner occupancy
goes 0 → 2, coverage 0.4999519 → 0.9847830 (**+97%**), scale +38%. **That gain
is corner occupancy — Goal 1's own lever.** If S3 lands that configuration and
S5 re-measures, **the coverage-versus-scale argument will attribute Goal 1's win
to Goal 2's slice.**

---

## 12. Open items — measure before dispatching §B

| unknown | what settles it | cost |
|---|---|---|
| **Does the 1-DOF constraint converge to the symmetric optimum, or into a hole?** Every headline number is a 0-DOF proxy. 1.3518 / 0.6612 prove a symmetric optimum **EXISTS and is reachable** — an existence proof, not a forecast. | Run the **already-built prototype `.so`** on the five scorecard subjects through `server.draft_and_compile_full_base` (**not** a bare compile). **Highest-value pre-dispatch measurement.** | ~1 hour |
| **fish** — unknown, not negative | same run, through the PLACEMENT rung | included |
| **quadruped** — can stub flaps be pinned at all? | does the axial gate fire *before* `_apply_stub_repair`? | ~30 min |
| **Does the `syms` self-pair hold the leaf, and change convergence?** Algebra verified, numerics not. | add self-pair rows to the prototype; read `proj_iters` and axial residual on all four templates. Watch `maxIters = 50` saturation. | ~45 min |
| **Which pin position does the ALM select?** `cp_mv_broken` (2 vs 6) and the scale sign both depend on it. | read the converged position off the 1-DOF solve | included |
| **Linux.** Zero readings. | `ci-amd64-run`, four-template arm, **before** re-blessing anything | ~1 hour |

**The originating bird probe is NOT in the repository** — the literals appear
only as prose in `COORDINATION.md`, the axis-projection design doc, and memory.
No fixture, no `probe_*.py`, nothing in `git log --all --diff-filter=D`. The
reproduction is a **reconstruction**. **Commit it** (`probe_s3_final.py`) so the
next slice does not re-derive it.
