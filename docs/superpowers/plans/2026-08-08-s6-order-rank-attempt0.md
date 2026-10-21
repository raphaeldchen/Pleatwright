# Goal 1 S6 — rank the attempt-0 pack — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **This run: executed INLINE in the same session that wrote this plan.**
> The planning session already holds full context (spec, coordination docs,
> the code around every call site, a reproduced R1-R3 fixture) that a fresh
> subagent would have to re-derive from scratch at real cost, and the task is
> a single Python-only slice with no independent-review requirement in its
> brief. Executed here rather than dispatched.

**Goal:** Open `server.py`'s attempt-0 short-circuit so a non-bijective
control is ranked against its own depth-1 `rescue_ladder.order_variants`
siblings (one batched child spawn) instead of always being served untouched,
per `docs/superpowers/specs/2026-08-06-order-rank-attempt0-design.md`.

**Architecture:** A new pure module `order_rank.py` owns the ranking RULE
(K1-K5) and the §2.1 predicate gate, operating only on already-compiled fold
strings — no engine, no spawn, unit-testable standalone. `server.py` gains
one new batched worker (`_worker_rank_variants`, mirroring
`_worker_compile_and_regions`'s "whole ladder in one child" precedent) and a
small amount of orchestration inside `_compile_with_perturb`, gated behind an
optional `rank_variants` callback that only `draft_and_compile_full_base`
supplies (`compile_base`'s session/recipe path is untouched — see "Scope
decision" below).

**Tech Stack:** Python 3.14, pytest, the existing `HeadlessTreemaker` pybind
engine (no C++ changes).

## Global Constraints

- Branch: `claude/goal-1-s6-order-rank`, off `482c689` (origin/main). Main is
  green at that commit region (per goal PROGRESS/COORDINATION).
- Do not touch `TreemakerWrapper.cpp`, `paper_coverage.py`, or `CLAUDE.md`.
- Do not re-bless `mcp_harness/fixtures/scorecard_baseline.jsonl`.
- `rescue_stage` must stay `"none"` and `attempt0_pack` must stay `True` on a
  re-ranked serve (this is the fact `tests/test_mesh_to_tree.py`'s shipped
  contract around line 135 depends on: `stage != STAGE_EXACT ⟹ attempt0_pack
  is False`, so the converse must hold too).
- Never mark a re-ranked serve with `rescue_stage` or a new ladder stage.
- Depth 1 only: a variant whose own attempt-0 fails is discarded, never
  rescued through its own ladder.
- Rank on the PARSED 6-decimal `design_scale` (`fold_meta.scale_from_fold_str`
  / `scale_from_raw`), never the raw engine float, never `hull_coverage`.
- A `None` `design_scale` on any survivor REFUSES ranking and falls back
  byte-identically to today's behaviour — never coerce to `0.0`.
- `PYTHONPATH=.:tests <venv python> -m pytest tests/ --timeout=420` is the
  full-suite command; venv is
  `<repo>/mcp_harness/.venv/bin/python`.
  Build (if ever needed) with
  `PYTHON=<that venv python> ./build.sh` — **not** bare `./build.sh`.
  This worktree's `.so` and `oriedita`/`OrieditaValidator.class` are already
  present and verified working; no rebuild is expected during this plan.

## Scope decision, stated once so it is not re-litigated

`_compile_with_perturb` is shared by two callers: `draft_and_compile_full_base`
(the one-shot pipeline, `_worker_full_base`) and `compile_base` (the
incremental session pipeline, `_worker_compile_recipe`, which replays a
recipe and can also run strain optimization). Every number in the design
spec, every acceptance criterion in this slice's brief, and the entire
154-arm sweep are about the one-shot pipeline. Batching a second, differently
-shaped worker for the recipe-replay path is not specced, not measured, and
not required by any acceptance criterion. `_compile_with_perturb` therefore
gains an **optional** `rank_variants` callback (default `None`); only
`draft_and_compile_full_base` supplies one. `compile_base` passes nothing,
so its behaviour is provably unchanged (same call, same arguments it already
had). This is called out explicitly rather than silently narrowed.

---

## Task 1: `order_rank.py` — the pure ranking rule

**Files:**
- Create: `mcp_harness/order_rank.py`
- Test: `mcp_harness/tests/test_order_rank.py`

**Interfaces:**
- Consumes: `fold_meta.scale_from_fold_str`, `cp_mirror.mirror_verdict`,
  `rescue_ladder.STUB_MARKER` (NOT `mesh_to_tree.served_stub_flaps` — that
  module imports numpy/networkx/skeletor/trimesh at module level, and
  `order_rank` must be importable from `server.py`'s top level without
  dragging that weight into every spawned child; see the module docstring
  below for the measured argument this mirrors).
- Produces (used by Task 2):
  - `order_rank.AXIS_DEGREES = 45.0`
  - `order_rank.RANK_MARKER: str` — the new frame_title marker text (a
    constant, not a function)
  - `order_rank.rank_note(variant_name: str) -> str` — the note body to hand
    `_append_frame_note`
  - `order_rank.is_bijection(fold_str: str) -> bool` — the §2.1 predicate
  - `order_rank.rank(fold_strs: list[str]) -> int | None` — `fold_strs[0]` is
    the control; returns the winning index (0 == control keeps serving,
    non-zero == that index's variant should serve), or `None` to REFUSE
    (any survivor's `design_scale` is unparseable)

- [ ] **Step 1: Write the failing tests using the regenerated R1-R3 fixture**

`tests/goldens/order_rank_r1r3.json` already exists (regenerated this
session from committed trees — see the module docstring of
`probe_order_rank_r1r3.py`) with this shape per subject:
`{"subject", "pairs", "arms": [{"name", "ok", "fold", "design_scale",
"is_bijection", "mv_swapped", "residual", "cardinality", "n_vertices"}, ...]}`,
arm 0 always `"control"`, matching `rescue_ladder.order_variants`'s order for
the rest.

```python
import json
import os

import pytest

import order_rank

HERE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(HERE, "goldens", "order_rank_r1r3.json")) as _f:
    _FIXTURE = json.load(_f)


def _fold_strs(subject):
    arms = [a for a in _FIXTURE[subject]["arms"] if a["ok"]]
    names = [a["name"] for a in arms]
    strs = [json.dumps(a["fold"]) for a in arms]
    return names, strs


def test_r1_humanoid_canonical_loses_to_seeded_1_on_scale_alone():
    """R1 (design spec S4.1): mesh-humanoid/canonical is bijective, residual
    0.0, 50/50 cardinality (the largest of any arm) -- "first bijection
    wins" / "most matched vertices wins" / "lowest residual wins" all pick
    it. It must LOSE. Reproduced this session: canonical is scale 0.598116,
    mv_swapped 26; seeded_1 is scale 0.775554, mv_swapped 2 -- K2 (scale)
    already resolves it before K3/K4 are even consulted."""
    names, strs = _fold_strs("mesh-humanoid")
    win = order_rank.rank(strs)
    assert names[win] == "seeded_1", (names, win)
    assert names[win] != "canonical"


def test_r2_hshape_seeded_2_loses_the_parsed_tie():
    """R2: hshape/seeded_2 beats control by 2.3e-9 on the RAW engine float
    and is NOT a bijection. Ranking the raw float would pick it and lose the
    control's bijection for noise below the emitter's own precision; ranking
    the PARSED 6-decimal value (both read 0.589256) ties K1/K2 and K3
    (is_bijection) resolves it to control."""
    names, strs = _fold_strs("hshape")
    win = order_rank.rank(strs)
    assert names[win] == "control", (names, win)


def test_r3_star4sym_seeded_3_loses_at_k4():
    """R3: star-4-sym/seeded_3 ties control at 6dp and is ALSO a bijection
    (K1/K2/K3 all tie), but it carries mv_swapped=2 against control's 0 --
    K4 must break the tie toward control."""
    names, strs = _fold_strs("star-4-sym")
    win = order_rank.rank(strs)
    assert names[win] == "control", (names, win)


def test_r4_stub_flaps_never_sold_for_scale():
    """R4 (constructed): a scale-maximal arm carrying stub_flaps > 0 must
    LOSE to a lower-scale arm with none -- K1 sits ahead of K2."""
    import rescue_ladder
    control = json.dumps({"frame_title": "scale=0.500000",
                          "vertices_coords": [[0, 0], [1, 0], [0, 1]],
                          "edges_vertices": [[0, 1], [1, 2], [2, 0]],
                          "edges_assignment": ["B", "B", "B"]})
    stub = json.dumps({
        "frame_title": (f"scale=0.900000 {rescue_ladder.STUB_MARKER} 2]"),
        "vertices_coords": [[0, 0], [1, 0], [0, 1]],
        "edges_vertices": [[0, 1], [1, 2], [2, 0]],
        "edges_assignment": ["B", "B", "B"]})
    win = order_rank.rank([control, stub])
    assert win == 0, "a stub-carrying candidate must never outrank on scale"


def test_r5_coverage_never_buys_a_scale_loss():
    """R5 (constructed): {A: scale 0.70} vs {B: scale 0.75} -- B must win.
    hull_coverage is not a rank() input at all (by construction, the
    function's signature has no coverage parameter), which is itself the
    proof that coverage can never buy a scale loss."""
    a = json.dumps({"frame_title": "scale=0.700000",
                    "vertices_coords": [[0, 0], [1, 0], [0, 1]],
                    "edges_vertices": [[0, 1], [1, 2], [2, 0]],
                    "edges_assignment": ["B", "B", "B"]})
    b = json.dumps({"frame_title": "scale=0.750000",
                    "vertices_coords": [[0, 0], [1, 0], [0, 1]],
                    "edges_vertices": [[0, 1], [1, 2], [2, 0]],
                    "edges_assignment": ["B", "B", "B"]})
    win = order_rank.rank([a, b])
    assert win == 1


def test_r6_missing_scale_refuses():
    """R6 (constructed): a fold whose frame_title carries no scale= must
    REFUSE (rank() returns None), never coerce to 0.0."""
    no_scale = json.dumps({"frame_title": "no scale here",
                           "vertices_coords": [[0, 0], [1, 0], [0, 1]],
                           "edges_vertices": [[0, 1], [1, 2], [2, 0]],
                           "edges_assignment": ["B", "B", "B"]})
    ok = json.dumps({"frame_title": "scale=0.700000",
                     "vertices_coords": [[0, 0], [1, 0], [0, 1]],
                     "edges_vertices": [[0, 1], [1, 2], [2, 0]],
                     "edges_assignment": ["B", "B", "B"]})
    assert order_rank.rank([ok, no_scale]) is None
    assert order_rank.rank([no_scale, ok]) is None


def test_predicate_gate_hshape_control_is_already_bijective():
    """S2.1: the predicate gate reads off the CONTROL alone. hshape's
    control is already a bijection, so a caller must never spawn the
    search for it."""
    _, strs = _fold_strs("hshape")
    assert order_rank.is_bijection(strs[0]) is True


def test_predicate_gate_fires_on_a_non_bijective_control():
    _, strs = _fold_strs("mesh-humanoid")
    assert order_rank.is_bijection(strs[0]) is False
```

- [ ] **Step 2: Run to verify failure** (`order_rank` module does not exist
      yet)

Run: `cd mcp_harness && PYTHONPATH=.:tests <venv python> -m pytest
tests/test_order_rank.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'order_rank'`

- [ ] **Step 3: Write `order_rank.py`**

```python
"""S6 (order-rank-attempt0): rank the attempt-0 pack among its own
depth-1 `rescue_ladder.order_variants` siblings instead of always serving
the caller's exact node order untouched.

See docs/superpowers/specs/2026-08-06-order-rank-attempt0-design.md sections
2 and 4 for the full rationale; this module is deliberately the RULE only --
independent of the engine, of spawning, and of rescue_ladder's rung
vocabulary (this ranks already-COMPILED fold strings, not un-run rungs), so
the required-fail inputs (COORDINATION.md #4.1) can be pinned without an
engine build.

Import-cheap by design, like fold_meta and cp_mirror (both already
import-cheap for the same reason): this module is imported at server.py's
top level, which every spawned compile child re-imports from disk. It
therefore does NOT import mesh_to_tree (numpy/networkx/skeletor/trimesh at
module level) even though mesh_to_tree.served_stub_flaps does exactly what
K1 needs -- _stub_flaps_in below duplicates that one small function against
rescue_ladder.STUB_MARKER (itself cheap: copy/math/random only) rather than
pay that import cost on every spawn, which is precisely the +8.89s/serve
regression (97% = `import server`) the design spec's S2.2 measured and this
slice exists to avoid reintroducing.
"""
from __future__ import annotations

import json

import cp_mirror
import fold_meta
import rescue_ladder

AXIS_DEGREES = 45.0

#: NOT a rescue stage -- the served ordering DID pack at attempt-0
#: (rescue_stage stays "none", attempt0_pack stays True; see
#: mcp_harness/tests/test_mesh_to_tree.py's shipped contract). This marker
#: exists only because agent_loop's SYSTEM_PROMPT tells the model "send
#: tree_nodes UNCHANGED -- node list position sets each node's initial
#: placement" (server.py's own doctrine to the agent); a silently reordered
#: serve would contradict that promise. Deliberately does not contain, and
#: is not contained by, any rescue_ladder marker, and does not contain the
#: jitter note's "did not pack exactly" phrase -- same three invariants
#: rescue_ladder's own markers keep, checked in test_order_rank.py.
RANK_MARKER = "[ide: served a re-ranked attempt-0 ordering:"


def rank_note(variant_name: str) -> str:
    return (f" {RANK_MARKER} '{variant_name}'] your node order packed, but "
            "a different attempt-0 ordering produced a strictly better base "
            "(by scale and/or mirror symmetry) with the exact same edge "
            "lengths, flaps, and pairs, so the backend served that ordering "
            "instead. Nothing about your requested anatomy changed -- only "
            "the packer's STARTING ORDER differed]")


def _verdict(fold_str: str) -> dict | None:
    try:
        fold = json.loads(fold_str)
    except (ValueError, TypeError):
        return None
    return cp_mirror.mirror_verdict(fold, axis_degrees=AXIS_DEGREES)


def is_bijection(fold_str: str) -> bool:
    """The S2.1 predicate gate. True means this fold is ALREADY a proven
    mirror bijection about the shipped 45-degree axis, so a caller must not
    spawn the search -- this is what structurally protects hshape and
    star-4-sym (see the design spec S2.1 and this module's tests)."""
    v = _verdict(fold_str)
    return bool(v and v["is_bijection"])


def _stub_flaps_in(fold_str: str) -> int:
    """K1's input. Duplicates mesh_to_tree.served_stub_flaps's algorithm
    (not a call to it -- see the module docstring on why) against the same
    marker constant, so the two cannot silently drift on WHAT counts as a
    stub."""
    i = fold_str.find(rescue_ladder.STUB_MARKER)
    if i < 0:
        return 0
    j = fold_str.find("]", i)
    if j < 0:
        return 0
    raw = fold_str[i + len(rescue_ladder.STUB_MARKER):j].strip()
    try:
        return max(0, int(raw))
    except ValueError:
        return 1


def rank_key(fold_str: str) -> tuple | None:
    """K1..K4 as a max-is-best tuple, or None if design_scale cannot be
    parsed (the REFUSE condition, design spec S4)."""
    scale = fold_meta.scale_from_fold_str(fold_str)
    if scale is None:
        return None
    stub_flaps = _stub_flaps_in(fold_str)
    v = _verdict(fold_str)
    is_bij = bool(v and v["is_bijection"])
    mv_swapped = (v or {}).get("mv_swapped")
    mv_swapped = mv_swapped if mv_swapped is not None else 0
    return (-stub_flaps, scale, int(is_bij), -mv_swapped)


def rank(fold_strs: list) -> int | None:
    """fold_strs[0] is the control; K5 ties go to it. Returns the winning
    index, or None to REFUSE (fall back byte-identically) when any
    survivor's design_scale could not be parsed -- never coerced to 0.0."""
    keyed = []
    for i, fs in enumerate(fold_strs):
        k = rank_key(fs)
        if k is None:
            return None
        keyed.append(k + (-i,))
    return max(range(len(fold_strs)), key=lambda i: keyed[i])
```

- [ ] **Step 4: Run to verify pass**

Run: `cd mcp_harness && PYTHONPATH=.:tests <venv python> -m pytest
tests/test_order_rank.py -v`
Expected: all 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add order_rank.py tests/test_order_rank.py tests/goldens/order_rank_r1r3.json probe_order_rank_r1r3.py
git commit -m "feat(goal-1/S6): order_rank -- the pure attempt-0 ranking rule (K1-K5)"
```

---

## Task 2: emitter-format pin

**Files:**
- Modify: `mcp_harness/tests/test_fold_meta.py` (add one test)

**Interfaces:**
- Consumes: `runner.compile_tree`, `cases.CASES_BY_NAME`, `fold_meta._SCALE_RE`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_fold_meta.py`:

```python
def test_emitter_pins_six_decimal_fixed_notation_never_scientific():
    """S6's latent hazard (design spec S4.1): fold_meta._SCALE_RE silently
    mis-parses scientific notation (scale=1e-05 -> reads 1.0), safe only
    because TreemakerWrapper.cpp pins `std::fixed << setprecision(6)`. Once
    design_scale is a RANKING SELECTOR (order_rank.py), a future emitter
    format change becomes a wrong SERVE, not a wrong report -- pin the real
    emitter's output shape, not just the regex's behaviour on a synthetic
    string."""
    import re
    import cases
    import runner

    status, payload = runner.compile_tree(*cases.CASES_BY_NAME["star-4"])
    assert status == "ok"
    fold = json.loads(payload)
    m = re.search(r"scale=(\S+)", fold["frame_title"])
    assert m, "no scale= token in a real compiled frame_title"
    token = m.group(1)
    assert re.fullmatch(r"[0-9]+\.[0-9]{6}", token), (
        f"emitter format changed: {token!r} is not fixed 6-decimal notation "
        "-- fold_meta._SCALE_RE and order_rank.rank_key both silently "
        "mis-parse scientific notation")
```

(Uses `json` and `os`/`sys` already imported at the top of
`test_fold_meta.py`; add `import json` at module scope if not already
present -- check before editing.)

- [ ] **Step 2: Run to verify it currently passes** (this pins CURRENT,
      correct behaviour — it is not expected to start red)

Run: `cd mcp_harness && PYTHONPATH=.:tests <venv python> -m pytest
tests/test_fold_meta.py -v`
Expected: PASS (this is a pin, not a TDD red step — the emitter format is
already correct; the test's job is to catch a FUTURE regression).

- [ ] **Step 3: Commit**

```bash
git add tests/test_fold_meta.py
git commit -m "test(goal-1/S6): pin the emitter's fixed 6-decimal scale= format"
```

---

## Task 3: batched worker + orchestration in `server.py`

**Files:**
- Modify: `mcp_harness/server.py`
  - add `_worker_rank_variants` near `_worker_full_base` (~line 158)
  - add `import order_rank` near the other module-level imports (~line 47)
  - modify `_compile_with_perturb` (~line 1484-1526): new optional
    `rank_variants` parameter, ranking logic inside the attempt-0
    short-circuit
  - modify `draft_and_compile_full_base` (~line 1701-1756): build and pass
    the `rank_variants` closure
- Test: `mcp_harness/tests/test_order_rank_serve.py`

**Interfaces:**
- Consumes: `order_rank.is_bijection`, `order_rank.rank`,
  `order_rank.rank_note`, `rescue_ladder.order_variants`,
  `_run_isolated`, `_worker_failure_payload`, `_append_frame_note`,
  `_record_serve`, `capture.record`
- Produces: `_compile_with_perturb(nodes, attempt, pairs=None,
  meta_sink=None, rank_variants=None)` — `rank_variants`, when given, is a
  callable `(nodes, pairs, control_fold, control_scale, control_locs) ->
  tuple | None`, returning `None` to mean "keep the control's own result
  unchanged" or `(served_nodes, fold_str, scale, locs, variant_name)` to mean
  "serve this instead, and mark it with `variant_name`".

- [ ] **Step 1: Write the failing tests**

```python
"""tests/test_order_rank_serve.py -- wiring tests for S6 inside
draft_and_compile_full_base. Uses cases.py subjects (dependency-free) plus
the mesh fixtures for the bird/humanoid reproduction and mesh-path cost
measurements."""
import json
import time

import cases
import order_rank
import rescue_ladder
import server


def test_bijective_control_is_never_searched():
    """S2.1's predicate gate proven load-bearing, direction 1: hshape's
    control is already a bijection, so draft_and_compile_full_base must
    serve it BYTE-IDENTICALLY to a direct compile -- no marker, and the
    batched worker must never be invoked."""
    nodes, pairs = cases.CASES_BY_NAME["hshape"]
    calls = []
    orig = server._run_isolated
    def spy(worker_fn, *a):
        if worker_fn is server._worker_rank_variants:
            calls.append(1)
        return orig(worker_fn, *a)
    server._run_isolated = spy
    try:
        out = server.draft_and_compile_full_base(nodes, symmetric_pairs=pairs)
    finally:
        server._run_isolated = orig
    assert not out.startswith("ERROR:")
    assert order_rank.RANK_MARKER not in out
    assert calls == [], "the batched search ran on an already-bijective control"


def test_non_bijective_control_is_searched():
    """S2.1's predicate gate proven load-bearing, direction 2: a control
    that is NOT a bijection must trigger the batched search."""
    nodes, pairs = cases.CASES_BY_NAME["dog-repaired"]
    calls = []
    orig = server._run_isolated
    def spy(worker_fn, *a):
        if worker_fn is server._worker_rank_variants:
            calls.append(1)
        return orig(worker_fn, *a)
    server._run_isolated = spy
    try:
        out = server.draft_and_compile_full_base(nodes, symmetric_pairs=pairs)
    finally:
        server._run_isolated = orig
    assert not out.startswith("ERROR:")
    assert calls == [1], "the batched search did not run on a non-bijective control"


def test_reranked_serve_stays_attempt0_pack_true_stage_none():
    """DO NOT list / acceptance criterion 9: a re-ranked serve must keep
    rescue_stage == 'none' and attempt0_pack == True -- the contract
    tests/test_mesh_to_tree.py pins."""
    nodes, pairs = cases.CASES_BY_NAME["dog-repaired"]
    out = server.draft_and_compile_full_base(nodes, symmetric_pairs=pairs)
    rec = json.loads(server.read_base())
    assert rec["stage"] == "none"
    import mesh_to_tree
    assert mesh_to_tree.served_stage(out) == rescue_ladder.STAGE_EXACT


def test_dog_repaired_reranks_and_is_marked():
    """dog-repaired is the project's own measured reorder-moves-the-serve
    case (memory; PR #92's required-fail). If S6 improves it, the served
    fold must carry the new marker (never a rescue marker)."""
    nodes, pairs = cases.CASES_BY_NAME["dog-repaired"]
    out = server.draft_and_compile_full_base(nodes, symmetric_pairs=pairs)
    assert not out.startswith("ERROR:")
    for bad in (rescue_ladder.ORDER_MARKER, rescue_ladder.PLACEMENT_MARKER,
                rescue_ladder.NORMALIZE_MARKER, rescue_ladder.STUB_MARKER):
        assert bad not in out


def test_batched_path_matches_per_variant_scales_and_is_fast():
    """Acceptance 4: batching proven -- one spawn's scales match compiling
    each variant in its own isolated spawn, and the batched call is fast."""
    nodes, pairs = cases.CASES_BY_NAME["dog-repaired"]
    variants = rescue_ladder.order_variants(nodes, pairs)
    payload = [(name, json.dumps(cand)) for name, cand in variants]

    t0 = time.monotonic()
    batched_raw = server._run_isolated(server._worker_rank_variants, payload,
                                       pairs, 1.0, 1.0)
    batched_elapsed = time.monotonic() - t0
    batched = json.loads(batched_raw)
    batched_scales = {r["name"]: r.get("scale") for r in batched if r.get("ok")}

    per_variant_scales = {}
    for name, cand in variants:
        out = server._run_isolated(server._worker_full_base,
                                   json.dumps(cand), pairs, 1.0, 1.0, 0)
        if not out.startswith("ERROR:"):
            per_variant_scales[name] = json.loads(out)["scale"]

    assert batched_scales == per_variant_scales
    assert batched_elapsed < 5.0, (
        f"batched spawn took {batched_elapsed:.2f}s -- expected well under "
        "the per-variant multi-spawn cost")


def test_severing_the_rank_call_turns_off_reranking():
    """Deletion proof (acceptance 6): with rank_variants forced to None,
    dog-repaired must serve byte-identically to its plain attempt-0 compile
    (the pre-S6 behaviour), proving the wiring -- not just a count -- is
    what the earlier tests depend on."""
    nodes, pairs = cases.CASES_BY_NAME["dog-repaired"]
    import functools
    orig = server._compile_with_perturb
    def severed(*a, **kw):
        kw["rank_variants"] = None
        return orig(*a, **kw)
    server._compile_with_perturb = severed
    try:
        out = server.draft_and_compile_full_base(nodes, symmetric_pairs=pairs)
    finally:
        server._compile_with_perturb = orig
    assert order_rank.RANK_MARKER not in out
```

- [ ] **Step 2: Run to verify failure**

Run: `cd mcp_harness && PYTHONPATH=.:tests <venv python> -m pytest
tests/test_order_rank_serve.py -v`
Expected: FAIL (`server._worker_rank_variants` does not exist;
`_compile_with_perturb` has no `rank_variants` parameter).

- [ ] **Step 3: Add `_worker_rank_variants` to `server.py`**

Insert after `_worker_full_base` (after line 205):

```python
def _worker_rank_variants(queue, variant_payloads, pairs, paper_width,
                          paper_height):
    """Compile each depth-1 order variant in ONE spawned child (S6, design
    spec S2.2). variant_payloads is [(name, tree_nodes_json), ...], already
    generated in the parent by rescue_ladder.order_variants (pure Python, no
    engine needed) -- this worker's only job is the compile.

    Depth 1 only: a variant whose compile fails is reported failed and
    DISCARDED by the caller, never rescued through its own ladder (design
    spec S3). Mirrors _worker_compile_and_regions's "whole ladder in one
    child" precedent, but each candidate gets its OWN fresh engine instance
    (never reused): engine reuse SIGSEGVs (measured pre-existing, S4a'
    review finding 3 / PROGRESS.md).

    Batched, not per-variant, because 97% of a per-variant spawn's cost is
    re-importing server (design spec S2.2) -- the packer itself is ~1ms.
    """
    out = []
    try:
        import headless_treemaker as ht_child
    except Exception as exc:                       # pragma: no cover
        queue.put(("err", repr(exc)[:200]))
        return
    for name, nodes_json in variant_payloads:
        stage = "init"
        scale = None
        engine = None
        try:
            engine = ht_child.HeadlessTreemaker()
            stage = "init_paper"
            engine.init_paper(paper_width, paper_height)
            stage = "build_tree"
            engine.build_tree_from_json(nodes_json)
            stage = "symmetry"
            for a, b in pairs:
                engine.apply_symmetry(int(a), int(b))
            stage = "scale_optimization"
            scale = engine.run_scale_optimization()
            stage = "molecule"
            fold = engine.build_and_export()
            locs = [list(row) for row in engine.leaf_node_locations()]
            out.append({"name": name, "ok": True, "fold": fold,
                       "scale": scale, "locs": locs})
        except Exception as exc:
            out.append({"name": name, "ok": False,
                       "error": _worker_failure_payload(exc, stage, scale,
                                                        engine)})
    queue.put(("ok", json.dumps(out)))
```

- [ ] **Step 4: Modify `_compile_with_perturb`'s signature and attempt-0
      branch**

In the function signature (~line 1484):

```python
def _compile_with_perturb(nodes: list[dict], attempt, pairs=None,
                          meta_sink=None, rank_variants=None) -> str:
```

Add one paragraph to the docstring, right after the `meta_sink` paragraph:

```
    `rank_variants` (S6, optional) is a callable `(nodes, pairs,
    control_fold, control_scale, control_locs) -> tuple | None`, invoked
    ONLY when attempt-0 packs AND the control is not already a proven mirror
    bijection (order_rank.is_bijection -- the load-bearing predicate gate,
    design spec S2.1). Returning None means "nothing beat the control";
    returning (served_nodes, fold_str, scale, locs, variant_name) means
    variant_name's compile should serve instead. compile_base does not
    supply this -- see the plan's "Scope decision".
```

Replace the attempt-0 branch (currently lines ~1514-1526):

```python
    result = attempt(nodes, 0)
    if not result.startswith("ERROR:"):
```

with:

```python
    result = attempt(nodes, 0)
    if not result.startswith("ERROR:"):
        # exact tree packed. S6: rank it against its own depth-1 order
        # siblings UNLESS it is already a proven mirror bijection -- the
        # predicate gate structurally protects an already-symmetric serve
        # from ever being swapped for a fractional scale gain (design spec
        # S2.1). Byte-identical to pre-S6 behaviour whenever rank_variants
        # is None (compile_base), the control is bijective, nothing beats
        # it, or ranking must REFUSE (an unparseable design_scale).
        served_nodes = nodes
        served_result = result
        served_scale = (meta_sink or {}).get("scale")
        served_locs = (meta_sink or {}).get("locs")
        variant_name = None
        if rank_variants is not None and not order_rank.is_bijection(result):
            won = rank_variants(nodes, pairs or [], result,
                                served_scale, served_locs)
            if won is not None:
                (served_nodes, served_result, served_scale, served_locs,
                 variant_name) = won
        if variant_name is not None:
            served_result = _append_frame_note(
                served_result, order_rank.rank_note(variant_name))
        # The row-level audit key enriches capture (2.4 retrain data) without
        # ever gating attempt-0: a dirty exact tree surfaces HITL through the
        # classified lint verdict, never a server-side retry.
        audit0 = audit_fn(served_result)
        capture.record(nodes, pairs or [], True, served_result, audit=audit0,
                       rescue_stage=rescue_ladder.STAGE_EXACT)
        _record_serve(nodes, served_nodes, None,
                      locs=served_locs, scale=served_scale)
        return served_result
```

(Delete the old body down through the old `return result` — the new block
fully replaces it. The `first_error = result` line that follows stays
untouched; it is only reached on the `ERROR:` branch, unaffected by this
change.)

- [ ] **Step 5: Wire `draft_and_compile_full_base`'s `rank_variants`
      closure**

Replace the function body (~line 1729-1756):

```python
    pairs = symmetric_pairs or []
    meta_sink: dict = {}

    def attempt(nodes: list[dict], stubs: int = 0) -> str:
        ...  # unchanged

    def rank_variants(req_nodes, req_pairs, control_fold, control_scale,
                      control_locs):
        """S6: compile every depth-1 order variant of req_nodes in ONE
        batched spawn and rank control + variants via order_rank.rank.
        Returns None (serve control unchanged) when there are no variants,
        the batch spawn errors, no variant packs, ranking REFUSES, or
        control already wins (index 0 -- K5's tie-break, and also the
        outcome when nothing beats it)."""
        variants = rescue_ladder.order_variants(req_nodes, req_pairs)
        if not variants:
            return None
        payload = [(name, json.dumps(cand)) for name, cand in variants]
        raw = _run_isolated(_worker_rank_variants, payload, req_pairs,
                            paper_width, paper_height)
        if raw.startswith("ERROR:"):
            return None
        try:
            results = json.loads(raw)
        except (ValueError, TypeError):
            return None
        by_name = dict(variants)
        pool = [("control", control_fold, control_scale, control_locs,
                req_nodes)]
        for r in results:
            if not r.get("ok"):
                continue          # depth-1 only: discard, never rescue
            cand_nodes = by_name.get(r["name"])
            if cand_nodes is None:
                continue
            pool.append((r["name"], r["fold"], r.get("scale"), r.get("locs"),
                        cand_nodes))
        win = order_rank.rank([p[1] for p in pool])
        if win is None or win == 0:
            return None
        _, fold_str, scale, locs, served_nodes = pool[win]
        return served_nodes, fold_str, scale, locs, pool[win][0]

    return _compile_with_perturb(tree_nodes, attempt, pairs,
                                 meta_sink=meta_sink,
                                 rank_variants=rank_variants)
```

Also extend the tool docstring (right after the `Returns:` paragraph) with
one short paragraph:

```
        S6: when your exact node order packs but is not already mirror-
        symmetric about the paper's 45-degree diagonal, the backend also
        tries up to 4 alternate orderings of the SAME nodes (same lengths,
        same flaps, same pairs) and serves whichever compiles to the
        highest design scale, preferring a mirror-symmetric result on a
        tie. If a different ordering wins, frame_title carries a note
        naming it; rescue_stage stays "none" either way, because every
        candidate packed on its own first attempt -- nothing was rescued.
```

- [ ] **Step 6: Run to verify pass**

Run: `cd mcp_harness && PYTHONPATH=.:tests <venv python> -m pytest
tests/test_order_rank_serve.py -v`
Expected: all 6 PASS.

- [ ] **Step 7: Commit**

```bash
git add server.py tests/test_order_rank_serve.py
git commit -m "feat(goal-1/S6): rank the attempt-0 pack among its order-variant siblings"
```

---

## Task 4: full-suite baseline delta, byte-pin re-bless with attribution,
      mesh-path cost, bird reproduction, report

Not a code task — verification and reporting per the slice brief's
ACCEPTANCE and REPORT BACK sections. Steps:

- [ ] **Step 1:** Run `PYTHONPATH=.:tests <venv python> -m pytest tests/
      --timeout=420` and compare to the pre-change baseline captured before
      Task 1 started. Expect `tests/test_serve_attempt0_pin.py` to be the
      only file with new failures (subjects whose control is not bijective
      and whose ranking now serves a different ordering) — this is the
      EXPECTED, MEASURED trigger the byte-pin was built for
      (`f01a292`'s own commit message: "A forthcoming slice will open the
      attempt-0 short-circuit and rank among reorders, so this needs to
      land first").

- [ ] **Step 2:** For every subject the pin now fails on, determine whether
      the new served fold is a genuine ranking-driven improvement (higher
      `design_scale`, or a gained bijection) by hand, using
      `fold_meta.scale_from_raw` and `cp_mirror.mirror_verdict` on both the
      old golden and the new serve. If genuine, regenerate ONLY that
      subject's golden entry in `tests/goldens/serve_attempt0_pin.json`
      (do not touch entries the pin still passes) and note the before/after
      `design_scale` in the report. If a subject's move is NOT attributable
      to ranking (e.g. an unrelated engine nondeterminism), STOP and
      investigate — do not fold it into the re-bless silently.

- [ ] **Step 3:** `cd mcp_harness && PYTHONPATH=.:tests <venv python>
      benchmark_subjects.py --baseline fixtures/scorecard_baseline.jsonl`.
      Report the delta table verbatim. Per COORDINATION.md #1, do NOT
      re-bless `scorecard_baseline.jsonl` — only report and attribute.
      Expect `bird`/`humanoid`/possibly others' `hull_coverage` and
      `design_scale` to move; attribute every moved row to this slice.

- [ ] **Step 4:** Reproduce the bird headline end-to-end:
      `server.draft_and_compile_full_base` on the bird mesh's extracted
      tree, before vs after this slice, `hull_coverage`
      (`paper_coverage.coverage_of_fold_str`) and `design_scale`
      (`fold_meta.scale_from_fold_str`). Report whether it reproduces
      `0.499952 -> 0.984783` — per the slice brief's confidence caveat, this
      number was measured on the STOCK drain's extracted tree and the
      marking-fork decision (this plan's Task 3, "NOT rescue_stage") is
      exactly what keeps the drain's extraction unchanged, so it should
      reproduce; report the actual figures either way, not the predicted
      ones.

- [ ] **Step 5:** Measure the honest end-to-end mesh-path cost: wall-clock
      `draft_and_compile_full_base` on `fixtures/bird.glb`'s extracted tree
      and `fixtures/humanoid.glb`'s, before (`git stash` or a checkout of
      the pre-Task-1 commit) vs after this slice. Report both, and the
      ratio.

- [ ] **Step 6:** Write the PR body / final report with: R1-R3 regenerated
      figures vs spec's quoted values (already confirmed exact-match this
      session — see the "R1-R3 regeneration" note above), which serves
      changed (before/after `design_scale`/`hull_coverage`), the bird
      end-to-end number, batched-vs-per-variant timing (from Task 3's
      test), the mesh-path cost, what went red under the deletion proof
      (Task 3's `test_severing_the_rank_call_turns_off_reranking` plus the
      byte-pin subjects), the measured suite baseline and final count, and
      the `--baseline` delta with attribution.

- [ ] No commit for this task by itself — its file changes (the golden
      re-bless, if any) are committed as part of Step 2's own commit:

```bash
git add tests/goldens/serve_attempt0_pin.json
git commit -m "test(goal-1/S6): re-bless the serve-attempt0 golden rows S6 moved, attributed"
```

---

## Self-review

**Spec coverage.** Predicate gate (Task 3 step 4) ✅. Batched single spawn
(Task 3 step 3) ✅. Depth 1 only (worker discards failed variants, S3's
`rank_variants` never recurses) ✅. Ranking rule K1-K5 + REFUSE (Task 1) ✅.
R1-R6 (Task 1 tests) ✅. Marking (RANK_MARKER, not a rescue stage, Task 1 +
Task 3 step 4) ✅. Emitter-format pin (Task 2) ✅. Byte-pin
before/after + attribution (Task 4) ✅. Frozen-baseline delta, not
re-blessed (Task 4 step 3) ✅. Bird reproduction (Task 4 step 4) ✅.
Mesh-path honest cost (Task 4 step 5) ✅. Deletion proof (Task 3's
`test_severing_the_rank_call_turns_off_reranking`) ✅.

**Placeholder scan.** No TBD/TODO; every step has real code or a real
command. Task 4 is verification, not code, and is described as such rather
than padded with fake steps.

**Type consistency.** `rank_variants` callable shape
`(nodes, pairs, control_fold, control_scale, control_locs) -> tuple | None`
is identical between `_compile_with_perturb`'s docstring (Task 3 step 4) and
`draft_and_compile_full_base`'s closure (Task 3 step 5). `order_rank.rank`'s
`list[str] -> int | None` is identical between Task 1's implementation and
every call site in Task 3.
