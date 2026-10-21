# Shaping Agent Wiring (B2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `IDE_SHAPE_OP` env var with an `apply_shaping_ops` MCP tool: the agent maps anatomy (leaf node ids) to reverse-fold ops, pre-validated server-side, HITL suggest-then-confirm, ops travel with the fold to the display boundary.

**Architecture:** New MCP tool recompiles the tree, maps `node_id → leaf paper coordinate` via `leaf_node_locations()`, and pre-validates each op by running the real `shaping.reverse_fold` against the squared fold in sequence. The tool result wraps the raw fold plus the applied op strings (`ide_shape_ops`); `web/server.py` unwraps and replays exactly those ops on `display_json`. Spec: `docs/superpowers/specs/2026-07-01-shaping-agent-wiring-b2-design.md`.

**Tech Stack:** Python (stdlib geometry in `mcp_harness/shaping.py`, FastMCP tool in `mcp_harness/server.py`, FastAPI bridge in `web/server.py`), pytest. No frontend changes.

## Global Constraints

- Op grammar unchanged: `reverse:<x>,<y>:<d>:<theta>` (what `shaping.parse_op` accepts). Op strings are built with plain Python `str(float)` interpolation (full repr precision).
- Provenance: the fold frame's `json` is ALWAYS the raw compiled fold (never squared, never shaped, no `edges_foldAngle`); shaping rides only on `display_json`. Ops never enter the FOLD dict (foreign keys trip Oriedita).
- Tool result JSON keys, exactly: `status` (`"shaped"` | `"no_ops_applied"`), `fold`, `ide_shape_ops`, `verdicts` (each `{"node_id", "status": "applied"|"refused", "reason"?}`). `ide_shape_ops` contains ONLY applied ops, in application order.
- Target schema: `{"node_id": <int leaf id>, "fraction": float in (0,1), default 0.5, "theta": float in (0,180]}`. A refused/malformed target never aborts the batch — later targets are attempted against the last successfully shaped state.
- Display boundary stays defensive: every transform failure keeps the previous step's output; the fold stream is never broken. `IDE_SHAPE_OP` remains the fallback only when a fold arrives without tool ops.
- Existing tests must stay green (run the covering test files per task; the full backend suite runs at branch end — it takes ~9 minutes).
- Python venv: run tests as `cd mcp_harness && .venv/bin/python -m pytest ...` (backend) and from repo root `mcp_harness/.venv/bin/python -m pytest web/tests ...` (web).
- Engine-touching tests spawn real compiles (~5–20 s each); keep compile counts low (probe-verified: star-4 leaves 1 and 2 accept `fraction 0.25, theta 90`, sequentially).

---

### Task 1: `shaping.axial_length` + `shaping.apply_display_ops`

**Files:**
- Modify: `mcp_harness/shaping.py` (append after `apply_display_op`, ~line 274)
- Test: `mcp_harness/tests/test_shaping.py` (append)

**Interfaces:**
- Consumes: existing `shaping._find_tip(fold, tip_xy)`, `shaping.apply_display_op(fold, op)`, `shaping.ShapingError`.
- Produces: `axial_length(fold: dict, tip_xy) -> float` (raises `ShapingError` when no tip signature); `apply_display_ops(fold: dict, ops: list[str] | None) -> dict` (None/empty → the same input object; sequential; per-op defensive). Task 3 calls `axial_length`; Task 4 calls `apply_display_ops`.

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_shaping.py`:

```python
# Unit square with TWO opposing flap tips: right tip 2 at (1, 0.5) and left
# tip 5 at (0, 0.5), axial V creases meeting at the dangling hub 6 (0.5, 0.5).
# Each tip carries the BB+one-crease signature; the hub has two creases and
# no B edge, so it is never mistaken for a tip.
TWO_TIP_SQUARE = {
    "vertices_coords": [[0, 0], [1, 0], [1, 0.5], [1, 1], [0, 1], [0, 0.5],
                        [0.5, 0.5]],
    "edges_vertices": [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 0],
                       [2, 6], [5, 6]],
    "edges_assignment": ["B", "B", "B", "B", "B", "B", "V", "V"],
}


def test_axial_length_measures_the_tip_crease():
    assert shaping.axial_length(TIP_SQUARE, (1, 0.5)) == pytest.approx(0.5)


def test_axial_length_raises_without_tip_signature():
    square = {
        "vertices_coords": [[0, 0], [1, 0], [1, 1], [0, 1]],
        "edges_vertices": [[0, 1], [1, 2], [2, 3], [3, 0]],
        "edges_assignment": ["B", "B", "B", "B"],
    }
    with pytest.raises(shaping.ShapingError):
        shaping.axial_length(square, (1, 0.5))


