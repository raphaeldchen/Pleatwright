# Pleat Filter (COrigami F.1.1 steps 3-4) Implementation Plan

> ⚠ **HALTED 2026-09-27 after Task 3. Do not execute Tasks 4 onward.** Tasks 1-3
> are committed and inert; Task 4 (the activation) was run and abandoned when it
> showed the filter is a **no-op** at COrigami's own unit of selection (a segment:
> 365 of 365 collinear runs retained on `lizard`) and **destructive** below it
> (408 of 454 fully-bound interior vertices go odd, breaking Maekawa). The spec's
> premise — "the filter rejects ~90% of dense candidates" — is **withdrawn**; it
> was measured at unit-piece granularity. Result:
> `../evidence/2026-09-27-pleat-filter/README.md`; spec status:
> `../specs/2026-09-27-pleat-filter-design.md`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop dense mode creasing every `axial`/`elev` piece; keep only those COrigami F.1.1 steps 3-4 retain, behind a flag, and measure whether a filtered dense pattern can reach a layer order.

**Architecture:** One new pure module, `box_pleat/pleat_filter.py`, exposing `retain(pieces, N) -> frozenset[int]`. Two touch points in `assign.py`: `initial_readings` pins a rejected candidate to `F`, and `pleat_paths`' dense candidate test becomes "not pinned". Two new keyword arguments (`filter_pleats`) on `assign` and `compile_tree`. Both dense modes coexist so the A/B runs in one process on the same geometry.

**Tech Stack:** Python 3.14, pytest 9. No new dependencies.

Spec: `docs/superpowers/specs/2026-09-27-pleat-filter-design.md`.

## Global Constraints

- **Run every command from this worktree.** Do NOT `cd` to the original repository root.
- **Use `../.venv/bin/python3` from `mcp_harness`.** Bare `python3` lacks `skeletor`, which `tests/conftest.py` imports, and dies at collection.
- **That venv has no `pytest-timeout`. NEVER pass `--timeout`.**
- **NEVER run `pytest tests/`** — 5,167 tests, over 3 hours. Always name files or use `-k`.
- **Never use bare `git stash` / `git stash pop`.** The stash stack is shared with the main checkout and other worktrees. Use a temporary WIP commit; if unavoidable, `git stash push -u -m "<unique-tag>"`, capture the SHA, restore with `git stash apply <sha>`.
- **End every commit message with:** `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`
- **Byte-identity, two guarantees, both load-bearing:** `dense=False` output is unchanged, and `dense=True, filter_pleats=False` output is unchanged.
- **Forbidden edits in `assign.py`** (they change which solution the CSP reaches first): the centre-column domain order `domain[i] = ["F"] + ([lab, "V" if lab == "M" else "M"] if lab in ("M","V") else ["M","V"])`, and `label_from_profile`'s mirroring `if lo is None: lo = e + (e - hi)`. Both look collapsible. Neither is.
- **`layer_order.py` must not be touched.**
- **`grep -c box_pleat mcp_harness/server.py` must stay 0.**
- **Every count assertion is paired with a non-vacuity assertion.** PR #193 shipped two tests reading `0 == 0` against fixtures that generated zero of the thing under test.
- **The filter gates dense-mode ADDITIONS ONLY.** A piece whose elevation profile already reads `M` or `V` is a variable in both modes and the filter must never remove it ("augment, don't replace").
- **If the filtered pattern is too sparse, DO NOT loosen the predicate.** The remedy is F.1.1 step 5 (a separate spec) or a recorded negative. Loosening a gate to reach a headline is this project's named recurring failure mode.

## File Structure

| file | responsibility |
|---|---|
| `mcp_harness/box_pleat/pleat_filter.py` (new) | The F.1.1 steps 3-4 predicate. Pure: no I/O, no geometry construction, no mutation. |
| `mcp_harness/tests/test_box_pleat_pleat_filter.py` (new) | Hand-built fixtures for the predicate, plus one real compiled subject for non-emptiness. |
| `mcp_harness/box_pleat/assign.py` (modify) | `initial_readings` gains `retained=`; `pleat_paths`' dense candidate test; `assign` gains `filter_pleats=`. |
| `mcp_harness/box_pleat/compile.py` (modify) | `compile_tree` gains `filter_pleats=`. |
| `mcp_harness/tests/test_box_pleat_assign.py` (modify) | Integration: pinned-`F` counts, additions-only rule, dense grouping regression pins. |
| `docs/superpowers/evidence/2026-09-27-pleat-filter/` (new) | The measurement: both dense modes side by side, byte-identity digests, verdicts. |

---

### Task 1: `pleat_filter.retain` — the predicate

**Files:**
- Create: `mcp_harness/box_pleat/pleat_filter.py`
- Test: `mcp_harness/tests/test_box_pleat_pleat_filter.py`

**Interfaces:**
- Consumes: `box_pleat.assign.Piece` (fields `a: tuple[int,int]`, `b: tuple[int,int]`, `role: str` in `B | axial | elev | ridge | hinge`).
- Produces: `retain(pieces: list, N: int) -> frozenset[int]` — indices of the `axial`/`elev` pieces F.1.1 steps 3-4 keep. Non-candidates are never in the result. Also `_orientation(piece) -> str` (`"h"`/`"v"`, raises `ValueError` on a non-axis-aligned-unit piece) and the module constant `X_SHAPE_MIN_RIDGES = 4`.

- [ ] **Step 1: Write the failing tests**

Create `mcp_harness/tests/test_box_pleat_pleat_filter.py`:

```python
"""COrigami F.1.1 steps 3-4, tested on hand-built piece lists.

Every fixture is built by hand so each test states exactly the geometry it
depends on, and every count assertion is paired with a non-vacuity assertion.

TWO CLAUSES OF THIS PREDICATE ARE VACUOUS IN PRODUCTION GEOMETRY and are
therefore ONLY reachable from hand-built fixtures:

  * the X-shape clause (four ridges at one vertex). Measured ridge-incidence
    degree 4: 0 on `lizard`, 1 on `bird` -- our ridges come from Lang's
    straight skeleton, whose edges meet at nodes rather than crossing.
  * the perpendicularity requirement in clause (a). Phase 0 measured `v1`
    (perpendicular hinge) == `v2` (any hinge) on all six subjects, i.e. real
    geometry contains no candidate that touches ONLY parallel hinges.

Both are still implemented as the paper states them, so both are tested here.
A test file that skipped them would leave a silently-omitted clause
indistinguishable from a buggy one.
"""
import json
import os

import pytest

from box_pleat import pleat_filter
from box_pleat.assign import Piece
from box_pleat.compile import compile_tree

_RULE6_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "docs", "superpowers", "evidence",
    "2026-09-08-vlm-tree-authoring", "data", "rule6_serve.json",
)


def test_orientation_refuses_a_diagonal_piece():
    """Ridges may be diagonal, but a CANDIDATE or HINGE never is (measured:
    every `elev` and `hinge` piece is axis-aligned). Guessing an orientation
    for a diagonal would hide a caller bug."""
    with pytest.raises(ValueError):
        pleat_filter._orientation(Piece((0, 0), (1, 1), "elev"))


def test_orientation_refuses_a_non_unit_piece():
    with pytest.raises(ValueError):
        pleat_filter._orientation(Piece((0, 0), (2, 0), "elev"))


def test_candidate_touching_a_perpendicular_hinge_is_retained():
    # horizontal candidate at (0,0)-(1,0); vertical hinge shares (0,0)
    pieces = [Piece((0, 0), (1, 0), "elev"),
              Piece((0, 0), (0, 1), "hinge")]
    # Fixture guard before the exact-set assertion below: an exact set already
    # implies its own cardinality, so a `len(keep) == 1` pairing would assert
    # nothing new. What needs pinning is that the fixture is what it claims.
    assert [q.role for q in pieces] == ["elev", "hinge"]
    assert (pleat_filter._orientation(pieces[0])
            != pleat_filter._orientation(pieces[1]))   # genuinely perpendicular
    keep = pleat_filter.retain(pieces, N=8)
    assert keep == frozenset({0})        # the candidate, and only it


def test_candidate_touching_only_a_parallel_hinge_is_rejected():
    """This is the ONLY test that exercises clause (a)'s perpendicularity
    requirement: real geometry contains no parallel-only candidate (Phase 0
    measured v1 == v2), so without this fixture the requirement would be
    untested and could be deleted without any test noticing."""
    # horizontal candidate at (0,0)-(1,0); horizontal hinge shares (1,0)
    pieces = [Piece((0, 0), (1, 0), "elev"),
              Piece((1, 0), (2, 0), "hinge")]
    # Fixture guard, NOT a redundant assertion: an expected-empty result would
    # also pass if a typo made the hinge an `elev` piece, or the candidate a
    # `ridge`. This pins that the fixture really is "candidate + parallel
    # hinge, sharing a vertex" before trusting the emptiness.
    assert [q.role for q in pieces] == ["elev", "hinge"]
    assert pieces[0].b == pieces[1].a            # they DO share a vertex
    assert (pleat_filter._orientation(pieces[0])
            == pleat_filter._orientation(pieces[1]))   # and ARE parallel
    keep = pleat_filter.retain(pieces, N=8)
    assert keep == frozenset()


def test_an_isolated_candidate_is_rejected_while_a_qualifying_one_is_kept():
    """Both directions in ONE fixture: asserting "rejected" against a fixture
    whose result is empty for unrelated reasons would pass while testing
    nothing."""
    pieces = [
        Piece((0, 0), (1, 0), "elev"),      # 0: touches the hinge -> retained
        Piece((0, 0), (0, 1), "hinge"),     # 1
        Piece((6, 6), (7, 6), "elev"),      # 2: isolated -> rejected
    ]
    keep = pleat_filter.retain(pieces, N=8)
    assert 0 in keep                        # non-vacuity: the result is not empty
    assert 2 not in keep


def test_candidate_at_an_x_shape_vertex_is_retained_with_no_hinge_present():
    """The X-shape clause, unreachable from production geometry. Four ridge
    pieces meet at (4,4); the candidate touches that vertex; there is no hinge
    anywhere, so clause (a) cannot be what retains it."""
    v = (4, 4)
    pieces = [
        Piece(v, (5, 4), "elev"),                    # 0: the candidate
        Piece((3, 3), v, "ridge"),
        Piece(v, (5, 5), "ridge"),
        Piece((3, 5), v, "ridge"),
        Piece(v, (5, 3), "ridge"),
    ]
    assert not any(p.role == "hinge" for p in pieces)   # clause (a) is inert here
    keep = pleat_filter.retain(pieces, N=8)
    assert keep == frozenset({0})


def test_three_ridges_at_a_vertex_do_not_make_it_an_x_shape():
    """A Y-shape (three ridges) is NOT an X-shape. Our geometry has Y-shapes
    (2 on lizard, 8 on bird) and essentially no X-shapes, so this boundary is
    exactly where a wrong `>= 3` would silently retain thousands of pieces."""
    v = (4, 4)
    pieces = [
        Piece(v, (5, 4), "elev"),
        Piece((3, 3), v, "ridge"),
        Piece(v, (5, 5), "ridge"),
        Piece((3, 5), v, "ridge"),
    ]
    # Fixture guard: exactly THREE ridges touch `v`, and no hinge exists, so
    # emptiness can only come from the X-shape threshold and not from a
    # miscounted fixture or an accidental clause-(a) retention.
    assert sum(1 for q in pieces
               if q.role == "ridge" and v in (q.a, q.b)) == 3
    assert not any(q.role == "hinge" for q in pieces)
    assert pleat_filter.retain(pieces, N=8) == frozenset()


def test_step_4_reintroduces_a_border_candidate():
    """Step 4: a border segment sharing a vertex with BOTH a ridge and an
    established (step-3) pleat."""
    pieces = [
        Piece((2, 0), (3, 0), "elev"),       # 0: on the border (y == 0)
        Piece((3, 0), (3, 1), "ridge"),      # 1: ridge at (3,0)
        Piece((3, 0), (4, 0), "elev"),       # 2: step-3 survivor via the hinge
        Piece((4, 0), (4, 1), "hinge"),      # 3: perpendicular hinge at (4,0)
    ]
    keep = pleat_filter.retain(pieces, N=8)
    assert 2 in keep                         # non-vacuity: step 3 retained one
    assert 0 in keep                         # step 4 reintroduced the border one


def test_step_4_is_one_pass_and_does_not_bootstrap_on_its_own_additions():
    """"An established pleat" reads as step 3's output. Piece 0 qualifies only
    if piece 1 -- itself a step-4 addition -- counted as established. One pass
    means it does not."""
    pieces = [
        Piece((0, 0), (1, 0), "elev"),       # 0: border, needs 1 to be established
        Piece((1, 0), (2, 0), "elev"),       # 1: border, step-4 addition
        Piece((1, 0), (1, 1), "ridge"),      # ridge at (1,0)
        Piece((2, 0), (2, 1), "ridge"),      # ridge at (2,0)
        Piece((2, 0), (3, 0), "elev"),       # 2: step-3 survivor via the hinge
        Piece((3, 0), (3, 1), "hinge"),      # perpendicular hinge at (3,0)
    ]
    keep = pleat_filter.retain(pieces, N=8)
    assert 4 in keep                         # non-vacuity: step 3 retained one
    assert 1 in keep                         # step 4's own addition
    assert 0 not in keep                     # NOT reached without a second pass


def test_retain_never_returns_a_non_candidate():
    pieces = [
        Piece((0, 0), (1, 0), "elev"),
        Piece((0, 0), (0, 1), "hinge"),
        Piece((2, 2), (3, 3), "ridge"),
        Piece((0, 0), (1, 0), "B"),
    ]
    keep = pleat_filter.retain(pieces, N=8)
    assert keep                                          # non-vacuity
    assert all(pieces[i].role in ("axial", "elev") for i in keep)


def test_retain_is_deterministic():
    pieces = [Piece((0, 0), (1, 0), "elev"), Piece((0, 0), (0, 1), "hinge")]
    assert pleat_filter.retain(pieces, N=8) == pleat_filter.retain(pieces, N=8)


def test_retain_is_non_degenerate_on_a_real_compiled_subject():
    """`interleave.adjacency`'s second definition passed every hand-built unit
    test in its own file while producing an EMPTY graph on every real subject
    -- a vacuous pass that looked like success. A fix dispatch in that wave
    made this assertion mandatory for any new geometric predicate.

    `bird`, following that file's precedent: it compiles faster than `lizard`
    (~3.7s vs ~7s) and carries far more candidates.
    """
    entries = {e["subject"]: e for e in json.load(open(_RULE6_PATH))}
    entry = entries["bird"]
    res = compile_tree(entry["requested"], entry["pairs"])
    assert res.stage_reached == "emit"        # non-vacuity: it actually compiled

    pieces = res.assignment.pieces
    candidates = [i for i, p in enumerate(pieces)
                  if p.role in ("axial", "elev")]
    assert len(candidates) > 10_000          # non-vacuity: bird reads 11,534
    keep = pleat_filter.retain(pieces, res.layout.N)
    assert keep, "empty -- the vacuous-pass failure mode this test exists for"
    assert len(keep) < len(candidates), "retained everything -- not a filter"
    # Phase 0's classifier measured 843 on `bird`
    # (evidence/2026-09-26-gap1-phase0/phase0.json, v4_step3_plus_step4_border).
    assert 600 < len(keep) < 1200
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -m pytest tests/test_box_pleat_pleat_filter.py -x -q
```

Expected: collection error, `ModuleNotFoundError: No module named 'box_pleat.pleat_filter'`.

- [ ] **Step 3: Write the module**

Create `mcp_harness/box_pleat/pleat_filter.py`:

