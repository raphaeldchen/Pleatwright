# Molecule Mobility Implementation Plan (M / K2 / H)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Sizing note (pinned at kickoff, Fable-5 working style):** tasks carry
> judgment-bearing prose briefs, not verbatim code. Implementers own the
> how; reviewers verify against the pinned gates and the spec
> (`docs/superpowers/specs/2026-07-14-molecule-mobility-design.md`).
> Lane M is derivation-FIRST: analytic predictions are committed to the
> SDD ledger BEFORE their numeric checks run; larger single-package briefs
> are deliberate there — every package still ends at a reviewer gate.
> Controller-only for ANY headed-sim run (standing hard rule).

**Goal:** Explain WHY every packable quadruped-family compile's front flex is totally obstructed (Q(w,w) ∉ range(J), rel = 1.0) and break the lock at the molecule level (M); settle the kick·target-branch sign hypothesis and, if confirmed, build the target-aware kick (K2); ship fold-handle passing and close the blocked P live demo (H).

**Architecture:** One sign-check probe (`probe_kick_alignment.py`: edges_foldAngle → ρ-convention target direction via the constructive-τ gauge → flex-space projection → z-field alignment vs the bridge hash kick), a conditional capture-harness target kick (`sim_capture.py` seam + `probe_kick_validation.py` driver), one fixture library (`molecule_fixtures.py`: hand-built Lang-molecule FOLD dicts), the mechanism note (committed doc + prediction-pinning tests), one generalized stage-1 instrument (`tip_mobility.py`: rigid-motion-quotient tip signatures, no hub assumption, reusing `rigid_fold.front_selectivity`), one pure augmentation library (`crease_augment.py`), one sim-free remedy funnel driver (`mobility_search.py`: families a+d → stage-1 → stage-2 → ledger), one sim confirm driver (`probe_mobility_confirm.py`), and the fold-handle registry (`fold_registry.py` file-backed shared store + `server.py`/`linter_server.py` wiring + SYSTEM_PROMPT pins). `rigid_fold.py`, `rigid/`, `shaping*.py`, `square_complete.py`, `web/server.py`, and the ide-bridge are untouched; the C++ engine is read-mostly with HALT-and-ask before any edit.

**Tech Stack:** Python 3 in `mcp_harness/.venv`, numpy only (no new deps), pytest; spawn-isolated `headless_treemaker` compiles (no GPU); headed `SimSession` for captures — controller-run only; Groq (`llama-4-scout`) for the H demo; Lang's official C++ source at `~/Desktop/TreeMakerSource` as read-only ground truth.

## Global Constraints

- **Budget: 90 reads = K2 25 / M 40 / H 5 / contingency 20.** Rollover K2→M at K2's end; unspent M → contingency, never unpinned exploration. A read = one measure-attempt. `WaveBudget` pattern (`probe_front_wave`) is the guard.
- **Pinned anchors (STOP the slice on drift):** unshaped dog r\* = **1.76272**, captured = **0.904**, coupling reconcile **162 = 114/12/36/0**; `probe_flex_extension` anchor PASS + NON-EXTENDING (defect **0.095625**, rel **1.0**); `probe_kick_projection` FALSIFIED with back_v12 **0.430763** vs back_v16 **0.238736**, frontpair **0.320051**; `structural_search --coarse` 144 rows = **108/12/12/12**, all 12 completed funnels rel = 1.0; local suite **741 passed / 4 skipped** + web **59** (CI-equivalent 737/9).
- **Pinned decision constants (this plan; do not tune):**
  - K2.0 gate (strict sign rule): CONFIRMED iff EVERY gated parked cell's alignment < −tie_tol AND every scored cell's > +tie_tol, **frontpair θ-pair included and gating**; any sign violation or |alignment| ≤ tie_tol → FALSIFIED. **tie_tol = 1e-9** on normalized alignment ∈ [−1, 1]. Op-refusal → exit 2 REFUSED.
  - K2.1 target kick: lift = z-field of the flex-projected target direction, normalized to max-|z| = **2e-4**, sign chosen so ⟨lift, target z-field⟩ > 0; no `edges_foldAngle` or zero flex-projection → send 2D unchanged (bridge hash kick). Gates = the unbuilt K.2's, verbatim (Task 4).
  - Stage-1 bar (remedies): tip_mobility **r\*_q ≥ 1.0** (quotient coordinates). Stage-2: `flex_extension.obstruction_verdict` EXTENDING iff rel defect < `STAGE2_REL_TOL = 1e-4` at both h (carried unchanged; anchor-first).
  - tip_mobility quotient: least-squares affine field z = a + bx + cy fitted over **ALL pattern vertices**, evaluated at tips, subtracted. Two-step-size agreement guard carried from `rigid_fold.tip_flex_signatures` (h 1e-6/1e-7 semantics unchanged).
  - tip_mobility calibration gate: **verdict agreement 13/13** (12 completed T-funnels + served dog) at the r\* ≥ 1.0 boundary vs the D1 ledger values, AND the instrument READS (finite r\*_q, no refusal) at least one flap-family compile (dof 7–17) and one headmid variant (dof 9). Disagreement → HALT the gate definition (calibration finding), do not tune.
  - M2 scope pins: augmentation move vocabulary ≤ **3** move families, pinned at Task 12 Step 0 from the mechanism note; separated-hub family ≤ **6** instances (one topology, no grid).
  - M sim CONFIRM: front ≥ **+20°** toward fox 134.83, mean of 3 standalone reads from a fresh baseline ×3; per-passer cap **12** reads, ≤3 passers ranked (rel_fine asc, r\*_q desc). ±7° drift band; any < 10° comparison needs ×3 + same-session baseline.
  - H registry: handle = `"fold:" + sha256(canonical_json)[:12]`, canonical_json = `json.dumps(parsed, sort_keys=True, separators=(",", ":"))`; store dir = `IDE_FOLD_REGISTRY_DIR` env var, default `os.path.join(tempfile.gettempdir(), "ide_fold_registry")`; cap **32** files, oldest-mtime eviction at register; hash re-verified on resolve. Handles never enter the FOLD dict.
