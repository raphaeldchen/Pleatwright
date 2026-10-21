# B5-PRIME Whole-Pose Fit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reopen B5 on the SERVED compiled dog with a whole-pose objective that exploits global coupling — deliver a reusable pytest-covered coupling/search layer (`pose_base.py`, `pose_coupling.py`, `sim_capture` ports) plus three probe drivers, then run Gates 0→3 to a measured routing verdict.

**Architecture:** Two new pure pytest-covered modules (`mcp_harness/pose_base.py` naming+ops, `mcp_harness/pose_coupling.py` table+predictor+search plumbing), two helpers ported into `mcp_harness/sim_capture.py`, and three thin probe drivers (`probe_dog_coupling.py`, `probe_dog_beam.py`, `probe_quad_recipe.py`). Spec: `docs/superpowers/specs/2026-07-11-b5-prime-whole-pose-design.md` (APPROVED — every constant below is copied from it).

**Tech Stack:** Python 3.14 in `mcp_harness/.venv` (numpy, pytest; playwright lives in this venv ONLY and is lazily imported by `SimSession`). Sim = vendored Origami Simulator via Playwright, HEADED only.

## Global Constraints (binding, from the spec)

- Branch `feat/b5-prime-whole-pose` off main `3d2963d`. Never name anything "slice5". Branch `feat/b5-rigid-fold-slice5` is READ-ONLY reference — do not merge, import, or build `solve_closure`/`tip_vectors`.
- Substrate = SERVED display dog: `raw = mcp_harness/tests/goldens/dog.fold` → `square_complete.complete_square(raw, 1.0, 1.0)` → `shaping.apply_display_ops(sq, ops, raw=raw)`. Never the raw hull.
- Objective = `pose_target.angle_error(achieved, targets)` over {front, back, head}; fox targets via `starhead.fox_targets()` live, recorded fallback front 134.8316 / back 138.6544 / head 137.7186. Tail dropped on the target side; the tail FLAP is a legal (unscored) actuator.
- Op vocabulary = `reverse`, `outside`, `reverse_deep`, crimp (`shaping.crimp_ops` pair) ONLY. θ=90 excluded by grid construction AND defensively in `site_op`.
- Sequencing law: ≤ 1 `reverse_deep`/`sink` per sequence, and it must come FIRST (`apply_display_ops` enforces; our proposal generator enforces structurally too).
- Reach = probe/harness/data layer ONLY. Any apparent need to touch `ide-bridge.js`/vendored sim → HALT and ask the user.
- Probe outputs (`*.out.json` / `*.out.jsonl` / `*.out.log`) and suite logs stay UNCOMMITTED. `.superpowers/sdd/progress.md` (uncommitted) is the durable ledger.
- Human merges every PR — ASK before any push.
- Long sim runs are CONTROLLER-launched (nohup or foreground with explicit timeout). Subagent-launched background processes are ORPHAN-KILLED at turn end. Tasks 5, 6, 8, 9, 10 below are controller tasks — never dispatch them to a subagent.
- Margins: no 0.0 tolerances; strict gates carry the 10° margin; additivity threshold 15°; per-capture drift ~1e-5–0.02°, derived quantities up to ~0.09°.
- Suite baseline: **454 passed / 4 skipped** (measured 2026-07-12, `cd mcp_harness && .venv/bin/python -m pytest -q`, 532 s). New tests are additive; opt-in `RUN_SIM_REGRESSION` untouched.
- Capture budget ceiling ~400 (Gate 0 ~10 / Gate 1 ~170 / Gate 2 ~130 / Gate 2b ~45 / Gate 3 ~5 / reserve ~40). Refusals are pure-geometry and cost NO capture.
- Pre-authorized contingencies (ONLY these): pair-symmetric sequences arising as depth-2 beam members, beam depth 4 on a ≥10° wave gain, one extra Gate-2b wave on a ≥10° gain, the descent downgrade on calibration failure. Anything else → return to the user.

## File Structure

| File | Responsibility |
|---|---|
| `mcp_harness/pose_base.py` (create) | `NamedBase`: guarded naming pipeline (extracted from `probe_dog_pose.py`, semantics preserved), per-base config, actuator sites, op construction, strict apply, angle computation. Pure geometry — no sim imports. |
| `mcp_harness/tests/test_pose_base.py` (create) | Dog-golden parity, quad dry naming (pinned from measurement), synthetic guard fixtures, op-string/apply tests. |
| `mcp_harness/sim_capture.py` (modify, append only) | `tracked_points_lifted`, `capture_checked` — verbatim ports of `probe_dog_pose._tracked_points_lifted` / `._capture_checked`. |
| `mcp_harness/tests/test_sim_capture_ports.py` (create) | Mock-capture unit tests for the two ports. |
| `mcp_harness/probe_dog_pose.py` (modify) | Switch to the shared port functions AFTER a `--dry` parity check. |
| `mcp_harness/pose_coupling.py` (create) | `CouplingRow`/`CouplingTable` (JSONL + resume), `predict`, `propose`, `calibration`, `descent_schedule`, `half_step_axis`, `heatmap`, `rank1_share`. Sim-free; injected callables. |
| `mcp_harness/tests/test_pose_coupling.py` (create) | Round-trip/resume, predictor, proposal rules, calibration, schedule, summaries, mock beam end-to-end. |
| `mcp_harness/probe_dog_coupling.py` (create) | Gate 0 (`--gate0`) + Gate 1 matrix driver; owns the shared driver helpers other probes import. |
| `mcp_harness/probe_dog_beam.py` (create) | Gate 2: calibration wave → beam/descent → refinement. |
| `mcp_harness/probe_quad_recipe.py` (create) | Gate 2b (conditional on the Gate-0 dry quad naming). |
| `docs/superpowers/2026-07-XX-handoff-b5-prime-outcome.md` (create, Task 10) | Outcome handoff; spec banner update. |

Naming note: `probe_pose_sensitivity.py` exists (slice-1 star-4 probe) — the name is reserved; do not touch it.

---

### Task 1: `pose_base.py` — guarded naming + op construction

**Files:**
- Create: `mcp_harness/pose_base.py`
- Test: `mcp_harness/tests/test_pose_base.py`
- Read-only reference: `mcp_harness/probe_dog_pose.py:102-215, 312-348, 425-602` (the pipeline being extracted — semantics MUST be preserved), `mcp_harness/starhead.py:60-93` (`_tip_axial_len`, `_axial_hub_set` semantics), `mcp_harness/shaping.py:36-98` (`parse_op`, `crimp_ops`).

**Interfaces:**
- Consumes: `shaping.crimp_ops`, `shaping.apply_display_ops`, `shaping.parse_op`, `pose_target.group_tips_by_head`, `pose_target.angles_from_bones`, `pose_target._angle_deg`, `square_complete.complete_square` (tests only).
- Produces (later tasks rely on these exact names):
  - `PoseBaseError(ValueError)`, `OpRefused(PoseBaseError)`
  - `BaseConfig` dataclass; module constants `DOG_CONFIG`, `QUAD_CONFIG`
  - `Site` dataclass: fields `key: str`, `vid: int`, `role: str`, `xy: tuple`, `axial: float`, `hub: str`
  - `NamedBase(raw: dict, sq: dict, config: BaseConfig)` with attributes `raw, sq, config, ambiguities: list[str], scale: float|None, leaves: list[int], head: int|None, fronts: list[int]|None, backs: list[int]|None, tail: int|None, rear3: list[int]|None, grouping: dict, sites: dict[str, Site], targets: dict[str, tuple], targets_dropped: dict, leaf_hub_name: dict[int, str], hub_xy: list[tuple]`; property `ambiguity_count: int`; methods `site_op(site_key, kind, theta, frac, f2=None) -> list[str]`, `apply_strict(ops: list[str]) -> dict` (raises `OpRefused`), `angles_of(pts: dict) -> (per_leaf: dict, triple: dict|None, hyp: dict|None)`
  - module function `unique_targets(fold, targets) -> (ok, dropped)` (the extracted `_unique_targets`, public because probes re-check targets after shaping)

- [ ] **Step 1: Write the failing tests**

`mcp_harness/tests/test_pose_base.py`. The recorded Gate-3 parity fixture (from `probe_dog_pose.out.json`, run of 2026-07-11) is hard-coded — this is the dog parity requirement from spec §3a:

```python
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
import pose_base                    # noqa: E402
import shaping                      # noqa: E402
import square_complete              # noqa: E402

GOLDENS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "goldens")


def _load(name):
    with open(os.path.join(GOLDENS, name)) as fh:
        raw = json.load(fh)
    return raw, square_complete.complete_square(raw, 1.0, 1.0)


@pytest.fixture(scope="module")
def dog():
    raw, sq = _load("dog.fold")
    return pose_base.NamedBase(raw, sq, pose_base.DOG_CONFIG)


# ---- dog parity: the recorded Gate-3 grouping, EXACTLY (spec 3a) ------

def test_dog_parity_grouping(dog):
    assert dog.ambiguity_count == 0, dog.ambiguities
    assert dog.head == 25
    assert dog.fronts == [13, 18]
    assert dog.backs == [12, 16]
    assert dog.tail == 14
    assert dog.leaves == [12, 13, 14, 16, 18, 25]
    assert dog.grouping["head"] == "v25"
    assert dog.grouping["front"] == ["v13", "v18"]
    assert dog.grouping["back"] == ["v12", "v16"]
    assert dog.grouping["tail"] == "v14"


def test_dog_parity_hubs_scale_axials(dog):
    assert dog.scale == pytest.approx(0.656321)
    assert sorted(dog.hub_xy) == [
        pytest.approx((0.27093233, 0.2639727)),
        pytest.approx((0.81684995, 0.80717147))]
    ax = {s.key: s.axial for s in dog.sites.values()}
    assert ax == {
        "back_v12": pytest.approx(0.13130853416613722),
        "front_v13": pytest.approx(0.2460320745547058),
        "tail_v14": pytest.approx(0.2530395480314645),
        "back_v16": pytest.approx(0.13252024303632126),
        "front_v18": pytest.approx(0.24796617323241296),
        "head_v25": pytest.approx(0.36723677539198724)}
    assert dog.sites["front_v18"].hub == "hub_front"
    assert dog.sites["back_v12"].hub == "hub_rear"
    assert dog.sites["front_v18"].xy == (0.0, 0.46801304)


def test_dog_targets_track_named_leaves(dog):
    # every named leaf + both hubs survive the 8dp-uniqueness pre-check
    for k in ("v12", "v13", "v14", "v16", "v18", "v25",
              "hub_front", "hub_rear"):
        assert k in dog.targets
    assert dog.targets_dropped == {}


# ---- op construction ---------------------------------------------------

def test_site_op_reverse_string(dog):
    ops = dog.site_op("front_v18", "reverse", 105.0, 0.5)
    assert len(ops) == 1
    kind, xy, d, theta = shaping.parse_op(ops[0])
    assert kind == "reverse" and theta == 105.0
    assert xy == (0.0, 0.46801304)
    assert d == pytest.approx(0.5 * 0.24796617323241296)
    # the exact recorded Gate-3 op string round-trips
    assert ops[0].startswith("reverse:0.0,0.46801304:")


def test_site_op_all_kinds_parse(dog):
    for kind, theta, frac, f2 in [("reverse", 60.0, 0.35, None),
                                  ("outside", 142.5, 0.65, None),
                                  ("reverse_deep", 170.0, 1.25, None),
                                  ("crimp", 105.0, 0.5, 0.35)]:
        ops = dog.site_op("head_v25", kind, theta, frac, f2)
        assert len(ops) == (2 if kind == "crimp" else 1)
        for op in ops:
            shaping.parse_op(op)   # must not raise


def test_site_op_guards(dog):
    with pytest.raises(pose_base.PoseBaseError):
        dog.site_op("front_v18", "reverse", 90.0, 0.5)      # theta 90
    with pytest.raises(pose_base.PoseBaseError):
        dog.site_op("front_v18", "reverse", 105.0, 1.25)    # tip-local frac bound
    with pytest.raises(pose_base.PoseBaseError):
        dog.site_op("front_v18", "crimp", 105.0, 0.5)       # crimp needs f2
    with pytest.raises(pose_base.PoseBaseError):
        dog.site_op("nope_v0", "reverse", 105.0, 0.5)       # unknown site
    with pytest.raises(pose_base.PoseBaseError):
        dog.site_op("front_v18", "squash", 105.0, 0.5)      # unknown kind
    # reverse_deep frac 1.25 is LEGAL (beyond-segment regime, spec Gate 1)
    dog.site_op("front_v18", "reverse_deep", 105.0, 1.25)


# ---- strict apply ------------------------------------------------------

def test_apply_strict_applies_and_refuses(dog):
    good = dog.site_op("front_v18", "reverse", 105.0, 0.5)
    shaped = dog.apply_strict(good)
    assert shaped is not dog.sq
    with pytest.raises(pose_base.OpRefused):
        # no flap tip at the paper center -> shaping refuses the op
        dog.apply_strict(["reverse:0.5,0.5:0.01:105"])
    with pytest.raises(pose_base.OpRefused):
        # atomicity: first op fine, second refused -> whole unit refused
        dog.apply_strict(good + ["reverse:0.5,0.5:0.01:105"])


# ---- angles_of on synthetic tracked points -----------------------------

def test_angles_of_synthetic(dog):
    # place hubs at origin-ish and tips on known rays; angles must come
    # out via pose_target.angles_from_bones semantics (front avg etc.)
    pts = {"hub_front": [0.0, 0.0, 0.0], "hub_rear": [1.0, 0.0, 0.0],
           "v25": [0.0, 1.0, 0.0],                    # head: +y from front hub
           "v13": [1.0, 0.0, 0.0], "v18": [1.0, 0.0, 0.0],   # fronts: +x
           "v12": [1.0, 1.0, 0.0], "v16": [1.0, 1.0, 0.0],   # backs: +y from rear
           "v14": [2.0, 0.0, 0.0]}
    per_leaf, triple, hyp = dog.angles_of(pts)
    assert per_leaf[13] == pytest.approx(90.0)
    assert triple["front"] == pytest.approx(90.0)
    assert triple["back"] == pytest.approx(0.0)
    assert hyp is None                # backs are named on the dog


# ---- synthetic guard fixtures (each guard fires) -----------------------

def _synth_star4():
    """Unit-square border (4 corners + 4 mid-edge subdivision points),
    single center hub, one axial edge per corner. Exercises: hub-count
    guard (1 hub, not 2), relative-radius head guard (all radii equal),
    mirror guard (no axis yields 2 pairs + 2 unpaired on 4 leaves)."""
    vc = [[0, 0], [0.5, 0], [1, 0], [1, 0.5], [1, 1], [0.5, 1],
          [0, 1], [0, 0.5], [0.5, 0.5]]
    ev = [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7], [7, 0],
          [8, 0], [8, 2], [8, 4], [8, 6]]
    ea = ["B"] * 8 + ["M", "V", "M", "V"]
    return {"vertices_coords": vc, "edges_vertices": ev,
            "edges_assignment": ea}


SYNTH_CONFIG = pose_base.BaseConfig(
    name="synth4", head_rule="relative_radius",
    mirrors=pose_base.QUAD_CONFIG.mirrors, expect_leaves=4)


def test_synthetic_guards_fire():
    raw = _synth_star4()
    nb = pose_base.NamedBase(raw, raw, SYNTH_CONFIG)
    assert nb.ambiguity_count >= 3
    joined = " | ".join(nb.ambiguities)
    assert "expected 2 hubs" in joined
    assert "relative-radius head rule failed" in joined
    assert "mirror axes" in joined
    assert nb.head is None and nb.sites == {}


def test_broken_border_raises():
    raw = _synth_star4()
    raw["edges_assignment"][0] = "F"      # border no longer a simple cycle
    with pytest.raises(pose_base.PoseBaseError):
        pose_base.NamedBase(raw, raw, SYNTH_CONFIG)


def test_wrong_leaf_count_is_ambiguity():
    raw = _synth_star4()
    cfg = pose_base.BaseConfig(name="synth6", head_rule="relative_radius",
                               mirrors=pose_base.QUAD_CONFIG.mirrors,
                               expect_leaves=6)
    nb = pose_base.NamedBase(raw, raw, cfg)
    assert any("border corners vs 6 leaves" in a for a in nb.ambiguities)


# ---- quad dry naming (Gate-0 item 4; 0 captures) -----------------------

def test_quad_dry_naming_pinned():
    raw, sq = _load("quad.fold")
    nb = pose_base.NamedBase(raw, sq, pose_base.QUAD_CONFIG)
    # PIN AFTER FIRST MEASUREMENT (measure-then-pin): run this test once,
    # print nb.grouping + nb.ambiguities, replace the assertion below with
    # the measured outcome and a provenance comment. The spec accepts
    # EITHER outcome (armed or disarmed); the pin just freezes it.
    assert isinstance(nb.ambiguity_count, int)
    print("QUAD GROUPING:", nb.grouping)
    print("QUAD AMBIGUITIES:", nb.ambiguities)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_pose_base.py -q`