```python
"""COrigami F.1.1 steps 3-4: which dense pleat candidates survive.

Spec: `docs/superpowers/specs/2026-09-27-pleat-filter-design.md`.

The paper, appendix F.1.1:

    (3) retain only segments strictly perpendicular to an intersecting hinge,
    or passing through an X-shape vertex (four intersecting ridges);
    (4) selectively re-introduce segments meeting the outer border where they
    share a vertex with both a ridge and an established pleat

`assign.pleat_paths(dense=True)` takes EVERY `axial`/`elev` piece; this module
is the filter that was never built. Measured on the corpus, it retains
5.6%-10.4% of dense candidates (`evidence/2026-09-26-gap1-phase0/`).

"INTERSECTING" MEANS SHARING A VERTEX, AND HERE THAT IS EXACTLY GEOMETRIC
INTERSECTION -- proved, not chosen. Every piece is a unit segment whose
direction is (1,0), (0,1) or (1,1) on the half-grid. Two such segments meet
only at half-grid points, and a half-grid point lying on a unit segment is one
of its endpoints. So no separate crossing test is needed, including for a
diagonal ridge against an axis-aligned candidate.

TWO CLAUSES ARE VACUOUS IN THIS PROJECT'S GEOMETRY. Do not read them as
load-bearing, and do not delete them either:

  * X-shape (four ridges at a vertex) reads 0 on `lizard` and 1 on `bird`.
    Our ridges come from Lang's straight skeleton (`skeleton.py`), whose edges
    meet at nodes rather than crossing; COrigami's evidently do cross.
  * The perpendicularity requirement never discriminates: Phase 0 measured
    `v1` (perpendicular hinge) == `v2` (any hinge) on all six subjects.

They are implemented as the paper states them because our ridge construction
may change, the X count is not identically zero, and a silently-omitted clause
is indistinguishable from a buggy one. Both are covered by hand-built fixtures
in `tests/test_box_pleat_pleat_filter.py`.

THE FILTER GATES DENSE-MODE ADDITIONS ONLY. A piece whose elevation profile
already reads M or V is a variable in both modes; `initial_readings`' branch
order enforces that, not this module. `retain` reports what F.1.1 keeps; it
does not decide what survives overall.
"""
from __future__ import annotations

import collections

#: An X-shape vertex is "four intersecting ridges" (F.1.1 step 3). THREE is a
#: Y-shape and must NOT qualify -- our geometry has Y-shapes and essentially no
#: X-shapes, so a `>= 3` here would silently retain thousands of pieces.
X_SHAPE_MIN_RIDGES = 4

_CANDIDATE_ROLES = ("axial", "elev")


def _orientation(piece) -> str:
    """"h" if the piece runs along x, "v" if along y.

    Refuses anything that is not an axis-aligned UNIT segment. Candidates and
    hinges are always axis-aligned unit pieces (measured on `lizard`: every
    `elev` and `hinge` piece is), so a diagonal here is a caller bug, and
    guessing would hide it. Ridges may be diagonal, but this is never called
    on a ridge -- only their INCIDENCE COUNT matters.
    """
    dx = abs(piece.b[0] - piece.a[0])
    dy = abs(piece.b[1] - piece.a[1])
    if (dx, dy) == (1, 0):
        return "h"
    if (dx, dy) == (0, 1):
        return "v"
    raise ValueError(
        f"not an axis-aligned unit piece: {piece.a}-{piece.b} role={piece.role}")


def retain(pieces, N) -> frozenset[int]:
    """Indices of the `axial`/`elev` pieces COrigami F.1.1 steps 3-4 keep.

    Pure: no I/O, no geometry construction, no mutation of `pieces`. A
    non-candidate (`B`, `ridge`, `hinge`) is never in the result and is never
    affected by it -- callers keep those exactly as before.
    """
    at_vertex: dict = collections.defaultdict(list)
    for i, p in enumerate(pieces):
        at_vertex[p.a].append(i)
        at_vertex[p.b].append(i)

    x_vertices = {
        v for v, ids in at_vertex.items()
        if sum(1 for i in ids if pieces[i].role == "ridge") >= X_SHAPE_MIN_RIDGES
    }

    candidates = [i for i, p in enumerate(pieces)
                  if p.role in _CANDIDATE_ROLES]

    # --- step 3 -----------------------------------------------------------
    step3 = set()
    for i in candidates:
        p = pieces[i]
        o = _orientation(p)
        for v in (p.a, p.b):
            if v in x_vertices:
                step3.add(i)
                break
            if any(pieces[j].role == "hinge" and _orientation(pieces[j]) != o
                   for j in at_vertex[v]):
                step3.add(i)
                break

    # --- step 4: ONE pass over step 3's output ----------------------------
    # "an ESTABLISHED pleat" reads as step 3's output. Iterating to a fixpoint
    # would let step 4 bootstrap off its own additions -- a different and
    # larger filter than the paper describes. Pinned by
    # test_step_4_is_one_pass_and_does_not_bootstrap_on_its_own_additions.
    established = {v for i in step3 for v in (pieces[i].a, pieces[i].b)}
    step4 = set()
    for i in candidates:
        if i in step3:
            continue
        p = pieces[i]
        if not any(c in (0, 2 * N) for v in (p.a, p.b) for c in v):
            continue
        touches_ridge = any(pieces[j].role == "ridge"
                            for v in (p.a, p.b) for j in at_vertex[v])
        if touches_ridge and any(v in established for v in (p.a, p.b)):
            step4.add(i)

    return frozenset(step3 | step4)
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -m pytest tests/test_box_pleat_pleat_filter.py -q
```

Expected: all pass. `test_retain_is_non_degenerate_on_a_real_compiled_subject` takes ~4s (it compiles `bird`).

- [ ] **Step 5: Replace the loose bound with the measured value**

Run the real-subject test verbosely and read the retained count:

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -c "
import json, os
from box_pleat import pleat_filter
from box_pleat.compile import compile_tree
p = os.path.join('..','docs','superpowers','evidence','2026-09-08-vlm-tree-authoring','data','rule6_serve.json')
e = {x['subject']: x for x in json.load(open(p))}['bird']
res = compile_tree(e['requested'], e['pairs'])
cand = [i for i,q in enumerate(res.assignment.pieces) if q.role in ('axial','elev')]
keep = pleat_filter.retain(res.assignment.pieces, res.layout.N)
print('bird candidates', len(cand), 'retained', len(keep))
"
```

In `test_retain_is_non_degenerate_on_a_real_compiled_subject`, replace
`assert 600 < len(keep) < 1200` with an exact pin on the printed number, e.g.:

```python
    # Regression pin, measured 2026-09-27 by this task's Step 5. Phase 0's
    # independent classifier read 843 (evidence/2026-09-26-gap1-phase0/
    # phase0.json, v4_step3_plus_step4_border); a DIFFERENT number here means
    # this module and that classifier disagree, which is a finding, not a
    # number to overwrite.
    assert len(keep) == <MEASURED>
```

If the measured value is not 843, **stop and report it** rather than pinning it silently: the two implementations were meant to agree, and a disagreement is information about which is wrong.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/box_pleat/pleat_filter.py mcp_harness/tests/test_box_pleat_pleat_filter.py
git commit -m "$(printf '%s\n' 'box_pleat: pleat_filter.retain -- COrigami F.1.1 steps 3-4' '' 'The selection filter dense mode never had. pleat_paths(dense=True) takes' 'every axial/elev piece; measured on the corpus this predicate retains' '5.6%-10.4% of them.' '' 'Two clauses are VACUOUS in our geometry and tested only from hand-built' 'fixtures: X-shape (0 on lizard, 1 on bird -- straight-skeleton ridges meet' 'at nodes rather than crossing) and the perpendicularity requirement (Phase 0' 'measured v1 == v2 on all six subjects). Both implemented as the paper states' 'them, because a silently-omitted clause is indistinguishable from a buggy' 'one. X_SHAPE_MIN_RIDGES = 4 with a test pinning that THREE (a Y-shape) does' 'not qualify.' '' 'Step 4 is ONE pass, not a fixpoint -- "an established pleat" reads as step' '3s output, and iterating would let step 4 bootstrap off its own additions.' 'Pinned by a test.' '' 'Non-degeneracy asserted on a real compiled subject, mandatory since' 'interleave.adjacency definition 2 passed every hand-built test while' 'producing an empty graph on all real data.' '' 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>')"
```

---

### Task 2: `pleat_paths`' dense candidate test becomes "not pinned"

> ⚠ **CORRECTED DURING IMPLEMENTATION (2026-09-27).** The code below originally
> said the dense test should be `labels[i] is not None` -> skip. That is WRONG:
> `pleat_paths`' second parameter is named `labels` but `assign` passes
> **`probe`** (`assign.py:611`), in which a LIVE candidate reads `"M"`/`"V"` and
> only a REJECTED one reads `"F"`. `is not None` would have skipped every live
> candidate (`lizard` 365 paths -> 3). The correct test is
> **`labels[i] == "F"` -> skip**, which also keeps centre-column pieces
> (`probe` `None`). Steps 3 and 4 below carry the corrected text.

**Files:**
- Modify: `mcp_harness/box_pleat/assign.py` (`pleat_paths`, the candidate loop at ~line 396 and the docstring above it)
- Test: `mcp_harness/tests/test_box_pleat_assign.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces: `pleat_paths(pieces, labels, *, dense: bool = False) -> list` — signature UNCHANGED. In dense mode it now skips a piece whose `labels[i] is not None`.

**This task is a provably inert refactor.** Nothing pins a dense candidate to `F` yet, so the change must not alter any output. Verify that before moving on.

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_box_pleat_assign.py`:

```python
def test_dense_pleat_paths_skips_a_pinned_piece():
    """The filter (Task 4) expresses itself by PINNING a rejected candidate to
    "F" in `initial_readings`. `pleat_paths` must then not group it."""
    pieces = [A.Piece((0, 0), (1, 0), "elev"),
              A.Piece((1, 0), (2, 0), "elev")]
    labels = [None, "F"]
    groups = A.pleat_paths(pieces, labels, dense=True)
    grouped = {i for g in groups for i in g}
    assert 0 in grouped          # non-vacuity: the unpinned piece IS grouped
    assert 1 not in grouped


def test_dense_pleat_paths_still_groups_a_centre_column_piece():
    """A centre-column piece gets a `domain` and NO `pleat_lab`, so its probe
    label is None -- not "M"/"V". Testing `probe[i] in ("M","V")` instead of
    `labels[i] is None` would silently drop these, a behaviour change in
    UNFILTERED dense that no sparse byte-identity test would catch."""
    pieces = [A.Piece((0, 0), (1, 0), "elev"),
              A.Piece((1, 0), (2, 0), "elev")]
    labels = [None, None]        # exactly what a centre-column piece carries
    groups = A.pleat_paths(pieces, labels, dense=True)
    grouped = {i for g in groups for i in g}
    assert grouped == {0, 1}


def test_dense_grouping_on_a_real_subject_is_unchanged_by_the_not_pinned_test():
    """Regression pin for Task 2's refactor. Committed values from
    `evidence/2026-09-24-dense-pleats/dense_labelling.json`: `lizard` reads 365
    dense paths. If this moves, the "not pinned" test is not equivalent to the
    old "no label test" in unfiltered dense."""
    entries = {e["subject"]: e for e in json.load(open(_RULE6_PATH))}
    entry = entries["lizard"]
    res = compile_tree(entry["requested"], entry["pairs"])
    assert res.stage_reached == "emit"        # non-vacuity: it compiled

    N, pieces = res.layout.N, res.assignment.pieces
    face_list = A.faces(N, pieces)
    prof, face_of = A.profiles(N, pieces, res.contours, face_list,
                               getattr(res.layout, "boundary_elev", None))
    _, _, _, probe = A.initial_readings(N, pieces, res.contours, prof, face_of,
                                        dense=True)
    groups = A.pleat_paths(pieces, probe, dense=True)
    assert len(groups) == 365
```

If `test_box_pleat_assign.py` lacks `_RULE6_PATH`, `json`, `os` or
`compile_tree`, add them at the top of the file, matching
`tests/test_box_pleat_interleave.py`:

```python
import json
import os

from box_pleat.compile import compile_tree

_RULE6_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "docs", "superpowers", "evidence",
    "2026-09-08-vlm-tree-authoring", "data", "rule6_serve.json",
)
```

- [ ] **Step 2: Run the tests to verify the first one fails**

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -m pytest tests/test_box_pleat_assign.py -q \
  -k "dense_pleat_paths_skips_a_pinned or centre_column_piece or grouping_on_a_real_subject"
```

Expected: `test_dense_pleat_paths_skips_a_pinned_piece` FAILS (`1 in grouped` — today dense applies no label test at all). The other two PASS already.

- [ ] **Step 3: Change the candidate test**

In `mcp_harness/box_pleat/assign.py`, inside `pleat_paths`, replace:

```python
    for i, p in enumerate(pieces):
        if p.role not in ("axial", "elev"):
            continue
        if not dense and labels[i] not in ("M", "V"):
            continue
```

with:

```python
    for i, p in enumerate(pieces):
        if p.role not in ("axial", "elev"):
            continue
        if dense:
            # A PINNED piece is not a pleat candidate. NOTE this
            # parameter is named `labels` but `assign` passes `probe`
            # (`assign.py`: `pleat_paths(pieces, probe, dense=dense)`), in
            # which a live candidate reads "M"/"V" (from `pleat_lab`), a
            # centre-column piece reads None (it gets `domain`, not
            # `pleat_lab`), and only a candidate `pleat_filter` REJECTED
            # reads "F". So testing for "F" -- not for `is None`, and not
            # for membership of ("M","V") -- is what skips exactly the
            # rejected ones while keeping centre-column pieces. In
            # UNFILTERED dense nothing reads "F" at all (the pinning branch
            # in `initial_readings` is unreachable when `retained is
            # None`), so this selects every candidate exactly as the old
            # "no label test at all" did.
            if labels[i] == "F":
                continue
        elif labels[i] not in ("M", "V"):
            continue
```

- [ ] **Step 4: Rewrite the docstring paragraph that forbids this**

In the same function's docstring, replace:

```python
    `labels` is read on no code path when `dense=True` -- dense mode groups
    by connectivity alone -- but the parameter is still required and still
    positional; it is simply ignored, on purpose, in that mode. Do not
    "fix" a dense-mode caller to pass a meaningful `labels` argument.
```

with:

```python
    `labels` IS read in dense mode, as of spec
    `2026-09-27-pleat-filter-design.md`: a piece with a non-`None` label has
    been PINNED (to "F", by `initial_readings` when `pleat_filter` rejected
    it) and is therefore not a pleat candidate. An earlier revision of this
    docstring said `labels` "is read on no code path when `dense=True`" and
    told callers not to pass a meaningful value; that was true before the
    filter existed and is now wrong. Dense mode still groups by CONNECTIVITY
    alone -- the label decides only whether a piece is a candidate at all,
    never whether two candidates join.
```

- [ ] **Step 5: Run the tests to verify they pass**

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -m pytest tests/test_box_pleat_assign.py tests/test_box_pleat_interleave.py -q
```

Expected: all pass, including the 365-path regression pin. `test_box_pleat_interleave.py` is included because it calls `pleat_paths(dense=True)` directly.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/box_pleat/assign.py mcp_harness/tests/test_box_pleat_assign.py
git commit -m "$(printf '%s\n' 'box_pleat: dense pleat_paths skips a PINNED piece' '' 'Provably inert on its own -- nothing pins a dense candidate yet -- and the' 'seam the pleat filter uses. In unfiltered dense every axial/elev piece has' 'labels[i] is None, so "not pinned" selects exactly what the old "no label' 'test at all" selected; lizards 365 dense paths are pinned as a regression' 'test.' '' 'NOT probe[i] in ("M","V"), which is the natural first implementation and' 'would SILENTLY DROP centre-column pieces: they get a domain and no' 'pleat_lab, so their probe is None. That is a behaviour change in unfiltered' 'dense that no sparse byte-identity test would catch. A test pins it.' '' 'The docstring paragraph forbidding exactly this edit is rewritten, since it' 'documented a contract that the filter deliberately changes.' '' 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>')"
```

---

### Task 3: `initial_readings` gains `retained=`

**Files:**
- Modify: `mcp_harness/box_pleat/assign.py` (`initial_readings`, signature at line 297 and the dense branch at ~line 345)
- Test: `mcp_harness/tests/test_box_pleat_assign.py`

**Interfaces:**
- Consumes: nothing from Tasks 1-2.
- Produces: `initial_readings(N, pieces, contours, prof, face_of, *, dense: bool = False, retained=None)`. With `retained=None` behaviour is unchanged. With a `frozenset[int]`, a dense candidate NOT in it is pinned exactly as sparse pins it.

- [ ] **Step 1: Write the failing test**

Append to `mcp_harness/tests/test_box_pleat_assign.py`:

```python
def _lizard_readings_inputs():
    """`lizard`'s real geometry, ready for `initial_readings`."""
    entries = {e["subject"]: e for e in json.load(open(_RULE6_PATH))}
    entry = entries["lizard"]
    res = compile_tree(entry["requested"], entry["pairs"])
    assert res.stage_reached == "emit"
    N, pieces = res.layout.N, res.assignment.pieces
    face_list = A.faces(N, pieces)
    prof, face_of = A.profiles(N, pieces, res.contours, face_list,
                               getattr(res.layout, "boundary_elev", None))
    return res, N, pieces, prof, face_of


def test_dense_readings_pin_nothing_when_retained_is_none():
    """Today's dense behaviour, restated as the `retained=None` contract."""
    res, N, pieces, prof, face_of = _lizard_readings_inputs()
    labels, _, _, _ = A.initial_readings(N, pieces, res.contours, prof,
                                         face_of, dense=True, retained=None)
    pinned_f = sum(1 for i, p in enumerate(pieces)
                   if p.role in ("axial", "elev") and labels[i] == "F")
    candidates = sum(1 for p in pieces if p.role in ("axial", "elev"))
    assert candidates > 4000          # non-vacuity: lizard reads 4,488
    assert pinned_f == 0


def test_dense_readings_pin_every_candidate_the_filter_rejects():
    """With an EMPTY retained set, every dense-only candidate is pinned -- and
    the ones sparse already keeps are NOT, which is the additions-only rule."""
    res, N, pieces, prof, face_of = _lizard_readings_inputs()
    labels, _, pleat_lab, _ = A.initial_readings(
        N, pieces, res.contours, prof, face_of, dense=True,
        retained=frozenset())
    pinned_f = sum(1 for i, p in enumerate(pieces)
                   if p.role in ("axial", "elev") and labels[i] == "F")
    assert pinned_f > 0               # non-vacuity: pinning actually happened
    # additions-only: a piece whose profile reads M/V is still a variable
    assert pleat_lab, "the M/V branch must be untouched by the filter"
    assert all(labels[i] is None for i in pleat_lab)
```

- [ ] **Step 2: Run the tests to verify the second fails**

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -m pytest tests/test_box_pleat_assign.py -q \
  -k "readings_pin_nothing or readings_pin_every_candidate"
```

Expected: `test_dense_readings_pin_nothing_when_retained_is_none` fails with
`TypeError: initial_readings() got an unexpected keyword argument 'retained'`.

- [ ] **Step 3: Add the parameter and the branch condition**

In `mcp_harness/box_pleat/assign.py`, change the signature:

```python
def initial_readings(N, pieces, contours, prof, face_of, *, dense: bool = False):
```

