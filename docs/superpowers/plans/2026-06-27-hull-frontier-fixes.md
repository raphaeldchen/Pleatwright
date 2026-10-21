# Hull-frontier Robustness (A-1) + Agent Teaching (A-2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `find_free_paper` report a "frame" region instead of crashing when the leaf hull is fully/partly interior (A-1), and rewrite the agent's free-paper-frontier prompt to lead with A-3=ACCEPT (A-2).

**Architecture:** Two independent, pure-Python edits in `mcp_harness/`. A-1 adds one branch to `free_paper_regions` (and a `hole` field + a point-in-polygon helper) without touching the proven boundary-walk path. A-2 rewrites one prose block in the `SYSTEM_PROMPT` constant. Both are verified by fast unit tests that need no compiled engine.

**Tech Stack:** Python 3.14, pytest. Pure modules — no TreeMaker `.so` or JVM needed for these tests.

## Global Constraints

- Pure geometry only: `free_paper.py` imports nothing from the engine/MCP/JVM — every function takes plain coordinates and returns plain data.
- The existing all-on-boundary path (the `for i in range(n)` perimeter walk producing `kind ∈ {"corner","edge-strip"}`) MUST stay byte-for-byte behavior-identical; the pinned `test_star5_*`, area-accounting, determinism, and degenerate tests must remain green.
- `_TOL = 1e-7` is the existing boundary-snap tolerance; reuse it, do not introduce a new one.
- Scope is A-1 + A-2 only. Do NOT touch C-8 (`MESH_PROVIDER` default), B-7 (python-dotenv), or A-9 (generative fill).
- Region schema change is additive only: add a `hole` field defaulting to `[]`; existing region constructions must not need editing.
- Tests run from `mcp_harness/` with `PYTHONPATH=.:tests` using `.venv/bin/python`.

---

### Task 1: A-1 — interior-hull frame region in `free_paper.py`

**Files:**
- Modify: `mcp_harness/free_paper.py` (imports line 13; `Region` dataclass lines 102-111; replace the raise block lines 141-145; add `_point_in_polygon` helper)
- Test: `mcp_harness/tests/test_free_paper.py` (append new cases)

**Interfaces:**
- Consumes: `convex_hull(points) -> list[Point]`, `_on_boundary(p, w, h) -> bool`, `_polygon_area(poly) -> float`, `_centroid(poly) -> Point`, `_rect_corners(w, h) -> list[(Point, float)]`, all existing in `free_paper.py`.
- Produces: `free_paper_regions(nodes, paper_w=1.0, paper_h=1.0) -> list[dict]` now returns a single `kind="frame"` region (instead of raising `ValueError`) when any hull vertex is interior. Each region dict gains a `hole: list` key (`[]` for non-frame regions). New module-level helper `_point_in_polygon(p: Point, poly: list[Point]) -> bool` (strictly-inside ray cast; boundary → False).

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_free_paper.py`:

```python
# A-1: hull fully/partly interior -> one "frame" region (sheet minus hull),
# instead of the old ValueError. (The "bear" packed entirely interior.)
INTERIOR = [(0, 0.3, 0.3), (1, 0.7, 0.3), (2, 0.5, 0.7), (3, 0.45, 0.5)]


def test_interior_hull_returns_single_frame_region():
    regions = fp.free_paper_regions(INTERIOR, 1.0, 1.0)
    assert len(regions) == 1
    r = regions[0]
    assert r["kind"] == "frame"
    assert r["region_id"] == 0
    # the hole is the leaf hull (node 3 at (0.45,0.5) is interior -> dropped)
    assert set(map(tuple, r["hole"])) == {(0.3, 0.3), (0.7, 0.3), (0.5, 0.7)}
    # outer polygon is the full sheet
    assert set(map(tuple, r["polygon"])) == {(0.0, 0.0), (1.0, 0.0),
                                             (1.0, 1.0), (0.0, 1.0)}
    # only the three hull vertices border the frame; node 3 is not on the hull
    assert set(r["adjacent_node_ids"]) == {0, 1, 2}
    assert r["adjacent_hull_edge"] == []


def test_frame_area_plus_hull_equals_sheet():
    regions = fp.free_paper_regions(INTERIOR, 1.0, 1.0)
    hull = fp.convex_hull([(x, y) for _id, x, y in INTERIOR])
    assert regions[0]["area"] + fp._polygon_area(hull) == pytest.approx(1.0,
                                                                        abs=1e-9)


def test_frame_reports_all_four_corners_when_fully_interior():
    r = fp.free_paper_regions(INTERIOR, 1.0, 1.0)[0]
    assert set(map(tuple, r["corners_contained"])) == {
        (0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)}


def test_mixed_hull_one_tip_on_edge_returns_frame():
    # node 0 sits on the left edge (x=0); the other two are interior -> still
    # an interior hull, so the frame branch (not the perimeter walk) handles it.
    mixed = [(0, 0.0, 0.5), (1, 0.7, 0.3), (2, 0.5, 0.8)]
    regions = fp.free_paper_regions(mixed, 1.0, 1.0)
    assert len(regions) == 1
    assert regions[0]["kind"] == "frame"


