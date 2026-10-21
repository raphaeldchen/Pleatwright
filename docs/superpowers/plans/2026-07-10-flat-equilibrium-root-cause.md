# Flat-Equilibrium Root Cause (Pillar B Capstone) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Diagnose why TreeMaker-compiled bases (dog, quad) sit at exactly-0.0 displacement in the vendored Origami Simulator, fix it at the bridge/data layer so the SERVED display dog folds (maxDisplacement > 0.1, 0 NaN), and measure the first real joint angles + one actuation datum on a compiled base.

**Architecture:** Instrument-first diagnosis: a new `sim_instrument` module classifies each frozen base into IMPORT-DEAD / ACTUATION-DEAD / SOLVER-PARKED / PHYSICS-PINNED using an error-channel listener, crease-build audit, and displacement time-series — all Playwright-side, zero vendored edits. A pure-python `fold_mutate` library then bisects the fold one mutation at a time (menu selected by the measured class); the smallest unfreezing mutation is promoted to the display path (`square_complete.py`/`web/server.py`) or `ide-bridge.js`, with an env-gated sim regression test.

**Tech Stack:** Python 3 (numpy, stdlib), Playwright (mcp_harness/.venv ONLY), pytest, the vendored Origami Simulator (read-only except ide-bridge.js), FOLD-format dicts.

**Spec:** `docs/superpowers/specs/2026-07-10-flat-equilibrium-root-cause-design.md` — read it before starting any task.

## Global Constraints

- Branch `feat/flat-eq-root-cause` off main `9bf8111`. Human merges the PR — ask before push/PR.
- Success bar: the SERVED display dog (`shaping.apply_display_ops(square_complete.complete_square(raw, 1.0, 1.0), [], raw=raw)`) folds: maxDisplacement > 0.1, 0 NaN.
- Fix reach: `ide-bridge.js` (mirrored public↔dist) + data layer only. NO edits to any other file under `simulator/js/`. If only a vendored-core change can work → HALT with measured verdict.
- SimSession is HEADED (never set PW_HEADLESS=1 for real runs); playwright lives in `mcp_harness/.venv` only; probes run via `cd mcp_harness && nohup .venv/bin/python <probe>.py > <probe>.out.log 2>&1 &` from subagent shells, controller polls the log.
- Probe outputs (`*.out.json`/`*.out.jsonl`/`*.out.log`) and suite logs stay UNCOMMITTED. SDD ledger `.superpowers/sdd/progress.md` stays uncommitted.
- Anti-vacuous: every "it folded" assertion requires maxDisplacement > 0.10. No 0.0 tolerances anywhere; strict-< gates need margin ≫ 0.1 (measured drift: per-capture ~1e-5–0.02°, derived quantities up to ~0.0934).
- Measure-then-pin: no pinned constant that wasn't printed and hand-checked (the motion noise floor, weld tolerance, etc. get pinned from Gate-0 output, not invented).
- Full backend suite (~10 min, 442 passed / 3 skipped at branch time) must stay green; suite runs use the repo's normal test venv, NOT mcp_harness/.venv.
- Every commit message ends with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- Fable-5 execution sizing: one task package = one gate / one coherent investigation; systematic-debugging discipline (hypothesis → probe → measured verdict in the ledger) INSIDE each package.

## Checkpoint protocol (controller, between task packages)

- **Checkpoint A (after Task 2):** read the Gate-0 verdict table. If dog-served FOLDS → stale lore → stop, write the re-scope note in the ledger, report to the user before continuing. Otherwise name the mechanism class for dog-served (and quad-squared) and select the Task-3/4 mutation menu for that class.
- **Checkpoint B (after Task 4):** root cause named with both-directions evidence (or quad-as-second-witness). Select the Gate-2 fix layer per §6 of the spec. If no bridge/data-layer mutation unfroze the dog → HALT: skip Tasks 5–6, go to Task 7 with the measured verdict.
- **Checkpoint C (after Task 5):** regression green (opt-in sim test PASS + suite green) → proceed to Task 6; else back to B with the new data.

---

### Task 0: Ledger seed + dog golden promotion

**Files:**
- Create: `.superpowers/sdd/progress.md` (uncommitted ledger)
- Create: `mcp_harness/tests/goldens/dog.fold` (committed fixture, copied from untracked `docs/dog.fold`)

**Interfaces:**
- Produces: `mcp_harness/tests/goldens/dog.fold` — the canonical dog fixture every later task loads (35 vertices, 62 edges, assignments M13/V25/F4/B20, no `edges_foldAngle`, no `faces_vertices`).

- [ ] **Step 1: Verify branch and base commit**

Run: `git branch --show-current && git merge-base HEAD origin/main | head -c 7`
Expected: `feat/flat-eq-root-cause` and `9bf8111`.

- [ ] **Step 2: Seed the ledger**

Write `.superpowers/sdd/progress.md`:

```markdown
# SDD ledger — flat-equilibrium root cause (feat/flat-eq-root-cause)
Spec: docs/superpowers/specs/2026-07-10-flat-equilibrium-root-cause-design.md
Plan: docs/superpowers/plans/2026-07-10-flat-equilibrium-root-cause.md

| task | status | verdict / notes |
|---|---|---|
| 0 ledger+golden | in_progress | |
```

- [ ] **Step 3: Promote the dog fixture**

Run: `cp docs/dog.fold mcp_harness/tests/goldens/dog.fold && cmp docs/dog.fold mcp_harness/tests/goldens/dog.fold && echo IDENTICAL`
Expected: `IDENTICAL`.

- [ ] **Step 4: Sanity-check the fixture content**

Run: `python3 -c "
import json; f=json.load(open('mcp_harness/tests/goldens/dog.fold'))
h={}
for a in f['edges_assignment']: h[a]=h.get(a,0)+1
print(len(f['vertices_coords']), len(f['edges_vertices']), h, 'edges_foldAngle' in f, 'faces_vertices' in f)"`
Expected: `35 62 {'M': 13, 'V': 25, 'F': 4, 'B': 20} False False`

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/tests/goldens/dog.fold
git commit -m "test(flat-eq): promote docs/dog.fold to committed golden (regression fixture)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 1: `sim_instrument.py` — pure analysis functions (TDD) + instrumented capture

**Files:**
- Create: `mcp_harness/sim_instrument.py`
- Test: `mcp_harness/tests/test_sim_instrument.py` (pure functions only — NO playwright import at module top level anywhere; suite must pass in the playwright-less venv)

