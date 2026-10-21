# Tree-Feasibility Data Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a resumable pipeline that generates synthetic Metric Trees, brute-force labels each through the existing compiler, and writes a streamable JSONL dataset — bootstrapping training data for the future `predict_tree_feasibility` model (CLAUDE.md §6, phase 1).

**Architecture:** Four small modules in a new `mcp_harness/feasibility/` package. A hybrid **generator** (procedural archetype families + random trees) feeds a **labeler** that wraps the crash-safe `tests/runner.compile_tree` primitive (each compile already runs in an isolated spawned subprocess, so SIGSEGV/hang become labels). A **dataset** module handles JSONL write/read + cheap feature extraction. A **build orchestrator** parallelizes labeling with a `ThreadPoolExecutor` over `compile_tree` (threads orchestrate; the real work and crash-isolation live in the spawned children), is resumable by id, and prints a class-mix health report. Model training and the MCP tool are out of scope.

**Tech Stack:** Python 3.14 (`mcp_harness/.venv`), `networkx`/`numpy` (already deps), stdlib `concurrent.futures`, `json`, `random`. Tests via `pytest`. The existing `headless_treemaker` engine `.so` and `tests/runner.py` / `server.py` are reused, not modified.

**Import/run contract (from the codebase):** Run everything from `mcp_harness/` with `PYTHONPATH=.:tests`. Modules import flat (`runner`, `server`, `cases`); the new package imports as `from feasibility import ...` because `mcp_harness/` is on the path.

---

## File Structure

- Create: `mcp_harness/feasibility/__init__.py` — empty package marker.
- Create: `mcp_harness/feasibility/tree_generator.py` — hybrid sampler (archetypes + random).
- Create: `mcp_harness/feasibility/dataset.py` — feature extraction + JSONL write/read/resume.
- Create: `mcp_harness/feasibility/tree_labeler.py` — `label()` + `perturb_label()` over the compiler.
- Create: `mcp_harness/feasibility/build_dataset.py` — CLI orchestrator (parallel, resumable, class-mix report).
- Create: `mcp_harness/tests/test_tree_generator.py` — generator validity/determinism tests.
- Create: `mcp_harness/tests/test_feasibility_dataset.py` — feature + JSONL round-trip/resume tests.
- Create: `mcp_harness/tests/test_tree_labeler.py` — taxonomy/labeling tests (uses the engine).

---

## Task 1: Package scaffold + generator skeleton

**Files:**
- Create: `mcp_harness/feasibility/__init__.py`
- Create: `mcp_harness/feasibility/tree_generator.py`
- Test: `mcp_harness/tests/test_tree_generator.py`

- [ ] **Step 1: Create the empty package marker**

Create `mcp_harness/feasibility/__init__.py` with a single line:

```python
"""Tier 2.5 tree-feasibility data pipeline (CLAUDE.md §6, phase 1)."""
```

- [ ] **Step 2: Write the failing test for structural validity helpers**

Create `mcp_harness/tests/test_tree_generator.py`:

```python
"""Generator emits only structurally valid Metric Trees, deterministically."""
import sys
sys.path.insert(0, "tests")

from feasibility import tree_generator as tg


def _assert_valid_tree(nodes, pairs):
    assert nodes, "empty tree"
    assert nodes[0]["parent_id"] is None and nodes[0]["length"] == 0, "bad root"
    ids = {n["id"] for n in nodes}
    assert ids == set(range(len(nodes))), "ids must be 0..n-1 contiguous"
    for n in nodes[1:]:
        assert n["parent_id"] is not None, "non-root needs a parent"
        assert n["parent_id"] < n["id"], "parent must precede child"
        assert n["length"] > 0, "non-root edge must be positive"
    children = {n["parent_id"] for n in nodes[1:]}
    leaves = {n["id"] for n in nodes} - children
    for a, b in pairs:
        assert a in leaves and b in leaves, "symmetry pairs must be leaves"
        assert a != b, "cannot pair a node with itself"


def test_radial_is_valid_and_has_expected_leaves():
    import random
    nodes, pairs = tg.radial(random.Random(0))
    _assert_valid_tree(nodes, pairs)
    # radial = all limbs hang off the root
    assert all(n["parent_id"] == 0 for n in nodes[1:])
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_tree_generator.py -v`
Expected: FAIL — `AttributeError: module 'feasibility.tree_generator' has no attribute 'radial'` (module is empty).

