# No-good clause indexing in `assign()` (follow-on from dense pleats)

**Status: WITHDRAWN 2026-09-26, before implementation, by the measurement it
should have taken first.** Approved earlier the same day on a cost
decomposition that was wrong. Nothing was built. The design below is kept
because the mechanism is sound and correctly described -- if a future change
makes the no-good scan matter, this is the design to use -- but **its premise is
refuted and it must not be implemented on the strength of section 1.**

## 0. Why this is withdrawn

`evidence/2026-09-26-nogood-indexing/where_the_time_goes.py` instrumented
production's own `hits_nogood` (patching `assign.py` in memory, asserting the
diff touched only that function's body) and measured dense `lizard` at the same
500,000-node budget:

| component | seconds | share of total |
|---|---|---|
| **`hits_nogood` (what this spec optimises)** | **11.88** | **1.28%** |
| `global_check` (the layer filter) | 178.15 | 19.15% |
| **remainder (the local CSP search itself)** | **740.16** | **79.57%** |
| total | 930.19 | 100% |

`hits_nogood` was called 500,831 times -- once per search node, as section 1
claimed -- at 23.7 us each. **The share is 1.28%, and that is an UPPER bound**
(the timer's own two `perf_counter` calls are counted inside it). Extrapolating
the scan's linear growth to the 5M run's 584 clauses puts it near 7% there, so
even at the largest measured scale indexing buys at most ~1.07x.

**Section 1's apportionment was wrong in three ways, all in the direction that
favoured building this.**

1. **The layer-check constant.** Section 1 used 6.4 s/candidate, taken from the
   dense-pleats spec section 6. That figure sums one per-candidate cost with two
   ONE-TIME costs: `constraint_graph` is cached (`compile.py:292`) and `certify`
   runs once after `assign` returns (`compile.py:347`). **Measured per-candidate
   layer cost: 1.577 s.**
2. **The per-clause cost.** The fitted model used 1.7 us per clause per call.
   Measured: 23.7 us per call across ~113 clauses, i.e. **~0.21 us per clause**,
   eight times smaller. *(Note added 2026-09-27: that divides by the run's FINAL
   clause count. The store grows from 0 to 113 over the run, so the average number
   of clauses present per call is roughly half the final count — about 57 — and the
   per-clause cost is correspondingly about 2x, ~0.42 us. An earlier version of
   this note said the correction "favours this withdrawal"; that was BACKWARDS.
   Point 2 rebuts section 1 by making the measured per-clause cost far smaller
   than the model's 1.7 us, so doubling it to ~0.42 us -- 4x smaller rather than
   8x -- WEAKENS this point. The conclusion still needs no recomputation, but for
   a different reason: the withdrawal rests on the DIRECT measurements in section
   0 point 3 (`hits_nogood` is 1.28% of runtime, and per-node cost is flat at
   1,668 vs 1,773 us), not on point 2's ratio. An error that flattered the
   conclusion is exactly the kind to recheck rather than wave through.)*
3. **The growth story.** Section 1 read a 4.63x rise in per-node cost against a
   5.17x rise in clause count and called the near-proportionality "the signature
   of the linear scan". **Per-node cost is in fact essentially FLAT** -- 1,668
   us/node on the 500k run versus 1,773 us/node on the 5M run, a 1.06x change.
   Nodes per candidate grew 1.93x and seconds per candidate 2.06x; the ratio of
   those is 1.07x, so **the entire per-candidate slowdown is more nodes, not
   slower nodes.**

**What the slowdown actually is, and why it is not a defect.** As clauses
accumulate the search must backtrack further and re-descend more, so it spends
more nodes per candidate. That is a learning search behaving correctly, not a
performance bug, and no indexing scheme removes it.

**Where the time really goes: the local CSP search, at 79.57%.** That reorders
the remaining levers, and the reordering is the useful output of this withdrawal:

* **COrigami F.3 deterministic ridge assignment** attacks the 79.57% directly by
  removing ridges from the CSP, leaving only hinges combinatorial as the paper
  intends. **Now the clearly best-supported lever, on measurement rather than
  inference.** *(Superseded 2026-09-27: `../evidence/2026-09-27-f3-rules/` found
  F.3 **degenerate** on our geometry — one of its three rules is already
  implemented by the mirror merge, one is inert, and the third reaches roughly
  5-10% of the CSP — and `../evidence/2026-09-27-nogood-core/` then took the
  best-supported slot.)*
* **Minimal unsat cores** attack the candidate count, supported by the
  large-budget run's reading 2 (the clause never tightens).
* **No-good indexing** attacks 1.28%. Dead.

Everything below is the design as approved, retained for reference only.

---

**Original status:** design approved 2026-09-26. Additive to
`2026-09-24-dense-pleats-design.md`, whose section 6.3.1 reading 3 is the
measurement that motivated it.

**Goal.** Replace `assign()`'s unindexed linear scan of the no-good store with a
one-watch index, so that the cost of checking stored clauses stops growing with
the number of clauses stored. **Semantics-preserving: the search visits the same
tree in the same order and emits the same labels, verified byte-for-byte on all
eight subjects.**

---

## 1. The measurement this starts from

From the large-budget run (`evidence/2026-09-24-dense-pleats/nogood-lizard-largebudget.json`,
`partial: false`), dense `lizard` at a 5,000,000-node budget refused 584
candidates in 8,865.1 s. Comparing against the 500,000-node run:

| | 500k | 5M | ratio |
|---|---|---|---|
| candidates refused | 113 | 584 | 5.17x |
| nodes per candidate | 4,424.8 | 8,561.6 | 1.93x |
| seconds per candidate | 7.38 | 15.18 | 2.06x |

**The cause is `assign.py:926`:**

```python
def hits_nogood() -> bool:
    return any(all(value.get(var) == val for var, val in g.items())
               for g in nogoods)
```

`nogoods` is a plain list, scanned linearly, and `hits_nogood()` is called from
`retry()` on every value assignment -- so at least once per search node. Its
cost therefore grows with the number of stored clauses.

**The fit.** Separating the measured ~6.4 s/candidate layer check *(refuted — see
§0: the measured per-candidate layer cost is 1.577 s)* from search
time gives a per-node cost of 222 us at 113 clauses and 1,026 us at 584. A
linear model `per_node ~= 30 us + 1.7 us * clauses` reproduces both points, and
`1.7 us` is a plausible CPython cost for constructing the inner generator and
calling `all()` once per clause. Under that model the scan is **~86% of search
time at 113 clauses and ~97% at 584**.

**Robustness.** Per-node cost grows under every internally consistent value of
the layer-check constant: 2.21x if the layer check is 5.0 s/candidate, 4.63x at
the measured 6.4 s *(refuted — see §0: 1.577 s)*, 11.11x at 7.0 s. The constant
cannot exceed
834.0 / 113 = 7.38 s/candidate without making the 500k run's search time
negative. **The direction of the conclusion does not depend on the assumption;
only its magnitude does.**

## 2. Prior art (CLAUDE.md section 0)

**External, read 2026-09-26.**

* **Katsirelos & Bacchus, *Generalized NoGoods in CSPs* (AAAI 2005).** Adapts
  SAT's watched-literal structure to CSP nogoods -- the same object this spec
  indexes. **Adopted:** the watched-literal structure over a nogood store.
  **Rejected for now:** their generalized nogoods (learning stronger nogoods
  from global constraints); that changes what is learned, not how it is
  indexed, and is a different spec.
* **Katsirelos & Bacchus, *Unrestricted Nogood Recording in CSP Search*
  (CP 2003).** Generalizes SAT clause recording to CSP search. Context for why
  nogood recording in a CSP is the same problem as clause learning in SAT.
* **Moskewicz, Madigan, Zhao, Zhang & Malik, *Chaff: Engineering an Efficient
  SAT Solver* (DAC 2001).** Origin of two-watched-literals. **Partially
  adopted:** one watch, not two -- see section 3.
* **Schiex & Verfaillie, *Nogood recording for static and dynamic constraint
  satisfaction problems* (IJAIT 3(2), 1994).** Origin of nogood recording.
  Context only.

**In-repo, checked 2026-09-26.** No precedent to match and nothing to reuse:
`layer_certify.decide` re-runs `layer_order.propagate` from scratch at every
node rather than maintaining any index, and no module under `mcp_harness`
implements watched literals (the one grep hit, `probe_fish_order_variants.py`,
uses the English word). This is the project's first clause index.

## 3. Scope: detection only. Propagation is a separate spec.

**Owner ruling, 2026-09-26.**

SAT watches **two** literals because it must detect "all but one false" in order
to *propagate* a unit. This spec needs only "all matched" in order to *detect* a
hit, and **one watch is sufficient for that**.

The second watch would buy real pruning -- when a nogood has exactly one
unmatched variable, that value can be eliminated immediately -- and the dense
pleats work established that pruning, not budget, is what this problem needs. It
is nonetheless **deliberately out of scope here**, for a reason specific to this
codebase:

**`compile_tree` always passes `global_check=_check`, so the SPARSE path runs the
same CEGAR loop** and accumulates 4-21 nogoods on the subjects that converge.
Propagation would change which candidate the sparse search reaches first, change
the emitted labels, and **break the all-8 byte-identity guarantee** that
`2026-09-24-dense-pleats-design.md` section 9 makes load-bearing. Gating
propagation to `dense=True` would avoid that at the cost of two different search
semantics inside one function, and would leave the propagating path with no
byte-identity baseline to verify against.

**So: ship the byte-identical index first.** It is a prerequisite refactor for
propagation either way, and it lets the semantic change be measured on its own
later, against a known-good indexed baseline instead of against an unindexed
one.

## 4. Architecture

One new module, `mcp_harness/box_pleat/nogood_store.py`, holding one class. No
other production file changes except the wiring in `assign()` (section 5).

**Why its own module rather than closures in `assign()`.** `assign()` is 545
lines (488-1032) in a 1,032-line file -- the largest function in the package --
and it carries the branch's whole review history of 2 Criticals and 1 Important.
The index maintains an invariant that is cheap to test directly against a
brute-force oracle and nearly untestable through a 545-line CSP, so the testable
boundary is worth a file.

### 4.1 The invariant

**Every stored clause is either in `matching` -- all of its entries equal the
current assignment -- or holds a watch entry `(var, val)` for which
`value.get(var) != val`.**

`hits()` is then exactly `bool(matching)`.

Two facts make one watch sufficient, and both must hold for the index to be
sound:

1. **A clause can only become fully-matching when its watched entry starts
   matching.** Its watch `(w_var, w_val)` currently does not match. Assigning
   some other variable cannot change `value.get(w_var)`. Assigning `w_var` to a
   value other than `w_val` leaves it non-matching. So the only transition into
   `matching` is an assignment of exactly `(w_var, w_val)` -- which is the event
   the index is keyed on.
2. **Un-assigning can only reduce matches, never create them.** So a watch that
   does not match stays valid across every backtrack, and the store needs **no
   trail and no backtrack bookkeeping**. (This is the property the two-watch
   propagating version would lose.)

**What each hook must therefore touch, stated so it cannot be read two ways:**

* `on_assign(var, val)` examines **only** `_index[(var, val)]`. It never needs to
  inspect `_matching`: a clause in `_matching` has every one of its variables
  already assigned, so an assignment of a previously-unassigned variable cannot
  break it, and the in-place *overwrite* case is handled by the preceding
  `on_unassign` that section 5 requires at line 937.
* `on_unassign(var)` examines **only** `_matching`. Watched clauses need no
  action, by fact 2: their watches do not match and un-assigning cannot make
  them match. For each clause in `_matching` that no longer fully matches, it
  acquires a watch and leaves the set.
* Neither hook ever rescans the whole store. That is the entire point.

### 4.2 Interface

```python
class NogoodStore:
    def __init__(self, value: dict): ...   # reads `value`, never mutates it
    def __len__(self) -> int                # replaces `if nogoods:`
    def add(self, clause: dict) -> None
    def hits(self) -> bool                  # O(1)
    def on_assign(self, var, val) -> None
    def on_unassign(self, var) -> None
```

State: `_clauses: list[dict]`, `_matching: set[int]`,
`_watch: list[tuple | None]` (per clause, its watched `(var, val)` or `None`
while in `_matching`), and `_index: dict[tuple, set[int]]` mapping a watched
`(var, val)` to the clauses watching it.

**`add` enters the clause directly into `_matching`.** The clause is built from
the current complete candidate (`assign.py:984` reads `value[...]` for every
key), so every entry matches at the moment of insertion and there is no
non-matching entry available to watch. It acquires a watch on the first mutation
that breaks it. A design that instead demanded a non-matching watch at insertion
would have no valid one to choose, which is why this case is stated explicitly
rather than left to the implementer.

**`on_unassign` must be idempotent** -- `assign.py:946` uses
`value.pop(var, None)`, which may be a no-op.

**Ownership.** The store reads `value` and never writes it; `assign()` remains
the only writer. One-way dependency, so the store can be constructed over a
plain dict in tests.

## 5. Data flow: the four hook sites

Every mutation of `value` in `assign()` is inside `retry()`, and there are only
three, plus the one insertion point. This is what makes the change small.

| line | current | becomes |
|---|---|---|
| 937 | `value[var] = vals[i]` | `on_unassign(var)` **then** `on_assign(var, vals[i])` |
| 941 | `del value[var]` | `on_unassign(var)` |
| 946 | `value.pop(frames[-1][0], None)` | `on_unassign` on that same var, read **after** the frame pop |
| 1008 | `nogoods.append(clause)` | `store.add(clause)` |
| 939 | `hits_nogood()` | `store.hits()` |
| 1023 | `if nogoods:` | `if len(store):` |

**Line 937 requires unassign-then-assign.** The write can *overwrite* a previous
value for the same variable when a frame advances to its next value. That
un-matches every `(var, old)` entry and matches every `(var, new)` one, so
treating it as a bare assignment would leave clauses watching `(var, old)`
wrongly indexed.

**Line 946 unassigns the PARENT frame's variable**, not the popped frame's: the
code pops the exhausted frame first, then clears `value` for the new deepest
frame so that frame can advance. The hook must read `frames[-1][0]` after the
pop, exactly as the current line does.

**`feasible()` short-circuits before `hits()` at line 939.** With the index,
`on_assign` has already run by then, so the store is consistent whichever way
the `and` resolves; line 941's `on_unassign` restores it.

## 6. Expected gain, and why the cheap measurement will not show it

Under section 1's model, removing the per-clause scan should take search time
from 5,127 s to a few hundred seconds on the 5M run, i.e. **8,865 s to roughly
4,000-4,300 s (~2.1x overall)**. `hits()` becomes O(1); the remaining
per-candidate floor is the ~6.4 s layer check *(refuted — see §0: the measured
per-candidate layer cost is 1.577 s)*, which this change cannot touch.

**A 500k A/B would show only ~1.1x and read as noise.** Search is 110.8 s of
that run's 834 s, so even eliminating it entirely moves the total by ~13%. The
gain is concentrated at high clause counts, so **the 5M re-run is the
measurement** (owner ruling, 2026-09-26). Reporting a 500k A/B as the result
would be reporting a number too small to distinguish from run-to-run variance.

**This change does not close the dense gap and must not be described as
doing so.** It makes a large budget deliver the candidates it pays for. Section
6.3.1 of the dense-pleats spec stands: convergence needs harder pruning or a
smaller search space.

## 7. Testing

* **Property test against a brute-force oracle -- the real correctness
  argument.** Random clause sets over a small variable pool, then random
  sequences of assign / unassign / overwrite. After **every** step, assert
  `store.hits()` equals
  `any(all(value.get(v) == x for v, x in g.items()) for g in clauses)` computed
  directly from the same `value`. Sequences must include: overwriting a variable
  in place, un-assigning a variable absent from `value`, adding a clause while
  other clauses are watched, and adding two clauses that share variables.
* **Invariant assertion.** After every step of the same sequences, every clause
  is in `_matching` or holds a watch whose entry does not match. Asserted
  directly against the store's internals, since this is the property section 4.1
  claims and the oracle test alone would pass even if the invariant were
  maintained by accident.
* **Non-vacuity, mandatory.** Both tests above assert that the generated
  sequences actually produced at least one `hits() == True` state and at least
  one watch migration. PR #193 shipped two tests reading `0 == 0` against
  fixtures that generated none of the thing under test, and the dense-pleats
  wave shipped a probe whose identity function silently collided; a count
  assertion here without a non-vacuity guard would repeat both.
* **Byte-identity on all 8 subjects -- the production gate.** `git archive` the
  branch base into a temp tree (never move HEAD, never `git stash`), compile
  `starfish`, `bird`, `lizard`, `horse`, `octopus`, `frog`, `guinea_pig`, `dog`
  from both sides, compare sha256 over the emitted dict. Method and expected
  digests: `evidence/2026-09-24-dense-pleats/README.md` section 2.
* **Existing suites.** `test_box_pleat_assign.py` and
  `test_box_pleat_layers.py` must stay green. Never run `pytest tests/` (5,167
  tests, over 3 hours). Use `../.venv/bin/python3` from `mcp_harness`; that venv
  has no `pytest-timeout`, so never pass `--timeout`.
* **Performance.** Re-run
  `nogood_diagnostic.py lizard <out> 18000 5000000 100000` and report elapsed at
  the same 584 candidates. **The candidate count and every clause-size statistic
  must be unchanged** -- if they move, the change was not semantics-preserving
  and the byte-identity gate missed it.

## 8. Risks

1. **The index is a stateful invariant inside a hot search loop.** A bug that
   makes `hits()` return `False` when a clause matches does not crash -- it
   silently lets the search re-offer a rejected candidate, which would surface
   as a *changed candidate count*, not as an error. This is why section 7's
   performance check treats an unchanged candidate count as a correctness
   assertion, not a curiosity.
2. **`on_assign` now does work on every node even when `feasible()` fails**,
   where `hits_nogood()` was previously skipped by short-circuiting. The work is
   bounded by the number of clauses watching exactly `(var, val)`, normally few,
   but it is a real new cost on the cheapest path. If the 5M re-run shows less
   than the predicted gain, this is the first thing to measure.
3. **Byte-identity is necessary but not sufficient.** It proves the eight
   subjects reach the same labelling; it does not prove the index is correct on
   search paths those subjects never take. That is what the property test is
   for, and neither gate substitutes for the other.
4. **The predicted 2.1x rests on a fitted two-point model.** Two points fit a
   two-parameter line exactly, so the model is unfalsified rather than
   confirmed. The 5M re-run is what tests it, and a materially different result
   should be reported as such rather than explained away.

## 9. Out of scope

* **Nogood propagation** (the second watch) -- section 3; its own spec.
* **Minimal unsat cores** -- the other follow-on from dense pleats; own spec.
* **F.3 deterministic ridge assignment** -- own spec.
* **`layer_order.py`** -- untouched across the dense-pleats branch and stays so.
* **The serve path.** `grep -c box_pleat mcp_harness/server.py` is 0 and stays 0.

## 10. Evidence

`docs/superpowers/evidence/2026-09-26-nogood-indexing/`, carrying: the all-8
byte-identity table with digests, the 5M re-run artifact beside the pre-change
one for direct comparison, and the candidate-count/clause-size equality check
from section 7. A negative or smaller-than-predicted result is recorded with the
same prominence as a positive one.
