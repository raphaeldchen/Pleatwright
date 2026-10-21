# Evidence for the packing layout choice (2026-10-16)

Spec: `docs/superpowers/specs/2026-10-16-packing-layout-choice-design.md`.
Research probes and their results, all over the 51 artifact trees:

| file | what it is |
|---|---|
| `bp_efficiency_probe.py` -> `bp_eff.jsonl` | packing-only efficiency metrics of the symmetric layout of every tree; `summ.py` summarises it |
| `rung_probe.py` -> `rung_asym.jsonl` | first N per packing-ladder rung (here the unmirrored rung), each rung run on its own |
| `asym_certify_probe.py` -> `asym_cert.jsonl` | the full pipeline with the symmetric rungs disabled, so the unmirrored layout wins; checks it still solves and certifies |
| `layout-choice-mockup.html` | mockup of the layout card |
| `budget_probe.py` | the budget calibration below |

## Unmirrored-search work budget (`pipeline.SMALLER_WORK_BUDGET`)

Once the symmetric layout (grid `N_sym`) is found, the unmirrored search runs
with the grid capped at `N_sym*10//11` and a deterministic budget counted in
packer ticks (`pack.tick`), not seconds.

`budget_probe.py ROLL BUDGET` runs exactly the unmirrored search that
`pipeline.pack_options` runs (capped `N_max`, `symmetric=False`, building bases
until one has no errors) and prints ticks used and seconds of that search alone.
From `mcp_harness/`:

```
PYTHONPATH=. python ../docs/superpowers/evidence/2026-10-16-layout-choice/budget_probe.py octopus_2 1e12
PYTHONPATH=. python ../docs/superpowers/evidence/2026-10-16-layout-choice/budget_probe.py scorpion_0 1e6   # and 1e7, 5.1e6, 3.5e6
```

Measured on this host (10-core Mac, load average about 5 to 6 throughout, so
seconds are indicative; ticks are exact and machine-independent):

| roll | N_sym / cap | budget | outcome | ticks | seconds | ticks/s |
|---|---|---|---|---|---|---|
| octopus_2 | 66 / 60 | 10^12 | found, N = 60 | **3,395,895** | 164.98 | 20,583 |
| scorpion_0 | 78 / 70 | 10^6 | `BudgetExhausted` | 1,000,001 | 46.09 | 21,699 |
| scorpion_0 | 78 / 70 | 3.5x10^6 | `BudgetExhausted` | 3,500,001 | **157.78** | 22,183 |
| scorpion_0 | 78 / 70 | 5.1x10^6 | `BudgetExhausted` | 5,100,001 | 235.63 | 21,644 |
| scorpion_0 | 78 / 70 | 10^7 | `BudgetExhausted` | 10,000,001 | 473.52 | 21,119 |

(10^8 was not run: at 21k ticks/s it would take about 80 minutes, and the rate
is already fixed by the rows above.)

Ticks track wall time well: octopus_2 and scorpion_0 both run at about 21k
ticks/s. A profile of scorpion_0 at 10^6 ticks puts nearly all the time in
`pack._pocket_solutions` (the assignment loop about 39 s of 68 s under the
profiler, the 232k `rowfn` calls about 16 s) and none in `base.build`, so no
extra ticks were added to `pack.py`.

### Decision

The brief's rule was 1.5 x octopus_2's ticks, rounded up to 5.1x10^6, which
costs scorpion_0 235.6 s and breaks the 180 s stop condition. Octopus_2's
search alone is about 165 s, so the spec's original "about 120 s" target was
not reachable with octopus_2 inside it. The ruling: ticks are deterministic, so
octopus_2's 3,395,895 ticks are the same on every machine and it always fits;
the 1.5x margin was a seconds-era safety factor and buys nothing.

