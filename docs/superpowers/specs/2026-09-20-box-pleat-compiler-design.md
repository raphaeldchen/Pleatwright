# Box-pleating compiler (subproject A) — design

Date: 2026-09-20
Status: approved in brainstorming; awaiting written-spec review
Branch: `claude/origami-design-secrets-summary-b2fcea`

## 0. Prior art (required by CLAUDE.md §0)

| Source | What it gives us | Adopted / rejected |
|---|---|---|
| Lang, *Origami Design Secrets* 2e, Ch. 13 (Uniaxial Box Pleating) | The whole construction: hinge polygons enclosing packing circles, rivers of constant width, ridges = straight skeleton, axial contours launched from tips and bounced off ridges, elevation contours between them, the elevation rule for M/V, rule 4 "all paper is assigned". | **Adopted verbatim** as the crease-construction algorithm. |
| Lang Ch. 14 (Polygon Packing) | Level shifters, Pythagorean stretches, meanders, parity rules (§14.3), dense bouncing (§14.6 — why the grid is mandatory), hex pleating, combs. | **Deferred to subproject B** (the macro library). §14.3 parity is used now as a diagnostic. §14.6 is why `Layout` refuses non-integral lengths. |
| Lang Ch. 6 (Grafting), Ch. 5 (Point splitting) | Base-modification techniques. | Deferred to B. |
| COrigami, arXiv:2606.26299 (DeepMind, 2026), §"base packing" and §"solving" | Backtracking packer: rivers first (first river straight or one L-bend, later rivers wall-following), flaps by sliding along placed faces or brute-force enumeration, gap-fill by backtracking over flap expansions, grid size swept from a circle-packing/diameter lower bound; M/V by deterministic pleat/ridge parity plus greedy hinge search scored on local flat-foldability; funnel 55.3% pack / 79.2% solve. | **Adopted** the packer shape and the lower bound. **Rejected** whole-square symmetric-filter packing in favour of Lang's half-square + mirror (halves the search; all 17 subjects are bilateral). **Rejected** their greedy hinge scoring in favour of exact DFS on Maekawa, because our plan-view constraint leaves few free hinges. Their global-foldability constraint graph is **not built** in v1 (see §6). |
| BP Studio (Tsai), cited by COrigami as the continuous-relaxation alternative | Continuous packing of box-pleated flaps. | Rejected: the output we need is an integer `Layout` B can mutate, not a relaxed optimum. |
| This repo: `draft_and_compile_full_base`, `cp_audit`, `lint_verdict`/`linter_server`, `flat_fold`, `layer_order`, `mv_repair` | TreeMaker serve path; the validators. | Validators **reused unchanged** on the emitted `.fold`. `mv_repair` **not used** for assignment (it repairs near-valid labels with bounded flips; it is not a from-scratch assigner) — its `cp_audit` acceptance bar is the gate. |
| CLAUDE.md §1.1 | Coverage ceiling is structural for tree theory; "reaching the rest of the square means adding flaps or a different paradigm." | This is the different paradigm. Coverage is **reported, not assumed**, per §1.1's own discipline. |

Measured on the 17 committed trees (`docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/data/rule6_serve.json`) before this spec: every tree's lengths are integer multiples of a common unit (dog 2/45, cat 1/12, horse/rabbit/spider 1/20, …); after contracting degree-2 joints every tree is a star (1 hub, 0 rivers) or a dumbbell (2 hubs, 1 river); flap lengths 6–20 units; 5–11 leaves; grid lower bounds 30–55. These facts set v1's scope: k rivers is written generally but only k ≤ 1 is exercised.

## 1. Goal and non-goals

**Goal.** Compile a metric tree (the node-dict format `draft_and_compile_full_base` accepts) into a box-pleated, plan-view, mirror-symmetric uniaxial base as a `.fold`, and measure all 17 subjects against the TreeMaker serve-path numbers. Establish `Layout` as the representation that subproject B's technique macros operate on.

**Non-goals for v1.** Serve-path integration; MCP tool; any base-modification macro (grafts, level shifters, stretches, meanders, stubs); more than two elevation families; hex pleating; global layer-order solving; folding-sequence generation; the shaping stage.

## 2. Fixed decisions (from brainstorming)