def test_apply_display_ops_empty_is_identity_object():
    assert shaping.apply_display_ops(TIP_SQUARE, None) is TIP_SQUARE
    assert shaping.apply_display_ops(TIP_SQUARE, []) is TIP_SQUARE


def test_apply_display_ops_applies_sequence():
    out = shaping.apply_display_ops(
        TWO_TIP_SQUARE, ["reverse:1,0.5:0.2:90", "reverse:0,0.5:0.2:90"])
    # each reverse fold adds 3 vertices (F + two boundary hits) and 5 edges
    assert len(out["vertices_coords"]) == 7 + 3 + 3
    assert len(out["edges_vertices"]) == 8 + 5 + 5
    assert len(out["edges_foldAngle"]) == len(out["edges_vertices"])
    # input untouched
    assert len(TWO_TIP_SQUARE["edges_vertices"]) == 8
    assert "edges_foldAngle" not in TWO_TIP_SQUARE


def test_apply_display_ops_skips_failing_op_and_continues():
    out = shaping.apply_display_ops(
        TWO_TIP_SQUARE, ["garbage", "reverse:1,0.5:0.2:90"])
    assert len(out["edges_vertices"]) == 8 + 5   # second op still applied
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_shaping.py -v -k "axial_length or display_ops"`
Expected: FAIL — `AttributeError: module 'shaping' has no attribute 'axial_length'` (and `apply_display_ops`).

- [ ] **Step 3: Implement**

Append to `mcp_harness/shaping.py` (after `apply_display_op`):

```python
def axial_length(fold: dict, tip_xy) -> float:
    """Length of the axial crease of the flap tip nearest tip_xy (the flap
    span a `fraction` is taken of). Raises ShapingError when no tip
    signature exists near tip_xy."""
    tip, axial = _find_tip(fold, tip_xy)
    vc = fold["vertices_coords"]
    a, b = fold["edges_vertices"][axial]
    other = b if a == tip else a
    return math.hypot(vc[other][0] - vc[tip][0], vc[other][1] - vc[tip][1])


def apply_display_ops(fold: dict, ops: list[str] | None) -> dict:
    """Sequential display-boundary hook (B2): apply each op in order, each
    against the previous op's output. Per-op defensive like
    apply_display_op — a refused op is skipped (one stderr line) and later
    ops continue from the last good state; never raises, never breaks the
    fold stream. No/empty ops -> the input object unchanged."""
    if not ops:
        return fold
    out = fold
    for op in ops:
        out = apply_display_op(out, op)
    return out
```

- [ ] **Step 4: Run to verify they pass (plus the whole file for regressions)**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_shaping.py -v`
Expected: all PASS (22 existing + 5 new).

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/shaping.py mcp_harness/tests/test_shaping.py
git commit -m "feat(shaping): axial_length + sequential apply_display_ops (B2 groundwork)"
```

---

### Task 2: `web/fold.py` — unwrap the shaping wrapper + `extract_shape_ops`

**Files:**
- Modify: `web/fold.py`
- Test: `web/tests/test_fold.py` (append)

**Interfaces:**
- Consumes: nothing new.
- Produces: `extract_fold(output)` additionally unwraps `{"fold": <FOLD>, "ide_shape_ops": [...]}` wrappers (returns the inner FOLD); new `extract_shape_ops(output: str) -> list[str] | None`. Task 4 imports both from `web.fold`.

- [ ] **Step 1: Write the failing tests**

Append to `web/tests/test_fold.py` (add `import pytest` and extend the existing `from web.fold import extract_fold` to also import `extract_shape_ops`):

```python
def test_extract_fold_unwraps_shaping_wrapper():
    inner = {"file_spec": 1.1, "vertices_coords": [[0, 0]]}
    wrapper = {"status": "shaped", "fold": inner,
               "ide_shape_ops": ["reverse:1,0.5:0.2:90"], "verdicts": []}
    assert extract_fold(json.dumps(wrapper)) == inner


def test_extract_fold_does_not_unwrap_other_fold_wrappers():
    # suggest_flap_for_region results also carry a "fold" key; only the
    # shaping wrapper (marked by ide_shape_ops) is unwrapped.
    wrapper = {"status": "filled", "fold": {"file_spec": 1.1}}
    assert extract_fold(json.dumps(wrapper)) is None


