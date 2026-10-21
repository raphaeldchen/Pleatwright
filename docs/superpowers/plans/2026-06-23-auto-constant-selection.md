# Auto-Constant Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace per-body-plan hand-tuned `(voxel_res, prune_fraction)` with a closed-loop search that takes any mesh and returns a packable Metric Tree — or a clearly-labeled best effort.

**Architecture:** A single new orchestrator `auto_mesh_to_metric_tree` layered on top of the five existing (untouched) extraction stages in `mesh_to_tree.py`. It sweeps the cheap `prune_fraction` axis over a skeleton cached per expensive `voxel_res`, uses the Tier 2.5 feasibility gate as a filter+ranker so only gate-blessed trees reach the C++ compiler, and always returns a `MeshTreeResult` with an explicit `confirmed` flag (never raises).

**Tech Stack:** Python 3.14, `networkx`, `numpy`, `trimesh`, `skeletor`, `scikit-learn` (via the existing `feasibility.gate`), `pytest`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-06-23-auto-constant-selection-design.md`.
- The five existing extraction stages (`load_mesh`, `extract_skeleton`, `simplify_to_tree`, `detect_symmetry`, `to_metric_tree`) and `mesh_to_metric_tree` MUST remain unchanged.
- A compile MUST only ever run on a tree whose gate verdict is NOT `"infeasible"`.
- The orchestrator MUST NOT raise on "nothing packed"; it returns `MeshTreeResult(confirmed=False, ...)`.
- Determinism: do not touch the existing seeds (`SKELETOR_SEED`, the `np.random.seed` in `extract_skeleton`). The same mesh must yield an identical `MeshTreeResult`.
- All new code lives in `mcp_harness/mesh_to_tree.py`; tests in `mcp_harness/tests/test_auto_mesh_to_tree.py`.
- Run tests with `<repo>/mcp_harness/.venv/bin/python -m pytest` and CWD = `mcp_harness/` (matches the existing suite's import style: `import mesh_to_tree as m2t`, `import server`).
- Commit messages end with: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

---

### Task 1: `structural_prefilter` — cheap reject before gate/compile

**Files:**
- Modify: `mcp_harness/mesh_to_tree.py` (add module constants + function near the other helpers)
- Test: `mcp_harness/tests/test_auto_mesh_to_tree.py` (create)

**Interfaces:**
- Consumes: existing `_leaf_count(nodes)` from `mesh_to_tree.py`.
- Produces: `structural_prefilter(nodes, *, min_leaves=4, max_leaves=8, max_root_children=4) -> bool`. Operates on the emitted Metric Tree node list (`[{"id", "parent_id", "length"}, ...]`). Returns `True` iff leaf count ∈ `[min_leaves, max_leaves]` AND the root (`parent_id is None`) has `≤ max_root_children` direct children.

- [ ] **Step 1: Write the failing test**

Create `mcp_harness/tests/test_auto_mesh_to_tree.py`:

```python
"""Auto-constant-selection: search orchestration over the mesh->tree pipeline.

Logic tests use dependency injection (stub gate + compile_fn) so they run with no
engine. A small real end-to-end suite proves auto-selection rediscovers good
constants on the fixtures. See docs/superpowers/specs/2026-06-23-auto-constant-selection-design.md.
"""
import mesh_to_tree as m2t


def _chain(n_leaves, root_children=None):
    """Build a Metric Tree node list: a root with `root_children` children, then
    enough extra leaf children hung off child 1 to reach n_leaves total leaves.
    If root_children is None it defaults to n_leaves (a flat star)."""
    if root_children is None:
        root_children = n_leaves
    nodes = [{"id": 0, "parent_id": None, "length": 0}]
    nid = 1
    # direct children of the root
    for _ in range(root_children):
        nodes.append({"id": nid, "parent_id": 0, "length": 0.1})
        nid += 1
    # remaining leaves hang off node 1 so they don't inflate root_children
    remaining = n_leaves - root_children
    for _ in range(remaining):
        nodes.append({"id": nid, "parent_id": 1, "length": 0.1})
        nid += 1
    return nodes