1. Standalone package `mcp_harness/box_pleat/` + probe. Not on the serve path.
2. Full depth: packing → creases → M/V → `.fold` that the existing validators judge.
3. Grid unit = the tree's native quantization. Non-integral trees are refused, naming the edge. No rounding.
4. Half-square + mirror; plan view (an unbroken axial contour down the centre column is forced).
5. Packer = backtracking enumerator (COrigami shape); crease construction = Lang Ch. 13; the seam for B = `Layout`.

## 3. Package layout

```
mcp_harness/box_pleat/
  __init__.py
  tree.py        contract joints; leaves (r_i), branch edges (w_j), pairs; unit; path matrix; N_lb
  layout.py      Layout / HingePoly / River / Contour dataclasses; validate(); mirror()
  pack.py        pack(tree, *, max_N=None, budget=...) -> Layout | PackFail
  skeleton.py    straight_skeleton(poly) -> list[Segment]   (rectilinear, 45° bisectors)
  contours.py    propagate(layout, ridges) -> Contours | ContourFail
  assign.py      assign(layout, ridges, contours) -> Assignment | AssignFail
  emit.py        to_fold(layout, ridges, contours, assignment) -> dict
  compile.py     compile_tree(nodes, pairs) -> Result   (the one entry point; wraps the chain)
mcp_harness/probe_box_pleat.py                              the 17-way comparison
mcp_harness/tests/test_box_pleat_{tree,layout,pack,skeleton,contours,assign,emit,e2e}.py
docs/superpowers/evidence/2026-09-20-box-pleat/            table.md, results.json, svg/
```

One file, one job. `compile.py` is the only module the probe (and later B) imports.

## 4. Data model

```python
Cell = tuple[int, int]            # (col, row) on the N×N grid, origin bottom-left
Pt   = tuple[Fraction, Fraction]  # half-grid coordinates allowed

@dataclass(frozen=True)
class HingePoly:
    leaf_id: int
    tip: Cell                     # flap tip; for axial leaves tip[0] == N/2
    r: int                        # flap length in units
    cells: frozenset[Cell]        # rectilinear, includes the tip-square clipped to paper

@dataclass(frozen=True)
class River:
    edge_id: tuple[int, int]      # branch edge (hub_a, hub_b) in contracted-tree ids
    width: int
    cells: frozenset[Cell]        # constant width, 90° bends only

@dataclass(frozen=True)
class Contour:
    pts: tuple[Pt, ...]           # polyline on the half-grid
    elevation: Fraction           # 0 for axial; 1/2 or 1 for the second family in v1

@dataclass
class Layout:
    N: int                        # even
    unit: Fraction                # paper length of one cell (N * unit == 1)
    polys: list[HingePoly]
    rivers: list[River]
    axis_col: int                 # == N // 2
    contours: list[Contour]       # empty until contours.py runs
    gadgets: list                 # v1: always empty; B: stretches / shifters / meanders
```

`Layout.validate()` (called after pack, after every future macro, and before emit):

