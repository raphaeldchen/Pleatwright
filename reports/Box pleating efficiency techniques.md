# Smarter packing, then stretches, reclaims box-pleated paper

Box pleating pays a geometric tax: flaps are separated in the L∞ (square) metric instead of the Euclidean one. Designers recover that tax with a small, well-documented toolkit:

- **Placement.** Big flaps go in corners, then on edges, and in the centre only when needed.
- **Gap control.** Gaps are filled by rectangles, river bends and meanders rather than by dead paper.
- **Pythagorean stretches.** Including Kamiya's 3-4-5 patterns and Tsai and Lang's GOPS/GPS, these let diagonally placed flaps sit at Euclidean rather than L∞ distance on an integer grid.
- **Level shifters.** These change the elevation of axial creases, so flaps come out wider or thinner. They are mainly a legibility tool, not a grid-size tool.

Tilted grids, 22.5° hybrids and hex pleating are separate design paradigms, not drop-in gadgets.

For Pleatwright, the measurements point to a different first target. Most of its surplus paper comes from its own search, not from the absence of gadgets:

- **Grid size.** Grids run from 10 to 136 (median 50), 1.46× COrigami's starting heuristic at the median and 1.30× Wong's perimeter lower bound.
- **Slack paper.** A median 39% of the sheet is expansion slack inside flaps.
- **Rung order.** The ladder ships the symmetric rung even when the unmirrored rung packs smaller. Keeping the smaller of the two would lift the median scale relative to TreeMaker from 0.904 to 0.974 on 42 trees. The 42-tree subset's median is 0.904; the median over all 51 trees is 0.894.

So the right order is:

1. Instrument efficiency.
2. Fix the search: rung choice, ranking and unequal pairs.
3. Route rivers.
4. Treat level shifters and Pythagorean stretches as later, costlier phases. Each one breaks an invariant `base.build` relies on today.

