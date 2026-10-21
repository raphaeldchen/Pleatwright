# Handoff — folded-state-first, slice 4 (squash / sink)

**Date:** 2026-07-06. Written at the end of the session that shipped PR #28
(at-depth reverse fold, `reverse_deep`, **merged** to main `7026fac`). Verify
main's tip is still at or above `7026fac` before starting; branch off origin/main.

## Where we are

Roadmap: `docs/superpowers/specs/2026-06-30-finished-model-view-research.md`.
Pillar A done (Model tab, PR #19). Pillar B core loop done (B1–B4, PRs #20–#24).
Current track = **folded-state-first** — build honest folded-geometry
primitives, each expressed as flat-CP creases + fold angles applied at the
**display boundary** (provenance contract: the raw linted `json` frame is NEVER
touched; shaping rides on `display_json`).

1. ✅ **Flat-fold engine** — PR #26. `mcp_harness/flat_fold.py`:
   `flat_fold(fold) -> FlatFoldResult` (`.faces`, `.transforms`,
   `.folded_vertices`, `.closure`, `.shared_edges`). Honest domain = RAW hull
   folds; Kawasaki-violating bases return large closure errors, never raise.
   Matches the live sim to 7e-6. Spec:
   `docs/superpowers/specs/2026-07-03-flat-fold-engine-slice1-design.md`.
2. ✅ **Layer ordering** — PR #27. `mcp_harness/layer_order.py`:
   `layer_order(result) -> LayerOrder`; `above(a,b) -> bool|None` (forced
   relations only), `stack_at(p)` (raises `AmbiguousStack` w/ `.free_pairs`),
   `.cells`. Fixpoint constraint propagation, **no search** — unknown-at-fixpoint
   IS the answer. Spec:
   `docs/superpowers/specs/2026-07-04-layer-order-slice2-design.md`.
3. ✅ **At-depth reverse fold** — PR #28. `mcp_harness/shaping_deep.py`:
   `reverse_deep(squared_fold, raw_fold, tip_xy, d, theta, gamma=45.0) -> dict`.
   Reverse-folds a flap THROUGH all its layers at a non-tip depth. Defined
   GEOMETRICALLY (through-set = CP crease-BFS gated by the folded fold-line;
   per-layer M/V from orientation parity), with `layer_order` used ONLY as a
   forced-only trap lint — free pairs never block or decide. Analyzes the RAW
   hull fold, writes creases into the SQUARED display fold. `shaping.py`
   `parse_op` / `apply_display_op(s)` gained a `reverse_deep:` dispatch + `raw=`
   plumbing; `web/server.py` passes `raw=fold` at the one display site.
   Spec: `docs/superpowers/specs/2026-07-05-atdepth-reverse-fold-slice3-design.md`.
   Plan: `docs/superpowers/plans/2026-07-05-atdepth-reverse-fold-slice3.md`.
4. ⏭ **THIS SLICE: squash / sink** — see below.
5. B5 target-mesh-guided shaping — LAST, do not start.

**No agent/SYSTEM_PROMPT wiring exists yet for `reverse_deep`** (deferred to its
own mini-PR after this slice). Squash/sink is engine + display only, same as
slice 3, unless the brainstorm decides otherwise.

## The opening design question for slice 4 (decide first — do not skip to impl)

Squash and sink are the two classic "flatten a flap into the sheet" moves, and
they differ from `reverse_deep` in a way that must be pinned before any code:

- **Reverse fold (done):** the flap keeps its layer count; you flip a
  sub-flap's M/V through the layers it already occupies.
- **Squash:** you open ONE flap and press it symmetrically flat — it
  *redistributes* a flap's paper into two mirror halves, adding new creases but
  keeping the sheet flat-foldable.
- **Sink (open vs. closed):** you reverse a flap's tip *inward* through the
  layer stack so it disappears between the layers — this is the move that most
  stresses layer ordering, because the sunk paper must nest BETWEEN existing
  layers at a forced depth.

The crux question, forced by the same data that shaped slice 3 (dog's deepest
cell = 20 faces / 96 free pairs, mostly ambiguous stacks):

> **Does sink need to place the sunk paper at a specific position in the layer
> order (→ it needs `stack_at` to be at least partially forced there, and must
> refuse or fall back when it is not), or can sink — like `reverse_deep` — be
> defined purely GEOMETRICALLY (reflect the tip region through a fold plane at
> the sink depth) and only lint against forced relations, letting the
> sim/strain oracle be the runtime judge?**

Slice 3 settled the analogous question for reverse fold in favor of
*geometric definition + forced-only lint, no search*. Start the brainstorm by
testing whether that same contract holds for sink, or whether sink's
"nest between layers" semantics genuinely require consulting (partial) order —
and whether **squash and sink are one slice or should be split** (squash may be
flat-foldable and order-agnostic; sink may not be). Measure before deciding:
extend `mcp_harness/probe_atdepth_stack.py` (or a new probe) to report, at
realistic squash/sink points, whether the target depth is forced.

## Load-bearing findings from slice 3 (read before you build on its outputs)

- **★ The squared dog and squared quad do NOT fold in the vendored mass-spring
  sim** — `setFold(100)` relaxes them to the FLAT rest state (max per-vertex
  displacement EXACTLY 0.0). Squaring a hull-frontier base adds flat "F" corner
  faces that pin the sheet flat. **star-4's hull fills the square**
  (`complete_square` is a no-op, raw == squared) so it folds. Any strain-gate
  "pass" on dog/quad is VACUOUS — the sim smoke MUST also assert
  `displacement > 0`. Slice-4 smokes: use **star-4** as the folding base and
  keep the anti-vacuous displacement guard (see
  `mcp_harness/probe_deep_sim_smoke.py`).
- **★ SNAP THE APEX FIRST.** At some deep points `reverse_deep` emits a residual
  ~1e-9 zero-length sliver edge: two fold-apex split requests differ by ~1.1e-9,
  just past `_key`'s round-to-9 dedup, producing two near-coincident apex
  vertices. It clears `flat_fold`'s 1e-12 guard and didn't break the smoke, but
  **before slice 4 builds on `reverse_deep`/`shaping_deep` outputs, snap
  apex split-requests at ~8dp before `_split_edges`.** (This same multi-split
  was the root cause of a StopIteration→ShapingError bug, now fixed by a
  chain-walk that retargets ALL carried-side fragments or refuses.) This is the
  first concrete task candidate for the slice.
- `flat_fold` closure is **M/V-BLIND** (M and V reflect identically in 2D) →
  `layer_order` is the real oracle for any per-layer assignment rule. Do not try
  to validate an assignment rule against closure alone.
- **Shared-edge clipping fabricates silent holes** — Monte-Carlo point-coverage
  is the tripwire, not area sums (`layer_order._cells`).
- `FlatFoldResult` is `@dataclass(frozen=True, eq=False)`; numpy 2.x has no
  `arr.ptp()` (use `np.ptp(arr, 0)`).
- Playwright CAN drive the vendored sim's GPU solver (postMessage
  loadFold / setFold(100) / getFoldedGeometry against
  `simulator/index.html?embed=1`).
- `docs/dog.fold` has never folded in the sim — consistent with the squaring
  finding above; do not treat it as a smoke base.

## Process (unchanged — followed for all three prior slices)

- Superpowers skills throughout: **brainstorming** (`docs/superpowers/specs/`)
  → **writing-plans** (`docs/superpowers/plans/`) → **subagent-driven
  development** → **finishing-a-development-branch**. SDD ledger at
  `.superpowers/sdd/progress.md` (gitignored).
- **Ask the user before anything outward-facing; the user merges PRs.**
- **Measure-then-pin:** probe engine behavior (commit the probe script as
  evidence) before pinning any expected value in a test.
- Backend suite: `cd mcp_harness && .venv/bin/python -m pytest tests -q`
  (~8 min, currently **391 passed / 3 skipped**).

## Deferred (fine to leave; pick up opportunistically)

- Agent/SYSTEM_PROMPT wiring for `reverse_deep` (own mini-PR, after this slice).
- Slice-3 minors in the SDD ledger from PR #28's final review (all safe-to-defer).
- B5 (target-mesh-guided shaping) is LAST — do not start it in this slice.
