# Stage 2 (lint split + audit-aware ladder) — session handoff, 2026-07-24

**Charter:** roadmap §Stage 2 (`2026-07-18-cp-root-cause-and-specificity-roadmap.md`) —
"measured trees compile as soundly as templates". Work items 2.0 (audit CLI),
2.1 (lint verdict split), 2.2 (consume the nudge signal), 2.3-mission (capture
the ladder outcome = roadmap 2.4's prereq) all shipped. Branch
`claude/stage2-cp-specificity-lint-35830c`, 14 commits (8 feature + 1 fixture
note + 5 post-review fixes, see §Post-review hardening). CI is down until end
of July — the gate was `make test` locally (green; see §Verification).

## The empirical discovery that reshaped the design

The mission's proposed classifier — "violation within tol of the leaf-hull
B-edge boundary = benign" — is **FALSIFIED** (probe_stage2_lint_coords.py,
live JVM): recompiled star-5's two benign violations sit at INTERIOR vertices
0.24–0.38 paper units from any B edge, while one REAL dog violation sits
2.4e-3 from one. The actual mechanism of the FAIL-LINT baseline class:

- **Oriedita's internal angle tolerance is ~1e-6 degrees.** star-5's flagged
  vertices carry Kawasaki residuals of ±2.6e-6° (cat-spine4: 1.9e-6..8e-6°) —
  pure floating-point noise; it flags exactly the largest-residual vertices
  and ignores their mirror twins at 5.4e-7°. First-principles audit says the
  patterns are flat-foldable, period (closure ~1e-8, parity perfect).
- **Oriedita's rule labels are unreliable.** It reports ANGLES at vertices
  whose true defect is Maekawa parity (|M−V| ∈ {0,4}) and MAEKAWA at |M−V|=0
  vertices. The "(N M/V-fixable, M geometry)" header split — which the old
  prompt pattern-matched — cannot classify anything.
