# Structural remedy — kick-hardening (K), structural compile search (T), pose-stack productization (P)

**Date:** 2026-07-13 · **Branch:** `feat/structural-remedy` (from main `641abf3`)
**Parent verdicts:** Phase S (PR #40, merged): the front flex w\* is a second-order
phantom — STRUCTURAL AT FINITE ORDER for rigid kinematics; kick asymmetry at five
data points is a named prerequisite; routing pinned in
`docs/superpowers/2026-07-13-handoff-front-lever-payoff-outcome.md` §4.
**Grandparent charter:** `2026-07-12-b5-front-dof-diagnosis-design.md` §5
(structural branch).

## 1. The questions this session answers

Three phases, pre-routed by Phase S; every phase's refusal path is a valid ending.

- **Phase K (prerequisite; gates T's sim validation):** why does the uniform
  2e-4 z-lift kick fail to break flat symmetry on some SHAPED patterns,
  asymmetrically across mirror twins — and can a deterministic symmetry-breaker
  make the parked cells scoreable without regressing the healthy ones?
- **Phase T (headline):** does a minimal Metric-Tree/compile intervention exist
  whose compiled+squared output has a front-selective flex that EXTENDS
  finitely — and does the sim confirm it can move front ≥ +20° toward the fox
  target (134.83)?
- **Phase P (guaranteed payoff; independent of K/T):** make the best-known pose
  stack user-visible via the agent HITL flow (B2 suggest-then-confirm), with
  the strain-oracle loop closed.
- **Phase 0 (bounded, conditional):** first execution of the merged-but-never-run
  ubuntu CI migration (PR #41), if Actions billing is restored.

## 2. Decisions pinned at the brainstorm

1. **K mechanism = flex-informed kick**, gated by a sim-free projection
   falsification check FIRST (K.0). Root-cause hypothesis: the Knuth-hash kick
   is a fixed pseudo-random vector keyed on vertex index; parking happens when
   its projection onto the shaped pattern's actual mechanism directions is
   anomalously small — direction, not amplitude, is the defect. Amplitude
   schedules and hash-reseed retries rejected as symptom-level (1e-4→2e-4
   already proved amplitude fixes don't generalize); hash-reseed remains a
   documented fallback only if K.0 confirms direction but the flex kick still
   parks.
2. **K fix site = capture harness** (`sim_capture`), never the bridge: the
   harness pre-lifts `vertices_coords` to 3D in the `loadFold` payload copy;
   the bridge's existing `all2d` guard stands down automatically. Raw fold on
   disk untouched; served-display path byte-identical to today. Documented
   limitation: display replay of shaped patterns keeps the old uniform bridge
   kick (safe for P — the incumbent demonstrably folds through that path);
   a shaped pattern that parks in DISPLAY is a named follow-up, not this
   session's scope.
3. **Stage-2 promotion home = new `mcp_harness/flex_extension.py`** (not
   `rigid_fold.py` — OWNERSHIP NOTE forbids closure math; not `rigid/` —
   Codex's namespace; not `pose_pregate.py` — stage 1 stays thin). The probe
   becomes a thin CLI over the library.
4. **T candidate families = all four, structured as primaries × diversity
   multipliers.** Primaries (change the tree): front-group edge reweights +
   added front detail flaps (A-9 machinery). Multipliers (same tree, different
   compiled geometry): node-order permutations + packing perturb seeds, layered
   per primary. Exact grid pinned at plan time.
5. **T search breadth = staged with early exit:** coarse grid ~120–200
   candidates, one refinement pass (~100) around near-passers, EARLY EXIT once
   3 distinct pre-gate passers exist (distinctness = different family or
   well-separated in knob space; rule pinned at plan time), hard compile cap.
   Zero passers after coarse+refine → the honest refuse verdict.
6. **Stage-2 gate form = relative defect + h-stability; continuation as
   corroboration only.** Pass iff ‖(I−JJ⁺)Q(w,w)‖/‖Q(w,w)‖ < τ AND the value
   agrees across the coarse/fine FD steps. τ pinned at plan time from the
   anchor calibration (extending ~1.6e-8 vs phantom 0.336 — seven decades of
   separation; geometric mean ~7e-5; τ needs ≥2 decades of margin each side).
   The degree-4 anchor runs first every session and the library REFUSES on
   drift. `continuation()` runs only on graduating passers before sim spend.
7. **P ships incumbent-first, fully decoupled** (`outside:0.0,0.46801304:
   0.12398308661620648:142.5` on `front_v18`, whole-pose 272.49 → 119.14).
   A T winner is a different compiled BASE, not a stack swap: if it lands
   in-session it enters as an additional suggestion behind the same HITL flow;
   otherwise "productize T's winner" is the named follow-up.
8. **Budget = 150 sim reads: K 25 / T 90 / P 15 / contingency 20.** Rollover
   K→T; unspent T rolls to contingency, never to unpinned exploration.
   Priced: K needs ~16; T's ~3 passers + one payoff ≈ 55–70; P's demo ~5.
9. **Ordering = interleaved sim-free builds, serial controller sim blocks**
   (K-validation → T-capture → P-demo). Phase 0 first if billing allows. K.0
   runs first among builds (it can kill K's design before the kick is written).
   T-search and P-build proceed regardless of K's state. All headed-sim runs
   controller-only (standing rule).
10. **Branch = `feat/structural-remedy`** (banned tokens avoided). PR structure
    (per phase-package vs one PR) decided at plan time.

## 3. Phase K — flex-informed kick

### K.0 — projection falsification check (sim-free; first build)

New geometric primitive (needed by the kick anyway): given a flat pattern and
a crease-rate flex w (`rigid_fold.null_space_basis`), construct the induced
first-order out-of-plane vertex field — root face z=0, walk `rigid_fold`'s
face tree, accumulate per crossed crease (rotation rate × signed distance to
the crease line). ~50–100 lines; sim-free-testable (faces stay planar to first
order; nonzero on dof ≥ 1 patterns; analytic degree-4 case).

K.0 then computes, for the kick record's five data points across three sites
(back_v12 parked ×3 vs its healthy mirror twin; front_v18 parked vs front_v13
scored at `outside|30|0.5`; `frontpair|outside|142.5|0.35` parked, no twin),
the projection of the
bridge's exact Knuth-hash kick vector (reproducible in Python from vertex
count alone) onto the span of each shaped pattern's induced z-fields.

**Pinned verdict rule (decided before computing):** the hypothesis survives
only if parked patterns' projections separate BELOW their scored twins'
(threshold pinned at plan time; expectation order-of-magnitude). A parked
pattern reading dof 0 also falsifies. Falsified → STOP the K build, report the
finding; the K-fail routing (T validates on non-kick-blocked reads only,
coverage hole flagged) takes over.

### K.1 — the kick (capture harness only)

In `sim_capture`, before `postMessage({type:'loadFold', …})`: compute the flex
basis of the pattern being sent; build the z-field from a deterministic basis
combination (rule pinned at plan time; leading candidate: `pose_pregate`'s
front-selective direction when defined, else the deterministic sum of basis
fields); normalize to max-|z| = 2e-4 (the validated amplitude); send
`vertices_coords` as 3D. Fallback: dof 0 → send 2D unchanged (bridge hash-kick
behavior preserved). Carried trap: the z-lift/`tracked_points` ratio-check
interaction (PR #35) — the harness kick goes through the same accommodation
the bridge kick has; pinned as a test.

### K gates (pre-pinned; validation ≈ 16 of 25 reads, controller-run)

Same-session baseline ×3 opens. Then:

- **(a)** `front_v18|outside|30|0.5` and `frontpair|outside|142.5|0.35` become
  scoreable ×3 (no vacuous-pass parks).
- **(b)** mirror-twin |Δ| symmetry front_v13 vs front_v18 within the ±7° band.
- **(c)** no regression: `front_v13|outside|30|0.5` ×3 re-reads within band
  (same triple serves gate b) AND `probe_dog_folds` tripwire stays green
  (served dog folds ~1.59).

back_v12 ×3 measured and reported, NON-gating. Terminal gate-1 cells never
re-measured.

## 4. Phase T — the structural compile search

### T.1 — promotion: `mcp_harness/flex_extension.py`

API: `assemble(fold)` (interior-vertex reduction: pure-flat vertices dropped,
single-M/V collinear vertices pinned f=0, genuine vertices through the
kernel), `constructive_tau(fold)`, `kernel_nullspace(fold)`,
`second_order_defect(fold, w)` (relative defect + coarse/fine h-pair),
`continuation(...)`, and `obstruction_verdict(fold, w) → EXTENDING |
NON_EXTENDING | REFUSED(reason)` enforcing the calibration contract (anchor
first, refuse on drift: deg-4 first-order dof 2 → finite dof 1; extending
defect ~1.6e-8 vs phantom 0.336). Consumes ONLY merged
`rigid/kinematics/closure.py` (Codex phase-2 branch re-checked at build time:
5 commits unmerged as of kickoff; never import from unmerged branches).
`probe_flex_extension.py` shrinks to a thin CLI; its 7 tests port and grow
library-level cases; dog-substrate tests keep `needs_flex_json` guards.

### T.2 — the search driver (working title `structural_search.py`)

Per-candidate funnel, all sim-free: family generator → Tier-2.5 feasibility
gate (existing; shields the compiler) → spawn-compile (no GPU) →
`square_complete` → `folding_dof` + D1 `front_selectivity` (**stage 1: r\* ≥
1.0**) → `obstruction_verdict` (**stage 2: relative defect < τ, h-stable**).
Families per decision 4; breadth per decision 5. Every funnel result → an
uncommitted `.out.jsonl` ledger. `continuation()` corroborates graduating
passers before any sim spend.

### T gates (pre-pinned; controller-run, ≤ 90 reads, only after K's verdict)

Per graduating base: fresh baseline ×3 (new base, same session; carried ±7°
drift rule) → `pose_pregate`-ranked op exploration → **sim CONFIRM = front ≥
+20° toward the fox target 134.83, mean of 3 standalone reads from the NEW
unshaped base.** On CONFIRM only, payoff fires: whole-pose ≤ 104 ×3 with ops
on the new base (measure, never predict — anti-additivity stands;
`pose_pregate` ranks the menu).

### T routing (every ending valid)

- Search exhausted, zero pre-gate passers → verdict "no nearby tree admits a
  finitely-front-mobile compile under studied interventions" → charter the
  molecule/design-theory follow-up; end honestly.
- Pre-gate passer that the sim refuses → instrument-vs-reality calibration
  finding; document, do not force.
- K-fail → T validation proceeds on non-kick-blocked reads only; coverage
  hole named in the verdict.
- CONFIRM + payoff → headline; follow-up = pose-search-on-mobile-base slice.

## 5. Phase P — productization; Phase 0 — CI

### Phase P (independent; fires regardless of K/T)

All load-bearing machinery is merged and proven: `ide_shape_ops` wrapper (ops
ride serve-side; raw fold never carries them), display replay, Model-tab
auto-switch, strain-oracle loop (`IDE_STRAIN_MAX`, capped retries). P is
wiring plus contract: after a dog-template compile passes lint, the agent
proposes the pose — B2 suggest-then-confirm, likely a small self-verifying
`suggest_pose_stack` tool that checks the compiled base actually exposes the
incumbent's site (`front_v18`) before offering the stack with its measured
payoff (272.49 → 119.14); on confirm, ops ride the existing wrapper and the
oracle loop closes. Tool-vs-prompt split is a plan-time detail.

**P gates (pre-pinned):** live e2e demo on Groq
(`LLM_MODEL=meta-llama/llama-4-scout-17b-16e-instruct`): compile → suggest →
confirm → posed dog renders in Model tab with oracle PASS; SYSTEM_PROMPT
contract pin-tested; backend + web suites green (baseline 668/4 + 40);
provenance contract untouched.

### Phase 0 (bounded ~30 min, conditional)

Check Actions billing first; still blocked → skip, one line in the handoff.
Unblocked → re-run checks on main; expected 664 passed / 8 skipped + web 40;
mesh-snapshot drift (~1e-3 cross-arch) → deliberate re-bless per the PR #41
body (`make bless`; commit ONLY the snapshot regeneration, labeled as such).

## 6. Code layout

- **New `mcp_harness/flex_extension.py`** — stage-2 library (§4 T.1) + its
  tests.
- **New z-field primitive** — home decided at plan time (candidate: inside
  `flex_extension.py` or a small sibling; NOT `rigid_fold.py`); used by both
  K.0 and K.1.
- **Modified `mcp_harness/sim_capture.py`** — flex-informed pre-lift at the
  `loadFold` seam (§3 K.1) + tests.
- **New K.0 probe** (working title `probe_kick_projection.py`) — the
  falsification check; writes an uncommitted `.out.json`.
- **New `mcp_harness/structural_search.py`** (working title) — the T.2 driver
  + tests; uncommitted `.out.jsonl` ledger.
- **Shrunk `mcp_harness/probe_flex_extension.py`** — thin CLI over the
  library; identical output contract and refuse behavior.
- **Phase P** — `agent_loop.py` SYSTEM_PROMPT + tool wiring (plan-time
  detail), pin tests; NO bridge changes anywhere.

## 7. Testing

- `flex_extension`: 7 ported probe tests + library-level — anchor
  refuse-on-drift, τ-gauge validation (degree-4 (1,1,−1,−1)),
  artifact-reduction units (drop/pin/genuine), defect h-stability contract.
- z-field primitive: first-order face-planarity check, nonzero on dof ≥ 1,
  analytic degree-4 case; hash-vector reproduction pinned against
  ide-bridge.js's constants.
- Capture kick: payload-is-3D unit test, bridge stand-down (`all2d` false),
  amplitude pin (max-|z| = 2e-4), dof-0 fallback, tracked_points-ratio
  accommodation.
- Search driver: funnel units with a stubbed compiler, ledger schema,
  early-exit/distinctness logic, Tier-2.5 gate wiring.
- P: SYSTEM_PROMPT contract pin test; web suite stays 40.
- Any new artifact-dependent test carries a `needs_flex_json`-style skipif
  guard (CI cannot regenerate GPU-captured inputs).

## 8. Process & logistics (house rules carried)

- SDD: writing-plans → subagent-driven-development; judgment-bearing prose
  briefs; gate-per-package sizing; reviewers verify against pinned gates;
  checkpoint long investigations to the ledger as they go.
- Controller-only for ANY headed-sim run (subagent sim processes get
  orphan-killed). Full suites via nohup + log-poll, never bare foreground.
- Preflight: regenerate `probe_front_flex.out.json` (expect r\* 1.76272 /
  captured 0.904 / reconcile 162 = 114/12/36/0, else STOP) and
  `probe_flex_extension.out.json` (expect NON-EXTENDING + anchor PASS).
  Coupling JSONL sourced read-only from the main checkout.
- Margins ≫ drift: ±7° shaped re-reads (one +8.5° session-drift datum
  exists); any < 10° comparison needs ×3 and same-session baselines. Pin
  gates BEFORE measuring, always.
- Probe outputs (`*.out.json`/`.jsonl`/`.log`) and suite logs uncommitted;
  never `git add -A`. Human merges every PR; ask before push. playwright
  lives in `mcp_harness/.venv` only; SimSession is HEADED; dist/ gitignored
  (cp public→dist load-bearing).
- Shared checkout: Codex active on `codex/rigid-origami-phase-2-topology-fold`
  (5 unmerged commits at kickoff); re-check merge state before building T.1;
  read main's state through git, not the main checkout's working dir.
- Slice end: outcome handoff doc; routing verdict names the follow-up for
  EVERY phase outcome (T-land → pose-search-on-mobile-base; T-refuse →
  molecule/design-theory charter; K-fail → kick root-cause slice; P always
  ships).

## 9. Out of scope

- Any bridge (`ide-bridge.js`) edit — the capture-harness site makes the
  HALT clause unreachable by construction.
- S1-style composition work beyond T's payoff gate.
- Molecule-level corner creasing (option 3, standing recommendation against).
- Changes under `rigid/` (Codex's namespace) or imports from unmerged
  branches.
- Re-measuring terminal gate-1 cells; making back_v12 a gate.
- Fixing display-replay parking for future shaped patterns (named follow-up
  if it ever bites).
