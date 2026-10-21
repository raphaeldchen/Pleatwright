# A-9: Generative Anatomy-Detail Engine — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `find_free_paper` generative — a self-verifying MCP tool that turns an approved free-paper region into new metric-tree leaf nodes (a detail flap), recompiles, and confirms the region shrank, closing the detect→fill→re-verify loop.

**Architecture:** One new pure-geometry module (`mcp_harness/flap_fill.py`) computes ordered candidate flaps `(attach_node_id, length)` from a region + tree, mirroring `free_paper.py`'s discipline (plain data in/out, no engine imports). One new MCP tool (`suggest_flap_for_region` in `server.py`) drives recompile + re-check through the **existing** `_run_isolated` / `_worker_full_base` / `_compile_with_perturb` / `free_paper` machinery and returns `status:"filled"` or `status:"accept"`. The agent SYSTEM_PROMPT gets a suggest-then-confirm (HITL) block.

**Tech Stack:** Python 3 (stdlib only for the geometry), pybind11 `headless_treemaker` engine (already built, no rebuild), pytest, `multiprocessing` spawn workers, Playwright (existing e2e harness).

## Global Constraints

- Metric-tree node shape (verbatim): `{"id": int, "parent_id": int|None, "length": float}`. Root has `parent_id=None, length=0`. Symmetry is a separate `pairs`/`symmetric_pairs` list of `[a, b]` node-id pairs. (Source: `mcp_harness/tests/cases.py`.)
- The AI edits ONLY the metric tree (CLAUDE.md §2). `flap_fill` emits **new tree nodes + a symmetric_pair**, never `.fold` geometry.
- `flap_fill.py` MUST NOT import the engine, JVM, MCP, or `server` — plain coordinates + tree topology only, like `free_paper.py`.
- Engine accessors already bound (no C++ change): `engine.run_scale_optimization()` **returns the scale `float`**; `engine.leaf_node_locations()` returns `[(id, x, y)]`. Spawn (not fork) is mandatory for any worker under the stdio transport.
- Verification gates on **packs + static-well-formed fold + target region shrank** — NOT a clean Oriedita lint (A-3: hull-frontier lint failures are false-negatives). True physics-fold confirmation is the Playwright check only.
- Tests live in `mcp_harness/tests/`; pure tests `import flap_fill`, tool tests `import server`, both rely on the suite's `sys.path` (run from `mcp_harness/`). Run with `cd mcp_harness && python -m pytest`.
- Commit after every green step. Branch: `feat/generative-anatomy-detail-a9` (already created; spec committed at `c2396d2`).

---

### Task 1: Polygon inradius (largest inscribed circle)

**Files:**
- Create: `mcp_harness/flap_fill.py`
- Test: `mcp_harness/tests/test_flap_fill.py`

**Interfaces:**
- Consumes: nothing (pure geometry).
- Produces: `largest_inscribed_circle(polygon: list[tuple[float,float]]) -> tuple[tuple[float,float], float]` returning `((cx, cy), radius)` — the center and radius of the largest circle that fits inside the (convex-or-simple) polygon. Used by Task 3 to size a flap.

- [ ] **Step 1: Write the failing test**

```python
# mcp_harness/tests/test_flap_fill.py
import math
import pytest
import flap_fill as ff


def test_inscribed_circle_unit_square_centered():
    sq = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    (cx, cy), r = ff.largest_inscribed_circle(sq)
    assert (cx, cy) == pytest.approx((0.5, 0.5), abs=1e-3)
    assert r == pytest.approx(0.5, abs=1e-3)


def test_inscribed_circle_thin_strip_radius_is_half_width():
    strip = [(0.0, 0.0), (1.0, 0.0), (1.0, 0.2), (0.0, 0.2)]
    _, r = ff.largest_inscribed_circle(strip)
    assert r == pytest.approx(0.1, abs=1e-3)


def test_inscribed_circle_right_triangle_corner():
    tri = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]
    (cx, cy), r = ff.largest_inscribed_circle(tri)
    # incircle of a unit right triangle: r = (a+b-c)/2 = (1+1-sqrt2)/2
    assert r == pytest.approx((2 - math.sqrt(2)) / 2, abs=1e-3)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp_harness && python -m pytest tests/test_flap_fill.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'flap_fill'` (then `AttributeError` once the file exists).

- [ ] **Step 3: Write minimal implementation**

