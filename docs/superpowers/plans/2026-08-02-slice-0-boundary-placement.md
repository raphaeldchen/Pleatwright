# Slice 0 — Boundary Placement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Determine whether constraining leaf nodes to the paper boundary rescues the 6-row cohort residual that every existing rescue stage fails on — and if so, ship it as a rescue-ladder rung.

**Architecture:** Three phases with a hard go/no-go between each. **Phase 0 is pure Python and needs no C++ at all**: the existing placement stage already carries `x`/`y` seeds to the engine, and it explicitly *clamps them off the boundary* (`rescue_ladder.py:188`). Lifting that clamp is a one-function experiment that answers the slice's central question for an afternoon's work. Only if seeds are insufficient does Phase 1 bind Lang's v5 `tmConditionNodeCombo` to *hold* nodes at the boundary through the solve. Phase 2 ships the rung.

**Tech Stack:** Python 3.14 (`mcp_harness/.venv`), pybind11 + C++17 (vendored TreeMaker), pytest.

## Global Constraints

- **Build and measure from the MAIN checkout** (`<repo>`), never a worktree. A worktree borrowing main's `.so` reports 27 baseline failures instead of ~3.
- **Run pytest with `--timeout=420`.** Bare `make test` never terminates on macOS.
- **Check host CPU for orphaned processes before timing anything.** A stale orphan once ran a gate 6× slow and manufactured timeout failures.
- **Attempt-0 output must stay byte-identical** for all four templates, at every phase.
- **Never freeze a byte hash over engine output.** Roundoff-bearing artifacts cannot be green on both macOS and Linux.
- **Never loosen a test pin to make something pass.** Re-bless deliberately, in the task that moved the rows.
- The full suite's expected shape is **4 failures / 2124 passed / 11 skipped**; it looks hung at ~0% CPU early and finishes in ~23 min.

**The target population — memorise these six ids:**

| id | nodes | leaves | root children | interior | shape |
|---|---|---|---|---|---|
| 90 | 10 | 8 | 5 | 1 | branched |
| **353** | 9 | **8** | **8** | 0 | **pure star** |
| **500** | 9 | **8** | **8** | 0 | **pure star** |
| 830 | 13 | 8 | 3 | 4 | branched |
| 865 | 10 | 6 | 3 | 3 | branched |
| **2099** | 9 | **8** | **8** | 0 | **pure star** |

Source: `mcp_harness/fixtures/rescue_cohort.json` → `residual_ids_s5b`; trees in `mcp_harness/feasibility/corpus_wide.jsonl` keyed by `id`. Five of six have exactly 8 leaves; three are pure 8-point stars. Lang's manual §3.3 fig. 3.3.7 is an 8-point base with all flaps forced to edges — valid, at scale 0.250. **That is the precedent this slice is testing.**

---

## Phase 0 — The go/no-go (pure Python, no C++)

### Task 1: Boundary layout and the residual measurement

**Files:**
- Modify: `mcp_harness/rescue_ladder.py` (add `boundary_layout` beside `structural_layout:445`)
- Test: `mcp_harness/tests/test_boundary_layout.py` (create)
- Create: `mcp_harness/probe_boundary_seeds.py`

**Interfaces:**
- Consumes: `rescue_ladder.root_id:321`, `_children:326`, `_well_formed:298`, `_dedupe_seeds`, `with_seeds:552`
- Produces: `boundary_layout(nodes, pairs, paper_w=1.0, paper_h=1.0) -> dict[int, tuple[float, float]]` — node id → seed position, root at centre, every leaf on the paper perimeter.

**Why this task exists.** `structural_layout` places the root at `(0.5, 0.5)` and grows outward, then `_clamp` pins every seed into `[_SEED_MIN, _SEED_MAX] = [0.05, 0.95]` under a comment reading *"keep seeds off the paper boundary"* (`rescue_ladder.py:188`). Boundary positions have therefore never been tried on any cohort row — not as constraints, and not even as starting points. This task tries them.

**The hazard to respect.** `_dedupe_seeds` exists because **two coincident seeds SIGSEGV the engine (exit -11)**, and `_worker_compile_and_regions` runs the whole ladder in one child, so a crash there takes every remaining rung with it. Distributing 8 leaves around a perimeter makes coincidence *more* likely than the centre-outward layout does. `boundary_layout` must return distinct positions by construction and still pass through `_dedupe_seeds`.

- [ ] **Step 1: Write the failing test**

```python
# mcp_harness/tests/test_boundary_layout.py
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
import rescue_ladder  # noqa: E402


def _star(k):
    """A k-point star: k leaves hanging directly off the root."""
    return ([{"id": 0, "parent_id": None, "length": 0}]
            + [{"id": i, "parent_id": 0, "length": 0.1 * i}
               for i in range(1, k + 1)])


def _on_perimeter(xy, w=1.0, h=1.0, tol=1e-9):
    x, y = xy
    return (abs(x) < tol or abs(x - w) < tol
            or abs(y) < tol or abs(y - h) < tol)


def test_every_leaf_lands_on_the_perimeter():
    nodes = _star(8)
    pos = rescue_ladder.boundary_layout(nodes, [])
    assert set(pos) == {n["id"] for n in nodes}
    for nid, xy in pos.items():
        if nid == 0:
            assert xy == (0.5, 0.5)          # root stays at centre
        else:
            assert _on_perimeter(xy), f"node {nid} at {xy} is not on the edge"


def test_no_two_seeds_coincide():
    # Coincident seeds SIGSEGV the engine (exit -11) -- rescue_ladder._dedupe_seeds
    for k in (3, 4, 5, 8, 12):
        pos = rescue_ladder.boundary_layout(_star(k), [])
        assert len(set(pos.values())) == len(pos), f"k={k} produced duplicates"


def test_bilateral_pairs_are_mirrored_about_the_diagonal():
    # The engine's symmetry axis is the 45-degree diagonal y=x through the
    # paper centre (TreemakerWrapper.cpp:311-313), so a pair (a, b) must
    # satisfy b == (a.y, a.x).
    nodes = _star(4)
    pos = rescue_ladder.boundary_layout(nodes, [(1, 2)])
    ax, ay = pos[1]
    bx, by = pos[2]
    assert abs(bx - ay) < 1e-9 and abs(by - ax) < 1e-9


def test_malformed_input_returns_empty():
    assert rescue_ladder.boundary_layout([], []) == {}
    assert rescue_ladder.boundary_layout(
        [{"id": 1, "parent_id": 99, "length": 1.0}], []) == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd <repo>/mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_boundary_layout.py -v --timeout=420`
Expected: FAIL, `AttributeError: module 'rescue_ladder' has no attribute 'boundary_layout'`

- [ ] **Step 3: Write minimal implementation**

Add to `mcp_harness/rescue_ladder.py`, directly after `structural_layout` (which ends at the `return _dedupe_seeds(pos)` around line 491):

