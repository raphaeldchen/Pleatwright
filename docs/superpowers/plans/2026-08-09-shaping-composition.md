# Shaping Composition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `edges_foldAngle` survive across shaping ops, so `apply_display_ops` implements the composition its docstring claims, and bound `_find_tip` so an op cannot silently land on a flap the caller did not ask for.

**Architecture:** Each op currently rebuilds the whole fold-angle array from `edges_assignment` plus its own overrides, resetting every earlier op's partial angle to full ±180. The fix threads a working angle array through `_split_edges` — the same way that function already propagates `edges_assignment` — seeds it from the incoming fold, and applies overrides on top. `shaping_deep.py` imports `_split_edges` and `_find_tip` from `shaping.py`, so two of the four edit sites are shared.

**Tech Stack:** Python 3.14, stdlib only in `shaping.py` (no numpy), pytest. `shaping_deep.py` already imports numpy.

**Spec:** `docs/superpowers/specs/2026-08-09-shaping-composition-design.md`

## Global Constraints

- **No new Python dependencies.** `mcp_harness/.venv` is a **symlink to the main repo's venv**; installing mutates the user's main environment and its CI-pinned deps.
- **`shaping.py` is stdlib-only** (`import math`, `import sys`). Do not add numpy to it.
- **Never touch `mcp_harness/TreemakerWrapper.cpp`** — claimed by Goal 2 / S3 in `docs/superpowers/goals/COORDINATION.md`.
- **Do not re-bless `mcp_harness/fixtures/scorecard_baseline.jsonl`** — frozen for the duration of Goals 1 and 2.
- **`TIP_BIND_MAX = 0.05` is pinned.** If a legitimate workflow needs a larger bound, that is a finding to record, not a constant to raise.
- Test command: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest --timeout=420`. Bare `make test` never terminates on this machine.
- Worktree setup: if this is a fresh worktree, symlink from the main checkout at `<repo>`: `mcp_harness/.venv`, `mcp_harness/headless_treemaker.cpython-314-darwin.so`, `mcp_harness/OrieditaValidator.class`, `mcp_harness/oriedita/oriedita-1.1.3.jar`, `web/frontend/dist`. Without the two Java artifacts you get ~35 bogus FAIL-LINT failures in 0.3 s.
- One test in the suite, `test_auto_selection_is_deterministic`, runs 417.20 s against a 420 s timeout on an idle machine. If it fails, re-run it alone before believing it — it is a contention artifact, not your change.

---

### Task 1: Capture the pre-change single-op baseline

**This task must run on pristine code, before any production change.** Its output is the fixture that Task 6 uses to prove the fix is a no-op for single ops. Generated after any change, it is worthless.

**Files:**
- Create: `mcp_harness/fixtures/shaping_single_op_baseline.json`
- Create: `mcp_harness/probe_shaping_baseline.py`

**Interfaces:**
- Produces: `fixtures/shaping_single_op_baseline.json`, a dict `{"<golden>::<op string>": <full output fold dict>}`, consumed by Task 6.

- [ ] **Step 1: Write the generator**

Create `mcp_harness/probe_shaping_baseline.py`:

```python
"""Freeze single-op shaping output BEFORE the composition fix.

PROBE -- not an agent tool. Task 6 asserts the post-fix output is
byte-identical to this. The spec argues the fix is a no-op for single ops;
this fixture is what turns that argument into a test.

Ops are placed at the EXACT coordinates of a served tip, so binding is
unambiguous and the Task 2 bound cannot change which tip is chosen.
See docs/superpowers/plans/2026-08-09-shaping-composition.md Task 1.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import shaping            # noqa: E402
import square_complete    # noqa: E402

GOLDENS = ["dog", "dog-repaired", "quad", "hshape", "star-4",
           "hf-dog-nudged", "hf-crane-ladder-blb", "hf-dog-ladder-best"]
OUT = os.path.join(HERE, "fixtures", "shaping_single_op_baseline.json")


def served_tips(fold):
    """Every vertex _find_tip's predicate accepts, sorted for determinism."""
    vc, ea = fold["vertices_coords"], fold["edges_assignment"]
    inc = {}
    for ei, (a, b) in enumerate(fold["edges_vertices"]):
        inc.setdefault(a, []).append(ei)
        inc.setdefault(b, []).append(ei)
    out = []
    for v, eids in sorted(inc.items()):
        kinds = [ea[e] for e in eids]
        creases = [e for e in eids if ea[e] in ("M", "V")]
        if "B" not in kinds or len(creases) != 1:
            continue
        if any(k not in ("B", "F", "M", "V") for k in kinds):
            continue
        out.append((round(vc[v][0], 9), round(vc[v][1], 9)))
    return sorted(out)


