# Handoff: B5 slice 1 (pose-search recovery) — outcome

**Spec:** docs/superpowers/specs/2026-07-07-b5-pose-search-slice1-design.md

## What shipped
- `mcp_harness/pose_search.py` — pure module: `chamfer`, `grid_search`, `refine`,
  `PoseSearchError`, `GridResult(best_params, best_score, scores)`. 10 pytest tests
  (`tests/test_pose_search.py`), all passing.
- `mcp_harness/sim_capture.py` — Playwright capture driver (`SimSession`,
  `check_capture`, `build_star4_base`, `build_star4_shaped`, `CaptureError`,
  `DISP_GATE`, `ANCHOR_DISP`). Anchor: measured maxDisp **1.3088** vs recorded
  **1.3109** (headed chromium; band 1.0–1.6 around the recorded value — PASS).
  Headless was tried first (per spec default) and failed: headless chromium's
  WebGL context never advances the GPU solver on this machine (`maxDisplacement`
  stuck at exactly 0.0000). `SimSession`'s default was flipped to **headed**
  (`PW_HEADLESS=1` opts into headless instead of the reverse) as the permanent
  default for this machine.
- Probes (all under `mcp_harness/`, `.out.json`/`.out.jsonl`/`.log` files
  intentionally left uncommitted):
  - `probe_pose_sensitivity.py` — **verdict PROCEED**. Noise floor
    **0.000000** (solver fully deterministic across repeat captures — bit-identical
    point clouds, maxDisp 1.2496 both times). Min adjacent-θ chamfer **0.043670**
    (30° steps, θ∈{60,90,120,150} at f=0.5), min adjacent-d chamfer **0.114881**
    (f∈{0.3,0.5,0.7} at θ=120). Gate: min θ signal 0.043670 > 3×noise 0.0 → PROCEED.
    All 8 captures maxDisp 1.2491–1.4500 (no vacuous passes).
  - `probe_pose_recovery.py` — **RECOVERY PASS**. Target (θ*=100.0, f*=0.45),
    target capture maxDisp 1.2581. Coarse 5×5 grid argmin (87.5, 0.5), chamfer
    **0.027300** (the cell containing the target — `theta_ok=True`, `f_ok=True`).
    Refined 5×5 grid argmin (101.25, 0.425), chamfer **0.014271**
    (`refine_improved=True`, 0.014271 < 0.027300). Landscape = clean unimodal
    basin centered on the target cell on both axes (only far-field
    non-monotonicities at f=0.8, ≥3 grid cells from the target). f-axis signal
    is ~3x the θ-axis signal per adjacent step, matching Task 3's measured
    anisotropy (f 0.115–0.179 vs θ 0.044–0.049).
  - `probe_hull_quad.py` — **1/5 candidates fold**. Fixed family: 3
    `star4-head-{0.15,0.3,0.5}` + 2 `spine2-quad-s{0.2,0.4}-l{1.0,0.8}`. Only
    `star4-head-0.5` (4 unit legs + 0.5-length head, all off the center node)
    packs with all 4 leg leaves at the 4 paper corners (corners 4/4, squaring
    NO-OP) and folds in the sim: maxDisp **1.5241** (» 0.10 gate). The other
    four candidates re-pack away from the corners when the head/spine is added
    (corners 0/4–3/4), so squaring adds pinning geometry and no sim capture was
    attempted for them. → **full B5 UNBLOCKED**.

## The two findings that gate what happens next

1. **Recovery:** The loop closes end-to-end. Starting cold from a 5×5 coarse
   grid over (θ, fraction) and refining a second 5×5 grid around the coarse
   argmin, the search recovered a known applied `reverse` pose on one star-4
   flap to within 1.25° in θ and 0.025 in fraction of the true target — an
   order of magnitude tighter than the grid resolution (13.75° / 0.075) would
   guarantee on its own. `theta_ok`, `f_ok`, and `refine_improved` all True.
   Recommended tolerance for future refined-estimate acceptance: **one
   refine-grid step** (θ ±13.75°, f ±0.075) — this run beat that bound
   comfortably in θ, less so in f, so it is not an artificially loose pin.
