# Design: Hull-frontier robustness (A-1) + agent teaching (A-2)

**Date:** 2026-06-27
**Branch:** `feat/hull-frontier-agent-fixes`
**Status:** Approved design, pre-implementation
**Roadmap item:** Follow-up **2 / A-1 + A-2** in `docs/followups-web-ui-and-foldability.md`.

## 1. Purpose

The `"bear"` run exposed two defects in how the tooling handles the documented
**hull-vs-square frontier** (TreeMaker creases only the convex hull of the leaf
nodes; paper outside the hull is uncreased, and Oriedita reads the hull boundary
as Kawasaki-failing interior vertices — `0 M/V-fixable, all geometry`):

- **A-1:** `free_paper_regions` (`mcp_harness/free_paper.py:141-145`) raises
  `ValueError` the moment any hull vertex is interior to the sheet. The bear
  packed with the **entire** leaf hull interior (no tip on any edge), so the
  perimeter-walk had no anchor and crashed instead of reporting the free paper.
- **A-2:** the system prompt (`mcp_harness/agent_loop.py:230-252`) tells the agent
  to call `find_free_paper` unconditionally (triggering A-1) and predates the
  A-3=ACCEPT decision, so it frames fill/accept as a coin-flip "design choice"
  and contradicts itself ("usable as-is" *and* "FAILED… add flaps or accept").

