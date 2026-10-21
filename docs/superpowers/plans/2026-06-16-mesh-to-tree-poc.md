# 3D Mesh → Metric Tree (POC) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn a provided 3D mesh into the abstract Metric Tree the system already compiles, validated against the four templated body plans, so the AI can derive limb topology + proportions from a real reference instead of guessing.

**Architecture:** A standalone module `mcp_harness/mesh_to_tree.py` with six focused functions (load → extract skeleton → simplify to tree → detect symmetry → to metric tree → orchestrate). The metric tree is abstract (topology + proportional lengths only), so there is no 3D→2D projection. Output is the same `(tree_nodes, symmetric_pairs)` the agent emits, fed through the existing `server.draft_and_compile_full_base` compile path (which already has perturb-and-retry). Not wired into the agent/MCP — POC only.

**Tech Stack:** Python 3.14, `trimesh` (mesh I/O + geometry), `skeletor` (mesh-contraction skeletonization), `networkx` (graph ops), `scikit-image` (marching cubes for voxel remesh), `scipy`/`numpy`. Existing: `headless_treemaker` (compiled), `server.py`, `tests/runner.py`. Tests via `pytest`.

**Spike findings already validated (2026-06-16, controller pre-flight):** deps
install + import on Py3.14 (`trimesh` 4.12, `skeletor` 1.5 with `by_wavefront` /
`pre.contract` / `pre.fix_mesh`). The quadruped fixture (`fixtures/quadruped.glb`,
the CC0 Khronos Fox) is already committed. Critically, the Fox is a **fragmented
14-body mesh**, so the naive "load + take largest component" yields a *disconnected*
skeleton and drops limbs. The working fix (validated end-to-end): **voxel-remesh to
a single watertight manifold** (`mesh.voxelized(pitch).fill().marching_cubes`)
before skeletonizing → connected skeleton, 15 raw leaves → prune to ~9 leaves / 4
interior (4 legs + 2 ears + snout + tail — anatomically right). Tasks 1/2/3 below
already reflect this.

**Conventions (from this repo):**
- Run tests from `mcp_harness/`: `PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/ -q`
- The venv interpreter is `./.venv/bin/python`.
- `cd` resets between shell calls — always use absolute paths or `cd` inside the same command.
- Spawn-based multiprocessing (used by `server`/`runner`) requires module-level code under `if __name__ == "__main__"`.

---

## File Structure

- Create: `mcp_harness/mesh_to_tree.py` — the six functions + tunable constants + `__main__` demo.
- Create: `mcp_harness/fixtures/quadruped.glb`, `bird.glb`, `humanoid.glb`, `insect.glb` — CC0 test meshes.
- Create: `mcp_harness/fixtures/SOURCES.md` — provenance + license of each mesh.
- Create: `mcp_harness/tests/test_mesh_to_tree.py` — the tests.
- Create (throwaway, not committed): `mcp_harness/spike_skeletor.py` — Task 2 observation only.

---

## Task 1: Dependencies + module scaffold

**Files:**
- Create: `mcp_harness/mesh_to_tree.py`
- Modify: none

- [ ] **Step 1: Install dependencies into the venv**

Run:
```bash
cd <repo>/mcp_harness && \
  ./.venv/bin/python -m pip install "trimesh[easy]" skeletor networkx scipy numpy scikit-image
```
(Already done in the controller pre-flight; this step is a no-op verification.)
Expected: installs successfully. Record installed versions:
```bash
cd <repo>/mcp_harness && \
  ./.venv/bin/python -c "import trimesh, skeletor, networkx, scipy, numpy; \
  print('trimesh', trimesh.__version__); print('skeletor', skeletor.__version__); \
  print('networkx', networkx.__version__)"
```

- [ ] **Step 2: Create the module scaffold with constants and stubs**

