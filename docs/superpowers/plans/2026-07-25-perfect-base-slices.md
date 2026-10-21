# Mission: Perfect bases from any query — conditioning-first slices, prior-art-hardened

Charter: make a single query reliably serve a "perfect" uniaxial base — (a) all
anatomy (leaf count == reference R, pairs kept), (b) compiles exactly (no nudge
marker) or via a proportion-preserving rescue, (c) lints Pass-or-BENIGN — by
moving every structural rule from LLM prose into deterministic code and
exposing the engine remedies Lang already wrote. Synthesized from the
2026-07-25 12-agent research workflow (7 recon incl. a live 907-compile rescue
experiment, 3 adversarial proposals, 2 critiques) plus the 5-angle landscape
survey (67 systems). Full agent outputs: session scratchpad `wf/` and `wf2/`.

## Evidence base (one paragraph)

The extractor already finds the correct 6-flap dog (fidelity 1.00, two voxel
resolutions); the PACKER rejects it. Node-order restarts alone rescue 45.8% of
attempt-0 pack failures (20.8% unreachable by the shipped ±10% length ladder,
~9x cheaper, zero proportion drift, deterministic); order+ladder+composition =
54.2% vs 29.2% shipped. The residual hard class is "polygon network is not
valid" (11/13 unrescued) — exactly what Lang's stub/edge-opt remedies target,
and both are vendored, compiled, and unexposed in our own wrapper, along with
a dormant per-node x/y placement hook whose golden-angle-by-list-order
fallback IS the node-order knife-edge. Our length-jitter ladder automates the
one remedy Lang never uses. COrigami independently measured the same
bottleneck at n=66k (74.4% of automated TreeMaker deaths at CP construction).
Packing is NP-hard — knife-edges are inherent; the field's answers are
multi-start, constraints, discretization.

## Prior-art adaptations folded into this plan

(Landscape survey 2026-07-25; memory: origami-landscape-survey. Verified: no
existing system mirrors the product; mesh→tree→TreeMaker, grounded
conversational origami, and the learned feasibility gate are unique to us.)

