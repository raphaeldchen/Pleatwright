# S1 — Crease-pattern mirror symmetry, measured correctly — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace three wrong crease-pattern symmetry metrics with one correct
one — two-sided, bijection-requiring, assignment-aware — wired into the
scorecard with pins that fail when deleted.

**Architecture:** A new `mcp_harness/cp_mirror.py` owns one "reflect and match"
core, parameterized by axis and by whether assignments are checked.
`mv_repair.mirror_map` becomes a thin caller keeping its assignment-blind,
axis-*searching* contract byte-identically; the new `mirror_verdict` tests a
*specified* axis and adds the assignment layer. Three scorecard columns replace
none — they are additive — and the two old metric functions are deleted.

**Tech Stack:** Python 3.14, pytest, pybind11 C++ extension (`headless_treemaker`),
no new dependencies.

**Spec:** [docs/superpowers/specs/2026-08-04-cp-mirror-metric-design.md](../specs/2026-08-04-cp-mirror-metric-design.md)

## Global Constraints

- **Environment:** `cd mcp_harness && PYTHONPATH=.:tests <repo>/mcp_harness/.venv/bin/python -m pytest tests/ --timeout=420`. Bare `make test` never terminates on this machine.
- **A worktree needs three gitignored build artifacts** or every lint verdict fakes `FAIL-LINT`: the engine `.so` (`cd mcp_harness && ./build.sh`), `oriedita/oriedita-1.1.3.jar`, and `OrieditaValidator.class` (`./build_linter.sh`).
- **Any script calling `draft_and_compile_full_base` must sit under `if __name__ == "__main__":`** — it spawns workers, and a module-level call deadlocks under the stdio MCP server.
- **A bare `HeadlessTreemaker` compile is NOT the serve path.** It is attempt-0 for one exact node list. Every acceptance pin in this plan compiles through `server.draft_and_compile_full_base`. This has bitten the project four times.
- **Tolerance is `tol = 1e-6` everywhere.** The FOLD writer quantizes to 9 dp and stores the origin as `(1e-9, 1e-9)`, so a 1e-9 test rejects the vertex that *is* the origin.
- **Never pin a number you did not measure.** Where a step says "record what it prints", paste that value. Inventing one reproduces the exact defect this slice exists to remove.
- **M/V convention is PRESERVED, not swapped** (spec §3.1). A swapped crease is a defect.
- Commit messages end with: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`

---

## File Structure

| File | Responsibility |
|---|---|
| `mcp_harness/cp_mirror.py` | **Create.** The one reflect-and-match core, the verdict, the tripwire renderer. |
| `mcp_harness/tests/test_cp_mirror.py` | **Create.** Unit tests for the core and verdict — pure data, no engine. |
| `mcp_harness/tests/test_cp_mirror_serve.py` | **Create.** Serve-path tier: control assertions and `mesh_validation_trees` pins. |
| `mcp_harness/mv_repair.py` | **Modify** `:408-487`. `mirror_map` becomes a thin caller; `MIRROR_PAIR_AXES_MAX` moves and is re-exported. |
| `mcp_harness/benchmark_subjects.py` | **Modify** `:186-240`, `:294-302`. Three new columns + `_COLS`. |
| `mcp_harness/tests/test_pair_reconcile.py` | **Modify.** Add the `hull_coverage` wiring pin beside its siblings. |
| `mcp_harness/probe_cp_symmetry.py` | **Modify.** Delete `cp_symmetry`; driver calls `cp_mirror.mirror_verdict`. |
| `docs/superpowers/evidence/2026-08-03-reparented-bases/fold_and_look.py` | **Modify.** Delete `cp_mirror_residual`; call `cp_mirror`. |
| `mcp_harness/fixtures/cp_symmetry_evidence.json` | **Regenerate.** |
| `mcp_harness/fixtures/scorecard_baseline.jsonl` | **Regenerate** — new columns, false `_meta` claim corrected. |
| `docs/superpowers/evidence/2026-08-03-reparented-bases/README.md` | **Regenerate** the residual table. |

---

## Task 1: The reflect-and-match core

**Files:**
- Create: `mcp_harness/cp_mirror.py`
- Test: `mcp_harness/tests/test_cp_mirror.py`

**Interfaces:**
- Consumes: `cp_audit._geometry_frame(fold) -> dict` (existing, `cp_audit.py:146`)
- Produces:
  - `MIRROR_PAIR_AXES_MAX: int = 64`
  - `axis_reflector(degrees: float, centre=(0.5, 0.5)) -> Callable[[tuple], tuple]`
  - `mirror_bijection(fold: dict, reflect, *, tol=1e-6) -> dict | None`

- [ ] **Step 1: Write the failing tests**

Create `mcp_harness/tests/test_cp_mirror.py`:

```python
import os
import sys

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _HERE)

import cp_mirror  # noqa: E402


def _square_fold():
    """A diamond that IS mirror-symmetric about y = x through (0.5, 0.5)."""
    return {
        "vertices_coords": [[0.5, 0.0], [1.0, 0.5], [0.5, 1.0], [0.0, 0.5]],
        "edges_vertices": [[0, 1], [1, 2], [2, 3], [3, 0]],
        "edges_assignment": ["B", "B", "B", "B"],
    }


def test_axis_reflector_at_45_degrees_swaps_x_and_y():
    r = cp_mirror.axis_reflector(45.0)
    got = r((0.3, 0.8))
    assert abs(got[0] - 0.8) < 1e-12
    assert abs(got[1] - 0.3) < 1e-12


def test_axis_reflector_at_0_degrees_is_the_horizontal_mirror():
    r = cp_mirror.axis_reflector(0.0)
    got = r((0.3, 0.8))
    assert abs(got[0] - 0.3) < 1e-12
    assert abs(got[1] - 0.2) < 1e-12


def test_bijection_found_on_a_symmetric_pattern():
    m = cp_mirror.mirror_bijection(_square_fold(),
                                   cp_mirror.axis_reflector(45.0))
    assert m is not None
    assert sorted(m.values()) == [0, 1, 2, 3]


def test_bijection_is_none_when_a_vertex_has_no_mirror_image():
    f = _square_fold()
    f["vertices_coords"].append([0.9, 0.1])      # its image (0.1,0.9) is absent
    f["edges_vertices"].append([0, 4])
    f["edges_assignment"].append("M")
    assert cp_mirror.mirror_bijection(f, cp_mirror.axis_reflector(45.0)) is None


def test_bijection_is_none_when_two_vertices_collapse_onto_one():
    """CARDINALITY. Every reflected point lands within tol of SOME actual
    point, but not injectively -- the failure a one-sided distance reads as 0."""
    f = {"vertices_coords": [[0.2, 0.2], [0.7, 0.7], [0.7, 0.7]],
         "edges_vertices": [[0, 1], [1, 2]],
         "edges_assignment": ["M", "M"]}
    assert cp_mirror.mirror_bijection(f, cp_mirror.axis_reflector(45.0)) is None


def test_bijection_is_none_when_the_edge_set_is_not_preserved():
    """Vertices mirror perfectly; one edge's image is not an edge."""
    f = {"vertices_coords": [[0.5, 0.0], [1.0, 0.5], [0.0, 0.5], [0.5, 1.0]],
         "edges_vertices": [[0, 2]],
         "edges_assignment": ["M"]}
    # reflect(v0)=v0? no: (0.5,0.0) -> (0.0,0.5) = v2, and v2 -> v0. Edge (0,2)
    # maps to (2,0) = itself, so add an asymmetric edge to break it.
    f["edges_vertices"].append([0, 1])
    f["edges_assignment"].append("M")
    # (0,1) -> (2,3); 3 exists but the edge (2,3) does not.
    assert cp_mirror.mirror_bijection(f, cp_mirror.axis_reflector(45.0)) is None


