# Front-Lever Payoff (Phase S) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Sizing note (pinned at kickoff):** tasks carry judgment-bearing prose
> briefs, not verbatim code. Implementers own the how; reviewers verify
> against the pinned gates and the spec
> (`docs/superpowers/specs/2026-07-13-front-lever-payoff-design.md`).

**Goal:** Excite the dog's front-selective flex direction with an applicable op recipe (Wave S0, sim-free instrument pre-gate ranking the menu), then beat the 119.14 whole-pose incumbent by composition (Wave S1, bar ≤ 104 ×3); on S0 failure, answer finite extension of w\* sim-free (escalation probe over the rigid/ closure kernel).

**Architecture:** One new pure library (`pose_pregate.py`: strict-apply → shaped-pattern flex re-analysis → ranked menu with defiant quota), one wave driver (`probe_front_wave.py`: budget ledger, table-mine, S0/S1 capture orchestration reusing the D3 pilot's stack), one conditional escalation probe (`probe_flex_extension.py`: consumes `rigid/kinematics/closure.py`, anchors on degree-4). `rigid_fold.py`, the ide-bridge, the shaping layer, and `rigid/` are untouched.

**Tech Stack:** Python 3 in `mcp_harness/.venv`, numpy only (no new deps), pytest; headed SimSession (`sim_capture.py`) for captures — controller-run only.

## Global Constraints

- Budget: **120 reads = 50 S0 / 50 S1 / 20 shared contingency**; unused S0 rolls into S1; escalation is sim-free (0 reads). A read = one measure-attempt (baselines, ×3 confirms, park retries all count — D3 convention). Hard guard, `BudgetExhausted` on overrun.
- Defiant quota: **ceil(0.15 × wave allocation) = 8** reads' worth of candidates per wave.
- S0 CONFIRM bar (carried): **front ≥ +20° toward the fox target, mean of 3 standalone reads from the unshaped base**; ×3 confirm rule at 20°.
- S1 payoff bar: **best cell ≤ 104 total whole-pose error, ×3, full per-group residual map**; incumbent re-baselined ×3 in-session.
- Pinned anchors: unshaped dog r\* = **1.76272**, D2 captured = **0.904**; dog-squared **dof 3 / rank 35 / creases 38**; coupling reconcile **162 = 114/12/36/0**; degree-4 **first-order dof 2 → finite dof 1**; full suite **592 passed / 4 skipped**.
- **Never re-measure a terminal gate-1 cell** (novelty enforced against `CouplingTable(...).resume_keys()`).
- **Kick trigger:** any symmetric front-pair recipe with verdict `parked` (persistent, 3/3) → HALT the wave, raise kick-hardening as prerequisite. **Bridge trigger:** any need for per-crease fold-angle targets the display pipeline cannot express → HALT and ask.
- **Controller-only for ANY headed-sim run** (subagent-launched sim processes get orphan-killed). Full-suite runs via `nohup ... &` + log-poll, never bare foreground (120 s default timeout).
- Probe outputs (`*.out.json/.jsonl/.log`) and suite logs stay **uncommitted** (not gitignored — never `git add -A`).
- Do NOT modify: `mcp_harness/rigid_fold.py`, `mcp_harness/rigid/`\*, `mcp_harness/shaping*.py`, `web/frontend/public/simulator/js/ide-bridge.js`.
- Test command: `cd mcp_harness && .venv/bin/python -m pytest tests/<file> -q` (targeted); full backend suite ~10 min via nohup.
- Ask before push; human merges the PR.

## Environment preflight (controller, before Task 1 review gates that need the dog fixture)

- [ ] Copy into this worktree (Phase-D lesson m2): `.venv` symlink, `headless_treemaker*.so`, `oriedita/*.jar`, `OrieditaValidator.class`, `web/frontend/dist`, and `cp <repo>/mcp_harness/probe_dog_coupling.out.jsonl mcp_harness/` (read-only source; confirmed present 2026-07-12).
- [ ] Regenerate the flex readout: `cd mcp_harness && .venv/bin/python probe_front_flex.py`; expect exit 0, `r* = 1.76272`, `captured 0.904`, tallies `{scored: 114, refused: 12, parked: 36, error: 0}`. **Any drift → STOP the slice** (spec Gate S0.a(a)).

---

### Task 1: `pose_pregate.py` — the sim-free instrument pre-gate (spec §3, Gate S0.a)

**Files:**
- Create: `mcp_harness/pose_pregate.py`
- Create: `mcp_harness/tests/test_pose_pregate.py`

**Interfaces:**
- Consumes (all existing, do not modify):
  - `pose_base.NamedBase(raw, sq, pose_base.DOG_CONFIG)` — `.apply_strict(ops) -> dict` (shaped fold; raises `pose_base.OpRefused`), `.sites` (`{key: Site(.xy, .axial, .hub, .vid)}`), `.targets`, `.fronts`, `.backs`, `.head`, `.leaf_hub_name`, `.site_op(key, kind, theta, frac)`
  - `rigid_fold.null_space_basis(fold) -> (creases, basis, DofResult)`; `rigid_fold.tip_flex_signatures(fold, creases, basis, tip_vids, hub_of_tip)`; `rigid_fold.front_selectivity(sigs, fronts, backs, head, basis) -> SelectivityResult(.r_star, .w_creases, ...)`; `rigid_fold.FlexInstrumentError`
  - `probe_front_flex.served_dog() -> (raw, sq)`; `probe_front_flex.sq_vertex_index(fold, xy)`
- Produces (later tasks rely on these exact names):
  - `@dataclass PregateResult: recipe_id: str; ops: list[str]; status: str  # "scored" | "refused" | "instrument_error"; dof_shaped: int | None; r_star_shaped: float | None; d2_cos: float | None; note: str | None; shaped: dict | None  # the strict-applied fold, reused by the driver`
  - `pregate_recipe(nb, recipe_id, ops, d2_cos=None) -> PregateResult`
  - `rank_menu(results, quota_n) -> tuple[list[PregateResult], set[str]]` — (measure order, defiant recipe_ids); refused results excluded from the order entirely.

**Brief.** `pregate_recipe`: strict-apply via `nb.apply_strict(ops)` — `OpRefused` → status `refused` (hard drop; refusal is ground truth). On success, re-run the D1 pipeline **on the shaped fold** exactly as `probe_front_flex.main()` does on `sq` (lines 228–246 are the reference): `null_space_basis(shaped)`, re-look-up tip/hub vertex indices **in the shaped fold** by xy via `sq_vertex_index(shaped, ...)` (shaping adds vertices, so indices shift; 2D tip positions are unchanged in the CP), `tip_flex_signatures`, `front_selectivity` → `r_star_shaped`, `dof_shaped`. `FlexInstrumentError` or a failed vertex lookup → status `instrument_error` (candidate stays rankable by `d2_cos` only — pinned behavior, flagged in the note). `rank_menu`: scored candidates ordered by (`r_star_shaped` desc, `d2_cos` desc, `recipe_id` lex) — deterministic; defiant set = top `quota_n` by `d2_cos` among candidates NOT already in the top `quota_n` of the instrument order, plus all `instrument_error` candidates (capped at `quota_n` total).

- [ ] **Step 1: Probe before pinning** — throwaway run (uncommitted script or `python -c`): pregate the B5-prime incumbent (`["outside:0.0,0.46801304:0.12398308661620648:142.5"]`) and the empty recipe `[]` on the served dog. Record actual `dof_shaped` / `r_star_shaped` for the incumbent; confirm `[]` reproduces r\* 1.76272. If the incumbent smoke raises (instrument does not survive shaped patterns), STOP — report to controller; that is a spec-level finding (Gate S0.a(b) fail), not something to code around.
- [ ] **Step 2: Write failing tests** in `tests/test_pose_pregate.py` (sim-free, dog fixture via `served_dog()`):
  1. `[]` (unshaped) → scored, `r_star_shaped == pytest.approx(1.76272, abs=1e-3)`, `dof_shaped == 3`.
  2. Incumbent op → scored; pin the exact `dof_shaped` / `r_star_shaped` values recorded in Step 1 (drift-tripwire style, `abs=1e-6`-ish per determinism precedent).
  3. The four D3-refused recipes — `reverse_deep` θ=105 frac=2.0 at `front_v13`, `front_v18`, `tail_v14`, `back_v12` (build ops via `nb.site_op(k, "reverse_deep", 105.0, 2.0)`) — all → `refused` (Gate S0.a(c), reproduces the pilot's 4/4 sim-free).
  4. `rank_menu` on a synthetic `PregateResult` list: pinned order; quota membership (high-`d2_cos`/low-instrument in; already-top-instrument excluded); `instrument_error` lands in the quota; refused excluded; determinism (same input twice → same output).
- [ ] **Step 3: Run tests, verify they fail** — `cd mcp_harness && .venv/bin/python -m pytest tests/test_pose_pregate.py -q` → import/attribute errors.
- [ ] **Step 4: Implement `pose_pregate.py`** per the brief (~120 lines; module docstring names the spec + the ranker-not-veto rationale).
- [ ] **Step 5: Tests pass** — same command, all green.
- [ ] **Step 6: Commit** — `git add mcp_harness/pose_pregate.py mcp_harness/tests/test_pose_pregate.py && git commit -m "feat(front-lever-payoff): pose_pregate -- sim-free instrument pre-gate (strict-apply -> shaped-pattern flex -> ranked menu w/ defiant quota)"`

### Task 2: `probe_front_wave.py` — wave driver, S0 menu, budget ledger (Gates S0.b/S0.c machinery)

**Files:**
- Create: `mcp_harness/probe_front_wave.py`
- Create: `mcp_harness/tests/test_front_wave.py`

**Interfaces:**
- Consumes: Task 1's `pregate_recipe`/`rank_menu`/`PregateResult`; the D3 pilot's stack **as the template** (`probe_front_pilot.py`: `ReadBudget`, `_read`, baseline-×3 + `toward` sign logic, `pc.CouplingTable`/`CouplingRow`, `pdc._measure`/`fox_targets_with_fallback`/`open_session_with_anchor`, `sim_capture.SimSession`) — import what is importable, copy-adapt what is `main()`-bound.
- Produces: `WaveBudget(s0=50, s1=50, contingency=20)` with `.spend(wave)` (draws wave allocation, then contingency; `BudgetExhausted` past both), `.rollover()` (S0 residue → S1), `.ledger() -> dict`; `build_s0_menu(nb, d2_ranking, terminal_keys) -> list[(recipe_id, ops, d2_cos)]`; `table_mine(cells, targets, baseline_angles) -> list[str]`; CLI `--menu-only` (S0.b: emit menu + pre-gate scores + order + quota to `probe_front_wave.out.json`, no sim) and `--wave s0` (capture).

**Pinned S0 menu** (14 cells; novelty-enforced at runtime against `resume_keys()`; collisions dropped and reported; cap 16):

| family | cells |
|---|---|
| front-pair atomic (one recipe, two ops) | `frontpair\|outside\|142.5\|0.5`, `frontpair\|outside\|105\|0.5` |
| front-pair moderated | `frontpair\|outside\|142.5\|0.35`, `frontpair\|outside\|105\|0.35` |
| front-tip sink | `front_v13\|sink\|1.25`, `front_v18\|sink\|1.25` |
| front-tip off-grid θ | `front_v13\|outside\|30\|0.5`, `front_v18\|outside\|30\|0.5` |
| in-grid-depth deep | `front_v13\|reverse_deep\|105\|0.5`, `front_v18\|reverse_deep\|105\|0.5`, `front_v13\|reverse_deep\|170\|1.25`, `front_v18\|reverse_deep\|170\|1.25` |
| D2-seeded variants (base cells terminal) | `head_v25\|reverse\|142.5\|0.5`, `head_v25\|outside\|142.5\|0.65` |

`d2_cos` per cell = |cos| of its site/kind's nearest measured row from `probe_front_flex.out.json`'s `d3_ranking` (None where absent).

**Brief.** Driver flow (S0): load `probe_front_flex.out.json` (STOP if missing/drifted anchors), `served_dog()` → `NamedBase` → `naming_parity`; **table-mine first** (zero reads: scan gate-1 scored cells for `toward × Δfront ≥ 20`; any hit goes straight to the confirm queue — none expected per B5-prime); pregate the full menu (refusals recorded, zero reads); `rank_menu` with `quota_n=8`; **`--menu-only` writes everything and exits** (the controller commits the ledger note BEFORE capture — Gate S0.b). Capture mode mirrors the pilot's `main()`: session anchor (1 read), baseline ×3, `toward` from own data, then menu in rank order — pinned ordering rule: **every quota pick gets its first read before any candidate gets confirm top-ups**; first read with `toward × Δfront ≥ 20` → 2 more reads immediately (×3 rule); CONFIRM = mean ≥ +20 toward. **Kick trigger:** a `frontpair|*` recipe going `parked` (persistent, 3/3 retries) → write verdict `HALT-KICK` to the out.json, stop capturing, exit 2. Emit final wave verdict: `CONFIRM(recipe_id, mean_deltas)` | `NO-CONFIRM(reason: menu_exhausted | budget_exhausted)`.

- [ ] **Step 1: Write failing tests** (all sim-free; monkeypatch/fixture-driven):
  1. `WaveBudget`: 50 S0 spends OK; 51st draws contingency; 71st (50+20, S1 untouched) raises `BudgetExhausted`; `.rollover()` moves S0 residue to S1; ledger counts exact.
  2. `build_s0_menu`: with `terminal_keys = set()` → exactly the 14 pinned cells above, in table order; with a terminal set containing two of them → those two dropped and reported; front-pair recipes carry two ops (one per front, sorted site order).
  3. Quota ordering rule: synthetic ranked menu + quota set → generated read order satisfies "all quota firsts before any confirm top-up".
  4. `table_mine`: fixture rows (one with Δfront +25 toward, rest below) → returns exactly that key; all-below → empty.
  5. Kick trigger: simulated `parked` row for `frontpair|outside|105|0.5` → driver returns/flags `HALT-KICK` without further reads (monkeypatch the read function).
- [ ] **Step 2: Run tests, verify they fail** — `.venv/bin/python -m pytest tests/test_front_wave.py -q`.
- [ ] **Step 3: Implement `probe_front_wave.py`** per the brief (~250 lines; reuse over rebuild — if a pilot helper is `main()`-bound, lift it into the new module rather than importing private state).
- [ ] **Step 4: Tests pass** — same command.
- [ ] **Step 5: Commit** — `git commit -m "feat(front-lever-payoff): probe_front_wave -- S0 wave driver (budget ledger 50/50/20, pinned 16-cell menu, table-mine, quota ordering, kick HALT)"`

### Task 3: S0 execution (controller-run; Gates S0.b → S0.c)

**Files:** none created (probe outputs uncommitted); SDD ledger + plan checkboxes updated.

- [ ] **Step 1 (S0.b):** `cd mcp_harness && .venv/bin/python probe_front_wave.py --menu-only` → review printed menu/scores/order/quota; record the menu block verbatim in `.superpowers/sdd/progress.md`; commit the ledger note (docs only) BEFORE any capture.
- [ ] **Step 2 (S0.c):** controller runs `.venv/bin/python probe_front_wave.py --wave s0` with the sim visible (SimSession is HEADED). Watch for `HALT-KICK` (exit 2) → stop the slice, report kick-hardening as prerequisite per spec.
- [ ] **Step 3:** record the verdict + read ledger in the SDD ledger. CONFIRM → proceed to Task 4A (skip 4B). NO-CONFIRM → proceed to Task 4B (skip 4A).

### Task 4A: S1 composition wave (fires ONLY on S0 CONFIRM; Gates S1.a/S1.b)

**Files:**
- Modify: `mcp_harness/probe_front_wave.py` (add `build_s1_menu` + `--wave s1`)
- Modify: `mcp_harness/tests/test_front_wave.py` (extend)

**Interfaces:**
- Produces: `build_s1_menu(nb, lever_recipe: tuple[str, list[str]], incumbent_ops: list[str], terminal_keys) -> list[(recipe_id, ops, d2_cos)]`. Incumbent op string (verbatim, B5-prime winner on `front_v18`): `outside:0.0,0.46801304:0.12398308661620648:142.5`.

**Brief.** Menu (cap 12, pre-gate-ranked like S0, same quota rule): `lever-alone` (re-uses the S0-confirmed recipe — its S0 reads stand, do not re-measure ×1; it enters the ×3 confirm queue directly if it is the best), `lever→incumbent`, `incumbent→lever`, plus ≥ 2 moderated-amplitude variants per order (lever at its θ and a −25 %-θ variant; incumbent moderated via `nb.site_op("front_v18", "outside", 105.0, <frac matching the winner's absolute d>)`) — implementer owns exact variant construction; reviewer checks: both orders present, lever-alone present, ≥ 2 moderated variants per order, cap respected, novelty enforced. Flow: incumbent re-baseline ×3 (whole-pose error vs fox targets — reuse `pdc._measure` totals), pregate + rank + `--menu-only` ledger commit (S1.a), capture in order, ×3 the best. **S1.b verdict:** best mean total ≤ 104 → `CEILING-BROKEN`; else `LEVER-CONFIRMED-COMPOSITION-EATS` — both emit the full per-group residual map (front/back/head/tail) ×3 means.

- [ ] **Step 1: Write failing tests** — menu construction (orders/lever-alone/moderation/cap/novelty), payoff arithmetic (`mean of 3 totals ≤ 104` boundary: 103.99 pass / 104.01 fail), lever-alone not re-measured ×1.
- [ ] **Step 2: Verify fail, implement, verify pass** — `.venv/bin/python -m pytest tests/test_front_wave.py -q`.
- [ ] **Step 3: Commit** — `git commit -m "feat(front-lever-payoff): S1 composition wave (pre-gate-ranked grid, incumbent re-baseline, payoff bar <=104 x3)"`
- [ ] **Step 4 (controller):** `--menu-only` → ledger commit → `--wave s1` capture → record verdict + residual map in SDD ledger.

### Task 4B: `probe_flex_extension.py` — escalation probe (fires ONLY on S0 NO-CONFIRM; Gates E.a/E.b)

**Files:**
- Create: `mcp_harness/probe_flex_extension.py`
- Create: `mcp_harness/tests/test_flex_extension.py`

**Interfaces:**
- Consumes: `rigid/kinematics/closure.py` (`closure_residual`, `closure_jacobian`, `RankDiagnostics`) and `rigid/degree4.py` (the finite degree-4 analytics + fixture — read both files AND `rigid/conventions.py` first; conventions are mm/radians with oriented left/right hinge transforms, *different* from `rigid_fold.py` — see its OWNERSHIP NOTE); `probe_front_flex.out.json` → `d1.w_creases` (the w\* direction over crease keys `"u-v"`).
- Produces: verdict `EXTENDS` | `NON-EXTENDING` | `REFUSED(anchor)` in `probe_flex_extension.out.json` (uncommitted).

**Brief.** Explicitly throwaway diagnostic code; NO additions under `rigid/`, no from-scratch residual/jacobian math — the kernel owns those; the probe only assembles per-interior-vertex constraints into a whole-pattern system and runs damped-Newton continuation along w\* at growing amplitude (amplitude schedule and convergence tolerances are implementer judgment, recorded in the out.json). Explicit convention translation layer (`rigid_fold` crease tuples/degrees ↔ kernel radians/hinge orientation) isolated in one function. **E.a anchor is mandatory and blocking:** the probe must reproduce degree-4 first-order dof 2 → finite dof 1 on the kernel's own fixture BEFORE loading the dog; anchor failure → `REFUSED`, no dog verdict (pattern from `probe_folding_dof`). **Coordination (pinned):** at build time check whether `codex/rigid-origami-phase-2-topology-fold` (TopologyView + SE(3) face poses; unmerged as of 2026-07-13) has landed on main — if yes, prefer consuming its topology layer; never import from unmerged branches. **Verdict semantics (spec §4 E.b):** `NON-EXTENDING` → "structural at finite order for rigid kinematics" → routing = charter the structural tree/compile slice. `EXTENDS` (but S0 could not reach it) → bridge-change territory → **HALT and ask** — do not build any bridge change.

- [ ] **Step 1: Read `rigid/kinematics/closure.py`, `rigid/degree4.py`, `rigid/conventions.py`** end-to-end; record the kernel's exact call signatures + tolerance constants in the SDD ledger before writing code.
- [ ] **Step 2: Write the failing anchor test** — `test_flex_extension.py`: degree-4 fixture through the probe's translation layer reproduces first-order dof 2 and finite dof 1 (exact fixture values from Step 1; pin them in the test).
- [ ] **Step 3: Verify fail, implement probe, verify pass** — `.venv/bin/python -m pytest tests/test_flex_extension.py -q`.
- [ ] **Step 4: Run on the dog (sim-free):** `.venv/bin/python probe_flex_extension.py` → record verdict + continuation trace summary in the SDD ledger.
- [ ] **Step 5: Commit** — `git commit -m "feat(front-lever-payoff): probe_flex_extension -- finite-extension continuation over rigid/ closure kernel (degree-4 anchored, verdict-routing per spec)"`. If verdict is `EXTENDS`: **HALT and ask before anything further.**

### Task 5: Full-suite gate, outcome handoff, PR

**Files:**
- Create: `docs/superpowers/2026-07-<DD>-handoff-front-lever-payoff-outcome.md`

- [ ] **Step 1: Full suite via nohup** — `cd mcp_harness && nohup .venv/bin/python -m pytest tests -q > /tmp/front-lever-suite.log 2>&1 &` then poll the log; expected: **592 + (new tests) passed / 4 skipped**, zero failures. Also `cd .. && mcp_harness/.venv/bin/python -m pytest web/tests -q` (should be untouched: 40 passed).
- [ ] **Step 2: Write the outcome handoff doc** — mirrors `2026-07-12-handoff-b5-prime-outcome.md` in shape: verdict per gate with measured numbers, read ledger vs the 50/50/20 grant, deferred minors, and the **routing verdict naming (a) productization of the best-known stack via `ide_shape_ops` — S1 winner if `CEILING-BROKEN`, else the 119.14 incumbent — ALWAYS, plus (b) the outcome's research follow-up** (composition follow-up / structural tree-compile charter / kick-hardening prerequisite / bridge HALT report).
- [ ] **Step 3: Commit the handoff; verify nothing uncommitted-by-design got staged** — `git status` must show `*.out.json(l)` / logs as untracked; never `git add -A`.
- [ ] **Step 4:** invoke superpowers:finishing-a-development-branch — ask the user before any push; human merges the PR.

---

## Self-review record (writing-plans checklist)

- **Spec coverage:** §2 decisions → Global Constraints + Tasks 1/2 (pre-gate, quota, budget), 4A (S1 bar/menu), 4B (adapter scope), 5 (routing); §3 → Task 1; §4 S0.a → preflight + Task 1 tests; S0.b/S0.c → Tasks 2/3; S1.a/b → 4A; E.a/b → 4B; §5 layout → file list; §6 testing → per-task test lists; §7 process → Global Constraints + Task 3/5 controller steps; §8 out-of-scope → "do NOT modify" line + 4B HALT rules.
- **Placeholders:** none — menu cells, bars, anchors, and commands are literal; the two implementer-judgment zones (S1 variant construction, continuation schedule) have explicit reviewer criteria instead of code, per the pinned sizing note.
- **Type consistency:** `PregateResult`/`pregate_recipe`/`rank_menu` (Task 1) match Task 2's consumption; `build_s1_menu` signature matches 4A; verdict strings (`CONFIRM`/`NO-CONFIRM`/`HALT-KICK`/`CEILING-BROKEN`/`LEVER-CONFIRMED-COMPOSITION-EATS`/`EXTENDS`/`NON-EXTENDING`/`REFUSED`) are each defined where produced and referenced identically where routed.

---

## S0.b menu of record (Gate S0.b, committed before any capture — 2026-07-13)

Pinned 14 → **6 capture candidates** after novelty + pre-gate:
- Terminal-collision drops (gate-1 already measured; none table-mined ≥ +20): `front_v13|reverse_deep|105|0.5`, `front_v13|reverse_deep|170|1.25`, `front_v18|reverse_deep|105|0.5`, `front_v18|reverse_deep|170|1.25`, `head_v25|outside|142.5|0.65`, `head_v25|reverse|142.5|0.5`.
- Pre-gate refusals (sim-free, 0 reads): `front_v13|sink|1.25`, `front_v18|sink|1.25` ("d reaches past the axial crease").
- Capture order (all r\*_shaped = inf — unbounded front selectivity on every shaped pattern; dof 4 tips / 5 pairs; lex tiebreak): `front_v13|outside|30|0.5`, `front_v18|outside|30|0.5`, `frontpair|outside|105|0.35`, `frontpair|outside|105|0.5`, `frontpair|outside|142.5|0.35`, `frontpair|outside|142.5|0.5`.
- Defiant quota: empty (menu ≤ quota_n — rule degenerates correctly). Table-mine: 0 hits.
- Budget at gate: 0/50 S0 spent.
