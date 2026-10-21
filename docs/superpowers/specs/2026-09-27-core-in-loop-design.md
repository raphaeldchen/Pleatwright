# Core extraction in the CEGAR loop: does dense layer-ordering converge?

**Status:** design approved 2026-09-27. The gated follow-on that
`2026-09-27-nogood-core-design.md` §8 said a core of <=10 variables would
justify. Additive to `2026-09-24-dense-pleats-design.md` (gap 1), whose §6.3 is
the blocker this attacks.

**Goal.** Wire minimal-unsat-core extraction into the box-pleat CEGAR loop
behind a flag, and run one cheap A/B to answer a single question: **does dense
layer-ordering converge when each rejection prunes its actual cause instead of
its dependency cone?**

This is an experiment with a production change, not a feature. Nothing is
enabled by default and nothing reaches the serve path.

---

## 1. Why now

`2026-09-24-dense-pleats-design.md` §6.3 is where gap 1 stopped: dense labelling
works (4,868 M/V pieces on `lizard`, every interior vertex satisfying Maekawa,
Kawasaki and the arrangement oracle) but **no globally stackable labelling is
reachable** -- every candidate is refused by the layer-order checker, and the
diagnosed cause was that each no-good prunes too little.

Five levers followed from that diagnosis. Four are closed or degenerate: raising
the budget (candidates scale as budget^0.71, economically implausible), the
F.1.1 pleat filter (a no-op at the paper's own granularity, destructive below
it), no-good indexing (the clause scan is 1.28% of runtime), and F.3 ridge
assignment (one rule already ours, one inert, residual ~5-10% of the CSP).