def test_extract_shape_ops_returns_ops_list():
    wrapper = {"status": "shaped", "fold": {"file_spec": 1.1},
               "ide_shape_ops": ["reverse:1,0.5:0.2:90", "reverse:0,0.5:0.1:45"]}
    assert extract_shape_ops(json.dumps(wrapper)) == [
        "reverse:1,0.5:0.2:90", "reverse:0,0.5:0.1:45"]


def test_extract_shape_ops_empty_list_passes_through():
    wrapper = {"status": "no_ops_applied", "fold": {"file_spec": 1.1},
               "ide_shape_ops": []}
    assert extract_shape_ops(json.dumps(wrapper)) == []


@pytest.mark.parametrize("out", [
    "not json",
    '{"ide_shape_ops": ["x"]}',                            # no fold
    '{"fold": {"file_spec": 1}, "ide_shape_ops": "x"}',    # ops not a list
    '{"fold": {"file_spec": 1}, "ide_shape_ops": [1]}',    # non-string entry
    '{"fold": {"nope": 1}, "ide_shape_ops": ["x"]}',       # fold not a FOLD
    '{"file_spec": 1.1}',                                  # bare fold, no ops
    '[1, 2]',                                              # non-dict JSON
])
def test_extract_shape_ops_defensive_returns_none(out):
    assert extract_shape_ops(out) is None
```

- [ ] **Step 2: Run to verify they fail**

Run: `mcp_harness/.venv/bin/python -m pytest web/tests/test_fold.py -v` (from repo root)
Expected: FAIL — `ImportError: cannot import name 'extract_shape_ops'`.

- [ ] **Step 3: Implement**

Replace the body of `web/fold.py` below the module docstring with:

```python
from __future__ import annotations

import json


def _json_dict(output: str) -> dict | None:
    text = output.strip()
    if not text.startswith("{"):
        return None
    try:
        doc = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None
    return doc if isinstance(doc, dict) else None


def _is_fold(doc) -> bool:
    return isinstance(doc, dict) and "file_spec" in doc


def extract_fold(output: str) -> dict | None:
    """Return the parsed FOLD dict if `output` is a FOLD document, or the
    inner FOLD of an apply_shaping_ops wrapper ({"fold": <FOLD>,
    "ide_shape_ops": [...]}). Other fold-carrying tool results (e.g.
    suggest_flap_for_region) are NOT unwrapped — the ide_shape_ops key is
    the wrapper marker. Else None."""
    doc = _json_dict(output)
    if doc is None:
        return None
    if _is_fold(doc):
        return doc
    if "ide_shape_ops" in doc and _is_fold(doc.get("fold")):
        return doc["fold"]
    return None


def extract_shape_ops(output: str) -> list[str] | None:
    """The applied-ops list when `output` is an apply_shaping_ops wrapper
    with a valid inner FOLD and a list-of-strings ide_shape_ops; else None.
    Defensive: any malformation reads as 'no ops', never an error."""
    doc = _json_dict(output)
    if doc is None or "ide_shape_ops" not in doc or not _is_fold(doc.get("fold")):
        return None
    ops = doc["ide_shape_ops"]
    if not (isinstance(ops, list) and all(isinstance(o, str) for o in ops)):
        return None
    return ops
```

Also update the module docstring's second paragraph to mention the wrapper:

```python
"""Recognize a FOLD document inside a tool's text output.

A FOLD file is JSON with a top-level "file_spec" key (the FOLD spec's version
marker). We content-sniff that key rather than keying on which tool produced the
output, so detection stays correct as backend tools are renamed or added.

The apply_shaping_ops tool (B2) returns a wrapper {"fold": <FOLD>,
"ide_shape_ops": [...]} instead of a bare FOLD; extract_fold unwraps it and
extract_shape_ops reads the ops the display boundary must replay.
"""
```

- [ ] **Step 4: Run to verify all fold tests pass**

Run: `mcp_harness/.venv/bin/python -m pytest web/tests/test_fold.py -v`
Expected: all PASS (5 existing + 11 new).

- [ ] **Step 5: Commit**

```bash
git add web/fold.py web/tests/test_fold.py
git commit -m "feat(web): unwrap apply_shaping_ops wrapper + extract_shape_ops"
```

---

### Task 3: the `apply_shaping_ops` MCP tool

**Files:**
- Modify: `mcp_harness/server.py` — `_worker_compile_and_regions` (~line 161) and a new tool after `suggest_flap_for_region` (~line 549)
- Test: `mcp_harness/tests/test_shaping_tool.py` (create)

**Interfaces:**
- Consumes: `shaping.axial_length(fold, tip_xy)` and `shaping.reverse_fold(fold, tip_xy, d, theta)` (Task 1 / existing), `square_complete.complete_square(fold, w, h)`, existing `_run_isolated` / `_worker_compile_and_regions` spawn plumbing.
- Produces: MCP tool `apply_shaping_ops(tree_nodes, symmetric_pairs=None, targets=None, paper_width=1.0, paper_height=1.0) -> str` returning the wrapper JSON per Global Constraints. `_worker_compile_and_regions` payload gains a `"locs"` key (`[[node_id, x, y], ...]`). Task 4's display path and Task 5's prompt reference this tool by name.

- [ ] **Step 1: Write the failing tests**

Create `mcp_harness/tests/test_shaping_tool.py`:

```python
"""apply_shaping_ops (B2): engine-level tests through the real spawn compile.

Parameters are probe-verified: every star-4 leaf accepts a reverse fold at
fraction 0.2-0.5 / theta 90 on the squared compile, including sequentially
on two different leaves. Each _run() spawns a real compile (~5-20 s); tests
batch targets to keep compile counts low.
"""
import json
import sys
sys.path.insert(0, "tests")
from cases import CASES_BY_NAME   # noqa: E402
import server                     # noqa: E402
import shaping                    # noqa: E402
import square_complete            # noqa: E402


