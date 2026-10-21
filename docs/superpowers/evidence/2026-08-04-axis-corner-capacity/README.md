# Evidence — the symmetry axis sets a corner ceiling (2026-08-04)

Measured by the Goal 1 planning session at base commit `1c9abe0`, on macOS /
Accelerate. Cited by
[`docs/superpowers/specs/2026-08-04-whole-square-axis-projection-design.md`](../../specs/2026-08-04-whole-square-axis-projection-design.md)
§3.

**Why these live here rather than in a transcript.** The measurement that
retired the corner-forcing mechanism in 2026-08-02 survives only as one line of
prose in a different spec — no script, no fixture, no log anywhere in git — and
the 49-cell axis sweep that reordered this goal is likewise uncommitted. A
premise correction citing numbers that live only in a chat message reproduces
that failure on the correction itself. These are evidence-of-record. **Slice 0α
hardens them into a single reproducible probe under `mcp_harness/` writing a
`fixtures/` JSON**; until then, this directory is the citable artifact.

## Running them

Each probe is self-locating (`HERE` is derived from `__file__`) and runs every
arm in an isolated child process, because the engine can `SIGSEGV` on a
not-fully-converged base.

```bash
<repo>/mcp_harness/.venv/bin/python \
    docs/superpowers/evidence/2026-08-04-axis-corner-capacity/probe_5_axis_corner_capacity.py
```

Requires the engine `.so` in `mcp_harness/`. **`build.sh` defaults to
`PYTHON=python3`**, which on this machine resolves to a Homebrew interpreter
without `pybind11` and exits *without producing a `.so` and without an obvious
failure*. Build with:

```bash
cd mcp_harness && PYTHON=<repo>/mcp_harness/.venv/bin/python ./build.sh
```

The committed `out_*.txt` files were regenerated from these exact files and
reproduced byte-identically against the originals.

## What each probe answers

| probe | question | headline |
|---|---|---|
| `probe_1_corner_baseline` | Does corner pinning cost scale and coverage on `star(4)`? | No — and this is the **wrong tree**. `star(4)` is unpaired; pinning is a no-op at coverage 1.000000. Kept because the error is instructive |
| `probe_2_corner_arms` | k-sweep, dose-response, the *paired* star-4, the production templates | Unpaired stars k=5–8 reach coverage **1.000000**, 3 of 4 at equal-or-better scale. `star-4-sym` pair→corners is **−17.16% on both axes**. **8 of 8** corner arms fail on the four templates |
| `probe_3_edge_pins_and_order` | Does a **one**-equality edge pin survive where the two-equality pin does not? Is the star-5 win a basin re-roll? | 4/12 vs 0/8 — yes. ⚠ **The order-restart control is VACUOUS**: `star(5)`'s five leaves are identical, so permuting them is a relabeling. 0α owes a rerun on an unequal-length tree |
| `probe_4_pin_survival` | Does `ProjectActivePaths` drop a boundary pin? (Slice 0 Phase A Q4, never run) | **No.** Worst displacement 5.83e-07, five of seven arms ≤ 4.4e-09. Falsifies the old spec's R8 — **for a clamp-specific reason** (a pin at 0 or `w` sits on the per-iteration clamp) that does **not** generalize to interior pins |
| `probe_5_axis_corner_capacity` | Does the symmetry axis cap how many corners a *paired* tree can occupy? | **Perfect separation, 5 of 5 both ways.** Two pairs → four corners: diag45 fails on every subject; book0 reaches leaf hull **1.000000** with 4 corners on every subject, 4 of 5 at higher scale |

## The two things these do NOT show

1. **`probe_5` is optimizer-only** — `run_scale_optimization` then read
   locations, `build_and_export` never called, because the projection
   re-symmetrizes about `y = x` regardless of angle and corrupts or kills every
   non-45° build. So "OPT" means the optimizer converged, **not** that the tree
   packs. Several arms elsewhere optimize cleanly and die at the polygon stage.
2. **Leaf hull ≠ `hull_coverage`.** `probe_5` reports the convex hull area of
   the leaf positions (via `paper_coverage._hull` / `._area`).
   `hull_coverage` reads B-assigned vertices of the *exported* fold. Related
   quantities, not the same number.

Converting §3.4's optimizer result into an export-path result is exactly what
slice **S4b₀** exists to do.
