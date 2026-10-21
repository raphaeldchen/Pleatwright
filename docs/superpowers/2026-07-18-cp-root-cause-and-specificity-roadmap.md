# CP "doesn't look like the model" — root cause, live HF run, and the specificity roadmap

**Date:** 2026-07-18.
**Trigger:** mid-B5 doubt — Origami Simulator's bundled examples (crane, flapping bird) fold
into recognizable models; the CPs our pipeline generates do not. Suspicion: a defect in metric
tree generation or CP compilation.
**Method:** 6-agent research workflow (theory, artifact math audit, viewer-code trace, external
sources, fresh live compiles, adversarial defect-hunt) + adversarial completeness critic + live
browser experiments folding both sides in the *same vendored simulator engine*, + a live
`MESH_PROVIDER=hf` end-to-end run. Every claim below was verified against code, artifacts, live
sim behavior, or primary external sources.

---

## 1. Verdict

**There is no geometry-math defect in the compiler.** The observed gap is definitional:

- TreeMaker output is a **uniaxial base** — a flat-folding flap arrangement. Its exporter
  (`mcp_harness/TreemakerWrapper.cpp` ExportFold, ~lines 895–908) emits exactly 9 FOLD keys and
  never `edges_foldAngle`; the bridge ([ide-bridge.js:18-21]) synthesizes **±180° (fully flat)**
  for every M/V crease. A flat-folded base is a stack of coincident flaps — the analytic fold of
  `dog.fold` collapses 104 vertex-images to 26 points; five flap tips land on the *same* point.
- The simulator examples are **hand-finished artist CPs for finished models**: SVG stroke
  opacity encodes partial target angles (`angle = ±opacity×180`, pattern.js:70-89).
  `traditionalCrane.svg` carries 45°/90°/135° creases; `langCardinal.svg` 90°/135°. The Lang
  examples are credited in the sim itself as "Designed by Robert Lang using Treemaker" — even
  TreeMaker-designed models reach the sim as artist-finished CPs.
- **Control experiment:** the classic hand-designed *bird base* folds into an abstract 4-point
  star in the same engine — not resembling the subject is a property of bases as a category.
  Lang's manual (p.169): "TreeMaker only provides a base. It's still up to you to thin the
  flaps and convert the base into the final model." Our own roadmap spec says the same
  (finished-model-view-research.md:104-106: "still a spiky base, not a dog").
- Nuance worth keeping: `flappingBird.svg` has NO partial angles (folds fully flat) yet reads
  as a bird — its *flat silhouette* was designed. Silhouette-first design is a viable cheaper
  sub-goal alongside full 3D shaping.

**Compiler math verified sound on both goldens and today's live output:**

| artifact | closure max err | interior Maekawa violations | Kawasaki max dev |
|---|---|---|---|
| goldens `dog.fold` | 2.5e-8 | 0 / 15 vertices | 4.4e-6° |
| fresh `live_dog.fold` (template) | 2.3e-9 | 0 / 11 | 1.2e-6° |
| fresh `live_bird_wings.fold` | 8.5e-10 | 0 / 11 | 4.1e-7° |

Oriedita's "4 geometry violations" on the template compile are hull-*boundary* vertices — the
long-documented hull-frontier false-negative (ACCEPT policy), not interior math errors.
M/V-assignment incompleteness was specifically hunted and **refuted**: export requires
`HasFullCP()`; Oriedita is check-only and patches nothing.

## 2. Real defects found (they compound the "broken" impression)

1. **Every animal gets the same base.** `MESH_PROVIDER=fake` (default + `.env`) resolves deer /
   ant / dog / tardigrade / elephant all to `quadruped.glb` (`mesh_acquire.py:26-43`), and the
   SYSTEM_PROMPT **bird template is numerically identical to the quadruped template**
   (`agent_loop.py:153-158`) — `live_bird.fold` came out *byte-identical* to `live_dog.fold`
   (all seeds pinned).
