# Squash Fold (Slice 4) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A `squash:X,Y:D` display op that opens a flap and presses it flat symmetrically about its spine, plus a prerequisite apex-snap fix to `shaping_deep`, plus a verified `sink` alias of `reverse_deep(θ=180)`.

**Architecture:** Squash is a **tip-local flat-CP op** in `shaping.py`, a sibling of `reverse_fold` — it reuses `_find_tip`/`_march_arm`/`_split_edges`/`_rot` and the ±γ wedge, computing new creases in flat CP and rebuilding `edges_foldAngle`. Its exact crease construction is **derived and pinned by a probe** (Task 2) with a hard **de-risk gate** (squash must be visibly distinct from `reverse_fold(θ=90)` — else STOP). `sink` is only a documented preset of the already-shipped `reverse_deep`, gated on a star-4 verification. No new numpy module; `shaping.py` stays stdlib-only.

**Tech Stack:** Python 3 + stdlib (`shaping.py`) and numpy (probes only), pytest, Playwright MCP for the one sim smoke. Consumed: `shaping.py`, `shaping_deep.py`, `flat_fold.py`, `layer_order.py`, `square_complete.py`. Spec: `docs/superpowers/specs/2026-07-06-squash-slice4-design.md`.

## Global Constraints

- Backend suite: `cd mcp_harness && .venv/bin/python -m pytest tests -q` (~8–10 min). At branch time: **391 passed / 3 skipped** — final count must be 391+new, 0 failures.
- All commands run from `mcp_harness/` with `.venv/bin/python` unless stated.
- **Measure-then-pin:** never write an expected value into a test without first printing it from a committed probe script AND checking it against hand reasoning. Commit probe scripts as evidence.
- **De-risk gate (Task 2):** if the probe shows a symmetric squash on our edge-flaps is NOT distinct from `reverse_fold(θ=90)` (same crease set AND same folded silhouette), STOP — do not ship a redundant op. Re-brainstorm. Everything after Task 2 is contingent on the gate passing.
- `shaping.py` stays **stdlib-only** (`math`, no numpy). Any numpy (`flat_fold`/`layer_order`) belongs in probe scripts, never imported by `shaping.py`. (Contrast: `reverse_deep` lives in `shaping_deep.py` precisely to keep `shaping.py` clean.)
- Provenance: the raw linted `json` frame is never touched; squash is tip-local and writes into `display_json` only. `web/server.py` needs **no** new plumbing (squash takes no `raw`). Input dicts never mutated (copy-then-mutate, as `reverse_fold` does).
- `ShapingError` is the only refusal exception; `apply_display_op(s)` swallows it (one stderr line, fold stream never breaks).
- Smoke base is **star-4** (its hull fills the square, so it folds); the squared dog/quad relax flat (max displacement 0.0) and are VACUOUS — every sim smoke asserts **`displacement > 0`**.
- Key API facts (verified at plan time, `shaping.py`):
  - `_find_tip(fold, xy) -> (tip_v, axial_edge)`: a tip = vertex with a `B` edge + exactly one `M`/`V` crease.
  - `reverse_fold(fold, tip_xy, d, theta, gamma=45.0, sense=1) -> dict`: wedge apex `F` at depth `d` on the axial; arms `_march_arm(fold, F, _rot(tipward, ±γ), {axial})`; region guard (no vertex strictly inside `[hit_l, P, hit_r, F]`); `s = +1 if axial is V else −1`; rebuilds `edges_foldAngle`.
  - `_march_arm(fold, start, dir, skip_edges) -> (crossings, terminal)`: `crossings` = list of `(edge_idx, pt)` where the ray crosses `F` edges; `terminal` = `(edge_idx, pt)` where it hits a `B`; REFUSES (`ShapingError`) if it crosses a real (M/V) crease.
  - `_split_edges(vc, ev, ea, requests) -> {_key(pt): new_vertex_idx}`; `requests = {edge_idx: [pt,...]}`.
  - `_key(p) = (round(p[0],9), round(p[1],9))`; `EPS=1e-9`, `SNAP=1e-7`.
  - `parse_op(op) -> (kind, tip_xy, d, theta)`; `apply_display_op(fold, op, raw=None)`; `apply_display_ops(fold, ops, raw=None)`.
  - `square_complete.complete_square(fold, w, h)`: appends only; raw indices stable.
  - star-4 geometry (Task-2 probe target): tip `v2` at CP `(1.0, 0.5)`; spine = axial edge 0 = `[2,3]` (V) to center `v3=(0.5,0.5)`; two raw half-edges `[0,2]`/`[2,1]` to corners `(1,1)`/`(1,0)`. Its two flap faces `f0=[2,3,1]` (det +1) and `f6=[3,2,0]` (det −1) are stacked, both folding to triangle `{(0.5,1),(0.5,0.5),(1,1)}`.

