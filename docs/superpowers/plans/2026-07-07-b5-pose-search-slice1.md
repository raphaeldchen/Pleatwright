# B5 Slice 1 — Pose-Search Recovery Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove the pose-search loop (apply op → sim relax → capture → chamfer score → iterate) closes end-to-end by recovering a known `(θ*, d*)` reverse-fold pose on star-4 from cold grid search; side-probe whether a hull-filling quadruped base exists (the gate on full B5).

**Architecture:** A pure, pytest-covered module (`pose_search.py`: chamfer + grid_search + refine, evaluator injected) sits under three committed manual probes. A probe-support capture driver (`sim_capture.py`, Python Playwright against the vendored Origami Simulator's `ide-bridge.js` postMessage API) supplies real evaluations. The de-risk sensitivity probe runs FIRST and can halt the slice; the recovery probe is the deliverable; the hull-quad probe produces a written finding.

**Tech Stack:** Python 3 (mcp_harness venv), numpy, pytest; Python `playwright` (chromium) as a **local-venv-only** probe dependency; the vendored Origami Simulator at `web/frontend/dist/simulator/` served by an in-process `http.server`.

**Spec:** `docs/superpowers/specs/2026-07-07-b5-pose-search-slice1-design.md` (approved 2026-07-07).

## Global Constraints

- **Measure-then-pin:** no test/probe value is pinned before a committed probe has printed it AND it has been checked against hand reasoning. Grid bounds, `(θ*, d*)`, and tolerances in Task 4 are chosen from Task 3's printed output, not invented.
- **Star-4 is the only folding base** (squared dog/quad relax FLAT, maxDisp exactly 0.0). Every capture must pass the anti-vacuous guards: **maxDisplacement ≥ 0.10** (`DISP_GATE`, same value as `probe_deep_sim_smoke.py`) and **0 NaN**. A displacement-0 capture is a FAILED capture, never a valid low-chamfer candidate.
- **Provenance contract untouched:** no changes to `web/server.py`, the lint path, or the raw `json` frame. Probes run offline on locally built folds.
- **`pose_search.py` imports no sim/Playwright/web code** — numpy + stdlib only. Evaluators are injected callables.
- **Playwright is a local dev dependency only:** installed into `mcp_harness/.venv`, NEVER added to `requirements*.txt`, `ci.yml`, or any pinned dep list (CI pins are exact-match drift tripwires). No probe or capture module is imported by anything under `mcp_harness/tests/`.
- **No new MCP tools, no agent/prompt changes, no UI changes** (spec §6).
- Backend suite must stay green: `cd mcp_harness && .venv/bin/python -m pytest tests -q` (~10 min; 401 passed / 3 skipped at branch time).
- Failed candidate evaluations score `inf` and are skipped; a failed **target** capture aborts the recovery run.
- Branch: `feat/b5-pose-search-slice1` off `main` (030b924 or later).

## File Map

| File | Responsibility |
|---|---|
| `mcp_harness/pose_search.py` (create) | Pure objective + search: `chamfer`, `grid_search`, `refine`, `PoseSearchError` |
| `mcp_harness/tests/test_pose_search.py` (create) | pytest coverage of the pure module (mocked evaluators, hand-derived fixtures) |
| `mcp_harness/sim_capture.py` (create) | Probe support (NOT in pytest suite): Playwright `SimSession` capture driver, capture guards, star-4 shaped-fold builder; `__main__` = anchor validation |
| `mcp_harness/probe_pose_sensitivity.py` (create) | De-risk gate: does the equilibrium vary with θ<180 above capture noise? |
| `mcp_harness/probe_pose_recovery.py` (create) | The deliverable: target capture → 5×5 grid → refine → recovery verdict |
| `mcp_harness/probe_hull_quad.py` (create) | Hull-filling quadruped side probe (compile → no-op check → lint → sim) |
| `docs/superpowers/2026-07-07-handoff-b5-slice1-outcome.md` (create, Task 6) | Findings write-up incl. the hull-quad finding and the pinned numbers |

Background facts an implementer needs (all verified in-repo, 2026-07-07):

- **The sim bridge** (`web/frontend/dist/simulator/js/ide-bridge.js`) listens for `message` events where `e.origin === window.location.origin` and understands `{type:'loadFold', fold}`, `{type:'setFold', percent}`, `{type:'getFoldedGeometry'}`; it replies by posting `{type:'foldedGeometry', vertices_coords, faces_vertices, flat_coords}` (or `{type:'error', message}`) to `parent`. When the page is loaded **top-level** (not in an iframe), `parent === window`, so a listener installed in the page via `page.evaluate` receives the reply, and `window.postMessage(msg, location.origin)` passes the origin check. `setFold` both sets the crease percent AND raises `shouldChangeCreasePercent` (without which the GPU solver never re-targets).
- **The solver needs wall-clock time:** after `setFold(100)`, wait ~20 s for the GPU relaxation (proven pattern, `probe_deep_sim_smoke.py`).
- **Anchor measurement** (2026-07-06, recorded in `probe_deep_sim_smoke.py`): un-shaped squared star-4 relaxes to **maxDisplacement 1.3109**, 0 NaN, strain 0.0. Task 2 validates the new driver against this.
- **Star-4 golden:** `mcp_harness/tests/goldens/star-4.fold` — its leaf hull fills the square, so `square_complete.complete_square(raw, 1.0, 1.0)` is a no-op (raw == squared).
- **Tip-local op grammar:** `reverse:{x},{y}:{d}:{theta}` applied via `shaping.apply_display_ops(squared, [op], raw=raw)`; a refused op returns the **same object** (check identity, like `probe_deep_sim_smoke.py` line 99).
- **Compile worker** (hull-quad probe): `server._run_isolated(server._worker_compile_and_regions, json.dumps(nodes), [list(p) for p in pairs], 1.0, 1.0)` returns JSON `{"fold": ..., "locs": [[node_id, x, y], ...], ...}`; nodes are `{"id", "parent_id", "length"}` dicts (`tests/cases.py`). Lint: `linter_server.validate_flat_foldability(fold_json_str)` returns a verdict string.
- **Long runs:** the recovery probe is ~50 captures × ~25 s ≈ 20–25 min. Run it in the background (`nohup … &` or the harness's background Bash) and tail its JSONL log; a foreground Bash call will hit the 10-min timeout.

---

### Task 1: `pose_search.py` — pure chamfer + grid + refine (TDD)

**Files:**
- Create: `mcp_harness/pose_search.py`
- Test: `mcp_harness/tests/test_pose_search.py`

**Interfaces:**
- Consumes: numpy, stdlib only.
- Produces (used verbatim by Tasks 3–4):
  - `chamfer(A, B) -> float` — symmetric mean nearest-neighbor distance between `(N,3)` (or `(N,k)`) arrays; raises `PoseSearchError` on empty/mismatched-width inputs. **No registration/alignment step** (same base, same sim frame — spec §3a).
  - `grid_search(evaluate, axes) -> GridResult` — `axes` is a sequence of 1-D value sequences; `evaluate(params_tuple) -> float`; evaluations that raise or return non-finite score `inf` and are skipped; all-`inf` raises `PoseSearchError`. `GridResult(best_params: tuple, best_score: float, scores: dict[tuple, float])`.
  - `refine(evaluate, axes, best_params, points=5) -> GridResult` — one local pass: per axis, span the closed interval between the best value's immediate grid neighbors (clamped at ends), re-sampled at `points` evenly spaced values; then `grid_search` on the new axes.
  - `PoseSearchError(ValueError)`.

- [ ] **Step 1: Write the failing tests**

Create `mcp_harness/tests/test_pose_search.py`:

```python
"""Pure pose-search module: chamfer objective + grid/refine search.

No sim, no Playwright — evaluators are mocked (spec 2026-07-07-b5, section 4).
Chamfer fixtures are hand-derived (worked in the comments).
"""
import math

import numpy as np
import pytest

import pose_search
from pose_search import PoseSearchError, chamfer, grid_search, refine


# ---------- chamfer ----------

def test_chamfer_identical_sets_is_zero():
    A = np.array([[0.0, 0.0, 0.0], [1.0, 2.0, 3.0], [-1.0, 0.5, 2.0]])
    assert chamfer(A, A.copy()) == pytest.approx(0.0)


def test_chamfer_single_points_is_euclidean_distance():
    # A->B nearest = 5 (3-4-5 triangle); B->A nearest = 5; mean of means = 5.
    A = np.array([[0.0, 0.0, 0.0]])
    B = np.array([[3.0, 4.0, 0.0]])
    assert chamfer(A, B) == pytest.approx(5.0)


def test_chamfer_asymmetric_sets_hand_derived():
    # A = {(0,0,0),(1,0,0)}, B = {(0,0,0)}.
    # A->B: dists 0 and 1, mean 0.5.  B->A: dist 0, mean 0.0.
    # symmetric chamfer = (0.5 + 0.0) / 2 = 0.25.
    A = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    B = np.array([[0.0, 0.0, 0.0]])
    assert chamfer(A, B) == pytest.approx(0.25)
    assert chamfer(B, A) == pytest.approx(0.25)  # symmetric by construction


def test_chamfer_is_translation_sensitive_no_registration():
    # Deliberate: shifting one cloud must CHANGE the score (spec: no
    # alignment step -- target and candidate share the sim frame).
    A = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    assert chamfer(A, A + np.array([0.0, 0.0, 2.0])) == pytest.approx(2.0)


def test_chamfer_rejects_empty_and_mismatched():
    A = np.array([[0.0, 0.0, 0.0]])
    with pytest.raises(PoseSearchError):
        chamfer(A, np.empty((0, 3)))
    with pytest.raises(PoseSearchError):
        chamfer(A, np.array([[1.0, 2.0]]))  # width 2 vs 3


# ---------- grid_search ----------

def _bowl(center):
    def evaluate(params):
        return sum((p - c) ** 2 for p, c in zip(params, center))
    return evaluate


def test_grid_search_finds_bowl_minimum_on_grid():
    axes = [[60.0, 90.0, 120.0, 150.0], [0.2, 0.4, 0.6, 0.8]]
    res = grid_search(_bowl((120.0, 0.4)), axes)
    assert res.best_params == (120.0, 0.4)
    assert res.best_score == pytest.approx(0.0)
    assert len(res.scores) == 16  # every cell evaluated and recorded


def test_grid_search_skips_raising_and_nonfinite_evals():
    calls = []

    def evaluate(params):
        calls.append(params)
        if params == (1.0, 1.0):
            raise RuntimeError("capture failed")
        if params == (1.0, 2.0):
            return float("nan")
        return abs(params[0] - 2.0) + abs(params[1] - 2.0)

    res = grid_search(evaluate, [[1.0, 2.0], [1.0, 2.0]])
    assert res.scores[(1.0, 1.0)] == math.inf   # raised -> inf, not fatal
    assert res.scores[(1.0, 2.0)] == math.inf   # nan -> inf
    assert res.best_params == (2.0, 2.0)
    assert len(calls) == 4                      # search continued past failures


def test_grid_search_all_failed_raises():
    def evaluate(params):
        raise RuntimeError("boom")

    with pytest.raises(PoseSearchError):
        grid_search(evaluate, [[1.0, 2.0]])


# ---------- refine ----------

def test_refine_tightens_around_off_grid_optimum():
    # True optimum (100, 0.45) sits inside the (90..120)x(0.4..0.6) cell.
    evaluate = _bowl((100.0, 0.45))
    axes = [[60.0, 90.0, 120.0, 150.0], [0.2, 0.4, 0.6, 0.8]]
    coarse = grid_search(evaluate, axes)
    assert coarse.best_params == (90.0, 0.4)
    fine = refine(evaluate, axes, coarse.best_params, points=5)
    # Refine spans [60,120]x[0.2,0.6] at 5 points -> includes finer values.
    assert fine.best_score < coarse.best_score
    assert abs(fine.best_params[0] - 100.0) <= abs(coarse.best_params[0] - 100.0)
    assert abs(fine.best_params[1] - 0.45) <= abs(coarse.best_params[1] - 0.45)


def test_refine_clamps_at_grid_edges():
    evaluate = _bowl((60.0, 0.2))     # optimum at the grid corner
    axes = [[60.0, 90.0], [0.2, 0.4]]
    coarse = grid_search(evaluate, axes)
    assert coarse.best_params == (60.0, 0.2)
    fine = refine(evaluate, axes, coarse.best_params, points=3)
    # Neighbor interval clamps to [60,90]x[0.2,0.4]; still finds the corner.
    assert fine.best_params == (60.0, 0.2)
    for params in fine.scores:
        assert 60.0 <= params[0] <= 90.0
        assert 0.2 <= params[1] <= 0.4
```

- [ ] **Step 2: Run tests, verify they fail with `ModuleNotFoundError: pose_search`**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_pose_search.py -q`
Expected: collection error, `No module named 'pose_search'`.

- [ ] **Step 3: Implement `mcp_harness/pose_search.py`**

```python
"""B5 slice 1 -- pure pose-search machinery (spec: docs/superpowers/specs/
2026-07-07-b5-pose-search-slice1-design.md, section 3a).

chamfer(A, B)              symmetric mean nearest-neighbor distance. NO
                           registration step: target and candidate captures
                           share the same base and sim coordinate frame.
grid_search(evaluate, axes) exhaustive cartesian grid; evaluator failures
                           (raise / non-finite) score inf and are skipped.
refine(evaluate, axes, best_params) one local pass around the argmin cell.

Deliberately sim-free: no Playwright, no web imports. Evaluators are
injected callables (params_tuple -> float), so the suite covers the search
logic with mocks while the committed probes supply real sim evaluations.
"""
from __future__ import annotations

import itertools
import math
from collections import namedtuple

import numpy as np


class PoseSearchError(ValueError):
    """Bad inputs or a search with no successful evaluation."""


GridResult = namedtuple("GridResult", "best_params best_score scores")


def chamfer(A, B) -> float:
    """Symmetric mean nearest-neighbor distance between two point sets."""
    A = np.asarray(A, dtype=float)
    B = np.asarray(B, dtype=float)
    if A.ndim != 2 or B.ndim != 2:
        raise PoseSearchError("point sets must be 2-D arrays (N, k)")
    if A.shape[0] == 0 or B.shape[0] == 0:
        raise PoseSearchError("point sets must be non-empty")
    if A.shape[1] != B.shape[1]:
        raise PoseSearchError(
            f"point width mismatch: {A.shape[1]} vs {B.shape[1]}")
    d2 = ((A[:, None, :] - B[None, :, :]) ** 2).sum(axis=-1)
    a_to_b = np.sqrt(d2.min(axis=1)).mean()
    b_to_a = np.sqrt(d2.min(axis=0)).mean()
    return float((a_to_b + b_to_a) / 2.0)


def _score_one(evaluate, params) -> float:
    try:
        s = float(evaluate(params))
    except Exception:
        return math.inf
    return s if math.isfinite(s) else math.inf


def grid_search(evaluate, axes) -> GridResult:
    """Evaluate every cell of the cartesian grid; failures score inf."""
    axes = [list(a) for a in axes]
    if not axes or any(len(a) == 0 for a in axes):
        raise PoseSearchError("axes must be non-empty value sequences")
    scores = {}
    for params in itertools.product(*axes):
        scores[params] = _score_one(evaluate, params)
    finite = {p: s for p, s in scores.items() if s < math.inf}
    if not finite:
        raise PoseSearchError("every grid evaluation failed (all inf)")
    best = min(finite, key=finite.get)
    return GridResult(best, finite[best], scores)


def refine(evaluate, axes, best_params, points: int = 5) -> GridResult:
    """One local pass: re-grid the neighbor interval around the argmin."""
    new_axes = []
    for values, best in zip(axes, best_params):
        vs = sorted(float(v) for v in values)
        i = vs.index(float(best))
        lo, hi = vs[max(i - 1, 0)], vs[min(i + 1, len(vs) - 1)]
        if lo == hi:
            new_axes.append([lo])
            continue
        step = (hi - lo) / (points - 1)
        new_axes.append([lo + step * k for k in range(points)])
    return grid_search(evaluate, new_axes)
```

- [ ] **Step 4: Run the new tests, verify all pass**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_pose_search.py -v`
Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
cd <repo>
git add mcp_harness/pose_search.py mcp_harness/tests/test_pose_search.py
git commit -m "feat(b5): pose_search -- chamfer objective + grid/refine (pure, mocked-evaluator tests)"
```

---

### Task 2: `sim_capture.py` — Playwright capture driver + anchor validation

**Files:**
- Create: `mcp_harness/sim_capture.py`
- Modify: none (playwright is installed into `.venv` only; NO requirements/CI file is touched)

**Interfaces:**
- Consumes: `web/frontend/dist/simulator/index.html?embed=1` + `ide-bridge.js` postMessage API; `shaping.apply_display_ops`, `shaping.axial_length`, `square_complete.complete_square`, golden `tests/goldens/star-4.fold`.
- Produces (used verbatim by Tasks 3–5):
  - `SimSession(headless=None, settle_s=20.0)` — context manager owning one chromium page + an in-process static server on `web/frontend/dist`; `capture(fold: dict) -> dict` reloads the page, loads the fold, `setFold(100)`, waits `settle_s`, returns the raw `foldedGeometry` dict. `headless=None` means headless unless env `PW_HEADED=1`.
  - `check_capture(cap: dict) -> tuple[np.ndarray, float]` — returns `(folded_vertices (N,3), max_displacement)`; raises `CaptureError` on empty geometry, missing/mismatched `flat_coords`, any non-finite coordinate, or `max_displacement < DISP_GATE` (the vacuous-pass trap).
  - `DISP_GATE = 0.10` (same value/meaning as `probe_deep_sim_smoke.py`).
  - `build_star4_shaped(theta: float, fraction: float) -> dict` — squared star-4 with `reverse:{x},{y}:{d}:{theta}` applied at tip vertex 0, `d = fraction * axial_length`; raises `CaptureError` if the op is refused. `build_star4_base() -> dict` — the un-shaped squared base. `fraction=None`/`theta=None` are invalid (no silent defaults).
  - `CaptureError(RuntimeError)`.
- This module is **probe support**: it is never imported by anything under `tests/`. Its validation is the `__main__` anchor run in Step 3, checked against the recorded 2026-07-06 measurement.

- [ ] **Step 1: Install Playwright into the local venv (NOT into any pinned dep file)**

```bash
cd <repo>/mcp_harness
.venv/bin/pip install playwright
.venv/bin/playwright install chromium
```

Expected: both succeed (chromium download is ~150 MB). Verify no dep file changed: `git status` shows no modification to any `requirements*.txt` or `.github/` file.

- [ ] **Step 2: Write `mcp_harness/sim_capture.py`**

```python
"""B5 probe support -- scripted Playwright capture against the vendored
Origami Simulator. NOT part of the pytest suite (probes only); validated by
the __main__ anchor run against the recorded 2026-07-06 measurement
(un-shaped squared star-4: maxDisplacement 1.3109, 0 NaN -- see
probe_deep_sim_smoke.py).

Bridge protocol (web/frontend/dist/simulator/js/ide-bridge.js): the page,
loaded TOP-LEVEL with ?embed=1, accepts window.postMessage
{loadFold, setFold, getFoldedGeometry} from its own origin and replies to
parent -- which is the page itself at top level, so an in-page listener
receives {type:'foldedGeometry', vertices_coords, faces_vertices,
flat_coords}. setFold raises shouldChangeCreasePercent (without it the GPU
solver never re-targets). The solver relaxes in wall-clock time: wait
settle_s (~20 s, the proven probe_deep_sim_smoke pattern) before reading.

Run the anchor check:
  cd mcp_harness && .venv/bin/python sim_capture.py
Headed fallback if headless WebGL misbehaves:  PW_HEADED=1 .venv/bin/python sim_capture.py
"""
from __future__ import annotations

import functools
import http.server
import json
import os
import sys
import threading

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shaping                      # noqa: E402
import square_complete              # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
GOLDENS = os.path.join(_HERE, "tests", "goldens")
DIST = os.path.abspath(os.path.join(_HERE, "..", "web", "frontend", "dist"))

DISP_GATE = 0.10          # anti-vacuous: the fold must actually move
ANCHOR_DISP = 1.3109      # squared star-4 base, measured 2026-07-06


class CaptureError(RuntimeError):
    """A capture that must not be scored (failed / vacuous / refused op)."""


def _serve(directory: str):
    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=directory)
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


class SimSession:
    """One chromium page + static server, reused across many captures."""

    def __init__(self, headless: bool | None = None, settle_s: float = 20.0):
        from playwright.sync_api import sync_playwright
        if headless is None:
            headless = os.environ.get("PW_HEADED", "") != "1"
        self.settle_s = settle_s
        self._srv = _serve(DIST)
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=headless)
        self._page = self._browser.new_page()
        port = self._srv.server_address[1]
        self._url = f"http://127.0.0.1:{port}/simulator/index.html?embed=1"

    def capture(self, fold: dict) -> dict:
        """Fresh page load -> loadFold -> setFold(100) -> settle -> read."""
        page = self._page
        page.goto(self._url)
        page.wait_for_function(
            "() => window.globals && window.globals.pattern"
            " && typeof window.globals.pattern.setFoldData === 'function'"
            " && typeof window.globals.setCreasePercent === 'function'",
            timeout=30_000)
        page.evaluate(
            "fold => window.postMessage({type:'loadFold', fold},"
            " location.origin)", fold)
        page.evaluate(
            "() => window.postMessage({type:'setFold', percent:100},"
            " location.origin)")
        page.wait_for_timeout(self.settle_s * 1000)
        cap = page.evaluate(
            """() => new Promise((resolve, reject) => {
                 const h = (e) => {
                   const d = e.data || {};
                   if (d.type === 'foldedGeometry') {
                     window.removeEventListener('message', h); resolve(d);
                   } else if (d.type === 'error') {
                     window.removeEventListener('message', h);
                     reject(new Error(d.message));
                   }
                 };
                 window.addEventListener('message', h);
                 window.postMessage({type:'getFoldedGeometry'},
                                    location.origin);
                 setTimeout(() => reject(new Error(
                   'getFoldedGeometry timeout')), 10000);
               })""")
        return cap

    def close(self):
        for closer in (self._browser.close, self._pw.stop,
                       self._srv.shutdown):
            try:
                closer()
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def check_capture(cap: dict):
    """Guards from the spec's error-handling section; returns (V, maxDisp)."""
    verts = cap.get("vertices_coords") or []
    flat = cap.get("flat_coords")
    if not verts:
        raise CaptureError("empty capture (no vertices)")
    V = np.asarray(verts, dtype=float)
    if flat is None:
        raise CaptureError("capture has no flat_coords (node count mismatch)")
    F = np.asarray(flat, dtype=float)
    if len(F) != len(V):
        raise CaptureError(f"node/flat mismatch {len(V)} vs {len(F)}")
    if not np.isfinite(V).all():
        raise CaptureError("non-finite folded coordinates (NaN)")
    disp = float(np.linalg.norm(V - F, axis=1).max())
    if disp < DISP_GATE:
        raise CaptureError(
            f"did not fold: maxDisplacement {disp:.4f} < {DISP_GATE}"
            " (vacuous-pass trap)")
    return V, disp


