# COrigami tree → finished model pipeline (`mcp_harness/corigami/`)

> **2026-10-07:** this pipeline is now **Pleatwright**, package `mcp_harness/pleatwright/`
> (see `docs/superpowers/specs/2026-10-07-pleatwright-retire-treemaker-design.md`).
> The body below is the record as written on 2026-10-06.

**Goal (owner, 2026-10-06).** Replicate COrigami's tree-to-finished-model
pipeline (arXiv:2606.26299, §3.2–3.7 + App. D–H) and run it on the 51 trees of
the "Bases in Triplicate III" artifact, producing a sample folder in the exact
layout of COrigami's released `origami_samples/`:

```
<name>_<grid>/packing_cp.svg  solving_cp.svg  shaping_cp.svg  overview.png
```

Inputs are ONLY the artifact's trees (owner instruction): topology/lengths in
`fixtures/full17_v3_trees/` (commit ad37b82), plus the authored 3-D stick
directions recovered from the same run's `state.json`
(`fixtures/full17_v3_sticks/`, verified node-for-node identical).

## Stages

| § | stage | module | what it does |
|---|---|---|---|
| 3.1 | stick figure | `stick.py` | authored nodes → sticks with integer grid length, azimuth/elevation; degree-2 joints contracted into chains for packing (App. C.2) |
| 3.2, E | packing | `pack.py` | grid from the E.1 heuristic upward; first river spans the full width, later rivers wall-follow (parallel bands → slab pockets); pockets tiled by symmetric rows of flap rectangles; tiling by flap expansion (ridge-direction growth, width growth at depth L, virtual hinge past the paper edge) |
| — | collapsed base | `base.py` | analytic folded state: each point → strip position `s = strip(u) + σ·d∞`, across-strip `w = tri(x or y)`; isometry + continuity checked on every cell quarter; creases read off as reflections; classified hinge / ridge / pleat |
| 3.3, D, F | solving | `solve.py` | F.2 pleat interleaving, F.3 ridge anchors + propagation, greedy hinge assignment scored by App. D's crimp test (Alg. 1, ported); global flat-foldability by the repo's SAT layer-order stage, phase-seeded with the heuristic labels |
| 3.5, G.2 | narrowing | `narrow.py` | Fig. 13(d) template as a piecewise isometry of the folded strip (the clip pattern algorithm: projected per layer, M/V swapped on face-down layers, clipped per face) |
| 3.6, G.1 | tree shaping | `shape.py` | BFS from the root stick; per stick the unique simple fold with axis in the parent's paper plane; cut restricted to the stick's subtree |
| 3.6, 3.8 | orchestration | `orchestrate.py` | single-step LLM tool-call proposals + VLM single-model judge + §3.6 reward, used as best-of-K selection over the tree-shaping baseline |
| 3.7, H | folding | `fold.py` | port of COrigami's own visualiser (`app.js`): PSLG faces, BFS 4×4 transforms, vertex averaging, mean axial strain |
| — | output | `render.py`, `pipeline.py` | overview in Fig. 4's layout; SVGs in the released format (stroke = assignment, opacity = fold fraction, pleats carry `elevation`) |

## Prior art used (CLAUDE.md §0)

