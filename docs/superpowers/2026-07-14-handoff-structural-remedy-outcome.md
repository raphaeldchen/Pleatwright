# Handoff: structural-remedy (K / T / P / 0) — outcome

**Date:** 2026-07-14 · **Branch:** `feat/structural-remedy` (from main `641abf3`) · **PR:** (opened at slice end)
**Spec:** `docs/superpowers/specs/2026-07-13-structural-remedy-design.md`
**Plan:** `docs/superpowers/plans/2026-07-13-structural-remedy.md`
**Probe/search outputs (uncommitted, regenerable):** `probe_kick_projection.out.json`
(rerun `probe_kick_projection.py`), `structural_search.out.jsonl` + `.out.run1.jsonl`
(rerun `structural_search.py --coarse` / `--refine`; run1 = pre-tie-fix instrument),
suite logs.

## 1. Session verdict (three phases + Phase 0, all honest endings)

- **Phase K — FALSIFIED at K.0, kick build stopped (0 sim reads).** The
  small-projection hypothesis is dead: parked patterns project *better* onto
  their mechanism z-fields than their scored twins (back_v12 0.431 vs back_v16
  0.239 on all three shared ops; front_v18 0.256 vs front_v13 0.324 — no
  separation anywhere, direction reversed). Sharper: the projection fraction is
  **op-invariant per site** (θ and M/V assignment don't change crease-line
  geometry; the rigidity linearization is assignment-blind), so
  frontpair-parked-at-142.5 vs frontpair-scored-at-105 have *identical*
  projections (0.320051) — parking is **θ-dependent solver dynamics** (which
  target branch the GPU solver is driven toward), not initial-kick direction.
- **Phase T — REFUSE: "no nearby tree admits a finitely-front-mobile compile
  under studied interventions" (0 sim reads).** 144-candidate coarse grid over
  the quadruped body plan (front-pair/hub/head reweights, joint grid, center +
  pair front flaps × 3 node orders × 2 jitters): **every packable candidate
  (12 completed funnels) is NON_EXTENDING at rel ≈ 1.0** — total quadratic
  obstruction, identical in character to the served dog. Zero near-passers →
  refinement generated zero candidates by construction. Routing: **charter the
  molecule/design-theory follow-up** (§4).
- **Phase P — SHIPS as code; live demo BLOCKED(platform), root-caused.**
  `suggest_pose_stack` (B2 suggest-then-confirm) landed through three review
  rounds: concrete node_id resolution via the engine's own leaf locations,
  user-adjudicated generalization to fresh compiles (two-tier: exact measured
  incumbent on the reference base, rescaled recipe + honest expected-string on
  fresh bases), provenance pin-tested, prompt contract pin-tested. Live
  sim-free smoke on a REAL fresh compile: applicable, correct site, resolved
  node_id. The live Groq demo is blocked by a **pre-existing platform
  limitation** (§3.3), not by P code.
