# Runtime Capture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record every served compile (tree + attempt-0 outcome + recomputed gate verdict) to an append-only `captured.jsonl`, so a later merge step can feed real data back into the gate corpus.

**Architecture:** A new defensive `feasibility/capture.py` with one `record(...)` function, gated by the `IDE_CAPTURE_PATH` env var (set = on + destination; unset = no-op). It is invoked from `server.py::_compile_with_perturb` right after the first (attempt-0) compile — a serve-only chokepoint the corpus builder never touches.

**Tech Stack:** Python 3.14, stdlib (`json`, `os`, `threading`, `datetime`); reuses `feasibility.dataset.extract_features`, `feasibility.tree_labeler.classify_status`, `feasibility.gate`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-06-24-runtime-capture-design.md`.
- Capture is active iff `IDE_CAPTURE_PATH` is set; that var is both the on-switch and the destination path. Unset → `record` is a no-op.
- `record(...)` MUST NEVER raise — capture is a side-channel; a failed capture drops one row, it never breaks the user's compile.
- Capture point is `server.py::_compile_with_perturb`, after the FIRST `attempt(nodes)` (the attempt-0 outcome, before perturb). It is serve-only: the corpus builder (`tree_labeler.label`) compiles via `runner.compile_tree` and never calls `_compile_with_perturb`, so builds are never captured.
- Row schema (corpus-compatible + serve metadata): keys `source="captured"`, `nodes`, `pairs`, `features` (== `ds.extract_features(nodes,pairs)`), `attempt0_pack` (bool), `failure_mode` (via `tree_labeler.classify_status` — same vocabulary as the corpus), `perturb_pack` (null), `gate` ({verdict,p_pack,ood,ood_score} or null), `ts` (ISO8601 seconds).
- `gate` is recomputed at capture via a cached `feasibility.gate.load`; if no artifact exists or it errors, `gate = null`. Capture does NOT train on-demand.
- `capture` must not import `tree_labeler` at module top (circular: `tree_labeler`→`server`→`capture`). Import `classify_status` lazily inside `record`.
- `captured.jsonl` is gitignored.
- Run tests from `mcp_harness/` with the venv: `cd <repo>/mcp_harness && .venv/bin/python -m pytest ...` (CWD = `mcp_harness/`; imports are `from feasibility import ...` / `import server`).
- Commit messages end with: `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`

---

### Task 1: `feasibility/capture.py` module

**Files:**
- Create: `mcp_harness/feasibility/capture.py`
- Test: `mcp_harness/tests/test_capture.py` (create)

**Interfaces:**
- Consumes: `feasibility.dataset.extract_features(nodes, pairs) -> dict`; `feasibility.tree_labeler.classify_status(status, msg) -> (attempt0_pack, failure_mode)` (lazy import); `feasibility.gate.load(path) -> Gate` with `.predict(nodes,pairs) -> {"verdict","p_pack","ood","ood_score",...}`.
- Produces: `record(nodes, pairs, attempt0_pack: bool, result_str: str) -> None` — appends one capture row iff `IDE_CAPTURE_PATH` is set; never raises. Module globals `_GATE`, `_GATE_TRIED` (cache), `_LOCK`, and a helper `_gate_verdict(nodes, pairs) -> dict | None`.

- [ ] **Step 1: Write the failing tests**

Create `mcp_harness/tests/test_capture.py`:

```python
"""Serve-time capture: env-gated, defensive, corpus-compatible rows."""
import json
import threading

from feasibility import capture
from feasibility import dataset as ds

STAR_NODES = [
    {"id": 0, "parent_id": None, "length": 0},
    {"id": 1, "parent_id": 0, "length": 0.3},
    {"id": 2, "parent_id": 0, "length": 0.3},
    {"id": 3, "parent_id": 0, "length": 0.3},
    {"id": 4, "parent_id": 0, "length": 0.3},
]
STAR_PAIRS = [[1, 2]]
FOLD = '{"vertices_coords": [[0, 0]]}'


def test_record_is_noop_when_disabled(monkeypatch, tmp_path):
    monkeypatch.delenv("IDE_CAPTURE_PATH", raising=False)
    capture.record(STAR_NODES, STAR_PAIRS, True, FOLD)   # must not raise
    assert list(tmp_path.iterdir()) == []                # nothing written


