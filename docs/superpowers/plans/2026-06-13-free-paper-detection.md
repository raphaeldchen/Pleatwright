# Free-Paper Detection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a deterministic, geometry-only `find_free_paper` MCP tool that reports the regions of paper a Metric Tree leaves uncreased (paper outside the leaf-node convex hull), so the agent and UI can treat unused paper as a design signal for detail flaps.

**Architecture:** Pure-Python geometry in `mcp_harness/free_paper.py` (convex hull → rectangle-minus-hull → free regions), unit-tested in isolation with captured leaf coordinates. A small `leaf_node_locations()` accessor on the C++ wrapper exposes optimized leaf-tip positions. A spawn-isolated `find_free_paper` tool in `server.py` wires them together. TreeMaker's molecule builder and Oriedita are untouched.

**Tech Stack:** Python 3.14 (stdlib only — no numpy/shapely), pybind11 (C++ wrapper), `mcp.server.fastmcp`, pytest. Build via `make build`; test via `make test`.

---

## Spec deviations (read first)

- **`adjacent_node_ids` retained**, sourced from inverting `mNodeMap` (`std::map<int, tmNode*>`, JSON id → node) in the accessor. No deviation.
- **Added field `corners_contained`** (list of rectangle corners inside a region). The spec's `location` becomes the region's **area-weighted centroid** rather than "the corner it contains", because a single region can wrap two corners (e.g. star-3); the centroid is always well-defined. This is a small, faithful refinement of the spec's intent.

## File structure

| File | Responsibility |
|---|---|
| `mcp_harness/free_paper.py` (create) | Pure geometry: `convex_hull`, perimeter/area helpers, `free_paper_regions`. No engine/MCP/JVM imports. |
| `mcp_harness/tests/test_free_paper.py` (create) | Unit tests on `free_paper.py` with captured leaf coords (no engine). |
| `mcp_harness/TreemakerWrapper.cpp` (modify) | Add `leaf_node_locations()` method + pybind binding. Requires rebuild. |
| `mcp_harness/server.py` (modify) | Add `_worker_free_paper` + `find_free_paper` MCP tool. |

---

## Task 1: Convex hull (`free_paper.py`)

**Files:**
- Create: `mcp_harness/free_paper.py`
- Test: `mcp_harness/tests/test_free_paper.py`

- [ ] **Step 1: Write the failing test**

```python
# mcp_harness/tests/test_free_paper.py
import free_paper as fp


def test_convex_hull_square_is_ccw():
    # Four corners + an interior point; hull drops the interior point, returns CCW.
    pts = [(0, 0), (1, 0), (1, 1), (0, 1), (0.5, 0.5)]
    hull = fp.convex_hull(pts)
    assert set(map(tuple, hull)) == {(0, 0), (1, 0), (1, 1), (0, 1)}
    # CCW: signed area positive
    s = sum(hull[i][0] * hull[(i + 1) % len(hull)][1]
            - hull[(i + 1) % len(hull)][0] * hull[i][1]
            for i in range(len(hull)))
    assert s > 0


def test_convex_hull_collinear_returns_points():
    assert fp.convex_hull([(0, 0), (1, 1)]) == [(0.0, 0.0), (1.0, 1.0)]
    assert len(fp.convex_hull([(0, 0), (1, 1), (2, 2)])) == 3  # all collinear
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_free_paper.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'free_paper'`.

- [ ] **Step 3: Write minimal implementation**