- **Phase 0 — SKIPPED:** GitHub Actions billing still blocked (run 29290064041
  annotation: payments failed / spending limit; jobs die in 3–5 s). The merged
  ubuntu CI migration (PR #41) remains never-executed.

**Read ledger: 0 of 150 sim reads spent.** K.0's falsification (sim-free)
stopped the K sim block; T's refuse verdict fired before capture; P's demo
never reached the sim. The entire session's evidence is sim-free — the
honest-outcome rule did exactly what it was designed to do, three times.

## 2. Gate-by-gate record

**Preflight (PASS, exact):** fresh worktree env per the Phase-D recipe;
`probe_front_flex` r\* 1.76272 / captured 0.904 / reconcile 162 = 114/12/36/0;
`probe_flex_extension` anchor PASS + NON-EXTENDING (defect 0.095625, rel 1.0,
h-stable 9.4e-10, carriers v5/v0/v1/v4); baseline suite 668/4.

**K.0 (falsification gate, pinned before measuring):** hypothesis survives
only if every gated parked cell's projection fraction < 1/3 × its scored
twin's, all parked dof ≥ 1. Measured: 4/4 gated pairs FAIL the separation
(all parked dof 4). **VERDICT: FALSIFIED** → pinned routing: STOP the K build;
Tasks K.1/K.2 never built; T validation would have proceeded on
non-kick-blocked reads only (moot — T never reached the sim).

**T search (two coarse runs, tie-fix between):**
- Run 1 (144 candidates): 108 compile_failed (real TreeMaker knife-edge:
  `NOT_LOCAL_*`, `POLYS_MULTIPLE_IBPS`, invalid polygon network — only
  designed-order compiles survive), 12 gate_blocked (Tier-2.5 shield:
  flap_pair 0.1/0.15, p_pack < 0.017), 12 analysis_error (hub-degree ties),
  12 stage2_fail. The tie errors blinded the flap family's only 3 surviving
  compiles → instrument completion (unique guard-consistent pair among
  tied-and-above vertices, refuse-on-0-or-2+; commit `6a66084`) + full rerun.
- Run 2 (final): same tallies, but the ties are now honest guard refusals —
  "0 consistent pairs" (or 3): those compiled geometries genuinely don't fit
  the two-hub quadruped model (flap candidates read dof 10–17; headmid
  variants dof 9 — structurally different mechanisms). The 12 completed
  funnels: control + reweight primaries in designed order, both jitters —
  nojit compiles read dof 7 / r\* = inf, jit1 read dof 3–5 / r\* 1.46–1.66,
  and **every one has rel_fine = rel_coarse = 1.0** (to machine precision).
- Near-passer rule ((r\* ≥ 1.0 ∧ rel < 10τ) ∨ (rel < τ ∧ 0.5 ≤ r\* < 1.0)):
  zero qualify → `--refine` generated 0 candidates. Continuation
  corroboration: vacuous (no passers). Early exit never triggered.

**P gates:** SYSTEM_PROMPT contract pin-tested (approval gate, oracle text,
tree_nodes instruction, paper-dims note, negative pin on the dropped
phrasing); provenance pin-tested (raw fold never carries ops; no session
mutation); suites green at each commit (backend 728/4 at 9188ffa; final
counts in §6); live sim-free smoke: fresh compile → applicable true, site
front_v11, site_is_reference false, op rescaled to the base's own axial
(d 0.124035 vs reference 0.123983), node_id 4 resolved on the correct side.
**Live demo gate: BLOCKED(platform)** — evidence chain in §3.3.

## 3. Measured findings beyond the gates

1. **The kick-asymmetry mechanism is θ-dependent branch dynamics.** K.0's
   op-invariance datum (identical projection, different park outcome across θ
   at the same sites) exonerates initial-kick *direction* entirely. The next
   kick hypothesis must involve the target state: candidate — the sign of the
   kick's projection onto the *target branch* direction (kick·branch < 0 →
   solver must cross flat → parks). This is the kick root-cause slice's
   pinned starting hypothesis, one datum from free.
2. **Total obstruction is uniform across the packable neighborhood.** Not one
   of 12 completed funnels moved rel off 1.0 — the entire quadratic form of
   every front-selective flex lies outside range(J) for every packable
   quadruped-family compile. Combined with Phase S (the served dog, same
   value), this strongly suggests the **universal-molecule construction on
   this body plan structurally produces fully-obstructed front flexes** —
   the remedy is not in tree-space metric/order/jitter neighborhoods.
3. **The Groq blob-echo limitation (P demo blocker), fully root-caused:**
   (a) the live agent on scout DID compile a real dog end-to-end (mesh →
   tree → compile, 7 perturb attempts — the compile leg of the HITL flow is
   proven live); (b) the lint call then failed 3× on the fold *echo* (one
   Groq 400 `tool_use_failed`, two content-dropped echoes that crashed
   Oriedita with "Index 64 out of bounds for length 64"); (c) the exact same
   fold (6223 chars, downloaded from the pane) lints fine server-side —
   verdict "FAILED: 10 vertex violations (0 M/V-fixable, 10 geometry)" = the
   canonical accepted hull-frontier signature; (d) every stronger Groq model
   is TPM-blocked at request 1 (gpt-oss-120b needs 11 808 vs cap 8 000;
   qwen3.6-27b needs 13 127); scout is the only free-tier fit and cannot
   reliably echo ≥6 KB tool args. The tool protocol's
   echo-the-full-FOLD-between-tools design is the fragility; it predates this
   slice.