- The **settled classifier** (validated on star-5 2/2 benign, cat-spine4 4/4
  benign, dog 7 real + 5 noise == cp_audit's independent set): inverse
  canvas→paper transform, snap to the normalized-fold vertex (observed snap
  ≤1.5e-6; tol 1e-3), then LOCAL first-principles re-audit — B-edge/segment
  boundary ⇒ benign-boundary; parity OK + residual ≤1e-3° ⇒ benign-noise;
  else real; unsnappable/ambiguous-with-defect ⇒ real (fail-safe).
- `tests/goldens/bear-base.fold` is a **squared display frame** (square
  corners, perimeter B edges, 34 F edges) — lint on it is out of the
  provenance contract; it is NOT a verdict fixture. The MIXED benchmark is
  the committed `goldens/hf-dog-nudged.fold` (the pre-2.2 first-pack dog).

## What shipped (per commit)

1. `bd42870` **2.0 cp_audit.py** — pure-Python closure + per-interior-vertex
   Maekawa/Kawasaki; interior = no incident B edge (pinned); tol 1e-3° sits
   3 orders above clean noise, >1 below the defect class. Probes:
   `probe_stage2_audit.py` (template-vs-mesh battery), `probe_stage2_lint_coords.py`
   (transform validation + classifier falsification evidence).
2. `6301243` **2.3-mission capture** — `perturb_pack` + `perturb` dict carry
   the FINAL ladder outcome; failure_mode still classifies attempt-0 (corpus
   semantics); the real-compile e2e asserts ROW CONTENT vs the fold's own
   annotation (the 94ff943 lesson).
3. `a91cb0d` **2.1 lint_verdict.py + linter_server wiring** — grammar:
   `Flat-foldability FAILED [BENIGN|REAL|MIXED|UNCLASSIFIED]` first line
   (byte-"Pass" and all baselines untouched BY CONSTRUCTION — bless dry-run
   diff EMPTY), per-violation `Vertex paper(x, y) [canvas (X, Y)] [tag]`
   lines with re-audit facts, machine `DETAIL:` JSON (vertex indices into the
   submitted fold = the 2.3-solver input), `Classification:` trailer.
   `parse_verdict()` is the one sanctioned parser. Live-JVM tests pin the
   canvas transform (squashed-bbox H-both-axes tripwire) and the adversarial
   property (deliberate interior defect can never read benign).
4. `208a896` **2.1 prompt** — frontier detection = trust the label; dual-side
   token pins (prompt ↔ renderer) so grammar drift reddens both.
5. `24f5718` **2.2 server** — `_search_first_clean` shared policy: first
   clean pack wins (silently), dirty packs best-tracked
   (violations, closure-bad-edges, closure-error; earliest on ties), extra
   budget `IDE_LADDER_EXTRA_TRIES`=6 after the first pack, kill switch
   `IDE_LADDER_AUDIT`=0, worker soft deadline 0.6×`_COMPILE_TIMEOUT`;
   dirty-exhaustion serves best + `[ide: cp-audit: ...]` marker
   (`CP_AUDIT_MARKER`, exported). UNAUDITABLE packs take the exact legacy
   path (zero-churn rule: stub call-count pins + goldens byte-stable).
6. `9c33f4c` **2.2 bridge** — `[CP AUDIT]` synthetic-message repair turn at
   end of user-prompt turns, keyed ONLY on the marker; matching classified
   lint verdict = optional enrichment ([real] lines quoted, ≤10);
   `IDE_CP_REPAIR_RETRIES`=1 (0 = inform-only); all three strain-oracle
   guards + a fix for a latent breach (shaped fold during a CP repair turn
   no longer refills the strain budget).
7. `e41c434` **2.2 prompt** — the DEAD `ide_perturbation` clause (only
   occurrence in the repo was the prompt itself) replaced with frame_title
   provenance; `[CP AUDIT]` declared backend-origin; repair recompile exempt
   from the 3-compile HARD LIMIT, capped at one per message.
8. `dbb8090`-ish **fixture provenance note** (pre-2.2 first-pack fold).

## Live acceptance evidence (2026-07-24, cached meshes, pinned seeds)

| tree | pre-2.2 served pack | post-2.2 served pack |
|---|---|---|
| hf dog (36f4aec6, v64/p0.6) | 7 interior Maekawa (incl. M=1/V=5), silent | **5 interior Maekawa** (best of 3 packed rungs, tries=11) + cp-audit marker |
| hf deer (62501429, v96/p0.4) | clean nudge (was already sound) | unchanged, no marker |
| hf crane (ca8680d8, v96/p0.2) | 2 interior Kawasaki 0.107°, closure 2.7e-4, silent | same pack (**no better rung exists in the ±10% ladder** — bounded honest negative) + cp-audit marker |

- Template quadruped: closure 2.266e-09, 0 interior violations — the "as
  soundly as templates" yardstick.
- Lint on the improved dog: `[MIXED] ... 5 real-interior`, [real] vertex set
  == cp_audit's independent set; star-5 recompile: `[BENIGN]`, all
  [benign-noise], trailer `ACCEPT.` — DIFFERENT verdicts from the SAME
  linter, both in paper coordinates (the 2.1 acceptance criterion).
- Captured row for the dog compile (live, content-checked):
  `perturb_pack=true, perturb={packed, tries:11, asymmetric:false,
  audit:{clean:false, maekawa:5, kawasaki:0, closure_*, packs_seen:3,
  dirty_packs_skipped:2, exhausted:true}}` (the 2.3 acceptance criterion).
- The repair loop's cap discipline is TESTED, not vibes:
  `web/tests/test_server_cp_oracle.py` (11 tests incl. exact turn counts).

## Post-review hardening (same session, after the multi-agent review)

The adversarial review surfaced 14 findings; a 22-agent verification panel
(two lenses per finding: code-path trace + live reproduction) adjudicated
them — 3 refuted, 1 prompt-math error, 8 code defects CONFIRMED with repros.
All confirmed items are fixed on this branch:

- `e9313ad` **prompt parity inversion** — the [real]-remedy sentence had the
  Maekawa classes backwards ("|M-V| of 1 or 3 may be repairable by flipping").
  One M/V flip moves M−V by EXACTLY ±2: odd |M−V| is NEVER relabel-fixable;
  even (0/4) is flip-reachable *in isolation only* (flips couple both endpoint
  vertices — the roadmap-2.3 solver's domain; single flips do NOT repair the
  dog, live-confirmed). Remedy guidance unchanged (micro-adjust + recompile);
  new pin test on the corrected arithmetic.
- `63a1727` **ladder** — (a) the worker's soft deadline truncated the climb
  to a FIRST pack at 36s (legacy climbed under the parent's full 60s kill;
  the kill switch didn't remove it) — deadline now bounds only the extra
  search; (b) a facet SIGSEGV / wedged rung during the extra search lost the
  held dirty pack — the worker now CHECKPOINTS each improving best onto the
  result queue and `_run_isolated` serves the last checkpoint on crash or
  timeout; (c) an unauditable LATER rung short-circuited over an audited
  dirty best, marker-less — the legacy short-circuit now covers the first
  pack only.
- `a8e2764` **the serious one: LITTLE_BIG_LITTLE false-BENIGN** — Oriedita
  flags big-little-big (M/V ARRANGEMENT) defects at vertices whose parity
  and Kawasaki residual are both clean; the re-audit checked only those two
  necessary conditions and blessed a genuinely unfoldable pattern
  [BENIGN]…ACCEPT (live JVM repro — the one pinned-forbidden fail
  direction). benign-noise now also requires `_mv_arrangement_ok` (greedy
  crimp reduction; conservative on ties — stuck reads real). All benign
  fixtures still reduce cleanly: zero reclassification churn. ⚠ KNOWN
  LIMITATION: `cp_audit.audit_fold`'s "clean" remains necessary-conditions
  ONLY (no arrangement check), so the ladder could in principle prefer a
  BLB-broken pack as "clean" — the classified lint verdict now catches it
  downstream; folding the arrangement check into cp_audit belongs with the
  roadmap-2.3 M/V solver work (it changes ladder/capture/probe pins).
- `18892b1` **web oracle** — (a) repair fired after ERRORED agent turns
  (error swallowed into an `__error__` frame), spending the budget against a
  failing backend — an errored turn now leaves the dirty flag standing and
  the repair fires after the next healthy user turn; (b) inform-only /
  exhausted-budget firings kept the imperative "Repair now… exempt" tail
  standing in LLM context, which the next user turn would obey un-capped —
  they now carry an explicit INFORM-ONLY stand-down; (c) a malformed
  `IDE_CP_REPAIR_RETRIES` crashed the whole websocket via bare `int()` —
  `_env_int` degrades to default (also applied to `IDE_ORACLE_RETRIES`, the
  pre-existing twin).
- `27ea043` **probe** — parses both verdict grammars (it matched only the
  retired one) and reads the committed dog golden instead of the wiped
  /tmp path; live output reproduces the acceptance table.

Refuted (not bugs; documented so nobody re-flags them): the drafting-phase
"TRUST the measured metrics" guardrail does not conflict with the [CP AUDIT]
micro-adjust (purpose-scoped to *pre-compile packing*, and the repair follows
a SUCCEEDED compile); NaN-coordinate folds cannot reach `classify()` through
the committed path (Jackson rejects the JSON at the JVM boundary first) —
the NaN residual guard was added anyway as defensive hardening since the
fail-direction contract is structural.

## Verification (CI down — local `make test` IS the gate)

- `make test` (final tree, post-hardening): **1427 passed, 10 skipped,
  3 failed — all 3 pre-existing.** One session-authored flake was found and
  fixed along the way: the checkpoint-timeout rescue test raced the spawn
  child's cold start under full-suite load with a 1s window (now 6s; the
  timeout path is still the one exercised).
  The failures (`test_rigid_compiler.py::test_representative_full_artifact_
  hash_vector_is_frozen`, `test_rigid_miura_compiler.py::…hash_vector…`,
  `test_rigid_phase3_oracle_fixture.py::…byte_identically`) are hash-frozen
  artifact tests in the Codex rigid-origami subsystem, which this branch
  never touches; **proven pre-existing** by running them at pristine base
  78b2be0 in a detached worktree with the same venv — identical 3 failures.
  Likely env-dependent float-repr drift in the shared .venv; belongs to the
  rigid-origami line, not Stage 2.
- Mid-session, `origin/main` moved to 688b78b (PR #48, rigid-origami phase
  4). Zero file overlap with this branch (`comm` of both name-only diffs is
  empty) — merges cleanly without rebase; PR #48 does not touch the three
  failing tests either.
- Adversarial review: 5-dimension multi-agent review of the full diff
  (classifier math, ladder policy, web state machine, prompt string
  integrity, cross-consumer grep), then a 22-agent verification panel with
  2 lenses per finding (code-path trace + live repro). Outcome: 14 findings
  → 3 refuted, 9 confirmed, ALL fixed on-branch (§Post-review hardening).
  `make test` re-run green after the fixes (same 3 pre-existing rigid-line
  failures only).
- Bless dry-run after 2.1: baseline_verdicts.json + goldens byte-identical
  (the zero-churn acceptance evidence).

## Gotchas discovered/confirmed this session

- **/tmp gets wiped between sessions** — battery artifacts now live in the
  session scratchpad; the committed `goldens/hf-dog-nudged.fold` is the
  durable fixture.
- Recompiles of the cached trees are deterministic across sessions (audit
  numbers byte-identical), but the SERVED pack changed at 2.2 by design
  (ladder now searches past dirty rungs) — anything diffing served folds
  across the 2.2 boundary sees rung 11, not rung 5, for the dog.
- The verdict body text changed (paper coords, tags, DETAIL) — a telemetry
  discontinuity for anything diffing raw verdict strings. First lines still
  start `Flat-foldability FAILED` (runner/baselines unaffected).
- Apple-Silicon JVM cold start is ~100ms — the live-JVM classification tests
  cost less than a second total; no slow-marking needed.
- `_worker_compile_and_regions`'s audit search runs in the spawn child with
  cp_audit only (no MCP, no capture) — the in-child constraint held.

## Next (per roadmap sequencing)

- **Roadmap 2.3 (M/V repair solver):** coupled parity reassignment consuming
  the `DETAIL:` payload. Parity math (review-corrected in the prompt): one
  flip moves a vertex's M−V by exactly ±2, so |M−V| ∈ {0,4} IS one flip from
  parity in isolation — but each crease couples two vertices, and single
  flips do NOT repair the dog (live-confirmed): the solver must reassign
  jointly. Odd |M−V| is never relabel-fixable. The solver should also own
  folding `_mv_arrangement_ok` (big-little-big) into cp_audit's "clean"
  (see the known limitation above). The dog's residual 5-defect base is the
  test subject; a solver win would close the gap the ladder search cannot.
- **Roadmap 2.4 (retrain):** capture is accumulating rich rows now; still
  needs the merge-with-id-assignment script before any corpus merge
  (`dataset.existing_ids` KeyErrors on id-less rows).
- **Live smoke of the [CP AUDIT] loop through the real serve surface** (Groq
  llama-4-scout; `IDE_CP_REPAIR_RETRIES=1`) — the bridge is fully tested
  against a stubbed agent_turn, but the agent's actual micro-adjust behavior
  on a real [CP AUDIT] message is unproven (session ended at the local-test
  gate; CI down).