```python
def boundary_layout(nodes, pairs, paper_w: float = 1.0,
                    paper_h: float = 1.0) -> dict:
    """{node_id: (x, y)} -- root at the paper centre, every LEAF on the paper
    perimeter, bilateral pairs mirrored about the 45-degree diagonal.

    WHY THIS EXISTS, AND WHY IT IS NOT structural_layout WITH A BIGGER SCALE.
    `_SEED_MIN, _SEED_MAX = 0.05, 0.95` clamps every structural seed OFF the
    boundary by design. So boundary starting positions have never been tried on
    a cohort row -- not as constraints, not even as seeds. The S5b residual is
    [90, 353, 500, 830, 865, 2099]: five have exactly 8 leaves and three
    (353, 500, 2099) are pure 8-point stars. Lang's TreeMaker 4.0 manual
    section 3.3 figure 3.3.7 shows an 8-point base with every flap forced to an
    edge -- VALID, at scale 0.250 -- while our unconstrained solve fails on
    this class roughly two thirds of the time. This function tests whether the
    basin is reachable from a boundary START, before any engine work is done.

    DISTINCTNESS IS LOAD-BEARING. Two coincident seeds SIGSEGV the engine
    (exit -11, see _dedupe_seeds), and a perimeter is a 1-D walk where
    collisions are easier than in the interior. Leaves are placed at distinct
    arc-length offsets by construction, and the result still goes through
    _dedupe_seeds.
    """
    if not _well_formed(nodes):
        return {}
    r = root_id(nodes)
    if r is None:
        return {}
    ch = _children(nodes)
    leaves = [n["id"] for n in nodes if not ch.get(n["id"]) and n["id"] != r]
    if not leaves:
        return {}

    perim = 2.0 * (paper_w + paper_h)

    def at(t: float):
        """Walk the perimeter anticlockwise from (0, 0); t in [0, perim)."""
        t %= perim
        if t < paper_w:
            return (t, 0.0)
        t -= paper_w
        if t < paper_h:
            return (paper_w, t)
        t -= paper_h
        if t < paper_w:
            return (paper_w - t, paper_h)
        t -= paper_w
        return (0.0, paper_h - t)

    def mirror(xy):
        """Reflect about y = x, the engine's symmetry axis."""
        return (xy[1], xy[0])

    pos = {r: (0.5 * paper_w, 0.5 * paper_h)}
    paired = {}
    for pair in pairs or []:
        if len(pair) == 2 and pair[0] in leaves and pair[1] in leaves:
            paired[pair[0]] = pair[1]
            paired[pair[1]] = pair[0]

    # Deterministic order: paired leaves first (lower id leads), then unpaired,
    # each group by id. Node LIST order must never decide placement -- see
    # canonical_order's input-order dependence, which cost a session.
    leads = sorted({min(a, b) for a, b in paired.items()})
    unpaired = sorted(n for n in leaves if n not in paired)

    step = perim / float(len(leaves) + 1)
    t = 0.0
    for lead in leads:
        t += step
        p = at(t)
        pos[lead] = p
        pos[paired[lead]] = mirror(p)
        t += step
    for nid in unpaired:
        t += step
        pos[nid] = at(t)

    # Interior (non-root, non-leaf) nodes keep the structural placement so a
    # branched tree is not left with unseeded nodes -- has_placement_seed fires
    # on ANY x/y key, and a partially seeded list is exactly what
    # placement_variants refuses to emit.
    missing = [n["id"] for n in nodes if n["id"] not in pos]
    if missing:
        fallback = structural_layout(nodes, pairs)
        if not fallback:
            return {}
        for nid in missing:
            if nid not in fallback:
                return {}
            pos[nid] = fallback[nid]

    return _dedupe_seeds(pos)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd <repo>/mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_boundary_layout.py -v --timeout=420`
Expected: PASS, 4 passed

- [ ] **Step 5: Confirm nothing else moved**

Run: `cd <repo>/mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_rescue_ladder.py tests/test_perturb_ladder.py tests/test_perturb_symmetry.py tests/test_normalizer.py -q --timeout=420`
Expected: PASS. `boundary_layout` is additive and no existing caller references it yet.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/rescue_ladder.py mcp_harness/tests/test_boundary_layout.py
git commit -m "feat(ladder): boundary_layout -- perimeter seeds, mirrored pairs

