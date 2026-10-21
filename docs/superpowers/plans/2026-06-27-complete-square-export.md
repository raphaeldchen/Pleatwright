# Complete-the-Square FOLD Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Post-process the hull-only TreeMaker FOLD into a full-square FOLD (4 corners + true border + flat corner faces) so the viewport/linter/download all see a square.

**Architecture:** One new pure-Python module `mcp_harness/square_complete.py` with `complete_square(fold, w, h)`, reusing `free_paper.py`'s perimeter helpers. Wired into both `server.py` compile workers right after `build_and_export()`. No C++/engine change.

**Tech Stack:** Python 3.14, pytest. `square_complete.py` is pure geometry (engine-free, fast tests); the golden bear test needs the compiled engine `.so`.

## Global Constraints

- `square_complete.py` is pure geometry: it imports ONLY from `free_paper` (the helpers `_on_boundary`, `_perimeter_coord`, `_rect_corners`) and the stdlib — no engine/MCP/JVM imports.
- Do NOT reimplement those helpers; reuse them from `free_paper`.
- Do NOT change `TreemakerWrapper.cpp` / `ExportFold` — squaring is a faithful post-export transform.
- `complete_square` MUST be deterministic and idempotent (squaring a square returns it unchanged).
- Degenerate inputs return the FOLD **unchanged**: no `"B"` border loop, or the border loop is already exactly the 4 square corners.
- Both compile workers (`_worker_full_base`, `_worker_compile_recipe`) must square their export.
- Do NOT change the A-2 prompt (`agent_loop.py`) in this sub-project.
- Former hull-outline chords that cut corners become `"F"` (flat); the true square sides are `"B"`.
- Tests run from `mcp_harness/` with `PYTHONPATH=.:tests` using `.venv/bin/python`.

---

### Task 1: `complete_square` — common case (tips on paper edges)

**Files:**
- Create: `mcp_harness/square_complete.py`
- Test: `mcp_harness/tests/test_square_complete.py`

**Interfaces:**
- Consumes: `free_paper._on_boundary(p, w, h) -> bool`, `free_paper._perimeter_coord(p, w, h) -> float`, `free_paper._rect_corners(w, h) -> list[(point, coord)]`.
- Produces: `complete_square(fold: dict, paper_w: float = 1.0, paper_h: float = 1.0) -> dict`. Returns a new FOLD dict (or the same object unchanged for degenerate inputs). Adds the 4 square corners as vertices, builds the `"B"` square border between perimeter-ordered anchors (on-edge tips + corners), and reassigns corner-cutting chords `"B"` → `"F"`. Does NOT emit `faces_vertices`.

- [ ] **Step 1: Write the failing tests**

Create `mcp_harness/tests/test_square_complete.py`:

```python
import pytest
import square_complete as sq
import free_paper as fp

# A right-triangle hull filling the lower-left half of the unit square; the
# hypotenuse (1,0)-(0,1) cuts off the (1,1) corner. Border-only input is enough
# to exercise square-completion (complete_square ignores interior creases).
HULL_TRI = {
    "vertices_coords": [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]],
    "edges_vertices": [[0, 1], [1, 2], [2, 0]],
    "edges_assignment": ["B", "B", "B"],
}


def _b_loop_area(fold):
    """Area enclosed by the 'B' edges (assumes one simple border loop)."""
    from collections import defaultdict
    adj = defaultdict(list)
    for (a, b), asg in zip(fold["edges_vertices"], fold["edges_assignment"]):
        if asg == "B":
            adj[a].append(b); adj[b].append(a)
    start = next(iter(adj)); loop = [start]; prev = None; cur = start
    while True:
        nxt = [n for n in adj[cur] if n != prev][0]
        if nxt == start:
            break
        loop.append(nxt); prev, cur = cur, nxt
    return fp._polygon_area([tuple(fold["vertices_coords"][i]) for i in loop])


def _coord_set(fold):
    return {(round(p[0], 6), round(p[1], 6)) for p in fold["vertices_coords"]}


def test_adds_missing_corner():
    out = sq.complete_square(HULL_TRI, 1.0, 1.0)
    assert (1.0, 1.0) in _coord_set(out)


def test_border_loop_is_the_full_square():
    out = sq.complete_square(HULL_TRI, 1.0, 1.0)
    assert _b_loop_area(out) == pytest.approx(1.0, abs=1e-9)


def test_corner_cutting_chord_becomes_flat():
    out = sq.complete_square(HULL_TRI, 1.0, 1.0)
    ci = {tuple(p): i for i, p in enumerate(out["vertices_coords"])}
    a, b = ci[(1.0, 0.0)], ci[(0.0, 1.0)]          # the hypotenuse endpoints
    found = [asg for (u, v), asg in
             zip(out["edges_vertices"], out["edges_assignment"]) if {u, v} == {a, b}]
    assert found and all(f == "F" for f in found)


def test_no_op_when_already_square():
    square = {
        "vertices_coords": [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
        "edges_vertices": [[0, 1], [1, 2], [2, 3], [3, 0]],
        "edges_assignment": ["B", "B", "B", "B"],
    }
    assert sq.complete_square(square, 1.0, 1.0) == square


def test_no_border_returns_same_object():
    f = {"vertices_coords": [[0.1, 0.1]], "edges_vertices": [],
         "edges_assignment": []}
    assert sq.complete_square(f, 1.0, 1.0) is f


def test_deterministic():
    assert sq.complete_square(HULL_TRI, 1.0, 1.0) == sq.complete_square(HULL_TRI, 1.0, 1.0)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_square_complete.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'square_complete'`.

