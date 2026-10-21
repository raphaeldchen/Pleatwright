# At-Depth Reverse Fold (Slice 3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A `reverse_deep:X,Y:D:THETA` display op that reverse-folds a flap THROUGH all its layers at a non-tip depth, defined geometrically (no layer-order search), with `layer_order` used only as a forced-only trap lint.

**Architecture:** New numpy module `mcp_harness/shaping_deep.py` analyzes the RAW hull fold (`flat_fold` + `layer_order`), computes the folded fold-line, the through-set (BFS over creases folded tipward of the line), per-layer pullback chords and carried-crease angle updates, and writes the creases into the SQUARED display fold (raw and squared share CP coordinates; edge/vertex indices are stable — `complete_square` only appends and reassigns). `shaping.py` gains dispatch only; `web/server.py` passes `raw=fold` at its one call site.

**Tech Stack:** Python 3 + numpy (mcp_harness/.venv), pytest. Existing modules consumed: `flat_fold.py`, `layer_order.py`, `shaping.py`, `square_complete.py`. Spec: `docs/superpowers/specs/2026-07-05-atdepth-reverse-fold-slice3-design.md`.

## Global Constraints

- Backend suite: `cd mcp_harness && .venv/bin/python -m pytest tests -q` (~8–10 min). At branch time: **350 passed / 3 skipped** — final count must be 350+new, 0 failures.
- All commands below run from `mcp_harness/` with `.venv/bin/python` unless stated otherwise.
- **Measure-then-pin:** never write an expected value into a test without first printing it from a committed probe script AND checking it against hand reasoning. Probe scripts are committed as evidence.
- Provenance contract: the raw linted `json` frame is never touched; `shaping_deep` reads the raw fold, writes only into a copy of the squared fold. Input dicts are never mutated.
- `shaping.py` stays stdlib-only: `shaping_deep` is imported **lazily** inside the dispatch branch.
- `FlatFoldResult` is `@dataclass(frozen=True, eq=False)` — never compare/hash results.
- numpy 2.x: `arr.ptp()` is gone; use `np.ptp(arr, 0)`.
- `ShapingError` (from `shaping.py`) is the only refusal exception; wrap `ValueError` from `flat_fold`/`layer_order` in it.
- Key API facts (verified at plan time):
  - `flat_fold(raw) -> FlatFoldResult` with `.faces` (CCW vertex-index lists), `.transforms` (list of 3×3 numpy, flat→folded), `.folded_vertices` (per-face Nx2 arrays), `.closure.bad_edges`, `.shared_edges` = tuple of `(face_a, face_b, (v_lo, v_hi), assignment)`.
  - `layer_order(res) -> LayerOrder`; `.above(a, b) -> True|False|None`; raises `ValueError` on bad closure / non-convex faces.
  - `shaping` helpers to reuse: `ShapingError`, `EPS=1e-9`, `SNAP=1e-7`, `_find_tip(fold, xy) -> (tip_v, axial_edge)`, `_rot(v, deg)`, `_ray_hit`, `_march_arm(fold, start, dir, skip_edges)`, `_split_edges(vc, ev, ea, requests)`, `_key(p)`.
  - `square_complete.complete_square(fold, w, h)`: appends vertices/edges only (raw indices stable), reassigns hull-chord `B`→`F`, snaps boundary vertices within `1e-6`.

---

### Task 1: Hand fixtures + assignment-hypothesis probe (measure-then-pin evidence)

**Files:**
- Create: `mcp_harness/probe_deep_hand.py`

**Interfaces:**
- Produces: fixture constructors `pent2_fold()` and `acc4_fold()` (copied into the test file by Task 2) and the **pinned per-layer assignment rule** for new fold-line creases, recorded in the probe's printed output and docstring.

Two hand fixtures (raw hull folds — the boundary need not be a square):

- **pent2** — a pointed pentagon folded in half lengthwise (ONE V crease). 2 faces; tip `(5,1)` has the raw tip signature (B + B + exactly one crease). Everything about `reverse_deep` on it is hand-derivable, and the existing tip-local `reverse_fold` ALSO works on it (its wedge arms cross no creases) — giving a differential oracle.
- **acc4** — a pointed 5-gon with 3 lengthwise creases (accordion M/V/M): a 4-layer flap. The tip-local op REFUSES it (arms cross real creases); `reverse_deep` is the only way through — this pins the multi-layer behavior.

The open measurement: the assignment rule for NEW fold-line creases per layer. Hypothesis A (matches the shipped tip-local op, where both arms get the same assignment): **every through-layer's pullback chord gets `assign(s*theta)`** with `s` from the flap's axial crease (V→+1, M→−1). Hypothesis B: assignment alternates with face orientation parity. Hand Maekawa analysis at the new degree-4 vertices favors A (B gives 2M/2V at the chord–crease crossings, violating Maekawa); the probe verifies via `flat_fold` closure on the constructed θ=180 result.

- [ ] **Step 1: Write the probe**