The existing structural_layout clamps every seed off the boundary
(_SEED_MIN/_SEED_MAX = 0.05/0.95, 'keep seeds off the paper boundary'), so
boundary starting positions have never been tried on a cohort row. Additive
only -- no caller yet."
```

- [ ] **Step 7: Write the residual probe**

```python
# mcp_harness/probe_boundary_seeds.py
"""Phase 0 go/no-go: do boundary SEEDS pack the S5b cohort residual?

Answers the slice's central question with zero C++ work. If seeds alone
rescue rows, the engine binding may be unnecessary; if they do not, the case
for a CONSTRAINT (which holds a node at the boundary through the solve rather
than merely starting it there) is what Phase 1 tests.

Run from the MAIN checkout:
  cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python probe_boundary_seeds.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rescue_ladder                      # noqa: E402
import structural_search                  # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
COHORT = os.path.join(_HERE, "fixtures", "rescue_cohort.json")
CORPUS = os.path.join(_HERE, "feasibility", "corpus_wide.jsonl")


def load_rows(ids):
    want, out = set(ids), {}
    with open(CORPUS) as fh:
        for line in fh:
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("id") in want:
                out[r["id"]] = r
    return out


def nodes_of(row):
    for key in ("nodes", "tree_nodes", "tree"):
        v = row.get(key)
        if isinstance(v, list):
            return v
        if isinstance(v, dict) and isinstance(v.get("nodes"), list):
            return v["nodes"]
    raise KeyError(f"row {row.get('id')} has no node list")


def compiles(nodes, pairs):
    """True iff the engine packs this node list. Isolated per row: a
    degenerate placement can SIGSEGV, and one crash must not end the sweep."""
    import subprocess
    payload = json.dumps({"nodes": nodes, "pairs": pairs})
    proc = subprocess.run(
        [sys.executable, "-c",
         "import sys, json, structural_search;"
         "d=json.loads(sys.stdin.read());"
         "print(structural_search.compiles(d['nodes'], d['pairs']))"],
        input=payload, capture_output=True, text=True, cwd=_HERE, timeout=300,
        env={**os.environ, "PYTHONPATH": _HERE})
    return proc.stdout.strip().endswith("True"), proc.returncode


def main():
    with open(COHORT) as fh:
        cohort = json.load(fh)
    ids = cohort["residual_ids_s5b"]
    rows = load_rows(ids)
    print(f"residual: {ids}\nloaded  : {sorted(rows)}\n")

    results = {}
    for rid in ids:
        nodes = nodes_of(rows[rid])
        pairs = rows[rid].get("pairs") or []
        pos = rescue_ladder.boundary_layout(nodes, pairs)
        if not pos:
            results[rid] = "NO_LAYOUT"
            print(f"{rid:5d}  NO_LAYOUT (boundary_layout returned empty)")
            continue
        seeded = rescue_ladder.with_seeds(nodes, pos)
        ok, rc = compiles(seeded, pairs)
        results[rid] = "PACK" if ok else (f"CRASH rc={rc}" if rc else "FAIL")
        print(f"{rid:5d}  leaves={sum(1 for n in nodes if n.get('parent_id') "
              f"is not None and not any(m.get('parent_id') == n['id'] "
              f"for m in nodes)):2d}  {results[rid]}")

    packed = sum(1 for v in results.values() if v == "PACK")
    print(f"\nBOUNDARY SEEDS RESCUE {packed}/{len(ids)} of the S5b residual")
    print("\nGO/NO-GO:")
    print("  >=1 PACK  -> boundary positions reach a valid basin. Phase 1 asks")
    print("              whether a CONSTRAINT beats a SEED; it is no longer")
    print("              asking whether the direction works at all.")
    print("  0 PACK    -> seeds are insufficient. Phase 1 tests whether HOLDING")
    print("              a node at the boundary through the solve differs from")
    print("              starting it there. If Phase 1 also fails, STOP.")
    print("  any CRASH -> _dedupe_seeds did not save us; fix distinctness")
    print("              BEFORE reading any other result.")
    out = os.path.join(_HERE, "..", "tmp", "boundary_seed_probe.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as fh:
        json.dump({"ids": ids, "results": results, "packed": packed}, fh,
                  indent=2)
    print(f"\nwritten: {os.path.abspath(out)}")


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 8: Confirm the probe's engine entry point exists**

Run: `cd <repo>/mcp_harness && PYTHONPATH=.:tests .venv/bin/python -c "import structural_search; print(structural_search.compiles)"`
Expected: a bound function. **If `compiles` does not exist under that name**, find the real one — `grep -n "def compiles\|def _compiles\|def try_compile" structural_search.py server.py rescue_ladder.py` — and substitute it in both places in `probe_boundary_seeds.py` before running. Do not proceed on a guess.

- [ ] **Step 9: Run the probe**

Run: `cd <repo>/mcp_harness && PYTHONPATH=.:tests .venv/bin/python probe_boundary_seeds.py`
Expected: a `PACK`/`FAIL`/`CRASH` verdict per id and a rescue count out of 6.

- [ ] **Step 10: Commit the probe and its result**

```bash
git add mcp_harness/probe_boundary_seeds.py tmp/boundary_seed_probe.json
git commit -m "probe(slice-0): boundary seeds vs the S5b cohort residual

Phase 0 go/no-go. Records the measured result whichever way it falls."
```

> ### GO/NO-GO GATE 1 — read before Phase 1
>
> | Probe result | What it means | Do this |
> |---|---|---|
> | ≥1 `PACK` | Boundary positions reach a valid basin without any constraint | Phase 1 is now a *narrower* question: does a constraint beat a seed? Consider shipping the seed variant as a `placement` sub-variant first — far cheaper than the whole slice |
> | 0 `PACK` | Seeds are insufficient | Proceed to Phase 1. It tests the genuinely different thing: *holding* a node at the boundary through the solve |
> | any `CRASH` | Seed distinctness failed | Fix `boundary_layout` before reading anything else |
>
> **If Phase 0 shows 0 PACK and Phase 1 Task 2 also shows no pack on any residual row, STOP AND REPORT.** The slice is falsified and the finding is worth more than the code. That is the spec's pre-registered stopping rule (§5 Phase A) and it is binding.

---

## Phase 1 — The engine binding

### Task 2: Bind `tmConditionNodeCombo`

**Files:**
- Modify: `mcp_harness/TreemakerWrapper.cpp` (methods beside `set_edge_strain_fixed:326`; `.def` exports beside `apply_symmetry`'s at `:1270`)
- Test: `mcp_harness/tests/test_boundary_binding.py` (create)

**Interfaces:**
- Consumes: `tmTree::GetOrMakeOnePartCondition<tmConditionNodeCombo, tmNode>`, `tmTreeCleaner`, `mNodeMap`, `mStubApplied`
- Produces, on the pybind11 module:
  - `set_node_at(node_id: int, x: float, y: float) -> None`
  - `set_node_on_x(node_id: int, x: float) -> None`
  - `set_node_on_y(node_id: int, y: float) -> None`
  - `get_boundary_conditions() -> dict[int, dict]` — `{node_id: {"x": float|None, "y": float|None}}`

**Why Combo and not `tmConditionNodeOnEdge`/`OnCorner`.** The v4 pair cannot name *which* edge or corner: `CornerFn::Func` is `u[ix]*(u[ix]-w)` (`tmConstraintFns.cpp:1657-1661`), so five nodes all at `(0,0)` satisfy all ten equalities. Combo's `XFixed`/`YFixed` name an exact coordinate **and** emit `AddLinearEquality(new OneVarFn(...))` where the v4 route emits a quartic `AddNonlinearEquality`. Linear equalities are far better conditioned for the ALM backend we build (CFSQP, which Lang tuned against, is absent). Combo is verified compiled (36 symbols in the shipped `.so`), tagged `"CNxn"`, and registered at `tmPart.h:334`.

- [ ] **Step 1: Write the failing test**

```python
# mcp_harness/tests/test_boundary_binding.py
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
import headless_treemaker as tm  # noqa: E402


def _star_engine(k=4):
    e = tm.TreemakerWrapper()
    e.build_tree_from_json(
        [{"id": 0, "parent_id": None, "length": 0}]
        + [{"id": i, "parent_id": 0, "length": 0.3} for i in range(1, k + 1)])
    return e


def test_set_node_at_reads_back_both_coordinates():
    e = _star_engine()
    e.set_node_at(1, 0.0, 1.0)
    got = e.get_boundary_conditions()
    assert got[1]["x"] == pytest.approx(0.0)
    assert got[1]["y"] == pytest.approx(1.0)


def test_set_node_on_x_leaves_y_free():
    e = _star_engine()
    e.set_node_on_x(2, 1.0)
    got = e.get_boundary_conditions()
    assert got[2]["x"] == pytest.approx(1.0)
    assert got[2]["y"] is None


def test_reapplying_is_idempotent():
    # GetOrMakeOnePartCondition returns the SAME condition, so the second call
    # must overwrite rather than stack a duplicate.
    e = _star_engine()
    e.set_node_at(1, 0.0, 0.0)
    e.set_node_at(1, 1.0, 1.0)
    got = e.get_boundary_conditions()
    assert len(got) == 1
    assert got[1]["x"] == pytest.approx(1.0)


def test_unknown_node_raises():
    e = _star_engine()
    with pytest.raises(RuntimeError, match="unknown node id"):
        e.set_node_at(99, 0.0, 0.0)


def test_non_leaf_raises():
    # A boundary condition on a non-leaf is a SILENT no-op in the engine
    # (IsValidCondition false -> GetBaseOffset BAD_OFFSET -> AddConstraints
    # adds nothing). Rejecting loudly is what turns that silence into a signal.
    e = tm.TreemakerWrapper()
    e.build_tree_from_json([
        {"id": 0, "parent_id": None, "length": 0},
        {"id": 1, "parent_id": 0, "length": 0.3},
        {"id": 2, "parent_id": 1, "length": 0.3},
        {"id": 3, "parent_id": 1, "length": 0.3},
    ])
    with pytest.raises(RuntimeError, match="not a leaf"):
        e.set_node_at(1, 0.0, 0.0)


def test_no_conditions_reads_back_empty():
    assert _star_engine().get_boundary_conditions() == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd <repo>/mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_boundary_binding.py -v --timeout=420`
Expected: FAIL, `AttributeError: 'TreemakerWrapper' object has no attribute 'set_node_at'`

- [ ] **Step 3: Write the implementation**

Add to `mcp_harness/TreemakerWrapper.cpp`, immediately after `set_edge_strain_fixed` (which ends around line 345):

```cpp
  /*
   * Constrain a leaf node's POSITION via tmConditionNodeCombo (Lang's v5
   * condition, driven by his own tmTree::SetNodesFixedToPaperEdge at
   * tmTree.cpp:1506). The v4 tmConditionNodeOnEdge/OnCorner pair it
   * supersedes cannot name WHICH edge or corner -- CornerFn is
   * u[ix]*(u[ix]-w), so five nodes at (0,0) satisfy all ten equalities -- and
   * emits a quartic where XFixed/YFixed emit a linear equality (OneVarFn),
   * which matters because we build with ALM and not the CFSQP backend Lang
   * tuned these against.
   *
   * This does NOT raise the design scale. tmScaleOptimizer already bounds
   * every leaf coordinate to the paper rectangle (tmScaleOptimizer.cpp:49-61)
   * and maximises scale with no coverage term (:180), so added equalities can
   * only shrink the feasible set. The lever is which BASIN the non-convex ALM
   * solve lands in -- and, for the 8-point stars in our cohort residual,
   * trading scale for polygon-network VALIDITY (Lang's manual section 3.3
   * figure 3.3.7: an 8-point all-edge base, valid, scale 0.250).
   *
   * Position only; edge lengths are untouched, which is why the boundary rung
   * is proportion-PRESERVING.
   */
  tmNode* BoundaryTarget(int node_id, const char* who) {
    if (mStubApplied) {
      // NOT because node ids go stale -- they do not (see the run_stub_repair
      // contract block, "AddStub never deletes a node"). Because
      // AddStubToTree -> CleanupAfterEdit recomputes leafness from edge degree
      // (tmTree.cpp:1009), so a planned leaf may now be a branch node, at
      // which point IsValidCondition() is false and the constraint is dropped
      // SILENTLY.
      throw std::runtime_error(
          std::string(who) + ": refused after a structural stub repair "
          "(leafness may have changed; re-plan against the repaired tree)");
    }
    auto it = mNodeMap.find(node_id);
    if (it == mNodeMap.end())
      throw std::runtime_error(std::string(who) + ": unknown node id");
    if (!it->second->IsLeafNode())
      throw std::runtime_error(
          std::string(who) + ": node is not a leaf; a boundary condition on a "
          "non-leaf is a silent no-op in the engine");
    return it->second;
  }

  void set_node_at(int node_id, double x, double y) {
    tmNode* n = BoundaryTarget(node_id, "set_node_at");
    tmTreeCleaner tc(mTree);
    tmConditionNodeCombo* c =
        mTree->GetOrMakeOnePartCondition<tmConditionNodeCombo, tmNode>(n);
    c->SetXFixed(true);  c->SetXFixValue(x);
    c->SetYFixed(true);  c->SetYFixValue(y);
  }

  void set_node_on_x(int node_id, double x) {
    tmNode* n = BoundaryTarget(node_id, "set_node_on_x");
    tmTreeCleaner tc(mTree);
    tmConditionNodeCombo* c =
        mTree->GetOrMakeOnePartCondition<tmConditionNodeCombo, tmNode>(n);
    c->SetXFixed(true);  c->SetXFixValue(x);
  }

  void set_node_on_y(int node_id, double y) {
    tmNode* n = BoundaryTarget(node_id, "set_node_on_y");
    tmTreeCleaner tc(mTree);
    tmConditionNodeCombo* c =
        mTree->GetOrMakeOnePartCondition<tmConditionNodeCombo, tmNode>(n);
    c->SetYFixed(true);  c->SetYFixValue(y);
  }

  /*
   * Read back what is actually set on the tree, so the ladder can assert what
   * it applied instead of trusting its own bookkeeping. Combo already carries
   * the getters; this is a thin wrapper, not new state.
   */
  py::dict get_boundary_conditions() {
    py::dict out;
    for (const auto& kv : mNodeMap) {
      tmConditionNodeCombo* c =
          mTree->GetOnePartCondition<tmConditionNodeCombo, tmNode>(kv.second);
      if (!c) continue;
      if (!c->GetXFixed() && !c->GetYFixed()) continue;
      py::dict entry;
      entry["x"] = c->GetXFixed() ? py::cast(c->GetXFixValue()) : py::none();
      entry["y"] = c->GetYFixed() ? py::cast(c->GetYFixValue()) : py::none();
      out[py::int_(kv.first)] = entry;
    }
    return out;
  }
```

Then add the exports beside `apply_symmetry`'s `.def` around line 1270:

```cpp
      .def("set_node_at", &TreemakerWrapper::set_node_at)
      .def("set_node_on_x", &TreemakerWrapper::set_node_on_x)
      .def("set_node_on_y", &TreemakerWrapper::set_node_on_y)
      .def("get_boundary_conditions", &TreemakerWrapper::get_boundary_conditions)
```

- [ ] **Step 4: Confirm the read-back accessor exists before building**

Run: `cd <repo> && grep -n "GetOnePartCondition\|GetOrMakeOnePartCondition" mcp_harness/treemaker/Source/tmModel/tmTreeClasses/tmTree.h`
Expected: both templates listed. **If only `GetOrMakeOnePartCondition` exists**, `get_boundary_conditions` must not use the Get-only form — it would create conditions as a side effect of reading. Instead iterate the tree's owned conditions and `dynamic_cast<tmConditionNodeCombo*>`, following whatever enumeration `tmTree` exposes. Do not call `GetOrMake` from a getter.

- [ ] **Step 5: Build**

Run: `cd <repo> && make build 2>&1 | tail -20`
Expected: a rebuilt `mcp_harness/headless_treemaker.cpython-314-darwin.so`. If `make build` is not a target, use `mcp_harness/build.sh` — the real build path is `Makefile:12-14` → `build.sh:16,39`. (`mcp_harness/CMakeLists.txt` points `TM_SRC` at a repo-root `treemaker/` that does not exist and cannot configure; ignore it.)

- [ ] **Step 6: Run test to verify it passes**

Run: `cd <repo>/mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_boundary_binding.py -v --timeout=420`
Expected: PASS, 6 passed

- [ ] **Step 7: Commit**

```bash
git add mcp_harness/TreemakerWrapper.cpp mcp_harness/tests/test_boundary_binding.py
git commit -m "feat(engine): bind tmConditionNodeCombo for boundary placement

Lang's v5 condition, not the v4 tmConditionNodeOnEdge/OnCorner pair: the v4
classes cannot name which edge or corner (CornerFn is u[ix]*(u[ix]-w), so
five nodes at (0,0) satisfy all ten equalities) and emit a quartic where
XFixed/YFixed emit a linear equality.

Rejects non-leaf nodes loudly because the engine's own behaviour there is a
SILENT no-op (IsValidCondition false -> GetBaseOffset BAD_OFFSET)."
```

### Task 3: Does the constraint survive the compile?

**Files:**
- Test: `mcp_harness/tests/test_boundary_geometry.py` (create)
- Modify: `mcp_harness/TreemakerWrapper.cpp` — `ProjectActivePaths` (`:1005`), **only if this task's test fails**

**Interfaces:**
- Consumes: Task 2's `set_node_at`, plus the existing `leaf_node_locations` read-back
- Produces: nothing new on success. On failure, boundary rows inside `ProjectActivePaths`' least-squares system.

**Why this task is separate from Task 2.** Task 2 proves the condition is *recorded*. That is bookkeeping. `ProjectActivePaths()` runs on the normal compile path at `TreemakerWrapper.cpp:1155`, after ALM converges and before the molecule build, and it **moves leaf coordinates via `SetLoc`** to tighten active-path equalities from ALM's ~1e-6 floor to ~1e-13. Its constraint set is active-path rows plus symmetry rows and **nothing else**. A node ALM placed exactly at `(0,1)` can be moved off it. A test that asserts only "the condition exists" passes green on a base whose corner flap is not at the corner.

- [ ] **Step 1: Write the failing test**

```python
# mcp_harness/tests/test_boundary_geometry.py
"""The condition must hold through the WHOLE compile, not just be recorded.