```python
# mcp_harness/free_paper.py
"""Geometry-only free-paper detection for the Origami IDE.

TreeMaker builds the crease pattern on the CONVEX HULL of the leaf nodes
(tmTree.cpp:2723-2734). When flap tips do not reach the paper corners, the hull
is smaller than the sheet and the leftover paper is left uncreased. This module
reports those uncreased regions as pure geometry, so the agent and UI can treat
them as a design signal for added detail flaps.

No engine, MCP, or JVM imports: every function takes plain coordinates and
returns plain data, so it is unit-testable in isolation.
"""
from __future__ import annotations

Point = tuple[float, float]
_TOL = 1e-9


def convex_hull(points: list[Point]) -> list[Point]:
    """Convex hull as a CCW list (no repeated last point), via Andrew's monotone
    chain. Degenerate input (<3 unique points, or all collinear) returns the
    unique points sorted."""
    pts = sorted(set((float(x), float(y)) for x, y in points))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    hull = lower[:-1] + upper[:-1]
    if len(hull) < 3:          # all collinear
        return pts
    return hull
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_free_paper.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/free_paper.py mcp_harness/tests/test_free_paper.py
git commit -m "feat(free-paper): convex hull (monotone chain)"
```

---

## Task 2: Rectangle perimeter + polygon helpers (`free_paper.py`)

**Files:**
- Modify: `mcp_harness/free_paper.py`
- Test: `mcp_harness/tests/test_free_paper.py`

- [ ] **Step 1: Write the failing test**

```python
# append to mcp_harness/tests/test_free_paper.py
import pytest


def test_perimeter_coord_walks_ccw_from_origin():
    # unit square, perimeter length 4, CCW: bottom, right, top, left
    assert fp._perimeter_coord((0.0, 0.0), 1.0, 1.0) == pytest.approx(0.0)
    assert fp._perimeter_coord((1.0, 0.0), 1.0, 1.0) == pytest.approx(1.0)
    assert fp._perimeter_coord((1.0, 1.0), 1.0, 1.0) == pytest.approx(2.0)
    assert fp._perimeter_coord((0.0, 1.0), 1.0, 1.0) == pytest.approx(3.0)
    assert fp._perimeter_coord((0.5, 1.0), 1.0, 1.0) == pytest.approx(2.5)


def test_perimeter_coord_rejects_interior_point():
    with pytest.raises(ValueError):
        fp._perimeter_coord((0.5, 0.5), 1.0, 1.0)


def test_polygon_area_and_centroid_unit_square():
    sq = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    assert fp._polygon_area(sq) == pytest.approx(1.0)
    cx, cy = fp._centroid(sq)
    assert (cx, cy) == pytest.approx((0.5, 0.5))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_free_paper.py -v`
Expected: FAIL — `AttributeError: module 'free_paper' has no attribute '_perimeter_coord'`.

- [ ] **Step 3: Write minimal implementation**

```python
# append to mcp_harness/free_paper.py
def _on_boundary(p: Point, w: float, h: float) -> bool:
    x, y = p
    return (abs(x) <= _TOL or abs(x - w) <= _TOL
            or abs(y) <= _TOL or abs(y - h) <= _TOL)


def _perimeter_coord(p: Point, w: float, h: float) -> float:
    """Arc-length coordinate in [0, 2(w+h)) of a point ON the rectangle boundary,
    measured CCW from (0,0): bottom, right, top, then left edge."""
    x, y = p
    if abs(y) <= _TOL:                 # bottom: (0,0)->(w,0)
        return x
    if abs(x - w) <= _TOL:             # right:  (w,0)->(w,h)
        return w + y
    if abs(y - h) <= _TOL:             # top:    (w,h)->(0,h)
        return w + h + (w - x)
    if abs(x) <= _TOL:                 # left:   (0,h)->(0,0)
        return 2 * w + h + (h - y)
    raise ValueError(f"point {p} is not on the rectangle boundary")


def _rect_corners(w: float, h: float):
    """Rectangle corners as (point, perimeter_coord), CCW from origin."""
    return [((0.0, 0.0), 0.0), ((w, 0.0), w),
            ((w, h), w + h), ((0.0, h), 2 * w + h)]


def _polygon_area(poly: list[Point]) -> float:
    s = 0.0
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        s += x0 * y1 - x1 * y0
    return abs(s) / 2.0


def _centroid(poly: list[Point]) -> Point:
    a = cx = cy = 0.0
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        cr = x0 * y1 - x1 * y0
        a += cr
        cx += (x0 + x1) * cr
        cy += (y0 + y1) * cr
    a *= 0.5
    if abs(a) < _TOL:                  # degenerate: fall back to vertex average
        return (sum(p[0] for p in poly) / n, sum(p[1] for p in poly) / n)
    return (cx / (6 * a), cy / (6 * a))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_free_paper.py -v`
