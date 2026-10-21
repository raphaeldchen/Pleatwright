# Pleat reassignment: global flat-foldability for the box-pleat compiler

**Date:** 2026-09-22
**Status:** design approved, not yet planned
**Supersedes nothing.** Extends `docs/superpowers/specs/2026-09-20-box-pleat-compiler-design.md`
(the v1 compiler) with the stage its §6 explicitly deferred.

## 1. Why

The v1 compiler emits 10 of 17 subjects with `cp_audit` clean, `flat_fold`
closure at machine epsilon and Oriedita lint PASS. Those are all **local**
flat-foldability conditions. Measured 2026-09-22 on the committed trees, the
**global** condition fails on 8 of the 10:

| subject | `layer_order` verdict | witness |
|---|---|---|
| bird | consistent | — |
| starfish | consistent | — |
| dog | contradiction | taco-tortilla crease (138, 142) through face 142 |
| horse | contradiction | taco-tortilla crease (64, 65) through face 49 |
| rabbit | contradiction | taco-tortilla crease (78, 82) through face 82 |
| guinea_pig | contradiction | taco-tortilla crease (1, 11) through face 24 |
| lizard | contradiction | taco-tortilla crease (5, 9) through face 12 |
| frog | contradiction | taco-tortilla crease (1, 11) through face 24 |
| octopus | contradiction | taco-tortilla crease (17, 18) through face 13 |
| spider | contradiction | taco-tortilla crease (69, 70) through face 7 |

Every one is **taco-tortilla**: a folded crease pair passing through a face
that the forced relations place between its two halves — paper through paper.
No taco-taco and no tortilla-tortilla witnesses occur. A base that reads
`contradiction` has not been shown to be foldable at all; spec §6 of v1
sanctioned reporting this and moving on, and this spec closes it.

## 2. Scope

**In:** choosing M/V labels over a **fixed crease set** so the crease pattern
satisfies the global conditions `layer_order` already implements.

**Out (and why):**
- Changing *which* segments are creased (F to fold). That shortens flaps and
  changes the base; it is Lang §14.1 level-shifter work, i.e. subproject B.
- Re-seeding contours or re-packing at a larger N. Ruled out by the owner on
  2026-09-22: the packing, the elevation field and the folded base stay
  byte-identical, and an unfixable subject **refuses** — "it's a finding, not
  a regression".
- A SAT or MILP encoding. Consciously rejected: new dependency, and it
  displaces the exact CSP this project already tests.

## 3. The enabling theorem

> Relabelling M to V, or V to M, on a fixed crease set leaves the folded base
> byte-identical and changes only the layer order.

Two facts, both verifiable in the existing code:

1. `flat_fold` composes reflections. `_reflect(a, b)` (`flat_fold.py:116`) is
   applied to every folded edge irrespective of its label; `M` and `V` produce
   the same reflection. The folded image is therefore a function of the crease
   **set** alone.
2. M/V enters `layer_order` at exactly one line — `val = (a == "V") ==
   (orient[fa] == 1)` (`layer_order.py:575`), which builds the `direct` facts.
   The overlapping face pairs, the taco-tortilla equalities, the taco-taco
   constraints and the covers are all derived from folded geometry.

Consequences the design rests on: the owner's no-change ruling is satisfied by
construction rather than by checking; and the expensive part — the constraint
graph — is built **once per crease set** and reused for every candidate
labelling. §7.1 makes the theorem a test rather than an assumption.

## 4. Architecture

Four files. One is new.

### 4.1 New: `mcp_harness/box_pleat/layers.py`

Owns the bridge between an assignment and the global conditions. Imports
`flat_fold` and `layer_order`; imported by `compile.py` only, never by
`assign.py`.

```python
@dataclass(frozen=True)
class Witness:
    kind: str          # "taco_tortilla" | "taco_taco" | "tortilla_tortilla" | "direct"
    creases: frozenset # FOLD edge keys (v_lo, v_hi) whose LABELS produced the conflict
    faces: tuple       # face indices named by the provenance, diagnostic only
    prov: str          # layer_order's provenance text, unchanged

@dataclass(frozen=True)
class LayerGraph:
    pairs: frozenset       # canonical overlapping face pairs
    equalities: tuple      # taco-tortilla / tortilla-tortilla
    tacos: tuple           # taco-taco
    covers: tuple
    slots: tuple           # (edge_key, lit, orient_sign) per creased shared edge

def constraint_graph(ff) -> LayerGraph
def propagate(graph: LayerGraph, labels: dict) -> Witness | None
```