Expected: collection error / FAIL with `ModuleNotFoundError: No module named 'pose_base'`.

- [ ] **Step 3: Write `mcp_harness/pose_base.py`**

The naming pipeline is an EXTRACTION: copy the bodies of `probe_dog_pose.py` functions `candidate_tips` (:102), `_border_cycle` (:114), `_turn_sins` (:136), `_leaf_radii` (:150), `_mirror_pairs` (:167), `_snap_onto` (:187), `_unique_targets` (:200) and the `main()` naming sequence (:425-602) with EXACTLY these changes: `sim_capture.CaptureError` → `PoseBaseError`; module constants → `BaseConfig` fields; ambiguity strings preserved VERBATIM where the tests above grep them; head naming gains the config-selected `relative_radius` branch; mirror axes come from `config.mirrors`. Full module:

```python
"""pose_base -- guarded naming + op construction for compiled
multi-molecule bases (B5-prime spec 3a). Extracted from probe_dog_pose.py
(2026-07-11, semantics preserved; the dog parity pytest is the oracle).
Pure geometry: NO sim imports (playwright never loads through this module).

Naming never guesses: every guard failure appends an ambiguity flag;
structural failures (broken border topology, missing vertices) raise
PoseBaseError.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

import numpy as np

import pose_target
import shaping


class PoseBaseError(ValueError):
    """Structural failure -- distinct from a naming guard failure, which
    appends an ambiguity flag instead of raising."""


class OpRefused(PoseBaseError):
    """apply_strict: the shaping layer refused an op (identity return)."""


def _diag(p):
    return (p[1], p[0])


def _anti(p):
    return (1.0 - p[1], 1.0 - p[0])


def _flip_x(p):
    return (1.0 - p[0], p[1])


def _flip_y(p):
    return (p[0], 1.0 - p[1])


@dataclass(frozen=True)
class BaseConfig:
    name: str
    head_rule: str            # "radius_band" | "relative_radius"
    mirrors: tuple            # ((axis_name, xy -> xy), ...)
    expect_leaves: int = 6
    head_band: tuple = (0.36, 0.44)   # radius_band: tree-frame radii
    leg_ceil: float = 0.35
    rel_head_min: float = 1.2         # relative_radius: r >= 1.2 * median
    rel_other_max: float = 1.1        # ... all others <= 1.1 * median
    corner_sin: float = 0.017
    collinear_sin: float = 1e-4
    mirror_tol: float = 1e-6


# dog mirrors FROZEN at the recorded Gate-3 two-axis list (parity);
# quad gets the four canonical square symmetries (spec 3a).
DOG_CONFIG = BaseConfig(
    name="dog", head_rule="radius_band",
    mirrors=(("diagonal x<->y", _diag), ("anti-diagonal", _anti)))
QUAD_CONFIG = BaseConfig(
    name="quad", head_rule="relative_radius",
    mirrors=(("diagonal x<->y", _diag), ("anti-diagonal", _anti),
             ("x->1-x", _flip_x), ("y->1-y", _flip_y)))

ROLE_SHORT = {"head": "head", "front_leg": "front",
              "back_leg": "back", "tail": "tail"}


@dataclass
class Site:
    key: str        # e.g. "front_v18"
    vid: int        # raw-fold vertex id
    role: str       # head | front_leg | back_leg | tail
    xy: tuple       # SQUARED-fold coords, 8dp-snapped (tracked_points key)
    axial: float    # first axial segment length, raw fold
    hub: str        # "hub_front" | "hub_rear"
```

Then the extracted helpers — copy from `probe_dog_pose.py` with the error-class rename and config threading (shown in full so the extraction is unambiguous):

```python
def candidate_tips(fold):
    """probe_dog_pose.candidate_tips, verbatim."""
    border = {v for (a, b), s in zip(fold["edges_vertices"],
              fold["edges_assignment"]) if s == "B" for v in (a, b)}
    deg = {}
    for (a, b), s in zip(fold["edges_vertices"], fold["edges_assignment"]):
        if s in ("M", "V"):
            deg[a] = deg.get(a, 0) + 1
            deg[b] = deg.get(b, 0) + 1
    return sorted(v for v in border if deg.get(v, 0) == 1)


def _border_cycle(fold):
    adj: dict = {}
    for (a, b), s in zip(fold["edges_vertices"], fold["edges_assignment"]):
        if s == "B":
            adj.setdefault(a, []).append(b)
            adj.setdefault(b, []).append(a)
    bad = {v: len(n) for v, n in adj.items() if len(n) != 2}
    if bad:
        raise PoseBaseError(f"border not a simple cycle: {bad}")
    start = min(adj)
    walk = [start, adj[start][0]]
    while walk[-1] != start:
        prev, cur = walk[-2], walk[-1]
        walk.append([n for n in adj[cur] if n != prev][0])
    walk = walk[:-1]
    if len(walk) != len(adj):
        raise PoseBaseError("border has more than one loop")
    return walk
```

`_turn_sins`, `_leaf_radii`, `_mirror_pairs` (takes `tol` parameter now), `_snap_onto`, `unique_targets` (public, was `_unique_targets`): copy `probe_dog_pose.py:136-215` verbatim modulo `CaptureError → PoseBaseError` and `MIRROR_TOL → tol`. Two local re-implementations keep the module sim-free (semantics from `starhead.py:60-93`, docstring must cite that):

```python
def _tip_axial_len(fold, xy):
    """starhead._tip_axial_len semantics (local copy: keeps pose_base
    sim-free)."""
    V = np.asarray([p[:2] for p in fold["vertices_coords"]], dtype=float)
    d = np.linalg.norm(V - np.asarray(xy, dtype=float), axis=1)
    tip = int(np.argmin(d))
    if d[tip] > 1e-6:
        raise PoseBaseError(f"no fold vertex at tip {xy}")
    partners = [(a if b == tip else b)
                for (a, b), asn in zip(fold["edges_vertices"],
                                       fold["edges_assignment"])
                if asn in ("M", "V") and tip in (a, b)]
    if not partners:
        raise PoseBaseError(f"tip {xy} has no axial edge")
    return float(np.linalg.norm(V[partners[0]] - V[tip]))


def _axial_hub_set(fold):
    """starhead._axial_hub_set semantics (local copy)."""
    deg = {}
    for (a, b), asn in zip(fold["edges_vertices"],
                           fold["edges_assignment"]):
        if asn in ("M", "V"):
            deg[a] = deg.get(a, 0) + 1
            deg[b] = deg.get(b, 0) + 1
    if not deg:
        raise PoseBaseError("fold has no axial (M/V) edges")
    top = max(deg.values())
    return [(round(float(fold["vertices_coords"][v][0]), 8),
             round(float(fold["vertices_coords"][v][1]), 8))
            for v in sorted(deg) if deg[v] == top]
```

`NamedBase.__init__` runs the `probe_dog_pose.main()` naming sequence (:425-602) verbatim-modulo-config; the only NEW logic is the `relative_radius` head branch (spec §3a pinned rule — median `m` of paper radii, candidates `r >= 1.2*m`, PASS iff exactly one candidate and every other leaf `<= 1.1*m`) and the config-driven mirror loop. Structure:

