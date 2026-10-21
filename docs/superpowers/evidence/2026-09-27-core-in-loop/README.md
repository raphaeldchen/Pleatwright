# Does dense layer-ordering converge when the clause is its actual cause?

Spec: `../../specs/2026-09-27-core-in-loop-design.md` §7. Script: `ab.py`.
Artifact: `ab.json` (both arms' full records, including arm B's three per-rejection
core rows). **Every measured figure in this file is read from `ab.json`**, which
was re-read after the process exited rather than transcribed from the log that was
watched while it ran; figures cited from elsewhere are attributed inline, and
figures obtained by arithmetic on the artifact show that arithmetic where they
appear. **Run metadata — date, commit, exit status — is this README's own record
and is not in the artifact**, because `ab.py` writes neither a timestamp nor a
commit into the JSON; a successor script should record both there.

```
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -u \
    ../docs/superpowers/evidence/2026-09-27-core-in-loop/ab.py \
    ../docs/superpowers/evidence/2026-09-27-core-in-loop/ab.json
```

Run 2026-09-28 on `61d4119`, launched in the background, exit 0 — date, commit and
exit status recorded here rather than in the artifact (above). The wall clock **is**
re-derivable from `ab.json`: the two arm records sum to 1,052.0 + 954.9 =
**2,006.9 s (33 m 27 s)**. Both arms completed; the JSON carries two arm records
and neither is partial.

**`cores.CoreExtractionError` was not raised in either arm** —
`core_extraction_error` is `null` on both records. That matters because `_core`
checks its own precondition (`holds(frozenset(candidates))`) and its own
postcondition (`holds(core)`) and raises rather than returning a silent no-op or
an unsound core, and the class deliberately escapes `compile_tree`'s catches so
it can never be mistaken for an ordinary refusal. Its absence is the evidence
that arm B's clauses are the cores they claim to be.

---

## Verdict: §7.2 row 3 — UNRESOLVED AT THIS BUDGET. §7.3's guard PASSED.

**The mechanism works. Convergence is not settled, in either direction.**

The clause narrowed **25.2x** — median **202 → 8 solver variables**, arm A's
113-row median against arm B's 3-row one. The exact ratio is 202 / 8 = **25.25**;
**25.2x** is that truncated rather than rounded (half-up would give 25.3), stated
once here and used in that form throughout the file, so every appearance of it
understates the measured tightening slightly. The terminal outcome
**did not change**: arm B still ends on
`AssignFail(kind='budget', site=500000)`, the same exhausted node budget as arm A
and as the committed baseline. It did not reach `emit` (row 1) and it did not
become a decision such as `layer_unsat` (row 2).

**§7.3's guard passed, so a row may be claimed.** Arm B's median clause is **8
solver variables**, below the single-digit bar the spec fixed before any data
existed, and it passed on **each of the three rejections individually** —
clause-size multiset {5, 8, 8} — rather than only on their median. This run
therefore measures a fact about
convergence rather than a broken extraction — the distinction §7.3 exists to
enforce.

Three rows are three rows, but single-digit cores are **not** an n=3 artefact of
this run: the prior core measurement put `core_variables <= 10` on **31 of 31**
rows with an observed maximum of 8 over the whole run
(`../2026-09-27-nogood-core/README.md`). That is an independent population behind
the guard's premise, measured before this loop existed. It does not widen this
run's clause *statistics* beyond three rows — see "What this does NOT establish".

**No unsat claim is made and none is available.** The outcome is a timeout, not a
decision, so this file says nothing about whether a stackable dense labelling of
this crease set exists.

## The two arms

One boolean apart. Both at `assign_budget=500,000`, both on dense `lizard`, both
in the same session on the same machine.

| reading | **arm A** (extraction OFF) | **arm B** (extraction ON) |
|---|---|---|
| `stage_reached` | `assign` | `assign` |
| `failure` | `AssignFail(kind='budget', site=500000)` | `AssignFail(kind='budget', site=500000)` |
| `verdict` | `None` | `None` |
| budget exhausted | True | True |
| `layers_tried` | 113 | **3** |
| rejections | 113 | **3** |
| clause size, solver variables — min / **median** / max | 6 / **202** / 259 | 5 / **8** / 8 |
| wall clock | 1,052.0 s | **954.9 s** |
| nodes per rejection | 4,424.8 | 166,666.7 |
| `CoreExtractionError` | none | none |

