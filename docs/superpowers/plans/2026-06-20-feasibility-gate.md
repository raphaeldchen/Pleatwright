# Feasibility Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Tier 2.5 fast gatekeeper from CLAUDE.md §6 — a two-stage gate (k-NN OOD check → recall-tuned RandomForest) that the agent calls via a `predict_tree_feasibility` MCP tool before the expensive C++ compile.

**Architecture:** Three modules under `mcp_harness/feasibility/`. `train_model.py` fits a `RandomForestClassifier(class_weight="balanced")` plus a `StandardScaler`+`NearestNeighbors` OOD detector on a labeled corpus, tunes a block threshold to a target recall on the feasible class, and saves one `joblib` artifact. `gate.py` loads that artifact and serves a pure two-stage `predict(nodes, pairs)`. `server.py` exposes it as the `predict_tree_feasibility` MCP tool. The C++ compiler stays authoritative; the gate may only ever skip near-certain failures, so bias costs latency, never correctness.

**Tech Stack:** Python 3.14 (`mcp_harness/.venv`), scikit-learn 1.9.0 + joblib (already installed — no new deps), numpy. Tests via pytest. Reuses `feasibility.dataset` for feature extraction (train/serve parity) and the existing FastMCP `server.py`.

**Import/run contract (from the codebase):** Run everything from `mcp_harness/` with `PYTHONPATH=.:tests`. The package imports as `from feasibility import ...`. `@mcp.tool()`-decorated functions in `server.py` remain directly callable in tests (e.g. `server.find_free_paper(...)`).

**Design spec:** `docs/superpowers/specs/2026-06-20-feasibility-gate-design.md`.

---

## File Structure

- Create: `mcp_harness/feasibility/train_model.py` — fit + persist (offline). Holds `FEATURE_ORDER`, the threshold/OOD math helpers, `fit()`, a `_report` printer, and a `__main__` CLI.
- Create: `mcp_harness/feasibility/gate.py` — load + serve. Holds `load()` and `Gate.predict()` (the two-stage routing). No training imports.
- Modify: `mcp_harness/server.py` — add the `predict_tree_feasibility` MCP tool (lazy-loads the gate artifact).
- Modify: `mcp_harness/.gitignore` — ignore the generated `*.joblib` artifact.
- Create: `mcp_harness/tests/test_train_model.py` — unit tests for the threshold + OOD math.
- Create: `mcp_harness/tests/test_gate.py` — verdict routing, feature parity, round-trip, recall guarantee, missing-artifact.
- Create: `mcp_harness/tests/test_predict_tool.py` — MCP tool integration test.

**Artifact dict schema** (saved by `train_model.fit`, loaded by `gate.load`) — referenced by every task:

```python
{
    "scaler":          StandardScaler,      # fit on TRAIN feature vectors
    "knn":             NearestNeighbors,    # fit on scaled TRAIN vectors, n_neighbors=k+1
    "k":               int,                 # neighbors used for the OOD mean-distance
    "ood_threshold":   float,               # P95 of train self mean-k-distances
    "classifier":      RandomForestClassifier,
    "block_threshold": float,               # block (infeasible) iff p_pack < this
    "feature_order":   list[str],           # column order used to build every vector
    "metadata":        dict,                # corpus_path, target_recall, k, sizes, date
}
```

**Verdict dict schema** (returned by `Gate.predict`) — referenced by every task:

```python
{"verdict": "feasible" | "infeasible" | "compile_anyway",
 "p_pack": float, "ood": bool, "ood_score": float, "reason": str}
```

---

## Task 1: Threshold + OOD math helpers (pure functions)

**Files:**
- Create: `mcp_harness/feasibility/train_model.py`
- Test: `mcp_harness/tests/test_train_model.py`

- [ ] **Step 1: Write the failing tests**

Create `mcp_harness/tests/test_train_model.py`:

```python
"""Unit tests for the recall-threshold and OOD-threshold math (no engine, no I/O)."""
import sys
sys.path.insert(0, "tests")

import numpy as np
from feasibility import train_model as tm


def test_fit_block_threshold_meets_target_recall():
    # 4 feasible (label 1) with scores .9 .8 .7 .6, plus 2 infeasible.
    # target_recall=0.75 -> must keep 3 of 4 positives -> largest t = 0.7.
    p_pack = np.array([0.9, 0.8, 0.7, 0.6, 0.4, 0.3])
    y = np.array([1, 1, 1, 1, 0, 0])
    t = tm._fit_block_threshold(p_pack, y, target_recall=0.75)
    assert abs(t - 0.7) < 1e-9
    # recall at this threshold (predict pack iff p_pack >= t) is >= target.
    recall = ((p_pack >= t) & (y == 1)).sum() / (y == 1).sum()
    assert recall >= 0.75


def test_fit_block_threshold_recall_1_keeps_all_positives():
    p_pack = np.array([0.9, 0.5, 0.2, 0.1])
    y = np.array([1, 1, 0, 0])
    t = tm._fit_block_threshold(p_pack, y, target_recall=1.0)
    # every positive must survive: t <= min positive score (0.5).
    assert t <= 0.5 + 1e-9


def test_fit_ood_separates_near_and_far():
    rng = np.random.RandomState(0)
    X = rng.normal(0, 1, size=(50, 3))          # a tight-ish training cluster
    scaler, knn, k, thr = tm._fit_ood(X, k=5)
    near = tm._ood_score(scaler, knn, k, X[0])  # identical to a train row
    far = tm._ood_score(scaler, knn, k, np.array([50.0, 50.0, 50.0]))
    assert near <= thr
    assert far > thr
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_train_model.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'feasibility.train_model'`.

- [ ] **Step 3: Implement the helpers**

Create `mcp_harness/feasibility/train_model.py`:

```python
"""Fit and persist the Tier 2.5 feasibility gate (CLAUDE.md §6).

Trains a recall-tuned RandomForest (Stage B) plus a k-NN OOD detector (Stage A)
on a labeled corpus and saves a single joblib artifact for gate.py to serve.
The C++ compiler stays authoritative, so the gate only ever SKIPS near-certain
failures -- we therefore tune for high recall on the feasible class."""
from __future__ import annotations
import numpy as np
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

# Column order for every feature vector. Must match keys from
# dataset.extract_features so training and serving build identical vectors.
FEATURE_ORDER = ["n_nodes", "n_leaves", "max_degree",
                 "edge_mean", "edge_max", "edge_min", "n_sym_pairs"]


def _fit_block_threshold(p_pack, y, target_recall: float) -> float:
    """Largest t such that recall on the feasible class (predict pack iff
    p_pack >= t) is >= target_recall. The gate blocks (infeasible) iff
    p_pack < t, so a larger t blocks more and recall falls; we pick the most
    aggressive t that still preserves the target recall."""
    pos = np.sort(p_pack[y == 1])[::-1]          # positive scores, descending
    if len(pos) == 0:
        return 0.0
    import math
    k = max(1, math.ceil(target_recall * len(pos)))   # positives we must keep
    k = min(k, len(pos))
    return float(pos[k - 1])


def _fit_ood(X_train, k: int = 5):
    """Fit StandardScaler + NearestNeighbors on the training vectors and return
    (scaler, knn, k, ood_threshold) where ood_threshold is the 95th percentile
    of training points' own mean distance to their k nearest OTHER neighbors."""
    scaler = StandardScaler().fit(X_train)
    Xs = scaler.transform(X_train)
    knn = NearestNeighbors(n_neighbors=k + 1).fit(Xs)   # +1 so we can drop self
    dist, _ = knn.kneighbors(Xs)                          # self is column 0 (dist 0)
    self_mean = dist[:, 1:].mean(axis=1)                  # mean of k OTHERS
    thr = float(np.percentile(self_mean, 95))
    return scaler, knn, k, thr


def _ood_score(scaler, knn, k: int, x_row) -> float:
    """Mean distance from x_row to its k nearest training neighbors (scaled)."""
    xs = scaler.transform(np.asarray(x_row, dtype=float).reshape(1, -1))
    dist, _ = knn.kneighbors(xs, n_neighbors=k)          # query not in index: k others
    return float(dist.mean())
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_train_model.py -v`
Expected: all 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd <repo>
git add mcp_harness/feasibility/train_model.py mcp_harness/tests/test_train_model.py
git commit -m "feat(feasibility): recall-threshold + k-NN OOD math helpers"
```

---

## Task 2: `fit()` — assemble + persist the artifact

**Files:**
- Modify: `mcp_harness/feasibility/train_model.py`
- Test: `mcp_harness/tests/test_train_model.py` (append)

- [ ] **Step 1: Append the failing test**

Append to `mcp_harness/tests/test_train_model.py`:

```python
def _write_corpus(path, n_each=40):
    """Write a tiny two-cluster corpus: small radial trees (mostly pack=True)
    and large trees (mostly pack=False), with real extract_features values."""
    import json, random
    from feasibility import dataset as ds
    rng = random.Random(0)
    rows = []
    rid = 0
    for _ in range(n_each):           # small, feasible
        nodes = [{"id": 0, "parent_id": None, "length": 0}]
        for i in range(1, rng.randint(3, 4) + 1):
            nodes.append({"id": i, "parent_id": 0, "length": round(rng.uniform(0.15, 0.3), 4)})
        rows.append({"id": rid, "source": "anchored", "nodes": nodes, "pairs": [],
                     "features": ds.extract_features(nodes, []),
                     "attempt0_pack": True, "failure_mode": "pack", "perturb_pack": None})
        rid += 1
    for _ in range(n_each):           # large, infeasible
        nodes = [{"id": 0, "parent_id": None, "length": 0}]
        for i in range(1, rng.randint(18, 24)):
            nodes.append({"id": i, "parent_id": rng.randint(0, i - 1),
                          "length": round(rng.uniform(0.4, 0.55), 4)})
        rows.append({"id": rid, "source": "random", "nodes": nodes, "pairs": [],
                     "features": ds.extract_features(nodes, []),
                     "attempt0_pack": False, "failure_mode": "build_failed", "perturb_pack": None})
        rid += 1
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def test_fit_saves_artifact_with_full_schema(tmp_path):
    corpus = str(tmp_path / "c.jsonl")
    out = str(tmp_path / "gate.joblib")
    _write_corpus(corpus)
    report = tm.fit(corpus, out, target_recall=0.98, k=5, seed=0)
    import joblib, os
    assert os.path.exists(out)
    art = joblib.load(out)
    assert set(art) >= {"scaler", "knn", "k", "ood_threshold", "classifier",
                        "block_threshold", "feature_order", "metadata"}
    assert art["feature_order"] == tm.FEATURE_ORDER
    # The recall guarantee actually holds on the validation split.
    assert report["val_recall_feasible"] >= 0.98 - 1e-9
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_train_model.py::test_fit_saves_artifact_with_full_schema -v`
Expected: FAIL — `AttributeError: module 'feasibility.train_model' has no attribute 'fit'`.

- [ ] **Step 3: Implement `fit()`, the report printer, and the CLI**

Append to `mcp_harness/feasibility/train_model.py`:

```python
import argparse
import datetime
import joblib
from collections import Counter
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

from feasibility import dataset as ds


def _matrix(rows):
    """Build (X, y) from corpus rows using the recorded feature dicts."""
    X = np.array([[r["features"][f] for f in FEATURE_ORDER] for r in rows], dtype=float)
    y = np.array([int(r["attempt0_pack"]) for r in rows])
    return X, y


def _pack_index(clf) -> int:
    """Column index of the 'pack' (label 1) class in predict_proba output."""
    return list(clf.classes_).index(1)