---

### Task 1: Snap fold-apex split-requests (shaping_deep sliver fix)

**Files:**
- Modify: `mcp_harness/shaping_deep.py` (`_pt_on_edge`, ~line 212)
- Modify: `mcp_harness/probe_atdepth_stack.py` (add a zero-length-edge report)
- Test: `mcp_harness/tests/test_shaping_deep.py`

**Interfaces:**
- Produces: `reverse_deep` output with **0 zero-length edges** at every probe point. No signature change.

The bug (from slice-3 handoff): at some deep points two fold-apex split
requests differ by ~1.1e-9 — just past `_key`'s 9-dp dedup — producing two
near-coincident apex vertices and a zero-length sliver edge. Apex points
all flow through `_pt_on_edge`; rounding its return to 8 dp merges them.
Because `_key` rounds to 9 dp, an 8-dp source is consistent with every
downstream `_key(pt)` lookup (`round(round(x,8),9) == round(x,8)`).

- [ ] **Step 1: Find the offending point (measure).** Extend `probe_atdepth_stack.py`: after each successful `reverse_deep`, count edges whose two endpoints are within `1e-6` in the OUTPUT (`out["vertices_coords"]`/`out["edges_vertices"]`), and print `slivers=N` with the tip/fraction. Run `.venv/bin/python probe_atdepth_stack.py` and record the first `slivers>0` point (expected: a mid-depth dog tip, per handoff).

- [ ] **Step 2: Write the failing regression test.**

```python
class TestApexSnap:
    def test_no_sliver_edges_at_sliver_point(self):
        # tip_xy / d = the point Step-1's probe reported with slivers>0
        import json, math
        raw = json.load(open("tests/goldens/dog.fold"))
        sq = square_complete.complete_square(raw, 1.0, 1.0)
        out = shaping_deep.reverse_deep(sq, raw, TIP_XY, D, 180.0)
        vc = out["vertices_coords"]
        slivers = [(a, b) for a, b in out["edges_vertices"]
                   if math.hypot(vc[a][0]-vc[b][0], vc[a][1]-vc[b][1]) < 1e-6]
        assert slivers == []
```

- [ ] **Step 3: Run to verify failure** — `.venv/bin/python -m pytest tests/test_shaping_deep.py -k ApexSnap -v` → FAIL (one sliver edge).

- [ ] **Step 4: Implement** — in `shaping_deep._pt_on_edge`, round the returned tuple to 8 dp:

```python
def _pt_on_edge(vc, ev, ei, t):
    """Point at parameter t (from ev[ei][0]) along edge ei, using vc.
    Rounded to 8 dp so near-coincident apex requests (float paths that
    differ by ~1e-9, just past _key's 9-dp dedup) collapse to ONE vertex
    instead of a zero-length sliver edge (slice-4 handoff)."""
    a, b = ev[ei]
    pa, pb = vc[a], vc[b]
    return (round((1 - t) * pa[0] + t * pb[0], 8),
            round((1 - t) * pa[1] + t * pb[1], 8))
```

- [ ] **Step 5: Run to verify pass** — `-k ApexSnap` PASS; then the whole file `.venv/bin/python -m pytest tests/test_shaping_deep.py -q` → 0 regressions (the 8-dp snap must not move any pinned slice-3 value; if a count shifts, the pin was at 9-dp noise — re-measure and re-pin that one value, noting it).

- [ ] **Step 6: Commit** — `git add mcp_harness/shaping_deep.py mcp_harness/probe_atdepth_stack.py mcp_harness/tests/test_shaping_deep.py && git commit -m "fix(slice4): snap fold-apex split-requests to 8dp — kill ~1e-9 sliver edge"`