`layers_tried` equals the rejection count in both arms, which is what a run that
never accepts a candidate looks like: every `_check` call was a rejection and
there was no accepting call to add.

**Seconds are reported as the experiment's cost, and nothing in this file is
inferred from the arms' ratio.** Arm B is the shorter arm — 954.9 s against
1,052.0 s, 0.91x, a 97.1 s difference — but a cross-arm wall-clock comparison is
confounded by construction. `ab.py`'s own docstring says so ("any wall-clock
comparison between the arms is confounded. Compare outcomes; report seconds as the
experiment's cost"), and spec §7.3 closes with the same reporting rule.

The confound is measurable here rather than merely asserted, because the arms
differ by 110 layer checks as well as by extraction, and the checks are the larger
term. Using 1.577 s per candidate layer check — measured on this exact
configuration in `../2026-09-26-nogood-indexing/wtg-lizard-500k.json`, and
cross-checked there as `global_check_secs` 178.15 / 113 rejections = 1.577 s:

    110 skipped layer checks x 1.577 s            = 173.5 s saved
    extraction                                    = +21.7 s
    predicted arm B = 1,052.0 - 173.5 + 21.7      =  900.2 s
    observed arm B                                =  954.9 s
    => arm B is 54.7 s DEARER than skipped checks alone predict.

The skipped-check term is **8.0x** extraction's cost (173.5 / 21.7) and runs in the
opposite direction. So the 97.1 s is bought by checks arm B never had to run, and
**none of it is attributable to extraction** — the arm is not "cheaper because of"
anything. The load-bearing cost figure in this file is instead extraction's **2.27%
share of arm B's own wall clock**, a within-arm reading that needs no cross-arm
comparison at all; §"Cost is not the binding constraint" below rests on that.

## Arm A against the committed baseline

Arm A exists to reproduce `../2026-09-24-dense-pleats/nogood-lizard.json` on this
machine in this session, so the comparison is not against a quoted figure.

| reading | committed baseline | **arm A, this run** | reproduced? |
|---|---|---|---|
| rejections | 113 | **113** | **yes, exactly** |
| outcome | `AssignFail(kind='budget', site=500000)` | same | **yes** |
| clause variables, min | 6 | **6** | **yes** |
| clause variables, **median** | 202 | **202** | **yes** |
| clause variables, max | 259 | **259** | **yes** |
| nodes per rejection | 4,424.8 | **4,424.8** | **yes** |
| wall clock | 834.0 s | **1,052.0 s** | **no — 1.26x** |

**Every structural reading reproduced exactly. Wall clock did not, and the
discrepancy is reported as a finding rather than as noise.** Arm A ran 26%
slower than the committed figure for a run that did identically the same work —
same 113 rejections, same clause size distribution to all three quantiles, same
outcome. Nothing about the search differed, so the 1.26x is a property of this
machine or this session, not of the compile.

The consequence is a reporting rule for the rest of this file: **wall-clock
comparisons against the committed 834.0 s and 8,865.1 s figures must be scaled by
~1.26x** (1,052.0 / 834.0 = 1.26), because those were measured on a session whose
speed this one does not match. Running both arms back to back in one process
removes *that* confound from the arm A vs arm B comparison — but it does not make
that comparison sound, because the arms also differ by 110 layer checks, as "The
two arms" above accounts for. **No conclusion in this file rests on the arm A vs
arm B seconds ratio.**

## The extraction reading

Three rejections, three core rows, read from `ab.json`'s `core_rows`. Crease
counts are **FOLD edges** (`len(witness.creases)` and `len(core)`) — the same unit
as `../2026-09-27-nogood-core/README.md`, and *not* the `piece_keys` unit-crease
count that `../2026-09-24-dense-pleats/README.md` calls a crease. The two differ
by an order of magnitude and must not be compared.

| rejection | cone, FOLD edges | **core, FOLD edges** | oracle calls | Junker bound `2k·log2(n/k)+2k` | secs |
|---|---|---|---|---|---|
| 1 | 44 | **8** | 31 | 55.4 | 5.069 |
| 2 | 361 | **5** | 47 | 71.7 | 9.789 |
| 3 | 65 | **8** | 43 | 64.4 | 6.847 |
| **median** | **65** | **8** | **43** | — | **6.847** |