| source | taken | rejected / changed, and why |
|---|---|---|
| COrigami paper §3, App. C–I | the whole stage structure, E.1 grid heuristic, F.1–F.3 solving steps, Alg. 1 crimp test, G.1 simple-fold rule, Fig. 13(d) template, H folding algorithm, App. I judge structure, §3.6 reward | RL fine-tuning of Gemini: not reproducible here → the same generation step at inference time + the VLM reward as a selection criterion (the paper's other documented use of the score) |
| COrigami Visualiser (`serve-dot-zipline…/app.js`, public) | exact SVG semantics (`foldAngle = ±180 × opacity`, B/M/V/F precedence, collinear splitting), the BFS folder, strain metric — ported line for line into `fold.py` / `cp.py` | — |
| COrigami released samples (`~/Desktop/origami_samples`) | folder/file layout; measured fact that a solved base collapses to a strip ONE grid unit wide (Ram: 1 × 16 units), which fixed the dense-pleat construction | — |
| this repo's `box_pleat/` (Lang Ch.13 compiler) | `sat_order` + `layer_certify` + `flat_fold` for global certification; `cp_audit.arrangement_ok_at_vertex` as an independent oracle for the crimp port (256/256 agree) | its packer/contours/assign path: measured on the 51 artifact trees it emits 7/51 (31 hit a 300 s cap) — evidence `docs/superpowers/evidence/2026-10-06-corigami-pipeline/` |
| this repo's fold-and-reflect engine (memory) | "the cut line passes through the hinge end opposite the turn" (no tear at the joint) | it shapes TreeMaker bases; COrigami's are box-pleated strips |

## Deviations from the paper, each forced and recorded

1. **Pocket tiling family.** The paper's packer snakes rivers by wall-following
   around arbitrary obstacles. Ours nests them. A path-shaped hub graph (all 51
   artifact trees, measured) gets parallel full-width bands, which is exactly
   the wall-following result for a chain. A branching one (first seen
   2026-10-10: a moose whose head carried forked antlers) is packed by
   `pleatwright/nest.py`: each child hub's river is the L-infinity offset band
   around its own rectangle, and a mirrored pair of hub subtrees shares a strip
   split at x = N/2 (spec `2026-10-10-branching-hub-packer-design.md`). Rivers
   still never bend around flaps, so a long thin branch costs a full-width
   strip; three of the 109 named branching edits exceed the pipeline's grid cap
   for that reason (evidence `2026-10-10-branching-packer/`).
2. **Crimp fallback in tree shaping.** G.1's unique fold line has
   cot α = t_y / (σ − t_x); for small in-plane deflections it runs along the
   strip past the stick's end and tears the next stick. The crimp (fold back
   flat, then one oblique fold, cot α = t_y / (σ + t_x)) always fits: the
   product of the two cotangents is t_y² / (1 − t_x²) ≤ 1. Single fold is used
   whenever it fits.
3. **Fold lines sit 0.4 units past the joint** and end 0.1 before the next:
   lines on integer contours run through grid vertices / ridge corners and
   produced degenerate vertices (19 → 2 failing per model, measured on
   bird_1).
4. **180° fold sense** is chosen greedily per fold to maximise shaping-CP
   flat-foldability (both senses give identical geometry).
5. **Certified labels replace the heuristic labels** when the SAT certificate
   exists; the record keeps how many it changed.
6. **The LLM/VLM key in `.env` is dead** (401, 2026-10-06), so every served
   model uses the paper's algorithmic orchestration (tree shaping); the
   `orchestrator` field of each record says so.
7. **Packing ladder** (`packing_rung` in each record): mirror-symmetric rows
   first; then unmirrored rows, needed when declared pairs have unequal
   lengths (starfish_0) or when an ODD river length puts the hinges on its
   two sides on opposite parities, which symmetric rows of the same hub
   structure cannot both meet (dog_2: heads 6 and tails 8 fix both slabs'
   column parity); last, all lengths doubled (exact, every river even).
8. **Global certification has a size guard** (`sat_order`'s raw-triple bound
   and streaming clause cap). Past it the solver still guarantees LOCAL
   flat-foldability exactly: every crimp-failing M/V combination at every
   vertex becomes a clause (`solve.local_sat`); the verdict reads
   `OVERSIZE+LOCAL_SAT`, never CERTIFIED.
9. **Chains are rooted at a hub**, so a chain through a degree-2 authored root
   traverses a stick end→start; its target direction is reversed
   (`shape.chain_dirs`). Before this fix guinea_pig_1 read similarity 0.49.
10. **Pairs are recovered by L/R name** when the declared pairs name nodes the
    authored tree lacks (octopus_0 pairs `arm*_tip_*`, its leaves are
    `arm*_base_*`).

## Verification

* crimp port vs `cp_audit.arrangement_ok_at_vertex`: 256/256 labellings agree;
* the folder port closes COrigami's own Ram `shaping_cp.svg` to 2.7e-7;
* every base is checked for exact isometry and continuity on all cell
  quarter-triangles before solving;
* our `shaping_cp.svg` files load in COrigami's own Visualiser (served
  locally) and fold at 0.0000% strain;
* `mcp_harness/tests/test_corigami_pipeline.py` (11 tests, ~20 s).
