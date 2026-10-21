# Projection Metric (P1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic, browser-free instrument that measures anatomy legibility from folded geometry, and establish by pre-registered test whether it actually separates a shaped base from an unshaped one.

**Architecture:** A pure-numpy module (`mcp_harness/projection_metric.py`) projects folded 3-D geometry to a camera's 2-D basis, reduces it to a **polar signature** (max radius per angular bin — no polygon booleans required), and counts protrusions as local maxima above a *derived, not fitted* threshold. A committed fixture of five real captures makes the whole thing testable with no browser. A pre-registered per-view human re-test supplies the ground truth the metric is calibrated against.

**Tech Stack:** Python 3.14, numpy (already a dependency), pytest. **No new dependencies** — see Global Constraints.

## Global Constraints

- **No new Python dependencies.** `mcp_harness/.venv` is a **symlink to the main repo's venv**; installing anything mutates the user's main environment and its CI-pinned deps. numpy is available. matplotlib, scipy, shapely, Pillow are **not** and must not be added.
- **No changes to what is served.** This plan adds an instrument. It must not touch `web/server.py`'s display path, `shaping.py`, or `square_complete.py`.
- **Never touch `mcp_harness/TreemakerWrapper.cpp`** — strictly serial, claimed by Goal 1's S4b₀ (see `docs/superpowers/goals/COORDINATION.md` §2).
- **Do not re-bless `mcp_harness/fixtures/scorecard_baseline.jsonl`.** It is frozen for the duration of Goals 1 and 2. This plan adds no scorecard column.
- **The protrusion threshold `K = 0.35` is PINNED before calibration and must not be tuned to make calibration pass.** A calibration failure is a *result* to report, not a signal to adjust the constant. This is the plan's single most important rule; the repo's recurring failure mode is the vacuous gate.
- Run tests with an explicit timeout — bare `make test` never terminates on this machine: `PYTHONPATH=.:tests .venv/bin/python -m pytest --timeout=420`.
- Commit messages end with:
  `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`

---

## File Structure

| file | responsibility |
|---|---|
| `mcp_harness/fixtures/legibility_captures.json` | **create** — five real folded-geometry captures (2 BASE, 3 SHAPED) from the 2026-08-07 calibration. Makes every downstream test browser-free. |
| `mcp_harness/projection_metric.py` | **create** — the instrument. Camera basis, polar signature, protrusion counting, per-view signature, aggregate score. Pure functions over `(vertices, faces)`. |
| `mcp_harness/tests/test_projection_metric.py` | **create** — unit tests on synthetic shapes with known answers, plus the fixture-shape pins. |
| `mcp_harness/tests/test_projection_metric_calibration.py` | **create** — the three pinned calibration criteria. Separate file because this is a *gate*, not a unit test, and it must be greppable as such. |
| `mcp_harness/probe_perview_retest.py` | **create** — renders per-view blinded pairs for the human re-test. Probe, not an agent tool. |
| `docs/superpowers/evidence/2026-08-08-perview-retest-prereg.md` | **create** — the pre-registration, committed before any per-view image exists. |

---

## Task 1: Commit the capture fixture

**Files:**
- Create: `mcp_harness/fixtures/legibility_captures.json`
- Create: `mcp_harness/tests/test_projection_metric.py`

**Interfaces:**
- Consumes: nothing.
- Produces: the fixture path `mcp_harness/fixtures/legibility_captures.json`, a JSON object `{"source": str, "incumbent_op": str, "captures": [ {"idx": int, "condition": "BASE"|"SHAPED", "maxDisplacement": float, "vertices_coords": [[x,y,z],...], "faces_vertices": [[i,j,k,...],...]} ]}` with exactly 5 entries, 2 BASE and 3 SHAPED.

- [ ] **Step 1: Extract the fixture from the session artifacts**

The five captures were produced on 2026-08-07 and are recorded in the evidence commit. Regenerate the slim fixture from the committed calibration script's output if present; otherwise re-run `docs/superpowers/evidence/2026-08-07-legibility-step1_capture.py` (requires a headed browser, ~4 min).

```bash
cd mcp_harness
.venv/bin/python - <<'PY'
import json, os
src = os.environ.get("CAPTURES_JSON", "captures.json")
d = json.load(open(src))
slim = {
    "source": "2026-08-07 legibility calibration (prereg 5598b12)",
    "incumbent_op": d["incumbent_op"],
    "captures": [
        {k: c[k] for k in ("idx", "condition", "maxDisplacement",
                           "vertices_coords", "faces_vertices")}
        for c in d["captures"] if c["ok"]
    ],
}
os.makedirs("fixtures", exist_ok=True)
json.dump(slim, open("fixtures/legibility_captures.json", "w"))
print(len(slim["captures"]), "captures")
PY
```

Expected: `5 captures`, file ~19 KB.

- [ ] **Step 2: Write the failing fixture-shape test**