```python
# mcp_harness/flap_fill.py
"""Pure geometry for A-9 generative anatomy detail: turn a free-paper region
(from free_paper.py) plus a metric tree into candidate detail flaps.

Same discipline as free_paper.py: plain coordinates + tree topology in, plain
data out. NO engine / JVM / MCP / server imports, so it is unit-testable in
isolation. The AI edits only the metric tree, so this module only ever emits
new tree nodes + symmetric pairs, never .fold geometry.
"""
from __future__ import annotations

Point = tuple[float, float]


def _point_to_segment_dist(p: Point, a: Point, b: Point) -> float:
    px, py = p
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    seg2 = dx * dx + dy * dy
    if seg2 <= 1e-18:
        return ((px - ax) ** 2 + (py - ay) ** 2) ** 0.5
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / seg2))
    cx, cy = ax + t * dx, ay + t * dy
    return ((px - cx) ** 2 + (py - cy) ** 2) ** 0.5


def _point_in_polygon(p: Point, poly: list[Point]) -> bool:
    x, y = p
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y):
            xint = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < xint:
                inside = not inside
        j = i
    return inside


def _clearance(p: Point, poly: list[Point]) -> float:
    """Distance from interior point p to the nearest polygon edge (0 if outside)."""
    if not _point_in_polygon(p, poly):
        return 0.0
    n = len(poly)
    return min(_point_to_segment_dist(p, poly[i], poly[(i + 1) % n])
              for i in range(n))


def largest_inscribed_circle(polygon: list[Point]) -> tuple[Point, float]:
    """Center + radius of the largest circle inside the polygon, by grid-refined
    search on the clearance (distance-to-nearest-edge) field. Deterministic."""
    xs = [x for x, _ in polygon]
    ys = [y for _, y in polygon]
    lo_x, hi_x, lo_y, hi_y = min(xs), max(xs), min(ys), max(ys)
    best_p, best_r = ((lo_x + hi_x) / 2, (lo_y + hi_y) / 2), 0.0
    step_x, step_y = (hi_x - lo_x), (hi_y - lo_y)
    for _ in range(6):                      # refine 6x around the best cell
        gx = step_x / 8 or 1e-9
        gy = step_y / 8 or 1e-9
        i = lo_x
        while i <= hi_x + 1e-12:
            j = lo_y
            while j <= hi_y + 1e-12:
                r = _clearance((i, j), polygon)
                if r > best_r:
                    best_r, best_p = r, (i, j)
                j += gy
            i += gx
        lo_x, hi_x = best_p[0] - gx, best_p[0] + gx
        lo_y, hi_y = best_p[1] - gy, best_p[1] + gy
        step_x, step_y = hi_x - lo_x, hi_y - lo_y
    return best_p, best_r
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp_harness && python -m pytest tests/test_flap_fill.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/flap_fill.py mcp_harness/tests/test_flap_fill.py
git commit -m "feat(a9): polygon largest-inscribed-circle for flap sizing"
```

---

### Task 2: Tree topology helpers

**Files:**
- Modify: `mcp_harness/flap_fill.py`
- Test: `mcp_harness/tests/test_flap_fill.py`

**Interfaces:**
- Consumes: node dicts `{"id","parent_id","length"}`.
- Produces:
  - `nearest_common_ancestor(nodes: list[dict], a: int, b: int) -> int` — id of the deepest node that is an ancestor of both `a` and `b` (root if nothing closer).
  - `next_node_id(nodes: list[dict]) -> int` — `max(id)+1`.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_flap_fill.py
def _quad_nodes():
    # root 0; chain 0->1->2 ; leaves 3 (off 0), 4 (off 1), 5 (off 2)
    return [
        {"id": 0, "parent_id": None, "length": 0},
        {"id": 1, "parent_id": 0, "length": 0.4},
        {"id": 2, "parent_id": 1, "length": 0.4},
        {"id": 3, "parent_id": 0, "length": 0.5},
        {"id": 4, "parent_id": 1, "length": 0.5},
        {"id": 5, "parent_id": 2, "length": 0.5},
    ]


def test_nearest_common_ancestor_siblings_off_root():
    assert ff.nearest_common_ancestor(_quad_nodes(), 3, 4) == 0


def test_nearest_common_ancestor_deeper_branch():
    # leaves 4 (parent 1) and 5 (parent 2, parent 1) share ancestor 1
    assert ff.nearest_common_ancestor(_quad_nodes(), 4, 5) == 1