def _run(targets, case="star-4"):
    nodes, pairs = CASES_BY_NAME[case]
    return json.loads(server.apply_shaping_ops(
        tree_nodes=nodes, symmetric_pairs=[list(p) for p in pairs],
        targets=targets))


def test_two_targets_apply_in_sequence():
    out = _run([{"node_id": 1, "fraction": 0.25, "theta": 90},
                {"node_id": 2, "fraction": 0.25, "theta": 90}])
    assert out["status"] == "shaped"
    assert [v["status"] for v in out["verdicts"]] == ["applied", "applied"]
    assert [v["node_id"] for v in out["verdicts"]] == [1, 2]
    assert len(out["ide_shape_ops"]) == 2
    for op in out["ide_shape_ops"]:
        shaping.parse_op(op)                      # grammar round-trips
    # provenance: the returned fold is the RAW compile artifact
    assert "file_spec" in out["fold"]
    assert "edges_foldAngle" not in out["fold"]

    # the display boundary replays EXACTLY these ops on the squared fold:
    # both must apply there too (this is the tool's core promise)
    squared = square_complete.complete_square(out["fold"], 1.0, 1.0)
    shaped = shaping.apply_display_ops(squared, out["ide_shape_ops"])
    # two reverse folds -> +10 edges over the squared base
    assert len(shaped["edges_vertices"]) == len(squared["edges_vertices"]) + 10
    assert len(shaped["edges_foldAngle"]) == len(shaped["edges_vertices"])


def test_mixed_verdicts_do_not_abort_the_batch():
    out = _run([
        {"node_id": 99, "theta": 90},                    # unknown leaf
        {"node_id": 1, "fraction": 1.5, "theta": 90},    # fraction out of range
        {"node_id": 1, "theta": 200},                    # theta out of range
        {"node_id": 2, "fraction": 0.25, "theta": 90},   # fine
    ])
    stats = [v["status"] for v in out["verdicts"]]
    assert stats == ["refused", "refused", "refused", "applied"]
    assert "node_id" in out["verdicts"][0]["reason"]
    assert "fraction" in out["verdicts"][1]["reason"]
    assert "theta" in out["verdicts"][2]["reason"]
    assert out["status"] == "shaped"
    assert len(out["ide_shape_ops"]) == 1


def test_no_targets_returns_no_ops_applied():
    out = _run([])
    assert out["status"] == "no_ops_applied"
    assert out["ide_shape_ops"] == []
    assert out["verdicts"] == []
    assert "file_spec" in out["fold"]


def test_error_when_tree_does_not_compile():
    out = server.apply_shaping_ops(
        tree_nodes=[], symmetric_pairs=[],
        targets=[{"node_id": 1, "theta": 90}])
    assert out.startswith("ERROR:")
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_shaping_tool.py -v`
Expected: FAIL — `AttributeError: module 'server' has no attribute 'apply_shaping_ops'`.

- [ ] **Step 3: Extend `_worker_compile_and_regions` to return leaf locations**

In `mcp_harness/server.py`, inside `_worker_compile_and_regions`, change `_try_once` and both success payloads:

```python
        def _try_once(ns):
            engine = ht_child.HeadlessTreemaker()
            engine.init_paper(paper_width, paper_height)
            engine.build_tree_from_json(json.dumps(ns))
            for a, b in pairs:
                engine.apply_symmetry(int(a), int(b))
            scale = engine.run_scale_optimization()   # Fix 2: capture real scale
            fold = engine.build_and_export()
            locs = list(engine.leaf_node_locations())
            regions = free_paper.free_paper_regions(locs, paper_width, paper_height)
            return fold, regions, scale, locs