2. **Hull-quad:** A hull-filling, animal-labeled foldable base **exists**:
   `star4-head-0.5`, a 5-leaf star topology (4 corner legs + 1 head, all
   incident on one center node) whose leaf hull already fills the square
   (`complete_square` is a geometric no-op) and which demonstrably folds in
   the Origami Simulator (maxDisp 1.524). It is 1 of 5 candidates tried —
   both true 2-spine quadruped topologies (spine node between front/back leg
   pairs) failed to fill the hull at either tested spine-length ratio, and
   smaller head lengths (0.15, 0.3) dislodged the star's own legs from the
   corners (knife-edge, non-monotonic circle-packing, consistent with prior
   `POLYS_MULTIPLE_IBPS` findings). So: a foldable animal-shaped substrate for
   B5 exists, but only in star topology for now — full B5 is unblocked to
   proceed on star-topology bases; spined-quadruped hull-filling bases remain
   an open problem for a later slice.

## Slice 2 entry point

Hull-quad found a working foldable animal base (`star4-head-0.5`, star
topology), so **slice 2 = joint-angle fit vs the `mesh_to_tree` skeleton** on
a star4-head-0.5-style base: given a target mesh's skeletal joint angles,
drive `pose_search`'s grid/refine loop (now proven to close on a
self-generated target in slice 1) to fit the base's flap parameters to the
skeleton's actual joint geometry, using `sim_capture`/`chamfer` as the same
score-and-iterate primitives. Caveats carried into slice 2:
- The foldable base must currently be **star topology** (all limbs off one
  center node) — spined quadrupeds never filled the hull in the 5-candidate
  probe family; extending to true spined-quadruped bases needs its own
  brainstorm/probe before it can be assumed to work.
- Hull-filling is **knife-edge in head length**: h=0.5 filled the hull,
  h=0.15/0.3 did not (packing re-optimizes discontinuously). Any new
  candidate body plan for slice 2 should be probed across a few ratios before
  being trusted, not assumed to hull-fill by analogy.
- Slice 1 recovered a single-flap, two-parameter (θ, fraction) pose on one
  base; slice 2 will need to generalize the search to multiple flaps/joints
  simultaneously, which was not exercised here.

## Gotchas carried forward
- `playwright` lives in `mcp_harness/.venv` ONLY — never add it to
  `requirements*.txt` or any CI/`.github` pin file.
- `SimSession` defaults to **HEADED** chromium, not headless: headless
  chromium's WebGL context never advances the GPU mass-spring solver on this
  machine (`maxDisplacement` stays exactly 0.0000 after a full 20s settle,
  tripping the anti-vacuous-pass `DISP_GATE` guard). Set `PW_HEADLESS=1` to
  opt into headless (e.g. for a future CI run on a machine where it might
  work) — do not assume headless works by default anywhere downstream.
- The solver is **exactly deterministic** across repeat captures on this
  machine (bit-identical point clouds, chamfer 0.0 on a same-params repeat).
  Do not reuse `0.0` as a convergence/noise tolerance anywhere downstream —
  it is a sign check (any nonzero signal clears "> 3x noise"), not a
  measured floor; pick tolerances from first principles or from the smallest
  observed real signal instead.
- Suggested refined-estimate tolerance for pose recovery: **one refine-grid
  step** (θ ±13.75°, f ±0.075), derived from Task 4's 5×5×5×5 coarse/refine
  grid spacing — not a universal constant, recompute if grid density changes.
- Probes/long-running scripts launched from a **subagent shell must use
  `nohup`** — a probe launched as a plain background task was reaped when the
  launching agent's turn ended partway through (Task 5's first hull-quad run,
  completed only 2/5 candidates before being killed); the identical script
  relaunched under `nohup` ran to completion.