def test_next_node_id_is_max_plus_one():
    assert ff.next_node_id(_quad_nodes()) == 6
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp_harness && python -m pytest tests/test_flap_fill.py -k "ancestor or next_node" -v`
Expected: FAIL — `AttributeError: module 'flap_fill' has no attribute 'nearest_common_ancestor'`.

- [ ] **Step 3: Write minimal implementation**

```python
# append to flap_fill.py
def _parent_of(nodes: list[dict]) -> dict[int, int | None]:
    return {int(n["id"]): n["parent_id"] for n in nodes}


def _ancestors(nodes: list[dict], a: int) -> list[int]:
    """a, then its parents up to the root (inclusive)."""
    par = _parent_of(nodes)
    chain, cur = [], a
    while cur is not None:
        chain.append(int(cur))
        cur = par.get(int(cur))
    return chain


def nearest_common_ancestor(nodes: list[dict], a: int, b: int) -> int:
    anc_a = _ancestors(nodes, a)
    anc_b = set(_ancestors(nodes, b))
    for x in anc_a:               # walk up from a, first hit in b's chain
        if x in anc_b:
            return x
    return anc_a[-1]              # fallback: root


def next_node_id(nodes: list[dict]) -> int:
    return max(int(n["id"]) for n in nodes) + 1
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp_harness && python -m pytest tests/test_flap_fill.py -k "ancestor or next_node" -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/flap_fill.py mcp_harness/tests/test_flap_fill.py
git commit -m "feat(a9): tree topology helpers (NCA, id allocation)"
```

---

### Task 3: Candidate generation (`suggest`)

**Files:**
- Modify: `mcp_harness/flap_fill.py`
- Test: `mcp_harness/tests/test_flap_fill.py`

**Interfaces:**
- Consumes: `largest_inscribed_circle` (T1), `nearest_common_ancestor`/`next_node_id` (T2). A `region` dict as emitted by `free_paper.free_paper_regions` (fields `polygon`, `adjacent_node_ids`; for `kind="frame"`, `adjacent_node_ids` are hull-vertex leaf ids).
- Produces:
  `suggest(nodes, region, scale, mirror_region=None, desired_length=None) -> list[dict]`
  returning an **ordered** candidate list. Each candidate:
  ```python
  {"new_nodes": [ {"id","parent_id","length"}, ... ],   # 1 (solo) or 2 (mirror)
   "new_pairs": [[id_a, id_b]] or [],
   "attach_node_id": int,
   "length": float}
  ```
  Length = `inradius/scale` clamped by `desired_length` when given (capped at the inradius-allowed value; a shorter hint is honored). Mirror candidates use a single shared length = `min` of both regions' allowed lengths and register a `symmetric_pair`.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_flap_fill.py
def _corner_region(adj_ids):
    # a corner triangle region near (1,1); adjacent leaves given by id
    return {"kind": "corner",
            "polygon": [[0.7, 1.0], [1.0, 1.0], [1.0, 0.7]],
            "adjacent_node_ids": adj_ids}


def test_suggest_solo_attaches_to_common_ancestor():
    nodes = _quad_nodes()
    cands = ff.suggest(nodes, _corner_region([3, 4]), scale=0.5)
    assert cands, "expected at least one candidate"
    top = cands[0]
    assert top["attach_node_id"] == 0          # NCA of leaves 3 and 4
    assert len(top["new_nodes"]) == 1
    assert top["new_nodes"][0]["parent_id"] == 0
    assert top["new_nodes"][0]["id"] == 6
    assert top["new_pairs"] == []
    assert top["length"] > 0


def test_suggest_length_scales_inverse_with_scale():
    nodes = _quad_nodes()
    big = ff.suggest(nodes, _corner_region([3, 4]), scale=0.25)[0]["length"]
    small = ff.suggest(nodes, _corner_region([3, 4]), scale=0.5)[0]["length"]
    assert big == pytest.approx(2 * small, rel=1e-6)


def test_suggest_desired_length_clamps_down_only():
    nodes = _quad_nodes()
    unhinted = ff.suggest(nodes, _corner_region([3, 4]), scale=0.5)[0]["length"]
    short = ff.suggest(nodes, _corner_region([3, 4]), scale=0.5,
                       desired_length=unhinted * 0.5)[0]["length"]
    long = ff.suggest(nodes, _corner_region([3, 4]), scale=0.5,
                      desired_length=unhinted * 10)[0]["length"]
    assert short == pytest.approx(unhinted * 0.5, rel=1e-6)
    assert long == pytest.approx(unhinted, rel=1e-6)   # capped at fit


def test_suggest_mirror_emits_pair_with_shared_length():
    nodes = _quad_nodes()
    cands = ff.suggest(nodes, _corner_region([3, 4]), scale=0.5,
                       mirror_region=_corner_region([2, 5]))
    top = cands[0]
    assert len(top["new_nodes"]) == 2
    assert top["new_nodes"][0]["id"] == 6
    assert top["new_nodes"][1]["id"] == 7
    assert top["new_pairs"] == [[6, 7]]
    assert top["new_nodes"][0]["length"] == top["new_nodes"][1]["length"]


def test_suggest_orders_primary_then_shorter():
    nodes = _quad_nodes()
    cands = ff.suggest(nodes, _corner_region([3, 4]), scale=0.5)
    assert len(cands) >= 2
    assert cands[1]["length"] < cands[0]["length"]   # shorter fallback second
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp_harness && python -m pytest tests/test_flap_fill.py -k suggest -v`
Expected: FAIL — `AttributeError: module 'flap_fill' has no attribute 'suggest'`.