The fifth measured **positive** (`evidence/2026-09-27-nogood-core/`): the median
actual cause of a rejection is **5 solver variables** where the clause records
**109**, with `core_variables <= 10` on **31 of 31** rejections and an observed
maximum of 8. Core size is flat at 4-8 while cone size spans 6-245, which is the
signature of `witness.creases` being a dependency CONE (it comes from
`layer_order`'s `exc.deps`, the whole derivation chain) rather than a CUT.

So the loop has been forbidding one point in a 2^109 space where it could be
forbidding one in 2^5. This spec asks whether closing that gap is enough.

**It is not obvious that it is.** A smaller core implies stronger pruning per
rejection, NOT convergence -- the large-budget run refused **584 distinct**
candidates in 8,865 s, every one a contradiction never seen before. The space of
contradictions may simply be too large to exhaust at any pruning strength. That
is the question this experiment exists to settle, and either answer is a result.

## 2. Prior art (CLAUDE.md section 0)

| source | adopted / rejected |
|---|---|
| Junker, *QuickXplain* (AAAI 2004); formal treatment arXiv:2001.01835 | **Adopted**, already implemented and measured here. Divide-and-conquer irreducible-subset extraction for a monotone property. 0 of 31 measured rows exceeded its `2k*log2(n/k)+2k` call bound. |
| Soerensson & Biere, *Minimizing Learned Clauses* (SAT 2009, LNCS 5584:237-243) | **Adopted as precedent.** Minimizing learned clauses is standard CDCL practice -- in MiniSat since 2005 and, in the authors' words, adopted by most modern SAT solvers. This is not a novel gamble. |
| Ohrimenko, Stuckey & Codish, *Lazy Clause Generation* | **Adopted as the argument.** LCG states the bet exactly: *"Learning changes the trade-offs for propagation. It may well be worth spending more time calculating stronger propagation, if the results can be reused elsewhere using learning, thus amortizing the cost over multiple uses."* It also gives the formal notion: a clause set is **stronger** than another if it implies it. A core-derived clause is strictly stronger than the cone-derived one it replaces. Our `global_check` is a propagator and `witness.creases` is its explanation; this slice strengthens the explanation. |
| Fleury & Biere, *Efficient All-UIP Learned Clause Minimization* (SAT 2021) | **Found and consciously NOT acted on -- see below.** The paper records that unbounded shrinking is too expensive in CDCL: *"In order to avoid spending too much time in such shrinking procedures the authors of [Feng & Bacchus] had to limit its effectiveness"*, and *"If fully applied, shrinking derives a subset of the decision-only clause. Therefore, it is limited."* |
| 1-UIP / implication-graph cut (CDCL) | **Rejected, second time.** Learning from a cut rather than the dependency cone is the textbook fix and would be cheaper than extraction. It requires changes inside `layer_order.py`, which is off-limits: `mv_symmetrize` on the serve path shares it. |

**Why the Fleury & Biere cost warning does not force a bounded variant here.**
It is the strongest available argument for capping extraction, and the reason it
does not apply is a difference of scale, not a disagreement. A CDCL solver sees
conflicts millions of times and must minimize within microseconds, so unbounded
shrinking is ruinous. Here a single rejection already costs ~7-15 s and there are
~113 of them in the baseline run; extraction adds a measured median 5.27 s. That
is ~35% overhead on an operation occurring about 10^2 times, not 10^6. Adding a
bound now would be a knob with no measurement behind it -- the failure mode that
produced the withdrawn `2026-09-26-nogood-indexing-design.md`. **The A/B in
section 7 is the measurement that would justify a bound**, and section 9 records
it as the designated follow-on if cost turns out to dominate.

## 3. The change

The wiring point is **one branch in `compile._check`**, not the CEGAR loop.

`_check` already owns the constraint graph, the candidate's labels and the
witness, and it ends with:

```python
        return _layers.piece_keys(w, fold), w
```

`assign` consumes exactly that (`keys, witness = verdict`) and builds its clause
from `keys` alone. So narrowing the clause means handing `piece_keys` a witness
whose `creases` are the core. `piece_keys` reads only that field
(`layers.py:190-227`; the sole reference is the `for k in witness.creases` loop
at `:214`), so a witness's `faces` and `prov` cannot affect the keys.

`piece_keys` also validates every crease against the fold's `edges_vertices` and
raises `ValueError` on a crease that is not an edge (`:216-221`). A core is a
SUBSET of `w.creases`, whose members the unshrunk path already resolves, so
narrowing can never make that validation newly fire.

**`assign.py` is not modified by this spec.** Its DFS, its CEGAR loop and its
clause comprehension are untouched, so the `2026-09-27-nogood-core-design.md`
§11 constraint ("do not wire core extraction into `assign`'s CEGAR loop") is
satisfied in letter: the loop still receives a `(keys, witness)` pair and cannot
tell the difference.

```
compile._check(cand)
   |
   propagate(graph, labels)  -> w  (unchanged)
   |
   +-- [core_extraction] cores.shrink(graph, labels, w.creases) -> core
   |
   piece_keys(replace(w, creases=core) if core_extraction else w, fold), w
   |
assign's clause comprehension                 (unchanged)
```

**The witness returned is the ORIGINAL `w`, not the shrunk one.** Only the keys
narrow. `assign` stores the witness in `AssignFail` payloads and
`compile_tree` surfaces it in `LayerFail`; the full cone is the more informative
diagnostic and keeping it means no failure payload changes shape.

## 4. Interfaces

### `mcp_harness/box_pleat/cores.py` (new)

Pure. Imports `layers` and nothing else from the package.

```python
class CoreExtractionError(Exception):
    """Extraction's PRECONDITION or POSTCONDITION failed, or the returned
    core was EMPTY. See section 6."""


def quickxplain(candidates, holds, counter=None) -> frozenset:
    """An IRREDUCIBLE subset of `candidates` for which `holds` stays true.

    `holds(frozenset)` must be MONOTONE: true for a set implies true for
    every superset. `counter`, when given, is a one-element list
    incremented once per oracle call.

    Irreducible, not minimum: a smallest core is NP-hard and is not
    attempted. Candidates are consumed in the order given.
    """


def shrink(graph, labels, creases, *, counter=None) -> frozenset:
    """The creases in `creases` that ALONE force `graph`+`labels` to contradict.

    Feeds `sorted(creases)` to `quickxplain` against the oracle
    `layers.propagate(graph, labels, only=S) is not None`.

    Sorted because QuickXplain's result depends on how it splits: an
    unordered input returns a different irreducible core run to run, making
    every run unreproducible. Which core is found is not canonical; finding
    the same one again must be.
    """
```

### `compile_tree` (modified signature)

```python
def compile_tree(nodes, pairs, *, max_N=None, pack_budget=200_000,
                 assign_budget=500_000, layer_budget=200,
                 certify_budget=layer_certify.CERTIFY_BUDGET,
                 dense: bool = False,
                 core_extraction: bool = False,
                 debug_cores: list | None = None,
                 debug_clause_sizes: list | None = None) -> Result:
```

* `core_extraction=False` is the default and every existing caller keeps it.
  With it False, `_check` is byte-for-byte the function it is today.
* `debug_cores`, when a list, receives one tuple per rejection:
  `(blamed_creases, core_creases, oracle_calls, secs)`. It mirrors `assign`'s
  existing `debug_clause_sizes` convention. Diagnostics only; production
  callers leave it `None`.
* `debug_clause_sizes`, when a list, is **passed straight through to
  `assign`**, whose identically-named parameter already exists and collects one
  clause size in solver variables per rejection. `compile_tree` does not
  currently forward it, so §7.3's only surviving guard would otherwise be
  unmeasurable from the compile path -- the clause is built from `assign`'s own
  `var_of`/`idx`, which `_check` cannot see. One argument, no new mechanism.
* `compile.py`'s `from dataclasses import dataclass, field` gains `replace`.

## 5. Why the narrowed clause is sound

The oracle certifies that seeding **only** the core, at this candidate's own
labels, already contradicts. Any labelling that agrees with the candidate on
those creases therefore also contradicts, because `propagate(graph, labels,
only=core)` depends on no other label. The narrowed clause forbids strictly more
assignments than the cone-derived one, and every one of them is genuinely
unsatisfiable. This is the LCG notion of a **stronger** explanation.

`layer_order._propagate` is **not confluent**, and that does not threaten this.
Non-confluence costs *completeness* -- a contradiction may be missed under one
propagation order -- not *soundness*: a contradiction that IS reported is a real
derivation from those seeds. The measurement already tested this per rejection
(`full_blamed_contradicts` true and `empty_contradicts` false on 31 of 31 rows).

The danger direction is a core that is too SMALL, which would forbid assignments
that are not contradictory and could make the search report unsat when a
solution exists. QuickXplain's recursion does not guard against this directly:
most of its internal unions are never themselves passed to the oracle, so
correctness rests on an invariant -- that `holds` is MONOTONE, so truth on the
tested background sets propagates to the returned union -- rather than on every
candidate core being tested. That invariant in turn rests on a precondition,
`holds(frozenset(candidates))`, that the recursion never checks before its
first split. `cores._core` (`cores.py:106-168`) closes both gaps with explicit
runtime guards around `quickxplain` rather than trusting them silently: it
refuses before calling `quickxplain` if the precondition does not hold (which
would otherwise degrade to a silent no-op core), and it refuses after if
`holds(core)` is False for the value about to be returned (which would
otherwise ship an unsound core). The postcondition guard is the one doing real
work here: `layer_order._propagate` is not confluent, so "more constraints
still yields the contradiction" is an empirical finding on this oracle (31 of
31 measured rejections), not a theorem, and nothing else in this design stands
between that gap and an unsound clause.

