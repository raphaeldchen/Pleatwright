# Incremental Vertex Index Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace dense `assign()`'s per-node rescan of every interior vertex with an incrementally maintained index, so the same vertex is selected with the same tie-break, faster.

**Architecture:** A new module `box_pleat/vertex_index.py` owns three per-vertex counts and two "non-empty" sets, maintained O(degree) at the only three sites that mutate `value`. `pick()` reads the index instead of calling `eligible()` on every vertex. The whole change is behind a flag defaulting to off, and correctness is established by **identity** — a correct index selects the same vertex, so sparse output must be byte-identical and dense must match both node count and a digest of the chosen-variable sequence.

**Tech Stack:** Python 3.14, the existing `mcp_harness/box_pleat/` package. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-09-29-vertex-index-design.md`. Every `§` below refers to it. **Read §1.1 first, then §11** — this is not a convergence fix and cannot be. 3.492× is `lizard`'s pair ceiling, **not this slice's cap**: ceilings are per subject and span 1.362× to 112.913×, and the measured realised speedups span 1.095× to 28.154×. Never print `lizard`'s ceiling beside another subject's realised figure (spec §5.2, corrected).

## Global Constraints

* **Python is `../.venv/bin/python3`, run from `mcp_harness`.** `mcp_harness/conftest.py`'s autouse fixture imports `mesh_to_tree`, gating all test collection on skeletor/trimesh/networkx/numpy.
* **Never pass `--timeout`** to pytest (no `pytest-timeout` in that venv) and **never run `pytest tests/`** (5,167 tests, >3 h). Always name test files, and **run the FULL named file, never a `-k` filtered subset.**
* **Do NOT modify `layer_order.py`.** `mv_symmetrize` on the serve path shares it (CLAUDE.md).
* **`grep -c box_pleat mcp_harness/server.py` must stay 0.** The serve path never sees this.
* **The flag defaults to OFF** in every signature. With it off, every code path must be byte-identical to today — that is what Task 2's identity tests assert.
* **The same vertex must be chosen, always.** This is the entire correctness argument (§4.4). Any change that alters which vertex `pick` returns is a defect, not an optimisation, and makes every timing figure meaningless.
* **Counts are over DISTINCT variables, never incident pieces** (§3.3 Trap 1). `var_of[i] = min(base, mirror)` (`assign.py:688`), so a piece and its mirror share one variable and both can touch the same vertex on the axis `x = N`.
* **The tie-break is positional and must be made explicit** (§3.3 Trap 3). `assign.py:919` keeps `best` only on strict `<`, so ties go to the earliest vertex in `interior` order (`:772` builds it as a list). Iterating a Python set instead would silently pick differently.
* **Two "non-empty" sets, both maintained, never rebuilt** (§3.2). `pleat_open` is recomputed every node (`:901`) and flips in **both** directions, so a single phase-dependent set would be rebuilt over all of `interior` on each flip — the very cost this removes.
* **A ceiling is not a speedup, and every ceiling is PER SUBJECT.** The realised figure must be printed beside **that subject's own** pair ceiling, recomputed from `evidence/2026-09-29-local-csp-profile/profile.json` as `1/(1 − (pick + free_vars_at)/total)` using the components' own `self_secs`. `lizard`'s are 1.907× (`free_vars_at` alone) and 3.492× (the pair); they are **not** the slice's cap, and printing them beside another subject's realised figure is the defect spec §5.2 was corrected to forbid. Measured range 1.362× (`starfish`) to 112.913× (`octopus`). The three highest are numerically unstable — their share is ≈0.99, so `1/(1 − x)` divides by ≈0.01 — and must never be quoted as precise.
* **Anti-vacuity is required, not optional** (§7). Every identity assertion must be demonstrated able to fail under a deliberately broken index, and the demonstration recorded. The predecessor found five tests on this branch that could not fail.
* **Never use bare `git stash` / `git stash pop`** — the stash stack is shared with other worktrees and concurrent sessions. Use a temporary WIP commit.
* **Commit messages end with** `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`. Write them with `git commit -F <file>`; a heredoc containing backticks or `§` has already been mangled by zsh in this project.
* **Never use tardigrade / water bear as a test subject** — OWNER INSTRUCTION.

## File Structure

| File | Responsibility |
|---|---|
| `mcp_harness/box_pleat/vertex_index.py` (create) | `VertexIndexError`, `VertexIndex` — the counts, the two sets, `bind`/`unbind`/`select`, and `snapshot()` for the verifier. No knowledge of `assign`'s internals beyond the five structures it is handed. |
| `mcp_harness/tests/test_box_pleat_vertex_index.py` (create) | unit tests for the index alone. **No compile runs** — every fixture is hand-built, so Trap 1 is tested directly rather than hoped for from a real subject. |
| `mcp_harness/box_pleat/assign.py` (modify) | build the index; hook `:978` / `:982` / `:987`; `pick` reads it; `_scan()` extracted so the verifier's reference **is** production code rather than a copy of it. |
| `mcp_harness/box_pleat/compile.py` (modify) | thread `vertex_index`, `vertex_index_verify` and `debug_search` through to `assign()`. |
| `mcp_harness/tests/test_box_pleat_vertex_index_identity.py` (create) | sparse byte-identity and dense identity on the two cheap subjects, plus the verify mode. |
| `docs/superpowers/evidence/2026-09-29-vertex-index/ab.py` (create) | the corpus instrument: identity pass then timing pass, 8 subjects. |
| `docs/superpowers/evidence/2026-09-29-vertex-index/ab.json` (generated) | per-subject identity verdicts and timings. |
| `docs/superpowers/evidence/2026-09-29-vertex-index/README.md` (create) | §5.2's figures, §8's limits, and §9's default-flip recommendation. |

Four tasks. Task 1 is the data structure and is testable with no compile at all. Task 2 wires it in and proves identity on cheap subjects. Task 3 spends the corpus runs. Task 4 writes the verdict.

---

### Task 1: The index module and its unit tests

**Files:**
- Create: `mcp_harness/box_pleat/vertex_index.py`
- Create: `mcp_harness/tests/test_box_pleat_vertex_index.py`

**Interfaces:**
- Consumes: nothing. This module imports only from the standard library and must not import `assign`.
- Produces, and Task 2 depends on these exact names:
  - `VertexIndexError(Exception)`
  - `VertexIndex(interior, inc, var_of, domain, pleat_pref, value)` — constructor
  - `.count_at(v, pleat_open) -> int`
  - `.bind(x) -> None` / `.unbind(x) -> None`
  - `.select(pleat_open) -> tuple | None` (a vertex, which is an `(x, y)` tuple)
  - `.pool_calls: int` and `.pool_total: int` — how many times `select` ran and the summed size of the pool it scanned, so §5.2's "vertices visited per node" is **measured** rather than inferred. Deliberately **not** in `snapshot()`, so two snapshots still compare by value.
  - `.snapshot() -> dict` — `{"n_free": {...}, "n_free_domain": {...}, "n_free_pleat": {...}, "nonempty_all": frozenset, "nonempty_pleat": frozenset}`, for the verifier

**Context you need.** In `assign.py`, a *variable* is an integer piece index used as a canonical representative: `var_of[i] = min(base, mirror)` (`:688`) maps piece index → variable, so **two different pieces can share one variable**. `inc[v]` maps a point `(x, y)` → the list of piece indices incident to it (`:768-771`). `interior` is a **list** of the non-boundary points (`:772`). `domain` maps variable → value order for column-contour pieces; `pleat_pref` maps variable → value order for pleat-path pieces. `value` maps variable → its assigned label, and a variable is *free* exactly when it is absent from `value`.

The reference implementation you must match is `free_vars_at` (`:856-861`):

```python
fv = {var_of[i] for i in inc[v] if i in var_of and var_of[i] not in value}
return sorted(fv, key=lambda var: (var not in domain, var))
```

Note the **set** comprehension: aliased variables collapse. This is Trap 1.

- [ ] **Step 1: Write the failing unit tests**

Create `mcp_harness/tests/test_box_pleat_vertex_index.py`:

```python
"""The incremental vertex index, tested without compiling anything.

Spec: `docs/superpowers/specs/2026-09-29-vertex-index-design.md`.

Every fixture here is hand-built. That is deliberate: the index's one
genuinely subtle requirement -- that counts are over DISTINCT variables
rather than incident pieces (spec section 3.3 Trap 1) -- arises on a real
subject only at mirror-axis vertices, so a test that borrowed a real
`inc`/`var_of` might never exercise it and would pass for a wrong
implementation. `test_trap1_*` below builds the aliasing directly.
"""
import pytest

from box_pleat.vertex_index import VertexIndex, VertexIndexError


def _plain():
    """Four interior vertices, one variable each, no aliasing, no overlap.

    inc maps point -> incident piece indices; var_of maps piece -> variable.
    Pieces 0..3 carry variables 0..3. Vertex A touches pieces 0 and 1, so
    it has two free variables; B touches 1 and 2; C touches 2; D touches 3.
    """
    A, B, C, D = (1, 1), (1, 2), (2, 1), (2, 2)
    interior = [A, B, C, D]
    inc = {A: [0, 1], B: [1, 2], C: [2], D: [3]}
    var_of = {0: 0, 1: 1, 2: 2, 3: 3}
    domain = {0: ["F"]}                 # variable 0 only
    pleat_pref = {3: ["M", "V"]}        # variable 3 only, disjoint from domain
    return interior, inc, var_of, domain, pleat_pref, (A, B, C, D)


def _pleat_mixed():
    """Five interior vertices built so the pleat and non-pleat pools DIFFER.

    `_plain()` cannot reach the pleat branch of `select` on a non-empty
    pool, and it cannot reach it usefully even if it did: no vertex there
    holds a `pleat_pref` variable AND a non-pleat one, so `n_free` and
    `n_free_pleat` never cross zero at different times, and every vertex in
    `nonempty_pleat` carries the same count. This fixture fixes all three.

    Variables 20, 22, 23, 24, 26 are `pleat_pref` keys; 21 and 25 are not.
    `domain` is EMPTY and must stay so -- the constructor refuses any
    overlap with `pleat_pref`, and the pleat branch's whole justification is
    that no eligible variable is a domain variable.

      N   piece 5    -> var 25            n_free 1, n_free_pleat 0
      W   pieces 3,4 -> vars 23, 24       n_free 2, n_free_pleat 2
      MX  pieces 0,1 -> vars 20, 21       n_free 2, n_free_pleat 1  (MIXED)
      T1  piece 2    -> var 22            n_free 1, n_free_pleat 1
      T2  piece 6    -> var 26            n_free 1, n_free_pleat 1

    So the pleat phase sees a genuine three-way tie at count 1 (MX, T1, T2),
    a genuine count difference (W at 2, which must lose), and one vertex
    that must not be in the pool at all (N, whose only variable is not a
    pleat variable). `interior` puts N and W FIRST, so a `select` that
    pooled `nonempty_all`, or that dropped the count from its key, would
    return one of them rather than MX.
    """
    N, W, MX, T1, T2 = (1, 1), (1, 2), (2, 1), (2, 2), (3, 1)
    interior = [N, W, MX, T1, T2]
    inc = {N: [5], W: [3, 4], MX: [0, 1], T1: [2], T2: [6]}
    var_of = {0: 20, 1: 21, 2: 22, 3: 23, 4: 24, 5: 25, 6: 26}
    domain: dict = {}
    pleat_pref = {x: ["M", "V"] for x in (20, 22, 23, 24, 26)}
    return interior, inc, var_of, domain, pleat_pref, (N, W, MX, T1, T2)


def _domain_flip():
    """Two vertices whose `select` winner changes when a domain bind lands.

    E holds variable 5 (in `domain`) and 6 (not); F holds 7 (not). While 5
    is free, E's key is `(False, 1, ...)` and beats F's `(True, 1, ...)`
    however `interior` is ordered. Once 5 is bound, both read `(True, 1,
    ...)` and the POSITIONAL tie-break decides -- and `interior` lists F
    first precisely so the answer moves.
    """
    E, F = (1, 1), (2, 2)
    interior = [F, E]                   # F first: the post-bind tie goes to F
    inc = {E: [0, 1], F: [2]}
    var_of = {0: 5, 1: 6, 2: 7}
    domain = {5: ["F"]}
    pleat_pref: dict = {}
    return interior, inc, var_of, domain, pleat_pref, (E, F)


def _two_counts():
    """Two NON-domain vertices with 2 and 1 free variables respectively.

    Nothing here is in `domain`, so the key's first component is `True` for
    both vertices and cannot decide. That leaves `len(fv)` -- the
    most-constrained-vertex heuristic itself -- as the only component that
    can, which is the point: every other `select` test in this file is
    decided by component 1 or by the positional tie-break.
    """
    X, Y = (1, 1), (2, 2)
    inc = {X: [0, 1], Y: [2]}
    var_of = {0: 30, 1: 31, 2: 32}
    return inc, var_of, (X, Y)