def main():
    baseline = {}
    for name in GOLDENS:
        path = os.path.join(HERE, "tests", "goldens", f"{name}.fold")
        raw = json.load(open(path))
        sq = square_complete.complete_square(raw, 1.0, 1.0)
        tips = served_tips(sq)
        if not tips:
            print(f"{name}: no served tips, skipped")
            continue
        for x, y in tips[:2]:            # two per golden keeps the fixture small
            for kind, d, theta in (("reverse", 0.05, 90.0),
                                   ("outside", 0.05, 75.0)):
                op = f"{kind}:{x},{y}:{d}:{theta}"
                out = shaping.apply_display_ops(sq, [op])
                if out is sq:
                    print(f"{name}: {op} refused, skipped")
                    continue
                baseline[f"{name}::{op}"] = out
                print(f"{name}: {op} -> {len(out['edges_vertices'])} edges")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(baseline, fh, sort_keys=True, indent=1)
    print(f"\nwrote {OUT} ({len(baseline)} entries)")
    return 0 if baseline else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run it**

Run: `cd mcp_harness && PYTHONPATH=. .venv/bin/python probe_shaping_baseline.py`
Expected: a list of `<golden>: <op> -> N edges` lines and a final `wrote ... (N entries)` with **N ≥ 8**. If N is 0 the fixture is useless and Task 6 cannot gate — stop and report.

- [ ] **Step 3: Sanity-check the fixture carries partial angles**

Run:

```bash
cd mcp_harness && PYTHONPATH=. .venv/bin/python -c "
import json
b = json.load(open('fixtures/shaping_single_op_baseline.json'))
k = sorted(b)[0]
fa = b[k]['edges_foldAngle']
partial = [a for a in fa if a not in (0.0, 180.0, -180.0)]
print(k); print('edges', len(fa), 'partial angles', len(partial), partial[:5])
"
```

Expected: `partial angles` is **> 0**. A single op sets partial angles by construction; if this reads 0, the op was refused or the angle model changed and the fixture is not exercising what Task 6 needs.

- [ ] **Step 4: Commit**

```bash
git add mcp_harness/probe_shaping_baseline.py mcp_harness/fixtures/shaping_single_op_baseline.json
git commit -m "fixture(shaping): freeze single-op output BEFORE the composition fix

Task 6 asserts byte-identity against this. Generated on pristine code --
regenerating it after the fix would make the gate vacuous."
```

---

### Task 2: Bound `_find_tip`

**Files:**
- Modify: `mcp_harness/shaping.py:28-29` (add the constant), `mcp_harness/shaping.py:109-128` (`_find_tip`)
- Test: `mcp_harness/tests/test_shaping.py`

**Interfaces:**
- Produces: `shaping.TIP_BIND_MAX = 0.05`; `_find_tip` raises `ShapingError` when the nearest qualifying tip is farther than that. Signature and return `(tip_vertex_index, axial_edge_index)` are unchanged.

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_shaping.py`:

```python
def test_find_tip_refuses_beyond_the_bind_bound():
    # (99, 99) is nowhere near the unit square; today this binds anyway.
    with pytest.raises(shaping.ShapingError) as exc:
        shaping._find_tip(TIP_SQUARE, (99.0, 99.0))
    msg = str(exc.value)
    assert "0.05" in msg, msg          # the bound is named
    assert "13" in msg or "138" in msg, msg   # the distance found is reported


def test_find_tip_still_binds_just_inside_the_bound():
    # 0.04 away from the tip at (1.0, 0.5): inside TIP_BIND_MAX.
    tip, axial = shaping._find_tip(TIP_SQUARE, (1.0 - 0.04, 0.5))
    assert tip == 2
    assert TIP_SQUARE["edges_vertices"][axial] == [2, 5]


def test_find_tip_refuses_just_outside_the_bound():
    # 0.06 away: outside TIP_BIND_MAX.
    with pytest.raises(shaping.ShapingError):
        shaping._find_tip(TIP_SQUARE, (1.0 - 0.06, 0.5))


