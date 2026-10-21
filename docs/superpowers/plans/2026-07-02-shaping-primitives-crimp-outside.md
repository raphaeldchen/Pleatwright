# Shaping Primitives (Crimp + Outside Reverse) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Grow the shaping vocabulary from one primitive to three agent-callable kinds — `reverse`, `outside`, `crimp` — on the existing `apply_shaping_ops` tool, with the display replay machinery unchanged beyond one new op-string kind.

**Architecture:** Approach A from the spec (`docs/superpowers/specs/2026-07-02-shaping-primitives-crimp-outside-design.md`): the ONLY new geometry is a `sense` parameter in `shaping.reverse_fold` that sign-flips the wedge-arm and tip-axial fold angles (outside reverse fold). A crimp is a tool-level atomic composition — inside reverse at `d1`, outside reverse at `d2 = fraction2 * d1` — emitted as two ordinary op strings, so `apply_display_ops`, `web/fold.py`, and `web/server.py` need no changes.

**Tech Stack:** Python 3 stdlib geometry (`mcp_harness/shaping.py`), FastMCP tool (`mcp_harness/server.py`), pytest via the project venv.

## Global Constraints

(Verbatim from the spec; every task's requirements include these.)

- Op grammar is exactly `reverse:X,Y:D:THETA` and `outside:X,Y:D:THETA`; `d` is baked into the op string by the tool (`f"...{d}..."` on the float — str/repr round-trip).
- With `kind` omitted (or `"reverse"`), tool behavior is **byte-identical to today** — default parameter values must preserve every existing call.
- Body-side axial angle stays `s * 180.0` for BOTH senses (that crease belongs to the compiled base).
- Theta ranges: `reverse` (0, 180]; `outside` (0, 180); `crimp` (0, 180) **and** `theta != 90` (at 90 the inside half's tip axial goes `F`, the tip loses its signature, and `_find_tip` silently retargets a different vertex — probe-proven).
- Crimp expansion: `d1 = fraction * shaping.axial_length(current, (x, y))`; `d2 = fraction2 * d1`; ops appended in order `reverse@d1` then `outside@d2`; **atomic** — on any `ShapingError` in either half, NEITHER op is recorded and `current` is unchanged.
- Wrapper JSON keys unchanged: `status`, `fold` (raw), `ide_shape_ops`, `paper`, `verdicts`. Verdicts gain a `kind` field on every entry (additive).
- A refused or malformed target never aborts the batch (B2 rule).
- `web/fold.py`, `web/server.py`, and `shaping.apply_display_ops` are NOT modified.
- Provenance: the raw `fold` in the wrapper is never squared or shaped; ops never enter the FOLD dict.
- The existing prompt pin `"ONLY AFTER THE USER APPROVES"` must still pass unmodified.
- Backend tests: `cd <repo>/mcp_harness && .venv/bin/python -m pytest <paths> -q`. Web tests (repo root): `mcp_harness/.venv/bin/python -m pytest web/tests -q`.
- Engine-test parameters below are probe-verified on star-4 (2026-07-02): inside@fraction 0.5/theta 75 then a second fold on the SAME leaf at fraction2 0.3–0.99 all APPLY on nodes 2/3/4; `axial_length` after fold 1 equals `d1` exactly. Do not substitute other parameters.

---

### Task 1: `sense` in `reverse_fold` + `outside:` op grammar

**Files:**
- Modify: `mcp_harness/shaping.py` (module docstring, `parse_op`, `reverse_fold`, `apply_display_op`)
- Test: `mcp_harness/tests/test_shaping.py`

**Interfaces:**
- Consumes: existing `shaping.py` internals (unchanged: `_find_tip`, `_march_arm`, `_split_edges`).
- Produces (Task 2 relies on these exact signatures):
  - `reverse_fold(fold, tip_xy, d, theta, gamma=45.0, sense=1) -> dict` — `sense` is `1` (inside, today's behavior bit-for-bit) or `-1` (outside); raises `ShapingError` for other values, and for `sense=-1` with `theta` at 180.
  - `parse_op(op) -> (kind, (x, y), d, theta)` where `kind` is `"reverse"` or `"outside"` — **4-tuple, a signature change**; the only unpacking caller is `apply_display_op` (updated here). `mcp_harness/tests/test_shaping_tool.py` calls `shaping.parse_op(op)` without unpacking — unaffected.

- [ ] **Step 1: Update the round-trip test and add the failing outside tests**

In `mcp_harness/tests/test_shaping.py`, replace `test_parse_op_roundtrip` with:

```python
def test_parse_op_roundtrip():
    assert shaping.parse_op("reverse:1.0,0.5:0.2:90") == \
        ("reverse", (1.0, 0.5), 0.2, 90.0)
    assert shaping.parse_op("outside:1.0,0.5:0.2:75") == \
        ("outside", (1.0, 0.5), 0.2, 75.0)
```

Extend the `test_parse_op_rejects` parametrize list with one entry:

```python
    "outside:1,0.5:0.2:180",    # outside needs theta < 180
```

Append after `test_reverse_fold_mirrors_sign_for_mountain_axial`:

```python
def test_outside_reverse_flips_wedge_and_tip_signs():
    inside = shaping.reverse_fold(TIP_SQUARE, (1, 0.5), d=0.2, theta=75)
    outside = shaping.reverse_fold(TIP_SQUARE, (1, 0.5), d=0.2, theta=75,
                                   sense=-1)
    # same topology delta as inside
    assert len(outside["vertices_coords"]) == len(inside["vertices_coords"])
    assert len(outside["edges_vertices"]) == len(inside["edges_vertices"])
    # body-side axial identical between senses (belongs to the base)
    assert _edge_lookup(inside, (0.8, 0.5), (0.5, 0.5)) == ("V", 180.0)
    assert _edge_lookup(outside, (0.8, 0.5), (0.5, 0.5)) == ("V", 180.0)
    # wedge arms and tip-side axial are the sign flip of inside
    assert _edge_lookup(inside, (0.8, 0.5), (1, 0.7)) == ("V", 75.0)
    assert _edge_lookup(outside, (0.8, 0.5), (1, 0.7)) == ("M", -75.0)
    assert _edge_lookup(outside, (0.8, 0.5), (1, 0.3)) == ("M", -75.0)
    assert _edge_lookup(inside, (1, 0.5), (0.8, 0.5)) == ("V", 30.0)
    assert _edge_lookup(outside, (1, 0.5), (0.8, 0.5)) == ("M", -30.0)


def test_outside_reverse_theta180_refused():
    with pytest.raises(shaping.ShapingError):
        shaping.reverse_fold(TIP_SQUARE, (1, 0.5), d=0.2, theta=180,
                             sense=-1)
    # inside theta=180 (the classic flat reverse fold) still applies
    shaping.reverse_fold(TIP_SQUARE, (1, 0.5), d=0.2, theta=180)


def test_reverse_fold_rejects_bad_sense():
    with pytest.raises(shaping.ShapingError):
        shaping.reverse_fold(TIP_SQUARE, (1, 0.5), d=0.2, theta=90, sense=0)


def test_apply_display_op_dispatches_outside():
    out = shaping.apply_display_op(TIP_SQUARE, "outside:1,0.5:0.2:75")
    assert len(out["edges_vertices"]) == 11
    assert _edge_lookup(out, (0.8, 0.5), (1, 0.7)) == ("M", -75.0)
    # defensive path unchanged: outside with bad geometry -> input unchanged
    assert shaping.apply_display_op(
        TIP_SQUARE, "outside:1,0.5:0.9:75") is TIP_SQUARE
```

- [ ] **Step 2: Run to verify the new tests fail**

Run: `cd <repo>/mcp_harness && .venv/bin/python -m pytest tests/test_shaping.py -q`
Expected: FAIL — `test_parse_op_roundtrip` (3-tuple vs 4-tuple), `TypeError: unexpected keyword argument 'sense'` on the new tests.

- [ ] **Step 3: Implement in `mcp_harness/shaping.py`**

Replace `parse_op` with:

```python
def parse_op(op: str):
    """'reverse:X,Y:D:THETA' or 'outside:X,Y:D:THETA' ->
    (kind, (x, y), d, theta). Raises ShapingError."""
    parts = op.strip().split(":")
    if len(parts) != 4 or parts[0] not in ("reverse", "outside"):
        raise ShapingError(f"unrecognized shape op: {op!r}")
    kind = parts[0]
    try:
        x, y = (float(t) for t in parts[1].split(","))
        d, theta = float(parts[2]), float(parts[3])
    except ValueError as exc:
        raise ShapingError(f"bad shape-op numbers: {op!r}") from exc
    if d <= 0 or not 0 < theta <= 180:
        raise ShapingError("need d > 0 and 0 < theta <= 180")
    if kind == "outside" and theta >= 180.0 - EPS:
        raise ShapingError("outside reverse fold needs theta < 180")
    return kind, (x, y), d, theta
```

Change `reverse_fold`'s signature and guards (first lines of the function):

```python
def reverse_fold(fold: dict, tip_xy, d: float, theta: float,
                 gamma: float = 45.0, sense: int = 1) -> dict:
    """Tip-local reverse fold (see module docstring for the angle model).
    sense=+1: inside (bend toward the flap's fold direction); sense=-1:
    outside (bend away). Returns a NEW fold dict; raises ShapingError
    when refused."""
    if sense not in (1, -1):
        raise ShapingError("sense must be 1 (inside) or -1 (outside)")
    if d <= 0 or not 0 < theta <= 180:
        raise ShapingError("need d > 0 and 0 < theta <= 180")
    if sense == -1 and theta >= 180.0 - EPS:
        raise ShapingError("outside reverse fold needs theta < 180")
```

and the two angle lines (body-side stays `s * 180.0` — do NOT touch the `overrides[body_seg]` line):

```python
    s = 1.0 if ea0[axial] == "V" else -1.0
    wedge_angle = sense * s * theta
    tip_angle = sense * s * (180.0 - 2.0 * theta)
```

Update `apply_display_op`'s try block:

```python
    try:
        kind, tip_xy, d, theta = parse_op(op)
        return reverse_fold(fold, tip_xy, d, theta,
                            sense=1 if kind == "reverse" else -1)
    except Exception as exc:
        print(f"shaping: op {op!r} refused: {exc}", file=sys.stderr)
        return fold
```

Extend the module docstring's angle-model paragraph with one sentence after the theta=90 sentence:

```
sense=-1 (outside reverse fold) sign-flips the wedge and tip-axial angles
while the body-side axial keeps s*180 (it belongs to the compiled base);
theta=180 outside is refused (breaks Maekawa parity at the new vertex).
```

- [ ] **Step 4: Run the shaping unit tests**

Run: `cd <repo>/mcp_harness && .venv/bin/python -m pytest tests/test_shaping.py tests/test_shaping_fixture.py -q`
Expected: PASS (all — the fixture drift tripwire must stay green; `sense=1` default is bit-for-bit today's behavior).

- [ ] **Step 5: Commit**

```bash
cd <repo>
git add mcp_harness/shaping.py mcp_harness/tests/test_shaping.py
git commit -m "feat(shaping): outside reverse fold — sense flip + outside: op grammar"
```

---

### Task 2: `kind` targets + atomic crimp composition in `apply_shaping_ops`

**Files:**
- Modify: `mcp_harness/server.py` (the `apply_shaping_ops` tool: docstring + per-target loop)
- Test: `mcp_harness/tests/test_shaping_tool.py`

**Interfaces:**
- Consumes (from Task 1): `shaping.reverse_fold(fold, tip_xy, d, theta, gamma=45.0, sense=1)`; `shaping.axial_length(fold, tip_xy)`.
- Produces: target schema `{"node_id", "kind": "reverse"|"outside"|"crimp" (default "reverse"), "fraction" (0,1) default 0.5, "fraction2" (0,1) default 0.5 (crimp only), "theta"}`; every verdict dict gains `"kind"`. Wrapper keys otherwise unchanged.

- [ ] **Step 1: Write the failing engine tests**

In `mcp_harness/tests/test_shaping_tool.py`, append:

```python
def test_kinds_batch_outside_crimp_guard_and_unknown():
    # ONE compile covers: outside applied; crimp applied atomically (two
    # ops, d2 = fraction2*d1); theta=90 crimp refused up front (silent
    # mis-targeting guard); unknown kind refused. Params probe-verified
    # 2026-07-02 (star-4: same-leaf stacking applies at theta 75).
    out = _run([
        {"node_id": 3, "kind": "outside", "fraction": 0.5, "theta": 75},
        {"node_id": 2, "kind": "crimp", "fraction": 0.5,
         "fraction2": 0.5, "theta": 75},
        {"node_id": 4, "kind": "crimp", "theta": 90},
        {"node_id": 1, "kind": "narrow", "theta": 75},
    ])
    assert out["status"] == "shaped"
    assert [v["status"] for v in out["verdicts"]] == \
        ["applied", "applied", "refused", "refused"]
    assert [v["kind"] for v in out["verdicts"]] == \
        ["outside", "crimp", "crimp", "narrow"]
    assert "90" in out["verdicts"][2]["reason"]
    assert "kind" in out["verdicts"][3]["reason"]
    # ops: outside:1 + crimp expansion:2 = 3, in application order
    assert len(out["ide_shape_ops"]) == 3
    assert out["ide_shape_ops"][0].startswith("outside:")
    assert out["ide_shape_ops"][1].startswith("reverse:")
    assert out["ide_shape_ops"][2].startswith("outside:")
    for op in out["ide_shape_ops"]:
        shaping.parse_op(op)
    # crimp halves: d2 == fraction2 * d1 exactly (baked-d contract)
    d1 = float(out["ide_shape_ops"][1].split(":")[2])
    d2 = float(out["ide_shape_ops"][2].split(":")[2])
    assert d2 == 0.5 * d1
    # display-replay equivalence over the mixed grammar: 3 folds -> +15 edges
    squared = square_complete.complete_square(out["fold"], 1.0, 1.0)
    shaped = shaping.apply_display_ops(squared, out["ide_shape_ops"])
    assert len(shaped["edges_vertices"]) == \
        len(squared["edges_vertices"]) + 15
    assert len(shaped["edges_foldAngle"]) == len(shaped["edges_vertices"])


def test_crimp_second_half_failure_rolls_back(monkeypatch):
    # No in-range fraction2 refuses naturally on star-4 (probe-verified),
    # so force the outside half to fail: the contract under test is the
    # tool's atomic bookkeeping, not the geometry (unit-tested in Task 1).
    real = shaping.reverse_fold

    def flaky(fold, tip_xy, d, theta, gamma=45.0, sense=1):
        if sense == -1:
            raise shaping.ShapingError("forced outside failure")
        return real(fold, tip_xy, d, theta, gamma=gamma, sense=sense)

    monkeypatch.setattr(shaping, "reverse_fold", flaky)
    out = _run([
        {"node_id": 2, "kind": "crimp", "theta": 75},
        {"node_id": 3, "fraction": 0.25, "theta": 90},
    ])
    assert [v["status"] for v in out["verdicts"]] == ["refused", "applied"]
    assert out["verdicts"][0]["kind"] == "crimp"
    assert out["verdicts"][0]["reason"] == "forced outside failure"
    # the applied inside half was rolled back: no leaked crimp ops, and the
    # following plain-reverse target validated against the UNSHAPED state
    assert len(out["ide_shape_ops"]) == 1
    assert out["ide_shape_ops"][0].startswith("reverse:")
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd <repo>/mcp_harness && .venv/bin/python -m pytest tests/test_shaping_tool.py -q`
Expected: the two new tests FAIL (verdicts lack `kind`; unknown kind currently ignored, so statuses mismatch). Existing four tests still pass. (6 tests = 6 real compiles, expect ~1–3 min.)

- [ ] **Step 3: Implement the per-target loop in `mcp_harness/server.py`**

In `apply_shaping_ops`, replace the entire `for t in (targets or []):` loop with:

```python
    ops: list[str] = []
    verdicts: list[dict] = []
    for t in (targets or []):
        nid = t.get("node_id") if isinstance(t, dict) else None
        kind = t.get("kind", "reverse") if isinstance(t, dict) else "reverse"

        def refuse(reason):
            verdicts.append({"node_id": nid, "kind": kind,
                             "status": "refused", "reason": reason})

        if kind not in ("reverse", "outside", "crimp"):
            refuse("kind must be reverse, outside, or crimp")
            continue
        if not isinstance(nid, int) or nid not in locs:
            refuse("unknown or non-leaf node_id")
            continue
        try:
            fraction = float(t.get("fraction", 0.5))
            fraction2 = float(t.get("fraction2", 0.5))
            theta = float(t["theta"])
        except (KeyError, TypeError, ValueError):
            refuse("target needs numeric theta (fraction/fraction2 optional)")
            continue
        if not 0 < fraction < 1:
            refuse("fraction must be in (0, 1)")
            continue
        if kind == "crimp" and not 0 < fraction2 < 1:
            refuse("fraction2 must be in (0, 1)")
            continue
        if not 0 < theta <= 180:
            refuse("theta must be in (0, 180]")
            continue
        if kind in ("outside", "crimp") and theta == 180:
            refuse("outside/crimp need theta < 180")
            continue
        if kind == "crimp" and theta == 90:
            refuse("crimp cannot use theta exactly 90 (the first half "
                   "flattens the tip axial and the second half would "
                   "mis-target another flap); use e.g. 75 or 105")
            continue
        x, y = locs[nid]
        try:
            if kind == "crimp":
                # atomic: nothing recorded until BOTH halves have applied
                d1 = fraction * shaping.axial_length(current, (x, y))
                step1 = shaping.reverse_fold(current, (x, y), d1, theta)
                d2 = fraction2 * d1
                step2 = shaping.reverse_fold(step1, (x, y), d2, theta,
                                             sense=-1)
                current = step2
                ops.append(f"reverse:{x},{y}:{d1}:{theta}")
                ops.append(f"outside:{x},{y}:{d2}:{theta}")
            else:
                d = fraction * shaping.axial_length(current, (x, y))
                current = shaping.reverse_fold(
                    current, (x, y), d, theta,
                    sense=1 if kind == "reverse" else -1)
                ops.append(f"{kind}:{x},{y}:{d}:{theta}")
        except shaping.ShapingError as exc:
            refuse(str(exc))
            continue
        verdicts.append({"node_id": nid, "kind": kind, "status": "applied"})
```

Update the tool docstring's `targets` paragraph to (keep the rest of the docstring as-is, it is the agent-facing schema and must stay concise):

```
    targets: [{"node_id": <leaf id from your compiled tree>,
               "kind": "reverse" (default: bend at a point) | "outside"
               (bend the other way) | "crimp" (zigzag: offsets the flap
               sideways, keeps its direction),
               "fraction": 0-1 fold point along the flap from the tip
               (default 0.5), "fraction2": crimp only, 0-1 second fold
               point within the tip segment (default 0.5),
               "theta": bend degrees -- (0, 180] for reverse, (0, 180)
               for outside/crimp, and crimp must not use exactly 90}].
    For "reverse", bend direction follows the flap's axial crease M/V
    family; theta is a magnitude only. A crimp counts as ONE verdict but
    TWO entries in ide_shape_ops.
```

- [ ] **Step 4: Run the tool tests**

Run: `cd <repo>/mcp_harness && .venv/bin/python -m pytest tests/test_shaping_tool.py -q`
Expected: PASS — all 6 (4 existing + 2 new).

- [ ] **Step 5: Run the neighbor suites (regression)**

Run: `cd <repo>/mcp_harness && .venv/bin/python -m pytest tests/test_shaping.py tests/test_shaping_fixture.py -q && cd <repo> && mcp_harness/.venv/bin/python -m pytest web/tests -q`
Expected: PASS (web suite proves the untouched transport still replays tool ops).

- [ ] **Step 6: Commit**

```bash
cd <repo>
git add mcp_harness/server.py mcp_harness/tests/test_shaping_tool.py
git commit -m "feat(shaping): kind targets — outside reverse + atomic crimp composition in apply_shaping_ops"
```

---

### Task 3: HITL prompt kinds vocabulary

**Files:**
- Modify: `mcp_harness/agent_loop.py` (the SHAPING section of `SYSTEM_PROMPT`, lines ~266-282)
- Test: `mcp_harness/tests/test_agent_shaping_prompt.py`

**Interfaces:**
- Consumes: the Task 2 target schema (the prompt must mirror it exactly).
- Produces: nothing downstream; the pinned substrings below.

- [ ] **Step 1: Write the failing pin test**

Append to `mcp_harness/tests/test_agent_shaping_prompt.py`:

```python
def test_prompt_teaches_target_kinds():
    for needle in ('"outside"', '"crimp"', "fraction2", "75 or 105"):
        assert needle in P, f"missing kinds-vocabulary pin: {needle}"
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd <repo>/mcp_harness && .venv/bin/python -m pytest tests/test_agent_shaping_prompt.py -q`
Expected: FAIL on the new test only.

- [ ] **Step 3: Edit the SHAPING section in `SYSTEM_PROMPT`**

In `mcp_harness/agent_loop.py`, replace these two exact fragments of the SHAPING paragraph.

Fragment 1 (the call schema) — replace:

```
apply_shaping_ops(tree_nodes=<the SAME tree you compiled>, \
symmetric_pairs=<the same pairs>, targets=[{node_id, fraction, theta}, ...]). \
Bend direction follows the flap's axial crease mountain/valley family -- theta \
is a magnitude only.
```

with:

```
apply_shaping_ops(tree_nodes=<the SAME tree you compiled>, \
symmetric_pairs=<the same pairs>, targets=[{node_id, kind, fraction, \
fraction2, theta}, ...]). Target kinds: "reverse" (default) bends the flap at \
the fold point -- direction follows the flap's axial crease mountain/valley \
family, theta is a magnitude only; "outside" bends the opposite way (needs \
theta below 180); "crimp" zigzags at the fold point, offsetting the flap \
sideways while keeping its direction (knees, ankles, neck angles, beaks) -- \
"fraction2" (0-1, default 0.5) places its second fold within the tip \
segment, and crimp needs theta below 180 and NOT exactly 90 (pick e.g. \
75 or 105).
```

- [ ] **Step 4: Run the prompt pins**

Run: `cd <repo>/mcp_harness && .venv/bin/python -m pytest tests/test_agent_shaping_prompt.py -q`
Expected: PASS — all 4 (the 3 existing pins, including `"ONLY AFTER THE USER APPROVES"`, must pass unmodified).

- [ ] **Step 5: Commit**

```bash
cd <repo>
git add mcp_harness/agent_loop.py mcp_harness/tests/test_agent_shaping_prompt.py
git commit -m "feat(agent): SYSTEM_PROMPT teaches outside/crimp target kinds"
```

---

### Task 4: Full gates + live acceptance demo

**Files:**
- Create: `docs/b3-dog-crimp-model-tab.png` (evidence screenshot)
- No source changes (fix regressions only if the gates fail).

**Interfaces:**
- Consumes: everything above.

- [ ] **Step 1: Full backend suite**

Run: `cd <repo>/mcp_harness && .venv/bin/python -m pytest tests -q`
Expected: 281+ passed / 3 skipped (B2 baseline 278/3 plus this cycle's net-new tests), ~10 min (real spawn compiles).

- [ ] **Step 2: Web suite**

Run: `cd <repo> && mcp_harness/.venv/bin/python -m pytest web/tests -q`
Expected: 34 passed.

- [ ] **Step 3: Live Groq demo (manual acceptance, per spec §1)**

1. Start the server from the repo root:
   `LLM_PROVIDER=groq LLM_MODEL=meta-llama/llama-4-scout-17b-16e-instruct mcp_harness/.venv/bin/python -m uvicorn web.server:app --port 8000`
   (llama-3.3-70b exceeds the free-tier 12k TPM on request 1 — do not use it.)
2. In the chat: "design a dog". Wait for compile + Pass.
3. Then: "crimp its neck" (expect the agent to propose/call `apply_shaping_ops` with a `crimp` target at theta ≠ 90) and/or "bend the head back" (expect an `outside` target).
4. Open the Model tab; wait for the strain oracle to converge; screenshot the posed render to `docs/b3-dog-crimp-model-tab.png`.
5. Identity check: a fresh "design a dog" turn with no shaping request must render exactly as before (no kind → byte-identical path).
6. Known flakes: Groq `tool_use_failed` 400s mid-turn usually self-recover on retry.

- [ ] **Step 4: Commit the evidence**

```bash
cd <repo>
git add docs/b3-dog-crimp-model-tab.png
git commit -m "docs(shaping): live acceptance evidence — crimp/outside posed dog in Model tab"
```