```

Attempt-0 payload:

```python
        try:
            fold, regions, scale, locs = _try_once(nodes)
            # Attempt 0 is unannotated — tree and fold match exactly.
            queue.put(("ok", json.dumps({"fold": fold, "regions": regions,
                                         "scale": scale, "locs": locs})))
            return
        except Exception:
            pass
```

Perturb-loop payload (note: `locs` are measured on the SAME jittered tree as the returned fold, so they stay consistent):

```python
            try:
                fold, regions, scale, locs = _try_once(jittered)
                # Fix 1: annotate the fold so tree/fold divergence is explicit,
                # matching _compile_with_perturb / draft_and_compile_full_base.
                fold = _annotate_perturbed(fold, t)
                queue.put(("ok", json.dumps({"fold": fold, "regions": regions,
                                             "scale": scale, "locs": locs})))
                return
```

(`suggest_flap_for_region` reads only `fold`/`regions`/`scale` from this payload; the extra key is inert there.)

- [ ] **Step 4: Add the tool**

In `mcp_harness/server.py`, directly after `suggest_flap_for_region` (before the `_GATE` block), add:

```python
@mcp.tool()
def apply_shaping_ops(
    tree_nodes: list[dict],
    symmetric_pairs: list[list[int]] | None = None,
    targets: list[dict] | None = None,
    paper_width: float = 1.0,
    paper_height: float = 1.0,
) -> str:
    """B2 honest shaping: pose a compiled base in 3D by bending flaps with
    inside reverse folds. Recompiles the tree, maps each target's leaf
    node_id to its paper coordinate, and pre-validates every op against the
    squared fold IN SEQUENCE with the real reverse-fold geometry — what this
    tool reports as applied is exactly what the 3D Model tab will render.
    ONLY call this after the user confirms the proposed pose.

    targets: [{"node_id": <leaf id from your compiled tree>,
               "fraction": 0-1 fold point along the flap from the tip
               (default 0.5), "theta": bend degrees in (0, 180]}].
    Bend direction follows the flap's axial crease M/V family; theta is a
    magnitude only.

    Returns JSON: {"status": "shaped"|"no_ops_applied", "fold": <raw
    compiled FOLD — untouched, for provenance>, "ide_shape_ops": [<applied
    ops, in order>], "verdicts": [{"node_id", "status":
    "applied"|"refused", "reason"?}]}. A refused target never aborts the
    batch. Returns 'ERROR: ...' if the base tree does not compile.
    """
    import shaping
    import square_complete
    pairs = [list(p) for p in (symmetric_pairs or [])]
    raw = _run_isolated(_worker_compile_and_regions, json.dumps(tree_nodes),
                        pairs, paper_width, paper_height)
    if raw.startswith("ERROR:"):
        return f"ERROR: base tree did not compile ({raw})"
    try:
        base = json.loads(raw)
    except Exception as exc:
        return f"ERROR: base tree did not compile ({exc})"
    if not isinstance(base, dict):
        return f"ERROR: base tree did not compile ({base})"
    fold = base["fold"]
    if isinstance(fold, str):
        fold = json.loads(fold)
    locs = {int(n): (x, y) for n, x, y in base.get("locs", [])}

    # Pre-validate on the SQUARED copy: the display boundary squares before
    # shaping (wedge creases must land on real paper boundary), so the ops
    # must be proven against that same geometry. Defensive like
    # _square_for_display: a squaring failure degrades identically here and
    # at display time.
    try:
        current = square_complete.complete_square(fold, paper_width,
                                                  paper_height)
    except Exception:
        current = fold

    ops: list[str] = []
    verdicts: list[dict] = []
    for t in (targets or []):
        nid = t.get("node_id") if isinstance(t, dict) else None
        if not isinstance(nid, int) or nid not in locs:
            verdicts.append({"node_id": nid, "status": "refused",
                             "reason": "unknown or non-leaf node_id"})
            continue
        try:
            fraction = float(t.get("fraction", 0.5))
            theta = float(t["theta"])
        except (KeyError, TypeError, ValueError):
            verdicts.append({"node_id": nid, "status": "refused",
                             "reason": "target needs numeric theta "
                                       "(fraction optional)"})
            continue
        if not 0 < fraction < 1:
            verdicts.append({"node_id": nid, "status": "refused",
                             "reason": "fraction must be in (0, 1)"})
            continue
        if not 0 < theta <= 180:
            verdicts.append({"node_id": nid, "status": "refused",
                             "reason": "theta must be in (0, 180]"})
            continue
        x, y = locs[nid]
        try:
            d = fraction * shaping.axial_length(current, (x, y))
            current = shaping.reverse_fold(current, (x, y), d, theta)
        except shaping.ShapingError as exc:
            verdicts.append({"node_id": nid, "status": "refused",
                             "reason": str(exc)})
            continue
        ops.append(f"reverse:{x},{y}:{d}:{theta}")
        verdicts.append({"node_id": nid, "status": "applied"})

    return json.dumps({
        "status": "shaped" if ops else "no_ops_applied",
        "fold": fold,
        "ide_shape_ops": ops,
        "verdicts": verdicts,
    })
