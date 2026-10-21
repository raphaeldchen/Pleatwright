# Flat-equilibrium root cause (Pillar B capstone) — design

**STATUS (2026-07-11): COMPLETE** — root cause measured (exact ±z force
cancellation at the flat bifurcation; SOLVER-PARKED), fix shipped at the
bridge (deterministic 2e-4 z-lift; served dog folds 1.5910, quad 0.8057),
regression + tripwire landed (454/4), Gate-3 payoff measured (first
fox-target comparison on a compiled base; global-coupling finding).
⚠ shipped amplitude is marginal (transient parks measured) — see handoff
docs/superpowers/2026-07-11-handoff-flat-equilibrium-outcome.md.

**Date:** 2026-07-10
**Branch:** `feat/flat-eq-root-cause` off main `9bf8111` (PR #34 merge verified on origin/main before branching).
**Predecessors:** docs/superpowers/2026-07-09-handoff-b5-slice4-outcome.md (B5 capped, names this as the next effort), docs/superpowers/2026-07-03-probe-folded-state-findings.md (closure + sim measurements reused below), mcp_harness/probe_deep_sim_smoke.py docstring (the exactly-0.0 measurement, 2026-07-06).
**Slice kind:** diagnosis-to-fix (systematic-debugging discipline inside the SDD frame), deliberately larger than the single-gate B5 slices.

## 1. Problem

TreeMaker-compiled realistic bases never fold in the vendored Origami
Simulator: driven to `setFold(100)` they sit at the flat state — the squared
dog and squared quad measured **maxDisplacement exactly 0.0** (2026-07-06,
probe_deep_sim_smoke). Lore since the reverse-fold slices ("docs/dog.fold
never folds in sim"). This blocks:

- the Step-5 product promise (the viewport "physically animates the paper
  collapsing into the 3D base") for every realistic compiled model, and
- any future pose-fit on a real base (B5 was capped as a research negative
  partly because the star toy's reachability wall may not exist on a real
  base with anatomically oriented flaps).

**The question:** why do compiled bases sit flat, and can the compiled dog
base be made to fold?

## 2. Decisions pinned with the user

- **Success bar:** the **served display fold** of the dog — the exact
  `web/server.py` display path, `apply_display_ops(complete_square(raw),
  [], raw=raw)` — folds in the sim: maxDisplacement > 0.1 (the anti-vacuous
  gate), 0 NaN. Raw-dog behavior is measured as diagnosis, not as the bar.
- **Fix reach:** bridge (`web/frontend/*/simulator/js/ide-bridge.js`, the
  one file we author inside the vendored app) + data layer
  (`square_complete.py`, `web/server.py`, harness preprocessing) ONLY.
  Vendored simulator JS stays pristine. If diagnosis proves only a
  vendored-core change can work, the slice **HALTs with the measured
  verdict** — a successful honest outcome, per the standing rule.
- **Stale-lore rule:** if Gate 0 shows the dog folds under the current
  scripted protocol, document it and re-scope on the spot.

## 3. Evidence already on file (do not re-derive)

All bases TreeMaker-compiled. "Closure" = reflection-composition
cycle-closure error, paper units (probe_folded_state findings, 2026-07-03).
"Hubs" = vertices with M/V degree >= 4 (measured this session).

| base | interior flat-consistent? | hubs | real F-frame after squaring? | sim result |
|---|---|---|---|---|
| star-4 golden | yes (closure 3e-16..9e-10) | 1 (deg 8) | no-op (hull fills square) | **folds** (disp 1.3109) |
| winner star b=0.95 h=0.40 | yes | 1 | **yes** ("stage-2": squaring adds geometry) | **folds** (slice-3 sim rescue) |
| bear-base asset | **no** (Kawasaki lints; closure 1.20, 15/42 bad edges) | 3 (deg 6) + 12 (deg 4) | yes (asset ships squared, 4 corners, 34 F) | **moves** (never converges; non-planar; still 0.24/40s at 60s) |
| dog | yes raw (closure <=9e-10); squared closure 0.83, 12 bad | 2 (deg 6) | yes | squared: **exactly 0.0**; raw: **never sim-tested** |
| quad golden | yes raw; squared closure 0.72, 1 bad | 2 (deg 4) | yes | squared: **exactly 0.0**; raw: never sim-tested |
| hshape golden | yes raw; squared closure 0.59, 2 bad | 2 | yes | never sim-tested |

**Open puzzle for Gate 0 to reconcile:** tracer-era Model-tab screenshots
(docs/b2-dog-head-bent-model-tab.png, docs/b3-dog-crimp-model-tab.png,
2026-07-02) show a visibly bent dog — shaped-crease motion coexisting with
the "dog never folds" lore. Gate 0's per-crease achieved-angle profile is
the instrument that resolves this (e.g. "shaped creases actuate, base
creases don't" would be a mechanism clue, and would make the lore
imprecise rather than wrong).

Geometry stats (measured this session): dog V=35 E=62 (M13/V25/F4/B20),
min edge 7.94e-3, six edges < 0.01, **min vertex-pair distance 7.94e-3 (no
near-duplicate slivers)**, min face area 1.91e-3 (from docs/dog_sim.fold,
which is exactly the ide-bridge preprocessing materialized — not squared).
Bear V=48 E=92 (F34/M20/V32/B6), min edge 5.63e-3, seven edges < 0.01 —
**more tiny edges than the dog, and it moves.**

### Suspect triage after this evidence

1. ~1e-9 `_key`-dedup sliver faces — **near-dead** for the unshaped dog (no
   vertex pair closer than 7.9e-3; that sliver is a shaping_deep output
   artifact). Survives only as the broader "face quality breaks the
   importer" mechanism (B below).
2. Missing/incomplete M/V — **dead**: assignments complete (no "U"),
   ide-bridge synthesizes edges_foldAngle (M→−180, V→+180, F/B→0) and
   faces on load; docs/dog_sim.fold proves the synthesis output is sane.
3. Symmetric flat state needing a kick — **alive** (mechanism class D).
4. Squaring's flat-F corner faces — **weakened but alive, refined**: the
   winner base has a real F-frame and folds, so a frame alone does not pin.
   Surviving form: *multi-hub + flat-consistent interior + frame* freezes
   (dog, quad) while single-hub+frame folds (winner) and
   multi-hub+INconsistent+frame moves (bear — its Kawasaki violations make
   flat unsatisfiable, so residual stress kicks it off the flat state).
5. Knife-edge packing geometry — **alive** as a face-level actuation
   mechanism (thin faces / earcut, class B), not as a vertex-dedup issue.

### New prime suspects from reading the vendored sim (this session)

"Exactly 0.0" is the signature of *silent non-actuation*, not smooth
physics: a mass-spring solver holding signed ±180° targets at a flat state
has nonzero initial crease torque, so something never engaged. Two code
facts make silence possible:

- **`loadFold` has no acknowledgment** (ide-bridge.js): an import-time
  exception posts `{type:'error'}` that no current caller listens for; the
  page keeps whatever model it had, positions frozen. `sim_capture.capture`
  never checks that the loaded model matches the input fold.
- **`pattern.js getFacesAndVerticesForEdges` silently drops any M/V/F edge**
  that doesn't find exactly 2 adjacent triangles after `triangulatePolys`
  (quads split manually; 5-gons+ go through earcut with **no result
  validation on the 2D path**). Dropped hinge = no actuation, no warning.
  `model.buildModel` accepts an empty/partial crease list without complaint.

## 4. Gate 0 — instrumented reproduction (the mechanism classifier)

New instrumented capture support in the harness (`mcp_harness/`), all
Playwright-side — **no bridge or vendored edits required for diagnosis**:

1. **Error channel:** install an in-page `window.addEventListener` for the
   bridge's `{type:'error'}` messages *before* posting `loadFold`; record
   into a page-global the probe reads back.
2. **Console harvest:** Playwright `page.on("console")` — pattern.js warns
   on redundant vertices, missing edges/faces, incompatible angles; all
   currently invisible to probes.
3. **Load verification:** captured vertex count must equal the input fold's
   vertex count (stale-model trap). Existing `tracked_points` does this;
   the instrumented path makes it unconditional.
4. **Crease-build audit:** on a fresh page load, call
   `globals.pattern.setFoldData(fold, true, true)` — the
   `returnCreaseParams` path computes crease params WITHOUT building the
   model — and diff creased edge indices against the input's M/V (and F)
   edges → explicit **dropped-crease list** + per-crease target angles.
   Then reload the page for the physics capture (the audit half-initializes
   pattern state; a fresh `goto` isolates it — captures already goto fresh).
5. **Displacement time-series:** read `getFoldedGeometry` at ~1s / 5s / 20s
   (read-only) — separates "never moved at all" from "moved then relaxed
   back to flat".
6. **Offline per-crease achieved angles:** from the captured triangulated
   faces + index alignment, compute each input M/V edge's dihedral vs its
   ±180 target (numpy, post-processing — no sim internals).
7. **Offline face-quality stats:** min face area, aspect, sub-0.01 chords
   per fixture (extends what this session measured).

**Fixture set (identical protocol, one SimSession) — the full matrix, not
a sample; every "never sim-tested" cell in the §3 table gets closed in one
run:** dog-served (squared, the success-bar artifact), dog-raw
(docs/dog.fold — the most informative unrun experiment), quad-squared,
quad-raw, hshape-squared, hshape-raw (the raw variants of the other
multi-hub bases discriminate "freezing requires the frame" from
"multi-hub freezes even raw"), star-4 (clean folding control), bear-base
asset (inconsistent mover control), winner-star (folding control WITH a
real frame; built via `starhead.winner_base()`). ~9 captures plus audits
in one session (~40s each) — run them all; do not sample.

The crease-build audit, achieved-angle profile, and console harvest are
reported for **every** fixture, movers included: a mover baseline for
crease drop-rate and angle deficit is what makes a nonzero reading on the
frozen bases interpretable.

**Classification rule per frozen base** (decision order):

- load error posted / vertex-count mismatch → **IMPORT-DEAD** (console
  warnings are recorded as evidence for every class, never as the
  classifier themselves)
- any input M/V edge missing from the built crease list → **ACTUATION-DEAD**
  (with the dropped-crease list and their owning faces)
- creases complete but no time-series sample shows motion above the noise
  floor → **SOLVER-PARKED**
- motion at early samples, final disp < 0.1 → **PHYSICS-PINNED**
- final disp ≥ 0.1 → **FOLDS** (stale lore for that base → re-scope)

The motion noise floor is **measured on the star-4 control in the same
session** (measure-then-pin), not invented; the pinned value goes in the
probe output and the handoff.

**Gate-0 exit:** every fixture classified; dog-served and quad classified
identically or the difference explained; verdict names the mechanism class
that Gate 1 will bisect. Deliverable: probe + `.out.json`/`.out.log`
(uncommitted) + written verdict in the ledger.

## 5. Gate 1 — mechanism-guided fold-file bisection

Mutations are pure-python transforms of the fold dict, applied one suspect
at a time; each is a measured probe with a written verdict. Menu by class:

- **ACTUATION-DEAD:** locate the dropped creases' owning polygons, then
  smallest-first: (a) pre-triangulate just those polygons in the data
  layer; (b) weld/simplify sub-0.01 hull chord chains; (c) convex-split the
  large corner F-faces; (d) strip the frame entirely (raw) as the bounding
  control.
- **SOLVER-PARKED / PHYSICS-PINNED:** (a) z-jitter kick (tiny out-of-plane
  `vertices_coords` perturbation, data-layer legal); (b) fold-percent ramp
  (setFold 20 → 50 → 100 with settles — protocol-level, harness-side);
  (c) frame experiments: corner faces removed vs retained, F-chord
  stiffness proxy via subdivision; (d) single-hub excision control (fold
  only one molecule's neighborhood).
- **IMPORT-DEAD:** the now-visible error names the throwing step;
  minimal data-layer preprocess to avoid it, then re-run.

**Causality rule (both directions):** the smallest mutation that unfreezes
the dog must ALSO freeze star-4 (or the winner base) when the inverse
pathology is injected into it. Correlation without the reverse direction
does not close the gate. (If the mechanism is inherently un-injectable —
e.g. a multi-hub-only kinematic property — the reverse direction is
replaced by a second independent frozen base unfrozen by the same mutation:
quad.)

**Gate-1 exit:** a named root cause with the minimal unfreezing mutation,
its measured displacement, and the reverse-direction (or quad) evidence.

## 6. Gate 2 — the fix + regression

Land the minimal-mutation insight at the layer the root cause names:

- **data layer:** `square_complete.py` post-step (e.g. triangulated/welded
  corner output) or `web/server.py` display path, or
- **bridge layer:** `ide-bridge.js` `loadFoldObject` preprocessing (also
  the natural home for surfacing load errors if IMPORT-DEAD). A bridge
  edit must land in `web/frontend/public/simulator/js/` AND be mirrored to
  `web/frontend/dist/simulator/js/` — the copies are currently identical
  and SimSession serves `dist`.

Whatever ships must keep the download/lint `json` frame untouched — the
fix rides `display_json`/display assets only, exactly like squaring does
today. Fix hygiene regardless of layer: the capture path gains the
vertex-count parity check permanently (silent stale-model loads must never
score again).

**Regression protocol (project convention: pytest suite stays sim-free):**

1. a permanent probe asserting the **served dog folds**: disp > 0.1, 0 NaN
   (quad as a secondary, reported not gated);
2. an env-gated pytest (skipped unless `RUN_SIM_REGRESSION=1`) wrapping the
   same check for opt-in runs;
3. ordinary pure-python unit tests for any data-layer transform that ships
   (these DO run in the ~10-min suite, which must stay green: 442/3 at
   branch time).

The dog fixture is promoted from untracked `docs/dog.fold` to a committed
golden (`mcp_harness/tests/goldens/dog.fold`) so the regression is
reproducible — fixture INPUTS are committed (like the existing goldens);
probe OUTPUTS stay uncommitted.

**HALT criterion:** if every bridge/data-layer mutation class fails to
unfreeze the dog and the diagnosis shows the mechanism lives in vendored
solver/import internals, the slice ends with the measured verdict
"compiled bases can't fold without engine-level work, here's why" +
handoff. Do not soften; do not patch vendored files.

## 7. Gate 3 — payoff (informational, never blocks, skipped on HALT)

On the folded served dog: adapt the B5 measurement machinery
(`sim_capture.tracked_points`, `pose_target` grouping/`fox_targets`) to
measure real joint angles vs the fox skeleton targets for the first time on
a compiled base. The dog's leaf-to-limb mapping is heuristic (hull-tip
geometry + `head_among_unpaired` tie guard); the probe reports what it can
measure and flags ambiguities instead of guessing.

Then one **actuation datum** — the question that actually decides whether
B5 reopens is not the unshaped angles but whether a tip-local op MOVES a
joint angle on a real base (the star toy's reachability wall may not exist
on anatomically oriented flaps): apply a single reverse fold to ONE dog
leg tip (θ from the B5-proven grid, e.g. 105°; the tracer-era dog
reverse/crimp ops prove the op machinery on this base), recapture, and
report the measured joint-angle delta vs the unshaped baseline. Still no
gate, no fit, no search — one op, one delta, honestly reported (including
"op refused" or "angle unmeasurable" if that is what happens). Output:
unshaped angles + gaps vs fox targets + the single-op delta, written to
the handoff — this determines whether B5 reopens on better terms.

## 8. Error handling & cross-cutting constraints (all inherited)

- `CaptureError` discipline everywhere; anti-vacuous `DISP_GATE = 0.1` on
  every "it folded" assertion; NaN check on captures.
- Solver drift: per-capture ~1e-5–0.02°, derived quantities up to ~0.0934 —
  no 0.0 tolerances anywhere; any strict-< gate carries margin ≫ 0.1;
  measure-then-pin for every constant (noise floor, thresholds).
- SimSession is HEADED (headless WebGL dead on this machine); playwright
  lives in `mcp_harness/.venv` ONLY; long probe runs via nohup from
  subagent shells, controller polls the log.
- Probe outputs (`*.out.json` / `*.out.jsonl` / `*.out.log`) and suite logs
  stay uncommitted. SDD ledger at `.superpowers/sdd/progress.md`
  (uncommitted).
- Full backend suite green before handoff; crimp θ=90 guard untouched.
- Human merges every PR — ask before push/PR. Review packages via
  `git diff BASE..HEAD`; final whole-branch review on the most capable
  model.

## 9. Out of scope

- New MCP tools, agent-prompt changes, UI/viewer feature work (bridge
  *preprocessing* is in scope as pinned; viewer.ts/React work is not).
- Edits to vendored simulator JS (anything under `simulator/js/` except
  `ide-bridge.js`).
- Molecule-level corner creasing in TreeMaker (the recommended-against
  option 3 from the export design) and any C++ engine work.
- Reopening B5 (Gate 3 only *informs* that decision).
- Making the squared FOLD lint-clean (squaring lints are a separate,
  documented item; this slice targets folding, not linting).

## 10. Deliverables

Spec (this file) → implementation plan → Gate-0 instrumented capture +
matrix probe → Gate-1 bisection probes → Gate-2 fix + regression tests →
Gate-3 payoff probe (conditional) → outcome handoff doc + memory update →
PR (user merges).

**Execution sizing:** implementation runs on Fable 5 subagents — size task
packages at one gate (or one coherent mechanism investigation) per
package, not micro-steps; each package carries the systematic-debugging
discipline internally (hypothesis → probe → measured verdict in the
ledger). The gates are checkpoints where the controller re-plans from
measured verdicts; they are not an excuse to fragment the work below the
level a strong executor can hold.
