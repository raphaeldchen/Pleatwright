# Auto-Constant Selection for mesh → tree

**Date:** 2026-06-23
**Status:** Design approved, pending implementation plan
**Component:** `mcp_harness/mesh_to_tree.py` (the reference-mesh → Metric Tree path)

## Problem

`mesh_to_tree.py` extracts an abstract Metric Tree from a provided 3D mesh, but the
two empirical constants that govern the extraction —

- `VOXEL_RES` (remesh resolution → topology fidelity), and
- `PRUNE_FRACTION` (twig pruning → flap count)

— are **hand-tuned per body plan** (humanoid 0.25, quadruped 0.60, fish 64-res,
etc.). A novel mesh with no pre-tuned constants will not reliably land in the
packable leaf-count window. This blocks any path that supplies arbitrary meshes
(notably a future text → mesh front-end), because nobody is there to tune.

## Goal

Replace per-body-plan hand tuning with a **closed-loop search** that takes *any*
mesh and finds constants yielding a packable Metric Tree — or returns a clearly
labeled best effort. No new ML model: the search reuses the existing Tier 2.5
feasibility gate as its fast fitness function.

Non-goals (explicitly out of scope for this spec):

- The text → mesh front-end (a separate, later spec).
- Closing the world-model data loop (we leave a capture *hook*, build nothing).
- Changing any of the five existing extraction stages.

## Architecture

One new orchestration function layered on top of the five existing pure stages,
which are **untouched**. The manual `mesh_to_metric_tree` stays for tests and
explicit control.

```
auto_mesh_to_metric_tree(path, *, gate=DEFAULT, compile_fn=DEFAULT) -> MeshTreeResult
    for voxel_res in VOXEL_GRID:                # outer, EXPENSIVE — escalate only on failure
        mesh = load_mesh(path, voxel_res)
        skel = extract_skeleton(mesh)           # paid ONCE per voxel_res
        feasible = []
        for prune in PRUNE_GRID:                # inner, CHEAP — reuses cached skel
            tree = simplify_to_tree(skel, prune)
            nodes, pairs = to_metric_tree(tree, detect_symmetry(tree, mesh))
            if not structural_prefilter(nodes):  # leaf-count window + root not overloaded
                continue
            verdict = gate.predict(nodes, pairs) # {verdict, p_pack, ood, ...}
            if verdict["verdict"] != "infeasible":   # NOT confidently rejected
                feasible.append((verdict, nodes, pairs, prune))
        for verdict, nodes, pairs, prune in rank(feasible)[:K]:   # only gate-blessed trees compile
            if compiles_to_fold(nodes, pairs, compile_fn):
                return MeshTreeResult(confirmed=True, ...)
    # nothing packed anywhere across the whole search:
    return MeshTreeResult(confirmed=False, best_effort=highest_p_pack_overall, trace=...)
```

### Why this stage ordering

The five stages have very different costs:

- `load_mesh` + `extract_skeleton` are **expensive** (voxelize → contract →
  skeletonize) and depend on `voxel_res`.
- `simplify_to_tree` is **cheap** and is the *only* stage `prune_fraction` touches.

So the skeleton is computed once per `voxel_res` (outer loop) and `prune_fraction`
is swept almost for free (inner loop). The expensive `voxel_res` axis is escalated
only when the entire cheap prune sweep fails.

### Components

| Unit | Purpose | Depends on |
|------|---------|------------|
| `auto_mesh_to_metric_tree` | orchestrate the search; return `MeshTreeResult` | the five stages, gate, compile_fn |
| `structural_prefilter(nodes)` | cheap reject on emitted Metric Tree nodes before paying for gate/compile | nothing (pure graph check) |
| `rank(feasible)` | order the feasible set for compilation | nothing (pure sort) |
| `MeshTreeResult` | always-returned result contract | — |

Dependency injection (`gate`, `compile_fn` params with real defaults) lets tests
exercise the orchestration logic without the real engine.

## The gate as a filter, not just a ranker

`feasibility/gate.py::Gate.predict(nodes, pairs)` returns one of three verdicts:

- `"infeasible"` — `p_pack` below the block threshold. **This is the confident
  rejection.** Excluded from compilation.
- `"feasible"` — in-distribution and above threshold. A compile candidate.
- `"compile_anyway"` — **OOD** (novel tree). The gate explicitly defers: "compile
  and log for retraining." *Not* a rejection — stays eligible.

