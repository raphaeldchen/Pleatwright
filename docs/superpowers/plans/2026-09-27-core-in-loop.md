# Core Extraction in the CEGAR Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Narrow the CEGAR loop's no-good clause from its dependency cone to its irreducible cause behind a flag, then run one A/B to answer whether dense layer-ordering converges.

**Architecture:** A new pure module `box_pleat/cores.py` wraps QuickXplain around the oracle `layers.propagate(graph, labels, only=S)`. One branch in `compile._check` hands `piece_keys` a witness whose `creases` are the core instead of the cone. `assign.py` is not touched: it still receives a `(keys, witness)` pair and cannot tell the difference.

**Tech Stack:** Python 3.14, pytest 9. No new dependencies.

Spec: `docs/superpowers/specs/2026-09-27-core-in-loop-design.md`.

## Global Constraints

- **Run every command from this worktree.** Do NOT `cd` to the original repository root.
- **Use `../.venv/bin/python3` from `mcp_harness`.** Bare `python3` lacks `skeletor`, which `tests/conftest.py` imports, and dies at collection.
- **That venv has no `pytest-timeout`. NEVER pass `--timeout`.**
- **NEVER run `pytest tests/`** — 5,167 tests, over 3 hours. Always name files.
- **Run the FULL named test files, never a `-k` filtered subset.** A previous implementer on this branch ran filtered subsets and shipped a red file; the fix cost three review rounds.
- **Never use bare `git stash` / `git stash pop`.** The stash stack is shared with the main checkout and other worktrees. Use a temporary WIP commit instead.
- **End every commit message with:** `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`
- **Do NOT modify `layer_order.py`.** Untouched across this whole line of work; `mv_symmetrize` on the serve path shares it.
- **Do NOT modify `assign.py`.** Spec §3: the CEGAR loop, its DFS and its clause comprehension stay exactly as they are.
- **`grep -c box_pleat mcp_harness/server.py` must stay 0.**
- **`core_extraction=False` must be behaviourally identical to today.** No emitted fold may change.
- **Every count assertion is paired with a non-vacuity assertion or a fixture guard.**
- **A core is TESTED, never assumed.** A too-small clause is unsound: it forbids assignments that are not contradictory and can make the search report unsat when a solution exists.
- **Report the A/B verdict in whichever direction the data falls.** Spec §7.2's four rows are fixed before the data; §7.3's clause-size guard decides whether ANY row may be claimed.

## File Structure

| file | responsibility |
|---|---|
| `mcp_harness/box_pleat/cores.py` (new) | `quickxplain`, `_core` (algorithm + the empty-core guard), `shrink` (the layers oracle), `CoreExtractionError`. Pure; imports only `layers`. |
| `mcp_harness/tests/test_box_pleat_cores.py` (new) | Unit tests for all of the above, against a synthetic oracle and the committed `lizard-v1.fold`. Fast — no `compile_tree`. |
| `mcp_harness/box_pleat/compile.py` (modify) | Three flags on `compile_tree`; one branch in `_check`; `debug_clause_sizes` passthrough. |
| `mcp_harness/tests/test_box_pleat_core_in_loop.py` (new) | Integration: inertness when nothing rejects, and soundness on a sparse subject that does reject. |
| `docs/superpowers/evidence/2026-09-27-core-in-loop/ab.py` (new) | The two-arm experiment. |
| `docs/superpowers/evidence/2026-09-27-core-in-loop/README.md` (new) | The verdict against spec §7.2, with §7.3's guard stated. |

---

### Task 1: `cores.py` — QuickXplain over the layers oracle

**Files:**
- Create: `mcp_harness/box_pleat/cores.py`
- Create: `mcp_harness/tests/test_box_pleat_cores.py`

**Interfaces:**
- Consumes: `layers.propagate(graph, labels, *, only=None) -> Witness | None`, which already exists on this branch (commit `9309c5d`). `only=None` seeds every slot; a `frozenset` of FOLD edge keys seeds only those; extra keys that are not slot edges are ignored.
- Produces, for Task 2:
  - `cores.shrink(graph, labels, creases, *, counter=None) -> frozenset`
  - `cores.CoreExtractionError` (subclasses `Exception`, deliberately NOT `ValueError`/`RuntimeError`/`KeyError`)
  - `cores.quickxplain(candidates, holds, counter=None) -> frozenset` and `cores._core(candidates, holds, counter=None) -> frozenset` (used by tests, not by Task 2)

- [ ] **Step 1: Write the failing tests**

Create `mcp_harness/tests/test_box_pleat_cores.py`:

```python
"""box_pleat/cores.py: a contradiction's dependency CONE -> its irreducible CAUSE."""
import json

import pytest

import flat_fold
from box_pleat import cores, layers
from test_box_pleat_layers import LIZARD_V1, LIZARD_V1_WITNESS_CREASES


def _v1_lizard():
    """The committed contradicting fixture, not a compiled subject.

    `compile_tree("lizard")` no longer contradicts -- the shipped layers stage
    repairs it (`test_box_pleat_layers.py`'s
    `test_the_layers_stage_repairs_v1s_lizard_without_moving_a_crease`) -- so a
    compiled subject is not a stable source of a contradicting labelling. A
    committed file cannot drift.
    """
    with open(LIZARD_V1) as fh:
        ff = flat_fold.flat_fold(json.load(fh))
    graph = layers.constraint_graph(ff)
    labels = {k: a for _, _, k, a in ff.shared_edges if a in ("M", "V")}
    return graph, labels


def test_quickxplain_finds_the_exact_cause():
    """The algorithm IS the measurement: a wrong implementation would not fail
    loudly, it would return plausible small cores. A synthetic monotone oracle
    with a known 2-of-8 cause is the only way to check it against ground truth.
    """
    cause = {2, 4}
    calls = [0]
    got = cores.quickxplain(sorted([1, 2, 3, 4, 5, 6, 7, 8]),
                            lambda s: cause <= set(s), calls)
    assert got == frozenset(cause)
    # non-vacuity: a degenerate implementation that returned the whole input,
    # or one that short-circuited, cannot have searched in under 3 calls.
    assert calls[0] >= 3


def test_quickxplain_result_is_irreducible():
    """Irreducible means every element is load-bearing: drop any one and the
    property stops holding. This is the contract Task 2 relies on for
    soundness, so it is asserted directly rather than inferred from the size.
    """
    cause = {3, 7}
    holds = lambda s: cause <= set(s)
    core = cores.quickxplain(sorted(range(1, 12)), holds)
    assert holds(core)                      # non-vacuity: it holds at all
    assert len(core) > 1                    # non-vacuity: something to remove
    for c in core:
        assert not holds(core - {c}), c


def test_shrink_narrows_the_committed_v1_lizard_contradiction():
    """Measured 2026-09-27 on `tests/data/lizard-v1.fold`: the cone is 12 FOLD
    edges and the irreducible cause is 5, found in 23 oracle calls
    ([(2, 6), (5, 6), (10, 11), (15, 16), (16, 20)]).

    The size is asserted as a BOUND, not pinned: the contract is
    irreducibility, and a different split order would legitimately return a
    different irreducible core. But a core of 7+ out of a 12-edge cone would
    mean the split regressed, so the bound is tight enough to catch that.
    """
    graph, labels = _v1_lizard()
    blamed = layers.propagate(graph, labels).creases
    assert blamed == LIZARD_V1_WITNESS_CREASES   # fixture guard
    assert len(blamed) == 12                     # fixture guard

    calls = [0]
    core = cores.shrink(graph, labels, blamed, counter=calls)

    assert 1 <= len(core) <= 6, sorted(core)
    assert core < blamed, "shrink returned the whole cone"
    assert calls[0] > 0
    # the core alone forces the contradiction ...
    assert layers.propagate(graph, labels, only=core) is not None
    # ... and every crease in it is necessary
    for c in core:
        assert layers.propagate(graph, labels, only=core - {c}) is None, c


def test_shrink_ignores_the_input_order():
    """`shrink` sorts its candidates because QuickXplain's result depends on how
    it splits: an unordered input would return a different irreducible core run
    to run and make every reported figure unreproducible. Which core is found is
    not canonical; finding the same one again must be.

    This test is strongly non-vacuous, measured 2026-09-27 on this fixture: fed
    the REVERSED order, QuickXplain returns
    [(6, 7), (12, 13), (12, 16), (16, 17), (16, 21)] -- a core of the same size
    (5) that is COMPLETELY DISJOINT from the sorted order's
    [(2, 6), (5, 6), (10, 11), (15, 16), (16, 20)]. Both are genuine irreducible
    causes of the same contradiction and they share no element, so an
    implementation that dropped the sort would fail this test outright rather
    than pass by luck.
    """
    graph, labels = _v1_lizard()
    blamed = layers.propagate(graph, labels).creases
    assert len(blamed) > 1                       # non-vacuity: order can differ
    forward = cores.shrink(graph, labels, sorted(blamed))
    backward = cores.shrink(graph, labels, list(reversed(sorted(blamed))))
    assert forward == backward


def test_core_refuses_an_oracle_that_contradicts_on_the_empty_set():
    """An empty core makes `layers.piece_keys` return nothing, `assign`'s clause
    comprehension yield `{}`, and `assign` report
    `AssignFail("layer_bad_witness")` -- a wrong answer dressed as a verdict.
    `empty_contradicts` was False on 31 of 31 measured rejections, so this
    condition means the oracle is broken and every clause derived from it is
    invalid. A real fold cannot produce it, hence the synthetic oracle.
    """
    with pytest.raises(cores.CoreExtractionError):
        cores._core(sorted([1, 2, 3]), lambda s: True)
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -m pytest tests/test_box_pleat_cores.py -q
```

Expected: collection error — `ImportError: cannot import name 'cores' from 'box_pleat'`.

- [ ] **Step 3: Write the module**

Create `mcp_harness/box_pleat/cores.py`:

```python
"""Minimal unsat cores over a layer-order contradiction.

Spec: `docs/superpowers/specs/2026-09-27-core-in-loop-design.md`.

`layers.propagate` reports a contradiction whose `witness.creases` comes from
`layer_order`'s `exc.deps` -- the whole derivation chain, a dependency CONE
rather than a CUT. Measured over 31 real rejections
(`docs/superpowers/evidence/2026-09-27-nogood-core/`): the cone is a median of
172 FOLD edges / 109 solver variables while the irreducible cause is **5**
variables, and core size stays flat at 4-8 while cone size spans 6-245. So the
CEGAR loop has been forbidding one point in a 2^109 space where it could forbid
one in 2^5.

This module shrinks the cone to a cause, so the clause forbids every labelling
that shares the cause instead of the single point it was handed.

SOUNDNESS. The oracle certifies that seeding ONLY the core, at this candidate's
own labels, already contradicts. Any labelling agreeing with the candidate on
those creases therefore also contradicts, because `propagate(graph, labels,
only=core)` depends on no other label. The narrowed clause forbids strictly more
assignments and every one of them is genuinely unsatisfiable. `layer_order.
_propagate` is not confluent, and that does not threaten this: non-confluence
costs COMPLETENESS (a contradiction may be missed) rather than soundness (one
that IS reported is a real derivation from those seeds).

The danger direction is a core that is too SMALL, which would forbid
satisfiable assignments. QuickXplain cannot produce one: every candidate core is
tested by the oracle before it is returned.

Prior art: Junker, QuickXplain (AAAI 2004); formal treatment arXiv:2001.01835.
Minimizing learned clauses is standard CDCL practice (Soerensson & Biere, SAT
2009 -- in MiniSat since 2005). The bet that a stronger explanation repays its
extraction cost is lazy clause generation's, stated there as: it may be worth
spending more time on stronger propagation when learning amortizes the cost over
multiple uses (Ohrimenko, Stuckey & Codish).
"""
from __future__ import annotations

from . import layers


class CoreExtractionError(Exception):
    """Extraction produced an empty core, so the oracle is unsound here.

    Deliberately subclasses `Exception` and NOT `ValueError`/`RuntimeError`/
    `KeyError`: those three are what `compile_tree` catches around `assign`
    (`compile.py:313`), folding them into an indistinguishable
    `AssignFail("error", ...)`. This condition must never be mistaken for a
    normal refusal, so it propagates out of `compile_tree` uncaught -- matching
    that module's existing treatment of conditions that invalidate a run.
    """


def quickxplain(candidates, holds, counter=None) -> frozenset:
    """An IRREDUCIBLE subset of `candidates` for which `holds` stays true.

    `holds(frozenset)` must be MONOTONE: true for a set implies true for every
    superset. Seeding more slots only adds constraints, and a contradictory
    system stays contradictory under added constraints, so the layers oracle in
    `shrink` satisfies this.

    `counter`, when given, is a one-element list incremented once per oracle
    call. Junker's bound is `2k*log2(n/k)+2k` for a core of size k out of n
    candidates; 0 of 31 measured rejections exceeded it.

    Irreducible, not minimum: a smallest core is NP-hard and is not attempted,
    matching the greedy-vs-minimum ruling already taken for `interleave`'s
    odd-cycle release.

    Candidates are consumed in the order given -- `shrink` sorts them.
    """
    def oracle(s):
        if counter is not None:
            counter[0] += 1
        return holds(s)

    def qx(background, cand):
        if oracle(background):
            return frozenset()
        if len(cand) == 1:
            return frozenset(cand)
        k = len(cand) // 2
        c1, c2 = cand[:k], cand[k:]
        d1 = qx(background | set(c1), c2)
        d2 = qx(background | d1, c1)
        return d1 | d2

    return qx(frozenset(), list(candidates))


def _core(candidates, holds, counter=None) -> frozenset:
    """`quickxplain` plus the empty-core guard.

    Split out from `shrink` so the guard is testable against a synthetic oracle.
    A real fold cannot reach it -- `empty_contradicts` was False on 31 of 31
    measured rejections -- which is exactly why it must be tested some other
    way rather than left to a condition that never arises in practice.
    """
    cand = list(candidates)
    core = quickxplain(cand, holds, counter)
    if not core:
        raise CoreExtractionError(
            f"extraction returned an EMPTY core from {len(cand)} "
            f"candidates, which means the property already holds under an empty "
            f"seed set. An empty core yields an empty clause, which `assign` "
            f"reports as AssignFail('layer_bad_witness') -- a wrong answer "
            f"dressed as a verdict -- so the run is invalid rather than "
            f"merely unlucky. Measured empty_contradicts=False on 31 of 31 "
            f"rejections (docs/superpowers/evidence/2026-09-27-nogood-core/"
            f"core-sizes.json).")
    return core


def shrink(graph, labels, creases, *, counter=None) -> frozenset:
    """The creases in `creases` that ALONE force `graph` + `labels` to contradict.

    The oracle is `layers.propagate(graph, labels, only=S) is not None`.

    Candidates are `sorted(creases)`. QuickXplain's result depends on how it
    splits, so an unordered input returns a different irreducible core run to
    run and makes every reported figure unreproducible. Which core is found is
    not canonical; finding the same one again must be.

    Raises `CoreExtractionError` if the core comes back empty -- see `_core`.
    """
    def holds(s):
        return layers.propagate(graph, labels, only=frozenset(s)) is not None

    return _core(sorted(creases), holds, counter)
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -m pytest tests/test_box_pleat_cores.py -q
```

Expected: 5 passed, in a few seconds. `lizard-v1.fold` is a committed file, so nothing compiles.

- [ ] **Step 5: Confirm nothing else moved**

`cores.py` is new and imported by nothing yet, so the only risk is the shared import of `test_box_pleat_layers`'s constants. Run both files in full:

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -m pytest \
  tests/test_box_pleat_cores.py tests/test_box_pleat_layers.py -q
