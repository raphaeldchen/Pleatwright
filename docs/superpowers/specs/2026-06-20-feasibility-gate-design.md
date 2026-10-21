# Tree-Feasibility Gate Design (Tier 2.5, phase 2)

**Status:** Approved design — ready for implementation plan.

**Context:** Phase 1 (the data pipeline, `2026-06-16-tree-feasibility-data-pipeline-design.md`)
generates and brute-force-labels synthetic Metric Trees into a JSONL corpus. This
phase consumes that corpus to build the actual fast gatekeeper from CLAUDE.md §6:
a lightweight model that the AI Orchestrator calls *before* the expensive C++
TreeMaker compile, so it can shrink/adjust physically-implausible trees in
milliseconds instead of waiting for the optimizer to fail.

## Why this shape (evidence from the investigation)

Before designing, we probed the existing 2k corpus and a widened 2k corpus:

- **The 7 features separate.** Best-possible accuracy on the features is ~88%
  (structural-only), real 5-fold CV ~82–90%. Not a feature dead-end.
- **Richer geometric features did NOT help generalization** (negative result):
  adding 7 circle-packing-proxy features left in-distribution CV flat and made
  off-distribution recall *worse*. The bottleneck is data *support*, not feature
  representation.
- **Diversity is the lever.** Widening the generator (fill the empty 15–39 node
  region, break the 40-node lattice spike) moved anchored→random pack-recall
  54.7% → 73.6%. Confirmed: coverage, not features.
- **Even maxed-out diversity leaves a blind region.** Off-distribution recall is
  still ~74%, so the model can *never* be trusted outside its training support.
  → an OOD gate + always-compile fallback is permanent architecture, not a
  temporary crutch.
- **Class imbalance is live.** The wide corpus is ~23% "pack", so a naive model
  drifts toward predicting "fail". Must use class weighting + a recall-tuned
  threshold.

## Core principle: bias degrades latency, never correctness

The gate sits in front of the deterministic C++ compiler, which stays the final
authority and runs on everything the gate does not block. Trace the costs:

- **False "feasible"** → the compiler runs and catches it. Lost latency, not a
  wrong answer.
- **False "infeasible"** → the agent needlessly shrinks a good tree. Missed
  design fidelity, not a wrong answer.

So the gate may only ever *remove* near-certain failures from the compile queue.
This is why we tune for **high recall on the feasible class** (rarely block a
foldable tree) and gate the classifier behind an OOD check (only trust it where
it has support).

## Architecture: two-stage gate

```
predict_tree_feasibility(tree)
        │
        ▼
 Stage A: OOD gate (k-NN distance)
        │  novel  ──────────────►  verdict = "compile_anyway"  (+flag for retrain)
        │ in-distribution
        ▼
 Stage B: classifier (RandomForest)
        │  p_pack < t  ─────────►  verdict = "infeasible"  (agent shrinks, skip compile)
        │ p_pack ≥ t
        ▼
              verdict = "feasible"  ──────►  (compile)
```

The only verdict that changes agent behavior is **`infeasible`** (skip compile +
shrink). Both `feasible` and `compile_anyway` lead to a real compile; they are
distinguished only for telemetry / the future retrain pool.

## Components

All new code under `mcp_harness/feasibility/`. Run contract is the existing one:
from `mcp_harness/` with `PYTHONPATH=.:tests`.

### `train_model.py` — fit + persist (offline, slow)

- Load a corpus JSONL; build the 7-feature matrix + labels using the SAME
  `dataset.extract_features` used to build the corpus (feature parity).
- Features (fixed order, recorded in the artifact):
  `n_nodes, n_leaves, max_degree, edge_mean, edge_max, edge_min, n_sym_pairs`.
- Stratified train/validation split, fixed `random_state`.
- **Stage B classifier:** `RandomForestClassifier(class_weight="balanced",
  random_state=…)` — `balanced` counters the ~23% pack imbalance.
- **Block-threshold fitting:** on the validation set, choose the largest `t` such
  that recall on the feasible (pack) class ≥ `target_recall` (default **0.98**).
  Block iff `p_pack < t`.
- **Stage A OOD:** `StandardScaler` + `NearestNeighbors` fit on the *training*
  feature vectors. OOD threshold = the 95th percentile of training points' own
  mean k-NN (k=5) distances. A tree is OOD iff its mean k-NN distance to the
  training set exceeds that threshold.
- Persist one artifact via `joblib`:
  `{scaler, knn, ood_threshold, classifier, block_threshold, feature_order,
    metadata}` where metadata records corpus path, target_recall, k, sizes, date.
- Print a human-reviewed report: validation recall/precision on feasible, the
  compile-save rate at the chosen `t`, and the OOD rate on validation.

### `gate.py` — load + serve (fast, per-call)

- `load(path) -> Gate` (raises a clear error if the artifact is missing).
- `Gate.predict(nodes, pairs) -> dict`:
  - extract features via `dataset.extract_features`, ordered by `feature_order`;
  - Stage A: scale + k-NN distance → `ood`, `ood_score`;
  - if OOD → `compile_anyway`; else Stage B: `p_pack` from the classifier →
    `infeasible` if `p_pack < block_threshold` else `feasible`;
  - returns `{"verdict", "p_pack", "ood", "ood_score", "reason"}`.
- Pure function of artifact + tree; no engine call; no training-path imports.

### `server.py` edit — MCP tool

- Register `predict_tree_feasibility(tree_json)` (the CLAUDE.md §6 name).
- Lazy-load the gate artifact on first call; cache it.
- If the artifact file is absent, return a clear "gate not trained" message so the
  server still boots and other tools keep working.

## Testing

Deterministic plumbing + guarantee tests only. No assertions on learned accuracy
(those are run-time report outputs that drift with the corpus).

### `tests/test_gate.py`
- **Verdict routing** (fixture artifact trained on a few hand-crafted rows):
  a feature-space-distant tree → `compile_anyway` + `ood=True`; an in-distribution
  low-`p_pack` tree → `infeasible`; in-distribution high-`p_pack` → `feasible`.
- **Feature parity:** served vector order/values match `dataset.extract_features`.
- **Round-trip:** `train_model.fit` → save → `gate.load` → `predict` end-to-end on
  a small corpus.
- **Recall guarantee:** after fitting with `target_recall=0.98`, the chosen
  threshold yields ≥98% recall on the validation set.
- **Missing artifact:** `gate.load` on a nonexistent path raises a clear error.

### `tests/test_train_model.py`
- `_fit_block_threshold`: on a known `(p_pack, label)` set, returns the correct
  `t` for a target recall.
- OOD threshold = P95 of training self-distances; a point identical to a training
  row scores in-distribution, a far point scores OOD.

### MCP tool
- One integration test: `predict_tree_feasibility` is registered and returns a
  well-formed verdict dict for a sample tree (mirrors existing harness tool tests).

## Out of scope (later phases)

- **Agent wiring / use of the verdict** — teaching `agent_loop.py` to shrink on
  `infeasible` and to compile-and-log on `compile_anyway`.
- **Production logging + retrain loop** — storing
  `(tree, features, prediction, confidence, ood_verdict, compiler_label)` and
  periodic retraining; depends on agent integration.
- **Geometric proxy features / GNN** — parked (negative result above); revisit
  only if diversity-driven gains plateau.
- **Corpus scaling to ~20k** — done as a follow-up after a rough gate exists, to
  see whether recall climbs further.

## Dependencies

scikit-learn 1.9.0 + joblib are already in `mcp_harness/.venv`. No new deps. No
changes to the engine `.so`, `runner.py`, or the phase-1 pipeline modules.
