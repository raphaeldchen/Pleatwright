# 0b — True polygon coverage — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `paper_coverage.hull_coverage` measure the crease pattern's **true
boundary polygon** instead of the convex hull of its boundary points, so that a
non-convex outline can no longer be over-reported.

**Architecture:** `paper_coverage` gains a B-edge cycle walk and uses its area
when the border is one simple closed loop, falling back to the convex hull —
**named in the `source` field, never silently** — otherwise. The walk already
exists as `pose_base._border_cycle`, but `pose_base` imports numpy and
`paper_coverage`'s docstring explicitly claims *"No engine, no scipy … no import
cost in the row builder."* So the primitive **moves down** into `paper_coverage`
and `pose_base._border_cycle` becomes a thin wrapper preserving its own
`PoseBaseError` contract. Dependency direction: the cheap module owns the cheap
primitive; the expensive one borrows it.

**Tech Stack:** Python 3.14, pytest. No new dependencies — and adding one would
defeat the point.

**Spec:** [docs/superpowers/specs/2026-08-04-whole-square-axis-projection-design.md](../specs/2026-08-04-whole-square-axis-projection-design.md) §4.4
**Coordination:** [docs/superpowers/goals/COORDINATION.md](../goals/COORDINATION.md) — **this is Goal 2's shared instrument; it lands standalone and they rebase onto it.**

---

## Global Constraints

