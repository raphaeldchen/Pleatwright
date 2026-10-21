# How small is the actual cause of a CEGAR rejection?

Spec: `../../specs/2026-09-27-nogood-core-design.md`. Script: `core_measure.py`.
Artifact: `core-sizes.json` (31 rows). Figures from this run are read directly
from that file; cross-referenced figures (wall clock, the pre-core column, the
large-budget figures, per-subject `propagate` times, and the 466,682 face-pair
figure) are cited to their sources inline.

```
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -u \
    ../docs/superpowers/evidence/2026-09-27-nogood-core/core_measure.py \
    ../docs/superpowers/evidence/2026-09-27-nogood-core/core-sizes.json 25
```

Run 2026-09-27 on `f21c382`, **1,213 s wall clock (20 m 13 s)**, exit 0. The
25-rejection depth sample completed in full: no `spy()` topology-drift
`AssertionError`, so **no truncation**, and **0 rows carry an `error` or `note`
key** — all 31 rows are measurements. `blamed_not_slots` is 0 on all 31, so
spec §4.1's slot-edge assertion held and no blamed crease was silently dropped.

---

## Headline: the cone was ~22x larger than the cause. Verdict band `<=10`.

| | pre-core (spec §1) | **measured core** |
|---|---|---|
| clause size, **solver variables** (median) | **109** | **5** |
| clause size, solver variables (max) | 245 | **8** |
| clause size, **FOLD edges** (`witness.creases`) (median) | 172 | **6** |

*The "creases" label on that last row was made explicit 2026-09-27. Every crease
count in this file is a **FOLD-edge** count (`len(witness.creases)`) — not a
`piece_keys` unit-crease count, which is what "creases" means in
`../2026-09-24-dense-pleats/README.md`. The two differ by an order of magnitude and
must not be compared.*

*The 109/172 pre-core medians and the 5/6 core medians are the 25-rejection
`lizard` depth sample (see Depth, below); the pooled median across all 31 rows,
`lizard` and the five other subjects together, is a blamed-variable median of
64, not 109 (see Breadth).*

**Median core: 5 solver variables against the pre-core median of 109 — a 21.8x
tightening.** Per-row tightening on the depth sample runs 1.2x (min) to 59.2x
(max), median 21.8x.

**This size headline is a single-subject measurement.** 26 of the 31 rows are
`lizard` (25 depth rows plus `lizard`'s own breadth row). Of the other five
breadth rows, four subjects (`frog`, `horse`, `bird`, `guinea_pig`) arrived with
a blamed set of only 2 variables — nothing to shrink — and the fifth
(`starfish`) arrived with 6. The `<=10` band verdict below is 31/31 and stands
regardless of population; the 109 -> 5 *magnitude* does not, and this run does
not support generalising it beyond `lizard`.

**This lands in spec §8's `<=10` band, and not marginally: `core_variables <= 10`
on 31 of 31 rows, and the observed maximum over the whole run is 8.** The band
does not depend on where the median falls, because every single row is inside it.
Per §8 that **justifies a follow-on spec that wires extraction into the CEGAR
loop**. It does not authorise the wiring; the follow-on is gated and is
explicitly out of scope here (§11), and nothing in this slice is wired into
production — `grep -c box_pleat mcp_harness/server.py` is still 0.

**The suspicion in §1 is confirmed as stated.** Every one of the 31 rows is a
`taco_tortilla` among exactly **3** faces (`witness_kind` and `witness_faces` are
constant across the artifact), and the recorded cause was a median of 172 FOLD
creases. The actual cause is 6 creases / 5 variables. `witness.creases` is a
dependency **cone**, and the cut inside it is 3.5% of it on creases (6/172) and
4.6% of it on variables (5/109).

**The depth sample reproduces the baseline exactly, so the comparison is
like-for-like.** All four of spec §1's `witness.creases` and clause readings come
back identical on this run's 25 lizard rejections:

| reading | spec §1 baseline | this run's depth sample |
|---|---|---|
| `witness.creases` min / median / max | 6 / **172** / 386 | 6 / **172** / 386 |
| clause variables min / median / max | 6 / **109** / 245 | 6 / **109** / 245 |
| `witness.faces` | 3 / 3 / 3 | 3 / 3 / 3 |

That is the same population, not a second one that happens to be smaller, so the
109 -> 5 comparison is not an artefact of sampling a different set of rejections.
The variable counts are computed with `assign`'s own clause expression
(`assign.py:1022`), so the two cannot disagree about what a clause's variable set
is.

## Monotonicity checks: 0 failures in 31 rows

All three of spec §4.2's checks passed on **every** row (`checks.all_ok` true,
31/31; **failure count 0**):

