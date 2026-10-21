# Lang's box-pleating techniques for paper efficiency and model quality (Origami Design Secrets 2e, Lang's papers, and work built on them)

Source-status legend used throughout:
- **[P]** primary source read directly (Lang & Demaine Origami⁴ chapter, full text extracted from the PDF; Tsai's own account; BP Studio's own pages).
- **[I]** internal project source: this repo's box-pleat compiler spec and evidence, which paraphrase and quote *Origami Design Secrets* 2e (ODS2) Ch. 13/14 with page/section numbers. These are the project's own reading of the book, i.e. a **secondary** source. The book itself was not accessible online during this research.
- **[S]** search-result summary / catalogue listing (secondary; not full text).
- Material I recall from the book but could not find a source for is listed under **Gaps**, never under Cited Findings.

Internal source paths (absolute):
- `<repo>/docs/superpowers/specs/2026-09-20-box-pleat-compiler-design.md` (cited below as **BP-spec**)
- `<repo>/docs/superpowers/evidence/2026-09-20-box-pleat/README.md` (cited as **BP-evidence**)
- `<repo>/docs/superpowers/specs/2026-09-22-pleat-reassignment-design.md` (cited as **PR-spec**)

## 1. How does Lang define uniaxial box pleating (flaps as squares/rectangles on a grid, rivers as strips, elevation, hinge/axial/ridge structure, the molecule set)?

### Takeaway
Uniaxial box pleating (UBP) is tree theory with the L2 (Euclidean) metric replaced by the L∞ (Chebyshev) metric on an integer grid. Flap "circles" become squares centred on the tip; rivers become constant-width orthogonal channels with 90° bends; the hinge polygons tile the whole square ("all paper is assigned"); the molecule inside each polygon is its straight skeleton (45° ridges), and fold directions follow an elevation-contour rule. Lang & Demaine's Origami⁴ paper supplies the general (non-BP) definitions of uniaxial base, axial/ridge/gusset/hinge/pseudohinge creases, elevation and depth, and the universal molecule that UBP specialises.