*Evidence tags.* **[P]** means a primary source was read directly: a paper, source code, or an author's own blog or slides. **[S]** means a secondary source: this repo's own paraphrase of *Origami Design Secrets* 2e (ODS2), which was not accessible; a forum quotation; or a catalogue or search summary. **[ASR]** means the claim was paraphrased from the auto-generated captions of Brandon Wong's videos; the on-screen figures were not seen. **[I]** means an inference, either mine or the research notes'. The Plant Psychologist *is* Brandon Wong ([Wong, "An Origami Journey"](https://web.mit.edu/wongb/www/origami/gallery/journey.html)), so his YouTube class and his BP guides are one source, not two.

## Box pleating's √2 tax is set first by placement and grid choice

### The efficiency yardstick is scale, which in box pleating means 1/N

Lang's efficiency measure for any uniaxial base is the scale m: the ratio of folded flap length to tree edge length. TreeMaker maximises m subject to |vᵢ − vⱼ| ≥ m·lᵢⱼ with every tip inside the paper. Lang and Demaine write that "a base with a large scale will have a folded form that is relatively large compared to the starting paper" **[P]** ([Lang & Demaine, Origami⁴ §2.1](https://erikdemaine.org/papers/TreeMaker_OSME2006/paper.pdf)). Wong teaches the same idea informally: "efficiency is the ratio between final model size compared to the initial starting paper" **[ASR]** ([Wong 6.1](https://www.youtube.com/watch?v=BDiDOsAM44c)).

On an N×N grid with integer tree lengths, the scale is simply 1/N. So in practice, "the smallest grid that packs" is the efficiency target that the community, BP Studio and COrigami all use **[I]**.

### How large the tax is, and who said what

Box pleating replaces Euclidean flap circles with L∞ squares and rivers with constant-width orthogonal channels. Demaine calls the result "a little bit less efficient… you're wasting those little corners. But not that much more inefficient" **[P, lecture]** ([MIT 6.849 Class 4](https://ocw.mit.edu/courses/6-849-geometric-folding-algorithms-linkages-origami-polyhedra-fall-2012/b67bcae394e440e6691812c6c9c6423d_ylQ5-9f5KIs.pdf)).

Lang's own position (ODS2 Ch. 13 p. 573, known here only through this repo's quotation) is that box pleating "must be, by definition, less efficient", but "the penalty is often very small" **[S]** ([BP compiler spec](../docs/superpowers/specs/2026-09-20-box-pleat-compiler-design.md)). **Lang gives no percentage.** The "up to 40%" figure this project once attributed to him was retracted. A similar "almost 40%" figure does appear in Arijan Abrashi's explainer, but its direction reads inverted relative to standard theory, so it should not be cited without re-reading the source **[P, flagged]** ([Abrashi, "Pythagorean stretch"](https://abrashiorigami.com/pythagorean-stretch/)).

The defensible theoretical statement is geometric **[I]**. Two tips offset by (Δx, Δy) are max(Δx, Δy) apart in L∞ but √(Δx² + Δy²) apart on the paper. A diagonally placed pair therefore wastes up to √2 ≈ 1.41× in required separation, while axis-aligned pairs waste nothing. Area ratios rank the per-flap shape waste of each angle system:

| angle system | polygon area / circle area |
|---|---|
| square (box pleating) | 4/π ≈ 1.27 |
| hexagon (hex pleating) | ≈ 1.10 |
| octagon (22.5°) | ≈ 1.06 |

This is a heuristic only, because real cost is set by active paths, not by per-flap area.

### Placement class is the first lever

Lang's minimum hinge polygon is the on-paper part of a 2r×2r square centred on the tip. That is r×r for a corner tip, 2r×r for an edge tip and 2r×2r for an interior tip, so a flap costs **r², 2r² or 4r²** of area depending on where its tip sits **[S]** ([BP compiler spec §11.8](../docs/superpowers/specs/2026-09-20-box-pleat-compiler-design.md)).

Wong gives the same rule as practice: a 4-unit corner flap takes 16 cells and the same flap on an edge about 32. So pack the biggest flaps first, in corners **[ASR]** ([Wong 4.2](https://www.youtube.com/watch?v=nuLFd4Hzoc8)). Centre flaps "make everything weird". Small trees avoid them, but once the minimum grid reaches "around 20 or higher" some are usually needed **[ASR]** (same video).

Abrashi adds a quality cost:

- **Trapped.** A central flap is normally trapped between the axial lines of a neighbour.
- **At most one free.** At most one central flap per configuration can be free.
- **Doubled width.** Freeing it means opening the axis, which doubles the base width **[P]** ([Abrashi, "Can central flaps be free?"](https://abrashiorigami.com/can-central-flaps-be-free/)).

### Two lower bounds, and Wong's is tighter on these trees

Wong's grid-size lower bound comes from perimeter. Every flap or river of length L consumes 2L of the sheet's 4N perimeter, so **N ≥ 2·ΣL / 4**, with centre-flap lengths subtracted. He says this bound is not in Lang's book **[ASR]** ([Wong 4.2](https://www.youtube.com/watch?v=nuLFd4Hzoc8)). His worked example has a 30-unit tree: the bound gives 15 and he chose 16, partly because 16 is easier to fold.

COrigami's App. E.1 instead starts the sweep at max(⌈√Σaᵢ⌉, D). The four longest flaps count lᵢ² ("quarter circles"), later flaps 2lᵢ², and rivers count max(kᵢmᵢ, kᵢ²) or kᵢ². An odd value is rounded up to even for symmetric figures **[P]** ([COrigami App. E.1](https://arxiv.org/html/2606.26299v1)).

I computed Wong's bound (⌈total tree length / 2⌉) for the 51 artifact trees in `fixtures/full17_v3_sticks/`:

- **It exceeds COrigami's `G_init` on 37 of 51 trees** (median `G_init` / Wong = 0.90).
- It never exceeds the shipped N.

So it is the sharper yardstick for Pleatwright **[I, new probe this report]**.

### Rectangles fill gaps without lengthening flaps

Box pleating "tend[s] to get more gaps". The standard fix is to grow a square into a rectangle **[P, lecture]** ([MIT 6.849 Class 4](https://ocw.mit.edu/courses/6-849-geometric-folding-algorithms-linkages-origami-polyhedra-fall-2012/b67bcae394e440e6691812c6c9c6423d_ylQ5-9f5KIs.pdf)). Lang's §13.3 invariant constrains the growth: the polygon may expand only while **at least one hinge stays at distance r from the tip**, otherwise the flap becomes longer than the tree says **[S]** ([BP compiler spec §11.9](../docs/superpowers/specs/2026-09-20-box-pleat-compiler-design.md)).

That makes gap fill free in grid size, but not free in thickness. This distinction matters a great deal for Pleatwright (see the last section).

## Pythagorean stretches buy Euclidean separation on an integer grid

### What a stretch does, and the parity test

A Pythagorean stretch ("pytha") lets two diagonally placed flaps move closer than square packing permits. In the definition attributed to Lang on a 2007 forum, "two diagonally-oriented leaf vertices are allowed to move closer to each other", with axial and ridge creases at angles other than 0/45/90° near the stretch **[S]** ([Origami Forum thread](https://snkhan.co.uk/forum/viewtopic.php?t=3505)).

The trigger condition is identical across Wong, Abrashi and BP Studio's code. With pure 45/90° creases, flap *squares* may not overlap. With a stretch, only flap *circles* must not overlap. Overlapping circles are illegal, and no stretch fixes that **[ASR]** ([Wong 6.2](https://www.youtube.com/watch?v=vaNPyzmIRx4)) **[P]** ([Abrashi](https://abrashiorigami.com/pythagorean-stretch/)).

In BP Studio the condition is code. Tsai's `createJunction` computes the axis separations sx and sy of two flaps whose tree distance is d. The layout is invalid if sx ≤ 0, sy ≤ 0 or sx² + sy² < d². Otherwise the pair needs a stretch covering an overlap rectangle of **(d − sx) × (d − sy)** **[P]** ([BPS junction.ts](https://github.com/MuTsunTsai/box-pleating-studio/blob/ae73ae7df05a33e4742bd1c7ae3f808efb923a4d/src/core/design/layout/junction/junction.ts)).

The parity test is the same in both community sources **[I]**. Wong uses the overlap's area: an even area means the stretch "works out evenly" and can be drawn by eye, while an odd area needs partials **[ASR]** ([Wong 6.2](https://www.youtube.com/watch?v=vaNPyzmIRx4)). Abrashi requires at least one even side for the parallelogram form, and otherwise uses the "universal" form **[P]** ([Abrashi](https://abrashiorigami.com/pythagorean-stretch/)). For integer rectangles these are the same condition.

### How it is constructed on the grid

Wong derives the gadget from a fish base **[ASR]** ([Wong 6.1](https://www.youtube.com/watch?v=BDiDOsAM44c)):

1. **The square fails.** A fish base on a square has irrational flap lengths, because the rabbit-eared 45-45-90 triangle has an irrational hypotenuse.
2. **The 3×4 rectangle works.** Rabbit-ear the 3-4-5 triangle inside a 3×4 rectangle on a 4×4 grid and every length comes out integral. The base reaches **5 units, longer than the paper's 4-unit side**, which "in normal box pleating would not be possible".
3. **The angles stay on grid.** The triangle's bisectors have slopes arctan 2 and arctan 3, so every crease still lands on grid points.

On the sheet, the stretch is a parallelogram plus two "arms". Wong's three eyeballing rules **[ASR]** ([Wong 6.2](https://www.youtube.com/watch?v=vaNPyzmIRx4)):

- **Slopes.** The parallelogram's slopes must meet at 45° and 135°. arctan 2 with arctan 3 works (from 3-4-5); 5-12-13 gives slopes 2/3 and 1/5; arctan 4 with arctan 2 fails.
- **Obtuse corners** lie on the diagonal tracks through the overlap box's corners.
- **Acute corners** lie on the diagonal ridges from the flap centres.

Hinges reflect across the parallelogram's ridges, which makes the flap polygons concave, and the gadget can slide along its tracks. Wong estimates that 3-4-5 covers "maybe 70–75%" of cases. That is his guess, not a measurement.

Abrashi supplies the underlying geometry **[P]** ([Abrashi](https://abrashiorigami.com/pythagorean-stretch/)):

- The two bisectors adjacent to any right triangle's hypotenuse meet at 135°, and Kawasaki then forces the opposite angle to 135°.
- He tabulates the grid ratio pairs that build that angle (1:2–1:3, 2:5–3:7, 1:4–3:5, …).
- The element must sit between the two circle centres.
- A river can be absorbed by enlarging a polygon. In his example an 8×8 grows to 13×13 to absorb a 5-unit river, which creates an even 4×5 overlap.

Wong treats the same case from the other side: a flap plus its surrounding river can be solved as "one big circle" **[ASR]**.

### Kamiya, GOPS and GPS: attribution and the factorization algorithm

Attribution needs care here.

- **Kamiya patterns.** Stretches built on the 3-4-5 triple "are commonly called Kamiya patterns", after Satoshi Kamiya **[P]** ([Tsai, "The story of Box Pleating Studio"](https://origami.abstreamace.com/2021/06/02/the-story-of-box-pleating-studio/)).
- **GOPS is Mu-Tsun Tsai's.** After reading ODS2's Ch. 14 (late 2016), he asked what happens with an offset greater than one. The result, the generalized offset Pythagorean stretch, has "a much larger solution space", and because it is integral, gadgets compose into compound and 3+-flap solutions.
- **GPS is Lang's.** Lang independently developed GPS, and "GPS is exactly the complement of GOPS". For both, the overlap rectangle's area is what matters, which led to a construction based on integer factorization **[P]** (same).
- **Earlier work.** Tsai credits essentially equivalent earlier patterns to Meguro, Murakami, Kamiya and Imai.
- **The papers.** The joint paper is Lang & Tsai, Origami⁷ (2018) vol. 2 pp. 591–606. Its follow-up is Tsai, Origami⁸ (2025). Both are paywalled and were not read ([BP Studio notes](https://bp-studio.github.io/notes.html); [Springer](https://link.springer.com/chapter/10.1007/978-981-96-6711-6_1)).
- **Unconfirmed.** No source confirms who coined "Pythagorean stretch".

The construction is therefore known from BP Studio's MIT-licensed code, not from the papers. `gops.ts` works as follows **[P]** ([BPS gops.ts](https://github.com/MuTsunTsai/box-pleating-studio/blob/ae73ae7df05a33e4742bd1c7ae3f808efb923a4d/src/core/math/gops.ts)):

- **Search.** For an overlap (ox, oy), it rejects the case where both are odd. Otherwise it enumerates factorizations of the half-area **ox·oy/2 = u·v**, searching downward from u = ⌊√(half-area)⌋ to "prioritize the most efficient gadget".
- **Span.** Each candidate's span is sx = u + v + oy.
- **Rank.** Candidates are ranked by the larger reduced numerator of (oy+v)/oy and (ox+u)/ox, in effect the complexity of the slopes the gadget needs.

Odd×odd overlaps are handled by fallbacks:

- **Half-integral "Kamiya" gadgets.** Double the overlap, run GOPS, keep rank ≤ 3, then halve ([kamiya.ts](https://github.com/MuTsunTsai/box-pleating-studio/blob/ae73ae7df05a33e4742bd1c7ae3f808efb923a4d/src/core/math/kamiya.ts)).
- **A "universal GPS" that is "guaranteed to find a pattern"** by scaling the overlap by 2, 4, 6, … ([universalGPS.ts](https://github.com/MuTsunTsai/box-pleating-studio/blob/ae73ae7df05a33e4742bd1c7ae3f808efb923a4d/src/core/design/layout/generators/universalGPS.ts)).

For a single junction the strategy order is: integral gadget → double relay → half-integral → universal ([singleConfigGenerator.ts](https://github.com/MuTsunTsai/box-pleating-studio/blob/ae73ae7df05a33e4742bd1c7ae3f808efb923a4d/src/core/design/layout/generators/singleConfigGenerator.ts)). Multi-junction groups are searched by increasing total rank, with span lower bounds that cut a search "from seconds down to ~100ms" ([spanBound.ts](https://github.com/MuTsunTsai/box-pleating-studio/blob/ae73ae7df05a33e4742bd1c7ae3f808efb923a4d/src/core/design/layout/generators/spanBound.ts)).

The BP Studio manual states its coverage: all valid 2-flap layouts, most 3-flap layouts and many 4-flap ones ([BP Studio manual](https://bp-studio.github.io/manual.html)).

| variant | when used | source tier |
|---|---|---|
| 3-4-5 parallelogram (Kamiya pattern) | overlap with an even side; the commonest case | [P] Tsai, Abrashi; [ASR] Wong |
| other triples (5-12-13, 8-15-17, 7-24-25) | other slope budgets | [P] Abrashi |
| GOPS (offset > 1) | larger solution space; composes | [P] Tsai blog, BPS code |
| half-integral Kamiya | odd×odd overlap, rank ≤ 3 | [P] BPS code |
| universal GPS | always succeeds, more complex | [P] BPS code, Abrashi |

### What a stretch actually saves, and what it costs

Only one measured, single-model effect was found. In Wong's lesson 5.5, pulling a human figure's legs together with a pytha cut the grid **from 36 to 32** **[ASR]** ([Wong 5.5](https://www.youtube.com/watch?v=0uPTFBkuJ4E)). That makes the model about 12.5% larger from the same sheet (my arithmetic).

BP Studio's homepage claims these gadgets bring box pleating "nearly as good as the optimal circle packing" **[P, claim]** ([BP Studio](https://bp-studio.github.io/)). No corpus-level measurement exists.

The costs are documented:

- **Gusset slivers.** Imperfect stretches "often come with gusset slivers" ([Tsai](https://origami.abstreamace.com/2021/06/02/the-story-of-box-pleating-studio/)).
- **Folding difficulty.** CPs get more complex and harder to fold, and moving the element leaves unused paper ([Abrashi](https://abrashiorigami.com/pythagorean-stretch/)).
- **No tiling guarantee.** BP Studio's validity notion does not require gap-free tiling or a fully certified CP. COrigami rejected BP Studio for exactly that reason: its solutions "frequently contain Pythagorean stretches and cannot enforce contiguous tiling" **[P]** ([COrigami App. A](https://arxiv.org/html/2606.26299v1)).

## Elevation and level shifters buy width, not grid size

### Elevation and the elevation rule

Elevation is a primary-source concept. In a folded uniaxial base, a point's perpendicular distance from the axis is its elevation and its distance along the axis is its depth. Active paths lie at elevation 0 and fold as axial creases. Insetting a polygon by h gives the constant-elevation contour at h **[P]** ([Lang & Demaine §2.2](https://erikdemaine.org/papers/TreeMaker_OSME2006/paper.pdf)).

Lang's ODS2 §13.5 elevation rule assigns fold direction (white side up) **[S]** ([BP compiler spec §5.5](../docs/superpowers/specs/2026-09-20-box-pleat-compiler-design.md)):

- higher on both sides → valley;
- lower on both sides → mountain;
- higher on one side only → unfolded.

Wong's vocabulary makes this concrete **[ASR]** ([Wong 5.1](https://www.youtube.com/watch?v=v4ZJzLWAK10)). Without intervention, valleys sit at "axial" and mountains at "axial+1". Flaps are therefore one unit thick, which is why box-pleated bases look like stick figures.

### Where level shifters are needed

Lang's §14.1 places the level-shifter site where two mismatched elevation families meet head-on, typically at the paper edge **[S]** ([BP compiler spec](../docs/superpowers/specs/2026-09-20-box-pleat-compiler-design.md)). This project's archived Lang Ch. 13 compiler hit exactly that site: all 6 of its contour-stage failures were 0-vs-1 collisions on a paper edge ([box-pleat evidence](../docs/superpowers/evidence/2026-09-20-box-pleat/README.md)).

### Two families of shifter

Wong teaches two families **[ASR]**:

- **Ridge level shifters** ([Wong 5.2](https://www.youtube.com/watch?v=PPyQmFRZKjw)). Squash a ridge, then sink through it.
  - *Range and setup:* the height is continuous from axial−1 to axial+2 and needs no special setup. Going below the axis also gives a colour change.
  - *On-grid version:* the naive squash produces 22.5° creases, which never lie on a grid, so Wong replaces it with an arctan-2 triangle whose vertices are all grid points. That is the same triangle found inside a 3-4-5 pytha.
- **Pleat ("general") level shifters**, "the much more common" type ([Wong 5.3](https://www.youtube.com/watch?v=XSZpbx-yy4s)).
  - *Host:* a pleat perpendicular to the axial pleats, with its mountain on the lower-elevation side.
  - *Stacking:* each such pleat buys up to two more levels, so one pleat reaches about axial+3 and stacked pleats go higher.
  - *Incorporating into a packing* ([Wong 5.4](https://www.youtube.com/watch?v=pNagY0LUGls)): collapse 1-unit centre or edge flaps as locked pleats, make the host flaps at least as long as the required width (8 units in his 16-grid exercise), pack them, then "slap" the shifter pattern over the pleats.

Abrashi prices the variants **[P]** ([Abrashi, "Level shifters"](https://abrashiorigami.com/level-shifters/)):

- **45° ridges:** shifters lose no paper and need no dummy element. An asymmetric one needs about 2 units to reach its elevation, a mirrored one 3, a symmetric one about 2.5.
- **Horizontal or vertical ridges:** shifters always need a hidden host and lose paper. His hidden example lost **4 units and piled 5 layers**, while a visible version reached the same elevation with **3 layers**.

### Theory and the purpose of shifters

The theory is recent and primary. Wong & Demaine (Origami⁸/OSME 2024) prove a condition for two sets of parallel pleat rays meeting a ridge at the same angle, with intercepts a₁<…<aₘ and b₁<…<bₙ. A locally flat-foldable transition exists **iff a₁−a₂+a₃−… = b₁−b₂+b₃−… and m ≡ n (mod 2)**. They give a constructive algorithm and use it to terminate dense bouncing **[P]** ([Wong & Demaine 2024](https://erikdemaine.org/papers/PleatTransitions_OSME2024/paper.pdf)).

Their stated motivation shows what shifters are for: figures "that are not a single uniform width", such as insects with thin legs and a wide shell. That is legibility, not grid size. Wong also uses a "wall of level shifters" to isolate a half-grid "partial 80ths" region inside a 40 grid, which gives local detail at higher crease density **[P]** ([Wong, Journey](https://web.mit.edu/wongb/www/origami/gallery/journey.html)).

BP Studio does not implement elevations or half-integral structures ([manual](https://bp-studio.github.io/manual.html)). Wong calls a level shifter "a pocket of unaxiality", which is why the tool cannot express it **[P, slides]** ([tilted-grid slides](https://docs.google.com/presentation/d/16M6jhZK4MUuGqAG5kYMUfz8ZF6cS7LhbnMdILSzndSo/edit)).

## Rivers, grids and angle systems decide where slack goes

### River rules, and gap filling by bends and meanders

River rules are consistent across sources. A river is a constant-width band with 90° bends and a ridge at every bend. It runs edge to edge or closes on itself, and every unit of paper belongs to some flap or river **[S]** ([BP compiler spec §4](../docs/superpowers/specs/2026-09-20-box-pleat-compiler-design.md)) **[ASR/slides]** ([Wong 4.2](https://www.youtube.com/watch?v=nuLFd4Hzoc8); [lesson 4 slides](https://docs.google.com/presentation/d/1iD7jaEIcR1WsLbMzQ1G06g-b0CCU3WViHhZDzVOXCxA/edit)).

The efficiency technique is to spend slack area in rivers instead of flaps **[ASR]** (same video):

- **Fill gaps** by meandering the river or by adding pleats to a flap.
- **For colour-change designs**, "make the river take up the space" by bending it.

Bending rivers to compact a packing makes flaps "grow a bit", which Wong accepts ([Wong 5.4](https://www.youtube.com/watch?v=pNagY0LUGls)). ODS2 Ch. 14 names "meanders" as a technique **[S]**, but no reachable source describes their construction.

### How tools route rivers

BP Studio traces a hub's river as the union of its children's contours expanded by the edge length. It flags rivers wider than needed as "unnatural" (implying a meander) **[P]** ([BPS layout README](https://github.com/MuTsunTsai/box-pleating-studio/blob/ae73ae7df05a33e4742bd1c7ae3f808efb923a4d/src/core/design/layout/README.md); [manual](https://bp-studio.github.io/manual.html)).

COrigami routes the first river as a straight or L-shaped band. Later rivers come from "a wall-following algorithm that traces the contour of previously placed elements, producing free-form paths that snake around existing obstacles". The algorithm is not specified further **[P]** ([COrigami §3.2](https://arxiv.org/html/2606.26299v1)).

Tsai explained to Wong an "Edge River Method" for polygon (unaxial) designs, in which bent rivers can overlap via Pythagorean stretches. Wong calls it "more of a theoretical thing" **[P, slides]** ([tilted-grid slides](https://docs.google.com/presentation/d/16M6jhZK4MUuGqAG5kYMUfz8ZF6cS7LhbnMdILSzndSo/edit)).

### Tilted grids are a different paradigm

Wong's tilted-grid lesson credits Shuki Kato's *Origami Nature Study* with popularising the method **[ASR]** ([Wong, tilted grid](https://www.youtube.com/watch?v=rnsL1Vz7y20)). The grid is tilted by slope 3 (about 18.4°). Wong's reasoning: slope 3 and slope 1/2 are exactly 45° apart, and the diagonal symmetry line crosses grid points 7 times, against 5 at slope 2 and 2 at slope 4. The design is drawn as an "abstraction" of overlapping convex polygons, negative space is removed, and the half-square is reflected.

He lists the trade-offs **[P, slides]** ([slides](https://docs.google.com/presentation/d/16M6jhZK4MUuGqAG5kYMUfz8ZF6cS7LhbnMdILSzndSo/edit)):

- **Pro:** efficient and organic for wide-bodied subjects.
- **Cons:** pose is locked ("the back leg is pretty much completely locked"); it is poor for thin-limbed subjects, where axial box pleating is more efficient; and it is hard to fold.
- **One subject on three grids:** the tilted version was most efficient "but not by much".

For a stick-figure tree pipeline this is not an incremental gadget **[I]**.

### 22.5° and hex systems sit outside an integer-grid tiler

22.5° is discouraged *inside* box pleating because tan 22.5° is irrational: "we don't like mixing 22 and a half with box pleated" **[ASR]** ([Wong 5.2](https://www.youtube.com/watch?v=PPyQmFRZKjw)). Hybrids exist; Brian Chan's Newt is described as "box-pleat + 22.5" ([MIT Newt page](https://www.mit.edu/~chosetec/origami/newt)).

The 22.5° system has an exact coordinate set, (m + n√2)/2^ℓ (Tachi & Demaine, Origami⁵). That result is known here only from a search summary of [the paper](https://erikdemaine.org/papers/AngularGrid_OSME2010/paper.pdf) **[S]**. Exact arithmetic in ℤ[√2] is automatable, but it is outside an integer-grid tiling model **[I]**.

Hex pleating is an ODS2 addition ([Routledge](https://www.routledge.com/Origami-Design-Secrets-Mathematical-Methods-for-an-Ancient-Art-Second/Lang/p/book/9781568814360)). COrigami says no computational model exists for it ([COrigami App. A](https://arxiv.org/html/2606.26299v1)), but Wong's Origami⁸ chapter covers packing uniaxial trees on a hex grid ([Springer](https://link.springer.com/chapter/10.1007/978-981-96-6711-6_2)). His slides say hex level shifters "are more efficient, and can be easily 'built in' by using ridge bevels" **[P]** ([Wong hex slides](https://web.mit.edu/wongb/www/origami/engineering/files/hp%20slides.pdf)).

## Quality heuristics treat every surplus cell as a layer

### Area becomes thickness

The community's core quality rule is that area becomes thickness. "Larger circles mean thicker flaps, so the tail was given as little paper area as possible" ([cExplr scorpion](https://cexplr.github.io/blog/origami-scorpion-design-from-start-to-finish)). Placing a big flap on an edge rather than in a corner makes the model thicker **[ASR]** ([Wong 4.2](https://www.youtube.com/watch?v=nuLFd4Hzoc8)). The repo's reading of ODS2 attributes the same corner > edge > interior ranking to "Lang's layer argument, Ch. 9 §9.4 / Ch. 14 §14.2" **[S]** ([BP compiler spec §5.2](../docs/superpowers/specs/2026-09-20-box-pleat-compiler-design.md)).

The heuristics that follow from it:

- **Prefer wide flaps.** "a wide tail can be thinned but it's hard for a thin tail to be thickened", so design legs about 2 units wide and give tails wide polygons **[ASR]** ([Wong, tilted grid](https://www.youtube.com/watch?v=rnsL1Vz7y20)).
- **Prefer visible level shifters over hidden ones** (Abrashi's 3 layers against 5).
- **Choose hinges to limit thickness.** Several hinge solutions are valid, but some make the model thicker. Wong drags them "the closest way to the edge" **[ASR]** ([Wong 4.3](https://www.youtube.com/watch?v=5pMxh01Dnqc)).
- **Put colour changes on raw paper edges.** They "can be realized only on the paper edges" ([Abrashi, Colour change](https://abrashiorigami.com/colour-change-part-1/)).

### Narrowing is a shaping-stage tool

COrigami's narrowing is a "clip pattern algorithm". A base-adapter-plus-narrowing-pleat template is propagated through a flat-folded flap's layers by affine transforms, in symmetric and asymmetric variants **[P]** ([COrigami App. G.2](https://arxiv.org/html/2606.26299v1)).

### BP Studio's tidy objective and the hardness wall

BP Studio's optimizer encodes a mechanical proxy for CP quality **[P]** ([BPS optimizer README](https://github.com/MuTsunTsai/box-pleating-studio/blob/ae73ae7df05a33e4742bd1c7ae3f808efb923a4d/src/client/plugins/optimizer/src/README.md)):

1. **Continuous relaxation.** SLSQP circle and rounded-rectangle packing with basin-hopping.
2. **Integer fitting.** A windowed CSP on the grid that starts one size *below* the continuous ceiling ("occasionally possible to beat the continuous solution on grids").
3. **Tidying.** At a fixed size, a large-neighbourhood search minimises, lexicographically, the number of rough-contour vertices and then the area of uncovered junctions. This "push[es] the flaps into neat rows and columns".

Hardness bounds how far exactness can go. Flat-foldability of box-pleated CPs is NP-complete even at ≤9 (unassigned) or ≤25 (assigned) layers ([Akitaya et al. 2016](https://scripts.mit.edu/~jasonku/pdf/BOXPLEATINGHARD_LNCS2016.pdf)), and circle/river optimisation on square paper is NP-hard ([Demaine, Fekete & Lang](https://arxiv.org/abs/1008.1224)). Heuristic search plus certification is the only realistic architecture **[I]**.

## Pleatwright's surplus comes mostly from its own search

### What the baseline measures

Pleatwright packs a contracted tree as rows of rectangular flap columns inside full-width hub slabs. Rivers are straight full-width bands, or L∞ offset rings for branching hubs. All slack is absorbed by flap expansion or by virtual hinges past the paper edge, and `base.build` requires every cell to be owned ([pack.py](../mcp_harness/pleatwright/pack.py); [base.py](../mcp_harness/pleatwright/base.py)). The packer sweeps N upward in steps of 2 and takes the first candidate that builds. Its `_score` counts only virtual hinge lines, and every one of the 51 records has `pack_tried: 1` ([pipeline.py](../mcp_harness/pleatwright/pipeline.py); [records.jsonl](../docs/superpowers/evidence/2026-10-06-corigami-pipeline/records.jsonl)).

The baseline probes give the following ([baseline notes](../research_notes/Box%20pleating%20efficiency%20techniques/pleatwright_baseline.md)):

| quantity (51 artifact trees) | median | range |
|---|---|---|
| grid N | 50 | 10–136 |
| N / COrigami `G_init` | 1.46 | 1.00–2.32 (equal on only 3) |
| N / Wong perimeter bound ⌈T/2⌉ (my probe) | 1.33 | 1.04–1.94 |
| scale vs TreeMaker, same rolls | 0.894 | 0.609–1.337 |
| expansion slack (1 − min flap polygons − rivers) / N² | **0.39** | 0.13–0.76 |
| flap area / min polygon, per tree | 1.74× | 1.00–4.78× |
| flap cells / Σ flap length (mean layers in a 1-unit strip) | 34 | 7–100 |

Two facts dominate:

- **Rung choice.** Running the unmirrored rung alone gives N ≤ shipped on all 42 trees where it finished, and strictly smaller on 16 (dolphin_0 50→32, lizard_1 64→38, octopus_3 84→56, ant_0 102→70). Keeping the better of the two rungs moves the median TreeMaker ratio on those trees from 0.904 to **0.974**. On my probe it also moves the median N / Wong-bound from 1.30 to **1.20** (best of three rungs).
- **Half-unit resolution rarely helps.** The doubled-length rung shrinks N on only 7 of 44 trees.

One best-rung N (octopus_3 at 56) falls *below* Wong's bound of 59. That is consistent with interior centre flaps, which the bound excludes. So the bound is a yardstick, not a guarantee **[I]**.

The shipped symmetric rung also turns any declared pair with unequal lengths into two centred rows. lizard_1's front legs expand 5.8× and 9.1× for that reason ([pack.py `_items_sym`](../mcp_harness/pleatwright/pack.py)).

### Which techniques are present, absent or rejected

| technique | Pleatwright status | where it plugs in | cost | expected effect |
|---|---|---|---|---|
| efficiency metrics (N/G, N/perimeter bound, slack, layers) | absent | `pipeline._run` record | very low | makes every later change measurable |
| rung choice / ranking by N, slack, corner-first | absent (first fit; symmetric preferred) | `pipeline._run` ladder; `pack._score` | low | measured: N down on 16/42; median TM 0.904→0.974 |
| unequal-pair handling on symmetric rows | weak (two axial rows) | `pack._items_sym`, `_row_concrete` | low–medium | targets lizard_1-type blowups [I] |
| corner > edge > interior placement | implicit only | `pack` column positions; archived `tip_square` ranking | low–medium | lower area per flap; thinner flaps |
| rectangle gap fill | present (flap expansion) | `pack.py` | — | already the only slack sink |
| river bends / wall-following / meanders | absent; fallback recorded | `pack.candidates`, `nest._Search` (Region `more` rects); `base` unchanged if L∞ | medium | branching medians 1.18–1.68×; 3 capped edits; lets slack go to rivers |
| level shifters / elevation | absent (virtual hinge δ>0 only) | new Region kind; elevation offset in `base` | high | wider, legible flaps; may resolve odd-river parity [I] |
| Pythagorean stretch / GOPS | explicitly rejected (2026-10-10 spec) | new non-L∞ region map or post-`base` overlay; `solve.heuristic_labels` | high | smaller N for diagonal pairs; adds slivers |
| flap narrowing | present, opt-in, LLM-driven | `narrow.py`, `shape.narrowings_for` | low (to default by rule) | thinner appendages; costs about H of length per halving |
| 22.5°, tilted grid, hex | absent | whole new lattice | very high | different paradigm |

The cost and effect columns are inferences; the status and module columns come from code ([2026-10-10 spec](../docs/superpowers/specs/2026-10-10-branching-hub-packer-design.md); [2026-09-20 spec §9](../docs/superpowers/specs/2026-09-20-box-pleat-compiler-design.md)).

### Why the costs are ordered this way

The cost ordering follows from three invariants **[I]**.

**First, river routing is the cheapest structural technique.** Bends and wall-following stay within L∞ elevation fields, so `base.build` re-derives and verifies every crease, and `solve` and `certify` need no change.

**Second, level shifters break the one-unit strip.** `base.build` maps every vertex to a strip one grid unit wide, with w a period-2 triangle wave. A level shifter's whole purpose is a flap wider than one unit, so it breaks that construction rather than plugging into it. The Wong–Demaine condition would serve as its local feasibility check.

**Third, Pythagorean stretches break the L∞ map.** `base.build`'s map is defined only on axis-aligned and 45° quarter-triangles with s = strip(u) + σ·d∞. A stretch therefore needs either a new region kind or a crease overlay injected before `solve`. BP Studio's MIT-licensed `gops.ts` factorization and strategy order can be ported directly.

A stretch has two further problems:

- **Gap-free ownership.** It must coexist with gap-free cell ownership, which BP Studio never enforces and which is why COrigami deferred stretches.
- **Sliver faces.** It will produce sliver faces near a certifier whose `AREA_EPS` already sits 1.0000000203× from firing on starfish.

The certifier itself is angle-agnostic, so a stretch-bearing CP can still be checked.

## Conclusion

The literature frames box-pleating efficiency as a gadget problem: L∞ wastes up to √2 on diagonal pairs, and Pythagorean stretches buy it back. Pleatwright's numbers say otherwise for now. Its median grid is 1.30× a perimeter bound that no gadget can beat while flaps sit on the paper boundary (the bound holds for circle packing too) **[I]**. Simply keeping the smaller of two existing rungs brings that to 1.20× and puts the median flap scale within about 3% of TreeMaker's.

The remaining headroom is concentrated in a tail: dolphins, lizards, octopus, ants and the branching edits. That is where river routing and stretches would pay. The slack paper (39% of the median sheet, an average of about 34 layers per flap) is a quality problem more than an efficiency one. The community's answer to it is not a smaller grid. It is to move slack into rivers, to use it as level-shifted width, and to keep flaps in corners. That points Pleatwright's first gadget investment toward river routing and shifters over stretches.

Two decisions belong to the owner, not to the research:

- **Symmetry versus grid size.** Should a materially smaller unmirrored packing beat a mirrored one? This is the single largest measured lever.
- **The strip model.** Is the one-unit strip a permanent invariant? Level shifters, the community's main legibility tool, cannot exist without relaxing it.
