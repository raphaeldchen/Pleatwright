# River routing in box pleating: prior art for Pleatwright's next packing slice

Date: 2026-10-18. Scope: how rivers bend, wall-follow and meander in box-pleated uniaxial
design, and how that maps onto Pleatwright's L∞-elevation-field tiler (`pack.py`, `nest.py`,
`base.py`). This builds on `reports/Box pleating efficiency techniques.md` and
`research_notes/Box pleating efficiency techniques/*.md` and does not repeat them.

**Tags.**
- **[P]** primary source read directly: paper text, source code at a pinned commit, the author's
  own slides, or auto-captions pulled from the author's own video.
- **[P-sum]** primary page read only through a summarising fetch tool, so the wording may be
  paraphrased.
- **[P-measured]** my own probe on primary artefacts. Here that means COrigami's 18 released
  `packing_cp.svg` files at `~/Desktop/origami_samples/`.
- **[ASR]** auto-generated captions of Brandon Wong's videos. The on-screen drawings were not seen.
- **[S]** secondary source.
- **[I]** my inference.

---

## 0. Bottom line

1. **No published source routes rivers as a separate step.** Each one derives river courses
   from where the flaps and pockets are placed.
   - BP Studio: a river is the L∞ offset of the union of its children's rectangles [P].
   - COrigami: each later river traces the contour of the elements already placed [P].
   - Wong's 2020 packer: rivers are the gaps left between flaps on the perimeter [P].
   - Pleatsmith: a river is a strip around a hand-drawn centreline [P].

   In an elevation-field tiler, "routing a river" means choosing the shape of the child region
   it wraps [I].
2. **Two opposite effects get called river routing [I, from §§1–4]:**
   - **Hugging** a small child pocket shortens the river. COrigami's L-shaped and Π-shaped rivers
     around corner and edge pockets are the measured example. A shorter river uses less area, so
     the grid can **shrink**.
   - **Meandering or bending to fill gaps** lengthens the river's course at a fixed grid size. Slack
     moves from flap expansion into the river: flaps get **thinner** and the river (body) gets
     **thicker**. Wong teaches this and Lang names it. BP Studio flags it as "unnatural" and does
     not support it. Wong's own Origami⁸ paper calls the resulting thickness concentration
     "inconvenient" [P].
3. **The corner gadget is the same everywhere [P: BPS code, Wong slides, Pleatsmith, Lang via spec].**
   - A constant-width river bends 90°.
   - The bend's w×w corner square is split by one 45° ridge from the outer-bank corner to the
     inner-bank corner. The two corners are exactly (w, w) apart.
   - An L∞ distance field produces that ridge automatically.
   - Parity: bend corners must lie on the x+y-even lattice. Pleatwright already enforces this
     (`pack._parity_ok`), and Tsai's ERM states the same rule.
4. **The most adaptable construction for Pleatwright [I]:**
   - Let a hub's child pocket be a **sub-rectangle anchored at a corner or an edge** of the parent
     pocket, not only a full-width strip.
   - Make its river the **L∞ offset band on the pocket's non-paper sides**: an L for a corner
     pocket, a Π/U for an edge pocket, a ring for an interior pocket.
   - This is exactly the shape family COrigami's samples show (§1.3).
   - It is BP Studio's contour rule restricted to one rectangle.
   - `base.build`'s existing "min over full hinge lines" distance already handles it, because the
     parent (u) bank is on the outside of every turn.
   - True meanders (S-bends) need the opposite corner type, so `_dist` would need a
     point-to-segment L∞ distance. Treat that as a second step.

---

## 1. COrigami (arXiv:2606.26299v1)

Full HTML fetched and converted to text (115,751 chars). §3.2, App. A, App. E and App. F were read
in full. The equations in App. E.1 are MathML and were lost in conversion. Their content is
already in the earlier report.

### 1.1 What §3.2 says [P]

- **The problem.** Packing is "a discrete rectangle-packing and tiling problem on a square integer
  grid". Leaves become rectangles. Internal edges become "paths of proportional width representing
  structural rivers".
- **Pockets.** "Rivers partition the grid into bounded regions called pockets". Components
  sharing a joint must sit in the same pocket.
- **Search.** The search is "iterative backtracking search over river placements and flap
  positions". Rivers are placed one after another in a "traversal plan", an ordering of tree
  edges that respects topological dependencies.
- **First river.** It comes from an "exhaustive enumeration of candidates that span the full grid
  width or height" (straight rivers), or with a single turn (L-shaped rivers).
- **Later rivers.** "Each subsequent river is placed using a wall-following algorithm that traces
  the contour of previously placed elements". The text adds that this produces free-form paths
  that "snake around existing obstacles".
- **Pocket packing.** "After each river is placed, its newly enclosed pockets are immediately
  packed with their constituent flaps." Flap positions come either from sliding a rectangle along
  the faces of adjacency-constrained neighbours, or from brute-force enumeration. They are then
  filtered (symmetry, overlap, area feasibility) and ranked by a scoring heuristic. The heuristic
  is unpublished.
