# Handoff: molecule-mobility (M / K2 / H) — outcome

**Dates:** 2026-07-14 → 2026-07-17 · **Branch:** `feat/molecule-mobility`
(from main `32afbd4`) · **PR:** (opened at slice end)
**Spec:** `docs/superpowers/specs/2026-07-14-molecule-mobility-design.md`
(amended twice in-flight, both user-adjudicated: registry → file-backed;
stage-2 → κ machinery) · **Plan:**
`docs/superpowers/plans/2026-07-14-molecule-mobility.md`
**Probe/search outputs (uncommitted, regenerable):**
`probe_kick_alignment.out.json`, `probe_tip_mobility_calibration.out.json`,
`mobility_search.out.jsonl` (+ run logs), regenerated preflight artifacts.

**Read ledger: 0 of 90 sim reads spent.** Every lane resolved sim-free —
the third consecutive slice in which the pre-gates did their job (150→0,
now 90→0).

## 1. Session verdict (three lanes, all honest endings)

- **Lane M — the headline. M1 LANDED (ending a): the lock is EXPLAINED and
  the explanation is a theorem plus a measured counting fact.** "Theorem Z"
  (flat-state cokernel): at any flat state, J's z-rows vanish identically and
  BCH parity makes every even-order residual purely z-directional — so ANY
  nonzero quadratic obstruction lies wholly in the cokernel. **rel = 1.0 is
  forced for every flat pattern**; the T-search's uniform 12/12 was
  over-determined, and the old "partial 0.336" degree-4 contrast was a
  misread (its rel is also exactly 1.0). Second-order extension ⟺ the
  per-vertex flex-polygon signed areas κ_v(w) all vanish. Single universal
  molecules are underdetermined (kernel dims 4–8 vs 1–3 area forms — zero
  cones real, continuation-foldable to the 0.5 rad cap); the compiled+squared
  dog network collapses the kernel to dim 3 with 8 active forms, two rank-1
  sign-definite (v4, v10) ⇒ min over the unit kernel sphere ‖κ‖ =
  **0.0225875 > 0** ⇒ the ENTIRE flex space is locked, not just w\*.
  Predict-then-measure protocol held (ledger-first; one rung-1 misprediction
  root-caused to 6-decimal witness truncation, revised account then held
  unrevised through rungs 2–3 + 29/29 out-of-sample dog checks).
- **Lane M2 — remedies: ZERO EXTENDING-grade passers → the named
  instrument-vs-construction boundary ending. But the funnel measured a
  GRADIENT:** all six single augmentation moves keep huge front-selectivity
  (r\*_q 14.6–15.4) and four of six SOFTEN the lock — `hub_cone_break@v5`
  0.0225875 → 0.00315 (7.2×), `@v11` → 0.00291 (7.8×), `restore_fourth@v4`
  → 0.00731, `hinge_split@v10` → 0.00912 — while the two whose split landed
  on an F edge are exactly inert. Hubsplit trees either fail the packing
  knife-edge (e=0.2 pair) or LOSE front-selectivity (r\*_q 0.85/0.80 — the
  split hub redistributes tip motion). Single moves soften; none breaks.
- **Lane K2 — FALSIFIED at K2.0, kick build stopped (0 reads).** The strict
  sign gate failed 4/5 pairs — and informatively: the back_v12 parked cells
  align POSITIVELY (+0.081…+0.092) while their scored mirror twins align
  negatively — the alignment sign tracks the site's MIRROR PARITY, not park
  status; and the decisive frontpair θ-pair reads 0.1165 vs 0.1182 (same
  sign, near-identical) — kick·target-branch direction cannot explain
  θ-dependent parking. Parking remains solver-dynamics beyond first-order
  geometry.
- **Lane H — SHIPS.** `fold_registry` (content-addressed, file-backed) +
  handle wiring in both MCP servers + the agent_loop history seam + the
  spawn-env pin (4 commits, each reviewed). Live demo: **the original
  blob-echo blocker is dead** — scout passed `fold_handle` on its FIRST lint
  call; `suggest_pose_stack` accepted the handle, resolved the node, and the
  posed dog RENDERED in the Model tab. The oracle loop closed live on its
  REJECT branch; the clean PASS transcript was blocked by two pre-existing
  platform defects (below), not by handle code.

## 2. Gate-by-gate record

**Preflight (PASS after one amendment):** all four regenerations matched
pins exactly — but only after copying `feasibility/gate.joblib` (+ corpus
JSONLs), which the standing env-copy list OMITS (first coarse run read
117/0/15/12; with the gate artifact: 108/12/12/12, completed rel 1.0).
**ENV-COPY LIST MUST ADD: `mcp_harness/feasibility/gate.joblib`,
`corpus.jsonl`, `corpus_smoke.jsonl`.**

**K2.0 (strict sign rule, tie_tol 1e-9, θ-pair gating, pinned before
measuring):** FALSIFIED — back pairs sign-anti-separated, θ-pair tied.
Exit 1; alignment table in the ledger and out.json.

**M1 gate:** predictions verified on rungs 1–2 (distinct topologies), rung 3
+ dog out-of-sample as further confirmation. Note committed
(`docs/superpowers/2026-07-14-molecule-obstruction-mechanism.md`) with 37
prediction-pinning tests.

**tip_mobility calibration gate: PASS 13/13** verdict agreement (5 finite
pairs, e.g. dog D1 1.76272 → r\*_q 15.3957; 8 inf→inf) + readability on the
previously-refused geometries (flap dof 7, headmid dof 9 — both read,
unbounded). r\*_q ≥ 1.0 went live as stage-1.