Create `mcp_harness/mesh_to_tree.py`:
```python
"""3D mesh -> abstract Metric Tree (POC).

Extracts limb topology + proportional bone lengths + bilateral symmetry from a
provided mesh and emits the same (tree_nodes, symmetric_pairs) the agent produces,
to feed the existing compile path. The Metric Tree is abstract (no coordinates),
so there is NO 3D->2D projection here. See
docs/superpowers/specs/2026-06-16-mesh-to-tree-poc-design.md.
"""
from __future__ import annotations

import networkx as nx
import numpy as np
import trimesh

# --- Tunable constants (starting points; tune per fixture, see Task 6/8) ------
PRUNE_FRACTION = 0.12        # prune a leaf whose branch length < this * longest branch
SYMMETRY_TOL = 0.08          # reflected-point match tolerance, fraction of mesh scale
LONGEST_LIMB_TARGET = 0.40   # normalize so the longest tree edge == this (packing regime)
SKELETOR_SEED = 0            # pin any skeletor/contraction randomness


def load_mesh(path: str) -> trimesh.Trimesh:
    raise NotImplementedError


def extract_skeleton(mesh: trimesh.Trimesh) -> nx.Graph:
    raise NotImplementedError


def simplify_to_tree(skel: nx.Graph) -> nx.Graph:
    raise NotImplementedError


def detect_symmetry(tree: nx.Graph, mesh: trimesh.Trimesh) -> list[tuple[int, int]]:
    raise NotImplementedError


def to_metric_tree(tree: nx.Graph, sym: list[tuple[int, int]]):
    raise NotImplementedError


def mesh_to_metric_tree(path: str):
    raise NotImplementedError


if __name__ == "__main__":
    import sys
    nodes, pairs = mesh_to_metric_tree(sys.argv[1])
    print("nodes:", nodes)
    print("pairs:", pairs)
```

- [ ] **Step 3: Verify it imports**

Run:
```bash
cd <repo>/mcp_harness && \
  ./.venv/bin/python -c "import mesh_to_tree; print('ok')"
```
Expected: prints `ok`.

- [ ] **Step 4: Commit**

```bash
cd <repo> && \
  git add mcp_harness/mesh_to_tree.py && \
  git commit -m "scaffold: mesh_to_tree module + deps"
```

---

## Task 2: Source the quadruped fixture + spike skeletor

**Files:**
- Create: `mcp_harness/fixtures/quadruped.glb`
- Create: `mcp_harness/fixtures/SOURCES.md`
- Create (throwaway): `mcp_harness/spike_skeletor.py`

- [ ] **Step 1: Obtain a CC0 quadruped mesh**