to:

```python
def initial_readings(N, pieces, contours, prof, face_of, *, dense: bool = False,
                     retained=None):
```

and change the dense branch:

```python
            elif lab in ("M", "V"):
                pleat_lab[i] = lab
            elif dense:
                # provisional: only its PRESENCE matters, so `probe` marks
                # this a pleat candidate. interleave.colour sets the value.
                pleat_lab[i] = "M"
            else:
                labels[i] = lab
```

to:

```python
            elif lab in ("M", "V"):
                pleat_lab[i] = lab
            elif dense and (retained is None or i in retained):
                # provisional: only its PRESENCE matters, so `probe` marks
                # this a pleat candidate. interleave.colour sets the value.
                pleat_lab[i] = "M"
            else:
                # Sparse always lands here; dense lands here only for a
                # candidate `pleat_filter` REJECTED. `lab` is "F" on this
                # path (the `elif` above catches M/V), so the piece is
                # pinned exactly as sparse pins it and `emit.py:31` drops
                # it -- no new label state is introduced.
                labels[i] = lab
```

Add to the docstring's parameter notes:

```python
    `retained`, when not `None`, is the set of piece indices
    `pleat_filter.retain` kept (spec `2026-09-27-pleat-filter-design.md`). A
    dense candidate outside it is pinned "F" instead of becoming a variable.
    `None` means no filtering, which is the pre-filter behaviour exactly.
    It gates DENSE-MODE ADDITIONS ONLY: the `elif lab in ("M", "V")` branch
    above fires first, so a piece whose profile already reads M or V stays a
    variable in both modes and the filter can never remove it ("augment,
    don't replace").
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -m pytest tests/test_box_pleat_assign.py -q
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/box_pleat/assign.py mcp_harness/tests/test_box_pleat_assign.py
git commit -m "$(printf '%s\n' 'box_pleat: initial_readings(retained=) pins a filtered-out candidate' '' 'Inert with retained=None, which is the default and today’s behaviour. With a' 'set, a dense candidate outside it falls to the existing else branch and is' 'pinned "F" exactly as sparse pins it -- no new label state.' '' 'Gates DENSE-MODE ADDITIONS ONLY: the `elif lab in ("M","V")` branch fires' 'first, so a piece whose profile already reads M/V stays a variable in both' 'modes. Filtering away a crease sparse keeps would be a regression on the' 'sparse baseline, not a filter. Both directions tested.' '' 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>')"
```

---

### Task 4: `assign(filter_pleats=)` wires the filter in

> ⚠ **NOT COMMITTED — Phase A was HALTED 2026-09-27 during this task.** The
> activation was written, run, and abandoned. Its work is **not preserved in
> this repository** -- it exists only as `.superpowers/sdd/task-4-wip.diff` in
> the author's local scratch directory, which is git-ignored and tracked
> nowhere, so no other clone has it. Treat it as unavailable. The test below asserts a headline that the
> task's own run refuted (see the annotation on its docstring), so **do not
> implement this task from the text as written.**
> `../evidence/2026-09-27-pleat-filter/README.md`.

**Files:**
- Modify: `mcp_harness/box_pleat/assign.py` (`assign` signature at line 488, the `initial_readings` call at line 581)
- Test: `mcp_harness/tests/test_box_pleat_assign.py`

**Interfaces:**
- Consumes: `pleat_filter.retain(pieces, N) -> frozenset[int]` (Task 1); `initial_readings(..., retained=)` (Task 3); `pleat_paths`' not-pinned test (Task 2).
- Produces: `assign(layout, ridges, boundary_ridges, contours, *, budget=500_000, global_check=None, layer_checks=200, dense=False, filter_pleats=False, debug_clause_sizes=None)`.

- [ ] **Step 1: Write the failing test**

Append to `mcp_harness/tests/test_box_pleat_assign.py`:

⚠ **The docstring below quotes a WITHDRAWN headline.** "The filter rejects ~90% of
dense candidates" was measured at unit-piece granularity; at COrigami's own unit (a
segment) the filter retains **100%**, and `assign(dense=True, filter_pleats=True)`
does not even reach the search — it fails as
`AssignFail(kind='maekawa_fixed', site=(1, 21))`. **This test as written cannot
pass and was never committed**; the withdrawn figure did not ship into any test in
`mcp_harness/` (checked 2026-09-27 by grep: no match for `rejects ~90` or
`far_fewer_pieces_than_unfiltered` anywhere under `mcp_harness/`). Left visible,
unerased, as the plan text that the measurement refuted.
`../evidence/2026-09-27-pleat-filter/README.md`.

```python
def test_filtered_dense_assign_creases_far_fewer_pieces_than_unfiltered():
    """The headline of spec `2026-09-27-pleat-filter-design.md`: the filter
    rejects ~90% of dense candidates.  [WITHDRAWN 2026-09-27 -- wrong unit; at
    segment granularity the filter retains 100%.  See the note above.]
    Run BOTH dense modes in one process on
    the SAME geometry -- the in-process A/B the spec's section 5 exists for.
    """
    entries = {e["subject"]: e for e in json.load(open(_RULE6_PATH))}
    entry = entries["lizard"]
    res = compile_tree(entry["requested"], entry["pairs"])
    assert res.stage_reached == "emit"

    unfiltered = A.assign(res.layout, res.ridges, res.boundary_ridges,
                          res.contours, dense=True, global_check=None)
    filtered = A.assign(res.layout, res.ridges, res.boundary_ridges,
                        res.contours, dense=True, filter_pleats=True,
                        global_check=None)
    assert not isinstance(unfiltered, A.AssignFail)
    assert not isinstance(filtered, A.AssignFail)

    n_un = sum(1 for l in unfiltered.labels if l in ("M", "V"))
    n_fi = sum(1 for l in filtered.labels if l in ("M", "V"))
    assert n_un == 4868            # non-vacuity + committed dense baseline
    assert n_fi < n_un             # the filter removed creases
    assert n_fi > 0                # non-vacuity: it did not remove everything


def test_filter_pleats_is_ignored_when_not_dense():
    """`filter_pleats` is documented as meaningless without `dense`. Assert it,
    so a future caller cannot silently change sparse output through it."""
    entries = {e["subject"]: e for e in json.load(open(_RULE6_PATH))}
    entry = entries["lizard"]
    res = compile_tree(entry["requested"], entry["pairs"])
    plain = A.assign(res.layout, res.ridges, res.boundary_ridges, res.contours,
                     global_check=None)
    flagged = A.assign(res.layout, res.ridges, res.boundary_ridges,
                       res.contours, filter_pleats=True, global_check=None)
    assert not isinstance(plain, A.AssignFail)
    assert plain.labels == flagged.labels
    assert sum(1 for l in plain.labels if l in ("M", "V")) > 0   # non-vacuity
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -m pytest tests/test_box_pleat_assign.py -q \
  -k "filtered_dense_assign_creases or filter_pleats_is_ignored"
```

Expected: `TypeError: assign() got an unexpected keyword argument 'filter_pleats'`.

- [ ] **Step 3: Add the import, the parameter, and the call**

At the top of `mcp_harness/box_pleat/assign.py`, beside the existing
`from . import interleave`, add:

```python
from . import pleat_filter
```

Change `assign`'s signature from:

```python
def assign(layout, ridges: list, boundary_ridges: list, contours: dict, *,
           budget: int = 500_000, global_check=None, layer_checks: int = 200,
           dense: bool = False, debug_clause_sizes: list | None = None):
```

to:

```python
def assign(layout, ridges: list, boundary_ridges: list, contours: dict, *,
           budget: int = 500_000, global_check=None, layer_checks: int = 200,
           dense: bool = False, filter_pleats: bool = False,
           debug_clause_sizes: list | None = None):
```

Change the `initial_readings` call from:

```python
    labels, domain, pleat_lab, probe = initial_readings(
        N, pieces, contours, prof, face_of, dense=dense)
```

to:

```python
    # COrigami F.1.1 steps 3-4 (spec `2026-09-27-pleat-filter-design.md`).
    # Computed ONCE here and expressed through `initial_readings`' pinning, so
    # `pleat_paths` needs no filter argument of its own -- it sees the result
    # as "this piece is pinned".
    retained = (pleat_filter.retain(pieces, N)
                if dense and filter_pleats else None)
    labels, domain, pleat_lab, probe = initial_readings(
        N, pieces, contours, prof, face_of, dense=dense, retained=retained)
```

Add to `assign`'s docstring:

```python
    `filter_pleats` applies COrigami F.1.1 steps 3-4 (`pleat_filter.retain`)
    to the dense candidate set, pinning every candidate the filter rejects.
    IGNORED unless `dense` -- a conditional parameter, accepted so that both
    dense modes run in one process on the same geometry, which is what makes
    the filtered/unfiltered comparison confound-free (spec
    `2026-09-27-pleat-filter-design.md` section 5).
```

