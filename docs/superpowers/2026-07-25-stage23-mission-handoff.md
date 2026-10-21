# Stage 2 completion mission (2.3 M/V solver + 2.4 merge) — handoff, 2026-07-25

**Charter:** roadmap §Stage 2 (`2026-07-18-cp-root-cause-and-specificity-roadmap.md`).
Branch `claude/stage23-mission-execution-1b52fb`, on top of the merged 2.1/2.2
work (PR #50). Five tasks: Phase-0 (session ledger gitignore), D (live
`[CP AUDIT]` repair-loop smoke), B (cp_audit arrangement oracle + the live
crane golden), A (2.3 coupled M/V repair solver + wiring), C (2.4 merge
machinery + the retrain decision). **Stage 2 now closes except for the 2.4
retrain, which is deferred on measured evidence — see §2.4.**

## What shipped (by commit)

| commit | what |
| --- | --- |
| `13eac0e` | gitignore the `.superpowers/` session ledger |
| `3262c0f` | golden: the ladder-served 5-defect dog base (`hf-dog-ladder-best.fold`) |
| `4a0230d` `0803f54` | live `[CP AUDIT]` repair-loop smoke — all 5 wire criteria PASS |
| `96d3b2a` `11d2f4d` `1b62f6b` | cp_audit owns the M/V-arrangement oracle ("ladder clean" is now sufficient); the crane v37 big-little-big defect pinned as a LIVE golden |
| `dc06eb1` `b6ee763` `8949f83` `9f32363` `21dc8e2` `58ea638` `88ee64a` | 2.3: `mv_repair.py`, the ladder re-solve, the `repair_mv_assignment` tool + D-contract web wiring, and three rounds of review hardening |
| `3e24a7c` | 2.4: `feasibility/merge_captured.py` + the corpus-path plumbing (this section) |
| `6afffa7` | 2.4 fix: merge refuses to write onto the base corpus (write guard) |
| `8490e9a` | 2.4 fix: strip stale ids, deviate to most-informative dedup (documented deviation), harden hostile-input handling |
| `9fb7513` | docs: mission-wide D/B/A sections, open-items-for-human, CLAUDE.md §4 drift note |
| this commit | fix(review): close final whole-branch review findings |

2.3's headline measurement: the golden hf-dog ladder-best base goes **5 → 0
interior defects at 5 flips (7, 8, 18, 57, 58) in 0.68 s**, closure
bit-identical, every Kawasaki residual unmoved. Two measured laws bound the
solver — a flip moves `D = M−V` by ±2 at BOTH endpoints and nowhere else, and
an ODD `|M−V|` is flip-INVARIANT (geometry, refused honestly rather than
attempted). Full detail is in the commit bodies, which are the primary record.

## D — the live [CP AUDIT] smoke (ran FIRST, before the solver could clean its trigger)

All 5 wire criteria PASS on the `claude-sonnet-5` verdict run; evidence frozen in
`docs/superpowers/evidence/2026-07-25-cp-audit-smoke/` (frame transcripts, served
folds, `METRICS.md`) with the reusable driver at `web/probe_cp_audit_smoke.py`.
Cost: **~$0.53 total** (haiku plumbing run ~145k in/$0.16; sonnet-5 verdict run
~174k in/$0.37; estimates — `llm_client` discards `resp.usage`; the fixed
per-step input was measured exactly via `count_tokens`: 16,579 tok/step
sonnet-5, 12,020 haiku). Outcome was the anticipated honest negative: the
one permitted length-micro-adjust recompile changed 4 of 6 edge lengths and was
DEFECT-NEUTRAL (5→5); haiku's repair made the base WORSE (5→8, a new
LITTLE_BIG_LITTLE). That live proof that lengths are the wrong lever is what
task A's M/V solver answered. Findings of record (all in METRICS.md): sonnet-5
falsely claimed "no auto-nudge note" at seq 12 (model-fidelity defect; final
still-violating report was accurate); criterion 3 is not frame-observable
(args_preview truncates — capture rows/fold handle are the authority); the
INFORM-ONLY stand-down and errored-turn deferral branches are stub-verified
only. NOTE: after task A landed, the dog serves CLEAN, so this exact smoke no
longer fires [CP AUDIT] on the dog — the driver grew a `repaired_in_ladder`
branch; a future smoke needs a subject the solver cannot fully repair.