- **Gap fill.** "Tiling (via Flap Expansion)": for every unoccupied cell, the solver computes
  feasible expansions of adjacent flaps. A backtracking search then finds "a consistent,
  non-conflicting set of flap enlargements that fills every gap".
- **The packer only grows flaps.** Rivers are never widened or lengthened to fill gaps.

### 1.2 Other sections [P]

- **App. A, the stacking baseline.** "Stacking" places flaps vertically at full width and lays
  rivers "via contour-hugging around the already-placed flaps". Lang's TreeMaker manual calls this
  Kawahata's "string-of-beads". It "empirically packed 100%" of COrigami's figures but gives grids
  "well over 100". So contour-hugging rivers alone do not buy efficiency. Efficiency comes from
  packing flaps in 2-D inside the pockets [I].
- **COrigami's stated objective.** COrigami "optimizes for success rate and visual
  recognizability at the cost of efficiency". The final packing is chosen by the VLM, not by
  scale.
- **App. E** contains only E.1, the grid-size heuristic. Nothing in it covers river placement,
  ordering, widths, the wall-follower or scoring.
- **App. F, the validity reminder.** "The rivers and flaps occupy the entire paper." Hinges may
  connect, and each connected hinge component is one tree node.
- **App. F.1.1, pleats.** Pleats are a dense orthogonal grid split at hinges and ridges. A
  segment is kept if it is perpendicular to an intersecting hinge or passes through an X-vertex of
  four ridges. That is how pleats run "perpendicular to the river" inside a bent river.
