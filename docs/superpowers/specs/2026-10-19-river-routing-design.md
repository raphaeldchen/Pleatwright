# River routing: anchored child pockets (efficiency slice 2)

Status: design, approved in conversation 2026-10-19; builder-checked.
Research behind it: `reports/Box pleating efficiency techniques.md`,
`research_notes/Box pleating efficiency techniques/` (in particular
`river_routing_prior_art.md`, written for this slice), and the slice-1 spec
`docs/superpowers/specs/2026-10-16-packing-layout-choice-design.md`.

## 1. Why

Every hub after the first gets a strip that spans its parent's whole pocket.
On a path-shaped tree (all 51 artifact trees) that is a full-width slab plus a
full-width river band (`pack.candidates`); on a branching tree it is a
full-width strip of the parent pocket with an offset band on its hinge sides
(`nest.py`). Either way, a hub with two small flaps still pays for a strip N
cells wide, and its flaps expand to fill it. Measured on the symmetric
layouts (`docs/superpowers/evidence/2026-10-16-layout-choice/bp_eff.jsonl`):

* ant_0: N = 102, slabs 15 / 70 / 13 tall; 76% of the sheet is expansion
  slack, one flap 11.3× its minimum polygon.
* the 39 trees with more than one hub: median slack 0.39; the worst are
  ant_0 0.76, crab_3 0.70, scorpion_2 0.68, lizard_1 0.67, ant_2 0.62,
  spider_1 0.62.
* the 12 single-hub trees (octopus, scorpion_0/1, spider_0, starfish,
  horse_0, dolphin_1, ant_1) have no river; this slice cannot change them.

Every published source that bends rivers does it the same way for this
purpose: the river wraps a pocket of flaps in a corner or against an edge, so
the river is about `W·(pocket width + height)` long instead of `W·N`, and the
grid can shrink (§3). A smaller grid on the same tree is a larger model from
the same sheet *and* fewer layers in every flap, because the tree's lengths
are fixed in grid units while the paper shrinks.

The owner has not folded models yet; the measure of success therefore has to
be computable (grid, certification) plus looking at the outputs. An origami
artist the owner knows may review crease patterns afterwards (§9).

## 2. Goals, non-goals, anti-goals

