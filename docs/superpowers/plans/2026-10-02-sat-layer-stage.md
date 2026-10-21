# The SAT Layer Stage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the complete layer-ordering query a first-class `compile_tree` stage, so the dense path decides whether an M/V labelling exists instead of searching for one and exhausting its budget.

**Architecture:** One new module translates `layer_certify._iter_clauses` into CNF over two variable families — one Boolean per canonical face pair and one per crease — and solves it with Cadical. `compile_tree` gains one default-off keyword, and under it the layer stage asks `assign` for its *first* complete candidate (geometry only), builds the CNF, solves, and takes the witness labelling. The verdict comes from `layer_certify.verify` on the SAT model rather than from `decide`'s search.

**Tech Stack:** Python 3.14.3, pytest, `python-sat==1.9.dev15` (Cadical153), `mcp_harness/box_pleat/`.

**Spec:** `docs/superpowers/specs/2026-10-02-sat-layer-stage-design.md`. Read §3.3 (the four translations), §6 (the failure taxonomy) and §8 (testing) before Task 1.

## Global Constraints

- **Run every command from the worktree root** `<repo>`, or from `mcp_harness` where a step says so. Do **NOT** `cd` to the original repository root.
- **Python is `../.venv/bin/python3` from inside `mcp_harness`** (`.venv/bin/python3` from the worktree root). The venv is a symlink shared across worktrees.
- Tests run as `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python3 -m pytest tests/<file> -v`.
- **Never pass `--timeout` to pytest.** `pytest-timeout` is not installed; the flag makes pytest exit 4.
- **Never run `pytest tests/`** — 5,167 tests, over 3 hours. Always name the file, and run named files in **full**, never a `-k` subset.
- **Do NOT modify** `mcp_harness/box_pleat/layers.py`, `mcp_harness/layer_order.py`, `mcp_harness/layer_certify.py`, or `mcp_harness/box_pleat/cores.py`. Four shipped callers read `layer_order` (`mv_symmetrize._LayerGate`, `mv_repair`, `root_rank`, `server.py`'s serve gate).
- **Do NOT widen** `compile.py`'s `except (ValueError, RuntimeError, KeyError)` (two occurrences).
- **Add no `print` / `warnings` / `sys.stderr` call to `mcp_harness/box_pleat/`** — the package has zero across all 16 modules.
- **`grep -c box_pleat mcp_harness/server.py` must stay 0.**
- `sat_layers` ships **`False`**. Do not flip any default.
- **Mark every test that runs a real compile `@pytest.mark.slow`** — `make test` is the PR gate and runs `-m "not slow"` (`Makefile:53`); the marker is registered at `mcp_harness/conftest.py:33`.
- Write commit messages to a file **outside the repo** under `<scratch>/9681b5fb-8510-4f03-86c1-4e4b6d0a887a/scratchpad/` and use `git commit -F <file>`. zsh mangles heredocs containing backticks. End each message with `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- **Never use bare `git stash` / `git stash pop`** — the stash stack is shared with other worktrees and live sessions. Use a temporary WIP commit.
- **Never `git add -f` anything under `.superpowers/`** — gitignored process scratch (`.gitignore:45`).
- **Quote every glob passed to grep.** zsh's `nomatch` aborts the whole command when a glob fails to match, producing no output and no error.
- `grep -c` exits 1 on zero matches, which short-circuits `&&` chains.

---

## Measured Facts This Plan Relies On

Verified during planning, not assumed. A step whose expected output disagrees with these should stop and report rather than adapt.

| fact | value | how obtained |
|---|---|---|
| `assign`'s first-candidate return | `compile.py`-visible at `assign.py:1230-1232` | `grep -n` |
| `compile.py`'s `_LAYER_KIND` | line **43-44**, 3 entries | `grep -n` |
| `compile.py`'s post-`assign` tail | lines **552-574** | `grep -n` |
| `_Constraints` fields | `pairs, direct, equalities, tacos, covers, slots` | introspection |
| `DirectSlot` fields | `edge, lit, sign, faces` | introspection |
| `_lit(1,0)` / `_lit(0,1)` | `((0,1), True)` / `((0,1), False)` | direct call |
| **the 4-face fixture's clause families** | equality **1**, transitivity **4**, taco **1** | `layer_certify.clauses` |
| **the 4-face fixture's ground truth** | `verify` accepts **8 of 64** relations over 6 pairs | exhaustive enumeration |
| the 4-face fixture's CNF size | **20** clauses | 2·1 + 2·4 + 8·1 + 2·1 |
| the 4-face fixture's raw bound | `C(4,3)` = **4** | `math.comb` |
| 3-face cover alone | `verify` accepts **6 of 8** | exhaustive enumeration |
| dense `lizard` instance | 53,754 order vars, 745 label vars, **9,678,554** clauses | evidence §14 |
| dense `lizard` raw bound | `Σ C(|cover|,3)` = **31,314,680** | computed from `cons.covers` |
| dense `lizard` dedupes to | **4,511,932** triples | evidence §14 |
| Python / pysat | 3.14.3 / **1.9.dev15**, Cadical153 | `pip show` |

---

## File Structure

| file | responsibility |
|---|---|
| `mcp_harness/box_pleat/sat_order.py` (create) | `raw_triple_bound`, `encode`, `solve`, `SatVerdict`, `SatResult`, `SatOrderError`. Consumes `layer_certify`; knows nothing about folds. |
| `mcp_harness/tests/test_box_pleat_sat_order.py` (create) | Unit: the exhaustive equivalence check, the per-family checks, the label-link forcing table, both guard stages. No geometry, no compile. |
| `mcp_harness/box_pleat/compile.py` (modify) | the `sat_layers` keyword, the stage, the two new `LayerFail` kinds, the fold rewrite |
| `mcp_harness/tests/test_box_pleat_sat_stage.py` (create) | Wiring on real subjects, `slow`-marked |
| `docs/superpowers/evidence/2026-10-02-sat-layer-stage/` (create) | the end-to-end run, peak RSS, and the `max_clauses` decision |

---

### Task 1: `sat_order.encode` and the exhaustive equivalence check

**Files:**
- Create: `mcp_harness/box_pleat/sat_order.py`
- Create: `mcp_harness/tests/test_box_pleat_sat_order.py`

**Interfaces:**
- Consumes: `layer_certify._iter_clauses(cons)` yielding `Clause(family, variables, flips, prov)` where `family ∈ {"equality","transitivity","taco"}`, `variables` is a tuple of canonical `(lo,hi)` face pairs and `flips` the matching bits; `layer_certify.verify(cons, rel) -> VerifyResult` with `.violation`; `layer_order._Constraints(pairs, direct, equalities, tacos, covers, slots)`; `layer_order.DirectSlot(edge, lit, sign, faces)`; `pysat.formula.IDPool`; `pysat.solvers.Solver`.
- Produces, for Tasks 2–4: `raw_triple_bound(cons) -> int`; `encode(cons, slots, sink, *, max_clauses=MAX_CLAUSES) -> EncodeStats` where `EncodeStats` is a frozen dataclass with fields `order_var: dict`, `label_var: dict`, `clauses: int`, `families: dict`; `SatOrderError`; the module constants `MAX_RAW_TRIPLES = 100_000_000`, `MAX_CLAUSES = 20_000_000`, `SOLVER = "cadical153"`.

**Note on one deviation from the spec's §7 sketch.** The spec sketches `encode(cons, slots, *, sink=None) -> tuple`. This plan makes **`sink` a required positional argument** and returns a named `EncodeStats` instead of a tuple. That removes a dual return mode (list-or-None) that nothing needs: tests pass `cl.append`, Task 3 passes `solver.add_clause`. Strictly simpler; recorded here so a reviewer sees it as a decision rather than a drift.

- [ ] **Step 1: Write the failing tests**

Create `mcp_harness/tests/test_box_pleat_sat_order.py`:

```python
"""`sat_order`: the ADK clause set as CNF, checked against `layer_certify`.

Spec: `docs/superpowers/specs/2026-10-02-sat-layer-stage-design.md` §3.3, §8.

No geometry and no compile in this file -- every fixture is a hand-built
`layer_order._Constraints`, so the encoder is tested against the project's own
clause semantics rather than against a folded state.

THE LOAD-BEARING TEST is `test_cnf_models_equal_verify_accepted_exactly`. It
enumerates every assignment of a small instance and requires the CNF's
satisfying set to EQUAL the set `layer_certify.verify` accepts -- both
directions. Every other test here localises a failure the equivalence check
would also catch, EXCEPT the label-link test, which the equivalence check
cannot catch at all: the label variables are free there, so they adapt to
whatever the order variables do and never restrict the order projection.
"""
import itertools
import math

import layer_certify
import pytest
from layer_order import _Constraints, DirectSlot, Prov, _lit

from box_pleat import sat_order

PROV = Prov(text="synthetic", creases=((0, 1),), faces=(0, 1))


def _cons(*, covers, equalities=(), tacos=(), slots=(), direct=()):
    """A `_Constraints` whose `pairs` is exactly the pairs its covers induce."""
    pairs = frozenset(pr for c in covers
                      for pr in itertools.combinations(sorted(c), 2))
    return _Constraints(pairs=pairs, direct=direct, equalities=equalities,
                        tacos=tacos, covers=tuple(covers), slots=tuple(slots))


def ALL_FAMILIES():
    """4 faces in one cover, one equality, one taco, one slot.

    Measured 2026-10-02: `layer_certify.clauses` yields equality 1,
    transitivity 4, taco 1, and `verify` accepts exactly 8 of the 64
    relations over its 6 pairs.
    """
    return _cons(
        covers=[frozenset({0, 1, 2, 3})],
        equalities=((_lit(0, 1), _lit(2, 3), PROV),),
        tacos=(((0, 1), (2, 3), PROV),),
        slots=(DirectSlot(edge=(10, 11), lit=_lit(0, 1), sign=1,
                          faces=(0, 1)),),
    )


def _encode(cons):
    cl = []
    st = sat_order.encode(cons, cons.slots, cl.append)
    return cl, st


def _models_over(cl, order_var):
    """Every assignment of the ORDER variables the CNF admits.

    Enumerated rather than taken from the solver, so this is the CNF's own
    satisfying set projected onto the order variables -- label variables are
    existentially quantified by being left free.
    """
    from pysat.solvers import Solver
    out = set()
    keys = sorted(order_var)
    with Solver(name=sat_order.SOLVER, bootstrap_with=cl) as s:
        for bits in itertools.product([False, True], repeat=len(keys)):
            ass = [order_var[k] if b else -order_var[k]
                   for k, b in zip(keys, bits)]
            if s.solve(assumptions=ass):
                out.add(bits)
    return out


def _verify_accepted(cons):
    """Every relation `layer_certify.verify` accepts."""
    keys = sorted(cons.pairs)
    out = set()
    for bits in itertools.product([False, True], repeat=len(keys)):
        rel = dict(zip(keys, bits))
        if layer_certify.verify(cons, rel).violation is None:
            out.add(bits)
    return out


def test_cnf_models_equal_verify_accepted_exactly():
    """THE load-bearing test: set EQUALITY, not containment.

    Containment in one direction would pass for an over-constrained encoder
    (admits too little) and in the other for an under-constrained one. Only
    equality rules out both.
    """
    cons = ALL_FAMILIES()
    cl, st = _encode(cons)
    assert st.clauses == 20, st.clauses
    assert st.families == {"equality": 1, "transitivity": 4, "taco": 1}
    accepted = _verify_accepted(cons)
    assert len(accepted) == 8, (
        f"the fixture's ground truth moved: verify accepts {len(accepted)} of "
        f"64, measured 8 on 2026-10-02. Fix the fixture, not the assertion.")
    assert _models_over(cl, st.order_var) == accepted


def test_transitivity_forbids_exactly_the_two_cyclic_states():
    """A bare 3-cover: 6 of 8 accepted, the two cyclic states excluded."""
    cons = _cons(covers=[frozenset({0, 1, 2})])
    cl, st = _encode(cons)
    assert st.families == {"equality": 0, "transitivity": 1, "taco": 0}
    accepted = _verify_accepted(cons)
    assert len(accepted) == 6, len(accepted)
    assert _models_over(cl, st.order_var) == accepted
    # The two forbidden states, in THIS test's coordinates. `_satisfied` reads
    # a transitivity clause's variables as ((a,b), (b,c), (a,c)) -- for faces
    # 0,1,2 that is (0,1), (1,2), (0,2) -- so its cyclic states (T,T,F) and
    # (F,F,T) become (T,F,T) and (F,T,F) once re-indexed into the SORTED pair
    # order these tuples use. Spelling that out because the two orders differ
    # and a tuple written in the wrong one silently tests nothing.
    assert (True, False, True) not in accepted
    assert (False, True, False) not in accepted


def test_equality_forces_its_two_literals_to_agree():
    cons = _cons(covers=[frozenset({0, 1, 2, 3})],
                 equalities=((_lit(0, 1), _lit(2, 3), PROV),))
    cl, st = _encode(cons)
    assert _models_over(cl, st.order_var) == _verify_accepted(cons)


def test_taco_forces_even_parity_over_its_four_literals():
    cons = _cons(covers=[frozenset({0, 1, 2, 3})],
                 tacos=(((0, 1), (2, 3), PROV),))
    cl, st = _encode(cons)
    assert _models_over(cl, st.order_var) == _verify_accepted(cons)


@pytest.mark.parametrize("lit,sign,label,expected", [
    (_lit(0, 1), 1, "M", False),
    (_lit(0, 1), 1, "V", True),
    (_lit(0, 1), -1, "M", True),
    (_lit(0, 1), -1, "V", False),
    (_lit(1, 0), 1, "M", True),
    (_lit(1, 0), 1, "V", False),
    (_lit(1, 0), -1, "M", False),
    (_lit(1, 0), -1, "V", True),
])
def test_label_link_forces_the_order_variable(lit, sign, label, expected):
    """The forcing table `layers._seed` implies, derived 2026-10-02.

    `_seed` is `(label == "V") == (sign == 1)` and a literal's value is
    `rel[pair] != flip`, so `rel[pair]` must be `_seed != flip`.

    THE EQUIVALENCE CHECK CANNOT CATCH THESE. There the label variables are
    free and simply follow the order variables, so dropping a biconditional
    direction or ignoring `sign` leaves the order projection untouched. This
    test pins the labels as assumptions instead, which is the only way the
    link is observable.
    """
    from pysat.solvers import Solver
    cons = _cons(covers=[frozenset({0, 1})],
                 slots=(DirectSlot(edge=(10, 11), lit=lit, sign=sign,
                                   faces=(0, 1)),))
    cl, st = _encode(cons)
    lv = st.label_var[(10, 11)]
    ov = st.order_var[lit[0]]
    with Solver(name=sat_order.SOLVER, bootstrap_with=cl) as s:
        assume = [lv if label == "V" else -lv]
        assert s.solve(assumptions=assume), "the labelling itself is unsat"
        assert not s.solve(assumptions=assume + [-ov if expected else ov]), (
            f"sign={sign} label={label} must force rel[{lit[0]}]={expected}")


def test_raw_triple_bound_is_the_sum_over_covers():
    cons = _cons(covers=[frozenset(range(4)), frozenset(range(5))])
    assert sat_order.raw_triple_bound(cons) == math.comb(4, 3) + math.comb(5, 3)
    assert sat_order.raw_triple_bound(ALL_FAMILIES()) == 4


def test_encode_refuses_past_max_clauses_mid_emission():
    """The streaming counter, which fires where the loose bound cannot."""
    cons = _cons(covers=[frozenset(range(8))])
    with pytest.raises(sat_order.SatOrderError, match="max_clauses"):
        sat_order.encode(cons, cons.slots, lambda c: None, max_clauses=5)


def test_unknown_clause_family_refuses_rather_than_guessing():
    """`layer_certify._satisfied` raises on an unknown family; so must this.

    Encoding an unrecognised family as anything would silently admit a
    constraint nobody checks.
    """
    class _Fake:
        family = "wormhole"
        variables = ((0, 1),)
        flips = (False,)
        prov = "synthetic"

    cons = _cons(covers=[frozenset({0, 1})])
    real = layer_certify._iter_clauses
    try:
        layer_certify._iter_clauses = lambda c: iter([_Fake()])
        with pytest.raises(sat_order.SatOrderError, match="wormhole"):
            sat_order.encode(cons, cons.slots, lambda c: None)
    finally:
        layer_certify._iter_clauses = real
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python3 -m pytest tests/test_box_pleat_sat_order.py -v
```

Expected: a collection error — `ModuleNotFoundError: No module named 'box_pleat.sat_order'`.

- [ ] **Step 3: Write the module**

Create `mcp_harness/box_pleat/sat_order.py`:

```python
"""The complete layer-ordering query as SAT: does ANY labelling order?

Spec: `docs/superpowers/specs/2026-10-02-sat-layer-stage-design.md`.

`layer_certify` already decides ONE labelling completely (Akitaya, Demaine &
Ku, OSME 2024: verifying a facewise order is in P, finding one is NP). This
module asks the JOINT question -- is there a labelling of this crease set that
admits a valid order -- which `layer_certify` cannot, because its `cons.direct`
pins the labelling before it starts.

WHAT IS NOT RE-DERIVED. The clause set is `layer_certify._iter_clauses`
TRANSLATED. This module reads no geometry and reimplements no predicate, so its
CNF cannot disagree with the shipped verifier about what the constraints are.
`layer_certify._satisfied` is the authority for all three families and the
translations below quote it.

TWO VARIABLE FAMILIES. One Boolean per canonical face pair, exactly
`layer_order._lit`'s convention -- a literal is `(pair, flip)` whose value is
`rel[pair] != flip`. And one per crease edge, linked to the order variables by
the `DirectSlot` biconditionals. The second family is what makes the query
joint, and it is sound because `layer_order.constraints_for` documents that
"everything except `_Constraints.direct` depends on the folded geometry alone,
which `flat_fold` derives from the crease SET": M and V both reflect across a
crease, so they give identical folded positions and differ only in which side
lands above. Measured on dense `lizard`: max folded-position difference
EXACTLY 0.0 (evidence `2026-10-02-witness-identity-113/README.md` section 15.1).

THIS MODULE NEVER TOUCHES A FOLD. `solve` returns a labelling and a relation;
`compile.py` owns the rewrite. That keeps the encoder testable against a
hand-built `_Constraints` with no geometry at all.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from math import comb

import layer_certify
from pysat.formula import IDPool
from pysat.solvers import Solver

#: Refuse before `layer_certify._iter_clauses` allocates. Dense `lizard`'s
#: bound is 31,314,680 against the 4,511,932 triples it dedupes to, so this is
#: ~3.2x that instance. NOT tuned: it exists to admit the one measured
#: instance with headroom and refuse what would exhaust memory.
MAX_RAW_TRIPLES = 100_000_000

#: The streaming ceiling. Dense `lizard` emits 9,678,554, so this is ~2.1x.
MAX_CLAUSES = 20_000_000

SOLVER = "cadical153"


class SatOrderError(Exception):
    """This module could not honour its own contract.

    Deliberately subclasses `Exception` and NOT
    `ValueError`/`RuntimeError`/`KeyError`: those three are what the
    `except (ValueError, RuntimeError, KeyError)` handler around the
    `assign(...)` call in `compile_tree` catches, folding them into an
    indistinguishable `AssignFail("error")`. Every condition raised here is a
    defect in this encoder -- an unknown clause family, a clause budget
    crossed, or a model the project's own verifier rejects -- and none is a
    fact about the tree being compiled. Matching `cores.CoreExtractionError`'s
    reasoning for the same choice.
    """


@dataclass(frozen=True)
class EncodeStats:
    order_var: dict      # (lo, hi) -> DIMACS variable
    label_var: dict      # crease edge -> DIMACS variable
    clauses: int
    families: dict       # family -> clauses of that family SEEN (not emitted)


@dataclass(frozen=True)
class SatVerdict:
    """CERTIFIED / REFUTED / OVERSIZE, with the solver's own facts.

    Deliberately NOT a `layer_certify.Verdict`. That type carries `nodes` and
    `free` -- search-node counts from `decide`'s branch-and-propagate -- and
    this stage runs no search, so both would have to be filled with a
    defaulted zero. A defaulted number read as a measurement is this project's
    named recurring failure, so the type differs instead. `kind` keeps the same
    vocabulary, so a caller reading `.kind` still works.
    """
    kind: str
    violation: object
    order_vars: int
    label_vars: int
    clauses: int
    build_secs: float
    solve_secs: float


@dataclass(frozen=True)
class SatResult:
    sat: bool
    labels: dict | None      # {(v_lo, v_hi): "M" | "V"}
    relation: dict | None    # {(lo, hi): bool}, COMPLETE
    verdict: SatVerdict


def raw_triple_bound(cons) -> int:
    """An upper bound on the transitivity triples, with no allocation.

    `sum(C(|cover|, 3))` over the arrangement cells, which over-counts because
    overlapping covers share triples -- 31,314,680 against dense `lizard`'s
    4,511,932, a factor of 6.94.

    Loose on purpose. The exact count needs the dedup set that lives INSIDE
    `layer_certify._iter_clauses`, and by the time that exists the memory is
    already spent, so an exact pre-check is impossible without editing a module
    this spec leaves alone. This only has to separate "fine" from "will exhaust
    memory", and the streaming counter in `encode` is the exact backstop.
    """
    return sum(comb(len(c), 3) for c in cons.covers)


def encode(cons, slots, sink, *, max_clauses: int = MAX_CLAUSES) -> EncodeStats:
    """Emit this constraint system's CNF into `sink`, one clause at a time.

    `sink` is required rather than optional so there is no dual return mode:
    tests pass `list.append`, `compile.py` passes `Solver.add_clause`. Nothing
    materialises 9.7 million Python lists.

    Raises `SatOrderError` the moment the emitted count crosses
    `max_clauses`, so an instance that slipped `raw_triple_bound` still never
    materialises.
    """
    pool = IDPool()
    order_var = {p: pool.id(("rel", p)) for p in sorted(cons.pairs)}
    label_var = {s.edge: pool.id(("lab", s.edge)) for s in slots}

    def lit(pair, flip):
        v = order_var[pair]
        return -v if flip else v

    n = 0
    fam = {"equality": 0, "transitivity": 0, "taco": 0}

    def emit(clause):
        nonlocal n
        n += 1
        if n > max_clauses:
            raise SatOrderError(
                f"this instance emits more than max_clauses={max_clauses:,} "
                f"CNF clauses. `raw_triple_bound` read "
                f"{raw_triple_bound(cons):,} and did not refuse, so the loose "
                f"bound was not loose enough for this shape; the streaming "
                f"counter is the exact backstop. Raise max_clauses only "
                f"against a measured peak-RSS figure.")
        sink(clause)

    for c in layer_certify._iter_clauses(cons):
        ls = [lit(p, f) for p, f in zip(c.variables, c.flips)]
        if c.family == "equality":
            # `_satisfied`: vals[0] == vals[1]  ->  L0 <-> L1
            emit([-ls[0], ls[1]])
            emit([ls[0], -ls[1]])
        elif c.family == "transitivity":
            # `_satisfied`: not (rab == rbc and rac != rab). The two cyclic
            # states (T,T,F) and (F,F,T) are the only forbidden assignments.
            a, b, d = ls
            emit([-a, -b, d])
            emit([a, b, -d])
        elif c.family == "taco":
            # `_satisfied`: (L0 != L1) == (L2 != L3), i.e. the 4-way XOR is
            # EVEN. Forbid every odd-parity assignment: 8 clauses. Chosen over
            # a Tseitin auxiliary variable per XOR -- 8 clauses x 74,602
            # tacos is cheaper for a CDCL solver at this scale than 74,602
            # extra variables (spec section 0).
            for m in range(16):
                bits = [(m >> i) & 1 for i in range(4)]
                if sum(bits) % 2 == 1:
                    emit([(-ls[i] if bits[i] else ls[i]) for i in range(4)])
        else:
            raise SatOrderError(
                f"unknown clause family {c.family!r}. "
                f"`layer_certify._satisfied` raises on it too; encoding it as "
                f"anything here would silently admit a family nobody checks.")
        fam[c.family] += 1

    for s in slots:
        # `layers._seed`: val = (label == "V") == (sign == 1). With Lv meaning
        # "this crease is V", the DirectSlot's constraint is
        #   (rel[pair] != flip) == (sign == 1 ? Lv : not Lv)
        pair, flip = s.lit
        o = lit(pair, flip)
        lv = label_var[s.edge]
        rhs = lv if s.sign == 1 else -lv
        emit([-o, rhs])
        emit([o, -rhs])

    return EncodeStats(order_var=order_var, label_var=label_var,
                       clauses=n, families=fam)
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python3 -m pytest tests/test_box_pleat_sat_order.py -v
```

Expected: **15 passed** — 7 test functions, one of them parametrised 8 ways. Under a minute.

- [ ] **Step 5: Verify the five pre-registered mutations, and which test kills each**

Each mutation must turn the named test red. Apply one at a time **to a copy in the scratchpad**, run, confirm red, discard the copy. Do not mutate the committed file.

All five were verified red during planning; the "killed by" column is **measured**, not predicted.

| # | mutation | killed by |
|---|---|---|
| 1 | drop `emit([ls[0], -ls[1]])` from `equality` | the equivalence test, and `test_equality_forces_its_two_literals_to_agree` |
| 2 | change transitivity's `emit([a, b, -d])` to `emit([a, b, d])` | the equivalence test, `test_transitivity_...`, and both other family tests (their fixtures share a 4-cover) |
| 3 | invert the taco parity (`% 2 == 0`) | the equivalence test and `test_taco_forces_even_parity_over_its_four_literals` |
| 4 | drop `emit([o, -rhs])` from the slot loop | `test_label_link_forces_the_order_variable` **and** the equivalence test — but see below |
| 5 | **ignore `sign` (`rhs = lv` always)** | **`test_label_link_forces_the_order_variable` ONLY** |

**The precise claim about mutation 4, because the loose version is wrong.** It *is* killed by the equivalence test — but by that test's `assert st.clauses == 20` line, a **clause-count** check, not by the set equality. Dropping a clause changes the count, and any dropped clause dies that way whatever its semantics.

**Mutation 5 is the one that proves the label-link test is necessary.** It changes a clause's *content* and not the count, so the count assertion cannot see it; and the equivalence check cannot either, because the label variables are free there and simply follow the order variables, leaving the order projection untouched. It is killed by the label-link test and by nothing else.

Report each mutation's actual outcome and the assertion that caught it. If mutation 5 is killed by anything other than the label-link test, that is a finding — report it rather than re-assigning the row.

- [ ] **Step 6: Commit**

```bash
cd mcp_harness && git add box_pleat/sat_order.py tests/test_box_pleat_sat_order.py && cd .. && git commit -F <scratch>/9681b5fb-8510-4f03-86c1-4e4b6d0a887a/scratchpad/t1-sat-msg.txt
```

`t1-sat-msg.txt`:

```
sat-stage: the ADK clause set as CNF, pinned by exhaustive equivalence

layer_certify already decides ONE labelling completely, so this encodes the
JOINT question instead: one Boolean per canonical face pair AND one per
crease, linked by the DirectSlot biconditionals.

The clause set is layer_certify._iter_clauses TRANSLATED, never re-derived, so
the CNF cannot disagree with the shipped verifier about what the constraints
are. _satisfied is the authority for all three families.

The load-bearing test enumerates all 64 assignments of a 4-face fixture and
requires the CNF's satisfying set to EQUAL the set verify accepts -- both
directions, since containment one way passes for an over-constrained encoder
and the other way for an under-constrained one.

And the label link needs its own test: the equivalence check CANNOT catch it,
because there the label variables are free and adapt to the order variables,
leaving the order projection untouched. Eight parametrised cases pin the
forcing table _seed implies across sign and label.

Five mutations verified red, two of them only by the label-link test.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

### Task 2: `sat_order.solve` — the guard, the solver, the verdict

**Files:**
- Modify: `mcp_harness/box_pleat/sat_order.py` (append `solve`)
- Modify: `mcp_harness/tests/test_box_pleat_sat_order.py` (append `solve` tests)

**Interfaces:**
- Consumes: `raw_triple_bound`, `encode`, `EncodeStats`, `SatVerdict`, `SatResult`, `SatOrderError`, `MAX_RAW_TRIPLES`, `MAX_CLAUSES`, `SOLVER` from Task 1; `layer_certify.verify(cons, rel)`.
- Produces, for Task 3: `solve(cons, slots, *, max_raw_triples=MAX_RAW_TRIPLES, max_clauses=MAX_CLAUSES, solver=SOLVER) -> SatResult`. On SAT, `SatResult.labels` maps each `DirectSlot.edge` to `"M"`/`"V"` and `SatResult.relation` maps every pair in `cons.pairs` to a bool; on UNSAT and OVERSIZE both are `None`.

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_box_pleat_sat_order.py`:

```python
def test_solve_returns_a_relation_verify_accepts():
    """SAT, and the model is a genuine layer order by the project's verifier.

    The POSITIVE control. An over-constrained encoder is UNSAT on everything
    and would pass every negative check below vacuously, so this is the one
    that cannot be substituted for.
    """
    cons = ALL_FAMILIES()
    res = sat_order.solve(cons, cons.slots)
    assert res.sat is True
    assert res.verdict.kind == "CERTIFIED"
    assert res.verdict.violation is None
    assert set(res.relation) == set(cons.pairs)
    assert set(res.labels) == {(10, 11)}
    assert res.labels[(10, 11)] in ("M", "V")
    assert layer_certify.verify(cons, res.relation).violation is None


def test_solve_reports_unsat_as_refuted_with_no_model():
    """An unsatisfiable system: a 3-cycle pinned by `direct` units.

    `direct` is the only part of a `_Constraints` that depends on labels, and
    pinning all three pair variables into a cyclic state makes the system
    unsatisfiable however the labels fall.
    """
    cons = _cons(covers=[frozenset({0, 1, 2})],
                 direct=((_lit(0, 1), True, PROV),
                         (_lit(1, 2), True, PROV),
                         (_lit(2, 0), True, PROV)))
    # `direct` is not encoded (the labels are variables), so pin the cycle
    # through slots instead -- one per pair, each forcing the cyclic value.
    slots = tuple(DirectSlot(edge=(100 + i, 101 + i), lit=l, sign=1,
                             faces=(0, 1))
                  for i, l in enumerate((_lit(0, 1), _lit(1, 2), _lit(2, 0))))
    cons = _cons(covers=[frozenset({0, 1, 2})], slots=slots)
    res = sat_order.solve(cons, cons.slots)
    # With three independent label variables the cycle is avoidable, so this
    # instance IS satisfiable -- assert that, then force the cycle.
    assert res.sat is True
    from pysat.solvers import Solver
    cl = []
    st = sat_order.encode(cons, cons.slots, cl.append)
    forced = []
    for l in (_lit(0, 1), _lit(1, 2), _lit(2, 0)):
        v = st.order_var[l[0]]
        forced.append(-v if l[1] else v)
    with Solver(name=sat_order.SOLVER, bootstrap_with=cl) as s:
        assert not s.solve(assumptions=forced), (
            "the cyclic state must be unsatisfiable; if it is not, "
            "transitivity is not being encoded")


def test_solve_refuses_an_oversize_instance_without_allocating():
    """Stage 1 of the guard: the loose bound, before `_iter_clauses` runs."""
    cons = _cons(covers=[frozenset(range(40))])
    res = sat_order.solve(cons, cons.slots, max_raw_triples=10)
    assert res.sat is False
    assert res.verdict.kind == "OVERSIZE"
    assert res.verdict.clauses == 0, "nothing may be emitted after OVERSIZE"
    assert res.labels is None and res.relation is None


def test_solve_refuses_when_the_streaming_counter_crosses():
    """Stage 2: slips the loose bound, caught during emission.

    `max_raw_triples` is set high enough to pass stage 1 and `max_clauses`
    low enough that stage 2 must fire, so neither test can pass by the
    other's mechanism.
    """
    cons = _cons(covers=[frozenset(range(8))])
    assert sat_order.raw_triple_bound(cons) == math.comb(8, 3)
    res = sat_order.solve(cons, cons.slots,
                          max_raw_triples=10 ** 9, max_clauses=4)
    assert res.sat is False
    assert res.verdict.kind == "OVERSIZE"


def test_solve_raises_when_verify_rejects_its_own_model(monkeypatch):
    """An under-constrained encoder must CRASH, not refuse.

    Every `LayerFail` kind reads as a fact about the tree. `verify` rejecting
    this module's model means the CNF admitted something the project's
    verifier calls invalid -- an encoder defect. Typing that as a per-tree
    refusal would publish a bug as a geometric finding.
    """
    class _Bad:
        violation = "synthetic violation"
        checked = 1
        skipped = 0

    monkeypatch.setattr(layer_certify, "verify", lambda c, r: _Bad())
    cons = ALL_FAMILIES()
    with pytest.raises(sat_order.SatOrderError, match="verify"):
        sat_order.solve(cons, cons.slots)
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python3 -m pytest tests/test_box_pleat_sat_order.py -v
```

Expected: the 15 from Task 1 pass; the 5 new ones fail with `AttributeError: module 'box_pleat.sat_order' has no attribute 'solve'`.

- [ ] **Step 3: Append `solve` to the module**

Append to `mcp_harness/box_pleat/sat_order.py`:

```python
def solve(cons, slots, *, max_raw_triples: int = MAX_RAW_TRIPLES,
          max_clauses: int = MAX_CLAUSES, solver: str = SOLVER) -> SatResult:
    """Is there a labelling of this crease set admitting a valid layer order?

    SAT means yes, with a witness. UNSAT is a PROOF that none exists -- over
    the crease set `cons` was built from, which fixes the F set. OVERSIZE means
    the instance was too big to decide and says nothing about either.

    The verdict on a SAT model comes from `layer_certify.verify`, not from
    `layer_certify.decide`: the model already assigns every order variable, so
    a complete relation is in hand and searching for one again would cost
    15-50 s (measured, evidence `2026-10-02-witness-identity-113` section 16.1)
    for an answer we have. `verify` checks every clause `clauses(cons)`
    generates against a complete relation, which is exactly what CERTIFIED
    claims.
    """
    bound = raw_triple_bound(cons)
    if bound > max_raw_triples:
        return SatResult(
            sat=False, labels=None, relation=None,
            verdict=SatVerdict(
                kind="OVERSIZE", violation=None, order_vars=len(cons.pairs),
                label_vars=len(slots), clauses=0, build_secs=0.0,
                solve_secs=0.0))

    s = Solver(name=solver)
    try:
        t0 = time.perf_counter()
        st = encode(cons, slots, s.add_clause, max_clauses=max_clauses)
        build = round(time.perf_counter() - t0, 3)

        t1 = time.perf_counter()
        sat = s.solve()
        model = s.get_model() if sat else None
        solve_secs = round(time.perf_counter() - t1, 3)
    except SatOrderError as exc:
        if "max_clauses" not in str(exc):
            raise
        return SatResult(
            sat=False, labels=None, relation=None,
            verdict=SatVerdict(
                kind="OVERSIZE", violation=None, order_vars=len(cons.pairs),
                label_vars=len(slots), clauses=max_clauses, build_secs=0.0,
                solve_secs=0.0))
    finally:
        s.delete()

    base = dict(order_vars=len(st.order_var), label_vars=len(st.label_var),
                clauses=st.clauses, build_secs=build, solve_secs=solve_secs)

    if not sat:
        return SatResult(sat=False, labels=None, relation=None,
                         verdict=SatVerdict(kind="REFUTED", violation=None,
                                            **base))

    true = {l for l in model if l > 0}
    relation = {p: (v in true) for p, v in st.order_var.items()}
    labels = {e: ("V" if v in true else "M")
              for e, v in st.label_var.items()}

    vr = layer_certify.verify(cons, relation)
    if vr.violation is not None:
        raise SatOrderError(
            f"`layer_certify.verify` REJECTS this module's own SAT model: "
            f"{vr.violation}. The CNF admitted a relation the project's "
            f"verifier calls invalid, so this encoder is under-constrained. "
            f"This is a defect in `sat_order`, never a fact about the tree, "
            f"which is why it raises instead of returning a verdict.")

    return SatResult(sat=True, labels=labels, relation=relation,
                     verdict=SatVerdict(kind="CERTIFIED", violation=None,
                                        **base))
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python3 -m pytest tests/test_box_pleat_sat_order.py -v
```

Expected: **20 passed**.

- [ ] **Step 5: Verify three more mutations**

On a scratchpad copy, each must turn the named test red:

All three were verified red during planning; the "killed by" column is **measured**.

| # | mutation | killed by |
|---|---|---|
| 6 | `if vr.violation is not None:` → `if False:` (never consult `verify`) | `test_solve_raises_when_verify_rejects_its_own_model` |
| 7 | `if bound > max_raw_triples:` → `if False:` | `test_solve_refuses_an_oversize_instance_without_allocating` |
| 8 | the counter's `SatOrderError` re-raised instead of becoming OVERSIZE | `test_solve_refuses_when_the_streaming_counter_crosses` |

- [ ] **Step 6: Commit**

```bash
cd mcp_harness && git add box_pleat/sat_order.py tests/test_box_pleat_sat_order.py && cd .. && git commit -F <scratch>/9681b5fb-8510-4f03-86c1-4e4b6d0a887a/scratchpad/t2-sat-msg.txt
```

`t2-sat-msg.txt`:

```
sat-stage: solve(), the two-stage size guard, and SatVerdict

The verdict on a SAT model comes from layer_certify.verify rather than
decide: the model already assigns every order variable, so searching for a
complete relation again would cost 15-50 s for an answer already in hand.

SatVerdict is deliberately NOT a layer_certify.Verdict. That type carries
nodes and free -- search-node counts from decide's branch-and-propagate --
and this path runs no search, so both would be a defaulted zero. A defaulted
number read as a measurement is this project's named recurring failure, so
the type differs instead and kind keeps the same vocabulary.

Two guard stages, neither satisfiable by the other: a raw bound computable
without allocation, because the exact triple count needs the dedup set that
lives INSIDE _iter_clauses; plus a streaming counter as the exact backstop.

And verify REJECTING the model raises rather than returning a verdict: every
LayerFail kind reads as a fact about the tree, and that case is an encoder
bug.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

### Task 3: wire the stage into `compile_tree`

**Files:**
- Modify: `mcp_harness/box_pleat/compile.py` — signature, `_LAYER_KIND` neighbourhood at `:43-44`, the `LayerFail` docstring, the tail at `:552-574`
- Create: `mcp_harness/tests/test_box_pleat_sat_stage.py`

**Interfaces:**
- Consumes: `sat_order.solve(cons, slots) -> SatResult` with `.sat`, `.labels`, `.relation`, `.verdict` (and `.verdict.kind ∈ {"CERTIFIED","REFUTED","OVERSIZE"}`) from Task 2; `assign(..., global_check=None)` returning the first complete candidate (`assign.py:1230-1232`); `to_fold`, `flat_fold.flat_fold`, `_layers.constraint_graph`.
- Produces: `compile_tree(..., sat_layers: bool = False)`; `LayerFail` kinds `"unsatisfiable"` and `"oversize"`; `res.verdict` as a `sat_order.SatVerdict` on the SAT path.

- [ ] **Step 1: Write the failing tests**

Create `mcp_harness/tests/test_box_pleat_sat_stage.py`:

```python
"""`compile_tree(sat_layers=True)`: the complete layer stage, end to end.

Spec: `docs/superpowers/specs/2026-10-02-sat-layer-stage-design.md` section 8.3.

SLOW BY DESIGN -- every test here runs a real compile. `make test` is the PR
gate and runs `-m "not slow"` (`Makefile:53`), so each is marked.

PROPERTIES GATE; IDENTITY IS REPORTED. Everywhere else in this codebase the
gate is identity -- byte-identical folds, equal node counts, matching digests.
That cannot be the gate here: ANY satisfying model is a valid answer, so the
stage has no single correct output. The CNF is deterministic (`sorted` pairs, a
tuple of covers, `combinations(sorted(cover), 3)`) so Cadical will very likely
return the same witness run to run, but requiring that would assert a solver
implementation detail as a correctness property and a solver upgrade would read
as a regression. So: assert CERTIFIED and `cp_audit` clean, and PRINT a hash of
the witness labelling so drift is visible without being a failure.
"""
import hashlib
import json

import cp_audit
import pytest
from box_pleat.compile import LayerFail, compile_tree
from test_box_pleat_tree import RULE6


def _entry(subject):
    with open(RULE6) as fh:
        return next(e for e in json.load(fh) if e["subject"] == subject)


def _audit(fold):
    r = cp_audit.audit_fold(fold)
    return {
        "interior": len(r.vertices),
        "maekawa": sum(1 for v in r.vertices if abs(v.m - v.v) != 2),
        "kawasaki": sum(1 for v in r.vertices
                        if abs(v.kawasaki_residual_deg) > r.kawasaki_tol_deg),
        "arrangement": sum(1 for v in r.vertices if not v.arrangement_ok),
        "closure_bad_edges": r.closure_bad_edges,
    }


@pytest.mark.slow
def test_sparse_lizard_sat_stage_emits_and_audits_clean():
    """The POSITIVE control, on a subject whose shipped compile reaches emit.

    An encoder that refuses everything would pass every negative assertion in
    this file; only this one rules that out.
    """
    e = _entry("lizard")
    res = compile_tree(e["requested"], e["pairs"], sat_layers=True)
    assert res.stage_reached == "emit", res.failure
    assert res.verdict.kind == "CERTIFIED", res.verdict
    a = _audit(res.fold)
    assert a["maekawa"] == 0 and a["kawasaki"] == 0, a
    assert a["arrangement"] == 0 and a["closure_bad_edges"] == 0, a
    assert a["interior"] > 0, "an empty audit population proves nothing"
    print("WITNESS HASH (reported, not gated):",
          hashlib.sha256(json.dumps(res.fold["edges_assignment"]).encode()
                         ).hexdigest()[:16])


@pytest.mark.slow
def test_sat_layers_off_is_byte_identical():
    """The default must change nothing."""
    e = _entry("lizard")
    a = compile_tree(e["requested"], e["pairs"])
    b = compile_tree(e["requested"], e["pairs"], sat_layers=False)
    assert a.stage_reached == b.stage_reached == "emit"
    assert json.dumps(a.fold, sort_keys=True) == json.dumps(b.fold,
                                                            sort_keys=True)


@pytest.mark.slow
def test_dense_lizard_sat_stage_emits_where_the_search_cannot():
    """The headline: dense `lizard` reaches emit.

    The shipped dense path spends 1052.0 s and returns
    `AssignFail(kind='budget', site=500000)`
    (`docs/superpowers/evidence/2026-09-27-core-in-loop/ab.json` arms[0]).
    """
    e = _entry("lizard")
    res = compile_tree(e["requested"], e["pairs"], dense=True,
                       sat_layers=True)
    assert res.stage_reached == "emit", res.failure
    assert res.verdict.kind == "CERTIFIED", res.verdict
    a = _audit(res.fold)
    assert a["interior"] == 366, a
    assert a["maekawa"] == 0 and a["kawasaki"] == 0, a
    assert a["arrangement"] == 0 and a["closure_bad_edges"] == 0, a
    print("WITNESS HASH (reported, not gated):",
          hashlib.sha256(json.dumps(res.fold["edges_assignment"]).encode()
                         ).hexdigest()[:16])


@pytest.mark.slow
def test_unsat_becomes_LayerFail_unsatisfiable_not_budget(monkeypatch):
    """UNSAT is a PROOF and must not wear a give-up kind.

    `"no_labelling"`'s docstring hedges "among those reachable" and
    `"budget"` says nothing about the crease set; `"unsatisfiable"` is the
    kind that asserts no labelling exists, so a caller must be able to tell
    them apart.
    """
    import box_pleat.compile as cm
    from box_pleat import sat_order

    def refuse(cons, slots, **kw):
        return sat_order.SatResult(
            sat=False, labels=None, relation=None,
            verdict=sat_order.SatVerdict(
                kind="REFUTED", violation=None, order_vars=len(cons.pairs),
                label_vars=len(slots), clauses=0, build_secs=0.0,
                solve_secs=0.0))

    monkeypatch.setattr(cm.sat_order, "solve", refuse)
    e = _entry("lizard")
    res = compile_tree(e["requested"], e["pairs"], sat_layers=True)
    assert res.stage_reached == "layers"
    assert isinstance(res.failure, LayerFail)
    assert res.failure.kind == "unsatisfiable", res.failure
    assert res.failure.checks == 0


@pytest.mark.slow
def test_oversize_becomes_LayerFail_oversize(monkeypatch):
    """`OVERSIZE` says nothing about the crease set and must not read as UNSAT."""
    import box_pleat.compile as cm
    from box_pleat import sat_order

    def oversize(cons, slots, **kw):
        return sat_order.SatResult(
            sat=False, labels=None, relation=None,
            verdict=sat_order.SatVerdict(
                kind="OVERSIZE", violation=None, order_vars=len(cons.pairs),
                label_vars=len(slots), clauses=0, build_secs=0.0,
                solve_secs=0.0))

    monkeypatch.setattr(cm.sat_order, "solve", oversize)
    e = _entry("lizard")
    res = compile_tree(e["requested"], e["pairs"], sat_layers=True)
    assert res.stage_reached == "layers"
    assert res.failure.kind == "oversize", res.failure
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python3 -m pytest tests/test_box_pleat_sat_stage.py -v
```

Expected: FAIL — `TypeError: compile_tree() got an unexpected keyword argument 'sat_layers'` on all but `test_sat_layers_off_is_byte_identical`, which fails the same way on its second call.

- [ ] **Step 3: Add the parameter and the import**

In `mcp_harness/box_pleat/compile.py`, add to the imports beside `from . import cores` (line 32):

```python
from . import sat_order
```

and add one line to `compile_tree`'s signature after `clause_prop_verify: bool = False,`:

```python
                 sat_layers: bool = False,
```

- [ ] **Step 4: Extend `_LAYER_KIND`'s neighbourhood and the `LayerFail` docstring**

`_LAYER_KIND` (`compile.py:43-44`) maps `AssignFail` kinds to `LayerFail` kinds and is **not** changed — the two new kinds do not come from `assign`. Add to the `LayerFail` docstring's bullet list, after the `"unfixable"` bullet:

```
    * "unsatisfiable" -- the SAT stage PROVED no M/V labelling of this crease
      set admits a valid layer order. This is the strict strengthening of
      "no_labelling": same claim, minus that kind's "among those reachable"
      hedge, and scoped to the F set `assign`'s first candidate fixed. Only
      this kind and "no_labelling" localise the defect in the packing, and
      only this one does so by proof -- see spec
      `2026-10-02-sat-layer-stage-design.md` section 6.
    * "oversize" -- the SAT stage's size guard refused the instance before
      deciding it. Like "budget", this says nothing whatever about the crease
      set: the clause count is cubic in arrangement-cell cover size and this
      instance exceeded the budget.
```

- [ ] **Step 5: Insert the stage**

In `compile.py`, replace the tail from `res.assignment = asg` through `res.fold = fold` (`:552-574`) with:

```python
    res.assignment = asg

    # The candidate `assign` accepted passed the per-candidate FILTER, which
    # only ever established "no contradiction found". Certify it once here:
    # a complete layer order must exist and satisfy every ADK clause before
    # this compiler claims the base stacks. Once, not per candidate -- see
    # `layers.certify`'s docstring for why.
    fold = to_fold(lay, asg)
    ff = flat_fold.flat_fold(fold)
    graph = graph_cell[0] if graph_cell else _layers.constraint_graph(ff)
    labels = {k: a for _, _, k, a in ff.shared_edges if a in ("M", "V")}

    if sat_layers:
        # `assign` ran with `global_check=None`, so `asg` is its FIRST
        # complete candidate and its labels are arbitrary. Only the geometry
        # is used: `layer_order.constraints_for` documents that everything
        # except `cons.direct` depends on the folded geometry alone, and the
        # folded positions are label-independent to exactly 0.0 (evidence
        # `2026-10-02-witness-identity-113` section 15.1). So the labelling is
        # decided here, completely, instead of searched for.
        sat = sat_order.solve(graph.cons, graph.slots)
        if not sat.sat:
            res.stage_reached = "layers"
            kind = ("unsatisfiable" if sat.verdict.kind == "REFUTED"
                    else "oversize")
            res.failure = LayerFail(kind, sat.verdict, counter[0])
            tick("layers")
            return res
        # Only edges already carrying M or V are rewritten, so the F set and
        # the boundary stay exactly as the pipeline produced them -- a
        # different F set would be a different crease set, and `sat`'s verdict
        # would not be about it.
        EV, EA = fold["edges_vertices"], fold["edges_assignment"]
        for i, (a, b) in enumerate(EV):
            if EA[i] in ("M", "V"):
                EA[i] = sat.labels[(min(a, b), max(a, b))]
        res.verdict = sat.verdict
        tick("layers")
        res.stage_reached = "emit"
        res.fold = fold
        tick("emit")
        return res

    res.verdict = _layers.certify(graph, labels, budget=certify_budget)
    if not dense and res.verdict.kind != "CERTIFIED":
        res.stage_reached = "layers"
        res.failure = LayerFail("uncertified", res.verdict, counter[0])
        tick("layers")
        return res
    tick("layers")

    res.stage_reached = "emit"
    res.fold = fold
    tick("emit")
    return res
```

- [ ] **Step 6: Pass `global_check=None` when `sat_layers` is set**

Find the `assign(...)` call (`compile.py:517`) and change its `global_check` argument so the CEGAR loop is never entered under the flag. It currently reads `global_check=_check,`; make it:

```python
                     global_check=None if sat_layers else _check,
```

`assign`'s loop reads `verdict = global_check(cand) if global_check is not None else None` and then `if verdict is None: return cand` (`assign.py:1230-1232`), so this returns the first complete candidate with no filtering and leaves `counter[0]` at 0.

- [ ] **Step 7: Run the new tests**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python3 -m pytest tests/test_box_pleat_sat_stage.py -v
```

Expected: **5 passed**. The dense test is the long one; budget 2–5 minutes for the file.

- [ ] **Step 8: Run every suite that covers the path you changed, in full**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python3 -m pytest tests/test_box_pleat_emit.py tests/test_box_pleat_layers.py tests/test_box_pleat_core_in_loop.py tests/test_box_pleat_cores.py tests/test_box_pleat_witness_identity.py tests/test_box_pleat_witness_record.py -v
```

Expected: all pass. Report the counts. A failure here means the `sat_layers=False` path is not byte-identical, which Step 5 is written to guarantee — stop and report rather than adjusting a test.

- [ ] **Step 9: Verify the standing invariants**

```bash
cd mcp_harness && grep -c box_pleat server.py; echo "exit=$?"
```

Expected: `0` then `exit=1` (zero matches; `grep -c` exits 1 on none, and the exit code is how you know the command ran).

```bash
cd mcp_harness && grep -n "except (ValueError, RuntimeError, KeyError)" box_pleat/compile.py
```

Expected: exactly two lines.

```bash
cd mcp_harness && grep -rn "print(\|warnings\.\|sys.stderr" box_pleat/; echo "exit=$?"
```

Expected: no output, `exit=1`.

```bash
cd mcp_harness && git diff --stat box_pleat/layers.py ../mcp_harness/layer_order.py ../mcp_harness/layer_certify.py box_pleat/cores.py
```

Expected: empty — all four untouched.

- [ ] **Step 10: Commit**

```bash
cd mcp_harness && git add box_pleat/compile.py tests/test_box_pleat_sat_stage.py && cd .. && git commit -F <scratch>/9681b5fb-8510-4f03-86c1-4e4b6d0a887a/scratchpad/t3-sat-msg.txt
```

`t3-sat-msg.txt`:

```
sat-stage: wire the complete query into compile_tree behind sat_layers

Under the flag the layer stage asks assign for its FIRST complete candidate
and uses it for GEOMETRY only -- global_check=None already returns it, so
assign needs no new mechanism and the CEGAR loop is never entered rather than
disabled. The labelling is then decided completely by one SAT call instead of
searched for over 500,000 nodes.

Two new LayerFail kinds. "unsatisfiable" is the strict strengthening of
"no_labelling" -- same claim minus that kind's "among those reachable" hedge,
scoped to the F set the first candidate fixed -- and it is the only kind that
localises the defect in the packing BY PROOF. "oversize" says nothing about
the crease set at all.

Only edges already carrying M or V are rewritten, so the F set and the
boundary stay as the pipeline produced them; a different F set would be a
different crease set and the verdict would not be about it.

checks is 0 and falls out correctly: counter[0] counts _check calls and
global_check is None.

With the flag off every path is byte-identical, pinned by a fold-equality
test and by six existing suites re-run in full.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

### Task 4: measure peak RSS, settle `max_clauses`, and run the evidence

**Files:**
- Create: `docs/superpowers/evidence/2026-10-02-sat-layer-stage/stage.py`
- Create: `docs/superpowers/evidence/2026-10-02-sat-layer-stage/stage.json`
- Create: `docs/superpowers/evidence/2026-10-02-sat-layer-stage/README.md`
- Possibly modify: `mcp_harness/box_pleat/sat_order.py` (`MAX_CLAUSES` only, and only if the measurement requires it)

**Interfaces:**
- Consumes: `compile_tree(..., dense=True, sat_layers=True)` from Task 3; `sat_order.MAX_CLAUSES`, `raw_triple_bound`.
- Produces: the evidence directory. Nothing consumes it.

**Why this is its own task.** Spec §5 commits to a measurement this plan cannot pre-empt: *"no peak-RSS figure appears in this spec because none has been measured. The plan must measure peak RSS for the dense `lizard` build and, if it exceeds ~4 GB, lower `max_clauses` to match."* That decision needs its own reviewer gate.

- [ ] **Step 1: Write the evidence script**

Create `docs/superpowers/evidence/2026-10-02-sat-layer-stage/stage.py`:

```python
"""The SAT layer stage, end to end on dense and sparse `lizard`.

Spec: `../../specs/2026-10-02-sat-layer-stage-design.md`.

Records the three things the spec left to measurement: peak RSS for the
9.7M-clause build (which decides whether `MAX_CLAUSES` must come down), the
stage's wall clock against the shipped dense path's 1052.0 s
(`../2026-09-27-core-in-loop/ab.json` arms[0].secs), and whether the emitted
fold passes `cp_audit`.

Prints no verdict until every figure is in hand.
"""
import json
import resource
import sys
import time

sys.path.insert(0, ".")

import cp_audit
from box_pleat import sat_order
from box_pleat.compile import compile_tree

RULE6 = ("../docs/superpowers/evidence/2026-09-08-vlm-tree-authoring"
         "/data/rule6_serve.json")


def peak_rss_mb():
    """macOS reports ru_maxrss in BYTES; Linux in kilobytes."""
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return raw / (1024 * 1024) if sys.platform == "darwin" else raw / 1024


def audit(fold):
    r = cp_audit.audit_fold(fold)
    return {
        "interior": len(r.vertices),
        "maekawa": sum(1 for v in r.vertices if abs(v.m - v.v) != 2),
        "kawasaki": sum(1 for v in r.vertices
                        if abs(v.kawasaki_residual_deg) > r.kawasaki_tol_deg),
        "arrangement": sum(1 for v in r.vertices if not v.arrangement_ok),
        "closure_bad_edges": r.closure_bad_edges,
        "closure_max_error": r.closure_max_error,
    }


def main(out_path):
    with open(RULE6) as fh:
        e = next(x for x in json.load(fh) if x["subject"] == "lizard")
    rec = {"subject": "lizard", "max_clauses": sat_order.MAX_CLAUSES,
           "max_raw_triples": sat_order.MAX_RAW_TRIPLES,
           "rss_before_mb": round(peak_rss_mb(), 1)}

    for tag, dense in (("sparse", False), ("dense", True)):
        t0 = time.perf_counter()
        res = compile_tree(e["requested"], e["pairs"], dense=dense,
                           sat_layers=True)
        secs = round(time.perf_counter() - t0, 1)
        row = {"stage_reached": res.stage_reached, "secs": secs,
               "peak_rss_mb": round(peak_rss_mb(), 1),
               "failure": repr(res.failure)}
        if res.verdict is not None:
            row["verdict"] = {
                "kind": res.verdict.kind,
                "order_vars": getattr(res.verdict, "order_vars", None),
                "label_vars": getattr(res.verdict, "label_vars", None),
                "clauses": getattr(res.verdict, "clauses", None),
                "build_secs": getattr(res.verdict, "build_secs", None),
                "solve_secs": getattr(res.verdict, "solve_secs", None),
            }
        if res.fold is not None:
            row["audit"] = audit(res.fold)
            row["fold"] = {"vertices": len(res.fold["vertices_coords"]),
                           "edges": len(res.fold["edges_vertices"])}
        rec[tag] = row
        print(f"{tag}: stage={row['stage_reached']} secs={secs} "
              f"peak_rss={row['peak_rss_mb']}MB "
              f"verdict={row.get('verdict', {}).get('kind')}", flush=True)
        if "audit" in row:
            print(f"   audit {row['audit']}", flush=True)

    with open(out_path, "w") as fh:
        json.dump(rec, fh, indent=1, sort_keys=True)
    print(f"wrote {out_path}")

    d = rec["dense"]
    print()
    if d["stage_reached"] != "emit":
        print(f"VERDICT: the dense stage did NOT reach emit "
              f"({d['stage_reached']}, {d['failure']}). Report this; it "
              f"contradicts evidence 2026-10-02-witness-identity-113 section 15.")
    elif d["peak_rss_mb"] > 4096:
        print(f"VERDICT: EMITS, but peak RSS is {d['peak_rss_mb']}MB, over the "
              f"spec's ~4 GB line. MAX_CLAUSES must come down to match -- "
              f"spec section 5 requires the default to be derived from this "
              f"measurement.")
    else:
        a = d["audit"]
        print(f"VERDICT: EMITS in {d['secs']}s at {d['peak_rss_mb']}MB peak "
              f"RSS, against the shipped dense path's 1052.0s with no answer "
              f"(../2026-09-27-core-in-loop/ab.json arms[0]). cp_audit "
              f"maekawa={a['maekawa']} kawasaki={a['kawasaki']} "
              f"arrangement={a['arrangement']} of {a['interior']} interior "
              f"vertices. MAX_CLAUSES stands at "
              f"{rec['max_clauses']:,}.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: stage.py <out.json>")
    main(sys.argv[1])
```

- [ ] **Step 2: Run it**

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -u ../docs/superpowers/evidence/2026-10-02-sat-layer-stage/stage.py ../docs/superpowers/evidence/2026-10-02-sat-layer-stage/stage.json
```

Expected: both rows reach `emit` with `verdict=CERTIFIED`, dense in roughly 15–40 s. Report the two `peak_rss_mb` figures verbatim.

- [ ] **Step 3: Settle `MAX_CLAUSES` against the measurement**

If dense `peak_rss_mb` ≤ 4096, change nothing and say so in the report.

If it exceeds 4096, lower `MAX_CLAUSES` in `mcp_harness/box_pleat/sat_order.py` so that the measured clause count sits at roughly half the new ceiling, and replace the constant's comment with the measured figure:

```python
#: The streaming ceiling. Dense `lizard` emits 9,678,554 clauses at a MEASURED
#: peak RSS of <X> MB (evidence `2026-10-02-sat-layer-stage/stage.json`), so
#: this ceiling is set from that measurement rather than from a guess.
MAX_CLAUSES = <value>
```

Then re-run Task 1 and Task 2's unit file to confirm nothing depended on the old value:

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python3 -m pytest tests/test_box_pleat_sat_order.py -v
```

Expected: **20 passed**.

- [ ] **Step 4: Write the README**

Create `docs/superpowers/evidence/2026-10-02-sat-layer-stage/README.md` containing, in this order:

1. **The headline**: dense `lizard`'s stage result and wall clock, against the shipped path's **1052.0 s** returning `AssignFail(kind='budget', site=500000)` — attributed inline to `../2026-09-27-core-in-loop/ab.json` `arms[0]`.
2. **The reproduction command** verbatim, plus the run date, commit SHA and exit status, stated as the README's own record because `stage.py` writes none of them into the JSON.
3. **The instance**: order vars, label vars, clauses, `raw_triple_bound`, build and solve seconds — every one from `stage.json`.
4. **Peak RSS, and the `MAX_CLAUSES` decision** it drove, including the case where nothing changed.
5. **`cp_audit` on the emitted fold**, all five counters, with the interior-vertex population named.
6. **What this does not establish**: the F set is fixed by `assign`'s first candidate; `AREA_EPS` was measured inert on dense `lizard` only (`../2026-10-02-witness-identity-113/README.md` §16) and the prior six-subject study found subjects that straddle; one subject; and `sat_layers` ships **off**.

**Prose rules, each of which this project has violated before:** attribute every figure from another evidence directory inline **on every appearance**; mark arithmetic as *derived* and show it; never state a row count as a subject count; a share with a zero denominator is **undefined**, not 100%.

- [ ] **Step 5: Verify every README figure against `stage.json`**

For each number, name its source — a JSON key, another evidence directory with its path, or a marked derivation. Remove any figure you cannot source rather than leaving it uncited.

- [ ] **Step 6: Commit**

```bash
git add docs/superpowers/evidence/2026-10-02-sat-layer-stage/ mcp_harness/box_pleat/sat_order.py && git commit -F <scratch>/9681b5fb-8510-4f03-86c1-4e4b6d0a887a/scratchpad/t4-sat-msg.txt
```

`t4-sat-msg.txt` — fill `<SECS>` and `<RSS>` from the run:

```
evidence: the SAT layer stage emits dense lizard in <SECS>s at <RSS>MB

The shipped dense path spends 1052.0 s and returns
AssignFail(kind='budget', site=500000)
(../2026-09-27-core-in-loop/ab.json arms[0]). The stage decides the same
crease set and emits.

Peak RSS is the figure the spec deliberately left unmeasured, because
MAX_CLAUSES had to be set from a measurement rather than a guess. Recorded
here, with the decision it drove.

cp_audit on the emitted fold is reported in full, with its interior-vertex
population named rather than implied.

sat_layers still ships off.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

## Self-Review

**1. Spec coverage.**

| spec section | task |
|---|---|
| §0 prior art | recorded in the spec; `layer_order`/`layer_certify`/`cores`/`layers` untouched, checked in Task 3 Step 9 |
| §3 flow | Task 3 Steps 5–6 |
| §3.1 `global_check=None` | Task 3 Step 6 |
| §3.2 geometry-only scaffold | Task 3 Step 5's comment; rests on evidence §15.1 |
| §3.3 the four translations | Task 1 Step 3, each quoting `_satisfied` |
| §4 verdict from `verify`; `SatVerdict` not `Verdict` | Task 2 Step 3 |
| §5 two-stage guard | Task 1 (`raw_triple_bound`, streaming counter), Task 2 (`solve`'s stage 1) |
| §5 peak RSS → `MAX_CLAUSES` | **Task 4 Steps 2–3** |
| §6 taxonomy, all four rows | Task 3 Steps 4–5; tests in Task 3 Step 1 |
| §6 `verify`-rejects raises | Task 2 Step 3, test in Task 2 Step 1 |
| §7 interfaces | Task 1 and Task 2 Interfaces blocks |
| §8.1 exhaustive equivalence | Task 1 Step 1 |
| §8.2 both guard stages | Task 2 Step 1 |
| §8.3 wiring table, all five rows | Task 3 Step 1 |
| §8.4 properties gate, identity reported | Task 3 Step 1's docstring and the two witness-hash prints |
| §8.5 five mutations | Task 1 Step 5, **re-assigned to the test that can actually kill each** |
| §9 limits | Task 4 Step 4 item 6 |
| §10 out of scope | no task flips a default, iterates F sets, extracts an UNSAT core, or removes `assign` |

**No gaps.**

**2. Placeholder scan.** No TBD/TODO. The `<SECS>`/`<RSS>`/`<X>`/`<value>` placeholders in Task 4 are values that cannot exist before the measurement, and each step says where they come from. Task 4 Step 3 is conditional on a measurement, not a deferred decision — both branches are written out.

**3. Type consistency.** `EncodeStats(order_var, label_var, clauses, families)` is defined in Task 1 Step 3 and its fields are read in Task 1's `_encode`/`_models_over` and Task 2's `solve`. `SatVerdict`'s seven fields are constructed in Task 2 and read in Task 3's tests and Task 4's script. `SatResult(sat, labels, relation, verdict)` likewise. `encode(cons, slots, sink, *, max_clauses)` has the same arity at all four call sites. `solve(cons, slots, *, max_raw_triples, max_clauses, solver)` matches its monkeypatched stand-ins in Task 3, which accept `**kw`.

**Two issues found and fixed inline while reviewing:**

- Task 2's `test_solve_reports_unsat_as_refuted_with_no_model` originally built a `cons` with `direct` units and expected UNSAT. But `direct` is **not encoded** — the labels are variables, which is the whole point — so the instance is satisfiable. The test now asserts that explicitly and forces the cyclic state through assumptions instead, which is what actually exercises transitivity.
- §8.5's mutation table pointed all five mutations at the exhaustive equivalence check. Mutations 4 and 5 (the label biconditional) **cannot** be caught there, because the label variables are free and adapt to the order variables. The table now names `test_label_link_forces_the_order_variable` for those two, and the plan says to report rather than re-assign if that turns out to be wrong.