```python
class NamedBase:
    def __init__(self, raw: dict, sq: dict, config: BaseConfig):
        self.raw, self.sq, self.config = raw, sq, config
        amb = self.ambiguities = []
        V = self.V = [(float(p[0]), float(p[1]))
                      for p in raw["vertices_coords"]]
        m = re.search(r"scale=([0-9.]+)", raw.get("frame_title", ""))
        self.scale = float(m.group(1)) if m else None

        hubs = _axial_hub_set(raw)
        if len(hubs) != 2:
            amb.append(f"expected 2 hubs, found {len(hubs)}")

        # step a: leaves = border-polygon corners  [probe :425-446]
        walk = _border_cycle(raw)
        sins = _turn_sins(V, walk)
        corners = [v for v in walk if sins[v] > config.corner_sin]
        mid = [v for v in walk
               if config.collinear_sin < sins[v] <= config.corner_sin]
        if mid:
            amb.append(f"border vertices with mid-range turn sins {mid}"
                       " -- corner vs subdivision classification"
                       " AMBIGUOUS for them")
        leaves_named = (len(corners) == config.expect_leaves and not mid)
        if not leaves_named:
            amb.append(f"{len(corners)} border corners vs"
                       f" {config.expect_leaves} leaves from provenance"
                       " -- leaf identification AMBIGUOUS")
        self.leaves = leaves = sorted(corners)
        leaf_xy = {v: V[v] for v in leaves}

        # step b: leaf radii from border tangencies  [probe :458-477]
        radii = _leaf_radii(V, walk, set(leaves))
        paper_r = {}
        for v in leaves:
            got = [r for r in radii[v] if r is not None]
            r = sum(got) / len(got) if got else None
            if len(got) == 2 and (max(got) - min(got)) > 2e-3:
                amb.append(f"leaf v{v} radius disagrees across its two"
                           f" border sides by {max(got) - min(got):.6f}"
                           " -- radius UNRELIABLE")
                r = None
            paper_r[v] = r
        self.paper_radius = paper_r

        # step c: head by config-selected rule  [probe :479-494 + spec]
        head = None
        if leaves_named and all(paper_r[v] is not None for v in leaves):
            if config.head_rule == "radius_band":
                if self.scale is None:
                    amb.append("frame_title scale missing -- radius_band"
                               " head rule unusable, head AMBIGUOUS")
                else:
                    tree_r = {v: paper_r[v] / self.scale for v in leaves}
                    in_band = [v for v, r in tree_r.items()
                               if config.head_band[0] <= r
                               <= config.head_band[1]]
                    below = [v for v, r in tree_r.items()
                             if r <= config.leg_ceil]
                    if (len(in_band) == 1
                            and len(below) == config.expect_leaves - 1):
                        head = in_band[0]
                    else:
                        amb.append(f"head band test failed (in-band"
                                   f" {in_band}) -- head AMBIGUOUS, no"
                                   " angle is computable without a head"
                                   " bone")
            elif config.head_rule == "relative_radius":
                med = float(np.median([paper_r[v] for v in leaves]))
                cand = [v for v in leaves
                        if paper_r[v] >= config.rel_head_min * med]
                others_ok = all(paper_r[v] <= config.rel_other_max * med
                                for v in leaves if v not in cand)
                if len(cand) == 1 and others_ok:
                    head = cand[0]
                else:
                    amb.append("relative-radius head rule failed"
                               f" (candidates {cand}, median {med:.6f})"
                               " -- head AMBIGUOUS")
            else:
                raise PoseBaseError(f"unknown head_rule"
                                    f" {config.head_rule!r}")
        elif leaves_named:
            amb.append("a leaf radius is unmeasurable -- head naming"
                       " AMBIGUOUS")
        self.head = head

        # step d: leg pairs by exact mirror symmetry over config.mirrors
        # [probe :496-511, guard unchanged: exactly ONE clean axis]
        valid = []
        for axis_name, fn in config.mirrors:
            pr, up = _mirror_pairs(leaf_xy, fn, config.mirror_tol)
            if len(pr) == 2 and len(up) == 2:
                valid.append((axis_name, pr, up))
        pairs = unpaired = mirror_name = None
        if len(valid) == 1:
            mirror_name, pairs, unpaired = valid[0]
        else:
            amb.append(f"{len(valid)} mirror axes give a clean"
                       " 2-pairs+2-unpaired split -- leg pairing"
                       " (symmetry basis) AMBIGUOUS")
        self.mirror_axis = mirror_name

        # hub association + group assembly  [probe :513-577, verbatim
        # modulo self./local renames -- copy it, do not re-derive]
        ...
        # sets: self.fronts, self.backs, self.tail, self.rear3,
        #       self.leaf_hub_name (v -> "hub_front"/"hub_rear"),
        #       hub_names (index -> name), including the
        #       group_tips_by_head cross-check ambiguity.

        # axial lengths + roles + grouping dict  [probe :579-602]
        axial = {v: _tip_axial_len(raw, V[v]) for v in leaves}
        self.axial = axial
        role = {}
        for v in leaves:
            role[v] = ("head" if v == head else
                       "front_leg" if self.fronts and v in self.fronts
                       else "back_leg" if self.backs and v in self.backs
                       else "tail" if v == self.tail
                       else "leaf (group AMBIGUOUS)")
        self.grouping = {
            "head": f"v{head}" if head is not None else "AMBIGUOUS",
            "front": ([f"v{v}" for v in self.fronts]
                      if self.fronts else "AMBIGUOUS"),
            "back": ([f"v{v}" for v in self.backs]
                     if self.backs else "AMBIGUOUS"),
            "tail": f"v{self.tail}" if self.tail is not None
                    else "AMBIGUOUS",
            "rear_trio": ([f"v{v}" for v in self.rear3]
                          if self.rear3 else None)}

        # sites: ONLY leaves with a positive role  [spec 3a]
        self.sites = {}
        for v in leaves:
            if role[v] in ROLE_SHORT:
                key = f"{ROLE_SHORT[role[v]]}_v{v}"
                self.sites[key] = Site(
                    key=key, vid=v, role=role[v],
                    xy=_snap_onto(sq, V[v]), axial=axial[v],
                    hub=self.leaf_hub_name.get(v))

        # tracked-point targets on the squared fold  [probe :609-618]
        self.hub_xy = [_snap_onto(sq, h) for h in hubs]
        tgt = {f"v{v}": _snap_onto(sq, V[v])
               for v in sorted(set(candidate_tips(raw)) | set(leaves))}
        for i, h in enumerate(self.hub_xy):
            tgt[hub_names.get(i, f"hub{i}")] = h
        self.targets, self.targets_dropped = unique_targets(sq, tgt)
        if self.targets_dropped:
            amb.append(f"targets dropped (8dp collision):"
                       f" {self.targets_dropped}")

    @property
    def ambiguity_count(self):
        return len(self.ambiguities)
```

(The two `...`-elided blocks are VERBATIM copies of `probe_dog_pose.py:513-577` — copy them; the parity test fails on any drift. Nothing else in this module may be elided.)

Op construction + strict apply + angles:

```python
    def site_op(self, site_key, kind, theta, frac, f2=None):
        """One actuator cell -> op strings. d = frac * the site's first
        axial segment. crimp emits the shaping.crimp_ops pair (atomic
        unit). theta=90 is structurally excluded from every grid AND
        rejected here (recorded silent mis-target hazard)."""
        if site_key not in self.sites:
            raise PoseBaseError(f"unknown site {site_key!r}")
        if theta == 90.0:
            raise PoseBaseError("theta 90 excluded (crimp silent"
                                " mis-target record; use 75/105)")
        s = self.sites[site_key]
        x, y = s.xy
        if kind == "crimp":
            if f2 is None:
                raise PoseBaseError("crimp needs f2")
            return shaping.crimp_ops((x, y), s.axial, theta, frac, f2)
        if kind in ("reverse", "outside"):
            if not 0.0 < frac < 1.0:
                raise PoseBaseError(f"tip-local frac {frac} outside (0,1)")
        elif kind != "reverse_deep":
            raise PoseBaseError(f"unknown op kind {kind!r}")
        # reverse_deep frac may exceed 1 (beyond-segment through-layers
        # regime, spec Gate 1 -- plain reverse refuses there)
        d = frac * s.axial
        return [f"{kind}:{x},{y}:{d}:{theta}"]

    def apply_strict(self, ops):
        """starhead.apply_ops pattern: one op at a time, object-identity
        refusal detection, raise OpRefused on ANY refusal (a half-applied
        crimp can never be scored)."""
        out = self.sq
        for op in ops:
            res = shaping.apply_display_ops(out, [op], raw=self.raw)
            if res is out:
                raise OpRefused(f"op refused: {op}")
            out = res
        return out

    def angles_of(self, pts):
        """probe_dog_pose._angles (:312-348) as a method: bone vector =
        folded tip - folded NEAREST hub; same pose_target primitives.
        Returns (per_leaf {vid: deg}, triple {front,back,head} | None,
        back-pair hypotheses | None)."""
        # copy probe_dog_pose.py:318-348 with leaf_hub= self.leaf_hub_name,
        # head=self.head, fronts=self.fronts, backs=self.backs,
        # rear3=self.rear3, leaves=self.leaves
```

- [ ] **Step 4: Run tests; pin the quad outcome**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_pose_base.py -q -s`
Expected: all PASS. Read the printed `QUAD GROUPING` / `QUAD AMBIGUITIES`, then REPLACE the placeholder assertion in `test_quad_dry_naming_pinned` with the measured outcome (e.g. `assert nb.ambiguity_count == 0 and nb.grouping["head"] == "vN"` if it names, or `assert nb.ambiguity_count >= 1 and "head AMBIGUOUS" in ...` if not), with a comment `# pinned from first measured run, 2026-07-12 (Gate-0 dry check)`. Re-run: PASS. This measured outcome is the Gate-2b arm/disarm signal — record it in the task report.

- [ ] **Step 5: Run the full suite**

Run: `cd mcp_harness && .venv/bin/python -m pytest -q`
Expected: 454 + (new pose_base tests) passed / 4 skipped, no regressions. (~9 min.)

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/pose_base.py mcp_harness/tests/test_pose_base.py
git commit -m "feat(b5-prime): pose_base NamedBase -- guarded naming extracted from probe_dog_pose (dog parity pinned) + per-base config + site ops + strict apply

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: `sim_capture` ports + `probe_dog_pose` switch

**Files:**
- Modify: `mcp_harness/sim_capture.py` (append two functions at the end, before `_anchor_main`)
- Modify: `mcp_harness/probe_dog_pose.py:218-288, 356-377` (replace bodies with aliases AFTER the parity check)
- Test: `mcp_harness/tests/test_sim_capture_ports.py`

**Interfaces:**
- Produces: `sim_capture.tracked_points_lifted(fold: dict, cap: dict, flat_targets: dict) -> dict[str, np.ndarray]` and `sim_capture.capture_checked(sim, fold, attempts_log: list, attempts: int = 3) -> (cap, disp)`. Both raise `sim_capture.CaptureError`. Every later probe consumes exactly these two names.

- [ ] **Step 1: Write the failing tests**

`mcp_harness/tests/test_sim_capture_ports.py`:

```python
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
import sim_capture                  # noqa: E402


def _fold_and_cap(scale=2.0, lift=1e-4):
    """4-vertex synthetic: flat unit square folded (scene X-Z paper) at a
    uniform scale, tiny Y lift -- passes every integrity check."""
    fold = {"vertices_coords": [[0.0, 0.0], [1.0, 0.0],
                                [1.0, 1.0], [0.0, 1.0]]}
    flat = [[x * scale, lift * i, y * scale]
            for i, (x, y) in enumerate([(0, 0), (1, 0), (1, 1), (0, 1)])]
    cap = {"vertices_coords": [[0.1 * i, 0.2, 0.3] for i in range(4)],
           "flat_coords": flat}
    return fold, cap


TARGETS = {"a": (0.0, 0.0), "b": (1.0, 1.0)}


def test_lifted_happy_path():
    fold, cap = _fold_and_cap()
    pts = sim_capture.tracked_points_lifted(fold, cap, TARGETS)
    assert set(pts) == {"a", "b"}
    assert np.allclose(pts["b"], [0.2, 0.2, 0.3])


def test_lifted_lift_axis_violation():
    fold, cap = _fold_and_cap(lift=0.5)   # Y extent >> 1% of X-Z extent
    with pytest.raises(sim_capture.CaptureError, match="lifted-plane"):
        sim_capture.tracked_points_lifted(fold, cap, TARGETS)


def test_lifted_absolute_residual():
    fold, cap = _fold_and_cap()
    cap["flat_coords"][2][0] += 0.01      # move one tracked vertex
    with pytest.raises(sim_capture.CaptureError, match="residual"):
        sim_capture.tracked_points_lifted(fold, cap, TARGETS)


def test_lifted_target_miss():
    fold, cap = _fold_and_cap()
    with pytest.raises(sim_capture.CaptureError, match="matches"):
        sim_capture.tracked_points_lifted(fold, cap, {"z": (5.0, 5.0)})


class _FakeSim:
    def __init__(self, caps):
        self.caps = list(caps)

    def capture(self, fold):
        return self.caps.pop(0)


def test_capture_checked_retries_parked_only(monkeypatch):
    calls = []

    def fake_check(cap, expect_verts=None):
        calls.append(cap)
        if cap == "parked":
            raise sim_capture.CaptureError("fold did not fold:"
                                           " maxDisplacement 0.0000")
        if cap == "boom":
            raise sim_capture.CaptureError("NaN in vertices")
        return [], 1.5

    monkeypatch.setattr(sim_capture, "check_capture", fake_check)
    log = []
    cap, disp = sim_capture.capture_checked(
        _FakeSim(["parked", "ok"]), {"vertices_coords": []}, log)
    assert cap == "ok" and disp == 1.5
    assert len(log) == 2 and "error" in log[0] and log[1]["disp"] == 1.5

    log2 = []
    with pytest.raises(sim_capture.CaptureError):      # fail fast
        sim_capture.capture_checked(
            _FakeSim(["boom", "ok"]), {"vertices_coords": []}, log2)
    assert len(log2) == 1

    log3 = []
    with pytest.raises(sim_capture.CaptureError):      # persistent park
        sim_capture.capture_checked(
            _FakeSim(["parked"] * 3), {"vertices_coords": []}, log3)
    assert len(log3) == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_sim_capture_ports.py -q`
Expected: FAIL with `AttributeError: module 'sim_capture' has no attribute 'tracked_points_lifted'`.

- [ ] **Step 3: Port the two functions into `sim_capture.py`**

Copy `probe_dog_pose.py:218-288` (`_tracked_points_lifted`) and `:356-377` (`_capture_checked`) VERBATIM to the end of `sim_capture.py` (before `_star4_raw`), renamed `tracked_points_lifted` / `capture_checked`, with `sim_capture.CaptureError` → `CaptureError` and `sim_capture.check_capture` → `check_capture` — wait: `capture_checked` must call `check_capture` through the module attribute so the monkeypatch test works; since it lives IN sim_capture, call it as a plain module-level name (`check_capture(...)`) — monkeypatch on `sim_capture.check_capture` rebinds that same global, so plain-name calls see the patch. Keep the full docstrings (they carry the measured evidence for the 1e-4 absolute bound and the parked-retry scoping). Also update the existing `tracked_points` docstring caveat (sim_capture.py, the "lifted fold" note) to point at `tracked_points_lifted` as the now-landed follow-up.

