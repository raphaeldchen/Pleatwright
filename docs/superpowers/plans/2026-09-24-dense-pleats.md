# Dense Pleats (gap 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `box_pleat` emit densely pleated crease patterns by adopting COrigami F.2 interleaving, replacing the branch that currently pins 81% of all crease pieces to `F` before the search starts.

**Architecture:** Additive, behind a `dense: bool = False` flag threaded from `compile_tree` down to `assign`. A new pure module `box_pleat/interleave.py` implements F.2 (path ordering, adjacency, 2-colouring). `assign.pleat_paths` gains connectivity-only grouping for dense mode. `assign.initial_readings` stops pinning `F`. `assign.assign` turns F.2's colour into a **single-value** domain, which is what makes this approach A. Nothing is replaced: `contours.py`, the elevation field, the CSP mechanism and the layer stage are untouched.

**Tech Stack:** Python 3.14, pytest, no new dependencies.

**Scope note:** this plan covers spec components **2 and 3 only**, per spec §8 ("Components 2 + 3, then measure; Component 1, then measure again"). Component 1 (`pleat_grid.py`, F.1.1 step 5 coverage) gets its own plan **after** this plan's measurement lands, because its design depends on what Task 2 and Task 7 find.

## Global Constraints

Copied verbatim from the spec. Every task's requirements implicitly include this section.

- **Byte-identity, load-bearing.** With `dense=False`, every currently-emitting subject must reproduce its committed fold **byte-for-byte**.

  ⚠ **The e2e test does NOT establish this, measured 2026-09-25.** `test_already_consistent_subjects_emit_byte_identical_folds` covers **only `bird` and `starfish`** — the two subjects with `layers_tried == 1`, i.e. the two that accept the FIRST candidate and therefore never enter the CEGAR relabelling loop. The other six (`lizard`, `horse`, `octopus`, `frog`, `guinea_pig`, `dog`) do enter it, and this plan modifies `assign`'s variable-setup block, which that loop runs through. The guard passes where the change cannot hurt and is silent where it can.

  Running it is still required at each task, but it is a smoke test, not the guarantee. **The guarantee is established once, over all 8 subjects, in Task 8 Step 0**, by the method the previous wave used: dump folds from a pre-branch checkout via `git archive <base> | tar -x` plus `PYTHONPATH`, dump them again from HEAD, and compare sha256 field-for-field. Never `git stash`, never `git checkout`, never move HEAD.
- **Byte-identity constrains BEHAVIOUR, not structure.** Refactoring that preserves bytes is *encouraged*. **Forbidden** because each changes which solution the CSP reaches first: reordering the centre-column domain (`["F"] + [lab, opposite]`, `assign.py:278`) and altering `label_from_profile`'s mirroring (`if lo is None: lo = e + (e - hi)`).
- **F.2's pleats outrank CEGAR.** In dense mode the `layers` stage's relabelling search may relabel **hinges and ridges only**; F.2's pleat labels are fixed and the search may not flip them. Sparse mode's CEGAR behaviour is unchanged.
- **Certification is computed and reported, never blocking, in dense mode only.** `compile.py` keeps its `CERTIFIED` refusal exactly as merged for sparse mode. Do not "optimise" the dense verdict away as dead work — the verdict is the deliverable.
- **Every count assertion is paired with a non-vacuity assertion.** PR #193 shipped two tests that read `0 == 0` against fixtures generating zero of the thing under test. Do not repeat it.
- **`layer_order.py` is not edited by this plan.** `git diff <base> HEAD -- mcp_harness/layer_order.py` must be empty at every task boundary.
- **The serve path stays untouched.** `grep -n "box_pleat" mcp_harness/server.py` must return zero matches at every task boundary.
- **Pin verdicts, never witness strings.** Witnesses move between runs; verdicts do not.
- **Run all commands from the worktree root** (`<repo>`). Never `cd` to the original repository root.
- **Never use bare `git stash` / `git stash pop`** — the stash stack is shared with other worktrees and sessions. Use a temporary WIP commit instead.
- **Use `../.venv/bin/python3` from inside `mcp_harness`, never bare `python3`.** The system interpreter lacks `skeletor`, which `mcp_harness/tests/conftest.py` imports, so bare `python3 -m pytest` fails at collection with `ModuleNotFoundError: No module named 'skeletor'` before any test runs. Found by Task 1's implementer.
- **Commit message trailer:** `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`

## Domain primer (the implementer has no context for this)

- A **crease pattern** here is a FOLD-format dict: `vertices_coords`, `edges_vertices`, `edges_assignment`. An assignment is `"M"` (mountain), `"V"` (valley), `"B"` (paper border) or `"F"` (flat — **not a crease at all**).
- **`emit.to_fold` drops every `F` piece** (`emit.py:31`). So `F` means "this candidate line does not become a crease".
- Coordinates are **half-grid integers** in `[0, 2N]` for an `N x N` box-pleat grid. `Point = tuple[int, int]`. One *grid* unit is **2** half-grid units; adjacent half-grid lines differ by **1**.
- A **`Piece`** is one unit segment: `Piece(a: Point, b: Point, role: str)` with `role` in `B | axial | elev | ridge | hinge`. `elev` pieces are elevation contours — the pleats.
- **`Assignment`** is `(pieces: list, labels: list)`, index-aligned.
- The measured problem: on `bird` (N=54), `build_pieces` makes 12,868 pieces, 11,144 of them `elev`. `initial_readings` hard-pins **10,456** to `F`, leaving 1,078 free variables. Those 10,456 are the density we are recovering.

---

### Task 1: `interleave.py` — COrigami F.2 as a pure function

**Files:**
- Create: `mcp_harness/box_pleat/interleave.py`
- Test: `mcp_harness/tests/test_box_pleat_interleave.py`

**Interfaces:**
- Consumes: `box_pleat.assign.Piece` (fields `a`, `b`, `role`).
- Produces, relied on by Tasks 3 and 4:
  - `origin_key(pieces: list, group: list[int]) -> tuple`
  - `adjacency(pieces: list, groups: list[list[int]]) -> dict[int, set[int]]`
  - `OddCycle` (frozen dataclass: `groups: tuple[int, ...]`)
  - `colour(pieces: list, groups: list[list[int]]) -> tuple[dict[int, str] | None, OddCycle | None]`

**Why this is a pure module:** it touches no CSP, no geometry construction and no I/O, so it is testable from hand-built `Piece` lists alone. That matters because it is the only place F.2 itself lives.

- [ ] **Step 1: Write the failing tests**

Create `mcp_harness/tests/test_box_pleat_interleave.py`:

```python
"""COrigami F.2 interleaving, tested on hand-built piece lists.

Every fixture here is built by hand rather than compiled, so each test states
exactly the geometry it depends on. Counts are paired with non-vacuity
assertions: a fixture that generates zero paths would make `len(...) == 0`
pass while testing nothing.
"""
import pytest

from box_pleat.assign import Piece
from box_pleat import interleave


def _hline(y, x0, x1):
    """Horizontal unit pieces along row `y`, from x0 to x1 (half-grid)."""
    return [Piece((x, y), (x + 1, y), "elev") for x in range(x0, x1)]


def test_origin_key_orders_by_distance_from_origin():
    pieces = _hline(0, 0, 2) + _hline(4, 0, 2)
    near, far = [0, 1], [2, 3]
    assert interleave.origin_key(pieces, near) < interleave.origin_key(pieces, far)


def test_adjacency_links_paths_one_half_grid_unit_apart():
    pieces = _hline(0, 0, 3) + _hline(1, 0, 3)
    groups = [[0, 1, 2], [3, 4, 5]]
    adj = interleave.adjacency(pieces, groups)
    assert adj[0] == {1} and adj[1] == {0}


def test_adjacency_does_not_link_paths_two_units_apart():
    pieces = _hline(0, 0, 3) + _hline(2, 0, 3)
    groups = [[0, 1, 2], [3, 4, 5]]
    adj = interleave.adjacency(pieces, groups)
    # non-vacuity: the groups exist and were considered
    assert set(adj) == {0, 1}
    assert adj[0] == set() and adj[1] == set()


def test_colour_alternates_across_adjacent_paths():
    pieces = _hline(0, 0, 3) + _hline(1, 0, 3) + _hline(2, 0, 3)
    groups = [[0, 1, 2], [3, 4, 5], [6, 7, 8]]
    col, odd = interleave.colour(pieces, groups)
    assert odd is None
    assert col is not None and len(col) == 3      # non-vacuity
    assert col[0] != col[1] and col[1] != col[2]
    assert col[0] == col[2]                        # alternation, not randomness
    assert set(col.values()) <= {"M", "V"}


def test_colour_starts_from_the_path_nearest_the_origin():
    """The BFS root is the nearest path, and it takes M. Pinning this makes
    the whole assignment deterministic rather than traversal-dependent."""
    pieces = _hline(5, 0, 3) + _hline(0, 0, 3)
    groups = [[0, 1, 2], [3, 4, 5]]      # group 1 is nearer the origin
    col, odd = interleave.colour(pieces, groups)
    assert odd is None and col is not None
    assert col[1] == "M"


def test_colour_reports_an_odd_cycle_instead_of_guessing():
    """Three mutually adjacent paths cannot alternate. F.2 is a 2-colouring,
    so an odd cycle in the adjacency graph makes strict alternation
    impossible -- the function must SAY so, not pick something."""
    # a triangle: rows 0 and 1 adjacent, 1 and 2 adjacent, and a vertical
    # path touching rows 0 and 2 one unit from both.
    pieces = (_hline(0, 0, 2) + _hline(1, 0, 2)
              + [Piece((5, 0), (5, 1), "elev"), Piece((5, 1), (5, 2), "elev")]
              + _hline(2, 0, 2))
    groups = [[0], [1], [2, 3], [4]]
    adj = {0: {1, 3}, 1: {0, 3}, 3: {0, 1}}
    col, odd = interleave.colour_graph(adj)
    assert col is None
    assert odd is not None
    assert len(odd.groups) >= 3                    # non-vacuity
    assert len(set(odd.groups)) == len(odd.groups)


def test_colour_graph_two_colours_a_bipartite_graph():
    adj = {0: {1}, 1: {0, 2}, 2: {1}}
    col, odd = interleave.colour_graph(adj)
    assert odd is None and col is not None and len(col) == 3
    assert col[0] != col[1] and col[1] != col[2]


def test_disconnected_components_each_start_at_M():
    """Two components with no adjacency between them. Each is rooted
    independently, so both roots take M -- otherwise the result would depend
    on dict iteration order."""
    adj = {0: set(), 1: set()}
    col, odd = interleave.colour_graph(adj)
    assert odd is None and col == {0: "M", 1: "M"}
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python3 -m pytest tests/test_box_pleat_interleave.py -v
```

Expected: **collection error**, `ModuleNotFoundError: No module named 'box_pleat.interleave'`. Note that pytest reports this as a collection failure and runs **zero** tests — it does not report 8 individual failures. Report what you actually see.

- [ ] **Step 3: Write `interleave.py`**

Create `mcp_harness/box_pleat/interleave.py`:

```python
"""COrigami F.2: interleaving assignment for pleat paths.

The paper (arXiv:2606.26299 appendix F.2) specifies three bullets:

  * Pleats are grouped into paths of connected segments.
  * Paths are sorted by their distance from the origin.
  * A Breadth-First Search is employed to assign fold orientations. Adjacent
    paths separated by a single grid unit are assigned alternating Mountain
    and Valley orientations.

The first bullet is `assign.pleat_paths`, which already cites F.2. This module
is the other two.

**Alternation across an adjacency graph is exactly a 2-colouring, so it is
possible if and only if that graph is bipartite.** An odd cycle is therefore
not an edge case to paper over but the precise, checkable statement that F.2
cannot be satisfied on this geometry, and `colour` returns it instead of
picking an arbitrary label. This is the same shape as `layer_certify.collapse`,
which refutes on an odd cycle in its parity quotient.

Adjacency is **facing**, not proximity: two paths are adjacent iff one holds
a unit piece and the other holds a unit piece of the SAME orientation,
ALIGNED on the parallel axis, exactly 1 unit away on the perpendicular axis.
An earlier version tested only "within one unit orthogonally", with no
parallelism or alignment test, and measured non-bipartite on starfish, horse
and octopus with an odd cycle of length exactly 3 every time -- a
perpendicular path crowding two parallel pleats closed a triangle.

The distance is 1 half-grid unit, the finest spacing this geometry admits:
`contours.py` places contours on half-grid lines, so a 2-unit test would skip
every odd line entirely.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

ORIGIN = (0, 0)
FLIP = {"M": "V", "V": "M"}


@dataclass(frozen=True)
class OddCycle:
    """Group indices forming a cycle of odd length in the adjacency graph.

    Its existence means strict alternation is impossible: the first and last
    entries are adjacent and would need the same colour.
    """
    groups: tuple


def _points(pieces, group):
    return [p for i in group for p in (pieces[i].a, pieces[i].b)]


def origin_key(pieces, group) -> tuple:
    """Sort key: squared distance from the origin of the path's nearest point.

    The point itself is the tiebreak, so the order is total and does not
    depend on how `group` was built.
    """
    pts = _points(pieces, group)
    near = min(pts, key=lambda q: (q[0] * q[0] + q[1] * q[1], q))
    return (near[0] * near[0] + near[1] * near[1], near)


def _unit_cells(pieces, group) -> set:
    """Half-grid points the path occupies."""
    return set(_points(pieces, group))


def adjacency(pieces, groups) -> dict:
    """Map group index -> set of group indices exactly 1 half-grid unit away.

    Two groups are adjacent when a point of one is orthogonally one unit from
    a point of the other. Every group index appears as a key, including
    isolated ones, so a caller can tell "considered, no neighbours" from
    "never considered".
    """
    cells = [_unit_cells(pieces, g) for g in groups]
    owner: dict = {}
    for gi, cs in enumerate(cells):
        for c in cs:
            owner.setdefault(c, set()).add(gi)

    adj: dict = {gi: set() for gi in range(len(groups))}
    for gi, cs in enumerate(cells):
        for (x, y) in cs:
            for nb in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                for gj in owner.get(nb, ()):
                    if gj != gi:
                        adj[gi].add(gj)
                        adj[gj].add(gi)
    return adj


def colour_graph(adj: dict) -> tuple:
    """2-colour `adj` by BFS. Returns `(colours, None)` or `(None, OddCycle)`.

    Roots are taken in ascending key order and every root takes "M", so the
    result never depends on dict iteration order.
    """
    colour: dict = {}
    parent: dict = {}
    for root in sorted(adj):
        if root in colour:
            continue
        colour[root] = "M"
        parent[root] = None
        q = deque([root])
        while q:
            u = q.popleft()
            for v in sorted(adj[u]):
                if v not in colour:
                    colour[v] = FLIP[colour[u]]
                    parent[v] = u
                    q.append(v)
                elif colour[v] == colour[u]:
                    return None, OddCycle(_cycle(parent, u, v))
    return colour, None


def _cycle(parent, u, v) -> tuple:
    """The odd cycle closed by the edge (u, v): both paths to their common
    ancestor, joined. Reported for diagnosis, never for control flow."""
    def up(x):
        seen = [x]
        while parent[x] is not None:
            x = parent[x]
            seen.append(x)
        return seen

    a, b = up(u), up(v)
    sb = set(b)
    meet = next((x for x in a if x in sb), None)
    ia = a[:a.index(meet) + 1] if meet is not None else a
    ib = b[:b.index(meet)] if meet is not None else b
    return tuple(ia + list(reversed(ib)))


def colour(pieces, groups) -> tuple:
    """F.2 end to end: order the paths, build adjacency, 2-colour.

    Returns `(colours_by_group_index, None)` or `(None, OddCycle)`.
    """
    order = sorted(range(len(groups)), key=lambda gi: origin_key(pieces, groups[gi]))
    rank = {gi: r for r, gi in enumerate(order)}
    adj = adjacency(pieces, groups)
    # Colour in ORIGIN-DISTANCE order, not index order: F.2's BFS starts from
    # the path nearest the origin. Relabel so `colour_graph`'s ascending-key
    # roots are that order, then map back.
    radj = {rank[gi]: {rank[gj] for gj in nb} for gi, nb in adj.items()}
    col, odd = colour_graph(radj)
    if odd is not None:
        return None, OddCycle(tuple(order[r] for r in odd.groups))
    return {order[r]: c for r, c in col.items()}, None
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python3 -m pytest tests/test_box_pleat_interleave.py -v
```

Expected: **8 passed**.

- [ ] **Step 5: Verify the global constraints still hold**

```bash
cd mcp_harness && grep -c "box_pleat" server.py; git diff --stat HEAD -- layer_order.py
```

Expected: `0` from grep (it prints `0` and exits 1 — that is the pass condition), and an empty diff.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/box_pleat/interleave.py mcp_harness/tests/test_box_pleat_interleave.py
git commit -m "$(cat <<'MSG'
box_pleat: COrigami F.2 interleaving as a pure 2-colouring