- [ ] **Step 3: Create the module**

Create `mcp_harness/square_complete.py`:

```python
"""Complete a TreeMaker hull crease pattern into a full-square FOLD.

TreeMaker creases only the convex hull of the leaf nodes, so build_and_export
emits a FOLD whose paper outline is that hull, not the square sheet (the
uncreased corners are omitted). This module adds the square's 4 corners and the
true border, reassigning the old hull-outline chords from border ("B") to flat
("F") so the leftover corner paper renders as flat uncreased faces. Geometry
only -- no engine/MCP/JVM imports.
"""
from __future__ import annotations

from free_paper import _on_boundary, _perimeter_coord, _rect_corners


def _key(p):
    return (round(p[0], 9), round(p[1], 9))


def complete_square(fold: dict, paper_w: float = 1.0, paper_h: float = 1.0) -> dict:
    vc = [[float(x), float(y)] for x, y in fold["vertices_coords"]]
    ev = [list(e) for e in fold["edges_vertices"]]
    ea = list(fold["edges_assignment"])

    idx_of = {_key(p): i for i, p in enumerate(vc)}

    def vertex_at(p):
        k = _key(p)
        if k not in idx_of:
            vc.append([float(p[0]), float(p[1])])
            idx_of[k] = len(vc) - 1
        return idx_of[k]

    border_vids = sorted({v for e, a in zip(ev, ea) if a == "B" for v in e})
    if not border_vids:                                  # no paper outline to fix
        return fold

    on_edge = [v for v in border_vids
               if _on_boundary(tuple(vc[v]), paper_w, paper_h)]

    # anchors = on-edge tips + the 4 square corners, ordered around the perimeter
    anchors = {}
    for v in on_edge:
        anchors[v] = _perimeter_coord(tuple(vc[v]), paper_w, paper_h)
    for cpt, ct in _rect_corners(paper_w, paper_h):
        anchors[vertex_at(cpt)] = ct
    order = sorted(anchors, key=lambda v: anchors[v])

    if len(order) == 4 and set(border_vids) == set(order):  # already a square
        return fold

    border_pairs = {frozenset((order[i], order[(i + 1) % len(order)]))
                    for i in range(len(order))}

    existing = {frozenset(e): i for i, e in enumerate(ev)}

    # corner-cutting chords -> flat; real square-side segments stay "B"
    for i, a in enumerate(ea):
        if a == "B" and frozenset(ev[i]) not in border_pairs:
            ea[i] = "F"
    # ensure every square-border segment exists as a "B" edge (walk order = stable)
    for i in range(len(order)):
        a, b = order[i], order[(i + 1) % len(order)]
        fs = frozenset((a, b))
        if fs in existing:
            ea[existing[fs]] = "B"
        else:
            ev.append([a, b]); ea.append("B"); existing[fs] = len(ev) - 1

    out = dict(fold)
    out["vertices_coords"] = vc
    out["edges_vertices"] = ev
    out["edges_assignment"] = ea
    return out
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_square_complete.py -v`
Expected: PASS — all six tests.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/square_complete.py mcp_harness/tests/test_square_complete.py
git commit -m "feat(square_complete): complete hull FOLD into a square (common case)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: `complete_square` — fully-interior hull (radial flat cuts)

**Files:**
- Modify: `mcp_harness/square_complete.py` (add a branch before the `out = dict(fold)` return)
- Test: `mcp_harness/tests/test_square_complete.py` (append cases)