Expected: PASS (5 tests total).

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/free_paper.py mcp_harness/tests/test_free_paper.py
git commit -m "feat(free-paper): rectangle perimeter + polygon helpers"
```

---

## Task 3: `free_paper_regions` — the core (`free_paper.py`)

**Files:**
- Modify: `mcp_harness/free_paper.py`
- Test: `mcp_harness/tests/test_free_paper.py`

Algorithm: free paper = rectangle − convex hull. Every hull vertex of a
scale-optimized base lies on the rectangle boundary (flap tips sit on the paper
edge). Walking the hull CCW, each hull edge `a→b` together with the rectangle
perimeter arc from `a` to `b` (increasing perimeter coordinate = the outside arc)
bounds one candidate region; the rectangle corners on that arc are the corners it
contains. Edges lying along the rectangle boundary enclose zero area and are
dropped.

- [ ] **Step 1: Write the failing test**

```python
# append to mcp_harness/tests/test_free_paper.py

# Captured scale-optimized LEAF-node coords (node_id, x, y).
STAR4 = [(2, 0.0, 1.0), (3, 1.0, 0.0), (4, 1.0, 1.0), (5, 0.0, 0.0)]
STAR5 = [(1, 0.0, 0.64711), (2, 0.64711, 0.0), (3, 0.54242, 1.0),
         (4, 0.0, 0.0), (5, 1.0, 0.54242)]


def test_star4_hull_fills_paper_no_free_regions():
    assert fp.free_paper_regions(STAR4, 1.0, 1.0) == []


def test_star5_has_three_corner_regions():
    regions = fp.free_paper_regions(STAR5, 1.0, 1.0)
    assert len(regions) == 3
    assert all(r["kind"] == "corner" for r in regions)
    # one region per missing paper corner
    contained = set()
    for r in regions:
        for c in r["corners_contained"]:
            contained.add(tuple(c))
    assert contained == {(0.0, 1.0), (1.0, 1.0), (1.0, 0.0)}


def test_star5_free_area_plus_hull_equals_sheet():
    regions = fp.free_paper_regions(STAR5, 1.0, 1.0)
    hull = fp.convex_hull([(x, y) for _id, x, y in STAR5])
    free = sum(r["area"] for r in regions)            # fraction of sheet
    assert free + fp._polygon_area(hull) == pytest.approx(1.0, abs=1e-9)


def test_star5_regions_sorted_and_indexed():
    regions = fp.free_paper_regions(STAR5, 1.0, 1.0)
    areas = [r["area"] for r in regions]
    assert areas == sorted(areas, reverse=True)
    assert [r["region_id"] for r in regions] == [0, 1, 2]


def test_star5_adjacent_node_ids_are_real_leaves():
    leaf_ids = {nid for nid, _x, _y in STAR5}
    for r in fp.free_paper_regions(STAR5, 1.0, 1.0):
        assert set(r["adjacent_node_ids"]).issubset(leaf_ids)


def test_degenerate_two_leaves_whole_sheet_is_free():
    regions = fp.free_paper_regions([(1, 0.0, 0.5), (2, 1.0, 0.5)], 1.0, 1.0)
    assert len(regions) == 1
    assert regions[0]["area"] == pytest.approx(1.0)


def test_determinism_same_input_same_output():
    a = fp.free_paper_regions(STAR5, 1.0, 1.0)
    b = fp.free_paper_regions(STAR5, 1.0, 1.0)
    assert a == b
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_free_paper.py -v`
Expected: FAIL — `AttributeError: module 'free_paper' has no attribute 'free_paper_regions'`.

- [ ] **Step 3: Write minimal implementation**

```python
# append to mcp_harness/free_paper.py
from dataclasses import dataclass, asdict