- [ ] **Step 3: Write minimal implementation**

```python
# append to flap_fill.py
_SHORTER = 0.6      # second-candidate length multiplier (tight repacks)


def _allowed_length(region: dict, scale: float) -> tuple[int, float]:
    """(attach-pair node ids unused here) -> fitting tree-edge length for region."""
    poly = [(float(x), float(y)) for x, y in region["polygon"]]
    _, inradius = largest_inscribed_circle(poly)
    if scale <= 1e-12:
        return 0.0
    return inradius / scale


def _leaf(node_id: int, parent_id: int, length: float) -> dict:
    return {"id": node_id, "parent_id": int(parent_id), "length": float(length)}


def suggest(nodes, region, scale, mirror_region=None, desired_length=None):
    a, b = (int(region["adjacent_node_ids"][0]),
            int(region["adjacent_node_ids"][1]))
    attach = nearest_common_ancestor(nodes, a, b)
    fit = _allowed_length(region, scale)

    if mirror_region is not None:
        ma, mb = (int(mirror_region["adjacent_node_ids"][0]),
                  int(mirror_region["adjacent_node_ids"][1]))
        mattach = nearest_common_ancestor(nodes, ma, mb)
        mfit = _allowed_length(mirror_region, scale)
        fit = min(fit, mfit)            # one shared length so the pair is balanced

    def clamp(base: float) -> float:
        return min(base, float(desired_length)) if desired_length is not None else base

    def build(length: float) -> dict:
        nid = next_node_id(nodes)
        if mirror_region is None:
            return {"new_nodes": [_leaf(nid, attach, length)], "new_pairs": [],
                    "attach_node_id": attach, "length": length}
        return {"new_nodes": [_leaf(nid, attach, length),
                              _leaf(nid + 1, mattach, length)],
                "new_pairs": [[nid, nid + 1]],
                "attach_node_id": attach, "length": length}

    primary = clamp(fit)
    out = [build(primary)]
    if primary * _SHORTER > 1e-6:
        out.append(build(primary * _SHORTER))
    return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp_harness && python -m pytest tests/test_flap_fill.py -k suggest -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/flap_fill.py mcp_harness/tests/test_flap_fill.py
git commit -m "feat(a9): region->candidate flap generation with mirror + length clamp"
```

---

### Task 4: Verification predicates

**Files:**
- Modify: `mcp_harness/flap_fill.py`
- Test: `mcp_harness/tests/test_flap_fill.py`

**Interfaces:**
- Consumes: region dicts, a parsed `.fold` dict, `paper_w`/`paper_h`.
- Produces:
  - `fold_is_wellformed(fold: dict, w: float, h: float) -> bool` — all `vertices_coords` finite and within `[-1e-6, w+1e-6] x [-1e-6, h+1e-6]`; non-empty.
  - `region_shrank(target: dict, regions_after: list[dict], frac: float = 0.5) -> bool` — no region in `regions_after` overlapping the target's centroid retains ≥ `frac` of the target's area. (Centroid-membership match; the target region object came from `free_paper`, which provides `location` + `area`.)

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_flap_fill.py
def test_fold_wellformed_accepts_bounded_finite():
    fold = {"vertices_coords": [[0, 0], [1, 0], [0.5, 1]]}
    assert ff.fold_is_wellformed(fold, 1.0, 1.0) is True


def test_fold_wellformed_rejects_nan_and_oob():
    assert ff.fold_is_wellformed({"vertices_coords": [[0, 0], [float("nan"), 0]]},
                                 1.0, 1.0) is False
    assert ff.fold_is_wellformed({"vertices_coords": [[0, 0], [5.0, 0]]},
                                 1.0, 1.0) is False
    assert ff.fold_is_wellformed({"vertices_coords": []}, 1.0, 1.0) is False