def _star4_raw() -> dict:
    with open(os.path.join(GOLDENS, "star-4.fold")) as fh:
        return json.load(fh)


def _tip_and_axial(raw: dict):
    """Tip vertex 0's (x, y) and axial length (probe_deep_sim_smoke pattern)."""
    V = np.asarray([p[:2] for p in raw["vertices_coords"]], dtype=float)
    inc: dict = {}
    for ei, (a, b) in enumerate(raw["edges_vertices"]):
        inc.setdefault(a, []).append(ei)
        inc.setdefault(b, []).append(ei)
    ea = raw["edges_assignment"]
    tip = 0
    axial = next(e for e in inc[tip] if ea[e] in ("M", "V"))
    a, b = raw["edges_vertices"][axial]
    other = b if a == tip else a
    return tuple(V[tip]), float(np.linalg.norm(V[other] - V[tip]))


def build_star4_base() -> dict:
    """Un-shaped squared star-4 (squaring is a no-op: hull fills the square)."""
    raw = _star4_raw()
    sq = square_complete.complete_square(raw, 1.0, 1.0)
    return shaping.apply_display_ops(sq, [], raw=raw)


def build_star4_shaped(theta: float, fraction: float) -> dict:
    """Squared star-4 + reverse fold at tip v0: d = fraction * axial length."""
    if not (0.0 < fraction < 1.0):
        raise CaptureError(f"fraction {fraction} outside (0, 1)")
    if not (0.0 < theta <= 180.0):
        raise CaptureError(f"theta {theta} outside (0, 180]")
    raw = _star4_raw()
    sq = square_complete.complete_square(raw, 1.0, 1.0)
    (x, y), axial = _tip_and_axial(raw)
    d = fraction * axial
    op = f"reverse:{x},{y}:{d}:{theta}"
    shaped = shaping.apply_display_ops(sq, [op], raw=raw)
    if shaped is sq:
        raise CaptureError(f"op refused: {op}")
    return shaped