_AREA_EPS = 1e-6   # regions below this fraction of the sheet are slivers; dropped


@dataclass
class Region:
    region_id: int
    kind: str                 # "corner" | "edge-strip"
    location: list            # [x, y] area-weighted centroid
    polygon: list             # [[x, y], ...] CCW outline (exact)
    area: float               # fraction of the total sheet
    adjacent_hull_edge: list  # [[x, y], [x, y]] hull chord bounding the region
    adjacent_node_ids: list   # tree node ids at the chord's two ends
    corners_contained: list   # rectangle corners inside the region


def free_paper_regions(nodes, paper_w: float = 1.0, paper_h: float = 1.0):
    """Uncreased free-paper regions for a tree whose LEAF nodes are `nodes`
    (list of (node_id, x, y) in paper coords, post scale-optimization).

    Returns a list of Region dicts sorted by descending area; [] when the hull
    already fills the paper. Raises ValueError if a hull vertex is interior to
    the paper (not an optimized base), so a caller never gets a silently-wrong
    region set.
    """
    pts = [(float(x), float(y)) for _id, x, y in nodes]
    id_of = {(round(float(x), 9), round(float(y), 9)): int(nid)
             for nid, x, y in nodes}

    def nid_at(p):
        return id_of.get((round(p[0], 9), round(p[1], 9)))

    sheet = paper_w * paper_h
    hull = convex_hull(pts)

    # Degenerate hull (<3 points / collinear): the whole sheet is free.
    if len(hull) < 3:
        rect = [(0.0, 0.0), (paper_w, 0.0), (paper_w, paper_h), (0.0, paper_h)]
        r = Region(0, "corner", list(_centroid(rect)),
                   [list(p) for p in rect], 1.0,
                   [[0.0, 0.0], [paper_w, 0.0]], [], [])
        return [asdict(r)]

    for v in hull:
        if not _on_boundary(v, paper_w, paper_h):
            raise ValueError(
                f"hull vertex {v} is interior to the paper; free-paper "
                "detection assumes scale-optimized bases (tips on the edge)")

    perim = 2 * (paper_w + paper_h)
    corners = _rect_corners(paper_w, paper_h)
    regions = []
    n = len(hull)
    for i in range(n):
        a = hull[i]
        b = hull[(i + 1) % n]                 # CCW hull edge a -> b
        ta = _perimeter_coord(a, paper_w, paper_h)
        tb = _perimeter_coord(b, paper_w, paper_h)
        span = (tb - ta) % perim
        arc = []
        for cpt, ct in corners:
            d = (ct - ta) % perim
            if _TOL < d < span - _TOL:
                arc.append((d, cpt))
        arc.sort()
        poly = [a] + [cpt for _d, cpt in arc] + [b]
        area = _polygon_area(poly)
        if area / sheet < _AREA_EPS:          # edge lies along the rectangle
            continue
        regions.append(Region(
            region_id=0,
            kind="corner" if arc else "edge-strip",
            location=list(_centroid(poly)),
            polygon=[list(p) for p in poly],
            area=area / sheet,
            adjacent_hull_edge=[list(a), list(b)],
            adjacent_node_ids=[nid_at(a), nid_at(b)],
            corners_contained=[list(cpt) for _d, cpt in arc],
        ))

    regions.sort(key=lambda r: r.area, reverse=True)
    for idx, r in enumerate(regions):
        r.region_id = idx
    return [asdict(r) for r in regions]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_free_paper.py -v`
Expected: PASS (12 tests total).

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/free_paper.py mcp_harness/tests/test_free_paper.py
git commit -m "feat(free-paper): free_paper_regions (rectangle minus hull)"
```

---

## Task 4: C++ accessor `leaf_node_locations()` (`TreemakerWrapper.cpp`)

**Files:**
- Modify: `mcp_harness/TreemakerWrapper.cpp` (add method ~after `build_and_export`, and a pybind `.def` in the `py::class_<HeadlessTreemaker>` block near line 883)

- [ ] **Step 1: Write the failing test**

