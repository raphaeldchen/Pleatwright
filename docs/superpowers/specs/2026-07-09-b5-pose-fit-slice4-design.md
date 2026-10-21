# B5 slice 4 — second descent pass + crimp reachability (design)

**Date:** 2026-07-09
**Status:** IMPLEMENTED — HALTED at gate 2 (crimp extension 0.0927 deg < 10 past reverse-only ceiling 62.8255; gate-1 second pass REGRESSED vs slice-3 seed 276.1833 -> 279.2709) (handoff: docs/superpowers/2026-07-09-handoff-b5-slice4-outcome.md)
**Predecessor:** docs/superpowers/specs/2026-07-08-b5-pose-fit-slice3-design.md
(IMPLEMENTED — FIT FAIL: back-group cross-coupling MISS; handoff
docs/superpowers/2026-07-08-handoff-b5-slice3-outcome.md)
**Branch:** feat/b5-pose-fit-slice4 off main (6a880ca, PR #33 merged —
merge verified on main's tip before branching)

## Goal

Answer: can richer ops + iteration actually pose the winner base
(asymmetric star b=0.95, h=0.40) toward the fox targets
{front 134.8316, back 138.6544, head 137.7186} deg?

Slice 3's fit FAILED on two independent, measured causes:

1. **Cross-group coupling** — back achieved 79.1928 in isolation but the
   later head fold moved the reference vector; the final joint capture
   re-measured back at 22.9936 (the MISS).
2. **Reachability** — single reverse folds top out 76–111 deg short of
   the targets even in isolation (front gap 85.3452, back gap 75.8289,
   head gap 110.5922 at their best-achievable theta).

Slice 4 attacks both, gated so each answer is cheap before the next is
bought: a second coordinate-descent pass pins the reverse-only ceiling
(coupling fix), a crimp range probe on the back group gates whether the
richer op is worth a fit (reachability), and only then does the extended
multi-pass fit run.

**Honest-outcome rule (standing): a documented FAIL or gated HALT with
measured numbers is a successful slice. Verdicts are never softened.**

## Decisions (all user-approved)

| Question | Decision | Why |
|---|---|---|
| Crimp gate threshold | Crimp's best-achievable back angle must beat the reverse-only ceiling by **>= 10.0 deg**; ceiling = max(re-measured reverse-only back best-achievable, stage-1 final back achieved) | With ~76 deg of back gap remaining, a 3 deg extension is measurable but pointless — the multi-pass fit is only worth building if crimp moves at limb-bend scale. The exact measured extension is reported either way |
| Crimp scope in the fit | **Back group only**; front/head stay reverse-only | The gate evidence only covers back (the proven MISS group). If the fit shows front/head become the bottleneck, that is the measured slice-5 entry point |
| Stage-3 PASS rule | Inherited relative-bound rule (re-measured bounds) AND total error < unshaped baseline **AND total error strictly < stage-1 reverse-only final error** | Without the stage-1 comparator, the fit could "PASS" while doing no better than the free reverse-only baseline — crimp would have provably added nothing |
| Architecture | Pure-loop extraction: `pose_search.coordinate_descent` + in-place probe evolution | One pytest-covered code path serves stage 1 and stage 3; avoids two divergent hand-rolled loop copies (approach B) and duplicated frozen probes (approach C — git history already preserves slice 3) |
| Stage-1 seeding | Resume from slice-3's fitted params, pinned as constants citing the committed handoff | Fitted params are independent of the angle_tol bug; descent is deterministic modulo ~0.02 deg capture drift; avoids depending on uncommitted `.out.json` files. Comparability caveat documented below |
| f2 in the fit | Pinned at the crimp range probe's argmax cell (measure-then-pin applied to the search grid) | Keeps a crimp stage at ~50 evals like a reverse stage instead of 150; total budget ~380 captures (~4 h sim) instead of ~600 |
| Back stage vocabulary | Crimp-only (not reverse-union-crimp) | The gate guarantees crimp exceeds the reverse ceiling somewhere; if pure-crimp back still underperforms overall, the must-beat-stage-1 comparator catches it honestly. Halves the grid |

## Execution gates (each can end the slice as a documented outcome)

- **Gate 0 (task zero):** two cleanups land (tail-drop tie guard,
  angle_tol grid-adjacency fix) + full suite green + `probe_angle_range`
  re-run to regenerate honest bounds (the tol fix changes `angle_tol`,
  which feeds every later PASS bound; the PROCEED/HALT verdict itself is
  tol-independent — ranges don't involve tol). PROCEED required.
- **Gate 1 (stage 1):** reverse-only second pass — schedule
  front→back→head→front→back, resuming from slice-3's fitted params, so
  only the two resume stages run (~100 captures max). Pins the
  reverse-only ceiling. **Never halts.** Even a relative-bound PASS gets
  the honest statement that absolute gaps remain ~60–110 deg.
- **Gate 2 (stage 2):** `probe_crimp_range.py` on the back group.
  **HALT unless** max successful crimp back angle >= ceiling + 10.0 deg
  (ceiling defined above). Extension toward the target means a LARGER
  angle (target 138.65 sits above the ~62.8 ceiling); a range extension
  downward does not help and correctly fails the gate. A HALT ends the
  slice like slice 2's: documented outcome + handoff.
- **Gate 3 (stage 3):** extended multi-pass fit, full 5-stage schedule
  from scratch: F(rev) → B(crimp) → H(rev) → F(rev) → B(crimp).
  PASS per the pinned rule. Measured verdict either way.

## Components

### `pose_search.py` (MODIFY — new pure function, pytest-covered)

```
coordinate_descent(evaluator_factory, schedule, initial=None)
    -> DescentResult(fitted, stages)
```

- `schedule`: explicit list of `(group, axes)` stages — no implicit pass
  counting, no early-stop (the schedule is a fixed 5-stage list; YAGNI).
- Threads a `fitted` dict through the stages:
  `evaluator_factory(group, fitted_snapshot)` returns the evaluate
  callable; each stage runs `grid_search` + one `refine`, then writes
  `fitted[group] = fine.best_params`.
- `initial` seeds `fitted` (stage-1 resume). Returns per-stage records
  (group, coarse best/score, fine best/score) for the JSONL log.
- Same failure semantics as `grid_search`: evaluator raise/non-finite →
  inf; all-inf stage → `PoseSearchError` (probe reports and exits).

### `shaping.py` (MODIFY — new pure helper, pytest-covered)

```
crimp_ops(xy, axial_len, theta, fraction, fraction2)
    -> ["reverse:{x},{y}:{d1}:{theta}", "outside:{x},{y}:{d2}:{theta}"]
```

- Mirrors `server.py`'s tool-layer crimp composition exactly:
  `d1 = fraction * axial_len`, `d2 = fraction2 * d1`; the second half is
  the `outside:` (sense=-1) op.
- Carries the tool-layer guards: theta must be in (0, 180) **excluding
  exactly 90** (the known silent mis-target), fraction and fraction2 in
  (0, 1). Violations raise `ShapingError`.
- Emits ONLY the engine's existing op strings — no new op vocabulary, so
  display replay via `ide_shape_ops` is unchanged.
- `server.py` is NOT refactored onto this helper this slice (scope).

### `starhead.py` (MODIFY)

- `make_ops` accepts per-group op specs: a bare `(theta, fraction)`
  tuple stays a reverse op (back-compat — stage 1 and existing callers
  unchanged); `("crimp", theta, fraction, fraction2)` emits the crimp
  pair per tip in the group via `shaping.crimp_ops` (a leg pair shares
  its params, same as reverse).
- Crimp atomicity is free: `apply_ops` already applies one op at a time
  and raises on any refused op (object-identity check), so a
  half-applied crimp can never be scored.
- **Task-zero fix (fox_targets tail drop):** if the top two unpaired
  leaves' y-values are within 1e-6, raise `PoseTargetError` instead of
  guessing which is the head (never guess — same principle as the
  hub-tie guard). Current fox data is nowhere near the guard
  (head y=39.9 vs tail y=18.1).

### `probe_angle_range.py` (MODIFY + re-run)

- **Task-zero fix (angle_tol):** neighbors for the tolerance must be
  grid-adjacent in `THETAS`, not adjacent in the successful-only list —
  a failed cell currently makes "adjacent" span two grid steps, silently
  inflating the PASS bound. Fallback when both grid neighbors of the
  best cell failed: max one-step angle diff over all successful
  grid-adjacent pairs in that group's sweep. The existing <2-successes
  gate already covers the degenerate case.
- Re-run after the fix (16 captures, ~8 min) so all slice-4 bounds use
  honest tolerances. Requires the winner in `probe_star_asym.out.json`;
  if absent (fresh checkout), re-run `probe_star_asym.py` first —
  slice-3 machinery, unchanged.

### `probe_pose_fit.py` (REBUILD as thin driver)

- Drives `pose_search.coordinate_descent` with a schedule + vocabulary
  parameter; keeps the existing evaluator shape (apply ops → capture →
  anti-vacuous check → achieved angles → total angle error), the JSONL
  incremental log, and the unshaped-baseline-first convention.
- **Stage-1 mode (reverse-only resume):** seeds
  `initial = {front: (73.75, 0.575), back: (73.75, 0.8),
  head: (73.75, 0.35)}` — pinned constants citing the committed slice-3
  handoff, NOT read from uncommitted probe outputs — and runs only the
  two resume stages `[front, back]` with reverse axes (5×5 coarse +
  refine each; <= ~100 captures). Output:
  `probe_pose_fit_r2.out.{json,jsonl,log}`.
- **Stage-3 mode (extended, gated on the crimp probe's PROCEED):** full
  5-stage schedule from scratch; back stages use crimp axes
  theta ∈ {60, 75, 105, 142.5, 170} × fraction ∈ {0.2, 0.35, 0.5, 0.65,
  0.8} with f2 pinned from the crimp probe. ~250 captures, overnight
  nohup run. Output: `probe_pose_fit_x.out.{json,jsonl,log}`.
- Separate output files per stage so evidence never clobbers (slice-3's
  local outputs also stay intact).
- `refine` around a crimp theta can generate exactly 90 (midpoint of
  75–105): the `crimp_ops` guard raises → scored inf → skipped. At most
  one wasted eval per refine; documented, not special-cased.

### `probe_crimp_range.py` (NEW — the gate probe)

- Back group only, other groups unshaped, fraction fixed at 0.5 (the
  range-sweep convention); winner base via `starhead.winner_base()`.
- Grid: theta ∈ {60, 75, 105, 142.5, 170} (no 90; 60/142.5/170 shared
  with the reverse sweep for comparability) × f2 ∈ {0.35, 0.5, 0.65} =
  15 captures (~9 min).
- Records each cell's back achieved angle + disp; failures recorded with
  the error string (flat-equilibrium holes expected, like slice 3's
  45/150 inf cells).
- Prints and writes: the best crimp cell (best = MAXIMUM back achieved
  angle, which is also closest-to-target since the fox target sits far
  above the reachable range), f2 sensitivity (angle spread across f2 at
  the best theta), the ceiling used, the measured extension, and the
  verdict `PROCEED` (extension >= 10.0) or `HALT`.
- Pins `f2*` = the best cell's f2 into its `.out.json` for stage 3.
- Also computes back's crimp-side `angle_tol`: the one-grid-step angle
  change at the best cell over theta-grid-adjacent successful neighbors
  (same rule + fallback as the fixed `probe_angle_range`) — this is the
  tolerance stage 3's back bound uses, since back's bound comes from
  THIS grid, not the reverse sweep's.

## Data flow

```
gate 0: cleanups + suite green
        └─ probe_angle_range.py (re-run, fixed tol) ─ PROCEED required
gate 1: probe_pose_fit.py --stage r2   (reverse-only resume, 2 stages)
        └─ pins reverse-only ceiling (never halts)
gate 2: probe_crimp_range.py           (15 captures, back group)
        └─ extension >= 10 deg? ── NO → documented HALT + handoff
                                   YES ↓ (f2* pinned)
gate 3: probe_pose_fit.py --stage x    (5-stage descent, crimp back)
        └─ FIT PASS/FAIL per pinned rule → handoff either way
```

The fit side continues to reuse verbatim: `pose_target.py`,
`sim_capture.py` (`tracked_points`, `check_capture`), `web/server.py`,
the lint path, the raw `json` frame. `playwright` stays in
`mcp_harness/.venv` ONLY.

## PASS rule (stage 3, pinned)

Per group: final |achieved − target| <= re-measured best-achievable gap
+ fixed angle_tol, where back's gap AND tol come from the crimp range
probe's grid (best cell + its theta-grid-adjacent tolerance) and
front/head's from the re-run reverse sweep. AND total
angle error strictly < unshaped baseline. AND total angle error strictly
< stage-1 (reverse-only multi-pass) final error.

## Comparability caveat (documented, accepted)

Stage 1 resumes from slice-3's recorded fitted params rather than
re-searching its first three stages. Legitimate because: the fitted
params are independent of the angle_tol bug (tol feeds only the PASS
bound, not the search), and the descent is deterministic modulo the
measured ~1e-5–0.02 deg capture drift. Stage 3 runs its full schedule
from scratch because its back stages search axes that earlier stages'
fits depend on. Both end at the same 5-stage schedule shape
(F→B→H→F→B); the stage-1-vs-stage-3 comparison is on final total error
from the final joint capture of each.

## Error handling

All slice-2/3 semantics carry verbatim:

- Evaluator failures (op refused/identity fold, capture failure,
  disp <= 0.10, NaN) → raise inside the evaluator → scored inf.
- Anti-vacuous guard on EVERY capture: maxDisplacement > 0.10 and 0 NaN.
- Solver is deterministic-ish ONLY: capture drift ~1e-5–0.02 deg — never
  0.0 tolerances; never assert bit-identical re-captures.
- `SimSession` HEADED by default (`PW_HEADLESS=1` opts in).
- multiprocessing spawn workers need a real script file as `__main__`.
- Sim bridge `flat_coords` are SCENE-frame; `tracked_points`
  index-alignment + uniform-scale check is the guarantee.
- Long probe runs launched from subagent shells MUST use `nohup`; the
  controller polls the log file, never Monitor.

## Testing

- `pose_search.coordinate_descent`: pytest with mock evaluators —
  stage sequencing, fitted-dict threading, `initial` seeding, per-stage
  records, all-inf stage raising (~4 tests). Pure, no sim.
- `shaping.crimp_ops`: pytest — composition matches the tool-layer
  formula (d1/d2 arithmetic, op-string shape), theta=90 and boundary
  guards raise (~3 tests). Pure, no sim.
- `starhead` tail-drop tie guard: pytest on a synthetic tree with tied
  unpaired-leaf y-values (the grouping logic itself is already
  pytest-pinned in `pose_target`).
- Probes stay OUT of pytest; printed maps, verdicts, and JSONL logs are
  the evidence. Probe outputs (`*.out.*`) stay uncommitted.
- Full backend suite (`cd mcp_harness && .venv/bin/python -m pytest
  tests -q`) must stay green (baseline 424 passed / 3 skipped).

## Budget

~380 captures total ≈ 4 h sim time across runs: range re-run 16 +
stage 1 <= ~100 + crimp gate 15 + stage 3 ~250. Stage 3 is an overnight
nohup run.

## Carried constraints (standing)

- Human merges every PR; ask before push/PR.
- Measure-then-pin: no pinned constant that wasn't first printed and
  hand-checked (the stage-1 seed constants were printed and hand-checked
  in the slice-3 handoff).
- Op vocabulary strings are the engine's own
  (`reverse:`/`outside:`/...); crimp extends via composition, never
  ad-hoc strings.
- crimp theta=90 silently MIS-TARGETS — guarded in `crimp_ops`; sweep
  grids designed around it (75/105).
- NO new MCP tools, agent, prompt, or UI work — probes + harness modules
  only.
- SDD ledger at `.superpowers/sdd/progress.md`; review packages via
  `git diff BASE..HEAD > .superpowers/sdd/review-BASE..HEAD.diff`.

## Out of scope (explicitly deferred)

- Crimp (or any extended op) on front/head groups — the measured slice-5
  entry point if stage 3 shows they become the bottleneck.
- sink / reverse_deep in the search; joint (simultaneous) optimization.
- Refactoring `server.py`'s crimp composition onto `shaping.crimp_ops`.
- Any agent/MCP wiring of the pose-fit loop; chamfer-vs-mesh with
  registration; new base families.