def test_counts_at_construction():
    interior, inc, var_of, domain, pleat_pref, (A, B, C, D) = _plain()
    ix = VertexIndex(interior, inc, var_of, domain, pleat_pref, {})
    s = ix.snapshot()
    assert s["n_free"] == {A: 2, B: 2, C: 1, D: 1}
    assert s["n_free_domain"] == {A: 1, B: 0, C: 0, D: 0}
    assert s["n_free_pleat"] == {A: 0, B: 0, C: 0, D: 1}
    assert s["nonempty_all"] == frozenset({A, B, C, D})
    assert s["nonempty_pleat"] == frozenset({D})


def test_counts_respect_an_already_bound_value_at_construction():
    """The constructor must read `value`, not assume it is empty. `assign`
    happens to build the index before the search binds anything, so this is
    the one property no live run would ever exercise."""
    interior, inc, var_of, domain, pleat_pref, (A, B, C, D) = _plain()
    ix = VertexIndex(interior, inc, var_of, domain, pleat_pref, {0: "M"})
    s = ix.snapshot()
    assert s["n_free"] == {A: 1, B: 2, C: 1, D: 1}
    assert s["n_free_domain"] == {A: 0, B: 0, C: 0, D: 0}


def test_counts_respect_an_already_bound_value_in_every_structure():
    """The sibling of the test above, covering the three structures it does
    not: `n_free_pleat` and BOTH `nonempty_*` sets must also read `value`.

    Variable 2 (at B and C) and variable 3 (at D, the only pleat variable)
    start bound, so C and D are empty from the outset and `nonempty_pleat`
    starts EMPTY. `test_counts_at_construction` cannot catch a constructor
    that ignores `value` in these three places, because there every vertex
    is non-empty and `free` equals `vars_at`.

    Kills: `n_free_pleat[v] = sum(1 for x in xs if x in pleat_pref)` (`xs`
    for `free`, leaving D at 1 and `nonempty_pleat` at `{D}`), and
    `nonempty_all = set(interior)` (leaving C and D in it), neither of which
    any other test in this file detects.
    """
    interior, inc, var_of, domain, pleat_pref, (A, B, C, D) = _plain()
    ix = VertexIndex(interior, inc, var_of, domain, pleat_pref,
                     {2: "M", 3: "V"})
    s = ix.snapshot()
    assert s["n_free"] == {A: 2, B: 1, C: 0, D: 0}
    assert s["n_free_domain"] == {A: 1, B: 0, C: 0, D: 0}
    assert s["n_free_pleat"] == {A: 0, B: 0, C: 0, D: 0}, \
        "n_free_pleat was built over vars_at instead of the free variables"
    assert s["nonempty_all"] == frozenset({A, B}), \
        "nonempty_all was seeded from interior rather than from n_free"
    assert s["nonempty_pleat"] == frozenset(), \
        "nonempty_pleat was seeded without consulting value"


def test_trap1_two_pieces_sharing_a_variable_count_once():
    """Spec section 3.3 Trap 1. Pieces 0 and 1 are both incident to A and
    `var_of` maps BOTH to variable 7 -- exactly what `var_of[i] =
    min(base, mirror)` produces for a piece and its mirror meeting on the
    axis. A count over incident pieces reads 2; the correct count over
    distinct variables reads 1.
    """
    A, B = (1, 1), (1, 2)
    interior = [A, B]
    inc = {A: [0, 1], B: [2]}
    var_of = {0: 7, 1: 7, 2: 8}
    ix = VertexIndex(interior, inc, var_of, {}, {}, {})
    assert ix.snapshot()["n_free"][A] == 1, "counted incident pieces, not distinct variables"


def test_trap1_binding_an_aliased_variable_decrements_once():
    """The other half of Trap 1: the count must not go negative, and the
    vertex must leave `nonempty_all` on the first bind rather than needing
    two. A per-piece implementation reads 1 here instead of 0.
    """
    A, B = (1, 1), (1, 2)
    ix = VertexIndex([A, B], {A: [0, 1], B: [2]}, {0: 7, 1: 7, 2: 8}, {}, {}, {})
    ix.bind(7)
    s = ix.snapshot()
    assert s["n_free"][A] == 0, "decremented once per piece instead of once per variable"
    assert A not in s["nonempty_all"]


def test_bind_then_unbind_restores_every_count_exactly():
    interior, inc, var_of, domain, pleat_pref, _ = _plain()
    ix = VertexIndex(interior, inc, var_of, domain, pleat_pref, {})
    before = ix.snapshot()
    for x in (0, 1, 2, 3):
        ix.bind(x)
    mid = ix.snapshot()
    assert mid["nonempty_all"] == frozenset(), mid
    assert mid["nonempty_pleat"] == frozenset(), mid
    for x in (3, 2, 1, 0):
        ix.unbind(x)
    assert ix.snapshot() == before


def test_nonempty_transitions_in_both_directions():
    """C has exactly one variable, so it is the vertex whose membership
    flips on a single bind. Both directions are asserted: a `discard`-only
    implementation passes the first half and fails the second."""
    interior, inc, var_of, domain, pleat_pref, (A, B, C, D) = _plain()
    ix = VertexIndex(interior, inc, var_of, domain, pleat_pref, {})
    assert C in ix.snapshot()["nonempty_all"]
    ix.bind(2)
    assert C not in ix.snapshot()["nonempty_all"]
    assert B in ix.snapshot()["nonempty_all"], "B still has variable 1 free"
    ix.unbind(2)
    assert C in ix.snapshot()["nonempty_all"]


def test_count_at_switches_with_the_phase():
    """`count_at(v, pleat_open)` is what `pick`'s sticky fast path reads.
    Inside the pleat phase only `pleat_pref` variables are eligible, so A
    (two free variables, neither a pleat variable) must read 0."""
    interior, inc, var_of, domain, pleat_pref, (A, B, C, D) = _plain()
    ix = VertexIndex(interior, inc, var_of, domain, pleat_pref, {})
    assert ix.count_at(A, False) == 2
    assert ix.count_at(A, True) == 0, "pleat phase must use the pleat count"
    assert ix.count_at(D, True) == 1


def test_a_variable_touching_no_interior_vertex_is_a_noop():
    """`vertices_of` has no entry for such a variable. Binding it must not
    raise and must not perturb any count -- correct rather than merely
    harmless, since `free_vars_at` is only ever called on `interior`."""
    interior, inc, var_of, domain, pleat_pref, _ = _plain()
    ix = VertexIndex(interior, inc, var_of, domain, pleat_pref, {})
    before = ix.snapshot()
    ix.bind(999)
    assert ix.snapshot() == before


def test_overlapping_domain_and_pleat_pref_is_refused():
    """Spec section 3.1. `eligible`'s docstring asserts that a `domain`
    variable is never a `pleat_pref` key, and `select` relies on it to treat
    the first key component as constant during the pleat phase. If it were
    ever false the shortcut would be wrong, so it is checked rather than
    trusted."""
    interior, inc, var_of, _, _, _ = _plain()
    with pytest.raises(VertexIndexError, match="domain.*pleat_pref"):
        VertexIndex(interior, inc, var_of, {1: ["F"]}, {1: ["M", "V"]}, {})


def _reference_select(interior, inc, var_of, domain, pleat_pref, value, pleat_open):
    """`assign.py`'s `_scan()` loop transcribed, and ONLY used to check
    `select`. Named by symbol, not by line range: the range this docstring
    once carried (`:913-923`) had already drifted across the boundary into
    the next function.

    This is a deliberate duplicate, confined to this file. Task 2 does the
    opposite for the live verifier -- there the reference IS production code,
    extracted as `_scan()` -- because a checker that re-implements production
    can agree with itself while both are wrong. Here the point is to pin the
    POSITIONAL tie-break independently, so a copy is what is wanted.
    """
    best = None
    for v in interior:
        fv = {var_of[i] for i in inc[v] if i in var_of and var_of[i] not in value}
        fv = sorted(fv, key=lambda var: (var not in domain, var))
        if pleat_open:
            fv = [x for x in fv if x in pleat_pref]
        if not fv:
            continue
        key = (fv[0] not in domain, len(fv))
        if best is None or key < best[0]:
            best = (key, v)
    return None if best is None else best[1]


def test_select_matches_the_positional_tie_break_on_a_three_way_tie():
    """Spec section 3.3 Trap 3. Vertices P, Q, R each have exactly one free
    non-domain variable, so all three share the key `(True, 1)`. The old
    loop keeps `best` on strict `<`, so the winner is the EARLIEST in
    `interior` order -- P. An implementation that iterates the `nonempty`
    set directly returns whichever vertex hashing happens to yield first.

    Anti-vacuity: the tie is asserted to exist (three vertices, one key) and
    the fixture is checked to be order-sensitive by re-running with
    `interior` reversed, which must then select R.
    """
    P, Q, R = (1, 1), (2, 2), (3, 3)
    inc = {P: [0], Q: [1], R: [2]}
    var_of = {0: 10, 1: 11, 2: 12}
    args = (inc, var_of, {}, {}, {})

    keys = {v: 1 for v in (P, Q, R)}
    assert len(set(keys.values())) == 1, "fixture does not actually tie"

    fwd = [P, Q, R]
    assert VertexIndex(fwd, *args).select(False) == P
    assert _reference_select(fwd, inc, var_of, {}, {}, {}, False) == P

    rev = [R, Q, P]
    assert VertexIndex(rev, *args).select(False) == R, \
        "select ignored `interior` order -- the positional tie-break is lost"
    assert _reference_select(rev, inc, var_of, {}, {}, {}, False) == R


def test_select_prefers_a_free_domain_variable_over_a_smaller_count():
    """The first key component outranks the count: a vertex WITH a free
    domain variable beats one with fewer free variables but none in
    `domain`. E has 2 free variables, one of them in `domain`; F has 1 and
    none. The old key is `(fv[0] not in domain, len(fv))`, so E's `(False,
    2)` beats F's `(True, 1)`.
    """
    E, F = (1, 1), (2, 2)
    interior = [E, F]
    inc = {E: [0, 1], F: [2]}
    var_of = {0: 5, 1: 6, 2: 7}
    domain = {5: ["F"]}
    assert VertexIndex(interior, inc, var_of, domain, {}, {}).select(False) == E
    assert _reference_select(interior, inc, var_of, domain, {}, {}, False) == E


def test_select_records_the_pool_it_scanned():
    """Spec section 5.2's measured quantity. Four vertices are non-empty, so
    one `select` must record a pool of 4; after binding variable 2, vertex C
    drops out and the next `select` records 3. Asserting the DELTA rather
    than the total is what makes this able to fail -- a `pool_total` that
    simply accumulated `len(interior)` would pass a single-call check."""
    interior, inc, var_of, domain, pleat_pref, (A, B, C, D) = _plain()
    ix = VertexIndex(interior, inc, var_of, domain, pleat_pref, {})
    ix.select(False)
    assert (ix.pool_calls, ix.pool_total) == (1, 4)
    ix.bind(2)
    ix.select(False)
    assert ix.pool_calls == 2
    assert ix.pool_total - 4 == 3, "second select did not record the shrunk pool"


def test_select_returns_none_when_nothing_is_free():
    interior, inc, var_of, domain, pleat_pref, _ = _plain()
    ix = VertexIndex(interior, inc, var_of, domain, pleat_pref, {})
    for x in (0, 1, 2, 3):
        ix.bind(x)
    assert ix.select(False) is None
    assert ix.select(True) is None


def test_binding_a_domain_variable_moves_the_domain_count():
    """`_delta`'s `n_free_domain` maintenance, asserted DIRECTLY.

    Every other `n_free_domain` assertion in this file reads it at
    construction, and `test_bind_then_unbind_restores_every_count_exactly`
    compares before to after -- so a maintenance step that never moves the
    count satisfies both. This asserts the intermediate state, in both
    directions, and asserts the non-domain variable at the same vertex does
    NOT move it.

    Kills: `if in_dom: self.n_free_domain[v] += d` -> `if False: ...`.
    """
    interior, inc, var_of, domain, pleat_pref, (A, B, C, D) = _plain()
    ix = VertexIndex(interior, inc, var_of, domain, pleat_pref, {})
    assert ix.snapshot()["n_free_domain"][A] == 1, "fixture: A must start at 1"

    ix.bind(1)                          # variable 1 is at A but NOT in domain
    assert ix.snapshot()["n_free_domain"][A] == 1, \
        "a non-domain bind moved n_free_domain -- the in_dom guard is inverted"

    ix.bind(0)                          # variable 0 IS in domain, and at A
    assert ix.snapshot()["n_free_domain"][A] == 0, \
        "n_free_domain did not drop on a domain bind -- dead maintenance in _delta"

    ix.unbind(0)
    assert ix.snapshot()["n_free_domain"][A] == 1, \
        "n_free_domain did not come back on unbind"


