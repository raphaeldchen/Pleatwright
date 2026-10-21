# River routing evidence

Slice: docs/superpowers/specs/2026-10-19-river-routing-design.md (the "beside" layout family).

## Baseline (Task 1)

The controller folded all 51 artifact trees at main `4a64d1ad` from a `git archive` snapshot (so no later commit could leak in) with

```
python -m pleatwright.pipeline --out ~/Desktop/pleatwright_baseline_4a64d1ad \
    --record ~/Desktop/pleatwright_baseline_4a64d1ad/records.jsonl
```

on the 10-core Mac at load average about 3. Result: 51 records, 0 failures, 44 CERTIFIED / 7 OVERSIZE+LOCAL_SAT; layouts 34 symmetric/rule, 11 smaller/rule, 6 smaller/only_option (identical to the slice-1 acceptance). Maximum `pack_secs` 69.4 s (scorpion_1). The 39 multi-hub trees:

| tree | chosen grid C | layout.chosen | pack_secs |
|---|---|---|---|
| ant_0 | 70 | smaller | 3.63 |
| ant_2 | 64 | smaller | 2.07 |
| bat_0 | 36 | symmetric | 0.23 |
| bat_2 | 32 | symmetric | 0.17 |
| bat_3 | 44 | symmetric | 0.37 |
| bird_0 | 50 | symmetric | 0.51 |
| bird_1 | 40 | symmetric | 0.29 |
| bird_2 | 42 | symmetric | 0.55 |
| cat_1 | 46 | symmetric | 0.44 |
| cat_2 | 46 | symmetric | 0.41 |
| cat_3 | 50 | symmetric | 0.5 |
| crab_0 | 66 | symmetric | 1.54 |
| crab_1 | 50 | symmetric | 0.95 |
| crab_3 | 104 | smaller | 4.11 |
| dog_0 | 46 | symmetric | 0.41 |
| dog_1 | 72 | symmetric | 1.36 |
| dog_2 | 50 | smaller | 1.29 |
| dolphin_0 | 32 | smaller | 0.56 |
| dolphin_2 | 30 | smaller | 0.43 |
| elephant_0 | 72 | smaller | 2.14 |
| elephant_1 | 72 | symmetric | 1.1 |
| elephant_3 | 80 | smaller | 2.23 |
| frog_0 | 42 | smaller | 0.84 |
| frog_1 | 40 | symmetric | 0.29 |
| frog_2 | 48 | symmetric | 0.43 |
| guinea_pig_0 | 60 | symmetric | 0.55 |
| guinea_pig_1 | 22 | symmetric | 0.1 |
| guinea_pig_2 | 56 | symmetric | 0.51 |
| horse_1 | 60 | symmetric | 1.46 |
| horse_2 | 54 | symmetric | 0.89 |
| lizard_0 | 38 | symmetric | 0.27 |
| lizard_1 | 38 | smaller | 1.14 |
| lizard_2 | 40 | smaller | 0.77 |
| rabbit_0 | 44 | symmetric | 0.39 |
| rabbit_1 | 54 | symmetric | 0.73 |
| rabbit_3 | 48 | symmetric | 0.44 |
| scorpion_2 | 86 | symmetric | 2.41 |
| spider_1 | 74 | symmetric | 2.25 |
| spider_2 | 136 | smaller | 10.61 |

## Phase 0 (Task 6)

