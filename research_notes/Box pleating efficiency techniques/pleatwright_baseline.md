# Pleatwright baseline: how a tree becomes a box-pleated base today, and what efficiency it achieves

Scope: a local code study of the worktree `claude/box-pleating-efficiency-research-21f027` (HEAD 63c838a2, clean), plus three cheap offline packing probes over the 51 artifact trees in `mcp_harness/fixtures/full17_v3_sticks/` (owner rule respected: only those trees, no tardigrade / water bear). Sources below are repo paths, relative to the worktree root `<repo>/`. Line numbers refer to HEAD 63c838a2.

Probe artefacts (scratchpad only; nothing was written to the repo except this file). `S` is `<scratch>/75077ba1-6565-424b-a575-a2861d01c57e/scratchpad`:
- `$S/bp_efficiency_probe.py` reproduces `pipeline._run`'s packing ladder (pack, then `base.build`, with no solve or shape) and measures the accepted layout. The output is `$S/bp_eff.jsonl`.
- `$S/rung_probe.py` runs ONE ladder rung on its own: the first certified N for that rung, using the pipeline's own `n_max` and 400-candidate cap. The outputs are `$S/rung_asym.jsonl` and `$S/rung_x2.jsonl`.
- `$S/summ.py` summarises the results and computes a TreeMaker scale ratio.
- Commands, run from the worktree's `mcp_harness/` with interpreter `P=<repo>/mcp_harness/.venv/bin/python`. The worktree has no `.venv` of its own; the main checkout's venv imports the worktree's `pleatwright` because cwd is on `sys.path`.
  - `$P $S/bp_efficiency_probe.py $S/bp_eff.jsonl`: 51 trees in about 30 s.
  - `$P $S/rung_probe.py $S/rung_asym.jsonl asymmetric 1.0 0 400`
  - `$P $S/rung_probe.py $S/rung_x2.jsonl x2 2.0 1 200`
  - `$P $S/summ.py $S`
- Check: all 51 grid sizes from `bp_efficiency_probe` equal the committed records exactly (an `assert` in `summ.py` passed). The 2026-10-10 byte-identity gate also reports the outputs unchanged since 2026-10-06 ("51 folders, 204 identical, 0 different"; [evidence README](docs/superpowers/evidence/2026-10-10-branching-packer/README.md)).

---

## 1. Packing model: flaps, rivers, grid size, ladder, nesting, optimality

### Takeaway
Pleatwright packs a *contracted* tree on an N×N integer grid:
- **Flaps.** Each leaf chain is an axis-aligned rectangular "column" region. Its elevation is the L∞ distance to that region's hinge lines, and it must reach exactly L.
- **Rivers.** Each hub-to-hub chain is a full-width horizontal band of width W (path-shaped hub graphs). Branching hub graphs use nested L∞ offset bands instead.
- **Search.** N is swept upward in steps of 2 from the App. E.1 heuristic `G_init`. The first layout `base.build` certifies is kept.

The search is a first-fit over a narrow, enumerated family of layouts (rows of columns in horizontal slabs, capped enumeration). It is not an optimiser. It accepted the very first candidate on all 51 trees.

### Cited Findings
- **Tree → chains.** `stick.contract` merges degree-2 joints into `Chain`s. A leaf chain is a *flap*; a hub-to-hub chain is a *river*. The packing root is the authored root if it is a hub, else the nearest hub. Integer lengths come from `round_half_up(length*scale)`, never below 1. — [mcp_harness/pleatwright/stick.py:108-243](mcp_harness/pleatwright/stick.py)
- **Default scale is 1.0.** `pipeline.run` uses `scale=1.0`, and all 51 artifact sticks have integer lengths (probe: zero non-integers), so at the first two rungs grid lengths equal authored lengths. — [mcp_harness/pleatwright/pipeline.py:214-260](mcp_harness/pleatwright/pipeline.py)
- **Packing model (module docstring).** "Every grid cell belongs to one contracted tree edge (a *flap* = leaf chain, or a *river* = hub-to-hub chain). Within an edge's region the elevation d(p) is the L-infinity distance from p to that region's hinge lines; a flap of length L must reach d = L and never exceed it, a river of length W is a band of L-infinity width W." — [mcp_harness/pleatwright/pack.py:1-31](mcp_harness/pleatwright/pack.py)
- **Data structures.** `Region(chain, rect, vlines, hlines, kind, L, u_line, virtual, more)`. Hinge lines may be *virtual*, i.e. outside the paper; the raw edge then sits at elevation δ>0, "as in COrigami's Avocet". `Layout(N, regions, hub_order, bands, slabs, score, pockets)`. — [pack.py:41-67](mcp_harness/pleatwright/pack.py)
- **Grid size.**
  - `grid_init` = max(ceil(sqrt(area)), D), rounded up to even when there are pairs, where D is the longest leaf-to-leaf path.
  - The area term counts the 4 largest flaps as L² (corner flaps) and every other flap as 2L² (edge flaps). A river counts max(W·m, W²) if all its neighbours are leaves, else W².
  - Sources: [pack.py:70-112](mcp_harness/pleatwright/pack.py), COrigami App. E.1 per [spec 2026-10-06](docs/superpowers/specs/2026-10-06-corigami-tree-to-model-pipeline.md).
  - `candidates()` then steps N over even values from G up to `N_max`. — [pack.py:724-827](mcp_harness/pleatwright/pack.py)
- **Path-shaped hub graph (all 51 artifact trees).**
  - Hubs are ordered along the path (`hub_path`), in both orientations.
  - Each river is a full-width band `(0, a, N, b)` with a single hinge line on its proximal side.
  - Each hub owns a full-width horizontal slab.
  - Slab heights come from a DP over start positions, with feasibility cached on (slab, height, start parity).
  - Source: [pack.py:126-141, 743-822](mcp_harness/pleatwright/pack.py); "All 51 artifact trees are path-shaped (measured)" — [spec 2026-10-10 §2](docs/superpowers/specs/2026-10-10-branching-hub-packer-design.md).