- [ ] **Step 4: Implement the `radial` archetype + shared helpers**

Create `mcp_harness/feasibility/tree_generator.py`:

```python
"""Hybrid synthetic Metric-Tree sampler: procedural archetype families plus
unstructured random trees. Every emitted tree is structurally valid by
construction (root parent_id=None/length 0; each child's parent_id < its id;
symmetry pairs reference distinct leaf nodes). See the design spec."""
from __future__ import annotations
import random

# Edge lengths are sampled in a regime that straddles the packable frontier --
# we WANT a mix of pack / no-pack so the dataset is informative.
_LEN_LO, _LEN_HI = 0.12, 0.55


def _len(rng: random.Random) -> float:
    return round(rng.uniform(_LEN_LO, _LEN_HI), 6)


def _node(i, parent, length):
    return {"id": i, "parent_id": parent, "length": length}


def _leaves(nodes):
    children = {n["parent_id"] for n in nodes[1:]}
    return [n["id"] for n in nodes if n["id"] not in children]


def _pair_leaves(nodes, rng, max_pairs):
    """Pair up distinct leaves into symmetry pairs (at most max_pairs)."""
    leaves = _leaves(nodes)
    rng.shuffle(leaves)
    pairs = []
    for i in range(0, len(leaves) - 1, 2):
        if len(pairs) >= max_pairs:
            break
        pairs.append([leaves[i], leaves[i + 1]])
    return pairs


def radial(rng: random.Random):
    """Star / insect / many-tentacle: n_limbs single-edge limbs off one root."""
    n_limbs = rng.randint(3, 8)
    nodes = [_node(0, None, 0)]
    for i in range(1, n_limbs + 1):
        nodes.append(_node(i, 0, _len(rng)))
    pairs = _pair_leaves(nodes, rng, max_pairs=n_limbs // 2)
    return nodes, pairs
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_tree_generator.py -v`
Expected: PASS (both tests).

- [ ] **Step 6: Commit**

```bash
cd <repo>
git add mcp_harness/feasibility/__init__.py mcp_harness/feasibility/tree_generator.py mcp_harness/tests/test_tree_generator.py
git commit -m "feat(feasibility): package scaffold + radial archetype generator"
```

---

## Task 2: Remaining archetype families + random + `generate`

**Files:**
- Modify: `mcp_harness/feasibility/tree_generator.py`
- Test: `mcp_harness/tests/test_tree_generator.py`

- [ ] **Step 1: Add failing tests for the other families, random, and `generate`**

Append to `mcp_harness/tests/test_tree_generator.py`:

```python
def test_spine_with_limbs_is_valid():
    import random
    nodes, pairs = tg.spine_with_limbs(random.Random(1))
    _assert_valid_tree(nodes, pairs)
    assert len(nodes) >= 4  # a spine plus at least one limb


def test_branching_is_valid():
    import random
    nodes, pairs = tg.branching(random.Random(2))
    _assert_valid_tree(nodes, pairs)


def test_random_tree_is_valid():
    import random
    for seed in range(20):
        nodes, pairs = tg.random_tree(random.Random(seed))
        _assert_valid_tree(nodes, pairs)


def test_generate_is_deterministic_and_respects_anchored_frac():
    a = list(tg.generate(50, anchored_frac=0.7, seed=123))
    b = list(tg.generate(50, anchored_frac=0.7, seed=123))
    assert a == b, "same seed must reproduce the same corpus"
    sources = [src for src, _, _ in a]
    assert sources.count("anchored") == 35  # round(0.7 * 50)
    assert sources.count("random") == 15
    for _src, nodes, pairs in a:
        _assert_valid_tree(nodes, pairs)
```

- [ ] **Step 2: Run to verify the new tests fail**

Run: `cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_tree_generator.py -v`
Expected: the 4 new tests FAIL (`spine_with_limbs`/`branching`/`random_tree`/`generate` undefined); the Task-1 tests still PASS.

- [ ] **Step 3: Implement the remaining families, `random_tree`, and `generate`**

Append to `mcp_harness/feasibility/tree_generator.py`:

```python
def spine_with_limbs(rng: random.Random):
    """Quadruped / centipede / humanoid: a chain of hubs, each sprouting limbs.

    Limbs sharing a hub are paired as bilateral symmetry where two are present.
    """
    n_hubs = rng.randint(2, 4)
    nodes = [_node(0, None, 0)]
    hub_ids = [0]
    # Build the spine as a chain off the root.
    for _ in range(n_hubs - 1):
        nid = len(nodes)
        nodes.append(_node(nid, hub_ids[-1], _len(rng)))
        hub_ids.append(nid)
    # Sprout limbs from each hub; remember which limbs share a hub (for pairing).
    same_hub = []
    for hub in hub_ids:
        limbs_here = []
        for _ in range(rng.randint(1, 3)):
            nid = len(nodes)
            nodes.append(_node(nid, hub, _len(rng)))
            limbs_here.append(nid)
        same_hub.append(limbs_here)
    leaves = set(_leaves(nodes))
    pairs = []
    for limbs_here in same_hub:
        ls = [l for l in limbs_here if l in leaves]
        for i in range(0, len(ls) - 1, 2):
            pairs.append([ls[i], ls[i + 1]])
    return nodes, pairs


def branching(rng: random.Random):
    """Antlers / fractal-ish: recursive fan-out to a bounded depth."""
    depth = rng.randint(2, 3)
    fanout = rng.randint(2, 3)
    nodes = [_node(0, None, 0)]

    def grow(parent, d):
        if d == 0:
            return
        for _ in range(fanout):
            nid = len(nodes)
            nodes.append(_node(nid, parent, _len(rng)))
            grow(nid, d - 1)

    grow(0, depth)
    pairs = _pair_leaves(nodes, rng, max_pairs=len(nodes) // 4)
    return nodes, pairs


def random_tree(rng: random.Random):
    """Unstructured: random size, each node parented to an earlier node."""
    n = rng.randint(4, 14)
    nodes = [_node(0, None, 0)]
    for i in range(1, n):
        nodes.append(_node(i, rng.randint(0, i - 1), _len(rng)))
    n_leaves = len(_leaves(nodes))
    pairs = _pair_leaves(nodes, rng, max_pairs=rng.randint(0, n_leaves // 2))
    return nodes, pairs


_ARCHETYPES = (radial, spine_with_limbs, branching)


def generate(n: int, anchored_frac: float = 0.7, seed: int = 0):
    """Yield n (source, nodes, pairs) triples deterministically for `seed`.

    The first round(anchored_frac * n) are 'anchored' (a random archetype
    family with sampled structural params); the rest are 'random'.
    """
    rng = random.Random(seed)
    n_anchored = round(anchored_frac * n)
    for i in range(n):
        if i < n_anchored:
            nodes, pairs = rng.choice(_ARCHETYPES)(rng)
            yield "anchored", nodes, pairs
        else:
            yield "random", *random_tree(rng)
```

- [ ] **Step 4: Run all generator tests to verify they pass**

Run: `cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_tree_generator.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
cd <repo>
git add mcp_harness/feasibility/tree_generator.py mcp_harness/tests/test_tree_generator.py
git commit -m "feat(feasibility): spine/branching/random families + generate()"
```

---

## Task 3: Dataset module (features + JSONL round-trip + resume)

**Files:**
- Create: `mcp_harness/feasibility/dataset.py`
- Test: `mcp_harness/tests/test_feasibility_dataset.py`

- [ ] **Step 1: Write the failing test**

Create `mcp_harness/tests/test_feasibility_dataset.py`:

```python
"""Cheap topological features + append-only JSONL store with id-based resume."""
import sys
sys.path.insert(0, "tests")

from feasibility import dataset as ds


def test_extract_features_on_a_known_tree():
    nodes = [{"id": 0, "parent_id": None, "length": 0},
             {"id": 1, "parent_id": 0, "length": 0.3},
             {"id": 2, "parent_id": 0, "length": 0.5}]
    pairs = [[1, 2]]
    f = ds.extract_features(nodes, pairs)
    assert f["n_nodes"] == 3
    assert f["n_leaves"] == 2
    assert f["max_degree"] == 2        # root has two children
    assert f["edge_max"] == 0.5
    assert f["edge_min"] == 0.3
    assert abs(f["edge_mean"] - 0.4) < 1e-9
    assert f["n_sym_pairs"] == 1


def test_append_and_read_round_trip(tmp_path):
    path = tmp_path / "corpus.jsonl"
    row = {"id": 7, "source": "anchored", "nodes": [], "pairs": [],
           "features": {}, "attempt0_pack": True, "failure_mode": "pack",
           "perturb_pack": None}
    ds.append_row(str(path), row)
    rows = ds.read_rows(str(path))
    assert rows == [row]


def test_existing_ids_enables_resume(tmp_path):
    path = tmp_path / "corpus.jsonl"
    for i in (0, 1, 2):
        ds.append_row(str(path), {"id": i})
    assert ds.existing_ids(str(path)) == {0, 1, 2}


def test_existing_ids_on_missing_file_is_empty(tmp_path):
    assert ds.existing_ids(str(tmp_path / "nope.jsonl")) == set()
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_feasibility_dataset.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'feasibility.dataset'`.

- [ ] **Step 3: Implement the dataset module**

Create `mcp_harness/feasibility/dataset.py`:

```python
"""JSONL dataset store for the feasibility corpus + cheap feature extraction.

JSONL is chosen for append-friendly, crash-resumable, streamable writes: each
labeled tree is one line, a partial run is still a valid dataset, and a re-run
skips ids already present."""
from __future__ import annotations
import json
import os
from collections import Counter


def extract_features(nodes, pairs):
    """Trivial topological stats recorded from data we already hold."""
    edge_lens = [n["length"] for n in nodes if n["parent_id"] is not None]
    children = Counter(n["parent_id"] for n in nodes if n["parent_id"] is not None)
    leaves = [n["id"] for n in nodes if n["id"] not in children]
    return {
        "n_nodes": len(nodes),
        "n_leaves": len(leaves),
        "max_degree": max(children.values()) if children else 0,
        "edge_mean": round(sum(edge_lens) / len(edge_lens), 6) if edge_lens else 0,
        "edge_max": max(edge_lens) if edge_lens else 0,
        "edge_min": min(edge_lens) if edge_lens else 0,
        "n_sym_pairs": len(pairs),
    }


def append_row(path: str, row: dict) -> None:
    with open(path, "a") as f:
        f.write(json.dumps(row) + "\n")


def read_rows(path: str) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def existing_ids(path: str) -> set[int]:
    if not os.path.exists(path):
        return set()
    return {r["id"] for r in read_rows(path)}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_feasibility_dataset.py -v`
Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd <repo>
git add mcp_harness/feasibility/dataset.py mcp_harness/tests/test_feasibility_dataset.py
git commit -m "feat(feasibility): JSONL dataset store + cheap feature extraction"
```

---

## Task 4: Labeler (taxonomy over the crash-safe compiler)

**Files:**
- Create: `mcp_harness/feasibility/tree_labeler.py`
- Test: `mcp_harness/tests/test_tree_labeler.py`

- [ ] **Step 1: Write the failing test**

Create `mcp_harness/tests/test_tree_labeler.py`:

```python
"""Labeler maps compile_tree's verdict to (attempt0_pack, failure_mode), and
classify_status handles every status the runner can return."""
import sys
sys.path.insert(0, "tests")

import cases
from feasibility import tree_labeler as tl

# Failure modes that mean "did not pack" (for asserting overpacked trees).
_NO_PACK = {"no_pack_ibps", "not_connectable", "build_failed", "crash", "hang"}


def test_classify_status_taxonomy():
    assert tl.classify_status("ok", "<fold>") == (True, "pack")
    assert tl.classify_status("err", "POLYS_MULTIPLE_IBPS: ...") == (False, "no_pack_ibps")
    assert tl.classify_status("err", "NOT_LOCAL_ROOT_CONNECTABLE") == (False, "not_connectable")
    assert tl.classify_status("err", "could not build a full crease pattern") == (False, "build_failed")
    assert tl.classify_status("err", "something else") == (False, "build_failed")
    assert tl.classify_status("CRASH", "exit -11") == (False, "crash")
    assert tl.classify_status("HANG", "") == (False, "hang")