**Interfaces:**
- Consumes: everything from Task 1 (`complete_square`, `_key`, the in-function `idx_of`/`existing`/`border_vids`/`on_edge`/`vc`/`ev`/`ea`).
- Produces: same `complete_square` signature; when no tip lies on a paper edge (`on_edge` empty), it additionally adds one radial `"F"` cut from each square corner to its nearest hull-loop vertex, so the square-minus-hull annulus splits into simple faces.

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_square_complete.py`:

```python
# A small triangle hull at the center -- no vertex touches any paper edge.
INNER_TRI = {
    "vertices_coords": [[0.4, 0.4], [0.6, 0.4], [0.5, 0.6]],
    "edges_vertices": [[0, 1], [1, 2], [2, 0]],
    "edges_assignment": ["B", "B", "B"],
}


def test_interior_hull_adds_four_corners_and_square_border():
    out = sq.complete_square(INNER_TRI, 1.0, 1.0)
    cs = _coord_set(out)
    for c in [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]:
        assert c in cs
    assert _b_loop_area(out) == pytest.approx(1.0, abs=1e-9)


def test_interior_hull_adds_radial_flat_cuts_from_each_corner():
    out = sq.complete_square(INNER_TRI, 1.0, 1.0)
    ci = {(round(p[0], 6), round(p[1], 6)): i
          for i, p in enumerate(out["vertices_coords"])}
    corners = [ci[c] for c in [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]]
    hull = {0, 1, 2}                                   # original interior hull vids
    for corner in corners:
        radial = [(u, v) for (u, v), a in
                  zip(out["edges_vertices"], out["edges_assignment"])
                  if a == "F" and corner in (u, v) and (set((u, v)) - {corner}) <= hull]
        assert radial, f"corner {corner} has no radial F cut"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_square_complete.py -k interior -v`
Expected: FAIL — `test_interior_hull_adds_radial_flat_cuts_from_each_corner` finds no radial `"F"` edges (annulus not split). `test_interior_hull_adds_four_corners_and_square_border` may already pass (corners + border are added by Task 1); both must pass after Step 3.

- [ ] **Step 3: Add the radial-cut branch**

In `mcp_harness/square_complete.py`, insert this block immediately before `out = dict(fold)`:

```python
    # Fully-interior hull (no tip on any paper edge): the square-minus-hull region
    # is an annulus, not a simple face. Add a radial "F" cut from each square
    # corner to its nearest hull-loop vertex so every resulting face is simple.
    if not on_edge:
        for cpt, _ct in _rect_corners(paper_w, paper_h):
            ci = idx_of[_key(cpt)]
            nearest = min(border_vids,
                          key=lambda v: (vc[v][0] - cpt[0]) ** 2
                          + (vc[v][1] - cpt[1]) ** 2)
            fs = frozenset((ci, nearest))
            if fs not in existing:
                ev.append([ci, nearest]); ea.append("F")
                existing[fs] = len(ev) - 1
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_square_complete.py -v`
Expected: PASS — all eight tests (the six common-case + two interior).

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/square_complete.py mcp_harness/tests/test_square_complete.py
git commit -m "feat(square_complete): handle fully-interior hull with radial flat cuts

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Wire squaring into both compile workers + golden bear test

**Files:**
- Modify: `mcp_harness/server.py` (add `_square_export` helper; call it in `_worker_full_base:103` and `_worker_compile_recipe:128`)
- Test: `mcp_harness/tests/test_square_complete.py` (append the engine-backed golden test)

**Interfaces:**
- Consumes: `square_complete.complete_square`; `server.draft_and_compile_full_base(tree_nodes, symmetric_pairs) -> str` (FOLD JSON or `"ERROR: ..."`); `mesh_acquire.query_to_metric_tree(prompt)` returning an object with `.nodes` and `.pairs`.
- Produces: `server._square_export(fold_str: str, w: float, h: float) -> str` (parses, squares, re-serializes; returns the input string unchanged on any failure). Both workers now emit squared FOLD.

- [ ] **Step 1: Write the failing golden test**

Append to `mcp_harness/tests/test_square_complete.py`:

```python
def test_bear_base_is_squared_through_the_worker(monkeypatch):
    # Engine-backed: the full compile path must now return a square FOLD with all
    # four paper corners present (was 1 of 4 before squaring).
    import os, json
    monkeypatch.setenv("MESH_PROVIDER", "fake")
    import mesh_acquire
    import server
    res = mesh_acquire.query_to_metric_tree("bear")
    fold_str = server.draft_and_compile_full_base(res.nodes, res.pairs)
    assert not fold_str.startswith("ERROR:"), fold_str[:300]
    fold = json.loads(fold_str)
    cs = {(round(p[0], 6), round(p[1], 6)) for p in fold["vertices_coords"]}
    for c in [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]:
        assert c in cs, f"missing square corner {c}"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_square_complete.py::test_bear_base_is_squared_through_the_worker -v`
Expected: FAIL — only `(1.0, 1.0)` is present; the assertion trips on `(0.0, 0.0)` (the worker still returns the raw hull FOLD).

- [ ] **Step 3: Add the `_square_export` helper**

In `mcp_harness/server.py`, add this top-level function just above `_worker_full_base` (line 84). `json` is already imported at module top:

```python
def _square_export(fold_str, paper_width, paper_height):
    """Complete the hull FOLD into a full square (corners + border + flat corner
    faces). Returns the input unchanged on any parse/transform failure so a
    squaring bug never breaks an otherwise-valid compile."""
    import square_complete
    try:
        fold = json.loads(fold_str)
    except (ValueError, TypeError):
        return fold_str
    try:
        return json.dumps(square_complete.complete_square(
            fold, paper_width, paper_height))
    except Exception:                                    # never fail the compile
        return fold_str
