# Packing Layout Choice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every fold computes the mirror-symmetric packing and a materially smaller unmirrored one; when the smaller grid makes the model ≥10% larger the person chooses (app card / `run` prompt, numbers recommend, VLM explains), `fold` decides by rule or `--layout`, and every record carries paper-efficiency metrics.

**Architecture:** The packer gains a deterministic work budget and JSON layout serialisation. A new `pipeline.pack_options` packs both layouts, applies the 10% rule and returns a `PackOptions`; `pipeline.run` takes a `layout` choice and an optional precomputed `PackOptions` instead of walking the ladder itself. `mcp_harness/layout_explain.py` builds the card text and the VLM explanation. The app packs options in a spawned child, pauses at an `awaiting_review` on the `packing` stage carrying the card, and folds the chosen layout from the saved options.

**Tech Stack:** Python 3.14 (pytest), FastAPI app server, React + TypeScript (vitest).

**Spec:** `docs/superpowers/specs/2026-10-16-packing-layout-choice-design.md`

## Global Constraints

* Tests use **only** the 51 artifact trees in `mcp_harness/fixtures/full17_v3_sticks/` (`artifact_trees.authored(roll)` for VLM payloads). **Never** tardigrade / water bear.
* Interpreter: the worktree has no `.venv`. `PY=<repo>/mcp_harness/.venv/bin/python`; pipeline tests run from `mcp_harness/` as `PYTHONPATH=.:tests $PY -m pytest tests/<file> -q`; app tests as `PYTHONPATH=.:tests:../app/server $PY -m pytest ../app/server/tests/<file> -q -p no:cacheprovider`; web tests `cd app/web && npm test`; full suite `make PYTHON=$PY test`.
* Threshold: `GAIN_THRESHOLD = Fraction(11, 10)`; compare exactly (`n_sym >= GAIN_THRESHOLD * n_small`), never with floats. The unmirrored grid cap is `n_sym * 10 // 11`.
* `layout` values: `"auto" | "symmetric" | "smaller"`. `rec["layout"]["reason"]` values: `"rule" | "user" | "flag" | "only_option" | "fallback"`. `n_smaller` values: `int | None | "none_below_cap" | "budget"`. Verdicts: `"ask" | "symmetric" | "only_unmirrored" | "doubled"`.
* When `layout="auto"` and the gain is below threshold, every one of the four output files must stay byte-identical to today's.
* A VLM failure never blocks or fails a fold: fall back to the template explanation.
* The CLI must not reuse one LLM client across two `asyncio.run` loops (the #198 lesson: the SDK silently retries on the closed loop and bills twice) — build a fresh client for the layout explanation.
* Commit messages end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. A tree whose symmetric search finds nothing (crab_3, dog_2, elephant_3, frog_0, spider_2, starfish_0) must fold exactly as today with no question and `reason: "only_option"` — Task 4 pins starfish_0, Task 6 pins its output grid 44.
2. A run reloaded (app restart / page reload) while waiting at the layout card must show the same card and accept a choice — Task 9 pins replay from the event log, Task 8 pins recovery.
3. The large trees with unmeasured unmirrored grids (scorpion ×3, spider ×3, starfish ×3) must not stall: the budget must fire inside `_pocket_solutions`, which never yields for scorpion_0 — Task 5 pins scorpion_0 finishing within the budget.
4. A choice of "smaller" that fails downstream in the app must offer the card again, not a dead Retry — Task 8 pins it.
5. Explanation text from the VLM is untrusted prose shown in the UI — it is rendered as text, never HTML (Task 10), and capped at 600 characters (Task 3b).

---

### Task 1: Deterministic work budget in the packer

**Files:**
- Modify: `mcp_harness/pleatwright/pack.py` (new helpers near `PackError`, ticks in `_pocket_solutions` and `candidates`)
- Modify: `mcp_harness/pleatwright/nest.py` (ticks in `_Search.fill`, `_Search.heights`, `candidates`)
- Test: `mcp_harness/tests/test_layout_choice.py` (new)

**Interfaces:**
- Produces: `pack.BudgetExhausted(Exception)`; `pack.work_budget(limit: int | None)` — a context manager (a `contextvars.ContextVar` holding `[used, limit]`; `None` = unlimited, also the state outside any `with`); `pack.tick(n: int = 1) -> None` raises `BudgetExhausted` when `used > limit`; `pack.work_used() -> int` (ticks spent in the current budget, 0 outside).

- [ ] **Step 1: Write the failing tests**

```python
def test_budget_one_tick_exhausts_on_the_unmirrored_dolphin():
    con = _con("dolphin_0")
    with pytest.raises(PK.BudgetExhausted):
        with PK.work_budget(1):
            next(PK.candidates(con, symmetric=False, N_max=45))

def test_no_budget_changes_nothing():
    con = _con("dolphin_0")
    a = next(PK.candidates(con, symmetric=True, N_max=64))
    with PK.work_budget(None):
        b = next(PK.candidates(con, symmetric=True, N_max=64))
    assert (a.N, [r.rect for r in a.regions]) == (b.N, [r.rect for r in b.regions]) and a.N == 50

def test_ticks_are_deterministic():
    con = _con("dolphin_0")
    used = []
    for _ in range(2):
        with PK.work_budget(10**9):
            next(PK.candidates(con, symmetric=False, N_max=45))
            used.append(PK.work_used())
    assert used[0] == used[1] > 0
```

`_con(roll)` loads `fixtures/full17_v3_sticks/<roll>.json` via `stick.load_roll(path, 1.0)` and `stick.contract`.

- [ ] **Step 2: Run to verify they fail** — `PYTHONPATH=.:tests $PY -m pytest tests/test_layout_choice.py -q` → FAIL (`AttributeError: ... work_budget`).
- [ ] **Step 3: Implement.** One `tick()` per `assign` iteration in `_pocket_solutions` (before the `len(set(assign))` filter, so filtered assignments also count), per yielded combo in `candidates`, and per loop iteration in `nest._Search.fill` / `heights`. `BudgetExhausted` propagates out of the generators.
- [ ] **Step 4: Run** the new tests plus `tests/test_pack_chain.py tests/test_nest.py` → PASS.
- [ ] **Step 5: Commit** — `git commit -m "pack: deterministic work budget for the packer search"`.

### Task 2: Layout ↔ JSON

**Files:**
- Modify: `mcp_harness/pleatwright/pack.py`
- Test: `mcp_harness/tests/test_layout_choice.py`

**Interfaces:**
- Produces: `pack.layout_to_dict(lay: Layout) -> dict` (JSON-safe) and `pack.layout_from_dict(d: dict) -> Layout` (tuples restored for `Region.rect`, every entry of `Region.more`, and pocket rects).

- [ ] **Step 1: Failing test** — for dolphin_0 at both `symmetric=True` and `False`: `lay2 = PK.layout_from_dict(json.loads(json.dumps(PK.layout_to_dict(lay))))`; assert `B.build(lay2, con, sigma).creases == B.build(lay, con, sigma).creases` and `lay2.N == lay.N`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** with `dataclasses.asdict` plus explicit tuple restoration.
- [ ] **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** — `"pack: serialise layouts to JSON"`.

### Task 3: Efficiency metrics

**Files:**
- Create: `mcp_harness/pleatwright/efficiency.py`
- Test: `mcp_harness/tests/test_layout_choice.py`

**Interfaces:**
- Produces: `efficiency.metrics(lay: Layout, con: Contracted, base: Base, scale: float) -> dict` with keys `grid, grid_init, perimeter_bound, n_over_bound, scale, slack_fraction, flap_expansion_max, flap_expansion_median, mean_layers, creases`. Definitions are spec §6; the reference implementation is `docs/superpowers/evidence/2026-10-16-layout-choice/bp_efficiency_probe.py` (`clipped_ball`, `flap_metrics`). `perimeter_bound = ceil(T/2)`, T = Σ length of every chain in `con`; `scale = scale / N`; `creases = len(base.creases)`; floats rounded to 4 places.

- [ ] **Step 1: Failing test** — values from the probe (`bp_eff.jsonl`), symmetric layouts:

```python
@pytest.mark.parametrize("roll,N,pb,slack,layers,exp_max,exp_med,creases", [
    ("dolphin_0", 50, 29, 0.5916, 43.27, 5.556, 2.5, 2656),
    ("bird_1",    40, 32, 0.2887, 23.27, 3.0, 1.4185, 1768),
])
def test_metrics_match_the_baseline_probe(roll, N, pb, slack, layers, exp_max, exp_med, creases):
    m = _metrics_for_first_symmetric(roll)
    assert (m["grid"], m["perimeter_bound"], m["creases"]) == (N, pb, creases)
    assert m["slack_fraction"] == pytest.approx(slack, abs=1e-4)
    assert m["mean_layers"] == pytest.approx(layers, abs=0.01)
    assert m["flap_expansion_max"] == pytest.approx(exp_max, abs=1e-3)
    assert m["flap_expansion_median"] == pytest.approx(exp_med, abs=1e-3)
    assert m["scale"] == pytest.approx(1 / N)
```

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** — `"efficiency: paper-efficiency metrics for a packed base"`.

### Task 3b: Card text and VLM explanation

**Files:**
- Create: `mcp_harness/layout_explain.py`
- Test: `mcp_harness/tests/test_layout_explain.py`

**Interfaces:**
- Consumes: the plain dict `PackOptions.summary()` returns (Task 4): `{"verdict", "gain", "n_smaller", "symmetric": {"grid", "metrics"}|None, "smaller": {"grid", "metrics"}|None, "recommended": "smaller"|"symmetric"}`.
- Produces: `card(summary: dict) -> dict` = `{"question": str, "options": [{"id": "smaller"|"symmetric", "label": str, "grid": int, "recommended": bool, "pros": [str], "cons": [str]}]}` (recommended first; pros/cons are numbers-only templates: size gain `gain`× as "1.56× larger", crease counts, slack, mean layers, mirror symmetry); `template_explanation(summary: dict, subject: str, pairs: list) -> str`; `async explain(client, summary: dict, subject: str, pairs: list) -> str` — one forced `submit_explanation` tool turn (`{"explanation": str}`), shaped like `subject_rewrite.rewrite`; system prompt states the recommendation is fixed and asks for 2–4 sentences on the trade-off for this subject; any exception, missing tool call, or empty text → `template_explanation(...)`; result stripped and capped at 600 chars.

- [ ] **Step 1: Failing tests** (`FakeClient` from `test_gated_pipeline`):
  - `test_card_recommends_first_with_the_gain` — dolphin-like summary (gain 1.5625, grids 50/32) → `options[0]["id"] == "smaller"`, `options[0]["recommended"]`, `"1.56×" in " ".join(options[0]["pros"])`.
  - `test_explain_uses_the_tool_text` — `FakeClient([{"explanation": "Dolphins read fine either way."}])` → returns that text; the user message contains `"50"`, `"32"` and `"1.56"`.
  - `test_explain_falls_back_on_a_refusal` — `FakeClient([None])` → equals `template_explanation(...)`.
  - `test_explain_caps_length` — 2000-char payload → `len(result) <= 600`.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** — `"layout_explain: card text and VLM explanation for the layout choice"`.

### Task 4: `pack_options` and the rule

**Files:**
- Modify: `mcp_harness/pleatwright/pipeline.py`
- Test: `mcp_harness/tests/test_layout_choice.py`

**Interfaces:**
- Consumes: Tasks 1–3.
- Produces, in `pipeline`:
  - constants `GAIN_THRESHOLD = Fraction(11, 10)`, `SMALLER_WORK_BUDGET: int` (placeholder `10**12` until Task 5), `MAX_CANDIDATES = 400`.
  - `@dataclass Option: name: str ("symmetric"|"smaller"|"doubled"), rung: str, scale: float, layout: Layout, base: Base, metrics: dict`.
  - `@dataclass PackOptions: sf, con, sigma, symmetric: Option|None, smaller: Option|None, doubled: Option|None, n_smaller: int|None|str, gain: Fraction|None, verdict: str`, plus `recommended -> str|None` (`"smaller"` iff verdict `ask`), `option(name) -> Option|None`, `summary() -> dict` (JSON-safe, shape in Task 3b; `gain` as `round(float, 4)`).
  - `pack_options(tree: str, *, scale: float = 1.0, work_budget: int | None = None) -> PackOptions` (`None` → `SMALLER_WORK_BUDGET`). Symmetric search as today (`N_max = max(2G, G+60)`, first base without errors, ≤ `MAX_CANDIDATES` tried). If it succeeds: unmirrored search with `N_max = n_sym*10//11` under `pack.work_budget(...)`; `BudgetExhausted` → `n_smaller = "budget"`; empty → `"none_below_cap"`. If symmetric fails: unmirrored search exactly as today's rung 2 (no cap, no budget); then the doubled rung as today. Verdict per spec §4.
  - `save_options(opts: PackOptions, directory: str) -> list[str]` writes `options.json` (`summary()` + `layout_to_dict` of each option) and `symmetric_packing_cp.svg` / `smaller_packing_cp.svg` (same rendering `_run` uses for `packing_cp.svg`), returning the written paths; `load_options(tree: str, directory: str) -> PackOptions` rebuilds bases with `B.build` (no search).

- [ ] **Step 1: Failing tests**

```python
def test_dolphin_asks():
    o = PL.pack_options("dolphin_0")
    assert (o.verdict, o.symmetric.layout.N, o.smaller.layout.N) == ("ask", 50, 32)
    assert o.gain == Fraction(50, 32) and o.recommended == "smaller"

def test_bird_keeps_symmetry_without_asking():
    o = PL.pack_options("bird_1")          # unmirrored 38 > cap 36
    assert (o.verdict, o.n_smaller, o.smaller) == ("symmetric", "none_below_cap", None)

def test_lizard_2_sits_exactly_on_the_threshold():
    o = PL.pack_options("lizard_2")        # 44 / 40 == 1.10
    assert o.verdict == "ask"

def test_starfish_has_only_the_unmirrored_layout():
    o = PL.pack_options("starfish_0")
    assert (o.verdict, o.symmetric, o.smaller.layout.N) == ("only_unmirrored", None, 44)

def test_budget_exhaustion_is_recorded():
    o = PL.pack_options("dolphin_0", work_budget=1)
    assert (o.verdict, o.n_smaller) == ("symmetric", "budget")

def test_saved_options_reload_without_searching(tmp_path, monkeypatch):
    o = PL.pack_options("dolphin_0")
    PL.save_options(o, str(tmp_path))
    monkeypatch.setattr(PL.PK, "candidates", lambda *a, **k: pytest.fail("searched"))
    r = PL.load_options("dolphin_0", str(tmp_path))
    assert r.summary() == o.summary() and r.smaller.base.creases == o.smaller.base.creases
```

- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** — `"pipeline: pack_options packs both layouts and applies the 10% rule"`.

### Task 5: Calibrate `SMALLER_WORK_BUDGET`

**Files:**
- Modify: `mcp_harness/pleatwright/pipeline.py` (the constant, with a comment citing the measurement)
- Create: `docs/superpowers/evidence/2026-10-16-layout-choice/README.md` (budget section)
- Test: `mcp_harness/tests/test_layout_choice.py`

- [ ] **Step 1: Measure.** For octopus_2 (unmirrored N 60 within cap 60) record ticks (`PK.work_used()`) and seconds of the capped unmirrored search under `work_budget(10**12)`. For scorpion_0, time the capped unmirrored search under budgets 10⁶, 10⁷, 10⁸ (each stops with `BudgetExhausted`) to get its ticks per second. Set `SMALLER_WORK_BUDGET = ceil(1.5 × octopus_2's ticks)` rounded up to 2 significant figures. If scorpion_0's wall time at that budget exceeds 180 s, stop and report the numbers before going further.
- [ ] **Step 2: Write tests** — `test_octopus_2_fits_the_budget` (`pack_options("octopus_2").verdict == "ask"` and `smaller.layout.N == 60`) and `test_scorpion_0_stops_within_the_budget` (`pack_options("scorpion_0")` returns, `n_smaller` is `"budget"`, `"none_below_cap"` or an int). Mark both `@pytest.mark.slow` only if the repo already has that marker; otherwise leave them in the default run.
- [ ] **Step 3: Run** → PASS.
- [ ] **Step 4: Record** ticks, seconds and the chosen constant in the evidence README.
- [ ] **Step 5: Commit** — `"pipeline: calibrate the unmirrored search budget"`.

### Task 6: `run` folds the chosen layout; records and fallback

**Files:**
- Modify: `mcp_harness/pleatwright/pipeline.py` (`run`, `_run`, `main`)
- Test: `mcp_harness/tests/test_layout_choice.py`

**Interfaces:**
- Produces: `run(tree, out_dir, *, scale=1.0, certify_global=True, max_candidates=400, verbose=True, orchestrate=False, orchestrate_k=3, on_stage=None, layout: str = "auto", chosen_by: str = "flag", options: PackOptions | None = None) -> dict` (keywords spelled out in both `run` and `_run`). `options=None` → `pack_options(tree, scale=scale)`. Choice: `auto` → `smaller` if verdict `ask` (reason `"rule"`), symmetric if verdict `symmetric` (`"rule"`), the only option for `only_unmirrored`/`doubled` (`"only_option"`); an explicit `layout` uses that option with reason `chosen_by` (`"flag"` or `"user"`), falling back to the existing option with reason `"only_option"` when it does not exist. `rec["layout"] = {"chosen", "reason", "n_symmetric", "n_smaller", "gain", "threshold": 1.1}` (`gain` as float or None); `rec["efficiency"] = chosen.metrics`; `packing_rung`, `scale`, `grid_size`, `pack_tried` keep today's meaning. **Fallback:** if `layout == "auto"`, the chosen option is `smaller`, and solving or shaping raises, remove the partial `<Subject>_<N>` folder and fold the symmetric option instead with `reason: "fallback"` and `rec["layout"]["fallback_error"] = "<Type>: <msg>"`. `main()` gains `--layout {auto,symmetric,smaller}`. The `packing` `on_stage` info gains `layout=rec["layout"]` and `efficiency=rec["efficiency"]` (spec §8.1: the app's packing summary shows them; Task 10 renders them).