**Interfaces:**
- Consumes: `sim_capture.SimSession` (page at `self._page`, URL at `self._url`), `sim_capture.CaptureError`.
- Produces (later tasks call these exactly):
  - `wing_fold_angle(V, tri1, tri2, a, b) -> float` — unsigned fold angle in degrees, 0 = flat, 180 = fully folded. `V` is an (N,3) float array; `tri1`/`tri2` are 3-tuples of vertex indices sharing edge `(a, b)`.
  - `edge_fold_angles(fold, cap) -> dict[int, float | None]` — input M/V edge index → achieved fold angle from the capture (None if the edge's two triangles can't be found in `cap["faces_vertices"]`).
  - `dropped_creases(fold, crease_params) -> dict` — `{"dropped_mv": [edge indices], "dropped_f": [...], "built": int, "expected_mv": int}`; `crease_params` is the raw list returned by the sim's `setFoldData(fold, true, true)` (each row `[face1, vert1, face2, vert2, edgeInd, angle]`; rows with `edgeInd >= len(fold["edges_vertices"])` are the sim's own triangulation edges and are ignored).
  - `face_quality(cap) -> dict` — `{"min_tri_area": float, "n_tris": int}` computed on `cap["flat_coords"]` normalized by bbox-diagonal².
  - `classify(load_errors, vertex_parity, dropped_mv, motion, final_disp, motion_floor, disp_gate=0.10) -> tuple[str, list[str]]` — class name + evidence flags. `motion` is `[(t_seconds, max_disp), ...]`.
  - `instrumented_capture(sim, fold, sample_times=(1.0, 5.0, 20.0), ramp=None) -> dict` — playwright-side; returns `{"cap": <final capture>, "motion": [(t, disp)], "load_errors": [str], "console": [str], "crease_params": [...], "vertex_parity": bool}`. `ramp=[(20, 8.0), (50, 8.0), (100, 20.0)]` folds in stages (percent, settle_s); default None = single setFold(100) with reads at `sample_times`.
  - `rest_noise_floor(sim, fold, settle_s=5.0) -> float` — loads the fold, never calls setFold, reads maxDisplacement at settle: the GPU idle jitter.

- [ ] **Step 1: Write the failing tests (pure functions)**

`mcp_harness/tests/test_sim_instrument.py`:

```python
import numpy as np
import pytest

import sim_instrument as si


def test_wing_fold_angle_flat_is_zero():
    V = np.array([[0, 0, 0], [1, 0, 0], [0.5, 1, 0], [0.5, -1, 0]], float)
    assert si.wing_fold_angle(V, (0, 1, 2), (0, 1, 3), 0, 1) == pytest.approx(0.0, abs=1e-9)


def test_wing_fold_angle_halfway_is_ninety():
    V = np.array([[0, 0, 0], [1, 0, 0], [0.5, 1, 0], [0.5, 0, 1]], float)
    assert si.wing_fold_angle(V, (0, 1, 2), (0, 1, 3), 0, 1) == pytest.approx(90.0, abs=1e-9)


def test_wing_fold_angle_fully_folded_is_180():
    V = np.array([[0, 0, 0], [1, 0, 0], [0.5, 1, 0], [0.5, 1, 1e-12]], float)
    assert si.wing_fold_angle(V, (0, 1, 2), (0, 1, 3), 0, 1) == pytest.approx(180.0, abs=1e-6)


def test_dropped_creases_diffs_against_input():
    fold = {"edges_vertices": [[0, 1], [1, 2], [2, 3], [3, 0]],
            "edges_assignment": ["M", "V", "F", "B"]}
    # sim built a crease for edge 0 only; edge 4 is a sim-added triangulation edge
    params = [[0, 2, 1, 3, 0, -180], [1, 0, 2, 3, 4, 0]]
    out = si.dropped_creases(fold, params)
    assert out == {"dropped_mv": [1], "dropped_f": [2], "built": 1, "expected_mv": 2}


def test_classify_decision_order():
    ok = dict(load_errors=[], vertex_parity=True, dropped_mv=[],
              motion=[(1, 0.0), (5, 0.0), (20, 0.0)], final_disp=0.0,
              motion_floor=1e-4)
    assert si.classify(**ok)[0] == "SOLVER-PARKED"
    assert si.classify(**{**ok, "load_errors": ["boom"]})[0] == "IMPORT-DEAD"
    assert si.classify(**{**ok, "vertex_parity": False})[0] == "IMPORT-DEAD"
    assert si.classify(**{**ok, "dropped_mv": [7]})[0] == "ACTUATION-DEAD"
    assert si.classify(**{**ok, "motion": [(1, 0.05), (5, 0.01), (20, 0.0)]})[0] == "PHYSICS-PINNED"
    assert si.classify(**{**ok, "final_disp": 1.3,
                          "motion": [(1, 0.5), (5, 1.2), (20, 1.3)]})[0] == "FOLDS"
    # FOLDS with dropped creases keeps the evidence flag
    klass, flags = si.classify(**{**ok, "dropped_mv": [7], "final_disp": 1.3,
                                  "motion": [(1, 0.5), (5, 1.2), (20, 1.3)]})
    assert klass == "ACTUATION-DEAD" and any("disp" in f for f in flags)
```

Note the last assertion pins a decision: dropped M/V creases classify as ACTUATION-DEAD even when displacement clears the gate (partial actuation is still a defect); the flags carry the "but it moved" evidence. This is the spec's decision order applied literally.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd mcp_harness && python3 -m pytest tests/test_sim_instrument.py -v` (repo test venv, NOT .venv)
Expected: FAIL — `ModuleNotFoundError: No module named 'sim_instrument'` (or collection error). Confirm the import error is about `sim_instrument`, not playwright.

- [ ] **Step 3: Implement `sim_instrument.py`**

