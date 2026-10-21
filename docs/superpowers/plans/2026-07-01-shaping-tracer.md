# Honest-Shaping Tracer (B1+B3+B4) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Apply a real tip-local inside reverse fold (new creases + 3D fold angles) to the compiled base at the display boundary, so the Model tab shows a genuinely 3D posed model, validated by a paper-strain oracle.

**Architecture:** New pure-geometry module `mcp_harness/shaping.py` transforms the squared FOLD dict (insert wedge creases, emit full `edges_foldAngle`); `web/server.py` calls it on `display_json` when `IDE_SHAPE_OP` is set (mirroring `square_complete`'s provenance contract — raw `json` untouched). The unchanged A1–A3 pipeline folds/captures it; `ide-bridge.js` additionally returns flat positions so `extraction.ts` can reject captures whose max edge strain exceeds a threshold.

**Tech Stack:** Python (stdlib only, pytest), vanilla JS (vendored sim bridge), TypeScript + vitest (frontend).

**Spec:** `docs/superpowers/specs/2026-07-01-shaping-tracer-b1-b3-b4-design.md` — read it first.

## Global Constraints

- Work on branch `feat/shaping-tracer` cut from `feat/cad-render-a1-a3` (the A1–A3 substrate).
- `shaping.py` is pure geometry: stdlib only, no engine/MCP imports, never mutates its input dict.
- Failure contract: `apply_display_op` NEVER raises; any precondition failure returns the input unchanged. With `IDE_SHAPE_OP` unset, server behavior must be byte-identical to today.
- Angle model (fixed for this tracer): `s = +1` if the flap's axial crease is `V` else `-1`; wedge arms `s*theta`; tip-side axial `s*(180 - 2*theta)`; body-side axial `s*180`. Wedge half-angle `gamma = 45°` default.
- Python tests: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_shaping.py -v`. Frontend tests: `cd web/frontend && npm test`.
- Commit after every task (message style: `feat(shaping): …` / `fix(shaping): …`).

---

### Task 0: Branch

- [ ] **Step 1: Create the working branch**

```bash
cd <repo>
git checkout feat/cad-render-a1-a3 && git checkout -b feat/shaping-tracer
```

---

### Task 1: `shaping.py` — op parsing + flap-tip location

**Files:**
- Create: `mcp_harness/shaping.py`
- Test: `mcp_harness/tests/test_shaping.py`

**Interfaces:**
- Produces: `ShapingError(ValueError)`; `parse_op(op: str) -> ((x, y), d, theta)`; `_find_tip(fold: dict, tip_xy) -> (tip_vertex_index, axial_edge_index)`; module constants `EPS = 1e-9`, `SNAP = 1e-7`.
- A "flap tip" is a vertex with ≥1 `B` edge, exactly ONE `M`/`V` crease (the axial), and no other edge kinds beyond `B`/`F`. This deliberately accepts post-`square_complete` tips, whose hull-chord edges are `F` (see `test_square_complete.py::test_corner_cutting_chord_becomes_flat`).

- [ ] **Step 1: Write the failing tests**

Create `mcp_harness/tests/test_shaping.py`:

```python
import pytest
import shaping

# Unit-square paper. Flap tip at (1.0, 0.5) on the right edge, axial V
# crease running inward to (0.5, 0.5). (Vertex 5 dangles — fine: these
# tests exercise pure crease-pattern geometry, nothing renders it.)
TIP_SQUARE = {
    "vertices_coords": [[0, 0], [1, 0], [1, 0.5], [1, 1], [0, 1], [0.5, 0.5]],
    "edges_vertices": [[0, 1], [1, 2], [2, 3], [3, 4], [4, 0], [2, 5]],
    "edges_assignment": ["B", "B", "B", "B", "B", "V"],
}


def test_parse_op_roundtrip():
    assert shaping.parse_op("reverse:1.0,0.5:0.2:90") == ((1.0, 0.5), 0.2, 90.0)


@pytest.mark.parametrize("bad", [
    "narrow:1,0.5:0.2:90",      # unknown op
    "reverse:1,0.5:0.2",        # missing theta
    "reverse:1;0.5:0.2:90",     # bad tuple
    "reverse:1,0.5:-0.1:90",    # d <= 0
    "reverse:1,0.5:0.2:0",      # theta out of (0, 180]
    "reverse:1,0.5:0.2:181",
])
def test_parse_op_rejects(bad):
    with pytest.raises(shaping.ShapingError):
        shaping.parse_op(bad)


def test_find_tip_picks_nearest_tip_vertex():
    tip, axial = shaping._find_tip(TIP_SQUARE, (0.98, 0.52))
    assert tip == 2
    assert TIP_SQUARE["edges_vertices"][axial] == [2, 5]


def test_find_tip_rejects_creaseless_pattern():
    square = {
        "vertices_coords": [[0, 0], [1, 0], [1, 1], [0, 1]],
        "edges_vertices": [[0, 1], [1, 2], [2, 3], [3, 0]],
        "edges_assignment": ["B", "B", "B", "B"],
    }
    with pytest.raises(shaping.ShapingError):
        shaping._find_tip(square, (1.0, 0.5))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_shaping.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'shaping'`.

- [ ] **Step 3: Write the implementation**

Create `mcp_harness/shaping.py`:

```python
"""Honest shaping ops on FOLD crease patterns (Pillar B tracer).

reverse_fold() adds a tip-local inside reverse fold to a (squared) crease
pattern: REAL new creases (a symmetric wedge) plus 3D fold angles, so the
Origami Simulator poses the flap out of plane. Pure geometry — stdlib
only, no engine access, input dict never mutated. Applied at the DISPLAY
boundary (web/server.py) after square_complete, mirroring its provenance
contract: the raw linted `json` is never touched.
See docs/superpowers/specs/2026-07-01-shaping-tracer-b1-b3-b4-design.md.

Angle model (calibration start; the frontend strain oracle is the judge):
with s = +1 if the flap's axial crease is V else -1, theta in (0, 180]:
  body-side axial : s*180 (unchanged full fold)
  tip-side axial  : s*(180 - 2*theta)
  wedge arms      : s*theta
theta=180 is the classic flat inside reverse fold (Maekawa holds at the
new degree-4 vertex: 3+1 crease parity); theta=90 stands the tip section
perpendicular with the spine momentarily open.
"""
from __future__ import annotations

import math

EPS = 1e-9
SNAP = 1e-7   # refuse wedge hits this close to an existing vertex


class ShapingError(ValueError):
    """Precondition or degeneracy: op refused, caller keeps the input."""


def parse_op(op: str):
    """'reverse:X,Y:D:THETA' -> ((x, y), d, theta). Raises ShapingError."""
    parts = op.strip().split(":")
    if len(parts) != 4 or parts[0] != "reverse":
        raise ShapingError(f"unrecognized shape op: {op!r}")
    try:
        x, y = (float(t) for t in parts[1].split(","))
        d, theta = float(parts[2]), float(parts[3])
    except ValueError as exc:
        raise ShapingError(f"bad shape-op numbers: {op!r}") from exc
    if d <= 0 or not 0 < theta <= 180:
        raise ShapingError("need d > 0 and 0 < theta <= 180")
    return (x, y), d, theta


def _incidence(fold: dict) -> dict:
    inc: dict = {}
    for ei, (a, b) in enumerate(fold["edges_vertices"]):
        inc.setdefault(a, []).append(ei)
        inc.setdefault(b, []).append(ei)
    return inc


def _find_tip(fold: dict, tip_xy):
    """Nearest flap-tip vertex: >=1 B edge, exactly ONE M/V crease (the
    flap's axial crease), any other edges B/F (post-squaring tips carry F
    hull chords). Returns (tip_vertex_index, axial_edge_index)."""
    vc = fold["vertices_coords"]
    ea = fold["edges_assignment"]
    best = None
    for v, eids in _incidence(fold).items():
        kinds = [ea[e] for e in eids]
        creases = [e for e in eids if ea[e] in ("M", "V")]
        if "B" not in kinds or len(creases) != 1:
            continue
        if any(k not in ("B", "F", "M", "V") for k in kinds):
            continue
        dist = math.hypot(vc[v][0] - tip_xy[0], vc[v][1] - tip_xy[1])
        if best is None or dist < best[0]:
            best = (dist, v, creases[0])
    if best is None:
        raise ShapingError("no flap-tip vertex (B + exactly one crease)")
    return best[1], best[2]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_shaping.py -v`
Expected: 8 PASS (1 + 6 parametrized + 2... i.e. all collected tests pass).

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/shaping.py mcp_harness/tests/test_shaping.py
git commit -m "feat(shaping): op parsing + flap-tip location (B1 groundwork)"
```

---

### Task 2: `reverse_fold` — the wedge construction

**Files:**
- Modify: `mcp_harness/shaping.py` (append)
- Test: `mcp_harness/tests/test_shaping.py` (append)

**Interfaces:**
- Consumes: `_find_tip`, `ShapingError`, `EPS`, `SNAP` from Task 1.
- Produces: `reverse_fold(fold: dict, tip_xy, d: float, theta: float, gamma: float = 45.0) -> dict` — returns a NEW fold dict with 3 new kinds of edits: the axial edge split at `F = P + d*u`; two wedge crease chains from `F` to the paper boundary (splitting every `F` edge crossed and the terminal `B` edge); and a complete `edges_foldAngle` for every edge (`M`→−180, `V`→+180, `B`/`F`→0, shaped edges per the angle model). Raises `ShapingError` on any precondition failure.

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_shaping.py`:

```python
def _edge_lookup(fold, p, q, tol=1e-6):
    """Find the edge whose endpoint coords match {p, q}; return
    (assignment, fold_angle). Robust to index reshuffling."""
    vc = fold["vertices_coords"]
    for i, (a, b) in enumerate(fold["edges_vertices"]):
        ends = {(round(vc[a][0], 6), round(vc[a][1], 6)),
                (round(vc[b][0], 6), round(vc[b][1], 6))}
        want = {(round(p[0], 6), round(p[1], 6)),
                (round(q[0], 6), round(q[1], 6))}
        if ends == want:
            return fold["edges_assignment"][i], fold["edges_foldAngle"][i]
    raise AssertionError(f"no edge {p}-{q}")


def test_reverse_fold_geometry_theta90():
    out = shaping.reverse_fold(TIP_SQUARE, (1, 0.5), d=0.2, theta=90)
    # input not mutated
    assert len(TIP_SQUARE["vertices_coords"]) == 6
    assert "edges_foldAngle" not in TIP_SQUARE
    # +3 vertices: F=(0.8,0.5), hits (1,0.7) and (1,0.3)
    assert len(out["vertices_coords"]) == 9
    # +5 edges: axial split, two B splits, two wedge arms
    assert len(out["edges_vertices"]) == 11
    assert len(out["edges_foldAngle"]) == 11
    # tip-side axial at theta=90: angle 180-2*90 = 0 -> "F"
    assert _edge_lookup(out, (1, 0.5), (0.8, 0.5)) == ("F", 0.0)
    # body-side axial keeps the full V fold
    assert _edge_lookup(out, (0.8, 0.5), (0.5, 0.5)) == ("V", 180.0)
    # wedge arms: s=+1 (axial is V) so +90 -> "V"
    assert _edge_lookup(out, (0.8, 0.5), (1, 0.7)) == ("V", 90.0)
    assert _edge_lookup(out, (0.8, 0.5), (1, 0.3)) == ("V", 90.0)
    # split boundary fragments stay B at angle 0
    assert _edge_lookup(out, (1, 0.5), (1, 0.7)) == ("B", 0.0)
    assert _edge_lookup(out, (1, 0.5), (1, 0.3)) == ("B", 0.0)


def test_reverse_fold_theta180_is_flat_and_maekawa():
    out = shaping.reverse_fold(TIP_SQUARE, (1, 0.5), d=0.2, theta=180)
    # tip axial fully flips V->M; wedge arms fully fold V
    assert _edge_lookup(out, (1, 0.5), (0.8, 0.5)) == ("M", -180.0)
    assert _edge_lookup(out, (0.8, 0.5), (1, 0.7)) == ("V", 180.0)
    # Maekawa at the new degree-4 vertex F: |V - M| == 2
    vc = out["vertices_coords"]
    fi = next(i for i, p in enumerate(vc)
              if abs(p[0] - 0.8) < 1e-9 and abs(p[1] - 0.5) < 1e-9)
    kinds = [a for (u, v), a in
             zip(out["edges_vertices"], out["edges_assignment"])
             if fi in (u, v)]
    assert abs(kinds.count("V") - kinds.count("M")) == 2


def test_reverse_fold_mirrors_sign_for_mountain_axial():
    fold = {**TIP_SQUARE,
            "edges_assignment": ["B", "B", "B", "B", "B", "M"]}
    out = shaping.reverse_fold(fold, (1, 0.5), d=0.2, theta=90)
    assert _edge_lookup(out, (0.8, 0.5), (1, 0.7)) == ("M", -90.0)
    assert _edge_lookup(out, (0.8, 0.5), (0.5, 0.5)) == ("M", -180.0)


def test_refuses_d_past_axial_end():
    with pytest.raises(shaping.ShapingError):
        shaping.reverse_fold(TIP_SQUARE, (1, 0.5), d=0.6, theta=90)


def test_refuses_crease_crossing_the_wedge():
    blocked = {
        "vertices_coords": TIP_SQUARE["vertices_coords"]
                           + [[0.85, 0.35], [0.95, 0.45]],
        "edges_vertices": TIP_SQUARE["edges_vertices"] + [[6, 7]],
        "edges_assignment": TIP_SQUARE["edges_assignment"] + ["M"],
    }
    with pytest.raises(shaping.ShapingError):
        shaping.reverse_fold(blocked, (1, 0.5), d=0.2, theta=90)


def test_refuses_vertex_inside_wedge_region():
    crowded = {
        "vertices_coords": TIP_SQUARE["vertices_coords"] + [[0.9, 0.5]],
        "edges_vertices": TIP_SQUARE["edges_vertices"],
        "edges_assignment": TIP_SQUARE["edges_assignment"],
    }
    with pytest.raises(shaping.ShapingError):
        shaping.reverse_fold(crowded, (1, 0.5), d=0.2, theta=90)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_shaping.py -v`
Expected: new tests FAIL with `AttributeError: module 'shaping' has no attribute 'reverse_fold'`; Task-1 tests still PASS.

- [ ] **Step 3: Write the implementation**

Append to `mcp_harness/shaping.py`:

```python
def _key(p):
    return (round(p[0], 9), round(p[1], 9))


def _rot(v, deg):
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return (c * v[0] - s * v[1], s * v[0] + c * v[1])


def _ray_hit(origin, direction, a, b):
    """Ray origin + t*direction vs segment ab. Returns (t, point) with
    t > EPS and the hit within the segment, else None."""
    ox, oy = origin
    dx, dy = direction
    ex, ey = b[0] - a[0], b[1] - a[1]
    den = dx * ey - dy * ex
    if abs(den) < EPS:
        return None
    t = ((a[0] - ox) * ey - (a[1] - oy) * ex) / den
    u = ((a[0] - ox) * dy - (a[1] - oy) * dx) / den
    if t <= EPS or u < -EPS or u > 1 + EPS:
        return None
    return t, (ox + t * dx, oy + t * dy)


def _point_in_poly(pt, poly):
    """Strict-interior ray-cast test (callers keep boundary points out:
    hit points are SNAP-guarded away from existing vertices)."""
    x, y = pt
    inside = False
    for i in range(len(poly)):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % len(poly)]
        if (y1 > y) != (y2 > y):
            xin = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if xin > x + EPS:
                inside = not inside
    return inside