* `full_blamed_contradicts` — true on 31/31. The oracle reproduces the rejection
  it came from.
* `empty_contradicts` — false on 31/31. The contradiction is not independent of
  the labelling.
* `core_plus_one_contradicts` — true on 31/31.

Had any row failed, **no figure in this file would be quotable** and this section
would report the failure instead of the sizes. It did not happen, so the sizes
above stand. Soundness is structural rather than statistical: every core was
*tested* by the oracle, so a too-small core could not have been produced (§4.3).

## Breadth: one rejection per labelling-capable subject

`assign(global_check=None)`, first locally feasible dense candidate, no CEGAR
loop. `s/call` is derived (`extract_secs / oracle_calls`).

| subject | blamed cr | blamed var | core cr | core var | oracle calls | secs | s/call |
|---|---|---|---|---|---|---|---|
| `starfish` | 6 | 6 | 5 | 5 | 11 | 0.02 | 0.002 |
| `lizard` | 44 | 44 | **8** | **8** | 29 | 4.15 | 0.143 |
| `frog` | 2 | 2 | 2 | 2 | 3 | 0.54 | 0.180 |
| `horse` | 2 | 2 | 2 | 2 | 3 | 1.45 | 0.483 |
| `bird` | 2 | 2 | 2 | 2 | 3 | 2.24 | 0.747 |
| `guinea_pig` | 2 | 2 | 2 | 2 | 3 | 1.66 | 0.553 |

**⚠ Read this table for COST, not for SIZE. Five of its six rows had nothing to
shrink.** `frog`, `horse`, `bird` and `guinea_pig` each arrived with a blamed set
of **2 creases / 2 variables** and returned a core of 2 — `core_variables ==
blamed_variables` on those four rows. `starfish` arrived with 6 and returned 5.
A tightening ratio near 1.0 on such a row is **a fact about that subject's first
dense candidate, not a fact about the method**: there was no cone to cut. The
four 2-variable rows also mean the pooled all-rows median the script prints
(`blamed variables median 64 -> CORE 5`, 12.8x) understates the blamed side,
because those rows drag the blamed median down and the core median is already at
the floor. **The headline above is therefore the depth median (109 -> 5, 21.8x),
which is the only like-for-like figure available**, and `lizard`'s breadth row
(44 -> 8) is the breadth row with the largest tightening; `starfish`'s (6 -> 5)
is the only other breadth row that shrinks at all.

The breadth rows are not discarded — they are 6 of the 31 rows behind the "31 of
31 rows have `core_variables <= 10`" claim, and they are the corpus-wide cost
evidence below. They just cannot drive the size headline.

## Depth: 25 rejections on `lizard`

| reading | min | **median** | max |
|---|---|---|---|
| blamed **FOLD edges** (`witness.creases`) | 6 | **172** | 386 |
| **core FOLD edges** | 4 | **6** | 8 |
| blamed variables | 6 | **109** | 245 |
| **core variables** | 4 | **5** | 8 |
| oracle calls | 11 | **35** | 57 |
| extraction seconds | 1.30 | **5.27** | 9.80 |