def test_select_lets_the_domain_component_change_the_winner_after_a_bind():
    """The other half of the gap above: dead `n_free_domain` maintenance must
    change the ANSWER, not merely a count.

    While variable 5 is free, E wins on the first key component even though
    F has the same free count and comes first in `interior`. Binding 5 takes
    E's free domain count to 0, both vertices read `(True, 1, ...)`, and the
    positional tie-break hands it to F. An index that never decremented
    `n_free_domain` still returns E.

    Kills: `if in_dom: self.n_free_domain[v] += d` -> `if False: ...`.
    """
    interior, inc, var_of, domain, pleat_pref, (E, F) = _domain_flip()
    ix = VertexIndex(interior, inc, var_of, domain, pleat_pref, {})
    assert ix.select(False) == E, "fixture: E must win while variable 5 is free"
    assert _reference_select(interior, inc, var_of, domain, pleat_pref,
                            {}, False) == E

    ix.bind(5)
    assert ix.select(False) == F, \
        "E still won after its only domain variable was bound -- " \
        "n_free_domain is not being maintained"
    assert _reference_select(interior, inc, var_of, domain, pleat_pref,
                            {5: "F"}, False) == F


def test_binding_a_mixed_vertexs_pleat_variable_empties_only_the_pleat_pool():
    """`n_free` and `n_free_pleat` crossing zero at DIFFERENT times.

    MX holds one pleat variable (20) and one non-pleat variable (21).
    Binding 20 takes `n_free_pleat[MX]` to 0 while `n_free[MX]` is still 1,
    so MX must leave `nonempty_pleat` and STAY in `nonempty_all`. No vertex
    in `_plain()` mixes the two, so no existing test can distinguish the two
    sets' maintenance.

    Kills: `nonempty_pleat` driven from `n` instead of `p` in `_delta`
    (MX would stay in `nonempty_pleat`); and the `p`-branch's `discard`
    removed altogether.
    """
    interior, inc, var_of, domain, pleat_pref, (N, W, MX, T1, T2) = _pleat_mixed()
    ix = VertexIndex(interior, inc, var_of, domain, pleat_pref, {})
    s = ix.snapshot()
    assert s["n_free"][MX] == 2 and s["n_free_pleat"][MX] == 1, \
        "fixture: MX must hold one pleat variable and one non-pleat variable"
    assert MX in s["nonempty_all"] and MX in s["nonempty_pleat"]
    assert N in s["nonempty_all"] and N not in s["nonempty_pleat"], \
        "fixture: N must be all-only"

    ix.bind(20)
    s = ix.snapshot()
    assert s["n_free"][MX] == 1 and s["n_free_pleat"][MX] == 0
    assert MX not in s["nonempty_pleat"], \
        "nonempty_pleat is tracking n_free rather than n_free_pleat"
    assert MX in s["nonempty_all"], \
        "nonempty_all dropped a vertex that still has a free variable"

    ix.unbind(20)
    assert MX in ix.snapshot()["nonempty_pleat"], \
        "nonempty_pleat was not restored on unbind"


def test_select_in_the_pleat_phase_uses_the_pleat_pool_and_the_pleat_count():
    """The pleat branch of `select`, on a NON-EMPTY pool.

    The file's other `select(True)` call is the all-bound `None` case, so
    every line of the pleat branch beyond `if not pool` was unexecuted. Here
    the pool is `{W, MX, T1, T2}`: N is excluded (its only variable is not a
    pleat variable), W loses on count (2 against 1), and MX, T1, T2 tie at
    1 so the positional tie-break decides. Both `interior` orders are
    asserted, because the correct answers differ (MX forward, T2 reversed)
    while any order-blind implementation returns the same vertex for both.

    Kills: pooling `nonempty_all` in the pleat phase (N would win with a
    pleat count of 0); replacing the pleat key with `(0, self.order[v])`
    (W would win on position); and dropping `self.order[v]` from the pleat
    key (one of the two orders must then be wrong).
    """
    interior, inc, var_of, domain, pleat_pref, (N, W, MX, T1, T2) = _pleat_mixed()
    ref = (inc, var_of, domain, pleat_pref, {})

    counts = {MX: 1, T1: 1, T2: 1}
    assert len(set(counts.values())) == 1, "fixture does not actually tie"

    ix = VertexIndex(interior, inc, var_of, domain, pleat_pref, {})
    assert ix.count_at(W, True) == 2, "fixture: W must break the tie by count"
    assert ix.select(True) == MX, \
        "pleat-phase select did not honour the pleat pool, the pleat count " \
        "and the positional tie-break together"
    assert _reference_select(interior, *ref, True) == MX

    rev = [T2, T1, MX, W, N]
    ixr = VertexIndex(rev, inc, var_of, domain, pleat_pref, {})
    assert ixr.select(True) == T2, \
        "pleat-phase select ignored `interior` order -- the positional " \
        "tie-break is lost inside the pleat phase"
    assert _reference_select(rev, *ref, True) == T2

    # And the count component still binds once the tie is broken by a bind:
    # MX leaves the pool entirely, leaving T1 (count 1) against W (count 2).
    ix.bind(20)
    assert ix.select(True) == T1, \
        "pleat-phase select preferred the larger pleat count"
    assert _reference_select(interior, inc, var_of, domain, pleat_pref,
                            {20: "M"}, True) == T1


def test_select_prefers_the_smaller_free_count_under_both_orders():
    """`len(fv)` -- the most-constrained-vertex heuristic, and the entire
    reason `pick` exists -- asserted on its own.

    Neither X nor Y has a free domain variable, so component 1 is `True` for
    both and cannot decide; only the count can. X comes FIRST in `interior`
    and still loses, which is what rules out the positional tie-break as the
    explanation. The reversed order is asserted too, so the test cannot be
    passing for a positional reason in either direction.

    Kills: dropping `self.n_free[v]` from the non-pleat `min` key -- X would
    then win the forward case on position alone.
    """
    inc, var_of, (X, Y) = _two_counts()
    args = (inc, var_of, {}, {}, {})

    ix = VertexIndex([X, Y], *args)
    assert (ix.count_at(X, False), ix.count_at(Y, False)) == (2, 1), \
        "fixture: the counts must differ, or nothing is being tested"

    assert ix.select(False) == Y, \
        "select ignored the free-variable count -- the " \
        "most-constrained-vertex heuristic is gone"
    assert _reference_select([X, Y], inc, var_of, {}, {}, {}, False) == Y

    assert VertexIndex([Y, X], *args).select(False) == Y, \
        "select ignored the free-variable count with the order reversed"
    assert _reference_select([Y, X], inc, var_of, {}, {}, {}, False) == Y
```

- [ ] **Step 2: Run the tests to verify they fail for the right reason**

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -m pytest tests/test_box_pleat_vertex_index.py -q
```

Expected: a collection error, `ModuleNotFoundError: No module named 'box_pleat.vertex_index'`. If you see anything else, stop — the fixture or the import path is wrong, not the module.

- [ ] **Step 3: Write the module**

Create `mcp_harness/box_pleat/vertex_index.py`:

```python
"""An incrementally maintained index of free variables per interior vertex.

Spec: `docs/superpowers/specs/2026-09-29-vertex-index-design.md`.

WHY THIS EXISTS. `evidence/2026-09-29-local-csp-profile/` measured dense
`assign()`'s 79.57% residual and found it is ~99% variable selection and
0.3-1.5% constraint checking. `pick()` rescans EVERY interior vertex at
EVERY node (`assign.py`'s `_scan`), each vertex calling `eligible` ->
`free_vars_at`, which builds a set and sorts it -- 4,237 calls per
node on `lizard`, 20,858 on `octopus`, of which >=90.4% return empty. Yet
between two consecutive `pick()` calls exactly ONE variable changes state.

THE MECHANISM IS WATCHED LITERALS, transposed. Chaff (Moskewicz et al., DAC
2001) visits a clause only when one of its watched literals becomes false;
this visits a vertex only when an incident variable changes state. The same
fix principle is being applied right now on the value-order side of a
production CP solver: Glasgow Constraint Solver issue #879, "Seven of eleven
value-order heuristics do work proportional to domain width, at every node",
whose remedy is to compute the shape you need without materialising the
structure. That is exactly section 3.1 below.

THE KEY REDUCTION. `pick`'s selection key is `(fv[0] not in domain,
len(fv))` and `fv` is sorted by `(var not in domain, var)`, so domain
variables sort FIRST and `fv[0] in domain` holds iff SOME free variable at
`v` is in `domain`. The key is therefore two integers per vertex and no list
need be built -- `assign`'s main loop reads only `fv[0]` (its
`var = pk[1][0]`) anyway, so the full sorted list is materialised once per
node, for the winner alone.

WHAT THIS MUST NOT DO. Change which vertex is chosen. A correct index makes
the search IDENTICAL, not merely equivalent, which is what lets the identity
gates in the spec's section 4 stand in for a correctness proof. Two traps
make that easy to get wrong and both are handled below: variables ALIAS
(`var_of[i] = min(base, mirror)`), so counts are over distinct variables;
and the tie-break is POSITIONAL, so it is made an explicit key component
rather than left to iteration order.

NOT A CONVERGENCE FIX. Dense still will not converge, and no subject moved
from budget-capped to solved. But the predecessor's 1.907x (`free_vars_at`
alone) and 3.492x (the pair) are `LIZARD`'s ceilings and nobody else's --
ceilings are per subject, and the realised dense speedups measured on the
8-subject corpus span 1.095x to 28.154x, exceeding 3.492x on five of the
eight. Do not read either figure as a cap on this slice; the per-subject
table, each realised figure beside its OWN recomputed ceiling, is
`docs/superpowers/evidence/2026-09-29-vertex-index/README.md` section 5.
The goal is dense measurable on MORE SUBJECTS.
"""
from __future__ import annotations


class VertexIndexError(Exception):
    """A structural assumption the index depends on does not hold.

    Deliberately subclasses `Exception` and NOT `ValueError`/`RuntimeError`/
    `KeyError`: those three are what `compile_tree`'s `except (ValueError,
    RuntimeError, KeyError)` around its `assign(...)` call folds into an
    indistinguishable `AssignFail("error", ...)`. A violated invariant here
    means the selection shortcut is unsound, which must never be mistaken
    for a normal refusal, so it propagates out uncaught -- matching
    `cores.CoreExtractionError`'s reasoning for the same choice.
    """


class VertexIndex:
    """Free-variable counts per interior vertex, maintained in O(degree).

    Hand it the five structures `assign` has already built plus the current
    `value`. It reads them at construction and thereafter only membership of
    `domain` and `pleat_pref`, which never change during a search.

    `bind(x)` / `unbind(x)` must be called for EVERY change to `value`.
    In `assign.py` those are exactly three sites, all inside `retry`: the
    bind at its `value[var] = vals[i]`, the unbind at its `del value[var]`,
    and the unbind at its `value.pop(popped, None)` on a frame pop. Symbol
    names rather than line numbers deliberately -- this contract is what a
    reader follows to check the correctness argument, and a rotted line
    number sends them to the wrong place silently.
    """

    def __init__(self, interior, inc, var_of, domain, pleat_pref, value):
        both = domain.keys() & pleat_pref.keys()
        if both:
            raise VertexIndexError(
                f"{len(both)} variable(s) are in BOTH `domain` and "
                f"`pleat_pref`, e.g. {next(iter(both))!r}. `eligible`'s "
                f"docstring states a `domain` variable is never a "
                f"`pleat_pref` key, and `select` relies on it: inside the "
                f"pleat phase it treats the key's first component as "
                f"constantly True, because the filtered list can contain no "
                f"domain variable. If that is false the pleat-phase "
                f"selection is wrong -- silently, and in a way the counts "
                f"themselves would not reveal.")

        self._domain = domain
        self._pleat = pleat_pref

        #: v -> its position in `interior`. This IS the tie-break: the loop
        #: it replaces (`assign.py`'s `_scan`) keeps `best` only on strict
        #: `<`, so
        #: among equal keys the earliest vertex in `interior` order wins.
        #: Making it an explicit key component is what frees `select` from
        #: depending on iteration order.
        self.order = {v: i for i, v in enumerate(interior)}

        #: v -> frozenset of DISTINCT variables incident to v. A set, not a
        #: list: `var_of[i] = min(base, mirror)` means a piece and its
        #: mirror share one variable and both can be incident to the same
        #: vertex on the axis x = N (spec 3.3 Trap 1).
        self.vars_at = {
            v: frozenset(var_of[i] for i in inc[v] if i in var_of)
            for v in interior
        }

        #: x -> set of interior vertices x touches. Also a set, so a
        #: variable reaching one vertex through two pieces decrements it
        #: once. A variable touching no interior vertex is simply absent,
        #: and `bind`/`unbind` are then a no-op -- correct, because
        #: `free_vars_at` is only ever called on members of `interior`.
        self.vertices_of: dict = {}
        for v, xs in self.vars_at.items():
            for x in xs:
                self.vertices_of.setdefault(x, set()).add(v)

        self.n_free: dict = {}
        self.n_free_domain: dict = {}
        self.n_free_pleat: dict = {}
        for v, xs in self.vars_at.items():
            free = [x for x in xs if x not in value]
            self.n_free[v] = len(free)
            self.n_free_domain[v] = sum(1 for x in free if x in domain)
            self.n_free_pleat[v] = sum(1 for x in free if x in pleat_pref)

        #: TWO sets, both maintained, neither ever rebuilt. `pleat_open` is
        #: recomputed every node (`pick`'s `now_open`) and flips in BOTH
        #: directions, including on backtracking across the boundary, so a
        #: single set whose DEFINITION changed with the phase would have to
        #: be rebuilt over all of `interior` on each flip -- reintroducing
        #: the O(|interior|)-per-node cost this class exists to remove, on
        #: an unbounded number of nodes. Maintaining both costs one extra
        #: set operation per state change and makes a flip O(1).
        self.nonempty_all = {v for v in interior if self.n_free[v]}
        self.nonempty_pleat = {v for v in interior if self.n_free_pleat[v]}

        #: How many vertices `select` actually scanned, summed. Spec 5.2
        #: requires "vertices visited per node" to be MEASURED rather than
        #: inferred from the >=90.4% empty rate, and the off arm's figure is
        #: `len(interior)` by construction, so the content is all here. Two
        #: integer adds per node against ~4,237 dict lookups is ~0.05% of the
        #: work being measured; kept unconditional so no flag can silently
        #: switch it off, and kept OUT of `snapshot()` so two snapshots still
        #: compare by value.
        self.pool_calls = 0
        self.pool_total = 0

    def count_at(self, v, pleat_open) -> int:
        """Eligible free variables at `v` under the current phase.

        This is what `pick`'s sticky fast path reads: a zero means
        `eligible(v)` would return `[]`, so the set build and the sort are
        skipped entirely.
        """
        return self.n_free_pleat[v] if pleat_open else self.n_free[v]

    def bind(self, x) -> None:
        """`x` has just entered `value`."""
        self._delta(x, -1)

    def unbind(self, x) -> None:
        """`x` has just left `value`."""
        self._delta(x, +1)

    def _delta(self, x, d) -> None:
        vs = self.vertices_of.get(x)
        if not vs:
            return
        in_dom = x in self._domain
        in_pleat = x in self._pleat
        for v in vs:
            n = self.n_free[v] + d
            self.n_free[v] = n
            if n:
                self.nonempty_all.add(v)
            else:
                self.nonempty_all.discard(v)
            if in_dom:
                self.n_free_domain[v] += d
            if in_pleat:
                p = self.n_free_pleat[v] + d
                self.n_free_pleat[v] = p
                if p:
                    self.nonempty_pleat.add(v)
                else:
                    self.nonempty_pleat.discard(v)

    def select(self, pleat_open):
        """The vertex `pick` would choose, or `None`.

        Equivalent to `assign.py`'s `_scan` -- scan `interior` in order,
        keep `best` on strict `<` -- because `self.order` carries the
        positional tie-break explicitly, so the result does not depend on
        how `pool` iterates.

        Inside the pleat phase the key's first component is constantly
        True: `eligible` filters to `pleat_pref` keys, and no such key is a
        `domain` variable (refused at construction), so the filtered list's
        head is never a domain variable. Minimising over a constant first
        component is minimising the rest.
        """
        pool = self.nonempty_pleat if pleat_open else self.nonempty_all
        self.pool_calls += 1
        self.pool_total += len(pool)
        if not pool:
            return None
        if pleat_open:
            return min(pool, key=lambda v: (self.n_free_pleat[v], self.order[v]))
        return min(pool, key=lambda v: (self.n_free_domain[v] == 0,
                                        self.n_free[v], self.order[v]))

    def snapshot(self) -> dict:
        """Every piece of state, for the verifier and the unit tests.

        Sets are returned frozen so a caller cannot mutate the live index
        by accident, and so two snapshots compare by value.
        """
        return {
            "n_free": dict(self.n_free),
            "n_free_domain": dict(self.n_free_domain),
            "n_free_pleat": dict(self.n_free_pleat),
            "nonempty_all": frozenset(self.nonempty_all),
            "nonempty_pleat": frozenset(self.nonempty_pleat),
        }
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -m pytest tests/test_box_pleat_vertex_index.py -q
```