- **Inside a slab ("pocket").**
  - Flaps are tiled as up to 4 rows of columns (`_pocket_solutions`, `max_rows=4`). Rows are assigned by brute-force `itertools.product(range(nrows), repeat=n)`.
  - Symmetric rows (`_row_concrete`) put a mirrored pair in mirrored columns about x=N/2, with at most ONE axial (centred) flap per row.
  - A column's width/height "realise exactly its length (a clipped 2L x 2L tip rectangle, Lang's minimum polygon)".
  - Source: [pack.py:209-235, 278-360, 538-605](mcp_harness/pleatwright/pack.py)
- **Gap fill is flap expansion only.** "a column absorbs the cells around it by growing along its ridge (taller than L) or across its tip (wider than 2L when its depth is exactly L), or by a virtual hinge beyond the paper edge". — [pack.py:24-27](mcp_harness/pleatwright/pack.py)
  - In `_row_concrete`, the leftover width `extra` is given to the first "flex" inner column, or to the edge/axial column. — [pack.py:306-357](mcp_harness/pleatwright/pack.py)
- **Acceptance filters before `base.build`.**
  - `_max_d(r) == r.L`: the region's max elevation equals its flap length exactly.
  - `_parity_ok`: every vline × hline corner must satisfy x+y even, because "Ridges leave every vertical/horizontal hinge corner at 45 degrees; the accordion coordinate ... agree along that ridge only if the corner lies on the x + y even lattice".
  - Hinge lines in a pocket are forced onto one parity class p.
  - Source: [pack.py:695-720, 813](mcp_harness/pleatwright/pack.py)
- **Ranking is not efficiency.** `_score` counts virtual hinge lines (lines outside the paper) and nothing else. The docstring also says "most balanced rows", but the code only counts virtual lines, and it scores yielded candidates rather than reordering them: `pipeline` takes the first that builds. — [pack.py:29-30, 830-840](mcp_harness/pleatwright/pack.py); [pipeline.py:265-272](mcp_harness/pleatwright/pipeline.py)
- **Per-N caps.** `per_N=60` layouts, 6 height tuples, 8 pocket solutions per slab, `limit=24` pocket solutions, row builders `limit=6`/`2`/`3`, `_compose cap=40`. — [pack.py:538-628, 724-827](mcp_harness/pleatwright/pack.py)
- **Packing ladder** in `pipeline._run`:
  1. `("symmetric", scale, True)`
  2. `("asymmetric", scale, False)` (unmirrored rows)
  3. `("symmetric x2", 2*scale, True)`: every length doubled, "exact, no rounding: an odd river length forces opposite hinge parities on its two sides, which even lengths cannot".
  - Each rung uses `n_max = max(2*G_init, G_init+60)` and a global `max_candidates=400`. The first rung that yields a certified base wins. — [pipeline.py:246-282](mcp_harness/pleatwright/pipeline.py)
- **Why rung 2 exists.** Unequal declared pair lengths (starfish_0), or an odd river (dog_2: "its 11-unit river puts opposite hinge parities on its two sides while both slabs' column boundaries (hw - 6, hw - 8) share one parity"). — [evidence 2026-10-06 README](docs/superpowers/evidence/2026-10-06-corigami-pipeline/README.md); [spec 2026-10-06 deviation 7](docs/superpowers/specs/2026-10-06-corigami-tree-to-model-pipeline.md)
- **Unequal pairs on the symmetric rung.** `_items_sym` makes a declared pair whose two lengths differ into two *axial* items. Since a symmetric row allows at most one axial item, each lands in its own centred row. — [pack.py:215-234, 284-285](mcp_harness/pleatwright/pack.py)
- **nest.py, for branching hub graphs only.**
  - Each hub owns a rectangular pocket; the root's pocket is the whole paper.
  - A child hub's river is "the band of width W along every side of that strip that is not paper edge (an L-infinity offset band, Box Pleating Studio's river contour)". Its pocket is the strip shrunk by W.
  - A pocket is a vertical stack of strips (the flap block plus one strip per child), with strip orders enumerated up to `ORDER_CAP=120`.
  - A mirrored hub pair shares one strip split at x=N/2; the right half is a mirror image.
  - Source: [mcp_harness/pleatwright/nest.py:1-221](mcp_harness/pleatwright/nest.py)
- **Hub pairs** are derived, never authored: two child hubs of one parent with equal river lengths whose subtrees match leaf-for-leaf through declared pairs, recursively. — [pack.py:144-192](mcp_harness/pleatwright/pack.py)
- **Rivers never bend around flaps.**
  - Spec: "Rivers still never bend around flaps, so a long thin branch costs a full-width strip; three of the 109 named branching edits exceed the pipeline's grid cap for that reason". — [spec 2026-10-06 deviation 1](docs/superpowers/specs/2026-10-06-corigami-tree-to-model-pipeline.md)
  - Branching-packer evidence: toed crab_3, toed elephant_3 and toed spider_2 need N = 108 / 110 / 142 against caps of 106 / 106 / 132. — [evidence 2026-10-10](docs/superpowers/evidence/2026-10-10-branching-packer/README.md)
  - Wall-following, COrigami-style snaking rivers were "Rejected for now ... (no algorithm published)". — [spec 2026-10-10 prior-art table](docs/superpowers/specs/2026-10-10-branching-hub-packer-design.md)
- **Cost of branching** (median grid relative to the unedited roll): antlered 1.30, toed 1.18, lopsided 1.68. "Its unpaired antlers become two full-width strips stacked one above the other". — [evidence 2026-10-10](docs/superpowers/evidence/2026-10-10-branching-packer/README.md)
- **First candidate always accepted.** Every committed 2026-10-06 record has `pack_tried: 1`, and my probe reproduces `tried=1` on all 51. For the 6 unmirrored rolls this means the symmetric rung produced no candidate at all within its cap, rather than producing candidates that `base.build` rejected. — [records.jsonl](docs/superpowers/evidence/2026-10-06-corigami-pipeline/records.jsonl); probe `$S/bp_eff.jsonl`

