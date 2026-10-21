# 3D Mesh → Metric Tree (Proof of Concept) — Design

**Date:** 2026-06-16
**Status:** Approved (design); pending implementation plan
**Scope:** A standalone proof-of-concept that turns a provided 3D mesh into a
Metric Tree (the abstract "stick figure" the rest of the system compiles), so the
AI can derive limb topology and proportions from a real reference instead of
guessing them from text. Validated against the four body-plan templates we
already measured. **Out of scope:** 3D generation, UI, agent/MCP wiring — all
deferred to later slices.

## Motivation

The AI currently drafts Metric Trees from a text description, guessing both the
**anatomy** (how many flaps, what proportions) and stumbling into the
**packability** knife-edge. Recent sessions patched packability (auto
perturb-and-retry, hand-made body-plan templates in `agent_loop.py`). But the
templates are a crutch on the *anatomy* side: they hard-code proportions and do
not generalize beyond four body plans.

The intended architecture (CLAUDE.md Steps 1–2) gives the AI a *reference* to
measure. This POC validates the riskiest assumption on that path: **can we turn a
real 3D mesh into a foldable Metric Tree at all?** It does so for a *provided*
mesh, deferring 3D generation (the heavy, swappable external dependency).

Crucially, anatomy and packability are **orthogonal**. A reference fixes anatomy;
it does not fix packability (a reality-measured tree is, if anything, harder to
pack). So this POC produces the same `(tree_nodes, symmetric_pairs)` the agent
already emits and feeds it into the existing compile → perturb-and-retry → lint →
free-paper path unchanged. It inherits all packability robustness already built.

## Pipeline decomposition

The full vision is four subsystems:

```
[A] Acquire a 3D mesh        -- text-to-3D generation OR import   (DEFERRED)
[B] Extract a skeleton       -- mesh -> joints + extremities + lengths   (NEW, this POC)
[C] Map skeleton -> tree     -- topology + proportional lengths + symmetry (NEW, this POC)
[D] Compile -> lint -> fold   -- ALREADY BUILT
```

This POC is **B + C on a provided mesh, validated through the existing D**.

## Key simplification

The Metric Tree is **abstract** — topology + proportional edge lengths, no
coordinates. TreeMaker does its own 2D layout. So we never project 3D → 2D. We
extract only: (a) tree **topology** (which tips connect through which junctions),
(b) **proportional bone lengths**, (c) **left/right symmetry pairs**. The 3D mesh
is a measurement source, nothing more.

## Architecture & components

A standalone Python module `mcp_harness/mesh_to_tree.py` (demo `__main__` + a
test + committed `fixtures/`). **Not** wired into the agent/MCP — the POC proves
the chain; integration is a later slice. Six focused, independently-testable
functions:

```
load_mesh(path)              -> trimesh.Trimesh        # load + light cleanup
extract_skeleton(mesh)       -> nx.Graph (3D nodes)    # skeletor mesh-contraction
simplify_to_tree(skel)       -> nx.Graph               # prune twigs, contract chains
detect_symmetry(tree, mesh)  -> [(leafA, leafB), ...]  # mirror-plane pairing
to_metric_tree(tree, sym)    -> (nodes_json, pairs)    # root, order, normalize lengths
mesh_to_metric_tree(path)    -> (nodes, pairs)         # orchestrates the above
```

### Data flow

```
fixtures/<plan>.glb
  -> load_mesh           -> watertight-ish trimesh
  -> extract_skeleton    -> noisy curve-skeleton graph (hundreds of nodes)
  -> simplify_to_tree    -> small topological tree (tips + junctions, edge = bone length)
  -> detect_symmetry     -> left/right limb pairs
  -> to_metric_tree      -> Metric Tree JSON + symmetric_pairs   <- OUR existing format
  -> server.draft_and_compile_full_base(...)   [EXISTING D]      -> FOLD
  -> validate_flat_foldability(FOLD)           [EXISTING]        -> Pass / frontier
```

### Approach for Stage B (chosen)

**Curve-skeleton library (`skeletor`)**: mesh contraction → skeleton graph with
3D node positions, giving extremities *and* junction topology for free, which we
contract into the small tree we need. Chosen over a custom geodesic-extremity
heuristic (which would make us rebuild junction recovery from scratch) and over an
ML auto-rigger (RigNet — PyTorch/weights/GPU, overkill, not reproducible). If
`skeletor` quality disappoints on a curated CC0 mesh, the geodesic heuristic is
the documented fallback.

