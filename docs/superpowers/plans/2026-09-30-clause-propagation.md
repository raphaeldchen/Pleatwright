# Descent-time Clause Propagation Instrument — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure what share of dense `assign()`'s search nodes a one-step propagator over the learned no-good clauses would have refuted outright, and report it against verdict bands fixed before the run.

**Architecture:** A new `ClauseIndex` keeps GRASP-style exact per-clause counters (`n_agree` / `n_contra`) updated on every change to `value`, so at every node it knows which clauses are live, unit or conflicting — where today's `hits_nogood()` can see only the conflicting case. At each unit clause it probes the one free variable's remaining values against the local laws; if all are refused, the node is provably dead. The index is wired into `assign()` behind two inert-by-default parameters and driven by a standalone evidence runner; no production behaviour changes.

**Tech Stack:** Python 3.14, pytest, the existing `mcp_harness/box_pleat/` package. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-09-30-clause-propagation-design.md`. Read it before Task 1; every section reference below points into it.

---

## Global Constraints

- **Run every command from the worktree root** `<repo>`. Do NOT `cd` to the original repository root.
- **Python is `../.venv/bin/python3` invoked from inside `mcp_harness`** (equivalently `.venv/bin/python3` from the worktree root). Tests need `PYTHONPATH=.` set from inside `mcp_harness`.
- **Never pass `--timeout` to pytest.** The venv has no `pytest-timeout`; passing it exits 4.
- **Never run `pytest tests/`** — 5,167 tests, over 3 hours. Always name files explicitly.
- **Run the FULL named test files, never a `-k` filtered subset.**
- **Do NOT modify `mcp_harness/box_pleat/layer_order.py`.** `mv_symmetrize` on the serve path shares it.
- **`grep -c box_pleat mcp_harness/server.py` must stay 0.**
- **Do NOT widen `compile.py`'s `except (ValueError, RuntimeError, KeyError)`.**
- **Never use bare `git stash` / `git stash pop`.** The stash stack is shared with the main checkout and every other worktree. Use a temporary WIP commit instead.
- **Never nest a heredoc inside another heredoc.** zsh terminates the OUTER one at the inner delimiter. Write the inner script to a file in the scratchpad and run it by path. Hit while writing this plan.
- **Write commit messages to a file and use `git commit -F <file>`.** zsh mangles heredocs containing backticks. Put the file in the session scratchpad, not the repo.
- **Every commit message ends with:** `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`
- **No production behaviour may change.** Both new parameters are inert when unset. Any arm that does not ask for the instrument must pay nothing.
- **Never use tardigrade / water bear as a test subject** — owner instruction.
- **Figures are read back from the artifact after the process exits**, never transcribed from a log watched while it ran.

---

## File Structure

| file | responsibility |
|---|---|
| `mcp_harness/box_pleat/clause_index.py` (**new**) | `ClauseIndexError`, `ClauseIndex`. Owns every counter, the unit/live/conflicting classification, the cascade probe, the per-node aggregation, and the from-scratch recompute used by the verify mode. Nothing else knows how a clause state is computed. |
| `mcp_harness/box_pleat/assign.py` (**modify**) | Two new inert parameters; five hook sites; one guard. Gains roughly 20 lines and no new logic — all measurement lives in `clause_index.py`. |
| `mcp_harness/box_pleat/compile.py` (**modify**) | Threads the two new parameters. Nothing else. |
| `mcp_harness/tests/test_box_pleat_clause_index.py` (**new**) | Counters and classification, on hand-built fixtures. Mutations 1–5. |
| `mcp_harness/tests/test_box_pleat_clause_probe.py` (**new**) | The cascade probe, on hand-built fixtures with injected `prefer` / `touching` / `feasible`. Mutations 6–7. |
| `mcp_harness/tests/test_box_pleat_clause_prop_wiring.py` (**new**) | The wiring: the verify mode on a real compile, the inertness guarantee, the `clause_prop_verify` misuse guard. |
| `docs/superpowers/evidence/2026-09-30-clause-propagation/probe.py` (**new**) | The runner: arms, identity gate, cost cap, artifact. |
| `docs/superpowers/evidence/2026-09-30-clause-propagation/probe.json` (**new**) | The measurement, with date, commit and exit status recorded in the artifact itself. |
| `docs/superpowers/evidence/2026-09-30-clause-propagation/README.md` (**new**) | The verdict band reached, every figure read back from `probe.json`, plus "what this does NOT establish". |

**Why the measurement logic lives in `clause_index.py`, not `assign.py`:** `assign.py` is 1,240 lines and is the file this project most fears touching. Keeping the per-node aggregation inside `ClauseIndex.observe()` makes `assign.py`'s hook a single line, and makes every reported quantity unit-testable on a hand-built fixture without compiling anything.

---

## Read this before Task 1: the three traps

Copied from spec sections 6.1–6.3 because they decide the code, and an implementer who reads only their own task will otherwise reintroduce a bug this project has already paid for.

**Trap 1 — do NOT copy `VertexIndex`'s `was_bound` guard.** `retry()` (`mcp_harness/box_pleat/assign.py:1099`) reassigns an **already-bound** variable on the CEGAR path: the main loop calls `retry()` right after `nogoods.append(clause)` **without pushing a frame**, so the deepest frame's variable is still bound from the candidate just rejected and `value[var] = vals[i]` overwrites it. `VertexIndex` counts free-vs-bound, which does not change on a reassignment, so it correctly **skips** (`assign.py:1117`, `if vx is not None and not was_bound`). `ClauseIndex` counts *agree-vs-contra*, which **does** change. Skipping here is silently wrong. `ClauseIndex` needs a real `rebind(var, old, new)`.

**Trap 2 — clauses are born conflicting.** At `nogoods.append(clause)` (`assign.py:1214`) every variable in the clause is bound and agrees, so the clause enters with `n_agree == size`, `n_contra == 0`. `add_clause` must compute its counters against the live `value`, never assume a fresh state.

**Trap 3 — the probe must not mutate search state.** It sets a value, calls `feasible`, and must restore under `try/finally`. It must **not** touch the live `VertexIndex`. Verified precondition: `feasible` → `violation` (`assign.py:848`) reads `ring`, `lab_of`, `var_of` and `value` only — it never consults `vx` — so a probe that restores `value` leaves the search bit-identical.

---

### Task 1: `ClauseIndex` — counters and classification

**Files:**
- Create: `mcp_harness/box_pleat/clause_index.py`
- Test: `mcp_harness/tests/test_box_pleat_clause_index.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces, relied on by Tasks 2 and 3:
  - `ClauseIndexError(Exception)`
  - `ClauseIndex(value: dict, prefer: callable, touching: dict, feasible: callable, out: dict)`
  - `add_clause(clause: dict) -> int` (the cid)
  - `bind(var, val) -> None`
  - `rebind(var, old, new) -> None`
  - `unbind(var, old) -> None`
  - `free_var_of(cid) -> tuple[var, forbidden_value]`
  - `snapshot() -> dict` with keys `n_agree`, `n_contra`, `size`, `live`, `unit`, `conflicting`
  - `recompute() -> dict` — same keys, rebuilt from scratch
  - attributes `live: set`, `unit: set`, `conflicting: set`, `clauses: list[dict]`
  - `probe`, `observe`, `verify`, `report` arrive in Tasks 2 and 3; do not stub them here.

- [ ] **Step 1: Write the failing tests**

Create `mcp_harness/tests/test_box_pleat_clause_index.py`:

```python
"""Per-clause counters, tested without compiling anything.

Spec: `docs/superpowers/specs/2026-09-30-clause-propagation-design.md`.

Every fixture is hand-built. That is deliberate. The behaviour that decides
whether this instrument is sound -- that a REASSIGNMENT moves a variable
between `n_agree` and `n_contra` (spec 6.1, Trap 1) -- happens on a real
subject only on the CEGAR path, which a borrowed fixture might never reach.
`test_trap1_*` builds it directly.
"""
import pytest

from box_pleat.clause_index import ClauseIndex, ClauseIndexError


def _ix(value=None):
    """A ClauseIndex over a live `value` dict the test controls directly.

    `prefer`, `touching` and `feasible` are unused by Task 1's surface and
    are given inert placeholders; Task 2's probe tests inject real ones.
    """
    value = {} if value is None else value
    return value, ClauseIndex(value, lambda var: ["M", "V"], {},
                              lambda w: True, {})


def test_empty_index_has_no_clauses():
    _, ix = _ix()
    assert ix.clauses == []
    assert ix.live == set()
    assert ix.unit == set()
    assert ix.conflicting == set()


def test_clause_added_with_nothing_bound_is_live_not_unit():
    _, ix = _ix()
    cid = ix.add_clause({1: "M", 2: "V", 3: "M"})
    assert cid == 0
    assert ix.n_agree[cid] == 0
    assert ix.n_contra[cid] == 0
    assert ix.size[cid] == 3
    assert ix.live == {0}
    assert ix.unit == set()
    assert ix.conflicting == set()


def test_size_two_clause_goes_unit_on_one_agreeing_bind():
    value, ix = _ix()
    ix.add_clause({1: "M", 2: "V"})
    value[1] = "M"
    ix.bind(1, "M")
    assert ix.n_agree[0] == 1
    assert ix.unit == {0}
    assert ix.conflicting == set()


def test_agreeing_bind_on_last_variable_makes_it_conflicting_not_unit():
    value, ix = _ix()
    ix.add_clause({1: "M", 2: "V"})
    value[1] = "M"
    ix.bind(1, "M")
    value[2] = "V"
    ix.bind(2, "V")
    assert ix.n_agree[0] == 2
    assert ix.conflicting == {0}
    assert ix.unit == set(), "a conflicting clause is not unit"


def test_contradicting_bind_kills_the_clause():
    value, ix = _ix()
    ix.add_clause({1: "M", 2: "V"})
    value[1] = "V"                      # the clause forbids M at 1
    ix.bind(1, "V")
    assert ix.n_contra[0] == 1
    assert ix.live == set(), "n_contra > 0 means dead"
    assert ix.unit == set()


def test_dead_clause_stays_dead_when_a_second_variable_agrees():
    value, ix = _ix()
    ix.add_clause({1: "M", 2: "V", 3: "M"})
    value[1] = "V"
    ix.bind(1, "V")
    value[2] = "V"
    ix.bind(2, "V")
    assert ix.n_agree[0] == 1
    assert ix.n_contra[0] == 1
    assert ix.live == set()
    assert ix.unit == set(), "size-1-free but dead: must never be unit"


def test_unbind_reverses_a_bind_exactly():
    value, ix = _ix()
    ix.add_clause({1: "M", 2: "V", 3: "M"})
    before = ix.snapshot()
    value[1] = "M"
    ix.bind(1, "M")
    del value[1]
    ix.unbind(1, "M")
    assert ix.snapshot() == before


def test_unbind_reverses_a_contradicting_bind_exactly():
    value, ix = _ix()
    ix.add_clause({1: "M", 2: "V", 3: "M"})
    before = ix.snapshot()
    value[1] = "V"
    ix.bind(1, "V")
    del value[1]
    ix.unbind(1, "V")
    assert ix.snapshot() == before


def test_trap1_rebind_moves_the_variable_between_counters():
    """Spec 6.1. The CEGAR path overwrites a bound variable in place."""
    value, ix = _ix()
    ix.add_clause({1: "M", 2: "V"})
    value[1] = "M"
    ix.bind(1, "M")
    assert (ix.n_agree[0], ix.n_contra[0]) == (1, 0)
    value[1] = "V"                      # reassignment, no unbind
    ix.rebind(1, "M", "V")
    assert (ix.n_agree[0], ix.n_contra[0]) == (0, 1)
    assert ix.live == set(), "the rebind killed the clause"


def test_trap1_rebind_matches_unbind_then_bind():
    """A rebind must be observationally identical to the pair it replaces."""
    va, ia = _ix()
    ib_value, ib = _ix()
    for ix, value in ((ia, va), (ib, ib_value)):
        ix.add_clause({1: "M", 2: "V", 3: "M"})
        ix.add_clause({1: "V", 4: "M"})
        value[1] = "M"
        ix.bind(1, "M")
    va[1] = "V"
    ia.rebind(1, "M", "V")
    del ib_value[1]
    ib.unbind(1, "M")
    ib_value[1] = "V"
    ib.bind(1, "V")
    assert ia.snapshot() == ib.snapshot()


def test_rebind_to_the_same_value_does_no_counter_work():
    """The `old == new` early return is an OPTIMISATION, not correctness.

    `unbind` then `bind` of the same value restores every counter exactly, so
    the snapshot cannot tell the two apart -- asserting on it would pass with
    the guard deleted. What the guard buys is skipped work, so that is what is
    pinned: no clause is reclassified.
    """
    value, ix = _ix()
    ix.add_clause({1: "M", 2: "V"})
    value[1] = "M"
    ix.bind(1, "M")
    before = ix.snapshot()
    reclassified = []
    # Fail LOUDLY if `_reclassify` is renamed or inlined: the shadow below
    # would then bind nothing and this test would pass without pinning the
    # guard at all.
    assert hasattr(type(ix), "_reclassify")
    real = ix._reclassify
    ix._reclassify = lambda cid: (reclassified.append(cid), real(cid))
    ix.rebind(1, "M", "M")
    assert reclassified == []
    assert ix.snapshot() == before


def test_trap2_clause_added_while_bound_is_born_conflicting():
    """Spec 6.2. Every clause in `assign` is appended at a full binding."""
    value = {1: "M", 2: "V"}
    _, ix = _ix(value)
    cid = ix.add_clause({1: "M", 2: "V"})
    assert ix.n_agree[cid] == 2
    assert ix.n_contra[cid] == 0
    assert ix.conflicting == {cid}
    assert ix.unit == set()


def test_trap2_clause_added_with_one_variable_free_is_born_unit():
    value = {1: "M"}
    _, ix = _ix(value)
    cid = ix.add_clause({1: "M", 2: "V"})
    assert ix.n_agree[cid] == 1
    assert ix.unit == {cid}


def test_trap2_clause_added_against_a_contradicting_binding_is_born_dead():
    value = {1: "V"}
    _, ix = _ix(value)
    cid = ix.add_clause({1: "M", 2: "V"})
    assert ix.n_contra[cid] == 1
    assert ix.live == set()


def test_one_variable_in_several_clauses_updates_all_of_them():
    value, ix = _ix()
    ix.add_clause({1: "M", 2: "V"})
    ix.add_clause({1: "M", 3: "V", 4: "M"})
    ix.add_clause({1: "V", 5: "M"})
    value[1] = "M"
    ix.bind(1, "M")
    assert ix.unit == {0}, "only the size-2 clause has one free left"
    assert ix.live == {0, 1}, "clause 2 forbids V at 1, so M kills it"
    assert ix.n_agree[1] == 1
    assert ix.n_contra[2] == 1


def test_bind_of_a_variable_in_no_clause_is_a_no_op():
    value, ix = _ix()
    ix.add_clause({1: "M", 2: "V"})
    before = ix.snapshot()
    value[99] = "M"
    ix.bind(99, "M")
    assert ix.snapshot() == before


def test_free_var_of_returns_the_single_free_variable_and_its_forbidden_value():
    value, ix = _ix()
    cid = ix.add_clause({1: "M", 2: "V", 3: "F"})
    for var, val in ((1, "M"), (3, "F")):
        value[var] = val
        ix.bind(var, val)
    assert ix.unit == {cid}
    assert ix.free_var_of(cid) == (2, "V")


def test_free_var_of_refuses_a_clause_that_is_not_unit():
    _, ix = _ix()
    cid = ix.add_clause({1: "M", 2: "V"})
    with pytest.raises(ClauseIndexError, match="not unit"):
        ix.free_var_of(cid)


def test_add_clause_refuses_an_empty_clause():
    _, ix = _ix()
    with pytest.raises(ClauseIndexError, match="empty"):
        ix.add_clause({})


def test_recompute_agrees_with_the_maintained_counters():
    value, ix = _ix()
    ix.add_clause({1: "M", 2: "V", 3: "M"})
    ix.add_clause({2: "M", 4: "V"})
    for var, val in ((1, "M"), (2, "V"), (4, "V")):
        value[var] = val
        ix.bind(var, val)
    assert ix.snapshot() == ix.recompute()


def test_recompute_catches_a_hand_corrupted_counter():
    """The verify mode's premise: recompute must DISAGREE when state is wrong."""
    value, ix = _ix()
    ix.add_clause({1: "M", 2: "V"})
    value[1] = "M"
    ix.bind(1, "M")
    ix.n_agree[0] = 0                   # corrupt it by hand
    assert ix.snapshot() != ix.recompute()


def test_recompute_catches_a_hand_corrupted_size():
    """`recompute` must rebuild `size` from the clause, not copy it, or a
    corrupted entry is invisible to the very reference built to expose it."""
    _, ix = _ix()
    ix.add_clause({1: "M", 2: "V"})
    ix.size[0] = 99                     # corrupt it by hand
    assert ix.snapshot() != ix.recompute()


@pytest.mark.parametrize("stray, counter", [("M", "n_agree"), ("V", "n_contra")])
def test_stray_unbind_raises_instead_of_drifting_negative(stray, counter):
    """An unbind of a variable that was never bound must not reach -1.

    `assign.py` has two separate unbind sites in `retry`, and its own comment
    names this hazard. The clause forbids M at variable 1, so `stray="M"`
    would underflow `n_agree` and `stray="V"` would underflow `n_contra`.
    """
    _, ix = _ix()
    ix.add_clause({1: "M", 2: "V"})
    before = ix.snapshot()
    with pytest.raises(ClauseIndexError,
                       match=rf"clause 0.*{counter}\[0\] is 0"):
        ix.unbind(1, stray)
    assert ix.snapshot() == before, "the counter must not have moved"


def test_rebind_between_two_contradicting_values_stays_dead():
    """Neither the old nor the new value is the forbidden one, so the variable
    must stay in `n_contra` throughout. Every other fixture rebinds M <-> V."""
    value, ix = _ix()
    ix.add_clause({1: "M", 2: "V"})
    value[1] = "V"
    ix.bind(1, "V")
    assert (ix.n_agree[0], ix.n_contra[0]) == (0, 1)
    value[1] = "F"
    ix.rebind(1, "V", "F")
    assert (ix.n_agree[0], ix.n_contra[0]) == (0, 1)
    assert ix.live == set()
    assert ix.snapshot() == ix.recompute()


def test_clause_with_two_contradictions_stays_dead_after_one_is_unbound():
    """`_reclassify` must test `n_contra > 0`, not `n_contra == 1`."""
    value, ix = _ix()
    ix.add_clause({1: "M", 2: "V", 3: "M"})
    for var, val in ((1, "V"), (2, "M")):
        value[var] = val
        ix.bind(var, val)
    assert ix.n_contra[0] == 2
    assert ix.live == set()
    del value[1]
    ix.unbind(1, "V")
    assert ix.n_contra[0] == 1
    assert ix.live == set(), "one contradiction is still a contradiction"
    assert ix.snapshot() == ix.recompute()
    del value[2]
    ix.unbind(2, "M")
    assert ix.live == {0}, "only now is the clause a threat again"


def test_size_one_clause_is_live_and_unit_with_nothing_bound():
    """k == 1: the single variable is the free one, so `a == k - 1 == 0`."""
    _, ix = _ix()
    cid = ix.add_clause({7: "F"})
    assert ix.live == {cid}
    assert ix.unit == {cid}
    assert ix.conflicting == set()
    assert ix.free_var_of(cid) == (7, "F")


def test_size_one_clause_is_conflicting_not_unit_after_an_agreeing_bind():
    value, ix = _ix()
    cid = ix.add_clause({7: "F"})
    value[7] = "F"
    ix.bind(7, "F")
    assert ix.conflicting == {cid}
    assert ix.unit == set()
    assert ix.live == {cid}
    assert ix.snapshot() == ix.recompute()
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -m pytest tests/test_box_pleat_clause_index.py -v
```

