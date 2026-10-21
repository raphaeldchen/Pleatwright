# Structural Remedy Implementation Plan (K / T / P / 0)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Sizing note (pinned at kickoff):** tasks carry judgment-bearing prose
> briefs, not verbatim code. Implementers own the how; reviewers verify
> against the pinned gates and the spec
> (`docs/superpowers/specs/2026-07-13-structural-remedy-design.md`).

**Goal:** Make the kick deterministic where it now parks (K), find a Metric-Tree/compile intervention whose compiled+squared output has a *finitely extending* front-selective flex and prove it in the sim (T), and ship the best-known pose stack through the agent HITL flow (P) — with Phase 0 (first ubuntu CI run) if Actions billing allows.

**Architecture:** One new first-order kinematics helper (`kick_field.py`: flex→out-of-plane vertex field, bridge-hash reproduction, canonical kick combination), a capture-harness kick seam in `sim_capture.py` (bridge untouched — its `all2d` guard stands down on 3D payloads), one promoted stage-2 library (`flex_extension.py`: τ-gauge + artifact-aware assembly + second-order obstruction + continuation, anchored and refusing on drift), one sim-free search driver (`structural_search.py`: generators × funnel × ledger with early exit), two capture drivers (`probe_kick_validation.py`, `probe_structural_confirm.py`), and one agent-side HITL tool (`suggest_pose_stack`). `rigid_fold.py`, `rigid/`, `shaping*.py`, `square_complete.py`, and the ide-bridge are untouched.

**Tech Stack:** Python 3 in `mcp_harness/.venv`, numpy only (no new deps), pytest; spawn-isolated `headless_treemaker` compiles (no GPU); headed `SimSession` for captures — controller-run only; Groq (`llama-4-scout`) for the P demo.

## Global Constraints

- **Budget: 150 reads = K 25 / T 90 / P 15 / shared contingency 20.** Rollover K→T at K's end; unspent T rolls to contingency, never to unpinned exploration. A read = one measure-attempt (baselines, ×3 confirms, park retries all count). Hard guard, `BudgetExhausted` pattern from `probe_front_wave.WaveBudget`.
- **Pinned anchors (STOP the slice on drift):** unshaped dog r\* = **1.76272**, captured = **0.904**, dof **3** / rank **35** / creases **38**; coupling reconcile **162 = 114/12/36/0**; `probe_flex_extension` verdict **NON-EXTENDING** with anchor PASS (degree-4 first-order dof 2 → finite dof 1; extending defect ~**1.6e-8** vs phantom **0.336**); local suite **668 passed / 4 skipped** + web **40**.
- **Pinned decision constants (this plan; do not tune):**
  - K.0 separation gate: parked twin's projection fraction < **1/3 ×** scored twin's, on EVERY gated pair; any parked pattern with dof 0 → FALSIFIED.
  - Kick: canonical-sign **sum of all null-space basis z-fields**, normalized to max-|z| = **2e-4** (measurement-integrity rationale: NOT front-seeded); dof-0 fallback = send 2D unchanged (bridge hash kick).
  - Stage-2 gate: `STAGE2_REL_TOL = 1e-4` — EXTENDING-grade iff rel defect < τ at **both** h = 1e-3 and 1e-4; NON-EXTENDING iff both > τ; split verdicts → `REFUSED(h-unstable)`. `q_norm < 1e-10` → extending-grade with note. Stage-1 bar: r\* ≥ **1.0**.
  - T search: coarse grid ~**150** candidates (≈25 primaries × 6 variants), refinement ≤ **100** compiles, **early exit at 3 distinct passers** (distinct = different primary family or different primary knob cell; multiplier-only variants are the SAME candidate — best graduates).
  - T sim: fresh baseline ×3 per new base; **CONFIRM = front ≥ +20° toward 134.83, mean of 3**; payoff (CONFIRM only) = whole-pose ≤ **104** ×3. Per-passer cap 15 reads.
  - ±7° drift band; any < 10° comparison needs ×3 + same-session baseline.
- **Never re-measure a terminal gate-1 cell** (novelty vs `CouplingTable.resume_keys()`), except the FOUR cells this plan's K gates explicitly name.
- **Controller-only for ANY headed-sim run** (subagent sim processes get orphan-killed). Full suites and the search run via `nohup ... > log 2>&1 &` + log-poll, never bare foreground.
- Probe outputs (`*.out.json/.jsonl/.log`) and suite logs stay **uncommitted** — never `git add -A`. Artifact-dependent tests carry `needs_flex_json`-style skipif guards (pattern: `tests/test_flex_extension.py:65`).
- Do NOT modify: `mcp_harness/rigid_fold.py`, `mcp_harness/rigid/`\*, `mcp_harness/shaping*.py`, `mcp_harness/square_complete.py`, `web/frontend/public/simulator/js/ide-bridge.js`. Never import from unmerged Codex branches (`codex/rigid-origami-phase-2-topology-fold` = 5 unmerged commits at kickoff; re-check `git log origin/main..` at T-1 build time; consume only `rigid/kinematics/closure.py` as merged).
- Test command: `cd mcp_harness && .venv/bin/python -m pytest tests/<file> -q` (targeted); backend full suite ~10 min via nohup; web suite per `web/frontend/package.json` (baseline 40).
- Branch `feat/structural-remedy`, single PR at slice end. Ask before push; human merges.