```python
"""Gate-0 instrumentation for the flat-equilibrium root-cause slice.

Pure analysis functions (numpy only) + a playwright-side instrumented
capture. NO playwright import at module level: the pytest suite runs in a
venv without playwright; only SimSession (passed in, already constructed)
touches the browser. See the spec, section 4.
"""
from __future__ import annotations

import math
import time

import numpy as np


# ---------- pure functions (unit-tested) ----------

def wing_fold_angle(V, tri1, tri2, a, b) -> float:
    """Unsigned fold angle at edge (a, b): 0 = flat, 180 = fully folded.

    Winding-independent 'wing' metric: drop each triangle's opposite
    vertex perpendicularly onto the hinge line, measure the angle between
    the two wing vectors (flat sheet -> 180 deg between wings -> fold 0)."""
    V = np.asarray(V, float)
    c1 = next(v for v in tri1 if v not in (a, b))
    c2 = next(v for v in tri2 if v not in (a, b))
    A, B = V[a], V[b]
    e = B - A
    ne = np.linalg.norm(e)
    if ne < 1e-12:
        raise ValueError(f"degenerate hinge ({a},{b})")
    e = e / ne

    def wing(c):
        w = V[c] - A
        w = w - np.dot(w, e) * e
        n = np.linalg.norm(w)
        if n < 1e-12:
            raise ValueError(f"wing vertex {c} on hinge line")
        return w / n

    cosw = float(np.clip(np.dot(wing(c1), wing(c2)), -1.0, 1.0))
    return 180.0 - math.degrees(math.acos(cosw))


def edge_fold_angles(fold, cap) -> dict:
    """Input M/V edge index -> achieved fold angle from the capture
    (None when the edge's two adjacent triangles aren't both present)."""
    V = np.asarray(cap["vertices_coords"], float)
    tri_of_pair: dict = {}
    for tri in cap["faces_vertices"]:
        for i in range(3):
            key = frozenset((tri[i], tri[(i + 1) % 3]))
            tri_of_pair.setdefault(key, []).append(tuple(tri))
    out = {}
    for ei, ((a, b), asn) in enumerate(
            zip(fold["edges_vertices"], fold["edges_assignment"])):
        if asn not in ("M", "V"):
            continue
        tris = tri_of_pair.get(frozenset((a, b)), [])
        if len(tris) != 2:
            out[ei] = None
            continue
        out[ei] = wing_fold_angle(V, tris[0], tris[1], a, b)
    return out


def dropped_creases(fold, crease_params) -> dict:
    n_in = len(fold["edges_vertices"])
    built = {int(row[4]) for row in crease_params if int(row[4]) < n_in}
    mv = [i for i, a in enumerate(fold["edges_assignment"]) if a in ("M", "V")]
    ff = [i for i, a in enumerate(fold["edges_assignment"]) if a == "F"]
    return {"dropped_mv": [i for i in mv if i not in built],
            "dropped_f": [i for i in ff if i not in built],
            "built": len(built), "expected_mv": len(mv)}


def face_quality(cap) -> dict:
    F = np.asarray(cap["flat_coords"], float)
    span = float(np.linalg.norm(F.max(axis=0) - F.min(axis=0)))
    areas = []
    for t in cap["faces_vertices"]:
        p, q, r = F[t[0]], F[t[1]], F[t[2]]
        areas.append(0.5 * float(np.linalg.norm(np.cross(q - p, r - p))))
    return {"min_tri_area": (min(areas) / (span * span)) if areas else None,
            "n_tris": len(areas)}


def classify(load_errors, vertex_parity, dropped_mv, motion, final_disp,
             motion_floor, disp_gate=0.10):
    """Spec section-4 decision order. Returns (class, evidence_flags)."""
    flags = []
    if load_errors:
        flags.append(f"load_errors={load_errors[:3]}")
    if not vertex_parity:
        flags.append("vertex_count_mismatch")
    if dropped_mv:
        flags.append(f"dropped_mv={len(dropped_mv)}")
    moved = [(t, d) for t, d in motion if d > motion_floor]
    if moved:
        flags.append(f"first_motion@t={moved[0][0]}s={moved[0][1]:.4g}")
    if final_disp >= disp_gate:
        flags.append(f"final_disp={final_disp:.4f}")
    if load_errors or not vertex_parity:
        return "IMPORT-DEAD", flags
    if dropped_mv:
        return "ACTUATION-DEAD", flags
    if final_disp >= disp_gate:
        return "FOLDS", flags
    if not moved:
        return "SOLVER-PARKED", flags
    return "PHYSICS-PINNED", flags


# ---------- playwright-side (validated by the Task-2 anchor, no unit tests) ----------

_READ_GEOMETRY = """() => new Promise((resolve, reject) => {
    const h = (e) => {
      const d = e.data || {};
      if (d.type === 'foldedGeometry') {
        window.removeEventListener('message', h); resolve(d);
      }
    };
    window.addEventListener('message', h);
    window.postMessage({type:'getFoldedGeometry'}, location.origin);
    setTimeout(() => reject(new Error('getFoldedGeometry timeout')), 10000);
  })"""

_WAIT_READY = ("() => window.globals && window.globals.pattern"
               " && typeof window.globals.pattern.setFoldData === 'function'"
               " && typeof window.globals.setCreasePercent === 'function'")


def _goto_ready(sim):
    page = sim._page
    page.goto(sim._url)
    page.wait_for_function(_WAIT_READY, timeout=30_000)
    return page


def _install_error_recorder(page):
    page.evaluate(
        """() => { window.__ideErrors = [];
             window.addEventListener('message', (e) => {
               const d = e.data || {};
               if (d.type === 'error') window.__ideErrors.push(String(d.message));
             }); }""")


def _max_disp(cap):
    V = np.asarray(cap["vertices_coords"], float)
    F = np.asarray(cap["flat_coords"], float)
    if cap["flat_coords"] is None or len(F) != len(V):
        return float("nan")
    return float(np.linalg.norm(V - F, axis=1).max())


def crease_audit(sim, fold):
    """setFoldData(fold, true, true) computes crease params WITHOUT
    building the model. Runs on a fresh page load and leaves the page
    dirty -- caller must goto again before a physics capture."""
    page = _goto_ready(sim)
    return page.evaluate(
        "fold => window.globals.pattern.setFoldData(fold, true, true)", fold)


def rest_noise_floor(sim, fold, settle_s=5.0):
    page = _goto_ready(sim)
    _install_error_recorder(page)
    page.evaluate("fold => window.postMessage({type:'loadFold', fold},"
                  " location.origin)", fold)
    page.wait_for_timeout(settle_s * 1000)
    return _max_disp(page.evaluate(_READ_GEOMETRY))


def instrumented_capture(sim, fold, sample_times=(1.0, 5.0, 20.0), ramp=None):
    console: list = []
    page = sim._page

    def on_console(msg):
        console.append(f"[{msg.type}] {msg.text}")

    # attach BEFORE the audit: pattern.js warnings during setFoldData are
    # exactly the evidence the audit exists to collect
    page.on("console", on_console)
    try:
        crease_params = crease_audit(sim, fold)
        page = _goto_ready(sim)
        _install_error_recorder(page)
        page.evaluate("fold => window.postMessage({type:'loadFold', fold},"
                      " location.origin)", fold)
        motion = []
        if ramp is None:
            page.evaluate("() => window.postMessage({type:'setFold',"
                          " percent:100}, location.origin)")
            t0, last = time.monotonic(), None
            for t in sample_times:
                page.wait_for_timeout(
                    max(0.0, t - (time.monotonic() - t0)) * 1000)
                last = page.evaluate(_READ_GEOMETRY)
                motion.append((t, _max_disp(last)))
            cap = last
        else:
            elapsed = 0.0
            for percent, settle_s in ramp:
                page.evaluate(
                    "p => window.postMessage({type:'setFold', percent:p},"
                    " location.origin)", percent)
                page.wait_for_timeout(settle_s * 1000)
                elapsed += settle_s
                cap = page.evaluate(_READ_GEOMETRY)
                motion.append((elapsed, _max_disp(cap)))
        load_errors = page.evaluate("() => window.__ideErrors || []")
        parity = len(cap["vertices_coords"]) == len(fold["vertices_coords"])
        return {"cap": cap, "motion": motion, "load_errors": load_errors,
                "console": list(console), "crease_params": crease_params,
                "vertex_parity": parity}
    finally:
        page.remove_listener("console", on_console)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd mcp_harness && python3 -m pytest tests/test_sim_instrument.py -v`
Expected: 5 passed. Also run `python3 -c "import sim_instrument"` in the repo test venv — must import cleanly with no playwright installed.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/sim_instrument.py mcp_harness/tests/test_sim_instrument.py
git commit -m "feat(flat-eq): sim_instrument -- crease audit, wing fold angles, motion time-series, mechanism classifier (Gate-0 instruments)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Gate 0 — `probe_flat_eq_matrix.py`, run the 9-fixture matrix

**Files:**
- Create: `mcp_harness/probe_flat_eq_matrix.py`
- Output (uncommitted): `mcp_harness/probe_flat_eq_matrix.out.json`, `.out.log`

**Interfaces:**
- Consumes: `sim_instrument.*` (Task 1), `sim_capture.SimSession/CaptureError/DISP_GATE`, `square_complete.complete_square`, `shaping.apply_display_ops`, `starhead.winner_base()` (returns object with `.sq` = squared display fold and `.raw`), goldens `dog.fold`, `quad.fold`, `hshape.fold`, `star-4.fold`, `bear-base.fold`.
- Produces: `probe_flat_eq_matrix.out.json` with per-fixture `{class, flags, motion, final_disp, dropped, load_errors, console, angle_deficit_summary, face_quality}` + pinned `motion_floor` — Checkpoint A reads this.