- **App. G, river narrowing.** It uses two mirrored adapters, one at each end ("Mirrored adapter
  blocks at both ends"), so a narrowed river shortens.
- **§5 (the thickness passage).** One appendage "can accumulate dozens of overlapping sheets". That
  is the bulk problem. Physical layer-thinning is left to the human folder.

### 1.3 What COrigami's rivers actually look like [P-measured]

**Probe.** `docs/superpowers/evidence/2026-10-19-river-routing/corigami_samples/{regions,nonrect,dump}.py`, run on the 18 released samples (N from
30 to 60):
1. Rasterise the green (hinge) lines of each `packing_cp.svg` onto the N×N grid.
2. Flood-fill the cells into hinge-bounded regions.
3. Classify each region's shape.

**Results:**
- **22 non-rectangular regions in 11 of 18 samples.** Every other region is a rectangle.
- **Full-span rectangles** are present in 17 of 18 samples. The count per sample is 0–4; only the
  peacock has none. Most are straight rivers, though the probe cannot tell a full-width flap from
  a river without the tree.
- **Every non-rectangular region reaches the paper boundary** (0 closed loops).
- **21 of the 22 are thin constant-width bands** (width 1, 2, 4, 5 or 6), with **90° bends only**.
- **The shapes:**
  - **L-shapes (6 vertices).** These enclose a corner pocket and touch two adjacent edges. Moorish
    gecko: four width-6 L-rivers, each walling off a corner pocket of 4–5 toe flaps. Moose: two
    width-2 L-rivers enclosing the antler-tine pockets at the bottom corners. Scorpion: two
    width-5 L-rivers.
  - **Π/U-shapes (8 vertices).** These enclose an edge pocket. Ground beetle, prairie chicken,
    sawyer beetle and spiny lobster have one each.
  - **Π-with-outward-feet (12 vertices).** Each runs from the left edge, up around a side flap,
    across, down around the opposite side flap, and out to the right edge. Rock lobster has three
    of these nested inside one another (width 2 each). Between each pair sits a pair of leg flaps,
    and a 24×28 central flap (the tail) sits innermost. This is the wall-following signature: each
    river traces the contour of the flaps placed in the previous step.
- **One ambiguous region.** Giraffe weevil has a 696-cell ∩-shaped region that is not uniformly
  thin. It is either the very long neck as an over-wide river or an expanded non-rectangular flap.
  It could not be resolved without the tree.
- **Inference [I].** COrigami's wall-following output is exactly the family "L∞ offset band of an
  anchored rectangular pocket, clipped at the paper edge". No sample shows an S-meander, a closed
  ring, or a river widened to absorb slack. The slack sits in big expanded flaps (rock lobster's
  tail region alone is 672 of 1,936 cells).

### 1.4 What success looks like for COrigami [P + I]

- **Success means packability and recognisability, not efficiency.** Bent rivers serve to *enclose
  pockets* (corner toes, antler tines, leg pairs) so each pocket can be packed in 2-D, rather than
  stacking everything in full-width rows.
- **Effect on N [I].** A corner-pocket L-river is about pocket width + height long, against N for
  a straight band. On the gecko that is ≈ 10 + 24 against 44 (my reading of the bounding boxes).
  So the effect is a smaller river area, and through it a smaller N. Thinner flaps are not the
  aim; flaps still absorb all slack.

### 1.5 Not accessible

- The wall-follower's actual algorithm, its tie-breaking, which side it hugs, its stopping rule,
  and the traversal plan.
- The scoring heuristic and the code (unreleased).

---

## 2. Box Pleating Studio (MuTsunTsai/box-pleating-studio, MIT)

All files read at commit `ae73ae7df05a33e4742bd1c7ae3f808efb923a4d`.

### 2.1 Files

| file | role |
|---|---|
| `src/core/design/layout/README.md` | outline of contour tracing |
| `src/core/design/tasks/README.md` | task dependency graph |
| `src/core/design/tasks/roughContour.ts` | rough contours (the river course) |
| `src/core/design/tasks/utils/expand.ts` | `expandPath`, the axis-aligned L∞ offset, and `simplify` |
| `src/core/design/tasks/utils/invasion.ts`, `carve.ts` | junction "invasions" carved from leaf rectangles |
| `src/core/math/sweepLine/polyBool/aaUnion/roughUnion.ts` | the fast axis-aligned union |
| `src/core/design/tasks/graphics.ts` | `riverRidge`: the ridges at river corners |
| `src/core/design/health/riverCorner.ts` | the "unnatural river" detector |
| `src/core/design/health/uncovered.ts` | the gap (uncovered region) detector |
| `src/client/plugins/optimizer/src/branching/contour.{h,cpp}` | river-bend count used by the optimizer |
| `src/client/plugins/optimizer/src/README.md`, "Tidying" | the objective that minimises bends |
| `src/locale/en.json` | user-facing text for "Unnatural rivers" |

### 2.2 How a river's course is computed [P]

- **The rule.** The README says: "For rivers, those will be the union of the expanded rough
  contour of its children". The union is axis-aligned and fast, and works "in most (say over
  90%) of the scenarios".
- **Flaps.** A flap's rough contour is its AABB (point tip or rectangular tip, expanded by r).
- **The optimizer's restatement.** `contour.h` says: "The rough contour of a tree edge … is the
  union of the rectangles of all flaps under it, each expanded by its tree distance to the edge."
- **The river region** is that node's contour minus its children's contours. River corners are
  then found on both the outer and the inner paths (`riverCorner.ts`).
- **Pseudocode (`roughContour.ts` + `expand.ts`):**

  ```
  roughContour(node):                         # bottom-up via climb()
    if node is root: return []
    if node is leaf:
      outer = carveLeaf(node) if some junction invasion fits else [AABB(node)]
      return [Contour(outer, leaves=[node])]
    inputs   = concat(roughContour(c) for c in node.children)
    shifted  = [expandOuter(c, node.length) for c in inputs]   # see expandPath
    comps    = AAUnion(shifted)                # may yield several components, with holes
    return [Contour(outer=simplify(paths), children=inputs_in_comp, leaves=...) for comp in comps]

  expandPath(path, u):                       # rectilinear L∞ offset by u
    for each vertex p with neighbours p1 (prev), p2 (next):
      dx = sign(p2.y - p1.y) * u ;  dy = sign(p1.x - p2.x) * u
      emit p + (dx, dy)                       # each edge moves u along its outward normal;
                                              # convex corners stay square (L∞, not rounded);
                                              # holes (isHole) shrink by u
  river(node) = contour(node) \ union(contour(c) for c in children)
  ```

- **Interpretation [I].** contour(v) = { p : min over leaves ℓ under v of (d∞(p, rect_ℓ) − dist(ℓ, v)) ≤ 0 }.
  That is a sublevel set of an L∞ "tree-distance" field. Pleatwright's `base.build` field is the
  same object, built from the parent side.
- **No "routing" step exists.** Move a flap and every ancestor river's course re-derives from the
  union. A bend appears wherever the union of offset children has a corner.

### 2.3 How bends are represented: the ridge at each corner [P, `graphics.ts` `riverRidge`]

- **Rule.** For each right-angle corner p1 on the river's **outer** path, compute the corresponding
  point p = p1 offset by `width` along the inward diagonal:
  `getCorrespondingPoint: (p1.x - side*fy*w, p1.y + side*fx*w)`.
- **Ridge placement.** A ridge [p1, p] is added if one of two things holds:
  - a gadget's free corner lies on that diagonal (stretch patterns take priority); or
  - the **inner** path has a right-angle corner exactly at p that "faces" p1, and the segment
    does not cross any hinge.
- **Leftovers.** Inner corners left unmatched shoot ridges only to gadget free corners.
- **Result for a pure L∞ layout [I].** Every bend is a w×w square split by one 45° ridge, joining
  the outer-bank corner to the inner-bank corner. This holds for convex and concave bends alike:
  `getInwardDiagonal` flips sign for concave corners. It is Lang's "45° ridge from a bend corner
  lands on the opposite bank's corner" test (the BP compiler spec's paraphrase of ODS2 §13, [S]).

### 2.4 The "unnatural" (over-wide) river detector [P]

- **`findMissingRiverRidges`** reports, for every non-leaf node, the right-angle corners on its
  contours (outer and holes) that point into the sheet but have no ridge within 45° of the
  inward diagonal. Its comment: "In a layout that can be turned into a CP, every such corner
  inside the sheet should have one."