def test_prefilter_accepts_in_window_non_overloaded():
    assert m2t.structural_prefilter(_chain(5, root_children=3)) is True


def test_prefilter_rejects_too_few_leaves():
    assert m2t.structural_prefilter(_chain(3, root_children=3)) is False


def test_prefilter_rejects_too_many_leaves():
    assert m2t.structural_prefilter(_chain(9, root_children=4)) is False


def test_prefilter_rejects_overloaded_root():
    # 5 leaves (in window) but all 5 hang off the root -> overloaded
    assert m2t.structural_prefilter(_chain(5, root_children=5)) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp_harness && ../mcp_harness/.venv/bin/python -m pytest tests/test_auto_mesh_to_tree.py -q`
Expected: FAIL with `AttributeError: module 'mesh_to_tree' has no attribute 'structural_prefilter'`

- [ ] **Step 3: Write minimal implementation**

In `mcp_harness/mesh_to_tree.py`, add after the existing tunable constants block (after `SKELETOR_SEED = 0`):

```python
# --- Auto-constant-selection search (see the 2026-06-23 design spec) ----------
PRUNE_GRID = [0.20, 0.30, 0.40, 0.50, 0.60, 0.70]   # cheap inner axis (reuses skel)
VOXEL_GRID = [96, 64, 128]                          # expensive outer axis; escalate on failure
SEARCH_K = 2                                        # max compiles attempted per voxel_res
MIN_LEAVES, MAX_LEAVES = 4, 8                       # packable flap-count window
MAX_ROOT_CHILDREN = 4                               # POLYS_MULTIPLE_IBPS overloaded-root guard
```

Then add this function near `_leaf_count` (after it):

```python
def structural_prefilter(nodes, *, min_leaves=MIN_LEAVES, max_leaves=MAX_LEAVES,
                         max_root_children=MAX_ROOT_CHILDREN) -> bool:
    """Cheap accept/reject on the emitted Metric Tree, before paying for the gate
    or a compile. True iff the leaf count is in the packable window and the root is
    not overloaded (a many-child root is the POLYS_MULTIPLE_IBPS anti-pattern)."""
    leaves = _leaf_count(nodes)
    root = next(n["id"] for n in nodes if n["parent_id"] is None)
    root_children = sum(1 for n in nodes if n["parent_id"] == root)
    return (min_leaves <= leaves <= max_leaves
            and root_children <= max_root_children)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp_harness && ../mcp_harness/.venv/bin/python -m pytest tests/test_auto_mesh_to_tree.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/mesh_to_tree.py mcp_harness/tests/test_auto_mesh_to_tree.py
git commit -m "$(printf 'feat(mesh_to_tree): structural_prefilter + search constants\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

### Task 2: `rank` — order the feasible set for compilation

**Files:**
- Modify: `mcp_harness/mesh_to_tree.py`
- Test: `mcp_harness/tests/test_auto_mesh_to_tree.py`

**Interfaces:**
- Produces: `rank(feasible) -> list`. Input/output element shape is `(verdict_dict, nodes, pairs, prune)` where `verdict_dict` has keys `"verdict"` (`"feasible"` | `"compile_anyway"`) and `"p_pack"` (float). Sort: `"feasible"` before `"compile_anyway"`, then `p_pack` descending. Stable for equal keys.

- [ ] **Step 1: Write the failing test**

Append to `mcp_harness/tests/test_auto_mesh_to_tree.py`:

```python
def _entry(verdict, p_pack, tag):
    # nodes/pairs are opaque to rank(); use the tag to identify ordering.
    return ({"verdict": verdict, "p_pack": p_pack}, [tag], [], 0.4)


def test_rank_feasible_before_compile_anyway():
    feasible = [
        _entry("compile_anyway", 0.99, "ood_high"),
        _entry("feasible", 0.10, "feas_low"),
    ]
    ordered = m2t.rank(feasible)
    # feasible wins even with a far lower p_pack than the OOD candidate
    assert [e[1][0] for e in ordered] == ["feas_low", "ood_high"]


def test_rank_by_p_pack_descending_within_class():
    feasible = [
        _entry("feasible", 0.30, "a"),
        _entry("feasible", 0.80, "b"),
        _entry("compile_anyway", 0.50, "c"),
        _entry("compile_anyway", 0.70, "d"),
    ]
    ordered = m2t.rank(feasible)
    assert [e[1][0] for e in ordered] == ["b", "a", "d", "c"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp_harness && ../mcp_harness/.venv/bin/python -m pytest tests/test_auto_mesh_to_tree.py -k rank -q`