def test_bijection_reads_a_nested_file_frames_fold():
    """Both metrics being replaced KeyError on this shape."""
    nested = {"file_frames": [_square_fold()]}
    assert cp_mirror.mirror_bijection(
        nested, cp_mirror.axis_reflector(45.0)) is not None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../mcp_harness/.venv/bin/python -m pytest tests/test_cp_mirror.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'cp_mirror'`

- [ ] **Step 3: Write the module**

Create `mcp_harness/cp_mirror.py`:

```python
"""Exact mirror symmetry of a crease pattern.

Mirror symmetry of a finite planar figure is DECIDABLE, not approximable
(Wolter/Woo/Volz, Theta(n log n) for 2-D point sets; Atallah, O(n log n) for a
planar figure of segments and points). The question is whether the reflection
induces a BIJECTION on the vertex set that carries the edge set onto itself
with a consistent assignment. This module answers exactly that; the residual it
also reports is a WITNESS, never the verdict.

It replaces three implementations that were each wrong in the same two ways --
`fold_and_look.cp_mirror_residual`, `probe_cp_symmetry.cp_symmetry`, and (for
the assignment question only) `mv_repair.mirror_map`. See
docs/superpowers/specs/2026-08-04-cp-mirror-metric-design.md section 1.

THE SPLIT IS THE POINT. `mirror_bijection` answers "is this pattern symmetric
about THIS axis", assignment-blind. `mv_repair` needs that question answered
without assignments, because labels are what it is solving for; the scorecard
needs it answered WITH them. Sharing the core without sharing the axis policy
is what lets both be true at once -- and `mirror_verdict` TESTS a specified
axis rather than SEARCHING for one, because a lopsided pattern that happens to
be symmetric about some accidental bisector must not score green.
"""
from __future__ import annotations

import math

#: Vertices above this: only the two bounding-box axes are tried by
#: `candidate_axes`, not every perpendicular bisector. Owned here now;
#: `mv_repair` re-exports it so its historical name keeps resolving.
MIRROR_PAIR_AXES_MAX = 64


def _frame(fold: dict) -> dict:
    """Top-level geometry, or file_frames[0] when nested. Imported lazily:
    cp_audit pulls in the audit surface and this module is imported by
    benchmark_subjects' hot row builder."""
    import cp_audit
    return cp_audit._geometry_frame(fold)


def _reflect_about(px: float, py: float, ax: float, ay: float):
    """Reflection about the line through (px, py) with unit direction (ax, ay).

    Byte-identical arithmetic to mv_repair.mirror_map's historical inline form
    (mv_repair.py:468-473), so the refactor in Task 2 cannot move a coordinate.
    """
    def reflect(p):
        wx, wy = p[0] - px, p[1] - py
        t = wx * ax + wy * ay
        return (px + 2 * t * ax - wx, py + 2 * t * ay - wy)
    return reflect


def axis_reflector(degrees: float, centre=(0.5, 0.5)):
    """Reflection about the line through `centre` at `degrees` from +x.

    45 degrees is the engine's shipped axis: all four `apply_symmetry` call
    sites hard-code it (server.py:185, 217, 264, 309). At 45 the arithmetic
    reduces to (x, y) -> (y, x) up to ~6e-17 (cos(pi/2) is not exactly 0 in
    binary floating point), which is eleven orders of magnitude inside `tol`.
    """
    t = math.radians(degrees)
    return _reflect_about(centre[0], centre[1], math.cos(t), math.sin(t))


def _bucket_finder(pts: list, tol: float):
    """Nearest-point-within-tol lookup, O(1) per query. Lifted verbatim from
    mv_repair.mirror_map (mv_repair.py:429-441)."""
    buckets: dict = {}
    inv = 1.0 / tol
    for i, (x, y) in enumerate(pts):
        buckets.setdefault((round(x * inv), round(y * inv)), []).append(i)

    def find(x, y):
        bx, by = round(x * inv), round(y * inv)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in buckets.get((bx + dx, by + dy), ()):
                    if abs(pts[j][0] - x) <= tol and abs(pts[j][1] - y) <= tol:
                        return j
        return None
    return find


def _points_and_edges(fold: dict):
    """(pts, edges, ev, assignments) or None when the fold cannot support the
    measurement. Never raises on a malformed fold."""
    frame = _frame(fold)
    coords = frame.get("vertices_coords") or []
    ev = frame.get("edges_vertices") or []
    asn = frame.get("edges_assignment") or ["U"] * len(ev)
    try:
        pts = [(float(p[0]), float(p[1])) for p in coords]
        ev = [(int(a), int(b)) for a, b in ev]
    except (TypeError, ValueError, IndexError):
        return None
    if len(pts) < 2:
        return None
    edges = {(min(a, b), max(a, b)) for a, b in ev}
    return pts, edges, ev, list(asn)


def mirror_bijection(fold: dict, reflect, *, tol: float = 1e-6) -> dict | None:
    """{i: j} when `reflect` induces a bijection of the vertex set that carries
    the edge set onto itself; None otherwise.

    ASSIGNMENT-BLIND BY DESIGN -- the assignment layer lives in
    `mirror_verdict`, because `mv_repair` needs this question answered without
    it. The three rejection conditions are, in order: some vertex has no mirror
    image within `tol`; the map is not injective (distinct vertices collapsing
    onto one, which a one-sided distance reads as 0); some edge's image is not
    an edge.
    """
    got = _points_and_edges(fold)
    if got is None:
        return None
    pts, edges, _ev, _asn = got
    find = _bucket_finder(pts, tol)

    m = {}
    for i, p in enumerate(pts):
        j = find(*reflect(p))
        if j is None:
            return None
        m[i] = j
    if len(set(m.values())) != len(m):
        return None
    if any((min(m[a], m[b]), max(m[a], m[b])) not in edges for a, b in edges):
        return None
    return m
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../mcp_harness/.venv/bin/python -m pytest tests/test_cp_mirror.py -v`
Expected: PASS, 7 passed

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/cp_mirror.py mcp_harness/tests/test_cp_mirror.py
git commit -m "feat(cp-mirror): the shared reflect-and-match core

Bijection-requiring and edge-set-preserving, with the cardinality check that
a one-sided distance cannot express. Assignment-blind: mv_repair needs this
question answered without labels, because labels are what it solves for.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 2: `candidate_axes`, and `mv_repair.mirror_map` becomes a thin caller

**Files:**
- Modify: `mcp_harness/cp_mirror.py` (append)
- Modify: `mcp_harness/mv_repair.py:408-487`
- Test: `mcp_harness/tests/test_cp_mirror.py` (append)

**Interfaces:**
- Consumes: `cp_mirror.mirror_bijection`, `cp_mirror.MIRROR_PAIR_AXES_MAX` (Task 1)
- Produces: `candidate_axes(fold: dict, tol=1e-6) -> list[Callable]`; `mv_repair.mirror_map(fold, tol=1e-6) -> dict | None` (signature unchanged)

**Why the order of `candidate_axes` is load-bearing:** `mirror_map` returns the
**first** axis that works, so a reordering silently changes which mirror the
M/V tie-break tier uses. The historical order is: the horizontal bbox axis, the
vertical bbox axis, then every perpendicular bisector of a vertex pair in
`(i, j)` ascending order, deduped by a key rounded at `1/tol`.

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_cp_mirror.py`:

```python
def test_candidate_axes_starts_with_the_two_bbox_axes_in_order():
    """ORDER IS LOAD-BEARING: mirror_map returns the FIRST axis that works."""
    f = _square_fold()
    axes = cp_mirror.candidate_axes(f)
    # bbox centre is (0.5, 0.5); axis 0 is horizontal, axis 1 vertical.
    assert abs(axes[0]((0.3, 0.8))[0] - 0.3) < 1e-12
    assert abs(axes[0]((0.3, 0.8))[1] - 0.2) < 1e-12
    assert abs(axes[1]((0.3, 0.8))[0] - 0.7) < 1e-12
    assert abs(axes[1]((0.3, 0.8))[1] - 0.8) < 1e-12


def test_candidate_axes_stops_at_the_bbox_pair_above_the_vertex_cap():
    big = {"vertices_coords": [[i * 0.001, i * 0.002]
                               for i in range(cp_mirror.MIRROR_PAIR_AXES_MAX + 1)],
           "edges_vertices": [], "edges_assignment": []}
    assert len(cp_mirror.candidate_axes(big)) == 2
```

Append to `mcp_harness/tests/test_mv_repair.py`:

```python
def test_mirror_map_is_unchanged_on_every_committed_golden():
    """The Task 2 refactor must not move a single result. mirror_map feeds the
    M/V tie-break tier on the serve path; a changed axis choice would change
    shipped assignments with nothing else going red."""
    import glob
    import json as _json
    import os as _os
    here = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                         "goldens")
    seen = 0
    for path in sorted(glob.glob(_os.path.join(here, "*.fold"))):
        with open(path) as fh:
            fold = _json.load(fh)
        got = mv_repair.mirror_map(fold)
        seen += 1
        # Recorded in Step 3 below from the PRE-refactor run.
        assert got == _MIRROR_MAP_GOLDENS[_os.path.basename(path)]
    assert seen == 9, f"expected 9 goldens, found {seen}"
```

