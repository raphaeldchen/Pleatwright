# Front-lever payoff — Phase S excitation, composition, and closure escalation

**Status:** Approved design (brainstormed 2026-07-13, decisions pinned below)
**Date:** 2026-07-13 · **Branch:** `feat/front-lever-payoff`
**Lineage:** executes the Phase-S charter of
`docs/superpowers/specs/2026-07-12-b5-front-dof-diagnosis-design.md` (§5),
under the Wave-S0 approval recorded in
`docs/superpowers/2026-07-13-checkpoint-b5-front-dof-phase-d.md` (DECISION
header). Phase D merged as PR #39 (main `1e8a3c6`).

---

## 1. The question this slice answers

Phase D proved the served/squared dog's crease pattern HAS a front-selective
first-order flex direction (r\* = 1.76272, calibrated captured 0.904) and that
B5-prime's front ceiling is therefore a property of the **op vocabulary**, not
the mechanism — but the pilot could not excite the direction (its dominant
front-hub context drew only op parameterizations the shaping layer refuses).

This slice answers, in order, with pre-pinned routing:

1. **S0 (excitation):** does an *applicable* op recipe move the front
   ≥ +20° toward the fox target? CONFIRM → S1; refuse/fail → escalation.
2. **S1 (payoff, fires only on S0 CONFIRM):** does the confirmed front lever,
   composed with the B5-prime incumbent, beat the 119.14 whole-pose error by
   ≥ 15° (bar ≤ 104, ×3)? This is the headline if it lands: the B5 vocabulary
   ceiling, measured across two slices, broken.
3. **Escalation (fires only on S0 refuse/fail, sim-free):** does the
   first-order flex w\* extend to a finite rigid fold, or is it a first-order
   mirage? Non-extending → structural verdict at finite order (for rigid
   kinematics) → charter the tree/compile slice. Extending-but-unreachable →
   bridge change territory → HALT and ask.

Honest-outcome rule pinned: S0-fail → clean escalation verdict is a
successful slice. All gates pinned BEFORE measurement.

## 2. Decisions pinned at the brainstorm

1. **Pre-gate authority — ranker + defiant quota.** The sim-free instrument
   pre-gate (new this slice, §3) *ranks* each wave's menu and steers reads,
   but does not get hard-cull veto power: **15% of each wave's read
   allocation, rounded up (8 of 50)**, is reserved for candidates the
   pre-gate ranks low but the D2 empirical |cos| ranking ranks high.
   Rationale: the pre-gate reasons about rigid first-order kinematics while
   the scoring oracle is a mass-spring sim tolerating p90 strain < 0.15 (the
   B5-prime incumbent lives in the strained regime), so an uncalibrated
   rigid-regime veto could silently drop a strained-regime winner. The quota
   doubles as calibration data for the pre-gate itself. Shaping-layer
   *refusals* found at pre-gate time are still dropped outright — refusal is
   ground truth, not heuristic.