---

### Task 2: Squash construction probe + DE-RISK GATE

**Files:**
- Create: `mcp_harness/probe_squash.py`

**Interfaces:**
- Produces: the **pinned squash construction** for a symmetric edge-flap — the new-crease set (endpoints as edge/parameter or CP coords), per-crease M/V + fold angle, and the reassignment of the spine segment — recorded in the probe's printed output and docstring. Consumed verbatim by Task 3.

This task does the slice's core geometry R&D on star-4's `v2` flap
(fully forced layer order → every layer is hand-checkable) and **decides
whether squash is a real op**. Work the construction on paper first, then
encode candidates and let `flat_fold` closure be the judge.

**Hypothesis to test (the spread-the-stacked-layers squash):** `v2`'s two
flap faces `f0`,`f6` are stacked (both fold to the same triangle,
connected at the spine). A symmetric squash at depth `d`:
1. `F` = point on the spine at depth `d` from `P=v2`.
2. The spine segment `P–F` **reassigns** (V → its opened value; pinned by
   closure) and two new symmetric creases open from `F` at ±γ toward the
   raw edges (the `reverse_fold` wedge arms), so the two stacked layers
   spread to opposite sides of the spine's folded image.
3. Each new crease's M/V + fold angle is pinned so `flat_fold` closure of
   the resulting CP is clean AND Maekawa holds at the new degree-4 apex.

- [ ] **Step 1: Write the probe.** For star-4 `v2`, depth `d=0.25`, γ=45°:
  print the flap faces/folded stack (reuse the Task-plan snippet), then for
  each candidate construction build the resulting CP and report:
  (a) `flat_fold(candidate)` closure `bad_edges` count (must be 0),
  (b) the folded silhouette bounding box / area of the squashed flap vs the
      original flap footprint (must CHANGE — a pocket opened),
  (c) the crease set of `reverse_fold(star4, (1,0.5), 0.25, 90.0)` for the
      **distinctness diff**.

```python
"""Slice-4 probe: derive + de-risk the symmetric squash on star-4 v2.

Target flap: tip v2=(1,0.5), spine=edge0 [2,3] (V) to center v3=(0.5,0.5),
raw half-edges to corners (1,1)/(1,0). Faces f0=[2,3,1], f6=[3,2,0] stack
onto triangle {(0.5,1),(0.5,0.5),(1,1)}.

For each candidate squash construction: (a) flat_fold closure must be
clean, (b) folded silhouette must differ from the un-squashed flap (pocket
opened), (c) crease set must differ from reverse_fold(theta=90). Print all
three. The candidate passing (a)+(b)+(c) is the PINNED construction; if
none does, the de-risk gate FAILS -> STOP and re-brainstorm.

Run: cd mcp_harness && .venv/bin/python probe_squash.py
"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flat_fold import flat_fold
import shaping
# ... build candidates, print closure/silhouette/diff ...
```

- [ ] **Step 2: Run + judge the gate.** `.venv/bin/python probe_squash.py`.
  - **Gate PASS** iff some candidate has clean closure, a changed folded
    silhouette, AND a crease set differing from `reverse_fold(θ=90)`.
    Record that candidate's exact creases/assignments/angles in the probe
    docstring — this is the pinned construction for Task 3.
  - **Gate FAIL** (no candidate distinct or none closes): STOP. Write the
    finding into the SDD ledger and return to brainstorming — do NOT
    proceed to Task 3.

- [ ] **Step 3: Commit** — `git add mcp_harness/probe_squash.py && git commit -m "probe(slice4): squash construction derived + de-risk gate on star-4 v2"`

---

### Task 3: Implement `squash()` in shaping.py

**Files:**
- Modify: `mcp_harness/shaping.py` (add `squash()` after `reverse_fold`)
- Test: `mcp_harness/tests/test_shaping.py`

**Interfaces:**
- Produces: `squash(fold, tip_xy, d, gamma=45.0) -> dict` — new fold dict; `ShapingError` on refusal; never mutates input.

Implement **per Task 2's pinned construction**. The scaffold reuses
`reverse_fold`'s machinery verbatim; only the crease-assignment step
differs (opening the flap symmetrically rather than reflecting the tip):