```

Expected: all pass. **`test_box_pleat_layers.py` takes ~15 minutes** — two of its tests compile dense subjects. That is expected; let it finish rather than killing it. Launch it in the background and poll if your tool has a shorter timeout.

**If any test fails, do NOT commit.** Report it verbatim. Do not call a failure "pre-existing" or "unrelated" without showing from the code why — that claim was made falsely on this branch once already and was wrong.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/box_pleat/cores.py mcp_harness/tests/test_box_pleat_cores.py
git commit -m "$(printf '%s\n' 'box_pleat: cores.shrink -- a contradictions cone narrowed to its cause' '' 'witness.creases comes from layer_orders exc.deps, the whole derivation chain:' 'a dependency CONE, not a cut. Measured over 31 real rejections, the cone is a' 'median 172 FOLD edges / 109 solver variables while the irreducible cause is 5' 'variables, and core size is FLAT at 4-8 while cone size spans 6-245.' '' 'QuickXplain (Junker, AAAI 2004) over the oracle layers.propagate(only=S), which' 'contradicts iff the creases in S alone are sufficient. Monotone, because seeding' 'more slots only adds constraints and a contradictory system stays contradictory' 'under added constraints.' '' 'Sound in the direction that matters: every candidate core is TESTED by the' 'oracle before it is returned, so a too-small core -- which would forbid' 'satisfiable assignments and could make the search report unsat when a solution' 'exists -- cannot be produced. Non-confluence in layer_order._propagate costs' 'completeness, not soundness.' '' 'The empty-core guard lives in _core so it can be tested against a synthetic' 'oracle: a real fold cannot reach it (empty_contradicts was False on 31 of 31' 'rejections), which is exactly why leaving it untested would be wrong. It raises' 'rather than returning, and CoreExtractionError deliberately does not subclass' 'the three exception types compile_tree catches around assign, so it cannot be' 'mistaken for a normal refusal.' '' 'Measured on the committed lizard-v1 fixture: cone 12 FOLD edges -> cause 5, in' '23 oracle calls. Size asserted as a bound, not pinned: the contract is' 'irreducibility, and a different split would legitimately find a different' 'irreducible core.' '' 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>')"
```

---

### Task 2: wire it into `compile._check` behind a flag