def test_bound_refusal_leaves_the_fold_untouched_through_the_display_hook():
    # apply_display_op catches every ShapingError and returns the INPUT.
    out = shaping.apply_display_op(TIP_SQUARE, "reverse:99,99:0.2:90")
    assert out is TIP_SQUARE
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_shaping.py -k "bind_bound or bind or untouched" -v --timeout=420`
Expected: `test_find_tip_refuses_beyond_the_bind_bound` FAILS with `DID NOT RAISE`, `test_find_tip_refuses_just_outside_the_bound` FAILS with `DID NOT RAISE`. The other two PASS already.

- [ ] **Step 3: Add the constant**

In `mcp_harness/shaping.py`, after line 29 (`SNAP = 1e-7 ...`), add:

```python
# Refuse to bind a tip-local op to a flap tip farther than this from the
# requested point. PINNED -- derived in
# docs/superpowers/specs/2026-08-09-shaping-composition-design.md section 6
# as below half the minimum served-tip spacing on 6 of 7 goldens. It catches
# requests for tips complete_square removed; it does NOT resolve wrong-flap
# ambiguity on a dense pattern (hf-dog-nudged tips are 0.020479 apart).
TIP_BIND_MAX = 0.05   # paper units
```

- [ ] **Step 4: Bound the search**

Replace `mcp_harness/shaping.py:126-128` (the tail of `_find_tip`):

```python
    if best is None:
        raise ShapingError("no flap-tip vertex (B + exactly one crease)")
    return best[1], best[2]
```

with:

```python
    if best is None:
        raise ShapingError("no flap-tip vertex (B + exactly one crease)")
    if best[0] > TIP_BIND_MAX:
        raise ShapingError(
            f"no flap tip within {TIP_BIND_MAX} of "
            f"({tip_xy[0]}, {tip_xy[1]}): nearest qualifying tip is "
            f"{best[0]:.6f} away")
    return best[1], best[2]