Expected: FAIL with `AttributeError: module 'mesh_to_tree' has no attribute 'rank'`

- [ ] **Step 3: Write minimal implementation**

Add to `mcp_harness/mesh_to_tree.py` after `structural_prefilter`:

```python
_VERDICT_PRIORITY = {"feasible": 0, "compile_anyway": 1}


def rank(feasible):
    """Order feasible candidates for compilation: in-distribution 'feasible' trees
    ahead of OOD 'compile_anyway' trees (whose p_pack is unreliable), then by
    p_pack descending. Each element is (verdict_dict, nodes, pairs, prune)."""
    return sorted(
        feasible,
        key=lambda e: (_VERDICT_PRIORITY[e[0]["verdict"]], -e[0]["p_pack"]),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp_harness && ../mcp_harness/.venv/bin/python -m pytest tests/test_auto_mesh_to_tree.py -k rank -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/mesh_to_tree.py mcp_harness/tests/test_auto_mesh_to_tree.py
git commit -m "$(printf 'feat(mesh_to_tree): rank() feasible candidates for compilation\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

### Task 3: `auto_mesh_to_metric_tree` orchestrator (with injectable gate/compile)

**Files:**
- Modify: `mcp_harness/mesh_to_tree.py`
- Test: `mcp_harness/tests/test_auto_mesh_to_tree.py`

**Interfaces:**
- Consumes: `structural_prefilter` (Task 1), `rank` (Task 2), existing `load_mesh`/`extract_skeleton`/`simplify_to_tree`/`detect_symmetry`/`to_metric_tree`, `feasibility.gate.load`, `server.draft_and_compile_full_base`.
- Produces:
  - `@dataclass MeshTreeResult` with fields: `confirmed: bool`, `nodes: list`, `pairs: list`, `voxel_res: int`, `prune_fraction: float`, `gate: dict`, `trace: list`.
  - `compiles_to_fold(nodes, pairs, compile_fn) -> bool` — `True` iff `compile_fn` returns a non-`ERROR:` string containing `'"vertices_coords"'`.
  - `auto_mesh_to_metric_tree(path, *, gate=None, compile_fn=None, voxel_grid=VOXEL_GRID, prune_grid=PRUNE_GRID, k=SEARCH_K) -> MeshTreeResult`. `gate` defaults to the loaded `feasibility.gate`; `compile_fn` defaults to `server.draft_and_compile_full_base`. `gate` must expose `.predict(nodes, pairs) -> dict`. `compile_fn` must be `Callable[[list, list], str]`.

- [ ] **Step 1: Write the failing test**

Append to `mcp_harness/tests/test_auto_mesh_to_tree.py`:

```python
class _StubGate:
    """Return a fixed verdict per call, keyed by a chooser(nodes)->verdict func."""
    def __init__(self, chooser):
        self._chooser = chooser
        self.calls = 0

    def predict(self, nodes, pairs):
        self.calls += 1
        return self._chooser(nodes)


def _fold_ok():
    return '{"vertices_coords": [[0,0]]}'