ProjectActivePaths (TreemakerWrapper.cpp:1155) runs after ALM and moves leaf
coords with only active-path and symmetry rows in its system -- no boundary
row. This is the test that catches that.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
import headless_treemaker as tm  # noqa: E402

TOL = 1e-9


def test_constrained_node_is_still_on_the_boundary_after_compile():
    e = tm.TreemakerWrapper()
    e.build_tree_from_json(
        [{"id": 0, "parent_id": None, "length": 0}]
        + [{"id": i, "parent_id": 0, "length": 0.3} for i in range(1, 5)])
    e.set_node_at(1, 0.0, 0.0)
    e.set_node_on_x(2, 1.0)
    assert e.run_scale_optimization(), "4-star must pack; fix the fixture first"

    locs = e.leaf_node_locations()
    x1, y1 = locs[1]
    assert abs(x1 - 0.0) < TOL, f"node 1 x drifted to {x1}"
    assert abs(y1 - 0.0) < TOL, f"node 1 y drifted to {y1}"
    x2, _ = locs[2]
    assert abs(x2 - 1.0) < TOL, f"node 2 x drifted to {x2}"
```

- [ ] **Step 2: Run the test**

Run: `cd <repo>/mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_boundary_geometry.py -v --timeout=420`
Expected: **unknown — this is a measurement, not a prediction.** Record the actual drift magnitude from the assertion message.

**If it PASSES:** the projection leaves constrained nodes alone at this size. Record that, skip Step 3, go to Step 4.
**If it FAILS:** note the drift, do Step 3.

**Confirm the read-back's name before running:** `grep -n "leaf_node_locations\|def leaf_node" mcp_harness/TreemakerWrapper.cpp`. It is referenced in the `run_stub_repair` contract block at `:429-431`. If it returns a list rather than a dict, index it accordingly rather than guessing.

- [ ] **Step 3: Add boundary rows to the projection (only if Step 2 failed)**

In `ProjectActivePaths` (`TreemakerWrapper.cpp:1005`), beside the symmetry rows built from `mSymPairs` (around `:1048-1053`), add fixed-coordinate rows. They are linear, exactly like the symmetry rows, and drop into the same least-squares system:

```cpp
    // Boundary rows: a node carrying an XFixed/YFixed Combo condition must
    // stay where ALM put it. Without these the projection tightens active
    // paths by ~1e-5 and silently walks a corner flap off its corner --
    // the same class of drift the symmetry rows above exist to prevent
    // ("free projection would drift it asymmetric").
    struct FixCon { std::size_t slot; double value; };
    std::vector<FixCon> fixes;
    for (const auto& kv : mNodeMap) {
      tmConditionNodeCombo* c =
          mTree->GetOnePartCondition<tmConditionNodeCombo, tmNode>(kv.second);
      if (!c) continue;
      auto ii = idx.find(kv.second);
      if (ii == idx.end()) continue;              // not a leaf in this system
      if (c->GetXFixed()) fixes.push_back({2 * ii->second,     c->GetXFixValue()});
      if (c->GetYFixed()) fixes.push_back({2 * ii->second + 1, c->GetYFixValue()});
    }
    if (outCons) *outCons += fixes.size();
```

Then, inside the Gauss-Newton iteration where the symmetry rows contribute to `A` and `g`, add one row per fix: residual `x[slot] - value`, with a single unit entry in the Jacobian at `slot`. Follow the symmetry rows' exact accumulation pattern — do not invent a different weighting.

- [ ] **Step 4: Rebuild and re-run**

Run: `cd <repo> && make build 2>&1 | tail -5 && cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_boundary_geometry.py tests/test_boundary_binding.py -v --timeout=420`
Expected: PASS

- [ ] **Step 5: Confirm the projection still does its original job**

Run: `cd <repo>/mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/ -q --timeout=420 -k "kawasaki or audit or molecule or golden"`
Expected: no new failures. The projection exists to make interior-vertex Kawasaki angles exact; adding rows must not regress that.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/TreemakerWrapper.cpp mcp_harness/tests/test_boundary_geometry.py
git commit -m "test(engine): assert boundary conditions survive the full compile

ProjectActivePaths moves leaf coords after ALM with only active-path and
symmetry rows in its system. Asserting the condition OBJECT exists is
bookkeeping; this asserts the COORDINATES."
```