**Oracle calls is the portable figure** — median **43**, total **121** over the
three rejections. It does not depend on any subject's propagation speed, which is
why it and not seconds is the number to carry into any follow-on. All three rows sit
inside Junker's QuickXplain call bound. The prior measurement reported only its
depth **median 35** and **max 57** against that bound and ran no per-row check
(`../2026-09-27-nogood-core/README.md`), so there is no earlier per-row result for
these three to match; this is the first one. (Its 31-of-31 figure is a different
column — the `core_variables <= 10` band, cited under the guard above — and is not
a Junker-bound result.)

**Seconds are `lizard`-specific and must not be generalised.** Extraction cost a
median **6.847 s** per rejection and **21.7 s** in total. `lizard`'s `propagate`
is ~100x slower than the other five subjects'
(`../2026-09-24-dense-pleats/README.md`: 1.070 s against 0.004–0.014 s), and
`../2026-09-27-nogood-core/README.md` measured that the per-*call* ordering
actually reverses — a subset-seeded call that finds no contradiction has no early
exit and must propagate to fixpoint, which on `bird` is 466,682 face pairs. So no
seconds figure here predicts another subject's cost in either direction.

**Cone → core, median 65 → 8 FOLD edges**, an 8.1x cut on the median and 72.2x on
the largest cone in the run (361 → 5). Core size is again flat where cone size is
not — cones of 44, 361 and 65 yielded cores of 8, 5 and 8 — which is the
signature the prior measurement predicted for a dependency cone rather than a
cut.

Two consistency checks that fell out of the data:

* **Rejection 1 reproduces the prior breadth row for `lizard` exactly** on both
  sizes: 44 FOLD edges blamed, an 8-edge core
  (`../2026-09-27-nogood-core/README.md`, Breadth table). Its oracle count reads
  **31 here against 29 there**, a difference of exactly **+2**, which is the two
  pre/postcondition guard calls that commit `7c32008` brought inside the counting
  wrapper so that `counter` means calls *made*. The figures agree once the unit
  does.