def _march_arm(fold, start, direction, skip_edges):
    """From `start` along `direction`: collect F-edge crossings (in ray
    order) until the first B edge. Returns (crossings, terminal) where
    crossings = [(edge_index, point), ...] and terminal = (edge_index,
    point). Raises ShapingError if an M/V crease is hit first, a hit
    grazes an existing vertex, or the ray never reaches the boundary."""
    vc = fold["vertices_coords"]
    ea = fold["edges_assignment"]
    hits = []
    for ei, (a, b) in enumerate(fold["edges_vertices"]):
        if ei in skip_edges:
            continue
        h = _ray_hit(start, direction, vc[a], vc[b])
        if h is None:
            continue
        t, pt = h
        for q in (vc[a], vc[b]):
            if math.hypot(pt[0] - q[0], pt[1] - q[1]) < SNAP:
                raise ShapingError("wedge arm grazes an existing vertex")
        hits.append((t, ei, pt))
    hits.sort()
    crossings = []
    for _t, ei, pt in hits:
        kind = ea[ei]
        if kind == "B":
            return crossings, (ei, pt)
        if kind == "F":
            crossings.append((ei, pt))
            continue
        raise ShapingError("wedge arm crosses a real crease")
    raise ShapingError("wedge arm never reaches the paper boundary")