Expected: `19 passed` in well under a second. If `test_select_matches_the_positional_tie_break_on_a_three_way_tie` fails, you have almost certainly dropped `self.order` from the `min` key.

- [ ] **Step 5: Prove the two Trap-1 tests are not vacuous**

Temporarily change `vars_at`'s comprehension from a `frozenset` to a `tuple` — i.e. count incident pieces rather than distinct variables:

```python
        self.vars_at = {
            v: tuple(var_of[i] for i in inc[v] if i in var_of)
            for v in interior
        }
```

Re-run the file. Expected: `test_trap1_two_pieces_sharing_a_variable_count_once` and `test_trap1_binding_an_aliased_variable_decrements_once` both **FAIL**. Record the actual output, then restore the `frozenset` and confirm the file passes again.

This step is not optional. Trap 1 is the one defect in this module that a real subject might not exercise, so a test that cannot catch it is worse than no test.

- [ ] **Step 6: Prove the tie-break test is not vacuous**

Temporarily drop `self.order[v]` from both `min` keys in `select`. Re-run the file. Expected: `test_select_matches_the_positional_tie_break_on_a_three_way_tie` **FAILS** on the reversed-`interior` assertion (the forward case may pass by luck, which is exactly why the test checks both directions). Record the output, restore, re-run.

- [ ] **Step 6b: Prove the remaining six mutations are covered**

Steps 5 and 6 were the only mutation gates this plan originally asked for, and that was a defect in the plan, not in the module: the first review of the shipped file found **three whole mechanisms with no test that could fail** — `_delta`'s `n_free_domain` maintenance, `select`'s pleat branch on a non-empty pool, and the `n_free` component of the non-pleat key, which *is* the most-constrained-vertex heuristic. Run each mutation below, one at a time. **Before each replacement, assert its target string occurs exactly once in the file** — a replace that silently matches nothing gives a green run indistinguishable from a real pass, which has happened three times in this project.

| # | mutation in `vertex_index.py` | must turn red |
|---|---|---|
| 1 | `if in_dom:` → `if False:` in `_delta` | `test_binding_a_domain_variable_moves_the_domain_count`, `test_select_lets_the_domain_component_change_the_winner_after_a_bind` |
| 2 | `pool = self.nonempty_pleat if pleat_open else self.nonempty_all` → `pool = self.nonempty_all` | `test_select_in_the_pleat_phase_uses_the_pleat_pool_and_the_pleat_count` |
| 3 | pleat `min` key → `(0, self.order[v])` | same |
| 4 | pleat `min` key → `(self.n_free_pleat[v],)` | same |
| 5 | `if p:` → `if n:` in `_delta`'s `nonempty_pleat` branch | `test_binding_a_mixed_vertexs_pleat_variable_empties_only_the_pleat_pool`, and the test above |
| 6 | drop `self.n_free[v]` from the non-pleat `min` key | `test_select_prefers_the_smaller_free_count_under_both_orders` |

Two further mutations guard the `value`-at-construction sibling and must also go red: `n_free_pleat[v] = sum(1 for x in xs if x in pleat_pref)` (`xs` for `free`), and `nonempty_all = set(interior)`. **Both are green against the original thirteen tests** — the second is the more instructive, because a `nonempty_all` seeded from `interior` survives every bind/unbind test in the file.

- [ ] **Step 7: Commit**

Write the message to a file — a heredoc with backticks has already been mangled by zsh in this project.

```bash
git add mcp_harness/box_pleat/vertex_index.py mcp_harness/tests/test_box_pleat_vertex_index.py
git commit -F <your message file>
```

Message content: that this adds the index and its unit tests, that nothing calls it yet, the two Trap-1 mutations you ran and that both went red, and the tie-break mutation. End with `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

---
### Task 2: Wire the index into `assign`, behind the flag

**Files:**
- Modify: `mcp_harness/box_pleat/assign.py` — signature (`:529-531`), a new import, `pick` (`:881-923`), the three `value` mutation sites (`:978`, `:982`, `:987`), and the node counter (`:1009`)
- Modify: `mcp_harness/box_pleat/compile.py` — signature (`:119-126`) and the `assign(...)` call (`:401-403`)
- Create: `mcp_harness/tests/test_box_pleat_vertex_index_identity.py`

**Interfaces:**
- Consumes from Task 1: `VertexIndex(interior, inc, var_of, domain, pleat_pref, value)`, `.count_at(v, pleat_open)`, `.bind(x)`, `.unbind(x)`, `.select(pleat_open)`, `.snapshot()`, and `VertexIndexError`.
- Produces, and Task 3 depends on these exact keyword names:
  - `assign(..., vertex_index: bool = False, vertex_index_verify: bool = False, debug_search: dict | None = None)`
  - `compile_tree(..., vertex_index: bool = False, vertex_index_verify: bool = False, debug_search: dict | None = None)`
  - `debug_search`, when a dict is passed, comes back with `{"nodes": int, "vars": list, "interior": int}` plus, when `vertex_index=True`, `{"pool_calls": int, "pool_total": int}`. `nodes` is counted, never inferred; `vars` is the variable pushed at each node in order; `interior` is `len(interior)`, which is the off arm's visited-vertices-per-node by construction.

**Context you need.** `assign` is a single large function with its helpers as closures over its locals. `pick` (`:881`) already does the phase bookkeeping and the sticky-vertex fast path; only its final rescan changes. `domain` is populated once at `:355` during setup and is final long before the search, so building the index just before the loop reads a finished `domain` — verify that for yourself rather than taking it from this plan.

**`assign` is on the SPARSE path too.** `compile.py:401-403` passes `dense=dense` to a single `assign` call, so sparse box-pleat compiles run this same code, and sparse output backs 10 validated folds. That is why sparse byte-identity is a gate and not a nicety.

- [ ] **Step 1: Write the failing identity tests**

Create `mcp_harness/tests/test_box_pleat_vertex_index_identity.py`:

```python
"""The vertex index changes nothing: same output, same search.

Spec: `docs/superpowers/specs/2026-09-29-vertex-index-design.md` section 4.

A correct index selects the same vertex, so these are IDENTITY tests, not
benchmarks. If any of them fails, no timing figure from the indexed arm
means anything (spec section 4.4) -- the two arms solved different problems.

Cheap subjects only. The 8-subject corpus is
`docs/superpowers/evidence/2026-09-29-vertex-index/ab.py`, not this suite.
"""
import json

import pytest

from box_pleat.compile import compile_tree
from box_pleat.vertex_index import VertexIndexError
from test_box_pleat_tree import RULE6


def _entry(subject):
    with open(RULE6) as fh:
        return next(e for e in json.load(fh) if e["subject"] == subject)


def _sparse_pair(subject):
    e = _entry(subject)
    off = compile_tree(e["requested"], e["pairs"])
    on = compile_tree(e["requested"], e["pairs"], vertex_index=True)
    return off, on


def test_sparse_starfish_is_byte_identical():
    off, on = _sparse_pair("starfish")
    assert off.stage_reached == "emit", off.failure
    assert on.stage_reached == "emit", on.failure
    assert on.fold == off.fold


def test_sparse_lizard_is_byte_identical():
    """`lizard` is the subject whose sparse labelling actually contradicts
    and drives the CEGAR loop (`layers_tried` 9 as of 2026-09-27), so unlike
    `starfish` it exercises backtracking, `retry`, and `retry`'s CEGAR unbind
    hook -- the one after `del value[var]` on the reassign path. That hook,
    and only that hook, is what the `off.layers_tried > 1` guard below pins.
    `retry`'s OTHER unbind, after `value.pop(popped, None)` on a frame pop,
    is exercised in fact by any search that pops a frame, but no assertion
    here pins it: a change that broke that hook alone could leave this test
    green. Guarded for non-vacuity below: if `lizard` ever stops rejecting,
    this test stops testing the CEGAR unbind path and must be replaced
    rather than quietly kept."""
    off, on = _sparse_pair("lizard")
    assert off.stage_reached == "emit", off.failure
    assert off.layers_tried > 1, \
        "lizard stopped rejecting -- this test no longer covers unbind"
    assert on.stage_reached == "emit", on.failure
    assert on.fold == off.fold
    assert on.layers_tried == off.layers_tried


def test_dense_lizard_matches_node_count_and_variable_sequence():
    """Spec section 4.3. Dense does not converge, so identity is asserted on
    the node count AND a digest of the chosen-variable sequence.

    The sequence is the point. Node counts alone would pass two searches
    that diverged and then reconverged to the same total; the sequence fails
    at the FIRST differing node. A small budget keeps this in the suite --
    the full 20,000-node ladder is Task 3's job.
    """
    e = _entry("lizard")
    a: dict = {}
    b: dict = {}
    off = compile_tree(e["requested"], e["pairs"], dense=True,
                       assign_budget=600, debug_search=a)
    on = compile_tree(e["requested"], e["pairs"], dense=True,
                      assign_budget=600, vertex_index=True, debug_search=b)
    assert a["nodes"] > 0, "node counter never fired"
    assert a["nodes"] == b["nodes"], (a["nodes"], b["nodes"])
    assert a["vars"], "no variable was ever chosen"
    assert a["vars"] == b["vars"], "the searches diverged"
    assert off.stage_reached == on.stage_reached


