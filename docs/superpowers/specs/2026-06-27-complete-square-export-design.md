# Design: complete-the-square FOLD export

**Date:** 2026-06-27
**Status:** Approved design, pre-implementation
**Roadmap:** Refinement under A-3 in `docs/followups-web-ui-and-foldability.md`
(the "REFINEMENT 2026-06-27" note); foundation slice ahead of item 5 / A-9.

## 1. Purpose

A user e2e run showed the 3D viewport rendering the unfolded paper as a **polygon,
not a square**. Root cause (confirmed): TreeMaker creases only the convex hull of
the leaf nodes, and `TreemakerWrapper.cpp::ExportFold` faithfully emits only the
vertices/creases TreeMaker built — so the square's uncreased corners are **omitted
from the `.fold` entirely** (committed `bear-base.fold`: border is a convex 20-gon =
42% of the sheet; the corner 58% is absent; only 1 of 4 square corners is a vertex).

The base is mathematically valid and A-3=ACCEPT stands for *foldability*, but the
artifact is a hull crease pattern, not a square. This sub-project makes the exported
FOLD a **true square**: hull creased, corners present as flat uncreased faces.

**Success criterion (agreed):** the served / linted / downloaded `.fold` renders as
a square in the viewport (0% fold), and folding to 100% does not explode or tear.
Realistic corner *tucking* is explicitly out of scope (it would require deducing
mountain/valley assignments TreeMaker never produced — molecule-level work).

## 2. Architecture & placement

One new pure-Python module, no engine/C++ change:

```
mcp_harness/
  square_complete.py        ← NEW: complete_square(fold, paper_w, paper_h) -> fold
  free_paper.py             ← reused (_on_boundary, _perimeter_coord,
                              _rect_corners) — no change
  server.py                 ← MODIFIED: call complete_square in the compile worker
  tests/test_square_complete.py  ← NEW
```

`complete_square(fold: dict, paper_w: float, paper_h: float) -> dict` takes the
exported hull FOLD (parsed) and returns a square FOLD with corner vertices, border
edges, and reassigned chords added. It is pure geometry: no engine, MCP, or JVM
imports — unit-testable in isolation, mirroring `free_paper.py`'s discipline.

**Wiring:** in `server.py`, the compile worker (`_worker_full_base` /
`draft_and_compile_full_base`, which returns `engine.build_and_export()`) parses the
FOLD string, calls `complete_square`, and re-serializes — so every downstream
consumer (viewport, the agent's `validate_flat_foldability` lint, and the browser
download) receives the squared FOLD. `_worker_free_paper` is untouched.

## 3. The geometry algorithm

Operates on the FOLD's own edge graph (the exported `"B"` border loop is already the
hull outline — we do not recompute the hull from leaf nodes):

1. Parse `vertices_coords`, `edges_vertices`, `edges_assignment`.
2. Find the `"B"` (border) edge loop = the current hull outline polygon.
3. Classify each border-loop vertex with `free_paper._on_boundary(v, w, h)`:
   - **on the square boundary** (a flap tip reaching a paper edge), or
   - **interior** (a chord vertex cutting a corner).
4. Add the square's 4 corners `(0,0),(w,0),(w,h),(0,h)` as vertices if absent.
5. Build the **true square border**: walk the rectangle perimeter
   (`free_paper._perimeter_coord` / `_rect_corners`); between consecutive
   on-boundary tips, emit `"B"` segments threading the square corners that fall in
   that arc. The result is a single closed `"B"` loop = the square outline.
6. **Reassign** every former border edge that is NOT a segment of the square
   boundary (the chords that cut corners) from `"B"` → `"F"` (flat): they are now
   interior edges between the creased hull and the flat corner paper.
7. **Faces:** emit only vertices + edges. The viewport bridge's edge→face builder
   (`FOLD.convert.*`) and the linter form the corner faces from the planar graph.
   - **Common case** (hull touches paper edges, e.g. the bear's 20-gon touching all
     four sides): the corner regions are already simple polygons — no extra edges.
   - **Fully-interior hull** (the A-1 "frame"/ring case, no tip on any edge): the
     square-minus-hull region is an annulus, which is not a simple face. Add radial
     `"F"` cuts from each square corner to the nearest hull-loop vertex so every
     resulting face is a simple polygon.

`"F"` edges carry foldAngle 0 (the bridge maps `M→-180, V→+180, else→0`), so the
flat corner paper stays coplanar at 0% and rides along without hinging — honest
"accept uncreased paper."

## 4. Data flow

```
draft_and_compile_full_base
  → engine.build_and_export()      (hull-only FOLD string, as today)
  → json.loads → complete_square(fold, w, h) → json.dumps   (NEW)
  → squared FOLD string returned
        ├── agent: validate_flat_foldability(squared)   (lint sees the square)
        └── web: stream to browser → viewport + download (square renders)
```

## 5. Lint interaction & error handling

