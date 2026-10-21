# Free-Paper Detection — Design

**Date:** 2026-06-13
**Status:** Approved (design); pending implementation plan
**Scope:** Add a deterministic, geometry-only MCP tool, `find_free_paper`, that
reports regions of the sheet a Metric Tree leaves uncreased (paper outside the
convex hull of the leaf nodes), plus the two entry points through which the agent
and the human use it. No change to the TreeMaker compiler or the Oriedita linter.

## Motivation

Session 5 (2026-06-13) established — with direct evidence, not inference — why the
"FAIL-LINT frontier" cases (star-5/6/8, star-6-sym, cat-spine4) fail Oriedita:

- TreeMaker builds the crease pattern on the **convex hull of the leaf nodes**
  (`tmTree.cpp:2723-2734`); `mIsPolygonValid` only certifies the *hull* is filled,
  not the paper square.
- When flap tips do not reach the paper corners (any figure whose symmetry does
  not align to a square — odd stars, some caterpillars), the hull is a polygon
  strictly inside the square, and the leftover corner/edge paper is left
  **uncreased by design**.
- The hull boundary is faintly non-convex at the hinge-boundary points (e.g.
  star-5 `v7 (0.27, 0.8236)` sits ~1.4e-3 inside the straight hull edge), so
  Oriedita classifies those points as *interior*, applies Kawasaki, sees an
  odd-degree (3) vertex, and reports a violation. Count law:
  **# Oriedita violations == # paper corners outside the hull.**

So FAIL-LINT here is **not an engine bug and not a regression** — it is the
correct, expected outcome for a tree whose leaf-node hull does not fill the paper.
(Full evidence trail: `mcp_harness/HANDOFF_molecule_topology.md`, session-5 block;
detectors `mcp_harness/probe_degree.py`, `probe_facets.py`.)

That reframes "unused paper" from a *defect* into a *design signal*. In real
origami practice (Lang et al.), corner/edge paper that the base does not consume
is the standard home for added detail — claws, ears, horns, color-change layers,
or thickening an existing flap. The mechanism to use it is identical to the
mechanism to "fill" the paper: **add a leaf node whose tip reaches into the free
region**, which grows the hull to cover it. This feature surfaces that signal and
makes the geometry of it available to the agent and the human, without letting an
LLM invent coordinates.

## Decisions (locked during brainstorming)

| Decision | Choice | Rationale |
|---|---|---|
| Trigger / availability | **Both**: proactive surfacing at the Reality Check (Step 3) **and** a standing tool callable on demand mid-session | User wants the design tradeoff visible up front *and* the ability to say "use that corner for an ear" any time |
| Tool intelligence | **Geometry-only**: returns free-paper regions (location, area, polygon, adjacent hull edge + nodes). Proposes NO anatomy and does NO packing | Preserves the project's core split — deterministic engines compute geometry, the AI handles intent. Keeps the tool trivially testable with exact numbers |
| Region computation | **Hull-complement, region-based**: free paper = paper polygon − convex hull of leaf nodes; connected components are the regions | Falls directly out of the proven root cause; naturally handles both corner triangles and edge strips; no new geometry theory |
| Feasibility ("will a flap fit here?") | **Out of scope**: not computed by this tool | That is circle-packing feasibility — its own hard problem (Section-6 "World Model"). A proposed flap goes through the normal compile→lint loop to learn if it packs |
| Anatomy decision | **AI agent + human**, never the tool | Aesthetic/anatomical calls are intent, not geometry |
| Engine / linter changes | **None** | The tool reads the tree's node geometry only; TreeMaker and Oriedita are untouched |

## Architecture

```
mcp_harness/
├── server.py                 ← EXISTING geometry MCP server (init_paper, add_node,
│                                add_edge, compile_treemaker_math, ...)
│   └── find_free_paper(...)   ← NEW tool, lives beside the tree-drafting tools
├── free_paper.py             ← NEW: pure-Python geometry (hull, complement, regions).
│                                No engine/MCP imports → unit-testable in isolation
└── tests/
    └── test_free_paper.py     ← NEW: exact-number assertions on known trees
```

`find_free_paper` is a thin MCP wrapper; all geometry lives in `free_paper.py`,
which depends only on the node coordinates already present after
`run_scale_optimization()`. It does **not** call TreeMaker's molecule builder or
Oriedita.

### Component 1 — `free_paper.py` (deterministic geometry)

Pure functions, no side effects, no MCP/engine imports.

```
free_paper_regions(node_locs, paper_w, paper_h) -> list[Region]
```

Algorithm:
1. Collect the leaf-node locations (the points TreeMaker hulls). These are read
   from the tree after scale optimization, in paper coordinates.
2. Compute the convex hull of those points (monotone-chain; small N, exact enough).
3. Compute the polygon difference `paper_rectangle − hull` (the complement). The
   result is zero or more polygons.
