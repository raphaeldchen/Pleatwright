# Descent-time clause propagation: what the learned clauses could prune, and don't

**Date:** 2026-09-30
**Status:** design approved, not implemented
**Scope:** one instrument. No production behaviour changes. `grep -c box_pleat mcp_harness/server.py` stays 0.

---

## 1. The question, and why the obvious answers are already refuted

Dense box-pleat `assign()` does not converge on `lizard`. It exhausts a
500,000-node budget and returns `AssignFail(kind='budget', site=500000)`.
Two explanations have already been measured and eliminated.

**"The local CSP is too slow."** It was, and it was fixed. The local-CSP
profile located **79.57%** of dense `assign`'s runtime in a remainder whose
largest component was `free_vars_at` at **65.13%** of it on `lizard`
(`../evidence/2026-09-29-local-csp-profile/`). The vertex index removed it:
the dense corpus went **630.82 s -> 109.90 s (5.740x)**, identity **8/8**
byte-identical (`../evidence/2026-09-29-vertex-index/`). Dense still does not
converge. Speed was never the wall.

**"The learned clauses are too weak."** They were, and that was fixed too.
Core extraction narrowed each rejection's no-good clause **25.2x** -- arm A's
median **202** solver variables against arm B's **8**
(`../evidence/2026-09-27-core-in-loop/README.md`). The terminal outcome did
not change: both arms end on `AssignFail(kind='budget', site=500000)`. An
independent population puts `core_variables <= 10` on **31 of 31** rows with
an observed maximum of **8** (`../evidence/2026-09-27-nogood-core/`), so the
single-digit cores are not an n=3 artefact. Clause *quality* is not the wall
either.

What remains is the shape of the arms themselves:

| reading | arm A (`core_extraction=False`) | arm B (`core_extraction=True`) |
|---|---|---|
| rejections in 500,000 nodes | 113 | 3 |
| nodes per rejection | 4,424.8 | 166,666.7 |
| clause size, median solver variables | 202 | 8 (multiset {5, 8, 8}) |
| wall clock | 1,052.0 s | 954.9 s |
| terminal outcome | `AssignFail(budget, 500000)` | same |

**At most 113 of 500,000 nodes reach a complete candidate.** Over 99.9% of
the budget is descent that never gets to a leaf, and between two candidates
the search burns 4,425 nodes. The live hypothesis is therefore not that the
clauses are weak but that they are **applied too late**: strong enough to
refute, never consulted early enough to steer.

### 1.1 The defect, precisely

`retry()` (`../../../mcp_harness/box_pleat/assign.py:1099`) tests a trial
value two ways, and both are pure refutation:

```python
if (all(feasible(w) for w in touching.get(var, ()))
        and not hits_nogood()):
    return True
```

`feasible` (`assign.py:848`) checks Maekawa / Kawasaki / arrangement / BLB at
the vertices the changed variable touches. `hits_nogood`
(`assign.py:1094`) is:

```python
return any(all(value.get(var) == val for var, val in g.items())
           for g in nogoods)
```

A clause with **any** unbound variable reads `None` for it, fails the `all`,
and is inert. A clause can only ever fire at the instant its *last* variable
is bound to the forbidden value.

In CDCL terms: **this solver has clause learning and no propagation.** A
learned clause of 5 variables with 4 already at their forbidden values is
asserting -- one value of the fifth variable is eliminated -- and the solver
has no way to notice. It descends, explores whatever the MRV order hands it,
and discovers the implication only by trying the value and being refused.

Note what is *not* lost. Because `hits_nogood()` runs before `retry()`
returns `True`, the forbidden value is refused on the same trial it is
offered; no subtree is explored beneath it. The cost of missing propagation
is **indirect**, and it is the same reason BCP pays off in a real CDCL
solver: binding a variable early cascades into the other constraints, where
it can refute values or refute the partial assignment outright.

### 1.2 Why this matters to gap 1

Gap 1 splits: dense *labelling* works, dense *layer-consistency* does not
converge. Dense labels **4,868 of 5,140** candidate pieces on `lizard`
(94.7%) against sparse's 476 (9.3%), with
`audit_maekawa_violations`, `audit_kawasaki_violations` and
`audit_arrangement_violations` all **0**
(`../evidence/2026-09-24-dense-pleats/dense_labelling.json`). What refutes it
is the global layer-ordering step: `propagate_kind: taco_tortilla`,
`verdict: REFUTED`. Every one of the 31 measured rejection cores is a
`taco_tortilla` among exactly **3** faces -- constant across the artifact.

