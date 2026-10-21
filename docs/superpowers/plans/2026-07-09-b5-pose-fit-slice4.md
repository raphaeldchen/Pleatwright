# B5 Slice 4 — Second Descent Pass + Crimp Reachability: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure whether a second coordinate-descent pass plus a crimp op on the back group can close (or provably cannot close) the gap between the winner base (asymmetric star b=0.95, h=0.40) and the fox pose targets {front 134.8316, back 138.6544, head 137.7186} deg.

**Architecture:** Pure-loop extraction — a pytest-covered `pose_search.coordinate_descent` drives both the reverse-only resume pass (gate 1) and the extended 5-stage fit (gate 3); a new `probe_crimp_range.py` gates (gate 2, HALT unless crimp beats the reverse-only ceiling by >= 10 deg) between them. Crimp enters via `shaping.crimp_ops`, a pure string-builder replicating the tool-layer reverse+outside composition — never ad-hoc op strings.

**Tech Stack:** Python (mcp_harness), pytest, Playwright-driven HEADED Origami Simulator (`sim_capture.SimSession`), TreeMaker compile via `server._run_isolated`.

**Spec:** `docs/superpowers/specs/2026-07-09-b5-pose-fit-slice4-design.md`
**Branch:** `feat/b5-pose-fit-slice4` (already created off main `6a880ca`; spec committed).

## Global Constraints

- Human merges every PR — ask before push/PR.
- Probe outputs (`*.out.json`, `*.out.jsonl`, `*.out.log`) and suite logs stay UNCOMMITTED.
- playwright lives in `mcp_harness/.venv` ONLY — never requirements/CI.
- `SimSession` is HEADED by default (`PW_HEADLESS=1` opts in); headless WebGL is dead.
- Solver deterministic-ish ONLY: capture drift ~1e-5–0.02 deg — never 0.0 tolerances, never assert bit-identical re-captures.
- Measure-then-pin: no pinned constant that wasn't first printed and hand-checked.
- Op vocabulary strings are the engine's own (`reverse:`/`outside:`/…); crimp extends via composition (PR #23 semantics), NOT ad-hoc strings.
- crimp theta=90 silently MIS-TARGETS — guarded; grids avoid it (75/105).
- Anti-vacuous guard: every sim assertion requires maxDisplacement > 0.1 (`sim_capture.check_capture` enforces); expect flat-equilibrium holes in grids.
- Long probe runs: `nohup` from subagent shells; the controller polls the `.out.log`, never Monitor.
- Full backend suite (`cd mcp_harness && .venv/bin/python -m pytest tests -q`) must stay green (baseline 424 passed / 3 skipped, ~10 min).
- NO new MCP tools, agent, prompt, or UI work — probes + harness modules only.
- SDD ledger at `.superpowers/sdd/progress.md`; review packages via `git diff BASE..HEAD > .superpowers/sdd/review-BASE..HEAD.diff`.
- HONEST-OUTCOME RULE: a documented FAIL or gated HALT with measured numbers is a successful slice. Never soften verdicts.
- All commands below run from `<repo>/mcp_harness` unless stated otherwise; python is `.venv/bin/python`.

---

### Task 1: `pose_search.coordinate_descent` (pure multi-pass loop)

**Files:**
- Modify: `mcp_harness/pose_search.py` (append after `refine`)
- Test: `mcp_harness/tests/test_pose_search.py` (append)

**Interfaces:**
- Consumes: existing `grid_search(evaluate, axes)`, `refine(evaluate, axes, best_params)`, `PoseSearchError` (all already in `pose_search.py`).
- Produces (Tasks 7/9 rely on these exact names):
  - `DescentStage = namedtuple("DescentStage", "group axes coarse fine")` — `coarse`/`fine` are `GridResult`s.
  - `DescentResult = namedtuple("DescentResult", "fitted stages")` — `fitted` is `{group: tuple(best_params)}`.
  - `coordinate_descent(evaluator_factory, schedule, initial=None) -> DescentResult` where `schedule` is a list of `(group, axes)` and `evaluator_factory(group, fitted_snapshot) -> evaluate(params) -> float`.

- [ ] **Step 1: Write the failing tests** — append to `mcp_harness/tests/test_pose_search.py`:

```python
# ---------- coordinate_descent ----------

def _bowl_factory(centers, calls):
    """Factory whose evaluator is a bowl at centers[group]; records each
    (group, fitted_snapshot) so tests can see stage sequencing and
    fitted-dict threading."""
    def factory(group, fitted):
        calls.append((group, dict(fitted)))

        def evaluate(params):
            return sum((p - c) ** 2 for p, c in zip(params, centers[group]))
        return evaluate
    return factory


def test_coordinate_descent_sequences_and_threads_fitted():
    calls = []
    axes = [[0.0, 2.0, 4.0]]
    centers = {"a": (1.1,), "b": (3.9,)}
    schedule = [("a", axes), ("b", axes), ("a", axes)]
    res = pose_search.coordinate_descent(
        _bowl_factory(centers, calls), schedule)
    assert [c[0] for c in calls] == ["a", "b", "a"]
    assert calls[0][1] == {}                      # first stage: nothing fitted
    assert set(calls[1][1]) == {"a"}              # b sees a's fit
    assert set(calls[2][1]) == {"a", "b"}         # re-pass sees both
    assert set(res.fitted) == {"a", "b"}
    # bowl at 1.1: coarse best 2.0; refine grid over [0,4] = {0,1,2,3,4}
    # -> best 1.0 (hand-derived)
    assert res.fitted["a"] == (1.0,)


def test_coordinate_descent_initial_seeds_fitted():
    calls = []
    axes = [[0.0, 2.0, 4.0]]
    res = pose_search.coordinate_descent(
        _bowl_factory({"a": (1.1,)}, calls), [("a", axes)],
        initial={"c": (7.0, 8.0)})
    assert calls[0][1] == {"c": (7.0, 8.0)}       # seed visible to stage 1
    assert res.fitted["c"] == (7.0, 8.0)          # unsearched seed survives
    assert res.fitted["a"] == (1.0,)


def test_coordinate_descent_records_stages():
    calls = []
    axes = [[0.0, 2.0, 4.0]]
    res = pose_search.coordinate_descent(
        _bowl_factory({"a": (1.1,)}, calls), [("a", axes)])
    assert len(res.stages) == 1
    st = res.stages[0]
    assert st.group == "a"
    assert st.coarse.best_params == (2.0,)
    assert st.fine.best_params == (1.0,)
    assert st.fine.best_score <= st.coarse.best_score


def test_coordinate_descent_empty_schedule_raises():
    with pytest.raises(PoseSearchError):
        pose_search.coordinate_descent(_bowl_factory({}, []), [])


def test_coordinate_descent_all_inf_stage_raises():
    def factory(group, fitted):
        def evaluate(params):
            raise RuntimeError("sim exploded")
        return evaluate
    with pytest.raises(PoseSearchError):
        pose_search.coordinate_descent(factory, [("a", [[0.0, 1.0]])])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_pose_search.py -q -k coordinate_descent`
Expected: 5 failed — `AttributeError: module 'pose_search' has no attribute 'coordinate_descent'`

- [ ] **Step 3: Implement** — append to `mcp_harness/pose_search.py`:

```python
DescentStage = namedtuple("DescentStage", "group axes coarse fine")
DescentResult = namedtuple("DescentResult", "fitted stages")


def coordinate_descent(evaluator_factory, schedule, initial=None
                       ) -> DescentResult:
    """Sequential coordinate descent over an EXPLICIT stage schedule
    (B5 slice 4): schedule = [(group, axes), ...]; each stage runs
    grid_search + one refine and writes fitted[group]. Re-passes are just
    repeated groups in the schedule -- no implicit pass counting.

    evaluator_factory(group, fitted_snapshot) must return the evaluate
    callable for that stage; the snapshot is a COPY of the currently
    fitted params (cross-group coupling is the caller's business -- the
    factory closes over it). `initial` seeds fitted (resume support);
    unsearched seed entries survive into the result untouched."""
    if not schedule:
        raise PoseSearchError("schedule must be a non-empty stage list")
    fitted = dict(initial or {})
    stages = []
    for group, axes in schedule:
        evaluate = evaluator_factory(group, dict(fitted))
        coarse = grid_search(evaluate, axes)
        fine = refine(evaluate, axes, coarse.best_params)
        fitted[group] = tuple(fine.best_params)
        stages.append(DescentStage(group, [list(a) for a in axes],
                                   coarse, fine))
    return DescentResult(fitted, stages)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_pose_search.py -q`
Expected: all pass (existing + 5 new), 0 failed

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/pose_search.py mcp_harness/tests/test_pose_search.py
git commit -m "feat(b5-slice4): pose_search.coordinate_descent -- explicit-schedule multi-pass descent (pure, mock-tested)"
```

---

### Task 2: `pose_search.grid_step_tol` (shared tolerance rule)

**Files:**
- Modify: `mcp_harness/pose_search.py` (append)
- Test: `mcp_harness/tests/test_pose_search.py` (append)

**Interfaces:**
- Produces (Tasks 6/8 rely on this exact name): `grid_step_tol(angles, best_index) -> float | None` — `angles` is a grid-ordered list of achieved values with `None` for failed cells; returns the one-grid-step tolerance at the best cell, or `None` when no grid-adjacent successful pair exists anywhere; raises `PoseSearchError` if `best_index` is out of range or points at a `None`.

- [ ] **Step 1: Write the failing tests** — append to `mcp_harness/tests/test_pose_search.py`:

```python
# ---------- grid_step_tol ----------

def test_grid_step_tol_uses_adjacent_neighbors():
    # best at idx 2 (15); neighbors 12 and 19 -> max(|12-15|, |19-15|) = 4
    assert pose_search.grid_step_tol([10.0, 12.0, 15.0, 19.0, 24.0], 2) \
        == pytest.approx(4.0)


def test_grid_step_tol_skips_failed_neighbor():
    # left neighbor failed: only the RIGHT neighbor counts -- the fix for
    # slice 3's bug where "adjacent in the successful-only list" silently
    # spanned two grid steps.
    assert pose_search.grid_step_tol([10.0, None, 15.0, 19.0, 24.0], 2) \
        == pytest.approx(4.0)


def test_grid_step_tol_fallback_max_adjacent_pair():
    # best at idx 0 with a failed idx 1: no adjacent neighbor of best ->
    # fallback = max |diff| over ALL grid-adjacent successful pairs
    # (here only (14, 15) -> 1.0)
    assert pose_search.grid_step_tol([10.0, None, 14.0, 15.0], 0) \
        == pytest.approx(1.0)


def test_grid_step_tol_none_when_no_adjacent_pair():
    assert pose_search.grid_step_tol([10.0, None, 15.0, None, 24.0], 2) \
        is None


def test_grid_step_tol_rejects_bad_best_index():
    with pytest.raises(PoseSearchError):
        pose_search.grid_step_tol([10.0, None], 1)   # best is a failed cell
    with pytest.raises(PoseSearchError):
        pose_search.grid_step_tol([10.0], 5)          # out of range
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_pose_search.py -q -k grid_step_tol`
Expected: 5 failed — no attribute `grid_step_tol`

- [ ] **Step 3: Implement** — append to `mcp_harness/pose_search.py`:

```python
def grid_step_tol(angles, best_index):
    """One-grid-step tolerance at a sweep's best cell (B5 slice 4 fix:
    slice 3 took neighbors from the successful-only list, so a failed
    cell made 'adjacent' span 2+ grid steps and silently inflated the
    fit's PASS bound). angles: achieved values in GRID order, None =
    failed cell. Prefer the best cell's grid-adjacent successful
    neighbors (max |diff| vs best); fallback = max |diff| over ALL
    grid-adjacent successful pairs; None if no such pair exists."""
    if not 0 <= best_index < len(angles) or angles[best_index] is None:
        raise PoseSearchError("best_index must point at a successful cell")
    best = float(angles[best_index])
    near = [float(angles[j]) for j in (best_index - 1, best_index + 1)
            if 0 <= j < len(angles) and angles[j] is not None]
    if near:
        return max(abs(a - best) for a in near)
    steps = [abs(float(angles[j + 1]) - float(angles[j]))
             for j in range(len(angles) - 1)
             if angles[j] is not None and angles[j + 1] is not None]
    return max(steps) if steps else None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_pose_search.py -q`
Expected: all pass, 0 failed

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/pose_search.py mcp_harness/tests/test_pose_search.py
git commit -m "fix(b5-slice4): grid_step_tol -- grid-adjacent tolerance rule (slice-3 angle_tol spanned failed cells)"
```

---

### Task 3: `shaping.crimp_ops` (pure crimp composition)

**Files:**
- Modify: `mcp_harness/shaping.py` (append after `parse_op`)
- Test: `mcp_harness/tests/test_shaping.py` (append)

**Interfaces:**
- Consumes: `ShapingError` (exists in `shaping.py`).
- Produces (Task 5 relies on this exact name): `crimp_ops(tip_xy, axial_len, theta, fraction, fraction2) -> [str, str]` — the atomic `reverse:` + `outside:` pair with `d1 = fraction * axial_len`, `d2 = fraction2 * d1`. Raises `ShapingError` on: fraction/fraction2 outside (0, 1), theta outside (0, 180), theta exactly 90, axial_len <= 0.

- [ ] **Step 1: Write the failing tests** — append to `mcp_harness/tests/test_shaping.py`:

```python
# ---------- crimp_ops (B5 slice 4: tool-layer crimp as op strings) ----------

def test_crimp_ops_composition_matches_tool_layer():
    # server.apply_shaping_ops formula: d1 = fraction*axial, d2 = f2*d1,
    # second half is the outside (sense=-1) op. Strings must round-trip
    # through parse_op (the engine's own vocabulary, no new op kinds).
    ops = shaping.crimp_ops((0.25, 0.75), 0.4, 105.0, 0.5, 0.35)
    d1 = 0.5 * 0.4
    d2 = 0.35 * d1
    assert ops == [f"reverse:0.25,0.75:{d1}:105.0",
                   f"outside:0.25,0.75:{d2}:105.0"]
    assert shaping.parse_op(ops[0]) == ("reverse", (0.25, 0.75), d1, 105.0)
    assert shaping.parse_op(ops[1]) == ("outside", (0.25, 0.75), d2, 105.0)


def test_crimp_ops_rejects_theta_90_exactly():
    # theta=90 silently MIS-TARGETS (first half flattens the tip axial);
    # the tool layer guards it and so must the composition helper.
    with pytest.raises(shaping.ShapingError):
        shaping.crimp_ops((0.5, 0.5), 0.4, 90.0, 0.5, 0.5)


def test_crimp_ops_rejects_theta_bounds():
    with pytest.raises(shaping.ShapingError):
        shaping.crimp_ops((0.5, 0.5), 0.4, 180.0, 0.5, 0.5)  # outside needs <180
    with pytest.raises(shaping.ShapingError):
        shaping.crimp_ops((0.5, 0.5), 0.4, 0.0, 0.5, 0.5)


def test_crimp_ops_rejects_bad_fractions_and_axial():
    with pytest.raises(shaping.ShapingError):
        shaping.crimp_ops((0.5, 0.5), 0.4, 105.0, 0.0, 0.5)
    with pytest.raises(shaping.ShapingError):
        shaping.crimp_ops((0.5, 0.5), 0.4, 105.0, 0.5, 1.0)
    with pytest.raises(shaping.ShapingError):
        shaping.crimp_ops((0.5, 0.5), 0.0, 105.0, 0.5, 0.5)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_shaping.py -q -k crimp_ops`