def test_record_writes_corpus_compatible_row(monkeypatch, tmp_path):
    out = tmp_path / "captured.jsonl"
    monkeypatch.setenv("IDE_CAPTURE_PATH", str(out))
    monkeypatch.setattr(capture, "_gate_verdict",
                        lambda n, p: {"verdict": "feasible", "p_pack": 0.9,
                                      "ood": False, "ood_score": 0.1})
    capture.record(STAR_NODES, STAR_PAIRS, True, FOLD)
    rows = [json.loads(l) for l in open(out)]
    assert len(rows) == 1
    r = rows[0]
    assert r["source"] == "captured"
    assert r["nodes"] == STAR_NODES and r["pairs"] == STAR_PAIRS
    assert r["features"] == ds.extract_features(STAR_NODES, STAR_PAIRS)
    assert r["attempt0_pack"] is True
    assert r["failure_mode"] == "pack"
    assert r["perturb_pack"] is None
    assert r["gate"]["verdict"] == "feasible"
    assert "ts" in r


def test_failure_mode_matches_corpus_vocabulary(monkeypatch, tmp_path):
    out = tmp_path / "captured.jsonl"
    monkeypatch.setenv("IDE_CAPTURE_PATH", str(out))
    monkeypatch.setattr(capture, "_gate_verdict", lambda n, p: None)
    capture.record(STAR_NODES, STAR_PAIRS, False,
                   "ERROR: packing failed POLYS_MULTIPLE_IBPS at vertex 3")
    r = json.loads(open(out).readlines()[-1])
    assert r["failure_mode"] == "no_pack_ibps"
    assert r["attempt0_pack"] is False
    assert r["gate"] is None


def test_record_never_raises_when_gate_loader_throws(monkeypatch, tmp_path):
    out = tmp_path / "captured.jsonl"
    monkeypatch.setenv("IDE_CAPTURE_PATH", str(out))
    monkeypatch.setattr(capture, "_GATE", None)
    monkeypatch.setattr(capture, "_GATE_TRIED", False)
    import feasibility.gate as g

    def boom(path):
        raise RuntimeError("artifact unreadable")
    monkeypatch.setattr(g, "load", boom)
    capture.record(STAR_NODES, STAR_PAIRS, True, FOLD)   # must not raise
    rows = [json.loads(l) for l in open(out)]
    assert len(rows) == 1 and rows[0]["gate"] is None


def test_concurrent_records_are_all_valid_lines(monkeypatch, tmp_path):
    out = tmp_path / "captured.jsonl"
    monkeypatch.setenv("IDE_CAPTURE_PATH", str(out))
    monkeypatch.setattr(capture, "_gate_verdict", lambda n, p: None)

    def worker():
        for _ in range(20):
            capture.record(STAR_NODES, STAR_PAIRS, True, FOLD)

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    lines = open(out).read().splitlines()
    assert len(lines) == 100
    for l in lines:
        json.loads(l)        # each line independently valid (no interleaving)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_capture.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'feasibility.capture'`

- [ ] **Step 3: Write the implementation**

Create `mcp_harness/feasibility/capture.py`:

```python
"""Serve-time capture of compiled trees for the gate data loop (capture half).

Appends one JSON row per served compile to the file named by IDE_CAPTURE_PATH
(that env var is both the on-switch and the destination). Unset => no-op, so
tests, CI, and the corpus builder never capture. Rows mirror a corpus row plus
serve metadata (recomputed gate verdict + timestamp) so a later merge step can
dedup and assign ids. record() must NEVER raise -- capture is a side-channel and
must not break a user's compile. See docs/superpowers/specs/2026-06-24-runtime-capture-design.md.
"""
from __future__ import annotations

import datetime
import json
import os
import sys
import threading

from feasibility import dataset as ds

_LOCK = threading.Lock()
_GATE = None
_GATE_TRIED = False


def _gate_verdict(nodes, pairs):
    """Best-effort gate verdict for tagging; None if no artifact / any error.
    Loads the artifact once (cached); never trains on demand."""
    global _GATE, _GATE_TRIED
    if not _GATE_TRIED:
        _GATE_TRIED = True
        try:
            from feasibility import gate as _gate
            path = os.environ.get(
                "FEASIBILITY_GATE_PATH",
                os.path.join(os.path.dirname(__file__), "gate.joblib"))
            _GATE = _gate.load(path)
        except Exception:
            _GATE = None
    if _GATE is None:
        return None
    try:
        v = _GATE.predict(nodes, pairs)
        return {"verdict": v["verdict"], "p_pack": v["p_pack"],
                "ood": v["ood"], "ood_score": v["ood_score"]}
    except Exception:
        return None


def _failure_mode(attempt0_pack: bool, result_str: str) -> str:
    """Reuse the corpus's exact vocabulary via tree_labeler.classify_status.
    Imported lazily: tree_labeler imports server at module top and server imports
    this module, so a top-level import would be circular."""
    from feasibility.tree_labeler import classify_status
    status = "ok" if attempt0_pack else "err"
    return classify_status(status, result_str)[1]


def record(nodes, pairs, attempt0_pack: bool, result_str: str) -> None:
    """Append one capture row iff IDE_CAPTURE_PATH is set. Never raises."""
    path = os.environ.get("IDE_CAPTURE_PATH")
    if not path:
        return
    try:
        row = {
            "source": "captured",
            "nodes": nodes,
            "pairs": pairs,
            "features": ds.extract_features(nodes, pairs),
            "attempt0_pack": bool(attempt0_pack),
            "failure_mode": _failure_mode(attempt0_pack, result_str),
            "perturb_pack": None,
            "gate": _gate_verdict(nodes, pairs),
            "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        }
        line = json.dumps(row)
        with _LOCK:
            with open(path, "a") as f:
                f.write(line + "\n")
    except Exception as exc:        # capture must never break a compile
        print(f"[capture] dropped one row: {exc}", file=sys.stderr)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_capture.py -q`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/feasibility/capture.py mcp_harness/tests/test_capture.py
git commit -m "$(printf 'feat(feasibility): capture.py serve-time capture module\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

### Task 2: Wire capture into the serve compile path

**Files:**
- Modify: `mcp_harness/server.py` (`_compile_with_perturb` + its two call sites + import)
- Modify: `.gitignore`
- Test: `mcp_harness/tests/test_capture.py` (append integration tests)

**Interfaces:**
- Consumes: `capture.record` (Task 1); existing `server._compile_with_perturb`, `tree_labeler.label`, `runner.compile_tree`.
- Produces: `_compile_with_perturb(nodes, attempt, pairs=None)` — new `pairs` parameter; calls `capture.record` after the first attempt.

- [ ] **Step 1: Write the failing integration tests**

Append to `mcp_harness/tests/test_capture.py`:

```python
def test_serve_hook_records_attempt0_outcome(monkeypatch, tmp_path):
    """_compile_with_perturb records the attempt-0 result, not a perturb-rescued
    one. A stub `attempt` that always ERRORs => attempt0_pack False (one row)."""
    import server
    out = tmp_path / "captured.jsonl"
    monkeypatch.setenv("IDE_CAPTURE_PATH", str(out))
    monkeypatch.setattr(capture, "_gate_verdict", lambda n, p: None)

    # always-ERROR attempt: first attempt fails, perturb loop also fails (stubbed)
    server._compile_with_perturb(STAR_NODES, lambda nodes: "ERROR: nope",
                                 pairs=STAR_PAIRS)
    rows = [json.loads(l) for l in open(out)]
    assert len(rows) == 1                       # recorded once, after attempt-0
    assert rows[0]["attempt0_pack"] is False
    assert rows[0]["pairs"] == STAR_PAIRS

    # a packing attempt: one row, attempt0_pack True
    out.unlink()
    server._compile_with_perturb(STAR_NODES, lambda nodes: FOLD, pairs=STAR_PAIRS)
    rows = [json.loads(l) for l in open(out)]
    assert len(rows) == 1 and rows[0]["attempt0_pack"] is True


def test_builder_path_does_not_capture(monkeypatch, tmp_path):
    """tree_labeler.label compiles via runner.compile_tree, NOT
    _compile_with_perturb, so even with capture enabled a build records nothing."""
    import runner
    from feasibility import tree_labeler as tl
    out = tmp_path / "captured.jsonl"
    monkeypatch.setenv("IDE_CAPTURE_PATH", str(out))
    monkeypatch.setattr(runner, "compile_tree", lambda nodes, pairs, timeout=40: ("ok", "pack"))

    tl.label(STAR_NODES, STAR_PAIRS)
    assert not out.exists()                     # build path never captured
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_capture.py -k "serve_hook or builder_path" -q`
Expected: FAIL — `_compile_with_perturb` does not accept a `pairs` keyword (TypeError), so the serve-hook test errors; the builder test fails because the hook isn't wired yet (or also errors).