So the CEGAR loop is the only machinery that carries global information back
into the local search, and it carries it 113 times in 500,000 nodes. This
instrument measures whether that information, once carried, is being used at
all during descent.

---

## 2. Prior art: found, adopted, consciously rejected

Required by CLAUDE.md section 0.

| source | finding | disposition |
|---|---|---|
| **GRASP** (Marques-Silva & Sakallah, 1996/1999) -- counter-based BCP: one exact counter per clause, updated on every assignment | This is exactly the mechanism needed | **Adopted.** `ClauseIndex` maintains exact per-clause counters. |
| **Chaff** (Moskewicz et al., DAC 2001) -- watched literals: two watches per clause, visit a clause only when a watched literal becomes false | Replaced counter BCP in production solvers *because* counters cost more per assignment | **Invalidation discipline adopted** (touch a clause only when an incident variable changes). **2-watch mechanism consciously rejected:** two watches tell you lazily *whether* one clause is unit; this instrument needs the eager *count* of unit clauses at every node, which a 2-watch scheme structurally cannot report. The counter cost is the measurement, not an overhead to be optimised away. |
| **`VertexIndex`** (this repo, `../../../mcp_harness/box_pleat/vertex_index.py`) -- counters on bind/unbind plus a recompute-from-scratch verify mode | The pattern works here and its verify mode caught a real bind bug in 21 s | **Pattern adopted. One guard consciously NOT copied** -- see section 6, trap 1. |
| **Glasgow Constraint Solver issue #879** -- value-order heuristics doing work proportional to domain width at every node; fix principle "compute the shape without materialising" | Same defect class, already cited by the vertex-index spec and already paid off there | Not re-applied. This slice's defect is missing inference, not redundant work. Recorded so a reader does not expect it to recur. |
| **`../evidence/2026-09-26-nogood-indexing/`** -- no-good *indexing* was specced and **withdrawn**: the `hits_nogood` scan is 1.28% of runtime, per-node cost is flat, the slowdown is more nodes | Indexing the scan is not the lever | **Respected.** This slice does not index the scan for speed. It changes *what is detected*, not how fast the existing detection runs. The counters happen to be cheaper, which is incidental. |

---

## 3. What is measured

### 3.1 Clause state

For a stored clause `g` (a `{variable: forbidden_value}` map of size `k`),
maintain two counters over its variables:

* `n_agree` -- bound to the value `g` forbids
* `n_contra` -- bound to some other value

| state | condition | meaning |
|---|---|---|
| **dead** | `n_contra > 0` | already satisfied on this branch; can never fire |
| **live** | `n_contra == 0` | still a threat |
| **unit** | `n_contra == 0` and `n_agree == k - 1` | one free variable; one of its values is eliminated |
| **conflicting** | `n_contra == 0` and `n_agree == k` | precisely what `hits_nogood()` detects today |

`hits_nogood` sees only the last row. Every row above it is invisible to the
solver.

### 3.2 The cascade probe, and the domain-size correction

A unit clause eliminates **one** value of its single free variable. It does
**not** in general force a value, because the domain is not always binary.
`prefer()` (`assign.py:1046`) ends:

```python
if can_be_flat(var):
    order = order + ["F"]
return order
```

so a ridge or hinge variable can carry **three** values (`["V", "M", "F"]`).
A unit clause therefore leaves **one or two** values behind, and forces a
value only when the domain has two elements.

The probe is defined on the general case:

> At a unit clause's free variable, remove the value the clause forbids and
> test each **remaining** value with `feasible(w)` for `w in touching[var]`.
> The node is **dead** iff every remaining value is refused.

For a 2-valued variable this is the forced-value test; for a 3-valued one it
costs a second `feasible` sweep. A dead node means the stored clauses and the
local laws **jointly refute the current partial assignment**, and the search
has no way to see it.

**Measured, 2026-10-01.** The 3-valued case was the live risk in this section:
if most unit clauses landed on 3-valued variables, propagation would be weak
*by construction*. **It does not, on this data.** `unit_domain_3` is **0 on
five of the six measured rows**, and on the sixth (dense `lizard` arm A) the
2-valued share is 3069/4137 = **74.18%**; `unit_domain_other` is 0 everywhere.
So wherever a clause goes unit, the inference available is almost always a
forced value. The general-case machinery was still necessary — arm A records
**1068** three-valued events, 1068/4137 = 0.2582 of its unit events — so the
probe's design stands; only the anticipated weakness is absent. See
`../evidence/2026-09-30-clause-propagation/README.md` §4.