def _anchor_main():
    """Driver validation against the recorded 2026-07-06 anchor."""
    print(f"anchor: un-shaped squared star-4, expect maxDisp ~{ANCHOR_DISP}")
    with SimSession() as sim:
        cap = sim.capture(build_star4_base())
        V, disp = check_capture(cap)
        print(f"  captured {len(V)} verts, maxDisplacement {disp:.4f}")
        ok = 1.0 <= disp <= 1.6
        print(f"  anchor {'PASS' if ok else 'FAIL'}"
              f" (band 1.0..1.6 around recorded {ANCHOR_DISP})")
        return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(_anchor_main())
```

- [ ] **Step 3: Run the anchor validation**

Run: `cd mcp_harness && .venv/bin/python sim_capture.py`
Expected: `anchor PASS` with maxDisplacement in the 1.0–1.6 band (recorded value 1.3109). Takes ~30 s.

If headless chromium's WebGL never moves the fold (`did not fold` CaptureError): retry `PW_HEADED=1 .venv/bin/python sim_capture.py`. If headed passes but headless fails, flip the default in `SimSession.__init__` to `headless = os.environ.get("PW_HEADLESS", "") == "1"` (headed default), update the module docstring, and note the finding in the commit message. If BOTH fail, STOP and report BLOCKED — the driver premise needs human review, do not proceed to Task 3.

- [ ] **Step 4: Confirm the suite does not import the new module**

Run: `cd mcp_harness && grep -rn "sim_capture" tests/ ; .venv/bin/python -m pytest tests/test_pose_search.py -q`
Expected: grep finds nothing; tests still pass (playwright stays out of the suite's import graph).

- [ ] **Step 5: Commit**

```bash
cd <repo>
git add mcp_harness/sim_capture.py
git commit -m "feat(b5): sim_capture Playwright driver -- anchor-validated vs 2026-07-06 star-4 measurement"
```

(Include the measured anchor number in the commit body.)

---

### Task 3: `probe_pose_sensitivity.py` — the de-risk gate (RUNS FIRST)

**Files:**
- Create: `mcp_harness/probe_pose_sensitivity.py`

**Interfaces:**
- Consumes: `sim_capture.SimSession/check_capture/build_star4_shaped/CaptureError`; `pose_search.chamfer`.
- Produces: a printed measurement table + a `PROCEED / PROCEED-WIDENED-THETA / HALT` verdict line, and a JSON results file `mcp_harness/probe_pose_sensitivity.out.json` (git-ignored scratch is fine to leave uncommitted; the printed numbers go in the Task 6 handoff). Task 4's grid bounds and `(θ*, d*)` are chosen FROM this output (measure-then-pin).

**Why this gates the slice (spec §3b):** slices 3–4 only ever sim-smoked θ=180, which relaxes at zero strain. Nothing yet proves the mass-spring equilibrium varies detectably with θ<180. If it doesn't — and d doesn't either — B5's objective cannot see the parameters and the slice halts, cheaply, here.

- [ ] **Step 1: Write the probe**

```python
"""B5 slice-1 de-risk gate (spec 3b): does the sim equilibrium vary with the
reverse-fold parameters ABOVE repeat-capture noise?

Captures on star-4 tip v0:
  theta sweep : theta in {60, 90, 120, 150} at fixed fraction 0.5
  repeat pair : theta=120 captured twice -> chamfer = the NOISE FLOOR
  d sweep     : fraction in {0.3, 0.5, 0.7} at fixed theta=120 (decides the
                "theta flat but d strong" branch of the decision rule)

Every capture must pass check_capture (displacement >= 0.10, 0 NaN).

Decision rule (printed as the last line):
  PROCEED                min adjacent-theta chamfer >  3x noise
  PROCEED-WIDENED-THETA  theta signal <= 3x noise BUT min adjacent-d
                         chamfer > 3x noise (recovery keeps d strict,
                         widens the theta tolerance and SAYS SO)
  HALT                   both signals <= 3x noise -- the objective cannot
                         see the parameters; the slice stops here and the
                         finding is written up (B5 dies cheaply, by design).

Run: cd mcp_harness && .venv/bin/python probe_pose_sensitivity.py
(~8 captures x ~25 s ~ 4 min)
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pose_search                  # noqa: E402
import sim_capture                  # noqa: E402

THETAS = [60.0, 90.0, 120.0, 150.0]
FRACTIONS = [0.3, 0.5, 0.7]
REPEAT_THETA = 120.0
FIXED_FRACTION = 0.5
NOISE_MULT = 3.0
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "probe_pose_sensitivity.out.json")


def main() -> int:
    results = {"theta": {}, "fraction": {}, "repeat": None}
    with sim_capture.SimSession() as sim:

        def grab(theta, fraction, label):
            fold = sim_capture.build_star4_shaped(theta, fraction)
            V, disp = sim_capture.check_capture(sim.capture(fold))
            print(f"  {label}: {len(V)} verts, maxDisp {disp:.4f}")
            return V

        clouds_t = {t: grab(t, FIXED_FRACTION, f"theta={t}") for t in THETAS}
        repeat = grab(REPEAT_THETA, FIXED_FRACTION, "theta=120 (repeat)")
        clouds_f = {f: grab(120.0, f, f"fraction={f}") for f in FRACTIONS}

    noise = pose_search.chamfer(clouds_t[REPEAT_THETA], repeat)
    results["repeat"] = noise
    print(f"\nnoise floor (repeat capture chamfer): {noise:.6f}")

    t_sig = []
    for a, b in zip(THETAS, THETAS[1:]):
        c = pose_search.chamfer(clouds_t[a], clouds_t[b])
        results["theta"][f"{a}->{b}"] = c
        t_sig.append(c)
        print(f"theta {a}->{b}: chamfer {c:.6f}")
    f_sig = []
    for a, b in zip(FRACTIONS, FRACTIONS[1:]):
        c = pose_search.chamfer(clouds_f[a], clouds_f[b])
        results["fraction"][f"{a}->{b}"] = c
        f_sig.append(c)
        print(f"fraction {a}->{b}: chamfer {c:.6f}")

    theta_ok = min(t_sig) > NOISE_MULT * noise
    d_ok = min(f_sig) > NOISE_MULT * noise
    verdict = ("PROCEED" if theta_ok
               else "PROCEED-WIDENED-THETA" if d_ok else "HALT")
    results["verdict"] = verdict
    with open(OUT, "w") as fh:
        json.dump(results, fh, indent=1)
    print(f"\nmin theta signal {min(t_sig):.6f}, min d signal "
          f"{min(f_sig):.6f}, {NOISE_MULT}x noise {NOISE_MULT * noise:.6f}")
    print(f"VERDICT: {verdict}")
    return 0 if verdict != "HALT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run it and sanity-check the numbers by hand**

Run: `cd mcp_harness && .venv/bin/python probe_pose_sensitivity.py` (~4 min; use background Bash if the harness timeout is a concern).
Expected shape of the output (values are MEASUREMENTS, not predictions):
- every capture prints a maxDisp ≥ 0.10 (any `CaptureError` on a θ means that θ's op refused or didn't fold — record it; if MOST θs fail, stop and report BLOCKED);
- noise floor should be small relative to the cloud scale (~1-unit paper);
- hand reasoning check: chamfer(θ=60, θ=90) should EXCEED chamfer(θ=120, θ=150) or at least be the same order — a reverse fold's tip sweeps an arc of roughly `2·d·sin(Δθ/2)` between poses, so adjacent-30° chamfers should be the same order of magnitude as `d ≈ 0.35` × the arc factor, i.e. order 0.01–0.2, NOT 1e-6. If the measured signals contradict this scale reasoning, investigate before trusting a PROCEED.

- [ ] **Step 3: Act on the verdict**

- `PROCEED` / `PROCEED-WIDENED-THETA`: continue to Step 4.
- `HALT`: STOP the slice. Commit the probe as-is, report BLOCKED with the printed table — the human decides whether B5 slice 1 ends with a written finding (per spec §3b this is a designed, acceptable outcome).

- [ ] **Step 4: Commit (include the verdict + key numbers in the commit body)**

```bash
cd <repo>
git add mcp_harness/probe_pose_sensitivity.py
git commit -m "probe(b5): theta/d sensitivity gate on star-4 -- <VERDICT> (noise <N>, min theta sig <T>, min d sig <D>)"
```

---

### Task 4: `probe_pose_recovery.py` — the deliverable recovery run

**Files:**
- Create: `mcp_harness/probe_pose_recovery.py`

**Interfaces:**
- Consumes: `pose_search.chamfer/grid_search/refine/PoseSearchError`; `sim_capture.SimSession/check_capture/build_star4_shaped/CaptureError`; Task 3's printed output (for bounds/target choice).
- Produces: printed target params, full 5×5 objective landscape, refine landscape, and a `RECOVERY PASS/FAIL` verdict; incremental JSONL log `mcp_harness/probe_pose_recovery.out.jsonl` (one line per eval, written as it goes — the run is ~25 min, the log is how progress is monitored).

**Measure-then-pin:** the constants block below holds DEFAULTS. Before running, adjust them per Task 3's measurements and record the choice in the file's docstring: `(θ*, f*)` must lie strictly INSIDE a grid cell (off-grid, so refine is meaningful); if Task 3 said `PROCEED-WIDENED-THETA`, the θ success criterion switches from cell-containment to the widened tolerance stated in the docstring, while f stays strict.

- [ ] **Step 1: Write the probe**

```python
"""B5 slice-1 deliverable (spec 3c): recover a self-generated target pose
(theta*, d*) on star-4 by cold chamfer grid search + one refine pass.