def _split_edges(vc, ev, ea, requests):
    """requests: {edge_index: [pt, ...]}. Split each edge at its points
    (any count/order; every fragment keeps the edge's assignment).
    Returns {_key(pt): new_vertex_index}."""
    new_by_pt = {}
    for ei, pts in requests.items():
        a0 = ev[ei][0]
        ax, ay = vc[a0]
        prev, seg = a0, ei
        for p in sorted(pts, key=lambda p: (p[0] - ax) ** 2 + (p[1] - ay) ** 2):
            vc.append([p[0], p[1]])
            nv = len(vc) - 1
            new_by_pt[_key(p)] = nv
            end = ev[seg][1]
            ev[seg] = [prev, nv]
            ev.append([nv, end])
            ea.append(ea[ei])
            prev, seg = nv, len(ev) - 1
    return new_by_pt


def reverse_fold(fold: dict, tip_xy, d: float, theta: float,
                 gamma: float = 45.0) -> dict:
    """Tip-local inside reverse fold (see module docstring for the angle
    model). Returns a NEW fold dict; raises ShapingError when refused."""
    tip, axial = _find_tip(fold, tip_xy)
    vc0 = fold["vertices_coords"]
    ev0 = fold["edges_vertices"]
    ea0 = fold["edges_assignment"]

    a, b = ev0[axial]
    other = b if a == tip else a
    P = (vc0[tip][0], vc0[tip][1])
    A = (vc0[other][0], vc0[other][1])
    ax_len = math.hypot(A[0] - P[0], A[1] - P[1])
    if d >= ax_len - EPS:
        raise ShapingError("d reaches past the axial crease")
    u = ((A[0] - P[0]) / ax_len, (A[1] - P[1]) / ax_len)   # inward
    F = (P[0] + d * u[0], P[1] + d * u[1])
    tipward = (-u[0], -u[1])

    s = 1.0 if ea0[axial] == "V" else -1.0
    wedge_angle = s * theta
    tip_angle = s * (180.0 - 2.0 * theta)

    def assign(angle):
        if angle > EPS:
            return "V"
        if angle < -EPS:
            return "M"
        return "F"

    # March both arms BEFORE mutating anything (all-or-nothing).
    arms = [_march_arm(fold, F, _rot(tipward, sg * gamma), {axial})
            for sg in (+1.0, -1.0)]

    # Region guard: no pre-existing vertex strictly inside the wedge.
    (_, (_, hit_l)), (_, (_, hit_r)) = arms
    poly = [hit_l, P, hit_r, F]
    for vi, p in enumerate(vc0):
        if vi != tip and _point_in_poly((p[0], p[1]), poly):
            raise ShapingError("existing structure inside the wedge region")

    # --- build the output (copy, then mutate the copy) ---
    vc = [list(p[:2]) for p in vc0]
    ev = [list(e) for e in ev0]
    ea = list(ea0)

    requests = {axial: [F]}
    for crossings, terminal in arms:
        for ei, pt in crossings:
            requests.setdefault(ei, []).append(pt)
        requests.setdefault(terminal[0], []).append(terminal[1])
    new_by_pt = _split_edges(vc, ev, ea, requests)
    nF = new_by_pt[_key(F)]

    overrides = {}
    tip_seg = next(i for i, (x, y) in enumerate(ev) if {x, y} == {tip, nF})
    body_seg = next(i for i, (x, y) in enumerate(ev) if {x, y} == {other, nF})
    ea[tip_seg] = assign(tip_angle)
    overrides[tip_seg] = tip_angle
    overrides[body_seg] = s * 180.0

    for crossings, terminal in arms:
        chain = ([nF] + [new_by_pt[_key(pt)] for _ei, pt in crossings]
                 + [new_by_pt[_key(terminal[1])]])
        for x, y in zip(chain, chain[1:]):
            ev.append([x, y])
            ea.append(assign(wedge_angle))
            overrides[len(ev) - 1] = wedge_angle

    out = {k: v for k, v in fold.items()}
    out["vertices_coords"] = vc
    out["edges_vertices"] = ev
    out["edges_assignment"] = ea
    out["edges_foldAngle"] = [
        overrides.get(i, {"M": -180.0, "V": 180.0}.get(k, 0.0))
        for i, k in enumerate(ea)
    ]
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_shaping.py -v`
Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/shaping.py mcp_harness/tests/test_shaping.py
git commit -m "feat(shaping): tip-local reverse-fold construction with 3D fold angles (B1)"
```