Expected: collection error, `ModuleNotFoundError: No module named 'box_pleat.clause_index'`.

- [ ] **Step 3: Write the implementation**

Create `mcp_harness/box_pleat/clause_index.py`:

```python
"""Exact per-clause counters over the CEGAR loop's learned no-goods.

Spec: `docs/superpowers/specs/2026-09-30-clause-propagation-design.md`.

WHY THIS EXISTS. `assign`'s `hits_nogood()` is
`any(all(value.get(var) == val for var, val in g.items()) for g in nogoods)`.
A clause with ANY unbound variable reads `None` for it, fails the `all`, and
is inert -- so a clause can only ever fire at the instant its LAST variable is
bound to the forbidden value. The solver therefore has clause learning and NO
propagation: a 5-variable clause with 4 variables already at their forbidden
values has eliminated one value of the fifth, and nothing notices.

This class makes every intermediate state visible. Per clause it keeps
`n_agree` (variables bound to the value the clause forbids) and `n_contra`
(bound to some other value), from which:

    dead        n_contra > 0                  already satisfied; can never fire
    live        n_contra == 0                 still a threat
    unit        n_contra == 0, n_agree == k-1 one free variable, one value gone
    conflicting n_contra == 0, n_agree == k   what hits_nogood() already sees

PRIOR ART. This is GRASP's counter-based BCP (Marques-Silva & Sakallah,
1996/99): one exact counter per clause, updated on every assignment. Chaff
(Moskewicz et al., DAC 2001) replaced counters with two watched literals
precisely BECAUSE counters cost more per assignment -- and that trade is
consciously rejected here. Two watches tell you lazily WHETHER one clause is
unit; this needs the eager COUNT of unit clauses at every node, which a
2-watch scheme structurally cannot report. The counter cost is the
measurement.

NOT A FIX. Nothing here changes the search. Every figure it produces is a
LOWER bound on what a propagator would buy, because only clauses already unit
are considered and the cascade (Task 2) is one step, never a fixpoint.
"""
from __future__ import annotations

#: Distinguishes "absent from `value`" from any real label. A sentinel rather
#: than `None` on purpose: conflating the two IS the defect this instrument
#: exists to measure, and reusing `None` here would reproduce it one layer
#: down.
_UNBOUND = object()


class ClauseIndexError(Exception):
    """An invariant the counters depend on does not hold.

    Deliberately subclasses `Exception` and NOT `ValueError`/`RuntimeError`/
    `KeyError`: those three are what `compile_tree`'s
    `except (ValueError, RuntimeError, KeyError)` around its `assign(...)`
    call folds into an indistinguishable `AssignFail("error", ...)`. A broken
    instrument must never be mistaken for an ordinary refusal, so this
    propagates out uncaught -- matching `VertexIndexError` and
    `cores.CoreExtractionError` for the same reason.
    """


class ClauseIndex:
    """Clause state, maintained in O(clauses containing the bound variable).

    Hand it `assign`'s live `value` dict plus the three things the cascade
    probe needs (`prefer`, `touching`, `feasible`) and the out-dict the
    per-node aggregates are written into.

    `bind` / `rebind` / `unbind` must be called for EVERY change to `value`.
    In `assign.py` those are THREE sites inside `retry` -- the bind or REBIND
    at its `value[var] = vals[i]`, the unbind at its `del value[var]`, and the
    unbind at its `value.pop(popped, None)` on a frame pop -- and there is a
    fourth hook that is NOT one of them and NOT in `retry`: `add_clause`, at
    the main loop's `nogoods.append(clause)`. Stated this way because an
    earlier wording said "four sites, all inside `retry`" and then named one
    in the main loop, which sends a reader hunting inside `retry` for a fourth
    that does not exist.
    Symbol names rather than line numbers deliberately: a rotted line number
    sends a reader checking the correctness argument to the wrong place
    silently.

    WHY `rebind` EXISTS AND WHY `VertexIndex`'s GUARD MUST NOT BE COPIED.
    The guard is NOT in `vertex_index.py`, which only supplies `bind` /
    `unbind`. It is at the call site: inside `retry()` in `assign.py`,
    `was_bound = var in value` followed by
    `if vx is not None and not was_bound: vx.bind(var)` (`assign.py:1115-1117`
    when written; search for `was_bound`). Read it there, not here.

    `retry()` is called right after `nogoods.append(clause)` WITHOUT a frame
    being pushed, so the deepest frame's variable is still bound from the
    candidate just rejected and `value[var] = vals[i]` REASSIGNS it.
    `VertexIndex` counts free-vs-bound, which does not change on a
    reassignment, so it correctly SKIPS. This class counts agree-vs-contra,
    which DOES change. Skipping here is silently wrong, and the skip is the
    bug `_verify_index` caught in 21 s during the vertex-index slice.
    """

    def __init__(self, value, prefer, touching, feasible, out):
        self._value = value
        self._prefer = prefer
        self._touching = touching
        self._feasible = feasible
        self._out = out

        #: cid -> the clause dict itself, so `free_var_of` can walk it.
        #: 113 clauses on the widest measured arm, so the copy is free.
        self.clauses: list = []
        #: var -> [(cid, forbidden_value), ...]. A bind touches only this
        #: list, which is what keeps wide clauses cheap: 113 x 202 = 22,826
        #: clause-variable incidences over ~5,140 variables is about 4.4
        #: counter updates per bind.
        self.var_to_clauses: dict = {}
        self.n_agree: list = []
        self.n_contra: list = []
        self.size: list = []
        #: Maintained rather than derived. `len(self.live)` is read once per
        #: node; recomputing it would be 113 x 500,000 iterations.
        self.live: set = set()
        self.unit: set = set()
        self.conflicting: set = set()

    def add_clause(self, clause) -> int:
        """Register a new no-good and classify it against the LIVE `value`.

        Spec 6.2: in `assign` this is called at `nogoods.append(clause)`,
        where every variable in the clause is bound and agrees -- so the
        clause is born CONFLICTING. Computing counters against an empty state
        would read it as live, and the error would never show up as a crash.
        """
        if not clause:
            raise ClauseIndexError(
                "refusing an empty clause. `assign` returns "
                'AssignFail("layer_bad_witness") or '
                'AssignFail("layer_unfixable") before `nogoods.append`, so an '
                "empty clause reaching here means that guard was bypassed.")
        cid = len(self.size)
        self.clauses.append(dict(clause))
        self.size.append(len(clause))
        self.n_agree.append(0)
        self.n_contra.append(0)
        for var, forbidden in clause.items():
            self.var_to_clauses.setdefault(var, []).append((cid, forbidden))
            cur = self._value.get(var, _UNBOUND)
            if cur is _UNBOUND:
                continue
            if cur == forbidden:
                self.n_agree[cid] += 1
            else:
                self.n_contra[cid] += 1
        self._reclassify(cid)
        return cid

    def bind(self, var, val) -> None:
        """`var` has just entered `value` with `val`."""
        for cid, forbidden in self.var_to_clauses.get(var, ()):
            if val == forbidden:
                self.n_agree[cid] += 1
            else:
                self.n_contra[cid] += 1
            self._reclassify(cid)

    def unbind(self, var, old) -> None:
        """`var` has just left `value`, where it held `old`.

        Refuses, loudly, to drive a counter below zero. A counter at zero
        means this variable was never counted as bound to `old` in this
        clause, so the unbind is stray: `assign.py`'s own comment in `retry`
        (the `value.pop(popped, None)` site) names the hazard -- "unbinding
        one that was never bound would drive a count above its true value".
        Silently going to -1 would never recover, and the first symptom would
        be a wrong `live` count several thousand nodes later.

        A single pass, so a raise part-way through a variable's clause list
        leaves the earlier clauses already decremented. Acceptable: the
        error is fatal by design (see `ClauseIndexError`), and the run that
        hit it is discarded. This catches an unbind of a variable that was
        never bound; it cannot catch one that was bound to a different value
        than `old`, where the wrong counter is still positive.
        """
        for cid, forbidden in self.var_to_clauses.get(var, ()):
            if old == forbidden:
                counter, name = self.n_agree, "n_agree"
            else:
                counter, name = self.n_contra, "n_contra"
            if counter[cid] <= 0:
                raise ClauseIndexError(
                    f"stray unbind: variable {var!r} (held {old!r}) is being "
                    f"unbound from clause {cid}, but {name}[{cid}] is "
                    f"{counter[cid]}, so it was never counted as bound that "
                    "way. `value` and the counters have diverged -- a "
                    "bind/rebind site is missing or an unbind is doubled.")
            counter[cid] -= 1
            self._reclassify(cid)

    def rebind(self, var, old, new) -> None:
        """`var` was overwritten in place, `old` -> `new` (spec 6.1).

        NOT a no-op, which is what `VertexIndex` correctly does here. See the
        class docstring.
        """
        if old == new:
            return
        self.unbind(var, old)
        self.bind(var, new)

    def _reclassify(self, cid) -> None:
        k = self.size[cid]
        a = self.n_agree[cid]
        c = self.n_contra[cid]
        if c:
            self.live.discard(cid)
            self.unit.discard(cid)
            self.conflicting.discard(cid)
            return
        self.live.add(cid)
        if a == k - 1:
            self.unit.add(cid)
        else:
            self.unit.discard(cid)
        if a == k:
            self.conflicting.add(cid)
        else:
            self.conflicting.discard(cid)

    def free_var_of(self, cid):
        """`(var, forbidden_value)` for a unit clause's one free variable."""
        if cid not in self.unit:
            raise ClauseIndexError(
                f"clause {cid} is not unit: n_agree={self.n_agree[cid]}, "
                f"n_contra={self.n_contra[cid]}, size={self.size[cid]}")
        for var, forbidden in self.clauses[cid].items():
            if var not in self._value:
                return var, forbidden
        raise ClauseIndexError(
            f"clause {cid} is classified unit (n_agree={self.n_agree[cid]}, "
            f"size={self.size[cid]}) but every variable is bound. The "
            "counters and `value` have diverged.")

    def snapshot(self) -> dict:
        """Every counter, frozen, so two snapshots compare by value."""
        return {
            "n_agree": list(self.n_agree),
            "n_contra": list(self.n_contra),
            "size": list(self.size),
            "live": frozenset(self.live),
            "unit": frozenset(self.unit),
            "conflicting": frozenset(self.conflicting),
        }

    def recompute(self) -> dict:
        """Every counter rebuilt from scratch against the live `value`.

        The verify mode's reference. Compared against `snapshot()`, this is
        what makes the counters trustworthy rather than merely plausible.
        """
        n_agree, n_contra, size = [], [], []
        live, unit, conflicting = set(), set(), set()
        for cid, clause in enumerate(self.clauses):
            a = c = 0
            for var, forbidden in clause.items():
                cur = self._value.get(var, _UNBOUND)
                if cur is _UNBOUND:
                    continue
                if cur == forbidden:
                    a += 1
                else:
                    c += 1
            n_agree.append(a)
            n_contra.append(c)
            size.append(len(clause))
            if not c:
                live.add(cid)
                if a == len(clause) - 1:
                    unit.add(cid)
                if a == len(clause):
                    conflicting.add(cid)
        return {
            "n_agree": n_agree,
            "n_contra": n_contra,
            "size": size,
            "live": frozenset(live),
            "unit": frozenset(unit),
            "conflicting": frozenset(conflicting),
        }
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -m pytest tests/test_box_pleat_clause_index.py -v
```

Expected: 28 passed.

- [ ] **Step 5: Verify mutations 1–11 turn the suite red**

> **Mutation-harness limitation (recorded 2026-10-01, final review).** The
> harness in this section scores a mutation as "covered" on ANY non-zero pytest
> exit. It never checks that the mutation's own target test is among the
> failures, and the task reports record only aggregate "N failed" counts, so a
> mutation can be scored covered on an unrelated collateral failure (a test that
> breaks for a reason the mutation merely happens to trigger). A successor should
> parse the run (`-rf` or `--junitxml`) and assert that the specific test node id
> the mutation is meant to kill appears in the failure list. The 28 mutations in
> this slice were not re-run under that stricter rule.

For each mutation: apply it, assert the pattern applied **exactly once**, run the suite, confirm failures, revert. Four mutation checks silently failed to apply during the last slice — a `perl` pattern that matched a comment, a no-op parameter addition, a wrong indent, and one relayed unverified — so the occurs-exactly-once assertion is mandatory, not optional.

```bash
cd <repo>
.venv/bin/python3 - <<'PY'
import pathlib, subprocess, sys

SRC = pathlib.Path("mcp_harness/box_pleat/clause_index.py")
orig = SRC.read_text()

MUTATIONS = [
    ("1: drop the n_agree increment in bind",
     "            if val == forbidden:\n                self.n_agree[cid] += 1\n",
     "            if val == forbidden:\n                pass\n"),
    ("2: never increment n_contra in bind",
     "            else:\n                self.n_contra[cid] += 1\n            self._reclassify(cid)\n\n    def unbind",
     "            else:\n                pass\n            self._reclassify(cid)\n\n    def unbind"),
    ("3: make rebind a skip (trap 1)",
     "        if old == new:\n            return\n        self.unbind(var, old)\n        self.bind(var, new)",
     "        return"),
    ("4: add_clause counts against an empty state (trap 2)",
     "            cur = self._value.get(var, _UNBOUND)\n            if cur is _UNBOUND:\n                continue",
     "            cur = _UNBOUND\n            if cur is _UNBOUND:\n                continue"),
    ("5: unit test uses == k instead of == k - 1",
     "        if a == k - 1:\n            self.unit.add(cid)",
     "        if a == k:\n            self.unit.add(cid)"),
    # --- added by the fix pass, one per finding ---
    ("6: remove the unbind underflow guard (finding 1)",
     "            if counter[cid] <= 0:\n",
     "            if False:\n"),
    ("7: _reclassify tests n_contra == 1 instead of > 0 (finding 3b)",
     "        if c:\n            self.live.discard(cid)",
     "        if c == 1:\n            self.live.discard(cid)"),
    ("8: recompute copies size instead of rebuilding it (finding 5)",
     '            "size": size,\n            "live": frozenset(live),\n',
     '            "size": list(self.size),\n            "live": frozenset(live),\n'),
    ("9: delete rebind's old == new early return (finding 2)",
     "        if old == new:\n            return\n",
     ""),
    ("10: unit requires k > 1, so size-1 clauses are never unit (finding 3c)",
     "        if a == k - 1:\n            self.unit.add(cid)",
     "        if a == k - 1 and k > 1:\n            self.unit.add(cid)"),
    ("11: unbind always decrements n_agree (contra path broken)",
     '                counter, name = self.n_contra, "n_contra"\n',
     '                counter, name = self.n_agree, "n_agree"\n'),
]

failed_to_apply = []
still_green = []
for name, old, new in MUTATIONS:
    n = orig.count(old)
    if n != 1:
        failed_to_apply.append(f"{name}: pattern occurs {n} times, expected 1")
        continue
    SRC.write_text(orig.replace(old, new))
    r = subprocess.run(
        ["../.venv/bin/python3", "-m", "pytest",
         "tests/test_box_pleat_clause_index.py", "-q"],
        cwd="mcp_harness", env={"PYTHONPATH": ".", "PATH": "/usr/bin:/bin"},
        capture_output=True, text=True)
    tail = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "(no output)"
    print(f"{name}\n    exit={r.returncode}  {tail}")
    if r.returncode == 0:
        still_green.append(name)
    SRC.write_text(orig)

assert SRC.read_text() == orig, "source not restored"
if failed_to_apply:
    print("\nDID NOT APPLY:"); [print("  " + x) for x in failed_to_apply]
if still_green:
    print("\nSTILL GREEN (test gap):"); [print("  " + x) for x in still_green]
sys.exit(1 if (failed_to_apply or still_green) else 0)
PY
```

Expected: every mutation prints a non-zero exit, no "DID NOT APPLY" and no "STILL GREEN" section, and the script exits 0. If any mutation is still green, add a test that catches it before continuing — that is a real gap, not a formality: last slice, deleting the MRV heuristic itself left 13 of 13 tests passing.

- [ ] **Step 6: Commit**

```bash
cd <repo>
git add mcp_harness/box_pleat/clause_index.py mcp_harness/tests/test_box_pleat_clause_index.py
git commit -F "$SCRATCH/t1.txt"
```

Write `$SCRATCH/t1.txt` first (`$SCRATCH` is the session scratchpad directory, not the repo), with this content:

```
box_pleat: per-clause counters over the learned no-goods

hits_nogood() tests all(value.get(var) == val ...), so a clause with any
unbound variable is inert and can only fire when its LAST variable is bound
to the forbidden value. ClauseIndex keeps GRASP-style exact n_agree /
n_contra per clause, making the live / unit / conflicting states visible
where only the conflicting one was before.

rebind() exists because VertexIndex's was_bound guard must NOT be copied:
VertexIndex counts free-vs-bound, unchanged by the CEGAR path's in-place
reassignment, so it correctly skips; this counts agree-vs-contra, which does
change. 28 tests, mutations 1-11 verified red.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---
### Task 2: the cascade probe and the per-node aggregation

**Files:**
- Modify: `mcp_harness/box_pleat/clause_index.py` (add `time` import; three attributes to `__init__`; `probe`, `observe`, `note_choice`, `verify`)
- Modify: `docs/superpowers/specs/2026-09-30-clause-propagation-design.md` (§3.3 — one documented deviation, Step 6)
- Test: `mcp_harness/tests/test_box_pleat_clause_probe.py`

**Interfaces:**
- Consumes from Task 1: `ClauseIndex(value, prefer, touching, feasible, out)`, `add_clause`, `bind`, `rebind`, `unbind`, `free_var_of`, `snapshot`, `recompute`, `live`, `unit`, `conflicting`, `clauses`, `size`, `n_agree`, `n_contra`; `ClauseIndexError`.
- Produces, relied on by Task 3:
  - `probe(cid) -> bool` — `True` iff every remaining value of that unit clause's free variable is locally refused
  - `observe() -> None` — one node's aggregates, written into the out-dict
  - `note_choice(var) -> None` — called with the variable `pick` chose at this node
  - `verify() -> None` — raises `ClauseIndexError` on any disagreement with `recompute()`
  - attributes `probe_calls: int`, `probe_secs: float`, `observe_secs: float`. **They time different things.** `probe_secs` is the inside of `probe()` only. `observe_secs` is the whole of `observe()` -- the probes PLUS the `sorted(self.unit)`, `free_var_of` and `prefer` work that `probe_secs` cannot see -- so `observe_secs >= probe_secs` **while probes are driven only through `observe`** (a direct `probe()` call charges `probe_secs` alone). `observe_secs` is the **observe-side** cost, not the instrument's total overhead: neither figure includes `note_choice` or the `bind`/`unbind`/`add_clause` counter updates (about 4.4 per bind on the widest arm), and the true total is the wall-clock difference measured in Task 3. Both are charged on the exception path (`try/finally` in `probe` and `observe`); the out-dict writes at the end of `observe` are skipped when it raises, so the attributes and the out-dict can then disagree.
  - out-dict keys written: `nodes`, `live_total`, `clauses_total` (a snapshot taken at the TOP of each node: it can trail the stored clause count by one -- Task 4's `derived()` reports the authoritative `len(debug_clause_sizes)` as `clauses_total` and keeps this one as `clauses_total_observed`), `unit_nodes`, `dead_nodes`, `unit_domain_2`, `unit_domain_3`, `unit_domain_other`, `unit_var_chosen_nodes`, `probe_calls`, `probe_secs`, `observe_secs`. Fractions are **not** written — the runner derives them (Task 4).

**One documented deviation from the spec.** Spec §3.3 lists `unit_latency_nodes` — per unit event, the nodes elapsed until that variable is next bound. Implementing it needs cross-node state that **goes stale on backtracking**: if the search backtracks past the binds that made a clause unit, the pending entry survives and a later bind of that variable records a latency for a clause that is no longer unit. A silently wrong diagnostic in an instrument is worse than no diagnostic. It is replaced by `unit_var_chosen_nodes` — nodes at which `pick` chose a variable that was already the free variable of some unit clause. Its complement, `unit_nodes − unit_var_chosen_nodes`, is exactly "a unit clause existed and the search worked on something else," which is the signal latency was for, needs no cross-node state, and is one set-membership test. Step 6 amends the spec.

- [ ] **Step 1: Write the failing tests**

Create `mcp_harness/tests/test_box_pleat_clause_probe.py`:

```python
"""The one-step cascade probe, tested without compiling anything.

Spec: `docs/superpowers/specs/2026-09-30-clause-propagation-design.md` 3.2.

`prefer`, `touching` and `feasible` are injected, so a variable's domain size
and each vertex's verdict are set by the test rather than by geometry. That is
the only way to exercise the 3-VALUED branch: a ridge or hinge variable can
carry ["V", "M", "F"], so a unit clause leaves TWO values behind and the node
is dead only if BOTH are refused. On a borrowed fixture that branch might
never be reached, and a probe that checked only the first remaining value
would pass while inflating every dead-node figure it reports.
"""
import time