Protocol:
  1. Build + capture the TARGET at (THETA_STAR, FRAC_STAR). A failed target
     capture ABORTS (no target, no run).
  2. 5x5 grid over (theta, fraction): each eval = build shaped fold (pure
     Python) -> sim capture -> chamfer vs target. Failures score inf.
  3. One refine pass around the argmin.
  4. PASS iff the grid argmin lands in the cell containing the target
     (|argmin_theta - theta*| <= theta grid spacing AND |argmin_f - f*| <=
     f spacing) and the refined estimate improves on the argmin score.
     (Refined-estimate tolerance is pinned AFTER reading the printed
     landscape -- record it in the Task 6 handoff, not here.)

CONSTANTS BELOW ARE DEFAULTS -- adjust from probe_pose_sensitivity output
before running (measure-then-pin) and record the choice here:
  <one line: chosen bounds/target and the sensitivity numbers behind them>

Run (~50 captures x ~25 s ~ 20-25 min -- run in background, tail the jsonl):
  cd mcp_harness && nohup .venv/bin/python probe_pose_recovery.py \
      > probe_pose_recovery.log 2>&1 &
  tail -f probe_pose_recovery.out.jsonl
"""
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pose_search                  # noqa: E402
import sim_capture                  # noqa: E402

THETAS = [60.0, 87.5, 115.0, 142.5, 170.0]      # 5 values, spacing 27.5
FRACTIONS = [0.2, 0.35, 0.5, 0.65, 0.8]         # 5 values, spacing 0.15
THETA_STAR = 100.0                               # inside the 87.5..115 cell
FRAC_STAR = 0.45                                 # inside the 0.35..0.5 cell
WIDENED_THETA_TOL = None    # set to a float iff Task 3 said WIDENED-THETA
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "probe_pose_recovery.out.jsonl")


def main() -> int:
    log = open(OUT, "w")

    def record(kind, **kw):
        log.write(json.dumps({"kind": kind, **kw}) + "\n")
        log.flush()

    with sim_capture.SimSession() as sim:
        try:
            target_fold = sim_capture.build_star4_shaped(THETA_STAR, FRAC_STAR)
            target, tdisp = sim_capture.check_capture(sim.capture(target_fold))
        except sim_capture.CaptureError as exc:
            print(f"TARGET CAPTURE FAILED -- ABORT: {exc}")
            record("abort", reason=str(exc))
            return 2
        print(f"target ({THETA_STAR}, {FRAC_STAR}): {len(target)} verts, "
              f"maxDisp {tdisp:.4f}")
        record("target", theta=THETA_STAR, fraction=FRAC_STAR, disp=tdisp)

        def evaluate(params):
            theta, frac = params
            try:
                fold = sim_capture.build_star4_shaped(theta, frac)
                V, disp = sim_capture.check_capture(sim.capture(fold))
                score = pose_search.chamfer(V, target)
                record("eval", theta=theta, fraction=frac, disp=disp,
                       score=score)
                print(f"  eval ({theta}, {frac}): chamfer {score:.6f}")
                return score
            except sim_capture.CaptureError as exc:
                record("eval", theta=theta, fraction=frac,
                       score=None, error=str(exc))
                print(f"  eval ({theta}, {frac}): FAILED ({exc})")
                raise            # grid_search converts to inf and continues

        coarse = pose_search.grid_search(evaluate, [THETAS, FRACTIONS])
        print(f"\ncoarse argmin {coarse.best_params} "
              f"score {coarse.best_score:.6f}")
        record("coarse", best=list(coarse.best_params),
               score=coarse.best_score)

        fine = pose_search.refine(evaluate, [THETAS, FRACTIONS],
                                  coarse.best_params)
        print(f"refined argmin {fine.best_params} "
              f"score {fine.best_score:.6f}")
        record("fine", best=list(fine.best_params), score=fine.best_score)

    bt, bf = coarse.best_params
    theta_spacing = THETAS[1] - THETAS[0]
    f_spacing = FRACTIONS[1] - FRACTIONS[0]
    if WIDENED_THETA_TOL is not None:
        theta_ok = abs(fine.best_params[0] - THETA_STAR) <= WIDENED_THETA_TOL
        theta_how = f"widened tol {WIDENED_THETA_TOL}"
    else:
        theta_ok = abs(bt - THETA_STAR) <= theta_spacing
        theta_how = f"cell containment (spacing {theta_spacing})"
    f_ok = abs(bf - FRAC_STAR) <= f_spacing
    improved = fine.best_score <= coarse.best_score
    passed = theta_ok and f_ok and improved

    print("\n--- landscape (coarse) ---")
    for params in sorted(coarse.scores):
        s = coarse.scores[params]
        print(f"  {params}: {'inf' if math.isinf(s) else f'{s:.6f}'}")
    print(f"\ntheta_ok={theta_ok} [{theta_how}]  f_ok={f_ok} "
          f"[spacing {f_spacing}]  refine_improved={improved}")
    print(f"RECOVERY {'PASS' if passed else 'FAIL'}")
    record("verdict", passed=passed, theta_ok=theta_ok, f_ok=f_ok,
           improved=improved)
    log.close()
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Pin the constants from Task 3's output**

Read `probe_pose_sensitivity.out.json` / the Task 3 commit body. Adjust `THETAS` bounds to the θ range that showed signal, keep `(THETA_STAR, FRAC_STAR)` strictly inside a cell, set `WIDENED_THETA_TOL` iff the verdict was `PROCEED-WIDENED-THETA`, and replace the docstring's `<one line: ...>` placeholder with the actual choice and the numbers behind it. If the defaults already match the measured signal range, say so in that line instead.

- [ ] **Step 3: Run the recovery probe in the background and monitor**

```bash
cd <repo>/mcp_harness
nohup .venv/bin/python probe_pose_recovery.py > probe_pose_recovery.log 2>&1 &
```

Poll `probe_pose_recovery.out.jsonl` until the `verdict` line appears (~20–25 min).
Expected: `RECOVERY PASS`; the printed landscape should look like a basin around the target cell (hand reasoning: chamfer grows monotonically with parameter distance from the target for a single reverse fold — if the landscape is non-monotonic noise, do NOT trust a lucky argmin; investigate or report the finding honestly as FAIL).

If `RECOVERY FAIL` or the landscape contradicts hand reasoning: do not tweak constants until it passes (that's pin-then-measure). Report the printed landscape and stop for review.

- [ ] **Step 4: Commit (verdict + argmin + target in the commit body)**

```bash
cd <repo>
git add mcp_harness/probe_pose_recovery.py
git commit -m "probe(b5): pose recovery on star-4 -- <PASS/FAIL> (target (<theta*>,<f*>), argmin <...>)"
```

---

### Task 5: `probe_hull_quad.py` — hull-filling quadruped side probe

**Files:**
- Create: `mcp_harness/probe_hull_quad.py`

**Interfaces:**
- Consumes: `server._run_isolated` + `server._worker_compile_and_regions` (compile; returns `{"fold", "locs", ...}`), `square_complete.complete_square`, `linter_server.validate_flat_foldability`, `sim_capture.SimSession/check_capture`. Independent of Tasks 3–4 (needs only Task 2).
- Produces: a printed per-candidate table (corner coverage, squaring no-op?, lint verdict, sim maxDisp) — the **written finding** for the Task 6 handoff. No shipped feature (spec §3d).

**Hypothesis under test:** star-4 folds because its 4 leaves land at the 4 paper corners → leaf hull = square → `complete_square` adds nothing → no flat "F" corner faces pin the sheet. An animal-labeled tree whose legs pin the corners might share this. Candidate family (small, fixed — a probe is a probe, not a search framework):
- `star4-head-h`: star-4 plus a 5th short leaf (head, length h ∈ {0.15, 0.3, 0.5}) on the center node — if the 4 long legs still take the corners, the hull is still the square regardless of where the head's circle lands.
- `spine2-quad`: minimal true quadruped topology — 2-node spine, 2 legs per spine node, head on the front node — at two leg/spine ratios.

- [ ] **Step 1: Write the probe**

```python
"""B5 slice-1 side probe (spec 3d): does a hull-filling QUADRUPED base
exist? star-4 folds in the sim because its leaf hull fills the square
(complete_square is a no-op -> no flat corner faces pin the sheet); the
squared dog/quad relax FLAT. If an animal-labeled tree shares the property,
full B5 (mesh-guided posing of an animal) is unblocked; if none does, the
foldable-animal-base problem needs its own brainstorm. Output = a printed
finding, not a feature.

