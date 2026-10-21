# Design: molecule-mobility — break the universal-molecule front lock (M / K2 / H)

**Date:** 2026-07-14 · **Branch:** `feat/molecule-mobility` · **Single PR**
(structural-remedy precedent; revisit only if lanes diverge).
**Lineage:** structural-remedy (PR #42, MERGED to main `32afbd4`
2026-07-14T15:15:43Z — preflight-verified). Its routing verdict is this
session's charter: the T search REFUSED tree-space (144-candidate grid, every
packable quadruped-family compile NON_EXTENDING at rel = 1.0 to machine
precision, zero near-passers), K.0 FALSIFIED the projection-magnitude kick
hypothesis (parking is θ-dependent target-branch solver dynamics), and P's
live demo is blocked solely on the Groq blob-echo platform limit.
**Handoff:** `docs/superpowers/2026-07-14-handoff-structural-remedy-outcome.md`
(§3 findings, §4 routing, §5 minors).

**Read budget: 90 sim reads = K2 25 / M 40 / H 5 / contingency 20.**
Rollover K2→M; unspent M → contingency, never unpinned exploration. Every
read sits behind a sim-free pre-gate (precedent: 150 granted / 0 spent).

**Session order:** preflight regenerations → K2.0 → M1 → H → M2 → sim blocks
(all reads last, gated by K2's verdict). Single controller; "parallel" lanes
are interleaved packages, each ending at a reviewer gate.

## 0. Preflight (regenerate, never copy)

Fresh-worktree env per the standing copy list (.venv symlink,
`headless_treemaker*.so`, `oriedita/*.jar`, `OrieditaValidator.class`,
`web/frontend/dist`, coupling JSONL read-only from the main checkout, `.env`
for live-agent work). Then regenerate with pinned expectations — **any
mismatch is STOP**:

- `probe_front_flex` → r\* 1.76272 / captured 0.904 / reconcile 162 =
  114/12/36/0.
- `probe_flex_extension` → anchor PASS + NON-EXTENDING, defect 0.095625,
  rel 1.0.
- `probe_kick_projection` → FALSIFIED; back_v12 0.430763 vs back_v16
  0.238736, frontpair identical 0.320051 (these are K2.0's baseline numbers).
- `structural_search.py --coarse` via nohup + log-poll (~35 min) → 144 rows
  = 108 compile_failed / 12 gate_blocked / 12 analysis_error / 12 completed,
  all completed funnels rel 1.0 (M1's ledger evidence).

Suite baselines: backend 741 passed / 4 skipped, web 59; CI-equivalent
(artifact-free) 737/9 — Actions billing-blocked, run `make test` locally
with artifacts stashed for CI parity.

Codex namespace check (charter): `codex/rigid-origami-phase-2-topology-fold`
no longer exists on origin (only phase-0/phase-1/degree4 remain). This slice
consumes ONLY merged `mcp_harness/rigid/kinematics/closure.py` (as
`flex_extension` already does); re-verify at build time; never import from
unmerged branches. `rigid/` stays Codex-owned (read-only); `rigid_fold.py`
stays OWNERSHIP-NOTE-protected (import from it, never edit it).

## 1. Lane K2 — target-branch kick v2 (prerequisite; gates M's sim block)

### K2.0 — the sign check (sim-free, first package after preflight)

**New probe `mcp_harness/probe_kick_alignment.py`.** Reuses
`probe_kick_projection`'s pinned cell construction verbatim: the same
`GATED_PAIRS` (back_v12 vs back_v16 at outside|142.5|0.5, reverse|105|0.5,
outside|60|0.5; front_v18 vs front_v13 at outside|30|0.5), the same
frontpair recipe (front_v13+front_v18, frac 0.35, parked θ=142.5 vs scored
θ=105) — but the frontpair θ-pair is now **gating** (it isolates the target
direction at identical geometry; K.0 kept it non-gating because projection
was op-invariant, which no longer holds for target directions).

Per cell:
1. Build the shaped twin via `pose_base.site_op` exactly as K.0 did.
2. **Target-direction extraction seam (decided):** read `edges_foldAngle`
   off the shaped dict — single-sourced from `shaping.py`, the exact array
   the sim drives toward. Convert deg→rad into `rigid_fold`'s
   ρ-about-low→high-vertex convention. This sign translation is the one
   careful step: it is validated on the degree-4 anchor pattern
   (predict-then-measure) BEFORE any twin cell is read, same discipline as
   `constructive_tau`.
3. Project the target-angle vector onto `null_space_basis`'s flex space
   (restricted to M/V creases). The raw target vector is NOT a first-order
   flex, and `kick_field.out_of_plane_field` is only face-consistent on
   flexes — the "target branch" is the flex-space projection.
4. Alignment = ⟨`bridge_hash_kick` z-vector, z-field of the projected
   target⟩ / (‖kick_z‖·‖field‖) ∈ [−1, 1].

**Pinned gate (strict sign rule, pinned here BEFORE the probe exists):**
CONFIRMED iff every gated parked cell's alignment < −tie_tol AND every
scored twin's > +tie_tol, INCLUDING the frontpair θ-pair (parked-θ negative,
scored-θ positive). Any parked cell positive, any scored cell negative, or
any |alignment| ≤ tie_tol → **FALSIFIED** (a tie refuses the sign story; it
does not pass). **tie_tol = 1e-9** on the normalized alignment. A cell whose
op refuses to apply → probe exit REFUSED (controller sees it; not silently
swallowed), mirroring K.0.

Routing: FALSIFIED → lane ends, report; M's sim block proceeds on
non-kick-blocked reads with the coverage hole flagged in the handoff. This
is a valid ending. CONFIRMED → K2.1 build.

### K2.1 — target-aware kick build (conditional on K2.0 CONFIRMED)

Capture-harness site ONLY: flex-informed, target-sign-aware pre-lift at the
`sim_capture` loadFold seam (the proven all2d-guard seam). The bridge is
untouched — `ide-bridge.js` remains out of scope; nothing in K falsified or
implicated it. z-lift interplay pins carried: the 2e-4 lift breaks
tracked_points ratio checks (known lore) — pre-lift must preserve the
existing capture contracts.

**Pinned K2.1 validation gates (reused verbatim from the unbuilt K.2):**
both S0-parked cells scoreable ×3; twin |δ| symmetry ±7°; front_v13 re-read
in band; `probe_dog_folds` green; back_v12 measured, non-gating. Budget ≤ 25
reads (rollover of the unspent to M).

## 2. Lane M1 — the mechanism note (headline; derivation-FIRST)

**Deliverable:** committed doc
`docs/superpowers/2026-07-14-molecule-obstruction-mechanism.md` — a
mechanism account of WHY Q(w,w) lies entirely outside range(J) (relative
defect = 1.0 to machine precision, uniformly across the packable
neighborhood) for this body plan's universal-molecule compiles.

**Scope (decided): dog-class.** The note is done when the lock on THIS body
plan's compiles is explained and predicts correctly on ≥2 independent
fixtures. If the account visibly generalizes to all Lang-molecule patterns
of a characterizable class, the note says so — but generality is not owed.
Grounding inputs: `flex_extension.per_vertex_defect` localization, the
cone-vertex carriers (served dog v5 deg-6, v0/v1/v4), `structural_search`'s
two ledgers (12 completed funnels, all rel 1.0), and Lang's official source
at `~/Desktop/TreeMakerSource` (`tmTree.cpp` molecule
build, `tmPoly::BuildPolyContents`) as ground truth for WHY the molecule
creases where it does — the note must tie the obstruction to the
CONSTRUCTION (bisector/ridge/gusset structure), not merely to observed
numbers.

**Protocol (pinned):** every analytic claim gets its numeric prediction
written to the SDD ledger BEFORE the check runs — predict-then-measure,
never measure-then-explain. Long derivations are checkpointed to the ledger
as they go. Larger single-package briefs are acceptable in this lane (one
mind holding the whole derivation), but every package still ends at a
reviewer gate.

**Fixture ladder (decided):** hand-built FOLD dicts, pure Python — no
TreeMaker compile, no `square_complete` (raw polygon paper; `flex_extension.
assemble` handles genuine interior vertices; boundary vertices are
unconstrained):

1. **Single rabbit-ear molecule** (the triangle universal molecule).
   Predict: flex-space dimension, obstruction verdict per designated flex
   direction, per-vertex defect localization. Then measure.
2. **Single gusset-quad molecule.** Same prediction set.
3. **Minimal two-molecule composite** sharing a ridge crease — the rung
   that separates "single molecules are obstructed" from "composition
   obstructs," which is the load-bearing question for remedy-family choice.

The degree-4 anchor stays the extending control, elevated:
predict-then-measure on every quantity the note leans on.

**M1 gate (pinned):** the note's predictions verified on ≥2 independent
fixtures; the fixtures land as committed tests (fixture builders + verdict
pins). Honest routing: if the mechanism proves the lock inherent to ALL
Lang-molecule patterns of this class → document the theorem-sketch, charter
the body-plan/design-level follow-up, end honestly (M2 remedies that the
theorem rules out are NOT built to fail).

## 3. Generalized selectivity instrument — `mcp_harness/tip_mobility.py`

M2's first package (prerequisite: the two-hub D1 instrument refuses
flap/reordered/augmented geometries — dof 7–17, 0-or-multiple
guard-consistent hub pairs, measured in the T run).

**Design (decided): rigid-motion quotient; role-derived tip groups; new
module.**

- **Contract:** fold dict + role-derived tip groups in (front tips, back
  tips, head, optional tail — vertex ids; role derivation reuses the
  `_tip_groups_sq` logic against tree leaf locations), `SelectivityResult`
  out. Raises a typed instrument error on genuine degeneracy (signatures
  vanish), never on topology grounds — no hub identification exists
  anywhere in the module.
- **Construction:** `null_space_basis` → absolute tip z-velocities per flex
  direction (reusing `tip_flex_velocity` with the two-step-size agreement
  guard unchanged) → **rigid-motion quotient**: least-squares affine field
  z = a + bx + cy fitted over ALL pattern vertices (exactly the flat
  pattern's three out-of-plane rigid modes), evaluated at the tips,
  subtracted → quotiented signatures into `rigid_fold.front_selectivity`
  (imported, unmodified — the Rayleigh machinery and r\* semantics stay
  single-sourced) → r\*.
- **Module constraints:** NOT in `rigid_fold.py` (OWNERSHIP NOTE), NOT in
  `rigid/` (Codex). Own test file, own docstring contract.

**Calibration gate (pinned before use as a remedy gate):**
- On D1-measurable geometries (the 12 completed T-funnels + the served
  dog): **verdict agreement** with D1 at the r\* ≥ 1.0 boundary — values
  may differ (the reference frame changed), verdicts may not. Any
  disagreement → HALT the gate definition; that is a calibration finding,
  not a nuisance to tune away.
- On the previously-refused geometries (flap-added dof 7–17, headmid
  dof 9, from the T ledger): the instrument must READ them (produce an r\*,
  not a refusal).

**Stage-1 bar for remedy candidates: r\* ≥ 1.0 in quotient coordinates.**

## 4. Lane M2 — remedies (mechanism-led; a+d core)

**Families (decided):** default order (a) → (d), reorderable by the
mechanism note; (b) conditional; (c) HALT-and-ask.

- **(a) Post-compile crease augmentation** — new `mcp_harness/
  crease_augment.py`, pure library: derived FOLD dicts with real added
  edges/vertices on the compiled+squared pattern, move vocabulary guided by
  `per_vertex_defect` and pinned at plan time from M1's findings.
- **(d) Separated-hub body plan** — ONE tree family (front legs on a hub
  separated from the rear hub), through the existing funnel: Tier-2.5
  feasibility gate → spawn-compile → `square_complete` → instruments. One
  family, not a grid — the T verdict already answered neighborhoods.
- **(b) Non-square paper** — only if the mechanism note implicates the
  square boundary/corner structure.
- **(c) Engine-side molecule variant** — only if the note DEMANDS it;
  treat the C++ engine as read-mostly; **HALT-and-ask before any engine
  edit** (pinned).

**Provenance seam (decided): research artifacts only.** Augmented folds are
uncommitted session artifacts feeding `tip_mobility`/`flex_extension` and —
for a pre-gate passer — loaded into `sim_capture` directly. `web/server.py`
is untouched; the raw-fold/display_json contract is untouched by
construction; handles never enter the FOLD dict (H lane, same rule). IF a
remedy sim-CONFIRMs, serve-side integration (likely ops-style, next to
shaping) is the follow-up slice's first package.

**Per-candidate gate chain (all sim-free, in order; stage-2 AMENDED at the
Task-11 checkpoint, user-adjudicated):** the mechanism note's Theorem Z
proves rel ≡ 1.0 for every flat pattern with a nonzero quadratic, so the
original rel-based EXTENDING can never fire on flat remedy candidates —
stage-2 is re-pinned to the κ (area-form) machinery the note verified:
1. Stage-1: `tip_mobility` r\* ≥ 1.0.
2. Stage-2 (re-pinned): EXTENDING-grade iff (i) min over the unit kernel
   sphere of ‖κ‖ < 1e-6 (`flat_area_forms` + the Task-6 witness machinery),
   (ii) the zero-cone direction is itself front-selective (front/backhead
   ≥ 1.0 under the quotient signatures), (iii) `continuation` on it reaches
   amplitude ≥ 0.3 rad without corrector failure. Calibration-first: the
   gate must PASS ≥2 ladder zero-cone witnesses AND FAIL the dog kernel
   before judging any candidate, else HALT.
3. Only then a sim read fires, under K2's verdict (K2.1-hardened kick if
   CONFIRMED+validated; otherwise non-kick-blocked reads with the hole
   flagged).

**Sim CONFIRM (pinned):** front ≥ +20° toward the fox target 134.83, mean
of 3 standalone reads from a fresh baseline ×3; carried ±7° shaped-re-read
drift rules; any < 10° comparison needs ×3 + same-session baselines.
Controller-only headed sim (subagent sim processes get orphan-killed —
standing hard rule). TreeMaker vertex numbering does not survive
recompilation — site keys are base-relative; fresh compiles get fresh site
resolution.

## 5. Lane H — fold-handle passing (guaranteed payoff; independent)

**Registry (decided, amended at plan time):** new
`mcp_harness/fold_registry.py` — content-hash handles (`fold:<12 hex>` over
canonical JSON: sorted keys, canonical float repr), **file-backed shared
store** (one `<hash>.json` per fold; directory = `IDE_FOLD_REGISTRY_DIR`
env var, default under the system tempdir; file-count cap 32 with
oldest-mtime eviction at register time; hash re-verified on resolve).
Amendment rationale (user-adjudicated during planning): `agent_loop.py`
spawns TWO child MCP server processes — `server.py` (compile tools) and
`linter_server.py` (`validate_flat_foldability`, the tool whose fold echo
broke the P demo) — so an in-memory registry can never cross that process
boundary; files can, and content addressing makes cross-process (even
cross-session) sharing benign: same content → same handle → same bytes,
with an evicted handle degrading to a clear tool error +
`fold_json_string` fallback. Content addressing keeps registration
idempotent and handles never-stale-against-content; tool SEMANTICS stay
stateless (same inputs → same outputs). Own test file.

**Wiring (`mcp_harness/server.py`):**
- Every tool that returns a fold ALSO returns a `fold_handle` field beside
  the existing payload — returns otherwise unchanged (backward compat
  pinned).
- Every fold-accepting tool gains optional `fold_handle`; **handle wins**
  over `fold_json_string` when both are present; unknown/evicted handle →
  clear tool error naming the handle (not a crash, not a silent fallback).
- Handles never enter the FOLD dict; provenance contract untouched; the
  raw fold never carries ops.
- SYSTEM_PROMPT updated to prefer handles — pin-tested like the P contract
  (positive pin on the instruction, negative pin on dropped phrasing).

**Pinned H gates:**
- Existing suites green; `fold_json_string`-only paths pin-tested unchanged.
- The blocked P live demo re-run end-to-end on Groq scout
  (`LLM_MODEL=meta-llama/llama-4-scout-17b-16e-instruct`): compile → lint
  (hull-frontier ACCEPT is the expected verdict on fresh dogs: 4–10
  geometry violations, 0 M/V-fixable) → suggest (tree_nodes passed, node_id
  resolved) → confirm → posed dog renders in Model tab → [STRAIN ORACLE]
  verdict loop closes.
- Carried platform facts: scout is the only free-tier fit (gpt-oss-120b
  needs 11 808 vs 8 000 TPM cap; qwen3.6-27b 13 127); the web chat's first
  send after page load can race the websocket (re-send works); stdin python
  cannot parent spawn workers (child re-runs `<stdin>` — real files only).

## 6. Honest-outcome routing (every ending valid; named follow-up for each)

- **M lands** (remedy passes pre-gates + sim CONFIRM) → follow-up:
  pose-search-on-mobile-base slice + serve-side augmentation seam.
- **M1 proves the lock inherent** to all Lang-molecule patterns of this
  class → theorem-sketch documented; follow-up: body-plan/design-level
  charter; end honestly, no remedies built to fail.
- **Remedies exhaust with no EXTENDING passer** → named
  instrument-vs-construction boundary in the handoff.
- **Pre-gate passer that the sim refuses** → calibration finding; document,
  do not force.
- **K2.0 FALSIFIED** → valid ending; M reads proceed non-kick-blocked with
  the hole flagged; follow-up: solver-dynamics instrumentation charter.
- **K2.1 validation fails** → same solver-dynamics charter, with the build
  preserved as instrument.
- **H always ships** → the live-demo gate closes; P productization is then
  fully DONE.

## 7. Testing, process, house rules

- TDD per package (superpowers discipline); every package — including the
  M1 derivation briefs — ends at a reviewer gate.
- Full suites and the coarse search via nohup + log-poll, never bare
  foreground. Playwright lives in `mcp_harness/.venv` only; SimSession is
  HEADED; controller-only for any headed-sim run.
- Probe outputs (`*.out.json`/`.jsonl`/`.log`) and suite logs stay
  uncommitted (never `git add -A`; keep the `needs_flex_json` skipif
  pattern; the gitignore question was reviewed and deliberately NOT
  adopted).
- `dist/` gitignored; `cp public→dist` load-bearing.
- Human merges every PR; ask before push.
- Shared checkout: Codex active — read main's state through git, never the
  main checkout's working dir.
- Slice end: outcome handoff doc (`docs/superpowers/
  2026-07-14-handoff-molecule-mobility-outcome.md` or dated successor) +
  the single PR; the handoff's routing verdict names the follow-up for
  EVERY lane outcome per §6.

## 8. Decision log (brainstorm 2026-07-14, all user-adjudicated)

1. M1 scope: **dog-class mechanism** (generalization welcome, not owed).
2. M1 fixtures: **molecule ladder** (rabbit-ear, gusset-quad, two-molecule
   composite) + degree-4 anchor control.
3. Instrument reference frame: **rigid-motion quotient** (affine z-field
   over all vertices projected out; no hub identification).
4. Instrument home: **new `mcp_harness/tip_mobility.py`**, importing
   `rigid_fold.front_selectivity`.
5. M2 families: **mechanism-led, a+d core**; b conditional on the note;
   c behind HALT-and-ask.
6. Augmentation provenance: **research artifacts only** this slice;
   serve-side integration chartered on M-land.
7. K2.0 target extraction: **`edges_foldAngle` off the shaped dict**,
   deg→rad into ρ convention, flex-space projection.
8. K2.0 gate: **strict sign rule**, tie_tol 1e-9, frontpair θ-pair gating;
   ties FALSIFY.
9. H registry: **`fold_registry.py`**, content-hash handles, cap 32 —
   AMENDED at plan time to a file-backed shared store
   (`IDE_FOLD_REGISTRY_DIR`, tempdir default): the two child MCP server
   processes (`server.py` / `linter_server.py`) cannot share in-process
   memory, and the linter is the tool that needs handles most.
10. Ordering: **preflight → K2.0 → M1 → H → M2 → sim blocks**.
11. Budget: **90 = K2 25 / M 40 / H 5 / contingency 20**, rollover K2→M.
12. Branch: **`feat/molecule-mobility`**, single PR.