- **User-facing text** (`en.json` `riverCornerDetail`): such rivers "cover more regions than
  necessary, so the correct ridges cannot be determined automatically". The fix offered is to
  fill the excess regions.
- **The manual [P-sum].** The arrangement "implies meandering", which "is not yet supported". As
  a workaround, "meandering rivers might be represented … by using stub flaps".
- **`findUncoveredRegions`** is the complement of the union of the top-level rough contours
  within the sheet. "Every part of the sheet should be covered by flaps or rivers" (`en.json`).
  The fix offered is to widen flaps or add a flap.
- **Interpretation [I].** BP Studio's validity has two conditions:
  1. **Full cover:** ∪ top-level contours equals the sheet.
  2. **Constant width:** every river corner pairs with an opposite-bank corner exactly (w, w) away.

  An offset union produces excess ("unnatural") area when two children's offsets merge across a
  notch narrower than 2w, or when they meet diagonally. At those corners the outer corner's
  45° ridge finds no inner corner. That excess is exactly where a meander would be needed.

### 2.5 Bends are a cost in BP Studio's optimizer [P]

- **Stage order.** Stage 1 (pre-solve) is continuous circle/river packing; stage 2 (fitting)
  places the result on the grid; both minimise sheet size. Stage 3, **tidying**, then keeps N fixed.
- **The tidying objective,** compared lexicographically:
  1. "The total number of vertices of the rough contours of the flaps and rivers … The fewer
     vertices there are, the straighter the rivers are and the simpler the crease pattern is."
  2. The area of uncovered junctions.
- **The motive,** from the same README: after fitting, "the rivers zigzag around them instead of
  running straight".
- **How vertices are counted.** `contour.cpp` coordinate-compresses the expanded rectangles,
  rasterises them with a 2-D difference array, and counts vertices. A 2×2 neighbourhood with 1 or
  3 filled cells counts 1; a diagonal pair counts 2. The count is cached per node and only
  ancestors of moved flaps are recomputed.
- **Success for BP Studio:** (1) the smallest sheet, then (2) the **fewest river bends**. Bends are
  tolerated as a by-product of compaction, never sought.

### 2.6 What BP Studio says about thickness

Nothing in the code reads river area or flap expansion as thickness. Its validity notion does
not require a gap-free tiling. Gaps are reported, not filled automatically [P].

---

## 3. Lang: *Origami Design Secrets* 2e, Ch. 13–14, and reachable descriptions

### 3.1 Access

- **The book itself was not reachable.** Google Books's in-book search (id `6bhEatkCuWgC`) gives
  **page locators only, no snippet text** [P, index only]:
  - "meander": pp. 258, 401, 405, 654, 756.
  - "meandering": pp. 258, 263, 405.
- **Reading those pages [I].**
  - pp. 258/263: likely the circle/river chapter, where meandering rivers appear in the tree
    method.
  - p. 654: likely Ch. 14 (polygon packing).
  - p. 756: likely the glossary or index.
- **Not used:** a pirated PDF that surfaced in search, on copyright grounds.
- **Also not reachable:**
  - The Taylor & Francis chapter page ("Uniaxial Box Pleating", 10.1201/b11074-15) had no
    abstract in the fetched content.
  - Lang & Alperin, "Graph Paper for Polygon-Packed Origami Design" (6OSME) was not found as a
    PDF.
  - Lang & Tsai, Origami⁷ (GOPS) is paywalled.
- **Lang's downloadable `ODS1e_Algorithms.pdf`** (langorigami.com) was read. It contains no
  occurrence of "river", "meander" or "box pleat", so it is irrelevant here [P].
- **Lang, "Crease Patterns as Art" [P-sum]:**
  - Uniaxial box pleating adds a family of "axial+N" creases, and N is the elevation.
  - Axial+N creases are "lines of constant elevation".
  - There is nothing on river routing.

### 3.2 What is known, and how

