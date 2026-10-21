# B5 Slice 2 — Joint-Angle Pose Fit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fit the star4-head-0.5 foldable base's per-group reverse-fold parameters to the joint angles of the committed fox mesh's skeleton, using slice 1's grid/refine search with a new frame-invariant angle objective.

**Architecture:** A pure angle-math module (`pose_target.py`) computes the same 3-angle representation `{front, back, head}` on both sides — the fox skeleton (bone vectors from node positions) and the sim capture (tracked tip/hub vertices). A probe-support module (`starhead.py`) compiles the star4-head-0.5 base, groups its 5 flaps, builds reverse ops, and turns captures into achieved angles. Two probes run the gates: `probe_angle_range.py` (fox-target sanity + per-group achievable-angle sweep) and `probe_pose_fit.py` (sequential 3-group coordinate descent with the PASS rule).

**Tech Stack:** Python 3 (mcp_harness/.venv), numpy, networkx, trimesh/skeletor (target side only), Playwright + vendored Origami Simulator (fit side), pytest for the pure module.

**Spec:** docs/superpowers/specs/2026-07-07-b5-pose-fit-slice2-design.md

## Global Constraints

- Reused **verbatim, zero changes**: `pose_search.py`, `web/server.py`, the lint path, the raw `json` frame.
- `playwright` stays in `mcp_harness/.venv` ONLY — never in `requirements*.txt`, `ci.yml`, or any pinned dep list.
- Op vocabulary: `reverse:{x},{y}:{d}:{theta}` ONLY.
- Grid axes: θ ∈ {60, 87.5, 115, 142.5, 170}, f ∈ {0.2, 0.35, 0.5, 0.65, 0.8}; 5×5 coarse + one 5×5 refine; refine-step tolerance θ ±13.75°, f ±0.075.
- Angle definition (both sides identical): each leg angle = angle(leg bone vector, HEAD bone vector), pair-averaged; head angle = angle(head bone vector, MEAN of the four leg vectors).
- Anti-vacuous guard: every capture goes through `check_capture` (DISP_GATE 0.10, NaN guard).
- `SimSession` stays HEADED by default (`PW_HEADLESS=1` opts in) — do NOT "fix" the visible browser window.
- Solver is exactly deterministic on this machine — never use 0.0 as a tolerance.
- Measure-then-pin: no pinned value that wasn't first printed by a committed probe and hand-checked.
- Long probe runs launched from subagent shells MUST use `nohup` (background shells are reaped at turn end).
- Probe output files (`.out.json`, `.out.jsonl`, `.log`) stay **uncommitted**.
- Full backend suite must stay green: `cd mcp_harness && .venv/bin/python -m pytest tests -q` (~10 min).
- Human merges every PR; ask before push/PR. No new MCP tools, agent/prompt changes, or UI work.

## File map

| File | Status | Responsibility |
|---|---|---|
| `mcp_harness/pose_target.py` | create | Pure angle math + skeleton grouping. No sim/mesh deps at import. Pytest-tested. |
| `mcp_harness/tests/test_pose_target.py` | create | Hand-derived fixtures for the pure module. |
| `mcp_harness/sim_capture.py` | modify | Add `axial_hub`, `tracked_points`; extend `__main__` anchor to print tracked points. |
| `mcp_harness/starhead.py` | create | Probe support for the star4-head-0.5 base: compile, flap grouping, op construction, capture→angles, fox target extraction. NOT in pytest (probe support, like sim_capture). |
| `mcp_harness/probe_angle_range.py` | create | Gates 1+2: fox target angles (hand-check) + per-group θ sweep → achievable ranges, best-achievable, verdict. Writes `probe_angle_range.out.json`. |
| `mcp_harness/probe_pose_fit.py` | create | Gate 3: sequential coordinate descent, JSONL log, PASS rule. |
| `docs/superpowers/2026-07-07-handoff-b5-slice2-outcome.md` | create | Outcome handoff (Task 6). |
| `docs/superpowers/specs/2026-07-07-b5-pose-fit-slice2-design.md` | modify | Status banner (Task 6). |

**Structure note (locked here):** the spec's component list put capture-side helpers in `sim_capture.py` and left the shared base/evaluator machinery implicit. That machinery (compile, grouping, ops, angles-from-capture, fox extraction) is shared by BOTH probes, so it gets its own probe-support module `starhead.py` rather than being duplicated in two probes or bloating `sim_capture.py`. Responsibilities are otherwise exactly the spec's.

## Execution notes (for the controller)

- **Decision gates:** Task 2 Step 6 (anchor + tracked points), Task 3 Step 4 (base self-check), Task 4 (gates 1+2), Task 5 (gate 3). At each, the human-readable printed numbers must be hand-checked before the next task is dispatched. A HALT/FAIL ends the slice as a documented outcome (Task 6 still runs, recording it).
- **Long runs:** Task 4's probe ≈ 16 captures ≈ 8 min; Task 5's ≈ 150 captures ≈ 65 min. Both open a visible chromium window. Run under `nohup`, watch the log file.
- Tasks 1 is pure transcription (cheapest model). Tasks 2–3 are small integrations (cheap model, sim run required). Tasks 4–5 are probe transcription + a long measured run (cheap model + nohup discipline). Task 6 is documentation.

---

### Task 1: `pose_target.py` — pure angle math (TDD)

**Files:**
- Create: `mcp_harness/pose_target.py`
- Test: `mcp_harness/tests/test_pose_target.py`

**Interfaces:**
- Consumes: nothing from this slice (numpy only; nx.Graph duck-typed via `.nodes`/`.degree`/`[]`).
- Produces (used by Tasks 3–5):
  - `PoseTargetError(ValueError)`
  - `bone_vectors(tree) -> dict[node_id, np.ndarray unit vector]`
  - `group_legs(tree, sym_pairs) -> (head_leaf, front_pair, back_pair)`
  - `angles_from_bones(head_vec, front_vecs, back_vecs) -> {"front": deg, "back": deg, "head": deg}`
  - `angle_error(achieved, target) -> float` (sum of |Δ| over the 3 keys)

Note: the spec sketched `angles_from_bones(head_vec, leg_vecs)`; the implemented signature takes the two leg groups separately because the front/back split must be known to produce the 3-angle dict. This is the locked signature.

- [ ] **Step 1: Write the failing tests**

Create `mcp_harness/tests/test_pose_target.py`:

```python
"""Hand-derived fixtures for pose_target (B5 slice 2). Every expected value
is computed by hand in the comments -- measure-then-pin applies to test
fixtures too."""
import math

import networkx as nx
import numpy as np
import pytest

import pose_target
from pose_target import PoseTargetError


def _graph(positions, edges):
    g = nx.Graph()
    for n, p in positions.items():
        g.add_node(n, pos=np.asarray(p, dtype=float))
    g.add_edges_from(edges)
    return g


def _quadruped():
    """Hips(0)--shoulders(1) spine; head(2) off shoulders; front legs (3,4)
    off shoulders; back legs (5,6) off hips. Positions chosen so every
    angle is hand-derivable."""
    positions = {
        0: (0, 0, 0),        # hips
        1: (1, 0, 0),        # shoulders
        2: (2, 0, 1),        # head tip   -> head bone (1,0,1)/sqrt(2)
        3: (1, 0.5, -1),     # front legs -> bones (0,+-0.5,-1)
        4: (1, -0.5, -1),
        5: (0, 0.5, -1),     # back legs  -> bones (0,+-0.5,-1)
        6: (0, -0.5, -1),
    }
    edges = [(0, 1), (1, 2), (1, 3), (1, 4), (0, 5), (0, 6)]
    return _graph(positions, edges)


def test_bone_vectors_unit_and_direction():
    g = _quadruped()
    b = pose_target.bone_vectors(g)
    assert set(b) == {2, 3, 4, 5, 6}          # leaves only
    # head bone: (2,0,1)-(1,0,0) = (1,0,1), normalized
    np.testing.assert_allclose(b[2], np.array([1, 0, 1]) / math.sqrt(2),
                               atol=1e-12)
    # front leg 3: (1,.5,-1)-(1,0,0) = (0,.5,-1), norm sqrt(1.25)
    np.testing.assert_allclose(b[3], np.array([0, 0.5, -1]) / math.sqrt(1.25),
                               atol=1e-12)
    for v in b.values():
        assert abs(np.linalg.norm(v) - 1.0) < 1e-12


def test_bone_vectors_zero_length_raises():
    g = _graph({0: (0, 0, 0), 1: (0, 0, 0)}, [(0, 1)])
    with pytest.raises(PoseTargetError):
        pose_target.bone_vectors(g)


def test_group_legs_head_and_front_back():
    g = _quadruped()
    head, front, back = pose_target.group_legs(g, [[3, 4], [5, 6]])
    assert head == 2
    # front pair = larger projection of (mean leaf pos - head junction)
    # onto head bone. Head junction = node 1 at (1,0,0).
    # front mean (1,0,-1): rel (0,0,-1), proj = -1/sqrt(2) ~ -0.707
    # back  mean (0,0,-1): rel (-1,0,-1), proj = -2/sqrt(2) ~ -1.414
    assert set(front) == {3, 4}
    assert set(back) == {5, 6}


def test_group_legs_wrong_pair_count_raises():
    g = _quadruped()
    with pytest.raises(PoseTargetError):
        pose_target.group_legs(g, [[3, 4]])          # only 1 pair


def test_group_legs_no_unpaired_head_raises():
    # 4 leaves, all paired -> no head leaf
    positions = {0: (0, 0, 0), 1: (1, 1, 0), 2: (1, -1, 0),
                 3: (-1, 1, 0), 4: (-1, -1, 0)}
    g = _graph(positions, [(0, 1), (0, 2), (0, 3), (0, 4)])
    with pytest.raises(PoseTargetError):
        pose_target.group_legs(g, [[1, 2], [3, 4]])


def test_angles_from_bones_hand_case():
    # head = +x. fronts at 90 deg to head; backs at 180 deg.
    head = np.array([1.0, 0, 0])
    fronts = [np.array([0, 1.0, 0]), np.array([0, -1.0, 0])]
    backs = [np.array([-1.0, 0, 0]), np.array([-1.0, 0, 0])]
    a = pose_target.angles_from_bones(head, fronts, backs)
    # front: mean(90, 90) = 90.  back: mean(180, 180) = 180.
    # mean leg = ((0,1,0)+(0,-1,0)+(-1,0,0)+(-1,0,0))/4 = (-0.5,0,0)
    # head angle = angle(+x, -x) = 180.
    assert a["front"] == pytest.approx(90.0, abs=1e-9)
    assert a["back"] == pytest.approx(180.0, abs=1e-9)
    assert a["head"] == pytest.approx(180.0, abs=1e-9)


def test_angles_from_bones_quadruped_fixture():
    g = _quadruped()
    b = pose_target.bone_vectors(g)
    a = pose_target.angles_from_bones(b[2], [b[3], b[4]], [b[5], b[6]])
    # head bone u = (1,0,1)/sqrt2; leg bone v = (0,+-.5,-1)/sqrt(1.25)
    # cos = (u.v) = (0 + 0 - 1)/(sqrt2*sqrt1.25) = -1/sqrt(2.5) ~ -0.632456
    # angle = acos(-0.632456) ~ 129.2315 deg -- same for all 4 legs.
    expect = math.degrees(math.acos(-1 / math.sqrt(2.5)))
    assert a["front"] == pytest.approx(expect, abs=1e-9)
    assert a["back"] == pytest.approx(expect, abs=1e-9)
    # mean leg = (0,0,-1)/sqrt(1.25) (y cancels); head vs (0,0,-1):
    # cos = -1/sqrt(2) -> 135 deg.
    assert a["head"] == pytest.approx(135.0, abs=1e-9)


def test_angles_from_bones_degenerate_mean_raises():
    head = np.array([1.0, 0, 0])
    # legs cancel exactly -> zero mean leg vector
    legs = [np.array([0, 1.0, 0]), np.array([0, -1.0, 0])]
    with pytest.raises(PoseTargetError):
        pose_target.angles_from_bones(head, [legs[0]], [legs[1]])


def test_angles_from_bones_empty_group_raises():
    with pytest.raises(PoseTargetError):
        pose_target.angles_from_bones(np.array([1.0, 0, 0]), [],
                                      [np.array([0, 1.0, 0])])


def test_angle_error_sum_of_abs():
    a = {"front": 90.0, "back": 100.0, "head": 45.0}
    t = {"front": 80.0, "back": 130.0, "head": 45.0}
    assert pose_target.angle_error(a, t) == pytest.approx(40.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_pose_target.py -q`
Expected: FAIL/ERROR with `ModuleNotFoundError: No module named 'pose_target'`

- [ ] **Step 3: Write the implementation**

Create `mcp_harness/pose_target.py`:

```python
"""B5 slice 2 -- pure joint-angle target machinery (spec: docs/superpowers/
specs/2026-07-07-b5-pose-fit-slice2-design.md).

Computes the frame-invariant 3-angle pose representation
{"front", "back", "head"} used on BOTH sides of the fit:
- target side: fox skeleton bone vectors (junction -> leaf, from node 'pos')
- fit side: tracked tip/hub vectors from a sim capture (starhead.py)

Deliberately import-light: numpy only. The tree argument is any nx.Graph
whose nodes carry 'pos'; skeletor/trimesh/Playwright never appear here, so
the pytest suite covers this module without heavy deps.

Angle definition (spec, verbatim): each leg angle = angle between the leg
bone vector and the HEAD bone vector (pair-averaged); head angle = angle
between the head bone vector and the MEAN of the four leg vectors.
"""
from __future__ import annotations

import numpy as np


class PoseTargetError(ValueError):
    """Degenerate skeleton or angle input -- a reportable finding, not a
    condition to guess around."""


def _unit(v, what: str) -> np.ndarray:
    v = np.asarray(v, dtype=float)
    n = float(np.linalg.norm(v))
    if n < 1e-12:
        raise PoseTargetError(f"zero-length vector: {what}")
    return v / n


def _angle_deg(u, v) -> float:
    u = _unit(u, "angle operand")
    v = _unit(v, "angle operand")
    c = float(np.clip(np.dot(u, v), -1.0, 1.0))
    return float(np.degrees(np.arccos(c)))


def bone_vectors(tree) -> dict:
    """{leaf_id: unit vector junction->leaf} for every degree-1 node.

    Each leaf's junction is its single neighbor (the tree is already
    degree-2-contracted by simplify_to_tree, so the neighbor IS the joint).
    """
    out = {}
    for n in tree.nodes:
        if tree.degree(n) == 1:
            j = next(iter(tree[n]))
            v = (np.asarray(tree.nodes[n]["pos"], dtype=float)
                 - np.asarray(tree.nodes[j]["pos"], dtype=float))
            out[n] = _unit(v, f"bone at leaf {n}")
    if not out:
        raise PoseTargetError("tree has no leaves")
    return out


def group_legs(tree, sym_pairs):
    """(head_leaf, front_pair, back_pair) from leaf symmetry pairs.

    Head = the single leaf in no symmetry pair. Front pair = the pair whose
    mean leaf position, relative to the head bone's junction, has the larger
    scalar projection onto the head bone's unit vector (i.e. the pair nearer
    the head). Exactly 2 leaf pairs + exactly 1 unpaired leaf required.
    """
    leaves = {n for n in tree.nodes if tree.degree(n) == 1}
    pairs = [tuple(p) for p in sym_pairs
             if p[0] in leaves and p[1] in leaves]
    if len(pairs) != 2:
        raise PoseTargetError(
            f"need exactly 2 leaf symmetry pairs, got {len(pairs)}")
    paired = {n for p in pairs for n in p}
    unpaired = leaves - paired
    if len(unpaired) != 1:
        raise PoseTargetError(
            f"need exactly 1 unpaired (head) leaf, got {len(unpaired)}")
    head = unpaired.pop()

    head_junction = next(iter(tree[head]))
    hpos = np.asarray(tree.nodes[head_junction]["pos"], dtype=float)
    hvec = bone_vectors(tree)[head]

    def proj(pair):
        mean = np.mean([np.asarray(tree.nodes[n]["pos"], dtype=float)
                        for n in pair], axis=0)
        return float(np.dot(mean - hpos, hvec))

    front, back = sorted(pairs, key=proj, reverse=True)
    return head, tuple(front), tuple(back)


def angles_from_bones(head_vec, front_vecs, back_vecs) -> dict:
    """The shared 3-angle representation; see module docstring.

    Inputs are normalized HERE: the target side passes unit bone vectors
    but the fit side passes raw (tip - hub) vectors of differing lengths,
    and an unnormalized mean-leg vector would silently weight long limbs.
    """
    fronts = [_unit(v, "front leg") for v in front_vecs]
    backs = [_unit(v, "back leg") for v in back_vecs]
    if not fronts or not backs:
        raise PoseTargetError("empty leg group")
    legs = fronts + backs
    mean_leg = np.mean(legs, axis=0)
    return {
        "front": float(np.mean([_angle_deg(v, head_vec) for v in fronts])),
        "back": float(np.mean([_angle_deg(v, head_vec) for v in backs])),
        "head": _angle_deg(head_vec, _unit(mean_leg, "mean leg vector")),
    }


def angle_error(achieved: dict, target: dict) -> float:
    """Search objective: sum of absolute per-key differences in degrees."""
    return float(sum(abs(float(achieved[k]) - float(target[k]))
                     for k in ("front", "back", "head")))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_pose_target.py -q`
Expected: `10 passed`

- [ ] **Step 5: Commit**

```bash
cd <repo>
git add mcp_harness/pose_target.py mcp_harness/tests/test_pose_target.py
git commit -m "feat(b5-slice2): pose_target -- pure frame-invariant joint-angle math"
```

---

### Task 2: `sim_capture.py` additions — `axial_hub` + `tracked_points`

**Files:**
- Modify: `mcp_harness/sim_capture.py`

**Interfaces:**
- Consumes: existing `CaptureError`, capture dict shape (`vertices_coords`, `flat_coords`, both length-N and 3-wide).
- Produces (used by Tasks 3–5):
  - `axial_hub(fold) -> (x, y)` — flat coords of the unique max-axial-degree vertex, 8dp-snapped; `CaptureError` on no axial edges or a tie.
  - `tracked_points(fold, cap, flat_targets) -> {name: np.ndarray(3,)}` — folded 3D positions of named flat points: each target is located by exact 8dp (x, y) match in the FOLD's own `vertices_coords`, then the captured arrays are read BY INDEX; `CaptureError` on 0 or >1 matches, count mismatch, or integrity failure.

Grounding facts (verified 2026-07-07 on `tests/goldens/star-4.fold` + a live capture): the axial (M/V) subgraph has a single hub vertex (v3 at (0.5, 0.5)) with axial degree 8; all 4 corner tips and 4 edge midpoints are axial-degree-1. The capture's arrays are index-aligned with the INPUT fold's vertices (star-4: index 3 is the hub in both), but the capture's `flat_coords` VALUES live in the simulator's own recentered/rotated scene frame (`ide-bridge.js` `getOriginalPosition()`: hub at origin, corners at ±0.7071 in the X-Z plane) — NEVER value-match fold-frame coordinates against them. Angles computed from captured vectors are frame-invariant, so the scene frame is harmless downstream.

- [ ] **Step 1: Add the two functions**

In `mcp_harness/sim_capture.py`, insert after `check_capture` (after line 145):

```python
def axial_hub(fold: dict):
    """Flat (x, y) of the axial hub: the unique vertex with maximum axial
    (M/V) degree. For star-topology bases every axial path radiates from
    the tree root's image, so max-degree identifies it; a tie means the
    base isn't the expected star shape -- raise, don't guess. 8dp-snapped
    (the slice-4 sliver lesson) so it can key tracked_points directly."""
    deg: dict = {}
    for (a, b), asn in zip(fold["edges_vertices"], fold["edges_assignment"]):
        if asn in ("M", "V"):
            deg[a] = deg.get(a, 0) + 1
            deg[b] = deg.get(b, 0) + 1
    if not deg:
        raise CaptureError("fold has no axial (M/V) edges")
    top = max(deg.values())
    hubs = [v for v, d in deg.items() if d == top]
    if len(hubs) != 1:
        raise CaptureError(f"ambiguous axial hub (degree {top}): {hubs}")
    x, y = fold["vertices_coords"][hubs[0]][:2]
    return (round(float(x), 8), round(float(y), 8))


def tracked_points(fold: dict, cap: dict, flat_targets: dict) -> dict:
    """{name: folded 3D position} for named flat-pattern points.

    Each target is located by EXACT 8dp (x, y) match in the FOLD's own
    vertices_coords (the [0,1]^2 paper frame we control), then the captured
    arrays are read BY INDEX. The sim's flat_coords live in its own
    recentered/rotated scene frame (ide-bridge getOriginalPosition; star-4
    hub comes back at the origin, corners at +-0.7071 in X-Z), so value-
    matching against them can never succeed -- index alignment between the
    input fold and the capture is what the bridge actually guarantees.

    Integrity check: pairwise distances among the tracked points' scene
    flat positions must equal the fold-frame distances up to ONE uniform
    scale -- catches any vertex reordering/dedup inside the simulator.
    0 or >1 matches, count mismatch, or integrity failure -> CaptureError."""
    fv = fold["vertices_coords"]
    V = np.asarray(cap["vertices_coords"], dtype=float)
    F = np.asarray(cap["flat_coords"], dtype=float)
    if not (len(fv) == len(V) == len(F)):
        raise CaptureError(
            f"vertex count mismatch: fold {len(fv)} vs cap {len(V)}/{len(F)}")
    index: dict = {}
    for i, p in enumerate(fv):
        key = (round(float(p[0]), 8), round(float(p[1]), 8))
        index.setdefault(key, []).append(i)
    idx = {}
    for name, (x, y) in flat_targets.items():
        key = (round(float(x), 8), round(float(y), 8))
        hits = index.get(key, [])
        if len(hits) != 1:
            raise CaptureError(
                f"tracked point {name!r} at {key}: {len(hits)} matches")
        idx[name] = hits[0]
    names = sorted(idx)
    ratios = []
    for a in range(len(names)):
        for b in range(a + 1, len(names)):
            i, j = idx[names[a]], idx[names[b]]
            df = float(np.linalg.norm(
                np.asarray(fv[i][:2], dtype=float)
                - np.asarray(fv[j][:2], dtype=float)))
            if df > 1e-9:
                ratios.append(float(np.linalg.norm(F[i] - F[j])) / df)
    if ratios and (max(ratios) - min(ratios)) > 1e-6 * max(ratios):
        raise CaptureError(
            "index-alignment integrity failed: scale ratios"
            f" {min(ratios):.8f}..{max(ratios):.8f}")
    return {name: V[i] for name, i in idx.items()}
```