- [ ] **Step 4: Run tests**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_sim_capture_ports.py -q`
Expected: 5 passed.

- [ ] **Step 5: Dry-run parity, then switch `probe_dog_pose`**

```bash
cd mcp_harness && .venv/bin/python probe_dog_pose.py --dry > /tmp/dry_before.json
```

Then edit `probe_dog_pose.py`: delete the bodies of `_tracked_points_lifted` (:218-288) and `_capture_checked` (:356-377) and replace with aliases (keep one-line docstring pointers):

```python
# ported to sim_capture (B5-prime Task 2); probe keeps the old names
_tracked_points_lifted = sim_capture.tracked_points_lifted
_capture_checked = sim_capture.capture_checked
```

```bash
cd mcp_harness && .venv/bin/python probe_dog_pose.py --dry > /tmp/dry_after.json
diff /tmp/dry_before.json /tmp/dry_after.json
```

Expected: NO diff (dry mode exercises naming/targets only; the ported functions are byte-identical copies covered by Step 1's unit tests). If the diff is non-empty: revert the probe edit, keep the private copies, record the failure in the task report (spec §3c contingency), and continue — the shared versions still ship for the NEW probes.

- [ ] **Step 6: Run the full suite**

Run: `cd mcp_harness && .venv/bin/python -m pytest -q`
Expected: previous count + 5 passed / 4 skipped.

- [ ] **Step 7: Commit**

```bash
git add mcp_harness/sim_capture.py mcp_harness/tests/test_sim_capture_ports.py mcp_harness/probe_dog_pose.py
git commit -m "feat(b5-prime): port tracked_points_lifted + capture_checked into sim_capture (unit-tested); probe_dog_pose switches after --dry parity

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: `pose_coupling.py` — table, predictor, proposal, calibration, descent

**Files:**
- Create: `mcp_harness/pose_coupling.py`
- Test: `mcp_harness/tests/test_pose_coupling.py`

**Interfaces:**
- Consumes: nothing sim-side; numpy only. Evaluators/apply-checks are injected callables (the `pose_search` philosophy).
- Produces (later tasks rely on these exact names):
  - `CouplingError(ValueError)`; `GROUPS = ("front", "back", "head")`
  - `CouplingRow` dataclass (fields below); `cell_key(site, kind, theta, frac, f2=None) -> str`; `seq_id(keys) -> str`
  - `CouplingTable(path)` with `.rows`, `.append(row)`, `.resume_keys() -> set`, `.scored_cells() -> dict[str, CouplingRow]`, `.measured_seqs() -> dict[tuple, float]`
  - `predict(cells, keys, baseline_angles, targets) -> (pred_angles, pred_total)`
  - `propose(cells, incumbents, *, width, depth_cap, per_wave, baseline_angles, targets, apply_check, measured_seqs) -> list[tuple]`
  - `calibration(pairs, threshold=15.0) -> (median_abs_err, keep_beam)`
  - `descent_schedule(cells, sites, incumbent, top_n=6) -> list[(site, [axis])]`
  - `half_step_axis(grid, value, lo=None, hi=None) -> list[float]`
  - `heatmap(cells) -> dict`, `rank1_share(cells) -> float|None`

- [ ] **Step 1: Write the failing tests**

`mcp_harness/tests/test_pose_coupling.py`:

```python
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
import pose_coupling as pc          # noqa: E402

TARGETS = {"front": 134.83, "back": 138.65, "head": 137.72}
BASE = {"front": 64.83, "back": 36.46, "head": 37.40}


def _row(site, kind, theta, frac, dg, f2=None, verdict="scored"):
    key = pc.cell_key(site, kind, theta, frac, f2)
    total = sum(abs(BASE[g] + dg[g] - TARGETS[g]) for g in pc.GROUPS)
    base_total = sum(abs(BASE[g] - TARGETS[g]) for g in pc.GROUPS)
    return pc.CouplingRow(
        gate="gate1", key=key, ops=[f"{kind}:0,0:0.1:{theta}"],
        verdict=verdict, site=site, kind=kind, theta=theta, frac=frac,
        f2=f2, angles={g: BASE[g] + dg[g] for g in pc.GROUPS},
        total=total, delta_total=total - base_total, delta_groups=dg)


def test_jsonl_roundtrip_and_resume(tmp_path):
    path = str(tmp_path / "t.jsonl")
    t = pc.CouplingTable(path)
    r = _row("front_v18", "reverse", 105.0, 0.5,
             {"front": -3.0, "back": 74.0, "head": 47.2})
    t.append(r)
    t.append(_row("head_v25", "outside", 60.0, 0.35,
                  {"front": 1.0, "back": 2.0, "head": 3.0},
                  verdict="refused"))
    t2 = pc.CouplingTable(path)
    assert len(t2.rows) == 2
    assert t2.resume_keys() == {r.key, t.rows[1].key}
    assert set(t2.scored_cells()) == {r.key}          # refused not scored


def test_cell_key_format():
    assert pc.cell_key("back_v12", "reverse", 105.0, 0.5) \
        == "back_v12|reverse|105|0.5"
    assert pc.cell_key("tail_v14", "crimp", 105.0, 0.5, 0.35) \
        == "tail_v14|crimp|105|0.5|0.35"


def test_predict_additive():
    cells = {r.key: r for r in [
        _row("front_v18", "reverse", 105.0, 0.5,
             {"front": -3.0, "back": 74.0, "head": 47.0}),
        _row("back_v12", "reverse", 60.0, 0.35,
             {"front": 10.0, "back": 20.0, "head": -5.0})]}
    pred, total = pc.predict(cells, list(cells), BASE, TARGETS)
    assert pred["back"] == pytest.approx(36.46 + 74.0 + 20.0)
    assert total == pytest.approx(
        sum(abs(pred[g] - TARGETS[g]) for g in pc.GROUPS))
    with pytest.raises(pc.CouplingError):
        pc.predict(cells, ["missing|reverse|105|0.5"], BASE, TARGETS)


def _world():
    """Synthetic additive world over 3 sites x 2 ops."""
    dgs = {
        ("front_v18", 105.0): {"front": -3.0, "back": 74.0, "head": 47.0},
        ("front_v18", 60.0): {"front": 5.0, "back": 10.0, "head": 5.0},
        ("back_v12", 105.0): {"front": 2.0, "back": 30.0, "head": 40.0},
        ("back_v12", 60.0): {"front": 1.0, "back": 5.0, "head": 2.0},
        ("head_v25", 105.0): {"front": 0.0, "back": -5.0, "head": 20.0},
        ("head_v25", 60.0): {"front": 0.0, "back": 1.0, "head": 4.0}}
    cells = {}
    for (site, theta), dg in dgs.items():
        r = _row(site, "reverse", theta, 0.5, dg)
        cells[r.key] = r
    return cells, dgs


def test_propose_rules():
    cells, _ = _world()
    deep = _row("tail_v14", "reverse_deep", 105.0, 0.5,
                {"front": 1.0, "back": 1.0, "head": 1.0})
    cells[deep.key] = deep
    base_total = sum(abs(BASE[g] - TARGETS[g]) for g in pc.GROUPS)
    out = pc.propose(cells, [((), base_total)], width=4, depth_cap=3,
                     per_wave=50, baseline_angles=BASE, targets=TARGETS,
                     apply_check=lambda seq: True, measured_seqs=set())
    assert out, "must propose something"
    for seq in out:
        sites = [k.split("|")[0] for k in seq]
        assert len(sites) == len(set(sites))          # one op per site
        deeps = [k for k in seq if k.split("|")[1] == "reverse_deep"]
        assert len(deeps) <= 1
        if deeps:
            assert seq[0] == deeps[0]                 # deep FIRST
        assert len(seq) <= 3
    # extension of a deep-holding incumbent APPENDS tip-local only
    inc = ((deep.key,), 200.0)
    out2 = pc.propose(cells, [inc], width=1, depth_cap=3, per_wave=10,
                      baseline_angles=BASE, targets=TARGETS,
                      apply_check=lambda seq: True, measured_seqs=set())
    for seq in out2:
        assert seq[0] == deep.key
        assert all(k.split("|")[1] != "reverse_deep" for k in seq[1:])
    # measured sequences never re-proposed; prefilter drops refusals
    first = tuple(out[0])
    out3 = pc.propose(cells, [((), base_total)], width=4, depth_cap=3,
                      per_wave=50, baseline_angles=BASE, targets=TARGETS,
                      apply_check=lambda seq: seq != first,
                      measured_seqs={first})
    assert first not in out3


def test_calibration():
    med, keep = pc.calibration([(100.0, 110.0), (90.0, 91.0),
                                (150.0, 120.0)])
    assert med == pytest.approx(10.0) and keep is True
    med2, keep2 = pc.calibration([(100.0, 130.0), (90.0, 130.0)])
    assert keep2 is False
    with pytest.raises(pc.CouplingError):
        pc.calibration([])


def test_descent_schedule_includes_incumbent_and_none():
    cells, _ = _world()
    inc_key = pc.cell_key("front_v18", "reverse", 60.0, 0.5)
    sched = pc.descent_schedule(cells, ["front_v18", "back_v12"],
                                {"front_v18": inc_key}, top_n=1)
    assert len(sched) == 2
    site, axes = sched[0]
    assert site == "front_v18" and len(axes) == 1
    axis = axes[0]
    assert None in axis and inc_key in axis


def test_half_step_axis():
    grid = [60.0, 105.0, 142.5, 170.0]
    assert pc.half_step_axis(grid, 105.0) == [82.5, 105.0, 123.75]
    assert pc.half_step_axis(grid, 60.0) == [60.0, 82.5]
    assert pc.half_step_axis([0.35, 0.5, 0.65], 0.65, lo=0.0, hi=1.0) \
        == [0.575, 0.65]                     # hi bound open: no 0.725+? no
    # frac 0.65 upper neighbor midpoint would need a >0.65 grid point;
    # with none, only the lower midpoint + incumbent appear


def test_summaries():
    cells, _ = _world()
    hm = pc.heatmap(cells)
    assert hm[("front_v18", "reverse")]["back"] == pytest.approx(74.0)
    share = pc.rank1_share(cells)
    assert share is not None and 0.0 < share <= 1.0


def test_mock_beam_finds_known_optimum():
    """End-to-end on a truly additive world: the beam must reach the
    exhaustive-search optimum over <=2-op site-exclusive sequences."""
    import itertools
    cells, _ = _world()

    def measure(seq):
        pred, total = pc.predict(cells, list(seq), BASE, TARGETS)
        return total                      # world IS additive: 0 noise

    best_true = min(
        (measure(s) for n in (1, 2) for s in itertools.permutations(
            cells, n) if len({k.split("|")[0] for k in s}) == n),
        default=None)
    base_total = sum(abs(BASE[g] - TARGETS[g]) for g in pc.GROUPS)
    incumbents = [((), base_total)] + sorted(
        (((k,), measure((k,))) for k in cells), key=lambda t: t[1])[:3]
    measured = {(): base_total}
    for _wave in range(3):
        newseqs = pc.propose(cells, incumbents, width=4, depth_cap=3,
                             per_wave=10, baseline_angles=BASE,
                             targets=TARGETS,
                             apply_check=lambda s: True,
                             measured_seqs=set(measured))
        for s in newseqs:
            measured[s] = measure(s)
        incumbents = sorted(measured.items(), key=lambda t: t[1])[:4]
    assert incumbents[0][1] == pytest.approx(best_true)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_pose_coupling.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'pose_coupling'`.

- [ ] **Step 3: Write `mcp_harness/pose_coupling.py`**