```

- [ ] **Step 4: Square the export in both workers**

In `mcp_harness/server.py`, change `_worker_full_base` line 103:

```python
        queue.put(("ok", _square_export(engine.build_and_export(),
                                        paper_width, paper_height)))
```

And `_worker_compile_recipe` line 128:

```python
        queue.put(("ok", _square_export(engine.build_and_export(),
                                        recipe["paper_width"], recipe["paper_height"])))
```

- [ ] **Step 5: Run the golden test + the pure suite**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_square_complete.py -v`
Expected: PASS — all nine tests including the engine-backed golden test.

- [ ] **Step 6: Run the existing compile/lint integration tests for regression**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_pipeline_dual.py -v`
Expected: PASS. If any test there asserts an exact pre-squaring vertex/edge count or an exact FOLD string, it is now stale because the served FOLD legitimately gained the square; update that expectation to the squared shape and note it in the task report. If none do, say so.

- [ ] **Step 7: Commit**

```bash
git add mcp_harness/server.py mcp_harness/tests/test_square_complete.py
git commit -m "feat(server): square the FOLD from both compile workers (corners + flat corners)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Verify in the viewport + lint delta + refresh fixture (CONTROLLER-RUN)

This task needs the engine `.so`, the Oriedita JVM linter, and a real browser (Playwright). It is **run by the SDD controller**, not delegated to an implementer subagent (mirrors the A-3 viewport task). No new unit tests; the deliverables are an observation record and a refreshed committed fixture.

- [ ] **Step 1: Measure the lint delta on the bear base**

Write `mcp_harness/probe_square_lint.py` that builds the bear base, lints the raw hull FOLD and the squared FOLD via `linter_server.validate_flat_foldability`, and prints both verdicts (violation counts + M/V-fixable vs geometry split). Run it. Record the before/after in the design doc.

Expected outcome (informational, not a gate): squaring does not ADD interior-vertex violations (corner vertices are degree-2 border vertices; corner paper is flat). If squaring resolves the hull-boundary Kawasaki failures, note it. **If squaring introduces NEW violations**, do NOT proceed to commit the fixture — apply the spec's fallback (square only the served/downloaded FOLD, keep lint on the raw hull) and surface the finding to the user.

- [ ] **Step 2: Regenerate the committed bear fixture**

Run: `cd <repo> && mcp_harness/.venv/bin/python scripts/make_hull_frontier_fixture.py`
This now flows through the squared worker, so `web/frontend/public/simulator/assets/ide/bear-base.fold` becomes the squared version. Confirm it has all four corners (the Task 3 golden test logic).

- [ ] **Step 3: Verify the viewport renders a square and folds without breaking**

Load the refreshed fixture in the vendored simulator via Playwright (the A-3 procedure: serve `web/frontend`, drive the bridge's `loadFold`/`setFold` postMessage path). Confirm: the 0% (flat) crease pattern is a **square** (four corners, full sheet), and folding 0→100% produces no NaN/exploded vertices and no `error` message. Record the result (and a screenshot, e.g. `docs/square-export-bear.png`).

- [ ] **Step 4: Commit the fixture + record the verdict**

```bash
git add web/frontend/public/simulator/assets/ide/bear-base.fold mcp_harness/probe_square_lint.py docs/superpowers/specs/2026-06-27-complete-square-export-design.md
git commit -m "test(square): refresh bear fixture to squared FOLD; record lint delta + viewport verdict

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Final verification (after all tasks)

- [ ] Run the full harness suite:

Run: `cd <repo> && make PYTHON=mcp_harness/.venv/bin/python test` (or, if the `.so` is already built, `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest -q`).
Expected: all tests pass (prior baseline + the new `test_square_complete.py`).

- [ ] Update `docs/followups-web-ui-and-foldability.md`: mark the A-3 "REFINEMENT" note RESOLVED with a pointer to this branch and the lint-delta/viewport verdict.
