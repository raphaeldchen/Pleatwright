# Flat-Fold Engine (Slice 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A pure-Python library (`mcp_harness/flat_fold.py`) that computes the analytic flat-folded 2D state of a compiled base — per-face transforms, folded positions, and a cycle-closure report — as the foundation for layer ordering, at-depth ops, and the headless B5 evaluator.

**Architecture:** Face extraction from the bare crease pattern (angle-sorted half-edge walk — TreeMaker FOLDs carry no `faces_vertices`), then reflection composition along a BFS spanning tree of the face-adjacency graph (Lang's construction). Self-consistency is a REPORTED output (`ClosureReport`), not an assertion: hull-frontier bases and squared display folds are valid inputs that legitimately return large closure errors.

**Tech Stack:** Python 3 + numpy (already a project dependency). Tests: pytest, offline only.

**Spec:** `docs/superpowers/specs/2026-07-03-flat-fold-engine-slice1-design.md`
**Probe evidence:** `docs/superpowers/2026-07-03-probe-folded-state-findings.md` (script `mcp_harness/probe_folded_state.py` — reference only; the library is a clean reimplementation, do not import from the probe).

## Global Constraints

- All commands run from `mcp_harness/`; the interpreter is `.venv/bin/python`.
- Test command: `.venv/bin/python -m pytest tests/test_flat_fold.py -q` (fast, offline; no browser, no compile).
- numpy only — no new dependencies.
- Do NOT touch `web/*`, `agent_loop.py`, `server.py`, or the probe script. The engine READS FOLD dicts and never writes one (provenance contract).
- `ValueError` is the only exception that may escape `flat_fold()`, and only for structurally unusable input (missing/empty/mismatched arrays, degenerate zero-length crease, face walk failure, disconnected face graph). Kawasaki-violating and squared folds must return normally.
- Numbers pinned as drift tripwires (bear closure count/max) must be MEASURED from the implementation before being written into the test — the probe's values (15 bad edges, max 1.199) came from a different spanning-tree construction and may legitimately differ. Steps below say exactly when to measure.

---

### Task 1: Face extraction (`_extract_faces`) + input validation

**Files:**
- Create: `mcp_harness/flat_fold.py`
- Create: `mcp_harness/tests/test_flat_fold.py`
- Create (fixture copies): `mcp_harness/tests/goldens/bear-base.fold` (from `web/frontend/public/simulator/assets/ide/bear-base.fold`), `mcp_harness/tests/goldens/dog.fold` (from `docs/dog.fold`)

**Interfaces:**
- Produces: `_validate(fold: dict) -> None` (raises `ValueError`), `_signed_area(P: np.ndarray) -> float`, `_extract_faces(V: np.ndarray, edges: list[tuple[int,int]]) -> list[list[int]]` (interior faces, CCW). Task 2 builds `flat_fold()` on these.

- [ ] **Step 1: Copy the fixtures**

```bash
cp ../web/frontend/public/simulator/assets/ide/bear-base.fold tests/goldens/bear-base.fold
cp ../docs/dog.fold tests/goldens/dog.fold
```

- [ ] **Step 2: Write the failing tests**

Create `mcp_harness/tests/test_flat_fold.py`:

```python
"""Tests for flat_fold.py (folded-state-first slice 1).

Spec: docs/superpowers/specs/2026-07-03-flat-fold-engine-slice1-design.md
Fixture provenance: star-4/hshape/quad are compile goldens; dog.fold is
the 2026-06 six-leaf dog compile; bear-base.fold is the hull-frontier
display asset (accepted Kawasaki violations); star4-sim-100.json is the
2026-07-03 probe's converged 100% browser capture of star-4.
"""
import json
import os

import numpy as np
import pytest

from flat_fold import _extract_faces, _signed_area, _validate

GOLDENS = os.path.join(os.path.dirname(__file__), "goldens")


def load_golden(name):
    with open(os.path.join(GOLDENS, name)) as fh:
        return json.load(fh)


def cp_vertices(fold):
    return np.asarray([v[:2] for v in fold["vertices_coords"]], dtype=float)


class TestExtractFaces:
    def test_star4_faces(self):
        fold = load_golden("star-4.fold")
        faces = _extract_faces(cp_vertices(fold),
                               [tuple(e) for e in fold["edges_vertices"]])
        assert len(faces) == 8
        assert all(len(f) == 3 for f in faces)

    def test_faces_are_ccw(self):
        fold = load_golden("star-4.fold")
        V = cp_vertices(fold)
        faces = _extract_faces(V, [tuple(e) for e in fold["edges_vertices"]])
        assert all(_signed_area(V[f]) > 0 for f in faces)

    def test_bear_faces_including_nonconvex_frame(self):
        # 45 interior faces; the hull-frontier frame region is a 12-gon.
        fold = load_golden("bear-base.fold")
        faces = _extract_faces(cp_vertices(fold),
                               [tuple(e) for e in fold["edges_vertices"]])
        assert len(faces) == 45
        assert max(len(f) for f in faces) == 12

    def test_every_edge_bounds_at_most_two_faces(self):
        fold = load_golden("dog.fold")
        V = cp_vertices(fold)
        faces = _extract_faces(V, [tuple(e) for e in fold["edges_vertices"]])
        assert len(faces) == 28
        count = {}
        for f in faces:
            for j in range(len(f)):
                k = tuple(sorted((f[j], f[(j + 1) % len(f)])))
                count[k] = count.get(k, 0) + 1
        assert max(count.values()) <= 2


class TestValidate:
    def test_missing_keys_raise(self):
        with pytest.raises(ValueError, match="vertices_coords"):
            _validate({"edges_vertices": [[0, 1]], "edges_assignment": ["B"]})
        with pytest.raises(ValueError, match="edges_vertices"):
            _validate({"vertices_coords": [[0, 0]], "edges_assignment": ["B"]})

    def test_empty_arrays_raise(self):
        with pytest.raises(ValueError):
            _validate({"vertices_coords": [], "edges_vertices": [],
                       "edges_assignment": []})

    def test_mismatched_lengths_raise(self):
        with pytest.raises(ValueError, match="length"):
            _validate({"vertices_coords": [[0, 0], [1, 0]],
                       "edges_vertices": [[0, 1]],
                       "edges_assignment": []})
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_flat_fold.py -q`
Expected: collection error — `ModuleNotFoundError: No module named 'flat_fold'` (or ImportError on the names).

- [ ] **Step 4: Write the implementation**

Create `mcp_harness/flat_fold.py`:

```python
"""Analytic flat-folded 2D state of a compiled base (folded-state-first
slice 1): where every face of a crease pattern lands at a 100% flat
fold, by composing reflections along the face-adjacency tree (Lang's
construction). Self-consistency is REPORTED, not assumed: hull-frontier
bases (accepted Kawasaki violations) and squared display folds have no
consistent flat-folded state — flat_fold() returns their closure errors
instead of raising.

Spec:  docs/superpowers/specs/2026-07-03-flat-fold-engine-slice1-design.md
Probe: docs/superpowers/2026-07-03-probe-folded-state-findings.md
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

import numpy as np

# Non-tree shared edges whose two transform paths disagree by more than
# this (paper units) are "bad": genuine flat-fold inconsistency rather
# than float noise. Clean raw bases measure <= 1e-9; the first genuinely
# inconsistent fixtures measure >= 0.39 (probe findings §2).
CLOSURE_EPS = 1e-6


def _validate(fold: dict) -> None:
    for key in ("vertices_coords", "edges_vertices", "edges_assignment"):
        if not fold.get(key):
            raise ValueError(f"fold is missing or has empty '{key}'")
    if len(fold["edges_vertices"]) != len(fold["edges_assignment"]):
        raise ValueError(
            "edges_vertices and edges_assignment lengths differ")


def _signed_area(P: np.ndarray) -> float:
    x, y = P[:, 0], P[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def _extract_faces(V: np.ndarray, edges: list) -> list[list[int]]:
    """Interior faces (CCW) of the planar straight-line graph.

    Angle-sorted rotations + half-edge walk — the same construction the
    vendored bridge gets from the FOLD JS library
    (vertices_vertices_to_faces_vertices). The outer face winds CW
    (signed area < 0) and is dropped.
    """
    nbrs: dict[int, list[int]] = {}
    for u, v in edges:
        nbrs.setdefault(u, []).append(v)
        nbrs.setdefault(v, []).append(u)
    for u in nbrs:
        nbrs[u].sort(key=lambda w: math.atan2(V[w][1] - V[u][1],
                                              V[w][0] - V[u][0]))
    limit = 2 * len(edges) + 1
    visited: set[tuple[int, int]] = set()
    interior: list[list[int]] = []
    for start in [(u, v) for u, v in edges] + [(v, u) for u, v in edges]:
        if start in visited:
            continue
        face: list[int] = []
        u, v = start
        while (u, v) not in visited:
            if len(face) > limit:
                raise ValueError("face walk failed to terminate")
            visited.add((u, v))
            face.append(u)
            ring = nbrs[v]
            u, v = v, ring[(ring.index(u) - 1) % len(ring)]
        if (u, v) != start:
            raise ValueError("face walk failed to close")
        if _signed_area(V[face]) > 0:
            interior.append(face)
    return interior
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_flat_fold.py -q`
Expected: `7 passed`.

- [ ] **Step 6: Commit**

```bash
git add flat_fold.py tests/test_flat_fold.py tests/goldens/bear-base.fold tests/goldens/dog.fold
git commit -m "feat(flat-fold): face extraction from bare crease patterns + input validation"
```

---

### Task 2: Reflection composition — `flat_fold()`, `ClosureReport`, `FlatFoldResult`

**Files:**
- Modify: `mcp_harness/flat_fold.py` (append)
- Modify: `mcp_harness/tests/test_flat_fold.py` (append)

**Interfaces:**
- Consumes: `_validate`, `_signed_area`, `_extract_faces` from Task 1 (signatures above).
- Produces: `flat_fold(fold: dict) -> FlatFoldResult` with `.faces: list[list[int]]`, `.transforms: list[np.ndarray]` (3x3), `.folded_vertices: list[np.ndarray]` (per-face Nx2), `.closure: ClosureReport` (`.edge_errors: tuple[(float, (int,int), str)]`, `.max_error: float`, `.bad_edges: tuple`). `CLOSURE_EPS = 1e-6`. Task 3 consumes `flat_fold` and `.folded_vertices`.

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_flat_fold.py` (extend the top import line to `from flat_fold import CLOSURE_EPS, FlatFoldResult, _extract_faces, _signed_area, _validate, flat_fold`; also `import sys` then `sys.path.insert` is NOT needed — tests run from `mcp_harness/`):

```python
CLEAN_RAW = ["star-4.fold", "hshape.fold", "quad.fold", "dog.fold"]


class TestCleanTier:
    @pytest.mark.parametrize("name", CLEAN_RAW)
    def test_raw_bases_close(self, name):
        res = flat_fold(load_golden(name))
        assert res.closure.max_error < 1e-6
        assert res.closure.bad_edges == ()

    @pytest.mark.parametrize("name", CLEAN_RAW)
    def test_folded_bbox_within_flat_bbox(self, name):
        fold = load_golden(name)
        V = cp_vertices(fold)
        res = flat_fold(fold)
        pts = np.vstack(res.folded_vertices)
        eps = 1e-9
        assert (pts.min(0) >= V.min(0) - eps).all()
        assert (pts.max(0) <= V.max(0) + eps).all()

    @pytest.mark.parametrize("name", CLEAN_RAW)
    def test_per_face_isometry(self, name):
        fold = load_golden(name)
        V = cp_vertices(fold)
        res = flat_fold(fold)
        for f, P in zip(res.faces, res.folded_vertices):
            for j in range(len(f)):
                flat_len = np.linalg.norm(V[f[j]] - V[f[(j + 1) % len(f)]])
                fold_len = np.linalg.norm(P[j] - P[(j + 1) % len(f)])
                assert abs(flat_len - fold_len) < 1e-9

    def test_deterministic(self):
        fold = load_golden("dog.fold")
        a, b = flat_fold(fold), flat_fold(fold)
        assert a.faces == b.faces
        for ta, tb in zip(a.transforms, b.transforms):
            assert np.array_equal(ta, tb)
        for pa, pb in zip(a.folded_vertices, b.folded_vertices):
            assert np.array_equal(pa, pb)

    def test_transforms_are_orthogonal(self):
        # every transform is a composition of reflections: orthogonal
        # linear part, det = +/-1
        res = flat_fold(load_golden("quad.fold"))
        for T in res.transforms:
            L = T[:2, :2]
            assert np.allclose(L @ L.T, np.eye(2), atol=1e-12)


class TestHullFrontierTier:
    def test_bear_reports_inconsistency_without_raising(self):
        # Drift-tripwire values: MEASURED from this implementation
        # (BFS spanning tree), sanity-bounded by the probe's findings
        # (probe measured 15 bad edges, max 1.199 with a different
        # tree; the error magnitude is tree-dependent, the EXISTENCE
        # of inconsistency is not).
        res = flat_fold(load_golden("bear-base.fold"))
        bad = res.closure.bad_edges
        assert len(bad) == BEAR_BAD_EDGES
        assert 1.0 <= res.closure.max_error <= 1.4
        # closure errors are reported, never raised
        assert isinstance(res, FlatFoldResult)


class TestSquaredFoldBehavior:
    def test_squaring_breaks_closure_and_is_reported(self):
        import square_complete
        fold = load_golden("dog.fold")
        raw = flat_fold(fold)
        assert raw.closure.bad_edges == ()
        squared = square_complete.complete_square(
            json.loads(json.dumps(fold)), 1.0, 1.0)
        res = flat_fold(squared)
        assert len(res.closure.bad_edges) > 0
        assert res.closure.max_error > 0.1


class TestErrorPaths:
    def test_flat_fold_validates(self):
        with pytest.raises(ValueError):
            flat_fold({"vertices_coords": [], "edges_vertices": [],
                       "edges_assignment": []})

    def test_degenerate_crease_raises(self):
        # two coincident vertices joined by an M edge inside a creased
        # square: zero-length crease is structurally unusable
        fold = {
            "vertices_coords": [[0, 0], [1, 0], [1, 1], [0, 1],
                                [0.5, 0.5], [0.5, 0.5]],
            "edges_vertices": [[0, 1], [1, 2], [2, 3], [3, 0],
                               [0, 4], [4, 5], [5, 2]],
            "edges_assignment": ["B", "B", "B", "B", "V", "M", "V"],
        }
        with pytest.raises(ValueError):
            flat_fold(fold)
```

At the top of the test file (after `GOLDENS = ...`) add the tripwire constant placeholder value measured in Step 4:

```python
# Drift tripwire, measured from THIS implementation in Task 2 Step 4
# (spanning-tree-dependent; see TestHullFrontierTier).
BEAR_BAD_EDGES = 15
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_flat_fold.py -q`
Expected: FAIL — `ImportError: cannot import name 'flat_fold'`.

- [ ] **Step 3: Write the implementation**

Append to `mcp_harness/flat_fold.py`:

```python
@dataclass(frozen=True)
class ClosureReport:
    """Cycle-closure errors of the reflection composition: one entry
    per non-spanning-tree shared edge, as (error_paper_units,
    (v_lo, v_hi), edge_assignment). Large errors mean the input has no
    consistent flat-folded state (hull-frontier Kawasaki violations,
    squared frames) — a reported property, not an error condition."""
    edge_errors: tuple

    @property
    def max_error(self) -> float:
        return max((e for e, _, _ in self.edge_errors), default=0.0)

    @property
    def bad_edges(self) -> tuple:
        return tuple(x for x in self.edge_errors if x[0] > CLOSURE_EPS)


@dataclass(frozen=True)
class FlatFoldResult:
    faces: list            # interior faces, CCW vertex-index lists
    transforms: list       # per-face 3x3 homogeneous 2D (flat -> folded)
    folded_vertices: list  # per-face Nx2 arrays; [i][j] is the image of
                           # faces[i][j] (a CP vertex has one image PER
                           # face it belongs to)
    closure: "ClosureReport"


def _reflect(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """3x3 homogeneous reflection across the line through a and b."""
    d = b - a
    n = float(np.hypot(d[0], d[1]))
    if n < 1e-12:
        raise ValueError("degenerate zero-length crease")
    d = d / n
    R = np.eye(3)
    R[0, 0] = d[0] * d[0] - d[1] * d[1]
    R[0, 1] = R[1, 0] = 2.0 * d[0] * d[1]
    R[1, 1] = d[1] * d[1] - d[0] * d[0]
    R[:2, 2] = a - R[:2, :2] @ a
    return R


def _apply(T: np.ndarray, p: np.ndarray) -> np.ndarray:
    return T[:2, :2] @ p + T[:2, 2]


def flat_fold(fold: dict) -> FlatFoldResult:
    """Analytic flat-folded state of a FOLD crease pattern.

    Raises ValueError only for structurally unusable input; folds with
    no consistent flat-folded state return normally with large
    closure errors (see ClosureReport).
    """
    _validate(fold)
    V = np.asarray([v[:2] for v in fold["vertices_coords"]], dtype=float)
    edges = [tuple(e) for e in fold["edges_vertices"]]
    for u, v in edges:
        if float(np.hypot(*(V[u] - V[v]))) < 1e-12:
            raise ValueError("degenerate zero-length edge")
    faces = _extract_faces(V, edges)
    if not faces:
        raise ValueError("crease pattern has no interior faces")
    assign = {tuple(sorted(e)): a
              for e, a in zip(edges, fold["edges_assignment"])}

    # face adjacency across shared edges (an edge bounds <= 2 faces)
    edge_faces: dict[tuple[int, int], list[int]] = {}
    for fi, f in enumerate(faces):
        for j in range(len(f)):
            k = tuple(sorted((f[j], f[(j + 1) % len(f)])))
            edge_faces.setdefault(k, []).append(fi)
    adj: dict[int, list] = {i: [] for i in range(len(faces))}
    shared = []
    for k, fs in edge_faces.items():
        if len(fs) == 2:
            shared.append((fs[0], fs[1], k))
            adj[fs[0]].append((fs[1], k))
            adj[fs[1]].append((fs[0], k))

    def edge_transform(k: tuple[int, int]) -> np.ndarray:
        # M/V creases reflect at a 100% flat fold; F (facet) edges join
        # faces that fold together; B never bounds two faces.
        return (_reflect(V[k[0]], V[k[1]])
                if assign.get(k, "F") in ("M", "V") else np.eye(3))

    # deterministic root: largest interior face, ties to lowest index
    root = max(range(len(faces)),
               key=lambda i: (abs(_signed_area(V[faces[i]])), -i))
    T: list = [None] * len(faces)
    T[root] = np.eye(3)
    tree: set = set()
    q = deque([root])
    while q:
        fi = q.popleft()
        for fj, k in adj[fi]:
            if T[fj] is None:
                T[fj] = T[fi] @ edge_transform(k)
                tree.add((min(fi, fj), max(fi, fj), k))
                q.append(fj)
    if any(t is None for t in T):
        raise ValueError("face-adjacency graph is disconnected")

    errors = []
    for fa, fb, k in shared:
        if (min(fa, fb), max(fa, fb), k) in tree:
            continue
        expect = T[fa] @ edge_transform(k)
        err = max(float(np.linalg.norm(_apply(expect, V[p])
                                       - _apply(T[fb], V[p])))
                  for p in k)
        errors.append((err, k, assign.get(k, "F")))

    folded = [np.asarray([_apply(T[i], V[p]) for p in f])
              for i, f in enumerate(faces)]
    return FlatFoldResult(faces=faces, transforms=T,
                          folded_vertices=folded,
                          closure=ClosureReport(edge_errors=tuple(errors)))
```

- [ ] **Step 4: Measure the bear tripwire values from THIS implementation**

Run:

```bash
.venv/bin/python -c "
import json
from flat_fold import flat_fold
res = flat_fold(json.load(open('tests/goldens/bear-base.fold')))
print('bad_edges:', len(res.closure.bad_edges),
      'max_error:', round(res.closure.max_error, 4))"
```

Expected output shape: `bad_edges: <N> max_error: <M>` with N near 15 and M within [1.0, 1.4]. **Set `BEAR_BAD_EDGES` in the test file to the printed N.** If M falls outside [1.0, 1.4], widen the asserted range in `test_bear_reports_inconsistency_without_raising` to bracket the printed value (±0.2) — the magnitude is spanning-tree-dependent; record the change in the commit message. If N is 0 or M < 0.1, STOP: that contradicts the probe (bear must be inconsistent) — debug before proceeding.

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_flat_fold.py -q`
Expected: `25 passed` (7 from Task 1 + 18 new: 4+4+4 parametrized clean-tier + determinism + orthogonality + bear + squared + 2 error paths).

- [ ] **Step 6: Run the full backend suite's fast neighbors to check nothing broke**

Run: `.venv/bin/python -m pytest tests/test_flat_fold.py tests/test_shaping.py -q`
Expected: all pass (shaping suite untouched; this just guards accidental namespace collisions).

- [ ] **Step 7: Commit**

```bash
git add flat_fold.py tests/test_flat_fold.py
git commit -m "feat(flat-fold): reflection composition with first-class closure report"
```

---

### Task 3: Sim-agreement acceptance test (star-4 vs pinned 100% capture)

**Files:**
- Modify: `mcp_harness/tests/test_flat_fold.py` (append)
- Uses fixture: `mcp_harness/tests/goldens/star4-sim-100.json` (already committed with the spec — the probe's converged 100% browser capture: maxMove 3e-5 between windows, planar to 3rd singular value 0.000)

**Interfaces:**
- Consumes: `flat_fold(fold) -> FlatFoldResult` (`.faces`, `.folded_vertices`) from Task 2.
- Produces: nothing new — final acceptance tier.

- [ ] **Step 1: Write the failing test**

Append to `mcp_harness/tests/test_flat_fold.py`:

```python
def _kabsch(A, B):
    """Best rigid alignment A->B; reflection allowed (a flat fold has
    mirror ambiguity — the sim may settle on either enantiomer)."""
    ca, cb = A.mean(0), B.mean(0)
    U, _, Vt = np.linalg.svd((A - ca).T @ (B - cb))
    R = Vt.T @ U.T
    return lambda X: (X - ca) @ R.T + cb


class TestSimAgreement:
    def test_star4_analytic_matches_converged_sim_capture(self):
        fold = load_golden("star-4.fold")
        cap = load_golden("star4-sim-100.json")
        V = cp_vertices(fold)
        Vsim = np.asarray(cap["vertices_coords"], dtype=float)
        flat = np.asarray(cap["flat_coords"], dtype=float)
        assert len(Vsim) == len(V)  # sim nodes are 1:1 with CP vertices

        res = flat_fold(fold)
        # one analytic image per CP vertex (star-4 closes: per-face
        # images of the same vertex coincide)
        img = {}
        for f, P in zip(res.faces, res.folded_vertices):
            for v, p in zip(f, P):
                img.setdefault(v, []).append(p)
        for ps in img.values():
            assert np.ptp(np.asarray(ps), 0).max() < 1e-9
        pos = {v: np.mean(ps, axis=0) for v, ps in img.items()}

        # sim-node -> CP-vertex correspondence via the capture's flat
        # coords: the sim recenters and rescales the pattern into a
        # plane, so fit a similarity and match nearest
        plane = sorted(np.argsort(np.ptp(flat, 0))[-2:])
        f2 = flat[:, plane]
        scale = float((np.ptp(f2, 0) / np.ptp(V, 0)).mean())
        Vs = (V - V.mean(0)) * scale + f2.mean(0)
        idx = [int(np.linalg.norm(Vs - q, axis=1).argmin()) for q in f2]
        assert sorted(idx) == list(range(len(V)))  # bijective match

        # embed the analytic folded state in 3D (z=0), align, compare
        A = np.array([np.append((pos[idx[i]] - V.mean(0)) * scale, 0.0)
                      for i in range(len(Vsim))])
        fit = _kabsch(A, Vsim)
        residual = float(np.linalg.norm(fit(A) - Vsim, axis=1).max())
        assert residual / scale < 1e-3  # paper units
```

- [ ] **Step 2: Run the test to verify it fails only for the right reason**

Run: `.venv/bin/python -m pytest tests/test_flat_fold.py::TestSimAgreement -v`
Expected: PASS is actually possible here because Task 2 already implemented the engine — TDD's failing-first requirement was satisfied at the engine level in Tasks 1–2; this test pins an ACCEPTANCE number. To still verify the test can fail, temporarily run it with a broken tolerance: change `1e-3` to `1e-12`, run, confirm FAIL on the residual assert (not on correspondence or spread asserts), then restore `1e-3`. If it fails on the bijective-match or image-spread asserts instead, debug — the correspondence recovery is broken, not the engine.

- [ ] **Step 3: Run the full test file**

Run: `.venv/bin/python -m pytest tests/test_flat_fold.py -q`
Expected: `26 passed`.

- [ ] **Step 4: Run the fast backend neighbors**

Run: `.venv/bin/python -m pytest tests/test_flat_fold.py tests/test_shaping.py tests/test_square_complete.py -q`
Expected: all pass. (Skip the full 10-minute compile suite here; the final-review gate runs it.)

- [ ] **Step 5: Commit**

```bash
git add tests/test_flat_fold.py
git commit -m "test(flat-fold): pin analytic-vs-sim agreement on the converged star-4 capture"
```

---

## Final verification (after all tasks)

- [ ] Full backend suite: `.venv/bin/python -m pytest tests -q` (~10 min, real compiles) — expected `313 passed / 3 skipped` (287 at branch time + 26 new; report the exact count at review).
- [ ] Web + frontend untouched: `git diff origin/main --stat` shows only `mcp_harness/flat_fold.py`, `mcp_harness/tests/test_flat_fold.py`, `mcp_harness/tests/goldens/{bear-base,dog}.fold`, plus the spec-commit files.
- [ ] Request final whole-branch code review, then finishing-a-development-branch.