```python
"""Slice-3 probe: hand fixtures + per-layer assignment hypothesis.

pent2: pointed pentagon, one lengthwise V crease -> 2-layer flap, tip (5,1).
acc4:  pointed 5-gon, lengthwise creases y=1 (M), y=2 (V, axial), y=3 (M)
       -> 4-layer flap, tip (5,2).

For each: flat_fold closure must be clean; layer_order must give a FORCED
total stack at a mid-flap folded point (print it). Then construct the
theta=180 reverse_deep RESULT CP for acc4 BY HAND-RULE under hypothesis A
(all new chords assign(s*theta); carried creases' angles scaled by
(180-2*theta)/180, i.e. sign-flipped at 180) and check flat_fold closure
of the constructed CP is clean. Repeat under hypothesis B (alternate
assignment by face parity) and show it is NOT clean. The winner is the
pinned rule.

Run: cd mcp_harness && .venv/bin/python probe_deep_hand.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flat_fold import flat_fold
from layer_order import layer_order, AmbiguousStack


def pent2_fold():
    return {
        "vertices_coords": [[0, 0], [4, 0], [5, 1], [4, 2], [0, 2], [0, 1]],
        "edges_vertices": [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5],
                           [5, 0], [5, 2]],
        "edges_assignment": ["B", "B", "B", "B", "B", "B", "V"],
    }


def acc4_fold():
    return {
        "vertices_coords": [
            [0, 0], [4, 0], [5, 2], [4, 4], [0, 4],    # boundary 0-4
            [0, 1], [4.5, 1],                            # y=1 crease 5,6
            [0, 2],                                      # axial left end 7
            [0, 3], [4.5, 3],                            # y=3 crease 8,9
        ],
        "edges_vertices": [
            [0, 1], [1, 6], [6, 2],          # bottom + lower slant split
            [2, 9], [9, 3],                  # upper slant split
            [3, 4],
            [4, 8], [8, 7], [7, 5], [5, 0],  # left edge split
            [5, 6],                          # y=1
            [7, 2],                          # y=2 axial (to tip v2)
            [8, 9],                          # y=3
        ],
        "edges_assignment": ["B", "B", "B", "B", "B", "B",
                             "B", "B", "B", "B",
                             "M", "V", "M"],
    }


def report(name, fold, probe_pt):
    res = flat_fold(fold)
    print(f"\n== {name}: {len(res.faces)} faces, "
          f"max closure {res.closure.max_error:.2e}, "
          f"bad edges {len(res.closure.bad_edges)}")
    print("   faces:", res.faces)
    print("   dets :", [round(float(np.linalg.det(np.asarray(T)[:2, :2])), 3)
                        for T in res.transforms])
    layers = layer_order(res)
    try:
        print(f"   stack_at{probe_pt}:", layers.stack_at(np.asarray(probe_pt)))
    except AmbiguousStack as exc:
        print(f"   stack_at{probe_pt}: AMBIGUOUS {len(exc.free_pairs)}")
    return res


if __name__ == "__main__":
    report("pent2", pent2_fold(), (2.0, 0.5))
    report("acc4", acc4_fold(), (2.0, 1.5))
    # Hypothesis check: build the theta=180 reverse_deep(acc4, tip=(5,2),
    # d=1.2) OUTPUT CP by hand-rule and closure-check it. F=(3.8,2);
    # the folded fold-line pulls back into each of the 4 layers as a
    # 45-degree chord; carried creases (axial tip-side, and the tip-side
    # fragments of y=1/y=3 past their chord crossings) flip M<->V.
    # Fill in the two constructed CPs here after printing the folded
    # geometry above (the chord endpoints come from intersecting the
    # pulled-back line with each face polygon — do the algebra on paper,
    # they are exact rationals for these coordinates), then:
    #   print("hypothesis A closure:", flat_fold(cp_A).closure.max_error)
    #   print("hypothesis B closure:", flat_fold(cp_B).closure.max_error)
```

The commented block is the working part of the task: derive the chord endpoints on paper (exact fractions — all creases are at 45° through rational points), build `cp_A`/`cp_B` dicts inline, and print both closure numbers. **Record the winning rule in the probe docstring** (expected: A clean at ~1e-16, B dirty).

- [ ] **Step 2: Run it, sanity-check by hand**

Run: `.venv/bin/python probe_deep_hand.py`
Expected: pent2 = 2 faces, closure 0, forced 2-stack; acc4 = 4 faces, clean closure, forced 4-stack at `(2.0, 1.5)`. If acc4 closure is NOT clean, the M/V/M accordion assignment is wrong — flip assignments until clean (it is a plain accordion; V/M/V also folds flat, pick whichever is clean and update `acc4_fold()`), and re-derive by hand which is consistent before proceeding. Hypothesis A closure clean; B not.

- [ ] **Step 3: Commit**

```bash
git add probe_deep_hand.py
git commit -m "probe(slice3): hand fixtures pent2/acc4 + per-layer assignment rule pinned"
```

---

### Task 2: `shaping_deep.py` — fold-line geometry + through-set

**Files:**
- Create: `mcp_harness/shaping_deep.py`
- Create: `mcp_harness/tests/test_shaping_deep.py`

**Interfaces:**
- Consumes: `pent2_fold()` / `acc4_fold()` from Task 1 (copy the constructors into the test file — tests never import probe scripts).
- Produces (used by Tasks 3–5):
  - `_analyze(raw: dict) -> tuple[FlatFoldResult, LayerOrder]` — wraps `ValueError` in `ShapingError`.
  - `_fold_geometry(raw, res, tip_xy, d, gamma) -> FoldLine` where `FoldLine` is a small dataclass: `tip: int`, `axial: int`, `s: float`, `F: np.ndarray` (CP apex), `Ff: np.ndarray` (folded apex), `u: np.ndarray` (unit direction of the folded fold-LINE), `n: np.ndarray` (unit normal, positive = carried/tipward side), `tip_faces: tuple[int, int]`.
  - `_through_set(res, fl: FoldLine) -> frozenset[int]`.

- [ ] **Step 1: Write failing tests**