```

- [ ] **Step 5: Run the new tests (each spawns real compiles; allow ~2 min)**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_shaping_tool.py -v`
Expected: 4 PASS.

- [ ] **Step 6: Run the neighbors that share the worker**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_flap_fill_tool.py tests/test_shaping.py -v`
Expected: all PASS (`suggest_flap_for_region` tolerates the new `locs` key).

- [ ] **Step 7: Commit**

```bash
git add mcp_harness/server.py mcp_harness/tests/test_shaping_tool.py
git commit -m "feat(mcp): apply_shaping_ops tool — anatomy->reverse-fold ops, sequence-validated (B2)"
```

---

### Task 4: display-boundary wiring in `web/server.py`

**Files:**
- Modify: `web/server.py:33` (import) and `web/server.py:104-116` (fold frame)
- Test: `web/tests/test_server.py` (append)

**Interfaces:**
- Consumes: `web.fold.extract_shape_ops` (Task 2), `shaping.apply_display_ops` (Task 1).
- Produces: fold frames whose `display_json` reflects tool-provided ops; `IDE_SHAPE_OP` only as fallback. No API change visible to the frontend.

- [ ] **Step 1: Write the failing tests**

Append to `web/tests/test_server.py`. The tests monkeypatch `_square_for_display` to identity after the reload — squaring has its own tests (`test_ws_splits_validated_hull_and_squared_display`); these isolate the shaping wiring:

```python
# Unit-square fold with one flap tip at (1, 0.5), axial V crease inward —
# accepts "reverse:1,0.5:0.2:90" (same fixture family as test_shaping.py).
_TIP_FOLD = {
    "file_spec": 1.1,
    "vertices_coords": [[0, 0], [1, 0], [1, 0.5], [1, 1], [0, 1], [0.5, 0.5]],
    "edges_vertices": [[0, 1], [1, 2], [2, 3], [3, 4], [4, 0], [2, 5]],
    "edges_assignment": ["B", "B", "B", "B", "B", "V"],
}


def _shaping_client(monkeypatch, tool_output, env_op=None):
    import agent_loop
    import llm_client
    from types import SimpleNamespace

    async def fake_connect(stack):
        return SimpleNamespace(sessions={}, tools=[], route={})

    monkeypatch.setattr(agent_loop, "connect_servers", fake_connect)
    monkeypatch.setattr(
        llm_client.LLMClient, "from_env",
        classmethod(lambda cls: SimpleNamespace(cfg=SimpleNamespace(
            provider="fake", model="fake"))),
    )

    async def fake_turn(client_, backend, messages, emit=None):
        emit({"type": "tool_result", "name": "apply_shaping_ops",
              "output": tool_output, "is_error": False})

    monkeypatch.setattr(agent_loop, "agent_turn", fake_turn)
    if env_op is None:
        monkeypatch.delenv("IDE_SHAPE_OP", raising=False)
    else:
        monkeypatch.setenv("IDE_SHAPE_OP", env_op)

    import importlib
    import web.server as server
    importlib.reload(server)
    # isolate shaping wiring from squaring (squaring has its own tests)
    monkeypatch.setattr(server, "_square_for_display", lambda f: f)
    return TestClient(server.app)


def _fold_frame(client):
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "prompt", "text": "pose it"})
        frames = [ws.receive_json() for _ in range(3)]
    return next(f for f in frames if f["type"] == "fold")


def test_ws_applies_tool_ops_to_display_json(monkeypatch):
    wrapper = {"status": "shaped", "fold": _TIP_FOLD,
               "ide_shape_ops": ["reverse:1,0.5:0.2:90"],
               "verdicts": [{"node_id": 1, "status": "applied"}]}
    frame = _fold_frame(_shaping_client(monkeypatch, json.dumps(wrapper)))
    # provenance: json = the raw inner fold, untouched
    assert frame["json"] == _TIP_FOLD
    assert "edges_foldAngle" not in frame["json"]
    # display: the op was replayed (a reverse fold adds 5 edges)
    assert len(frame["display_json"]["edges_vertices"]) == 6 + 5
    assert "edges_foldAngle" in frame["display_json"]