def test_only_non_infeasible_trees_are_compiled(monkeypatch, tmp_path):
    # Force the extraction to yield one valid tree per prune value by stubbing the
    # stages so the orchestrator logic is exercised without the real engine.
    import networkx as nx

    def fake_load_mesh(path, voxel_res=96):
        return object()

    def fake_extract_skeleton(mesh):
        return nx.path_graph(2)

    def fake_simplify(skel, prune_fraction):
        g = nx.Graph()
        g.add_node(0, pos=[0, 0, 0])
        for i in range(1, 6):                      # 5 leaves off node 1 hub
            g.add_node(i, pos=[i, 0, 0])
        g.add_edge(0, 1, length=1.0)
        g.add_edge(1, 2, length=0.5)
        g.add_edge(1, 3, length=0.5)
        g.add_edge(0, 4, length=0.5)
        g.add_edge(0, 5, length=0.5)
        return g

    def fake_symmetry(tree, mesh):
        return []

    monkeypatch.setattr(m2t, "load_mesh", fake_load_mesh)
    monkeypatch.setattr(m2t, "extract_skeleton", fake_extract_skeleton)
    monkeypatch.setattr(m2t, "simplify_to_tree", fake_simplify)
    monkeypatch.setattr(m2t, "detect_symmetry", fake_symmetry)

    gate = _StubGate(lambda nodes: {"verdict": "infeasible", "p_pack": 0.01})
    compiled = []

    def compile_fn(nodes, pairs):
        compiled.append(nodes)
        return _fold_ok()

    res = m2t.auto_mesh_to_metric_tree(
        "x.glb", gate=gate, compile_fn=compile_fn,
        voxel_grid=[96], prune_grid=[0.4])
    assert compiled == []                 # gate rejected -> nothing compiled
    assert res.confirmed is False
    assert res.gate["verdict"] == "infeasible"
    assert len(res.trace) >= 1


def test_confirmed_when_a_feasible_tree_compiles(monkeypatch):
    import networkx as nx
    monkeypatch.setattr(m2t, "load_mesh", lambda p, voxel_res=96: object())
    monkeypatch.setattr(m2t, "extract_skeleton", lambda m: nx.path_graph(2))

    def fake_simplify(skel, prune_fraction):
        g = nx.Graph()
        g.add_node(0, pos=[0, 0, 0])
        for i in range(1, 6):
            g.add_node(i, pos=[i, 0, 0])
        g.add_edge(0, 1, length=1.0)
        g.add_edge(1, 2, length=0.5)
        g.add_edge(1, 3, length=0.5)
        g.add_edge(0, 4, length=0.5)
        g.add_edge(0, 5, length=0.5)
        return g

    monkeypatch.setattr(m2t, "simplify_to_tree", fake_simplify)
    monkeypatch.setattr(m2t, "detect_symmetry", lambda t, m: [])

    gate = _StubGate(lambda nodes: {"verdict": "feasible", "p_pack": 0.9})
    res = m2t.auto_mesh_to_metric_tree(
        "x.glb", gate=gate, compile_fn=lambda n, p: _fold_ok(),
        voxel_grid=[96], prune_grid=[0.4])
    assert res.confirmed is True
    assert res.voxel_res == 96
    assert res.prune_fraction == 0.4
    assert '"vertices_coords"' not in str(res.gate)   # gate is the verdict dict, not FOLD