### Inferences
- In practice `base.build` never rejects a candidate here, because `_max_d`/`_parity_ok` already filter for it. So the final grid N is decided entirely by which (N, layout) the enumerator yields first. Two levers drive grid size: the enumeration family (rows-of-columns inside full-width slabs) and the ladder order. A better packer could plug in at `pack.candidates` / `nest.candidates` without touching anything downstream: solve/shape/fold consume only the `Base` ([spec 2026-10-10 "Out of scope"](docs/superpowers/specs/2026-10-10-branching-hub-packer-design.md)).
- **Rivers today are only straight full-width bands** (path graphs) or rectangular offset rings (nest.py). There is no river routing in the Lang/BP-Studio sense: no bends around flaps, no corner gadgets, no variable-direction rivers.

### Gaps
- The docstring's "most balanced rows" ranking is not implemented in `_score`. I found no other ranking signal, and there is no objective that minimises N inside a given N's candidate list.

---

## 2. What `base.build` tiles with, and where slack paper goes

### Takeaway
`base.build` requires every cell of the N×N grid to be owned by exactly one region (flap or river). It then builds the folded state analytically and checks it: a piecewise isometry onto a strip one grid unit wide.

There is no filler or padding region type. All slack is absorbed by **flap expansion**: flap regions grow beyond their minimum L∞ polygon, which makes thicker flaps rather than longer or wider ones, or by virtual hinges that lift the raw edge. On the 51 trees, a median 39% of the sheet is such expansion paper. The code has no paper-efficiency metric.

### Cited Findings
- **Ownership check.** Each cell is owned once ("cell owned twice" → `BaseError`), and `len(owner) != N*N` raises `tiling incomplete`. — [mcp_harness/pleatwright/base.py:95-107](mcp_harness/pleatwright/base.py)
- **Folded state.** Each cell is split into 4 quarter-triangles. Each vertex maps to (s, w):
  - s = strip(u) + σ_e·d∞(p), the position along the tree;
  - w = tri(x) or tri(y), a period-2 triangle wave across the strip.
  - Every triangle is checked for isometry (AᵀA = I to 1e-9) and every shared vertex for continuity. A crease exists wherever neighbouring triangles' maps differ, and is classified H (region boundary), R (zone switch = straight skeleton) or P (accordion pleat). — [base.py:1-26, 109-176](mcp_harness/pleatwright/base.py)
- **The folded base is 1 grid unit wide.** COrigami's solved base is "a dense, flat-folded strip of paper ... its measured width is exactly one grid unit (fold their Ram solving CP: a 1 x 16 unit strip)". — [base.py:3-6](mcp_harness/pleatwright/base.py)
  - The orchestrator prompt states the same: "every flap is a strip one grid unit wide". — [orchestrate.py:52-53](mcp_harness/pleatwright/orchestrate.py)
- **Slack mechanisms, as built.**
  - ridge-direction growth;
  - width growth when depth is exactly L;
  - a virtual hinge past the paper edge, so the raw edge sits at δ>0.
  - Source: [pack.py:24-27, 241-263](mcp_harness/pleatwright/pack.py)