`labels` maps a FOLD edge key to `"M"` or `"V"`. `propagate` runs
`layer_order`'s fixpoint with `direct` facts computed from `slots` and
`labels`, and returns `None` when the forced relations are consistent.

**Conflict analysis.** `propagate` records, for every literal it sets, the
provenance that set it. On contradiction it walks both contradicting literals
back through their antecedents to the `direct` facts at the leaves. Those
facts are labels, so the set of edge keys reached **is** the no-good clause:
"these creases may not all keep their current labels". A witness that reaches
no direct fact is impossible — every literal is ultimately seeded by a direct
fact — and `propagate` raises `AssertionError` if it ever happens, because
that would mean the graph, not the labelling, is inconsistent.

### 4.2 Changed: `mcp_harness/layer_order.py`

Small and backwards-compatible. Provenance stops being an f-string and becomes

```python
@dataclass(frozen=True)
class Prov:
    text: str
    creases: tuple = ()
    faces: tuple = ()
    def __str__(self) -> str: return self.text
```

Every existing message stays byte-identical: the contradiction sites
interpolate the provenance (`f"layer-order contradiction via {prov}"`), which
now calls `__str__`. One site composes rather than consumes — `layer_order.py:566`
builds `f"{prov} through face {x}"` — and becomes `Prov(text=f"{prov} through
face {x}", creases=prov.creases, faces=prov.faces + (x,))`, keeping the same
text while carrying the tortilla face into the witness. One public function is
added so `layers.py` does not reach into underscored internals:

```python
def constraints_for(result: FlatFoldResult) -> _Constraints
```

Nothing else in the module changes; `layer_order(result)` keeps its present
signature, behaviour and exceptions, and every existing caller
(`probe_box_pleat.py`, the serve path) is untouched.

### 4.3 Changed: `mcp_harness/box_pleat/assign.py`

Two changes.

**Pleat-path variables.** Today the off-column contour pieces take their label
from `label_from_profile` and are not variables. They become variables grouped
into **pleat paths**: a maximal set of creased contour pieces that are
connected through degree-2 vertices and share an elevation, one `{M, V}`
variable per path (COrigami §F.2 assigns one orientation per connected path
for the same reason — it is what keeps the variable count in the hundreds
rather than the thousands: 307 merged creases on horse, 569 on dog, roughly
halved again by mirror pairing). The profile rule survives as each path's
**initial value**, so the solver's first candidate is v1's answer and a
subject that is already consistent is unaffected.

**Global hook.**

```python
def assign(layout, ridges, boundary_ridges, contours, *,
           budget=500_000, global_check=None) -> Assignment | AssignFail
```

`global_check: Callable[[Assignment], Witness | None]`, supplied by
`compile.py`. When a candidate satisfies every local condition, `assign` calls
it; `None` accepts, a `Witness` is stored as a no-good clause over the
variables its `creases` map to, and the search continues. `assign` keeps no
knowledge of what the check means, and `flat_fold`/`layer_order` stay out of a
geometry module.

**Witness-guided ordering.** The variables named by the most recent witness are
tried first on the next descent. This is the one idea borrowed from the
rejected greedy approach: it is a heuristic on search order only and cannot
change which labellings are reachable.

### 4.4 Changed: `mcp_harness/box_pleat/emit.py` and `compile.py`

`to_fold` gains an optional provenance return so a witness can be mapped back
to CSP variables across the collinear-run merge:

```python
def to_fold(layout, assignment, *, with_index=False) -> dict | tuple[dict, dict]
```

`with_index=True` returns `(fold, edge_index)` where `edge_index` maps a FOLD
edge index to the tuple of source piece keys merged into it. Default
behaviour, and the emitted FOLD bytes, are unchanged.

**Superseded (§11 item 11): not built this way.** The shipped
`box_pleat/emit.py::to_fold` signature is `to_fold(layout, assignment)` --
no `with_index` parameter exists anywhere under `box_pleat/`. See §11 item
11 for what was built instead and why this paragraph was left specifying an
unbuilt API.

`compile.py` gains the stage:

```python
STAGES = ("tree", "pack", "skeleton", "contours", "assign", "layers", "emit")

@dataclass
class LayerFail:
    kind: str              # "no_labelling" | "budget"
    witness: Witness | None
    tried: int

def compile_tree(nodes, pairs, *, max_N=None, pack_budget=200_000,
                 assign_budget=500_000, layer_budget=200) -> Result
```

and builds the closure it injects:

```
assignment -> to_fold(with_index=True) -> flat_fold -> constraint_graph (cached
by crease set) -> propagate -> Witness | None
```

