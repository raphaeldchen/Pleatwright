# Pleatwright: packing branching hub graphs (nested pockets)

**Problem (2026-10-10).** Pleatwright's packer (`mcp_harness/pleatwright/pack.py`)
lays rivers as parallel full-width bands, so a tree's hubs (branch points) must
form one chain (spec 2026-10-06, deviation 1). A user "moose" whose head carried
forked antlers failed with "hub graph is not a path": `head` joined the body and
both antler bases. PR #204 made that refusal legible (`pack.chain_problem`: a
warning at review, and a refusal at packing that sends the human back to the
tree). This spec makes such trees pack.

**Base branch note.** PR #204 was merged into `claude/app-model-switch` after
that branch had already been merged to `main` (#203), so `chain_problem`,
`stick.load_tree` and `tests/test_pack_chain.py` are not on `main`. This work
fast-forwards onto `0e5a4966` (#204's merge commit). Its PR to `main` therefore
carries #204 as well.

## Decisions (owner, in the design discussion)

| question | decision |
|---|---|
| scope | **symmetric animals** are the design and measurement target: hubs on the mirror axis plus *mirrored pairs of hub subtrees* (left/right antlers, toed paired limbs) |
| test trees | **named edits of artifact trees only** (`antlered`, `toed`, `lopsided`); no new fixture corpus |
| approach | **nested pockets** (below), used only for branching hub graphs |
| #204's guard | **retired.** The nested packer lays out every hub tree, so `chain_problem` has nothing true left to say. A first draft kept a narrower rule (a parent plus at most one unpaired child hub). Measured, it refused 3 of the 74 branching edits, and the 2026-10-10 moose reported `withers` joining three hubs, the shape that rule refuses (its tree was not kept, so this is inferred from the report). |

## Prior art (CLAUDE.md §0)

| source | what it says | adapted / rejected |
|---|---|---|
| COrigami §3.2, App. E (arXiv:2606.26299v1, read in full) | Very thin: the first river is straight or L-shaped; each later river is placed by "a wall-following algorithm that traces the contour of previously placed elements"; newly enclosed pockets are packed immediately; gaps are closed by flap expansion. App. E holds only E.1 (`G_init`). Branching hubs, hub pairs, elevation and the scoring rule are not described. | **Adapted:** pack each pocket as soon as its enclosing river exists; flap expansion as gap fill (both already in `pack.py`). **Rejected for now:** rivers snaking around flaps (no algorithm published; see *Fallbacks*). |
| Box Pleating Studio (M.-T. Tsai), read from source: `core/design/tasks/roughContour.ts`, `plugins/optimizer/src/branching/contour.h`, `core/design/health/riverCorner.ts` | A hub's contour is the union of its children's contours, each expanded by the edge length; the river is that contour minus the children. Branching is native (several components, holes). Every right-angle river corner inside the sheet must have an inward 45° ridge. | **Adapted:** a river is the L∞ offset band of its child's region; the corner rule becomes our parity check on a band's outer corners. **Rejected:** Pythagorean stretches and junction gadgets (Euclidean separation, non-orthogonal). |
| Archived `box_pleat` compiler (`archive/treemaker-box-pleat:mcp_harness/box_pleat/`) | A river was a set of cells: a band or a single L-bend, always a chord from the axis to an edge (`pack.py:71-104`), self-mirrored (`layout.py:232`). Chords from the axis give a path-shaped region graph, so it could not branch either. Leaf pairs on different hubs were refused (`AsymmetricPair`). | **Adapted:** the constant-width multi-bend idea of `river_ridges` (`skeleton.py:264`) and the paper-edge vs hinge classification of `hinge_segments` (`layout.py:30`). Nothing to adapt for hub pairs. |
| Lang & Demaine, "Facet ordering and crease assignment in uniaxial bases" (OSME 2006); Demaine, 6.849 (2012) | Hinge creases are lines of constant depth; in box pleating flaps are squares and rivers are "orthogonal channels of constant width". | Confirms the model; nothing new to build. |
| Demaine, Demaine & Ku, "Folding any orthogonal maze" (OSME 2010) | T and cross junction gadgets with fixed interfaces, for extruded mazes (not uniaxial bases). | Rejected: a different base family. |
| Floorplanning: slicing trees (Wong & Liu 1986), nested treemaps (Lü & Fogarty 2008) | A hierarchy of rectangles; nested treemaps put a border band around each internal node. | **Adapted:** the pocket hierarchy below *is* a nested treemap whose borders are rivers, clipped where they meet the paper edge. |
| This repo, 2026-10-10 probe (throwaway, not committed) | `antlered("dog_0")`: collapse each antler to one flap of length river + tip, pack with today's packer, carve the flap's region into a width-2 band plus a pocket, split the pocket between beam and palm. `base.build` certified it at N=72 (365th candidate, unmirrored rung), with the antlers stacked as full-width rows. | Shows that offset bands built from rectangles certify under the unchanged elevation rule, and exposed the one `base` coupling (Section 1). Rejected as the main approach because region sizes are fixed before the subtree is known. Kept as a fallback rung idea. |

## Section 1: data model

**`pack.Region`** gets one optional field; every existing positional call is
unchanged.

```python
more: list = field(default_factory=list)   # further rectangles of the SAME region

@property
def rects(self):
    return [self.rect, *self.more]
```

* A **river band is one `Region`** (`kind="river"`). Its rectangles are the
  band's pieces: strips and corner squares, non-overlapping. Its
  `vlines`/`hlines` are the band's **outer** hinge lines, which are the sides
  of the child's region that are not paper edge. `base._dist` (min L∞ distance
  to the region's lines) is then exactly the offset-band elevation. In a
  corner square it equals `min(dist to the two outer lines)`, with the 45°
  ridge on the diagonal. `u_line` stays `None` for nested bands; nothing reads
  it outside `pack.py`.
* **`base.build`** iterates `r.rects` in its ownership loop. `diff_region`
  keeps comparing region indices, so a band's pieces never meet at a hinge. A
  band split into separate Regions would draw spurious green hinges in
  `packing_cp.svg`. Single-rectangle regions behave exactly as before.
* **`pack.Layout`** gains `pockets: list` (default `[]`) of
  `(hub, rect, sides)` for tests and diagnostics. Nested layouts set
  `bands = slabs = []`. Only `pack.py` reads those two fields.
* **`pack.hub_pairs(con)`** derives hub pairs from leaf pairs, so the tree
  schema does not change. Two child hubs `a`, `b` of the same parent are
  paired when all three hold:
  * their rivers have equal length;
  * the leaves of the two subtrees match one-to-one through `con.pairs`;
  * the same holds recursively for their child hubs.

  `tree.json` keeps carrying leaf pairs only.

## Section 2: the nested search (`pleatwright/nest.py`)

**Dispatch.** `pack.candidates` first checks the hub graph:

* path-shaped: today's code, unchanged;
* otherwise: `yield from nest.candidates(con, N_min=..., N_max=..., per_N=..., symmetric=...)`.

The pipeline's ladder (symmetric → asymmetric → every length doubled) and
`max_candidates` apply unchanged. All 51 artifact trees are path-shaped
(measured), so their outputs are byte-identical by construction.

**Unit tree.** The layout is rooted at `con.root`, which is on the axis
because paired hubs share a parent. Each hub *h* owns:

* its **flap block**, `_items(con, h, symmetric)`, which may be empty (the
  moose's `head` has no flaps of its own);
* one **axial child** per unpaired child hub;
* one **pair child** per `hub_pairs` entry under *h*.

**Pocket** = `(hub, rect, sides)`, where each of top/bottom/left/right is
`paper` or `hinge`. The root's pocket is the whole paper. A pocket is a
vertical stack of strips: the flap block (if non-empty) and one strip per
child, in an enumerated order. A hub's flap block is one contiguous strip.

* **Flap block in an axial pocket**: `_pocket_solutions` as it is. Axial
  pockets always span `[0, N]` with paper on the left and right, which is
  all it assumes.
* **Axial child strip** `[x0, x1] × [a, b]`. The child's region is the whole
  strip. Its band runs along every strip side that is not paper edge, and the
  child's pocket is the strip shrunk by the river length W on those sides.
  The child's pocket is then filled recursively.
* **Pair child strip** (axial pockets only), split at `x = N/2`. The left
  child's region is `[0, N/2] × [a, b]`, with the axis side a hinge, and it
  is filled recursively. The right child is the left child's whole solution
  mirrored (`x → N − x`), with chain ids swapped through the hub-pair and
  leaf-pair maps.
* **Off-axis pocket** (inside a pair child). The new
  `_row_concrete_span(items, x0, x1, left, right, h, top, bot, y_paper, p)`
  generalises `_row_concrete_asym` from `[0, N]` to `[x0, x1]`.
  * An edge column on a hinge side puts its vline on the boundary and behaves
    as an inner column.
  * Virtual hinges past an edge are allowed on paper sides only, as today.
  * Child hubs of an off-axis hub stack as full-pocket-width strips. There is
    no pairing off-axis.

```
 y=0  ┌──────────────── hip region (band 8 on bottom) ───────────────┐
      │   tail · paw_rear_L/R rows                                   │
      ├░░░░░░░░░░░░░░░░░░░ hip river, W=8 ░░░░░░░░░░░░░░░░░░░░░░░░░░░┤
      │   body flap rows: paw_front_L/R                              │
      ├▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ head river, W=9 ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒┤
      ├▓▓▓▓ antler_L, W=2 ▓▓▓▓▓▓▓▓┬▓▓▓▓▓▓▓ antler_R, W=2 ▓▓▓▓▓▓▓▓▓▓▓▓┤
      │ beam_L │ palm_L         ▓▓│▓▓          palm_R │ beam_R       │
 y=N  └─────────────────────────┴┴──────────────────────────────────┘
                              x=N/2 (head hinge)
      antlered("dog_0") at scale 1, schematic (not to scale)
```

**Sizing.** For each even N from `grid_init(con)` (App. E.1 already covers
general trees), a recursive `fill(pocket)` does the following:

1. Enumerate strip orders.
2. Choose strip heights with the same "reach" dynamic programme over y that
   the slab code uses.
3. Memoise feasibility on `(hub, width, height, sides, parity)`, as today's
   `fcache` does.

A child strip needs at least W on each hinge side plus one cell. Per-N caps
match today's: `per_N` layouts, a few height tuples, 8 pocket solutions each.

**Acceptance per candidate** (before `base.build`):

* every flap region: `_max_d == L` and `_parity_ok`;
* every band: maximum `d == W`, and `_parity_ok` on its outer lines. This is
  BP Studio's river-corner rule: an outer corner at `(x, y)` gets its 45°
  ridge only if `x + y` is even.
* The row packers carry the parity class `p` as today. An off-axis pocket's
  vertical hinge must also lie on `p`.

`base.build` remains the final judge (isometry and continuity), as in the
pipeline today.

## Section 3: retiring #204's guard

Every hub tree has a nested layout structurally. An unpaired child hub is a
full-width strip on the axis, and a hub pair is a strip split at the axis. A
tree can therefore fail to pack only because the search ran out (grid cap or
candidate budget), the same as any path-shaped tree. #204's structural
guard has nothing true left to say, so it goes.

**Removed:**

| piece | where |
|---|---|
| `chain_problem` | `pleatwright/pack.py` (`_hub_graph` stays; `hub_path` uses it) |
| the `pack_problem` state key and the review WARNING | `gated_pipeline._draft`, `gated_pipeline.summarise` |
| `_pack_problem` and the pre-fold refusal | `app/server/pleatwright_app/tools.py` `fold` |
| the `packable: false` round flag | `tools.present`; `app/web/src/runStore.ts` ("can't pack yet", "packs: no") and its test |
| #204's tests of the above | `test_gated_pipeline.py::test_review_warns_when_the_tree_cannot_be_packed_yet`, `test_guided.py::test_an_unpackable_tree_is_flagged_and_its_failure_returns_to_review`, `test_pack_chain.py` (rewritten, Section 4) |

**Kept from #204** (generic, not tied to the guard):

* `stick.load_tree`;
* `review_again` reopening an approved tree;
* tree rounds labelled with the model that wrote them;
* the "Back to the tree" button label for `retry == "review"` (a failed
  `revise_tree` still uses it);
* `guided.retry` no longer requiring an LLM key for `review`.

**Unchanged.**

* `hub_path` and its "not a path" `PackError`. Packing reaches it only for
  path-shaped graphs, so that error can no longer fire from packing.
* A branching tree the search cannot pack fails at the packing stage like
  any other tree: CLI exit 1; in the app, `stage_failed` for packing with its
  usual retry.

**Docs.**

* Spec 2026-10-06 deviation 1 is rewritten. Rivers are nested offset bands,
  and mirrored hub pairs split at the axis. The remaining deviation is that
  rivers never snake around flaps. Its sentence about `chain_problem` is
  replaced.
* CLAUDE.md §2's `pairs` bullet gains one sentence: hub pairs are derived
  from leaf pairs.

## Section 4: testing and acceptance

**Named edits**, in `tests/test_pack_chain.py` beside `antlered`, applied only
to artifact trees:

| edit | definition | branching members of the 51 (measured 2026-10-10) |
|---|---|---|
| `antlered(roll)` | as in #204: `head` gets two antlers (river 2), each forking into beam and palm (3), paired | 35 (every roll with a `head` node) |
| `toed(roll)` | each leaf of the roll's longest declared leaf pair gets an inner and an outer toe (2), paired across; pairs naming missing nodes (octopus) are skipped | 39 (11 more stay path-shaped and keep the old code) |
| `lopsided(roll)` | `antlered` with the right antler's river set to 3, so no hub pair exists | the unpaired-siblings case: both antlers become axial strips |

**Unit tests**, written test-first:

1. `hub_pairs`:
   * `antlered("dog_0")` → `{(antler_L, antler_R)}`;
   * `toed` → its two limbs;
   * `lopsided` → none;
   * hub pairs inside a path-shaped artifact tree are not asserted, since
     path graphs never reach `nest`.
2. Rewritten `test_pack_chain.py`:
   * all 51 artifact trees are still path-shaped, so `hub_path` succeeds on
     each (this is the dispatch's precondition for byte identity);
   * `hub_path` still raises on `antlered("dog_0")`;
   * `pack.candidates` yields for `antlered("dog_0")` and for
     `lopsided("dog_0")`.
3. `_row_concrete_span` on the antler pocket items:
   * columns tile `[x0, x1]` exactly;
   * every column has `_max_d == L` and `_parity_ok`;
   * a hinge side carries a vline on its boundary;
   * no virtual line lies past a hinge side.
4. `base.build` with multi-rectangle regions, on the first certified nested
   layout of `antlered("dog_0")`:
   * every cell is owned once;
   * `boundary_edges` never separates two cells of the same region;
   * every band rectangle carries its region's outer lines.
5. Nested symmetry: that layout maps to itself under `x → N − x` with paired
   chains swapped.
6. Dispatch: with `nest.candidates` monkeypatched to raise,
   `pack.candidates` on `dog_0` still yields.
7. End to end: `pipeline.run` on `antlered("dog_0")` (written to
   `tmp_path/tree.json`) writes the four files, and every solving vertex is
   locally flat-foldable. The global verdict asserted is the one measured
   during implementation.

**App / review tests.** #204's two guard tests are deleted (Section 3). They
are replaced by one app test (`test_guided.py`): an approved `antlered` tree
goes to packing with no refusal and writes `packing_cp.svg`, with
`certify_global=False` as the other app tests use. The web test for the
`packable` summary is removed with the field.

**Byte-identity gate** (before the PR):

* `python -m pleatwright fold` on all 51 artifact trees, with every file
  compared (`cmp`) against `~/Desktop/origami_samples_artifact_trees`:
  **204/204 identical**;
* CI's two pinned `packing_cp.svg` hashes (bird_1, starfish_1) stay green.

**Acceptance.**

* **Hard gate.** `antlered("dog_0")` folds end to end through `fold` on its
  `tree.json`, to the same certification standard as the 51: solving locally
  flat-foldable, and the global verdict recorded.
* **Probe, reported with no pass threshold.** Run over all 74 branching edits
  (35 `antlered` + 39 `toed`), plus `lopsided` on the same 35 rolls as the
  unpaired-siblings column, and save to
  `docs/superpowers/evidence/2026-10-10-branching-packer/`. Per tree it
  records:
  * packed or not, and the rung;
  * N against the unedited roll's N (the cost of branching);
  * candidates tried and pack seconds;
  * solving flat-foldability and the global verdict;
  * for a miss, where the search died.
* **Looked at, not only scored.** View the overview PNGs of
  `antlered("dog_0")`, one `antlered` horse and one `toed` crab.

## Fallbacks (decided by the probe, not now)

* **Collapse-and-carve** (the probe above) as an extra ladder rung for
  branching trees the nested search misses.
* **Wall-following rivers** (COrigami's, with BP Studio's contour union) if
  misses cluster where a river would have to bend around a flap. That
  approach makes pockets rectilinear polygons, which needs a new pocket
  packer, so it gets its own spec.

## Out of scope

* Optimising for asymmetric branching. Such trees pack through axial strips
  and the unmirrored rung, and `lopsided` measures them, but nothing is tuned
  for them.
* Splitting a hub's flap block around its children; pairing inside off-axis
  pockets.
* Any change to solve, shape, fold or render. They consume only the Base.
* A branching fixture corpus. If wanted, it needs the owner's sign-off
  (CLAUDE.md §5).