Goals (owner, 2026-10-19: "smaller grid on the multi-hub trees, every tree
still certified, nothing else changes")
1. The packer can place a child hub's pocket in a box that does not span its
   parent's pocket, wrapped by an L-, U- or ring-shaped river (§4).
2. A tree gets such a layout only when it packs on a strictly smaller grid
   than the grid it is folded on today; every other tree's output is
   byte-identical (§5).
3. Every changed tree still certifies (§8).
4. A small before/after packet for an artist's review is produced at the end
   (§9).

Non-goals (later slices, or never)
* Meanders, or any shape whose parent-side bank has a reflex corner (S-bends).
  They need `base._dist` to measure L∞ distance to bank *segments* rather than
  to full hinge lines, and they move thickness from limbs into the body
  without changing N; no source treats them as more than gap filler, and
  Wong's hex paper calls the result an inconvenient concentration of
  thickness. Not measurable without folding, so deferred.
* Wall-following around non-rectangular unions of placed children (the
  general form of COrigami's later rivers; `river_routing_prior_art.md`
  §7.3 item 2).
* Hub-subtree pairs (`nest` 'pair' strips) placed beside flaps.
* Level shifters, Pythagorean stretches, 22.5°, changes to the slice-1 choice
  rule, speeding up `_pocket_solutions`, any app or CLI surface change.

Anti-goals (a failure even if it works)
* Any output change for a tree whose grid does not shrink.
* A tree that folds today failing, or folding on a larger grid, because the
  new search spent its candidates or ticks first.
* Any change to `base.py`, `solve`, `shape`, `fold` or `certify/`.
* A layout offered as the *symmetric* option that is not mirror-symmetric.
* Packing becoming slower than today's worst case (§5.3).

## 3. Prior art (CLAUDE.md §0)

Full notes, with evidence tags: `research_notes/Box pleating efficiency
techniques/river_routing_prior_art.md`.

| source | what we take | what we leave, and why |
|---|---|---|
| COrigami §3.2 (arXiv:2606.26299) and its 18 released `packing_cp.svg` (probe: `docs/superpowers/evidence/2026-10-19-river-routing/corigami_samples/`) | the shape family. 22 bent regions in 11 of 18 samples; 21 are constant-width bands with 90° bends only, every one touching the paper edge, none closed: **L** around a corner pocket (gecko toes, moose tines), **Π/U** around an edge pocket, Π with outward feet (rock lobster, nested). Bends enclose pockets so they pack in 2-D. | the incremental "wall-following" algorithm, which is unpublished beyond one sentence; Π-with-feet (needs non-rectangular parent remainders); slack stays in flaps there too |
| Box Pleating Studio (Tsai, MIT; `src/core/design/tasks/roughContour.ts`, `utils/expand.ts`, `graphics.ts` `riverRidge`, `health/riverCorner.ts` at `ae73ae7`) | a river's course is its child's region expanded by the river's length; for one rectangle that is exactly `nest.band()`. Its optimiser fixes the sheet size first and treats bends as a cost: a bent layout is used only when it beats the bend-free one on grid size (§5.2). | the corner-pairing health check (`riverCorner.ts`): `band()` is constant-width by construction, so it cannot fail; stretches/GOPS (slice 3+) |
| B. Wong, Origami Design Class 4.2 / 5.4 (slides + captions) | bending full-width rivers into nested U shapes to remove side gaps (5.4); bends either let a flap fill the gap or move thickness into the river (4.2) | the "move thickness into the river" use (meanders, non-goal); his 2020 `boxpleater-beta` perimeter-walk packer (no explicit rivers, no licence) |
| Lang, ODS2 Ch. 13–14 | the rule that each bend carries a 45° ridge from corner to opposite corner, which `base.build` already derives from the elevation field | meanders: the text was not reachable; only page numbers were found |
| Demaine, Demaine & Ku, "Folding any orthogonal maze" (Origami⁵) | nothing to port: its corner/T/cross gadgets solve interface compatibility, which our single elevation field already guarantees | its gadget library (different base family; also rejected by the 2026-10-10 spec) |
| Tsai, "Edge-River Method" blog | its parity rule (two copies of a vertex an even taxicab distance apart) is `pack._parity_ok`, already applied | — |
| This repo, spec 2026-10-10 (branching hub packer) | `band()`, `mirror()`, `_row_concrete_span`, and its recorded fallback "wall-following ... makes pockets rectilinear polygons, which needs a new pocket packer" | that fallback's cost: we keep every pocket a rectangle by cutting the parent's remainder into rectangles (§4.2) |

Why `base.build` needs no change: `base._dist` is the minimum distance to a
region's full hinge *lines*. For a band built by `nest.band(box)` the hinge
lines are the box's own hinge sides and the band lies inside the box, so the
line distance equals the true L∞ distance to the parent-side bank whenever
the box is at least `2W + 1` across in each wrapped direction (`band()`
already requires a non-empty pocket). L, U and ring bands are all of this
form. `base.build` still verifies isometry and continuity on every
candidate, so a wrong shape fails loudly.

## 4. The layout family

### 4.1 Today, for reference

`nest._Search.fill(hub, box)` cuts a pocket into a vertical stack of
full-width strips: the hub's flap block (`('flaps',)`, packed by
`_pocket_solutions`), one strip per child hub (`('child', river)`: `band()`
around the strip's hinge sides, the child's pocket inside), and one strip per
mirrored hub pair on the axis. `pack.candidates` (path-shaped hub graphs) is
the special case of full-width slabs and bands down the hub path.

### 4.2 New: the beside strip

A new strip kind, `('beside', river)`: a full-width strip of the pocket, of
height h, cut left to right into a **child box** C for that child hub and one
or two **flank blocks** of the parent hub's own flaps. C's top and bottom
sides are the strip's (paper where the strip touches a paper side of the
pocket, else hinge); its left and right sides are the pocket's side kind when
C touches the pocket's side, else hinge. The river is `band(river, W, C)`,
which gives:

* an **L** when C sits in a corner of a pocket with two paper sides,
* a **U** when C sits against one paper side,
* a **ring** when C touches no paper side (exists today).

The child's pocket inside the band is filled recursively by `fill`, so beside
strips nest.

Arrangements:
* **Unmirrored mode, or an off-axis pocket**: `[C | F]`, `[F | C]`, or
  `[F1 | C | F2]`, C at any column whose parity `band()`/`_parity_ok` accept.
  Flank blocks and the child pocket are spans with hinge sides, packed by the
  existing `_row_concrete_span` (the child pocket is filled with
  `axial=False`). No new row-model code.
* **Symmetric mode, on-axis pocket**: `[F | C | mirror(F)]` with C centred on
  x = N/2. F holds the left members of some of the hub's mirrored pairs,
  packed as an off-axis span (`_row_concrete_span`, as `nest` packs a pair
  half today); the right block is `mirror(F)` through the pair map. Axial
  flaps never flank; they stay in the hub's ordinary flap strip.
  The child pocket inside C is a centred span `[a, N − a]` with hinge sides,
  and it must be packed mirror-symmetrically. **No row builder does that
  today**: axial packing (`_row_concrete` with `hw = N // 2`, laid out by
  `_row_regions` from x = 0) assumes the full paper width with paper or
  virtual hinges at its ends (`pack.py` `_pocket_solutions`, `_row_regions`).
  This slice adds a **new** mirrored span row builder (the symmetric
  counterpart of `_row_concrete_span`: pairs in mirrored columns, at most one
  axial column centred, hinge sides on the span's ends) as a new function in
  `pack.py`, plus the matching region layout. `_row_concrete`,
  `_row_concrete_asym`, `_row_concrete_span` and `_row_regions`' existing
  behaviour are not modified, so today's layouts stay byte-identical. *(Call
  made after the builder check: this is the only route to a smaller
  symmetric grid, which 32 trees use today.)*

The hub's items are partitioned between the flank block(s) and its ordinary
flap strip; the flap strip may become empty if every item flanks. Every flank
block holds at least one item, because a cell no region owns fails the tiling.
One child per beside strip. Which items flank, in what order, and how many
partitions are tried is a bounded enumeration left to the builder (§11),
under the work budget of §5.3.

### 4.3 Path-shaped trees

All 51 artifact trees are path-shaped, so the new family must also run for
them. It runs as the `nest` recursion from `con.root` with beside strips
enabled (a hub path is a hub tree). `pack.candidates` is **not** changed: it
still sends only branching trees to `nest`
(`test_a_path_shaped_tree_never_enters_nest` stays true). The beside family is
a separate generator (e.g. `nest.beside_candidates`) that the pipeline calls
on its own (§5).

**The beside family yields only layouts with at least one beside strip.** A
plain nest layout of a path-shaped tree (no river bend, only a different strip
order than the slab programme) is not river routing; it is neither yielded nor
credited to this slice. *(Call made after the builder check.)*

## 5. Search integration

### 5.1 Today's search runs first, unchanged

`pipeline.pack_options` first runs exactly today's search (symmetric rung,
capped and budgeted unmirrored rung, doubled rung), producing today's options
S (symmetric), U (unmirrored) and today's chosen grid C under the slice-1
rule (`--layout auto`). Nothing in that search changes: same candidates, same
`MAX_CANDIDATES`, same `SMALLER_WORK_BUDGET`, same caps. So no old result can
be lost to the new family, and trees with no beside result are byte-identical
by construction.

### 5.2 Then the beside search, which must beat C

Only for trees with at least one child hub, and only when today's search found
a symmetric or unmirrored option (the doubled rung is used by none of the 51
trees today and gets no beside search):

1. Beside symmetric search, `N_max = C − 2` → S_b, or none.
2. Beside unmirrored search, `N_max = C − 2` → U_b, or none.

When today's search found nothing at all (e.g. the branching edits past the
grid cap), both beside searches run with today's `n_max` instead of C − 2.