def test_escalates_voxel_res_on_failure(monkeypatch):
    import networkx as nx
    monkeypatch.setattr(m2t, "load_mesh", lambda p, voxel_res=96: voxel_res)

    def fake_extract(voxel_res):
        return nx.path_graph(2)            # identity carrier; value unused downstream

    monkeypatch.setattr(m2t, "extract_skeleton", fake_extract)

    def fake_simplify(skel, prune_fraction):
        g = nx.Graph()
        g.add_node(0, pos=[0, 0, 0])
        for i in range(1, 6):
            g.add_node(i, pos=[i, 0, 0])
        g.add_edge(0, 1, length=1.0)
        g.add_edge(1, 2, length=0.5)
        g.add_edge(1, 3, length=0.5)
        g.add_edge(0, 4, length=0.5)
        g.add_edge(0, 5, length=0.5)
        return g

    monkeypatch.setattr(m2t, "simplify_to_tree", fake_simplify)
    monkeypatch.setattr(m2t, "detect_symmetry", lambda t, m: [])

    # compile fails at voxel 96, succeeds at 64
    def compile_fn(nodes, pairs):
        # the orchestrator must pass the chosen voxel via the result; emulate by
        # failing the first voxel. Use a mutable counter on the function.
        compile_fn.n += 1
        return "ERROR: no pack" if compile_fn.n == 1 else _fold_ok()
    compile_fn.n = 0

    gate = _StubGate(lambda nodes: {"verdict": "feasible", "p_pack": 0.9})
    res = m2t.auto_mesh_to_metric_tree(
        "x.glb", gate=gate, compile_fn=compile_fn,
        voxel_grid=[96, 64], prune_grid=[0.4])
    assert res.confirmed is True
    assert res.voxel_res == 64            # escalated past 96
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp_harness && ../mcp_harness/.venv/bin/python -m pytest tests/test_auto_mesh_to_tree.py -k "auto or compiled or escalat or confirmed" -q`
Expected: FAIL with `AttributeError: module 'mesh_to_tree' has no attribute 'auto_mesh_to_metric_tree'`

- [ ] **Step 3: Write minimal implementation**

At the top of `mcp_harness/mesh_to_tree.py`, add to the imports block:

```python
import os
from dataclasses import dataclass, field
```

Add the result type near the other module-level definitions (after the search constants):

```python
@dataclass
class MeshTreeResult:
    """Always-returned contract from auto_mesh_to_metric_tree.

    confirmed=True  -> (nodes, pairs) is FOLD-verified at (voxel_res, prune_fraction).
    confirmed=False -> best effort: the highest-p_pack tree seen; nothing packed.
    `gate` is the verdict dict for the chosen tree; `trace` logs every attempt.
    """
    confirmed: bool
    nodes: list
    pairs: list
    voxel_res: int
    prune_fraction: float
    gate: dict
    trace: list = field(default_factory=list)
```

Add the helpers + orchestrator after `to_metric_tree` (and before `mesh_to_metric_tree`):

```python
def compiles_to_fold(nodes, pairs, compile_fn) -> bool:
    """True iff compile_fn yields a real FOLD (not an 'ERROR:' string)."""
    result = compile_fn(nodes, pairs)
    return not result.startswith("ERROR:") and '"vertices_coords"' in result


def _default_gate():
    from feasibility import gate as _gate
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.environ.get("FEASIBILITY_GATE_PATH",
                          os.path.join(here, "feasibility", "gate.joblib"))
    return _gate.load(path)


def _default_compile_fn(nodes, pairs):
    import server
    return server.draft_and_compile_full_base(nodes, pairs)


