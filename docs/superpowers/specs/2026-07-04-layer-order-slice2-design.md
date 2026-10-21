# Layer ordering (folded-state-first, slice 2) — design

**Date:** 2026-07-04. Second of the four folded-state-first slices
(flat-fold engine → **layer ordering** → at-depth op → squash/sink).
Builds directly on slice 1's `flat_fold()`
(`docs/superpowers/specs/2026-07-03-flat-fold-engine-slice1-design.md`,
merged as PR #26). Overlap census grounding the approach:
`docs/superpowers/2026-07-03-probe-folded-state-findings.md` §4
(282–544 overlapping face pairs on real bases).

## Decisions (from brainstorming)

| Decision | Choice |
|---|---|
| Deliverable | **Point-query stack over a partial order** — `above(a,b)` and `stack_at(p)`, forced relations only — over full global `faces_layer` (research swamp, no consumer needs it) and probe-first-then-decide. Slice 3's at-depth ops ask exactly the point question. |
| Oracle | **Hand-derived + self-consistency**: exact stacks asserted for hand-derivable fixtures (2-crease strip, star-4 center); an INDEPENDENT checker validates every forced relation against the raw constraints on real bases; drift-tripwire pinned stacks at fixed probe points. The simulator CANNOT be the oracle here — its mass-spring solver models no layer contact or self-intersection. |
| Closure-inconsistent input | **Refuse the whole fold**: `layer_order()` raises `ValueError` when `closure.bad_edges` is non-empty (message includes the count). Layers are only meaningful where the folded state exists. Bear-posing keeps using tip-local ops, which need no layers. |
| Internals | **Approach A — constraint propagation to fixpoint** (honest `None` = genuinely free), over one-satisfying-total-order CSP (reports arbitrary tie-breaks as facts) and lazy per-point solving (locally consistent answers that no global order realizes). No backtracking search in this slice (YAGNI until the fixtures prove under-determination at points we care about). |

## 1. Purpose

Given a consistent flat-folded state, determine which face lies above
which — wherever Justin/Tachi's non-crossing conditions force it — and
answer point queries: the top-to-bottom stack of faces covering a point.
This is what slice 3 needs to fold THROUGH layers at a non-tip point,
and what keeps the project's honesty contract: forced relations are
facts, free relations are reported as free, never invented.

"Above" is with respect to the +z side of the folded plane; the root
face of slice 1's BFS (largest face, identity transform) keeps its
flat orientation, and orientation of every face is the parity of its
reflection composition (det of the transform's linear part: +1 face-up,
−1 face-down).

## 2. API

New module `mcp_harness/layer_order.py`, numpy only:

```python
from layer_order import layer_order, LayerOrder, AmbiguousStack

layers = layer_order(result)   # result: FlatFoldResult from flat_fold()
```

- `layer_order(result) -> LayerOrder` — raises `ValueError` if
  `result.closure.bad_edges` is non-empty (count in message), or if a
  face is non-convex (see §3 stage 1), or if constraint propagation
  derives a contradiction (message carries the constraint provenance —
  on flat-foldable input this indicates a bug and must not silently
  produce an order).
- `layers.above(a, b) -> bool | None` — `True` iff face `a` is forced
  strictly above face `b`; `False` iff forced below; `None` when the
  pair is unconstrained OR does not overlap. Antisymmetric by
  construction: when forced, `above(a,b) is (not above(b,a))`; when
  free, both directions return `None`.
- `layers.stack_at(p) -> list[int]` — face indices covering point `p`
  (folded coordinates), top to bottom. Raises `AmbiguousStack`
  (subclass of `ValueError`) when the covering set is not totally
  ordered by forced relations; the exception carries the list of free
  pairs (`.free_pairs`). Points covering no face return `[]`; points on
  a cell boundary (within 1e-9 of an arrangement edge) are
  implementation-defined — tests query interior points only.
- `layers.cells` — the overlap decomposition, exposed for tests and
  debugging: a list of `(interior_point: np.ndarray, faces: frozenset[int])`.

## 3. Internals — three stages, each independently testable

### Stage 1: cell decomposition

Overlay the folded faces (from `result.folded_vertices`) into an
arrangement of cells — maximal regions with a constant covering set.
Built from the pairwise convex-polygon clip (Sutherland–Hodgman, the
slice-0 probe's machinery cleaned up) refined across all overlapping
pairs; each cell is represented by an interior point and its covering
set (containment test of that point against every folded face).

All faces are asserted convex up front; a non-convex face raises
`ValueError`. (The only known non-convex face in the fixture corpus is
bear's 12-gon frame, and bear is refused earlier by the closure gate;
squared folds likewise. Triangulation support is deliberately out of
scope until an in-domain fixture needs it.)

### Stage 2: constraint generation

For the folded state, generate the standard non-crossing constraints,
each recorded with provenance (which crease/cell produced it):

- **Taco-tortilla:** for each crease (M/V shared edge), its two incident
  faces fold onto the same half-plane boundary line. Any face whose
  folded polygon properly crosses the folded crease segment within the
  overlap region must lie strictly above BOTH or strictly below BOTH
  connected faces. Encoded as the implication pair
  `(above(x,f1) == above(x,f2))` for the crossing face `x`.
- **Taco-taco:** two creases whose folded segments overlap along a
  common stretch: their two flap-pairs must nest or be disjoint —
  encoded as the standard exclusion over the 4 involved faces (the two
  interleavings are forbidden).
- **Tortilla-tortilla:** two faces adjacent across a cell boundary that
  is NOT a fold between them keep the same relative order on both sides
  — encoded as an equality between the pair's relation in adjacent
  cells (relations live per overlap component, so this collapses to
  "one relation variable per unordered face pair per component").

### Stage 3: propagation to fixpoint

Relation variables (`a` above `b`: true/false/unknown) per overlapping
pair, grouped by overlap component (faces connected through shared
cells). Propagate until no change:

1. transitivity within a cell's covering set (`a>b`, `b>c` ⇒ `a>c`
   whenever all three share a cell),
2. taco-tortilla implications (equality constraints between pair
   variables),
3. taco-taco case elimination: each such constraint has a finite set of
   admissible orderings of its 4 faces; when current forced relations
   exclude all but one admissible case, force that case's remaining
   relations.

Fixpoint is reached in finitely many rounds (each round either forces
at least one unknown or terminates). A derived contradiction raises
`ValueError` with the provenance chain. **No search**: whatever remains
unknown at fixpoint IS the answer (`None` / `AmbiguousStack`).

## 4. What this slice does NOT do

- No backtracking search / "a consistent completion" API — deferred
  until the fixtures prove under-determination at points slice 3 needs.
- No `faces_layer` export, no MCP tool, no UI, no display/agent change.
- No non-convex face handling (refused with `ValueError`).
- Provenance contract unchanged: reads `FlatFoldResult`, writes nothing.

## 5. Testing

`mcp_harness/tests/test_layer_order.py`, offline, fast. **Plan must
include a probe-first task**: run the generator + propagator on star-4
and dog and PRINT forced-pair counts and candidate stacks before any
expectation is pinned (slice 1's measure-then-pin lesson — the
constraint machinery, not the spec, decides the numbers).

1. **Hand-derived tier:**
   - a synthetic 2-crease paper strip (1×3 strip, two parallel V
     creases → 3 faces folded into a Z/S; the full stack is forced and
     derivable on paper in a minute): assert the exact `stack_at`
     result at the triple-overlap point, and `above()` for all 3 pairs;
   - star-4 center: the 8 triangles fan alternately around the center;
     assert the hand-derived relative order of the pairs the
     constraints force (exact expected values fixed during the plan's
     probe step, from hand analysis — not copied from the solver).
2. **Self-consistency tier (dog, quad, hshape):** an independent
   `check_order(cells, constraints, above)` function — implemented
   against the constraint DEFINITIONS (§3 stage 2), reading the
   propagator's output but sharing none of its code — asserts every
   forced relation satisfies every constraint; plus pinned
   drift-tripwire stacks at 2–3 fixed interior probe points per fixture
   (values measured in the plan's probe step).
3. **Contract tier:** bear → `ValueError` (closure count in message);
   squared dog → `ValueError`; `above()` antisymmetry when forced and
   double-`None` when free; non-overlapping pair → `None`;
   `AmbiguousStack.free_pairs` populated; `stack_at` on an uncovered
   point → `[]`; determinism across two calls.

## 6. Risks / notes for slice 3

- If the probe step reveals real bases are heavily under-determined at
  flap midpoints (the points slice 3 cares about), the follow-up is the
  deferred search/"consistent completion" — a new decision, not scope
  creep here.
- Taco-taco is the fiddliest predicate (segment-overlap detection on
  folded creases + 4-face case tables); the plan should isolate it in
  its own task with synthetic minimal fixtures.
- Cell decomposition cost is O(F²) clips with F ≤ 45 — trivial at our
  scale; no spatial indexing.
