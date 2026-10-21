# Box-Pleating Compiler (Subproject A) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Compile each of the 17 committed VLM-authored metric trees into a box-pleated, mirror-symmetric uniaxial base as a `.fold`, validate it with the existing validators, and tabulate grid, scale, coverage and lint next to the TreeMaker serve-path numbers.

**Architecture:** A new pure-Python package `mcp_harness/box_pleat/` implements Lang *Origami Design Secrets* Ch. 13 — polygon packing on an integer grid (half-square + mirror, COrigami-shaped backtracking), straight-skeleton ridges (mirrored across the paper edge for boundary-tipped flaps), densely traced bouncing contours, nearest-neighbour elevation labels plus a Maekawa CSP for ridges and hinges — and emits FOLD. `Layout` (hinge polygons + rivers on the grid) is the data model that subproject B's technique macros will mutate. A probe script runs all 17 trees through both compilers and writes an evidence directory.

**Tech Stack:** Python 3.14 (main-repo venv), `fractions.Fraction`, pytest; existing validators `cp_audit.audit_fold`, `flat_fold.flat_fold`, `layer_order.layer_order`, `linter_server.validate_flat_foldability` + `lint_verdict.parse_verdict`, `paper_coverage.hull_coverage`; TreeMaker side via `server.draft_and_compile_full_base` + `server.read_base`. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-09-20-box-pleat-compiler-design.md` — read it first, **including §10 (amendments)**, which overrides §2.4, §5.3, §5.4 and §5.5 where they differ.

## Global Constraints

- **No new third-party dependencies.** Standard library + numpy (already present) only.
- **Grid unit = the tree's native quantization.** Any edge length that is not an integer multiple of the detected unit (relative tolerance `2e-3`, divisors 1..12 tried) is refused with `NonIntegral(edge, length, unit)`. Never round silently (spec §2.3, §5.1).
- **Half-square + mirror.** Paired leaves are placed in the left half and mirrored; axial (unpaired) leaves have their tip on the centre column `N/2`. Paired polygons may meet across the centre column (spec §10.2). Contour pieces on the centre column are `F` (plan view where possible).
- **`N` is always even.** `N_lb = max(diameter, ceil(sqrt(area)))` rounded up to even; sweep `N += 2` up to `2·N_lb` (spec §5.1, §5.2).
- **Rule 4: every cell belongs to exactly one hinge polygon or river** after gap fill (spec §4 "Partition").
- **Rivers never grow; polys only grow** (spec §5.2 step 3). v1 invents no stubs.
- **Ridges:** straight skeleton of the polygon mirrored across every raw-edge line containing its tip, restricted to the paper (spec §10.1); rivers get bend diagonals only; every skeleton vertex must land on the half-grid, else `SkeletonFail`.
- **Contours are traced densely** (spec §10.3): tip launches and raw-edge axials at elevation 0, then perpendicular launches from every interior half-grid point of every axially-touched run at elevation `min|P−a|/2`, to a fixpoint. Two different elevations on one segment = `ContourFail("collision")`.
- **M/V (white side up, spec §10.3):** a contour piece that is a minimum in its face profile → `M` (elevation 0 always `M`), a maximum → `V`, a slope → `F`; centre column → `F`; boundary → `B`; ridges + hinges by an exact Maekawa CSP with mirrored pieces sharing one variable. Kawasaki asserted. Global layer order is **reported, never required** (spec §6).
- **Typed failures, never exceptions out of `compile_tree`** for a well-formed tree: `NonIntegral`, `PackFail`, `SkeletonFail`, `ContourFail`, `AssignFail` (spec §5.7, §6).
- **Determinism:** identical input → byte-identical `.fold` (sorted vertices/edges; no randomness).
- **Existing validators are reused unchanged.** `server.py`, `cp_audit.py`, `flat_fold.py`, `layer_order.py`, `lint_verdict.py`, `linter_server.py`, `paper_coverage.py` are NOT modified.
- **Never use tardigrade / water bear as a test subject** (owner instruction).
- **Unit tests never start the JVM or spawn a TreeMaker compile.** Only `test_box_pleat_e2e.py` touches the linter and that test is marked `@pytest.mark.slow`.
- **The pre-registered bar (spec §6) is never loosened to make a test pass.** A subject that fails is recorded with its stage and failure kind.
- Commit messages end with `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

## How to run tests

All commands from the worktree root `<repo>`. The worktree's `.venv`, `mcp_harness/.venv`, `.env`, `mcp_harness/oriedita/oriedita-1.1.3.jar`, `mcp_harness/OrieditaValidator.class` and `mcp_harness/headless_treemaker.cpython-314-darwin.so` are symlinks to the main checkout (already created; see memory `worktree-missing-build-artifacts`). If any is missing:

```bash
M=<repo>
ln -sfn $M/.venv .venv; ln -sfn $M/mcp_harness/.venv mcp_harness/.venv; ln -sfn $M/.env .env
mkdir -p mcp_harness/oriedita
ln -sfn $M/mcp_harness/oriedita/oriedita-1.1.3.jar mcp_harness/oriedita/oriedita-1.1.3.jar
ln -sfn $M/mcp_harness/OrieditaValidator.class mcp_harness/OrieditaValidator.class
ln -sfn $M/mcp_harness/headless_treemaker.cpython-314-darwin.so mcp_harness/headless_treemaker.cpython-314-darwin.so
```

Run one test file:

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_box_pleat_tree.py -v
```

Run all box-pleat unit tests (fast, no JVM):

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_box_pleat_*.py -m "not slow" -q
```

Coordinate conventions used by every module (memorise these):

- **Cell** `(c, r)`: column `c` in `[0, N)`, row `r` in `[0, N)`, origin bottom-left.
- **Grid point** `(x, y)`: cell corner, `x, y` in `[0, N]`. Flap tips are grid points.
- **Half-grid point** `(X, Y)`: integers in `[0, 2N]`; grid point `(x, y)` is half-grid `(2x, 2y)`; the centre of cell `(c, r)` is `(2c+1, 2r+1)`. The centre column `c = N/2` is the line `X = N`.
- **Quarter units** appear only inside `skeleton.py` (`(4x, 4y)`), so the wavefront simulation stays integral.
- **Mirror**: cell `(c, r) → (N-1-c, r)`; point `(x, y) → (N-x, y)`; half-grid `(X, Y) → (2N-X, Y)`.
- **Directions** are unit steps `(dx, dy)`; an undirected ridge direction is normalised so its first non-zero component is positive: `(1,0)`, `(0,1)`, `(1,1)`, `(1,-1)`.
- **Elevation** is a `Fraction` in cells; a half-grid offset of `k` from an axial is elevation `k/2`.

---

### Task 1: `tree.py` — contract joints, detect the unit, compute the lower bound

**Files:**
- Create: `mcp_harness/box_pleat/__init__.py`
- Create: `mcp_harness/box_pleat/tree.py`
- Test: `mcp_harness/tests/test_box_pleat_tree.py`

**Interfaces:**
- Consumes: node dicts `{"id", "parent_id", "length"}` (the `describe_tree_format` schema) and `pairs: list[list[int]]`.
- Produces: `contract(nodes, pairs) -> Tree`; `Tree.leaves: tuple[Leaf]`, `Tree.branches: tuple[Branch]`, `Tree.hubs: tuple[int]`, `Tree.unit: float`, `Tree.path(i, j) -> int`, `Tree.diameter() -> int`, `Tree.n_lb() -> int`, `Tree.leaf(id) -> Leaf`, `Tree.placed_leaves() -> list[Leaf]` (axial leaves plus the lower-id member of each pair), `Leaf(id, hub, r, partner)`, `Branch(a, b, w)`, exception `NonIntegral(edge, length, unit)`.

- [ ] **Step 1: Write the failing tests**

```python
# mcp_harness/tests/test_box_pleat_tree.py
import json
import os
import pytest

from box_pleat.tree import contract, NonIntegral, Tree

HERE = os.path.dirname(__file__)
RULE6 = os.path.join(HERE, "..", "..", "docs", "superpowers", "evidence",
                     "2026-09-08-vlm-tree-authoring", "data", "rule6_serve.json")


def toy_nodes():
    # Lang Fig. 13.12-style toy: hub 0 with paired r=2 leaves and an axial
    # r=1 leaf; river w=1 to hub 1 with paired r=1 leaves.
    return [
        {"id": 0, "parent_id": None, "length": 0.0},
        {"id": 1, "parent_id": 0, "length": 1.0},
        {"id": 2, "parent_id": 0, "length": 2.0},
        {"id": 3, "parent_id": 0, "length": 2.0},
        {"id": 4, "parent_id": 0, "length": 1.0},
        {"id": 5, "parent_id": 1, "length": 1.0},
        {"id": 6, "parent_id": 1, "length": 1.0},
    ], [[2, 3], [5, 6]]


def test_toy_contracts_to_two_hubs_one_river():
    nodes, pairs = toy_nodes()
    t = contract(nodes, pairs)
    assert set(t.hubs) == {0, 1}
    assert len(t.branches) == 1 and t.branches[0].w == 1
    assert {l.id: l.r for l in t.leaves} == {2: 2, 3: 2, 4: 1, 5: 1, 6: 1}
    assert t.leaf(2).partner == 3 and t.leaf(4).partner is None
    assert t.unit == pytest.approx(1.0)
    assert t.path(2, 5) == 4 and t.path(2, 3) == 4 and t.path(4, 6) == 3
    assert t.diameter() == 4
    # area LB: radii 2,2,1,1 as corners (4+4+1+1) + 1 as edge (2) = 12 -> 4
    assert t.n_lb() == 4
    assert [l.id for l in t.placed_leaves()] == [2, 4, 5]


def test_joints_are_contracted_and_lengths_add():
    # leaf 3 hangs off a chain 0 -> 1 -> 2 -> 3 of lengths 0.5, 0.5, 1.0
    nodes = [
        {"id": 0, "parent_id": None, "length": 0.0},
        {"id": 1, "parent_id": 0, "length": 0.5},
        {"id": 2, "parent_id": 1, "length": 0.5},
        {"id": 3, "parent_id": 2, "length": 1.0},
        {"id": 4, "parent_id": 0, "length": 1.0},
        {"id": 5, "parent_id": 0, "length": 1.0},
    ]
    t = contract(nodes, [[4, 5]])
    assert t.leaf(3).r == 4 and t.leaf(3).hub == 0     # unit 0.5 -> 2.0 = 4 units
    assert t.unit == pytest.approx(0.5)


def test_committed_dog_matches_measured_units():
    d = json.load(open(RULE6))
    dog = next(e for e in d if e["subject"] == "dog")
    t = contract(dog["requested"], dog["pairs"])
    assert sorted(l.r for l in t.leaves) == [12, 15, 15, 17, 20, 20]
    assert [b.w for b in t.branches] == [8]
    assert t.unit == pytest.approx(2 / 45, rel=1e-3)


def test_non_integral_is_refused_naming_the_edge():
    nodes = [
        {"id": 0, "parent_id": None, "length": 0.0},
        {"id": 1, "parent_id": 0, "length": 1.0},
        {"id": 2, "parent_id": 0, "length": 1.0},
        {"id": 3, "parent_id": 0, "length": 2.3336},
    ]
    with pytest.raises(NonIntegral) as ei:
        contract(nodes, [])
    assert ei.value.edge == 3


def test_all_17_committed_trees_contract():
    d = json.load(open(RULE6))
    for e in d:
        t = contract(e["requested"], e["pairs"])
        assert 5 <= len(t.leaves) <= 11, e["subject"]
        assert t.n_lb() % 2 == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_box_pleat_tree.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'box_pleat'`

- [ ] **Step 3: Write the implementation**

```python
# mcp_harness/box_pleat/__init__.py
"""Box-pleating compiler (Lang, Origami Design Secrets 2e, Ch. 13).

Spec: docs/superpowers/specs/2026-09-20-box-pleat-compiler-design.md
"""
```

```python
# mcp_harness/box_pleat/tree.py
"""Contract a metric tree into box-pleating quantities (spec §5.1).

Joints (degree-2 nodes) only set path lengths, so they are contracted away.
What remains: hubs (degree >= 3), leaves with an integer radius r, branch
edges with an integer width w, all in one grid unit that every length is an
integer multiple of. Non-integral trees are REFUSED, never rounded.
"""
from __future__ import annotations

import math
from collections import defaultdict, deque
from dataclasses import dataclass

MAX_UNIT_DIVISOR = 12
REL_TOL = 2e-3


class NonIntegral(ValueError):
    def __init__(self, edge: int, length: float, unit: float):
        self.edge, self.length, self.unit = edge, length, unit
        super().__init__(
            f"edge to node {edge}: length {length!r} is not an integer "
            f"multiple of the unit {unit:.6g}")


@dataclass(frozen=True)
class Leaf:
    id: int
    hub: int
    r: int
    partner: int | None       # paired leaf id, None for an axial leaf


@dataclass(frozen=True)
class Branch:
    a: int
    b: int
    w: int


@dataclass(frozen=True)
class Tree:
    leaves: tuple
    branches: tuple
    hubs: tuple
    unit: float
    adj: dict                 # node -> {nbr: int units}

    def leaf(self, i: int) -> Leaf:
        for l in self.leaves:
            if l.id == i:
                return l
        raise KeyError(i)

    def path(self, i: int, j: int) -> int:
        """Tree distance in units between any two contracted nodes."""
        if i == j:
            return 0
        dist = {i: 0}
        q = deque([i])
        while q:
            u = q.popleft()
            for v, w in self.adj[u].items():
                if v not in dist:
                    dist[v] = dist[u] + w
                    if v == j:
                        return dist[v]
                    q.append(v)
        raise KeyError((i, j))

    def diameter(self) -> int:
        ids = [l.id for l in self.leaves]
        return max(self.path(a, b) for a in ids for b in ids if a < b)

    def n_lb(self) -> int:
        """max(diameter, ceil(sqrt(best-case tip-square area))), even."""
        radii = sorted((l.r for l in self.leaves), reverse=True)
        area = sum(r * r if k < 4 else 2 * r * r for k, r in enumerate(radii))
        n = max(self.diameter(), math.ceil(math.sqrt(area)))
        return n + (n % 2)

    def placed_leaves(self) -> list:
        """Leaves the packer places itself: axial ones and the lower-id
        member of each pair (the partner is mirrored)."""
        return [l for l in self.leaves
                if l.partner is None or l.id < l.partner]


def _detect_unit(lengths: list) -> float:
    u = min(lengths)
    for k in range(1, MAX_UNIT_DIVISOR + 1):
        if all(abs(x / u * k - round(x / u * k)) <= REL_TOL * max(1.0, x / u * k)
               for x in lengths):
            return u / k
    return u / MAX_UNIT_DIVISOR   # caller finds the offender and refuses


def contract(nodes: list, pairs: list) -> Tree:
    adj: dict = defaultdict(dict)
    for n in nodes:
        p = n.get("parent_id")
        if p is None:
            adj.setdefault(n["id"], {})
            continue
        adj[n["id"]][p] = float(n["length"])
        adj[p][n["id"]] = float(n["length"])
    changed = True
    while changed:                       # contract joints
        changed = False
        for v in list(adj):
            if len(adj[v]) == 2:
                (a, la), (b, lb) = adj[v].items()
                del adj[a][v]
                del adj[b][v]
                adj[a][b] = adj[b][a] = la + lb
                del adj[v]
                changed = True
                break
    hubs = tuple(sorted(v for v in adj if len(adj[v]) >= 3))
    if not hubs:
        raise ValueError("tree has no hub (no node of degree >= 3)")
    lengths = [w for v in adj for w in adj[v].values()]
    unit = _detect_unit(lengths)
    iadj: dict = {}
    for v in adj:
        iadj[v] = {}
        for u, w in adj[v].items():
            k = w / unit
            if abs(k - round(k)) > REL_TOL * max(1.0, k):
                raise NonIntegral(u if len(adj[u]) == 1 else v, w, unit)
            iadj[v][u] = int(round(k))
    partner = {}
    for a, b in pairs:
        partner[a] = b
        partner[b] = a
    leaves = []
    for v in sorted(adj):
        if len(adj[v]) == 1:
            (hub, r), = iadj[v].items()
            leaves.append(Leaf(v, hub, r, partner.get(v)))
    leaf_ids = {l.id for l in leaves}
    for a, b in pairs:
        if a not in leaf_ids or b not in leaf_ids:
            raise ValueError(f"pair {a, b} is not a pair of leaves")
        la = next(l for l in leaves if l.id == a)
        lb = next(l for l in leaves if l.id == b)
        if la.r != lb.r or la.hub != lb.hub:
            raise ValueError(f"pair {a, b} differs in radius or hub")
    branches = tuple(Branch(a, b, iadj[a][b]) for a in hubs for b in iadj[a]
                     if b in hubs and a < b)
    return Tree(tuple(leaves), branches, hubs, unit, iadj)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_box_pleat_tree.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/box_pleat/__init__.py mcp_harness/box_pleat/tree.py mcp_harness/tests/test_box_pleat_tree.py
git commit -m "box_pleat: tree contraction, unit detection, grid lower bound

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: `skeleton.py` — straight skeleton of rectilinear polygons, boundary-tip mirroring, river bend ridges

**Files:**
- Create: `mcp_harness/box_pleat/skeleton.py`
- Test: `mcp_harness/tests/test_box_pleat_skeleton.py`

**Interfaces:**
- Consumes: `frozenset[Cell]` (cells may have negative coordinates when mirrored).
- Produces: `boundary_polygons(cells) -> list[list[Point]]` (half-grid coords, CCW, collinear merged; raises `ValueError` on holes/pinches/several pieces); `straight_skeleton(cells) -> list[Segment]` (half-grid, sorted, deduped); `poly_ridges(cells, tip, N) -> tuple[list[Segment], list[Segment]]` = `(interior, on_boundary)` with the polygon mirrored across each raw-edge line containing `tip` and the result clipped to the paper; `river_ridges(cells, width) -> list[Segment]`; `ridge_points(segments) -> dict[Point, frozenset[Dir]]`; `SkeletonFail(poly_id, detail)`. `Segment = tuple[Point, Point]` with the two points sorted.

- [ ] **Step 1: Write the failing tests**

```python
# mcp_harness/tests/test_box_pleat_skeleton.py
import pytest

