# Stage 1 (mesh fidelity) — session handoff, 2026-07-19

**Charter:** roadmap §Stage 1 (`2026-07-18-cp-root-cause-and-specificity-roadmap.md`) —
"prompt → THIS animal's tree". All five work items shipped; suite green (1360 passed,
10 skipped); live acceptance passed. Branch `claude/stage1-mesh-fidelity-f79dc2`.

## What shipped (per item, with the load-bearing decisions)

### 1.1 — hf interactive default + hardened HF path + capture on
- **Where the default lives:** `web/serve_env.py::apply_interactive_env_defaults` —
  `setdefault(MESH_PROVIDER=hf)` + `setdefault(IDE_CAPTURE_PATH=<mcp_harness>/feasibility/captured.jsonl)`,
  called by `web/server.py` after `load_env()` and **before `import agent_loop`** (the MCP
  child env `_SERVERS` is snapshotted at import — a later call never reaches the children).
  Code default stays `fake` (C-8 pin); `.env` and shell exports override (setdefault).
- **The child boundary:** `_mcp_child_env` (agent_loop.py) now forwards a pass-through
  allowlist (MESH_PROVIDER, MESH_OUTPUT_DIR, IDE_CAPTURE_PATH, HF_SPACE_ID, HF_API_NAME,
  HF_TOKEN, MESHY_API_KEY, FEASIBILITY_GATE_PATH) when set — previously the sanitized
  safelist silently dropped all of them, which is why "export MESH_PROVIDER=hf" never worked.
- **HF hardening:** bounded retries (3 attempts, 10s/30s backoff, injectable sleep) for
  transient failures (cold start/queue/connect); quota errors fail FAST with
  wait-or-set-HF_TOKEN guidance; unreachable-space errors name the space URL and the
  `MESH_PROVIDER=fake` offline fallback; httpx connect timeout 30s with **unlimited read**
  (Shap-E + ZeroGPU queue legitimately take minutes — an aggressive read timeout would kill
  the generation mid-stream).
- **Main-checkout `.env`:** line 12 `MESH_PROVIDER=fake` commented out (backup at
  `.env.bak-stage1`) so the serve default actually applies for the user.
- **BONUS ROOT-CAUSE FIX:** serve-time capture was dead since PR #10 —
  `feasibility/tree_labeler.py` imported the **tests-only** `runner` module at module top, so
  outside the pytest harness `capture.record`'s lazy import died and every row was silently
  dropped (`[capture] dropped one row: No module named 'runner'`, observed live). Fixed with
  lazy imports; regression test simulates the serve import environment. 5 mesh-path rows
  accrued live after the fix.

### 1.2 — bird ≠ quadruped template
New bird weights **wings 0.4 / legs 0.25 / head 0.3 / tail 0.35** (hubs 0.3, node order
UNCHANGED — knife-edge rule). Chosen by a 7-candidate live pack probe: this set packs
**exactly** (no nudge). Notable probe result: changing ONLY the wings to 0.4 (a strictly
smaller change) needs an *asymmetric* nudge — packability is non-monotonic in weights; never
reweigh templates without re-probing. `tests/test_template_distinctness.py` parses the
SYSTEM_PROMPT template numbers and compares them to `benchmark_templates.py` structurally,
so the copies cannot silently desync again, plus a real-compile distinctness pin.

### 1.3 — heuristic anatomy labels
`label_leaves` (mesh_to_tree.py) computes per-leaf labels where geometry still exists,
captured per candidate keyed `(voxel_res, prune)` (the tree graph is a loop variable);
`MeshTreeResult.leaf_labels` (defaulted). Vocabulary: `likely head` / `likely tail` /
`{left|right} {fore|hind} limb (pair N)` / `axial extremity (head or tail)` /
`unpaired limb (mirror twin possibly lost in extraction)` / `mid-body appendage` — every
basis string states its heuristic and hedges (head/tail via elevation tie-break; fore-limbs
may be wings). Labeling failures degrade to None, never break extraction.

### 1.4 — fidelity-aware two-phase ranking
- **R** = leaf count with the **widest plateau** across the prune sweep, counts below
  MIN_LEAVES excluded, ties → higher count → lower min-prune. Calibrated against recorded
  real curves (all 5 fixtures + the cached HF dog, `tests/test_fidelity_rank.py` pins them):
  noise spikes all have width 1; **hf_dog reads R=6 at voxel 96 AND 64**; fish reads R=10 →
  `R_eff = clamp(R, 4, 8)` in `fidelity_score` (distance-normalized, so an 8-leaf monster
  cannot beat a 5-leaf tree when R=5 — the wrong-easy-answer guard).
- **Queue** = `dedup( rank_by_fidelity(feasible,R)[:FIDELITY_K1=2] ++ rank(feasible)[:SEARCH_K=4] )`,
  first FOLD wins. Verdict priority stays primary in BOTH rankers (never OOD before
  in-distribution). Phase 2 is byte-for-byte today's queue → the compiled set is a strict
  superset → the measured rank-4 packable quadruped/humanoid candidates cannot be lost.
  Content-dedup matters: adjacent prunes emit identical trees (the dog's six 6-leaf
  candidates collapse to one compile).