- **No efficiency metric.** I found no paper-efficiency, scale or utilisation metric anywhere in `mcp_harness/pleatwright/` (grep for efficien/stretch/level shift/22.5/TODO returned nothing outside `certify/`). The run record keeps `grid_init` and `grid_size`, but nothing computes their ratio. — [pipeline.py:244, 284](mcp_harness/pleatwright/pipeline.py)
- **Measured area split** (probe `$S/bp_eff.jsonl`, 51 trees). For each flap region I computed the smallest L∞ ball (radius L, clipped to the paper) centred on a tip point (d = L) of that region, which is Lang's minimum box-pleated flap polygon at that tip location. Results:

  | quantity | median | min | max |
  |---|---|---|---|
  | minimum flap polygons, sum / N² | 0.501 | 0.198 | 0.731 |
  | river cells / N² | 0.119 | 0.000 | 0.607 (guinea_pig_2) |
  | expansion "filler" (1 − both) | 0.39 | 0.126 | 0.763 |
  | per-tree median flap expansion (region area / min polygon) | 1.74× | 1.00× | 4.78× (scorpion_2) |
  | flap cells / Σ flap lengths (= mean layer count over a flap's 1-unit-wide strip, since folding preserves area) | 34.2 | 7.1 | 100.2 |
  | virtual (off-paper) hinge lines per layout | 2 | 0 | 4 |

  Source: probe `$S/bp_eff.jsonl`.
- **Crease budget.** Pleats dominate the base's unit creases (median 88.1% P versus H and R). Example, dog_0 at N=46: H 76, R 241, P 2045. — probe `$S/bp_eff.jsonl`

### Inferences
- The square is always fully used, so CLAUDE.md §1's invariant holds. But "used" means that up to about 3/4 of the sheet (median about 2/5) is surplus layers inside flaps: the strip is 1 unit wide and each flap carries about A/L layers. Example: lizard_1's front legs expand 5.8× and 9.1×, because its unequal front-paw pair (6 vs 5) became two stacked axial rows.
- So "efficiency" in Pleatwright has two faces:
  - (a) grid size N relative to tree size, i.e. scale;
  - (b) layer thickness and uneven thickness from expansion, i.e. foldability and quality.
- Techniques that shrink N (better packing, stretches, level shifts) improve (a). Techniques that let slack become *useful* structure (e.g. hinge shifts that move paper to rivers, or turning surplus into extra flap width before narrowing) would improve (b).

### Gaps
- No existing measure of per-flap thickness or layer count exists in code or docs. The A/L figure above is my derivation (area is preserved and the base is 1 unit wide), not a recorded metric.

---

## 3. Measured grid sizes and efficiency on the 51 artifact trees

### Takeaway
- **Grid sizes** run from N=10 to 136 (median 50). On the median tree N is 1.46× the App. E.1 heuristic `G_init` and 1.69× the tree diameter D. Only 3 trees land at `N == G_init`.
- **Against TreeMaker's** circle/river-packing scale for the same rolls, Pleatwright's flaps are about 10% shorter per unit of anatomy (median scale ratio 0.894).
- **The ladder order costs paper.** Running the unmirrored rung alone gives an equal or smaller N on every tree where it finished (42), and a strictly smaller N on 16, e.g. dolphin_0 50→32 and octopus_3 84→56. Taking the better of the two rungs lifts the median TreeMaker ratio to 0.974.
- **Doubling lengths** (half-unit resolution) shrinks N on 7 trees, by up to 22% (ant_0 102→80 equivalent).

### Cited Findings
- **Committed per-tree records** (2026-10-06, 51/51 complete): grid sizes 10-136; 45 symmetric and 6 unmirrored rolls (crab_3, dog_2, elephant_3, frog_0, spider_2, starfish_0), "all at authored lengths"; 39/51 globally CERTIFIED, the 12 largest (grid 66-136) `OVERSIZE+LOCAL_SAT`. — [results.md / README](docs/superpowers/evidence/2026-10-06-corigami-pipeline/README.md), [records.jsonl](docs/superpowers/evidence/2026-10-06-corigami-pipeline/records.jsonl)
- **Per-tree table** (probe `$S/bp_eff.jsonl` + `$S/summ.py`; N equals the committed `grid_size` for every roll). Column notes:
  - G = `grid_init`, D = tree diameter, Σflap = sum of flap chain lengths.
  - "TM ratio" = (k/N)/s_TM. Here k = stick length / normalized tree length for that roll (from `full17_v3_trees/<roll>.json` `tree_nodes` vs the sticks), and s_TM = the TreeMaker `scale=` in that roll's `served_fold` `frame_title`, i.e. paper per tree unit. A ratio <1 means Pleatwright's flaps are shorter than TreeMaker's.
  - "asym N" = the unmirrored rung run alone; "x2 N/2" = the doubled-length rung run alone, halved; "—" = not found within the cap or the run was stopped.

| roll | rung | N | G | D | N/G | N/D | Σflap | flaps | TM ratio | asym N | x2 N/2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| ant_0 | sym | 102 | 44 | 31 | 2.32 | 3.29 | 104 | 8 | 0.649 | 70 | 80 |
| ant_1 | sym | 54 | 44 | 28 | 1.23 | 1.93 | 100 | 8 | 1.184 | 54 | 54 |
| ant_2 | sym | 78 | 44 | 33 | 1.77 | 2.36 | 100 | 8 | 0.850 | 64 | 64 |
| bat_0 | sym | 36 | 28 | 28 | 1.29 | 1.29 | 55 | 6 | 1.016 | 36 | 36 |
| bat_2 | sym | 32 | 32 | 31 | 1.00 | 1.03 | 46 | 5 | 0.969 | 32 | 32 |
| bat_3 | sym | 44 | 32 | 31 | 1.38 | 1.42 | 53 | 6 | 0.741 | 44 | 44 |
| bird_0 | sym | 50 | 26 | 26 | 1.92 | 1.92 | 54 | 6 | 0.929 | 50 | 50 |
| bird_1 | sym | 40 | 32 | 31 | 1.25 | 1.29 | 55 | 6 | 0.912 | 38 | 40 |
| bird_2 | sym | 42 | 30 | 27 | 1.40 | 1.56 | 59 | 6 | 0.896 | 42 | 42 |
| cat_1 | sym | 46 | 36 | 35 | 1.28 | 1.31 | 73 | 6 | 1.101 | 46 | 46 |
| cat_2 | sym | 46 | 36 | 36 | 1.28 | 1.28 | 71 | 6 | 1.099 | 46 | 46 |
| cat_3 | sym | 50 | 34 | 32 | 1.47 | 1.56 | 66 | 6 | 0.877 | 50 | 50 |
| crab_0 | sym | 66 | 44 | 28 | 1.50 | 2.36 | 106 | 10 | 0.960 | 66 | 66 |
| crab_1 | sym | 50 | 34 | 21 | 1.47 | 2.38 | 82 | 10 | 0.896 | 50 | 50 |
| crab_3 | asym | 104 | 48 | 31 | 2.17 | 3.35 | 121 | 11 | 0.656* | 104 | — |
| dog_0 | sym | 46 | 34 | 34 | 1.35 | 1.35 | 67 | 6 | 0.989 | 44 | 44 |
| dog_1 | sym | 72 | 44 | 38 | 1.64 | 1.89 | 94 | 6 | 0.775 | 70 | 70 |
| dog_2 | asym | 50 | 46 | 46 | 1.09 | 1.09 | 84 | 6 | 1.337 | 50 | 50 |
| dolphin_0 | sym | 50 | 32 | 32 | 1.56 | 1.56 | 52 | 5 | 0.670 | 32 | 50 |
| dolphin_1 | sym | 46 | 30 | 30 | 1.53 | 1.53 | 52 | 5 | 0.646 | 30 | 46 |
| dolphin_2 | sym | 42 | 30 | 29 | 1.40 | 1.45 | 40 | 5 | 0.658 | 30 | 41 |
| elephant_0 | sym | 80 | 42 | 39 | 1.90 | 2.05 | 90 | 7 | 0.771 | 72 | 80 |
| elephant_1 | sym | 72 | 42 | 40 | 1.71 | 1.80 | 96 | 8 | 0.858 | 72 | 72 |
| elephant_3 | asym | 80 | 46 | 46 | 1.74 | 1.74 | 103 | 8 | 0.863 | 80 | — |
| frog_0 | asym | 42 | 42 | 41 | 1.00 | 1.02 | 66 | 5 | 1.202 | 42 | 42 |
| frog_1 | sym | 40 | 32 | 31 | 1.25 | 1.29 | 59 | 5 | 1.203 | 38 | 40 |
| frog_2 | sym | 48 | 40 | 40 | 1.20 | 1.20 | 72 | 5 | 1.093 | 46 | 46 |
| guinea_pig_0 | sym | 60 | 56 | 56 | 1.07 | 1.07 | 94 | 5 | 1.169 | 60 | 60 |
| guinea_pig_1 | sym | 22 | 20 | 19 | 1.10 | 1.16 | 26 | 5 | 0.982 | 22 | 22 |
| guinea_pig_2 | sym | 56 | 56 | 55 | 1.00 | 1.02 | 36 | 5 | 0.792 | 56 | 56 |
| horse_0 | sym | 70 | 48 | 39 | 1.46 | 1.79 | 102 | 6 | 0.867 | 68 | 70 |
| horse_1 | sym | 60 | 38 | 33 | 1.58 | 1.82 | 77 | 6 | 0.844 | 60 | 60 |
| horse_2 | sym | 54 | 40 | 35 | 1.35 | 1.54 | 81 | 6 | 1.297 | 54 | 54 |
| lizard_0 | sym | 38 | 28 | 28 | 1.36 | 1.36 | 54 | 6 | 0.980 | 38 | 38 |
| lizard_1 | sym | 64 | 30 | 29 | 2.13 | 2.21 | 57 | 6 | 0.609 | 38 | — |
| lizard_2 | sym | 44 | 28 | 26 | 1.57 | 1.69 | 56 | 6 | 0.779 | 40 | 44 |
| octopus_0 | sym | 10 | 8 | 7 | 1.25 | 1.43 | 14 | 9 | 1.158* | 10 | 10 |
| octopus_2 | sym | 66 | 48 | 36 | 1.38 | 1.83 | 118 | 9 | 0.894 | 60 | 66 |
| octopus_3 | sym | 84 | 50 | 28 | 1.68 | 3.00 | 118 | 9 | 0.710 | 56 | 84 |
| rabbit_0 | sym | 44 | 32 | 32 | 1.38 | 1.38 | 63 | 6 | 0.942 | 44 | 44 |
| rabbit_1 | sym | 54 | 36 | 34 | 1.50 | 1.59 | 76 | 6 | 0.929 | 54 | 54 |
| rabbit_3 | sym | 48 | 38 | 37 | 1.26 | 1.30 | 77 | 6 | 1.035 | 48 | 48 |
| scorpion_0 | sym | 78 | 56 | 31 | 1.39 | 2.52 | 146 | 11 | 0.956 | — (>11 CPU-min, killed) | 78 |
| scorpion_1 | sym | 84 | 62 | 33 | 1.35 | 2.55 | 161 | 11 | 0.894 | — (not run) | 84 |
| scorpion_2 | sym | 86 | 42 | 32 | 2.05 | 2.69 | 107 | 11 | 0.669 | — (not run) | — |
| spider_0 | sym | 102 | 62 | 38 | 1.65 | 2.68 | 148 | 9 | 0.737 | — (not run) | — |
| spider_1 | sym | 74 | 40 | 28 | 1.85 | 2.64 | 96 | 9 | 0.773 | — (not run) | 72 |
| spider_2 | asym | 136 | 72 | 48 | 1.89 | 2.83 | 171 | 9 | 0.726 | — (not run) | — |
| starfish_0 | asym | 44 | 28 | 25 | 1.57 | 1.76 | 58 | 5 | 0.823 | — (not run) | — |
| starfish_1 | sym | 48 | 30 | 24 | 1.60 | 2.00 | 59 | 5 | 0.764 | — (not run) | 48 |
| starfish_2 | sym | 44 | 30 | 26 | 1.47 | 1.69 | 60 | 5 | 0.859 | — (not run) | 44 |

  \* crab_3's TreeMaker base used an engine-added stub flap and octopus_0's had edge lengths nudged ±10% (`served_fold` frame titles), so those two TM ratios are not like-for-like.
- **Summary statistics** (probe `$S/summ.py`):
  - N: min 10, median 50, mean 58.4, max 136.
  - N/G_init: median 1.458, mean 1.490, max 2.318; N == G_init on 3/51.
  - N/D: median 1.692, mean 1.801, max 3.355.
  - TM ratio: median 0.894, mean 0.902, range 0.609-1.337. 12/51 are ≥ 1. Excluding the stub/jitter rolls: n=49, median 0.894.
- **Rung comparison** (`$S/rung_asym.jsonl`, 42 trees completed before I stopped the run at scorpion_0):
  - The unmirrored rung alone gives N ≤ shipped N on 42/42 and N < shipped N on 16/42: ant_0 102→70, ant_2 78→64, bird_1 40→38, dog_0 46→44, dog_1 72→70, dolphin_0 50→32, dolphin_1 46→30, dolphin_2 42→30, elephant_0 80→72, frog_1 40→38, frog_2 48→46, horse_0 70→68, lizard_1 64→38, lizard_2 44→40, octopus_2 66→60, octopus_3 84→56.
  - On those 42 trees, taking min(shipped, asym) moves the TM ratio median from 0.904 to 0.974 (mean 0.923 → 0.989), and the count ≥1.0 from 12 to 17.
- **Unmirrored-rung cost on large single-hub trees.** scorpion_0 (11 flaps) ran >11 CPU-minutes without yielding a candidate before I killed it. The likely cause is the brute-force row assignment `itertools.product(range(nrows), repeat=n)` in `_pocket_solutions` ([pack.py:560-566](mcp_harness/pleatwright/pack.py)), which grows as 4^n. This is my reading of the code, not profiled.
- **Doubled-length rung** run alone (`$S/rung_x2.jsonl`; N cap = min(200, pipeline n_max)):
  - N_x2/2 < shipped N on 7/44: ant_0 102→80, ant_2 78→64, dog_0 46→44, dog_1 72→70, dolphin_2 42→41, frog_2 48→46, spider_1 74→72. Equal on the rest.
  - Median ratio 1.0, min 0.784.
  - 7 trees found none within the cap (crab_3, elephant_3, lizard_1, scorpion_2, spider_0, spider_2, starfish_0).
- **Prior measurement on the archived compiler** (different trees: 16 subjects of the 09-09 artifact, archived Lang Ch.13 compiler). `ratio = scale_bp / scale_tm` had "mean 0.952, median 0.885, min 0.732 (spider), max 1.297 (lizard), with 6 of 16 at or above 1.0". Lang Ch.13 p.573 says only that BP "must be, by definition, less efficient" and "the penalty is often very small"; an "up to 40%" figure attributed to Lang "does not exist". — [spec 2026-09-20 §11 amendment 18 and §6](docs/superpowers/specs/2026-09-20-box-pleat-compiler-design.md)

### Inferences
- The baseline box-pleating penalty against TreeMaker (median about 0.89) matches the archived compiler's (0.885). But a large share of Pleatwright's penalty comes from its own search, not from box pleating as such:
  - The ladder takes the symmetric rung whenever it packs, even when the unmirrored rung packs much smaller (dolphins about 35% smaller N).
  - Rows-of-columns plus full-width bands leave about 46% headroom over `G_init` at the median.
- The cheapest efficiency wins are therefore packer-level: try all rungs and keep the smallest N, or rank by N across rungs, before any gadget work.
- Caveat: dropping the symmetric rung trades away mirror symmetry of the CP, which the project values. The doubled-length rung shows that finer grid resolution rarely helps (7/44), so integer resolution is not the main bottleneck.
- TreeMaker ratios above 1 (12 trees) show that TreeMaker's scale was itself a local optimum, frequently on a rescued or re-ordered tree (`served_stage` order/flatten/placement), so it is not an upper bound. Use it as a reference, not as an optimum.

### Gaps
- There is no true optimum for these trees (no exact BP packer, no global circle-packing optimum), so absolute efficiency is relative to `G_init`, D and TreeMaker only.
- The unmirrored-rung N is missing for 9 trees (scorpion ×3, spider ×3, starfish ×3), which I stopped or did not reach for time.
- I did not run the full pipeline (solve/shape) on the smaller-N layouts, so it is unverified whether they also certify globally and fold. `base.build` did certify them, and they were all accepted at `tried=1`.

---

## 4. Solving, narrowing, shaping, and what certification checks

### Takeaway
- **Base creases** lie on a 0°/45°/90° lattice: integer grid lines plus half-diagonals of each unit cell. There are no molecules or gadgets: the crease *set* is read off the analytic folded state, and `solve.py` only assigns M/V.
- **No 22.5° or other off-grid crease** exists anywhere in the base.
- **Off-grid creases appear only in shaping**, as arbitrary-angle simple folds and the `asym2`/`asym4` narrowing template applied to the folded strip.
- **Certification is geometry-generic** (crimp test per vertex; SAT over facewise layer order), so a new gadget would pass through it unchanged, if it can be expressed as a crease set whose folded state `flat_fold` can reconstruct.

### Cited Findings
- **Crease geometry.** `base.build` triangulates each cell into 4 quarter-triangles meeting at the cell centre. Creases are edges between triangles with different affine maps, so they are axis-parallel unit edges or 45° half-diagonals. `merged_segments` keys lines by `round(2*dx), round(2*dy)`, i.e. the half-unit lattice. — [base.py:109-129, 151-176, 210-252](mcp_harness/pleatwright/base.py)
- **`solve.py` assigns M/V on a fixed crease set**:
  1. F.2 pleat interleaving: pleat paths alternate M/V.
  2. F.3 ridge anchors and propagation.
  3. Hinge components tried as interleaved or symmetric, then greedy flips scored by App. D's crimp test (Alg. 1, ported).
  - Global flat-foldability is decided by SAT over layer order (`certify.sat_order`), phase-seeded with the heuristic labels; certified labels replace the heuristic ones.
  - Past the size guard (`MAX_RAW_TRIPLES = 100_000_000`) it falls back to `local_sat`, where every crimp-failing combination at each vertex becomes a clause → `OVERSIZE+LOCAL_SAT`.
  - Source: [solve.py:1-27, 340-416, 418-473](mcp_harness/pleatwright/solve.py); [certify/sat_order.py:46](mcp_harness/pleatwright/certify/sat_order.py)
- **Pleats carry an elevation attribute.** `elevation="1"` if M, else `"0"`, in the solving SVG. This is interleave parity, not Lang's elevation concept for level shifters. — [solve.py:428-433](mcp_harness/pleatwright/solve.py); [cp.py:14-15](mcp_harness/pleatwright/cp.py)
- **`narrow.py` is flap narrowing.** COrigami Fig. 13(d) "2x asymmetric flap narrowing", implemented as a piecewise isometry ψ on the folded strip (the clip-pattern algorithm).
  - "beyond the adapter the flap has width H/2 and is H shorter"; `asym4` = asym2 twice.
  - Creases: diagonals D1 and D2 (at 45° in strip coordinates) plus orthogonal lines. Projected back onto the paper through each face's map, they land on the paper at whatever angle that face has.
  - Source: [narrow.py:1-127](mcp_harness/pleatwright/narrow.py)
- **Narrowing is off by default.** It is applied only when requested: `shape_and_fold(..., narrow=())` defaults to none, and requests come only from the LLM orchestrator (`--orchestrate`, the `narrow` tool: "Costs about one unit of length per halving").
  - The adapter starts `NARROW_GAP = 1.75` units after the joint and needs room for H + 0.5.
  - Source: [pipeline.py:101-107, 310-314](mcp_harness/pleatwright/pipeline.py); [orchestrate.py:41-47](mcp_harness/pleatwright/orchestrate.py); [shape.py:232-266](mcp_harness/pleatwright/shape.py)
- **`shape.py` is tree shaping** (COrigami §3.6 / G.1): per stick, the unique simple fold with its axis in the parent's paper plane, or a crimp fallback, restricted to the stick's subtree.
  - Fold lines sit 0.4 units past the joint (`FOLD_OFFSET=0.4`, `FOLD_MARGIN=0.1`) so they avoid grid vertices.
  - Shaping creases have arbitrary angles, and their opacity encodes the fold fraction.
  - Source: [shape.py:1-27, 263-266](mcp_harness/pleatwright/shape.py); [spec 2026-10-06 deviations 2-3](docs/superpowers/specs/2026-10-06-corigami-tree-to-model-pipeline.md)
- **What a new crease set must pass.**
  1. `base.build`'s isometry/continuity on every triangle (only if the gadget is expressed inside the base's analytic map).
  2. `count_cp` / `local_count`: Alg. 1 crimp test at every interior vertex, with arbitrary sector angles.
  3. Global `certify`: `flat_fold.flat_fold` (reflection composition along the face-adjacency tree, `CLOSURE_EPS=1e-6`), then `layers.constraint_graph`, `sat_order.encode`, and `layer_certify.verify`.
  - Shaping CPs get local counting only, plus the folder's closure error < 1e-3 (`valid`).
  - Source: [pipeline.py:43-71, 127-141](mcp_harness/pleatwright/pipeline.py); [solve.py:340-384](mcp_harness/pleatwright/solve.py); [certify/flat_fold.py:1-24](mcp_harness/pleatwright/certify/flat_fold.py); [certify/__init__.py](mcp_harness/pleatwright/certify/__init__.py)