import pytest

from box_pleat.clause_index import ClauseIndex, ClauseIndexError


class Laws:
    """A recording `feasible`. `refuse` names the (vertex, value) pairs it
    rejects; every other pair is accepted."""

    def __init__(self, value, refuse=()):
        self.value = value
        self.refuse = set(refuse)
        self.seen = []

    def __call__(self, w):
        val = self.value.get(self._var())
        self.seen.append((w, val))
        return (w, val) not in self.refuse

    def _var(self):
        #: The variable under test is NAMED by the test through
        #: `laws.probed`, not inferred from `value`: `value` also holds the
        #: other clause variables, bound to their forbidden values, so it
        #: cannot say which key the probe just set. The probe sets exactly
        #: that one variable at a time, so `value[probed]` is the candidate
        #: value being judged.
        #:
        #: Raises rather than defaulting: with `probed` unset this would read
        #: `value.get(None)` -> None, every `(w, None)` would miss `refuse`,
        #: and the test would pass while measuring nothing.
        if self.probed is None:
            raise AssertionError("this test must set `laws.probed`")
        return self.probed

    probed = None


def _ix(domains, touching, refuse=(), value=None):
    """A ClauseIndex whose `prefer` returns `domains[var]`."""
    value = {} if value is None else value
    laws = Laws(value, refuse)
    ix = ClauseIndex(value, lambda var: list(domains[var]), touching,
                     laws, {})
    return value, ix, laws


def _make_unit(ix, value, clause, free):
    """Add `clause` and bind every variable except `free` to its forbidden
    value, so the clause becomes unit with `free` still open."""
    cid = ix.add_clause(clause)
    for var, forbidden in clause.items():
        if var == free:
            continue
        value[var] = forbidden
        ix.bind(var, forbidden)
    assert cid in ix.unit
    return cid


def test_probe_returns_false_when_the_remaining_value_is_feasible():
    domains = {1: ["M", "V"], 2: ["M", "V"]}
    value, ix, laws = _ix(domains, {2: ["W1"]})
    laws.probed = 2
    cid = _make_unit(ix, value, {1: "M", 2: "V"}, free=2)
    assert ix.probe(cid) is False, "M survives at W1, so the node is alive"


def test_probe_returns_true_when_the_only_remaining_value_is_refused():
    domains = {1: ["M", "V"], 2: ["M", "V"]}
    value, ix, laws = _ix(domains, {2: ["W1"]}, refuse=[("W1", "M")])
    laws.probed = 2
    cid = _make_unit(ix, value, {1: "M", 2: "V"}, free=2)
    assert ix.probe(cid) is True, "V is forbidden, M is refused: node is dead"


def test_probe_mutation6_tests_every_remaining_value_not_just_the_first():
    """A 3-valued variable leaves TWO values after the clause prunes one.

    `prefer` order is ["M", "V", "F"]; the clause forbids M, so the remaining
    values are V then F. V is refused and F is accepted, so the node is ALIVE.
    A probe that checked only `remaining[0]` would return True.
    """
    domains = {1: ["M", "V"], 2: ["M", "V", "F"]}
    value, ix, laws = _ix(domains, {2: ["W1"]}, refuse=[("W1", "V")])
    laws.probed = 2
    cid = _make_unit(ix, value, {1: "M", 2: "M"}, free=2)
    assert ix.probe(cid) is False
    assert ("W1", "F") in laws.seen, "the second remaining value was never tried"


def test_probe_on_a_3_valued_variable_is_dead_only_when_both_remain_refused():
    domains = {1: ["M", "V"], 2: ["M", "V", "F"]}
    value, ix, laws = _ix(domains, {2: ["W1"]},
                          refuse=[("W1", "V"), ("W1", "F")])
    laws.probed = 2
    cid = _make_unit(ix, value, {1: "M", 2: "M"}, free=2)
    assert ix.probe(cid) is True


def test_probe_mutation7_restores_value_exactly():
    domains = {1: ["M", "V"], 2: ["M", "V"]}
    value, ix, laws = _ix(domains, {2: ["W1"]})
    laws.probed = 2
    cid = _make_unit(ix, value, {1: "M", 2: "V"}, free=2)
    before = dict(value)
    ix.probe(cid)
    assert value == before, "the probe left search state behind"
    assert 2 not in value


def test_probe_restores_value_even_when_feasible_raises():
    domains = {1: ["M", "V"], 2: ["M", "V"]}

    def boom(w):
        raise RuntimeError("engine")

    value = {}
    ix = ClauseIndex(value, lambda var: list(domains[var]), {2: ["W1"]},
                     boom, {})
    cid = _make_unit(ix, value, {1: "M", 2: "V"}, free=2)
    with pytest.raises(RuntimeError, match="engine"):
        ix.probe(cid)
    assert 2 not in value, "try/finally did not restore `value`"
    assert ix.probe_calls == 1, "the call was counted before it raised"
    assert ix.probe_secs > 0.0, (
        "time spent before the raise was not charged: `probe_secs` must be "
        "accumulated in the `finally`, not only on a normal return")


def test_probe_refuses_a_value_when_any_one_touched_vertex_refuses_it():
    """Two vertices, one accepts and one refuses: the value is REFUSED.

    In production nearly every variable touches two vertices. `all` over the
    vertices means one refusal kills the value; an `any` (or a `not vertices`
    short-circuit on the first accept) would call it feasible and understate
    `dead_node_fraction`. Both orders are tested so the verdict cannot depend
    on which vertex is consulted first.
    """
    domains = {1: ["M", "V"], 2: ["M", "V"]}
    for refusing in ("W1", "W2"):
        value, ix, laws = _ix(domains, {2: ["W1", "W2"]},
                              refuse=[(refusing, "M")])
        laws.probed = 2
        cid = _make_unit(ix, value, {1: "M", 2: "V"}, free=2)
        assert ix.probe(cid) is True, (
            f"M is refused at {refusing} only, but still counted feasible")


def test_probe_consults_only_the_vertices_the_variable_touches():
    domains = {1: ["M", "V"], 2: ["M", "V"]}
    value, ix, laws = _ix(domains, {2: ["W1", "W2"], 9: ["W9"]})
    laws.probed = 2
    cid = _make_unit(ix, value, {1: "M", 2: "V"}, free=2)
    ix.probe(cid)
    assert {w for w, _ in laws.seen} == {"W1", "W2"}


def test_probe_on_a_variable_touching_nothing_is_alive():
    """No incident vertex means no local law can refuse anything."""
    domains = {1: ["M", "V"], 2: ["M", "V"]}
    value, ix, laws = _ix(domains, {})
    laws.probed = 2
    cid = _make_unit(ix, value, {1: "M", 2: "V"}, free=2)
    assert ix.probe(cid) is False
    assert laws.seen == []


def test_probe_dedupes_a_repeated_domain_value():
    domains = {1: ["M", "V"], 2: ["M", "V", "M"]}
    value, ix, laws = _ix(domains, {2: ["W1"]}, refuse=[("W1", "M")])
    laws.probed = 2
    cid = _make_unit(ix, value, {1: "M", 2: "V"}, free=2)
    assert ix.probe(cid) is True
    assert len(laws.seen) == 1, "M was tried twice"


def test_probe_refuses_a_domain_that_holds_only_the_forbidden_value():
    domains = {1: ["M", "V"], 2: ["V"]}
    value, ix, laws = _ix(domains, {2: ["W1"]})
    laws.probed = 2
    cid = _make_unit(ix, value, {1: "M", 2: "V"}, free=2)
    with pytest.raises(ClauseIndexError, match="no value left"):
        ix.probe(cid)


def test_probe_refuses_a_clause_that_is_not_unit():
    domains = {1: ["M", "V"], 2: ["M", "V"]}
    value, ix, laws = _ix(domains, {2: ["W1"]})
    cid = ix.add_clause({1: "M", 2: "V"})
    with pytest.raises(ClauseIndexError, match="not unit"):
        ix.probe(cid)


def test_probe_counts_its_calls_and_accumulates_time():
    domains = {1: ["M", "V"], 2: ["M", "V"]}
    value, ix, laws = _ix(domains, {2: ["W1"]})
    laws.probed = 2
    cid = _make_unit(ix, value, {1: "M", 2: "V"}, free=2)
    assert ix.probe_calls == 0
    ix.probe(cid)
    ix.probe(cid)
    assert ix.probe_calls == 2
    #: STRICTLY greater: `>= 0.0` cannot fail for a sum of perf_counter
    #: deltas, and a test that cannot fail is this project's named recurring
    #: defect. macOS perf_counter has ns resolution and a probe does a dict
    #: set, a generator pass and a dict pop, so the delta is never 0.
    assert ix.probe_secs > 0.0


def test_observe_counts_a_node_with_no_clauses():
    out = {}
    value = {}
    ix = ClauseIndex(value, lambda var: ["M", "V"], {}, lambda w: True, out)
    ix.observe()
    assert out["nodes"] == 1
    assert out["live_total"] == 0
    assert out["clauses_total"] == 0
    assert "unit_nodes" not in out
    assert "dead_nodes" not in out


def test_observe_counts_live_clauses_per_node():
    out = {}
    value = {}
    ix = ClauseIndex(value, lambda var: ["M", "V"], {}, lambda w: True, out)
    ix.add_clause({1: "M", 2: "V"})
    ix.add_clause({3: "M", 4: "V"})
    ix.observe()
    ix.observe()
    assert out["nodes"] == 2
    assert out["live_total"] == 4, "two live clauses observed twice"
    #: A SNAPSHOT of the clause count, not an accumulation over nodes: after
    #: two observes it must read 2, not 4. An `+=` here would read
    #: nodes x clauses and silently corrupt "clauses stored by end of arm".
    assert out["clauses_total"] == 2


def test_observe_records_a_unit_node_and_the_domain_size():
    out = {}
    domains = {1: ["M", "V"], 2: ["M", "V"]}
    value = {}
    ix = ClauseIndex(value, lambda var: list(domains[var]), {2: ["W1"]},
                     lambda w: True, out)
    _make_unit(ix, value, {1: "M", 2: "V"}, free=2)
    ix.observe()
    assert out["unit_nodes"] == 1
    assert out["unit_domain_2"] == 1
    assert "unit_domain_3" not in out
    assert "dead_nodes" not in out, "M is feasible, so the node is alive"


def test_observe_files_a_4_valued_domain_under_unit_domain_other():
    """Only 2 and 3 have their own key. A wider domain must land in
    `unit_domain_other`, the one key the runner reads for it; widening the
    tuple would file it under a `unit_domain_4` nothing reads."""
    out = {}
    domains = {1: ["M", "V"], 2: ["M", "V", "F", "X"]}
    value = {}
    ix = ClauseIndex(value, lambda var: list(domains[var]), {2: ["W1"]},
                     lambda w: True, out)
    _make_unit(ix, value, {1: "M", 2: "V"}, free=2)
    ix.observe()
    assert out["unit_domain_other"] == 1
    assert "unit_domain_4" not in out
    assert "unit_domain_2" not in out and "unit_domain_3" not in out


def test_observe_records_a_dead_node():
    out = {}
    domains = {1: ["M", "V"], 2: ["M", "V"]}
    value = {}
    ix = ClauseIndex(value, lambda var: list(domains[var]), {2: ["W1"]},
                     lambda w: False, out)
    _make_unit(ix, value, {1: "M", 2: "V"}, free=2)
    ix.observe()
    assert out["dead_nodes"] == 1


def test_observe_counts_the_domain_histogram_for_every_unit_clause():
    """Both unit clauses contribute, even though the probe loop short-circuits.

    Each free variable TOUCHES a vertex and `feasible` refuses everything, so
    the first unit clause (cid 0) is dead and the probe loop breaks there. With
    an empty `touching` map `all([])` is True, every probe reports ALIVE, the
    loop never short-circuits, and a histogram folded into it would pass this
    test while under-counting in production.
    """
    out = {}
    domains = {1: ["M", "V"], 2: ["M", "V"], 3: ["M", "V"], 4: ["M", "V", "F"]}
    value = {}
    ix = ClauseIndex(value, lambda var: list(domains[var]),
                     {2: ["W1"], 4: ["W2"]}, lambda w: False, out)
    _make_unit(ix, value, {1: "M", 2: "V"}, free=2)
    _make_unit(ix, value, {3: "M", 4: "V"}, free=4)
    ix.observe()
    assert out["dead_nodes"] == 1, "the probe must actually have short-circuited"
    assert ix.probe_calls == 1, "second probe ran: the loop did not break"
    assert out["unit_domain_2"] == 1
    assert out["unit_domain_3"] == 1


def test_note_choice_counts_only_a_variable_that_was_unit_free():
    out = {}
    domains = {1: ["M", "V"], 2: ["M", "V"]}
    value = {}
    ix = ClauseIndex(value, lambda var: list(domains[var]), {2: ["W1"]},
                     lambda w: True, out)
    _make_unit(ix, value, {1: "M", 2: "V"}, free=2)
    ix.observe()
    ix.note_choice(7)
    assert "unit_var_chosen_nodes" not in out
    ix.note_choice(2)
    assert out["unit_var_chosen_nodes"] == 1


def test_note_choice_is_inert_when_no_clause_was_unit():
    out = {}
    value = {}
    ix = ClauseIndex(value, lambda var: ["M", "V"], {}, lambda w: True, out)
    ix.observe()
    ix.note_choice(2)
    assert "unit_var_chosen_nodes" not in out


def test_note_choice_does_not_see_a_unit_set_left_over_from_an_earlier_node():
    """`_unit_vars` is per-node. After backtracking un-units the clause, the
    next `observe` must clear it, or `note_choice` would count a variable that
    is no longer the free variable of any unit clause -- exactly the stale
    cross-node state `unit_latency_nodes` was withdrawn to avoid."""
    out = {}
    domains = {1: ["M", "V"], 2: ["M", "V"]}
    value = {}
    ix = ClauseIndex(value, lambda var: list(domains[var]), {2: ["W1"]},
                     lambda w: True, out)
    _make_unit(ix, value, {1: "M", 2: "V"}, free=2)
    ix.observe()
    del value[1]
    ix.unbind(1, "M")
    assert not ix.unit
    ix.observe()
    ix.note_choice(2)
    assert "unit_var_chosen_nodes" not in out


def test_observe_reports_the_probe_cost_into_the_out_dict():
    out = {}
    domains = {1: ["M", "V"], 2: ["M", "V"]}
    value = {}
    ix = ClauseIndex(value, lambda var: list(domains[var]), {2: ["W1"]},
                     lambda w: True, out)
    ix.observe()
    assert out["probe_calls"] == 0 and out["probe_secs"] == 0.0
    _make_unit(ix, value, {1: "M", 2: "V"}, free=2)
    ix.observe()
    assert out["probe_calls"] == ix.probe_calls == 1
    assert out["probe_secs"] == ix.probe_secs > 0.0


def test_observe_times_its_whole_body_into_observe_secs():
    """`observe_secs` covers the whole of `observe`, so it is written to the
    out-dict and is never less than `probe_secs` WHEN PROBES RUN THROUGH
    `observe` (the probe runs inside it). It is also nonzero on a node with NO
    unit clause: `probe_secs` stays 0 there while the bookkeeping is still
    spent.

    The `>=` alone cannot detect a PARTIAL wrap -- `t0` moved later still
    leaves `observe_secs >= probe_secs`. The two tests after this one give the
    untimed segments real, sleep-backed cost so a shortened wrap is red."""
    out = {}
    domains = {1: ["M", "V"], 2: ["M", "V"]}
    value = {}
    ix = ClauseIndex(value, lambda var: list(domains[var]), {2: ["W1"]},
                     lambda w: True, out)
    ix.observe()
    assert "observe_secs" in out
    assert out["probe_secs"] == 0.0
    assert out["observe_secs"] > 0.0, "an observe with no probe still costs"
    _make_unit(ix, value, {1: "M", 2: "V"}, free=2)
    ix.observe()
    assert out["observe_secs"] == ix.observe_secs
    assert out["probe_secs"] > 0.0
    assert out["observe_secs"] >= out["probe_secs"]


class _SlowIterSet(set):
    """A `set` whose iteration costs 5 ms. `observe` iterates `self.unit`
    exactly once, in `sorted(self.unit)`, which is the first thing it does
    after the counters -- and the segment a late `t0` leaves untimed."""

    def __iter__(self):
        time.sleep(0.005)
        return super().__iter__()


def test_observe_secs_covers_the_sort_of_the_unit_set():
    """Kills a `t0` moved to just before `if units:`, which leaves
    `sorted(self.unit)` untimed. No unit clause exists on this node, so there
    is no probe and no `prefer` call: `observe_secs` can only reach 4 ms if
    the sort's 5 ms sleep was inside the timed region."""
    out = {}
    ix = ClauseIndex({}, lambda var: ["M", "V"], {}, lambda w: True, out)
    ix.unit = _SlowIterSet()
    ix.observe()
    assert out["probe_secs"] == 0.0
    assert out["observe_secs"] >= 0.004, (
        f"observe_secs={out['observe_secs']!r}: the 5 ms spent iterating the "
        "unit set was not charged, so the timed region starts too late")