def test_verify_mode_passes_on_dense_starfish():
    """Spec section 4.1, the gate that makes the counts trustworthy rather
    than merely consistent with the answer. It recomputes every count for
    every interior vertex at every node that reaches `select` and raises
    `VertexIndexError` on any disagreement, so reaching the end without
    raising IS the assertion -- PROVIDED the verifier ran at all, which is
    what the `pool_calls` assertion below pins. `_verify_index` runs only at
    a node that reaches `select`, so without that assertion this file's two
    verify tests would both stay green on a `pick` that never consults the
    index. What `pool_calls > 0` pins is that `select` ran, and therefore
    that the straight-line block containing `_verify_index(chosen)` was
    reached; it does NOT pin that the call itself is still present. Deleting
    the call outright is caught only by the mutation runs recorded in
    `.superpowers/sdd/task-2-report.md`, not by an assertion here."""
    e = _entry("starfish")
    d: dict = {}
    res = compile_tree(e["requested"], e["pairs"], dense=True,
                       vertex_index=True, vertex_index_verify=True,
                       debug_search=d)
    assert res.stage_reached in ("emit", "layers", "assign"), res.failure
    assert d["pool_calls"] > 0, \
        ("`select` ran zero times, so `_verify_index` -- which `pick` calls "
         "only on the line after it -- never ran and this test asserted "
         "nothing: either every node returned via `pick`'s sticky fast "
         "path, or `pick` no longer goes through the index at all")


def test_verify_without_the_index_refuses():
    """`vertex_index_verify=True` with `vertex_index=False` verifies NOTHING:
    `vx` is `None`, so `pick` takes the `_scan` branch and `_verify_index` is
    never called. It used to be accepted in silence, which would let a
    harness record a "verified" run in which the verifier never ran once. It
    now refuses.

    Asserted on the exception TYPE and on two specific fragments of its
    message, so this cannot pass on some unrelated failure that happens to
    raise, nor on a `VertexIndexError` raised for a different reason.
    """
    e = _entry("starfish")
    with pytest.raises(VertexIndexError) as exc:
        compile_tree(e["requested"], e["pairs"], vertex_index_verify=True)
    msg = str(exc.value)
    assert "verifies NOTHING" in msg, msg
    assert "vertex_index=True" in msg, msg


def test_verify_mode_passes_on_capped_dense_lizard():
    """Spec section 4.1's second subject, capped at 200 nodes as the spec
    names. `lizard` carries 4,489 interior vertices against `starfish`'s 49
    (both read from `debug_search["interior"]`, 2026-09-30; the "~4,237" this
    docstring used to claim was the predecessor profile's per-node
    `free_vars_at` CALL count, not a vertex count), so this checks a
    different order of magnitude of vertex-state."""
    e = _entry("lizard")
    d: dict = {}
    compile_tree(e["requested"], e["pairs"], dense=True, assign_budget=200,
                 vertex_index=True, vertex_index_verify=True, debug_search=d)
    assert d["nodes"] > 0, "verify mode ran zero nodes -- nothing was checked"
    assert d["pool_calls"] > 0, \
        ("`select` ran zero times, so `_verify_index` -- which `pick` calls "
         "only on the line after it -- never ran and this test asserted "
         "nothing: either every node returned via `pick`'s sticky fast "
         "path, or `pick` no longer goes through the index at all")
```

- [ ] **Step 2: Run them to verify they fail**

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -m pytest tests/test_box_pleat_vertex_index_identity.py -q
```

Expected: every test errors with `TypeError: assign() got an unexpected keyword argument` or `compile_tree() got an unexpected keyword argument`. Anything else means the fixture is wrong, not the code.

- [ ] **Step 3: Add the import and the three new parameters to `assign`**

In `mcp_harness/box_pleat/assign.py`, add to the existing relative imports:

```python
from .vertex_index import VertexIndex, VertexIndexError
```

Change the signature at `:529-531` from:

```python
def assign(layout, ridges: list, boundary_ridges: list, contours: dict, *,
           budget: int = 500_000, global_check=None, layer_checks: int = 200,
           dense: bool = False, debug_clause_sizes: list | None = None):
```

to:

```python
def assign(layout, ridges: list, boundary_ridges: list, contours: dict, *,
           budget: int = 500_000, global_check=None, layer_checks: int = 200,
           dense: bool = False, debug_clause_sizes: list | None = None,
           vertex_index: bool = False, vertex_index_verify: bool = False,
           debug_search: dict | None = None):
```

Then, as the **first statement of `assign`'s body** -- immediately after the
closing `"""` of its docstring and **before** `N = layout.N`, so it fires
before any structure is built -- insert the flag-combination refusal:

```python
    if vertex_index_verify and not vertex_index:
        # Refused HERE, before any structure is built, because the
        # combination cannot be made to mean anything later: with no index
        # `vx` is `None`, `pick` takes the `_scan` branch, and
        # `_verify_index` is never reached. Accepting it silently would let
        # a harness record a "verified" run in which the verifier never ran
        # once -- which is exactly the shape of vacuous pass this project
        # keeps rediscovering.
        raise VertexIndexError(
            "vertex_index_verify=True with vertex_index=False verifies "
            "NOTHING: no index is built, so `pick` takes the `_scan` branch "
            "and `_verify_index` is never called. Pass vertex_index=True as "
            "well, or drop vertex_index_verify.")
```

- [ ] **Step 4: Extract the rescan as `_scan()` and rewrite `pick`**

Replace `pick`'s body from `best = None` through `return best[1:]` (`:913-923`). Insert `_scan` **before** `def pick():`, keeping `pick`'s existing docstring and its phase/sticky block exactly as they are:

```python
    def _scan():
        """The original rescan: every vertex in `interior`, `best` kept only
        on strict `<` so ties go to the EARLIEST vertex in `interior` order.

        Extracted rather than left inline so that `vertex_index_verify`
        compares the index against production code ITSELF. A verifier
        holding its own copy of this loop can agree with its copy while both
        have drifted from the real thing -- this project has a recorded
        instance of exactly that, a probe that re-implemented production and
        consequently measured nothing.
        """
        best = None
        for v in interior:
            fv = eligible(v)
            if not fv:
                continue
            key = (fv[0] not in domain, len(fv))
            if best is None or key < best[0]:
                best = (key, v, fv)
        return best

    def _verify_index(chosen):
        """Spec section 4.1: recompute everything the old way, refuse on any
        disagreement.

        WHEN IT RUNS, precisely: at every node that reaches `select` -- which
        is NOT every node. A node whose sticky vertex still has an eligible
        variable returns from `pick` above without calling `select`, so this
        does not run there. Measured 2026-09-30: 3,835 of 6,806 nodes (56.3%)
        on dense `starfish`, 197 of 200 on dense `lizard` capped at 200. Spec
        section 4.1 says "at every node", which overstates it; this is what
        the code does.

        The gap is benign, and the unverified nodes are safe for a stated
        reason: a sticky return's ONLY dependence on the index is
        `count_at(v) > 0`, and a non-empty `eligible(v)` -- which the sticky
        branch goes on to require anyway -- implies it. So on those nodes the
        index cannot change the chosen vertex, and the counts it holds are
        re-checked in full at the next node that does reach `select`. A wrong
        count cannot hide; it can only be reported one node later.

        Do NOT widen this to run on the sticky path either. It performs the
        very rescan the index exists to remove, so running it there would
        make the cheap path the most expensive one, and the sticky path is
        0.024% of `lizard`'s calls -- nothing to be bought.

        Test-only. It performs the very rescan the index exists to remove,
        plus three more passes over `interior`, so it multiplies per-node
        cost several times over. It is the gate that makes the COUNTS
        trustworthy: byte-identity says the ANSWER matched, this says the
        counts were right at every step, and a count that is wrong in a
        compensating way passes the former and fails the latter.
        """
        s = vx.snapshot()
        for v in interior:
            ref = free_vars_at(v)
            if s["n_free"][v] != len(ref):
                raise VertexIndexError(
                    f"n_free[{v!r}] = {s['n_free'][v]} but free_vars_at "
                    f"returns {len(ref)} ({ref!r})")
            d = sum(1 for x in ref if x in domain)
            if s["n_free_domain"][v] != d:
                raise VertexIndexError(
                    f"n_free_domain[{v!r}] = {s['n_free_domain'][v]} but a "
                    f"recount of {ref!r} gives {d}")
            p = sum(1 for x in ref if x in pleat_pref)
            if s["n_free_pleat"][v] != p:
                raise VertexIndexError(
                    f"n_free_pleat[{v!r}] = {s['n_free_pleat'][v]} but a "
                    f"recount of {ref!r} gives {p}")
        want_all = frozenset(v for v in interior if free_vars_at(v))
        if s["nonempty_all"] != want_all:
            raise VertexIndexError(
                f"nonempty_all disagrees: index-only "
                f"{sorted(s['nonempty_all'] - want_all)!r}, reference-only "
                f"{sorted(want_all - s['nonempty_all'])!r}")
        want_pleat = frozenset(
            v for v in interior
            if any(x in pleat_pref for x in free_vars_at(v)))
        if s["nonempty_pleat"] != want_pleat:
            raise VertexIndexError(
                f"nonempty_pleat disagrees: index-only "
                f"{sorted(s['nonempty_pleat'] - want_pleat)!r}, "
                f"reference-only {sorted(want_pleat - s['nonempty_pleat'])!r}")
        best = _scan()
        want = None if best is None else best[1]
        if chosen != want:
            raise VertexIndexError(
                f"SELECTION DIVERGED: the index chose {chosen!r}, the "
                f"`interior` scan chose {want!r}. The search is no longer "
                f"identical, so no timing figure from this arm means "
                f"anything (spec section 4.4).")
```

Then `pick`'s tail. The phase block (`:899-907`) and the sticky block are shown here in full because the sticky block **changes** — it must consult the index before building a set:

```python
        v = current[0]
        if v is not None:
            # The index answers "would `eligible(v)` be empty?" from a
            # counter, so `free_vars_at`'s set build and its sort are
            # skipped outright. The profile measured this sticky path at
            # 0.024% of `lizard`'s calls, so it is cheap either way -- but
            # both arms must agree, and `count_at` is exactly
            # `len(eligible(v))`.
            if vx is None or vx.count_at(v, pleat_open[0]):
                fv = eligible(v)
                if fv:
                    return v, fv
        if vx is None:
            best = _scan()
            if best is None:
                return None
            current[0] = best[1]
            return best[1:]
        chosen = vx.select(pleat_open[0])
        if vertex_index_verify:
            _verify_index(chosen)
        if chosen is None:
            return None
        current[0] = chosen
        # The main loop reads only `pk[1][0]`, so the sorted list is
        # materialised for the WINNER alone -- once per node instead of once
        # per interior vertex. The return shape is unchanged.
        return chosen, eligible(chosen)
```

- [ ] **Step 5: Build the index and hook the three mutation sites**

Immediately **before** `nodes = budget` (`:960`), insert:

```python
    # Built here, after `domain` (populated once, in `initial_readings`),
    # `pleat_pref` and `interior` are all final, and after every early
    # `return AssignFail(...)` above -- so a refused setup never pays for it.
    # `pick` and `_verify_index` close over `vx`, and a closure resolves at
    # CALL time, so defining it below their `def`s is correct.
    vx = VertexIndex(interior, inc, var_of, domain, pleat_pref,
                     value) if vertex_index else None
```

Change the node decrement (`:1009-1011`) from:

```python
    while True:
        nodes -= 1
        if nodes < 0:
            return AssignFail("budget", budget)
```

to:

```python
    while True:
        nodes -= 1
        if nodes < 0:
            return AssignFail("budget", budget)
        if debug_search is not None:
            # COUNTED, never inferred: `AssignFail("budget", budget)`
            # reports the budget, not the consumption, which is how a
            # predecessor slice nearly published a node count it had not
            # measured.
            debug_search["nodes"] = debug_search.get("nodes", 0) + 1
            # Spec 5.2's "vertices visited per node". The off arm's figure is
            # `interior` by construction, which is why it is recorded for
            # both arms. The pool figures lag by at most one `select` call,
            # because this runs at the TOP of the loop and `pick` has not
            # run yet for this node -- immaterial at 20,000 nodes, and stated
            # rather than left for a reader to wonder about. This whole block
            # is inert unless `debug_search` is passed, so the timing arm
            # pays nothing for it.
            debug_search.setdefault("interior", len(interior))
            if vx is not None:
                debug_search["pool_calls"] = vx.pool_calls
                debug_search["pool_total"] = vx.pool_total
```

Change `retry`'s three `value` mutations (`:976-987`) from:

```python
            var, vals, i = frames[-1]
            if i < len(vals):
                frames[-1][2] = i + 1
                value[var] = vals[i]
                if (all(feasible(w) for w in touching.get(var, ()))
                        and not hits_nogood()):
                    return True
                del value[var]
            else:
                frames.pop()
                if not frames:
                    return False
                value.pop(frames[-1][0], None)
```