Expected: 4 failed — no attribute `crimp_ops`

- [ ] **Step 3: Implement** — append to `mcp_harness/shaping.py` directly after `parse_op`:

```python
def crimp_ops(tip_xy, axial_len, theta, fraction, fraction2):
    """The tool-layer crimp (server.apply_shaping_ops, PR #23) as engine
    op strings: a reverse fold at d1 = fraction*axial_len then an outside
    fold at d2 = fraction2*d1 -- a zigzag that offsets the flap sideways
    but keeps its direction. Emits ONLY existing op vocabulary so display
    replay via ide_shape_ops is unchanged; the pair is atomic only if the
    CALLER refuses the whole crimp when either half is refused
    (starhead.apply_ops raises on any refusal, so evals stay honest).
    Guards mirror the tool layer, including theta != 90: the first half
    flattens the tip axial and the second half would mis-target another
    flap (known silent hazard; use e.g. 75 or 105)."""
    if not 0 < fraction < 1:
        raise ShapingError("crimp fraction must be in (0, 1)")
    if not 0 < fraction2 < 1:
        raise ShapingError("crimp fraction2 must be in (0, 1)")
    if not 0 < theta < 180:
        raise ShapingError("crimp needs 0 < theta < 180")
    if theta == 90:
        raise ShapingError("crimp cannot use theta exactly 90 (the first "
                           "half flattens the tip axial and the second "
                           "half would mis-target another flap); use e.g. "
                           "75 or 105")
    if axial_len <= 0:
        raise ShapingError("axial_len must be > 0")
    x, y = tip_xy
    d1 = fraction * axial_len
    d2 = fraction2 * d1
    return [f"reverse:{x},{y}:{d1}:{theta}",
            f"outside:{x},{y}:{d2}:{theta}"]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_shaping.py -q`
Expected: all pass, 0 failed

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/shaping.py mcp_harness/tests/test_shaping.py
git commit -m "feat(b5-slice4): shaping.crimp_ops -- tool-layer crimp composition as engine op strings (theta-90 guard carried)"
```

---

### Task 4: `pose_target.head_among_unpaired` + fox tail-drop tie guard

**Files:**
- Modify: `mcp_harness/pose_target.py` (append)
- Modify: `mcp_harness/starhead.py:284-291` (the tail-drop block inside `fox_targets`)
- Test: `mcp_harness/tests/test_pose_target.py` (append)

**Interfaces:**
- Consumes: `PoseTargetError` (exists in `pose_target.py`).
- Produces: `head_among_unpaired(leaf_ys) -> (head_node, dropped_list)` — `leaf_ys` is `[(node, y)]` for every unpaired leaf; head = max y; tie within 1e-6 between the top two raises `PoseTargetError`; empty input raises `PoseTargetError`.

- [ ] **Step 1: Write the failing tests** — append to `mcp_harness/tests/test_pose_target.py`:

```python
# ---------- head_among_unpaired (B5 slice 4: fox tail-drop tie guard) ----------

def test_head_among_unpaired_picks_max_y_and_drops_rest():
    # fox-like: head y=39.9 far above tail y=18.1 (the pinned rule's
    # measured case, committed fixture is y-up)
    head, dropped = pose_target.head_among_unpaired(
        [(7, 18.1), (3, 39.9), (9, 25.0)])
    assert head == 3
    assert dropped == [9, 7]        # y-descending after the head


def test_head_among_unpaired_single_leaf_no_drops():
    assert pose_target.head_among_unpaired([(4, 12.0)]) == (4, [])


def test_head_among_unpaired_tie_raises():
    # never guess the head: a y-tie within 1e-6 is ambiguous anatomy
    with pytest.raises(pose_target.PoseTargetError):
        pose_target.head_among_unpaired([(3, 20.0), (7, 20.0 + 5e-7)])


def test_head_among_unpaired_empty_raises():
    with pytest.raises(pose_target.PoseTargetError):
        pose_target.head_among_unpaired([])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_pose_target.py -q -k head_among_unpaired`
Expected: 4 failed — no attribute `head_among_unpaired`

- [ ] **Step 3: Implement helper** — append to `mcp_harness/pose_target.py`:

```python
def head_among_unpaired(leaf_ys):
    """Pick the head among a tree's unpaired leaves: the one with max y
    (the committed fox fixture is y-up; measured head y=39.9 vs tail
    y=18.1). leaf_ys: [(node, y)]. Returns (head, dropped) with dropped
    in y-descending order. A tie within 1e-6 between the top two ->
    PoseTargetError: never guess which leaf is the head (B5 slice-4
    guard; same never-guess principle as the hub-tie check)."""
    if not leaf_ys:
        raise PoseTargetError("no unpaired leaves to pick a head from")
    by_y = sorted(leaf_ys, key=lambda ny: float(ny[1]), reverse=True)
    if len(by_y) > 1 and abs(float(by_y[0][1]) - float(by_y[1][1])) < 1e-6:
        raise PoseTargetError(
            f"head ambiguous: unpaired leaves {by_y[0][0]} and"
            f" {by_y[1][0]} tie on y ({by_y[0][1]} vs {by_y[1][1]})")
    return by_y[0][0], [n for n, _ in by_y[1:]]
```

- [ ] **Step 4: Wire into `starhead.fox_targets`** — replace this block in `mcp_harness/starhead.py` (currently lines 284-291):

```python
    unpaired = sorted(leaves - paired)
    dropped = []
    if len(unpaired) > 1:
        by_y = sorted(unpaired,
                      key=lambda n: float(tree.nodes[n]["pos"][1]),
                      reverse=True)
        dropped = by_y[1:]
        tree.remove_nodes_from(dropped)
```

with:

```python
    unpaired = sorted(leaves - paired)
    dropped = []
    if len(unpaired) > 1:
        # tie guard lives in pose_target (pytest-covered): a y-tie means
        # the head is ambiguous -> PoseTargetError, never guess
        _, dropped = pose_target.head_among_unpaired(
            [(n, float(tree.nodes[n]["pos"][1])) for n in unpaired])
        tree.remove_nodes_from(dropped)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_pose_target.py -q`
Expected: all pass (10 existing + 4 new), 0 failed
(The starhead wiring is exercised live by Task 6's `probe_angle_range` re-run — its printed `fox skeleton info` must show the same drop as slice 3: tail dropped, 1 head + 2 leg pairs.)

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/pose_target.py mcp_harness/starhead.py mcp_harness/tests/test_pose_target.py
git commit -m "fix(b5-slice4): fox tail-drop tie guard -- head pick moves to pose_target.head_among_unpaired (never guess on a y-tie)"
```