### 3.3 Reported quantities

Per arm, per node, aggregated:

| name | definition |
|---|---|
| `nodes` | search nodes executed (counted, never inferred from the budget) |
| `unit_node_fraction` | nodes with at least one unit clause / `nodes` |
| **`dead_node_fraction`** | nodes where every remaining value of some unit clause's free variable is locally refused / `nodes` |
| `clause_availability` | node-weighted mean live-clause count |
| `clauses_total` | clauses stored by the end of the arm |
| `unit_domain_sizes` | histogram of `len(prefer(var))` at unit events (2 or 3) |
| `unit_var_chosen_nodes` | nodes at which `pick` chose a variable that was already the free variable of some unit clause |
| `probe_calls`, `probe_secs`, `observe_secs` | the instrument's own cost, as three figures. `probe_calls` counts `probe()` calls. `probe_secs` times only the inside of `probe()`. `observe_secs` times the whole of `observe()` -- the probes plus the `sorted`, `free_var_of` and `prefer` passes `probe_secs` cannot see -- so `observe_secs >= probe_secs` **while probes are driven only through `observe`** (a direct `probe()` call charges `probe_secs` alone). **`observe_secs` is the observe-side cost, not the total overhead**: neither figure times `note_choice` or the `bind`/`unbind`/`add_clause` counter updates (about 4.4 per bind on the widest arm), and the true total overhead is the wall-clock difference between an instrumented and an uninstrumented run (plan Task 3). Both are charged on the exception path; the end-of-`observe` out-dict writes are skipped when it raises, so the attributes and the out-dict can then disagree |
| `rejections`, `assign_fail` | for the identity gate (section 8.2) |

**Correction, 2026-09-30 (during implementation).** This table originally
listed `unit_latency_nodes` -- per unit event, the nodes elapsed until that
variable is next bound. It is withdrawn and replaced by
`unit_var_chosen_nodes` above. Latency needs cross-node state that **goes
stale on backtracking**: when the search backtracks past the binds that made
a clause unit, the pending entry survives, and the next bind of that variable
records a latency for a clause that is no longer unit. The replacement
carries the same signal -- `unit_nodes - unit_var_chosen_nodes` is "a unit
clause existed and the search worked on something else" -- with no cross-node
state, as one set-membership test against state `observe` builds for the
current node anyway.

**Measured, 2026-10-01: the overhead RATIO does not transfer between budgets.**
Task 3 bounded the instrument's total overhead at roughly **1-3%** on dense
`lizard` at a 20,000-node budget (+0.59 s/+3.2% and +0.33 s/+1.2%, two single
runs on a shared machine). At 500,000 nodes, dense `lizard` arm B's
**observe-side cost alone** reads **15.83 s of 68.2 s = 23.211%** — an order of
magnitude larger as a ratio than that whole range. Task 3's measurement is not
wrong; the driver is probe density, and `probe_calls` per node is
457,592/500,000 = 0.915 on arm B against 116/20,000 = 0.0058 on Task 3's row,
a factor of **157.8**. Quote the overhead range only for the budget it was
measured at. No fraction is affected: every reported fraction is a node count
over `nodes`, and the instrument does not change the node count.

`dead_node_fraction` is the headline and is a **lower bound**, for two stated
reasons: only clauses already unit are considered, and the cascade is one
step, never a fixpoint.

---

## 4. Verdict bands, fixed before any data exists

| `dead_node_fraction` (primary run, either arm) | verdict |
|---|---|
| **>= 0.50** | propagation is the lever. Justifies a follow-on spec wiring one-step propagation into `retry()`. Does not authorise the wiring. |
| **0.05 -- 0.50** | real but partial. Report it; wire nothing. |
| **< 0.05** | propagation **refuted** as a lever for gap 1. Record the negative and redirect. |

**Attribution guard.** If `unit_node_fraction < 0.01` in **both** arms, the
verdict is "clauses essentially never go unit", and `clause_availability`
plus `clauses_total` decide which cause it is:

* arm A clauses are **too wide** (median 202 variables needs 201 bound to
  their forbidden values before going unit), or