1. `tip, axial = _find_tip(fold, tip_xy)`; guards `d>0`, `d < ax_len − EPS`.
2. `F` on the axial at depth `d`; `arms = [_march_arm(fold, F, _rot(tipward, sg*gamma), {axial}) for sg in (+1,-1)]`; region guard `[hit_l, P, hit_r, F]` (copy from `reverse_fold`).
3. `_split_edges` for `F` + arm crossings/terminals (copy from `reverse_fold`).
4. Assign the spine segment(s) and the two arm creases per the **pinned rule from Task 2** (assignments + fold angles); rebuild `edges_foldAngle`.
5. Copy-then-mutate; return new dict.

- [ ] **Step 1: Write failing hand-derived test** — the star-4 `v2` squash from Task 2, asserting the exact new-edge count, the new creases' `{v,v}` vertex pairs, their assignments, and their fold angles (values from the Task-2 probe docstring).

```python
class TestSquash:
    def test_star4_v2_squash_hand_derived(self):
        fold = json.load(open("tests/goldens/star-4.fold"))
        out = shaping.squash(fold, (1.0, 0.5), 0.25)
        assert out is not fold                       # new object
        assert len(out["edges_vertices"]) == PINNED_EDGE_COUNT
        # the two opened arm creases + reassigned spine (from probe):
        got = {frozenset(e): (a, ang) for e, a, ang in zip(
            out["edges_vertices"], out["edges_assignment"],
            out["edges_foldAngle"])}
        for pair, assign, ang in PINNED_NEW_CREASES:
            assert got[frozenset(pair)] == (assign, ang)
```

- [ ] **Step 2: Run to verify failure** — `-k TestSquash` → `AttributeError: module 'shaping' has no attribute 'squash'`.

- [ ] **Step 3: Implement `squash()`** per the scaffold above and Task 2's pinned rule (≈40 lines; every helper already exists and is tested by `reverse_fold`).

- [ ] **Step 4: Run to verify pass** — `-k TestSquash` PASS. Acceptance gate: if the hand-derived crease set fails, diff the produced vs pinned creases — assignment sign of the spine reassignment is the usual suspect.

- [ ] **Step 5: Commit** — `git add mcp_harness/shaping.py mcp_harness/tests/test_shaping.py && git commit -m "feat(slice4): squash() — symmetric flap-open, hand-derived on star-4"`

---

### Task 4: Refusal + contract tests for `squash()`

**Files:**
- Modify: `mcp_harness/tests/test_shaping.py`

- [ ] **Step 1: Write failing tests** for every §2 refusal + contract:

```python
class TestSquashContract:
    def test_no_tip_near_point_refused(self):
        with pytest.raises(shaping.ShapingError):
            shaping.squash(json.load(open("tests/goldens/star-4.fold")),
                           (0.5, 0.5), 0.25)          # center, no tip sig
    def test_d_past_axial_refused(self):
        with pytest.raises(shaping.ShapingError):
            shaping.squash(json.load(open("tests/goldens/star-4.fold")),
                           (1.0, 0.5), 10.0)
    def test_arm_crosses_real_crease_refused(self):
        # a flap whose ±gamma arm hits an M/V crease -> _march_arm raises
        ...  # pick the star-4 tip Task-2 identifies as arm-blocked, or skip if none
    def test_input_not_mutated(self):
        fold = json.load(open("tests/goldens/star-4.fold"))
        before = json.dumps(fold, sort_keys=True)
        shaping.squash(fold, (1.0, 0.5), 0.25)
        assert json.dumps(fold, sort_keys=True) == before
    def test_deterministic(self):
        fold = json.load(open("tests/goldens/star-4.fold"))
        a = shaping.squash(fold, (1.0, 0.5), 0.25)
        b = shaping.squash(fold, (1.0, 0.5), 0.25)
        assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
```