---

### Task 3: F-chord crossing + the defensive display hook

**Files:**
- Modify: `mcp_harness/shaping.py` (append one function)
- Test: `mcp_harness/tests/test_shaping.py` (append)

**Interfaces:**
- Consumes: `parse_op`, `reverse_fold` (Tasks 1–2). The F-crossing behavior already exists in `_march_arm`/`_split_edges`; this task pins it with tests.
- Produces: `apply_display_op(fold: dict, op: str | None) -> dict` — never raises; `None`/empty op or ANY failure returns the input object unchanged (identity, so the inactive server path is byte-identical). This is the only function `web/server.py` calls.

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_shaping.py`:

```python
# Same tip, plus an F hull-chord (x=0.85 from y=0.3 to y=0.7) between the
# fold point and the boundary — the post-square_complete situation. Both
# wedge arms must split it and continue to the B edge.
TIP_CHORD = {
    "vertices_coords": TIP_SQUARE["vertices_coords"]
                       + [[0.85, 0.3], [0.85, 0.7]],
    "edges_vertices": TIP_SQUARE["edges_vertices"] + [[6, 7]],
    "edges_assignment": TIP_SQUARE["edges_assignment"] + ["F"],
}


def test_wedge_arms_pass_through_flat_chords():
    out = shaping.reverse_fold(TIP_CHORD, (1, 0.5), d=0.2, theta=90)
    # +5 vertices: F, 2 chord crossings, 2 boundary hits
    assert len(out["vertices_coords"]) == 8 + 5
    # +9 edges: axial split +1, chord split x2 +2, B splits +2, wedge 2x2
    assert len(out["edges_vertices"]) == 7 + 9
    # wedge chain segments on both sides of the chord carry the angle
    assert _edge_lookup(out, (0.8, 0.5), (0.85, 0.55)) == ("V", 90.0)
    assert _edge_lookup(out, (0.85, 0.55), (1, 0.7)) == ("V", 90.0)
    assert _edge_lookup(out, (0.8, 0.5), (0.85, 0.45)) == ("V", 90.0)
    assert _edge_lookup(out, (0.85, 0.45), (1, 0.3)) == ("V", 90.0)
    # chord fragments stay F / 0
    assert _edge_lookup(out, (0.85, 0.45), (0.85, 0.55)) == ("F", 0.0)


