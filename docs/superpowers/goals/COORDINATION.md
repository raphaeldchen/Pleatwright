# Goal coordination — Goal 1 (whole square) × Goal 2 (models that look symmetric)

Two planning sessions run in parallel. This file is the only place a constraint
that spans both goals can be enforced; git cannot warn about any of them.

**Two different commits matter and they are not the same one:**

| | commit | meaning |
|---|---|---|
| **Branch from** | **`a04cb0a`** (main: S4a′ + 0α + PR #75) | the base for all new work |
| **Measure against** | ~~`1c9abe0`~~ → **the current fixture** | ✅ freeze LIFTED 2026-08-16; the baseline was re-blessed once over `1c9abe0..153f9c7` — §1 |

**Both planners maintain this file.** Edit it in the same commit as the action it
records.

---

## 1. THE SCORECARD IS FROZEN — ✅ **FREEZE LIFTED 2026-08-16, AS DESIGNED**

> ✅ **The freeze has ENDED and the one combined re-bless HAS HAPPENED.** Both
> goals are closed and the final unit discharged the debt this section
> created: `scorecard_baseline.jsonl` now measures `1c9abe0..153f9c7`, with a
> per-cell attribution table in its own `_meta` — **36 cells, 6 owning
> slices, 31 bisected + 5 structural, zero unattributed**, plus **four
> zero-row segments verified rather than asserted**. The protocol below was
> met, not bypassed: the field-by-field check it demands was done in both
> directions and is shown in the PR body.
>
> **What is still binding is the purpose, and it outlives the freeze:** one
> instrument, every moved row attributed, **no unattributed re-bless, ever**.
> The next re-bless owes the same table. What is retired: "neither planning
> session re-blesses it" and the `1c9abe0` measure-against target.

`mcp_harness/fixtures/scorecard_baseline.jsonl` was **frozen at `1c9abe0`** for
the duration of both goals. **Neither planning session re-blessed it.**

> ⚠ **Amended 2026-08-05 — the file is no longer byte-identical to `1c9abe0`,
> and pretending otherwise would make this section the stale binding doc it
> exists to prevent.** Commit **`d542053`** (PR #78, a third workstream)
> populated `served_stage` and `path_drift_max`, which PR #75 had added to
> `_COLS` as *keys the fixture did not carry* — so every run was reporting them
> as `None -> value` on all five rows.
>
> **Verified before accepting it** (field-by-field diff of `d542053~1` vs
> `d542053`): **10 new-column cells, ZERO moved values**, and
> `served_stage == rescue_stage` on all five subjects — i.e. the new column
> restates one that already existed at `1c9abe0`, so no post-#75 state was
> written into the frozen values. Nothing was absorbed. `no axis moved` is
> again the correct reading, and **that block is spent — do not expect it and
> do not re-derive it.**
>
> **What is still binding:** the *purpose* — one instrument, every moved row
> attributed, no unattributed re-bless. What is retired: the claim that the
> bytes match `1c9abe0`. A future re-bless still requires the field-by-field
> zero-moved-values check **shown in the PR body**, not asserted.
>
> **Read the failure this exposed, because it will recur.** The warning that
> would have flagged this in advance was written, correct, and **sitting
> unmerged in PR #76 at the moment PR #78 needed it.** A coordination file has a
> liveness precondition: unmerged, it protects nobody. It cost nothing this
> time only because #78 happened to do the attribution carefully on its own.
> **Land coordination edits immediately; do not hold them for a green PR.**

That file has been re-blessed ~~six~~ **seven** times (the seventh is the
2026-08-16 combined re-bless); `--out` **appends**, so regenerating
means replacing it wholesale; and its own `_meta` records `quadruped` deltas it
can only label `NOT_attributable` because the prior baseline was two shipped
slices stale — with ~~**one** branch in flight. There are now two.~~ ⚠ **Both
goals are now CLOSED and there are ZERO branches in flight**, so the
two-branch contention model this sentence describes no longer applies.

**Protocol, binding on every PR from either goal:**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python \
    benchmark_subjects.py --baseline fixtures/scorecard_baseline.jsonl
```

- Report that delta table in the PR body.
- **Attribute every moved row to a slice.**
- **A row you cannot attribute is a FINDING, not noise.** Say so.
- ~~**One combined re-bless at the very end of both goals**, with a full
  attribution table in `_meta`. Not before.~~ ✅ **DONE 2026-08-16.** Both
  goals are closed and the combined re-bless has happened. **The rule that
  replaces it:** re-bless when you must, never incrementally, and **never
  without the full per-cell attribution table** — the first three bullets
  above are unchanged and remain binding.
- ⚠ **ONE KNOWN EXCEPTION to bullet 3, and only one:** `path_drift_max`
  deltas of order `1e-16` on `humanoid` or `insect`. Those two cells carry
  1-ulp values (`1.887163533429072e-16`, `2.389544559551537e-16`) blessed as
  measured on macOS/Accelerate, and `diff_table` compares them with an exact
  `!=`. A different BLAS will report them as moved forever. **That is this
  known issue, not an unattributed row** — and it excuses nothing else. See
  the fixture's `_meta.path_drift_max`.

**Its `_COLS` carries both goals' columns in the same rows.**

| column | owner |
|---|---|
| `hull_coverage`, `design_scale` | **Goal 1** |
| `cp_symmetric`, `cp_mirror_residual`, `cp_mv_broken` | **Goal 2** |
| `served_stage`, `path_drift_max` | **neither — a THIRD workstream** (PR #75, base-inspection loop) |

> ⚠ **There is a third writer on this file and it did not announce here.**
> PR #75 (merged `58d2acd`) added `served_stage` and `path_drift_max` to
> `_COLS`. **Measured on `a04cb0a`, the frozen-baseline delta is therefore no
> longer `no axis moved`:**
>
> ```
> quadruped: served_stage: None -> 'stub';      path_drift_max: None -> 0.0
> bird:      served_stage: None -> 'none';      path_drift_max: None -> 0.0
> humanoid:  served_stage: None -> 'none';      path_drift_max: None -> 0.0
> fish:      served_stage: None -> 'placement'; path_drift_max: None -> 0.0
> insect:    served_stage: None -> 'order';     path_drift_max: None -> 0.0
> ```
>
> **Every move is a column-addition (`None -> value`), not a value movement,
> and no goal-owned axis moved — `hull_coverage` is unchanged on all five.**
> Attribute this block to **PR #75** in every future PR body from either goal
> and do not re-derive it. Recording it now, while attribution is still
> possible, is the whole point of §1: this is exactly how the previous
> baseline came to carry `quadruped` deltas it could only label
> `NOT_attributable`.

Announce every `_COLS` edit in §4 below before dispatching it.

> **Adding a column fires the delta table on every row.** `_diff` reads both
> sides with `.get(c)`, so a new column renders as `None -> <value>` for all five
> subjects. Label that as column-addition, not movement.

---

## 2. FILE-REGION CLAIMS

`mcp_harness/TreemakerWrapper.cpp` is **strictly serial**. Claim it here before
dispatching; release on merge.

| file / region | claimed by | since | status |
|---|---|---|---|
| `TreemakerWrapper.cpp` — `ProjectActivePaths` | Goal 1 / S4a′ | 2026-08-04 | RELEASED — merged `5f6ab2a` |
| `TreemakerWrapper.cpp` | — | **2026-08-06** | 🟢 **RELEASED BY GOAL 2, SAME DAY. S3 was refuted before dispatch — Goal 1's S4b₀ is UNBLOCKED NOW** |
| `TreemakerWrapper.cpp` — `ProjectActivePaths` + `projection_report()` | Goal 1 / S4b₀ | 2026-08-07 | 🟢 **RELEASED — merged `8af5bc4` (PR #90).** Book (0°) and 90° ship as exact integer rows; `maxr`/`ran` in `projection_report()`. ⚠ **The result is a NEGATIVE and Goal 2 should know it:** book0 is rejected downstream on 4 of 4 production templates, never for projection precision. **Goal 1's S4b-general is CANCELLED and S5 shrinks to the coverage-vs-scale argument alone.** The file is free for either goal |
| `mcp_harness/treemaker/Source/tmModel/**` (vendored) | — | 2026-08-05 | **RELEASED by Goal 2** — see below |
| `mcp_harness/mv_repair.py` + a new `.fold`-side module | Goal 2 / S2′ | — | soft claim; **does not touch the serial file** |
| `mcp_harness/vlm_judge.py` + `mcp_harness/fixtures/vlm_judge/` | corigami-2 rubric unit | **2026-08-29** | 🔒 **CLAIMED — strictly serial for this wave.** The shipped rubric is COrigami's **Appendix I, p.30 folded-model** prompt (five ordinal criteria, transcribed verbatim), applied at the **stick-figure** stage that `vlm_judge.py:1-30` argues is the only judgeable one. It is replaced by COrigami **§3.1, p.5**'s four stick-figure criteria (`topological_accuracy` 4, `proportional_feasibility` 3, `semantic_recognisability` 2, `structural_complexity` 1), so `RUBRIC_VERSION` moves `"corigami-1"` → `"corigami-2"`. That edits `SYSTEM_PROMPT`, which invalidates **all 41 case digests** across the two corpora, stranding **164 recorded replies** (24 in `replay.json`, 140 in `battery.json`); neither rekeyer can repair them (`vlm_judge.rekey_fixture` for replay, `probe_judge_battery.rekey_battery` for the battery — by design **neither ever touches a reply**), so both are **re-recorded: 164 calls, plus 48 for the new Gate D and its live required-fail input = 212 billed calls**. A parallel writer landing any prompt or payload edit would silently strand that spend. Bars for all four gates, the `anatomy` statistic and five required-fail inputs are pre-registered **before the first billed call** in `docs/superpowers/decisions/corigami-2-stick-figure-rubric.md`; Gates A/B/C reuse `axis-a-verdict.md`'s verbatim, because changing rubric and bar together would make the two calibrations incomparable. RELEASE ON MERGE |
| `mcp_harness/judge_loop.py` (new) + `mcp_harness/extraction_blob.py` (new) + `mcp_harness/mesh_to_tree.py` + `mcp_harness/mesh_report.py` + `mcp_harness/server.py` | judge-in-the-loop wave (U1–U8) | **2026-08-30** | 🔒 **CLAIMED — five files, one wave.** Wires the existing stick-figure judge into the mesh→metric-tree extraction path as **report-only advisory feedback** at `server.py:4152`, the only point that holds the user's prompt and a `MeshTreeResult` at once. Behind `IDE_JUDGE_LOOP`, **default OFF and byte-identical when off**. `mesh_to_tree.py` gains the **runner-up** the search currently overwrites at `:2962` and discards; `_serve_rank` (`:1850`) is **not touched**. `mesh_report.py` gains an advisory block; `server.py` gains the seam and `_LAST_EXTRACTION["judge_loop"]`. **Nothing is re-ranked, re-searched or rejected** — the agent reads the opinion and decides. ⚠ **`mcp_harness/vlm_judge.py` and `mcp_harness/fixtures/vlm_judge/` are DELIBERATELY NOT CLAIMED, and no unit in this wave may touch the digest surface** (`SYSTEM_PROMPT`, `CRITERIA`, `build_payload`, `render_user_text`, `COMPARE_SYSTEM_PROMPT`, `render_compare_text`): **45 digests** across `battery.json` (35) + `replay.json` (6) + `compare.json` (3 + 1 top-level `system_prompt_digest`), and **164 billed calls** to re-record — a bill the corigami-2 wave paid on 2026-08-29 and this one does not re-pay. Budget here is **18 billed calls, hard cap 40**, meshes free (fake provider, committed fixtures). Four claims and four required-fail inputs pre-registered **before the first billed call** in `docs/superpowers/decisions/judge-in-the-loop.md`. ⚠ **Gate B has never been measured on an extracted tree** — its four good arms are `E1_PLANS = body_plans.NAMES` (`probe_judge_battery.py:340`), all hand-authored templates — so Claim 2 is a **first measurement**, not a re-run: the bar is reused from `axis-a-verdict.md` verbatim (median `anatomy` ≥ 0.80, which corigami-2 **PASSES at 0.813750** on E1) with **no outcome pre-registered**, and the result is recorded either way. ⚠ **E1 and E2 numbers are NOT interchangeable** (`build_case`, `probe_judge_battery.py:465-495`: E1 forces `stub_flaps 0` / `served_fidelity 1.0` on hand-authored trees, E2 copies the extracted serve verbatim) — `axis-a-verdict.md:533-542` already warned this is *"two products, not two trees"*. RELEASE ON MERGE |

~~**Agreed order:** Goal 1's S4a′ → Goal 2's S3 → Goal 1's S4b₀.~~
**SUPERSEDED 2026-08-06.** S3 was refuted before dispatch and never entered the
file, so the middle term is gone: **S4a′ (merged) → S4b₀, whenever Goal 1 is
ready.** Goal 2 has no current or queued claim on `TreemakerWrapper.cpp`. Its
remaining slices (S2′, and the ordering slice if Goal 2 owns it) are Python-only.

> ✅ **Goal 2 RELEASES the vendored TreeMaker claim, 2026-08-05.** S2a measured
> that the facet-ordering solver **cannot express** a mirror-symmetric-and-
> foldable M/V assignment: quadruped/bird's post-cut ordering graph admits
> **exactly one** linear extension, and corpus-wide **225/225** M/V-bearing
> creases have order-comparable facet pairs, so every label is forced. Making
> the cut σ-symmetric drives the mirror metric green on all four targets and
> yields a pattern the non-crossing oracle refutes with `taco-taco` — measured
> two independent ways, stock passing 8/8 as the control. The FOG encodes
> physical layer constraints; deleting links until the answer goes symmetric is
> discarding physics. **Goal 2's M/V fix moves out of the C++ entirely.** Only
> the read-only, env-guarded FOG dump (`822497b`, branch
> `claude/goal-2-s2a-fog-dump`, byte-identical output 27–28 patterns) touched
> vendored source, and it is **not** proposed for merge.
>
> ⚠ **For Goal 1: `cp_mirror_residual` and `mv_swapped` are GAMEABLE.** A
> pattern can score perfectly mirror-symmetric and be unfoldable. Goal 1's live
> lever is the placement seed → packing → CP → M/V, so a Goal 1 slice can move
> those columns in the good direction while producing paper that cannot fold.
> **Do not read a falling residual as an improvement without a `flat_fold` +
> `layer_order` check.**

> **One deferred item rides with S4b₀, not ahead of it.** S4a′'s review found
> `projection_report()`'s `iters` **saturates at `maxIters = 50`** — `star-4-sym`
> and `star-5` both exit on the cap with the residual barely moved
> (2.031e-09 → 1.717e-09), so the margin-to-cliff proxy is censored on exactly
> the tree S4b₀'s headline result depends on. The fix is to expose the loop's
> final `maxr` plus a `ran` flag. It is ~5 lines in `ProjectActivePaths`, so
> **it is S4b₀'s Task 1** rather than a separate claim on the serial file —
> queueing it separately would make Goal 2 wait twice.

---

## 3. CROSS-GOAL GATES

| gate | blocked slice | why |
|---|---|---|
| **Goal 1 S4a′ merged** | Goal 2's **S3** | S3 is blocked on the projection refusing what it cannot represent |
| **Goal 2 S3 merged AND Goal 1 re-measured** | Goal 1's **S5** | ⚠ **Non-negotiable.** S3 pins unpaired axial leaves and was measured to move **bird coverage 0.5206 → 0.6612 and scale 1.3093 → 1.3518**. S5's entire deliverable is the coverage-versus-scale argument. Measuring S5's baseline before S3 lands argues against numbers about to move ~27% on the lowest-coverage subject in the corpus |
| **Goal 1 S4b₀ reported** | Goal 1's **S5** | S5 needs the export-path result, not the optimizer-only one. ✅ **Reported 2026-08-07** — see the 2026-08-07 signal below and `goal-1-whole-square/PROGRESS.md`. This half of the double gate is satisfied; the S3-merged-and-remeasured half is not this slice's to close |
| **Goal 1's `hull_coverage` → true polygon area (0b)** | Goal 2 reporting **any** coverage number | Shared instrument. Goal 2 rebases onto it first, or the two goals' figures are not comparable |

**S5's gate is a DOUBLE gate**: S4b₀ reported **AND** S3 merged **AND**
re-measured.

---

## 4. SHARED-INSTRUMENT LOG

Append-only. Announce before dispatch; record the merge commit after.

| date | goal | instrument | state |
|---|---|---|---|
| 2026-08-04 | 1 | `docs/superpowers/evidence/2026-08-04-axis-corner-capacity/` — five probes + outputs, reproducible from a clean checkout | **landed (planning session)** |
| 2026-08-06 | 1 | `paper_coverage.hull_coverage` → true polygon area (**0b**). **Lands standalone.** | **PR pending, rebased onto `7a94b67`** — `hull_coverage` unchanged on all five frozen-baseline subjects; all nine committed goldens now report `source == "boundary_cycle"`. Goal 2 rebases onto it once merged |
| 2026-08-04 | 1 | `0α` premise probe → `fixtures/axis_corner_capacity.json`. New file; adds **no** scorecard column and moves **no** row | **DISPATCHED — parallel-safe, no conflict with S3** |
| 2026-08-06 | 1 | `design_scale` column — `_COLS` edit (**`0-scale`**, renamed from `0a`). Sourced from the served fold's `frame_title` via the shared parser below. ⚠ **WITHIN-SUBJECT ONLY** — paper-units per TREE-unit, and the tree unit drifts across rows (`to_metric_tree`'s own docstring: `LONGEST_LIMB_TARGET` is reconciliation's *input*, not its post-condition; humanoid 0.400000 → 0.349099, re-parenting worst 2.02×). Reading the column ACROSS subjects measures tree size, not design quality — the five rows' apparent coverage↔scale trade (ρ = −0.700) is beaten on both legs by `served_leaves` (−0.900 / +0.900). See Goal 1 PROGRESS, "0-scale review" | **IMPLEMENTED, branch `claude/goal-1-0-scale-design-scale-bf5d26`. `--baseline` delta is EXACTLY the column-addition on all five rows (`None -> value`), nothing else moved; `hull_coverage` unchanged on all five. Values live in Goal 1's PROGRESS — deliberately not listed side by side here** |
| 2026-08-06 | 1 | one shared `scale=` parser (`fold_meta.py`, new module) de-duplicating `pose_base.py`/`probe_dog_pose.py`'s verbatim regex copies; `pose_base` and `probe_dog_pose` become its callers. Byte-identical behaviour pinned in `tests/test_fold_meta.py` (normal title, no-scale title, missing frame_title, ERROR string) | **IMPLEMENTED with `0-scale`** — `pose_base`'s existing tests pass unmodified |
| 2026-08-04 | 1 | `ProjectActivePaths` `outIters`/`outCons` exposed at the production call site (margin-to-cliff proxy) | **shipped in S4a′** |
| 2026-08-04 | 1 | `error_recipes` gains the projection-failure code — **can move the `error_codes` column** | **shipped in S4a′** |
| — | 2 | `cp_mirror.mirror_verdict(axis_degrees=…)` — Goal 1's S4b₀ is its first caller off 45° | shipped in S1 |
| 2026-08-16 | 1+2 | **`fixtures/scorecard_baseline.jsonl` — THE COMBINED RE-BLESS.** The shared instrument itself, re-blessed once over `1c9abe0..153f9c7` after both goals closed. 36 attributed cells / 6 owning slices / 31 bisected + 5 structural / 0 unattributed; 4 zero-row segments verified by bisection, not asserted. Attribution table lives in the fixture's own `_meta` and is authoritative over every prose copy | **LANDED — the freeze created in §1 is lifted. Post-re-bless `--baseline` delta is `no axis moved` on all five subjects** |
| 2026-08-17 | 1+2 | **`fixtures/scorecard_baseline.jsonl` — THE SECOND RE-BLESS, four cells, one owner.** ⚠ The 2026-08-16 row above was measured at `153f9c7`, which **predates #128 and #129** (the two Linux-CI fixes), so it was stale on arrival: `bird` `lint_class` PASS → BENIGN, `cp_symmetric` **False → True**, `cp_mv_broken` **4 → 0**, and `insect` `lint_class` PASS → BENIGN. **`bird` is mirror-symmetric, so Goal 2 is 4 of 5, not 3 of 5.** Owner is **#129**'s `serve_rank` Pass/BENIGN collapse, **bisected over four arms with the `.so` rebuilt at each** — #128 innocent, current `main` innocent (including #127, which moves the extractor). Table now 40 cells / 7 owners / 35 bisected + 5 structural / 0 unattributed; the derived counts are asserted in `test_pair_reconcile.py`, not restated in prose | **LANDED. `--baseline` delta is `no axis moved` on all five on the blessing platform (macOS); on `linux/amd64` exactly one cell reports, `quadruped.lint_class` BENIGN → PASS, which is NAMED as platform-divergent in `_meta.platform_divergent_cells` and pinned as tolerated. ⚠ The divergent set SHRANK from two cells to one — #129 closed `bird.lint_class`'s swap** |
| 2026-08-15 | base-eval | `evaluate_base()` MCP tool + `server._read_base_payload()` extraction (**U13**). `read_base()` now delegates to the new helper and its payload is **byte-identical** (`test_read_base_payload_is_unchanged_by_the_extraction`, plus `tests/test_read_base.py` 28/28 unmodified). The extraction is the point: `read_base()` names THREE routes that can make a serve record stale, and a second tool re-deriving the `_CHILD_COMPILE_EPOCH` comparison would have become a **fourth** the moment the two drifted. Any goal adding a serve-record reader should call `_read_base_payload()` rather than re-read `_LAST_SERVE`. ⚠ Also recorded: **`validate_flat_foldability` is NOT an `@mcp.tool()`** in `server.py` despite CLAUDE.md §5 describing the agent calling it — it is a plain function in `linter_server.py` (separate process). Measured lint cost 0.14 s on folds 1.5–10 KB | **IMPLEMENTED** — 47/47 (`test_evaluate_base.py` + `test_read_base.py`) |
| 2026-08-15 | base-eval | `base_accept` + `base_reject_rules` columns (**U12**) — `_COLS`/`_DIFF_COLS` edit. The pre-registered accept rule (`base_verdict`, `RULE_VERSION 1`) applied per row. **Not a new measurement**: every input is already a column here (`served` / `shadow_diff` / `lint_class`); what is new is that the bar is applied identically every run. `base_verdict` never reads `judge`, so **no model opinion can reach the scorecard**. Rule version rides the scorecard HEADER, not a third column. `build_row` gains `shadow_diff=` (the whole dict `path_drift_max` was already reduced out of) — `None` REJECTS rather than reading clean | **IMPLEMENTED** — see delta note below |
| 2026-08-15 | base-eval | `diff_table` now distinguishes **absent from null** (**U12**, shared instrument — affects every goal's `--baseline` read). A column added after the frozen baseline was blessed is missing from every baseline row; the old `.get()` comparison read that as `None` and reported a move on **every** subject. Now skipped per-subject and **announced once by name** (`new columns since the baseline`), so the `design_scale` precedent's evidence value is preserved without burying real regressions. A baseline column holding `null` that now holds a value is still a real move and still reports | **IMPLEMENTED** — `diff_table(baseline, baseline)` is now silent, which it was not before: the committed baseline predates `design_scale` too, so a self-diff announced three phantom additions until the "present in this run **and** absent from the baseline" condition was corrected |
| 2026-08-30 | judge-in-the-loop | **`vlm_judge.judge()` + `judge_compare.compare()` — THE JUDGE GAINS ITS FIRST CALLER INSIDE AN MCP TOOL.** Announced before dispatch, per this section's rule. Today `vlm_judge` has **three** non-test importers and none is on the serve path: `base_report.py:200` and `:782` (an offline HTML-report CLI, behind an opt-in `--judge` flag), `probe_judge_battery.py:209` (the calibration probe), and `judge_compare.py:303` (which imports it for `_assert_advisory_shape`, not to score). (`probe_base_eval.py` and `mesh_identity.py` name it only in prose — verified, neither imports it.) **Nothing on the serve path has ever invoked it**, and `judge_compare.compare` has **no caller at all outside its own test** — its committed corpus is `"provenance": "hand-authored"`, so its pairwise behaviour has never been measured against a model. This wave adds `judge_loop.run` at `server.py:4152` behind `IDE_JUDGE_LOOP`, **default OFF and byte-identical when off**. ⚠ **Advisory, report-only, and gating NOTHING** — `base_verdict` still never reads `judge` (`base_verdict.py:111`) and still stamps `judge_consulted: False` (`:183`); `_serve_rank` is unchanged; the served tree is unchanged. ⚠ **The judge may never set `R`**: `reference_count` feeds `fidelity_score` (`mesh_to_tree.py:3126`), which is `_serve_rank`'s primary key (`:1867`), so a judge that reads a tree and proposes a count is the closed loop the anatomy-oracle plan forbids (`2026-08-29-anatomy-oracle-beyond-the-table.md:76`). **NO instrument definition moves and NO scorecard column is added** — this wave adds a report block, not a metric. Pre-registration: `docs/superpowers/decisions/judge-in-the-loop.md` | **PRE-REGISTERED — U1 landed; U2–U8 in flight. 18 billed calls budgeted, hard cap 40** |

---

## 4.1 ★ STANDING RULE — every metric ships with an input it MUST fail

> **A metric ships with a known-bad input it is *required* to score as failing,
> asserted in a test. If you cannot construct one, the metric is vacuous and
> does not ship.**

Cheap, and it would have caught **all four** of these. Four is a pattern:

| metric | how it was vacuous | found |
|---|---|---|
| `pair_path_gap_max` | read `0.0` **tautologically** — bird's CP was byte-identical before and after the change it measured | 2026-08-03 |
| the FOG dump's `color` field | **always `0`** (`NOT_ORIENTED`) — dumped inside `CalcFacetOrder`, *before* `CalcFacetColor` | 2026-08-05 |
| the `flat_coords` bypass | a vacuous-pass path that skipped the verdict | PR #63 |
| `mv_swapped == 0` | is **exactly** what the unfoldable symmetric patterns score | 2026-08-05 |

Three earlier symmetry metrics also scored a lopsided pattern `0.000000`; S1's
bijection reformulation reversed all three. Same shape every time: *the metric
cannot express the defect it is named after.*

⇒ **Goal 1 owes one for `hull_coverage`.** It has never been shown an input it
must reject. Before it is an acceptance criterion, construct a pattern whose
true polygon coverage is knowably poor and assert it scores poorly. **A metric
that only ever goes up is not a measurement.** (Noted as owed, not as a demand
on 0b's scope — Goal 1 owns when.)

⇒ **Goal 2:** S2′'s gate is `flat_fold` + `layer_order` + `cp_audit`, never
`mv_swapped` alone. Its required-fail input already exists: any SYMFIX pattern.

⇒ **S2′a paid this rule three times over, 2026-08-07.** `layer_order` gained
the constraint families its `if a not in ("M","V"): continue` filter dropped,
and each one ships with a relabel of a COMMITTED golden that the pre-S2′a
system accepts and that family alone refutes — `hshape.fold` flips `[3,6,10]`,
`quad.fold` flip `[13]`, `quad.fold` flip `[2]`
(`tests/test_layer_order.py::TestRequiredFailInputs`). The test asserts
CAUSATION, not co-occurrence: it propagates the constraint set with the new
families stripped out, shows no contradiction, then re-propagates with them and
matches the offender string. `star-4.fold` is the vacuity guard on the other
side — it has no `F` shared edge, so it must gain no constraint at all.

**`layer_order`'s error direction, measured 2026-08-05 — it UNDER-refutes.**
Every constraint family in `_build_constraints` is gated on membership in
`pairs`, which is derived from the arrangement cells, and `AREA_EPS = 1e-9`
drops sliver cells. A dropped cell **removes** constraints and can never
manufacture one. So a refutation surviving it is *stronger* evidence, and an
independent implementation of the three Justin conditions is **confirmatory,
not blocking**. (Oriedita and the simulator are **not** valid cross-checks here:
Maekawa/Kawasaki are strictly per-vertex, taco-taco is global, and the simulator
has no collision detection.)

---

## 5. SIGNALS

Post here when a gate opens. Both sessions read this file at the start of every
working turn.

| date | signal |
|---|---|
| 2026-08-04 | Goal 1: spec approved, `2026-08-04-whole-square-axis-projection-design.md`. S4a′ claimed on `TreemakerWrapper.cpp`, dispatching next. **Goal 2: S3 stays blocked until S4a′ merges.** |
| 2026-08-04 | Goal 1: **S4a′ merged.** `TreemakerWrapper.cpp` released. Goal 2's S3 is unblocked. Nine committed geometry goldens byte-identical; full suite 2256/11/0 (2241 + 15 new); Linux `ci-amd64-run` container green (see `PROGRESS.md` for the measured pin displacements and the frozen-baseline delta). |
| 2026-08-04 | Goal 1: **S4a′ independently re-verified by the planning session on its own build** — diff matches the plan with no improvisation; 15/15 in 1.14s; `pin_max_displacement` exact (`0.0`, `6.629976567751328e-10`); ODR trace confirmed (`TreemakerWrapper.cpp` has **no** direct `#include "tmTree.h"`, transitive via `tmModel.h`, hygiene 3/3); **frozen-baseline delta reproduced: `no axis moved`**. Zero discrepancies between report and reality. |
| 2026-08-04 | ⚠ **The 2256/11 vs 2257/10 skip split is NOT macOS-vs-Linux — it is short-path-vs-long-path.** Reproduced 2257/10 **on macOS** from a 46-char worktree path against 107 chars; `test_rigid_collision_evidence[member_socket]` binds an AF_UNIX socket under `Path.cwd()` and overruns `sun_path`. Do not go hunting a Linux-specific cause. |
| 2026-08-04 | ⚠ **`PROJECTION_UNSUPPORTED` / `PROJECTION_INVALID` are live but unexercised by any scorecard row.** None of the five subjects' current failures is one of them, which is why S4a′ moved `error_codes` nowhere. **The first row that ever trips them will move a frozen column, and it belongs to S4a′ retroactively** — not to whatever slice is in flight when it surfaces. |
| 2026-08-04 | Goal 1: **0α and 0b dispatched in parallel.** Neither touches `TreemakerWrapper.cpp`; **Goal 2's S3 is not blocked by either.** 0b is the shared coverage instrument — rebase onto it before reporting a coverage number. |
| 2026-08-05 | Goal 1: **0α merged** (PR #74, `a04cb0a`). `mcp_harness/fixtures/axis_corner_capacity.json` + `probe_axis_corner_capacity.py` are now the committed premise instrument. **`TreemakerWrapper.cpp` remains FREE — 0α touched no C++. Goal 2's S3 is still unblocked and is the next claimant.** |
| 2026-08-05 | ⚠ **A THIRD workstream merged between the two goals' slices** (PR #75, `58d2acd`, base-inspection loop) and added two `_COLS` columns without announcing here. See §1: the frozen-baseline delta on `a04cb0a` now fires on all five rows. **It is a column-addition, not movement; no goal-owned axis moved.** Both goals: paste that block and attribute it to PR #75 rather than re-diagnosing it. |
| 2026-08-05 | 🔴 **MAIN IS RED AT `a04cb0a`, AND IT BLOCKS BOTH GOALS.** `tests/test_read_base.py::test_checkpoint_fallback_pins_the_served_tree_not_the_request` fails with `ERROR: compilation timed out after 1.2s`. **Reproduced on two platforms** — GitHub CI (Linux): `1 failed, 2357 passed, 10 skipped in 2131.76s`; Goal 1 planning session (macOS): `1 failed, 2356 passed, 11 skipped in 1411.99s`. (The 2357/10 vs 2356/11 split is the short-path/long-path AF_UNIX effect, already diagnosed under S4a′ — not a second bug.) **Not caused by 0α, and not a merge interaction:** PR #74's `test` check was green, and this same test was already failing on PR #75's own head before it landed. **Nobody should branch off a red main without knowing it is red.** |
| 2026-08-05 | ✅ **Timed before fixing, because the fix destroys the evidence: PR #75 did NOT cause this — it is ONE ticket, not two.** `_run_ladder_child(DOG_RAW)` at production timeout, n=7, identical `.so` (no C++ changed): `5f6ab2a` pre-#75 median **1.746 s**, `a04cb0a` post-#75 median **1.855 s** — **+6.2%**, a creep, not a tripling. Also corrects the reading of the test: the compile is ~1.8 s against a 1.2 s budget, so it **always** times out *by design* — the assertion is that the checkpoint fallback returns a served tree. |
| 2026-08-05 | ⚠ **Correction to the line above, measured: the child's `0.6 × _COMPILE_TIMEOUT` deadline is NOT the live budget** (I first recorded that it was). `_run_isolated` uses `mp.get_context("spawn")`, so the child **re-imports `server` from disk** and never sees a parent-side `monkeypatch.setattr` — verified directly: parent patched to 1.2, child still reports **60** (internal deadline 36 s, never fires). **The only live budget is the parent's `proc.join(1.2)`.** Consequence for whoever fixes it: **the test cannot reach the child's behaviour through module globals at all** — an injected condition must survive spawn (parent-side seam, env var, or stub worker). |
| 2026-08-05 | ⚠ **The failing test is wall-clock-calibrated and was tuned in the regime where it cannot fail.** It sets `_COMPILE_TIMEOUT = 1.2` and its own comment records "empirically stable on this checkout (6/6 trials)" — measured **in isolation**. Goal 1 planning re-ran it: **5/5 green standalone, 20/20 green running its whole module**, and red only inside the full suite, at ~93% progress on macOS and ~56% on Linux. This is the project's own rule — *never measure a mechanism only in the regime where it cannot fail* — inverted: the budget was calibrated isolated and deployed in the suite. A fix that just raises 1.2s re-calibrates in the easy regime again; the durable fix is to stop making a correctness assertion depend on wall-clock, or to calibrate it from inside a full-suite run. **Goal 1 is not the owner of this file and is not fixing it — flagged here for whoever is.** |
| 2026-08-05 | Goal 1 planning: **0α independently re-verified.** All six acceptance numbers, `star-6`'s `pin_max_displacement = 6.629976567751328e-10`, and the fixture-break proof all reproduced on a rebuilt `.so`; the order-restart control is genuinely non-vacuous (12/10/12 *distinct* scale values). **Its headline verdict does not survive an equal-N comparison** — see `goal-1-whole-square/PROGRESS.md`. The correction *strengthens* the corner lever, so **S4b₀'s justification is unaffected** and no gate changes. |
| 2026-08-05 | Goal 2: **S2a shipped and independently verified — the M/V fix CANNOT live in the facet ordering.** Vendored TreeMaker released (§2). Every number in the implementation report reproduced on independently written code; the *remedy* is what fell. A valid symmetric target EXISTS on 6 of 7 subjects (most need a σ-FIXED crease flip) but is unreachable from the ordering graph. **`mv_swapped == 0` is now a known-vacuous criterion — see §4.1.** |
| 2026-08-06 | ✅ **Goal 2 ANSWERS THE SCHEDULING QUESTION: S3 IS NEXT, ahead of S2′. `TreemakerWrapper.cpp` CLAIMED (§2).** Goal 1's S4b₀ and S5 do **not** slip. The reason is a measurement, not a preference: §1's own rule forbids an acceptance criterion on a column reading `None`, and **`cp_mv_broken` is `None` on 4 of the 5 subjects** because no vertex bijection exists there. S3 creates the bijection — so **S3 is a precondition for S2′ being measurable at all**, not merely adjacent to it. Running S2′ first would gate it on a 1-subject scorecard (only `insect` has a bijection today). S2′ touches only Python on the `.fold` and **never** the serial file, so it is being specced in parallel and dispatches the moment S3 merges. |
| 2026-08-06 | ⚠ **Goal 2 → Goal 1, on S3's announcement:** §3's gate says Goal 2 announces S3's merge *with the new coverage figures*. Per the 0b signal, **Goal 2 will announce S3 with its SYMMETRY figures only and explicitly DEFER the coverage figures until 0b is on `main`.** The bird 0.5206 → 0.6612 number predates 0b and was measured with the convex hull, which can only overstate a non-convex outline. Treat it as indicative, not as S5's input. |
| 2026-08-06 | ✅ **SUPERSEDES the deferral above — 0b IS on `main` (PR #81, `773982a`) and Goal 2 has rebased onto it. The coverage gate is LIFTED for Goal 2.** Verified independently on post-0b main before claiming it: `benchmark_subjects.py --baseline` returns **`no axis moved: quadruped, bird, humanoid, fish, insect`**, and `hull_coverage` reproduces the frozen values **exactly** (0.7161 / 0.5 / 0.6319 / 0.9077 / 0.8595) under the new true-boundary-polygon instrument. Consistent with CLAUDE.md §1.1(1): these five have a boundary hull equal to their full hull, so the two instruments agree **on them**. ⚠ **That does not generalise** — convex hull and true polygon diverge only on non-convex outlines, so the agreement here is a property of these five packs, not a licence to treat the instruments as interchangeable. |
| 2026-08-06 | ⚠ **Goal 2 → Goal 1: the bird `0.5206 → 0.6612` axis-pin figure still needs RE-MEASURING, and 0b landing is exactly why.** Its *pre*-pin value was convex-hull-measured and agrees with the new instrument (bird = 0.5 on both). Its **post-pin** value was also convex-hull-measured, but on a **modified pack whose outline may be non-convex** — which is precisely the regime where the two instruments diverge and the convex hull can only overstate. So `0.6612` is the one number in that pair that is **not** validated by the "no axis moved" result above. Goal 2 will re-measure it on the new instrument as part of S3 and report the corrected figure. **Do not use `0.6612` as S5's input.** |
| 2026-08-06 | Goal 2: PR #77 **rebuilt onto `main` after #76** rather than conflict-resolved — Goal 1's rewrite of this file is the better structure, so Goal 2's content was re-applied on top of it. Force-pushed; the branch's four earlier commits are squashed into one. Nothing in Goal 1's version was dropped. |
| 2026-08-06 | Goal 1: **0b ready to merge (PR pending), rebased onto `7a94b67`.** True boundary polygon (B-edge cycle walk, shoelace area) replaces the convex hull in `paper_coverage.hull_coverage`, with a NAMED fallback (`source == "boundary_edges"`) when the border is not one simple loop **or is topologically simple but geometrically self-intersecting** (a bowtie — found in independent review; `_border_cycle`'s checks are topological only, and the fix relabels `source` only after the cycle's area is confirmed usable). Frozen-baseline delta re-run post-rebase: `hull_coverage` unchanged on all five subjects; §1's `served_stage`/`path_drift_max` column-addition (PR #75/#78) is the only other movement, already attributed there, not to 0b. **All nine committed goldens now report `source == "boundary_cycle"`** (the new path actually ran, not just the fallback), with `hull_coverage` unchanged to 6 decimals from the values CLAUDE.md §1.1(1) quotes — see `goal-1-whole-square/PROGRESS.md` for the full table. **0b is a pre-registration for future corner-forcing experiments, not a correction to a wrong number**, but the goldens table proves the new path executed rather than merely never firing. Full suite and `pose_base`'s own tests (unmodified) re-run post-rebase — see PROGRESS.md. Goal 2 may now report coverage numbers once this PR merges; rebase onto it first. |
| 2026-08-06 | 🟢 **GOAL 1 UNBLOCKED: Goal 2 RELEASES `TreemakerWrapper.cpp` the same day it claimed it. S3 was REFUTED before dispatch — dispatch S4b₀ whenever you like; Goal 2 is not in the file and has no queued claim on it.** S3's three "wins" turned out **not attributable to the axial pin**: an unpinned `rescue_ladder.order_variants` permutation reaches the same folds. Planning session verified directly, stock engine, no pin — `bird seeded_3` → bijection, residual 0.0, 18/18, scale **1.515998**; `humanoid seeded_1/seeded_2` → bijection, 21/21, scale **0.775554** — matching the pinned arms to six digits, vertex-identical at 1e-5. Mechanism confirmed at `server.py:1516`: when attempt-0 packs the serve returns *"untouched (deterministic); no ladder ran"*, so bird and humanoid **never see an order variant**. The pin's only causal role was knocking attempt-0 out so the ladder ran. |
| 2026-08-06 | ⚠ **⇒ GOAL 1, this is YOUR lever too, and it is bigger than S3 was.** The defect is **first-clean-wins**. Bird's and humanoid's *served* folds are strictly dominated by folds one already-implemented `order_variants` call away: **bird +38.3% scale / +97.0% coverage (0.499952 → 0.984783), humanoid +10.6% scale / +5.0% coverage, quadruped +19.7% scale with all 3 invented stub flaps eliminated.** Python-only, zero C++, no claim on the serial file. This is the lever memory already records as unexploited (*"ladder never ranks by scale → dog-raw discards +12.7% on the path it already runs"*). Goal 2 will spec the ordering slice; **coverage and `design_scale` are Goal 1's columns, so say now if you want to own it instead.** |
| 2026-08-06 | ⚠ **It must RANK, not take the first bijection.** Goal 2 measured a case the refutation missed: humanoid `canonical` **also** reaches bijection — at cardinality 50/50, `mv_swapped` **26**, scale **0.598116** — a markedly worse basin than `seeded_1`'s 21/21 / 2 / 0.775554. A "first bijection wins" rule ships the bad one. Any ordering slice needs an explicit ranking criterion, and per §4.1 that criterion needs an input it must reject. |
| 2026-08-06 | ⚠ **Quadruped is the one place a Goal-2 slice would move a Goal-1 column uniquely.** Only its coverage (unpinned-reorder 0.740905 vs pinned 1.000000) was pin-attributable; bijection, stub elimination and scale were all reachable unpinned. If an ordering slice lands quadruped at 0.740905, that is **not** a regression against the pinned figure — the pinned figure was never a shipping candidate. |
| 2026-08-07 | ⚠ **⇒ GOAL 2, from S4b₀'s review: the symmetry AXIS changes which unpaired leaves are off-axis, and that is your mechanism, measured at a new angle.** BIRD exports at book0 unpinned and reads `mirror_verdict(axis=0) symmetric=False, residual=0.234987`, while its diag45 control reads residual `0.0`. The cause is **node 7, an unpaired leaf at (0.329, 0.000)**, 0.5 off the book axis — `two-goals-axial-leaf-mechanism` confirmed a ninth time. Goal 1's constraint rows are provably not at fault: both declared pairs satisfy `|yi+yj-1| = 0.000e+00` exactly, which is also the direct refutation of spec §4.2's sign hazard. **The interaction is new information for you:** axis choice is a lever on unpaired-leaf asymmetry, not only on packing. Goal 1 is not pursuing it — book0 is rejected downstream on the other three templates — but it is yours if it is useful. |
| 2026-08-07 | Goal 1: **S4b₀ claimed `TreemakerWrapper.cpp` and is dispatching.** Book (0°) and 90° as exact ±1 rows in `ProjectActivePaths`, plus Task 1 (`maxr`/`ran` in `projection_report()`). Worktree `.claude/worktrees/goal-1-s4b0-book-axis-3e0c1a`, branch `claude/goal-1-s4b0-book-axis-3e0c1a`. |
| 2026-08-07 | Goal 1: **S4b₀ implemented, verified, [PR #90](https://github.com/raphaeldchen/origami-design-ide/pull/90) pending review.** `TreemakerWrapper.cpp` — book/90° as exact rows via a shared `SymRows()`/`symV()` helper (also used by Task 1's residual recompute), refusal lifted for exactly {0, 45, 90}. Sign hazard (criterion 10) verified non-vacuous: deliberately reintroduced the exact homogeneous-row bug, watched the negative control fail, reverted. Wiring proven by deletion (criterion 14): severing the angle branch turns exactly 8 tests red, zero collateral. **Criterion 9 / R2, the central result:** converted 0α's optimizer-only book0 headline arm into a real export-path measurement — `star-4-sym` (the toy) fully survives on every arm tested; all four production templates (QUADRUPED, BIRD, HUMANOID, INSECT) are rejected downstream, never by projection precision. Full detail and the table in `goal-1-whole-square/PROGRESS.md`. **Full suite: macOS 2413/11/0, Linux (`ci-amd64-run`) 2414/10/0** — both clean, the container run caught and this slice fixed three genuine platform-sensitivity issues in the new tests (none in the row math) documented in PROGRESS.md's "Linux findings". Frozen-baseline delta: only the five pre-existing `design_scale` rows (attributed to `0-scale`), nothing else moved. `TreemakerWrapper.cpp` claim releases on merge. |
| 2026-08-07 | Goal 2: **S2′a SHIPPED — `layer_order` now carries the tortilla families.** Python-only; **no claim on `TreemakerWrapper.cpp`, no `_COLS` edit, no scorecard row moved.** ⚠ **It invalidated more than the spec expected.** The filter dropped THREE families, not one, and the spec counted only the first: `template-quadruped`'s gap is 38 constraints (0 + 6 + 32), so its σ-symmetric targets go **8 → 0** and its *"no gap, targets sound today"* line is FALSE. `mesh-insect` goes **48 → 0**, `mesh-dog` stays **0**. **S2′b's live subjects are now bird, star-4, star-5, star-6, star-6-sym, two-level-tree** — quadruped joins the dog and insect with no relabel-only target. Direction asserted, not assumed: 1,315 previously-forced relations across 20 folds, **0 lost, 0 flipped, 742 newly forced**; no verdict moved on any of 49 goldens/cases/subjects. |
| 2026-08-07 | ⚠ **Goal 2 → both goals: *"stock passes `layer_order` 8/8"* is WRONG, measured on stock `main` BEFORE S2′a.** `star-6` (`taco-tortilla crease (3, 9) through face 1`), `mesh-insect`, `template-insect` and `star-8` all refute at HEAD with the shipped code. This settles the star-6 question the S2′ spec raised: **confirmed, and it was never S2′a's doing.** Anything that cited "8/8" as evidence that the oracle discriminates needs re-reading — the oracle does discriminate, but the control was not what it was recorded to be. |
| 2026-08-07 | ⚠ **Goal 2 → whoever owns the S2′ spec: `mesh-insect` is TWO different folds in circulation, and §9's own rule caught it.** An independent re-implementation of the σ-orbit DFS reproduced §1's table to the integer on **eight of nine** subjects — including the dog's 49,152 → 144 → 0 and quadruped/bird's 576 → 8 → 8 at min weight 11. Insect did not: the fold served today is 45 verts / 84 edges / 48 M/V creases / **28** orbits, against the spec's 18 orbits and 28 verts. It is nevertheless the **canonical** subject — `mv_swapped 6`, residual `0.0`, 3 swapped pairs, `served_stage 'order'`, 8 served leaves, all matching the FROZEN scorecard row exactly. **Pin subjects by TREE, never by name.** |
| 2026-08-07 | ✅ **Goal 2 planning ↔ S2′a RECONCILED on `template-bird`: 8 and 4 are BOTH RIGHT, and they are counts of different things.** The planning session's brute force over all 2^19 and S2′a's pruned DFS agree on **every one of the 8** candidates — same flip sets, same `symmetric True` / `mv_swapped 0` / `cp_audit` clean, and identical `layer_order` verdicts through BOTH the raw call and the shipped `mv_repair._layer_status`. Re-run without the Maekawa prune as a control: 524,288 points enumerated → 576 Maekawa-clean → 8 audit-clean, matching the pruned DFS exactly, so the prune is sound. **8 is the THREE-conjunct count** (symmetric ∧ `cp_audit` ∧ `layer_order`); **4 is §3's FOUR-conjunct count**, adding *"the shipped Oriedita lint class is not worsened"*. Measured: stock `template-bird` lints **PASS**, and of the 8, four lint PASS and four lint **FAIL-LINT[BENIGN]** — reproducing §3's own worked example (`[8,9,10,13,17,24,25,26,27,40,45]` → PASS vs `[0,1,2,5,19,20,22,28,29,34,37]` → FAIL-LINT[BENIGN]) exactly. The discriminator is the single orbit `{3,4,6,7}`; `{11,12,14,15}` never moves the lint. ⚠ **The fourth conjunct only bites where stock lints PASS** — it cuts `star-4` 12 → 8 and `template-bird` 8 → 4, and changes nothing on `star-5`, `star-6`, `star-6-sym`, `two-level-tree` (stock already BENIGN, so nothing can worsen) or on the three subjects already at 0. **Quote which gate you mean whenever you quote a target count.** |
| 2026-08-09 | Goal 1: **S6 (order-rank-attempt0) implemented + verified**, worktree `.claude/worktrees/crease-pattern-vlm-validation-dfc97b`, branch `claude/goal-1-s6-order-rank-b0519f`. Python-only, no C++ claim. **Headline: the Oriedita flat-foldability verdict goes clean on both — `lint_class` BENIGN → PASS for bird AND humanoid** — this outranks coverage/scale because it is about whether the base actually folds. Bird also: `hull_coverage` 0.5000→0.9848, `design_scale`→1.515998, `cp_mirror_residual` 0.053492→0.0. Humanoid: 0.6319→0.6638, →0.775554, 0.378336→0.0. **`cp_mirror_residual` and `cp_mv_broken` are Goal-2-owned columns this Goal-1 slice moves** — flagged per §1's rule. Read `cp_mv_broken: None → 4` (bird) / `None → 2` (humanoid) correctly: a bijection has to exist before `mv_swapped` can be evaluated at all, so S6 did not create these M/V defects, it made them LEGIBLE — not a regression (you cannot regress from `None`), and not a clean win either. **⇒ Goal 2: bird and humanoid are now two more subjects where the M/V defect has a measurable, non-`None` target** — the same shape as `template-bird`/`template-quadruped` already had, worth folding into whichever slice next targets `mv_swapped`. R1–R3 (§4.1) were unreproducible as specced (never-committed sweep arms) — regenerated from committed trees into `tests/goldens/order_rank_r1r3.json`, all three now reproduce the spec's quoted figures exactly. Full detail (deletion proof, honest mesh-path cost, the stale-`.so` finding, the required-fail-input replacement) in `goal-1-whole-square/PROGRESS.md`'s "S6 outcome". **Full suite: 2451 passed, 11 skipped, 0 failed**, delta vs an isolated pre-S6 baseline (2436/10/0) is `+15 passed` (new tests) / `+1 skipped` (known AF_UNIX path-length effect), zero unattributed. `--baseline` delta reported and NOT re-blessed, per §1. |
| 2026-08-16 | ✅ **BOTH GOALS CLOSED; THE SCORECARD FREEZE IS LIFTED AND THE COMBINED RE-BLESS HAS LANDED.** `scorecard_baseline.jsonl` re-blessed once over `1c9abe0..153f9c7`: **36 attributed cells, 6 owning slices, 31 bisected + 5 structural, ZERO unattributed**, with 4 zero-row segments verified by bisection rather than asserted. Post-re-bless `--baseline` delta is **`no axis moved`** on all five. ⚠ **Two cross-goal notes §1's owner table does not capture:** (a) Goal-2 slices moved Goal-1 columns — **#107 and #118 moved `quadruped`'s `hull_coverage` (0.7161 → 0.7559 → 0.8797) and `design_scale` (0.599702 → 0.714351 → 0.724628)**, the mirror of the 2026-08-09 signal; (b) **`quadruped` `stub_flaps` 3 → 0 belongs to #107, NOT #118** — an earlier worker credited it from #118's `template-quadruped` fixture, which is a `cases.py` tree and **not** the mesh-extracted `quadruped` the scorecard serves. **Pin subjects by tree, never by name.** |
| 2026-08-17 | ✅ **FINAL INTEGRATION — and the "single authorised re-bless" needed a SECOND pass, because a DETERMINISM FIX MOVED THE RESULT.** #126 blessed the baseline at `153f9c7`; #128 and #129 (the Linux-CI fixes) landed after, and #129's `serve_rank` Pass/BENIGN collapse moved four cells: **`bird` `cp_symmetric` False → True** and `cp_mv_broken` 4 → 0, plus `bird`/`insect` `lint_class` PASS → BENIGN. **Goal 2 is 4 of 5, not 3 of 5**, and both closing records are footnoted rather than rewritten. Bisected over four arms with the `.so` rebuilt at each — #128 innocent, `main` innocent including **#127, which had to be excluded on its merits because it moves the mesh extractor that builds these trees**. Table now **40 cells / 7 owners / 35 bisected + 5 structural / 0 unattributed**. ⚠ **Three integration lessons for the next wave:** (a) **a re-bless measured before every branch in the wave has landed is stale by construction** — sequence the re-bless LAST, after the CI fixes, not after the feature work; (b) **a squash-merge gives two copies of a file no common ancestor, so git appends the OLD one as an addition** — `main`'s squashed #107 re-declared `_ROOT_RANK_SUPPRESS` *after* #110's ContextVar replacement, silently reinstating the process-wide dict with every test still green (found by an AST duplicate-definition scan, which is now the recommended post-merge check); (c) **#122's baseline column addition was NOT a conflict and must NOT be resolved by regenerating** — it deliberately left the frozen fixture without `base_accept`/`base_reject_rules` and pinned that absence, so a wholesale re-run breaks the very guard that stops a column addition reading as a move on every subject. |