- **Do NOT modify:** `mcp_harness/rigid_fold.py` (OWNERSHIP NOTE — import only), `mcp_harness/rigid/`\* (Codex namespace), `mcp_harness/shaping*.py`, `mcp_harness/square_complete.py`, `web/server.py`, `web/frontend/public/simulator/js/ide-bridge.js`. TreeMaker C++ engine read-mostly: **HALT-and-ask before any engine edit** (remedy family c). Never import from unmerged Codex branches — `codex/rigid-origami-phase-2-topology-fold` is GONE from origin (checked 2026-07-14); consume only merged `rigid/kinematics/closure.py` + `rigid.degree4` + `rigid.kinematics.rotations`; re-check `git branch -r | grep codex` at Task-10 build time.
- **Controller-only for ANY headed-sim run** (subagent sim processes get orphan-killed). Full suites and searches via `nohup ... > log 2>&1 &` + log-poll, never bare foreground. Playwright lives in `mcp_harness/.venv` only; SimSession is HEADED.
- Probe outputs (`*.out.json/.jsonl/.log`) and suite logs stay **uncommitted** — never `git add -A`. Artifact-dependent tests carry `needs_flex_json`-style skipif guards (pattern: `tests/test_flex_extension.py:65`).
- Test command: `cd mcp_harness && .venv/bin/python -m pytest tests/<file> -q` (targeted); backend full suite ~10 min via nohup; web suite per `web/frontend/package.json` (baseline 59).
- Branch `feat/molecule-mobility`, single PR at slice end. Ask before push; human merges. Shared checkout: read main's state through git, never the main checkout's working dir. TreeMaker vertex numbering does NOT survive recompilation — site keys are base-relative.

## Environment preflight (controller, before any task review gate)

- [ ] Copy into this worktree (Phase-D recipe): `.venv` symlink, `headless_treemaker*.so`, `oriedita/*.jar`, `OrieditaValidator.class`, `web/frontend/dist`, `.env`, and `cp <repo>/mcp_harness/probe_dog_coupling.out.jsonl mcp_harness/` (read-only source).
- [ ] `cd mcp_harness && .venv/bin/python probe_front_flex.py` — expect exit 0, r\* 1.76272, captured 0.904, tallies 114/12/36/0. Drift → STOP.
- [ ] `cd mcp_harness && .venv/bin/python probe_flex_extension.py` — expect anchor PASS + VERDICT NON-EXTENDING, defect 0.095625, rel 1.0. Drift → STOP.
- [ ] `cd mcp_harness && .venv/bin/python probe_kick_projection.py` — expect exit 1 (FALSIFIED), back_v12 0.430763 / back_v16 0.238736 / frontpair 0.320051. These are K2.0's baseline numbers. Drift → STOP.
- [ ] `cd mcp_harness && nohup .venv/bin/python structural_search.py --coarse > structural_search.coarse.log 2>&1 &` — poll; expect 144 rows = 108 compile_failed / 12 gate_blocked / 12 analysis_error / 12 completed, completed all rel 1.0 (~35 min). This regenerated ledger feeds Task 10's calibration and M1's evidence. Drift → STOP.
- [ ] Baseline suites via nohup: expect backend 741 passed / 4 skipped; web 59.

---

### Task 1 [K2.0]: `probe_kick_alignment.py` — target-branch sign probe

**Files:**
- Create: `mcp_harness/probe_kick_alignment.py`
- Test: `mcp_harness/tests/test_kick_alignment.py`

**Interfaces:**
- Consumes (do not modify): `probe_kick_projection.GATED_PAIRS` and its `_ops_for(nb, site, kind, theta, frac)` cell construction (import, don't copy — the pinned cells must be bit-identical to K.0's); `pose_base.NamedBase(raw, sq, DOG_CONFIG)`, `.apply_strict(ops)`; `probe_front_flex.served_dog()`; `rigid_fold.null_space_basis(fold) -> (creases, basis, DofResult)`; `kick_field.out_of_plane_field(fold, creases, w)`, `kick_field.bridge_hash_kick(n_verts)`; `flex_extension.constructive_tau(fold)`, `flex_extension.degree4_fixture()`, `rigid.degree4.enumerate_degree4_branches`.
- Produces:
  - `target_direction(shaped) -> tuple[list, np.ndarray]` — `(creases, t)` where `creases` is `null_space_basis(shaped)`'s canonical M/V crease order and `t_c = tau_c * radians(edges_foldAngle_c)` — the shaped pattern's target fold-angle vector translated from FOLD convention into rigid_fold's ρ convention via the constructive-τ gauge (`flex_extension.constructive_tau` is the reference and the implementation: FOLD/kernel fold angles and rigid_fold ρ differ by exactly the per-crease τ sign, up to global gauge).
  - `alignment_record(shaped) -> dict` — keys `align` (normalized ⟨`bridge_hash_kick(n_verts)`, z-field of the FLEX-PROJECTED target⟩ ∈ [−1, 1]), `dof`, `target_in_flex_frac` (‖P_flex t‖/‖t‖, telemetry only), `n_verts`. Flex projection = least-squares of `t` onto span(basis); z-field via `out_of_plane_field` on the projected vector (the raw target is NOT a flex; the field is only face-consistent on flexes).
  - `evaluate(records) -> dict` — the pinned strict-sign verdict (Global Constraints) over the 4 gated twin pairs + the gating frontpair θ-pair (parked θ=142.5 vs scored θ=105, both frac 0.35).
  - CLI writes `probe_kick_alignment.out.json` (uncommitted); prints per-cell table + verdict line; exit 0 CONFIRMED / 1 FALSIFIED / 2 REFUSED.

**Brief.** The one careful step is the sign translation, and it is validated BEFORE any twin cell is read (predict-then-measure): on the degree-4 anchor fixture, for each branch tangent from `enumerate_degree4_branches`, write the tangent (kernel convention, radians→degrees) into a copy's `edges_foldAngle`, run `target_direction`, and assert the result lies in `null_space_basis`'s span (residual < 1e-8 after unit normalization) AND is positively aligned with the τ-mapped kernel tangent. A global sign flip is gauge — pin the gauge choice in one place (same convention `flex_extension` uses) and document it in the probe docstring. Note the K.0 contrast in the docstring: K.0's projection was op-invariant per site (assignment-blind rigidity); the TARGET direction is NOT op-invariant (edges_foldAngle changes with θ and kind) — that is exactly why the frontpair θ-pair becomes the decisive, gating comparison.