- **Partition.** `polys` ∪ `rivers` cells cover the N×N grid exactly once (Lang's rule 4).
- **Tip-square inclusion.** Each poly contains the 2r×2r square about `tip`, clipped to the paper (corner flap → r×r, edge flap → 2r×r).
- **Constant width.** Each river's cells form a strip of its `width` with 90° bends only (checked by Lang's test: every 45° ridge from a bend corner must land on the opposite bank's corner).
- **Mirror.** The right half is the mirror of the left about `axis_col`; axial leaves are self-mirrored.
- **Path condition.** For every leaf pair, Chebyshev distance between tips ≥ tree path length in units (necessary for box-pleated non-overlap, Lang §13.3 + Ch. 11 path inequality in the ∞-norm).
- **Hub regions.** Rivers partition the grid; every poly lies inside the region of its hub.

## 5. Algorithms

### 5.1 `tree.py`
- Build undirected weighted graph from node dicts; contract every degree-2 node (joints only set path lengths). Result: hubs (deg ≥ 3), leaves (deg 1) with `r_i` = leaf-to-hub chain, branch edges with `w_j` = hub-to-hub chain.
- Unit: largest `u` such that every `r_i`, `w_j` is an integer multiple (search k = 1..12 on the smallest length; refuse with `NonIntegral(edge_id, length)` otherwise).
- Leaves are *paired* if in `symmetric_pairs`, else *axial*. Refuse if a pair's radii differ.
- `N_lb = max(tree diameter in units, ceil(sqrt(Σ clipped tip-square areas)))`, rounded up to even. Area term assumes the best case (four corner flaps at ¼, rest edge at ½) — it is a lower bound, not an estimate.

### 5.2 `pack.py`
Half-grid search over columns `0..N/2` (inclusive of the axis column for axial leaves). Order: rivers, then leaves by descending `r`.

1. **Rivers** (k ≤ 1 exercised; written for k): candidate placements = horizontal band of `width` rows at each row offset, or one L-bend within the half; each candidate partitions the half-grid into hub regions. Reject candidates leaving a region too small for its hub's tip-square areas.
2. **Leaves**: candidate tips = cells in the hub's region where the clipped tip-square fits with no overlap and the Chebyshev path condition holds against all placed tips. Axial leaves: `tip[0] == N/2`. Rank candidates: touches a paper corner > touches a paper edge > interior (Lang's layer argument, Ch. 9 §9.4 / Ch. 14 §14.2); then number of touching neighbours; then distance to the hub's centroid. Backtrack on dead end.
3. **Gap fill**: collect empty cells; for each, candidates = extend one adjacent poly by a full strip along one of its edges (keeps it rectilinear; tip-square stays inside). Rivers never grow. Backtracking search for a consistent, non-conflicting set. Remaining gaps → `PackFail(stage="gapfill", cells=...)`.
4. Node budget per `N` (default 200k expansions). Exhausted → `N += 2`; stop at `2·N_lb` → `PackFail(stage="pack", N_tried, tightest_gap)`.
5. Mirror the half into the full `Layout`; `validate()`.

### 5.3 `skeleton.py`
Straight skeleton of a rectilinear polygon by incremental bisector collision (Lang §13.4): bisectors from every corner at 45°; when adjacent bisectors meet, drop the excluded edge and continue with the bisector of the remaining pair; terminate when the wavefront collapses. Squares → two diagonals; rectangles → diagonals + spine; L/T → general case. Rivers: one 45° ridge from each bend corner to the opposite bank. Assert every skeleton vertex is on the half-grid; otherwise `SkeletonFail(poly_id, vertex)` (this is the §14.3 odd-side diagnostic).

### 5.4 `contours.py`
- **Axial seeds**: every ridge junction on `axis_col` emits a contour leftward (plan-view requirement); every tip emits a contour toward each hinge edge of its polygon that it can reach perpendicularly.
- **Propagation**: straight until a ridge; reflect across it (45° incidence → 90° turn; 90° → straight through; Y-junction → one contour in, one out per remaining ridge; corner junction of two ridges → terminate). Terminate on a coincident same-elevation contour or the paper edge. Runaway guard: a contour longer than `4·N²` half-cells → `ContourFail("runaway")` (cannot happen on an integral grid per Lang §14.6; the guard is a tripwire).
- **Second family**: for every pair of adjacent parallel axial contours, insert a contour midway (elevation ½ if the gap is 1 cell, 1 if 2 cells) and propagate it identically. Repeat until no two same-elevation contours are adjacent without a higher contour between them. Two families only. A head-on meeting of two different elevations → `ContourFail("collision", site)` — reported, because that site is exactly where B's level shifter goes (Lang §14.1).

### 5.5 `assign.py`
- **Axis-parallel creases**: elevation rule — higher on both sides → V, lower on both sides → M, higher on one side → unfolded (`F`). (Viewed from the white side; Lang §13.5.)
- **Ridges and hinges**: a single CSP. Variables = M/V per ridge and hinge segment; mirrored segments share one variable. Constraint = Maekawa `|M − V| = 2` over folded creases at every interior vertex. Kawasaki is asserted, not solved (it holds by construction on a 45°/90° grid). DFS with unit propagation, most-constrained vertex first; tie-break prefers ridges alternating along their length. First solution wins. Unsatisfiable → `AssignFail(vertices=...)`.
- **Global layer order**: not solved. See §6.

