# Squash fold (folded-state-first, slice 4) — design

> **OUTCOME (2026-07-07): squash DEFERRED.** The de-risk gate (§1) failed
> provably — on an edge flap (which our `tips()` signature always selects) a
> flat-foldable symmetric squash reduces to `reverse_fold`. The slice shipped
> the apex-snap fix + a verified `sink`=`reverse_deep(θ=180)` alias instead.
> See `docs/superpowers/2026-07-07-handoff-folded-state-slice4-outcome.md`.
> This spec is preserved as the design that was attempted and de-risked.

**Date:** 2026-07-06. Fourth of the folded-state-first slices
(flat-fold engine → layer ordering → at-depth reverse fold →
**squash/sink**). Builds on slice 1's `flat_fold()` (PR #26), slice 2's
`layer_order()` (PR #27), and slice 3's `reverse_deep()` (PR #28, merged
at main `7026fac`). Probe evidence for the crux decision:
`mcp_harness/probe_atdepth_stack.py` (slice-3's committed probe, re-run
2026-07-06).

## Decisions (from brainstorming)

| Decision | Choice |
|---|---|
| **Split squash and sink** | The slice ships **squash only**. Measurement (below) shows sink carries no honest new content in an M/V-blind + forced-only-order engine: an open sink's creases and folded coordinates equal `reverse_deep(θ=180)`; its sole distinguishing semantic — the sunk bundle's *interior layer rank* — is exactly the unforced quantity (dog: 24–64 free pairs at every flap). Building a separate sink primitive would either duplicate `reverse_deep` or require the order *commitment/search* the whole track has refused. Squash, by contrast, is genuinely new 2D geometry. |
| **Sink: verify-then-alias, no new code** | A plan task *verifies* "open sink ≡ `reverse_deep(θ=180)`" on star-4 (fully forced order, so every layer is hand-checkable). If it holds, sink is exposed only as a **documented alias/preset** of `reverse_deep(θ=180)` with a note that interior nesting is left to the sim/strain oracle. No sink module, no order-search. If the verification *fails* (sink is geometrically distinct after all), stop and re-brainstorm sink as its own slice — do not improvise. |
| Crux: relation to layer order | **Geometric definition + forced-only lint, no search** — the same contract slice 3 settled. A squash is *local* to one flap's own layers, so its layer relations are forced (star-4/quad `stack_at` is TOTAL); the lint refuses provable conflicts, free pairs never block or decide, the sim/strain oracle stays the runtime judge (the B4 pattern). |
| Op surface & module | **Tip-local sibling of `reverse_fold` in `shaping.py`** (flat-CP wedge construction, reuses `_find_tip`/`_march_arm`/`_split_edges`), *not* `shaping_deep`. New op kind `squash:X,Y:D[:...]`. A squash *opens a pocket* — it spreads the flap's two stacked layers apart about the spine, revealing paper hidden in the flat fold. This is a **different** reflection than `reverse_deep`'s (across the spine's folded image, moving a whole hidden layer — not a perpendicular sub-region of the footprint); the exact construction is **pinned by the probe** (§1), which decides folded-space vs. purely flat-CP. It stays a flat-CP-local op like `reverse_fold`. |
| Slice scope | **Engine + display dispatch, no agent wiring.** SYSTEM_PROMPT / strain-oracle vocabulary for `reverse_deep` AND `squash` deferred to one shared mini-PR after this slice. |
| Prerequisite (from handoff) | **Task 1: snap fold-apex split-requests to ~8dp before `_split_edges`** in `shaping_deep`, killing the residual ~1e-9 zero-length sliver, since squash reuses the same `_key`/`_split_edges` machinery and would inherit the bug. |

### Probe evidence (measured 2026-07-06)

`probe_atdepth_stack.py` reports `stack_at` at realistic mid-flap points
(30/50/70% along each tip's axial). `stack_at` at a flap point IS the
covering stack a sink would nest into, so it directly answers "is the
sink target depth forced?":

- **star-4** (8 faces): `stack_at` **TOTAL** (0/28 free pairs) at every tip.
- **quad** (10 faces): `stack_at` **TOTAL** *locally* — each tip's cover
  of 4 faces is fully ordered (0/6 free), even though slice 2's deep cell
  was not.
- **dog** (28 faces): `stack_at` **AMBIGUOUS** everywhere — 24 to 64 free
  pairs among the 8–16-face local cover.

So on the realistic target (dog) the covering stack at *every* flap is
massively unforced → a sink demanding a forced interior rank would refuse
across the whole dog (slice-3's dead-on-arrival pathology). A squash's
layer relations are the *local* flap-own relations, which ARE forced
(star-4/quad TOTAL) → the forced-only lint has teeth for squash.

## 1. Purpose & op semantics

`squash:X,Y:D` — a **symmetric squash** of the flap whose tip is nearest
CP point (X,Y): open the flap at depth `d` along its axial crease and
press it flat symmetrically about its spine, spreading the flap's second
layer into the plane. Parameter shape matches the tip-local ops
(`_find_tip` selects a tip = B edge + exactly one M/V crease; `d` is a
depth along the axial, `0 < d < ax_len`). An optional half-angle `γ`
(default 45°) parameterizes the opened wedge as in `reverse_fold`.

The op is **defined geometrically** in flat CP — layer order never
determines what folds:

- **Wedge.** Apex `F` on the axial (spine) crease at depth `d` from the
  tip `P`; arms at ±γ tipward (the `reverse_fold` wedge). The flap is
  symmetric about the spine, so the two arms are mirror images across it.
- **Squash creases.** Opening the flap reassigns the spine segment `P–F`
  and introduces the symmetric arm creases; the flap's outline (its two
  raw edges) spreads about the spine. The result is flat-foldable
  (Kawasaki holds at `F` by the ±γ symmetry).
- **Per-crease M/V & fold angle.** **The exact crease set, assignments,
  and fold angles are measured-then-pinned** — hand-derived on star-4's
  edge-midpoint flap `v2` (tip (1,0.5), spine = perpendicular bisector to
  center `v3`, two symmetric raw half-edges to corners (1,1)/(1,0)),
  where the layer order is fully forced. The spec states the principle
  (symmetric opening about the spine); the plan's probe fixes the
  numbers. This mirrors slice 3's per-layer-assignment approach.

### De-risking gate (resolve FIRST in the plan, before pinning tests)

The one open geometric risk, flagged in brainstorming: on our
*edge/corner* flaps (one B + one M/V crease), a symmetric squash must be
shown **visibly distinct from `reverse_fold(θ=90)`** — distinct crease
set and/or a distinct folded silhouette (pocket opened, second layer
revealed). The plan's first geometric task probes exactly this on the
`v2` flap. **If the probe shows non-distinctness, STOP and re-brainstorm
— do not ship a redundant op.** Everything downstream is contingent on
this gate passing.

## 2. Validity — forced-only lint, honest refusals

`ShapingError` (op skipped, one stderr line, fold stream never breaks —
the existing `apply_display_op` contract) when:

- no tip signature (B + exactly one M/V) near (X,Y); `d` reaches past the
  axial crease (`d ≥ ax_len − EPS`); an arm/squash crease grazes an
  existing vertex within `SNAP`; the opened wedge is degenerate;
- **region guard** (as in `reverse_fold`): a pre-existing vertex lies
  strictly inside the opened wedge region;
- **forced-conflict lint**: if a squash crease's assignment is forced
  inconsistent by `layer_order`'s forced relations among the flap's own
  layers, refuse. (Squash relations are local and forced on star-4/quad,
  so this lint has teeth; free pairs never refuse — the sim/strain oracle
  is the runtime judge, per §Decisions.)

## 3. Module & pipeline wiring

- **`shaping.py`** gains `squash(fold, tip_xy, d, gamma=45.0) -> dict`,
  a sibling of `reverse_fold` (stdlib-only path preserved; it reuses the
  existing wedge/march/split helpers). Input dict never mutated; returns
  a new fold with `vertices_coords`/`edges_vertices`/`edges_assignment`/
  `edges_foldAngle` rebuilt exactly as `reverse_fold` does.
- `parse_op` learns `squash:X,Y:D` (and optional `:γ`). `apply_display_op`
  / `apply_display_ops` dispatch it. Tip-local → needs **no** `raw=`
  (unlike `reverse_deep`). Composition ordering with `reverse_deep`
  follows the existing rule (deep before tip-local; squash is tip-local).
- **Provenance unchanged**: the raw linted `json` frame is never touched;
  everything rides `display_json`. `web/server.py` needs no new plumbing
  (squash takes no `raw`).
- **Task 1 (shaping_deep apex snap)** is an independent fix landing first:
  in `reverse_deep`'s split-request gathering, snap apex points to ~8dp
  (before `_split_edges`) so near-coincident apex requests dedup to one
  vertex. Pinned by re-running `probe_deep_sim_smoke.py` (0 sliver edges).

## 4. Testing

`mcp_harness/tests/test_shaping.py` (squash lives in `shaping.py`) plus a
star-4 Playwright smoke. Measure-then-pin throughout: a plan probe task
runs the machinery and PRINTS values before any expectation is pinned.

1. **De-risk probe** (gate, above): print the `v2` squash crease set and
   compare to `reverse_fold(θ=90)`; commit the probe script as evidence.
2. **Hand-derived tier**: star-4 `v2` squash — full expected crease set,
   assignments, fold angles derived on paper; pins the M/V convention.
3. **Fixture tier**: squash at forced-order flaps (star-4, quad); pinned
   crease/edge/vertex counts as drift tripwires (measured first).
4. **Contract tier**: every §2 refusal (incl. a synthetic
   forced-conflict case), input dict never mutated, determinism across
   two calls, `parse_op`/dispatch round-trip.
5. **Task-1 regression**: `reverse_deep` emits **0 zero-length edges** at
   the deep points that previously produced the ~1e-9 sliver.
6. **End-to-end smoke**: one scripted Playwright run — a `squash`'d
   **star-4** `display_json` into the vendored sim
   (`simulator/index.html?embed=1`), fold to 100%, assert no NaN, max
   strain under `IDE_STRAIN_MAX`, **and `displacement > 0`** (anti-vacuous
   guard: the squared dog/quad relax flat and never fold; star-4's hull
   fills the square so it folds).
7. **Sink verification** (Decisions): assert `reverse_deep(star-4,
   θ=180)` matches the hand-derived open-sink crease set on the forced
   base; on match, add the documented `sink` alias (a thin `reverse_deep`
   θ=180 preset) + its round-trip test. On mismatch, the alias is NOT
   added and the mismatch is reported for a fresh brainstorm.

## 5. What this slice does NOT do

- No sink *module* and no interior-rank placement / order search — sink
  is only a verified alias of `reverse_deep(θ=180)`, or deferred.
- No consistent-completion or existential search over free pairs.
- No agent / SYSTEM_PROMPT / strain-oracle vocabulary wiring (shared
  mini-PR after this slice, covering `reverse_deep` + `squash` + `sink`).
- No petal fold / other compound moves; no B5 (target-mesh-guided
  shaping) — that is LAST.
- No post-op layer re-analysis (the sim renders the result).