- [ ] **Step 3: Wire capture into `server.py`**

Add the import near the other `from feasibility import ...` lines (next to `from feasibility import gate as _gate`):

```python
from feasibility import capture
```

Change `_compile_with_perturb`'s signature and add the capture call right after the first attempt. The function currently starts:

```python
def _compile_with_perturb(nodes: list[dict], attempt) -> str:
    """..."""
    result = attempt(nodes)
    if not result.startswith("ERROR:"):
        return result  # exact tree packed -> return untouched (deterministic)
```

Replace those lines with:

```python
def _compile_with_perturb(nodes: list[dict], attempt, pairs=None) -> str:
    """..."""
    result = attempt(nodes)
    capture.record(nodes, pairs or [], not result.startswith("ERROR:"), result)
    if not result.startswith("ERROR:"):
        return result  # exact tree packed -> return untouched (deterministic)
```

(Keep the existing docstring body unchanged.)

Update the two call sites to pass `pairs`:
- In `draft_and_compile_full_base` (the `return _compile_with_perturb(tree_nodes, attempt)` line):
  ```python
      return _compile_with_perturb(tree_nodes, attempt, pairs)
  ```
  (`pairs` is already defined earlier in that function as `symmetric_pairs or []`.)
- In `compile_base` (the `return _compile_with_perturb(_SESSION["tree_nodes"], attempt)` line):
  ```python
      return _compile_with_perturb(_SESSION["tree_nodes"], attempt, _SESSION["pairs"])
  ```

- [ ] **Step 4: Add `.gitignore` entry**

Append to `.gitignore`:

```
mcp_harness/feasibility/captured.jsonl
```

- [ ] **Step 5: Run the integration tests**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_capture.py -q`
Expected: PASS (7 passed — 5 unit + 2 integration)

- [ ] **Step 6: Run the broader serve-path suite for no regressions**

The change adds a parameter and one side-effect call to a hot serve helper; confirm the existing serve/compile tests still pass.
Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_pipeline_dual.py tests/test_capture.py -q` (and any test importing `server`)
Expected: PASS. (Capture is a no-op there because `IDE_CAPTURE_PATH` is unset.)

- [ ] **Step 7: Commit**

```bash
git add mcp_harness/server.py .gitignore mcp_harness/tests/test_capture.py
git commit -m "$(printf 'feat(server): capture served compiles via _compile_with_perturb hook\n\nThreads pairs through _compile_with_perturb and records the attempt-0 outcome\n(serve-only; the corpus builder bypasses this helper). Gitignores captured.jsonl.\n\nCo-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>')"
```

---

## Self-Review

**Spec coverage:**
- Capture point at `_compile_with_perturb`, serve-only, attempt-0 label → Task 2 (hook after first attempt) + `test_serve_hook_records_attempt0_outcome` + `test_builder_path_does_not_capture`. ✓
- `pairs` threaded into `_compile_with_perturb` from both call sites → Task 2 Step 3. ✓
- `IDE_CAPTURE_PATH` gating (set=on+dest, unset=no-op) → Task 1 `record` + `test_record_is_noop_when_disabled`. ✓
- Never raises → Task 1 try/except + `test_record_never_raises_when_gate_loader_throws`. ✓
- Row schema (all keys, corpus-compatible) → Task 1 `record` + `test_record_writes_corpus_compatible_row`. ✓
- `failure_mode` reuses `classify_status` vocabulary → Task 1 `_failure_mode` + `test_failure_mode_matches_corpus_vocabulary`. ✓
- `gate` recomputed/cached, null if absent, no train-on-demand → Task 1 `_gate_verdict`. ✓
- No circular import (lazy `classify_status`) → Task 1 `_failure_mode`. ✓
- Concurrency lock → Task 1 `_LOCK` + `test_concurrent_records_are_all_valid_lines`. ✓
- `captured.jsonl` gitignored → Task 2 Step 4. ✓

**Placeholder scan:** No TBD/TODO; every code/command step is complete. ✓

**Type consistency:** `record(nodes, pairs, attempt0_pack, result_str)` signature, `_gate_verdict(nodes, pairs)`, `_compile_with_perturb(nodes, attempt, pairs=None)`, and the row keys are consistent between Tasks 1 and 2 and the tests. `classify_status(status, msg) -> (pack, mode)` matches its real definition in `tree_labeler.py`. ✓