---

### Task 5: `starhead.make_ops` crimp spec + winner self-check mode

**Files:**
- Modify: `mcp_harness/starhead.py` (`make_ops`, `__main__` block, new `_self_check_winner`)

**Interfaces:**
- Consumes: `shaping.crimp_ops` (Task 3), existing `StarHeadBase`, `winner_base()`, `apply_ops`.
- Produces (Tasks 7/8 rely on this): `make_ops(base, params)` where each `params[group]` is either `(theta, fraction)` (reverse, unchanged back-compat) or `("crimp", theta, fraction, fraction2)` (the crimp pair per tip in the group; a leg pair shares its params).

- [ ] **Step 1: Extend `make_ops`** — replace the whole function in `mcp_harness/starhead.py`:

```python
def make_ops(base: StarHeadBase, params: dict) -> list:
    """params: {group: spec or None} -> ops, one spec applied per flap in
    the group (a leg pair shares its params; depth d = fraction * that
    flap's own axial length).

    spec forms (B5 slice 4):
      (theta, fraction)                     -> one reverse op per tip
      ("crimp", theta, fraction, fraction2) -> the atomic reverse+outside
        pair per tip via shaping.crimp_ops (tool-layer composition;
        apply_ops raises on any refused half, so a half-applied crimp can
        never be scored)."""
    ops = []
    for grp in GROUPS:
        spec = params.get(grp)
        if spec is None:
            continue
        if len(spec) == 4 and spec[0] == "crimp":
            _, theta, frac, frac2 = spec
            for xy in base.tips[grp]:
                ops.extend(shaping.crimp_ops(xy, base.axial[xy],
                                             theta, frac, frac2))
            continue
        theta, frac = spec
        if not (0.0 < frac < 1.0):
            raise sim_capture.CaptureError(f"fraction {frac} outside (0, 1)")
        if not (0.0 < theta <= 180.0):
            raise sim_capture.CaptureError(f"theta {theta} outside (0, 180]")
        for (x, y) in base.tips[grp]:
            d = frac * base.axial[(x, y)]
            ops.append(f"reverse:{x},{y}:{d}:{theta}")
    return ops
```

- [ ] **Step 2: Add the winner self-check** — append to `mcp_harness/starhead.py` before the `__main__` block, and replace the `__main__` block:

```python
def _self_check_winner(crimp_theta: float = 105.0,
                       crimp_f2: float = 0.5) -> int:
    """Winner-base self-check (needs probe_star_asym.out.json; NO sim):
    prints grouping + a sample back CRIMP pair for hand-check. Verify by
    hand: d2 == crimp_f2 * d1, both strings parse via shaping.parse_op,
    and the pair applies (vert count grows vs base). If the sample cell
    is refused (wedge crossing), retry with another grid theta (75 or
    142.5) and record which -- the full map is Task 8's job."""
    base = winner_base()
    print("winner base constructed")
    print(f"  hub (flat): {base.hub}")
    for grp in GROUPS:
        for xy in base.tips[grp]:
            print(f"  {grp} tip {xy}  axial {base.axial[xy]:.6f}")
    cops = make_ops(base, {"back": ("crimp", crimp_theta, 0.5, crimp_f2)})
    print(f"  sample back crimp ops (theta={crimp_theta}, f=0.5,"
          f" f2={crimp_f2}):")
    for op in cops:
        print(f"    {op}  parsed {shaping.parse_op(op)}")
    shaped = apply_ops(base, cops)
    print(f"  crimp pair applied: {len(shaped['vertices_coords'])} verts"
          f" (base {len(base.sq['vertices_coords'])})")
    return 0


if __name__ == "__main__":
    _args = sys.argv[1:]
    if _args and _args[0] == "winner":
        raise SystemExit(_self_check_winner(*[float(a) for a in _args[1:]]))
    raise SystemExit(_self_check(*[float(a) for a in _args]))
```

- [ ] **Step 3: Verify — run the winner self-check (compiles the base; no sim)**

Run: `.venv/bin/python starhead.py winner 105 0.5`
Expected output shape (hand-check, measure-then-pin):
- `winner base constructed`, hub + 5 tips with axial lengths (same values slice 3 printed);
- 4 sample ops (2 back tips x reverse+outside), where each pair's `d2 / d1 == 0.5` (compute by hand from the printed strings);
- `crimp pair applied: N verts (base M)` with N > M.
If the apply is REFUSED at theta=105, retry `winner 75 0.5` then `winner 142.5 0.5`; at least one grid theta must apply, else STOP and report — the crimp probe would be dead on arrival (that finding ends the slice at gate 2 as a documented HALT).

- [ ] **Step 4: Run the existing pose/shaping tests as a regression guard**

Run: `.venv/bin/python -m pytest tests/test_pose_target.py tests/test_pose_search.py tests/test_shaping.py -q`
Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/starhead.py
git commit -m "feat(b5-slice4): make_ops crimp spec (tool-layer pair per tip) + winner self-check mode [hand-checked: d2/d1 == f2]"
```

Include the printed hand-checked sample values in the commit body.

---

### Task 6: `probe_angle_range` angle_tol fix + gate-0 run

**Files:**
- Modify: `mcp_harness/probe_angle_range.py:88-100` (tolerance block) + add `import pose_search`
- Run artifacts (UNCOMMITTED): `mcp_harness/probe_angle_range.out.{json,log}`

**Interfaces:**
- Consumes: `pose_search.grid_step_tol` (Task 2), fixed `starhead.fox_targets` (Task 4).
- Produces: regenerated `probe_angle_range.out.json` with honest `angle_tol` — the bounds source for Tasks 7/8/9. Keys used downstream: `verdict`, `fox_targets`, `winner_bh`, `best_achievable[grp]{theta,angle,gap_to_target}`, `angle_tol[grp]`.

- [ ] **Step 1: Fix the tolerance block** — in `mcp_harness/probe_angle_range.py`, add `import pose_search` after `import pose_target`, then replace (current lines 90-94):

```python
            b = min(good, key=lambda r: abs(r["angle"] - tgt))
            i = good.index(b)
            neighbors = [good[j] for j in (i - 1, i + 1)
                         if 0 <= j < len(good)]
            tol[grp] = max(abs(n["angle"] - b["angle"]) for n in neighbors)
```

with:

```python
            b = min(good, key=lambda r: abs(r["angle"] - tgt))
            # angle_tol over the FULL theta grid (slice-4 fix): taking
            # neighbors from the successful-only list let a failed cell
            # silently widen "one step" to 2+ grid steps, inflating the
            # fit's PASS bound.
            t = pose_search.grid_step_tol(
                [r.get("angle") for r in rows], rows.index(b))
            if t is None:
                print(f"GATE 3 FAIL: group {grp} has no grid-adjacent"
                      " successful sweep pair to measure angle_tol")
                out["sweep"] = sweep
                out["verdict"] = "HALT"
                json.dump(out, open(OUT, "w"), indent=2)
                return 3
            tol[grp] = t