### Task 4: Probe the residual with real constraints

**Files:**
- Modify: `mcp_harness/probe_boundary_seeds.py` → add a constrained arm

**Interfaces:**
- Consumes: Task 1's `boundary_layout`, Task 2's `set_node_at`/`set_node_on_x`/`set_node_on_y`

- [ ] **Step 1: Add the constrained arm**

Extend `probe_boundary_seeds.py` with a third arm per row, alongside the existing seed arm:

```python
def compiles_constrained(nodes, pairs, plan):
    """Apply `plan` as real Combo CONSTRAINTS, then pack. Isolated per row."""
    import subprocess
    payload = json.dumps({"nodes": nodes, "pairs": pairs,
                          "plan": {str(k): v for k, v in plan.items()}})
    script = (
        "import sys, json, headless_treemaker as tm;"
        "d=json.loads(sys.stdin.read());"
        "e=tm.TreemakerWrapper();"
        "e.build_tree_from_json(d['nodes']);"
        "[e.apply_symmetry(a,b) for a,b in d['pairs']];"
        "[ (e.set_node_at(int(k),v[0],v[1]) if v[0] is not None and v[1] is not None"
        "   else e.set_node_on_x(int(k),v[0]) if v[0] is not None"
        "   else e.set_node_on_y(int(k),v[1])) for k,v in d['plan'].items() ];"
        "print(e.run_scale_optimization())")
    proc = subprocess.run([sys.executable, "-c", script], input=payload,
                          capture_output=True, text=True, cwd=_HERE,
                          timeout=300,
                          env={**os.environ, "PYTHONPATH": _HERE})
    return proc.stdout.strip().endswith("True"), proc.returncode, proc.stderr[-300:]
```

For each residual row, derive the plan from `boundary_layout` by turning each leaf's `(x, y)` into a corner (`set_node_at`) when both coordinates are extreme, and an edge (`set_node_on_x`/`_on_y`) otherwise. Report **three** columns per row: seed-only, constrained, and the `design_scale` for whichever arm packs.

- [ ] **Step 2: Add R12's control arm**

The spec's R12 records that Lang's documented remedy for many-sided polygons — our exact failure class — is to drag a node into the polygon's **centre**, i.e. create a middle flap, the opposite of boundary placement. Add a fourth column: the same rows seeded with **one leaf at the paper centre** and the rest structural. This costs almost nothing and directly tests the alternative hypothesis.

- [ ] **Step 3: Run all four arms**

Run: `cd <repo>/mcp_harness && PYTHONPATH=.:tests .venv/bin/python probe_boundary_seeds.py`
Expected: a 6×4 table — id × {seed, constrained, centre-control, scale}.

- [ ] **Step 4: Commit the measurement**

```bash
git add mcp_harness/probe_boundary_seeds.py tmp/boundary_seed_probe.json
git commit -m "probe(slice-0): seed vs constraint vs centre-control on the residual"
```

> ### GO/NO-GO GATE 2 — the slice's verdict
>
> | Outcome | Verdict |
> |---|---|
> | Constrained arm packs rows the seed arm does not | **GO.** Proceed to Phase 2. The constraint is doing work a seed cannot |
> | Seed arm packs everything the constrained arm does | **RESCOPE.** Ship a boundary variant of the existing `placement` stage. Skip Phase 2's engine plumbing entirely — the six coordinated edits are still needed, but no side channel is |
> | Neither packs anything, centre-control packs | **STOP AND PIVOT.** Lang was right and boundary placement is the wrong lever. Report; propose a middle-flap rung instead |
> | Nothing packs at all | **STOP.** Record the negative. This is the spec's pre-registered stopping rule |
> | ALM diverges (non-convergence, not just failure) | **STOP.** Risk R1 fired |

---

## Phase 2 — The rung

**Only enter Phase 2 on a GO or RESCOPE verdict from Gate 2.**

### Task 5: The placement policy

**Files:**
- Create: `mcp_harness/boundary_placement.py`
- Test: `mcp_harness/tests/test_boundary_plan.py` (create)

**Interfaces:**
- Produces: `boundary_plan(nodes, pairs, paper_w=1.0, paper_h=1.0, *, max_corners=4) -> dict[int, tuple[float | None, float | None]]` — node id → `(x, y)`, where `None` leaves that coordinate free. `(0.0, None)` is the left edge; `(0.0, 1.0)` is a corner.

**The mirror-class rule, which is the only real algorithm here.** The engine's symmetry axis is the 45° diagonal through the paper centre (`TreemakerWrapper.cpp:311-313`: `SetSymmetry(tmPoint(0.5*W, 0.5*H), 45.0)`). Under reflection about `y = x`: `(0,0)` and `(w,h)` are **self-mirror**; `(w,0)` and `(0,h)` **swap**. Therefore the off-diagonal corners are assignable to at most **one** bilateral pair, both members or neither; the on-diagonal corners are assignable **only to unpaired leaves**; and a pair may never take one corner and one edge. A second bilateral pair cannot take corners at all — there are only two off-diagonal corners — and must fall back to mirrored edge positions.

- [ ] **Step 1: Write the failing test**

```python
# mcp_harness/tests/test_boundary_plan.py
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
import boundary_placement  # noqa: E402

CORNERS = {(0.0, 0.0), (1.0, 1.0), (1.0, 0.0), (0.0, 1.0)}
ON_DIAG = {(0.0, 0.0), (1.0, 1.0)}
OFF_DIAG = {(1.0, 0.0), (0.0, 1.0)}


def _tree(lengths):
    return ([{"id": 0, "parent_id": None, "length": 0}]
            + [{"id": i + 1, "parent_id": 0, "length": L}
               for i, L in enumerate(lengths)])


def test_root_is_never_constrained():
    plan = boundary_placement.boundary_plan(_tree([0.4, 0.3, 0.2]), [])
    assert 0 not in plan


def test_longest_flaps_are_placed_first():
    # Ranked by length descending; the longest leaf must get a corner (the
    # cheapest slot) before any shorter one does.
    plan = boundary_placement.boundary_plan(_tree([0.1, 0.5, 0.3]), [])
    assert plan[2] in CORNERS, "the 0.5 flap should hold a corner"


def test_equal_lengths_break_ties_by_node_id_deterministically():
    # Node LIST order must never decide placement. Same multiset, reversed
    # list -> identical plan.
    nodes = _tree([0.3, 0.3, 0.3, 0.3])
    forward = boundary_placement.boundary_plan(nodes, [])
    backward = boundary_placement.boundary_plan(
        [nodes[0]] + list(reversed(nodes[1:])), [])
    assert forward == backward


def test_a_pair_takes_both_off_diagonal_corners_or_neither():
    plan = boundary_placement.boundary_plan(_tree([0.5, 0.5, 0.2]), [(1, 2)])
    a, b = plan[1], plan[2]
    if a in CORNERS or b in CORNERS:
        assert {a, b} == OFF_DIAG, f"pair split across {a}, {b}"


def test_one_pair_plus_two_unpaired_may_use_all_four_corners():
    # The configuration revision 1's "<=2 corners when a pair is placed" rule
    # wrongly forbade. All four are mirror-consistent.
    plan = boundary_placement.boundary_plan(
        _tree([0.5, 0.5, 0.45, 0.44]), [(1, 2)])
    used = {v for v in plan.values() if v in CORNERS}
    assert used == CORNERS, f"expected all four corners, got {used}"
    assert {plan[1], plan[2]} == OFF_DIAG
    assert {plan[3], plan[4]} == ON_DIAG


def test_a_second_pair_gets_edges_not_corners():
    plan = boundary_placement.boundary_plan(
        _tree([0.5, 0.5, 0.4, 0.4]), [(1, 2), (3, 4)])
    assert {plan[1], plan[2]} == OFF_DIAG
    assert plan[3] not in CORNERS and plan[4] not in CORNERS


def test_corner_budget_is_never_exceeded():
    plan = boundary_placement.boundary_plan(_tree([0.5] * 10), [])
    assert sum(1 for v in plan.values() if v in CORNERS) <= 4


def test_no_two_nodes_share_a_slot():
    plan = boundary_placement.boundary_plan(_tree([0.5] * 8), [])
    assert len(set(plan.values())) == len(plan)


def test_malformed_input_returns_empty():
    assert boundary_placement.boundary_plan([], []) == {}


def test_paired_slots_are_exact_mirrors_about_the_diagonal():
    """Spec section 6's test_boundary_symmetry, at the policy layer.

    Every paired leaf's slot must be its partner's reflection about y = x.
    This is an A/B against the mirror relation itself -- NOT against 0.026,
    which is dog.fold's MEASURED mismatch and must never become a tolerance.
    """
    for pairs in ([(1, 2)], [(1, 2), (3, 4)]):
        plan = boundary_placement.boundary_plan(_tree([0.5] * 6), pairs)
        for a, b in pairs:
            ax, ay = plan[a]
            bx, by = plan[b]
            assert (bx, by) == (ay, ax), f"pair ({a},{b}) not mirrored"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd <repo>/mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_boundary_plan.py -v --timeout=420`
