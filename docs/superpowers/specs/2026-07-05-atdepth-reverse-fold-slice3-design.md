# At-depth reverse fold (folded-state-first, slice 3) — design

**Date:** 2026-07-05. Third of the four folded-state-first slices
(flat-fold engine → layer ordering → **at-depth op** → squash/sink).
Builds on slice 1's `flat_fold()` (PR #26) and slice 2's `layer_order()`
(PR #27, merged at main `e4596c8`). Probe evidence for the crux decision:
`mcp_harness/probe_atdepth_stack.py` (committed alongside this spec).

## Decisions (from brainstorming)

| Decision | Choice |
|---|---|
| Crux: relation to layer order | **Geometric definition + forced-only lint, no search.** The op's through-set and per-layer assignments are determined by geometry and orientation parity alone; `layer_order`'s forced relations serve only as a static lint (refuse provable traps). Free pairs never block or decide anything — the sim/strain oracle stays the runtime judge (the B4 pattern). Rejected: consistent-completion total order (makes arbitrary tie-breaks load-bearing, the honesty violation slice 2 refused) and targeted existential search (sound but a real search component; deferred until the strain oracle proves insufficient). |
| Op surface | **New op kind `reverse_deep:X,Y:D:THETA`, tip-local ops untouched.** New numpy module (`shaping_deep.py`); `shaping.py` stays stdlib-only. No behavior change to the shipped B1–B4 loop. |
| Slice scope | **Engine + display dispatch, no agent wiring.** SYSTEM_PROMPT / strain-oracle-loop vocabulary deferred to its own mini-PR after slice 4, when the full at-depth vocabulary exists. |
| Raw vs squared | **Analyze raw, apply to squared.** `flat_fold`/`layer_order` run on the RAW hull fold (they refuse squared folds — non-convex corner faces); creases are computed in the shared CP coordinates and written into the squared display fold, extended through corner paper where they terminate on former-B hull edges. `apply_display_ops` grows `raw=`; one deep op per fold, deep before tip-local. |

### Probe evidence (why forced-only, measured 2026-07-05)

At realistic mid-flap points (30/50/70% along each tip's axial crease):

- **dog** (28 faces, 16 tips): `stack_at` is AMBIGUOUS at almost every
  point — 4 to 96 free pairs; only two shallow tips and one 4-face flap
  group are fully forced. A total-stack-based op would refuse nearly
  every realistic op on dog or invent facts.
- **quad, star-4**: fully forced total stacks at every probed point —
  the forced-only lint has teeth where order IS determined.
- A naive geometric "grabbed set" (any covering face extending beyond an
  infinite fold line) grabs the ENTIRE covering set everywhere — the
  through-set must be flap membership (connectivity), not a half-plane
  test.

## 1. Purpose & op semantics

`reverse_deep:X,Y:D:THETA` — an **inside** reverse fold of the flap
whose tip is nearest CP point (X,Y), at depth `d` along its axial
crease, folding **through all layers of that flap** at that depth.
Parameter shape and angle model match the tip-local op: `theta ∈ (0,
180]`, `theta=180` = classic flat reverse fold; the base sign `s` comes
from the flap's axial crease assignment (V → +1, M → −1). Outside-at-
depth (`sense=-1`) is out of scope (YAGNI until a need appears).

The op is **defined geometrically** — layer order never determines what
folds:

- **Wedge.** As in the tip-local op: apex `F` on the axial crease at
  depth `d` from the tip, arms at ±γ (default 45°) tipward. The tip
  layer's CP wedge is mapped through its face transforms into **folded
  space**; that folded wedge is the fold's shape for every layer.
- **Through-set** (which faces get creased): BFS from the tip-layer
  faces (the raw-CP faces containing the wedge apex `F`, one on each
  side of the axial crease) across CP crease edges **whose folded segment intersects the folded wedge
  interior**. This grabs exactly the layers physically connected through
  the fold region and excludes foreign paper that merely overlaps in
  folded space. Purely combinatorial + geometric. If the flap root is
  close enough that a body crease folds into the wedge, the body
  legitimately gets grabbed — that is physically what a too-deep reverse
  fold does.
- **Per-layer creases.** The folded wedge pulled back through each
  through-face's inverse transform lands as real crease segments in that
  face's CP region. M/V assignment and fold angle per pulled-back crease
  come from the layer's orientation parity (`det` of the transform's
  linear part — slice 2's pinned sign convention: +1 face-up, −1
  face-down). **The exact per-layer assignment table is
  measured-then-pinned** against the hand-derivable 2-layer fixture
  during the plan's probe step — the spec states the principle, the
  probe fixes the numbers.

## 2. Validity — forced-only lint, honest refusals

`ShapingError` (op skipped, one stderr line, fold stream never breaks —
the existing `apply_display_op` contract) when:

- the raw fold is refused by `flat_fold`/`layer_order`
  (closure-inconsistent — e.g. bear — or non-convex faces);
- no tip signature (B + exactly one M/V) near (X,Y); `d` reaches past
  the axial crease; a pullback crease grazes an existing vertex within
  `SNAP` (as today); a pullback wedge is degenerate;
- **forced-trap lint**: some foreign face `x` (folded image intersects
  the wedge, not in the through-set) is *forced* strictly between two
  through-layers — `above(a,x) is True` and `above(x,b) is True` (both
  forced, not free) for through-faces `a`, `b`. Reversing would provably trap or tear it.
- a second deep op on the same fold, or a deep op after a tip-local op
  (see §3 ordering).

Free pairs never refuse: pairwise freedom means no proof of trapping
exists. Known, documented unsoundness: a foreign face whose relations
are pairwise-free but jointly unsatisfiable ("no consistent completion
un-traps it") slips through to the sim — the strain oracle is the
runtime judge. If that proves insufficient, the follow-up is a targeted
existential search (a new decision, not this slice).

## 3. Module & pipeline wiring

- **New module `mcp_harness/shaping_deep.py`** (numpy; imports
  `flat_fold`, `layer_order`). `shaping.py` stays stdlib-only; its only
  change is dispatch.
- `reverse_deep(squared_fold, raw_fold, tip_xy, d, theta,
  gamma=45.0) -> dict` — analysis on `raw_fold`; creases written into a
  copy of `squared_fold` (raw and squared share CP coordinates —
  squaring adds corner paper outside the hull without moving hull
  geometry). Input dicts never mutated. Pullback creases terminating on
  a former-B hull edge (an F hull chord in the squared fold) are
  **extended straight through the corner paper to the true square
  boundary**, same assignment/angle — making explicit what the tip-local
  `_march_arm` already does implicitly. Output carries
  `edges_foldAngle` rebuilt as in the tip-local op.
- `shaping.apply_display_ops(fold, ops, raw=None)` — recognizes
  `reverse_deep:`; enforces **at most one deep op per fold, and deep
  ops before tip-local ops** (the raw-fold analysis is only exact
  against the pristine base; violations are per-op refusals, logged,
  later ops continue from the last good state). `parse_op` learns the
  new kind. `web/server.py` passes `raw=fold` at the one call site
  (`server.py:155`).
- **Provenance unchanged**: the raw linted `json` frame is never
  touched; everything rides `display_json`.

## 4. Testing

`mcp_harness/tests/test_shaping_deep.py`, offline except the single
Playwright smoke. Measure-then-pin throughout: a plan probe task runs
the machinery and PRINTS values before any expectation is pinned.

1. **Hand-derived tier**: a synthetic CP whose flap is 2 layers (a flap
   folded in half lengthwise, tip signature intact); `reverse_deep` at
   mid-flap; the full expected crease set, assignments, and fold angles
   derived on paper — this pins the per-layer assignment convention.
2. **Fixture tier** (dog, quad, star-4): through-sets asserted at the
   probe points from `probe_atdepth_stack.py`; pinned crease/edge/vertex
   counts as drift tripwires (values measured first).
3. **Contract tier**: every §2 refusal (including a synthetic
   forced-trap case), input dicts never mutated, one-deep-max and
   ordering enforcement, deep-then-tip-local composition succeeds,
   determinism across two calls.
4. **End-to-end smoke**: one scripted Playwright run — a
   `reverse_deep`'d dog `display_json` into the vendored sim
   (`simulator/index.html?embed=1`, slice-1 capture machinery), fold to
   100%, assert no NaN and max strain under `IDE_STRAIN_MAX`. A smoke
   assert, not a golden-mesh pin.

## 5. What this slice does NOT do

- No consistent-completion or existential search over free pairs.
- No agent / SYSTEM_PROMPT / strain-oracle-loop vocabulary wiring.
- No outside-at-depth (`sense=-1`).
- No squash/sink (slice 4); no B5.
- No post-op layer analysis (the sim renders the result; recomputing
  layer order after the op is slice-4+ territory if needed).