```python
# mcp_harness/tests/test_projection_metric.py
import json
import os

import numpy as np
import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(HERE, "fixtures", "legibility_captures.json")


def load_captures():
    with open(FIXTURE) as fh:
        return json.load(fh)["captures"]


def test_fixture_has_the_recorded_five_captures():
    caps = load_captures()
    assert len(caps) == 5
    conds = [c["condition"] for c in caps]
    assert conds.count("BASE") == 2
    assert conds.count("SHAPED") == 3


def test_fixture_displacements_match_the_recorded_run():
    """Pins the actual numbers from the 2026-08-07 run. If these move, the
    fixture was regenerated and every calibration claim needs re-deriving."""
    caps = load_captures()
    base = sorted(round(c["maxDisplacement"], 4)
                  for c in caps if c["condition"] == "BASE")
    shaped = sorted(round(c["maxDisplacement"], 4)
                    for c in caps if c["condition"] == "SHAPED")
    assert base == [1.5908, 1.5950]
    assert shaped == [0.9216, 0.9390, 0.9418]


def test_fixture_geometry_is_well_formed():
    for c in load_captures():
        V = np.asarray(c["vertices_coords"], dtype=float)
        assert V.ndim == 2 and V.shape[1] == 3
        assert np.isfinite(V).all()
        n = len(V)
        for f in c["faces_vertices"]:
            assert len(f) >= 3
            assert all(0 <= i < n for i in f)


def test_shaped_captures_have_more_vertices_than_base():
    """The incumbent op adds a wedge: +3 vertices on a clean tip."""
    caps = load_captures()
    base_n = {len(c["vertices_coords"]) for c in caps if c["condition"] == "BASE"}
    shaped_n = {len(c["vertices_coords"]) for c in caps if c["condition"] == "SHAPED"}
    assert base_n == {39}
    assert shaped_n == {44}
```

- [ ] **Step 3: Run to verify it fails**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_projection_metric.py -v --timeout=420`
Expected: FAIL — `FileNotFoundError` on the fixture, or assertion errors, until Step 1 has been run.

- [ ] **Step 4: Run again after Step 1 to verify it passes**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_projection_metric.py -v --timeout=420`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/fixtures/legibility_captures.json mcp_harness/tests/test_projection_metric.py
git commit -m "fixture(legibility): commit the five 2026-08-07 captures

Makes every downstream projection-metric test browser-free. Pins the
recorded maxDisplacement values so a silent regeneration is caught.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 2: Pre-register and render the per-view re-test

This task ends with a **human checkpoint**. Do not proceed to Task 3 until the judge's answers are recorded, because Task 6's third calibration criterion consumes them.

