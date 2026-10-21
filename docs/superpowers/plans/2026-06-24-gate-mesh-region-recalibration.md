# Gate Mesh-Region Recalibration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make mesh-derived Metric Trees in-distribution for the Tier 2.5 feasibility gate by adding a synthetic `mesh_like` family to the corpus, validated against the 5 real fixtures as a held-out set.

**Architecture:** A new `mesh_like` generator family (small anatomy topologies normalized like `mesh_to_tree` output) is mixed into the corpus via a `mesh_like_frac` knob; `build_dataset` gains an `id_offset` so a labeled mesh-like batch can be appended to the committed `corpus_wide.jsonl` without regenerating it. A held-out validation test trains the gate from the updated corpus and asserts the 5 fixtures are no longer OOD and not rejected.

**Tech Stack:** Python 3.14, `scikit-learn` (RandomForest + k-NN via existing `feasibility/`), `pytest`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-06-24-gate-mesh-region-recalibration-design.md`.
- `LONGEST_LIMB_TARGET = 0.40` — must match `mesh_to_tree.LONGEST_LIMB_TARGET` (the normalization target that defines the mesh slice).
- The `mesh_like` family MUST straddle the packable frontier (vary limb count + lengths) so the labeled slice carries a pack/no-pack mix, not all-pack.
- The 5 fixtures are VALIDATION ONLY — never added to the training corpus (avoid circularity). Pass criterion: each fixture `ood == False` AND `verdict != "infeasible"` under a gate trained from the updated corpus.
- No regression: `train_model.fit(...)["val_recall_feasible"]` on the updated corpus must stay `>= 0.95` (the block threshold is tuned to `target_recall=0.98`, so a large drop signals corpus damage).
- Append, don't regenerate: the existing 2000 rows (ids 0–1999) stay; the mesh-like batch is appended at `id_offset=2000`.
- Existing `feasibility.gate.Gate.predict(nodes, pairs) -> {"verdict","p_pack","ood","ood_score","reason"}`; `train_model.fit(corpus_path, out_path, ...) -> dict` with key `val_recall_feasible`.
- Run tests from `mcp_harness/` with the venv: `cd <repo>/mcp_harness && .venv/bin/python -m pytest ...` (CWD = `mcp_harness/`; tests import `from feasibility import ...` and `import mesh_to_tree`).
- Commit messages end with: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

---

### Task 1: `mesh_like` generator family

**Files:**
- Modify: `mcp_harness/feasibility/tree_generator.py`
- Test: `mcp_harness/tests/test_tree_generator.py` (append)

**Interfaces:**
- Consumes: existing `_node`, `_len`, `_leaves`, `_pair_leaves` in `tree_generator.py`.
- Produces:
  - `LONGEST_LIMB_TARGET = 0.40` (module constant).
  - `_normalize_longest(nodes, target=LONGEST_LIMB_TARGET) -> nodes` — scales every edge so the longest equals `target` (in place; returns `nodes`).
  - `mesh_like(rng) -> (nodes, pairs)` — a small anatomy tree (4–8 leaves, bilateral pairs) normalized so the longest edge `== LONGEST_LIMB_TARGET`; frontier-straddling across seeds.

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_tree_generator.py`:

```python
import random

import feasibility.tree_generator as tg


def _leaf_ids(nodes):
    children = {n["parent_id"] for n in nodes[1:]}
    return [n["id"] for n in nodes if n["id"] not in children]


def test_mesh_like_is_valid_and_normalized():
    rng = random.Random(0)
    for _ in range(200):
        nodes, pairs = tg.mesh_like(rng)
        # structurally valid: one root, each child's parent is an earlier id
        roots = [n for n in nodes if n["parent_id"] is None]
        assert len(roots) == 1 and roots[0]["id"] == 0
        for n in nodes:
            if n["parent_id"] is not None:
                assert n["parent_id"] < n["id"]
        # longest edge normalized to the mesh target
        edge_lens = [n["length"] for n in nodes if n["parent_id"] is not None]
        assert abs(max(edge_lens) - tg.LONGEST_LIMB_TARGET) < 1e-9
        # mesh-range leaf count
        assert 4 <= len(_leaf_ids(nodes)) <= 8
        # pairs reference distinct leaf ids
        leaves = set(_leaf_ids(nodes))
        for a, b in pairs:
            assert a != b and a in leaves and b in leaves


def test_mesh_like_straddles_the_frontier_by_construction():
    """Across seeds the family must vary in size and total edge length, so that
    labeling yields a pack/no-pack mix rather than all-pack (a proxy checked here
    without invoking the compiler; the real mix is asserted at corpus-build time)."""
    rng = random.Random(1)
    leaf_counts, total_lens = set(), set()
    for _ in range(200):
        nodes, _ = tg.mesh_like(rng)
        leaf_counts.add(len(_leaf_ids(nodes)))
        total_lens.add(round(sum(n["length"] for n in nodes if n["parent_id"] is not None), 3))
    assert len(leaf_counts) >= 3          # spans several flap counts
    assert min(leaf_counts) <= 5 and max(leaf_counts) >= 7
    assert len(total_lens) >= 20          # wide spread of total limb length
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_tree_generator.py -k mesh_like -q`
Expected: FAIL with `AttributeError: module 'feasibility.tree_generator' has no attribute 'mesh_like'`