def fit(corpus_path, out_path, target_recall: float = 0.98, k: int = 5,
        val_frac: float = 0.2, seed: int = 0) -> dict:
    """Fit Stage B (RandomForest) + Stage A (k-NN OOD), tune the block threshold
    to target_recall on a held-out split, save the artifact, return a report."""
    rows = ds.read_rows(corpus_path)
    X, y = _matrix(rows)
    Xtr, Xval, ytr, yval = train_test_split(
        X, y, test_size=val_frac, random_state=seed, stratify=y)

    clf = RandomForestClassifier(n_estimators=300, class_weight="balanced",
                                 random_state=seed, n_jobs=-1).fit(Xtr, ytr)
    pi = _pack_index(clf)
    p_val = clf.predict_proba(Xval)[:, pi]
    block_threshold = _fit_block_threshold(p_val, yval, target_recall)

    scaler, knn, k, ood_threshold = _fit_ood(Xtr, k=k)

    artifact = {
        "scaler": scaler, "knn": knn, "k": k, "ood_threshold": ood_threshold,
        "classifier": clf, "block_threshold": block_threshold,
        "feature_order": FEATURE_ORDER,
        "metadata": {"corpus_path": corpus_path, "target_recall": target_recall,
                     "k": k, "n_train": len(Xtr), "n_val": len(Xval),
                     "date": datetime.date.today().isoformat()},
    }
    joblib.dump(artifact, out_path)

    # Report on the validation split.
    pred_pack = p_val >= block_threshold
    feasible = yval == 1
    val_recall = float((pred_pack & feasible).sum() / max(feasible.sum(), 1))
    blocked = ~pred_pack
    val_precision_block = float((blocked & ~feasible).sum() / max(blocked.sum(), 1))
    ood_val = np.array([_ood_score(scaler, knn, k, x) > ood_threshold for x in Xval])
    save_rate = float((blocked & ~ood_val).sum() / len(yval))   # in-dist blocks = compiles skipped
    return {
        "n_rows": len(rows), "pack_rate": float(y.mean()),
        "block_threshold": block_threshold, "ood_threshold": ood_threshold,
        "val_recall_feasible": val_recall,
        "val_block_precision": val_precision_block,
        "compile_save_rate": save_rate, "val_ood_rate": float(ood_val.mean()),
        "failure_modes": dict(Counter(r["failure_mode"] for r in rows)),
    }