def test_ws_tool_ops_beat_env_op(monkeypatch):
    # wrapper ops present -> IDE_SHAPE_OP must NOT be applied on top
    wrapper = {"status": "shaped", "fold": _TIP_FOLD,
               "ide_shape_ops": ["reverse:1,0.5:0.2:90"], "verdicts": []}
    frame = _fold_frame(_shaping_client(
        monkeypatch, json.dumps(wrapper), env_op="reverse:1,0.5:0.3:45"))
    assert len(frame["display_json"]["edges_vertices"]) == 6 + 5  # one op only


def test_ws_env_op_still_shapes_bare_folds(monkeypatch):
    # tracer behavior preserved: bare FOLD + IDE_SHAPE_OP -> shaped display
    frame = _fold_frame(_shaping_client(
        monkeypatch, json.dumps(_TIP_FOLD), env_op="reverse:1,0.5:0.2:90"))
    assert frame["json"] == _TIP_FOLD
    assert len(frame["display_json"]["edges_vertices"]) == 6 + 5


def test_ws_bare_fold_without_env_is_untouched(monkeypatch):
    frame = _fold_frame(_shaping_client(monkeypatch, json.dumps(_TIP_FOLD)))
    assert frame["display_json"] == _TIP_FOLD   # identity path
```

- [ ] **Step 2: Run to verify they fail**

Run: `mcp_harness/.venv/bin/python -m pytest web/tests/test_server.py -v -k "tool_ops or env_op or bare_fold"`
Expected: the wrapper tests FAIL (no fold frame emitted — the wrapper isn't recognized until Task 2's `extract_fold` is wired here… Task 2 already shipped `extract_fold` unwrapping, so the first test fails differently: the fold frame appears but `display_json` has only 6 edges — no ops applied). Either failure mode is fine; the point is they fail before Step 3.

- [ ] **Step 3: Implement the wiring**

In `web/server.py`, change the import (line 33):

```python
from web.fold import extract_fold, extract_shape_ops  # noqa: E402
```

Replace the fold-frame block (the `fold = extract_fold(output)` clause inside `_send_frames`):

```python
        fold = extract_fold(output)
        if fold is not None:
            # json = the raw fold the agent actually linted (Download + JSON
            # tab); display_json = the squared + shaped copy for the 3D
            # viewers only. Ops come from the apply_shaping_ops wrapper when
            # present (B2); IDE_SHAPE_OP is the debug fallback for folds
            # that arrive without ops. Provenance per
            # docs/superpowers/specs/2026-07-01-shaping-agent-wiring-b2-design.md
            ops = extract_shape_ops(output)
            if not ops:
                env_op = os.environ.get("IDE_SHAPE_OP")
                ops = [env_op] if env_op else []
            await ws.send_json({"type": "fold", "filename": "model.fold",
                                "json": fold,
                                "display_json": shaping.apply_display_ops(
                                    _square_for_display(fold), ops)})
```

- [ ] **Step 4: Run the full web suite**

Run: `mcp_harness/.venv/bin/python -m pytest web/tests -v`
Expected: all PASS (existing 9 + new 4).

- [ ] **Step 5: Commit**

```bash
git add web/server.py web/tests/test_server.py
git commit -m "feat(web): display boundary replays apply_shaping_ops ops; env var demoted to fallback"
```

---

### Task 5: HITL prompt wiring in `agent_loop.py`

**Files:**
- Modify: `mcp_harness/agent_loop.py` — insert into `SYSTEM_PROMPT` after the free-paper frontier block (after the line "the frontier above, not a retry target." ~line 264, before the Golden Base paragraph)
- Test: `mcp_harness/tests/test_agent_shaping_prompt.py` (create)

**Interfaces:**
- Consumes: the tool name `apply_shaping_ops` and target schema from Task 3.
- Produces: prompt text only; no code interface.

- [ ] **Step 1: Write the failing test**

Create `mcp_harness/tests/test_agent_shaping_prompt.py` (same substring-pinning style as `test_agent_reference_prompt.py`):

```python
"""B2 HITL contract: the prompt must teach suggest-then-confirm shaping."""
import agent_loop

P = agent_loop.SYSTEM_PROMPT


def test_prompt_names_the_tool_and_target_schema():
    assert "apply_shaping_ops" in P
    assert "node_id" in P and "fraction" in P and "theta" in P