def test_boundary_regions_expose_empty_hole():
    # additive-schema check: the proven star5 corner regions gain hole == [].
    for r in fp.free_paper_regions(STAR5, 1.0, 1.0):
        assert r["hole"] == []


def test_point_in_polygon_inside_and_outside():
    tri = [(0.3, 0.3), (0.7, 0.3), (0.5, 0.7)]
    assert fp._point_in_polygon((0.5, 0.4), tri) is True    # interior
    assert fp._point_in_polygon((0.0, 0.0), tri) is False   # below-left, outside
    assert fp._point_in_polygon((0.9, 0.9), tri) is False   # above-right, outside
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_free_paper.py -v`
Expected: the six new tests FAIL — `test_interior_hull_*`/`test_frame_*`/`test_mixed_*` raise `ValueError("hull vertex ... is interior to the paper")`; `test_point_in_polygon_*` fails with `AttributeError: module 'free_paper' has no attribute '_point_in_polygon'`; `test_boundary_regions_expose_empty_hole` fails with `KeyError: 'hole'`. Existing tests still PASS.

- [ ] **Step 3: Add the `field` import and the `hole` field**

In `mcp_harness/free_paper.py`, change the dataclass import (line 13):

```python
from dataclasses import dataclass, asdict, field
```

Add `hole` as the last field of `Region` (after `corners_contained`, line 111). Because it has a default, no existing `Region(...)` construction needs editing:

```python
    corners_contained: list   # rectangle corners inside the region
    hole: list = field(default_factory=list)  # inner boundary (hull) for kind="frame"; [] otherwise
```

- [ ] **Step 4: Add the `_point_in_polygon` helper**

In `mcp_harness/free_paper.py`, add this module-level function just after `_centroid` (after line 96):

```python
def _point_in_polygon(p: Point, poly: list[Point]) -> bool:
    """True if p is strictly inside the polygon (even-odd ray cast).
    Points on an edge or vertex return False."""
    x, y = p
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y):
            xint = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < xint:
                inside = not inside
        j = i
    return inside
```

- [ ] **Step 5: Replace the raise block with the frame branch**

In `mcp_harness/free_paper.py`, replace the interior-vertex raise loop (current lines 141-145):

```python
    for v in hull:
        if not _on_boundary(v, paper_w, paper_h):
            raise ValueError(
                f"hull vertex {v} is interior to the paper; free-paper "
                "detection assumes scale-optimized bases (tips on the edge)")
```

with the frame branch (A-3=ACCEPT: this is now a signal, not an error):

```python
    # Any interior hull vertex (no flap tip on that edge) breaks the perimeter
    # walk's tips-on-edge assumption. The base still folds (A-3=ACCEPT), so
    # report the whole leftover "frame" -- sheet minus the interior hull -- as
    # ONE region rather than raising. Subsumes the mixed case (some tips on an
    # edge, some interior): any interior vertex routes here.
    if any(not _on_boundary(v, paper_w, paper_h) for v in hull):
        rect = [(0.0, 0.0), (paper_w, 0.0), (paper_w, paper_h), (0.0, paper_h)]
        hull_area = _polygon_area(hull)
        c_rect = _centroid(rect)
        c_hull = _centroid(hull)
        denom = sheet - hull_area
        if abs(denom) < _TOL:                # hull ~ fills sheet: fall back
            loc = list(c_rect)
        else:
            loc = [(sheet * c_rect[0] - hull_area * c_hull[0]) / denom,
                   (sheet * c_rect[1] - hull_area * c_hull[1]) / denom]
        corners = [c for c, _t in _rect_corners(paper_w, paper_h)
                   if not _point_in_polygon(c, hull)]
        ids = [nid for nid in (nid_at(v) for v in hull) if nid is not None]
        r = Region(
            region_id=0,
            kind="frame",
            location=loc,
            polygon=[list(p) for p in rect],
            area=denom / sheet,
            adjacent_hull_edge=[],
            adjacent_node_ids=ids,
            corners_contained=[list(c) for c in corners],
            hole=[list(p) for p in hull],
        )
        return [asdict(r)]
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_free_paper.py -v`
Expected: PASS — all six new tests plus every pre-existing test in the file (star5, area accounting, determinism, degenerate two-leaf).

- [ ] **Step 7: Run the find_free_paper integration tests for regression**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_find_free_paper.py -v`
Expected: PASS — confirms the additive `hole` key did not break the MCP-tool-level tests (no exact dict-key-set assertions there). If any test there asserts an exact dict equality that now misses `hole`, update that expected dict to include `"hole": []` and note it in the task report.

- [ ] **Step 8: Commit**

