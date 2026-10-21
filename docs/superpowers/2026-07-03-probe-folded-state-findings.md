# Slice-0 probe findings: folded-state-first (flat-fold engine)

**Date:** 2026-07-03. Throwaway probe agreed in the folded-state-first
decomposition brainstorm (handoff §2 Step 2, "Add a slice 0 probe").
Script: `mcp_harness/probe_folded_state.py` (face extraction + reflection
composition + overlap census). Sim comparison driven via Playwright against
the vendored simulator (`ide-bridge.js` postMessage protocol), analysis in
scratchpad (`compare_capture.py`, not kept).

Fixtures: goldens `star-4`/`hshape`/`quad` (raw + squared), `bear-base`
(the hull-frontier display asset — already squared), `docs/dog.fold`
(raw + squared).

## 1. Face extraction from bare crease patterns: WORKS, pure Python

TreeMaker FOLDs carry no `faces_vertices`; the probe reimplements the FOLD
library's construction (angle-sorted rotations + half-edge walk) in ~40
lines of numpy-free Python. On all 5 fixtures, raw and squared:

- exactly one outer face detected (signed area), every interior face
  reached by the adjacency BFS — no disconnected pieces, no walk failures;
- real-base messiness is bounded: bear has sliver faces down to
  4.7e-4 area (not degenerate — no zero-area faces anywhere) and exactly
  ONE non-convex face (a 12-gon; the hull-frontier frame region). Face
  counts: 8 (star) → 45 (bear); sizes 3–12 vertices.

**Consequence for slice 1:** face extraction is not a risk item. Non-convex
frame faces exist, so anything assuming convex faces (e.g. overlap tests)
must triangulate or special-case the frame.

## 2. Reflection composition: sound exactly where theory says

Per-face transforms by composing reflections along a BFS spanning tree of
the face-adjacency graph; consistency measured as **cycle-closure error**
on non-tree shared edges (how far the two paths' transforms disagree,
max over the shared edge's endpoints, paper units).

| fixture | closure max | bad edges (>1e-6) |
|---|---|---|
| star-4 / hshape / quad / dog — **raw** | 3e-16 … 9e-10 | 0 |
| hshape / quad / dog — **squared** | 0.59 / 0.72 / 0.83 | 2 / 1 / 12 |
| bear-base (hull-frontier, raw=squared) | **1.20** | **15 / 42** |

Two distinct causes, both expected:

- **Hull-frontier bases** (bear): the accepted Kawasaki violations make a
  consistent flat-folded state mathematically nonexistent — reflection
  composition cannot close around those vertices. Not a bug; a property.
- **Squaring** breaks closure on otherwise-clean bases: the added corner
  faces/border are not flat-foldable (the long-known deferred item from
  the complete-square design). Closure errors appear on cycles that pass
  through the frame; which edge "carries" the error is spanning-tree
  dependent, so interior-rooted composition that excludes frame faces
  stays clean.

**Consequence for slice 1:** the engine's honest domain is the RAW hull
fold of a lint-clean base. Closure error must be a first-class OUTPUT of
the engine (per-edge report + max), not an assertion — hull-frontier
bases are a supported input that legitimately reports inconsistency.
At-depth ops (slice 3) should compute on the raw fold and transport to
display exactly the way shaping ops do today, NOT compute on the squared
copy.

## 3. Oracle for slice 1: sim agreement IS achievable — on clean bases

Big operational finding first: **the vendored sim's GPU solver runs fine
under Playwright** (the visible-tab constraint is about offscreen iframes,
not automation) — loadFold / setFold(100) / getFoldedGeometry over
postMessage against `simulator/index.html?embed=1` works scripted,
end-to-end. A future headless-ish capture harness is feasible.

At `setFold(100)`:

- **star-4 (clean):** converges hard (maxMove 3e-5 per 15s window),
  perfectly planar (3rd singular value 0.000), and after rigid alignment
  the analytic flat-fold positions match the sim capture to
  **≤1e-4 paper units** (residual max printed 0.0000). The sim-node ↔
  CP-vertex correspondence is recoverable bijectively from the capture's
  `flat_coords` with a simple similarity fit (sim normalizes by ~1.414).
- **bear-base (hull-frontier):** does NOT converge at 100% (still moving
  0.24/40s after 60s), NOT planar (singular values 2.19/1.16/0.78), and
  the analytic state is itself inconsistent there (a vertex's per-face
  images spread up to 1.28 paper units). Residual vs analytic: 0.61 —
  meaningless given both sides are degenerate.

**Consequence for slice 1's acceptance:** two-tier oracle.
(a) Clean golden fixtures: analytic vs sim-capture agreement at 100%,
tolerance ~1e-3 paper units — strong, automatable, now proven feasible.
(b) Hull-frontier fixtures: pin the closure-error REPORT (count + max
localized to the known Kawasaki-violating region) + internal invariants
(per-face isometry, folded bbox ⊆ flat bbox on the closed subgraph);
do NOT promise sim agreement at 100%.

## 4. Layer-ordering difficulty (slice 2 preview, byproduct)

Overlapping folded face pairs (area > 1e-6): star-4 28/28 possible,
dog raw 282 (28 faces), bear 544 (45 faces, ~55% of all pairs). Every face
overlaps many others — a total order is meaningful, but constraints are
dense: expect Tachi-style pairwise constraints over hundreds of pairs
(tractable for a small CSP/SAT, not for naive enumeration), and plan for
partial orders where the closure-error region makes "the" folded state
ill-defined.

## Probe verdict on the 4-slice decomposition

Slicing stands (flat-fold engine → layer ordering → at-depth op →
squash/sink), with two spec-shaping adjustments for slice 1:

1. Engine operates on RAW folds; closure report is a public output.
2. Acceptance = sim-agreement on clean goldens + pinned closure/invariant
   behavior on bear; the Playwright capture path makes (a) automatable.