def test_apply_display_op_identity_when_unset():
    assert shaping.apply_display_op(TIP_SQUARE, None) is TIP_SQUARE
    assert shaping.apply_display_op(TIP_SQUARE, "") is TIP_SQUARE


def test_apply_display_op_applies():
    out = shaping.apply_display_op(TIP_SQUARE, "reverse:1,0.5:0.2:90")
    assert len(out["edges_vertices"]) == 11
    assert "edges_foldAngle" in out


def test_apply_display_op_never_raises():
    assert shaping.apply_display_op(TIP_SQUARE, "garbage") is TIP_SQUARE
    # valid syntax, impossible geometry (d too long) -> input unchanged
    assert shaping.apply_display_op(
        TIP_SQUARE, "reverse:1,0.5:0.9:90") is TIP_SQUARE
    # not even a fold dict -> input unchanged
    assert shaping.apply_display_op({"nope": 1},
                                    "reverse:1,0.5:0.2:90") == {"nope": 1}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_shaping.py -v`
Expected: `test_apply_display_op_*` FAIL (no attribute); `test_wedge_arms_pass_through_flat_chords` may already PASS (the machinery is in Task 2 — that is fine, it pins the behavior).

- [ ] **Step 3: Write the implementation**

Append to `mcp_harness/shaping.py`:

```python
def apply_display_op(fold: dict, op: str | None) -> dict:
    """Display-boundary hook (web/server.py). op unset/empty -> input
    unchanged; ANY parse/precondition/geometry failure -> input unchanged.
    Never raises — never break the fold stream."""
    if not op:
        return fold
    try:
        tip_xy, d, theta = parse_op(op)
        return reverse_fold(fold, tip_xy, d, theta)
    except Exception:
        return fold
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_shaping.py -v`
Expected: ALL PASS.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/shaping.py mcp_harness/tests/test_shaping.py
git commit -m "feat(shaping): F-chord traversal pin + defensive apply_display_op (B3)"
```