def test_observe_secs_exceeds_probe_secs_by_the_untimed_prefer_calls():
    """With one unit clause `prefer` is called exactly twice per `observe`:
    by the histogram pass and at the top of `probe`, which runs BEFORE
    `probe`'s own `t0`. Both are therefore outside `probe_secs` and inside
    `observe_secs`; at 5 ms each the gap must be at least 9 ms. A `t0` moved
    to the start of the probe loop drops the histogram's call and halves the
    gap, which a bare `>=` cannot see."""
    out = {}
    domains = {1: ["M", "V"], 2: ["M", "V"]}

    def slow_prefer(var):
        time.sleep(0.005)
        return list(domains[var])

    value = {}
    ix = ClauseIndex(value, slow_prefer, {2: ["W1"]}, lambda w: True, out)
    _make_unit(ix, value, {1: "M", 2: "V"}, free=2)
    ix.observe()
    assert out["probe_calls"] == 1
    gap = out["observe_secs"] - out["probe_secs"]
    assert gap >= 0.009, (
        f"observe_secs - probe_secs = {gap!r}: the two 5 ms `prefer` calls "
        "outside `probe`'s own timing were not both charged")


def test_observe_charges_observe_secs_when_a_probe_raises():
    """`feasible` raising inside a probe that `observe` is running: the
    probe's own `finally` charges `probe_secs`, so `observe` must charge
    `observe_secs` too, or the invariant `observe_secs >= probe_secs` breaks
    on the exception path. The out-dict writes at the end of `observe` are
    skipped on that path -- the attributes and the out-dict DISAGREE -- and
    this test pins that so nobody mistakes the `finally` for a full rollback."""
    out = {}
    domains = {1: ["M", "V"], 2: ["M", "V"]}

    def boom(w):
        time.sleep(0.002)
        raise RuntimeError("feasible blew up")

    value = {}
    ix = ClauseIndex(value, lambda var: list(domains[var]), {2: ["W1"]},
                     boom, out)
    _make_unit(ix, value, {1: "M", 2: "V"}, free=2)
    with pytest.raises(RuntimeError, match="feasible blew up"):
        ix.observe()
    assert ix.probe_secs > 0.0
    assert ix.observe_secs >= ix.probe_secs
    assert "observe_secs" not in out and "probe_secs" not in out, (
        "the end-of-observe out-dict writes are skipped when observe raises")


def test_a_direct_probe_charges_probe_secs_alone():
    """The precondition on `observe_secs >= probe_secs`: it holds only while
    probes are driven through `observe`. A direct `probe()` call charges
    `probe_secs` and leaves `observe_secs` at zero."""
    value, ix, laws = _ix({1: ["M", "V"], 2: ["M", "V"]}, {2: ["W1"]})
    laws.probed = 2
    cid = _make_unit(ix, value, {1: "M", 2: "V"}, free=2)
    ix.probe(cid)
    assert ix.probe_secs > 0.0
    assert ix.observe_secs == 0.0


def test_verify_passes_on_a_correctly_maintained_index():
    value = {}
    ix = ClauseIndex(value, lambda var: ["M", "V"], {}, lambda w: True, {})
    ix.add_clause({1: "M", 2: "V", 3: "M"})
    value[1] = "M"
    ix.bind(1, "M")
    ix.verify()


def test_verify_raises_and_names_the_clause_on_a_corrupted_counter():
    value = {}
    ix = ClauseIndex(value, lambda var: ["M", "V"], {}, lambda w: True, {})
    ix.add_clause({1: "M", 2: "V"})
    value[1] = "M"
    ix.bind(1, "M")
    ix.n_agree[0] = 0
    with pytest.raises(ClauseIndexError, match="clause 0"):
        ix.verify()


def test_verify_raises_when_only_the_classification_diverges():
    value = {}
    ix = ClauseIndex(value, lambda var: ["M", "V"], {}, lambda w: True, {})
    ix.add_clause({1: "M", 2: "V"})
    value[1] = "M"
    ix.bind(1, "M")
    ix.unit.discard(0)
    with pytest.raises(ClauseIndexError, match="classification"):
        ix.verify()


def test_verify_names_a_size_divergence_rather_than_printing_empty_sets():
    """Corrupt only `size`. The counters still match, so the old fallback fell
    through to the classification message and printed three empty sets."""
    value = {}
    ix = ClauseIndex(value, lambda var: ["M", "V"], {}, lambda w: True, {})
    ix.add_clause({1: "M", 2: "V"})
    ix.size[0] = 5
    with pytest.raises(ClauseIndexError, match=r"size=5 but recompute gives size=2"):
        ix.verify()


def test_verify_names_a_size_list_of_the_wrong_length():
    value = {}
    ix = ClauseIndex(value, lambda var: ["M", "V"], {}, lambda w: True, {})
    ix.add_clause({1: "M", 2: "V"})
    ix.size.append(2)
    with pytest.raises(ClauseIndexError, match="size list length 2 but 1"):
        ix.verify()


@pytest.mark.parametrize("name", ["n_agree", "n_contra"])
@pytest.mark.parametrize("direction", ["too long", "too short"])
def test_verify_names_a_counter_list_of_the_wrong_length(name, direction):
    """A trailing extra entry diverges on no clause and used to fall through
    to the classification message with three empty sets; a missing entry used
    to raise a bare IndexError rather than `ClauseIndexError`."""
    value = {}
    ix = ClauseIndex(value, lambda var: ["M", "V"], {}, lambda w: True, {})
    ix.add_clause({1: "M", 2: "V"})
    counter = getattr(ix, name)
    if direction == "too long":
        counter.append(0)
        expected = f"{name} list length 2 but 1"
    else:
        counter.pop()
        expected = f"{name} list length 0 but 1"
    with pytest.raises(ClauseIndexError, match=expected):
        ix.verify()
```

**A defect in this plan, found during execution and fixed here.** The first
draft of `test_observe_counts_the_domain_histogram_for_every_unit_clause` used
`touching={}`. With no touched vertices `all([])` is True, so every probe
reports ALIVE, the probe loop never short-circuits, and the aggregation
mutation in Step 5 came back STILL GREEN -- the test could not distinguish the
two-pass implementation from the folded one it exists to pin. The shipped test
gives each free variable a real vertex and a refusing `feasible`, and asserts
`dead_nodes == 1` and `probe_calls == 1` so the short-circuit is proved rather
than assumed. Two further tests were added for the same reason, each after an
extra mutation found its state unguarded:
`test_note_choice_does_not_see_a_unit_set_left_over_from_an_earlier_node` and
`test_observe_reports_the_probe_cost_into_the_out_dict` -- the second guards
the out-dict keys Task 3 depends on.

**Review round, same task.** Seven further findings were closed. The one that
mattered: no test had a variable touching TWO vertices where one refuses and the
other accepts, so `all(feasible(w) ...)` could become an `any` with every test
green -- and in production nearly every variable touches two vertices, so
`dead_node_fraction` would have been silently understated. Second:
`probe_secs` times only the inside of `probe`, while `observe` spends untimed
work per unit clause (`sorted`, three `free_var_of` scans of up to ~200
variables, two `prefer` calls), so calling it "the instrument's own cost" would
have understated the overhead. `observe_secs` (the whole of `observe`) was added
alongside it rather than renaming it. The rest: `clauses_total` is asserted to
be a snapshot, `unit_domain_other` is exercised with a 4-valued domain, the
exception-path test asserts `probe_calls`/`probe_secs`, `verify()` names a
`size` divergence instead of printing empty sets, and a stale comment in
`Laws._var` was corrected.

**Third round, same task.** Four findings, all documented claims that were not
quite true. `observe_secs >= probe_secs` was stated unconditionally; it holds
only while probes run through `observe` (a direct `probe()` charges
`probe_secs` alone), and `observe` had no `try/finally`, so a raising
`feasible` charged `probe_secs` and never `observe_secs`. Now it does, and the
docs say the out-dict writes are still skipped on that path. The test that
pinned the wrap could not fail on a late `t0`; two sleep-backed tests now kill
the two partial wraps separately. `observe_secs` was called "the honest
overhead figure" and is now the **observe-side** cost, with the wall-clock
difference from Task 3 named as the true overhead. `verify()` checks the
`n_agree` and `n_contra` lengths as it already did `size`.

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -m pytest tests/test_box_pleat_clause_probe.py -v
```

Expected: every test errors with `AttributeError: 'ClauseIndex' object has no attribute 'probe'` (or `observe` / `note_choice` / `verify`).

- [ ] **Step 3: Write the implementation**

In `mcp_harness/box_pleat/clause_index.py`, change the import block from:

```python
from __future__ import annotations
```

to:

```python
from __future__ import annotations

import time
```

Then, in `__init__`, after the line `self.conflicting: set = set()`, add:

```python

        #: The instrument's own cost, reported rather than assumed. A per-node
        #: slowdown that is measured is a finding; one that is discovered
        #: afterwards invalidates the run it was discovered in.
        #:
        #: TWO figures, because they answer different questions.
        #: `probe_calls` counts `probe()` invocations. `probe_secs` times ONLY
        #: the inside of `probe()` (the value sets and `feasible` calls).
        #: `observe_secs` times the whole of `observe()`: the probe passes PLUS
        #: the bookkeeping `probe_secs` cannot see -- `sorted(self.unit)`, the
        #: `free_var_of` scans of each unit clause's dict and the `prefer`
        #: calls of the histogram pass. So `observe_secs >= probe_secs` WHILE
        #: PROBES ARE DRIVEN ONLY THROUGH `observe()`; a direct `probe()` call
        #: charges `probe_secs` alone, so the inequality can fail then.
        #:
        #: `observe_secs` is the OBSERVE-SIDE cost, not the instrument's total
        #: overhead. It excludes the out-dict writes at the very end of
        #: `observe`, `note_choice`, and every `bind`/`unbind`/`add_clause`
        #: counter update -- the per-assignment maintenance, about 4.4 counter
        #: updates per bind on the widest measured arm. The true total
        #: overhead is the wall-clock difference between an instrumented and
        #: an uninstrumented run (Task 3), not this field.
        #:
        #: Both attributes are charged on the exception path as well
        #: (`try/finally` in `probe` and in `observe`). The out-dict writes at
        #: the end of `observe` are NOT: when `observe` raises they are
        #: skipped, so the attributes and the out-dict can then disagree.
        self.probe_calls = 0
        self.probe_secs = 0.0
        self.observe_secs = 0.0
        #: The free variables of the clauses that were unit at the CURRENT
        #: node, set by `observe` and read by `note_choice`. Deliberately not
        #: cross-node state: see `note_choice`.
        self._unit_vars: frozenset = frozenset()
```

Then append these four methods to the class:

```python
    def probe(self, cid) -> bool:
        """`True` iff this unit clause makes the current node PROVABLY DEAD.

        Spec 3.2. The clause eliminates one value of its single free
        variable. It does NOT in general FORCE a value: `prefer()`
        (`assign.py:1046`) ends `if can_be_flat(var): order = order + ["F"]`,
        so a ridge or hinge variable can carry three values and a unit clause
        leaves TWO behind. So every REMAINING value is tested, and the node is
        dead only when all of them are locally refused.

        Trap 3: `feasible` -> `violation` (`assign.py:848`) reads `ring`,
        `lab_of`, `var_of` and `value` only -- it never consults the live
        `VertexIndex` -- so setting a value here, testing, and restoring it
        under `try/finally` leaves the search bit-identical. Do NOT add a
        `vx` update: that would corrupt the index this run depends on for
        speed.
        """
        var, forbidden = self.free_var_of(cid)
        dom = self._prefer(var)
        remaining = [v for i, v in enumerate(dom)
                     if v != forbidden and v not in dom[:i]]
        if not remaining:
            raise ClauseIndexError(
                f"clause {cid} forbids {forbidden!r} at variable {var!r}, "
                f"whose whole domain is {dom!r} -- no value left. The search "
                "could never have bound this variable at all, so the clause "
                "and the value order disagree about its domain.")
        vertices = tuple(self._touching.get(var, ()))
        self.probe_calls += 1
        t0 = time.perf_counter()
        try:
            for val in remaining:
                self._value[var] = val
                # ALL touched vertices must accept the value. A value refused
                # at ANY one vertex is refused, which is why this is `all`:
                # an `any` here would call a value feasible when only one of
                # a variable's two vertices accepts it, and understate
                # `dead_node_fraction` silently.
                if all(self._feasible(w) for w in vertices):
                    return False
            return True
        finally:
            self._value.pop(var, None)
            self.probe_secs += time.perf_counter() - t0

    def observe(self) -> None:
        """One search node's worth of state, accumulated into the out-dict.

        Called at the TOP of `assign`'s main loop, before `pick()`, so
        `value` holds the state this node inherited.

        Raw counts only. The fractions in spec 3.3 are derived by the runner,
        so the index never has to be asked what its own headline is.

        Times its own whole body into `observe_secs` (see `__init__` for
        exactly what that covers and excludes): the observe-side cost,
        including the work `probe_secs` cannot see. The timing is charged in a
        `finally`, so an `observe` that raises still pays for the time it
        spent. The out-dict writes after the `finally` are skipped on that
        path, so the attributes and the out-dict can disagree after a raise.
        """
        t0 = time.perf_counter()
        out = self._out
        try:
            out["nodes"] = out.get("nodes", 0) + 1
            out["live_total"] = out.get("live_total", 0) + len(self.live)
            out["clauses_total"] = len(self.size)
            units = sorted(self.unit)
            if units:
                out["unit_nodes"] = out.get("unit_nodes", 0) + 1
                self._unit_vars = frozenset(
                    self.free_var_of(c)[0] for c in units)
                # TWO passes over `units`, not one. The probe loop
                # short-circuits on the first dead clause, so folding the
                # histogram into it would silently under-count the domain
                # sizes of every clause after the first -- biasing exactly the
                # figure that says whether propagation is weak by
                # construction.
                for cid in units:
                    n = len(self._prefer(self.free_var_of(cid)[0]))
                    key = (f"unit_domain_{n}" if n in (2, 3)
                           else "unit_domain_other")
                    out[key] = out.get(key, 0) + 1
                for cid in units:
                    if self.probe(cid):
                        out["dead_nodes"] = out.get("dead_nodes", 0) + 1
                        break
            else:
                self._unit_vars = frozenset()
        finally:
            self.observe_secs += time.perf_counter() - t0
        out["probe_calls"] = self.probe_calls
        out["probe_secs"] = self.probe_secs
        out["observe_secs"] = self.observe_secs

    def note_choice(self, var) -> None:
        """`pick` chose `var` at this node.

        Replaces spec 3.3's `unit_latency_nodes`, which needed cross-node
        state that GOES STALE on backtracking: if the search backtracks past
        the binds that made a clause unit, a pending latency entry survives
        and the next bind of that variable records a latency for a clause
        that is no longer unit. This is the same signal without the staleness
        -- `unit_nodes - unit_var_chosen_nodes` is "a unit clause existed and
        the search worked on something else" -- and it is one set-membership
        test against state `observe` just built for this node.
        """
        if var in self._unit_vars:
            out = self._out
            out["unit_var_chosen_nodes"] = out.get("unit_var_chosen_nodes", 0) + 1

    def verify(self) -> None:
        """Refuse on any disagreement with a from-scratch recompute.

        Test-only: it walks every clause on every node, which is the work the
        counters exist to avoid. It is what makes the counters trustworthy
        rather than plausible -- a counter that is wrong in a COMPENSATING way
        still produces a wrong headline, and only this catches it.
        """
        got = self.snapshot()
        ref = self.recompute()
        if got == ref:
            return
        for name in ("size", "n_agree", "n_contra"):
            if len(got[name]) != len(ref[name]):
                raise ClauseIndexError(
                    f"{name} list length {len(got[name])} but "
                    f"{len(ref[name])} clauses are stored: `add_clause` and "
                    "`clauses` have diverged")
        for cid in range(len(self.size)):
            if (got["n_agree"][cid] != ref["n_agree"][cid]
                    or got["n_contra"][cid] != ref["n_contra"][cid]):
                raise ClauseIndexError(
                    f"clause {cid} (size {self.size[cid]}, "
                    f"{self.clauses[cid]!r}): maintained n_agree="
                    f"{got['n_agree'][cid]} n_contra={got['n_contra'][cid]} "
                    f"but recompute gives n_agree={ref['n_agree'][cid]} "
                    f"n_contra={ref['n_contra'][cid]}")
            if got["size"][cid] != ref["size"][cid]:
                raise ClauseIndexError(
                    f"clause {cid} ({self.clauses[cid]!r}): maintained "
                    f"size={got['size'][cid]} but recompute gives "
                    f"size={ref['size'][cid]}. The counters agree, so this "
                    "is a corrupted `size` entry, which would misclassify "
                    "the clause as unit or conflicting.")
        raise ClauseIndexError(
            "counters agree but classification differs -- live "
            f"{set(got['live']) ^ set(ref['live'])}, unit "
            f"{set(got['unit']) ^ set(ref['unit'])}, conflicting "
            f"{set(got['conflicting']) ^ set(ref['conflicting'])}")
```

- [ ] **Step 4: Run both test files to verify they pass**

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -m pytest tests/test_box_pleat_clause_index.py tests/test_box_pleat_clause_probe.py -v
```

Expected: 28 + 37 = 65 passed.

- [ ] **Step 5: Verify the Task 2 mutations turn the suite red**

> **Mutation-harness limitation (recorded 2026-10-01, final review).** The
> harness in this section scores a mutation as "covered" on ANY non-zero pytest
> exit. It never checks that the mutation's own target test is among the
> failures, and the task reports record only aggregate "N failed" counts, so a
> mutation can be scored covered on an unrelated collateral failure (a test that
> breaks for a reason the mutation merely happens to trigger). A successor should
> parse the run (`-rf` or `--junitxml`) and assert that the specific test node id
> the mutation is meant to kill appears in the failure list. The 28 mutations in
> this slice were not re-run under that stricter rule.

```bash
cd <repo>
.venv/bin/python3 - <<'PY'
import pathlib, subprocess, sys

SRC = pathlib.Path("mcp_harness/box_pleat/clause_index.py")
orig = SRC.read_text()