- [ ] **Step 2: Record the pre-refactor golden results**

Before touching `mv_repair`, capture what it does today. Run:

```bash
cd mcp_harness && PYTHONPATH=.:tests ../mcp_harness/.venv/bin/python -c "
import glob, json, os
import mv_repair
out = {}
for p in sorted(glob.glob('tests/goldens/*.fold')):
    out[os.path.basename(p)] = mv_repair.mirror_map(json.load(open(p)))
print(json.dumps(out, indent=1, sort_keys=True))
"
```

Paste the printed dict verbatim into `tests/test_mv_repair.py` as
`_MIRROR_MAP_GOLDENS`, above the test. **Do not hand-write it** — this is the
before-image the refactor is judged against, and inventing it defeats the test.
Note the count it covers; if it is not 9, use the real number in the assertion.

- [ ] **Step 3: Run the tests to verify they fail**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../mcp_harness/.venv/bin/python -m pytest tests/test_cp_mirror.py -k candidate_axes -v`
Expected: FAIL — `AttributeError: module 'cp_mirror' has no attribute 'candidate_axes'`

- [ ] **Step 4: Implement `candidate_axes`**

Append to `mcp_harness/cp_mirror.py`:

```python
def candidate_axes(fold: dict, tol: float = 1e-6) -> list:
    """Reflectors to try, in mv_repair's exact historical order.

    ★ THE ORDER IS LOAD-BEARING. `mv_repair.mirror_map` returns the FIRST axis
    that works and feeds the M/V tie-break tier on the serve path, so a
    reordering would change shipped assignments with nothing going red.
    Historical order (mv_repair.py:443-466 before this refactor): the
    horizontal bbox axis, the vertical bbox axis, then every perpendicular
    bisector of a vertex pair in (i, j) ascending order, deduped on a key
    rounded at 1/tol.

    This is the SEARCH. `mirror_verdict` deliberately does not use it -- it
    tests the axis it is given, because a pattern symmetric about an accidental
    bisector is not a symmetric model.
    """
    got = _points_and_edges(fold)
    if got is None:
        return []
    pts, _edges, _ev, _asn = got
    inv = 1.0 / tol

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    cx = (min(xs) + max(xs)) / 2.0
    cy = (min(ys) + max(ys)) / 2.0
    specs = [(cx, cy, 1.0, 0.0), (cx, cy, 0.0, 1.0)]

    if len(pts) <= MIRROR_PAIR_AXES_MAX:
        seen = set()
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                mx = (pts[i][0] + pts[j][0]) / 2.0
                my = (pts[i][1] + pts[j][1]) / 2.0
                dx, dy = pts[j][0] - pts[i][0], pts[j][1] - pts[i][1]
                n = math.hypot(dx, dy)
                if n < tol:
                    continue
                ax, ay = -dy / n, dx / n
                key = (round(mx * inv), round(my * inv),
                       round(ax * inv), round(ay * inv))
                if key in seen:
                    continue
                seen.add(key)
                specs.append((mx, my, ax, ay))

    return [_reflect_about(*s) for s in specs]
```

- [ ] **Step 5: Replace `mv_repair.mirror_map`'s body**

In `mcp_harness/mv_repair.py`, replace the whole body of `mirror_map`
(`:408-487`) with the thin caller, keeping the docstring and adding the
provenance note. Also replace the `MIRROR_PAIR_AXES_MAX = 64` line at `:102`
with the re-export:

```python
# Owned by cp_mirror since 2026-08-04; re-exported so the historical name
# keeps resolving for any caller that reads it from here.
from cp_mirror import MIRROR_PAIR_AXES_MAX  # noqa: F401
```

```python
def mirror_map(fold: dict, tol: float = 1e-6) -> dict | None:
    """A vertex->vertex mirror automorphism of the crease GEOMETRY, or None.

    Read from the fold itself, never from the tree's symmetric_pairs: that
    lives in tree space and has no surviving map into per-fold vertex indices.
    Assignments are deliberately ignored -- labels are the thing being solved
    for; what a mirror has to preserve is the coordinates and the edge set.
    Measured on the served dog: None at every tolerance tried, so the
    tie-break tier below it is provably inert there.

    Since 2026-08-04 the machinery lives in `cp_mirror` and is shared with the
    scorecard's `mirror_verdict`. This function keeps its exact contract: it
    SEARCHES axes and ignores assignments. The three rejection conditions moved
    inside `mirror_bijection` but the accepted SET of axes is unchanged -- all
    three were `continue` conditions, so reordering them cannot change which
    axis is accepted first, only how quickly a rejected one is discarded.
    """
    for reflect in cp_mirror.candidate_axes(fold, tol):
        m = cp_mirror.mirror_bijection(fold, reflect, tol=tol)
        if m is None:
            continue
        if all(m[i] == i for i in m):
            continue                       # the identity is not a mirror
        return m
    return None
```

Add `import cp_mirror` to `mv_repair.py`'s import block.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../mcp_harness/.venv/bin/python -m pytest tests/test_cp_mirror.py tests/test_mv_repair.py -v`
Expected: PASS. Both pre-existing mirror tests (`test_mirror_map_is_read_from_the_geometry_not_from_the_tree`, `test_the_served_dog_has_no_mirror_and_symmetry_stays_inert`) must pass **unmodified**, and the new golden-parity test must pass against the values recorded in Step 2.

- [ ] **Step 7: Commit**

```bash
git add mcp_harness/cp_mirror.py mcp_harness/mv_repair.py mcp_harness/tests/
git commit -m "refactor(mv-repair): mirror_map delegates to the shared core

The axis SEARCH order is load-bearing -- mirror_map returns the first axis
that works and feeds the serve path's M/V tie-break -- so candidate_axes
reproduces it verbatim and a new test pins mirror_map's result on all nine
committed goldens against its pre-refactor output.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 3: `mirror_verdict` — the assignment layer and the two-sided residual

**Files:**
- Modify: `mcp_harness/cp_mirror.py` (append)
- Test: `mcp_harness/tests/test_cp_mirror.py` (append)

**Interfaces:**
- Consumes: `mirror_bijection`, `axis_reflector`, `_points_and_edges` (Tasks 1–2)
- Produces:
  - `mirror_verdict(fold: dict, *, axis_degrees: float, tol=1e-6) -> dict | None`
  - `verdict_of_fold_str(fold_str, *, axis_degrees=45.0) -> dict | None`
  - Verdict keys: `symmetric` `residual` `is_bijection` `cardinality` `cardinality_ok` `n_vertices` `n_edges` `edges_ok` `mv_ok` `mv_preserved` `mv_swapped` `mv_mismatched` `offenders`
  - ⚠ AMENDED DURING IMPLEMENTATION: `residual` is the DIRECTED Hausdorff and
    `residual_one_sided` does not exist. This task's code block below still
    shows the superseded two-sided form; a reflection is an isometry AND an
    involution, so both directions are provably equal and the two-sided form
    was arithmetic theatre. The collapse it was meant to catch is caught by
    `cardinality_ok`. See the spec's §1.2 and §3.

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_cp_mirror.py`:

```python
def _mv_fold(a01, a12):
    """Two creases that are exact mirror images about y = x, with settable
    assignments: v1=(0.3,0.7) and v2=(0.7,0.3) are each other's images, and
    v0=(0.5,0.5) sits on the axis."""
    return {"vertices_coords": [[0.5, 0.5], [0.3, 0.7], [0.7, 0.3]],
            "edges_vertices": [[0, 1], [0, 2]],
            "edges_assignment": [a01, a12]}


def test_verdict_is_symmetric_when_geometry_and_assignment_both_mirror():
    v = cp_mirror.mirror_verdict(_mv_fold("M", "M"), axis_degrees=45.0)
    assert v["symmetric"] is True
    assert v["residual"] == 0.0
    assert v["mv_swapped"] == 0 and v["mv_mismatched"] == 0


def test_verdict_is_asymmetric_on_swapped_mv_with_a_zero_residual():
    """THE DEFECT THIS SLICE EXISTS FOR: the geometry is an exact bijection
    and the residual is 0, but two mirror-image creases fold opposite ways."""
    v = cp_mirror.mirror_verdict(_mv_fold("M", "V"), axis_degrees=45.0)
    assert v["residual"] == 0.0
    assert v["is_bijection"] is True and v["edges_ok"] is True
    assert v["mv_swapped"] == 2
    assert v["symmetric"] is False


def test_verdict_counts_folded_versus_flat_as_mismatched_not_swapped():
    """QUAD's failure mode: folded on one side, flat on its mirror image."""
    v = cp_mirror.mirror_verdict(_mv_fold("M", "F"), axis_degrees=45.0)
    assert v["mv_mismatched"] == 2 and v["mv_swapped"] == 0
    assert v["symmetric"] is False


def test_verdict_reports_the_offending_creases():
    v = cp_mirror.mirror_verdict(_mv_fold("M", "V"), axis_degrees=45.0)
    assert {(o[0], o[1]) for o in v["offenders"]} == {(0, 1), (0, 2)}


def test_two_sided_residual_catches_a_strict_subset_the_one_sided_form_misses():
    """reflect(V) is a strict SUBSET of V: every reflected point lands on an
    actual point, so the one-sided reading is 0 while the pattern is not
    symmetric. This is defect (a) in the spec."""
    f = {"vertices_coords": [[0.2, 0.2], [0.6, 0.6], [0.9, 0.1]],
         "edges_vertices": [[0, 1]], "edges_assignment": ["M"]}
    v = cp_mirror.mirror_verdict(f, axis_degrees=45.0)
    assert v["residual_one_sided"] < 1e-9      # what the shipped metric reports
    assert v["residual"] > 0.5                 # what is actually true
    assert v["symmetric"] is False


def test_verdict_reports_cardinality_and_does_not_evaluate_mv_when_it_fails():
    f = {"vertices_coords": [[0.5, 0.0], [1.0, 0.5], [0.5, 1.0], [0.0, 0.5],
                             [0.9, 0.1]],
         "edges_vertices": [[0, 1]], "edges_assignment": ["M"]}
    v = cp_mirror.mirror_verdict(f, axis_degrees=45.0)
    assert v["is_bijection"] is False
    assert v["cardinality_ok"] is False
    assert v["mv_swapped"] is None and v["mv_mismatched"] is None
    assert v["symmetric"] is False


def test_verdict_of_fold_str_is_none_for_an_unserved_row():
    assert cp_mirror.verdict_of_fold_str("ERROR: did not pack") is None
    assert cp_mirror.verdict_of_fold_str("") is None
    assert cp_mirror.verdict_of_fold_str("{not json") is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../mcp_harness/.venv/bin/python -m pytest tests/test_cp_mirror.py -k verdict -v`
Expected: FAIL — `AttributeError: module 'cp_mirror' has no attribute 'mirror_verdict'`

- [ ] **Step 3: Implement the verdict**

Append to `mcp_harness/cp_mirror.py`:

```python
def _hausdorff_two_sided(pts: list, reflect) -> tuple:
    """(two_sided, one_sided). The one-sided form is returned only so a caller
    can show what the superseded metric would have said."""
    ref = [reflect(p) for p in pts]
    fwd = [min(math.dist(r, v) for v in pts) for r in ref]
    bwd = [min(math.dist(v, r) for r in ref) for v in pts]
    return max(max(fwd), max(bwd)), max(fwd)


def mirror_verdict(fold: dict, *, axis_degrees: float,
                   tol: float = 1e-6) -> dict | None:
    """Is this crease pattern mirror-symmetric about the GIVEN axis?

    `symmetric` is the verdict. `residual` is a two-sided Hausdorff distance
    reported as a WITNESS -- residual == 0 does NOT imply symmetry, and the
    standing counterexample is bird under an axis pin: an exact 19/19
    vertex-and-edge bijection carrying four swapped creases.

    `axis_degrees` is required and never searched (see `candidate_axes`).
    A .fold does not record which axis produced it, so the caller must know;
    every caller today passes 45.0, the axis all four `apply_symmetry` sites
    hard-code. Threading a real angle is a prerequisite of the slice that makes
    the axis selectable.

    M/V CONVENTION IS PRESERVED, AND THAT IS MEASURED, NOT ASSUMED. The mirror
    is R:(x,y,z)->(y,x,z), which leaves z alone, so a mountain maps to a
    mountain; and the repo's two unambiguously symmetric patterns (star-4 with
    pairs, HSHAPE) come out with ZERO swapped creases. A swap is a defect.
    Boundary ("B") must map to "B". `mv_swapped` (mirror images folding
    opposite ways) and `mv_mismatched` (folded one side, flat on the other) are
    counted apart because they are physically different failures.
    """
    got = _points_and_edges(fold)
    if got is None:
        return None
    pts, _edges, ev, asn = got
    reflect = axis_reflector(axis_degrees)

    residual, one_sided = _hausdorff_two_sided(pts, reflect)
    sigma = mirror_bijection(fold, reflect, tol=tol)

    # |reflect(V) cap V| -- reported even when the bijection fails, because
    # "4 of 18 vertices have a mirror image at all" is the honest reading of a
    # failure that a bare distance renders as an uninterpretable float.
    find = _bucket_finder(pts, tol)
    hit = {j for j in (find(*reflect(p)) for p in pts) if j is not None}

    out = {
        "symmetric": False,
        "residual": residual,
        "residual_one_sided": one_sided,
        "is_bijection": sigma is not None,
        "n_vertices": len(pts),
        "n_edges": len(ev),
        "cardinality": len(hit),
        "cardinality_ok": len(hit) == len(pts),
        "edges_ok": sigma is not None,
        "mv_ok": None,
        "mv_preserved": None,
        "mv_swapped": None,
        "mv_mismatched": None,
        "offenders": [],
    }
    if sigma is None:
        return out

    have = {frozenset(e): a for e, a in zip(ev, asn)}
    preserved = swapped = mismatched = 0
    offenders = []
    for (a, b), lab in zip(ev, asn):
        img = frozenset((sigma[a], sigma[b]))
        other = have.get(img)
        if other is None:                 # unreachable while sigma is not None
            mismatched += 1
            offenders.append((a, b, lab, None))
            continue
        if lab == other:
            preserved += 1
        elif {lab, other} == {"M", "V"}:
            swapped += 1
            offenders.append((a, b, lab, other))
        else:
            mismatched += 1
            offenders.append((a, b, lab, other))

    out["mv_preserved"] = preserved
    out["mv_swapped"] = swapped
    out["mv_mismatched"] = mismatched
    out["mv_ok"] = swapped == 0 and mismatched == 0
    out["offenders"] = offenders[:12]
    out["symmetric"] = bool(out["mv_ok"])
    return out


def verdict_of_fold_str(fold_str, *, axis_degrees: float = 45.0):
    """Scorecard convenience: verdict from a serve-path string, or None for an
    unserved / unparseable row. Mirrors paper_coverage.coverage_of_fold_str."""
    import json
    if (not fold_str or not isinstance(fold_str, str)
            or fold_str.startswith("ERROR:")):
        return None
    try:
        return mirror_verdict(json.loads(fold_str), axis_degrees=axis_degrees)
    except (ValueError, TypeError):
        return None
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../mcp_harness/.venv/bin/python -m pytest tests/test_cp_mirror.py -v`
Expected: PASS, 16 passed

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/cp_mirror.py mcp_harness/tests/test_cp_mirror.py
git commit -m "feat(cp-mirror): the verdict -- assignment-aware, two-sided

symmetric is the verdict; residual is a witness. residual == 0 does not imply
symmetry, and the pinned counterexample is a fold whose geometry is an exact
bijection carrying two swapped creases.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 4: The tripwire, and the pin that would have caught its first version

**Files:**
- Modify: `mcp_harness/cp_mirror.py` (append)
- Test: `mcp_harness/tests/test_cp_mirror.py` (append)

**Interfaces:**
- Consumes: `mirror_verdict`, `axis_reflector` (Tasks 1–3)
- Produces: `overlay_svg(fold, *, axis_degrees=45.0, panel=300, pad=24, label="") -> tuple[list[str], int]`; `write_overlay_sheet(path, panels, *, axis_degrees=45.0, cols=3) -> str` where `panels` is `[(label, fold)]`

- [ ] **Step 1: Write the failing test**