- **Rivers [S]** (this repo's BP compiler spec, paraphrasing ODS2 §13):
  - Rivers have constant width, with 90° bends only.
  - Constant width is checked by "every 45° ridge from a bend corner must land on the opposite
    bank's corner".
  - Rule 4: "all paper is assigned".
  - ODS2 Ch. 14 contains "level shifters, Pythagorean stretches, meanders, parity rules (§14.3)…".
  - The archived compiler's river ridges were "one 45° ridge from each bend corner to the opposite
    bank".
- **Pleatsmith's THEORY.md [P]** cites ODS2 Chs. 12–13. It describes "rivers of constant width
  with horizontal and vertical banks" and an L∞ ownership field that "reproduces … contours that
  continue across rivers, and ridges at river bends".
- **Tree-theory basis [P].** In Lang & Demaine (OSME 2006), hinges are lines of constant depth.
  A river is therefore the band between two depth levels, which in L∞ is an offset band. This
  was read for the earlier report.
- **Wong 4.2 [ASR]** credits the meander to Lang ("Lang talks about that in his book").
- **Conclusion.** ODS2's meander construction remains unread. No reachable source gives its
  crease-level construction or a measured effect.

---

## 4. Brandon Wong (The Plant Psychologist): lessons 4.2 and 5.4, slides, code, papers

### 4.1 Sources

- **Lesson 4 slides [P]** (Google Slides `1iD7jaEIcR1WsLbMzQ1G06g-b0CCU3WViHhZDzVOXCxA`, text
  export). This is the deck linked from 4.2's description.
- **Lessons 4.2 and 5.4: full auto-captions [ASR].** These were captured in the in-app browser,
  from the player's own timedtext request. Captions only; the drawings were not seen.
- **`boxpleater-beta` [P]** (github.com/theplantpsychologist, 2020, commit `1e44631f`, no licence
  file). This is Wong's own automated packer.
- **"New techniques in hex pleating for representational origami design" [P]** (Wong,
  web.mit.edu/wongb, the Origami⁸ chapter's PDF).

### 4.2 River rules, verbatim from the slides [P]

- "Rivers must start and end at the edge OR loop back on itself".
- "Rivers must stay the same width as it 'meanders'".
- "Every unit must be part of a flap or river. Don't leave any gaps unfilled!"
- CP rules: "There is a ridge crease at every bend", and "The river runs perpendicular to the
  pleats".
- Flaps: "Flaps must not overlap (except with pythas)", and "You can add on pleats to all 3 types
  of flaps".
- Tips: big flaps first, in corners and edges.

### 4.3 Lesson 4.2 walkthrough [ASR]: rivers in practice

Tree: total length 30. Grid 16 against the bound 15 ("four units of edge to spare").

- **Edge-unit budget.** A mis-sized corner flap that took 8 edge units instead of 6 used up two of
  the four spare units. Wong tracks rivers and flaps by *edge consumption*. A river consumes 2w of
  edge, w at each place it meets the edge.
- **Distance rule.** After marking where a river starts, "the next flap … needs to start … at least
  two units away from the river". The river's width is the L∞ separation.
- **Bend rule.** "every time the river bends we need a diagonal ridge" [ASR, ≈16:20].
- **Gap filling, two alternatives (≈16:30–18:00):**
  - **(a) Flap fills.** Bend the river the other way and shift a flap up, so the flap fills the gap.
  - **(b) River fills (colour change).** Keep the edge flap without extra pleats and "shift the
    thickness of the paper into the river … instead of making the flap take up the space you make
    the river take up the space". The bend is what does this. In his example it was "not
    completely possible": a box stayed unfilled.
- **Closing rules (≈24:30–25:40):**
  - Rivers go edge to edge or loop. His loop example is a river around two centre flaps.
  - "no unfilled gaps … you can fill in your gaps by meandering your river … or you can also add
    extra pleats onto the flap".

### 4.4 Lesson 5.4, "bend rivers to compact" [ASR]

- **Setup (≈11:30–13:00).** Wong packs a level-shifter host: a stack of 8-unit-wide centre flaps
  separated by straight full-width rivers of 3, 2 and 3 units.
- **The problem.** "we got these weird gaps on the side".
- **The fix (≈13:30–15:00).** He bends each river "straight downwards to kind of compact it". He
  bends the bottom river, then the 2-unit river "down to follow" it, then the last one again. He
  then extends flaps to fill: "these are actually not eight unit flaps these are a little bit
  longer but that's okay we're okay with extra … pleats".
- **His summary.** "we just bent the rivers … straight downwards to kind of compact it. We had to
  expand these flaps a little bit as a result."
- **Topology caveat (≈15:30).** "these rivers you can bend however you want". But whatever you
  pack inside the bend ends up between the flap and the river, on that side of the tree.
- **Reading of 5.4 [I]:**
  - The bends turn full-width rows into nested Γ/U shapes stacked against one edge. That is the
    same nested-U pattern as COrigami's rock lobster.
  - The leftover gaps are filled by **flap growth**, not by the river. The grid is fixed (16).
  - In 5.4, bending is a layout-compaction move. It is not a slack-into-river move.

### 4.5 Wong's own packer, `boxpleater-beta` [P, `full box pleater.py`]

The algorithm is perimeter-first, and rivers are implicit:

```
blobify(tree):   # tree as nested lists, leaves in planar (cyclic) order
  for consecutive leaves (a, b) in cyclic order:
     blob.append(len(a) + rivers strictly between a and b + len(b))   # perimeter walk segment
findgrid(blob): N = ceil(sum(blob)/4); N = max(N, max(blob))          # = Wong's perimeter bound
pack(blob):      # wrap the cyclic blob sequence around the 4 sides, trying every start offset;
                 # if no start fits all segments on 4 sides of length N: N += 1
blackhole():     # repeat: move each flap one unit inward (perpendicular to its side) if every
                 # L∞ distance to every other flap stays >= tree distance; stop when nothing moves
```

- **Rivers.** No river geometry is ever constructed. Rivers are the paper left between the flaps
  after the inward contraction, and each crosses the boundary where its perimeter segment lies.
- **Formulation [I].** The square's boundary is laid out as the Euler tour of the tree (Lang's
  perimeter/active-path view), and the rivers fall out.
- **Gap filling.** The packer does not do it: "faulty solution … increase the grid size".

### 4.6 Wong's hex-pleating paper [P]

- **On box pleating's gap filling:** "Box pleating sometimes is forced to fill space by using 90
  degree river meanders or by adding small unused flaps. In both cases, this results in an
  inconvenient concentration of paper thickness."
- **The hex alternative (Fig. 17).** In hex pleating, leftover pockets can be absorbed either "as
  shallow ridges in the river" (details on the body, e.g. clothes) or in the limbs. The designer
  chooses, and either choice does not affect the rest of the packing.
- **Grid-filling rule.** Hex packing, like box pleating, "must be completely filled by the flaps
  and rivers without any empty spaces".
- **What success looks like for Wong [I]:** grid size is set up front by the perimeter bound and
  held fixed. River bends and meanders decide **where thickness goes**: colour changes, keeping
  pleats off edge flaps, compacting rows. Meanders are a last-resort filler with a thickness
  penalty. None of his material claims a bend shrinks the grid.

---

## 5. Other sources

### 5.1 Demaine, Demaine & Ku, "Folding Any Orthogonal Maze" (Origami⁵, 2010) [P]

PDF read; its figures were viewed at 70 dpi. The 6.849 Fall 2012 Lecture 7 transcript (OCW) was
also read [P].

- **What it builds.** A (2h+1)n × (2h+1)n square folds into any orthogonal graph on an n×n grid,
  extruded to a uniform height h.
- **The algorithm.** Place "an appropriate folding gadget at each grid point". Up to rotation
  there are six vertex gadgets: degree 0, straight, degree 4, degree 3, degree 1, and corner.
  The algorithm is linear time and amounts to cut-and-paste tiling.
- **Why it composes.** All gadgets share "a consistent interface on each of their four sides".
  The lecture explains the interface:
  - a raised edge goes "over, up, down, over";
  - an absent edge goes "over and then you have a pleat underneath";
  - "it's important that those are the same total length", so either choice can be made
    independently at every side.
- **The turn ("corner") gadget.**
  - Its crease pattern has 45° creases at the turn.
  - For h > 1 it "extends outside the central 2 × 2 square reserved for the gadget" and would
    overlap a neighbour.
  - The fix is to "thin the excess structure near the floor (nonridge) edges of every gadget by
    sufficiently many sink folds".
  - Layers at any point are bounded by a constant (stated for h = 1).
- **Scale.** The (2h+1) factor is within about 2√2 of optimal. The lower-bound argument is the
  same kind of paper-path counting as Wong's perimeter bound. Lecture: "up and down and along the
  floor … three for every square".
- **Relevance [I].** This is not a uniaxial river construction: maze walls are 3-D ridges, not
  tree edges. What transfers is the **design pattern**:
  - a finite library of per-cell gadgets (straight, turn, T, cross, end, empty);
  - interfaces equal in paper length, so local choices compose with no global solve;
  - a turn costs extra paper that spills into the neighbouring cell, handled by local sinks.

  Pleatwright's elevation field gets interface compatibility for free, because every crease is
  derived from one global d(p) and `base.build` checks continuity. A maze-style gadget library
  would be redundant for rivers, but useful for anything not expressible as L∞ distance [I].

### 5.2 Tsai, "Geography of Origami: The Edge-River Method" (blog, 2021) [P-sum]

- **The idea.** ERM generalises the tree method to non-uniaxial "abstractions". Every edge
  occupies a river whose width equals the edge length.
- **River termination.** A river must "loop back into itself", connect two lake copies of the
  same edge, or flow to the sea (the paper edge).
- **Bending.** "Rivers change direction when they hit ridge creases" (fetch summary).
- **Concavities.** Rivers of edges forming a concavity may not share a bank segment, which usually
  needs a 1-unit "peninsula".
- **Box-pleating parity.** Any two copies of the same vertex must be an even taxicab distance
  apart, otherwise half-unit structures are needed.
- **In box pleating,** "rivers become in-and-out pleats".
- **Thickness.** Narrower peninsulas are more efficient, but "local thickness can approach
  infinity".
- **Relevance [I].** The parity statement is the general form of Pleatwright's `_parity_ok`.
  Every bend corner (a copy of a hinge vertex) must sit on the x+y-even lattice.

### 5.3 Pleatsmith (`benwalley/Box-pleating-generator`, commit `b8c4de4c`, **no licence: ideas only**) [P]

- **River model.** "drawn as a strip of constant width around an orthogonal centerline"
  (`model/types.ts`).
- **Crease field.** An L∞ ownership field: each point belongs to the flap whose square boundary
  is nearest, and contours are at integer elevation from the owner's axis. Its THEORY.md says this
  "reproduces … contours that continue across rivers, and ridges at river bends".
- **Auto-fill (`fill/fill.ts`):**
  1. Grow every flap by one unit per round, shortest first, keeping a step only if no
     error/overlap/circle-pair count rises.
  2. Turn each implied gap between groups into a **straight** river, edge to edge if possible.
  3. Grow again.
- **Not covered** (its own list): "meandering rivers" and level shifters.
- **Relevance [I].** This is the "everything but routing" baseline: the slack goes into flaps,
  and rivers are straight.

### 5.4 Lecture-note and misc. coverage

- **MIT 6.849 Fall 2010.** The L04/L05 notes are handwritten scans with no extractable text, and
  were not read.
- **MIT 6.849 Fall 2012 Lecture 7 transcript** (read): covers universal box pleating
  (polycubes, Ovadya's thesis on sharing pleats between aligned gadgets) and maze folding. There
  is nothing on uniaxial rivers.
- **pixel-druid.com notes [P-sum]:** only Wong's perimeter rule, "2 * riverlen of perimeter".
- **Akitaya et al., "Box Pleating is Hard"** (NP-completeness of flat folding) and **Demaine,
  Fekete & Lang** (NP-hard circle/river packing): covered in the earlier report. Neither gives
  routing constructions.
- **Search coverage.** No further academic paper on algorithmic river routing in box pleating
  (2023–2026) was found beyond COrigami.

---

## 6. Cross-source answers to (a)–(e)

| | (a) how rivers bend | (b) constraints | (c) effect of bending: grid vs thickness | (d) algorithm | (e) measured |
|---|---|---|---|---|---|
| COrigami | straight or one L-turn for the first river; later rivers snake around placed elements [P]; samples show L, Π/U and Π-with-feet, 90° only [P-measured] | contiguous tiling, edge to edge (all 22 bent regions touch the boundary), constant width [P-measured] | encloses corner/edge pockets, so shorter rivers and 2-D pocket packing, so smaller N; slack still in expanded flaps [I] | backtracking; first river by enumeration; wall-following for the rest; pockets packed on enclosure; flap-expansion gap fill [P] | 11/18 samples bent, 22 regions, 0 loops [P-measured]; paper: packing pass rate 55.3% [P] |
| BP Studio | course = union of children's rects offset by tree distance; 45° ridge from each outer corner to the facing inner corner [P] | full cover; constant width (corner pairing); excess means "unnatural", implying a meander, which is unsupported [P] | bends are a *cost*, minimised after N is fixed [P] | rough contour = offset union; riverRidge corner pairing; health checks [P] | "seconds to ~100 ms" search claims only; no river metrics [P] |
| Lang ODS2 | 90° bends with a 45° ridge from each bend corner to the opposite bank [S]; meanders named in Ch. 14 [S] | constant width; all paper assigned [S] | rivers and meanders fill gaps [S]; nothing quantified | not read | none reachable |
| Wong | "diagonal ridge" at every bend [P slides, ASR] | edge to edge or loop; constant width; no gaps; pleats perpendicular to the river [P] | grid fixed by perimeter bound; bends compact rows (5.4) or move thickness into the river (4.2); meanders concentrate thickness [P hex paper, ASR] | by hand; his 2020 code = perimeter walk + inward contraction, rivers implicit [P] | 4.2: 30-unit tree at N=16 vs bound 15 [ASR]; nothing on bends |
| Maze folding | per-cell corner gadget with 45° creases, thinned by sinks when h>1 [P] | equal-length interfaces; uniform height [P] | fixed scale 2h+1; bounded layers [P] | linear-time gadget tiling [P] | scale within ~2√2 of optimal (proof) [P] |
| Tsai ERM | change direction at ridges [P-sum] | loop, lake-to-lake or to the sea; even taxicab parity [P-sum] | narrow peninsulas are efficient but thicker [P-sum] | manual; map, then CP [P-sum] | none |
| Pleatsmith | strip around an orthogonal centreline; field gives bend ridges [P] | constant width [P] | slack into flaps [P] | grow flaps, then straight gap rivers [P] | none |

---

## 7. Mapping onto Pleatwright's elevation-field tiler [I unless marked]

### 7.1 What `base.build` already supports

`base.py` `_dist(r, p)` = min over the region's hinge *lines* of |x − v| or |y − h| (code read
[P]). That is the L∞ distance to the region's u-bank, valid where the u-bank is convex as seen
from inside the region. Three river shapes satisfy this:

- **A straight band.** d is measured from one line.
- **A nest.py offset ring.** d is measured from the outer (parent-side) rectangle; its corners
  give the bend ridges.
- **An L, Π/U or Π-with-feet river enclosing a child pocket.** The parent (u) bank is on the
  outside of every turn. With the arms at least w long, the infinite-line extension never
  undercuts the true segment distance (checked by hand on an L of width 6). These are exactly the
  COrigami sample shapes.

`_parity_ok` already enforces corners on the x+y-even lattice. `base.build` rejects any
non-isometric or discontinuous result. So a wrong river shape fails loudly, not silently.

### 7.2 What needs a change

- **S-bends and meanders,** i.e. a river whose u-bank has a **reflex** corner. Here d must be the
  L∞ distance to the corner *point* (the max form) in the corner square. The minimum change: make
  `_dist` the min over u-bank **segments** of L∞ point-to-segment distance. For constant width
  w, the equivalent is d_u = w − d_v near reflex u-corners.
- **Constant-width check.** Port BP Studio's corner pairing (`riverRidge` / `findMissingRiverRidges`):
  every right-angle corner of either bank must have a facing corner exactly (w, w) away on the
  other bank. That is the cheap pre-check before `base.build`.

### 7.3 Candidate constructions, ranked by fit

1. **Anchored-pocket offset bands** (COrigami shapes + BPS contour rule).
   - **What changes.** `nest.py` currently gives a child hub a full-width strip of its parent
     pocket. Allow a child pocket to be a w_p × h_p rectangle anchored at a corner of the parent
     pocket (river = L), at an edge (river = Π/U), or floating (river = ring, which already
     exists).
   - **Search.** It stays a floorplan (guillotine/treemap) search, so the existing pocket
     machinery and `_pocket_solutions` carry over.
   - **Expected effect.** A shorter river (≈ w·(w_p + h_p) instead of w·N) lowers the area, so N
     can drop. This is where the grid-size gain is.
   - **`base.build`** needs no change (u-bank outside the turn).
2. **Wall-following = offset of placed children.**
   - COrigami's "trace the contour of previously placed elements" and BPS's offset-union are the
     same set when the river is drawn at distance w around the union of the already-placed child
     elements.
   - An incremental implementation: pack the child pocket first (any rectilinear union), take
     its L∞ w-offset clipped to the paper (`expandPath` + union), and reject if (i) the offset
     overlaps a placed element, (ii) a corner pairing fails ("unnatural"), or (iii) parity fails.
   - This generalises (1) to non-rectangular child unions.
3. **Slack-into-river (meander) mode.**
   - Lengthen a river's course by giving the child-side boundary tongues, filled on the other
     side by parent-side flap expansion (BPS's "stub flaps" workaround). This needs the
     segment-distance `_dist`.
   - Expected effect: flap expansion drops (fewer layers per flap) and river layers rise. N does
     not change.
   - Only Wong and Lang endorse it, and both treat it as a gap filler. Wong's paper calls the
     result an inconvenient thickness concentration. BPS does not support it.
   - Measure before committing.
4. **Perimeter-first seeding** (Wong's 2020 packer).
   - Assign the Euler-tour edge segments to the four sides first, which fixes where each river
     meets the paper. Then contract inward.
   - It is a useful heuristic for choosing which edges a river's ends touch, a decision both (1)
     and (2) need.
   - It cannot replace the tiler: there is no gap fill and no explicit rivers.

### 7.4 Metrics implied by the sources

| source | what it optimises |
|---|---|
| COrigami | packing success rate first; recognisability (VLM) second; N third |
| BPS | N first, then river bends (contour-vertex count) at fixed N |
| Wong / Lang | N fixed by the perimeter bound; where the thickness goes (flap expansion against river area) |

**Proposal for the slice:**
- Report N/Wong-bound.
- Report flap expansion (flap cells / min polygon).
- Report **river course ratio** (river cells / (w × the shortest edge-to-edge course)).
- Report **river vertex count** (BPS's tidy metric) as a CP-complexity guardrail.

Bent rivers should be accepted when they lower N or flap expansion without raising the vertex
count gratuitously.

---

## 8. What could NOT be accessed

- **ODS2** Ch. 13/14 text, including the meander construction. Only page locators were found
  (meander: pp. 258, 401, 405, 654, 756).
- **Lang & Tsai, Origami⁷;** Tsai, Origami⁸ (paywalled).
- **Lang & Alperin, "Graph Paper for Polygon-Packed Origami Design"** (no PDF found).
- **COrigami code,** wall-follower details, traversal plan, scoring. The trees behind the 18
  samples are not available, so the probe cannot say which region is which tree edge, and the
  giraffe weevil's ∩-region stays ambiguous.
- **Wong's on-screen drawings** in 4.2 and 5.4 (captions only). The lesson 5 slides were not
  linked from 5.4's description and were not found.
- **MIT 6.849 Fall 2010 L04/L05 notes** (handwritten scans, no text layer).
- **The maze paper's figures:** only low-resolution renders of Figs. 2–3 were viewed. The six
  gadgets' exact crease coordinates were not transcribed.

## 9. Probe artefacts

- `docs/superpowers/evidence/2026-10-19-river-routing/corigami_samples/` (`regions.py`, `nonrect.py`, `dump.py`): hinge-region segmentation of COrigami
  packings. Read-only on `~/Desktop/origami_samples`.
- Fetched sources (untrusted data, not executed) were in a session scratchpad (not kept), `dl/{corigami,bps,maze,wong,
  wongcode,wonghex,lang,mit,pleatsmith}`.