2. **The viewport folds the squared display file, and 34–51% of it is uncreased slab.**
   Corner paper: dog 33.6%, quad 50.4%, hshape 51.4%. The folded visual is dominated by a blank
   flat slab; what folds is `display_json`, not the linted artifact.
3. **NEW UI bug — 60% boot vs 0% label.** The sim boots at `creasePercent 0.6`
   (`globals.js:49`); `viewer.ts` never posts an initial `setFold` (`OrigamiViewer.tsx:9`
   starts the label at 0%). A fresh fold is driven to 60%-of-flat while the UI claims unfolded.
4. **NEW defect — perturb rescue breaks bilateral symmetry.** `_jitter_nodes`
   (`mcp_harness/server.py:272-287`) jitters every edge independently ±10%;
   `tmConditionNodesPaired` mirrors node *positions* only, never edge lengths → rescued
   "symmetric" animals ship lopsided (golden dog: max mirror mismatch 0.026 after 2 nudges).
5. **Flat-equilibrium parking is still marginal.** The squared bear-base parked persistently in
   a live run (height frozen at 5.5e-4 for 10+s at a 95% target) despite the 2e-4 z-lift. A
   *downloaded* `.fold` in the stock origamisimulator.org won't fold at all (its import modal
   defaults to deriving ~0° targets from current — flat — geometry).
6. **Mesh→tree can drop features / mis-rank.** `PRUNE_FRACTION 0.60` "collapses ears/snout"
   (`mesh_to_tree.py:23-25`); the ranking comment (:31-47) admits `p_pack` over-rewards
   fewer-flap trees.

## 3. Live HF run ("a dog", `MESH_PROVIDER=hf`, hysts/Shap-E)

Works end-to-end: 874KB dog `.glb` → 68s extraction (voxel 64, prune 0.6) → compile 2.5s.

- **The tree is measurably dog-derived**: 5 leaf flaps, *differentiated* lengths
  `[0.338, 0.343, 0.382, 0.297, 0.275]`, one bilateral pair, sub-hub topology — vs the
  template's uniform 0.3s and byte-identical dog/bird. Input specificity works.
- **Finding A — prune dropped a feature**: a ~6-feature dog came out as 5 flaps.
- **Finding B — knife-edge packing ships strained CPs**: compile needed a ±10% nudge
  ("did not pack exactly" in `frame_title`) and the shipped CP has **real interior
  violations** — closure 3.8e-4 (5 bad edges), 5 interior Maekawa violations (one vertex
  M=1,V=5), Kawasaki 0.049° — unlike template compiles (clean to 2.3e-9). Oriedita flagged it
  ("4 M/V-fixable, 6 geometry") but the one-shot serve path has no repair loop, and the lint
  verdict prints the same "FAILED" for real interior defects as for benign hull-frontier cases.
  In the sim it settles into a strained half-collapse (height 0.27 at a 100% target).

**Template path = perfect math, generic animal. HF path = the right animal, imperfect math.**

## 4. The remediation lever, proven

Injecting partial `edges_foldAngle` (uniform ±120°) into our own fresh compiled dog and loading
it through the bridge produced a **stable, coherent 3D form at 100%** (height 0.349, converged).
The bridge honors supplied angles (it only synthesizes ±180 when the key is absent). The entire
difference between "flat wad" and "shaped model" is *which angles* — i.e., Pillar B's job.

Probe gotchas (will bite again): compiles run via `python - <<EOF` or scripts without an
`if __name__ == "__main__":` guard break the spawn worker and masquerade as
"geometry engine crashed … 12 nudges failed". Run compiles from a real, guarded script file.

---

## 5. Roadmap: prompt → CP for specifically what the prompt requests

Draft was adversarially reviewed by two agents (feasibility-vs-repo, completeness-vs-research-
memory); corrections are folded in. Ordering is load-bearing.

### Stage 0 — Truth in the viewport + ship the pose we already have (days)