| Adaptation | Source | Lands in |
|---|---|---|
| Error-category → fix-recipe table retrieved into repair prompts (98.5% compile-error fix rate) | RTLFixer, NVIDIA DAC'24 (arXiv 2311.16543) | Slice 2 envelope + Slice 7 prompt |
| Breadth-over-depth rescue budget: many diverse initial variants, shallow repair, beats deep ladders at fixed budget | "Is Self-Repair a Silver Bullet?", ICLR'24 (arXiv 2306.09896); matches our 7/10-first-restart measurement | Slice 3 ladder policy |
| Inner loop = execution errors, outer loop = exact kernel measurements vs spec, separate judge role | CADSmith (arXiv 2603.26512) | Slice 2 envelope shape, Slice 7 oracle |
| VLM self-generates per-query yes/no anatomy checks answered against renders | CADCodeVerify, ICLR'25 (arXiv 2410.05340) | Slice 7 [ANATOMY] oracle |
| Multi-axis eval (compiles / lints / folds-in-sim / anatomy as separate reported axes, never one verdict) | MUSE benchmark (arXiv 2605.28579) | Slice 1 scorecard |
| Negative corpora: 186 impossible CPs + 350 strict CPs as gate/lint calibration fixtures | GamiBench (2512.22207), OrigamiSpace (2511.18450) | Slice 1 (optional import) |
| Differential-test oracles for our TreeMaker fork: same tree in, compare CP out | Tessellatica (Lang's own Mathematica tree theory), TreeFaker (MIT 6.849 JS port) | Slice 1 eval tier (offline, optional) |
| In-browser Maekawa/Kawasaki pre-lint + Maekawa-satisfying M/V permutation enumerator (JS) | Rabbit Ear (rabbitear.org, maintained) | Slice 7/UI; M/V solver cross-check |
| Symbolic pre-execution contract checking (multi-step pass 30%→84%, tool calls halved) | Structural Verification for EDA (arXiv 2604.18834) | Slice 7 validate_tree |
| Reeb-graph skeletonization + exact topological pre-gate before geometry | Autoknit, CMU TOG'18 | Slice 8 extraction fallback (probe first) |
| MCTS over discrete, feasibility-checked edit moves; foldable-by-construction action space | rigid-origami gym, IJCAI'23 (arXiv 2211.13219) | Contingency if Slice 3+4 plateau |
| Agent-in-the-loop synthetic corpus + compile-verdicts-as-preference-pairs (DPO) | Zero-to-CAD (arXiv 2604.24479), CADCrafter (CVPR'25) | Slice 8 / Stage 2.4 retrain |
| ILP/MILP global M/V assignment formulations | Computers & Structures 2020; Hull 4OSME | Cross-check for the shipped 2.3 T-join solver |
| Joint-angle-annotated tree → simple-fold shaping ops; constraint-projection form-finding | COrigami §tree-shaping; Crane/Freeform Origami (Tachi) | B5 pose pillar (out of scope here; noted for next B5 iteration) |
| CP → human folding instructions (unpopulated product gap: only Creasy + Akitaya SIGGRAPH'13 + ReferenceFinder landmarks) | — | Future product slice; no competitor has it |

Explicitly rejected after critique: vector RAG (unanimous — knowledge is
procedural + page-sized; compile it into code + cheat-sheet), interactive
agent topology MCP tools (no measured failure needed an LLM topology
decision), book/diagonal both-compile at serve time (breaks attempt-0 happy
paths), standalone sliver contraction (measured dud 0/12), blanket MAX_LEAVES
lift, box-pleating backend (only if a persistent >8 wall survives
structure-gated admission), VLM anatomy scoring (deterministic counts give the
same signal).

## Sequencing rules (binding)

1. Stage 2.3 (D→B→A→C) SHIPPED 2026-07-25 (M/V solver, dog 5→0 [BENIGN], live
   smoke 5/5) — the "wait for D/B" gates are cleared. What remains binding:
   the ladder restage (Slice 3) churns test_ladder_audit/test_capture pins and
   changes which rung serves previously-nudged subjects → ONE coordinated
   re-bless, never loosened pins, and B5 pose recipes recompute from the newly
   served fold (suggest_pose_stack caveat).
2. x/y placement seeds NEVER ride in the node dicts that reach attempt-0 —
   the wrapper hook (TreemakerWrapper.cpp:216-229) fires whenever x/y is
   present. Seeds travel a side-channel the server injects only at the
   placement rung.
3. Edge-opt (Optimize Selection) LENGTHENS slack edges with no nudge marker —
   every metric counts edge-opt serves as proportion-CHANGED. No metric
   channel may reward silent anatomy stretch.
4. Fidelity is reported UNCLAMPED (fish = 8/10, not 1.0). Stub flaps are a
   separate STRUCTURAL column and can never satisfy anatomy targets.
5. All live compiles, blesses, C++ builds run from the MAIN checkout
   (worktrees lack .venv/.so; borrowed .so inflates failures 27 vs ~3).
6. Structured envelopes keep the "ERROR:" string head and stay under (or are
   whitelisted past) agent_loop's 2000-char history trimmer; CP AUDIT / STRAIN
   ORACLE contract strings stay byte-identical.

## Slice 1 — Truth + baseline (small; zero served-base behavior change)

- compiles_to_fold returns (ok, error_text); trace rows record the error
  (mesh_to_tree.py:391-394, :505-508).
- mesh_report._fidelity_lines reads the trace: when a fidelity-1.0 row has
  compiled=False, replace "likely collapsed by pruning" with "the
  full-anatomy tree WAS extracted (voxel V, prune P) but failed to pack
  (ERROR after N tries)" and route to tree-conditioning, not the A-9 fill
  recipe. Unit test: zero pruning-blame reports while such a row exists.
- TRUST guardrail split (mesh_report.py:92-124, agent_loop.py:141-146):
  PROPORTIONS trusted/never rescaled vs STRUCTURE (slivers, hubs, order) =
  sanctioned levers.
- Commit fixtures/anatomy_reference.json {subject → R, expected_pairs}:
  quadruped 6/2, bird 4/2, humanoid 5/2, fish 10/?, insect 9/3, dog 6/2 —
  values already test-pinned as leaf curves.
- benchmark_subjects.py: per-subject row {R, served_leaves, served_fidelity
  (unclamped), pairs_expected, pairs_kept, attempt0_pack, rescue_stage,
  nudge_marker, asymmetric, lint_class, error_codes} — MUSE-style separate
  axes, one row per fixture subject; fish = deterministic >8 subject;
  cached-dog/live-HF stay env-gated.
- cases.py tripwires (bless from main checkout): raw 6-leaf dog pinned
  CLEAN-ERR (flip to PASS = forced conscious re-bless), hand-repaired dog
  pinned PASS + golden geometry, insect 0.25-vs-0.24 knife-edge canary, 4
  templates gated attempt-0-exact via compile_tree with marker absence.
  *(S1 measured deviation: the repaired dog packs attempt-0 exact but lints
  FAIL-LINT[BENIGN] — the documented hull-frontier ACCEPT class, within the
  charter's Pass-or-BENIGN acceptance — so its pin is FAIL-LINT[BENIGN], the
  measured truth, not bare PASS. Do not "fix" the pin toward PASS.)*
- Extend baseline vocabulary to FAIL-LINT[BENIGN|REAL|MIXED]
  (runner.verdict_for currently collapses them).
- Optional, cheap: import GamiBench's 186 impossible CPs as a negative fixture
  set (does the lint stack reject all 186?); wire Tessellatica/TreeFaker as
  offline differential oracles for fork-regression hunts (not CI).

## Slice 1.5 — Probes (1 day, scratchpad scripts, main checkout)

- Probe A: canonical pairs-first + 4 seeded order restarts on the RAW failing
  6-leaf dog tree — does order alone rescue the dog?
- Probe B: x/y placement seeding (skeleton pos + mirrored-pair layout) on the
  dog + ~10 cohort failures — placement has ZERO measured rescues today; do
  not build Slice 3 stage 2 without this probe paying.
- Probe C (only if A and B miss the dog): throwaway binding calling
  tmStubFinder::TriangulateTree then build_and_export on the dog tree —
  de-risks Slice 6 before real C++ commitment.
- Probe D (only if slivered skeletons persist through Slice 4): Autoknit-style
  Reeb graph over geodesic distance as an alternative skeletonizer on the dog
  mesh — decides Slice 8's extraction bet.

## Slice 2 — Serve the right tree + structured envelope (small, Python)

- Drain-before-downgrade (mesh_to_tree.py:503-516): return early only on
  fidelity 1.0; else hold the success, drain remaining phase-1 candidates
  (bounded ≤6 extra ladder runs, failure path only). Enumerate the
  extraction-snapshot blast radius across the 5 fixtures BEFORE landing.
- _compile_with_perturb returns {code, scale_at_failure, stage_reached,
  rungs_tried, distinct_errors, suggested_lever} — CADSmith split: this is
  the INNER (execution-error) channel; Oriedita/audit numeric deltas are the
  OUTER (measurement-vs-spec) channel. suggested_lever comes from a curated
  error→recipe table (RTLFixer pattern): POLYS_MULTIPLE_IBPS → order restarts
  exhausted? → stub/triangulate on named polys; scale<0.05 → over-constrained;
  NOT_LOCAL_ROOT_CONNECTABLE → rehome root; polygon-network-invalid →
  normalizer/edge-opt. Retire the wrapper's contradictory advice text.

## Slice 3 — Staged rescue ladder (one coordinated re-bless)

Stages: (0) exact tree, byte-preserved → (1) canonical pairs-first order + up
to 4 seeded deterministic order restarts → (2) x/y placement seeds via
side-channel, ONLY if Probe B paid → (3) legacy length jitter, demoted →
(4) composition (order+jitter; measured +1). Policy per ICLR breadth-over-depth
and our own saturation data: wide and shallow — 4 order restarts capture 9/10
of order's value; do not deepen any stage without measured marginal rescues.
frame_title names the serving stage; capture rows gain superset-legal keys
(rescue_stage, order_variant). Keep audit-preferring selection across stages
(3/11 measured order rescues linted MIXED — the shipped 2.3 solver is the
designated consumer). Expected: cohort rescue 29.2% → ~50%+ (54.2% measured
union), dog-class serves with zero proportion drift.

## Slice 4 — Composed normalizer (variant generator, honestly scoped)

normalize_tree = interior-ONLY sliver contraction (<0.08×max, flap-count
preserving; leaf-sliver deletion banned) + root rehoming to ≤2-3 hubs by
pair/axial position (label_leaves already computes coordinates) + canonical
order. Wired as (a) phase-3 compile queue tried only after phase-1/2 drain
(first-FOLD-wins protects every currently-compiling fixture), (b) ladder stage
between order and jitter. structural_prefilter routes root>4 rejects THROUGH
the normalizer, but repaired candidates stay PINNED to the phase-3 queue —
never re-admitted upstream of phase-1 ranking (silent-golden-churn hole both
critics caught). Evidence honesty: composed form is n=1 (the hand-repaired
dog); contraction alone is a measured dud — this slice is a variant
generator, not a standalone fix.

## Slice 5 — C++ diagnostics (small, read-only)

Map GetCPStatus badPolys → mRingNodes → JSON node ids via reverse mNodeMap
(guard engine parts absent from the map, e.g. future stub nodes); attach to
the Slice 2 envelope. Rides the established debug_poly_report binding
pattern. The engine computes exactly which flap cluster is bad; the wrapper
currently discards the lists (TreemakerWrapper.cpp:838-848).

## Slice 6 — Automatic engine repair (large; conditional on residual; Probe C informs)

- tmEdgeOptimizer slack pass (Lang's documented step 2) — FLAG-GATED behind
  the scorecard before default-on (adjacent to the documented strain-path
  flat-foldability regression, server.py:88-94); serves counted
  proportion-CHANGED per rule 3.
- tmStubFinder FindLargestStub/AddStubToTree/TriangulateTree as final rescue
  stage, firing only on POLYS_MULTIPLE_IBPS / POLYS_NOT_VALID survivors of
  stages 1-4. Stub flaps returned with new ids + lengths (AddStub bypasses
  mNodeMap — bookkeeping required), labeled STRUCTURAL in frame_title,
  report, and scorecard; blank-stub → honest error. Classified-lint gated
  before default-on. Server-side automatic = validated offline on the 24-row
  cohort, zero LLM budget. Agent-facing stub/absorb tools stay deferred until
  this stage measurably strands cases needing semantic placement choices.

## Slice 7 — Agent contract (after server surfaces stabilize)

- validate_tree tool: schema, parents-before-children, root-children cap, hub
  grouping, pair coverage, length bands — symbolic pre-execution contract
  (EDA precedent: pass rate 30%→84%, tool calls halved). Malformed trees
  never reach the C++ crash path.
- get_template(body_plan) returns template JSON (retires ~680 prompt tokens);
  coded compile/gate budget counters in agent_turn (MAX_AGENT_STEPS proves
  the pattern).
- [ANATOMY] end-of-turn oracle mirroring CP AUDIT: served leaves + pairs vs
  anatomy_reference; ONE synthetic retry, inform-only stand-down, guarded on
  mesh-report presence, SUPPRESSED for R-unservable subjects (fish until >8
  admission) and fake-provider wrong-R. CADCodeVerify upgrade: derive
  per-query yes/no checks at draft time ("8 distinct leg flaps?"), answer
  against the fold render, feed failures as targeted repair.
- Prompt diet ~2k of 5.7k tokens; add the ~1.5-2k-token compiled cheat-sheet
  (flap-placement economics: corner ¼ / edge ½ / middle 1; stub semantics;
  scale-collapse diagnostic; error→recipe pointers). NO vector RAG.
- Optional UI: Rabbit Ear in-browser Kawasaki/Maekawa pre-lint the moment a
  CP arrives, before the Java round-trip.
- All prompt-behavior changes validated in ONE batched paid RUN_AGENT_SMOKE
  A/B against the Slice 1 scorecard.

## Slice 8 — Extraction + corpus (last; coordinates with Stage 2.4 retrain)

- Pair detection: free the reflection-plane offset along the PCA normal,
  optimal-assignment matching (not greedy index order), boost shared-hub
  near-equal-length candidates, escalate SYMMETRY_TOL on the
  unpaired-lateral tripwire label_leaves already computes. (Pairs are doubly
  load-bearing: engine mirror constraint + symmetric ladder jitter.)
- Structure-gated 9-12-leaf admission: past structural_prefilter only
  post-normalizer (hubs ≤3, ≥2 pairs, no slivers), queued after raw
  candidates; generates the >8-leaf ladder rows the corpus has zero of
  (perturb_pack is null on ALL 2600 rows).
- Rescue/normalizer provenance to a separate gitignored jsonl (source tag, no
  ids, no gate field); the capture-merge remains sole id assigner; add the
  never-sort-nodes dedup test (order variants must stay distinct rows).
- Gate retrain (Stage 2.4, currently deferred on data volume): add structure
  features (min-interior-edge-ratio, root-children, per-hub leaf counts,
  order-canonicality — today's 7 features are order-invariant and
  structure-blind). Upgrade the bootstrap per Zero-to-CAD: agent-in-the-loop
  labeled tree synthesis inside the compile/lint environment, curated by
  diversity; capture verdicts double as DPO preference pairs for the drafting
  prompt (CADCrafter pattern).
- Extraction fallback if Probe D paid: Reeb-graph skeletonization module
  behind a flag, snapshot-diffed against the voxel-thinning baseline.

## Contingency

If Slices 3+4+6 leave the cohort rescue rate below ~70% or a persistent >8
wall stands after structure-gated admission data exists: (a) MCTS over
discrete tree-edit moves scored by the gate (rigid-origami gym template)
replaces the linear ladder; (b) the box-pleating backend (BP Studio / COrigami
backtracking packer) becomes the discretization escape hatch. Neither is
built speculatively.

**The ~70% trigger did not fire: the measured serve rate is 75% (18/24) as of
S5b.** The residual is 6 rows, all one class, and S5's leaf-count control
explains them: the wall is a LEAF-COUNT phenomenon (k=8 flat at ~35% compile
rate at every jitter level), so the remaining rows are asking the packer for
something it fails at ~2/3 of the time regardless of conditioning. That routes
to Slice 8's structure-gated 9-12-leaf admission, not to the contingency.

**EDGE-OPT lives here, not in a flag.** `tmEdgeOptimizer` was measured in S5 at
**0 of 9 standalone across 562 arms** (all-edges, singles, pairs,
longest/shortest, loose set, complement, greedy coordinate ascent). Over ALL
edges it writes one shared strain scalar, which is a uniform rescale and
provably redundant with scale optimization -- so a near-zero achieved strain
there is a TAUTOLOGY, not evidence of no slack (single-edge subsets reach 1.70).
It compiles a row only as a FINISHER after a >=0.70 strain SEED, i.e. 7x-24x the
shipped +/-10% jitter budget, so every such serve is proportion-CHANGED per
rule 3 and far outside the ladder's envelope. Shipping it flagged-off would buy
a stage, a marker in the (now five-member) lockstep, a scorecard column and a
flag for zero measured value. **Reopen only with a NEW measurement that beats
0/9** -- this pointer is the record, and there is deliberately no dormant code
to re-enable. (`tmStrainOptimizer`, already bound as
`run_strain_optimization_and_export` and deliberately off the serve path, is
likewise a clean negative on all 9: it MINIMIZES mean-square strain and 0 is
feasible.)

## Metrics (all from Slice 1 scorecard; separate axes, never one verdict)

- Anatomy: served_leaves/R unclamped per subject; pairs_kept/pairs_expected;
  asymmetric-nudge → 0 on symmetric subjects; stub flaps separate column.
  Acceptance: dog serves 6/6 with both pairs (today 5/6, 1/2).
- Rescue coverage on the committed 24-row cohort: 29.2% baseline → ≥50%
  (Slice 3, measured floor) → residual tracked per error class (Slice 6
  owns polygon-network-invalid). No ≥70% promise — that was refuted as
  extrapolation.
- Proportion integrity: fraction of serves with ANY length change (jitter
  marker OR edge-opt flag) falls monotonically.
- Exactness canaries in make test: 4 templates + repaired-dog attempt-0 exact,
  marker absent; dog CLEAN-ERR flip = conscious re-bless event.
- Lint: % serves Pass-or-BENIGN under the extended vocabulary; MIXED rescues
  routed to the shipped M/V solver, routing rate tracked.
- Report honesty invariant (unit-tested) + agent efficiency (steps per served
  base; C++ crashes from malformed trees → 0 via validate_tree).

## Session partition (model + effort per session)

One re-bless event per session, maximum. Every session runs live compiles /
blesses / C++ builds from the MAIN checkout. Effort tiers are Claude Code
reasoning-effort settings (medium / high / xhigh / max).

Model note: "Opus 5" rows mean top-tier Claude 5 — **Fable 5 at the same
effort tier is an equal substitute**. Pick ONE and keep it across S1–S7 so
behavioral baselines (especially S6's paid smoke A/B and the scorecard) are
not confounded by mid-arc model switches. S8's Sonnet 5 downgrade stands
either way. The product's own agent under test (S6 smoke) is the provider's
claude-sonnet-5 — independent of the dev-session model.

Ultracode: EVERY session starts with the `ultracode` keyword (stage23-mission
precedent). Its payoff concentrates in: (a) adversarial multi-agent review
before the session's single re-bless — MANDATORY for S3 and S5, the
silent-blast-radius sessions; (b) parallel blast-radius enumeration (S2
across the 5 fixtures); (c) S6's prompt A/B design and smoke-result
adjudication. Mechanical bless/build/commit steps stay solo.

| # | Session | Slices | Model | Effort | Why this setting |
|---|---------|--------|-------|--------|------------------|
| S1 | Truth, baseline & probes | 1 + 1.5 | Opus 5 | high | Bless discipline + probe interpretation; probe results route S3/S4/S5 scope. Wrong baselines poison every later measurement. |
| S2 | Legible failure | 2 + 5 | Opus 5 | high | Changes WHICH base serves (drain-before-downgrade blast radius) + first C++ binding (bad-poly ids). Envelope lands end-to-end. |
| S3 | Staged rescue ladder | 3 | Opus 5 | **max** | Highest-leverage behavior change in the plan; golden churn, coordinated ladder/capture re-bless, B5 recipe recompute. Mistakes here are the expensive kind. |
| S4 | Composed normalizer | 4 | Opus 5 | high | Graph surgery + queue-placement correctness (the silent-golden-churn hole both critics flagged). |
| S5 | Engine repair | 6 | Opus 5 | **max** | Hardest C++ in the plan: stub id bookkeeping across part creation/deletion, edge-opt flag-gating against the strain-regression precedent. CONDITIONAL — only if S4 residual + Probe C justify it. |
| S6 | Agent contract | 7 | Opus 5 | high | Prompt rewrites are regression-prone (parity-math-inversion precedent); includes the ONE batched paid RUN_AGENT_SMOKE A/B. |
| S7 | Extraction upgrades | 8 (pair detection, >8 admission, optional Reeb flag) | Opus 5 | high | Optimal-assignment geometry + extraction-snapshot churn; >8 admission generates the first >8 ladder rows. |
| S8 | Corpus + gate retrain | 8 (corpus, Stage 2.4 retrain) | Sonnet 5 | high | Well-templated ML plumbing riding existing precedent (mesh_like family, merge-as-sole-id-assigner). WAITS on capture data volume (retrain deferred 2026-07-25 at 21 nudge rows). Upgrade to Opus 5 if merge/dedup complexities bite. |

Decision gates between sessions:
- After S1: probe results allocate S3 stage 2 (placement — build only if Probe
  B paid), S4 (does the dog need the normalizer?), and S5 (Probe C de-risk).

  **S1 probe verdicts (measured 2026-07-25, main checkout, scratchpad
  `probe_a_results.json` / `probe_b_results.json`):**
  - **Probe A: MISS.** Order alone never packs the raw 6-leaf dog: 0/12
    attempts (canonical pairs-first + 4 seeded restarts, voxels 64 and 96;
    errors: polygon-network-invalid / POLYS_MULTIPLE_IBPS, plus one
    FACETS_NOT_VALID at raw_96/seeded_3 — a third class that also recurs in
    the structural variants, so the S2 error→recipe table must route it).
    Order remains a cohort-level lever (45.8% measured on the 24-row cohort)
    but is NOT the dog's rescue.
  - **Probe B: PAYS — build S3 stage 2.** x/y placement seeding through the
    dormant wrapper hook packs the RAW dog at BOTH voxels with zero
    proportion drift — best outcome: voxel-96 structural mirrored-pair layout
    on the raw order → FAIL-LINT[BENIGN]; skeleton-projection seeds also pack
    at voxel 64 (MIXED). On the 14 order-UNRESCUED cohort rows it adds 2
    rescues (row316 BENIGN, row2324 MIXED) — marginal value on exactly the
    residual "polygon network is not valid" class. Placement rescues often
    lint MIXED → the Stage 2.3 M/V solver is the designated downstream
    consumer, as planned. Seeds MUST stay side-channel (rule 2).
  - **Probe C: SKIPPED by its own gate** (it required A and B to BOTH miss
    the dog; B hit). TriangulateTree stays de-risked only on paper; S5 keeps
    its "conditional on S4 residual" gate.
  - **Probe D: NOT RUN** — its trigger (slivered skeletons persisting through
    Slice 4) cannot fire before Slice 4 exists.
  - **S4 allocation:** the dog does NOT need the normalizer to pack
    (placement suffices), but the composed normalizer recipe is now MEASURED
    reproducible, not just hand-lore: contract-0.0186-sliver + rehome-root-to
    -hub-2 + canonical pairs-first order packs the dog deterministically
    (FAIL-LINT[BENIGN], attempt-0 exact, zero nudges; 5 further
    structure+order variants also pack). n grew from 1 to a scripted recipe —
    S4 stays justified as a variant generator, now with two independent dog
    rescues (normalizer path, placement path) to draw on.
  - **GamiBench negatives (Slice 1 optional): SKIPPED — not cheap.** Verified
    image-only: HF `stvngo/GamiBench` (MIT) ships 777 PNGs; the 186
    impossible CPs exist solely as rasters (vectorizing = a CV subproject);
    OrigamiSpace has no public release. If lint-calibration negatives are
    wanted later, corrupting known-good FOLD files in-house reproduces
    GamiBench's recipe in vector form for less effort.
- **S2 verdicts (measured 2026-07-26, blast-radius enumeration = every
  two-phase-queue candidate compiled for the 5 fixtures + cached dog;
  scratchpad `blast_*_{96,64,128}.json`):**
  - **Slices 2 + 5 SHIPPED.** Envelope validated on real failures: the dog's
    voxel-96 6-leaf failure carries `bad_poly_node_ids [8,3,9,4]`; quadruped's
    v96/0.4 6-leaf phase-1 candidate fails NOT_LOCAL_ROOT_CONNECTABLE (+one
    FACETS_NOT_VALID co-occurrence) and its envelope names rehome-root — the
    direct 5/6→6/6 quadruped path runs through S4's normalizer. Fish's
    v64/0.25 7-leaf (== extractor R) candidate fails polygon-network-invalid
    with the placement/normalizer lever — fish's fidelity ceiling is a
    COMPILE failure, not an extraction gap.
  - **Drain-before-downgrade landed with an ANCHOR amendment the enumeration
    forced:** per-voxel-R fidelity let the dog's degraded voxel-128 skeleton
    (R=5) score a fake clamped 1.0 and flip asym+cp_audit on for zero anatomy
    gain. Drain comparisons now use a MAX-RATCHET anchor over voxel Rs (the
    adversarial review then proved a fixed first-hold anchor INVERTS when a
    feature-losing skeleton holds first -- DI repro: true 6-leaf skipped,
    4-of-6 served; feature loss only lowers R, so max picks the trustworthy
    count). Re-derived from the measured records: ALL 6 subjects keep
    their exact S1 serve; total drain cost = 2 extra failed compiles
    (insect 45.9s chasing a 7th-of-9 leaf; quadruped 40.7s — the ratchet's
    known blind side is over-segmentation, its v64/v128 skeletons read
    R=9/11 vs true 6, so their 7-leaf candidate qualifies; bounded, serve
    unchanged). Drain pays off only once a rescue stage makes full-anatomy
    candidates compile — exactly the S3 handoff.
    Real-path cross-check: the post-S2 scorecard (`--baseline` deltas, dog
    included) moved ONLY the error_codes axis, by design — the 4 rescued
    subjects now name their attempt-0 class (quadruped polygon-network-
    invalid, bird NLRC, fish FACETS_NOT_VALID, dog NLRC); suite gate
    3F/1728P/10S (the 3 = pre-existing rigid hash pins; +43 new S2 tests).
  - **Sliver precedence rule (measured):** a sub-1% edge throws the wrapper's
    polygon-invalid pre-gate text while GetCPStatus diagnoses EDGES_TOO_SHORT
    and names the edge; the envelope carries both (`code` = text class,
    `cp_status` = engine diagnosis) and the lever follows the engine.
  - **Per-voxel R is wildly unstable across voxels** (quadruped v64→9,
    v128→11 vs true 6; bird v128→12; fish v128→14 with an EMPTY queue; dog
    v128→5): any cross-voxel fidelity comparison must anchor, and S8's pair
    detection/extraction work should treat per-voxel R divergence as a
    signal, not noise.
  - **Bird upgrade lever sitting idle:** voxel 64 holds two attempt-0-clean
    full-fidelity 5-of-5 candidates (~1.7s, no nudge, no asym) that queue
    order never reaches; the served v96 bird is nudged+asym (37.8s). A
    voxel-order / prefer-attempt-0 policy is a measured S3 candidate.
  - **Insect's drain payoff is gate-blocked:** the only 8-leaf candidate
    (the clamped-1.0 target for true R=9) passes structural_prefilter but is
    gate-rejected infeasible at p_pack=0.01, so it is never enqueued — the
    same gate mis-ranking debt that forced SEARCH_K=4; routes to the S8
    retrain (structure features).
  - **2.3 handoff item closed:** repair_mv_assignment now strips stale
    cp-audit/mv-repair notes from its input (web reads the FIRST marker; a
    full repair no longer keeps firing the [CP AUDIT] oracle).
  - **S6 note:** agent_loop's SYSTEM_PROMPT error doctrine ("the remaining
    lever is TOPOLOGY — move toward the quadruped template") now contradicts
    the envelope's measured suggested_lever; deliberately NOT touched in S2
    (prompt changes require S6's batched paid smoke A/B).
- **S3 verdicts (measured 2026-07-26; cohort end-to-end through the SHIPPED
  ladder, subjects through the real serve path; scratchpad `cohortF_*.json`,
  `scorecard_final.log`, `diag*_*.log`):**
  - **Slice 3 SHIPPED.** Cohort rescue on the committed 24 rows: **29.2% →
    62.5% (15/24)**, measured through `draft_and_compile_full_base`, not a
    probe kernel. By serving stage: order 8, placement 4, jitter 2,
    composed 1. **12 of the 15 rescues are proportion-PRESERVING** (order +
    placement) against 0 of 7 at baseline; exactly 1 serve is asymmetric.
    Lint: 13 BENIGN, 2 MIXED (both route to the shipped 2.3 M/V solver). The
    request tree was byte-untouched on 24/24 rows — rule 2 verified at the
    serve boundary, not just in the generator.
  - **The dog headline is MET.** The raw 6-leaf dog serves **6/6 leaves, BOTH
    pairs, `rescue_stage=placement`, no nudge marker, no asymmetry,
    FAIL-LINT[BENIGN]** — zero proportion drift, via the voxel-96 structural
    mirrored-pair layout on the raw order (exactly Probe B). A counterfactual
    test pins that the pre-S3 jitter-only ladder still CANNOT rescue it
    (`IDE_LADDER_STAGES=jitter`), so the attribution is not engine drift. The
    plan's stated dog canary could never have shown this: both dog-raw pins go
    through `runner.compile_tree`, the LADDER-FREE engine call, so
    `tests/test_dog_ladder_rescue.py` is the missing ladder-aware evidence.
  - **Per-subject serve deltas vs the committed S1 baseline** (the fixture
    stays the S1 yardstick, S2's precedent; deltas are the report):
    quadruped 5→6 leaves, 1→2 pairs, jitter→placement, asym→False,
    nudge→False, **lint BENIGN→MIXED**; bird jitter→**attempt-0 exact**,
    asym→False, nudge→False, but 4→5 leaves (unclamped fidelity 1.0→0.75);
    dog as above; **fish and humanoid and insect: no anatomy axis moved**
    (fish gains only its `error_codes` class). Proportion integrity:
    nudge_marker true on **4/6 → 1/6**; asymmetric **2/6 → 0/6**;
    attempt0_pack **2/6 → 3/6**. Monotone on every proportion axis.
  - **Composed's marginal value is exactly the measured +1** (cohort row 85,
    order variant `seeded_0` + jitter rung 1); `_COMPOSED_JITTER = 2` is the
    measured minimum with margin — budgets of 3, 4, 6 and 12 buy zero further
    rows, so the stage is not deepened. With `ORDER_SEED = 1000` the order
    stage alone rescues 8/24 (33.3%), not the 45.8% the pre-plan experiment
    measured with a different variant set; placement more than covers it.
  - **★ "It compiled" stopped being a sufficient serve criterion.** A stronger
    ladder makes weak early candidates compile, and `auto_mesh_to_metric_tree`
    served the FIRST candidate that compiled — a rule that was, by accident,
    also best-anatomy-wins only because bad candidates used to FAIL. Measured
    fallout before the fix: humanoid fell from an attempt-0-exact 2-pair serve
    to an order-rescued 1-pair one; fish fell from 6 served leaves to 4. Two
    fixes, both STRICT extensions that leave the S2 max-ratchet anchor
    semantics untouched (all 52 drain/anchor/fidelity pins stay green):
    (a) `_serve_rank` — anchored fidelity still decides between candidates of
    different anatomy, and only TIES on it consult proportion integrity then
    pairs kept; a full-fidelity candidate that needed a RESCUE no longer ends
    the search (this is the S2 "bird lever", now pulled);
    (b) the drain's `in_phase1` exclusion is retired. S2 justified it with
    "phase-2 gate favorites can only yield another downgrade" — true while a
    hold was near-full-fidelity, MEASURABLY FALSE once a 0.5-fidelity
    candidate can hold: both fish's 6-leaf and humanoid's exact candidate sat
    in phase 2. Phase 1 keeps its PRIORITY and now its own budget:
    `DRAIN_BUDGET` is unchanged and phase-2 admissions draw on a separate
    `DRAIN_BUDGET_PHASE2 = 3`, so a leaf-count-mis-ranking gate cannot starve
    phase 1 (adversarial review).
  - **The anchor's over-segmentation blind side is now LIVE, on the bird —
    route it to S8.** Pulling the bird lever serves voxel 64's
    attempt-0-exact 5-leaf candidate (no nudge, no asym: three axes better)
    whose own voxel reads R=5 while the committed anatomy reference says R=4,
    so UNCLAMPED fidelity reads 0.75. The max ratchet picks R=5 BY DESIGN
    (feature loss only lowers R) and S2 already named over-segmentation as its
    known blind side. This is the ratchet operating as specified, not a new
    defect, and it is the strongest case yet for S8's better reference-count
    estimation. Do NOT "fix" it by softening the ratchet — the S2 adversarial
    repro proves the other direction inverts.
  - **quadruped's lint BENIGN→MIXED is a geometry residual, not a labelling
    one.** Its new (anatomically complete, proportion-exact) pack carries 2
    REAL Kawasaki violations of ~3.23° with `mv_fixable: false`, alongside 7
    benign-noise ones at ~1e-6°. The 2.3 M/V solver DID fire (both markers are
    on the served fold) and cleared what labels can clear; angle defects are
    not label defects. The lever is **S5/S6** (stub/edge-opt), or a different
    placement seed — not the M/V solver.
  - **Routing is live and is a permutation, never a truncation.**
    `error_recipes.first_stage_for` resolves the failure class with ONE shared
    resolver (`resolved_code`) that the envelope's `suggested_lever` also
    uses, so the message and the ladder cannot disagree. Precedence is on the
    CLASS, not the lookup: a curated cp_status wins outright (an
    EDGES_TOO_SHORT sliver is not routed on the polygon-invalid text the
    engine already contradicted), while an UNCURATED cp_status falls back to
    the text class — load-bearing, since the raw dog's `POLYS_NOT_VALID` is
    not in the vocabulary at all.
  - **Path parity was a real hazard and is closed.** Both ladder consumers
    share `_drive_ladder`, and the in-child worker now builds attempt-0's
    error through `_worker_failure_payload` — the same string shape the parent
    gets — so both ROUTE identically. Without it, `suggest_pose_stack` (which
    compiles a fold on one path and re-derives leaf locations on the other)
    would silently stop resolving node ids.
  - **B5 pose recipes needed no recompute — verified, not assumed.**
    `tests/bless.py` regenerates goldens and verdicts through
    `runner.compile_tree`, the DIRECT ladder-free engine call, so S3 cannot
    churn `baseline_verdicts.json` or `goldens/` — a bless run produced ZERO
    diff to both. No committed pose recipe persists vertex indices (the
    binding is computed per call); all 91 B5 pose tests pass unchanged. What
    S3 actually owed the re-bless was the test pins, not the goldens.
  - **★ Adversarial review found TWO blockers the tests would not have caught,
    and the second one only because a VERIFIER refused to accept the fix for
    the first.** Worth carrying into S5, the other silent-blast-radius session:
    the refuters were told to try to REFUTE, and the one that could not
    reproduce finding #1 (already fixed mid-review) went looking for the
    consequence anyway and found a deeper cause.
    1. `structural_layout`'s root-children loop omits the sibling stagger that
       `place()` applies deeper, so equal-length UNPAIRED root children landed
       on IDENTICAL seeds — and two coincident seeds SIGSEGV the engine (exit
       -11). Fixed by de-duplicating seeds: a no-op on every collision-free
       layout, so every measurement (the dog's included) is preserved. Adding
       the stagger at the source would move the dog's seeds and is left for a
       slice that can re-measure it.
    2. **Seed collisions were never the necessary condition.** A placement
       candidate can SIGSEGV the engine with a perfectly collision-free
       layout, and `_worker_compile_and_regions` runs the WHOLE ladder inside
       ONE spawned child — so the crash killed every later rung, while the
       parent path (one spawn per rung) treated it as a single failed rung.
       Measured divergence on T = root + 0.5/0.5/0.2: the child returned
       ENGINE_CRASH while the parent served a jitter fold, so
       `apply_shaping_ops` and `suggest_flap_for_region` LOST a base they
       served pre-S3. The child now publishes each rung index through SHARED
       MEMORY and `_run_ladder_child` re-spawns past the culprit (bounded).
       The transport matters: a `queue.put` is buffered by a feeder thread and
       is LOST when the process SIGSEGVs — measured, and the reason the first
       attempt at this fix silently did nothing. Both paths now return the
       identical fold. NOTE this hazard is pre-existing in KIND (a jitter rung
       could always crash); S3 made it likely by adding a candidate class that
       crashes readily.
    3. **The de-duplication in (1) had its own gap, and the same review found
       it:** it enforced uniqueness on RAW floats while `with_seeds` emits
       `round(x, 6)`, so seeds closer than 1e-6 survived dedup and reached the
       engine coincident anyway — 59 of the 2600 committed corpus trees. The
       consequence there is NOT a crash (60 of 61 such candidates exit
       cleanly) but an engine **WEDGE**: corpus_wide row 1586 puts two nodes on
       the clamp corner 2.2e-16 apart and never returns (>500s), so the
       in-child ladder burned its whole 60s budget and reported a TIMEOUT
       instead of the structured compiler error it produced in 2.1s pre-S3 —
       and crash resume does not cover a wedge. Fixed by deduping on the
       EMITTED coordinates (0/2600 collisions; that row now returns its real
       error in 1.6s). Generalisable lesson: **enforce an invariant at the
       precision the consumer actually sees.**
    Also fixed: `IDE_LADDER_STAGES=composed` yielded a zero-rung ladder;
    malformed node dicts raised out of the MCP tool instead of returning the
    envelope; the cp-audit/mv-repair provenance called every rung a "nudge
    rung" on serves whose own title says no length moved.
  - **Latency, measured:** the ladder's worst case grew 24 → 37 rungs on a
    9-node tree (~1.7x on total failures, 30.9s → 51.7s on the parent
    spawn-per-rung path), and a mesh serve pays that per drained candidate.
    `IDE_LADDER_STAGES` is the one-env-var rollback and reproduces the pre-S3
    ladder BYTE-for-byte (pinned paired and pairless).
  - **A bless-time hazard was closed in passing:** `bless.py`'s sanity check
    only proved the ENGINE was alive. A dead JVM or missing oriedita jar makes
    `verdict_for` degrade every PASS and FAIL-LINT[BENIGN] pin to bare
    FAIL-LINT — a wholesale LOOSENING that looks like an ordinary diff. The
    canary now lints star-4 and refuses to bless unless it reads PASS.
  - **S4 allocation:** the quadruped's 6/6 no longer needs the normalizer's
    rehome-root (placement got it there), so S4's remaining justification is
    what it always was — a VARIANT GENERATOR — plus the 9 cohort rows no stage
    rescues. **S5 go/no-go:** the residual is now 9/24, and quadruped's
    2-real-Kawasaki geometry residual is the first measured case pointing at
    S5's engine remedies rather than at tree conditioning.
  - **S6 note (still parked):** the SYSTEM_PROMPT's "the backend already
    auto-nudges your edge lengths" is now incomplete rather than wrong. The
    new stage markers deliberately avoid the phrase "did not pack exactly",
    which the prompt's nudge-relay doctrine is scoped to, so no
    proportion-preserving rescue trips it. Rewording stays S6's.
- **S4 verdicts (measured 2026-07-26; cohort end-to-end through the SHIPPED
  ladder, subjects through the real serve path; cohort ids now COMMITTED at
  `fixtures/rescue_cohort.json`; scratchpad `cohortS4b_*.json`,
  `residual_probe2.json`, `s4b_scorecard.log`):**
  - **Slice 4 SHIPPED, and it rescues NOTHING. That is the result, and it is
    the one S5 needed.** The normalizer is wired both ways the plan specced --
    a ladder stage between placement and jitter, and a phase-3 compile queue
    after the phase-1/2 drain -- and on the committed 24-row cohort it changes
    **zero rows**: 15/24 (62.5%) served, every row's serving stage and lint
    class byte-identical to S3, **0 rows served by normalize**, 24/24 request
    trees untouched. The scorecard reports **"no axis moved"** on all six
    subjects against the freshly re-blessed post-S3 baseline. Nothing
    regressed and nothing improved.
  - **The residual is 9/24 still, and tree conditioning is EXHAUSTED on it.**
    Probed with `MAX_NORMALIZE_HUBS` lifted entirely -- every interior node
    enumerated as a rehome target, compiled directly through the ladder-free
    engine -- **normalize packs 0 of 9**. The hub bound costs nothing. The
    measured reason is structural: **five of the nine (97, 353, 500, 2099,
    2192) are STARS** -- 8 leaves hanging directly off the root, no interior
    node to rehome to and no interior edge to contract, so a structural
    normalizer has nothing to grip; 830 (5 interior nodes) and 865 (4) sit past
    the hub bound and their variants fail anyway; only 90 and 385 generate a
    variant the shipped stage even tries. All nine still share the single
    "polygon network is not valid" class.
  - **★ S5 GO.** The residual is not a conditioning problem. Every
    proportion-preserving lever the tree affords -- order, placement, rehoming,
    contraction -- has now been measured against these nine rows and none
    moves them, while the error class they share is exactly the one Lang's
    stub/edge-opt remedies target. S5 is the first slice in the mission whose
    justification is a measured exhaustion of the alternative rather than an
    extrapolation.
  - **Contraction is UNTESTED by the cohort, and the report says so.** Zero of
    the 24 rows has an interior edge under `SLIVER_RATIO x max`, so no cohort
    number measures sliver contraction; any normalizer delta there would
    measure rehoming and ordering alone. Corpus-wide, contraction fires on
    **21 of 2600 rows (0.81%)** and on exactly **one of the 25 committed cases
    -- `dog-raw`**, the case it was designed for. The stage adds **0.34 rungs
    per corpus row** (573 of 2600 rows get >= 1 variant); it emits **zero**
    rungs on a star, which is why test_ladder_audit's byte-pinned exhaustion
    census ("37 staged rescue rung(s) (order 4, placement 1, jitter 24,
    composed 8)") does not move.
  - **The dog gains a SECOND independent rescue path.** With
    `IDE_LADDER_STAGES=normalize`, the raw 6-leaf dog serves 6 leaves, both
    pairs, no nudge, no asymmetry, FAIL-LINT[BENIGN] -- alongside S3's
    placement rescue. The variant generator generates; the cohort simply has
    nothing for it to generate *for*.
  - **★ The plan's specced composition does not reproduce its own evidence,
    and would have shipped a silently non-packing tree.** Measured:
    contract(node 5) + rehome(root -> 2) + `rescue_ladder.canonical_order`
    yields order [2,0,7,8,1,3,4,6] and the engine REJECTS it ("polygon network
    is not valid after optimization, scale=0.665154"), while the golden
    DOG_REPAIRED is [2,0,7,8,1,3,6,4] and packs attempt-0 exact. They differ
    only in the last two unpaired leaves. Root cause: `canonical_order` emits
    unpaired leaves in the INPUT LIST's order, so it is a function of the list
    it was handed, not a canonicalisation -- correct for the order stage
    (whose job IS re-ordering the caller's list), useless for a stage that has
    just rebuilt it. The normalizer keeps its own `normalize_order` (unpaired
    leaves grouped by their parent's position in the hub prefix), which
    reproduces the golden BYTE-EXACTLY. `canonical_order` was deliberately NOT
    changed: it would move the shipped order stage on live extractions.
  - **The proportion barrier needed a RANK, not a boolean.** Normalize moves no
    length off its requested value but deletes a sub-threshold node, so both
    settings of `preserves` are wrong -- non-preserving lets a clean jitter
    rung displace a normalize pack, preserving blocks jitter AND claims an
    (id,length) multiset identity a contraction falsifies. The barrier is now
    monotone in `rescue_ladder.STAGE_HONESTY`, a STRICT generalisation: with
    normalize absent, "rank >= 2" IS `PRESERVING_STAGES`, so every shipped
    stage keeps byte-identical behavior (pinned). `mesh_to_tree._STAGE_INTEGRITY`
    was rescaled to the same rank and the two are now pinned equal.
  - **DROPPED for lack of evidence: routing structural_prefilter's root>4
    rejects through the normalizer.** `structural_prefilter` ACCEPTS
    root_children == 4 (`<= MAX_ROOT_CHILDREN`), no committed fixture anywhere
    has root > 4, and there is no evidence live extraction produces one. The
    branch would have been built blind.
  - **★ Adversarial review found NINE defects, three of them blockers, and the
    committed golden actively CONCEALED two of them.** 73 agents, 20 findings,
    65 verdicts. The blockers:
    1. `_annotate_rung` -- "the ONE served-fold annotation entry point" --
       omitted STAGE_NORMALIZE from its dispatch tuple, so `_annotate_stage`'s
       normalize branch was dead code and **every normalize serve shipped
       UNMARKED**. That is the silent-wrong-serve hazard in full: served_stage
       falls through to "none", the candidate takes top integrity, the terminal
       `fid >= 1.0 and stage == "none"` branch ends the drain early, and the
       scorecard scores attempt0_pack=True for a restructured tree. Nothing
       goes red. A test of `_annotate_stage` would have passed.
    2. `rehome` INVENTED a length: the reversal loop read a value the previous
       iteration had already overwritten, collapsing every edge on the root
       path to the deepest one's. **Invisible on the dog**, whose only rehome
       target sits at depth 1.
    3. `rehome` INVENTED a flap, and **the property check written to pin (2) is
       what found it**: if the old root's only child lies on the path to the
       new root, the reversal leaves it childless and it becomes a leaf
       (corpus row 44, the chain 0->1->2, goes from 1 flap to 2).
       `contract_slivers` had a leaf-set invariant; `rehome` had none, and its
       failure was the mirror image -- creating anatomy rather than deleting
       it. **Also invisible on the dog**, whose root has four children.
    Plus: rehome crashed (KeyError) on a node with no "length", reopening the
    malformed-input regression S3 closed one function over; phase 3 re-graded
    the held serve against an anchor the drain never adopted (fidelity_score
    CLAMPS, so a higher anchor only LOWERS the held score); phase 3's docstring
    claimed "can only win on anatomy" while the code let a repair win a
    fidelity TIE on integrity; phase 3 ordered its budget by RAW leaf count,
    rewarding the ratchet's over-segmentation blind side; `capture.record`
    had no channel for the variant name, making normalize the only rescue
    class whose corpus row could not be replayed; and `test_mesh_to_tree`'s
    live-serve cross-check turned out to be a **FOURTH member of the marker
    lockstep** -- fixed by deleting its duplicate marker list rather than
    extending it, so there is now one place mapping markers to stages.
  - **Phase 3 writes NO capture rows.** The gate's feature vector is
    order-invariant, so two normalize variants of one source carry IDENTICAL X
    with different outcomes (measured on DOG_RAW's `contract` and
    `contract+rehome:2`) -- the duplicate-X reweighting capture.record's own
    docstring exists to prevent, and irreversible once written since nothing
    marks the row synthetic. Feeding repaired trees to the corpus stays Slice
    8's item, where the plan already specifies the shape (separate channel,
    source tag, capture-merge as sole id assigner).
  - **The re-bless was ZERO, and that is verified, not assumed.** `bless.py`
    regenerates goldens and verdicts through `runner.compile_tree`, the direct
    ladder-free engine call, and `tests/cases.py` was untouched, so a bless run
    from the main checkout produced no diff to `baseline_verdicts.json` or
    `goldens/`. What S4 owed was test pins, every one refined rather than
    loosened: the pre-jitter stage set is widened to what is actually emitted
    AND the new stage's position pinned outright (the pre-S4 assertions said
    nothing about where a fourth stage could sit), and three tests whose "only
    a length change can pack" predicate compared `(id, length)` now compare
    length VALUES -- naming the property they always meant, since a rehome
    re-attributes a length across ids without moving one.
  - **Housekeeping the session owed and paid:** `fixtures/scorecard_baseline.jsonl`
    was still S1-era (b7a75c2) and was re-blessed against post-S3 main in its
    own commit BEFORE any S4 code, so S3's wins could not be reported as S4's
    deltas; and the 24 cohort ids -- quoted as "committed" by S1, S2 and S3
    while living only in a session scratchpad -- are now actually committed,
    with the 9 residual ids and both provenance caveats.
- After S4: cohort residual per error class decides whether S5 runs at all.
  **ANSWERED: S5 RUNS.** One class ("polygon network is not valid"), 9 rows, and
  every tree-conditioning lever measured against it and refuted.
- **S5 verdicts (measured 2026-07-27; shipped engine on branch
  `claude/s5-slice6-engine-repair`; every number reproducible from the committed
  `fixtures/s5_engine_repair_evidence.json`):**
  - **★ A latent ODR VIOLATION had to be fixed before any measurement was
    trustworthy, and it would have produced a spurious S5 negative.** Two
    vendored headers declare `class tmTree` behind the SAME guard `_TMTREE_H_`
    -- `Source/tmTree.h` (`mNeedsCleanup` FIRST) and
    `Source/tmModel/tmTreeClasses/tmTree.h` (`mNeedsCleanup` LAST) -- and
    `build.sh` puts `-ISource` first. `tmSolvers/tmStubFinder.cpp` was the ONLY
    `.cpp` outside `tmTreeClasses/` including `tmTree.h` directly, so it read
    `mScale`, `mPaperWidth`, `mPaperHeight` and `mOwnedPolys` at offsets shifted
    by 8 bytes. Latent purely because nothing called tmStubFinder; it fires the
    instant Slice 6 wires it up. Fixed by fully qualifying the include; verified
    with `clang++ -H`. Compile, link AND the 1875-test suite all pass through an
    ODR violation silently -- offsets are not part of symbol mangling and dead
    code never exhibits it. `tests/test_vendor_header_hygiene.py` pins the
    general invariant (no bare include of a shadowed, differing header), not
    just the one line, and is verified to FAIL on the reverted bug.
  - **★ THE ENTRY POINT IS THE WHOLE SLICE, and the obvious one is a trap.**
    The plan and the S5 brief both name `TriangulateTree` as the remedy. It is
    polygon-DRIVEN (loops `mOwnedPolys` for >=4-gons, tmStubFinder.cpp:328-336)
    and on this failure class `BuildTreePolys` has already DELETED every poly
    enclosing an unpinned leaf (tmTree.cpp:1749), leaving 0-2 polys and ZERO
    >=4-gons. **Measured: TriangulateTree adds 0 stubs on 8 of the 9 rows** and
    the 9th (830) fires correctly, +2 nodes, and still fails -- so a probe bound
    to it returns a clean, well-explained, WRONG negative. This session produced
    exactly that negative and only caught it under adversarial review. Lang
    generalised the SOLVER beyond polygons -- tmStubFinder.cpp:43-45 "you can
    apply a stub to any group of four nodes, whether or not they're part of a
    polygon", and FindAllStubs ":142-148" exists to "add a node that PINS a
    group of nodes with the maximum number of active paths". `FindLargestStub`
    over `GetLeafNodes()` needs no polygon network at all.
  - **The residual's mechanism, named at last: POLYS_NOT_VALID means A LEAF IS
    NOT PINNED.** `CalcIsPinnedNode` needs >=2 active paths with no >180 deg gap
    (tmNode.cpp:212-251) -> `CalcPolygonNetwork` grants polygon-node status only
    to pinned-or-border nodes (tmTree.cpp:2144-2200) -> `CalcPolygonValidity`
    fails on any leaf with <2 polygon paths (:2225-2246) -> `BuildTreePolys`
    deletes the enclosing poly (:1749) -> zero polys. Row 97 after scale-opt has
    6 of 28 leaf paths active, with leaves 7 and 8 interior on 1 active path.
    This is why `GetCPStatus` returns POLYS_NOT_VALID with **EMPTY bad-part
    lists** on all 9 rows -- Slice 5's diagnostic, which the S5 brief called
    "Slice 6's input with no adapter", has nothing to hand over, and that
    absence is the diagnosis rather than a Slice 5 defect.
  - **Stub repair SHIPPED as `run_stub_repair(max_stubs)`; it rescues 3 of the 9
    residual rows** -- 385 -> FAIL-LINT[BENIGN] at k=1 (+1 stub flap), 97 (a
    STAR) -> MIXED at k=3 (+3), 2192 (a STAR) -> MIXED at k=6 (+6). Two of the
    three are stars, the rows S4 called structurally ungrippable. The other six
    do not rescue at any k <= 8. Both MIXED serves route to the shipped 2.3 M/V
    solver per the charter.
  - **A stub is a SUPERSET repair and is proportion-preserving by construction.**
    `SplitEdge` sets the two halves to `splitLoc/(1+strain)` and
    `(strainedLen-splitLoc)/(1+strain)` (tmTree.cpp:543-551), which sum exactly
    to the original `mLength`; the stub's own edge is brand new. No requested
    length moves and no existing node moves. So on the "how much of the request
    survived" axis a stub scores the TOP rank truthfully -- while the served
    product carries anatomy nobody asked for. Database-repair theory names the
    trio (subset / superset / symmetric-difference repairs) and they are
    different admissibility classes, not one ordered scale; EDA/ECO and the MVS
    accuracy-vs-completeness protocol both report insertion as a SEPARATE count
    beside a conformance verdict. Hence the binding reports `stub_leaves`
    separately, and the ladder barrier must become lexicographic --
    `(0 if invents_anatomy else 1, STAGE_HONESTY[stage])` -- which is a strict
    generalisation: with stubs absent the first key is constant and the ordering
    collapses to today's, exactly the trick S4 used to replace the boolean.
  - **★ `fidelity_score` is broken for stubs in BOTH directions, and the masking
    one is worse than the plan anticipated.** It is `1 - abs(leaf_count -
    r_eff)/r_eff` (mesh_to_tree.py:1014-1024) and a stub counts as a leaf. For
    the dog (R=6): 5 real + 1 stub = 6 leaves reads a **false 1.000 that hides a
    missing leg**; 6 real + 1 stub = 7 scores 0.833, ranking a successful
    proportion-preserving rescue exactly like a dropped flap. The fix is two
    directed terms never summed (completeness `min(leaves, R)/R` and an
    independent `stub_flaps` count), per the LinLin asymmetric-loss and MVS
    two-directed-distance precedents.
  - **EDGE-OPT: NOT SHIPPED, and the easy negative for it is a tautology.**
    Over ALL edges `tmEdgeOptimizer` writes one shared strain scalar to every
    selected edge (`DataToTree`, .cpp:213-226), which is a uniform rescale --
    provably redundant with scale optimization, measured identical to ~1e-8. So
    "achieved strain 6.1e-09" measures the identity, NOT the absence of slack:
    single-edge subsets reach strain 1.70. Properly tested, edge-opt rescues
    **0 of 9 standalone across 562 arms** (all-edges, singles, pairs,
    longest/shortest, loose set, complement, greedy coordinate ascent). It
    compiles a row only as a FINISHER after a >=0.70 strain SEED -- 7x-24x the
    shipped +/-10% jitter budget, at per-edge shape change 0.33-1.61 -- so every
    such serve is proportion-CHANGED per rule 3 and far outside the ladder's
    envelope. Shipping it flagged-off would add a stage, a marker in the
    four-member lockstep, a scorecard column and a flag for zero measured value.
    Also tested and clean-negative: `tmStrainOptimizer`, already bound as
    `run_strain_optimization_and_export` and deliberately unused on the serve
    path, is a no-op on all 9 (it MINIMIZES mean-square strain; 0 is feasible).
  - **★ The wall is a LEAF-COUNT phenomenon, not a property of these 9 rows.**
    Control: compile rate of a k-leaf star under +/-pct length jitter, N=20.
    It is NON-MONOTONIC at low k (k=4: 3/3 at 0%, **2/20 at 1%**, 20/20 at 30%)
    -- near-ties in the active-path network are ambiguous while exact ties are a
    clean special case, the same mechanism as the committed insect
    0.25-vs-0.24 canary. An EQUAL-LENGTH 7-star fails outright (0/3) while 4, 5,
    6 and 8 pass. **k=8 is FLAT at ~35% across every perturbation level** and
    symmetry pairs do not move it. And the failure CLASS shifts with k:
    POLYS_MULTIPLE_IBPS -- precisely the class Lang wrote the stub remedy for --
    dominates at k=6, while POLYS_NOT_VALID barely exists below k=7 and
    dominates at k=8. That is why the stub stage rescues only a third of the
    residual: it is being asked to fix a class one leaf-count band above the one
    it was designed for. **This is the plan's ">8 wall", now quantified, and it
    is a direct input to Slice 8's structure-gated 9-12-leaf admission: the
    engine's success rate there is ~35% and falling.**
  - **Cohort rescue: 15/24 -> 18/24 (62.5% -> 75%) IF the stub stage is wired to
    the serve path.** NOT YET WIRED -- see "S5 remaining work" below. The 3
    rescues are measured through the engine binding, not through
    `draft_and_compile_full_base`, so 75% is a measured CAPABILITY, not yet a
    measured serve rate. No existing serve changed: the binding is additive and
    the full suite is unchanged at 3F/10S with the 3 pre-existing rigid hash
    pins.
- ~~**S5 remaining work (handoff, deliberately not half-built).**~~ **DONE in
  S5b, 2026-07-27** -- all seven steps landed. See the S5b verdicts below.
- **S5b verdicts (measured 2026-07-27; branch `claude/s5b-stub-serve-wiring`;
  cohort end-to-end through `draft_and_compile_full_base`, subjects through the
  real serve path; scratchpad `step0_results.json`, `cohort_s5b.json`,
  `scorecard_final.log`):**
  - **★ THE HEADLINE IS CONVERTED: cohort SERVE rate 15/24 -> 18/24 (62.5% ->
    75%).** S5's 18/24 was a measured CAPABILITY through the engine binding;
    this is the same number measured through the real serve path, and it lands
    on the SAME three rows -- 385 (k=1, FAIL-LINT[BENIGN]), 97 (k=3, MIXED),
    2192 (k=6, MIXED) -- the SAME rows at the SAME k as the binding. The
    residual falls 9 -> 6: 90, 353, 500, 830, 865, 2099.
    Lint over the 18 serves: 14 BENIGN, 4 MIXED, all four routed to the
    shipped 2.3 M/V solver. **The 15 faithful serves are UNCHANGED** and their
    stage distribution is byte-identical to S3/S4 (order 8, placement 4,
    jitter 2, composed 1) -- no faithful serve was displaced by a stub, which
    is the lexicographic barrier doing its job.
  - **★ STEP 0: re-scaling AFTER the stub is not neutral, it REGRESSES rows.**
    S5 optimized the scale before the stubs existed, so every rescued base
    packed at a scale computed for a tree with k fewer flaps -- a live question
    worth one experiment before building a stage around 3/9. Measured on all 9
    residual rows, k=1..8, two arms: re-scaling rescues **exactly the same 3
    rows at exactly the same k**, and on rows **90 and 500 it DESTROYS a
    polygon-validity repair the stub had just achieved** -- both regress from a
    later-stage failure (NOT_LOCAL_ROOT_CONNECTABLE / FACETS_NOT_VALID) back to
    polygon-network-invalid. The scale moves only ~1e-9 relative, so the
    pre-stub scale is already at the stubbed tree's optimum; the class is a
    knife-edge and the re-solve lands on the wrong side. S5's ordering is
    correct and is now pinned on all three compile paths.
    *(The sweep's first run returned 0/9 on BOTH arms -- python puts the
    SCRIPT's directory on sys.path, not the cwd, so the worker never imported
    the .so. Only the known-answer CONTROL arm, which had to reproduce S5's
    committed 3/9, turned a session-shaped false negative into a one-minute
    fix. Carry the control forward.)*
  - **Rows 90 and 500 are not simply unrescued -- the remedy ADVANCES them.**
    At k>=4 both reach `poly_valid = True` and fail LATER and in a DIFFERENT
    class. So the stub stage moves 5 of the 9 residual rows, of which 3 build.
    This is why the k-sweep terminates on a successful BUILD and never on
    `poly_valid`, which would have declared victory on two rows that still fail.
  - **★ TWO AXES, NOT ONE -- and the scalar rank was actively unsafe.** A stub
    is proportion-PRESERVING and anatomy-INVENTING simultaneously: `SplitEdge`'s
    two halves sum exactly to the original (tmTree.cpp:543-551) and the stub's
    edge is brand new, so on "how much of the request survived" a stub
    truthfully tops the rank, while the served base carries a flap nobody asked
    for. `STAGE_HONESTY["stub"] = 3` AND `INVENTS_ANATOMY = {"stub"}`, with the
    barrier lexicographic over `(0 if invents else 1, honesty)`. This is not
    bookkeeping: the shipped barrier asks `honesty < best`, and **3 < 2 is
    FALSE**, so on the scalar rank a PACKED order rung would fail to stop the
    ladder -- it would climb into the stub stage, and if that stub pack audited
    CLEAN while the order pack was dirty, `_search_first_clean` would return the
    anatomy-inventing serve. Verified exhaustively: 0 disagreements with the old
    scalar on non-stub ladders (byte-identical pre-S5b behavior), stub blocked
    by all six faithful stages, stub-vs-stub correctly does NOT fire so the
    k-sweep continues.
  - **`PRESERVING_STAGES` gains "stub", and that is the truthful reading.** The
    set is documented as a claim about the CANDIDATE ("same node ids, same
    lengths on the same ids"); a stub rung hands the engine the caller's list
    BYTE-IDENTICALLY and the flap is created inside the engine, after
    `build_tree_from_json`. It also has ZERO production consumers (the barrier
    reads `honesty`, not `preserves`), so membership changes no behavior. Both
    pins were refined to cover both axes rather than excepted by name.
  - **★ The plan's own specced fidelity fix was REFUTED before it shipped.**
    S5 specced completeness as `min(leaves, R)/R`. That is monotone
    non-decreasing in leaves, so `min(8,5)/5 == min(5,5)/5 == 1.0`: an
    over-split skeleton would score exactly like a perfect one at the phase-1
    and phase-3 ranking sites -- destroying the anti-fragmentation guarantee
    `fidelity_score`'s docstring exists to provide, and breaking two shipped
    pins. The SYMMETRIC distance form is KEPT over REQUESTED leaves (a stub is
    structurally absent from that count, since no Python node list ever sees
    one) and `stub_flaps` rides an independent axis that is never summed:
    `anatomy_axes`, `served_stub_flaps`, a `_serve_rank` key, and its own
    scorecard column in BOTH `_COLS` and `_DIFF_COLS`. **Honesty note: the lie
    was LATENT, not live** -- no caller passed a stub-inclusive count before
    this slice, because the stub stage is what creates them.
  - **`-stub_flaps` sits AHEAD of stage integrity in `_serve_rank`, and the
    position is forced.** A stub tops integrity at 3, so behind it the key would
    never fire and a stub-repaired candidate would beat an order-rescued one of
    identical anatomy. Ahead of it, anatomy still dominates outright (43k-combo
    brute force: the pre-S5b ordering of every stub-free pair is unchanged).
  - **The lockstep is FIVE members, not four.** S4 believed it had consolidated
    to one marker->stage table; `benchmark_subjects.build_row` still runs its
    OWN independent chain in production, and `mesh_to_tree.py:481-482`'s comment
    already said so. Omitting a stub branch there reproduces S4 blocker #1
    exactly: `rescued` False, stage "none", `attempt0_pack` True for a base with
    an invented flap, nothing red.
  - **Gating uses its OWN table (`STUB_REMEDY_CLASSES`), and the alternative was
    measured.** Adding a POLYS_NOT_VALID *recipe* makes `recipe(cp)` truthy,
    `resolved_code` starts returning POLYS_NOT_VALID, `first_stage` returns None
    for it, and the raw dog silently loses placement-first routing -- verified
    by counterfactual. `_FIRST_STAGE` and `_RECIPES` are untouched, so routing
    is provably unmoved.
  - **★ "Sweep k upward and take the FIRST build" was PROSE, not behavior, and
    adversarial review caught it.** The first cut served row 2192 at k=7 where
    its first build is k=6. Mechanism: every stub rung shares one stage, so the
    barrier's `(invents, honesty)` pair is the CONSTANT `(0, 3)` across the
    whole sweep and can never engage BETWEEN stub rungs; selection then fell
    through to `_search_first_clean`'s dirty-best tracker, which ranks by AUDIT
    SCORE with k as an uncounted cost. Measured: k=6 audits (36 defects, **9**
    mid-category, max 2.3e-4), k=7 audits (33, **0**, 4.0e-8) -- so the ladder
    bought a cleaner audit with a flap nobody asked for. That inverted THREE
    written statements of intent at once: `stub_rungs`' own docstring, the
    committed `s5_engine_repair_evidence` `_meta`, and this slice's own
    `_serve_rank`, which places `-stub_flaps` AHEAD of stage integrity
    precisely so fewer invented flaps settles a tie. **Fixed by adding `-stubs`
    as a THIRD barrier key.** It is again a strict generalisation: non-stub
    rungs carry `stubs == 0` so the key is constant for every shipped stage,
    and the barrier only engages once something has PACKED, so the sweep still
    runs k=1..8 freely while nothing builds and no rescue is lost. Re-measured
    through the serve path: 385 k=1, 97 k=3, **2192 k=6** -- the serve path now
    agrees with the binding measurement exactly, at one fewer invented flap.
    *(The session's first instinct was to keep k=7 as a "defensible trade" and
    merely report it. It was not defensible: it contradicted the brief's
    explicit instruction and three of the code's own statements. Consistency
    with stated intent beats a post-hoc preference for the geometrically nicer
    pack -- and a dirty pack is still M/V-repaired and served, which is what
    the 2.3 solver is for.)*
  - **Per-subject: 5 of 6 show `stub_flaps: None -> 0` and nothing else.** The
    dog headline HOLDS unchanged (6/6 leaves, both pairs, placement, no nudge,
    no asymmetry, BENIGN). **insect MOVED and it is an anatomy WIN**: served
    REAL leaves 6 -> 7 of R=9 (unclamped fidelity 0.667 -> 0.778), pairs still
    3/3, lint still BENIGN, no nudge and no asymmetry -- at the cost of 1
    invented flap and losing attempt-0 status. This is phase 3's FIRST rescue in
    the mission: a normalize-repaired candidate that only packs once the stub
    stage exists. Its `rescue_stage` reads "normalize" rather than "stub"
    because build_row clamps a repaired serve to the LESS honest of the two;
    `stub_flaps = 1` carries the invention, so nothing is hidden.
  - **★ Adversarial review found seven defects, and the blocker was a RED SUITE
    the session's own sweep hid.** `compiles_to_fold` went 3-tuple -> 4-tuple;
    both production unpack sites were updated and `test_auto_mesh_to_tree.py`
    was not. The break is LOUD (ValueError), but that file had been excluded
    from the fast regression sweep to save 20 minutes -- **a loud break in a
    file you do not run is indistinguishable from no break at all.** Also fixed:
    `poly_valid` degenerated to a constant `false` for every `added == 0`
    outcome (the "report the cached flag" reasoning was wrong -- a stale flag is
    not a measurement; it now emits null == NOT COMPUTED); the served note
    asserted a POLYS_NOT_VALID-specific CAUSE while the stage is gated on two
    classes; `-1` was guarded in `apply_shaping_ops` but NOT in the two
    consumers its own comment named -- `suggest_pose_stack` would hand the agent
    a paste-ready call targeting an engine-invented flap, and `flap_fill`'s
    MIRROR case is worse still (one `-1` makes `nearest_common_ancestor` return
    the ROOT, so A-9 attaches a detail flap at the body centre and that
    candidate PACKS and is served as a success); `capture.record` gained
    `stub_flaps`, without which a stub row says `perturb_pack=True` and teaches
    the 2.4 model that the REQUEST was packable.
  - **KNOWN GAP, deliberately not closed: a stub serve is not relayed to the
    USER on the direct compile path.** SYSTEM_PROMPT relays a backend caveat
    only on the literal "did not pack exactly", which STUB_MARKER must not
    contain (a stub-rescued base HAS the requested proportions). The mesh path
    IS covered -- mesh_report emits "STRUCTURAL FLAPS ADDED BY THE ENGINE" --
    but the direct path has no report. **This is S6's**, and editing the prompt
    here would confound S6's ONE batched paid RUN_AGENT_SMOKE A/B with a
    serve-delta, which is exactly why S5b is its own session. A test pins the
    gap and instructs S6 to INVERT it rather than delete it.
  - **Also known and unclosed (report, not defect):** a stub-served base is not
    poseable or fillable. `suggest_pose_stack` / `suggest_flap_for_region`
    RE-COMPILE the tree through workers that do not stub, so on exactly the
    bases the stub stage rescued they now decline honestly instead of silently
    misbehaving. Making them stub-aware means re-running the k-sweep inside
    those tools and is outside the seven steps.
  - **EDGE-OPT STAYS OUT.** S5 measured it 0/9 standalone across 562 arms and
    that decision stands; the record is the S5 verdict above and this pointer,
    not a flagged-off stage. See Contingency.
- **S6 verdicts (measured 2026-07-27; branch `claude/s6-agent-contract`, MAIN
  checkout; scratchpad `tokens_BEFORE.json`, `ab-dry2/`, `s6_prompt_ab/`):**
  - **★ THE TOKEN BASELINE THIS PLAN QUOTES IS WRONG, AND IT IS WRONG BY
    MODEL.** Plan:213 says "~2k of 5.7k tokens". Measured with Anthropic's free
    `messages.count_tokens` (new tool: `scripts/measure_prompt_tokens.py`,
    which reads the LIVE MCP tool schemas so it cannot drift from what the
    model is shown): SYSTEM_PROMPT is **6,530 tokens on claude-sonnet-4.5 and
    9,436 on claude-sonnet-5**, the model `.env` actually configures. The same
    24,160 chars, 44% more tokens -- a real tokenizer difference (2.50 vs 4.09
    chars/token on plain English), not per-call overhead. chars/4 undercounts
    the configured model by 52% because the prompt is dense with snake_case
    identifiers. **Quote the model with the number or the number means
    nothing.**
  - **★ THE PLAN NEVER COUNTED THE TOOL SCHEMAS, AND THEY ARE HALF THE BILL.**
    15 tools = **8,946 tokens**, 49% of the 18,382-token fixed prompt. A
    "prompt diet" that ignores them is optimising the smaller half. Slice 7
    adds two tools (+670 marginal: validate_tree 389, get_template 281), so the
    prose diet has to beat 670 just to break even.
  - **★ NET: SYSTEM_PROMPT 9,436 -> 10,300 (+864), tools 8,946 -> 9,616
    (+670), total 18,382 -> 19,916 (+1,534). THE PROMPT GOT BIGGER AND THE
    DIET BULLET IS NOT MET.** Recorded as a rise rather than dressed as a cut.
    Cut ~1.4k: templates 1,309 -> 569 (retired to `get_template`), plus
    TWO-WAYS, FOLD-HANDLES, FREE-PAPER, ALWAYS-LINT and the now-coded budget
    prose. Added ~2.3k: ERROR HANDLING 1,962 -> 2,509 and a new 1,116-token
    cheat-sheet. The doctrine fixes are the overrun -- closing three honesty
    holes and routing to the error envelope requires saying things the prompt
    never said -- and adversarial review then made several of them LONGER (the
    `stages_tried` cross-check, splitting normalize out of the preserving
    relay, the corrected `scale_at_failure` gloss, the measured pose-vs-fill
    split). The plan's own arithmetic ("diet ~2k, add a 1.5-2k cheat-sheet")
    was net-zero by construction, so a reduction was never on the table; what
    shipped is ~900 tokens worse than net-zero. **If a future slice wants the
    prompt genuinely smaller, the honest target is SHAPING + POSE SUGGESTION
    (1,741 + 748 tokens, 20 test pins, untouched here because the pins made it
    the highest-risk block for the least doctrine value), not another pass over
    ERROR HANDLING.**
  - **The templates cost 1,309 tokens, not the ~680 plan:204 budgets.** The 680
    figure is exactly the CONCRETE-TEMPLATES sub-block (prompt lines 170-191);
    the whole retirable section is 153-191. Its numeric payload tokenizes at
    2.15 chars/token, the worst density in the prompt.
  - **★ A FOURTH DOCTRINE DEFECT, NOT IN THE S2/S3/S5b NOTES, AND THE ONLY ONE
    WITH CAPTURED HARM.** Template rule (1) -- "a root carrying four-plus
    branches reliably fails (POLYS_MULTIPLE_IBPS, a topology degeneracy no
    length change can fix)" -- is falsified by this repo's own
    `fixtures/s5_engine_repair_evidence.json -> packability_control`. A k-leaf
    STAR *is* a root with k children: k=4 packs 3/3 at 0% jitter, 2/20 at 1%,
    **20/20 at 30%**; k=5 3/3 then 16/20; k=6 3/3 then 15/20; k=8 3/3 then
    7/20. Only k=7 fails at equal lengths, and it packs 15/20 at 1%. So
    "reliably fails" is false at every k tested, and "no length change can fix"
    is false in the *opposite* direction -- length change is precisely what
    moves k=4 and k=7. **Captured harm:**
    `docs/superpowers/evidence/2026-07-25-cp-audit-smoke/haiku45-frames.jsonl`
    frame 22 shows a live agent quoting the rule verbatim to REFUSE the
    measured dog reference candidate ("will not pack cleanly on a unit square
    regardless of edge-length tuning") and demand a template redesign -- the
    prompt overriding measured anatomy, which its own guardrail forbids. S3
    then served that same dog 6/6 with both pairs and zero drift.
    **Consequence for the plan: `validate_tree` reports root degree as an
    OBSERVATION carrying its measurement, never as an error.** Plan:200's
    "root-children cap" is deliberately NOT implemented as a cap; coding it
    would freeze a refuted number into a tool and make the harm harder to see.
    `structural_prefilter`'s MAX_ROOT_CHILDREN keeps its separate job (ranking
    extractor candidates, where no agent reads it as doctrine).
  - **The other three defects closed as the notes specified.** (1) the lever
    doctrine now reads `DETAIL.suggested_lever` instead of deriving "the
    remaining lever is TOPOLOGY"; (2) the relay covers all six frame_title
    markers, and the proportion-PRESERVING ones explicitly FORBID claiming the
    lengths moved -- widening the relay carelessly would have installed a new
    lie where an old omission was; (3) the stub disclosure landed on the direct
    path and `test_stub_stage`'s tripwire was INVERTED to the cross-pin form
    its own docstring specified, not deleted.
  - **The word "stub" was already taken, and it was a one-site fix.** Exactly
    ONE occurrence existed in the prompt (line 383, the A-9 sense: a FILL that
    is too SHORT) and zero in the engine-structural sense. Renamed to
    "UNDERSIZED FILL" with both meanings contrasted in-line; the A-9 sentence
    is load-bearing (it governs whether a fill is proposed) so neither side
    could be dropped.
  - **★ THE A/B HARNESS THE PLAN ASSUMES EXISTS DID NOT, and building its two
    free controls was worth more than the paid run.** `probe_prompt_ab.py`:
    paired arms (A = the e18f296 prompt frozen byte-exact + the 15 pre-S6
    tools; B = live), four subjects pinned to DISTINCT fake-provider buckets,
    12 coded criteria fixed before any output. Both controls caught a real
    defect:
    * `--self-test` (scorer) FAILED first run -- `reached_fold` and
      `no_engine_crash` cannot be falsified by a record that compiles, so the
      control was demanding something impossible. Fixed by adding a third
      `crashed` synthetic and asserting the stronger property: every criterion
      must read True on at least one record and False on at least one.
    * `--dry-run` (plumbing, real backend, scripted model) caught the serious
      one: the direct subject was **hand-typed plausible numbers, not corpus
      row 385**, and that tree packs attempt-0 exact -- `stub_disclosed` would
      have scored None on BOTH arms and the paid run would have measured
      nothing about the honesty fix it exists to test. The real row produces
      `[ide: engine added structural flap(s): 1]` at k=1, matching S5b.
    Both controls run inside `make test` so they cannot rot.
  - **★ THE SESSION INTRODUCED TWO OF THE DEFECT CLASS IT WAS SENT TO REMOVE,
    and caught them by applying its own rule to itself.** (a) A first draft said
    the ladder is "dozens of attempts, MOST of which change no length at all" --
    false: `test_ladder_audit` byte-pins 37 rungs as order 4, placement 1,
    jitter 24, composed 8, of which only FIVE preserve length (13.5%). The true
    and useful statement is about RESCUES, not rungs (12 of 15 cohort rescues
    came from preserving stages). (b) A first draft told the agent "below ~0.05
    the tree is over-constrained" -- that constant comes from plan:143, a
    SKETCH, and exists nowhere in the code; `error_recipes` deliberately says
    "below the packable threshold" without naming one because none is measured.
    Both are now pinned to the code constants and the committed fixtures rather
    than restated in prose. **Generalisable: a prompt claim with a number in it
    needs a test that recomputes the number.**
  - **Coded budgets: the per-turn scope IS the [CP AUDIT] exemption.** The
    3-compile and 3-gate-round budgets moved into `agent_turn._TurnBudget`
    (MAX_AGENT_STEPS's pattern). Because the bridge runs a repair as its OWN
    agent_turn, a turn-scoped counter starts the repair at zero -- the plan's
    exemption falls out with no flag threaded through web/server.py and nothing
    to keep in sync. Only FAILED compiles count, matching the prompt's wording.
  - **The [ANATOMY] oracle fires on NOTHING today, and that is the honest
    state.** It mirrors CP AUDIT structurally (one synthetic retry, inform-only
    stand-down composed FOR the budget outcome, errored-turn deferral, per-fold
    consumption) and stands down on: no mesh report, no reference count, the
    FAKE PROVIDER (the mesh is a canned keyword-matched fixture -- the bird
    fixture extracts R=5 against a committed reference of 4), R above the
    packable window (fish R=10, insect R=9), and anatomy already complete. On
    the six committed subjects every path is suppressed or complete, so it is a
    REGRESSION TRIPWIRE for the day a full-anatomy subject starts serving
    short, not a live repair driver. Slice 8's >8 admission is what changes
    that, and a test pins the transition.
  - **★ ADVERSARIAL REVIEW FOUND TWO BLOCKERS, AND BOTH WERE S6 RE-COMMITTING
    THE EXACT DEFECT CLASS IT WAS SENT TO REMOVE.** 6 lenses, ~20 findings.
    1. **The falsified root-degree rule was deleted from the prompt and
       re-shipped VERBATIM through `get_template`.** `body_plans.SHARED_RULES[0]`
       carried "a root carrying four or more branches reliably fails
       (POLYS_MULTIPLE_IBPS, a topology degeneracy no length change fixes)" --
       and the prompt now TELLS the agent to call that tool, so the refuted
       claim and its refutation would have arrived in the same context window.
       The session transcribed the harmful sentence while writing the paragraph
       explaining why it is harmful.
    2. **The [ANATOMY] oracle fired "carries 0 of the R" on any serve whose
       tree it could not record.** `served_anatomy(None)` returns 0 leaves,
       which `decide()` could not distinguish from "a base with no flaps", so
       the incremental `new_base -> compile_base` path (compile_base takes no
       tree_nodes at all) and `convert_tmd_to_fold` would each get a maximal,
       entirely false shortfall -- and the per-user-turn report reset added in
       the SAME session made that certain rather than merely possible. Fixed
       with an explicit `unknown-tree` suppression: "I do not know what was
       served" is not "nothing was served", and only a suppression can say so.
    Also fixed from review: `pending_tree` was promoted by ANY fold, so a
    FAILED compile's tree became "the tree that produced the served fold";
    non-dict tool `args` raised AttributeError out of `_send_frames` and killed
    the websocket session; BOTH oracles could fire on one user action, leaving
    contradictory imperatives standing (CP AUDIT: "keep the topology IDENTICAL,
    adjust lengths"; ANATOMY: "recondition the STRUCTURE, do not rescale") and
    granting two fresh compile budgets; `scale_at_failure` was glossed
    BACKWARDS (it is the CONVERGED scale and is NULL exactly when the optimizer
    gave up, so the draft's "small means over-constrained" would route a
    polygon-network degeneracy to dropping flaps); the cohort statistic was
    stale by a slice AND its pin read `measured["s3"]` by name, freezing the
    stale figure instead of catching it; `stages_tried` was missing from the
    DETAIL list, which is the only field distinguishing "this lever already
    ran" from "not tried"; NaN/Infinity edge lengths passed `validate_tree`
    (`nan <= 0` is False and `json.loads` accepts the bare token); arm A of the
    paid A/B was silently receiving S6's coded budgets, making one of the three
    treatments unattributable; `tests/cases.py` held an unpinned FOURTH copy of
    the template numbers; and the prompt became a THIRD stub-disclosure site
    while the class-neutrality test still iterated only two.
  - **Three further false claims were self-caught before review, by applying
    the session's own rule to its own writing.** "the ladder is dozens of
    attempts, MOST of which change no length" (false: 5 of 37 rungs preserve
    length); "below ~0.05 the tree is over-constrained" (that constant comes
    from plan:143, a SKETCH, and exists nowhere in the code); and two
    cheat-sheet sentences contradicting each other about k=8. **Every
    quantitative prompt claim now has a test that RECOMPUTES the number from
    the fixture or the code constant** -- the generalisable rule this session
    earned.
  - **★ THE PAID A/B CAME BACK NEGATIVE ON THE ONE THING S6 EXISTS TO FIX, AND
    THAT IS THE RESULT.** 4 subjects x 2 arms, one process, ~$3;
    `docs/superpowers/evidence/2026-07-27-s6-prompt-ab/`. Scored: **arm A
    35/37, arm B 32/36.** Nine of the twelve criteria are identical across
    every subject (reached_fold, linted_served_fold, compiles_within_limit,
    gate_before_compile, no_path_mixing, no_forbidden_paper,
    benign_not_retried, no_engine_crash, reference_first) -- so the diet, the
    retired templates and the coded budgets cost NOTHING measurable on the
    contract axes. The whole difference is one subject, `direct_stub_385`:
    * **`stub_disclosed` went P -> F. Arm A disclosed the invented flap; arm B,
      the arm carrying the new disclosure clause, did NOT.** Arm A's turn 1
      reads "the backend added **1 extra structural flap** -- the exact tree as
      given did not pack, and no rescue preserving your anatomy could pack it
      either, so it added a small stub flap to make the crease pattern
      resolvable" -- essentially a relay of S5b's `frame_title` note, which is
      long and self-explanatory. Arm B's turn 1 reads, in full, "The compile
      succeeded, but with an important caveat -- let me lint it now", and the
      caveat is never returned to. **The disclosure clause did not produce the
      disclosure; the served note already did, and the arm without the clause
      is the one that relayed it.**
    * The second arm-B loss on that subject is a VERIFIED SCORER ARTIFACT, not
      behavior: `no_false_length_claim` matched "normally I'd adjust
      lengths/topology first, but since you asked me to compile this exact tree
      with no changes..." -- a negated counterfactual about what the agent
      declined to do.
  - **The scorer was corrected TWICE, on recorded data, and then deliberately
    left alone.** Both corrections were objective, not outcome-shaped: (a) the
    length-claim regex matched "changed" INSIDE "unchanged", so the bird arm
    saying "Node order and lengths were sent unchanged" -- the literal truth --
    scored as a false claim; (b) an exemption for the agent's own
    micro-adjustment was first written as a prose regex, which promptly
    exonerated the BAD synthetic's "I adjusted the limb lengths, which now
    differ from your request" (the control caught it) and was replaced by a
    comparison of the recorded compile ARGS, which cannot be talked around. A
    THIRD false positive of the same negation family was then found and
    **deliberately NOT patched** -- two instrument fixes with objective
    justification is repair; a third, after seeing which arm it helps, is
    fitting. It is reported as an artifact instead.
    **Generalisable: a discrimination control proves a criterion CAN separate
    good from bad. It does not prove the criterion is RIGHT about which is
    which.** Neither synthetic contained a negated sentence; both do now.
  - **Efficiency moved the wrong way and it is unexplained at n=1:** arm B used
    **22 steps / 22 tool calls / 4 compiles** against arm A's **16 / 12 / 3**.
    Some of that is the new tools being used as intended (validate_tree on 3 of
    4 subjects, get_template on 2 of 4 -- uptake is real), but not all of it.
    The plan tracks "steps per served base" as a metric and this is a
    regression on it.
  - **NOT ITERATED AGAINST.** The brief is explicit that iterating the prompt
    until the paid signal turns favourable is fitting to a sample of one, and
    the prompt was not touched after the run. What the result licenses is a
    HYPOTHESIS for a future slice, not an edit now: the disclosure may be
    better served by the backend NOTE (already sufficient in arm A) than by
    prompt doctrine, in which case S6's clause is redundant rather than wrong
    -- and the honest test of that is a repeat A/B with n>1 per arm, which this
    session did not buy.
  - **DROPPED, named rather than omitted: the optional Rabbit Ear UI pre-lint**
    (plan:216). It is the only Slice 7 bullet with no measured precedent in
    this repo, and the diet plus the A/B consumed the session. Not started; no
    half-wired path shipped.
  - **NOT S6's, left declining honestly:** `suggest_pose_stack` /
    `suggest_flap_for_region` remain non-stub-aware per S5b's handoff. Making
    them stub-aware means re-running the k-sweep inside those tools; if that is
    wanted it deserves its own slice, and the cheat-sheet now tells the agent
    the decline is correct rather than a bug.
- **S7 DESIGN DECISIONS + PREDICTIONS (written 2026-07-27 BEFORE any
  measurement run; branch `claude/s7-extraction-pairs-admission`, MAIN
  checkout, from main 66c361c). Recorded here first so predicted-vs-actual is
  a real test and not a post-hoc narrative.**
  - **★ DECISION 1: `MIN_LEAVES, MAX_LEAVES = 4, 8` DOES NOT MOVE.** Slice 8's
    text is a second gated admission path, not a wider window, and three
    measured facts say a blanket raise would be actively wrong:
    1. **The clamp controls TERMINATION, not just ordering.**
       `fidelity_score`'s `r_eff = min(max(R, MIN), MAX)` (mesh_to_tree.py:1176)
       is read by the terminal early-exit `fid >= 1.0 and stage == "none"`
       (:1035), by `rank_by_fidelity` (:1198), `_serve_rank` (:575),
       `_best_possible_rank` (:591) and `_p3_rank` (:608). Raising MAX to 12
       takes fish's voxel-96 `r_eff` from 8 to 10 and insect's from 8 to 9
       (`reference_feature_count(FISH_96) == 10`, `(INSECT_96) == 9`, pinned in
       test_anatomy_reference.py), so an 8-leaf candidate that is terminal
       today stops being terminal — a serve change on two of the three subjects
       the slice exists to help, arriving as a side effect rather than as a
       measured rescue.
    2. **Admission cannot change R or the anchor anyway, so the raise buys
       nothing there.** `leaf_by_prune[prune] = leaf_count` is written at
       mesh_to_tree.py:911, one line BEFORE `structural_prefilter` at :912. The
       >8 leaf counts already enter `reference_feature_count` today; the
       prefilter only decides what gets COMPILED. Raising the window would be
       redundant for R and destructive for ranking.
    3. **The window is quoted verbatim on the agent-facing surface, and one
       copy does not track the constant.** `agent_loop.py:542` hard-codes "THE
       PACKABLE WINDOW IS 4-8 FLAPS"; `tree_contract.py:283-288` interpolates
       `{lo}-{hi}` from `_window()` (which does track) but hard-codes "~35% at
       8 flaps" beside it; `anatomy_oracle.py:35` names fish and insect as
       above the window. Leaving MAX_LEAVES at 8 keeps every one of those
       sentences TRUE with zero prompt edits — and S6 measured prompt edits as
       the regression-prone half of the work.
    Consequence: the five lockstep consumers (`structural_prefilter` :1121,
    `fidelity_score` :1176, `anatomy_oracle._max_leaves` :58,
    `tree_contract._window` :77, plus `unclamped_fidelity` :1188 which is
    reporting-only and never moved) are all UNTOUCHED, and so are the two
    transition pins the brief flagged: `test_anatomy_oracle.py:121` and `:214`
    were both written to TRACK the constant, so they stay green rather than
    needing an update. A SIXTH pin the brief did not list encodes the clamp
    directly and would have gone red on a raise:
    `test_anatomy_reference.py: assert m2t.fidelity_score(8, 10) == 1.0`.
    The transition tripwire is instead ADDED for the constant that actually
    changes (`ADMIT_MAX_LEAVES`), never by deleting the ones above.
  - **★ DECISION 2: an admitted 9-12-leaf candidate may NEVER displace a held
    serve.** It is compiled and RECORDED (trace + capture row — that is the
    point, it generates the >8-leaf ladder rows `corpus_wide.jsonl` has zero
    of) but can only become the serve when nothing else compiled at all. The
    reason is measured, not timid: the only yardstick available at that point
    is `anchor_r`, and over-segmentation is exactly what corrupts it. For
    quadruped (true R=6) S2 measured v64 reading R=9 and v128 R=11, so against
    an anchor of 11 a 9-leaf artifact scores 0.875 clamped and 0.818 unclamped
    against the true 6-leaf serve's 0.75 and 0.545 — **BOTH axes prefer the
    artifact.** S3 named this the anchor's over-segmentation blind side and
    routed it here; S7 does not have the better reference-count estimator that
    would fix it (that is the bird ratchet item, still open), so the honest
    move is to refuse the comparison rather than pick the wrong side of it.
  - **DECISION 3: the admission gate does not read root degree.** The gate is
    the plan's own three terms, each reusing an existing code constant rather
    than a new threshold: hubs <= `MAX_NORMALIZE_HUBS` (rescue_ladder.py:623),
    >= 2 pairs, and no interior edge under `SLIVER_RATIO` (:616). S6 falsified
    "a root with 4+ children reliably fails" at every k tested and caught a
    live agent quoting it to refuse a candidate that then served 6/6, so
    `MAX_ROOT_CHILDREN` keeps its ranking job in `structural_prefilter` and
    gets no new doctrinal one here.
  - **★ PREDICTED SCORECARD DELTAS, per row, on the UNCLAMPED axis, vs the
    committed post-S5b baseline (`fixtures/scorecard_baseline.jsonl`,
    3244d3c). `stub_flaps` is never summed into `served_leaves`.**
    Mechanism split: **admission is predicted to move NOTHING on any row**
    (Decision 2, and all six subjects already hold a serve), so **pair
    detection is the only axis that can move the scorecard** — it changes the
    `pairs` list, which is the engine's mirror constraint, which changes which
    candidates pack.

    | subject | baseline (leaves / unclamped fid / pairs_kept-of-expected) | PREDICTION |
    |---|---|---|
    | quadruped | 6 / 1.00 / 2 of 2 | **FROZEN — no axis moves.** Pairs already complete; nothing for pair detection to find. |
    | humanoid | 5 / 1.00 / 2 of 2 | **FROZEN — no axis moves.** Same reason. |
    | dog | 6 / 1.00 / 2 of 2 | **FROZEN — no axis moves.** Same reason. Also the single-machine cached-mesh row, so any dog-only move is a provenance artifact until proven otherwise. |
    | bird | 5 / 0.75 / **1 of 2** | **pairs_kept 1 -> 2** is the target and the primary hypothesis (MEDIUM confidence). `served_leaves` 5 and unclamped 0.75 predicted UNCHANGED: bird's over-split is a REFERENCE-COUNT defect (extractor_R=5 vs committed R=4), which S7 does not touch. `attempt0_pack` predicted to stay True — a new mirror constraint could make the currently attempt-0-exact candidate fail, and if it does that is a REGRESSION to investigate, not a win. |
    | fish | 6 / 0.60 / 1 of **null** | `expected_pairs` null -> a measured integer (the slice's own ground-truth deliverable). `pairs_kept` 1 -> 1 or 2, genuinely UNKNOWN — fish is the least bilaterally symmetric subject and this is the reference nobody has measured. `served_leaves` 6 and unclamped 0.60 predicted UNCHANGED. |
    | insect | 7 (+1 stub) / 0.7778 / 3 of 3 | **FROZEN — no axis moves**, including `stub_flaps` staying 1. Pairs already complete at 3/3. |

    Falsifier: an unpredicted move on quadruped, humanoid or dog is a DEFECT
    however good it looks, and will be reported as one.
  - **★ COHORT MEASURED: 18/24, residual EXACTLY `[90, 353, 500, 830, 865,
    2099]` — the S5b list, unchanged — with all 24 request trees byte-untouched.
    Prediction met.** Measured end-to-end through
    `server.draft_and_compile_full_base`, and there is also a static argument
    for why it could not have moved: `import server` never imports
    `mesh_to_tree` (its only reference is inside the mesh tool at
    server.py:2319), while every S7 change lives in `mesh_to_tree`. It was
    measured anyway, because "by construction" arguments are what this
    project's history says to distrust.
    - **The FIRST cohort run was VOID and is reported rather than quietly
      re-run.** Executed while three other heavy jobs were running, it produced
      a log saying row 85 SERVED and a JSON saying it did not, plus two
      `RuntimeError: An attempt has been made to start a new process before the
      current process has finished its bootstrapping phase` traces. Rows 85 and
      90 were then re-run twice each in isolation: **85 serves 2/2, 90 fails
      2/2**, and the clean re-run reproduced 18/24 with zero such traces. The
      mechanism is a NESTED SPAWN — S3's `_worker_compile_and_regions` runs the
      whole ladder inside one spawned child and re-spawns past crashes, so a
      grandchild start during a child's bootstrap import raises. **Pre-existing
      in kind and load-dependent, not S7's**, but worth carrying: a cohort run
      sharing a machine with other spawning jobs can report a FALSE residual.
    - **The stage-distribution control reported a mismatch, and it is the
      INSTRUMENT, not the product.** The measuring script buckets serves by
      marker substring and has no `composed` branch, so S3's composed rescue
      (row 85 = order variant + jitter rung) reads as `order`. Faithful totals
      agree exactly — 9 order + 4 placement + 1 jitter + 1 unclassified = 15
      faithful + 3 stub = 18, against S5b's 8 + 4 + 2 + 1 = 15 + 3. Flagged as
      a limitation BEFORE the run, and reported as one rather than dressed up
      as a finding about the ladder.
  - **PREDICTED COHORT: 18/24, byte-identical, and that is a PASS not a
    shortfall.** Verified before building: all six `residual_ids_s5b` rows are
    at or below 8 leaves (90/353/500/830/2099 at k=8, 865 at k=6; recomputed
    from `corpus_wide.jsonl` and cross-checked against each row's committed
    `features.n_leaves`, 0 mismatches), and three of them (353, 500, 2099) are
    stars with root_children == 8. A 9-12-leaf admission path cannot reach a
    row already inside the window, and pair detection cannot either —
    `detect_symmetry` takes a MESH and cohort rows are synthetic corpus rows
    whose `pairs` come from the generator.
  - **★ SUITE: THE FAILING-ID SETS ARE IDENTICAL.** Baseline **4F / 2036P /
    11S** (pristine 66c361c, built IN PLACE in its own worktree so no `.so` was
    borrowed) -> after **4F / 2083P / 10S**. The `+47 passed / -1 skipped`
    decomposes exactly: 46 new tests, plus one dog-gated test that SKIPPED in
    the baseline worktree (the cached HF dog mesh lives in a gitignored
    `generated_meshes/` and does not exist there) and RUNS in the main checkout.
    The four failures are the same four IDs in both runs.
    - **★ MAIN AT 66c361c DOES NOT ACTUALLY PRODUCE 3F/2038P/10S ON THIS
      MACHINE, AND A BARE `make test` NEVER TERMINATES.**
      `test_feasibility_dataset.py::test_perturb_pack_is_persisted_to_disk`
      wedges in a multiprocessing poll — reproduced on PRISTINE HEAD with every
      S7 change stashed, so it is not S7's. Both runs therefore used
      `--timeout=420`, which converts the hang into a 4th failure present
      IDENTICALLY on both sides; the other three are the documented pre-existing
      rigid hash pins. Recorded because the next session will otherwise spend
      the same hour rediscovering it.
  - **RE-BLESS: ZERO, PROVEN TWICE.** Structurally — `bless.py`, `runner.py`
    and `cases.py` contain **no reference** to `mesh_to_tree`,
    `detect_symmetry` or `auto_mesh`, so no extraction change can reach them —
    and empirically: `make bless` regenerated all four goldens and
    `baseline_verdicts.json` and produced **no diff**. What S7 owed instead was
    `fixtures/scorecard_baseline.jsonl`, re-blessed to post-S7 in its own commit
    (S5b's precedent) so S8 cannot report S7's fish win as its own delta; that
    diff is TWO LINES, the `_meta` and the fish row.
  - **EXTRACTION SNAPSHOT CHURN: ZERO, and the itemised list is empty for a
    measured reason.** `test_snapshots_match_live_extraction` — the repo's ONLY
    exact-match extraction snapshot — passes unchanged before AND after the
    review fix, because greedy was already optimal at all five snapshot configs
    and the base pass is byte-identical there. The `nodes` half could not have
    moved in any case: `to_metric_tree` derives it from `_bfs_remap` alone.
  - **CORPUS FILE DISAMBIGUATION (plan:230 reads global, is file-specific).**
    Measured: `feasibility/corpus_wide.jsonl` = 2600 rows, **0** non-null
    `perturb_pack`, and it IS `dataset.DEFAULT_CORPUS` (dataset.py:15) and the
    file `rescue_cohort.json` keys into — so plan:230's claim is TRUE of the
    file that matters. `feasibility/corpus.jsonl` is a SEPARATE 2000-row file
    with **100** labeled rows, **17** of them above k=8 (9 at k=9, 1 at k=10,
    2 at k=11, 5 at k=27). Every S7 statement names its file.
- **S7 MEASURED VERDICTS (2026-07-27; branch
  `claude/s7-extraction-pairs-admission`, MAIN checkout, from 66c361c;
  scratchpad `sweep_pairs.json`, `scorecard_s7.log`, `cohort_s7.json`,
  `baseline_suite.log`).**
  - **★ ADVERSARIAL REVIEW FOUND THE SLICE'S CENTRAL MECHANISM BROKEN, AND THE
    PIN THAT SHOULD HAVE CAUGHT IT VACUOUS.** 6 lenses, 24 findings. The verify
    pass died on a usage limit, so every finding was triaged and reproduced by
    hand rather than by refuter agents — worth stating, because "0 survived
    refutation" was an ARTIFACT of that failure and not a clean bill.
    1. **THE ESCALATION WAS DISCARDING GENUINE MIRROR PAIRS.** It re-ran the
       WHOLE matching and kept any result with a larger pair COUNT. On
       `fixtures/fish.glb` at (voxel 96, prune 0.40) the base pass found two
       pairs with reflection residuals 6.51 and 10.28 against a base tolerance
       of 10.88; one leaf was stranded; the 2x-tolerance matching returned five
       pairs; and 5 > 2 threw BOTH genuine pairs away. Worse, `d < tol` never
       required the two leaves to lie on OPPOSITE sides of the plane, so at 2x
       tolerance it emitted "pairs" that are not mirrors in any sense — and
       `label_leaves` then labelled both members "left" (measured on fish v96
       p0.25: one pair rendered as two `left hind limb (pair 5)` entries).
       **Fixed** by matching only among the UNPAIRED leaves and requiring each
       added pair to STRADDLE the plane, so monotonicity is STRUCTURAL rather
       than a comparison that can be got wrong. Re-measured on the same 144
       configs: the escalation now discards a base pair in **0** of them, fires
       on 12, and adds 15 pairs. `label_leaves` declines to claim left/right
       when a pair shares a sign about the centroid plane instead of asserting
       a side that is not there. **5 of the 15 added pairs still read same-side
       against the CENTROID plane, and that is correct** — they mirror an
       OFFSET plane, which is what freeing the offset means; 24 further
       same-side pairs come from the BASE pass and are a PRE-EXISTING mechanism
       present in the old greedy too, not something S7 introduced.
    2. **THE ★ AXIS-INSULATION PIN WAS VACUOUS.** Three lenses independently
       showed it passing under the exact regression it names: it never asserted
       on the axis, and its fixture gave both axes the same base count. A
       `sys.settrace` line census proved the escalation's ACCEPT BRANCH was
       executed **zero times** by the entire new suite — so every claim made
       about the escalation was untested. The replacement fixture is verified
       against the mutant (shipped -> axis 0; escalate-all-then-argmax -> axis
       1) and asserts on the AXIS.
    **★ AND THE SCORECARD IS BYTE-IDENTICAL BEFORE AND AFTER THE FIX.** The
    fish win is therefore NOT built on the spurious pairs — the fix removed
    bogus pairs at other configs without moving the serving candidate. That is
    the check worth having: a fix that changes a headline number is a fix whose
    headline was wrong.
    Also fixed from review: phase-4 trace rows bypassed
    `mesh_report._full_anatomy_row`'s exclusion (it knew `normalized`; phase 4
    tags `admitted`), flipping the agent off the A-9 fill route — now keyed on
    `phase` so a third phase cannot slip through; the `maxcardinality=True`
    guarantee had no pin that could see it; the hub-bound `getsource` pin was
    satisfied by the DOCSTRING (the S6 defect class, reproduced inside the very
    slice that quotes S6 about it); `structural_admission` could be deleted from
    the serve path with all 20 admission tests green; `IDE_ADMIT_WIDE` read
    "False"/"off"/"no" as ON; and the `admitted` source list was not
    content-deduped (quadruped@64 contributes 7 sources but only 2 distinct
    trees). All seven load-bearing pins are mutation-proven.
  - **★ SCORECARD: PREDICTED vs ACTUAL. ONE ROW MOVED — fish — and it moved on
    four axes at once, all favourably.** Deltas vs the committed post-S5b
    baseline (`--baseline`, dog included, unclamped axis, `stub_flaps` never
    summed into `served_leaves`):

    | subject | predicted (written before the run) | actual | verdict |
    |---|---|---|---|
    | quadruped | FROZEN | no axis moved | **HIT** |
    | humanoid | FROZEN | no axis moved | **HIT** |
    | dog | FROZEN | no axis moved | **HIT** |
    | insect | FROZEN, incl. `stub_flaps` staying 1 | no axis moved | **HIT** |
    | bird | `pairs_kept` 1 -> 2 (medium confidence) | no axis moved | **MISS — predicted a move that did not happen** |
    | fish | `expected_pairs` null -> int; `pairs_kept` 1 or 2; **anatomy UNCHANGED** | `served_leaves` **6 -> 7**, unclamped `served_fidelity` **0.60 -> 0.70**, `pairs_expected` **null -> 2**, `pairs_kept` **1 -> 2**, `rescue_stage` **jitter -> order**, `nudge_marker` **True -> False**, `error_codes` FACETS_NOT_VALID -> POLYS_MULTIPLE_IBPS | **MISS, in the favourable direction** |

    **All four PROTECTED rows held**, which is the acceptance the brief set: an
    unpredicted move on quadruped/humanoid/dog would have been a defect however
    good it looked. Both misses are reported as misses.
    - **Why the bird prediction was wrong, and it is a useful wrong.** It was
      reasoned from the scorecard (`pairs_kept` 1 of an expected 2) that better
      matching would find the missing pair. The sweep says bird's pairs change at
      **zero of its 24 configs**: bird's second pair is not MISSED BY THE MATCHER,
      it is ABSENT FROM THE SKELETON. Better matching cannot invent a leaf
      extraction never produced. The lesson generalises to the whole slice —
      `pairs_kept < pairs_expected` does not imply a pairing defect.
    - **Why fish moved further than predicted.** The prediction treated pairs as
      a REPORTING axis. They are not: each pair is an engine mirror constraint
      AND a shared jitter factor AND a pairs-first order seed AND a mirrored
      placement layout, so finding fish's second pair changed which candidate
      PACKS. The result is the strongest single row in the mission's scorecard
      history — **+1 real flap while REMOVING the only remaining length change**:
      the serve moves off `jitter` (proportion-CHANGED) onto `order`
      (proportion-PRESERVING), so across the six subjects `nudge_marker` falls
      **1/6 -> 0/6** and `asymmetric` stays 0/6. The plan's "proportion integrity
      falls monotonically" metric is met outright for the first time.
    - **★ THE FISH MOVE IS ATTRIBUTED, NOT INFERRED.** S3's precedent (it pinned
      the dog's placement rescue with an `IDE_LADDER_STAGES` counterfactual
      rather than asserting the attribution) applied here: arm A = the shipped
      matcher, arm B = the pre-S7 greedy monkeypatched back in with NOTHING else
      changed, both through the real `benchmark_subjects.measure` serve path.
      **Arm B reproduces the committed pre-S7 fish row EXACTLY on every axis** --
      6 leaves, 0.60, `pairs_kept` 1, `jitter`, `nudge_marker` True,
      `error_codes` FACETS_NOT_VALID -- and the known-answer control against
      `fixtures/scorecard_baseline.jsonl` passes on all five compared keys. So
      the +1 flap and the jitter->order move are attributable to PAIR DETECTION
      ALONE: not to admission (measured: fish admits nothing -- every one of its
      9-12-leaf candidates is hub-fragmented), not to engine drift, not to luck.
      Scratchpad `fish_counterfactual.json`.
    - **fish's `pairs_kept` 1 -> 2 is NOT commensurable with its new
      `expected_pairs` = 2, and the coincidence must not be read as a match.**
      The served fish comes from voxel 64, where the winning mirror plane is
      DORSAL-VENTRAL (the skeleton is median-dominated), so `pairs_kept` counts
      median mirrors while `expected_pairs` counts bilateral ones. Two numbers
      that agree by arithmetic and disagree by meaning; recorded in
      `fixtures/anatomy_reference.json` so a later reader cannot mistake it for
      a solved axis.
  - **★ REEB-GRAPH EXTRACTION FLAG: DROPPED, NOT DEFERRED — and the bullet
    rests on TWO factual errors about this repo.** Probe D never ran (plan:352);
    S7 ran it. Verified firsthand, not relayed:
    1. **`by_wavefront` ALREADY IS the geodesic Reeb construction the bullet
       proposes as its "alternative."** `mesh_to_tree.py:224` calls
       `sk.skeletonize.by_wavefront`, and `skeletor/skeletonize/wave.py:242-257`
       is `SG.distances(source=seeds)` (graph geodesic) -> `np.digitize(dist,
       bins=...)` (level sets) -> `SG.subgraph(ix).connected_components()` per
       bin. Level sets of a geodesic distance function, one node per connected
       component: that is the textbook discrete Reeb graph. Building a flag to
       switch to what is already running cannot pay.
    2. **There is no "voxel-thinning baseline" to diff against.** Plan:243 names
       one; `mesh_to_tree.py:209` is `mesh.voxelized(pitch).fill()
       .marching_cubes` — a voxel REMESH that fuses fragmented .glb assets into
       one watertight manifold — and `grep skeletonize_3d|medial_axis|thinning`
       over the harness returns **0** hits. Both arms of the proposed A/B
       describe the same incumbent code.
    Probe D was then RUN on its literal target, the dog mesh: every alternative
    skeletonizer skeletor ships reaches the SAME 6-leaf plateau the baseline
    already reaches (baseline vox96 `0.30:6 ... 0.60:6`), and `by_teasar` is
    strictly worse (33 leaves at prune 0.20 collapsing to 2 by 0.50, no stable
    plateau). Honest counter-evidence, reported rather than suppressed:
    `by_wavefront_exact` does natively de-sliver (dog@96 emits a 0.169x shortest
    edge where the baseline emits 0.066x) — but `contract_slivers`
    (`SLIVER_RATIO = 0.08`) already catches exactly that sliver, and S4 measured
    the normalizer that owns it rescuing ZERO. The deficit Probe D was designed
    to fix is both already handled and already known not to be the blocker.
    Cost was never the issue: the seam is one line and all five alternatives
    satisfied the `pos`+`length` contract first try. **The bullet is cheap to
    build and impossible to cash, so nothing was built and no half-wired flag
    shipped** (S6's precedent for naming a drop).
  - **★ PAIR DETECTION SHIPPED, and the axis rule is what made it hard.** All
    four sub-bullets land in `_symmetry_pairs_and_axis`. The matcher is
    `nx.max_weight_matching` (blossom), **not** `scipy.linear_sum_assignment`:
    leaves are matched to other leaves out of ONE set, so bipartite assignment
    can emit a->b while b->c and mutual pairs would have to be salvaged from it,
    losing the optimality that is the point. Checked rather than assumed, as the
    brief asked — scipy 1.17.1 IS importable and IS pinned in `ci.yml:76`, but
    it is declared in no manifest and imported by no first-party module, while
    `networkx` is already imported at `mesh_to_tree.py:15`.
    - **The greedy defect, quantified before replacing it:** leaves iterate in
      networkx insertion order (traceable to SWC row order, arbitrary with
      respect to anatomy). Measured on a synthetic box mesh, a ZERO-cost pair
      loses to a 0.07-cost pair purely on scan order; greedy returns strictly
      fewer pairs than maximum-cardinality matching in ~2 of 755 random trials;
      and because the winning axis is `argmax(pair count)`, that undercount
      **flipped which PCA axis became the mirror normal in 110 of 30,000**
      random 4-6-leaf stars. `mirror_idx` also sets body/height in
      `label_leaves`, so a one-pair miss re-labels head/tail/fore/hind for every
      leaf.
    - **★ THE REGRESSION THIS SLICE ALMOST SHIPPED.** The first cut let the new
      degrees of freedom vote on the axis. Measured on `fixtures/quadruped.glb`
      at (voxel 96, prune 0.55): the escalation lifted the 97-unit BODY axis
      from 1 pair to 2 and flipped the winner off the 17-unit lateral axis,
      replacing a genuine left/right hind-leg pair (lateral offsets -5.38 vs
      +4.00) with head-paired-to-tail plus left-hind-paired-to-left-fore. Bird
      flipped the same way, matching two wings 15.2 apart under the 23.7
      escalated tolerance. **The distinction that fixes it:** optimal matching
      CORRECTS A MISCOMPUTATION of the documented criterion (greedy undercounted
      at the same plane and tolerance) so it may move the winner; the offset and
      the raised tolerance CHANGE the criterion, so they may not. Axis chosen at
      base plane + base tolerance; escalation refines only the winner. Pinned as
      a property test, not as a recorded answer.
    - **Blast radius, measured across 144 (subject, voxel, prune) configs
      including the cached dog: 17 pair changes, 2 axis changes, ZERO node
      changes** — committed as `fixtures/pair_detection_sweep.json` and
      RECOMPUTED from it by a test, not restated. The zero is structural and is
      itself pinned: `to_metric_tree` derives `nodes` from `_bfs_remap` alone
      and consults `sym` only on its final line, so a pairs-only change can
      churn only the `pairs` half of a snapshot — which makes any node-side
      movement in a regenerated snapshot evidence of an unrelated second
      change. Changes are **fish 12, humanoid 4, dog 1**; **quadruped, bird and
      insect change at ZERO configs**. The dog's single change is a 13-leaf tree
      at prune 0.20 — far outside the packable window, and the same pair count.
      *(The first draft of this paragraph said 16 changes, "humanoid at three
      prunes" and "a 22-leaf dog tree". All three were wrong: the 22 came from
      printing `n_nodes - 1` as a leaf count. Adversarial review caught all
      three, which is why the sweep is now a committed fixture with a recompute
      test rather than a number in prose.)*
    - **At the five SNAPSHOT configs the answer is byte-identical old-vs-new**,
      which is what bounds the extraction-snapshot churn.
  - **★ fish `expected_pairs` MEASURED: 2, was null since Slice 1.** Read at
    voxel 128 — the only voxel at which the extractor selects the lateral axis
    for this mesh — at the prune whose leaf count equals the committed R=10. The
    two pairs are lateral offsets -14.06/+14.30 and -8.88/+7.61. Committed with
    its evidence (`fixtures/fish_bilateral_evidence.json`) and RECOMPUTED from
    it by the test rather than restated.
    **Why it was never measured, and why it changes how the scorecard reads:
    the fish skeleton is MEDIAN-DOMINATED.** At voxel 96, 8 of its 10 leaves sit
    within +/-1.6 of the lateral midplane out of a 22-unit lateral spread, so
    "keep the pairing that matches the most leaves" correctly picks the
    DORSAL-VENTRAL plane and emits dorsal/anal mirrors. The fish SERVES from
    voxel 64, where the same thing happens — so **the fish row's `pairs_kept`
    counts a MEDIAN pair and is not commensurable with its `expected_pairs`.**
    Every other subject's winning plane is the bilateral one, so only fish is
    affected. Recorded in the fixture rather than papered over.
  - **★ ADMISSION SHIPPED AS A SECOND GATED PATH, and the gate does real
    work.** `MIN_LEAVES, MAX_LEAVES = 4, 8` is untouched (see the pre-measurement
    decisions above); `structural_admission` + a new phase 4 let 9-12-leaf
    prefilter rejects compile, strictly after phase 3. Measured across the same
    144 configs: 73 pass the prefilter, 43 land in the 9-12 window, and **8 are
    admitted post-normalizer**. The rejection cause is startlingly clean —
    **all 35 rejections are the HUB term, and none is the pair or sliver term**
    (interior counts of 6-10 against a bound of 3), so in practice the gate IS
    the hub bound and the other two terms are currently free. The admitted set
    is quadruped at voxel 64 (7 configs, 9 leaves, 2 pairs) and bird at
    (128, 0.30). **fish and insect admit NOTHING**, so the two subjects the
    window was nominally aimed at cannot move through this path — their >8-leaf
    candidates are HUB-FRAGMENTED, not merely large, which is a more useful
    statement of the >8 problem than "the engine fails above 8 leaves" and is
    the concrete handoff to S8. (Re-measured after the escalation fix: the
    census is unchanged, because every rejected candidate failed on hubs rather
    than on the pair count the fix moved.)
    - The three gate terms each reuse an existing constant
      (`MAX_NORMALIZE_HUBS`, `SLIVER_RATIO`) rather than a new threshold, and
      the gate **does not read root degree** — a 9-leaf star is admissible and a
      test pins it, because S6 falsified the root-degree rule and caught a live
      agent quoting it to refuse a candidate that then served 6/6.
    - **Default-off when a serve is already held (`IDE_ADMIT_WIDE=1` to widen),
      and the reason is latency, not doubt:** admission can never displace a
      held serve, so on a subject that already serves it buys data and nothing
      else while costing up to `ADMIT_BUDGET` ladder runs at up to ~52s each
      (S3's measured failure-path cost). With nothing held it always runs and is
      a genuine last-chance rescue.
    - **The persisted >8-leaf corpus rows remain S8's.** Capture is suppressed
      for the pass exactly as phase 3 suppresses it (`capture.record`'s contract
      is that `nodes` is the REQUEST; a phase-4 tree is backend-synthesized),
      and the plan already specifies the separate provenance channel. What S7
      leaves behind is the compile attempts and their trace rows.
  - **★ THE 17 ">8-LEAF PRIOR" ROWS ARE NOT USABLE PRIOR DATA — a definitive
    answer to the question plan:230 raises.** `feasibility/corpus.jsonl` is
    **gitignored and untracked** (`mcp_harness/.gitignore:3`), so those rows
    exist on one machine and no CI checkout has them. Their `perturb_pack` was
    written by `tree_labeler.perturb_label` against the commit live at the
    file's mtime (0a89ba4, 2026-06-17), when the retry path was **jitter-only,
    12 rungs, and ASYMMETRIC-only** — symmetry-preserving jitter did not exist
    until e462096 on 2026-07-18. Today's ladder is order -> placement ->
    normalize -> jitter -> composed -> stub, so a `False` there means "12
    asymmetric nudges failed", a subset of a subset. All 17 are `False`; there
    is not one positive above 8 leaves anywhere. Only 12 sit in the 9-11 band
    (the other 5 are a 27-leaf outlier family) and there are **zero rows at 12
    leaves**. `dataset.DEFAULT_CORPUS` points at `corpus_wide.jsonl` and nothing
    live reads `corpus.jsonl` at all. Finally the gate trains `y =
    attempt0_pack`, not `perturb_pack` (`train_model.py:65-69`), so even current
    rows would need a new label column and a new objective. **S8 should treat
    the >8 band as having NO prior and generate it.**
- S5's edge-opt and stub stages each flag-gated behind the scorecard before
  default-on.
- S6 runs only after S2-S5's server surfaces are stable (the slimmed prompt
  points at final tool contracts). **RAN 2026-07-27; verdicts above.**
- Contingency (MCTS ladder, box-pleating backend) gets its own planning
  session — with a fresh prior-art pass per CLAUDE.md §0 — only if the S3-S5
  metrics demand it.
- **S8 MEASURED VERDICTS (2026-07-31; branch
  `claude/s8-rescue-normalizer-retrain-d326bc` from b69ce68; the retrain,
  provenance, dedup pin and >8 ceiling; evidence
  `docs/superpowers/2026-07-31-s8-gate-retrain-prereg.md`, scratchpad
  `eval_gate_s8.json`).** This is the last session in the plan.
  - **★ ADVERSARIAL REVIEW EARNED ITS COST FIVE TIMES OVER — AND THE MECHANISM
    S8 BUILT TO STOP THE S7 ARTIFACT HAD THE S7 DEFECT.** 6 lenses, 50 findings,
    46 verdicts (27 refuted, 19 confirmed), **five rounds of fixes**, and the
    single most useful outcome was a BLOCKER in S8's own work: its
    "provenance is off by default" pin was VACUOUS — it asserted
    `list(tmp_path.iterdir()) == []` where nothing was ever configured to write,
    so a mutant with the guard deleted wrote a real 577-byte row to disk and the
    pin still passed. That is the S6/S7 class, third session running, inside the
    session that quotes S7 about it.
    - **And then a fourth instance, one level up.** S8's review workflow carried
      a deliberate dead-agent detector, written from the S7 memory that verify
      agents dying on a usage limit still report "0 survived" and read as a clean
      bill. **The detector did not fire.** The `find:stats` lens — the one
      attacking the session's central statistical claim — died mid-response
      ("API Error: Connection closed"), and the workflow reported
      `lenses_incomplete: []`. Cause: `agent()` returns `null` on death, and the
      script did `.then(r => ({lens: k, ...r}))`; spreading `null` yields
      `{lens: 'stats'}`, which is **truthy** with `completed === undefined`, so
      neither `!found[i]` nor `found[i].completed === false` fired. The guard
      needed a null check BEFORE the spread, and "absent `completed`" must read
      as dead rather than as unset. **The generalisable rule, now stated four
      failures in: a health check that reads the object the failure produced,
      rather than the fact OF the failure, is not a health check.** The stats
      lens was re-run separately; the runtime's own `agents_error: 1` was the
      only honest signal, and it is what caught this.
  - **★ THE GATE RETRAIN IS A MEASURED NEGATIVE, AND THE ESTIMATOR IS THE
    POINT.** The plan's bullet asks whether structure features
    (min-interior-edge-ratio, root-children, per-hub leaf counts,
    order-canonicality) beat today's seven order-invariant, structure-blind
    ones. **They do not. `FEATURE_ORDER` does not move and no new artifact was
    fitted.**

    The available measurement error here was larger than S5's or S6's, because
    `n_leaves` ALONE is already a strong predictor — the attempt-0 pack rate is
    monotone .899 → .848 → .639 → .182 → .037 → .011 across k = 3..8. Any
    headline AUC gain from structure features would therefore prove nothing:
    the new features correlate with `n_leaves`, so a model that merely got
    better at reading `n_leaves` off them posts the identical gain. So the
    evaluation was **pre-registered in its own commit before any model was
    fitted** (arms, seeds, folds, sentinels, controls, decision rule and a
    written prediction), and the estimator was chosen so the error cannot
    survive it:

    > **Within-stratum AUC, strata = exact `n_leaves`.** Every row inside a
    > stratum has the identical `n_leaves`, so a model that is a function of
    > `n_leaves` alone scores them all the same and its within-stratum AUC is
    > **exactly 0.5** — by construction of the estimator, not on average.
    > Anything above 0.5 is, by construction, not `n_leaves`.

    | arm (5 seeds × 5 folds) | k=5 | k=6 | k=7 | band 5–7 | Δ vs A1 |
    |---|---|---|---|---|---|
    | `A0_leaves_only` | .500 | .500 | .500 | .5000 | −.1495 |
    | `A1_shipped` (today's 7) | .747 | .513 | .432 | .6495 | — |
    | `A2_shipped+structure` | .753 | .534 | .365 | .6548 | **+.0053** |
    | `A3_structure_only` | .682 | .550 | .304 | .6123 | −.0372 |
    | `C_POS` noisy label | .794 | .669 | .603 | .7402 | +.0907 |
    | `C_NEG` n_leaves² | .745 | .517 | .428 | .6489 | −.0006 |

    A2 needed +.02 and sign-consistency in ≥4/5 seeds; it returned +.0053 and
    3/5. Two independent runs are byte-identical (md5
    `43eba626aad0da588719acc8f408993e`).
    - **★ AND THE INDEPENDENT STATISTICAL AUDIT MAKES THE NEGATIVE STRONGER AND
      THE ARITHMETIC WEAKER.** Across-seed dispersion is **+0.0053 ± 0.0104** —
      sd twice the mean — and a row bootstrap gives CI **[−0.0197, +0.0308]**,
      P(>0) = 0.679. So the effect is not merely under the bar, it is
      indistinguishable from zero. Against that: **§6 said "support-weighted"
      without defining the weights, and the SIGN flips with the reading** (pairs
      +.0053 as implemented; rows −.0123; unweighted-over-k −.0134). The NO SHIP
      verdict is identical under all four, and the implemented pair-weighting was
      verified to equal the pooled Mann-Whitney concordance — **but no prose may
      lean on the sign of +.0053, and this document no longer does.** The study
      is also underpowered against its own bar: SE 0.0136 puts +0.02 at 1.47 SE,
      so a truly-zero effect had a 7.0% chance of clearing it. The only
      near-significant result in the whole study is a **degradation at k=7**
      (A2 −0.0666, P(>0) = 0.039) — pointing against the structure features, on
      an axis the decision rule never checked.
    - **The construction check fired, and it justified the aggregation with a
      number.** Under the primary (per-fold) aggregation `A0_leaves_only`
      returns exactly 0.500 at every k. Under the *pooled* out-of-fold
      aggregation — the obvious implementation — that same provably
      uninformative model returns **0.247 at k=8**, a large apparent signal
      manufactured purely by two fold-models disagreeing about one `n_leaves`
      value. Pinned in `test_eval_gate.py` and mutation-proven: swapping the
      harness to pool first makes the pin fail at 0.466.
    - **`C_NEG` is the control S5 and S6 both lacked.** Feeding the model
      `n_leaves` squared — an exact function of the stratum, the tautology in
      its purest form — moved the band figure by −.0006. That is what licenses
      reading +.0053 as a real-but-tiny structural effect rather than a
      re-measurement. One control would not have been enough: S6 established
      that a discrimination control proves a criterion CAN separate, not that
      it is right about which side is which, so `C_POS` and `C_NEG` are run in
      opposite directions and both must behave.
    - **The order thesis got a fair test and lost on the merits.** The
      pre-registration's prerequisite gate anticipated that
      `order_canonicality` might be constant on this corpus — in which case the
      thesis would be *untestable*, not refuted. It is not constant: 89 distinct
      values spanning 0.25–1.0, sd .198, inside the target band. So the
      strongest available candidate for "the shipped features are
      order-invariant while S3 measured order as the biggest rescue lever" was
      measurable, and did not pay.
  - **★ AND A FINDING NOBODY WAS LOOKING FOR: CONDITIONAL ON LEAF COUNT, THE
    SHIPPED GATE IS INDISTINGUISHABLE FROM CHANCE EXACTLY WHERE THE PRODUCT
    LIVES.** k=5 .747 (bird, humanoid; permutation p < .0005) but **k=6 .513**
    (quadruped, dog; p = .753) and **k=7 .432** (fish, insect; p = .408, CI
    [.282, .592]). The band's .6495 is carried almost entirely by k=5 —
    measured, k=5 supplies **100.4% of the band's excess over 0.5**.
    *(An earlier draft wrote "at or below chance" and "below a coin flip". With
    ten positives against 262 negatives at k=7 the null sd is .083, so .432 is
    0.8σ from chance and its CI covers 0.5. The independent statistical audit
    caught the directional overclaim; the finding survives it, because
    "indistinguishable from chance at both k=6 and k=7" is what the section's
    conclusion actually needed.)*
    This is invisible to any pooled metric, because pooled over all rows
    `n_leaves` does the work and `n_leaves` is the one thing the gate needs no
    model to know. **The honest reading is that the Tier 2.5 gate is today close
    to an `n_leaves` lookup table.** The useful next question is not "which
    features" but "what signal exists at fixed leaf count at all" — for which
    the answer, across twelve features including four purpose-built structural
    ones and one order-sensitive one, is: very little, and none at k=6–7.
  - **★ THE >8 CEILING, CLOSED — AND FAILURE ABOVE 8 LEAVES CHANGES KIND, NOT
    JUST FREQUENCY.** S7 supplied the mesh half (fish and insect admit nothing;
    their 9–12-leaf candidates are hub-fragmented, and all 35 admission
    rejections were the hub term). S8 supplies the corpus half, and the two
    converge. Measured on `corpus_wide.jsonl`:

    | band | rows | pos | `build_failed` | `no_pack_ibps` |
    |---|---|---|---|---|
    | ≤4 | 591 | 412 | 22% | 7% |
    | 5–7 | 862 | 259 | 39% | **28%** |
    | 8 | 266 | 3 | 86% | 11% |
    | 9–12 | 451 | **2** | **95%** | 3% |
    | 13+ | 430 | **2** | **98%** | 0% |

    1. **THERE IS NO POSITIVE CLASS TO LEARN ABOVE 8.** Two positives in the
       451 rows at k=9–12; four in the 881 rows across k=9–34. A retrain aimed
       at ">8" would be fitting a boundary to four rows, and generating more >8
       data mostly generates more negatives. The plan's premise for that bullet
       is refuted by its own corpus.
    2. **THE KNIFE-EDGE CLASS DISAPPEARS.** `no_pack_ibps`
       (POLYS_MULTIPLE_IBPS) — the class the entire rescue ladder was built to
       win — peaks at 28% in the 5–7 band and collapses to 3% at 9–12 and 0% at
       13+, while `build_failed` climbs to 95–98%. Above 8 leaves the packer is
       not losing near-misses that conditioning could rescue; it is failing to
       build. **That is why order, placement and jitter have nothing to offer
       there, and it is a better statement of the wall than "the engine fails
       above 8 leaves".**
    3. **★ THE FOUR >8 PACKERS ARE DEEP-AND-THIN, AND THE CORPUS CANNOT SPEAK TO
       THE ADMISSION GATE'S CALIBRATION AT ALL.** They are long thin trees with
       small branch points, not wide flap clusters — every one has
       `max_hub_leaves` ≤ 3 while carrying 6 to 18 interior nodes. *(The first
       draft listed those two vectors as "3, 3, 3, 2" and "6, 16, 18, 12" against
       "k = 9, 12, 16, 17" — the `max_hub_leaves` vector was zipped to the wrong
       trees; by ascending k it is 3, 2, 3, 3. Caught by adversarial review. The
       per-row table below is the measured truth and is why the prose no longer
       carries a second copy of it.)*

       *(An earlier draft of this bullet claimed the admission gate would reject
       all four ON THE HUB TERM, and inferred it from `MAX_NORMALIZE_HUBS = 3`
       rather than by calling the function. Running
       `mesh_to_tree.structural_admission` term by term shows the inference was
       wrong about the mechanism. Recorded rather than quietly fixed, per S7's
       precedent for its own three-wrong-numbers paragraph.)*

       | id | k | pairs | interior | max_hub_leaves | terms it FAILS |
       |---|---|---|---|---|---|
       | 1740 | 9 | 1 | 6 | 3 | **pairs**, hubs |
       | 1887 | 12 | 1 | 16 | 2 | **pairs**, hubs |
       | 1673 | 16 | 1 | 18 | 3 | window, pairs, hubs |
       | 1980 | 17 | 0 | 12 | 3 | window, pairs, hubs |

       All four are rejected, but **not distinctively on hubs**: two are outside
       the 9–12 window entirely so the gate never considers them, and both that
       are inside fail the PAIR term (`ADMIT_MIN_PAIRS = 2`) as well. And they
       fail it because all four are `source=random` synthetic trees with
       `n_sym_pairs ≤ 1` — a property of the tree GENERATOR, not of packability.
       (Control, verified: a 9-leaf star with two pairs IS admitted, exactly as
       S7's pin says; an earlier one-pair control read False for the pair term
       and briefly looked like a contradiction of S7. It is not.)

       **So the honest conclusion is a disjointness statement, not a calibration
       one: the corpus's >8 packers and the admission path's >8 candidates are
       different populations**, separated on axes the generator controls. The
       corpus cannot tell you whether the hub bound is right, and nothing here
       should be read as saying it is wrong. What survives is the observation
       that few-leaves-per-hub co-occurs with the only >8 packs anyone has —
       n=4, synthetic, offered as a place to point the next measurement and
       nothing more.
    **The thread is closed rather than left open for a ninth session:** the >8
    band is not a learning problem (no positive class), not a conditioning
    problem (the ladder's failure class is absent there), and the one structural
    lever anyone has proposed for it — the S4 normalizer that owns hubs —
    was measured by S4 rescuing zero. What remains is a *packer* question, and
    the plan's own Contingency already names the escape hatch for it
    (box-pleating / discretization). Nothing here justifies pulling that
    trigger; it justifies not re-litigating the band.
  - **RESCUE/NORMALIZER PROVENANCE SHIPPED, and the "sole id assigner" rule is
    enforced structurally.** `feasibility/provenance.py` writes one row per
    ladder ATTEMPT to its own gitignored file, hooked in `_drive_ladder` — the
    ONE funnel every rung passes on BOTH compile paths, the same property that
    made `_perturb_ladder` shared — so parent and spawn child cannot re-diverge
    on what is recorded. Off unless `IDE_PROVENANCE_PATH` is set, exactly as
    capture is gated, so the serve path is byte-identical by default.
    - A provenance row carries no `id`, no `gate`, and — load-bearing — no
      `nodes` and no `pairs`. `merge_captured.REQUIRED_KEYS` demands the last
      two, so `is_trainable` is False for every row in the file and `merge`
      drops and COUNTS them. **Feeding the file to `--captured` by mistake, the
      single most plausible way a diagnostic channel corrupts a training set,
      cannot inject one row.** Pinned, not asserted.
    - Measured end-to-end through the real serve path on an 8-leaf star: 45
      rows, one `request_key`, placement 1 / order 4 / jitter 24 / composed 8 /
      stub 8 — exactly one ladder pass, no parent/child duplication — and
      **`normalize` offered ZERO rungs**, which is precisely the class of fact
      capture structurally cannot report, since it records only the winner.
  - **THE NEVER-SORT-NODES DEDUP PIN SHIPPED, MUTATION-PROVEN TWICE.** The
    BEHAVIOR was already correct (`canonical_key`'s `sort_keys=True` sorts DICT
    keys, never the nodes LIST), so what was owed was a test that can SEE the
    regression it names — S7 having shipped an axis pin that passed under
    exactly its own regression, with a `sys.settrace` census proving the branch
    never ran. Proven at two levels: three monkeypatched mutants (sort by id, by
    length, by serialised node) each asserted to collapse 2 rows → 1, and a
    mutation of the REAL source that makes two of the new tests fail with the
    two identical keys printed side by side (verified and reverted;
    `merge_captured.py` is byte-identical to HEAD). `len(kept) == 2` alone was
    refused as vacuous: the test also asserts the rows survive with their orders
    INTACT and that every other field is equal, so list order is the only thing
    keeping them apart.
  - **`perturb_pack` GOT AN ERA TAG, NOT A DOCSTRING FIX — and it needed one,
    six times over.** `tree_labeler.perturb_label`'s docstring said "the ±10%
    ×12 server retry path" while calling `draft_and_compile_full_base`, whose
    retry path changed meaning at E1 2e39884 (jitter only, 12 rungs, asymmetric
    only) → E2 e462096 (symmetric then asymmetric, 24) → E3 24f5718
    (first-CLEAN-wins) → E4 34db484 (staged) → E5 cdf562d (+normalize) → E6
    05beb87 (+stub). E6 matters most: a `True` can now mean the ENGINE ADDED A
    FLAP and the tree as requested still does not pack, so two eras' `True`
    values are not the same measurement. `perturb_era()` DERIVES its stage half
    from **`server._ladder_stages()` — the set actually ENABLED, not the registry
    of stages that exist** — so it cannot go stale the way prose did, and a test
    pins the derived value to a literal so adding a stage reddens a test: the
    plan's "CLEAN-ERR flip = conscious re-bless event" rule applied to a label.
    Written by `build_dataset` AND by `capture` (the live rows that would
    actually feed a retrain), OMITTED not null when no ladder ran, and `era_of()`
    reads a missing tag as UNKNOWN, never as today's meaning.
    *(This sentence said `_ALL_LADDER_STAGES` until adversarial review found it
    describing a version the session itself had already replaced two commits
    earlier — a stale claim about the anti-staleness mechanism, which is worth
    recording precisely because it shows the failure mode does not respect
    intent. See the `IDE_LADDER_STAGES` defect below.)*
    - Found in passing and fixed: `_perturb_ladder`'s OWN docstring listed four
      stages, omitting normalize and stub — the same silent drift, one call away
      from the defect S8 was sent to fix.
  - **scikit-learn AND joblib PINNED (`ci.yml`), and the brief's framing of the
    exposure was inverted in a way worth recording.** `gate.joblib` is NOT a
    committed pickle — it is gitignored (`mcp_harness/.gitignore:12`) and
    REGENERATED per checkout from the committed corpus, while
    `dataset.py:13-15` promises "a fresh checkout reproduces the same model from
    git alone". That promise holds only while the TRAINER is fixed, and
    scikit-learn arrived only transitively through `skeletor==1.5.0`'s
    unbounded `scikit-learn>=0.23`.
    - **The mechanism is already real for this exact call site, verified in the
      installed source rather than relayed:** `train_model.py:94` fits
      `RandomForestClassifier(class_weight="balanced", random_state=seed)` with
      no `sample_weight`, and sklearn 1.9 (#31529) changed the bootstrap draw
      for precisely that path — `_forest.py:401-403` now does
      `if sample_weight is None: _sample_weight = expanded_class_weight` and
      feeds it to `_get_n_samples_bootstrap`.
    - **And a silent refit is scorecard-moving.** `test_gate_mesh_region.py:25-36`
      records fish and insect at `p_pack ~0.17` against a `block_threshold` of
      0.0167, with margins moving ~±0.15 under a seed change and a 7-seed sweep
      already finding seed 3 BLOCKING both. The gate EXCLUDES `infeasible`
      candidates from the compile queue (`mesh_to_tree.py:1328`) and RANKS the
      phase-2 queue by `p_pack` (:1325, :1357), so blocking fish moves a
      scorecard row with no code change anywhere in this repo.
    - Pinned at 1.9.0 / 1.5.3, under which the served 2026-06-24 artifact still
      refits from the committed corpus with identical thresholds and identical
      fixture predictions — locking in a state proven good, and a no-op locally.
    - **CORRECTION to the brief: there IS a CI check on model quality.**
      `test_gate_mesh_region.py:37-60` trains from the real committed corpus and
      asserts `val_recall_feasible >= 0.95` plus all five mesh fixtures
      in-distribution. What is missing is narrower and worse: no test ever
      touches the SERVED artifact, and `test_gate_startup.py:20-27` writes 8
      bytes of the literal string `sentinel` to `gate.joblib` and asserts the
      gate is "ready" — auto-train fires only when the file is ABSENT, so a
      corrupt, stale or wrong-corpus artifact is indistinguishable from a good
      one. Named here; not fixed by S8 (see the closing section).
  - **★ THE SCORECARD FREEZE RESTS ON A DIFFERENT ARGUMENT THAN S7's, BECAUSE
    S7's DOES NOT TRANSFER.** S7 froze the goldens structurally (`bless.py`,
    `runner.py` and `cases.py` contain no reference to `mesh_to_tree`). The
    analogous claim for the gate is **TRUE of the cohort and FALSE of the
    scorecard**:
    - **Cohort: structural, and it holds.** `grep -n '_gate\.\|_load_gate\|_GATE'
      mcp_harness/server.py` returns only the import, `_GATE`/`_load_gate`
      themselves, and ONE call site — and that call site is inside
      `predict_tree_feasibility`, the MCP tool, nothing else. *(Stated as the
      grep rather than as line numbers: the first draft quoted b69ce68's
      49/2269-2280/2297, which were already stale in the commit that wrote them
      and moved twice more during the session. A locator that rots is worse than
      no locator, and review caught it.)*
      `draft_and_compile_full_base` never reaches it. Confirmed empirically by
      pointing `FEASIBILITY_GATE_PATH` at a nonexistent file and getting the
      committed outcomes on rows 85 (served) and 90 (residual) with
      `server._GATE is None`. **A gate retrain cannot move 18/24.**
      **MEASURED ANYWAY, end to end through the real serve path, 24/24 rows in
      988s: `SERVE RATE 18/24 (75.0%)`, residual `[90, 353, 500, 830, 865,
      2099]` — IDENTICAL to the S5b list, unchanged now through S6, S7 and S8.**
      Serving stages: order 8, placement 4, stub 3, jitter 2, composed 1. Run
      serially and alone, per the recorded hazard that a cohort sharing a
      machine with other spawning jobs reports a FALSE residual. Scratchpad
      `cohort_s8.json` / `run_cohort.py` — and note that there is still **no
      committed cohort runner**, so every session has now written its own; that
      is named in the closing section.
    - **Scorecard: REFUTED.** `benchmark_subjects.measure` →
      `auto_mesh_to_metric_tree` → `_default_gate()`, and `gate.predict` both
      excludes and ranks (above). So the scorecard IS gate-sensitive, and its
      freeze here is not structural: it is that **nothing the scorecard reads
      changed.** The verdict was NO SHIP so no artifact was fitted, and
      `ds.extract_features` still emits exactly the frozen seven, so the
      five-member lockstep is intact. The structure features live in their own
      module, consumed by `eval_gate.py`, and never enter `FEATURE_ORDER`.
    - **★ MEASURED: ALL SIX ROWS FROZEN.** `benchmark_subjects.py --baseline
      fixtures/scorecard_baseline.jsonl`, run WITH the S8 changes present,
      output: **`no axis moved: quadruped, bird, humanoid, fish, insect, dog`**.
      `nudge_marker` 0/6 and `asymmetric` 0/6 both hold.
    - **A correction adversarial review forced, and the corrected version is
      BETTER evidence.** An earlier draft offered "`gate.joblib` is
      byte-identical at md5 `6e317609e12b54b987f52be0d1849f18`, dated
      2026-06-24" as the freeze evidence. That is MAIN's artifact — but the
      scorecard ran in the WORKTREE, which has its own (md5
      `2083da6ef9394def453b8b99edeb0e04`, dated 2026-07-25). The quoted hash was
      not the artifact actually exercised, and **byte-identity was the wrong
      invariant anyway.** Measured, the two are independent refits of the same
      corpus that agree on everything load-bearing and differ only in bytes:

      | | main | worktree |
      |---|---|---|
      | md5 | `6e317609…` | `2083da6e…` |
      | metadata date | 2026-06-24 | 2026-07-25 |
      | `block_threshold` | 0.016667 | 0.016667 |
      | `ood_threshold` | 0.862617 | 0.862617 |
      | `feature_order` | the frozen 7 | the frozen 7 |

      Neither file was written by S8 (both mtimes predate the session). And the
      stronger claim the correction buys: **S7 measured the committed baseline
      in MAIN against one artifact, and S8 reproduced it exactly against a
      DIFFERENT one** — so the six rows are shown insensitive to which of these
      two artifacts serves, rather than merely protected by nobody touching one.

## Closing state of the arc (written by S8, 2026-07-31 — the last session)

Eight sessions, S1 → S8. This section exists so the arc ends with a record
rather than evaporating, and so the next person can tell in one read what is
settled, what was tried and failed, and what is genuinely unowned.

### What shipped

| slice | shipped | measured effect |
|---|---|---|
| 1 | Truth: unclamped fidelity, MUSE-style multi-axis scorecard, `anatomy_reference`, CLEAN-ERR tripwires | the baseline every later claim is measured against |
| 2 | Structured error envelope, error→recipe table, drain-before-downgrade, bad-poly ids | all 6 serves unchanged; only `error_codes` moved |
| 3 | **Staged rescue ladder** (order → placement → jitter → composed) | **cohort 29.2% → 62.5%**; the single biggest behaviour change in the plan |
| 4 | Composed normalizer (sliver contraction + rehome + canonical order) as a variant generator | **rescues ZERO**; kept as a stage, honest about it |
| 5 | C++ bad-poly diagnostics → JSON node ids | feeds the S2 envelope |
| 6 | Lang's `tmStubFinder` wired to the serve path | **3/9 of the S3+S4 residual**; cohort → 75% (18/24) |
| 7 | Optimal-assignment pair detection; structure-gated 9–12-leaf admission | **fish 6→7 leaves and jitter→order**; proportion integrity 1/6 → **0/6** |
| 8 | Rescue provenance channel, never-sort-nodes pin, `perturb_pack` era tag, sklearn pin, conditional gate evaluation | serve path unchanged; the retrain is a measured negative |

The charter's headline metrics, end state: **cohort serve rate 29.2% → 75%
(18/24)**; **`nudge_marker` 1/6 → 0/6 and `asymmetric` 0/6**, i.e. proportion
integrity met outright; dog serves **6/6 with both pairs** (the Slice-1
acceptance) via a proportion-preserving placement rescue.

### What was refuted — the durable negatives

These cost real sessions and are the most reusable thing the arc produced. None
should be re-attempted without a NEW measurement that beats the recorded one.

1. **Edge-opt: 0 of 9 across 562 arms** (S5). Over all edges `tmEdgeOptimizer`
   writes one shared strain scalar, which is a uniform rescale and provably
   redundant with scale optimisation — so a near-zero achieved strain there is a
   TAUTOLOGY. There is deliberately no dormant code to re-enable.
2. **The composed normalizer rescues zero** (S4), and the unbounded probe packs
   0/9 residuals, 5 of which are stars with nothing to normalize.
3. **The Reeb-graph extraction flag is unbuildable-and-uncashable** (S7).
   `by_wavefront` ALREADY IS the geodesic Reeb construction the bullet proposed
   as its alternative, and the "voxel-thinning baseline" it would be diffed
   against does not exist. Probe D then ran on the dog: every alternative
   skeletonizer reaches the same 6-leaf plateau.
4. **Structure features do not beat the shipped seven, conditional on
   `n_leaves`** (S8, above), and the order thesis in particular lost on the
   merits rather than being untestable.
5. **The >8 band is not a learning target** (S8): 4 positives in 881 rows, and
   the ladder's own failure class is absent there.
6. **Order alone never packs the raw 6-leaf dog** (S1 Probe A: 0/12) — though
   order remains a 45.8% cohort-level lever.
7. **The root-degree rule is false** (S6): a live agent quoted it to refuse a
   candidate that then served 6/6. S7's admission gate deliberately does not
   read root degree.

Refuted about our own *measurements*, which is the part that generalises:
S5's tautology, S6's `"changed"`-inside-`"unchanged"` scorer, S7's vacuous axis
pin (passed under the exact regression it named), and S7's "0 findings survived
refutation" that was an ARTIFACT of the verifier agents dying on a usage limit.
Every one was caught by an adversarial pass, and three of the four were caught
only because someone re-derived the claim by hand.

### ★ What no session owns

Named here rather than left to evaporate. None of these is blocked; each was
consciously declined, and the reason is recorded.

1. **Bird's reference-count ratchet.** The extractor finds **R=5** while
   `anatomy_reference` commits **R=4**, so `served_fidelity` is pinned at 0.75
   and cannot reach 1.0 no matter what the packer does. Declined by **S2, S3 and
   S7 in turn** — S7 additionally proved the adjacent hypothesis wrong: bird's
   missing second pair is not missed by the matcher, it is **ABSENT FROM THE
   SKELETON**, and its pairs change at **zero of its 24 configs**. So this is a
   *reference-count* question (is a bird 4 flaps or 5?), not an extraction or
   matching one, and it needs a human decision about the anatomy target before
   any code moves. `test_anatomy_oracle.py:95-106` currently PINS the
   disagreement (5 != 4), so resolving it is a deliberate act with a visible
   diff.
2. **The 6 residual cohort rows: 90, 353, 500, 830, 865, 2099.** Unchanged since
   S5b through S6, S7 and S8. **All are ≤8 leaves and three are 8-leaf stars.**
   S5's leaf-count control explains them without excusing them: k=8 sits flat at
   ~35% compile rate at every jitter level, and an equal-length 7-star fails
   while 4/5/6/8-stars pass — so these rows ask the packer for something it
   fails at roughly two thirds of the time regardless of conditioning. Every
   shipped stage has been tried on them. They are the honest floor of the
   current ladder, not a bug with a known fix.
3. **Hub fragmentation above 8 leaves.** S7 named it as the real >8 blocker (all
   35 admission rejections were the hub term; fish and insect admit NOTHING
   because their 9–12-leaf candidates are hub-fragmented, not merely large), and
   **the S4 normalizer that owns hubs rescues zero of them.** S8 adds that above
   8 leaves the failure class changes from knife-edge to `build_failed` (95–98%),
   and that the corpus CANNOT adjudicate the admission gate's calibration —
   its four >8 packers are synthetic trees with ≤1 pair, so they fail the gate
   on the pair term and the window as well as on hubs, which makes them a
   different population from the mesh candidates the gate actually sees. The
   cheap next measurement is therefore NOT "re-cut the gate on `max_hub_leaves`"
   — that would be fitting to n=4 synthetic rows — but "generate >8 candidates
   that pass the pair term and vary hub structure, and measure their pack rate."
   Nobody owns that.
4. **There is still no committed cohort runner.** `fixtures/rescue_cohort.json`
   commits the 24 ids and the expected residual, and its `_meta.how_to_measure`
   records the recipe — but every session from S4 to S8 has written its own
   throwaway script to run it, which is exactly the reproducibility gap that got
   the *ids* committed at S4. ~40 lines, and it must run serially and alone
   (a cohort sharing a machine with other spawning jobs reports a false
   residual). S8 measured 18/24 with a scratchpad script rather than fixing this,
   because committing a runner on the arc's last day would ship an untested
   fixture-adjacent tool with no session left to shake it out.
5. **The served gate artifact has no quality check** (found by S8, not fixed).
   `gate.joblib` is gitignored and auto-trained only when ABSENT, and
   `test_gate_startup.py:20-27` shows 8 bytes of the string `sentinel` passing
   as a ready gate. Both auto-train sites (`agent_loop.py:974-978`,
   `mesh_to_tree.py:903-906`) DISCARD the report `train_model.fit` returns,
   which already carries `val_recall_feasible`. The cheapest real fix is to
   assert that report against the floor CI already enforces (0.95). This is the
   parked **world-model-data-loop-deploy-concern**, now with a named line and a
   one-line remedy; S8 pinned the toolchain under it but did not close it.
6. **The Zero-to-CAD / CADCrafter corpus bootstrap (plan:238-241) is DROPPED,
   not deferred.** Both are real prior art, but they bootstrap a corpus, and
   S8's measurement says this corpus's problem is not volume — 2600 rows, 678
   positives — but that the region the plan wanted to learn has no positive
   class, and that at fixed leaf count the existing 2600 rows already support
   almost no signal at k=6–7. Synthesising more rows of the same kind buys
   nothing that can be stated in numbers beforehand, which was the bar. Reopen
   only with a stated, quantified expectation.
   **The bullet has a SECOND half, and it is dropped for a different reason.**
   "Capture verdicts double as DPO preference pairs for the drafting prompt"
   (CADCrafter) is not about the corpus at all — it is about fine-tuning the
   agent that drafts trees, and the measurement above says nothing either way
   about it. It is dropped because the product's drafting agent is a hosted
   `claude-sonnet-5` behind an API (memory: llm-provider-state), so there is no
   weight-update path to apply a preference pair to; DPO would require either a
   self-hosted model or a fine-tuning contract this project does not have. That
   is an infrastructure fact, not a measured negative, and it is the honest
   reason. *(An earlier draft of this bullet answered only the corpus half;
   adversarial review pointed out the ask was two things.)*
7. **The Contingency (MCTS ladder, box-pleating backend) never fired and should
   not fire on this evidence.** Its trigger was "cohort rescue below ~70% or a
   persistent >8 wall after structure-gated admission data exists". The first
   half did not fire (75%). The second half is now answered rather than open:
   the >8 wall is real, but S8 shows it is a *packer* problem, not a
   conditioning or learning one. If anyone ever pulls the box-pleating trigger,
   §0 requires a fresh prior-art pass first.