Per candidate: compile (TreeMaker worker) -> do 4 leaves hit the 4 corners?
-> is complete_square a no-op (vertex+edge counts unchanged)? -> lint
verdict (informational; hull bases lint FAIL-expected) -> sim fold ->
maxDisplacement (the decisive number: > 0.10 means it FOLDS).

Run: cd mcp_harness && .venv/bin/python probe_hull_quad.py
(~7 candidates; sim capture only for those passing the no-op check)
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import linter_server                # noqa: E402
import server                       # noqa: E402
import sim_capture                  # noqa: E402
import square_complete              # noqa: E402

CORNER_TOL = 0.05      # leaf-to-corner distance (paper units) to count a hit


def N(i, parent, length):
    return {"id": i, "parent_id": parent, "length": length}


def candidates():
    for h in (0.15, 0.3, 0.5):
        yield (f"star4-head-{h}",
               [N(0, None, 0)] + [N(i, 0, 1.0) for i in range(1, 5)]
               + [N(5, 0, h)], [])
    for spine, leg in ((0.2, 1.0), (0.4, 0.8)):
        yield (f"spine2-quad-s{spine}-l{leg}",
               [N(0, None, 0), N(1, 0, spine),
                N(2, 0, leg), N(3, 0, leg),          # hind legs
                N(4, 1, leg), N(5, 1, leg),          # front legs
                N(6, 1, leg * 0.5)],                  # head
               [[2, 3], [4, 5]])