```

- [ ] **Step 2: Full suite green (gate-0 requirement — all code tasks are now in)**

Run: `.venv/bin/python -m pytest tests -q` (~10 min)
Expected: 442 passed / 3 skipped (424 baseline + 18 new from Tasks 1-4), 0 failed. If the count differs from 442, investigate before proceeding; the exact new-test count is 5+5+4+4.

- [ ] **Step 3: Verify the winner artifact exists (probe prerequisite)**

Run: `.venv/bin/python -c "import json; print(json.load(open('probe_star_asym.out.json'))['winner'])"`
Expected: `{'b': 0.95, 'h': 0.4, 'stage': 2, ...}`
If the file is missing (fresh checkout): first run `nohup .venv/bin/python probe_star_asym.py > probe_star_asym.out.log 2>&1 &` and poll the log until its winner line prints (slice-3 machinery, unchanged; ~20 compiles + up to 3 sim tests).

- [ ] **Step 4: Re-run the range probe (HEADED sim — a window opens; ~16 captures + fox extraction, ~10 min)**

```bash
nohup .venv/bin/python probe_angle_range.py > probe_angle_range.out.log 2>&1 &
```

Poll `probe_angle_range.out.log` until the `--- VERDICT ---` block prints.
Expected (hand-check against slice-3's committed numbers — capture drift ~1e-5–0.02 deg is normal, tol values may legitimately change where a sweep cell failed):
- `fox skeleton info` shows the tail dropped, 6->5 leaves, head leaf + 2 pairs (Task 4 wiring live-verified here);
- fox targets ≈ {front 134.8316, back 138.6544, head 137.7186};
- per-group ranges ≈ front 22.47 / back 9.89 / head 13.37, all above floor 3.0;
- `PROCEED` (exit 0). A HALT here ends the slice as a documented outcome (write it up per Task 10).

- [ ] **Step 5: Commit (probe fix only — outputs stay uncommitted)**

```bash
git add mcp_harness/probe_angle_range.py
git commit -m "fix(b5-slice4): angle_tol over the full theta grid via grid_step_tol [re-run PROCEED, measured tols in body]"
```

Include the re-run's printed per-group best/tol numbers in the commit body.

---

### Task 7: rebuild `probe_pose_fit.py` (r2 + x modes) and run gate 1 (r2)

**Files:**
- Rewrite: `mcp_harness/probe_pose_fit.py` (full replacement below)
- Run artifacts (UNCOMMITTED): `mcp_harness/probe_pose_fit_r2.out.{json,jsonl,log}`

**Interfaces:**
- Consumes: `pose_search.coordinate_descent` (Task 1), `starhead.make_ops` specs (Task 5), `probe_angle_range.out.json` (Task 6).
- Produces: `probe_pose_fit_r2.out.json` with keys `final_error`, `final_angles{front,back,head}`, `back_ceiling`, `seed_error`, `per_group` — consumed by Tasks 8/9. The `x` mode (run in Task 9) consumes `probe_crimp_range.out.json` keys `verdict`, `f2_star`, `best{gap_to_target}`, `angle_tol`.

- [ ] **Step 1: Replace `mcp_harness/probe_pose_fit.py` entirely with:**

```python
"""B5 slice-4 fit driver (gates 1+3): multi-pass sequential coordinate
descent fitting the winner base's per-group shaping params to the fox
skeleton's target angles, via pose_search.coordinate_descent.

Modes (sys.argv[1]):
  r2  gate 1 -- reverse-only resume pass. Seeds the slice-3 fitted
      params (pinned constants, hand-checked printed numbers in
      docs/superpowers/2026-07-08-handoff-b5-slice3-outcome.md) and runs
      the two resume stages front -> back (the full schedule shape is
      then F->B->H->F->B across slices 3+4). Pins the reverse-only
      ceiling; NEVER halts (gate 1 is informational).
      Output: probe_pose_fit_r2.out.{json,jsonl}.
  x   gate 3 -- extended-vocabulary fit, full 5-stage schedule from
      scratch: front(rev) -> back(CRIMP) -> head(rev) -> front(rev) ->
      back(CRIMP); back searches (theta, fraction) on the crimp grid
      with fraction2 PINNED from probe_crimp_range.out.json (f2_star).
      PASS = per-group gap <= bound (back bound from the CRIMP grid,
      front/head from the reverse sweep) AND total error < unshaped
      baseline AND total error < the r2 final error.
      Output: probe_pose_fit_x.out.{json,jsonl}.

refine() around a crimp theta can generate exactly 90 (midpoint of
75..105): shaping.crimp_ops raises -> scored inf -> skipped. At most one
wasted eval per refine; expected, not special-cased.

Run (long, HEADED sim -- a window opens):
  cd mcp_harness && nohup .venv/bin/python probe_pose_fit.py r2 \
      > probe_pose_fit_r2.out.log 2>&1 &     # ~103 captures ~ 70 min
  cd mcp_harness && nohup .venv/bin/python probe_pose_fit.py x \
      > probe_pose_fit_x.out.log 2>&1 &      # ~252 captures ~ 2.6 h
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pose_search                  # noqa: E402
import pose_target                  # noqa: E402
import sim_capture                  # noqa: E402
import starhead                     # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
RANGE_JSON = os.path.join(_HERE, "probe_angle_range.out.json")
CRIMP_JSON = os.path.join(_HERE, "probe_crimp_range.out.json")
R2_JSON = os.path.join(_HERE, "probe_pose_fit_r2.out.json")
X_JSON = os.path.join(_HERE, "probe_pose_fit_x.out.json")

# Slice-3 fitted params (its gate-4 descent output), pinned from the
# committed handoff's hand-checked printed numbers (measure-then-pin) --
# NOT read from the uncommitted slice-3 probe outputs. Legitimate seed:
# fitted params are independent of the slice-3 angle_tol bug (tol feeds
# only the PASS bound, not the search), and the descent is deterministic
# modulo ~1e-5-0.02 deg capture drift.
SLICE3_FITTED = {"front": (73.75, 0.575),
                 "back": (73.75, 0.8),
                 "head": (73.75, 0.35)}

REV_AXES = [starhead.THETAS, starhead.FRACTIONS]
CRIMP_THETAS = [60.0, 75.0, 105.0, 142.5, 170.0]   # no 90 (guarded)
CRIMP_AXES = [CRIMP_THETAS, starhead.FRACTIONS]


def main(mode: str) -> int:
    if mode not in ("r2", "x"):
        print("usage: probe_pose_fit.py r2|x")
        return 2
    if not os.path.exists(RANGE_JSON):
        print(f"missing {RANGE_JSON} -- run probe_angle_range.py first")
        return 2
    rng = json.load(open(RANGE_JSON))
    if rng.get("verdict") != "PROCEED":
        print(f"probe_angle_range verdict was {rng.get('verdict')} -- halt")
        return 2
    targets = rng["fox_targets"]
    best_ach = rng["best_achievable"]
    angle_tol = rng["angle_tol"]
    print(f"fox targets: {targets}")
    print(f"winner base (b, h): {rng['winner_bh']}")

    crimp = r2 = None
    if mode == "x":
        for path, what in ((CRIMP_JSON, "probe_crimp_range.py"),
                           (R2_JSON, "probe_pose_fit.py r2")):
            if not os.path.exists(path):
                print(f"missing {path} -- run {what} first")
                return 2
        crimp = json.load(open(CRIMP_JSON))
        if crimp.get("verdict") != "PROCEED":
            print(f"crimp gate verdict was {crimp.get('verdict')} -- halt")
            return 2
        r2 = json.load(open(R2_JSON))

    out_json = X_JSON if mode == "x" else R2_JSON
    log = open(out_json.replace(".json", ".jsonl"), "w")

    def jlog(**kw):
        log.write(json.dumps(kw) + "\n")
        log.flush()

    f2_star = float(crimp["f2_star"]) if mode == "x" else None

    def to_spec(group, params):
        """Search params (theta, fraction) -> make_ops spec; in x mode
        the back group folds as a crimp with the pinned f2_star."""
        theta, frac = params
        if mode == "x" and group == "back":
            return ("crimp", theta, frac, f2_star)
        return (theta, frac)

    if mode == "x":
        schedule = [("front", REV_AXES), ("back", CRIMP_AXES),
                    ("head", REV_AXES), ("front", REV_AXES),
                    ("back", CRIMP_AXES)]
        initial = None
    else:
        schedule = [("front", REV_AXES), ("back", REV_AXES)]
        initial = dict(SLICE3_FITTED)

    base = starhead.winner_base()
    seed_angles = seed_err = None
    with sim_capture.SimSession() as sim:
        cap = sim.capture(base.sq)
        _V, disp = sim_capture.check_capture(cap)
        baseline_angles = starhead.achieved_angles(base, base.sq, cap)
        baseline_err = pose_target.angle_error(baseline_angles, targets)
        jlog(kind="baseline", angles=baseline_angles, error=baseline_err,
             disp=disp)
        print(f"baseline angles {baseline_angles} error {baseline_err:.4f}")

        if mode == "r2":
            # Re-measure the seed (slice-3 final) in THIS session: the r2
            # improvement claim compares fresh captures, not the
            # handoff's number (capture drift ~1e-5-0.02 deg).
            shaped = starhead.apply_ops(base, starhead.make_ops(
                base, {g: to_spec(g, p) for g, p in SLICE3_FITTED.items()}))
            cap = sim.capture(shaped)
            _V, disp = sim_capture.check_capture(cap)
            seed_angles = starhead.achieved_angles(base, shaped, cap)
            seed_err = pose_target.angle_error(seed_angles, targets)
            jlog(kind="seed",
                 fitted={g: list(v) for g, v in SLICE3_FITTED.items()},
                 angles=seed_angles, error=seed_err, disp=disp)
            print(f"seed (slice-3 fitted) angles {seed_angles}"
                  f" error {seed_err:.4f}")

        def evaluator_factory(group, fitted_snapshot):
            def evaluate(params):
                p = dict(fitted_snapshot)
                p[group] = tuple(params)
                spec = {g: to_spec(g, v) for g, v in p.items()}
                shaped = starhead.apply_ops(base,
                                            starhead.make_ops(base, spec))
                cap = sim.capture(shaped)
                _V, disp = sim_capture.check_capture(cap)
                ach = starhead.achieved_angles(base, shaped, cap)
                err = pose_target.angle_error(ach, targets)
                jlog(kind="eval", group=group, params=list(params),
                     disp=disp, achieved=ach, score=err)
                print(f"  eval {group} {tuple(params)}: err {err:.4f}",
                      flush=True)
                return err
            return evaluate

        res = pose_search.coordinate_descent(evaluator_factory, schedule,
                                             initial=initial)
        stage_rows = []
        for st in res.stages:
            row = {"group": st.group,
                   "coarse": list(st.coarse.best_params),
                   "coarse_score": st.coarse.best_score,
                   "fine": list(st.fine.best_params),
                   "fine_score": st.fine.best_score}
            stage_rows.append(row)
            jlog(kind="stage", **row)
            print(f"stage {st.group}: coarse {st.coarse.best_params}"
                  f" ({st.coarse.best_score:.4f}) -> fine"
                  f" {st.fine.best_params} ({st.fine.best_score:.4f})")

        fitted = res.fitted
        shaped = starhead.apply_ops(base, starhead.make_ops(
            base, {g: to_spec(g, v) for g, v in fitted.items()}))
        cap = sim.capture(shaped)
        _V, disp = sim_capture.check_capture(cap)
        final_angles = starhead.achieved_angles(base, shaped, cap)
        final_err = pose_target.angle_error(final_angles, targets)
        jlog(kind="final", fitted={g: list(v) for g, v in fitted.items()},
             angles=final_angles, error=final_err, disp=disp)

    # ---- verdict ----
    per_group = {}
    all_ok = True
    for grp in starhead.GROUPS:
        gap = abs(final_angles[grp] - targets[grp])
        if mode == "x" and grp == "back":
            bound = crimp["best"]["gap_to_target"] + crimp["angle_tol"]
            src = "crimp grid"
        else:
            bound = best_ach[grp]["gap_to_target"] + angle_tol[grp]
            src = "reverse sweep"
        ok = gap <= bound
        per_group[grp] = {"achieved": final_angles[grp],
                          "target": targets[grp], "gap": gap,
                          "bound": bound, "bound_source": src, "ok": ok}
        all_ok = all_ok and ok
    improved = final_err < baseline_err

    verdict = {"mode": mode,
               "fitted": {g: list(v) for g, v in fitted.items()},
               "stages": stage_rows,
               "baseline_error": baseline_err,
               "final_error": final_err, "final_angles": final_angles,
               "per_group": per_group, "improved": improved}
    if mode == "r2":
        verdict["seed_error"] = seed_err
        verdict["seed_angles"] = seed_angles
        verdict["improved_vs_seed"] = final_err < seed_err
        # the reverse-only ceiling the crimp gate must beat: the better
        # of (single-op sweep best, r2's in-context final) for back
        verdict["back_ceiling"] = max(best_ach["back"]["angle"],
                                      final_angles["back"])
        verdict["passed"] = None       # gate 1 is informational
    else:
        verdict["f2_star"] = f2_star
        verdict["r2_final_error"] = r2["final_error"]
        verdict["beats_r2"] = final_err < r2["final_error"]
        verdict["passed"] = bool(all_ok and improved and
                                 verdict["beats_r2"])
    json.dump(verdict, open(out_json, "w"), indent=2)
    jlog(kind="verdict", **verdict)

    print("\n--- " + ("R2 CEILING (gate 1)" if mode == "r2"
                      else "FIT X VERDICT (gate 3)") + " ---")
    for grp, r in per_group.items():
        print(f"  {grp}: achieved {r['achieved']:.4f} vs target"
              f" {r['target']:.4f} (gap {r['gap']:.4f}, bound"
              f" {r['bound']:.4f}, {r['bound_source']})"
              f" {'OK' if r['ok'] else 'MISS'}")
    print(f"  total error {final_err:.4f} vs baseline {baseline_err:.4f}"
          f" ({'improved' if improved else 'NOT improved'})")
    if mode == "r2":
        print(f"  vs slice-3 seed {seed_err:.4f}: "
              + ("improved" if verdict["improved_vs_seed"]
                 else "NOT improved"))
        print(f"  reverse-only back ceiling pinned:"
              f" {verdict['back_ceiling']:.4f}")
        print("  HONEST NOTE: absolute gaps to the fox targets remain"
              " large; a relative-bound OK is not a posed fox.")
        return 0
    print(f"  vs r2 final {r2['final_error']:.4f}: "
          + ("beats r2" if verdict["beats_r2"] else "does NOT beat r2"))
    print("FIT " + ("PASS" if verdict["passed"] else "FAIL"))
    return 0 if verdict["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else ""))
```

- [ ] **Step 2: Commit the rebuild (before the long run, so the run is against committed code)**

```bash
git add mcp_harness/probe_pose_fit.py
git commit -m "feat(b5-slice4): probe_pose_fit -> coordinate_descent driver with r2 (reverse resume) + x (crimp back) modes"
```

- [ ] **Step 3: Run gate 1 (HEADED sim; ~103 captures ~ 70 min)**

```bash
nohup .venv/bin/python probe_pose_fit.py r2 > probe_pose_fit_r2.out.log 2>&1 &
```

Poll `probe_pose_fit_r2.out.log` until the `--- R2 CEILING (gate 1) ---` block prints (check every few minutes; eval lines should tick ~every 40 s — a silent log for >10 min means a wedged sim: check the window, kill and rerun once before reporting a blocker).

- [ ] **Step 4: Hand-check + record gate-1 outcome**

Expected shape (numbers are measured, not predicted):
- `seed (slice-3 fitted) ... error` ≈ 276.2 (within capture drift of the handoff's 276.2131);
- two stage lines (front, back), then final angles/error;
- `back_ceiling` printed — this is the number the crimp gate must beat by 10;
- exit code 0. Record final error, per-group gaps, and the ceiling in the SDD ledger; gate 1 NEVER halts the slice.

- [ ] **Step 5: Commit ledger note (no probe outputs)**

```bash
git add .superpowers/sdd/progress.md
git commit -m "probe(b5-slice4): gate-1 r2 run recorded [reverse-only ceiling pinned; measured numbers in ledger]"
```

---

### Task 8: `probe_crimp_range.py` + run gate 2 (the crimp HALT gate)

**Files:**
- Create: `mcp_harness/probe_crimp_range.py`
- Run artifacts (UNCOMMITTED): `mcp_harness/probe_crimp_range.out.{json,log}`

**Interfaces:**
- Consumes: `starhead.make_ops` crimp spec (Task 5), `pose_search.grid_step_tol` (Task 2), `probe_angle_range.out.json` (Task 6), `probe_pose_fit_r2.out.json` (Task 7).
- Produces: `probe_crimp_range.out.json` with keys `verdict` ("PROCEED"/"HALT"), `f2_star`, `best{theta,f2,angle,gap_to_target}`, `angle_tol`, `ceiling`, `extension`, `f2_sensitivity`, `cells` — consumed by Task 9's x run.

- [ ] **Step 1: Create `mcp_harness/probe_crimp_range.py`:**

```python
"""B5 slice-4 de-risk probe (gate 2): does a CRIMP measurably extend the
back group's reachable angle past the reverse-only ceiling?