* **At core scale the FOLD-edge and solver-variable counts form the same
  multiset.** The core
  edge counts are {8, 5, 8} and arm B's clause-variable multiset is {5, 8, 8} —
  the same multiset. Multiset equality is all that is claimed: `ab.json` records
  the clause sizes only as min/median/max, so the per-row pairing of an edge count
  to a variable count is not recoverable and no row-by-row coincidence is asserted.
  The units are genuinely different (one is
  `len(core)`, the other `assign`'s own `var_of` over `piece_keys`), so this is an
  observation about core scale and not an identity; the prior measurement
  predicted it, reading a median 6 edges against 5 variables at core scale while
  the two separate by 1.58x at cone scale.

## Why the rejection count is not the criterion

Arm A refused **113** candidates and arm B **3**, a 37.7x drop, at 4,424.8 and
166,666.7 nodes per rejection respectively — a 37.7x rise. **Those are one figure,
not two independent readings.** Both arms exhausted the same 500,000-node budget,
so nodes per rejection is `500,000 / rejections` *identically*; the rise is the
reciprocal of the drop by construction and carries no information the drop does
not. Quoting both is arithmetic, not corroboration.

Nor does the drop discriminate on its own. Fewer distinct complete candidates
before exhaustion is the **expected** signature of stronger clauses — a clause
forbidding one point in a 2^8 space excludes vastly more of the search space a
priori than one forbidding a point in 2^202 — but it is **equally consistent with
a search wandering deeper without getting closer to a decision**: each clause now
forbids a far larger region, which can make *completing* any candidate at all
correspondingly harder. Both arms ended on the same budget with the same failure
kind, so **this run cannot distinguish those two readings** and no argument in
this file is built on their ratio. Its only further use is the illustration of
scale under "Sizing the 5,000,000-node run" below, which is labelled there as an
illustration and not as a reason.

## Cost is not the binding constraint — so §9.1's bounded variant is NOT indicated

Spec §9.1 designates a bounded extraction variant (Fleury & Biere, SAT 2021) as
the follow-on **if and only if** the A/B shows cost rather than pruning strength
to be the binding constraint. It does not.

* Extraction is **21.7 s of arm B's 954.9 s: 2.27%**. That is a within-arm share,
  which is why this section rests on it and not on any cross-arm ratio (see "The
  two arms": the arms' seconds are confounded). Capping it could recover at most
  that 2.27%.
* Both arms consumed 500,000 nodes — **inferred, not recorded; see the limitation
  below** — while their rejection counts differ **37.7x** (113 against 3). Per node,
  with layer checking excluded from **both** arms so the two sides are the same
  quantity, the cost is **1.748 ms in arm A** ((1,052.0 − 113 × 1.577) / 500,000)
  against **1.857 ms in arm B** ((954.9 − 21.7 − 3 × 1.577) / 500,000). Arm B is
  **6.3% more** expensive per node, not less. **Wall clock here tracks the node
  budget, not the rejection count**: a 37.7x difference in rejections moves the
  per-node cost by 6.3%, and it moves it *against* arm B.
* The 1.577 s layer cost is borrowed from a different session, so the per-node pair
  above carries this file's scaling caveat. That session did the same
  113-rejection work in 930.19 s against arm A's 1,052.0 s — **1.13x** slower here
  — and scaling the layer cost by that factor (1.784 s) gives **1.701 ms in arm A
  against 1.856 ms in arm B, 9.1% more**. The sign does not change and the margin
  widens, so the reading is robust to the borrowing in either direction.

The 1.577 s and the apportionment it comes out of are a measurement on this exact
configuration. `../2026-09-26-nogood-indexing/wtg-lizard-500k.json` instruments
dense `lizard` at the same 500,000-node budget with the same 113 rejections and
apportions its 930.19 s as **79.57% the local CSP search itself** (740.16 s),
19.15% the per-candidate layer check (178.15 s) and **1.28% the no-good scan**
(11.88 s). The clause machinery was already a ~1% line item there, and extraction
makes it a ~2% one here.

Applying that file's measured 1.577 s per-candidate layer cost to arm B's three
candidates — **an estimate combining this run's counts with a figure measured
elsewhere, not a measurement of arm B** — puts arm B's layer checking at about
4.7 s. With extraction's 21.7 s that accounts for roughly 26 s of 954.9 s, leaving
~97% of arm B in the local CSP search.

So the binding constraint is not the price of a clause. It is that under the
narrowed clauses the DFS travels 166,666.7 nodes between complete candidates and
still reaches no decision inside the budget. **A bounded variant would cap a
2.27% line item and is therefore not indicated by this measurement** — which is
exactly the "knob with no measurement behind it" that §2 refused to add
pre-emptively, and the refusal is now vindicated by the number rather than by the
argument.

## Sizing the 5,000,000-node run (not started — spec §11)

Two estimates, one assuming linearity in the budget and one from the lineage's
measured elapsed scaling:

* **Linear in budget:** arm B's 954.9 s × 10 = 9,549 s = **2.65 h** (`ab.py`
  printed this to one decimal, as 2.7 h).
* **From the arm-A lineage's measured elapsed scaling:** 10x the nodes took
  834.0 → 8,865.1 s, **10.63x**, in `../2026-09-24-dense-pleats/README.md`.
  Applied to arm B's 954.9 s that is **2.82 h**.

So **2.65–2.82 h**, and the two agree closely enough that the choice between them
changes nothing.

What it would buy is the discouraging part, and the reason is the measurement in
hand rather than any projection forward. Extraction is 2.27% of the arm, so a 10x
budget buys 10x the nodes and essentially nothing else. The binding constraint this
run measured is that under the narrowed clauses the DFS travels **166,666.7 nodes
between complete candidates and still reaches no decision**, and nothing in either
arm predicts that more nodes changes that: both ended on the same failure kind at
the same site, so the run records no gradient towards a decision. **The run stays
out of scope (§11); this file sizes it and does not recommend it** — which is
deliberately weaker than recommending against it. A 5,000,000-node run may be worth
spending for reasons outside this measurement; this measurement simply does not
argue for it.

*An illustration of scale, not a reason.* `../2026-09-24-dense-pleats/README.md`
measured candidates ∝ budget^**0.71** on the arm-A lineage (113 → 584 for 10x the
nodes), and carrying that exponent to arm B turns 3 rejections into about **15**.
That number indicates a scale and nothing more. It **cannot be offered as grounds
for expecting the 5M run to exhaust its budget**, because the exponent was fitted
on two budget-exhausted runs, so applying it already assumes the exhaustion it
would be predicting — the declination above therefore does not rest on it. It is
also an extrapolation across arms (fitted on arm A's rejection rate, not arm B's)
and, more seriously, across search-tree *shape*, which is exactly what that
exponent describes and exactly what this file says elsewhere may differ between
the arms — see "Why the rejection count is not the criterion" and the follow-on
below. Nor would a larger clause sample be the 5M run's deliverable: per §7.2 row 3
what such a run has to produce is a **terminal outcome**.

The more informative follow-on that this measurement points at is not more nodes
but an answer to the question the run could not distinguish: whether the DFS under
narrowed clauses is approaching a decision or merely traversing a differently
shaped space. That needs an instrument this run does not have — for instance
whether arm B's three contradictions repeat, which `ab.json` does not record
because the witness identity is not in `debug_cores`.

## What this does NOT establish

* **It is not evidence that dense box-pleating converges.** Arm B did not reach
  `emit`. The only thing that changed is the clause.
* **It is not evidence that dense box-pleating is infeasible, for this crease set
  or any other.** The outcome is an exhausted node budget, not a decision. Both
  arms are silent on satisfiability.
* **It is about `lizard`.** 26 of the 31 rows behind the core measurement were
  `lizard`, and the subjects that would test generality cannot produce a dense
  labelling at all: `octopus` and `dog` do not finish dense labelling inside a
  300 s cap. Of the five other labelling-capable subjects, four (`frog`, `horse`,
  `bird`, `guinea_pig`) produce a first dense candidate whose blamed set is only 2
  creases — no cone to cut — and the fifth, `starfish`, arrives with 6 and shrinks
  to 5, so none of them can exercise the mechanism at the scale `lizard` does.
  Nothing here generalises to the corpus.
* **Arm B's clause statistics rest on three rows.** The guard passed on each of
  them, which is stronger than passing on a median of three, but n=3 is n=3. The
  25.2x tightening is a comparison of a 3-row median against a 113-row one.
* **Node counts were not recorded, only inferred — a gap against spec §7.1.**
  `ab.json` carries no node count for either arm. That both arms consumed exactly
  500,000 nodes is an inference from the recorded
  `AssignFail(kind='budget', site=500000)`: `assign.py:960` sets `nodes = budget`,
  and `:1009-1011` decrement it once per iteration and return that failure the
  moment `nodes < 0`, so a `kind='budget'` failure means the budget was run out
  exactly — identically in both arms, since both were given 500,000. The inference
  is sound, but it is an inference and it is flagged as one where this file uses it
  (§"Cost is not the binding constraint"). **Spec §7.1 requires both arms to record "nodes" and §7.3 says to "Compare
  nodes and outcomes"; this run's instrumentation does not satisfy either**, and
  closing the gap needed a change to `assign.py`, which was out of scope for this
  slice. A successor should return the consumed node count alongside the failure so
  the comparison is read rather than derived.
* **The cores are irreducible, not minimum.** Every element is necessary and a
  smaller core may exist; a minimum core is NP-hard and was not attempted
  (spec §5). So 8 variables is an upper bound on the true minimum, which
  strengthens the tightening's direction rather than weakening it.
* **Which irreducible core is found is not canonical.** It depends on
  QuickXplain's split order, which is why `shrink` feeds it `sorted(creases)`.
  Reproducibility of *this* core is claimed; uniqueness is not.

## Where this leaves the line of work

This is the fifth lever in the CEGAR-cost line of work and the first whose
*mechanism* measured positive end to end: the clause really does narrow 25.2x
inside the live loop — **a 3-row median against a 113-row one; n=3** — at 2.27% of
the arm's wall clock, with no soundness refusal.
The four before it are closed or degenerate (budget scaling, the F.1.1 pleat
filter, no-good indexing, F.3 ridge assignment).

It is also the fifth lever that did not move the terminal outcome. Recording that
honestly is the point: a 25.2x stronger clause (again, three arm-B rejections
against arm A's 113), delivered at negligible cost and with its soundness checked
per rejection, was **not** enough to make dense layer-ordering on `lizard` reach a
decision inside 500,000 nodes.

Nothing in this slice is enabled by default and nothing reaches the serve path:
`core_extraction` defaults to `False`, and `grep -c box_pleat
mcp_harness/server.py` is still 0.