**Superseded (§11 item 11):** this diagram's `to_fold(with_index=True)` step
was never built; see §11 item 11 for the shipped data flow.

The graph cache is keyed by the frozenset of folded piece keys, because
`assign`'s centre-column F decisions can change the crease set; every other
candidate reuses the cached graph.

**Superseded (final review, 2026-09-23): not built this way.** The shipped
cache is keyed by nothing (one graph per `compile_tree` call), on the
premise that the crease set is fixed across candidates — which is true only
of the M/V-labelled creases, not of the F set the sentence above itself
names as variable. That gap went unguarded until this review; the shipped
fix is an `assert`-based topology-drift guard in `compile.py`'s `_check`,
not a cache key. See "Final review 2026-09-23" at the end of `§11` for the
full accounting.

`layer_budget` counts global checks (one
`to_fold` + `flat_fold` + `propagate` each); exhausting it is
`LayerFail("budget", last_witness, tried)`. Exhausting the search space is
`LayerFail("no_labelling", last_witness, tried)`. `compile_tree` still never
raises for a well-formed tree.

## 5. Data flow

```
tree -> pack -> skeleton -> contours -> assign <-------+
                                          |            | no-good clause
                                          v            |
                                    to_fold(index)     |
                                          v            |
                                     flat_fold         |
                                          v            |
                              constraint_graph (cached)|
                                          v            |
                                      propagate -------+ Witness
                                          |
                                          | None
                                          v
                                        emit
```

## 6. Pre-registered bar

Two-sided, in the project's usual form: a subject that starts passing forces
the table to be updated.

**Invariant established by this work.** No subject reaches `emit` with a
layer-order contradiction. A subject whose crease set admits no consistent
labelling stops at stage `layers` with a typed `LayerFail`. That may reduce
the count of emitting subjects below 10; per the owner's 2026-09-22 ruling
that outcome is a finding — it localises the defect in the *packing* rather
than the labelling, and hands subproject B a measured site.

**Must not move.** `bird` and `starfish` are already consistent; their emitted
FOLD must be **byte-identical** to the 2026-09-20 artifacts. For every subject
that still emits: `N`, `scale_bp`, `hull_coverage` and the folded base are
unchanged from `docs/superpowers/evidence/2026-09-20-box-pleat/results.json`,
`cp_audit` reports clean, `flat_fold` closure stays at or below 2.6e-15, and
Oriedita lint reads PASS.

**Recorded per subject.** Each of dog, horse, rabbit, guinea_pig, lizard,
frog, octopus, spider is pinned in a strict expectation table as either
`consistent` or `LayerFail(kind)`, filled in by measurement and updated when a
subject moves.

**Evidence.** `probe_box_pleat.py` gains a `layer_order` column that reads
`consistent` for every emitting subject by construction, plus a
`layers_tried` count and the refusals. The 17-way table and README are
regenerated.

## 7. Testing

### 7.1 The theorem (first test written)
Take the committed `lizard` fold; generate 50 random relabellings of its
creased edges; assert `flat_fold(...).folded_vertices` equals the baseline
exactly, array for array, and that `closure.max_error` is unchanged. Labels
need not be locally valid — the theorem is about reflections, not validity.

### 7.2 Graph invariance
`constraint_graph` over two different labellings of one crease set returns
equal `pairs`, `equalities`, `tacos` and `covers`.

### 7.3 Conflict analysis
A hand-built five-face strip with one taco-tortilla, derived on paper in the
test's docstring: `propagate` returns a `Witness` whose `creases` equals the
hand-derived set exactly — not a superset.

**Superseded (§11 item 12):** this hand-built five-face fixture was replaced
during execution; see §11 item 12 for what was built and measured instead.

### 7.4 The loop finds it
A fixture whose profile-rule labelling is inconsistent and whose single pleat
path flip is consistent: `compile_tree` reaches `emit` and `layer_order` reads
consistent.

### 7.5 The loop refuses
A fixture with no consistent labelling: `compile_tree` returns
`LayerFail("no_labelling", witness, tried)` with a witness attached,
terminating well inside the budget. No hang, no raise.

### 7.6 Regression
`bird` and `starfish` emit byte-identical FOLD; existing box-pleat tests pass
unchanged.

### 7.7 End to end
`tests/test_box_pleat_e2e.py` gains the strict expectation table of §6, with
the slow tier marked `@pytest.mark.slow` — dog (569 creases) and spider are
expected to dominate runtime.

## 8. Prior art (CLAUDE.md §0)