- [ ] **Step 1: failing tests** (all sim-free): (1) degree-4 sign-translation validation as in the brief (both branches); (2) `alignment_record` on one shaped cell (`back_v16|outside|142.5|0.5`): `align` finite, in [−1, 1], dof ≥ 1; (3) `evaluate` verdict arithmetic on synthetic record tables — CONFIRMED case, FALSIFIED-by-parked-positive, FALSIFIED-by-scored-negative, FALSIFIED-by-tie (|align| ≤ 1e-9); (4) pinned-cell drift tripwire: the gated list matches `probe_kick_projection.GATED_PAIRS` and the frontpair constants (142.5/105/0.35), and the θ-pair is marked gating; (5) unshaped dog: `target_direction` on a fold WITHOUT `edges_foldAngle` raises a clear `ValueError` (the probe only reads shaped patterns).
- [ ] **Step 2: implement; targeted tests green.**
- [ ] **Step 3: commit** (`feat(kick-alignment): K2.0 target-branch sign probe (strict sign gate, theta-pair gating)`).

### Task 2 (CONTROLLER CHECKPOINT — K2.0 gate, sim-free)

- [ ] `cd mcp_harness && .venv/bin/python probe_kick_alignment.py` — record the per-cell alignment table in the ledger regardless of verdict.
- [ ] **CONFIRMED** → Tasks 3–4 build the target kick. **FALSIFIED** → STOP the K2 build (Tasks 3–4 skipped); K2-fail routing: M's sim block proceeds on non-kick-blocked reads, coverage hole named in the handoff; follow-up = solver-dynamics instrumentation charter. **REFUSED** (exit 2) → investigate before proceeding; these cells all applied in K.0.

### Task 3 [K2.1-a, conditional on CONFIRMED]: target-aware kick in `sim_capture.py`

**Files:**
- Modify: `mcp_harness/sim_capture.py` (the `SimSession.capture` loadFold seam, ~line 76)
- Modify: `mcp_harness/probe_dog_folds.py` (pin `kick="bridge"` — it exercises the exact product load path; one docstring line)
- Test: `mcp_harness/tests/test_sim_capture_target_kick.py`

