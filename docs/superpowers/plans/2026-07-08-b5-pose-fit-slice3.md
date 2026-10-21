# B5 Slice 3 — Asymmetric Star Probe + Pose Fit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Find an asymmetric 5-leaf star base whose head tip is a distinct vertex from the axial hub (un-sticking slice 2's halt), then run the slice-2 joint-angle pose fit against the fox skeleton on it.

**Architecture:** A new compile-only probe (`probe_star_asym.py`) sweeps a 20-cell (back-leg × head) grid, prints a geometric map, gates stage-1 candidates (hull no-op + head ≠ hub + separable front/back), and — only if stage 1 is empty — sim-rescues the best near-misses; it records a winner in its out.json. `starhead.py` is generalized to `(back_len, head_len)` with the front/back grouping extracted into pure, pytest-covered `pose_target.group_tips_by_head`. The two slice-2 probes (`probe_angle_range.py`, `probe_pose_fit.py`) are then built exactly per the slice-2 design, constructing their base from the recorded winner.

**Tech Stack:** Python 3 (mcp_harness/.venv), numpy, networkx, trimesh/skeletor (target side only), Playwright + vendored Origami Simulator (fit side), pytest for the pure additions.

**Spec:** docs/superpowers/specs/2026-07-08-b5-pose-fit-slice3-design.md
**Branch:** feat/b5-pose-fit-slice3 (off main 3b55531)

## Global Constraints

- Reused **verbatim, zero changes**: `pose_search.py`, `sim_capture.py` (`axial_hub`, `tracked_points` — landed in slice 2), `web/server.py`, the lint path, the raw `json` frame.
- `playwright` stays in `mcp_harness/.venv` ONLY — never in `requirements*.txt`, `ci.yml`, or any pinned dep list.
- Op vocabulary: `reverse:{x},{y}:{d}:{theta}` ONLY.
- Grid axes (fit stage): θ ∈ {60, 87.5, 115, 142.5, 170}, f ∈ {0.2, 0.35, 0.5, 0.65, 0.8}; 5×5 coarse + one 5×5 refine.
- Angle definition (both sides identical): each leg angle = angle(leg bone vector, HEAD bone vector), pair-averaged; head angle = angle(head bone vector, MEAN of the four leg vectors).
- Anti-vacuous guard: every capture goes through `check_capture` (DISP_GATE 0.10, NaN guard).
- `SimSession` stays HEADED by default (`PW_HEADLESS=1` opts in) — do NOT "fix" the visible browser window.
- Solver is exactly deterministic on this machine — never use 0.0 as a tolerance.
- Measure-then-pin: no pinned value that wasn't first printed by a committed probe and hand-checked.
- Long probe runs launched from subagent shells MUST use `nohup` (background shells are reaped at turn end).
- Probe output files (`.out.json`, `.out.jsonl`, `.out.log`) stay **uncommitted**.
- multiprocessing spawn workers (`server._run_isolated`) need a real script file as `__main__` — never stdin heredocs.
- Full backend suite must stay green: `cd mcp_harness && .venv/bin/python -m pytest tests -q` (~10 min).
- Human merges every PR; ask before push/PR. No new MCP tools, agent/prompt changes, or UI work.

## File map

| File | Status | Responsibility |
|---|---|---|
| `mcp_harness/probe_star_asym.py` | create | Base probe: 20-cell (b, h) map, stage-1 gate, stage-2 sim rescue, winner selection → `probe_star_asym.out.json`. NOT in pytest. |
| `mcp_harness/pose_target.py` | modify | Add pure `group_tips_by_head` (front/back split by distance to head tip, ambiguity guard). |
| `mcp_harness/tests/test_pose_target.py` | modify | +3 hand-derived tests for `group_tips_by_head`. |
| `mcp_harness/starhead.py` | modify | Parameterize over `(back_len, head_len)`; grouping via `pose_target.group_tips_by_head`; explicit head==hub guard; `winner_base()`; CLI-arg self-check. |
| `mcp_harness/probe_angle_range.py` | create | Gates 2+3: fox target angles (hand-check) + per-group θ sweep on the winner base → `probe_angle_range.out.json`. NOT in pytest. |
| `mcp_harness/probe_pose_fit.py` | create | Gate 4: sequential coordinate descent, JSONL log, PASS rule. NOT in pytest. |
| `docs/superpowers/2026-07-08-handoff-b5-slice3-outcome.md` | create | Outcome handoff (Task 5). |
| `docs/superpowers/specs/2026-07-08-b5-pose-fit-slice3-design.md` | modify | Status banner (Task 5). |