def test_label_known_packing_template():
    nodes, pairs = cases.CASES_BY_NAME["star-4"]
    pack, mode = tl.label(nodes, pairs)
    assert pack is True and mode == "pack"


def test_label_known_failing_case_does_not_pack():
    # cat-spine5 is pinned CLEAN-ERR in the baseline: it packs by scale but its
    # Universal-Molecule build fails (POLYS_MULTIPLE_IBPS), so attempt-0 fails.
    # (An overpacked symmetric star does NOT work as a negative fixture: the
    # scale optimizer shrinks the paper until any pure star packs.)
    nodes, pairs = cases.CASES_BY_NAME["cat-spine5"]
    pack, mode = tl.label(nodes, pairs)
    assert pack is False and mode in _NO_PACK
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_tree_labeler.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'feasibility.tree_labeler'`.

- [ ] **Step 3: Implement the labeler**

Create `mcp_harness/feasibility/tree_labeler.py`:

```python
"""Brute-force labeler: compile each tree once (attempt-0, deterministic, in an
isolated subprocess via runner.compile_tree) and map the verdict to
(attempt0_pack, failure_mode). perturb_label() runs the live retry path and is
called only on a sampled subset by the orchestrator (it costs ~12x a compile)."""
from __future__ import annotations
import runner
import server


def classify_status(status: str, msg: str):
    """(status, msg) from compile_tree -> (attempt0_pack, failure_mode)."""
    if status == "ok":
        return True, "pack"
    if status == "CRASH":
        return False, "crash"
    if status == "HANG":
        return False, "hang"
    # status == "err": disambiguate by the engine's error vocabulary.
    if "POLYS_MULTIPLE_IBPS" in msg:
        return False, "no_pack_ibps"
    if "NOT_LOCAL_ROOT_CONNECTABLE" in msg:
        return False, "not_connectable"
    return False, "build_failed"


def label(nodes, pairs, timeout: int = 40):
    """One isolated compile -> (attempt0_pack, failure_mode)."""
    status, payload = runner.compile_tree(nodes, pairs, timeout=timeout)
    return classify_status(status, payload)


def perturb_label(nodes, pairs) -> bool:
    """Did the +/-10% x12 server retry path eventually pack? (sampled use only)"""
    return not server.draft_and_compile_full_base(nodes, pairs).startswith("ERROR:")
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_tree_labeler.py -v`
Expected: all 3 tests PASS (the engine compiles run for real; allow a few seconds).

- [ ] **Step 5: Commit**

```bash
cd <repo>
git add mcp_harness/feasibility/tree_labeler.py mcp_harness/tests/test_tree_labeler.py
git commit -m "feat(feasibility): brute-force labeler + failure-mode taxonomy"
```

---

## Task 5: Build orchestrator (parallel, resumable, class-mix report)

**Files:**
- Create: `mcp_harness/feasibility/build_dataset.py`
- Test: `mcp_harness/tests/test_feasibility_dataset.py` (append one integration test)

- [ ] **Step 1: Append a failing integration test for the orchestrator core**

Append to `mcp_harness/tests/test_feasibility_dataset.py`:

```python
def test_build_corpus_writes_rows_and_is_resumable(tmp_path):
    from feasibility import build_dataset as bd
    path = str(tmp_path / "corpus.jsonl")
    # Small corpus so the test stays fast; threads fan compiles out.
    summary = bd.build_corpus(n=6, seed=7, out_path=path,
                              anchored_frac=0.5, workers=3, perturb_sample=0)
    rows = ds.read_rows(path)
    assert len(rows) == 6
    assert summary["total"] == 6
    for r in rows:
        assert set(r) >= {"id", "source", "nodes", "pairs", "features",
                          "attempt0_pack", "failure_mode", "perturb_pack"}
        assert r["failure_mode"] in {"pack", "no_pack_ibps", "not_connectable",
                                     "build_failed", "crash", "hang"}
    # Re-running with the same args adds nothing (resume by id).
    summary2 = bd.build_corpus(n=6, seed=7, out_path=path,
                               anchored_frac=0.5, workers=3, perturb_sample=0)
    assert len(ds.read_rows(path)) == 6
    assert summary2["added"] == 0