MUTATIONS = [
    ("6: probe only the first remaining value",
     "        vertices = tuple(self._touching.get(var, ()))",
     "        remaining = remaining[:1]\n"
     "        vertices = tuple(self._touching.get(var, ()))"),
    ("7: probe leaves value[var] set",
     "            self._value.pop(var, None)\n"
     "            self.probe_secs += time.perf_counter() - t0",
     "            self.probe_secs += time.perf_counter() - t0"),
    ("6b: probe does not dedupe repeated domain values",
     "        remaining = [v for i, v in enumerate(dom)\n"
     "                     if v != forbidden and v not in dom[:i]]",
     "        remaining = [v for v in dom if v != forbidden]"),
    ("aggregation: fold the histogram into the short-circuiting probe loop",
     "                for cid in units:\n"
     "                    n = len(self._prefer(self.free_var_of(cid)[0]))\n"
     "                    key = (f\"unit_domain_{n}\" if n in (2, 3)\n"
     "                           else \"unit_domain_other\")\n"
     "                    out[key] = out.get(key, 0) + 1\n"
     "                for cid in units:\n"
     "                    if self.probe(cid):",
     "                for cid in units:\n"
     "                    n = len(self._prefer(self.free_var_of(cid)[0]))\n"
     "                    key = (f\"unit_domain_{n}\" if n in (2, 3)\n"
     "                           else \"unit_domain_other\")\n"
     "                    out[key] = out.get(key, 0) + 1\n"
     "                    if self.probe(cid):"),
    # --- finding 1
    ("F1: all -> any over the touched vertices",
     "                if all(self._feasible(w) for w in vertices):",
     "                if (not vertices) or any([self._feasible(w) for w in vertices]):"),
    # --- finding 2
    ("F2: drop the observe_secs write",
     "        out[\"observe_secs\"] = self.observe_secs\n",
     ""),
    ("F2b: observe_secs never accumulated",
     "            self.observe_secs += time.perf_counter() - t0\n",
     "            self.observe_secs += 0.0\n"),
    # --- finding 3
    ("F3: clauses_total accumulates instead of snapshotting",
     "            out[\"clauses_total\"] = len(self.size)",
     "            out[\"clauses_total\"] = out.get(\"clauses_total\", 0) + len(self.size)"),
    ("F3b: clauses_total += (literal)",
     "            out[\"clauses_total\"] = len(self.size)",
     "            out.setdefault(\"clauses_total\", 0)\n"
     "            out[\"clauses_total\"] += len(self.size)"),
    # --- finding 4
    ("F4: widen the histogram key tuple to (2, 3, 4)",
     "if n in (2, 3)\n",
     "if n in (2, 3, 4)\n"),
    # --- finding 5
    ("F5: probe_secs accumulated only on normal return (not in finally)",
     "                if all(self._feasible(w) for w in vertices):\n"
     "                    return False\n"
     "            return True\n"
     "        finally:\n"
     "            self._value.pop(var, None)\n"
     "            self.probe_secs += time.perf_counter() - t0",
     "                if all(self._feasible(w) for w in vertices):\n"
     "                    self.probe_secs += time.perf_counter() - t0\n"
     "                    return False\n"
     "            self.probe_secs += time.perf_counter() - t0\n"
     "            return True\n"
     "        finally:\n"
     "            self._value.pop(var, None)"),
    # --- finding 6
    ("F6: verify drops the size-divergence branch",
     "            if got[\"size\"][cid] != ref[\"size\"][cid]:",
     "            if False:"),
    # --- round 3: findings 1, 2, 4 of the third review
    ("G1: t0 restarted just before `if units:` (sort untimed)",
     "            units = sorted(self.unit)\n"
     "            if units:\n",
     "            units = sorted(self.unit)\n"
     "            t0 = time.perf_counter()\n"
     "            if units:\n"),
    ("G2: t0 restarted before the probe loop (histogram untimed)",
     "                for cid in units:\n"
     "                    if self.probe(cid):",
     "                t0 = time.perf_counter()\n"
     "                for cid in units:\n"
     "                    if self.probe(cid):"),
    ("G3: observe charges observe_secs on the normal path only (no finally)",
     "        finally:\n"
     "            self.observe_secs += time.perf_counter() - t0\n",
     "        except ZeroDivisionError:\n"
     "            raise\n"
     "        self.observe_secs += time.perf_counter() - t0\n"),
    ("G4: verify's length check covers `size` only",
     "        for name in (\"size\", \"n_agree\", \"n_contra\"):",
     "        for name in (\"size\",):"),
    ("G5: verify's length check catches only a too-LONG list",
     "            if len(got[name]) != len(ref[name]):",
     "            if len(got[name]) > len(ref[name]):"),
]

failed_to_apply, still_green = [], []
for name, old, new in MUTATIONS:
    n = orig.count(old)
    if n != 1:
        failed_to_apply.append(f"{name}: pattern occurs {n} times, expected 1")
        print(f"{name}\n    DID NOT APPLY ({n} occurrences)")
        continue
    SRC.write_text(orig.replace(old, new))
    r = subprocess.run(
        ["../.venv/bin/python3", "-m", "pytest",
         "tests/test_box_pleat_clause_index.py",
         "tests/test_box_pleat_clause_probe.py", "-q"],
        cwd="mcp_harness", env={"PYTHONPATH": ".", "PATH": "/usr/bin:/bin"},
        capture_output=True, text=True)
    tail = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "(no output)"
    print(f"{name}\n    exit={r.returncode}  {tail}")
    if r.returncode == 0:
        still_green.append(name)
    SRC.write_text(orig)

assert SRC.read_text() == orig, "source not restored"
if failed_to_apply:
    print("\nDID NOT APPLY:"); [print("  " + x) for x in failed_to_apply]
if still_green:
    print("\nSTILL GREEN (test gap):"); [print("  " + x) for x in still_green]
print("\nscript exit:", 1 if (failed_to_apply or still_green) else 0)
sys.exit(1 if (failed_to_apply or still_green) else 0)
PY
```

Expected: all seventeen print a non-zero exit, no "DID NOT APPLY", no "STILL GREEN", script exits 0. G1 and G2 are the pair that pins the `t0` placement: G1 (sort untimed) is killed only by `test_observe_secs_covers_the_sort_of_the_unit_set`, G2 (histogram untimed) only by `test_observe_secs_exceeds_probe_secs_by_the_untimed_prefer_calls`; the bare `>=` test survives both.

- [ ] **Step 6: Amend the spec's §3.3 to match**

In `docs/superpowers/specs/2026-09-30-clause-propagation-design.md`, replace this table row:

```
| `unit_latency_nodes` | for each unit event, nodes elapsed until that variable is next bound; `null` if never |
```

with:

```
| `unit_var_chosen_nodes` | nodes at which `pick` chose a variable that was already the free variable of some unit clause |
```

and append this paragraph immediately after that table:

```
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
```

- [ ] **Step 7: Commit**

```bash
cd <repo>
git add mcp_harness/box_pleat/clause_index.py \
        mcp_harness/tests/test_box_pleat_clause_probe.py \
        docs/superpowers/specs/2026-09-30-clause-propagation-design.md
git commit -F "$SCRATCH/t2.txt"
```

Write `$SCRATCH/t2.txt` first, with this content:

```
box_pleat: the one-step cascade probe and the per-node aggregation

A unit clause eliminates one value of its single free variable. It does NOT
force a value: prefer() appends "F" when can_be_flat(var), so a ridge or
hinge variable carries three values and a unit clause leaves two behind. The
probe tests every REMAINING value and calls the node dead only when all are
locally refused, which makes dead_node_fraction a lower bound twice over --
only clauses already unit, and one cascade step.

The histogram and the probe run in two passes over the unit set on purpose:
the probe loop short-circuits on the first dead clause, so folding them
together would under-count exactly the figure that says whether propagation
is weak by construction.

Spec 3.3's unit_latency_nodes is withdrawn in favour of
unit_var_chosen_nodes: latency needed cross-node state that goes stale when
the search backtracks past the binds that made a clause unit.

37 tests; mutations 6, 7, a dedupe variant, a folded-histogram variant, the
seven review-round mutations (all->any, observe_secs x2, clauses_total x2,
unit_domain key tuple, probe_secs outside finally, verify size branch) and five
third-round mutations (t0 restarted before `if units:`, t0 restarted before the
probe loop, observe without a finally, verify length check size-only, verify
length check too-long-only) all verified red.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---
### Task 3: wire the index into `assign()` and `compile_tree()`

**Files:**
- Modify: `mcp_harness/box_pleat/assign.py` — import (after `:42`), signature (`:530-534`), guard (after `:627`), construction (after `:1090`), four hook sites (`:1115-1118`, `:1122-1124`, `:1133-1134`, `:1214`), per-node observe (after `:1176`), choice hook (after `var = pk[1][0]`)
- Modify: `mcp_harness/box_pleat/compile.py` — signature (`:119-129`), the `assign(...)` call (`:404-409`)
- Test: `mcp_harness/tests/test_box_pleat_clause_prop_wiring.py`

**Interfaces:**
- Consumes from Tasks 1 and 2: `ClauseIndex(value, prefer, touching, feasible, out)`, `add_clause(clause)`, `bind(var, val)`, `rebind(var, old, new)`, `unbind(var, old)`, `observe()`, `note_choice(var)`, `verify()`; `ClauseIndexError`.
- Produces, relied on by Tasks 4 and 5: `assign(..., clause_prop: dict | None = None, clause_prop_verify: bool = False)` and the same two keyword parameters on `compile_tree(...)`. When `clause_prop` is a dict it is populated in place with the keys listed in Task 2.

**Do NOT widen `compile.py`'s `except (ValueError, RuntimeError, KeyError)`.** `ClauseIndexError` subclasses `Exception` precisely so it escapes that catch. A broken instrument must surface as a crash, never as `AssignFail("error")`.

- [ ] **Step 1: Write the failing tests**

Create `mcp_harness/tests/test_box_pleat_clause_prop_wiring.py`:

```python
"""The clause-propagation instrument, wired into a real compile.

Spec: `docs/superpowers/specs/2026-09-30-clause-propagation-design.md` 7.

Cheap subjects only. The corpus run is
`docs/superpowers/evidence/2026-09-30-clause-propagation/probe.py`, not this
suite.

Sparse `lizard` is the important subject here and not for its size: it is the
subject whose sparse labelling actually CONTRADICTS and drives the CEGAR loop,
so it is the only cheap subject that exercises `retry`'s in-place
REASSIGNMENT -- the path where `ClauseIndex.rebind` must run and where
`VertexIndex`'s skip would be silently wrong (spec 6.1, Trap 1). The
non-vacuity guard below pins that: if `lizard` ever stops rejecting, this file
stops testing the rebind hook and must be replaced.
"""
import json

import pytest

from box_pleat.clause_index import ClauseIndexError
from box_pleat.compile import compile_tree
from test_box_pleat_tree import RULE6


def _entry(subject):
    with open(RULE6) as fh:
        return next(e for e in json.load(fh) if e["subject"] == subject)


def test_clause_prop_verify_without_clause_prop_is_refused():
    """A "verified" run in which the verifier never ran is the exact shape of
    vacuous pass this project keeps rediscovering. Mirrors the
    `vertex_index_verify` guard at `assign.py:615`."""
    e = _entry("starfish")
    with pytest.raises(ClauseIndexError, match="verifies NOTHING"):
        compile_tree(e["requested"], e["pairs"], clause_prop_verify=True)


def test_clause_index_error_escapes_compile_tree(monkeypatch):
    """A broken instrument must CRASH, not be folded into AssignFail("error").

    `compile.py` wraps `assign(...)` in
    `except (ValueError, RuntimeError, KeyError)`. If that were widened to
    `except Exception`, a real `ClauseIndexError` raised by the counters would
    be typed into a plausible-looking per-tree failure and a counter bug would
    read as a fact about the tree.

    The first test in this file pins that only incidentally (its guard raises
    inside `assign()`, so it also depends on the guard's position). This one
    exercises the real path directly: a `ClauseIndexError` raised from
    INSIDE the `assign()` call that `compile.py` wraps in its `try`. Nothing
    in `compile.py` or `assign.py` provides a hook for that, so it is
    provoked by monkeypatching `box_pleat.assign.ClauseIndex` -- the module
    global `assign()` constructs its index from -- with a subclass whose
    `observe` raises on the first search node. `assign()` calls `observe`
    at the top of its main loop, so the raise is on the wrapped path.
    """
    import box_pleat.assign as assign_mod

    # The class-hierarchy fact is cheap and documents the intent: the three
    # types compile.py catches must not include this one.
    assert not issubclass(ClauseIndexError, (ValueError, RuntimeError, KeyError))

    calls = []

    class BrokenIndex(assign_mod.ClauseIndex):
        def observe(self):
            calls.append(1)
            raise ClauseIndexError("injected: counter divergence")

    monkeypatch.setattr(assign_mod, "ClauseIndex", BrokenIndex)
    e = _entry("starfish")
    with pytest.raises(ClauseIndexError, match="injected"):
        compile_tree(e["requested"], e["pairs"], clause_prop={})
    # Non-vacuity: the raise must have come from the wrapped assign() call,
    # not from somewhere that merely happened to be on the way there.
    assert calls, "the injected observe() was never reached"


def test_instrument_does_not_change_a_sparse_compile():
    e = _entry("lizard")
    off = compile_tree(e["requested"], e["pairs"])
    on = compile_tree(e["requested"], e["pairs"], clause_prop={})
    assert off.stage_reached == on.stage_reached
    assert on.fold == off.fold, "the instrument changed the emitted FOLD"
    assert on.layers_tried == off.layers_tried


def test_instrument_does_not_change_a_dense_compile():
    e = _entry("starfish")
    kw = dict(dense=True, assign_budget=20_000)
    off = compile_tree(e["requested"], e["pairs"], **kw)
    on = compile_tree(e["requested"], e["pairs"], clause_prop={}, **kw)
    assert off.stage_reached == on.stage_reached
    assert on.fold == off.fold
    assert on.layers_tried == off.layers_tried


def test_sparse_lizard_exercises_the_cegar_path_and_verifies():
    """The rebind hook, on the real reassignment path, with verify on."""
    e = _entry("lizard")
    sizes: list = []
    prop: dict = {}
    res = compile_tree(e["requested"], e["pairs"], debug_clause_sizes=sizes,
                       clause_prop=prop, clause_prop_verify=True)
    assert len(sizes) > 0, (
        "NON-VACUITY: sparse `lizard` stored no no-good clause, so the CEGAR "
        "reassignment path never ran and `rebind` was never called. This "
        "file no longer tests Trap 1 -- replace the subject.")
    assert res.stage_reached == "emit", res.failure
    assert prop["nodes"] > 0
    # `observe()` runs at the TOP of the solver loop, so a clause learned on
    # the final node is never observed: the snapshot may trail the stored
    # count by exactly one. A gap of 0 or 1 is the contract; `== len(sizes)`
    # was wrong about it.
    assert len(sizes) - prop["clauses_total"] in (0, 1)


def test_verify_holds_on_a_dense_compile():
    e = _entry("starfish")
    prop: dict = {}
    res = compile_tree(e["requested"], e["pairs"], dense=True,
                       assign_budget=20_000, vertex_index=True,
                       clause_prop=prop, clause_prop_verify=True)
    assert res.stage_reached in ("emit", "layers", "assign"), res.failure
    assert prop["nodes"] > 0
    assert "probe_calls" in prop
    assert "probe_secs" in prop
    assert "observe_secs" in prop


def test_reported_counts_are_internally_consistent():
    e = _entry("lizard")
    prop: dict = {}
    compile_tree(e["requested"], e["pairs"], clause_prop=prop)
    n = prop["nodes"]
    assert prop.get("unit_nodes", 0) <= n
    assert prop.get("dead_nodes", 0) <= prop.get("unit_nodes", 0), (
        "a dead node is by definition a unit node")
    assert prop.get("unit_var_chosen_nodes", 0) <= prop.get("unit_nodes", 0)
    assert prop["live_total"] <= n * prop["clauses_total"]
    #: NOT `probe_calls >= 0`, which cannot fail. A probe is called only at a
    #: unit node, so zero unit nodes must mean zero probes and vice versa.
    assert (prop["probe_calls"] > 0) == (prop.get("unit_nodes", 0) > 0)


def test_instrument_and_vertex_index_compose_without_changing_the_fold():
    """Trap 3: the probe must leave `value` alone, so the VertexIndex the run
    depends on for speed stays correct. A probe that leaked a binding would
    corrupt the index and change the search."""
    e = _entry("lizard")
    base = compile_tree(e["requested"], e["pairs"])
    both = compile_tree(e["requested"], e["pairs"], vertex_index=True,
                        vertex_index_verify=True, clause_prop={},
                        clause_prop_verify=True)
    assert both.fold == base.fold
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -m pytest tests/test_box_pleat_clause_prop_wiring.py -v
```

Expected: every test fails -- most with `TypeError: compile_tree() got an unexpected keyword argument 'clause_prop'` or `'clause_prop_verify'`, and `test_clause_index_error_escapes_compile_tree` with `AttributeError` because `box_pleat.assign` has no `ClauseIndex` yet. (That test used to pass at this point because it only inspected the class and never called `compile_tree`; it now provokes the error from inside the `assign()` call `compile.py` wraps in its `try`, and its mutation -- widening that `except` to `Exception` -- must turn it red.)

- [ ] **Step 3: Add the import and the signature to `assign.py`**

Replace line 42:

```python
from .vertex_index import VertexIndex, VertexIndexError
```

with:

```python
from .clause_index import ClauseIndex, ClauseIndexError
from .vertex_index import VertexIndex, VertexIndexError
```

Replace the signature at `assign.py:530-534`:

```python
def assign(layout, ridges: list, boundary_ridges: list, contours: dict, *,
           budget: int = 500_000, global_check=None, layer_checks: int = 200,
           dense: bool = False, debug_clause_sizes: list | None = None,
           vertex_index: bool = False, vertex_index_verify: bool = False,
           debug_search: dict | None = None):
```

with:

```python
def assign(layout, ridges: list, boundary_ridges: list, contours: dict, *,
           budget: int = 500_000, global_check=None, layer_checks: int = 200,
           dense: bool = False, debug_clause_sizes: list | None = None,
           vertex_index: bool = False, vertex_index_verify: bool = False,
           debug_search: dict | None = None,
           clause_prop: dict | None = None,
           clause_prop_verify: bool = False):
```

- [ ] **Step 4: Add the misuse guard**

Immediately after the `vertex_index_verify` guard's closing line (`assign.py:627`, `"well, or drop vertex_index_verify.")`), insert:

```python
    if clause_prop_verify and clause_prop is None:
        # Same reasoning as the guard above, same failure shape: with
        # `clause_prop` unset no `ClauseIndex` is built, so `observe` and
        # `verify` are never called and a harness could record a "verified"
        # run in which the verifier never ran once.
        raise ClauseIndexError(
            "clause_prop_verify=True with clause_prop=None verifies NOTHING: "
            "no ClauseIndex is built, so `observe` and `verify` are never "
            "called. Pass a dict as clause_prop as well, or drop "
            "clause_prop_verify.")
```

- [ ] **Step 5: Build the index**

Immediately after `assign.py:1090` (`nogoods: list = []         # each a {variable: value} that must not all hold`), insert:

```python
    # Built here, after `feasible`, `touching`, `prefer` and `value` are all
    # final and after every early `return AssignFail(...)` above, so a refused
    # setup never pays for it. `nogoods` is the list it shadows: `add_clause`
    # below is called at the same site that appends to it, so the two can
    # never disagree about which clauses exist.
    cx = (ClauseIndex(value, prefer, touching, feasible, clause_prop)
          if clause_prop is not None else None)
```

- [ ] **Step 6: Add the three `retry` hooks**

Replace `assign.py:1115-1118`:

```python
                was_bound = var in value
                value[var] = vals[i]
                if vx is not None and not was_bound:
                    vx.bind(var)
```

with:

```python
                was_bound = var in value
                # Captured strictly BEFORE the overwrite on the next line:
                # on the CEGAR reassignment path it is the binding the
                # rejected candidate left, which `cx.rebind` needs. Read
                # only when the instrument is on, so an uninstrumented run
                # pays no dict lookup per `retry()` iteration.
                old_val = value.get(var) if cx is not None else None
                value[var] = vals[i]
                if vx is not None and not was_bound:
                    vx.bind(var)
                if cx is not None:
                    # TRAP 1 (spec 6.1). `was_bound` here means the CEGAR
                    # path OVERWROTE this variable in place. `VertexIndex`
                    # counts free-vs-bound, which a reassignment does not
                    # change, so it correctly SKIPS one line above. This
                    # index counts agree-vs-contra, which DOES change --
                    # skipping here would be silently wrong, and the counters
                    # would never recover.
                    if was_bound:
                        cx.rebind(var, old_val, vals[i])
                    else:
                        cx.bind(var, vals[i])
```

Replace `assign.py:1122-1124`:

```python
                del value[var]
                if vx is not None:
                    vx.unbind(var)
```