- [ ] **Step 1: Write the probe**

```python
"""Gate-0 probe: instrumented 9-fixture matrix (spec section 4).

Order matters: star-4 runs FIRST to (a) validate the driver against the
recorded anchor band (disp 1.0..1.6 around 1.3109) and (b) pin the motion
noise floor from a rest-state read (loaded, never folded, 5 s settle):
motion_floor = 10 x rest jitter. Every later fixture classifies against
that pinned floor. Run:
  cd mcp_harness && nohup .venv/bin/python probe_flat_eq_matrix.py \
      > probe_flat_eq_matrix.out.log 2>&1 &
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shaping                      # noqa: E402
import sim_capture                  # noqa: E402
import sim_instrument as si         # noqa: E402
import square_complete              # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
GOLDENS = os.path.join(HERE, "tests", "goldens")
OUT = os.path.join(HERE, "probe_flat_eq_matrix.out.json")


def load(name):
    with open(os.path.join(GOLDENS, name)) as fh:
        return json.load(fh)


def served(raw):
    """The web/server.py display path for an unshaped base."""
    sq = square_complete.complete_square(raw, 1.0, 1.0)
    return shaping.apply_display_ops(sq, [], raw=raw)


def fixtures():
    dog, quad, hsh = load("dog.fold"), load("quad.fold"), load("hshape.fold")
    star, bear = load("star-4.fold"), load("bear-base.fold")
    fx = [("star4", served(star)),          # anchor first
          ("dog_served", served(dog)), ("dog_raw", dog),
          ("quad_squared", served(quad)), ("quad_raw", quad),
          ("hshape_squared", served(hsh)), ("hshape_raw", hsh),
          ("bear", bear)]
    try:
        import starhead
        fx.append(("winner_star", starhead.winner_base().sq))
    except Exception as e:                   # compile failure is reportable, not fatal
        print(f"winner_star SKIPPED: {e!r}")
    return fx


def summarize_angles(fold, cap):
    angles = si.edge_fold_angles(fold, cap)
    vals = [v for v in angles.values() if v is not None]
    missing = [k for k, v in angles.items() if v is None]
    return {"n": len(angles), "n_missing_adjacency": len(missing),
            "missing_edges": missing[:20],
            "achieved_max": max(vals) if vals else None,
            "achieved_p50": float(np.percentile(vals, 50)) if vals else None}


def main():
    results, floor = {}, None
    with sim_capture.SimSession() as sim:
        for name, fold in fixtures():
            if floor is None:                       # star-4 rest read, once
                rest = si.rest_noise_floor(sim, fold)
                floor = max(10.0 * rest, 1e-6)
                print(f"rest jitter {rest:.3e} -> motion_floor {floor:.3e}")
            try:
                r = si.instrumented_capture(sim, fold)
            except Exception as e:
                results[name] = {"class": "PROBE-ERROR", "error": repr(e)}
                print(f"{name}: PROBE-ERROR {e!r}")
                continue
            drop = si.dropped_creases(fold, r["crease_params"])
            final = r["motion"][-1][1]
            klass, flags = si.classify(
                r["load_errors"], r["vertex_parity"], drop["dropped_mv"],
                r["motion"], final, floor)
            results[name] = {
                "class": klass, "flags": flags, "motion": r["motion"],
                "final_disp": final, "dropped": drop,
                "load_errors": r["load_errors"], "console": r["console"][:40],
                "angles": summarize_angles(fold, r["cap"]),
                "face_quality": si.face_quality(r["cap"]),
                "verts_in": len(fold["vertices_coords"]),
                "verts_cap": len(r["cap"]["vertices_coords"])}
            print(f"{name}: {klass} disp={final:.4f} "
                  f"droppedMV={len(drop['dropped_mv'])} flags={flags}")
    anchor = results.get("star4", {}).get("final_disp") or 0.0
    anchor_ok = 1.0 <= anchor <= 1.6
    out = {"motion_floor": floor, "anchor_disp": anchor,
           "anchor_ok": anchor_ok, "results": results}
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"anchor {'PASS' if anchor_ok else 'FAIL'} ({anchor:.4f}); "
          f"wrote {OUT}")
    return 0 if anchor_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Launch headed run via nohup, poll the log**

Run: `cd mcp_harness && nohup .venv/bin/python probe_flat_eq_matrix.py > probe_flat_eq_matrix.out.log 2>&1 & echo started`
Poll: `tail -5 mcp_harness/probe_flat_eq_matrix.out.log` every ~60 s. Full run ≈ 9 fixtures × (audit goto + capture 20 s + overhead) ≈ 8–12 min (winner_star adds a TreeMaker compile).
Expected: `anchor PASS (1.3±0.3)`; every fixture printed with a class; exit 0.

- [ ] **Step 3: Hand-check the verdict table**

Read `probe_flat_eq_matrix.out.json`. Verify by hand, and record in the ledger:
- star4 = FOLDS (anchor band 1.0..1.6) — if not, the DRIVER is broken: stop, fix, re-run before trusting anything.
- dog_served / quad_squared classes + the three headline numbers each (final_disp, dropped_mv count, load_errors).
- dog_raw / quad_raw / hshape_raw / hshape_squared / bear / winner_star classes — the never-tested cells now have values.
- The b2/b3 bent-dog puzzle note: does dog_served's angle profile show ANY crease actuating (achieved_max vs 0)?
- If dog_served FOLDS → stale lore → STOP per Checkpoint A.

- [ ] **Step 4: Ledger + commit probe (outputs stay uncommitted)**

```bash
git add mcp_harness/probe_flat_eq_matrix.py
git commit -m "probe(flat-eq): Gate-0 instrumented 9-fixture matrix [measured classes in ledger; outputs uncommitted]

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

Update `.superpowers/sdd/progress.md` with the full verdict table (every fixture, every class, motion_floor, anchor).

**CHECKPOINT A — controller re-plans here** (see Checkpoint protocol above).

---

### Task 3: `fold_mutate.py` — mutation library for the selected menu (TDD)