- [ ] **Step 1: Failing tests** (all with `certify_global=False`, `verbose=False`, `tmp_path`):
  - `test_auto_takes_the_smaller_dolphin` → `grid_size == 32`, `layout["reason"] == "rule"`, folder name ends `_32`, `rec["efficiency"]["grid"] == 32`.
  - `test_flag_keeps_the_symmetric_dolphin` → `layout="symmetric"` gives `grid_size == 50`, reason `"flag"`.
  - `test_auto_bird_keeps_the_old_layout` → `grid_size == 40`, `packing_rung == "symmetric"`, `layout == {"chosen": "symmetric", "reason": "rule", "n_symmetric": 40, "n_smaller": "none_below_cap", "gain": None, "threshold": 1.1}` (byte identity is checked corpus-wide in Task 11).
  - `test_starfish_only_option` → `grid_size == 44`, reason `"only_option"`.
  - `test_failed_smaller_falls_back_to_symmetric` → monkeypatch `PL.SV.solve` to raise `RuntimeError("boom")` when `base.layout.N == 32`, else call the original; `grid_size == 50`, reason `"fallback"`, `fallback_error == "RuntimeError: boom"`, and no `*_32` folder remains under `tmp_path`.
  - `test_precomputed_options_are_used` → pass `options=PL.pack_options("dolphin_0")` and monkeypatch `PK.candidates` to fail if called.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** — replace the ladder loop in `_run` with the choice above; keep every downstream stage untouched. **Step 4: Run** the new tests and `tests/test_pleatwright.py tests/test_pipeline_hooks.py` → PASS.