- [ ] **Step 2: Extend the `__main__` anchor to print tracked points**

Replace the existing `_anchor_main` body (lines 192-202) with:

```python
def _anchor_main():
    """Driver validation against the recorded 2026-07-06 anchor, plus a
    hand-checkable tracked-points readout (B5 slice 2): the 4 corner tips
    + hub of the un-shaped star-4, folded. Expect 4 symmetric tip positions
    and the hub near the stack."""
    print(f"anchor: un-shaped squared star-4, expect maxDisp ~{ANCHOR_DISP}")
    base = build_star4_base()
    hub = axial_hub(base)
    targets = {"hub": hub,
               "tip_00": (0.0, 0.0), "tip_10": (1.0, 0.0),
               "tip_01": (0.0, 1.0), "tip_11": (1.0, 1.0)}
    with SimSession() as sim:
        cap = sim.capture(base)
        V, disp = check_capture(cap)
        print(f"  captured {len(V)} verts, maxDisplacement {disp:.4f}")
        ok = 1.0 <= disp <= 1.6
        print(f"  anchor {'PASS' if ok else 'FAIL'}"
              f" (band 1.0..1.6 around recorded {ANCHOR_DISP})")
        pts = tracked_points(base, cap, targets)
        print(f"  axial hub (flat): {hub}   [expect (0.5, 0.5)]")
        for name in sorted(pts):
            x, y, z = (float(c) for c in pts[name])
            print(f"  tracked {name}: ({x:+.4f}, {y:+.4f}, {z:+.4f})")
        return 0 if ok else 1
```

- [ ] **Step 3: Sanity-check the pure part without the sim**

Run:
```bash
cd mcp_harness && .venv/bin/python - <<'EOF'
import sim_capture
base = sim_capture.build_star4_base()
print("hub:", sim_capture.axial_hub(base))
EOF
```
Expected: `hub: (0.5, 0.5)`

- [ ] **Step 4: Run the anchor (HEADED sim — a chromium window opens; ~30 s)**

Run: `cd mcp_harness && .venv/bin/python sim_capture.py 2>&1 | grep -v "127.0.0.1\|code 404"`
Expected: anchor PASS (maxDisp in 1.0..1.6), hub `(0.5, 0.5)`, and 5 tracked lines with finite coordinates.

- [ ] **Step 5: DECISION GATE — hand-check the tracked points**

The 4 tips must be symmetric (pairwise-mirrored coordinates up to sign patterns) and clearly displaced from their flat corners; the hub must sit near the folded stack. If any tracked point failed to match or the positions are asymmetric garbage, STOP and report — the tracking approach is broken and the slice halts here.