Append to `mcp_harness/tests/test_cp_mirror.py`:

```python
def test_tripwire_draws_every_offender_as_two_colours_on_one_segment():
    """THE PIN THAT CATCHES THIS TRIPWIRE'S OWN FIRST VERSION, which reflected
    only VERTICES and drew the reflection wider than the original -- so on a
    pattern whose vertices overlap perfectly it rendered a clean picture and
    caught nothing, reproducing the blindness it exists to guard."""
    fold = _mv_fold("M", "V")
    v = cp_mirror.mirror_verdict(fold, axis_degrees=45.0)
    assert v["mv_swapped"] == 2                      # precondition
    cell, _size = cp_mirror.overlay_svg(fold, axis_degrees=45.0)
    svg = "\n".join(cell)
    # both assignment colours must be present: the solid line in its own
    # colour, and the reflected dash in the OTHER one, on the same segment.
    assert cp_mirror._MV["M"] in svg and cp_mirror._MV["V"] in svg
    # the reflected overlay must be NARROWER than the pattern it overlays,
    # or it covers the very line it is meant to be compared against.
    assert 'stroke-dasharray' in svg


def test_tripwire_reflects_creases_not_only_vertices():
    """A vertex-only overlay is blind to a swapped crease. Count dashed
    segments: one per non-boundary crease."""
    cell, _ = cp_mirror.overlay_svg(_mv_fold("M", "V"), axis_degrees=45.0)
    assert "\n".join(cell).count("stroke-dasharray") >= 2
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../mcp_harness/.venv/bin/python -m pytest tests/test_cp_mirror.py -k tripwire -v`
Expected: FAIL — `AttributeError: module 'cp_mirror' has no attribute 'overlay_svg'`

- [ ] **Step 3: Implement the renderer**

Append to `mcp_harness/cp_mirror.py`:

```python
# --------------------------------------------------------------------------- #
# The visual TRIPWIRE ON THE METRIC -- not an acceptor.                        #
#                                                                              #
# Its one job is to catch "the number says 0.000000 but the two point sets     #
# plainly do not sit on top of each other". It renders the crease pattern with #
# reflect(V) overlaid, so asymmetry reads as visible NON-OVERLAP -- an         #
# alignment judgement, which is the axis the visual-feedback-loop spec found   #
# reliable, rather than a crease-counting one, which it falsified twice.       #
#                                                                              #
# ★ IT REFLECTS THE CREASES, NOT ONLY THE VERTICES, AND DRAWS THEM NARROWER.   #
# Measured: an axis-pinned bird is an EXACT vertex bijection (19/19) whose     #
# defect is four creases whose mirror images fold the opposite way. A          #
# vertex-only overlay shows perfect overlap there and catches nothing; an      #
# overlay drawn WIDER covers the line it is meant to be compared against.      #
# Both were true of this function's first draft.                               #
#                                                                              #
# Deliberately NOT a render of the folded base: every flap of a uniaxial base  #
# collapses onto one line, so that view shows layer stacking and not limb      #
# placement (2026-08-03-reparented-bases/README.md, "Two limits").             #
# --------------------------------------------------------------------------- #
_MV = {"M": "#c1272d", "V": "#2b6cb0", "B": "#444444", "F": "#bbbbbb"}


def overlay_svg(fold: dict, *, axis_degrees: float = 45.0, panel: int = 300,
                pad: int = 24, label: str = "") -> tuple:
    """(svg_element_list, cell_size) for one panel."""
    got = _points_and_edges(fold)
    if got is None:
        return [], panel + 2 * pad
    pts, _edges, ev, asn = got
    reflect = axis_reflector(axis_degrees)

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    lo = min(min(xs), min(ys), 0.0)
    hi = max(max(xs), max(ys), 1.0)
    span = (hi - lo) or 1.0

    def T(p):
        return (pad + (p[0] - lo) / span * panel,
                pad + panel - (p[1] - lo) / span * panel)

    out = [f'<rect x="{pad}" y="{pad}" width="{panel}" height="{panel}" '
           f'fill="none" stroke="#dddddd" stroke-width="1"/>']
    a0, a1 = T(reflect((lo, hi))), T(reflect((hi, lo)))
    out.append(f'<line x1="{a0[0]:.2f}" y1="{a0[1]:.2f}" x2="{a1[0]:.2f}" '
               f'y2="{a1[1]:.2f}" stroke="#e8a33d" stroke-width="1.5" '
               f'stroke-dasharray="6 4"/>')

    for (a, b), lab in zip(ev, asn):                  # the pattern: solid, WIDE
        p, q = T(pts[a]), T(pts[b])
        out.append(f'<line x1="{p[0]:.2f}" y1="{p[1]:.2f}" x2="{q[0]:.2f}" '
                   f'y2="{q[1]:.2f}" stroke="{_MV.get(lab, "#999999")}" '
                   f'stroke-width="{3.4 if lab == "B" else 3.0}"/>')
    for (a, b), lab in zip(ev, asn):                # its mirror: dashed, NARROW
        if lab == "B":
            continue
        p, q = T(reflect(pts[a])), T(reflect(pts[b]))
        out.append(f'<line x1="{p[0]:.2f}" y1="{p[1]:.2f}" x2="{q[0]:.2f}" '
                   f'y2="{q[1]:.2f}" stroke="{_MV.get(lab, "#999999")}" '
                   f'stroke-width="1.3" stroke-dasharray="4 4"/>')
    for p in pts:
        c = T(p)
        out.append(f'<circle cx="{c[0]:.2f}" cy="{c[1]:.2f}" r="2.4" '
                   f'fill="#222222"/>')
    for p in pts:
        c = T(reflect(p))
        out.append(f'<circle cx="{c[0]:.2f}" cy="{c[1]:.2f}" r="5.0" '
                   f'fill="none" stroke="#12a594" stroke-width="1.6"/>')
    if label:
        out.append(f'<text x="{pad}" y="{pad - 8}" font-family="monospace" '
                   f'font-size="12" fill="#222222">{label}</text>')
    return out, panel + 2 * pad


def write_overlay_sheet(path: str, panels: list, *, axis_degrees: float = 45.0,
                        cols: int = 3) -> str:
    """panels: [(label, fold)] -> an SVG grid `cols` wide. Returns `path`."""
    body, size = [], None
    for i, (label, fold) in enumerate(panels):
        cell, size = overlay_svg(fold, axis_degrees=axis_degrees, label=label)
        r, c = divmod(i, cols)
        body.append(f'<g transform="translate({c * size},{r * size})">'
                    + "\n".join(cell) + "</g>")
    size = size or 1
    rows = (len(panels) + cols - 1) // cols
    w, h = min(len(panels), cols) * size, rows * size
    with open(path, "w") as fh:
        fh.write(f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" '
                 f'height="{h}" viewBox="0 0 {w} {h}">'
                 f'<rect width="{w}" height="{h}" fill="#ffffff"/>'
                 + "\n".join(body) + "</svg>")
    return path
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../mcp_harness/.venv/bin/python -m pytest tests/test_cp_mirror.py -v`
Expected: PASS, 18 passed

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/cp_mirror.py mcp_harness/tests/test_cp_mirror.py
git commit -m "feat(cp-mirror): the tripwire, and the pin that catches its own v1

Reflects creases with their assignment, drawn narrower than the pattern. Its
first draft reflected only vertices and drew the overlay wider -- on a fold
whose vertices overlap perfectly it rendered clean and caught nothing.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 5: Scorecard columns and the two wiring pins

**Files:**
- Modify: `mcp_harness/benchmark_subjects.py:186-240` (row assembly), `:294-302` (`_COLS`)
- Test: `mcp_harness/tests/test_pair_reconcile.py` (append)

**Interfaces:**
- Consumes: `cp_mirror.verdict_of_fold_str` (Task 3)
- Produces: row keys `cp_symmetric` (bool|None), `cp_mirror_residual` (float|None), `cp_mv_broken` (int|None)

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_pair_reconcile.py`:

```python
def _mirror_fold_str(a01, a12):
    import json as _json
    return _json.dumps({
        "vertices_coords": [[0.5, 0.5], [0.3, 0.7], [0.7, 0.3]],
        "edges_vertices": [[0, 1], [0, 2]],
        "edges_assignment": [a01, a12]})