## The four judgment calls (where the risk lives)

1. **Twig pruning.** Skeletonization sprays spurious short branches. After
   contracting degree-2 chains, iteratively prune any leaf whose branch length
   < ~10–15% of the longest branch, until stable. The threshold is the most
   likely thing to need tuning; keep it a named per-fixture constant and report
   leaf count before/after.
2. **Root selection.** TreeMaker's root must be a central body node, not a tip.
   Pick the interior (branch) node of minimum eccentricity (graph center),
   re-root, and emit nodes parent-before-child (BFS) since `build_tree_from_json`
   requires parents to precede children.
3. **Symmetry detection.** Find the bilateral mirror plane via PCA (normal to the
   minor lateral axis through the centroid); pair leaf nodes whose 3D positions
   reflect onto each other within tolerance. Fallback: pair leaves by matching
   distance-from-root and opposite lateral sign. Symmetry is what makes the tree
   pack, so this matters.
4. **Length normalization (packability bridge).** Scale all edges so the longest
   limb ≈ 0.4 (the template regime we measured), preserving *relative*
   proportions (the anatomical point). The tree then enters the existing compile
   path; a knife-edge miss is cleared by the already-built perturb-and-retry.

## Error handling

Each stage fails loud with a clear message (bad/unreadable mesh, skeleton too
sparse, no symmetry plane found). A tree that **compiles but hits the free-paper
frontier is success, not failure** — consistent with the rest of the system.

## Test meshes & success criteria

Source one CC0 mesh for each of the four body plans we templated — **quadruped,
bird, humanoid, insect** — committed as fixtures. The hand-made templates in
`agent_loop.py` are the ground-truth yardstick.

Success has **two separable dimensions per body plan:**

| Dimension | Checks | Yardstick |
|---|---|---|
| Extraction faithfulness | right flap count + hub structure for that body plan | the matching template (e.g. quadruped mesh → ~6 leaves, two hubs) |
| Packability | extracted tree compiles to a foldable base | existing compile → perturb → lint path |

**Expected outcomes:** all five body plans → *both* dimensions pass.
**Insect** was originally expected to hit the TreeMaker fragile-edge wall (the
hand-made insect *template* packs 0% under jitter), but `auto_mesh_to_metric_tree`
rediscovers a packable extraction: as of the 2026-06-24 live verification it
confirms a foldable insect at (voxel_res 96, prune 0.55), 6 leaves / 3 bilateral
pairs. The closed-loop search finds packable proportions the single hand template
did not — so insect is now expected-pass, pinned by
test_auto_selection_confirms_each_body_plan. See the 2026-06-24 hardening spec.

Headline deliverable: a small table — for each of the 4 body plans, extracted leaf
count vs. template, hubs vs. template, and compile outcome — mirroring
`benchmark_templates.py`'s framing.

## Testing

A test runs `mesh_to_metric_tree(fixture)` for each fixture and asserts:
(a) leaf count is anatomically plausible for the body plan (compared to the
template's leaf count), (b) symmetry pairs are found, (c) the result is a valid
Metric Tree that compiles. Compilation goes through the realistic path
`server.draft_and_compile_full_base` (spawn-isolated, includes perturb-and-retry)
— the same path the agent uses — not the no-perturb `runner.compile_tree`. For
the three robust plans, assert a non-`ERROR` FOLD; for insect, assert faithful
extraction and record the compile outcome without requiring success. Pin
`skeletor` randomness with a fixed seed; assert structural properties, not exact
coordinates.

## Dependencies

New, into the venv: `trimesh`, `skeletor`, `networkx`, `scipy`, `numpy`. Standard,
pip-installable, CPU-only. This is the heaviest part of the POC's footprint and a
real cost to weigh.

## Explicitly out of scope (YAGNI)

- 3D generation (text-to-3D) — deferred slice.
- UI / viewport.
- Anatomical naming ("which leaf is the head") — structure suffices.
- Agent / MCP-tool wiring — the POC is a standalone script + test.
- Multi-mesh robustness *beyond* the four chosen fixtures; per-fixture threshold
  tuning is acceptable.