## 6. Error handling

**Three distinct conditions raise `CoreExtractionError`, and the message text
distinguishes them** (`cores.py:50-68` for the class, `:106-168` for `_core`,
which is where all three are actually raised):

**The precondition case.** `quickxplain` assumes `holds(frozenset(candidates))`
is true before it starts splitting; `_core` checks this directly rather than
trusting it. If it is false, the recursion's monotone-invariant argument no
longer applies -- every leaf still contributes its singleton, so the entire
candidate set comes back as a "core" that does not itself satisfy `holds`,
SILENTLY, and for this feature's caller that degrades to exactly the
un-narrowed clause emitted before extraction existed. Not unsound on its own,
but indistinguishable from "extraction is ineffective" and a threat to the
Task 3 clause-size measurement, so `_core` raises rather than returning it.

**The empty-core case must stop the run.** If `holds(frozenset())` is true -- the
empty seed set already contradicts -- the core is empty, `piece_keys` returns
nothing, and `assign`'s clause comprehension yields `{}`, which it reports as
`AssignFail("layer_bad_witness")`: a wrong answer dressed as a verdict.
`empty_contradicts` was False on 31 of 31 measured rows, so this condition means
the oracle is broken, and a broken oracle invalidates every clause in the run.

**The postcondition case.** `_core` also checks `holds(core)` directly on the
value it is about to return, instead of trusting QuickXplain's invariant
silently. This is the one that guards SOUNDNESS rather than a no-op:
`layer_order._propagate` is not confluent, so "more constraints still yields
the contradiction" is an empirical finding on this oracle (31 of 31 measured
rejections), not a theorem, and this guard is what stands between that gap and
an unsound clause reaching the CEGAR loop.