4. **Instrument boundary named:** the two-hub D1 model cannot read flap-added
   or reordered-packing geometries (dof 7–17, 0-or-multiple guard-consistent
   hub pairs). A generalized front-selectivity instrument (arbitrary hub
   topology) is prerequisite to ever measuring the flap family — worth
   knowing before any molecule-level slice assumes flaps are measurable.
5. **Fresh dogs lint as hull-frontier FAILs** (4–10 geometry violations,
   0 M/V-fixable) — consistent with the known lore (agent taught to ACCEPT);
   no fresh-compile linter crash exists (the demo's crash was echo-induced).

## 4. Routing verdict (a follow-up named for EVERY phase outcome)

1. **Molecule/design-theory charter (T-refuse routing, the headline
   follow-up):** the question is no longer "which nearby tree" but "what in
   the universal-molecule construction forces rel = 1.0 on front flexes of
   this body plan, and what molecule-level or paper-shape intervention
   breaks it." Inputs ready: `flex_extension.obstruction_verdict` (calibrated,
   anchored), `structural_search`'s funnel + both ledgers, per-vertex defect
   localization (v5-class cone vertices), finding #2.
2. **Kick root-cause slice (K routing):** pinned starting hypothesis =
   kick·target-branch sign (finding #1). `kick_field.py` (z-fields, exact
   bridge-hash reproduction, canonical flex kick) and
   `probe_kick_projection.py` are its ready-made instrument kit.
3. **Fold-handle passing (P demo unblock):** replace echo-the-FOLD tool args
   with short server-side handles (registry keyed by compile; tools accept
   `fold_handle` OR `fold_json_string`). Unblocks live dogs on Groq scout and
   de-fragiles `validate_flat_foldability` for every provider. Then re-run
   the pinned live demo (compile → suggest → confirm → Model tab + oracle).
4. **P productization is otherwise DONE** — merged machinery + this slice's
   tool ship the incumbent stack behind HITL confirm; the demo is the only
   outstanding gate and it has a single named blocker (#3).
5. **Phase 0 (unchanged):** first ubuntu CI run still pending billing; the
   PR #41 re-bless protocol stands.
6. **Explicitly NOT routed:** more tree-space search breadth (the neighborhood
   answered uniformly); bridge changes (nothing implicated the bridge —
   ide-bridge.js untouched all session); amplitude-schedule kicks (falsified
   direction-class fix on falsified hypothesis).

## 5. Deferred minors (final-review triage input)

From task reviews, all non-blocking: (m1) `flex_kick` normalization asserts
`== 2e-4` exactly (IEEE-brittle if the fixture changes); (m2) `kick_field`
FD helper could shape-mismatch on a face-less trailing vertex (unreached);
(m3) all-zero flex field → nan not raise (unreachable); (m4) probe imports
`_resid_jac` across module boundary (pre-existing coupling made visible);
(m5) stale comment `test_kick_field.py:27` says `degree4_fixture` lives in
the probe; (m6) `REFUSED(translation)` + non-finite `not-a-flex` guard
untested; (m7) `--refine` before `--coarse` surfaces a raw
`FileNotFoundError`; (m8) `refine_around` cap can truncate mid-primary
(documented); (m9) `*.out.json(l)` still not gitignored (manual discipline);
(m10) `suggest_pose_stack` direct-call serialization edge outside try
(unreachable via MCP validation); (m11) fresh-base mirror-leg choice is a
numbering artifact, strain oracle is the validity gate (adjudicated,
disclosed in the expected string); (m12) "lexicographic" site tie-break is
string order (front_v9 > front_v11), deterministic but non-numeric.

## 6. Suite state

Backend suite green through the slice: 668/4 baseline → 695/4 (Task 7) →
710/4 (Task 8) → 728/4 (Task 11 feature) → final counts at HEAD recorded in
the PR body from `/tmp/claude-501/suite_final.log` (this handoff was written
while the final run completed; the PR body carries the exact numbers). Web
suite: 59 passed (6 files; the 40 baseline grew on main before this slice).
Probe outputs and suite logs uncommitted per house rules; the coupling JSONL
remains sourced read-only from the main checkout.