- **0.1** Post initial `setFold` on viewer `ready` (`viewer.ts:52-59`; fixes 60%/0% mismatch).
- **0.2** Label the 3D view "compiled base (pre-shaping)".
- **0.3** Hull-crop toggle for the corner slab (cheap: `viewer.ts:45` already picks
  `displayJson ?? json`). Translucent F-faces would need per-face materials — skip.
- **0.4** Symmetric jitter: one shared factor per bilateral pair (`mcp_harness/server.py:277`).
- **0.5** **Default pose on every compile** — automate `suggest_pose_stack` (`server.py:721`;
  productized in Phase P, proven live in Lane H) so `display_json` ships partial
  `edges_foldAngle`. Also the routed Theorem-Z escape (off-flat serve states leave the
  flat-state cokernel trap). Gates: B4 strain oracle must gate posed folds; platform chips
  h-f1 (Model-tab extraction visibility race) and h-f2 (Groq client timeout) first. Caveat:
  partial angles avoid the flat bifurcation but do NOT eliminate parking generally (kick
  research: parking documented on posed targets).

### Stage 1 — The right animal's tree (input fidelity) — **DONE 2026-07-19**

All five items shipped (see `2026-07-19-stage1-mesh-fidelity-handoff.md` for evidence):

- **1.1 DONE** — interactive serve defaults to `MESH_PROVIDER=hf` + `IDE_CAPTURE_PATH` via
  `web/serve_env.py` (applied BEFORE `import agent_loop`: the MCP child env is snapshotted at
  import); `_mcp_child_env` forwards the config allowlist through the sanitized child boundary;
  HF path hardened (typed-exception retries, quota fail-fast, actionable errors); code default
  stays `fake` (C-8). Bonus fix: serve-time capture was DEAD (tests-only `runner` import made
  every row silently drop) — found live, fixed, regression-tested.
- **1.2 DONE** — bird template differentiated (wings 0.4 / legs 0.25 / head 0.3 / tail 0.35,
  measured live to pack EXACTLY, node order unchanged); prompt<->benchmark sync now test-pinned.
- **1.3 DONE** — heuristic anatomical labels per leaf (positions + PCA frame captured at
  candidate creation) rendered in the reference report.
- **1.4 DONE** — reference feature count R = widest leaf-count-vs-prune plateau (calibrated on
  recorded real curves incl. the HF dog: R=6); two-phase compile queue (fidelity picks first,
  legacy gate queue second — a strict superset, no reachable winner lost); fidelity +
  reference_count on MeshTreeResult/trace/report. Gate untouched (2.4 unchanged).
- **1.5 DONE** — report renders a MISSING FEATURES repair plan wiring A-9 fill;
  SYSTEM_PROMPT carries the fill-BEFORE-posing ordering contract; the pairs-blind worker
  jitter is fixed via one shared `_perturb_ladder` (fill-path rescues stay symmetric-first).

Live acceptance (2026-07-19): dog/deer/crane through the real serve path → three DISTINCT
trees (byte-distinct folds), each traceable to its own HF mesh cache sha. The dog still lands
5-of-6 flaps — but the trace now PROVES the 6-leaf candidates were compiled first and failed
(engine limit, not ranking), and the deficit ships as a repair plan instead of silence.
Known Stage-2 interaction confirmed: all three live compiles needed the ±10% nudge (all
rescued symmetrically) — the 2.1/2.2 lint-split + micro-adjust work is now the bottleneck.

### Stage 2 — Sound compiles on measured trees (knife-edge robustness)

**STATUS 2026-07-25: 2.1 + 2.2 + 2.3 + 2.4's machinery DONE; the 2.4 RETRAIN
is DEFERRED on measured evidence** (2.1/2.2 on branch
claude/stage2-cp-specificity-lint-35830c, handoff
`2026-07-24-stage2-lint-split-handoff.md`; 2.3/2.4 on
claude/stage23-mission-execution-1b52fb, handoff
`2026-07-25-stage23-mission-handoff.md`). Stage 2 is closed except for the
retrain, which is blocked on DATA VOLUME, not on missing code.