**Interfaces:**
- Consumes: Task 1's `target_direction`; `kick_field.out_of_plane_field`; `rigid_fold.null_space_basis`.
- Produces: `SimSession.capture(fold, kick="bridge")` — new keyword. `kick="target"`: if the fold is all-2D AND has `edges_foldAngle` AND the flex-projected target is nonzero (‖P_flex t‖ > 1e-12·‖t‖), post `vertices_coords` as `[x, z_i, y]` (the bridge's y-up lift frame, ide-bridge.js:45) in a COPY of the fold dict, lift = the pinned Global-Constraints formula (max-|z| 2e-4, sign ⟨lift, target z-field⟩ > 0); otherwise send unchanged (bridge hash kick fires as today). `kick="bridge"` (default): always send unchanged. Factor the payload as a pure function `_kicked_payload(fold, kick) -> dict` so tests need no Playwright. The fold argument is never mutated.

**Brief.** The bridge stands down on 3D payloads (its `all2d` guard — the proven seam); nothing in ide-bridge.js changes. The known z-lift gotcha (2e-4 lift breaks `tracked_points` ratio checks) is the reason the lift rides the SAME 2e-4 amplitude and y-up frame the bridge itself uses — `tracked_points_lifted`'s Y-extent guard (1% of X-Z extent) already tolerates it; add the shape test proving it. Do NOT touch `check_capture`/`DISP_GATE`; `sim_capture._anchor_main` pins `kick="bridge"` (its 1.0–1.6 band was recorded under the bridge kick).

- [ ] **Step 1: failing tests:** (1) shaped dog cell in → payload has 3-vectors, `max|y| == 2e-4`, sign check ⟨y-column, target z-field⟩ > 0, x/z columns byte-equal to input x/y, input unmutated; (2) `kick="bridge"` → payload identical to input; (3) fold without `edges_foldAngle` under `kick="target"` → payload identical (fallback); (4) determinism: same fold → same payload; (5) zero-projection synthetic (target orthogonal to flex space, monkeypatched) → fallback.
- [ ] **Step 2: implement; targeted green; full backend suite via nohup (741+new / 4); commit** (`feat(sim-capture): target-aware capture kick behind the all2d seam`).

### Task 4 [K2.1-b, conditional]: `probe_kick_validation.py` + K2 verdict run

**Files:**
- Create: `mcp_harness/probe_kick_validation.py`
- Test: `mcp_harness/tests/test_kick_validation.py`

**Interfaces:**
- Consumes: `probe_dog_coupling._measure(sim, base, targets, shaped, tgt)`, `dog_base()`, `fox_targets_with_fallback()`, `open_session_with_anchor`; `pose_base.unique_targets`; `probe_front_wave` constants (`PARK_RETRIES=3`, `READS_PER_RECIPE=3`) — import, don't copy; `WaveBudget` pattern with cap K2=25 + contingency.
- Produces: `probe_kick_validation.out.json(l)` (uncommitted) with per-cell rows and the gate verdict block.

**Brief.** Controller-run driver, the unbuilt K.2's spec verbatim (structural-remedy plan Task 4 is the reference): session anchor (star-4, `kick="bridge"` — the anchor band predates any new kick) → baseline ×3 (unshaped dog; unshaped has no `edges_foldAngle`, so `kick="target"` falls back to bridge — this is correct and stated in the out.json) → cells ×3 each under `kick="target"`: `front_v18|outside|30|0.5`, `frontpair|outside|142.5|0.35`, `front_v13|outside|30|0.5`, `back_v12|outside|142.5|0.5` (representative parked-site cell, NON-gating). **Pinned gates:** (a) both S0-parked cells (`front_v18|outside|30|0.5`, `frontpair|outside|142.5|0.35`) scored 3/3, zero parks; (b) twin symmetry |ΔF(front_v13)| vs |ΔF(front_v18)| within ±7°; (c) front_v13 ΔF within ±7° of Phase-S's +6.52 AND `probe_dog_folds` exits 0 (driver shells it, costs 1 read). back_v12 outcome reported, non-gating. ~16 planned reads, hard cap 25.

- [ ] **Step 1: failing tests** (sim-free): gate arithmetic on synthetic row sets (pass; fail-(a) park; fail-(b) asymmetry; fail-(c) out-of-band); budget guard trips at 25+contingency.
- [ ] **Step 2: implement; targeted green; commit** (`feat(kick-validation): K2 driver, unbuilt-K.2 gates verbatim`).
- [ ] **Step 3 (CONTROLLER CHECKPOINT — K2 verdict, headed sim, ≤25 reads):** run. All gates PASS → K2 done; M's sim block uses `kick="target"`; rollover unspent to M. Any gate FAIL → M's sim block uses `kick="bridge"` with parked reads recorded as kick-blocked (coverage hole list); do NOT iterate on the kick without a new pinned hypothesis in the ledger.

### Task 5 [M1-a]: `molecule_fixtures.py` — the hand-built molecule ladder

**Files:**
- Create: `mcp_harness/molecule_fixtures.py`
- Test: `mcp_harness/tests/test_molecule_fixtures.py`

**Interfaces:**
- Consumes: `flat_fold.flat_fold(fold)` (closure validation); `rigid_fold.folding_dof`, `null_space_basis`; `flex_extension.assemble`, `kernel_nullspace` (readability checks). Ground truth for constructions: `~/Desktop/TreeMakerSource/Source/tmModel/tmTreeClasses/tmTree.cpp` (molecule build) and `tmPoly.cpp` (`BuildPolyContents` — ridge/hinge crease generation); `mcp_harness/HANDOFF_molecule_topology.md` for the crease-KIND vocabulary (`probe_creasekind.py`, `probe_facets.py` are existing C++-dump diagnostics if a construction question needs engine-side confirmation).
- Produces (exact names; Tasks 6, 12, 13 rely on them):
  - `rabbit_ear(a, b, c) -> dict` — FOLD dict of the triangle universal molecule on triangle paper with corners `a, b, c` (2D coord pairs): axial creases = the triangle sides (paper boundary, `"B"`), ridge creases = the three angle bisectors to the incenter, hinge creases per Lang's construction, M/V assignment matching TreeMaker's molecule output. Must accept BOTH a scalene default (documented in the docstring) and caller-supplied corners.
  - `gusset_quad(corners) -> dict` — the quad (gusset) molecule, same contract.
  - `composite_two(...) -> dict` — two triangle molecules glued along a shared polygon side (the poly-network adjacency TreeMaker itself produces), signature pinned at build time from the construction (documented in the module docstring).
  - `designate_flexes(fold) -> dict[str, np.ndarray]` — named first-order flex directions per fixture (e.g. per-basis-column canonical labels) so Task 6's predictions can reference specific directions.

**Brief.** Fixtures are RAW patterns on their own polygon paper — no `square_complete`, no TreeMaker compile (pure Python, exact coordinates). The construction MUST be derived from Lang's source, not from memory of "the rabbit ear": read `tmPoly::BuildPolyContents`'s ridge/hinge generation and reproduce it for the minimal polygons; where the C++ leaves a choice (e.g. reduced-path markings), document the choice in the docstring with the tmPoly line reference. Validity gates (these are the task's tests, NOT obstruction measurements — dof counts and verdicts are Task 6's predictions and must not be pinned here): every interior vertex satisfies Kawasaki (angle-alternating sum) and Maekawa (|M−V| = 2); `flat_fold` closure report clean on the designated flat fold; `flex_extension.assemble` + `kernel_nullspace` run without refusal (instrument-readable). One symmetric instance (equilateral/square) and one generic instance (scalene) per rung — symmetric degeneracies are exactly the kind of confound the generic instance exists to break.

- [ ] **Step 1: failing tests:** per fixture × {generic, symmetric}: (1) Kawasaki + Maekawa at every interior vertex; (2) `flat_fold` closure clean; (3) `assemble`/`kernel_nullspace` readable (no exception, kernel dimension > 0 — dimension VALUE not pinned); (4) determinism (two calls → identical dicts); (5) `designate_flexes` returns unit vectors in the flex space (‖J w‖ small via kernel residual).
- [ ] **Step 2: implement against tmPoly ground truth; targeted green.**
- [ ] **Step 3: commit** (`feat(molecule-fixtures): hand-built Lang-molecule ladder (rabbit-ear, gusset quad, composite)`).

### Task 6 [M1-b]: the derivation + mechanism note (single large package, derivation-FIRST)

**Files:**
- Create: `docs/superpowers/2026-07-14-molecule-obstruction-mechanism.md` (the mechanism note)
- Modify: `mcp_harness/flex_extension.py` (ADDITIVE ONLY if the derivation needs new observables — e.g. a `cokernel_basis(fold)` / self-stress extraction or a defect-pairing helper; existing functions and constants byte-unchanged; each addition tested)
- Test: `mcp_harness/tests/test_molecule_mechanism.py`

**Interfaces:**
- Consumes: Task 5's fixtures + `designate_flexes`; `flex_extension.second_order_defect`, `per_vertex_defect`, `obstruction_verdict`, `continuation`, `kernel_nullspace`, `anchor_ea`, `degree4_fixture`; the regenerated `structural_search.out.jsonl` (12 completed funnels, ledger evidence); `probe_front_flex.out.json` (dog w\*); Lang source for construction reasons.
- Produces: the mechanism note (committed) + prediction-pinning tests. The note's structure is pinned: §1 the observed lock (dog + 12 funnels, rel = 1.0, carriers v5/v0/v1/v4); §2 the mechanism claim (WHY Q(w,w) ∉ range(J), tied to the universal-molecule CONSTRUCTION — bisector/ridge/gusset structure per tmPoly, not merely to observed numbers); §3 the ladder table — per rung: prediction (written BEFORE measurement, with ledger timestamp), measurement, verdict; §4 what would break the lock (the remedy-facing conclusions that pin Task 12's move vocabulary); §5 scope honesty (dog-class claim; what is and is not established about generality).