---

### Task 4: Real-model fixture — shaped squared dog

**Files:**
- Test: `mcp_harness/tests/test_shaping_dog.py`
- Reads: `docs/dog.fold` (committed base), `mcp_harness/square_complete.py`

**Interfaces:**
- Consumes: `square_complete.complete_square(fold, 1.0, 1.0)`, `shaping.apply_display_op`.
- Produces: a pinned demo op string (drift tripwire) recorded as `DEMO_OP` in the test file — Task 7 uses the same string for `IDE_SHAPE_OP`.

- [ ] **Step 1: Probe the squared dog for a workable tip**

The dog's tips (probed 2026-07-01): `(1.0, 0.619)`, `(0.468, 0.0)`, `(0.619, 1.0)`, `(0.0, 0.468)` and others; post-squaring their hull chords become `F`, which `_find_tip` and `_march_arm` accept. Find which ops actually apply:

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python - <<'EOF'
import json, shaping, square_complete
fold = json.load(open("../docs/dog.fold"))
sq = square_complete.complete_square(fold, 1.0, 1.0)
for op in ["reverse:1.0,0.62:0.10:90", "reverse:0.62,1.0:0.10:90",
           "reverse:0.47,0.0:0.08:90", "reverse:0.0,0.47:0.08:90",
           "reverse:1.0,0.62:0.15:90", "reverse:0.62,1.0:0.15:90"]:
    out = shaping.apply_display_op(sq, op)
    print(op, "APPLIED" if out is not sq else "refused")
EOF
```

Expected: at least one line prints `APPLIED`. If all refuse, call `shaping.reverse_fold` directly on the failing op to read the `ShapingError` message and adjust `d` (shorter) or the tip coordinate — the axial creases here are short (~0.26). Record the first APPLIED op string; the steps below assume `reverse:1.0,0.62:0.10:90` — substitute yours everywhere if different.

- [ ] **Step 2: Write the fixture test**

Create `mcp_harness/tests/test_shaping_dog.py`:

```python
"""Drift tripwire: the shaping tracer applies to the real squared dog.

DEMO_OP is the acceptance demo op (IDE_SHAPE_OP in Task 7 of the plan).
If this test starts refusing after an engine/squaring change, the Model
tab demo silently degrades to the unshaped base — this test makes that
loud instead."""
import json
import os

import pytest
import shaping
import square_complete

DEMO_OP = "reverse:1.0,0.62:0.10:90"
DOG = os.path.join(os.path.dirname(__file__), "..", "..", "docs", "dog.fold")


@pytest.fixture(scope="module")
def squared():
    with open(DOG) as fh:
        return square_complete.complete_square(json.load(fh), 1.0, 1.0)


def test_demo_op_applies_to_squared_dog(squared):
    out = shaping.apply_display_op(squared, DEMO_OP)
    assert out is not squared, "demo op was refused"
    assert len(out["edges_vertices"]) > len(squared["edges_vertices"])
    assert len(out["edges_foldAngle"]) == len(out["edges_vertices"])
    # at least one genuinely 3D (non-flat, non-zero) target angle
    assert any(0 < abs(a) < 180 for a in out["edges_foldAngle"])


def test_demo_op_refused_on_raw_hull_is_harmless(squared):
    # Sanity for the failure contract on an arbitrary bad op.
    assert shaping.apply_display_op(squared, "reverse:0.5,0.5:0.9:90") \
        is squared
```

- [ ] **Step 3: Run the test**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_shaping_dog.py -v`
Expected: 2 PASS. If `test_demo_op_applies_to_squared_dog` fails, go back to Step 1 and pick an op that printed APPLIED.

- [ ] **Step 4: Commit**

```bash
git add mcp_harness/tests/test_shaping_dog.py
git commit -m "test(shaping): pin demo op against the real squared dog (drift tripwire)"
```

---

### Task 5: Server wiring at the display boundary

**Files:**
- Modify: `web/server.py` (import block ~line 28; the fold frame in `_send_frames`, ~line 104–110)

**Interfaces:**
- Consumes: `shaping.apply_display_op(fold, op)` (Task 3) — already defensive, so no try/except needed at the call site.
- Produces: `display_json` = squared-then-shaped fold when `IDE_SHAPE_OP` is set; byte-identical behavior when unset (`apply_display_op` returns its input object).

- [ ] **Step 1: Add the import**

In `web/server.py`, next to `import square_complete`:

```python
import shaping               # noqa: E402
import square_complete       # noqa: E402
```