def auto_mesh_to_metric_tree(path, *, gate=None, compile_fn=None,
                             voxel_grid=VOXEL_GRID, prune_grid=PRUNE_GRID,
                             k=SEARCH_K) -> MeshTreeResult:
    """Closed-loop search for packable extraction constants on an arbitrary mesh.

    Sweeps the cheap prune axis over a skeleton cached per expensive voxel_res;
    the gate filters out 'infeasible' trees and ranks the rest; only the top k
    gate-blessed trees per voxel_res are compiled. Returns a MeshTreeResult that is
    confirmed when a tree compiles to FOLD, else the best-effort (highest p_pack)
    tree. See the 2026-06-23 design spec.
    """
    gate = gate or _default_gate()
    compile_fn = compile_fn or _default_compile_fn

    trace = []
    best = None     # (p_pack, nodes, pairs, voxel_res, prune, verdict)

    for voxel_res in voxel_grid:
        mesh = load_mesh(path, voxel_res)
        skel = extract_skeleton(mesh)
        feasible = []
        for prune in prune_grid:
            tree = simplify_to_tree(skel, prune)
            if tree.number_of_edges() == 0:          # over-pruned -> nothing to emit
                trace.append({"voxel_res": voxel_res, "prune": prune,
                              "leaf_count": 0, "verdict": "empty",
                              "p_pack": 0.0, "compiled": None})
                continue
            nodes, pairs = to_metric_tree(tree, detect_symmetry(tree, mesh))
            leaf_count = _leaf_count(nodes)
            if not structural_prefilter(nodes):
                trace.append({"voxel_res": voxel_res, "prune": prune,
                              "leaf_count": leaf_count, "verdict": "prefilter",
                              "p_pack": 0.0, "compiled": None})
                continue
            verdict = gate.predict(nodes, pairs)
            trace.append({"voxel_res": voxel_res, "prune": prune,
                          "leaf_count": leaf_count, "verdict": verdict["verdict"],
                          "p_pack": verdict["p_pack"], "compiled": None})
            p = verdict["p_pack"]
            if best is None or p > best[0]:
                best = (p, nodes, pairs, voxel_res, prune, verdict)
            if verdict["verdict"] != "infeasible":
                feasible.append((verdict, nodes, pairs, prune))

        for verdict, nodes, pairs, prune in rank(feasible)[:k]:
            ok = compiles_to_fold(nodes, pairs, compile_fn)
            # annotate the matching trace row for this (voxel_res, prune)
            for row in trace:
                if row["voxel_res"] == voxel_res and row["prune"] == prune:
                    row["compiled"] = ok
            if ok:
                return MeshTreeResult(
                    confirmed=True, nodes=nodes, pairs=pairs,
                    voxel_res=voxel_res, prune_fraction=prune,
                    gate=verdict, trace=trace)

    if best is None:    # nothing even survived prefilter anywhere
        return MeshTreeResult(confirmed=False, nodes=[], pairs=[],
                              voxel_res=voxel_grid[-1], prune_fraction=prune_grid[-1],
                              gate={}, trace=trace)
    _, nodes, pairs, voxel_res, prune, verdict = best
    return MeshTreeResult(confirmed=False, nodes=nodes, pairs=pairs,
                          voxel_res=voxel_res, prune_fraction=prune,
                          gate=verdict, trace=trace)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp_harness && ../mcp_harness/.venv/bin/python -m pytest tests/test_auto_mesh_to_tree.py -q`
Expected: PASS (all unit tests; ~9 passed)

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/mesh_to_tree.py mcp_harness/tests/test_auto_mesh_to_tree.py
git commit -m "$(printf 'feat(mesh_to_tree): auto_mesh_to_metric_tree closed-loop search\n\nGate-filtered, gate-ranked search over (voxel_res, prune_fraction); only\nnon-infeasible trees compile; always returns a MeshTreeResult.\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

### Task 4: Real end-to-end integration + determinism

**Files:**
- Test: `mcp_harness/tests/test_auto_mesh_to_tree.py`

**Interfaces:**
- Consumes: `auto_mesh_to_metric_tree` with its real defaults (real gate + real `server` compile), the 5 fixtures in `mcp_harness/fixtures/`.
- Produces: nothing new — validation only.

- [ ] **Step 1: Write the failing test**

Append to `mcp_harness/tests/test_auto_mesh_to_tree.py`:

```python
import os

import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # mcp_harness/

# Faithfulness yardstick per fixture: auto-selection must rediscover a tree whose
# leaf count + bilateral pairs match what the hand-tuned constants produced.
#   name, file, lo_leaves, hi_leaves, min_pairs
E2E_FIXTURES = [
    ("quadruped", "quadruped.glb", 4, 7, 1),
    ("humanoid",  "humanoid.glb",  4, 7, 2),
    ("fish",      "fish.glb",      4, 8, 1),
    ("bird",      "bird.glb",      4, 7, 1),
    ("insect",    "insect.glb",    4, 8, 3),
]


@pytest.mark.parametrize("name,fname,lo,hi,min_pairs", E2E_FIXTURES)
def test_auto_selection_confirms_each_body_plan(name, fname, lo, hi, min_pairs):
    """auto_mesh_to_metric_tree (real gate + real compiler, NO hand-tuned
    constants) finds a packable tree for each body plan with a faithful flap
    count + bilateral pairs."""
    path = os.path.join(HERE, "fixtures", fname)
    res = m2t.auto_mesh_to_metric_tree(path)
    assert res.confirmed is True, f"{name}: not confirmed; trace={res.trace}"
    leaves = m2t._leaf_count(res.nodes)
    assert lo <= leaves <= hi, f"{name}: {leaves} leaves outside [{lo},{hi}]"
    assert len(res.pairs) >= min_pairs, f"{name}: {len(res.pairs)} pairs < {min_pairs}"