**Brief.** This is the capability-spend package; one mind holds the whole derivation. Working sequence (checkpoint each stage to the SDD ledger AS YOU GO — the Phase-S salvage lesson): (0) regenerate and study `per_vertex_defect` on the served dog; extract the cokernel (left null space of the assembled J) and localize which constraint rows carry the defect pairing — small additive helpers to `flex_extension` are allowed here, tested, existing API untouched; (1) study `tmPoly::BuildPolyContents` for the cone-vertex crease structure the molecule builds (why deg-6 at v5-class vertices; which creases are ridge vs hinge); (2) for ladder rung 1 (rabbit ear): derive the kernel dimension and the second-order behavior of each designated flex analytically; WRITE THE PREDICTIONS TO THE LEDGER; only then run the instrument; a misprediction is DATA — revise the account, re-derive, and the revised prediction must then hold on rung 2 without further revision to count toward the gate; (3) rungs 2 (gusset quad) and 3 (composite) same discipline; (4) dog confirmation: from the mechanism, predict a FEATURE of the dog's defect localization or cokernel structure that was not used to build the account (out-of-sample), verify it; (5) write the note; port every prediction table into `test_molecule_mechanism.py` as pinned assertions (fixture in → measured dim/verdict/defect-carrier set == the note's table).

**M1 gate (pinned):** predictions verified on ≥2 independent fixtures (two ladder rungs with distinct topology count; the two instances of ONE rung do not). Honest endings: (a) account verified → proceed to Task 12 with §4's vocabulary; (b) the mechanism proves the lock inherent to ALL Lang-molecule patterns of the class → theorem-sketch in the note, SKIP Tasks 12–15's remedy work that the theorem rules out, route the body-plan/design charter (remedies NOT built to fail); (c) predictions keep failing → the note documents predicted-vs-measured honestly, M2 proceeds empirically with the mechanism hole named.

- [ ] **Step 0: ledger scaffold** — open a derivation section in the task report/ledger; every prediction gets a timestamped entry BEFORE its check.
- [ ] **Step 1: dog + cokernel study** (additive `flex_extension` helpers + their failing-then-green tests if needed; commit separately: `feat(flex-extension): additive cokernel/defect-pairing observables`).
- [ ] **Step 2: rung-1 predictions → measure → reconcile** (ledger).
- [ ] **Step 3: rung-2 + rung-3 predictions → measure → reconcile** (ledger).
- [ ] **Step 4: out-of-sample dog prediction → verify** (ledger).
- [ ] **Step 5: write the note; port prediction tables to `test_molecule_mechanism.py`; targeted green.**
- [ ] **Step 6: commit** (`docs(molecule-mechanism): mechanism note + prediction-pinning tests`) — reviewer gate on the whole package (note + tests + any flex_extension additions).

### Task 7 [H-a]: `fold_registry.py` — file-backed shared fold store

**Files:**
- Create: `mcp_harness/fold_registry.py`
- Test: `mcp_harness/tests/test_fold_registry.py`

**Interfaces:**
- Produces (Tasks 8–9 rely on these exact names):
  - `register(fold: dict | str) -> str` — parses str input as JSON; writes `<hash>.json` (the canonical JSON bytes) into the store dir; returns `"fold:<12hex>"`. Idempotent (same content → same handle, file rewritten harmlessly). Evicts oldest-mtime files beyond cap 32 AFTER writing.
  - `resolve(handle: str) -> dict` — validates prefix/format, reads the file, re-hashes content and compares to the handle (mismatch or missing → `FoldRegistryError` with the handle named in the message).
  - `resolve_fold_arg(fold_handle: str | None, fold_json_string: str | None) -> dict` — the handle-wins rule in one place: handle present → `resolve` (errors propagate as `FoldRegistryError`); else JSON string present → parse; neither → `FoldRegistryError("no fold provided")`.
  - `FoldRegistryError(ValueError)`; constants `HANDLE_PREFIX = "fold:"`, `CAP = 32`, `ENV_VAR = "IDE_FOLD_REGISTRY_DIR"`.

**Brief.** Store dir per Global Constraints (env override → tempdir default), created lazily with `os.makedirs(exist_ok=True)`. Cross-process is the WHOLE POINT (the spec amendment): `server.py` and `linter_server.py` are separate processes sharing only this directory. Canonicalization runs on the PARSED dict, so formatting differences in the input string do not fork handles. No locks needed: content-addressed writes are last-writer-wins on identical bytes; eviction races degrade to `FoldRegistryError` on resolve, which every caller surfaces as a clear tool error (the agent falls back to `fold_json_string`).

- [ ] **Step 1: failing tests** (use `monkeypatch.setenv(ENV_VAR, tmp_path)`): (1) round-trip register→resolve; (2) idempotency (two registers → same handle, one file); (3) formatting-invariance (same dict, differently-formatted JSON strings → same handle); (4) handle-wins + neither-arg error in `resolve_fold_arg`; (5) unknown handle → `FoldRegistryError` naming the handle; (6) tamper detection (edit the file bytes → resolve raises); (7) eviction: register 33 distinct folds → 32 files remain, the oldest-mtime one gone; (8) cross-process smoke: `subprocess.run([sys.executable, "-c", ...])` resolving a handle registered by the test process (env passed through).
- [ ] **Step 2: implement; targeted green; commit** (`feat(fold-registry): content-addressed file-backed fold handles`).

### Task 8 [H-b]: handle wiring in both servers + SYSTEM_PROMPT contract

**Files:**
- Modify: `mcp_harness/server.py` (fold-returning tools: `draft_and_compile_full_base`, `compile_base`, `convert_tmd_to_fold`, `apply_shaping_ops` — verify the exact envelope-assembly sites by grepping the return construction; fold-accepting tool: `suggest_pose_stack` gains `fold_handle: str = ""`)
- Modify: `mcp_harness/linter_server.py` (`validate_flat_foldability(fold_json_string: str = "", fold_handle: str = "")`)
- Modify: `mcp_harness/agent_loop.py` (SYSTEM_PROMPT: prefer handles)
- Test: `mcp_harness/tests/test_fold_handles.py`, extend the SYSTEM_PROMPT pin test (pattern: `tests/test_agent_shaping_prompt.py`)