Implement the transforms for the class named at Checkpoint A, PLUS the three always-cheap controls (`to_3d`, `z_jitter`, percent-ramp comes free from Task 1's `ramp=`). All transforms below are specified with code; the executor implements the subset the checkpoint instruction names (plus controls) and skips the rest — do not implement dead menus.

**Files:**
- Create: `mcp_harness/fold_mutate.py`
- Test: `mcp_harness/tests/test_fold_mutate.py`

**Interfaces:**
- Consumes: FOLD dicts (`vertices_coords` 2D, `edges_vertices`, `edges_assignment`).
- Produces (exact signatures; every function returns a NEW dict, input untouched):
  - `to_3d(fold) -> fold` — coords `[x, y]` → `[x, y, 0.0]` (flips the sim's is2d path; the zero-amplitude control for z_jitter).
  - `z_jitter(fold, amplitude=1e-4, seed=0) -> fold` — coords → `[x, y, z]` with z ~ uniform(±amplitude), deterministic per seed. NOTE: any 3-coord vertex makes the sim take the 3D earcut path — always compare against `to_3d` to separate "kick" from "code path".
  - `interior_faces(fold) -> list[list[int]]` — planar face walk (angle-sorted neighbor rotation, outer face dropped by most-negative signed area), pure python.
  - `pre_triangulate(fold, min_gon=5) -> fold` — every interior face with ≥ min_gon vertices gets fan chords (assignment "F") from a fan apex that sees all other vertices; raises `ValueError` naming the face if no apex works.
  - `weld_short_chords(fold, tol) -> fold` — collapse each run of border-adjacent vertices closer than `tol` along B/F hull chains into the run's first vertex; remap all edges; drop self-loops and duplicate edges (keep first). `tol` is ALWAYS passed explicitly (pinned at Checkpoint A from measured chord stats — never bake a default).

- [ ] **Step 1: Write the failing tests**

```python
import copy
import json
import math
import os

import pytest

import fold_mutate as fm

GOLDENS = os.path.join(os.path.dirname(__file__), "goldens")


def _dog():
    with open(os.path.join(GOLDENS, "dog.fold")) as fh:
        return json.load(fh)


def test_to_3d_appends_zero_z_and_preserves_input():
    fold = _dog()
    before = copy.deepcopy(fold)
    out = fm.to_3d(fold)
    assert fold == before
    assert all(len(p) == 3 and p[2] == 0.0 for p in out["vertices_coords"])


def test_z_jitter_is_deterministic_and_bounded():
    a = fm.z_jitter(_dog(), amplitude=1e-4, seed=7)
    b = fm.z_jitter(_dog(), amplitude=1e-4, seed=7)
    assert a == b
    zs = [p[2] for p in a["vertices_coords"]]
    assert max(abs(z) for z in zs) <= 1e-4 and any(z != 0.0 for z in zs)


def test_interior_faces_euler_count_on_dog():
    faces = fm.interior_faces(_dog())
    # V - E + F = 2 with the outer face -> interior faces = E - V + 1 = 28
    assert len(faces) == 28
    assert all(len(f) >= 3 for f in faces)


def test_pre_triangulate_leaves_only_small_faces():
    out = fm.pre_triangulate(_dog(), min_gon=4)
    faces = fm.interior_faces(out)
    assert max(len(f) for f in faces) <= 3
    # only F edges added, M/V untouched
    dog = _dog()
    n = len(dog["edges_vertices"])
    assert out["edges_vertices"][:n] == dog["edges_vertices"]
    assert out["edges_assignment"][:n] == dog["edges_assignment"]
    assert set(out["edges_assignment"][n:]) == {"F"}


def test_weld_short_chords_removes_short_border_edges():
    dog = _dog()
    out = fm.weld_short_chords(dog, tol=0.012)   # dog hull chains are ~7.9e-3
    def short_border(f):
        V, n = f["vertices_coords"], 0
        for (a, b), asn in zip(f["edges_vertices"], f["edges_assignment"]):
            if asn in ("B", "F") and math.dist(V[a][:2], V[b][:2]) < 0.012:
                n += 1
        return n
    assert short_border(dog) > 0 and short_border(out) == 0
    # no self-loops, no duplicate edges, M/V count preserved
    seen = set()
    for a, b in out["edges_vertices"]:
        assert a != b
        assert frozenset((a, b)) not in seen
        seen.add(frozenset((a, b)))
    for tag in ("M", "V"):
        assert out["edges_assignment"].count(tag) == dog["edges_assignment"].count(tag)
```

- [ ] **Step 2: Run tests, verify failure** — `cd mcp_harness && python3 -m pytest tests/test_fold_mutate.py -v` → ModuleNotFoundError.

- [ ] **Step 3: Implement**

```python
"""Pure-python fold mutations for Gate-1 bisection (spec section 5).
Every function returns a new dict; inputs are never mutated."""
from __future__ import annotations

import copy
import math
import random


def _clone(fold):
    return {k: copy.deepcopy(v) for k, v in fold.items()}


def to_3d(fold):
    out = _clone(fold)
    out["vertices_coords"] = [[float(p[0]), float(p[1]), 0.0]
                              for p in out["vertices_coords"]]
    return out


def z_jitter(fold, amplitude=1e-4, seed=0):
    rng = random.Random(seed)
    out = _clone(fold)
    out["vertices_coords"] = [
        [float(p[0]), float(p[1]), rng.uniform(-amplitude, amplitude)]
        for p in out["vertices_coords"]]
    return out


def interior_faces(fold):
    """Angle-sorted half-edge walk; drops the outer face (most-negative
    signed area). Same construction the sim's FOLD library uses."""
    V = [(float(p[0]), float(p[1])) for p in fold["vertices_coords"]]
    nbr = {i: [] for i in range(len(V))}
    for a, b in fold["edges_vertices"]:
        nbr[a].append(b)
        nbr[b].append(a)
    for v in nbr:
        nbr[v].sort(key=lambda u: math.atan2(V[u][1] - V[v][1],
                                             V[u][0] - V[v][0]))
    visited, faces = set(), []
    for v0 in nbr:
        for u0 in nbr[v0]:
            if (v0, u0) in visited:
                continue
            face, (v, u) = [], (v0, u0)
            while (v, u) not in visited:
                visited.add((v, u))
                face.append(v)
                # next half-edge: arrive at u from v, take the neighbor
                # clockwise-next after the reverse direction
                ring = nbr[u]
                i = ring.index(v)
                w = ring[(i - 1) % len(ring)]
                v, u = u, w
            faces.append(face)
    def area(f):
        s = 0.0
        for i in range(len(f)):
            x1, y1 = V[f[i]]
            x2, y2 = V[f[(i + 1) % len(f)]]
            s += x1 * y2 - x2 * y1
        return s / 2.0
    # outer face = the one whose |area| equals the hull area, always the
    # max (walk-direction-independent, unlike a signed-area sort)
    outer = max(range(len(faces)), key=lambda i: abs(area(faces[i])))
    return [f for i, f in enumerate(faces) if i != outer]


def _sees_all(V, face, apex_i):
    """Fan apex validity: every fan diagonal must stay inside the face
    (no crossing with any face boundary segment)."""
    def seg_cross(p, q, r, s):
        def orient(a, b, c):
            return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
        d1, d2 = orient(p, q, r), orient(p, q, s)
        d3, d4 = orient(r, s, p), orient(r, s, q)
        return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))
    n = len(face)
    apex = V[face[apex_i]]
    for k in range(n):
        if k in (apex_i, (apex_i - 1) % n, (apex_i + 1) % n):
            continue
        diag = (apex, V[face[k]])
        for j in range(n):
            a, b = V[face[j]], V[face[(j + 1) % n]]
            if face[j] in (face[apex_i], face[k]) or \
               face[(j + 1) % n] in (face[apex_i], face[k]):
                continue
            if seg_cross(diag[0], diag[1], a, b):
                return False
    return True


def pre_triangulate(fold, min_gon=5):
    out = _clone(fold)
    V = [(float(p[0]), float(p[1])) for p in out["vertices_coords"]]
    existing = {frozenset(e) for e in out["edges_vertices"]}
    for face in interior_faces(fold):
        if len(face) < min_gon:
            continue
        apex_i = next((i for i in range(len(face)) if _sees_all(V, face, i)),
                      None)
        if apex_i is None:
            raise ValueError(f"no valid fan apex for face {face}")
        apex = face[apex_i]
        for k in range(len(face)):
            if k in (apex_i, (apex_i - 1) % len(face),
                     (apex_i + 1) % len(face)):
                continue
            fs = frozenset((apex, face[k]))
            if fs in existing:
                continue
            out["edges_vertices"].append([apex, face[k]])
            out["edges_assignment"].append("F")
            if "edges_foldAngle" in out:
                out["edges_foldAngle"].append(0)
            existing.add(fs)
    return out


def weld_short_chords(fold, tol):
    V = [(float(p[0]), float(p[1])) for p in fold["vertices_coords"]]
    parent = list(range(len(V)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for (a, b), asn in zip(fold["edges_vertices"], fold["edges_assignment"]):
        if asn in ("B", "F") and math.dist(V[a], V[b]) < tol:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[max(ra, rb)] = min(ra, rb)   # keep lowest index
    reps = sorted({find(i) for i in range(len(V))})
    new_id = {r: i for i, r in enumerate(reps)}
    out = _clone(fold)
    out["vertices_coords"] = [fold["vertices_coords"][r] for r in reps]
    ev, ea, fa = [], [], []
    seen = set()
    for i, (a, b) in enumerate(fold["edges_vertices"]):
        na, nb = new_id[find(a)], new_id[find(b)]
        if na == nb:
            continue
        fs = frozenset((na, nb))
        if fs in seen:
            continue
        seen.add(fs)
        ev.append([na, nb])
        ea.append(fold["edges_assignment"][i])
        if "edges_foldAngle" in fold:
            fa.append(fold["edges_foldAngle"][i])
    out["edges_vertices"], out["edges_assignment"] = ev, ea
    if "edges_foldAngle" in fold:
        out["edges_foldAngle"] = fa
    return out
```

- [ ] **Step 4: Run tests, verify pass** — `cd mcp_harness && python3 -m pytest tests/test_fold_mutate.py -v` → all pass. The dog must yield exactly 28 interior faces (Euler: E − V + 1 = 62 − 35 + 1); do not weaken the assertion — a count mismatch means the face walk is wrong, not the fixture.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/fold_mutate.py mcp_harness/tests/test_fold_mutate.py
git commit -m "feat(flat-eq): fold_mutate -- Gate-1 mutation library (to_3d/z_jitter controls + <selected menu>)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Gate 1 — `probe_flat_eq_bisect.py`, mutation ladder + second witness

**Files:**
- Create: `mcp_harness/probe_flat_eq_bisect.py`
- Output (uncommitted): `mcp_harness/probe_flat_eq_bisect.out.json`, `.out.log`

**Interfaces:**
- Consumes: `fold_mutate.*`, `sim_instrument.instrumented_capture/classify`, `sim_capture.SimSession`, the Checkpoint-A menu order, `motion_floor` from `probe_flat_eq_matrix.out.json`.
- Produces: per-mutation verdict rows `{mutation, params, class, final_disp, dropped_mv}` for dog-served AND (same winning mutation) quad-squared; Checkpoint B reads this.

- [ ] **Step 1: Write the driver**

```python
"""Gate-1 bisection: apply ONE mutation at a time to the frozen base,
capture, classify. The LADDER list is edited at Checkpoint A to the menu
the Gate-0 class selects (spec section 5) -- rungs are (name, callable)
pairs over the SERVED dog fold. The winning rung re-runs on quad_squared
(second witness). Run:
  cd mcp_harness && nohup .venv/bin/python probe_flat_eq_bisect.py \
      > probe_flat_eq_bisect.out.log 2>&1 &
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fold_mutate as fm            # noqa: E402
import shaping                      # noqa: E402
import sim_capture                  # noqa: E402
import sim_instrument as si         # noqa: E402
import square_complete              # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
GOLDENS = os.path.join(HERE, "tests", "goldens")
OUT = os.path.join(HERE, "probe_flat_eq_bisect.out.json")
MATRIX = os.path.join(HERE, "probe_flat_eq_matrix.out.json")


def load(name):
    with open(os.path.join(GOLDENS, name)) as fh:
        return json.load(fh)


def served(raw):
    sq = square_complete.complete_square(raw, 1.0, 1.0)
    return shaping.apply_display_ops(sq, [], raw=raw)


# ---- EDITED AT CHECKPOINT A: rungs for the selected menu, cheapest first.
# Every rung is (name, transform(fold)->fold, ramp_or_None).
# Controls first (they separate code-path effects from geometry effects):
LADDER = [
    ("to_3d_control", fm.to_3d, None),
    ("z_jitter_1e-4", lambda f: fm.z_jitter(f, amplitude=1e-4, seed=0), None),
    ("percent_ramp", lambda f: f, [(20, 8.0), (50, 8.0), (100, 20.0)]),
    # <menu rungs inserted here at Checkpoint A, e.g.:
    #  ("pre_triangulate", fm.pre_triangulate, None),
    #  ("weld_<tol>", lambda f: fm.weld_short_chords(f, tol=<PINNED>), None),
    #  ("raw_no_frame", None, None),   # None transform = use the RAW dog
]


def run_one(sim, name, fold, ramp, floor):
    r = si.instrumented_capture(sim, fold, ramp=ramp)
    drop = si.dropped_creases(fold, r["crease_params"])
    final = r["motion"][-1][1]
    klass, flags = si.classify(r["load_errors"], r["vertex_parity"],
                               drop["dropped_mv"], r["motion"], final, floor)
    row = {"mutation": name, "class": klass, "final_disp": final,
           "dropped_mv": len(drop["dropped_mv"]), "flags": flags,
           "motion": r["motion"]}
    print(json.dumps(row))
    return row


def main():
    floor = json.load(open(MATRIX))["motion_floor"]
    dog_raw = load("dog.fold")
    quad_raw = load("quad.fold")
    rows, winner = [], None
    with sim_capture.SimSession() as sim:
        base = run_one(sim, "baseline_served", served(dog_raw), None, floor)
        rows.append(base)
        for name, transform, ramp in LADDER:
            fold = dog_raw if transform is None else transform(served(dog_raw))
            row = run_one(sim, name, fold, ramp, floor)
            rows.append(row)
            if winner is None and row["class"] == "FOLDS" \
                    and row["dropped_mv"] == 0:
                winner = (name, transform, ramp)
        if winner is not None:
            name, transform, ramp = winner
            fold = quad_raw if transform is None else transform(served(quad_raw))
            rows.append({"witness": True,
                         **run_one(sim, f"quad+{name}", fold, ramp, floor)})
    with open(OUT, "w") as fh:
        json.dump({"rows": rows,
                   "winner": winner[0] if winner else None}, fh, indent=1)
    print(f"winner: {winner[0] if winner else 'NONE (all rungs frozen)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Edit LADDER per Checkpoint A** — insert the selected menu's rungs (the commented examples show the shape); pin any tolerance from measured Gate-0 stats and record the pinned value in the ledger. The baseline row re-establishes the frozen state in the same session (guards against environment drift).

- [ ] **Step 3: Launch via nohup, poll** — same pattern as Task 2. Expected: baseline reproduces the Gate-0 class; each rung prints a verdict row; ideally some rung prints `class=FOLDS`.

- [ ] **Step 4: Hand-check + reverse direction** — record in the ledger: smallest winning rung, its disp, quad-witness result. If the controller can design an inverse injection for star-4/winner (pathology is injectable), add it as one more LADDER rung on the mover and re-run; otherwise the quad witness stands (spec allows this substitution).

- [ ] **Step 5: Commit the probe (outputs uncommitted)**

```bash
git add mcp_harness/probe_flat_eq_bisect.py
git commit -m "probe(flat-eq): Gate-1 mutation ladder -- <winning mutation / NONE> [measured rows in ledger]

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

**CHECKPOINT B — controller names the root cause + fix layer, or HALTs.**

---

### Task 5: Gate 2 — promote the fix + regression

The exact promotion depends on Checkpoint B. Both layer patterns are given; implement the one named. Either way, ALL of the following land: the parity-check hygiene, the env-gated regression test, the unit tests, a green suite.

**Files:**
- Modify (data layer): `mcp_harness/square_complete.py` (add `display_ready`), `web/server.py` (call it at both `complete_square` call sites — lines ~83 and ~155 region)
- OR Modify (bridge layer): `web/frontend/public/simulator/js/ide-bridge.js` + byte-identical copy to `web/frontend/dist/simulator/js/ide-bridge.js`
- Modify: `mcp_harness/sim_capture.py` — `check_capture` gains an optional parity argument
- Create: `mcp_harness/tests/test_display_ready.py` (data-layer case)
- Create: `mcp_harness/tests/test_sim_regression.py`
- Create: `mcp_harness/probe_dog_folds.py`

**Interfaces:**
- Produces: `square_complete.display_ready(fold, paper_w=1.0, paper_h=1.0) -> dict` — the ONE display-path entry point (complete_square + the winning transform); server and regression test both import it (single source of truth).
- Produces: `sim_capture.check_capture(cap, expect_verts=None)` — raises `CaptureError` on vertex-count mismatch when `expect_verts` is given (backward-compatible; existing callers unchanged).

- [ ] **Step 1 (data layer): failing unit test for `display_ready`**

```python
# mcp_harness/tests/test_display_ready.py
import json
import os

import square_complete

GOLDENS = os.path.join(os.path.dirname(__file__), "goldens")


def _dog():
    with open(os.path.join(GOLDENS, "dog.fold")) as fh:
        return json.load(fh)


def test_display_ready_is_idempotent_and_preserves_mv():
    dog = _dog()
    one = square_complete.display_ready(dog, 1.0, 1.0)
    two = square_complete.display_ready(one, 1.0, 1.0)
    assert one == two
    for tag in ("M", "V"):
        assert one["edges_assignment"].count(tag) == dog["edges_assignment"].count(tag)


def test_display_ready_removes_the_measured_pathology():
    # EDIT AT CHECKPOINT B: assert the specific property the root cause
    # named, with the pinned constant from the ledger, e.g. no B/F edge
    # shorter than <PINNED_TOL>, or no interior face above 4 vertices.
    ...
```

The second test's body is written at Checkpoint B against the named root cause — it must assert the measured pathology is absent, with the pinned constant, and must FAIL against plain `complete_square` output (prove it detects).

- [ ] **Step 2: implement `display_ready`**

```python
# appended to mcp_harness/square_complete.py
def display_ready(fold: dict, paper_w: float = 1.0, paper_h: float = 1.0) -> dict:
    """complete_square + the Gate-1-proven transform that makes the result
    actually fold in the vendored sim (root cause + evidence: see
    docs/superpowers/specs/2026-07-10-flat-equilibrium-root-cause-design.md
    and the slice handoff). Display boundary ONLY -- the lint/download
    `json` frame never passes through here."""
    sq = complete_square(fold, paper_w, paper_h)
    return _WINNING_TRANSFORM(sq)        # named function landed from fold_mutate
```

Concretely: copy the winning transform's implementation (or import it — `fold_mutate` is import-clean, stdlib-only) and wire the pinned constant. Update BOTH `web/server.py` call sites to call `display_ready` instead of `complete_square`; run existing server tests.

- [ ] **Step 2-alt (bridge layer):** extend `loadFoldObject` in `ide-bridge.js` with the winning preprocessing before `setFoldData` (plain ES5, matching file style), then `cp web/frontend/public/simulator/js/ide-bridge.js web/frontend/dist/simulator/js/ide-bridge.js` and `diff` to confirm identical. The regression test then exercises it through `SimSession` automatically.

- [ ] **Step 3: parity hygiene in `sim_capture.check_capture`**

```python
def check_capture(cap: dict, expect_verts: int | None = None):
    ...existing checks...
    if expect_verts is not None and len(V) != expect_verts:
        raise CaptureError(
            f"loaded model has {len(V)} vertices, input fold has"
            f" {expect_verts} (stale/failed load)")
```

(Add after the existing `len(F) != len(V)` check; existing callers pass no second arg and are unaffected. Add one unit test alongside the existing suite conventions in `test_sim_instrument.py`: build a fake cap dict, assert the raise.)

- [ ] **Step 4: env-gated regression test + permanent probe**

```python
# mcp_harness/tests/test_sim_regression.py
"""Opt-in sim regression: RUN_SIM_REGRESSION=1 (needs headed chromium and
the mcp_harness/.venv playwright interpreter). The 442-test suite skips it."""
import json
import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_SIM_REGRESSION") != "1",
    reason="RUN_SIM_REGRESSION not set (headed sim required)")


def test_served_dog_folds():
    import sim_capture
    import square_complete
    import shaping
    goldens = os.path.join(os.path.dirname(__file__), "goldens")
    raw = json.load(open(os.path.join(goldens, "dog.fold")))
    served = shaping.apply_display_ops(
        square_complete.display_ready(raw, 1.0, 1.0), [], raw=raw)
    with sim_capture.SimSession() as sim:
        cap = sim.capture(served)
    _, disp = sim_capture.check_capture(
        cap, expect_verts=len(served["vertices_coords"]))
    assert disp > 0.10
```

(Bridge-layer case: `display_ready` doesn't exist — the test uses `complete_square` and the bridge does the work in-page; adjust the one call accordingly at Checkpoint B.)

`mcp_harness/probe_dog_folds.py` — thin permanent probe, same check, printed verdict:

```python
"""Permanent regression probe: does the SERVED dog fold? PASS requires
maxDisplacement > 0.1 and 0 NaN. Quad reported as secondary (not gated).
Run: cd mcp_harness && .venv/bin/python probe_dog_folds.py"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shaping                      # noqa: E402
import sim_capture                  # noqa: E402
import square_complete              # noqa: E402

GOLDENS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "tests", "goldens")


def served(name):
    raw = json.load(open(os.path.join(GOLDENS, name)))
    sq = square_complete.display_ready(raw, 1.0, 1.0)
    return raw, shaping.apply_display_ops(sq, [], raw=raw)


def main():
    with sim_capture.SimSession() as sim:
        raw, dog = served("dog.fold")
        cap = sim.capture(dog)
        _, disp = sim_capture.check_capture(
            cap, expect_verts=len(dog["vertices_coords"]))
        print(f"dog: maxDisplacement {disp:.4f} -> "
              f"{'PASS' if disp > 0.10 else 'FAIL'}")
        ok = disp > 0.10
        try:
            _, quad = served("quad.fold")
            qcap = sim.capture(quad)
            _, qdisp = sim_capture.check_capture(
                qcap, expect_verts=len(quad["vertices_coords"]))
            print(f"quad (secondary, not gated): {qdisp:.4f}")
        except sim_capture.CaptureError as e:
            print(f"quad (secondary, not gated): {e}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: run everything**

- Unit tests: `cd mcp_harness && python3 -m pytest tests/test_display_ready.py tests/test_sim_instrument.py tests/test_fold_mutate.py -v` → pass.
- Sim regression (opt-in, from .venv): `cd mcp_harness && RUN_SIM_REGRESSION=1 .venv/bin/python -m pytest tests/test_sim_regression.py -v` → 1 passed.
- Probe: `cd mcp_harness && .venv/bin/python probe_dog_folds.py` → `dog: ... PASS` (record the measured disp in the ledger; quad's number too).
- FULL suite (repo venv, ~10 min): run the project's standard suite command; expected 442+new passed / 3 skipped, `test_sim_regression` reported as skipped without the env var.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/square_complete.py web/server.py mcp_harness/sim_capture.py \
        mcp_harness/tests/test_display_ready.py mcp_harness/tests/test_sim_regression.py \
        mcp_harness/probe_dog_folds.py
git commit -m "fix(flat-eq): <root cause one-liner> -- served display dog now folds (disp <MEASURED>); parity hygiene + opt-in sim regression

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

(Adjust the file list for the bridge-layer case: both ide-bridge.js copies instead of square_complete/server.)

**CHECKPOINT C — regression green → Task 6; else back to B.**

---

### Task 6: Gate 3 — payoff probe (conditional on Checkpoint C)

**Files:**
- Create: `mcp_harness/probe_dog_pose.py`
- Output (uncommitted): `mcp_harness/probe_dog_pose.out.json`, `.out.log`

**Interfaces:**
- Consumes: the folded served dog (Task-5 entry point), `sim_capture.tracked_points/axial_hub`, `pose_target.fox_targets` machinery via `starhead.fox_targets()` (read `mcp_harness/probe_angle_range.py` FIRST — it prints fox targets front 134.8316 / back 138.6544 / head 137.7186 and contains the exact angle-measurement helper the B5 probes used; REUSE that helper verbatim rather than re-deriving the angle definition, so the dog's numbers are commensurable with the B5 record).
- Produces: `probe_dog_pose.out.json` — candidate tips with folded positions, measurable joint angles + gaps vs fox targets, ambiguity flags, and the single-op actuation delta.

- [ ] **Step 1: Write the probe.** Structure (fill the angle-helper call from probe_angle_range at execution):

```python
"""Gate-3 payoff: first real joint-angle measurement on a compiled base.

1. Fold the served dog, tracked_points on every candidate tip (border
   vertices with exactly one incident M/V edge, 8dp-snapped) + hub(s).
2. Report each measurable joint angle vs starhead.fox_targets() where the
   heuristic grouping can name a group; report AMBIGUOUS where it can't
   (never guess -- the dog has more degree-1 border vertices than tree
   leaves: corner tangent points etc.).
3. ONE actuation datum: reverse fold on the leg tip with the LONGEST
   axial edge, theta=105, d = 0.5 * axial (sim_capture.build_star4_shaped
   pattern); recapture; report the joint-angle delta for that tip.
   theta=90 is guarded (known silent mis-target); never use it.
Informational only -- no gate, no fit, no search."""
```

Candidate-tip finder (concrete):

```python
def candidate_tips(fold):
    V = fold["vertices_coords"]
    border = {v for (a, b), s in zip(fold["edges_vertices"],
              fold["edges_assignment"]) if s == "B" for v in (a, b)}
    deg = {}
    for (a, b), s in zip(fold["edges_vertices"], fold["edges_assignment"]):
        if s in ("M", "V"):
            deg[a] = deg.get(a, 0) + 1
            deg[b] = deg.get(b, 0) + 1
    return sorted(v for v in border if deg.get(v, 0) == 1)
```

The op application mirrors `sim_capture.build_star4_shaped` exactly but over the dog raw + `square_complete.display_ready`; if `shaping.apply_display_ops` refuses the op (`shaped is sq`), print `op refused` and still emit the unshaped measurements (honest partial output).

- [ ] **Step 2: Run via nohup, poll; hand-check output** — every reported angle has a named tip pair + a printed folded position; ambiguity count stated; delta reported with the drift band caveat (±~0.1 for derived quantities).

- [ ] **Step 3: Commit probe; ledger entry with the measured table.**

```bash
git add mcp_harness/probe_dog_pose.py
git commit -m "probe(flat-eq): Gate-3 payoff -- first fox-target comparison + single-op actuation delta on the compiled dog [measured table in ledger]

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: Outcome handoff + spec banner + memory + review

**Files:**
- Create: `docs/superpowers/2026-07-XX-handoff-flat-equilibrium-outcome.md` (date of writing)
- Modify: `docs/superpowers/specs/2026-07-10-flat-equilibrium-root-cause-design.md` (status banner at top: PROCEEDED-to-fix / HALT-at-gate-N, one line, measured numbers)
- Modify: memory `b5-pose-fit-slice4.md`-style new file + `MEMORY.md` line (controller does this, not a subagent)

- [ ] **Step 1: Write the handoff** following the slice-4 outcome handoff's structure exactly (What shipped / Findings per gate with measured numbers / Next-slice entry points cheapest-first / Gotchas carried forward). Every number copied from probe outputs, not from memory of them.
- [ ] **Step 2: Full suite one last time; record count in handoff.**
- [ ] **Step 3: Commit docs.**

```bash
git add docs/superpowers/2026-07-*-handoff-flat-equilibrium-outcome.md docs/superpowers/specs/2026-07-10-flat-equilibrium-root-cause-design.md
git commit -m "docs(flat-eq): outcome handoff + spec status banner [measured verdicts in body]

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

- [ ] **Step 4: Final whole-branch review** on the most capable model (`git diff 9bf8111..HEAD` as the review package), fix findings, re-run suite if code changed.
- [ ] **Step 5: ASK THE USER before any push/PR** (human merges; never push unprompted).

---

## Self-review notes (run once, fixes applied inline)

- Spec coverage: §4 matrix → Task 2 (all 9 fixtures + rest-noise-floor + mover baselines); §4 instruments 1–7 → Task 1 (error recorder, console, parity, audit, time-series, wing angles, face quality); §5 menus + causality → Tasks 3–4 (controls + menu rungs + quad witness + optional inverse injection); §6 fix/regression/golden/parity-hygiene → Task 5 + Task 0; §7 payoff incl. actuation datum → Task 6; §8 constraints → Global Constraints; HALT path → Checkpoint B → Task 7. Stale-lore rule → Checkpoint A.
- The two deliberate execution-time blanks are CHECKPOINT-scoped, not placeholders: LADDER menu rungs (Task 4 Step 2) and `test_display_ready` pathology assertion (Task 5 Step 1) — both are unknowable before Gate-0/1 measurements exist, both carry explicit edit instructions and shape examples, and the checkpoint protocol names who fills them (the controller) from what (the ledger's pinned values).
- Type consistency: `instrumented_capture` return keys match Task-2/4 consumption (`cap/motion/load_errors/console/crease_params/vertex_parity`); `classify` signature identical across Tasks 1/2/4; `display_ready(fold, paper_w, paper_h)` matches Task-5 test and probe usage; `check_capture(cap, expect_verts=None)` matches regression/probe calls.