- **2.1 DONE:** the lint verdict is CLASSIFIED (`lint_verdict.py`): first line
  `Flat-foldability FAILED [BENIGN|REAL|MIXED|UNCLASSIFIED]`, per-violation
  paper-frame coords + locally re-audited facts, a machine `DETAIL:` JSON
  line, a closing `Classification:` directive; truly-clean stays byte-"Pass"
  and the FAIL-LINT baselines never flipped (bless dry-run diff EMPTY). KEY
  FINDING that reshaped the design: the benign class is NOT
  hull-boundary-distance — recompiled star-5/cat-spine4 violations are
  floating-point noise (~2e-6 deg) at INTERIOR vertices tripping Oriedita's
  ~1e-6-deg internal tolerance, and Oriedita's rule labels are unreliable
  (ANGLES at parity defects, MAEKAWA at |M−V|=0). The classifier is
  per-vertex first-principles re-audit (cp_audit's shared machinery, tol
  1e-3°); fail direction is false-FAILED-never-false-Pass by construction.
  The SYSTEM_PROMPT now trusts the label (the pattern-matching heuristic
  that blessed the hf_dog's real defects is deleted).
- **2.2 DONE (two halves):** server — the perturb ladder audits every pack
  (cp_audit) and serves the first CLEAN rung (`_search_first_clean`; extra
  budget `IDE_LADDER_EXTRA_TRIES`=6, kill switch `IDE_LADDER_AUDIT`=0); a
  dirty-only exhaustion serves the best-scoring pack with an explicit
  `[ide: cp-audit: ...]` frame_title marker, never a failure. bridge —
  web/server.py fires a capped `[CP AUDIT]` synthetic-message repair turn
  (strain-oracle guard discipline; `IDE_CP_REPAIR_RETRIES`=1, 0=inform-only)
  keyed ONLY on the marker. Live: the hf dog improved 7→5 interior Maekawa
  (best of 3 packed rungs, honestly marked); the crane has NO better rung in
  the ±10% ladder (2 interior Kawasaki 0.107°, now marked, previously
  silent); the deer's nudge was already clean. (Optimizer convergence knobs
  in the compiled .so remain the heavier unexplored lever.)
- **2.3 DONE:** M/V repair shipped as a *solver*, not a patch (`mv_repair.py`,
  the `repair_mv_assignment` tool, and the ladder re-solving labels before it
  serves a best-dirty pack; `cp_audit` now owns the M/V-arrangement oracle, so
  "ladder clean" is sufficient). Joint reassignment, certified by cp_audit, JVM
  never in the loop: the golden hf-dog ladder-best base goes 5 → 0 interior
  defects at 5 flips in 0.68 s with closure bit-identical. Two measured laws
  bound it — a flip moves D = M−V by ±2 at BOTH endpoints, and an ODD |M−V| is
  flip-INVARIANT (geometry, refused honestly rather than attempted).