- [ ] **Step 5: Commit** — `"pipeline: fold the chosen layout, record layout and efficiency"`.

### Task 7: CLI — `fold --layout` and the `run` prompt

**Files:**
- Modify: `mcp_harness/pleatwright/__main__.py`
- Test: `mcp_harness/tests/test_cli.py`

**Interfaces:**
- Consumes: `pipeline.pack_options`, `pipeline.run(layout=, chosen_by=, options=)`, `layout_explain.card/explain/template_explanation`.
- Produces: `LAYOUT_PROMPT = "\n[a] accept recommendation   [s] symmetric   [m] smaller   [q] quit: "`; `choose_layout(opts: PackOptions, explanation: str, ask=input) -> str | None` (prints both grids, gain, recommendation, explanation; `a`/`y`/`yes`/`approve` → recommendation, `s`/`symmetric`, `m`/`smaller`, `q`/`quit`/EOF → `None`; anything else re-prompts); `fold(tree_path, out_dir, *, layout="auto", chosen_by="flag", options=None) -> int`; `fold` subparser gets `--layout {auto,symmetric,smaller}` (default `auto`). `main` for `run`: after `author` returns a path, `opts = pipeline.pack_options(path)`; if `opts.verdict == "ask"`: explanation via `asyncio.run(layout_explain.explain(_client(), ...))` with a **fresh** `_client()` (Global Constraints), falling back to `template_explanation` on `ConfigError`; `choose_layout` → `None` exits 1; else `fold(path, out, layout=choice, chosen_by="user", options=opts)`.