to:

```python
            var, vals, i = frames[-1]
            if i < len(vals):
                frames[-1][2] = i + 1
                # `value[var] = vals[i]` is NOT always an unbound->bound
                # transition. The CEGAR path -- the main loop's `retry()`
                # call right after `nogoods.append(clause)` -- calls it
                # WITHOUT pushing a frame, so the deepest frame's variable is
                # still bound from the complete candidate that was just
                # rejected, and this line REASSIGNS it. Counting that as a
                # bind decrements a variable already counted as bound, and
                # the count never recovers. Measured: `verify` mode caught it
                # on sparse `lizard` as `n_free[(4, 7)] = 0` against a
                # `free_vars_at` of `[79]`.
                was_bound = var in value
                value[var] = vals[i]
                if vx is not None and not was_bound:
                    vx.bind(var)
                if (all(feasible(w) for w in touching.get(var, ()))
                        and not hits_nogood()):
                    return True
                del value[var]
                if vx is not None:
                    vx.unbind(var)
            else:
                frames.pop()
                if not frames:
                    return False
                popped = frames[-1][0]
                # `pop` with a default: the variable may already be absent,
                # and unbinding one that was never bound would drive a
                # count above its true value.
                if value.pop(popped, None) is not None and vx is not None:
                    vx.unbind(popped)
```

Finally, record the chosen variable. Change `:1061` from:

```python
        var = pk[1][0]
```

to:

```python
        var = pk[1][0]
        if debug_search is not None:
            debug_search.setdefault("vars", []).append(var)
```

- [ ] **Step 6: Thread the flags through `compile_tree`**

In `mcp_harness/box_pleat/compile.py`, add three parameters to the signature at `:119-126`, after `debug_witness_cores`:

```python
                 vertex_index: bool = False,
                 vertex_index_verify: bool = False,
                 debug_search: dict | None = None) -> Result:
```

and pass them at the `assign(...)` call (`:401-403`):

```python
        asg = assign(lay, ridges, boundary, cont, budget=assign_budget,
                     global_check=_check, layer_checks=layer_budget,
                     dense=dense, debug_clause_sizes=debug_clause_sizes,
                     vertex_index=vertex_index,
                     vertex_index_verify=vertex_index_verify,
                     debug_search=debug_search)
```

**Note `VertexIndexError` will NOT be swallowed here.** `compile.py`'s `except (ValueError, RuntimeError, KeyError)` around this call folds those three into `AssignFail("error", ...)`; `VertexIndexError` subclasses plain `Exception`, so it propagates out of `compile_tree` uncaught. That is deliberate (Task 1's docstring explains why) and you must not widen the `except` to catch it.

- [ ] **Step 7: Run the identity tests**

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -m pytest tests/test_box_pleat_vertex_index_identity.py -q
```

Expected: `6 passed` (the 5 originally planned plus `test_verify_without_the_index_refuses`, added by the review-findings wave). Budget roughly 40-60 s — two sparse `lizard` compiles at ~6.5 s each dominate. If `test_dense_lizard_matches_node_count_and_variable_sequence` fails on `a["vars"] == b["vars"]`, read the first differing index: an early divergence points at the selection key or the tie-break, a late one at a missing `unbind`.

- [ ] **Step 8: Run the existing box-pleat suite to prove the flag-off path is untouched**

Run the FULL named files, never a `-k` subset:

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -m pytest tests/test_box_pleat_tree.py tests/test_box_pleat_core_in_loop.py tests/test_box_pleat_witness_identity.py -q
```

Expected: all pass, with the same counts as before your change. This is the real regression gate: with `vertex_index=False` every path must behave exactly as it did, and these files never pass the flag.

- [ ] **Step 9: Prove the identity tests are not vacuous — break the index three ways**

For each mutation: apply it, run `tests/test_box_pleat_vertex_index_identity.py`, record the actual failure, restore, and re-run to confirm green. **A mutation that leaves the suite green is a finding you must report, not one to move past.**

1. **Drop an unbind.** In `retry`, delete the `if vx is not None: vx.unbind(var)` after `del value[var]`. Expected: counts drift down and never recover, so `lizard` diverges.
2. **Drop the tie-break.** In `vertex_index.py`'s `select`, remove `self.order[v]` from the non-pleat `min` key. Expected: a divergence on some subject. **If everything stays green, say so explicitly** — it would mean no test here reaches a real tie, and the unit test in Task 1 is then the only thing pinning Trap 3.
3. **Use the wrong phase count — and note the DIRECTION, which is the whole lesson.** In `count_at`, return `self.n_free_pleat[v]` unconditionally. Expected: `test_dense_lizard_matches_node_count_and_variable_sequence` **FAILS** at its `a["vars"] == b["vars"]` assertion; the other four pass.

   **Do not use the opposite mutation** (`return self.n_free[v]` unconditionally). It was tried, and all five tests stay **green**, because `count_at`'s errors are asymmetric:

   * **Too HIGH is inert.** The guard `if vx is None or vx.count_at(v, pleat_open[0]):` is a pure short-circuit. An over-count lets the guard pass, `eligible(v)` is called anyway, it returns `[]`, and control falls through to `select` exactly as it would have. The result is a missed optimisation, not a changed search — so no identity test can see it, and none should be expected to.
   * **Too LOW changes the selection.** An under-count skips the sticky path for a vertex that *does* have free eligible variables, so `select` returns the globally-best vertex where the original code would have returned the sticky one. That is a real divergence and the sequence digest catches it.

   `count_at`'s phase-correctness is pinned directly by Task 1's `test_count_at_switches_with_the_phase`, which is where it belongs. Record this asymmetry in your report; it is the kind of thing a later reader will otherwise rediscover by writing a test that cannot fail.

Before you begin, assert each mutation's target string occurs **exactly once** in the file. A search-and-replace that silently matches nothing, or matches a comment, produces a green run indistinguishable from a real pass — that has already happened twice in this project's history.

- [ ] **Step 10: Confirm the serve path is untouched**

```bash
grep -c box_pleat mcp_harness/server.py
git diff --stat -- mcp_harness/layer_order.py
```

Expected: `0`, and no output.

- [ ] **Step 11: Commit**

```bash
git add mcp_harness/box_pleat/assign.py mcp_harness/box_pleat/compile.py mcp_harness/tests/test_box_pleat_vertex_index_identity.py
git commit -F <your message file>
```

Message content: the three new parameters, that the flag defaults off and the off path is byte-identical, the three hook sites, that `_scan` was extracted so the verifier's reference is production code, and the three mutations you ran with their outcomes. End with `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

---
### Task 3: The corpus instrument, and spend its runs

**Files:**
- Create: `docs/superpowers/evidence/2026-09-29-vertex-index/ab.py`
- Create: `docs/superpowers/evidence/2026-09-29-vertex-index/ab.json` (generated)

**Interfaces:**
- Consumes from Task 2: `compile_tree(..., vertex_index=, vertex_index_verify=, debug_search=)`, and `debug_search`'s keys `nodes`, `vars`, `interior`, `pool_calls`, `pool_total`.
- Produces: `ab.json`. Task 4 reads it and nothing else.

**Context you need.** §4.4 is the governing rule: **identity must be established before any speedup figure is quoted.** A speedup measured on an arm that failed identity is not a result, because the two arms solved different problems. So the instrument runs **two separate passes**: an identity pass with `debug_search` on, and a timing pass with every debug channel off. They must be separate because the identity pass appends 20,000 entries to `debug_search["vars"]`, and you cannot time an instrumented arm.

**Harness checks already measured on this machine**, so you know what working looks like. These are **harness checks, not results** — one subject, small budgets, single runs — and they must not appear in Task 4's README:

| check | reading |
|---|---|
| dense `lizard`, 3,000 nodes, whole `compile_tree` | off 17.80 s, on 13.13 s (1.36×), both `nodes=3000`, both `vars` length 2995 |
| dense `lizard`, 1,500 nodes | `interior` = **4,489**; `pool_calls` 1,426; mean pool **402.3** = **8.96%** of `interior` |
| `select` skipped on some nodes | `pool_calls` 1,426 against `nodes` 1,500 — the sticky fast path returns before `select` on ~5% |

The 8.96% is worth noting: the predecessor's ≥90.4% empty rate predicts ~9.6% non-empty, and this is an independent route to the same number.

- [ ] **Step 1: Write the instrument**

Create `docs/superpowers/evidence/2026-09-29-vertex-index/ab.py`:

```python
"""Does the incremental vertex index preserve the search, and what does it buy?

Spec: `../../specs/2026-09-29-vertex-index-design.md`.

IDENTITY FIRST, ALWAYS (spec section 4.4). A correct index selects the same
vertex, so a speedup measured on an arm that failed identity is not a result
-- the two arms solved different problems. Every subject therefore gets an
IDENTITY pass before a TIMING pass, and `verdict()` refuses to report a
speedup for any subject whose identity failed.

TWO PASSES, NOT ONE. The identity pass appends one entry per node to
`debug_search["vars"]` and records the pool figures; you cannot time an
instrumented arm, so the timing pass runs with every debug channel off.

A CEILING IS NOT A SPEEDUP. `CEILINGS` below are the predecessor's Amdahl
bounds for removing a component ENTIRELY, which no real optimisation
achieves. They are printed beside every realised figure so the gap is
visible, and Task 4's README is required to name it.

NO FIGURE FROM A REDUCED BUDGET MAY BE EXTRAPOLATED. The speedup GROWS
with the node budget: measured on dense `lizard`, 1.45x at 4,000 nodes
against 2.43x at 20,000. The reason is structural -- deeper in the search
more variables are bound, so more vertices are empty and the index skips more
of them, which means the saving compounds with depth rather than holding a
constant ratio. So `BUDGET` below is NOT a knob to trim when a run is slow: a
smaller budget produces a different and systematically PESSIMISTIC figure,
and Task 4's README may quote only figures taken at the real `BUDGET`.

NOT A CONVERGENCE FIX. The ceiling caps this at 3.492x on `lizard`. Dense
still will not converge. The goal is dense measurable on MORE SUBJECTS.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4] / "mcp_harness"))

from box_pleat.compile import compile_tree            # noqa: E402

#: The same eight subjects and the same fixture the predecessor's ladder used,
#: so the off arm's dense numbers are comparable with
#: `../2026-09-29-local-csp-profile/profile.json`.
SUBJECTS = ("starfish", "lizard", "frog", "horse", "bird", "guinea_pig",
            "octopus", "dog")

#: The predecessor's node budget, unchanged, so per-node figures compare.
BUDGET = 20_000

#: From `../2026-09-29-local-csp-profile/profile.json`, `lizard`'s row:
#: `whole_run_ceiling["free_vars_at"]` and the pair
#: (free_vars_at + pick) recomputed as 1/(1 - (pick+free_vars_at)/total).
#: Quoted as that directory's figures, never recomputed here.
CEILINGS = {"free_vars_at_alone": 1.907, "pick_and_free_vars_at": 3.492}

RULE6 = (pathlib.Path(__file__).resolve().parents[4] / "docs" / "superpowers"
         / "evidence" / "2026-09-08-vlm-tree-authoring" / "data"
         / "rule6_serve.json")


def _commit() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True, check=True).stdout.strip()


def digest(vars_seq) -> str:
    """A stable digest of the chosen-variable sequence (spec section 4.3).

    The sequence is what makes identity meaningful: node counts alone would
    pass two searches that diverged and then reconverged to the same total,
    while this differs as soon as one choice differs. Length is folded in so
    a prefix cannot collide with its own extension.
    """
    h = hashlib.sha256()
    h.update(str(len(vars_seq)).encode())
    for v in vars_seq:
        h.update(b"|")
        h.update(str(v).encode())
    return h.hexdigest()[:16]


def speedup(off_secs, on_secs):
    """`off / on`, or None when either arm has no usable time.

    Refuses rather than dividing by zero, and refuses a negative or zero
    duration, which would mean the clock was misread rather than that the
    code was infinitely fast.
    """
    if not off_secs or not on_secs or off_secs <= 0 or on_secs <= 0:
        return None
    return round(off_secs / on_secs, 3)


def first_divergence(a, b):
    """The index of the first differing element, or None if equal.

    Reported because WHERE two searches diverge localises the defect: an
    early index points at the selection key or the tie-break, a late one at
    a missing `unbind`.
    """
    if a == b:
        return None
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i
    return min(len(a), len(b))


def visited(pool_total, pool_calls, nodes, interior):
    """Vertices the index actually looked at: per SELECT CALL and per NODE.

    THESE ARE TWO DIFFERENT QUANTITIES and confusing them is a ~5% error in
    the headline figure. `select` does not run at every node: `pick`'s sticky
    fast path returns before it whenever the previously chosen vertex still
    has an eligible variable. So `pool_total / pool_calls` is vertices per
    `select` CALL, while `pool_total / nodes` is vertices per NODE -- and only
    the per-node one is comparable with `interior`, which is per node by
    construction, because the off arm's loop visits every interior vertex at
    every node. Measured on dense `lizard` at 4,000 nodes: `pool_total`
    942,563, `pool_calls` 3,794, `nodes` 4,000, so 248.4 per select against
    235.6 per node, with `select` skipped on 5.15% of nodes. Against
    `interior` = 4,489 that is a fraction of 0.0525 the right way and 0.0553
    the wrong way. Every comparison and every fraction below therefore uses
    the PER-NODE figure; the per-select one is recorded because it is the
    figure `select`'s own cost attaches to, under a name that says so.

    Both lag by at most one `select` call: `assign` records `pool_calls` and
    `pool_total` at the TOP of its loop, before that node's `pick` has run
    (stated at the recording site). Immaterial at 20,000 nodes, and
    immaterial to the distinction above, which is about 5% not 0.005%.

    Every field is `None` rather than 0 when its input is missing, so a
    dropped debug channel reads as absent instead of as a measurement.
    """
    keys = ("visited_per_select_on", "visited_per_node_on",
            "visited_fraction_on", "select_calls_per_node_on")
    if pool_total is None:
        return dict.fromkeys(keys)
    per_select = round(pool_total / pool_calls, 1) if pool_calls else None
    per_node = round(pool_total / nodes, 1) if nodes else None
    return {
        "visited_per_select_on": per_select,
        "visited_per_node_on": per_node,
        "visited_fraction_on": (round(per_node / interior, 4)
                                if per_node and interior else None),
        "select_calls_per_node_on": (round(pool_calls / nodes, 4)
                                     if pool_calls is not None and nodes
                                     else None),
    }


def identity_verdict(row):
    """(passed, [failure, ...]) for one subject. Spec section 4.

    Every check is stated as a positive requirement so a missing field fails
    rather than passing vacuously -- a `row.get(...)` that returns None must
    not read as agreement.
    """
    bad = []
    if row.get("sparse_fold_equal") is not True:
        bad.append(f"sparse FOLD not byte-identical "
                   f"(off stage {row.get('sparse_stage_off')!r}, "
                   f"on stage {row.get('sparse_stage_on')!r})")
    if row.get("dense_nodes_off") is None or row.get("dense_nodes_on") is None:
        bad.append("a dense arm recorded no node count")
    elif row["dense_nodes_off"] != row["dense_nodes_on"]:
        bad.append(f"dense node counts differ: {row['dense_nodes_off']} "
                   f"vs {row['dense_nodes_on']}")
    elif row["dense_nodes_off"] == 0:
        bad.append("dense ran zero nodes, so identity is vacuous")
    if row.get("dense_digest_off") is None or row.get("dense_digest_on") is None:
        bad.append("a dense arm recorded no variable-sequence digest")
    elif row["dense_digest_off"] != row["dense_digest_on"]:
        bad.append(f"chosen-variable sequences differ, first at index "
                   f"{row.get('dense_first_divergence')}")
    return not bad, bad


def _sparse_pair(entry):
    off = compile_tree(entry["requested"], entry["pairs"])
    on = compile_tree(entry["requested"], entry["pairs"], vertex_index=True)
    return off, on


def identity_pass(entry) -> dict:
    """Both arms, sparse and dense, with `debug_search` on. Never timed."""
    row: dict = {}
    off, on = _sparse_pair(entry)
    row["sparse_stage_off"] = off.stage_reached
    row["sparse_stage_on"] = on.stage_reached
    row["sparse_fold_equal"] = (off.fold == on.fold)
    row["sparse_layers_tried_off"] = off.layers_tried
    row["sparse_layers_tried_on"] = on.layers_tried

    a: dict = {}
    b: dict = {}
    d_off = compile_tree(entry["requested"], entry["pairs"], dense=True,
                         assign_budget=BUDGET, debug_search=a)
    d_on = compile_tree(entry["requested"], entry["pairs"], dense=True,
                        assign_budget=BUDGET, vertex_index=True, debug_search=b)
    row["dense_stage_off"] = d_off.stage_reached
    row["dense_stage_on"] = d_on.stage_reached
    row["dense_nodes_off"] = a.get("nodes")
    row["dense_nodes_on"] = b.get("nodes")
    row["dense_digest_off"] = digest(a.get("vars", []))
    row["dense_digest_on"] = digest(b.get("vars", []))
    row["dense_first_divergence"] = first_divergence(a.get("vars", []),
                                                     b.get("vars", []))
    # Spec 5.2: visited vertices per node. The off arm's figure is `interior`
    # BY CONSTRUCTION -- its loop visits everything -- so the comparison's
    # content is entirely in the on arm. `visited()` records the per-node and
    # the per-select figure under separate names and explains why they differ;
    # `visited_per_node_on` is the only one that may be compared against
    # `visited_per_node_off` or turned into a fraction.
    row["interior"] = b.get("interior")
    row["visited_per_node_off"] = b.get("interior")
    row["select_calls_on"] = b.get("pool_calls")
    row.update(visited(b.get("pool_total"), b.get("pool_calls"),
                       b.get("nodes"), b.get("interior")))
    return row


def timing_pass(entry) -> dict:
    """Both arms, dense only, every debug channel OFF. This is the only pass
    whose seconds mean anything.

    TWO CLOCKS, both recorded. The wall clock spans the whole `compile_tree`
    -- tree, pack, skeleton, contours, assign, layers, emit -- while
    `Result.timings["assign"]` is the `assign` stage alone, written by
    `compile.py`'s `tick("assign")` on both the success and the failure path.
    `assign` is the unit the predecessor's ceilings attach to, so it is the
    honest denominator for any speedup quoted against them (spec 5.2). On
    dense `lizard` the two nearly coincide -- `assign` 16.67 s of a 16.72 s
    compile -- but "nearly" is a measurement, not a property, and it will not
    hold for a subject whose packing or emit dominates. Record both rather
    than assume.
    """
    out: dict = {}
    for label, kw in (("off", {}), ("on", {"vertex_index": True})):
        t = time.perf_counter()
        res = compile_tree(entry["requested"], entry["pairs"], dense=True,
                           assign_budget=BUDGET, **kw)
        out[f"dense_secs_{label}"] = round(time.perf_counter() - t, 2)
        out[f"dense_assign_secs_{label}"] = res.timings.get("assign")
    out["speedup"] = speedup(out["dense_secs_off"], out["dense_secs_on"])
    out["assign_speedup"] = speedup(out["dense_assign_secs_off"],
                                    out["dense_assign_secs_on"])
    for label, kw in (("off", {}), ("on", {"vertex_index": True})):
        t = time.perf_counter()
        res = compile_tree(entry["requested"], entry["pairs"], **kw)
        out[f"sparse_secs_{label}"] = round(time.perf_counter() - t, 2)
        out[f"sparse_assign_secs_{label}"] = res.timings.get("assign")
    out["sparse_speedup"] = speedup(out["sparse_secs_off"],
                                    out["sparse_secs_on"])
    out["sparse_assign_speedup"] = speedup(out["sparse_assign_secs_off"],
                                           out["sparse_assign_secs_on"])
    return out


def _selftest():
    assert digest([]) != digest([1]), "empty and one-element digests collide"
    assert digest([1, 2]) == digest([1, 2])
    assert digest([1, 2]) != digest([2, 1]), "digest ignores order"
    assert digest([1, 2]) != digest([1, 2, 3]), "a prefix collides"
    # SAME LENGTH, so the length prefix cannot do the work: without the
    # separator both hash "2" + "1" + "23" and "2" + "12" + "3" == "2123".
    # An earlier version of this assertion used `[12]` vs `[1, 2]`, which
    # passes with the separator REMOVED because the length prefix already
    # differs -- a check that could not fail, verified by mutation.
    assert digest([1, 23]) != digest([12, 3]), "separator missing"

    assert speedup(10.0, 5.0) == 2.0
    assert speedup(10.0, 0) is None
    assert speedup(0, 5.0) is None
    assert speedup(-1.0, 5.0) is None
    assert speedup(None, 5.0) is None

    assert first_divergence([1, 2, 3], [1, 2, 3]) is None
    assert first_divergence([1, 2, 3], [1, 9, 3]) == 1
    assert first_divergence([1, 2], [1, 2, 3]) == 2, "prefix not reported"

    ok_row = {"sparse_fold_equal": True, "dense_nodes_off": 20001,
              "dense_nodes_on": 20001, "dense_digest_off": "a",
              "dense_digest_on": "a"}
    ok, bad = identity_verdict(ok_row)
    assert ok and not bad, bad
    ok, bad = identity_verdict({**ok_row, "sparse_fold_equal": False})
    assert not ok and "byte-identical" in bad[0], bad
    ok, bad = identity_verdict({**ok_row, "dense_nodes_on": 19000})
    assert not ok and "node counts differ" in bad[0], bad
    ok, bad = identity_verdict({**ok_row, "dense_digest_on": "b"})
    assert not ok and "sequences differ" in bad[0], bad
    # a zero-node run must FAIL rather than pass vacuously
    ok, bad = identity_verdict({**ok_row, "dense_nodes_off": 0,
                                "dense_nodes_on": 0})
    assert not ok and "vacuous" in bad[0], bad
    # a MISSING field must fail, not read as agreement
    ok, bad = identity_verdict({"dense_nodes_off": 1, "dense_nodes_on": 1,
                                "dense_digest_off": "a", "dense_digest_on": "a"})
    assert not ok, "a missing sparse_fold_equal passed"
    ok, bad = identity_verdict({**ok_row, "dense_digest_on": None})
    assert not ok and "no variable-sequence digest" in bad[0], bad

    # THE PER-NODE / PER-SELECT CONFUSION (review FIX E). `select` is skipped
    # on every node `pick`'s sticky path answers, so `pool_calls != nodes` and
    # the two figures genuinely differ. These are the MEASURED dense `lizard`
    # readings at 4,000 nodes. An earlier `ab.py` computed
    # `pool_total / pool_calls` and stored it as `visited_per_node_on`, then
    # compared it against `interior`, which is per node -- so it read 248.4
    # and a fraction of 0.0553 where the honest per-node figures are 235.6 and
    # 0.0525. Under that formula the first two assertions below fail.
    v = visited(pool_total=942_563, pool_calls=3_794, nodes=4_000,
                interior=4_489)
    assert v["visited_per_select_on"] == 248.4, v
    assert v["visited_per_node_on"] == 235.6, v
    assert v["visited_per_node_on"] != v["visited_per_select_on"], \
        ("the two figures collapsed -- this case no longer distinguishes "
         "per-node from per-select, so it cannot catch the confusion")
    assert v["select_calls_per_node_on"] == 0.9485, v
    # the fraction must be built from the PER-NODE figure, not the other one
    assert v["visited_fraction_on"] == round(235.6 / 4_489, 4), v
    assert v["visited_fraction_on"] != round(248.4 / 4_489, 4), \
        "the fraction was built from the per-select figure"
    # a missing channel reads as None everywhere, never as 0
    assert all(x is None for x in visited(None, None, None, None).values())
    assert visited(100, 0, 0, 10)["visited_per_node_on"] is None
    assert visited(100, 0, 5, 10)["visited_per_select_on"] is None

    print("selftest OK: digest (5), speedup (5), first_divergence (3), "
          "identity_verdict (7 incl. vacuous-zero and two missing fields), "
          "visited (9 incl. the per-node/per-select confusion case)")


def main(out_path):
    entries = {e["subject"]: e for e in json.load(open(RULE6))}
    rec = {
        "measured_utc": datetime.datetime.now(datetime.UTC).isoformat(
            timespec="seconds"),
        "commit": _commit(),
        "budget": BUDGET,
        "ceilings": CEILINGS,
        "note": ("Identity is established BEFORE any speedup is quoted "
                 "(spec 4.4). The identity and timing passes are separate "
                 "runs because the identity pass instruments the search."),
        "rows": [],
    }

    def flush():
        with open(out_path, "w") as fh:
            json.dump(rec, fh, indent=1)

    flush()
    for s in SUBJECTS:
        row = {"subject": s}
        try:
            row.update(identity_pass(entries[s]))
            ok, bad = identity_verdict(row)
            row["identity_passed"] = ok
            row["identity_failures"] = bad
            if ok:
                row.update(timing_pass(entries[s]))
            else:
                row["timing_skipped"] = (
                    "identity failed, so a speedup would be meaningless "
                    "(spec 4.4)")
        except Exception as exc:                       # noqa: BLE001
            # Per-subject, so one engine failure does not lose the corpus.
            # `VertexIndexError` lands here too and is recorded as an
            # identity failure, which is what it is.
            row["outcome"] = f"{type(exc).__name__}: {exc}"[:400]
            row["identity_passed"] = False
        rec["rows"].append(row)
        flush()
        if not row.get("identity_passed"):
            print(f"{s}: IDENTITY FAILED -- "
                  f"{row.get('identity_failures') or row.get('outcome')}",
                  flush=True)
            continue
        print(f"{s}: identity OK | dense {row['dense_secs_off']}s -> "
              f"{row['dense_secs_on']}s ({row['speedup']}x); assign "
              f"{row['dense_assign_secs_off']}s -> "
              f"{row['dense_assign_secs_on']}s ({row['assign_speedup']}x) "
              f"| sparse {row['sparse_secs_off']}s -> "
              f"{row['sparse_secs_on']}s ({row['sparse_speedup']}x) "
              f"| visited/NODE {row['visited_per_node_off']} -> "
              f"{row['visited_per_node_on']} "
              f"({row['visited_fraction_on']}); per select "
              f"{row['visited_per_select_on']} on "
              f"{row['select_calls_per_node_on']} select/node", flush=True)

    passed = [r for r in rec["rows"] if r.get("identity_passed")]
    rec["identity_passed_count"] = len(passed)
    rec["corpus_size"] = len(SUBJECTS)
    flush()
    print()
    print(f"identity: {len(passed)} of {len(SUBJECTS)} subjects")
    print(f"ceilings (that directory's figures, for removing a component "
          f"ENTIRELY): {CEILINGS}")
    print("A ceiling is NOT a speedup. Task 4 must print the realised "
          "figure beside it and name the gap.")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    elif len(sys.argv) < 2:
        print("usage: ab.py <out.json> | ab.py --selftest", file=sys.stderr)
        raise SystemExit(1)
    else:
        main(sys.argv[1])
```