with:

```python
                del value[var]
                if vx is not None:
                    vx.unbind(var)
                if cx is not None:
                    cx.unbind(var, vals[i])
```

Replace `assign.py:1133-1134`:

```python
                if value.pop(popped, None) is not None and vx is not None:
                    vx.unbind(popped)
```

with:

```python
                # Restructured, same semantics: `ClauseIndex.unbind` needs the
                # value that was there, which the original one-liner discarded.
                popped_val = value.pop(popped, None)
                if popped_val is not None:
                    if vx is not None:
                        vx.unbind(popped)
                    if cx is not None:
                        cx.unbind(popped, popped_val)
```

- [ ] **Step 7: Add the per-node observe, the choice hook, and `add_clause`**

Immediately after `assign.py:1176` (`                debug_search["pool_total"] = vx.pool_total`) and before `        pk = pick()`, insert at eight-space indentation:

```python
        if cx is not None:
            cx.observe()
            if clause_prop_verify:
                cx.verify()
```

Find `        var = pk[1][0]` (just below `            root = pk[0]`) and insert immediately after it:

```python
        if cx is not None:
            cx.note_choice(var)
```

Replace `assign.py:1214` (`            nogoods.append(clause)`) with:

```python
            nogoods.append(clause)
            if cx is not None:
                cx.add_clause(clause)
```

- [ ] **Step 8: Thread the parameters through `compile.py`**

Replace `compile.py:129`:

```python
                 debug_search: dict | None = None) -> Result:
```

with:

```python
                 debug_search: dict | None = None,
                 clause_prop: dict | None = None,
                 clause_prop_verify: bool = False) -> Result:
```

Replace `compile.py:409`:

```python
                     debug_search=debug_search)
```

with:

```python
                     debug_search=debug_search,
                     clause_prop=clause_prop,
                     clause_prop_verify=clause_prop_verify)
```

- [ ] **Step 9: Run the wiring tests**

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -m pytest tests/test_box_pleat_clause_prop_wiring.py -v
```

Expected: 8 passed. If `test_sparse_lizard_exercises_the_cegar_path_and_verifies` fails on its NON-VACUITY assertion, stop: the subject no longer rejects and the rebind hook is untested. If it fails inside `verify()`, read the `ClauseIndexError` message — it names the clause, the variable and both counter values, and a mismatch on the CEGAR path is Trap 1.

- [ ] **Step 9b: Run the spec's named integration gate, and MEASURE THE INSTRUMENT'S TOTAL OVERHEAD -- dense `lizard` at 20,000**

**This step owes a figure nothing else produces.** `clause_index.py`'s docstring
and Task 5's README item 7 both say `observe_secs` is only the observe-side
cost and that "the true total overhead is the wall-clock difference measured in
Task 3". Task 3 is this task. If you skip the third arm below, Task 5 has to
cite a figure that does not exist -- so run all three and record the two
differences in your report.

Spec 9.2 names this subject and budget specifically. It is NOT added to the
test file: `verify()` walks every clause on every node, so it is too slow for
the standing suite. Run it once, here, and paste the output into the task
report. Write the snippet to a file and run it -- do NOT nest a heredoc inside
another heredoc, which zsh mis-terminates.

Write `$SCRATCH/gate.py`:

```python
import json, time
from box_pleat.compile import compile_tree

RULE6 = ("../docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/"
         "data/rule6_serve.json")
e = next(x for x in json.load(open(RULE6)) if x["subject"] == "lizard")
BASE = dict(dense=True, assign_budget=20_000, vertex_index=True)


def run(label, **kw):
    t0 = time.perf_counter()
    res = compile_tree(e["requested"], e["pairs"], **BASE, **kw)
    secs = time.perf_counter() - t0
    print(f"{label:22} {secs:8.2f}s stage={res.stage_reached} "
          f"fail={res.failure}")
    return secs, res


# ARM 1: the spec 9.2 integration gate. Both verifiers on -- this is the
# correctness check, and its wall time is NOT an overhead figure (verify()
# walks every clause on every node by design).
prop, sizes = {}, []
gate_secs, res = run("gate (both verify)", vertex_index_verify=True,
                     debug_clause_sizes=sizes, clause_prop=prop,
                     clause_prop_verify=True)
print(f"  nodes={prop['nodes']} clauses_observed={prop['clauses_total']} "
      f"clauses_stored={len(sizes)} unit_nodes={prop.get('unit_nodes', 0)} "
      f"dead_nodes={prop.get('dead_nodes', 0)} "
      f"probe_calls={prop['probe_calls']} "
      f"probe_secs={prop['probe_secs']:.2f} "
      f"observe_secs={prop['observe_secs']:.2f}")

# ARM 2: the instrument as a measurement run uses it -- no verify.
prop2, sizes2 = {}, []
on_secs, res2 = run("instrument ON", debug_clause_sizes=sizes2,
                    clause_prop=prop2)

# ARM 3: the same compile with no instrument at all. ARM 2 - ARM 3 is the
# TOTAL overhead, and it is the only figure that includes the bind/unbind/
# add_clause counter updates and note_choice, which observe_secs cannot see.
sizes3: list = []
off_secs, res3 = run("instrument OFF", debug_clause_sizes=sizes3)

# NOT `res2.fold == res3.fold`. At this budget dense `lizard` never
# reaches `emit`, so both folds are None and that comparison is VACUOUS --
# it passed while proving nothing when this step was first run. What IS
# meaningful at a budget-exhausted stage is that both arms consumed the
# search identically.
assert res2.stage_reached == res3.stage_reached, (
    f"stage differs: {res2.stage_reached} vs {res3.stage_reached}")
assert len(sizes2) == len(sizes3), (
    f"rejections differ: {len(sizes2)} vs {len(sizes3)} -- the instrument "
    "changed the search")
if res2.fold is None and res3.fold is None:
    print("NOTE: both folds are None (budget-exhausted), so this step does "
          "NOT check FOLD identity. That is pinned by "
          "test_instrument_does_not_change_a_sparse_compile, on sparse "
          "`lizard`, which does reach emit.")
else:
    assert res2.fold == res3.fold, "the instrument changed the emitted FOLD"
print(f"\nTOTAL overhead  = {on_secs - off_secs:+.2f}s "
      f"({(on_secs / off_secs - 1) * 100:+.1f}% of {off_secs:.2f}s)")
print(f"observe-side    = {prop2['observe_secs']:.2f}s "
      f"({prop2['observe_secs'] / off_secs * 100:.1f}% of the OFF arm)")
print(f"probe-only      = {prop2['probe_secs']:.2f}s")
print("QUOTE THE TOTAL as overhead. observe_secs is a component of it, "
      "and the difference between them is the bind-side maintenance cost.")
```

Then:

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 "$SCRATCH/gate.py"
```

Expected: all three arms complete without raising, and arms 2 and 3
agree on `stage_reached` and on their rejection count -- an instrument that
changes the search is a Critical defect, not a measurement. Note which identity
the step actually checked: at a budget-exhausted stage both folds are `None`, so
FOLD identity is pinned by the wiring tests on sparse `lizard` instead, and the
script says so rather than passing a vacuous comparison. A `ClauseIndexError` or
`VertexIndexError` here is a real counter bug; the message names the clause,
the variable and both counter values.

**Record all three wall times and both derived figures in your report, and
record `os.getloadavg()` alongside EACH arm.** The TOTAL overhead (arm 2 minus
arm 3) is the figure Task 5's README is required to quote as the instrument's
overhead, and this is the only step that measures it.

**One sample is not a figure.** Two single-run samples of this same pair of arms
on dense `lizard` at 20,000 nodes, taken on a shared machine, read **+0.59 s /
+3.2%** (18.98 s on, 18.39 s off) and **+0.33 s / +1.2%** (27.42 s vs 27.09 s):
the ratio moved 2.7x between them and the absolute times differed by ~47% (27.09 / 18.39 - 1 = 0.473 on the uninstrumented arm; the "~45%" this line carried until 2026-10-01 was my own arithmetic slip, caught when the README printed its inputs beside it).
Record the load average with each arm and state in your report that a single
ratio taken on a shared machine is **indicative only**. If you re-run it, add
the new sample to those two rather than replacing them; do not report a tighter
bound than the samples you actually hold support.

No *measurement* figure from this run is quotable -- the budget is 20,000, not
500,000, and spec 8.1 gates every reported measurement on the real budget. The
overhead figures are the exception and must be labelled with their budget: an
overhead *ratio* is a per-node property, so it is meaningful here, while
`dead_node_fraction` and the rest are not.

- [ ] **Step 10: Run the full standing regression gate**

Every box-pleat test file that calls `compile_tree` or `assign`, in full — no `-k` filter. This list is explicit because the last slice's gate named 3 files and left 11 unrun, including the only committed-golden FOLD test.

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -m pytest \
  tests/test_box_pleat_assign.py \
  tests/test_box_pleat_layers.py \
  tests/test_box_pleat_emit.py \
  tests/test_box_pleat_vertex_index_identity.py \
  tests/test_box_pleat_e2e.py \
  tests/test_box_pleat_core_in_loop.py \
  tests/test_box_pleat_interleave.py \
  tests/test_box_pleat_witness_identity.py \
  tests/test_probe_box_pleat.py \
  tests/test_box_pleat_pleat_filter.py \
  tests/test_box_pleat_cores.py \
  tests/test_box_pleat_clause_index.py \
  tests/test_box_pleat_clause_probe.py \
  tests/test_box_pleat_clause_prop_wiring.py \
  -q
```

Expected: all passed, 0 failed. Record the exact count in the commit message.

- [ ] **Step 11: Confirm the serve path is untouched**

```bash
cd <repo>
grep -c box_pleat mcp_harness/server.py
git diff --stat HEAD -- mcp_harness/box_pleat/layer_order.py
```

Expected: `0`, and an empty diff for `layer_order.py`.

- [ ] **Step 12: Verify the wiring mutations turn the suite red**

> **Mutation-harness limitation (recorded 2026-10-01, final review).** The
> harness in this section scores a mutation as "covered" on ANY non-zero pytest
> exit. It never checks that the mutation's own target test is among the
> failures, and the task reports record only aggregate "N failed" counts, so a
> mutation can be scored covered on an unrelated collateral failure (a test that
> breaks for a reason the mutation merely happens to trigger). A successor should
> parse the run (`-rf` or `--junitxml`) and assert that the specific test node id
> the mutation is meant to kill appears in the failure list. The 28 mutations in
> this slice were not re-run under that stricter rule.

The hooks are the part a reviewer cannot check by reading, so each gets a mutation.

```bash
cd <repo>
.venv/bin/python3 - <<'PY'
import pathlib, subprocess, sys

SRC = pathlib.Path("mcp_harness/box_pleat/assign.py")
orig = SRC.read_text()

MUTATIONS = [
    ("hook A: rebind replaced by VertexIndex's skip (Trap 1)",
     "                    if was_bound:\n"
     "                        cx.rebind(var, old_val, vals[i])\n"
     "                    else:\n"
     "                        cx.bind(var, vals[i])",
     "                    if not was_bound:\n"
     "                        cx.bind(var, vals[i])"),
    ("hook B: the `del value[var]` unbind dropped",
     "                if cx is not None:\n                    cx.unbind(var, vals[i])",
     "                if cx is None:\n                    cx.unbind(var, vals[i])"),
    ("hook C: the frame-pop unbind dropped",
     "                    if cx is not None:\n"
     "                        cx.unbind(popped, popped_val)",
     "                    if cx is None:\n"
     "                        cx.unbind(popped, popped_val)"),
    ("hook D: add_clause never called",
     "            nogoods.append(clause)\n"
     "            if cx is not None:\n"
     "                cx.add_clause(clause)",
     "            nogoods.append(clause)"),
]

failed_to_apply, still_green = [], []
for name, old, new in MUTATIONS:
    n = orig.count(old)
    if n != 1:
        failed_to_apply.append(f"{name}: pattern occurs {n} times, expected 1")
        continue
    SRC.write_text(orig.replace(old, new))
    r = subprocess.run(
        ["../.venv/bin/python3", "-m", "pytest",
         "tests/test_box_pleat_clause_prop_wiring.py", "-q"],
        cwd="mcp_harness", env={"PYTHONPATH": ".", "PATH": "/usr/bin:/bin"},
        capture_output=True, text=True)
    tail = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "(no output)"
    print(f"{name}\n    exit={r.returncode}  {tail}")
    if r.returncode == 0:
        still_green.append(name)
    SRC.write_text(orig)

assert SRC.read_text() == orig, "source not restored"
if failed_to_apply:
    print("\nDID NOT APPLY:"); [print("  " + x) for x in failed_to_apply]
if still_green:
    print("\nSTILL GREEN (test gap):"); [print("  " + x) for x in still_green]
sys.exit(1 if (failed_to_apply or still_green) else 0)
PY
```

Expected: all four non-zero, no "DID NOT APPLY", no "STILL GREEN", exit 0. Hook A is the one that matters most: it is the exact bug `VertexIndex`'s correct guard would produce here, and `verify()` on sparse `lizard` is what must catch it.

- [ ] **Step 13: Commit**

```bash
cd <repo>
git add mcp_harness/box_pleat/assign.py mcp_harness/box_pleat/compile.py \
        mcp_harness/tests/test_box_pleat_clause_prop_wiring.py
git commit -F "$SCRATCH/t3.txt"
```

Write `$SCRATCH/t3.txt` first, filling in the real test count from Step 10:

```
box_pleat: wire the clause index behind two inert parameters

assign() and compile_tree() gain clause_prop and clause_prop_verify, joining
debug_search / debug_clause_sizes / vertex_index / vertex_index_verify. Both
inert when unset, so an arm that does not ask for the instrument pays nothing.
No production behaviour changes; the serve path stays at
`grep -c box_pleat mcp_harness/server.py` == 0 and layer_order.py is
untouched.

Four hooks in retry() plus one at nogoods.append. The frame-pop unbind is
restructured to keep the popped value, which the original one-liner
discarded. The CEGAR reassignment goes through rebind(), NOT the skip
VertexIndex correctly uses there.

Sparse lizard is the gate: it is the only cheap subject whose sparse
labelling contradicts, so it is the only one that exercises the in-place
reassignment. It runs with clause_prop_verify=True and a non-vacuity
assertion on debug_clause_sizes, so the test cannot pass while the rebind
hook goes unexercised.

<N> passed across 14 named box-pleat files. Four wiring mutations verified
red, including replacing rebind with VertexIndex's skip.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---
### Task 4: the runner, smoke-validated at a reduced budget

**Files:**
- Create: `docs/superpowers/evidence/2026-09-30-clause-propagation/probe.py`

**Interfaces:**
- Consumes from Task 3: `compile_tree(nodes, pairs, *, dense=True, assign_budget=..., vertex_index=True, core_extraction=..., debug_clause_sizes=list, clause_prop=dict)`; the out-dict keys from Task 2.
- Produces, relied on by Task 5: `probe.py` writes `probe.json` at the path given as `sys.argv[1]`, with top-level keys `measured_utc`, `commit`, `run_completed`, `loadavg_at_start`, `config`, `rows`, `identity`, `verdict`. `rows` is a list of arm records; each carries `subject`, `core_extraction`, `budget`, `secs`, `truncated`, `stage_reached`, `assign_fail`, `layers_tried`, `rejections`, `clause_sizes`, `raw`, and the derived fractions.

**This task must NOT run the primary arms.** It builds the runner and proves it works at a reduced budget. The 500,000-node run is Task 5, after a reviewer has seen the runner. A ~30-minute measurement taken with a broken runner is 30 minutes and a wrong headline.

- [ ] **Step 1: Write the runner**

Create `docs/superpowers/evidence/2026-09-30-clause-propagation/probe.py`:

```python
"""What could the learned clauses have pruned during descent, and don't?

Spec: `../../specs/2026-09-30-clause-propagation-design.md`.

THE DEFECT. `assign`'s `hits_nogood()` is
`any(all(value.get(var) == val ...) for g in nogoods)`, so a clause with ANY
unbound variable reads `None` for it and is inert -- it can only fire when its
LAST variable is bound to the forbidden value. The solver has clause learning
and NO propagation.

WHY THE TWO OBVIOUS EXPLANATIONS DO NOT APPLY. Dense non-convergence is not
speed: the local CSP was 79.57% of runtime and the vertex index made the dense
corpus 5.740x faster with identity 8/8, and dense still does not converge
(`../2026-09-29-vertex-index/`). It is not clause width either: core
extraction narrowed the median clause 25.2x, 202 -> 8 solver variables, and
both arms still end on `AssignFail(kind='budget', site=500000)`
(`../2026-09-27-core-in-loop/`). What is left is that the clauses are applied
too LATE.

IDENTITY BEFORE ANY FIGURE (spec 8.2). Arm A must reproduce 113 rejections and
arm B 3, both ending on the node budget, against the committed control. A
figure from an arm that failed identity is not a measurement -- the arm solved
a different problem. `verdict()` refuses to name a band when identity failed.

EVERY HEADLINE IS A LOWER BOUND, twice over: only clauses ALREADY unit are
considered, and the cascade is ONE step, never a fixpoint. `dead_node_fraction`
is therefore never a predicted speedup -- a real propagator would change the
search path, so the node count it would reach is not derivable from here.

THE BREADTH BUDGET IS PESSIMISTIC BY CONSTRUCTION. Clause availability grows
with nodes, so the 50,000-node breadth arms UNDERSTATE it. A null breadth
result is weaker evidence than a positive one, and the README must say so.
"""
from __future__ import annotations

import datetime
import json
import os
import pathlib
import signal
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4] / "mcp_harness"))

from box_pleat.compile import compile_tree            # noqa: E402

RULE6 = (pathlib.Path(__file__).resolve().parents[4] / "docs" / "superpowers"
         / "evidence" / "2026-09-08-vlm-tree-authoring" / "data"
         / "rule6_serve.json")

#: Dense `lizard` at the real budget, both arms -- like-for-like with
#: `../2026-09-27-core-in-loop/`, whose figures are the control.
PRIMARY = "lizard"
PRIMARY_BUDGET = 500_000

#: The primary arms of the run plan, `core_extraction` per arm: A is extraction
#: off, B is extraction on. `main` builds the primary plan from this tuple and
#: `identity` requires one CHECKED row per entry, so the number of arms the
#: gate demands is the number the plan runs and cannot drift from it.
PRIMARY_ARMS = (False, True)

#: Arm A only, reduced budget. `octopus` and `dog` are excluded although they
#: too reach `assign` in dense: neither completed the dense labelling audit
#: (`../2026-09-24-dense-pleats/dense_labelling.json` carries no `dense_mv`
#: for either), so there is no dense control to compare a reading against.
BREADTH = ("frog", "horse", "bird", "guinea_pig")
BREADTH_BUDGET = 50_000

#: Spec 8.3. An unbounded run is why the pleat-filter halt table still has no
#: committed script. On expiry the arm records `truncated` and keeps the
#: partial measurement -- which survives because `ClauseIndex` writes into the
#: caller's dict every node rather than returning a summary at the end.
ARM_CAP_SECS = 1800.0

#: The committed control, `../2026-09-27-core-in-loop/ab.json`, keyed by
#: `core_extraction`. Arm A's 113 rejections reproduce the baseline exactly
#: there; arm B's clause-variable multiset is {5, 8, 8}.
BASELINE = {
    False: {"rejections": 113},
    True: {"rejections": 3, "clause_sizes": [5, 8, 8]},
}

#: Spec 4, fixed before any data existed. Descending thresholds.
BANDS = ((0.50, "PROPAGATION IS THE LEVER"),
         (0.05, "REAL BUT PARTIAL"),
         (0.00, "PROPAGATION REFUTED"))

#: Spec 4's attribution guard.
UNIT_GUARD = 0.01


class ArmTimeout(Exception):
    """The per-arm wall-clock cap expired.

    Subclasses `Exception` and NOT `RuntimeError`, so it escapes
    `compile_tree`'s `except (ValueError, RuntimeError, KeyError)`: a
    truncation must be recorded as a truncation, never folded into
    `AssignFail("error")`.
    """


def _alarm(signum, frame):
    raise ArmTimeout()


REPO = pathlib.Path(__file__).resolve().parents[4]


def _commit() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True, check=True, cwd=REPO).stdout.strip()


def _dirty(out_path: str) -> dict:
    """Whether the tree differs from the recorded `commit`. `commit` alone
    reads as a clean provenance even when the runner that produced the
    figures was an uncommitted edit, so the artifact states it. Untracked
    files count (a brand-new uncommitted runner is untracked), except the
    artifact's own output path, which a re-run would otherwise report as
    dirt it created itself."""
    res = subprocess.run(["git", "status", "--porcelain"], capture_output=True,
                         text=True, check=True, cwd=REPO)
    out = pathlib.Path(out_path).resolve()
    lines = []
    for ln in res.stdout.splitlines():
        if (REPO / ln[3:].strip().strip('"')).resolve() == out:
            continue
        lines.append(ln)
    return {"dirty": bool(lines), "dirty_paths": lines}


def _fail(f) -> dict | None:
    if f is None:
        return None
    return {"kind": getattr(f, "kind", None),
            "site": repr(getattr(f, "site", None))}


#: The out-dict keys `ClauseIndex.observe` writes UNCONDITIONALLY, on every
#: node it observes, so after any run that observed one node all of them are
#: present. Their absence means the instrument did not run (never constructed
#: on this path, the out-dict never passed, or `observe` never reached), and
#: nothing may default them: a defaulted `nodes` is how a dead instrument
#: becomes a `0.0` fraction, and `0.0 < 0.05` is "PROPAGATION REFUTED".
#:
#: The counters `unit_nodes`, `dead_nodes`, `unit_domain_*` and
#: `unit_var_chosen_nodes` are deliberately NOT in this tuple: `observe` creates
#: them lazily, the first time the event occurs, so a run with no unit node
#: legitimately has no `unit_nodes` key and `.get(..., 0)` is the correct read
#: for them. Whether the instrument ran is decided by the keys below.
REQUIRED_RAW = ("nodes", "live_total", "clauses_total", "probe_calls",
                "probe_secs", "observe_secs")


def instrument_gaps(prop: dict) -> list:
    """The `REQUIRED_RAW` keys absent from the index's out-dict, in order. One
    definition, called by `derived` (which records the answer on the row and
    refuses to compute a figure from absent keys) and by `identity` (which
    re-evaluates it on the row's `raw` block and does not trust the recorded
    flag, so an edited artifact cannot launder a gap)."""
    return [k for k in REQUIRED_RAW if k not in prop]


def derived(prop: dict, n_clauses: int) -> dict:
    """The spec 3.3 fractions. Computed here, not in the index: the index
    reports raw counts and is never asked what its own headline is.

    `n_clauses` is `len(debug_clause_sizes)`, the number of no-good clauses the
    solver actually stored, and it is the AUTHORITATIVE clause count: it is
    reported as `clauses_total`, and every consumer (the smoke check, `verdict`
    and the README) reads that key. The index's own `prop["clauses_total"]` is
    kept beside it as `clauses_total_observed` and is NOT interchangeable,
    because `ClauseIndex.observe` snapshots `len(self.size)` at the TOP of the
    solver's main loop, once per node. A clause learned on the LAST node --
    `nogoods.append` -> `add_clause` -> `retry()` returns False -> `return
    AssignFail("layer_unsat")` -- is appended after the final `observe` and
    never loops back to another, so the observed value can be one short. Any
    per-clause figure derived from the observed value would be inflated by
    1/n_clauses; with a handful of clauses (arm B stores 3) that is a third.
    The hook stays at the top of the loop (that is where the state a node
    inherited is visible); the discrepancy is corrected here, in the
    reporting, and left inspectable rather than hidden."""
    gaps = instrument_gaps(prop)
    out = {"instrument_ok": not gaps, "instrument_missing": gaps,
           "clauses_total": n_clauses}
    if gaps:
        # No figure from an instrument that did not report. Not zeros: absent.
        return out
    n = prop["nodes"]
    out = {
        "instrument_ok": True,
        "instrument_missing": [],
        "nodes": n,
        "unit_domain_2": prop.get("unit_domain_2", 0),
        "unit_domain_3": prop.get("unit_domain_3", 0),
        "unit_domain_other": prop.get("unit_domain_other", 0),
        "probe_calls": prop["probe_calls"],
        #: `probe_secs` = inside `probe()` only. `observe_secs` = the whole of
        #: `observe()`, including the work `probe_secs` cannot see: the
        #: OBSERVE-SIDE cost, not the total overhead (it excludes the
        #: bind/unbind/add_clause counter updates). >= `probe_secs` while
        #: probes run only through `observe`, which the runner guarantees.
        "probe_secs": round(prop["probe_secs"], 2),
        "observe_secs": round(prop["observe_secs"], 2),
        "clauses_total": n_clauses,
        "clauses_total_observed": prop["clauses_total"],
    }
    if not n:
        return out
    out["unit_node_fraction"] = round(prop.get("unit_nodes", 0) / n, 6)
    out["dead_node_fraction"] = round(prop.get("dead_nodes", 0) / n, 6)
    out["unit_var_chosen_fraction"] = round(
        prop.get("unit_var_chosen_nodes", 0) / n, 6)
    out["clause_availability"] = round(prop["live_total"] / n, 4)
    return out


def run_arm(entry, *, core_extraction: bool, budget: int) -> dict:
    """One dense arm. `vertex_index=True`: dense `lizard` measured 2.449x wall
    with identity byte-identical 8/8, so the search path is the same and the
    measurement is unaffected (`../2026-09-29-vertex-index/timing.json`)."""
    prop: dict = {}
    sizes: list = []
    row = {"subject": entry["subject"], "core_extraction": core_extraction,
           "budget": budget, "truncated": False, "loadavg": os.getloadavg()}
    signal.signal(signal.SIGALRM, _alarm)
    signal.setitimer(signal.ITIMER_REAL, ARM_CAP_SECS)
    t0 = time.perf_counter()
    try:
        res = compile_tree(entry["requested"], entry["pairs"], dense=True,
                           assign_budget=budget, vertex_index=True,
                           core_extraction=core_extraction,
                           debug_clause_sizes=sizes,
                           # clause_prop_verify is deliberately NOT set:
                           # verify() is O(clauses x nodes), prohibitive at
                           # 500,000 nodes. Counter correctness was checked
                           # only at 20,000 nodes / 10 rejections (Task 3
                           # gate), so it is NOT established at this budget
                           # (README s1 and s8).
                           clause_prop=prop)
        row["stage_reached"] = res.stage_reached
        row["assign_fail"] = _fail(res.failure)
        row["layers_tried"] = res.layers_tried
    except ArmTimeout:
        row["truncated"] = True
        row["stage_reached"] = None
        row["assign_fail"] = None
        row["layers_tried"] = None
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        row["secs"] = round(time.perf_counter() - t0, 1)
    row["rejections"] = len(sizes)
    row["clause_sizes"] = sorted(sizes)
    #: `raw` is the index's own out-dict verbatim, so `raw["clauses_total"]`
    #: is the OBSERVED value (see `derived`). Read the clause count from the
    #: row's `clauses_total`, never from `raw`.
    row["raw"] = dict(prop)
    row.update(derived(prop, len(sizes)))
    return row


def identity(rows: list) -> dict:
    """Spec 8.2. The gate is BOTH primary arms reproducing the control; one arm
    is not the gate. A truncated arm was never given the chance to reach the
    control's rejection count, so it cannot be checked -- and it is therefore a
    NAMED FAILURE, not a skip: skipping it let `checked == 1` pass on half the
    evidence. Every arm in `PRIMARY_ARMS` must be checked, or the gate fails
    and says which arm fell short and why.

    The gate also requires that the instrument PRODUCED its figures (see
    `REQUIRED_RAW`): reproducing the control proves the solver unchanged, not
    that anything was measured."""
    failures = []
    checked = set()
    for row in rows:
        if row["budget"] != PRIMARY_BUDGET:
            continue
        arm = "B" if row["core_extraction"] else "A"
        if row["truncated"]:
            failures.append(
                f"arm {arm}: truncated at the {ARM_CAP_SECS:.0f} s cap after "
                f"{row.get('nodes')} nodes, so it could not be checked "
                f"against the control; the gate needs both primary arms")
            continue
        checked.add(row["core_extraction"])
        exp = BASELINE[row["core_extraction"]]
        # The instrument must have RUN, and run to the budget. The solver
        # reproducing the control says nothing about this: it reproduces 113
        # and 3 whether or not the index was ever constructed, and a silent
        # instrument would otherwise surface as a 0.0 fraction.
        raw = row.get("raw") or {}
        gaps = instrument_gaps(raw)
        if not raw:
            failures.append(
                f"arm {arm}: the instrument wrote nothing (empty raw block), "
                f"so no figure from this arm is a measurement")
        else:
            for key in gaps:
                failures.append(
                    f"arm {arm}: the instrument never wrote the required "
                    f"counter {key!r}")
        # EXACT, no tolerance. `assign` decrements its node budget at the top
        # of the loop and calls `observe` after the budget test, so a run that
        # ends on `AssignFail('budget', B)` has observed exactly B nodes
        # (budget B admits B iterations and fails on B+1). The smoke run
        # confirms it: starfish at budget 4000 reads nodes == 4000. Anything
        # else means observe was skipped on some nodes or the arm ended
        # elsewhere.
        if "nodes" in raw and raw["nodes"] != row["budget"]:
            failures.append(
                f"arm {arm}: the instrument observed {raw['nodes']} nodes "
                f"but the arm's budget is {row['budget']}")
        site = (row["assign_fail"] or {}).get("site")
        if site != repr(row["budget"]):
            failures.append(
                f"arm {arm}: AssignFail site {site}, control says "
                f"{row['budget']!r} (a layer-budget end is also kind "
                f"'budget' and carries no node site)")
        if row["rejections"] != exp["rejections"]:
            failures.append(
                f"arm {arm}: {row['rejections']} rejections, control says "
                f"{exp['rejections']}")
        kind = (row["assign_fail"] or {}).get("kind")
        if kind != "budget":
            failures.append(
                f"arm {arm}: AssignFail kind {kind!r}, control says 'budget'")
        if "clause_sizes" in exp and row["clause_sizes"] != exp["clause_sizes"]:
            failures.append(
                f"arm {arm}: clause sizes {row['clause_sizes']}, control says "
                f"{exp['clause_sizes']}")
    for core in PRIMARY_ARMS:
        arm = "B" if core else "A"
        if core not in checked and not any(
                row["budget"] == PRIMARY_BUDGET
                and row["core_extraction"] == core for row in rows):
            failures.append(f"arm {arm}: no row at the primary budget, so it "
                            f"could not be checked against the control")
    return {"checked_arms": len(checked),
            "passed": not failures and len(checked) == len(PRIMARY_ARMS),
            "failures": failures}


def _band(dead: float) -> str:
    return next(label for thr, label in BANDS if dead >= thr)


def verdict(rows: list, ident: dict) -> dict:
    """Spec 4. Refuses to name a band unless identity passed. The refusal is
    first, before any figure is read; and a truncated arm never contributes a
    band-deciding figure even then (it cannot while the gate passes, since a
    truncated primary arm fails the gate -- this keeps that true by
    construction rather than by the gate's behaviour).

    BOTH primary arms must have contributed a `dead_node_fraction`, and each is
    banded on its own. The overall band is the maximum, as before, but it is
    never stated unqualified when the arms disagree: a band decided by one arm
    alone is exactly what a clause-scarcity artifact looks like (the 4,000-node
    smoke read arm B at `unit_node_fraction` 0.501 on 3 clauses against arm
    A's 0.0035), so the split is surfaced here, in the artifact, instead of
    being left for the README to walk back. No arm is picked as the winner."""
    if not ident["passed"]:
        return {"band": None,
                "reason": "identity gate failed -- no band may be claimed",
                "identity_failures": ident["failures"]}
    primary = {("B" if r["core_extraction"] else "A"): r for r in rows
               if r["budget"] == PRIMARY_BUDGET and not r["truncated"]}
    names = ["B" if core else "A" for core in PRIMARY_ARMS]
    missing = [a for a in names
               if primary.get(a, {}).get("dead_node_fraction") is None
               or primary.get(a, {}).get("unit_node_fraction") is None]
    if missing:
        return {"band": None,
                "reason": ("no band: primary arm(s) " + ", ".join(missing)
                           + " produced no dead_node_fraction / "
                           "unit_node_fraction; both arms must contribute")}
    deads = {a: primary[a]["dead_node_fraction"] for a in names}
    best = max(deads.values())
    per_arm = {a: {"dead_node_fraction": deads[a], "band": _band(deads[a])}
               for a in names}
    agree = len({v["band"] for v in per_arm.values()}) == 1
    out = {"band_per_arm": per_arm, "arms_agree": agree,
           "dead_node_fraction_max": best,
           "dead_node_fraction_per_arm": deads}
    if agree:
        out["band"] = _band(best)
    else:
        out["band"] = ("ARMS DISAGREE: " + "; ".join(
            f"{a}={per_arm[a]['band']}" for a in names))
        out["band_split"] = {
            "note": ("the two primary arms fall in different bands; the "
                     "maximum-arm band is recorded below for reference and is "
                     "NOT the verdict. Read clauses_total and "
                     "clause_availability per arm before attributing."),
            "band_max_arm": _band(best),
            "per_arm": [{"arm": a,
                         "clauses_total": primary[a].get("clauses_total"),
                         "clause_availability":
                             primary[a].get("clause_availability"),
                         "unit_node_fraction":
                             primary[a].get("unit_node_fraction")}
                        for a in names],
        }
    units = {a: primary[a]["unit_node_fraction"] for a in names}
    guard = all(u < UNIT_GUARD for u in units.values())
    out["attribution_guard_fired"] = guard
    if guard:
        out["attribution"] = {
            "note": ("clauses essentially never go unit in EITHER arm; "
                     "clause_availability and clauses_total decide whether "
                     "the clauses are too wide or too few"),
            "per_arm": [{"core_extraction": primary[a]["core_extraction"],
                         "clauses_total": primary[a].get("clauses_total"),
                         "clause_availability":
                             primary[a].get("clause_availability"),
                         "unit_node_fraction": units[a]}
                        for a in names],
        }
    return out


def main(out_path: str, *, smoke: bool = False) -> int:
    entries = {e["subject"]: e for e in json.load(open(RULE6))}
    art = {
        "measured_utc": datetime.datetime.now(datetime.UTC).isoformat(),
        "commit": _commit(),
        **_dirty(out_path),
        "run_completed": False,
        "loadavg_at_start": os.getloadavg(),
        "config": {
            "primary": PRIMARY,
            "primary_budget": PRIMARY_BUDGET,
            "breadth": list(BREADTH),
            "breadth_budget": BREADTH_BUDGET,
            "arm_cap_secs": ARM_CAP_SECS,
            "vertex_index": True,
            "smoke": smoke,
        },
        "rows": [],
    }

    def flush():
        with open(out_path, "w") as fh:
            json.dump(art, fh, indent=1, sort_keys=True)

    if smoke:
        # Reduced budget, reduced breadth. Proves the runner works; produces
        # NO quotable figure, which is why `config.smoke` is recorded and the
        # identity gate is skipped (its control is the real budget's).
        art["config"]["primary_budget"] = 4_000
        art["config"]["breadth"] = ["starfish"]
        art["config"]["breadth_budget"] = 4_000
        plan = [(PRIMARY, False, 4_000), (PRIMARY, True, 4_000),
                ("starfish", False, 4_000)]
    else:
        plan = [(PRIMARY, core, PRIMARY_BUDGET) for core in PRIMARY_ARMS]
        plan += [(s, False, BREADTH_BUDGET) for s in BREADTH]

    for subject, core, budget in plan:
        print(f"-> {subject} core_extraction={core} budget={budget}", flush=True)
        row = run_arm(entries[subject], core_extraction=core, budget=budget)
        art["rows"].append(row)
        flush()                      # after EVERY arm, so a crash keeps what ran
        print(f"   {row['secs']}s nodes={row.get('nodes')} "
              f"rejections={row['rejections']} "
              f"unit={row.get('unit_node_fraction')} "
              f"dead={row.get('dead_node_fraction')} "
              f"truncated={row['truncated']}", flush=True)

    art["identity"] = ({"checked_arms": 0, "passed": False,
                        "failures": ["smoke run: identity is not gated at a "
                                     "reduced budget"]}
                       if smoke else identity(art["rows"]))
    art["verdict"] = verdict(art["rows"], art["identity"])
    art["run_completed"] = True
    flush()

    print("\nidentity:", art["identity"])
    print("verdict:", art["verdict"])
    return 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--smoke"]
    sys.exit(main(args[0], smoke="--smoke" in sys.argv[1:]))
```

- [ ] **Step 2: Run the smoke arm**

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -u \
  ../docs/superpowers/evidence/2026-09-30-clause-propagation/probe.py \
  /tmp/clause-smoke.json --smoke
```

Write the smoke artifact to `/tmp`, not the evidence directory — a smoke artifact committed beside the real one is a figure waiting to be quoted by mistake.

Expected: exit 0; three `->` lines; every row prints `nodes=` equal to 4,000 or lower and `truncated=False`; `verdict` reports `band: None` with the reason `identity gate failed -- no band may be claimed`, because a smoke run deliberately does not gate identity.

- [ ] **Step 3: Check the smoke artifact's shape**

```bash
cd <repo>
.venv/bin/python3 - <<'PY'
import json
a = json.load(open("/tmp/clause-smoke.json"))
assert a["run_completed"] is True, "the runner did not reach the end"
assert a["config"]["smoke"] is True
assert a["commit"] and a["measured_utc"]
assert len(a["rows"]) == 3, len(a["rows"])
for r in a["rows"]:
    assert r["nodes"] > 0, r
    assert r["nodes"] <= 4000, r
    #: `clauses_total` is `len(debug_clause_sizes)` by construction (see
    #: `derived`), so equating it with `rejections` would be a tautology.
    #: What CAN fail is the instrument's own snapshot: it may trail the stored
    #: count by exactly one (a clause learned on the final node, after the last
    #: `observe`) and never by more, and never exceed it.
    gap = r["clauses_total"] - r["clauses_total_observed"]
    assert gap in (0, 1), (
        f"clauses_total_observed={r['clauses_total_observed']} vs "
        f"clauses_total={r['clauses_total']}: the index's snapshot may trail "
        "the stored clause count by one, never anything else")
    u = r["raw"].get("unit_nodes", 0)
    assert r["raw"].get("dead_nodes", 0) <= u, "dead nodes exceed unit nodes"
    assert r["raw"].get("unit_var_chosen_nodes", 0) <= u
    #: `probe_calls >= 0` cannot fail for a counter. What CAN fail: a probe
    #: was called on a node with no unit clause, or time was charged without
    #: a call.
    #: Against the RAW value, never the derived one. `derived()` rounds
    #: `probe_secs` to 2 decimals, so a cheap smoke arm with a handful of
    #: probes reports 0.0 and this assertion would fail on correct code.
    raw_secs = r["raw"].get("probe_secs", 0.0)
    assert (r["probe_calls"] > 0) == (raw_secs > 0.0), (
        f"probe_calls={r['probe_calls']} but raw probe_secs={raw_secs}")
    assert r["observe_secs"] >= r["probe_secs"], (
        "observe() wraps every probe, so its time cannot be smaller")
    assert r["probe_calls"] >= u or u == 0, (
        "fewer probes than unit nodes: the probe loop was skipped")