def test_region_shrank_true_when_area_gone():
    target = {"location": [0.85, 0.85], "area": 0.1}
    # after fill there is no region near (0.85, 0.85)
    assert ff.region_shrank(target, [{"location": [0.1, 0.1], "area": 0.05}]) is True


def test_region_shrank_false_when_area_persists():
    target = {"location": [0.85, 0.85], "area": 0.1}
    after = [{"location": [0.85, 0.85], "area": 0.09}]   # basically unchanged
    assert ff.region_shrank(target, after) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp_harness && python -m pytest tests/test_flap_fill.py -k "wellformed or shrank" -v`
Expected: FAIL — attributes missing.

- [ ] **Step 3: Write minimal implementation**

```python
# append to flap_fill.py
import math as _math


def fold_is_wellformed(fold: dict, w: float, h: float) -> bool:
    verts = fold.get("vertices_coords") if isinstance(fold, dict) else None
    if not verts:
        return False
    for v in verts:
        if not isinstance(v, (list, tuple)) or len(v) < 2:
            return False
        x, y = float(v[0]), float(v[1])
        if not (_math.isfinite(x) and _math.isfinite(y)):
            return False
        if not (-1e-6 <= x <= w + 1e-6 and -1e-6 <= y <= h + 1e-6):
            return False
    return True


def region_shrank(target: dict, regions_after: list[dict], frac: float = 0.5) -> bool:
    tx, ty = target["location"]
    t_area = float(target["area"])
    for r in regions_after:
        rx, ry = r["location"]
        if abs(rx - tx) < 0.08 and abs(ry - ty) < 0.08:     # same locale
            if float(r["area"]) >= frac * t_area:
                return False                                # still substantial
    return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp_harness && python -m pytest tests/test_flap_fill.py -k "wellformed or shrank" -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/flap_fill.py mcp_harness/tests/test_flap_fill.py
git commit -m "feat(a9): fold well-formedness + region-shrank verification predicates"
```

---

### Task 5: `suggest_flap_for_region` MCP tool (self-verify loop)

**Files:**
- Modify: `mcp_harness/server.py` (add a worker near `_worker_free_paper` ~line 144; add the tool near `find_free_paper` ~line 369)
- Test: `mcp_harness/tests/test_flap_fill_tool.py`

**Interfaces:**
- Consumes: `flap_fill.suggest`, `flap_fill.fold_is_wellformed`, `flap_fill.region_shrank` (T3/T4); existing `_run_isolated`, `_worker_full_base`, `free_paper.free_paper_regions`, and the bound engine accessors.
- Produces: MCP tool
  `suggest_flap_for_region(tree_nodes, region, mirror_region=None, symmetric_pairs=None, desired_length=None, name=None, paper_width=1.0, paper_height=1.0) -> str`
  returning a JSON string: on success `{"status":"filled","tree_nodes":[...],"symmetric_pairs":[...],"fold":{...},"regions_after":[...],"added_node_ids":[...],"name":...}`; on no-converge `{"status":"accept","tree_nodes":<unchanged>,"message":"..."}`; on bad input `"ERROR: ..."`.

- [ ] **Step 1: Write the failing test**

```python
# mcp_harness/tests/test_flap_fill_tool.py
import json
import sys
sys.path.insert(0, "tests")
from cases import CASES_BY_NAME   # noqa: E402
import server                     # noqa: E402


def _regions(name):
    nodes, pairs = CASES_BY_NAME[name]
    return nodes, pairs, json.loads(server.find_free_paper(
        tree_nodes=nodes, symmetric_pairs=[list(p) for p in pairs]))


def test_fill_star5_corner_shrinks_and_packs():
    # star-5 leaves 3 corner regions; filling the largest should consume it.
    nodes, pairs, regions = _regions("star-5")
    assert regions, "star-5 must report free paper"
    target = max(regions, key=lambda r: r["area"])
    out = json.loads(server.suggest_flap_for_region(
        tree_nodes=nodes, region=target,
        symmetric_pairs=[list(p) for p in pairs], name="ear"))
    assert out["status"] == "filled", out
    assert len(out["tree_nodes"]) == len(nodes) + 1       # one new leaf
    assert out["fold"]["vertices_coords"]                 # real geometry
    # the target locale lost its free paper
    import flap_fill as ff
    assert ff.region_shrank(target, out["regions_after"])