### Cited Findings
**General uniaxial-base vocabulary (primary):**
- Definition [P]: a uniaxial base "can be partitioned into distinct regions, called flaps, and for which a particular line can be defined, called the axis"; each flap is incident to the axis, its perpendicular projection onto the axis is contained in the flap, the connections between flaps are hinges, all perpendicular to the axis, and a flap's length is the length of its projection on the axis. The tree graph is an edge-weighted graph whose edges are flaps and whose weights are flap lengths. — [Lang & Demaine, "Facet Ordering and Crease Assignment in Uniaxial Bases", Origami⁴ (2006), pp. 189–205, §2.1](https://erikdemaine.org/papers/TreeMaker_OSME2006/paper.pdf)
- Coordinates [P]: in the folded form a point's perpendicular distance from the axis is its *elevation* e, and its distance along the axis from a reference point is its *depth* d. Active paths have constant elevation 0, so they lie on the axis and must be folded: these are *axial creases*. — [Lang & Demaine, Origami⁴ §2.2](https://erikdemaine.org/papers/TreeMaker_OSME2006/paper.pdf)
- Crease families [P]: insetting an active polygon's boundary by h gives a constant-elevation polygon at elevation h; the inset polygon's corners trace *ridge creases*; a reduced path that becomes a line of constant elevation with higher paper on both sides is a folded *gusset crease*; *hinge creases* are lines of constant depth propagated from axial vertices and reflected at ridges; *pseudohinge* creases are constant-depth creases that are always folded and do not map to hinges. The crease pattern inside each polygon "is called the universal molecule". — [Lang & Demaine, Origami⁴ §2.2](https://erikdemaine.org/papers/TreeMaker_OSME2006/paper.pdf)
- Lang & Demaine state the TreeMaker algorithm applies to any convex polygon of paper, and that paper outside the convex hull of the leaf vertices "is effectively unused"; they "assume that the paper P and the convex hull of the leaf node vertices P_H are one and the same." — [Lang & Demaine, Origami⁴ §2.1–2.2](https://erikdemaine.org/papers/TreeMaker_OSME2006/paper.pdf)
- The term and concept "molecule" was coined by Toshiyuki Meguro. — [Lang & Demaine, Origami⁴ §1](https://erikdemaine.org/papers/TreeMaker_OSME2006/paper.pdf)

**The box-pleated specialisation (ODS2 Ch. 13, via internal and lecture sources):**
- Demaine (MIT 6.849 Fall 2012, Class 4 Q&A): in the box-pleated version of the tree method, "instead of disks, you have squares. And instead of rivers, you have these orthogonal channels of constant width"; gaps that appear can be filled by extending a square into a rectangle; the construction then puts in ridge creases ("something like a straight skeleton"), then hinge creases perpendicular to them. He calls ODS2 "the best writeup" and says the theory was begun by Demaine, Martin Demaine and Lang, around 2004. — [MIT OCW 6.849 Class 4 transcript](https://ocw.mit.edu/courses/6-849-geometric-folding-algorithms-linkages-origami-polyhedra-fall-2012/b67bcae394e440e6691812c6c9c6423d_ylQ5-9f5KIs.pdf)
- ODS2 Ch. 13 elements as the project adopted them [I]: hinge polygons enclose packing "circles"; rivers have constant width; ridges = straight skeleton; axial contours are launched from tips and bounced off ridges; elevation contours lie between them; there is an elevation rule for mountain/valley assignment; and rule 4, "all paper is assigned". — BP-spec, prior-art table row 1
- Minimum hinge polygon ("rule 2") [I]: the on-paper part of the 2r×2r square *centred* on the tip, so r×r for a corner tip, 2r×r for an edge tip, 2r×2r for an interior tip. A tip may lie on the paper boundary but never on a hinge. — BP-spec §11 item 8
- Hinge-distance invariant (Lang §13.3) [I]: the minimum perpendicular distance from a tip to any hinge segment of its polygon is exactly r. Expansion in every direction "truly lengthens" the flap, so a polygon may grow (to fill gaps) only if it keeps at least one hinge at distance r. — BP-spec §11 item 9
- Rivers [I]: strips of constant width with 90° bends only; constant width is checked by Lang's test that every 45° ridge from a bend corner lands on the opposite bank's corner. — BP-spec §4 invariants
- Path condition [I]: for every leaf pair, the Chebyshev (L∞) distance between tips must be ≥ the tree path length in grid units (Lang §13.3 combined with the Ch. 11 path inequality in the ∞-norm). — BP-spec §4
- Ridges (Lang §13.4) [I]: the straight skeleton of a rectilinear polygon, built from 45° bisectors at every corner: a square gives two diagonals, a rectangle diagonals plus a spine, L/T shapes the general case. Every skeleton vertex must land on the half-grid, and an odd side length breaks this (the §14.3 parity diagnostic). — BP-spec §5.3
- Elevation rule (Lang §13.5, white side up) [I]: an axis-parallel crease that is higher on both sides is a valley, lower on both sides is a mountain, and higher on one side is unfolded (a slope). — BP-spec §5.5; PR-spec (keeps this as the initial labelling heuristic)
- The elevation field is global (Lang §13.5) [I]: axials continue across hinges and rivers into neighbouring polygons, and "the axial contours from a hinge polygon often do NOT line up with the axial contours from the neighboring polygon"; two misaligned axials leave a half-elevation crest between them, a folded pleat. — BP-spec §11 item 14
- Flap-length invariant [I]: every elevation-0 path from a tip must meet the hinge at arc length exactly r. — BP-spec §11 item 7

**Worked examples (ODS2) as used by the project [I]:**
- Fig. 13.12–13.17 toy: five leaves of 1 and 2 units plus one river packs at exactly N = 6, with the lower-left square expanded to a rectangle. — BP-spec §7 goldens
- §13.6 generic beetle: legs 4/6/8 with body rivers of 1. Its centre column is fully axial, and Lang adds circles (stubs) to make the centre column axial. — BP-spec §7 and §11 item 2
- §9.7 tarantula: shows a valley along the centre column (cited as precedent for not forcing the centre column axial). — BP-spec §11 item 2
- Demaine's lecture walks through the ODS2 box-pleated "Scorpion varileg" and an insect example: bilateral layout, squares and channels, gaps filled by rectangles, then ridges and hinges. — [MIT OCW 6.849 Class 4 transcript](https://ocw.mit.edu/courses/6-849-geometric-folding-algorithms-linkages-origami-polyhedra-fall-2012/b67bcae394e440e6691812c6c9c6423d_ylQ5-9f5KIs.pdf)

**Book structure [S]:**
- ODS2 adds coverage of uniaxial box pleating, introduces hex pleating, and describes "methods of generalizing polygon packing to arbitrary angles". — [Routledge listing](https://www.routledge.com/Origami-Design-Secrets-Mathematical-Methods-for-an-Ancient-Art-Second/Lang/p/book/9781568814360)
- One library record gives "Polygon packing" as chapter 14 of 15, and new or highly revised chapters on box pleating, uniaxial box pleating and polygon packing. — [ISI Kolkata OPAC](https://library.isical.ac.in/bib/423279)
- Lang's own site gives the 2nd edition as 2011, adding "new chapters on advanced box-pleating techniques, hex pleating, and polygon packing". — [langorigami.com publications](https://langorigami.com/publications/). The library catalogues list it as CRC/A K Peters 2012 (a 2011 vs 2012 date conflict, probably copyright year vs print year).

### Inferences
- UBP is the universal molecule restricted to rectilinear polygons. For rectilinear polygons the inset ("shrinking") process is exactly the straight skeleton, which puts every ridge at 45° and every axial and hinge at 0°/90°. That is why Kawasaki holds by construction on the grid (BP-spec §5.6 asserts this) and why no off-grid angles appear unless a gadget (a stretch) introduces them.
- Because the minimum polygon is centred on the tip and clipped by the paper, the placement class (corner / edge / interior) sets each flap's paper cost directly. See Q2.

### Gaps
- The exact wording of ODS2 Ch. 13's rules 1–4 (only rule 2 and rule 4 are paraphrased internally) and the figure numbers for the river, ridge and elevation figures could not be verified against the book text.
- Whether ODS2 uses the phrase "box pleat molecules" or a named BP molecule set (beyond "the universal molecule on a rectilinear polygon = straight skeleton") was not found. I recall that ODS2 Ch. 13 discusses gussets and "pleat" contours inside non-square polygons, but this is unverified.

## 2. What are Lang's techniques for packing more efficiently (rivers vs circles, corner/edge/middle placement, rectangles, offsets, level shifting, Pythagorean stretches, 22.5° hybrids, hex pleating)?

### Takeaway
The verified levers are: (a) **placement class**: corner tips cost r², edge tips 2r², interior tips 4r²; (b) **rectangle expansion / gap fill**, which removes holes without changing flap length if one hinge stays at distance r; (c) **level shifters**, which reconcile mismatched elevation families where two contour systems meet; (d) **Pythagorean stretches** and their generalisation **GOPS** (Lang & Tsai, Origami⁷ 2018), which let flaps sit at non-45° offsets whose distance is an integer hypotenuse. Stretches are what bring box pleating "close to" circle-packing efficiency. (e) **hex pleating** (60° grid) and arbitrary-angle polygon packing are ODS2 additions. Of these, the mechanics of (c) and (d) are only partly documented in sources I could reach.

### Cited Findings
**Placement class (corner > edge > interior):**
- Minimum polygon sizes [I]: r×r corner, 2r×r edge, 2r×2r interior. The project's lower bound counts r² for the four corners and 2r² for the rest, and interior tips cost 4r². — BP-spec §11 item 8
- The packer ranks tip candidates as touches a paper corner > touches a paper edge > interior, citing "Lang's layer argument, Ch. 9 §9.4 / Ch. 14 §14.2". [I] — BP-spec §5.2
- Corner tips may grow along both edges, giving a blunt flap whose tip is a raw edge at a = 0, which is valid. An edge tip may grow along its edge or away from it, but not both. An interior tip may have arms along one axis only. [I] — BP-spec §11 item 12

**Rectangles / gap filling:**
- Box pleating "tend[s] to get more gaps", and "instead of just having a square, you can extend it out to be a rectangle" to fill holes. — [MIT OCW 6.849 Class 4 transcript](https://ocw.mit.edu/courses/6-849-geometric-folding-algorithms-linkages-origami-polyhedra-fall-2012/b67bcae394e440e6691812c6c9c6423d_ylQ5-9f5KIs.pdf)
- Constraint [I]: gap fill may add a cell to a polygon only if at least one hinge segment stays at distance r, otherwise the flap becomes longer than the tree says. — BP-spec §11 items 9, 11

**Ch. 14 polygon-packing toolkit (names and sections as recorded internally) [I]:**
- ODS2 Ch. 14 (Polygon Packing) contains "level shifters, Pythagorean stretches, meanders, parity rules (§14.3), dense bouncing (§14.6 — why the grid is mandatory), hex pleating, combs". Ch. 6 covers grafting and Ch. 5 point splitting. — BP-spec, prior-art table rows 2–3
- Level-shifter site (Lang §14.1) [I]: two mismatched elevation families meeting head-on, typically at the paper edge. In the project's 2026-09-22 run, all 6 contour-stage failures (cat, elephant, bat, dolphin, scorpion, ant) were collisions at a point on the paper edge, which the project classified as level-shifter sites. — BP-evidence, failure list; BP-spec §5.4
- A flap grown along its raw edge that conflicts with a neighbour pinned at elevation 0 is "the corpus's dominant failure and a Ch. 14 level-shifter site". [I] — BP-spec §11 item 14
- Parity (§14.3) [I]: polygon skeleton vertices must fall on the half-grid, so odd-sided polygons cause trouble. — BP-spec §5.3
- Dense bouncing (§14.6) [I]: the reason the grid is mandatory. Contours bouncing between ridges terminate on an integral grid, and the project treats non-integral lengths as refused for that reason. — BP-spec prior-art row 2; §5.4

**Pythagorean stretches, GOPS and GPS:**
- Tsai read ODS2 (late 2016) and used its Ch. 14 polygon-packing idea on his Blue Crab. While working on *offset Pythagorean stretches*, he asked "what will happen if I use an offset greater than one?". The result is GOPS (generalized offset Pythagorean stretch), which has "a much larger solution space"; its integral nature lets separate GOPS gadgets combine into compound solutions, and he extended it to three or more flaps. [P] — [Tsai, "The story of Box Pleating Studio" (2021)](https://origami.abstreamace.com/2021/06/02/the-story-of-box-pleating-studio/)
- Lang was independently developing a generalisation called GPS, and "GPS is exactly the complement of GOPS". The area of the overlapping rectangle matters for both, which led to a construction based on integer factorization. Perfect Pythagorean stretches are rare, and imperfect ones often come with gusset slivers. [P] — [Tsai blog](https://origami.abstreamace.com/2021/06/02/the-story-of-box-pleating-studio/); [S] [search summary of the same](https://bp-studio.github.io/notes.html)
- Joint paper: Lang & Tsai, "Generalized Offset Pythagorean Stretches in Box-Pleated Uniaxial Bases", *Origami⁷* (7OSME, Oxford 2018), Vol. 2, pp. 591–606. Follow-up: Tsai, "On the Constructions of Generalized Offset Pythagorean Stretch Patterns", 8OSME (2025). — [BP Studio Notes](https://bp-studio.github.io/notes.html); [Tsai blog](https://origami.abstreamace.com/2021/06/02/the-story-of-box-pleating-studio/); [Springer chapter page (Tsai 2025)](https://link.springer.com/chapter/10.1007/978-981-96-6711-6_1)
- Stretch patterns based on the 3-4-5 Pythagorean triple "are commonly called Kamiya patterns", after Satoshi Kamiya's work with them, and Tsai says such solutions are very common. [P] — [Tsai blog](https://origami.abstreamace.com/2021/06/02/the-story-of-box-pleating-studio/)
- Efficiency claim [P]: "pure box pleating is well-known for not being very efficient in utilizing paper area"; stretching gadgets "such as Kamiya patterns and the more generalized GOPS" can bring efficiency close to optimal circle packing. — [BP Studio homepage](https://bp-studio.github.io/)
- BP Studio automates GOPS: the user drags flaps, and the app computes the stretches and river shapes. — [Tsai blog](https://origami.abstreamace.com/2021/06/02/the-story-of-box-pleating-studio/); [BP Studio GitHub](https://github.com/MuTsunTsai/box-pleating-studio)
- The project's spec names Pythagorean stretches as "the designed remedy" for the box-pleating efficiency penalty. [I] — BP-spec §9

**Other angle systems:**
- ODS2 introduces hex pleating and generalises polygon packing to arbitrary angles. — [Routledge listing](https://www.routledge.com/Origami-Design-Secrets-Mathematical-Methods-for-an-Ancient-Art-Second/Lang/p/book/9781568814360)
- Demaine's lecture shows examples of tree-method bases on 22.5° and 60° grids, an "alternate version of the tree method that doesn't just use arbitrary circles, but tries to stay on these nice grids". — [MIT OCW 6.849 Class 4 transcript](https://ocw.mit.edu/courses/6-849-geometric-folding-algorithms-linkages-origami-polyhedra-fall-2012/b67bcae394e440e6691812c6c9c6423d_ylQ5-9f5KIs.pdf)
- BP Studio describes box pleating as the standard framework for modern complex origami, with creases more predictable than in the traditional 22.5° system or circle packing. — [BP Studio homepage](https://bp-studio.github.io/)

### Inferences
- **Placement-class arithmetic (from the cited polygon sizes).** A flap of length r costs r² on a corner, 2r² on an edge and 4r² in the interior, so moving the longest flaps to corners is the single biggest area lever. With a total-area lower bound N² ≥ Σ cost, the grid lower bound N_lb scales as sqrt(Σ cost), so for a fixed tree, more corner and edge tips give a smaller N and a larger scale 1/N.
- **Why stretches recover efficiency.** In L∞ two tips separated by (Δx, Δy) are only "distance max(Δx, Δy)" apart, while the paper actually holds sqrt(Δx² + Δy²) of separation. A pair placed diagonally wastes up to a factor of √2 ≈ 1.414 in required separation. A Pythagorean stretch with integer triple (a, b, c) lets the active path run at the triple's angle, so the pair needs only c = sqrt(a² + b²) of separation rather than max(a, b) ≥ c in L∞-only packing. This is the mechanism by which BP "approaches circle packing" (consistent with Tsai's and BP Studio's claims). The ≈41% worst-case per-pair penalty may also be where the retracted "up to 40%" figure came from (see Q3), though nothing found confirms that.
- **Polygon-to-circle area ratios (exact geometry, my calculation).** The area of the polygon circumscribing a circle of radius r, divided by πr², is 4/π ≈ 1.273 for a square (box pleating), 2√3/π ≈ 1.103 for a hexagon (hex pleating), and 8·tan(22.5°)/π ≈ 1.055 for an octagon (22.5°). This orders the local "shape waste" BP > hex > 22.5° > circles. It is an area heuristic only: the real cost is set by the metric on paths, not per-flap area.

### Gaps
- **Pythagorean stretch construction details (unverified recollection, needs ODS2 §14):** that the basic PS joins two flaps whose tips are offset by (a, b) on the grid with c = sqrt(a² + b²) equal to the summed tree distance, producing a small region of non-45° creases (the triple's angles, e.g. atan(3/4) ≈ 36.87°) bounded by gussets. Whether Lang coined the name "Pythagorean stretch" in ODS2, or it predates the book (Kamiya, Meguro, Murakami), is unconfirmed. Tsai credits independent earlier work on similar patterns to Toshiyuki Meguro and Yuya Murakami ([Tsai blog](https://origami.abstreamace.com/2021/06/02/the-story-of-box-pleating-studio/)).
- **Level shifter geometry:** no source I reached describes the actual crease gadget (my recollection is that it is a short 45° or step pleat that shifts the elevation of a contour family by one half unit across a hinge so that axials line up). Only the site definition (Lang §14.1, via BP-spec) is cited.
- **Meanders and combs:** named in ODS2 Ch. 14 per BP-spec, but their construction and efficiency effect were not found. I recall that meanders snake a river to lengthen it inside a fixed footprint and that combs are arrays of parallel equal flaps; both are unverified.
- **"Hinge shifting", "offsets", "side flaps vs corner flaps" as Lang's terms:** not found in any reachable source; possibly vocabulary from other designers or from BP Studio.
- **Measured effects of stretches** (e.g. "grid reduced from N to M on model X"): no worked numbers found for ODS2 or Lang & Tsai 2018. The paper's figures are behind the Origami⁷ volume.
- **Hex pleating efficiency figure from Lang:** not found. Only the area ratio I calculated above.

## 3. What does Lang say about efficiency metrics, and what is the theoretical efficiency gap between box pleating and circle packing?

### Takeaway
Lang's efficiency metric is the **scale m**, the ratio of folded flap length to tree edge length, maximised by the tree-theory NLCO. For box pleating the analogue is 1/N (paper per grid unit). Lang states qualitatively that circle/river packing is the optimal uniaxial packing, so box pleating is "by definition, less efficient" but "the penalty is often very small" (ODS2 Ch. 13, p. 573, as quoted internally). He gives **no percentage**, and the "up to 40%" figure previously attributed to him was retracted by this project. The project's own measurement shows a mean penalty of about 5% against TreeMaker, but box pleating covers the full square, while the circle optimum is computed on the leaf hull.

### Cited Findings
- **Scale m as Lang's efficiency measure [P]:** "We therefore introduce a scaling factor m, which is the ratio between the length of an edge of the tree graph and the length of the corresponding flap in the folded form"; constraint |v_i − v_j| ≥ m·l_ij; "The scale is a measure of the efficiency of the folded base; a base with a large scale will have a folded form that is relatively large compared to the starting paper"; the optimum is "maximize m over {v_i} subject to |v_i − v_j| ≥ m l_ij, v_i ∈ P." — [Lang & Demaine, Origami⁴ §2.1, Eqs. (1)–(3)](https://erikdemaine.org/papers/TreeMaker_OSME2006/paper.pdf)
- **Optimum solutions may be non-well-formed [P]:** it is "not uncommon" for the optimum to leave leaf vertices "rattling around" in the interior; adding edges to the tree or lengthening edges (stubs) usually reaches a well-formed state "without reducing the size of the original graph". — [Lang & Demaine, Origami⁴ §2.1](https://erikdemaine.org/papers/TreeMaker_OSME2006/paper.pdf)
- **Box pleating vs circles (Lang, ODS2 Ch. 13 p. 573, via internal quotation) [I]:** circle/river packing is provably the most efficient uniaxial packing, so box pleating "must be, by definition, less efficient", but "the penalty is often very small, and uniaxial box-pleated structures can still be surprisingly efficient." The project's earlier attribution of "up to 40%" to Lang "was an error, now retracted" (spec §11.18). — BP-evidence "Scale penalty"; BP-spec §6, §11 item 18
- **Demaine's characterisation [P-lecture]:** box pleating is "a little bit less efficient, because instead of using a disk, which is the minimum amount of paper you need to make a flap, you're using a square. So you're wasting those little corners. But not that much more inefficient." — [MIT OCW 6.849 Class 4 transcript](https://ocw.mit.edu/courses/6-849-geometric-folding-algorithms-linkages-origami-polyhedra-fall-2012/b67bcae394e440e6691812c6c9c6423d_ylQ5-9f5KIs.pdf)
- **Measured gap (internal, 2026-09-22, 16 subjects, scale_bp/scale_tm in paper length per grid unit) [I]:** min 0.732 (spider), median 0.8845, mean 0.9523 (a 4.8% mean penalty), max 1.297 (lizard); 6/16 subjects read ≥ 1.0. Restricted to the 10 subjects with a validated fold, the mean is 0.9519. Caveat: these are flap-length-per-grid-unit ratios, not area efficiency. — BP-evidence "Scale penalty"
- **Coverage asymmetry [I]:** TreeMaker creases only the convex hull of leaf vertices (consistent with Lang & Demaine's P = P_H assumption above). The project measured hull coverage of 0.46–0.98 on TreeMaker outputs against exactly 1.000 for every emitted box-pleated fold, because rule 4 ("every cell belongs to some polygon") makes full coverage the construction. — BP-evidence "Coverage"; [Lang & Demaine §2.2](https://erikdemaine.org/papers/TreeMaker_OSME2006/paper.pdf)
- **Complexity of the optimum [P]:** deciding whether a given set of circles packs into a square (or rectangle, or equilateral triangle) is NP-hard; any set of circles of total area 1 fits in a square of side 4/√π ≈ 2.2567. — [Demaine, Fekete & Lang, "Circle Packing for Origami Design Is Hard", arXiv:1008.1224 (5OSME)](https://arxiv.org/abs/1008.1224)

### Inferences
- The fair BP-vs-circle comparison must hold the paper fixed. Because the circle-packing optimum ignores the area outside the leaf hull (Lang & Demaine), a box-pleated base that uses the whole square can come out *ahead* on usable-paper accounting even when its scale is slightly lower. The 6/16 internal subjects with ratio ≥ 1.0 also show that BP's integer search sometimes finds packings the TreeMaker local optimiser misses.
- A defensible theoretical bound on the per-pair separation penalty is √2 (L∞ vs L2 along a 45° diagonal) and 1.0 along the axes. Real models land well inside this because most active paths in a good BP layout are axis-aligned, which is consistent with Lang's "often very small".

### Gaps
- No Lang statement of a numerical worst case or average BP penalty was found (and the internal record says he makes none).
- No Lang-defined efficiency metric specific to box pleating (e.g. "grid units per square side" as a named figure of merit) was found. Designers commonly quote the grid size N, which the internal spec uses as scale = 1/N, but I found no Lang source naming it.

## 4. Quality techniques: flap thickness, narrowing/sinking, flap width, color change via grafting, symmetry, layer distribution, collapsibility

### Takeaway
The sources I could reach cover quality only partly. Verified: corner/edge placement is preferred for layer (thickness) reasons (Lang Ch. 9 §9.4 and Ch. 14 §14.2, as cited internally); box-pleated rivers and flaps have constant width ("tabs that are a constant width", Demaine); a bilateral half-square-plus-mirror layout is Lang's symmetry method; and fold-direction plus layer order is a separate solvable step for uniaxial bases (Lang & Demaine), but NP-complete for general box-pleated crease patterns (Akitaya et al.). Grafting (Ch. 6) is the book's color-change and base-modification tool, but no source I reached gives its specifics.

### Cited Findings
- **Corner/edge for thickness [I]:** the corner > edge > interior ranking is attributed to "Lang's layer argument, Ch. 9 §9.4 / Ch. 14 §14.2". — BP-spec §5.2
- **Constant-width flaps [P-lecture]:** "You tend to get tabs that are a constant width like this", and box-pleated bases are "so much easier to fold... You don't have to construct really weird angles... A lot cleaner." — [MIT OCW 6.849 Class 4 transcript](https://ocw.mit.edu/courses/6-849-geometric-folding-algorithms-linkages-origami-polyhedra-fall-2012/b67bcae394e440e6691812c6c9c6423d_ylQ5-9f5KIs.pdf)
- **Bilateral symmetry by half-square plus mirror [I]:** the project adopted "Lang's half-square + mirror" as the packing approach (all its subjects are bilateral), rejecting COrigami's whole-square symmetric-filter packing. — BP-spec prior-art row 4. Demaine's lecture describes the same design move ("I'd like to make the left half of the paper same as the right half"). — [MIT OCW 6.849 Class 4](https://ocw.mit.edu/courses/6-849-geometric-folding-algorithms-linkages-origami-polyhedra-fall-2012/b67bcae394e440e6691812c6c9c6423d_ylQ5-9f5KIs.pdf)
- **Plan-view centre column [I]:** Lang's plan-view uniaxial base has an axial contour down the centre column; forcing it fully axial needs axial stubs ("Lang adds circles for exactly this, §13.6"). — BP-spec §2.4, §11 item 2
- **Stacking order / crease assignment [P]:** creases, assignment and stacking order together fully describe a flat fold. Lang & Demaine give "for the first time a relatively simple algorithm for crease assignment in a uniaxial base" via a facet-ordering digraph satisfying Justin's layer conditions. Kawasaki holds by design, and Maekawa follows if Justin's conditions hold. The proof was deferred ("the subject of ongoing work"), but the algorithm was tested "on many individual cases, including intentionally pathological test structures, with success". — [Lang & Demaine, Origami⁴ §1, §3, conclusion](https://erikdemaine.org/papers/TreeMaker_OSME2006/paper.pdf)
- **Hardness for box pleating in general [S]:** flat-foldability of a box-pleated crease pattern (creases a subset of the square grid plus diagonals) is NP-complete (Akitaya, Cheung, Demaine, Horiyama, Hull, Ku, Tachi, Uehara, JCDCGG 2015 / LNCS 9943, pp. 167–179, 2016). The paper also introduces an implicit representation of global layer order and corrects an error in Bern–Hayes's crossover gadget. — [Akitaya et al., "Box Pleating is Hard" (Jason Ku's PDF)](https://scripts.mit.edu/~jasonku/pdf/BOXPLEATINGHARD_LNCS2016.pdf); [Demaine paper page](https://erikdemaine.org/papers/BoxPleatingHard_JCDCGG2015/)
- **The base must be stackable, not just labelled [I]:** pleat reassignment (searching M/V labellings of a fixed crease set) moved the project's emitting subjects from 2/10 to 8/10 layer-order-consistent, which supports Lang's elevation rule as the right initial labelling but not a sufficient one. — BP-evidence "Layer order"; PR-spec §ODS §13.5 row
- **Grafting / point splitting** are ODS Ch. 6 / Ch. 5 base-modification techniques. — BP-spec prior-art row 3; [Routledge listing](https://www.routledge.com/Origami-Design-Secrets-Mathematical-Methods-for-an-Ancient-Art-Second/Lang/p/book/9781568814360)

### Inferences
- In box pleating, flap width is set by the polygon's short dimension and the river widths, so a narrower finished flap comes from (a) an elongated rectangle polygon (arms along one axis, BP-spec item 12) or (b) post-base narrowing and sinking. The first costs nothing in N when it fills an existing gap.
- Grid parity (§14.3) is also a quality constraint: odd-sided polygons put skeleton vertices off the half-grid, which forces off-grid reference points and is exactly what box pleating exists to avoid.

### Gaps
- **Color change via grafting**: no reachable source. My unverified recollection is that ODS Ch. 6 grafts a border strip around a base so that flap tips can be color-changed (white vs colored side). No BP-specific color-change gadget was found.
- **Narrowing/sinking specifics** (Lang's "sink to thin a flap", closed vs open sinks in BP bases), **layer-count distribution metrics**, and **lockability**: not found in reachable sources.
- **Collapsibility of box-pleated bases** (all creases collapsing simultaneously, the practical "collapse" difficulty): mentioned only qualitatively ("easier to fold"). No Lang metric was found.

## 5. Lang's later work and algorithmic formulations (Twists, Tilings & Tessellations; OSME papers; TreeMaker; automation; complexity)

### Takeaway
After ODS2, Lang's BP-specific research output that I could confirm is the Lang & Tsai Origami⁷ (2018) GOPS/GPS paper, with its integer-factorization construction. Automation of BP uniaxial design is Tsai's Box Pleating Studio (released end of 2020), not a Lang tool. *Twists, Tilings, and Tessellations* (2017) is about geometric folding rather than uniaxial bases. On the algorithmic side: tree theory is an NLCO (Lang 1996); circle packing for origami is NP-hard (Demaine, Fekete & Lang 2010); uniaxial crease assignment and stacking order have a proposed polynomial facet-ordering algorithm (Lang & Demaine 2006, proof deferred); and general box-pleated flat-foldability is NP-complete (Akitaya et al. 2015/16). A Demaine–Demaine–Lang manuscript, "Mathematics of Origami Design", was unfinished as of 2012.

### Cited Findings
- *Twists, Tilings, and Tessellations: Mathematical Methods for Geometric Origami* (2017) covers "the mathematics of twists, tilings, tessellations, and other geometric folding". — [langorigami.com publications](https://langorigami.com/publications/)
- Lang & Tsai (2018), Origami⁷ Vol. 2 pp. 591–606; GOPS (Tsai: offsets > 1, compound and multi-flap) and GPS (Lang) are complements; integer-factorization construction; earlier similar patterns by Meguro and Murakami. — [Tsai blog](https://origami.abstreamace.com/2021/06/02/the-story-of-box-pleating-studio/); [BP Studio Notes](https://bp-studio.github.io/notes.html)
- BP Studio: development began early 2018 to automate GOPS; first public release at the end of 2020; it uses "configurations" and "devices" as data abstractions. Tsai's "perhaps a tenfold speed-up" for designers is his estimate, not a measurement. — [Tsai blog](https://origami.abstreamace.com/2021/06/02/the-story-of-box-pleating-studio/)
- BP Studio credits Lang for inspiring GOPS and thanks Jason S. Ku for computational-geometry insights. — [BP Studio GitHub README](https://github.com/MuTsunTsai/box-pleating-studio)
- Tree theory history [P]: Meguro and Lang independently devised disk-packing design techniques in the 1990s; Lang gave the first computational-geometric description in 1996 as an NLCO; molecules (Meguro's term) fill the vertex pattern; the method was implemented in TreeMaker. — [Lang & Demaine, Origami⁴ §1](https://erikdemaine.org/papers/TreeMaker_OSME2006/paper.pdf)
- Uniaxial facet ordering [P]: the ordering is expressed as a digraph, and the authors stress "the primacy of the ordering relationship, rather than the crease assignment, as the fundamental mathematical description". — [Lang & Demaine, Origami⁴ conclusion](https://erikdemaine.org/papers/TreeMaker_OSME2006/paper.pdf)
- Box Pleating is Hard (NP-complete flat-foldability for BP crease patterns). — [Akitaya et al. 2016](https://scripts.mit.edu/~jasonku/pdf/BOXPLEATINGHARD_LNCS2016.pdf)
- Circle Packing for Origami Design Is Hard. — [Demaine, Fekete, Lang, arXiv:1008.1224](https://arxiv.org/abs/1008.1224)
- Demaine (2012): "We are working on this giant manuscript. It's currently called the Mathematics of Origami Design", aimed at proving the tree method always works and generalising it to box-pleated variants; "not finished". — [MIT OCW 6.849 Class 4 transcript](https://ocw.mit.edu/courses/6-849-geometric-folding-algorithms-linkages-origami-polyhedra-fall-2012/b67bcae394e440e6691812c6c9c6423d_ylQ5-9f5KIs.pdf)
- Universal box-pleated (tetrakis) crease pattern folds any polycube (Benbernou, Demaine, Demaine, Ovadya); this is non-uniaxial "classical" box pleating. — [arXiv:0909.5388](https://arxiv.org/pdf/0909.5388)

### Inferences
- For a pipeline like this one (integer grid, packer plus solver), the most transferable algorithmic results are: (1) the GOPS/GPS integer-factorization construction, which is directly enumerable on a grid and is the published route to closing the BP-vs-circle gap; (2) the Lang–Demaine facet-ordering digraph for uniaxial bases, which suggests uniaxial structure is what makes layer ordering tractable even though BP flat-foldability is NP-complete in general.

### Gaps
- The full text (constructions, figures, any measured efficiency gains) of Lang & Tsai 2018 and Tsai 2025 was not accessible (paywalled proceedings).
- Whether TreeMaker 5 has any box-pleating mode or notes: not found. TreeMaker as described by Lang & Demaine is circle/NLCO-based.
- I found no Lang OSME paper on uniaxial box pleating itself (as opposed to stretches) in Origami⁵–⁸. Searches for an Origami⁶ BP paper returned nothing. The ODS2 chapters appear to be the canonical statement.
- The proof of the Lang–Demaine ordering algorithm: deferred in 2006, and its later status is unknown from these sources.

## 6. Attribution: who invented or named what

### Takeaway
Box pleating as a style dates to the 1960s and is credited to Neal Elias. Disk/circle packing tree theory belongs to Lang and Meguro (independently, 1990s), with "molecule" coined by Meguro. Uniaxial box pleating theory began with Demaine, Demaine and Lang (around 2004) and was written up in ODS2. 3-4-5 stretch patterns are called "Kamiya patterns" after Satoshi Kamiya. GOPS is Tsai's and GPS is Lang's, published jointly in 2018, with prior similar work by Meguro and Murakami. BP Studio is Tsai's. Jason Ku appears as a co-author of the BP hardness result and a BP Studio advisor, not as an inventor of any of these techniques in the sources found.

### Cited Findings
- Box pleating "developed and popularized by Neal Elias in the 1960s". — [Benbernou et al., arXiv:0909.5388](https://arxiv.org/pdf/0909.5388). Lang & Demaine list Elias, Hulme, Engel and Maekawa among designers of the box-pleating-onward era. — [Origami⁴ §1](https://erikdemaine.org/papers/TreeMaker_OSME2006/paper.pdf)
- Meguro and Lang co-originated disk-packing design; Meguro coined "molecule". — [Origami⁴ §1](https://erikdemaine.org/papers/TreeMaker_OSME2006/paper.pdf)
- Uniaxial BP theory: begun by Erik Demaine, Martin Demaine and Lang around 2004. — [MIT OCW 6.849 Class 4](https://ocw.mit.edu/courses/6-849-geometric-folding-algorithms-linkages-origami-polyhedra-fall-2012/b67bcae394e440e6691812c6c9c6423d_ylQ5-9f5KIs.pdf)
- Kamiya patterns (3-4-5); GOPS (Tsai); GPS (Lang); earlier similar work by Meguro and Murakami. — [Tsai blog](https://origami.abstreamace.com/2021/06/02/the-story-of-box-pleating-studio/)

### Inferences
- Treat "level shifter", "meander" and "comb" as Lang ODS2 Ch. 14 vocabulary, since the internal spec lists them as Ch. 14 content. Treat "Pythagorean stretch" as at least *used* in ODS2: Tsai describes reading ODS2 Ch. 14 and then working on offset Pythagorean stretches. That sequencing suggests, but does not prove, that the term comes from ODS2.

### Gaps
- Who first named "Pythagorean stretch", and whether Brandon Wong, Jason Ku or others named specific BP gadgets (e.g. Ku's work on "flaps by pleat layout"), could not be confirmed.
- The attribution of the 22.5° design system (often associated with Kamiya, Meguro and Jun Maekawa) is unconfirmed here, since no reached source covers it.