- **The certifier came from angle-agnostic tooling.** It "was written for the TreeMaker serve path and the Lang box-pleat compiler", and TreeMaker's crease patterns are not grid-locked. — [certify/__init__.py](mcp_harness/pleatwright/certify/__init__.py)
  - `layer_order` drops slivers under `AREA_EPS = 1e-9`. Memory records it as "1.0000000203x from firing on starfish", a known fragility for thin gadget faces. — [certify/layer_order.py:63](mcp_harness/pleatwright/certify/layer_order.py); project MEMORY.md index entry "AREA_EPS is 1.0000000203x from firing on starfish"

### Inferences
- **Grid-locked techniques plug in at `pack.py`/`nest.py` (Region geometry) and `base.py`**, provided they can be written as L∞ elevation fields per region. This covers level shifters (elevation offsets), hinge shifts, and river bends or corner bands. `base.build` re-derives creases automatically and verifies them, and solve/certify need no change.
- **22.5° gadgets and Pythagorean stretches cannot be expressed in `base.build`.** Its affine map is defined only on axis-aligned/45° quarter-triangles with s = strip(u) + σ·d∞ and the w = tri(x|y) accordion.
  - Adding either needs a new region kind with its own (s, w) map, or a gadget-overlay crease set injected after `base.build` and before `solve`.
  - Either way, `solve.heuristic_labels` (which assumes P/R/H kinds) would need extending. The certifier (crimp + SAT) can check the result, since it is angle-agnostic.
