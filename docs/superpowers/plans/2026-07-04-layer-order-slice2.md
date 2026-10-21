# Layer Ordering (Slice 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `mcp_harness/layer_order.py` — a partial layer order over the faces of a flat-folded state (`above(a,b) -> bool|None`, `stack_at(p)`), computed by generating Justin/Tachi non-crossing constraints and propagating them to fixpoint; forced relations are facts, free relations are honestly `None`.

**Architecture:** Three stages on top of slice 1's `FlatFoldResult`: (1) cell decomposition — overlay the folded convex faces into maximal regions of constant covering set via convex clipping; (2) constraint generation — crease-direction (M/V + face orientation), taco-tortilla, taco-taco, each with provenance; (3) propagation to fixpoint (equalities, taco case-elimination, per-cell transitivity), no search. Closure-inconsistent inputs are refused up front.

**Tech Stack:** Python 3 + numpy (existing dep). Tests: pytest, offline.

**Spec:** `docs/superpowers/specs/2026-07-04-layer-order-slice2-design.md`
**Consumes:** `flat_fold.flat_fold` (merged PR #26). **Cross-module note:** Task 1 adds an additive `shared_edges` field to `FlatFoldResult` — the crease-direction constraint needs M/V assignments, which geometry alone cannot recover (M and V reflect identically); `flat_fold()` already computes this data and currently discards it. The spec's `layer_order(result)` single-argument API is preserved by this.

## Global Constraints

- All commands run from `mcp_harness/`; the interpreter is `.venv/bin/python`.
- Test commands: `.venv/bin/python -m pytest tests/test_layer_order.py -q` (new file) and `tests/test_flat_fold.py` (must stay green — Task 1 touches `flat_fold.py` additively).
- numpy only — no new dependencies.
- Do NOT touch `web/*`, `agent_loop.py`, `server.py`, or the probe script. The module READS `FlatFoldResult`; it writes nothing (provenance contract).
- `ValueError` (including the `AmbiguousStack` subclass) is the only exception that may escape: closure-inconsistent input, non-convex face, propagation contradiction (with constraint provenance), ambiguous stack query.
- All measured pins (cell counts, constraint counts, star-4 center stack, per-fixture probe-point stacks) follow slice 1's rule: MEASURE from this implementation before writing the number into a test, and sanity-check as instructed in the step. Never guess.
- **Sign convention checkpoint:** the crease-direction rule (`neighbor above reference iff (assignment=='V') == (reference is face-up)`) is verified by the hand-derived V+M strip test (physical accordion: stack C,B,A top-to-bottom). If that test fails with the exact inverse stack, the convention constant is flipped ONCE in `_build_constraints` (documented in the commit message) and all tests re-run — do not "fix" the hand-derived expectation.

---

### Task 1: `shared_edges` on FlatFoldResult + geometry substrate (clipping, cells)

**Files:**
- Modify: `mcp_harness/flat_fold.py` (two small additive edits)
- Create: `mcp_harness/layer_order.py` (geometry half)
- Create: `mcp_harness/tests/test_layer_order.py`
- Modify: `mcp_harness/tests/test_flat_fold.py` (append one test)

**Interfaces:**
- Consumes: `flat_fold(fold) -> FlatFoldResult` (`.faces`, `.transforms`, `.folded_vertices`, `.closure`), internal `shared` list + `assign` dict inside `flat_fold()`.
- Produces: `FlatFoldResult.shared_edges: tuple[(fa:int, fb:int, edge:(v_lo,v_hi), assignment:str)]` (ALL shared edges, F included); in `layer_order.py`: `AREA_EPS=1e-9`, `GEOM_EPS=1e-9`, `_cross(u,v)->float`, `_area(P)->float`, `_is_convex(P)->bool`, `_strictly_inside(p,P)->bool`, `_clip_half(poly,a,b)->np.ndarray`, `_split_convex(subject,clip)->(inter|None, pieces)`, `_cells(polys)->list[(poly, frozenset)]`. Test helpers `strip_fold(a1,a2)`, `face_at(fold,result,p)`, `load_golden(name)`.

- [ ] **Step 1: Write the failing tests**

Create `mcp_harness/tests/test_layer_order.py`:

```python
"""Tests for layer_order.py (folded-state-first slice 2).

Spec: docs/superpowers/specs/2026-07-04-layer-order-slice2-design.md
Hand-derived fixtures: a 1x3 paper strip with two creases at x=1, x=2.
Both M and V reflect identically in flat_fold, so V+M and V+V strips
fold to the SAME geometry (all three unit faces stacked over [0,1]^2)
and differ only in layer order — V+M is the accordion (fully forced),
V+V leaves the outer pair genuinely free (spiral vs tuck are both
physically valid).
"""
import json
import os
from itertools import combinations

import numpy as np
import pytest

from flat_fold import flat_fold
from layer_order import (
    _cells,
    _is_convex,
    _split_convex,
    _strictly_inside,
)

GOLDENS = os.path.join(os.path.dirname(__file__), "goldens")


def load_golden(name):
    with open(os.path.join(GOLDENS, name)) as fh:
        return json.load(fh)


def strip_fold(a1, a2):
    """1x3 strip, creases at x=1 (a1) and x=2 (a2)."""
    return {
        "vertices_coords": [[0, 0], [1, 0], [2, 0], [3, 0],
                            [3, 1], [2, 1], [1, 1], [0, 1]],
        "edges_vertices": [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5],
                           [5, 6], [6, 7], [7, 0], [1, 6], [2, 5]],
        "edges_assignment": ["B", "B", "B", "B", "B", "B", "B", "B",
                             a1, a2],
    }


def face_at(fold, result, p):
    """Index of the face whose FLAT polygon strictly contains p."""
    V = np.asarray([v[:2] for v in fold["vertices_coords"]], dtype=float)
    for i, f in enumerate(result.faces):
        if _strictly_inside(p, V[f]):
            return i
    raise AssertionError(f"no face contains {p}")


class TestSharedEdges:
    def test_strip_shared_edges_carry_assignments(self):
        fold = strip_fold("V", "M")
        res = flat_fold(fold)
        assert len(res.shared_edges) == 2
        by_edge = {k: (fa, fb, a) for fa, fb, k, a in res.shared_edges}
        assert set(by_edge) == {(1, 6), (2, 5)}
        assert by_edge[(1, 6)][2] == "V"
        assert by_edge[(2, 5)][2] == "M"


class TestGeometry:
    def test_split_convex_partitions_area(self):
        sq = np.array([[0.0, 0], [2, 0], [2, 2], [0, 2]])
        off = np.array([[1.0, 1], [3, 1], [3, 3], [1, 3]])
        inter, pieces = _split_convex(sq, off)
        assert inter is not None
        total = abs(_area_of(inter)) + sum(abs(_area_of(p)) for p in pieces)
        assert abs(total - 4.0) < 1e-9          # partitions the subject
        assert abs(abs(_area_of(inter)) - 1.0) < 1e-9

    def test_split_convex_disjoint(self):
        sq = np.array([[0.0, 0], [1, 0], [1, 1], [0, 1]])
        far = np.array([[5.0, 5], [6, 5], [6, 6], [5, 6]])
        inter, pieces = _split_convex(sq, far)
        assert inter is None
        assert sum(abs(_area_of(p)) for p in pieces) == pytest.approx(1.0)

    def test_cells_identical_stack(self):
        # V+M strip folds all three faces onto [0,1]^2: exactly one cell
        res = flat_fold(strip_fold("V", "M"))
        polys = [_ccw(np.asarray(P)) for P in res.folded_vertices]
        cells = _cells(polys)
        assert len(cells) == 1
        assert cells[0][1] == frozenset({0, 1, 2})

    def test_cells_partial_overlap(self):
        a = np.array([[0.0, 0], [2, 0], [2, 2], [0, 2]])
        b = np.array([[1.0, 1], [3, 1], [3, 3], [1, 3]])
        cells = _cells([a, b])
        covers = sorted(tuple(sorted(c)) for _, c in cells)
        assert covers.count((0, 1)) == 1
        assert sum(abs(_area_of(p)) for p, c in cells if c == frozenset({0, 1})) \
            == pytest.approx(1.0)
        total = sum(abs(_area_of(p)) for p, _ in cells)
        assert total == pytest.approx(7.0)      # union area, disjoint cells

    def test_cells_cover_membership_is_consistent(self):
        # every cell's centroid must lie strictly inside exactly its cover
        res = flat_fold(load_golden("quad.fold"))
        polys = [_ccw(np.asarray(P)) for P in res.folded_vertices]
        cells = _cells(polys)
        for poly, cover in cells:
            if abs(_area_of(poly)) < 1e-6:
                continue     # sliver cells: centroid too close to
                             # boundaries for a 1e-9-tolerance check
            centroid = np.mean(poly, axis=0)
            inside = {i for i, fp in enumerate(polys)
                      if _strictly_inside(centroid, fp)}
            assert inside == set(cover)


def _area_of(P):
    x, y = P[:, 0], P[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def _ccw(P):
    return P if _area_of(P) > 0 else P[::-1]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_layer_order.py -q`
Expected: collection error — `ModuleNotFoundError: No module named 'layer_order'`.

- [ ] **Step 3: Add `shared_edges` to FlatFoldResult (additive)**

In `mcp_harness/flat_fold.py`, add a field to the dataclass:

```python
@dataclass(frozen=True, eq=False)
class FlatFoldResult:
    faces: list            # interior faces, CCW vertex-index lists
    transforms: list       # per-face 3x3 homogeneous 2D (flat -> folded)
    folded_vertices: list  # per-face Nx2 arrays; [i][j] is the image of
                           # faces[i][j] (a CP vertex has one image PER
                           # face it belongs to)
    closure: "ClosureReport"
    # every shared edge as (face_a, face_b, (v_lo, v_hi), assignment) —
    # layer ordering needs M/V labels, which folded geometry alone
    # cannot recover (M and V reflect identically)
    shared_edges: tuple = ()
```

and in `flat_fold()`'s return statement:

```python
    return FlatFoldResult(faces=faces, transforms=T,
                          folded_vertices=folded,
                          closure=ClosureReport(edge_errors=tuple(errors)),
                          shared_edges=tuple(
                              (fa, fb, k, assign.get(k, "F"))
                              for fa, fb, k in shared))
```

- [ ] **Step 4: Write the geometry half of layer_order.py**

Create `mcp_harness/layer_order.py`:

```python
"""Partial layer order of a flat-folded state (folded-state-first
slice 2): which face is forced above which by the non-crossing
conditions (crease direction, taco-tortilla, taco-taco), propagated to
fixpoint. Forced relations are facts; anything else is honestly None /
AmbiguousStack — no search, no invented tie-breaks.

Spec: docs/superpowers/specs/2026-07-04-layer-order-slice2-design.md
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import cmp_to_key
from itertools import combinations

import numpy as np

from flat_fold import FlatFoldResult

AREA_EPS = 1e-9   # cells/pieces smaller than this are dropped as noise
GEOM_EPS = 1e-9   # strict-interior / segment tolerance


class AmbiguousStack(ValueError):
    """stack_at() covering set is not totally ordered by FORCED
    relations; .free_pairs lists the genuinely unconstrained pairs."""

    def __init__(self, message: str, free_pairs: list):
        super().__init__(message)
        self.free_pairs = free_pairs


def _cross(u, v) -> float:
    return float(u[0] * v[1] - u[1] * v[0])


def _area(P: np.ndarray) -> float:
    x, y = P[:, 0], P[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def _is_convex(P: np.ndarray) -> bool:
    n = len(P)
    sign = 0
    for i in range(n):
        c = _cross(P[(i + 1) % n] - P[i], P[(i + 2) % n] - P[(i + 1) % n])
        if abs(c) < GEOM_EPS:
            continue
        s = 1 if c > 0 else -1
        if sign == 0:
            sign = s
        elif s != sign:
            return False
    return True


def _strictly_inside(p, P) -> bool:
    """p strictly interior to convex CCW polygon P (boundary excluded)."""
    q = np.asarray(p, dtype=float)
    n = len(P)
    return all(_cross(P[(i + 1) % n] - P[i], q - P[i]) > GEOM_EPS
               for i in range(n))


def _clip_half(poly: np.ndarray, a, b) -> np.ndarray:
    """Clip a convex polygon to the closed half-plane LEFT of line a->b."""
    out = []
    d = b - a
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        pin = _cross(d, p - a) >= -GEOM_EPS
        qin = _cross(d, q - a) >= -GEOM_EPS
        if pin:
            out.append(p)
        if pin != qin:
            e = q - p
            t = _cross(d, a - p) / _cross(d, e)
            out.append(p + t * e)
    return np.asarray(out) if out else np.empty((0, 2))


def _split_convex(subject: np.ndarray, clip: np.ndarray):
    """Partition convex `subject` by convex CCW `clip`: returns
    (intersection_or_None, outside_pieces). Pieces are convex and,
    together with the intersection, partition the subject (up to
    AREA_EPS slivers, which are dropped)."""
    pieces = []
    remaining = subject
    n = len(clip)
    for i in range(n):
        a, b = clip[i], clip[(i + 1) % n]
        if len(remaining) < 3:
            break
        outside = _clip_half(remaining, b, a)   # right of a->b
        if len(outside) >= 3 and abs(_area(outside)) > AREA_EPS:
            pieces.append(outside)
        remaining = _clip_half(remaining, a, b)
    inter = (remaining if len(remaining) >= 3
             and abs(_area(remaining)) > AREA_EPS else None)
    return inter, pieces


def _cells(polys: list) -> list:
    """Arrangement cells of a set of convex CCW polygons: maximal
    regions with a constant covering set, as (polygon, frozenset)."""
    cells: list = []
    for fi, poly in enumerate(polys):
        new = []
        rem = [poly]                    # parts of face fi not yet placed
        for cpoly, cover in cells:
            inter, outs = _split_convex(cpoly, poly)
            new.extend((o, cover) for o in outs)
            if inter is not None:
                new.append((inter, cover | frozenset({fi})))
            nrem = []
            for r in rem:
                _, outside = _split_convex(r, cpoly)
                nrem.extend(outside)
            rem = nrem
        new.extend((r, frozenset({fi})) for r in rem)
        cells = new
    return cells
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_layer_order.py -q`
Expected: `6 passed`.

- [ ] **Step 6: Append the shared_edges pin to test_flat_fold.py and run it**

Append to `TestCleanTier` in `mcp_harness/tests/test_flat_fold.py`:

```python
    def test_shared_edges_field(self):
        # additive slice-2 field: every shared edge with its assignment
        res = flat_fold(load_golden("star-4.fold"))
        assert len(res.shared_edges) == 8
        for fa, fb, k, a in res.shared_edges:
            assert a in ("M", "V", "B", "F")
            assert k[0] < k[1]
```

Run: `.venv/bin/python -m pytest tests/test_flat_fold.py -q`
Expected: `28 passed` (27 existing + 1).

- [ ] **Step 7: Commit**

```bash
git add flat_fold.py layer_order.py tests/test_layer_order.py tests/test_flat_fold.py
git commit -m "feat(layer-order): geometry substrate (cells via convex clipping) + shared_edges on FlatFoldResult"
```

---

### Task 2: Constraint generation (crease-direction, taco-tortilla, taco-taco)

**Files:**
- Modify: `mcp_harness/layer_order.py` (append)
- Modify: `mcp_harness/tests/test_layer_order.py` (append)

**Interfaces:**
- Consumes: Task 1's geometry helpers, `FlatFoldResult.shared_edges`.
- Produces: `_lit(x:int, f:int) -> ((lo,hi), flip:bool)` (literal for "x above f"), `_orientation(T)->int` (+1 face-up), `_clip_seg(seg, poly) -> (t0,t1)|None`, `_segs_interact(s1, s2)->bool`, `_Constraints` (frozen dataclass: `.pairs: frozenset`, `.direct: tuple[(lit,value,prov)]`, `.equalities: tuple[(litA,litB,prov)]`, `.tacos: tuple[((p,q),(r,s),prov)]`, `.covers: tuple[frozenset]`), `_build_constraints(result, polys, cells) -> _Constraints`. Task 3 consumes `_Constraints` and `_lit`.

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_layer_order.py` (extend the layer_order import to also name `_build_constraints, _cells, _clip_seg, _lit, _orientation, _segs_interact`):

```python
def _constraints_for(fold):
    res = flat_fold(fold)
    polys = [_ccw(np.asarray(P)) for P in res.folded_vertices]
    cells = _cells(polys)
    from layer_order import _build_constraints
    return res, _build_constraints(res, polys, cells)


class TestLit:
    def test_lit_canonicalization(self):
        assert _lit(2, 5) == ((2, 5), False)   # "2 above 5" is rel itself
        assert _lit(5, 2) == ((2, 5), True)    # "5 above 2" is NOT rel


class TestSegPredicates:
    def test_clip_seg_inside(self):
        sq = np.array([[0.0, 0], [1, 0], [1, 1], [0, 1]])
        span = _clip_seg((np.array([-1.0, 0.5]), np.array([2.0, 0.5])), sq)
        t0, t1 = span
        assert t0 == pytest.approx(1 / 3)
        assert t1 == pytest.approx(2 / 3)

    def test_clip_seg_outside(self):
        sq = np.array([[0.0, 0], [1, 0], [1, 1], [0, 1]])
        assert _clip_seg((np.array([2.0, 2]), np.array([3.0, 3])), sq) is None

    def test_segs_proper_cross(self):
        s1 = (np.array([0.0, 0]), np.array([2.0, 2]))
        s2 = (np.array([0.0, 2]), np.array([2.0, 0]))
        assert _segs_interact(s1, s2)

    def test_segs_collinear_overlap(self):
        s1 = (np.array([0.0, 0]), np.array([2.0, 0]))
        s2 = (np.array([1.0, 0]), np.array([3.0, 0]))
        assert _segs_interact(s1, s2)

    def test_segs_disjoint_and_touching(self):
        s1 = (np.array([0.0, 0]), np.array([1.0, 0]))
        s2 = (np.array([2.0, 0]), np.array([3.0, 0]))
        assert not _segs_interact(s1, s2)
        s3 = (np.array([1.0, 0]), np.array([2.0, 0]))   # endpoint touch
        assert not _segs_interact(s1, s3)


class TestConstraintGeneration:
    def test_strip_vm_direct_constraints(self):
        fold = strip_fold("V", "M")
        res, cons = _constraints_for(fold)
        A = face_at(fold, res, (0.5, 0.5))
        B = face_at(fold, res, (1.5, 0.5))
        C = face_at(fold, res, (2.5, 0.5))
        assert len(cons.direct) == 2
        # decode each direct constraint into canonical rel facts:
        # rel[(lo,hi)] means "lo above hi"; the stored value is the raw
        # proposition, so apply the literal's flip
        facts = {}
        for (pair, flip), value, _ in cons.direct:
            facts[pair] = (value != flip)
        ab = tuple(sorted((A, B)))
        bc = tuple(sorted((B, C)))
        # V at x=1: B above A; M at x=2 (B is face-down): C above B
        assert facts[ab] == (ab[0] == B)
        assert facts[bc] == (bc[0] == C)

    def test_strip_vv_direct_constraints_differ(self):
        fold = strip_fold("V", "V")
        res, cons = _constraints_for(fold)
        B = face_at(fold, res, (1.5, 0.5))
        C = face_at(fold, res, (2.5, 0.5))
        facts = {}
        for (pair, flip), value, _ in cons.direct:
            facts[pair] = (value != flip)
        bc = tuple(sorted((B, C)))
        # second V, reference face-down: C below B
        assert facts[bc] == (bc[0] == B)

    def test_strip_has_no_taco_constraints(self):
        # folded creases land exactly ON face boundaries (x=0 and x=1
        # edges) — strictly-inside filtering must exclude them
        _, cons = _constraints_for(strip_fold("V", "V"))
        assert cons.equalities == ()
        assert cons.tacos == ()

    def test_every_constraint_names_overlapping_pairs(self):
        res, cons = _constraints_for(load_golden("star-4.fold"))
        for (pair, _), _, _ in cons.direct:
            assert pair in cons.pairs
        for la, lb, _ in cons.equalities:
            assert la[0] in cons.pairs and lb[0] in cons.pairs
        for (p, q), (r, s), _ in cons.tacos:
            for x, f in ((r, p), (r, q), (s, p), (s, q)):
                assert tuple(sorted((x, f))) in cons.pairs
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_layer_order.py -q`
Expected: FAIL — `ImportError: cannot import name '_lit'` (or `_build_constraints`).

- [ ] **Step 3: Write the implementation**

Append to `mcp_harness/layer_order.py`:

```python
def _orientation(T: np.ndarray) -> int:
    """+1 = face-up (even number of reflections), -1 = face-down."""
    return 1 if float(np.linalg.det(T[:2, :2])) > 0 else -1


def _lit(x: int, f: int):
    """Literal for the proposition 'face x is above face f', expressed
    over the canonical pair variable rel[(lo,hi)] = 'lo above hi'.
    Returns (pair, flip): the proposition's value is rel[pair] != flip."""
    return ((x, f), False) if x < f else ((f, x), True)


def _clip_seg(seg, poly: np.ndarray):
    """Parametric span (t0,t1) of the segment inside a convex CCW
    polygon, or None when the intersection is empty/degenerate."""
    p0 = np.asarray(seg[0], dtype=float)
    d = np.asarray(seg[1], dtype=float) - p0
    t0, t1 = 0.0, 1.0
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        e = b - a
        denom = _cross(e, d)
        num = _cross(e, p0 - a)          # >0: p0 on the inside of edge
        if abs(denom) < GEOM_EPS:
            if num < -GEOM_EPS:
                return None              # parallel and fully outside
            continue
        t = -num / denom
        if denom > 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
    return (t0, t1) if t1 - t0 > GEOM_EPS else None


def _segs_interact(s1, s2) -> bool:
    """True when the segments properly cross, or are collinear with
    overlapping interiors (endpoint-touching does not count)."""
    p, q = np.asarray(s1[0], float), np.asarray(s1[1], float)
    r, s = np.asarray(s2[0], float), np.asarray(s2[1], float)
    d1, d2 = q - p, s - r
    o1, o2 = _cross(d1, r - p), _cross(d1, s - p)
    o3, o4 = _cross(d2, p - r), _cross(d2, q - r)
    if all(abs(o) < GEOM_EPS for o in (o1, o2, o3, o4)):
        length = float(np.hypot(*d1))
        if length < GEOM_EPS:
            return False
        u = d1 / length
        b0, b1 = sorted((float(np.dot(r - p, u)), float(np.dot(s - p, u))))
        return min(length, b1) - max(0.0, b0) > GEOM_EPS
    strad1 = (o1 > GEOM_EPS and o2 < -GEOM_EPS) or \
             (o1 < -GEOM_EPS and o2 > GEOM_EPS)
    strad2 = (o3 > GEOM_EPS and o4 < -GEOM_EPS) or \
             (o3 < -GEOM_EPS and o4 > GEOM_EPS)
    return strad1 and strad2


@dataclass(frozen=True)
class _Constraints:
    pairs: frozenset      # canonical overlapping face pairs
    direct: tuple         # (lit, value, provenance)
    equalities: tuple     # (litA, litB, provenance): values must be equal
    tacos: tuple          # ((p,q),(r,s), prov): between(r;p,q)==between(s;p,q)
    covers: tuple         # frozenset per cell


def _build_constraints(result: FlatFoldResult, polys: list,
                       cells: list) -> _Constraints:
    covers = tuple(c for _, c in cells)
    pairs = frozenset(pr for c in covers
                      for pr in combinations(sorted(c), 2))
    orient = [_orientation(T) for T in result.transforms]

    creases = []
    for fa, fb, k, a in result.shared_edges:
        if a not in ("M", "V"):
            continue
        face = result.faces[fa]
        i0, i1 = face.index(k[0]), face.index(k[1])
        seg = (np.asarray(result.folded_vertices[fa][i0], float),
               np.asarray(result.folded_vertices[fa][i1], float))
        creases.append((fa, fb, a, seg, k))

    direct, eqs, tacos = [], [], []
    for fa, fb, a, seg, k in creases:
        if tuple(sorted((fa, fb))) in pairs:
            # Crease direction: a V fold (toward +z, seen from the
            # face-up side) puts the neighbor ABOVE the reference face;
            # M puts it below; a face-down reference flips the sense.
            # (Sign convention pinned by the hand-derived strip test.)
            val = (a == "V") == (orient[fa] == 1)   # "fb above fa"
            direct.append((_lit(fb, fa), val, f"crease {k} {a}"))
        for x in range(len(polys)):
            if x in (fa, fb):
                continue
            if tuple(sorted((x, fa))) not in pairs:
                continue
            if tuple(sorted((x, fb))) not in pairs:
                continue
            span = _clip_seg(seg, polys[x])
            if span is None:
                continue
            mid = seg[0] + ((span[0] + span[1]) / 2.0) * (seg[1] - seg[0])
            if not _strictly_inside(mid, polys[x]):
                continue     # crease lies ON x's boundary: no tortilla
            eqs.append((_lit(x, fa), _lit(x, fb),
                        f"taco-tortilla crease {k} through face {x}"))
    for c1, c2 in combinations(creases, 2):
        fa1, fb1, _, s1, k1 = c1
        fa2, fb2, _, s2, k2 = c2
        if not _segs_interact(s1, s2):
            continue
        quad = ((fa2, fa1), (fa2, fb1), (fb2, fa1), (fb2, fb1))
        if any(tuple(sorted(pq)) not in pairs for pq in quad):
            continue
        tacos.append(((fa1, fb1), (fa2, fb2), f"taco-taco {k1}x{k2}"))
        tacos.append(((fa2, fb2), (fa1, fb1), f"taco-taco {k2}x{k1}"))
    return _Constraints(pairs=pairs, direct=tuple(direct),
                        equalities=tuple(eqs), tacos=tuple(tacos),
                        covers=covers)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_layer_order.py -q`
Expected: `16 passed` (6 from Task 1 + 10 new).

- [ ] **Step 5: Commit**

```bash
git add layer_order.py tests/test_layer_order.py
git commit -m "feat(layer-order): non-crossing constraint generation with provenance"
```

---

### Task 3: Propagation + LayerOrder API (`layer_order`, `above`, `stack_at`)

**Files:**
- Modify: `mcp_harness/layer_order.py` (append)
- Modify: `mcp_harness/tests/test_layer_order.py` (append)

**Interfaces:**
- Consumes: `_Constraints`, `_lit`, `_cells`, geometry helpers.
- Produces: `_propagate(cons) -> dict[(lo,hi), bool]`, `class LayerOrder` (`.above(a,b)->bool|None`, `.stack_at(p)->list[int]`, `.cells -> list[(np.ndarray, frozenset)]`), `layer_order(result) -> LayerOrder`, `AmbiguousStack` already defined in Task 1. Task 4 consumes `layer_order` and `LayerOrder`.

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_layer_order.py` (extend imports to add `AmbiguousStack, LayerOrder, layer_order`):

```python
class TestHandDerivedStrips:
    def test_vm_accordion_fully_forced(self):
        # V then M = accordion/zigzag: stack C,B,A top-to-bottom.
        # THIS TEST PINS THE SIGN CONVENTION — if it fails with the
        # exact inverse stack [A,B,C], flip the convention in
        # _build_constraints once (see plan Global Constraints), never
        # this expectation.
        fold = strip_fold("V", "M")
        res = flat_fold(fold)
        layers = layer_order(res)
        A = face_at(fold, res, (0.5, 0.5))
        B = face_at(fold, res, (1.5, 0.5))
        C = face_at(fold, res, (2.5, 0.5))
        assert layers.above(B, A) is True
        assert layers.above(C, B) is True
        assert layers.above(C, A) is True          # via transitivity
        assert layers.stack_at((0.5, 0.5)) == [C, B, A]

    def test_vv_outer_pair_genuinely_free(self):
        # V then V: B above A and C below B are forced; A-vs-C is
        # genuinely free (spiral and tuck are both physically valid)
        fold = strip_fold("V", "V")
        res = flat_fold(fold)
        layers = layer_order(res)
        A = face_at(fold, res, (0.5, 0.5))
        B = face_at(fold, res, (1.5, 0.5))
        C = face_at(fold, res, (2.5, 0.5))
        assert layers.above(B, A) is True
        assert layers.above(B, C) is True
        assert layers.above(A, C) is None
        assert layers.above(C, A) is None
        with pytest.raises(AmbiguousStack) as exc:
            layers.stack_at((0.5, 0.5))
        assert exc.value.free_pairs == [tuple(sorted((A, C)))]


class TestContract:
    def test_bear_refused_with_closure_count(self):
        res = flat_fold(load_golden("bear-base.fold"))
        with pytest.raises(ValueError, match=r"15 closure-inconsistent"):
            layer_order(res)

    def test_squared_dog_refused(self):
        import square_complete
        fold = load_golden("dog.fold")
        squared = square_complete.complete_square(
            json.loads(json.dumps(fold)), 1.0, 1.0)
        with pytest.raises(ValueError, match="closure-inconsistent"):
            layer_order(flat_fold(squared))

    def test_above_antisymmetry_and_nonoverlap(self):
        fold = strip_fold("V", "M")
        res = flat_fold(fold)
        layers = layer_order(res)
        A = face_at(fold, res, (0.5, 0.5))
        B = face_at(fold, res, (1.5, 0.5))
        assert layers.above(A, B) is (not layers.above(B, A))
        assert layers.above(A, A) is None      # a face vs itself: no pair

    def test_stack_at_uncovered_point(self):
        res = flat_fold(strip_fold("V", "M"))
        layers = layer_order(res)
        assert layers.stack_at((10.0, 10.0)) == []

    def test_deterministic(self):
        fold = load_golden("star-4.fold")
        res = flat_fold(fold)
        l1, l2 = layer_order(res), layer_order(res)
        pairs = sorted(l1._pairs)
        assert pairs == sorted(l2._pairs)
        assert all(l1.above(a, b) == l2.above(a, b) for a, b in pairs)

    def test_cells_property_shape(self):
        res = flat_fold(strip_fold("V", "M"))
        layers = layer_order(res)
        cells = layers.cells
        assert len(cells) == 1
        point, cover = cells[0]
        assert cover == frozenset({0, 1, 2})
        assert point.shape == (2,)


class TestStar4Center:
    def test_center_stack_is_measured_total_order(self):
        # Measured pin (plan Task 3 Step 4): the star-4 fan at a point
        # near the folded center. Sanity requirements enforced here:
        # a total order over all faces covering the point, and every
        # ADJACENT-in-stack crease-connected pair must match the
        # crease-direction rule (hand-checkable from the M/V labels).
        res = flat_fold(load_golden("star-4.fold"))
        layers = layer_order(res)
        stack = layers.stack_at(STAR4_PROBE_POINT)
        assert stack == STAR4_EXPECTED_STACK
```

And near the top of the file (after `GOLDENS = ...`) add the measured-pin constants with placeholder-free initial values to be REPLACED in Step 4:

```python
# Measured pins (Task 3 Step 4 prints these; see plan). The probe point
# is an interior point of the deepest star-4 cell; the stack is the
# propagator's forced total order there, hand-checked pairwise.
STAR4_PROBE_POINT = (0.75, 0.75)
STAR4_EXPECTED_STACK = [0, 1, 2, 3, 4, 5, 6, 7]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_layer_order.py -q`
Expected: FAIL — `ImportError: cannot import name 'layer_order'`.

- [ ] **Step 3: Write the implementation**

Append to `mcp_harness/layer_order.py`:

```python
def _propagate(cons: _Constraints) -> dict:
    """Fixpoint propagation. Returns rel: {(lo,hi): bool} for FORCED
    pairs only. Raises ValueError (with provenance) on contradiction."""
    rel: dict = {}

    def get(lit):
        pair, flip = lit
        v = rel.get(pair)
        return None if v is None else (v != flip)

    def put(lit, value, prov) -> bool:
        pair, flip = lit
        v = (value != flip)
        if pair in rel:
            if rel[pair] != v:
                raise ValueError(f"layer-order contradiction via {prov}")
            return False
        rel[pair] = v
        return True

    for lit, val, prov in cons.direct:
        put(lit, val, prov)
    changed = True
    while changed:
        changed = False
        for la, lb, prov in cons.equalities:
            va, vb = get(la), get(lb)
            if va is None and vb is not None:
                changed |= put(la, vb, prov)
            elif vb is None and va is not None:
                changed |= put(lb, va, prov)
            elif va is not None and vb is not None and va != vb:
                raise ValueError(f"layer-order contradiction via {prov}")
        for (p, q), (r, s), prov in cons.tacos:
            lits = (_lit(r, p), _lit(r, q), _lit(s, p), _lit(s, q))
            vals = [get(li) for li in lits]
            known = [v is not None for v in vals]
            if all(known):
                if (vals[0] != vals[1]) != (vals[2] != vals[3]):
                    raise ValueError(
                        f"layer-order contradiction via {prov}")
            elif sum(known) == 3:
                m = known.index(False)
                if m in (0, 1):
                    straddles = vals[2] != vals[3]
                    other = vals[1 - m]
                else:
                    straddles = vals[0] != vals[1]
                    other = vals[5 - m]
                changed |= put(lits[m],
                               (not other) if straddles else other, prov)
        for cover in cons.covers:
            for a, b, c in combinations(sorted(cover), 3):
                for x, y, z in ((a, b, c), (a, c, b), (b, a, c),
                                (b, c, a), (c, a, b), (c, b, a)):
                    if (get(_lit(x, y)) is True
                            and get(_lit(y, z)) is True
                            and get(_lit(x, z)) is None):
                        changed |= put(_lit(x, z), True,
                                       f"transitivity {x}>{y}>{z}")
    return rel


class LayerOrder:
    """Partial layer order: forced relations only (see module doc)."""

    def __init__(self, rel: dict, pairs: frozenset, cells: list,
                 polys: list):
        self._rel = rel
        self._pairs = pairs
        self._raw_cells = cells
        self._polys = polys

    @property
    def cells(self):
        return [(np.mean(poly, axis=0), cover)
                for poly, cover in self._raw_cells]

    def above(self, a: int, b: int):
        pr = (a, b) if a < b else (b, a)
        if a == b or pr not in self._pairs:
            return None
        v = self._rel.get(pr)
        if v is None:
            return None
        return v if a < b else (not v)

    def stack_at(self, p) -> list:
        cover = sorted(i for i, poly in enumerate(self._polys)
                       if _strictly_inside(p, poly))
        if not cover:
            return []
        free = [(a, b) for a, b in combinations(cover, 2)
                if self.above(a, b) is None]
        if free:
            raise AmbiguousStack(
                f"stack at {tuple(np.asarray(p))} has {len(free)} "
                f"unforced pair(s)", free)
        return sorted(cover, key=cmp_to_key(
            lambda a, b: -1 if self.above(a, b) else 1))


def layer_order(result: FlatFoldResult) -> LayerOrder:
    """Partial layer order of a consistent flat-folded state.

    Raises ValueError when the folded state is closure-inconsistent
    (layers only exist where the fold does), when a face is non-convex,
    or when constraint propagation derives a contradiction."""
    bad = result.closure.bad_edges
    if bad:
        raise ValueError(
            f"cannot order layers: folded state has {len(bad)} "
            f"closure-inconsistent edges (no consistent flat-fold "
            f"exists for this input)")
    polys = []
    for i, P in enumerate(result.folded_vertices):
        P = np.asarray(P, dtype=float)
        if _area(P) < 0:
            P = P[::-1]       # reflected faces wind CW: normalize to CCW
        if not _is_convex(P):
            raise ValueError(f"face {i} is non-convex; layer ordering "
                             f"supports convex faces only")
        polys.append(P)
    cells = _cells(polys)
    cons = _build_constraints(result, polys, cells)
    rel = _propagate(cons)
    return LayerOrder(rel, cons.pairs, cells, polys)
```

- [ ] **Step 4: Measure the star-4 pin (and verify the strips by hand)**

Run:

```bash
.venv/bin/python -c "
import json
import numpy as np
from flat_fold import flat_fold
from layer_order import layer_order, AmbiguousStack
res = flat_fold(json.load(open('tests/goldens/star-4.fold')))
layers = layer_order(res)
best = max(layers.cells, key=lambda c: len(c[1]))
pt = tuple(np.round(best[0], 6))
print('probe point:', pt, 'cover size:', len(best[1]))
try:
    print('stack:', layers.stack_at(best[0]))
except AmbiguousStack as e:
    print('AMBIGUOUS:', len(e.free_pairs), 'free pairs:', e.free_pairs)
print('creases (fa, fb, edge, assign):')
for fa, fb, k, a in res.shared_edges:
    if a in ('M', 'V'):
        print(' ', fa, fb, k, a)"
```

Then:
- Set `STAR4_PROBE_POINT` to the printed probe point and `STAR4_EXPECTED_STACK` to the printed stack. If the deepest cell is AMBIGUOUS, replace `TestStar4Center`'s body with a pin of the free-pair count at that point (an honest result is a valid result) and note it in the commit message.
- Sanity: hand-check at least two adjacent-in-stack pairs that are crease-connected against the crease table printed above (V with face-up reference → neighbor above; M → below; face-down flips). If a hand-check contradicts the stack, STOP: sign-convention bug — see Global Constraints.

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_layer_order.py -q`
Expected: `25 passed` (16 + 9 new: 2 strips + 6 contract + 1 star pin).

- [ ] **Step 6: Confirm flat_fold suite still green**

Run: `.venv/bin/python -m pytest tests/test_flat_fold.py -q`
Expected: `28 passed`.

- [ ] **Step 7: Commit**

```bash
git add layer_order.py tests/test_layer_order.py
git commit -m "feat(layer-order): fixpoint propagation + LayerOrder point-query API"
```

---

### Task 4: Independent checker + self-consistency tier + fixture pins

**Files:**
- Modify: `mcp_harness/tests/test_layer_order.py` (append)

**Interfaces:**
- Consumes: `layer_order`, `LayerOrder`, `flat_fold`, `FlatFoldResult.shared_edges`.
- Produces: test-local `check_order(fold_or_result, layers)` — an independent validator implemented against the constraint DEFINITIONS in the spec §3, sharing no layer_order.py code beyond `_strictly_inside`-equivalent local helpers.

- [ ] **Step 1: Write the checker and the failing tests**

Append to `mcp_harness/tests/test_layer_order.py`:

```python
# ---------------------------------------------------------------------
# Independent checker: validates a LayerOrder's FORCED relations against
# the constraint definitions (spec §3 stage 2) using its own primitive
# helpers — it reads layers.above() but shares none of the module's
# constraint/propagation code.

def _chk_inside(p, P):
    n = len(P)
    q = np.asarray(p, dtype=float)
    return all((P[(i + 1) % n][0] - P[i][0]) * (q[1] - P[i][1])
               - (P[(i + 1) % n][1] - P[i][1]) * (q[0] - P[i][0]) > 1e-9
               for i in range(n))


def check_order(fold, layers):
    res = flat_fold(fold)
    polys = [_ccw(np.asarray(P)) for P in res.folded_vertices]
    orient = [1 if np.linalg.det(T[:2, :2]) > 0 else -1
              for T in res.transforms]
    # 1. acyclicity: forced relations admit consistent heights per cell
    for point, cover in layers.cells:
        faces = sorted(cover)
        graph = {f: {g for g in faces if layers.above(f, g) is True}
                 for f in faces}
        seen, done = set(), set()

        def dfs(u):
            seen.add(u)
            for v in graph[u]:
                assert v not in seen or v in done, \
                    f"cycle in forced order within cell at {point}"
                if v not in done:
                    dfs(v)
            done.add(u)

        for f in faces:
            if f not in done:
                dfs(f)
    # 2. crease-direction rule, independently recomputed
    for fa, fb, k, a in res.shared_edges:
        if a not in ("M", "V"):
            continue
        got = layers.above(fb, fa)
        if got is None:
            continue                      # pair may not overlap
        expected = (a == "V") == (orient[fa] == 1)
        assert got == expected, f"crease rule violated at {k} ({a})"
    # 3. taco-tortilla by sampling folded crease midpoints: any face
    # strictly containing the midpoint must not separate the pair
    for fa, fb, k, a in res.shared_edges:
        if a not in ("M", "V"):
            continue
        face = res.faces[fa]
        i0, i1 = face.index(k[0]), face.index(k[1])
        mid = (np.asarray(res.folded_vertices[fa][i0])
               + np.asarray(res.folded_vertices[fa][i1])) / 2.0
        for x in range(len(polys)):
            if x in (fa, fb) or not _chk_inside(mid, polys[x]):
                continue
            va, vb = layers.above(x, fa), layers.above(x, fb)
            if va is not None and vb is not None:
                assert va == vb, \
                    f"face {x} separates taco {k}: {va} vs {vb}"


CONSISTENT_FIXTURES = ["quad.fold", "hshape.fold", "dog.fold",
                       "star-4.fold"]


class TestSelfConsistency:
    @pytest.mark.parametrize("name", CONSISTENT_FIXTURES)
    def test_forced_relations_satisfy_constraints(self, name):
        fold = load_golden(name)
        layers = layer_order(flat_fold(fold))
        check_order(fold, layers)

    def test_strips_pass_checker_too(self):
        for a1, a2 in (("V", "M"), ("V", "V"), ("M", "M"), ("M", "V")):
            fold = strip_fold(a1, a2)
            check_order(fold, layer_order(flat_fold(fold)))


class TestFixturePins:
    # Measured drift tripwires (Task 4 Step 3 prints these): the stack
    # or honest ambiguity at the deepest cell of each real fixture.
    def test_dog_deepest_cell(self):
        layers = layer_order(flat_fold(load_golden("dog.fold")))
        point, cover = max(layers.cells, key=lambda c: len(c[1]))
        assert len(cover) == DOG_DEEPEST_COVER
        try:
            stack = layers.stack_at(point)
            assert DOG_DEEPEST_RESULT == ("stack", stack)
        except AmbiguousStack as e:
            assert DOG_DEEPEST_RESULT == ("free", len(e.free_pairs))

    def test_quad_deepest_cell(self):
        layers = layer_order(flat_fold(load_golden("quad.fold")))
        point, cover = max(layers.cells, key=lambda c: len(c[1]))
        assert len(cover) == QUAD_DEEPEST_COVER
        try:
            stack = layers.stack_at(point)
            assert QUAD_DEEPEST_RESULT == ("stack", stack)
        except AmbiguousStack as e:
            assert QUAD_DEEPEST_RESULT == ("free", len(e.free_pairs))
```

And near the measured-pin constants at the top, add (values REPLACED in Step 3):

```python
DOG_DEEPEST_COVER = 0
DOG_DEEPEST_RESULT = ("stack", [])
QUAD_DEEPEST_COVER = 0
QUAD_DEEPEST_RESULT = ("stack", [])
```

- [ ] **Step 2: Run tests to verify the new ones fail**

Run: `.venv/bin/python -m pytest tests/test_layer_order.py -q`
Expected: the two `TestFixturePins` tests FAIL on the placeholder constants (cover sizes are certainly not 0); `TestSelfConsistency` may pass (the checker validates already-working code — its falsifiability is established in Step 4).

- [ ] **Step 3: Measure and set the fixture pins**

Run:

```bash
.venv/bin/python -c "
import json
import numpy as np
from flat_fold import flat_fold
from layer_order import layer_order, AmbiguousStack
for name in ('dog', 'quad'):
    layers = layer_order(flat_fold(json.load(
        open(f'tests/goldens/{name}.fold'))))
    point, cover = max(layers.cells, key=lambda c: len(c[1]))
    print(name, 'deepest cover:', len(cover), 'at', np.round(point, 4))
    try:
        print(' ', ('stack', layers.stack_at(point)))
    except AmbiguousStack as e:
        print(' ', ('free', len(e.free_pairs)))"
```

Set `DOG_DEEPEST_COVER`/`DOG_DEEPEST_RESULT` and `QUAD_DEEPEST_COVER`/`QUAD_DEEPEST_RESULT` to the printed values. These are drift tripwires: an honest `('free', N)` is as valid a pin as a stack. Record the measured values in the commit message.

- [ ] **Step 4: Falsify the checker once**

Temporarily break the crease-direction convention in `_build_constraints` (swap `val = (a == "V") == (orient[fa] == 1)` to `!=`), run:

`.venv/bin/python -m pytest tests/test_layer_order.py -q`

Expected: FAILURES — at minimum `test_vm_accordion_fully_forced` (hand tier) and, if any forced crease pair exists on the goldens, `TestSelfConsistency` via the checker's crease rule. Confirm the checker itself catches the inversion on at least one fixture (its assertion message names the crease). Restore the `==` and re-run to green. Record in the report which tests caught it.

- [ ] **Step 5: Run the full new file + neighbors**

Run: `.venv/bin/python -m pytest tests/test_layer_order.py tests/test_flat_fold.py -q`
Expected: `60 passed` total — 32 in test_layer_order (25 + 7 new: 4 parametrized self-consistency + 1 strips + 2 pins) + 28 in test_flat_fold.

- [ ] **Step 6: Commit**

```bash
git add tests/test_layer_order.py
git commit -m "test(layer-order): independent constraint checker + measured fixture pins"
```

---

## Final verification (after all tasks)

- [ ] Full backend suite: `.venv/bin/python -m pytest tests -q` (~10 min, real compiles) — expected `346 passed / 3 skipped` (313 at branch time + 32 layer_order + 1 flat_fold; report exact count).
- [ ] `git diff origin/main --stat` shows only: `mcp_harness/layer_order.py`, `mcp_harness/flat_fold.py`, `mcp_harness/tests/test_layer_order.py`, `mcp_harness/tests/test_flat_fold.py`, plus the spec/plan docs.
- [ ] Final whole-branch review (most capable model), then finishing-a-development-branch.