from box_pleat.skeleton import (boundary_polygons, straight_skeleton,
                                poly_ridges, river_ridges, ridge_points)


def _segs(s):
    return {tuple(sorted(x)) for x in s}


def test_boundary_of_a_square_is_ccw_with_four_corners():
    cells = frozenset({(0, 0), (1, 0), (0, 1), (1, 1)})
    (ring,) = boundary_polygons(cells)
    assert ring == [(0, 0), (4, 0), (4, 4), (0, 4)]


def test_square_skeleton_is_two_diagonals():
    cells = frozenset({(0, 0), (1, 0), (0, 1), (1, 1)})
    assert _segs(straight_skeleton(cells)) == _segs([
        ((0, 0), (2, 2)), ((4, 0), (2, 2)), ((4, 4), (2, 2)), ((0, 4), (2, 2))])


def test_rectangle_skeleton_has_a_spine():
    cells = frozenset((c, r) for c in range(4) for r in range(2))
    assert _segs(straight_skeleton(cells)) == _segs([
        ((0, 0), (2, 2)), ((0, 4), (2, 2)), ((8, 0), (6, 2)), ((8, 4), (6, 2)),
        ((2, 2), (6, 2))])


def test_l_shape_skeleton_is_on_the_half_grid_and_reaches_every_corner():
    cells = frozenset({(c, r) for c in range(3) for r in range(3)} - {(2, 2), (1, 2), (2, 1)})
    segs = straight_skeleton(cells)
    pts = {p for s in segs for p in s}
    assert all(isinstance(v, int) for p in pts for v in p)
    (ring,) = boundary_polygons(cells)
    assert set(ring) <= pts


def test_corner_flap_gets_one_diagonal_and_edge_flap_gets_a_v():
    # corner flap r=1 at the origin of an N=4 paper: one diagonal from the tip
    interior, on_boundary = poly_ridges(frozenset({(0, 0)}), (0, 0), 4)
    assert _segs(interior) == _segs([((0, 0), (2, 2))]) and on_boundary == []
    # edge flap r=1, tip (2,0) on the bottom edge: a V from the tip
    interior, on_boundary = poly_ridges(frozenset({(1, 0), (2, 0)}), (2, 0), 4)
    assert _segs(interior) == _segs([((4, 0), (2, 2)), ((4, 0), (6, 2))])
    assert on_boundary == []
    # interior tip: plain skeleton
    interior, on_boundary = poly_ridges(frozenset({(1, 1), (2, 1), (1, 2), (2, 2)}), (2, 2), 4)
    assert len(interior) == 4 and on_boundary == []


def test_boundary_spine_is_reported_not_emitted():
    # edge flap r=1 tip (1,0) inflated to 3 cells wide: mirrored 3x2 rectangle
    # has a spine along the paper edge from the tip to (2,0)
    interior, on_boundary = poly_ridges(frozenset({(0, 0), (1, 0), (2, 0)}), (1, 0), 4)
    assert _segs(on_boundary) == _segs([((2, 0), (4, 0))])
    assert _segs(interior) == _segs([((2, 0), (0, 2)), ((4, 0), (6, 2))])


def test_river_ridges_join_bend_corners():
    cells = frozenset({(1, 2), (2, 2), (1, 3), (1, 4), (1, 5)})
    assert _segs(river_ridges(cells, 1)) == _segs([((4, 6), (2, 4))])


def test_ridge_points_expands_a_diagonal():
    rp = ridge_points([((0, 0), (2, 2)), ((2, 2), (6, 2))])
    assert rp[(1, 1)] == frozenset({(1, 1)})
    assert rp[(2, 2)] == frozenset({(1, 1), (1, 0)})
    assert rp[(4, 2)] == frozenset({(1, 0)})


def test_holes_are_refused():
    cells = frozenset({(c, r) for c in range(3) for r in range(3)} - {(1, 1)})
    with pytest.raises(ValueError):
        boundary_polygons(cells)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_box_pleat_skeleton.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'box_pleat.skeleton'`

- [ ] **Step 3: Write the implementation**

```python
# mcp_harness/box_pleat/skeleton.py
"""Straight skeleton of a rectilinear cell polygon (Lang §13.4, spec §5.3,
§10.1).

Wavefront simulation in QUARTER grid units: every edge moves inward one
quarter-unit per step, so every vertex moves (+-1, +-1) per step, edge
collapses and reflex-vertex splits happen exactly on integer steps, and all
event positions land on the half-grid. A polygon whose tip lies on a raw
paper edge is mirrored across that edge line first (a corner flap then folds
on its single diagonal, an edge flap on the V from its tip). Rivers get only
their bend diagonals (their long banks are hinges, not ridges).
"""
from __future__ import annotations

from dataclasses import dataclass

Point = tuple[int, int]
Segment = tuple[Point, Point]


@dataclass
class SkeletonFail:
    poly_id: object
    detail: str


def _sign(v: int) -> int:
    return (v > 0) - (v < 0)


def _seg(a: Point, b: Point) -> Segment:
    return (a, b) if a <= b else (b, a)


def boundary_polygons(cells: frozenset) -> list:
    """CCW rings in half-grid coordinates, collinear vertices merged.

    Raises ValueError if the cell set is not one simply-connected polygon
    (holes, pinched corners, several components)."""
    edges: dict = {}
    for (c, r) in cells:
        for a, b, nb in (((c, r), (c + 1, r), (c, r - 1)),
                         ((c + 1, r), (c + 1, r + 1), (c + 1, r)),
                         ((c + 1, r + 1), (c, r + 1), (c, r + 1)),
                         ((c, r + 1), (c, r), (c - 1, r))):
            if nb not in cells:
                if a in edges:
                    raise ValueError(f"pinched corner at {a}")
                edges[a] = b
    rings = []
    while edges:
        start = min(edges)
        ring, cur = [], start
        while True:
            ring.append(cur)
            cur = edges.pop(cur)
            if cur == start:
                break
        rings.append(ring)
    if len(rings) != 1:
        raise ValueError(f"cell set has {len(rings)} boundary rings (holes or pieces)")
    ring = rings[0]
    out = []
    n = len(ring)
    for i in range(n):
        p, c, q = ring[i - 1], ring[i], ring[(i + 1) % n]
        if (c[0] - p[0]) * (q[1] - c[1]) - (c[1] - p[1]) * (q[0] - c[0]) != 0:
            out.append(c)
    return [[(2 * x, 2 * y) for x, y in out]]


def _velocities(poly):
    vel = []
    n = len(poly)
    for i in range(n):
        p, c, q = poly[i - 1]["p"], poly[i]["p"], poly[(i + 1) % n]["p"]
        e1 = (_sign(c[0] - p[0]), _sign(c[1] - p[1]))
        e2 = (_sign(q[0] - c[0]), _sign(q[1] - c[1]))
        n1, n2 = (-e1[1], e1[0]), (-e2[1], e2[0])      # inward (left) normals, CCW
        vel.append((n1[0] + n2[0], n1[1] + n2[1]))
    return vel


def _on_segment(p, a, b) -> bool:
    if a[0] == b[0]:
        return p[0] == a[0] and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])
    if a[1] == b[1]:
        return p[1] == a[1] and min(a[0], b[0]) <= p[0] <= max(a[0], b[0])
    return False


def _cross_at(poly, i) -> int:
    n = len(poly)
    p, c, q = poly[i - 1]["p"], poly[i]["p"], poly[(i + 1) % n]["p"]
    return (c[0] - p[0]) * (q[1] - c[1]) - (c[1] - p[1]) * (q[0] - c[0])


def _resolve(poly, segs, stack):
    """Apply merges and splits until none apply. Returns the polygon (maybe
    shorter) or None if it was split (pieces pushed to `stack`)."""
    while True:
        n = len(poly)
        merged = False
        for i in range(n):                       # coincident neighbours
            j = (i + 1) % n
            a, b = poly[i], poly[j]
            if a["p"] == b["p"]:
                segs.append(_seg(a["s"], a["p"]))
                segs.append(_seg(b["s"], b["p"]))
                new = {"p": a["p"], "s": a["p"]}
                keep = [v for k, v in enumerate(poly) if k not in (i, j)]
                keep.insert(min(i, j) if j != 0 else 0, new)
                poly = keep
                merged = True
                break
        if merged:
            continue
        n = len(poly)
        if n >= 3:                               # collinear vertices vanish
            for i in range(n):
                if _cross_at(poly, i) == 0:
                    segs.append(_seg(poly[i]["s"], poly[i]["p"]))
                    del poly[i]
                    merged = True
                    break
        if merged:
            continue
        if len(poly) <= 2:
            return poly
        n = len(poly)
        for i in range(n):                       # reflex vertex on an edge
            if _cross_at(poly, i) >= 0:
                continue
            R = poly[i]
            for j in range(n):
                if j in (i, (i - 1) % n):
                    continue
                a, b = poly[j]["p"], poly[(j + 1) % n]["p"]
                if _on_segment(R["p"], a, b):
                    segs.append(_seg(R["s"], R["p"]))
                    idx1 = [(j + 1 + k) % n for k in range((i - j - 1) % n)]
                    idx2 = [(i + 1 + k) % n for k in range((j - i) % n)]
                    p1 = [{"p": R["p"], "s": R["p"]}] + [poly[k] for k in idx1]
                    p2 = [{"p": R["p"], "s": R["p"]}] + [poly[k] for k in idx2]
                    stack.append(p1)
                    stack.append(p2)
                    return None
        return poly