**Reframe from A-3=ACCEPT:** the hull-frontier base folds cleanly as-is (proven
in the embedded WebGL viewport, PR #15). So `find_free_paper` is now a
**signal-only / optional-polish** tool, not a correctness gate. A-1 therefore
needs a robust, honest report — not high-fidelity decomposition.

Scope is **A-1 + A-2 only**. C-8/B-7 (item 4) and A-9 generative fill (item 5)
are separate efforts.

## 2. Background (verified facts)

- `free_paper_regions(nodes, paper_w, paper_h)` returns a list of `Region` dicts,
  sorted by descending area, `[]` when the hull fills the sheet.
- The existing algorithm walks the rectangle perimeter between hull **chords**,
  which structurally assumes every hull vertex lies **on** the sheet boundary
  (tips-on-edge). It produces `kind ∈ {"corner", "edge-strip"}` regions.
- **No test currently pins the interior-hull `ValueError`** — the pinned tests are
  the scale-optimized cases (`test_star5_*`, area accounting, determinism) and the
  degenerate `<3`-point case. We are free to replace the raise with a frame report.
- The MCP entry point `_worker_free_paper` (`server.py:144-158`) runs
  `run_scale_optimization()` then calls `free_paper_regions`, returning JSON. It
  already catches `BaseException`, so today the crash surfaces as an error string;
  after A-1 it returns a valid frame region.

## 3. Architecture & components

Two independent units, no new files:

```
mcp_harness/
  free_paper.py        ← A-1: add interior-hull branch + `hole` field to Region
  agent_loop.py        ← A-2: rewrite the "FREE-PAPER FRONTIER" prompt block
  tests/test_free_paper.py   ← A-1 tests (new cases; existing stay green)
```

### Component 1 — `free_paper.py` (A-1)

Add one branch in `free_paper_regions`, after `hull = convex_hull(pts)` and the
existing degenerate `len(hull) < 3` branch. When `len(hull) >= 3` **and any** hull
vertex satisfies `not _on_boundary(v, w, h)`, return a **single frame region**
instead of raising:

| Field | Value |
|-------|-------|
| `region_id` | `0` |
| `kind` | `"frame"` |
| `location` | area-weighted frame centroid: `(A_rect·C_rect − A_hull·C_hull) / (A_rect − A_hull)` |
| `polygon` | rectangle outline CCW: `[[0,0],[w,0],[w,h],[0,h]]` (outer boundary) |
| `hole` | the hull polygon `[[x,y],…]` (inner boundary) — **NEW field** |
| `area` | `(sheet − hull_area) / sheet` |
| `adjacent_hull_edge` | `[]` (a ring has no single bounding chord) |
| `adjacent_node_ids` | every leaf id on the hull (whole hull borders the frame), `None`s dropped |
| `corners_contained` | rectangle corners **outside** the hull (all 4 when fully interior) |

`Region` gains a `hole: list` field defaulting to `[]`; the existing
corner/edge-strip and degenerate regions therefore emit `hole: []`. This is an
additive schema change — `asdict` includes the new key for every region.

The all-on-boundary path (the `for i in range(n)` perimeter walk) is **untouched**.
The branch ordering is: degenerate (`<3`) → interior-vertex frame → all-on-boundary
perimeter walk. The mixed case (some tips on an edge, some interior) is subsumed by
the interior-vertex branch: any interior vertex ⇒ one honest "sheet minus hull"
frame. `hull_area` reuses `_polygon_area(hull)`.

### Component 2 — `agent_loop.py` system prompt (A-2)

Rewrite the "THE FREE-PAPER FRONTIER -- DO NOT MISDIAGNOSE IT" block (lines
230-252). New content must:

1. **Lead with A-3=ACCEPT:** a base that compiled cleanly but lints as all
   geometry/Kawasaki with zero M/V-fixable is the expected free-paper frontier
   *and folds cleanly as-is* (verified physically in the WebGL viewport).
   **Accept is the default correct outcome — not a failure, not a retry target.**
2. Keep the existing "do NOT invent causes / do NOT propose remedies that cannot
   help / do NOT spend compile retries" guidance — that was correct.
3. Keep step 1 (call `find_free_paper` with the same nodes/pairs — now crash-proof),
   but frame its returned regions as **optional detail-flap locations**, not a defect.
4. Remove the self-contradiction: the base is **valid and foldable**; adding flaps
   to fill the free paper is **optional aesthetic polish**, not a math fix. Drop the
   "or accepting the uncreased corners is a DESIGN choice" framing that put
   fill/accept on equal footing.

## 4. Data flow (unchanged shape)

```
agent compiles base → lints → 0 M/V-fixable + all geometry  (frontier signature)
   │
   ▼  prompt: recognize frontier → ACCEPT (folds as-is); optionally:
find_free_paper(nodes, pairs) → _worker_free_paper
   │  run_scale_optimization → leaf_node_locations → free_paper_regions
   ▼
hull fully/partly interior → ONE {kind:"frame", area, hole, adjacent_node_ids,…}
   │  (previously: ValueError → error string)
   ▼  agent presents free regions as optional detail-flap locations
```

## 5. Error handling

- `free_paper_regions` no longer raises for interior hulls; it always returns a
  region list (`[]` only when the hull genuinely fills the sheet).
- `_worker_free_paper` keeps its `BaseException` guard for genuine engine faults.
- Degenerate (`<3` unique/collinear) hull still returns the whole-sheet region.

## 6. Testing strategy

**A-1 — `tests/test_free_paper.py` (TDD, new cases):**
- `test_interior_hull_returns_single_frame_region`: the bear-like repro
  `[(0,0.3,0.3),(1,0.7,0.3),(2,0.5,0.7),(3,0.45,0.5)]` → exactly one region,
  `kind == "frame"`, `hole` == the hull, `adjacent_node_ids` ⊆ leaf ids.
- `test_frame_area_plus_hull_equals_sheet`: `region["area"] + hull_area/sheet == 1`
  within tolerance.
- `test_mixed_hull_one_tip_on_edge_returns_frame`: one vertex on an edge, rest
  interior → still one `"frame"` region (covers the mixed branch).
- `test_frame_corners_contained`: fully-interior hull → all 4 rectangle corners
  reported in `corners_contained`.
- Existing tests (`test_star5_*`, area accounting, determinism, degenerate
  two-leaf) must stay green — the boundary path is unchanged; confirm the added
  `hole: []` key does not break `test_find_free_paper.py` (no exact dict-key
  assertions).

**A-2 — prompt:** the prompt is a constant string; verified by reading and by the
existing agent tests staying green. Add one light assertion (e.g., in an existing
agent-prompt test or a new small one) that `SYSTEM_PROMPT` contains the accept
framing (e.g., "folds cleanly as-is" / "accept") and no longer contains the
contradictory "FAILED" wording for this case.

## 7. Out of scope (YAGNI)

- Per-hull-edge / medial decomposition of the frame (rejected in favor of a single
  frame region; revisit only if A-9 generative fill needs per-edge anchors).
- Making `find_free_paper` generative (A-9 / item 5).
- C-8 (`MESH_PROVIDER` default unification) and B-7 (python-dotenv manifest) — item 4.
- Changing the boundary-anchored corner/edge-strip output for scale-optimized bases.

## 8. Open questions / risks

- **`hole` field consumers:** the UI / agent currently read `polygon`/`area`; the
  additive `hole` key is ignored by existing consumers. Confirm no JSON-schema
  validation rejects extra keys (none known).
- **`adjacent_node_ids` for a frame** is the full leaf set; downstream "two nodes
  per chord" assumptions don't apply to `kind == "frame"`. The prompt change makes
  the agent present these as a region list, not per-chord pairs, so this is safe.