- **Flap narrowing already exists** (`narrow.py`), but it is shaping-stage, opt-in and LLM-driven, and costs length.
  - A packing-stage alternative is narrower flaps via different pleat density, so that excess expansion becomes width that the strip model currently forbids.
  - This would require relaxing the "strip 1 grid unit wide" construction.

### Gaps
- I did not verify empirically whether the SAT certifier stays tractable with 22.5° faces. It has only been exercised on 0/45/90 Pleatwright bases on main; the TreeMaker-era runs are archived.

---

## 5. Which box-pleating techniques are present, absent or rejected

### Takeaway
- **Present** (sometimes under other names): flap expansion (all gap fill), virtual hinges / raw-edge elevation δ>0 (a weak form of level change), mirrored hub pairs, nested L∞ offset river bands, straight full-width rivers, and flap narrowing (`asym2`/`asym4`, shaping-stage only).
- **Absent:** level shifters, Pythagorean stretches, hinge shifts, river routing or bending, 22.5° gadgets, meanders, and grafting.
- **Recorded positions:**
  - Pythagorean stretches and junction gadgets were explicitly *rejected* for the branching packer ("Euclidean separation, non-orthogonal").
  - Level shifters, stretches and meanders were *deferred* to "subproject B" of the archived compiler, which was never built.
  - Wall-following rivers are a recorded fallback ("gets its own spec").