def straight_skeleton(cells: frozenset) -> list:
    (ring,) = boundary_polygons(cells)
    segs: list = []
    stack = [[{"p": (2 * x, 2 * y), "s": (2 * x, 2 * y)} for x, y in ring]]
    steps = 0
    while stack:
        poly = stack.pop()
        while poly is not None:
            poly = _resolve(poly, segs, stack)
            if poly is None:
                break
            if len(poly) == 2:
                a, b = poly
                segs += [_seg(a["s"], a["p"]), _seg(b["s"], b["p"]), _seg(a["p"], b["p"])]
                break
            if len(poly) == 1:
                segs.append(_seg(poly[0]["s"], poly[0]["p"]))
                break
            for v, d in zip(poly, _velocities(poly)):
                v["p"] = (v["p"][0] + d[0], v["p"][1] + d[1])
            steps += 1
            if steps > 100_000:
                raise RuntimeError("straight skeleton did not terminate")
    out = set()
    for a, b in segs:
        if a == b:
            continue
        for v in (*a, *b):
            if v % 2:
                raise ValueError(f"skeleton vertex off the half-grid: {a, b}")
        out.add(_seg((a[0] // 2, a[1] // 2), (b[0] // 2, b[1] // 2)))
    return sorted(out)


def poly_ridges(cells: frozenset, tip: Point, N: int):
    """(interior ridges, ridges lying on the paper edge) for one hinge polygon."""
    cs = set(cells)
    x, y = tip
    if x == 0:
        cs |= {(-1 - c, r) for c, r in list(cs)}
    if x == N:
        cs |= {(2 * N - 1 - c, r) for c, r in list(cs)}
    if y == 0:
        cs |= {(c, -1 - r) for c, r in list(cs)}
    if y == N:
        cs |= {(c, 2 * N - 1 - r) for c, r in list(cs)}
    L = 2 * N

    def inside(p):
        return 0 <= p[0] <= L and 0 <= p[1] <= L

    def on_edge_line(a, b):
        return ((a[0] == b[0] == 0) or (a[0] == b[0] == L) or
                (a[1] == b[1] == 0) or (a[1] == b[1] == L))

    interior, on_boundary = [], []
    for a, b in straight_skeleton(frozenset(cs)):
        if not (inside(a) and inside(b)):
            continue
        (on_boundary if on_edge_line(a, b) else interior).append((a, b))
    return sorted(interior), sorted(on_boundary)


def river_ridges(cells: frozenset, width: int) -> list:
    (ring,) = boundary_polygons(cells)
    poly = [{"p": p, "s": p} for p in ring]
    vel = _velocities(poly)
    out = []
    for i in range(len(poly)):
        if _cross_at(poly, i) < 0:
            vx, vy = vel[i]
            p = poly[i]["p"]
            q = (p[0] + 2 * width * vx, p[1] + 2 * width * vy)
            if q not in ring:
                raise ValueError(f"river is not constant width at bend {p}")
            out.append(_seg(p, q))
    return sorted(set(out))


def ridge_points(segments: list) -> dict:
    pts: dict = {}
    for a, b in segments:
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = max(abs(dx), abs(dy))
        if n == 0 or not (abs(dx) in (0, n) and abs(dy) in (0, n)):
            raise ValueError(f"ridge {a, b} is neither axis-parallel nor 45 degrees")
        s = (_sign(dx), _sign(dy))
        d = s if (s[0] > 0 or (s[0] == 0 and s[1] > 0)) else (-s[0], -s[1])
        for k in range(n + 1):
            pts.setdefault((a[0] + k * s[0], a[1] + k * s[1]), set()).add(d)
    return {p: frozenset(v) for p, v in pts.items()}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_box_pleat_skeleton.py -v`
Expected: 9 passed. The L-shape test exercises splits; if it fails, print `segs` for the L and compare against a roof-ridge sketch (Lang Fig. 13.19) before changing the event logic. `test_boundary_spine_is_reported_not_emitted` exercises the mirrored 3×2 rectangle: nodes at (2,0) and (4,0) in half-units.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/box_pleat/skeleton.py mcp_harness/tests/test_box_pleat_skeleton.py
git commit -m "box_pleat: straight skeleton by integral wavefront; boundary-tip mirroring; river bend ridges

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: `layout.py` — the data model and its invariants

**Files:**
- Create: `mcp_harness/box_pleat/layout.py`
- Test: `mcp_harness/tests/test_box_pleat_layout.py`

**Interfaces:**
- Consumes: `Tree`, `Leaf` (Task 1); `poly_ridges` (Task 2).
- Produces: `Cell`, `Point`, `tip_square(tip, r, N) -> frozenset[Cell]`, `mirror_cell(cell, N)`, `mirror_point(pt, N)`, `HingePoly(leaf_id, tip, r, cells)`, `River(edge, width, cells)`, `Layout(N, polys, rivers, contours={}, gadgets=[])` with `axis_col`, `cell_owner() -> dict[Cell, tuple]`, `validate(tree) -> list[str]`, and `from_half(N, tree, half_polys: dict[int, tuple[Point, set[Cell]]], half_rivers: list[tuple[tuple, int, set[Cell]]]) -> Layout`.

- [ ] **Step 1: Write the failing tests**

```python
# mcp_harness/tests/test_box_pleat_layout.py
from box_pleat.tree import contract
from box_pleat.layout import (tip_square, mirror_cell, mirror_point,
                              HingePoly, River, Layout, from_half)
from test_box_pleat_tree import toy_nodes


def test_tip_square_clips_corner_edge_middle():
    assert tip_square((0, 0), 2, 6) == frozenset({(0, 0), (1, 0), (0, 1), (1, 1)})
    assert tip_square((3, 0), 1, 6) == frozenset({(2, 0), (3, 0)})
    assert len(tip_square((3, 3), 1, 6)) == 4


def test_mirrors():
    assert mirror_cell((0, 2), 6) == (5, 2)
    assert mirror_point((1, 2), 6) == (5, 2)
    assert mirror_point((3, 2), 6) == (3, 2)


def hand_layout():
    """A valid N=6 packing of the toy worked out by hand."""
    nodes, pairs = toy_nodes()
    tree = contract(nodes, pairs)
    half_polys = {
        2: ((0, 2), {(c, r) for c in range(2) for r in range(4)} | {(2, 0), (2, 1)}),  # L-shape
        4: ((3, 3), {(2, 2), (2, 3)}),                                                # axial square
        5: ((0, 6), {(c, 5) for c in range(3)}),                                      # corner, grown
    }
    half_rivers = [((0, 1), 1, {(c, 4) for c in range(3)})]
    return tree, from_half(6, tree, half_polys, half_rivers)


def test_from_half_builds_a_valid_mirrored_layout():
    tree, lay = hand_layout()
    assert lay.N == 6 and lay.axis_col == 3
    assert {p.leaf_id for p in lay.polys} == {2, 3, 4, 5, 6}
    assert next(p for p in lay.polys if p.leaf_id == 3).tip == (6, 2)
    assert next(p for p in lay.polys if p.leaf_id == 4).cells == frozenset(
        {(2, 2), (2, 3), (3, 2), (3, 3)})
    assert lay.validate(tree) == []
    assert len(lay.cell_owner()) == 36


def test_validate_reports_each_broken_invariant():
    tree, lay = hand_layout()
    bad = Layout(lay.N, [HingePoly(p.leaf_id, p.tip, p.r, p.cells | {(0, 4)})
                         if p.leaf_id == 5 else p for p in lay.polys], lay.rivers)
    assert any("partition" in e for e in bad.validate(tree))
    bad2 = Layout(lay.N, [HingePoly(p.leaf_id, (3, 2), p.r, p.cells)
                          if p.leaf_id == 4 else p for p in lay.polys], lay.rivers)
    assert any("path" in e for e in bad2.validate(tree))


def test_tall_axial_rectangle_is_rejected():
    # leaf 4 grown down to a 2x4 rectangle: its spine would lie on the axis
    nodes, pairs = toy_nodes()
    tree = contract(nodes, pairs)
    half_polys = {
        2: ((0, 2), {(c, r) for c in range(2) for r in range(4)}),
        4: ((3, 3), {(2, r) for r in range(4)}),
        5: ((0, 6), {(c, 5) for c in range(3)}),
    }
    lay = from_half(6, tree, half_polys, [((0, 1), 1, {(c, 4) for c in range(3)})])
    assert any("axis" in e for e in lay.validate(tree))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_box_pleat_layout.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'box_pleat.layout'`

- [ ] **Step 3: Write the implementation**

```python
# mcp_harness/box_pleat/layout.py
"""The packing layout: hinge polygons + rivers on an N x N grid (spec §4).

This is the seam subproject B's technique macros mutate. Every macro must
leave `validate()` empty; the crease construction reads nothing else.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from .skeleton import poly_ridges

Cell = tuple[int, int]
Point = tuple[int, int]

_N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


def tip_square(tip: Point, r: int, N: int) -> frozenset:
    x, y = tip
    return frozenset((c, rr) for c in range(max(0, x - r), min(N, x + r))
                     for rr in range(max(0, y - r), min(N, y + r)))


def mirror_cell(cell: Cell, N: int) -> Cell:
    return (N - 1 - cell[0], cell[1])


def mirror_point(pt: Point, N: int) -> Point:
    return (N - pt[0], pt[1])


def _components(cells: frozenset) -> list:
    todo, out = set(cells), []
    while todo:
        seed = min(todo)
        comp, q = {seed}, deque([seed])
        todo.discard(seed)
        while q:
            c, r = q.popleft()
            for dc, dr in _N4:
                n = (c + dc, r + dr)
                if n in todo:
                    todo.discard(n)
                    comp.add(n)
                    q.append(n)
        out.append(frozenset(comp))
    return out


def _run_len(cells, c, r, dc, dr, N) -> int:
    k = 0
    while (c + (k + 1) * dc, r + (k + 1) * dr) in cells and k < N:
        k += 1
    return k


@dataclass(frozen=True)
class HingePoly:
    leaf_id: int
    tip: Point
    r: int
    cells: frozenset


@dataclass(frozen=True)
class River:
    edge: tuple
    width: int
    cells: frozenset


@dataclass
class Layout:
    N: int
    polys: list
    rivers: list
    contours: dict = field(default_factory=dict)
    gadgets: list = field(default_factory=list)

    @property
    def axis_col(self) -> int:
        return self.N // 2

    def cell_owner(self) -> dict:
        owner = {}
        for p in self.polys:
            for c in p.cells:
                owner.setdefault(c, ("poly", p.leaf_id))
        for rv in self.rivers:
            for c in rv.cells:
                owner.setdefault(c, ("river", rv.edge))
        return owner

    def validate(self, tree) -> list:
        errs = []
        N = self.N
        if N % 2:
            errs.append(f"N={N} is odd")
        seen: dict = {}
        for p in self.polys:
            for c in p.cells:
                seen.setdefault(c, []).append(("poly", p.leaf_id))
        for rv in self.rivers:
            for c in rv.cells:
                seen.setdefault(c, []).append(("river", rv.edge))
        for c, owners in sorted(seen.items()):
            if len(owners) > 1:
                errs.append(f"partition: cell {c} owned by {owners}")
        missing = [(c, r) for c in range(N) for r in range(N) if (c, r) not in seen]
        if missing:
            errs.append(f"partition: {len(missing)} unowned cells, first {missing[0]}")
        for p in self.polys:
            if not tip_square(p.tip, p.r, N) <= p.cells:
                errs.append(f"tip-square: leaf {p.leaf_id} tip {p.tip} r={p.r}")
            if len(_components(p.cells)) != 1:
                errs.append(f"connectivity: leaf {p.leaf_id} polygon is disconnected")
        by_id = {p.leaf_id: p for p in self.polys}
        for p in self.polys:
            partner = tree.leaf(p.leaf_id).partner
            q = by_id.get(partner if partner is not None else p.leaf_id)
            if q is None:
                errs.append(f"mirror: leaf {p.leaf_id} has no partner polygon")
                continue
            if frozenset(mirror_cell(c, N) for c in p.cells) != q.cells:
                errs.append(f"mirror: leaf {p.leaf_id} vs {q.leaf_id}")
            if mirror_point(p.tip, N) != q.tip:
                errs.append(f"mirror: tip of leaf {p.leaf_id}")
        for rv in self.rivers:
            if frozenset(mirror_cell(c, N) for c in rv.cells) != rv.cells:
                errs.append(f"mirror: river {rv.edge}")
        tips = {p.leaf_id: p.tip for p in self.polys}
        ids = sorted(tips)
        for i in ids:
            for j in ids:
                if i < j:
                    d = max(abs(tips[i][0] - tips[j][0]), abs(tips[i][1] - tips[j][1]))
                    need = tree.path(i, j)
                    if d < need:
                        errs.append(f"path: leaves {i},{j} Chebyshev {d} < {need}")
        for rv in self.rivers:
            if len(_components(rv.cells)) != 1:
                errs.append(f"river {rv.edge} is disconnected")
            for (c, r) in rv.cells:
                row = 1 + _run_len(rv.cells, c, r, 1, 0, N) + _run_len(rv.cells, c, r, -1, 0, N)
                col = 1 + _run_len(rv.cells, c, r, 0, 1, N) + _run_len(rv.cells, c, r, 0, -1, N)
                if max(row, col) < rv.width:
                    errs.append(f"river {rv.edge}: cell {(c, r)} thinner than {rv.width}")
                    break
        river_cells = frozenset(c for rv in self.rivers for c in rv.cells)
        free = frozenset((c, r) for c in range(N) for r in range(N)) - river_cells
        regions = _components(free)
        region_of = {}
        for k, reg in enumerate(regions):
            for c in reg:
                region_of[c] = k
        hub_region: dict = {}
        for p in self.polys:
            ks = {region_of.get(c) for c in p.cells}
            if len(ks) != 1 or None in ks:
                errs.append(f"region: leaf {p.leaf_id} spans regions {ks}")
                continue
            hub = tree.leaf(p.leaf_id).hub
            k = ks.pop()
            if hub_region.setdefault(hub, k) != k:
                errs.append(f"region: hub {hub} in two regions")
        if len(set(hub_region.values())) != len(hub_region):
            errs.append("region: two hubs share a region")
        for rv in self.rivers:
            a, b = rv.edge
            adj = {region_of[n] for c in rv.cells for dc, dr in _N4
                   for n in [(c[0] + dc, c[1] + dr)] if n in region_of}
            for hub in (a, b):
                if hub in hub_region and hub_region[hub] not in adj:
                    errs.append(f"region: river {rv.edge} does not touch hub {hub}")
        # an axial polygon whose ridge runs along the centre column cannot
        # carry the tip's axial contour (spec §10.2)
        for p in self.polys:
            if tree.leaf(p.leaf_id).partner is None:
                try:
                    interior, _ = poly_ridges(p.cells, p.tip, N)
                except ValueError as exc:
                    errs.append(f"skeleton: leaf {p.leaf_id}: {exc}")
                    continue
                if any(a[0] == b[0] == N for a, b in interior):
                    errs.append(f"axis: leaf {p.leaf_id} has a ridge along the centre column")
        return errs


def from_half(N: int, tree, half_polys: dict, half_rivers: list) -> Layout:
    """Mirror a left-half placement into a full Layout.

    half_polys: {leaf_id: (tip, cells)} for every placed leaf (axial leaves
    carry only their left-half cells); half_rivers: [(edge, width, cells)].
    """
    polys = []
    for lid, (tip, cells) in sorted(half_polys.items()):
        leaf = tree.leaf(lid)
        cells = frozenset(cells)
        if leaf.partner is None:
            polys.append(HingePoly(lid, tip, leaf.r,
                                   cells | frozenset(mirror_cell(c, N) for c in cells)))
        else:
            polys.append(HingePoly(lid, tip, leaf.r, cells))
            polys.append(HingePoly(leaf.partner, mirror_point(tip, N), leaf.r,
                                   frozenset(mirror_cell(c, N) for c in cells)))
    rivers = [River(tuple(edge), w, frozenset(cells) |
                    frozenset(mirror_cell(c, N) for c in cells))
              for edge, w, cells in half_rivers]
    polys.sort(key=lambda p: p.leaf_id)
    return Layout(N, polys, rivers)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_box_pleat_layout.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/box_pleat/layout.py mcp_harness/tests/test_box_pleat_layout.py
git commit -m "box_pleat: Layout data model with the packing invariants

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: `pack.py` — half-square backtracking packer with gap fill and grid sweep

**Files:**
- Create: `mcp_harness/box_pleat/pack.py`
- Test: `mcp_harness/tests/test_box_pleat_pack.py`

**Interfaces:**
- Consumes: `Tree`, `Leaf`, `Branch` (Task 1); `tip_square`, `from_half`, `Layout` (Task 3).
- Produces: `pack(tree, *, max_N=None, budget=200_000) -> Layout | PackFail`; `PackFail(stage: str, N_tried: int, detail: str)`.

- [ ] **Step 1: Write the failing tests**

```python
# mcp_harness/tests/test_box_pleat_pack.py
import json
import pytest

from box_pleat.tree import contract
from box_pleat.pack import pack, PackFail
from test_box_pleat_tree import toy_nodes, RULE6


def test_toy_packs_at_six_and_not_at_four():
    nodes, pairs = toy_nodes()
    tree = contract(nodes, pairs)
    lay = pack(tree)
    assert not isinstance(lay, PackFail), lay
    assert lay.N == 6
    assert lay.validate(tree) == []
    # exhaustive at N=4: every river band / L and every tip is enumerated
    fail = pack(tree, max_N=4, budget=10**9)
    assert isinstance(fail, PackFail) and fail.N_tried == 4


def test_star_tree_without_rivers_packs():
    nodes = [{"id": 0, "parent_id": None, "length": 0.0}] + [
        {"id": i, "parent_id": 0, "length": 2.0} for i in range(1, 7)]
    tree = contract(nodes, [[1, 2], [3, 4], [5, 6]])
    lay = pack(tree)
    assert not isinstance(lay, PackFail), lay
    assert lay.validate(tree) == [] and lay.rivers == []


def test_two_river_beetle_packs_within_bound():
    # Lang §13.6 generic beetle: antennae 1, head 1, front legs 4 | river 1 |
    # mid legs 6, body 1 | river 2 | hind legs 8, abdomen 2
    nodes = [
        {"id": 0, "parent_id": None, "length": 0.0},
        {"id": 1, "parent_id": 0, "length": 1.0},
        {"id": 2, "parent_id": 1, "length": 2.0},
        {"id": 10, "parent_id": 0, "length": 1.0}, {"id": 11, "parent_id": 0, "length": 1.0},
        {"id": 12, "parent_id": 0, "length": 1.0},
        {"id": 13, "parent_id": 0, "length": 4.0}, {"id": 14, "parent_id": 0, "length": 4.0},
        {"id": 20, "parent_id": 1, "length": 6.0}, {"id": 21, "parent_id": 1, "length": 6.0},
        {"id": 22, "parent_id": 1, "length": 1.0},
        {"id": 30, "parent_id": 2, "length": 8.0}, {"id": 31, "parent_id": 2, "length": 8.0},
        {"id": 32, "parent_id": 2, "length": 2.0},
    ]
    pairs = [[10, 11], [13, 14], [20, 21], [30, 31]]
    tree = contract(nodes, pairs)
    lay = pack(tree, budget=2_000_000)
    assert not isinstance(lay, PackFail), lay
    assert lay.N <= 2 * tree.n_lb()
    assert lay.validate(tree) == []


@pytest.mark.parametrize("subject", ["frog", "bird", "dog", "spider"])
def test_committed_subjects_pack(subject):
    d = json.load(open(RULE6))
    e = next(x for x in d if x["subject"] == subject)
    tree = contract(e["requested"], e["pairs"])
    lay = pack(tree, budget=2_000_000)
    assert not isinstance(lay, PackFail), lay
    assert lay.validate(tree) == []
    assert lay.N <= 2 * tree.n_lb()


def test_pack_is_deterministic():
    nodes, pairs = toy_nodes()
    tree = contract(nodes, pairs)
    a, b = pack(tree), pack(tree)
    assert [(p.leaf_id, p.tip, sorted(p.cells)) for p in a.polys] == \
           [(p.leaf_id, p.tip, sorted(p.cells)) for p in b.polys]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_box_pleat_pack.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'box_pleat.pack'`

- [ ] **Step 3: Write the implementation**

```python
# mcp_harness/box_pleat/pack.py
"""Half-square backtracking polygon packer (spec §5.2, §10.4).

At each even grid size N: rivers (straight band or one L-bend from the
axis, enumerated), hub->region assignment, leaves largest-first with
candidate tips ranked corner > edge > interior then most contacts, then gap
fill one cell at a time (smallest perimeter increase first, lower leaf id on
ties). Rivers never grow. Exhausting the node budget or the candidates moves
on to N + 2, up to max_N (default 2 * N_lb).
"""
from __future__ import annotations

import itertools
from collections import deque
from dataclasses import dataclass

from .layout import Layout, from_half, tip_square

_N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


@dataclass
class PackFail:
    stage: str
    N_tried: int
    detail: str


class _Budget(Exception):
    pass


def pack(tree, *, max_N: int | None = None, budget: int = 200_000):
    N = tree.n_lb()
    max_N = max_N or 2 * N
    last = PackFail("pack", N, "no grid tried")
    while N <= max_N:
        res = _pack_at(tree, N, budget)
        if isinstance(res, Layout):
            return res
        last = res
        N += 2
    return last


# --- rivers -----------------------------------------------------------------

def _half_cells(N):
    H = N // 2
    return frozenset((c, r) for c in range(H) for r in range(N))


def _river_candidates(N, w):
    """Cell sets in the left half: straight bands (central first), then
    L-bends leaving the axis and turning to the top or bottom edge."""
    H = N // 2
    out = []
    for y0 in sorted(range(0, N - w + 1), key=lambda y: (abs(2 * y + w - N), y)):
        out.append(frozenset((c, r) for c in range(H) for r in range(y0, y0 + w)))
    for y0 in range(0, N - w + 1):
        for c1 in range(1, H - w + 1):
            horiz = {(c, r) for c in range(c1, H) for r in range(y0, y0 + w)}
            out.append(frozenset(horiz | {(c, r) for c in range(c1, c1 + w)
                                          for r in range(y0 + w, N)}))
            out.append(frozenset(horiz | {(c, r) for c in range(c1, c1 + w)
                                          for r in range(0, y0)}))
    return out


def _river_placements(tree, N):
    """Yield lists [(edge, w, cells)] covering every branch, pairwise disjoint."""
    branches = list(tree.branches)
    if not branches:
        yield []
        return

    def rec(k, used, acc):
        if k == len(branches):
            yield list(acc)
            return
        b = branches[k]
        for cells in _river_candidates(N, b.w):
            if cells & used:
                continue
            acc.append(((b.a, b.b), b.w, cells))
            yield from rec(k + 1, used | cells, acc)
            acc.pop()
    yield from rec(0, frozenset(), [])


def _regions(N, river_cells):
    todo = set(_half_cells(N)) - set(river_cells)
    regs = []
    while todo:
        seed = min(todo)
        comp, q = {seed}, deque([seed])
        todo.discard(seed)
        while q:
            c, r = q.popleft()
            for dc, dr in _N4:
                n = (c + dc, r + dr)
                if n in todo:
                    todo.discard(n)
                    comp.add(n)
                    q.append(n)
        regs.append(frozenset(comp))
    return regs


def _hub_maps(tree, regions, rivers):
    """Every bijection hub->region consistent with the river adjacencies."""
    if len(regions) != len(tree.hubs):
        return
    touch = []
    for edge, w, cells in rivers:
        adj = set()
        for k, reg in enumerate(regions):
            if any((c + dc, r + dr) in reg for (c, r) in cells for dc, dr in _N4):
                adj.add(k)
        touch.append((edge, adj))
    for perm in itertools.permutations(range(len(regions))):
        m = dict(zip(tree.hubs, perm))
        if all(m[a] in adj and m[b] in adj and m[a] != m[b] for (a, b), adj in touch):
            yield m


# --- leaves -----------------------------------------------------------------

def _candidates(leaf, tree, N, region, occupied, placed):
    H = N // 2
    r = leaf.r
    xs = [H] if leaf.partner is None else range(0, H - r + 1)
    out = []
    for x in xs:
        for y in range(0, N + 1):
            cells = frozenset(c for c in tip_square((x, y), r, N) if c[0] < H)
            if not cells or (cells & occupied) or not cells <= region:
                continue
            if any(max(abs(tx - x), abs(ty - y)) < tree.path(leaf.id, lid)
                   for lid, (tx, ty) in placed.items()):
                continue
            if leaf.partner is None:
                cls = 1 if y in (0, N) else 2
            else:
                cls = 0 if (x == 0 and y in (0, N)) else 1 if (x == 0 or y in (0, N)) else 2
            contacts = 0
            for (c, rr) in cells:
                for dc, dr in _N4:
                    n = (c + dc, rr + dr)
                    if n in occupied or n[0] < 0 or n[0] >= H or n[1] < 0 or n[1] >= N:
                        contacts += 1
            out.append(((cls, -contacts, y, x), (x, y), cells))
    out.sort(key=lambda t: t[0])
    return [(tip, cells) for _, tip, cells in out]


def _place_leaves(tree, N, hub_region, river_cells, counter):
    order = sorted(tree.placed_leaves(),
                   key=lambda l: (-l.r, 0 if l.partner is None else 1, l.id))
    occupied = set(river_cells)
    placed: dict = {}          # leaf id -> tip, INCLUDING mirrored partners
    result: dict = {}
    deepest = [0, None]

    def rec(i):
        if i == len(order):
            return True
        leaf = order[i]
        cands = _candidates(leaf, tree, N, hub_region[leaf.hub], occupied, placed)
        if not cands and i >= deepest[0]:
            deepest[0], deepest[1] = i, leaf.id
        for tip, cells in cands:
            counter[0] -= 1
            if counter[0] < 0:
                raise _Budget()
            occupied.update(cells)
            placed[leaf.id] = tip
            if leaf.partner is not None:
                placed[leaf.partner] = (N - tip[0], tip[1])
            result[leaf.id] = (tip, set(cells))
            if rec(i + 1):
                return True
            occupied.difference_update(cells)
            del placed[leaf.id]
            if leaf.partner is not None:
                del placed[leaf.partner]
            del result[leaf.id]
        return False

    if rec(0):
        return result, None
    return None, f"no tip for leaf {deepest[1]} after placing {deepest[0]} leaves"


# --- gap fill ---------------------------------------------------------------

def _gap_fill(N, polys, river_cells, counter):
    occupied = set(river_cells)
    for _, cells in polys.values():
        occupied |= cells
    empty = sorted(set(_half_cells(N)) - occupied, key=lambda c: (c[1], c[0]))

    def rec(k):
        if k == len(empty):
            return True
        e = empty[k]
        cands = []
        for lid, (tip, cells) in polys.items():
            nb = sum(1 for dc, dr in _N4 if (e[0] + dc, e[1] + dr) in cells)
            if nb:
                cands.append((4 - 2 * nb, lid))
        if not cands:
            return False
        for _, lid in sorted(cands):
            counter[0] -= 1
            if counter[0] < 0:
                raise _Budget()
            polys[lid][1].add(e)
            if rec(k + 1):
                return True
            polys[lid][1].discard(e)
        return False

    if rec(0):
        return None
    return f"unfillable cell {empty[0] if empty else None}"


# --- driver -----------------------------------------------------------------

def _pack_at(tree, N, budget):
    counter = [budget]
    fail = PackFail("river", N, "no river placement")
    try:
        for rivers in _river_placements(tree, N):
            river_cells = frozenset(c for _, _, cells in rivers for c in cells)
            regions = _regions(N, river_cells)
            for hub_map in _hub_maps(tree, regions, rivers):
                hub_region = {h: regions[k] for h, k in hub_map.items()}
                polys, why = _place_leaves(tree, N, hub_region, river_cells, counter)
                if polys is None:
                    fail = PackFail("leaf", N, why)
                    continue
                why = _gap_fill(N, polys, river_cells, counter)
                if why is not None:
                    fail = PackFail("gapfill", N, why)
                    continue
                lay = from_half(N, tree, polys, rivers)
                errs = lay.validate(tree)
                if errs:
                    fail = PackFail("validate", N, "; ".join(errs[:3]))
                    continue
                return lay
    except _Budget:
        return PackFail(fail.stage, N, f"budget {budget} exhausted ({fail.detail})")
    return fail
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_box_pleat_pack.py -v`
Expected: 8 passed. If a committed subject or the beetle exhausts the budget, raise the budget in that test (not the default) and note the number in the commit message. If `validate` rejects every gap-filled layout with `axis:` (a tall axial rectangle), the fix is in `_gap_fill`'s candidate order, not in `validate`: prefer non-axial polygons for cells in column `N//2 - 1`.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/box_pleat/pack.py mcp_harness/tests/test_box_pleat_pack.py
git commit -m "box_pleat: half-square backtracking packer with gap fill and grid sweep

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: `contours.py` — dense bouncing contours

**Files:**
- Create: `mcp_harness/box_pleat/contours.py`
- Test: `mcp_harness/tests/test_box_pleat_contours.py`

**Interfaces:**
- Consumes: `Layout` (Task 3); ridge point dict from `ridge_points` (Task 2); `boundary_ridges: list[Segment]` (Task 2, `poly_ridges` second element).
- Produces: `propagate(layout, tree, ridge_pts, boundary_ridges) -> dict[SegKey, Fraction] | ContourFail`; `ContourFail(kind: str, site)`; `SegKey = tuple[Point, Point]` (sorted pair of adjacent half-grid points); `out_dirs(lines: frozenset[Dir], d: Dir) -> list[Dir]`; `is_boundary_seg(key, N) -> bool`; `runs(layout) -> list[Run]` with `Run(horizontal: bool, line: int, start: int, end: int, owner_pos: tuple | None, owner_neg: tuple | None)` in half-grid units (`owner_pos` is the owner on the +normal side, i.e. above a horizontal run / right of a vertical run; `None` means the paper edge).

- [ ] **Step 1: Write the failing tests**

```python
# mcp_harness/tests/test_box_pleat_contours.py
from fractions import Fraction

from box_pleat.contours import out_dirs, propagate, ContourFail, is_boundary_seg, runs
from box_pleat.layout import Layout, HingePoly
from box_pleat.skeleton import poly_ridges, ridge_points
from box_pleat.tree import contract


def test_out_dirs_reflection_rules():
    # 45 degree incidence: 90 degree turn along the optical back-trace
    assert out_dirs(frozenset({(1, 1)}), (1, 0)) == [(0, -1)]
    assert out_dirs(frozenset({(1, 1)}), (-1, 0)) == [(0, 1)]
    # perpendicular ridge: straight through
    assert out_dirs(frozenset({(0, 1)}), (1, 0)) == [(1, 0)]
    # parallel ridge: not a crossing, straight on
    assert out_dirs(frozenset({(1, 0)}), (1, 0)) == [(1, 0)]
    # V-corner of two diagonals pointing at the contour: back the way it came
    assert out_dirs(frozenset({(1, 1), (1, -1)}), (1, 0)) == []
    # Y junction (spine + two diagonals): straight on AND a side branch
    outs = out_dirs(frozenset({(1, 0), (1, 1), (1, -1)}), (0, 1))
    assert set(outs) == {(0, 1), (-1, 0)}


def _single_square():
    nodes = [{"id": 0, "parent_id": None, "length": 0.0},
             {"id": 1, "parent_id": 0, "length": 1.0},
             {"id": 2, "parent_id": 0, "length": 1.0},
             {"id": 3, "parent_id": 0, "length": 1.0}]
    tree = contract(nodes, [])
    cells = frozenset({(0, 0), (1, 0), (0, 1), (1, 1)})
    lay = Layout(2, [HingePoly(1, (1, 1), 1, cells)], [])
    interior, on_b = poly_ridges(cells, (1, 1), 2)
    return tree, lay, ridge_points(interior), on_b


def test_single_square_tip_axials_and_corner_slivers():
    tree, lay, rp, on_b = _single_square()
    cont = propagate(lay, tree, rp, on_b)
    assert not isinstance(cont, ContourFail), cont
    # axials from the tip (2,2) to all four edges, elevation 0
    for k in (((1, 2), (2, 2)), ((2, 2), (3, 2)), ((2, 1), (2, 2)), ((2, 2), (2, 3))):
        assert cont[k] == 0
    # dense seeds from the raw (hinge-like) edges bounce into corner slivers
    assert cont[((1, 0), (1, 1))] == Fraction(1, 2)
    assert cont[((0, 1), (1, 1))] == Fraction(1, 2)
    # no contour is registered on the paper boundary itself
    assert not any(is_boundary_seg(k, 2) for k in cont)


def test_runs_of_single_square_are_four_raw_edges():
    tree, lay, rp, on_b = _single_square()
    rs = runs(lay)
    assert len(rs) == 4
    assert all((r.owner_pos is None) != (r.owner_neg is None) for r in rs)


def test_two_stacked_rectangles_share_one_axial_and_emit_spine_extensions():
    nodes = [{"id": 0, "parent_id": None, "length": 0.0},
             {"id": 1, "parent_id": 0, "length": 1.0},
             {"id": 2, "parent_id": 0, "length": 1.0},
             {"id": 3, "parent_id": 0, "length": 1.0}]
    tree = contract(nodes, [])
    lower = frozenset((c, r) for c in range(4) for r in range(2))
    upper = frozenset((c, r) for c in range(4) for r in range(2, 4))
    lay = Layout(4, [HingePoly(1, (2, 1), 1, lower), HingePoly(2, (2, 3), 1, upper)], [])
    ridges, on_b = [], []
    for p in lay.polys:
        i, b = poly_ridges(p.cells, p.tip, 4)
        ridges += i
        on_b += b
    cont = propagate(lay, tree, ridge_points(ridges), on_b)
    assert not isinstance(cont, ContourFail), cont
    assert cont[((4, 2), (4, 3))] == 0 and cont[((4, 5), (4, 6))] == 0
    # the sawhorse spine extension of the lower rectangle: (0,2)-(2,2) at elevation 1
    assert cont[((0, 2), (1, 2))] == 1 and cont[((1, 2), (2, 2))] == 1
    # nothing on the boundary, and no horizontal launch along the spine from the tip
    assert not any(is_boundary_seg(k, 4) for k in cont)
    assert ((3, 2), (4, 2)) not in cont
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_box_pleat_contours.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'box_pleat.contours'`

- [ ] **Step 3: Write the implementation**

```python
# mcp_harness/box_pleat/contours.py
"""Dense axis-parallel contours (Lang §13.5, spec §5.4 as amended by §10.3).

Contours live on half-grid lines as unit segments keyed by their sorted
endpoints, each carrying an elevation (Fraction, cells). They propagate
straight, reflect at ridges (the outgoing ray is the mirror image of the
incoming ray across the ridge line: 45-degree incidence turns 90 degrees,
perpendicular incidence passes straight), split at multi-ridge junctions,
and stop on the paper edge or on an existing contour of the same elevation.
A segment reached at two elevations is a collision.

Seeds, in order: (a) raw-edge axials for boundary tips and tip launches at
elevation 0; (b) for every straight boundary run touched by an elevation-0
segment at points A, every interior half-grid point P of the run launches
perpendicular to the run into each owner at elevation min|P - a| / 2, until
no run gains a new launch.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from fractions import Fraction

Point = tuple[int, int]
Dir = tuple[int, int]
SegKey = tuple[Point, Point]

AXIS_ELEV = Fraction(0)
_DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))


@dataclass
class ContourFail:
    kind: str
    site: object


@dataclass(frozen=True)
class Run:
    horizontal: bool
    line: int          # Y (horizontal) or X (vertical), half-grid
    start: int         # along-run coordinate, half-grid, start < end
    end: int
    owner_pos: tuple | None   # above / right
    owner_neg: tuple | None   # below / left


def _key(p: Point, q: Point) -> SegKey:
    return (p, q) if p <= q else (q, p)


def is_boundary_seg(key: SegKey, N: int) -> bool:
    (a, b) = key
    L = 2 * N
    return (a[0] == b[0] == 0 or a[0] == b[0] == L or
            a[1] == b[1] == 0 or a[1] == b[1] == L)


def _on_boundary(p: Point, N: int) -> bool:
    L = 2 * N
    return p[0] in (0, L) or p[1] in (0, L)


def _reflect(v, line):
    lx, ly = line
    n = math.hypot(lx, ly)
    lx, ly = lx / n, ly / n
    dot = v[0] * lx + v[1] * ly
    return (2 * dot * lx - v[0], 2 * dot * ly - v[1])


def out_dirs(lines: frozenset, d: Dir) -> list:
    """Directions leaving a point where the ridge `lines` meet, for a contour
    arriving with direction d: perturb to either side, follow sequential
    mirror reflections of the back-trace, drop the back-direction."""
    outs = []
    nrm = (-d[1], d[0])
    for s in (1.0, -1.0):
        pos = [-float(d[0]) + s * 1e-3 * nrm[0], -float(d[1]) + s * 1e-3 * nrm[1]]
        vel = [float(d[0]), float(d[1])]
        for _ in range(16):
            best = None
            for L in lines:
                den = L[0] * vel[1] - L[1] * vel[0]
                if abs(den) < 1e-12:
                    continue
                t = -(L[0] * pos[1] - L[1] * pos[0]) / den
                if t > 1e-9 and (best is None or t < best[0]):
                    best = (t, L)
            if best is None:
                break
            t, L = best
            pos = [pos[0] + t * vel[0], pos[1] + t * vel[1]]
            r = _reflect(vel, L)
            vel = [-r[0], -r[1]]
        o = (round(vel[0]), round(vel[1]))
        if abs(vel[0] - o[0]) > 1e-6 or abs(vel[1] - o[1]) > 1e-6:
            raise ValueError(f"contour left a junction off-axis: {vel}")
        if o != (-d[0], -d[1]) and o not in outs:
            outs.append(o)
    return outs


def _trace(N, contours, ridge_pts, start, d, elev):
    """Register segments from `start` in direction d. Returns None or a
    ContourFail."""
    stack = [(start, d)]
    while stack:
        P, d = stack.pop()
        while True:
            Q = (P[0] + d[0], P[1] + d[1])
            if not (0 <= Q[0] <= 2 * N and 0 <= Q[1] <= 2 * N):
                break
            k = _key(P, Q)
            if is_boundary_seg(k, N):
                break
            ex = contours.get(k)
            if ex is not None:
                if ex == elev:
                    break
                return ContourFail("collision", (k, ex, elev))
            contours[k] = elev
            P = Q
            if _on_boundary(P, N):
                break
            R = ridge_pts.get(P)
            if not R:
                continue
            outs = out_dirs(R, d)
            if not outs:
                break
            d = outs[0]
            stack.extend((P, o) for o in outs[1:])
    return None


def runs(layout) -> list:
    """Maximal straight boundary runs between two owners (or an owner and
    the paper edge), in half-grid units."""
    N = layout.N
    owner = layout.cell_owner()
    pieces: dict = {}     # (horizontal, line, coord) -> (owner_pos, owner_neg)
    for c in range(N):
        for r in range(N):
            o = owner[(c, r)]
            up = owner.get((c, r + 1))
            if r == N - 1 or up != o:
                for k in (2 * c, 2 * c + 1):
                    pieces[(True, 2 * r + 2, k)] = (up if r < N - 1 else None, o)
            down = owner.get((c, r - 1))
            if r == 0:
                for k in (2 * c, 2 * c + 1):
                    pieces[(True, 0, k)] = (o, None)
            right = owner.get((c + 1, r))
            if c == N - 1 or right != o:
                for k in (2 * r, 2 * r + 1):
                    pieces[(False, 2 * c + 2, k)] = (right if c < N - 1 else None, o)
            if c == 0:
                for k in (2 * r, 2 * r + 1):
                    pieces[(False, 0, k)] = (o, None)
    out = []
    for (horizontal, line), _ in sorted({(h, l): 0 for h, l, _ in pieces}.items()):
        ks = sorted(k for h, l, k in pieces if h == horizontal and l == line)
        i = 0
        while i < len(ks):
            j = i
            own = pieces[(horizontal, line, ks[i])]
            while j + 1 < len(ks) and ks[j + 1] == ks[j] + 1 and \
                    pieces[(horizontal, line, ks[j + 1])] == own:
                j += 1
            out.append(Run(horizontal, line, ks[i], ks[j] + 1, own[0], own[1]))
            i = j + 1
    return out


def _raw_axials(layout, tree, boundary_ridges) -> list:
    """Raw-edge segments adjacent to a boundary tip, walked from the tip
    until a boundary ridge or the polygon's edge run ends."""
    N, L = layout.N, 2 * layout.N
    covered = set()
    for a, b in boundary_ridges:
        sx, sy = (b[0] > a[0]) - (b[0] < a[0]), (b[1] > a[1]) - (b[1] < a[1])
        for k in range(max(abs(b[0] - a[0]), abs(b[1] - a[1]))):
            covered.add(_key((a[0] + k * sx, a[1] + k * sy), (a[0] + (k + 1) * sx, a[1] + (k + 1) * sy)))
    out = []
    for p in layout.polys:
        x, y = p.tip
        T = (2 * x, 2 * y)
        lines = []
        if x == 0 or x == N:
            lines.append((0, 1))
        if y == 0 or y == N:
            lines.append((1, 0))
        for u in lines:
            for sgn in (1, -1):
                P = T
                while True:
                    Q = (P[0] + sgn * u[0], P[1] + sgn * u[1])
                    if not (0 <= Q[0] <= L and 0 <= Q[1] <= L):
                        break
                    # the cell inside the paper touching this boundary segment
                    mid = ((P[0] + Q[0]) // 2, (P[1] + Q[1]) // 2)
                    cx = min(mid[0] // 2, N - 1) if u[0] == 1 else (0 if x == 0 else N - 1)
                    cy = min(mid[1] // 2, N - 1) if u[1] == 1 else (0 if y == 0 else N - 1)
                    if (cx, cy) not in p.cells:
                        break
                    k = _key(P, Q)
                    if k in covered:
                        break
                    out.append(k)
                    P = Q
    return out


def propagate(layout, tree, ridge_pts: dict, boundary_ridges: list):
    N = layout.N
    contours: dict = {}
    raw = {}
    for k in _raw_axials(layout, tree, boundary_ridges):
        raw[k] = AXIS_ELEV
    # (a) tip launches, skipping directions along a ridge line at the tip or
    # along the paper edge
    for p in sorted(layout.polys, key=lambda p: p.leaf_id):
        T = (2 * p.tip[0], 2 * p.tip[1])
        R = ridge_pts.get(T, frozenset())
        for d in _DIRS:
            und = d if (d[0] > 0 or (d[0] == 0 and d[1] > 0)) else (-d[0], -d[1])
            if und in R:
                continue
            if (T[0] in (0, 2 * N) and d[0] == 0) or (T[1] in (0, 2 * N) and d[1] == 0):
                continue
            f = _trace(N, contours, ridge_pts, T, d, AXIS_ELEV)
            if f:
                return f
    # (b) dense launches from axially-touched runs, to a fixpoint
    all_runs = runs(layout)
    tips_on_line = {}
    for p in layout.polys:
        tips_on_line[("poly", p.leaf_id)] = p.tip
    launched: set = set()
    while True:
        zero_pts = set()
        for k, e in list(contours.items()) + list(raw.items()):
            if e == AXIS_ELEV:
                zero_pts.add(k[0])
                zero_pts.add(k[1])
        progressed = False
        for run in all_runs:
            # raw edges of rivers, and raw edges on a polygon tip's line, are
            # contour-like (not hinge-like): never seed from them
            if run.owner_pos is None or run.owner_neg is None:
                o = run.owner_pos or run.owner_neg
                if o[0] == "river":
                    continue
                tx, ty = tips_on_line[o]
                if (run.horizontal and 2 * ty == run.line) or \
                        (not run.horizontal and 2 * tx == run.line):
                    continue

            def pt(k):
                return (k, run.line) if run.horizontal else (run.line, k)
            A = [k for k in range(run.start, run.end + 1) if pt(k) in zero_pts]
            if not A:
                continue
            for k in range(run.start + 1, run.end):
                e = Fraction(min(abs(k - a) for a in A), 2)
                if e == 0:
                    continue
                for side, o in ((1, run.owner_pos), (-1, run.owner_neg)):
                    if o is None:
                        continue
                    d = (0, side) if run.horizontal else (side, 0)
                    tag = (run, k, side)
                    if tag in launched:
                        continue
                    launched.add(tag)
                    progressed = True
                    f = _trace(N, contours, ridge_pts, pt(k), d, e)
                    if f:
                        return f
        if not progressed:
            break
    layout.contours = contours
    return contours
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_box_pleat_contours.py -v`
Expected: 4 passed. In the stacked-rectangle test the spine extension appears because the dense vertical contour `X=2` (elevation 1, seeded from the shared hinge at `Y=4`) reaches the lower rectangle's node `(2,2)` and the Y-junction rule emits `(−1,0)`; if the assertion fails, print `out_dirs(frozenset({(1,0),(1,1),(1,-1)}), (0,-1))` first.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/box_pleat/contours.py mcp_harness/tests/test_box_pleat_contours.py
git commit -m "box_pleat: dense bouncing contours seeded from tips and axially-touched runs

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: `assign.py` — pieces, face profiles, elevation labels, Maekawa CSP for ridges and hinges

**Files:**
- Create: `mcp_harness/box_pleat/assign.py`
- Test: `mcp_harness/tests/test_box_pleat_assign.py`

**Interfaces:**
- Consumes: `Layout`, interior ridge segments and boundary ridge segments (Task 2), contours dict (Task 5).
- Produces: `Piece(a: Point, b: Point, role: str)` with `role ∈ {"B","axial","elev","ridge","hinge"}`; `build_pieces(layout, ridges, contours) -> list[Piece] | AssignFail`; `faces(N, pieces) -> list[list[Point]]` (CCW cycles of the subdivision by B/ridge/hinge pieces); `profiles(N, pieces, contours, face_list) -> dict[int, dict[int, Fraction]] | AssignFail` (face index → {line coordinate → elevation}) plus `face_of_piece: dict[SegKey, int]`; `label_from_profile(profile: dict, s: int, e: Fraction) -> str`; `assign(layout, ridges, boundary_ridges, contours, *, budget=500_000) -> Assignment | AssignFail`; `Assignment(pieces: list[Piece], labels: list[str])`; `AssignFail(kind: str, site)`.

- [ ] **Step 1: Write the failing tests**

```python
# mcp_harness/tests/test_box_pleat_assign.py
from fractions import Fraction

from box_pleat.assign import (build_pieces, label_from_profile, faces, assign,
                              Assignment, AssignFail, Piece)
from box_pleat.contours import propagate
from box_pleat.layout import Layout, HingePoly
from box_pleat.skeleton import poly_ridges, ridge_points
from box_pleat.tree import contract


def _square():
    nodes = [{"id": 0, "parent_id": None, "length": 0.0},
             {"id": 1, "parent_id": 0, "length": 1.0},
             {"id": 2, "parent_id": 0, "length": 1.0},
             {"id": 3, "parent_id": 0, "length": 1.0}]
    tree = contract(nodes, [])
    cells = frozenset({(0, 0), (1, 0), (0, 1), (1, 1)})
    lay = Layout(2, [HingePoly(1, (1, 1), 1, cells)], [])
    ridges, on_b = poly_ridges(cells, (1, 1), 2)
    cont = propagate(lay, tree, ridge_points(ridges), on_b)
    return lay, ridges, on_b, cont


def test_label_from_profile():
    prof = {2: Fraction(1, 2), 3: Fraction(1), 4: Fraction(1, 2), 5: Fraction(0), 6: Fraction(1, 2)}
    assert label_from_profile(prof, 3, Fraction(1)) == "V"        # maximum
    assert label_from_profile(prof, 5, Fraction(0)) == "M"        # elevation 0
    assert label_from_profile(prof, 4, Fraction(1, 2)) == "F"     # slope
    assert label_from_profile(prof, 2, Fraction(1, 2)) == "F"     # one side extrapolated: slope
    assert label_from_profile({1: Fraction(3, 2), 2: Fraction(1), 3: Fraction(3, 2)}, 2, Fraction(1)) == "M"
    # neighbours farther than 1 are interpolated
    assert label_from_profile({0: Fraction(0), 4: Fraction(2)}, 2, Fraction(1)) == "F"
    assert label_from_profile({0: Fraction(2), 2: Fraction(1), 6: Fraction(3)}, 2, Fraction(1)) == "M"


def _area(cyc):
    return abs(sum(cyc[i][0] * cyc[(i + 1) % len(cyc)][1] - cyc[(i + 1) % len(cyc)][0] * cyc[i][1]
                   for i in range(len(cyc)))) / 2


def test_faces_of_the_square_are_four_equal_triangles():
    lay, ridges, on_b, cont = _square()
    pieces = build_pieces(lay, ridges, cont)
    fl = faces(2, pieces)
    assert len(fl) == 4
    assert all(_area(f) == 4 for f in fl)          # cycles keep degree-2 vertices


def test_pieces_cover_boundary_axials_ridges_and_no_hinges_for_one_flap():
    lay, ridges, on_b, cont = _square()
    pieces = build_pieces(lay, ridges, cont)
    assert not isinstance(pieces, AssignFail), pieces
    roles = {p.role for p in pieces}
    assert {"B", "axial", "ridge", "elev"} <= roles and "hinge" not in roles
    assert sum(1 for p in pieces if p.role == "B") == 16


def test_single_flap_is_the_waterbomb():
    lay, ridges, on_b, cont = _square()
    res = assign(lay, ridges, on_b, cont)
    assert isinstance(res, Assignment), res
    lab = {(p.a, p.b): l for p, l in zip(res.pieces, res.labels)}
    # centre column unfolded (plan view), horizontal axial folded, ridges all one way
    assert lab[((2, 1), (2, 2))] == "F" and lab[((1, 2), (2, 2))] == "M"
    diag = {l for (a, b), l in lab.items() if a[0] != b[0] and a[1] != b[1]}
    assert diag == {"V"}
    # corner slivers at elevation 1/2 are slopes
    assert lab[((1, 0), (1, 1))] == "F"
    inc = {}
    for p, l in zip(res.pieces, res.labels):
        if l in ("M", "V"):
            inc.setdefault(p.a, []).append(l)
            inc.setdefault(p.b, []).append(l)
    for v, labs in inc.items():
        if v[0] in (0, 4) or v[1] in (0, 4):
            continue
        assert abs(labs.count("M") - labs.count("V")) == 2, (v, labs)


def test_mirrored_pieces_share_a_label():
    lay, ridges, on_b, cont = _square()
    res = assign(lay, ridges, on_b, cont)
    lab = dict(zip(res.pieces, res.labels))
    for p in res.pieces:
        m = Piece(*sorted(((4 - p.a[0], p.a[1]), (4 - p.b[0], p.b[1]))), p.role)
        if m in lab:
            assert lab[m] == lab[p]


def test_stacked_rectangles_spine_extension_is_a_minimum():
    nodes = [{"id": 0, "parent_id": None, "length": 0.0},
             {"id": 1, "parent_id": 0, "length": 1.0},
             {"id": 2, "parent_id": 0, "length": 1.0},
             {"id": 3, "parent_id": 0, "length": 1.0}]
    tree = contract(nodes, [])
    lower = frozenset((c, r) for c in range(4) for r in range(2))
    upper = frozenset((c, r) for c in range(4) for r in range(2, 4))
    lay = Layout(4, [HingePoly(1, (2, 1), 1, lower), HingePoly(2, (2, 3), 1, upper)], [])
    ridges, on_b = [], []
    for p in lay.polys:
        i, b = poly_ridges(p.cells, p.tip, 4)
        ridges += i
        on_b += b
    cont = propagate(lay, tree, ridge_points(ridges), on_b)
    res = assign(lay, ridges, on_b, cont)
    assert isinstance(res, Assignment), res
    lab = {(p.a, p.b): l for p, l in zip(res.pieces, res.labels)}
    assert lab[((0, 2), (1, 2))] == "M" and lab[((1, 2), (2, 2))] == "M"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_box_pleat_assign.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'box_pleat.assign'`

- [ ] **Step 3: Write the implementation**

```python
# mcp_harness/box_pleat/assign.py
"""Crease pieces and their M/V assignment (spec §5.5 as amended by §10.3).

Contour pieces are labelled from the elevation PROFILE of the face of the
ridge+hinge subdivision they lie in (white side up: minimum -> M, maximum
-> V, slope -> F; elevation 0 always M); pieces on the centre column are F
(plan view); the paper boundary is B. Ridge and hinge pieces are one CSP
under Maekawa |M - V| = 2 at every interior vertex, mirrored pieces sharing
a variable. Kawasaki is checked, not solved.
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction

from .contours import is_boundary_seg, AXIS_ELEV

Point = tuple[int, int]


@dataclass(frozen=True)
class Piece:
    a: Point
    b: Point
    role: str          # B | axial | elev | ridge | hinge


@dataclass
class Assignment:
    pieces: list
    labels: list


@dataclass
class AssignFail:
    kind: str
    site: object


def _key(p, q):
    return (p, q) if p <= q else (q, p)


def _unit_pieces(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    n = max(abs(dx), abs(dy))
    sx, sy = (dx > 0) - (dx < 0), (dy > 0) - (dy < 0)
    return [_key((a[0] + k * sx, a[1] + k * sy), (a[0] + (k + 1) * sx, a[1] + (k + 1) * sy))
            for k in range(n)]


def build_pieces(layout, ridges: list, contours: dict):
    N, L = layout.N, 2 * layout.N
    pieces: dict = {}
    for i in range(L):
        for key in (((i, 0), (i + 1, 0)), ((i, L), (i + 1, L)),
                    ((0, i), (0, i + 1)), ((L, i), (L, i + 1))):
            k = _key(*key)
            pieces[k] = Piece(k[0], k[1], "B")
    for key, e in contours.items():
        if is_boundary_seg(key, N):
            continue
        pieces[key] = Piece(key[0], key[1], "axial" if e == AXIS_ELEV else "elev")
    for a, b in ridges:
        for key in _unit_pieces(a, b):
            if key in contours:
                return AssignFail("ridge_on_contour", key)
            pieces[key] = Piece(key[0], key[1], "ridge")
    owner = layout.cell_owner()
    for (c, r), o in owner.items():
        for nb, corner1, corner2 in (((c + 1, r), (c + 1, r), (c + 1, r + 1)),
                                     ((c, r + 1), (c, r + 1), (c + 1, r + 1))):
            if nb in owner and owner[nb] != o:
                X1, Y1, X2, Y2 = 2 * corner1[0], 2 * corner1[1], 2 * corner2[0], 2 * corner2[1]
                mid = ((X1 + X2) // 2, (Y1 + Y2) // 2)
                for p, q in (((X1, Y1), mid), (mid, (X2, Y2))):
                    key = _key(p, q)
                    if key in contours:
                        return AssignFail("hinge_on_contour", key)
                    if key in pieces and pieces[key].role == "ridge":
                        return AssignFail("hinge_on_ridge", key)
                    pieces[key] = Piece(key[0], key[1], "hinge")
    return [pieces[k] for k in sorted(pieces)]


# --- faces of the ridge + hinge + boundary subdivision ------------------------

def faces(N, pieces) -> list:
    """CCW vertex cycles of the interior faces of the planar graph formed by
    the B, ridge and hinge pieces (contour pieces are not walls)."""
    adj = defaultdict(list)
    for p in pieces:
        if p.role in ("B", "ridge", "hinge"):
            adj[p.a].append(p.b)
            adj[p.b].append(p.a)
    for u in adj:
        adj[u].sort(key=lambda w: math.atan2(w[1] - u[1], w[0] - u[0]))
    used, out = set(), []
    for u in sorted(adj):
        for v in adj[u]:
            if (u, v) in used:
                continue
            cyc, a, b = [], u, v
            while (a, b) not in used:
                used.add((a, b))
                cyc.append(a)
                nb = adj[b]
                c = nb[(nb.index(a) - 1) % len(nb)]
                a, b = b, c
            area = 0
            for i in range(len(cyc)):
                x1, y1 = cyc[i]
                x2, y2 = cyc[(i + 1) % len(cyc)]
                area += x1 * y2 - x2 * y1
            if area > 0:
                out.append(cyc)
    return out


def _inside(cyc, x, y) -> bool:
    inside = False
    n = len(cyc)
    for i in range(n):
        x1, y1 = cyc[i]
        x2, y2 = cyc[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xi = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if xi > x:
                inside = not inside
    return inside


def profiles(N, pieces, contours, face_list):
    """Per-face {coordinate -> elevation} from the contour pieces inside it,
    and the face index of every contour piece."""
    boxes = [(min(x for x, _ in c), max(x for x, _ in c),
              min(y for _, y in c), max(y for _, y in c)) for c in face_list]
    prof: dict = defaultdict(dict)
    orient: dict = {}
    face_of: dict = {}
    for p in pieces:
        if p.role not in ("axial", "elev"):
            continue
        key = (p.a, p.b)
        mx, my = (p.a[0] + p.b[0]) / 2, (p.a[1] + p.b[1]) / 2
        horizontal = p.a[1] == p.b[1]
        fi = None
        for k, (c, bx) in enumerate(zip(face_list, boxes)):
            if bx[0] <= mx <= bx[1] and bx[2] <= my <= bx[3] and _inside(c, mx, my):
                fi = k
                break
        if fi is None:
            return AssignFail("piece_outside_faces", key), None
        if orient.setdefault(fi, horizontal) != horizontal:
            return AssignFail("mixed_contour_directions", (fi, key)), None
        s = p.a[1] if horizontal else p.a[0]
        e = contours[key]
        if prof[fi].setdefault(s, e) != e:
            return AssignFail("profile_conflict", (fi, s, prof[fi][s], e)), None
        face_of[key] = fi
    return dict(prof), face_of


def _side(profile: dict, s: int, e: Fraction, sign: int, K: int):
    for k in range(1, K + 1):
        if s + sign * k in profile:
            return e + (profile[s + sign * k] - e) / k
    return None


def label_from_profile(profile: dict, s: int, e: Fraction) -> str:
    if e == 0:
        return "M"
    K = max(profile) - min(profile) + 1 if profile else 1
    lo, hi = _side(profile, s, e, -1, K), _side(profile, s, e, 1, K)
    if lo is None and hi is None:
        return "F"
    if lo is None:
        lo = e + (e - hi)
    if hi is None:
        hi = e + (e - lo)
    if lo > e and hi > e:
        return "M"
    if lo < e and hi < e:
        return "V"
    return "F"


# --- Maekawa CSP -------------------------------------------------------------

def _maekawa_feasible(D: int, k: int) -> bool:
    """Exists S in [-k, k], S == k (mod 2), with |D + 2S| == 2."""
    if D % 2:
        return False
    for target in (2, -2):
        S2 = target - D
        if S2 % 2 == 0:
            S = S2 // 2
            if -k <= S <= k and (S - k) % 2 == 0:
                return True
    return False


def _kawasaki_ok(vertex, nbr_pts) -> bool:
    if len(nbr_pts) % 2:
        return False
    angs = sorted(math.atan2(q[1] - vertex[1], q[0] - vertex[0]) for q in nbr_pts)
    total = 0.0
    for i in range(len(angs)):
        a = (angs[(i + 1) % len(angs)] - angs[i]) % (2 * math.pi)
        total += a if i % 2 == 0 else -a
    return abs(total) < 1e-9


def assign(layout, ridges: list, boundary_ridges: list, contours: dict, *,
           budget: int = 500_000):
    N = layout.N
    pieces = build_pieces(layout, ridges, contours)
    if isinstance(pieces, AssignFail):
        return pieces
    face_list = faces(N, pieces)
    prof, face_of = profiles(N, pieces, contours, face_list)
    if isinstance(prof, AssignFail):
        return prof
    labels: list = [None] * len(pieces)
    idx = {(p.a, p.b): i for i, p in enumerate(pieces)}
    for i, p in enumerate(pieces):
        if p.role == "B":
            labels[i] = "B"
        elif p.role in ("axial", "elev"):
            if p.a[0] == p.b[0] == N:
                labels[i] = "F"
            else:
                horizontal = p.a[1] == p.b[1]
                s = p.a[1] if horizontal else p.a[0]
                labels[i] = label_from_profile(prof[face_of[(p.a, p.b)]], s, contours[(p.a, p.b)])
    var_of: dict = {}
    for i, p in enumerate(pieces):
        if labels[i] is not None:
            continue
        m = _key((2 * N - p.a[0], p.a[1]), (2 * N - p.b[0], p.b[1]))
        var_of[i] = min(i, idx.get(m, i))
    inc: dict = {}
    for i, p in enumerate(pieces):
        inc.setdefault(p.a, []).append(i)
        inc.setdefault(p.b, []).append(i)
    interior = [v for v in inc if not (v[0] in (0, 2 * N) or v[1] in (0, 2 * N))]
    value: dict = {}

    def counts(v):
        M = V = k = 0
        for i in inc[v]:
            lab = labels[i] if labels[i] is not None else value.get(var_of[i])
            if lab == "M":
                M += 1
            elif lab == "V":
                V += 1
            elif lab is None:
                k += 1
        return M, V, k

    def feasible(v):
        M, V, k = counts(v)
        if k == 0 and M + V == 0:
            return True
        return _maekawa_feasible(M - V, k)

    for v in interior:
        if not feasible(v):
            return AssignFail("maekawa_fixed", v)
    touching: dict = {}
    for v in interior:
        for i in inc[v]:
            if i in var_of:
                touching.setdefault(var_of[i], set()).add(v)
    nodes = [budget]

    def free_vars_at(v):
        return sorted({var_of[i] for i in inc[v] if i in var_of and var_of[i] not in value})

    def pick():
        best = None
        for v in interior:
            fv = free_vars_at(v)
            if fv and (best is None or len(fv) < len(best[1])):
                best = (v, fv)
        return best

    def prefer(var):
        p = pieces[var]
        if p.role == "ridge":
            d = (p.b[0] - p.a[0], p.b[1] - p.a[1])
            for q in (p.a, p.b):
                for j in inc[q]:
                    if j == var or pieces[j].role != "ridge":
                        continue
                    dj = (pieces[j].b[0] - pieces[j].a[0], pieces[j].b[1] - pieces[j].a[1])
                    if dj in (d, (-d[0], -d[1])) and var_of.get(j) in value:
                        return ["V", "M"] if value[var_of[j]] == "M" else ["M", "V"]
            return ["V", "M"]
        return ["M", "V"]

    def rec():
        nodes[0] -= 1
        if nodes[0] < 0:
            raise RuntimeError("budget")
        pk = pick()
        if pk is None:
            return True
        v, fv = pk
        var = fv[0]
        for lab in prefer(var):
            value[var] = lab
            if all(feasible(w) for w in touching.get(var, ())):
                if rec():
                    return True
            del value[var]
        return False

    try:
        ok = rec()
    except RuntimeError:
        return AssignFail("budget", budget)
    if not ok:
        return AssignFail("unsat", sorted(v for v in interior if not feasible(v))[:5])
    for i in var_of:
        labels[i] = value[var_of[i]]
    for v in interior:
        nb = [pieces[i].b if pieces[i].a == v else pieces[i].a
              for i in inc[v] if labels[i] in ("M", "V")]
        if nb and not _kawasaki_ok(v, nb):
            return AssignFail("kawasaki", v)
    return Assignment(pieces, labels)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_box_pleat_assign.py -v`
Expected: 6 passed. `test_single_flap_is_the_waterbomb` is the physical check: one unfolded midline (the centre column), one folded midline, four diagonals the other way — the real Waterbomb base. `test_stacked_rectangles_spine_extension_is_a_minimum` checks that the face profile (not the same-interval neighbour) decides the label next to a node.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/box_pleat/assign.py mcp_harness/tests/test_box_pleat_assign.py
git commit -m "box_pleat: face-profile elevation labels and Maekawa CSP for ridges and hinges

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: `emit.py` + `compile.py` — FOLD output and the one entry point; end-to-end on all 17

**Files:**
- Create: `mcp_harness/box_pleat/emit.py`
- Create: `mcp_harness/box_pleat/compile.py`
- Test: `mcp_harness/tests/test_box_pleat_emit.py`
- Test: `mcp_harness/tests/test_box_pleat_e2e.py`

**Interfaces:**
- Consumes: everything above.
- Produces: `to_fold(layout, assignment) -> dict`; `compile_tree(nodes, pairs, *, max_N=None, pack_budget=200_000, assign_budget=500_000) -> Result`; `Result(fold, layout, ridges, boundary_ridges, contours, assignment, stage_reached, failure, timings, tree)`; `STAGES = ("tree", "pack", "skeleton", "contours", "assign", "emit")`.

- [ ] **Step 1: Write the failing tests**

```python
# mcp_harness/tests/test_box_pleat_emit.py
import json

import cp_audit
import flat_fold
from box_pleat.compile import compile_tree, STAGES
from test_box_pleat_tree import toy_nodes


def test_toy_compiles_to_a_fold_that_audits_clean():
    nodes, pairs = toy_nodes()
    res = compile_tree(nodes, pairs)
    assert res.stage_reached == "emit", (res.stage_reached, res.failure)
    f = res.fold
    assert f["file_spec"] == 1.1 and "creasePattern" in f["frame_classes"]
    assert len(f["edges_vertices"]) == len(f["edges_assignment"]) == len(f["edges_foldAngle"])
    assert set(f["edges_assignment"]) <= {"M", "V", "B"}
    assert all(0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 for x, y in f["vertices_coords"])
    rep = cp_audit.audit_fold(f)
    bad = [(v.vertex, v.m, v.v) for v in rep.vertices if abs(v.m - v.v) != 2]
    assert not bad, bad
    ff = flat_fold.flat_fold(f)
    assert max(ff.closure.edge_errors, default=0.0) <= flat_fold.CLOSURE_EPS
    bp = f["box_pleat"]
    assert bp["N"] == 6 and set(bp["edge_roles"]) <= {"axial", "elev", "ridge", "hinge", "B"}
    assert set(map(int, bp["leaf_tips"])) == {2, 3, 4, 5, 6}


def test_fold_is_byte_identical_on_rerun():
    nodes, pairs = toy_nodes()
    a = json.dumps(compile_tree(nodes, pairs).fold, sort_keys=True)
    b = json.dumps(compile_tree(nodes, pairs).fold, sort_keys=True)
    assert a == b


def test_non_integral_tree_fails_at_tree_stage():
    nodes = [{"id": 0, "parent_id": None, "length": 0.0},
             {"id": 1, "parent_id": 0, "length": 1.0},
             {"id": 2, "parent_id": 0, "length": 1.0},
             {"id": 3, "parent_id": 0, "length": 2.3336}]
    res = compile_tree(nodes, [])
    assert res.stage_reached == "tree" and res.fold is None
    assert type(res.failure).__name__ == "NonIntegral"
    assert STAGES[0] == "tree"
```

```python
# mcp_harness/tests/test_box_pleat_e2e.py
"""All 17 committed trees through the box-pleat compiler and the validators.

Spec §6 pre-registered bar. This is the ONLY box-pleat test that may start
the JVM linter, and that test is marked slow.
"""
import json

import pytest

import cp_audit
import flat_fold
from box_pleat.compile import compile_tree
from test_box_pleat_tree import RULE6

SUBJECTS = [e["subject"] for e in json.load(open(RULE6))]


def _entry(subject):
    return next(e for e in json.load(open(RULE6)) if e["subject"] == subject)


@pytest.mark.parametrize("subject", SUBJECTS)
def test_subject_reaches_emit_and_audits_clean(subject):
    e = _entry(subject)
    res = compile_tree(e["requested"], e["pairs"], pack_budget=2_000_000)
    assert res.stage_reached == "emit", (subject, res.stage_reached, res.failure)
    rep = cp_audit.audit_fold(res.fold)
    bad = [(v.vertex, v.m, v.v) for v in rep.vertices if abs(v.m - v.v) != 2]
    assert not bad, (subject, bad[:5])
    ff = flat_fold.flat_fold(res.fold)
    assert max(ff.closure.edge_errors, default=0.0) <= flat_fold.CLOSURE_EPS, subject


@pytest.mark.slow
@pytest.mark.parametrize("subject", SUBJECTS)
def test_subject_lints_pass_or_benign(subject):
    import lint_verdict
    import linter_server
    e = _entry(subject)
    res = compile_tree(e["requested"], e["pairs"], pack_budget=2_000_000)
    assert res.fold is not None, (subject, res.failure)
    text = linter_server.validate_flat_foldability(fold_json_string=json.dumps(res.fold))
    parsed = lint_verdict.parse_verdict(text)
    label = {"pass": "PASS", "classified": parsed["label"]}.get(parsed["kind"], parsed["kind"])
    assert label in ("PASS", "BENIGN"), (subject, label, text[:300])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_box_pleat_emit.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'box_pleat.compile'`

- [ ] **Step 3: Write the implementation**

```python
# mcp_harness/box_pleat/emit.py
"""Layout + assignment -> FOLD 1.1 dict (spec §5.6).

Unfolded (F) pieces are dropped; collinear consecutive pieces with equal
label and role through degree-2 vertices are merged; vertices and edges are
sorted so equal inputs give byte-identical output.
"""
from __future__ import annotations

from collections import defaultdict


def _merge_runs(pieces, labels):
    keep = [(p, l) for p, l in zip(pieces, labels) if l != "F"]
    inc = defaultdict(list)
    for i, (p, l) in enumerate(keep):
        inc[p.a].append(i)
        inc[p.b].append(i)
    parent = list(range(len(keep)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for v, ids in inc.items():
        if len(ids) != 2:
            continue
        i, j = ids
        (p, l), (q, m) = keep[i], keep[j]
        if l != m or p.role != q.role:
            continue
        d1 = (p.b[0] - p.a[0], p.b[1] - p.a[1])
        d2 = (q.b[0] - q.a[0], q.b[1] - q.a[1])
        if d1[0] * d2[1] - d1[1] * d2[0] == 0:
            parent[find(i)] = find(j)
    groups = defaultdict(list)
    for i in range(len(keep)):
        groups[find(i)].append(i)
    out = []
    for ids in groups.values():
        pts = defaultdict(int)
        for i in ids:
            pts[keep[i][0].a] += 1
            pts[keep[i][0].b] += 1
        ends = sorted(p for p, c in pts.items() if c == 1)
        if len(ends) != 2:
            for i in ids:
                p, l = keep[i]
                out.append((p.a, p.b, l, p.role))
            continue
        out.append((ends[0], ends[1], keep[ids[0]][1], keep[ids[0]][0].role))
    return out


def to_fold(layout, assignment) -> dict:
    N = layout.N
    runs = _merge_runs(assignment.pieces, assignment.labels)
    verts = sorted({a for a, _, _, _ in runs} | {b for _, b, _, _ in runs})
    vid = {v: i for i, v in enumerate(verts)}
    runs.sort(key=lambda r: (vid[r[0]], vid[r[1]]))
    angle = {"M": -180.0, "V": 180.0, "B": 0.0}
    return {
        "file_spec": 1.1,
        "file_creator": "box_pleat",
        "frame_classes": ["creasePattern"],
        "vertices_coords": [[x / (2 * N), y / (2 * N)] for x, y in verts],
        "edges_vertices": [[vid[a], vid[b]] for a, b, _, _ in runs],
        "edges_assignment": [l for _, _, l, _ in runs],
        "edges_foldAngle": [angle[l] for _, _, l, _ in runs],
        "box_pleat": {
            "N": N,
            "unit": 1.0 / N,
            "edge_roles": [role for _, _, _, role in runs],
            "leaf_tips": {str(p.leaf_id): [p.tip[0] / N, p.tip[1] / N]
                          for p in layout.polys},
        },
    }
```

```python
# mcp_harness/box_pleat/compile.py
"""The one entry point: metric tree -> box-pleated base (spec §5.7)."""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from . import tree as _tree
from .assign import assign, AssignFail, Assignment
from .contours import propagate, ContourFail
from .emit import to_fold
from .pack import pack, PackFail
from .skeleton import poly_ridges, river_ridges, ridge_points, SkeletonFail

STAGES = ("tree", "pack", "skeleton", "contours", "assign", "emit")


@dataclass
class Result:
    fold: dict | None = None
    layout: object = None
    ridges: list = field(default_factory=list)
    boundary_ridges: list = field(default_factory=list)
    contours: dict = field(default_factory=dict)
    assignment: Assignment | None = None
    stage_reached: str = "tree"
    failure: object = None
    timings: dict = field(default_factory=dict)
    tree: object = None


def compile_tree(nodes, pairs, *, max_N=None, pack_budget=200_000,
                 assign_budget=500_000) -> Result:
    res = Result()
    t0 = time.perf_counter()

    def tick(stage):
        nonlocal t0
        now = time.perf_counter()
        res.timings[stage] = round(now - t0, 4)
        t0 = now

    try:
        res.tree = _tree.contract(nodes, pairs)
    except (_tree.NonIntegral, ValueError) as exc:
        res.failure = exc
        return res
    tick("tree")
    res.stage_reached = "pack"
    lay = pack(res.tree, max_N=max_N, budget=pack_budget)
    tick("pack")
    if isinstance(lay, PackFail):
        res.failure = lay
        return res
    res.layout = lay
    res.stage_reached = "skeleton"
    ridges, boundary = [], []
    try:
        for p in lay.polys:
            i, b = poly_ridges(p.cells, p.tip, lay.N)
            ridges += i
            boundary += b
        for rv in lay.rivers:
            ridges += river_ridges(rv.cells, rv.width)
    except ValueError as exc:
        res.failure = SkeletonFail(None, str(exc))
        return res
    tick("skeleton")
    res.ridges, res.boundary_ridges = ridges, boundary
    res.stage_reached = "contours"
    try:
        cont = propagate(lay, res.tree, ridge_points(ridges), boundary)
    except ValueError as exc:
        res.failure = ContourFail("error", str(exc))
        return res
    tick("contours")
    if isinstance(cont, ContourFail):
        res.failure = cont
        return res
    res.contours = cont
    res.stage_reached = "assign"
    asg = assign(lay, ridges, boundary, cont, budget=assign_budget)
    tick("assign")
    if isinstance(asg, AssignFail):
        res.failure = asg
        return res
    res.assignment = asg
    res.stage_reached = "emit"
    res.fold = to_fold(lay, asg)
    tick("emit")
    return res
```

- [ ] **Step 4: Run the fast tests**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_box_pleat_emit.py tests/test_box_pleat_e2e.py -m "not slow" -v`
Expected: `test_box_pleat_emit.py` 3 passed — the toy is the golden; a failure there is a bug in Tasks 2–6, and the way to find it is the SVG from Task 8's `render_svg` (which works on a partial `Result`), not a looser assertion. `test_subject_reaches_emit_and_audits_clean` runs 17 cases; **some may fail** at `contours` (collision / error), `assign` (unsat / kawasaki / hinge_on_contour) or `cp_audit`. That is an allowed outcome of this task: record every failing subject with its `stage_reached` and failure kind in the commit message and carry them into the probe's table. Do NOT edit the bar; raise `pack_budget` in the test only.

- [ ] **Step 5: Run the slow lint tier once**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_box_pleat_e2e.py -m slow -v`
Expected: 17 cases; note which are PASS / BENIGN / REAL / MIXED. Same rule: record, don't loosen.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/box_pleat/emit.py mcp_harness/box_pleat/compile.py mcp_harness/tests/test_box_pleat_emit.py mcp_harness/tests/test_box_pleat_e2e.py
git commit -m "box_pleat: FOLD emitter and compile_tree entry point; e2e bar on the 17 trees

<one line per subject that does not reach emit or fails a validator: subject / stage / failure kind>

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 8: `probe_box_pleat.py` — the 17-way comparison and evidence directory

**Files:**
- Create: `mcp_harness/probe_box_pleat.py`
- Create: `docs/superpowers/evidence/2026-09-20-box-pleat/README.md` (by hand, after the run)
- Generated: `docs/superpowers/evidence/2026-09-20-box-pleat/{table.md,results.json,svg/*.svg}`
- Test: `mcp_harness/tests/test_probe_box_pleat.py`

**Interfaces:**
- Consumes: `compile_tree` (Task 7); `server.draft_and_compile_full_base`, `server.read_base`; `cp_audit.audit_fold`; `flat_fold.flat_fold`; `layer_order.layer_order`; `linter_server.validate_flat_foldability`; `lint_verdict.parse_verdict`; `paper_coverage.hull_coverage`.
- Produces: `row_for(entry, *, treemaker=True, lint=True) -> dict` (one table row; the key `_result` holds the `Result`), `tip_hull_coverage(points) -> float | None`, `render_svg(result) -> str`, `write_table(rows) -> str`, CLI `python probe_box_pleat.py --out DIR [--subjects a,b] [--no-treemaker] [--no-lint]`.

- [ ] **Step 1: Write the failing tests**

```python
# mcp_harness/tests/test_probe_box_pleat.py
from box_pleat.compile import compile_tree
from probe_box_pleat import row_for, tip_hull_coverage, render_svg, write_table
from test_box_pleat_tree import toy_nodes


def test_tip_hull_coverage():
    assert tip_hull_coverage([(0, 0), (1, 0), (1, 1), (0, 1)]) == 1.0
    assert tip_hull_coverage([(0, 0), (1, 0), (0.5, 0.5)]) == 0.25
    assert tip_hull_coverage([(0, 0), (1, 1)]) is None


def test_row_without_treemaker_or_lint_has_every_column():
    nodes, pairs = toy_nodes()
    entry = {"subject": "toy", "requested": nodes, "pairs": pairs}
    row = row_for(entry, treemaker=False, lint=False)
    for k in ("subject", "leaves", "rivers", "unit", "N_lb", "N", "scale_bp",
              "scale_tm", "ratio", "hull_coverage", "tip_hull_coverage",
              "flap_width_units", "stage_reached", "maekawa_defects",
              "lint_class", "flat_fold_ok", "layer_order", "pack_ms", "failure"):
        assert k in row, k
    assert row["N"] == 6 and row["scale_tm"] is None and row["lint_class"] is None
    if row["stage_reached"] == "emit":
        assert row["maekawa_defects"] == 0 and row["flat_fold_ok"] is True


def test_svg_and_table_render_even_on_a_partial_result():
    nodes, pairs = toy_nodes()
    res = compile_tree(nodes, pairs)
    svg = render_svg(res)
    assert svg.startswith("<svg") and "<rect" in svg
    md = write_table([row_for({"subject": "toy", "requested": nodes, "pairs": pairs},
                              treemaker=False, lint=False)])
    assert "| toy |" in md and "scale_bp" in md
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_probe_box_pleat.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'probe_box_pleat'`

- [ ] **Step 3: Write the implementation**

```python
# mcp_harness/probe_box_pleat.py
"""The 17-way comparison: box-pleat compiler vs the TreeMaker serve path.

Spec: docs/superpowers/specs/2026-09-20-box-pleat-compiler-design.md §6.

    cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python probe_box_pleat.py \
        --out ../docs/superpowers/evidence/2026-09-20-box-pleat

Sequential, no multiprocessing: a standalone script, never run under the
stdio MCP server. TreeMaker and the JVM linter are imported function-locally
(order_rank.py:12-21 measured +8.89 s/serve from hoisting them).
"""
from __future__ import annotations

import argparse
import json
import os

from box_pleat.compile import compile_tree
from box_pleat.tree import contract, NonIntegral

RULE6 = os.path.join(os.path.dirname(__file__), "..", "docs", "superpowers", "evidence",
                     "2026-09-08-vlm-tree-authoring", "data", "rule6_serve.json")

COLUMNS = ("subject", "leaves", "rivers", "unit", "N_lb", "N", "scale_bp", "scale_tm",
           "ratio", "hull_coverage", "tip_hull_coverage", "tm_tip_hull_coverage",
           "flap_width_units", "stage_reached", "maekawa_defects", "lint_class",
           "flat_fold_ok", "layer_order", "pack_ms", "failure", "tm_error")


def tip_hull_coverage(points):
    pts = sorted(set((float(x), float(y)) for x, y in points))
    if len(pts) < 3:
        return None

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    hull = lo[:-1] + hi[:-1]
    if len(hull) < 3:
        return None
    area = 0.0
    for i in range(len(hull)):
        x1, y1 = hull[i]
        x2, y2 = hull[(i + 1) % len(hull)]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def _lint_class(fold: dict):
    import lint_verdict
    import linter_server
    text = linter_server.validate_flat_foldability(fold_json_string=json.dumps(fold))
    parsed = lint_verdict.parse_verdict(text)
    return {"pass": "PASS", "classified": parsed["label"],
            "legacy_failed": "LEGACY-FAILED", "error": "LINT-ERROR"}.get(
                parsed["kind"], "LINT-ERROR")


def _treemaker(entry):
    import server
    fold_str = server.draft_and_compile_full_base(entry["requested"], entry["pairs"])
    if fold_str.startswith("ERROR:"):
        return None, None, fold_str[:120]
    rb = json.loads(server.read_base())
    locs = rb.get("locs") or []
    cov = tip_hull_coverage([(l[1], l[2]) for l in locs]) if locs else None
    return rb.get("scale"), cov, None


def row_for(entry, *, treemaker=True, lint=True) -> dict:
    row = {k: None for k in COLUMNS}
    row["subject"] = entry["subject"]
    try:
        tree = contract(entry["requested"], entry["pairs"])
    except (NonIntegral, ValueError) as exc:
        row["stage_reached"], row["failure"] = "tree", f"{type(exc).__name__}: {exc}"
        row["_result"] = None
        return row
    row["leaves"], row["rivers"] = len(tree.leaves), len(tree.branches)
    row["unit"], row["N_lb"] = round(tree.unit, 6), tree.n_lb()
    res = compile_tree(entry["requested"], entry["pairs"], pack_budget=2_000_000)
    row["pack_ms"] = round(1000 * res.timings.get("pack", 0.0), 1)
    row["stage_reached"] = res.stage_reached
    if res.failure is not None:
        row["failure"] = f"{type(res.failure).__name__}: {res.failure}"[:160]
    if res.layout is not None:
        row["N"] = res.layout.N
        row["scale_bp"] = round(1.0 / res.layout.N, 6)
        row["tip_hull_coverage"] = tip_hull_coverage(
            [(p.tip[0] / res.layout.N, p.tip[1] / res.layout.N) for p in res.layout.polys])
        row["flap_width_units"] = 1
    if res.fold is not None:
        import cp_audit
        import flat_fold
        import layer_order
        import paper_coverage
        rep = cp_audit.audit_fold(res.fold)
        row["maekawa_defects"] = sum(1 for v in rep.vertices if abs(v.m - v.v) != 2)
        ff = flat_fold.flat_fold(res.fold)
        row["flat_fold_ok"] = max(ff.closure.edge_errors, default=0.0) <= flat_fold.CLOSURE_EPS
        try:
            layer_order.layer_order(ff)
            row["layer_order"] = "consistent"
        except layer_order.AmbiguousStack:
            row["layer_order"] = "ambiguous"
        except Exception as exc:                       # noqa: BLE001
            row["layer_order"] = f"error: {type(exc).__name__}"
        hc = paper_coverage.hull_coverage(res.fold)
        row["hull_coverage"] = round(hc["coverage"], 4) if hc else None
        if lint:
            row["lint_class"] = _lint_class(res.fold)
    if treemaker:
        scale, cov, err = _treemaker(entry)
        if scale is not None:
            row["scale_tm"] = round(scale * tree.unit, 6)
            if row["scale_bp"]:
                row["ratio"] = round(row["scale_bp"] / row["scale_tm"], 3)
        row["tm_tip_hull_coverage"] = cov
        row["tm_error"] = err
    row["_result"] = res
    return row


_ROLE_COLOUR = {"axial": "#2a7", "elev": "#a72", "ridge": "#c33", "hinge": "#36c", "B": "#000"}


def render_svg(res) -> str:
    lay = getattr(res, "layout", None)
    if lay is None:
        return "<svg xmlns='http://www.w3.org/2000/svg' width='10' height='10'></svg>"
    S = 400
    u = S / lay.N
    out = [f"<svg xmlns='http://www.w3.org/2000/svg' width='{S}' height='{S}' viewBox='0 0 {S} {S}'>"]
    for p in lay.polys:
        for (c, r) in p.cells:
            out.append(f"<rect x='{c * u:.1f}' y='{(lay.N - 1 - r) * u:.1f}' width='{u:.1f}' "
                       f"height='{u:.1f}' fill='hsl({(p.leaf_id * 47) % 360},60%,85%)' stroke='none'/>")
    for rv in lay.rivers:
        for (c, r) in rv.cells:
            out.append(f"<rect x='{c * u:.1f}' y='{(lay.N - 1 - r) * u:.1f}' width='{u:.1f}' "
                       f"height='{u:.1f}' fill='#ddd' stroke='none'/>")
    if getattr(res, "assignment", None) is not None:
        for piece, lab in zip(res.assignment.pieces, res.assignment.labels):
            if lab == "F":
                continue
            (ax, ay), (bx, by) = piece.a, piece.b
            dash = " stroke-dasharray='4 3'" if lab == "V" else ""
            out.append(f"<line x1='{ax * u / 2:.1f}' y1='{S - ay * u / 2:.1f}' "
                       f"x2='{bx * u / 2:.1f}' y2='{S - by * u / 2:.1f}' "
                       f"stroke='{_ROLE_COLOUR[piece.role]}' stroke-width='1.2'{dash}/>")
    else:
        for a, b in getattr(res, "ridges", []):
            out.append(f"<line x1='{a[0] * u / 2:.1f}' y1='{S - a[1] * u / 2:.1f}' "
                       f"x2='{b[0] * u / 2:.1f}' y2='{S - b[1] * u / 2:.1f}' stroke='#c33' stroke-width='1'/>")
        for (a, b), e in getattr(res, "contours", {}).items():
            col = "#2a7" if e == 0 else "#a72"
            out.append(f"<line x1='{a[0] * u / 2:.1f}' y1='{S - a[1] * u / 2:.1f}' "
                       f"x2='{b[0] * u / 2:.1f}' y2='{S - b[1] * u / 2:.1f}' stroke='{col}' stroke-width='0.6'/>")
    for p in lay.polys:
        out.append(f"<circle cx='{p.tip[0] * u:.1f}' cy='{S - p.tip[1] * u:.1f}' r='3' fill='#000'/>")
    out.append("</svg>")
    return "\n".join(out)


def write_table(rows) -> str:
    cols = list(COLUMNS)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        lines.append("| " + " | ".join("" if r.get(c) is None else str(r[c]) for c in cols) + " |")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--subjects", default="")
    ap.add_argument("--no-treemaker", action="store_true")
    ap.add_argument("--no-lint", action="store_true")
    a = ap.parse_args(argv)
    entries = json.load(open(RULE6))
    if a.subjects:
        keep = set(a.subjects.split(","))
        entries = [e for e in entries if e["subject"] in keep]
    os.makedirs(os.path.join(a.out, "svg"), exist_ok=True)
    rows = []
    for e in entries:
        row = row_for(e, treemaker=not a.no_treemaker, lint=not a.no_lint)
        res = row.pop("_result")
        with open(os.path.join(a.out, "svg", f"{e['subject']}.svg"), "w") as fh:
            fh.write(render_svg(res))
        rows.append(row)
        print(f"{row['subject']:11s} stage={row['stage_reached']:8s} N={row['N']} "
              f"scale_bp={row['scale_bp']} scale_tm={row['scale_tm']} ratio={row['ratio']} "
              f"lint={row['lint_class']} maekawa={row['maekawa_defects']} "
              f"failure={row['failure']}", flush=True)
    with open(os.path.join(a.out, "results.json"), "w") as fh:
        json.dump(rows, fh, indent=2, sort_keys=True)
    with open(os.path.join(a.out, "table.md"), "w") as fh:
        fh.write(write_table(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the probe's unit tests**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_probe_box_pleat.py -v`
Expected: 3 passed

- [ ] **Step 5: Run the probe on all 17**

Run:
```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python probe_box_pleat.py --out ../docs/superpowers/evidence/2026-09-20-box-pleat 2>&1 | tail -25
```
Expected: 17 lines, one per subject, then `table.md`, `results.json`, `svg/` in the evidence dir. The TreeMaker side spawns compiles (seconds each); the JVM lint adds ~0.2 s per fold. Under 5 minutes total. If `server` import fails on the `.so`, re-check the worktree symlinks in "How to run tests".

- [ ] **Step 6: Write the evidence README by hand from the numbers**

Create `docs/superpowers/evidence/2026-09-20-box-pleat/README.md` with exactly these sections, every number copied from `table.md`:

```markdown
# Box-pleating compiler vs TreeMaker on the 17 committed trees (2026-09-20)

Regenerate: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python probe_box_pleat.py --out ../docs/superpowers/evidence/2026-09-20-box-pleat`

Spec: docs/superpowers/specs/2026-09-20-box-pleat-compiler-design.md §6 (pre-registered bar), §10 (amendments).

## Bar

- reached `emit`: <n>/17
- `maekawa_defects == 0`: <n>/17
- `lint_class ∈ {PASS, BENIGN}`: <n>/17
- `flat_fold_ok`: <n>/17

## Scale penalty (ratio = scale_bp / scale_tm, both paper-per-grid-unit)

min <x> (<subject>), median <x>, max <x> (<subject>). Lang gives no percentage: box pleating "must be, by definition, less efficient" than circle/river packing, but "the penalty is often very small" (Ch. 13, p. 573). Report the measured spread; <k> subjects read ratio >= 1.0.

## Coverage

`hull_coverage` reads 1.000 on every emitted fold (the B border is the square; measured, not assumed). `tip_hull_coverage` (leaf-tip hull, the 09-09 artifact's metric): min/median/max, vs TreeMaker's `tm_tip_hull_coverage`.

## Failures, by stage

<one line per subject that did not reach emit: subject / stage / failure kind / the B macro this site calls for: level shifter for a contour collision, stub for an unfillable gap, Pythagorean stretch for a corner collision at N_lb>

## Table

(paste table.md)
```

- [ ] **Step 7: Commit**

```bash
git add mcp_harness/probe_box_pleat.py mcp_harness/tests/test_probe_box_pleat.py docs/superpowers/evidence/2026-09-20-box-pleat
git commit -m "box_pleat: 17-way probe vs TreeMaker; evidence table, svgs, README

<paste the four Bar lines and the ratio min/median/max here>

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Self-review against the spec

- **§0 prior art** — carried by the spec. ✓
- **§2 decisions** — 1: Task 8 standalone probe; 2: Tasks 5–7 full depth; 3: Task 1 unit + refusal; 4 (as amended §10.2): Task 3 mirror, Task 4 half-square, Task 6 centre-column `F`; 5: Task 4 backtracking, Tasks 2/5/6 Ch. 13, Task 3 `Layout`. ✓
- **§4 `Layout` and invariants** — Task 3 `validate()`: partition, tip-square, connectivity, constant width (necessary check), mirror, path (Chebyshev), hub regions, plus the §10.2 centre-column ridge rule; `gadgets` present and unused; `contours` filled by Task 5. ✓
- **§5.1** Task 1. **§5.2 / §10.4** Task 4 (rivers never grow, no stubs, cell-wise gap fill). **§5.3 / §10.1** Task 2 (`poly_ridges` mirroring; off-half-grid → `ValueError` → `SkeletonFail` in Task 7). **§5.4 / §10.3** Task 5 (raw-edge axials, tip launches with skips, dense run seeding, collision). **§5.5 / §10.3** Task 6 (face profiles, minimum → `M` / maximum → `V`, centre `F`, boundary `B`, Maekawa CSP with mirrored variables, Kawasaki asserted). **§5.6** Task 7 `to_fold` with `box_pleat` block and deterministic ordering. **§5.7** Task 7 `compile_tree` / `Result` / `STAGES`. ✓
- **§6 bar and columns** — Task 7 e2e asserts the three required validators and marks lint slow; Task 8 rows carry every listed column plus `tip_hull_coverage` / `tm_tip_hull_coverage`; `layer_order` reported only. ✓
- **§7 tests** — goldens: Task 4 (toy N=6 and exhaustive N=4 refusal; beetle within bound), Task 6 (single flap is the Waterbomb); unit: Tasks 1, 2 (square / rectangle / L / corner / edge / boundary spine / river / holes), 5 (`out_dirs` rules, slivers, spine extension), 6 (elevation rule); property: `validate()` on every packed layout (Task 4); integration + determinism: Task 7; negatives: Tasks 1, 2, 3, 7. ✓
- **§8 seams** — `Layout.gadgets`, `Layout.contours`, `compile_tree` as the only import, `Result` exposing every intermediate. The `Macro` registry is B's work. ✓
- **Placeholder scan** — the `<...>` fields are in Task 8's README/commit templates and are filled from measured numbers at run time by instruction; no "TBD", no "similar to Task N". ✓
- **Type consistency** — `Tree.placed_leaves()` used by `pack._place_leaves`; `from_half(N, tree, half_polys, half_rivers)` identical in Tasks 3 and 4; `poly_ridges(cells, tip, N) -> (interior, on_boundary)` consumed by Tasks 3, 5, 6, 7; `ridge_points` returns `dict[Point, frozenset]` and `out_dirs` takes a `frozenset`; `propagate(layout, tree, ridge_pts, boundary_ridges)` called identically in Tasks 5, 6, 7; `assign(layout, ridges, boundary_ridges, contours)` identical in Tasks 6 and 7; `Assignment(pieces, labels)` consumed by `emit._merge_runs`; `Result.timings["pack"]`, `.layout`, `.assignment`, `.ridges`, `.contours` read by the probe. ✓