- **Branch from `5f6ab2a`** (main, S4a′ merged). Branch `claude/goal-1-0b-polygon-coverage`, its own worktree.
- **Measure against `1c9abe0`** — the FROZEN scorecard baseline. It does **not** advance. `mcp_harness/fixtures/scorecard_baseline.jsonl` is **not** to be regenerated.
- **Tests:** `cd mcp_harness && PYTHONPATH=.:tests <repo>/mcp_harness/.venv/bin/python -m pytest tests/ --timeout=420`. Bare `make test` never terminates. Full suite ~15 min, **looks stalled early at near-zero CPU — do not kill it.** Expect **2256 passed, 11 skipped, 0 failed** from a deeply-nested worktree, or **2257 / 10** from a short path (the delta is `test_rigid_collision_evidence[member_socket]`'s AF_UNIX `sun_path` limit under `Path.cwd()` — path length, **not** platform).
- **This slice needs no engine build** for its own tests, but the full suite does: `cd mcp_harness && PYTHON=<repo>/mcp_harness/.venv/bin/python ./build.sh` — bare `./build.sh` uses a Homebrew interpreter without `pybind11` and **exits producing no `.so` and no obvious failure.** Also symlink or build `oriedita/` and `OrieditaValidator.class` or every lint verdict fakes `FAIL-LINT`.
- **The shell cwd is `mcp_harness`**, and `tests/` means `mcp_harness/tests`.
- **Never pin a number you did not observe.**
- Commit messages end with: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`

> **Honest expectation, stated up front so the result is not oversold: this
> probably moves nothing today.** Spec §1.1(1) records the committed outlines as
> having a boundary hull equal to their full hull — i.e. already convex. If no
> committed row moves, **0b is a pre-registration for experiments that have not
> run, not a correction to a wrong number**, and the PR must say that in those
> words. Any corner-forcing experiment produces exactly the non-convex outline
> the convex hull would over-report, which is why this lands *before* them.

---

## File Structure

| File | Responsibility |
|---|---|
| `mcp_harness/paper_coverage.py` | **Modify.** Own `_border_cycle` + `CoverageError`; polygon area with a named fallback; docstring corrected. |
| `mcp_harness/pose_base.py` | **Modify.** `_border_cycle` becomes a thin wrapper re-raising `PoseBaseError`. Behaviour unchanged. |
| `mcp_harness/tests/test_paper_coverage.py` | **Create or modify.** Unit tests on synthetic folds — no engine. |

---

## Task 1: Move the border-cycle walk into `paper_coverage`

**Files:**
- Modify: `mcp_harness/paper_coverage.py`, `mcp_harness/pose_base.py`
- Test: `mcp_harness/tests/test_paper_coverage.py`

**Interfaces:**
- Produces: `paper_coverage.CoverageError(Exception)` and
  `paper_coverage._border_cycle(fold) -> list[int]` — the ordered vertex cycle of
  the `"B"` border, raising `CoverageError` unless it is one simple closed loop.
- `pose_base._border_cycle` keeps its exact signature and keeps raising
  `PoseBaseError`. Its existing tests must pass **unmodified** — that is the guard.

- [ ] **Step 1: Write the failing test**

Create `mcp_harness/tests/test_paper_coverage.py`:

```python
"""paper_coverage: the boundary polygon, not the convex hull of its points.

A convex hull can only OVERSTATE a non-convex outline, and a non-convex outline
is exactly what any corner-forcing experiment produces. This module must be able
to score one before such an experiment runs, which is why the change lands
standalone and ahead of them.

No engine here -- these are synthetic folds. paper_coverage is deliberately
dependency-free (its own docstring: "No engine, no scipy ... no import cost in
the row builder"), and these tests hold that line.
"""
from __future__ import annotations
import pytest

import paper_coverage


def square_fold():
    """The unit square: four B edges, area 1.0."""
    return {
        "vertices_coords": [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
        "edges_vertices": [[0, 1], [1, 2], [2, 3], [3, 0]],
        "edges_assignment": ["B", "B", "B", "B"],
    }


def chevron_fold():
    """A NON-CONVEX closed border: the unit square with the top edge pushed
    down to (0.5, 0.5). True area 0.75; its convex hull is the full square, 1.0.
    This is the shape the old implementation over-reports by a third."""
    return {
        "vertices_coords": [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0],
                            [0.5, 0.5], [0.0, 1.0]],
        "edges_vertices": [[0, 1], [1, 2], [2, 3], [3, 4], [4, 0]],
        "edges_assignment": ["B", "B", "B", "B", "B"],
    }


def test_border_cycle_walks_a_simple_loop():
    walk = paper_coverage._border_cycle(square_fold())
    assert sorted(walk) == [0, 1, 2, 3]
    assert len(walk) == 4


def test_border_cycle_rejects_a_non_cycle():
    f = square_fold()
    f["edges_assignment"] = ["B", "B", "B", "F"]      # open chain
    with pytest.raises(paper_coverage.CoverageError):
        paper_coverage._border_cycle(f)


def test_border_cycle_rejects_two_loops():
    f = {
        "vertices_coords": [[0.0, 0.0], [0.1, 0.0], [0.1, 0.1],
                            [0.5, 0.5], [0.6, 0.5], [0.6, 0.6]],
        "edges_vertices": [[0, 1], [1, 2], [2, 0], [3, 4], [4, 5], [5, 3]],
        "edges_assignment": ["B"] * 6,
    }
    with pytest.raises(paper_coverage.CoverageError):
        paper_coverage._border_cycle(f)


def test_paper_coverage_imports_no_numpy():
    """The row builder runs this on every scorecard row. Its docstring promises
    no engine and no scipy; numpy would be the same broken promise. pose_base
    (which DOES use numpy) borrows from here, never the other way round."""
    import sys
    for mod in ("numpy", "scipy", "headless_treemaker"):
        sys.modules.pop(mod, None)
    import importlib
    importlib.reload(paper_coverage)
    assert "numpy" not in sys.modules, "paper_coverage pulled in numpy"
    assert "scipy" not in sys.modules, "paper_coverage pulled in scipy"
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd mcp_harness && PYTHONPATH=.:tests <repo>/mcp_harness/.venv/bin/python -m pytest tests/test_paper_coverage.py -v --timeout=420
```

Expected: the three `_border_cycle` tests FAIL with
`AttributeError: module 'paper_coverage' has no attribute 'CoverageError'` (or
`_border_cycle`). `test_paper_coverage_imports_no_numpy` should already PASS —
it is a regression guard on a property the module has today, and it must still
pass at the end.

- [ ] **Step 3: Add the error type and the walk to `paper_coverage`**

In `mcp_harness/paper_coverage.py`, after the `PAPER_W` / `PAPER_H` constants,
insert:

```python
class CoverageError(Exception):
    """The fold cannot support a boundary-polygon measurement."""


def _border_cycle(fold):
    """Ordered vertex cycle of the 'B' border.

    Raises CoverageError unless the border is ONE simple closed loop (every
    border vertex carrying exactly two B edges). Lifted from
    pose_base._border_cycle so the dependency runs downhill: this module is
    deliberately import-free and the scorecard row builder calls it on every
    row, while pose_base already carries numpy. pose_base now wraps this.
    """
    adj: dict = {}
    for (a, b), s in zip(fold.get("edges_vertices") or (),
                         fold.get("edges_assignment") or ()):
        if s == "B":
            adj.setdefault(a, []).append(b)
            adj.setdefault(b, []).append(a)
    if not adj:
        raise CoverageError("no B edges")
    bad = {v: len(n) for v, n in adj.items() if len(n) != 2}
    if bad:
        raise CoverageError(f"border not a simple cycle: {bad}")
    start = min(adj)
    walk = [start, adj[start][0]]
    while walk[-1] != start:
        prev, cur = walk[-2], walk[-1]
        walk.append([n for n in adj[cur] if n != prev][0])
    walk = walk[:-1]
    if len(walk) != len(adj):
        raise CoverageError("border has more than one loop")
    return walk
```

- [ ] **Step 4: Make `pose_base._border_cycle` a thin wrapper**

Replace the body of `pose_base._border_cycle` with:

```python
def _border_cycle(fold):
    """Ordered vertex cycle of the 'B' border; raises unless it is one
    simple closed loop (every border vertex has exactly two B edges).

    The walk lives in paper_coverage now -- that module is dependency-free and
    the scorecard row builder calls it on every row, so it owns the cheap
    primitive and this one borrows it. Contract here is unchanged: same
    signature, same PoseBaseError.
    """
    try:
        return paper_coverage._border_cycle(fold)
    except paper_coverage.CoverageError as exc:
        raise PoseBaseError(str(exc)) from exc
```

Add `import paper_coverage` to `pose_base`'s imports.

- [ ] **Step 5: Run both test files**

```bash
cd mcp_harness && PYTHONPATH=.:tests <repo>/mcp_harness/.venv/bin/python -m pytest tests/test_paper_coverage.py tests/test_pose_base.py -v --timeout=420
```

Expected: all PASS. **`tests/test_pose_base.py` must pass UNMODIFIED** — if it
does not exist under that name, find and run whatever exercises `pose_base` and
say which file you ran. Do not edit a pose_base test to accommodate this change;
if one needs editing, that is a behaviour change and it is out of scope — report
it instead.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/paper_coverage.py mcp_harness/pose_base.py mcp_harness/tests/test_paper_coverage.py
git commit -m "$(cat <<'EOF'
refactor(paper-coverage): own the B-border cycle walk; pose_base wraps it

paper_coverage is deliberately dependency-free -- the scorecard row builder
calls it on every row and its docstring promises no engine and no scipy.
pose_base carries numpy, so importing upward to reuse its _border_cycle would
put numpy in the row builder. The primitive moves down instead; pose_base keeps
its exact signature and its PoseBaseError contract, and its tests pass
unmodified.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Use the polygon area, and name the fallback

**Files:**
- Modify: `mcp_harness/paper_coverage.py` — `hull_coverage`
- Test: `mcp_harness/tests/test_paper_coverage.py`

**Interfaces:**
- `hull_coverage(fold, paper_w=1.0, paper_h=1.0) -> dict | None` keeps its keys
  and adds nothing. The `source` field gains a third value: `"boundary_cycle"`
  when the true polygon was measured, alongside the existing `"boundary_edges"`
  (convex-hull fallback over B vertices) and `"all_vertices"`.

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_paper_coverage.py`:

```python
def test_a_convex_border_is_unchanged_and_says_so():
    got = paper_coverage.hull_coverage(square_fold())
    assert got["coverage"] == pytest.approx(1.0)
    assert got["source"] == "boundary_cycle"


def test_a_NON_convex_border_is_no_longer_overstated():
    """The whole point. True area 0.75; the convex hull reads 1.0.

    A convex hull can only OVERSTATE a non-convex outline, and corner-forcing
    is exactly what produces one -- so this must be right BEFORE such an
    experiment is scored, not after.
    """
    got = paper_coverage.hull_coverage(chevron_fold())
    assert got["coverage"] == pytest.approx(0.75), got
    assert got["source"] == "boundary_cycle"
    # and the convex hull of the same points really does read 1.0, so the test
    # is measuring the change rather than restating the implementation
    pts = [tuple(p) for p in chevron_fold()["vertices_coords"]]
    assert paper_coverage._area(paper_coverage._hull(pts)) == pytest.approx(1.0)


def test_the_fallback_is_NAMED_never_silent():
    """Two disjoint B loops cannot give a polygon. Falling back is fine;
    doing it silently is not -- the module's own rule is that a fabricated
    number is worse than an empty cell."""
    f = {
        "vertices_coords": [[0.0, 0.0], [0.4, 0.0], [0.4, 0.4],
                            [0.6, 0.6], [1.0, 0.6], [1.0, 1.0]],
        "edges_vertices": [[0, 1], [1, 2], [2, 0], [3, 4], [4, 5], [5, 3]],
        "edges_assignment": ["B"] * 6,
    }
    got = paper_coverage.hull_coverage(f)
    assert got is not None
    assert got["source"] == "boundary_edges", got
    assert got["coverage"] > 0.0


def test_no_b_edges_still_falls_back_to_all_vertices():
    f = square_fold()
    f["edges_assignment"] = ["F", "F", "F", "F"]
    got = paper_coverage.hull_coverage(f)
    assert got["source"] == "all_vertices", got


def test_a_degenerate_fold_still_returns_None_not_a_number():
    assert paper_coverage.hull_coverage({"vertices_coords": [[0.0, 0.0]]}) is None
    assert paper_coverage.hull_coverage(None) is None
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd mcp_harness && PYTHONPATH=.:tests <repo>/mcp_harness/.venv/bin/python -m pytest tests/test_paper_coverage.py -v --timeout=420
```

Expected: `test_a_convex_border_is_unchanged_and_says_so` FAILS on
`source == "boundary_edges"`, and `test_a_NON_convex_border_is_no_longer_overstated`
FAILS with `coverage == 1.0` where 0.75 is expected. **That 1.0 is the defect,
observed.** Record it here → `____________`

- [ ] **Step 3: Implement**

In `hull_coverage`, replace the hull computation block. The current code reads:

```python
    hull = _hull(pts)
    hull_area = _area(hull)
    if hull_area <= 0.0:
        return None                      # collinear or coincident
```

Replace with:

```python
    # Prefer the TRUE boundary polygon. A convex hull can only OVERSTATE a
    # non-convex outline, and a non-convex outline is exactly what a
    # corner-forcing experiment produces -- so the hull is not merely
    # imprecise here, it is biased in the direction that flatters the result.
    # The fallback is NAMED in `source`, never silent: this module's rule is
    # that a fabricated number is worse than an empty cell.
    hull_area = 0.0
    if source == "boundary_edges":
        try:
            walk = _border_cycle(fold)
            poly = [(float(coords[i][0]), float(coords[i][1])) for i in walk]
            hull_area = _area(poly)
            source = "boundary_cycle"
        except (CoverageError, IndexError, TypeError, ValueError):
            hull_area = 0.0              # fall through to the hull below
    if hull_area <= 0.0:
        hull_area = _area(_hull(pts))
    if hull_area <= 0.0:
        return None                      # collinear or coincident
```

- [ ] **Step 4: Run to verify they pass**

```bash
cd mcp_harness && PYTHONPATH=.:tests <repo>/mcp_harness/.venv/bin/python -m pytest tests/test_paper_coverage.py -v --timeout=420
```

Expected: all PASS.

- [ ] **Step 5: Correct the module docstring**

`paper_coverage.py`'s docstring says *"monotone-chain hull plus the shoelace
formula."* That is now the fallback, not the primary. Update that sentence to
describe the B-border cycle walk with a convex-hull fallback, and keep the
"no engine, no scipy" promise — it is still true and Task 1 pins it.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/paper_coverage.py mcp_harness/tests/test_paper_coverage.py
git commit -m "$(cat <<'EOF'
fix(paper-coverage): measure the true boundary polygon, not its convex hull

A convex hull can only OVERSTATE a non-convex outline, and a non-convex outline
is what any corner-forcing experiment produces -- so the hull is biased in the
direction that flatters the result, not merely imprecise. Measured on a
synthetic chevron: true area 0.75, convex hull 1.0.

The fallback to the hull is NAMED via source="boundary_edges" rather than
silent, per this module's own rule that a fabricated number is worse than an
empty cell.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Measure the committed corpus, and report either way

- [ ] **Step 1: Full suite**

```bash
cd mcp_harness && PYTHONPATH=.:tests <repo>/mcp_harness/.venv/bin/python -m pytest tests/ --timeout=420
```

Expected: **2256 / 11 / 0** (deep worktree path) or **2257 / 10 / 0** (short
path), plus the new tests. Record the line → `____________`

- [ ] **Step 2: The frozen-baseline delta**

```bash
cd mcp_harness && PYTHONPATH=.:tests <repo>/mcp_harness/.venv/bin/python benchmark_subjects.py --baseline fixtures/scorecard_baseline.jsonl
```

**Do NOT regenerate the baseline.** Record the delta → `____________`

**Both outcomes are publishable and neither is a failure:**

- **`no axis moved`** → the committed outlines are already convex, exactly as
  spec §1.1(1) records. Say so plainly: *0b is a pre-registration for
  experiments that have not run, not a correction to a wrong number.* Do not
  dress it up as a fix.
- **`hull_coverage` moved on some subject** → that subject's outline is
  **non-convex and has been over-reported all along**. That is a finding worth
  more than the code: name the subject, give both numbers, and say which
  direction the error ran (it can only have been an overstatement).

- [ ] **Step 3: Check the nine goldens are untouched**

This slice changes a *measurement*, not geometry. No golden should move. Confirm
from the suite result rather than by assertion.

- [ ] **Step 4: Update the tracking docs and commit**

In `docs/superpowers/goals/COORDINATION.md` §4, mark the 0b row **landed** with
its merge commit, and add a §5 signal: **"0b merged — Goal 2 may now report
coverage numbers; rebase onto it first."**

In `docs/superpowers/goals/goal-1-whole-square/PROGRESS.md`, record 0b's outcome
including whether any row moved.

---

## Self-review against the spec

| spec §4.4 requirement | task |
|---|---|
| True polygon area, not the convex hull | Task 2 |
| Reuse the existing B-edge traversal rather than writing a second | Task 1 — moved down, not duplicated |
| Fallback named, never silent | Task 2, `source == "boundary_cycle"` vs `"boundary_edges"` |
| Honest expectation: may move nothing; say so in those words | Task 3 Step 2 |
| Lands standalone; Goal 2 rebases onto it | Global constraints; Task 3 Step 4 |

**Not in this plan:** the `design_scale` column (0a — held until this reports so
the two scorecard-touching changes stay separately attributable), the display
badge (0c), and 0α's probe.