**Files:**
- Create: `docs/superpowers/evidence/2026-08-08-perview-retest-prereg.md`
- Create: `mcp_harness/probe_perview_retest.py`
- Modify: `mcp_harness/tests/test_projection_metric.py` (add the probe's correctness trap)

**Interfaces:**
- Consumes: `mcp_harness/fixtures/legibility_captures.json` from Task 1.
- Produces: `perview_KEY.json` written next to the rendered SVGs, mapping each presented pair id to `{"A": str, "B": str, "view": int, "is_null": bool}`.

- [ ] **Step 1: Write the pre-registration and commit it BEFORE rendering**

Create `docs/superpowers/evidence/2026-08-08-perview-retest-prereg.md`:

```markdown
# Pre-registration: per-view legibility re-test

**Written before any per-view image exists.** Committed before the renderer runs.

## Question

The 2026-08-07 calibration asked for ONE preference per row across seven views
at once and returned FAIL (k=0/3). Post-hoc, the judge identified leg structure
in panel 6 of 7 (view index 5, elev -25, azim -125) in all three SHAPED
captures and neither BASE capture. A one-camera signal can wash out in a
whole-sheet comparison.

**Question: judged PER VIEW, is the shaped base preferred at any camera?**

## Design

Source: `mcp_harness/fixtures/legibility_captures.json` (2 BASE, 3 SHAPED).
Zero new captures.

For each of the 7 views: one test pair (BASE vs a SHAPED capture) and one null
pair (BASE#1 vs BASE#2) at the SAME camera. 14 pairs total, presented in a
seeded random order with A/B position randomised. The key is withheld until
answers are recorded.

Renders are identical across conditions in every respect except geometry: same
camera, same shared scale computed over the union of all captures, same fixed
Lambert light, same edge weight, no labels.

## Questions asked (fixed wording)

For each pair: *"Which is more dog-like -- A, B, or no difference?"*
Then: *"Name any body parts you can identify in each. If none, say none."*

## Outcome criteria -- PINNED

Let `v` = number of the 7 views where SHAPED is preferred in the test pair.
Let `n` = number of views where a NULL pair draws a confident preference.

| verdict | condition |
|---|---|
| **VOID** | `n >= 3` -- the judge is manufacturing differences; the run is void. |
| **PASS** | `v >= 3` AND `n <= 1` |
| **WEAK PASS** | `v == 2` AND `n == 0` |
| **FAIL** | `v <= 1` |

Anything else is **INCONCLUSIVE**, reported as such, not rounded to a row.

## Declared limitations

- The 7 views are not independent; treat `v` as descriptive, not as 7 trials.
- One subject, one op. No claim generalises beyond this base.
- The judge has already seen these captures and flagged view 5. This is
  therefore a **confirmatory test of a specific pre-stated view**, and view 5's
  result carries less evidential weight than the other six. Stated in advance.
```

```bash
git add docs/superpowers/evidence/2026-08-08-perview-retest-prereg.md
git commit -m "prereg(perview): pin the per-view criterion before rendering

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

- [ ] **Step 2: Write the failing correctness-trap test for the probe**

Probes in this repo carry a correctness trap (precedent: `probe_packing_diagram`). Add to `mcp_harness/tests/test_projection_metric.py`:

```python
def test_perview_probe_pairs_each_view_once_with_a_null():
    """The probe must emit exactly one test pair and one null pair per view,
    and never pair a capture with itself."""
    import probe_perview_retest as P
    caps = load_captures()
    pairs = P.build_pairs(caps, seed=20260808)
    assert len(pairs) == 2 * len(P.VIEWS)
    for view in range(len(P.VIEWS)):
        at_view = [p for p in pairs if p["view"] == view]
        assert len(at_view) == 2
        assert sum(1 for p in at_view if p["is_null"]) == 1
    for p in pairs:
        assert p["left"] is not p["right"]
        if p["is_null"]:
            assert p["left"]["condition"] == p["right"]["condition"] == "BASE"
        else:
            assert {p["left"]["condition"], p["right"]["condition"]} == {"BASE", "SHAPED"}
```

- [ ] **Step 3: Run to verify it fails**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_projection_metric.py::test_perview_probe_pairs_each_view_once_with_a_null -v --timeout=420`
Expected: FAIL with `ModuleNotFoundError: No module named 'probe_perview_retest'`.

- [ ] **Step 4: Write the probe**

Create `mcp_harness/probe_perview_retest.py`:

```python
"""Per-view legibility re-test renderer. PROBE -- not an agent tool.

Renders one test pair (BASE vs SHAPED) and one null pair (BASE vs BASE) per
camera, blinded and order-randomised, from the committed capture fixture.
Zero browser cost. Prereg:
docs/superpowers/evidence/2026-08-08-perview-retest-prereg.md
"""
from __future__ import annotations

import json
import os
import random

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, "fixtures", "legibility_captures.json")

VIEWS = [(90, -90), (0, -90), (0, 0), (25, -55), (25, 35), (-25, -125), (55, 140)]
PANEL = 460
LIGHT = np.array([0.35, -0.55, 0.75])
LIGHT = LIGHT / np.linalg.norm(LIGHT)
EDGE = "#242832"
LW = 0.5


def load_captures(path: str = FIXTURE) -> list:
    with open(path) as fh:
        return json.load(fh)["captures"]


def camera_basis(elev_deg: float, azim_deg: float):
    e, a = np.radians(elev_deg), np.radians(azim_deg)
    cam = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
    f = -cam / np.linalg.norm(cam)
    up = np.array([0.0, 0.0, 1.0])
    if abs(float(np.dot(f, up))) > 0.999:
        up = np.array([0.0, 1.0, 0.0])
    r = np.cross(f, up)
    r = r / np.linalg.norm(r)
    u = np.cross(r, f)
    return r, u, f


def build_pairs(caps: list, seed: int) -> list:
    base = [c for c in caps if c["condition"] == "BASE"]
    shaped = [c for c in caps if c["condition"] == "SHAPED"]
    rng = random.Random(seed)
    pairs = []
    for view in range(len(VIEWS)):
        s = shaped[view % len(shaped)]
        pairs.append({"view": view, "is_null": False,
                      "left": base[0], "right": s})
        pairs.append({"view": view, "is_null": True,
                      "left": base[0], "right": base[1]})
    rng.shuffle(pairs)
    for p in pairs:
        if rng.random() < 0.5:
            p["left"], p["right"] = p["right"], p["left"]
    return pairs


def _newell(pts: np.ndarray) -> np.ndarray:
    n = np.zeros(3)
    m = len(pts)
    for i in range(m):
        a, b = pts[i], pts[(i + 1) % m]
        n[0] += (a[1] - b[1]) * (a[2] + b[2])
        n[1] += (a[2] - b[2]) * (a[0] + b[0])
        n[2] += (a[0] - b[0]) * (a[1] + b[1])
    ln = np.linalg.norm(n)
    return n / ln if ln > 1e-12 else np.array([0.0, 0.0, 1.0])


def _shade(nrm: np.ndarray) -> str:
    c = abs(float(np.dot(nrm, LIGHT)))
    q = int(max(0, min(255, round((0.42 + 0.50 * c) * 255))))
    return f"#{q:02x}{q:02x}{min(255, q + 6):02x}"


def panel_svg(cap: dict, view: int, scale: float, ox: float, oy: float) -> str:
    elev, azim = VIEWS[view]
    V = np.asarray(cap["vertices_coords"], dtype=float)
    V = V - V.mean(axis=0)
    r, u, f = camera_basis(elev, azim)
    P2 = np.stack([V @ r, V @ u], axis=1)
    depth = V @ f
    faces = [np.asarray(fv, dtype=int) for fv in cap["faces_vertices"]]
    order = sorted(range(len(faces)),
                   key=lambda i: -float(depth[faces[i]].mean()))
    cx, cy = ox + PANEL / 2.0, oy + PANEL / 2.0
    out = []
    for i in order:
        idx = faces[i]
        xy = P2[idx]
        sx = cx + xy[:, 0] * scale
        sy = cy - xy[:, 1] * scale
        d = " ".join(f"{x:.2f},{y:.2f}" for x, y in zip(sx, sy))
        out.append(f'<polygon points="{d}" fill="{_shade(_newell(V[idx]))}" '
                   f'stroke="{EDGE}" stroke-width="{LW}" '
                   f'stroke-linejoin="round"/>')
    return "".join(out)


def union_scale(caps: list) -> float:
    m = 0.0
    for c in caps:
        V = np.asarray(c["vertices_coords"], dtype=float)
        V = V - V.mean(axis=0)
        for view in range(len(VIEWS)):
            r, u, _ = camera_basis(*VIEWS[view])
            m = max(m, float(np.abs(V @ r).max()), float(np.abs(V @ u).max()))
    return (PANEL / 2.0 * 0.88) / m


def main(outdir: str = ".", seed: int = 20260808) -> int:
    caps = load_captures()
    pairs = build_pairs(caps, seed)
    scale = union_scale(caps)
    key = {}
    for n, p in enumerate(pairs, start=1):
        pid = f"V{n:02d}"
        W, H = 2 * PANEL, PANEL + 26
        parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" '
                 f'height="{H}" viewBox="0 0 {W} {H}">',
                 f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
                 f'<text x="8" y="18" font-family="sans-serif" font-size="14" '
                 f'fill="#444">Pair {pid}</text>',
                 panel_svg(p["left"], p["view"], scale, 0, 26),
                 panel_svg(p["right"], p["view"], scale, PANEL, 26),
                 f'<text x="10" y="{26 + PANEL - 8}" font-family="sans-serif" '
                 f'font-size="22" font-weight="700" fill="#111">A</text>',
                 f'<text x="{PANEL + 10}" y="{26 + PANEL - 8}" '
                 f'font-family="sans-serif" font-size="22" font-weight="700" '
                 f'fill="#111">B</text>',
                 f'<line x1="{PANEL}" y1="26" x2="{PANEL}" y2="{H}" '
                 f'stroke="#ddd" stroke-width="1"/>',
                 "</svg>"]
        with open(os.path.join(outdir, f"perview_{pid}.svg"), "w") as fh:
            fh.write("\n".join(parts))
        key[pid] = {"A": p["left"]["condition"], "B": p["right"]["condition"],
                    "view": p["view"], "is_null": p["is_null"]}
    with open(os.path.join(outdir, "perview_KEY.json"), "w") as fh:
        json.dump({"seed": seed, "key": key}, fh, indent=2)
    print(f"wrote {len(pairs)} pairs + perview_KEY.json to {outdir}")
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_projection_metric.py -v --timeout=420`
Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/probe_perview_retest.py mcp_harness/tests/test_projection_metric.py
git commit -m "probe(perview): per-view blinded re-test renderer, zero new captures

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

- [ ] **Step 7: HUMAN CHECKPOINT — run the probe and collect answers**

```bash
cd mcp_harness && .venv/bin/python probe_perview_retest.py /tmp/perview
```

Present the 14 SVGs to the user, ask the two pinned questions from the prereg,
record the answers verbatim, **then** reveal `perview_KEY.json`. Write the
outcome to `docs/superpowers/evidence/2026-08-08-perview-retest-outcome.md`
applying the pinned criterion unchanged, and commit it.

**Do not start Task 3 until this is done** — Task 6 consumes the recorded
per-view judgments.

---

## Task 3: Camera basis and polar signature

**Files:**
- Create: `mcp_harness/projection_metric.py`
- Modify: `mcp_harness/tests/test_projection_metric.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `camera_basis(elev_deg: float, azim_deg: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]` returning `(right, up, forward)`, each shape `(3,)`, orthonormal.
  - `polar_signature(vertices, elev_deg, azim_deg, nbins: int = 180) -> np.ndarray` of shape `(nbins,)`, strictly positive, bin `i` covering angles `[2*pi*i/nbins, 2*pi*(i+1)/nbins)` measured from the projected centroid.
  - Module constants `VIEWS` (the same 7 as the probe) and `NBINS = 180`.

- [ ] **Step 1: Write the failing tests**

Add to `mcp_harness/tests/test_projection_metric.py`:

```python
def test_camera_basis_is_orthonormal():
    import projection_metric as PM
    for elev, azim in PM.VIEWS:
        r, u, f = PM.camera_basis(elev, azim)
        for v in (r, u, f):
            assert abs(np.linalg.norm(v) - 1.0) < 1e-12
        assert abs(float(np.dot(r, u))) < 1e-12
        assert abs(float(np.dot(r, f))) < 1e-12
        assert abs(float(np.dot(u, f))) < 1e-12


def test_polar_signature_of_a_circle_is_flat():
    import projection_metric as PM
    t = np.linspace(0, 2 * np.pi, 400, endpoint=False)
    pts = np.stack([np.cos(t), np.sin(t), np.zeros_like(t)], axis=1)
    sig = PM.polar_signature(pts, 90, -90)          # top view: sees the circle
    assert sig.shape == (PM.NBINS,)
    assert sig.min() > 0
    assert (sig.max() - sig.min()) / sig.mean() < 0.02


def test_polar_signature_of_a_four_point_star_has_four_maxima():
    import projection_metric as PM
    t = np.linspace(0, 2 * np.pi, 720, endpoint=False)
    rad = 1.0 + 0.8 * (np.cos(4 * t) > 0.9)          # four spikes
    pts = np.stack([rad * np.cos(t), rad * np.sin(t), np.zeros_like(t)], axis=1)
    sig = PM.polar_signature(pts, 90, -90)
    assert sig.max() / sig.min() > 1.5


def test_polar_signature_fills_empty_bins():
    """A sparse cloud leaves bins with no vertex; they must be interpolated,
    never left at zero -- a zero bin would fake a concavity."""
    import projection_metric as PM
    t = np.linspace(0, 2 * np.pi, 11, endpoint=False)
    pts = np.stack([np.cos(t), np.sin(t), np.zeros_like(t)], axis=1)
    sig = PM.polar_signature(pts, 90, -90, nbins=180)
    assert (sig > 0).all()
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_projection_metric.py -k "basis or polar" -v --timeout=420`
Expected: FAIL with `ModuleNotFoundError: No module named 'projection_metric'`.

- [ ] **Step 3: Write the implementation**

Create `mcp_harness/projection_metric.py`:

```python
"""Projection-silhouette anatomy metric.

Deterministic, browser-free. Consumes folded geometry -- the payload
sim_capture returns AND the payload flat_fold/rigid_fold produce -- projects it
to a camera basis and reduces it to a POLAR SIGNATURE: the maximum radius per
angular bin about the projected centroid. No polygon boolean union is required,
which matters because this repo ships no polygon library and must not gain one
(mcp_harness/.venv is a symlink to the main repo's venv).

SCOPE WARNING. The analytic folders are valid for UNSHAPED flat states only:
flat_fold/rigid_fold/flex_extension/mobility_search/square_complete contain
zero references to edges_foldAngle and are theta-blind, and a shaped pattern
has no rigid state (measured closure residual 1.03 at the prescribed angles,
global minimum only at fully flat). Shaped evaluation therefore still requires
a browser capture. This module does not change that; it only makes the
measurement possible once you have the geometry.

Spec: docs/superpowers/specs/2026-08-07-instrument-first-shaping-evaluation-design.md
"""
from __future__ import annotations

import numpy as np

#: The seven cameras, shared with probe_perview_retest.
VIEWS = [(90, -90), (0, -90), (0, 0), (25, -55), (25, 35), (-25, -125), (55, 140)]

#: Angular bins in the polar signature (2 degrees each).
NBINS = 180

#: Protrusion threshold: a local maximum counts when it exceeds the mean
#: radius by this fraction. DERIVED, NOT FITTED -- a limb protruding less than
#: 35% beyond the mean radius is not something a viewer calls a limb. Pinned
#: before calibration; NEVER tune it to make calibration pass.
K = 0.35

#: Minimum angular separation between distinct protrusions, in bins.
MIN_SEP_BINS = 5


def camera_basis(elev_deg: float, azim_deg: float):
    """(right, up, forward) orthonormal basis for an orthographic camera."""
    e, a = np.radians(elev_deg), np.radians(azim_deg)
    cam = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
    f = -cam / np.linalg.norm(cam)
    up = np.array([0.0, 0.0, 1.0])
    if abs(float(np.dot(f, up))) > 0.999:
        up = np.array([0.0, 1.0, 0.0])
    r = np.cross(f, up)
    r = r / np.linalg.norm(r)
    u = np.cross(r, f)
    return r, u, f


def _fill_empty_bins(sig: np.ndarray) -> np.ndarray:
    """Circular linear interpolation across bins containing no vertex. A zero
    bin would read as a deep concavity that is not in the geometry."""
    n = len(sig)
    filled = sig > 0
    if filled.all():
        return sig
    if not filled.any():
        raise ValueError("polar signature is empty in every bin")
    idx = np.flatnonzero(filled)
    # unroll one period so interpolation wraps
    xs = np.concatenate([idx, idx + n])
    ys = np.concatenate([sig[idx], sig[idx]])
    out = np.interp(np.arange(n), xs, ys, period=None)
    # np.interp clamps below xs[0]; handle the wrap explicitly
    below = np.arange(n) < idx[0]
    if below.any():
        out[below] = np.interp(np.arange(n)[below] + n, xs, ys)
    return out


def polar_signature(vertices, elev_deg: float, azim_deg: float,
                    nbins: int = NBINS) -> np.ndarray:
    """Max projected radius per angular bin about the projected centroid."""
    V = np.asarray(vertices, dtype=float)
    if V.ndim != 2 or V.shape[1] not in (2, 3):
        raise ValueError(f"vertices must be (n,2) or (n,3), got {V.shape}")
    if V.shape[1] == 2:
        V = np.hstack([V, np.zeros((len(V), 1))])
    r_hat, u_hat, _ = camera_basis(elev_deg, azim_deg)
    x = V @ r_hat
    y = V @ u_hat
    dx = x - x.mean()
    dy = y - y.mean()
    ang = np.mod(np.arctan2(dy, dx), 2 * np.pi)
    rad = np.hypot(dx, dy)
    idx = np.minimum((ang / (2 * np.pi) * nbins).astype(int), nbins - 1)
    sig = np.zeros(nbins)
    np.maximum.at(sig, idx, rad)
    return _fill_empty_bins(sig)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_projection_metric.py -k "basis or polar" -v --timeout=420`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/projection_metric.py mcp_harness/tests/test_projection_metric.py
git commit -m "feat(projection-metric): camera basis + polar signature

Max radius per angular bin about the projected centroid -- the silhouette in
polar form, with no polygon boolean union, because the venv is the main
repo's and must not gain a polygon library. Empty bins are interpolated
circularly; a zero bin would fake a concavity.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 4: Protrusion counting

**Files:**
- Modify: `mcp_harness/projection_metric.py`
- Modify: `mcp_harness/tests/test_projection_metric.py`

**Interfaces:**
- Consumes: `polar_signature`, `K`, `MIN_SEP_BINS` from Task 3.
- Produces: `count_protrusions(sig: np.ndarray, k: float = K) -> tuple[int, list[int]]` returning `(count, peak_bin_indices)`; and `protrusion_aspects(sig, peaks) -> list[float]`, one aspect ratio per peak (peak radius divided by angular width in radians over which the signature stays above the mean).

- [ ] **Step 1: Write the failing tests**

```python
def test_count_protrusions_finds_four_spikes():
    import projection_metric as PM
    t = np.linspace(0, 2 * np.pi, PM.NBINS, endpoint=False)
    sig = 1.0 + 0.9 * np.exp(-((np.cos(4 * t) - 1) ** 2) / 0.002)
    count, peaks = PM.count_protrusions(sig)
    assert count == 4
    assert len(peaks) == 4


def test_count_protrusions_of_a_circle_is_zero():
    import projection_metric as PM
    sig = np.ones(PM.NBINS)
    count, peaks = PM.count_protrusions(sig)
    assert count == 0
    assert peaks == []


def test_count_protrusions_merges_adjacent_bins():
    """A single wide bump must count once, not once per bin above threshold."""
    import projection_metric as PM
    sig = np.ones(PM.NBINS)
    sig[40:47] = 2.0
    count, _ = PM.count_protrusions(sig)
    assert count == 1


def test_count_protrusions_wraps_around_zero():
    """A bump straddling bin 0 is ONE protrusion, not two."""
    import projection_metric as PM
    sig = np.ones(PM.NBINS)
    sig[-3:] = 2.0
    sig[:3] = 2.0
    count, _ = PM.count_protrusions(sig)
    assert count == 1


def test_protrusion_aspects_are_larger_for_thinner_spikes():
    import projection_metric as PM
    thin = np.ones(PM.NBINS); thin[90:93] = 2.5
    fat = np.ones(PM.NBINS); fat[80:103] = 2.5
    _, p_thin = PM.count_protrusions(thin)
    _, p_fat = PM.count_protrusions(fat)
    assert PM.protrusion_aspects(thin, p_thin)[0] > PM.protrusion_aspects(fat, p_fat)[0]
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_projection_metric.py -k "protrusion" -v --timeout=420`
Expected: FAIL with `AttributeError: module 'projection_metric' has no attribute 'count_protrusions'`.

- [ ] **Step 3: Write the implementation**

Append to `mcp_harness/projection_metric.py`:

```python
def count_protrusions(sig: np.ndarray, k: float = K,
                      min_sep: int = MIN_SEP_BINS):
    """(count, peak_bins) for local maxima exceeding mean_radius * (1 + k).

    Circular: a bump straddling bin 0 is one protrusion. Peaks closer than
    `min_sep` bins are merged, keeping the larger -- otherwise a single wide
    bump counts once per bin.
    """
    sig = np.asarray(sig, dtype=float)
    n = len(sig)
    thresh = float(sig.mean()) * (1.0 + k)
    cand = [i for i in range(n)
            if sig[i] >= thresh
            and sig[i] >= sig[(i - 1) % n]
            and sig[i] >= sig[(i + 1) % n]]
    if not cand:
        return 0, []
    # merge circularly-adjacent candidates
    cand.sort(key=lambda i: -sig[i])
    kept: list[int] = []
    for i in cand:
        if all(min(abs(i - j), n - abs(i - j)) >= min_sep for j in kept):
            kept.append(i)
    kept.sort()
    return len(kept), kept


def protrusion_aspects(sig: np.ndarray, peaks: list) -> list:
    """Peak radius divided by the angular width (radians) over which the
    signature stays above its mean, walking outward from each peak."""
    sig = np.asarray(sig, dtype=float)
    n = len(sig)
    mean = float(sig.mean())
    bin_rad = 2 * np.pi / n
    out = []
    for p in peaks:
        w = 1
        i = p
        while w < n and sig[(i - 1) % n] > mean:
            i -= 1
            w += 1
        i = p
        while w < n and sig[(i + 1) % n] > mean:
            i += 1
            w += 1
        out.append(float(sig[p] / max(w * bin_rad, 1e-9)))
    return out
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_projection_metric.py -k "protrusion" -v --timeout=420`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/projection_metric.py mcp_harness/tests/test_projection_metric.py
git commit -m "feat(projection-metric): circular protrusion counting with merge

Local maxima above mean*(1+K), K=0.35 pinned. Circular so a bump across bin 0
counts once; adjacent peaks merged so a wide bump does not count per-bin.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 5: Per-view signature and aggregate score

**Files:**
- Modify: `mcp_harness/projection_metric.py`
- Modify: `mcp_harness/tests/test_projection_metric.py`

**Interfaces:**
- Consumes: `polar_signature`, `count_protrusions`, `protrusion_aspects`, `VIEWS`.
- Produces:
  - `view_signature(vertices, elev_deg, azim_deg) -> dict` with keys `protrusions` (int), `aspects` (list[float]), `max_aspect` (float), `radius_cv` (float), `compactness` (float).
  - `anatomy_score(vertices, views=VIEWS) -> dict` with keys `per_view` (list of the above, one per view, in `views` order), `max_protrusions` (int), `mean_protrusions` (float).
  - **`anatomy_score` never returns a single scalar verdict.** The finding that motivated this design is that a one-camera signal washes out when views are averaged; a scalar aggregate would rebuild exactly that failure.

- [ ] **Step 1: Write the failing tests**

```python
def test_view_signature_reports_all_fields():
    import projection_metric as PM
    caps = load_captures()
    V = caps[0]["vertices_coords"]
    s = PM.view_signature(V, *PM.VIEWS[5])
    for key in ("protrusions", "aspects", "max_aspect", "radius_cv", "compactness"):
        assert key in s
    assert isinstance(s["protrusions"], int)
    assert len(s["aspects"]) == s["protrusions"]


def test_anatomy_score_has_one_entry_per_view_and_no_scalar_verdict():
    import projection_metric as PM
    caps = load_captures()
    score = PM.anatomy_score(caps[0]["vertices_coords"])
    assert len(score["per_view"]) == len(PM.VIEWS)
    assert "verdict" not in score
    assert "score" not in score


def test_anatomy_score_is_deterministic():
    import projection_metric as PM
    caps = load_captures()
    a = PM.anatomy_score(caps[0]["vertices_coords"])
    b = PM.anatomy_score(caps[0]["vertices_coords"])
    assert a == b


def test_metric_is_invariant_to_rigid_motion():
    """A rotated and translated copy must score identically per view up to the
    camera's own dependence on orientation -- so rotate ABOUT the view axis."""
    import projection_metric as PM
    caps = load_captures()
    V = np.asarray(caps[0]["vertices_coords"], dtype=float)
    sig_a = PM.polar_signature(V, 90, -90)
    sig_b = PM.polar_signature(V + np.array([3.0, -2.0, 5.0]), 90, -90)
    assert np.allclose(sig_a, sig_b, atol=1e-9)
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_projection_metric.py -k "signature or anatomy or invariant" -v --timeout=420`
Expected: FAIL with `AttributeError: ... has no attribute 'view_signature'`.

- [ ] **Step 3: Write the implementation**

Append to `mcp_harness/projection_metric.py`:

```python
def view_signature(vertices, elev_deg: float, azim_deg: float,
                   nbins: int = NBINS) -> dict:
    """Per-camera silhouette descriptors."""
    sig = polar_signature(vertices, elev_deg, azim_deg, nbins)
    count, peaks = count_protrusions(sig)
    aspects = protrusion_aspects(sig, peaks)
    dtheta = 2 * np.pi / nbins
    area = 0.5 * float(np.sum(sig ** 2) * dtheta)
    dr = np.diff(np.concatenate([sig, sig[:1]]))
    perim = float(np.sum(np.hypot(dr, sig * dtheta)))
    return {
        "protrusions": int(count),
        "aspects": [round(a, 6) for a in aspects],
        "max_aspect": round(max(aspects), 6) if aspects else 0.0,
        "radius_cv": round(float(sig.std() / sig.mean()), 6),
        "compactness": round(area / (perim ** 2) if perim > 0 else 0.0, 6),
    }


def anatomy_score(vertices, views=None) -> dict:
    """Per-view descriptors plus count summaries.

    Deliberately returns NO scalar verdict. The measurement that motivated this
    module (2026-08-07) found a real signal at ONE camera that vanished when
    seven views were collapsed into a single judgment; a scalar aggregate here
    would rebuild that exact failure inside the instrument.
    """
    views = list(VIEWS if views is None else views)
    per = [view_signature(vertices, e, a) for e, a in views]
    counts = [p["protrusions"] for p in per]
    return {
        "per_view": per,
        "max_protrusions": int(max(counts)) if counts else 0,
        "mean_protrusions": round(float(np.mean(counts)), 6) if counts else 0.0,
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_projection_metric.py -v --timeout=420`
Expected: 18 passed.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/projection_metric.py mcp_harness/tests/test_projection_metric.py
git commit -m "feat(projection-metric): per-view signature + aggregate, no scalar verdict

anatomy_score returns per-view descriptors and count summaries only. A scalar
aggregate would rebuild the exact failure that motivated this module: a real
one-camera signal vanishing when seven views are collapsed into one judgment.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 6: The calibration gate

This task decides whether P2 and P3 happen at all. **A failure here is a result to report, not a constant to tune.**

**Files:**
- Create: `mcp_harness/tests/test_projection_metric_calibration.py`
- Create: `docs/superpowers/evidence/2026-08-08-projection-metric-calibration.md`

**Interfaces:**
- Consumes: `anatomy_score`, `view_signature`, `VIEWS`, `K` from Tasks 3-5; the fixture from Task 1; the recorded per-view judgments from Task 2 Step 7.
- Produces: a committed calibration verdict document, and either a green gate or a written STOP.

- [ ] **Step 1: Write the three pinned criteria as tests**

Create `mcp_harness/tests/test_projection_metric_calibration.py`:

```python
"""CALIBRATION GATE for projection_metric.

These are not unit tests. They decide whether the instrument sees the property
it was built to see. K is pinned at 0.35 and MUST NOT be adjusted to make them
pass -- this repo's recurring failure is the vacuous gate (mv_swapped==0
scoring 8/8 on stock input; path_drift_max 0.0 on all five subjects;
pose_pregate returning identical dof/r* for six different theta).

Criteria, from the spec section 5:
  1. SHAPED scores above BASE at view index 5 (elev -25, azim -125), the
     camera at which a human identified leg structure in 4/4 shaped captures
     and 0/2 base captures.
  2. The BASE-vs-BASE null is NOT separated at any view.
  3. Views where the judge reported nothing read approximately equal.
"""
import json
import os

import numpy as np
import pytest

import projection_metric as PM

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(HERE, "fixtures", "legibility_captures.json")
FLAGGED_VIEW = 5


def _caps():
    with open(FIXTURE) as fh:
        return json.load(fh)["captures"]


def _by(cond):
    return [c for c in _caps() if c["condition"] == cond]


def _protrusions_at(cap, view):
    e, a = PM.VIEWS[view]
    return PM.view_signature(cap["vertices_coords"], e, a)["protrusions"]


def test_criterion_1_shaped_exceeds_base_at_the_flagged_view():
    base = [_protrusions_at(c, FLAGGED_VIEW) for c in _by("BASE")]
    shaped = [_protrusions_at(c, FLAGGED_VIEW) for c in _by("SHAPED")]
    assert min(shaped) > max(base), (
        f"CALIBRATION FAILURE (criterion 1): at view {FLAGGED_VIEW} "
        f"shaped protrusions {shaped} do not exceed base {base}. "
        f"Do NOT adjust K ({PM.K}) -- report this as a vacuous-metric result."
    )


def test_criterion_2_the_null_is_not_separated_at_any_view():
    b1, b2 = _by("BASE")
    for view in range(len(PM.VIEWS)):
        n1 = _protrusions_at(b1, view)
        n2 = _protrusions_at(b2, view)
        assert n1 == n2, (
            f"CALIBRATION FAILURE (criterion 2): the BASE-vs-BASE null "
            f"separates at view {view} ({n1} vs {n2}). The metric is reading "
            f"solver drift, not anatomy."
        )


def test_criterion_3_shaped_reads_are_mutually_consistent():
    """The three SHAPED captures are the same fold; the metric must not
    separate them either, or its 'signal' is capture noise."""
    shaped = _by("SHAPED")
    for view in range(len(PM.VIEWS)):
        counts = {_protrusions_at(c, view) for c in shaped}
        assert len(counts) == 1, (
            f"CALIBRATION FAILURE (criterion 3): the three SHAPED captures "
            f"disagree at view {view}: {sorted(counts)}."
        )


def test_the_metric_is_not_vacuous_across_views():
    """Anti-vacuity: the metric must not return the same protrusion count for
    every view of every capture. A constant reading passes criteria 2 and 3
    trivially."""
    vals = {_protrusions_at(c, v)
            for c in _caps() for v in range(len(PM.VIEWS))}
    assert len(vals) > 1, (
        f"CALIBRATION FAILURE: protrusion count is constant ({vals}) across "
        f"every view and every capture. Criteria 2 and 3 pass vacuously."
    )
```

- [ ] **Step 2: Run the gate**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_projection_metric_calibration.py -v --timeout=420`

Expected: **unknown — this is the experiment.** Record the actual output verbatim.

- [ ] **Step 3: Write the calibration verdict document**

Create `docs/superpowers/evidence/2026-08-08-projection-metric-calibration.md` recording, verbatim: the pytest output; the per-view protrusion counts for all 5 captures as a table; `K` as run; and one of:

- **PASS** (all four tests green) → the instrument separates shaped from base without separating the nulls. P2 and P3 are unblocked.
- **FAIL** (any test red) → **STOP.** The metric as specified is vacuous or mis-specified. Do **not** tune `K`. Report which criterion failed and by how much, and hand back for a design revision. P2 and P3 do not proceed.

Include the per-view table regardless of outcome — it is the evidence either way.

- [ ] **Step 4: Commit**

```bash
git add mcp_harness/tests/test_projection_metric_calibration.py \
        docs/superpowers/evidence/2026-08-08-projection-metric-calibration.md
git commit -m "gate(projection-metric): the calibration criteria, and their verdict

Four pinned criteria: shaped exceeds base at the flagged view; the
BASE-vs-BASE null is not separated at any view; the three shaped reads agree;
and the counts are not constant across views (anti-vacuity, without which
criteria 2 and 3 pass trivially). K stays 0.35.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

- [ ] **Step 5: Run the full suite**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest --timeout=420`
Expected: the pre-existing baseline plus this plan's new tests, with **no** previously-green test turning red. Main's true baseline is recorded as ~2417 passed / 11 skipped / 0 failed as of 2026-08-07; if a worktree shows ~35 extra failures, the gitignored Java artifacts are missing — symlink `mcp_harness/oriedita/oriedita-1.1.3.jar` and `mcp_harness/OrieditaValidator.class` from the main checkout rather than rebuilding.

---

## Self-Review

**1. Spec coverage.** Spec §5 (metric) → Tasks 3-5. §5 calibration criteria → Task 6. §6 (per-view re-test) → Task 2. §9a P1 boundary respected: §7 (kick) and §8 (VLM loop) are **deliberately absent** — they are P2 and P3 and get their own plans, per the spec's own decomposition. §10 error handling → the `ValueError` on an empty signature (Task 3) and the explicit STOP semantics (Task 6). §11 testing → Tasks 1-6; the "image reaches the model" test belongs to P3 and is correctly out of scope. §12 risk 1 ("the metric may be vacuous") → Task 6 Step 3's FAIL branch and `test_the_metric_is_not_vacuous_across_views`.

**2. Placeholder scan.** No TBD/TODO. Every code step carries complete code. Task 6 Step 2's "expected: unknown" is not a placeholder — it is the honest expected value of an experiment, and the step says to record the actual output.

**3. Type consistency.** `camera_basis` returns a 3-tuple everywhere (Tasks 2 and 3 both use `r, u, f`). `count_protrusions` returns `(int, list)` in Task 4 and is unpacked that way in Task 5. `polar_signature`'s `nbins` parameter is threaded consistently. The probe (Task 2) duplicates `camera_basis` rather than importing `projection_metric`, which does not exist until Task 3 — deliberate, so Task 2 can be built and judged first; the duplication is 8 lines and is resolved in P2's plan if desired.

**One deviation from the spec's stated order, flagged:** the spec lists §6 (re-test) then §5 (metric). This plan puts the fixture first (Task 1) because both the re-test and the metric depend on it, and keeps the re-test at Task 2 so the human-latency step starts as early as possible.