4. For each complement polygon, classify and describe it (below).
5. Return them sorted by descending area.

`Region` fields (geometry only):
```
region_id        : int
kind             : "corner" | "edge-strip"   # corner if it contains a paper corner
location         : [x, y]    # the paper corner it contains, or the midpoint of the
                             #   paper-edge it abuts (edge-strip)
polygon          : [[x,y], ...]              # exact free-paper outline, CCW
area             : float                     # fraction of total sheet area
adjacent_hull_edge : [[x,y],[x,y]]           # the hull segment bounding the region
adjacent_node_ids  : [int, ...]              # tree node ids at that hull edge's ends
```

An empty list means the hull already fills the paper (star-4 / hshape / quad) —
i.e. "expect a clean lint, no free paper to offer."

Edge cases handled explicitly: hull == paper (empty result); degenerate/collinear
hulls (≤2 distinct points → whole paper is "free", reported as one region);
slivers below an area epsilon are dropped (the ~1e-3 concavity must NOT be reported
as a usable region).

### Component 2 — `find_free_paper(tree_json)` MCP tool

In `server.py`, beside the existing drafting tools. Builds/uses the current tree's
optimized node locations, calls `free_paper.free_paper_regions`, returns the region
list as JSON. Geometry-only contract: it never proposes a node, a length, or an
anatomy label.

### Component 3 — Proactive surfacing (Reality Check, Step 3)

After the agent drafts the Metric Tree and before/alongside compiling, it calls
`find_free_paper`. The Tier-1 UI renders any returned regions as shaded overlays on
the stick-figure viewport, next to the concept art: *"these areas of paper are
unused."* The human sees the tradeoff before committing to a compile. (This spec
defines the tool + its output contract; the React overlay rendering is a Tier-1
task that consumes this contract and is tracked separately.)

### Component 4 — On-demand use (mid-session)

The same tool is callable any time. Flow when the user asks to use free paper:

```
find_free_paper(tree)        → REGIONS                     (deterministic)
        │
        ▼
AI agent + concept art       → picks a region, decides the detail + size  (intent)
        │
        ▼
add_node / add_edge          → drafts a leaf reaching into the region      (intent)
        │
        ▼
compile_treemaker_math       → did the new flap pack?                      (deterministic)
validate_flat_foldability    → does it fold flat?                          (deterministic)
        │
        ▼
human approves
```

Every aesthetic call stays with the AI; every geometry/feasibility call stays with
the existing deterministic engines.

## What this is NOT (YAGNI)

- **Not** a packing/feasibility predictor — it never estimates whether a flap fits.
- **Not** an anatomy suggester — no "corner near head → horn".
- **Not** an auto-filler — it never mutates the tree; it only measures.
- **Not** an engine or linter change — TreeMaker and Oriedita are untouched.
- **Not** the Tier-1 overlay implementation — that consumes this tool's output.

## Testing

`tests/test_free_paper.py`, pure unit tests on `free_paper.py` (no engine, no JVM).
Because `free_paper_regions` takes node locations as a plain argument, tests feed
the **captured scale-optimized leaf-node coordinates** for each case as fixtures
(deterministic, already measured — e.g. star-5 tips at `(0,0.647),(0.647,0),
(0.542,1),(0,0),(1,0.542)`). The engine is therefore not needed to test the
geometry; a single separate integration check exercises the `find_free_paper` MCP
wrapper end-to-end against the live engine.

- **star-4** (hull == square): returns `[]`.
- **hshape, quad** (PASS cases): returns `[]`.
- **star-5**: returns exactly 3 corner regions at `(0,1),(1,1),(1,0)`; assert each
  region's `location`, `kind == "corner"`, and that total free area ≈ (1 − hull
  area) within epsilon; assert `adjacent_node_ids` are the expected hull-edge nodes.
- **star-6**: returns exactly 2 corner regions (matches the 2 missing corners).
- **Degenerate**: a 2-leaf tree → one region covering ~the whole sheet.
- **Determinism**: same tree → byte-identical region list across runs.

The region count must equal the corner-deficit the session-5 detectors already
measured (`probe_degree.py`), tying this tool to the proven root cause.

## Relationship to the regression baseline

`find_free_paper` is also the principled answer to the FAIL-LINT baseline question.
A non-empty result certifies "this tree intentionally leaves paper bare → FAIL-LINT
is the *expected* verdict, not a regression." Follow-up (out of scope here, noted
for the plan): the regression suite may annotate hull<paper cases as
expected-FAIL-by-design using this signal, so the baseline documents *why* rather
than just pinning a string.

## Open questions deferred to the plan

- Exact polygon-difference implementation (hand-rolled rectangle−convex-hull clip
  vs. a small dependency). Rectangle minus a convex polygon is simple enough to
  hand-roll and keep the harness dependency-free; the plan will confirm.
- Whether leaf-node locations are read via an existing wrapper accessor or a new
  small one on `HeadlessTreemaker`.