- **2.4 machinery DONE; retrain DEFERRED (measured 2026-07-25).**
  `feasibility/merge_captured.py` turns capture rows into corpus rows (ids
  above the corpus max — `dataset.existing_ids` KeyErrors on any id-less row;
  canonical-tree dedup keeps the MOST-INFORMATIVE row, ts as the secondary key
  (a deliberate deviation from the plan's literal "keep first by ts" — see the
  module docstring); `perturb_pack` None-vs-False preserved;
  attempt-0-only `failure_mode`; the `gate` field stripped as old-model
  leakage; every capture schema era tolerated), and
  `dataset.training_corpus_path()` + `FEASIBILITY_CORPUS_PATH` plumb any corpus
  through train_model, `ensure_gate_trained`, `_default_gate` and the mesh
  tripwire tests. **The retrain itself is deferred because the data is thin and
  measurably harmful:** all three capture sources hold 33 rows → 25 distinct
  trees, of which ONE packed at attempt 0 (4% vs the corpus's 26%), and the
  merged corpus is 0.95% captured rows. Over 7 training seeds the merge left
  `val_recall_feasible` at 0.9853 EVERY time (zero measured gain) while the
  `insect` mesh fixture's margin above the block threshold fell on 7/7 seeds
  (mean +0.233 → +0.071), and at seed 3 BOTH thin-margin fixtures (fish,
  insect) flipped to `infeasible` — the gate would have started blocking real
  meshes. The "needs nudge" label the retrain is FOR is also not learnable yet:
  `corpus_wide.jsonl` carries `perturb_pack: null` on all 2600 rows, so the
  entire non-null ladder signal in existence is 21 rows (4 True / 17 False).
  Unblock by VOLUME first — a synthetic ladder-outcome corpus pass (the
  `mesh_like` precedent, PR #9: label a batch with `tree_labeler.perturb_label`
  so the corpus has a nudge class at all), then re-run the 7-seed margin sweep.

### Stage 2.5 — Unlock base mobility (prerequisite for shaping search)

Theorem Z proves flat compiled patterns are fully locked (dog min ‖κ‖ 0.0225875, rel=1.0
forced); B5 pose-fit was CAPPED as a research negative; whole-pose floor 119.14; the T-search
REFUSED tree-space remedies. Angle search on unmodified bases optimizes inside a proven
ceiling. Routed remedy (2026-07-17 handoff): **composed-move kappa-descent over the
crease-augmentation lattice** — `crease_augment.py` + `mobility_search.py` + the kappa gate
ship; only the composer is new (single moves soften 7-8× via hub-cone breaks; none breaks the
lock). Parallel route: the off-flat serve state from 0.5.

### Stage 3 — Look like the subject (artistry)

- **3.1** B2 semantic op mapping with the vocabulary that actually ships: reverse_fold,
  outside reverse, crimp, reverse_deep, sink(=reverse_deep 180). "Thin flap" (B1 narrow-flap)
  was never built; interior-pocket squash deferred — body-rounding eventually needs one.
  Tracer-bullet on template trees now (they already carry semantic names); don't block on 1.3.
- **3.2** Target-mesh-guided search *redefined post-unlock*: the same HF mesh is the goal
  silhouette. Honest evaluators: `flat_fold`/folded-state engine = flat state only (fast);
  shaped-3D eval = HEADED sim capture, 30-90s/candidate, visible-tab-only → search must be
  sample-efficient. Sequence after 2.5/0.5 — do not re-run capped B5 against the lock.
- **3.3** Parallel cheaper track: silhouette-first flat design (flappingBird lesson).
- **3.4** Model tab: essentially done (`CADViewer.tsx` reads `displayJson`; capture path
  exists) — it renders whatever the display path serves.

### Sequencing logic

Stage 0 is hygiene plus the one Stage-3 item already productized (0.5) — it changes first
impressions immediately and opens the off-flat route. Stage 1 makes the tree about the right
animal (HF proven live today). Stage 2 makes measured trees compile as cleanly as templates
(today they don't). Stage 2.5 gates any shaping search that wants to move the base. Stage 3 is
where "looks like a dog" lives. Nothing in Stages 0–2 makes the base *resemble* the animal —
they make it the *right base*, honestly presented.

---

## 6. Session artifacts

Scratchpad (session-local): `live_dog.fold` / `live_bird.fold` (byte-identical) /
`live_bird_wings.fold` + display variants; `hf_dog.fold` + display; `live_dog_shaped.fold`
(±120° lever probe); `artifact_audit.py/.json`; CP SVG renders; `wf_*.json` (six investigator
reports + critic); `roadmap_draft.md` + `roadmap_final.md` + critique output. HF dog mesh
cached at `mcp_harness/generated_meshes/36f4aec…/mesh.glb`. Durable summary in auto-memory
(`cp-look-root-cause`).
