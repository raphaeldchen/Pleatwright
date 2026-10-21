# Goal 1 — whole-square design: PROGRESS

> ## ✅ THIS GOAL IS CLOSED. **Read the CLOSING RECORD (2026-08-15) at the
> ## bottom of this file first** — everything above it is the working history
> ## that led there, and one earlier closing record (2026-08-14) is SUPERSEDED.
>
> **The one-line answer:** coverage moved on **3 of 5** subjects, mean
> `hull_coverage` **0.7230 → 0.8591**, and it stops there for a *structural*
> reason — the creased region is by construction the convex hull of the leaf
> nodes and the optimizer objective has **no coverage term**. Both levers that
> ever moved it were changes to the problem instance handed to the packer:
> node **ORDER** and node **ROOT**. **Do not plan a sixth cheap lever.**

**Recovery map for the planning session.** Assume context is compacted; this
file plus the spec is enough to resume.

- **Branch new work from:** `d035943` (main). **Main is GREEN.**
- ⚠ **Do NOT read repo files from `<repo>`
  directly** — that checkout is parked on an unrelated branch and is many slices
  stale. It cost the planning session three wrong readings in one session,
  including a `paper_coverage` with no `_border_cycle` and a golden reporting
  the pre-0b `source`. Read from a worktree that is actually on current `main`,
  or via `git show origin/main:<path>`.
- ~~**Measure against:** `1c9abe0` — the FROZEN scorecard baseline. It does NOT
  advance when a slice merges.~~ ✅ **RETIRED 2026-08-16 — the freeze is
  lifted.** The baseline was re-blessed once, spanning `1c9abe0..153f9c7`,
  with a per-cell attribution table in its own `_meta`. Measure against the
  **current** `mcp_harness/fixtures/scorecard_baseline.jsonl`. What did NOT
  retire is the rule the freeze existed to enforce: **every moved cell
  attributed, no unattributed re-bless.** See "THE OPEN CROSS-GOAL ITEMS" §2.
  ⚠ **RE-BLESSED A SECOND TIME 2026-08-17**, four cells, owner **#129**,
  bisected — the 2026-08-16 pass was measured at `153f9c7` and therefore
  predated #128/#129. **No Goal-1 column moved:** `hull_coverage` and
  `design_scale` are byte-identical on all five subjects, on both platforms, so
  the headline below stands unchanged. What moved is Goal 2's — `bird` is now
  mirror-symmetric (4 of 5). The table is now 40 cells / 7 owners / 35 bisected
  + 5 structural / 0 unattributed. **The transferable lesson is about
  SEQUENCING: re-bless after the whole wave has landed, including its CI fixes,
  because a determinism fix can move the result it was meant to stabilise.**
- **Spec:** [`docs/superpowers/specs/2026-08-04-whole-square-axis-projection-design.md`](../../specs/2026-08-04-whole-square-axis-projection-design.md)
- **Evidence:** [`docs/superpowers/evidence/2026-08-04-axis-corner-capacity/`](../../evidence/2026-08-04-axis-corner-capacity/)
- **Cross-goal:** [`COORDINATION.md`](../COORDINATION.md) — the frozen scorecard,
  the serial C++ file, and S5's double gate live there, not here.

---

## The goal in one paragraph

Every model folds from one uncut square and the folder receives the whole sheet,
but the crease pattern reaches only the convex hull of the leaf positions —
bird 0.5000, humanoid 0.6319, quadruped 0.7161, insect 0.8595, fish 0.9077.
Done means: models reach more of the square, **and** the system can state how
much, **and** it can argue that against design scale instead of moving it
silently.

⚠ **Those are the GOAL-START figures and they are kept as the goal's starting
line, not as current state.** The serve path now reads bird 0.9848, humanoid
0.6638, quadruped 0.8797, insect 0.8595, fish 0.9077. ⚠ **And the framing
sentence turned out to be the answer, not the problem:** "the crease pattern
reaches only the convex hull of the leaf positions" is not a limitation to be
engineered away — it is `tmTree::CalcBorderNodesAndPaths` doing exactly what
Lang and Demaine specify. See the closing record.

## The finding the goal is built on

**The symmetry axis caps corner occupancy.** A paired leaf can only take a
corner whose mirror image is also a corner: the diagonal supplies **two**, book
supplies **four**. At the optimizer, two pairs → four corners **fails on 5 of 5
subjects at diag45** and **succeeds on 5 of 5 at book0**, reaching leaf hull
`1.000000` with four corners, four of them at higher scale (star-4-sym +41.4%,
HUMANOID +22.2%, BIRD +11.4%, QUADRUPED +7.9%, INSECT −10.4%). Every one is
unreachable today because `ProjectActivePaths` re-symmetrizes about `y = x`
regardless of the requested angle.

⚠ **SUPERSEDED 2026-08-07 — the paragraph above is the premise the goal STARTED from, and S4b₀ refuted it on the export path.** Converting the book readings was S4b₀'s job; it is done and the answer is negative. 3 of 4 production templates do not export at book0 at all; BIRD does and is not symmetric about the book axis (unpaired leaf). **The dead lever is corner pinning, not the axis** — dead at diag45 in the optimizer and at book0 downstream. See "S4b₀ review" at the end of this file. Kept, not deleted, because the goal's whole shape follows from it.

---

## Status