def test_perturb_pack_is_persisted_to_disk(tmp_path):
    """The sampled perturb result must be written to the JSONL, not just the
    live summary -- on-disk non-null perturb_pack count == perturb_sampled."""
    from feasibility import build_dataset as bd
    path = str(tmp_path / "corpus.jsonl")
    # Pick a corpus that contains at least one attempt-0 failure so the perturb
    # sample is non-empty (verified to hold for these params; adjust seed/n if
    # the generator changes and this becomes vacuous).
    summary = bd.build_corpus(n=20, seed=3, out_path=path,
                              anchored_frac=0.5, workers=4, perturb_sample=100)
    assert summary["perturb_sampled"] >= 1, "fixture must produce >=1 failure"
    rows = ds.read_rows(path)
    on_disk_non_null = sum(1 for r in rows if r["perturb_pack"] is not None)
    assert on_disk_non_null == summary["perturb_sampled"]
```

> **Implementer note:** before finalizing, confirm the `n=20, seed=3` corpus actually yields `perturb_sampled >= 1`. If it does not (the generator produced no attempt-0 failures), find a small `(n, seed)` that does and update the test — do NOT delete the assertion.

- [ ] **Step 2: Run to verify it fails**

Run: `cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_feasibility_dataset.py::test_build_corpus_writes_rows_and_is_resumable -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'feasibility.build_dataset'`.

- [ ] **Step 3: Implement the orchestrator**

Create `mcp_harness/feasibility/build_dataset.py`:

```python
"""Orchestrate generate -> label (parallel) -> JSONL, resumable, with a
class-mix health report. Parallelism uses a ThreadPoolExecutor over
tree_labeler.label: each label already runs its compile in an isolated spawned
subprocess, so threads give concurrency and a child crash is just a label."""
from __future__ import annotations
import argparse
import random
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

from feasibility import dataset as ds
from feasibility import tree_generator as tg
from feasibility import tree_labeler as tl


def _label_one(item):
    src, nodes, pairs = item
    pack, mode = tl.label(nodes, pairs)
    return {
        "source": src, "nodes": nodes, "pairs": pairs,
        "features": ds.extract_features(nodes, pairs),
        "attempt0_pack": pack, "failure_mode": mode, "perturb_pack": None,
    }


def build_corpus(n, seed, out_path, anchored_frac=0.7, workers=4,
                 perturb_sample=50):
    """Generate, label (threaded), perturb-sample the attempt-0 failures, then
    append unseen rows, and return a class-mix summary dict.

    Rows are appended AFTER the perturb pass so the sampled perturb_pack value
    is persisted on disk (not just in the live summary). Resume is unaffected:
    tg.generate is seed-deterministic, so an interrupted run re-derives the same
    trees by enumeration index and existing_ids skips the ones already written.
    """
    done = ds.existing_ids(out_path)
    todo = [(i, item) for i, item in enumerate(tg.generate(n, anchored_frac, seed))
            if i not in done]

    new_rows = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for (i, _item), row in zip(todo, pool.map(_label_one, (it for _, it in todo))):
            row["id"] = i
            new_rows.append(row)

    # Sampled perturb pass over attempt-0 FAILURES only (measures rescue rate).
    failures = [r for r in new_rows if not r["attempt0_pack"]]
    rescued = sampled = 0
    if perturb_sample and failures:
        rng = random.Random(seed)
        for r in rng.sample(failures, min(perturb_sample, len(failures))):
            r["perturb_pack"] = tl.perturb_label(r["nodes"], r["pairs"])
            sampled += 1
            rescued += bool(r["perturb_pack"])

    # Persist only now, so perturb_pack is durable on disk.
    for row in new_rows:
        ds.append_row(out_path, row)
    added = len(new_rows)

    all_rows = ds.read_rows(out_path)
    modes = Counter(r["failure_mode"] for r in all_rows)
    by_source = Counter(r["source"] for r in all_rows)
    return {
        "total": len(all_rows), "added": added,
        "pack_rate": round(sum(r["attempt0_pack"] for r in all_rows) / len(all_rows), 4),
        "failure_modes": dict(modes), "by_source": dict(by_source),
        "perturb_sampled": sampled, "perturb_rescued": rescued,
    }


