# Minimal unsat cores for the CEGAR no-good clause (measurement slice)

**Status:** design approved 2026-09-27. Follow-on from
`2026-09-24-dense-pleats-design.md` section 6.3.1, which named this and called
it "the root-cause fix". **Scope is a MEASUREMENT, not a production feature**
(owner ruling, 2026-09-27): find out how small a core actually is before any
change to the CEGAR loop.

**Goal.** The clause the CEGAR loop learns is a median of **109 solver
variables**, and prunes almost nothing. Measure whether its *actual cause* is
small enough that learning the cause instead of the dependency set would change
convergence.

---

## 1. The measurement this starts from

Instrumenting production's rejection path on dense `lizard`, 25 rejections:

| reading | min | **median** | max |
|---|---|---|---|
| `witness.faces` | 3 | **3** | 3 |
| `witness.creases` (FOLD edges blamed) | 6 | **172** | 386 |
| `piece_keys` (unit creases) | 39 | **1,139** | 2,411 |
| clause (solver variables) | 6 | **109** | 245 |

**Every contradiction was a `taco_tortilla` among exactly THREE faces, and the
recorded cause was 172 FOLD edges.** The conflict is tiny; the explanation is
enormous. `witness.creases` is built from `layer_order`'s `exc.deps`, which
accumulates the whole derivation chain, so it is a dependency *cone*, not a
*cut*.

That gap is the entire opportunity, and it is also the entire risk: if the cone
is 172 because the cause really is 172, there is nothing here.

