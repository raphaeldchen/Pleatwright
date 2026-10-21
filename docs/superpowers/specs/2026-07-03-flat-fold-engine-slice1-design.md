# Flat-fold engine (folded-state-first, slice 1) — design

**Date:** 2026-07-03. First of the four folded-state-first slices agreed in
the decomposition brainstorm (flat-fold engine → layer ordering → at-depth
op → squash/sink), per the handoff `docs/superpowers/2026-07-03-handoff-pillar-b-next.md`
§2 Step 2. Design decisions are grounded in the slice-0 probe:
`docs/superpowers/2026-07-03-probe-folded-state-findings.md`
(probe script `mcp_harness/probe_folded_state.py`).

## Decisions (from brainstorming)

| Decision | Choice |
|---|---|
| Decomposition | Keep the handoff's 4 slices; a slice-0 probe ran first and validated the algorithms on real bases. |
| Slice-1 contract | **Library + closure report** (pure Python, `mcp_harness/flat_fold.py`), over library+Playwright-harness (harness maintenance now, no consumer yet) and library+MCP-tool (no agent use-case until slice 3). |
| Acceptance oracle | Two-tier, per probe finding #3: analytic-vs-sim agreement pinned OFFLINE against a checked-in 100% capture for a clean base; closure-error REPORT pinned for hull-frontier bases (sim never converges there at 100%). |
| Domain | RAW hull folds are the honest domain (probe finding #2: squaring breaks flat-foldability of the frame). Squared and hull-frontier folds are still VALID inputs — they return large closure errors instead of raising. |

## 1. Purpose

Compute the analytic flat-folded 2D state of a compiled base: where every
face lands at 100% fold (Lang's reflection-composition construction), with
self-consistency (cycle closure) reported rather than assumed. This is the
foundation for layer ordering (slice 2), at-depth ops (slice 3), and the
fast headless pose evaluator B5 needs (browser capture is 30–90 s per
candidate and visible-tab-bound; this is milliseconds).

## 2. API

One entry point, pure function, numpy only (already a project dependency):

```python
from flat_fold import flat_fold, FlatFoldResult, ClosureReport

result = flat_fold(fold)   # fold: FOLD dict (vertices_coords,
                           # edges_vertices, edges_assignment)
result.faces            # list[list[int]] — interior faces, CCW winding
result.transforms       # list[np.ndarray] — per-face 3x3 homogeneous 2D
                        # reflection compositions (flat -> folded)
result.folded_vertices  # list[np.ndarray] — per-face folded 2D coords,
                        # folded_vertices[i][j] is the image of
                        # faces[i][j]; a CP vertex has one image PER FACE
result.closure          # ClosureReport
```

`ClosureReport`:

```python
closure.edge_errors     # list[(error: float, edge: (v_lo, v_hi), assignment: str)]
                        # one entry per non-spanning-tree shared edge
closure.max_error       # float; 0.0 when the adjacency graph is a tree
closure.bad_edges       # entries with error > 1e-6 (the CLOSURE_EPS constant)
```

Semantics and conventions:

- **Faces** are extracted from the bare crease pattern (TreeMaker FOLDs
  carry no `faces_vertices`): angle-sorted rotations + half-edge walk —
  the same construction the vendored bridge gets from the FOLD JS library.
  The outer face is identified by signed area and dropped.
- **Transforms** compose reflections along a BFS spanning tree of the
  face-adjacency graph (faces sharing an edge). M/V edges reflect across
  the shared edge's flat line; F edges are identity (faces fold
  together); B edges are boundary (never shared). Root face = the
  interior face with the largest |area| (deterministic; ties broken by
  lowest face index).
- **Closure error** for a non-tree shared edge = max over the edge's two
  endpoints of the distance between the two paths' images of that
  endpoint (paper units). Kawasaki-violating vertices and squared frames
  make this large — that is a REPORTED property of the input, not an
  error condition.
- **Errors**: `ValueError` only for structurally unusable input — missing
  or empty `vertices_coords`/`edges_vertices`/`edges_assignment`,
  mismatched lengths, a face walk that fails to terminate, or a
  face-adjacency graph whose faces are not all reachable from the root
  (disconnected sheet). No other exceptions escape.

## 3. What this slice does NOT touch

- No layer ordering (slice 2), no ops (slice 3), no MCP tool, no UI, no
  display-path change. `web/*` and `agent_loop.py` are untouched.
- Provenance contract unchanged: the engine READS FOLD dicts; it never
  writes one, and nothing here edits coordinates.
- The probe script stays as-is (throwaway reference); `flat_fold.py` is a
  clean reimplementation with tests, not a rename of the probe.

## 4. Testing (the two-tier oracle)

All in `mcp_harness/tests/test_flat_fold.py`, offline, fast:

1. **Clean tier** — star-4, hshape, quad, dog (raw goldens; dog checked in
   as a golden fixture from `docs/dog.fold`):
   `closure.max_error < 1e-6`; folded bbox ⊆ flat bbox (+ small epsilon);
   per-face isometry (each face's folded edge lengths equal flat edge
   lengths, by construction but pinned); deterministic output across two
   calls.
2. **Sim-agreement tier** — the probe's star-4 100% browser capture is
   checked in as `tests/goldens/star4-sim-100.json` (converged: maxMove
   3e-5, planar to 3rd-singular-value 0.000). The test recovers the
   sim-node → CP-vertex correspondence from the capture's `flat_coords`
   (similarity fit: sim recenters and scales by ~1.414, then nearest
   neighbor; asserts bijective), embeds the analytic folded state in the
   capture's plane, Kabsch-aligns (reflection allowed — a flat fold has
   mirror ambiguity), and pins residual **max < 1e-3 paper units**.
3. **Hull-frontier tier** — bear-base fixture: closure report pinned as a
   drift tripwire with tolerance (bad_edges count == 15, max_error within
   [1.0, 1.4]); engine returns normally (no raise).
4. **Squared-fold behavior** — dog + `square_complete.complete_square`:
   raw closes clean, squared reports bad_edges (count > 0) — pins the
   "honest domain" finding so nobody later assumes squared folds compose.
5. **Error paths** — empty/mismatched arrays raise `ValueError`.

## 5. Risks / notes for later slices

- Overlap census (probe #4): 282–544 overlapping face pairs on real bases
  — slice 2 should plan Tachi-style pairwise constraints via a small
  CSP/SAT and accept partial orders.
- The Playwright capture path (probe #3) is proven and repeatable; if the
  pinned-capture fixture ever needs refreshing, the probe's method is the
  recipe. A reusable harness is deliberately deferred until something
  needs recurring captures.
- One non-convex face exists on bear (12-gon frame region): slice-2
  overlap logic must triangulate or special-case it.