**Files:**
- Modify: `mcp_harness/box_pleat/compile.py` (imports at `:27`; `compile_tree` signature at `:118-121`; `_check`'s return at `:303-307`; the `assign` call at `:310-312`)
- Create: `mcp_harness/tests/test_box_pleat_core_in_loop.py`

**Interfaces:**
- Consumes from Task 1: `cores.shrink(graph, labels, creases, *, counter=None) -> frozenset`.
- Produces, for Task 3: `compile_tree(..., core_extraction: bool = False, debug_cores: list | None = None, debug_clause_sizes: list | None = None)`. `debug_cores` receives one `(blamed_creases, core_creases, oracle_calls, secs)` tuple per rejection; `debug_clause_sizes` is forwarded to `assign` and receives one clause size in solver variables per rejection.

- [ ] **Step 1: Write the failing tests**

Create `mcp_harness/tests/test_box_pleat_core_in_loop.py`:

```python
"""compile_tree(core_extraction=True): the CEGAR clause narrowed to its cause.

Sparse subjects only. A dense run is 15+ minutes and is the job of
`docs/superpowers/evidence/2026-09-27-core-in-loop/ab.py`, not of this suite.
"""
import json

from box_pleat.compile import compile_tree
from test_box_pleat_tree import RULE6


def _entry(subject):
    with open(RULE6) as fh:
        return next(e for e in json.load(fh) if e["subject"] == subject)


def test_extraction_is_inert_when_nothing_is_rejected():
    """`starfish` accepts candidate 1, so `_check` returns `None` and extraction
    never runs. This is the ONE subject/flag combination where byte-identity is
    a legitimate expectation -- see the next test for why it is not general.
    """
    e = _entry("starfish")
    off = compile_tree(e["requested"], e["pairs"])
    on = compile_tree(e["requested"], e["pairs"], core_extraction=True)
    assert off.stage_reached == "emit", off.failure
    assert off.layers_tried == 1, "starfish started rejecting -- test is vacuous"
    assert on.stage_reached == "emit", on.failure
    assert on.layers_tried == 1
    assert on.fold == off.fold


def test_extraction_narrows_the_clause_and_the_search_still_succeeds():
    """`lizard`'s sparse labelling contradicts, so extraction actually runs
    (measured 2026-09-27: `layers_tried` 9, i.e. 8 rejections then an accepting
    call, in ~6.5 s).

    Output is deliberately NOT asserted byte-identical. A narrower clause
    forbids strictly more, so the search legitimately takes a different path and
    may accept a different candidate. What must hold is that it still finds one
    and that one still CERTIFIES -- this is the test that a too-small clause has
    not made a satisfiable problem look unsatisfiable.
    """
    e = _entry("lizard")
    seen: list = []
    clauses: list = []
    res = compile_tree(e["requested"], e["pairs"], core_extraction=True,
                       debug_cores=seen, debug_clause_sizes=clauses)
    assert res.stage_reached == "emit", res.failure
    assert res.verdict is not None, "no verdict recorded"
    assert res.verdict.kind == "CERTIFIED", res.verdict
    assert seen, "extraction never ran -- lizard stopped rejecting?"
    assert len(seen) == len(clauses), (len(seen), len(clauses))
    for blamed, core, calls, secs in seen:
        assert 0 < core <= blamed, (blamed, core)
        assert calls > 0
        assert secs >= 0
    assert any(core < blamed for blamed, core, _, _ in seen), \
        "extraction ran on every rejection but narrowed none of them"


def test_debug_cores_stays_empty_when_extraction_is_off():
    """The flag gates the work, not just the reporting."""
    e = _entry("lizard")
    seen: list = []
    clauses: list = []
    res = compile_tree(e["requested"], e["pairs"],
                       debug_cores=seen, debug_clause_sizes=clauses)
    assert res.stage_reached == "emit", res.failure
    assert res.layers_tried > 1, "lizard stopped rejecting -- test is vacuous"
    assert clauses, "no clause was recorded, so nothing was rejected"
    assert seen == []
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -m pytest tests/test_box_pleat_core_in_loop.py -q
```

Expected: FAIL with `TypeError: compile_tree() got an unexpected keyword argument 'core_extraction'`.

- [ ] **Step 3: Add the import and the `replace` name**

In `mcp_harness/box_pleat/compile.py`, replace:

```python
from dataclasses import dataclass, field
```

with:

```python
from dataclasses import dataclass, field, replace
```

and replace:

```python
from . import layers as _layers
```

with:

```python
from . import cores
from . import layers as _layers
```

- [ ] **Step 4: Add the three parameters**

Replace `compile_tree`'s signature:

```python
def compile_tree(nodes, pairs, *, max_N=None, pack_budget=200_000,
                 assign_budget=500_000, layer_budget=200,
                 certify_budget=layer_certify.CERTIFY_BUDGET,
                 dense: bool = False) -> Result:
```

with:

```python
def compile_tree(nodes, pairs, *, max_N=None, pack_budget=200_000,
                 assign_budget=500_000, layer_budget=200,
                 certify_budget=layer_certify.CERTIFY_BUDGET,
                 dense: bool = False,
                 core_extraction: bool = False,
                 debug_cores: list | None = None,
                 debug_clause_sizes: list | None = None) -> Result:
```

Then add to `compile_tree`'s docstring, immediately after the existing paragraph that documents `dense`:

```python
    `core_extraction`, when `True`, narrows each rejection's no-good clause
    from its dependency CONE to its irreducible CAUSE before `assign` learns
    it (spec `2026-09-27-core-in-loop-design.md`). `witness.creases` comes
    from `layer_order`'s `exc.deps`, the whole derivation chain, so the
    clause records a median of 109 solver variables where the measured cause
    is 5. `False` -- the default, and what every production call site passes
    -- leaves `_check` byte-for-byte the function it was before this
    parameter existed.

    `debug_cores`, when not `None`, gets one
    `(blamed_creases, core_creases, oracle_calls, secs)` tuple appended per
    rejection, and stays empty when `core_extraction` is `False` because the
    flag gates the work rather than the reporting. `debug_clause_sizes` is
    forwarded to `assign`, whose identically-named parameter records one
    clause size in SOLVER VARIABLES per rejection -- the unit the spec's
    guard is stated in, and one `_check` cannot compute because the clause
    is built from `assign`'s own `var_of`/`idx`. Both are diagnostics;
    production callers leave them `None`.
```

- [ ] **Step 5: Add the extraction branch to `_check`**

In `_check`, replace:

```python
        w = _layers.propagate(graph_cell[0], labels)
        if w is None:
            return None
        return _layers.piece_keys(w, fold), w
```

with:

```python
        w = _layers.propagate(graph_cell[0], labels)
        if w is None:
            return None
        if not core_extraction:
            return _layers.piece_keys(w, fold), w
        calls = [0]
        t0 = time.perf_counter()
        core = cores.shrink(graph_cell[0], labels, w.creases, counter=calls)
        if debug_cores is not None:
            debug_cores.append((len(w.creases), len(core), calls[0],
                                round(time.perf_counter() - t0, 3)))
        # Only the KEYS narrow. The witness returned is the ORIGINAL `w`:
        # `assign` stores it in `AssignFail` payloads and `compile_tree`
        # surfaces it in `LayerFail`, and the full cone is the more
        # informative diagnostic (spec section 3). `piece_keys` reads only
        # `witness.creases`, and a core is a SUBSET of creases the unshrunk
        # path already resolves, so its edge validation cannot newly fire.
        return _layers.piece_keys(replace(w, creases=core), fold), w
```

`time` is already imported at `compile.py:26`.

- [ ] **Step 6: Forward `debug_clause_sizes` to `assign`**

Replace:

```python
        asg = assign(lay, ridges, boundary, cont, budget=assign_budget,
                     global_check=_check, layer_checks=layer_budget,
                     dense=dense)
```

with:

```python
        asg = assign(lay, ridges, boundary, cont, budget=assign_budget,
                     global_check=_check, layer_checks=layer_budget,
                     dense=dense, debug_clause_sizes=debug_clause_sizes)
```

`assign` already declares `debug_clause_sizes: list | None = None`
(`assign.py:531`, documented at `:604`, appended at `:1028`), so this adds an
argument and no mechanism.

- [ ] **Step 7: Run the new tests to verify they pass**

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -m pytest tests/test_box_pleat_core_in_loop.py -q
```

Expected: 3 passed in roughly 20-30 s (`starfish` compiles in ~0.1 s, `lizard` in ~6.5 s, and the file compiles `lizard` twice and `starfish` twice).

- [ ] **Step 8: Confirm the inertness invariant across the box-pleat suite**

`compile.py` is on every box-pleat test's path, so run the full files:

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -m pytest \
  tests/test_box_pleat_core_in_loop.py tests/test_box_pleat_cores.py \
  tests/test_box_pleat_e2e.py tests/test_box_pleat_assign.py \
  tests/test_box_pleat_layers.py -q
```

Expected: all pass. `test_box_pleat_e2e.py` carries
`test_already_consistent_subjects_emit_byte_identical_folds`, which is the
load-bearing byte-identity invariant for `core_extraction=False`.
**This run is long — `test_box_pleat_layers.py` alone is ~15 minutes and the e2e
file compiles several subjects.** Launch it in the background and poll; do not
kill it.

**If any test fails, do NOT commit.** Report it verbatim with the failing
assertion, and show from the code why before calling anything unrelated.

- [ ] **Step 9: Commit**

```bash
git add mcp_harness/box_pleat/compile.py mcp_harness/tests/test_box_pleat_core_in_loop.py
git commit -m "$(printf '%s\n' 'box_pleat: compile_tree(core_extraction=) narrows the no-good to its cause' '' 'The wiring point is ONE BRANCH in _check, not the CEGAR loop. _check already' 'owns the graph, the labels and the witness, and ended with piece_keys(w, fold),' 'w; assign consumes exactly that and builds its clause from the keys alone. So' 'narrowing means handing piece_keys a witness whose creases are the core, and' 'assign.py is not touched at all -- it still receives a (keys, witness) pair and' 'cannot tell the difference.' '' 'The witness returned stays the ORIGINAL cone: only the keys narrow. assign' 'stores the witness in AssignFail payloads and compile_tree surfaces it in' 'LayerFail, and the full cone is the better diagnostic.' '' 'core_extraction=False is the default, every existing caller keeps it, and the' 'branch leaves _check byte-for-byte what it was. Verified by the committed' 'byte-identity invariant in test_box_pleat_e2e.py.' '' 'NOT asserted byte-identical with the flag ON for a subject that rejects: a' 'narrower clause forbids strictly more, so the search legitimately takes a' 'different path. The test asserts the thing that must hold instead -- sparse' 'lizard still reaches emit and still CERTIFIES -- which is the check that a' 'too-small clause has not made a satisfiable problem look unsat.' '' 'debug_clause_sizes is forwarded to assign because the clause is built from' 'assigns own var_of/idx, which _check cannot see, so the specs clause-size guard' 'was otherwise unmeasurable from the compile path.' '' 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>')"
```

---

### Task 3: run the A/B and write the verdict

**Files:**
- Create: `docs/superpowers/evidence/2026-09-27-core-in-loop/ab.py`
- Create: `docs/superpowers/evidence/2026-09-27-core-in-loop/ab.json`
- Create: `docs/superpowers/evidence/2026-09-27-core-in-loop/README.md`

**Interfaces:**
- Consumes from Task 2: `compile_tree(..., dense=True, assign_budget=, core_extraction=, debug_cores=, debug_clause_sizes=)`.
- Produces: the evidence directory.

- [ ] **Step 1: Write the experiment script**

Create `docs/superpowers/evidence/2026-09-27-core-in-loop/ab.py`:

```python
"""A/B: does dense layer-ordering converge when the clause is its actual cause?

Spec: `../../specs/2026-09-27-core-in-loop-design.md` section 7.

ONE boolean changes between the arms. Arm A reproduces the committed baseline
(`../2026-09-24-dense-pleats/nogood-lizard.json`: 113 rejections, 834.0 s,
`AssignFail(kind='budget', site=500000)`, median clause 202 solver variables) on
THIS machine in THIS session, so the comparison is not against a quoted figure.

`lizard` is the subject because it is the only one whose loop yields many
rejections cheaply: `octopus` and `dog` do not finish dense labelling inside a
300 s cap at all, and the other subjects' first dense candidate produces a
2-crease blamed set with nothing to shrink.

WHAT THE NUMBERS CAN AND CANNOT SAY. The terminal outcome is the primary signal.
The rejection count is NOT: a run that exhausts its node budget consumes exactly
the budget, so nodes-per-rejection = budget / rejections IDENTICALLY, and the two
are one figure rather than two independent readings. Fewer rejections is the
EXPECTED signature of stronger clauses -- more of the space excluded a priori
means fewer distinct complete candidates -- but it is equally consistent with a
search wandering deeper, so it sizes the follow-on run and establishes nothing on
its own.

Extraction adds seconds per rejection BY CONSTRUCTION, so any wall-clock
comparison between the arms is confounded. Compare outcomes; report seconds as
the experiment's cost.

Run from mcp_harness:
  PYTHONPATH=. ../.venv/bin/python3 -u \\
      ../docs/superpowers/evidence/2026-09-27-core-in-loop/ab.py \\
      ../docs/superpowers/evidence/2026-09-27-core-in-loop/ab.json
"""
import json
import os
import statistics
import sys
import time

from box_pleat.compile import compile_tree

OUT = sys.argv[1]
RULE6 = os.path.join("..", "docs", "superpowers", "evidence",
                     "2026-09-08-vlm-tree-authoring", "data", "rule6_serve.json")
BUDGET = 500_000
BASELINE = {"rejections": 113, "secs": 834.0, "clause_vars_median": 202,
            "outcome": "AssignFail(kind='budget', site=500000)",
            "source": "../2026-09-24-dense-pleats/nogood-lizard.json"}


def arm(entry, core_extraction):
    clauses: list = []
    seen: list = []
    t0 = time.time()
    res = compile_tree(entry["requested"], entry["pairs"], dense=True,
                       assign_budget=BUDGET,
                       core_extraction=core_extraction,
                       debug_clause_sizes=clauses,
                       debug_cores=seen if core_extraction else None)
    secs = time.time() - t0
    row = {
        "core_extraction": core_extraction,
        "assign_budget": BUDGET,
        "stage_reached": res.stage_reached,
        "failure": repr(res.failure),
        "verdict": repr(res.verdict),
        "layers_tried": res.layers_tried,
        "rejections": len(clauses),
        "secs": round(secs, 1),
    }
    if clauses:
        row["clause_vars_min"] = min(clauses)
        row["clause_vars_median"] = statistics.median(clauses)
        row["clause_vars_max"] = max(clauses)
    # nodes-per-rejection is budget/rejections ONLY when the budget was
    # exhausted; if the run reached a decision it consumed fewer nodes and the
    # division would be meaningless.
    exhausted = "kind='budget'" in row["failure"]
    row["budget_exhausted"] = exhausted
    row["nodes_per_rejection"] = (
        round(BUDGET / len(clauses), 1) if exhausted and clauses else None)
    if core_extraction and seen:
        row["core_rows"] = seen
        row["blamed_creases_median"] = statistics.median(r[0] for r in seen)
        row["core_creases_median"] = statistics.median(r[1] for r in seen)
        row["oracle_calls_median"] = statistics.median(r[2] for r in seen)
        row["extract_secs_total"] = round(sum(r[3] for r in seen), 1)
        row["extract_secs_median"] = statistics.median(r[3] for r in seen)
    return row


def main():
    entry = next(e for e in json.load(open(RULE6))
                 if e["subject"] == "lizard")
    out = {"subject": "lizard", "baseline": BASELINE, "arms": []}

    def flush():
        json.dump(out, open(OUT, "w"), indent=1)

    for extraction in (False, True):
        label = "B (extraction ON)" if extraction else "A (extraction OFF)"
        print(f"=== arm {label} ===", flush=True)
        row = arm(entry, extraction)
        out["arms"].append(row)
        flush()
        print(f"  stage={row['stage_reached']} failure={row['failure']}",
              flush=True)
        print(f"  rejections={row['rejections']} secs={row['secs']} "
              f"clause_vars_median={row.get('clause_vars_median')}", flush=True)
        if extraction:
            print(f"  cone->core creases: "
                  f"{row.get('blamed_creases_median')} -> "
                  f"{row.get('core_creases_median')}  "
                  f"oracle_calls_median={row.get('oracle_calls_median')}  "
                  f"extraction {row.get('extract_secs_total')}s of "
                  f"{row['secs']}s", flush=True)

    a, b = out["arms"]

    # --- the guard that decides whether ANY verdict row may be claimed -------
    guard = (b.get("clause_vars_median") is not None
             and b["clause_vars_median"] < 10)
    out["clause_size_guard_passed"] = guard

    print()
    print(f"arm A: {a['rejections']} rejections, {a['secs']}s, "
          f"clause median {a.get('clause_vars_median')} vars, "
          f"outcome {a['failure']}")
    print(f"arm B: {b['rejections']} rejections, {b['secs']}s, "
          f"clause median {b.get('clause_vars_median')} vars, "
          f"outcome {b['failure']}")
    print()

    if not guard:
        out["verdict"] = "GUARD FAILED"
        flush()
        print("GUARD FAILED (spec section 7.3): arm B's median clause did not "
              "fall below 10 solver variables, so this run measures a broken "
              "or ineffective extraction rather than a fact about convergence. "
              "NO row of section 7.2 may be claimed, in either direction.")
        return

    if b["stage_reached"] == "emit":
        out["verdict"] = "CONVERGES"
        print("CONVERGES (row 1): dense layer-ordering reached emit. Wire on "
              "for dense; dense-pleats component 1 and its section 10 gallery "
              "become reachable.")
    elif "kind='budget'" not in b["failure"]:
        out["verdict"] = "DECISION NOT TIMEOUT"
        print("DECISION, NOT TIMEOUT (row 2): the search terminated on "
              f"{b['failure']} rather than exhausting its budget. The "
              "mechanism works AND no dense labelling of THIS crease set is "
              "stackable -- which points at the crease set and dense-pleats "
              "component 1, never at dense box-pleating in general.")
    else:
        out["verdict"] = "UNRESOLVED AT THIS BUDGET"
        print("UNRESOLVED AT THIS BUDGET (row 3): the clause narrowed but the "
              "run still exhausted its node budget. Size the 5,000,000-node "
              "run from the measured per-rejection cost below, then decide "
              "whether to spend it.")
        per = (b["extract_secs_total"] / b["rejections"]) if b["rejections"] else 0
        print(f"  extraction cost {per:.2f}s per rejection; at 10x the budget "
              f"and arm B's rejection rate that is roughly "
              f"{b['secs'] * 10 / 3600:.1f}h.")

    flush()


main()
```

- [ ] **Step 2: Run the A/B**

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -u \
    ../docs/superpowers/evidence/2026-09-27-core-in-loop/ab.py \
    ../docs/superpowers/evidence/2026-09-27-core-in-loop/ab.json
```

Expect roughly **40 minutes for the pair** if nothing improves: arm A ~834 s,
arm B ~1,430 s worst case (113 rejections carrying a measured median 5.27 s of
extraction each). **Launch it in the background, redirect to a log, and poll the
log and the JSON.** Do NOT kill it for being slow. The script writes `ab.json`
after each arm, so arm A's record survives even if arm B is interrupted.

**Re-read `ab.json` after the process exits and build every figure in the README
from that file, not from the log you watched.** On this branch a README once
asserted that a subject "never reached even its first rejection" while the JSON
committed in the same commit recorded that it had finished — the author had
capped a waiter and asserted the negative without re-reading the artifact.

- [ ] **Step 3: Write the README**

Create `docs/superpowers/evidence/2026-09-27-core-in-loop/README.md` containing:

- **The verdict first**, naming which of spec §7.2's four rows the run landed in,
  and whether §7.3's clause-size guard passed. If the guard failed, the file must
  say that no row may be claimed in either direction and must not report a
  convergence result.
- **The two arms side by side**: outcome and failure kind, rejections,
  `layers_tried`, wall-clock, and clause size in solver variables (min / median /
  max) for each.
- **Arm A against the committed baseline** (113 rejections, 834.0 s, median 202
  variables, `AssignFail(kind='budget', site=500000)`). State explicitly whether
  arm A reproduced it, and if it did not, say so and treat the discrepancy as a
  finding rather than noise — arm A exists to make the comparison same-machine.
- **The extraction reading**: cone → core in creases (median), oracle calls
  (median), and extraction seconds as a share of arm B's total. Name oracle calls
  as the portable figure and seconds as `lizard`-specific.
- **Why the rejection count is not the criterion**, in one short paragraph:
  nodes-per-rejection is `budget / rejections` identically when the budget is
  exhausted, so the two are one figure; and a rejection drop is the expected
  signature of stronger clauses but equally consistent with a search wandering
  deeper. Quote both numbers, and do not build an argument on their ratio.
- **What this does NOT establish.** A positive result here is about `lizard`: 26
  of the 31 rows behind the core measurement were `lizard`, and its `propagate`
  is ~100x slower than the other five subjects'. The subjects that would test
  generality (`octopus`, `dog`) cannot produce a dense labelling at all.
- **If the verdict is row 2 (`layer_unsat`)**: state it as "unsat for THIS crease
  set", never as "dense box-pleating is infeasible". The crease set is fixed by
  `contours.py`'s elevation field and dense-pleats component 1 (`pleat_grid.py`,
  the contiguity fill) was never built.
- **If the verdict is row 3 or 4**: give the measured per-rejection extraction
  cost and the sizing for the 5,000,000-node run, and say plainly whether the
  spec's §9.1 follow-on (a bounded variant, per Fleury & Biere) is indicated —
  that is, whether cost or pruning strength is the binding constraint.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/evidence/2026-09-27-core-in-loop/
git commit -m "$(printf '%s\n' 'evidence: does dense converge when the clause is its actual cause?' '' 'A/B on dense lizard at the 500,000-node budget, one boolean apart. Arm A' 'reproduces the committed baseline on the same machine in the same session' 'rather than quoting it.' '' 'The terminal outcome is the primary signal. The rejection count is not: a run' 'that exhausts its node budget consumes exactly the budget, so' 'nodes-per-rejection = budget/rejections identically and the two are ONE figure.' 'A rejection drop is the expected signature of stronger clauses and equally' 'consistent with a search wandering deeper.' '' 'The clause-size guard decides whether any verdict may be claimed at all: if arm' 'Bs median clause did not fall below 10 solver variables, the run measured a' 'broken extraction rather than a fact about convergence.' '' 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>')"
```

---

## Plan Self-Review

**Spec coverage.** §1 motivation → Task 1's module docstring. §2 prior art →
Task 1's docstring (all four sources, with the Fleury & Biere non-adoption
recorded in the spec rather than the code). §3 the change → Task 2 Steps 3-6.
§4 interfaces → Task 1 Step 3 and Task 2 Steps 4-6, signatures matching the spec
exactly. §5 soundness → Task 1's module docstring, and tested by
`test_shrink_narrows_the_committed_v1_lizard_contradiction`'s irreducibility loop
plus Task 2's CERTIFIED assertion. §6 error handling → Task 1's
`CoreExtractionError` and `_core`, tested by
`test_core_refuses_an_oracle_that_contradicts_on_the_empty_set`. §7.1 protocol →
Task 3 Steps 1-2. §7.2 the four rows → Task 3 Step 1's verdict block and Step 3's
first bullet. §7.3 the guard → Task 3 Step 1's `clause_size_guard_passed` and its
GUARD FAILED branch. §8 testing → Task 1 Step 1 (five tests), Task 2 Step 1
(three tests), Task 2 Step 8 (the byte-identity invariant via
`test_box_pleat_e2e.py`), and the explicit decision not to add a dense case.
§9 risks → Task 3 Step 3's "does NOT establish" and row-2 bullets. §10 evidence →
Task 3. §11 out of scope → Global Constraints.