## B — cp_audit owns the arrangement oracle

Port equivalence proven by review at 200k+ comparisons / 0 disagreements; the
conservative stuck⇒NOT-ok tie rule survived verbatim (false-FAILED-only). Churn
probe (`probe_arrangement_churn.py`): ZERO served-rung churn — dog 11→11, deer
9→9 (clean), crane 2→2, but the crane now reports its real defect: **v37 is the
first LIVE arrangement-only (big-little-big) defect**, pinned as golden
`hf-crane-ladder-blb.fold`. Schema truth that 2.4 must respect: in
`perturb['audit']` only the `arrangement` count is disjoint; maekawa and
kawasaki CAN co-flag one vertex, so the SUM is an upper bound on distinct
defective vertices, not a total. Operational: `bless.py` has NO dry-run flag —
the protocol is run-then-`git status` (empty = no re-bless owed, which is what
happened).

## A — solver facts beyond the roadmap entry

The dog full win is end-to-end live (ladder parent AND spawn-child paths):
5→0 at flips (7,8,18,57,58), JVM [MIXED]/5-real → [BENIGN]/0-real; crane
partial 3→2 at weight 3 (73,74,81); the frozen 7-defect golden clears 5-of-7
in-ladder. Honesty semantics hardened by review: a certify-phase budget stop
now reads `deadline`/`audit_cap` with `exhausted: False` (never dressed as a
proven negative); deadline-truncated serves carry a "search truncated" clause.
**The completeness guarantee is SCOPED**: full repairs are provably never
missed; PARTIAL search is complete only for candidates that keep every clean
vertex clean and fully fix every defect they touch — two real weight-2 partials
on the dog golden fall outside that rule and are deliberately pinned as
real-but-not-emitted (`test_missed_partials_document_the_emission_rules_scope`).
Known deferred items: iterative deepening to replace the ~14-48× pessimistic
`_effective_weight` degrade (cliff between n=50 and n=52; costs the nudged
golden one repair); widening the emission rule to the sound bar (measured
argmin-identical on live fixtures — safe future PR); `repair_mv_assignment`
does NOT strip a stale cp-audit marker from its INPUT (inert while tool output
is not web-extractable — `web/fold.py` find()s the FIRST marker, so this MUST
land with any change that makes tool folds extractable); tool-repaired folds
do not render in the viewport (in-ladder repairs do, with `repaired: true`);
the MCP tool adds ~+835 tokens/step (~+5% on D's measured base); the child
repair budget can overshoot the ladder's soft deadline by ≤5 s (fail-safe:
the unrepaired checkpoint serves).

## 2.4 — merge machinery DONE, retrain DEFERRED

### The machinery

`feasibility/merge_captured.py` is the only place serve-time capture rows
become training rows. Every invariant that could silently skew a model is
pinned in `tests/test_merge_captured.py` (35 tests -- 22 shipped originally,
+13 from the post-review fixes below):

* **ids.** Captured ids continue above the base corpus max and EVERY emitted
  row has one — `dataset.existing_ids` KeyErrors on any id-less row and
  `build_dataset.build_corpus` calls it unconditionally, so one id-less row
  bricks every later resume. An id-less row in the BASE corpus is a loud
  `ValueError` naming the line, not a silent skip.
* **dedup.** Identity is the canonical `[nodes, pairs]` JSON — compiles are
  deterministic, so a re-served design is a duplicate feature vector that would
  reweight training. Keep the MOST INFORMATIVE row (non-None labels beat None),
  `ts` earliest as the secondary key — see the dedup-tiebreak deviation below.
  Captured trees already present in the corpus are dropped (the pinned
  synthetic label wins).