- [ ] **Step 3: Write minimal implementation**

In `mcp_harness/feasibility/tree_generator.py`, add after the `_LEN_LO, _LEN_HI` block:

```python
LONGEST_LIMB_TARGET = 0.40   # match mesh_to_tree.LONGEST_LIMB_TARGET
```

Add these functions after `random_tree` (before `_ARCHETYPES`):

```python
def _normalize_longest(nodes, target: float = LONGEST_LIMB_TARGET):
    """Scale every edge so the longest equals target -- the post-step that
    mesh_to_tree.to_metric_tree applies, and the dominant driver of the mesh
    feature-space slice."""
    longest = max(n["length"] for n in nodes if n["parent_id"] is not None)
    scale = target / longest
    for n in nodes:
        if n["parent_id"] is not None:
            n["length"] = round(n["length"] * scale, 6)
    return nodes


def _mesh_spine(rng: random.Random):
    """Small spine-with-limbs: 2-3 hubs, 1-3 limbs each."""
    n_hubs = rng.randint(2, 3)
    nodes = [_node(0, None, 0)]
    hub_ids = [0]
    for _ in range(n_hubs - 1):
        nid = len(nodes)
        nodes.append(_node(nid, hub_ids[-1], _len(rng)))
        hub_ids.append(nid)
    same_hub = []
    for hub in hub_ids:
        limbs = []
        for _ in range(rng.randint(1, 3)):
            nid = len(nodes)
            nodes.append(_node(nid, hub, _len(rng)))
            limbs.append(nid)
        same_hub.append(limbs)
    leaves = set(_leaves(nodes))
    pairs = []
    for limbs in same_hub:
        ls = [l for l in limbs if l in leaves]
        for i in range(0, len(ls) - 1, 2):
            pairs.append([ls[i], ls[i + 1]])
    return nodes, pairs


def _mesh_radial(rng: random.Random):
    """Small radial: 4-8 single-edge limbs off the root (high end straddles into
    the crowded/over-packed regime)."""
    n_limbs = rng.randint(4, 8)
    nodes = [_node(0, None, 0)]
    for i in range(1, n_limbs + 1):
        nodes.append(_node(i, 0, _len(rng)))
    pairs = _pair_leaves(nodes, rng, max_pairs=n_limbs // 2)
    return nodes, pairs


def mesh_like(rng: random.Random):
    """Mimic mesh_to_tree extraction output: a small anatomy tree (4-8 leaves,
    bilateral pairs) with the longest edge normalized to LONGEST_LIMB_TARGET and
    the rest proportionally smaller -- the structured slice real meshes occupy.
    Rejection-samples until the leaf count lands in the mesh window."""
    nodes, pairs = _mesh_radial(rng)
    for _ in range(20):
        if 4 <= len(_leaves(nodes)) <= 8:
            break
        nodes, pairs = rng.choice((_mesh_spine, _mesh_radial))(rng)
    return _normalize_longest(nodes), pairs
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_tree_generator.py -k mesh_like -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/feasibility/tree_generator.py mcp_harness/tests/test_tree_generator.py
git commit -m "$(printf 'feat(feasibility): mesh_like generator family for the mesh slice\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

### Task 2: Mix `mesh_like` into `generate` + append support in `build_dataset`

**Files:**
- Modify: `mcp_harness/feasibility/tree_generator.py` (`generate`)
- Modify: `mcp_harness/feasibility/build_dataset.py` (`build_corpus` + CLI)
- Test: `mcp_harness/tests/test_tree_generator.py`, `mcp_harness/tests/test_feasibility_dataset.py` (append)

**Interfaces:**
- Consumes: `mesh_like` (Task 1); existing `build_corpus`, `tg.generate`, `tl.label`, `tl.perturb_label`, `ds.existing_ids`, `ds.append_row`.
- Produces:
  - `generate(n, anchored_frac=0.7, seed=0, mesh_like_frac=0.0)` — now yields `round(mesh_like_frac*n)` rows tagged source `"mesh_like"` (after the anchored block, before random). New param appended last for backward compatibility.
  - `build_corpus(n, seed, out_path, anchored_frac=0.7, workers=4, perturb_sample=50, mesh_like_frac=0.0, id_offset=0)` — assigns ids `id_offset + i`, skips ids already in the file, threads `mesh_like_frac` into `generate`. New params appended last.
  - CLI flags `--mesh-like-frac` (float, default 0.0) and `--id-offset` (int, default 0).

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_tree_generator.py`:

```python
def test_generate_emits_requested_mesh_like_fraction():
    rows = list(tg.generate(100, anchored_frac=0.5, seed=0, mesh_like_frac=0.3))
    from collections import Counter
    counts = Counter(src for src, _, _ in rows)
    assert counts["mesh_like"] == 30
    assert counts["anchored"] == 50
    assert counts["random"] == 20
```

Append to `mcp_harness/tests/test_feasibility_dataset.py`:

```python
def test_build_corpus_id_offset_appends_mesh_like_without_collision(tmp_path, monkeypatch):
    import feasibility.tree_labeler as tl
    import feasibility.build_dataset as bd
    monkeypatch.setattr(tl, "label", lambda nodes, pairs: (True, "none"))
    monkeypatch.setattr(tl, "perturb_label", lambda nodes, pairs: None)
    path = str(tmp_path / "corpus.jsonl")

    s1 = bd.build_corpus(n=3, seed=1, out_path=path, anchored_frac=0.0,
                         mesh_like_frac=1.0, perturb_sample=0, id_offset=2000)
    import feasibility.dataset as ds
    rows = ds.read_rows(path)
    assert {r["id"] for r in rows} == {2000, 2001, 2002}
    assert all(r["source"] == "mesh_like" for r in rows)
    assert s1["added"] == 3

    # re-running with the same offset is a no-op (ids already present)
    s2 = bd.build_corpus(n=3, seed=1, out_path=path, anchored_frac=0.0,
                         mesh_like_frac=1.0, perturb_sample=0, id_offset=2000)
    assert s2["added"] == 0
    assert len(ds.read_rows(path)) == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_tree_generator.py::test_generate_emits_requested_mesh_like_fraction tests/test_feasibility_dataset.py::test_build_corpus_id_offset_appends_mesh_like_without_collision -q`
Expected: FAIL — `generate()` has no `mesh_like_frac` (TypeError) / `build_corpus()` has no `id_offset` (TypeError).

- [ ] **Step 3: Write minimal implementation**

In `tree_generator.py`, replace `generate`:

```python
def generate(n: int, anchored_frac: float = 0.7, seed: int = 0,
             mesh_like_frac: float = 0.0):
    """Yield n (source, nodes, pairs) triples deterministically for `seed`.

    Order: round(anchored_frac*n) 'anchored' (archetype family), then
    round(mesh_like_frac*n) 'mesh_like' (the mesh-region slice), then the rest
    'random'.
    """
    rng = random.Random(seed)
    n_anchored = round(anchored_frac * n)
    n_mesh = round(mesh_like_frac * n)
    for i in range(n):
        if i < n_anchored:
            nodes, pairs = rng.choice(_ARCHETYPES)(rng)
            yield "anchored", nodes, pairs
        elif i < n_anchored + n_mesh:
            yield "mesh_like", *mesh_like(rng)
        else:
            yield "random", *random_tree(rng)
```

In `build_dataset.py`, change the `build_corpus` signature and the `todo`/id lines:

```python
def build_corpus(n, seed, out_path, anchored_frac=0.7, workers=4,
                 perturb_sample=50, mesh_like_frac=0.0, id_offset=0):
```

Replace the `todo` comprehension and the id assignment:

```python
    done = ds.existing_ids(out_path)
    todo = [(id_offset + i, item)
            for i, item in enumerate(
                tg.generate(n, anchored_frac, seed, mesh_like_frac=mesh_like_frac))
            if (id_offset + i) not in done]

    new_rows = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for (gid, _item), row in zip(todo, pool.map(_label_one, (it for _, it in todo))):
            row["id"] = gid
            new_rows.append(row)
```