print("rows ok")
for r in a["rows"]:
    print(f"  core={r['core_extraction']!s:5} {r['subject']:10} "
          f"nodes={r['nodes']:6} rej={r['rejections']:3} "
          f"clauses={r['clauses_total']}(obs {r['clauses_total_observed']}) "
          f"unit={r.get('unit_node_fraction')} dead={r.get('dead_node_fraction')} "
          f"avail={r.get('clause_availability')} probe_s={r['probe_secs']} "
          f"observe_s={r['observe_secs']}")
print("verdict:", a["verdict"]["band"], "-", a["verdict"].get("reason"))
PY
```

Expected: `rows ok`, three printed rows, and `verdict: None - identity gate failed -- no band may be claimed`.

- [ ] **Step 4: Check the cap actually fires**

The cap is the one mechanism that cannot be tested by the real run, because the real run must not hit it. Temporarily set it very low and confirm a truncated row still carries its partial measurement.

```bash
cd <repo>
P=docs/superpowers/evidence/2026-09-30-clause-propagation/probe.py
.venv/bin/python3 - "$P" <<'PY'
import pathlib, subprocess, sys, json
p = pathlib.Path(sys.argv[1]); orig = p.read_text()
old, new = "ARM_CAP_SECS = 1800.0", "ARM_CAP_SECS = 2.0"
assert orig.count(old) == 1, orig.count(old)
p.write_text(orig.replace(old, new))
try:
    r = subprocess.run(["../.venv/bin/python3", "-u",
                        "../" + sys.argv[1], "/tmp/clause-cap.json", "--smoke"],
                       cwd="mcp_harness", env={"PYTHONPATH": ".",
                                               "PATH": "/usr/bin:/bin"},
                       capture_output=True, text=True)
    print("exit", r.returncode)
    a = json.load(open("/tmp/clause-cap.json"))
    trunc = [x for x in a["rows"] if x["truncated"]]
    print("truncated rows:", len(trunc), "of", len(a["rows"]))
    for x in trunc:
        print(f"  secs={x['secs']} nodes={x['nodes']} "
              f"stage={x['stage_reached']}")
    assert trunc, "the cap never fired -- it cannot be trusted in the real run"
    assert all(x["nodes"] > 0 for x in trunc), (
        "a truncated arm lost its partial measurement")
    assert a["run_completed"] is True
finally:
    p.write_text(orig)
    assert p.read_text() == orig
print("cap ok, source restored")
PY
```

Expected: `exit 0`, at least one truncated row, every truncated row carrying `nodes > 0`, then `cap ok, source restored`.

- [ ] **Step 5: Commit the runner only**

```bash
cd <repo>
git add docs/superpowers/evidence/2026-09-30-clause-propagation/probe.py
git status --short docs/superpowers/evidence/2026-09-30-clause-propagation/
git commit -F "$SCRATCH/t4.txt"
```

`git status --short` must show only `probe.py`. No smoke artifact may be staged. Write `$SCRATCH/t4.txt` first:

```
evidence: the clause-propagation runner, smoke-validated

Two dense lizard arms at 500,000 nodes (core_extraction off and on) plus four
breadth subjects at 50,000, all with vertex_index=True -- dense lizard
measured 2.449x with identity byte-identical 8/8, so the search path is the
same and the measurement is unaffected.

Identity is gated before any figure is quoted: arm A must reproduce 113
rejections and arm B 3, both ending on the node budget, against the committed
core-in-loop control. verdict() returns band None when identity fails, so a
contaminated run cannot name a band.

The per-arm cap raises an ArmTimeout that escapes compile_tree's catch, and
the partial measurement survives because ClauseIndex writes into the caller's
dict every node. Verified by temporarily setting the cap to 2 s: truncated
rows keep nodes > 0.

No figure from this commit is quotable -- the smoke artifact is written to
/tmp on purpose and config.smoke is recorded in the JSON.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

### Task 5: the measurement and the verdict

**Files:**
- Create: `docs/superpowers/evidence/2026-09-30-clause-propagation/probe.json`
- Create: `docs/superpowers/evidence/2026-09-30-clause-propagation/README.md`

**Interfaces:**
- Consumes from Task 4: `probe.py`, and the artifact keys it writes.
- Produces: nothing code depends on. The README's band is what gates any follow-on spec.

- [ ] **Step 1: Check the machine is quiet before starting**

```bash
uptime && ps -Ao pcpu,comm -r | head -8
```

The first timing run of the previous slice was contaminated — `dog` read 902.5 s against a committed 537.3 s, with load peaking at 12.1 and an unrelated `pytest` alongside. If the 1-minute load average is above ~4 or another Python job is running, wait. `probe.py` records `loadavg_at_start` and each row's `loadavg` so a reader can check this after the fact, but a contaminated run still has to be re-taken.

- [ ] **Step 2: Run the full measurement in the background**

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -u \
  ../docs/superpowers/evidence/2026-09-30-clause-propagation/probe.py \
  ../docs/superpowers/evidence/2026-09-30-clause-propagation/probe.json
```

Run it in the background and let it finish. Expected wall clock: the control's two `lizard` arms were 1,052.0 s and 954.9 s; at `vertex_index`'s measured 2.449× that is roughly 430 s and 390 s, plus probe cost, plus four breadth arms — call it 25–40 minutes. Each arm flushes the artifact as it completes, so partial progress is readable at any time. Do **not** poll in a tight loop; check back when the process exits.

- [ ] **Step 3: Read the identity gate FIRST, before looking at any fraction**

```bash
cd <repo>
.venv/bin/python3 - <<'PY'
import json
a = json.load(open("docs/superpowers/evidence/2026-09-30-clause-propagation/probe.json"))
print("run_completed:", a["run_completed"])
print("commit:", a["commit"], "| measured:", a["measured_utc"])
print("identity:", json.dumps(a["identity"], indent=1))
PY
```

If `identity.passed` is `False`, **stop**. Do not quote a fraction. Write the README as a contamination report naming each failure, and hand it back — spec 8.2 makes the passing guard the thing that licenses claiming a row. The most likely single cause is that `vertex_index=True` does not preserve the search at 500,000 nodes, which the vertex-index slice never verified (its identity run was at 20,000); if so, that is itself the finding, and the fix is to re-run with `vertex_index=False` and roughly 2.4× the wall clock.

- [ ] **Step 4: Read every figure back out of the artifact**

```bash
cd <repo>
.venv/bin/python3 - <<'PY'
import json
a = json.load(open("docs/superpowers/evidence/2026-09-30-clause-propagation/probe.json"))
hdr = ("subject", "core", "budget", "secs", "nodes", "rej", "clauses",
       "cl_obs", "avail", "unit_frac", "dead_frac", "chosen_frac", "dom2", "dom3",
       "probe_s", "observe_s", "trunc")
print(" | ".join(f"{h:>10}" for h in hdr))
for r in a["rows"]:
    print(" | ".join(f"{v!s:>10}" for v in (
        r["subject"], r["core_extraction"], r["budget"], r["secs"],
        r["nodes"], r["rejections"], r["clauses_total"],
        r["clauses_total_observed"], r.get("clause_availability"), r.get("unit_node_fraction"),
        r.get("dead_node_fraction"), r.get("unit_var_chosen_fraction"),
        r["unit_domain_2"], r["unit_domain_3"], r["probe_secs"],
        r["observe_secs"], r["truncated"])))
print()
print("verdict:", json.dumps(a["verdict"], indent=1))
PY
```

Copy these numbers into the README from this output. Do not transcribe anything from the run's own stdout — the previous slice's README records that discipline explicitly, and the `share_of_remainder` rounding incident is what it cost to learn.

- [ ] **Step 4b: Answer the `unit_node_fraction` question with data, before writing it up**

Why this check exists. The Task 4 smoke run, at a **4,000-node budget and NOT quotable**, read `unit_node_fraction` **0.501** on the extraction-on arm, which had stored only **3** clauses, against **0.0035** on the extraction-off arm: a gap of two orders of magnitude. That is either the real signal this slice is looking for or an artifact of having almost no clauses, and a smoke figure cannot say which. It is recorded here only so the question is not forgotten by the time the real run finishes; it is not a result and must not appear in the README as one.

The README must answer, from the real run's figures and **whatever the answer turns out to be**: *is a high `unit_node_fraction` on the extraction-on arm attributable to clause tightness or to clause scarcity?* Spec §4's attribution guard already separates these two causes and must be applied here, not only in the both-arms-near-zero case that `attribution_guard_fired` detects. A high figure on one arm is the case the flag does not cover.

```bash
cd <repo>
.venv/bin/python3 - <<'PY'
import json
a = json.load(open("docs/superpowers/evidence/2026-09-30-clause-propagation/probe.json"))
print(f"{'core':>5} {'clauses_total':>13} {'avail':>8} {'unit_frac':>10} {'dead_frac':>10} {'min_clause_size':>16}")
for r in a["rows"]:
    if r["budget"] != a["config"]["primary_budget"]:
        continue
    cs = r["clause_sizes"]
    print(f"{r['core_extraction']!s:>5} {r['clauses_total']:>13} "
          f"{r.get('clause_availability')!s:>8} {r.get('unit_node_fraction')!s:>10} "
          f"{r.get('dead_node_fraction')!s:>10} {(min(cs) if cs else None)!s:>16}")
PY
```

Compare `unit_node_fraction` against `clauses_total` and `clause_availability` across **both** arms. Questions the data must settle, each answered with a number from this table: how many clauses does each arm hold, and how many are live per node on average (`clause_availability`)? Does the arm with the higher `unit_node_fraction` have a high or a low clause count? If a handful of clauses go unit at most nodes, is that because they are tight (few free variables) or because there are so few that the same ones are counted repeatedly? State the answer in the README under item 4, with the figures. If the data does not settle it, say so; do not choose the more flattering reading.

- [ ] **Step 5: Write the README**

Create `docs/superpowers/evidence/2026-09-30-clause-propagation/README.md`. It must contain, in this order:

1. **Title and provenance.** The question, the spec path, the script, the artifact, the exact reproduction command, and a line stating that every figure is read back from `probe.json` after the process exited. Give date, commit, exit status and wall clock — and say that `run_completed` and `commit` are in the artifact itself, unlike the predecessor, whose README asked for exactly that.
2. **The identity gate, before any headline.** `identity.checked_arms`, `passed`, and the arm-by-arm comparison against the control's 113 / 3 rejections. State plainly that this is also the 500,000-node identity evidence the vertex-index slice left open, and that it does **not** flip `vertex_index`'s default.
3. **The headline: the band.** `verdict.band`, with `dead_node_fraction` per arm beside the three thresholds (0.50 / 0.05) that were fixed before the run. If `verdict.arms_agree` is false, `verdict.band` reads `ARMS DISAGREE: ...` by design: report each arm's own band from `verdict.band_per_arm`, state the split as the headline, and do not quote `band_split.band_max_arm` as the verdict. Say in one sentence what the band licenses — and, if it is `PROPAGATION IS THE LEVER`, that it justifies a follow-on spec and does **not** authorise the wiring.
4. **The attribution: whenever `attribution_guard_fired` is true, AND always the Step 4b question (is a high `unit_node_fraction` on the extraction-on arm tightness or scarcity?).** `clauses_total` (the row's authoritative count, i.e. `len(debug_clause_sizes)`; **not** `raw["clauses_total"]`, which is the index's per-node snapshot and can trail it by one) and `clause_availability` per arm, and which of the two causes the data supports: arm A's clauses too wide to go unit (control median 202 solver variables, needing 201 agreeing binds), or arm B having too few clauses to matter. Do not conflate them.
5. **Domain sizes.** `unit_domain_2` against `unit_domain_3`. If most unit clauses land on 3-valued variables, propagation is weak *by construction* — a unit clause there prunes one of three values and forces nothing — and that is a separate finding from the band.
6. **`unit_var_chosen_fraction`.** Its complement is the nodes at which a unit clause existed and the search chose to work on something else. Note that spec §3.3's `unit_latency_nodes` was withdrawn during implementation and why.
7. **Instrument cost.** `probe_calls`, `probe_secs` (the inside of `probe()` only) and `observe_secs` (the whole of `observe()`, which also pays for the `sorted`, `free_var_of` and `prefer` passes `probe_secs` cannot see). **Publish `observe_secs` as the observe-side cost**, as a share of that arm's own `secs`, and show `probe_secs` beside it as the probe-only portion. **State in the README that it is NOT the instrument's total overhead**: it excludes every `bind`/`unbind`/`add_clause` counter update and `note_choice` (the per-assignment maintenance, about 4.4 counter updates per bind on the widest arm), and the true total overhead is the wall-clock difference measured in Task 3, which is the figure to quote as overhead. Never write "overhead N%" from `observe_secs` alone; a README that does understates the cost. **Report the total overhead as a RANGE, from both Task 3 Step 9b samples, with the budget named**: dense `lizard` at 20,000 nodes read **+0.59 s / +3.2%** in one run and **+0.33 s / +1.2%** in an independent rerun, so write it as "roughly 1-3% at a 20,000-node budget" and call it a **noisy bound, not a point estimate**. Include one sentence saying the machine was shared (the two runs' absolute times differed by ~47%) and that both samples were single runs. Do not quote either sample alone, do not average them into one number, and do not state a tighter bound than those two samples support; a ratio is a per-node property, so quote it only for the 20,000-node budget it was measured at and not as a figure for the 500,000-node arms.
8. **Breadth.** The four subjects' rows, each beside `lizard`'s, and the stated bias: 50,000 nodes **understates** clause availability, so a null breadth result is weaker evidence than a positive one. Name `octopus` and `dog` as excluded and why.
9. **What this does NOT establish.** Reproduce spec §12 in full, adapted to the numbers actually measured: it cannot show dense converges or cannot; `dead_node_fraction` is a lower bound and not a predicted speedup; a null breadth result is weak; and it says nothing about the eight subjects that never reach `emit` — only `rabbit` fails in the stage this instrument watches, and it is in neither arm.
10. **Anything that surprised you.** If a number contradicts something this plan or the spec asserts, say so with the figure, and correct the spec in the same commit. The previous two slices each shipped a wrong claim that a later check caught; the cheapest place to catch the next one is here.

- [ ] **Step 6: Verify every figure in the README appears in the artifact**

```bash
cd <repo>
D=docs/superpowers/evidence/2026-09-30-clause-propagation
.venv/bin/python3 - "$D" <<'PY'
import json, pathlib, re, sys
d = pathlib.Path(sys.argv[1])
art = d.joinpath("probe.json").read_text()
readme = d.joinpath("README.md").read_text()
vals = set(re.findall(r"\d+\.\d+|\b\d{2,}\b", art))
#: Numbers in the README that are NOT in the artifact must each be either a
#: figure cited to another directory (the control's 113 / 3 / 202 / 2.449,
#: spec thresholds) or arithmetic shown where it appears.
CITED = {"113", "202", "2.449", "0.50", "0.05", "500000", "50000", "20000",
         "5.740", "79.57", "25.2", "1800", "4425", "166666", "1052.0",
         "954.9", "2026", "2001", "1996", "1999", "879", "3.3", "8.2", "12"}
unknown = sorted(v for v in set(re.findall(r"\d+\.\d+|\b\d{2,}\b", readme))
                 if v not in vals and v not in CITED)
print("README numbers not in probe.json and not in the cited allow-list:")
for v in unknown:
    print("   ", v)
print("\nCheck each one by hand: it must be cited to its source directory, or "
      "be arithmetic whose inputs are shown, or it is a transcription error.")
PY
```

This does not fail the build — it is a checklist. Resolve every line it prints before committing: either the number is cited inline to the directory it came from, or its arithmetic is shown, or it is wrong.

- [ ] **Step 7: Re-run the standing regression gate**

Nothing in Task 5 touches production code, so this is a guard against a stray edit made while reading.

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -m pytest \
  tests/test_box_pleat_assign.py \
  tests/test_box_pleat_layers.py \
  tests/test_box_pleat_emit.py \
  tests/test_box_pleat_vertex_index_identity.py \
  tests/test_box_pleat_e2e.py \
  tests/test_box_pleat_core_in_loop.py \
  tests/test_box_pleat_interleave.py \
  tests/test_box_pleat_witness_identity.py \
  tests/test_probe_box_pleat.py \
  tests/test_box_pleat_pleat_filter.py \
  tests/test_box_pleat_cores.py \
  tests/test_box_pleat_clause_index.py \
  tests/test_box_pleat_clause_probe.py \
  tests/test_box_pleat_clause_prop_wiring.py \
  -q
```

Then:

```bash
cd <repo>
git diff --stat HEAD -- mcp_harness/
grep -c box_pleat mcp_harness/server.py
```

Expected: all tests pass, an empty `mcp_harness/` diff, and `0`.

- [ ] **Step 8: Commit**

```bash
cd <repo>
git add docs/superpowers/evidence/2026-09-30-clause-propagation/probe.json \
        docs/superpowers/evidence/2026-09-30-clause-propagation/README.md
git commit -F "$SCRATCH/t5.txt"
```

Write `$SCRATCH/t5.txt` first, with the band and the real figures substituted — not the placeholders:

```
evidence: <BAND> -- dead_node_fraction <X> on dense lizard

Identity passed on <N> primary arms: arm A reproduced <A> rejections against
the control's 113 and arm B <B> against 3, both ending on
AssignFail(kind='budget', site=500000). That is also the 500,000-node
identity evidence the vertex-index slice left open; it does NOT flip that
default.

<one or two sentences: the band reached, and what the data says about
whether clause propagation is a lever -- including the attribution when the
guard fired, and the unit_domain_2 vs unit_domain_3 split.>

Every figure is read back from probe.json after the process exited. The
artifact records measured_utc, commit and run_completed itself, which the
predecessor's README asked a successor to do.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

## Appendix: the seven spec mutations, and where each is verified

| spec 9.1 # | mutation | verified in |
|---|---|---|
| 1 | drop the `n_agree` increment in `bind` | Task 1, Step 5 |
| 2 | never increment `n_contra` | Task 1, Step 5 |
| 3 | make `rebind` a skip (Trap 1) | Task 1, Step 5 (unit) and Task 3, Step 12 hook A (integration) |
| 4 | `add_clause` counts against an empty state (Trap 2) | Task 1, Step 5 |
| 5 | unit test `n_agree == size` instead of `size − 1` | Task 1, Step 5 |
| 6 | probe only the first remaining value of a 3-valued variable | Task 2, Step 5 |
| 7 | probe leaves `value[var]` set (Trap 3) | Task 2, Step 5 |

Four further mutations not in the spec are added because the code invited them: a probe that does not dedupe a repeated domain value, a histogram folded into the short-circuiting probe loop (Task 2, Step 5), and the three dropped `assign.py` hooks (Task 3, Step 12).