The new options are S' = S_b if it exists, else S; and U' = the smaller-grid
of U and U_b. The slice-1 rule is applied to (S', U') exactly as today (the
10% threshold, its verdicts, the app card). Because every beside result is
strictly below C, the chosen grid never grows:

* S_b found: the rule picks S_b (< C) or an unmirrored option at least 10%
  smaller still;
* only U_b found: the rule picks U' (< C) if it is ≥ 10% smaller than S',
  else S' = S, i.e. today's choice;
* neither: today's options, today's choice, byte-identical outputs.

Consequences, accepted *(calls made after the builder check)*:

* A multi-hub tree that has no symmetric layout today (crab_3, dog_2,
  elephant_3, frog_0, spider_2 among the 51) may gain one below C; its verdict
  then moves from `only_unmirrored` to the slice-1 rule's `ask` / `symmetric`,
  and the app may show the layout card where it did not before. That is the
  slice-1 rule doing its job with a better option.
* A tree whose chosen layout stays the same may still record a different
  `n_smaller` (a beside U_b that lost the 10% rule). Record fields may change;
  the four output files may not.

### 5.3 Budget: ticks and a candidate cap

Each beside search runs under its own deterministic tick budget
(`pack.work_budget`) **and** its own cap on candidates passed to
`base.build`, because `base.build` spends no ticks
(slice-1 evidence README) and failed builds cost wall time a tick budget
does not see. When either is spent, that beside search stops with no result.
Calibrate both as slice 1 did (counts, not seconds;
`docs/superpowers/evidence/2026-10-16-layout-choice/README.md`) so that no
tree's `pack_secs` exceeds about 165 s on the reference Mac, today's ceiling.
Single-hub trees never run a beside search (no child hub), so the five slowest
trees today (spider_0, scorpion_0/1, octopus_2, octopus_3, all single-hub)
are unaffected.

## 6. Phase 0: measure before building the rest (kill switch)

Phase 0 builds the whole packing path behind an off-by-default switch
(e.g. an environment variable or a `pack_options` argument): the beside
generator (§4), the new mirrored span row builder, and the §5 extension of
`pack_options`, with their unit tests. Order: the unmirrored arrangements
first (existing row code only), measured; then the symmetric ones. Then run
`pipeline.pack_options` (packing only, no solve) on the 39 multi-hub
artifact trees with the switch on and off, and record per tree: S, U, C and
S_b, U_b, the new chosen grid, ticks, candidates built and seconds.

* **Stop** if fewer than 5 of the 39 trees get a smaller chosen grid (both
  arrangements measured). Write up what was measured in the evidence folder
  and report to the owner; leave the switch off and do not proceed.
* Otherwise turn the switch on by default (or remove it) and continue to §8.

The probe is the real `pack_options` path with the real `base.build`, never a
copy: a re-implemented probe has misled this project before.

## 7. Records and metrics