```

Also extend the docstring's first line so the refusal is documented at the call site — replace `"""Nearest flap-tip vertex: >=1 B edge, exactly ONE M/V crease (the` with:

```python
    """Nearest flap-tip vertex within TIP_BIND_MAX: >=1 B edge, exactly ONE
    M/V crease (the
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_shaping.py -k "bind_bound or bind or untouched" -v --timeout=420`
Expected: 4 passed.

- [ ] **Step 6: Verify no existing shaping test regressed**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_shaping.py tests/test_shaping_deep.py tests/test_shaping_tool.py tests/test_shaping_fixture.py -v --timeout=420`
Expected: all pass. Measured bind distances at every existing call site are 0.028284 (`TIP_SQUARE`), 0.000000 (`pent2` at `(5,1)` — that fixture's paper is 5×2 and `(5,1)` is an exact tip), so none is near the bound.

**If any test fails here, do not raise `TIP_BIND_MAX`.** Report which call site binds far and at what distance — that is a finding about the call site.

- [ ] **Step 7: Commit**

```bash
git add mcp_harness/shaping.py mcp_harness/tests/test_shaping.py
git commit -m "fix(shaping): bound _find_tip -- an op can no longer grab any flap at any distance

_find_tip computed dist and returned only the vertex. A probe at (99,99)
bound a tip 138.61 away and reported success. TIP_BIND_MAX = 0.05 paper
units, derived: below half the minimum served-tip spacing on 6 of 7 goldens.

Measured, this matters in production: server.py's _ref_xy binds at 0.000000
on dog (its intended subject) but 0.468013 on quad -- half a sheet away."
```

---

### Task 3: `_split_edges` propagates fold angles

**Files:**
- Modify: `mcp_harness/shaping.py:205-223` (`_split_edges`)
- Test: `mcp_harness/tests/test_shaping.py`

**Interfaces:**
- Produces: `_split_edges(vc, ev, ea, requests, fa=None)`. When `fa` is a list, every appended fragment gets `fa[ei]` appended alongside `ea[ei]`, keeping `len(fa) == len(ea)`. When `fa` is `None`, behaviour is exactly as before. Consumed by Tasks 4 and 5.

- [ ] **Step 1: Write the failing test**

Append to `mcp_harness/tests/test_shaping.py`:

```python
def test_split_edges_propagates_fold_angles_to_every_fragment():
    # One edge 0->1 at a partial angle, split at two interior points.
    vc = [[0.0, 0.0], [1.0, 0.0]]
    ev = [[0, 1]]
    ea = ["V"]
    fa = [37.5]
    shaping._split_edges(vc, ev, ea, {0: [(0.25, 0.0), (0.75, 0.0)]}, fa)
    assert len(ev) == 3, ev
    assert len(fa) == len(ea) == 3
    # Every fragment -- including the one that REUSED index 0 -- carries 37.5.
    assert fa == [37.5, 37.5, 37.5]
    assert ea == ["V", "V", "V"]


def test_split_edges_without_fold_angles_is_unchanged():
    vc = [[0.0, 0.0], [1.0, 0.0]]
    ev = [[0, 1]]
    ea = ["M"]
    out = shaping._split_edges(vc, ev, ea, {0: [(0.5, 0.0)]})
    assert len(ev) == 2 and ea == ["M", "M"]
    assert out[shaping._key((0.5, 0.0))] == 2
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_shaping.py -k split_edges -v --timeout=420`
Expected: `test_split_edges_propagates_fold_angles_to_every_fragment` FAILS with `TypeError: _split_edges() takes 4 positional arguments but 5 were given`.

- [ ] **Step 3: Add the parameter**

Replace `mcp_harness/shaping.py:205-223` entirely:

```python
def _split_edges(vc, ev, ea, requests, fa=None):
    """requests: {edge_index: [pt, ...]}. Split each edge at its points
    (any count/order; every fragment keeps the edge's assignment, and its
    fold angle when `fa` is supplied).
    Returns {_key(pt): new_vertex_index}.

    Edge identity: the FIRST fragment reuses the original index and the
    rest are appended, so unsplit edges never move. That is what lets the
    angle array be propagated by index rather than by a remap -- see the
    persistent-naming row in the design doc's prior-art table.
    """
    new_by_pt = {}
    for ei, pts in requests.items():
        a0 = ev[ei][0]
        ax, ay = vc[a0]
        prev, seg = a0, ei
        for p in sorted(pts, key=lambda p: (p[0] - ax) ** 2 + (p[1] - ay) ** 2):
            vc.append([p[0], p[1]])
            nv = len(vc) - 1
            new_by_pt[_key(p)] = nv
            end = ev[seg][1]
            ev[seg] = [prev, nv]
            ev.append([nv, end])
            ea.append(ea[ei])
            if fa is not None:
                fa.append(fa[ei])
            prev, seg = nv, len(ev) - 1
    return new_by_pt
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_shaping.py -k split_edges -v --timeout=420`
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/shaping.py mcp_harness/tests/test_shaping.py
git commit -m "feat(shaping): _split_edges propagates fold angles like it already does assignments

One line beside ea.append(ea[ei]). Optional param, so callers that do not
pass fa are byte-identical."
```

---

### Task 4: `shaping.py` composes fold angles

**Files:**
- Modify: `mcp_harness/shaping.py` — add `_angle_default` and `_seed_fold_angles` near `_key` (after line 132); `reverse_fold` body (lines ~276-317)
- Test: `mcp_harness/tests/test_shaping.py`

**Interfaces:**
- Consumes: `_split_edges(..., fa)` from Task 3.
- Produces: `_angle_default(kind: str) -> float` and `_seed_fold_angles(fold: dict, ea: list) -> list`. `reverse_fold`'s signature and return type are unchanged. Consumed by Task 5.

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_shaping.py`:

```python
def test_seed_uses_incoming_angles_when_the_length_matches():
    fold = dict(TIP_SQUARE, edges_foldAngle=[0, 0, 0, 0, 0, 42.0])
    assert shaping._seed_fold_angles(fold, TIP_SQUARE["edges_assignment"])[5] \
        == 42.0


def test_seed_discards_a_length_mismatched_array_whole():
    # square_complete grows edges_assignment WITHOUT growing edges_foldAngle,
    # so a short array is normal. Padding would misattribute angles to edges.
    fold = dict(TIP_SQUARE, edges_foldAngle=[42.0, 42.0])
    seeded = shaping._seed_fold_angles(fold, TIP_SQUARE["edges_assignment"])
    assert seeded == [0.0, 0.0, 0.0, 0.0, 0.0, 180.0]


def test_seed_replaces_null_entries_with_the_assignment_default():
    fold = dict(TIP_SQUARE, edges_foldAngle=[None] * 6)
    seeded = shaping._seed_fold_angles(fold, TIP_SQUARE["edges_assignment"])
    assert seeded == [0.0, 0.0, 0.0, 0.0, 0.0, 180.0]


def test_a_second_op_preserves_the_first_ops_partial_angles():
    """THE HEADLINE TEST. Two ops at DIFFERENT sites: every edge op1 set to a
    partial angle must still carry it after op2 runs."""
    square = {
        "vertices_coords": [[0, 0], [1, 0], [1, 0.5], [1, 1], [0, 1],
                            [0.5, 0.5], [0, 0.5], [0.5, 0.5]],
        "edges_vertices": [[0, 1], [1, 2], [2, 3], [3, 4], [4, 6], [6, 0],
                           [2, 5], [6, 7]],
        "edges_assignment": ["B", "B", "B", "B", "B", "B", "V", "V"],
    }
    one = shaping.apply_display_ops(square, ["reverse:1.0,0.5:0.2:90"])
    assert one is not square, "op1 was refused; fix the fixture, not the test"
    partial_after_one = {i: a for i, a in enumerate(one["edges_foldAngle"])
                         if a not in (0.0, 180.0, -180.0)}
    assert partial_after_one, "op1 set no partial angle"

    two = shaping.apply_display_ops(square, ["reverse:1.0,0.5:0.2:90",
                                             "reverse:0.0,0.5:0.2:90"])
    assert two is not one, "op2 was refused; fix the fixture, not the test"
    for i, angle in partial_after_one.items():
        assert two["edges_foldAngle"][i] == angle, (
            f"op2 reset edge {i}: op1 set {angle}, "
            f"after op2 it reads {two['edges_foldAngle'][i]}")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_shaping.py -k "seed or preserves_the_first" -v --timeout=420`
Expected: the three `seed` tests FAIL with `AttributeError: module 'shaping' has no attribute '_seed_fold_angles'`; `test_a_second_op_preserves_the_first_ops_partial_angles` FAILS with `op2 reset edge 11: op1 set 90.0, after op2 it reads 180.0` — **that failure message is the defect**.

**Verified against pristine code 2026-08-09**, this exact fixture reproduces: op1 sets partial angles on edges **11 and 12 (both 90.0°)**, and op2 resets **2 of 2** to 180.0° — total drift **180.0°**, both moves toward *more* fold. (The spec's 5-of-5 / 225.0° figures are a different measurement, taken on `dog.fold` with the arc's incumbent recipe. Do not expect those numbers here.)

- [ ] **Step 3: Add the seed helpers**

In `mcp_harness/shaping.py`, immediately after `_key` (line 132), add:

```python
def _angle_default(kind: str) -> float:
    """The FOLD default fold angle for an assignment: positive = valley,
    negative = mountain, 0 = flat/unassigned/border (FOLD spec)."""
    return {"M": -180.0, "V": 180.0}.get(kind, 0.0)


def _seed_fold_angles(fold: dict, ea: list) -> list:
    """The op's working fold-angle array.

    Uses the incoming edges_foldAngle when present AND the same length as
    the assignments; otherwise derives the FOLD default from assignments.

    A length-mismatched array is DISCARDED WHOLE, never padded:
    square_complete (square_complete.py:104) shallow-copies the fold and
    grows edges_assignment without growing edges_foldAngle, so a short
    array is its normal output and its entries cannot be trusted to line
    up with the edges they would be assigned to.
    """
    incoming = fold.get("edges_foldAngle")
    if isinstance(incoming, list) and len(incoming) == len(ea):
        return [_angle_default(k) if a is None else float(a)
                for a, k in zip(incoming, ea)]
    return [_angle_default(k) for k in ea]
```

- [ ] **Step 4: Seed and thread the array in `reverse_fold`**

In `mcp_harness/shaping.py`, replace the three-line copy block (currently lines 277-279):

```python
    vc = [list(p[:2]) for p in vc0]
    ev = [list(e) for e in ev0]
    ea = list(ea0)
```

with:

```python
    vc = [list(p[:2]) for p in vc0]
    ev = [list(e) for e in ev0]
    ea = list(ea0)
    fa = _seed_fold_angles(fold, ea0)
    # Captured BEFORE the split. Both fragments of the axial crease inherit
    # this, so the body side keeps whatever angle a previous op left there
    # instead of being slammed back to a full fold.
    axial_angle = fa[axial]
```

- [ ] **Step 5: Pass the array to the splitter and to the wedge arms**

Replace `new_by_pt = _split_edges(vc, ev, ea, requests)` with:

```python
    new_by_pt = _split_edges(vc, ev, ea, requests, fa)
```

Replace `overrides[body_seg] = s * 180.0` with:

```python
    overrides[body_seg] = axial_angle
```

In the wedge-arm loop, replace:

```python
        for x, y in zip(chain, chain[1:]):
            ev.append([x, y])
            ea.append(assign(wedge_angle))
            overrides[len(ev) - 1] = wedge_angle
```

with:

```python
        for x, y in zip(chain, chain[1:]):
            ev.append([x, y])
            ea.append(assign(wedge_angle))
            fa.append(wedge_angle)
            overrides[len(ev) - 1] = wedge_angle
```

- [ ] **Step 6: Build the output from the working array**

Replace the output construction (currently lines 313-316):

```python
    out["edges_foldAngle"] = [
        overrides.get(i, {"M": -180.0, "V": 180.0}.get(k, 0.0))
        for i, k in enumerate(ea)
    ]
```

with:

```python
    out["edges_foldAngle"] = [overrides.get(i, fa[i]) for i in range(len(ea))]
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_shaping.py -v --timeout=420`
Expected: all pass, including the four new ones and every pre-existing test in the file.

- [ ] **Step 8: Commit**

```bash
git add mcp_harness/shaping.py mcp_harness/tests/test_shaping.py
git commit -m "fix(shaping): ops COMPOSE -- seed edges_foldAngle instead of rebuilding it

reverse_fold rebuilt the whole array from edges_assignment plus its OWN
overrides, so every earlier op's partial angle was reset to full +/-180.
The implemented operator was op_N o flatten(everything prior).

body_seg now inherits the axial crease's incoming angle rather than s*180.
Provably identical when that crease carries its default (s is +1 exactly
when the axial is V, and the V default is +180), so single ops are
unaffected; it only differs when an earlier op left a partial angle."
```

---

### Task 5: `shaping_deep.py` composes fold angles

**Files:**
- Modify: `mcp_harness/shaping_deep.py:20-21` (import), `:314` (split call), `:319-324` (chord edges), `:405-408` (extension edges), `:417-420` (output)
- Test: `mcp_harness/tests/test_shaping_deep.py`

**Interfaces:**
- Consumes: `_split_edges(..., fa)` from Task 3; `_seed_fold_angles` from Task 4.
- Produces: no new names. `reverse_deep`'s signature and return type are unchanged.

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_shaping_deep.py`:

```python
def test_deep_op_preserves_an_incoming_partial_angle_on_an_untouched_edge():
    """A deep op must not reset an angle it did not set."""
    raw = pent2_fold()
    sq = _squared(raw, 5.0, 2.0)
    seeded = dict(sq)
    fa = [180.0 if k == "V" else (-180.0 if k == "M" else 0.0)
          for k in sq["edges_assignment"]]
    # Mark a BORDER edge: no op targets it, so it must survive verbatim.
    border = next(i for i, k in enumerate(sq["edges_assignment"]) if k == "B")
    fa[border] = 12.5
    seeded["edges_foldAngle"] = fa

    out = shaping.apply_display_ops(seeded, ["reverse_deep:5,1:1.5:180"],
                                    raw=raw)
    assert out is not seeded, "the deep op was refused"
    assert out["edges_foldAngle"][border] == 12.5


def test_deep_output_angle_array_matches_the_edge_count():
    raw = pent2_fold()
    sq = _squared(raw, 5.0, 2.0)
    out = shaping.apply_display_ops(sq, ["reverse_deep:5,1:1.5:180"], raw=raw)
    assert len(out["edges_foldAngle"]) == len(out["edges_vertices"])


def test_deep_op_after_a_tip_local_op_is_still_refused():
    """LOAD-BEARING for shaping_deep.py:334, which derives old_angle from the
    NOMINAL +/-180 rather than the incoming array. That is only correct
    because a deep op always runs first. If this guard is ever relaxed,
    line 334 must be revisited -- see the design doc, section 5."""
    raw = pent2_fold()
    sq = _squared(raw, 5.0, 2.0)
    both = shaping.apply_display_ops(
        sq, ["reverse:5,1:0.5:120", "reverse_deep:5,1:1.5:180"], raw=raw)
    tip_only = shaping.apply_display_ops(sq, ["reverse:5,1:0.5:120"])
    assert json.dumps(both, sort_keys=True) == \
        json.dumps(tip_only, sort_keys=True)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_shaping_deep.py -k "preserves_an_incoming or matches_the_edge_count or still_refused" -v --timeout=420`
Expected: `test_deep_op_preserves_an_incoming_partial_angle_on_an_untouched_edge` FAILS (`assert 0.0 == 12.5`). The other two PASS already — they pin behaviour that must not regress.

- [ ] **Step 3: Import the seed helper**

In `mcp_harness/shaping_deep.py`, replace the import block at lines 20-21:

```python
from shaping import (EPS, SNAP, ShapingError, _find_tip, _key, _march_arm,
                     _rot, _split_edges)
```

with:

```python
from shaping import (EPS, SNAP, ShapingError, _find_tip, _key, _march_arm,
                     _rot, _seed_fold_angles, _split_edges)
```

- [ ] **Step 4: Seed and thread the array**

Replace the split call (currently line 314):

```python
    new_by_pt = _split_edges(vc, ev, ea, split_requests)
```

with:

```python
    fa = _seed_fold_angles(squared_fold, ea)
    new_by_pt = _split_edges(vc, ev, ea, split_requests, fa)
```

In the chord-edge loop, replace:

```python
        ev.append([v1, v2])
        ea.append(wedge_kind)
        overrides[len(ev) - 1] = wedge_angle
```

with:

```python
        ev.append([v1, v2])
        ea.append(wedge_kind)
        fa.append(wedge_angle)
        overrides[len(ev) - 1] = wedge_angle
```

In the corner-extension loop, replace:

```python
        for x, y in zip(chain, chain[1:]):
            ev.append([x, y])
            ea.append(wedge_kind)
            overrides[len(ev) - 1] = wedge_angle
```

with:

```python
        for x, y in zip(chain, chain[1:]):
            ev.append([x, y])
            ea.append(wedge_kind)
            fa.append(wedge_angle)
            overrides[len(ev) - 1] = wedge_angle
```

**Note:** the carried-crease loop only reassigns `ea[frag]` and sets `overrides[frag]`; it never appends, so it needs no `fa` change. `overrides` already covers those edges.

- [ ] **Step 5: Build the output from the working array**

Replace the output construction (currently lines 417-420):

```python
    out["edges_foldAngle"] = [
        overrides.get(i, {"M": -180.0, "V": 180.0}.get(k, 0.0))
        for i, k in enumerate(ea)
    ]
```

with:

```python
    out["edges_foldAngle"] = [overrides.get(i, fa[i]) for i in range(len(ea))]
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_shaping_deep.py -v --timeout=420`
Expected: all pass, including the three new ones.

- [ ] **Step 7: Commit**

```bash
git add mcp_harness/shaping_deep.py mcp_harness/tests/test_shaping_deep.py
git commit -m "fix(shaping_deep): same composition fix on the deep path

shaping_deep.py:334 derives old_angle from the nominal +/-180, which is the
same 'ignore the incoming state' shape -- but it is CORRECT because
apply_display_ops refuses a deep op after any tip-local op, so a deep op
always runs first. Left unchanged; the ordering guard now has a test that
fails if it is relaxed."
```

---

### Task 6: The byte-identity STOP gate and the full suite

**Files:**
- Create: `mcp_harness/tests/test_shaping_composition_gate.py`
- Test: itself

**Interfaces:**
- Consumes: `fixtures/shaping_single_op_baseline.json` from Task 1; the fixed `shaping.apply_display_ops` from Tasks 2-5.

- [ ] **Step 1: Write the gate**

Create `mcp_harness/tests/test_shaping_composition_gate.py`:

```python
"""The safety gate for the composition fix.

Almost every measurement in the shaping arc came from SINGLE ops. If this
fix moved those numbers, every past result becomes incomparable to every
future one. The design argues the change is a no-op for single ops
(docs/superpowers/specs/2026-08-09-shaping-composition-design.md section 5);
this VERIFIES it rather than assuming it.

A difference here is a STOP, not a re-baseline. Regenerating
fixtures/shaping_single_op_baseline.json to make this pass would delete the
only evidence that the fix is safe.
"""
import json
import os

import pytest

import shaping
import square_complete

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE = os.path.join(HERE, "fixtures", "shaping_single_op_baseline.json")


def _baseline():
    with open(BASELINE) as fh:
        return json.load(fh)


def test_the_baseline_fixture_is_present_and_non_trivial():
    b = _baseline()
    assert len(b) >= 8, f"baseline has only {len(b)} entries"


@pytest.mark.parametrize("key", sorted(_baseline()))
def test_single_op_output_is_byte_identical_to_the_pre_fix_baseline(key):
    golden, op = key.split("::", 1)
    raw = json.load(open(os.path.join(HERE, "tests", "goldens",
                                      f"{golden}.fold")))
    sq = square_complete.complete_square(raw, 1.0, 1.0)
    out = shaping.apply_display_ops(sq, [op])
    assert out is not sq, f"{key}: the op is now REFUSED but was applied before"
    assert json.dumps(out, sort_keys=True) == \
        json.dumps(_baseline()[key], sort_keys=True), (
            f"{key}: single-op output CHANGED. This is a STOP -- the fix was "
            f"supposed to be a no-op for single ops. Do NOT regenerate the "
            f"baseline; report which field moved.")


def test_composition_is_not_a_flatten_of_everything_prior():
    """The claim in one line: op2 does not reset op1."""
    square = {
        "vertices_coords": [[0, 0], [1, 0], [1, 0.5], [1, 1], [0, 1],
                            [0.5, 0.5], [0, 0.5], [0.5, 0.5]],
        "edges_vertices": [[0, 1], [1, 2], [2, 3], [3, 4], [4, 6], [6, 0],
                           [2, 5], [6, 7]],
        "edges_assignment": ["B", "B", "B", "B", "B", "B", "V", "V"],
    }
    one = shaping.apply_display_ops(square, ["reverse:1.0,0.5:0.2:90"])
    two = shaping.apply_display_ops(square, ["reverse:1.0,0.5:0.2:90",
                                             "reverse:0.0,0.5:0.2:90"])
    assert one is not square and two is not one
    reset = [i for i, a in enumerate(one["edges_foldAngle"])
             if a not in (0.0, 180.0, -180.0)
             and two["edges_foldAngle"][i] != a]
    assert not reset, f"op2 reset {len(reset)} of op1's partial angles: {reset}"
```

- [ ] **Step 2: Run the gate**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_shaping_composition_gate.py -v --timeout=420`
Expected: all pass.

**If `test_single_op_output_is_byte_identical_to_the_pre_fix_baseline` fails: STOP.** Do not regenerate the baseline. Report which key failed and diff the two folds field by field — the likely culprits are `_seed_fold_angles` returning something other than the old default for some assignment, or `axial_angle` differing from `s * 180.0` because the input carried a non-default angle on the axial crease.

- [ ] **Step 3: Run the full suite**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest --timeout=420 2>&1 | tail -25`
Expected: `2422 passed, 11 skipped` or higher, plus the new tests. **No previously-green test may turn red.**

If `test_auto_selection_is_deterministic` fails, re-run it alone before believing it:
`cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_mesh_auto.py -k test_auto_selection_is_deterministic -v --timeout=420`

- [ ] **Step 4: Record the measured composition defect**

Create `docs/superpowers/evidence/2026-08-09-shaping-composition-outcome.md` with: the reset count and total drift that Task 4 Step 2 reported **before** the fix; the byte-identity result for every baseline key; the full-suite counts before and after; and the measured bind-distance table from the spec's §6, noting that `server.py`'s `_ref_xy` binds at 0.000000 on `dog` and 0.468013 on `quad`.

State plainly what this does **not** establish: nothing about whether composed ops produce better models, and nothing about whether the B5-prime anti-additivity finding was an artifact. That needs the Gate-2 re-run and its own pre-registration.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/tests/test_shaping_composition_gate.py docs/superpowers/evidence/2026-08-09-shaping-composition-outcome.md
git commit -m "gate(shaping): single-op byte-identity, and the composition claim in one test

The load-bearing safety property: this fix must move NO single-op number,
because that is where every measurement in the arc came from. A difference
is a STOP, not a re-baseline."
```

---

## Self-Review

**1. Spec coverage.** §3's four edit sites → Tasks 2 (`_find_tip`), 3 (`_split_edges`), 4 (`shaping.py`), 5 (`shaping_deep.py`). §4 seeding and the discard-not-pad rule → Task 4 Steps 1/3. §5 `body_seg` → Task 4 Step 5. §5's `shaping_deep` ordering subsection → Task 5 Step 1's third test. §6 bound + derivation → Task 2. §7 error handling → Task 2 Step 1's display-hook test and Task 4's mismatch tests. §9's headline test → Task 4 Step 1 and Task 6 Step 1. §9's load-bearing byte-identity test → Tasks 1 and 6. §10 risk 1 (index stability) → Task 3's test asserts *which* fragment carries the angle, not merely the length. §8 non-goals are respected: no Gate-2 re-run, no `square_complete` fix, no tip-set change, no new primitive.

**2. Placeholder scan.** No TBD/TODO. Every code step carries complete code; every run step carries an exact command and expected output.

**3. Type consistency.** `_seed_fold_angles(fold, ea) -> list` is defined in Task 4 Step 3 and imported by name in Task 5 Step 3. `_split_edges(vc, ev, ea, requests, fa=None)` is defined in Task 3 and called with five positional args in Tasks 4 and 5. `_angle_default(kind) -> float` is used only inside `_seed_fold_angles`. `TIP_BIND_MAX` is defined in Task 2 and referenced in Task 2's tests only. `fa` is a `list[float]` throughout and stays the same length as `ea` at every append site.

**One ordering constraint, called out because it is easy to get wrong:** Task 1 **must** run before Tasks 2-5. Its fixture is the pre-change baseline; generated afterwards it proves nothing.