- [ ] **Step 4: Run to verify it passes**

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -m pytest tests/test_box_pleat_assign.py tests/test_box_pleat_interleave.py -q
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/box_pleat/assign.py mcp_harness/tests/test_box_pleat_assign.py
git commit -m "$(printf '%s\n' 'box_pleat: assign(filter_pleats=) applies the F.1.1 filter' '' 'retain() is computed once and expressed through initial_readings pinning, so' 'pleat_paths needs no filter argument -- it sees the result as "pinned".' '' 'filter_pleats is ignored unless dense, and a test asserts that so no future' 'caller can change sparse output through it. Both dense modes now run in ONE' 'process on the SAME geometry, which is the confound-free A/B the spec asks' 'for; the test exercises exactly that.' '' 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>')"
```

---

### Task 5: `compile_tree(filter_pleats=)`

**Files:**
- Modify: `mcp_harness/box_pleat/compile.py` (signature at line 118, `assign` call at line 310)
- Test: `mcp_harness/tests/test_box_pleat_layers.py`

**Interfaces:**
- Consumes: `assign(..., filter_pleats=False)` (Task 4).
- Produces: `compile_tree(nodes, pairs, *, max_N=None, pack_budget=200_000, assign_budget=500_000, layer_budget=200, certify_budget=..., dense=False, filter_pleats=False) -> Result`.

- [ ] **Step 1: Write the failing test**

Append to `mcp_harness/tests/test_box_pleat_layers.py`:

```python
def test_compile_tree_accepts_filter_pleats_and_leaves_sparse_untouched():
    """`filter_pleats` must reach `assign` and must do nothing without
    `dense`. A cheap subject: `starfish` compiles in ~0.1s."""
    entries = {e["subject"]: e for e in json.load(open(_RULE6_PATH))}
    entry = entries["starfish"]
    plain = compile_tree(entry["requested"], entry["pairs"])
    flagged = compile_tree(entry["requested"], entry["pairs"],
                           filter_pleats=True)
    assert plain.stage_reached == "emit"        # non-vacuity: it compiled
    assert flagged.stage_reached == "emit"
    assert plain.assignment.labels == flagged.assignment.labels
```

Add `json`, `os`, `_RULE6_PATH` and `compile_tree` imports at the top of that
file if absent, matching `tests/test_box_pleat_interleave.py`.

- [ ] **Step 2: Run to verify it fails**

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -m pytest tests/test_box_pleat_layers.py -q \
  -k "accepts_filter_pleats"
```

Expected: `TypeError: compile_tree() got an unexpected keyword argument 'filter_pleats'`.

- [ ] **Step 3: Thread the parameter**

In `mcp_harness/box_pleat/compile.py`, change:

```python
def compile_tree(nodes, pairs, *, max_N=None, pack_budget=200_000,
                 assign_budget=500_000, layer_budget=200,
                 certify_budget=layer_certify.CERTIFY_BUDGET,
                 dense: bool = False) -> Result:
```

to:

```python
def compile_tree(nodes, pairs, *, max_N=None, pack_budget=200_000,
                 assign_budget=500_000, layer_budget=200,
                 certify_budget=layer_certify.CERTIFY_BUDGET,
                 dense: bool = False, filter_pleats: bool = False) -> Result:
```

and the `assign` call from:

```python
        asg = assign(lay, ridges, boundary, cont, budget=assign_budget,
                     global_check=_check, layer_checks=layer_budget,
                     dense=dense)
```

to:

```python
        asg = assign(lay, ridges, boundary, cont, budget=assign_budget,
                     global_check=_check, layer_checks=layer_budget,
                     dense=dense, filter_pleats=filter_pleats)
```

Add to the docstring, after the existing `dense` paragraph:

```python
    `filter_pleats`, when `True` AND `dense` is `True`, applies COrigami
    F.1.1 steps 3-4 to the dense candidate set (spec
    `2026-09-27-pleat-filter-design.md`). Ignored when `dense` is `False`.
    `dense=True, filter_pleats=False` remains available and byte-identical to
    the pre-filter dense behaviour, so the two can be compared in one process.
```

- [ ] **Step 4: Run to verify it passes**

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -m pytest tests/test_box_pleat_layers.py -q -k "accepts_filter_pleats"
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/box_pleat/compile.py mcp_harness/tests/test_box_pleat_layers.py
git commit -m "$(printf '%s\n' 'box_pleat: compile_tree(filter_pleats=) threads the flag through' '' 'Ignored without dense, asserted by a test on starfish. dense=True,' 'filter_pleats=False stays byte-identical to pre-filter dense behaviour so' 'the two modes are comparable in one process.' '' 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>')"
```

---

### Task 6: Byte-identity — both guarantees, all 8 subjects

**Files:**
- Create: `docs/superpowers/evidence/2026-09-27-pleat-filter/byte_identity.py`

**Interfaces:**
- Consumes: `compile_tree(..., dense=..., filter_pleats=...)` (Task 5).
- Produces: `byte-identity.json` with, per subject, the sha256 of the emitted dict from the branch base and from HEAD, for `dense=False`; plus the dense-mode counts for `dense=True, filter_pleats=False` compared against the committed baseline.

**Both guarantees are load-bearing** (spec section 5): `dense=False` output unchanged, AND `dense=True, filter_pleats=False` output unchanged.

- [ ] **Step 1: Record the branch base**

```bash
git log --oneline -1 && git merge-base main HEAD
```

Note the merge-base SHA; call it `BASE`.

- [ ] **Step 2: Archive the base into a temp tree**

**Never move HEAD. Never use `git stash`** (the stack is shared with other
worktrees).

```bash
BASE=$(git merge-base main HEAD)
rm -rf /tmp/bp-base && mkdir -p /tmp/bp-base
git archive "$BASE" | tar -x -C /tmp/bp-base
ls /tmp/bp-base/mcp_harness/box_pleat/
```

Expected: the base's `box_pleat/` with no `pleat_filter.py`.

- [ ] **Step 3: Write the comparison script**

Create `docs/superpowers/evidence/2026-09-27-pleat-filter/byte_identity.py`:

```python
"""Both byte-identity guarantees of spec 2026-09-27-pleat-filter-design.md.

  1. `dense=False` emits byte-identical folds to the branch base.
  2. `dense=True, filter_pleats=False` reproduces the committed dense counts
     from `evidence/2026-09-24-dense-pleats/dense_labelling.json`.

Guarantee 1 is verified against a `git archive` of the merge-base, extracted
to a temp tree -- HEAD never moves and `git stash` is never used, because the
stash stack is shared with the main checkout and other worktrees.

One trap recorded from the dense-pleats wave: an earlier comparison read
IDENTICAL on all 8 while the `dog` and `guinea_pig` dumps PREDATED the
verified base archive. Had they come from HEAD by mistake, "IDENTICAL" would
have been vacuous for exactly the two most expensive subjects. This script
therefore computes both sides in one run and never reuses an older dump.

Run from mcp_harness (HEAD side), with BASE_TREE pointing at the archive:
  BASE_TREE=/tmp/bp-base PYTHONPATH=. ../.venv/bin/python3 -u \\
      ../docs/superpowers/evidence/2026-09-27-pleat-filter/byte_identity.py \\
      ../docs/superpowers/evidence/2026-09-27-pleat-filter/byte-identity.json
"""
import hashlib
import json
import os
import subprocess
import sys

OUT = sys.argv[1]
BASE_TREE = os.environ["BASE_TREE"]
RULE6 = os.path.join("..", "docs", "superpowers", "evidence",
                     "2026-09-08-vlm-tree-authoring", "data", "rule6_serve.json")
SUBJECTS = ["starfish", "bird", "lizard", "horse", "octopus", "frog",
            "guinea_pig", "dog"]

#: lizard's committed unfiltered-dense baseline
#: (evidence/2026-09-24-dense-pleats/dense_labelling.json)
DENSE_BASELINE = {"lizard": {"dense_mv": 4868, "paths": 365}}

#: Committed sparse digests (evidence/2026-09-24-dense-pleats/README.md §2),
#: 16-char prefixes. A THIRD check, independent of base-vs-head: if both sides
#: agree with each other but neither matches these, the sparse path moved
#: before this branch and the base==head comparison would hide it.
COMMITTED_PREFIX = {
    "starfish": "d9941daef6ec28d4", "bird": "cf0b50cfe50b9ef5",
    "lizard": "3a9206eeb3c5a55f", "horse": "0e9411295dee9c0f",
    "octopus": "6bb99090370fc2a0", "frog": "09c83d7c92bf39f8",
    "guinea_pig": "f882f4bd74447289", "dog": "4dbebfe175f61a96",
}