Core size distribution over the 25 depth rows: 4 vars x4, 5 vars x9, 6 vars x7,
7 vars x1, 8 vars x4. **The distribution is tight and flat in the blamed size** —
the largest blamed set in the run (386 creases / 245 variables, depth row 9)
yielded a 6-variable core, and the smallest blamed set in the run (6 creases / 6
variables, depth row 15) yielded a 5-variable core — a ~41x range in cone size
(245 vs 6 solver variables) producing cores of 6 and 5. Core size does not
track cone size, which is what "the cone is not the cause" predicts.

Note also that **at core scale FOLD edges and variables nearly coincide** (median
6 edges / 5 variables), whereas at cone scale they separate — median 172 FOLD
edges against 109 variables, a factor of 1.58. The merged-run-to-piece collapse
that makes a crease count run ahead of a variable count is a property of the cone,
not of the cause.

⚠ *Corrected 2026-09-27. This sentence read "whereas at cone scale they diverge
sharply (172 -> 109 here, 2,069 -> 202 in the large-budget run)", and the second
ratio has been dropped for two independent reasons. (1) **The two ratios are over
different populations.** 172 is `len(witness.creases)` — FOLD edges — while 2,069
is a `piece_keys` **unit-crease** median (`../2026-09-24-dense-pleats/README.md`
labels it "`len(keys)`, what `piece_keys` returns"), so 1.58x and 10.2x do not
belong in one parenthesis, and the merged-run-to-piece mechanism named next
applies only to the second. `../../specs/2026-09-27-nogood-core-design.md` §1
gives all three readings for this very 25-rejection sample. (2) **The attribution
was wrong**: 2,069 creases / 202 variables are the medians of
`../2026-09-24-dense-pleats/nogood-lizard.json` (113 rejections, no
`assign_budget` key — the default run); the large-budget run
(`nogood-lizard-largebudget.json`, `assign_budget` 5,000,000, 584 rejections)
reads 2,117 and 204.5. This file measures no unit-crease population of its own, so
the comparison is withdrawn rather than restated.*

## Cost, reported separately from size

**Oracle calls is the portable number.** Depth median **35** calls per rejection,
max 57. That is above the spec's ~20 estimate but inside Junker's bound for
QuickXplain at this core size and candidate count. It is the figure to carry into
the follow-on, because it does not depend on any subject's propagation speed.

**Seconds, measured:** depth median **5.27 s** per rejection, max 9.80 s; 136.5 s
and 905 oracle calls for all 25 lizard rejections together. Against the
large-budget run's **15.18 s per candidate** on `lizard`, extraction would add
roughly a third to the cost of a rejection on this subject.

**⚠ The spec's own cost expectation was INVERTED by the measurement, and this is
the correction a reader most needs.** Spec §6 and §10 risk 2 warned that a
`lizard`-derived seconds figure *overstates* extraction cost by ~100x, because
`lizard`'s `propagate` costs 1.07 s against 0.004–0.014 s on the other five
subjects. At the level of a whole extraction that warning stands — a `lizard`
rejection is the expensive kind. But **per oracle call the ordering reverses**:
`lizard` extraction calls run **0.143 s** (breadth) / **0.140 s** median (depth),
while `bird` reads **0.747 s**, `guinea_pig` **0.553 s** and `horse` **0.483 s**
per call — 3.45x (horse) to 5.34x (bird) *more* than `lizard`'s 0.140 s depth
median, and, against those subjects' own production `propagate` times in
`../2026-09-24-dense-pleats/README.md` (bird 0.006 s, guinea_pig 0.014 s, horse
0.012 s), the ratios are bird 124.5x, guinea_pig 39.5x and horse 40.2x — roughly
40x to 125x, not a single tight band.

The mechanism, which follows from the oracle's definition rather than from a
guess: a fully-seeded `propagate` **exits at the first contradiction**, so the
per-subject `propagate` figures in `../2026-09-24-dense-pleats/README.md` §4b are
*time-to-first-contradiction*. A subset-seeded call that finds **no**
contradiction has no early exit and must propagate to fixpoint. On `bird` that is
466,682 face pairs. So a **negative** oracle call is the expensive kind, and
production `propagate` time does not predict extraction cost in either direction.