- [ ] **Step 2: Run the self-test**

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 ../docs/superpowers/evidence/2026-09-29-vertex-index/ab.py --selftest
```

Expected: `selftest OK: digest (5), speedup (5), first_divergence (3), identity_verdict (7 incl. vacuous-zero and two missing fields)`, exit 0. Do not proceed unless it passes.

- [ ] **Step 3: Prove the self-test is not vacuous**

Temporarily remove the `h.update(b"|")` separator from `digest`. Re-run `--selftest`. Expected: it **FAILS** on `digest([12]) != digest([1, 2])`. Restore and confirm green. Then temporarily make `identity_verdict` return `True, []` unconditionally and confirm the self-test fails; restore.

Record both outputs. A gate whose own tests cannot fail is this project's named recurring defect.

- [ ] **Step 4: Record the instrument's blob hash**

```bash
git hash-object docs/superpowers/evidence/2026-09-29-vertex-index/ab.py
```

Paste it in your report. Task 4 and the reviewer compare against it: an instrument edited after its run is one whose results cannot be reproduced from what is committed.

- [ ] **Step 5: Run it**

In the background, from `mcp_harness`:

```bash
PYTHONPATH=. ../.venv/bin/python3 -u ../docs/superpowers/evidence/2026-09-29-vertex-index/ab.py ../docs/superpowers/evidence/2026-09-29-vertex-index/ab.json
```

**Budget generously and check back at intervals rather than polling tightly.** This is four dense runs and four sparse runs per subject. The predecessor's ladder — one dense and one sparse arm per subject — took 34.3 minutes, so expect on the order of **two hours**. `ab.json` is flushed after every subject, so partial progress is always on disk.

**Do not edit `ab.py` once it has started.** If you believe it has a defect, stop and report BLOCKED.

- [ ] **Step 6: Check the run agrees with itself**

```bash
cd mcp_harness && ../.venv/bin/python3 -c "
import json
d = json.load(open('../docs/superpowers/evidence/2026-09-29-vertex-index/ab.json'))
print('commit', d['commit'][:7], '| budget', d['budget'])
print(f\"identity {d.get('identity_passed_count')} of {d.get('corpus_size')}\")
for r in d['rows']:
    if not r.get('identity_passed'):
        print(f\"{r['subject']:<11} FAILED {r.get('identity_failures') or r.get('outcome')}\")
        continue
    print(f\"{r['subject']:<11} nodes={r['dense_nodes_off']:<6} \"
          f\"dense {r['dense_secs_off']:>8}->{r['dense_secs_on']:<8} \"
          f\"{r['speedup']}x | visited {r['visited_per_node_off']}\"
          f\"->{r['visited_per_node_on']} ({r['visited_fraction_on']})\")
"
```

Expected: every row has `identity_passed: true`, matching node counts, and a `visited_fraction_on` near 0.09. **Any identity failure is a result and must be reported as one** — do not retry hoping for a different answer, and do not change the code to make it pass.

- [ ] **Step 7: Confirm nothing moved**

```bash
git status --porcelain docs/superpowers/evidence/2026-09-29-vertex-index/ab.py
git hash-object docs/superpowers/evidence/2026-09-29-vertex-index/ab.py
grep -c box_pleat mcp_harness/server.py
```

Expected: the first prints nothing, the second the same hash as Step 4, the third `0`.

- [ ] **Step 8: Commit both artifacts**

```bash
git add docs/superpowers/evidence/2026-09-29-vertex-index/ab.py \
        docs/superpowers/evidence/2026-09-29-vertex-index/ab.json
git commit -F <your message file>
```

Message content: how many subjects passed identity out of 8, the range of realised dense speedups, the visited-vertices-per-node figures, and that the ceilings are the predecessor's. State figures; draw no conclusions — that is Task 4's job. End with `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

---

### Task 4: The README, and the default-flip recommendation

**Files:**
- Create: `docs/superpowers/evidence/2026-09-29-vertex-index/README.md`

**Interfaces:**
- Consumes: `ab.json` from Task 3. Nothing else.
- Produces: the README. It is the deliverable.

**Context you need.** Every figure must come from `ab.json`, or be explicitly labelled as cited from a named other evidence directory. **This branch has withdrawn five of its own figures for being quoted forward without recomputation, and had a sixth withdrawal refused by the artifacts** — so both directions of that error have already happened here. Step 2 exists to catch it.

Do **not** carry the harness-check figures from Task 3's context block (the 1.36×, the 402.3, the 4,489) into the README. They were one subject at small budgets on one machine. Task 3's run supersedes them.

- [ ] **Step 1: Write the README**

Create `docs/superpowers/evidence/2026-09-29-vertex-index/README.md` with these sections, every figure taken from `ab.json`:

1. **The question.** The predecessor located dense `assign()`'s 79.57% residual as ~99% variable selection and 0.3–1.5% constraint checking; `pick()` rescanned every interior vertex at every node. This slice replaces that rescan. State up front that the goal is **dense measurable on more subjects, NOT convergence** (§1.1).
2. **Identity, before any timing.** How many of the 8 subjects passed, and for each: `sparse_fold_equal`, the dense node counts, and whether the two variable-sequence digests matched. **If any subject failed, the README stops here** and reports that no speedup may be quoted for it (§4.4). Say explicitly that the digest — not the node count — is what makes this meaningful, and why: node counts alone would pass two searches that diverged and reconverged.
3. **What the index changed mechanically.** `visited_per_node_off` against `visited_per_node_on` and `visited_fraction_on`, per subject. Note that the off figure is `interior` **by construction**. This is the mechanism's own claim, measured.
4. **The realised speedup, beside its ceiling.** Per subject: `dense_secs_off`, `dense_secs_on`, `speedup`, and the two `ceilings` values labelled as **cited from `../2026-09-29-local-csp-profile/`**. **Name the gap between realised and ceiling** and state why one exists: a ceiling prices removing a component *entirely*, which no real optimisation achieves (§5.3).
5. **Sparse.** `sparse_secs_off` / `sparse_secs_on` / `sparse_speedup`. Expected small, and say so plainly if it is — sparse cost is what gates corpus size, so it was measured rather than assumed.
6. **What this buys, concretely.** Given the realised speedup, how much cheaper is a dense run at a fixed budget, and therefore how many more subjects fit a given time budget? That is §1.1's goal, and it is the only claim this slice supports.
7. **What this cannot say (§8).** Nothing about convergence — and note this item's own original wording, "the ceiling caps it at 3.492×", was the false generalisation the run refuted: that is `lizard`'s ceiling, and `bird` realised 28.154×. A ceiling is not a speedup. Nothing about the CEGAR regime, since the predecessor's ladder had 3 of 8 subjects at zero rejections and the rest at 1–10. Nothing about the >8-flap wall, `layer_order` confluence, or the serve path.
8. **The default-flip recommendation (§9).** State plainly whether the flag should now default to **on**, and base it on the identity results across the whole corpus, not on the speedup. Note explicitly that shipping an optimisation permanently behind an off-by-default flag means paying for the work and never collecting it, and that a flip changes what every dense compile does — so the recommendation is evidenced, and it is the owner's call.
9. **Run metadata.** `measured_utc`, `commit`, `budget`, and `ab.py`'s blob hash with the statement that it is unchanged from before the run.

- [ ] **Step 2: Check every README figure against the artifact**

Re-read the README beside `ab.json` and confirm each number appears in it or is labelled as cited. Any figure that does not must be removed or recomputed with its derivation shown. **Show this arithmetic in your report, rather than asserting you did it.**

- [ ] **Step 3: Confirm nothing was edited**

```bash
git status --porcelain docs/superpowers/evidence/2026-09-29-vertex-index/
git diff --stat HEAD -- mcp_harness/
git hash-object docs/superpowers/evidence/2026-09-29-vertex-index/ab.py
```

Expected: the only untracked path is `README.md`; the second prints nothing; the third matches Task 3's hash.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/evidence/2026-09-29-vertex-index/README.md
git commit -F <your message file>
```

Message content: one clause for the verdict, then a paragraph giving the identity result across the corpus, the realised speedup range beside the ceiling, the visited-vertices-per-node change, and the default-flip recommendation. End with `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

---

## Self-Review

**Spec coverage.**

| spec section | task |
|---|---|
| §1.1 goal is not convergence | Task 1's module docstring; Task 3's `ab.py` docstring; Task 4 item 1 and item 7 |
| §2 prior art adopted / rejected | Task 1's module docstring names Chaff's watched literals and Glasgow #879 |
| §3.1 the key reduction | `VertexIndex.select`, and the construction-time refusal of a `domain`/`pleat_pref` overlap |
| §3.2 the index, two sets, no rebuild | `VertexIndex.__init__`'s `nonempty_all` / `nonempty_pleat` with the phase-flip comment |
| §3.3 Trap 1 aliasing | `vars_at` and `vertices_of` as sets; Task 1 Steps 1 and 5, mutation-proved |
| §3.3 Trap 2 only `fv[0]` is read | Task 2 Step 4's `return chosen, eligible(chosen)` and its comment |
| §3.3 Trap 3 positional tie-break | `self.order` in both `min` keys; Task 1 Steps 1 and 6, mutation-proved |
| §3.4 what `pick` becomes | Task 2 Step 4 |
| §4.1 the invariant check | `_verify_index`, run by two tests in Task 2 Step 1 |
| §4.2 sparse byte-identity | Task 2's two sparse tests; Task 3's `identity_pass` |
| §4.3 dense identity + sequence digest | Task 2's dense test; `digest()` and `identity_verdict` in Task 3 |
| §4.4 identity before timing | `identity_verdict` gating `timing_pass`; two separate passes |
| §5.1 the A/B | Task 3 `timing_pass` over 8 subjects at `BUDGET` |
| §5.2 the required figures | `ab.json`'s timing, speedup, sparse and visited-per-node fields; Task 4 items 3-5 |
| §5.3 the ceiling discipline | `CEILINGS`, printed beside every realised figure; Task 4 item 4 |
| §6 files | File Structure |
| §7 testing, anti-vacuity | Task 1 Steps 5-6, Task 2 Step 9, Task 3 Step 3 |
| §8 what it cannot say | Task 4 item 7 |
| §9 the default flip | Task 4 item 8 |
| §10 out of scope | Global Constraints and Task 2 Step 10 |

**Placeholder scan.** The only intentional placeholders are the four commit messages, which cannot be written before their results exist; each has its required content enumerated. `<your message file>` is deliberate — a heredoc containing backticks has already been mangled by zsh in this project.

**Type consistency.** `VertexIndex`'s six constructor arguments are passed in that order at Task 2 Step 5. `count_at(v, pleat_open)`, `select(pleat_open)`, `bind(x)`, `unbind(x)`, `snapshot()`, `pool_calls` and `pool_total` are the only members Task 2 touches, and all seven are defined in Task 1. `debug_search`'s five keys — `nodes`, `vars`, `interior`, `pool_calls`, `pool_total` — are written in Task 2 Step 5 and read in Task 3's `identity_pass`. `VertexIndexError` is raised in Task 1's constructor and in Task 2's `_verify_index`, imported once at Task 2 Step 3, and deliberately not caught by `compile.py`.

**Executed before shipping.** Tasks 1 and 2 were applied to real files and run: Task 1's file gives `19 passed`, Task 2's `5 passed` (`6 passed` after the review-findings wave added `test_verify_without_the_index_refuses`), and the three pre-existing box-pleat files give `13 passed` both before and after the change. Four mutations were confirmed red and one was found **green** — see Task 2 Step 9's item 3, which was corrected from a wrong prediction to the real asymmetry. The `was_bound` guard in Task 2 Step 5 exists because the first draft omitted it and `_verify_index` caught the resulting drift on sparse `lizard` within 21 seconds.
