# Fold a re-parented base and look at it

Design [2026-08-03-path-reconciliation-design.md](../../specs/2026-08-03-path-reconciliation-design.md)
§7, last risk row — the only mitigation that spec offers for its **central
claim**:

> Non-sibling pairs may include genuinely different body positions. The
> junctions really are ~8% of the mesh apart along the body. Merging asserts
> they are one point. … the pack measurement is weak corroboration, but it is
> not proof, and the honest check is visual: **phase C should fold one
> re-parented base and look at it.**

Reproduce: `PYTHONPATH=.:tests .venv/bin/python fold_and_look.py [subject...]`
from `mcp_harness/`. Writes `bases.svg` — per subject, one row per arm, crease
pattern beside the flat-folded base.

## `mirror_overlay.svg` — the S1 tripwire sheet

Design [2026-08-04-cp-mirror-metric-design.md](../../specs/2026-08-04-cp-mirror-metric-design.md)
§6's tripwire, rendered for four cases: the two genuinely mirror-symmetric
controls (`star-4 + pairs`, `HSHAPE`) beside the two known-broken ones
(`TEMPLATE_QUADRUPED`, `QUAD`) — the same four cases §11's acceptance criteria
pin. Each panel overlays the crease pattern (solid, wide, assignment colour)
with its own reflection (dashed, narrow) and teal rings on `reflect(V)`, so a
swapped crease reads as a dashed line of one colour running down a solid line
of another.

Reproduce: `PYTHONPATH=.:tests .venv/bin/python \
../docs/superpowers/evidence/2026-08-03-reparented-bases/mirror_overlay.py`
from `mcp_harness/`. Writes `mirror_overlay.svg` into this directory, via
`cp_mirror.write_overlay_sheet` — added 2026-08-04 (fix-wave review) as the
committed driver `write_overlay_sheet` had lacked since the SVG itself was
first committed: the function had zero call sites and this README never
named the file it produces. `mirror_overlay.py` is now that call site;
running it reproduces the committed SVG byte-for-byte.

## Measured, serve default (voxel 64 / prune 0.30)

Under `cp_mirror.mirror_verdict` (spec
[2026-08-04-cp-mirror-metric-design.md](../../specs/2026-08-04-cp-mirror-metric-design.md)),
which replaced this file's own `cp_mirror_residual` — a vertex-only,
assignment-blind Hausdorff distance that could not see the defect the
`mv_swapped` column below reports. `residual` is a **witness**, never the
verdict: `residual == 0` does not imply `symmetric`, and `humanoid` below is
the standing proof. `—` for `mv_swapped` / `mv_mismatched` means the bijection
failed (`is_bijection` is `False`), so the assignment layer was never reached
— `None`, not zero.

| subject | arm | verts | creases | symmetric | residual | mv_swapped | mv_mismatched |
|---|---|---|---|---|---|---|---|
| humanoid | raw | 33 | 60 | False | 1.0442e-01 | — | — |
| humanoid | **reconciled** (1 re-parented) | 21 | 38 | **False** | 0.0000e+00 | **2** | 0 |
| quadruped | raw | — | — | **did not pack** | | | |
| quadruped | **reconciled** (2 re-parented) | 80 | 161 | False | 2.0200e-01 | — | — |
| fish | raw | 82 | 159 | False | 1.1233e-01 | — | — |
| fish | **reconciled** (2 re-parented) | 70 | 139 | False | 1.1457e-01 | — | — |

## What the eye found

**No pathology.** All three reconciled bases are well-formed uniaxial bases:
closed hulls, no holes, no degenerate faces, layers stacking to a single flat
silhouette. Nothing looks like a merge that fused two body positions that
should have stayed apart — which is the failure the risk row is about.

`humanoid` is the clean case and is visible in the render: the reconciled
crease pattern is markedly *simpler* than the raw one (21 vertices against 33,
38 creases against 60) and is a **geometrically exact** mirror about `y = x`
— every vertex has a mirror image and the edge set carries onto itself
(`is_bijection` True, `residual` 0.0) — while the raw pattern is 0.104 off.

**But the geometry being exact is not the same claim as the pattern being
symmetric, and `humanoid` reconciled is the case that proves it:** two of its
38 creases are exact mirror images that fold in *opposite* directions
(`mv_swapped = 2`), so `cp_mirror.mirror_verdict` correctly reads `symmetric:
False` even here. The earlier draft of this table read the 0.0 residual alone
and called this row "**exact**" without qualification — that overclaimed,
because the old `cp_mirror_residual` never looked at `edges_assignment` and
could not have caught this.

`quadruped` raw does not pack at all at this configuration, so its row is the
`+re-parent` rescue §2.6.2 reports, seen directly. Its reconciled row and
`fish`'s both fail on the *geometry* (`is_bijection` False, so `mv_swapped` /
`mv_mismatched` read `None`) rather than the assignment — a different failure
mode from `humanoid`'s, and one `mirror_verdict`'s three-column split (design
spec §5.2) exists specifically to keep apart.

## Two limits, stated so this is not over-read

1. **A flat-folded silhouette shows layer structure, not limb placement.** Every
   flap of a uniaxial base collapses onto the same axis, so this view cannot
   show that the two front legs ended up the same length. The number that
   answers *that* is `pair_path_gap_max`, measured **0.0** on all five subjects
   and on every (subject, voxel, prune) the live test sweeps. A genuine
   anatomical read needs the 3-D simulator, which is headed-only here.
2. **The residual is a directed Hausdorff distance, and is reported only as a
   witness.** `residual == 0` does not imply `symmetric`, for two independent
   reasons: a many-to-one collapse can drive it to 0 without a genuine
   bijection existing at all (caught by `cardinality_ok` / `is_bijection`,
   never by the residual); and, separately, even a real bijection says
   nothing about the M/V assignment. `humanoid`'s 0.0 residual above is the
   second case, cleanly: a real, full 21/21 bijection (`is_bijection` True,
   `cardinality_ok` True) that is demonstrably **not** sufficient for
   symmetry, because 2 of its creases swap M/V. Read `symmetric` and
   `mv_swapped` / `mv_mismatched`, never the residual alone.

Compiled through `server.draft_and_compile_full_base` — the **real serve path**,
not a bare engine call. Measured with a bare `HeadlessTreemaker` compile all
six rows read "did not pack", because that is attempt-0 for one exact node
list; §4.9 was wrong twice for exactly this reason.