```python
"""pose_coupling -- coupling table, additive predictor, beam proposal,
calibration decision, and descent schedule for B5-prime (spec 3b).
Sim-free: evaluators and apply-checks are injected callables (the
pose_search philosophy). All thresholds from the approved spec:
additivity keep-beam median <= 15 deg; beam width 4, depth cap 3
(4 pre-authorized on a >=10 deg wave gain).

Structural proposal rules:
  - <= 1 deep op (reverse_deep/sink) per sequence, deep op FIRST
    (mirrors shaping.apply_display_ops' law -- refused otherwise).
  - at most one op per SITE per sequence: the additive predictor sums
    measured single-op deltas, which is meaningless for two ops stacked
    on one flap (plan-level pin, 2026-07-12).
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field

import numpy as np

GROUPS = ("front", "back", "head")
DEEP_KINDS = ("reverse_deep", "sink")


class CouplingError(ValueError):
    pass


def _fmt(x):
    return f"{float(x):g}"


def cell_key(site, kind, theta, frac, f2=None) -> str:
    tail = f"|{_fmt(f2)}" if f2 is not None else ""
    return f"{site}|{kind}|{_fmt(theta)}|{_fmt(frac)}{tail}"


def seq_id(keys) -> str:
    return " + ".join(keys)


@dataclass
class CouplingRow:
    gate: str                 # gate0|gate1|gate1_baseline|gate2|gate2b|gate3
    key: str                  # cell_key or seq_id
    ops: list                 # exact op strings applied (empty = baseline)
    verdict: str              # scored | refused | parked | error
    site: str | None = None   # single-op rows only
    kind: str | None = None
    theta: float | None = None
    frac: float | None = None
    f2: float | None = None
    seq: list | None = None   # sequence rows: ordered cell keys
    angles: dict | None = None
    per_leaf: dict | None = None
    total: float | None = None
    delta_total: float | None = None
    delta_groups: dict | None = None
    predicted_total: float | None = None   # gate2 rows: what predict said
    disp: float | None = None
    attempts: list = field(default_factory=list)
    session: str | None = None
    anchor_ok: bool | None = None
    note: str | None = None


class CouplingTable:
    """Append-only JSONL row store with resume support. A killed run
    loses nothing: every row is flushed on append."""

    def __init__(self, path: str | None):
        self.path = path
        self.rows: list[CouplingRow] = []
        if path and os.path.exists(path):
            with open(path) as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        self.rows.append(CouplingRow(**json.loads(line)))

    def append(self, row: CouplingRow):
        self.rows.append(row)
        if self.path:
            with open(self.path, "a") as fh:
                fh.write(json.dumps(asdict(row)) + "\n")
                fh.flush()

    def resume_keys(self) -> set:
        """Every key with a terminal verdict -- restarted runs skip them.
        (All four verdicts are terminal; a parked/errored CELL is recorded
        and skipped, never retried across runs -- spec Gate 1.)"""
        return {r.key for r in self.rows
                if r.verdict in ("scored", "refused", "parked", "error")}

    def scored_cells(self) -> dict:
        """Single-op scored rows by cell key (the Gate-1 product)."""
        return {r.key: r for r in self.rows
                if (r.verdict == "scored" and r.site is not None
                    and r.delta_groups is not None)}

    def measured_seqs(self) -> dict:
        """{tuple(seq): measured total} over scored sequence rows."""
        return {tuple(r.seq): float(r.total) for r in self.rows
                if r.verdict == "scored" and r.seq is not None
                and r.total is not None}


def predict(cells, keys, baseline_angles, targets):
    """Additive superposition (spec 3b): predicted achieved angle per
    group = baseline + sum of each op's measured delta_groups; predicted
    total = sum over groups |predicted - target|. No off-grid
    interpolation -- every key must be a scored cell."""
    pred = {g: float(baseline_angles[g]) for g in GROUPS}
    for k in keys:
        if k not in cells:
            raise CouplingError(f"predict: {k!r} is not a scored cell")
        dg = cells[k].delta_groups
        for g in GROUPS:
            pred[g] += float(dg[g])
    total = float(sum(abs(pred[g] - float(targets[g])) for g in GROUPS))
    return pred, total


def _kind_of(key):
    return key.split("|")[1]


def _site_of(key):
    return key.split("|")[0]


def propose(cells, incumbents, *, width, depth_cap, per_wave,
            baseline_angles, targets, apply_check, measured_seqs):
    """Beam expansion (spec Gate 2). incumbents: [(seq_tuple, measured
    total)] -- the empty tuple with the baseline total is a legal
    incumbent. Extends each of the top-`width` incumbents by ONE scored
    cell; deep cells may only be PREPENDED to a deep-free sequence,
    tip-local cells are APPENDED; one op per site; ranked by predicted
    total; geometry-prefiltered by apply_check(seq_tuple) -> bool
    (refused sequences never reach the sim). Returns up to per_wave NEW
    sequences."""
    seen = set(measured_seqs)
    cands = {}
    ranked_inc = sorted(incumbents, key=lambda t: t[1])[:width]
    for seq, _score in ranked_inc:
        seq = tuple(seq)
        sites = {_site_of(k) for k in seq}
        has_deep = any(_kind_of(k) in DEEP_KINDS for k in seq)
        for k in cells:
            if _site_of(k) in sites:
                continue
            if _kind_of(k) in DEEP_KINDS:
                if has_deep:
                    continue
                new = (k,) + seq            # deep op FIRST
            else:
                new = seq + (k,)
            if len(new) > depth_cap or new in seen or new in cands:
                continue
            _pred, total = predict(cells, new, baseline_angles, targets)
            cands[new] = total
    out = []
    for seq in sorted(cands, key=cands.get):
        if apply_check(seq):
            out.append(seq)
            if len(out) == per_wave:
                break
    return out


def calibration(pairs, threshold=15.0):
    """pairs: [(predicted_total, measured_total)] -> (median |err|,
    keep_beam). median <= threshold keeps the coupling-guided beam; worse
    fires the pre-pinned descent downgrade (spec Gate 2)."""
    if not pairs:
        raise CouplingError("no calibration pairs")
    errs = sorted(abs(float(p) - float(m)) for p, m in pairs)
    n = len(errs)
    med = errs[n // 2] if n % 2 else 0.5 * (errs[n // 2 - 1]
                                            + errs[n // 2])
    return med, med <= threshold


def descent_schedule(cells, sites, incumbent, top_n=6):
    """[(site, [axis])] one stage per site; the single axis per stage =
    up to top_n scored ops for that site ranked by |delta_total|, PLUS
    the incumbent's current op for that site, PLUS None (op removed).
    The incumbent being IN the axes makes regression structurally
    impossible (the slice-4 resume-regression lesson)."""
    schedule = []
    for s in sites:
        rows = sorted((r for r in cells.values()
                       if r.site == s and r.delta_total is not None),
                      key=lambda r: -abs(float(r.delta_total)))
        axis = [r.key for r in rows[:top_n]]
        inc = incumbent.get(s)
        if inc is not None and inc not in axis:
            axis.append(inc)
        axis.append(None)
        schedule.append((s, [axis]))
    return schedule


def half_step_axis(grid, value, lo=None, hi=None):
    """Refinement axis (spec Gate 2): +/- half-grid-step midpoints around
    `value`'s nearest grid cell, incumbent value ALWAYS included, open
    (lo, hi) bounds. Sorted ascending."""
    g = sorted(float(v) for v in grid)
    v = float(value)
    i = min(range(len(g)), key=lambda j: abs(g[j] - v))
    out = {v}
    if i > 0:
        out.add((g[i] + g[i - 1]) / 2.0)
    if i < len(g) - 1:
        out.add((g[i] + g[i + 1]) / 2.0)
    return sorted(x for x in out
                  if (lo is None or x > lo) and (hi is None or x < hi))


def heatmap(cells):
    """{(site, kind): {group: max |delta_group|}} -- the reported
    coupling summary (informational)."""
    out = {}
    for r in cells.values():
        cur = out.setdefault((r.site, r.kind),
                             {g: 0.0 for g in GROUPS})
        for g in GROUPS:
            cur[g] = max(cur[g], abs(float(r.delta_groups[g])))
    return out


def rank1_share(cells):
    """Rank-1 energy share of the op x group response matrix
    (informational; None when under 2 scored rows)."""
    M = np.asarray([[float(r.delta_groups[g]) for g in GROUPS]
                    for r in cells.values()], dtype=float)
    if M.shape[0] < 2:
        return None
    s = np.linalg.svd(M, compute_uv=False)
    denom = float((s ** 2).sum())
    return float(s[0] ** 2 / denom) if denom > 0 else None
```

- [ ] **Step 4: Run tests**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_pose_coupling.py -q`
Expected: 9 passed. (Fix `test_half_step_axis`'s expectations against the implementation semantics if the midpoint arithmetic disagrees — the SEMANTICS above are pinned; the test literals serve them.)

- [ ] **Step 5: Run the full suite, then commit**

Run: `cd mcp_harness && .venv/bin/python -m pytest -q` — no regressions.

```bash
git add mcp_harness/pose_coupling.py mcp_harness/tests/test_pose_coupling.py
git commit -m "feat(b5-prime): pose_coupling -- JSONL coupling table + additive predictor + structural beam proposal + calibration/descent plumbing (mock-world beam e2e)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: `probe_dog_coupling.py` — Gate 0 + Gate 1 driver

**Files:**
- Create: `mcp_harness/probe_dog_coupling.py`
- Test: extend `mcp_harness/tests/test_pose_coupling.py` (grid-constructor tests only — the driver itself is sim-bound, validated by its Gate-0/1 runs)

**Interfaces:**
- Consumes: `pose_base.NamedBase/DOG_CONFIG/QUAD_CONFIG/unique_targets/OpRefused`, `pose_coupling.*`, `sim_capture.SimSession/build_star4_base/check_capture/capture_checked/tracked_points_lifted`, `shaping.apply_display_ops`, `square_complete.complete_square`, `starhead.fox_targets`.
- Produces (probes 5/6 import these): `served(name) -> (raw, sq, served_fold)`, `dog_base() -> NamedBase`, `fox_targets_with_fallback() -> (targets, provenance)`, `open_session_with_anchor(sim) -> anchor_row_dict` (raises `CaptureError` on anchor fail), `run_cell(sim, base, targets, baseline, table, gate, site, kind, theta, frac, f2) -> CouplingRow`, `run_sequence(sim, base, targets, baseline, table, gate, seq_keys, cells) -> CouplingRow`, `baseline_from_table(table) -> (angles_mean, total_mean)`, `matrix_cells() -> list[tuple]`, `GRIDS` dict.
- Output: `mcp_harness/probe_dog_coupling.out.jsonl` (rows) + `.out.log` (uncommitted).

- [ ] **Step 1: Write the failing grid test** (append to `tests/test_pose_coupling.py`)

```python
def test_gate1_matrix_cells():
    import probe_dog_coupling as pdc
    cells = pdc.matrix_cells()
    assert len(cells) == 162
    per_site = {}
    for site, kind, theta, frac, f2 in cells:
        per_site[site] = per_site.get(site, 0) + 1
        assert theta != 90.0
        if kind in ("reverse", "outside"):
            assert 0.0 < frac < 1.0
    assert set(per_site) == set(pdc.SITES) and set(per_site.values()) == {27}
    keys = [pc.cell_key(*c[:4], c[4]) for c in cells]
    assert len(set(keys)) == 162
    # the Gate-3 drift-datum cell is in-grid
    assert ("front_v18", "reverse", 105.0, 0.5, None) in cells
```

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_pose_coupling.py::test_gate1_matrix_cells -q` — FAIL (`ModuleNotFoundError`).

- [ ] **Step 2: Write `mcp_harness/probe_dog_coupling.py`**

```python
"""probe_dog_coupling -- B5-prime Gate 0 preflight (--gate0) and Gate 1
single-op coupling matrix on the SERVED compiled dog (spec Gates 0-1).
CONTROLLER-LAUNCHED (long sim runs; ~25 s per accepted capture).
Resumable: rerunning skips every cell already holding a terminal verdict
in probe_dog_coupling.out.jsonl.

Run (from mcp_harness/):
  .venv/bin/python probe_dog_coupling.py --gate0
  .venv/bin/python probe_dog_coupling.py --chunk 45     # one Gate-1 chunk
Exit codes: 0 ok; 1 persistent park on the UNSHAPED dog (slice HALT);
2 naming ambiguity on the dog (slice HALT); 3 baseline outside the
recorded band (slice HALT); 4 anchor failure (session refused).
"""
import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pose_base                    # noqa: E402
import pose_coupling as pc          # noqa: E402
import shaping                      # noqa: E402
import sim_capture                  # noqa: E402
import square_complete              # noqa: E402
import starhead                     # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
GOLDENS = os.path.join(_HERE, "tests", "goldens")
OUT_JSONL = os.path.join(_HERE, "probe_dog_coupling.out.jsonl")
OUT_JSON = os.path.join(_HERE, "probe_dog_coupling.out.json")

# ---- pinned constants (spec Gates 0-1) --------------------------------
SITES = ["head_v25", "front_v13", "front_v18", "back_v12", "back_v16",
         "tail_v14"]
GRIDS = {
    "reverse": {"thetas": [60.0, 105.0, 142.5, 170.0],
                "fracs": [0.35, 0.5, 0.65]},
    "outside": {"thetas": [60.0, 105.0, 142.5],
                "fracs": [0.35, 0.5, 0.65]},
    "reverse_deep": {"thetas": [105.0, 170.0], "fracs": [0.5, 1.25]},
    "crimp": {"thetas": [105.0], "fracs": [0.5], "f2s": [0.35, 0.65]},
}
EXPECTED_BASELINE_TOTAL = 272.52   # recorded Gate-3 datum
BASELINE_BAND = 1.0                # HALT if any read differs by more
                                   # (10x the ~0.09 derived-drift band;
                                   # misnaming shifts by tens of degrees)
ANCHOR_BAND = (1.0, 1.6)           # star-4 anchor disp (spec Gate 0.5)
MID_CHALLENGER_AT = 81             # accepted count crossing = challenge


def matrix_cells():
    """The 162-cell Gate-1 grid, (site, kind, theta, frac, f2)."""
    cells = []
    for site in SITES:
        for kind in ("reverse", "outside", "reverse_deep"):
            g = GRIDS[kind]
            for theta in g["thetas"]:
                for frac in g["fracs"]:
                    cells.append((site, kind, theta, frac, None))
        g = GRIDS["crimp"]
        for f2 in g["f2s"]:
            cells.append((site, "crimp", g["thetas"][0], g["fracs"][0],
                          f2))
    return cells