| # | slice | model | state |
|---|---|---|---|
| — | spec + evidence | — | ✅ **landed** 2026-08-04 |
| 1 | **S4a′** — verify pins; refuse non-45° + non-square; classify the projection error; expose the margin proxy | Sonnet, high | ✅ **merged** 2026-08-04 (worktree `.claude/worktrees/goal-1-s4a-projection-guards`, branch `claude/goal-1-s4a-projection-guards`) |
| 2 | **S4b₀** — book + 90° as exact ±1 rows. **Task 1 is now `maxr` + `ran` in `projection_report()`** (see below) | Sonnet, high | ✅ **implemented + verified 2026-08-07** (worktree `.claude/worktrees/goal-1-s4b0-book-axis-3e0c1a`, branch `claude/goal-1-s4b0-book-axis-3e0c1a`), [PR #90](https://github.com/raphaeldchen/origami-design-ide/pull/90) pending review. See "S4b₀ outcome" below |
| 3 | **0α** — probes → fixture; edge-pin arms; unequal-tree order control; margin-to-cliff | Sonnet, medium | ✅ **merged** 2026-08-05 (worktree `.claude/worktrees/perfect-base-slices-s1-c2c889`, branch `claude/goal-1-0alpha-premise-probe-2be0bc`) |
| 4 | **CLAUDE.md §1.1(2)+(4) edit** | planning session | ✅ **merged** 2026-08-05 (PR #76) |
| 5a | **0b** true polygon coverage — standalone, Goal 2's shared instrument | Sonnet, medium | ✅ **merged** 2026-08-06 (PR #81). Independently re-verified by the planning session; **Goal 2 may now report coverage numbers.** |
| 5b | **`0-scale`** — `design_scale` column + the shared `scale=` parser. ⚠ **Renamed from `0a`**: `0a` and `0α` differ only by alphabet, branch names flatten the Greek (`…-0alpha-…`), and the two WERE mistaken for each other in review. `0α` is merged with its name in commits and branches, so the **undone** slice is the one that moved. | Sonnet, medium | ✅ **implemented + reviewed** 2026-08-06 — every number reproduced independently; **not yet committed** at review time. See "0-scale review" below |
| 5c | **0c** display badge | Sonnet, medium | ✅ **merged** 2026-08-07 (PR #87, `64598bd`). Reviewed; one real defect found and fixed before merge. See "0c review" below |
| 6 | **S5** — axis selection, coverage vs scale as an argued trade | Opus, high | ⛔ **double gate**: S4b₀ reported **AND** Goal 2 S3 merged **AND** re-measured. ⚠ **`0.6612` is NOT S5's input** — Goal 2 (PR #83) withdrew the bird `0.5206 → 0.6612` axis-pin figure: the *post*-pin half was convex-hull-measured on a modified pack whose outline may be non-convex, exactly where the two instruments diverge and the convex hull can only overstate. Goal 2 re-measures it under 0b as part of S3. ⚠ **And `design_scale` is a within-subject signal only** — see "0-scale review" below before writing the coverage-vs-scale argument |
| 7 | **S4b-general** — arbitrary angle | ~~Opus, max~~ | ❌ **CANCELLED 2026-08-07.** Its gate cannot be met: neither 0° nor 90° pays, and the rejection is a packing-topology problem (invalid polygon partition / multiple IBPs), not angle representability. See "S4b₀ review" |
| 8 | **S6 — order-rank-attempt0** — `order_variants` reaches bird **0.9848** coverage on the SHIPPED 45° axis, Python-only, no C++ | Sonnet, high | ✅ **implemented + verified 2026-08-08/09** (worktree `.claude/worktrees/crease-pattern-vlm-validation-dfc97b`, branch `claude/goal-1-s6-order-rank-b0519f`). Bird reproduces **exactly**: coverage 0.5000 → **0.9848**, scale → **1.515998**. See "S6 outcome" below |
| 9 | **S8 — order-pool-width probe** — does widening `ORDER_RESTARTS=4` change the RANKED winner (not just rescue)? READ-ONLY, no production edit | Sonnet, medium | ✅ **measured 2026-08-10** (worktree `.claude/worktrees/goal-1-s8-pool-width-probe-6f700d`, branch `claude/goal-1-s8-pool-width-probe-6f700d`). **Yes, sometimes**: 4 of 21 rankable `tests/cases.py` subjects change ranked winner at k≥8, always improving scale/bijection (never coverage-for-free — §1.1(4) still holds inside one lever). Superset property PASS 25/25; no subject dedup-saturates by k=20. See "S8" below |

**Cancelled / out of scope, with reasons in spec §9:** S4c (boundary rows in the
projection — R8 falsified by measurement); a boundary rung in the rescue ladder
(ceiling is the tangency cliff, folded into 0α as measurement); the k=7 rescue
(recorded, not chased); ladder scale-ranking (real, justified on scale alone,
**never** as a coverage lever).

---

## Decisions taken, so they are not re-litigated

1. **CLAUDE.md §1.1(2) is wrong in its prescriptive claim and its own example.**
   *"k=4 puts 4/4 at the corners and scores coverage 1.000"* holds for the
   **unpaired** `star(4)`; the **paired** one reads coverage `0.500000` with
   **zero** corners. The headline is unpaired-only; the product is paired.
2. **CLAUDE.md §1.1(4) attaches Lang's 0.323/0.353 to the wrong arms.** This
   engine's *unconstrained* solve lands on 0.323556 (Lang's worse, all-on-edge
   basin) and corner-pinning reaches 0.353553 = 1/(2√2) with coverage 1.000.
   **The rule survives and strengthens** — the trade has no fixed sign — but the
   supporting example is backwards.
3. **Coverage and scale are independent.** All three sign combinations measured.
   `bbox_area = 1.000000` on every packing arm, so coverage is purely outline
   shape, never pattern size.
4. **R8 is falsified.** Boundary pins survive the projection (worst 5.83e-07).
   Closed **narrowly**: for a clamp-specific reason (a pin at 0 or `w` sits on
   the per-iteration clamp). Does **not** generalize to interior pins, and
   emphatically not to "the projection preserves constraints" — the symmetry
   rows preserve the *wrong* mirror perfectly.
5. **S4b₀ needs no trig.** Lang's `PairFn1A`/`PairFn1B` evaluated at 0/45/90 on
   square paper give exact integer rows. The 45° pair is an **identity** with
   the shipped rows, independently re-derived by the reviewer.
6. **Non-square: refuse, don't fix.** The correct constants are recorded in spec
   §4.2 so a later slice lifts the refusal deliberately.

## Errors this session made, recorded so they are not repeated

- **Built the wrong tree** (`star(4)`, unpaired) to check a claim about
  `symmetric_pairs_star(4)`, and briefly concluded the record's number did not
  reproduce. It reproduces to six digits.
- **Ran a vacuous control**: order-restarts measured on an equal-flap star,
  where permuting identical leaves is a relabeling. The exact "measured in the
  regime where it cannot fail" error. **0α owes the rerun on an unequal tree.**
- **Filed R8 as a risk rather than measuring it**, and let it drive a proposed
  reordering, when the measurement took twenty minutes and closed it.

---

## Traps that cost time here

- **`build.sh` defaults to `PYTHON=python3`** → a Homebrew interpreter without
  `pybind11` → **exits producing no `.so` and no obvious failure**. The worktree
  has no `.venv` of its own. Use
  `PYTHON=<repo>/mcp_harness/.venv/bin/python ./build.sh`.
- **The shell cwd is `mcp_harness`, not the repo root**, and `tests/` is
  `mcp_harness/tests`. Use absolute paths in anything long-lived.
- A bare `HeadlessTreemaker` compile is **not** the serve path — it is attempt-0
  for one exact node list. Right instrument for a variant × angle grid; wrong one
  for an acceptance pin. Any script calling `draft_and_compile_full_base` must
  sit under `if __name__ == "__main__":`.
- Full suite: `cd mcp_harness && PYTHONPATH=.:tests <venv python> -m pytest
  tests/ --timeout=420`. Bare `make test` never terminates. ~14 min, looks
  stalled early at near-zero CPU — do not kill it. **~19–29 min.** Count at
  `773982a`: **2385 / 11 / 0** deep path, **2386 / 10 / 0** short — the ±1 is the
  AF_UNIX `sun_path` effect, seen six times including CI-vs-local. Not a bug.
- Verify C++ on Linux in the `ci-amd64-run` container **before** merge. Check
  host CPU for orphans first.

---

## S4a′ — merged 2026-08-04

Four changes, all in `mcp_harness/TreemakerWrapper.cpp` (`ProjectActivePaths`,
the three `set_node_*` setters, the `BuildAndExport` call site) plus two
appended `error_recipes` codes:

1. **Refuse a non-45° symmetry axis** when mirror rows are actually emitted
   (gated on `!syms.empty()`, not `HasSymmetry()` — an angle with zero pairs
   is genuinely harmless). Both directions tested.
2. **Refuse non-square paper** under the same gate; fixed the routine's own
   stale comment (claimed the diagonal was "through the paper center" for any
   `w`/`h`, false for `w ≠ h`) — a spec §4.1(2) requirement the plan's own
   steps had omitted, caught by comparing spec against plan before editing.
3. **Verify (never refuse) boundary pins.** R8 stays falsified: measured
   `pin_max_displacement = 0.0` on the star-5 four-corner arm (reproduces
   probe_4's `0.00e+00` exactly) and `6.6300e-10` on the star-6 four-edge arm
   (matches probe_4's `6.63e-10`).
4. **Stop discarding `outIters`/`outCons`** at the production `BuildAndExport`
   call site; expose both plus the pin ledger via a new `projection_report()`
   binding.

**Verification, not adjectives:**
- Full suite (macOS, this worktree): **2256 passed, 11 skipped, 0 failed**
  (2241 baseline + 15 new), 944.01s.
- Full suite (Linux, `ci-amd64-run` container, source copied not
  bind-mounted): **2257 passed, 10 skipped, 0 failed**, 1354.22s (22:34,
  amd64-on-arm64 emulation). The 2257/10 vs 2256/11 is **not** a regression:
  `test_rigid_collision_evidence.py::…[member_socket]` binds an AF_UNIX socket
  to `Path.cwd()`, which exceeds macOS's `sun_path` limit under this
  session's deeply nested worktree cwd (skip) but fits under the container's
  short `/repo` cwd (pass) — the exact mechanism memory
  `worktree-borrowed-so-inflates-failures` already recorded. Zero failures on
  either platform.
- Nine committed geometry goldens byte-identical (0 failures on either
  platform run — a golden regression would have shown as a failure). The ODR
  hazard (`GetSymAngle()` in two shadowed `tmTree.h` headers) is **not live**
  for `TreemakerWrapper.cpp`: `test_vendor_header_hygiene.py` (S5) already
  pins that only `tmStubFinder.cpp` was ever affected, and it fully qualifies
  its include; traced independently and confirmed the guard does not misfire
  at 45°.
- Frozen-baseline delta (`fixtures/scorecard_baseline.jsonl`, not
  regenerated): **`no axis moved: quadruped, bird, humanoid, fish, insect`.**
  Not even `error_codes` moved — none of the five subjects' current failures
  are one of the two new projection classes.
- All three "count-based test is not a pin" deletion checks performed and
  recorded in the plan: deleting `PROJECTION_UNSUPPORTED` /
  `PROJECTION_INVALID` from `error_recipes._MATCHERS`, and reverting the
  out-param pass-through at the `BuildAndExport` call site, each turned
  exactly one test red with no collateral, confirming the wiring (not just a
  count) is what the tests pin.

**Plan discrepancy found and corrected in place:** the plan's Task 1 steps
never included the spec §4.1(2) stale-comment fix, even though the plan's own
self-review table claimed Task 1 covered it. Fixed as a comment-only,
zero-risk edit; flagged rather than silently absorbed.

Full detail, every observed number, and the exact deletion-check output are
recorded inline in
[`docs/superpowers/plans/2026-08-04-s4a-projection-guards.md`](../../plans/2026-08-04-s4a-projection-guards.md).

---

## S4a′ review findings — carried, not blocking

The planning session re-ran every claim on its own build. Zero discrepancies
between report and reality. Four findings survive, none a regression:

1. **`iters` saturates at `maxIters = 50`, so the margin proxy is censored.**
   Measured via `debug_active_path_report`, byte-identical before and after
   S4a′ (so **pre-existing, revealed** by the new instrument on its first use):

   | tree | residual before → after | iters |
   |---|---|---|
   | **star-4-sym** | 2.031e-09 → **1.717e-09** | **50 = the cap** |
   | **star-5** | 2.489e-09 → **2.233e-09** | **50 = the cap** |
   | HSHAPE | 2.933e-09 → 1.110e-16 | 1 |
   | QUAD | 9.535e-09 → 0.000e+00 | 1 |
   | TEMPLATE_QUADRUPED | 2.384e-09 → 5.551e-17 | 1 |
   | TEMPLATE_HUMANOID | 6.340e-09 → 7.361e-14 | 22 |

   `50` cannot be told from "converged on the 50th step", and `star-4-sym` is
   the +41.4% case S4b₀ exists to convert. **Fix = expose the loop's final
   `maxr`. Assigned to S4b₀ as its Task 1**, because the file is serial and a
   separate claim would make Goal 2 wait twice.

2. **The routine's own precision claim is false on those trees.** Its comment
   says *"a handful of iterations drive the residual to ~1e-13"*; on
   `star-4-sym` it runs 50 iterations for a **15% total reduction**, four orders
   short. `star-4` is in `GOLDEN_CASE_NAMES`. Pre-existing; spawned as its own
   task. Adds a second reason the *"~1e-9 drift, so it's only a polish"* reading
   was wrong — on these trees it is not achieving the polish either.

3. **`projection_report()` cannot say "the projection did not run."** After a
   failure at the pre-projection polygon gate the dict returns anyway, and
   `cons` is assigned *before* the `cons.empty()` early return, so it is not a
   usable sentinel. Unreachable today (one engine per compile in production, and
   **engine reuse SIGSEGVs — verified pre-existing, reproduces at `c60840d`
   with no pins at all**). Closes with a `ran` flag beside finding 1.

4. **The 2256/11 vs 2257/10 skip split is path length, not platform.**
   Reproduced 2257/10 **on macOS** from a 46-character worktree path against
   107. `test_rigid_collision_evidence[member_socket]` binds an AF_UNIX socket
   under `Path.cwd()` and overruns `sun_path`. Matches memory
   `worktree-missing-build-artifacts`; do not hunt a Linux-specific cause.

**Also live but invisible:** `PROJECTION_UNSUPPORTED` / `PROJECTION_INVALID`
classify correctly but no scorecard subject currently trips either, which is why
`error_codes` moved nowhere. The first row that ever trips them moves a frozen
column and **belongs to S4a′ retroactively.**

---

## 0α — merged 2026-08-05

One instrument, `mcp_harness/probe_axis_corner_capacity.py`, forked from
`probe_symmetry_axis.py`, replacing the five ad-hoc evidence scripts under
`docs/superpowers/evidence/2026-08-04-axis-corner-capacity/`. Writes
`mcp_harness/fixtures/axis_corner_capacity.json`. Adds no scorecard column,
moves no scorecard row — an instrument, not a product change.

**All six committed-evidence numbers reproduced exactly** on this worktree's
engine `.so` (macOS/Accelerate, arm64):

| arm | reproduced |
|---|---|
| `star-4-sym` diag45 free | scale 0.353553, leaf hull 0.500000, 0 corners ✅ |
| `star-4-sym` book0, 2 pairs → 4 corners | scale 0.500000, leaf hull 1.000000, 4 corners ✅ |
| all five subjects, diag45, 2 pairs → 4 corners | **FAIL**, `scale optimization did not converge (reason code 1)` ✅ |
| all five subjects, book0, 2 pairs → 4 corners | **OPT**, leaf hull 1.000000, 4 corners ✅ |
| star-5 free vs 4 corners (export) | 0.323556/0.703897 → 0.353553/1.000000 ✅ |
| star-6 four-edge one-equality pins | `pin_max_displacement` = 6.629976567751328e-10 ✅ |

**The non-vacuous order-restart control (Task 2) — MIXED, and worth stating
plainly.** Reran the planning session's control (previously vacuous: it
permuted `star(5)`'s five *identical* 1.0-length leaves, so 12/12 identical
results were a relabeling, not a finding) on three trees with genuinely
distinct leaf lengths, ≥12 orderings each via the shipped order lever
(`rescue_ladder.random_topo_order`):

- **`uneven-star-5`** (lengths 0.2/0.3/0.4/0.5/0.6, unpaired): best order-restart
  scale **0.946973** *exceeds* the corner-pinned reference **0.708652**
  (2-corner pin; the naive 4-corner pin fails to converge here,
  `POLYS_MULTIPLE_IBPS` — itself the same failure mode Group 2 shows on some
  equal-length stars). **Order restarts alone reach further than corner
  pinning on this tree.**
- **`HUMANOID`** (paired): best order-restart scale **0.682489** *falls short*
  of the corner-pinned reference **0.769231** — but that reference is itself
  an **optimizer-only** (book0, non-45°) reading, because diag45 corner-pinning
  does not converge on this tree at all, so no real-pack reference exists to
  compare against.
- **`BIRD`** (paired): same pattern — falls short (0.652542 vs 0.726750
  optimizer-only book0 reference).

**Verdict:** order restarts are not a uniform substitute for corner pinning —
they beat it on the unpaired asymmetric star and fall short on the two paired
templates tested. On the paired templates the comparison is against an
optimizer-only reading (no real pack exists to compare against at all under
diag45), which is itself informative: **the corner lever's headline
(diag45 fails to converge, book0 doesn't) cannot even be checked against a
real-pack order-restart baseline until S4b₀ makes book0 an export-capable
axis.** The corner lever is not shown to be redundant with the shipped order
mechanism.

**Margin-to-cliff (Task 3).** `QUAD` calibration point: scale 0.717008473909996
(macOS/Accelerate basin, matches memory's 0.717008 to six digits), 1 GN
iteration, 3 constraints. Every exporting arm records `proj_iters`/`proj_cons`/
`pin_max_displacement`; rows where `proj_iters == 50` are marked
`margin_proxy_censored: true` — measured on `star-4-sym` and `star-5`, exactly
the trees S4b₀'s headline depends on, matching the S4a′ review finding above.
The residual itself is not exposed by this slice; that is S4b₀'s Task 1.

**Fixture pin proved by breaking it (Task 4).** Flipped `star-4-sym`'s diag45
four-corner row from `FAIL` to `OPT` in the committed fixture and reran:
`test_the_diagonal_cannot_seat_four_paired_corners` went **RED**
(`[('star-4-sym', 'OPT'), ('QUADRUPED', 'FAIL'), ('BIRD', 'FAIL'),
('HUMANOID', 'FAIL'), ('INSECT', 'FAIL')]`), confirming the test pins the
row's content, not just its presence. Restored via `git checkout`.

**Verification:**
- Full suite (macOS, this worktree): **2260 passed, 11 skipped, 0 failed**
  (2256 S4a′ baseline + 4 new fixture-pin tests), 941.75s.
- Frozen-baseline delta (`fixtures/scorecard_baseline.jsonl`, not
  regenerated): **`no axis moved: quadruped, bird, humanoid, fish, insect`.**

**Finding, not chased further:** `star-7` does not build unpinned (Group 2:
`free` → FAIL, `POLYS_MULTIPLE_IBPS`) and does build corner-pinned (`4
corner(s)` → PACK, coverage 1.000000). Recorded in the fixture per the plan's
explicit instruction not to extend the probe hunting for more rescue-shaped
results (memory `rescue-ladder-vs-alignment-tool`).

**One probe-authoring bug caught by cross-checking against the committed
evidence, not shipped:** the child script's first draft never imported
`paper_coverage`, so every `export=True` arm read `NameError` as its failure
reason instead of a real compile outcome. Caught because acceptance criterion
5 (`star-5` free/4-corner) did not reproduce on the first run; fixed before
the fixture was committed.

## 0α review findings — the fixture stands, the verdict does not

Re-measured by the planning session on its own rebuilt `.so` (macOS/Accelerate,
arm64) at `a04cb0a`. **Everything the report claimed as a measurement
reproduced.** All six acceptance numbers, `star-6`'s
`pin_max_displacement = 6.629976567751328e-10`, and the fixture-break proof
(flipping `star-4-sym`'s diag45 four-corner row turns exactly
`test_the_diagonal_cannot_seat_four_paired_corners` red; restored clean). The
control is genuinely **non-vacuous**: 12 / 10 / 12 *distinct* scale values
across the orderings on `uneven-star-5` / `HUMANOID` / `BIRD`, driven through
the shipped `rescue_ladder.random_topo_order` rather than a hand-rolled
permutation. The vacuity that killed the planning session's own control is
fixed at the mechanism, not papered over.

**What does not stand is the verdict, for two reasons that compound.**

**1. The two arms were given different N.** The order lever got 12 restarts;
the corner lever got **one** — pins were only ever applied to the canonical
ordering. Crossing the two levers on the same tree, the same export path, and
one common set of 64 distinct orderings (seeds 7000–7089 + canonical), best
arm selected **by coverage**:

| arm | packed | best coverage | corners @ best | scale @ best |
|---|---|---|---|---|
| order restarts, **no pins** | 43/64 | 0.923838 | 3 | 0.919577 |
| order restarts **+ 1 corner pin** | 50/64 | 0.923838 | 3 | 0.919577 |
| order restarts **+ 2 corner pins** | 14/64 | **0.979973** | 2 | 0.894741 |
| order restarts **+ 4 corner pins** | 0/64 | — | — | — |

The levers **compose**: two pins buy **+5.6 coverage points** on top of a
fully-exercised order lever. The reading is *conservative*: the 2-pin arm beat
the no-pin arm from **14** packing draws against **43**, and more draws can
only help a best-of. Two caveats to carry: these are `hull_coverage` numbers,
i.e. the **convex** hull, which 0b is replacing precisely because it can only
overstate a non-convex outline — the absolute figures are upper bounds and
should be re-read after 0b lands, though both arms share the metric so the
*ordering* between them should survive. And this is **one** unpaired 5-leaf
tree; it is not yet shown on a paired production template. `REACHES/EXCEEDS` on `uneven-star-5` is an
artifact of unequal N, and **MIXED's positive arm does not survive an equal-N
comparison.** This *strengthens* the corner lever — S4b₀'s justification is
unaffected, and the record must not be left saying the opposite. Two honest
qualifiers: one pin is **inert** (identical to free at the optimum), and the
best-coverage arm occupies **2** corners while a 3-corner arm scores lower —
coverage and corner count are **not** monotone in each other.

**2. The verdict was decided on `scale`; this goal is about `coverage`.**
`corner_pinned_reference` records only `scale`, so no other comparison was
available to it. On `uneven-star-5` the reference arm is `export=True` and
PACKs, so its coverage *was* measurable and was discarded — it reads
**0.791191** (2 corners, scale 0.708652) against the free canonical arm's
0.807930 (1 corner). The one tree where the comparison is clean and fully
exportable was measured on the wrong axis.

**On the paired templates the comparison changes three variables at once.**
The order arms run diag45 + no pins + `export=True`; the reference is book0 +
4 pins + `export=False`. Axis, pins, and export path all differ; the probe's
comment names only the export mismatch. Since the axis change *alone* moves
scale +7.9% to +22.2%, `FALLS SHORT` on `HUMANOID`/`BIRD` may be reading the
axis rather than the corners. **The clean within-axis control is already in
the fixture and was never used** — and it is the most valuable result in it:

| subject | diag45 free | book0 **free** | book0 **+ 4 pins** |
|---|---|---|---|
| | scale / hull / corners | scale / hull / corners | scale / hull / corners |
| `star-4-sym` | 0.353553 / 0.500 / 0 | **0.500000 / 1.000 / 4** | 0.500000 / 1.000 / 4 |
| `QUADRUPED` | 0.667979 / 0.681 / 2 | 0.612039 / 0.695 / 1 | 0.720456 / 1.000 / 4 |
| `BIRD` | 0.652542 / 0.669 / 2 | 0.599416 / 0.695 / **0** | 0.726750 / 1.000 / 4 |
| `HUMANOID` | 0.629445 / 0.559 / 0 | 0.788309 / 0.776 / 2 | 0.769231 / 1.000 / 4 |
| `INSECT` | 0.763400 / 0.789 / 2 | 0.770078 / 0.870 / 1 | 0.683946 / 1.000 / 4 |

**`star-4-sym` is the only subject where the axis alone seats four corners** —
and it is the toy. On all four production templates book0-free reaches **0–2**
corners, and diag45-with-pins FAILs outright. **Both levers are necessary and
neither is sufficient.** That is the sharpest justification S4b₀ has, and it
also settles the scale question with a cleaner within-axis control than the
spec had: pins **raise** scale on `QUADRUPED` (+17.7%) and `BIRD` (+21.2%)
while **lowering** it on `HUMANOID` (−2.4%) and `INSECT` (−11.2%). Coverage and scale have no
fixed sign — measured at fixed axis, not inferred across axes.

**Suite on the merged tree: 1 failed, 2356 passed, 11 skipped (23:31).** The
failure is **not 0α's** — `tests/test_read_base.py::test_checkpoint_fallback_
pins_the_served_tree_not_the_request`, from PR #75, `ERROR: compilation timed
out after 1.2s`. It reproduces on GitHub CI (Linux, `1 failed, 2357 passed`)
and was already red on PR #75's own head before that PR landed, so it is
neither a merge interaction nor attributable to this goal. It passes **5/5
standalone and 20/20 module-only** here, failing only inside the full suite.
**Main is red; see COORDINATION.md.** Consequence for Goal 1: `--baseline` and
the fixture tests are unaffected (both verified green above), but no Goal 1 PR
can show a green suite until this is fixed by its owner.

### The timing measurement taken *before* the fix, because the fix destroys it

5/5 green standalone cannot tell "always took 0.4s" from "took 0.4s, now takes
1.15s" — if PR #75 had tripled the compile, this test would be an accidental
canary and making it deterministic would silence a real regression. Timed
`server._run_ladder_child(DOG_RAW)` — the exact call the test makes — at
production `_COMPILE_TIMEOUT = 60`, so a slow run reports a time instead of an
error. **No C++ changed between the two commits**, so the `.so` is byte-identical
and this is a clean Python-only comparison. n=7 each, macOS/arm64:

| commit | median | min | max |
|---|---|---|---|
| `5f6ab2a` (pre-#75) | **1.746 s** | 1.736 | 1.790 |
| `a04cb0a` (post-#75) | **1.855 s** | 1.780 | 1.864 |

**PR #75 cost ≈ +0.109 s, +6.2%.** The distributions barely overlap, so the
shift is real — but it is a creep, **not a tripling. This is one ticket, not
two.** Record the 6% rather than lose it; that is the kind of drift that
accumulates into the next expiry.

**And the measurement corrects how the test is being read.** The compile takes
**1.75–1.86 s against a 1.2 s budget**, so it *always* times out — that is the
point of the test, whose name is `..._pins_the_served_tree_not_the_request`.
The assertion is that the timeout fires **and the checkpoint fallback returns a
served tree instead of an error**.

⚠ **Correction, measured after I first wrote this: the child's own
`0.6 × _COMPILE_TIMEOUT` deadline is NOT the live budget, and I said it was.**
`_run_isolated` uses `mp.get_context("spawn")`, so the child **re-imports
`server` from disk** and never sees a parent-side `monkeypatch.setattr`.
Verified directly — patch the parent to 1.2, and the child still reports
`_COMPILE_TIMEOUT = 60`, i.e. an internal deadline of **36 s**, which never
fires. **The only live budget is the parent's `proc.join(1.2)`.** The race is
solely whether a checkpoint reaches the queue within 1.2 s of wall-clock, out of
a ~1.8 s compile.

This matters for the fix, not just the record: **the test cannot reach the
child's behaviour through module globals at all.** Anything injected has to
survive spawn — a parent-side seam, an env var, or a stub worker — so "just
patch the deadline" is not available.

**Three carried defects, none blocking:**

1. **The child's exception handler can turn a real PACK into `FAIL`.**
   `status` is set to `"PACK"` *before* `locs()` and `projection_report()`; an
   exception in either rewrites it to `FAIL` while `coverage` stays populated.
   Hit live on a stale `.so`: the 2-corner arm exported a real fold
   (coverage 0.791191) and reported `FAIL`. This is the same root as the
   `paper_coverage` import bug the report disclosed — that one was fixed, the
   ordering that *hid* it was not. The probe still cannot distinguish "did not
   pack" from "packed, then instrumentation failed."
2. **The non-vacuity test pins the input, not the output.**
   `test_the_order_restart_control_is_not_vacuous` asserts distinct
   `leaf_lengths` and `n_orders >= 12`. The vacuity that actually bit was
   identical *results*. It should assert distinct observed scales.
3. **`pin_max_displacement = 0.0` overloads two meanings** — "no pins were
   set" and "pins were set and did not move." Recurrence of S4a′ review
   finding 3 (`projection_report()` has no "did not run" sentinel).

---

## 0b — true polygon coverage — merged 2026-08-06 (PR #81)

`paper_coverage.hull_coverage` now measures the true "B"-border polygon (a
shoelace area over the ordered edge-cycle walk) instead of the convex hull of
its boundary points, falling back to the hull — **named** via
`source == "boundary_edges"`, never silently — when the border is not one
simple closed loop **or is topologically simple but geometrically
self-intersecting**. The B-edge cycle walk moved down from
`pose_base._border_cycle` into `paper_coverage` (dependency-free, called on
every scorecard row); `pose_base._border_cycle` is now a thin wrapper that
keeps its exact signature and `PoseBaseError` contract. Its own tests pass
**unmodified** — the guard the plan specified.

**Defect found in independent review, fixed:** `_border_cycle`'s checks are
TOPOLOGICAL (degree-2, one loop), not geometric — they accept a
self-intersecting boundary (a bowtie), whose shoelace area is meaningless and
can read `<= 0`. The original code assigned `source = "boundary_cycle"`
*before* checking the cycle's area, so a bowtie fell through to the hull
number while still reporting the cycle source: a fabricated number wearing
the wrong label, in exactly the direction that flatters the result. Reproduced
with `[[0,0],[1,1],[1,0],[0,1]]`: `_border_cycle` accepts it, true (shoelace)
area is `0.0`, and the pre-fix code reported `coverage 1.000000,
source "boundary_cycle"`. Fixed by relabeling `source` only after confirming
the cycle area is `> 0.0`; pinned by
`test_a_self_intersecting_bowtie_falls_back_named_not_silent`, proved real by
reverting the fix and watching it fail. `_border_cycle`'s docstring now states
plainly that it guarantees topology, not simplicity, and that a full
simple-polygon check is not attempted (not worth the cost for this module's
callers).

**Verification, not adjectives (post-rebase onto `7a94b67`):**
- Full suite: **2385 passed, 11 skipped, 0 failed**, 1113.19s (2367 baseline on
  `7a94b67` + 18 in `test_paper_coverage.py`, up from 9 pre-review — the
  self-intersecting-bowtie regression test and the nine-goldens pin).
- Frozen-baseline delta (`fixtures/scorecard_baseline.jsonl`, not
  regenerated): **`no axis moved: quadruped, bird, humanoid, fish, insect`.**
  `hull_coverage` unchanged on all five; `served_stage`/`path_drift_max` are
  present but were populated by PR #75/#78 before this slice ever ran and are
  already attributed there per COORDINATION.md §1's amendment — not to 0b.
- **All nine committed goldens (`tests/goldens/*.fold`) report
  `source == "boundary_cycle"`** — the new path actually ran on every real
  fold in the corpus, not merely the synthetic fixtures, closing the gap a
  "no axis moved" reading alone cannot close (the fallback IS the old
  behaviour, so identical numbers are also what a never-executing new path
  would produce). `hull_coverage` on those nine is unchanged to 6 decimals
  from the values CLAUDE.md §1.1(1) quotes: dog 0.663641, quad 0.496181,
  hshape 0.486111, hf-dog-ladder-best 0.458523, hf-dog-nudged 0.467292,
  star-4 1.000000, bear-base 1.000000 — pinned in
  `test_all_committed_goldens_report_boundary_cycle`.
- The chevron regression fixture (unit square, top edge pulled to its
  midpoint) reads **coverage 1.0 under the pre-fix convex-hull
  implementation** — the observed defect — and **0.75** (its true area) after,
  with `source == "boundary_cycle"`. The convex hull of the same points is
  independently asserted at 1.0 in the same test, so the test measures the
  change, not the implementation.

**Headline, stated plainly per the plan's own instruction, and stronger than
the first report because it is now shown to have executed, not just to agree:**
no committed frozen-baseline row moved, **and** the true-polygon path is
proven to run on all nine committed goldens (`source == "boundary_cycle"`),
so "no axis moved" is not indistinguishable from "the new code never
executed." **0b is a pre-registration for experiments that have not run, not
a correction to a wrong number.** The five frozen-baseline subjects' and nine
committed goldens' outlines are already convex, exactly as spec §1.1(1)
records — the true-polygon measurement and the convex-hull measurement agree
on all of them. The value of this slice is that a future corner-forcing
experiment (which produces non-convex outlines by construction) can now be
scored correctly the first time it runs, rather than over-reported until
someone noticed.

One deviation from the plan, reported rather than silently absorbed: the
plan's `test_paper_coverage_imports_no_numpy` pops `"numpy"` from
`sys.modules` and reloads `paper_coverage` in-process. Run after
`test_pose_base.py` (which already holds a live reference to the numpy module
object via `pose_target`), this corrupts numpy's lazy submodule
`__getattr__` and throws `RecursionError` in unrelated, later `pose_base`
tests — collateral damage from this slice's own new test, not an edit to a
pose_base test. Rewrote the check to run in a subprocess (asserts
`"numpy" not in sys.modules` after a fresh `import paper_coverage`), which
proves the same guarantee without mutating the running interpreter's module
table. Full suite green with the rewrite.

Goal 2 may now report `hull_coverage`/`cp_*` numbers side by side once this
PR merges — this is the shared instrument they were rebasing onto.

## 0b review — merged 2026-08-06 (PR #81), defect found and fixed

Reviewed 2026-08-05 by the planning session against `5d491c6`, on a scratch
merge of the 0b branch onto current main. **0b was 52 commits behind**, so its
own `2265 / 11` was measured against a base that no longer exists; these are
the numbers that transfer.

| measurement | result |
|---|---|
| Full suite, 0b **merged onto current main** | **2373 passed, 10 skipped, 0 failed** (28:59) |
| Frozen-baseline delta | **`no axis moved: quadruped, bird, humanoid, fish, insect`** |
| `hull_coverage`, all five | 0.7161 / 0.5000 / 0.6319 / 0.9077 / 0.8595 — the goal's founding numbers, unmoved |

The suite arithmetic re-confirms the AF_UNIX diagnosis a fourth time: 2363
(main) + 9 (0b's new tests) + 1 (the socket test *runs* here, because
`/tmp/0b-merge` is a short path) = 2373, skips 11 → 10.

**The headline is stronger than the slice claimed, and the missing evidence is
the part that matters.** 0b reported "no committed row moved" having exercised
the new path only on a synthetic chevron. That leaves the result reading as
possibly vacuous — **the fallback IS the old convex-hull behaviour, so identical
numbers are exactly what a never-executing new path would produce.** Ran all
nine committed goldens through both implementations:

**Every golden reports `source == "boundary_cycle"` under 0b, and
`"boundary_edges"` before it.** The new measurement ran on real folds and
agreed. That is what makes "no axis moved" a finding rather than a silence.

**And it clears a risk nobody checked: `CLAUDE.md` §1.1(1) quotes coverage
numbers this very function produced.** They are unchanged to six decimals —
`dog` 0.663641, `quad` 0.496181, `hshape` 0.486111, `hf-dog` 0.458523 /
0.467292, `star-4` and `bear-base` 1.000000. Had they moved, §1.1(1) would have
gone stale two commits after §1.1(2) and (4) were corrected. **Any future change
to `hull_coverage` must re-check the goldens against §1.1(1) — the scorecard's
five subjects do not cover it.**

### The defect: `source` can lie, in the flattering direction

`source = "boundary_cycle"` is assigned **before** the computed area is
validated. `_border_cycle`'s guarantees are **topological** (every border vertex
degree-2, one loop); neither rules out a **geometrically self-intersecting**
boundary, whose shoelace value is meaningless and can be ≤ 0. Reproduced with a
bowtie `[[0,0],[1,1],[1,0],[0,1]]`, which `_border_cycle` accepts:

```
raw shoelace area = 0.0        -> falls through to the convex hull
reported          = coverage 1.000000, source "boundary_cycle"
```

It returns **the convex-hull number labelled as the trustworthy one** — the
exact bias 0b exists to remove, and a direct breach of the module's own
docstring rule, *"the fallback is NAMED in `source`, never silent."* Two lines:
assign `source` only once `a > 0.0`.

Low probability today — real CP boundaries do not self-intersect. But 0b's
stated purpose is **corner-forcing experiments**, the regime most likely to
produce degenerate outlines, so this is once again a mechanism pinned only where
it cannot fail.

### Verified clean

Chevron 0.75; convex square 1.0; two disjoint loops → **named** `boundary_edges`;
no B edges → `all_vertices`; collinear and 2-point → **`None`**, never a
fabricated number; dangling spur → falls back. `paper_coverage` still imports
**neither numpy nor scipy** (checked in a fresh interpreter). The `pose_base`
wrapper genuinely **translates** rather than leaking — `CoverageError` is *not* a
subclass of `PoseBaseError` — and both `_border_cycle` implementations agree
vertex-for-vertex on `dog.fold`. The reported numpy-test deviation (subprocess
instead of in-process reload) is the right call and leaks nothing.

### Carried

- 0b's `PROGRESS` line *"Goal 2 may report coverage numbers"* is wrong twice:
  the slice is not merged, and the freeze rule it was written against has been
  **amended** (`d542053`). Fix on rebase.
- Merging 0b onto main **conflicts** on `COORDINATION.md` and `PROGRESS.md`
  (#76 edited both). Code files merge clean.

---

## 0-scale review — reproduces exactly; the cross-subject reading is the trap

Reviewed 2026-08-06 by the planning session against the implementation
worktree `.claude/worktrees/xenodochial-mayer-f3c8ab` (branch
`claude/goal-1-0-scale-design-scale-bf5d26`, branched off `e100cf1`).
**Uncommitted at review time** — seven dirty files, nothing on a branch tip.

**Every reported number reproduced on an independent run** of
`benchmark_subjects.py --baseline fixtures/scorecard_baseline.jsonl`:

```
=== deltas vs fixtures/scorecard_baseline.jsonl ===
quadruped: design_scale: None -> 0.599702
bird: design_scale: None -> 1.095885
humanoid: design_scale: None -> 0.701537
fish: design_scale: None -> 0.653249
insect: design_scale: None -> 0.582125
```

Exactly the column-addition on five rows. No other axis moved. Frozen fixture
untouched.

**Wiring pinned harder than reported.** The implementation's own sever
hardcoded `"design_scale": None` in the row dict, which only proves the key
exists. The review severed `fold_meta.scale_from_fold_str` *itself* and
diffed the whole row: **exactly one key moved**, and `hull_coverage` was
unchanged. That is the pin — `build_row` has no second path to the value.
Dropping `import re` from both former copy-sites is the structural half of
the same proof.

**Three things the report undersold, all in its favour.**

1. **The `ERROR:` guard is the sharpest test in the set.** `TreemakerWrapper.cpp`
   writes `scale=` into **three error strings**, not just the frame title
   (`could not build a full crease pattern (scale=0.56): …`). Without the
   guard an unserved row would report a design scale lifted from a *failure
   message* — a fabricated number wearing a real column's name, which is the
   exact failure `design_scale`'s "never 0.0" rule exists to prevent. Tested;
   described as routine.
2. **The scientific-notation risk is CLOSED, not deferred.** The writer emits
   under `std::fixed << std::setprecision(6)`, so `e` notation is structurally
   impossible from production output. `[0-9.]+` is therefore safe against the
   only writer that exists. The preserved-behaviour test is still right — but
   the residual risk is retired, not carried.
3. **`frame_title` is the ONLY channel.** The pybind surface exposes no scale
   getter (`run_scale_optimization` is a driver, not an accessor). The string
   parse is *forced*, not lazy. Recorded so nobody later "improves" it into a
   direct read that does not exist. ⚠ Corollary: `design_scale` is quantised
   to 1e-6 by the writer's `setprecision(6)` and cannot be more precise
   without a C++ change.

### THE FINDING — `design_scale` is a within-subject signal; reading down the column is the `n_leaves` confound again

The five values *look* like the coverage-versus-scale trade CLAUDE.md §1.1(4)
demands be argued. They are not evidence of it.

| pairing (n=5, frozen-baseline subjects) | Spearman |
|---|---|
| `hull_coverage` ↔ `design_scale` | **−0.700** |
| `served_leaves` ↔ `design_scale` | **−0.900** |
| `served_leaves` ↔ `hull_coverage` | **+0.900** |

The confound beats the direct association **on both legs**. This is the same
shape as the S8 gate retrain that was measured and rejected (memory
`perfect-base-s8-outcome`: within-stratum AUC showed the apparent signal was
an `n_leaves` confound). n=5 needs |ρ| ≥ 0.900 for p < 0.05, so −0.700
establishes nothing on its own either way.

**The dimensional argument is stronger than the correlation and does not
depend on n.** `design_scale` is paper-units per **tree**-unit, and the tree
unit is not shared across subjects. `mesh_to_tree.to_metric_tree` normalises
the longest edge to `LONGEST_LIMB_TARGET = 0.40` — but **its own docstring
warns that this is the input to reconciliation, not the post-condition**:
equalization measured humanoid at 0.400000 → **0.349099**, and re-parenting
puts **22 of 50 measured configs over target, worst 0.8085 (2.02×)**. That is
~2.3× of possible unit spread against the **1.88×** actually observed in the
scales (1.095885 / 0.582125). Unit drift alone could account for the entire
observed range before any design effect.

**Consequence for S5.** `design_scale` is exactly the right instrument for the
argument §1.1(4) demands — as a **within-subject, before-vs-after** reading:
same tree, one lever changed, scale before and after. It is **not** a
cross-subject ranking, and the five-row column must not be read as one. Any
S5 sentence of the form "subject A trades better than subject B" is measuring
tree size, not design quality.

**Cheap follow-up that would make the column cross-comparable** (not yet
scoped): `design_scale × emitted longest edge` = the longest limb's length in
paper units on the unit square. Dimensionless in paper units, comparable
across subjects, and it is the number a folder physically experiences. The
emitted longest edge is not currently a column.

### Requested before commit

- One sentence in the `design_scale` column comment marking it a
  **within-subject** signal.
- Reword the `COORDINATION.md` §4 row so listing the five values side by side
  does not invite the cross-row reading it currently invites.

---

## 0c review — merged 2026-08-07 (PR #87), one real defect found and fixed

Reviewed by the planning session before merge. The badge computes
`paper_coverage.hull_coverage` server-side on the **raw** `fold` at the single
fold-frame construction site in `web/server.py`, and carries `{value, source}`
on the wire so the fallback stays NAMED — 0b's central guarantee.

**Reproduced independently:** `dog` reads `0.663641` → badge `0.6636`, matching
CLAUDE.md §1.1(1)'s `0.664`.

**Stronger than the implementation reported:** all **nine** committed goldens
report `source == "boundary_cycle"`, so the "estimated" wording never renders
on any model that ships today. The degraded path is proven to work *and*
proven not to be reached.

| golden | coverage | source |
|---|---|---|
| bear-base | 1.000000 | boundary_cycle |
| dog | 0.663641 | boundary_cycle |
| dog-repaired | 0.657074 | boundary_cycle |
| hf-crane-ladder-blb | 0.501679 | boundary_cycle |
| hf-dog-ladder-best | 0.467292 | boundary_cycle |
| hf-dog-nudged | 0.458523 | boundary_cycle |
| hshape | 0.486111 | boundary_cycle |
| quad | 0.496181 | boundary_cycle |
| star-4 | 1.000000 | boundary_cycle |

### The defect — the fallback sentence was false in the case 0b was built for

The original text read *"the crease border isn't one closed loop."* Measured
against every source that triggers the fallback:

| case | `source` | old text |
|---|---|---|
| two disjoint loops | `boundary_edges` | ✅ true |
| **bowtie** (self-intersecting) | `boundary_edges` | ❌ **false** |
| no B edges at all | `all_vertices` | ❌ misdescribes |

The bowtie is decisive: `_border_cycle` **accepts** it (`walk=[0,1,2,3]`,
degree-2, one loop) and it falls back only because its shoelace area is `0.0`.
It *is* one closed loop; it crosses itself. That is exactly the case PR #81
shipped a regression test for, so the badge contradicted the defect 0b fixed —
and it rendered *"an estimated 100.0% of the square"* for a pattern enclosing
zero area.

Fixed before merge to *"the true crease border couldn't be measured"* — true
of all three causes — with a regression test pinning the bowtie case.

**Deliberately NOT fixed:** the 100% over-read itself. Returning the convex
hull with a named `source` is **0b's policy, not 0c's bug**; overriding it from
a display slice would be one slice silently re-deciding another's design.

**Finding, recorded for whoever next touches `paper_coverage`:**
`source == "boundary_edges"` is doing **double duty** — it means both "the
border is not a single loop" and "the border is a single SELF-INTERSECTING
loop". Two different facts under one label, which is why no single honest
sentence can name the cause.

**Not test-covered, flagged rather than glossed:** the JSX call site itself.
There is no RTL/jsdom anywhere in this frontend — every existing test targets a
pure function — so `coverageNote` is pinned and `{note && <p>…}` is not.

---

## ⚠ The ordering lever — Goal 2's offer, and why it is not yet actionable

Goal 2's 154-arm sweep (COORDINATION log, 2026-08-06) reports that
`order_variants` — **already implemented** — reaches folds that strictly
dominate what is served today, on the **shipped 45° axis**, Python-only, with
no claim on the serial file:

- **bird +38.3% scale, coverage 0.499952 → 0.984783 (+97.0%)**
- humanoid +10.6% scale, +5.0% coverage
- quadruped +19.7% scale, all 3 invented stub flaps eliminated

The defect is **first-clean-wins**: the ladder takes the first ordering that
packs and never ranks. Memory already records this lever as unexploited
(*"the ladder never ranks by scale → dog-raw discards +12.7% on the path it
already runs"*).

**Goal 2 explicitly offered it to Goal 1** — "coverage and `design_scale` are
Goal 1's columns, so say now if you want to own it instead."

### Why the number must be re-measured before anything is scoped on it

`0.984783` has **the same shape as the `0.6612` figure Goal 2 itself
withdrew**: a coverage reading on a *modified* pack, where the outline may be
non-convex and the convex hull can only overstate. 0b merged on 2026-08-06
(`773982a`) and the sweep ran the same day, so whether it used the true
boundary polygon or the convex hull is **not established by the record**. Its
pre-value `0.499952` also does not equal the frozen baseline's bird `0.5000`,
confirming this is a different measurement path than the scorecard.

**Ask Goal 2 for the sweep artifact and the reproduction command; re-measure
bird under 0b before this is scoped.** Applying the same correction Goal 2
applied to `0.6612` is not scepticism about their work — it is the rule they
themselves set.

### Two constraints already established, to carry into any scoping

1. **It must RANK, not take the first bijection.** Humanoid `canonical` also
   reaches bijection — at `mv_swapped` 26 and scale 0.598116, a markedly worse
   basin than `seeded_1`'s 2 / 0.775554. "First bijection wins" ships the bad
   one.
2. **Quadruped landing at 0.740905 is NOT a regression** against the pinned
   `1.000000`. The pinned figure was never a shipping candidate.

### The consequence for S5, which is the reason this matters

If ordering delivers most of the coverage on the shipped axis, **S5's premise
changes**: the question stops being "should the axis change?" and becomes
"does the axis add anything beyond what ordering already gives?" That is a
smaller question, and it lowers S4b₀'s expected value — though not to zero,
since S5 needs an export-capable book axis to answer it either way.

---

## S4b₀ — implemented 2026-08-07

Three changes, all in `mcp_harness/TreemakerWrapper.cpp` (`ProjectActivePaths`
+ `projection_report()`):

1. **Task 1 — `maxr`/`ran` in `projection_report()`.** `maxr` is the GN loop's
   actual final residual, recomputed read-only on the post-loop x,y (does not
   change convergence, iteration count, or the written-back coordinates).
   `ran` is a real "did the loop reach its solve step" sentinel, true only
   past the `cons.empty()` early return that S4a' review finding 3 flagged
   `cons` as unable to signal. Reproduces the S4a' review's exact figures on
   macOS/Accelerate: `star-4-sym` 1.717e-09 (50 iters, the cap), `star-5`
   2.233e-09 (50 iters), `TEMPLATE_HUMANOID` ~7.4e-14 (22 iters, well
   converged). **Does NOT reproduce on Linux/OpenBLAS** — see "Linux
   findings" below; this is a genuine, newly-measured platform divergence in
   the ALM optimizer's own convergence path, not an instrumentation bug.
2. **Task 2 — book (0°) and 90° as exact integer rows**, per spec §4.2's
   table. Factored into a shared `SymRows()`/`symV()` helper used by both the
   GN loop and Task 1's residual recompute, so the two representations of
   "which rows are being solved" cannot drift apart. The 45° branch is that
   same helper's `default` case, algebraically identical to the code it
   replaced.
3. **Task 3 — lift the S4a' refusal for exactly {0, 45, 90}.** Every other
   angle, and non-square paper at any of the three, still refuses.

**The sign hazard, verified non-vacuous, not just reasoned about.** Row 2 is
inhomogeneous at 0°/90° (`yi+yj-h=0` / `xi+xj-w=0`); the natural
pattern-matching mistake off 45°'s homogeneous rows is `yi-yj=0` /
`xi-xj=0`. Built the negative control (criterion 10) *before* Task 2's code:
QUAD's leaves 3/4 pinned to an identical y (or x, for 90°) via two
independent `set_node_on_y`/`set_node_on_x` calls *before* any symmetry
condition exists — decoupling the pre-projection state from the optimizer's
own correct, angle-general `PairFn1B` enforcement, so `yi=yj` holds exactly
going in while `yi+yj=h` does not. Watched it fail (refused, pre-Task-2/3);
implemented the exact homogeneous-row bug deliberately, rebuilt, watched the
control fail again (this time via a genuinely wrong pack); reverted; watched
it pass. `test_the_homogeneous_row_sign_hazard_is_caught[_at_90]`.

Measured via `debug_active_path_report()`, not `build_and_export()` — a
first draft used the latter and broke on Linux; see "Linux findings" below.

**Criterion 9 / R2 — the central empirical result.** Converted 0α's
optimizer-only book0 "2 pairs → 4 corners" headline arm into a real
export-path measurement, for all five subjects, across the full arm grid
(free, either single pair, 2-pairs→4-corners — 16 arms total):

| subject | book0 arms that reach a verified-symmetric export |
|---|---|
| `star-4-sym` | **all 4 tested** (free, both single-pair, 2-pair-4-corner) — residual ≤1.4e-08, bijection true |
| `QUADRUPED` | **0 of 4** — free/2-pair-4-corner die at `POLYS_MULTIPLE_IBPS` (Universal Molecule build); one single-pair arm packs but is NOT symmetric (residual 0.097) |
| `BIRD` | **0 of 4** — free and one single-pair arm pack but are NOT symmetric (residual 0.11–0.23); the other two arms die at `POLYS_MULTIPLE_IBPS` |
| `HUMANOID` | **0 of 4** — free and 2-pair-4-corner die at the FIRST polygon-valid gate (`ran=False`, before the projection ever runs); the two single-pair arms die at `FACETS_NOT_VALID` / `POLYS_MULTIPLE_IBPS` |
| `INSECT` | **0 of 4** — free and 2-pair-4-corner die at the first polygon-valid gate; the two single-pair arms die at `NOT_LOCAL_ROOT_CONNECTABLE` / the first gate |

**In no case is the rejection attributable to projection precision.** Every
arm where the projection ran at all converged to `maxr < 1e-8` (several to
machine noise); the optimizer's own scale reproduces the 0α fixture's
book0-4-corner figures to 6 digits on every subject (e.g. `QUADRUPED`
0.720456, `BIRD` 0.726750). **This is R2, measured**: book0 geometry is
rejected downstream of a cleanly-converged optimizer, on 4 of 5 production
subjects, at one of two failure points (the Universal Molecule / crease-
pattern build, or the pre-projection polygon-valid gate — never the
projection itself). Only the toy fully survives. Asserted as a
regression-pinned finding
(`test_r2_book0_is_rejected_downstream_on_the_production_templates`): if a
future engine change makes any of these four pack, the test fails loudly and
that is itself news, not silent progress.

**Whether book0 should be a default given this is explicitly S5's question**
(CLAUDE.md's own DO NOT for this slice) — this result is the input S5 needs,
not a verdict on it.

**Verification, not adjectives:**
- 45° unmoved: `test_geometry.py::test_geometry_matches_golden` (existing,
  unmodified) passed on both platforms — VERTEX_TOL=1e-6 + QUAD's basin
  registry. A hand-run diff-inspection script on this macOS build additionally
  confirmed all four `GOLDEN_CASE_NAMES` byte-identical to their golden
  `.fold`, `vertices_coords` included — a single-platform fact, not encoded as
  a test (see "Linux findings" for why not). `git status` confirms none of the
  nine committed `goldens/*.fold` files were touched.
- Wiring proven by deletion (criterion 14): forced `symCase` to always
  resolve to the 45° case (simulating the refusal-lift landing without the
  new rows actually being wired in). Exactly 8 tests went red — the four
  book/90 "not refused" tests, both sign-hazard controls, and both criterion
  9/R2 tests — with zero collateral on the other 27. Reverted; full green.
  Re-verified after the Linux-driven test rewrites below; same 8, same zero
  collateral.
- No trig anywhere in the diff (`grep -i 'cos(|sin('` on the new code: zero
  hits outside comments).
- Full suite (macOS, this worktree, final): **2413 passed, 11 skipped, 0
  failed** (1257.89s / 20:57).
- Frozen-baseline delta (`fixtures/scorecard_baseline.jsonl`, not
  regenerated): **only the five `design_scale: None -> value` rows**,
  attributed to `0-scale` (merged, not this slice) per COORDINATION.md §1.
  Nothing else moved — the frozen five subjects never exercise a non-45°
  axis, so 45° being untouched is exactly what this predicts.
- Linux (`ci-amd64-run` container, final run after the fixes below):
  **2414 passed, 10 skipped, 0 failed** (2663.77s / 44:23 — amd64-on-arm64
  emulation). 2414/10 vs macOS's 2413/11 is the same AF_UNIX
  `sun_path`-length skip-count offset memory `worktree-missing-build-
  artifacts` already diagnosed (both sum to 2424); zero failures on either
  platform.

**Linux findings — three genuine platform-sensitivity issues, all in the new
tests, none in the row math.** The container run (criterion 13) is not a
formality here; it caught real cross-platform mistakes a macOS-only session
would have shipped:

1. **`iters == 50` was asserted as if it were a property of the tree.** The
   ALM scale optimizer's own convergence path differs by BLAS backend
   *before* the projection ever starts (the 1-ULP-level divergence memory
   `packer-two-basins-scale-lever` documents for `QUAD`'s two packing
   basins), so the projection inherits a different starting point and needs
   a different step count: 50 (macOS/Accelerate) vs 37 (Linux/OpenBLAS) for
   `star-4-sym`. Worse: on Linux the residual ALSO reaches ~7.9e-14 in those
   37 iterations — fully converged, not censored at all, contradicting the
   very S4a' review finding 1 this test exists to expose. **The "saturates
   at 50 iterations with residual ~1e-9" behavior is a macOS-specific
   OBSERVATION about these two trees, not a guarantee the projection makes.**
   Renamed to `test_star4sym_and_star5_expose_the_margin_proxy`; now pins
   only what is platform-invariant (the instrument reports a real,
   self-consistent `iters`/`maxr`/`ran`), with the macOS figures kept here as
   a measurement rather than a cross-platform assertion.
2. **The sign-hazard negative controls ran the full `build_and_export()`
   pipeline on `QUAD`.** `QUAD`'s leaves 3/4 sit near a knife-edge in the
   downstream `BuildPolysAndCreasePattern` — a k-sweep (`0.05` to `0.49` in
   steps of `0.005`–`0.05`) showed FAIL/PACK alternating at a finer
   granularity than sampled, consistent with the tangency-cliff sensitivity
   `packer-two-basins-scale-lever` already documents for this exact subject.
   The large, correct move row 2 forces (this control's whole point) can
   land on either side of that cliff depending on 1-ULP platform
   differences, independent of row correctness — and it did: PACK on macOS,
   `polygon network became invalid after active-path projection` on Linux,
   for the SAME code. Switched to `debug_active_path_report()`: runs the
   real `ProjectActivePaths` (same rows, same `SetLoc` write-back) but stops
   after one more `BuildTreePolys()` call with **no validity check**, so it
   measures whether row 2 is right without depending on the fragile
   downstream molecule build. That build is exactly what criterion 9's
   separate, dedicated test already exercises end-to-end (and which
   correctly reports the four production templates as NOT reaching it — see
   above).
3. **A first draft of criterion 11 asserted exact `vertices_coords`
   equality.** Passed 4/4 on macOS; failed 4/4 on Linux — reproducing, in a
   test I almost shipped, the exact mistake memory
   `rigid-frozen-hash-platform-divergence` already named: *"a frozen sha256
   over roundoff-bearing artifacts CANNOT be green on both platforms ...
   never re-bless."* Deleted outright; `test_geometry.py`'s existing
   `VERTEX_TOL=1e-6` + basin-registry pin already does this correctly and is
   unmodified by this slice — it passed on both platforms without touching a
   single assertion.

**A fourth, build-only trap, not a test defect:** the container invocation
(`cp -r /repo-src/. /repo && ... make PYTHON=python test`) copies the whole
worktree, including this session's own local `oriedita`/
`OrieditaValidator.class` symlinks (created per the S4a'-plan's documented
trap so `build.sh` produces a real `.so` locally). Those symlinks collided
with `build_linter.sh`'s own `mkdir oriedita` inside the container
(`mkdir: cannot create directory 'oriedita': File exists`), failing the
container run before a single test ran. Fix: `rm` the local symlinks
immediately before each `docker run`, restore them after for continued local
work. Worth adding to the traps list alongside the existing
`PYTHON=python3` one, since it will bite the next Linux verification too.

**Not applied cleanly / departures from the plan:**
- `test_projection_guards.py::test_non_45_axis_with_pairs_is_refused` used
  `angle=0.0` as its refused-axis example; renamed to
  `test_an_unsupported_axis_with_pairs_is_refused` and re-pointed at 30°,
  since 0° is now a supported axis. Two new tests
  (`test_book_axis_with_pairs_is_NOT_refused`,
  `test_90_degree_axis_with_pairs_is_NOT_refused`) added alongside it.
- The plan's criterion 9 wording ("ALL FIVE SUBJECTS") is not literally
  achievable today — see the table above. Reported as the R2 finding rather
  than narrowed silently; the negative result is pinned by a test, not just
  described in prose.
- One unrelated flake observed in a full-suite rerun under heavy host
  contention (another session running concurrently, load average 5-6):
  `test_auto_mesh_to_tree.py::test_auto_selection_is_deterministic` failed
  once, then passed in isolation (7 minutes for what should be a fast test —
  clearly starved, not broken). Nothing this slice touches; not
  investigated further per the project's own rule not to chase a mechanism
  measured only in a contended regime.

---

## S4b₀ review — VERIFIED, and it changes the goal's direction

Reviewed 2026-08-07 by the planning session on its own build of `8af5bc4`.
`tests/test_book_axis_projection.py` **14/14 green**, and the headline
reproduced by driving the engine directly rather than through the slice's own
`run()` helper:

| subject | scale | rejected where | `ran` | `iters` | `maxr` |
|---|---|---|---|---|---|
| QUADRUPED | 0.7204555096546211 | CP build, `POLYS_MULTIPLE_IBPS` | True | **50** | **2.857e-10** |
| HUMANOID | 0.7692307671167886 | polygon-validity gate, before projection | **False** | 0 | 0.0 |

**Both halves of Task 1 are load-bearing in the headline, which the report
undersold.** QUADRUPED *saturates* the 50-iteration cap — without `maxr` that is
indistinguishable from a precision failure, and `maxr = 2.86e-10` rules
precision out cleanly. HUMANOID never reaches the projection at all, which only
`ran=False` can say. Task 1 was added because 0α could not tell these apart; it
now decides the slice's own central result.

### The decomposition S4b₀ did not run — and it narrows the conclusion

S4b₀'s arm sets the axis **and** pins four corners at once, so "book0 is
rejected downstream" conflates two levers. Separated, on the four production
templates (bare-engine template path, **not** the serve path — do not compare
these to the scorecard):

| arm | QUADRUPED | BIRD | HUMANOID | INSECT |
|---|---|---|---|---|
| **book0, no pins** | rejected `POLYS_MULTIPLE_IBPS` | **EXPORTS** 0.599416 / cov 0.694637 | rejected, polygon gate | rejected, polygon gate |
| **diag45 + 4 corner pins** | optimizer non-convergence | optimizer non-convergence | optimizer non-convergence | optimizer non-convergence |
| **diag45, no pins** (shipped) | 0.667979 / 0.680970 | 0.652542 / 0.669464 | 0.629445 / 0.558981 | 0.763400 / 0.789076 |

**The dead lever is CORNER PINNING, not the axis** — and it is dead at *both*
axes for *different* reasons: diag45 fails at the optimizer (0α's result,
reproduced), book0 converges and is rejected downstream (S4b₀'s result,
reproduced). 0α's headline — book0 + 2 pairs → 4 corners → leaf hull `1.000000`
on 5 of 5 — was optimizer-only, and **the optimizer is the only place it ever
worked.**

### The one export the axis does buy is not usable

BIRD exports at book0 unpinned with coverage `0.694637` against its diag45
control `0.669464` — the first export-path coverage gain from the axis this
project has measured. **It does not survive inspection:**

```
mirror_verdict(axis=0.0): symmetric=False  residual=0.23498677575211477
mirror_verdict(axis=45.0, control): residual=0.0
```

**S4b₀'s rows are NOT at fault — verified directly.** Both declared pairs are
mirrored about `y = 0.5` to machine zero:

```
pair (3,4): |xi-xj|=9.660e-20   |yi+yj-1|=0.000e+00   OK
pair (5,6): |xi-xj|=0.000e+00   |yi+yj-1|=0.000e+00   OK
```

Exact zeros on the **inhomogeneous** row are the direct refutation of §4.2's
sign hazard: a homogeneous row would give `yi == yj`, and we measure
`yi + yj == 1`. The residual is **node 7, an UNPAIRED leaf at (0.329, 0.000)**,
0.5 off the book axis — Goal 2's axial-leaf mechanism
(`two-goals-axial-leaf-mechanism`), confirmed a ninth time and now at book0.
Note the interaction: at diag45 bird's residual is `0.0`, so **the axis choice
changes which unpaired leaves are off-axis.**

### Consequences — three, and they are not small

1. **CLAIM CORRECTED: "the corners are reached by choosing the symmetry axis"
   is falsified on the export path.** CLAUDE.md §1.1(2) already flagged the book
   readings as optimizer-only and said making the book axis export-capable "is
   its own piece of work." That work is now done and **the answer is negative**:
   3 of 4 production templates do not export at book0 at all, and the one that
   does is not symmetric about the axis it asked for. §1.1(2) owes a correction
   with this evidence — planning session's job, same as PR #76.
2. **S4b-general: CANCEL.** Its gate is "only if S5 shows an angle outside
   {0, 45, 90} pays." Neither 0° nor 90° pays, and the rejection mechanism —
   polygon-partition validity and multiple inactive border paths — is a
   **packing-topology** problem, not an angle-representability one. An arbitrary
   angle has no path to paying, and the slice was costed at Opus-max.
3. **S5: rewrite, and much smaller.** There is no axis selection to make; 45° is
   the only axis producing production crease patterns. What survives is the
   coverage-versus-scale argument itself, applied to whatever lever *does* work
   — which is now the ordering lever.

**S4b₀ was not wasted by this.** It is what converted a five-subject
optimizer-only headline into a measured export-path negative, at Sonnet cost,
exactly as spec §8 R2 predicted it would. A negative that closes an Opus-max
slice is a good trade.

---

## S6 (order-rank-attempt0) — implemented + verified 2026-08-08/09

Spec:
[`2026-08-06-order-rank-attempt0-design.md`](../../specs/2026-08-06-order-rank-attempt0-design.md).
Plan:
[`2026-08-08-s6-order-rank-attempt0.md`](../../plans/2026-08-08-s6-order-rank-attempt0.md).
Python-only, `TreemakerWrapper.cpp` untouched.

Opens `server._compile_with_perturb`'s attempt-0 short-circuit: when the exact
tree packs but is not already a proven mirror bijection about the shipped
45° axis (`order_rank.is_bijection` — the load-bearing predicate gate, spec
§2.1), one batched child spawn (`server._worker_rank_variants`, mirroring
`_worker_compile_and_regions`'s "whole ladder in one child" precedent)
compiles every depth-1 `rescue_ladder.order_variants` sibling and
`order_rank.rank` (K1 `-stub_flaps`, K2 parsed-6dp `design_scale`, K3
`is_bijection`, K4 `-mv_swapped`, K5 ties-to-control) picks the winner. A
re-ranked serve carries a new, non-rescue frame_title marker
(`order_rank.RANK_MARKER`) and keeps `rescue_stage == "none"` /
`attempt0_pack == True` — nothing failed, nothing was rescued, so the shipped
`tests/test_mesh_to_tree.py` contract (`stage != STAGE_EXACT ⟹ attempt0_pack
is False`) is untouched by construction. Only `draft_and_compile_full_base`
gains ranking; `compile_base`'s session/recipe path is unchanged (scope
decision — every measured number and every acceptance criterion in the spec
is about the one-shot pipeline, and batching a second, differently-shaped
worker for the recipe-replay path was neither specced nor required).

**R1–R3 (COORDINATION.md §4.1 required-fail inputs) were not reproducible as
written** — the spec's cited sweep arms (`mesh-humanoid/canonical`,
`hshape/seeded_2`, `star-4-sym/seeded_3`) were never committed. Regenerated
from committed trees (`fixtures/humanoid.glb`, `tests/cases.py`'s
hshape/star-4-sym) via `rescue_ladder.order_variants` — deterministic, no
env dependence — into the now-committed
`tests/goldens/order_rank_r1r3.json` (`probe_order_rank_r1r3.py`). **All
three reproduce the spec's quoted figures exactly**: humanoid/canonical
scale 0.598116, `mv_swapped` 26 (loses to `seeded_1`'s 0.775554/2 on K2
alone); hshape/`seeded_2` ties control at the parsed 6dp scale 0.589256 and
loses at K3 (not a bijection); star-4-sym/`seeded_3` ties control at every
key through K3 and loses at K4 (`mv_swapped` 2 vs 0).

**Bird reproduces exactly**: `hull_coverage` 0.5000 → **0.9848**,
`design_scale` → **1.515998**, `is_bijection` False → True,
`cp_mirror_residual` 0.053492 → 0.0. Humanoid: `hull_coverage` 0.6319 →
0.6638, `design_scale` → 0.775554, `cp_mirror_residual` 0.378336 → 0.0.
Both matched to 6 digits against every number this goal and Goal 2 had
already quoted for this lever, on the FIRST run — no iteration needed.
quadruped/fish/insect are untouched (none packs at attempt-0, so S6's
predicate never fires for them); quadruped's depth-2 win stays correctly
out of scope, exactly as the spec's §9 recorded it must.

**On `cases.py`'s 21 attempt-0 subjects (the PR #92 byte-pin's coverage
set), 6 moved and 15 did not** — cat-spine3, cat-spine4, cat-long-legs,
cat-short-legs, uneven-star, dog-repaired, every scale move matching the
spec's §5 table to 6 decimals. `cat-long-legs` is the one real trade
(scale +0.8%, coverage down, §1.1(4)-sanctioned in direction but argued, per
spec). `hshape`/`star-3`/`star-4-sym` (bijective controls) are provably
untouched — the predicate gate structurally protects them, exactly as
designed.

**A real gap found and closed, not silently absorbed**: PR #92's own
required-fail test (`test_serve_attempt0_pin.py::
test_required_fail_detects_reordered_serve`) used dog-repaired/`seeded_0` —
and its own docstring predicted this: *"if a future ranking slice ever
serves this variant in place of the control, THIS pin must be the one that
fails."* S6 does exactly that (dog-repaired's control now itself resolves to
`seeded_0`'s basin), which makes that specific pair vacuous for its original
purpose. Replaced with hshape/`seeded_0` — durable across future S6 changes,
because hshape's control is a proven bijection the predicate gate
structurally refuses to ever search, so a pure reorder stays exactly as
invisible to `rescue_stage`/`attempt0_pack` as it always was.

**Marking-fork confidence caveat (spec §7.1) — RESOLVED, not merely
checked.** The fork's claim (b) — that marking a re-ranked serve as a rescue
stage would destroy the G2a fix by re-timing `mesh_to_tree`'s extraction
drain — is confirmed directly: bird's extraction post-S6 still yields
`n_nodes=6, pairs=[[4,2]]`, byte-identical to the pre-S6 stock drain (spec's
own "6 nodes / pairs `[[4,2]]`" figure), because `rescue_stage` stays
`"none"` and the drain's terminal `fid >= 1.0 and stage == "none"` condition
still fires unchanged. Marking it as a rescue stage would have moved this;
not marking it as one is what keeps the bird headline attached to the tree
the stock drain actually extracts.

**A stale `.so` was found and fixed, unrelated to S6.** This worktree's
built `headless_treemaker.so` predated `8af5bc4` (S4b₀'s C++ merge, already
on `main` at this branch's base) — `hasattr(engine, "projection_report")`
was `False` on a source tree that has it, producing 26 pre-existing
failures in `test_book_axis_projection.py`/`test_projection_guards.py` that
had nothing to do with this slice. Rebuilt with `PYTHON=<venv> ./build.sh`
(TreemakerWrapper.cpp untouched, confirmed via `git status` before
rebuilding); all 26 pass afterward. Recorded because the next session to
pick up this worktree should not re-diagnose it.

**Verification, not adjectives:**
- Pre-S6 baseline, measured on an ISOLATED worktree (a second `git worktree
  add` at the parent commit `f01a292`, artifacts copied across so the build
  is genuinely untouched by concurrent edits — the first same-directory
  attempt was contaminated by spawned children re-importing `server.py`
  live off disk mid-edit, and was discarded): **2436 passed, 10 skipped, 0
  failed** (2422.31s / 40:22).
- Post-S6, this worktree: **2451 passed, 11 skipped, 0 failed** (2497.41s /
  41:37). Delta is `+15 passed` (exactly the two new test files, 9 + 6) and
  `+1 skipped` (the already-diagnosed AF_UNIX `sun_path` path-length effect,
  memory `worktree-missing-build-artifacts`). Zero unattributed movement.
- Deletion proof, not a count: forcing the predicate-gate condition to
  `False` (one line) turns exactly 9 tests red —
  `test_order_rank_serve.py::test_non_bijective_control_is_searched` plus
  the 6 re-blessed `test_serve_attempt0_pin.py` rows plus the 2 re-blessed
  `test_cp_mirror_serve.py` mesh rows — with zero collateral on the other
  2,442. Reverted; full re-run green.
- `--baseline` delta (`fixtures/scorecard_baseline.jsonl`, NOT re-blessed
  per COORDINATION.md §1): `quadruped`/`fish`/`insect` are pure
  column-additions (`design_scale: None -> value`, matching `0-scale`'s
  already-attributed figures exactly, nothing else moved). `bird` and
  `humanoid` move for real: `lint_class` BENIGN→PASS, `hull_coverage`
  0.5→0.9848 / 0.6319→0.6638, `design_scale` None→1.515998 / None→0.775554,
  `cp_mirror_residual` 0.053492→0.0 / 0.378336→0.0, `cp_mv_broken`
  None→4 / None→2. `cp_mirror_residual` and `cp_mv_broken` are **Goal 2's
  columns** (COORDINATION.md §1) — flagged here explicitly, not absorbed
  silently, exactly the outcome the spec's §7.3 pre-registered as a "red pin
  needing a re-bless," now executed.
- Honest mesh-path cost, measured both ways on this engine build: bird
  extraction 2.12s→3.55s, fresh serve of the confirmed tree 1.46s→2.95s
  (≈2.0×); humanoid extraction 2.06s→3.50s, fresh serve 1.49s→2.94s
  (≈1.97×). Real, but well short of the spec's own worst-case "bird 4.4s →
  20.1s, ~4×" figure — consistent with that number depending on how many
  extraction-phase probe candidates individually hit the non-bijective
  search branch, which this run's search happened not to hit as often.
- Batching proven (`test_batched_path_matches_per_variant_scales_and_is_fast`):
  one batched spawn's scales are byte-identical to compiling each variant in
  its own isolated spawn, and the batched call completed well under the
  per-variant multi-spawn cost on every measured subject.

**Confidence caveat from the spec, addressed:** claim (a) — the shipped
`test_mesh_to_tree` contract — was already independently confirmed before
this slice started. Claim (b) — the G2a destruction risk from mismarking —
is now directly confirmed (see above), not merely asserted.

Report and every number above verified by driving the real engine on this
worktree's own rebuilt `.so`, not carried from the spec or from the
dispatch prompt.

---

## S7 — CANCELLED at its own Task 0 gate. A clean negative.

S7 proposed ranking the rescue ladder's packs the way S6 ranks attempt-0
siblings, targeting the three subjects S6 could not reach. It was dispatched
**gated**: Task 0 measured the premise before any code was written. The premise
does not hold.

**Evidence — landed `de79b31` (PR #102), 2026-08-15, U5.** That is the commit
that first put it in the repo. Four files, recovered from the unmerged branch
`claude/goal-1-s7-rank-ladder-packs-3bc46a` where they were authored as
`3e2be23`:

* `mcp_harness/probe_ladder_ranks_task0.py` + `fixtures/task0_ladder_probe.json`
  — the table below.
* `mcp_harness/probe_insect_order_exhaustive.py` +
  `fixtures/task0_insect_order_exhaustive.json` — the insect follow-up two
  paragraphs down.

Plus one new file, `mcp_harness/tests/test_task0_ladder_probe_fixture.py`.

**Both probes re-run on `main` at 29dbb5a, and both fixtures reproduce
BYTE-IDENTICALLY** — despite S2'b (`5eb30fb`) and the shaping-composition fix
(`8fffd7d`) landing after they were written. Nothing below is a re-bless; the
numbers are the original ones, re-measured.

The test pins the load-bearing rows AND the probe's grip on the serve path it
monkeypatches (`server._search_first_clean`'s signature), so the next
serve-path change that would break the probe fails the suite instead of
silently rotting the probe. Two things it deliberately does **not** assert,
both recorded in its docstrings: `clean_pack_count < 2` would be a **vacuous
gate** (first-clean-wins returns on the first clean pack, so the probe's tee
can never log a second — "insect saw 1 clean pack" is a property of the
short-circuit, not of insect, which is exactly why the second probe exists);
and the insect comparison checks K2/scale only, because neither fixture records
K1/`stub_flaps`, which dominates it.

**One caveat measured rather than assumed.** The probe reads `is_bijection`
inside the tee — on the RAW pack, before `_repair_and_annotate` rewrites
`edges_assignment` (which it does whenever the serve is dirty, i.e. for
quadruped and fish). Serving all three subjects and re-reading the returned
fold gives `fish 0.653249 / 0.9077 / False / None`, `quadruped 0.599702 /
0.7161 / False / None`, `insect 0.582125 / 0.8595 / True / 6` — **identical to
the fixture on every field.** So the pre/post-repair distinction is a latent
hazard, not an active divergence, and the fish rows are sound for served bytes
as well as raw ones. (`_symmetrize_and_annotate` is default-OFF.)

> ⚠ **This citation previously read "Probe and outputs committed
> (`3e2be23`, …)". They were not committed.** PR #96 (`01134cd`) landed only
> this document; `3e2be23` was never an ancestor of `main`, so for five days
> the entry that CANCELLED S7 cited, as landed evidence, two files no reader
> could open — while a sibling unit was consuming the fish rows below as a
> baseline. **This is COORDINATION.md:45-48's liveness failure recurring, the
> same shape as the PR #76/#78 incident it records:** evidence sitting
> unmerged protects nobody, and a document that cites it as landed is worse
> than one that admits it is not, because it removes the reader's cue to go
> looking. That entry's rule — *land the artifacts immediately; do not hold
> them for a green PR* — applies to EVIDENCE, not just to coordination files.
> Landing a doc that cites an artifact, without the artifact, is the same
> defect wearing a different hat.

| subject | packs_seen | clean | served | scale | coverage |
|---|---|---|---|---|---|
| quadruped | **1** | 0 | stub (stubs=3) | 0.599702 | 0.7161 |
| fish | 2 | **0** | placement/tries=2 (canonical) | 0.653249 | 0.9077 |
| insect | **1** | 1 | order/canonical | 0.582125 | 0.8595 |

> ⚠ **`packs_seen` COUNTS PACKS, NOT ATTEMPTS. Do not read it as "how many
> variants were tried."** The probe's tee logs a row only when
> `fold_str is not None` — a rung that ran and *failed to pack* is forwarded to
> `_search_first_clean` untouched and never appears. So the fixture cannot
> distinguish "variant was never built" from "variant was built and failed.".
>
> A sibling unit re-measured `fish` at attempt level this wave and found what
> this table structurally cannot show: **all five order variants
> (`canonical`, `seeded_0..3`) DID run**, at the order stage, and all five
> failed to pack with `POLYS_NOT_VALID` at the molecule build (scale-at-failure
> 0.471786 / 0.498340 / 0.583904 / 0.536191 / 0.556913); attempt-0 fails
> `NOT_LOCAL_ROOT_CONNECTABLE` @ 0.579991; **dedup removed zero variants**, so
> fish's pool is not narrower than `ORDER_RESTARTS = 4`. Attempt-level data
> lives in that unit's `probe_fish_order_variants.py` /
> `fixtures/fish_order_variants.json` — **which are landing in a sibling PR
> this wave and are NOT on `main` as of this commit.** Said plainly here for
> the obvious reason: citing an unlanded artifact as landed is the defect this
> very section exists to correct.
>
> **This does NOT weaken S7's cancellation, and must not be reported as if it
> does.** Ranking is scoped to the CLEAN set; quadruped and fish produce zero
> clean packs, and ranking zero candidates serves byte-identical output no
> matter how many variants were attempted to get there. The correction is to
> **what a reader may infer from `packs_seen`**, not to the conclusion.
>
> The limitation is recorded here and in `test_task0_ladder_probe_fixture.py`
> rather than in the fixture, because `task0_ladder_probe.json` is a top-level
> JSON **list** and the probe writes a list: adding a `_meta` key would make
> the file a dict, so the probe would no longer regenerate it byte-identically
> — destroying the exact reproduction check that justifies landing it. The
> numbers are correct for what they measure and are NOT re-blessed.

**Ranking within the clean set has zero candidates on all three.** quadruped
and fish never produce a clean pack at any stage, so the short-circuit S7
removes never fires for them. insect produces exactly one; an exhaustive
read-only compile of its other four order variants (using S6's shipped
`_worker_rank_variants`) found `seeded_3` also packs clean, and
`order_rank.rank` picks the served `canonical` over it on **K2 alone**
(0.582125 vs 0.528337). `rank_winner_is_served: True`.

S7 would have served **byte-identical output on all three**.

### The proposed follow-up is refuted by the same probe

The implementing session suggested `_audit_score` (the dirty-pack tie-break)
might be "doing real, un-audited-by-scale work," pointing at fish's two packs.
Its own committed data says otherwise — the two are **identical on every axis
scale or coverage could rank**:

```
pack 0: placement tries=1              scale 0.653249  coverage 0.9077
pack 1: placement tries=2, canonical   scale 0.653249  coverage 0.9077
```

`_audit_score` ties go to the EARLIEST rung, and pack **1** was served — so it
won on strictly fewer lint violations. It is discriminating on the only axis
where the candidates differ. That is correct behaviour, not a gap. **Do not
re-propose it on this evidence.**

### What the negative actually teaches

The ladder's selection policy is not the bottleneck. **Candidate SUPPLY is.**
quadruped has one candidate; nothing can be selected from one. The defect S6
fixed exists structurally one layer down but has **no measured cost**, because
the ladder rarely reaches a second comparable pack at all.

### Goal 1's standing after S6

| subject | coverage | was | scale | lint |
|---|---|---|---|---|
| bird | **0.9848** | 0.5000 | 1.515998 | PASS |
| fish | 0.9077 | 0.9077 | 0.653249 | BENIGN |
| insect | 0.8595 | 0.8595 | 0.582125 | BENIGN |
| quadruped | 0.7161 | 0.7161 | 0.599702 | MIXED |
| humanoid | **0.6638** | 0.6319 | 0.775554 | PASS |

Mean coverage **0.7230 → 0.8264**. Bird went from the corpus's worst subject to
its best. Two of the charter's three clauses are fully delivered (*state how
much* — 0b + 0c; *argue it against scale* — 0-scale + S6's K2). The first
clause moved on 2 of 5.

---

## S8 (order-pool-width probe) — measured 2026-08-10

READ-ONLY. One instrument, `mcp_harness/probe_order_pool_width.py`, forked
from 0α's shape. Writes `mcp_harness/fixtures/order_pool_width.json`. Ships
no behaviour change: `ORDER_RESTARTS`, `order_rank.rank`, and
`server._worker_rank_variants` are all imported and reused unmodified — the
probe's only new code is `order_variants_k`, a parameterized copy of
`rescue_ladder.order_variants` that takes pool width `k` as an argument
instead of the hardwired constant.

**The question**: `order_variants`' docstring says its 4-draw pool is never
topped up "without a measured marginal rescue," and that number
(`ORDER_RESTARTS = 4`) was measured for RESCUE (does *any* variant pack) —
never for RANKING QUALITY (does a wider pool ever change which variant
`order_rank.rank` picks), because ranking (S6) postdates the constant. This
probe measures the second question directly, swept over all 25 subjects in
`tests/cases.py` at k ∈ {4, 8, 12, 20} — not just `bird`/`humanoid`, since
n=2 cannot decide a shared constant (the `n_leaves` confound precedent,
memory `perfect-base-s8-outcome`).

**Superset property: PASS on all 25/25 subjects.** `order_variants_k`
seeds `random.Random(ORDER_SEED)` once per call; each `random_topo_order`
draw consumes exactly `len(nodes)` `rng.randrange` calls regardless of
outcome, so the k-th draw is bitwise identical whether it is the last draw
of a k-draw run or an early draw of a wider one. Asserted, not assumed: a
narrower pool's accepted-variant list is a verified prefix of every wider
pool's, node list and all, for every subject.

**Dedup saturation: never full by k=20, on any of the 21 subjects that
compile a control at all.** `distinct_orderings` (generated, not
necessarily compiling) keeps growing from k=4 to k=20 on every packable
subject — e.g. `star-6`/`star-8`/`star-6-sym` reach the full 20/20 (no
duplicate draws at all up to this width), `hshape` and `quad` grow but
slow down (4→14, 3→10). So a wider pool is not a wasted draw on this
corpus's tree sizes; `ORDER_RESTARTS=4` is genuinely leaving orderings on
the table, not scraping a saturated space. (4 subjects —
`cat-spine5`, `deep-chain`, `dog-raw`, `insect-knife-024` — have no
control to rank against at all; these are the corpus's pinned non-packing
canaries and are out of scope by design, not a probe defect.)

**The ranked winner DOES change for some subjects once k≥8 — this is NOT
the "winner never changes" outcome the dispatch prompt expected, and it is
reported as the finding it is.** Of the 21 rankable subjects, 4 changed
winner somewhere in {8, 12, 20} versus k=4: `cat-long-legs` (scale
0.4932→0.5278, coverage 0.804→0.924, already at k=8), `cat-spine4` (moves
*twice* — k=4/8 winner `seeded_0`, k=12 winner `seeded_8` at the same
scale reading as k=20's different winner `seeded_15` — scale climbs
0.4411→0.4759→0.5010 and coverage 0.839→0.745→0.969 non-monotonically
across widths, the clearest case in the corpus that k=4 is leaving a real
margin unclaimed), **`template-humanoid`** (scale 0.6294→0.6825, +8.4%,
*gains* `is_bijection` False→True, but **coverage moves the wrong way**,
0.5590→0.5519 — a live instance of §1.1(4)'s "coverage and scale are not
coupled in one direction," this time inside a single lever's own pool
rather than across levers), and **`template-insect`** (scale
0.7634→0.8247, +8.0%, coverage 0.789→0.883). 17 of 21 never changed
winner across the whole k=4..20 sweep, `template-bird` among them
(`compiled_ok` is 0 of 4 variants at k=4 and only 2 of 20 even at the
widest pool — bird's variants mostly fail to compile at all, and the ones
that do never beat control's scale).

**`template-bird`/`template-humanoid` are NOT the scorecard's `bird`/
`humanoid` rows — flagged explicitly, not conflated.** `tests/cases.py`'s
templates are the 8/9-node agent-prompt KNOWN-GOOD trees; the frozen
scorecard's `bird`/`humanoid` are mesh-extracted from committed `.glb`
assets via the skeletonization pipeline (`benchmark_subjects.py`,
confirmed live this session — `humanoid` scores `design_scale=0.775554`,
nowhere close to any pool-width reading `template-humanoid` produced here,
because they are different trees with the same anatomical name). S6's own
PROGRESS.md entry makes the same distinction (cases.py's 6 movers are
listed separately from bird/humanoid's mesh-path numbers). This probe
swept the full `tests/cases.py` catalog as specced; reproducing the true
mesh-extracted `bird`/`humanoid` node lists at each pool width would
require re-running mesh extraction per width (heavy pipeline, not in
`tests/cases.py`, not attempted here) and is left as a gap for whichever
slice next touches this lever.

**Cost holds flat across pool width, dominated by spawn overhead, and is
far from S6's quoted per-variant figure.** Batched-compile wall-clock per
subject-width cell is ~2.2-3.5s regardless of k (a k=20 pool is not
meaningfully slower than a k=4 pool — batching amortizes the fixed
`import server`/`import headless_treemaker` cost exactly as S6's design
predicted), but the absolute number is ~50-70x S6's quoted "0.042-0.050s
for six candidates" figure. This probe measures full process wall-clock
(`server._run_isolated`'s spawn-to-join time, unmodified); S6's number
likely excluded process startup or was measured on a warmer OS cache.
Reported as a discrepancy, not resolved — the *shape* (flat with k) is
confirmed, the *magnitude* is not reproduced.

**Frozen-baseline delta (`fixtures/scorecard_baseline.jsonl`, NOT
re-blessed): exactly the known-attributed deltas, nothing else.**
`quadruped`/`fish`/`insect`: `design_scale: None -> value` (0-scale,
`cfdb60a`). `bird`/`humanoid`: `lint_class`/`hull_coverage`/
`design_scale`/`cp_mirror_residual`/`cp_mv_broken` (S6, `cc05027`). No
other row moved.

**Verification:**
- Full suite, this worktree (base `226b61b`): **2473 passed, 11 skipped, 0
  failed** (2144.28s / 35:44). No test file was added for the probe itself
  (unlike 0α, which added 4 fixture-pin tests) — the probe's own
  superset-property and dedup-saturation checks run and print inline each
  invocation, so there is no separate pytest surface to pin, and the
  suite's only possible delta is upstream drift from the two other
  workstreams landing tests concurrently in this repo (memory
  `linux-ci-3-failures-diagnosis-outcome`'s "two workstreams land tests
  daily" note) — none observed here since no test file changed.
- `--baseline` delta: confirmed above, zero unattributed movement.

**Answer to the dispatch question**: widening the order-variant pool past
`ORDER_RESTARTS=4` DOES sometimes change the ranked winner — on this
corpus, 4 of 21 rankable subjects, always for the better on the ranked
axes (scale and/or bijection), never worse on those axes (coverage can
still trade against scale within the improvement, per §1.1(4)). The
'measured marginal rescue' `order_variants`' docstring asks for before
topping up the pool exists in this data. Whether it is worth the ~2x-3x
wall-clock cost of a wider batched spawn on the serve path is a
scoping/product decision this probe does not make — per the dispatch's DO
NOT list, `ORDER_RESTARTS` is untouched here.

⚠ **CORRECTION (S8b): `scorecard_subjects` above was a bare equivalence its
own live check already refuted.** `fixtures/order_pool_width.json`'s
`template-bird -> bird` / `template-humanoid -> humanoid` mapping reads as
"same tree", which this section's own paragraph two above disproves in the
same breath (`humanoid` reads `design_scale=0.775554`, nowhere near any
`template-humanoid` reading). The field is renamed
`scorecard_subjects_nearest_analogue_not_same_tree` and carries an inline
note; `probe_order_pool_width.py`'s `SCORECARD_SUBJECTS` constant is
similarly renamed `NEAREST_ANALOGUE_NOT_SAME_TREE`. Neither the sweep data
nor `order_rank.rank` changed — this is a labelling fix only.

---

## S8b (scorecard-subject order-pool-width probe) — measured 2026-08-14

READ-ONLY, extending S8's question to the trees that actually matter: does a
k=8 order-variant pool move the FROZEN SCORECARD's `bird`/`humanoid` rows
(the only two with `attempt0_pack = True` — quadruped/fish/insect all fail
attempt 0 per S7 and are out of reach by construction). New instrument,
`mcp_harness/probe_scorecard_pool_width.py`, imports and reuses S8's
`probe_order_pool_width.order_variants_k` / `assert_superset` / `rank_pool`
and S6's `order_rank.rank` / `server._worker_rank_variants` UNMODIFIED — its
only new code is (1) extracting and freezing the two real trees so the sweep
needs no re-extraction per width, and (2) the timing-boundary decomposition
below. Writes `fixtures/scorecard_pool_width.json`.

**Width-independence: PASS on both subjects.** S8 recorded that measuring
the real subjects "would need re-running mesh extraction per width" — this
was checked, not assumed, and is wrong: pool width only reaches
`rescue_ladder.order_variants`, a pure function of an already-extracted
tree. `bird` and `humanoid` were each extracted twice via
`auto_mesh_to_metric_tree` (the same call `benchmark_subjects.measure()`
makes) with nothing else changed; both extractions produced byte-identical
`(nodes, pairs)` JSON. Each subject was therefore extracted ONCE and the
frozen tree committed as this probe's fixture.

**attempt0_pack precondition: True on both, and — a live trap this probe
caught in its own first draft — `served_tree != requested nodes` on BOTH,
which is the CORRECT shape, not a failure.** The first version of this
probe checked `served_tree == nodes` literally and reported `attempt0_pack:
False` on both subjects; that check was wrong. S6's re-ranking (§1.1(2) of
CLAUDE.md, PR #94) can serve a *different* depth-1 ordering of the same
tree while `rescue_stage` stays `"none"` — `order_rank.RANK_MARKER` is
deliberately not one of the rescue markers `benchmark_subjects.build_row`
checks, so a re-ranked serve correctly scores `attempt0_pack = True`. Fixed
to classify by the same rescue-marker vocabulary the scorecard itself uses;
both subjects confirmed `reranked_by_s6: True, attempt0_pack: True` — i.e.
both are already inside S6's re-ranking pool at today's `ORDER_RESTARTS=4`,
which is exactly the precondition this probe needs to ask whether widening
that pool helps further.

**Superset property: PASS on both** (k=4's accepted-variant list is an
exact prefix of k=8's, same assertion S8 made, reused unmodified).

**The bird/humanoid × k table:**

| subject | k | winner | design_scale | hull_coverage | distinct_orderings | compiled_ok |
|---|---|---|---|---|---|---|
| bird | 4 | `seeded_3` | 1.515998 | 0.984783 | 5 | 5 |
| bird | 8 | `seeded_3` | 1.515998 | 0.984783 | 9 | 9 |
| humanoid | 4 | `seeded_1` | 0.775554 | 0.663787 | 5 | 4 |
| humanoid | 8 | `seeded_1` | 0.775554 | 0.663787 | 9 | 6 |

Both readings reproduce the frozen scorecard's own numbers exactly (bird
`design_scale=1.515998`/`hull_coverage=0.9848`, humanoid
`design_scale=0.775554`/`hull_coverage=0.6638`, per this section's own
table above) — confirming the extracted-and-frozen tree really is the tree
the scorecard scores, not a near-miss.

**Widening the pool discovers more orderings (5→9 distinct on both) but the
ranked winner does not move.** `seeded_3` (bird) and `seeded_1` (humanoid)
were already inside the k=4 pool and already won there; the four extra
draws at k=8 are all beaten by the same incumbent. This is the opposite
shape from S8's `tests/cases.py` finding (4 of 21 template subjects moved
at k≥8) — on the two subjects that actually matter to the frozen scorecard,
more draws found nothing better.

**📌 DECISION BRANCH FIRED: `DO_NOT_SHIP` — winner did not change at k=8 on
either subject.** Per the dispatch's pre-registered rule, this is the same
outcome as "coverage falls on either" would have been: widening the pool is
not worth shipping. **Goal 1's cheap levers are exhausted, and this closes
on a measurement rather than an analogy.** No planning session, no Goal 2
coordination needed — there is nothing to scope. The sweep was not extended
past k=8 looking for a width where the winner does move; the dispatch
explicitly forbids that and this report names the branch that actually
fired rather than a friendlier one.

**Timing-boundary discrepancy (S6 vs S8): RESOLVED — it is a measurement
boundary, not a contradiction, confirmed by decomposition rather than
inference.** Measured on `bird` at k=4 (5 candidates):

| measurement | seconds |
|---|---|
| `full_spawn_s` (S8's boundary: spawn + import + compile, `_run_isolated`) | 1.2609 |
| `spawn_overhead_only_s` (spawn + import, a no-op worker, zero compile) | 1.5021 |
| `fresh_import_server_s` (independent cross-check: bare `python -c "import server"`) | 1.1903 |
| `in_child_compile_loop_s` (S6's boundary: the worker called in-process, no spawn) | 0.0026 |

`full_spawn_s` and `spawn_overhead_only_s` land in the same ~1.2-1.5s band;
`in_child_compile_loop_s` is three orders of magnitude smaller (~0.5ms per
candidate). **Spawn/import overhead — not the packer — is the entire cost
of a pool-compile call.** S8's ~2.2-3.5s per subject-width cell timed the
full boundary (this probe's smaller absolute number likely reflects a
warmer OS/import cache or fewer concurrent workers than S8's full 25-subject
×4-width sweep); S6's 0.042-0.050s figure timed the in-child loop alone.
Both numbers are correct measurements of different things — the
discrepancy is retired, not just plausibly explained.

**Verification:**
- Full suite, this worktree (base `01134cd` + S8's cherry-picked commit
  `24d1a28`, S8b's own changes present): **2473 passed, 11 skipped, 0
  failed** (1280.23s / 21:20). No test file added — same reasoning as S8:
  the probe's own width-independence/attempt0_pack/superset assertions run
  and print inline each invocation, so there is no separate pytest surface
  to pin, and both new files (`probe_scorecard_pool_width.py`,
  `fixtures/scorecard_pool_width.json`) are outside pytest's collection
  scope. Matches S8's own quoted 2473/11/0 exactly — no drift from the two
  workstreams landing tests concurrently in this repo.
- `--baseline` delta (`fixtures/scorecard_baseline.jsonl`, NOT re-blessed):
  **clean** — `benchmark_subjects.py --baseline fixtures/scorecard_baseline.jsonl`
  reports exactly the five known-attributed `design_scale: None -> value`
  rows (0-scale) and the `bird`/`humanoid` block (S6:
  `lint_class`/`hull_coverage`/`design_scale`/`cp_mirror_residual`/
  `cp_mv_broken`). No other row, and no other axis, moved. This probe is
  read-only as designed.

**Two S8 corrections applied in this same change** (see the ⚠ block above
this section): (1) `order_pool_width.json`'s `scorecard_subjects` bare
equivalence relabelled `scorecard_subjects_nearest_analogue_not_same_tree`
with an inline note; (2) the timing-boundary discrepancy resolved above.

---

# GOAL 1 — CLOSING RECORD (2026-08-14) — ⚠ SUPERSEDED

⚠ **SUPERSEDED 2026-08-15 by the record at the end of this file. Read that one.
This section is kept, not deleted, because keeping it is what made the gap
visible** — its premise survived with its refutation attached, and the next
reader could therefore see that "cheap levers exhausted" had never been tested
against the one lever nobody had pulled.

**What refuted it, in one line:** the required prior-art pass (CLAUDE.md §0)
found the **dangle ROOT** — `tmTree::GetRootNode()` returns `mNodes.front()`
(`treemaker/Source/tmModel/tmTreeClasses/tmTree.cpp:260-263`), and
`rescue_ladder.canonical_order` (`:364`) and `random_topo_order` (`:391`) both
seed from `root_id(nodes)`, so **every order variant, every rescue rung and
every subject in this project's history had emitted the same root.** Four of
this section's claims are now wrong — **do not cite any of them without the
right-hand column**:

| this section claimed | corrected to |
|---|---|
| clause 1 moved on **2 of 5** | **3 of 5** — `quadruped` also moved |
| `quadruped` is a **packer-capacity problem out of this goal's scope** | **wrong on both halves.** It moved on five axes without touching the packer: coverage 0.7161 → **0.8797**, scale 0.599702 → **0.724628**, `lint_class` MIXED → **BENIGN**, `stub_flaps` 3 → **0**, `layer_order` contradiction → **consistent** |
| mean coverage 0.7230 → **0.8264** | 0.7230 → 0.8264 → **0.8591** |
| S6 is *"the only slice that moved coverage"* (What shipped table) | true when written, **now false** — the root wave (#107/#108/#110/#118) moved `quadruped` coverage 0.7161 → 0.8797. There are **two** coverage levers, ORDER and ROOT |

**What in it still stands:** every refutation in "What was refuted" below —
the axis premise, S4b-general, S7 and S8b are all correctly closed, and none
of them was reopened. The error was never in what it measured; it was in
generalising four negatives on *selection* into a claim about the *goal*.

---

The cheap-lever search is **exhausted on a measurement, not on an assumption.**
S8b's pre-registered rule fired `DO_NOT_SHIP` and this closes the arc.

## What the goal moved

| subject | coverage now | at goal start | scale | lint |
|---|---|---|---|---|
| bird | **0.9848** | 0.5000 | 1.515998 | PASS |
| fish | 0.9077 | 0.9077 | 0.653249 | BENIGN |
| insect | 0.8595 | 0.8595 | 0.582125 | BENIGN |
| quadruped | 0.7161 | 0.7161 | 0.599702 | MIXED |
| humanoid | **0.6638** | 0.6319 | 0.775554 | PASS |

**Mean coverage 0.7230 → 0.8264.** `bird` went from the corpus's worst subject
to its best, and `lint_class` went `BENIGN → PASS` on both moved subjects — the
flat-foldability verdict, which outranks both coverage and scale.

Against the charter's three clauses:

1. *models reach more of the square* — moved on **2 of 5**.
2. *the system can state how much* — ✅ `hull_coverage` as a true boundary
   polygon (0b) and a server-side badge that names its fallback (0c).
3. *it can argue that against design scale* — ✅ `design_scale` on the
   scorecard (0-scale) and shipped as ranking key **K2** with `hull_coverage`
   deliberately **not** a key (S6).

Clauses 2 and 3 are fully delivered. Clause 1 is where the ceiling sits.

## What shipped

| slice | result |
|---|---|
| S4a′ | projection guards; refuse non-45°/non-square; margin proxy |
| 0α | the axis-corner-capacity premise instrument |
| 0b | `hull_coverage` = true boundary polygon, fallback NAMED |
| 0-scale | `design_scale` column + one shared `scale=` parser |
| 0c | the coverage badge, reading raw `json`, `source` carried |
| S4b₀ | book/90° as exact integer rows; `maxr`/`ran` in `projection_report()` |
| **S6** | **rank the attempt-0 pack — the only slice that moved coverage** |

## What was refuted, and this is the more valuable half

- **The goal's founding premise.** "Coverage comes from choosing the symmetry
  axis" was optimizer-only, and S4b₀ proved it cannot be converted: book0 is
  rejected downstream on 4 of 4 production templates, never for projection
  precision (`QUADRUPED` saturates the 50-iteration cap at
  `maxr = 2.86e-10`). **The dead lever is corner pinning, not the axis** —
  dead at both axes for different reasons. CLAUDE.md §1.1(2) corrected (PR #95).
- **S4b-general** — cancelled. Its gate cannot be met; an Opus-max slice closed
  by a Sonnet-high negative.
- **S7** — cancelled at its own Task 0 gate. Ranking the rescue ladder has zero
  candidates on all three target subjects; it would have served byte-identical
  output. Selection is not the bottleneck.
- **S8b** — `DO_NOT_SHIP`, non-vacuously: k=8 compiled **9** candidates against
  k=4's 5 on both subjects, `dedup_saturated: false`, and every extra draw lost
  to the incumbent. Pool width does not move the real scorecard.

## What is left, and why it is out of this goal's scope

⚠ **THIS ENTIRE SECTION IS WRONG AND IS THE REASON THE RECORD WAS REOPENED.**
`quadruped` was not out of scope and needed no packer work: re-rooting moved it
on five axes (see the 2026-08-15 record). Its three premises each failed for a
different reason — "3 invented flaps" was already 0 by `70c3b6d`, "exactly one
candidate" counted candidates at a **fixed root**, and "no ranking, no pool
width and no axis can act on a single candidate" is true and irrelevant,
because re-rooting does not rank candidates — **it builds a different problem
instance.** Kept as written; the lesson is in the mistake.

`quadruped` is the laggard at 0.7161 and it is **not a selection problem**. It
serves at the `stub` stage with **3 invented flaps** and `lint_class: MIXED` —
order, placement, normalize and jitter all failed before it got there. It has
exactly **one** candidate because it barely packs. No ranking, no pool width and
no axis can act on a single candidate.

That is a **packer-capacity** problem, and project memory already places it
outside a gate-or-selection fix (`perfect-base-s8-outcome`: ">8 leaves is a
PACKER problem, not a gate problem"). Naming it here so the next person does not
re-derive the same three negatives to reach it.

## The one open cross-goal item

> ⚠ **SUPERSEDED — DISCHARGED 2026-08-16.** This was written before the root
> wave and its attribution list is **incomplete**: it names only #85 and #94,
> and misses #107, #118, #119 and #125 entirely. The re-bless happened once,
> over `1c9abe0..153f9c7`, with **36 attributed cells across 6 owning
> slices**. See "THE OPEN CROSS-GOAL ITEMS" §2 in the closing record below,
> and the fixture's own `_meta.attribution`, which is authoritative.

**The combined frozen-baseline re-bless.** `scorecard_baseline.jsonl` is still
frozen at `1c9abe0` and must be re-blessed **once**, with a full attribution
table in `_meta`, when both goals finish. Every row currently moved is
attributed: five `design_scale` column-additions (0-scale, `cfdb60a`) and the
bird/humanoid block (S6, `cc05027` — `lint_class`, `hull_coverage`,
`cp_mirror_residual`, `cp_mv_broken`). Goal 2's S2′a has shipped; confirm S2′b's
state with Goal 2 before scheduling it.

---

# GOAL 1 — CLOSING RECORD (2026-08-15)

**Supersedes the 2026-08-14 record above**, which is kept with its refutation
attached. That record closed the goal on four measured negatives about
*selection*; this one closes it on a **structural argument about the engine**,
which is a different and much stronger kind of stop. The difference matters:
"we tried the cheap things" invites a fifth try, and a fifth try is exactly
what overturned it. "The creased region is by construction the convex hull of
the leaf nodes, and no knob in this engine has a coverage term" does not.

---

### ⚠ Provenance — what this record was written against, and what was NOT on it

This record was written on a branch off **PR #120's head (`054fd07`)**, the
integration merge of the root wave. **Not everything it cites was on that
branch**, and the distinction matters for anyone reproducing a number:

| carried by `054fd07` | measured, PR open at the time of writing |
|---|---|
| the root wave: #107, #108, #110, #118, #119 (and, via main, S6/#94 and the `design_scale` column) — **this is where every number in "THE FINAL NUMBERS" comes from, and they were re-run here, not copied** | #101 (`hull_coverage` required-fail inputs), #103 (fish order variants), #105 (`mv_repair` weight sweep), #106 (`tmEdgeOptimizer` binding) |

The right-hand column is **read-only probe and test work** — none of it changes
the serve path, and the scorecard is identical with or without it, which is why
its absence does not qualify any measured row here. Its numbers are quoted from
those PRs' own reports and are flagged as such; **the engine and prior-art
citations underpinning the structural ruling were independently re-verified
against the vendored source on this branch**, not taken from the PRs.

## THE FINAL NUMBERS

`benchmark_subjects.py --baseline fixtures/scorecard_baseline.jsonl`, the real
serve path, at PR #120 (`054fd07`) — **re-run for this record and reproduced
exactly**, with no re-bless (`scorecard_baseline.jsonl` untouched).

| subject | coverage | scale | lint | cp_symmetric | cp_mv_broken | stubs | served stage |
|---|---|---|---|---|---|---|---|
| bird | 0.9848 | 1.515998 | PASS | False | 4 | 0 | none |
| fish | 0.9077 | 0.653249 | BENIGN | False | null (no bijection) | 0 | placement |
| insect | 0.8595 | 0.582125 | PASS | True | 0 | 0 | order |
| **quadruped** | **0.8797** | **0.724628** | **BENIGN** | False ‡ | 8 ‡ | **0** | placement |
| humanoid | 0.6638 | 0.775554 | PASS | True | 0 | 0 | none |

> ‡ **THIS TABLE IS A DATED SNAPSHOT, NOT A LIVE VIEW — and these two cells
> have since moved.** The values in the row above are left **exactly as
> measured at PR #120 (`054fd07`)**, because that is what the header claims
> the table is; overwriting them would make the header false and mix two
> measurement points inside one table presented as one run.
>
> **Current state (re-measured 2026-08-16 on the same serve path):
> `cp_symmetric` **True**, `cp_mv_broken` **0**.** PR #125's `MAX_ORBITS`
> ruling moved them — see "THE OPEN CROSS-GOAL ITEMS" §1.
>
> **Only those two cells moved.** That is what §1 predicted, and the re-bless
> bisection of the #119 → #125 segment independently confirmed it: every
> other value in this table was re-run on the real serve path and reproduced
> **exactly**. The live view is
> `mcp_harness/fixtures/scorecard_baseline.jsonl`.

**Mean `hull_coverage` 0.7230 (goal start) → 0.8264 (pre-wave) → 0.8343 (at
#110) → 0.8591 (now).** Suite **2645 passed / 11 skipped / 0 failed** in
3242.04 s — run for this record, not carried over. The scorecard above was run
twice here (before and after the record was written) and is **byte-identical
both times**, which is the check that matters for a documentation unit: the
prose moved, the behaviour did not.

### ⚠ `quadruped` is the headline correction

The 2026-08-14 record parked it at 0.7161 as "a packer-capacity problem, out of
this goal's scope". It moved on **five** axes, and the packer was never touched:

| axis | before | after |
|---|---|---|
| `hull_coverage` | 0.7161 | **0.8797** |
| `design_scale` | 0.599702 | **0.724628** (+20.8%) |
| `lint_class` | MIXED | **BENIGN** — the last MIXED in the corpus |
| `stub_flaps` | 3 | **0** — all three engine-invented flaps eliminated |
| `layer_order` | contradiction: `taco-tortilla crease (62, 66) through face 59` | **consistent** |

⚠ **Attribution is BISECTED, not inferred** (PR #120 re-ran the scorecard at the
merge base `70c3b6d` precisely because inferring it from each PR's own report
got two rows wrong). Do not re-credit these from PR bodies:

| axis | 0.7161 → 0.7559 → 0.8797 |
|---|---|
| `hull_coverage` | 0.7161 → 0.7559 owned by the #107/#108/#110 root-rank arc; **0.7559 → 0.8797 owned by #118** (leaf-root admissibility, root 5 → root 8) |
| `design_scale` | → 0.714351 at #110; **0.714351 → 0.724628 by #118** |
| `stub_flaps` 3 → 0, `lint_class` MIXED → BENIGN, stage `stub` → `placement` | **already landed at #110.** NOT #118's — #118's own `_MOVED` fixture is about `template-quadruped`, a `cases.py` tree, not the mesh-extracted `quadruped` the scorecard serves. The same template-vs-mesh confusion the S8b record warns about, caught a second time |

### The lever, and why it had never been pulled

Lang's TreeMaker 5 help (`Action→Build Crease Pattern`) says the M/V colouring
*"depends on the particular arrangement of flaps in the flattened base, and so
there are many possible MVF colorings"*, selected by the `dangle` algorithm
from a picked-up node. In the vendored engine that node is **positional**:

| citation | verified |
|---|---|
| `tmTree::GetRootNode()` returns `mNodes.front()` | `tmTree.cpp:260-263` ✅ exact |
| `rescue_ladder.canonical_order` seeds from `root_id(nodes)` | `rescue_ladder.py:350` (def), `:364` (seed) ✅ |
| `rescue_ladder.random_topo_order` seeds from `root_id(nodes)` | `rescue_ladder.py:386-401` (def), `:391` (seed) ✅ |

⇒ **every order variant, every rescue rung, every subject, for the project's
entire history, emitted the same ROG root.** Re-rooting is not a tie-break and
not a restart: it builds a **different facet-ordering graph**, i.e. a different
problem instance. That is why Goal 2's "225/225 M/V creases are order-forced"
result — true of *one* such graph — said nothing about it, and why four
negatives on *selection* could not have found it.

**Coverage's lever list now reads: node ORDER (S6, PR #94) and node ROOT
(#107/#108/#110/#118). Neither is the axis, and neither is a pin.**

⚠ **And it was nearly missed a SECOND time, after the lever was already built.**
U1' shipped the root stage with an admissibility filter keyed on
`rescue_ladder.leaf_ids`, which **excluded every leaf root** — and quadruped's
winning root 8 is a leaf. The filter was **shadowing the ranking key**: it
refused root 8, which *"DOMINATES the shipped root 5 on every measured axis
(scale 0.724628 vs 0.714351, coverage 0.8797 vs 0.7559, 8 M/V defects vs 10,
both zero stubs, both layer-consistent, both cp_audit clean)"*
(`root_rank.py:106-110`). #118 measured the filter's premise and found it false
— the engine never lost the flap, and TreeMaker's own help says *"Any tree node
(leaf or branch) can be the root node."* **The lesson generalises: a
conservative pre-filter in front of a measured ranking key can silently delete
the win the key was built to find.**

---

## THE CHARTER, ANSWERED CLAUSE BY CLAUSE

> *"Done means: models reach more of the square, **and** the system can state
> how much, **and** it can argue that against design scale instead of moving it
> silently."*

| # | clause | verdict |
|---|---|---|
| 1 | *models reach more of the square* | **moved on 3 of 5** — `bird` 0.5000 → 0.9848, `humanoid` 0.6319 → 0.6638, `quadruped` 0.7161 → 0.8797. `fish` and `insect` unchanged at 0.9077 / 0.8595 |
| 2 | *the system can state how much* | ✅ `hull_coverage` as a true boundary polygon (0b, PR #81), a server-side badge that names its fallback (0c, PR #87), and — new this wave — the fallback's **required-fail inputs and its named ceiling** (PR #101) |
| 3 | *it can argue that against design scale* | ✅ `design_scale` on the scorecard (0-scale, `cfdb60a`) and shipped as ranking key **K2** in `order_rank.rank_key` (`order_rank.py:143`, K2 documented at `:148`), with `hull_coverage` deliberately **not** a key — **on BOTH ranking stages** |

Clauses 2 and 3 were already delivered at the previous record and are unchanged.
Clause 1 is where the ceiling sits, and the next section says why the ceiling is
where it is.

⚠ **Clause 3's discipline was re-affirmed by the root stage, not merely
inherited.** Verified: the string `hull_coverage` occurs **zero** times in
`order_rank.py`, and its three occurrences in `root_rank.py` are all prose —
`root_rank.py:64` states the rule in its own words, *"`hull_coverage` is not a
key at all, for the reason S6 gives: no measured arm ever reached it."*

★ **And the root stage produced the best evidence yet that ranking on scale is
the right discipline — because it is what PROTECTED bird's coverage.**
`bird`'s leaf roots collapse `hull_coverage` **0.9848 → 0.5** and lose the
vertex bijection. They are refused **by K2** — `design_scale` 1.095885 against
the control's 1.515998 — and are rejected before K3 is even reached
(`root_rank.py:99-106`). No coverage key was needed or used. That is the
strongest form the clause can take: **coverage was defended by the scale
argument, not by a coverage objective**, which is exactly what §1.1(4) asks for
and the opposite of moving it silently.

---

## ★ WHY FULL SQUARE COVERAGE IS NOT REACHABLE IN THIS ENGINE

**This is the section the previous record lacked, and it is the most valuable
thing in this file, because it is what stops the next person re-deriving four
negatives to arrive at the same place.** The previous record's stop was
empirical ("cheap levers exhausted"). This one is structural, it is checkable,
and every line number below was read and confirmed at `054fd07`.

### 1. The creased region IS the leaf hull, by construction

| what | where | verified |
|---|---|---|
| `tmTree::CalcBorderNodesAndPaths()` — gift-wraps the **leaf node positions** into a convex hull, setting `mIsBorderNode` / `mIsBorderPath` | `tmTree.cpp:2024` (comment block opens `:2019`, body ends `:2105`); **called at `:2725`** | ✅ exact |
| its body contains **zero** references to `mPaperWidth` / `mPaperHeight` | `tmTree.cpp:2024-2105`, `grep -c` → **0** | ✅ |
| `tmTree::CalcPolygonValidity()` — the completeness gate, likewise over `leafNodes` | `tmTree.cpp:2219-2248` (comment `:2219`, `void` at `:2225`, closes `:2248`); called at `:2735` | ✅ |

The paper dimensions enter the hull computation **nowhere**. The only two
mentions of "paper" inside `CalcBorderNodesAndPaths` are *comments* — `:2030`
("a starting point that lies below and outside the paper", describing the
gift-wrap seed) and `:2052`. The sheet is a constraint on where leaves may
*sit*; it is not an input to what gets creased.

⚠ Note what this means for the `mcp_harness/free_paper.py` premise, and for
`square_complete.py`: the uncreased margin is **not a bug to be fixed inside
the hull computation**. There is no term in there to fix.

### 2. Nothing in the objective wants coverage

| what | where | verified |
|---|---|---|
| `tmScaleOptimizerObjective::Func` returns **`-u[0]`** — maximise scale, full stop | `tmScaleOptimizer.cpp:175-180` (`Func` at `:175`, `return -u[0];` at `:180`) | ✅ exact |
| `Grad` sets `du[0] = -1` and zeroes the rest | `tmScaleOptimizer.cpp:192` | ✅ exact |

**There is no coverage term anywhere in the objective.** Coverage is not
traded away by the optimizer — it is not represented to it. Every coverage
movement this project has measured is therefore a *side effect* of moving the
problem instance (order, root), never an optimization of coverage, and that is
a permanent property of the objective as vendored.

### 3. The engine rejects, rather than fills, the configurations that would help

| what | where | verified |
|---|---|---|
| `POLYS_MULTIPLE_IBPS` raised when any poly has >1 inactive border path | predicate tested `tmTree.cpp:1846`; **raise block `:1849-1854`** (`return POLYS_MULTIPLE_IBPS;` at `:1853`) | ⚠ the previously circulated `1848-1854` is off by one at the start — `:1848` is the `for` loop's closing brace |
| `tmPoly::GetNumInactiveBorderPaths()` | `tmPoly.cpp:1158-1169` (comment `:1158`, `size_t` at `:1161`, closes `:1169`) | ✅ |
| top-level polys that are non-convex **or enclose another leaf node** are **deleted** | `tmTree.cpp:1747-1751` | ✅ exact |

### 4. Lang and Demaine say this is the design, not a defect

All quotes below were extracted from the primary sources and checked
word-for-word; where an earlier circulated paraphrase was wrong, the correction
is marked.

**Lang & Demaine, *Facet Ordering and Crease Assignment in Uniaxial Bases*,
Origami⁴, ch. 17 (p. 189 ff.), §2.2 "Molecules", p. 193** —
https://erikdemaine.org/papers/TreeMaker_OSME2006/paper.pdf

> *"We first note that any paper outside of the convex hull of the leaf vertices
> is effectively unused. In practice, it can be folded underneath and the
> resulting polygon treated as a single sheet of paper; in the interest of
> brevity, we will ignore it going forward and will assume that the paper P and
> the convex hull of the leaf node vertices PH are one and the same."*

Two consequences that settle long-running arguments in this repo:

1. **`POLYS_MULTIPLE_IBPS` is literally their well-formedness condition 2.**
   ⚠ **Two corrections to how this has been cited here.** The conditions sit at
   the **end of §2.1 "Optimization"**, immediately *before* §2.2 (same page
   193), and condition 2 is stated **positively** and in **hull**, not border,
   vocabulary:

   > *"A set of leaf node vertices in a polygon P with convex hull PH is said to
   > be well-formed with respect to a tree graph if it satisfies the following
   > properties: 1. Every point within the convex hull lies within some active
   > polygon. 2. Every active polygon contains at most one inactive hull path."*

   TreeMaker's own help calls the same object a **border** path, which is where
   our `IBP` (inactive border path) naming comes from, so the concepts coincide
   — but **cite the paper as "hull path"**. It is not our compiler being
   fragile: project memory (`polys-multiple-ibps-is-inherent`) reached the same
   verdict empirically against Lang's 5.0.1 source; this is the citation that
   explains *why*.
2. **Their prescribed repair is to add flaps** — and they say plainly that the
   optimizer does not deliver well-formedness on its own:

   > *"There is no guarantee that a solution to Equation (3) satisfies these two
   > conditions; it is not uncommon to find a solution with active paths all
   > around the boundary and one or more unconstrained leaf vertices "rattling
   > around" in the interior of the polygon. However, it is usually possible to
   > either add additional edges to the tree graph or to selectively lengthen
   > certain edges of the tree graph to attain the well-formed state—and
   > importantly, this is accomplished without reducing the size of the original
   > graph; the solution to Equation (3) remains an optimum."*

   Spend anatomy, or spend proportion, but do not shrink the design.

**TreeMaker's own help calls the leaf hull "the useful area" of the paper.**
⚠ **Attribute this to the TreeMaker 5 help (`Source/help/menus.htm`), NOT the
4.0 manual** — the phrase "useful area" does **not** occur anywhere in
`TreeMkr40.pdf`, which uses only "border node" / "border path". Verbatim:

> *"The convex hull of all the leaf nodes is called the useful area of the
> paper."*

And `overview.htm` states the whole ruling in TreeMaker's own voice, independent
of the paper:

> *"In a TreeMaker base, the minimum paper needed to fold the base is the convex
> hull of the leaf nodes. Any paper that lies outside the convex hull (like
> three of the corners in the image above) is unused in the base. It could
> effectively be cut off, but in practice, it is usually just folded over and
> the resulting polygon folded as if it were a single sheet."*

The paper outside the hull is not a deficiency the tool is failing to address;
it is a region the tool has **defined out of the problem** — asserted by the
author in the paper *and* in the software's own documentation. Three
independent primary sources now back memory `export-emits-hull-not-square`, and
its "LIKELY PERMANENT" tag is well-founded.

**The same help is also the primary source for the ROOT lever**, and it states
the mechanism outright — worth quoting because it is the sentence that would
have saved this project four negatives (`overview.htm`):

> *"The tree node with index 1 is called the root node… Any tree node (leaf or
> branch) can be the root node. If you make a different choice of root node, you
> will get a different folded form and a different MVF crease assignment."*

and (`menus.htm`, `Build Crease Pattern`):

> *"The MVF coloring, however, depends on the particular arrangement of flaps in
> the flattened base, and so there are many possible MVF colorings."*
>
> *"TreeMaker chooses the flap arrangement from an algorithm called the "dangle"
> algorithm, in which (figuratively) one node of the tree is picked up and the
> remainder of the tree is allowed to dangle under the force of gravity…"*

⚠ **"Any tree node (leaf or branch) can be the root node"** is also the
independent documentary confirmation of #118's result (leaf roots ARE
admissible) — the engine never lost the flap, and the help said so all along.

### 5. ⇒ THE RULING

> **Full square coverage is not reachable within tree theory as TreeMaker
> implements it.** Reaching it requires either **adding tree nodes** — which
> spends anatomy, and `stub_flaps` is ranking key **K1**, above scale,
> precisely so that anatomy is never spent silently — or a **different
> paradigm**.

The different paradigm exists and is worth naming so nobody re-invents it:
**"COrigami: An AI Pipeline for Co-Designing Flat-Foldable Visually
Recognisable Origami"** (arXiv:2606.26299v1 [cs.AI], submitted 24 June 2026,
https://arxiv.org/abs/2606.26299 — Zahavy et al., 19 authors, **Robert J. Lang
14th**). It reaches full coverage via **grid box-pleating plus an explicit
flap-expansion tiling pass** — *not* via circle packing, which is what this
repo's Tier 3 compiler is. Adopting it is a **Tier-3 replacement, not a slice.**

⚠ **Locator correction: none of this is in the abstract** (which lists only the
pipeline stages). Cite the body and Figure 1:

- **box-pleating** — Fig. 1 caption: *"automated box-pleated crease pattern
  layout"*; body: *"modern computational design relies heavily on "box pleating"
  (BP), which restricts all structural creases to an orthogonal integer grid
  intersected by 45-degree diagonal ridges."*
- **full coverage, framed as *contiguous tiling*** — *"Only COrigami provides an
  end-to-end, fully automated pipeline that guarantees contiguous 2D tiling on a
  discrete orthogonal grid directly from natural language."*
- **the flap-expansion pass** (their stage "Tiling (via Flap Expansion)") —
  *"the algorithm must eliminate all residual gaps to achieve a perfect
  tiling—a mathematical prerequisite for generating a physically viable base
  crease pattern. The system identifies all unoccupied cells and, for each,
  computes feasible geometric expansions of adjacent flaps that will cover that
  cell."*

⚠⚠ **CITE THEIR 1.1% AS THEIRS, WITH THEIR OWN CAVEAT ATTACHED — OR NOT AT
ALL.** Their Table 3 ("TreeMaker results on 66,036 stick figures") reads
Success **743 (1.1%)**, CP construction failed 49,120 (74.4%), scale
optimisation failed 7,012 (10.6%), flat-foldability violation 8,736 (13.2%),
timeout 425 (0.6%). That is **their** measurement of **their** harness on
**their** corpus, not an independent audit of this engine, and our numbers are
not comparable to it.

**And the authors explicitly discount it**, in terms that matter here more than
the figure does:

> *"because TreeMaker relies heavily on human-in-the-loop interactions to
> resolve complex topologies, its performance in this fully automated benchmark
> likely under represents its efficacy, as critical manual interventions were
> bypassed"*

The interventions they list as bypassed are, almost line for line, **this
project's own slice list**: *"imposing symmetry conditions by pairing nodes
about a symmetry line, fracturing high-order polygons by adding auxiliary
stubs, forcing leaf nodes to paper edges to reduce layer count, and manually
repositioning nodes to escape local optima."*

⇒ **Read the 1.1% as a floor for an unassisted pipeline, never as a ceiling for
this one.** It is not evidence that our rescue ladder is futile — it is evidence
that the ladder is the *right category of work*, and that its yield is the thing
separating us from that floor. What it does support is narrower and is the
recommendation this record leaves: **a sixth coverage lever inside circle
packing is not where the remaining square is.**

---

## WHAT WAS MEASURED AND REFUTED THIS WAVE

Three pre-registered gates, three non-firings, and **each one is more specific
than "did not help"** — which is the whole point of writing them down.

### Edge optimization — a MECHANISM-LEVEL ceiling, not a tuning shortfall (PR #106)

`tmEdgeOptimizer` is **Lang's own tool for exactly this problem** — TM4 manual
§6.4: *"Edge optimization is used to selectively lengthen points by the same
relative amount to 'fill out' a crease pattern."* It has been vendored since
the first TreeMaker import and had **zero** references in
`TreemakerWrapper.cpp`. PR #106 bound it to Python for the first time.

ⓘ *That §6.4 quote is carried from PR #106's report and was **not**
independently re-verified for this record* (unlike the engine and Lang &
Demaine citations above, which were). Treat it accordingly. ⚠ Related, and
verified: **"useful area" is NOT in the 4.0 manual** — see §4 above — so do not
assume the two TreeMaker documents are interchangeable when citing.

> **Gate:** ship a production path only if `hull_coverage` rises by ≥0.05 on ≥1
> of quadruped/fish/insect with `design_scale` not falling and `lint_class` not
> worsening. **DID NOT FIRE.**

| subject | coverage | Δ | scale | lint | leaves pinned |
|---|---|---|---|---|---|
| quadruped | 0.7161 → 0.7191 | **+0.0030** (1/17th of the bar) | 0.599702 → 0.599702 (bit-identical) | MIXED → MIXED | 9 → 10 |
| fish | 0.9077 → 0.9077 | 0.0000 | unchanged | MIXED → MIXED | 7 → 7 |
| insect | *refused* | — | — | — | — |
| bird *(control)* | *refused* | — | — | — | — |
| star-4 *(control)* | *refused* | — | — | — | — |

**The three refusals are the finding.** They raise `EX_NO_MOVING_NODES` because
their packs are **already fully pinned**:

- `tmEdgeOptimizer::Initialize` calls `theTree->FilterMovableParts(...)` at
  `tmEdgeOptimizer.cpp:39`, then throws `EX_NO_MOVING_NODES` at `:41` when the
  moving-node list is empty ✅ verified
- `tmTree::FilterMovableParts` strips every **pinned** leaf — `tmTree.cpp:1462`
  ✅ verified exact (comment block `:1458-1461`)
- `EX_NO_MOVING_NODES` is declared at `tmEdgeOptimizer.h:26` ✅

⇒ **This is a mechanism-level ceiling on the lever, not a shortfall of the
constants.** There is nothing a shared edge strain can buy on a fully-pinned
tree. No sweep, no schedule and no relaxation reaches it, and this is a far more
precise parking argument than "cheap levers exhausted" — it says *which* trees
the lever can never touch and *why*.

**Record the one positive, because it proves the mechanism itself works.**
`cat-spine5` goes **BUILD-FAIL (`POLYS_NOT_FILLED`) → BUILD-OK**, leaves pinned
5/6 → **6/6**, at max strain **+0.589633**, with `design_scale` **0.349429 →
0.349429, unchanged**. Lang's mechanism does exactly what the manual says — on
trees that are **not yet pinned**. Goal 1's laggards are all on the other side
of that line. Anatomy cost was priced rather than assumed: 2.74% max / 0.69% RMS
relative strain, and the one strained edge is a **requested limb**
(0.269426 → 0.276817), not an engine-invented stub.

### `mv_repair` weight sweep — flat, and the a-priori bound is ~40× too tight (PR #105)

> **DID NOT FIRE.** `lint_class` MIXED at every arm.

Every requested weight **3 – 12 collapses to effective weight 3**: weights 6 and
8 visit an identical **173,205** nodes and return an identical flip set, so
raising `DEFAULT_MAX_WEIGHT` 6 → 8 is **provably inert**, not merely unhelpful.
`hull_coverage` 0.7161, `design_scale` 0.599702 and `stub_flaps` 3 are identical
on every arm.

**But the sweep found a real defect in the budget logic, and it is the reusable
part.** `_effective_weight` denies weight 4 a priori on a worst-case `C(196,4)`
= **59.6M** node estimate against the 20M cap. Bought outright, weight 4 actually
traverses **1,523,430** nodes in 3.85 s — comfortably inside the shipped cap.

> **The a-priori combinatorial gate is ~40× too conservative** (59.6M estimated
> vs 1.52M actual), and it is **redundant**: the DFS already carries a *live*
> `max_nodes` counter (`stopped = "node_cap"`). It is belt-and-braces that is
> costing real repair.

It still does not reach the goal — 15 interior defects remain at weight 5 and
Oriedita still read MIXED — which is why it was reported and not shipped as a
default change. ⚠ **And quadruped's `lint_class` reached BENIGN anyway, by
re-rooting, without any of it.** The budget finding survives as a standing
efficiency defect, now decoupled from the subject that surfaced it.

Two incidental findings kept: the env var is **`IDE_MV_REPAIR_MAX_WEIGHT`**, not
`IDE_MV_REPAIR_WEIGHT`; and `layer_order` already rejected quadruped's served
base *before any repair* — `contradiction: taco-tortilla crease (62, 66) through
face 59`, the contradiction that the root wave has since cleared.

### Fish order variants — the gate did not fire and **the unit's own premise was falsified** (PR #103)

The unit was chartered on the belief that `fish`'s placement rung compiled only
`canonical`, so `order_variants`' four seeded draws were **never built**.

**All five were built. All five died `POLYS_NOT_VALID` at the molecule build.**

★ **The transferable finding is about the instrument, not about fish.** The S7
Task-0 fixture **records only *packs*, so it structurally cannot distinguish
"variant never built" from "variant built and failed to pack."**

| | |
|---|---|
| order variants that actually ran | **5** |
| order variants that packed | **0** |
| order variants visible in the S7 log | **0** |
| S7 `packs_seen` | 2 (both `placement`) |

A reader who takes `packs_seen: 2` to mean "the ladder only tried 2 things" is
**wrong by five rungs**. ⚠ This does **not** reopen S7: its gate was about
*ranking* packs, fish and quadruped produce zero clean packs at any stage, and
ranking zero packs is byte-identical either way. **The cancellation stands on
its own arithmetic; what is now off-limits is reading those counts as search
breadth.** Another instance of COORDINATION.md §4.1's recurring shape — a metric
that cannot express the defect it is named after.

---

## THE `hull_coverage` METRIC DEBT, DISCHARGED (PR #101)

COORDINATION.md §4.1 requires every metric to ship with an input it is
*required* to score as failing. `hull_coverage`'s **primary** path
(`source == "boundary_cycle"`) already had three. The residue was the two
**convex-hull fallbacks**, whose entire coverage was full-square fixtures
reading 1.0 and one `coverage > 0.0` assertion **that no input can fail** —
exactly the shape §4.1 exists to catch.

Three required-fail inputs now ship:

| input | asserts |
|---|---|
| two disjoint B loops **confined** to the bottom-left corner | `source == "boundary_edges"` **and** `coverage == 0.0325` |
| the **same** six-vertex two-loop topology **spread** across the sheet | `0.75` — the causation control: identical vertex count, identical edge list, identical `source`, **only the geometry differs** |
| no B edges at all, every vertex inside a 0.2 box | `source == "all_vertices"` **and** `coverage == 0.04` |

**Proved by mutation, not by inspection.** Replacing the fallback with the
maximally-flattering implementation (`hull_area = paper_w * paper_h`, literally
"a number that only goes up") **fails all three new tests — and both
pre-existing fallback tests still PASS.** That is the direct demonstration that
the old coverage was vacuous against precisely the implementation §4.1 exists to
catch, and that the new coverage is not.

### ⚠ The named ceiling — a READING RULE, not a bug

A fourth test records what the fallback **cannot** claim: four tiny corner
B-loops crease **0.005** of the sheet and the hull reports a flawless
**1.000000** — a **200× overstatement**. Nothing is fixable inside the fallback
(with no walkable border there is no polygon to measure), so it pins a rule:

> **On `boundary_edges` / `all_vertices`, `coverage` is an UPPER BOUND on
> creased area, never a measurement. Read `source` before quoting the number.**

The test says in its own docstring that it is **not** the §4.1 discharge — any
always-1.0 stub satisfies it. ⚠ **All nine committed goldens take the
`boundary_cycle` path — pinned by
`test_all_committed_goldens_report_boundary_cycle`**, which is the fact that is
asserted rather than assumed. The scorecard subjects serve real crease patterns
with walkable borders and are expected to do the same; **that was not
separately re-pinned here, so if you ever quote a scorecard coverage in a
context where the distinction matters, read its `source` first** rather than
inheriting this sentence. The reading rule is for the next input, not a
retro-active caveat on these.

**§4.1's conditional never fired**, and that is correct: it binds a metric that
*ranks*, and `hull_coverage` is report-only — deliberately excluded from
`order_rank.rank_key` (`order_rank.py:143`; the string `hull_coverage` does not
occur in that file). A metric that no ranking key reads cannot silently buy a
scale loss.

---

## WHAT IS HONESTLY NOT DONE

| item | state |
|---|---|
| **Full square coverage** | **structurally out of reach** — §"WHY FULL SQUARE COVERAGE IS NOT REACHABLE". Not parked pending effort; ruled out pending a paradigm change |
| **`bird` stays asymmetric** | `cp_symmetric: False`, `cp_mv_broken: 4`. A **settled ruling**, not an open task: conjunct 4 stays strict. `bird` is also the wave's control and is **byte-for-byte identical at #110 and at the merge** |
| **`fish` has no vertex bijection at ANY root** | `cp_mv_broken: null` — Goal 2 cannot score the subject at all. Measured across the full root sweep, not assumed |
| **`humanoid` is the coverage laggard at 0.6638** | moved (0.6319 → 0.6638) but least. No lever measured this wave acts on it; the structural ruling explains why the remaining margin is not a defect |
| **`mv_repair`'s a-priori node bound is ~40× too conservative** | a live, unfixed efficiency defect (PR #105). Decoupled from quadruped, which no longer needs it |

---

## THE OPEN CROSS-GOAL ITEMS

### 1. ✅ RESOLVED (2026-08-16) — `mv_symmetrize.MAX_ORBITS`, and it touched exactly the two cells predicted

> **THE RULING: the ceiling rose, 40 → 45, and quadruped is symmetric.**
> [PR #125](https://github.com/raphaeldchen/origami-design-ide/pull/125)
> shipped **early-exit** (`first_valid=True` above a **two-tier** ceiling —
> new `MAX_RANKED_ORBITS = 40` keeps every narrower fold on the *ranked*
> gate, `MAX_ORBITS = 45` admits quadruped's 2⁴⁵ under first-valid only) and
> measured **1.336 s median over 7 runs against a 10 s bar**, deterministic
> across 9 samples / 2 hash seeds. **`quadruped` `cp_symmetric` False →
> True, `cp_mv_broken` 8 → 0.**
>
> **The premise the section below reasons from was itself wrong, and that is
> the finding, not the raise.** The ceiling was **rationing VALIDATION, not
> search**: the 2⁴⁵ DFS completes in ≤ 2 s; the ~17 s that made 45 look
> unaffordable was *ranking 288 survivors*. So this is not "a gate loosened
> to reach a headline" — the failure mode this section rightly warns about —
> it is a gate that was measuring the wrong quantity. Full derivation:
> [`../goal-2-symmetry/PROGRESS.md`](../goal-2-symmetry/PROGRESS.md),
> §"`quadruped` — ✅ SOLVED at first-valid strength".
>
> **This section's own prediction held exactly, and was re-verified
> independently.** It promised that if the raise shipped, quadruped's
> `cp_symmetric` and `cp_mv_broken` would move and **nothing else** would.
> The 2026-08-16 frozen-baseline re-bless bisected the #119 → #125 segment
> on the real serve path and measured **exactly two moved cells, both
> quadruped's, both the promised ones** — `hull_coverage` 0.8797,
> `design_scale` 0.724628, `lint_class` BENIGN and `stub_flaps` 0 all stood.
> See `mcp_harness/fixtures/scorecard_baseline.jsonl`'s `_meta.attribution`.
>
> ⚠ **The stale `2**64` comments below are STILL STALE and still unowned** —
> `server.py:1186`, `mv_symmetrize.py:140`, and a third the table below does
> not list, at **`mv_symmetrize.py:1106`** (*"Measured on the served
> `quadruped` (2\*\*64): AssertionError"*). ⚠ **The dispatched brief cited
> `:788` for that third one and it is WRONG** — verified by grep at this
> commit: `2**64` occurs at 140 and 1106 only, and line 788 is a
> first-valid docstring about mesh-dog's 2³⁵. The ruling did not correct
> any of the three and this record does not own them. They remain required
> work for whoever owns those files.

**The measurement that framed the decision is kept below unedited**, because
the reasoning it records is what the ruling had to answer.

**Measured on branch `054fd07`, serving the real mesh-extracted `quadruped`
and reading `server._LAST_SERVE["mv_symmetrize"]` directly:**

```
{"orbits": 45, "space": 35184372088832, "refusal": "orbit_space_too_large",
 "exhausted": false, "elapsed_s": 0.0, "audit_clean": 0,
 "layer_consistent": 0, "lint_ok": 0}
```

**45 σ-orbits (2⁴⁵ = 35,184,372,088,832) against `MAX_ORBITS = 40`**
(`mv_symmetrize.py:149`). The relabel is refused before the search starts and
the served fold carries `MV_SYMMETRIZE_SKIP_MARKER` saying in words that this
is a **non-answer, not an exhausted zero**. PR #109's σ-orbit census exhausted
that same space **offline** and found **24** σ-symmetric M/V targets, so a
target is known to exist; this is a refusal to spend the *serve* budget, not a
claim that none exists.

#### ⚠⚠ BEFORE DECIDING: TWO SHIPPED DOCSTRINGS SAY **64**, AND BOTH ARE STALE

This is a live trap for exactly the person who has to make this call, and it
was caught in review of this record rather than by either source noticing:

| source | says | status |
|---|---|---|
| `server.py:1186` — "THE FULL SERVED-FOLD CENSUS … each measured on the fold this branch actually serves" | `quadruped 64 orbits (2**64)` | ⚠ **STALE** |
| `mv_symmetrize.py:140` — "the SERVED `quadruped` at its shipped root carries 64 orbits (2**64, 5 swapped / 49 preserved / 10 fixed)" | 64 | ⚠ **STALE** |
| **direct measurement of the served fold, above** | **45 orbits (2⁴⁵)** | ✅ **authoritative** |

**Both stale readings describe root 5 — the root quadruped served *before* #118
moved it to root 8.** The comments were correct when written and neither was
updated by the merge. **The discrepancy is a factor of ~524,000 in search
space** (2⁶⁴ / 2⁴⁵ = 2¹⁹), and it is decision-flipping: 2⁶⁴ is hopeless on any
budget, 2⁴⁵ is merely five orbits over a ceiling that was itself set to clear a
measured 2³⁵. **Anyone reasoning about `MAX_ORBITS` from the code comments
alone will reject the change for a reason that is no longer true.**

⚠ Those two files are **not owned by this record** and were deliberately not
edited here. **Correcting them is required work for whoever owns
`mv_symmetrize.py` / `server.py`**, independent of how the ceiling decision
goes. Note also that `MAX_ORBITS = 40`'s stated calibration ("40 clears the
largest of those by five orbits") was computed against a measured maximum of
2³⁵ plus the then-hopeless 2⁶⁴ — **45 was not a number in front of anyone when
40 was chosen**, which is the honest framing of the decision, and is different
from "the ceiling was set to exclude quadruped."

> **If it ships, quadruped's `cp_symmetric` and `cp_mv_broken` change. NOTHING
> ELSE.** `hull_coverage` 0.8797, `design_scale` 0.724628, `lint_class` BENIGN
> and `stub_flaps` 0 are **final** and are not downstream of that decision.
> Slot the outcome into the table at the top of this record; no other line in
> this file needs to move.

This record deliberately does **not** guess the outcome. Loosening a gate to
reach a headline is this project's named recurring failure mode, and the
ceiling is doing exactly the job its docstring claims.

⚠ **That last sentence is the one the ruling overturned**, and it is kept
because being wrong in a legible way is the point of the record: the ceiling
was *not* doing the job its docstring claimed. It claimed to bound **search**;
it was bounding **validation**. The refusal to guess was right; the premise
was not.

### 2. ✅ RESOLVED (2026-08-16) — the combined frozen-baseline re-bless

**Discharged.** `scorecard_baseline.jsonl` was frozen at `1c9abe0` from
2026-08-05 and has now been re-blessed **exactly once**, spanning
`1c9abe0..153f9c7`, with a full per-cell attribution table in `_meta`.

**36 attributed cells across 6 owning slices; 31 bisected, 5 structural; zero
unattributed.** The scorecard was re-run through the real serve path at **ten
commits forming a strictly linear ancestry chain**, so consecutive deltas
partition the range and no cell can be orphaned or double-counted; the
attribution was then checked programmatically against those snapshots **in
both directions** — a measured cell with no claim fails as loudly as a claim
that did not move. **Four segments moved zero rows, each verified rather than
asserted** (#96–#100, #108, #110, and #125's post-gate review fixes).

⚠ **Three corrections to this record's own summary above**, all measured:

1. `quadruped` `stub_flaps` 3 → 0 is **#107**, not #118 — re-confirmed by
   bisection. #118's fixture concerns `template-quadruped`, a `cases.py`
   tree, **not** the mesh-extracted `quadruped` the scorecard serves. **Pin
   subjects by tree, never by name.**
2. The `design_scale` column slice (`cfdb60a`, #85) owns only the
   `None → value` step. **Three later slices also moved `design_scale`** —
   #94 (bird 1.095885 → 1.515998, humanoid 0.701537 → 0.775554), #107
   (quadruped 0.599702 → 0.714351) and **#118** (quadruped 0.714351 →
   0.724628). **Four owners touch this column in total.** Where this prose
   and `_meta.attribution` disagree, **believe the table**.
3. humanoid's `cp_mirror_residual` 0.378336 → 0.0 and `cp_mv_broken`
   None → 2 are **#94**, not #107; #107 owns only the subsequent 2 → 0 and
   `cp_symmetric` False → True.

Two cells the dispatched provenance did not list at all are now attributed:
`bird` `cp_mv_broken` None → 4 (**#94** — a bijection existed at last, so the
metric stopped returning its `None` sentinel), and `path_drift_max`
0.0 → ~2e-16 on humanoid and insect (**#107** — ~1 ulp of reassociation from
recomputing each path through a different root; roundoff, not a proportion
change). That last one **supersedes the old `_meta`'s claim that
`path_drift_max` reads "0.0 on all five"**.

---

## THE ONE-PARAGRAPH VERSION, FOR WHOEVER PICKS THIS UP

Coverage moved on 3 of 5 subjects and the mean went 0.7230 → 0.8591. **Both
levers that ever moved it were changes to the problem instance handed to the
packer — node ORDER and node ROOT — never the symmetry axis, never a corner
pin, never a tuning constant.** It stops there for a reason that is checkable in
the vendored source rather than inferred from failed attempts: the creased
region is by construction the convex hull of the leaf nodes
(`tmTree.cpp:2024`), the objective maximises scale and contains no coverage term
(`tmScaleOptimizer.cpp:175-180`), and Lang & Demaine state outright that paper
outside that hull *"is effectively unused"*. **Getting the rest of the square
means adding flaps — spending anatomy — or leaving circle packing behind. Do not
plan a sixth cheap lever.**