So the feasible set = verdicts ∈ {`feasible`, `compile_anyway`}. A compile only ever
runs on a tree the gate did not confidently reject — the Tier 2.5 "shielded
compiler" principle applied to the mesh front-end.

Selection per `voxel_res`:

- `> K` feasible → compile the top `K`.
- `1..K` feasible → compile exactly those.
- `0` feasible → compile **nothing**, escalate `voxel_res`.

## Search grids

Engineering defaults; tunable as module constants.

- `PRUNE_GRID = [0.20, 0.30, 0.40, 0.50, 0.60, 0.70]` — covers all current
  hand-tuned values (0.25–0.60). Cheap, so the grid can be generous.
- `VOXEL_GRID = [96, 64, 128]` — tried in order, escalate only on failure. 96 is
  the common-good default; 64 for compact/blobby meshes (fish needed it); 128 to
  preserve fine spines. Capped at 3 to bound the expensive outer loop.
- `K = 2` — max compiles attempted per `voxel_res`.

`structural_prefilter` thresholds (from existing tests):

- leaf count ∈ `[4, 8]`
- root children `≤ 4` (the `POLYS_MULTIPLE_IBPS` overloaded-root guard)

## Ranking within the feasible set

Two-key sort:

1. `feasible` ranked above `compile_anyway` — prefer in-distribution gate-blessed
   trees over OOD unknowns (whose `p_pack` is unreliable out of distribution).
2. then `p_pack` descending.

## Result contract

`MeshTreeResult` is **always** returned — never raises, consistent with the
existing `server.draft_and_compile_full_base` return-value error convention.

| field | meaning |
|-------|---------|
| `confirmed` | `True` = FOLD-verified; `False` = best-effort, nothing packed |
| `nodes`, `pairs` | the chosen Metric Tree |
| `voxel_res`, `prune_fraction` | the winning constants |
| `gate` | the verdict dict (`verdict`, `p_pack`, `ood`, …) for the chosen tree |
| `trace` | per-attempt log: `(voxel_res, prune, leaf_count, verdict, p_pack, compiled?)` |

The explicit `confirmed` flag is the safety guarantee: an unconfirmed best-effort
tree is clearly labeled and cannot be mistaken for a verified one. If zero trees
are feasible across the *entire* search, no compile ever runs and `best_effort` is
the highest-`p_pack` tree seen (least-bad), still marked `confirmed=False` — the
contract stays total without ever compiling a rejected tree.

## Determinism

Grids are fixed and the existing seeds (`SKELETOR_SEED`, the `np.random.seed` in
`extract_skeleton`) are untouched, so the same mesh always yields the same
`MeshTreeResult`.

## Data-loop hook (not built)

Every OOD (`compile_anyway`) tree the loop compiles produces a real pack/no-pack
outcome — exactly the labeled data the parked world-model data-loop concern needs.
The `trace` is the natural capture point. This spec leaves the hook and builds no
capture, to stay focused.

## Testing strategy

Two tiers, enabled by dependency injection.

### Fast unit tests (no engine, stubbed gate/compile)

- `structural_prefilter`: synthetic trees — leaf count below/in/above `[4,8]`;
  root with 4 vs. 5 children → assert accept/reject.
- `rank`: a feasible list mixing `feasible`/`compile_anyway` at various `p_pack` →
  assert `feasible` sorts ahead of `compile_anyway`, then `p_pack` descending.
- Gate-as-filter: stub gate → all `infeasible` → assert **zero** compiles attempted.
- Failure contract: stub so nothing packs → assert `confirmed=False`,
  `best_effort` populated, `trace` non-empty.
- Escalation: stub so `voxel_res=96` yields nothing but `64` succeeds → assert it
  escalated and the result records `voxel_res=64`.

### Real end-to-end integration (headline validation)

- Run the real `auto_mesh_to_metric_tree` on all 5 fixtures → assert
  `confirmed=True` and the chosen tree lands in the same leaf/pair expectations the
  hand-tuned constants produced. This proves auto-selection rediscovers good
  constants with no per-body-plan tuning. Cost stays bounded — skeleton computed
  once per `voxel_res` (96 should win for all 5), cheap prune sweep, gate shields
  down to ~1 compile each.
- Determinism: run one fixture twice → assert identical `MeshTreeResult`.