def _report(s):
    print(f"rows={s['n_rows']}  pack_rate={s['pack_rate']:.1%}  "
          f"block_threshold={s['block_threshold']:.3f}  ood_threshold={s['ood_threshold']:.3f}")
    print(f"val recall(feasible)={s['val_recall_feasible']:.1%}  "
          f"block precision={s['val_block_precision']:.1%}")
    print(f"compile-save rate={s['compile_save_rate']:.1%}  val OOD rate={s['val_ood_rate']:.1%}")
    print(f"failure modes: {s['failure_modes']}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="feasibility/corpus_wide.jsonl")
    ap.add_argument("--out", default="feasibility/gate.joblib")
    ap.add_argument("--target-recall", type=float, default=0.98)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    _report(fit(a.corpus, a.out, a.target_recall, a.k, seed=a.seed))
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_train_model.py -v`
Expected: all tests PASS (allow a few seconds for the RandomForest fit).

- [ ] **Step 5: Commit**

```bash
cd <repo>
git add mcp_harness/feasibility/train_model.py mcp_harness/tests/test_train_model.py
git commit -m "feat(feasibility): fit() assembles+persists the gate artifact + CLI"
```

---

## Task 3: `gate.py` — load + two-stage predict

**Files:**
- Create: `mcp_harness/feasibility/gate.py`
- Test: `mcp_harness/tests/test_gate.py`

- [ ] **Step 1: Write the failing tests**

Create `mcp_harness/tests/test_gate.py`:

```python
"""Gate serving: two-stage verdict routing, feature parity, round-trip, errors."""
import sys
sys.path.insert(0, "tests")

import pytest
from feasibility import train_model as tm
from feasibility import gate as g
from feasibility import dataset as ds
from tests.test_train_model import _write_corpus   # reuse the fixture builder


def _small(): # in-distribution, feasible-looking (3 short limbs off root)
    return ([{"id": 0, "parent_id": None, "length": 0},
             {"id": 1, "parent_id": 0, "length": 0.2},
             {"id": 2, "parent_id": 0, "length": 0.22},
             {"id": 3, "parent_id": 0, "length": 0.18}], [])


def _large(): # in-distribution, infeasible-looking (20 long edges)
    nodes = [{"id": 0, "parent_id": None, "length": 0}]
    for i in range(1, 20):
        nodes.append({"id": i, "parent_id": i - 1, "length": 0.5})
    return nodes, []


def _wild(): # far outside training support (hundreds of nodes)
    nodes = [{"id": 0, "parent_id": None, "length": 0}]
    for i in range(1, 200):
        nodes.append({"id": i, "parent_id": 0, "length": 0.5})
    return nodes, []


@pytest.fixture
def gate(tmp_path):
    corpus = str(tmp_path / "c.jsonl")
    out = str(tmp_path / "gate.joblib")
    _write_corpus(corpus)
    tm.fit(corpus, out, target_recall=0.98, k=5, seed=0)
    return g.load(out)


def test_in_distribution_feasible_tree_is_feasible(gate):
    r = gate.predict(*_small())
    assert r["ood"] is False
    assert r["verdict"] == "feasible"
    assert 0.0 <= r["p_pack"] <= 1.0


def test_in_distribution_infeasible_tree_is_blocked(gate):
    r = gate.predict(*_large())
    assert r["ood"] is False
    assert r["verdict"] == "infeasible"


def test_far_tree_is_compile_anyway(gate):
    r = gate.predict(*_wild())
    assert r["ood"] is True
    assert r["verdict"] == "compile_anyway"


def test_feature_parity_with_dataset(gate):
    nodes, pairs = _small()
    feats = ds.extract_features(nodes, pairs)
    vec = gate._vector(feats)                       # serving builds in FEATURE_ORDER
    assert vec == [feats[f] for f in tm.FEATURE_ORDER]


def test_load_missing_artifact_raises_clearly(tmp_path):
    with pytest.raises(FileNotFoundError, match="gate artifact not found"):
        g.load(str(tmp_path / "nope.joblib"))
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_gate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'feasibility.gate'`.

- [ ] **Step 3: Implement `gate.py`**

Create `mcp_harness/feasibility/gate.py`:

```python
"""Serve the trained feasibility gate (fast, per-call). Loads the joblib artifact
from train_model and runs the two-stage gate: Stage A k-NN OOD check, then Stage B
RandomForest with a recall-tuned block threshold. Pure function of artifact+tree;
no engine call, no training-path imports. See the design spec."""
from __future__ import annotations
import os
import numpy as np
import joblib

from feasibility import dataset as ds
from feasibility import train_model as tm


def load(path: str) -> "Gate":
    # Security: the artifact is a pickle, but it is ALWAYS self-produced by
    # train_model.fit on this machine and read from a local, gitignored path --
    # never sourced from an untrusted party. This is the standard sklearn
    # persistence pattern and is safe in that trusted-producer context.
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"gate artifact not found at {path!r}; run train_model.fit first")
    return Gate(joblib.load(path))


class Gate:
    def __init__(self, artifact: dict):
        self.a = artifact
        self.feature_order = artifact["feature_order"]

    def _vector(self, features: dict) -> list:
        return [features[f] for f in self.feature_order]

    def predict(self, nodes, pairs) -> dict:
        a = self.a
        feats = ds.extract_features(nodes, pairs)
        x = np.array([self._vector(feats)], dtype=float)

        # Stage A: OOD (scaled k-NN distance).
        ood_score = tm._ood_score(a["scaler"], a["knn"], a["k"], x[0])
        ood = ood_score > a["ood_threshold"]

        # p_pack always computed (telemetry); RandomForest needs no scaling.
        clf = a["classifier"]
        pi = list(clf.classes_).index(1)
        p_pack = float(clf.predict_proba(x)[0][pi])

        if ood:
            verdict, reason = "compile_anyway", (
                f"novel tree (OOD score {ood_score:.3f} > {a['ood_threshold']:.3f}); "
                "compile and log for retraining")
        elif p_pack < a["block_threshold"]:
            verdict, reason = "infeasible", (
                f"p_pack {p_pack:.3f} < block threshold {a['block_threshold']:.3f}; "
                "shrink/adjust before compiling")
        else:
            verdict, reason = "feasible", (
                f"p_pack {p_pack:.3f} >= block threshold {a['block_threshold']:.3f}")
        return {"verdict": verdict, "p_pack": p_pack, "ood": bool(ood),
                "ood_score": ood_score, "reason": reason}
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_gate.py -v`
Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd <repo>
git add mcp_harness/feasibility/gate.py mcp_harness/tests/test_gate.py
git commit -m "feat(feasibility): gate.py two-stage predict (OOD -> classifier)"
```