Expected: FAIL, `ModuleNotFoundError: No module named 'boundary_placement'`

- [ ] **Step 3: Write the implementation**

```python
# mcp_harness/boundary_placement.py
"""Which leaf goes to which boundary slot.

Pure function, no engine import, unit-testable off-line. Emits COORDINATES,
not slot names, because only Lang's v5 tmConditionNodeCombo can express "this
corner" -- the v4 conditions this project first reached for constrain a node
to ANY corner (CornerFn is u[ix]*(u[ix]-w)), which leaves the mirror-class
reasoning below with nothing to act on.

THE MIRROR CLASSES ARE THE WHOLE ALGORITHM. The engine's symmetry axis is the
45-degree diagonal through the paper centre (TreemakerWrapper.cpp:311-313).
Reflecting about y = x:
    (0,0) and (w,h)  -> SELF-MIRROR  (on-diagonal)
    (w,0) and (0,h)  -> SWAP         (off-diagonal)
So a bilateral pair may take the two off-diagonal corners, both or neither;
the on-diagonal corners belong to unpaired leaves; and a SECOND pair cannot
take corners at all, because there are only two off-diagonal ones.

A split-placed pair would fight tmConditionNodesPaired directly. The project
has already shipped lopsided bases once from the analogous mistake in the
LENGTH domain (tests/test_perturb_symmetry.py:1-11), which is why this is a
partition rule and not a count cap.
"""
from __future__ import annotations


def _leaves(nodes):
    children = set()
    for n in nodes:
        if n.get("parent_id") is not None:
            children.add(n["parent_id"])
    root = next((n["id"] for n in nodes if n.get("parent_id") is None), None)
    return root, [n["id"] for n in nodes
                  if n["id"] not in children and n["id"] != root]


def boundary_plan(nodes, pairs, paper_w: float = 1.0, paper_h: float = 1.0,
                  *, max_corners: int = 4) -> dict:
    if not nodes:
        return {}
    root, leaves = _leaves(nodes)
    if root is None or not leaves:
        return {}
    length = {n["id"]: (n.get("length") or 0.0) for n in nodes}

    on_diag = [(0.0, 0.0), (paper_w, paper_h)]
    off_diag = [(paper_w, 0.0), (0.0, paper_h)]

    pair_of = {}
    for p in pairs or []:
        if len(p) == 2 and p[0] in leaves and p[1] in leaves:
            pair_of[p[0]], pair_of[p[1]] = p[1], p[0]

    # Rank by length descending; ties by node id ASCENDING so the caller's list
    # order can never decide placement.
    def rank(nid):
        return (-length.get(nid, 0.0), nid)

    pair_leads = sorted({min(a, b) for a, b in pair_of.items()}, key=rank)
    unpaired = sorted((n for n in leaves if n not in pair_of), key=rank)

    plan: dict = {}
    corners_used = 0

    # 1. The single strongest bilateral pair takes the off-diagonal corners.
    if pair_leads and corners_used + 2 <= max_corners:
        lead = pair_leads.pop(0)
        plan[lead] = off_diag[0]
        plan[pair_of[lead]] = off_diag[1]
        corners_used += 2

    # 2. Unpaired leaves take the on-diagonal (self-mirror) corners.
    for slot in on_diag:
        if not unpaired or corners_used >= max_corners:
            break
        plan[unpaired.pop(0)] = slot
        corners_used += 1

    # 3. Everyone else takes edges. Remaining pairs get MIRRORED edge slots so
    #    the pairing condition is satisfied by construction; unpaired leaves
    #    fill the rest. Offsets are distinct by construction -- two coincident
    #    positions SIGSEGV the engine (rescue_ladder._dedupe_seeds).
    step = 1.0 / float(len(leaves) + 2)
    t = step
    for lead in pair_leads:
        x = min(max(t, step), 1.0 - step) * paper_w
        plan[lead] = (x, 0.0)                     # bottom edge
        plan[pair_of[lead]] = (0.0, x)            # mirror: left edge
        t += step
    for nid in unpaired:
        y = min(max(t, step), 1.0 - step) * paper_h
        plan[nid] = (paper_w, y)                  # right edge
        t += step

    return plan
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd <repo>/mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_boundary_plan.py -v --timeout=420`
Expected: PASS, 9 passed

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/boundary_placement.py mcp_harness/tests/test_boundary_plan.py
git commit -m "feat(ladder): boundary_plan -- mirror-class corner partition

Emits coordinates, not slot names, because only Combo can express 'this
corner'. Corners partition by mirror class about the 45-degree axis rather
than being capped by count: one pair off-diagonal, unpaired leaves
on-diagonal, all four legal simultaneously."
```

### Task 6: The rung, and all six coordinated edits

**Files:**
- Modify: `mcp_harness/rescue_ladder.py` (`STAGE_BOUNDARY`, `BOUNDARY_MARKER` beside `ORDER_MARKER:153`, `PRESERVING_STAGES`, `STAGE_HONESTY`)
- Modify: `mcp_harness/server.py:593` (`_ALL_LADDER_STAGES`)
- Modify: `mcp_harness/mesh_to_tree.py:114` (`_STAGE_INTEGRITY`), `:724-748` (`served_stage`)
- Modify: `mcp_harness/benchmark_subjects.py:96-130` (stage chain)
- Modify: `mcp_harness/feasibility/tree_labeler.py:53` (`PERTURB_ERA_REVISION` 7 → 8)
- Test: `mcp_harness/tests/test_boundary_stage.py` (create)

**Interfaces:**
- Consumes: Task 5's `boundary_plan`
- Produces: `rescue_ladder.STAGE_BOUNDARY = "boundary"`, `rescue_ladder.BOUNDARY_MARKER = "[ide: rescued by boundary placement:"`

**This is six sites, not one, and two of them fail SILENTLY.** `mesh_to_tree.served_stage` falls through to `STAGE_EXACT` and `benchmark_subjects` falls through to `"none"` on an unrecognised marker. Ship the constant alone and a boundary rescue is scored as a clean attempt-0 exact serve, the extraction drain ends early, and **every test still passes**. `mesh_to_tree.py:733-735` says so in the source: *"a missing marker here is therefore a silent WRONG SERVE, not a red test."*

- [ ] **Step 1: Write the failing test**

```python
# mcp_harness/tests/test_boundary_stage.py
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
import benchmark_subjects  # noqa: E402
import mesh_to_tree        # noqa: E402
import rescue_ladder       # noqa: E402
import server              # noqa: E402


def test_stage_is_proportion_preserving_and_invents_nothing():
    assert rescue_ladder.STAGE_BOUNDARY in rescue_ladder.PRESERVING_STAGES
    assert rescue_ladder.STAGE_BOUNDARY not in rescue_ladder.INVENTS_ANATOMY
    assert rescue_ladder.STAGE_HONESTY[rescue_ladder.STAGE_BOUNDARY] == 2


def test_marker_satisfies_the_three_pinned_invariants():
    m = rescue_ladder.BOUNDARY_MARKER
    for other in (rescue_ladder.ORDER_MARKER, rescue_ladder.PLACEMENT_MARKER,
                  rescue_ladder.NORMALIZE_MARKER, rescue_ladder.STUB_MARKER):
        assert other not in m and m not in other
    # A boundary-rescued base HAS the requested proportions, so it must not
    # trip agent_loop's "tell the user the proportions differ" doctrine, which
    # is scoped to exactly this phrase.
    assert "did not pack exactly" not in m
    assert "ADDED ANATOMY" not in m


def test_both_marker_to_stage_chains_agree():
    """The two production derivations must not fall through.

    mesh_to_tree.served_stage falls through to STAGE_EXACT and
    benchmark_subjects falls through to "none". Either omission scores a
    boundary rescue as a byte-clean attempt-0 exact serve with nothing red.
    """
    fold = '{"frame_title": "x ' + rescue_ladder.BOUNDARY_MARKER + ' 2c/4e]"}'
    assert mesh_to_tree.served_stage(fold, nudged=False) == \
        rescue_ladder.STAGE_BOUNDARY
    assert benchmark_subjects.stage_from_fold(fold) == \
        rescue_ladder.STAGE_BOUNDARY