def test_accept_fallback_returns_unchanged_tree():
    # A region the engine cannot fill (degenerate inward polygon, tiny scale-fit)
    nodes, pairs, _ = _regions("star-4")   # star-4 already fills the square
    fake_region = {"kind": "corner",
                   "polygon": [[0.49, 0.49], [0.51, 0.49], [0.5, 0.51]],
                   "adjacent_node_ids": [1, 2],
                   "location": [0.5, 0.497], "area": 1e-4}
    out = json.loads(server.suggest_flap_for_region(
        tree_nodes=nodes, region=fake_region,
        symmetric_pairs=[list(p) for p in pairs]))
    assert out["status"] == "accept", out
    assert out["tree_nodes"] == nodes      # unchanged
    assert "free paper" in out["message"].lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp_harness && python -m pytest tests/test_flap_fill_tool.py -v`
Expected: FAIL — `AttributeError: module 'server' has no attribute 'suggest_flap_for_region'`.

- [ ] **Step 3: Write minimal implementation**

Add the worker (top-level, picklable — required for spawn) next to `_worker_free_paper`:

```python
# mcp_harness/server.py  (near _worker_free_paper, ~line 159)
def _worker_compile_and_regions(queue, tree_nodes_json, pairs,
                                paper_width, paper_height):
    """Compile a candidate tree AND report its post-compile free paper, so the
    A-9 verify loop gets both the .fold and the new frontier from one spawn."""
    try:
        import headless_treemaker as ht_child
        import free_paper
        engine = ht_child.HeadlessTreemaker()
        engine.init_paper(paper_width, paper_height)
        engine.build_tree_from_json(tree_nodes_json)
        for a, b in pairs:
            engine.apply_symmetry(int(a), int(b))
        engine.run_scale_optimization()
        fold = engine.build_and_export()
        locs = list(engine.leaf_node_locations())
        regions = free_paper.free_paper_regions(locs, paper_width, paper_height)
        queue.put(("ok", json.dumps({"fold": fold, "regions": regions})))
    except BaseException as exc:  # noqa: BLE001
        queue.put(("err", repr(exc)[:200]))
```

Add the tool (decorated like the others) near `find_free_paper`:

```python
# mcp_harness/server.py  (after find_free_paper, ~line 399)
@mcp.tool()
def suggest_flap_for_region(
    tree_nodes: list[dict],
    region: dict,
    mirror_region: dict | None = None,
    symmetric_pairs: list[list[int]] | None = None,
    desired_length: float | None = None,
    name: str | None = None,
    paper_width: float = 1.0,
    paper_height: float = 1.0,
) -> str:
    """A-9 generative anatomy detail: turn a free-paper REGION (from
    find_free_paper) into a new detail flap, recompile, and verify it consumed
    the region. Pass mirror_region to add a bilaterally symmetric pair atomically.
    'name' is descriptive only (ear/tail) and never affects geometry.

    Returns JSON: status 'filled' (with the updated tree_nodes, symmetric_pairs,
    fold, regions_after, added_node_ids) or 'accept' (no flap converged; the
    region is fine as free paper per A-3, tree unchanged), or 'ERROR: ...'.
    """
    import flap_fill
    pairs = [list(p) for p in (symmetric_pairs or [])]

    # scale comes free from the FIRST recompile; but suggest() needs a scale to
    # size the flap. Use the base tree's scale via a lightweight compile+regions
    # call, reusing the worker (its fold tells us nothing new but its regions do).
    try:
        base = json.loads(_run_isolated(
            _worker_compile_and_regions, json.dumps(tree_nodes), pairs,
            paper_width, paper_height))
    except Exception as exc:                      # base itself failed to compile
        return f"ERROR: base tree did not compile ({exc})"
    if not isinstance(base, dict):                # _run_isolated returned ERROR str
        return f"ERROR: base tree did not compile ({base})"

    # Derive scale from the base fold's frame_title ("...scale=<v>)"). Robust and
    # needs no new binding; falls back to 1.0 if absent.
    scale = _scale_from_fold(base["fold"])

    candidates = flap_fill.suggest(tree_nodes, region, scale,
                                   mirror_region=mirror_region,
                                   desired_length=desired_length)
    for cand in candidates:
        tree2 = tree_nodes + cand["new_nodes"]
        pairs2 = pairs + cand["new_pairs"]
        raw = _run_isolated(_worker_compile_and_regions, json.dumps(tree2),
                            pairs2, paper_width, paper_height)
        try:
            res = json.loads(raw)
        except Exception:
            continue                              # ERROR string -> didn't pack
        if not isinstance(res, dict):
            continue
        fold, regions_after = res["fold"], res["regions"]
        if not flap_fill.fold_is_wellformed(fold, paper_width, paper_height):
            continue
        targets = [region] + ([mirror_region] if mirror_region else [])
        if all(flap_fill.region_shrank(t, regions_after) for t in targets):
            return json.dumps({
                "status": "filled",
                "tree_nodes": tree2,
                "symmetric_pairs": pairs2,
                "fold": fold,
                "regions_after": regions_after,
                "added_node_ids": [n["id"] for n in cand["new_nodes"]],
                "name": name,
            })
    return json.dumps({
        "status": "accept",
        "tree_nodes": tree_nodes,
        "message": ("No flap converges into this region; accept it as free "
                    "paper (the base still folds, per A-3)."),
    })


