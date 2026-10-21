# Were dense `lizard`'s 113 rejections 113 obstructions, or a few repeated ones?

**23.** Ninety of the 113 rejections re-derive a cause already seen — 104 rows sit in a group that recurs, and 14 of those are the group's own first sighting (*derived*, 104 − 14 = 90; check: 23 first sightings + 90 re-derivations = 113).

The same 113 rejections were already measured to have **113 distinct witnesses** —
`../2026-09-24-dense-pleats/nogood-lizard.json`'s `distinct_witnesses`. What changes the
answer is not the budget or the subject but **extraction**: the dependency cone never
repeats, and the minimal cause under it repeats constantly. See §4.3.

Spec: `../../specs/2026-10-02-witness-identity-113-design.md`. Script: `identity113.py`.
Artifact: `identity113.json` (the guard, both bars, the distinct counts, the multiplicity
and overlap tables, and all 113 per-rejection records in full).

**Every measured figure in this file is read from `identity113.json`**, re-read after the
process exited rather than transcribed from the log watched while it ran. Figures cited
from other evidence directories are attributed inline **on every appearance**. Figures
obtained by arithmetic or set operations on the artifact's own fields are marked *derived*
and show their derivation.

```
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -u \
    ../docs/superpowers/evidence/2026-10-02-witness-identity-113/identity113.py \
    ../docs/superpowers/evidence/2026-10-02-witness-identity-113/identity113.json
```

**Run metadata is this README's own record and is not in the artifact**, because
`identity113.py` writes neither a timestamp nor a commit into the JSON — a defect its
predecessor recorded against itself and this successor did not fix. Run **2026-10-02**,
launched 08:01:50Z on commit **`da3c629`**, exit **0**. The script's `--selftest` was run
immediately before and passed, printing `ARM_A pinned against
../docs/superpowers/evidence/2026-09-27-core-in-loop/ab.json` — so the guard's baseline
constants were checked against their source file, not merely against themselves.
`identity113.py` was not modified at any point during or after the run.

**`cores.CoreExtractionError` was never raised** — `core_refusals` is **0**, so all 113
rejections carry a real core and both bars ran on the full population with nothing
defaulted. That matters for the same reason it did in the predecessor: `cores._core`
checks its own pre- and postcondition and raises rather than returning an unsound core,
so its silence is the evidence that these 23 cores are the cores they claim to be.

---

## Verdicts

| bar | verdict | population | `partial` | `note` |
|---|---|---|---|---|
| solver (spec §5.2) | **2 LATE ENFORCEMENT** (`verdict_level` = `signed`) | 113 of 113 | `false` | `null` |
| geometry (spec §5.4) | **G2 BOUNDED** | 113 of 113 | `false` | `null` |

Both bars ran over the complete 113-rejection population, so neither verdict is PARTIAL
and neither carries a caveat note. `malformed_records` is `[]` for both.

**The two bars fired on the same 23 objects.** That is not a coincidence of thresholds
and it is the central finding — see §4.

## 1. The question, and why n=3 could not answer it

The core-in-loop A/B (`../2026-09-27-core-in-loop/`) settled that the no-good clause
narrows hard — median **202 → 8** solver variables, *its* figures — and left the terminal
outcome unmoved: both arms ended `AssignFail(kind='budget', site=500000)`. What moved was
the rejection count, **113 → 3**, again that directory's figures.

The identity instrument was then built and run (`../2026-09-28-witness-identity/`), but
only on the 3-rejection arm, because the record sat inside the `core_extraction` branch.
It returned row 4 NEW TERRITORY and said plainly what that was worth: *"three distinct is
consistent with new territory each time and equally consistent with a loop that would
begin repeating at rejection 20."*

**The loop begins repeating at rejection 8.** *Derived* from `rejection_records`: the 8th
and 3rd rejections **(0-based indices 7 and 2)** have equal `core` and `signed`. The predecessor's caveat was correct
and its guessed threshold was conservative by a factor of 2.5.

## 2. The reproduction guard (spec §5.5, §5.6)

`guard_passed` = **`true`**, `guard_mismatches` = **`[]`**.

| guarded value | expected (arm A) | measured | |
|---|---|---|---|
| rejections | 113 | **113** | **PASS** |
| `layers_tried` | 113 | **113** | **PASS** |
| `records` | 113 | **113** | **PASS** |
| `failure` | `AssignFail(kind='budget', site=500000)` | **identical** | **PASS** |
| `clause_sizes` length | 113 | **113** | **PASS** |
| clause vars min / median / max | 6 / 202 / 259 | **6 / 202 / 259** | **PASS** |

The expected column is the artifact's own `arm_a_expected`, whose `source` field names
`../2026-09-27-core-in-loop/ab.json arms[0]`; the measured column is `rejections`,
`layers_tried`, `records`, `failure` and `clause_sizes`.

**This guard is weaker than the predecessor's, and spec §5.6 says so in advance.** Arm B's
guard compared three exact per-rejection triples *in order*; arm A published no
`core_rows`, so this one can compare only a count and a min/median/max. The run therefore
**publishes its full 113-value `clause_sizes` population** so a successor can guard it
exactly. Fixing the guard forward is part of the deliverable, not a note about it. The
published `clause_sizes` is **sorted** (`main()` writes `sorted(clauses)`), so it is not in
rejection order: a successor correlating `clause_sizes[i]` with `rejection_records[i]` would
be wrong, because the list is sorted for the min/median/max comparison.

Two further readings agree with arm A without being guarded: `stage_reached` = `assign`,
and `layer_verdict` = `"None"` — the string, because the script records `repr(res.verdict)`,
so the layer stage produced no verdict object at all.

**Non-interference is established separately, and empirically.** The whole design rests on
diagnostic extraction not changing the search, which could not be settled by reading code:
`layers._seeded` returns `dataclasses.replace(graph.cons, direct=direct)` and `replace` is
**shallow**. `mcp_harness/tests/test_box_pleat_witness_record_dense_aa.py` runs dense
`lizard` at 20,000 nodes with `core_record` off and on and asserts the clause-size
population is identical as an **ordered list**; it measured
`[44, 210, 65, 48, 50, 64, 220, 42, 245, 53]` in both arms, 10 rejections each, both
`AssignFail(kind='budget', site=20000)`. The guard above is the same claim re-made at
500,000 nodes on the four figures arm A published.

## 3. The distinct-count table

| level | distinct | population | repeated values | rows covered by a repeat |
|---|---|---|---|---|
| `candidate` | **113** | 113 | 0 | 0 |
| `witness` | **113** | 113 | 0 | 0 |
| `keys` | **113** | 113 | 0 | 0 |
| `core` | **23** | 113 | **14** | **104** |
| `signed` | **23** | 113 | **14** | **104** |
| `core_keys` | **23** | 113 | **14** | **104** |
| `faces` | **38** | 113 | 18 | 93 |
| `kind` | **1** | 113 | 1 | 113 |

`kind` is `taco_tortilla` on **113 of 113** rows, and every witness names exactly **3**
faces (*derived* from `rejection_records`, counting `len(faces)` per row). That reproduces
`../2026-09-27-nogood-core/core-sizes.json`'s 31-of-31 reading on a population 3.6× larger.
`kind` carries no bar row precisely because this was expected; a row guaranteed to fire
measures nothing.

## 4. The finding: `core` and `signed` partition the 113 rejections **identically**