* arm B has **too few clauses** (3 in 500,000 nodes; for most of the run
  there are 0, 1 or 2).

These are different next levers and the README must not conflate them. Both
are stated here, before the run, as the expected shape of a null result --
not discovered afterwards.

**Counter-hypothesis, also stated in advance.** A core's 5--8 variables are
the blamed faces of a single `taco_tortilla` among exactly 3 faces, so they
are geometrically adjacent; `touching` and the MRV order may well bind them
consecutively. If so, clauses may go unit often relative to how few there
are. The outcome is genuinely uncertain in both directions, which is why it
is measured rather than argued.

**Measured, 2026-10-01: the counter-hypothesis is CONFIRMED, and the guard
above did not fire.** Arm B reads `unit_node_fraction` **0.741764** on **3**
clauses against arm A's **0.008238** on **113**, so `unit_node_fraction < 0.01`
in *both* arms is false and `attribution_guard_fired` is `false`. The case that
actually arose is the one the guard does not cover: **a high figure on one
arm**. It is settled by normalising out the clause count, which the two causes
above do not do on their own — arm B holds **fewer** live clauses per node than
arm A (`clause_availability` 1.624 against 3.438) and still goes unit 90.0x
more often, and scarcity can only depress that fraction, never raise it. Per
live clause the rates are 0.741764/1.624 = 0.456751 against
0.008238/3.438 = 0.002396, a factor of **190.6**. So arm A is the "too wide"
cause (201 agreeing binds needed at its median 202) and arm B's rate is
**tightness, not scarcity**. The two arms also fell in **different bands**, so
the slice's headline is a split and not a verdict. See
`../evidence/2026-09-30-clause-propagation/README.md` §2-3.

---

## 5. The mechanism: `mcp_harness/box_pleat/clause_index.py`

New module, following `vertex_index.py`'s shape.

```
ClauseIndexError(Exception)
    Deliberately not ValueError / RuntimeError / KeyError, so
    compile_tree's except clause cannot fold it into
    AssignFail("error") and hide a broken instrument as an
    ordinary refusal. Same reasoning as VertexIndexError.

ClauseIndex(value, prefer, touching, feasible)
    var_to_clauses : dict[var, list[tuple[int, value]]]   # cid, forbidden
    n_agree        : list[int]      # indexed by cid
    n_contra       : list[int]      # indexed by cid
    size           : list[int]      # indexed by cid
    unit           : set[int]       # cids currently unit
    probe_calls    : int
    probe_secs     : float
    observe_secs   : float     # whole of observe(): observe-side cost; >= probe_secs only via observe()

    add_clause(clause)  -> cid       # counters computed against live `value`
    bind(var, val)      -> None
    rebind(var, old, new) -> None
    unbind(var, old)    -> None
    unit_clauses()      -> list[int]
    probe(cid)          -> bool      # True iff the node is dead via this clause
    snapshot()          -> dict      # the section 3.3 aggregates
```

`bind` / `rebind` / `unbind` touch only `var_to_clauses[var]`, so cost is the
number of clauses containing that variable. On arm A that is
113 x 202 = 22,826 clause-variable incidences over roughly 5,140 variables,
about **4.4 counter updates per bind** -- wide clauses do not make arm A
expensive.

---

## 6. Three traps

### Trap 1: the `was_bound` guard must NOT be copied from `VertexIndex`

`retry()` reassigns an already-bound variable on the CEGAR path. This is
documented in place at `assign.py:1101-1113` and is the bug `_verify_index`
caught in 21 s during the vertex-index slice: `retry()` is called right after
`nogoods.append(clause)` **without a frame being pushed**, so the deepest
frame's variable is still bound from the candidate just rejected, and
`value[var] = vals[i]` *reassigns* it.

The guard in question is not in `vertex_index.py`. It is at the call site:
`was_bound = var in value` then `if vx is not None and not was_bound:
vx.bind(var)`, inside `retry()` in `assign.py` (`assign.py:1115-1117` when
written; search for `was_bound`).

`VertexIndex` correctly **skips** on a reassignment, because it counts only
free-vs-bound and that does not change. `ClauseIndex` counts *agree vs
contra*, which **does** change. Skipping is silently wrong here. The hook
needs a genuine `rebind(var, old, new)` that decrements the old value's
contribution and increments the new one.

Same trap, opposite fix. Copying the working guard is how this gets written
wrong.

### Trap 2: clauses are born conflicting