Alternation across adjacent pleat paths is exactly a 2-colouring, so it is
possible iff the adjacency graph is bipartite. colour() returns an OddCycle
rather than guessing a label when it is not -- the same shape as
layer_certify.collapse refuting on an odd cycle in its parity quotient.

Adjacency is measured at 1 half-grid unit, the finest spacing contours.py
admits; a 2-unit test would skip every odd line.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
MSG
)"
```

---

### Task 2: The bipartiteness probe script (the gate itself is deferred to Task 4)

**Files:**
- Already committed: `docs/superpowers/evidence/2026-09-24-dense-pleats/bipartite_probe.py`

**Status: the script exists and is committed. Do not run it against the sparse grouping — that measurement cannot answer the question.**

**Why this task is now a no-op, recorded rather than deleted.** The original Task 2 ran the probe over the EXISTING sparse `pleat_paths` grouping and treated a non-bipartite reading as conclusive, on the stated reasoning that "denser grouping only adds edges, so sparse is a lower bound on difficulty."

That reasoning is false. The sparse grouping is not a subgraph of the dense one. It keeps roughly 6% of the pleats, so the spacing between surviving paths is an artifact of the discard this plan exists to remove — measured perpendicular offsets between aligned parallel pieces are bimodal and subject-dependent (`bird` mode 2 with zero pairs at offset 1; `horse` mode 6 with zero pairs at offset 2). A gate run on that graph answers a question nobody asked.

**The gate runs at Task 4, Step 6, on the dense grouping.** Its stopping rule is unchanged and absolute: any subject reading `bipartite=False` halts the plan and escalates to the human, because the fallback (COrigami's trap-and-release pleat reassignment) is a design decision reserved for them.

**Consequence accepted by the owner (2026-09-24):** Tasks 3 and 4 are built before the gate can be evaluated. Both are additive and sit behind the `dense` flag, so a failed gate invalidates neither sparse-mode behaviour nor the byte-identity guarantee.

- [ ] **Step 1: Confirm the probe script is present and unmodified**

```bash
git log --oneline -- docs/superpowers/evidence/2026-09-24-dense-pleats/bipartite_probe.py
```

Expected: at least one commit. No action beyond confirming it exists — Task 4 Step 6 edits and runs it.

---

### Task 3: Connectivity-only path grouping for dense mode

**Files:**
- Modify: `mcp_harness/box_pleat/assign.py:288-333` (`pleat_paths`)
- Test: `mcp_harness/tests/test_box_pleat_assign.py`

**Interfaces:**
- Consumes: nothing new.
- Produces, relied on by Tasks 4 and 5: `pleat_paths(pieces, labels, *, dense: bool = False) -> list[list[int]]`.

**Why this change is needed.** `pleat_paths` currently selects pieces with `labels[i] in ("M", "V")` and unions two pieces at a vertex only `if labels[i] == labels[j]`. Both tests consult the *profile-derived* label. In dense mode the previously-`F` pieces have no meaningful profile label to agree on, and F.2 groups purely by connectivity — *"pleats are grouped into paths of connected segments"*. So dense mode selects every `axial`/`elev` piece and unions on connectivity alone.

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_box_pleat_assign.py`:

```python
def test_pleat_paths_dense_groups_pieces_the_sparse_form_drops():
    """Sparse grouping consults the profile label twice: to SELECT a piece and
    to decide whether two pieces join. Dense grouping does neither -- F.2
    groups by connectivity."""
    from box_pleat.assign import Piece, pleat_paths
    pieces = [Piece((0, 0), (1, 0), "elev"),
              Piece((1, 0), (2, 0), "elev"),
              Piece((2, 0), (3, 0), "elev")]
    labels = ["M", "F", "M"]          # the middle piece is dropped when sparse

    sparse = pleat_paths(pieces, labels)
    dense = pleat_paths(pieces, labels, dense=True)

    flat_sparse = sorted(i for g in sparse for i in g)
    flat_dense = sorted(i for g in dense for i in g)
    assert flat_sparse == [0, 2]            # non-vacuity: sparse really drops it
    assert flat_dense == [0, 1, 2]
    assert len(dense) == 1                  # and connectivity joins them
    assert dense[0] == [0, 1, 2]


def test_pleat_paths_dense_joins_pieces_whose_labels_disagree():
    """The sparse form refuses to union two pieces carrying different labels.
    Dense mode must union them anyway: their label is F.2's to decide, so a
    disagreement in the seed is not information."""
    from box_pleat.assign import Piece, pleat_paths
    pieces = [Piece((0, 0), (1, 0), "elev"), Piece((1, 0), (2, 0), "elev")]
    labels = ["M", "V"]

    sparse = pleat_paths(pieces, labels)
    dense = pleat_paths(pieces, labels, dense=True)

    assert len(sparse) == 2                 # non-vacuity: they really are split
    assert len(dense) == 1 and dense[0] == [0, 1]


def test_pleat_paths_dense_still_splits_at_a_ridge_vertex():
    """The conservative rule that a ridge or hinge landing at a vertex breaks
    the path is about GEOMETRY, not labels, so dense mode keeps it."""
    from box_pleat.assign import Piece, pleat_paths
    pieces = [Piece((0, 0), (1, 0), "elev"),
              Piece((1, 0), (2, 0), "elev"),
              Piece((1, 0), (1, 1), "ridge")]
    dense = pleat_paths(pieces, ["M", "M", None], dense=True)
    assert len(dense) == 2                  # non-vacuity: two groups, not one
    assert sorted(i for g in dense for i in g) == [0, 1]


def test_pleat_paths_sparse_behaviour_is_unchanged():
    """Byte-identity depends on the sparse path being untouched."""
    from box_pleat.assign import Piece, pleat_paths
    pieces = [Piece((0, 0), (1, 0), "elev"), Piece((1, 0), (2, 0), "elev")]
    assert pleat_paths(pieces, ["M", "M"]) == [[0, 1]]
    assert pleat_paths(pieces, ["M", "F"]) == [[0]]
```