```python
# mcp_harness/tests/test_leaf_locations.py
import json
import multiprocessing as mp
import sys
sys.path.insert(0, "tests")
from cases import CASES_BY_NAME   # noqa: E402


def _worker(q, name):
    import headless_treemaker as ht
    nodes, pairs = CASES_BY_NAME[name]
    e = ht.HeadlessTreemaker(); e.init_paper(1.0, 1.0)
    e.build_tree_from_json(json.dumps(nodes))
    for a, b in pairs:
        e.apply_symmetry(int(a), int(b))
    e.run_scale_optimization()
    q.put(list(e.leaf_node_locations()))


def test_star5_returns_five_leaf_locations_on_boundary():
    ctx = mp.get_context("spawn"); q = ctx.Queue()
    p = ctx.Process(target=_worker, args=(q, "star-5")); p.start(); p.join(40)
    locs = q.get(timeout=5)
    assert len(locs) == 5
    for nid, x, y in locs:
        assert isinstance(nid, int)
        on_edge = (abs(x) < 1e-6 or abs(x - 1) < 1e-6
                   or abs(y) < 1e-6 or abs(y - 1) < 1e-6)
        assert on_edge, f"leaf {nid} at ({x},{y}) not on paper edge"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_leaf_locations.py -v`
Expected: FAIL — `AttributeError: 'headless_treemaker.HeadlessTreemaker' object has no attribute 'leaf_node_locations'`.

- [ ] **Step 3: Write minimal implementation**

Add `#include <tuple>` with the other includes near the top of `TreemakerWrapper.cpp` (after `#include <vector>` on line 21). Then add this method to the `HeadlessTreemaker` class, right after the `build_and_export()` method (around line 325):

```cpp
  // Return the optimized LEAF-node locations as (json_id, x, y) triples so the
  // Python side can compute the leaf-node convex hull (what TreeMaker creases)
  // and report uncreased free paper. Read-only; assumes run_scale_optimization()
  // has run. json_id is the id from build_tree_from_json (via mNodeMap), or -1
  // if the node is not in the map.
  std::vector<std::tuple<int, double, double>> leaf_node_locations() {
    if (mNodeMap.empty())
      throw std::runtime_error("no tree built; call build_tree_from_json first");
    std::map<tmNode*, int> idOf;
    for (const auto& kv : mNodeMap) idOf[kv.second] = kv.first;
    std::vector<std::tuple<int, double, double>> out;
    tmArray<tmNode*> leaves;
    mTree->GetLeafNodes(leaves);
    for (std::size_t i = 0; i < leaves.size(); ++i) {
      tmNode* n = leaves[i];
      auto it = idOf.find(n);
      int jid = (it != idOf.end()) ? it->second : -1;
      out.emplace_back(jid, double(n->GetLoc().x), double(n->GetLoc().y));
    }
    return out;
  }
```

Add the binding inside the `py::class_<HeadlessTreemaker>(m, "HeadlessTreemaker")` chain (after the `build_and_export` `.def`, around line 884):

```cpp
      .def("leaf_node_locations", &HeadlessTreemaker::leaf_node_locations,
           "optimized leaf-node (json_id, x, y) triples")
```

- [ ] **Step 4: Rebuild, then run test to verify it passes**

Run: `cd mcp_harness && PYTHON=.venv/bin/python ./build.sh && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_leaf_locations.py -v`
Expected: build succeeds (fresh `headless_treemaker*.so`), then PASS.
(Note: build the `.so` from INSIDE `mcp_harness` — `treemaker/build.sh` is a different script that builds the GUI app.)

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/TreemakerWrapper.cpp mcp_harness/tests/test_leaf_locations.py
git commit -m "feat(engine): leaf_node_locations() accessor for free-paper detection"
```

---

## Task 5: `find_free_paper` MCP tool (`server.py`)

**Files:**
- Modify: `mcp_harness/server.py` (add `_worker_free_paper` near the other `_worker_*` functions ~line 130, and the `find_free_paper` tool in the incremental-session section ~line 240)
- Test: `mcp_harness/tests/test_find_free_paper.py`

- [ ] **Step 1: Write the failing test**

```python
# mcp_harness/tests/test_find_free_paper.py
import json
import sys
sys.path.insert(0, "tests")
from cases import CASES_BY_NAME   # noqa: E402
import server                     # noqa: E402