### Cited Findings
- **Present: flap expansion and virtual hinges.** — [pack.py:24-27](mcp_harness/pleatwright/pack.py)
- **Present: L∞ offset river bands** ("Box Pleating Studio's river contour") **and a corner parity rule** ("Every right-angle river corner inside the sheet must have an inward 45° ridge ... becomes our parity check on a band's outer corners"). — [nest.py:1-11](mcp_harness/pleatwright/nest.py); [spec 2026-10-10 prior art](docs/superpowers/specs/2026-10-10-branching-hub-packer-design.md)
- **Rejected: Pythagorean stretches.** Spec 2026-10-10's prior-art row on Box Pleating Studio: "**Rejected:** Pythagorean stretches and junction gadgets (Euclidean separation, non-orthogonal)." Demaine-Demaine-Ku maze T/cross gadgets were also "Rejected: a different base family". — [spec 2026-10-10](docs/superpowers/specs/2026-10-10-branching-hub-packer-design.md)
- **Deferred: Lang Ch.14 techniques.** The archived compiler's spec: "Lang Ch. 14 (Polygon Packing) | Level shifters, Pythagorean stretches, meanders, parity rules (§14.3), dense bouncing (§14.6) ... | **Deferred to subproject B** (the macro library)".
  - Its non-goals: "any base-modification macro (grafts, level shifters, stretches, meanders, stubs)".
  - "B's Pythagorean stretches are the designed remedy" for efficiency.
  - Seams designed: `Macro(name, params_schema, sites(layout), apply(layout, site, **params))` and `Layout.gadgets` ("v1: always empty").
  - Source: [spec 2026-09-20 §1, §8, §9](docs/superpowers/specs/2026-09-20-box-pleat-compiler-design.md)
- **Level-shifter sites measured.** In the archived compiler, 6 contour-stage failures (cat, elephant, bat, dolphin, scorpion, ant) were `ContourFail("collision")` on the paper edge, "exactly the level-shifter site Lang §14.1 describes". — [evidence 2026-09-20-box-pleat README](docs/superpowers/evidence/2026-09-20-box-pleat/README.md)
  - Pleat reassignment "changes the base; it is Lang §14.1 level-shifter work, i.e. subproject B". — [spec 2026-09-22](docs/superpowers/specs/2026-09-22-pleat-reassignment-design.md)
- **Recorded fallbacks for the branching packer:**
  - "Collapse-and-carve ... as an extra ladder rung";
  - "Wall-following rivers ... makes pockets rectilinear polygons, which needs a new pocket packer, so it gets its own spec".
  - Out of scope: "Splitting a hub's flap block around its children; pairing inside off-axis pockets".
  - Source: [spec 2026-10-10 Fallbacks / Out of scope](docs/superpowers/specs/2026-10-10-branching-hub-packer-design.md)
- **COrigami gives little detail.** Its App. E holds only E.1 (`G_init`); "Branching hubs, hub pairs, elevation and the scoring rule are not described". — [spec 2026-10-10 prior art](docs/superpowers/specs/2026-10-10-branching-hub-packer-design.md)
- **No TODOs or FIXMEs** in `mcp_harness/pleatwright/` outside `certify/` (grep). — local grep