**Placeholder scan.** None. Task 3 Step 3 describes README *content* rather than
supplying prose, which is correct: the text depends on numbers that do not exist
until Step 2 runs, and the bullets fix what must be said in every direction the
data can fall.

**Type consistency.** `cores.shrink(graph, labels, creases, *, counter=None) ->
frozenset` is defined in Task 1 and called with exactly that signature in Task 2
Step 5. `cores._core(candidates, holds, counter=None)` is used only by Task 1's
own test. `CoreExtractionError` is named identically in both. `debug_cores`
tuples are `(blamed_creases, core_creases, oracle_calls, secs)` in Task 2's
docstring, Task 2's test unpacking, and Task 3's `arm()` indexing (`r[0]`..`r[3]`)
— four fields in the same order in all three. `debug_clause_sizes` matches
`assign`'s existing parameter name.

**Two things the plan pins down deliberately:**

1. **Byte-identity is asserted only for `core_extraction=False`, and for
   `True` only on a subject that never rejects.** With the flag on and a
   rejection occurring, a narrower clause forbids more, so the search may accept
   a different candidate — a legitimate difference. A test asserting byte-identity
   there would be wrong, and Task 2 Step 1 says so in the test's own docstring so
   a later reader does not "fix" it.
2. **The `lizard-v1` core size is a bound (`1 <= len(core) <= 6`), not a pin,**
   even though the measured value is exactly 5 and this repository pins exact
   values elsewhere. The contract QuickXplain offers is irreducibility; a
   different split order would legitimately return a different irreducible core.
   The bound is tight enough to catch a regressed split out of a 12-edge cone
   while leaving the contract's real freedom intact.