| Source | Taken / rejected |
|---|---|
| COrigami §3.3, §F.2–F.3 (arXiv 2606.26299) | **Adapted.** Their deferred pleat reassignment — a trapped pleat returns to the unassigned pool to be flipped downstream — becomes no-good-driven revisiting. One orientation per connected pleat path is taken directly (§F.2). Their greedy vertex scoring and priority queue are rejected: our CSP is exact and has never failed locally (10/10), so a heuristic would only lose completeness. |
| Justin's / Hull's global conditions | **Reused unchanged.** Already implemented in `layer_order.py` as taco-taco, taco-tortilla and tortilla-tortilla; this work supplies labels to them rather than re-deriving them. |
| MILP / SAT M/V assignment (landscape survey) | **Rejected.** Complete and fast, but adds a solver dependency and moves flat-foldability reasoning out of the exact CSP this project tests. Revisit only if §7.5-class refusals turn out to be search failures rather than genuine emptiness. |
| Lang, *Origami Design Secrets* §13.5 | **Kept as heuristic.** The elevation-profile rule (minimum M, maximum V, slope F) stays as each pleat path's initial value — it is the canonical white-side-up labelling and the first candidate the solver tries. |

## 9. Risks

1. **Search blow-up** on dog and spider. Mitigated by witness-guided ordering,
   the graph cache and `layer_budget`; a budget exhaustion is typed, reported
   and distinguishable from emptiness.
2. **The space may be empty** for some subjects. That is the finding §6
   anticipates, not a failure of the design; it points at the packing and
   hands subproject B a measured site.
3. **Cost per check.** One `to_fold` plus one `flat_fold` per candidate.
   `flat_fold` on 300 faces is milliseconds, but 200 checks on spider's 146
   faces is the slow-tier cost to watch.

## 10. Amendment 2026-09-22 (Task 2): `_propagate` is NOT confluent

This spec and the plan both justified making the transitivity closure
incremental with "propagation is confluent, so the verdict cannot change."
**That premise is false as the rule is implemented, and Task 2 measured it.**

Both the old triple loop and the new worklist write a pair only when it is
currently unknown (`get(_lit(x, z)) is None`). When two independently
admissible derivation chains imply *opposite* values for the same pair,
whichever chain the traversal reaches first fills the slot and the second is
never used to cross-check it. The fixpoint is therefore an artifact of
iteration order.

**Measured.** On `mesh-humanoid` flip-set `(8, 9, 21)`, permuting nothing but
the old rule's own iteration order flips its verdict: reversing the face order
within each cover (`sorted(cov, reverse=True)`) turns the pinned "consistent,
133 forced facts" into a contradiction. All six flip-sets on which the new
closure disagrees with the old are order-flippable this way, while four
flip-sets both agree are consistent stay consistent under all ten permutations
tried — the shuffle discriminates rather than breaking everything. One
permutation reproduces the new closure's own witness verbatim.

**Consequence for this design, and it is a weakening of what we may claim.**
`layer_order` under-refutes: a reported contradiction is entailed by the
bedrock facts (every derivation step is sound), but "no contradiction found"
is **not** a proof of flat-foldability — it means this traversal found none.
The module's existing docstrings already say this about `AREA_EPS`-dropped
cells; non-confluence is a second, independent reason. So the `layers` stage
certifies "no contradiction found", never "provably globally flat-foldable",
and §6's refusal remains a finding about a subject rather than a theorem.

**Why the change is still right, and is not a regression.** On the one test
that moved
(`test_conjunct_2_is_load_bearing_on_the_live_space[mesh-humanoid__seeded_1]`)
the layer gate accepts 24 flip-sets before and 18 after — but `unfoldable` is
a *subset* of `consistent`, and the difference, the flip-sets that actually
fold, is **8 either way** (24−16 and 18−10). All six newly rejected flip-sets
were already condemned by `cp_audit`, an independent oracle. The tightened
gate agrees with cp_audit where the old one did not, and the foldable set is
unchanged. The test's pinned counts are updated to 18/10 with that reason
recorded beside them.

**Rejected alternative:** making the rule confluent by cross-checking a known
slot against every later derivation (i.e. refuting instead of skipping on
disagreement). That is the *correct* fix and would make the verdict
order-independent, but it changes `layer_order`'s verdict on inputs far
outside this subproject — including the shipped serve path's `mv_symmetrize`
search — and belongs in its own spec with its own scorecard measurement, not
inside a performance task. Recorded as follow-up work.

### §10 correction, 2026-09-23: two witnesses DID move on our own corpus

Task 2's commit message (`b00a1fc`) claims "all 10 emitting box-pleat subjects
keep their verdict AND their witness string." **The second half is wrong.** All
ten verdicts hold — eight contradict, `bird` and `starfish` are consistent — but
two witnesses moved:

| subject | pre-Task-2 (`003316b`) | post-Task-2 |
|---|---|---|
| lizard | `taco-tortilla crease (5, 9) through face 12` | `taco-tortilla crease (3, 6) through face 7` |
| octopus | `taco-tortilla crease (17, 18) through face 13` | `taco-tortilla crease (4, 10) through face 11` |

The other eight are byte-identical. Task 2's implementer reported this
correctly; the controller read the first two rows of their before/after table,
generalised from them, and wrote the stronger claim into the commit message.
Recorded here because that message is permanent and a later reader would
otherwise rely on it.

**This supports the §10 ruling rather than undermining it.** "Which of several
contradictions is reported can differ" is exactly what §10 predicts, and these
two rows are a **second, independent corpus instance** of the order-dependence —
on the subjects this subproject actually targets, not only on `mesh-humanoid`.
Anything keyed to a witness *string* on this corpus is therefore keyed to
traversal order; that is why Task 2's review replaced a witness-regex test with
a structural provenance pin, and any future expectation table should record
verdicts rather than witnesses.

## 11. Execution amendments (Task 8)

Task 8's brief predicted four amendments to record here. Execution produced
**ten**; this section records all ten, in the project's usual form (what
changed, and why the measurement forced it). `§10` above is already taken
by the non-confluence ruling, so this is a new heading rather than the
brief's own `§10`.

### Rulings that changed what the code does or claims

1. **`layer_order._propagate` is NOT confluent** (`da927ca`) — recorded in
   full as `§10` above; listed here only as an index entry. The premise
   Task 2 was planned on (that propagation is confluent, so the verdict
   cannot change) is false; the task stands with a weaker, corrected claim
   ("no contradiction found", never "provably flat-foldable"), established
   by permuting the old loop's own iteration order.

2. **Two witnesses moved, and a commit message overclaims** (`74e0141`,
   the `§10` correction above) — Task 2's own commit message claimed all 10
   emitting box-pleat subjects kept both verdict *and* witness string. All
   10 verdicts held, but `lizard` and `octopus` witnesses changed, moved by
   Task 2's own closure change. A second, independent corpus instance of the
   same order-dependence `§10` predicts. **Consequence for Task 8 and every
   table downstream of it: pin verdicts, never witness strings.**

3. **Tasks 4 and 7 re-scoped onto `mv_symmetrize._LayerGate`** (`87e5c6e`,
   verified `a96282f`) — CLAUDE.md §0 requires a prior-art survey before
   planning. The survey behind this spec looked outward (COrigami,
   Justin/Hull, MILP — see §8) and missed that this repository already
   ships the mechanism Tasks 4 and 7 specify, on the TreeMaker serve path.
   `_LayerGate`'s docstring states this design's own enabling theorem (§3)
   more completely than this spec originally did, and its
   `__init__`/`consistent(flips)` split — build the geometry-derived
   constraints once, re-seed and re-propagate only the `direct` tuple per
   candidate — is exactly the cache Task 7 needed, already written and
   already carrying a drift guard this design lacked. Includes two
   follow-on corrections found while adapting it: the `_polys_of`
   soft-fail-vs-raise dedupe trap (`959f570`), and a correction to the
   drift-guard instruction itself (`7128a1a`), which as first written would
   have asserted something vacuously true.

4. **`piece_keys` lost its `N` parameter** (`045ec35`) — a caller-supplied
   `N` silently returned wrong-but-plausible piece keys rather than raising.
   Four call sites already written into this plan, verbatim, still passed
   the stale 3-arg form; all four were corrected once the defect was found,
   and the missing-key case now raises with a named error instead of
   returning a plausible wrong answer.

5. **`constraints_for` gained the `closure.bad_edges` guard** (`c7befc1`) —
   `layer_order()` and `_LayerGate` both already refuse a closure-inconsistent
   folded state via this guard; the new public entry point Task 4 calls
   (`constraints_for`) did not carry it, for no principled reason, and needed
   it for the identical reason.

6. **Task 5's two-phase `pick()`** — unrequested by the plan as written, and
   kept after a review proved it necessary (`starfish` diverges without it)
   and non-blocking on every other subject.

7. **Three bugs in this plan's own verbatim pseudocode, and one regression
   they caused downstream** — found in Task 5, and in Task 6's
   `materialise()`, which dropped Task 5's `unbound_variable` guard on top
   of the original three. One of the three would have violated this design's
   own "F stays F" invariant (Global Constraints, above): the toy fixture's
   F-routing bug emitted 0 F pieces instead of 60 before it was caught.