The agent now lints the squared FOLD. Expected: corner vertices are degree-2 border
vertices (not Kawasaki-checked) and corner paper is flat, so squaring should **not
add** interior-vertex violations; the former hull-boundary points may even read as
**resolved** once the geometry closes. This is empirically unknown, so the plan
includes an explicit **measurement step**: lint the bear base before and after
`complete_square` and record the delta.

- **Success does not depend on the lint passing** — the deliverable is the square
  rendering and folding without breaking.
- **Fallback (if squaring introduces NEW false alarms):** square only the
  served/downloaded FOLD and keep the lint on the raw hull — a one-line wiring split
  in `server.py`. This finding would be brought back to the user; A-2's prompt
  teaching is **not** changed within this sub-project.
- **Degenerate inputs:** if the FOLD has no `"B"` loop, or is an `ERROR:` string, or
  the hull already fills the square, `complete_square` returns the FOLD unchanged.

## 6. Testing strategy

- **`complete_square` unit tests** (pure, no engine): on a synthetic hull FOLD —
  all 4 square corners present after; total face/area coverage = the full sheet;
  the `"B"` loop is exactly the square outline; former corner-cutting chords are now
  `"F"`; the planar graph yields simple faces (no annulus).
- **Fully-interior case:** a hull FOLD with no on-boundary tip → radial `"F"` cuts
  added; faces simple; square border closed.
- **Golden bear assertion:** regenerate the bear base through the compile worker and
  assert the squared FOLD has 4 square corners and full-sheet coverage (vs. today's
  1 corner / 42%).
- **Lint delta:** a measurement test/script recording bear lint before vs. after
  (informational — pins the observed behavior, not a pass/fail gate).
- **Viewport load:** manual/Playwright check that the squared bear renders as a
  square and folds without NaN/explosion (mirrors the A-3 procedure).

## 6b. Implementation outcome (2026-06-28) — FALLBACK applied

The §5 lint-delta measurement tripped the fallback. Measured on the bear base
(`probe_square_lint.py`):

- **Raw hull (what the agent lints): 10 violations** (0 M/V-fixable, all geometry)
  — the clean documented frontier the prompt teaches as ACCEPT.
- **Squared: 19 violations** (0 M/V-fixable; the extra 9 are `NUMBER_OF_FOLDS` at
  the former boundary tips, where an axial crease now terminates against the new
  flat corner face). Squaring makes the lint **worse**.

So per §5 we applied the **fallback**: squaring is **NOT** in the compile worker.
`server.py`'s workers return the raw hull (the agent lints that — the clean 10-geom
frontier, A-2 teaching intact). `complete_square` is applied only at the **display
boundary**: `web/server.py::_square_for_display` (viewport + download) and
`scripts/make_hull_frontier_fixture.py` (the committed static fixture). The
`_square_export` worker helper was removed.

**Robustness fix:** `complete_square` now snaps vertices within `1e-6` of a paper
edge exactly onto it (`_snap_to_boundary`), because the ALM optimizer leaves tips
~1e-7 off — just outside the `1e-7` `_on_boundary` tolerance — which otherwise
produced a degenerate near-coincident pair at a near-corner tip (e.g. the bear's
`(1,1)`).

**Viewport verdict (Playwright, vendored sim):** the squared bear fixture loads with
no bridge error, the bridge builds faces from edges, and at flat it renders as a
**square sheet** with the hull crease pattern in the middle and flat corners (see
`docs/square-export-bear.png`) — the "triangle, not square" symptom is resolved.
Driven to 100% the geometry is **bounded, 0 NaN, genuinely 3D** (no explosion/tear).
The squared pattern is not perfectly flat-foldable (the 19 violations), so the
dynamic fold animation is not physically clean — that is the deferred molecule-level
work (see §7 / the "what it would take" note), outside this slice's scope.

## 7. Out of scope (YAGNI)

- Realistic corner tucking / mountain-valley deduction for the former-border edges.
- Generative anatomy-detail fill (item 5 / A-9) — this slice only completes the
  paper square; it adds no new flaps.
- Any C++ / `ExportFold` change — squaring is a faithful post-export transform.

## 8. Deferred: a genuinely flat-foldable crease pattern — two distinct problems

The squared FOLD renders as a square and folds without exploding, but the crease
pattern is **not a clean, fully-flat-foldable molecule** — a user inspecting it noted
creases that appear to "hang." Diagnosis (`probe_dangling.py`, on the bear):

- **0 dangling (degree-1) creases** — no crease has a literal free end; everything
  connects.
- **17 odd-degree interior vertices** (degree 3, a couple degree 5). Flat-foldable
  interior vertices must be **even**-degree (Maekawa/Kawasaki), so these are the real
  `geometry` lint violations and the reason the pattern looks malformed.

There are **two distinct problems**, often conflated:

**Problem A — the raw molecule's hull-frontier (the dominant, pre-existing cause).**
The 17 odd-degree vertices are present in the RAW engine output, before any squaring,
and **all 17 lie ON the hull boundary; 0 are strictly interior** (verified:
every strictly-interior vertex is even-degree). So the molecule build is *clean inside
the hull* — this is NOT an incomplete/buggy molecule. The defect is purely the
hull-vs-square frontier: TreeMaker creases only the leaf hull, so each hull-boundary
vertex is missing the creases that would continue into the uncreased corner regions,
leaving it odd-degree. **The project previously chose to ACCEPT this (A-3)** on the
grounds that the base still folds to a stable 3D shape (the failures read as Oriedita
false-negatives). That decision was about *foldability*, not *pattern cleanliness* —
under the "is this a clean crease pattern?" lens, A is unresolved and would partly
re-open A-3.

**Problem B — the squaring corner-stitching (what this slice added).** `complete_square`
flips the hull chords to flat `"F"` and adds flat corner faces. That makes it *look*
square but does not give the boundary vertices flat-foldable creases — it adds the
extra `NUMBER_OF_FOLDS` violations (10→19) and (because the sim renders flat `"F"`
creases faintly) makes the hull outline visually vanish, amplifying the "hanging" look.

**Why squaring *raises* the count (the boundary-edge exemption).** This is the
counter-intuitive bit and the reason we lint the hull, not the square. Flat-foldability
(Maekawa even-degree, Kawasaki angle-balance) is a *local rule that applies only to
**interior** vertices*; a vertex sitting on a free paper edge is **exempt** — the
boundary absorbs odd parity. On the raw hull, the incomplete rim vertices (odd-degree,
missing their corner-side creases) lie on the artifact's outer boundary, so they read
as the benign, accepted hull-frontier effect. `complete_square` then stitches a real
square border and flat `"F"` seams onto exactly those rim vertices: they are no longer
on a free edge, so the "on-the-edge, never mind" exemption is gone and their odd
degree now counts as a hard Maekawa violation, **plus** the new flat seams meeting the
new border create fresh awkward-degree junctions. No real fold is added and the paper
is identical — squaring simply **removes the boundary exemption**, converting exempt
edge-points into non-exempt interior junctions, so the linter starts counting
violations it previously let slide. That is the whole of the 10→19 delta, and why
feeding the square back into the validation loop would only hand the agent phantom
errors it cannot fix. (It also tells you what the real fix must do: not attach corners,
but crease them with genuine M/V folds so each former rim vertex gets an even, balanced
fan — i.e. actually solve the corner as origami, the same hard problem as A-9.)

**SPIKE RESULT (2026-06-28, `probe_spike_kawasaki.py`) — the molecule is NOT broken;
do NOT build the deep fix as a correctness effort.** Computing the Kawasaki
alternating-angle condition directly at every vertex of the raw bear base:

- **25 strictly-interior vertices: max deviation 0.0000°, zero failures** — every
  interior vertex is *exactly* flat-foldable.
- **All 20 hull-boundary vertices** are the odd-degree/deviating ones, and nothing
  else.

So the crease pattern is a **mathematically perfect, exactly-flat-foldable uniaxial
base on the leaf hull**. The lint failures are entirely the hull-vs-square artifact
(Oriedita reading the uncreased corner paper as if it must participate). **A-3's
false-negative / accept judgment is justified — Problem A is NOT a molecule defect.**

**Recommendation: ACCEPT. Do not invest in the molecule-level "A+B" fix.** It would
only make the *square itself* (corners included) flat-fold — a purely aesthetic
"the pattern looks fully creased" goal, not a correctness fix, and it would partly
contradict the (correct) A-3 decision. If ever wanted, it is engine-level (force the
full-square molecule via `CalcPolygonValidity`, or a Kawasaki/Maekawa corner-repair
pass) and should be bundled with A-9 (which adds new flaps into the same corner
regions). Probes for that day: `probe_spike_kawasaki.py` (interior must stay 0°),
`probe_dangling.py`, `probe_square_lint.py`.

Note Problem B (the squaring's flat-`"F"` corner-stitching) remains a display-only
approximation. The "creases hang" look is a *rendering* effect: the sim hides flat
(`"F"`) creases (`passiveEdgesVisible=false`), so the mountain/valley creases that
terminate on the flat hull outline appear to end mid-paper. **A quick fix was tried
and rejected (2026-06-28):** enabling `globals.passiveEdgesVisible` in the bridge does
NOT work — `updateEdgeVisibility()` does not control the rendered hinge-line object in
the embed, the hinge bucket is **77 edges** (our `"F"` creases *plus* the sim's
internal triangulation diagonals → clutter, not a clean outline), and the
non-flat-foldable squared model never lies flat so there is no clean pattern view to
show anyway. The Origami Simulator is a 3D folding sim, not a clean 2D CP renderer. A
genuine clean crease-pattern display would be a **separate 2D panel** (draw
`vertices_coords` + `edges_*` colored by M/V/F on a canvas/SVG) — its own feature, not
a sim toggle. Until then, the 3D viewport's busy/"hanging" look is cosmetic only; the
base is mathematically correct (the spike above).