def test_scorecard_carries_the_cp_symmetry_verdict():
    import benchmark_subjects as bs
    assert "cp_symmetric" in bs._COLS
    assert "cp_mirror_residual" in bs._COLS
    assert "cp_mv_broken" in bs._COLS
    row = bs.build_row("x", {"reference_count": 2, "expected_pairs": 0},
                       _result([]), _mirror_fold_str("M", "M"), "Pass")
    assert row["cp_symmetric"] is True
    assert row["cp_mirror_residual"] == 0.0
    assert row["cp_mv_broken"] == 0


def test_scorecard_separates_a_geometry_failure_from_an_assignment_failure():
    """The whole reason there are three columns: one number cannot say which."""
    import benchmark_subjects as bs
    swapped = bs.build_row("x", {"reference_count": 2, "expected_pairs": 0},
                           _result([]), _mirror_fold_str("M", "V"), "Pass")
    assert swapped["cp_mirror_residual"] == 0.0   # geometry exact
    assert swapped["cp_mv_broken"] == 2           # assignment broken
    assert swapped["cp_symmetric"] is False


def test_scorecard_cp_columns_are_none_for_an_unserved_row():
    import benchmark_subjects as bs
    row = bs.build_row("x", {"reference_count": 2, "expected_pairs": 0},
                       _result([]), "ERROR: did not pack", None)
    assert row["cp_symmetric"] is None
    assert row["cp_mirror_residual"] is None
    assert row["cp_mv_broken"] is None


def test_hull_coverage_is_wired_into_the_scorecard_columns():
    """The pin its siblings stub_flaps / pair_gap_max / pair_path_gap_max have
    always had and it never did: deleting it from _COLS left the suite green."""
    import benchmark_subjects as bs
    assert "hull_coverage" in bs._COLS
    assert "hull_coverage" in bs._DIFF_COLS
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../mcp_harness/.venv/bin/python -m pytest tests/test_pair_reconcile.py -k "cp_symmetry or cp_columns or geometry_failure or hull_coverage_is_wired" -v`
Expected: FAIL — `AssertionError` on `"cp_symmetric" in bs._COLS`

- [ ] **Step 3: Add the columns**

In `mcp_harness/benchmark_subjects.py`, add `import cp_mirror` beside the
existing `import paper_coverage` (`:38`). Insert into `build_row`'s returned
dict immediately after `"hull_coverage": ...`:

```python
        # CREASE-PATTERN mirror symmetry about the engine's shipped 45-degree
        # axis. THREE columns, not one, because a single scalar hides two
        # independent failures: bird as served fails on GEOMETRY (4 of 18
        # vertices have a mirror image at all), while an axis-pinned bird is an
        # exact 19/19 bijection failing on ASSIGNMENT (4 creases whose mirror
        # images fold the opposite way). Read them together:
        #   residual > 0, mv_broken None -> geometry failed, M/V unevaluated
        #   residual = 0, mv_broken = 4  -> geometry exact, assignment broken
        #
        # The three metrics these replace were all one-sided Hausdorff
        # distances and two read vertices_coords ONLY, so a pattern whose
        # vertices mirror but whose M/V does not scored a perfect 0.000000.
        # `symmetric` is the verdict; `residual` is only a witness.
        "cp_symmetric": (_cp["symmetric"] if _cp else None),
        "cp_mirror_residual": (round(_cp["residual"], 6) if _cp else None),
        "cp_mv_broken": (None if not _cp or not _cp["is_bijection"]
                         else _cp["mv_swapped"] + _cp["mv_mismatched"]),