*Derived* from `rejection_records` by grouping rows on each field: the `core` grouping and
the `signed` grouping are **the same 23 groups, row for row**.

That is stronger than either count alone. It means **no recurrence is a case of "the same
cause under a different label pattern."** Every time a cause came back, it came back with
its labels unchanged — the same no-good, re-derived verbatim.

This is why the two bars coincide. The geometry bar reads `core` and the solver bar reads
`signed`; the spec gives them different rows because the same cause under different labels
is one obstruction and a legitimately different no-good. Here that distinction is empty,
so one set of 23 objects answers both questions.

⚠ **"23" IS NOT THE NUMBER OF OBSTRUCTIONS.** `order_probe.py` re-extracted these same
113 rejections with the candidate order REVERSED and found **15** distinct causes, essentially
DISJOINT from these 23. Both sets are irreducible. Read this table as "what ascending
extraction finds", not as a census. See §12.

**The 23 causes, complete.** Multiplicity, core size, and how many distinct face triples
each cause was reported through (*derived* from `rejection_records`; the crease sets
themselves are in the artifact's `repeats` field):

| × | core size | distinct face triples | first rows |
|---|---|---|---|
| **19** | 6 | 13 | 6, 11, 16, 18, … |
| **17** | 4 | 13 | 13, 21, 25, 48, … |
| **11** | 6 | 8 | 8, 29, 36, 38, … |
| **10** | 5 | 3 | 5, 9, 12, 17, … |
| 9 | 7 | 6 | 20, 41, 53, 55, … |
| 8 | 6 | 1 | 26, 51, 54, 85, … |
| 8 | 4 | 3 | 19, 27, 34, 42, … |
| 5 | **46** | 1 | 33, 68, 79, 81, … |
| 5 | 6 | 4 | 31, 37, 40, 65, … |
| 3 | **48** | 1 | 35, 57, 104 |
| 3 | 8 | 1 | 45, 62, 109 |
| 2 | 8 | 2 | 2, 7 |
| 2 | 8 | 1 | 0, 10 |
| 2 | 6 | 1 | 77, 99 |
| 1 | **46** | 1 | 111 |
| 1 | **44** | 1 | 86 |
| 1 | 6 | 1 | 3 |
| 1 | 5 | 1 | 98 |
| 1 | 5 | 1 | 14 |
| 1 | 5 | 1 | 4 |
| 1 | 5 | 1 | 1 |
| 1 | 4 | 1 | 80 |
| 1 | 4 | 1 | 15 |

Mean multiplicity **4.91** (*derived*, 113/23). Nine of the 23 are singletons; the top
five cover **66 of 113 rejections, 58.4%** (`top5.core`).

### 4.1 `faces` is a worse identity than `core`, and the data shows why

The most frequent cause — 19 rejections, core size 6 — was reported through **13 different
face triples**. The second — 17 rejections, core size 4 — through 13. That is why
`faces` reads 38 distinct where `core` reads 23: one cause wears many triples.

The spec pre-registered that **`faces` may never fire a G1 row alone**, on the grounds that
`mcp_harness/box_pleat/layers.py:52` annotates it `# face indices the provenance names;
diagnostic only`. That decision was made before this data existed and the data vindicates
it: had `faces` been allowed to carry the geometry verdict, it would have over-counted the
obstructions by 65% (*derived*, 38/23).

### 4.2 A shipped docstring is falsified by this run — ⚠ ORDER-DEPENDENT, see §12

⚠ **This subsection's conclusion does not survive §12.** Under reversed consumption the core
sizes are 4–7, i.e. INSIDE the range `cores.py` claims. The large 44–48 family is an artifact
of ascending order, so the docstring is not falsified; what is true is weaker and more
interesting — core size is order-dependent. The measurements below are correct for this run's
order and are left as recorded.

`mcp_harness/box_pleat/cores.py`'s module docstring states that **"core size stays flat at
4-8 while cone size spans 6-245."** Measured over 31 rejections, that was right:
`../2026-09-27-nogood-core/core-sizes.json` reads `core_creases` min 2, median 5, max **8**.

Over these 113 it does not hold. `core_rows` reads core size min 4, median 6, max **48** —
six times the prior maximum. Four of the 23 causes are large (44, 46, 46, 48 creases) and
they account for **10 of the 113 rejections** (*derived* from the table above: 5+3+1+1).
The small family (4–8) still covers 103.

The cone also ran larger here: `core_rows` reads blamed min 6, median **327**, max 395,
against `../2026-09-27-nogood-core/core-sizes.json`'s min 2, median 65, max 386. The
maxima are comparable; the medians are not, and that directory's population mixed subjects
and arms, so the comparison bounds nothing on its own.

**This does not weaken narrowing's case** — a 48-crease core against a 395-crease cone is
still an 8.2× narrowing (*derived*) — but the docstring's "flat at 4-8" is a claim about a
31-row sample stated as a property, and it should be corrected to say so.

### 4.3 The witness-level result REPRODUCES a prior measurement; the core-level result does not

**`witness` reading 113 distinct with 0 repeats is not new, and must not be presented as
new.** `../2026-09-24-dense-pleats/nogood-lizard.json` already measured this arm —
`rejections` 113, `var_clause_size_min/median/max` 6/202/259, the same
`AssignFail(kind='budget', site=500000)` — and recorded **`distinct_witnesses` = 113**,
**`top_witness_count` = 1**, with a `witness_count_histogram` of all ones. This run
reproduces that independently, through a different instrument.

That directory went further than this run on budget. `nogood-lizard-largebudget.json`
records **584 rejections at a 5,000,000-node budget** with **`distinct_witnesses` = 584**
and `top_witness_count` = 1 — so **witnesses still never repeat at 5.2× the rejection
count** (*derived*, 584/113).

**That contrast is what makes the core result informative rather than merely different.**
Across two budgets and 697 rejections of prior measurement, the *cone* identity has never
once repeated. On the same 113 rejections, the *core* identity repeats 14 times and covers
104 rows. The cone is not a weak identity by accident: that same README observes the cone is
an "over-approximation that drags propagation hubs into every witness," and its
large-budget artifact quantifies it — **`crease_freq_max` = 581**, meaning one crease
appears in 581 of the 584 cones.

So the honest division of credit is: **the question "do the rejections repeat?" was already
answered NO at the cone level, twice, and this run answers it YES at the cause level.**
Extraction is what changed, not the budget and not the subject.

One further cross-check falls out. That artifact's `elapsed_secs` for the same 113
rejections is **834.0**, against `../2026-09-27-core-in-loop/ab.json`'s **1052.0** for arm A
and this run's search-side share of roughly 1115 s (*derived*, 2435.9 − 1321.3). Three runs
of one unchanged search path spanning 834–1115 s is a **1.34×** spread (*derived*), which is
why §2's guard checks structure and not wall clock.

**One more prior overlap, and it runs in the modest direction.**
`../2026-09-24-dense-pleats/README.md` records a **withdrawn** claim of *"38 distinct
contradictions of 113, one repeating 15×"*, and explains why it was withdrawn: the probe
bucketed witnesses on `w[w.find("faces="):w.find("faces=")+40]`, a truncated slice, so it was
counting **face triples** rather than contradictions, while the committed diagnostic read 113
distinct witnesses of 113.

This run's `faces` level reads **38 distinct** with multiplicities `[15, 15, 7, 7, …]`
(*derived* from `rejection_records`). **The withdrawn count was correct** — it was the right
number for the wrong object, and that directory's own diagnosis of its probe is confirmed
here. So §4.1's 38 is independently corroborated by a second instrument, and the prior claim
differed only in reading two ×15 triples as one.

That claim's **conclusion** was "the loop rediscovers what it has already stored," retracted
at the time because the witness-level reading refuted it. This run reinstates that
conclusion, on a different identity level and soundly: row 2 LATE ENFORCEMENT over 23 causes
and 90 re-derivations. Credit for the reading belongs there.

**What this does NOT reinstate.** That same withdrawn text also concluded *"no budget
increase can converge this"*, and that stays withdrawn. Nothing here speaks to it, and the
same directory's `nogood-lizard-largebudget.json` is evidence against it: a 10× budget
produced 584 rejections against 113, so budget does buy more candidates. The standing
position is unchanged — dense does not converge within 113 candidates and a 500,000-node
budget, **not** that it cannot.

## 5. Multiplicity, and an estimate that is not a measurement

Histogram per level, as *multiplicity → how many values occur that often*
(`multiplicity_histogram`):

| level | ×1 | ×2 | ×3 | ×4 | ×5 | ×6 | ×7 | ×8 | ×9 | ×10 | ×11 | ×15 | ×17 | ×19 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `core` / `signed` / `core_keys` | 9 | 3 | 2 | – | 2 | – | – | 2 | 1 | 1 | 1 | – | 1 | 1 |
| `faces` | 20 | 3 | 6 | 2 | 1 | 2 | 2 | – | – | – | – | 2 | – | – |
| `keys` | 113 | – | – | – | – | – | – | – | – | – | – | – | – | – |

**Chao1 is an ESTIMATE and its assumption does not hold here.** `chao1_reference` reads
**36.5** for `core` (and for `signed` and `core_keys`), **104.67** for `faces`, and `null`
for `candidate`, `witness`, `keys` and `kind` — where the estimator is undefined because
there are no doubletons, and the script returns `null` rather than a number that would read
as a measurement of zero. The `core` figure is *derived* by the estimator as
`23 + 9²/(2·3) = 36.5` from `f1 = 9` singletons and `f2 = 3` doubletons.

Chao1 assumes independent sampling. **These 113 rejections are the output of one search,
not independent draws**, so 36.5 is a reference point for "how many causes might exist
beyond the 23 observed" and is **not a claim about this fold**. The same caveat applies to
the 104.67 for `faces`, which is in any case an estimate of the wrong population — §4.1
shows face triples are not causes.

## 6. Every repeat, by level

- **`candidate`, `witness`, `keys`: none.** `repeats` is the empty map at all three, and no
  `REPEAT at ...` line was printed for them. So **row 1 ENFORCEMENT DEFECT did not fire**:
  the loop never re-checked a labelling it had already refuted, over 113 rejections. Nor
  did any cone-derived clause input recur.
- **`core`, `signed`, `core_keys`: 14 repeated values each, covering 104 of 113 rows**, with
  the multiplicities in §4's table. The crease sets themselves are in the artifact's
  `repeats` field, keyed by the serialised value and listing the row indices.
- **`faces`: 18 repeated triples covering 93 rows.**
- **`kind`: one value, `taco_tortilla`, covering all 113.**

Row indices in `repeats` and in `overlaps` are indices into the record list **as given**, so
a reported row can be looked up directly in `rejection_records`.

## 7. Pairwise overlap — distinct is not disjoint

The predecessor's §3 found its three candidates reading fully distinct while agreeing on
677 of 745 labels, and noted a reader would find that unaided. The same holds at 113, and
more sharply.

**`candidate`** (`overlaps.candidate`, all 6328 pairs — *derived*, 113·112/2): every
candidate is a complete labelling over the **same 745** creases, and pairwise agreement
runs **min 482, median 650, max 739** of 745. So the median pair agrees on **87.2%** of
labels (*derived*, 650/745) and the closest pair differs on **6** (*derived*, 745−739).
For scale, two independent labellings over 745 binary creases would be expected to agree
on about half, ~372 — an expectation for independent labellings offered as a reference
point, not a claim about these 113, which are one search's outputs.

**`core`** (`overlaps.core`, 6328 pairs): **10.3%** of pairs are disjoint, **8.3%** are
identical, and the mean shared size is **2.31** (*derived* from the 5-tuples' third field).
The 8.3% identical is the §4 repetition seen pairwise.

**This does not soften the verdicts.** The bars ask about identity, not distance, and a
`candidate` set differing in 6 of 745 labels is still a different labelling. But it is the
reading a reviewer would reach on their own, and it points the same way as §4: this is not
a picture of a search ranging widely.

## 8. The `core_keys` counterfactual (spec §5.3)

`keys` is the clause input `assign` actually received — derived from the full cone.
`core_keys` is the clause input **the narrowing path would have built**, computed on all 113
of arm A's rejections for one extra `piece_keys` call.

| | distinct over 113 | repeated values | rows covered |
|---|---|---|---|
| `keys` (what arm A used) | **113** | 0 | 0 |
| `core_keys` (what narrowing would have built) | **23** | 14 | **104** |

**Narrowing collapses 113 distinct clause inputs onto 23.** That is the prediction spec
§5.3 registered, and it resolves the A/B's central ambiguity in a specific direction.

The mechanism is `assign.hits_nogood`: a clause prunes only when its **last** variable
becomes bound, so arm A's 113 wide clauses (median 202 variables,
`../2026-09-27-core-in-loop/ab.json`'s figure) each effectively forbade one point and did
nothing to stop the same 6-crease cause being re-derived **18** times after its first
sighting (19 occurrences). A narrowed clause over
that cause forbids every labelling sharing it. So arm B's **113 → 3** is consistent with
narrower clauses excluding more of the space a priori — the first of the two readings §1
offered — rather than with the search wandering.

**The limit, stated whichever way it fell.** This is **arm A's trajectory under
counterfactual narrowing, not arm B's actual trajectory.** It shows narrowing *can*
collapse these rejections; it does not show arm B's 3 rejections *were* the collapsed
remainder of these 113. Arm B ran a different search from its first rejection onward.
`core_keys` carries **no bar row** for this reason.

## 9. What the verdicts make the next slice

### The solver reading

**Row 2 LATE ENFORCEMENT fired over the full population.** The spec describes its trigger
as "a no-good re-derived from a different subtree — what `hits_nogood`'s full-binding-only
pruning predicts," and that is what **90** of the 113 rejections are (*derived*; 104 rows sit
in a recurring group, 14 of them as that group's first sighting).

**The remedy already exists and is off by default.** `compile_tree`'s signature carries
`core_extraction: bool = False` (`mcp_harness/box_pleat/compile.py`). Turning it on is what
arm B did. So this run does not call for new machinery; it quantifies what the existing,
unshipped-by-default lever is worth: **90 of 113 rejections are re-derivations** (*derived*,
Σ(m−1) over the 23 groups), i.e. 79.6% of the search's rejection budget spent re-deriving a
cause already in hand.

**It does not close gap 1.** Arm B had extraction on and still ended
`AssignFail(kind='budget', site=500000)` with no fold
(`../2026-09-27-core-in-loop/ab.json`). Cutting re-derivation makes the search cheaper per
unit of exclusion; it did not make the space yield.

### The geometry reading

**G2 BOUNDED**, and it missed G1 on **both** conditions: `distinct_faces` 38 against a
threshold of 10, and `distinct_core` 23 against 20. Pre-registered, G2 means *"a bounded
pool of causes; upstream action plausible but not pinpointed → spatial follow-up."*

⚠ **THE REST OF THIS SUBSECTION IS SUPERSEDED BY §12.** Eliminating a cause upstream does
not remove a contradiction that has a second, disjoint minimal cause — and 112 of 113
rejections have one. Read the paragraph below as the reading this run supported before that
was measured.

**23 causes over 113 rejections is a bounded pool, and the pool is the actionable object.**
Four causes account for 57 rejections (*derived*, 19+17+11+10). If those four are
eliminable in the crease set — by interleaving, by the elevation field, or by the tiling —
half the rejections disappear by construction rather than by search.

**What G2 does not license.** It does not say the pool is 23 and closed. Nine singletons
and a Chao1 reference of 36.5 both point at causes not yet seen, and `layer_order._propagate`
is **not confluent**, so a core is *a* derivation of the contradiction rather than *the*
cause. The spec's asymmetry applies here in the robust direction — a recurrence cannot be
manufactured by non-confluence, so the 14 repeats are real — but the **count** of 23 is a
count of derivations reached by QuickXplain's split order, and a different order could
partition the same geometry differently.

### The one thing this run makes newly answerable

Enumerating the full minimal-unsatisfiable-set family of a **single** rejection would say
whether a recurring cause is the only cause of that contradiction or merely the one
QuickXplain reaches first. Spec §0 named MARCO (Liffiton & Sakallah, *Enumerating
Infeasibility*, JAR 2016) as the prior art for that and gated it on **G1** firing. G2
fired, so by the spec's own gate that follow-on is not opened here — and the 23-cause pool
is now a concrete enough object that the gate's wording, not its intent, is what excludes
it. That is a judgement for whoever writes the next spec, recorded rather than taken.

## 10. Limits (spec §8)

**One subject.** `lizard`, as in every predecessor, for the same measured reason: 26 of the
31 rows behind the core measurement were lizard (`../2026-09-27-nogood-core/`), and the
subjects that would test generality either cannot produce a dense labelling at all or
arrive with two blamed creases and nothing to shrink. Lizard's `propagate` is ~100× slower
than the other five subjects' — 1.07 s against 0.004–0.014 s, which is
`../2026-09-24-dense-pleats/dense_labelling.json`'s `propagate_secs` field for
`lizard` against `starfish` 0.004, `bird` 0.006, `frog` 0.006, `horse` 0.012 and
`guinea_pig` 0.014 (`octopus` and `dog` carry no `propagate_secs` field there, having never reached
propagate). It is the subject here because its dense loop yields rejections cheaply,
not by preference. **Whether any other subject's dense loop
re-derives its no-goods is untested and untestable by this instrument today.**

**One arm, one budget.** Nothing here licenses a statement about dense `assign` in general.

**The geometry bar's asymmetry.** G1 would have been robust and G3 would have been soft;
G2 sits between them and inherits some of each. The repeats are robust — non-confluence
cannot manufacture a coincidence. The **count** of distinct causes is softer, for the
reason in §9.

**What no verdict here can say.** `assign`'s no-good is a `{variable: value}` map built in
`assign`'s own locals; `_check` sees neither `var_of` nor `value`. `keys` and `core_keys`
are clause *inputs*, not clauses. A `signed` repeat is strong evidence and not proof of a
duplicated clause; proving one would need a `debug_clauses` list in `assign.py`, which spec
§10 keeps out of scope. In the direction this run fell, 14 repeated `signed` values over
104 rows make a duplicated narrowed clause very likely — but likely is the claim, not
certain.

## 11. Cost — and a correction to a correction

| component | figure | source |
|---|---|---|
| total | **2435.9 s** (40.6 min) | `secs` |
| extraction, 113 rejections | **1321.3 s** (54.2% of the run) | *derived*, sum of `core_rows`' 4th field |
| extraction per rejection | **11.69 s** | *derived*, 1321.3/113 |
| oracle calls | median **47**, total **6583** | `core_rows`' 3rd field |
| per oracle call | **0.2007 s** | *derived*, 1321.3/6583 |

**I corrected the spec's estimate downward before the run, and the measurement went the
other way.** Spec §7 estimated 0.18 s per oracle call and ~87 calls per rejection, giving
~1770 s of extraction and a ~47-minute total. After Task 2 measured 5.13 s of extraction
per rejection at a 20,000-node budget, I revised that to ~27 minutes.

**Source note.** The 20,000-node figures in this section — 5.13 s of extraction per
rejection, and that run's clause-size median — come from the dense A/A gate and are **this
README's own record**, like the run metadata above: `mcp_harness/tests/
test_box_pleat_witness_record_dense_aa.py` pins the clause-size population it measured
(`EXPECTED_CLAUSE_SIZES`) but records no timing, and the per-arm wall clock was taken with a
throwaway harness outside the repo. Treat them as reported, not as retrievable.

The measurement vindicates the spec's model, not my revision:

* its **per-call** figure was nearly exact — 0.18 s estimated against **0.2007 s** measured;
* its **calls per rejection** was 1.5× high — 87 estimated against **58.3** measured
  (*derived*, 6583/113);
* net, it over-estimated extraction by **34%** (1770 against 1321.3 s), while my revision
  under-estimated it by **56%** (5.13 against 11.69 s per rejection).

The reason is the one both the spec and the Task 2 review flagged as a caveat and I
under-weighted: the 20,000-node sample's cones are far smaller than the baseline's, and
extraction cost scales with cone size. Like for like, this run's clause-variable median is **202** against the 20,000-node sample's
**64** — 3.2× (*derived*) — and its cone median is 327 FOLD edges. The 327-against-64
comparison that first suggested itself here mixes FOLD edges with solver variables, in the
direction that flatters the excuse; the predecessor directory
(`../2026-09-24-dense-pleats/`) is emphatic about that exact trap, having been caught by it. **A small-budget sample is not a scaled
model of a large-budget run, and this is the second time in this line of work that an
overhead figure has failed to transfer between budgets** — the clause-propagation slice
recorded the same lesson in the opposite direction.

The 40.6-minute total sits inside spec §7's stated **35–70 minute** band. Nothing is
guarded on time, so no verdict depends on any of this.


## 12. CORRECTION (2026-10-02, same day): the cores are order-dependent, and 112 of 113 rejections have TWO DISJOINT minimal causes

Script: `order_probe.py`. Artifact: `order-reversed.json`. Run on commit `cdade6e`, exit 0,
1463.8 s. **This section was measured after §1–§11 were published and it changes three of
their claims.** Each is marked inline above.

### 12.1 Why it was run

§9 proposed acting upstream on a localised site, and a crease-level read of
`rejection_records` (not in §1–§11) found `(135, 136)` load-bearing in the minimal core of
**106 of 113** rejections. `cores.shrink` consumes `sorted(creases)` and returns an
**irreducible** core, not a minimum one, and `layer_order._propagate` is not confluent — so
which irreducible set comes back can depend on consumption order. The crease sat a median 31%
through the sorted cone, which weakened that hypothesis without closing it.

### 12.2 The result: the crease was an artifact

The same compile, the same 113 rejections — all 113 cones **pairwise identical** to this
directory's run, and the guard reproduced 113 rejections / 113 `layers_tried` / clause vars
6/202/259 / `AssignFail(kind='budget', site=500000)` — with extraction consuming candidates in
**descending** order:

| | ascending (§1–§11) | descending |
|---|---|---|
| cores that differ | — | **113 of 113** |
| contain `(135, 136)` | **106** of 113 | **0** of 113 |
| distinct causes | 23 | **15** |
| core size min/med/max | 4 / 6 / **48** | 4 / 5 / **7** |
| extraction cost | 1321.3 s | **349.2 s** (*derived*, 1463.8 − the 1114.6 s search share) |

**`(135, 136)` falls from 106 to 0.** It was an artifact of QuickXplain's split order, and the
"one site" reading built on it is withdrawn.

### 12.3 The real finding: disjoint alternative causes

For the **same** rejection, the ascending and descending cores share almost nothing:

* **112 of 113 pairs are completely disjoint**; one pair (rejection 14) shares 4 creases.
* Mean |intersection| **0.035**, against **0.264** expected if the two were independent random
  subsets of the same cone (*derived*, mean of |A|·|B|/|cone|) — an expectation for
  independent subsets offered as a reference point, not a claim about these pairs, which are
  two outputs of one deterministic extractor. They overlap **less** than independence predicts.
* Rejection 35 carries a **48**-crease ascending core and a **4**-crease descending core with
  **zero** creases in common. Rejection 57 likewise. Both passed `cores._core`'s postcondition
  guard, so each contradicts on its own.

This is minimal-unsatisfiable-subset multiplicity, which §0 named (MARCO; Liffiton &
Sakallah, *Enumerating Infeasibility*, JAR 2016) and gated on a G1 verdict that did not fire.
**It is now the load-bearing fact, and it inverts §9's recommendation:** a contradiction with
two disjoint minimal causes is not removed by eliminating one of them. Upstream
site-elimination cannot work on 112 of 113 rejections, and two orders found two alternatives —
nobody has measured how many there are.

### 12.4 What survives, and what does not

**Survives, order-robust:**

| | ascending | descending |
|---|---|---|
| re-derivations | 90 of 113 | **98** of 113 |
| `core` partition ≡ `signed` partition | True | **True** |
| solver bar | **2 LATE ENFORCEMENT** (14 repeated values) | **2 LATE ENFORCEMENT** (10) |
| geometry bar | **G2 BOUNDED** | **G2 BOUNDED** |

The geometry bar holds under both orders because G1 requires `faces` ≤ 10 **and** `core` ≤ 20,
and `faces` is a property of the witness, which this probe did not touch: 38 > 10 fails G1
either way. **Both pre-registered verdicts were robust to a parameter nobody thought to
vary** — which is the strongest thing that can be said for a bar.

**Does not survive:** the `(135, 136)` site (§12.2); "23" as a count of obstructions (§12.2);
§4.2's falsification of `cores.py`'s "flat at 4-8", which holds under descending order; and
§9's upstream-site recommendation (§12.3).

### 12.5 Two things this creates

**A cheaper and sharper default.** Descending consumption is **3.78×** cheaper (*derived*,
1321.3/349.2) **and** returns smaller cores (max 7 against 48). `shrink`'s fixed order is
deliberate and its reason stands — a core found twice must be the same core — but the specific
order it fixed is the worse of the two measured on both axes.

**The next measurement, now justified by data rather than blocked by a gate.** Enumerate the
MUS family of a **single** rejection. Two orders found two disjoint causes; MARCO would find
how many exist. If a rejection has many, a complete method (SAT/ILP over the layer-ordering
constraints) is the only way to settle existence, and no amount of upstream crease-set surgery
will help.

✅ **DONE — see §13.** At least **80** on one rejection, with 47.5% of MUS pairs disjoint and
42 of 44 cone creases load-bearing in some minimal cause. The "no upstream surgery" branch is
the one the data selected.

### 12.6 Limits

One subject, one arm, one budget, as everywhere in this directory. **Two orders are two
samples, not a distribution** — ascending and descending are the two extremes of one ordering
family, and nothing here measures a random order. The disjointness is measured between those
two only; a third order could return a core overlapping either, both or neither.

The probe's own non-vacuity is pinned rather than asserted: it verifies the reversal changes
which irreducible core comes back on a synthetic order-sensitive oracle **before** the real
run, and that check was itself tested against a deliberately inert patch, which it refused.
It prints a verdict only after the guard, the refusal check and the 113-cone equality check
have all passed.


## 13. The MUS family, measured: a single rejection has **at least 80** minimal causes

Script: `mus_probe.py`. Artifact: `mus-family.json`. Run 2026-10-02 on commit `ddee834`,
exit 0, 61.5 min, 28,202 oracle calls. **This answers §12.5's open question and settles the
direction §9 proposed.**

MARCO (Liffiton & Sakallah, *Enumerating Infeasibility*, CPAIOR 2013 / JAR 2016) is the
standard MUS enumerator, but its explored-power-set "map" needs a SAT solver and **none is
installed here** (`pysat`, `pycosat`, `z3`, `ortools` all absent). So two solver-free arms.

### 13.1 Arm 1 — COMPLETE, by exhaustion

Rejection **14**'s cone is **6** creases, so all **64** subsets were tested. No heuristic, no
ordering: a subset is a MUS iff it contradicts and no proper subset does, and both halves are
decided from the full table.

| | |
|---|---|
| contradicting subsets | **8** of 64 |
| **MUSes, exact** | **5** — sizes 4, 5, 5, 5, 5 |
| pairwise disjoint MUS pairs | **0** of 10 |
| **monotonicity violations** | **0** — the assumption holds **exhaustively** |

**The monotonicity result is a contribution in its own right.** `cores.py` states that
QuickXplain's **soundness** rests on `holds` being monotone, and that this is *"an empirical
finding (31 of 31 measured rejections), not a theorem"* — the 31 being single observations per
rejection, not checks of the implication. This is the first exhaustive check: over all 64
subsets of a real rejection, `holds(S)` implies `holds(T)` for every superset `T`, with zero
violations. One instance, so still not a theorem.

### 13.2 Arm 2 — LOWER BOUND, by randomised consumption order, validated against arm 1

200 shuffled orders per rejection. Distinct irreducible cores found is a **floor** on the
family size, never an estimate.

| rejection | cone | MUSes found | last new at | |
|---|---|---|---|---|
| 0 | 44 | **80** | **200**/200 | still climbing |
| 7 | 42 | **69** | 196/200 | still climbing |
| 10 | 42 | **61** | 189/200 | still climbing |
| **14** | **6** | **5** | **16**/200 | **saturated** |
| 15 | 30 | **62** | 198/200 | still climbing |

**Validation, run before any of these numbers were read:** on rejection 14 the sampler found
**5 of 5** exact MUSes — **100% recall, 0 spurious**. The script refuses outright on a
spurious result and withholds its verdict below 80% recall.

**Saturation is what makes the floors readable.** On the one rejection whose true count is
known, 200 shuffles was **12.5×** more than needed — it saturated at shuffle 16 (*derived*,
200/16). On the four large cones it had not saturated at all, still finding new MUSes at
shuffles 189–200 of 200. So 80, 69, 61 and 62 are not near-complete counts; they are floors
**well below** the true families.

### 13.3 The finding that kills site-elimination

On rejection 0, over the 80 MUSes found:

* **47.5%** of the 3,160 MUS pairs are **completely disjoint** (*derived*, 1,502/3,160).
* Their union covers **42 of the 44** creases in the cone — **essentially the whole cone is
  load-bearing in some minimal cause.**
* MUS sizes span **4 to 17**, mode 5–6.

There is no small site. §9 proposed eliminating a localised obstruction upstream and §12.3
showed two disjoint causes made that doubtful; this makes it **structurally impossible**:
removing any one cause leaves at least 79 others, nearly half of which share nothing with it.

**Arm 1's `0 of 10 disjoint` does not contradict this.** Five MUSes of size 4–5 cannot be
pairwise disjoint inside a 6-element universe — there is no room. Disjointness is a
large-cone phenomenon, which is also why rejection 14 was the one rejection in §12.3 whose
two cores were *not* disjoint. The two sections agree.

### 13.4 What this predicts about CEGAR itself

The loop learns **one** clause per rejection. If a rejection has 80+ minimal causes, a
*minimal* clause excludes one of them, and the remaining 79 stay live for other labellings.
That is a mechanism for three results this directory and its predecessors already measured
but could not explain:

* narrowing the clause **25.2×** (`../2026-09-27-core-in-loop/`) tightened the clause and left
  the outcome unmoved;
* a **10×** budget bought only **5.17×** candidates (`../2026-09-26-...`/ memory, exponent 0.71);
* and **90–98 of 113** rejections are re-derivations (§4, §12.4).

Each rejection teaches the solver roughly one-eightieth of why its region is infeasible.

**Stated as a prediction, not a proof.** This gives the first mechanistic reason to expect
per-rejection clause learning in this formulation **not** to converge. It is **not** a proof
that dense cannot fold, and the standing position is unchanged: dense does not converge within
113 candidates and a 500,000-node budget, not that it cannot.

### 13.5 What remains

A **complete** method — SAT or ILP over the layer-ordering constraints — which returns a
witness or a proof of infeasibility rather than enumerating reasons one at a time. It is now
supported by two independent arguments: this one, and the standing fact that
`layer_order._propagate` is **not confluent**, so "consistent" is never a foldability proof.
`"MILP M/V"` has been on this project's adapt-list since the landscape survey, and Lang &
Demaine's facet-ordering conditions (Origami⁴ 2006, already load-bearing in CLAUDE.md §1.1)
are what such an encoding would encode.

A solver would also have to be installed: none is present.

### 13.6 Limits

Five rejections of one subject on one arm at one budget. Arm 1 is complete for **one**
rejection whose cone is the smallest of 113 (6 against a median of 327), so it is ground truth
for an outlier — which is exactly why it is used to validate the sampler rather than to
characterise the population. Arm 2's floors are floors; nothing here estimates a true count,
and the four unsaturated rejections could have families an order of magnitude larger.

The probe's non-vacuity is pinned, not asserted: the capture is verified to have happened,
each captured oracle is checked against `holds(full universe)`, every reported MUS is
re-verified to contradict and to be minimal, and both of arm 1's checkers were themselves
tested against deliberately broken oracles — a non-monotone one to confirm the violation
detector fires, and a non-minimal set to confirm the minimality checker refuses it.


## 14. THE QUERY ANSWERED: the dense crease set **is** satisfiable, and CEGAR's failure was a SEARCH failure

Script: `sat_encode.py`. Artifact: `sat-dense.json`. Run 2026-10-02, python-sat 1.9.dev15,
Cadical153. **This reverses what §9, §12 and §13 were pointing at, and it is the result this
whole directory was working toward.**

### 14.1 What was encoded, and what was deliberately not re-derived

`layer_certify` already decides a **single** labelling completely — it cites
Akitaya–Demaine–Ku, branches where propagation leaves variables free, and returns
CERTIFIED / REFUTED / UNDECIDED. Encoding one labelling as SAT would have rebuilt shipped
work. The non-duplicative query is **joint**: make the labels variables too.

`box_pleat.layers.constraint_graph` is documented as *"the label-independent layer-order
system of a folded state"*, and `compile._check` reuses one graph across all 113 candidates,
re-seeding only `cons.direct` — because M and V both reflect across a crease, giving identical
folded **positions** and differing only in which side lands above. So:

| | |
|---|---|
| order variables (canonical face pairs) | **53,754** |
| **label variables (creases)** | **745** |
| clauses | **9,678,554** |
| from equality / transitivity / taco | 28,192 / **4,511,932** / 74,602 |
| build | 10.9 s, streamed into the solver |

The clause set is `layer_certify._iter_clauses(cons)` **translated, not re-derived**, so this
CNF cannot disagree with the shipped verifier about what the constraints are. Equality →
biconditional; transitivity → the two cyclic states forbidden, 2 clauses per triple; taco →
an even-parity 4-XOR, 8 clauses.

### 14.2 The answer: SAT, in 0.2 seconds

| check | result |
|---|---|
| **the query** | **SAT** (0.2 s) |
| `layer_certify.verify` on the witness' order | **ACCEPTS** |
| **`layer_certify.decide` on the witness** | **CERTIFIED** (2 nodes, 72 free) |
| Maekawa on the witness | **0** violations of **366** interior vertices |
| witness labelling | 361 V / 384 M of 745 creases |
| min Hamming to any of the 113 refuted candidates | **308** of 745 |
| equals a refuted candidate | **False** |

**There exists an M/V labelling of this fixed dense crease set that admits a valid layer
order.** The 500,000-node CEGAR search never came within **308 of 745** labels of it.

### 14.3 Why this is not an encoding artifact

A SAT answer in 0.2 s on a 9.7M-clause instance, contradicting a 500,000-node search, is
exactly the shape of result that is usually a bug. Four controls, and the positive one is
load-bearing:

* **V1 POSITIVE.** On sparse `lizard` — a state whose compile reaches `emit` — the CNF is
  **SAT** and `layer_certify.verify` **accepts the model** (856 clauses checked, 0 skipped).
  This is the control the 113 cannot replace: an **over-constrained** encoding is UNSAT on
  everything and would pass every negative check vacuously.
* **V2 NEGATIVE.** All **113** labellings `layer_order.propagate` refuted come back **UNSAT**
  — 0 wrong, 0.3 s. `propagate` under-refutes but never over-refutes, so each is genuinely
  unsatisfiable, and an **under-constrained** encoding would have admitted some.
* **LEGALITY.** The CNF encodes layer ordering only; Maekawa is **not** among its clauses, so
  a model could have been an illegal labelling that merely happened to be orderable. It is
  not: 0 violations of 366 interior vertices, checked over `ff.shared_edges` rather than
  assumed.
* **INDEPENDENCE.** `layer_certify.decide` — the project's own complete per-labelling
  procedure, which reimplements nothing in this module — returns **CERTIFIED** on the witness.

Sanity, from the same run: `propagate` on the captured candidate returns **CONTRADICTION
`taco_tortilla`**, confirming the captured graph is the refuted pair it claims to be, while
`propagate` on the witness returns **None**.

### 14.4 This reverses the reading, and §13 explains why the search failed

The standing position was that dense *does not converge* within 113 candidates and a
500,000-node budget, **not** that it cannot. That caution is now vindicated in the strongest
way: **the space was never empty.** §13's 80+ minimal causes per rejection were causes of
*refuted* labellings — many reasons why particular labellings fail is entirely compatible with
other labellings succeeding, and the two findings together give the mechanism:

* the CEGAR loop's 113 candidates agree with each other on a median **650 of 745** labels
  (§7) — it never left one basin;
* each rejection has **80+** minimal causes, so a learned clause teaches ~1/80th of why that
  basin is infeasible (§13.4);
* and the satisfying region sits **308+** labels away, which a loop learning one clause per
  rejection was never going to reach.

**So §12 and §13's "site-elimination is dead" stands, and is now moot in the better
direction:** there is nothing upstream to fix. The crease set is satisfiable; the solver could
not find the good region.

### 14.5 What is NOT claimed

**This is not "dense `lizard` flat-folds."** `layer_certify`'s own docstring says it in
capitals: `layer_order.AREA_EPS` drops sliver arrangement cells before `cons.pairs` is built,
and a dropped cell removes constraints and can never add one. So SAT and CERTIFIED both mean
*satisfiable against the constraint set that survived AREA_EPS*.

⚠ **§16 MEASURED THAT GAP AND IT IS EMPTY HERE.** Nothing is dropped at any threshold from
1e-9 down to 0 — the smallest arrangement cell clears 1e-9 by **108,131×** — so on this
instance the constraint set that survived AREA_EPS *is* the full constraint set. The caveat as
stated is closed for dense `lizard`.

**It is also not "the dense pipeline now emits."** The F set and folded topology are fixed to
the ones the pipeline produced; `assign` searches a 3-valued domain (M/V/**F**) under its own
local laws, and nothing here steers it to this labelling. Whether `emit` yields a valid
`.fold` from the witness is the next step, not a result of this one.

One subject, one crease set, one F set.

### 14.6 What this makes the next slice

Hand the witness back to the pipeline. Three things to do in order:

1. **Seed `assign` with the witness** (or fix its 745 labels and run the downstream path) and
   see whether `compile_tree` reaches `emit` and produces a `.fold`. That converts a
   satisfiability result into an artifact.
2. **Close the AREA_EPS gap**, or measure it: how many cells does it drop on dense `lizard`,
   and does the witness survive re-adding them? `layer_certify`'s docstring calls this
   "separate work"; it is now the load-bearing caveat on a positive result rather than on a
   negative one.
3. **Make the complete query a first-class stage.** A 0.2 s SAT call that decides what a
   500,000-node search could not is not a diagnostic — it is a better algorithm, and the
   `box_pleat` compile path should use it. That needs its own spec: `core_extraction`,
   `vertex_index` and `clause_prop` are all still default-off, and this would be a far larger
   change than any of them.


## 15. IT EMITS: a validated dense `lizard` FOLD from the SAT witness

Script: `seed_witness.py`. Artifacts: `seed-witness.json`, **`witness.fold`** (380 vertices,
759 edges). Run 2026-10-02.

§14 found the labelling. This is the artifact, and every validator in the pipeline accepts it.

### 15.1 §14's load-bearing assumption, now MEASURED rather than argued

§14's joint encoding is sound only if `cons` really is label-independent — the argument being
that M and V both reflect across a crease and so give identical folded **positions**. Measured
by flat-folding the refuted candidate's labelling and the witness's and comparing:

| | |
|---|---|
| faces | **380 vs 380** |
| **max \|folded position difference\|** | **0.0** |

Exactly zero, not merely small. The assumption holds on this instance, so §14's SAT result
means what it says.

### 15.2 `compile_tree`'s own tail, run on the witness

The witness is keyed by FOLD edge, so rather than reach back through `piece_keys` into
`assign`'s variables, `edges_assignment` is rewritten on the candidate's own fold — **only
edges already carrying M or V**, so the F set and the boundary are untouched and this is the
same crease set — and `compile_tree`'s post-`assign` tail is run on it.

| step | result |
|---|---|
| creased edges relabelled | **745 of 745**, 0 absent from the witness |
| labels recovered from `ff2` match the witness | **745 of 745** |
| `layers.propagate` | **None (consistent)** |
| `layers.certify` | **CERTIFIED** (2 nodes, 72 free) in 18.3 s |

`res.stage_reached` would be `"emit"` and `res.fold` would be `witness.fold`.

### 15.3 Four independent validators, all clean

| validator | result |
|---|---|
| `cp_audit` — Maekawa (\|m−v\| ≠ 2) | **0** of 366 interior vertices |
| `cp_audit` — Kawasaki residual | **0** over tolerance (max **4.5e-13°** against 0.001°) |
| `cp_audit` — `arrangement_ok` | **366 of 366 True** |
| `cp_audit` — closure | **0** bad edges, max error **3.1e-15** |
| **Oriedita (Tier 3 Java static linter)** | **Pass** |

> **2026-10-04 — `witness.fold` repaired, and this table re-verified against the
> repaired file.** The committed artifact carried an `edges_foldAngle` array
> that was **stale from the refuted candidate**: `seed_witness.py` rewrote only
> `edges_assignment`, so **352 of 745 creases** had an angle contradicting the
> labelling the file claimed. It hid because the histograms nearly agree (388
> entries at −180 against 384 `M`; 357 at +180 against 361 `V`), so a count
> check passes and only a per-edge comparison finds it.
>
> **The verdicts above are unaffected, and that was measured rather than
> assumed.** Oriedita reads `edges_assignment`, not `edges_foldAngle`:
> inverting *every* creased angle leaves it at **Pass**, while flipping a
> *single* assignment yields `Flat-foldability FAILED [REAL] … MAEKAWA` — so
> the instrument is live, not vacuous, and simply does not consult that field.
> `cp_audit` likewise. The repaired file changes `edges_foldAngle` and nothing
> else, and re-reads clean on all five rows.
>
> Where it did bite: the Origami Simulator bridge uses `edges_foldAngle` **when
> present**, so the stale array folded 352 creases the wrong way. See
> `../2026-10-03-dense-fold-simulation/`. `seed_witness.py` now rewrites both
> arrays and refuses if any contradiction survives.

### 15.4 The witness is INSIDE `assign`'s search space

This is the part that pins what went wrong, and it comes from reading `assign.violation()`
rather than from a measurement:

* `assign.py:44` imports **`cp_audit.arrangement_ok_at_vertex`** — the same oracle §15.3 ran.
* `violation()` reports `maekawa`, `arrangement` or `blb`. But on a vertex where **every
  incident piece is bound** — which a complete labelling is — the function reduces to exactly
  two tests: `abs(D) != 2` → `"maekawa"`, then `arrangement_ok_at_vertex(...)` →
  `"arrangement"`. The `blb` return and the `itertools.product` completion search are reached
  **only** when free variables remain; they are mid-search prunes.
* `violation`'s own docstring describes the arrangement oracle as *"cp_audit's exact oracle
  over the folded pieces: Kawasaki and big-little-big"* — so BLB is inside it, not additional
  to it, for a complete assignment.

Both of those tests are clean on all 366 interior vertices. **So the witness satisfies every
local law `assign` enforces on a complete assignment: it was always in the search space, and
the 500,000-node search simply never reached it** — 308+ of 745 labels away, one basin over.
Gap 1's dense failure was a search failure, start to finish.

### 15.5 What is still NOT claimed

**~~`AREA_EPS` still binds.~~ ✅ MEASURED AND INERT — see §16.** Nothing is dropped at any
threshold from 1e-9 down to **0**: the constraint system is identical in every column (26
cells, 53,754 pairs, 4,511,932 triples), **0** intersection drops, and the witness stays
CERTIFIED throughout. The smallest arrangement cell clears the threshold by **108,131×**. So
for dense `lizard` the constraint set that survived AREA_EPS is the full constraint set, and
this was the one caveat that could have undone §15.

**This does not show the search can reach the witness.** Seeding bypasses `assign` entirely.
§15.4 establishes the witness is *admissible*, not that any search order finds it.

**It is not a folded 3-D model.** It is a crease pattern with an M/V assignment and a
certified layer order. One subject, one crease set, one F set.

### 15.6 What this makes the next slice

Unchanged from §14.6 except in priority. The complete query is no longer a diagnostic — it
produced the first validated dense `lizard` FOLD in this project's history, in 0.2 s, after
five slices of search-side work returned negative. **Making it a first-class compile stage is
now the obvious move, and it needs its own spec:** `core_extraction`, `vertex_index` and
`clause_prop` are all still default-off, and this is a far larger change than any of them —
it replaces the CEGAR loop's role rather than tuning it.

Measure AREA_EPS first, because it is the one caveat that could still undo the result.


## 16. THE AREA_EPS CAVEAT IS INERT ON DENSE `lizard`: nothing is dropped, at any threshold down to zero

Script: `area_eps.py`. Artifact: `area-eps.json`. Run 2026-10-02.

§14.5 and §15.5 both named `layer_order.AREA_EPS` the load-bearing caveat on a positive
result — `layer_certify`'s docstring says in capitals that CERTIFIED is not flat-foldable
because AREA_EPS drops sliver arrangement cells before `cons.pairs` is built, and "a dropped
cell REMOVES constraints and can never add one". Measured, it drops nothing here.

### 16.1 The sweep: the constraint system does not move at all

The witness fold's constraint system, rebuilt at six thresholds from the shipped 1e-9 down to
**exactly 0**:

| AREA_EPS | cells | pairs | triples | equalities | tacos | dropped out/int | `propagate` | `certify` |
|---|---|---|---|---|---|---|---|---|
| **1e-9** (shipped) | 26 | 53,754 | 4,511,932 | 28,192 | 74,602 | **0 / 0** | None | **CERTIFIED** |
| 1e-10 | 26 | 53,754 | 4,511,932 | 28,192 | 74,602 | 0 / 0 | None | CERTIFIED |
| 1e-11 | 26 | 53,754 | 4,511,932 | 28,192 | 74,602 | 0 / 0 | None | CERTIFIED |
| 1e-12 | 26 | 53,754 | 4,511,932 | 28,192 | 74,602 | 0 / 0 | None | CERTIFIED |
| 1e-14 | 26 | 53,754 | 4,511,932 | 28,192 | 74,602 | 0 / 0 | None | CERTIFIED |
| **0** | 26 | 53,754 | 4,511,932 | 28,192 | 74,602 | **0 / 0** | None | **CERTIFIED** |

Identical in every column. Not "similar" — the same 26 cells, the same 53,754 pairs, the same
4,511,932 transitivity triples.

### 16.2 Why: the smallest cell clears the threshold by five orders of magnitude

| | |
|---|---|
| arrangement cells | **26** |
| smallest cell area | **1.0813e-04** |
| median cell area | 2.1626e-04 |
| **margin over AREA_EPS = 1e-9** | **108,131×** |

Dense `lizard`'s folded footprint divides into only **26** large cells — each covered by
168–224 of the 380 faces (§14's sizing) — so there are no slivers to drop. The threshold never
fires.

For contrast, all of it `layer_order.py:35-62`'s figures rather than this run's: that
six-subject study found minimum cell areas of **1.02e-09–1.75e-09**, genuinely *straddling* the
1e-9 threshold, with cell counts differing by platform (hshape 4 vs 17, star-6 26 vs 45); and
`template-bird` at 1.378e-06, a margin of ~1,378×. Dense `lizard`'s margin is roughly **78×
larger than template-bird's**.

### 16.3 What the prior study got right, and the half it did not cover

`layer_order.py:35-62` clears the constant on a structural argument: *"a sliver's cover is a
subset of the cover of the cell it was split from, so dropping it removes no pair."*

That argument is **exactly right for half the drops and silent on the other half**. `_cells`
starts from one bounding-box cell and cuts it by each face (`layer_order.py:347`):

* an **outside** piece keeps the parent's cover, so dropping it removes no pair — the prior
  argument holds precisely here;
* the **intersection** takes cover ∪ {face}, a strict **superset**, and `_split_convex`
  (`layer_order.py:310-311`) drops that too. Dropping an intersection removes every pair
  between the new face and the parent's cover, so it *can* remove constraints.

This run counts the two kinds separately for that reason, and reports **0 intersection drops**
at every threshold — so the gap in the argument is real but empty on this instance.

### 16.4 What this closes, and what it does not

**For dense `lizard`, `layer_certify`'s stated gap is closed.** Its docstring defines CERTIFIED
as *"certified against the constraint set that survived AREA_EPS"*. Nothing was dropped, so the
constraint set that survived AREA_EPS **is** the full constraint set, and §15's CERTIFIED is
against all of it.

**It does not clear AREA_EPS in general.** The prior study's subjects genuinely straddle, so
this is a statement about dense `lizard`'s arrangement, not about the constant. One subject,
one crease set, one F set — as everywhere in this directory.

**And it closes only the gap the docstring names.** AREA_EPS is the only mechanism
`layer_certify` cites for CERTIFIED ≠ flat-foldable; whether ADK facewise certification is
equivalent to flat-foldability in the fullest sense is a different question that neither that
docstring nor this run addresses.

**One unexplained reading, recorded rather than smoothed.** `certify` wall clock rises across
the sweep — 15.6 s at 1e-9 to 49.2 s at 0 — on provably identical inputs, since every
structural column above is unchanged. `decide` is deterministic given `cons`, so this is most
likely machine load from concurrent work rather than anything about the thresholds. The
verdict is CERTIFIED at every step, so nothing here depends on it.

### 11.1 The artifact is 25 MB, and does not scale

Recorded for whoever runs this at a larger budget, because nothing in the spec anticipated
it. `identity113.json` is **25.0 MB** on disk for a payload of roughly **7.4 MB**
(*derived*, `len(json.dumps(field))` summed) — `main()` writes with `indent=1`, which
roughly triples it.

`rejection_records` is **89.4%** of that payload and overwhelmingly the dominant term (*derived*, 6,635,499 of
7,423,984 bytes dumped without indentation), because **every
record carries its complete `candidate`: all 745 (crease, label) pairs**, so the field holds
113 × 745 = **84,185 pairs** (*derived*). `overlaps` is **9.6%** here (*derived*, 713,430 bytes) but is **quadratic**:
6,328 pairs per level across 5 levels at 113 rejections, which at the 584 rejections
`../2026-09-24-dense-pleats/nogood-lizard-largebudget.json` reached would be 170,236 pairs
per level, **26.9×** more (*derived*).

So a successor at that budget should expect an artifact of well over 100 MB and should
either store `candidate` as a hash plus a single reference copy, or write without `indent`,
or summarise `overlaps` rather than enumerate it. **None of that may be done by editing this
run's script**, which must stay byte-identical for the result to remain reproducible.