def _scale_from_fold(fold: dict) -> float:
    title = (fold or {}).get("frame_title", "") if isinstance(fold, dict) else ""
    import re
    m = re.search(r"scale=([0-9.eE+-]+)", title or "")
    return float(m.group(1)) if m else 1.0
```

> Note for the implementer: `_worker_full_base` exports with `frame_title` containing `scale=<v>` (see `ExportFold`, `TreemakerWrapper.cpp:901`). `_scale_from_fold` parses it — no new C++ binding. If a future refactor drops the title, expose `run_scale_optimization()`'s return instead (it already returns the scale).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp_harness && python -m pytest tests/test_flap_fill_tool.py -v`
Expected: PASS (2 tests). (These spawn the engine; allow ~60s.)

- [ ] **Step 5: Run the full harness suite (no regressions)**

Run: `cd mcp_harness && python -m pytest -q`
Expected: all green (≥ 212 prior + the new flap_fill tests).

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/server.py mcp_harness/tests/test_flap_fill_tool.py
git commit -m "feat(a9): suggest_flap_for_region self-verifying MCP tool"
```

---

### Task 6: Agent SYSTEM_PROMPT — suggest-then-confirm (HITL)

**Files:**
- Modify: `mcp_harness/agent_loop.py` (the SYSTEM_PROMPT "free-paper frontier" block added in A-2)
- Test: `mcp_harness/tests/test_agent_reference_prompt.py` (or the existing prompt-content test — match its style)

**Interfaces:**
- Consumes: nothing new at runtime; the tool is auto-discovered over MCP like the others.
- Produces: prompt text teaching the HITL flow. No code signature.

- [ ] **Step 1: Find the existing free-paper prompt block**

Run: `cd mcp_harness && grep -n "free.paper\|find_free_paper\|ACCEPT" agent_loop.py`
Expected: locates the A-2 ACCEPT block to extend.

- [ ] **Step 2: Write the failing test**

```python
# append to the existing prompt test module (match its import of SYSTEM_PROMPT)
def test_prompt_teaches_suggest_then_confirm():
    from agent_loop import SYSTEM_PROMPT
    p = SYSTEM_PROMPT.lower()
    assert "suggest_flap_for_region" in p
    assert "ask" in p and "approv" in p          # HITL: ask before filling
    assert "accept" in p                          # ACCEPT-as-default preserved
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd mcp_harness && python -m pytest tests/ -k suggest_then_confirm -v`
Expected: FAIL — `suggest_flap_for_region` not in prompt.

- [ ] **Step 4: Extend the prompt block**

Append to the existing free-paper block (keep the A-2 ACCEPT-default wording intact):

```
After a base compiles, you MAY use find_free_paper to look for uncreased
regions. If you find substantial free paper, NAME what it could become
(e.g. "room for ears near the head, a tail at the back") and ASK the user
whether to add it — do NOT add flaps unprompted. Only for regions the user
APPROVES, call suggest_flap_for_region(region=..., mirror_region=<the
mirror region for a bilateral feature>, name="<their words>",
desired_length=<optional size cue>). Report its result honestly: status
"filled" -> the flap was added and verified (show the updated 2D pattern);
status "accept" -> no flap converges there, so leave it as free paper. A
base with free paper is already a valid, foldable finished base (A-3); A-9
detail is optional polish, never required.
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd mcp_harness && python -m pytest tests/ -k suggest_then_confirm -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/agent_loop.py mcp_harness/tests/
git commit -m "feat(a9): teach agent the suggest-then-confirm HITL fill loop"
```

---

### Task 7: Debug probe + 2D-panel e2e verification

**Files:**
- Create: `mcp_harness/probe_flap_fill.py`
- Verify: `web/frontend` Playwright (existing harness) — manual/CI visual check

**Interfaces:**
- Consumes: `server.suggest_flap_for_region` (T5).
- Produces: a runnable probe (not a pytest test) printing before/after regions + the chosen candidate, matching the `probe_*.py` family.

- [ ] **Step 1: Write the probe**

```python
# mcp_harness/probe_flap_fill.py
"""Eyeball A-9: fill the largest free-paper region of a named case and print
before/after. Usage: python probe_flap_fill.py star-5
Not a pytest test — a developer probe (cf. probe_sweep.py, probe_verify.py)."""
import json
import sys
sys.path.insert(0, "tests")
from cases import CASES_BY_NAME
import server