In `mcp_harness/tests/test_shaping_deep.py` (follow `test_layer_order.py`'s import pattern for `sys.path`/`GOLDENS`; copy `pent2_fold`/`acc4_fold` in as module-level helpers):

```python
class TestFoldGeometry:
    def test_pent2_geometry(self):
        raw = pent2_fold()
        res, layers = shaping_deep._analyze(raw)
        fl = shaping_deep._fold_geometry(raw, res, (5, 1), 1.5, 45.0)
        assert fl.s == 1.0                       # axial is V
        assert np.allclose(fl.F, [3.5, 1.0])
        assert set(fl.tip_faces) == set(range(2))
        # folded apex lies on the folded axial line; carried side normal
        # points tipward: the folded tip image is strictly positive side
        tip_img = None
        for fi in fl.tip_faces:
            f = res.faces[fi]
            if fl.tip in f:
                tip_img = res.folded_vertices[fi][f.index(fl.tip)]
        assert float((tip_img - fl.Ff) @ fl.n) > 0

    def test_analyze_refuses_bear(self):
        fold = load_golden("bear-base.fold")
        with pytest.raises(ShapingError):
            shaping_deep._analyze(fold)

    def test_d_past_axial_refused(self):
        raw = pent2_fold()
        res, _ = shaping_deep._analyze(raw)
        with pytest.raises(ShapingError):
            shaping_deep._fold_geometry(raw, res, (5, 1), 99.0, 45.0)


class TestThroughSet:
    def test_pent2_grabs_both_layers(self):
        raw = pent2_fold()
        res, _ = shaping_deep._analyze(raw)
        fl = shaping_deep._fold_geometry(raw, res, (5, 1), 1.5, 45.0)
        assert shaping_deep._through_set(res, fl) == frozenset(range(2))

    def test_acc4_grabs_all_four(self):
        raw = acc4_fold()
        res, _ = shaping_deep._analyze(raw)
        fl = shaping_deep._fold_geometry(raw, res, (5, 2), 1.2, 45.0)
        assert shaping_deep._through_set(res, fl) == frozenset(range(4))
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/test_shaping_deep.py -v`
Expected: FAIL — `ModuleNotFoundError: shaping_deep` (or AttributeError).

- [ ] **Step 3: Implement**

`mcp_harness/shaping_deep.py`:

```python
"""At-depth reverse fold (folded-state-first slice 3).

reverse_deep() folds a flap THROUGH all its layers at a non-tip depth.
Defined geometrically: the fold appears in folded space as a single LINE
through the folded apex; every layer connected to the tip through creases
folded tipward of that line (the through-set) gets the line's pullback as
a real crease; layer_order is consulted ONLY as a forced-only trap lint.
Analysis runs on the RAW hull fold; creases are written into the SQUARED
display fold (shared CP coordinates; stable indices). Spec:
docs/superpowers/specs/2026-07-05-atdepth-reverse-fold-slice3-design.md
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from flat_fold import flat_fold
from layer_order import layer_order
from shaping import EPS, SNAP, ShapingError, _find_tip, _rot

@dataclass(frozen=True)
class FoldLine:
    tip: int
    axial: int
    s: float
    F: np.ndarray
    Ff: np.ndarray
    u: np.ndarray
    n: np.ndarray
    tip_faces: tuple

def _analyze(raw):
    try:
        res = flat_fold(raw)
        return res, layer_order(res)
    except ValueError as exc:
        raise ShapingError(f"base fold unusable for at-depth ops: {exc}") from exc

def _fold_geometry(raw, res, tip_xy, d, gamma):
    tip, axial = _find_tip(raw, tip_xy)
    V = np.asarray([p[:2] for p in raw["vertices_coords"]], float)
    a, b = raw["edges_vertices"][axial]
    other = b if a == tip else a
    P, A = V[tip], V[other]
    ax_len = float(np.linalg.norm(A - P))
    if d >= ax_len - EPS:
        raise ShapingError("d reaches past the axial crease")
    inward = (A - P) / ax_len
    F = P + d * inward
    tipward = -inward
    key = tuple(sorted((tip, other)))
    tip_faces = tuple(fi for fi, f in enumerate(res.faces)
                      if key in {tuple(sorted((f[j], f[(j + 1) % len(f)])))
                                 for j in range(len(f))})
    if not tip_faces:
        raise ShapingError("axial crease bounds no face")
    T = np.asarray(res.transforms[tip_faces[0]])
    Ff = T[:2, :2] @ F + T[:2, 2]
    u = T[:2, :2] @ np.asarray(_rot(tipward, gamma))
    u = u / np.linalg.norm(u)
    ft = T[:2, :2] @ tipward
    n = ft - float(ft @ u) * u
    nl = float(np.linalg.norm(n))
    if nl < EPS:
        raise ShapingError("degenerate fold line (gamma parallel to axis)")
    n = n / nl
    s = 1.0 if raw["edges_assignment"][axial] == "V" else -1.0
    return FoldLine(tip, axial, s, F, Ff, u, n, tip_faces)

def _side(fl, q):
    return float((np.asarray(q) - fl.Ff) @ fl.n)

def _through_set(res, fl):
    V = {}
    seen = set(fl.tip_faces)
    queue = list(fl.tip_faces)
    by_face = {}
    for fa, fb, k, _a in res.shared_edges:
        by_face.setdefault(fa, []).append((fb, k))
        by_face.setdefault(fb, []).append((fa, k))
    while queue:
        fi = queue.pop()
        f = res.faces[fi]
        pos = {v: res.folded_vertices[fi][j] for j, v in enumerate(f)}
        for fj, k in by_face.get(fi, ()):
            if fj in seen:
                continue
            if max(_side(fl, pos[k[0]]), _side(fl, pos[k[1]])) > EPS:
                seen.add(fj)
                queue.append(fj)
    return frozenset(seen)
```

(Note: the BFS crosses ANY shared edge — M/V/F — whose folded segment reaches the carried side; F-joined paper tipward of the line is carried too.)

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_shaping_deep.py -v`
Expected: PASS. If `test_acc4_grabs_all_four` fails, print the folded segments and `_side` values per shared edge — the y=1/y=3 creases must reach past the fold line (they extend to x=4.5 > the line's crossing) — and check `acc4_fold()` matches Task 1's committed version.

- [ ] **Step 5: Commit**

```bash
git add shaping_deep.py tests/test_shaping_deep.py
git commit -m "feat(slice3): fold-line geometry + geometric through-set BFS"
```

---

### Task 3: Pullback chords + carried-crease updates

**Files:**
- Modify: `mcp_harness/shaping_deep.py`
- Modify: `mcp_harness/tests/test_shaping_deep.py`

**Interfaces:**
- Produces (consumed by Task 5's assembly):
  - `_pullback_chords(res, fl, through) -> list[Chord]`; `Chord` dataclass: `face: int`, `p1: np.ndarray`, `p2: np.ndarray` (CP coords), `e1: tuple[int, float]`, `e2: tuple[int, float]` (raw-edge index + parameter t of each endpoint along that edge, from the edge's first vertex). Raises `ShapingError` on a vertex graze (endpoint within `SNAP` of an edge endpoint).
  - `_carried_updates(res, raw, fl, through) -> list[Carried]`; `Carried` dataclass: `edge: int` (raw index), `t_cross: float | None` (None = whole edge carried; else split parameter, carried side = the side containing higher `_side`), `carried_from_first: bool` (True if the fragment from the edge's FIRST vertex is the carried one).

Semantics: for each through-face, intersect the infinite folded line `(Ff, u)` with the face's folded polygon → 0 or 2 points (convex); map back through the inverse transform → a CP chord with endpoints on the face's boundary edges. For each M/V crease edge of a through-face: fully on the carried side (`_side ≥ −EPS` at both ends) → whole-edge carried; crossing → split parameter. Angle math happens in Task 5 (single place): new chords get `assign(s*theta)` (Task 1's pinned rule) and carried creases/fragments get `old_angle * (180 − 2*theta) / 180`.

- [ ] **Step 1: Write failing tests** (hand-derived pent2 values; d=1.5, gamma=45 — worked out on paper at plan time)

```python
class TestPullback:
    def test_pent2_chords(self):
        raw = pent2_fold()
        res, _ = shaping_deep._analyze(raw)
        fl = shaping_deep._fold_geometry(raw, res, (5, 1), 1.5, 45.0)
        chords = shaping_deep._pullback_chords(res, fl, frozenset(range(2)))
        assert len(chords) == 2
        pts = sorted((sorted((tuple(np.round(c.p1, 6)),
                              tuple(np.round(c.p2, 6))))) for c in chords)
        # lower face: (3.5,1)->(4.25,0.25) on slant edge (1,2);
        # upper face: (3.5,1)->(4.25,1.75) on slant edge (2,3)
        assert pts == [[(3.5, 1.0), (4.25, 0.25)],
                       [(3.5, 1.0), (4.25, 1.75)]]

    def test_pent2_carried_axial_split(self):
        raw = pent2_fold()
        res, _ = shaping_deep._analyze(raw)
        fl = shaping_deep._fold_geometry(raw, res, (5, 1), 1.5, 45.0)
        car = shaping_deep._carried_updates(res, raw, fl,
                                            frozenset(range(2)))
        assert len(car) == 1 and car[0].edge == 6   # the axial (5,2)
        # axial runs v5=(0,1) -> v2=(5,1); F=(3.5,1) => t = 0.7,
        # carried fragment is the tip side (toward v2, NOT from first)
        assert abs(car[0].t_cross - 0.7) < 1e-9
        assert car[0].carried_from_first is False

    def test_acc4_chord_and_carried_counts(self):
        raw = acc4_fold()
        res, _ = shaping_deep._analyze(raw)
        fl = shaping_deep._fold_geometry(raw, res, (5, 2), 1.2, 45.0)
        chords = shaping_deep._pullback_chords(res, fl, frozenset(range(4)))
        car = shaping_deep._carried_updates(res, raw, fl, frozenset(range(4)))
        assert len(chords) == 4
        # 3 lengthwise creases each interact with the fold line:
        # axial splits at F; y=1 and y=3 split at their chord crossings
        assert sorted(c.edge for c in car) == [10, 11, 12]
        assert all(c.t_cross is not None for c in car)
```

(If Step 2 of Task 1 changed `acc4_fold` assignments, mirror that here. The acc4 expectations are structural — counts and which edges — not coordinates; coordinates get pinned only if the hand algebra was done in Task 1.)

- [ ] **Step 2: Run to verify failure**

Run: `.venv/bin/python -m pytest tests/test_shaping_deep.py -k "Pullback" -v`
Expected: FAIL with AttributeError (`_pullback_chords` missing).

- [ ] **Step 3: Implement**

Add to `shaping_deep.py`:

```python
@dataclass(frozen=True)
class Chord:
    face: int
    p1: np.ndarray
    p2: np.ndarray
    e1: tuple
    e2: tuple

@dataclass(frozen=True)
class Carried:
    edge: int
    t_cross: float | None
    carried_from_first: bool

def _edge_index(raw):
    return {tuple(sorted(e)): i
            for i, e in enumerate(raw["edges_vertices"])}

def _pullback_chords(res, fl, through):
    eidx = None
    out = []
    for fi in sorted(through):
        f = res.faces[fi]
        poly = res.folded_vertices[fi]
        hits = []
        for j in range(len(f)):
            q1, q2 = poly[j], poly[(j + 1) % len(f)]
            d1, d2 = _side(fl, q1), _side(fl, q2)
            if (d1 > EPS) == (d2 > EPS) or abs(d1 - d2) < EPS:
                continue
            t = d1 / (d1 - d2)
            if t < SNAP or t > 1 - SNAP:
                raise ShapingError("fold line grazes an existing vertex")
            key = tuple(sorted((f[j], f[(j + 1) % len(f)])))
            hits.append((key, t if f[j] == key[0] else 1 - t,
                         q1 + t * (q2 - q1)))
        if len(hits) != 2:
            continue                     # face fully on one side: no chord
        T = np.asarray(res.transforms[fi])
        Tinv = np.linalg.inv(T)
        pts = [Tinv[:2, :2] @ h[2] + Tinv[:2, 2] for h in hits]
        out.append(Chord(fi, pts[0], pts[1], (hits[0][0], hits[0][1]),
                         (hits[1][0], hits[1][1])))
    return out

def _carried_updates(res, raw, fl, through):
    eidx = _edge_index(raw)
    V = np.asarray([p[:2] for p in raw["vertices_coords"]], float)
    seen, out = set(), []
    for fa, fb, k, a in res.shared_edges:
        if a not in ("M", "V") or k in seen:
            continue
        if fa not in through and fb not in through:
            continue
        seen.add(k)
        fi = fa if fa in through else fb
        f = res.faces[fi]
        pos = {v: res.folded_vertices[fi][j] for j, v in enumerate(f)}
        d1, d2 = _side(fl, pos[k[0]]), _side(fl, pos[k[1]])
        if d1 <= EPS and d2 <= EPS:
            continue                                   # rootward: untouched
        ei = eidx[k]
        ev = raw["edges_vertices"][ei]
        if d1 >= -EPS and d2 >= -EPS:
            out.append(Carried(ei, None, True))        # whole edge carried
            continue
        t = d1 / (d1 - d2)                             # crossing in k-order
        if ev[0] != k[0]:
            t = 1 - t
        if t < SNAP or t > 1 - SNAP:
            raise ShapingError("fold line grazes an existing vertex")
        first_carried = (_side(fl, pos[ev[0]]) > 0)
        out.append(Carried(ei, float(t), first_carried))
    return out
```

Note the chord endpoint bookkeeping: `e1`/`e2` carry `(edge_key, t)` where t is measured from the RAW edge's first vertex — Task 5 converts keys to indices via `_edge_index`. Two adjacent through-faces hit the same shared edge at the same t (closure-consistent folds guarantee it); Task 5 dedupes by rounded (edge, t).

- [ ] **Step 4: Run tests**

Run: `.venv/bin/python -m pytest tests/test_shaping_deep.py -v`
Expected: PASS. If pent2 chord values are off, print the folded polygons and the raw hit points — the lower face is identity (chord IS the folded segment), so a wrong value means the side/parameter algebra is inverted.

- [ ] **Step 5: Commit**

```bash
git add shaping_deep.py tests/test_shaping_deep.py
git commit -m "feat(slice3): per-layer pullback chords + carried-crease crossings"
```

---

### Task 4: Forced-trap lint

**Files:**
- Modify: `mcp_harness/shaping_deep.py`
- Modify: `mcp_harness/tests/test_shaping_deep.py`

**Interfaces:**
- Produces: `_forced_trap(above, through: list[int], others: list[int]) -> tuple | None` — pure function over the `above(a,b) -> True|False|None` protocol; returns `(x, over, under)` for the first foreign face `x` forced strictly between two through-faces, else `None`. Candidate set (`others`) is computed by the caller (Task 5) as faces not in the through-set with any folded vertex strictly on the carried side.

- [ ] **Step 1: Write failing tests** (unit level — a fake `above` keeps this independent of finding a real trapped fixture; spec allows it, dog is free nearly everywhere)

```python
class TestForcedTrap:
    def test_forced_between_refused(self):
        rel = {(1, 9): True, (9, 2): True}     # 1 above 9 above 2
        above = lambda a, b: rel.get((a, b),
                                     (not rel[(b, a)]) if (b, a) in rel
                                     else None)
        assert shaping_deep._forced_trap(above, [1, 2], [9]) == (9, 1, 2)

    def test_free_pairs_never_refuse(self):
        above = lambda a, b: None
        assert shaping_deep._forced_trap(above, [1, 2], [9]) is None

    def test_fully_above_ok(self):
        rel = {(9, 1): True, (9, 2): True}
        above = lambda a, b: rel.get((a, b),
                                     (not rel[(b, a)]) if (b, a) in rel
                                     else None)
        assert shaping_deep._forced_trap(above, [1, 2], [9]) is None
```

- [ ] **Step 2: Run to verify failure** — `.venv/bin/python -m pytest tests/test_shaping_deep.py -k Trap -v` → AttributeError.

- [ ] **Step 3: Implement**

```python
def _forced_trap(above, through, others):
    for x in others:
        over = [t for t in through if above(t, x) is True]
        under = [t for t in through if above(x, t) is True]
        if over and under:
            return x, over[0], under[0]
    return None
```

- [ ] **Step 4: Run tests** — expected PASS.
- [ ] **Step 5: Commit** — `git add ... && git commit -m "feat(slice3): forced-only trap lint (free pairs never refuse)"`

---

### Task 5: `reverse_deep()` assembly on the squared fold

**Files:**
- Modify: `mcp_harness/shaping_deep.py`
- Modify: `mcp_harness/tests/test_shaping_deep.py`

**Interfaces:**
- Consumes: everything above plus `shaping._split_edges`, `shaping._march_arm`, `square_complete.complete_square`.
- Produces: `reverse_deep(squared_fold: dict, raw_fold: dict, tip_xy, d: float, theta: float, gamma: float = 45.0) -> dict` — a NEW squared-fold dict with the at-depth creases, rebuilt `edges_foldAngle`; raises `ShapingError` on every refusal; never mutates either input.

Assembly algorithm (all in one public function, private helpers above):

1. Validate `d > 0`, `0 < theta <= 180`; `_analyze(raw)`; `_fold_geometry`; `_through_set`.
2. Trap candidates: `[i for i in range(len(res.faces)) if i not in through and any(_side(fl, q) > EPS for q in res.folded_vertices[i])]`; `_forced_trap(layers.above, sorted(through), candidates)` → refuse with the triple in the message.
3. `_pullback_chords` + `_carried_updates` (raw-space, exact).
4. Copy `squared_fold`'s three arrays (same shallow-copy comment/contract as `shaping.reverse_fold` — see `shaping.py:259-262`). **Raw edge index i is the same edge in the squared fold** (`complete_square` appends only) — but verify defensively: check `squared["edges_vertices"][i]` equals the raw pair for every touched edge, else `ShapingError("squared fold does not extend the raw fold")`.
5. Split requests: for every chord endpoint and every `Carried.t_cross`, compute the split POINT from the SQUARED endpoints (`pt = (1-t)*vc[a] + t*vc[b]`, honoring boundary snap), dedupe by `_key(pt)`, feed `shaping._split_edges`.
6. Add chord edges between the two new endpoint vertices per chord; assignment `assign(fl.s * theta)` (Task 1's rule) with `assign` copied from `shaping.reverse_fold`'s local (module-level here); record fold-angle override `fl.s * theta`.
7. Carried angles: for each `Carried`, the carried fragment (whole edge, or the post-split fragment on the carried side, located via `carried_from_first` and `_split_edges`' fragment layout: the original index keeps the FIRST-vertex fragment, the appended one is the far fragment) gets `new_angle = old_angle * (180 - 2*theta)/180` where `old_angle = ±180` by assignment (M→−180, V→+180); update `edges_assignment` via `assign(new_angle)`, record the override.
8. Corner extension: for each chord endpoint whose RAW edge assignment is `"B"` but whose SQUARED assignment is `"F"` (hull chord with corner paper outside): `shaping._march_arm(squared_copy, endpoint, direction_out_of_face, skip={the split fragments of that edge})` collecting F crossings to the true B boundary; split those edges, chain new crease edges with the chord's assignment/angle. Direction = normalized `(endpoint − other_chord_endpoint)`.
9. Rebuild `edges_foldAngle` exactly as `shaping.reverse_fold` does (default −180/180/0, overrides map).

- [ ] **Step 1: Write failing tests**

```python
def _squared(raw, w, h):
    sys.path fixup as at top of file
    import square_complete
    return square_complete.complete_square(raw, w, h)


class TestReverseDeep:
    def test_pent2_matches_tip_local(self):
        # pent2 is a pure 2-layer flap where the tip-local op also works:
        # reverse_deep must produce the identical crease pattern.
        raw = pent2_fold()
        deep = shaping_deep.reverse_deep(raw, raw, (5, 1), 1.5, 180.0)
        local = shaping.reverse_fold(raw, (5, 1), 1.5, 180.0)
        canon = lambda f: sorted(
            (tuple(sorted((_r(f["vertices_coords"][a]),
                           _r(f["vertices_coords"][b])))), asg, round(ang, 6))
            for (a, b), asg, ang in zip(f["edges_vertices"],
                                        f["edges_assignment"],
                                        f["edges_foldAngle"]))
        assert canon(deep) == canon(local)   # _r rounds coords to 9 dp

    def test_acc4_flat_result_is_flat_foldable(self):
        raw = acc4_fold()
        out = shaping_deep.reverse_deep(raw, raw, (5, 2), 1.2, 180.0)
        assert flat_fold(out).closure.max_error < 1e-9

    def test_inputs_never_mutated_and_deterministic(self):
        raw = acc4_fold()
        import copy, json
        snap = copy.deepcopy(raw)
        a = shaping_deep.reverse_deep(raw, raw, (5, 2), 1.2, 120.0)
        b = shaping_deep.reverse_deep(raw, raw, (5, 2), 1.2, 120.0)
        assert raw == snap and json.dumps(a, sort_keys=True) == \
            json.dumps(b, sort_keys=True)

    def test_corner_extension_reaches_square_boundary(self):
        raw = pent2_fold()
        sq = _squared(raw, 5.0, 2.0)
        out = shaping_deep.reverse_deep(sq, raw, (5, 1), 1.5, 180.0)
        # the lower chord ends at (4.25,0.25) on the former-B slant edge
        # (now an F hull chord); it must continue at -45 deg through the
        # corner paper to the true boundary at (4.5, 0).
        coords = {(round(x, 6), round(y, 6))
                  for x, y in out["vertices_coords"]}
        assert (4.5, 0.0) in coords

    def test_theta_120_angles(self):
        raw = pent2_fold()
        out = shaping_deep.reverse_deep(raw, raw, (5, 1), 1.5, 120.0)
        angles = sorted(round(a, 6) for a in out["edges_foldAngle"] if a)
        # carried axial tip-side: 180*(180-240)/180 = -60;
        # body-side axial stays 180; two chords at s*theta = 120
        assert angles == [-60.0, 120.0, 120.0, 180.0]
```

Plus refusal tests: bear (`ShapingError`), `d` past axial, `theta` out of range, and a graze case (pent2 with `d` chosen so a chord endpoint lands within `1e-8` of vertex `(4,0)` — d=1.0 hits it exactly, expect `ShapingError`).

- [ ] **Step 2: Run to verify failure** — `-k ReverseDeep` → AttributeError.
- [ ] **Step 3: Implement `reverse_deep()`** per the assembly algorithm above (≈120 lines; every helper already exists and is tested).
- [ ] **Step 4: Run the whole file** — `.venv/bin/python -m pytest tests/test_shaping_deep.py -v` → all PASS. The differential pent2 test is the acceptance gate: if it fails, diff the two canonical edge sets — endpoint bookkeeping (t direction) is the usual suspect.
- [ ] **Step 5: Commit** — `git commit -m "feat(slice3): reverse_deep assembly — splits, corner extension, fold angles"`

---

### Task 6: Dispatch wiring (`shaping.py`, `web/server.py`)

**Files:**
- Modify: `mcp_harness/shaping.py` (`parse_op`, `apply_display_op`, `apply_display_ops`)
- Modify: `web/server.py:155` (one line)
- Modify: `mcp_harness/tests/test_shaping_deep.py` (dispatch tests)
- Test (existing, must stay green): `mcp_harness/tests/test_shaping.py`, `web/tests/`

**Interfaces:**
- Produces: `apply_display_ops(fold, ops, raw=None)` and `apply_display_op(fold, op, raw=None)`; op string `reverse_deep:X,Y:D:THETA`.

- [ ] **Step 1: Write failing tests**

```python
class TestDispatch:
    def test_reverse_deep_op_applies(self):
        raw = pent2_fold()
        sq = _squared(raw, 5.0, 2.0)
        out = shaping.apply_display_ops(sq, ["reverse_deep:5,1:1.5:180"],
                                        raw=raw)
        assert out is not sq and len(out["edges_vertices"]) > \
            len(sq["edges_vertices"])

    def test_deep_without_raw_refused(self):
        sq = _squared(pent2_fold(), 5.0, 2.0)
        assert shaping.apply_display_ops(
            sq, ["reverse_deep:5,1:1.5:180"]) is sq

    def test_second_deep_refused_first_applies(self):
        raw = pent2_fold()
        sq = _squared(raw, 5.0, 2.0)
        one = shaping.apply_display_ops(sq, ["reverse_deep:5,1:1.5:180"],
                                        raw=raw)
        two = shaping.apply_display_ops(
            sq, ["reverse_deep:5,1:1.5:180", "reverse_deep:5,1:0.8:180"],
            raw=raw)
        assert json.dumps(two, sort_keys=True) == \
            json.dumps(one, sort_keys=True)

    def test_deep_after_tip_local_refused(self):
        raw = pent2_fold()
        sq = _squared(raw, 5.0, 2.0)
        out = shaping.apply_display_ops(
            sq, ["reverse:5,1:0.5:120", "reverse_deep:5,1:1.5:180"],
            raw=raw)
        # tip-local applied, deep refused -> equals tip-local alone
        assert json.dumps(out, sort_keys=True) == json.dumps(
            shaping.apply_display_ops(sq, ["reverse:5,1:0.5:120"]),
            sort_keys=True)
```

- [ ] **Step 2: Run to verify failure** — `parse_op` rejects the op string today → the first test fails with `out is sq`.

- [ ] **Step 3: Implement** in `shaping.py`:

- `parse_op`: accept `"reverse_deep"` in the kind set (the existing 4-part parse covers it; the `outside` theta guard stays `outside`-only).
- `apply_display_op(fold, op, raw=None)`: in the try block, on `kind == "reverse_deep"`: `if raw is None: raise ShapingError("reverse_deep needs the raw base fold")`; lazy `from shaping_deep import reverse_deep`; `return reverse_deep(fold, raw, tip_xy, d, theta)`.
- `apply_display_ops(fold, ops, raw=None)`:

```python
def apply_display_ops(fold, ops, raw=None):
    if not ops:
        return fold
    out, deep_done, tip_done = fold, False, False
    for op in ops:
        is_deep = op.strip().startswith("reverse_deep:")
        if is_deep and (deep_done or tip_done):
            print(f"shaping: op {op!r} refused: at most one reverse_deep,"
                  f" and before tip-local ops", file=sys.stderr)
            continue
        res = apply_display_op(out, op, raw=raw)
        if res is not out:
            deep_done, tip_done = (deep_done or is_deep,
                                   tip_done or not is_deep)
        out = res
    return out
```

- `web/server.py:155-157`: `shaping.apply_display_ops(_square_for_display(fold, width, height), ops, raw=fold)`.

- [ ] **Step 4: Run dispatch tests + neighbors**

Run: `.venv/bin/python -m pytest tests/test_shaping_deep.py tests/test_shaping.py -q` and `cd .. && web/... tests if any reference apply_display_ops` (`grep -rn apply_display_ops web/tests mcp_harness/tests` first; run whatever hits).
Expected: PASS, zero regressions.

- [ ] **Step 5: Commit** — `git commit -m "feat(slice3): reverse_deep display dispatch + server raw= plumbing"`

---

### Task 7: Fixture tier — measure-then-pin on dog/quad/star-4

**Files:**
- Modify: `mcp_harness/probe_atdepth_stack.py` (add through-set + reverse_deep reporting)
- Modify: `mcp_harness/tests/test_shaping_deep.py`

- [ ] **Step 1: Extend the probe** — for each golden and 2–3 chosen tip/depth points (reuse the probe's tips; pick points that did NOT graze in earlier runs), print: through-set, trap-candidate count, trap verdict, and (when the op succeeds on the squared fold) the output's new-edge count and assignment histogram. Run `.venv/bin/python probe_atdepth_stack.py` and eyeball: dog tip `v16` at `f=0.5` must yield a through-set ⊆ its cover `{11,14,19,27}` — sanity-check against the flap structure (11/14 are the deep-forced pair from `f=0.7`); star-4 is expected to grab all 8 coincident faces (honest: the flat state stacks all flaps).
- [ ] **Step 2: Pin** — write `TestFixtureTier` asserting, for the 3 fixtures at the probed points: exact through-sets, `reverse_deep` success (or specific `ShapingError`), pinned new-edge counts + assignment histograms. Values come from Step 1's printout, cross-checked for plausibility (through-set sizes must match the flap layer counts the slice-2 memory records: dog deep flap pair = 2, star-4 = 8).
- [ ] **Step 3: Full suite** — `.venv/bin/python -m pytest tests -q` → **0 failures** (350 + new). Fix anything red before committing.
- [ ] **Step 4: Commit** — `git commit -m "test(slice3): measured fixture pins — through-sets + crease histograms"` (probe + tests together).

---

### Task 8: End-to-end sim smoke (Playwright, evidence-recorded)

**Files:**
- Create: `mcp_harness/probe_deep_sim_smoke.py` (builds the shaped display_json + computes strain from a captured geometry file)

This is executed WITH the Playwright MCP browser tools (the vendored sim's GPU solver runs under Playwright — proven slice 0/1; `ide-bridge.js` guards `e.origin === location.origin`, and same-page `window.postMessage(msg, location.origin)` passes it).

- [ ] **Step 1: Build the shaped fold** — probe script part 1: load `tests/goldens/dog.fold`, `complete_square(fold, 1.0, 1.0)`, `shaping.apply_display_ops(sq, ["reverse_deep:X,Y:D:180"], raw=fold)` using the dog point Task 7 pinned as succeeding; write to `web/frontend/dist/deep_smoke.fold` (served statically; delete after).
- [ ] **Step 2: Drive the sim** — `python3 -m http.server 8123 -d web/frontend/dist` (background); Playwright: navigate to `http://localhost:8123/simulator/index.html?embed=1`; `browser_evaluate`: fetch the fold JSON, `window.postMessage({type:"loadFold", fold}, location.origin)`; then `{type:"setFold", percent:100}`; wait ~20s (visible tab); then request `{type:"getFoldedGeometry"}` capturing the `foldedGeometry` reply; save `vertices_coords`/`faces_vertices`/`flat_coords` to a JSON file under `$CLAUDE_JOB_DIR/tmp/`.
- [ ] **Step 3: Assert strain** — probe script part 2: per-triangle-edge strain `|len3d − lenflat| / lenflat`; print NaN count, max, p90. **Gate: 0 NaN and p90 < 0.15** (the strain oracle's own metric and default `IDE_STRAIN_MAX`); record max for the PR text. If p90 fails, this is a REAL signal about the angle model — stop and investigate (systematic-debugging), do not loosen the gate.
- [ ] **Step 4: Record + commit** — paste the numbers into the SDD ledger and the eventual PR body; `git add probe_deep_sim_smoke.py && git commit -m "probe(slice3): sim smoke — reverse_deep dog strain evidence"`. Remove `deep_smoke.fold` from `dist/`.

---

### Task 9: Final verification & branch finish

- [ ] Full backend suite: `cd mcp_harness && .venv/bin/python -m pytest tests -q` — 0 failures; report exact counts.
- [ ] `git diff origin/main --stat` — only: `mcp_harness/shaping_deep.py`, `mcp_harness/shaping.py`, `mcp_harness/tests/test_shaping_deep.py`, `web/server.py`, the 3 probe scripts, spec + plan docs.
- [ ] Provenance spot-check: `grep -n "raw=fold" web/server.py` shows exactly one site; `json` frame construction untouched.
- [ ] Use superpowers:requesting-code-review for a whole-branch review; fix findings.
- [ ] Use superpowers:finishing-a-development-branch — the user merges the PR themselves.

## Self-Review (done at plan time)

- **Spec coverage:** §1 semantics → Tasks 2–3; §2 refusals → Tasks 4–5 (trap, closure, graze, d, theta) + Task 6 (ordering/one-max); §3 wiring → Tasks 5–6; §4 tiers 1–4 → Tasks 1/5, 7, 5–6, 8; §5 non-goals — no task touches them.
- **Known deviation:** spec §4 says "max strain under IDE_STRAIN_MAX"; the plan gates on **p90** (the shipped strain oracle's metric) and records max — noted in Task 8.
- **Type consistency:** `FoldLine`/`Chord`/`Carried` names and the `reverse_deep(squared, raw, tip_xy, d, theta, gamma)` signature are used identically in Tasks 2–8.