```bash
git add mcp_harness/free_paper.py mcp_harness/tests/test_free_paper.py
git commit -m "fix(free_paper): report frame region for interior hull instead of crashing (A-1)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: A-2 — rewrite the free-paper-frontier prompt in `agent_loop.py`

**Files:**
- Modify: `mcp_harness/agent_loop.py` (the "THE FREE-PAPER FRONTIER" block, lines 230-252, inside the `SYSTEM_PROMPT` constant that starts at line 76)
- Test: `mcp_harness/tests/test_agent_reference_prompt.py` (append one test)

**Interfaces:**
- Consumes: `agent_loop.SYSTEM_PROMPT` (a module-level `str`).
- Produces: no code interface change — only the prompt text. The new block leads with A-3=ACCEPT and frames `find_free_paper` as optional.

- [ ] **Step 1: Write the failing test**

Append to `mcp_harness/tests/test_agent_reference_prompt.py`:

```python
def test_system_prompt_accepts_free_paper_frontier():
    sp = agent_loop.SYSTEM_PROMPT
    low = sp.lower()
    # A-3=ACCEPT: the frontier folds and is the default correct outcome
    assert "free-paper frontier" in low
    assert "folds cleanly as-is" in low
    assert "default correct outcome" in low
    # find_free_paper is now optional polish, not a required remedy
    assert "optionally call find_free_paper" in low
    assert "optional aesthetic polish" in low
    # the old self-contradiction is gone
    assert "is a DESIGN choice, not a math error to fix" not in sp
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_agent_reference_prompt.py::test_system_prompt_accepts_free_paper_frontier -v`
Expected: FAIL — current prompt lacks "folds cleanly as-is" / "default correct outcome" / "optionally call find_free_paper" / "optional aesthetic polish", and still contains "is a DESIGN choice, not a math error to fix".

- [ ] **Step 3: Replace the prompt block**

In `mcp_harness/agent_loop.py`, replace the entire block from `THE FREE-PAPER FRONTIER -- DO NOT MISDIAGNOSE IT` (line 230) through the line ending `the frontier above, not a retry target.` (line 252) with:

```python
THE FREE-PAPER FRONTIER -- ACCEPT IT, DO NOT MISDIAGNOSE IT
There is one lint outcome you MUST recognize and ACCEPT, not treat as a defect: \
a base that COMPILED cleanly but lints as ALL geometry/Kawasaki violations with \
ZERO M/V-fixable. This is the expected "free-paper frontier" and it FOLDS CLEANLY \
AS-IS (verified physically in the WebGL viewport) -- accept is the DEFAULT CORRECT \
OUTCOME, not a failure and not a retry target. TreeMaker only creases the CONVEX \
HULL of the leaf nodes; when a subject has many flaps (e.g. a real quadruped: 4 \
legs + head + tail = 6 leaves), that hull does not reach the square's corners, so \
the leftover paper is left uncreased and the linter reads the hull boundary as \
Kawasaki-failing vertices. The uncreased paper stays flat when folded, so those \
are Oriedita false-negatives for this class. Do NOT invent causes ("tight \
packing", "short body edge", "the molecule is a separate step") and do NOT propose \
remedies that cannot help (longer edges, bigger/2x2 paper, hand-editing in a GUI) \
-- and do NOT spend compile retries on it. Instead:
  1. Tell the user the base is VALID and FOLDABLE as-is -- this is the finished \
result for this subject, not an error to fix.
  2. Optionally call find_free_paper with the SAME tree_nodes and symmetric_pairs \
you compiled to report which regions are uncreased, and present them as OPTIONAL \
detail-flap locations: "the base folds as-is; these regions are free paper where \
extra detail flaps COULD go if you want more anatomy", citing the region locations \
it returns. Adding flaps to fill the free paper is OPTIONAL AESTHETIC POLISH, not a \
math fix.
Only treat a lint failure as fixable when it includes M/V-fixable violations \
(flip mountain/valley) -- geometry-only failures on a freshly compiled base are \
the frontier above, not a retry target.
```

- [ ] **Step 4: Run the prompt tests to verify they pass**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_agent_reference_prompt.py -v`
Expected: PASS — the new test plus the existing `test_system_prompt_wires_reference_flow`.

- [ ] **Step 5: Run the broader agent-prompt-dependent tests for regression**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_mesh_to_tree.py tests/test_tree_generator.py -v`
Expected: PASS — these import `SYSTEM_PROMPT`; confirm the rewrite didn't break a substring they assert on.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/agent_loop.py mcp_harness/tests/test_agent_reference_prompt.py
git commit -m "feat(agent): teach the free-paper frontier as ACCEPT, find_free_paper optional (A-2)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Final verification (after both tasks)

- [ ] Run the full harness suite to confirm no regression:

Run: `cd <repo> && make PYTHON=mcp_harness/.venv/bin/python test` (or, if the engine `.so` is already built, `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest -q`).
Expected: all tests pass (the prior baseline plus the seven new tests).

- [ ] Update the roadmap: in `docs/followups-web-ui-and-foldability.md`, mark items 1 (A-1) and 2 (A-2) RESOLVED with a one-line pointer to this branch, mirroring the A-3 resolution note already in item 3.