- [ ] **Step 1: Failing tests** — `test_fold_layout_flag` (`main(["fold", "dolphin_0", "--out", d, "--layout", "symmetric"])` → exit 0, folder `Dolphin roll 0_50`); `test_choose_layout_accepts_and_overrides` (scripted `ask` returning `"a"` → `"smaller"`; `"s"` → `"symmetric"`; `"x"` then `"m"` → `"smaller"`; `"q"` → `None`; raising `EOFError` → `None`); `test_run_asks_for_the_dolphin_layout(offline)` — like `test_run_produces_the_four_file_model_folder` with the authored tree `authored("dolphin_0")`, the client payloads `[DOLPHIN, {"explanation": "x"}]` (patch `_client` to return a fresh `FakeClient` per call), answers `["a", "m"]` → exit 0 and a `_32` folder.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** `tests/test_cli.py` → PASS.
- [ ] **Step 5: Commit** — `"cli: fold --layout and the run layout prompt"`.

### Task 8: App server — pack options, card, choice

**Files:**
- Modify: `app/server/pleatwright_app/foldproc.py`, `tools.py`, `guided.py`, `api.py`
- Test: `app/server/tests/test_foldproc.py`, `test_tools.py`, `test_guided.py`

**Interfaces:**
- Consumes: `pipeline.pack_options/save_options/load_options/run`, `layout_explain`.
- Produces:
  - `foldproc.PackJob(tree_path: str, out_dir: str)` — same shape as `FoldJob` (spawned child, `start`, `messages`, `cancel`); the child runs `pack_options` + `save_options(opts, <run_dir>/layout)` and sends `("done", None, opts.summary())` or `("failed", "packing", msg)`.
  - `FoldJob(tree_path, out_dir, *, certify_global=True, layout="auto", chosen_by="flag", options_dir: str | None = None)`; with `options_dir` the child passes `options=load_options(tree_path, options_dir)` to `PL.run`.
  - `tools.LAYOUT_DIR = "layout"`; `async tools.pack_and_fold(ctx, *, certify_global=True)` — emits `stage_started packing`, runs `PackJob`; verdict `ask` → `await present_layout(ctx, summary)`; otherwise `await fold(ctx, certify_global=..., layout="auto")` reusing the saved options.
  - `async tools.present_layout(ctx, summary, *, note: str | None = None)` — explanation via `layout_explain.explain(ctx.client, ...)` (template when `ctx.client` is None), saved with the card to `layout/card.json` (reused on re-present, so a reload or retry shows the same text and costs no second VLM call); emits `stage_output` stage `packing` with files `[layout/smaller_packing_cp.svg, layout/symmetric_packing_cp.svg]` and `summary={"layout_choice": card, "explanation": str, "note": note}`, then `awaiting_review` with `stage="packing"`, `can_approve=True`, `round=0`, `card=card`, `explanation=...`, `note=note`.
  - `tools.fold(ctx, *, certify_global=True, layout="auto", chosen_by="flag")` passes `options_dir=<run_dir>/layout` when `layout/options.json` exists. A failed fold whose `layout` was an explicit choice emits `stage_failed ... retry="layout"`.
  - `Manager.approve(rid, model=None, choice: str | None = None)`: at review stage `packing` requires `choice in ("smaller", "symmetric")` (else `Refused("choose the smaller or the symmetric layout")`), logs `user_message` text `"Smaller grid"` / `"Mirror-symmetric"`, runs `T.fold(ctx, certify_global=..., layout=choice, chosen_by="user")`. Tree approval now runs `approve_tree` then `pack_and_fold`. `Manager.retry`: tool `"layout"` → `T.present_layout(ctx, <saved summary>, note="The smaller layout failed: <error>")`; tool `"fold"` → `pack_and_fold`. `Manager.message` at stage `packing` → `Refused`.
  - `api.py`: the `approve` action passes `m.get("choice")` (string or None).