### 5.6 `emit.py`
FOLD 1.1 frame: `vertices_coords` at half-grid × `unit/2`, `edges_vertices`, `edges_assignment` ∈ {M, V, F, B}, `edges_foldAngle` ∈ {±180, 0}, `faces_vertices` (planar faces, so `flat_fold`/`layer_order` run), plus a `box_pleat` block: `{N, unit, edge_roles: [axial|elev|ridge|hinge], leaf_tips: {leaf_id: [x, y]}}`. Deterministic ordering (sorted vertices, sorted edges) so reruns are byte-identical.

### 5.7 `compile.py`
`compile_tree(nodes, pairs) -> Result` with `Result.fold | None`, `Result.layout`, `Result.stage_reached ∈ {tree, pack, skeleton, contours, assign, emit}`, `Result.failure` (one of the typed failures) and timings. Never raises on a tree; raises only on malformed input.

## 6. Validation and the pre-registered bar

Per subject, the probe runs the emitted `.fold` through the existing, unchanged:
- `cp_audit` — Maekawa/Kawasaki per vertex; require 0 Maekawa defects.
- `lint_verdict` via `linter_server` (Oriedita, JVM) — require class PASS or BENIGN.
- `flat_fold` — require `bad_edges == 0`.
- `layer_order` — reported (consistent / contradiction), **not required**: self-intersection is the acknowledged v1 gap (COrigami's global-foldability step is not built).

Table columns: `subject, leaves, rivers, unit, N_lb, N, scale_bp, scale_tm, ratio, hull_coverage, flap_width_units, stage_reached, maekawa_defects, lint_class, flat_fold_ok, layer_order, pack_ms`, where both scales are in **paper length per grid unit** so they compare directly: `scale_bp = 1/N` and `scale_tm = design_scale × unit` (`design_scale` from the 09-09 artifact is paper per tree-length-unit; `unit` converts to grid units). `ratio = scale_bp / scale_tm` is the measured box-pleating penalty. Lang gives no figure: circle/river packing is provably the most efficient uniaxial packing, so box pleating "must be, by definition, less efficient", but "the penalty is often very small" (Ch. 13, p. 573). Any percentage attributed to him here is an error — measure the ratio and report it. `hull_coverage` is measured on the emitted leaf tips, not assumed to be 1.0.

Success = all 17 rows have `stage_reached == emit` and pass the three required validators. A row that fails is kept with its typed failure; the probe never raises.

## 7. Testing

TDD; every module has its test file before its implementation.
- **Goldens from the book**: Lang Fig. 13.12–13.17 toy (five leaves of 1 and 2 units, one river) packs at exactly `N = 6` with the lower-left square expanded to a rectangle; the §13.6 generic beetle (legs 4/6/8, body rivers 1) packs and its centre column is fully axial.
- **Unit**: `tree.py` contraction on the committed dog (radii 12,15,15,17,20,20; river 8; unit 2/45); skeleton on square/rectangle/L/T with vertex-on-half-grid assertions; contour reflection rules on 3×3 fixtures (45°, 90°, Y, corner); the CSP on a lone Waterbomb-style vertex and on a mirrored pair sharing a variable; emit round-trips through `flat_fold._validate`.
- **Property**: `Layout.validate()` holds for every packed layout; mirror(mirror(x)) == x.
- **Integration**: all 17 end-to-end against §6's bar; byte-identical `.fold` on rerun (`test_determinism` pattern).
- **Negative**: non-integral tree refused naming the edge; a deliberately unfillable gap fails at `pack`, not downstream; a `ContourFail("collision")` fixture reports the site.
- Runtime: the JVM lint is invoked only in the e2e test, marked like the existing linter tests; unit tests are pure Python.

## 8. Seams for subproject B (designed now, built later)

- `Macro(name, params_schema, sites(layout) -> list[Site], apply(layout, site, **params) -> Layout)`; postcondition is `Layout.validate()` followed by the unchanged `skeleton → contours → assign → emit → validators` chain. A macro that fails any of these is rejected with the typed failure as the LLM's feedback.
- `Layout.gadgets` carries fixed crease sets (Pythagorean stretch, level shifter, meander); `skeleton.py` and `contours.py` treat gadget cells as pre-creased and route contours through them rather than re-deriving.
- The LLM sees `Layout` (integers, ≤ a few hundred cells, human-readable), never `.fold`.
- v1 guarantees nothing about macros except that the interfaces above are stable.

## 9. Open risks

- **Straight skeleton on L/T polygons** is the one piece of real geometry; if it costs more than a day, v1 may restrict gap-fill to rectangles (never L/T) and record which subjects needed L/T.
- **Hinge CSP size**: bounded by the number of hinge segments (hundreds), mirrored, with most forced by the plan-view axial. If DFS blows up, fall back to COrigami's greedy score with the same acceptance bar.
- **Efficiency**: some penalty is expected (circle/river packing is provably optimal); its size is to be measured, not predicted. B's Pythagorean stretches are the designed remedy, not v1 tuning.

## 10. Amendments made while writing the plan (2026-09-20)

Found by working the toy golden (§7) through §5 by hand; each one changes a
sentence above and is binding.

1. **§5.3 ridges for boundary-tipped flaps.** The straight skeleton of the
   on-paper polygon is wrong when the tip lies on a raw paper edge: for a
   corner flap it would emit the anti-diagonal, which is not a crease (the
   corner flap folds on the single diagonal from the tip; the edge flap on the
   V from the tip — Lang Fig. 12.33, 12.26). Rule: ridges = straight skeleton
   of the polygon **mirrored across every raw-edge line that contains the
   tip**, restricted to the paper; skeleton segments lying on the paper edge
   are not creases but suppress raw-edge axials (below). Interior-tipped
   polygons keep the plain skeleton (a square is the Waterbomb, as before).
2. **§2.4 / §5.4 the centre column is not forced axial.** Forcing every cell
   of the column into an axial polygon or river is reachable only by adding
   axial stubs (Lang adds circles for exactly this, §13.6), which contradicts
   "no stubs in v1". Lang's tarantula (§9.7) shows a valley along the
   symmetry line *for most of the model* is enough. Therefore: no contour is
   pre-registered on the centre column and no junction seeds are launched
   from it; contours originate at tips only (plus raw-edge axials: the raw
   edge segments of a polygon whose tip lies on that edge, minus segments
   under a boundary skeleton piece); paired polygons may meet across the axis
   (a hinge on the axis is legal); an axial polygon whose skeleton has a
   segment along the centre column is rejected by `Layout.validate()`.
   Plan view survives as a labelling rule: any axial contour piece lying on
   the centre column is `F`.
3. **§5.4 / §5.5 dense contours and labels.** Sparse bookkeeping (axials
   plus midlines between equal elevations) misses real creases: the
   sawhorse spine extension of a rectangle flap is emitted only when a
   contour at the node's elevation reaches the node (Y-junction rule), and
   whether a midline is a maximum or a minimum is not decidable from the two
   bounding contours alone. Therefore contours are traced **densely**:
   (a) raw-edge axials for boundary tips and tip launches (elevation 0; a
   launch is skipped along a ridge line through the tip or along the paper
   edge); (b) for every straight boundary run (hinge run between two owners,
   or a raw edge of a polygon whose tip is not on that line — raw edges of
   rivers and tip-line raw edges are excluded) that is touched by an
   elevation-0 segment at points A, every interior half-grid point P of the
   run launches a contour perpendicular to the run into each owner at
   elevation min|P−a|/2, until a fixpoint. Labels (white side up, Lang
   §13.6): a contour piece is a **minimum** (both neighbours higher) → `M`,
   a **maximum** (both lower) → `V`, a slope → `F`; elevation 0 is always
   `M`; centre-column pieces → `F`; paper boundary → `B`. Because a face
   narrows toward its ridge nodes, "neighbour" is not the parallel line over
   the same interval: within one face of the ridge+hinge subdivision the
   elevation is a function of one coordinate, so each face carries a
   **profile** {line coordinate → elevation} collected from every contour
   piece inside it (faces found by a planar walk over ridge, hinge and
   boundary pieces; a piece belongs to the face containing its midpoint),
   and the two neighbours are read from the profile at ±1 with linear
   interpolation, or extrapolated by continuing the slope when one side is
   absent. Ridges and hinges stay a Maekawa CSP. A segment reached twice at different elevations is
   `ContourFail("collision")` — a real inconsistency of the layout, the
   level-shifter site of Lang §14.1.
4. **§5.2** tip candidates need not stay off the axis; gap fill is one cell
   at a time (smallest perimeter increase first, lower leaf id on ties).

## 11. Amendments made during execution (2026-09-21)

Each item was forced by a hand-trace or a measured failure while
implementing the plan; the plan's tests were corrected where noted.

1. **§5.1 unit detection.** The unit is detected from the *raw*
   pre-contraction edge lengths (joint chains carry the finest quantum);
   divisor `k ∈ 1..12` is accepted iff every raw length `q = ℓ / (ℓ_min/k)`
   satisfies `|q − round(q)| ≤ 2e-3 / k` (tolerance tightens with `k`, so a
   length coincidentally near `7/3` is refused rather than admitted at
   `k = 3`); the final per-edge check uses a flat `2e-3`. A declared pair
   whose radii or hubs differ after contraction is refused with the typed
   `AsymmetricPair` — the committed `crab` (claw pair `[4, 6]`, radii 26/35
   vs 18/35) is refused at stage `tree`, as §5.1 already required.
2. **§4 validate.** `validate()` never raises: an unknown leaf id is an
   error `leaf: …`; river messages share the prefix `river:`; every message
   prefix names exactly one invariant (subproject B reads them). The path
   check stays the pure Chebyshev comparison (a tip-square failure is not a
   path failure).
3. **§5.2 gap fill** grows polygons from the frontier, choosing the globally
   smallest perimeter increase (ties: lower leaf id, then row, col). A fixed
   scan order is not equivalent: the first cell of the row above a river can
   never be adjacent to a polygon under any earlier assignment, and the
   backtracking that follows is exponential (measured: `dog` never packed).
   The packer may skip a grid size only by an **exact** necessary condition
   (`_pair_span_infeasible`, per-hub demand with `min(N/2, r)·r` for an axial
   leaf, per-leaf empty-region pre-check); each prune has a test comparing
   it with the unpruned search. The plan's "prefer non-axial polygons in
   column `N/2 − 1`" preference is not implemented.
4. **§10.1 skeleton.** A wavefront vertex whose adjacent edges are
   anti-parallel (a collapsing strip) is a spike, not a collinear
   pass-through, and must be kept so the reflex-on-edge split fires;
   otherwise T-shaped gap-filled tiles get off-45° ridges. Mirrored
   skeleton segments crossing the paper edge are **clipped**, never dropped;
   the on-boundary pieces are what suppress raw-edge axials.
5. **§10.3 reflection.** `−refl(d)` is exact for one line only. At a
   junction the level line in each wedge between consecutive ridge rays is
   the mirror image of the incoming line carried wedge to wedge (elevation
   is a distance function with |∇e| = 1, linear per face, and the gradient
   mirrors across each ray); it is emitted only where it lies strictly inside
   its wedge. This reproduces 45° → 90°, ⟂ → straight, Y → straight plus a
   branch, V → terminate, and X → the three other axials. `ridge_points`
   therefore returns **directed rays** per point (a dict of undirected lines
   cannot tell a V from an X and invents rays on gap-fill bars). The tip
   launch skip is "along a ridge *ray* at the tip". Dense seeding is a
   single pass: seeds carry elevation > 0, so no new elevation-0 touch can
   appear. Raw-edge axials are walked from the tip until a boundary skeleton
   piece or the end of the polygon's edge run.
6. **§10.2 axis rule, narrowed.** A centre-column ridge that starts at the
   tip (the clipped mirrored spine of a boundary-tipped axial flap) is
   valid: the tip's launch along it is skipped and both faces carry `y/2`;
   it is the symmetry fold. The invalid configuration is a tip whose
   vertical launch is *not* along a ridge ray and which runs into an
   interior ridge on the centre column further inside the polygon: the
   axial turns at the V node and reaches the hinge at arc length > r.
7. **Flap-length invariant (new).** Lang's construction requires every
   elevation-0 path from a tip to meet the hinge at arc length exactly `r`
   (the axial coordinate `a ≡ r` on the hinge polygon boundary). Nothing
   else enforces it — a gap-filled polygon can violate it while passing
   every §4 invariant and every downstream validator, yielding a base whose
   flap is longer than the tree says. `propagate` therefore tracks arc length
   along tip-originated elevation-0 traces (branches continue the count) and
   returns `ContourFail("flap_length", (leaf, arc, r))` when a trace crosses
   the polygon's hinge, or a raw-edge axial reaches the end of the polygon's
   edge run, at arc length ≠ r. Traces ending on the paper boundary, on a
   boundary skeleton piece, or on an existing same-elevation contour are not
   checked. Known gap: point-level elevation conflicts at shared corners are
   invisible to segment-keyed collision detection.
8. **§4 tip square = Lang's minimum polygon (rule 2).** The minimum hinge
   polygon is the on-paper part of the `2r × 2r` square *centred* on the
   tip (the box-pleating "circle"): `r × r` for a corner tip, `2r × r` for
   a tip on a paper edge, `2r × 2r` for an interior tip; an axial tip on the
   centre column owns the left half of that square and its mirror. A tip
   may lie on the paper boundary but never on a hinge. The plan's one-sided
   `r × r` square was Lang's polygon only for corner tips; for edge and
   interior tips it put the tip on a hinge, so the tip's axials ran along
   the hinge (measured: 10 of 15 packed subjects failed the flap-length
   invariant). `Tree.n_lb` already counted `r²` for four corners and `2r²`
   for the rest, so the lower bound stands; interior tips cost `4r²`.
9. **§4 hinge-distance invariant (Lang §13.3).** For every polygon, the
   minimum perpendicular distance from the tip to the line of any hinge
   boundary segment (a boundary unit segment not on the paper edge) is
   exactly `r`: at least `r` by item 8, and equal to `r` or the flap is
   longer than the tree says (Lang: expansion in every direction "truly
   lengthens" the flap). Gap fill may add a cell to a polygon only if the
   polygon keeps at least one hinge segment at distance `r` afterwards; a
   cell nobody can take is a `PackFail("gap_fill")` for that placement.
10. **§10.3 elevation anchors and the boundary.** Elevation along a hinge run
    is the lower envelope of cones from every known point on it: `e(P) =
    min_a (e_a + |P − a| / 2)` over anchors `a`; elevation-0 touches are the
    special case. Contours reaching the paper boundary are recorded in a
    boundary elevation map (never as creases); a river's raw end is
    contour-like at the river's elevation there and supplies an anchor to
    the runs it meets, so seeding runs to a fixpoint after all (the
    frog "bar" collision was a missing anchor at the river's raw end, not a
    level-shifter site). A contour segment lying on a hinge is
    `ContourFail("contour_on_hinge", key)` at registration.
11. **§11.9 made constructive: growth units.** "Every hinge line at distance
    ≥ r" is equivalent to: no horizontal hinge strictly inside the tip's
    horizontal band (row boundaries in `(y − r, y + r)`) and no vertical hinge
    strictly inside its vertical band. A valid polygon is therefore the tip
    square, plus *arms* (whole band-columns extending the horizontal band,
    whole band-rows extending the vertical band, clipped to the paper), plus
    arbitrary cells in the four corner regions beyond both bands, 4-connected,
    with at least one hinge left on a band boundary. Gap fill grows by these
    units; a single cell beside a tip square is never admissible (its far
    edge is a hinge inside the band and folds to `a = r + 1`). The plan's
    hand toy layout had exactly such a bump on leaf 2 and was invalid; the
    toy packs at N = 6 with the axial leaf taking those cells instead.
12. **§11.11 corrected: arms along one axis (Lang: "expand in both
    directions … truly lengthen").** The line-distance condition is
    necessary, not sufficient (measured: horse, an interior axial tip whose
    polygon had grown sideways *and* upward — closest hinge at r, upward
    axial crossing the horizontal spine to a hinge at 2r). Traced by tip
    class: an **interior** tip may have arms (band-columns or band-rows)
    along one axis only — two perpendicular expansions put two zero-lines in
    one skeleton face; an **edge** tip may grow along its edge or away from
    it, not both (the mirrored polygon's spine leaves the tip and a raw
    axial overruns r); a **corner** tip may grow along both edges — both raw
    axials are then blocked by boundary spine pieces and the flap is blunt
    (its tip is a raw edge at `a = 0`), which is valid. Corner-region cells
    remain free; `propagate`'s arc-length check (§11.7) stays the ground
    truth. `validate` reports a violation as `arms:`.
13. **Tip position (v1 restriction, exact in `validate`).** A tip lies on a
    paper edge, or at least `r` from every edge, or exactly on the paper's
    midline (`x ∈ {0, N} ∪ [r, N − r] ∪ {N/2}`, same for `y`: a symmetric
    clip keeps the tip at the centre of its clipped square, so the spine
    still passes through the tip); `validate` reports `tip-position:`
    otherwise, so the
    packer's candidate range is a necessary condition, not a search
    restriction. A tip nearer than `r` to an edge is geometrically fine in
    tree theory (its axial toward the edge ends on the raw edge; the flap
    is length `r` with a bite out of one side) but its ridges are NOT the
    straight skeleton of the clipped polygon (measured: horse, guinea_pig,
    frog — the clipped rectangle's spine sits at mid-height, not at the tip,
    and a launch loops back to the tip). They are the skeleton of the tip's
    full `2r × 2r` square restricted to the paper — the generalisation of
    the §10.1 mirror. Deferred: implement that completion and lift this
    rule.
14. **The elevation field is global (Lang §13.5).** Axials keep going across
    hinges and rivers into neighbouring polygons; "the axial contours from a
    hinge polygon often do NOT line up with the axial contours from the
    neighboring polygon" and that is normal — two misaligned axials leave a
    half-elevation crest between them, a folded pleat. A face's profile is
    therefore read from the global contours lying in it (and contours ending
    at its own vertices), never from a per-polygon field. Collinear runs are
    merged into lines for seeding, so a crest at a T-junction launches. Tip-
    line raw edges are registered like river raw ends (level runs), which is
    how a flap grown along its raw edge shows its conflict with a neighbour
    pinned at 0 — the corpus's dominant failure and a Ch. 14 level-shifter
    site. Plan view is a *preference*: centre-column pieces of every role are
    CSP variables over {F, M, V} with F tried first for column contours;
    Maekawa and Kawasaki are checked inside the search (Kawasaki depends on
    which pieces are unfolded). Measured on the 15 packable subjects before
    any packer preference: 4 assign cleanly, 11 collide at a paper edge.
15. **Packer acceptance is contour-aware (bounded).** After `validate`, the
    packer runs the skeleton and `propagate`; a collision continues the
    enumeration (next fill / placement / hub map / river) up to a bounded
    number of tries per N, then returns the first valid layout so the failure
    is recorded at the contours stage. Gap fill ranks units that run along a
    corner/edge flap's raw edge last. This is search, not a bar change: a
    subject with no collision-free fill still records `contours: collision`.
16. **§5.5 CSP: local flat-foldability, not Maekawa + Kawasaki.** Maekawa
    and Kawasaki are necessary; the big-little-big lemma (a strict-minimum
    sector must be flanked by opposite labels, applied through the crimp
    reduction) is what `cp_audit` and Oriedita actually test. Measured on the
    first ten emitted folds: Maekawa 0 and closure clean, every one REAL with
    `LITTLE_BIG_LITTLE`. The CSP's fully-bound vertex check is the project's
    own oracle `cp_audit.arrangement_ok_at_vertex` (reused, unchanged), so the
    compiler cannot disagree with the validator; BLB is also a partial prune.
17. **FOLD custom block.** Oriedita's reader refuses unknown bare keys; the
    block ships as `"box_pleat:layout"` (FOLD custom-field namespacing).
18. **The "up to 40%" scale penalty attributed to Lang does not exist.** Ch. 13
    (p. 573) says only that box pleating "must be, by definition, less
    efficient" than circle/river packing, and that "the penalty is often very
    small". Measured here over the 16 subjects that reach a layout:
    `ratio = scale_bp / scale_tm` has mean **0.952**, median 0.885, min 0.732
    (spider), max 1.297 (lizard), with **6 of 16 at or above 1.0** — i.e. this
    compiler's flaps are on average ~5% shorter per unit of anatomy than
    TreeMaker's, and on six subjects longer. Lang's qualitative claim is
    confirmed; the invented percentage was not his and must not be requoted.