### Measurements recorded here, not only in the plan

8. **The no-good clause covers 125 of 249 variables** (`1d30200`) — and a
   *bigger* clause is a *weaker* one: it prunes less of the search tree per
   rejection, so convergence on this corpus is closer to plain DFS
   backtracking than to no-good-driven learning. Tightening the dependency
   set (item 10, below) is the lever that would change this, deferred on
   purpose.

9. **`layer_budget=200` is a give-up threshold, not a search-capacity
   knob** (`bd45d1b`, corrected `4c29a5a`) — every subject in this corpus
   that resolves does so in **1, 1, 2, 5, 9, 10, 20 or 22** candidates, an
   order of magnitude below the default of 200. The first cost model
   (`bd45d1b`) extrapolated from `lizard` and `horse`'s ~1.25–1.5× cost per
   extra candidate (versus the first descent) and predicted a ~30-hour worst
   case on `spider` at `layer_budget=200`. The correction (`4c29a5a`)
   measured `dog` directly at **0.38×**, not 1.25–1.5×, because `retry()`
   pops back only as far as a clause variable — a re-descent explores a
   shrinking *suffix* of the tree as the subject grows, not the whole tree
   — so the ratio the first two (small) data points suggested runs backwards
   on a large one. **Do not extrapolate this cost from small subjects.**
   Task 8 is bound by this: it must cap its own run and report `budget`
   refusals with their measured cost, never raise the budget to make a
   table read better (this project's own named recurring failure mode).

10. **Tightening the dependency set is the primary performance lever, and
    is deliberately left undone** — it both prunes more of the search *and*
    costs less to test than the alternatives, which is two independent
    reasons to want it. Deferred anyway: the tightening direction is the
    **unsound** one (an over-tight clause can discard a labelling that would
    actually have worked), so shipping it without its own correctness
    argument is a risk this task's schedule does not carry.

11. **`to_fold` did not gain a `with_index` parameter.** §4.4's planned
    signature, `to_fold(layout, assignment, *, with_index=False)`, and §5's
    data flow, `to_fold(with_index=True) -> (fold, edge_index)`, were never
    built. The shipped `box_pleat/emit.py::to_fold(layout, assignment)` is
    unchanged from v1, and `with_index`/`edge_index` occur nowhere under
    `box_pleat/`. The problem `edge_index` was meant to solve — mapping a
    witness's creases back to CSP variables across the collinear-run merge
    — is instead solved without touching `to_fold` at all:
    `layer_order.constraints_for` (via `mcp_harness/box_pleat/layers.py`)
    builds its `DirectSlot`s keyed directly on FOLD edge keys `(v_lo, v_hi)`,
    and `Witness.creases` is a `frozenset` of those same keys, so a witness
    names creases in the crease set's own vocabulary and never needs a
    separate index back into merged pieces. §4.4's `to_fold` signature and
    §5's data flow diagram are both marked superseded in place, pointing
    here.

12. **§7.3's hand-built five-face fixture was replaced.** The planned toy
    strip, "derived on paper in the test's docstring," was swapped for a
    committed real golden: `tests/data/lizard-v1.fold`, v1's actual
    pre-pleat-reassignment `lizard` output, which reads `contradiction` with
    a measured 12-crease `taco_tortilla` witness
    (`test_box_pleat_layers.py::test_contradiction_returns_a_witness_naming_creases`,
    pinned as `LIZARD_V1_WITNESS_CREASES`, an exact set rather than
    "non-empty" or "a subset"). A committed file drawn from the compiler's
    own output is harder to get wrong than a hand-derived toy and, being
    real geometry, exercises `constraint_graph`/`propagate` on the same
    inputs the corpus measurement uses. §7.3 is marked superseded in place,
    pointing here.

### Measured 2026-09-23: `rabbit` is unresolved, and `assign_budget` binds first

`rabbit` is the one subject in this corpus that neither repairs nor exhausts
the search space it claims to. Two runs, both `2026-09-23` (`1be01b0`):

| `layer_budget` | stage | `layers_tried` | secs | failure |
|---:|---|---:|---:|---|
| 25 | `layers` | 25 | 447 | `LayerFail(budget)` |
| 100 | `assign` | **56** | 1765 | **`AssignFail(budget)`** |

At `layer_budget=100` the search never reaches 100 layers-stage candidates:
it exhausts `assign_budget=500_000` **local-CSP search nodes** first, at 56
of them. The Task 7 review's claim that `assign_budget=500_000` "does not
bind this" was measured on `lizard`, which exhausts its whole reachable
space in 11 candidates — that does not generalise, and is **false for
`rabbit`**: the node budget binds before the layer budget gets a chance to.
Since 56 « 100 « 200, the same node-budget wall binds at `compile_tree`'s
actual shipped default (`layer_budget=200`) too — `rabbit` under default
settings reaches stage `assign`, not `layers`, with `AssignFail("budget",
500000)`, `layers_tried=56`. (Not independently re-measured at 200 — the
100-run already shows the layer budget is not the binding constraint, and a
third ~29-minute run to confirm an arithmetic consequence was judged not
worth its cost; see risk discipline in item 9 above.)

**This is a fourth outcome the plan never enumerated**, and it is the reason
`Result.layers_tried` is load-bearing rather than merely informative: without
it, `rabbit`'s row reads as an ordinary local-CSP node exhaustion; with
`layers_tried=56` a reader can see the CEGAR re-descents are what consumed
the nodes.

**What `rabbit` does and does not establish.** It establishes that no
consistent labelling is reachable within 500,000 search nodes and 56
candidates, in ~29 minutes. It does **not** establish that none exists: only
a `layer_unsat` — the search space genuinely exhausted — would do that, and
`rabbit` never gets there. (`lizard` reaches `layer_unsat` at 11 candidates
only under a probe that forces every candidate to be rejected regardless of
its own verdict, to characterize the per-rejection cost; `lizard`'s actual
recorded outcome, uncoerced, is `consistent (repaired)` at 9 candidates —
see the table above and the evidence README.) So
`rabbit` is reported as a **budget** refusal with its measured cost, never as
a subject whose crease set admits no consistent labelling. That distinction
is the whole reason the kind taxonomy separates `budget` from
`no_labelling`: a genuine emptiness would localise the defect in the
**packing** and hand subproject B a measured site, while a budget refusal
points at this search's own weakness — whose measured cause is already
recorded above (item 8: a no-good clause covering half the CSP prunes almost
nothing).

### Measured 2026-09-23: `spider` did not resolve in 60 minutes at `layer_budget=25`, and the run was stopped

This is **a bounded negative, reported as a measurement in its own right —
not an absence of one, and not itself an outcome.** The controller ran
`spider` (this corpus's largest subject, 146 faces, spec §9's own named
risk) at `layer_budget=25` and stopped it after 60 minutes of wall clock
with no verdict: no `emit`, no `LayerFail`, no `AssignFail`. Every other
subject in the corpus finished in at most **9.4 minutes** (`dog`, 565.5 s,
contended host); the next most expensive was `guinea_pig`, 272.9 s
(4.55 min). Because the run was stopped rather than left to terminate, its
`layers_tried` count at the stop point is unknown, and **no try count should
be extrapolated from it** — unlike `rabbit`, this is not even a budget
exhaustion with a measured `tried`, it is a run that was cut off before
producing one.

**This is the strongest single illustration of this design's plan risk #1**
(§9, "search blow-up on dog and spider") measured anywhere in this corpus:
at the same `layer_budget=25` the controller's cost-model script used for
the whole corpus, `dog` resolved in 10 candidates and 565.5 s (contended),
while `spider` consumed roughly **6.4×** `dog`'s wall clock -- a full 60
minutes -- and produced no verdict at all. `dog`'s own shipped default is
`layer_budget=200`, not unbounded; the corpus-wide run described here used
25 for every subject, `dog` included. Do not read `spider`'s absence from the
per-subject outcome tables (evidence README "Layer order" section, this
spec's own `§6` "recorded per subject" list, and `test_box_pleat_e2e.py`'s
`LAYERS_EXPECTED`) as a gap in measurement discipline — it is the deliberate
alternative to recording a guessed value, and this paragraph is where the
measurement that justifies the gap lives.

### Final review 2026-09-23: the graph cache's premise was untested, and §4.4's own sentence names the gap

`§4.4`'s "The graph cache is keyed by the frozenset of folded piece keys,
because `assign`'s centre-column F decisions can change the crease set" is
**itself the counterexample to `compile.py`'s shipped comment**, which
justified dropping that key with "the crease set is fixed and Task 1 proved
the emitted FOLD topology is label-independent." Task 1's theorem
(`test_layers_theorem.py::test_merge_topology_does_not_depend_on_labels`)
covers an M<->V relabelling of a FIXED crease set only — it applies a
global mirror, which preserves the F set by construction and so cannot
see an F-set change. `emit._merge_runs`'s `vertices_coords`/`edges_vertices`
are functions of the **kept** (non-F) pieces, and `assign.initial_readings`
gives every centre-column contour piece the domain `["F", lab, flip]` — a
solver variable, not a constant — so the F set is not fixed across
candidates the way the shipped comment claimed. An F-set change between
candidates would either raise a bare `KeyError` out of
`layers.propagate`'s `labels[s.edge]` (caught by `compile.py`'s existing
`except (ValueError, RuntimeError, KeyError)` and typed as an
indistinguishable `AssignFail("error", ...)`) or silently resolve to
different vertices and return a verdict for a pattern that was never
checked, letting a contradictory base reach `emit`.