## Environment preflight (controller, before any task review gate)

- [ ] Copy into this worktree (Phase-D recipe): `.venv` symlink, `headless_treemaker*.so`, `oriedita/*.jar`, `OrieditaValidator.class`, `web/frontend/dist`, and `cp <repo>/mcp_harness/probe_dog_coupling.out.jsonl mcp_harness/` (read-only source; also mirrored in `.claude/worktrees/peaceful-herschel-d5c5bf/mcp_harness/`).
- [ ] `cd mcp_harness && .venv/bin/python probe_front_flex.py` — expect exit 0, r\* 1.76272, captured 0.904, tallies 114/12/36/0. Drift → STOP.
- [ ] `cd mcp_harness && .venv/bin/python probe_flex_extension.py` — expect anchor PASS + VERDICT NON-EXTENDING. Drift → STOP.
- [ ] Baseline suite run (nohup + poll): expect 668 passed / 4 skipped; web 40.

## Phase 0 (controller, conditional, ~30 min hard box)

- [ ] `gh run list --branch main --limit 5` — if Actions is still billing-blocked (API error / no runs startable), record one line for the handoff and SKIP.
- [ ] If unblocked: re-run the latest main workflow (`gh run rerun <id>` or trigger via `gh workflow run`). Expected: **664 passed / 8 skipped** + web 40 on ubuntu.
- [ ] If mesh-snapshot tests drift (~1e-3 cross-arch): re-bless deliberately per the PR #41 body (`make bless` on Linux), commit ONLY the snapshot regeneration on a `ci/` branch, labeled as such — separate PR, not this slice's.

---

### Task 1 [K.0-a]: `kick_field.py` — flex→z-field primitive + bridge-hash reproduction + canonical kick

**Files:**
- Create: `mcp_harness/kick_field.py`
- Test: `mcp_harness/tests/test_kick_field.py`

**Interfaces:**
- Consumes (do not modify): `rigid_fold._build_face_graph(fold) -> _FaceGraph` (`.faces`, `.adj`, `.tree` (fa, fb, key) with fb the child, `.root`, `.V3`, `.shared`), `rigid_fold.null_space_basis(fold) -> (creases, basis[E×dof], DofResult)`.
- Produces (Tasks 2, 3 rely on these exact names):
  - `out_of_plane_field(fold, creases, w) -> np.ndarray  # (n_verts,) z-velocities` — first-order out-of-plane vertex field of crease-rate flex `w` (rigid_fold ρ-convention, same crease order as `creases`).
  - `bridge_hash_kick(n_verts) -> np.ndarray  # (n_verts,)` — the EXACT ide-bridge vector: `h = (((i+1) * 2654435761) % 2**32) / 2**32; z = 2e-4 * (2h - 1)`.
  - `flex_kick(fold) -> np.ndarray | None` — canonical-sign sum of all basis z-fields normalized to max-|z| = 2e-4; `None` iff dof 0 (caller falls back to 2D send). Deterministic per fold.

**Brief.** The field: root face has z ≡ 0; walk the BFS face tree (`g.tree` edges, parent→child); crossing crease c (line through V2[a]→V2[b], a<b sorted, rate w_c in rigid_fold's ρ-about-low→high-axis convention) adds to every vertex p of the child subtree's faces the increment `±w_c × signed_dist(p, line_c)` — derive the sign once from rigid_fold's tree-child rotation convention (its OWNERSHIP NOTE ~line 47 and `_crease_params`/`fold_to_3d` are the reference; validate against the analytic degree-4 rather than trusting a re-derivation). Accumulate per-face offsets along the tree (each face's z is affine over the face: z(p) = α + β·p; store (α, β) per face, evaluate at vertices; vertices shared by faces must agree — that's the test). Canonical sign per basis column: flip the z-field so its largest-|entry| is positive (tie: lowest vertex index among maximal entries). Sum, guard degenerate sum (‖·‖∞ < 1e-12 × max column norm → use first column's field), normalize.