Back group only, other groups unshaped, first fold fraction fixed at 0.5
(the range-sweep convention). Grid: theta in {60, 75, 105, 142.5, 170}
(no 90 -- guarded silent mis-target) x fraction2 in {0.35, 0.5, 0.65} =
15 captures. Best = MAXIMUM back achieved angle (== closest to target:
the fox back target sits far above the reachable range).

Ceiling = max(reverse-sweep back best-achievable angle, r2 final back
achieved). PROCEED iff best crimp angle >= ceiling + MARGIN (10.0 deg,
user-pinned: with ~76 deg of gap, a 3-deg extension is measurable but
not worth building the stage-3 fit for). HALT ends the slice as a
documented outcome. Also pins f2* (best cell's f2) and back's
crimp-grid angle_tol for the stage-3 fit's PASS bound.

Run (HEADED sim -- a window opens; ~15 captures ~ 10 min):
  cd mcp_harness && nohup .venv/bin/python probe_crimp_range.py \
      > probe_crimp_range.out.log 2>&1 &
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pose_search                  # noqa: E402
import pose_target                  # noqa: E402
import sim_capture                  # noqa: E402
import starhead                     # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
RANGE_JSON = os.path.join(_HERE, "probe_angle_range.out.json")
R2_JSON = os.path.join(_HERE, "probe_pose_fit_r2.out.json")
OUT = os.path.join(_HERE, "probe_crimp_range.out.json")

CRIMP_THETAS = [60.0, 75.0, 105.0, 142.5, 170.0]
F2S = [0.35, 0.5, 0.65]
FRACTION = 0.5
MARGIN = 10.0


def _halt(out, reason):
    out["verdict"] = "HALT"
    out["reason"] = reason
    json.dump(out, open(OUT, "w"), indent=2)
    print(f"HALT: {reason}")
    return 3


def main() -> int:
    for path, what in ((RANGE_JSON, "probe_angle_range.py"),
                       (R2_JSON, "probe_pose_fit.py r2")):
        if not os.path.exists(path):
            print(f"missing {path} -- run {what} first")
            return 2
    rng = json.load(open(RANGE_JSON))
    if rng.get("verdict") != "PROCEED":
        print(f"probe_angle_range verdict was {rng.get('verdict')} -- halt")
        return 2
    r2 = json.load(open(R2_JSON))
    target = rng["fox_targets"]["back"]
    sweep_best = rng["best_achievable"]["back"]["angle"]
    r2_back = r2["final_angles"]["back"]
    ceiling = max(sweep_best, r2_back)
    print(f"back target {target:.4f}; reverse-only ceiling {ceiling:.4f}"
          f" (sweep best {sweep_best:.4f}, r2 final {r2_back:.4f});"
          f" gate: best crimp >= ceiling + {MARGIN}")

    base = starhead.winner_base()
    cells = []
    with sim_capture.SimSession() as sim:
        for theta in CRIMP_THETAS:
            for f2 in F2S:
                cell = {"theta": theta, "f2": f2, "angle": None}
                try:
                    ops = starhead.make_ops(
                        base, {"back": ("crimp", theta, FRACTION, f2)})
                    shaped = starhead.apply_ops(base, ops)
                    cap = sim.capture(shaped)
                    _V, disp = sim_capture.check_capture(cap)
                    ang = starhead.achieved_angles(base, shaped,
                                                   cap)["back"]
                    cell.update(angle=ang, disp=disp)
                    print(f"  theta={theta} f2={f2}: back {ang:.4f}"
                          f" disp {disp:.4f}", flush=True)
                except (sim_capture.CaptureError,
                        pose_target.PoseTargetError) as exc:
                    cell["error"] = str(exc)
                    print(f"  theta={theta} f2={f2}: FAILED ({exc})",
                          flush=True)
                cells.append(cell)

    out = {"winner_bh": rng["winner_bh"], "target_back": target,
           "ceiling": ceiling, "ceiling_parts": [sweep_best, r2_back],
           "margin": MARGIN, "fraction": FRACTION, "cells": cells}
    good = [c for c in cells if c["angle"] is not None]
    if not good:
        return _halt(out, "every crimp cell failed (refused/flat/NaN)")
    best = max(good, key=lambda c: c["angle"])
    # tolerance on the best cell's f2 COLUMN (theta-grid-adjacent, same
    # rule + fallback as the fixed probe_angle_range): stage 3's back
    # bound comes from THIS grid, so its tol must too
    col = [c for c in cells if c["f2"] == best["f2"]]
    tol = pose_search.grid_step_tol([c["angle"] for c in col],
                                    col.index(best))
    if tol is None:
        return _halt(out, "no theta-grid-adjacent successful pair in the"
                          " best cell's f2 column to measure angle_tol")
    at_best_theta = [c["angle"] for c in cells
                     if c["theta"] == best["theta"]
                     and c["angle"] is not None]
    extension = best["angle"] - ceiling
    out.update(best={"theta": best["theta"], "f2": best["f2"],
                     "angle": best["angle"],
                     "gap_to_target": abs(best["angle"] - target)},
               f2_star=best["f2"], angle_tol=tol,
               f2_sensitivity=max(at_best_theta) - min(at_best_theta),
               extension=extension)
    out["verdict"] = "PROCEED" if extension >= MARGIN else "HALT"
    json.dump(out, open(OUT, "w"), indent=2)

    print("\n--- CRIMP GATE (gate 2) ---")
    print(f"  best crimp: back {best['angle']:.4f} @ theta="
          f"{best['theta']} f2={best['f2']} (gap to target"
          f" {out['best']['gap_to_target']:.4f}, tol {tol:.4f})")
    print(f"  f2 sensitivity at best theta:"
          f" {out['f2_sensitivity']:.4f} deg")
    print(f"  extension past reverse-only ceiling: {extension:.4f} deg"
          f" (need >= {MARGIN})")
    print(out["verdict"])
    return 0 if out["verdict"] == "PROCEED" else 3


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Commit the probe (before running)**

```bash
git add mcp_harness/probe_crimp_range.py
git commit -m "probe(b5-slice4): crimp range gate -- back group, theta x f2 grid, >=10 deg past reverse ceiling else HALT"
```

- [ ] **Step 3: Run gate 2 (HEADED sim; ~15 captures ~ 10 min)**

```bash
nohup .venv/bin/python probe_crimp_range.py > probe_crimp_range.out.log 2>&1 &
```

Poll `probe_crimp_range.out.log` until `--- CRIMP GATE (gate 2) ---` prints.

- [ ] **Step 4: Hand-check + record gate-2 outcome**

Hand-check the printed map: expect some flat-equilibrium/refused holes (recorded, not fatal); the ceiling line must show the same numbers Task 7 pinned. Record best cell, extension, f2_star, tol, verdict in the SDD ledger.
- **PROCEED** → continue to Task 9.
- **HALT** → skip Task 9; Task 10 documents the halt (like slice 2's) with the measured extension. This is a successful slice outcome — do not soften it.

- [ ] **Step 5: Commit ledger note**

```bash
git add .superpowers/sdd/progress.md
git commit -m "probe(b5-slice4): gate-2 crimp range run recorded [verdict + measured extension in ledger]"
```

---

### Task 9: run gate 3 (extended fit, x mode) — ONLY if gate 2 PROCEEDed

**Files:**
- Run artifacts (UNCOMMITTED): `mcp_harness/probe_pose_fit_x.out.{json,jsonl,log}`

**Interfaces:**
- Consumes: everything — `probe_pose_fit.py x` (Task 7 code) reading Task 6 + Task 7 + Task 8 outputs.
- Produces: `probe_pose_fit_x.out.json` with `passed`, `per_group`, `final_error`, `beats_r2` — the slice's headline verdict for Task 10.

- [ ] **Step 1: Run gate 3 (HEADED sim; ~252 captures ~ 2.6 h — overnight-style run)**

```bash
nohup .venv/bin/python probe_pose_fit.py x > probe_pose_fit_x.out.log 2>&1 &
```

Poll `probe_pose_fit_x.out.log` every ~15 min until `--- FIT X VERDICT (gate 3) ---` prints. Eval lines tick ~every 40 s; expect inf holes (flat equilibrium, refused wedges, and up to one theta=90 refine cell per back stage — all normal). A silent log >15 min: check the sim window, kill and rerun once before reporting a blocker.

- [ ] **Step 2: Hand-check + record gate-3 verdict**

From the printed verdict block, record in the SDD ledger: per-group achieved/gap/bound/OK-MISS (back's bound_source must read "crimp grid"), total error vs baseline, vs r2 final, and `FIT PASS` or `FIT FAIL`. Verify arithmetic by hand for one group (gap = |achieved − target|). Exit 0 = PASS, 1 = FAIL — either is a valid slice outcome; report it exactly.

- [ ] **Step 3: Commit ledger note**

```bash
git add .superpowers/sdd/progress.md
git commit -m "probe(b5-slice4): gate-3 extended fit run recorded [measured verdict in ledger]"
```

---

### Task 10: outcome documentation + review package

**Files:**
- Modify: `docs/superpowers/specs/2026-07-09-b5-pose-fit-slice4-design.md` (Status line only)
- Create: `docs/superpowers/2026-07-09-handoff-b5-slice4-outcome.md`
- Create: `.superpowers/sdd/review-6a880ca..HEAD.diff`

- [ ] **Step 1: Update the spec's Status line** to the measured outcome, one of:
  - `**Status:** IMPLEMENTED — FIT PASS/FAIL on star(b=0.95, h=0.40) (<one-line measured summary>) (handoff: docs/superpowers/2026-07-09-handoff-b5-slice4-outcome.md)`
  - `**Status:** HALTED at gate 2 (crimp extension <measured> deg < 10) (handoff: ...)` — mirror the slice-2/3 banner style.

- [ ] **Step 2: Write the handoff** at `docs/superpowers/2026-07-09-handoff-b5-slice4-outcome.md`, mirroring the slice-3 handoff's structure exactly (sections: What shipped / Findings / Slice 5 entry point / Gotchas carried forward). It MUST contain, verbatim from the probe outputs: the r2 ceiling numbers, the crimp gate's best cell + extension + verdict, the gate-3 per-group table + PASS/FAIL (if run), and every new gotcha discovered. All numbers copied from `.out.json` files, none invented; state plainly which gates were reached.

- [ ] **Step 3: Full suite green (final verification)**

Run: `.venv/bin/python -m pytest tests -q`
Expected: 442 passed / 3 skipped, 0 failed

- [ ] **Step 4: Verify no probe outputs are staged**

Run: `git status --short` — every `*.out.json|jsonl|log` line must show `??` (untracked), never `A `/`M `.

- [ ] **Step 5: Commit docs + build the review package**

```bash
git add docs/superpowers/specs/2026-07-09-b5-pose-fit-slice4-design.md docs/superpowers/2026-07-09-handoff-b5-slice4-outcome.md
git commit -m "docs(b5-slice4): outcome handoff + spec status banner [measured verdict in body]"
cd <repo>
git diff 6a880ca..HEAD > .superpowers/sdd/review-6a880ca..HEAD.diff
```

- [ ] **Step 6: STOP — ask the human before any push/PR** (standing constraint). Present the measured outcome summary and the review diff path; the human merges every PR.

---

## Task flow / conditionality

Tasks 1→8 are strictly sequential (each consumes the previous task's interface or output). Task 9 runs ONLY if Task 8's verdict is PROCEED; on HALT, go straight to Task 10 and document the halt. Task 10 always runs.

## Self-review notes (already applied)

- Spec coverage: gate 0 = Tasks 2/4/6; gate 1 = Task 7; gate 2 = Task 8; gate 3 = Task 9; pure-loop = Task 1; crimp composition = Task 3; make_ops = Task 5; docs = Task 10. All spec sections mapped.
- Type consistency: `coordinate_descent`/`DescentResult`/`grid_step_tol`/`crimp_ops`/`make_ops` spec forms and all `.out.json` keys (`f2_star`, `best.gap_to_target`, `angle_tol`, `final_angles`, `final_error`, `back_ceiling`, `verdict`) are used with identical names in Tasks 6-9.
- The 442 expected suite count = 424 baseline + 18 new tests (5+5+4+4); if a task adds/removes a test, adjust the expectation in Tasks 6/10 accordingly.