- Gate/p_pack untouched (separation constraint; Stage 2.4 unaffected). FIDELITY_K1 is
  documented as a bridge constant with a retirement criterion.

### 1.5 — A-9 fill wiring + shared perturb ladder
- Report renders `Anatomy fidelity:` and, on deficit, `MISSING FEATURES -- repair plan`
  (missing_count + recipe: compile base → find_free_paper → one HITL
  suggest_flap_for_region proposal per feature, bilateral = region+mirror_region with both
  locations stated, shortfall pre-reporting, explicit `unfillable` terminal verdict).
- SYSTEM_PROMPT section "MISSING FEATURES -- REPAIR BEFORE ANY POSING": fills are
  measured-anatomy repair (still HITL, one re-proposal cap), **fills BEFORE any
  shaping/posing** (a fill recompile renumbers vertices and invalidates pose recipes), and
  after `status:"filled"` the result's `tree_nodes ARE the canonical tree`.
- **Pairs-blind jitter fixed:** `_worker_compile_and_regions` (fill/shaping/pose path)
  previously jittered bilateral pairs independently and unannotated. One shared
  `_perturb_ladder` now feeds both compile paths: symmetric-first, then the annotated
  independent fallback reproducing the legacy seed-0 draw sequence (no historical rescue
  lost; pairless trees byte-identical to before — pinned).

## Live acceptance evidence (2026-07-19)

| prompt | time | tree | provenance |
|---|---|---|---|
| "a dog" | 61s (cached mesh) | 5 leaves, 1 pair, differentiated lengths | voxel 64 / prune 0.6, sha `36f4aec6…`, 874,640B |
| "a deer" | 43s (fresh HF gen) | **6 leaves, 2 pairs**, 10 nodes | voxel 96 / prune 0.4, sha `62501429…`, 752,240B |
| "a crane bird" | 9s (fresh HF gen) | 5 leaves, 1 pair, long-neck lengths | voxel 96 / prune 0.2, sha `ca8680d8…`, 400,548B |

All three pairwise distinct (tree structure AND byte-level fold). Forced-failure probe
(bogus HF_SPACE_ID): `ERROR: … looks unreachable or down after 3 attempts …` naming the
space URL and the `MESH_PROVIDER=fake` fallback — through the real serve surface.

**The dog's 6th feature, resolved honestly:** the search trace shows phase-1 compiled the
6-leaf candidates FIRST at voxel 96 (p_pack 0.40, fid 1.00 → `compiled=False`) and voxel 64
(p_pack 0.36, fid 1.00 → `compiled=False`); only then did the 5-leaf prune-0.6 tree win
(p_pack 0.77, fid 0.83). The deficit is an **engine packing limit, not a ranking artifact**,
and now ships as a MISSING FEATURES repair plan (A-9 fill = the designed restoration path)
instead of silence. The prune cap itself is vindicated: prune 0.6 is the only setting that
yields the packable 5-leaf tree; lower prunes preserve the 6th feature but do not pack.

**Stage-2 interactions recorded (NOT fixed here, per charter):** all three live compiles
needed the ±10% nudge (all rescued symmetrically — the ladder held). Strained-CP interior
violations on nudged mesh compiles remain Stage 2.1/2.2's charter.

## Operational notes for the next session
- Worktree provisioning recipe (a fresh worktree has no runtime artifacts): symlink
  `mcp_harness/.venv` → main's, copy `headless_treemaker.cpython-314-darwin.so`,
  `feasibility/gate.joblib`, `oriedita/oriedita-1.1.3.jar`, `OrieditaValidator.class`.
- Mesh caches are per-checkout (`mcp_harness/generated_meshes/<sha256(provider:prompt)>/`).
  This worktree now holds the genuine dog/deer/crane HF meshes — copy them forward; the
  cache key ignores provider config, so a changed HF_SPACE_ID reuses old bytes (known,
  documented, unaddressed).
- Design-panel artifacts (judged designs for 1.4/1.5) live in the session workflow outputs;
  the losing-but-grafted ideas (dropped-twig attach-id telemetry, server-side fill_plan
  tool) are the natural Stage-2/3 hardening steps.
- The 2 failed design agents (StructuredOutput retry cap) mean the 1.4 judgment was a
  field of one — mitigated by three independent judges finding no disqualifying flaw and
  by the calibration probe defusing their one near-fatal concern on real data.

## Next (per roadmap sequencing)
Stage 2.1 (lint verdict split: benign hull-frontier vs real interior violations) is now the
bottleneck for everything downstream — the live HF-path compiles all ship nudged and the
repair loop cannot exist without the split. Then 2.2 (consume the "did not pack exactly"
annotation). Stage 0.5 (default pose) still gated on platform chips h-f1/h-f2 + B4.