* **labels.** `perturb_pack` None vs False passes through untouched (None =
  attempt-0 packed or never sampled; False = the ladder exhausted);
  `failure_mode` keeps attempt-0-only semantics even when a rung later packed.
* **leakage.** The `gate` field is stripped: it is the OLD model's verdict on
  that very tree.
* **eras.** Rows are copied key-by-key, so all four shipped capture schemas
  merge unchanged (no `perturb` key at all; `perturb` without an audit;
  row-level or ladder-embedded `audit`; the post-2.3 sibling `mv_repair`), and
  a missing `audit` stays MISSING rather than becoming null. Era flags in the
  summary are deliberately NON-exclusive — a post-2.3 row is both
  `mv_repair_bearing` and `audit_bearing`.
* **robustness.** Unknown keys survive (the corpus key-set pin is a superset
  check); rows that could not be trained on at all are dropped, counted and
  reported rather than allowed to `KeyError` a future `train_model._matrix`.
* **reporting.** Duplicates that DISAGREE on a label are surfaced, not hidden —
  see the keep-first hazard below.

`dataset.training_corpus_path()` is now the single answer to "which corpus does
the gate train from?": committed `corpus_wide.jsonl` by default,
`FEASIBILITY_CORPUS_PATH` to opt in to a merged one. Wired through
`train_model --corpus`, `agent_loop.ensure_gate_trained`,
`mesh_to_tree._default_gate`, `test_gate_mesh_region` and
`test_mesh_recalibration_live`, so the mesh-fixture tripwire measures whatever
corpus the gate would actually train on. Opt-in on purpose: a merged file that
became the default when present would silently make one machine's gate differ
from CI's. The merged file is derived and gitignored — served USER trees stay
out of git and the committed synthetic corpus stays pristine.

```
cd mcp_harness && ./.venv/bin/python -m feasibility.merge_captured \
    --captured feasibility/captured.jsonl <other captured.jsonl...>
# writes feasibility/corpus_merged.jsonl (gitignored)
FEASIBILITY_CORPUS_PATH=$PWD/feasibility/corpus_merged.jsonl \
    PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_gate_mesh_region.py
```

### The data (measured 2026-07-25, all three capture sources)

| source | rows | note |
| --- | --- | --- |
| main checkout | 6 | 1 audit-bearing pack, 5 ladder rows (2026-07-24/25) |
| this worktree | 22 | rows 1–10 = task D's live smoke (incl. the known dup pair), 11–22 = task B's churn probe |
| `origedita-integration-e4f8cd` | 5 | 2026-07-19, PRE-ladder schema (no `perturb` key at all) |
| **merged** | **33 read → 25 kept** | 8 duplicates collapsed, 0 corpus collisions, 0 malformed, ids 2600–2624 |

Post-dedup labels: **`attempt0_pack` True on 1 of 25 (4%)** against the
corpus's 26.1%; `perturb_pack` = 17 False / 5 True / 3 None; failure modes
build_failed 15, not_connectable 5, no_pack_ibps 4, pack 1. Eras: 2 pre-ladder,
23 ladder, 6 audit-bearing, **0 mv_repair-bearing** (2.3 shipped after this
capture). The merged corpus is 2625 rows — captured data is **0.95%** of it.
(Numbers above are POST-review-fix: the dedup tiebreak now keeps the most
informative row rather than strictly the earliest by ts — see "dedup tiebreak"
below — which moved one row's `perturb_pack` from None to True and shifted
its era flags; `attempt0_pack` and the feature vectors are unchanged, so the
retrain-deferral evidence in the next section still stands unchanged.)

### Why the retrain is deferred (7-seed sweep, nothing committed)

Trained base-vs-merged at seeds 0–6 and read the five mesh validation fixtures'
`p_pack` margin above the block threshold:

| | base mean margin | merged mean margin | seeds worse | worst merged |
| --- | --- | --- | --- | --- |
| `insect` | +0.233 | **+0.071** | **7 / 7** | **−0.007 (BLOCKED, seed 3)** |
| `fish` | +0.161 | +0.123 | 5 / 7 | **−0.030 (BLOCKED, seed 3)** |

`val_recall_feasible` was **0.9853 on all 14 fits** — the merge bought exactly
nothing measurable — while at seed 3 BOTH thin-margin fixtures flipped to
`infeasible`, i.e. the gate would have started blocking real extracted meshes
from compiling at all. That is the help/hurt tripwire firing. Adding 24 failures
and 1 pack to a corpus whose mesh region is deliberately calibrated (PR #9)
pushes `p_pack` down exactly where the fixtures live.

Second, independent blocker: **the label the retrain is FOR does not exist in
the corpus.** `corpus_wide.jsonl` carries `perturb_pack: null` on all 2600 rows,
so the entire non-null ladder signal anywhere is 21 rows (4 True / 17 False),
and 4 of the Trues are near-identical serves of one tree family. There is no
"needs nudge" class to learn.

**Unblock by VOLUME, not by code.** The documented next step is a synthetic
ladder-outcome corpus pass (`mesh_like` precedent, PR #9): run
`build_dataset` with a large `--perturb-sample` over a mesh-like batch so
`tree_labeler.perturb_label` gives the corpus a nudge class, then re-run the
7-seed margin sweep before touching the gate. Scoped but NOT built this session
(the plan says do not half-build it).

### Structural facts for whoever does the retrain

* **`gate.joblib` has no lifecycle.** Every loader early-returns when the
  artifact exists (`ensure_gate_trained`, `_default_gate`), and
  `server`/`capture` cache the `Gate` in process globals. A retrain therefore
  takes effect ONLY by explicitly calling `train_model.fit`, or by deleting the
  artifact AND restarting every long-lived process. There is no staleness check
  and no CI/CD (out of scope by charter, still true).
* **Where a retrained gate would LIVE is unresolved.** `gate.joblib` is
  gitignored and train-on-demand reproduces only from the COMMITTED corpus. If
  the merged corpus stays gitignored (it does), then a gate trained from it
  exists on exactly one machine and cannot be reproduced from git. Shipping a
  capture-informed gate means choosing one of: commit the merged corpus
  (puts served user trees in git history), commit the artifact (a pickle in
  git), or regenerate the capture rows synthetically. Decide before retraining.
* **The mesh tripwire is single-seed and under-powered.** `test_gate_mesh_region`
  trains at `train_model.fit`'s default `seed=0`, and fixture margins move
  ±0.15 across seeds on the UNCHANGED corpus. The merged corpus PASSES that test
  at seed 0 while failing at seed 3 — the sweep found the regression, the test
  would not have. Sweep seeds when evaluating any corpus change.
* **`benchmark_templates.py` cannot measure a gate retrain.** It calls
  `runner.compile_tree` and `server.draft_and_compile_full_base` only; the gate
  is not in that path, so before/after numbers there are noise by construction.
  The real instruments are the fixture margins and `train_model.fit`'s report.
* **Dedup tiebreak is now most-informative-wins, not keep-first-by-ts
  (POST-REVIEW DEVIATION).** Measured: one tree was served on 2026-07-19 under
  the pre-ladder schema (`perturb_pack` None = UNKNOWN) and four more times
  after the ladder shipped (True). Literal keep-first-by-ts kept the OLDER,
  less informative `None` row — silently converting a known ladder rescue
  into UNKNOWN, and losing 1 of only 5 distinct nudge-positive trees in
  existence (`perturb_pack` True count in the merged corpus: 4 → 5 after this
  fix). Both reviews flagged this as Important. The 2.4 plan's own
  `perturb_pack` None-vs-False preservation clause outranks its own
  dedup-letter, so `merge_captured.py` now keeps whichever row in a duplicate
  group actually carries a known outcome (`attempt0_pack is True`, or
  `perturb_pack is not None`) over one where the ladder never ran at all
  (`attempt0_pack` False AND `perturb_pack` None), with `ts` as the secondary
  key among equally-informative rows — this is a deliberate deviation from the
  plan's literal words, not a silent change (see the PR description). Ties
  still reported via `label_disagreements`, which now also carries a
  `tree_key_hash` and the kept row's `kept_id` so a consumer can locate the
  affected merged row without re-running the merge.
* **The label mapping is hierarchical (binary + conditional second head), not
  flat 3-class.** Read any "3-class" table (see the task report) as shorthand
  for: the existing binary head (`attempt0_pack`, defined on every row) stays
  as-is, plus a NEW second head trained only where `perturb_pack is not None`
  (EXACT / NUDGE / FAIL), with `(False, None)` rows excluded from that second
  head as UNKNOWN but retained for the binary head. It is not a flat 3-way
  softmax over all rows.
* **FAIL is defined by the ladder's budget/rung schedule, not by geometry.**
  `perturb_pack=False` means "the ladder exhausted ITS budget", so NUDGE/FAIL
  labels are only comparable within one ladder version. Record the ladder
  version/budget alongside `perturb_pack` (partially recoverable today from
  `perturb["tries"]`) before the nudge head is ever trained on rows spanning
  more than one ladder version.
* **id space.** Captured rows continue the corpus counter (2600–2624 today), so
  a future synthetic batch appended with `--id-offset` must start above the
  merged max, which `merge()` reports. A reserved high band (e.g. 1e6+) for
  captured rows would remove that coupling if it ever bites.

## Verification

`make test` on this branch (final, after every review-fix wave): **3 failed /
1645 passed / 11 skipped (983 s)** — vs the fresh pre-mission baseline of
3 failed / 1519 passed / 11 skipped, i.e. +126 tests, zero regressions.
The three failures are the pre-existing rigid-origami hash pins, unchanged and
out of this mission's scope by charter:
`test_rigid_compiler::test_representative_full_artifact_hash_vector_is_frozen`,
`test_rigid_miura_compiler::test_representative_miura_artifact_hash_vector_is_frozen`,
`test_rigid_phase3_oracle_fixture::test_phase3_oracle_regenerates_byte_identically`.
CI was still down at time of writing; this is the local gate.

## Open items needing a human decision

1. **The dog mesh `.glb` is still single-machine.** `mesh_acquire` cache
   `36f4aec6…` (sha256 of "hf:a dog", 874,640 bytes) exists ONLY in local
   worktree caches on this machine (NOT in the main checkout's cache — this
   session found it in three old worktrees and re-seeded it). Committing it as
   a test fixture (~875 KB binary) would end the risk; the mission plan says
   ask before adding a binary to git, so it is NOT committed. Decide.
2. **Dedup-tiebreak deviation from the plan letter** (§ dedup above): the plan
   said keep-first-by-ts; shipped is most-informative-label-wins with ts
   secondary, because keep-first measurably converted a known nudge-positive
   label to unknown (1 of only 5 positives in existence). Reviewed and
   approved in-session; flagged here because it deviates from the plan text.
3. **CLAUDE.md §4 drift**: the tool names in CLAUDE.md's "Agent's Tool
   Harness" section (init_paper, add_node, compile_treemaker_math, …) are the
   original design fiction and do not match the real MCP tools
   (draft_and_compile_full_base, validate_flat_foldability,
   reference_tree_from_query, repair_mv_assignment, …). A one-line disclaimer
   was added to CLAUDE.md this session; a real rewrite remains out of scope.
4. **Cosmetic residuals** (all pinned or inert, listed for completeness):
   `hf-dog-ladder-best.fold`'s frame_title carries the pre-2.3 two-term marker
   text; `test_cli_loosened_kawasaki_tolerance_still_exits_nonzero` is vacuous
   as a regression pin (closure defects force exit 1 regardless);
   `_max_id` raises a bare int() error on a non-int corpus id;
   `test_gate_mesh_region`'s docstring references a session-scoped scratchpad
   probe path.