def _report(summary):
    print(f"total={summary['total']}  added={summary['added']}  "
          f"attempt0_pack_rate={summary['pack_rate']:.1%}")
    print(f"by source : {summary['by_source']}")
    print(f"by mode   : {summary['failure_modes']}")
    if summary["perturb_sampled"]:
        rate = summary["perturb_rescued"] / summary["perturb_sampled"]
        print(f"perturb rescue (sampled {summary['perturb_sampled']} failures): "
              f"{summary['perturb_rescued']} -> {rate:.1%}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="feasibility/corpus.jsonl")
    ap.add_argument("--anchored-frac", type=float, default=0.7)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--perturb-sample", type=int, default=100)
    a = ap.parse_args()
    _report(build_corpus(a.n, a.seed, a.out, a.anchored_frac,
                         a.workers, a.perturb_sample))
```

- [ ] **Step 4: Run to verify the integration test passes**

Run: `cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_feasibility_dataset.py -v`
Expected: all dataset tests PASS, including the resume integration test (real compiles run; allow ~30s).

- [ ] **Step 5: Commit**

```bash
cd <repo>
git add mcp_harness/feasibility/build_dataset.py mcp_harness/tests/test_feasibility_dataset.py
git commit -m "feat(feasibility): parallel resumable build orchestrator + class-mix report"
```

---

## Task 6: Validation run + ignore the corpus artifact

**Files:**
- Modify: `mcp_harness/.gitignore` (create if absent)

- [ ] **Step 1: Keep generated corpora out of git**

Create or append `mcp_harness/.gitignore`:

```
feasibility/corpus*.jsonl
```

- [ ] **Step 2: Smoke-run a small corpus to confirm the pipeline end-to-end**

Run:
```bash
cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -m feasibility.build_dataset \
  -n 200 --seed 1 --workers 6 --perturb-sample 20 --out feasibility/corpus_smoke.jsonl
```
Expected: a class-mix report prints; `attempt0_pack_rate` is strictly between 0% and 100% (a non-degenerate mix), `by_source` shows both `anchored` and `random`, and `by mode` shows more than one failure mode. If the mix is degenerate (≈0% or ≈100% pack), tune `_LEN_LO/_LEN_HI` in `tree_generator.py` and/or `--anchored-frac`, then re-run.

- [ ] **Step 3: Run the full validation corpus (~2k)**

Run:
```bash
cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -m feasibility.build_dataset \
  -n 2000 --seed 1 --workers 6 --out feasibility/corpus.jsonl
```
Expected: completes (resumable if interrupted — re-run the same command to continue); prints a healthy class mix. Record the printed summary in the commit message of the next step.

- [ ] **Step 4: Run the whole feasibility test suite once more**

Run: `cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_tree_generator.py tests/test_feasibility_dataset.py tests/test_tree_labeler.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit the gitignore (corpus files themselves stay untracked)**

```bash
cd <repo>
git add mcp_harness/.gitignore
git commit -m "chore(feasibility): ignore generated corpus artifacts

Validation run (n=2000): <paste class-mix summary here>"
```

---

## Self-Review Notes

- **Spec coverage:** generator (Task 1–2, all 3 archetype families + random + `generate` with `anchored_frac`), labeler with the exact failure-mode taxonomy `{pack, no_pack_ibps, not_connectable, build_failed, crash, hang}` (Task 4), JSONL dataset + 7 cheap features (Task 3), parallel + resumable orchestrator + class-mix report (Task 5), ~2k validation run + health-check criteria (Task 6). Perturb sampling over attempt-0 failures only (Task 5). All spec sections map to a task.
- **Deviation from spec (intentional, within design intent):** parallelism uses `ThreadPoolExecutor` over the already-isolating `compile_tree` instead of a `multiprocessing` spawn pool — same parallelism and crash-safety, avoids spawn re-import/pickling friction. Noted in the plan header and Task 5.
- **Type consistency:** `label()`/`classify_status()` return `(bool, str)` everywhere; row schema keys are identical across `dataset` test, `build_dataset._label_one`, and the integration test; `generate` yields `(source, nodes, pairs)` consumed consistently in `build_corpus`.
- **No placeholders:** every code/command step is concrete; the only fill-in is the run-time class-mix summary pasted into the final commit message (a genuine runtime value, not a design gap).