**Interfaces:**
- Produces: every enumerated fold-returning tool's result JSON envelope gains `"fold_handle": "<handle>"` NEXT TO its existing fold payload key — the payload itself is byte-unchanged and the handle key NEVER goes inside the FOLD dict (provenance pin). Every enumerated fold-accepting tool: `fold_handle` wins when non-empty; resolution failure → the tool returns its normal error-string shape naming the handle and telling the agent to re-send `fold_json_string`; empty handle + present JSON string → identical behavior to today (backward compat).
- SYSTEM_PROMPT contract (pin-tested): when a tool result carries `fold_handle`, later tool calls pass `fold_handle` instead of echoing the FOLD JSON; `fold_json_string` remains valid.

**Brief.** Registration lives where the envelope is assembled (server-side, after the fold is final — for `_compile_with_perturb`-based tools that's the served/annotated string). `linter_server` registers nothing; it only resolves (import `fold_registry` there too — the shared directory is the bridge). Keep `linter_server._normalize_for_foldability` downstream of resolution so handle-provided folds go through the identical lint pipeline. Mind the history-trimming interplay: `_trim_consumed_blobs` keys on blob size — handles are tiny and never trimmed; no agent_loop logic change beyond the prompt text.

- [ ] **Step 1: failing tests:** (1) compile-tool result envelope carries `fold_handle` and the embedded FOLD dict does NOT contain any handle key (provenance pin); (2) `validate_flat_foldability(fold_handle=h)` on a registered known-good fold → same verdict string as the `fold_json_string` path (byte-equal); (3) handle-wins: both args given, garbage JSON string + valid handle → handle's verdict; (4) unknown handle → error string naming the handle, no exception escape; (5) backward compat: `fold_json_string`-only call byte-identical to pre-change behavior (pin against a golden verdict); (6) `suggest_pose_stack(fold_handle=...)` parity with its `fold_json_string` path on the dog golden; (7) SYSTEM_PROMPT pins: prefer-handle instruction present + the existing shaping/oracle contract phrases unchanged.
- [ ] **Step 2: implement; targeted green; full backend suite via nohup (all existing green + new); web suite green (59); commit** (`feat(fold-handles): registry wiring in both servers + prompt contract`).

### Task 9 (CONTROLLER — H live demo, headed, ≤5 reads)

- [ ] `LLM_PROVIDER=groq LLM_MODEL=meta-llama/llama-4-scout-17b-16e-instruct` live agent session: compile a dog → lint via `fold_handle` (expected verdict: hull-frontier ACCEPT — 4–10 geometry violations, 0 M/V-fixable, agent proceeds per taught lore) → `suggest_pose_stack` (tree_nodes passed, node_id resolved) → confirm → posed dog renders in Model tab → `[STRAIN ORACLE]` verdict loop closes. Record the transcript path in the ledger.
- [ ] Carried gotchas: web chat's first send after page load can race the websocket (re-send); scout is the only free-tier fit; TPM backoff is built in; stdin python can't parent spawn workers (drive via real files).
- [ ] **H verdict:** demo PASS + suites green + provenance pins green → **H ships** (regardless of K2/M outcomes). Demo failure that is NOT blob-echo → document root cause; H's code gates already passed, the demo blocker is named in the handoff.

### Task 10 [M2-a]: `tip_mobility.py` — generalized selectivity instrument + calibration probe

**Files:**
- Create: `mcp_harness/tip_mobility.py`
- Create: `mcp_harness/probe_tip_mobility_calibration.py` (thin controller CLI)
- Test: `mcp_harness/tests/test_tip_mobility.py`

**Interfaces:**
- Consumes (do not modify): `rigid_fold.null_space_basis`, `rigid_fold.tip_flex_velocity(fold, creases, d, vids, h)`, `rigid_fold.front_selectivity(signatures, front, back, head, basis) -> SelectivityResult`, `rigid_fold.FlexInstrumentError`; `structural_search.compile_candidate`, `coarse_grid` (calibration probe only); the regenerated `structural_search.out.jsonl`.
- Produces (Tasks 12, 13, 15 rely on these exact names):
  - `role_tip_groups(sq, leaf_xy, roles) -> tuple[list, list, int, int | None]` — `(fronts, backs, head, tail)` squared-fold vertex ids via 8dp xy-match of tree leaf locations (reference: `probe_front_flex.sq_vertex_index`; role validation mirrors `structural_search._tip_groups_sq`: exactly 1 head, ≥1 front and back, ≤1 tail — NO hub logic).
  - `quotient_signatures(fold, creases, basis, tip_vids) -> list[dict]` — one `{tip_vid: quotiented z-velocity}` per basis column: absolute z-velocities at ALL vertices at both step sizes with the same agreement guard semantics as `rigid_fold.tip_flex_signatures` (raise `FlexInstrumentError` on disagreement), then subtract the least-squares affine field z = a + bx + cy fitted over ALL vertices, evaluated at each tip.
  - `mobility_selectivity(fold, fronts, backs, head) -> SelectivityResult` — full pipeline ending in the imported `front_selectivity` (r\*_q and `w_creases` come out of the same dataclass).
- Calibration probe CLI: reads the coarse ledger, recompiles the 12 completed-funnel candidates by cand_id (via `coarse_grid()` lookup + `compile_candidate`), adds the served dog, emits `probe_tip_mobility_calibration.out.json` (uncommitted) with per-candidate `(r_star_D1_from_ledger, r_star_q, verdict_agree)` plus readability rows for ≥1 flap-family compile (dof 7–17) and ≥1 headmid variant (dof 9) — iterate the generator's flap/headmid candidates until one compiles (the T run proved ≥3 flap compiles exist).

**Brief.** The quotient is the design's load-bearing move: absolute z-velocities depend on the root-face gauge (`_build_face_graph` fixes a face), and changing that gauge composes an infinitesimal out-of-plane rigid motion — exactly an affine z-field. Subtracting the all-vertex affine fit removes the gauge exactly at first order, with no topology identification anywhere. Signatures are per-tip ABSOLUTE-quotiented (no bone/hub convention) — r\*_q values therefore differ from D1's; only the r\* ≥ 1.0 VERDICT is comparable, which is what the calibration gate checks. Module docstring must state the contract (fold + role groups in, SelectivityResult out; refuses only on genuine degeneracy) and the D1 contrast.

- [ ] **Step 1: failing tests** (sim-free): (1) gauge-injection: hand-add an exact affine field to the velocity dicts (monkeypatch `tip_flex_velocity`'s return) → quotiented signatures unchanged to 1e-12; (2) degree-4 fixture with designated front/back tips → r\*_q finite and `SelectivityResult` well-formed; (3) served dog + DOG roles (`needs_flex_json`-guarded or direct compute): r\*_q ≥ 1.0 verdict agrees with the pinned D1 r\* 1.76272 ≥ 1.0; (4) degenerate path: all-tip signatures ~0 → `FlexInstrumentError` propagates (monkeypatch); (5) `role_tip_groups` role validation errors (2 heads / 0 fronts) raise `ValueError`; (6) REAL flap-family compile (slow-ok, seconds): `mobility_selectivity` returns finite r\*_q — the previously-refused geometry is readable.
- [ ] **Step 2: implement; targeted green; commit** (`feat(tip-mobility): rigid-motion-quotient selectivity instrument + calibration probe`).
- [ ] **Step 3 (CONTROLLER CHECKPOINT — calibration gate):** run `probe_tip_mobility_calibration.py`. **Gate:** 13/13 verdict agreement AND flap+headmid readability. PASS → r\*_q ≥ 1.0 is live as the stage-1 remedy bar. FAIL → HALT the gate definition; the disagreement table IS the calibration finding — bring it to the user before any remedy gating.

### Task 11 (CONTROLLER — M1 routing checkpoint)

- [ ] With the mechanism note landed (Task 6) and the instrument calibrated (Task 10): route per the note's §4/§5. Ending (a) verified account → pin Task 12's move vocabulary from §4 (≤3 move families, each with a ledgered predicted effect). Ending (b) lock-inherent theorem-sketch → SKIP Tasks 12–15 for the families the theorem rules out; if it rules out ALL of a+d, route the body-plan/design charter and jump to Task 16. Ending (c) mechanism hole → default vocabulary below stands, flagged empirical.
- [ ] Default vocabulary if (c): (i) cone-vertex ridge split (convert a deg-6 carrier into two deg-4 vertices by inserting a short crease pair along the ridge); (ii) hinge-diagonal insertion in the faces adjacent to a carrier (adds kernel directions local to the defect support); (iii) front-region degree-4 overlay (a twist-like patch manufacturing an independent extending DOF). These defaults are PLACEHOLDER-BREAKERS only — ending (a) replaces them with mechanism-derived moves.

### Task 12 [M2-b]: `crease_augment.py` — pure augmentation library

**Files:**
- Create: `mcp_harness/crease_augment.py`
- Test: `mcp_harness/tests/test_crease_augment.py`

**Interfaces:**
- Consumes: the Task-11 pinned move vocabulary; `probe_front_flex.served_dog()` (the reference squared base); `rigid_fold.folding_dof` (readability check).
- Produces (Task 13 relies on these):
  - `AugmentMove` dataclass — `kind: str` (one of the ≤3 pinned move-family names), `params: dict` (site vertex id + family-specific knobs, documented per family).
  - `augment(sq: dict, move: AugmentMove) -> dict` — pure; returns a NEW fold dict with real added vertices/edges (and M/V assignments for added creases); input never mutated; original vertex indices preserved (append-only) so site keys on the base remain valid.
  - `enumerate_moves(sq, per_vertex_defect_rows) -> list[AugmentMove]` — the bounded move menu targeted at the defect carriers (cap documented in the docstring, ≤ ~12 total across the ≤3 families).
  - `validate_augmented(fold) -> None` — structural sanity (edge/face arrays consistent, planar faces, no duplicate vertices at 8dp) — raises `ValueError` on breakage. Flat-foldability of the augmented pattern is NOT required (added creases may function as unfolded hinges; stage-2 and the sim adjudicate physical validity).

**Brief.** Research-artifacts-only provenance (spec §4): this library's outputs never touch `web/server.py` or the raw-fold/display chain; they feed instruments and `sim_capture` directly. Keep each move family a small pure function; `augment` dispatches. Added creases carry `edges_foldAngle` 0 when the base has that array (hinges, not folds).

- [ ] **Step 1: failing tests:** (1) per pinned family on the served dog: `augment` returns a structurally valid dict (`validate_augmented` passes), input unmutated, original vertices index-stable; (2) added creases are M/V with foldAngle 0; (3) `enumerate_moves` respects the cap and targets carrier vertices (feed it a synthetic defect table naming v5); (4) `folding_dof` on an augmented dog runs (dof value NOT pinned — it is a measurement); (5) determinism.
- [ ] **Step 2: implement; targeted green; commit** (`feat(crease-augment): pinned move families as pure fold augmentation`).

### Task 13 [M2-c]: `mobility_search.py` — the a+d remedy funnel (sim-free)

**Files:**
- Create: `mcp_harness/mobility_search.py`
- Test: `mcp_harness/tests/test_mobility_search.py`

**Interfaces:**
- Consumes: `crease_augment.enumerate_moves/augment/validate_augmented`; `structural_search.compile_candidate` (spawn compile; import, don't copy); `square_complete.complete_square`; `tip_mobility.role_tip_groups/mobility_selectivity`; `flex_extension.obstruction_verdict`; `probe_front_flex.served_dog`; `benchmark_templates.quadruped` (tree-shape reference for the hub family).
- Produces: `run(ledger_path) -> SearchSummary`; CLI `python mobility_search.py` writing `mobility_search.out.jsonl` (uncommitted; one line per candidate report + summary block). Candidate report fields: `cand_id, family  # augment|hubsplit, status  # pass|stage1_fail|stage2_fail|refused|compile_failed|gate_blocked|analysis_error, r_star_q, verdict, rel_fine, rel_coarse, notes`.
- Candidate sets (pinned): **augment family** = `enumerate_moves` over the served dog's defect carriers (≤ ~12); **hubsplit family** = ≤6 instances of ONE topology: the quadruped tree with the front hub split into two adjacent spine nodes (front_left on hub1a, front_right on hub1b, head on hub1a, hub1a–hub1b edge length ∈ {0.2, 0.4}, front-leg length ∈ {1.0, 0.85}, designed node order only; roles carried per leaf). Tier-2.5 gate shields hubsplit compiles exactly as `structural_search` does.

**Brief.** Funnel per candidate, nothing raises across the boundary (search survives any candidate): build (augment on the squared dog / compile+square for hubsplit) → `role_tip_groups` (dog roles are known; hubsplit roles come from the generator) → stage-1 `mobility_selectivity` (r\*_q < 1.0 → stage1_fail) → stage-2 `obstruction_verdict(fold, sel.w_creases)` (NON_EXTENDING → stage2_fail; REFUSED → refused; EXTENDING → **pass**). Run `flex_extension.continuation` corroboration on every passer (verdict_hint in notes). For augmented-dog candidates the fold passed to stage-2 is the augmented SQUARED dog (already square); for hubsplit it is the squared compile.

- [ ] **Step 1: failing tests:** (1) funnel status routing on monkeypatched stages (each terminal status reachable, no exception escape); (2) hubsplit generator: ≤6 candidates, well-formed trees (roles for every leaf, symmetric front pair), deterministic; (3) ledger JSONL round-trips; (4) REAL smoke (slow-ok): one augment candidate flows to a definite status with finite fields — status VALUE not pinned (it is a measurement).
- [ ] **Step 2: implement; targeted green; full backend suite via nohup; commit** (`feat(mobility-search): a+d remedy funnel over tip_mobility + obstruction_verdict`).

### Task 14 (CONTROLLER — M2 search run + SEARCH CHECKPOINT, sim-free)

- [ ] `cd mcp_harness && nohup .venv/bin/python mobility_search.py > mobility_search.log 2>&1 &`; poll.
- [ ] **Checkpoint outcomes (pinned):** ≥1 passer → Task 15 with the top ≤3 passers ranked (rel_fine asc, r\*_q desc). Zero passers across BOTH families → the named **instrument-vs-construction boundary** ending: record per-family funnels + the boundary statement in the ledger, skip Task 15, route per spec §6. If (b)-theorem already fired at Task 11, this task never runs.
- [ ] Family (b) (non-square paper) fires ONLY here and only if the mechanism note implicated the square boundary AND both a+d refused — bring the concrete (b) proposal to the user first (scope gate; it was chartered conditional).

### Task 15 [M2-d]: `probe_mobility_confirm.py` — sim CONFIRM driver (fires only on passers)

**Files:**
- Create: `mcp_harness/probe_mobility_confirm.py`
- Test: `mcp_harness/tests/test_mobility_confirm.py`

**Interfaces:**
- Consumes: the passer candidates (rebuild for freshness: re-augment / recompile, assert ledger geometry match); `probe_dog_coupling._measure`, `fox_targets_with_fallback`, `open_session_with_anchor`; `pose_pregate.pregate_recipe/rank_menu` (op menu ranking on the NEW base); `pose_base.NamedBase` where naming succeeds, else role-derived Sites from `leaf_xy` + roles (numbering is base-relative; augmented dogs keep original indices by Task 12's append-only pin); `WaveBudget` cap = M 40 (+K2 rollover); `sim_capture` kick mode per Task 4's verdict.
- Produces: `probe_mobility_confirm.out.json(l)` (uncommitted): per-passer baseline rows, menu, reads, CONFIRM verdicts, kick-blocked list (if K2 failed).

**Brief.** Per passer (≤3, cap 12 reads each): session anchor (star-4, `kick="bridge"`) → fresh baseline ×3 on the NEW unshaped base → pregate-ranked front-site menu (families from `probe_front_wave.pinned_menu` semantics: front-tip `outside` θ∈{30, 105, 142.5} × frac {0.35, 0.5} + front-pair atomic recipes; top 3 ranked cells get 1 read each) → best first-read cell tops up ×2 → **CONFIRM iff mean ΔF of the ×3 ≥ +20° toward 134.83.** Augmented-dog passers additionally assert `probe_dog_folds`-style displacement > 0 on the base capture before any op read (flat-equilibrium tripwire — augmented hinges must not re-park the base). Kick discipline: K2 PASSED → `kick="target"` everywhere; K2 FAILED/FALSIFIED → `kick="bridge"`, parked reads recorded kick-blocked and the cell skipped.

- [ ] **Step 1: failing tests** (sim-free): budget/cap arithmetic; CONFIRM verdict arithmetic on synthetic rows; role-derived Site construction parity on the dog golden (reproduces `NamedBase` fronts/backs/head grouping).
- [ ] **Step 2: implement; targeted green; commit** (`feat(mobility-confirm): M2 sim CONFIRM driver`).
- [ ] **Step 3 (CONTROLLER CHECKPOINT — M verdict, headed sim, ≤40 reads + rollover):** run per Task-14 ranking. Outcomes (pinned): CONFIRM → **headline** (follow-up: pose-search-on-mobile-base + serve-side augmentation seam). All passers sim-refuse → instrument-vs-reality calibration finding — document, do not force.

### Task 16 (CONTROLLER — slice end)

- [ ] Handoff doc `docs/superpowers/2026-07-14-handoff-molecule-mobility-outcome.md`: verdict per lane; read ledger vs the 90 grant; K2.0 alignment table; M1 prediction/measurement tables + the note's routing; calibration table (Task 10); M2 funnel coverage + verdicts; H demo transcript; routing verdict naming the follow-up for EVERY outcome (spec §6); deferred minors from task reviews (seed with the structural-remedy §5 list where still relevant).
- [ ] Final suites (backend nohup + web 59); update memory files; single PR from `feat/molecule-mobility` (ask before push; human merges).

## Self-check ordering rules (carried)

- Task 2's checkpoint gates Tasks 3–4 (conditional). Tasks 5–8 are independent of K2's verdict and may interleave; Task 9 (H demo) needs Task 8 only. Task 10's calibration gates Tasks 13–15's stage-1 semantics. Task 11 (M1 routing) gates Task 12's vocabulary and may SKIP Tasks 12–15 (theorem ending). Task 14 gates Task 15.
- Sim blocks strictly serial and controller-only: Task 4 → Task 15 (Task 9's demo is headed but read-light and may run at any natural break after Task 8).
- Checkpoint every long derivation/investigation to the SDD ledger as it goes (Phase-S lesson: salvage came from transcripts).
- Honest-outcome rule: every lane's refusal path is a valid ending; pin gates BEFORE measuring, always.