### Inferences
Mapping each technique to a module and its expected effect (the inference column is mine):

| technique | status | where it would plug in | what it would change |
|---|---|---|---|
| better packing order / try-all-rungs | absent (first rung wins) | `pipeline._run` ladder loop (lines 256-277) | measured: N down on 16/42 trees (up to 40%); costs CP mirror symmetry when the asym layout wins |
| river routing (bends, wall-following, L-bands) | absent; fallback recorded | `pack.candidates` / `nest._Search` (new Region shapes with `more` rects); `base` unchanged if L∞ | removes the "long thin branch costs a full-width strip" penalty; the 3 capped branching edits |
| hinge shifts / flap re-placement | absent | `pack._row_concrete*` (column x positions), `nest` strip order | moves expansion paper; lowers N/G (median 1.46) |
| level shifter (Lang §14.1) | absent; only virtual-hinge δ>0 | new Region kind in `pack.py` + elevation offset in `base._dist`/`strip_positions` | allows flaps/rivers at different elevations to meet (the parity/odd-river failures that force the unmirrored rung or doubled lengths) |
| elevation (raising flaps or rivers) | only virtual lines past the paper edge | `pack._vopts` virt options, `base.build` | packs edge flaps more tightly |
| Pythagorean stretch | explicitly rejected (non-orthogonal) | needs a non-L∞ region map in `base.build` or a post-`base` crease overlay; `solve.heuristic_labels` would need extending | Euclidean separation → smaller N for diagonal flap pairs |
| 22.5° gadgets | absent; base lattice is 0/45/90 only | same as the Pythagorean stretch; the certifier is angle-agnostic | new crease directions in the solving CP |
| flap narrowing | present (shaping, opt-in, LLM) | `narrow.py` / `shape.narrowings_for`; could be defaulted by rule | thinner appendages; costs about H of length per halving |

### Gaps
- Nothing records why the symmetric rung is preferred over a smaller unmirrored layout, beyond the design aim of symmetric animals ([spec 2026-10-10 decisions](docs/superpowers/specs/2026-10-10-branching-hub-packer-design.md)). Whether the owner accepts asymmetric CPs for smaller N is a policy question.

---

## 6. The archived Lang Ch.13 compiler (`archive/treemaker-box-pleat:mcp_harness/box_pleat/`)

### Takeaway
The archive holds a full Lang Ch.13 compiler, about 6.3k lines in 16 modules:
- `pack` (half-square backtracking polygon packer)
- `layout` (`tip_square` = Lang's minimum polygon; `Layout.gadgets` seam)
- `skeleton` (straight skeleton, `river_ridges` for multi-bend constant-width rivers)
- `contours` (dense axial / elevation contours with a global elevation field)
- `assign` (M/V CSP with arrangement checks)
- `sat_order` / `layers`, now moved into `pleatwright/certify/`.

It never built gadgets, but it detects level-shifter sites (contour collisions) and has designed `Macro` seams. On the 51 artifact trees it emitted only 7/51, which is why Pleatwright replaced it.

### Cited Findings
- **Module sizes** (`git show archive/treemaker-box-pleat:<f> | wc -l`): assign 1294, pack 919, compile 716, contours 602, clause_index 466, sat_order 337, layout 333, skeleton 297, layers 227, vertex_index 231, interleave 200, cores 187, tree 180, pleat_filter 171, emit 96. There are 90 commits touching `box_pleat/`. — `git log/show archive/treemaker-box-pleat`
- **Packer** (`box_pleat/pack.py` docstring):
  - a half-square backtracking polygon packer;
  - rivers as straight bands or one L-bend from the axis;
  - leaves largest-first, ranked corner > edge > interior;
  - finger and frontier gap fill.
  - "a corner/edge flap grown along its raw edge puts that edge at elevation 1 where a neighbour pins it at 0, a level-shifter site the packer would otherwise pick blindly". — `git show archive/treemaker-box-pleat:mcp_harness/box_pleat/pack.py` (lines 1-25)
- **Layout** (`box_pleat/layout.py`): `tip_square` = "the on-paper cells of the 2r x 2r square CENTRED on the tip -- r x r for a corner tip, 2r x r for a tip on a paper edge, 2r x 2r for an interior tip"; `gadgets: list` field at line 140. — `git show archive/treemaker-box-pleat:mcp_harness/box_pleat/layout.py`
- **Reuse already done and assessed.** The spec 2026-10-10 adapted "the constant-width multi-bend idea of `river_ridges` (`skeleton.py:264`) and the paper-edge vs hinge classification of `hinge_segments` (`layout.py:30`)". Archived rivers were "always a chord from the axis to an edge", so the archive could not branch either. — [spec 2026-10-10 prior art](docs/superpowers/specs/2026-10-10-branching-hub-packer-design.md)
- **Baseline on the 51 trees.** "7 emit, 31 time out, 7 stop at contours, 4 refused at tree, 2 fail to pack" (sparse labelling, 300 s cap). — [evidence 2026-10-06 README](docs/superpowers/evidence/2026-10-06-corigami-pipeline/README.md)
- **On its own 17 VLM trees** (2026-09-22): 15/16 contractable subjects pack, 10 reach a validated `.fold`, and 5 stop at contours with 0-vs-1 collisions on a paper edge ("exactly Lang Ch.14's level-shifter site, i.e. subproject B's input"). — project memory `box-pleat-compiler-design.md`

### Inferences
- **Reusable for efficiency work:**
  - the `tip_square` minimum-polygon definition and the corner > edge > interior placement ranking, as a packing objective;
  - the level-shifter site detector (collision on a raw edge between elevation families), which marks exactly where a level shifter is needed;
  - the `Macro`/`Layout.gadgets` interface design, as a template for a Pleatwright gadget seam.
- Its contour / skeleton machinery is less relevant: Pleatwright derives creases from an analytic folded state instead.

### Gaps
- I did not read the archived `skeleton.py` / `contours.py` bodies in full, so I cannot say whether a 22.5° or stretch-capable skeleton exists there. The spec says gadgets were "v1: always empty", so most likely not.