At `nogoods.append(clause)` (`assign.py:1214`) every variable in the clause
is bound and agrees, so the clause enters with `n_agree == k`,
`n_contra == 0` -- the conflicting state. `add_clause` must compute its
counters against the live `value`, never assume a fresh state.

### Trap 3: the probe must not mutate search state

`feasible` -> `violation` reads `value`. The probe must set a value, test,
and remove it under `try/finally`, and must **not** touch the live
`VertexIndex`, or it corrupts the index that makes the run affordable. The
verify mode asserts `value` and every `VertexIndex` counter are unchanged
across each probe.

---

## 7. Wiring

Following the established debug-channel pattern exactly
(`compile.py:120-129`, `compile.py:404-409`):

* `assign()` gains `clause_prop: dict | None = None` and
  `clause_prop_verify: bool = False`
* `compile_tree()` threads both, joining `debug_search`,
  `debug_clause_sizes`, `vertex_index`, `vertex_index_verify`,
  `core_extraction`
* both inert when unset -- an arm that does not ask for the instrument pays
  nothing
* `compile_tree`'s `except (ValueError, RuntimeError, KeyError)` is **not**
  widened
* clause sizes are read from the existing `debug_clause_sizes`, not
  re-derived

No production behaviour changes.

---

## 8. Run matrix

### 8.1 The arms

**Primary.** Dense `lizard`, `assign_budget=500_000`, `vertex_index=True`,
fixture
`../evidence/2026-09-08-vlm-tree-authoring/data/rule6_serve.json`.
Two arms: `core_extraction=False` and `core_extraction=True`. Like-for-like
with `../evidence/2026-09-27-core-in-loop/`, whose figures are the control.

`vertex_index=True` is used because dense `lizard` measured **2.449x** wall
and **2.452x** assign with identity byte-identical 8/8, so the search path is
the same and the measurements are unaffected
(`../evidence/2026-09-29-vertex-index/timing.json`).

**Correction, 2026-10-01 (measured).** That **2.449x** was measured at
`assign_budget=20_000` and **does not extrapolate to 500,000 nodes.** The real
run read arm A **209.2 s** and arm B **68.2 s** against the uninstrumented
control's 1,052.0 s and 954.9 s — **5.03x** and **14.00x** — and the arms'
ordering flipped: the control's arms were near-equal (1052.0/954.9 = 1.10)
while the measured ratio is 209.2/68.2 = **3.07**. Plausibly arm A's 113
clauses of median width 202 make its `hits_nogood` scan and counter
maintenance far heavier than arm B's three narrow ones, which is a
500,000-node effect a 20,000-node run barely sees. **No figure is affected** —
identity passed on both arms, so the search path is pinned and only time per
node changed — but any future plan budgeting wall clock from the 2.449x will
under-predict: the realised speedups exceed it by 5.03/2.449 = **2.05x** on arm
A and 14.00/2.449 = **5.72x** on arm B. See
`../evidence/2026-09-30-clause-propagation/README.md` §9(a).

**Breadth.** Arm A only, dense, `assign_budget=50_000`, on the four other
subjects that reach `assign`: `frog`, `horse`, `bird`, `guinea_pig`.
`octopus` and `dog` are excluded although they too reach `assign` in dense:
neither completed the dense labelling audit
(`../evidence/2026-09-24-dense-pleats/dense_labelling.json` carries no
`dense_mv` for either), so there is no dense control to compare against.
Every
headline is a per-node rate, so the smaller budget is comparable, with one
stated direction of bias: **clause availability grows with nodes, so 50,000
understates it**, which makes a null breadth result weaker evidence than a
positive one.

A lizard-only headline would repeat the vertex-index slice's own error, where
a ceiling measured on `lizard` was published as the slice's cap and had to be
corrected.

### 8.2 Identity gate, checked before any figure is quoted

| arm | must reproduce |
|---|---|
| A | `rejections == 113` and `AssignFail(kind='budget', site=500000)` |
| B | `rejections == 3` and clause-size multiset `{5, 8, 8}` |

If either misses, the run is contaminated: the README reports the mismatch
instead of a verdict. This is `core-in-loop` section 7.3's discipline -- a
guard that passes is what licenses claiming a row.

This gate also supplies the 500,000-node identity evidence the vertex-index
slice left open when it declined to flip `vertex_index`'s default (its
identity run was at `assign_budget=20_000`). **It does not flip that
default**; it stops owing one of the missing points.