- [ ] **Step 1: Failing tests**
  - `test_foldproc`: `PackJob` on `authored("dolphin_0")`'s tree file → `done` summary `verdict == "ask"`, `layout/options.json` and both SVGs exist.
  - `test_guided`: `test_a_dolphin_run_stops_at_the_layout_card(offline)` — `LoopRecordingClient([DOLPHIN, DOLPHIN, {"explanation": "e"}])`, approve the mesh, then the tree → `phase(log) == {"phase": "review", "stage": "packing", "can_approve": True}`, `log.last["card"]["options"][0]["id"] == "smaller"`; `await m.approve(rid, choice="smaller")` → `run_finished` with `grid == 32`; all VLM calls on one loop.
  - `test_approve_without_a_choice_is_refused_at_the_card(offline)`.
  - `test_symmetric_choice_folds_at_50(offline)`.
  - `test_a_failed_smaller_fold_retries_back_to_the_card(offline, monkeypatch)` — after the card, monkeypatch `pleatwright_app.tools.fold` with a fake that emits `stage_failed` (stage `solve`, reason `error`, `error="RuntimeError: boom"`, `retry="layout"`) and raises `ToolFailed`; `m.approve(rid, choice="smaller")`, then `m.retry(rid)` → last event `awaiting_review` stage `packing` with `note == "The smaller layout failed: RuntimeError: boom"`, and the client saw no second explanation call. A separate `test_tools` test drives the real `tools.fold` failure path and asserts `retry == "layout"` for an explicit choice and `"fold"` for `auto`.
  - `test_recover_keeps_a_run_paused_at_the_card(offline)` — after the card, a new `Manager` on the same store `recover()`s and `phase` is still the packing review.
  - The existing `test_a_whole_guided_run` (bird_1, gain 1.05) passes unchanged: no card, `len(client.calls) == 2`.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement.** **Step 4: Run** `make PYTHON=$PY test-app` → PASS.