- [ ] **Step 6: Run the existing suite subset touching sim_capture imports**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_pose_search.py tests/test_pose_target.py -q`
Expected: all pass (sim_capture is probe support, not pytest-covered; this checks nothing else broke by import).

- [ ] **Step 7: Commit**

```bash
cd <repo>
git add mcp_harness/sim_capture.py
git commit -m "feat(b5-slice2): sim_capture axial_hub + tracked_points; anchor prints tracked readout"
```

---

### Task 3: `starhead.py` — star4-head-0.5 probe support

**Files:**
- Create: `mcp_harness/starhead.py`

**Interfaces:**
- Consumes: `server._run_isolated(server._worker_compile_and_regions, nodes_json, pairs, 1.0, 1.0)` → `{"fold", "locs", ...}` (locs = `[(node_id, x, y), ...]` leaf locations); `square_complete.complete_square(fold, 1.0, 1.0)`; `shaping.apply_display_ops(fold, [op], raw=raw)` (identity return object = refused); `sim_capture.axial_hub`, `sim_capture.tracked_points`, `sim_capture.check_capture`, `sim_capture.CaptureError`; `pose_target.angles_from_bones`, `pose_target.angle_error`, `pose_target.bone_vectors`, `pose_target.group_legs`; `mesh_to_tree.load_mesh/extract_skeleton/simplify_to_tree/detect_symmetry`.
- Produces (used by Tasks 4–5):
  - `THETAS = [60.0, 87.5, 115.0, 142.5, 170.0]`, `FRACTIONS = [0.2, 0.35, 0.5, 0.65, 0.8]`, `GROUPS = ("front", "back", "head")`
  - `StarHeadBase()` — attributes `.raw`, `.sq`, `.hub`, `.tips` (`{"front": [xy, xy], "back": [xy, xy], "head": [xy]}`), `.axial` (`{xy: length}`)
  - `make_ops(base, params) -> list[str]` — `params: {group: (theta, fraction) | None}`
  - `apply_ops(base, ops) -> dict` — sequential, raises `CaptureError` on ANY refused op
  - `achieved_angles(base, shaped, cap) -> {"front","back","head"}` — `shaped` is the exact fold dict that was captured (needed for index-based tracking)
  - `fox_targets() -> (angles_dict, info_dict)` — target-side extraction from `fixtures/quadruped.glb`

- [ ] **Step 1: Write the module**

Create `mcp_harness/starhead.py`:

```python
"""B5 slice-2 probe support -- the star4-head-0.5 foldable base (the one
hull-filling animal-labeled base found by probe_hull_quad, slice 1) plus
the machinery both slice-2 probes share: compile-and-group, reverse-op
construction, capture -> achieved angles, and fox target extraction.

NOT part of the pytest suite (probe support, like sim_capture): correctness
is pinned by the __main__ self-check's printed, hand-checked numbers.

Run the self-check (compiles the base; NO sim):
  cd mcp_harness && .venv/bin/python starhead.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pose_target                  # noqa: E402
import server                       # noqa: E402
import shaping                      # noqa: E402
import sim_capture                  # noqa: E402
import square_complete              # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
FOX_GLB = os.path.join(_HERE, "fixtures", "quadruped.glb")

HEAD_LEN = 0.5
GROUPS = ("front", "back", "head")
THETAS = [60.0, 87.5, 115.0, 142.5, 170.0]
FRACTIONS = [0.2, 0.35, 0.5, 0.65, 0.8]


def _N(i, parent, length):
    return {"id": i, "parent_id": parent, "length": length}


def compile_starhead():
    """Compile star4-head-0.5 (4 unit corner legs + 0.5 head off one center
    node -- the probe_hull_quad winner). Returns (raw_fold, locs)."""
    nodes = ([_N(0, None, 0)] + [_N(i, 0, 1.0) for i in range(1, 5)]
             + [_N(5, 0, HEAD_LEN)])
    out = json.loads(server._run_isolated(
        server._worker_compile_and_regions, json.dumps(nodes), [], 1.0, 1.0))
    fold = out["fold"]
    if isinstance(fold, str):
        fold = json.loads(fold)
    return fold, out["locs"]


def _tip_axial_len(fold: dict, xy) -> float:
    """Length of the tip's first axial (M/V) segment -- the slice-1
    _tip_and_axial semantics, generalized to any tip located by flat xy."""
    V = np.asarray([p[:2] for p in fold["vertices_coords"]], dtype=float)
    d = np.linalg.norm(V - np.asarray(xy, dtype=float), axis=1)
    tip = int(np.argmin(d))
    if d[tip] > 1e-6:
        raise sim_capture.CaptureError(f"no fold vertex at tip {xy}")
    partners = [
        (a if b == tip else b)
        for (a, b), asn in zip(fold["edges_vertices"],
                               fold["edges_assignment"])
        if asn in ("M", "V") and tip in (a, b)]
    if not partners:
        raise sim_capture.CaptureError(f"tip {xy} has no axial edge")
    return float(np.linalg.norm(V[partners[0]] - V[tip]))


class StarHeadBase:
    """Compiled star4-head-0.5 with its flap grouping.

    tips: front = the 2 corner legs nearest the head tip in the flat
    pattern, back = the other 2, head = the length-0.5 flap (tree node 5).
    All flat coords 8dp-snapped so they key tracked_points directly.
    """

    def __init__(self):
        raw, locs = compile_starhead()
        sq = square_complete.complete_square(raw, 1.0, 1.0)
        if (len(sq["vertices_coords"]) != len(raw["vertices_coords"])
                or len(sq["edges_vertices"]) != len(raw["edges_vertices"])):
            raise sim_capture.CaptureError(
                "star4-head-0.5 no longer hull-fills (squaring added"
                " geometry) -- slice-1 finding no longer holds")
        self.raw, self.sq = raw, sq

        # Snap each engine-reported leaf location to the FOLD's own vertex
        # coordinate before 8dp-rounding: locs (engine) and vertices_coords
        # (export) are two float sources, and tracked_points locates targets
        # by exact 8dp match in the fold's vertices_coords. Keying everything
        # off the fold's floats kills 9th-decimal cross-source mismatches.
        V2 = np.asarray([p[:2] for p in raw["vertices_coords"]], dtype=float)

        def _snap(x, y):
            d = np.linalg.norm(V2 - np.asarray([x, y], dtype=float), axis=1)
            i = int(np.argmin(d))
            if d[i] > 1e-6:
                raise sim_capture.CaptureError(
                    f"no fold vertex at leaf location ({x}, {y})")
            return (round(float(V2[i, 0]), 8), round(float(V2[i, 1]), 8))

        loc = {int(n): _snap(float(x), float(y)) for n, x, y in locs}
        if set(loc) != {1, 2, 3, 4, 5}:
            raise sim_capture.CaptureError(f"unexpected leaf ids {set(loc)}")
        head_xy = loc[5]
        legs = sorted((loc[i] for i in range(1, 5)),
                      key=lambda p: ((p[0] - head_xy[0]) ** 2
                                     + (p[1] - head_xy[1]) ** 2))
        d1 = ((legs[1][0] - head_xy[0]) ** 2 + (legs[1][1] - head_xy[1]) ** 2)
        d2 = ((legs[2][0] - head_xy[0]) ** 2 + (legs[2][1] - head_xy[1]) ** 2)
        if abs(d1 - d2) < 1e-9:
            raise sim_capture.CaptureError(
                "front/back split ambiguous: legs 2 and 3 equidistant"
                " from the head tip")
        self.tips = {"front": legs[:2], "back": legs[2:], "head": [head_xy]}
        self.hub = sim_capture.axial_hub(raw)
        self.axial = {xy: _tip_axial_len(raw, xy)
                      for xys in self.tips.values() for xy in xys}


def make_ops(base: StarHeadBase, params: dict) -> list:
    """params: {group: (theta, fraction) or None} -> reverse ops, one per
    flap in each parameterized group (a leg pair shares its (theta, f);
    depth d = fraction * that flap's own axial length)."""
    ops = []
    for grp in GROUPS:
        tf = params.get(grp)
        if tf is None:
            continue
        theta, frac = tf
        if not (0.0 < frac < 1.0):
            raise sim_capture.CaptureError(f"fraction {frac} outside (0, 1)")
        if not (0.0 < theta <= 180.0):
            raise sim_capture.CaptureError(f"theta {theta} outside (0, 180]")
        for (x, y) in base.tips[grp]:
            d = frac * base.axial[(x, y)]
            ops.append(f"reverse:{x},{y}:{d}:{theta}")
    return ops


def apply_ops(base: StarHeadBase, ops: list) -> dict:
    """Sequential apply with STRICT refusal detection: apply_display_ops
    skips a refused op silently (returns its input object), which would let
    a partially-shaped fold be scored as if fully shaped. Applying one op
    at a time and checking object identity catches every refusal."""
    out = base.sq
    for op in ops:
        res = shaping.apply_display_ops(out, [op], raw=base.raw)
        if res is out:
            raise sim_capture.CaptureError(f"op refused: {op}")
        out = res
    return out


def achieved_angles(base: StarHeadBase, shaped: dict, cap: dict) -> dict:
    """The fit-side half of the shared angle representation: bone vector =
    folded tip - folded hub (angles_from_bones normalizes), then the SAME
    angles_from_bones as the target side. `shaped` must be the exact fold
    dict that produced `cap` (index-based tracking); tips/hub keep their
    flat coords through shaping ops, so base's targets locate in it."""
    targets = {"hub": base.hub}
    names: dict = {}
    for grp, xys in base.tips.items():
        for k, xy in enumerate(xys):
            nm = f"{grp}{k}"
            targets[nm] = xy
            names.setdefault(grp, []).append(nm)
    pts = sim_capture.tracked_points(shaped, cap, targets)
    hub = pts["hub"]

    def vec(nm):
        return np.asarray(pts[nm], dtype=float) - np.asarray(hub, dtype=float)

    return pose_target.angles_from_bones(
        vec("head0"),
        [vec(n) for n in names["front"]],
        [vec(n) for n in names["back"]])


def fox_targets():
    """Target-side extraction (runs ONCE per probe): fox mesh -> skeleton ->
    grouped bones -> the 3 target angles. PoseTargetError here is gate-1
    failing -- a reportable target-side blocker, not something to catch."""
    import mesh_to_tree
    mesh = mesh_to_tree.load_mesh(FOX_GLB)
    skel = mesh_to_tree.extract_skeleton(mesh)
    tree = mesh_to_tree.simplify_to_tree(skel)
    sym = mesh_to_tree.detect_symmetry(tree, mesh)
    head, front, back = pose_target.group_legs(tree, sym)
    bones = pose_target.bone_vectors(tree)
    angles = pose_target.angles_from_bones(
        bones[head], [bones[n] for n in front], [bones[n] for n in back])
    info = {"head_leaf": int(head),
            "front_pair": [int(n) for n in front],
            "back_pair": [int(n) for n in back],
            "n_leaves": sum(1 for n in tree.nodes if tree.degree(n) == 1),
            "sym_pairs": [[int(a), int(b)] for a, b in sym]}
    return angles, info


def _self_check() -> int:
    """No-sim self-check: compile the base, print grouping + geometry for
    hand-check (measure-then-pin: these numbers pin Task 4's assumptions)."""
    base = StarHeadBase()
    print("star4-head-0.5 compiled; squaring NO-OP confirmed")
    print(f"  hub (flat): {base.hub}")
    for grp in GROUPS:
        for xy in base.tips[grp]:
            print(f"  {grp} tip {xy}  axial {base.axial[xy]:.6f}")
    ops = make_ops(base, {"front": (115.0, 0.5)})
    print(f"  sample front ops: {ops}")
    shaped = apply_ops(base, ops)
    print(f"  sample ops applied: {len(shaped['vertices_coords'])} verts"
          f" (base {len(base.sq['vertices_coords'])})")
    return 0


if __name__ == "__main__":
    raise SystemExit(_self_check())
```

- [ ] **Step 2: Run the self-check (compiles TreeMaker; no sim; ~1 min)**

Run: `cd mcp_harness && .venv/bin/python starhead.py`
Expected output shape:
- `squaring NO-OP confirmed` (if this raises instead, the slice-1 finding broke — STOP and report)
- hub near the paper interior; 2 front tips (nearest the head tip), 2 back tips at the remaining corners, 1 head tip; all 4 leg tips at/near the 4 corners
- positive axial lengths; head axial < leg axials
- `sample ops applied` with MORE vertices than the base (the reverse fold split real geometry)

- [ ] **Step 3: DECISION GATE — hand-check the printed grouping**

Check against slice-1 knowledge: legs at the 4 corners (probe_hull_quad measured corners 4/4), head on a paper edge. Front tips must be the two corners geometrically nearest the head tip. If the grouping or axials look wrong, STOP.

- [ ] **Step 4: Commit**

```bash
cd <repo>
git add mcp_harness/starhead.py
git commit -m "feat(b5-slice2): starhead probe support -- base grouping, ops, capture->angles, fox targets"
```

---

### Task 4: `probe_angle_range.py` — gates 1 + 2

**Files:**
- Create: `mcp_harness/probe_angle_range.py`

**Interfaces:**
- Consumes: `starhead.StarHeadBase/make_ops/apply_ops/achieved_angles/fox_targets/GROUPS/THETAS`; `sim_capture.SimSession/check_capture/CaptureError`.
- Produces: `mcp_harness/probe_angle_range.out.json` (uncommitted) with keys `fox_targets`, `fox_info`, `baseline_angles`, `sweep` (per group: list of `{theta, angle, disp}`), `best_achievable` (per group: `{theta, angle, gap_to_target}`), `angle_tol` (per group), `verdict`. Task 5 REQUIRES this file.

**The gate rules (from the spec):**
- Gate 1: `fox_targets()` must succeed AND the printed angles must survive a hand sanity check vs the fox's anatomy (legs point away from the head — expect leg-vs-head angles well above 90°; head-vs-mean-legs likewise obtuse). `PoseTargetError` → exit 2 with the message.
- Gate 2: HALT if any group's achieved-angle range across the θ sweep is `< 3 * ANGLE_FLOOR` where `ANGLE_FLOOR = 1.0°` — a first-principles measurement floor (the refine grid cannot meaningfully resolve below ~1°; the deterministic solver's noise is exactly 0, which slice 1 pinned as unusable for thresholds). The controller hand-checks the printed ranges at the gate regardless of the automated verdict.

- [ ] **Step 1: Write the probe**

Create `mcp_harness/probe_angle_range.py`:

```python
"""B5 slice-2 de-risk probe (gates 1+2): can the angle objective SEE theta
on each flap group, and are the fox's target angles sane?

Per group: sweep theta over the coarse grid at f=0.5 (other groups
unshaped), record the group's OWN achieved angle. Range = max - min.
HALT if any range < 3 * ANGLE_FLOOR (1.0 deg first-principles floor --
solver noise is exactly 0.0 and slice 1 pinned that as unusable).
Also records per-group best-achievable angle (closest to the fox target
at f=0.5) and angle_tol (achieved-angle change across the adjacent theta
step at the best cell) for Task 5's PASS rule.

Run (long, HEADED sim -- a window opens; ~16 captures ~ 8 min):
  cd mcp_harness && nohup .venv/bin/python probe_angle_range.py \
      > probe_angle_range.out.log 2>&1 &
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pose_target                  # noqa: E402
import sim_capture                  # noqa: E402
import starhead                     # noqa: E402

ANGLE_FLOOR = 1.0    # degrees; see module docstring
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "probe_angle_range.out.json")


def main() -> int:
    # ---- Gate 1: fox targets (raises PoseTargetError = gate fails) ----
    try:
        targets, info = starhead.fox_targets()
    except pose_target.PoseTargetError as exc:
        print(f"GATE 1 FAIL (fox skeleton degenerate): {exc}")
        return 2
    print(f"fox targets (deg): {json.dumps(targets, indent=2)}")
    print(f"fox skeleton info: {json.dumps(info)}")
    print("hand-check: legs should point away from the head"
          " (expect obtuse leg-vs-head angles)")

    base = starhead.StarHeadBase()
    out = {"fox_targets": targets, "fox_info": info}
    with sim_capture.SimSession() as sim:
        cap = sim.capture(base.sq)
        _V, disp = sim_capture.check_capture(cap)
        baseline = starhead.achieved_angles(base, base.sq, cap)
        out["baseline_angles"] = baseline
        print(f"baseline (unshaped) angles: {baseline}  disp {disp:.4f}")

        sweep, best, tol = {}, {}, {}
        for grp in starhead.GROUPS:
            rows = []
            for theta in starhead.THETAS:
                try:
                    shaped = starhead.apply_ops(
                        base, starhead.make_ops(base, {grp: (theta, 0.5)}))
                    cap = sim.capture(shaped)
                    _V, disp = sim_capture.check_capture(cap)
                    ang = starhead.achieved_angles(base, shaped, cap)[grp]
                    rows.append({"theta": theta, "angle": ang,
                                 "disp": disp})
                    print(f"  {grp} theta={theta}: angle {ang:.4f}"
                          f" disp {disp:.4f}")
                except (sim_capture.CaptureError,
                        pose_target.PoseTargetError) as exc:
                    rows.append({"theta": theta, "angle": None,
                                 "error": str(exc)})
                    print(f"  {grp} theta={theta}: FAILED ({exc})")
            sweep[grp] = rows
            good = [r for r in rows if r.get("angle") is not None]
            if len(good) < 2:
                print(f"GATE 2 FAIL: group {grp} has <2 successful"
                      " sweep points")
                out["sweep"] = sweep
                out["verdict"] = "HALT"
                json.dump(out, open(OUT, "w"), indent=2)
                return 3
            angles = [r["angle"] for r in good]
            rng = max(angles) - min(angles)
            tgt = targets[grp]
            b = min(good, key=lambda r: abs(r["angle"] - tgt))
            i = good.index(b)
            neighbors = [good[j] for j in (i - 1, i + 1)
                         if 0 <= j < len(good)]
            tol[grp] = max(abs(n["angle"] - b["angle"]) for n in neighbors)
            best[grp] = {"theta": b["theta"], "angle": b["angle"],
                         "gap_to_target": abs(b["angle"] - tgt)}
            print(f"  {grp}: range {rng:.4f} deg, best-achievable"
                  f" {b['angle']:.4f} @ theta={b['theta']}"
                  f" (target {tgt:.4f}, gap {abs(b['angle'] - tgt):.4f},"
                  f" tol {tol[grp]:.4f})")
            sweep[grp + "_range"] = rng

    out["sweep"] = sweep
    out["best_achievable"] = best
    out["angle_tol"] = tol
    ranges = {g: sweep[g + "_range"] for g in starhead.GROUPS}
    halted = [g for g, r in ranges.items() if r < 3 * ANGLE_FLOOR]
    out["verdict"] = "HALT" if halted else "PROCEED"
    json.dump(out, open(OUT, "w"), indent=2)

    print("\n--- VERDICT ---")
    for g, r in ranges.items():
        print(f"  {g}: achievable range {r:.4f} deg"
              f" (floor {3 * ANGLE_FLOOR:.1f})")
    print(f"{out['verdict']}"
          + (f" -- groups below floor: {halted}" if halted else ""))
    return 0 if out["verdict"] == "PROCEED" else 3


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run under nohup (HEADED; ~16 captures ≈ 8 min + skeletor ~1 min)**

```bash
cd mcp_harness && nohup .venv/bin/python probe_angle_range.py \
    > probe_angle_range.out.log 2>&1 &
```
Watch: `tail -f mcp_harness/probe_angle_range.out.log` (strip http noise with `grep -v "127.0.0.1\|code 404"`).

- [ ] **Step 3: DECISION GATE — hand-check before Task 5**

1. Gate 1: the printed fox target angles must be anatomically plausible (obtuse leg-vs-head angles; no NaN; exactly 2 leg pairs + 1 unpaired head in `fox_info`). Exit 2 = slice ends here as a documented target-side blocker.
2. Gate 2: printed per-group ranges vs the 3.0° floor, hand-checked (not just the automated verdict). Exit 3 = HALT = slice ends here as a documented sensitivity failure.
3. Confirm `probe_angle_range.out.json` exists (Task 5 reads it).

- [ ] **Step 4: Commit (the probe file ONLY — not the .out/.log files)**

```bash
cd <repo>
git add mcp_harness/probe_angle_range.py
git commit -m "probe(b5-slice2): angle-range de-risk gate -- fox targets + per-group theta sweep [VERDICT + measured ranges in commit body]"
```
Amend the commit message body with the measured verdict line and per-group ranges from the log (measure-then-pin: the numbers live in git).

---

### Task 5: `probe_pose_fit.py` — gate 3, the fit itself

**Files:**
- Create: `mcp_harness/probe_pose_fit.py`

**Interfaces:**
- Consumes: everything Task 4 consumes, plus `pose_search.grid_search/refine/PoseSearchError` and `probe_angle_range.out.json` (`fox_targets`, `best_achievable`, `angle_tol`).
- Produces: `probe_pose_fit.out.jsonl` (every evaluation) + `probe_pose_fit.out.json` (final verdict), both uncommitted.

**PASS rule (from the spec, operationalized with Task 4's measurements):**
- Per group: `|fit_achieved_angle - fox_target| <= best_achievable.gap_to_target + angle_tol` (the fit must not do meaningfully worse than the crude f=0.5 sweep's best; doing better passes trivially), AND
- Total: final `angle_error` strictly < baseline (unshaped) `angle_error`.

- [ ] **Step 1: Write the probe**

Create `mcp_harness/probe_pose_fit.py`:

```python
"""B5 slice-2 main probe (gate 3): sequential 3-group coordinate descent
fitting the star4-head-0.5 base's reverse-fold (theta, fraction) per group
to the fox skeleton's target angles.

Requires probe_angle_range.out.json (Task 4 must have PROCEEDed).

Order: front -> back -> head; each group runs a 5x5 coarse grid + one 5x5
refine over (theta, fraction) with previously fitted groups held at their
refined best. Score = pose_target.angle_error(achieved, targets) -- the
TOTAL error, so cross-group coupling (legs move the mean-leg vector inside
the head angle) is scored, not ignored.

PASS = per group |achieved - target| <= sweep_gap + angle_tol (from
probe_angle_range.out.json) AND total error strictly < unshaped baseline.

Run (long, HEADED sim; ~150 captures ~ 65 min):
  cd mcp_harness && nohup .venv/bin/python probe_pose_fit.py \
      > probe_pose_fit.out.log 2>&1 &
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pose_search                  # noqa: E402
import pose_target                  # noqa: E402
import sim_capture                  # noqa: E402
import starhead                     # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
RANGE_JSON = os.path.join(_HERE, "probe_angle_range.out.json")
OUT_JSONL = os.path.join(_HERE, "probe_pose_fit.out.jsonl")
OUT_JSON = os.path.join(_HERE, "probe_pose_fit.out.json")


def main() -> int:
    if not os.path.exists(RANGE_JSON):
        print(f"missing {RANGE_JSON} -- run probe_angle_range.py first")
        return 2
    rng = json.load(open(RANGE_JSON))
    if rng.get("verdict") != "PROCEED":
        print(f"probe_angle_range verdict was {rng.get('verdict')} -- halt")
        return 2
    targets = rng["fox_targets"]
    best_ach = rng["best_achievable"]
    angle_tol = rng["angle_tol"]
    print(f"fox targets: {targets}")

    log = open(OUT_JSONL, "w")

    def jlog(**kw):
        log.write(json.dumps(kw) + "\n")
        log.flush()

    base = starhead.StarHeadBase()
    fitted: dict = {}
    with sim_capture.SimSession() as sim:
        cap = sim.capture(base.sq)
        _V, disp = sim_capture.check_capture(cap)
        baseline_angles = starhead.achieved_angles(base, base.sq, cap)
        baseline_err = pose_target.angle_error(baseline_angles, targets)
        jlog(kind="baseline", angles=baseline_angles, error=baseline_err,
             disp=disp)
        print(f"baseline angles {baseline_angles} error {baseline_err:.4f}")

        def make_evaluator(group):
            def evaluate(params):
                theta, frac = params
                p = dict(fitted)
                p[group] = (theta, frac)
                shaped = starhead.apply_ops(base, starhead.make_ops(base, p))
                cap = sim.capture(shaped)
                _V, disp = sim_capture.check_capture(cap)
                ach = starhead.achieved_angles(base, shaped, cap)
                err = pose_target.angle_error(ach, targets)
                jlog(kind="eval", group=group, theta=theta, fraction=frac,
                     disp=disp, achieved=ach, score=err)
                print(f"  eval {group} ({theta}, {frac}):"
                      f" err {err:.4f}", flush=True)
                return err
            return evaluate

        axes = [starhead.THETAS, starhead.FRACTIONS]
        results = {}
        for grp in starhead.GROUPS:
            ev = make_evaluator(grp)
            coarse = pose_search.grid_search(ev, axes)
            jlog(kind="coarse", group=grp, best=list(coarse.best_params),
                 score=coarse.best_score)
            fine = pose_search.refine(ev, axes, coarse.best_params)
            jlog(kind="fine", group=grp, best=list(fine.best_params),
                 score=fine.best_score)
            fitted[grp] = tuple(fine.best_params)
            results[grp] = {"coarse": list(coarse.best_params),
                            "coarse_score": coarse.best_score,
                            "fine": list(fine.best_params),
                            "fine_score": fine.best_score}
            print(f"{grp}: coarse {coarse.best_params}"
                  f" ({coarse.best_score:.4f}) -> fine {fine.best_params}"
                  f" ({fine.best_score:.4f})")

        # Final joint capture at all three fitted params.
        shaped = starhead.apply_ops(base, starhead.make_ops(base, fitted))
        cap = sim.capture(shaped)
        _V, disp = sim_capture.check_capture(cap)
        final_angles = starhead.achieved_angles(base, shaped, cap)
        final_err = pose_target.angle_error(final_angles, targets)
        jlog(kind="final", fitted={g: list(v) for g, v in fitted.items()},
             angles=final_angles, error=final_err, disp=disp)

    # ---- PASS rule ----
    per_group = {}
    all_ok = True
    for grp in starhead.GROUPS:
        gap = abs(final_angles[grp] - targets[grp])
        bound = best_ach[grp]["gap_to_target"] + angle_tol[grp]
        ok = gap <= bound
        per_group[grp] = {"achieved": final_angles[grp],
                          "target": targets[grp], "gap": gap,
                          "bound": bound, "ok": ok}
        all_ok = all_ok and ok
    improved = final_err < baseline_err
    passed = all_ok and improved

    verdict = {"fitted": {g: list(v) for g, v in fitted.items()},
               "results": results, "baseline_error": baseline_err,
               "final_error": final_err, "final_angles": final_angles,
               "per_group": per_group, "improved": improved,
               "passed": passed}
    json.dump(verdict, open(OUT_JSON, "w"), indent=2)
    jlog(kind="verdict", **verdict)

    print("\n--- FIT VERDICT ---")
    for grp, r in per_group.items():
        print(f"  {grp}: achieved {r['achieved']:.4f} vs target"
              f" {r['target']:.4f} (gap {r['gap']:.4f},"
              f" bound {r['bound']:.4f}) {'OK' if r['ok'] else 'MISS'}")
    print(f"  total error {final_err:.4f} vs baseline {baseline_err:.4f}"
          f" ({'improved' if improved else 'NOT improved'})")
    print("FIT " + ("PASS" if passed else "FAIL"))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run under nohup (HEADED; ~150 captures ≈ 65 min)**

```bash
cd mcp_harness && nohup .venv/bin/python probe_pose_fit.py \
    > probe_pose_fit.out.log 2>&1 &
```
Watch the JSONL grow: `wc -l mcp_harness/probe_pose_fit.out.jsonl` (expect 159 lines at completion: 1 baseline + 150 evals + 3 coarse + 3 fine + 1 final + 1 verdict).

- [ ] **Step 3: DECISION GATE — read the verdict**

`FIT PASS` (exit 0) or `FIT FAIL` (exit 1). Either is a valid slice outcome; a FAIL with clean per-group numbers is a documented finding (e.g., coordinate descent got stuck, or the head group's coupling breaks the sequential assumption). Hand-check the landscape in the JSONL for the same unimodal-basin sanity slice 1 had.

- [ ] **Step 4: Commit (probe file only)**

```bash
cd <repo>
git add mcp_harness/probe_pose_fit.py
git commit -m "probe(b5-slice2): sequential joint-angle fit vs fox skeleton [VERDICT + fitted params + errors in commit body]"
```
Amend the body with: baseline error, final error, per-group fitted (θ, f) + achieved-vs-target gaps, PASS/FAIL.

---

### Task 6: Handoff + spec banner + full suite

**Files:**
- Create: `docs/superpowers/2026-07-07-handoff-b5-slice2-outcome.md`
- Modify: `docs/superpowers/specs/2026-07-07-b5-pose-fit-slice2-design.md` (status banner)

**Interfaces:**
- Consumes: all measured numbers from Tasks 2–5's printed outputs and out.json files.
- Produces: the slice's durable record.

- [ ] **Step 1: Run the full backend suite (~10 min; use nohup from a subagent shell)**

```bash
cd mcp_harness && nohup .venv/bin/python -m pytest tests -q \
    > suite_slice2.out.log 2>&1 &
```
Expected: all pass (411+10 new = ~421 passed, 3 skipped). A failure blocks the slice from finishing — fix before proceeding.

- [ ] **Step 2: Write the handoff**

Create `docs/superpowers/2026-07-07-handoff-b5-slice2-outcome.md` with this structure, filling every bracketed value from the actual probe outputs (NO invented numbers):

```markdown
# Handoff: B5 slice 2 (joint-angle pose fit) — outcome

**Spec:** docs/superpowers/specs/2026-07-07-b5-pose-fit-slice2-design.md

## What shipped
- `mcp_harness/pose_target.py` + 10 tests — pure 3-angle representation
  {front, back, head}, shared by target and fit sides.
- `mcp_harness/sim_capture.py` — `axial_hub` + `tracked_points`
  (8dp flat-coordinate re-location; anchor run printed [tracked readout]).
- `mcp_harness/starhead.py` — star4-head-0.5 probe support
  (grouping: front tips [xy, xy], back [xy, xy], head [xy]; hub [xy];
  axials [values]).
- `probe_angle_range.py` — gates 1+2: fox targets
  {front [x], back [x], head [x]} deg; per-group achievable ranges
  [values]; verdict [PROCEED/HALT].
- `probe_pose_fit.py` — gate 3: baseline error [x], final error [x],
  fitted params [per group], per-group gaps vs bounds; FIT [PASS/FAIL].

## Findings
[The measured story: did the sequential coordinate descent close on a
real-mesh target? Which groups hit their bounds? Was the landscape
unimodal like slice 1's?]

## Slice 3 entry point
[Based on the outcome: if PASS — candidates are richer op vocabulary
(crimp for knee bends) or spined-quadruped bases; if FAIL — what the
numbers say broke (coupling? reachability?) and the cheapest probe to
answer it.]

## Gotchas carried forward
- All slice-1 gotchas still hold (headed SimSession, deterministic solver,
  nohup for subagent probes, playwright venv-only).
- [Any new ones found this slice, e.g. tracked-point collisions, fox
  skeleton quirks, coupling between head angle and leg groups.]
```

- [ ] **Step 3: Update the spec status banner**

In `docs/superpowers/specs/2026-07-07-b5-pose-fit-slice2-design.md`, change the `**Status:**` line to:
`**Status:** IMPLEMENTED [+ outcome, e.g. "— FIT PASS" or "— HALTED at gate N (see handoff)"] (handoff: docs/superpowers/2026-07-07-handoff-b5-slice2-outcome.md)`

- [ ] **Step 4: Commit**

```bash
cd <repo>
git add docs/superpowers/2026-07-07-handoff-b5-slice2-outcome.md \
        docs/superpowers/specs/2026-07-07-b5-pose-fit-slice2-design.md
git commit -m "docs(b5-slice2): outcome handoff + spec status banner"
```