### 8.3 Cost cap

**1,800 s per arm.** On expiry the arm truncates and records
`truncated: true` with the node count reached; all rates stay valid over the
nodes actually executed. Unbounded runs are why the pleat-filter halt table
still has no committed script.

---

## 9. Testing

### 9.1 Mutation-verified unit tests

Last slice, deleting the MRV heuristic itself left 13 of 13 tests passing.
Each mutation below must be demonstrated **red**, and the demonstration
recorded:

| # | mutation | what it breaks |
|---|---|---|
| 1 | drop the `n_agree` increment in `bind` | unit detection |
| 2 | never increment `n_contra` | dead clauses counted as live |
| 3 | make `rebind` a skip (trap 1) | counter drift on the CEGAR path |
| 4 | `add_clause` counts against an empty state (trap 2) | born-conflicting clause read as live |
| 5 | unit test `n_agree == size` instead of `size - 1` | conflicting counted as unit |
| 6 | probe only the first remaining value of a 3-valued variable | `dead_node_fraction` inflated |
| 7 | probe leaves `value[var]` set (trap 3) | search state corrupted |

Each mutation must be asserted to apply exactly once before the suite is run,
because four mutation checks silently failed to apply during the last slice
(a `perl` pattern that matched a comment, a no-op parameter addition, a wrong
indent, and one relayed unverified).

### 9.2 Integration gate

`clause_prop_verify=True` on dense `lizard` at `assign_budget=20_000`:
recompute every clause's `n_agree` / `n_contra` from scratch against `value`
at every node and assert equality. On mismatch raise `ClauseIndexError`
naming the clause id, the variable, and both counter values, in
`VertexIndex`'s message style
(`n_free[(4, 7)] = 0 but free_vars_at returns 1 ([79])`).

### 9.3 Standing regression gate

The named box-pleat test files that reach `assign` must stay green. Name the
files explicitly and run them in full -- never a `-k` filtered subset, and
never `pytest tests/` (5,167 tests, over 3 hours). `--timeout` is
unavailable: the venv has no `pytest-timeout` and passing it exits 4.

---

## 10. Deliverable

`docs/superpowers/evidence/2026-09-30-clause-propagation/`

* `probe.py` -- the runner
* `probe.json` -- all arms' records, including **date, commit and exit
  status**. `core-in-loop`'s README states that a successor script should
  record these in the artifact rather than in prose; this is that successor.
* `README.md` -- the band reached, every figure read back from `probe.json`
  after the process exits (never transcribed from a watched log), with an
  explicit "what this does NOT establish" section.

---

## 11. Out of scope

* Wiring propagation into `retry()`. Gated on the `>= 0.50` band, and even
  then the band justifies a follow-on spec, not the wiring.
* Fixpoint propagation. One cascade step only, so every figure is a lower
  bound.
* The local-laws arm -- measuring where `feasible` was refutation-only but a
  value was in fact forced. A larger population (thousands of interior
  vertices against at most 113 clauses) and a likelier positive, but a
  separate instrument.
* Flipping `vertex_index`'s default.
* Any change to `layer_order.py`. `mv_symmetrize` on the serve path shares
  it.

---

## 12. What this instrument cannot establish

* **It cannot show that dense converges, or that it cannot.** The arms end on
  a node budget, which is a timeout, not a decision. The withdrawal recorded
  at `../specs/2026-09-24-dense-pleats-design.md:510` stands: dense "does not
  converge within 113 candidates and a 500,000-node budget -- **not that it
  cannot**."
* **It cannot bound the saving from propagation.** `dead_node_fraction` is a
  lower bound on nodes spent inside provably-dead regions. It is not a
  predicted speedup: a real propagator would change the search path, so the
  node count it would actually reach is not derivable from this measurement.
* **A null breadth result is weak.** The 50,000-node breadth budget
  understates clause availability by construction (section 8.1).
* **It says nothing about the eight subjects that never reach `emit`.** Six
  stop at `contours` (`cat`, `elephant`, `bat`, `dolphin`, `scorpion`,
  `ant`), `crab` stops at `tree`, and `rabbit` stops at `assign` -- so only
  `rabbit` fails in the stage this instrument watches, and it is in neither
  the primary nor the breadth arm. Counted from
  `../evidence/2026-09-20-box-pleat/results.json`: 9 of 17 subjects read
  `flat_fold_ok: True`, 8 non-emitting.