`SMALLER_WORK_BUDGET = 3_500_000` (octopus_2's ticks plus 3%). Worst case is
scorpion_0 at about 158 s on this host under load (about 165 s from the
rate). `test_octopus_2_fits_the_budget` asserts octopus_2 still asks with
smaller N = 60, which is what catches any future code change that shifts tick
counts.

## Corpus acceptance (spec §9), 2026-10-16

All numbers below come from one run of `python -m pleatwright.pipeline --out OUT
--record OUT/records.jsonl` (default `--layout auto`) over the 51 artifact
trees, started from a clean output directory at the head of this branch (before
the commit that adds this section), on the same shared 10-core Mac as the
budget calibration above (load average about 3 to 4). The whole corpus took
2,613 s (43.5 min wall; the records' `total_secs` sum to 2,611 s).

**1. Every tree folds.** 51 records, none with `failure`. Verdicts: 44
`CERTIFIED`, 7 `OVERSIZE+LOCAL_SAT` (crab_3, octopus_2, scorpion_0, scorpion_1,
scorpion_2, spider_1, spider_2). All seven were already `OVERSIZE+LOCAL_SAT` in
the 2026-10-06 records; five more trees that were then (ant_0, ant_2,
elephant_0, octopus_3, spider_0) are `CERTIFIED` now, see item 3. Layout
decisions:

| `layout.chosen` / `reason` | trees |
|---|---|
| `smaller` / `rule` (gain >= 1.10) | 11 |
| `smaller` / `only_option` (no symmetric layout exists, as before) | 6: crab_3, dog_2, elephant_3, frog_0, spider_2, starfish_0 |
| `symmetric` / `rule`, no unmirrored layout below the cap (`none_below_cap`) | 32 |
| `symmetric` / `rule`, unmirrored search stopped by the budget (`budget`) | 2: scorpion_0, scorpion_1 |

**2. Byte-identity gate.** Every output folder whose layout is not
`smaller`/`rule` (40 folders: the 32 + 2 + 6 above) was compared file by file
(`filecmp`, byte comparison) with `~/Desktop/origami_samples_artifact_trees`
(read only):

```
40 folders, 160 identical, 0 different []
```

The 11 switched trees have a different grid in the folder name, so they have no
counterpart there.

**3. The 11 switched trees.** The ten expected (ant_0, ant_2, dolphin_0..2,
elephant_0, lizard_1, lizard_2, octopus_2, octopus_3) plus spider_0, which the
budgeted search now finds (102 -> 70). `solving` and `shaping` are flat-foldable
vertices over total vertices; every tree is all-flat-foldable.

| roll | grid symmetric | grid smaller | gain | verdict symmetric (10-06) | verdict smaller | solving | shaping | `pack_secs` (10-06 value) |
|---|---|---|---|---|---|---|---|---|
| ant_0 | 102 | 70 | 1.457 | OVERSIZE+LOCAL_SAT | CERTIFIED | 547/547 | 2169/2169 | 7 (3.1) |
| ant_2 | 78 | 64 | 1.219 | OVERSIZE+LOCAL_SAT | CERTIFIED | 416/416 | 2038/2038 | 5 (1.7) |
| dolphin_0 | 50 | 32 | 1.562 | CERTIFIED | CERTIFIED | 129/129 | 397/397 | 1 (0.7) |
| dolphin_1 | 46 | 30 | 1.533 | CERTIFIED | CERTIFIED | 129/129 | 467/467 | 1 (0.6) |
| dolphin_2 | 42 | 30 | 1.400 | CERTIFIED | CERTIFIED | 143/143 | 467/467 | 1 (0.5) |
| elephant_0 | 80 | 72 | 1.111 | OVERSIZE+LOCAL_SAT | CERTIFIED | 468/468 | 1714/1714 | 4 (2.3) |
| lizard_1 | 64 | 38 | 1.684 | CERTIFIED | CERTIFIED | 177/177 | 512/512 | 2 (2.0) |
| lizard_2 | 44 | 40 | 1.100 | CERTIFIED | CERTIFIED | 226/226 | 954/954 | 1 (0.8) |
| octopus_2 | 66 | 60 | 1.100 | OVERSIZE+LOCAL_SAT | OVERSIZE+LOCAL_SAT | 459/459 | 1374/1374 | 124 (2.5) |
| octopus_3 | 84 | 56 | 1.500 | OVERSIZE+LOCAL_SAT | CERTIFIED | 374/374 | 1253/1253 | 56 (4.1) |
| spider_0 | 102 | 70 | 1.457 | OVERSIZE+LOCAL_SAT | CERTIFIED | 362/362 | 2252/2252 | 140 (5.8) |

octopus_2 stays `OVERSIZE+LOCAL_SAT`, as its symmetric layout was (permitted by
§9.3). Five trees (ant_0, ant_2, elephant_0, octopus_3, spider_0) go from
`OVERSIZE+LOCAL_SAT` to `CERTIFIED` on the smaller grid. lizard_2 (44/40) and
octopus_2 (66/60) sit exactly on gain 1.10 and switch, so the rule is
`>=`, as specified.

*Looked at.* Each switched tree's `overview.png` was opened and read:

* ant_0 (70): body with a long gaster and six splayed legs; reads as an ant.
* ant_2 (64): six legs and head hang from the thorax; reads as an ant, legs
  thinner than ant_0.
* dolphin_0 (32): dorsal fin, tail and two pectorals off one trunk; the
  silhouette reads as a dolphin-like stick figure (fins thin, as before).
* dolphin_1 (30): same, with a longer tail; reads as the stick-figure dolphin.
* dolphin_2 (30): upright dorsal fin, long tail, pectoral pair; reads as the
  stick-figure dolphin.
* elephant_0 (72): four columns for legs under an arched back, trunk down at
  the left; reads as the quadruped.
* lizard_1 (38): four legs at the corners of a long body, tail out the back;
  reads as a lizard.
* lizard_2 (40): long head and tail, four short legs; reads as a lizard.
* octopus_2 (60): a mantle with eight arms in two bunches; reads as an octopus,
  with an irregular arm fan.
* octopus_3 (56): mantle with eight evenly fanned arms; reads as an octopus.
* spider_0 (70): eight long jointed legs around a small body; reads as a
  spider.

None looks worse than its symmetric folder in the 2026-10-06 samples as a
silhouette; the smaller grids simply spend the sheet on larger flaps.

**4. Determinism and packing time.**

*Determinism.* Not a second full fold: `pipeline.pack_options(roll).summary()`
(verdict, gain, `n_smaller`, both grids, metrics, recommendation) was computed
for all 51 rolls in two separate Python processes and the two JSON dumps
compared: `51 51 True []` (identical). The summaries also match the `layout`
fields of the corpus run for every tree (grid of the symmetric and smaller
layouts, `n_smaller`). Layout decisions are therefore the same across processes
and runs.

*Extra packing time.* `pack_secs` in the corpus run against the 2026-10-06
records, largest first:

| roll | `pack_secs` now | 10-06 | extra |
|---|---|---|---|
| spider_0 | 140.3 | 5.8 | 134.6 s |
| scorpion_1 | 136.3 | 5.8 | 130.5 s |
| octopus_2 | 123.9 | 2.5 | 121.4 s |
| scorpion_0 | 110.1 | 5.3 | 104.8 s |
| octopus_3 | 55.5 | 4.1 | 51.4 s |
| ant_1 | 16.1 | 0.8 | 15.3 s |

All 51 are under the spec's about 165 s. The brief's "~120 s" figure is
exceeded by spider_0 and scorpion_1 (about 135 s) and touched by octopus_2; the
spec was amended to 165 s for this reason (budget section above). Wall time is
noisy on this shared host: the same packing-only runs gave spider_0 at 288 s
and 75 s in the two determinism processes, and octopus_2 at 139 s and 169 s.
Ticks, not seconds, are what the budget counts and they are deterministic.

**5. Suites.** `make PYTHON=... test`: 624 passed, 2 skipped (pipeline, 321 s)
and 104 passed (app server, 73 s), 396 s in all. `cd app/web && npm test`: 94
passed; `npm run build` succeeds (only the usual chunk-size warning).

*CI timeout.* `.github/workflows/ci.yml` gives the `test` job
`timeout-minutes: 30` and the `web` job 10. The calibration tests
(`test_octopus_2_fits_the_budget`, `test_scorpion_0_stops_within_the_budget`,
reported at about 5 min together; not timed separately here) are part of the 321 s pipeline run above, so the whole
`test` job needs about 7 min of test time on this Mac, well inside 30 min even
at two to three times slower on a CI runner. CI is unchanged.