In all three cases `shrink` raises `CoreExtractionError`. That class
deliberately subclasses `Exception` and **not** `ValueError`/`RuntimeError`/
`KeyError`, which are the three the `except (ValueError, RuntimeError,
KeyError)` handler around the `assign(...)` call in `compile_tree` catches and
folds into an indistinguishable `AssignFail("error", ...)`. It therefore
**propagates out of `compile_tree` uncaught**, matching the module's existing
documented treatment of conditions that must not be mistaken for a normal
refusal.

Exceptions raised by the extra `propagate` calls extraction makes are already
covered: `compile.py`'s module docstring records that hook calls into
`layers.propagate` are caught by that same handler.

## 7. The experiment

### 7.1 Protocol

One A/B on dense `lizard` at the **500,000-node budget**, the same budget as the
committed baseline, changing exactly one boolean:

* **arm A** `compile_tree(dense=True, core_extraction=False)`
* **arm B** `compile_tree(dense=True, core_extraction=True)`

`lizard` because it is the only subject whose loop yields many rejections
cheaply: `octopus` and `dog` do not finish dense labelling inside a 300 s cap at
all, and the other subjects' first dense candidate produces a 2-crease blamed set
with nothing to shrink.

Both arms record: outcome kind and site, rejections, wall-clock, nodes,
`debug_clause_sizes` (clause size in solver variables, via the new passthrough),
and for arm B `debug_cores`. Arm A reproduces the committed baseline and is run rather than
quoted, so the comparison is same-machine and same-session.

Cost expectation: arm A ~834 s, arm B ~1,430 s worst case (113 rejections x
5.27 s extraction on top), so **~40 minutes for the pair** if nothing improves.

### 7.2 The bar, fixed before the data

Baseline, from the committed `nogood-lizard.json`: **113 rejections, 834.0 s,
`AssignFail(kind='budget', site=500000)`, median clause 202 variables.**

**The TERMINAL OUTCOME is the primary signal.** The rejection count is not, and
§7.3 explains why.

| arm B outcome | reading | next |
|---|---|---|
| reaches **`emit`** | dense layer-ordering CONVERGES | wire on for dense; `2026-09-24-dense-pleats-design.md` component 1 and its §10 gallery become reachable |
| outcome becomes **`layer_unsat`** (a decision, not a timeout) | the mechanism works AND no dense labelling of this crease set is stackable | major result: the blocker is the crease SET, pointing at component 1, not the search |
| still `budget`, and clause size **dropped to single digits** | the mechanism works; convergence is UNRESOLVED at this budget | size the ~3.3 h 5,000,000-node run from the measured per-rejection cost and rejection count, then decide whether to spend it |
| still `budget`, and clause size **did not drop** | extraction is ineffective or broken here | no convergence claim in either direction; fix the extraction or close the lever, but do not report a negative from this run |

Stated now because a bar chosen after seeing the number is not a bar.

### 7.3 Why the rejection count is NOT the criterion

The approved version of this bar made ">=5x fewer rejections, with
nodes-per-rejection within 2x" a success row. **That is arithmetically
incoherent and is corrected here before any data exists.**

A run that exhausts its node budget stops at `nodes < 0` having consumed exactly
the budget, so **nodes-per-rejection = budget / rejections identically**. At a
fixed 500,000 nodes, 113 -> 22 rejections *necessarily* means 4,424.8 -> 22,727
nodes per rejection -- a 5.1x rise. The "within 2x" guard would therefore have
automatically failed the very row it was meant to validate. The two figures are
one figure, not two independent readings.

Nor does a rejection drop discriminate on its own. Stronger clauses exclude more
of the space a priori, so **fewer distinct complete candidates before exhaustion
is the EXPECTED signature** -- but it is equally consistent with a search
wandering deeper without getting closer to a decision. It sizes the follow-on
run; it does not establish progress.

What survives from the original intent is the one guard that does work:

**Clause size must actually drop.** Arm B's median `debug_clause_sizes` must fall
from the baseline's **202 solver variables** to single digits (the core
measurement's median was 5). If it does not, the run measures a broken extraction
rather than a fact about convergence, and **no row of §7.2 may be claimed** --
neither a positive nor a negative.

And one reporting rule, because seconds and nodes are not interchangeable here:
extraction adds ~5.3 s per rejection **by construction**, so any wall-clock
comparison between the arms is confounded. Compare nodes and outcomes; report
seconds only as the experiment's cost.

## 8. Testing

* **`cores.quickxplain`**, as real pytest rather than an in-script self-check:
  recovers a synthetic 2-of-8 monotone cause exactly; the result is irreducible
  (removing any single element makes `holds` false); deterministic across
  repeated calls on the same sorted input; and made more than 3 oracle calls, so
  a degenerate short-circuit cannot pass.
* **`cores.shrink`** on the `LIZARD_V1` fixture (`tests/data/lizard-v1.fold`,
  measured: 27 slots, 27 labels, witness naming 12 creases, all of them slot
  edges): the core is strictly smaller than the blamed set, still contradicts,
  and every element of it is necessary. Guarded for non-vacuity by asserting the
  blamed set is non-empty and that the unshrunk labelling contradicts.
* **The empty-core guard fires:** `shrink` raises `CoreExtractionError` when
  handed an oracle that contradicts on the empty set. Constructed directly
  against a synthetic oracle, not via a real fold.
* **Inertness, load-bearing.** With `core_extraction=False`, every currently
  emitting sparse subject reproduces its committed fold **byte-for-byte**. This
  is the invariant the dense-pleats work has used throughout and it is the one
  test that must not be weakened.
* **Not tested end to end in pytest.** A dense `compile_tree` run is 15+ minutes
  and `test_box_pleat_layers.py` already costs that. The section 7 A/B is the
  evidence for the dense path; adding a dense case to the suite would double a
  suite that is already the slowest thing in this repository.

## 9. Risks

1. **Extraction cost dominates and nothing converges.** Then the answer is the
   fourth row of §7.2 and the lever closes. The designated follow-on, if and only
   if the A/B shows cost rather than pruning strength as the binding constraint,
   is a bounded variant along Fleury & Biere's lines -- justified then by
   measurement rather than by analogy.
2. **`lizard` does not generalise.** 26 of the 31 rows behind the core
   measurement were `lizard`, and its `propagate` is ~100x slower than the other
   five subjects'. A positive A/B is evidence about `lizard` and must be reported
   as such; the subjects that would test generality (`octopus`, `dog`) cannot
   currently produce a dense labelling at all.
3. **A `layer_unsat` outcome may be an artifact of the F set rather than a fact
   about dense labelling.** The crease set is fixed by `contours.py`'s elevation
   field, and component 1 (F.1.1 step 5, the contiguity fill) was never built.
   An unsat verdict must therefore be reported as "unsat for THIS crease set",
   never as "dense box-pleating is infeasible".
4. **Topology drift.** `_check`'s cached constraint graph is indexed by candidate
   1's FOLD vertex ids and asserts every later candidate matches. Extraction adds
   no new exposure -- it reuses the same graph and labels within one `_check`
   call -- but the assert stays load-bearing and must not be removed.

## 10. Evidence

`docs/superpowers/evidence/2026-09-27-core-in-loop/`, carrying `ab.py`, `ab.json`
(both arms' full records), and a README stating the outcome against §7.2's four
rows, both §7.3 guards with their measured values, and -- whichever way it falls
-- the limits in §9.2 and §9.3.

## 11. Out of scope

* **Enabling `core_extraction` by default.** Gated on the A/B; a separate
  decision with its own record.
* **The 5,000,000-node run.** Gated on row 3 of §7.2.
* **Any change to `assign.py`, `layer_order.py`, or the serve path.**
  `grep -c box_pleat mcp_harness/server.py` stays 0.
* **A bounded/approximate extraction variant.** §9.1: only if the A/B shows cost
  is the binding constraint.
* **`2026-09-24-dense-pleats-design.md` component 1 (`pleat_grid.py`) and its
  §10 dense-beside-sparse gallery.** Both become reachable only if this
  experiment converges, and both get their own spec.