Add the two CLI args in `__main__` and pass them through:

```python
    ap.add_argument("--mesh-like-frac", type=float, default=0.0)
    ap.add_argument("--id-offset", type=int, default=0)
    a = ap.parse_args()
    _report(build_corpus(a.n, a.seed, a.out, a.anchored_frac, a.workers,
                         a.perturb_sample, mesh_like_frac=a.mesh_like_frac,
                         id_offset=a.id_offset))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_tree_generator.py tests/test_feasibility_dataset.py -q`
Expected: PASS (all existing dataset/generator tests + the 2 new).

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/feasibility/tree_generator.py mcp_harness/feasibility/build_dataset.py mcp_harness/tests/test_tree_generator.py mcp_harness/tests/test_feasibility_dataset.py
git commit -m "$(printf 'feat(feasibility): mesh_like_frac in generate + id_offset append in build_corpus\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

### Task 3: Build the mesh-region corpus + held-out validation

**Files:**
- Create: `mcp_harness/tests/fixtures/mesh_validation_trees.json` (generated)
- Modify: `mcp_harness/feasibility/corpus_wide.jsonl` (append 300 mesh-like rows)
- Test: `mcp_harness/tests/test_gate_mesh_region.py` (create)

**Interfaces:**
- Consumes: `mesh_to_tree.mesh_to_metric_tree`, `feasibility.train_model.fit`, `feasibility.gate.load`, the Task 1/2 generator+append path.
- Produces: a committed updated corpus and a validation test proving the 5 fixtures are in-distribution.

- [ ] **Step 1: Generate the held-out validation fixtures (the 5 real trees)**

Run from `mcp_harness/` (slow — skeletonizes 5 meshes, ~1–2 min):

```bash
cd <repo>/mcp_harness && mkdir -p tests/fixtures && .venv/bin/python -c "
import json, os, mesh_to_tree as m2t
cfg = {'quadruped':(96,0.55),'humanoid':(96,0.20),'fish':(64,0.40),'bird':(96,0.25),'insect':(96,0.55)}
out = {}
for name,(vox,prune) in cfg.items():
    nodes, pairs = m2t.mesh_to_metric_tree(os.path.join('fixtures', name+'.glb'), voxel_res=vox, prune_fraction=prune)
    out[name] = {'nodes': nodes, 'pairs': pairs}
json.dump(out, open('tests/fixtures/mesh_validation_trees.json','w'), indent=2)
print('wrote', len(out), 'validation trees')
"
```
Expected: `wrote 5 validation trees`

- [ ] **Step 2: Write the validation test (will fail against the current corpus)**

Create `mcp_harness/tests/test_gate_mesh_region.py`:

```python
"""Held-out validation: after adding the mesh_like family to the corpus, the 5
real mesh fixtures must be in-distribution (ood == False) and not rejected. The
fixtures are NEVER training data -- passing proves the synthetic slice generalizes
to real extraction output. See the 2026-06-24 design spec."""
import json
import os

import pytest

from feasibility import gate as gatemod
from feasibility import train_model

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # mcp_harness/
CORPUS = os.path.join(HERE, "feasibility", "corpus_wide.jsonl")
TREES = os.path.join(HERE, "tests", "fixtures", "mesh_validation_trees.json")


@pytest.fixture(scope="module")
def trained(tmp_path_factory):
    """Train a gate from the committed corpus into a temp artifact (a few seconds)."""
    art = str(tmp_path_factory.mktemp("gate") / "gate.joblib")
    report = train_model.fit(CORPUS, art)
    return gatemod.load(art), report


def test_mesh_fixtures_are_in_distribution(trained):
    gate, _ = trained
    trees = json.load(open(TREES))
    assert set(trees) == {"quadruped", "humanoid", "fish", "bird", "insect"}
    for name, t in trees.items():
        r = gate.predict(t["nodes"], t["pairs"])
        assert r["ood"] is False, f"{name} still OOD: {r}"
        assert r["verdict"] != "infeasible", f"{name} rejected as infeasible: {r}"


def test_no_recall_regression(trained):
    _, report = trained
    # block threshold is tuned to target_recall=0.98; a large drop signals the
    # mesh_like rows damaged the corpus.
    assert report["val_recall_feasible"] >= 0.95, report
```