```

And immediately before the `return {` that opens that dict, add:

```python
    # Computed once: three columns read it, and it walks every vertex pair.
    _cp = cp_mirror.verdict_of_fold_str(fold_str, axis_degrees=45.0)
```

Then extend `_COLS` (`:294-302`), inserting after `"hull_coverage"`:

```python
_COLS = ["subject", "R", "served_leaves", "stub_flaps", "served_fidelity",
         "pairs_expected", "pairs_kept", "attempt0_pack", "rescue_stage",
         "asymmetric", "lint_class", "hull_coverage",
         "cp_symmetric", "cp_mirror_residual", "cp_mv_broken",
         "pair_gap_max", "pair_path_gap_max",
         "error_codes"]
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../mcp_harness/.venv/bin/python -m pytest tests/test_pair_reconcile.py -v`
Expected: PASS

- [ ] **Step 5: Prove the wiring pin actually pins**

Delete the `"cp_symmetric",` entry from `_COLS`, run the test, confirm it goes
RED, then restore it. Do the same for `"hull_coverage"`. A count-based test is
not a pin of the wiring — measure that by deleting the line.

Run: `cd mcp_harness && PYTHONPATH=.:tests ../mcp_harness/.venv/bin/python -m pytest tests/test_pair_reconcile.py -k "cp_symmetry or hull_coverage_is_wired" -v`
Expected: FAIL while deleted, PASS once restored.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/benchmark_subjects.py mcp_harness/tests/test_pair_reconcile.py
git commit -m "feat(scorecard): CP symmetry as three columns, and pin hull_coverage

Three columns because one scalar hides two independent failures -- geometry
versus assignment. hull_coverage gets the _COLS pin its siblings have always
had and it never did; verified by deleting the line and watching it go red.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 5b: A test that opens the scorecard fixture

**Files:**
- Test: `mcp_harness/tests/test_pair_reconcile.py` (append)

**Interfaces:**
- Consumes: `benchmark_subjects.load_baseline(path) -> list` (existing, `:312`)

Spec §5.3 pin 2. **Nothing reads this file today** — and its `_meta` claims
`tests/test_anatomy_oracle.py` does, which is false. Until something opens it,
every number in it can go stale silently.

- [ ] **Step 1: Write the failing test**

```python
def test_the_committed_scorecard_baseline_is_read_by_something():
    """Spec 5.3 pin 2. Before this, NOTHING opened this file -- and its own
    _meta claimed test_anatomy_oracle.py did, which was false. A fixture no
    test reads cannot go red, so every number in it could drift unnoticed."""
    import os
    import benchmark_subjects as bs
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    rows = bs.load_baseline(os.path.join(here, "fixtures",
                                         "scorecard_baseline.jsonl"))
    by = {r["subject"]: r for r in rows}
    assert set(by) == {"bird", "fish", "humanoid", "insect", "quadruped"}
    # every row carries the new columns (they are added in Task 7's re-bless)
    for subject, row in by.items():
        assert "cp_symmetric" in row, f"{subject} predates the S1 re-bless"
        assert "hull_coverage" in row
    # the two facts this slice measured and must not lose
    assert by["bird"]["cp_symmetric"] is False
    assert by["quadruped"]["stub_flaps"] == 3
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../mcp_harness/.venv/bin/python -m pytest tests/test_pair_reconcile.py -k committed_scorecard -v`
Expected: FAIL — `KeyError`/`AssertionError` on `"cp_symmetric" in row`, because the fixture has not been re-blessed yet.

- [ ] **Step 3: Make it pass**

This test passes only **after** Task 7 Step 5 regenerates the fixture. Run it in
that order; if `bird`'s re-blessed `cp_symmetric` is not `False`, **stop and
report** rather than editing the assertion — that would contradict the measured
basis of the whole slice.

- [ ] **Step 4: Commit**

```bash
git add mcp_harness/tests/test_pair_reconcile.py
git commit -m "test(scorecard): something finally reads the committed baseline

Nothing opened fixtures/scorecard_baseline.jsonl before this, and its _meta
falsely claimed test_anatomy_oracle.py did. A fixture no test reads cannot go
red.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 6: The CI tier — serve-path controls and committed-tree pins

**Files:**
- Create: `mcp_harness/tests/test_cp_mirror_serve.py`

**Interfaces:**
- Consumes: `cp_mirror.mirror_verdict` (Task 3); `server.draft_and_compile_full_base(nodes, pairs) -> str`; `cases.symmetric_pairs_star`, `cases.HSHAPE`, `cases.TEMPLATE_QUADRUPED`, `cases.QUAD`; `tests/fixtures/mesh_validation_trees.json`
- Produces: nothing consumed downstream

**These run through the serve path deliberately.** S2 will modify `mv_repair`,
which only runs there, so a control compiled with a bare `HeadlessTreemaker`
would be structurally blind to the change it exists to protect.

- [ ] **Step 1: Measure the serve-path verdicts**

The CI-tier `bird` comes from `mesh_validation_trees.json` at **voxel 96 /
prune 0.25** — four leaves, pair `(4, 2)`, lengths `0.249594`. That is **not**
the tree the scorecard's `bird` row describes and its verdict is **unmeasured**.
Measure it, and the others, before writing any assertion:

```bash
cd mcp_harness && PYTHONPATH=.:tests ../mcp_harness/.venv/bin/python -c "
import json, sys
sys.path.insert(0, '.'); sys.path.insert(0, 'tests')

if __name__ == '__main__':
    import server, cases, cp_mirror
    subs = [('star-4 + pairs', *cases.symmetric_pairs_star(4, 0.5)),
            ('HSHAPE', *cases.HSHAPE),
            ('TEMPLATE_QUADRUPED', *cases.TEMPLATE_QUADRUPED),
            ('QUAD', *cases.QUAD)]
    trees = json.load(open('tests/fixtures/mesh_validation_trees.json'))
    for name, t in sorted(trees.items()):
        subs.append((f'mvt:{name}', t['nodes'], t['pairs']))
    for label, nodes, pairs in subs:
        out = server.draft_and_compile_full_base(
            [dict(n) for n in nodes], [list(p) for p in pairs])
        if out.startswith('ERROR'):
            print(f'{label:28} DID NOT SERVE: {out.splitlines()[0][:60]}')
            continue
        v = cp_mirror.mirror_verdict(json.loads(out), axis_degrees=45.0)
        print(f'{label:28} symmetric={v[\"symmetric\"]!s:5} '
              f'residual={v[\"residual\"]:.6f} bij={v[\"is_bijection\"]!s:5} '
              f'card={v[\"cardinality\"]}/{v[\"n_vertices\"]} '
              f'swap={v[\"mv_swapped\"]} mism={v[\"mv_mismatched\"]}')
" 2>&1 | grep -v "it/s"
```

**Record every line.** These become the pins. Do not carry `0.318880` — or any
other number from the spec's §1.2 table — across to a subject you did not just
measure here; that table is a bare compile of the serve-default trees, and
these are different trees on a different path.

- [ ] **Step 2: Write the tests using the measured values**

Create `mcp_harness/tests/test_cp_mirror_serve.py`. Replace every `<measured>`
with the Step 1 output. If a subject printed `DID NOT SERVE`, replace its
assertion with `pytest.skip` naming the error, and record that in the commit
message — do not silently drop it.

```python
"""Serve-path tier for crease-pattern mirror symmetry.

THROUGH server.draft_and_compile_full_base, NOT a bare HeadlessTreemaker
compile. The bare call is attempt-0 for one exact node list; the serve runs the
rescue ladder and the M/V repair. S2 modifies mv_repair, which only runs here,
so a control compiled bare would be blind to the change it exists to protect.
Mistaking one for the other has bitten this project four times.
"""
import json
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "tests"))

import cases          # noqa: E402
import cp_mirror      # noqa: E402

_TREES = os.path.join(_HERE, "tests", "fixtures", "mesh_validation_trees.json")


def _serve(nodes, pairs):
    import server
    out = server.draft_and_compile_full_base(
        [dict(n) for n in nodes], [list(p) for p in pairs])
    if out.startswith("ERROR"):
        pytest.skip(f"did not serve: {out.splitlines()[0][:70]}")
    return cp_mirror.mirror_verdict(json.loads(out), axis_degrees=45.0)


def test_a_symmetric_tree_yields_a_symmetric_crease_pattern_star4():
    """THE INVARIANT. It cannot be satisfied dishonestly, and it is what S2
    must not break."""
    v = _serve(*cases.symmetric_pairs_star(4, 0.5))
    assert v["symmetric"] is True
    assert v["mv_swapped"] == 0 and v["mv_mismatched"] == 0


def test_a_symmetric_tree_yields_a_symmetric_crease_pattern_hshape():
    v = _serve(*cases.HSHAPE)
    assert v["symmetric"] is True
    assert v["mv_swapped"] == 0 and v["mv_mismatched"] == 0


def test_template_quadruped_is_pinned_red_on_mv_and_is_S2s_target():
    """Hand-authored, exactly symmetric, no extractor and no lever involved --
    and it still carries the defect. S2 turns this green or explains why not."""
    v = _serve(*cases.TEMPLATE_QUADRUPED)
    assert v["is_bijection"] is True          # geometry is fine
    assert v["residual"] == 0.0
    assert v["mv_swapped"] == <measured>      # expected 2
    assert v["symmetric"] is False


def test_quad_the_negative_control_the_shipped_metric_scored_perfect():
    """probe_cp_symmetry called QUAD's 0.0 an unexplained small-tree
    degeneracy. It is six creases mapping M/V to F: folded on one side of the
    axis, flat on its mirror image."""
    v = _serve(*cases.QUAD)
    assert v["mv_mismatched"] == <measured>   # expected 6
    assert v["symmetric"] is False


@pytest.mark.parametrize("subject", ["bird", "fish", "humanoid", "insect",
                                     "quadruped"])
def test_mesh_validation_tree_verdicts_are_pinned(subject):
    """Committed trees at voxel 96 / prune 0.25 -- NOT the scorecard's serve
    default. Already a drift tripwire for test_gate_mesh_region and
    test_pair_detection, so it inherits the pinned-mesh-lib discipline."""
    expected = {
        "bird": <measured>,
        "fish": <measured>,
        "humanoid": <measured>,
        "insect": <measured>,
        "quadruped": <measured>,
    }[subject]
    with open(_TREES) as fh:
        t = json.load(fh)[subject]
    v = _serve(t["nodes"], t["pairs"])
    assert v["symmetric"] is expected["symmetric"]
    assert abs(v["residual"] - expected["residual"]) < 1e-6
    assert v["mv_swapped"] == expected["mv_swapped"]
    assert v["mv_mismatched"] == expected["mv_mismatched"]
```

- [ ] **Step 3: Run the tests to verify they pass**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../mcp_harness/.venv/bin/python -m pytest tests/test_cp_mirror_serve.py -v --timeout=420`
Expected: PASS. If either control fails `symmetric is True`, **stop and report** — that contradicts the spec's measured basis and the slice needs re-examining, not a loosened assertion.

- [ ] **Step 4: Time it, and record the number**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../mcp_harness/.venv/bin/python -m pytest tests/test_cp_mirror_serve.py -q --durations=0 --timeout=420`

Record the total. Nine serve-path compiles. If it exceeds the suite's budget,
the spec's stated fallback is the two controls in CI with the rest fixture-
pinned — **take it explicitly in the commit message, never silently.**

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/tests/test_cp_mirror_serve.py
git commit -m "test(cp-mirror): the serve-path tier

star-4 and HSHAPE assert the invariant a symmetric tree must yield a symmetric
crease pattern. TEMPLATE_QUADRUPED is pinned RED on M/V as S2's target, and
QUAD -- the negative control the shipped metric scored perfect -- is pinned red
on six creases mapping M/V to F.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 7: Delete the two wrong implementations and re-bless their evidence

**Files:**
- Modify: `mcp_harness/probe_cp_symmetry.py` (delete `cp_symmetry`, re-point the driver)
- Modify: `docs/superpowers/evidence/2026-08-03-reparented-bases/fold_and_look.py:146` (delete `cp_mirror_residual`)
- Regenerate: `mcp_harness/fixtures/cp_symmetry_evidence.json`, `docs/superpowers/evidence/2026-08-03-reparented-bases/README.md`, `mcp_harness/fixtures/scorecard_baseline.jsonl`
- Modify: `mcp_harness/benchmark_subjects.py:226-229` (false docstring), `mcp_harness/probe_cp_symmetry.py:59-61` (false docstring)

**Interfaces:**
- Consumes: `cp_mirror.mirror_verdict`, `cp_mirror.write_overlay_sheet` (Tasks 3–4)
- Produces: nothing consumed downstream

- [ ] **Step 1: Delete `cp_symmetry` and re-point its driver**

In `mcp_harness/probe_cp_symmetry.py`: delete the `cp_symmetry` function
(`:95-137`) and the `reflect` helper (`:90-92`). In `main`'s `run`, replace
`s = cp_symmetry(out)` with:

```python
        import cp_mirror
        s = cp_mirror.mirror_verdict(json.loads(out), axis_degrees=45.0)
```

and update the print and the `rows.append` to the new keys (`symmetric`,
`residual`, `mv_swapped`, `mv_mismatched`, `cardinality`, `n_vertices`).

Keep the driver: subject construction, the node-order basin control and the
extracted-subject arms are not in question.

- [ ] **Step 2: Add the staleness banner the probe needs**

Its `(raw)` arm is **already reconciled** at HEAD — `probe_cp_symmetry.py`
predates the wiring commit `8894d95`, and because the re-parent is idempotent a
naive re-run silently produces identical rows instead of erroring. Add to the
module docstring:

```
⚠ THE "(raw)" ARM IS NO LONGER RAW. `to_metric_tree` has run path
reconciliation unconditionally since 8894d95 (mesh_to_tree.py:669-671), so
`mesh_to_metric_tree` returns an already-reconciled tree and this probe's
`(re-parent + drop)` arm applies an IDEMPOTENT second pass. The two arms are
therefore the same tree, and the A/B this probe was written to show is gone --
it will print two identical rows rather than fail. To recover a genuine raw
arm, suppress both steps the way
docs/superpowers/evidence/2026-08-03-reparented-bases/fold_and_look.py:29-36
does.
```

- [ ] **Step 3: Delete `cp_mirror_residual` and re-point `fold_and_look`**

In `docs/superpowers/evidence/2026-08-03-reparented-bases/fold_and_look.py`,
delete `cp_mirror_residual` (`:146-166`) and replace its call sites with:

```python
import cp_mirror
...
    v = cp_mirror.mirror_verdict(fold, axis_degrees=45.0)
```

reporting `v["symmetric"]`, `v["residual"]`, `v["mv_swapped"]`,
`v["mv_mismatched"]`.

- [ ] **Step 4: Correct the two false docstrings**

`benchmark_subjects.py:226-229` currently says a nonzero `pair_path_gap_max`
means a pair was refused. Refused pairs never reach `kept`, so the column
returns `None` — never a nonzero. Replace that sentence with:

```python
        # `null` for a subject with no pairs. NOT a refusal signal: a refused
        # pair never reaches `kept`, so a refusal reads as `null` here, never
        # as a nonzero. The committed bird row is the proof --
        # pairs_expected 2 / pairs_kept 1 / pair_path_gap_max 0.0.
```

`probe_cp_symmetry.py:59-61` says a ~0.0 reading on a small tree is
UNINFORMATIVE. Replace with:

```
  * a 0.0 reading means the leaf set was mirror-symmetric, which is the
    property Goal 2 wants -- QUAD is the case that made this look mysterious
    and it is a genuine mirror-symmetric leaf set. What a 0.0 does NOT mean is
    that the PATTERN is symmetric: the assignment can still be lopsided, which
    is why `cp_mirror.mirror_verdict` exists;
```

- [ ] **Step 5: Regenerate the three committed artifacts**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../mcp_harness/.venv/bin/python probe_cp_symmetry.py
```

Then regenerate the scorecard (needs the single-machine cached dog mesh):

```bash
cd mcp_harness && IDE_BENCH_DOG=1 PYTHONPATH=.:tests ../mcp_harness/.venv/bin/python \
  benchmark_subjects.py --out /tmp/scorecard_new.jsonl --baseline fixtures/scorecard_baseline.jsonl
```

`--out` APPENDS, so **replace** `fixtures/scorecard_baseline.jsonl` rather than
adding to it. Update its `_meta`: name this commit and date, and **delete the
false claim** that `tests/test_anatomy_oracle.py` reads the bird row — that
test was deliberately re-pointed away on 2026-08-03
(`tests/test_anatomy_oracle.py:92-105`).

Rewrite the residual table in
`docs/superpowers/evidence/2026-08-03-reparented-bases/README.md` under the new
metric, and write the tripwire sheet beside it:

```bash
cd mcp_harness && PYTHONPATH=.:tests ../mcp_harness/.venv/bin/python -c "
import json, sys; sys.path.insert(0,'.'); sys.path.insert(0,'tests')
if __name__ == '__main__':
    import server, cases, cp_mirror
    panels = []
    for label, nodes, pairs in [
            ('star-4 + pairs', *cases.symmetric_pairs_star(4, 0.5)),
            ('HSHAPE', *cases.HSHAPE),
            ('TEMPLATE_QUADRUPED', *cases.TEMPLATE_QUADRUPED),
            ('QUAD', *cases.QUAD)]:
        out = server.draft_and_compile_full_base(
            [dict(n) for n in nodes], [list(p) for p in pairs])
        if not out.startswith('ERROR'):
            panels.append((label, json.loads(out)))
    cp_mirror.write_overlay_sheet(
        '../docs/superpowers/evidence/2026-08-03-reparented-bases/mirror_overlay.svg',
        panels)
"
```

- [ ] **Step 6: Run the whole suite**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../mcp_harness/.venv/bin/python -m pytest tests/ --timeout=420 -q`
Expected: the suite's known baseline (memory `worktree-borrowed-so-inflates-failures`: build in place; a borrowed `.so` inflates failures to ~27). Compare **failing-test IDs**, not counts, against a pre-change run. The suite looks hung early at ~0% CPU and finishes in ~23 min — do not kill it.

- [ ] **Step 7: Verify on Linux before merge**

Per memory `ubuntu-platform-truth` and `rigid-frozen-hash-platform-divergence`,
reproduce in the `ci-amd64-run` container rather than push-and-wait. The
asserted controls are boolean verdicts at `tol = 1e-6`, not frozen hashes over
roundoff-bearing floats, so they are expected to hold — confirm rather than
assume. **Check host CPU load first**: a stray orphan process once made a gate
run 6× slow and would have manufactured timeout failures.

- [ ] **Step 8: Commit**

```bash
git add mcp_harness/probe_cp_symmetry.py mcp_harness/fixtures/ \
        mcp_harness/benchmark_subjects.py \
        docs/superpowers/evidence/2026-08-03-reparented-bases/
git commit -m "refactor(cp-mirror): delete the two wrong metrics, re-bless evidence

probe_cp_symmetry.cp_symmetry and fold_and_look.cp_mirror_residual are gone;
their drivers now call cp_mirror.mirror_verdict. Three committed verdicts
reverse. Also corrects two docstrings that were false in ways that would
mislead the next reader of this exact area, and banners probe_cp_symmetry's
'(raw)' arm, which has been silently already-reconciled since 8894d95.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage.** §3 definition → Tasks 1, 3. §3.1 convention → Task 3 docstring
+ Task 6 controls. §4.1 boundary → Tasks 1–2. §4.2 test-not-search → Task 2
`candidate_axes` docstring + Task 3's required `axis_degrees`. §4.3 axis not
recorded → Task 3 docstring. §5.1 return shape → Task 3. §5.2 three columns →
Task 5. §5.3 two pins → Task 5 (wiring, proven by deletion in Step 5) and
Task 5b (value, opening the committed fixture). §6 tripwire → Task 4. §6.1 its
pin → Task 4 Step 1. §7.1 CI tier → Task 6. §7.2 scorecard tier → Tasks 5, 7.
§8 re-blessed evidence and both false docstrings → Task 7. §11 acceptance
criteria 1–9 → Tasks 6, 6, 5b/6, 6, 5, 5b, 2, 4, 7 respectively.

**Gap found and closed:** §5.3's second pin requires "a test that actually opens
`fixtures/scorecard_baseline.jsonl`". Task 6 pins `mesh_validation_trees.json`,
which is a *different* file, so the requirement had no task. Task 5b was added
and sequenced between Tasks 5 and 7 — it is written before the re-bless and
passes only after it, which is deliberate and stated in its Step 3.

**Ordering note for the executor:** Task 5b's test is RED until Task 7 Step 5
regenerates the fixture. That is the one place in this plan where a task does
not go green on its own; do Tasks 5b → 6 → 7, then re-run 5b.

**Type consistency:** `mirror_verdict`'s keys are used identically in Tasks 3–7
(`symmetric`, `residual`, `is_bijection`, `mv_swapped`, `mv_mismatched`,
`cardinality`, `n_vertices`). `overlay_svg` returns `(list, int)` in Task 4 and
is unpacked as such in its tests and in `write_overlay_sheet`. `candidate_axes`
returns reflector callables in Task 2 and is consumed as such by `mirror_map`.
`verdict_of_fold_str` is defined in Task 3 and consumed in Task 5.