def test_prompt_requires_user_approval_before_calling():
    assert "ONLY AFTER THE USER APPROVES" in P


def test_prompt_teaches_verdict_handling_and_optionality():
    assert "refused" in P
    # shaping must never read as a lint/packing remedy
    assert "never required" in P
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_agent_shaping_prompt.py -v`
Expected: FAIL — `assert "apply_shaping_ops" in P`.

- [ ] **Step 3: Add the prompt section**

In `mcp_harness/agent_loop.py`, insert between the frontier block's closing line ("...the frontier above, not a retry target.") and the "(For an already-solved \"Golden Base\" file..." paragraph:

```python
SHAPING (3D POSING) -- OPTIONAL POLISH, HITL, ONLY AFTER A BASE COMPILES
When the user asks to POSE or SHAPE a compiled base ("bend the head down", \
"make it stand"), do NOT redraft the tree and do NOT treat it as a math fix. \
Instead: (1) PROPOSE the pose in plain language -- which flaps, named by their \
tree node ids and anatomical meaning (e.g. "node 4, the head"), where along \
each flap the bend sits (fraction from the tip, 0-1, default 0.5), and the \
bend angle theta in degrees (0-180; 180 is a flat reverse fold, 90 stands the \
tip perpendicular). (2) ONLY AFTER THE USER APPROVES, call \
apply_shaping_ops(tree_nodes=<the SAME tree you compiled>, \
symmetric_pairs=<the same pairs>, targets=[{node_id, fraction, theta}, ...]). \
Bend direction follows the flap's axial crease mountain/valley family -- theta \
is a magnitude only. Read the verdicts honestly: "applied" targets render \
posed in the 3D Model tab automatically (no further call needed); for each \
"refused" target, report its geometric reason verbatim, suggest an adjusted \
fraction or theta, and re-confirm with the user before calling the tool \
again. Shaping is optional polish on a finished base -- never required, and \
never a remedy for lint or packing failures.

```

(As with the rest of `SYSTEM_PROMPT`, keep the `\`-continuation string style of the surrounding lines.)

- [ ] **Step 4: Run the prompt tests (new + existing prompt pins)**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_agent_shaping_prompt.py tests/test_agent_reference_prompt.py -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/agent_loop.py mcp_harness/tests/test_agent_shaping_prompt.py
git commit -m "feat(agent): SYSTEM_PROMPT teaches HITL shaping via apply_shaping_ops (B2)"
```

---

### Task 6: full-suite gate + live acceptance

**Files:**
- None created (manual verification + evidence). Modify nothing unless a failure is found.

**Interfaces:**
- Consumes: everything above.
- Produces: the branch-ready state.

- [ ] **Step 1: Full backend suite**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/ -q` (takes ~9 min)
Expected: all pass (was 266 passed / 3 skipped at branch start; now +~17).

- [ ] **Step 2: Web suite + frontend build sanity**

Run (repo root): `mcp_harness/.venv/bin/python -m pytest web/tests -q`
Expected: all pass. (No frontend source changed; skip the npm build.)

- [ ] **Step 3: Live acceptance demo (manual, Groq)**

1. Ensure `IDE_SHAPE_OP` is **unset**. Start the server:
   `LLM_PROVIDER=groq mcp_harness/.venv/bin/python -m uvicorn web.server:app --port 8000`
   (`.env` has `LLM_PROVIDER=claude` but the Anthropic key is out of credits; Groq llama has known tool-call 400 flakes — retry the prompt if a turn errors.)
2. In the chat: ask for a simple subject (e.g. "design a dog"). Wait for the compiled base + fold frame; Model tab shows the flat-ish base.
3. Ask: "bend its head down". EXPECT: the agent proposes flaps/fraction/theta in plain language and asks for confirmation — it must NOT call the tool yet.
4. Confirm. EXPECT: one `apply_shaping_ops` call; a new fold frame; the Model tab re-folds and shows the posed base (converge-or-reject capture may take up to ~60 s). Verify the JSON tab / Download still serve the raw fold (no `edges_foldAngle`).
5. Identity checks: send a prompt that compiles without shaping — display matches today's behavior. Then restart with `IDE_SHAPE_OP="reverse:0.319,0.0:0.09:90"` and replay the tracer's bear fixture path (or any compile) to confirm the fallback still shapes bare folds.
6. Capture screenshots of the posed model into `docs/` as acceptance evidence (convention: `docs/b2-*.png`).

- [ ] **Step 4: Commit evidence**

```bash
git add docs/b2-*.png
git commit -m "docs(shaping): B2 live acceptance evidence — agent-proposed pose rendered in Model tab"
```