- [ ] **Step 3: Run the validation test against the CURRENT corpus — confirm it fails on OOD**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_gate_mesh_region.py -q`
Expected: `test_mesh_fixtures_are_in_distribution` FAILS — fixtures assert `r["ood"] is False` but they are still OOD (`compile_anyway`) because the corpus has no mesh_like rows yet. (This reproduces the documented problem.) Note the printed `val_recall_feasible` baseline from `test_no_recall_regression` (it should pass) for the before/after record.

- [ ] **Step 4: Append the mesh-like batch to the committed corpus**

Run from `mcp_harness/` (slow — labels 300 trees via real compile; resumable):

```bash
cd <repo>/mcp_harness && .venv/bin/python -m feasibility.build_dataset -n 300 --seed 1 --out feasibility/corpus_wide.jsonl --anchored-frac 0 --mesh-like-frac 1.0 --id-offset 2000 --perturb-sample 0
```
Expected report line shows `added=300` and `by source` now includes `mesh_like: 300` (total 2300). If interrupted, re-run the same command — it resumes (ids 2000–2299 already written are skipped).

- [ ] **Step 5: Re-run the validation test — confirm it passes**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_gate_mesh_region.py -q`
Expected: PASS (2 passed). All 5 fixtures now `ood == False` and `verdict != "infeasible"`; `val_recall_feasible >= 0.95`. Record the new `val_recall_feasible` for the before/after note.

If any fixture is still OOD: the mesh_like slice did not land close enough to that fixture. Inspect its `ood_score` vs `ood_threshold`, and increase the batch size (e.g. `-n 500`) or widen `_mesh_spine`/`_mesh_radial` size ranges so the slice covers it; re-run Steps 4–5. Do NOT add the fixtures to the corpus to force a pass.

- [ ] **Step 6: Refresh the local stale gate artifact (so local dev uses the new corpus)**

The on-disk `feasibility/gate.joblib` is gitignored and is NOT auto-retrained while it exists. Remove it so `_default_gate` retrains from the updated corpus on next use:

```bash
rm -f <repo>/mcp_harness/feasibility/gate.joblib
```

- [ ] **Step 7: Commit corpus + fixtures + test**

```bash
git add mcp_harness/feasibility/corpus_wide.jsonl mcp_harness/tests/fixtures/mesh_validation_trees.json mcp_harness/tests/test_gate_mesh_region.py
git commit -m "$(printf 'feat(feasibility): add mesh_like rows to corpus; mesh fixtures now in-distribution\n\nAppends 300 labeled mesh_like trees (ids 2000-2299) to corpus_wide.jsonl so the\ngate stops flagging real meshes OOD. Held-out validation over the 5 fixtures:\nall ood==False and not infeasible; val_recall_feasible unchanged.\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

## Self-Review

**Spec coverage:**
- `mesh_like` family (normalized to 0.40, small size, bilateral pairs) → Task 1. ✓
- Frontier-straddling → Task 1 proxy test + Task 3 Step 4 real pack/no-pack mix in `by source` report. ✓
- Mixed at a guaranteed fraction (`mesh_like_frac`) → Task 2. ✓
- Append, don't regenerate (id_offset, preserve 2000 rows) → Task 2 + Task 3 Step 4. ✓
- Stored mesh-tree fixtures (constants 96/0.55, 96/0.20, 64/0.40, 96/0.25, 96/0.55) → Task 3 Step 1. ✓
- Pass criterion (`ood==False` AND `verdict != "infeasible"`) → Task 3 Step 2 `test_mesh_fixtures_are_in_distribution`. ✓
- Held-out, not trained on → fixtures live in `tests/fixtures/`, never appended to the corpus; Task 3 Step 5 note forbids it. ✓
- No-regression on `val_recall_feasible` → Task 3 `test_no_recall_regression` (>= 0.95). ✓
- Updated corpus committed; gate.joblib stays gitignored, train-on-demand → Task 3 Steps 6–7. ✓
- Before/after baseline recorded → Task 3 Steps 3 and 5 capture the metric. ✓

**Placeholder scan:** No TBD/TODO; every code/command step is complete. Task 3 Step 5's remediation branch gives concrete actions, not a placeholder. ✓

**Type consistency:** `generate(n, anchored_frac, seed, mesh_like_frac)` and `build_corpus(..., mesh_like_frac, id_offset)` signatures match between Task 2's definition and Task 3's CLI call; source tag `"mesh_like"`, fixture keys `{nodes,pairs}`, and `gate.predict` keys (`ood`, `verdict`) are consistent across tasks. `LONGEST_LIMB_TARGET` used in Task 1 matches the spec's 0.40. ✓