def served(name):
    with open(os.path.join(GOLDENS, name)) as fh:
        raw = json.load(fh)
    sq = square_complete.complete_square(raw, 1.0, 1.0)
    return raw, sq, shaping.apply_display_ops(sq, [], raw=raw)


def dog_base():
    raw, sq, _srv = served("dog.fold")
    return pose_base.NamedBase(raw, sq, pose_base.DOG_CONFIG)


def fox_targets_with_fallback():
    """probe_dog_pose._fox_targets semantics: live first, recorded
    fallback (probe_angle_range.out.json), provenance always stated."""
    try:
        targets, info = starhead.fox_targets()
        return targets, {"provenance": "live (starhead.fox_targets)",
                         "info": info}
    except Exception as exc:
        rec = os.path.join(_HERE, "probe_angle_range.out.json")
        try:
            with open(rec) as fh:
                targets = json.load(fh)["fox_targets"]
            return targets, {"provenance": f"recorded {rec}"
                             f" (live failed: {exc})"}
        except Exception as exc2:
            raise sim_capture.CaptureError(
                f"fox targets UNAVAILABLE (live: {exc};"
                f" recorded: {exc2})")


def _session_id():
    return datetime.datetime.now().strftime("%Y%m%dT%H%M%S")


def open_session_with_anchor(sim, table, session):
    """Spec Gate 0.5: the star-4 anchor opens EVERY session; a failed
    anchor refuses all verdicts from that session."""
    star = sim_capture.build_star4_base()
    cap = sim.capture(star)
    _V, disp = sim_capture.check_capture(
        cap, expect_verts=len(star["vertices_coords"]))
    ok = ANCHOR_BAND[0] <= disp <= ANCHOR_BAND[1]
    table.append(pc.CouplingRow(
        gate="anchor", key=f"anchor#{session}", ops=[],
        verdict="scored" if ok else "error", disp=disp,
        session=session, anchor_ok=ok,
        note=f"star-4 anchor band {ANCHOR_BAND}"))
    if not ok:
        raise sim_capture.CaptureError(
            f"anchor disp {disp:.4f} outside {ANCHOR_BAND}")


def _measure(sim, base, targets, shaped, tgt):
    """One accepted capture -> (angles triple, per_leaf, total, disp,
    attempts). Raises CaptureError (parked propagates with 'did not
    fold' in the message)."""
    attempts = []
    cap, disp = sim_capture.capture_checked(sim, shaped, attempts)
    pts = sim_capture.tracked_points_lifted(shaped, cap, tgt)
    per_leaf, triple, _hyp = base.angles_of(pts)
    if triple is None:
        raise sim_capture.CaptureError("angle triple unmeasurable"
                                       " (target dropped post-shape?)")
    import pose_target
    total = pose_target.angle_error(triple, targets)
    return (triple, {f"v{v}": a for v, a in per_leaf.items()},
            float(total), disp, attempts)


def baseline_from_table(table):
    rows = [r for r in table.rows
            if r.gate == "gate0" and r.verdict == "scored"
            and r.key.startswith("baseline")]
    if not rows:
        raise sim_capture.CaptureError("no gate0 baseline rows -- run"
                                       " --gate0 first")
    angles = {g: float(sum(r.angles[g] for r in rows) / len(rows))
              for g in pc.GROUPS}
    total = float(sum(r.total for r in rows) / len(rows))
    return angles, total


def run_cell(sim, base, targets, baseline, table, gate,
             site, kind, theta, frac, f2, session):
    """One Gate-1 cell -> appended CouplingRow (never raises on a cell
    verdict; only session-level errors propagate)."""
    angles0, total0 = baseline
    key = pc.cell_key(site, kind, theta, frac, f2)
    common = dict(gate=gate, key=key, site=site, kind=kind, theta=theta,
                  frac=frac, f2=f2, session=session)
    try:
        ops = base.site_op(site, kind, theta, frac, f2)
    except pose_base.PoseBaseError as exc:
        row = pc.CouplingRow(ops=[], verdict="refused",
                             note=f"construction: {exc}", **common)
        table.append(row)
        return row
    try:
        shaped = base.apply_strict(ops)
    except pose_base.OpRefused as exc:
        row = pc.CouplingRow(ops=ops, verdict="refused",
                             note=str(exc), **common)
        table.append(row)
        return row
    tgt, dropped = pose_base.unique_targets(shaped, base.targets)
    try:
        triple, per_leaf, total, disp, attempts = _measure(
            sim, base, targets, shaped, tgt)
    except sim_capture.CaptureError as exc:
        verdict = ("parked" if "did not fold" in str(exc) else "error")
        row = pc.CouplingRow(ops=ops, verdict=verdict, note=str(exc),
                             **common)
        table.append(row)
        return row
    row = pc.CouplingRow(
        ops=ops, verdict="scored", angles=triple, per_leaf=per_leaf,
        total=total, delta_total=total - total0,
        delta_groups={g: triple[g] - angles0[g] for g in pc.GROUPS},
        disp=disp, attempts=attempts,
        note=f"targets_dropped: {dropped}" if dropped else None,
        **common)
    table.append(row)
    return row


def run_sequence(sim, base, targets, baseline, table, gate, seq_keys,
                 cells, session, predicted_total=None):
    """One measured SEQUENCE (Gate 2/2b/3) -> appended CouplingRow."""
    angles0, total0 = baseline
    ops = []
    for k in seq_keys:
        r = cells[k]
        ops.extend(r.ops)
    key = pc.seq_id(list(seq_keys))
    common = dict(gate=gate, key=key, seq=list(seq_keys),
                  session=session, predicted_total=predicted_total)
    try:
        shaped = base.apply_strict(ops)
    except pose_base.OpRefused as exc:
        row = pc.CouplingRow(ops=ops, verdict="refused", note=str(exc),
                             **common)
        table.append(row)
        return row
    tgt, dropped = pose_base.unique_targets(shaped, base.targets)
    try:
        triple, per_leaf, total, disp, attempts = _measure(
            sim, base, targets, shaped, tgt)
    except sim_capture.CaptureError as exc:
        verdict = ("parked" if "did not fold" in str(exc) else "error")
        row = pc.CouplingRow(ops=ops, verdict=verdict, note=str(exc),
                             **common)
        table.append(row)
        return row
    row = pc.CouplingRow(
        ops=ops, verdict="scored", angles=triple, per_leaf=per_leaf,
        total=total, delta_total=total - total0,
        delta_groups={g: triple[g] - angles0[g] for g in pc.GROUPS},
        disp=disp, attempts=attempts,
        note=f"targets_dropped: {dropped}" if dropped else None,
        **common)
    table.append(row)
    return row


def gate0(table):
    base = dog_base()
    print(f"dog naming: grouping {json.dumps(base.grouping)}")
    print(f"ambiguities ({base.ambiguity_count}): {base.ambiguities}")
    if base.ambiguity_count != 0:
        print("GATE 0 HALT: naming ambiguity on the dog")
        return 2
    targets, prov = fox_targets_with_fallback()
    print(f"fox targets ({prov['provenance']}): {json.dumps(targets)}")

    # dry quad naming feasibility (0 captures) -- arms/disarms Gate 2b
    qraw, qsq, _ = served("quad.fold")
    qb = pose_base.NamedBase(qraw, qsq, pose_base.QUAD_CONFIG)
    armed = qb.ambiguity_count == 0
    print(f"quad dry naming: ambiguities {qb.ambiguity_count}"
          f" {qb.ambiguities} -> Gate 2b {'ARMED' if armed else 'DISARMED'}")
    table.append(pc.CouplingRow(
        gate="gate0", key="quad_dry_naming", ops=[],
        verdict="scored" if armed else "error",
        note=json.dumps({"grouping": qb.grouping,
                         "ambiguities": qb.ambiguities})))

    session = _session_id()
    _r, _s, srv = served("dog.fold")
    import pose_target
    with sim_capture.SimSession() as sim:
        open_session_with_anchor(sim, table, session)
        for k in range(3):
            tgt, _dropped = pose_base.unique_targets(srv, base.targets)
            try:
                triple, per_leaf, total, disp, attempts = _measure(
                    sim, base, targets, srv, tgt)
            except sim_capture.CaptureError as exc:
                if "did not fold" in str(exc):
                    print(f"GATE 0 HALT: unshaped dog persistent park"
                          f" ({exc})")
                    table.append(pc.CouplingRow(
                        gate="gate0", key=f"baseline#{k}", ops=[],
                        verdict="parked", note=str(exc),
                        session=session))
                    return 1
                raise
            print(f"baseline read {k}: total {total:.4f}"
                  f" (disp {disp:.4f}) angles {json.dumps(triple)}")
            table.append(pc.CouplingRow(
                gate="gate0", key=f"baseline#{k}", ops=[],
                verdict="scored", angles=triple, per_leaf=per_leaf,
                total=total, disp=disp, attempts=attempts,
                session=session))
            if abs(total - EXPECTED_BASELINE_TOTAL) > BASELINE_BAND:
                print(f"GATE 0 HALT: baseline {total:.4f} outside"
                      f" {EXPECTED_BASELINE_TOTAL} +/- {BASELINE_BAND}")
                return 3
    angles0, total0 = baseline_from_table(table)
    print(f"GATE 0 PASS: baseline mean total {total0:.4f},"
          f" angles {json.dumps(angles0)}")
    return 0


def gate1(table, chunk):
    base = dog_base()
    if base.ambiguity_count != 0:
        print("HALT: naming ambiguity")
        return 2
    targets, _prov = fox_targets_with_fallback()
    baseline = baseline_from_table(table)
    done = table.resume_keys()
    todo = [c for c in matrix_cells()
            if pc.cell_key(*c[:4], c[4]) not in done]
    print(f"gate1: {len(todo)} cells remaining of 162")
    session = _session_id()
    accepted = sum(1 for r in table.rows
                   if r.gate == "gate1" and r.verdict == "scored")
    challenged = any(r.gate == "gate1_baseline" for r in table.rows)
    _r, _s, srv = served("dog.fold")
    with sim_capture.SimSession() as sim:
        open_session_with_anchor(sim, table, session)
        this_run = 0
        for cell in todo:
            row = run_cell(sim, base, targets, baseline, table, "gate1",
                           *cell, session=session)
            print(f"{row.key}: {row.verdict}"
                  + (f" dTotal {row.delta_total:+.4f}"
                     if row.verdict == "scored" else f" ({row.note})"))
            if row.verdict in ("scored", "parked", "error"):
                this_run += 1          # captures consumed (refusals free)
            if row.verdict == "scored":
                accepted += 1
            if accepted >= MID_CHALLENGER_AT and not challenged:
                tgt, _d = pose_base.unique_targets(srv, base.targets)
                triple, per_leaf, total, disp, attempts = _measure(
                    sim, base, targets, srv, tgt)
                table.append(pc.CouplingRow(
                    gate="gate1_baseline", key="mid_challenger", ops=[],
                    verdict="scored", angles=triple, total=total,
                    disp=disp, attempts=attempts, session=session,
                    note=f"vs gate0 mean {baseline[1]:.4f}"))
                print(f"mid-matrix challenger: {total:.4f}"
                      f" (gate0 mean {baseline[1]:.4f})")
                challenged = True
                this_run += 1
            if this_run >= chunk:
                print(f"chunk limit {chunk} reached -- rerun to resume")
                break
    _summarize(table, baseline)
    return 0


def _summarize(table, baseline):
    cells = table.scored_cells()
    improvers = sorted((r for r in cells.values()),
                       key=lambda r: r.delta_total)
    big = [r for r in cells.values() if abs(r.delta_total) >= 10.0]
    neg = [r for r in cells.values() if r.delta_total <= -10.0]
    out = {
        "scored": len(cells),
        "refused": sum(1 for r in table.rows if r.verdict == "refused"),
        "parked": sum(1 for r in table.rows if r.verdict == "parked"),
        "error": sum(1 for r in table.rows if r.verdict == "error"),
        "baseline_mean_total": baseline[1],
        "abs_ge_10": len(big), "improvers_le_minus10": len(neg),
        "gate1_pass": len(big) >= 8 and len(neg) >= 1,
        "top10": [{"key": r.key, "delta_total": r.delta_total,
                   "delta_groups": r.delta_groups}
                  for r in improvers[:10]],
        "heatmap": {f"{s}|{k}": v
                    for (s, k), v in pc.heatmap(cells).items()},
        "rank1_share": pc.rank1_share(cells),
        "drift_datum": next(
            (r.delta_groups for r in cells.values()
             if r.key == "front_v18|reverse|105|0.5"), None),
    }
    with open(OUT_JSON, "w") as fh:
        json.dump(out, fh, indent=1)
    print(json.dumps({k: out[k] for k in
                      ("scored", "refused", "parked", "error",
                       "abs_ge_10", "improvers_le_minus10",
                       "gate1_pass", "rank1_share")}, indent=1))
    print(f"wrote {OUT_JSON}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gate0", action="store_true")
    ap.add_argument("--chunk", type=int, default=45)
    args = ap.parse_args()
    table = pc.CouplingTable(OUT_JSONL)
    try:
        return gate0(table) if args.gate0 else gate1(table, args.chunk)
    except sim_capture.CaptureError as exc:
        if "anchor" in str(exc):
            print(f"SESSION REFUSED: {exc}")
            return 4
        raise


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Run the grid test + full suite**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_pose_coupling.py -q` — all pass (grid test included).
Run: `cd mcp_harness && .venv/bin/python -m pytest -q` — no regressions.

- [ ] **Step 4: Commit**

```bash
git add mcp_harness/probe_dog_coupling.py mcp_harness/tests/test_pose_coupling.py
git commit -m "feat(b5-prime): probe_dog_coupling -- Gate 0 preflight + resumable Gate 1 matrix driver (162-cell grid pinned by test)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: CONTROLLER — Gate 0 run + checkpoint