- [ ] **Step 2: Run them to verify they fail**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python3 -m pytest tests/test_box_pleat_assign.py -k "pleat_paths_dense or pleat_paths_sparse" -v
```

Expected: the three `dense` tests FAIL with `TypeError: pleat_paths() got an unexpected keyword argument 'dense'`. `test_pleat_paths_sparse_behaviour_is_unchanged` **passes already** — it pins existing behaviour, which is its job.

- [ ] **Step 3: Implement**

In `mcp_harness/box_pleat/assign.py`, change the signature and the two label tests:

```python
def pleat_paths(pieces, labels, *, dense: bool = False) -> list:
    """Groups of contour pieces that MUST carry the same label.

    Two folded creases meeting at a vertex where nothing else but the paper
    edge lands are forced equal: Maekawa needs |M - V| = 2 and two creases
    have no mixed solution. Grouping them into one variable is also what
    COrigami §F.2 does ("pleats are grouped into paths of connected
    segments"), and it is why the variable count stays in the hundreds.

    Conservative on purpose: a vertex where a ridge or hinge also lands
    leaves its pieces in separate groups. That costs variables, never
    correctness.

    `dense=True` groups by CONNECTIVITY ALONE, which is what F.2 specifies.
    The sparse form consults `labels` twice -- to select a piece and to
    decide whether two pieces join -- and both tests read the
    profile-derived label. In dense mode that label is not information: F.2
    decides it. The ridge/hinge split above is geometric, not label-based,
    so it is kept in both modes.
    """
    inc: dict = {}
    for i, p in enumerate(pieces):
        if p.role not in ("axial", "elev"):
            continue
        if not dense and labels[i] not in ("M", "V"):
            continue
        inc.setdefault(p.a, []).append(i)
        inc.setdefault(p.b, []).append(i)
    parent = list(range(len(pieces)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        a, b = find(i), find(j)
        if a != b:
            parent[max(a, b)] = min(a, b)

    other: dict = {}
    for i, p in enumerate(pieces):
        if p.role == "B":
            continue
        for v in (p.a, p.b):
            other[v] = other.get(v, 0) + 1
    for v, ids in inc.items():
        if len(ids) == 2 and other.get(v, 0) == 2:
            i, j = ids
            if dense or labels[i] == labels[j]:
                union(i, j)
    groups: dict = {}
    for i in {j for ids in inc.values() for j in ids}:
        groups.setdefault(find(i), []).append(i)
    return [sorted(g) for g in groups.values()]
```

- [ ] **Step 4: Run them to verify they pass**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python3 -m pytest tests/test_box_pleat_assign.py -v
```

Expected: the whole file passes, including the pre-existing tests (the sparse path is unchanged by construction — `dense` defaults to `False` and both new conditions collapse to the originals).

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/box_pleat/assign.py mcp_harness/tests/test_box_pleat_assign.py
git commit -m "$(cat <<'MSG'
box_pleat: pleat_paths groups by connectivity alone in dense mode

The sparse form consults the profile label twice -- to select a piece and to
decide whether two join. In dense mode that label is not information, because
F.2 decides it; F.2 groups "pleats into paths of connected segments". The
ridge/hinge split stays in both modes: it is geometric, not label-based.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
MSG
)"
```

---

### Task 4: `initial_readings` stops pinning F, plus the permitted tidying

**Files:**
- Modify: `mcp_harness/box_pleat/assign.py:244-285` (`initial_readings`)
- Test: `mcp_harness/tests/test_box_pleat_assign.py`

**Interfaces:**
- Consumes: nothing new.
- Produces, relied on by Task 5: `initial_readings(N, pieces, contours, prof, face_of, *, dense: bool = False) -> (labels, domain, pleat_lab, probe)`. In dense mode every `axial`/`elev` off-column piece lands in `pleat_lab` (so `probe` marks it a pleat candidate and `pleat_paths` groups it); none is written into `labels`.

**The measured facts this task changes** (from the spec §2): `bird` 10,456 hard-pinned `F` -> 0, free variables 1,078 -> 11,534. `lizard` 4,392 -> 0, 96 -> 4,488.

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_box_pleat_assign.py`:

```python
def _readings_for(subject, dense):
    """Compile `subject` and rebuild its pre-search readings both ways."""
    import json
    from box_pleat import assign as A
    from box_pleat.compile import compile_tree
    entries = {e["subject"]: e for e in json.load(open(
        "../docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/data/rule6_serve.json"))}
    e = entries[subject]
    res = compile_tree(e["requested"], e["pairs"])
    assert res.stage_reached == "emit", res.stage_reached
    N, pieces = res.layout.N, res.assignment.pieces
    face_list = A.faces(N, pieces)
    prof, face_of = A.profiles(N, pieces, res.contours, face_list)
    return pieces, A.initial_readings(N, pieces, res.contours, prof, face_of,
                                      dense=dense)


@pytest.mark.slow
def test_dense_readings_pin_no_piece_to_F():
    pieces, (labels, domain, pleat_lab, probe) = _readings_for("lizard", True)
    pinned_F = [i for i, l in enumerate(labels) if l == "F"]
    assert pinned_F == []
    # non-vacuity: the sparse run really does pin thousands, so the zero above
    # is a change, not an empty fixture.
    _, (s_labels, _, s_pleat, _) = _readings_for("lizard", False)
    assert sum(1 for l in s_labels if l == "F") > 1000
    assert len(pleat_lab) > len(s_pleat) * 10


@pytest.mark.slow
def test_dense_readings_leave_boundary_pieces_fixed():
    """B is a paper border, not a crease. Unpinning F must not unpin B."""
    pieces, (labels, _, pleat_lab, _) = _readings_for("lizard", True)
    b = [i for i, p in enumerate(pieces) if p.role == "B"]
    assert b                                   # non-vacuity
    assert all(labels[i] == "B" for i in b)
    assert not any(i in pleat_lab for i in b)


@pytest.mark.slow
def test_sparse_readings_are_unchanged_by_this_task():
    """Byte-identity's precondition, asserted directly on the readings."""
    pieces, (labels, domain, pleat_lab, probe) = _readings_for("lizard", False)
    assert sum(1 for l in labels if l == "F") == 4392
    assert len(pleat_lab) == 48
    assert len(domain) == 48
```

- [ ] **Step 2: Run them to verify they fail**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python3 -m pytest tests/test_box_pleat_assign.py -k "dense_readings or sparse_readings" -v -m slow
```

Expected: the two `dense_readings` tests FAIL with `TypeError: initial_readings() got an unexpected keyword argument 'dense'`. `test_sparse_readings_are_unchanged_by_this_task` PASSES already — it pins the numbers the spec measured.

- [ ] **Step 3: Implement, including the three permitted tidyings**

Replace `initial_readings` in `mcp_harness/box_pleat/assign.py`:

```python
def initial_readings(N, pieces, contours, prof, face_of, *, dense: bool = False):
    """Each piece's starting label, before any search.

    Returns `(labels, domain, pleat_lab, probe)`:

    * `labels[i]` is a FIXED label -- "B" for boundary, "F" for an
      off-column slope -- or None where `i` is a variable.
    * `domain[i]` is the value order for a centre-column variable: F first,
      where a flat plan view is feasible.
    * `pleat_lab[i]` is an off-column piece's elevation-profile reading,
      which becomes its pleat path's FIRST value.
    * `probe` is the label vector those readings imply, which is what
      `pleat_paths` must be grouped over -- not a solved assignment, whose
      groups differ because the search may have flipped a path.

    Extracted so `pleat_paths`' input can be reconstructed without copying
    this branch structure: the grouping is only meaningful against `probe`,
    and a test that rebuilt it by hand would drift from this loop silently
    (Task 5 review, 2026-09-23).

    `dense=True` (COrigami F.2, spec 2026-09-24) stops pinning "F". An
    off-column piece whose elevation profile reads a monotone slope becomes a
    VARIABLE rather than a fixed flat line, so F.2's interleaving can give it
    a fold. Its `pleat_lab` entry is provisional and exists so `probe` marks
    it a pleat candidate for `pleat_paths(dense=True)`; the value is replaced
    wholesale by `interleave.colour`. "B" stays fixed in both modes -- a paper
    border is not a crease.
    """
    labels: list = [None] * len(pieces)
    domain: dict = {}          # variable -> value order
    pleat_lab: dict = {}       # off-column piece -> its profile reading
    for i, p in enumerate(pieces):
        if p.role == "B":
            labels[i] = "B"
        elif p.role in ("axial", "elev"):
            # `on_column` is only read in this branch; ridge/hinge and B
            # pieces never consult it.
            on_column = p.a[0] == p.b[0] == N
            horizontal = p.a[1] == p.b[1]
            s = p.a[1] if horizontal else p.a[0]
            lab = label_from_profile(prof[face_of[(p.a, p.b)]], s,
                                     contours[(p.a, p.b)])
            if on_column:
                # plan view where feasible: F first, then the profile's
                # own reading, then the other fold direction
                domain[i] = ["F"] + ([lab, "V" if lab == "M" else "M"]
                                     if lab in ("M", "V") else ["M", "V"])
            elif lab in ("M", "V"):
                pleat_lab[i] = lab
            elif dense:
                # provisional: only its PRESENCE matters, so `probe` marks
                # this a pleat candidate. interleave.colour sets the value.
                pleat_lab[i] = "M"
            else:
                labels[i] = lab
        # ridge and hinge pieces fall through deliberately: labels[i] stays
        # None, meaning "free variable, no seed". Stated rather than left as
        # an absence, because that is what a reader trips on.
    probe = [pleat_lab[i] if i in pleat_lab else labels[i]
             for i in range(len(pieces))]
    return labels, domain, pleat_lab, probe
```

Three tidyings are included, all byte-preserving and all named as permitted by the plan's Global Constraints: `on_column` hoisted into the branch that reads it; `pleat_lab.get(i) or labels[i]` replaced by an explicit membership test (the `or` was correct only because every label is a non-empty string); and the ridge/hinge fall-through made explicit in a comment.

**Do not** touch the centre-column domain order or `label_from_profile`.

- [ ] **Step 4: Run them to verify they pass**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python3 -m pytest tests/test_box_pleat_assign.py -v -m slow
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python3 -m pytest tests/test_box_pleat_assign.py -v
```

Expected: both green. The second run (no `-m slow`) must still pass every pre-existing test, which is the tidying's proof.

- [ ] **Step 5: Prove the tidying changed no bytes**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python3 -m pytest tests/test_box_pleat_e2e.py -k "byte_identical" -v
```

Expected: PASS. If this fails, a "tidying" changed behaviour — revert it rather than updating the expectation.

- [ ] **Step 6: Re-measure bipartiteness on the DENSE grouping**

Task 2 measured the sparse grouping, a lower bound. Now measure the real one. Edit `bipartite_probe.py`'s two grouping lines to:

```python
        _, _, _, probe = A.initial_readings(N, pieces, res.contours, prof,
                                            face_of, dense=True)
        groups = A.pleat_paths(pieces, probe, dense=True)
```

then:

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -u ../docs/superpowers/evidence/2026-09-24-dense-pleats/bipartite_probe.py ../docs/superpowers/evidence/2026-09-24-dense-pleats/bipartite-dense.json 2>&1 | tail -20
```

Same stopping rule as Task 2 Step 3: **any `bipartite=False` halts the plan and escalates.** Keep both JSON files; the sparse-vs-dense comparison is evidence in its own right.

- [ ] **Step 7: Commit**

```bash
git add mcp_harness/box_pleat/assign.py mcp_harness/tests/test_box_pleat_assign.py docs/superpowers/evidence/2026-09-24-dense-pleats/
git commit -m "$(cat <<'MSG'
box_pleat: initial_readings stops pinning F in dense mode

One branch was pinning 81% of all pieces out of the search before it began:
an off-column piece whose elevation profile reads a monotone slope became a
fixed flat line. In dense mode it becomes a variable instead, so F.2 can give
it a fold. Measured: bird 10,456 pinned -> 0, free 1,078 -> 11,534.

Includes the three byte-preserving tidyings the spec names as permitted:
on_column hoisted into the only branch that reads it, the fragile
`pleat_lab.get(i) or labels[i]` made an explicit membership test, and the
ridge/hinge fall-through stated rather than left as an absence. The
byte-identity e2e test is what proves they changed nothing.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
MSG
)"
```

---

### Task 5: `colour` releases instead of failing

**Files:**
- Modify: `mcp_harness/box_pleat/interleave.py`
- Test: `mcp_harness/tests/test_box_pleat_interleave.py`

**Interfaces:**
- Produces, relied on by Task 6:
  - `colour(pieces, groups) -> tuple[dict[int, str], frozenset[int]]` — `(colours, released)`. Every group index is either a key of `colours` or a member of `released`, never both, never neither.
  - `colour_graph(adj) -> tuple[dict[int, str], frozenset[int]]` — same contract on a raw adjacency dict.
- **Removed:** `OddCycle`. Nothing can produce it once release is unconditional. Delete the dataclass and every test that expects it.

**Why.** Measured 2026-09-24: `bird` 963 paths / 1216 edges, `lizard` 365/482, `horse` 809/977, each with an odd cycle of length 5 and zero isolated nodes. Strict 2-colouring is impossible on this geometry. COrigami's answer is to trap a pleat and return it to the `unassigned_pleats` pool; this is that, triggered where our pipeline discovers the conflict.

- [ ] **Step 1: Write the failing tests**

Replace the odd-cycle tests in `mcp_harness/tests/test_box_pleat_interleave.py` with:

```python
def test_colour_releases_one_endpoint_of_an_odd_cycle():
    """A triangle cannot alternate. Exactly one of its three nodes is
    released; the remaining two are coloured and differ."""
    adj = {0: {1, 2}, 1: {0, 2}, 2: {0, 1}}
    col, released = interleave.colour_graph(adj)
    assert len(released) == 1, released
    kept = sorted(set(adj) - released)
    assert len(kept) == 2                              # non-vacuity
    assert col[kept[0]] != col[kept[1]]
    assert set(col) == set(adj) - released             # partition, no overlap


def test_colour_releases_nothing_on_a_bipartite_graph():
    adj = {0: {1}, 1: {0, 2}, 2: {1}}
    col, released = interleave.colour_graph(adj)
    assert released == frozenset()
    assert len(col) == 3                               # non-vacuity
    assert col[0] != col[1] and col[1] != col[2]


def test_every_group_is_either_coloured_or_released():
    """The partition invariant, on a graph with two odd cycles and an
    isolated node, so the assertion is not carried by a trivial case."""
    adj = {0: {1, 2}, 1: {0, 2}, 2: {0, 1},
           3: {4, 5}, 4: {3, 5}, 5: {3, 4},
           6: set()}
    col, released = interleave.colour_graph(adj)
    assert len(released) == 2                          # one per triangle
    assert set(col) | released == set(adj)
    assert not (set(col) & released)
    assert 6 in col                                    # isolated still coloured


def test_the_remainder_after_release_really_is_properly_two_coloured():
    """The point of releasing: every surviving EDGE joins different colours.
    Asserting the release count alone would not show that."""
    adj = {0: {1, 2}, 1: {0, 2}, 2: {0, 1, 3}, 3: {2}}
    col, released = interleave.colour_graph(adj)
    edges = [(u, v) for u in adj for v in adj[u] if u < v]
    assert edges                                        # non-vacuity
    live = [(u, v) for u, v in edges
            if u not in released and v not in released]
    assert live                                         # non-vacuity
    assert all(col[u] != col[v] for u, v in live)


@pytest.mark.slow
def test_release_count_on_a_real_subject_is_a_small_fraction():
    """bird is NOT bipartite, so release must be non-zero -- and the whole
    approach is only worth shipping if it is a small minority."""
    pieces, groups = _real_dense_groups("bird")
    col, released = interleave.colour(pieces, groups)
    assert len(groups) > 500                            # non-vacuity
    assert released                                     # bird is not bipartite
    assert len(col) + len(released) == len(groups)
    assert len(released) / len(groups) < 0.25, len(released)
```

Add the helper the last test uses, beside the existing real-subject helper in that file:

```python
def _real_dense_groups(subject):
    """Compile `subject` and return (pieces, dense pleat-path groups)."""
    import json
    from box_pleat import assign as A
    from box_pleat.compile import compile_tree
    entries = {e["subject"]: e for e in json.load(open(
        "../docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/data/rule6_serve.json"))}
    e = entries[subject]
    res = compile_tree(e["requested"], e["pairs"])
    assert res.stage_reached == "emit", res.stage_reached
    N, pieces = res.layout.N, res.assignment.pieces
    fl = A.faces(N, pieces)
    prof, face_of = A.profiles(N, pieces, res.contours, fl)
    _, _, _, probe = A.initial_readings(N, pieces, res.contours, prof, face_of,
                                        dense=True)
    return pieces, A.pleat_paths(pieces, probe, dense=True)
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python3 -m pytest tests/test_box_pleat_interleave.py -v
```

Expected: the new tests fail because `colour_graph` still returns `(colours|None, OddCycle|None)` — unpacking gives an `OddCycle` where a `frozenset` is expected. Report exactly what you see.

- [ ] **Step 3: Implement**

In `mcp_harness/box_pleat/interleave.py`, delete the `OddCycle` dataclass and the `_cycle` helper (nothing consumes them once release is unconditional), and rewrite `colour_graph`:

```python
def colour_graph(adj: dict) -> tuple:
    """2-colour `adj`, releasing a node from every odd cycle.

    Returns `(colours, released)`. Every key of `adj` appears in exactly one
    of them. A released node carries no F.2 colour: it goes back to the
    solver's variable pool with the ordinary ["M", "V"] domain, which is this
    pipeline's form of COrigami's `unassigned_pleats`.

    Release is GREEDY -- the node whose edge closes the odd cycle is the one
    released. A MINIMUM odd-cycle transversal would give up less of F.2 but
    is NP-hard; the release count (see the evidence table) is what says
    whether greedy is good enough. Do not replace this with a heuristic that
    merely LOOKS better without measuring it.

    Roots are taken in ascending key order and every root takes "M", so the
    result never depends on dict iteration order.
    """
    colour: dict = {}
    released: set = set()
    for root in sorted(adj):
        if root in colour or root in released:
            continue
        colour[root] = "M"
        q = deque([root])
        while q:
            u = q.popleft()
            if u in released:
                continue
            for v in sorted(adj[u]):
                if v in released:
                    continue
                if v not in colour:
                    colour[v] = FLIP[colour[u]]
                    q.append(v)
                elif colour[v] == colour[u]:
                    # odd cycle: release the node that closed it
                    released.add(v)
                    colour.pop(v, None)
    return colour, frozenset(released)
```

Update `colour` to match — it keeps its rank/order remapping and returns `({order[r]: c}, frozenset(order[r] for r in released))`:

```python
def colour(pieces, groups) -> tuple:
    """F.2 end to end: order the paths, build adjacency, 2-colour, release.

    Returns `(colours_by_group_index, released_group_indices)`.
    """
    order = sorted(range(len(groups)),
                   key=lambda gi: origin_key(pieces, groups[gi]))
    rank = {gi: r for r, gi in enumerate(order)}
    adj = adjacency(pieces, groups)
    radj = {rank[gi]: {rank[gj] for gj in nb} for gi, nb in adj.items()}
    col, released = colour_graph(radj)
    return ({order[r]: c for r, c in col.items()},
            frozenset(order[r] for r in released))
```

Also update the module docstring: it currently says an odd cycle is "a genuine refutation" the function reports rather than guessing past. That was true under approach A and is now wrong. It must say that odd cycles are expected on real geometry (measured: bird, lizard and horse all carry length-5 cycles), and that the response is release, not refusal.

- [ ] **Step 4: Run to verify they pass**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python3 -m pytest tests/test_box_pleat_interleave.py -v
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python3 -m pytest tests/test_box_pleat_interleave.py -v -m slow
```

Expected: both green. **Report bird's actual release count and fraction** — it is the number this whole approach is judged on, and Task 8 records it.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/box_pleat/interleave.py mcp_harness/tests/test_box_pleat_interleave.py
git commit -m "$(cat <<'MSG'
box_pleat: colour() releases an odd cycle's node instead of failing

Strict 2-colouring is impossible on this geometry -- bird, lizard and horse
each carry an odd cycle of length 5 on a dense, fully connected adjacency
graph. COrigami's answer is to trap a pleat and return it to the
unassigned_pleats pool; this is that. A released path carries no F.2 colour
and goes back to the solver with the ordinary ["M","V"] domain.

Release is greedy by owner ruling. Minimum odd-cycle transversal is NP-hard
and deliberately not attempted; the release count is the evidence for
whether greedy is good enough.

OddCycle and _cycle are deleted -- nothing can produce them now.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
MSG
)"
```

---

### Task 6: Wire colours and releases into `assign`

**Files:**
- Modify: `mcp_harness/box_pleat/assign.py` (`assign` signature, the variable-setup block, the no-good clause filter)
- Test: `mcp_harness/tests/test_box_pleat_assign.py`

**Interfaces:**
- Consumes: `interleave.colour` (Task 5), `pleat_paths(..., dense=True)`, `initial_readings(..., dense=True)`.
- Produces, relied on by Task 7:
  - `assign(layout, ridges, boundary_ridges, contours, *, budget=500_000, global_check=None, layer_checks=200, dense=False)`
  - `Assignment.pleat_vars: frozenset` — solver variables whose value F.2 **fixed**. Released paths are NOT members.
  - `Assignment.released_vars: frozenset` — solver variables released from an odd cycle. Empty in sparse mode.

**The two-domain rule.** A **coloured** path's variable gets a one-element domain `[f2_colour]` — F.2 is fixed for it. A **released** path's variable gets the ordinary two-element domain `["M", "V"]` — the solver decides. That difference is the whole of approach C.

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_box_pleat_assign.py`:

```python
@pytest.mark.slow
def test_dense_assign_fixes_coloured_paths_and_frees_released_ones():
    import json
    from box_pleat.assign import assign, Assignment, AssignFail
    from box_pleat.compile import compile_tree
    entries = {e["subject"]: e for e in json.load(open(
        "../docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/data/rule6_serve.json"))}
    e = entries["lizard"]
    res = compile_tree(e["requested"], e["pairs"])
    out = assign(res.layout, res.ridges, res.boundary_ridges, res.contours,
                 dense=True)
    assert not isinstance(out, AssignFail), out
    assert isinstance(out, Assignment)
    assert out.pleat_vars                               # non-vacuity
    assert not (out.pleat_vars & out.released_vars)     # disjoint by construction
    fixed = [out.labels[i] for i, _ in enumerate(out.pieces)
             if i in out.pleat_vars]
    assert fixed and set(fixed) <= {"M", "V"}


@pytest.mark.slow
def test_dense_assign_emits_far_more_creases_than_sparse():
    """The point of the whole change, as a number."""
    import json
    from box_pleat.assign import assign
    from box_pleat.compile import compile_tree
    entries = {e["subject"]: e for e in json.load(open(
        "../docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/data/rule6_serve.json"))}
    e = entries["lizard"]
    res = compile_tree(e["requested"], e["pairs"])
    sparse_mv = sum(1 for l in res.assignment.labels if l in ("M", "V"))
    dense = assign(res.layout, res.ridges, res.boundary_ridges, res.contours,
                   dense=True)
    dense_mv = sum(1 for l in dense.labels if l in ("M", "V"))
    assert sparse_mv == 476                             # today's measured value
    assert dense_mv > sparse_mv * 5


def test_sparse_assign_records_no_pleat_or_released_vars():
    """Both fields are dense-mode concepts; sparse must leave them empty so
    the precedence filter in Step 3 can never fire on a sparse run."""
    from box_pleat.assign import Assignment
    a = Assignment([], [])
    assert a.pleat_vars == frozenset()
    assert a.released_vars == frozenset()
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python3 -m pytest tests/test_box_pleat_assign.py -k "dense_assign or released" -v -m slow
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python3 -m pytest tests/test_box_pleat_assign.py -k "released" -v
```

Expected: `TypeError: assign() got an unexpected keyword argument 'dense'` on the two slow tests, and `TypeError: __init__() ... 'released_vars'` or an `AttributeError` on the fast one.

- [ ] **Step 3: Implement**

In `mcp_harness/box_pleat/assign.py`:

1. Add the import at module top: `from . import interleave`

2. Extend `Assignment`:

```python
@dataclass
class Assignment:
    pieces: list
    labels: list
    # Solver variables whose value F.2 FIXED (dense mode only). The layers
    # stage may not relabel these: spec 2026-09-24 section 6.
    pleat_vars: frozenset = frozenset()
    # Solver variables RELEASED from an odd cycle (dense mode only). F.2 has
    # no opinion about these -- releasing one is precisely that statement --
    # so the layers stage MAY relabel them. Spec section 5.2.
    released_vars: frozenset = frozenset()
```

3. Add `dense: bool = False` to `assign`'s keyword-only parameters, and replace the variable-setup block:

```python
    labels, domain, pleat_lab, probe = initial_readings(
        N, pieces, contours, prof, face_of, dense=dense)

    # Pleat paths become variables. Sparse: the profile reading first (so the
    # first candidate is exactly what v1 emitted), the flip second. Dense:
    # COrigami F.2's colour as a ONE-ELEMENT domain for a coloured path, and
    # the ordinary two-element domain for a RELEASED one -- which is this
    # pipeline's form of the `unassigned_pleats` pool (spec section 5).
    groups = pleat_paths(pieces, probe, dense=dense)
    f2_colour, f2_released = ({}, frozenset())
    if dense:
        f2_colour, f2_released = interleave.colour(pieces, groups)

    pleat_pref: dict = {}
    pleat_of: dict = {}
    fixed_reps: set = set()
    released_reps: set = set()
    for gi, group in enumerate(groups):
        members = [i for i in group if i in pleat_lab]
        if not members:
            continue
        rep = min(members)
        if dense and gi in f2_colour:
            pleat_pref[rep] = [f2_colour[gi]]
            fixed_reps.add(rep)
        elif dense:
            lab = pleat_lab[rep]
            pleat_pref[rep] = [lab, "V" if lab == "M" else "M"]
            released_reps.add(rep)
        else:
            lab = pleat_lab[rep]
            pleat_pref[rep] = [lab, "V" if lab == "M" else "M"]
        for i in members:
            pleat_of[i] = rep
```

4. Enforce the precedence carve-out at the no-good clause site (around `assign.py:752`), where a rejection's keys are resolved into a clause:

```python
            clause = {var_of[idx[k]]: value[var_of[idx[k]]]
                      for k in keys
                      if k in idx and idx[k] in var_of
                      # Spec section 6 + 5.2: F.2's COLOURED pleats outrank
                      # CEGAR -- a no-good over a one-element domain could
                      # never be satisfied, so the search would grind to
                      # unsat. RELEASED pleats are not F.2's to own and are
                      # deliberately left available to the search.
                      and not (dense and var_of[idx[k]] in fixed_reps)}
```

If the filtered clause is empty, the rejection implicated nothing the search may act on: accept the candidate rather than looping, since re-offering an identical candidate spins until the budget expires. Its verdict is recorded either way.

5. Where `assign` returns its `Assignment`, carry both sets:

```python
        return Assignment(pieces, out,
                          frozenset(fixed_reps) if dense else frozenset(),
                          frozenset(released_reps) if dense else frozenset())
```

- [ ] **Step 4: Run to verify they pass**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python3 -m pytest tests/test_box_pleat_assign.py -v
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python3 -m pytest tests/test_box_pleat_assign.py -v -m slow
```

- [ ] **Step 5: Prove sparse mode still emits identical bytes**

**This guard was skipped in Task 4 and is now overdue — it covers both tasks.**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python3 -m pytest tests/test_box_pleat_e2e.py -k "byte_identical" -v
```

Expected: PASS. If it fails, sparse behaviour moved — revert the offending change rather than updating the expectation. Report the result explicitly either way; do not mark this task DONE without it.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/box_pleat/assign.py mcp_harness/tests/test_box_pleat_assign.py
git commit -m "$(cat <<'MSG'
box_pleat: coloured pleats get one value, released pleats get two

Approach C in one line: a coloured path's variable has a one-element domain
so F.2 is fixed for it, and a released path's has the ordinary two, so the
solver decides. Assignment carries both sets.

The CEGAR precedence filter applies to COLOURED paths only. A no-good over a
one-element domain could never be satisfied and would grind the search to
unsat; a released path is not F.2's to own, so it stays available.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
MSG
)"
```

---

### Task 7: `compile_tree(dense=...)` and compute-and-report certification

**Files:**
- Modify: `mcp_harness/box_pleat/compile.py`
- Test: `mcp_harness/tests/test_box_pleat_layers.py`

**Interfaces:**
- Consumes: `assign(..., dense=)` (Task 6).
- Produces, relied on by Task 8: `compile_tree(nodes, pairs, *, max_N=None, pack_budget=200_000, assign_budget=500_000, layer_budget=200, certify_budget=..., dense=False)`, with `Result.verdict` populated in both modes and `Result.stage_reached == "emit"` in dense mode **regardless of verdict**.

**The ruling this implements.** Spec section 7: dense mode computes the certification verdict, records it, and emits anyway. Sparse mode's refusal is untouched. The bypass is a named parameter, not a relaxed check.

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_box_pleat_layers.py`:

```python
@pytest.mark.slow
def test_dense_compile_emits_even_when_not_certified():
    import json
    from box_pleat.compile import compile_tree
    entries = {e["subject"]: e for e in json.load(open(
        "../docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/data/rule6_serve.json"))}
    e = entries["lizard"]
    res = compile_tree(e["requested"], e["pairs"], dense=True)
    assert res.stage_reached == "emit"
    assert res.fold is not None
    assert res.verdict is not None                    # computed, not skipped
    assert res.verdict.kind in ("CERTIFIED", "REFUTED", "UNDECIDED")


@pytest.mark.slow
def test_sparse_compile_still_refuses_an_uncertified_base(monkeypatch):
    """The guarantee merged in PR #193, asserted BEHAVIOURALLY.

    Forcing certify to return a non-CERTIFIED verdict is the only way to
    reach the refusal, because no current subject genuinely fails it.
    Asserting on compile.py's source text would pin wording, not behaviour.
    """
    import json
    import box_pleat.compile as C
    import box_pleat.layers as L
    from box_pleat.compile import LayerFail
    from layer_certify import Verdict

    entries = {e["subject"]: e for e in json.load(open(
        "../docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/data/rule6_serve.json"))}
    e = entries["lizard"]
    stub = Verdict(kind="UNDECIDED", violation=None, nodes=0, free=0)
    monkeypatch.setattr(L, "certify", lambda *a, **k: stub)

    sparse = C.compile_tree(e["requested"], e["pairs"])
    assert sparse.stage_reached == "layers"
    assert isinstance(sparse.failure, LayerFail)
    assert sparse.failure.kind == "uncertified"
    assert sparse.fold is None

    dense = C.compile_tree(e["requested"], e["pairs"], dense=True)
    assert dense.stage_reached == "emit"              # same verdict, emits anyway
    assert dense.fold is not None
    assert dense.verdict.kind == "UNDECIDED"          # recorded, not hidden
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python3 -m pytest tests/test_box_pleat_layers.py -k dense -v -m slow
```

Expected: `TypeError: compile_tree() got an unexpected keyword argument 'dense'`.

- [ ] **Step 3: Implement**

In `mcp_harness/box_pleat/compile.py`:

1. Add `dense: bool = False` to `compile_tree`'s keyword-only parameters.
2. Pass it through: `assign(lay, ridges, boundary_ridges, contours, budget=assign_budget, global_check=_check, layer_checks=layer_budget, dense=dense)`.
3. Change the certification tail so dense mode reports rather than refuses:

```python
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

**Do not** delete or weaken the `LayerFail("uncertified", ...)` branch. It must be reached exactly as before whenever `dense=False`.

- [ ] **Step 4: Run to verify they pass**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python3 -m pytest tests/test_box_pleat_layers.py -v -m slow
```

- [ ] **Step 5: Run the full fast suite**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python3 -m pytest tests/ -q --timeout=900 2>&1 | tail -20
```

Expected: the pre-existing count (222 as of PR #193) plus this plan's new fast tests, zero failures. Record the exact number.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/box_pleat/compile.py mcp_harness/tests/test_box_pleat_layers.py
git commit -m "$(cat <<'MSG'
box_pleat: compile_tree(dense=), report the verdict, do not refuse

Spec section 7: dense mode computes the certification verdict, records it,
and emits regardless. Sparse mode's LayerFail("uncertified") refusal is
untouched and still reached whenever dense=False. The bypass is a named
parameter, not a relaxed check.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
MSG
)"
```

---

### Task 8: Establish byte-identity, measure the labelling, write up the negative

> ⚠ **WARNING, added 2026-09-27: this task's reference figures were REFUTED by
> the diagnostic it asked for. Everything below is left visible as written; do
> not cite its numbers.** The wrong figures are in Step 2 ("38 distinct
> witnesses of 113 rejections; top witness 15×"), in Step 3 item 4 ("38 distinct
> contradictions, and the conclusion that no budget converges it"), in Step 3
> item 5 ("That this bounds the shipped pleat-reassignment feature"), and in
> Step 4's commit-message template ("the loop is measurably not learning ...
> only 38 distinct contradictions"). The corrections:
>
> | claim as planned | as measured |
> |---|---|
> | 38 distinct contradictions of 113 | **113 distinct of 113** |
> | top witness repeated 15× | **1×** — nothing recurs |
> | "the loop is measurably not learning" | the loop **is** learning; every rejection is new |
> | "no budget converges it" | **WITHDRAWN** — no budget run can prove impossibility |
> | "this bounds the shipped pleat-reassignment feature" | **RETRACTED** — inference presented as a finding |
> | Step 3 item 4's "880 s" for the 113 rejections | **834.0 s** (`elapsed_secs`) — a rounded pre-figure, not a measurement |
>
> Source: the committed `nogood-lizard.json` (`partial: false`) — `rejections`
> 113, `distinct_witnesses` 113, `top_witness_count` 1, `clause_size_median`
> 2069, `var_clause_size_median` 202.
>
> Step 4's "median no-good implicates 42% of the pattern" is **not** in the
> refuted set, but it is only checkable in one unit: 2,069 creases of `lizard`'s
> 4,868 dense M/V pieces is 42.5% (`clause_size_median` / `dense_mv`, both
> committed). The same fraction at **solver-variable** level cannot be checked —
> no committed artifact records the total number of solver variables, only the
> clause's 202. This branch has already been burned once by quoting a clause size
> in the wrong unit, so say which unit you mean; the README reports both side by
> side for that reason.
>
> **Mechanism of the error, because it is the reusable lesson.** The "38
> distinct / 15×" figures came from a throwaway probe that identified a witness
> by a **40-character truncated slice of its `repr`**
> (`w[w.find("faces="):w.find("faces=")+40]`), which ends mid-string — so
> distinct contradictions that happened to share a face triple collided into one
> bucket. The committed diagnostic hashes the full frozen `Witness` dataclass
> instead, and reads no repetition at all. Every conclusion that rested on the
> repetition fell with it, including the "no budget converges it" claim this
> task instructed the README to draw. A later 10x-budget run (5,000,000 nodes)
> refused 584 distinct candidates of 584 and still did not converge — which
> makes convergence-by-budget *economically implausible* but still does not
> prove impossibility.
>
> The spec was corrected for these in commit `92a5147`; this plan was not, until
> now. Read
> `docs/superpowers/evidence/2026-09-24-dense-pleats/README.md` (§4 and its
> "An earlier revision of this section was wrong, twice") for what was actually
> measured and shipped.

**Files:**
- Create: `docs/superpowers/evidence/2026-09-24-dense-pleats/dump_folds.py`
- Create: `docs/superpowers/evidence/2026-09-24-dense-pleats/dense_labelling.py`
- Create (generated): `dense_labelling.json`
- Modify: `docs/superpowers/evidence/2026-09-24-dense-pleats/README.md`

**Scope changed 2026-09-25.** The original Task 8 built a cost curve and a dense-vs-sparse gallery. Neither is reachable: `compile_tree(dense=True)` does not reach `emit`, so there is no dense fold to time a layer pipeline over and no dense crease pattern to render. The owner chose to write up the measured negative rather than emit patterns carrying proven layer contradictions. What remains is the part that IS establishable, and it is the more load-bearing half.

- [ ] **Step 0: Establish byte-identity across ALL 8 subjects**

This is the guarantee behind the plan's central claim that the change is additive. The e2e test covers only `bird` and `starfish` — the two subjects that accept the first candidate and never enter the CEGAR loop this plan modified.

Create `dump_folds.py`, which for each of the 8 emitting subjects calls `compile_tree(entry["requested"], entry["pairs"])` with **no `dense` argument** and writes `json.dumps(res.fold, sort_keys=True)` to `<outdir>/<subject>.json`. Subjects: `starfish bird lizard horse octopus frog guinea_pig dog`.

Dump the branch base without moving HEAD. **Never `git stash`, never `git checkout`:**

```bash
mkdir -p /tmp/bp-base && git archive a7bb00d | tar -x -C /tmp/bp-base
cd /tmp/bp-base/mcp_harness && PYTHONPATH=. <this worktree>/.venv/bin/python3 -u <script> /tmp/bp-old
cd <this worktree>/mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -u <script> /tmp/bp-new
for s in starfish bird lizard horse octopus frog guinea_pig dog; do
  a=$(shasum -a 256 < /tmp/bp-old/$s.json | cut -d' ' -f1)
  b=$(shasum -a 256 < /tmp/bp-new/$s.json | cut -d' ' -f1)
  [ "$a" = "$b" ] && echo "IDENTICAL $s" || echo "DIFFERS   $s"
done
```

Expected: `IDENTICAL` on all 8. **Any `DIFFERS` is Critical — stop and report; do not adjust an expectation to match.** Record the shared sha256 per subject in the README.

Budget ~35 minutes for the two sparse passes (`dog` ~578 s and `guinea_pig` ~295 s dominate each side).

- [ ] **Step 1: Measure the dense labelling on all 8 subjects**

Create `dense_labelling.py`. For each subject: compile sparsely to get the layout, then call `assign(..., dense=True, global_check=None)` — which returns the first locally feasible candidate and is the stage that WORKS. Record per subject: `N`, total pieces, sparse M/V count, dense M/V count, pleat paths, coloured, released-by-odd-cycle, released-by-conflict, flipped-from-F.2 (expected 0 here, since `global_check=None` runs no repair loop), assign seconds, and the crease-degree histogram over interior vertices in both modes.

Write `dense_labelling.json` incrementally. Expect a few minutes total — the sparse compiles dominate, the dense assign is under a second each.

- [ ] **Step 2: Confirm the negative is not lizard-specific**

The no-good diagnostic has one data point. Run it on **`bird`** for a second. Wrap production's own `global_check` in a spy that records, per rejection, the number of implicated creases and the witness identity, then report: clause size min/median/max, distinct witnesses over total rejections, and the most-repeated witness count.

Reference figures from `lizard`: clause size min 39 / median 2,069 / max 3,161; 38 distinct witnesses of 113 rejections; top witness 15×.

Budget ~20 minutes and a hard cap. If `bird` behaves differently from `lizard`, that is a finding — report it rather than assuming the lizard reading generalises.

- [ ] **Step 3: Write the README**

Rewrite `docs/superpowers/evidence/2026-09-24-dense-pleats/README.md`, with no placeholder text, covering:

1. **What ships**: dense labelling behind `dense=False`, inert by default.
2. **The byte-identity guarantee** from Step 0, with the per-subject sha256, and the explicit note that the e2e test alone covers only 2 of 8 and why those 2 are the uninformative ones.
3. **The labelling measurements** from Step 1.
4. **The negative**, from Step 2 and the committed lizard figures: 113 candidates refused, 880 s, clause size median 2,069 of ~4,868 creases, 38 distinct contradictions, and the conclusion that no budget converges it.
5. **That this bounds the shipped pleat-reassignment feature** — its own clause size was 125 of 249 variables, the same ~50% weakness, surviving only because sparse subjects need 5–22 candidates.
6. **The three superseded adjacency definitions** and the measurement that refuted each: proximity → odd cycles of length exactly 3; facing-at-1 → an empty graph (`bird` edges=0, isolated=76), a vacuous bipartite pass; nearest-neighbour → the shipped one.
7. **"What this does NOT establish"**: (a) the conflict count is "conflicts among coloured-only merges" — a mixed variable's coloured disagreement is not recorded, measured at 0 cases on all three subjects; (b) greedy release is not a minimum odd-cycle transversal, so release counts are an upper bound; (c) no dense fold was ever emitted, so nothing here measures the layer pipeline's cost at dense scale beyond the per-candidate figures; (d) the negative is measured on `lizard` and `bird` only.
8. **Regenerate commands** for all three scripts.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/evidence/2026-09-24-dense-pleats/
git commit -m "$(cat <<'MSG'
evidence: dense labelling works, dense layer-consistency does not

Byte-identity established across all 8 subjects by dumping folds from the
branch base via git archive and comparing sha256 -- the e2e test covers only
bird and starfish, which accept the first candidate and never enter the
CEGAR loop this plan modified.

The labelling stage works: 4,868 M/V pieces on lizard in 0.76s, every
interior vertex passing Maekawa, Kawasaki and the arrangement oracle. Global
layer consistency does not: 113 candidates refused, and the loop is measurably
not learning -- median no-good implicates 42% of the pattern, and only 38
distinct contradictions appear across 113 rejections.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
MSG
)"
```

---

## Plan self-review (updated 2026-09-24 after the gate fired)

**1. Spec coverage.**

| spec section | task |
|---|---|
| §4 component 2 (`interleave.py`) | Task 1 |
| §4 component 3 (`initial_readings`) | Task 4 |
| §4 component 1 (`pleat_grid.py`) | **deliberately out of scope** — own plan, per spec §8 |
| §5 approach C, greedy release | Task 5 |
| §5.2 released paths exempt from the CEGAR carve-out | Task 6 step 3 item 4 |
| §5.3 release count as headline measurement | Task 5 step 4, Task 8 |
| §6 F.2 outranks CEGAR (coloured paths only) | Task 6 step 3 item 4 |
| §7 compute-and-report | Task 7 step 3 item 3 |
| §9 byte-identity | **Task 6 step 5** — overdue, it was skipped in Task 4 |
| §9 non-vacuity pairing | every test in Tasks 1, 3, 4, 5, 6, 7 |
| §10 evidence + gallery | Task 8 |
| §11 risk 2 (`flat_fold` before certify) | Task 8 step 1, timed separately |
| §11 risk 3 (`AREA_EPS`) | Task 8 step 5 README |

**Changes forced by the gate.** Approach A's single-value domain is gone; Tasks 5–8 are rewritten around trap-and-release. `OddCycle` and `AssignFail("f2_odd_cycle", ...)` are **deleted** rather than kept — with release unconditional, nothing can produce them, and a type with no producer is exactly the YAGNI violation this plan's own self-review flagged in its first version.

**Outstanding debt carried into Task 6.** The byte-identity guard (spec §9) was skipped by Task 4's implementer when the gate fired. It is the load-bearing regression test for the entire "additive, behind a flag" claim, and Task 6 Step 5 must not be marked DONE without it.

**Deferred minor findings for the final whole-branch review.** F5: an odd cycle was theoretically reachable from a single lane if one path re-entered it — measured at 0 of 216 lanes on `bird`, so not the cause of the real cycles, but still untested. F9: the interleave test file's docstring claims "every fixture built by hand" while reaching another wave's `rule6_serve.json` at module scope, so it errors rather than skips if that file is ever pruned.

**2. Placeholder scan.** No "TBD", "TODO", "handle edge cases" or "similar to Task N". Task 8 step 3 names the exact file to adapt, the exact two changes, and the exact function to keep verbatim — a reference to committed code, not a placeholder.

**3. Type consistency.** `colour` and `colour_graph` both return `(dict, frozenset)` in Tasks 5, 6 and 8. `pleat_vars` and `released_vars` are `frozenset` in the `Assignment` definition (Task 6), constructed from `fixed_reps` / `released_reps`, consumed as membership tests and lengths in Tasks 6 and 8, and asserted disjoint. `dense` is keyword-only with default `False` in `pleat_paths`, `initial_readings`, `assign` and `compile_tree`.