def test_auto_selection_is_deterministic():
    path = os.path.join(HERE, "fixtures", "quadruped.glb")
    a = m2t.auto_mesh_to_metric_tree(path)
    b = m2t.auto_mesh_to_metric_tree(path)
    assert a.confirmed == b.confirmed
    assert a.voxel_res == b.voxel_res
    assert a.prune_fraction == b.prune_fraction
    assert a.nodes == b.nodes
    assert a.pairs == b.pairs
```

- [ ] **Step 2: Run test to verify it fails (then confirm it is the intended state)**

Run: `cd mcp_harness && ../mcp_harness/.venv/bin/python -m pytest tests/test_auto_mesh_to_tree.py -k "auto_selection" -q`
Expected: Tests run end-to-end. They should PASS if the search finds packable constants for each fixture. If any body plan fails to confirm, that is real signal — inspect `res.trace` to see whether the gate over-rejected or no prune value landed in-window, and widen `PRUNE_GRID`/`VOXEL_GRID` (or adjust `MIN_LEAVES`/`MAX_LEAVES`) accordingly, then re-run. Do NOT loosen the faithfulness assertions to force a pass.

- [ ] **Step 3: (Only if a fixture failed) widen the search grids**

If e.g. the humanoid did not confirm, the most likely cause is its gentler pruning need (hand-tuned 0.25). `PRUNE_GRID` already starts at 0.20, so first inspect the trace. If a needed value is missing, extend the grid in `mesh_to_tree.py`, e.g.:

```python
PRUNE_GRID = [0.20, 0.25, 0.30, 0.40, 0.50, 0.60, 0.70]
```

Re-run Step 2.

- [ ] **Step 4: Run the full new test file + the existing mesh suite**

Run: `cd mcp_harness && ../mcp_harness/.venv/bin/python -m pytest tests/test_auto_mesh_to_tree.py tests/test_mesh_to_tree.py -q`
Expected: PASS (all unit + e2e + the pre-existing 11 mesh tests)

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/tests/test_auto_mesh_to_tree.py mcp_harness/mesh_to_tree.py
git commit -m "$(printf 'test(mesh_to_tree): e2e auto-selection confirms all 5 body plans\n\nProves the search rediscovers packable constants with no hand tuning,\nplus a determinism check.\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

## Self-Review

**Spec coverage:**
- Closed-loop search, cheap-prune/expensive-voxel ordering → Task 3 orchestrator. ✓
- Gate as filter (exclude `infeasible`), OOD stays eligible → Task 3 (`verdict["verdict"] != "infeasible"`), tested in Task 3. ✓
- `min(k, n_feasible)` compile rule → `rank(feasible)[:k]` slice (a list shorter than k yields all of it). ✓
- Ranking (feasible > compile_anyway, then p_pack desc) → Task 2. ✓
- Grids + `structural_prefilter` thresholds → Tasks 1, 3 constants. ✓
- `MeshTreeResult` contract incl. `confirmed`, `trace`, best-effort highest-p_pack → Task 3. ✓
- Never raises on exhaustion → Task 3 returns `confirmed=False`. ✓
- Determinism → Task 4 determinism test; no seed changes. ✓
- E2E faithfulness on all 5 fixtures → Task 4. ✓
- Data-loop hook (trace as capture point, nothing built) → satisfied by `trace` field; no task needed (explicitly out of scope). ✓

**Placeholder scan:** No TBD/TODO; every code step shows complete code. Task 4 Step 3 is a conditional remediation with concrete code, not a placeholder. ✓

**Type consistency:** `structural_prefilter(nodes)`, `rank(feasible)` element shape `(verdict_dict, nodes, pairs, prune)`, `compiles_to_fold(nodes, pairs, compile_fn)`, `MeshTreeResult` fields, and `auto_mesh_to_metric_tree(...)` signature are consistent across Tasks 1–4. The gate stub exposes `.predict(nodes, pairs) -> dict` matching the real `feasibility.gate.Gate`. ✓