**Measured as not currently violated:** all 7 emitting subjects (this
corpus) show exactly 1 FOLD topology and 1 F-set across every candidate
`_check` saw, and 0 of 154 centre-column variables resolve to `F`. So this
was an unguarded assumption, not a live defect.

**Fix:** `compile.py`'s `_check` now freezes candidate 1's
`(vertices_coords, edges_vertices)` into `topo_cell` alongside the cached
graph, and every later candidate's topology is asserted (bare `assert`,
deliberately uncaught, matching `layers.constraint_graph`'s own drift-guard
precedent) to reproduce it before its labels are propagated over the cached
graph. `compile.py`'s cache-key comment and `_check`'s docstring are
corrected to state what is actually relied on — the F set being stable,
not merely the crease set among creased edges — and that the new guard is
what enforces it. `test_layers_theorem.py`'s fact-2 module docstring is
extended to say its global-mirror test cannot see this gap and to point at
the guard as what covers it instead; no new test was added, since the guard
is unconditional and runs on every `_check` call regardless of which test
exercises it.

**§4.4's own sentence above is superseded in place by this note**: the
"crease set is fixed... Task 1 proved" framing (repeated, independently, in
`compile.py`'s old comment) does not hold for the F set, and the graph
cache's soundness now rests on the guard described here, not on that
framing.

## 12. Amendment 2026-09-23: the deferred §10 follow-up, measured and sized

§10 defers two things: the *correct* fix (cross-check a known slot against
every later derivation instead of skipping on disagreement) and, implicitly,
the search §10 calls "ADK's satisfiability result" that this module does not
implement. Neither was ever sized. A census on the 8 emitting subjects now
sizes both — full table and readings in
`docs/superpowers/evidence/2026-09-20-box-pleat/README.md`, probe and JSON in
that directory's `oracle-census/`.

**The search is nearly empty on this corpus, so §10's cross-check is the whole
of the follow-up.** Propagation forces EVERY overlapping face pair on 5 of the
8 subjects, including all the large ones: `dog` decides all 30,697 across a
180-face stack, `horse` all 12,407, and `octopus`/`frog`/`guinea_pig` all of
theirs. On those subjects the relation is complete — a total order on every
arrangement cell — so deciding whether a valid order exists needs no search at
all, only a full cross-check of the completed relation, which is polynomial.
`bird` and `lizard` leave 8 unforced pairs each (256 completions before
pruning). Only `starfish` has a real search instance: 236 unforced pairs in one
34-face cell.

**Consequence for how the follow-up should be scoped.** It is a VERIFIER, not a
solver. Implementing ADK's DFS backtracking would be building the expensive
half of a decision procedure for a corpus whose undecided-variable count is 0
on 5 of 8 subjects and 8 on two more. The cross-check §10 already names
subsumes the confluence worry on the same pass: if an order-dependent write
happened, re-checking every family against the finished relation catches it.

**Non-confluence has no measured exposure on box-pleat geometry, which
relocates that risk rather than retiring it.** Re-running propagation under
FIFO drain and two seeded-random worklist orders moves nothing on any of the 8
— 0 pairs disagree, 0 decided by only one order, 0 verdict flips. That does not
contradict §10, whose flip is on `mesh-humanoid`, serve-path geometry. It also
does not mean the rule is confluent: the probe permutes the closure worklist
and its neighbour walk, not the order `_propagate` applies the other families,
and three orders are not all orders. The confluence follow-up's value is on the
serve path, where `mv_symmetrize`, `mv_repair`, `root_rank` and `server.py`'s
serve gate all read `layer_order` — and where every current reading, including
`quadruped`'s contradiction → consistent from the root wave, was taken with the
propagation-only rule. So the fix must be ADDITIVE and opt-in, or it silently
re-decides five served subjects.

**Still unmeasured, and this census cannot see it.** `AREA_EPS`-dropped sliver
cells, the other independent under-refutation reason, are excluded from the
denominator by construction — a dropped cell removes pairs from `cons.pairs`
before they are counted. "0 unforced" means the pairs that survived `AREA_EPS`
are all forced, nothing more.
