# Slice 0 — Boundary placement conditions (leaf nodes on paper edges and corners)

**Date:** 2026-08-02
**Status:** design, revision 2, awaiting review
**Author:** brainstorming session (Claude + raphaeldchen)
**Companion:** the visual-feedback-loop spec (separate document). This slice is
sequenced FIRST and has no dependency on it.

> **Revision 2 (2026-08-02), after a five-lens audit.** Four load-bearing
> decisions in revision 1 did not survive verification. Summarised in §10; the
> two that change what gets built are (a) the slice now binds Lang's **v5**
> `tmConditionNodeCombo`, not the **v4** classes revision 1 chose, and (b) the
> stated mechanism ("largest packing-efficiency lever") was **backwards** for
> the quantity the optimizer maximises and has been rewritten.

---

## 1. Why this slice exists

COrigami (arXiv:2606.26299, Zahavy et al. incl. R. J. Lang) Appendix A names
four manual TreeMaker interventions their fully-automated baseline bypassed,
and reports that baseline at **1.1% success on n=66,036**, with **74.4% of all
attempts** dying at crease-pattern construction. Verbatim:

> "imposing symmetry conditions by pairing nodes about a symmetry line,
> fracturing high-order polygons by adding auxiliary stubs, **forcing leaf
> nodes to paper edges to reduce layer count**, and manually repositioning
> nodes to escape local optima."

Two of the four we have already shipped: auxiliary-stub fracturing (S5,
`FindLargestStub`) and node repositioning (S1/S3 placement seeds + order
multi-start). Of the remaining two:

- **Symmetry pairing about a symmetry line — ALREADY SHIPPED.**
  `TreemakerWrapper.cpp:302 apply_symmetry` establishes a real symmetry axis
  and applies `tmConditionNodesPaired`, wired through `server.py:185,217,264,309`,
  `structural_search.py:107`, and its own MCP tool at `server.py:1621`. What
  misled an earlier survey is naming drift: `CLAUDE.md` §4A documents
  `set_symmetry(axis, node_pairs)`; the real tool is
  `apply_symmetry(node_a, node_b)`. **No work is proposed here.**
  *(Provenance note: that drift is present in `main` but already deleted by an
  uncommitted working-tree edit in this worktree. Whichever lands first, this
  paragraph's citation should be re-checked, not trusted.)*
- **Forcing leaf nodes to paper edges/corners — GENUINELY UNSHIPPED.** This
  slice.

### 1.1 What the lever actually is — and what it is not

**Revision 1 claimed boundary placement is "the largest single
packing-efficiency lever in tree theory". That is false for the quantity
TreeMaker optimises, and the direction is backwards.** Verified in the
vendored source:

| Fact | Evidence |
|---|---|
| Every leaf coordinate is already bounded to the paper rectangle: `bl = 0`, `bu = (w, h)` | `tmScaleOptimizer.cpp:49-61` |
| The objective is `-u[0]` — pure scale maximisation | `tmScaleOptimizer.cpp:180` |
| There is **no** circle-area, paper-coverage, or packing-efficiency term anywhere in the optimizer | grep for `area\|coverage\|circle` over `tmScaleOptimizer.cpp` → no matches |

Corner and edge positions are therefore **already inside the feasible set**.
A boundary condition adds *equalities*, which strictly **shrink** it — so the
global-optimum scale is **non-increasing**. Constraining leaves to the
boundary cannot raise the design scale, and may lower it.

Two independent sources point the same way. COrigami's own stated motive is
"to reduce **layer count**", not efficiency — revision 1 dropped that clause
when quoting the passage.

And **Lang's own manual measures the effect and states the rule** (TreeMaker
4.0 manual, §3.3, pp. 49-52; verified directly against the PDF at
`langorigami.com/wp-content/uploads/2015/09/TreeMkr40.pdf`):

| Case | Scale | Figure |
|---|---|---|
| 5 equal flaps, all forced to edges | **0.323** | 3.3.2 |
| 5 equal flaps, one allowed into the middle | **0.353** — "significantly larger" | 3.3.3 |
| 7 equal flaps (no configuration avoids a middle flap) | 0.268 | 3.3.4 |
| 8-point base, all edge flaps | 0.250 | 3.3.7 |

His conclusion, verbatim: "the most efficient crease pattern will have at least
one middle flap" — for five or more flaps. **Every subject in our corpus has
≥5 leaves.**

**And Lang gives three reasons to force edge flaps. None is efficiency.**
Ease of collapsing the crease pattern into a base; **layer count** — an edge
flap has half the layers of a middle flap of the same width, so a flap that
will be folded further is easier to fold as an edge flap; and **colour
change** — TreeMaker bases are inherently single-colour, and only an edge flap
can be turned inside-out around its raw edges. COrigami's "to reduce layer
count" is Lang's second reason, quoted back.

### 1.2 The uncomfortable corollary

Lang's documented remedy for **the exact failure this slice targets** points
the opposite way. On many-sided polygons — our "polygon network is not valid"
class — his advice is to drag a node **into the centre of the big polygon** and
re-optimize, i.e. deliberately create a **middle** flap. He also confirms the
solver framing: TreeMaker finds local, not global optima, and unused space in
the crease pattern is a cue to rearrange circles and restart.