**Stage-2 re-pin (user-adjudicated, spec commit `e38ba46`):** Theorem Z makes
rel-based EXTENDING unsatisfiable on flat patterns → re-pinned to
(i) min ‖κ‖ < 1e-6, (ii) zero-cone direction front-selective ≥ 1.0,
(iii) continuation ≥ 0.3 rad; calibration-first (≥2 ladder witnesses PASS —
measured κ≈0, continuation 0.52/0.51 — AND dog FAILS in-band 0.02258753).
Calibration passed; the funnel ran; zero passers (§1).

**H gates:** suites green at every commit (final counts §6); backward-compat
byte-pins on `fold_json_string` paths; provenance pins (handle never in the
FOLD dict) tested both directions; live demo evidence per §1/§3.

## 3. Measured findings beyond the gates

1. **Theorem Z reframes the instrument forever:** rel is not a verdict
   channel on flat patterns — EXTENDING reads only via the q-norm floor /
   κ machinery. The old EXTENDING/NON_EXTENDING rel semantics remain valid
   only off-flat. (`flex_extension` gained additive observables:
   `flat_area_forms`, `defect_z_split`, `cokernel_basis`.)
2. **The lock is single-move-softenable but not single-move-breakable**, and
   the κ-descent ordering (hub-cone breaks ≫ restore-fourth > hinge-split >
   F-edge-landed ≈ 0) is a measured gradient pointing at composed moves.
3. **Mirror parity governs kick alignment** (K2.0): twin sites flip alignment
   sign; θ barely moves it (0.1165 vs 0.1182 at identical geometry).
4. **Two-process env sanitization is a real deployment hazard:** the MCP
   stdio client's env safelist (no TMPDIR) forked the registry store dir
   between parent and linter child — caught ONLY by the live demo; fixed by
   pinning `IDE_FOLD_REGISTRY_DIR` into child spawn env with a red-first
   cross-process regression test.
5. **Two platform defects found live (chips spawned):** (h-f1) Model-tab
   extraction races tab visibility → sticky `'array'` REJECT verdict
   (task_1596504e); (h-f2) agent turns hang without a Groq client timeout,
   wedging the ws loop and any queued oracle verdicts (task_87e72a92). Also:
   scout's string-vs-array tool-arg hiccup did NOT self-recover once a 400
   `failed_generation` blob entered history.
6. **suggest_pose_stack declines honestly on 3-hub fresh compiles** ("expected
   2 hubs, found 3") — the two-hub naming boundary now has a live product
   sighting; `tip_mobility`'s quotient design is the template for
   generalizing it.

## 4. Routing verdict (a follow-up named for EVERY outcome)

1. **Composed-move κ-descent search (M2 boundary routing — the headline
   follow-up):** single moves leave min ‖κ‖ at 0.003; compose 2–3 moves
   (hub-cone pair first), treat min-κ as the descent objective over the
   move lattice, gate exactly as this slice pinned (κ < 1e-6 +
   front-selective zero cone + continuation). All machinery ships in
   `crease_augment` + `mobility_search`; only the composer is new.
2. **Off-flat serve states (note §4 family 3):** Theorem Z is flat-state-
   only — pose work targeting finitely folded states escapes the cokernel
   trap entirely; connects to the existing shaping/pose stack.
3. **Solver-dynamics instrumentation (K2 routing):** two falsified
   first-order hypotheses (projection K.0, target-sign K2.0) now bound the
   space — parking needs solver-trajectory observables, not flat-state
   geometry.
4. **H platform follow-ups:** the two spawned chips (h-f1, h-f2); after
   both land, re-run the demo for the clean PASS transcript (all handle
   machinery already proven).
5. **Explicitly NOT routed:** more single-move augmentation breadth (the
   gradient is measured; composition is the question); more hubsplit
   instances (selectivity loss is structural); non-square paper (the note
   never implicated the boundary); tree-space search of any kind
   (Theorem Z + T-refuse close it).

## 5. Deferred minors (final-review triage input)

(t1) alignment_record double null_space_basis + unasserted crease-order
invariant; anchor-test loop not parametrized; ±1 fp tolerance nit.
(t5) dead `_TOL` constant; gusset_quad trapezoid-domain not in docstring.
(t6) dead loop test_flex_extension.py:438-440; §4 families 2–3 metrics
qualitative; stochastic witness reproducibility rests on seeds+tolerance.
(t7) tmp-file leak on write failure; `""` handle treated as absent
(undocumented); no unicode/empty-dict tests; mtime-tie eviction theoretical.
(t8) handle-wins branch duplicated across accept tools; per-result registry
write cost; some tests touch the real default registry dir (hygiene); dead
TMPDIR pops in the sanitized-env test.
(t10) probe's redundant folding_dof solve; calibration gate one-sided by
data construction.
(t12) "append-only" docstring loose (split edge necessarily rewritten —
vertex indices ARE stable); shallow-shared non-geometry keys; theoretical
StopIteration.
(t13) stage-2 (ii)/(iii) + calibration monkeypatch-only in-suite (verified
live by reviewer + Task-14 run); unregistered pytest.mark.slow; tautological
status-set test; refused/analysis_error asymmetry on stage-2 instrument
faults.

## 6. Suite state

Backend grew 741/4 → **890 passed / 4 skipped** at Task 12 (last full
nohup run before slice end; final-commit counts recorded in the PR body
from `/tmp/suite_final_mm.log`). Web vitest **59 passed** throughout
(+ web/tests Python 40 where run). Probe outputs and `.superpowers/sdd/*`
stay uncommitted per house rules. New committed modules this slice:
`probe_kick_alignment.py`, `molecule_fixtures.py`,
`test_molecule_mechanism.py` (+ the mechanism note), `fold_registry.py`,
handle wiring in `server.py`/`linter_server.py`/`agent_loop.py`,
`tip_mobility.py` + calibration probe, `crease_augment.py`,
`mobility_search.py`, and their test files.