* The run record's `layout` block (`pipeline._layout_record`) gains `family`:
  which family produced the chosen layout (`"today"` or `"beside"`; names are
  the builder's), and the beside searches' outcomes (S_b and U_b grids, or why
  there are none: `none_below_cap`, `budget`, `no_child_hub`), in the style of
  `n_smaller`.
* `efficiency.metrics` gains `river_corners`: the number of right-angle
  corners of river bands strictly inside the paper (BP Studio's tidiness
  measure), recorded only, as a crease-pattern complexity guardrail.
* No other record, file or surface changes.

## 8. Acceptance

Before changing any code, fold all 51 artifact trees at `main` 4a64d1ad
(`python -m pleatwright.pipeline --out OUT --record OUT/records.jsonl`, the
slice-1 acceptance command) and keep it as the baseline; the 2026-10-06
samples on the Desktop predate slice 1 for 11 trees.

1. **Every tree folds**: the corpus run with the slice wired in has 51 records
   and no `failure`.
2. **Byte identity**: every tree whose chosen grid is unchanged has its four
   output files byte-identical to the baseline (`filecmp`, as in slices 0–1).
3. **Changed trees**: each is `CERTIFIED`, or `OVERSIZE+LOCAL_SAT` only if its
   baseline already was; all solving and shaping vertices flat-foldable; its
   `overview.png` opened and described in the evidence README (as slice 1 did).
4. **Grid report** (no threshold beyond §6): for the 39 multi-hub trees, chosen
   N before/after, N / perimeter bound, slack fraction, mean layers,
   `river_corners`.
5. **Branching edits, report only**: N before/after for the 74 branching
   edits plus `lopsided` (`tests/test_pack_chain.py`), and whether the three
   edits that exceed the grid cap today (toed crab_3, elephant_3, spider_2)
   now fit. If toed crab_3 now packs, `test_a_branching_tree_past_the_grid_cap_fails_at_packing`
   (`tests/test_nest.py`, which pins `pack_tried == 0`) is updated to an edit
   that still exceeds the cap, or to assert the new outcome.
6. **Time and determinism**: no `pack_secs` above about 165 s; two separate
   processes give identical `pack_options(...).summary()` for all 51 trees.
7. **Suites**: `make test` passes; CI's `web` job unaffected.
8. Tests use only the 51 artifact trees and the named edits of them (owner
   rule); never tardigrade / water bear.

Evidence goes in `docs/superpowers/evidence/2026-10-19-river-routing/`.

## 9. The artist packet

`docs/superpowers/evidence/2026-10-19-river-routing/artist/`:

* before/after `packing_cp.svg` and `solving_cp.svg` for three or four changed
  trees (the largest grid drops, at least one symmetric U and one L if both
  occur);
* the two current crease patterns with the highest mean layers per flap;
* a one-page README for someone who knows box pleating but not this project:
  what each file is, the grid and layers numbers, and three questions: could
  you collapse this by hand; do the river bends look like good box pleating;
  for these models, does the grid size or the flap thickness worry you more.

The review is optional and does not gate the slice; its answers feed the
choice of slice 3.

## 10. What changes where

| file | change |
|---|---|
| `mcp_harness/pleatwright/nest.py` | beside strips (§4.2) and the beside generator (§4.3) |
| `mcp_harness/pleatwright/pack.py` | a **new** mirrored span row builder and its region layout (§4.2); `candidates` and the existing row builders unchanged |
| `mcp_harness/pleatwright/pipeline.py` | `pack_options` runs the beside searches after today's (§5.2) under their budget and candidate cap (§5.3), behind the Phase 0 switch; `family` and beside outcomes in the layout record (§7) |
| `mcp_harness/pleatwright/efficiency.py` | `river_corners` |
| `mcp_harness/tests/test_nest.py` (and siblings) | unit tests for beside strips and the guards |
| `docs/superpowers/evidence/2026-10-19-river-routing/` | Phase 0 measurements, acceptance, artist packet |
| `base.py`, `solve`, `shape`, `fold`, `certify/`, `app/` | none |

## 11. Left to the builder

* The item-partition and flank-order enumeration, and its caps.
* The calibrated tick budget and candidate cap of the beside searches (§5.3),
  and whether the symmetric and unmirrored beside searches share one budget.
* The switch's form (§6).
* The exact record field names (§7).
* Rendering of the artist packet (SVGs as written, or PNGs beside them).

## 12. Calls made in design (not asked of the owner)

* Today's search runs first and unchanged, and the beside searches must beat
  today's chosen grid C (§5.1–5.2): that makes byte identity automatic and
  means no tree's chosen grid can grow. It costs extra time on multi-hub
  trees, bounded by §5.3.
* A tree with no symmetric layout today may gain one, which can change its
  verdict and show the layout card (§5.2).
* The beside family counts only layouts with a beside strip (§4.3), and gets
  a new mirrored span row builder so symmetric layouts can shrink (§4.2).
* No beside search on the doubled rung (no artifact tree uses it today).
* L-shaped (corner) layouts are unmirrored, so they only reach a model through
  the slice-1 10% rule; centred U layouts count as symmetric.
* No app or CLI change: a smaller layout simply is the packing.
* The Phase 0 probe is the real `pack_options` path behind a switch rather
  than a throwaway copy; the kill threshold is 5 of the 39 multi-hub trees.
* `river_corners` is recorded, not optimised.