That is not a reason to abandon the slice — boundary placement changes which
basin the solve finds, and Lang is describing a human working interactively
with global judgement we do not have. But it does mean **boundary placement is
not obviously the right lever for high-order-polygon failures**, and R12
records the alternative the manual actually recommends.

**So what is the lever?** ALM is a local solver on a non-convex problem.
Boundary conditions do not enlarge the optimum; they change **which basin the
solve lands in** — the same mechanism as node-order restarts and placement
seeds, both of which measurably rescue trees without improving any global
bound. Boundary placement is therefore a lever of the **same class** as
`order` and `placement`, not a stronger one, and this slice is justified only
if it rescues trees those two do not.

That reframing has three consequences carried through this document: §4.3's
ladder ordering no longer rests on "strictly stronger"; §4.4 must measure
**design scale** so the slice can detect the regression it is most likely to
cause; and the C++ doc comment in §4.1 must not repeat the efficiency claim.

The failure class remains the target: "polygon network is not valid", 11/13
unrescued at the time of the 2026-07-25 plan.

---

## 2. Prior art (CLAUDE.md §0)

| Source | Finding | Adopted / rejected |
|---|---|---|
| COrigami Appendix A (arXiv:2606.26299) | Names leaf-to-paper-edge forcing as one of four interventions; motive is **layer count** | **Adopted** — this slice, with the motive restored |
| **Lang's own v5 API: `tmConditionNodeCombo` + `tmTree::SetNodesFixedToPaperEdge/Corner`** | "new in version 5; it combines the functionality of `tmConditionNodeFixed`, `tmConditionNodeSymmetric`, `tmConditionNodeOnEdge`, and `tmConditionNodeOnCorner`" (`tmConditionNodeCombo.cpp:16-22`) | **Adopted — this is the redirection.** §3, §4.1 |
| Vendored `tmConditionNodeOnEdge` / `tmConditionNodeOnCorner` (v4) | Lang's earlier implementation, superseded by Combo; reachable only via the `...v4` entry points, which have **zero callers** | **Rejected** — §3.2 gives the three reasons |
| **Lang, TreeMaker 4.0 manual §3.3 (verified against the PDF)** | Boundary flaps cost scale (5 flaps: 0.323 all-edge vs 0.353 with a middle flap); the three stated reasons to force them are collapse ease, **layer count**, and colour change | **Adopted as the mechanism** (§1.1) and as a caution — the objective is not efficiency |
| Lang, same manual, §4.5.29-4.5.32 | His UI exposes four distinct conditions: fix one or both **coordinates** to a value, fix to corner, fix to edge, fix to symmetry line | **Adopted** — this is Combo's flag set exactly, and independent confirmation that the coordinate route (§4.2) is the intended one |
| Lang, same manual, general advice | Many-sided polygons → drag a node into the polygon's **centre**; TreeMaker finds local not global optima | **Noted as a counter-indication** — R12 |
| Our own S1/S3 order restarts and placement seeds | Basin selection in a non-convex solve rescues trees no global bound predicts. *(The "~9× cheaper" figure in the parent plan was measured for node-ORDER restarts, `plan:15-17` — not for placement seeds, as revision 1 stated.)* | **Adopted** — boundary is the same *class* of lever |
| "Is Self-Repair a Silver Bullet?" (ICLR'24, arXiv:2306.09896) | Breadth over depth at fixed budget | **Adopted** — small variant fan, not a deep search. *(Revision 1 attributed this to RTLFixer arXiv:2311.16543, which makes no such claim; the parent plan splits them correctly at `plan:36-37`.)* |
| RTLFixer (arXiv:2311.16543) | RAG-guided error feedback for HDL repair | Cited for the agent-loop pattern only |
| MCTS over feasibility-checked edit moves (IJCAI'23, arXiv:2211.13219) | Search over a discrete constrained action space | Noted; **rejected for now**. *(Revision 1 credited it with a "discrete beats continuous perturbation" comparison it does not make.)* |
| COrigami's discrete box-pleating packer | Their Fig. 7 shows failure mass shifting into *their* packer as flap count rises | **Rejected** — do not rewrite Tier 3 |

**No competitor exposes this as an automated rescue stage** — TreeMaker's
conditions are a manual GUI action in Lang's workflow, so automating their
*selection* is the novel part. *(Asserted, not demonstrated: no systematic
search for prior work on automatic node-to-boundary assignment was run.)*

---

## 3. What already exists (verified 2026-08-02, revision 2)

### 3.1 `tmConditionNodeCombo` — the class this slice binds

| Fact | Evidence |
|---|---|
| Declared "new in version 5", combining Fixed / Symmetric / OnEdge / OnCorner | `tmConditionNodeCombo.cpp:16-22` |
| **Public constructor**, taking `aToSymmetryLine, aToPaperEdge, aToPaperCorner, aXFixed, aXFixValue, aYFixed, aYFixValue` | `tmConditionNodeCombo.h:37-40` |
| Full getter set — `GetToPaperEdge`, `GetToPaperCorner`, `GetXFixed`, `GetXFixValue`, `GetYFixed`, `GetYFixValue`, `GetToSymmetryLine` | `.h:43-49` |
| Full setter set, plus `SetNode` | `.h:53-60` |
| Lang's own list-taking public API drives it via the standard idiom | `tmTree.cpp:1506 SetNodesFixedToPaperEdge`, `:1521 SetNodesFixedToPaperCorner` — both open a `tmTreeCleaner` and call `GetOrMakeOnePartCondition<tmConditionNodeCombo, tmNode>` |
| Stream tag | `tmConditionNodeCombo.cpp:329` `"CNxn"` |
| Registered in the `InitTypes` type array (the documented gotcha — clear) | `tmPart.h:334`, beside `tmConditionNodeOnCorner` `:336` and `tmConditionNodeOnEdge` `:338` |
| **Compiled into the shipped extension** | `nm` on `headless_treemaker.cpython-314-darwin.so`: 36 `tmConditionNodeCombo` symbols (v4 pair: 41 each; `tmConditionNodesPaired`, which `apply_symmetry` uses in production: 32) |
| Leaf-only, like the v4 classes | `.cpp:151-154` `IsValidCondition() { return (mNode != 0) && (mNode->IsLeafNode()); }` |
| **The ALM backend we build supports both equality kinds it emits** | `tmNLCO_alm.cpp:92 AddNonlinearEquality`; linear equalities via `AddLinearEquality` |
| References outside vendored source: **zero** | grep for `NodeOnEdge\|NodeOnCorner\|NodeCombo` excluding `treemaker/Source` → no matches |

### 3.2 Why not the v4 classes (revision 1's choice)

Its `AddConstraints(tmScaleOptimizer*)` is the whole argument:

```cpp
if (mTree->HasSymmetry() && mToSymmetryLine)
  AddLinearEquality(new StickToLineFn(ix, iy, mTree->mSymLoc, mTree->mSymAngle));
if (mToPaperEdge)
  AddNonlinearEquality(new StickToEdgeFn(ix, iy, w, h));      // quartic
if (mToPaperCorner) {
  AddNonlinearEquality(new CornerFn(ix, w));                  // x in {0, w}
  AddNonlinearEquality(new CornerFn(iy, h));                  // y in {0, h}
}
if (mXFixed) AddLinearEquality(new OneVarFn(ix, -1., mXFixValue));
if (mYFixed) AddLinearEquality(new OneVarFn(iy, -1., mYFixValue));
```

The first three branches are *exactly* what the v4 classes provide. The last
two exist only on Combo, and they decide the slice:

**(a) The v4 conditions cannot name a slot.** `CornerFn::Func` is
`u[ix] * (u[ix] - w)` (`tmConstraintFns.cpp:1657-1661`) — roots at `0` and
`w`. Two of them constrain `x ∈ {0,w}` and `y ∈ {0,h}`: *any* corner, with
nothing coupling two conditioned nodes. **Five nodes all at (0,0) satisfy all
ten equalities exactly.** `StickToEdgeFn::Func` is
`W · u[ix](u[ix]−w) · u[iy](u[iy]−h)` (`:553-557`) — a product, zero on any
edge and also zero at every corner.

This is not a nitpick: §4.2's entire policy decides *which* boundary slot each
leaf takes, and under v4 that decision has **no mechanism to express it**.
`SetXFixValue`/`SetYFixValue` express it exactly.

**(b) Linear beats quartic on the backend we actually build.** `OneVarFn`
emits a **linear** equality. `StickToEdgeFn` is a degree-4 polynomial whose
gradient (`:563-567`) *vanishes at the corners*. R1 — "ALM diverges" — is this
spec's top risk and the sole basis for its Phase A stopping rule, and it is
much smaller against linear equalities. This matters more here than in Lang's
own build: CFSQP, the backend he tuned these against, is absent from ours.

**(c) Read-back is free, and rule 5 becomes true.** Revision 1 proposed
building `get_boundary_conditions()`; Combo's getters already are it.
Separately, revision 1's rule 5 ("a fifth corner condition is infeasible by
arithmetic") is **false** under v4 — see (a) — and becomes true under the
coordinate route, where two nodes cannot be pinned to the same corner without
making the path inequalities infeasible.

**(d) A lever revision 1 did not consider.** `SetToSymmetryLine(true)` emits a
*linear* `StickToLineFn` against the axis `apply_symmetry` already establishes
(`TreemakerWrapper.cpp:311-313`: paper centre, 45°). A bilateral animal's
**axial** leaves — head and tail — belong on the mirror line, not at a corner,
and `mesh_to_tree.label_leaves` already identifies head/tail extremity
candidates (`mesh_to_tree.py:617-622`). Three pieces built separately that have
never been connected.

So this remains a **binding** slice, not an algorithms slice — but of a
different, better class than revision 1 identified.

### 3.3 Citation corrections carried from the audit

Revision 1's §3 table was substantially right and off by one line in several
places. Corrected: the class declarations are `tmConditionNodeOnEdge.h:30` /
`tmConditionNodeOnCorner.h:30` (`:31` is `public:`); `friend class tmTree;` is
`:70` (`:69` is `friend class tmPart::CreatorFnT<...>`) — and `friend class
tmNode;` is present at `:71`, so **R7's premise needs re-checking** if the v4
path is ever revisited. `ORDER_MARKER` is `rescue_ladder.py:153` and
`PLACEMENT_MARKER` `:154` (revision 1 said 152/153); `NORMALIZE_MARKER` `:161`
is correct; `STUB_MARKER` is `:174`; the invariants block is `:145-152`.
`mcp_harness/CMakeLists.txt` points `TM_SRC` at a repo-root `treemaker/` that
does not exist and cannot configure — the real build path is `Makefile:12-14`
→ `mcp_harness/build.sh:16,39`. The underlying "both compiled" claim is true
and was re-confirmed by `nm` (§3.1).

---

## 4. Design

### 4.1 Wrapper bindings (`TreemakerWrapper.cpp`)

Three methods over Combo, following the `set_edge_strain_fixed` idiom
(`TreemakerWrapper.cpp:326-345`) including its invalidation guard:

```cpp
/*
 * Constrain a leaf node's position via tmConditionNodeCombo (Lang's v5
 * condition; the v4 tmConditionNodeOnEdge/OnCorner pair it supersedes cannot
 * name WHICH edge or corner, and emits a quartic equality where these emit a
 * linear one -- see the design spec section 3.2).
 *
 * Boundary placement does NOT raise the design scale: tmScaleOptimizer
 * already bounds every leaf coordinate to the paper rectangle and maximises
 * scale with no coverage term, so adding equalities can only shrink the
 * feasible set. The lever is BASIN SELECTION in a non-convex ALM solve --
 * the same mechanism as node-order restarts and placement seeds.
 *
 * Constrains POSITION only; edge lengths are untouched, which is why the
 * boundary rung is proportion-PRESERVING.
 */
void set_node_at(int node_id, double x, double y);   // corner or exact point
void set_node_on_x(int node_id, double x);           // vertical edge, y free
void set_node_on_y(int node_id, double y);           // horizontal edge, x free
```

Each resolves to `GetOrMakeOnePartCondition<tmConditionNodeCombo, tmNode>` and
sets the corresponding `XFixed`/`XFixValue`/`YFixed`/`YFixValue` pair, exactly
as `tmTree::SetNodesFixedToPaperEdge` does for its own flag.

Binding rules, each with a reason:

1. **Reject after a structural stub repair** — but **not** for the reason
   revision 1 gave. `TreemakerWrapper.cpp:429-431` states the opposite of that
   rationale verbatim: *"Node ids stay valid (AddStub never deletes a node), so
   `leaf_node_locations` keeps working."* `run_stub_repair` clears `mEdgeMap`
   only (`:507-508`). The real hazard: `AddStubToTree` → `CleanupAfterEdit`
   recomputes leafness from edge degree (`tmTree.cpp:1009`
   `theNode->mIsLeafNode = (theNode->mEdges.size() == 1);`), so a planned leaf
   can become a branch node — at which point `IsValidCondition()` returns false
   and the constraint is dropped **silently**.
2. **`tmTreeCleaner tc(mTree)` scope**, as every other condition setter does.
3. **`GetOrMakeOnePartCondition`** — idempotent by construction, so
   re-applying a rung is safe.
4. **Reject non-leaf nodes, loudly.** This is the guard that converts rule 1's
   silent no-op into an error. Without it the slice's most likely failure is
   measuring "no effect" and wrongly concluding ALM ignored the constraint.
5. **At most one node per corner, and at most 4 corners.** Under the
   coordinate route this is real arithmetic, not a guess.
6. pybind11 `.def` exports beside `apply_symmetry` (`TreemakerWrapper.cpp:1270`).

Read-back — `get_boundary_conditions() -> {node_id: {"x": float|None, "y": float|None}}`
— is a thin wrapper over Combo's existing getters, not new bookkeeping.

### 4.2 Placement policy (`mcp_harness/boundary_placement.py`, new, pure Python)

Pure function, no engine import, unit-testable off-line. **It emits
coordinates, not slot names** — the change that revision 1's API could not
support:

```python
def boundary_plan(nodes, pairs, paper_w, paper_h, *, max_corners=4)
    -> dict[int, tuple[float | None, float | None]]
```

`nodes` is the tree-JSON node list (`{id, parent_id, length, ...}`); `pairs` is
the bilateral pair list as `structural_search` already produces it. The return
maps node id → `(x, y)`, where `None` means "leave this coordinate free" — so
`(0.0, None)` is the left edge and `(0.0, 1.0)` is a corner.

Policy, in priority order:

1. **Longest flaps first.** A longer flap needs a larger circle, so boundary
   placement relieves the most pressure there. Rank leaves by edge length
   descending, **breaking ties by node id** — the project has been bitten by
   node-order dependence before (memory: `body-plan-templates-and-node-order`),
   so the tie-break is explicit and deterministic, never list order.
2. **Corners partition by mirror class.** The symmetry axis is the 45°
   diagonal through the paper centre (`TreemakerWrapper.cpp:311-313`). Under
   that mirror, `(0,0)` and `(w,h)` are **self-mirror**; `(w,0)` and `(0,h)`
   **swap**. Therefore:
   - the two off-diagonal corners are assignable to **at most one** bilateral
     pair, both members or neither;
   - the two on-diagonal corners are assignable **only to unpaired leaves**;
   - a pair may never take one corner and one edge.

   This is a *partition* rule, not a count cap. Revision 1 wrote it as
   "corner budget ≤ 4, and ≤ 2 when any pair is placed at corners", which
   forbids the legal configuration of one pair off-diagonal plus two unpaired
   leaves on-diagonal — four corners, all mirror-consistent.

   Corollary revision 1 never stated: since there are only two off-diagonal
   corners, a **second** bilateral pair cannot take corners at all and must
   fall back to mirrored edge positions.

   The rule exists because the project has already been bitten in the *length*
   domain: `tests/test_perturb_symmetry.py:1-11` records that independent
   per-pair draws shipped lopsided bases, and that `goldens/dog.fold` still
   carries a 0.026 mirror mismatch after 2 nudges. Boundary placement is the
   *position* domain, where `tmConditionNodesPaired` **does** apply — so a
   split-placed pair would fight it directly.
3. **Axial leaves go to the symmetry line, not to corners.** Where
   `leaf_labels` identifies a head/tail axial candidate
   (`mesh_to_tree.py:617-622`), prefer `SetToSymmetryLine` over a corner. This
   is §3.2(d)'s lever and it is the placement a bilateral animal's anatomy
   actually implies.
4. **No cap on edge placements** beyond what packing rejects. Only corners are
   scarce.
5. **Never constrain the root.**
6. **Emit a plan, never mutate.** The plan is data; the ladder applies it.

Deliberately a fixed heuristic, not a search. If it plateaus, the escalation is
the §4.3 variant fan, not MCTS.

### 4.3 Ladder rung (`rescue_ladder.py`, `server.py`)

New stage in the existing vocabulary (`rescue_ladder.py:53-61`):

```python
STAGE_BOUNDARY = "boundary"
```

Classification:

| Set | Member? | Why |
|---|---|---|
| `PRESERVING_STAGES` | **Yes** | Constrains position only; the caller's exact `(id, length)` multiset is preserved — the same argument that admits `STAGE_PLACEMENT` |
| `INVENTS_ANATOMY` | **No** | No flap is created |
| `STAGE_HONESTY` | **2** | Same rank as `order`/`placement` |

Ordering: **after `placement`, before `normalize`** — but the justification is
now that boundary is the **same class** of position-space lever as `order` and
`placement` (§1.1), so it belongs adjacent to them; and ahead of `jitter`,
because the point is to avoid paying proportion drift for a packing win.
Revision 1's "strictly stronger position-space lever" is withdrawn.

Variant fan: **≤ 3**, tried in order, first success wins — (a) the policy plan,
(b) corners demoted to edges (drop the second coordinate of every corner
assignment), (c) longest-flap-only.

**Attempt-0 must be byte-identical after this slice.** Boundary conditions
travel a side channel applied at the rung, never inside the node dicts that
reach attempt-0 — the same contract `Rung.stubs` already establishes
(`rescue_ladder.py:217-223`).

#### 4.3.1 Coordinated edits — this is NOT one constant

Revision 1 treated the stage as a constant plus one classification row.
It is **six sites**, and three of them carry code comments warning they move
together. `mesh_to_tree.served_stage:730-736` states it outright:

> *"A missing marker here is therefore a silent WRONG SERVE, not a red test,
> which is why this table, rescue_ladder's constants and benchmark_subjects'
> stage chain must always move together."*

| # | Site | Consequence of omitting |
|---|---|---|
| 1 | `rescue_ladder`: `STAGE_BOUNDARY`, `BOUNDARY_MARKER`, `PRESERVING_STAGES`, `STAGE_HONESTY` | — |
| 2 | `server._ALL_LADDER_STAGES` (`server.py:593`) | rung silently unreachable via the stage-selection env var |
| 3 | `mesh_to_tree._STAGE_INTEGRITY` (`:114`, "Pinned dict-equal to `STAGE_HONESTY`") | dict-equality test goes red (this one is caught) |
| 4 | `mesh_to_tree.served_stage` chain (`:724-748`) | **falls through to `STAGE_EXACT`** — a boundary serve reads as attempt-0 exact and **ends the drain early** |
| 5 | `benchmark_subjects` stage chain (`:96-130`) | **falls through to `"none"`** — scorecard reports `attempt0_pack=True`, `rescue_stage="none"` |
| 6 | `feasibility/tree_labeler.py:80-81` (era string built from `_ALL_LADDER_STAGES`; `PERTURB_ERA_REVISION = 7` at `:53`) | every captured row's era string changes; needs a bump to 8 |

Sites 4 and 5 are the dangerous pair: **ship the marker constant alone and a
boundary rescue is scored as a clean attempt-0 exact serve, with every test in
§6 still green.** This is the exact inversion `benchmark_subjects.py:105-112`
documents as "S4 blocker #1".

`BOUNDARY_MARKER = "[ide: rescued by boundary placement:"` must satisfy the
three test-pinned invariants at `rescue_ladder.py:145-152`: it contains no
other marker nor `CP_AUDIT_MARKER`/`MV_REPAIR_MARKER`; it does **not** contain
the jitter note's phrase `"did not pack exactly"` (a boundary-rescued base HAS
the requested proportions); and the jitter note itself is untouched. Like
`PLACEMENT_MARKER`, it says what **moved**, never what appeared — the
`STUB_MARKER` "backend ADDED ANATOMY" language must not be copied.

### 4.4 Measurement

`benchmark_subjects._COLS` gains two columns:

- `boundary_nodes` — `"<n_corner>c/<n_edge>e"`, or `null` when the rung did not
  serve.
- **`design_scale`** — the engine's optimized scale. **New in revision 2 and
  non-optional:** §1.1 proves boundary conditions cannot raise the global
  optimum, so scale is the quantity most likely to regress. Without this
  column the slice cannot detect its own most probable harm.

Revision 1 claimed "existing columns already carry the rest: `rescue_stage`
reports `boundary`". **That is false** — see §4.3.1 sites 4-5. `rescue_stage`
is re-derived from `frame_title`, and both derivations fall through silently.

Primary metric: **attempt-0-failing subjects rescued at `boundary`, minus any
that regress, minus any whose `design_scale` drops below a pre-registered
floor.** That floor is set in Phase A, not chosen after seeing results: run the
probe template with the rung applied and with it absent, take the observed
run-to-run scale variance of the *unconstrained* path, and set the floor at
`scale_without × (1 − 3σ)`. A drop past that is a regression, not noise.
Secondary:
whether previously-`jitter`/`composed` subjects move UP to `boundary` — a
proportion-integrity win at constant rescue count, credited the way S7's fish
row was.

*(Audit finding I did not verify: that §4.4's primary and secondary metrics
have zero candidates on the named corpus. Confirm the candidate count before
Phase C, since it would make the measurement vacuous.)*

### 4.5 Hull-vs-square probe (hypothesis, explicitly labelled)

Memory records `export-emits-hull-not-square` as "LIKELY PERMANENT":
TreeMaker creases only the leaf convex hull, and squaring is display-only
(`square_complete.py`).

**Hypothesis (untested):** if leaves are constrained to paper edges and
corners, the leaf hull extends to the paper boundary and the exported hull
approaches the square.

Test: `hull_area / paper_area` per template, with and without the rung, where
`hull_area` is the area of the convex hull of the `B`-assignment boundary
vertices in the exported `.fold`. Report the number either way. **This is a
hypothesis, not a promise** — if it fails, the slice is still justified by
§4.4 alone.

### 4.6 The post-optimization projection (NEW in revision 2)

**Applying the condition is not sufficient to hold the node there.**

`ProjectActivePaths()` (`TreemakerWrapper.cpp:1005`) runs on the **normal
compile path** at `:1155`, after ALM converges and before the molecule build.
It is a damped Gauss-Newton polish that **calls `SetLoc` and moves leaf
coordinates**, tightening active-path equalities from ALM's ~1e-6 penalty floor
to ~1e-13. Its constraint set is exactly two things: active-path rows, and
symmetry rows (`b.x − a.y = 0`, `b.y − a.x = 0` about the 45° axis).

**There is no row for a boundary condition.** A node ALM placed exactly at
`(0, h)` is free to be moved off it by the ~1e-5 the code comment advertises as
safe — and Combo's boundary equalities are *exact*, so any displacement
violates them.

Two options, to be decided in Phase A on evidence:

- **(i) Add boundary rows to the projection.** For a node with `XFixed`, add
  `x = mXFixValue`; likewise `y`. These are linear, so they drop straight into
  the existing least-squares system beside the symmetry rows.
- **(ii) Re-assert and verify after projection.** Cheaper, but leaves the
  active-path residual and the boundary equality fighting each other.

**(i) is the proposal**, on the grounds that the projection already carries
hard symmetry rows for exactly this reason — its own comment says free
projection "would drift it asymmetric".

This defect also invalidates revision 1's test design: `test_boundary_binding`
asserted that the condition exists and reads back, which is **bookkeeping, not
geometry**, and would pass green on a base whose corner flap sits off the
corner. §6 is corrected accordingly.

---

## 5. Phasing

**Phase A — probe (scratchpad, main checkout, ~half a day).** Bind the three
Combo methods, apply corner conditions by hand to a **named** currently-failing
template, and answer five questions before any policy code is written:

1. Does ALM converge with the added **linear** equalities, or diverge?
2. Does a known-failing tree pack?
3. **What is `design_scale` with and without?** (§1.1 predicts non-increasing.)
4. **Does the node survive `ProjectActivePaths`?** Read `leaf_node_locations`
   after the compile and check the constrained coordinate to 1e-9. If not, §4.6
   option (i) is in scope for Phase B.
5. Confirm that a condition on a non-leaf is dropped **silently**, so rule 4's
   loud rejection is justified by observation rather than by inference.

**Naming the sample:** the probe template must be named in the implementation
plan and must be one that currently fails at attempt-0, drawn from
`fixtures/scorecard_baseline.jsonl`. *(An audit finding I did not verify claims
revision 1's Phase A sample is empty as specified; the plan must confirm a
non-empty set before Phase A starts.)*

> **STOP IF ALM diverges** on linear equalities. That is the pre-registered
> stopping rule, and it is a much stronger signal under Combo than it would
> have been under v4's quartic.

**Phase B — policy + rung.** `boundary_placement.py`, the `STAGE_BOUNDARY`
rung, all six coordinated edits (§4.3.1), the side-channel plumbing, the
marker, and §4.6 option (i) if Phase A question 4 failed.

**Phase C — measurement + re-bless.** Scorecard columns, one coordinated
re-bless of the `benchmark_subjects` baseline and `cases.py` tripwires.

> **STOP IF** the §4.4 candidate count is zero — the measurement would be
> vacuous.

---

## 6. Testing

| Test | Asserts |
|---|---|
| `test_boundary_binding` | `set_node_at` / `set_node_on_x` / `set_node_on_y` create a `tmConditionNodeCombo`; `get_boundary_conditions` reads the coordinates back; idempotent on re-apply |
| **`test_boundary_geometry`** | **the served node's COORDINATES are within 1e-9 of the requested slot after a full compile** — the §4.6 guard. Bookkeeping assertions alone cannot catch the projection defect |
| `test_boundary_rejects` | non-leaf → loud error; two nodes to one corner → named error; 5th corner → named error; after stub repair → named error |
| `test_boundary_plan` | pure-Python policy: pairs placed together or not at all; the mirror-class partition (§4.2 rule 2) including one-pair-plus-two-unpaired = 4 corners **legal**; a second pair gets edges, not corners; root never constrained; **deterministic under input reordering** (tie-break by node id) |
| `test_boundary_symmetry` | **A/B against the same tree, not a magic number**: mirror residual of the boundary-served base ≤ that of the same tree served without the rung. (`0.026` is `dog.fold`'s *measured* mismatch, not a tolerance.) |
| `test_attempt0_unchanged` | **byte-identical** attempt-0 output for all four templates |
| `test_ladder_stage_sets` | `STAGE_BOUNDARY ∈ PRESERVING_STAGES`, `∉ INVENTS_ANATOMY`, honesty rank 2, `_STAGE_INTEGRITY` dict-equal |
| **`test_stage_chains_agree`** | **both** marker→stage derivations (`mesh_to_tree.served_stage`, `benchmark_subjects`) return `boundary` for a `BOUNDARY_MARKER` fold — the §4.3.1 sites-4-and-5 guard |
| **`test_worker_paths_apply_plan`** | each of `_worker_full_base`, `_worker_compile_recipe`, `_worker_compile_and_regions._try_once` actually **calls** the engine binding when the rung carries a plan — a call-count assertion against a stub engine, not merely "the argument arrived". Without this, a path that accepts the argument and forgets the call serves an **unconstrained** base under `BOUNDARY_MARKER` and scores as a rescue |
| `test_scorecard_columns` | `boundary_nodes` and `design_scale` present; `null` when the rung did not serve |
| Regression | full suite from the MAIN checkout; expect 4/2124/11 ± the re-blessed rows |

Per memory `ubuntu-platform-truth` and `perfect-base-s7-outcome`: run with
`--timeout=420`; bare `make test` never terminates on macOS. Check host CPU for
orphaned processes before timing anything.

---

## 7. Risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | **ALM diverges** with the added equalities | Much reduced by the Combo redirection: `OneVarFn` is *linear* where `StickToEdgeFn` was quartic with a gradient vanishing at the corners. Phase A remains a pre-registered stopping rule |
| R2 | **Over-constraining makes more trees fail** than it rescues | Boundary is a RUNG, never a default. Attempt-0 byte-identical by test. Net rescue is the primary metric and may be negative → the rung ships disabled or not at all |
| R3 | **Corner placement breaks bilateral symmetry** | §4.2 rule 2 is a mirror-class partition; `test_boundary_symmetry` pins it |
| R4 | **Scorecard churn** | One coordinated re-bless in Phase C, per the S5b/S7 precedent. Never loosen a pin to make it pass |
| R5 | **Worktree cannot build** — borrowed `.so` inflates failures 27 vs ~3 | All builds, compiles and blesses from the MAIN checkout |
| R6 | Hull-vs-square hypothesis fails | Labelled a hypothesis in §4.5; slice justified by §4.4 alone |
| **R7** | ~~`tmConditionNodeOnCorner` friend-list asymmetry~~ | **Dissolved by the redirection** — Combo's constructor is public. (The premise was also shaky: `friend class tmNode;` *is* present in `tmConditionNodeOnEdge.h:71`.) |
| **R8** | **`ProjectActivePaths` moves the node off the boundary** | §4.6. Phase A question 4 measures it; option (i) adds linear boundary rows beside the existing symmetry rows |
| **R9** | **A condition on a non-leaf is a SILENT no-op** (`IsValidCondition` false → `GetBaseOffset` returns `BAD_OFFSET` → nothing added) | §4.1 rule 4 rejects loudly at bind time; Phase A question 5 confirms the silence exists. This is the single most likely way the slice measures "no effect" and mis-attributes it to ALM |
| **R10** | **A coordinated-edit site is missed** and a boundary rescue scores as attempt-0 exact with all tests green | §4.3.1 enumerates all six; `test_stage_chains_agree` and `test_worker_paths_apply_plan` are the two new guards |
| **R11** | **`design_scale` regresses** — the outcome §1.1 predicts | It is now a measured column, and part of the primary metric. A rescue bought with a lower scale than the pre-registered floor is not a win |
| **R12** | **Boundary placement may be the wrong lever for this failure class.** Lang's own remedy for many-sided polygons is a node in the polygon's *centre* — a middle flap (§1.2) | Phase A adds a cheap control arm: on the same failing template, try a centre-seeded node alongside the boundary plan and report both. If the centre arm rescues and the boundary arm does not, this slice is the wrong slice and the finding is worth more than the code |

---

## 8. Out of scope

- The visual-feedback loop (separate spec).
- Fixing the `CLAUDE.md` §4A `set_symmetry` naming drift (docs chore; note it
  may already be resolved by an uncommitted edit — §1).
- Any change to `_audit_score`, `lint_verdict`, or the acceptance ratchet.
- Reworking `square_complete.py`, regardless of the §4.5 outcome.
- MCTS or any search over placement beyond the ≤3 variant fan.
- The v4 `tmConditionNodeOnEdge`/`OnCorner` path (§3.2).
- `tmConditionNodeCombo`'s `Fixed`-to-arbitrary-point capability beyond the
  boundary; the same binding exposes it, but no measured failure asks for it.
- **Book-vs-diagonal symmetry axis selection** (§9 question 5). It is a
  genuinely promising lever surfaced by the same manual read, and it is a
  different slice: it touches `apply_symmetry`, not the boundary conditions,
  and it would change attempt-0 output — which this slice is committed to
  leaving byte-identical.

---

## 9. Open questions

1. **Should `boundary` sit before or after `normalize`?** Proposed: before.
   Reviewable once Phase A shows the rescue rate.
2. **Should the agent be able to request boundary placement directly** via an
   MCP tool, or is it ladder-only? Proposed: **ladder-only** initially — the
   parent plan rejected "interactive agent topology MCP tools" because no
   measured failure needed an LLM topology decision.
3. **Does the corner cap interact with `MAX_LEAVES`?** For a 9–12-leaf
   structure-gated admission, 4 corners + N edges may still not pack. Measure;
   do not pre-optimize.
4. **Should axial leaves prefer the symmetry line over a corner unconditionally**
   (§4.2 rule 3), or should that be a fourth variant in the fan? Proposed:
   unconditional, since it is what the anatomy implies — but it is the least
   evidenced rule in the policy.
5. **Is our hard-coded 45° symmetry axis costing us scale on every paired
   tree?** `apply_symmetry` always sets diagonal symmetry
   (`TreemakerWrapper.cpp:311-313`). Lang's manual §2.2 works an example where
   switching to diagonal symmetry *drops* the scale to 0.2626 and calls it less
   efficient than book symmetry, noting that either can win and TreeMaker lets
   you check both — we never check. **Out of scope for this slice** (§8), but it
   is a one-parameter experiment with a plausible whole-corpus effect and it
   should not be lost.

---

## 10. Revision history

**Revision 2 (2026-08-02)** — after a five-lens audit with adversarial
verification. Every finding below was reproduced against the source before
being written in.

| # | Change | Section |
|---|---|---|
| 1 | **Bind Combo, not the v4 classes.** The v4 conditions cannot name which edge or corner, emit a quartic where Combo emits a linear equality, and have private constructors. Lang's own v5 API drives Combo | §3.1, §3.2, §4.1 |
| 2 | **The mechanism story was backwards.** Boundary conditions cannot raise the design scale; the lever is basin selection, the same class as order/placement | §1.1, §4.3, §4.4 |
| 3 | **`ProjectActivePaths` can undo the placement**, and revision 1's test would not catch it | §4.6, §6, R8 |
| 4 | **Adding a stage is six coordinated edits**, two of which fail silently | §4.3.1, §6, R10 |
| 5 | Corner policy rewritten as a mirror-class partition; the "≤2 corners" cap forbade a legal configuration. `boundary_plan` now emits coordinates | §4.2 |
| 6 | Rule 1's rationale replaced (the cited file says the opposite); rule 5 now true; R7 dissolved; R9 added for the silent no-op | §4.1, §7 |
| 7 | Symmetry-line placement for axial leaves added — a lever revision 1 did not consider | §3.2(d), §4.2 rule 3 |
| 8 | Citation offsets corrected; prior-art misattributions corrected (order-vs-placement, RTLFixer vs ICLR'24, IJCAI'23) | §2, §3.3 |

**Revision 2a (same day)** — the TreeMaker 4.0 manual was located on Lang's
site and read directly. It **confirms** §1.1's figures (0.323 / 0.353 / 0.268 /
0.250) and the five-flap rule, supplies the three real reasons to force edge
flaps, independently confirms the coordinate route (§4.5.29-4.5.32 of the
manual is Combo's flag set), and adds the §1.2 counter-indication that produced
R12. Two further findings from the same read are recorded as §9 question 5 and
§8's last bullet.

**Claims still NOT personally verified** — flagged inline so they are easy to
close out: that Phase A's revision-1 sample was empty; that §4.4's metrics have
zero candidates on the named corpus. Both are Phase-A/Phase-C gating questions
and neither changes the design.