- [ ] **Step 5: Commit** — `"app: pack both layouts and ask at the packing stage"`.

### Task 9: Web store — the card in the run view

**Files:**
- Modify: `app/web/src/types.ts`, `app/web/src/runStore.ts`
- Test: `app/web/src/runStore.test.ts`

**Interfaces:**
- Produces: `types.LayoutCard = { question: string; options: { id: "smaller" | "symmetric"; label: string; grid: number; recommended: boolean; pros: string[]; cons: string[] }[] }`; `RunView.review` gains optional `card?: LayoutCard; explanation?: string; note?: string | null` filled from the `awaiting_review` event; `reviewCopy("packing")` returns `approve: "Choose a layout"`; `sizeRatio(nA: number, nB: number): number` (`nB / nA`, the folded-size ratio of grid A against grid B) exported from `runStore.ts`.
- [ ] **Step 1: Failing tests** — reducing a dolphin event sequence (hand-write `__fixtures__/dolphin_layout.events.jsonl`: `run_created`, the tree `stage_output`, `stage_started packing`, the `packing` `stage_output` with `summary.layout_choice`, and the `awaiting_review` copied from a Task 8 test run's log) gives `review.stage === "packing"`, `review.card.options[0].id === "smaller"`, `stages.packing === "waiting"`; replaying the same events from scratch gives an equal view (reload); `sizeRatio(32, 50) === 1.5625`.
- [ ] **Step 2: Run** `cd app/web && npm test` → FAIL. **Step 3: Implement.** **Step 4: Run** → PASS.
- [ ] **Step 5: Commit** — `"web: carry the layout card in the run view"`.

### Task 10: Web UI — card in the chat, side-by-side in the viewer

**Files:**
- Create: `app/web/src/components/LayoutCard.tsx`, `app/web/src/components/LayoutCompare.tsx`
- Modify: `app/web/src/components/Chat.tsx`, `app/web/src/components/Viewer.tsx`, `app/web/src/styles.css`

**Interfaces:**
- Consumes: Task 9's `review.card/explanation/note`, `sizeRatio`.
- Produces: `LayoutCard({ card, explanation, note, onChoose })` — the question, one button-card per option (recommended first, labelled "(Recommended)"), grid, pros/cons, the explanation as plain text (React text node, never `dangerouslySetInnerHTML`), the note above it when present; `onChoose(id)` sends `{ type: "approve", choice: id, model }`. In `Chat`, `review.stage === "packing"` renders `LayoutCard` in place of the Approve button and disables the textarea. `LayoutCompare({ runId, output })` renders when `output.summary.layout_choice` is present: the two SVGs side by side via `CPView`, each captioned `"<label>: N × N"`, and two squares sized by `sizeRatio` captioned "Folded size from the same sheet". Layout follows `docs/superpowers/evidence/2026-10-16-layout-choice/layout-choice-mockup.html`. The finished packing stage's chat line (where `runStore.ts` builds per-stage summary text, near the `names` map) shows `grid N · <chosen> (<reason>) · slack <slack_fraction as %> · ~<mean_layers> layers` when `summary.layout` / `summary.efficiency` are present.
- [ ] **Step 1: Build** — `cd app/web && npm run build` → PASS (typecheck).
- [ ] **Step 2: Look at it.** `make app`, run "a dolphin" through to the card (live key) or load the Task 9 fixture run into a runs dir, screenshot the card and viewer in the browser pane at desktop and 375 px widths; check the side-by-side stacks at narrow widths.
- [ ] **Step 3: Click both options** on two runs and confirm the folds finish at 32 and 50.
- [ ] **Step 4: Commit** — `"web: layout choice card and side-by-side packing view"`.

### Task 11: Corpus acceptance, docs

**Files:**
- Modify: `docs/superpowers/evidence/2026-10-16-layout-choice/README.md`, `CLAUDE.md` (§4 `fold` line gains `[--layout auto|symmetric|smaller]`), `app/README.md` (one paragraph on the card)

- [ ] **Step 1: Run** `cd mcp_harness && $PY -m pleatwright.pipeline --out $OUT --record $OUT/records.jsonl` (all 51, `layout=auto`) in the background; expect 51 records, none with `failure`.
- [ ] **Step 2: Byte-compare** every output folder whose `layout.reason` is not `"rule"`-with-`chosen == "smaller"` against `~/Desktop/origami_samples_artifact_trees` (same method as the 2026-10-10 gate) → 0 different.
- [ ] **Step 3: Check the switched trees** — expected at least ant_0 70, ant_2 64, dolphin_0 32, dolphin_1 30, dolphin_2 30, elephant_0 72, lizard_1 38, lizard_2 40, octopus_2 60, octopus_3 56, plus any scorpion/spider/starfish tree the budget now finds. Each is `CERTIFIED` (octopus_2 may be `OVERSIZE+LOCAL_SAT`, as its symmetric layout was) with every solving and shaping vertex flat-foldable. Open each switched tree's `overview.png` and look at it.
- [ ] **Step 4: Run the corpus twice** and diff the `layout` fields → identical (determinism). Record per-tree extra packing seconds; none exceeds ~120 s beyond the 2026-10-06 `pack_secs`.
- [ ] **Step 5: Full suite** — `make PYTHON=$PY test` and `cd app/web && npm test && npm run build` → PASS.
- [ ] **Step 6: Write** the README results table and the doc lines; **commit** — `"docs: layout choice acceptance on the 51 artifact trees"`.