---

## Task 4: `predict_tree_feasibility` MCP tool

**Files:**
- Modify: `mcp_harness/server.py`
- Test: `mcp_harness/tests/test_predict_tool.py`

- [ ] **Step 1: Write the failing test**

Create `mcp_harness/tests/test_predict_tool.py`:

```python
"""The predict_tree_feasibility MCP tool returns a well-formed verdict JSON,
and degrades gracefully when no model is trained."""
import sys
sys.path.insert(0, "tests")

import json
import importlib
from feasibility import train_model as tm
from tests.test_train_model import _write_corpus


def test_tool_returns_verdict_json(tmp_path, monkeypatch):
    corpus = str(tmp_path / "c.jsonl")
    out = str(tmp_path / "gate.joblib")
    _write_corpus(corpus)
    tm.fit(corpus, out, target_recall=0.98, k=5, seed=0)

    import server
    importlib.reload(server)                 # reset the lazy gate cache
    monkeypatch.setenv("FEASIBILITY_GATE_PATH", out)

    nodes = [{"id": 0, "parent_id": None, "length": 0},
             {"id": 1, "parent_id": 0, "length": 0.2},
             {"id": 2, "parent_id": 0, "length": 0.2}]
    result = server.predict_tree_feasibility(tree_nodes=nodes, symmetric_pairs=[])
    payload = json.loads(result)
    assert payload["verdict"] in {"feasible", "infeasible", "compile_anyway"}
    assert 0.0 <= payload["p_pack"] <= 1.0
    assert set(payload) >= {"verdict", "p_pack", "ood", "ood_score", "reason"}


def test_tool_without_trained_model_is_graceful(tmp_path, monkeypatch):
    import server
    importlib.reload(server)
    monkeypatch.setenv("FEASIBILITY_GATE_PATH", str(tmp_path / "absent.joblib"))
    result = server.predict_tree_feasibility(
        tree_nodes=[{"id": 0, "parent_id": None, "length": 0}], symmetric_pairs=[])
    assert result.startswith("ERROR:")
    assert "not trained" in result or "not found" in result
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_predict_tool.py -v`
Expected: FAIL — `AttributeError: module 'server' has no attribute 'predict_tree_feasibility'`.

- [ ] **Step 3: Add the tool to `server.py`**

Add near the other `@mcp.tool()` definitions in `mcp_harness/server.py` (e.g. after `find_free_paper`). First add these imports at the top of the file, beside the existing imports:

```python
import os
from feasibility import gate as _gate
```

Then add the tool and its lazy loader:

```python
# Lazily-loaded feasibility gate (Tier 2.5). Cached after first successful load
# so the agent's tight drafting loop never re-reads the artifact from disk.
_GATE = None


def _load_gate():
    global _GATE
    if _GATE is None:
        path = os.environ.get("FEASIBILITY_GATE_PATH", "feasibility/gate.joblib")
        _GATE = _gate.load(path)        # raises FileNotFoundError if untrained
    return _GATE


@mcp.tool()
def predict_tree_feasibility(
    tree_nodes: list[dict],
    symmetric_pairs: list[list[int]] | None = None,
) -> str:
    """Fast Tier 2.5 gatekeeper (CLAUDE.md §6): predict whether a metric tree
    will compile BEFORE running the expensive C++ packer.

    Returns a JSON string with: verdict ('feasible' | 'infeasible' |
    'compile_anyway'), p_pack, ood, ood_score, reason. Only 'infeasible' means
    skip-and-shrink; 'feasible' and 'compile_anyway' both still compile (the C++
    engine stays authoritative). Returns 'ERROR: ...' if no model is trained.
    """
    try:
        gate = _load_gate()
    except FileNotFoundError as exc:
        return f"ERROR: feasibility gate not trained ({exc})"
    return json.dumps(gate.predict(tree_nodes, symmetric_pairs or []))
```