def test_stage_is_registered_everywhere_it_must_be():
    assert rescue_ladder.STAGE_BOUNDARY in server._ALL_LADDER_STAGES
    assert rescue_ladder.STAGE_BOUNDARY in mesh_to_tree._STAGE_INTEGRITY
    # _STAGE_INTEGRITY is pinned dict-equal to STAGE_HONESTY.
    assert mesh_to_tree._STAGE_INTEGRITY == dict(rescue_ladder.STAGE_HONESTY)


def test_era_revision_was_bumped():
    from feasibility import tree_labeler
    assert tree_labeler.PERTURB_ERA_REVISION >= 8, (
        "adding a stage changes every captured row's era string "
        "(tree_labeler.py:80-81); bump the revision")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd <repo>/mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_boundary_stage.py -v --timeout=420`
Expected: FAIL, `AttributeError: module 'rescue_ladder' has no attribute 'STAGE_BOUNDARY'`

**`benchmark_subjects.stage_from_fold` may not exist as a named function** — the chain at `:96-130` is currently inline in `build_row`. Extracting it into `stage_from_fold(fold_str, nudged=False, served=True)` is part of Step 3, and is the change that makes the fall-through testable at all.

- [ ] **Step 3: Make all six edits**

1. `rescue_ladder.py`, beside `ORDER_MARKER` at `:153`:
   ```python
   STAGE_BOUNDARY = "boundary"
   #: Slice 0. The same three invariants as the markers above. Says what MOVED
   #: (positions), never what appeared -- no anatomy is added, so STUB_MARKER's
   #: "backend ADDED ANATOMY" language must not be copied.
   BOUNDARY_MARKER = "[ide: rescued by boundary placement:"
   ```
   Add `STAGE_BOUNDARY` to `PRESERVING_STAGES` and `STAGE_HONESTY` with rank `2`, ordered after `placement` and before `normalize`.
2. `server.py:593`: add `rescue_ladder.STAGE_BOUNDARY` to `_ALL_LADDER_STAGES`.
3. `mesh_to_tree.py:114`: add `"boundary": 2` to `_STAGE_INTEGRITY`.
4. `mesh_to_tree.py:724-748`: add a `BOUNDARY_MARKER` branch **before** the `STAGE_EXACT` fall-through.
5. `benchmark_subjects.py:96-130`: extract the chain into `stage_from_fold(...)`, add a `boundary` branch before the `else: stage = "none"`, and call it from `build_row`.
6. `feasibility/tree_labeler.py:53`: `PERTURB_ERA_REVISION = 8`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd <repo>/mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_boundary_stage.py -v --timeout=420`
Expected: PASS, 5 passed

- [ ] **Step 5: Re-pin the four tests that enumerate stages**

Run: `cd <repo>/mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_rescue_ladder.py tests/test_perturb_ladder.py tests/test_normalizer.py tests/test_provenance.py -v --timeout=420`
Expected: failures in tests that enumerate the stage list or assert an era string. **Update each pin to include `boundary` deliberately.** Never loosen an assertion to make it pass — if a test asserted an exact set, it must still assert an exact set.

- [ ] **Step 6: Verify attempt-0 is byte-identical**

Run: `cd <repo>/mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/ -q --timeout=420 -k "attempt0 or golden or dog_ladder"`
Expected: PASS. The rung must not fire unless a plan is supplied.

- [ ] **Step 7: Commit**

```bash
git add mcp_harness/rescue_ladder.py mcp_harness/server.py mcp_harness/mesh_to_tree.py \
        mcp_harness/benchmark_subjects.py mcp_harness/feasibility/tree_labeler.py \
        mcp_harness/tests/
git commit -m "feat(ladder): STAGE_BOUNDARY across all six registries

Two of the six fail SILENTLY: mesh_to_tree.served_stage falls through to
STAGE_EXACT and benchmark_subjects to 'none', so shipping the marker alone
would score a boundary rescue as a byte-clean attempt-0 exact serve with
nothing red. test_both_marker_to_stage_chains_agree is the guard.

Extracts benchmark_subjects.stage_from_fold so the fall-through is testable."
```

### Task 7: Wire the rung to the serve path

**Files:**
- Modify: `mcp_harness/rescue_ladder.py` (`Rung`, `:217-223`)
- Modify: `mcp_harness/server.py` (`_perturb_ladder:819-823`, `_compile_with_perturb:1350`, `_worker_full_base:158`, `_worker_compile_recipe:197`, `_worker_compile_and_regions._try_once:301`)
- Test: `mcp_harness/tests/test_boundary_wiring.py` (create)

**Interfaces:**
- Consumes: Task 5's `boundary_plan`, Task 2's three setters
- Produces: `Rung.boundary` — `dict[int, tuple[float|None, float|None]] | None`, applied at the rung, never inside the node dicts that reach attempt-0.

**The failure this task's test exists to catch.** A worker path that accepts the new argument and forgets to call the engine binding still compiles, still packs, and still emits `BOUNDARY_MARKER` — serving an **unconstrained** base under a boundary label, which then scores as a rescue. Asserting "the argument arrived" does not catch it; asserting the engine was **called** does. The precedent is `server.py:1358-1367`: *"All 31 shipped call sites were widened at once; any missed one raises TypeError immediately."*

- [ ] **Step 1: Write the failing test**

```python
# mcp_harness/tests/test_boundary_wiring.py
"""Every worker path must CALL the binding, not merely accept the argument."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
import rescue_ladder  # noqa: E402
import server         # noqa: E402


class _SpyEngine:
    def __init__(self):
        self.calls = []

    def set_node_at(self, nid, x, y):
        self.calls.append(("at", nid, x, y))

    def set_node_on_x(self, nid, x):
        self.calls.append(("x", nid, x))

    def set_node_on_y(self, nid, y):
        self.calls.append(("y", nid, y))


def test_apply_boundary_dispatches_each_slot_kind():
    e = _SpyEngine()
    server._apply_boundary(e, {1: (0.0, 1.0), 2: (0.5, None), 3: (None, 0.5)})
    kinds = sorted(c[0] for c in e.calls)
    assert kinds == ["at", "x", "y"]


def test_apply_boundary_is_a_noop_for_an_empty_plan():
    e = _SpyEngine()
    server._apply_boundary(e, None)
    server._apply_boundary(e, {})
    assert e.calls == []


@pytest.mark.parametrize("worker", [
    "_worker_full_base", "_worker_compile_recipe",
    "_worker_compile_and_regions",
])
def test_every_worker_path_reaches_apply_boundary(worker):
    """Static guard: each worker body must reference _apply_boundary.

    A path that threads the argument through without applying it serves an
    UNCONSTRAINED base under BOUNDARY_MARKER and scores as a rescue.
    """
    import inspect
    src = inspect.getsource(getattr(server, worker))
    assert "_apply_boundary" in src, (
        f"{worker} accepts a boundary plan but never applies it")


def test_rung_carries_boundary_and_defaults_to_none():
    r = rescue_ladder.Rung(stage="boundary")
    assert r.boundary is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd <repo>/mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_boundary_wiring.py -v --timeout=420`
Expected: FAIL, `AttributeError: module 'server' has no attribute '_apply_boundary'`

**Confirm `Rung`'s real constructor signature first** — `sed -n '205,230p' mcp_harness/rescue_ladder.py`. If it is not a dataclass with keyword defaults, adapt the test's construction rather than changing `Rung`'s shape.

- [ ] **Step 3: Implement**

Add to `server.py`, beside the other rung helpers:

```python
def _apply_boundary(engine, plan) -> None:
    """Apply a boundary plan to a built tree, before scale optimization.

    Called from EVERY worker path. A path that threads the plan through
    without calling this serves an unconstrained base under BOUNDARY_MARKER
    and scores as a rescue -- see tests/test_boundary_wiring.py.
    """
    for nid, (x, y) in (plan or {}).items():
        if x is not None and y is not None:
            engine.set_node_at(int(nid), float(x), float(y))
        elif x is not None:
            engine.set_node_on_x(int(nid), float(x))
        elif y is not None:
            engine.set_node_on_y(int(nid), float(y))
```