**CONTROLLER TASK — do not dispatch to a subagent** (sim runs are orphan-killed under subagents). ~10 captures, ~5 min.

- [ ] **Step 1: Tripwire re-run**

Run: `cd mcp_harness && .venv/bin/python probe_dog_folds.py 2>&1 | tee probe_dog_folds.rerun.out.log` (foreground, ~2–3 min).
Expected: `dog: maxDisplacement ... -> PASS`. PERSISTENT park (3/3) → **slice HALT**: stop all tasks, write the finding to the ledger, report to the user (kick-hardening reroute).

- [ ] **Step 2: Gate 0 probe**

Run: `cd mcp_harness && .venv/bin/python probe_dog_coupling.py --gate0 2>&1 | tee probe_dog_coupling.gate0.out.log`
Expected: exit 0, `GATE 0 PASS: baseline mean total ~272.5`. Exit 1/2/3 → **slice HALT** per the probe's printed reason; report to the user.

- [ ] **Step 3: Checkpoint record**

Append to `.superpowers/sdd/progress.md`: baseline mean + 3 reads, quad Gate-2b ARMED/DISARMED, captures consumed. Decide Gate-2b arming now and record it.

---

### Task 6: CONTROLLER — Gate 1 chunked runs + verdict

**CONTROLLER TASK.** ≤162 accepted captures + anchors + 1 challenger; ~4 chunks × ~45 ≈ 70–120 min each. Launch each chunk foreground with a generous timeout or `nohup`:

- [ ] **Step 1: Run chunks until the matrix is complete**

```bash
cd mcp_harness && nohup .venv/bin/python probe_dog_coupling.py --chunk 45 >> probe_dog_coupling.out.log 2>&1 &
```

Monitor `probe_dog_coupling.out.jsonl` row count; rerun the same command until `gate1: 0 cells remaining of 162`. Anchor failure (exit 4) → relaunch (fresh session); repeated anchor failures → report to the user.

- [ ] **Step 2: Gate-1 verdict (pinned)**

From `probe_dog_coupling.out.json`: **PASS = `abs_ge_10 >= 8` AND `improvers_le_minus10 >= 1`.** Else **HALT** → B5 re-capped with compiled-base evidence: skip to Task 10 (handoff documents the measured NO — a successful slice outcome). Report the heatmap, rank-1 share, and the drift datum (re-measured front_v18|reverse|105|0.5 vs recorded −3.02/+74.05/+47.15) either way.

- [ ] **Step 3: Checkpoint record** in the ledger: verdict, capture count vs the ~170 ceiling, top-10 table.

---

### Task 7: `probe_dog_beam.py` — Gate 2 driver

**Files:**
- Create: `mcp_harness/probe_dog_beam.py`
- Test: none new (all decision logic already unit-tested in `pose_coupling`; this driver is thin orchestration, validated by its run)

**Interfaces:**
- Consumes: everything Task 4 produces (`import probe_dog_coupling as pdc`), `pose_coupling`, `pose_search.coordinate_descent`.
- Output: `mcp_harness/probe_dog_beam.out.jsonl` / `.out.json` / `.out.log`.

- [ ] **Step 1: Write `mcp_harness/probe_dog_beam.py`**

```python
"""probe_dog_beam -- B5-prime Gate 2: whole-pose search on the served
dog (spec Gate 2). CONTROLLER-LAUNCHED. Resumable: measured sequences
are reloaded from probe_dog_beam.out.jsonl and never re-captured.

Flow: wave 0 = top-8 predicted pairs (= additivity calibration; median
|pred - meas| <= 15 keeps the beam, else the pre-pinned DOWNGRADE to
incumbent-safe coordinate descent). Beam: width 4, ~10 seqs/wave, depth
cap 3 (4 pre-authorized on a >=10 deg wave gain); stop on wave gain
< 10 deg or the ~130-capture gate budget. Refinement: +/- half-grid-step
per op of the best sequence, incumbent always in the axes.
PASS bar: best measured total < 144.34 (= 154.34 - 10).

Run: cd mcp_harness && .venv/bin/python probe_dog_beam.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pose_base                    # noqa: E402
import pose_coupling as pc          # noqa: E402
import probe_dog_coupling as pdc    # noqa: E402
import sim_capture                  # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
OUT_JSONL = os.path.join(_HERE, "probe_dog_beam.out.jsonl")
OUT_JSON = os.path.join(_HERE, "probe_dog_beam.out.json")

PASS_BAR = 144.34          # 154.34 recorded single-op datum - 10 margin
WIDTH, PER_WAVE, DEPTH, DEPTH_MAX = 4, 10, 3, 4
WAVE_GAIN_MIN = 10.0
CAL_PAIRS = 8
BUDGET = 130               # accepted-capture ceiling for this gate


def _apply_check(base, cells):
    def check(seq):
        ops = []
        for k in seq:
            ops.extend(cells[k].ops)
        try:
            base.apply_strict(ops)
            return True
        except pose_base.OpRefused:
            return False
    return check


def main():
    g1 = pc.CouplingTable(pdc.OUT_JSONL)     # read-only source
    table = pc.CouplingTable(OUT_JSONL)      # this gate's rows
    base = pdc.dog_base()
    assert base.ambiguity_count == 0, base.ambiguities
    targets, _prov = pdc.fox_targets_with_fallback()
    baseline = pdc.baseline_from_table(g1)
    angles0, total0 = baseline
    cells = g1.scored_cells()
    check = _apply_check(base, cells)

    measured = {(): total0}
    measured.update(g1.measured_seqs())      # none expected, but honest
    for k, r in cells.items():
        measured[(k,)] = float(r.total)      # gate-1 singles ARE measured
    measured.update(table.measured_seqs())   # resume this gate's rows

    def incumbents():
        return sorted(measured.items(), key=lambda t: t[1])[:WIDTH]

    def best():
        return incumbents()[0]

    captures = sum(1 for r in table.rows
                   if r.verdict in ("scored", "parked", "error"))
    session = pdc._session_id()
    summary = {"baseline_total": total0, "pass_bar": PASS_BAR,
               "waves": [], "path": None}
    with sim_capture.SimSession() as sim:
        pdc.open_session_with_anchor(sim, table, session)

        def measure_seq(seq, gate, pred=None):
            nonlocal captures
            row = pdc.run_sequence(sim, base, targets, baseline, table,
                                   gate, list(seq), cells, session,
                                   predicted_total=pred)
            if row.verdict in ("scored", "parked", "error"):
                captures += 1
            if row.verdict == "scored":
                measured[tuple(seq)] = float(row.total)
            print(f"{gate} {row.key}: {row.verdict}"
                  + (f" total {row.total:.4f}"
                     f" (pred {pred if pred is None else round(pred, 2)})"
                     if row.verdict == "scored" else f" ({row.note})"))
            return row

        # ---- wave 0: top-8 predicted pairs = additivity calibration ---
        cal_rows = [r for r in table.rows if r.gate == "gate2_cal"]
        if len([r for r in cal_rows if r.verdict != "refused"]) \
                < CAL_PAIRS:
            singles = sorted(((k,) for k in cells),
                             key=lambda s: cells[s[0]].total)
            pair_inc = [(s, measured[s]) for s in singles[:WIDTH]]
            pairs = pc.propose(cells, pair_inc, width=WIDTH,
                               depth_cap=2, per_wave=CAL_PAIRS,
                               baseline_angles=angles0, targets=targets,
                               apply_check=check,
                               measured_seqs=set(measured))
            for seq in pairs:
                _p, pred = pc.predict(cells, seq, angles0, targets)
                measure_seq(seq, "gate2_cal", pred)
        cal_pairs = [(r.predicted_total, r.total) for r in table.rows
                     if r.gate == "gate2_cal" and r.verdict == "scored"]
        med, keep_beam = pc.calibration(cal_pairs)
        summary["calibration"] = {"median_abs_err": med,
                                  "keep_beam": keep_beam,
                                  "pairs": len(cal_pairs)}
        print(f"calibration: median |pred-meas| {med:.4f} ->"
              f" {'BEAM' if keep_beam else 'DESCENT DOWNGRADE'}")

        if keep_beam:
            summary["path"] = "beam"
            depth = DEPTH
            prev_best = best()[1]
            while captures < BUDGET:
                seqs = pc.propose(cells, incumbents(), width=WIDTH,
                                  depth_cap=depth, per_wave=PER_WAVE,
                                  baseline_angles=angles0,
                                  targets=targets, apply_check=check,
                                  measured_seqs=set(measured))
                if not seqs:
                    print("no new proposals -- stopping")
                    break
                for seq in seqs:
                    if captures >= BUDGET:
                        break
                    _p, pred = pc.predict(cells, seq, angles0, targets)
                    measure_seq(seq, "gate2_wave", pred)
                gain = prev_best - best()[1]
                summary["waves"].append({"gain": gain,
                                         "best": best()[1],
                                         "captures": captures})
                print(f"wave done: best {best()[1]:.4f}"
                      f" gain {gain:.4f}")
                if gain >= WAVE_GAIN_MIN:
                    depth = DEPTH_MAX      # pre-authorized depth 4
                else:
                    print(f"wave gain {gain:.4f} < {WAVE_GAIN_MIN}"
                          " -- stopping beam")
                    break
                prev_best = best()[1]
        else:
            summary["path"] = "descent"
            # incumbent-safe coordinate descent over site-op choices
            best_seq = best()[0]
            inc_by_site = {k.split("|")[0]: k for k in best_seq}
            sched = pc.descent_schedule(cells, pdc.SITES, inc_by_site)
            import pose_search

            def factory(site, fitted):
                def evaluate(params):
                    choice = params[0]
                    seq = tuple(v[0] for s, v in sorted(fitted.items())
                                if v and v[0] is not None and s != site)
                    if choice is not None:
                        seq = seq + (choice,)
                    # deep-first re-order + site exclusivity hold by
                    # construction (one op per site stage)
                    deep = tuple(k for k in seq
                                 if k.split("|")[1] in pc.DEEP_KINDS)
                    tips = tuple(k for k in seq if k not in deep)
                    if len(deep) > 1:
                        return float("inf")
                    seq = deep + tips
                    if seq == ():
                        return total0
                    if tuple(seq) in measured:
                        return measured[tuple(seq)]
                    if captures >= BUDGET or not check(seq):
                        return float("inf")
                    row = measure_seq(seq, "gate2_descent")
                    return (float(row.total)
                            if row.verdict == "scored" else float("inf"))
                return evaluate

            res = pose_search.coordinate_descent(factory, sched)
            summary["descent_fitted"] = {s: v for s, v in
                                         res.fitted.items()}

        # ---- refinement: +/- half-grid-step on the best sequence ------
        best_seq, best_total = best()
        summary["pre_refine_best"] = {"seq": list(best_seq),
                                      "total": best_total}
        for i, k in enumerate(best_seq):
            if captures >= BUDGET:
                break
            site, kind, theta_s, frac_s = k.split("|")[:4]
            f2 = float(k.split("|")[4]) if kind == "crimp" else None
            theta, frac = float(theta_s), float(frac_s)
            g = pdc.GRIDS[kind]
            for axis, cur, grid, lo, hi in (
                    ("theta", theta, g["thetas"], 0.0, 180.0),
                    ("frac", frac, g["fracs"], 0.0,
                     None if kind == "reverse_deep" else 1.0)):
                for val in pc.half_step_axis(grid, cur, lo=lo, hi=hi):
                    if val == cur or captures >= BUDGET:
                        continue
                    th, fr = ((val, frac) if axis == "theta"
                              else (theta, val))
                    nk = pc.cell_key(site, kind, th, fr, f2)
                    if nk not in cells:
                        # measure the off-grid single first so the
                        # sequence row composes from measured cells
                        row = pdc.run_cell(sim, base, targets, baseline,
                                           table, "gate2_refine_cell",
                                           site, kind, th, fr, f2,
                                           session=session)
                        if row.verdict in ("scored", "parked", "error"):
                            captures += 1
                        if row.verdict != "scored":
                            continue
                        cells[nk] = row
                    seq = tuple(best_seq[:i] + (nk,) + best_seq[i + 1:])
                    if seq in measured:
                        continue
                    if check(seq):
                        measure_seq(seq, "gate2_refine")
        best_seq, best_total = best()

    summary["best"] = {"seq": list(best_seq), "total": best_total,
                       "ops": [op for k in best_seq
                               for op in cells[k].ops]
                       if all(k in cells for k in best_seq) else None,
                       "gate2_pass": best_total < PASS_BAR}
    summary["captures"] = captures
    with open(OUT_JSON, "w") as fh:
        json.dump(summary, fh, indent=1)
    print(json.dumps(summary["best"], indent=1))
    print(f"vs unshaped {total0:.2f} / single-op datum 154.34 /"
          f" bar {PASS_BAR}")
    print(f"wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Implementation note (not optional): the refinement loop composes sequence rows only from MEASURED cells so `run_sequence`/`predict` invariants hold; an off-grid refinement cell is measured as a `gate2_refine_cell` single first. The descent branch's `fitted` values are 1-tuples `(cell_key_or_None,)` because `pose_search.grid_search` iterates the cartesian product of the single axis.

- [ ] **Step 2: Sanity-run the module import + lints**

Run: `cd mcp_harness && .venv/bin/python -c "import probe_dog_beam"` — imports cleanly (no sim started at import).
Run: `cd mcp_harness && .venv/bin/python -m pytest -q` — no regressions.

- [ ] **Step 3: Commit**

```bash
git add mcp_harness/probe_dog_beam.py
git commit -m "feat(b5-prime): probe_dog_beam -- Gate 2 calibration wave + beam/descent + half-step refinement driver

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 8: CONTROLLER — Gate 2 run + verdict