Download a small (≤ a few thousand faces) CC0 quadruped `.glb`. Concrete CC0 sources, in order of preference:
- Quaternius animal packs (https://quaternius.com, CC0) — e.g. a wolf/dog/horse, export/convert to `.glb`.
- Poly Pizza (https://poly.pizza, filter license = CC0) — search "dog"/"horse".
- Kenney (https://kenney.nl, CC0).

Save as `mcp_harness/fixtures/quadruped.glb`. If the asset is large, decimate:
```bash
cd <repo>/mcp_harness && \
  ./.venv/bin/python -c "import trimesh; m=trimesh.load('fixtures/quadruped.glb', force='mesh'); \
  m=m.simplify_quadric_decimation(2000) if len(m.faces)>2000 else m; \
  m.export('fixtures/quadruped.glb'); print('faces', len(m.faces))"
```

- [ ] **Step 2: Record provenance**

Create `mcp_harness/fixtures/SOURCES.md`:
```markdown
# Test mesh sources

All meshes are CC0 (public domain) and committed for reproducible POC testing.

| file | subject | source URL | license |
|------|---------|-----------|---------|
| quadruped.glb | <animal> | <url> | CC0 |
```
Fill `<animal>` and `<url>` with the actual download.

- [ ] **Step 3: Spike — observe what skeletor produces**

Create `mcp_harness/spike_skeletor.py` (throwaway, not committed):
```python
"""Spike: observe skeletor's output structure on the quadruped fixture so the
real tasks build on reality, not assumptions. Reconcile extract_skeleton (Task 5)
with whatever the installed skeletor version actually returns."""
import trimesh, skeletor as sk
import numpy as np

m = trimesh.load("fixtures/quadruped.glb", force="mesh")
print("mesh: faces", len(m.faces), "watertight", m.is_watertight, "extents", m.extents)

fixed = sk.pre.fix_mesh(m, remove_disconnected=5, inplace=False)
cont = sk.pre.contract(fixed, epsilon=0.1, iter_lim=10)
skel = sk.skeletonize.by_wavefront(cont, waves=1, step_size=1)

print("type", type(skel))
print("attrs", [a for a in dir(skel) if not a.startswith("_")])
print("swc head:\n", skel.swc.head())          # node_id, parent_id, x,y,z, radius
print("n_swc_nodes", len(skel.swc))
print("graph", type(skel.graph), skel.graph.number_of_nodes(), "nodes")
```
Run:
```bash
cd <repo>/mcp_harness && \
  ./.venv/bin/python spike_skeletor.py 2>&1 | head -40
```
Expected: prints the mesh stats and skeletor's SWC dataframe (a rooted tree of
`node_id, parent_id, x, y, z`) plus a networkx graph. **Note the exact attribute
names and the API that worked** (`by_wavefront` vs `by_teasar`); Task 5 must match
them. If `by_wavefront` errors, try `skel = sk.skeletonize.by_teasar(cont)`.

- [ ] **Step 4: Commit the fixture (not the spike)**

```bash
cd <repo> && \
  git add mcp_harness/fixtures/quadruped.glb mcp_harness/fixtures/SOURCES.md && \
  git commit -m "fixtures: CC0 quadruped mesh for mesh_to_tree POC"
```

---

## Task 3: load_mesh

**Files:**
- Modify: `mcp_harness/mesh_to_tree.py` (implement `load_mesh`)
- Test: `mcp_harness/tests/test_mesh_to_tree.py`

- [ ] **Step 1: Write the failing test**

Create `mcp_harness/tests/test_mesh_to_tree.py`:
```python
"""POC tests: mesh -> Metric Tree, validated against the templated body plans."""
import os
import mesh_to_tree as m2t

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # mcp_harness/
QUAD = os.path.join(HERE, "fixtures", "quadruped.glb")


def test_load_mesh_returns_single_watertight_component():
    mesh = m2t.load_mesh(QUAD)
    assert len(mesh.faces) > 0
    # after cleanup, one connected body (no stray islands)
    assert mesh.body_count == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd <repo>/mcp_harness && \
  PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_mesh_to_tree.py::test_load_mesh_returns_single_watertight_component -v
```
Expected: FAIL with `NotImplementedError`.

- [ ] **Step 3: Implement load_mesh**

Replace the `load_mesh` stub in `mesh_to_tree.py`:
```python
VOXEL_RES = 64  # remesh resolution: longest extent / this = voxel pitch


def load_mesh(path: str) -> trimesh.Trimesh:
    """Load a mesh and remesh it into a SINGLE watertight manifold.

    Real animal .glb assets are often fragmented multi-body meshes (legs/head as
    separate sub-objects not welded at seams) -> a disconnected skeleton that drops
    limbs. Voxel-remeshing (voxelize -> fill -> marching cubes) fuses everything
    into one closed manifold suitable for curve-skeletonization. Validated on the
    Khronos Fox in the Task-2 spike.
    """
    mesh = trimesh.load(path, force="mesh")
    pitch = float(mesh.extents.max()) / VOXEL_RES
    mani = mesh.voxelized(pitch=pitch).fill().marching_cubes
    mani.merge_vertices()
    return mani
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd <repo>/mcp_harness && \
  PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_mesh_to_tree.py::test_load_mesh_returns_single_watertight_component -v
```
Expected: PASS. (If `body_count` != 1, the chosen mesh has stray geometry; re-check the fixture.)

- [ ] **Step 5: Commit**

```bash
cd <repo> && \
  git add mcp_harness/mesh_to_tree.py mcp_harness/tests/test_mesh_to_tree.py && \
  git commit -m "feat(mesh_to_tree): load_mesh"
```

---

## Task 4: extract_skeleton

**Files:**
- Modify: `mcp_harness/mesh_to_tree.py` (implement `extract_skeleton`)
- Test: `mcp_harness/tests/test_mesh_to_tree.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_mesh_to_tree.py`:
```python
def test_extract_skeleton_is_connected_graph_with_positions():
    mesh = m2t.load_mesh(QUAD)
    skel = m2t.extract_skeleton(mesh)
    import networkx as nx
    assert isinstance(skel, nx.Graph)
    assert skel.number_of_nodes() > 8          # a curve skeleton has many nodes
    assert nx.is_connected(skel)
    # every node carries a 3D position
    n0 = next(iter(skel.nodes))
    assert len(skel.nodes[n0]["pos"]) == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd <repo>/mcp_harness && \
  PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_mesh_to_tree.py::test_extract_skeleton_is_connected_graph_with_positions -v
```
Expected: FAIL with `NotImplementedError`.

- [ ] **Step 3: Implement extract_skeleton (reconcile with the Task 2 spike)**

Replace the `extract_skeleton` stub. This uses skeletor's SWC output (a rooted
tree of `node_id, parent_id, x,y,z`) to build a positioned networkx graph. **Match
the API that the Task 2 spike confirmed works** — if the spike used `by_teasar`,
swap it in here.
```python
import skeletor as sk


def extract_skeleton(mesh: trimesh.Trimesh) -> nx.Graph:
    """Curve-skeletonize via mesh contraction; return a positioned nx.Graph.

    Uses skeletor's SWC (node_id, parent_id, x,y,z) as the skeleton tree and
    builds an undirected graph whose nodes carry 'pos' and whose edges carry the
    euclidean 'length' between endpoints.
    """
    np.random.seed(SKELETOR_SEED)
    fixed = sk.pre.fix_mesh(mesh, remove_disconnected=5, inplace=False)
    cont = sk.pre.contract(fixed, epsilon=0.1, iter_lim=10)
    skel = sk.skeletonize.by_wavefront(cont, waves=1, step_size=1)

    swc = skel.swc
    pos = {int(r.node_id): np.array([r.x, r.y, r.z]) for r in swc.itertuples()}
    g = nx.Graph()
    for nid, p in pos.items():
        g.add_node(nid, pos=p)
    for r in swc.itertuples():
        if int(r.parent_id) >= 0:  # SWC root has parent_id -1
            a, b = int(r.node_id), int(r.parent_id)
            g.add_edge(a, b, length=float(np.linalg.norm(pos[a] - pos[b])))
    # keep the largest connected component if skeletonization fragmented
    if not nx.is_connected(g):
        comp = max(nx.connected_components(g), key=len)
        g = g.subgraph(comp).copy()
    return g
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd <repo>/mcp_harness && \
  PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_mesh_to_tree.py::test_extract_skeleton_is_connected_graph_with_positions -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd <repo> && \
  git add mcp_harness/mesh_to_tree.py mcp_harness/tests/test_mesh_to_tree.py && \
  git commit -m "feat(mesh_to_tree): extract_skeleton via skeletor SWC"
```

---

## Task 5: simplify_to_tree

**Files:**
- Modify: `mcp_harness/mesh_to_tree.py` (implement `simplify_to_tree`)
- Test: `mcp_harness/tests/test_mesh_to_tree.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_mesh_to_tree.py`:
```python
def test_simplify_to_tree_yields_small_acyclic_tree():
    import networkx as nx
    skel = m2t.extract_skeleton(m2t.load_mesh(QUAD))
    tree = m2t.simplify_to_tree(skel)
    assert nx.is_tree(tree)
    leaves = [n for n in tree.nodes if tree.degree(n) == 1]
    # the Fox: 4 legs + 2 ears + snout + tail -> ~6..10 leaves after pruning twigs
    assert 6 <= len(leaves) <= 10, f"got {len(leaves)} leaves"
    # contracted edges carry a summed length
    a, b = next(iter(tree.edges))
    assert tree.edges[a, b]["length"] > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd <repo>/mcp_harness && \
  PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_mesh_to_tree.py::test_simplify_to_tree_yields_small_acyclic_tree -v
```
Expected: FAIL with `NotImplementedError`.

- [ ] **Step 3: Implement simplify_to_tree**

Replace the stub:
```python
def _contract_degree2(g: nx.Graph) -> nx.Graph:
    """Collapse every degree-2 chain into a single edge whose length is the sum."""
    h = g.copy()
    changed = True
    while changed:
        changed = False
        for n in list(h.nodes):
            if h.degree(n) == 2:
                (a, da), (b, db) = h[n].items()
                if a == b:
                    continue
                h.add_edge(a, b, length=da["length"] + db["length"])
                h.remove_node(n)
                changed = True
                break
    return h


def simplify_to_tree(skel: nx.Graph) -> nx.Graph:
    """Reduce a noisy curve skeleton to a small tree of tips + junctions.

    Iterates: contract degree-2 chains, then prune any leaf whose single edge is
    shorter than PRUNE_FRACTION * longest edge, until stable. Spanning-tree first
    guarantees acyclicity if the skeleton had loops.
    """
    tree = nx.minimum_spanning_tree(skel, weight="length")
    while True:
        tree = _contract_degree2(tree)
        if tree.number_of_edges() == 0:
            break
        longest = max(d["length"] for _, _, d in tree.edges(data=True))
        cutoff = PRUNE_FRACTION * longest
        twigs = [n for n in tree.nodes
                 if tree.degree(n) == 1
                 and next(iter(tree[n].values()))["length"] < cutoff]
        if not twigs:
            break
        tree.remove_nodes_from(twigs)
    return tree
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd <repo>/mcp_harness && \
  PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_mesh_to_tree.py::test_simplify_to_tree_yields_small_acyclic_tree -v
```
Expected: PASS. **If the leaf count is out of the 4–8 range, tune `PRUNE_FRACTION`**
(raise it to prune more aggressively, lower it to keep more limbs) and re-run.

- [ ] **Step 5: Commit**

```bash
cd <repo> && \
  git add mcp_harness/mesh_to_tree.py mcp_harness/tests/test_mesh_to_tree.py && \
  git commit -m "feat(mesh_to_tree): simplify_to_tree (prune + contract)"
```

---

## Task 6: detect_symmetry

**Files:**
- Modify: `mcp_harness/mesh_to_tree.py` (implement `detect_symmetry`)
- Test: `mcp_harness/tests/test_mesh_to_tree.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_mesh_to_tree.py`:
```python
def test_detect_symmetry_pairs_quadruped_legs():
    mesh = m2t.load_mesh(QUAD)
    tree = m2t.simplify_to_tree(m2t.extract_skeleton(mesh))
    pairs = m2t.detect_symmetry(tree, mesh)
    # a quadruped has at least the two leg pairs mirrored across the body axis
    assert len(pairs) >= 1
    # pairs reference leaf nodes only, and never pair a node with itself
    leaves = {n for n in tree.nodes if tree.degree(n) == 1}
    for a, b in pairs:
        assert a != b and a in leaves and b in leaves
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd <repo>/mcp_harness && \
  PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_mesh_to_tree.py::test_detect_symmetry_pairs_quadruped_legs -v
```
Expected: FAIL with `NotImplementedError`.

- [ ] **Step 3: Implement detect_symmetry**

Replace the stub:
```python
def detect_symmetry(tree: nx.Graph, mesh: trimesh.Trimesh) -> list[tuple[int, int]]:
    """Pair leaf nodes that reflect onto each other across the mesh's mirror plane.

    The bilateral plane is found via PCA of the mesh vertices: its normal is the
    axis of LEAST spread (the left-right axis), through the centroid. Two leaves
    pair if reflecting one across that plane lands near the other.
    """
    verts = mesh.vertices - mesh.centroid
    # principal axes; smallest-variance axis is the bilateral normal
    cov = np.cov(verts.T)
    eigvals, eigvecs = np.linalg.eigh(cov)
    normal = eigvecs[:, 0]                      # least-variance direction
    centroid = mesh.centroid
    scale = float(np.linalg.norm(mesh.extents))

    def reflect(p):
        d = np.dot(p - centroid, normal)
        return p - 2.0 * d * normal

    leaves = [n for n in tree.nodes if tree.degree(n) == 1]
    pos = {n: tree.nodes[n]["pos"] for n in leaves}
    pairs, used = [], set()
    for i, a in enumerate(leaves):
        if a in used:
            continue
        ra = reflect(pos[a])
        best, bestd = None, SYMMETRY_TOL * scale
        for b in leaves[i + 1:]:
            if b in used:
                continue
            d = float(np.linalg.norm(ra - pos[b]))
            if d < bestd:
                best, bestd = b, d
        if best is not None:
            pairs.append((a, best))
            used.add(a); used.add(best)
    return pairs
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd <repo>/mcp_harness && \
  PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_mesh_to_tree.py::test_detect_symmetry_pairs_quadruped_legs -v
```
Expected: PASS. **If zero pairs are found, raise `SYMMETRY_TOL`**; if it pairs
the wrong limbs, lower it.

- [ ] **Step 5: Commit**

```bash
cd <repo> && \
  git add mcp_harness/mesh_to_tree.py mcp_harness/tests/test_mesh_to_tree.py && \
  git commit -m "feat(mesh_to_tree): detect_symmetry via PCA mirror plane"
```

---

## Task 7: to_metric_tree

**Files:**
- Modify: `mcp_harness/mesh_to_tree.py` (implement `to_metric_tree`)
- Test: `mcp_harness/tests/test_mesh_to_tree.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_mesh_to_tree.py`:
```python
def test_to_metric_tree_is_valid_and_normalized():
    mesh = m2t.load_mesh(QUAD)
    tree = m2t.simplify_to_tree(m2t.extract_skeleton(mesh))
    sym = m2t.detect_symmetry(tree, mesh)
    nodes, pairs = m2t.to_metric_tree(tree, sym)

    # exactly one root, parent_id null
    roots = [n for n in nodes if n["parent_id"] is None]
    assert len(roots) == 1
    # parents precede children (build_tree_from_json requirement)
    seen = set()
    for n in nodes:
        if n["parent_id"] is not None:
            assert n["parent_id"] in seen
        seen.add(n["id"])
    # lengths positive on non-root edges; longest normalized to the packing target
    lens = [n["length"] for n in nodes if n["parent_id"] is not None]
    assert all(l > 0 for l in lens)
    assert abs(max(lens) - m2t.LONGEST_LIMB_TARGET) < 1e-6
    # symmetric pairs reference real node ids
    ids = {n["id"] for n in nodes}
    for a, b in pairs:
        assert a in ids and b in ids
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd <repo>/mcp_harness && \
  PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_mesh_to_tree.py::test_to_metric_tree_is_valid_and_normalized -v
```
Expected: FAIL with `NotImplementedError`.

- [ ] **Step 3: Implement to_metric_tree**

Replace the stub:
```python
def to_metric_tree(tree: nx.Graph, sym: list[tuple[int, int]]):
    """Emit (tree_nodes, symmetric_pairs) in the engine's Metric Tree format.

    Root = the graph-center interior node (min eccentricity). Nodes are numbered
    in BFS order from the root so parents precede children. Edge lengths are the
    contracted bone lengths, scaled so the longest == LONGEST_LIMB_TARGET (the
    measured packing regime); relative proportions are preserved.
    """
    # root: minimum-eccentricity node that is interior if possible
    ecc = nx.eccentricity(tree, weight="length")
    interior = [n for n in tree.nodes if tree.degree(n) > 1]
    root = min(interior or tree.nodes, key=lambda n: ecc[n])

    # normalization factor from the longest single edge
    longest = max(d["length"] for _, _, d in tree.edges(data=True))
    scale = LONGEST_LIMB_TARGET / longest

    # BFS numbering from root: original graph id -> sequential metric id
    order = list(nx.bfs_tree(tree, root).nodes)
    remap = {orig: i for i, orig in enumerate(order)}
    parent = nx.bfs_predecessors(tree, root)
    parent_of = {c: p for c, p in parent}

    nodes = []
    for orig in order:
        mid = remap[orig]
        if orig == root:
            nodes.append({"id": mid, "parent_id": None, "length": 0})
        else:
            p = parent_of[orig]
            length = round(tree.edges[orig, p]["length"] * scale, 6)
            nodes.append({"id": mid, "parent_id": remap[p], "length": length})

    pairs = [[remap[a], remap[b]] for a, b in sym
             if a in remap and b in remap]
    return nodes, pairs
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd <repo>/mcp_harness && \
  PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_mesh_to_tree.py::test_to_metric_tree_is_valid_and_normalized -v
```
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd <repo> && \
  git add mcp_harness/mesh_to_tree.py mcp_harness/tests/test_mesh_to_tree.py && \
  git commit -m "feat(mesh_to_tree): to_metric_tree (root, BFS order, normalize)"
```

---

## Task 8: mesh_to_metric_tree orchestrator + compiles end-to-end

**Files:**
- Modify: `mcp_harness/mesh_to_tree.py` (implement `mesh_to_metric_tree`)
- Test: `mcp_harness/tests/test_mesh_to_tree.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_mesh_to_tree.py`:
```python
def test_quadruped_mesh_compiles_to_foldable_base():
    import server
    nodes, pairs = m2t.mesh_to_metric_tree(QUAD)
    result = server.draft_and_compile_full_base(nodes, pairs)
    # the realistic path (incl. perturb-and-retry); a foldable base is non-ERROR FOLD
    assert not result.startswith("ERROR:"), result[:300]
    assert '"vertices_coords"' in result
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
cd <repo>/mcp_harness && \
  PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_mesh_to_tree.py::test_quadruped_mesh_compiles_to_foldable_base -v
```
Expected: FAIL with `NotImplementedError`.

- [ ] **Step 3: Implement the orchestrator**

Replace the stub:
```python
def mesh_to_metric_tree(path: str):
    """Full POC pipeline: mesh file -> (tree_nodes, symmetric_pairs)."""
    mesh = load_mesh(path)
    tree = simplify_to_tree(extract_skeleton(mesh))
    sym = detect_symmetry(tree, mesh)
    return to_metric_tree(tree, sym)
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
cd <repo>/mcp_harness && \
  PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_mesh_to_tree.py::test_quadruped_mesh_compiles_to_foldable_base -v
```
Expected: PASS. **If it returns ERROR**, the extracted proportions sit in a dead
zone; first confirm the tree is sane via `./.venv/bin/python mesh_to_tree.py
fixtures/quadruped.glb`, then adjust `LONGEST_LIMB_TARGET` toward 0.3 (the
template regime). A free-paper-frontier compile (non-ERROR FOLD) counts as PASS.

- [ ] **Step 5: Commit**

```bash
cd <repo> && \
  git add mcp_harness/mesh_to_tree.py mcp_harness/tests/test_mesh_to_tree.py && \
  git commit -m "feat(mesh_to_tree): orchestrator; quadruped mesh compiles end-to-end"
```

---

## Task 9: Add bird, humanoid, insect fixtures + body-plan validation

**Files:**
- Create: `mcp_harness/fixtures/bird.glb`, `humanoid.glb`, `insect.glb`
- Modify: `mcp_harness/fixtures/SOURCES.md`
- Modify: `mcp_harness/tests/test_mesh_to_tree.py`

- [ ] **Step 1: Source the three CC0 meshes**

Download CC0 `.glb` meshes (same sources as Task 2): a bird, a humanoid/biped, and
an insect (6-legged — try Poly Pizza "ant"/"beetle"). Decimate to ≤ ~2000 faces as
in Task 2. Save as `fixtures/bird.glb`, `fixtures/humanoid.glb`,
`fixtures/insect.glb`. Add their rows to `fixtures/SOURCES.md`.

- [ ] **Step 2: Write the parametrized body-plan test**

Append to `tests/test_mesh_to_tree.py`:
```python
import pytest

# expected leaf count vs the hand-made templates (faithfulness yardstick), and
# whether packability is expected (insect is the known fragile edge -> not required)
BODY_PLANS = [
    # name,        file,            min_leaves, max_leaves, expect_pack
    ("quadruped",  "quadruped.glb", 6, 10, True),
    ("bird",       "bird.glb",      4, 8, True),
    ("humanoid",   "humanoid.glb",  3, 6, True),
    ("insect",     "insect.glb",    5, 9, False),
]


@pytest.mark.parametrize("name,fname,lo,hi,expect_pack", BODY_PLANS)
def test_body_plan_extraction_faithful_and_compiles(name, fname, lo, hi, expect_pack):
    import server
    path = os.path.join(HERE, "fixtures", fname)
    nodes, pairs = m2t.mesh_to_metric_tree(path)
    leaves = [n for n in nodes
              if all(o["parent_id"] != n["id"] for o in nodes) and n["parent_id"] is not None]
    assert lo <= len(leaves) <= hi, f"{name}: {len(leaves)} leaves outside [{lo},{hi}]"
    assert len(pairs) >= 1, f"{name}: no symmetry pairs"
    result = server.draft_and_compile_full_base(nodes, pairs)
    if expect_pack:
        assert not result.startswith("ERROR:"), f"{name}: {result[:200]}"
    # insect: extraction faithfulness asserted above; compile outcome only recorded
```

- [ ] **Step 3: Run the full POC test suite**

Run:
```bash
cd <repo>/mcp_harness && \
  PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_mesh_to_tree.py -v
```
Expected: all PASS. **Per-fixture tuning is expected** — if bird/humanoid leaf
counts fall outside range, tune `PRUNE_FRACTION`; if they don't compile, nudge
`LONGEST_LIMB_TARGET`. Insect need not compile.

- [ ] **Step 4: Add the headline summary demo**

Append to `mesh_to_tree.py`, replacing the `__main__` block:
```python
def _summary_table():
    """Print the POC headline: per body plan, leaf count + compile outcome."""
    import os, server
    here = os.path.dirname(os.path.abspath(__file__))
    print(f"{'body plan':12} {'leaves':>7} {'pairs':>6} {'compile':>10}")
    for name in ("quadruped", "bird", "humanoid", "insect"):
        path = os.path.join(here, "fixtures", f"{name}.glb")
        nodes, pairs = mesh_to_metric_tree(path)
        leaves = sum(1 for n in nodes if n["parent_id"] is not None
                     and all(o["parent_id"] != n["id"] for o in nodes))
        r = server.draft_and_compile_full_base(nodes, pairs)
        outcome = "ERROR" if r.startswith("ERROR:") else "FOLD"
        print(f"{name:12} {leaves:>7} {len(pairs):>6} {outcome:>10}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        nodes, pairs = mesh_to_metric_tree(sys.argv[1])
        print("nodes:", nodes); print("pairs:", pairs)
    else:
        _summary_table()
```

- [ ] **Step 5: Run the headline demo**

Run:
```bash
cd <repo>/mcp_harness && \
  PYTHONPATH=. ./.venv/bin/python mesh_to_tree.py 2>&1 | grep -v "Processing request"
```
Expected: a 4-row table; quadruped/bird/humanoid show `FOLD`, insect may show `ERROR`.

- [ ] **Step 6: Confirm the full repo suite still passes**

Run:
```bash
cd <repo>/mcp_harness && \
  PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/ -q 2>&1 | tail -3
```
Expected: all green (the 42 existing + the new mesh_to_tree tests).

- [ ] **Step 7: Commit**

```bash
cd <repo> && \
  git add mcp_harness/fixtures/ mcp_harness/tests/test_mesh_to_tree.py mcp_harness/mesh_to_tree.py && \
  git commit -m "feat(mesh_to_tree): bird/humanoid/insect fixtures + body-plan validation table"
```

---

## Task 10: Clean up the spike

**Files:**
- Delete: `mcp_harness/spike_skeletor.py`

- [ ] **Step 1: Remove the throwaway spike**

Run:
```bash
cd <repo> && rm -f mcp_harness/spike_skeletor.py
```

- [ ] **Step 2: Confirm nothing references it, suite still green**

Run:
```bash
cd <repo>/mcp_harness && \
  PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_mesh_to_tree.py -q 2>&1 | tail -3
```
Expected: PASS.

- [ ] **Step 3: Commit if anything changed**

```bash
cd <repo> && \
  git add -A && git commit -m "chore: remove mesh_to_tree skeletor spike" || echo "nothing to commit"
```

---

## Notes for the implementer

- **The empirical parts are Tasks 4–8.** Skeletonization quality and the three
  constants (`PRUNE_FRACTION`, `SYMMETRY_TOL`, `LONGEST_LIMB_TARGET`) are expected
  to need tuning against the real meshes. The tests assert *structural properties*
  (ranges, validity), not exact values, precisely so tuning stays inside the test.
- **A free-paper-frontier compile is success** (non-ERROR FOLD), consistent with
  the rest of the system. Only an `ERROR:` string is a packability failure.
- **Insect is expected to be faithful but may not pack** — that is the known
  TreeMaker fragile-edge limit, not a POC bug.
- If `skeletor` proves too noisy on a fixture even after tuning `PRUNE_FRACTION`,
  the spec's documented fallback is a geodesic-extremity heuristic for that mesh —
  but exhaust pruning-threshold tuning first.