def corner_hits(locs, tol=CORNER_TOL):
    corners = [(0, 0), (1, 0), (0, 1), (1, 1)]
    hits = 0
    for cx, cy in corners:
        if any(abs(x - cx) <= tol and abs(y - cy) <= tol
               for _n, x, y in locs):
            hits += 1
    return hits


def main() -> int:
    rows = []
    folded_names = []
    sim = None
    try:
        for name, nodes, pairs in candidates():
            try:
                out = json.loads(server._run_isolated(
                    server._worker_compile_and_regions, json.dumps(nodes),
                    [list(p) for p in pairs], 1.0, 1.0))
            except Exception as exc:
                rows.append((name, f"compile failed: {exc}"))
                continue
            fold = out["fold"]
            if isinstance(fold, str):
                fold = json.loads(fold)
            hits = corner_hits(out.get("locs", []))
            sq = square_complete.complete_square(fold, 1.0, 1.0)
            noop = (len(sq["vertices_coords"]) == len(fold["vertices_coords"])
                    and len(sq["edges_vertices"]) == len(fold["edges_vertices"]))
            lint = linter_server.validate_flat_foldability(
                json.dumps(fold)).splitlines()[0]
            disp = None
            if noop:
                if sim is None:
                    sim = sim_capture.SimSession()
                try:
                    _V, disp = sim_capture.check_capture(sim.capture(sq))
                    folded_names.append(name)   # check_capture => disp >= gate
                except sim_capture.CaptureError as exc:
                    disp = f"capture failed: {exc}"
            rows.append((name, f"corners {hits}/4, squaring "
                         f"{'NO-OP' if noop else 'ADDS GEOMETRY'}, "
                         f"lint[{lint}], maxDisp={disp}"))
            print(f"{name}: {rows[-1][1]}")
    finally:
        if sim is not None:
            sim.close()

    print("\n--- FINDING ---")
    for name, desc in rows:
        print(f"  {name}: {desc}")
    print(f"hull-filling candidates that FOLD: {folded_names or 'NONE'}"
          " -> full B5 "
          f"{'UNBLOCKED (cheap direction works)' if folded_names else 'still gated'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run it and hand-check the geometry claims**

Run: `cd mcp_harness && .venv/bin/python probe_hull_quad.py` (~5–10 min: 7 compiles, sim captures only for no-op candidates).
Hand-reasoning checks before trusting the output:
- star-4 itself gets `corners 4/4` and `NO-OP` (it is the control — if the family's `star4-head-*` rows report corners < 4, print the actual `locs` and reason about where the packer put the head circle before concluding);
- a candidate reported `NO-OP` must also report `corners 4/4` (a filled hull with an unfilled corner is contradictory — investigate if seen);
- lint verdicts are informational only (hull bases FAIL-lint by design — the decisive column is maxDisp).

- [ ] **Step 3: Commit (finding summary in the commit body)**

```bash
cd <repo>
git add mcp_harness/probe_hull_quad.py
git commit -m "probe(b5): hull-filling quadruped -- <N>/7 candidates fold (full B5 <unblocked/still gated>)"
```

---

### Task 6: Full suite + handoff write-up

**Files:**
- Create: `docs/superpowers/2026-07-07-handoff-b5-slice1-outcome.md`
- Modify: `docs/superpowers/specs/2026-07-07-b5-pose-search-slice1-design.md` (status banner only)

**Interfaces:**
- Consumes: every prior task's committed probe output (commit bodies + `.out` files still on disk).

- [ ] **Step 1: Run the full backend suite**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests -q` (~10 min; background Bash recommended).
Expected: previous count + the Task 1 tests, 0 failures (401 + 10 = 411 passed / 3 skipped if the count hasn't drifted). If anything unrelated fails, STOP and report.

- [ ] **Step 2: Write the handoff**

Create `docs/superpowers/2026-07-07-handoff-b5-slice1-outcome.md` recording, with the MEASURED numbers from the probe runs (never invented):

```markdown
# Handoff: B5 slice 1 (pose-search recovery) — outcome

**Spec:** docs/superpowers/specs/2026-07-07-b5-pose-search-slice1-design.md

## What shipped
- pose_search.py (chamfer + grid/refine, pure, N pytest tests)
- sim_capture.py Playwright driver (anchor: measured maxDisp <value> vs
  recorded 1.3109; headless=<what was measured>)
- Probes: sensitivity (verdict <V>, noise <n>, min theta signal <t>, min d
  signal <d>), recovery (<PASS/FAIL>, target (<theta*>,<f*>), coarse argmin
  <cell>, refined <params>, landscape summary), hull-quad (<table summary>).

## The two findings that gate what happens next
1. **Recovery:** <one paragraph: did the loop close? with what tolerance?>
2. **Hull-quad:** <one paragraph: does a foldable animal base exist? which
   candidate? or: all candidates pinned flat / hull never filled -> the
   foldable-animal-base problem needs its own brainstorm before full B5.>

## Slice 2 entry point
<Joint-angle fit vs the mesh_to_tree skeleton IF hull-quad unblocked full
B5; otherwise the animal-base brainstorm is the prerequisite. State which,
based on finding 2.>

## Gotchas carried forward
- playwright lives in mcp_harness/.venv ONLY (never in requirements/CI pins).
- <any driver findings: headless vs headed, settle time adequacy, capture
  noise floor for future probes>
```

Replace every `<...>` with measured values/prose — a handoff with a surviving `<placeholder>` is not done.

- [ ] **Step 3: Update the spec status banner**

In `docs/superpowers/specs/2026-07-07-b5-pose-search-slice1-design.md`, change the `**Status:**` line to reflect the outcome, e.g. `**Status:** Implemented 2026-07-07 — recovery <PASS/FAIL>, hull-quad <finding>; see 2026-07-07-handoff-b5-slice1-outcome.md.`

- [ ] **Step 4: Commit**

```bash
cd <repo>
git add docs/superpowers/2026-07-07-handoff-b5-slice1-outcome.md docs/superpowers/specs/2026-07-07-b5-pose-search-slice1-design.md
git commit -m "docs(b5): slice-1 outcome handoff + spec status banner"
```

---

## Execution notes for the controller

- Tasks must run in order 1 → 2 → 3 → 4; Task 5 needs only Task 2 and may run after 4 (never in parallel with another implementer). Task 6 is last.
- Task 2 Step 3, Task 3 Step 3, and Task 4 Step 3 are **decision gates**: a BLOCKED/HALT/FAIL there stops the slice for human review instead of proceeding. That is a designed outcome, not an error.
- Long-running probe/suite commands: use background execution and poll the log/JSONL; foreground Bash times out at 10 min.
- Do not push or open a PR without explicit user approval (finishing-a-development-branch gate).