**CONTROLLER TASK.** ~130 accepted captures ≈ 55 min–1.5 h.

- [ ] **Step 1:** `cd mcp_harness && nohup .venv/bin/python probe_dog_beam.py >> probe_dog_beam.out.log 2>&1 &` — monitor the JSONL; rerun to resume after any crash/anchor failure.
- [ ] **Step 2:** Verdict from `probe_dog_beam.out.json`: **PASS = best total < 144.34**. Record informational deltas (vs best Gate-1 single, vs 272.52, per-group residuals), which path ran (beam vs descent downgrade) and why.
- [ ] **Step 3:** Ledger checkpoint + 2 baseline challengers if the budget allows (rerun `--gate0`-style unshaped reads are acceptable via `probe_dog_coupling.py --gate0`? NO — that would rewrite gate0 rows; instead note: the beam driver's session anchor + Gate-3's winner re-measurement serve as the challenge discipline here; record the decision).

---

### Task 9: `probe_quad_recipe.py` + CONTROLLER Gate 2b run (conditional)

**Skip entirely if Gate 0 DISARMED quad naming — record "unmeasurable on quad" and move on (budget returns to Gate 2).**

**Files:**
- Create: `mcp_harness/probe_quad_recipe.py`

**Interfaces:** consumes Task 4's helpers; own outputs `probe_quad_recipe.out.jsonl/.out.json/.out.log`.

- [ ] **Step 1: Write `mcp_harness/probe_quad_recipe.py`**

```python
"""probe_quad_recipe -- B5-prime Gate 2b (informational): does the dog's
coupling structure generalize to the served quad? Conditional on the
Gate-0 dry naming check (run only if ARMED). CONTROLLER-LAUNCHED.

Mini-matrix: reverse-only, theta {60, 105, 170} x frac {0.35, 0.65} x
<= 6 nameable sites (<= 36 accepted ceiling) + quad unshaped baseline x2
+ ONE beam wave of top-6 predicted pairs (one more wave pre-authorized
iff wave 1 improved the best total by >= 10 deg). Same fox targets; the
tail-drop rule applies if a tail names. Verdict (no hard gate):
generalizes | dog-specific | unmeasurable.

Run: cd mcp_harness && .venv/bin/python probe_quad_recipe.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pose_base                    # noqa: E402
import pose_coupling as pc          # noqa: E402
import probe_dog_coupling as pdc    # noqa: E402
import sim_capture                  # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
OUT_JSONL = os.path.join(_HERE, "probe_quad_recipe.out.jsonl")
OUT_JSON = os.path.join(_HERE, "probe_quad_recipe.out.json")

THETAS = [60.0, 105.0, 170.0]
FRACS = [0.35, 0.65]
WAVE_SIZE = 6
WAVE_GAIN_MIN = 10.0


def main():
    raw, sq, srv = pdc.served("quad.fold")
    base = pose_base.NamedBase(raw, sq, pose_base.QUAD_CONFIG)
    if base.ambiguity_count != 0:
        print(f"UNMEASURABLE on quad: {base.ambiguities}")
        with open(OUT_JSON, "w") as fh:
            json.dump({"verdict": "unmeasurable",
                       "ambiguities": base.ambiguities}, fh, indent=1)
        return 0
    targets, prov = pdc.fox_targets_with_fallback()
    table = pc.CouplingTable(OUT_JSONL)
    session = pdc._session_id()
    with sim_capture.SimSession() as sim:
        pdc.open_session_with_anchor(sim, table, session)
        # unshaped baseline x2
        base_rows = [r for r in table.rows
                     if r.key.startswith("baseline")
                     and r.verdict == "scored"]
        for k in range(len(base_rows), 2):
            tgt, _d = pose_base.unique_targets(srv, base.targets)
            triple, per_leaf, total, disp, attempts = pdc._measure(
                sim, base, targets, srv, tgt)
            table.append(pc.CouplingRow(
                gate="gate2b", key=f"baseline#{k}", ops=[],
                verdict="scored", angles=triple, per_leaf=per_leaf,
                total=total, disp=disp, attempts=attempts,
                session=session))
            print(f"quad baseline {k}: total {total:.4f}")
        brows = [r for r in table.rows if r.key.startswith("baseline")
                 and r.verdict == "scored"]
        angles0 = {g: sum(r.angles[g] for r in brows) / len(brows)
                   for g in pc.GROUPS}
        total0 = sum(r.total for r in brows) / len(brows)
        baseline = (angles0, total0)
        # mini-matrix (resumable)
        done = table.resume_keys()
        for site in sorted(base.sites):
            for theta in THETAS:
                for frac in FRACS:
                    if pc.cell_key(site, "reverse", theta, frac) in done:
                        continue
                    row = pdc.run_cell(sim, base, targets, baseline,
                                       table, "gate2b", site, "reverse",
                                       theta, frac, None,
                                       session=session)
                    print(f"{row.key}: {row.verdict}"
                          + (f" dTotal {row.delta_total:+.4f}"
                             if row.verdict == "scored" else ""))
        cells = table.scored_cells()
        check = lambda seq: _check(base, cells, seq)   # noqa: E731
        measured = {(): total0}
        measured.update({(k,): float(r.total)
                         for k, r in cells.items()})
        measured.update(table.measured_seqs())
        best0 = min(measured.values())
        for wave in range(2):                     # wave 2 pre-authorized
            incumbents = sorted(measured.items(),
                                key=lambda t: t[1])[:4]
            seqs = pc.propose(cells, incumbents, width=4, depth_cap=2,
                              per_wave=WAVE_SIZE,
                              baseline_angles=angles0, targets=targets,
                              apply_check=check,
                              measured_seqs=set(measured))
            for seq in seqs:
                _p, pred = pc.predict(cells, seq, angles0, targets)
                row = pdc.run_sequence(sim, base, targets, baseline,
                                       table, "gate2b", list(seq),
                                       cells, session,
                                       predicted_total=pred)
                if row.verdict == "scored":
                    measured[tuple(seq)] = float(row.total)
                print(f"wave{wave} {row.key}: {row.verdict}")
            gain = best0 - min(measured.values())
            if wave == 0 and gain < WAVE_GAIN_MIN:
                break                             # no second wave
            best0 = min(measured.values())
    # verdict: compare coupling structure to the dog's (informational)
    dog_cells = pc.CouplingTable(pdc.OUT_JSONL).scored_cells()
    out = {"targets_provenance": prov, "baseline_total": total0,
           "best": min(measured.items(), key=lambda t: t[1]),
           "heatmap": {f"{s}|{k}": v for (s, k), v
                       in pc.heatmap(cells).items()},
           "rank1_share_quad": pc.rank1_share(cells),
           "rank1_share_dog": pc.rank1_share(dog_cells)}
    q, d = out["rank1_share_quad"], out["rank1_share_dog"]
    cross = any(max(abs(r.delta_groups[g]) for g in pc.GROUPS
                    if g not in r.site) >= 10.0
                for r in cells.values())
    out["verdict"] = ("generalizes" if cross else "dog-specific")
    out["verdict_basis"] = ("cross-group |delta| >= 10 deg exists on"
                            " quad" if cross else "no cross-group"
                            " response >= 10 deg on quad")
    with open(OUT_JSON, "w") as fh:
        json.dump(out, fh, indent=1, default=str)
    print(json.dumps({"verdict": out["verdict"],
                      "rank1_quad": q, "rank1_dog": d}, indent=1))
    return 0


def _check(base, cells, seq):
    ops = []
    for k in seq:
        ops.extend(cells[k].ops)
    try:
        base.apply_strict(ops)
        return True
    except pose_base.OpRefused:
        return False


if __name__ == "__main__":
    raise SystemExit(main())
```

Note on `cross`: a site key is `front_vN` etc.; "cross-group" = a ≥10° |Δ| in a group OTHER than the site's own role prefix (`g not in r.site` implements this because group names are literal substrings of site keys; tail sites count every group as cross).

- [ ] **Step 2:** `cd mcp_harness && .venv/bin/python -c "import probe_quad_recipe"` + full suite — clean.
- [ ] **Step 3: Commit**, then **CONTROLLER runs it** (`nohup ... probe_quad_recipe.py >> probe_quad_recipe.out.log 2>&1 &`, ≤45 captures ≈ 20 min) and records the verdict in the ledger.

```bash
git add mcp_harness/probe_quad_recipe.py
git commit -m "feat(b5-prime): probe_quad_recipe -- Gate 2b reverse-only generalization mini-run on the served quad (conditional)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 10: CONTROLLER — Gate 3 payoff, routing verdict, handoff

**CONTROLLER TASK.** ~5 captures.

- [ ] **Step 1: Winner ×3 re-measurement**

Write a ≤40-line inline script (scratchpad, uncommitted) that loads the best sequence from `probe_dog_beam.out.json`, rebuilds its op strings via the gate-1/2 cells, and measures it 3× in one anchored session using `pdc.run_sequence` with `gate="gate3"` appended to `probe_dog_beam.out.jsonl`. The payoff table rests on these re-measurements, not the search-time read.

- [ ] **Step 2: Payoff table + routing verdict**

Compose (in the handoff doc): best sequence op strings (product-applicable via `ide_shape_ops`), per-group achieved/target/gap from the ×3 mean, totals vs 272.52 / 154.34 / 144.34. Then EXACTLY ONE routing verdict with the measured case: (a) coupling exploitable + search converging → **B5 REOPENED**, name the next slice; (b) exploitable but plateaued above the bar / model implies unreached improvements → the measured case for the rigid-fold instrument; (c) ceiling below target → **B5 re-capped**. All three are successful outcomes.

- [ ] **Step 3: Handoff doc + spec banner**

Create `docs/superpowers/2026-07-XX-handoff-b5-prime-outcome.md` (date = actual): thesis recap, per-gate measured results, capture spend vs budget, the routing verdict + case, gotchas found, follow-ups. Update the spec's Status banner with the outcome. Commit both.

```bash
git add docs/superpowers/2026-07-XX-handoff-b5-prime-outcome.md docs/superpowers/specs/2026-07-11-b5-prime-whole-pose-design.md
git commit -m "docs(b5-prime): outcome handoff + spec status banner [routing verdict recorded]

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

- [ ] **Step 4: Final review + branch finish**

Run the full suite one last time (`cd mcp_harness && .venv/bin/python -m pytest -q` — expected: baseline + new tests, 0 failures). Then use superpowers:requesting-code-review (final whole-branch review on the most capable model, per kickoff) followed by superpowers:finishing-a-development-branch. **ASK the user before any push.**

---

## Self-Review (performed at write time)

1. **Spec coverage:** §3a → Task 1; §3c → Task 2; §3b → Task 3; Gate 0/1 + §3d driver → Tasks 4–6; Gate 2 → Tasks 7–8; Gate 2b → Task 9; Gate 3 + handoff → Task 10; §6 bookkeeping → JSONL/append/resume in Task 3 + ledger steps in controller tasks; §7 HALT semantics → probe exit codes (Task 4) + controller checkpoints; §8 testing → Tasks 1–4 test files; §9 process rules → Global Constraints. No uncovered spec requirement found.
2. **Placeholder scan:** the only elisions are the two VERBATIM-copy blocks in Task 1 (`probe_dog_pose.py:513-577`, `:318-348`) and `_turn_sins`/`_leaf_radii`/`_mirror_pairs`/`_snap_onto`/`unique_targets` — each names its exact source lines and the parity test is the oracle; that is a copy instruction, not a TBD.
3. **Type consistency:** `site_op`/`apply_strict`/`angles_of`/`unique_targets`/`capture_checked`/`tracked_points_lifted`/`cell_key`/`CouplingRow` field names match across Tasks 1→4→7→9 (checked by grep of this document).
4. **Plan-level pins introduced here (flagged, not in the spec):** one-op-per-site per sequence (additive-prediction validity); `BASELINE_BAND = 1.0`; refinement measures off-grid singles as `gate2_refine_cell` rows first. Rationale stated inline at each pin.