**Winner plumbing (locked here):** the spec left "how downstream probes learn the winning (b, h)" implicit. Decision: `probe_star_asym.py` writes a `winner` object into its out.json (deterministic rule: largest front/back split among stage-1 survivors, else among folding stage-2 rescues); `starhead.winner_base()` reads it. This matches the existing probe-chaining pattern (slice-2's `probe_pose_fit` reads `probe_angle_range.out.json`); the winner's numbers additionally land in commit-message bodies (measure-then-pin: durable in git even though out.json is uncommitted).

## Execution notes (for the controller)

- **Decision gates:** Task 1 Step 4 (map hand-check + winner pin), Task 2 Step 8 (winner-base self-check), Task 3 Step 3 (fox targets + angle ranges), Task 4 Step 3 (fit verdict). At each, the printed numbers must be hand-checked before the next task is dispatched. A HALT/FAIL ends the slice as a documented outcome (Task 5 still runs, recording it).
- **Long runs:** Task 1 ≈ 20 compiles ≈ 5 min (+ ≤3 sim captures if stage 2 triggers); Task 3 ≈ 16 captures ≈ 8 min + skeletor ~1 min; Task 4 ≈ 150 captures ≈ 65 min. Sim runs open a visible chromium window. Run under `nohup`, watch the log file.
- Task 2 is TDD on a pure function + a small refactor. Tasks 1, 3, 4 are probe transcription + measured runs. Task 5 is documentation.
- The default `StarHeadBase()` (b=1.0, h=0.5) now raises `PoseTargetError` from the grouping guard — that IS the slice-2 halt reproducer, preserved. Do not "fix" it.

---

### Task 1: `probe_star_asym.py` — the base probe (map, stage-1 gate, stage-2 rescue)

**Files:**
- Create: `mcp_harness/probe_star_asym.py`

**Interfaces:**
- Consumes: `server._run_isolated(server._worker_compile_and_regions, nodes_json, [], 1.0, 1.0)` → `{"fold", "locs", ...}` (`locs` = `[(node_id, x, y), ...]` leaf locations); `square_complete.complete_square(fold, 1.0, 1.0)`; `sim_capture.SimSession/check_capture/CaptureError` (NOT `axial_hub` — plan fix: its uniqueness assumption is symmetric-only; the probe computes the hub SET inline).
- Produces: `mcp_harness/probe_star_asym.out.json` (uncommitted) with keys `grid` (all 20 rows), `stage1` (survivor rows), `stage2` (rescue rows with `disp` or `error`), `winner` (`{"b", "h", "stage", "split", ...}` or `null`). Tasks 2–4 REQUIRE the `winner`.

Note: the tree is compiled WITHOUT symmetry pairs (`[]`), matching the proven slice-1 star compile path (`probe_hull_quad.candidates()` passed `[]` for all star cells; node LIST ORDER flips packability, so we keep the star family's proven shape: root, 4 legs, head last). Downstream grouping is distance-based, not node-id-based, so it does not care which leg ids end up front.

- [ ] **Step 1: Write the probe**

Create `mcp_harness/probe_star_asym.py`:

```python
"""B5 slice-3 base probe: sweep the asymmetric 5-leaf star family for a
fittable base -- head tip DISTINCT from the axial hub, front/back legs
distance-separable, and still foldable in the sim.

Grid: back-leg b in {0.80, 0.85, 0.90, 0.95} x head h in {0.40, 0.45,
0.50, 0.55, 0.60}; front legs pinned 1.0; no symmetry pairs (the proven
slice-1 star compile shape -- grouping downstream is distance-based).

Stage 1 (all 20 cells, compile-only): squaring NO-OP and head != hub and
front/back split unambiguous. Stage 2 (ONLY if stage 1 is empty): the
RESCUE_MAX best non-noop cells by hull gap (still head-distinct and
separable) are squared and sim-tested (disp > gate, 0 NaN) -- "squared
folds don't fold" is a measured hazard from other base families, tested
here rather than assumed.

Winner (recorded in probe_star_asym.out.json for starhead.winner_base()):
largest front/back split among stage-1 survivors, else among folding
stage-2 rescues. The printed map is hand-checked at the decision gate
regardless of the automated pick; numeric thresholds for "off-center
enough"/"split enough" are pinned FROM this map (measure-then-pin), so
the automated gate only requires distinctness beyond float noise (1e-6).

Run (~20 compiles ~5 min; HEADED sim only if stage 2 triggers):
  cd mcp_harness && nohup .venv/bin/python probe_star_asym.py \
      > probe_star_asym.out.log 2>&1 &
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server                       # noqa: E402
import sim_capture                  # noqa: E402
import square_complete              # noqa: E402

BS = [0.80, 0.85, 0.90, 0.95]
HS = [0.40, 0.45, 0.50, 0.55, 0.60]
RESCUE_MAX = 3
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "probe_star_asym.out.json")


def _N(i, parent, length):
    return {"id": i, "parent_id": parent, "length": length}


def compile_cell(b, h):
    """Root + 2 front legs (1.0) + 2 back legs (b) + head (h), no pairs.
    At b=1.0, h=0.5 this is exactly the slice-2 star4-head-0.5 node list."""
    nodes = [_N(0, None, 0), _N(1, 0, 1.0), _N(2, 0, 1.0),
             _N(3, 0, b), _N(4, 0, b), _N(5, 0, h)]
    out = json.loads(server._run_isolated(
        server._worker_compile_and_regions, json.dumps(nodes), [], 1.0, 1.0))
    fold = out["fold"]
    if isinstance(fold, str):
        fold = json.loads(fold)
    return fold, out["locs"]


def measure_cell(b, h):
    """One map row of geometric facts (no sim). Returns (row, squared_fold)."""
    fold, locs = compile_cell(b, h)
    loc = {int(n): (float(x), float(y)) for n, x, y in locs}
    if set(loc) != {1, 2, 3, 4, 5}:
        raise RuntimeError(f"unexpected leaf ids {sorted(loc)}")
    head = np.asarray(loc[5])
    legs = [np.asarray(loc[i]) for i in range(1, 5)]

    sq = square_complete.complete_square(fold, 1.0, 1.0)
    noop = (len(sq["vertices_coords"]) == len(fold["vertices_coords"])
            and len(sq["edges_vertices"]) == len(fold["edges_vertices"]))
    # Rescue ranking only: distance from each square corner to the nearest
    # leaf (an upper bound on corner-to-hull distance; the no-op boolean is
    # the real stage-1 criterion).
    corners = [np.asarray(c, dtype=float)
               for c in ((0, 0), (1, 0), (0, 1), (1, 1))]
    leaves = legs + [head]
    hull_gap = max(min(float(np.linalg.norm(c - p)) for p in leaves)
                   for c in corners)

    # Axial (M/V) degree structure. PLAN FIX (measured 2026-07-08): an
    # asymmetric star packs a hub PATH -- 3 tied max-degree vertices (a
    # spine) -- so sim_capture.axial_hub's uniqueness assumption only holds
    # for the symmetric slice-2 base. Measure the head against the SET.
    deg = {}
    for (a, c), asn in zip(fold["edges_vertices"], fold["edges_assignment"]):
        if asn in ("M", "V"):
            deg[a] = deg.get(a, 0) + 1
            deg[c] = deg.get(c, 0) + 1
    if not deg:
        raise RuntimeError("fold has no axial (M/V) edges")
    top = max(deg.values())
    hub_xys = [np.asarray(fold["vertices_coords"][v][:2], dtype=float)
               for v in sorted(deg) if deg[v] == top]
    head_hub_dist = min(float(np.linalg.norm(head - p)) for p in hub_xys)

    d = sorted(float(np.linalg.norm(leg - head)) for leg in legs)
    split = d[2] - d[1]
    row = {
        "b": b, "h": h,
        "head_xy": [round(float(head[0]), 8), round(float(head[1]), 8)],
        "head_center_dist": float(np.linalg.norm(head - np.array([.5, .5]))),
        "noop": bool(noop), "hull_gap": hull_gap,
        "max_axial_degree": top, "n_hubs": len(hub_xys),
        "hub_xys": [[round(float(p[0]), 8), round(float(p[1]), 8)]
                    for p in hub_xys],
        "head_hub_dist": head_hub_dist,
        "head_distinct": head_hub_dist > 1e-6,
        "leg_head_dists": d, "split": split,
        "separable": split > 1e-6,
    }
    return row, sq


def main() -> int:
    cells, squared = [], {}
    for b in BS:
        for h in HS:
            try:
                row, sq = measure_cell(b, h)
                squared[(b, h)] = sq
            except Exception as exc:
                row = {"b": b, "h": h, "error": str(exc)}
            cells.append(row)
            if "error" in row:
                print(f"b={b} h={h}: COMPILE/MEASURE FAILED: {row['error']}")
                continue
            sqs = "NO-OP" if row["noop"] else f"gap {row['hull_gap']:.4f}"
            hh = "!=" if row["head_distinct"] else "=="
            print(f"b={b} h={h}: head ({row['head_xy'][0]:.4f},"
                  f" {row['head_xy'][1]:.4f})"
                  f" ctr {row['head_center_dist']:.4f} | squaring {sqs}"
                  f" | {row['n_hubs']} hubs, head{hh}hub"
                  f" {row['head_hub_dist']:.4f}"
                  f" | split {row['split']:.4f}")

    ok = [r for r in cells if "error" not in r]
    stage1 = [r for r in ok
              if r["noop"] and r["head_distinct"] and r["separable"]]
    stage2, winner = [], None
    if stage1:
        w = max(stage1, key=lambda r: r["split"])
        winner = {"b": w["b"], "h": w["h"], "stage": 1, "split": w["split"],
                  "head_hub_dist": w["head_hub_dist"]}
    else:
        print("\nstage 1 empty -> stage-2 sim rescue on best near-misses")
        rescue = sorted(
            (r for r in ok
             if not r["noop"] and r["head_distinct"] and r["separable"]),
            key=lambda r: r["hull_gap"])[:RESCUE_MAX]
        if rescue:
            with sim_capture.SimSession() as sim:
                for r in rescue:
                    entry = {"b": r["b"], "h": r["h"],
                             "hull_gap": r["hull_gap"], "split": r["split"],
                             "head_hub_dist": r["head_hub_dist"]}
                    try:
                        _V, disp = sim_capture.check_capture(
                            sim.capture(squared[(r["b"], r["h"])]))
                        entry["disp"] = disp
                        print(f"stage-2 b={r['b']} h={r['h']}:"
                              f" maxDisp {disp:.4f} FOLDS")
                    except sim_capture.CaptureError as exc:
                        entry["error"] = str(exc)
                        print(f"stage-2 b={r['b']} h={r['h']}:"
                              f" does not fold ({exc})")
                    stage2.append(entry)
        folded = [e for e in stage2 if "disp" in e]
        if folded:
            w = max(folded, key=lambda e: e["split"])
            winner = dict(w)
            winner["stage"] = 2

    json.dump({"grid": cells, "stage1": stage1, "stage2": stage2,
               "winner": winner}, open(OUT, "w"), indent=2)

    print("\n--- FINDING ---")
    print(f"stage-1 survivors: "
          + (", ".join(f"(b={r['b']}, h={r['h']}, split {r['split']:.4f})"
                       for r in stage1) or "NONE"))
    if stage2:
        print(f"stage-2 rescues tried: {len(stage2)}, folded:"
              f" {sum(1 for e in stage2 if 'disp' in e)}")
    if winner:
        print(f"WINNER: b={winner['b']} h={winner['h']}"
              f" (stage {winner['stage']}, split {winner['split']:.4f},"
              f" head-hub dist {winner['head_hub_dist']:.4f})")
        return 0
    print("NO fittable base in this family -> slice HALTS here"
          " (the map above is the deliverable)")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run under nohup (~5 min compile-only; sim only if stage 2 triggers)**

```bash
cd mcp_harness && nohup .venv/bin/python probe_star_asym.py \
    > probe_star_asym.out.log 2>&1 &
```
Watch: `tail -f mcp_harness/probe_star_asym.out.log` (strip http noise with `grep -v "127.0.0.1\|code 404"` if stage 2 runs).

- [ ] **Step 3: Sanity anchor inside the map**

The b=0.95/h=0.50 neighborhood should look nearly symmetric, and if a b=1.0 column existed it would reproduce slice 2's halt; verify the closest cell to (1.0, 0.5) — b=0.95, h=0.50 — has a SMALL head-hub distance and split relative to the far-asymmetric corner (b=0.80). If the map shows no such gradient (e.g., every cell identical), suspect the probe is not actually varying the tree — STOP and debug before trusting any verdict.

- [ ] **Step 4: DECISION GATE — hand-check the map, pin the winner**

1. Exit 0: a winner exists. Hand-check its row: head clearly off-center (`head_hub_dist` well above float noise — compare against the map's own spread), split clearly nonzero, and for a stage-1 winner `squaring NO-OP`; for a stage-2 winner, `maxDisp` comfortably above 0.10. Pin the accepted (b, h) — it goes in the commit body and drives Tasks 2–4.
2. Exit 3: NO fittable base — the slice HALTS as a documented outcome. Skip Tasks 2–4's probe runs; go to Task 5 and record the 20-cell map as the deliverable (the documented escalation — varying front-leg length or head attachment — is explicitly out of scope).
3. Confirm `probe_star_asym.out.json` exists with a non-null `winner` (Tasks 2–4 read it).

- [ ] **Step 5: Commit (probe file ONLY — not the .out/.log files)**

```bash
cd <repo>
git add mcp_harness/probe_star_asym.py
git commit -m "probe(b5-slice3): asymmetric star base map -- stage-1/stage-2 fittable-base gate [WINNER + map summary in commit body]"
```
Amend the commit body with the winner line and the stage-1 survivor list (or the HALT finding) from the log — measure-then-pin: the numbers live in git.

---

### Task 2: `pose_target.group_tips_by_head` (TDD) + `starhead.py` generalization

**Files:**
- Modify: `mcp_harness/pose_target.py` (append one function)
- Modify: `mcp_harness/tests/test_pose_target.py` (append 3 tests)
- Modify: `mcp_harness/starhead.py`

**Interfaces:**
- Consumes: Task 1's `probe_star_asym.out.json` `winner` (for the self-check run); existing `pose_target.PoseTargetError`; everything `starhead.py` already imports.
- Produces (used by Tasks 3–4):
  - `pose_target.group_tips_by_head(head_xy, leg_xys) -> (front_pair, back_pair)` — pure; raises `PoseTargetError` on ≠4 legs or an ambiguous middle split.
  - `starhead.compile_starhead(back_len=1.0, head_len=0.5) -> (raw_fold, locs)`
  - `starhead.StarHeadBase(back_len=1.0, head_len=0.5, require_noop=True)` — same attributes as before (`.raw`, `.sq`, `.hub`, `.tips`, `.axial`); NEW: raises `CaptureError` if squaring adds geometry while `require_noop`, and if the head tip IS the hub (the slice-2 halt, now an explicit guard).
  - `starhead.winner_base() -> StarHeadBase` — constructs the Task-1 winner (`require_noop=False` for a stage-2 winner).
  - `make_ops` / `apply_ops` / `achieved_angles` / `fox_targets` / `GROUPS` / `THETAS` / `FRACTIONS` — unchanged signatures.

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_pose_target.py`:

```python
def test_group_tips_by_head_separable():
    # head near the +x edge: front = the two +x legs (nearer the head).
    head = (0.9, 0.5)
    legs = [(1.0, 0.0), (0.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    front, back = pose_target.group_tips_by_head(head, legs)
    # d^2 to head: (1,0) 0.26, (1,1) 0.26, (0,0) 1.06, (0,1) 1.06
    assert set(front) == {(1.0, 0.0), (1.0, 1.0)}
    assert set(back) == {(0.0, 0.0), (0.0, 1.0)}


def test_group_tips_by_head_symmetric_raises():
    # head at the center of a 4-fold-symmetric square = the slice-2 halt
    # geometry: all four legs equidistant -> ambiguous by design.
    head = (0.5, 0.5)
    legs = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (1.0, 1.0)]
    with pytest.raises(PoseTargetError):
        pose_target.group_tips_by_head(head, legs)


def test_group_tips_by_head_wrong_count_raises():
    with pytest.raises(PoseTargetError):
        pose_target.group_tips_by_head((0.5, 0.5), [(0.0, 0.0), (1.0, 0.0)])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_pose_target.py -q`
Expected: 3 FAIL/ERROR with `AttributeError: ... 'group_tips_by_head'`, 10 pass.

- [ ] **Step 3: Implement `group_tips_by_head`**

Append to `mcp_harness/pose_target.py`:

```python
def group_tips_by_head(head_xy, leg_xys):
    """(front_pair, back_pair) of flat 2D leg tips split by distance to the
    head tip: front = the 2 nearest (the fox convention -- front legs sit
    nearer the head; group_legs applies the same idea to the skeleton).

    Exactly 4 legs required. The middle two distances equal (within 1e-9 on
    the squared distances) is the slice-2 4-fold-symmetry halt geometry ->
    PoseTargetError, never guess. Pure: probes hand this the compiled
    base's leaf locations; tests hand it synthetic layouts.
    """
    if len(leg_xys) != 4:
        raise PoseTargetError(f"need exactly 4 leg tips, got {len(leg_xys)}")
    hx, hy = float(head_xy[0]), float(head_xy[1])

    def d2(p):
        return (float(p[0]) - hx) ** 2 + (float(p[1]) - hy) ** 2

    legs = sorted(leg_xys, key=d2)
    if abs(d2(legs[1]) - d2(legs[2])) < 1e-9:
        raise PoseTargetError(
            "front/back split ambiguous: middle two legs equidistant"
            " from the head tip")
    return tuple(legs[:2]), tuple(legs[2:])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_pose_target.py -q`
Expected: `13 passed`

- [ ] **Step 5: Generalize `starhead.py`**

Apply these modifications to `mcp_harness/starhead.py` (module docstring, `compile_starhead`, `StarHeadBase.__init__`, new `winner_base`, `_self_check`, `__main__`; `_tip_axial_len`, `make_ops`, `apply_ops`, `achieved_angles`, `fox_targets` stay byte-identical):

Replace the module docstring (lines 1–11) with:

```python
"""B5 probe support -- the asymmetric 5-leaf star base family (slice 3
generalization of slice 2's star4-head-0.5) plus the machinery the fit
probes share: compile-and-group, reverse-op construction, capture ->
achieved angles, and fox target extraction.

NOT part of the pytest suite (probe support, like sim_capture); the pure
front/back grouping lives in pose_target.group_tips_by_head and IS
pytest-covered. Correctness here is pinned by the __main__ self-check's
printed, hand-checked numbers.

Run the self-check (compiles the base; NO sim):
  cd mcp_harness && .venv/bin/python starhead.py [back_len head_len]
Default (no args) reproduces the slice-2 halt: star4-head-0.5's head tip
packs AT the axial hub -> PoseTargetError from the grouping guard.
"""
```

Replace `compile_starhead` with:

```python
def compile_starhead(back_len: float = 1.0, head_len: float = HEAD_LEN):
    """Compile a 5-leaf star: root + 2 front legs (1.0) + 2 back legs
    (back_len) + head (head_len), no symmetry pairs. Defaults are exactly
    the slice-2 star4-head-0.5 node list (the halt reproducer); node order
    is preserved because list order flips packability on the knife-edge.
    Returns (raw_fold, locs)."""
    nodes = [_N(0, None, 0), _N(1, 0, 1.0), _N(2, 0, 1.0),
             _N(3, 0, back_len), _N(4, 0, back_len), _N(5, 0, head_len)]
    out = json.loads(server._run_isolated(
        server._worker_compile_and_regions, json.dumps(nodes), [], 1.0, 1.0))
    fold = out["fold"]
    if isinstance(fold, str):
        fold = json.loads(fold)
    return fold, out["locs"]
```

Replace the `StarHeadBase` class docstring and `__init__` with:

```python
class StarHeadBase:
    """Compiled asymmetric star (front legs 1.0, back legs back_len, head
    head_len) with its flap grouping.

    tips: front = the 2 legs nearest the head tip in the flat pattern
    (pose_target.group_tips_by_head -- matches the fox convention), back =
    the other 2, head = the head_len flap (tree node 5). All flat coords
    8dp-snapped so they key tracked_points directly.
    """

    def __init__(self, back_len: float = 1.0, head_len: float = HEAD_LEN,
                 require_noop: bool = True):
        raw, locs = compile_starhead(back_len, head_len)
        sq = square_complete.complete_square(raw, 1.0, 1.0)
        noop = (len(sq["vertices_coords"]) == len(raw["vertices_coords"])
                and len(sq["edges_vertices"]) == len(raw["edges_vertices"]))
        if require_noop and not noop:
            raise sim_capture.CaptureError(
                f"star(b={back_len}, h={head_len}) does not hull-fill"
                " (squaring added geometry); require_noop=False is only for"
                " a base the stage-2 sim rescue PROVED folds")
        self.raw, self.sq = raw, sq

        # Snap each engine-reported leaf location to the SQUARED fold's own
        # vertex coordinates before 8dp-rounding -- sq, not raw, because sq
        # is the fold that gets shaped and captured, and tracked_points
        # locates targets by exact 8dp match in the captured fold's
        # vertices_coords. PLAN FIX (measured 2026-07-08, first stage-2
        # winner): complete_square on a non-noop base both ADDS geometry
        # and SNAPS near-boundary floats (0.99999999 -> 1.0, 1e-08 -> 0.0),
        # so raw-keyed tips get 0 exact matches in sq. Raw-side consumers
        # (_tip_axial_len, shaping's op targeting) resolve sq-snapped keys
        # through 1e-6 nearest-vertex lookups (the raw/sq float gap is
        # ~1e-8), so keying off sq is safe on both sides.
        V2 = np.asarray([p[:2] for p in sq["vertices_coords"]], dtype=float)

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
        front, back = pose_target.group_tips_by_head(
            head_xy, [loc[i] for i in range(1, 5)])
        self.tips = {"front": list(front), "back": list(back),
                     "head": [head_xy]}
        # 1e-6 (not 1e-9): head_xy is sq-snapped, the hub set is raw-based,
        # and complete_square moves boundary floats by ~1e-8; real
        # head-to-hub distances on any acceptable base are >> 1e-6.
        hubs = _axial_hub_set(raw)
        for hxy in hubs:
            if (abs(head_xy[0] - hxy[0]) < 1e-6
                    and abs(head_xy[1] - hxy[1]) < 1e-6):
                raise sim_capture.CaptureError(
                    "head tip IS an axial hub-path vertex (the slice-2 halt"
                    " geometry): head angle unmeasurable/unactuatable")
        # Re-snap the raw-derived hub onto sq's floats for the same reason
        # as the tips: it is a tracked_points key against captured folds.
        self.hub = _snap(*axial_hub_near_center(raw))
        self.axial = {xy: _tip_axial_len(raw, xy)
                      for xys in self.tips.values() for xy in xys}
```

Insert BEFORE the `StarHeadBase` class (after `_tip_axial_len`) the two hub helpers (PLAN FIX, measured 2026-07-08: an asymmetric star packs a hub PATH — 3 tied max-axial-degree vertices, a spine — so `sim_capture.axial_hub`'s uniqueness assumption only holds for the symmetric slice-2 base; `sim_capture` itself stays untouched):

```python
def _axial_hub_set(fold: dict):
    """8dp-snapped flat coords of ALL max-axial-degree vertices. Slice-3
    measured finding: an asymmetric star packs a hub PATH (tied max-degree
    vertices -- a spine), so sim_capture.axial_hub's uniqueness assumption
    only holds for the symmetric slice-2 base. sim_capture stays untouched."""
    deg = {}
    for (a, b), asn in zip(fold["edges_vertices"], fold["edges_assignment"]):
        if asn in ("M", "V"):
            deg[a] = deg.get(a, 0) + 1
            deg[b] = deg.get(b, 0) + 1
    if not deg:
        raise sim_capture.CaptureError("fold has no axial (M/V) edges")
    top = max(deg.values())
    return [(round(float(fold["vertices_coords"][v][0]), 8),
             round(float(fold["vertices_coords"][v][1]), 8))
            for v in sorted(deg) if deg[v] == top]


def axial_hub_near_center(fold: dict):
    """The fit-side bone-vector origin: among the hub-path vertices, the
    one nearest the paper center (0.5, 0.5) -- a deterministic 'body
    center'. Distance tie within 1e-9 (squared) -> CaptureError, never
    guess. On the symmetric slice-2 base this returns its single hub, so
    the reproducer semantics are unchanged."""
    hubs = _axial_hub_set(fold)
    d = [((x - 0.5) ** 2 + (y - 0.5) ** 2) for x, y in hubs]
    order = sorted(range(len(hubs)), key=lambda i: d[i])
    if len(hubs) > 1 and abs(d[order[0]] - d[order[1]]) < 1e-9:
        raise sim_capture.CaptureError(
            f"hub-path center ambiguous: {hubs[order[0]]} and"
            f" {hubs[order[1]]} equidistant from paper center")
    return hubs[order[0]]
```

Insert after the `StarHeadBase` class (before `make_ops`):

```python
def winner_base() -> "StarHeadBase":
    """Construct the slice-3 base probe's recorded winner. The winner
    object is written by probe_star_asym.py; a stage-2 winner (squaring
    adds geometry but the sim rescue proved it folds) relaxes the no-op
    requirement -- exactly and only that case."""
    sel_path = os.path.join(_HERE, "probe_star_asym.out.json")
    if not os.path.exists(sel_path):
        raise sim_capture.CaptureError(
            f"missing {sel_path} -- run probe_star_asym.py first")
    w = json.load(open(sel_path)).get("winner")
    if not w:
        raise sim_capture.CaptureError(
            "probe_star_asym recorded NO winner (slice halts at the"
            " base gate)")
    return StarHeadBase(back_len=float(w["b"]), head_len=float(w["h"]),
                        require_noop=(int(w["stage"]) == 1))
```

Replace `_self_check` and the `__main__` block with:

```python
def _self_check(back_len: float = 1.0, head_len: float = HEAD_LEN) -> int:
    """No-sim self-check: compile the base, print grouping + geometry for
    hand-check (measure-then-pin: these numbers pin the fit probes'
    assumptions). Default args reproduce the slice-2 halt."""
    base = StarHeadBase(back_len, head_len)
    print(f"star(b={back_len}, h={head_len}) compiled;"
          " squaring NO-OP confirmed")
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
    raise SystemExit(_self_check(*[float(a) for a in sys.argv[1:]]))
```

- [ ] **Step 6: Verify the slice-2 halt reproducer still reproduces**

Run: `cd mcp_harness && .venv/bin/python starhead.py`
Expected: raises `PoseTargetError: front/back split ambiguous: middle two legs equidistant from the head tip` (the guard moved from `CaptureError` to pure `pose_target` — the halt behavior is preserved, the exception type is the documented change).

- [ ] **Step 7: Run the self-check on the Task-1 winner (compiles TreeMaker; no sim; ~1 min)**

Run with the winner's values from `probe_star_asym.out.json` (example shown for a winner of b=0.85, h=0.50 — substitute the actual values):
```bash
cd mcp_harness && .venv/bin/python starhead.py 0.85 0.50
```
NOTE: if the winner is stage-2 (non-noop), the bare CLI will raise the `does not hull-fill` guard — expected; verify instead via:
```bash
cd mcp_harness && .venv/bin/python -c "import starhead; b = starhead.winner_base(); print(b.tips, b.hub)"
```
Expected output shape (either path):
- 2 front tips (nearest the head tip), 2 back tips, 1 head tip; head tip NOT equal to the hub
- positive axial lengths; head axial < leg axials
- `sample ops applied` with MORE vertices than the base (bare CLI path only)

- [ ] **Step 8: DECISION GATE — hand-check the winner base's grouping**

The front pair must be the two legs geometrically nearest the head tip on the printed map from Task 1; the ambiguity guard must NOT have fired; the head tip and hub must be distinct coordinates. If the grouping contradicts the Task-1 map, STOP.

- [ ] **Step 9: Run the pure-test files**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_pose_target.py tests/test_pose_search.py -q`
Expected: `23 passed` (13 pose_target + 10 pose_search).

- [ ] **Step 10: Commit**

```bash
cd <repo>
git add mcp_harness/pose_target.py mcp_harness/tests/test_pose_target.py \
        mcp_harness/starhead.py
git commit -m "feat(b5-slice3): parameterized star base -- pure front/back grouping + winner_base [winner (b, h) + grouping readout in commit body]"
```
Amend the body with the winner's (b, h), tips, and hub from Step 7's output.

---

### Task 3: `probe_angle_range.py` — fox-target gate + per-group achievable range

**Files:**
- Create: `mcp_harness/probe_angle_range.py`

**Interfaces:**
- Consumes: `starhead.winner_base/make_ops/apply_ops/achieved_angles/fox_targets/GROUPS/THETAS`; `sim_capture.SimSession/check_capture/CaptureError`; `pose_target.PoseTargetError`.
- Produces: `mcp_harness/probe_angle_range.out.json` (uncommitted) with keys `winner_bh`, `fox_targets`, `fox_info`, `baseline_angles`, `sweep` (per group: list of `{theta, angle, disp}` plus `<group>_range`), `best_achievable` (per group: `{theta, angle, gap_to_target}`), `angle_tol` (per group), `verdict`. Task 4 REQUIRES this file.

**PLAN FIX (2026-07-08, discovered at gate 2):** at the inherited default
constants (voxel_res=96, prune_fraction=0.60) the fox tree is anatomically
WRONG — 5 leaves where the front legs are merged into one leaf and the tail
survives, so `detect_symmetry` finds only ONE leaf pair and `fox_targets`
raises. A measured 16-cell (voxel_res × prune_fraction) sweep found that
voxel_res=96 / prune_fraction=0.45 yields the honest topology: 6 leaves =
2 leg pairs (back n2/n143 at z≈36.5, front n4/n164 at z≈67–70) + head n1
(y=39.9) + tail n84 (y=18.1). `group_legs` requires exactly 1 unpaired
leaf, so `fox_targets` drops the tail by pinned rule: among unpaired leaves
the head is the one with max y (the committed fixture is y-up; 39.9 vs
18.1, hand-checked); every other unpaired leaf is removed from the tree
before grouping. `group_legs`'s front/back projection rule was hand-checked
on this tree (front proj −17.1 > back −44.5 onto the head bone — correct).
Replace `fox_targets` in `mcp_harness/starhead.py` (Task 2's "byte-identical"
constraint is amended by this fix) with:

```python
FOX_VOXEL_RES = 96
FOX_PRUNE_FRACTION = 0.45


def fox_targets():
    """Target-side extraction (runs ONCE per probe): fox mesh -> skeleton ->
    grouped bones -> the 3 target angles. PoseTargetError here is the
    fox-skeleton gate failing -- a reportable target-side blocker.

    Slice-3 measured fix: the old default constants (prune 0.60) merge the
    fox's front legs and keep the tail (5 leaves, ONE pair -> raise). At
    voxel_res=96 / prune_fraction=0.45 the tree is anatomically honest:
    6 leaves = 2 leg pairs + head + tail. group_legs requires exactly 1
    unpaired leaf, so the TAIL is dropped by pinned rule: among unpaired
    leaves the head is the one with max y (the committed fixture is y-up;
    head y=39.9 vs tail y=18.1, hand-checked); every other unpaired leaf
    is removed from the tree before grouping. info records the drops."""
    import mesh_to_tree
    mesh = mesh_to_tree.load_mesh(FOX_GLB, voxel_res=FOX_VOXEL_RES)
    skel = mesh_to_tree.extract_skeleton(mesh)
    tree = mesh_to_tree.simplify_to_tree(
        skel, prune_fraction=FOX_PRUNE_FRACTION)
    sym = mesh_to_tree.detect_symmetry(tree, mesh)
    leaves = {n for n in tree.nodes if tree.degree(n) == 1}
    leaf_pairs = [p for p in sym if p[0] in leaves and p[1] in leaves]
    paired = {n for p in leaf_pairs for n in p}
    unpaired = sorted(leaves - paired)
    dropped = []
    if len(unpaired) > 1:
        by_y = sorted(unpaired,
                      key=lambda n: float(tree.nodes[n]["pos"][1]),
                      reverse=True)
        dropped = by_y[1:]
        tree.remove_nodes_from(dropped)
    head, front, back = pose_target.group_legs(tree, leaf_pairs)
    bones = pose_target.bone_vectors(tree)
    angles = pose_target.angles_from_bones(
        bones[head], [bones[n] for n in front], [bones[n] for n in back])
    info = {"head_leaf": int(head),
            "front_pair": [int(n) for n in front],
            "back_pair": [int(n) for n in back],
            "dropped_unpaired": [int(n) for n in dropped],
            "n_leaves": sum(1 for n in tree.nodes if tree.degree(n) == 1),
            "sym_pairs": [[int(a), int(b)] for a, b in sym]}
    return angles, info
```

**The gate rules (from the spec):**
- Gate 2 (fox skeleton): `fox_targets()` must succeed AND the printed angles must survive a hand sanity check vs the fox's anatomy (legs point away from the head — expect obtuse leg-vs-head angles). `PoseTargetError` → exit 2 with the message.
- Gate 3 (angle range): HALT if any group's achieved-angle range across the θ sweep is `< 3 * ANGLE_FLOOR` where `ANGLE_FLOOR = 1.0°` — a first-principles measurement floor (the refine grid cannot meaningfully resolve below ~1°; the deterministic solver's noise is exactly 0, which slice 1 pinned as unusable for thresholds). The controller hand-checks the printed ranges regardless of the automated verdict.

- [ ] **Step 1: Write the probe**

Create `mcp_harness/probe_angle_range.py`:

```python
"""B5 slice-3 de-risk probe (gates 2+3): can the angle objective SEE theta
on each flap group of the winner base, and are the fox's target angles
sane?

Per group: sweep theta over the coarse grid at f=0.5 (other groups
unshaped), record the group's OWN achieved angle. Range = max - min.
HALT if any range < 3 * ANGLE_FLOOR (1.0 deg first-principles floor --
solver noise is exactly 0.0 and slice 1 pinned that as unusable).
Also records per-group best-achievable angle (closest to the fox target
at f=0.5) and angle_tol (achieved-angle change across the adjacent theta
step at the best cell) for the fit probe's PASS rule.

Requires probe_star_asym.out.json with a winner (Task 1's gate).

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
    # ---- Gate 2: fox targets (raises PoseTargetError = gate fails) ----
    try:
        targets, info = starhead.fox_targets()
    except pose_target.PoseTargetError as exc:
        print(f"GATE 2 FAIL (fox skeleton degenerate): {exc}")
        return 2
    print(f"fox targets (deg): {json.dumps(targets, indent=2)}")
    print(f"fox skeleton info: {json.dumps(info)}")
    print("hand-check: legs should point away from the head"
          " (expect obtuse leg-vs-head angles)")

    base = starhead.winner_base()
    bh = json.load(open(os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "probe_star_asym.out.json")))["winner"]
    print(f"winner base: b={bh['b']} h={bh['h']} (stage {bh['stage']})")
    out = {"winner_bh": [bh["b"], bh["h"]],
           "fox_targets": targets, "fox_info": info}
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
                print(f"GATE 3 FAIL: group {grp} has <2 successful"
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

- [ ] **Step 3: DECISION GATE — hand-check before Task 4**

1. Gate 2: the printed fox target angles must be anatomically plausible (obtuse leg-vs-head angles; no NaN; exactly 2 leg pairs + 1 unpaired head in `fox_info`). Exit 2 = slice ends here as a documented target-side blocker.
2. Gate 3: printed per-group ranges vs the 3.0° floor, hand-checked (not just the automated verdict). Exit 3 = HALT = slice ends here as a documented sensitivity failure. Special attention to the HEAD group — this is the first time a head angle has ever been measured (slice 2 died before it); a head range near zero despite a distinct tip vertex would be a NEW finding worth its own paragraph in the handoff.
3. Confirm `probe_angle_range.out.json` exists (Task 4 reads it).

- [ ] **Step 4: Commit (the probe file ONLY — not the .out/.log files)**

```bash
cd <repo>
git add mcp_harness/probe_angle_range.py
git commit -m "probe(b5-slice3): angle-range de-risk gate -- fox targets + per-group theta sweep on the winner base [VERDICT + measured ranges in commit body]"
```
Amend the commit message body with the measured verdict line and per-group ranges from the log.

---

### Task 4: `probe_pose_fit.py` — the fit itself

**Files:**
- Create: `mcp_harness/probe_pose_fit.py`

**Interfaces:**
- Consumes: everything Task 3 consumes, plus `pose_search.grid_search/refine` (`GridResult.best_params/.best_score`) and `probe_angle_range.out.json` (`fox_targets`, `best_achievable`, `angle_tol`, `verdict`).
- Produces: `probe_pose_fit.out.jsonl` (every evaluation) + `probe_pose_fit.out.json` (final verdict), both uncommitted.

**PASS rule (from the spec, operationalized with Task 3's measurements):**
- Per group: `|fit_achieved_angle - fox_target| <= best_achievable.gap_to_target + angle_tol` (the fit must not do meaningfully worse than the crude f=0.5 sweep's best; doing better passes trivially), AND
- Total: final `angle_error` strictly < baseline (unshaped) `angle_error`.

- [ ] **Step 1: Write the probe**

Create `mcp_harness/probe_pose_fit.py`:

```python
"""B5 slice-3 main probe (gate 4): sequential 3-group coordinate descent
fitting the winner base's reverse-fold (theta, fraction) per group to the
fox skeleton's target angles.

Requires probe_angle_range.out.json (Task 3 must have PROCEEDed) and
probe_star_asym.out.json (Task 1's winner, via starhead.winner_base).

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
    print(f"winner base (b, h): {rng['winner_bh']}")

    log = open(OUT_JSONL, "w")

    def jlog(**kw):
        log.write(json.dumps(kw) + "\n")
        log.flush()

    base = starhead.winner_base()
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

`FIT PASS` (exit 0) or `FIT FAIL` (exit 1). Either is a valid slice outcome; a FAIL with clean per-group numbers is a documented finding (e.g., coordinate descent got stuck, or head-group coupling breaks the sequential assumption). Hand-check the landscape in the JSONL for the same unimodal-basin sanity slice 1 had.

- [ ] **Step 4: Commit (probe file only)**

```bash
cd <repo>
git add mcp_harness/probe_pose_fit.py
git commit -m "probe(b5-slice3): sequential joint-angle fit vs fox skeleton on the winner base [VERDICT + fitted params + errors in commit body]"
```
Amend the body with: baseline error, final error, per-group fitted (θ, f) + achieved-vs-target gaps, PASS/FAIL.

---

### Task 5: Handoff + spec banner + full suite

**Files:**
- Create: `docs/superpowers/2026-07-08-handoff-b5-slice3-outcome.md`
- Modify: `docs/superpowers/specs/2026-07-08-b5-pose-fit-slice3-design.md` (status banner)

**Interfaces:**
- Consumes: all measured numbers from Tasks 1–4's printed outputs and out.json files.
- Produces: the slice's durable record.

- [ ] **Step 1: Run the full backend suite (~10 min; use nohup from a subagent shell)**

```bash
cd mcp_harness && nohup .venv/bin/python -m pytest tests -q \
    > suite_slice3.out.log 2>&1 &
```
Expected: `424 passed, 3 skipped` (421 from slice 2 + 3 new grouping tests). A failure blocks the slice from finishing — fix before proceeding.

- [ ] **Step 2: Write the handoff**

Create `docs/superpowers/2026-07-08-handoff-b5-slice3-outcome.md` with this structure, filling every bracketed value from the actual probe outputs (NO invented numbers):

```markdown
# Handoff: B5 slice 3 (asymmetric star probe + pose fit) — outcome

**Spec:** docs/superpowers/specs/2026-07-08-b5-pose-fit-slice3-design.md
**Plan:** docs/superpowers/plans/2026-07-08-b5-pose-fit-slice3.md

## What shipped
- `mcp_harness/probe_star_asym.py` — 20-cell (b, h) map: [stage-1 survivor
  count]; winner b=[x] h=[x] (stage [1/2], split [x], head-hub dist [x]).
- `mcp_harness/pose_target.py` `group_tips_by_head` + 3 tests — pure
  front/back split, ambiguity guard now pytest-pinned.
- `mcp_harness/starhead.py` — parameterized (back_len, head_len);
  head==hub explicit guard; `winner_base()`; default args still reproduce
  the slice-2 halt.
- `probe_angle_range.py` — gates 2+3: fox targets {front [x], back [x],
  head [x]} deg; per-group achievable ranges [values]; verdict
  [PROCEED/HALT].
- `probe_pose_fit.py` — gate 4: baseline error [x], final error [x],
  fitted params [per group], per-group gaps vs bounds; FIT [PASS/FAIL].

## Findings
[The measured story: did an asymmetric hull-filler exist (stage 1) or did
the sim rescue save a near-miss (stage 2)? Was the head angle finally
measurable and actuatable? Did the sequential coordinate descent close on
the real-mesh target? Was the landscape unimodal like slice 1's?]

## Slice 4 entry point
[Based on the outcome: if PASS — candidates are agent/MCP wiring of the
pose-fit loop (the deferred item that makes B5 real), richer op vocabulary
(crimp for knee bends), or spined bases; if HALT/FAIL — what the numbers
say broke and the cheapest probe to answer it.]

## Gotchas carried forward
- All slice-1/2 gotchas still hold (headed SimSession, deterministic
  solver — never 0.0 tolerances, nohup for subagent probes, playwright
  venv-only, scene-frame flat_coords / index-based tracking, spawn workers
  need real script files, probe outputs uncommitted).
- [Any new ones found this slice, e.g. asymmetric-packing quirks, stage-2
  squared-fold sim behavior, head-angle coupling.]
```

- [ ] **Step 3: Update the spec status banner**

In `docs/superpowers/specs/2026-07-08-b5-pose-fit-slice3-design.md`, change the `**Status:**` line to:
`**Status:** IMPLEMENTED [+ outcome, e.g. "— FIT PASS on star(b=[x], h=[x])" or "— HALTED at gate N (see handoff)"] (handoff: docs/superpowers/2026-07-08-handoff-b5-slice3-outcome.md)`

- [ ] **Step 4: Commit**

```bash
cd <repo>
git add docs/superpowers/2026-07-08-handoff-b5-slice3-outcome.md \
        docs/superpowers/specs/2026-07-08-b5-pose-fit-slice3-design.md
git commit -m "docs(b5-slice3): outcome handoff + spec status banner"
```