_RUNNER = r'''
import hashlib, json, sys
from box_pleat.compile import compile_tree
entries = {e["subject"]: e for e in json.load(open(sys.argv[1]))}
e = entries[sys.argv[2]]
res = compile_tree(e["requested"], e["pairs"])
if res.stage_reached != "emit":
    print(json.dumps({"stage": res.stage_reached})); raise SystemExit
# EXACTLY the committed serialisation (evidence/2026-09-24-dense-pleats/
# dump_folds.py: json.dumps(res.fold, sort_keys=True)), so these digests are
# comparable to the committed table and not merely to each other.
blob = json.dumps(res.fold, sort_keys=True).encode()
print(json.dumps({"stage": "emit",
                  "sha256": hashlib.sha256(blob).hexdigest()}))
'''


def sparse_digest(tree, subject):
    """Compile `subject` sparsely inside `tree` and return its fold's sha256.

    A SUBPROCESS per side, because both trees define `box_pleat` and importing
    two versions into one interpreter would resolve to whichever landed in
    sys.modules first -- silently comparing a tree against itself.
    """
    harness = os.path.join(tree, "mcp_harness")
    rule6 = os.path.join(tree, "docs", "superpowers", "evidence",
                         "2026-09-08-vlm-tree-authoring", "data",
                         "rule6_serve.json")
    out = subprocess.run(
        [sys.executable, "-c", _RUNNER, rule6, subject],
        cwd=harness, capture_output=True, text=True,
        env={**os.environ, "PYTHONPATH": "."})
    if out.returncode != 0:
        return {"error": out.stderr.strip()[-400:]}
    return json.loads(out.stdout.strip().splitlines()[-1])


def main():
    rows = []
    for s in SUBJECTS:
        row = {"subject": s}
        row["base"] = sparse_digest(BASE_TREE, s)
        row["head"] = sparse_digest(os.path.join("..", ""), s)
        row["sparse_identical"] = (
            row["base"].get("sha256") is not None
            and row["base"].get("sha256") == row["head"].get("sha256"))
        row["matches_committed"] = bool(
            row["head"].get("sha256", "").startswith(COMMITTED_PREFIX[s]))
        rows.append(row)
        json.dump(rows, open(OUT, "w"), indent=1)
        print(f"{s:11} sparse base={row['base'].get('sha256','?')[:16]} "
              f"head={row['head'].get('sha256','?')[:16]} "
              f"{'IDENTICAL' if row['sparse_identical'] else 'DIFFERS'}",
              flush=True)

    # --- guarantee 2: unfiltered dense counts ---------------------------
    sys.path.insert(0, ".")
    from box_pleat import assign as A
    from box_pleat.compile import compile_tree
    entries = {e["subject"]: e for e in json.load(open(RULE6))}
    dense_rows = []
    for s, want in DENSE_BASELINE.items():
        res = compile_tree(entries[s]["requested"], entries[s]["pairs"])
        asg = A.assign(res.layout, res.ridges, res.boundary_ridges,
                       res.contours, dense=True, global_check=None)
        got_mv = sum(1 for l in asg.labels if l in ("M", "V"))
        N, pieces = res.layout.N, res.assignment.pieces
        face_list = A.faces(N, pieces)
        prof, face_of = A.profiles(N, pieces, res.contours, face_list,
                                   getattr(res.layout, "boundary_elev", None))
        _, _, _, probe = A.initial_readings(N, pieces, res.contours, prof,
                                            face_of, dense=True)
        got_paths = len(A.pleat_paths(pieces, probe, dense=True))
        dense_rows.append({"subject": s, "want": want,
                           "got": {"dense_mv": got_mv, "paths": got_paths},
                           "unchanged": (got_mv == want["dense_mv"]
                                         and got_paths == want["paths"])})
        print(f"{s:11} unfiltered dense mv={got_mv} paths={got_paths} "
              f"{'UNCHANGED' if dense_rows[-1]['unchanged'] else 'MOVED'}",
              flush=True)

    json.dump({"sparse": rows, "unfiltered_dense": dense_rows},
              open(OUT, "w"), indent=1)
    bad = [r["subject"] for r in rows if not r["sparse_identical"]]
    bad += [f"{r['subject']}(committed-digest)" for r in rows
            if not r["matches_committed"]]
    bad += [r["subject"] for r in dense_rows if not r["unchanged"]]
    print("\nALL GUARANTEES HOLD" if not bad else f"\nFAILED: {bad}", flush=True)


main()
```

- [ ] **Step 4: Run it**

```bash
cd mcp_harness && BASE_TREE=/tmp/bp-base PYTHONPATH=. ../.venv/bin/python3 -u \
    ../docs/superpowers/evidence/2026-09-27-pleat-filter/byte_identity.py \
    ../docs/superpowers/evidence/2026-09-27-pleat-filter/byte-identity.json
```

Expected: `IDENTICAL` on all 8 sparse rows, `UNCHANGED` on `lizard`'s
unfiltered dense counts (4,868 M/V and 365 paths), and
`ALL GUARANTEES HOLD`. Runtime ~30 minutes: the two expensive subjects compile
on both sides (`dog` ~500s each, `guinea_pig` ~275s each).

**If any row DIFFERS, stop and report it.** A sparse difference means one of
Tasks 2-5 changed sparse behaviour; a dense MOVED means Task 2's "not pinned"
test is not equivalent to the old "no label test".

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/evidence/2026-09-27-pleat-filter/
git commit -m "$(printf '%s\n' 'evidence: both byte-identity guarantees hold across all 8 subjects' '' 'dense=False emits byte-identical folds to the merge-base, and dense=True,' 'filter_pleats=False reproduces lizards committed 4,868 M/V and 365 paths.' '' 'Base side comes from a git archive of the merge-base into a temp tree --' 'HEAD never moves, git stash is never used (the stack is shared with other' 'worktrees), and BOTH sides are computed in one run. The dense-pleats wave' 'was nearly bitten by the alternative: an earlier comparison read IDENTICAL' 'on all 8 while the dog and guinea_pig dumps predated the verified archive,' 'which would have made the claim vacuous for exactly the two most expensive' 'subjects.' '' 'Each side compiles in a SUBPROCESS: both trees define box_pleat, so' 'importing two versions into one interpreter would resolve to whichever' 'reached sys.modules first and silently compare a tree against itself.' '' 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>')"
```

---

### Task 7: The measurement — does a filtered dense pattern certify?

**Files:**
- Create: `docs/superpowers/evidence/2026-09-27-pleat-filter/filtered_dense.py`
- Create: `docs/superpowers/evidence/2026-09-27-pleat-filter/README.md`

**Interfaces:**
- Consumes: `compile_tree(..., dense=True, filter_pleats=True)` (Task 5); `pleat_filter.retain` (Task 1).
- Produces: `filtered-dense.json`, one row per subject with both dense modes side by side.

**This is the point of the whole plan.** Spec risk 4: if filtered dense still
never certifies, that REFUTES the crease-set hypothesis and redirects to the
search levers. Report a negative with the same prominence as a positive.

- [ ] **Step 1: Write the measurement script**

Create `docs/superpowers/evidence/2026-09-27-pleat-filter/filtered_dense.py`:

```python
"""Does a FILTERED dense pattern reach a layer order? (spec section 6)

Per subject, both dense modes on the SAME geometry in ONE process:
  * candidates, retained, retained %
  * dense M/V, paths, variables -- filtered vs unfiltered
  * faces, face pairs
  * the layer verdict, or UNDECIDED with its budget (never silence)

`assign(global_check=None)` measures the LABELLING; `compile_tree` measures
whether the CEGAR loop converges. Both are reported, because the dense-pleats
wave established that labelling works and layer ordering does not, and this
script exists to test whether filtering changes the second.

Each stage is capped independently by wall clock: the downstream stages grow in
FACE PAIRS (~0.4 x faces^2, measured), so one subject's blow-up must not cost
the corpus. A capped stage is recorded by NAME with the cap that stopped it.

Run from mcp_harness:
  PYTHONPATH=. ../.venv/bin/python3 -u \\
      ../docs/superpowers/evidence/2026-09-27-pleat-filter/filtered_dense.py \\
      ../docs/superpowers/evidence/2026-09-27-pleat-filter/filtered-dense.json \\
      [assign_cap_secs] [compile_cap_secs]
"""
import json
import os
import signal
import sys
import time

import flat_fold

from box_pleat import assign as A
from box_pleat import emit
from box_pleat import layers as L
from box_pleat import pleat_filter
from box_pleat.compile import compile_tree

OUT = sys.argv[1]
ASSIGN_CAP = int(sys.argv[2]) if len(sys.argv) > 2 else 300
COMPILE_CAP = int(sys.argv[3]) if len(sys.argv) > 3 else 1800
RULE6 = os.path.join("..", "docs", "superpowers", "evidence",
                     "2026-09-08-vlm-tree-authoring", "data", "rule6_serve.json")
ORDER = ["starfish", "lizard", "frog", "horse", "bird", "guinea_pig",
         "octopus", "dog"]


class Cap(Exception):
    pass


def _alarm(signum, frame):
    raise Cap()


def capped(row, name, secs, fn):
    """Run `fn()` under a wall-clock cap, recording `<name>_secs` either way."""
    t = time.time()
    old = signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(secs)
    try:
        val = fn()
    except Cap:
        row[f"{name}_secs"] = round(time.time() - t, 2)
        row[f"{name}_capped_at"] = secs
        print(f"    {name} CAPPED at {secs}s", flush=True)
        return None, False
    except Exception as exc:                # noqa: BLE001 - recorded, not swallowed
        row[f"{name}_secs"] = round(time.time() - t, 2)
        row[f"{name}_error"] = f"{type(exc).__name__}: {exc}"
        print(f"    {name} ERROR {type(exc).__name__}: {exc}", flush=True)
        return None, False
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)
    row[f"{name}_secs"] = round(time.time() - t, 2)
    return val, True


def downstream(row, prefix, layout, asg):
    """faces / face pairs / verdict for one candidate labelling."""
    fold = emit.to_fold(layout, asg)
    row[f"{prefix}_emitted_edges"] = len(fold["edges_vertices"])
    ff, ok = capped(row, f"{prefix}_flat_fold", 300,
                    lambda: flat_fold.flat_fold(fold))
    if not ok:
        return
    row[f"{prefix}_faces"] = len(ff.faces)
    graph, ok = capped(row, f"{prefix}_constraint_graph", 900,
                       lambda: L.constraint_graph(ff))
    if not ok:
        return
    row[f"{prefix}_face_pairs"] = len(graph.cons.pairs)
    labels = {k: a for _, _, k, a in ff.shared_edges if a in ("M", "V")}
    w, ok = capped(row, f"{prefix}_propagate", 900,
                   lambda: L.propagate(graph, labels))
    if ok:
        row[f"{prefix}_propagate_contradiction"] = w is not None
    verdict, ok = capped(row, f"{prefix}_certify", 900,
                         lambda: L.certify(graph, labels))
    # Spec section 7 of the dense-pleats design: an unaffordable verdict is
    # recorded as UNDECIDED with its budget. Silence is not a result.
    row[f"{prefix}_verdict"] = verdict.kind if ok else "UNMEASURED"
    if ok:
        row[f"{prefix}_verdict_free"] = verdict.free


def main():
    entries = {e["subject"]: e for e in json.load(open(RULE6))}
    rows = []
    for s in ORDER:
        row = {"subject": s}
        print(f"=== {s}", flush=True)
        res = compile_tree(entries[s]["requested"], entries[s]["pairs"])
        if res.stage_reached != "emit":
            row["error"] = f"sparse compile stopped@{res.stage_reached}"
            rows.append(row); json.dump(rows, open(OUT, "w"), indent=1); continue
        N, pieces = res.layout.N, res.assignment.pieces
        row["N"] = N
        cand = [i for i, p in enumerate(pieces) if p.role in ("axial", "elev")]
        keep = pleat_filter.retain(pieces, N)
        row["candidates"] = len(cand)
        row["retained"] = len(keep)
        row["retained_pct"] = round(100 * len(keep) / len(cand), 2) if cand else None
        row["sparse_mv"] = sum(1 for l in res.assignment.labels
                               if l in ("M", "V"))

        for prefix, flt in (("unfiltered", False), ("filtered", True)):
            asg, ok = capped(row, f"{prefix}_assign", ASSIGN_CAP,
                             lambda flt=flt: A.assign(
                                 res.layout, res.ridges, res.boundary_ridges,
                                 res.contours, dense=True, filter_pleats=flt,
                                 global_check=None))
            if not ok or isinstance(asg, A.AssignFail):
                row[f"{prefix}_assign_result"] = repr(asg)[:120] if ok else "capped"
                continue
            row[f"{prefix}_dense_mv"] = sum(1 for l in asg.labels
                                            if l in ("M", "V"))
            row[f"{prefix}_pleat_vars"] = len(asg.pleat_vars)
            row[f"{prefix}_released_vars"] = len(asg.released_vars)
            downstream(row, prefix, res.layout, asg)

        # Does the CEGAR loop converge on the FILTERED set? The question.
        out, ok = capped(row, "filtered_compile", COMPILE_CAP,
                         lambda: compile_tree(entries[s]["requested"],
                                              entries[s]["pairs"],
                                              dense=True, filter_pleats=True))
        if ok:
            row["filtered_compile_stage"] = out.stage_reached
            row["filtered_compile_failure"] = repr(out.failure)[:200]
            row["filtered_compile_verdict"] = (out.verdict.kind
                                               if out.verdict else None)
        rows.append(row)
        json.dump(rows, open(OUT, "w"), indent=1)
        print(f"  retained {row['retained']}/{row['candidates']} "
              f"({row['retained_pct']}%) "
              f"unfiltered_mv={row.get('unfiltered_dense_mv')} "
              f"filtered_mv={row.get('filtered_dense_mv')} "
              f"filtered_verdict={row.get('filtered_verdict')} "
              f"compile_stage={row.get('filtered_compile_stage')}", flush=True)
    json.dump(rows, open(OUT, "w"), indent=1)
    print("done", flush=True)


main()
```

- [ ] **Step 2: Run it on the two cheapest subjects first**

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -u \
    ../docs/superpowers/evidence/2026-09-27-pleat-filter/filtered_dense.py \
    /tmp/fd-quick.json 300 600
```

Interrupt after `lizard` completes. Confirm the row carries
`retained`, `filtered_dense_mv`, `filtered_faces`, `filtered_face_pairs`,
`filtered_verdict` and `filtered_compile_stage`. **If any is missing, fix the
script before the full run** — a multi-hour run that produces an incomplete row
wastes the whole run.

- [ ] **Step 3: Run the full corpus**

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -u \
    ../docs/superpowers/evidence/2026-09-27-pleat-filter/filtered_dense.py \
    ../docs/superpowers/evidence/2026-09-27-pleat-filter/filtered-dense.json \
    300 1800
```

Expected: several hours. `octopus` and `dog` are expected to cap at the
labelling stage in BOTH modes (they produce no candidate within 300s
unfiltered) — **unless filtering makes them reachable, which would itself be a
result worth reporting.**

- [ ] **Step 4: Write the evidence README**

Create `docs/superpowers/evidence/2026-09-27-pleat-filter/README.md` with:

- the per-subject table: candidates, retained, retained %, sparse M/V,
  unfiltered dense M/V, filtered dense M/V, faces, face pairs, verdict, and
  `filtered_compile_stage`, for both modes side by side;
- both byte-identity guarantees from Task 6 with digests;
- **the headline, stated in whichever direction the data goes.** If filtered
  dense certifies on any subject, that is gap 1's first globally-foldable dense
  pattern and must be said plainly. If it does not, write the negative as
  plainly: the crease-set hypothesis is **refuted**, spec risk 4 fired, and the
  remaining levers are F.3 (see spec risk 5 — its Y/X-shape anchors are
  themselves in doubt) and minimal unsat cores;
- whether the filtered pattern is too sparse to read as box-pleated, with the
  crease counts beside sparse's — and if so, that the remedy is F.1.1 step 5,
  **not a looser predicate**.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/evidence/2026-09-27-pleat-filter/
git commit -m "$(printf '%s\n' 'evidence: filtered dense measured across the corpus' '' 'Both dense modes on the same geometry in one process: candidates, retained,' 'dense M/V, variables, faces, face pairs, and the layer verdict for each --' 'plus whether compile_tree(dense=True, filter_pleats=True) converges, which' 'is the question the whole Phase A exists to answer.' '' 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>')"
```

---

## Plan Self-Review

**Spec coverage.** §3.1 predicate → Task 1. §3.2 vacuous clauses → Task 1 Steps 1/3 (hand-built X-shape, parallel-only rejection, Y-shape boundary). §3.3 additions-only → Task 3 Step 1's second test. §4.1 `initial_readings` → Task 3. §4.2 `pleat_paths` contract change + docstring → Task 2. §4.3 signatures → Tasks 3-5. §5 coexistence → Task 4's in-process A/B test and Task 5's docstring. §6 testing → Tasks 1-6. §7 risks → Task 7 Step 4's README instructions. §9 evidence → Tasks 6-7.

**One spec item deliberately not a task:** §7 risk 5 (F.3's anchors are in doubt). It is a finding to carry forward, not work in this plan; Task 7's README records it.

**Placeholder scan.** One intentional placeholder remains: `<MEASURED>` in Task 1 Step 5, which is a value the implementer must measure rather than a gap in the plan — the step says exactly how to obtain it and what to do if it disagrees with 843.

**Type consistency.** `retain(pieces, N) -> frozenset[int]` is used identically in Tasks 1, 4 and 7. `retained=` is the keyword in Tasks 3 and 4. `filter_pleats` is the keyword in Tasks 4, 5 and 7. `_orientation` and `X_SHAPE_MIN_RIDGES` are defined in Task 1 and referenced only there.
