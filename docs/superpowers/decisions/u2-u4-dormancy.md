# Decision: U4's widened grid is obsolete; U2 stays dormant until measured

**Date:** 2026-09-04 · **Status:** ACCEPTED

§15 Integration was never done, and P2's components — `anatomy_spec` (U2),
`WIDE_VOXEL_GRID` / `wide_grid_budget` / `spec_distance` (U4) — are built,
tested and called by nothing. `server.py` contains **zero** references to any of
them. This records what happens to them.

## U4's widened grid — OBSOLETE, on measured evidence

U4's motivation was §1.1's **Class 1**, quoted verbatim:

> *"A bird's six flaps exist in the reachable set at voxel 192 / prune 0.40.
> `_VOXEL_GRID_DEFAULT` is `[96, 64, 128]`. **We have never looked there.**"*

Measured 2026-09-04 under the freeze default, sweeping the full 8×8 grid on live
meshes:

| subject | target | in-grid hits | out-of-grid hits |
|---|---|---|---|
| lizard | 6 | **7** | 6 |
| horse | 6 | **3** | 2 |
| bird | 6 | **1** | 5 |
| spider | 9 | **1** | 3 |
| octopus | 9 | **1** | 3 |

**All five subjects reach their authored target inside the shipped 3-voxel
grid.** The bird — Class 1's own example — has an in-grid hit. The claim the
unit rests on is false.

**So the widened grid buys nothing measurable on any subject we have**, at
~2.3× the skeleton builds. It stays dormant. `WIDE_VOXEL_GRID` and
`wide_grid_budget` remain in the tree as measured, tested constants; nothing
calls them, and nothing should until a subject is found that needs them.

⚠ **This is a consequence of the freeze default (PR #185), not of U4 being
wrong when written.** When the spec was authored the bird had 0 in-grid hits
and the lizard 0 hits anywhere. A one-line deterministic prune change removed
the unit's justification.

`spec_distance` is dormant for a second reason: on subjects the authored table
covers, `reference_count_for` already supplies R, which already drives ranking
through `fidelity_score`. It would duplicate machinery that ships.

## U2 — DORMANT PENDING MEASUREMENT, not obsolete

U2 addresses a **real** gap that nothing else covers: prompts absent from the
14-row authored table. That is the actual product — a user types an arbitrary
animal — and `reference_count_for` returns `None` for anything unlisted.

**It is not wired because it has never been measured on the thing it exists
for.** Two facts make wiring-before-measuring unacceptable here:

1. **U2's output is the pipeline's highest-leverage number.** An LLM-supplied
   `R` drives `fidelity_score`, which drives **both terminal exits** *and*
   **`_serve_rank`'s first key**. Unlike U5′ — whose pair list nothing ranked on
   — a wrong R steers the entire search.
2. **This model was measured unstable on a structurally similar task, three
   days ago.** U5′'s K=5 consensus found five draws expressing opinions with no
   pair appearing in three of them. The model did not disagree with the
   extractor; it disagreed with itself. Nothing yet says R is more stable than
   pairs.

**The measurement is specified in
`docs/superpowers/specs/2026-09-04-u2-unlisted-prompts.md` and must return
SHIP before U2 is wired.**

## What this decision does not say

* It does not say the LLM cannot do this. It says nobody has checked.
* It does not retire U2 or U4's code. Both stay in the tree, tested.
* It does not close §15. Integration remains open — but with U4 obsolete and
  U2 gated, there is currently **nothing whose wiring is justified**, which is
  itself the honest state of the design.