def _regions(name):
    nodes, pairs = CASES_BY_NAME[name]
    out = server.find_free_paper(tree_nodes=nodes,
                                 symmetric_pairs=[list(p) for p in pairs])
    return json.loads(out)


def test_star4_reports_no_free_paper():
    assert _regions("star-4") == []


def test_star5_reports_three_corner_regions():
    regions = _regions("star-5")
    assert len(regions) == 3
    assert all(r["kind"] == "corner" for r in regions)


def test_star6_region_count_matches_missing_corners():
    # star-6 keeps 2 of 4 corners -> 2 free regions
    assert len(_regions("star-6")) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_find_free_paper.py -v`
Expected: FAIL — `AttributeError: module 'server' has no attribute 'find_free_paper'`.

- [ ] **Step 3: Write minimal implementation**

Add the worker next to the other `_worker_*` functions (after `_worker_convert_tmd`, ~line 132). It mirrors `_worker_full_base` but returns regions instead of a FOLD:

```python
def _worker_free_paper(queue, tree_nodes_json, pairs, paper_width, paper_height):
    try:
        import headless_treemaker as ht_child
        import free_paper
        engine = ht_child.HeadlessTreemaker()
        engine.init_paper(paper_width, paper_height)
        engine.build_tree_from_json(tree_nodes_json)
        for a, b in pairs:
            engine.apply_symmetry(int(a), int(b))
        engine.run_scale_optimization()
        locs = list(engine.leaf_node_locations())
        regions = free_paper.free_paper_regions(locs, paper_width, paper_height)
        queue.put(("ok", json.dumps(regions)))
    except BaseException as exc:  # noqa: BLE001
        queue.put(("err", repr(exc)[:200]))
```

Add the tool in the incremental-session section (after `apply_symmetry`, ~line 256):

```python
@mcp.tool()
def find_free_paper(
    tree_nodes: list[dict],
    symmetric_pairs: list[list[int]] | None = None,
    paper_width: float = 1.0,
    paper_height: float = 1.0,
) -> str:
    """Report paper a tree leaves UNCREASED (paper outside the leaf-node convex
    hull) — a design signal for adding detail flaps. Geometry only: no anatomy,
    no packing.

    Args:
        tree_nodes: list of node dicts (see describe_tree_format).
        symmetric_pairs: list of [node_a, node_b] leaf-node id pairs to mirror.
        paper_width, paper_height: paper canvas size (default 1x1 square).

    Returns:
        A JSON array of free-paper regions, each with: region_id, kind
        ("corner"/"edge-strip"), location [x,y] (centroid), polygon, area
        (fraction of the sheet), adjacent_hull_edge, adjacent_node_ids,
        corners_contained. An empty array "[]" means the hull already fills the
        paper (expect a clean lint). On failure, a string starting with "ERROR:".
    """
    pairs = symmetric_pairs or []
    return _run_isolated(
        _worker_free_paper,
        json.dumps(tree_nodes),
        pairs,
        paper_width,
        paper_height,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_find_free_paper.py -v`
Expected: PASS (3 tests). (Requires Task 4's rebuilt `.so`.)

- [ ] **Step 5: Run the whole suite to confirm no regressions**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/ -v`
Expected: all pre-existing tests still PASS, plus the new free-paper tests.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/server.py mcp_harness/tests/test_find_free_paper.py
git commit -m "feat(server): find_free_paper MCP tool"
```

---

## Final verification

- [ ] **Run `make test` from repo root** to confirm the build + full regression suite (including the new tests) is green:

Run: `make test`
Expected: build succeeds; pytest reports all tests passing.

- [ ] **Push:**

```bash
git push origin main
```