What can the beside family find, with a generous budget? One real `pipeline.pack_options(roll, beside=True)` call per multi-hub tree (today's search first, unchanged, then the two beside searches below `C - 2`), with `BESIDE_WORK_BUDGET = 10_000_000` ticks and `BESIDE_MAX_BUILDS = 400` (provisional production values are 1M / 50; Phase 0 measures what the family CAN find). Today's S/U/verdict and the ticks of each beside search are captured by `phase0_probe.py` wrapping `_pack_options_today` and `_search_beside` inside the worker; no search code is copied. From `mcp_harness/`:

```
PYTHONPATH=. <repo>/mcp_harness/.venv/bin/python ../docs/superpowers/evidence/2026-10-19-river-routing/phase0_probe.py --workers 6 --multi > ../docs/superpowers/evidence/2026-10-19-river-routing/phase0.jsonl
```

Raw output: `phase0.jsonl` (39 lines, 0 errors). 6 workers on a host shared with unrelated `train_online.py` jobs at load about 6-10, so **seconds are noisy; ticks are exact**. Ticks = packer work (`pack.tick`) the beside search spent; 10,000,001 means the budget was exhausted.

Cross-check: today's C from this run equals the baseline chosen grid (Task 1) for all 39 trees; no mismatches.

Columns: today S / U (a grid, `none` = none_below_cap, `-` = no layout), verdict, C; S_b / U_b = beside search outcome (grid, `none`, or **BUDGET**); new verdict, new C, family of the chosen option; ticks of the symmetric and unmirrored beside search; seconds of the whole call. Shrunk trees are marked **bold**.

| tree | S | U | verdict | C | S_b | U_b | new verdict | new C | family | ticks S_b | ticks U_b | secs |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **ant_0** | 102 | 70 | ask | 70 | none | 60 | ask | 60 (was 70) | beside | 133k | 2.16M | 23.35 |
| **ant_2** | 78 | 64 | ask | 64 | none | 62 | ask | 62 (was 64) | beside | 255k | 2.28M | 24.33 |
| bat_0 | 36 | none | symmetric | 36 | none | none | symmetric | 36 | today | 2k | 70k | 0.99 |
| bat_2 | 32 | none | symmetric | 32 | none | none | symmetric | 32 | today | 0k | 0k | 0.19 |
| **bat_3** | 44 | none | symmetric | 44 | none | 40 | ask | 40 (was 44) | beside | 4k | 77k | 1.82 |
| **bird_0** | 50 | none | symmetric | 50 | none | 40 | ask | 40 (was 50) | beside | 104k | 199k | 3.68 |
| bird_1 | 40 | none | symmetric | 40 | none | none | symmetric | 40 | today | 3k | 94k | 1.54 |
| bird_2 | 42 | none | symmetric | 42 | none | none | symmetric | 42 | today | 6k | 133k | 2.53 |
| cat_1 | 46 | none | symmetric | 46 | none | none | symmetric | 46 | today | 4k | 142k | 2.56 |
| cat_2 | 46 | none | symmetric | 46 | none | none | symmetric | 46 | today | 4k | 125k | 2.45 |
| cat_3 | 50 | none | symmetric | 50 | none | none | symmetric | 50 | today | 8k | 205k | 3.53 |
| crab_0 | 66 | none | symmetric | 66 | none | 64 | symmetric | 66 | today | 137k | 5.36M | 37.94 |
| crab_1 | 50 | none | symmetric | 50 | none | none | symmetric | 50 | today | 69k | 2.81M | 17.31 |
| **crab_3** | - | 104 | only_unmirrored | 104 | 86 | **BUDGET** | symmetric | 86 (was 104) | beside | 4.47M | 10.00M | 82.79 |
| dog_0 | 46 | none | symmetric | 46 | none | none | symmetric | 46 | today | 4k | 145k | 2.66 |
| dog_1 | 72 | none | symmetric | 72 | none | 68 | symmetric | 72 | today | 39k | 502k | 12.75 |
| dog_2 | - | 50 | only_unmirrored | 50 | none | none | only_unmirrored | 50 | today | 2k | 98k | 3.32 |
| dolphin_0 | 50 | 32 | ask | 32 | none | none | ask | 32 | today | 0k | 0k | 0.86 |
| dolphin_2 | 42 | 30 | ask | 30 | none | none | ask | 30 | today | 0k | 0k | 0.68 |
| **elephant_0** | 80 | 72 | ask | 72 | 64 | 64 | symmetric | 64 (was 72) | beside | 63k | 525k | 12.03 |
| **elephant_1** | 72 | none | symmetric | 72 | 64 | 64 | symmetric | 64 (was 72) | beside | 65k | 587k | 11.71 |
| **elephant_3** | - | 80 | only_unmirrored | 80 | none | 68 | only_unmirrored | 68 (was 80) | beside | 100k | 688k | 13.04 |
| frog_0 | - | 42 | only_unmirrored | 42 | none | none | only_unmirrored | 42 | today | 0k | 0k | 1.21 |
| frog_1 | 40 | none | symmetric | 40 | none | none | symmetric | 40 | today | 3k | 69k | 1.75 |
| frog_2 | 48 | none | symmetric | 48 | none | 46 | symmetric | 48 | today | 2k | 53k | 1.72 |
| guinea_pig_0 | 60 | none | symmetric | 60 | none | none | symmetric | 60 | today | 1k | 65k | 1.79 |
| guinea_pig_1 | 22 | none | symmetric | 22 | none | none | symmetric | 22 | today | 0k | 6k | 0.19 |
| guinea_pig_2 | 56 | none | symmetric | 56 | none | none | symmetric | 56 | today | 0k | 0k | 0.73 |
| horse_1 | 60 | none | symmetric | 60 | none | none | symmetric | 60 | today | 25k | 459k | 8.81 |
| horse_2 | 54 | none | symmetric | 54 | none | none | symmetric | 54 | today | 9k | 235k | 4.9 |
| lizard_0 | 38 | none | symmetric | 38 | none | none | symmetric | 38 | today | 2k | 80k | 1.46 |
| lizard_1 | 64 | 38 | ask | 38 | none | none | ask | 38 | today | 6k | 79k | 2.62 |
| lizard_2 | 44 | 40 | ask | 40 | none | none | ask | 40 | today | 7k | 129k | 2.79 |
| rabbit_0 | 44 | none | symmetric | 44 | none | none | symmetric | 44 | today | 5k | 159k | 2.61 |
| rabbit_1 | 54 | none | symmetric | 54 | none | none | symmetric | 54 | today | 13k | 275k | 5.19 |
| rabbit_3 | 48 | none | symmetric | 48 | none | none | symmetric | 48 | today | 4k | 163k | 2.8 |
| **scorpion_2** | 86 | none | symmetric | 86 | 82 | 64 | ask | 64 (was 86) | beside | 2.85M | 9.02M | 70.71 |
| **spider_1** | 74 | none | symmetric | 74 | 70 | 64 | symmetric | 70 (was 74) | beside | 773k | 5.06M | 41.28 |
| spider_2 | - | 136 | only_unmirrored | 136 | **BUDGET** | **BUDGET** | only_unmirrored | 136 | today | 10.00M | 10.00M | 99.63 |

### Kill counts

Chosen grid shrank (new C < today C), out of 39. The first row is what the probe ran; the unmirrored-only and symmetric-only rows were computed offline from the recorded S / U / S_b / U_b of each tree (applying the 10% rule to today's options plus the one beside result), not by separate runs:

| arrangement | trees shrunk |
|---|---|
| both beside searches (what `pack_options(beside=True)` does) | **10** |
| unmirrored only (the chosen grid had only U_b been used) | 9 |
| symmetric only (only S_b used) | 5 |

Both: ant_0 70->60, ant_2 64->62, bat_3 44->40, bird_0 50->40, crab_3 104->86, elephant_0 72->64, elephant_1 72->64, elephant_3 80->68, scorpion_2 86->64, spider_1 74->70.
Unmirrored only (crab_3's gain comes from S_b 86, and its U_b hit the budget): ant_0 70->60, ant_2 64->62, bat_3 44->40, bird_0 50->40, elephant_0 72->64, elephant_1 72->64, elephant_3 80->68, scorpion_2 86->64, spider_1 74->64.
Symmetric only: crab_3 104->86, elephant_0 72->64, elephant_1 72->64, scorpion_2 86->82, spider_1 74->70.

Largest wins (chosen grid, both searches): scorpion_2 86->64 (-26%), bird_0 50->40 (-20%), crab_3 104->86 (-17%), elephant_3 80->68, elephant_0/1 72->64, ant_0 70->60, bat_3 44->40 (-9% to -15%), spider_1 74->70 (-5%; its U_b 64 is not chosen, 70 < 1.1 x 64, so 64 is the unmirrored-only figure), ant_2 64->62 (-3%).

### Decision

**Kill threshold (fewer than 5 of 39 shrink): NOT met. 10 of 39 shrink (>= 5), so the slice continues to Task 7. `BESIDE` stays `False` until the production switch task.** Both searches also pass the threshold individually (unmirrored-only 9, symmetric-only 5).

### Budget notes for Task 7 calibration

Trees where a beside search exhausted the 10M budget:
- **spider_2**: BOTH searches hit the budget (S_b and U_b, cap 134); no win found within 10M. Today C 136 (only_unmirrored). Unresolved: more budget might still find one.
- **crab_3**: U_b hit the budget (cap 102); the symmetric search won with 86 at 4.47M ticks. Unmirrored could yet find something smaller (cap 102, S_b already 86).

Ticks of the winning searches (the budget must cover these for the win to be kept):

| tree | winner | grid | ticks |
|---|---|---|---|
| scorpion_2 | U_b | 64 | 9,022,945 |
| spider_1 | U_b | 64 | 5,064,953 |
| crab_3 | S_b | 86 | 4,469,256 |
| scorpion_2 | S_b | 82 | 2,854,785 |
| ant_2 | U_b | 62 | 2,278,563 |
| ant_0 | U_b | 60 | 2,155,646 |
| spider_1 | S_b | 70 | 772,920 |
| elephant_3 | U_b | 68 | 688,492 |
| elephant_1 | U_b | 64 | 587,068 |
| elephant_0 | U_b | 64 | 525,125 |
| bird_0 | U_b | 40 | 198,804 |
| bat_3 | U_b | 40 | 76,681 |
| elephant_1 | S_b | 64 | 64,803 |
| elephant_0 | S_b | 64 | 63,280 |

Large winners: scorpion_2 U_b 9.02M (just under the 10M budget), crab_0 U_b 5.36M (finds 64 but does not shrink C, see below), spider_1 U_b 5.06M (but its kept win, S_b 70, needs only 0.77M), crab_3 S_b 4.47M, scorpion_2 S_b 2.85M, ant_2 U_b 2.28M, ant_0 U_b 2.16M. At the provisional 1M budget the searches costing more than 1M would end as `budget`: ant_0/ant_2 (U_b 2.2-2.3M), crab_3 (S_b 4.5M), scorpion_2 (S_b 2.9M, U_b 9.0M) and spider_1's U_b (5.1M) would be lost, leaving bat_3, bird_0, elephant_0/1/3 and spider_1 (S_b 70) shrinking, i.e. 6 trees (read from the ticks above, not re-run). Task 7 should choose the budget knowing this: about 2.3M adds ant_0/ant_2, about 4.5M adds crab_3, and 9.1M+ is needed for scorpion_2's 64 (82 at 2.9M).
Failed (non-winning) searches are cheap: most `none_below_cap` searches finish in 3k-0.2M ticks; the exceptions are crab_1 (2.81M, none) and crab_0 (5.36M). Trees where the beside family found a grid but C did not shrink: dog_1 U_b 68 (S 72 with a 10% rule: 72 < 1.1*68), frog_2 U_b 46 (48 < 1.1*46), crab_0 U_b 64 (66 < 1.1*64); the 10% rule keeps the symmetric layout.

## Beside budget calibration (Task 7)

`pipeline.BESIDE_WORK_BUDGET` (ticks) and `pipeline.BESIDE_MAX_BUILDS` apply to EACH of the two beside searches. Method as slice 1's (`2026-10-16-layout-choice/README.md`): ticks are deterministic and machine-independent, so the budget is the most expensive WINNING search's ticks plus 3%; seconds only check the 165 s ceiling (spec §5.3).

`budget_probe.py ROLL...` makes one real `pipeline.pack_options(roll, beside=True)` call at the given budget and cap, wrapping (not copying) `_search_beside` and `base.build` to record, per beside search, the outcome, ticks, `base.build` calls and seconds of that search alone. Run single-process, one roll after another. From `mcp_harness/`:

```
PYTHONPATH=. python ../docs/superpowers/evidence/2026-10-19-river-routing/budget_probe.py ant_0 ant_2 bat_3 bird_0 crab_3 elephant_0 elephant_1 elephant_3 spider_1 scorpion_2 > budget_builds.jsonl            # 10M / 400
PYTHONPATH=. python ../docs/superpowers/evidence/2026-10-19-river-routing/budget_probe.py --budget 9.3e6 --max-builds 11 spider_2 scorpion_2 crab_3 crab_0 > budget_calibrated.jsonl
```

Raw output: `budget_builds.jsonl` (the 10 shrinking trees at Phase 0's generous settings), `budget_calibrated.jsonl` (the worst cases at the calibrated constants). The ticks reproduce Phase 0's to the tick (the searches are deterministic).

### Builds

Every winning beside search built **once**: `base.build` succeeded on the first candidate the search yielded (builds = 1 in all 14 winning searches below). The searches that find nothing yield no candidate at all (0 builds), including the budget-exhausted ones. crab_0's unmirrored search (64, below) also built once, so across the 15 measured winning searches the largest builds-to-first-success is 1 and `BESIDE_MAX_BUILDS = 1 + 10 = 11`. The cap covers those 15 winners; it is a guard against a pathological run of failed builds, and nothing beyond the 15 measured searches says how many builds an unmeasured tree's search needs.

### Ticks and seconds of the winning searches (10M / 400, single process)

The host was shared with the owner's unrelated jobs, so seconds swing with load (load averages shown are before / after the call). Whole-call seconds include today's own search.

| roll | search | grid | builds | ticks | search secs | call secs | load |
|---|---|---|---|---|---|---|---|
| scorpion_2 | unmirrored | 64 | 1 | **9,022,945** | 82.6 | 135.2 | 4.6 / 12.5 |
| spider_1 | unmirrored | 64 | 1 | 5,064,953 | 59.5 | 74.6 | 4.4 / 4.6 |
| crab_3 | symmetric | 86 | 1 | 4,469,256 | 42.1 | 167.7 | 4.9 / 3.9 |
| scorpion_2 | symmetric | 82 | 1 | 2,854,785 | 45.8 | (above) | |
| ant_2 | unmirrored | 62 | 1 | 2,278,563 | 47.3 | 58.0 | 4.0 / 4.4 |
| ant_0 | unmirrored | 60 | 1 | 2,155,646 | 39.2 | 56.1 | 4.4 / 4.0 |
| spider_1 | symmetric | 70 | 1 | 772,920 | 11.7 | (above) | |
| elephant_3 | unmirrored | 68 | 1 | 688,492 | 18.2 | 25.5 | 4.3 / 4.4 |
| elephant_1 | unmirrored | 64 | 1 | 587,068 | 14.1 | 22.1 | 4.4 / 4.3 |
| elephant_0 | unmirrored | 64 | 1 | 525,125 | 16.9 | 28.6 | 3.9 / 4.4 |
| bird_0 | unmirrored | 40 | 1 | 198,804 | 5.9 | 8.9 | 5.3 / 4.9 |
| bat_3 | unmirrored | 40 | 1 | 76,681 | 4.5 | 5.8 | 4.4 / 5.3 |
| elephant_1 | symmetric | 64 | 1 | 64,803 | 4.0 | (above) | |
| elephant_0 | symmetric | 64 | 1 | 63,280 | 4.5 | (above) | |

Ticks per second is not constant across searches (about 55k/s for ant_0's unmirrored search, 109k/s for scorpion_2's, 250k/s for crab_3's budget-exhausted one on a quiet host): the slice-1 caches (Task 3) made the pocket loop cheap, and what remains is dominated by other costs. The ceiling is therefore checked in seconds on the worst case, not by a single ticks/s figure.

### The worst case at the calibrated constants

`BESIDE_WORK_BUDGET = 9,300,000` (9,022,945 plus 3% is 9,293,633, rounded up) and `BESIDE_MAX_BUILDS = 11`. A tree's worst case is today's search plus two budget-exhausting beside searches: spider_2 (the only tree where both exhaust; no win found at 10M either). Single process, one call at a time:

| roll | S_b / U_b outcome | S_b ticks / secs | U_b ticks / secs | today's search secs | whole call secs | load before / after |
|---|---|---|---|---|---|---|
| spider_2 | budget / budget | 9,300,001 / 27.1 | 9,300,001 / 62.2 | 20.6 | **110.2** | 10.9 / 7.9 |
| scorpion_2 | 82 / 64 | 2,854,785 / 23.5 | 9,022,945 / 42.2 | 4.8 | 70.5 | 7.9 / 15.0 |
| crab_3 | 86 / budget | 4,469,256 / 13.6 | 9,300,001 / 37.3 | 4.0 | 55.0 | 13.5 / 7.5 |
| crab_0 | none / 64 | 136,987 / 1.6 | 5,363,005 / 23.2 | 1.6 | 26.3 | 7.5 / 5.9 |

The slowest whole call, spider_2's, is 110 s, inside the 165 s ceiling (the earlier run of crab_3 at 10M took 167.7 s, its budget-exhausted unmirrored search 111.5 s of it, at load 4.9 before the call; at the calibrated constants the same call took 55.0 s, that search 37.3 s, at load 13.5. Seconds therefore vary with load in both directions on this shared host and do not track the load average; ticks are what the budget counts). Phase 0's seconds (spider_2 99.6 s, scorpion_2 70.7 s) were measured with 6 parallel workers and agree. **No budget reduction was needed; no Phase 0 win is lost**: all 10 shrinking trees still shrink to their Phase 0 grids (ant_0 60, ant_2 62, bat_3 40, bird_0 40, crab_3 86, elephant_0 64, elephant_1 64, elephant_3 68, scorpion_2 64, spider_1 70). At the calibrated budget crab_3's and spider_2's budget-exhausted searches stay unresolved, as in Phase 0.

### Tests

`test_scorpion_2_fits_the_beside_budget` asserts the anchor still gives S_b 82 / U_b 64 and a chosen grid of 64 (today 86) with `beside=True` (it fails, with both searches `budget`, at the provisional 1M); `test_beside_ticks_are_deterministic` asserts two `pack_options("scorpion_2", beside=True)` summaries are identical. Together they add about 100 s to `tests/test_river_routing.py` (116 s -> 216 s, 47 -> 49 tests); any code change that shifts the beside searches' tick counts past the budget fails the first.


## Corpus acceptance (spec §8), 2026-10-20

The controller folded the 51 artifact trees from HEAD `22e32eb3` (beside layouts on by default) in one process, from `mcp_harness/`:

```
python -m pleatwright.pipeline --out ~/Desktop/pleatwright_river_routing \
    --record ~/Desktop/pleatwright_river_routing/records.jsonl
```

at host load about 1.8 at the start. The records' `total_secs` sum to 2,985 s (the baseline's: 1,436 s); `pack_secs` sum to 1,227 s (baseline 365 s). Items 2-4 and the time half of item 6 are read from the two runs' folders and records by `acceptance_check.py` (raw output: `acceptance.json`); nothing was re-folded.

**1. Every tree folds.** 51 records, none with `failure`. Verdicts: 44 `CERTIFIED`, 7 `OVERSIZE+LOCAL_SAT` (crab_3, octopus_2, scorpion_0, scorpion_1, scorpion_2, spider_1, spider_2), the same seven as the baseline. Layout decisions (`chosen` / `reason` / `family`):

| layout | trees | baseline |
|---|---|---|
| `symmetric` / `rule` / today | 29 | 34 (all today) |
| `symmetric` / `rule` / beside | 4: crab_3, elephant_0, elephant_1, spider_1 | |
| `smaller` / `rule` / today | 8 | 11 (all today) |
| `smaller` / `rule` / beside | 5: ant_0, ant_2, bat_3, bird_0, scorpion_2 | |
| `smaller` / `only_option` / today | 4: dog_2, frog_0, spider_2, starfish_0 | 6 (all today) |
| `smaller` / `only_option` / beside | 1: elephant_3 | |

Beside outcomes over the 102 searches (two per tree): 17 found a grid, 58 `none_below_cap`, 24 `no_child_hub` (the 12 single-hub trees), 3 `budget` (crab_3's unmirrored search, both of spider_2's), **0 `builds`**: no search reached the build cap of 11, which is calibrated on the 15 measured winners only.

**2. Byte identity.** Every new-run folder whose name (`<Subject>_<grid>`) also exists in the baseline `~/Desktop/pleatwright_baseline_4a64d1ad/` was compared file by file (`filecmp.cmp(..., shallow=False)`, the four files):

```
41 folders, 164 identical, 0 different
```

The other 10 trees have no counterpart (their grid changed) and every one has `layout.family == "beside"`: ant_0, ant_2, bat_3, bird_0, crab_3, elephant_0, elephant_1, elephant_3, scorpion_2, spider_1. These are exactly Phase 0's 10 shrinking trees, on Phase 0's grids.

**3. The 10 changed trees.** `solving` and `shaping` are flat-foldable vertices over total vertices; every tree is all-flat-foldable. Each is `CERTIFIED`, or `OVERSIZE+LOCAL_SAT` where the baseline already was (crab_3, scorpion_2, spider_1).

| roll | grid before -> after | chosen (S_b / U_b) | verdict before | verdict after | solving | shaping | `pack_secs` before -> after |
|---|---|---|---|---|---|---|---|
| ant_0 | 70 -> 60 | smaller (none / 60) | CERTIFIED | CERTIFIED | 345/345 | 1627/1627 | 3.6 -> 29.8 |
| ant_2 | 64 -> 62 | smaller (none / 62) | CERTIFIED | CERTIFIED | 432/432 | 1984/1984 | 2.1 -> 31.6 |
| bat_3 | 44 -> 40 | smaller (none / 40) | CERTIFIED | CERTIFIED | 198/198 | 782/782 | 0.4 -> 2.5 |
| bird_0 | 50 -> 40 | smaller (none / 40) | CERTIFIED | CERTIFIED | 205/205 | 642/642 | 0.5 -> 5.8 |
| crab_3 | 104 -> 86 | symmetric (86 / budget) | OVERSIZE+LOCAL_SAT | OVERSIZE+LOCAL_SAT | 1080/1080 | 2914/2914 | 4.1 -> 101.8 |
| elephant_0 | 72 -> 64 | symmetric (64 / 64) | CERTIFIED | CERTIFIED | 399/399 | 1671/1671 | 2.1 -> 15.2 |
| elephant_1 | 72 -> 64 | symmetric (64 / 64) | CERTIFIED | CERTIFIED | 427/427 | 1876/1876 | 1.1 -> 14.8 |
| elephant_3 | 80 -> 68 | smaller, only option (none / 68) | CERTIFIED | CERTIFIED | 378/378 | 1641/1641 | 2.2 -> 16.6 |
| scorpion_2 | 86 -> 64 | smaller (82 / 64) | OVERSIZE+LOCAL_SAT | OVERSIZE+LOCAL_SAT | 555/555 | 2057/2057 | 2.4 -> 95.9 |
| spider_1 | 74 -> 70 | symmetric (70 / 64) | OVERSIZE+LOCAL_SAT | OVERSIZE+LOCAL_SAT | 570/570 | 1784/1784 | 2.3 -> 53.9 |

*Looked at.* Each changed tree's `overview.png` was opened, new and baseline side by side:

* ant_0 (60, was 70): six jointed legs splayed from the thorax, head and gaster on the axis; reads as an ant. Not worse than the baseline.
* ant_2 (62, was 64): six legs hanging from the thorax, head forward; reads as an ant. Not worse.
* bat_3 (40, was 44): two jointed wings out to the sides, head up, two legs and a tail down; reads as the stick-figure bat. Not worse. Its packing CP is now unmirrored (the child pocket sits at the lower left) while the folded views stay symmetric.
* bird_0 (40, was 50): head on a neck, two wings, two legs and a long tail; reads as a stick-figure bird. Not worse.
* crab_3 (86, was 104): two claws forward and four parallel leg pairs; reads as a crab. Not worse. Its packing CP is now mirror-symmetric (a beside S_b) where the baseline's was the one-sided unmirrored strip stack.
* elephant_0 (64, was 72): four column legs under an arched back, trunk down at the front; reads as the quadruped. Not worse.
* elephant_1 (64, was 72): four legs, two ears up, trunk down; reads as an elephant-like quadruped. Not worse.
* elephant_3 (68, was 80): four legs, ears and a curled trunk; reads as an elephant-like quadruped. Not worse.
* scorpion_2 (64, was 86): two claws forward, four leg pairs, tail raised over the back; reads as a scorpion. Not worse.
* spider_1 (70, was 74): eight long jointed legs around a body with an abdomen behind; reads as a spider. Not worse.

At the overview's resolution each folded view is indistinguishable from its baseline: the shaping places the same flaps the same way, and what visibly changes is the three CP panels (fewer, coarser pleats on the smaller grid). None reads worse.

**4. Grid report.** The 39 multi-hub trees, baseline (C before) against this run (C after). `N/bound` is `efficiency.n_over_bound`, `slack` `slack_fraction`; a single value means unchanged. The baseline records predate `river_corners`, so the before value is recomputed on today's chosen layout by `river_corners_before.py` (`pack_options(roll, beside=False)`, auto rule; its grids equal the baseline's for all 39): it is 0 for every tree. Changed trees are **bold**.

| tree | C before | C after | family | S_b / U_b | N/bound | slack | mean layers | river_corners |
|---|---|---|---|---|---|---|---|---|
| **ant_0** | 70 | 60 | beside | none_below_cap / 60 | 1.2963 -> 1.1111 | 0.4184 -> 0.3667 | 44.4231 -> 32.3077 | 0 -> 4 |
| **ant_2** | 64 | 62 | beside | none_below_cap / 62 | 1.2075 -> 1.1698 | 0.386 -> 0.3624 | 37.76 -> 35.1 | 0 -> 2 |
| bat_0 | 36 | 36 | today | none_below_cap / none_below_cap | 1.1613 | 0.2917 | 18.9818 | 0 |
| bat_2 | 32 | 32 | today | none_below_cap / none_below_cap | 1.1852 | 0.1445 | 17.3913 | 0 |
| **bat_3** | 44 | 40 | beside | none_below_cap / 40 | 1.4194 -> 1.2903 | 0.3905 -> 0.3356 | 29.8868 -> 24.4528 | 0 -> 2 |
| **bird_0** | 50 | 40 | beside | none_below_cap / 40 | 1.5625 -> 1.25 | 0.5136 -> 0.2869 | 37.963 -> 23.1852 | 0 -> 2 |
| bird_1 | 40 | 40 | today | none_below_cap / none_below_cap | 1.25 | 0.2887 | 23.2727 | 0 |
| bird_2 | 42 | 42 | today | none_below_cap / none_below_cap | 1.2727 | 0.3912 | 25.6271 | 0 |
| cat_1 | 46 | 46 | today | none_below_cap / none_below_cap | 1.15 | 0.327 | 24.5753 | 0 |
| cat_2 | 46 | 46 | today | none_below_cap / none_below_cap | 1.15 | 0.2807 | 23.9718 | 0 |
| cat_3 | 50 | 50 | today | none_below_cap / none_below_cap | 1.3158 | 0.4256 | 31.0606 | 0 |
| crab_0 | 66 | 66 | today | none_below_cap / 64 | 1.1579 | 0.3416 | 36.1132 | 0 |
| crab_1 | 50 | 50 | today | none_below_cap / none_below_cap | 1.1628 | 0.3368 | 28.0488 | 0 |
| **crab_3** | 104 | 86 | beside | 86 / budget | 1.6 -> 1.3231 | 0.7001 -> 0.4013 | 82.5124 -> 53.0579 | 0 -> 12 |
| dog_0 | 46 | 46 | today | none_below_cap / none_below_cap | 1.2105 | 0.3129 | 26.0896 | 0 |
| dog_1 | 72 | 72 | today | none_below_cap / 68 | 1.4694 | 0.5042 | 52.8511 | 0 |
| dog_2 | 50 | 50 | today | none_below_cap / none_below_cap | 1.0417 | 0.2096 | 23.2143 | 0 |
| dolphin_0 | 32 | 32 | today | none_below_cap / none_below_cap | 1.1034 | 0.1641 | 16.6154 | 0 |
| dolphin_2 | 30 | 30 | today | none_below_cap / none_below_cap | 1.3043 | 0.2833 | 18.75 | 0 |
| **elephant_0** | 72 | 64 | beside | 64 / 64 | 1.4118 -> 1.2549 | 0.4579 -> 0.3711 | 48.8 -> 36.2889 | 0 -> 4 |
| **elephant_1** | 72 | 64 | beside | 64 / 64 | 1.3333 -> 1.1852 | 0.4167 -> 0.3184 | 45.0 -> 33.0 | 0 -> 4 |
| **elephant_3** | 80 | 68 | beside | none_below_cap / 68 | 1.3333 -> 1.1333 | 0.3623 -> 0.3369 | 49.7087 -> 35.1456 | 0 -> 2 |
| frog_0 | 42 | 42 | today | none_below_cap / none_below_cap | 1.0769 | 0.1259 | 19.7273 | 0 |
| frog_1 | 40 | 40 | today | none_below_cap / none_below_cap | 1.25 | 0.2475 | 23.7288 | 0 |
| frog_2 | 48 | 48 | today | none_below_cap / 46 | 1.1707 | 0.1259 | 26.0 | 0 |
| guinea_pig_0 | 60 | 60 | today | none_below_cap / none_below_cap | 1.1111 | 0.22 | 29.3617 | 0 |
| guinea_pig_1 | 22 | 22 | today | none_below_cap / none_below_cap | 1.2941 | 0.2397 | 11.8462 | 0 |
| guinea_pig_2 | 56 | 56 | today | none_below_cap / none_below_cap | 1.6 | 0.1913 | 34.2222 | 0 |
| horse_1 | 60 | 60 | today | none_below_cap / none_below_cap | 1.4634 | 0.5283 | 42.8571 | 0 |
| horse_2 | 54 | 54 | today | none_below_cap / none_below_cap | 1.2273 | 0.3333 | 32.0 | 0 |
| lizard_0 | 38 | 38 | today | none_below_cap / none_below_cap | 1.1875 | 0.313 | 20.4074 | 0 |
| lizard_1 | 38 | 38 | today | none_below_cap / none_below_cap | 1.1515 | 0.2964 | 20.0 | 0 |
| lizard_2 | 40 | 40 | today | none_below_cap / none_below_cap | 1.3333 | 0.4263 | 25.7143 | 0 |
| rabbit_0 | 44 | 44 | today | none_below_cap / none_below_cap | 1.2571 | 0.4215 | 25.8413 | 0 |
| rabbit_1 | 54 | 54 | today | none_below_cap / none_below_cap | 1.35 | 0.4252 | 35.5263 | 0 |
| rabbit_3 | 48 | 48 | today | none_below_cap / none_below_cap | 1.1429 | 0.3247 | 25.5584 | 0 |
| **scorpion_2** | 86 | 64 | beside | 82 / 64 | 1.4828 -> 1.1034 | 0.6752 -> 0.3838 | 62.6916 -> 33.1589 | 0 -> 4 |
| **spider_1** | 74 | 70 | beside | 70 / 64 | 1.451 -> 1.3725 | 0.6158 -> 0.5494 | 52.4167 -> 45.8333 | 0 -> 4 |
| spider_2 | 136 | 136 | today | budget / budget | 1.4945 | 0.6138 | 100.2105 | 0 |
| **median (39)** | 50 | 48 | | | 1.2571 -> 1.2105 | 0.3368 -> 0.327 | 28.0488 -> 26.0 | 0 -> 0 |

Over the 10 changed trees alone the medians move: C 72 -> 64, N/bound 1.416 -> 1.218, slack 0.438 -> 0.365, mean layers 46.9 -> 34.1, river_corners 0 -> 4. Three trees find a beside layout that the 10% rule does not choose: crab_0 (U_b 64, S 66), dog_1 (U_b 68, S 72), frog_2 (U_b 46, S 48), as in Phase 0.

**5. Branching edits (report only).** `edits_probe.py` makes two real calls per edit, `pipeline.pack_options(tree, beside=False)` and `pipeline.pack_options(tree, beside=True)` (production budget 9.3M ticks / 11 builds), and records each call's verdict, S / U and the grid the auto rule chooses (C). The edits are the 2026-10-10 probe's enumeration (`2026-10-10-branching-packer/probe_branching.py`): `antlered` on the 35 rolls with a `head`, `toed` on the 39 rolls where it branches, and `lopsided` on the same 35 rolls. From `mcp_harness/`:

```
PYTHONPATH=.:tests <repo>/mcp_harness/.venv/bin/python \
    ../docs/superpowers/evidence/2026-10-19-river-routing/edits_probe.py --workers 6 \
    > ../docs/superpowers/evidence/2026-10-19-river-routing/edits.jsonl
```

Raw output: `edits.jsonl` (109 lines, 0 errors), 13 min 53 s wall with 6 spawn workers (`edits.stderr.txt`).

| edit | edits | C shrinks | newly packs | unchanged | grows | median C off -> on (both pack) | sum C off -> on |
|---|---|---|---|---|---|---|---|
| antlered | 35 | 29 | 0 | 6 | 0 | 64 -> 58 | 2284 -> 2006 |
| toed | 39 | 18 | 2 (crab_3, elephant_3) | 19 (spider_2 packs in neither) | 0 | 58 -> 54 | 2162 -> 1970 |
| lopsided | 35 | 33 | 0 | 2 | 0 | 76 -> 58 | 2658 -> 2068 |

No edit's chosen grid grows, and no beside search ended with `builds`; 9 edits had one beside search end with `budget` and toed spider_2 had both.

**The three edits over the grid cap.** toed crab_3 now packs: S_b 90 (U_b `budget`), chosen symmetric 90, where `beside=False` gives verdict `none`. toed elephant_3 now packs: U_b 76, chosen smaller (only option) 76. toed spider_2 still packs nothing (`none`; both beside searches `budget`), so `test_a_branching_tree_past_the_grid_cap_fails_at_packing` (`tests/test_nest.py`), already moved to toed spider_2 in Task 8, still pins the right edit.

Per edit, C with `beside=False` -> `beside=True` (`none` = no layout; changed in bold):

*antlered* (35): **ant_0 90 -> 70**, **ant_1 74 -> 60**, **ant_2 88 -> 70**, bat_0 52, **bat_3 56 -> 46**, **bird_0 74 -> 44**, **bird_1 54 -> 48**, **bird_2 50 -> 44**, **cat_1 62 -> 56**, **cat_2 60 -> 56**, cat_3 62, **dog_0 62 -> 58**, **dog_1 78 -> 70**, **dog_2 68 -> 62**, **dolphin_0 54 -> 48**, **dolphin_1 52 -> 42**, **dolphin_2 46 -> 40**, **elephant_0 90 -> 66**, **elephant_1 80 -> 68**, elephant_3 90, **frog_0 64 -> 52**, **frog_1 54 -> 48**, **frog_2 70 -> 60**, **guinea_pig_0 88 -> 80**, **guinea_pig_1 34 -> 30**, **guinea_pig_2 70 -> 60**, **horse_0 74 -> 66**, horse_1 70, horse_2 68, **lizard_0 54 -> 48**, **lizard_1 54 -> 50**, **lizard_2 50 -> 42**, **rabbit_0 60 -> 54**, rabbit_1 66, **rabbit_3 66 -> 60**.

*toed* (39): **ant_0 70 -> 64**, **ant_2 80 -> 70**, bat_0 44, bat_2 38, **bat_3 48 -> 40**, **bird_0 72 -> 48**, **bird_1 54 -> 46**, bird_2 50, cat_1 54, cat_2 54, cat_3 58, **crab_0 78 -> 66**, **crab_1 56 -> 54**, **crab_3 none -> 90**, dog_0 54, **dog_1 74 -> 68**, dog_2 60, **dolphin_0 48 -> 38**, **dolphin_2 44 -> 32**, elephant_0 74, **elephant_1 88 -> 72**, **elephant_3 none -> 76**, frog_0 48, frog_1 54, **frog_2 62 -> 50**, **guinea_pig_0 80 -> 64**, **guinea_pig_1 34 -> 30**, guinea_pig_2 58, horse_1 62, horse_2 62, lizard_0 48, **lizard_1 70 -> 56**, **lizard_2 50 -> 42**, rabbit_0 52, rabbit_1 62, rabbit_3 58, **scorpion_2 90 -> 70**, **spider_1 74 -> 70**, spider_2 none.

*lopsided* (35): ant_0 102, **ant_1 76 -> 56**, **ant_2 100 -> 72**, **bat_0 62 -> 50**, **bat_3 68 -> 48**, **bird_0 84 -> 44**, **bird_1 66 -> 48**, **bird_2 62 -> 44**, **cat_1 74 -> 58**, **cat_2 72 -> 56**, **cat_3 74 -> 62**, **dog_0 72 -> 58**, **dog_1 90 -> 70**, **dog_2 80 -> 62**, **dolphin_0 64 -> 48**, **dolphin_1 54 -> 42**, **dolphin_2 56 -> 40**, **elephant_0 102 -> 70**, **elephant_1 92 -> 74**, elephant_3 102, **frog_0 76 -> 54**, **frog_1 66 -> 48**, **frog_2 80 -> 60**, **guinea_pig_0 98 -> 76**, **guinea_pig_1 46 -> 36**, **guinea_pig_2 82 -> 62**, **horse_0 86 -> 66**, **horse_1 80 -> 72**, **horse_2 78 -> 66**, **lizard_0 64 -> 48**, **lizard_1 64 -> 50**, **lizard_2 60 -> 42**, **rabbit_0 70 -> 56**, **rabbit_1 78 -> 66**, **rabbit_3 78 -> 60**.

Seconds (6 workers sharing the host with the determinism runs below, so not comparable with the corpus's): the slowest `beside=True` calls are toed spider_2 259 s (both searches `budget`), lopsided ant_1 213 s and antlered ant_1 204 s (U_b `budget`), toed crab_3 186 s (U_b `budget`). These edits are outside §8.6, which bounds the 51 trees; they show that a tree whose beside search exhausts the budget costs about two to three times today's search on a busy host.

**6. Time and determinism.** *Time*: the largest `pack_secs` in the corpus run is spider_2's 133.8 s (both beside searches `budget`), then scorpion_1 132.4 s (single-hub, today's search only), octopus_2 121.9 s, spider_0 113.0 s, scorpion_0 107.6 s, crab_3 101.8 s: all under the about 165 s ceiling.

*Determinism*: `pack_options(roll).summary()` (production default, beside on) for all 51 rolls in two separate, concurrently running single-threaded processes (`determinism_probe.py OUT.json`, from `mcp_harness/` with `PYTHONPATH=.`), the two JSON dumps compared: `51 51 True []`, and the files are byte-identical. One dump is kept as `determinism_summary.json`. The summaries also match the corpus run's `layout` fields (`n_symmetric`, `n_smaller`, `beside`) for every tree. Seconds in those two processes, which overlapped the edits probe and then `make test` (load averages read during the run ranged from about 7 to a 5-minute average of 76 at one reading): scorpion_1 162 s, crab_3 154 s, spider_2 138 s per call in both. That is inside 165 s but close to it on a loaded host; ticks, not seconds, are what the budgets count.

**7. Suites.** `make PYTHON=<repo>/mcp_harness/.venv/bin/python test` from the worktree root: 687 passed, 2 skipped (pipeline, 1,142 s) and 105 passed (app server, 133 s); 21 min 17 s wall, run concurrently with the two determinism processes, so slower than on an idle host. `cd app/web && npm test`: 10 files, 95 passed; `npm run build` succeeds (only the usual chunk-size warning). The worktree has no `node_modules`; it was symlinked from the main checkout (identical `package.json` and `package-lock.json`) for the run and removed afterwards. CI's `web` job is unaffected: no file under `app/` differs between the baseline commit `4a64d1ad` and HEAD.

**8. Trees.** Every probe here uses only the 51 artifact trees and the named edits `antlered`, `toed`, `lopsided` of them; no tardigrade / water bear.