- [ ] **Step 1: failing tests** (all sim-free): (1) degree-4 fixture (copy `probe_flex_extension.degree4_fixture()` shape into the test, or import it): field of each basis flex is nonzero, exactly affine per face (assert per-face plane fit residual < 1e-12), and vertices shared across faces agree; (2) served dog (`probe_front_flex.served_dog()[1]`): dof-3 basis → 3 fields, all faces planar to first order, field ≠ 0; (3) `bridge_hash_kick(24)` matches a hand-computed triple of entries (compute the i=0,1,23 values in the test from the formula — pins against ide-bridge.js:44-45 drift); (4) `flex_kick` determinism: two calls → identical arrays; max-|z| == 2e-4; (5) dof-0 case → `None` (build a trivially rigid fold: single face, no M/V creases).
- [ ] **Step 2: implement**; run targeted tests to green.
- [ ] **Step 3: probe-before-pinning sanity** (uncommitted): print the mirror behavior — `flex_kick` on the dog vs the dog reflected through the diagonal (pose_base `_diag`); fields should be mirror-related in magnitude pattern. Record in the task report (informs K.2's twin-symmetry expectations; not a gate).
- [ ] **Step 4: commit** (`feat(kick-field): first-order out-of-plane field + deterministic flex kick`).

### Task 2 [K.0-b]: `probe_kick_projection.py` — the falsification probe

**Files:**
- Create: `mcp_harness/probe_kick_projection.py`
- Test: `mcp_harness/tests/test_kick_projection.py`

**Interfaces:**
- Consumes: Task 1's three functions; `pose_base.NamedBase(raw, sq, DOG_CONFIG)`, `.site_op(key, kind, theta, frac)`, `.apply_strict(ops)`; `probe_front_flex.served_dog()`; `rigid_fold.null_space_basis`.
- Produces: `projection_fraction(shaped) -> dict` with keys `frac` (‖P_span(hash)‖/‖hash‖ over the orthonormalized span of ALL basis z-fields), `dof`, `n_verts`; probe writes `probe_kick_projection.out.json` (uncommitted).

**Brief.** Pinned cells (constants in the probe, cited to the Phase-S handoff §3 and the coupling table): **gated twin pairs** — (`back_v12` vs `back_v16`) × {`outside|142.5|0.5`, `reverse|105|0.5`, `outside|60|0.5`} and (`front_v18` vs `front_v13`) × {`outside|30|0.5`} — parked site listed first; **non-gating comparators** — `frontpair|outside|142.5|0.35` (parked, ops = `site_op(front_v13,…) + site_op(front_v18,…)`) vs `frontpair|outside|105|0.35` (scored). For each cell: strict-apply, compute z-fields of the shaped pattern's full flex basis, orthonormalize (QR), project `bridge_hash_kick(n_verts)`, report the fraction. **Pinned verdict (§ Global Constraints):** CONFIRMED iff every gated parked cell's `frac` < 1/3 × its scored twin's `frac` AND all parked cells have dof ≥ 1; otherwise FALSIFIED. Probe prints a verdict line and per-cell table; exit 0 CONFIRMED / 1 FALSIFIED / 2 REFUSED (an op refuses to apply — should not happen, these cells all applied in gate 1).

- [ ] **Step 1: failing tests** (sim-free, no verdict-dependence): (1) `projection_fraction` on the unshaped dog returns 0 ≤ frac ≤ 1 and dof 3; (2) verdict arithmetic unit-tested on synthetic fraction tables (CONFIRMED case, FALSIFIED-by-separation case, FALSIFIED-by-dof-0 case); (3) the pinned cell list matches the constants above (drift tripwire).
- [ ] **Step 2: implement; targeted tests green; commit** (`feat(kick-projection): K.0 falsification probe`).
- [ ] **Step 3 (CONTROLLER CHECKPOINT — K.0 gate):** run the probe. CONFIRMED → proceed to Task 3. FALSIFIED → STOP the K build; K-fail routing activates (T validation on non-kick-blocked reads only; hole flagged); report the measured fractions in the ledger either way.

### Task 3 [K.1]: capture-harness flex kick in `sim_capture.py`

**Files:**
- Modify: `mcp_harness/sim_capture.py` (the `SimSession.capture` seam, ~line 76)
- Modify: `mcp_harness/probe_dog_folds.py` (pin `kick="bridge"` — it exercises the exact product load path; one docstring line)
- Test: `mcp_harness/tests/test_sim_capture_kick.py`

**Interfaces:**
- Produces: `SimSession.capture(fold, kick="flex")` — `kick="flex"`: if every vertex is 2D and `kick_field.flex_kick(fold)` returns a field, post `vertices_coords` as `[x, z_i, y]` (the bridge's y-up lift frame, matching ide-bridge.js:45) in a COPY of the fold dict; dof-0/`None` → send unchanged (bridge hash kick). `kick="bridge"`: always send unchanged. The fold argument is never mutated.
- `sim_capture._anchor_main` pins `kick="bridge"` (its 1.0–1.6 band was recorded under the bridge kick).

**Brief.** Compute the kick lazily per capture (null_space_basis SVD is milliseconds at this scale). The payload copy must be shallow-safe: copy the dict and replace only `vertices_coords`. `tracked_points_lifted` already tolerates ~2e-4 lift (its Y-extent guard is 1% of X-Z extent) — add a test proving a flex-kicked payload passes its lift-axis check shape-wise (build the payload, assert Y-column max-|·| == 2e-4 and the `all2d` predicate from ide-bridge (every len==2) is False). Do NOT touch `check_capture`/`DISP_GATE`.

- [ ] **Step 1: failing tests:** (1) payload construction — 2D dog fold in, posted fold has 3-vectors, `max|y| == 2e-4`, x/z columns byte-equal to input x/y, input dict unmutated; (2) `kick="bridge"` → payload identical to input; (3) dof-0 fold → payload identical (fallback); (4) determinism: same fold → same payload. (Factor the payload builder as a pure function `_kicked_payload(fold, kick)` so tests don't need Playwright.)
- [ ] **Step 2: implement; targeted green; full backend suite via nohup (expect 668+new passed / 4 skipped); commit** (`feat(sim-capture): flex-informed capture kick, bridge stands down on 3D payloads`).

### Task 4 [K.2]: `probe_kick_validation.py` — K validation driver

**Files:**
- Create: `mcp_harness/probe_kick_validation.py`
- Test: `mcp_harness/tests/test_kick_validation.py`

**Interfaces:**
- Consumes: `probe_dog_coupling._measure(sim, base, targets, shaped, tgt)`, `dog_base()`, `fox_targets_with_fallback()`, `open_session_with_anchor`; `pose_base.unique_targets`; `probe_front_wave` constants (`PARK_RETRIES=3`, `READS_PER_RECIPE=3`) — import, don't copy; `WaveBudget` pattern with caps K=25 + contingency.
- Produces: `probe_kick_validation.out.json(l)` (uncommitted) with per-cell rows and the gate verdict block.

**Brief.** Controller-run driver, mirrors `probe_front_wave`'s S0 loop at 1/10 scale. Sequence (pinned, 16 planned reads): session anchor (star-4, `kick="bridge"` — the anchor band predates the flex kick) → baseline ×3 (unshaped dog, flex kick) → cells ×3 each: `front_v18|outside|30|0.5`, `frontpair|outside|142.5|0.35`, `front_v13|outside|30|0.5`, `back_v12|outside|142.5|0.5` (representative parked-site cell, NON-gating). Gate evaluation in-code, written to the out.json: **(a)** both S0-parked cells scored 3/3 (zero parks); **(b)** |ΔF(front_v13)| vs |ΔF(front_v18)| within ±7°; **(c)** front_v13 ΔF within ±7° of Phase-S's +6.52 AND `probe_dog_folds` exits 0 (driver shells it, 1 read). back_v12 outcome reported. Baseline drift vs Phase-S (64.64/36.29/37.22) reported, non-gating (session drift is a known datum).

- [ ] **Step 1: failing tests** (sim-free): gate arithmetic on synthetic row sets (pass case; fail-(a) park case; fail-(b) asymmetry case; fail-(c) out-of-band case); budget guard trips at 25+contingency.
- [ ] **Step 2: implement; targeted green; commit** (`feat(kick-validation): K.2 driver + pinned gates`).
- [ ] **Step 3 (CONTROLLER CHECKPOINT — K verdict, headed sim, ≤25 reads):** run the driver. All three gates PASS → K done, rollover unspent to T. Any gate FAIL → K-fail routing (T proceeds on non-kick-blocked reads; coverage hole named); do NOT iterate on the kick without returning to the ledger with a new pinned hypothesis.

### Task 5 [T.1-a]: extract `flex_extension.py` (pure refactor)

**Files:**
- Create: `mcp_harness/flex_extension.py`
- Modify: `mcp_harness/probe_flex_extension.py` (becomes a thin CLI: imports the library, keeps `FLEX_JSON`/`OUT_JSON` paths, `run()/main()` semantics and output contract IDENTICAL)
- Modify: `mcp_harness/tests/test_flex_extension.py` (imports move to the library; the 7 tests' assertions unchanged; `needs_flex_json` guards kept)

**Interfaces:**
- Produces (exact re-homes, signatures unchanged): `interior_vertex_data`, `constructive_tau`, `assemble`, `kernel_nullspace`, `pinned_creases`, `span_min_cosine`, `span_principal_cosines`, `second_order_defect`, `per_vertex_defect`, `continuation`, `degree4_fixture`, `anchor_ea`, plus the tolerance constants (`SECTOR_STRAIGHT_ATOL`, `NULL_TOL_REL`, `SPAN_MATCH_MIN_COS`, `Q_STEP_COARSE=1e-3`, `Q_STEP_FINE=1e-4`, `EXTEND_DEFECT_TOL`, `CONT_*`).
- The probe keeps: `served_dog` wiring, `_served_w_kernel`, `reconcile_dog`, `dog_verdict`, `run`, `main`, `_write` (they consume `probe_front_flex.out.json` — probe-specific, not library).

**Brief.** Move code verbatim (no behavior change); the library must not import `probe_front_flex` (that's the probe's dependency). Consumes only merged `rigid/kinematics/closure.py` + `rigid.degree4` + `rigid.kinematics.rotations` — verify Codex branch merge state first (`git log origin/main..codex/rigid-origami-phase-2-topology-fold --oneline`); if it has since merged, note it and STILL consume only the closure API this code already uses.

- [ ] **Step 1:** verify Codex merge state; record in commit message.
- [ ] **Step 2:** move; probe shrinks; run `probe_flex_extension.py` → byte-comparable verdict output (anchor PASS, NON-EXTENDING, same defect numbers to 1e-12).
- [ ] **Step 3:** ported tests green (`pytest tests/test_flex_extension.py -q`, 7 tests, dog ones running locally via the guard); full suite via nohup unchanged counts; commit (`refactor(flex-extension): promote stage-2 machinery to a library; probe becomes thin CLI`).

### Task 6 [T.1-b]: `obstruction_verdict` — the calibrated stage-2 gate

**Files:**
- Modify: `mcp_harness/flex_extension.py`
- Test: `mcp_harness/tests/test_flex_extension.py` (add library-level cases)

**Interfaces:**
- Produces: `obstruction_verdict(fold, w_rf, *, _anchor_cache={}) -> VerdictResult` — dataclass with `verdict: str  # "EXTENDING" | "NON_EXTENDING" | "REFUSED"`, `reason: str | None`, `rel_fine: float | None`, `rel_coarse: float | None`, `defect: float | None`, `q_norm: float | None`, `min_principal_cosine: float | None`. `w_rf` is in rigid_fold ρ-convention over the fold's canonical crease order; the function translates via `constructive_tau` internally.
- `STAGE2_REL_TOL = 1e-4` (module constant, pinned).

**Brief.** Contract, in order: (1) **anchor first, cached per process** — `anchor_ea()` must pass, else every call returns `REFUSED(anchor)`; (2) per-fold reconciliation — `span_min_cosine(diag(τ)·basis_rf, kernel null)` ≥ `SPAN_MATCH_MIN_COS`, else `REFUSED(translation)`; (3) translate `w_k = τ ⊙ w_rf`, require `‖J w_k‖` small (≤ 1e-8 after unit-normalizing — it came from the rigid_fold kernel, tolerance covers the gauge), else `REFUSED(not-a-flex)`; (4) defect at both h — verdict per the pinned rule (both < τ → EXTENDING; both > τ → NON_EXTENDING; split → `REFUSED(h-unstable)`; `q_norm < 1e-10` → EXTENDING with reason note).

- [ ] **Step 1: failing tests:** (1) degree-4 branch tangent → EXTENDING (reuse `anchor_ea`'s tangent construction); (2) degree-4 generic direction → NON_EXTENDING; (3) dog w\* (guarded by `needs_flex_json`) → NON_EXTENDING with `rel_fine` ≈ 1.0; (4) REFUSED(anchor) path via monkeypatched `anchor_ea`; (5) h-split synthetic → REFUSED(h-unstable) (monkeypatch `second_order_defect`).
- [ ] **Step 2: implement; targeted green; commit** (`feat(flex-extension): calibrated obstruction_verdict (rel-defect + h-stability, anchor-refusing)`).

### Task 7 [T.2-a]: candidate compile + analysis pipeline

**Files:**
- Create: `mcp_harness/structural_search.py` (pipeline half)
- Test: `mcp_harness/tests/test_structural_search.py`

**Interfaces:**
- Consumes: `tests/runner.compile_tree(nodes, pairs, timeout=40) -> (status, fold_json_str)` as the spawn pattern reference, but this task builds its own spawn worker that ALSO returns leaf locations (see brief); `square_complete.complete_square(raw, 1.0, 1.0)`; `rigid_fold.folding_dof / null_space_basis / tip_flex_signatures / front_selectivity`; `flex_extension.obstruction_verdict`; `feasibility.gate.Gate.load(...)` (read `mcp_harness/feasibility/gate.py:16-27` and how `agent_loop` calls it, for the shield step).
- Produces:
  - `compile_candidate(nodes, pairs) -> CompileResult` — dataclass: `status: str  # ok|err|crash|hang|gate_blocked`, `raw: dict | None`, `leaf_xy: dict[int, tuple] | None  # tree node id -> (x, y)`, `note: str`. Spawn-isolated worker (pattern: `tests/runner._worker` + `server.py:77-160`) that builds the tree in `headless_treemaker`, optimizes, exports FOLD **and** `engine.leaf_node_locations()` (server.py:154 is the accessor reference) in ONE child process.
  - `analyze_candidate(cand_id, raw, leaf_xy, roles) -> CandidateReport` — dataclass: `cand_id, status  # pass|stage1_fail|stage2_fail|refused|analysis_error`, `dof, r_star, verdict  # from obstruction_verdict`, `rel_fine, rel_coarse, notes`. `roles` maps tree node ids → `front|back|head|tail` (the generator supplies it — tree-name-based, NOT geometric inference, so flap-added candidates work).
- Tip/hub location: front/back/head tip vertices found by 8dp xy-match of `leaf_xy` into the squared fold (`probe_front_flex.sq_vertex_index` is the reference); hubs = per tip, walk the axial (M/V) path inward from the tip to the first vertex of axial degree ≥ 3 (reference: `sim_capture.axial_hub` uses global max-degree; here per-tip nearest axial hub — front tips and head share `hub_front`, back tips and tail share `hub_rear` in the quadruped family; assert exactly 2 hubs found, else `analysis_error`).

**Brief.** Funnel order inside `analyze_candidate`: square → `folding_dof` (dof 0 → stage1_fail degenerate) → D1 `front_selectivity` with the role-derived tips (r\* < 1.0 → stage1_fail) → `obstruction_verdict(sq, w_creases)` (NON_EXTENDING → stage2_fail; REFUSED → refused; EXTENDING → **pass**). The Tier-2.5 gate shields BEFORE compile inside `compile_candidate` (gate says infeasible → `gate_blocked`, no compile spend; keep the gate's OOD-vs-block semantics as `agent_loop` uses them — read its call site). Everything returns a report; nothing raises across the funnel boundary (search must survive any candidate).

- [ ] **Step 1: failing tests:** (1) REAL compile smoke (marked slow-ok, still seconds): `benchmark_templates.quadruped(1.0)` → `compile_candidate` status ok, 6 leaf_xy entries, raw has M/V edges; (2) `analyze_candidate` on the CONTROL: quadruped compile → report completes with a definite status and finite fields (do NOT pin its verdict — that's a measurement, recorded in Task 9's ledger); (3) role-mapping unit test: synthetic leaf_xy + fold → correct front/back/head vertex ids (build from the dog golden: roles for the golden's 6 tips via `pose_base.NamedBase` cross-check); (4) funnel error paths: refusing fold (monkeypatched verdict) → status refused; no-hub geometry → analysis_error; (5) Tier-2.5 shield: a gate-blocked tree (monkeypatched gate) → status `gate_blocked` with NO compile spend (assert the spawn worker was never invoked).
- [ ] **Step 2: implement; targeted green; commit** (`feat(structural-search): spawn compile+leaf-locations worker and two-stage analysis funnel`).

### Task 8 [T.2-b]: generators, grid, early exit, ledger

**Files:**
- Modify: `mcp_harness/structural_search.py` (search half)
- Test: `mcp_harness/tests/test_structural_search.py` (extend)

**Interfaces:**
- Produces: `coarse_grid() -> list[Candidate]` (dataclass: `cand_id, family, nodes, pairs, roles, primary_key, variant_key`), `refine_around(near_passers) -> list[Candidate]`, `run_search(candidates, *, ledger_path, early_exit=3) -> SearchResult`, CLI `python structural_search.py --coarse` / `--refine` writing `structural_search.out.jsonl` (uncommitted; one JSON line per CandidateReport + the grid/verdict summary block at end).

**Brief.** Base tree = `benchmark_templates.quadruped(1.0)` (9 nodes; roles pinned: 3,4 = front; 5,6 = back; 7 = head; 8 = tail; 1 = hub_front; 2 = hub_rear). **Primaries (~25):** control ×1; front-pair length ×{0.7, 0.85, 1.15, 1.3, 1.5} (nodes 3,4 together — keep symmetric); hub_front edge (node 1 length) ×{0.7, 0.85, 1.15, 1.3}; head ×{0.75, 1.25}; front-pair × hub_front joint grid {0.85, 1.15, 1.3}×{0.85, 1.15}; **flap family:** single center flap = new leaf on node 1, length ∈ {0.1, 0.15, 0.2} (role `front`); symmetric flap pair = two new leaves on node 1, lengths {0.1, 0.15, 0.2}, appended to `pairs` (role `front`). **Multipliers (6 per primary):** node-list order ∈ {designed; head-middle (move node 7 before 3); legs-first (3,4,5,6 before 7,8)} × jitter ∈ {none; seeded ±3% on all leaf lengths, `random.Random(1)`}. Distinctness/early-exit per Global Constraints. Near-passer for refinement: (r\* ≥ 1.0 AND rel_fine < 10τ) OR (rel_fine < τ AND 0.5 ≤ r\* < 1.0); refine = ±half-step on the primary knob + the full 6-variant multiplier set, ≤100 compiles, generated from the ledger.

- [ ] **Step 1: failing tests:** (1) grid size and shape (~150, every candidate has roles for all leaves, flap candidates keep symmetric pairs well-formed); (2) determinism (two `coarse_grid()` calls identical); (3) early-exit logic on a stubbed analyze (injected reports: 3 distinct passers → stops; 3 same-primary passers → does NOT stop); (4) ledger JSONL round-trips; (5) `refine_around` produces only neighbors of near-passers and respects the cap.
- [ ] **Step 2: implement; targeted green; full suite nohup green; commit** (`feat(structural-search): generator grid, early-exit search, ledger CLI`).

### Task 9 (CONTROLLER — T search run + SEARCH CHECKPOINT, sim-free)

- [ ] `cd mcp_harness && nohup .venv/bin/python structural_search.py --coarse > structural_search.coarse.log 2>&1 &`; poll the log. Then `--refine` if near-passers and no early exit.
- [ ] Run `flex_extension.continuation` corroboration on every passer (small controller script; record `verdict_hint` + trace in the ledger notes).
- [ ] **Checkpoint outcomes (pinned):** ≥1 passer → proceed to Task 10 with the top ≤3 distinct passers ranked by (rel_fine asc, r\* desc). Zero passers after coarse+refine → **T refuse verdict**: "no nearby tree admits a finitely-front-mobile compile under studied interventions" — skip Task 10, record the verdict + grid coverage in the ledger, route the molecule/design-theory charter in the handoff. Control candidate's verdict is recorded either way (expected NON-EXTENDING; a deviation is a finding, not a gate).

### Task 10 [T.3]: `probe_structural_confirm.py` — sim validation driver (fires only on passers)

**Files:**
- Create: `mcp_harness/probe_structural_confirm.py`
- Test: `mcp_harness/tests/test_structural_confirm.py`

**Interfaces:**
- Consumes: the passer Candidates (nodes/pairs/roles + compiled raw from the ledger — recompile via `compile_candidate` for freshness, assert leaf_xy match); `pose_base.NamedBase` with a config chosen per base (start from `DOG_CONFIG`; if naming fails on a new base, fall back to role-derived sites — the driver may construct Sites directly from `leaf_xy` + roles, bypassing geometric inference; keep `angles_of` semantics); `pose_pregate.pregate_recipe/rank_menu` for the op menu; `probe_dog_coupling._measure`, `fox_targets_with_fallback`, `open_session_with_anchor`; `WaveBudget` caps T=90 (+K rollover).
- Produces: `probe_structural_confirm.out.json(l)` (uncommitted): per-base baseline, menu, reads, CONFIRM/payoff verdicts.

**Brief.** Per passer (≤3, cap 15 reads each until a CONFIRM): fresh baseline ×3 on the NEW unshaped base → op menu = pregate-ranked front-site cells (families from `probe_front_wave.pinned_menu` semantics: front-tip `outside` θ∈{30, 105, 142.5} × frac {0.35, 0.5} + the front-pair atomic recipes; ranked sim-free, top 3 by rank get 1 read each) → best first-read cell tops up ×2 → **CONFIRM iff mean ΔF of the ×3 ≥ +20° toward 134.83**. On CONFIRM: payoff wave on that base (pregate-ranked ~4-cell menu ×1 + best ×2 top-up; **payoff iff whole-pose ≤ 104 on ×3 mean**), spending the remaining T budget. Kick discipline: all reads use `kick="flex"` (K's outcome); if K FAILED, any parked read is recorded as kick-blocked and the cell skipped (coverage hole list in the out.json). Never touch terminal dog cells — these are NEW bases, no novelty conflict.

- [ ] **Step 1: failing tests** (sim-free): budget/cap arithmetic; CONFIRM/payoff verdict arithmetic on synthetic rows; role-derived Site construction on the dog golden reproduces `NamedBase`'s fronts/backs/head grouping (parity check).
- [ ] **Step 2: implement; targeted green; commit** (`feat(structural-confirm): T.3 sim validation driver`).
- [ ] **Step 3 (CONTROLLER CHECKPOINT — T verdict, headed sim, ≤90 reads):** run per checkpoint-9 ranking. Outcomes (pinned): CONFIRM+payoff → headline (follow-up: pose-search-on-mobile-base). CONFIRM only → lever exists on a mobile base; payoff miss documented (anti-additivity stands). All passers sim-refuse → instrument-vs-reality calibration finding — document, do not force.

### Task 11 [P]: `suggest_pose_stack` tool + HITL wiring + pin tests

**Files:**
- Modify: `mcp_harness/server.py` (new MCP tool `suggest_pose_stack`; read the `suggest_flap_for_region` tool at server.py:460 and the ops/display seam at server.py:580-702 first — follow the B2 suggest-then-confirm shape exactly)
- Modify: `mcp_harness/agent_loop.py` (SYSTEM_PROMPT: after a dog-like compile passes lint, propose the pose via `suggest_pose_stack`; on user confirm, apply via the EXISTING ops path — read how `ide_shape_ops` rides the serve payload, and the strain-oracle contract at agent_loop.py:293 / web/server.py:153,224)
- Test: `mcp_harness/tests/test_suggest_pose_stack.py`, extend the SYSTEM_PROMPT pin test (pattern: `tests/test_agent_shaping_prompt.py`)

**Interfaces:**
- Produces: MCP tool `suggest_pose_stack()` — self-verifying against the CURRENT session fold: builds `NamedBase(raw, sq, DOG_CONFIG)`; if naming succeeds AND site `front_v18` exists → returns the incumbent proposal `{site: "front_v18", ops: ["outside:0.0,0.46801304:0.12398308661620648:142.5"], expected: "whole-pose error 272.49 -> 119.14 (measured, B5-prime)", apply_hint: {tool, args}}` — `apply_hint` names the EXISTING tool that carries `ide_shape_ops` into the serve payload (identify it by reading server.py:580-702; name it exactly, build nothing new); else returns a structured decline (`{applicable: false, reason}`) — the agent must NOT offer the pose then. If T landed in-session, a second entry may be added behind the same shape (controller decides at Task 13; do not build speculative plumbing).
- SYSTEM_PROMPT contract (pin-tested): propose only after lint Pass on a dog-like base; suggest-then-confirm wording; on confirm apply ops via the existing wrapper; `[STRAIN ORACLE]` loop text unchanged.

**Brief.** No new display machinery: ops already ride the serve payload (`"ide_shape_ops"`) and never enter the raw FOLD — the pin test must assert the raw fold in the tool result carries NO ops key (provenance contract). The tool is pure/deterministic given the session fold; NamedBase failure modes (wrong leaf count, ambiguity) → decline, never raise to the agent loop.

- [ ] **Step 1: failing tests:** (1) tool on the dog golden session → applicable, exact incumbent op string, provenance assert; (2) tool on star-4 session → declines; (3) SYSTEM_PROMPT pin test: the B2 contract phrases present (follow the existing prompt-pin test style — assert key contract substrings, not the whole prompt); (4) declined path returns structured JSON, no exception.
- [ ] **Step 2: implement; targeted green; backend suite nohup green; web suite green (40); commit** (`feat(agent): suggest_pose_stack HITL tool + prompt contract (B2 pattern)`).

### Task 12 (CONTROLLER — P live demo, headed, ≤15 reads)

- [ ] `LLM_PROVIDER=groq LLM_MODEL=meta-llama/llama-4-scout-17b-16e-instruct` agent session: compile a dog → lint Pass → agent proposes → confirm → posed dog renders in Model tab, `[STRAIN ORACLE]` PASS (IDE_STRAIN_MAX default 0.15). Record the transcript path in the ledger. Known Groq gotchas: llama placeholder-threading hiccup self-recovers; TPM backoff is built in.
- [ ] P verdict: demo PASS + suites green + provenance pin test green → **P ships** (regardless of K/T outcomes).

### Task 13 (CONTROLLER — slice end)

- [ ] Handoff doc `docs/superpowers/2026-07-13-handoff-structural-remedy-outcome.md`: verdict per phase, read ledger vs the 150 grant, K.0 measured fractions, T grid coverage + verdicts, routing verdict naming the follow-up for EVERY outcome (T-land → pose-search-on-mobile-base slice; T-refuse → molecule/design-theory charter; K-fail → kick root-cause slice; P always ships), deferred minors from task reviews.
- [ ] Final suites (backend nohup + web); update memory files; single PR from `feat/structural-remedy` (ask before push; human merges).

## Self-check ordering rules (carried)

- Task 2's checkpoint gates Tasks 3–4. Tasks 5–8 and 11 are independent of K and may interleave. Task 9 gates Task 10. Sim blocks strictly serial: Task 4 → Task 10 → Task 12 (Task 12 may move earlier if idle).
- Checkpoint every long investigation to the SDD ledger as it goes (Phase-S lesson: salvage came from transcripts).