(The large-budget run's corpus-wide figures are median 2,069 creases / 202
variables over 584 rejections; the 25-rejection sample above is smaller on both
counts. The spec uses the sample's figures where it compares like with like, and
the bar in section 8 is set against the sample's 109.)

## 2. Prior art (CLAUDE.md section 0)

**External, read 2026-09-27.**

* **Junker, *QUICKXPLAIN: Preferred explanations and relaxations for
  over-constrained problems* (AAAI 2004); formal treatment in Rodler,
  *Understanding the QuickXPlain Algorithm* (Artif. Intell. Rev. 2022,
  arXiv:2001.01835).** Divide-and-conquer extraction of an irreducible subset
  having a **monotone** property, in between `log2(n)` and `2*log2(n)` oracle
  calls, average `1.5*log2(n)`. **Adopted** as the extraction algorithm: our
  property is monotone (section 4.2) and our oracle is expensive, which is
  exactly the regime QuickXplain is for.
* **Deletion-based and insertion-based MUS extraction.** **Rejected**: linear in
  the candidate set, so ~172 oracle calls per rejection where QuickXplain needs
  ~20.
* **CDCL 1-UIP conflict analysis** (implication-graph cut rather than dependency
  cone). **Rejected for this slice, and the reason matters**: it is the
  structurally cheaper answer -- essentially free per conflict -- but it requires
  `layer_order`'s propagation to expose its implication structure, and
  `layer_order.py` has been untouched across this entire line of work because it
  is shared with the serve path via `mv_symmetrize`. If this slice shows cores
  are small, a 1-UIP-style cut becomes the obvious follow-on and would get its
  own spec and its own risk argument.
* **Li et al., *Clause Vivification by Unit Propagation in CDCL SAT Solvers*
  (arXiv:1807.11061).** Noted as adjacent; minimises learned clauses by
  propagation. Not adopted -- it presumes a unit-propagation engine we do not
  have.

**In-repo.** `layer_certify.collapse` (parity quotient) and
`interleave.colour_graph` (2-colouring) make union-find-style reasoning
house-familiar, but **nothing in this repo computes a core**, and
`layer_certify.decide` re-propagates from scratch per node rather than analysing
conflicts. This is the project's first conflict analysis.

## 3. The blocker, and the one production change

**`propagate` cannot be called with a partial labelling.** `layers._seeded`
(`layers.py:124`) iterates **every** slot in `graph.slots` and reads
`labels[s.edge]`, so a missing key is a `KeyError`; the docstring states the
contract outright ("`labels` maps every slot's edge key to M or V"). An oracle
that "propagates with only the subset labelled" therefore cannot be written
against today's signature.

**The change:**

```python
def propagate(graph: LayerGraph, labels: dict, *, only=None) -> Witness | None:
    """... `only`, when not None, seeds ONLY the edge keys it contains, leaving
    every other slot unconstrained. `None` seeds every slot, which is the
    pre-existing behaviour exactly."""
```

`_seeded` gains the same parameter and filters `graph.slots` by it.

**Why this and not a diagnostic-side reimplementation.** The alternative is for
the diagnostic to build the `dataclasses.replace(graph.cons, direct=...)`
structure itself. That duplicates production's seeding logic, and **a probe that
re-implements production is a recorded failure mode in this project's memory**
(`extraction-geometry-merged-and-measured`: a probe that re-implemented
production read "0 moved" while a direct call moved `octopus` 4 -> 8). Adding an
inert parameter is smaller and cannot drift.

**Why it is safe.** `only=None` is the default and reproduces today's behaviour
by construction. No existing caller passes it, so sparse and dense output are
unchanged; section 9 requires that be verified, not assumed.

## 4. The oracle

### 4.1 Definition

`core_holds(S)` := `propagate(graph, labels, only=S) is not None` — the creases
in `S`, at the candidate's own labels, are **alone sufficient** to force a
contradiction. Every crease outside `S` is left unconstrained.

**Every element of `S` must be a slot edge.** `witness.creases` comes from
`layer_order`'s `exc.deps`, and whether those are always slot edge keys is an
assumption, not a documented guarantee. **The diagnostic must assert
`witness.creases <= {s.edge for s in graph.slots}` on every rejection** and
report a violation rather than silently dropping the stragglers — a dropped
crease would make a core look smaller than it is.

### 4.2 Monotonicity, which QuickXplain requires

If `S` forces a contradiction then so does any `T ⊇ S`: seeding more slots only
**adds** `direct` constraints, and a contradictory constraint system stays
contradictory when constraints are added. So `core_holds` is monotone.

**Verified empirically rather than trusted**, on every rejection:

* `core_holds(witness.creases)` is **True** (the full blamed set contradicts) —
  if this fails, the oracle does not reproduce the rejection it came from and
  nothing downstream is meaningful.
* `core_holds(frozenset())` is **False** (the empty set does not) — otherwise the
  contradiction is independent of the labelling and the whole framing is wrong.
* for each extracted core `C`, `core_holds(C ∪ {one extra blamed crease})` is
  **True**.

### 4.3 Soundness

A core is **tested**, never assumed, so an unsound core cannot be produced. This
matters more than size: a clause that is too *small* forbids assignments that are
not actually contradictory, which prunes valid labellings and can make the search
report unsat when a solution exists. Today's clause is weak but correct, and that
is strictly better than small and wrong.

## 5. Extraction

QuickXplain over `witness.creases`, with `core_holds` as the oracle, returning an
**irreducible** subset — every element necessary, i.e. removing any one makes the
contradiction disappear. Irreducible, not globally minimum: a smallest core is
NP-hard and is not attempted, exactly as the greedy-vs-minimum ruling went for
`interleave`'s odd-cycle release.

**The candidate set is processed in a DETERMINISTIC order** -- `sorted(...)` over
the crease keys -- because QuickXplain's result depends on the order it splits,
so an unordered input would yield a different irreducible core run to run and
make every figure in section 7 unreproducible. Which irreducible core is found
is not canonical; *that one is found again* must be.

Cost is reported in **oracle calls** as well as seconds, because seconds are
dominated by `propagate` and `propagate` varies ~100x across subjects
(section 6).

## 6. Sampling: breadth AND depth

**`lizard` alone would mislead in both directions.** Its `propagate` costs
**1.07 s** against **0.004-0.014 s** on the other five measured subjects
(`evidence/2026-09-24-dense-pleats/README.md` section 4b, finding 3) — it is the
corpus outlier by two orders of magnitude — so a `lizard`-only cost figure
overstates extraction cost by roughly 100x. But `lizard` is the only subject
whose CEGAR loop yields many rejections cheaply.

* **Breadth — 1 rejection on each labelling-capable subject** (`starfish`,
  `lizard`, `frog`, `horse`, `bird`, `guinea_pig`). Obtained from
  `assign(global_check=None)`, which returns the first locally feasible
  candidate: no CEGAR loop needed, so this is cheap. `octopus` and `dog` are out
  of reach — they produce no candidate within 300 s.
* **Depth — 25 rejections on `lizard`**, matching the sample in section 1 so the
  before/after comparison is like-for-like.

## 7. What is reported, per rejection

`witness.kind`; `witness.faces` count; blamed creases; **core size in creases**;
**core size in SOLVER VARIABLES** -- the clause's own unit, and therefore the
headline -- ; oracle calls; extraction seconds; and the three monotonicity checks
from 4.2.

**How the variable count is obtained**, since `var_of` is a local inside
`assign` and not returned: by the in-memory patch technique this project has
already used twice (`evidence/2026-09-26-gap1-phase0/phase0.py`,
`evidence/2026-09-26-nogood-indexing/where_the_time_goes.py`) -- read
`box_pleat/assign.py`, insert a single line stashing `dict(var_of)` into a probe
dict, **assert the diff added only that line**, and import the result under the
dotted name `box_pleat._assign_<something>` so its relative imports resolve.
Never a committed fork of `assign.py`, and the script must refuse to run if the
anchor text it patches no longer matches exactly once.

The variable-level core is then `{var_of[idx[k]] for k in piece_keys(core, fold)}`
restricted to keys that are pieces with variables -- the same expression
`assign` itself uses to build the clause (`assign.py`, the `clause = {...}`
comprehension), so the two cannot disagree about what a clause's variable set
is.

Per subject: the median and max of each, beside the pre-core figures so the
tightening ratio is visible without arithmetic by the reader.

## 8. The bar, set before the data arrives

Today's clause is a median of **109 solver variables** on this sample.

* **Core <= 10 variables** — the ~10x tightening section 6.3.1 hoped for.
  Justifies a follow-on spec that wires extraction into the loop.
* **Core 10-50** — real but ambiguous. The decision then needs the *convergence*
  effect, not the size, and the follow-on is a bounded experiment rather than a
  feature.
* **Core 50+** — the dependency cone was **not** the slack. Recorded as a
  negative and the lever closes. **This outcome must not be answered by
  searching for a better heuristic** — four levers have already been examined in
  this line of work and two died; a fifth dying is information, not a prompt to
  keep digging.

Stated now because a bar chosen after seeing the number is not a bar.

## 9. Testing

* **`only=` is inert.** `propagate(graph, labels)` and
  `propagate(graph, labels, only={s.edge for s in graph.slots})` return equal
  witnesses on a real compiled subject — the explicit-everything case must equal
  the default. Plus a unit test that a strict subset yields a DIFFERENT result on
  a fixture where it should, so the parameter is not silently ignored (a
  parameter tested only in its no-op direction is untested).
* **Byte-identity is NOT required for this slice** and is deliberately not
  claimed: no production call site passes `only=`, so no emitted fold can
  change. Sparse and dense e2e tests staying green is the check that this is
  true, and is required.
* **Oracle non-vacuity, mandatory.** The diagnostic refuses to report unless at
  least one rejection was observed AND the 4.2 checks passed on it. A run where
  `core_holds` never returned True would report cores of size 0 and look like a
  spectacular success.
* **Existing suites stay green:** `test_box_pleat_layers.py`,
  `test_box_pleat_assign.py`, `test_box_pleat_interleave.py`,
  `test_box_pleat_pleat_filter.py`. Use `../.venv/bin/python3` from
  `mcp_harness`; that venv has no `pytest-timeout`, so never pass `--timeout`;
  **never run `pytest tests/`** (5,167 tests, over 3 hours).

## 10. Risks

1. **The cone may be honest.** If cores come back at 50+ variables, the clause
   was never the slack and section 8 closes the lever. This is the most likely
   single outcome and the spec is scoped so that discovering it is cheap.
2. **Extraction may cost more than it saves.** ~20 oracle calls per rejection at
   `lizard`'s 1.07 s propagate is ~21 s, against ~15 s per candidate today. On
   the other five subjects the same 20 calls cost under a third of a second. So
   the cost verdict depends on the subject, and reporting oracle CALLS separately
   from seconds is what keeps that visible.
3. **A small core does not imply convergence.** It implies stronger pruning per
   rejection. Whether that exhausts a contradiction space the large-budget run
   showed to be vast is a separate question, and this spec must not be cited as
   evidence for it.
4. **`exc.deps` may not be exactly the slot-edge set.** Handled by 4.1's
   mandatory assertion rather than assumed.
5. **One production signature changes.** Inert by default, but it is a change to
   `layers.py`, which the layers stage and `compile._check` both call. Section 9's
   inertness test is what stands behind that.

## 11. Out of scope

* **Wiring extraction into `assign`'s CEGAR loop** — the follow-on, gated on
  section 8.
* **A 1-UIP-style implication-graph cut** — cheaper and better if it works, but
  it needs `layer_order.py`, untouched across this work; own spec, see section 2.
* **A globally minimum core** — NP-hard; irreducible is what section 5 targets.
* **`layer_order.py`** — untouched, as throughout.
* **The serve path.** `grep -c box_pleat mcp_harness/server.py` is 0 and stays 0.

## 12. Evidence

`docs/superpowers/evidence/2026-09-27-nogood-core/`: the per-rejection and
per-subject tables of section 7, the monotonicity checks, and the verdict against
section 8's bar stated in whichever direction the data falls.