Add a `boundary` field to `Rung` (appended, defaulting to `None`, exactly as `stubs` was added). Widen `attempt(nodes, stubs)` to `attempt(nodes, stubs, boundary)` and update **all** call sites at once — `grep -rn "stubs=0\|attempt(" mcp_harness/server.py mcp_harness/rescue_ladder.py` finds them. Call `_apply_boundary(engine, boundary)` in each worker body, **after** `apply_symmetry` and **before** `run_scale_optimization`.

Add the boundary rung generator to `_perturb_ladder:819-823`, ordered after `placement` and before `normalize`, with the ≤3 variant fan: the policy plan; the plan with corners demoted to edges (drop the second coordinate of each corner); longest-flap-only.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd <repo>/mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_boundary_wiring.py tests/test_boundary_stage.py -v --timeout=420`
Expected: PASS

- [ ] **Step 5: Verify attempt-0 is still byte-identical**

Run: `cd <repo>/mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/ -q --timeout=420 -k "attempt0 or golden or dog_ladder or perturb"`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/server.py mcp_harness/rescue_ladder.py mcp_harness/tests/test_boundary_wiring.py
git commit -m "feat(ladder): wire the boundary rung to all three worker paths

Side channel on Rung, never inside the node dicts that reach attempt-0.
The wiring test asserts each worker CALLS _apply_boundary -- a path that
accepts the plan and forgets to apply it would serve an unconstrained base
under BOUNDARY_MARKER and score as a rescue."
```

---

## Phase 3 — Measurement

### Task 8: Scorecard columns and the cohort re-measure

**Files:**
- Modify: `mcp_harness/benchmark_subjects.py` (`_COLS:247`)
- Modify: `mcp_harness/fixtures/scorecard_baseline.jsonl`, `mcp_harness/fixtures/rescue_cohort.json`
- Test: `mcp_harness/tests/test_boundary_scorecard.py` (create)

**Interfaces:**
- Produces: `boundary_nodes` (`"<n>c/<n>e"` or `None`) and `design_scale` (float or `None`) in every scorecard row.

**Read the corpus honestly before claiming a win.** The 6-subject scorecard has **no headroom**: all six serve, none is at `jitter` or `composed`, so the spec's secondary metric has zero candidates and the primary metric can only move a subject between two rank-2 preserving stages. **The real target is the 24-row cohort residual `[90, 353, 500, 830, 865, 2099]`.** Report both, and do not dress a scorecard no-op as a success.

**`design_scale` is a price tag, not a regression guard.** §1.1 proves boundary conditions cannot raise the global-optimum scale. We *expect* it to fall; the question is whether polygon-network validity is bought with it. Report the delta, do not gate on it being non-negative.

- [ ] **Step 1: Write the failing test**

```python
# mcp_harness/tests/test_boundary_scorecard.py
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
import benchmark_subjects  # noqa: E402


def test_new_columns_are_present_and_ordered_last():
    assert "boundary_nodes" in benchmark_subjects._COLS
    assert "design_scale" in benchmark_subjects._COLS


def test_columns_are_none_when_the_rung_did_not_serve():
    row = benchmark_subjects.build_row(
        "quadruped", ref=None, res=None,
        fold_str='{"frame_title": "plain"}', lint_text=None,
        attempt0_codes=[])
    assert row["boundary_nodes"] is None


def test_boundary_nodes_counts_corners_and_edges():
    assert benchmark_subjects.format_boundary_nodes(
        {1: (0.0, 0.0), 2: (1.0, 1.0), 3: (0.5, None)}) == "2c/1e"
    assert benchmark_subjects.format_boundary_nodes({}) is None
    assert benchmark_subjects.format_boundary_nodes(None) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd <repo>/mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_boundary_scorecard.py -v --timeout=420`
Expected: FAIL, `AssertionError` on the `_COLS` membership.

**Check `build_row`'s real signature first** — `grep -n "def build_row" mcp_harness/benchmark_subjects.py` — and match the test's call to it rather than assuming.

- [ ] **Step 3: Implement**

```python
def format_boundary_nodes(plan):
    """'<corners>c/<edges>e', or None when the rung did not serve."""
    if not plan:
        return None
    corners = sum(1 for x, y in plan.values() if x is not None and y is not None)
    return f"{corners}c/{len(plan) - corners}e"
```

Add both names to `_COLS` and populate them in `build_row`. `design_scale` comes from the engine's optimized scale; **confirm it is reachable from where `build_row` runs** — `grep -n "get_scale\|GetScale\|scale" mcp_harness/TreemakerWrapper.cpp | head`. If it is not currently exposed, add a `get_scale()` binding in the same style as Task 2's, in this task.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd <repo>/mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_boundary_scorecard.py -v --timeout=420`
Expected: PASS, 3 passed

- [ ] **Step 5: Re-measure the cohort**

Run: `cd <repo>/mcp_harness && PYTHONPATH=.:tests .venv/bin/python probe_boundary_seeds.py`
Then run the full ladder over all 24 cohort ids and record the serve rate. Expected before this slice: **18/24 (75%)**, residual exactly `[90, 353, 500, 830, 865, 2099]`.

- [ ] **Step 6: Re-measure the scorecard**

Run: `cd <repo>/mcp_harness && IDE_BENCH_DOG=1 PYTHONPATH=.:tests .venv/bin/python benchmark_subjects.py --out /tmp/scorecard_new.jsonl --baseline fixtures/scorecard_baseline.jsonl`
Expected: the two new columns, and **no other column changed**. A diff on `rescue_stage`, `served_fidelity`, `asymmetric` or `lint_class` for any of the six subjects needs explaining before it is blessed.

- [ ] **Step 7: Bless deliberately**

Update `fixtures/scorecard_baseline.jsonl` and `fixtures/rescue_cohort.json` (add a `measured.s0_boundary` block beside `s5b_serve_wiring`, and a new `residual_ids_s0` list) **in this commit**, with the `_meta` provenance updated to name the commit and date. Follow the S5b/S7 precedent: re-bless in the session that moved the rows, never later.

- [ ] **Step 8: Answer the hull-vs-square hypothesis (spec §4.5)**

The spec labels this a hypothesis, not a promise: *if* leaves are constrained to
the paper edges and corners, the exported leaf hull may extend to the paper
boundary, and the exported hull may approach the square. Memory records
`export-emits-hull-not-square` as "LIKELY PERMANENT", so a negative here changes
nothing — but it is a two-line measurement on data this task already has.

Add to `probe_boundary_seeds.py` and run over whichever rows packed:

```python
def hull_ratio(fold: dict) -> float:
    """Area of the convex hull of the B-assignment boundary vertices, over
    paper area. 1.0 means the crease pattern fills the square."""
    import numpy as np
    from scipy.spatial import ConvexHull
    V = np.asarray(fold["vertices_coords"], float)[:, :2]
    on_b = sorted({v for (a, b), asn in zip(fold["edges_vertices"],
                                            fold["edges_assignment"])
                   if asn == "B" for v in (a, b)})
    if len(on_b) < 3:
        return float("nan")
    return float(ConvexHull(V[on_b]).volume)   # 'volume' is area in 2-D
```

Report `hull_ratio` with and without the rung for each packing row. **Record the
number either way.** If it does not move, `export-emits-hull-not-square` keeps
its status and the slice stands on the cohort rate alone.

- [ ] **Step 9: Full suite**

Run: `cd <repo>/mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/ -q --timeout=420`
Expected: **4 failed / 2124 passed / 11 skipped**, ± the rows re-blessed above. It looks hung at ~0% CPU early and finishes in ~23 min — do not kill it. Check the host for orphaned processes first.

- [ ] **Step 10: Commit**

```bash
git add mcp_harness/benchmark_subjects.py mcp_harness/tests/test_boundary_scorecard.py \
        mcp_harness/fixtures/scorecard_baseline.jsonl mcp_harness/fixtures/rescue_cohort.json
git commit -m "measure(slice-0): boundary_nodes + design_scale, cohort re-measured

design_scale is a PRICE TAG, not a regression guard: boundary conditions
cannot raise the global-optimum scale, so the question is whether validity
was bought with the loss, not whether the loss occurred."
```

---

## What "done" looks like

The slice ships if, and only if, the cohort serve rate rises above **18/24** with `nudge_marker` and `asymmetric` unchanged and attempt-0 byte-identical. If it does not, the honest deliverable is the measurement and the two negative results (boundary seeds, boundary constraints), recorded in `rescue_cohort.json` alongside R12's centre-control arm — which, if *it* rescues rows, is the next slice.

**Do not ship a rung that moves subjects between two rank-2 preserving stages and call it a win.** The scorecard has no headroom; the cohort is the measurement.