(`json` is already imported in `server.py`.)

- [ ] **Step 4: Run to verify it passes**

Run: `cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_predict_tool.py -v`
Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
cd <repo>
git add mcp_harness/server.py mcp_harness/tests/test_predict_tool.py
git commit -m "feat(feasibility): predict_tree_feasibility MCP tool (lazy gate load)"
```

---

## Task 5: Train on the real corpus + ignore the artifact

**Files:**
- Modify: `mcp_harness/.gitignore`

- [ ] **Step 1: Ignore the generated model artifact**

Append to `mcp_harness/.gitignore`:

```
feasibility/*.joblib
```

- [ ] **Step 2: Train the gate on the widened corpus and read the report**

Run:
```bash
cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -m feasibility.train_model \
  --corpus feasibility/corpus_wide.jsonl --out feasibility/gate.joblib
```
Expected: a report prints and `feasibility/gate.joblib` is written. Sanity checks:
`val recall(feasible)` is >= 98%; `compile-save rate` is strictly between 0% and 100% (the gate skips *some* but not all compiles); `val OOD rate` is small (single-digit %, since validation is drawn from the same distribution). If the save rate is ~0%, the threshold is too conservative for this corpus — note it; we will revisit when scaling the corpus.

- [ ] **Step 3: Run the whole feasibility test suite once more**

Run:
```bash
cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -m pytest \
  tests/test_train_model.py tests/test_gate.py tests/test_predict_tool.py \
  tests/test_tree_generator.py tests/test_feasibility_dataset.py -v
```
Expected: all PASS.

- [ ] **Step 4: Commit the gitignore (the artifact itself stays untracked)**

```bash
cd <repo>
git add mcp_harness/.gitignore
git commit -m "chore(feasibility): ignore the generated gate.joblib artifact

Training run (corpus_wide, n=2000): <paste report summary here>"
```

---

## Self-Review Notes

- **Spec coverage:** two-stage gate (Task 3), Stage A k-NN OOD with P95 threshold (Tasks 1–2), Stage B `RandomForestClassifier(class_weight="balanced")` (Task 2), recall-0.98 block threshold (Tasks 1–2), `train_model`/`gate` train/serve split with feature parity via `dataset.extract_features` (Tasks 2–3), the `predict_tree_feasibility` MCP tool with graceful untrained behavior (Task 4), artifact persistence via joblib + gitignore (Tasks 2, 5). Deterministic plumbing/guarantee tests only; no learned-accuracy assertions (Tasks 1–4). All spec sections map to a task.
- **Verdict/artifact schema consistency:** the artifact dict (8 keys) and verdict dict (5 keys) defined in File Structure are produced in Tasks 2/3 and consumed identically in Tasks 3/4 tests. `FEATURE_ORDER`, `_fit_block_threshold`, `_fit_ood`, `_ood_score`, `_vector`, `_load_gate`, and `_GATE` names are identical across every task that references them.
- **Train/serve parity:** both `_matrix` (train) and `Gate._vector` (serve) build vectors from `FEATURE_ORDER` over `dataset.extract_features` keys — one feature implementation, no drift.
- **No placeholders:** every code/command step is concrete; the only fill-in is the runtime report summary pasted into the final commit message (a genuine runtime value).
- **Deferred (out of scope, per spec):** agent wiring, production logging/retrain loop, geometric/GNN features, corpus scaling to ~20k.