**The size of that caveat, stated honestly.** The four 2-crease breadth rows made
exactly 3 oracle calls each, and all three returned False — forced, not assumed:
`empty_contradicts` is false, and `core_creases == blamed_creases == 2` means
both singletons were necessary, so `oracle(∅)`, `oracle({a})` and `oracle({b})`
all returned False. Those rows therefore measure **only** the expensive
full-fixpoint call, and their `s/call` is an upper bound on per-call cost, not an
average. `lizard`'s 0.140 s median is a mix of positive and negative calls over
much larger candidate sets. The two are **not like-for-like**, and no per-call
figure here should be multiplied out into a per-rejection cost for a subject that
never produced a real rejection. For scale only, and as an **extrapolation from
three calls rather than a measurement**: `bird` at `lizard`'s 35 calls and
`bird`'s measured negative-call cost would be ~26 s per rejection. Measuring
extraction cost on a non-`lizard` subject requires rejections from those
subjects, which this run did not obtain and which the follow-on would need.

## What this does NOT establish

**A small core implies stronger pruning per rejection. It does NOT imply
convergence.** These are different claims and only the first is measured here.

The large-budget run (`../2026-09-24-dense-pleats/README.md`) refused **584
distinct** candidates in **8,865 s** and **every one was new** — no contradiction
repeated, the clause never tightened (202 -> 204.5 variables across 5.17x more
experience), and candidates grew as budget^**0.71**. The space of distinct
contradictions is vast. A 21.8x tighter clause forbids a much larger region per
rejection, but whether that region-per-rejection multiplied by an achievable
number of rejections covers that space is **a separate question this file does
not address in either direction**.

**This file must not be cited as evidence about convergence.** It is evidence
about clause *size*, and about one mechanism (the cone is not the cut). The
convergence effect is precisely what spec §8 says a follow-on would have to
measure, and it is the reason the follow-on is a gated experiment rather than a
feature.

Two further non-claims:

* **The cores are irreducible, not minimum.** Every element is necessary, but a
  smaller core may exist (§5; a minimum core is NP-hard and was not attempted).
  So 5 variables is an upper bound on the true minimum, which only strengthens
  the direction of the headline.
* **Which irreducible core is found is not canonical.** It depends on
  QuickXplain's split order, which is why the candidate set is `sorted(...)`.
  Reproducibility of *this* core is what is claimed; uniqueness is not.

## Where this leaves the line of work

This is the fifth lever examined in the CEGAR-cost line of work (spec §8: "four
levers have already been examined in this line of work and two died; a fifth
dying is information"), and the first to come back positive. The other four:
the COrigami F.1.1 pleat filter (a no-op at the paper's own granularity),
no-good indexing (withdrawn — the clause scan is 1.28% of runtime; the slowdown
is more nodes, not slower nodes), F.3 ridge assignment (degenerate — of its three
rules, *one* already exists here under another name, the mirror merge, and *one*
is inert on our geometry; corrected 2026-09-27 from "two of its three rules
already exist here under other names", which is both stronger and different from
what `../2026-09-27-f3-rules/` found), and raising the assign
budget (the large-budget run: 10x budget bought 5.17x candidates, budget^0.71,
closed as economically implausible — see
`../2026-09-24-dense-pleats/README.md`).

The positive result is **narrow and exactly what the spec asked for**: the cause
of a rejection is 5 variables where the clause states 109, on a sample that
reproduces the baseline's figures exactly, with 0 monotonicity failures. The
decision §8 attaches to that is a follow-on spec, and the cheaper structural
alternative the prior-art pass already identified — a 1-UIP-style implication-graph
cut instead of repeated QuickXplain oracle calls — becomes the obvious thing for
that spec to weigh, since it needs `layer_order.py`, untouched across this work
(§2, §11).