- [ ] **Step 2: Apply the op to the display copy**

In `_send_frames`, replace the fold frame send:

```python
        fold = extract_fold(output)
        if fold is not None:
            # json = the raw hull the agent actually linted (Download + JSON
            # tab); display_json = the squared (and, when IDE_SHAPE_OP is
            # set, shaped) copy for the 3D viewers only. Shaping mirrors
            # squaring's provenance contract: a display-boundary transform,
            # defensive, never on the linted artifact. See
            # docs/superpowers/specs/2026-07-01-shaping-tracer-b1-b3-b4-design.md
            await ws.send_json({"type": "fold", "filename": "model.fold",
                                "json": fold,
                                "display_json": shaping.apply_display_op(
                                    _square_for_display(fold),
                                    os.environ.get("IDE_SHAPE_OP"))})
```

- [ ] **Step 3: Run the full backend suite (regression gate)**

Run: `cd <repo> && make test`
Expected: all tests pass (existing suite + the new shaping tests).

- [ ] **Step 4: Commit**

```bash
git add web/server.py
git commit -m "feat(shaping): apply IDE_SHAPE_OP at the display boundary (B3 wiring)"
```

---

### Task 6: Strain oracle — flat positions from the bridge, check in extraction

**Files:**
- Modify: `web/frontend/public/simulator/js/ide-bridge.js` (the `getFoldedGeometry` handler)
- Modify: `web/frontend/src/extraction.ts`
- Test: `web/frontend/src/extraction.test.ts` (append)

**Interfaces:**
- Consumes: `globals.model.getNodes()` — vendored `model.js` exposes it; `nodes[i].getOriginalPosition()` returns a THREE.Vector3 of the FLAT position, and nodes are 1:1 with the geometry's position triplets (`model.js:364` syncs them index-for-index).
- Produces: `foldedGeometry` messages gain optional `flat_coords: number[][] | null`; `extraction.ts` exports `MAX_STRAIN = 0.05` and `maxEdgeStrain(folded: number[][], flat: number[][], faces: number[][]): number`; the controller rejects captures whose strain exceeds `MAX_STRAIN`. Missing/mismatched `flat_coords` skips the check (defensive — old bridge, buffer mismatch).

- [ ] **Step 1: Write the failing tests**

Append to `web/frontend/src/extraction.test.ts` (add `maxEdgeStrain`, `MAX_STRAIN` to the import from `./extraction`):

```ts
import { maxEdgeStrain, MAX_STRAIN } from "./extraction";

describe("maxEdgeStrain", () => {
  const flat = [[0, 0, 0], [1, 0, 0], [0, 1, 0]];
  const faces = [[0, 1, 2]];

  it("is 0 for an unstretched mesh", () => {
    expect(maxEdgeStrain(flat, flat, faces)).toBe(0);
  });

  it("reports the worst stretched edge", () => {
    const folded = [[0, 0, 0], [1.2, 0, 0], [0, 1, 0]];
    expect(maxEdgeStrain(folded, flat, faces)).toBeCloseTo(0.2, 5);
  });

  it("ignores degenerate zero-length flat edges", () => {
    const degFlat = [[0, 0, 0], [0, 0, 0], [0, 1, 0]];
    const folded = [[0, 0, 0], [5, 0, 0], [0, 1, 0]];
    expect(Number.isFinite(maxEdgeStrain(folded, degFlat, faces))).toBe(true);
  });
});

describe("strain gate in the controller", () => {
  it("rejects a capture whose strain exceeds MAX_STRAIN", async () => {
    const { c, runSettle } = make();
    const p = c.start({});
    c.receive({ type: "ready" });
    runSettle();
    c.receive({
      type: "foldedGeometry",
      vertices_coords: [[0, 0, 0], [2, 0, 0], [0, 1, 0]],
      faces_vertices: [[0, 1, 2]],
      flat_coords: [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
    });
    await expect(p).rejects.toThrow(/strain/);
  });

  it("accepts a capture within MAX_STRAIN", async () => {
    const { c, runSettle } = make();
    const p = c.start({});
    c.receive({ type: "ready" });
    runSettle();
    c.receive({
      type: "foldedGeometry",
      vertices_coords: [[0, 0, 0], [1.01, 0, 0], [0, 1, 0]],
      faces_vertices: [[0, 1, 2]],
      flat_coords: [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
    });
    await expect(p).resolves.toBeTruthy();
  });

  it("skips the strain check when flat_coords is absent (old bridge)", async () => {
    const { c, runSettle } = make();
    const p = c.start({});
    c.receive({ type: "ready" });
    runSettle();
    c.receive({
      type: "foldedGeometry",
      vertices_coords: [[0, 0, 0], [9, 0, 0], [0, 1, 0]],
      faces_vertices: [[0, 1, 2]],
    });
    await expect(p).resolves.toBeTruthy();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd web/frontend && npm test`
Expected: FAIL — `maxEdgeStrain` is not exported; the strain-reject test fails (resolves instead of rejects).

- [ ] **Step 3: Implement in `extraction.ts`**

Update the inbound type and add the check:

```ts
export type ExtractInbound =
  | { type: "ready" }
  | { type: "foldedGeometry"; vertices_coords: number[][];
      faces_vertices: number[][]; flat_coords?: number[][] | null }
  | { type: "error"; message: string };

// Paper-conservation oracle (B4): shaping leaves the flat-foldable regime,
// so Maekawa/Kawasaki no longer apply; "valid" = the solver reached the
// pose without stretching/tearing the sheet. 5% absorbs normal mass-spring
// compliance at a 90% fold; real tears/explosions read far higher.
export const MAX_STRAIN = 0.05;

function edgeLen(a: number[], b: number[]): number {
  return Math.hypot(a[0] - b[0], a[1] - b[1], (a[2] ?? 0) - (b[2] ?? 0));
}

export function maxEdgeStrain(
  folded: number[][], flat: number[][], faces: number[][],
): number {
  let max = 0;
  for (const f of faces) {
    for (let i = 0; i < f.length; i++) {
      const a = f[i], b = f[(i + 1) % f.length];
      const l0 = edgeLen(flat[a], flat[b]);
      if (l0 < 1e-12) continue; // degenerate flat edge: no defined strain
      const strain = Math.abs(edgeLen(folded[a], folded[b]) - l0) / l0;
      if (strain > max) max = strain;
    }
  }
  return max;
}
```

In `receive`, inside the `foldedGeometry` branch after the `allFinite` check:

```ts
        if (msg.flat_coords &&
            msg.flat_coords.length === msg.vertices_coords.length) {
          const strain = maxEdgeStrain(
            msg.vertices_coords, msg.flat_coords, msg.faces_vertices);
          if (strain > MAX_STRAIN) {
            rejectMesh?.(new Error(
              `paper strain ${(strain * 100).toFixed(1)}% exceeds ` +
              `${MAX_STRAIN * 100}% — pose not physically realizable`));
            return;
          }
        }
```

- [ ] **Step 4: Emit flat positions from the bridge**

In `ide-bridge.js`, inside the `getFoldedGeometry` handler, after `faces` is built and before `emit`:

```js
        // Flat (unfolded) positions for the strain oracle: nodes are 1:1
        // with the geometry position triplets (model.js sync). If the
        // counts ever disagree, send null and the check is skipped.
        var nodes = window.globals.model.getNodes();
        var flat = null;
        if (nodes && nodes.length === verts.length) {
          flat = [];
          for (var m = 0; m < nodes.length; m++) {
            var opos = nodes[m].getOriginalPosition();
            flat.push([opos.x, opos.y, opos.z]);
          }
        }
        emit({ type: "foldedGeometry", vertices_coords: verts,
               faces_vertices: faces, flat_coords: flat });
```

(Replace the existing `emit({ type: "foldedGeometry", ... })` line.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd web/frontend && npm test`
Expected: ALL PASS (new + existing extraction/viewer/shell tests).

- [ ] **Step 6: Commit**

```bash
git add web/frontend/src/extraction.ts web/frontend/src/extraction.test.ts \
        web/frontend/public/simulator/js/ide-bridge.js
git commit -m "feat(shaping): paper-strain validity oracle on captured geometry (B4)"
```

---

### Task 7: Acceptance — the posed dog in the Model tab

**Files:** none (verification only; adjust `MAX_STRAIN` or `DEMO_OP` if calibration demands, then re-run Tasks 4/6 test steps and commit).

- [ ] **Step 1: Build the frontend**

```bash
cd web/frontend && npm run build
```

Expected: vite build succeeds into `web/frontend/dist`.

- [ ] **Step 2: Baseline run (no shaping) — strain oracle must not redden A1–A3**

```bash
cd <repo>
mcp_harness/.venv/bin/python -m uvicorn web.server:app --port 8000
```

Open `http://localhost:8000`, prompt `design a dog`, open the **Model** tab.
Expected: the thick-paper base renders as before — no `paper strain … exceeds` error. If the unshaped base trips the oracle, raise `MAX_STRAIN` just above the observed value (the error message prints it), re-run `npm test` + rebuild, and note the calibrated value in the commit.

- [ ] **Step 3: Shaped run**

Restart the server with the pinned demo op (the `DEMO_OP` from Task 4):

```bash
IDE_SHAPE_OP="reverse:1.0,0.62:0.10:90" \
  mcp_harness/.venv/bin/python -m uvicorn web.server:app --port 8000
```

Prompt `design a dog`, open the **Model** tab.
Expected: the captured model shows the chosen flap bent ~90° out of the flat base plane (orbit to confirm it is genuinely 3D, not flat), no strain rejection. The **JSON** tab and **Download** still show the raw hull (no `edges_foldAngle`) — provenance intact.

- [ ] **Step 4: Full regression gates**

```bash
cd <repo> && make test
cd web/frontend && npm test
```

Expected: everything green.

- [ ] **Step 5: Commit any calibration + record completion**

```bash
git add -A && git commit -m "chore(shaping): acceptance calibration for strain oracle / demo op" \
  || echo "nothing to calibrate — done"
```