2. **Budget — 50 S0 / 50 S1 / 20 shared contingency (120 total, approved at
   the Phase-D checkpoint).** A read = one sim measure-attempt (D3
   convention: baselines and ×3 confirms count; parked slots retry
   internally). The 20 is a shared pool for baseline re-reads, park retries,
   and ×3 top-ups, drawable by either wave. Unused S0 budget rolls into S1.
   The escalation branch is sim-free — it costs dev time, zero reads. A hard
   budget guard (D3's 40-read-guard pattern) enforces the ledger.
3. **S1 payoff bar — total whole-pose error ≤ 104, mean of 3 re-measures,**
   reported with the full per-group residual map (front/back/head/tail).
   ≥ 15° better than the 119.14 incumbent = > 2× the ±7° shaped re-read
   noise. Incumbent is re-baselined ×3 in-session before comparison.
4. **S1 search — pre-gate-ranked bounded grid.** A pinned composition menu
   (~8–12 cells) measured in pre-gate rank order with the same defiant
   quota; no greedy hill-climb (anti-additivity median 127° and slice-4's
   descent regression argue against path-dependent search).
5. **Escalation adapter — minimal probe in `mcp_harness/`,** consuming
   main's per-vertex closure kernel; explicitly throwaway diagnostic code;
   no new module under `rigid/` (Codex's active namespace); mandatory
   degree-4 anchor before touching the dog.
6. **Routing — productization named in every outcome.** The handoff's
   routing verdict always names "productize the best-known recipe stack via
   `ide_shape_ops`" as a follow-up (S1 winner if it lands, the 119.14
   incumbent otherwise), alongside the outcome's research follow-up.
7. **Branch name:** `feat/front-lever-payoff` (constraint honored: no
   "b5-front-dof" / "prime" / "slice").

## 3. The instrument pre-gate (new machinery; the slice's durable artifact)

`mcp_harness/pose_pregate.py` — a pure, sim-free library closing the loop
Phase D opened: the rigid instrument stops being a diagnostician and becomes
the search's ranking function.

Per candidate recipe:

1. **Apply** the recipe's ops to the display pattern through the existing
   shaping layer (pure geometry, seconds). A shaping refusal drops the
   candidate for **zero reads** — this alone retires the D3 failure mode
   (6/8 refusals discovered only at capture time).
2. **Re-analyze** the shaped pattern with the promoted instrument:
   `null_space_basis` → `tip_flex_signatures` → `front_selectivity`.
3. **Score:** primary = r\*_shaped (does a front-selective flex direction
   survive/strengthen in the shaped pattern?); tiebreak = the candidate's D2
   empirical |cos| against the predicted front-direction signature, where a
   measured coupling row exists.

`rigid_fold.py` is NOT modified — the promoted instrument stays pure; the
pre-gate *composes* shaping + instrument. The pre-gate has never been run on
shaped patterns; §4 Gate S0.a(b) is the validation that it works at all,
before it is trusted to rank.

## 4. Gates (verdict rules pinned BEFORE measurement)

### Gate S0.a — pre-gate anchors (sim-free; must pass before menu scoring)

- (a) Regenerated `probe_front_flex.out.json` reproduces **r\* = 1.76272,
  captured = 0.904** on the unshaped dog (probe refuses on anchor drift —
  kickoff requirement; on failure STOP the slice).
- (b) Shaped-pattern smoke: apply the B5-prime incumbent op
  (`outside:0.0,0.46801304:0.12398308661620648:142.5` on `front_v18`), run
  the flex analysis on the result; require finite dof and a well-formed
  signature matrix. This is the pre-gate's real technical risk, gated first.
- (c) The four D3-refused `reverse_deep|frac 2.0` recipes refuse at pre-gate
  time (reproduces the pilot's refusals sim-free).
- Coupling table sourced read-only from the main checkout
  (`mcp_harness/probe_dog_coupling.out.jsonl`, confirmed present 2026-07-12)
  and reconciled **162 = 114 scored / 12 refused / 36 parked / 0 error** via
  the committed `reconcile_coupling` gate.

### Gate S0.b — menu committed (sim-free; before the first capture)

The exact S0 menu, pre-gate scores, rank order, and defiant-quota selections
are written to `probe_front_wave.out.json` and recorded in the SDD ledger
BEFORE any sim read. Menu families (exact cells pinned at plan time):

- Symmetric front-pair `outside` θ ∈ {105, 142.5} — both fronts as ONE
  atomic recipe (1 read each).
- Front-tip `sink|1.25` and `outside|30` (the tip-context menu the pilot
  never reached because hub_front dominated).
- Moderated front-tip amplitudes.
- In-grid-depth `reverse_deep` frac ∈ {0.5, 1.25} at front sites.
- D2-seeded cells (top measured couplings: `head_v25|reverse|142.5|0.65`
  0.972, `head_v25|reverse|105|0.35` 0.958, `front_v13|reverse_deep|170|0.5`
  0.912) — entering only as moderated/composed variants where the base cell
  is terminal.

**Table-mine first (zero reads):** scan the committed coupling table for any
already-measured cell with Δfront ≥ +20° toward target; such a cell (none is
expected, per B5-prime's ceiling finding) goes straight to ×3 confirm.
**Never re-measure a terminal gate-1 cell.**

### Gate S0.c — excitation verdict

Baseline ×3 opens the wave (D3 reference: front 65.98 / back 27.80 /
head 34.52; fox front target 134.83). **CONFIRM bar (carried, pinned):
front ≥ +20° toward the fox target, mean of 3 standalone reads from the
unshaped base** (×3 confirm rule at 20°). CONFIRM → S1 fires. Budget
exhausted or menu exhausted without confirm → escalation fires.

**Kick trigger (pre-armed, standing):** if a symmetric front-pair recipe
parks asymmetrically (back_v12 precedent, 3/3 park, third datum), **HALT**
and raise kick-hardening as a prerequisite rather than absorbing it.

### Gate S1.a — composition menu committed (fires only on S0 CONFIRM)

- Incumbent re-baselined ×3 in-session (3 reads); fox-target baseline
  carries from S0.
- Pinned menu (~8–12 cells): both op orders (lever→winner, winner→lever) ×
  amplitude variants (full and moderated θ each side) + **lever-alone**
  (catches the lever by itself beating the incumbent). Pre-gate-ranked
  sim-free, same defiant quota, committed to the ledger before capture.

### Gate S1.b — payoff verdict

Best cell **≤ 104 total whole-pose error, ×3, with the full per-group
residual map**. Met → ceiling broken (headline). Missed with lever
confirmed → still positive: routing = "lever exists and is excitable;
composition eats it" → productization of best-known stack + a
composition-focused follow-up. **S1-miss does NOT route to escalation** —
a confirmed lever makes the finite-extension question moot.

### Gates E.a / E.b — escalation (fires only on S0 refuse/fail; sim-free)

- **E.a (anchor, mandatory before the dog):** the probe reproduces the
  degree-4 fixture's known reduction — **first-order dof 2 → finite dof 1**.
  Conventions differ between `rigid/` (mm/radians, oriented left/right hinge
  transforms, pinned tolerances) and `rigid_fold.py` (see its OWNERSHIP
  NOTE); the probe translates explicitly and the anchor proves the
  translation. Anchor failure → probe refuses a verdict (pattern from
  `probe_folding_dof`).
- **E.b (continuation verdict):** compose per-interior-vertex closure
  constraints (`closure_residual`, exact `closure_jacobian`,
  `RankDiagnostics` from `rigid/kinematics/closure.py`) over the squared
  dog; continuation along w\* at growing amplitude. Verdicts:
  - **Non-extending** → "structural at finite order **for rigid
    kinematics**" — decisive in combination with S0's excitation failure →
    charter the structural tree/compile slice (parent spec §5 structural
    branch) and end honestly.
  - **Extending but unreachable by the vocabulary** → remedy likely needs
    per-crease fold-angle targets the display pipeline cannot express →
    bridge change → **HALT and ask** (house rule; the bridge is untouched
    this slice).
- **Coordination rule:** check `codex/rigid-origami-phase-2-topology-fold`
  merge status at build time (its TopologyView / SE(3) face-pose layer
  overlaps the adapter's scaffolding; spec frozen 2026-07-12, unmerged). If
  landed on main, prefer consuming it; never import from unmerged branches.
  Do NOT build a from-scratch Gauss-Newton; consume the kernel.

## 5. Code layout

- **New `mcp_harness/pose_pregate.py`** — the pre-gate library (§3). Pure,
  sim-free, unit-tested. The slice's durable artifact.
- **New `mcp_harness/probe_front_wave.py`** — S0/S1 driver: pinned menu →
  table-mine → pre-gate rank → capture orchestration on the existing
  `pose_base` / `pose_coupling` / `sim_capture` stack (reuse, don't
  rebuild), budget ledger with hard guard, ×3 confirm rule, verdict
  emission. Writes `probe_front_wave.out.json(l)` (uncommitted).
- **New `mcp_harness/probe_flex_extension.py`** — escalation probe, built
  ONLY if the branch fires. Explicitly throwaway diagnostic code; no
  additions under `rigid/`.
- **Untouched:** `rigid_fold.py`, the ide-bridge, `rigid/` package,
  shaping layer semantics.

## 6. Testing

All tests sim-free (the suite never captures; sim runs are controller-only):

- Pre-gate: refusal → drop; the four D3 refusals reproduced sim-free;
  shaped-pattern flex smoke on the incumbent op; ranking + defiant-quota
  selection deterministic on a synthetic menu.
- Driver: budget-guard unit test (50/50/20 ledger, rollover, contingency
  draw); table-mine correctness on a fixture table; terminal-cell
  no-re-measure rule pinned.
- Escalation (only if built): degree-4 anchor (dof 2 → finite dof 1) as a
  test; convention translation pinned against the fixture.
- Full-suite baseline to hold: **592 passed / 4 skipped**.

## 7. Process & logistics (house rules carried)

- Full SDD: this spec → writing-plans → subagent-driven-development. Plans
  may carry judgment-bearing prose briefs; tasks sized gate-per-package;
  reviewers verify against pinned gates and this spec.
- **Controller-only for ANY headed-sim run** (subagent-launched sim
  processes get orphan-killed — standing hard rule). Full-suite runs via
  nohup + log-poll, never a bare foreground call (120s default timeout
  parked an implementer 2.5 h last slice).
- Fresh-worktree env copy list (Phase-D lesson m2): `.venv` symlink,
  `headless_treemaker*.so`, `oriedita/*.jar`, `OrieditaValidator.class`,
  `web/frontend/dist`, coupling JSONL.
- Regenerate, don't copy: `probe_front_flex.out.json` via
  `probe_front_flex.py` (sim-free, seconds, deterministic, refuses on
  anchor drift).
- Probe outputs (`*.out.json/.jsonl/.log`) and suite logs stay uncommitted
  (NOT gitignored — never `git add -A`). `dist/` is gitignored; cp
  public→dist is load-bearing.
- Margins ≫ drift: ±7° shaped re-reads; any < 10° comparison needs ×3.
- Shared checkout: Codex is active on the main checkout (currently parked
  on `codex/rigid-origami-phase-0` — read main's state through git, not the
  working directory).
- Human merges every PR; ask before push.
- Slice end: outcome handoff doc + PR. Routing verdict names
  **productization of the best-known stack (always)** + the outcome's
  research follow-up (composition follow-up / structural tree-compile
  charter / kick-hardening prerequisite).

## 8. Out of scope

- Bridge changes of any kind (per-crease fold-angle targets → HALT and ask).
- Kick-hardening implementation (HALT trigger only; raising it as a
  prerequisite is the deliverable if it fires).
- Contributions to the `rigid/` package or its conventions.
- Productization implementation (`ide_shape_ops` wiring) — routed, not built.
- Metric-Tree / compile-side intervention (chartered by the structural
  branch verdict, not executed here).