- [ ] **Step 2: Run to verify failure**, then confirm the guards in `squash()` cover them (they reuse `reverse_fold`'s guards) — add any missing guard.
- [ ] **Step 3: Run to verify pass** — `-k TestSquashContract` PASS.
- [ ] **Step 4: Commit** — `git commit -am "test(slice4): squash refusal + contract tier"`

---

### Task 5: Dispatch wiring (`parse_op` / `apply_display_op(s)`)

**Files:**
- Modify: `mcp_harness/shaping.py` (`parse_op`, `apply_display_op`, `apply_display_ops`)
- Test: `mcp_harness/tests/test_shaping.py`

**Interfaces:**
- Produces: op string `squash:X,Y:D` (optional `:γ`), dispatched by `apply_display_op(s)`; tip-local (no `raw`), composes after `reverse_deep` and alongside `reverse`/`outside`.

- [ ] **Step 1: Write failing dispatch tests.**

```python
class TestSquashDispatch:
    def test_squash_op_applies(self):
        fold = json.load(open("tests/goldens/star-4.fold"))
        out = shaping.apply_display_ops(fold, ["squash:1,0.5:0.25"])
        assert out is not fold and \
            len(out["edges_vertices"]) > len(fold["edges_vertices"])
    def test_bad_squash_op_is_noop(self):
        fold = json.load(open("tests/goldens/star-4.fold"))
        assert shaping.apply_display_ops(fold, ["squash:0.5,0.5:0.25"]) is fold
```

- [ ] **Step 2: Run to verify failure** — `parse_op` doesn't know `squash` → first test fails.
- [ ] **Step 3: Implement** — `parse_op` accepts `"squash"` (3-part `kind:X,Y:D`, optional 4th `γ`; `theta` field unused → default). `apply_display_op`: on `kind == "squash"`, `return squash(fold, tip_xy, d, gamma)`. `squash` is tip-local, so `apply_display_ops`' existing deep-before-tip-local ordering treats it as tip-local (no change to the ordering rule). Confirm `grep -n "squash" web/server.py` needs nothing (no `raw`).
- [ ] **Step 4: Run to verify pass** — `-k TestSquashDispatch` PASS; run `tests/test_shaping.py -q` → 0 regressions.
- [ ] **Step 5: Commit** — `git commit -am "feat(slice4): squash display dispatch (parse_op + apply_display_op)"`

---

### Task 6: Sink verification + alias (verify-then-alias)

**Files:**
- Create: `mcp_harness/probe_sink.py`
- Modify: `mcp_harness/shaping.py` (add `sink` alias to `parse_op`/dispatch) — ONLY if the probe passes
- Test: `mcp_harness/tests/test_shaping_deep.py`

- [ ] **Step 1: Verification probe.** `probe_sink.py`: on star-4 (fully forced order), build the open-sink of a flap BY HAND (all creases in the tip region above the sink line flip M/V) and compare the crease set to `shaping_deep.reverse_deep(sq_star4, star4, tip_xy, d, 180.0)`. Print MATCH / MISMATCH with the diff. Run it.
- [ ] **Step 2: Branch on the result.**
  - **MATCH** → sink is a preset of `reverse_deep(θ=180)`. Add `sink:X,Y:D` to `parse_op`/`apply_display_op` as a thin alias: `kind == "sink"` dispatches `reverse_deep(fold, raw, tip_xy, d, 180.0)` (needs `raw`, like `reverse_deep`; enforce the same one-deep/ordering rule). Add a round-trip dispatch test.
  - **MISMATCH** → sink is genuinely distinct. Do NOT add the alias. Record the diff in the SDD ledger + PR body as a "sink needs its own slice" finding. Skip the rest of this task.
- [ ] **Step 3: Test (MATCH path)** — `test_sink_alias_equals_reverse_deep_180` asserts `apply_display_ops(sq, ["sink:X,Y:D"], raw=raw)` equals `apply_display_ops(sq, ["reverse_deep:X,Y:D:180"], raw=raw)`.
- [ ] **Step 4: Commit** — `git add mcp_harness/probe_sink.py [mcp_harness/shaping.py mcp_harness/tests/test_shaping_deep.py] && git commit -m "feat(slice4): sink = verified reverse_deep(180) alias (or documented deferral)"`

---

### Task 7: End-to-end sim smoke (star-4, Playwright)

**Files:**
- Create: `mcp_harness/probe_squash_sim_smoke.py`

Executed WITH the Playwright MCP browser tools (the vendored sim's GPU
solver runs under Playwright — proven slices 0/1/3). Reuse the exact
capture flow of `probe_deep_sim_smoke.py`.

- [ ] **Step 1: Build the shaped fold** — load `tests/goldens/star-4.fold`, `complete_square(fold, 1.0, 1.0)` (a no-op for star-4: hull fills the square), `shaping.apply_display_ops(sq, ["squash:1,0.5:0.25"])`; write to `web/frontend/dist/squash_smoke.fold`.
- [ ] **Step 2: Drive the sim** — `python3 -m http.server 8123 -d web/frontend/dist` (background); Playwright navigate `http://localhost:8123/simulator/index.html?embed=1`; `browser_evaluate`: fetch the fold, `postMessage({type:"loadFold", fold}, location.origin)`, `postMessage({type:"setFold", percent:100}, location.origin)`; wait ~20s (visible tab); `postMessage({type:"getFoldedGeometry"}, ...)`; save `vertices_coords`/`faces_vertices`/`flat_coords` to `$CLAUDE_JOB_DIR/tmp/`.
- [ ] **Step 3: Assert** — probe part 2: per-triangle-edge strain `|len3d − lenflat|/lenflat`; **and max per-vertex `displacement` between flat and folded**. Gates: **0 NaN**, **p90 strain < 0.15** (`IDE_STRAIN_MAX`), and **`max_displacement > 1e-6`** (anti-vacuous — a squash on star-4 must actually move paper; a 0.0 here means the sim relaxed flat and the smoke is vacuous → investigate, do not loosen).
- [ ] **Step 4: Record + commit** — paste NaN/strain/displacement numbers into the SDD ledger + PR body; `git add mcp_harness/probe_squash_sim_smoke.py && git commit -m "probe(slice4): star-4 squash sim smoke — 0 NaN, displacement>0"`. Remove `squash_smoke.fold` from `dist/`.

---

### Task 8: Final verification & branch finish

- [ ] Full backend suite: `cd mcp_harness && .venv/bin/python -m pytest tests -q` — 0 failures; report exact counts (expect 391 + new).
- [ ] `git diff origin/main --stat` — only: `mcp_harness/shaping.py`, `mcp_harness/shaping_deep.py`, `mcp_harness/tests/test_shaping.py`, `mcp_harness/tests/test_shaping_deep.py`, the probe scripts (`probe_squash.py`, `probe_sink.py`, `probe_squash_sim_smoke.py`, `probe_atdepth_stack.py`), spec + plan docs. `web/server.py` should be UNCHANGED (squash needs no `raw`).
- [ ] Provenance spot-check: `grep -rn "squash" web/server.py` → nothing new; `json` frame construction untouched; squash only reachable via `display_json` ops.
- [ ] Use superpowers:requesting-code-review for a whole-branch review; fix findings.
- [ ] Use superpowers:finishing-a-development-branch — **the user merges the PR themselves** (ask before anything outward-facing).

## Self-Review (done at plan time)

- **Spec coverage:** §Decisions split/alias → Tasks 2/6; prerequisite apex-snap → Task 1; §1 semantics + de-risk gate → Task 2; squash impl → Task 3; §2 refusals → Task 4; §3 wiring → Task 5; §4 testing tiers 1–7 → Tasks 2/3/4/5/6/7; §5 non-goals — no task touches them.
- **Contingency:** Tasks 3–5, 7 are contingent on Task 2's de-risk gate PASSING; Task 6's alias is contingent on its own verification. Both failure paths (STOP+re-brainstorm; document-and-defer) are written into the tasks, not left implicit.
- **Measure-then-pin:** `PINNED_EDGE_COUNT`/`PINNED_NEW_CREASES` (Task 3) and the Task-1 regression point come from committed probes (Tasks 2, 1), not guessed.
- **Type consistency:** `squash(fold, tip_xy, d, gamma=45.0)` used identically in Tasks 3–5; `sink` dispatches `reverse_deep(fold, raw, tip_xy, d, 180.0)` (the shipped slice-3 signature) in Task 6.
- **Known latitude:** Task 3's exact crease-assignment code is deferred to Task 2's pinned construction (same pattern slice-3's plan used for its per-layer assignment table) — justified because squash's CP is genuine R&D and is gated.