def main(name="star-5"):
    nodes, pairs = CASES_BY_NAME[name]
    sp = [list(p) for p in pairs]
    before = json.loads(server.find_free_paper(tree_nodes=nodes, symmetric_pairs=sp))
    print(f"[{name}] regions before: {len(before)}")
    if not before:
        print("no free paper; nothing to fill"); return
    target = max(before, key=lambda r: r["area"])
    print(f"target area={target['area']:.3f} kind={target['kind']}")
    out = json.loads(server.suggest_flap_for_region(
        tree_nodes=nodes, region=target, symmetric_pairs=sp, name="probe-flap"))
    print(f"status={out['status']}")
    if out["status"] == "filled":
        print(f"added nodes={out['added_node_ids']} "
              f"regions after={len(out['regions_after'])}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "star-5")
```

- [ ] **Step 2: Run the probe (sanity)**

Run: `cd mcp_harness && python probe_flap_fill.py star-5`
Expected: prints `status=filled`, `regions after:` fewer/smaller than before.

- [ ] **Step 3: Manual 2D-panel verification (the visual proof the user asked for)**

Drive the web app (use the `/run` skill or existing dev server). In the chat, ask the agent to design a quadruped/bear, accept the base, then approve an "ears" suggestion. Confirm the **2D tab** (`CreasePanel`) re-renders with the new flap's creases after the fill. Capture a screenshot to `docs/a9-flap-fill-2d.png`.

- [ ] **Step 4: Run the full suite one final time**

Run: `cd mcp_harness && python -m pytest -q`
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/probe_flap_fill.py docs/a9-flap-fill-2d.png
git commit -m "chore(a9): flap-fill probe + 2D-panel e2e verification"
```

---

## Self-Review

**Spec coverage:**
- §2 `flap_fill.py` pure module → Tasks 1–4. ✓
- §2 `suggest_flap_for_region` self-verifying tool → Task 5. ✓
- §3 sibling-flap geometry (NCA + inradius/scale + candidate list) → Tasks 2, 3. ✓
- §3 branch flap deferred → not built (correct). ✓
- §4 verify loop (packs + well-formed + region shrank) + ACCEPT fallback → Tasks 4, 5. ✓
- §4 no Oriedita-clean gate → encoded as well-formedness + shrank only (Task 4/5). ✓
- §5 symmetry (atomic pair, shared length, both regions shrink) → Task 3 (emission) + Task 5 (both-targets check). ✓
- §6 HITL prompt + 2D panel (no panel code change) → Task 6 + Task 7 Step 3. ✓
- §7 testing (unit + pinned integration + probe + Playwright) → Tasks 1–7. ✓
- §8 YAGNI (no new compile path, no molecule/squaring/recursion) → honored; tool reuses existing workers, single cycle. ✓

**Placeholder scan:** No TBD/TODO; every code step has full code; the "still folds" gate is concretely defined as static well-formedness with physics-fold pushed to the Playwright step (honest, not a placeholder). ✓

**Type consistency:** `suggest` returns dicts with `new_nodes`/`new_pairs`/`attach_node_id`/`length`, consumed verbatim in Task 5. `region_shrank(target, regions_after, frac)`, `fold_is_wellformed(fold, w, h)`, `largest_inscribed_circle(polygon) -> (point, radius)`, `nearest_common_ancestor(nodes, a, b)`, `next_node_id(nodes)` — all used with matching signatures across tasks. Tool returns `status`/`tree_nodes`/`symmetric_pairs`/`fold`/`regions_after`/`added_node_ids` consistently. ✓

**One risk flagged for execution:** Task 5's `region_shrank` locale tolerance (0.08) and Task 4's `frac=0.5` are heuristics tuned for the 1×1 paper; if the star-5 integration test is flaky on the shrank check, widen the candidate list (add the parent-of-A/parent-of-B variants from §3) before loosening the gate — the gate is the correctness guarantee.
