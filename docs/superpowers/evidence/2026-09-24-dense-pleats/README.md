# Dense pleat construction (gap 1): what works, what does not, and why

Spec: `docs/superpowers/specs/2026-09-24-dense-pleats-design.md`
Plan: `docs/superpowers/plans/2026-09-24-dense-pleats.md`

**The short version.** The box-pleat compiler's crease patterns looked like
COrigami's Figure 5 "step 1" — a packing skeleton of ridges and hinges with
almost no pleats. The cause was measured: `contours.py` was already dense, and
one branch of `assign.initial_readings` discarded 94% of it. This work adopts
COrigami's F.2 interleaving so those creases survive.

**Labelling now works on 6 of 8 subjects. Global layer-ordering works on
none.** Both halves are measured below.

---

## 1. What ships

Dense labelling behind `compile_tree(..., dense=False)`, **inert by default**.
Nothing on the serve path changes: `grep -c "box_pleat" mcp_harness/server.py`
is 0, as it was before.

## 2. The byte-identity guarantee (all 8 subjects)

With `dense=False`, the sparse path emits **byte-for-byte identical** folds.
Established by `git archive`-ing the branch base `a7bb00d` into a temp tree
(HEAD never moved, no `checkout`, no `stash`), compiling all 8 subjects from
both sides, and comparing sha256:

| subject | sha256 (both sides) | sparse compile |
|---|---|---|
| `starfish` | `d9941daef6ec28d4…` | 0.1 s |
| `bird` | `cf0b50cfe50b9ef5…` | 3.5 s |
| `lizard` | `3a9206eeb3c5a55f…` | 6.6 s |
| `horse` | `0e9411295dee9c0f…` | 14.4 s |
| `octopus` | `6bb99090370fc2a0…` | 35.3 s |
| `frog` | `09c83d7c92bf39f8…` | 54.0 s |
| `guinea_pig` | `f882f4bd74447289…` | 275.1 s |
| `dog` | `4dbebfe175f61a96…` | 499.1 s |

**Why this file exists rather than relying on the test suite.**
`test_already_consistent_subjects_emit_byte_identical_folds` covers only
`bird` and `starfish` — and those are exactly the two subjects with
`layers_tried == 1`, which accept the first candidate and therefore **never
enter the CEGAR relabelling loop this work modified**. The guard passes where
the change cannot hurt and is silent where it can. The other six are covered
only here.

One trap worth recording: an earlier comparison read IDENTICAL on all 8, but
the `dog` and `guinea_pig` dumps predated the verified base archive. Had they
been produced from HEAD by mistake, "IDENTICAL" would have been vacuous for
precisely the two most expensive subjects — the two nobody would want to
re-run. Both were re-dumped from the verified base and re-compared.

## 3. What works: the labelling

`assign(..., dense=True, global_check=None)` — the first locally feasible
candidate, no layer repair loop.

| subject | N | pieces | sparse M/V | dense M/V | paths (raw) | coloured (final) | rel. odd (final) | rel. conflict (final) | released (final) | flipped | assign s |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `starfish` | 4 | 136 | 84 | 104 | 39 | 12 | 0 | 7 | 7 | 0 | 0.005 |
| `lizard` | 34 | 5140 | 476 | 4868 | 365 | 161 | 2 | 18 | 20 | 0 | 0.796 |
| `horse` | 46 | 9484 | 2232 | 9116 | 809 | 381 | 4 | 17 | 21 | 0 | 5.803 |
| `frog` | 38 | 6432 | 608 | 6128 | 488 | 189 | 3 | 51 | 54 | 1 | 16.881 |
| `guinea_pig` | 64 | 17512 | 1024 | 17000 | 856 | 325 | 3 | 99 | 102 | 1 | 116.273 |
| `bird` | 54 | 12868 | 1980 | 12436 | 963 | 413 | 5 | 62 | 67 | 1 | 200.974 |
| `octopus` | 74 | 23684 | 3180 | **timeout** | 1451 | — | — | — | — | — | >300 (cap) |
| `dog` | 74 | 23868 | 4752 | **timeout** | 1636 | — | — | — | — | — | >300 (cap) |

**Every figure in this table is read from the committed
`dense_labelling.json`** (the run of 2026-09-26 that also produced §4b's cost
curve) — so a future reader knows which run these seconds are. The `assign s`
column is `dense_assign_secs`; `octopus`/`dog` read 300.006 / 300.008 s, i.e.
the 300 s `DENSE_ASSIGN_CAP_SECS` alarm, not a completion.

⚠ **CORRECTED 2026-09-27: the `assign s` column was one run out of date.** It
previously read 0.004 / 0.788 / 5.704 / 22.716 / 108.965 / 177.595 for
`starfish` / `lizard` / `horse` / `frog` / `guinea_pig` / `bird`. Commit
`98e0fed` re-ran `dense_labelling.py` when it added §4b and overwrote those
values in the artifact without updating this table. The largest disagreements
are `bird` (177.595 → 200.974, **+13.2%**) and `frog` (22.716 → 16.881,
**−25.7%**). The corrections run in *both* directions, and that commit touched
no production code ("Evidence only; no production code touched" — it changed
only this README, `dense_labelling.py`/`.json` and a probe script), so the
differences are run-to-run wall-clock variance rather than a change in what
`assign` costs. The qualitative conclusion below is unchanged and, on `bird`,
slightly stronger.

⚠ **CORRECTED 2026-09-27: the column labels mixed two populations.** `paths`
is `pleat_paths_raw`, counted **before** `assign()`'s mirror-merge
reconciliation; `coloured` / `rel. odd` / `rel. conflict` are the `*_final`
fields, counted **after** it. Subtracting them (`bird`: 963 − 413 = 550) does
not give a release count — `released_final` is 67. The two populations are now
labelled, and `released (final)` is shown so the post-merge arithmetic is
visible: `rel. odd + rel. conflict = released (final)` holds exactly on all six
measured rows. The raw→final drop is mirror-merging, not release: `paths (raw)`
divided by `coloured (final) + released (final)` is 2.05 / 2.02 / 2.01 / 2.01 /
2.00 / 2.01 across the six (`guinea_pig` is 856/427 = 2.0047), i.e. a mirrored pair of dense pleat groups shares
one final solver variable, exactly as `dense_labelling.py`'s step 2 docstring
describes.

Crease counts rise 1.2× (`starfish`) to 16.6× (`guinea_pig`). Every emitted
interior vertex satisfies Maekawa, Kawasaki and `cp_audit`'s arrangement
oracle **by construction of `assign`'s local CSP** (`violation()`'s checks at
every vertex) -- `dense_labelling.py` makes no oracle call of its own and
records no such field; this is a property of the CSP the labelling comes
from, not a measurement this script performed.

**Cost does not generalise from the cheap subjects.** `lizard` assigns in
**0.796 s**; `bird` takes **201.0 s** — a 252x spread — and `octopus`/`dog` do
not finish inside a 300 s cap. Any statement of the form "dense labelling takes
under a second" is a statement about `lizard` alone. (Both seconds are
`dense_assign_secs` in the committed `dense_labelling.json`; this sentence
previously read "0.79 s" and "177 s" against an earlier run of that artifact —
see the correction under the table.)

### Crease-degree histograms (interior vertices)

| subject | sparse | dense |
|---|---|---|
| `starfish` | `{0:2, 2:29, 4:12, 6:6}` | `{2:15, 4:28, 6:6}` |
| `lizard` | `{0:4032, 2:449, 4:4, 6:4}` | `{2:4123, 4:360, 6:6}` |
| `horse` | `{0:6214, 2:1925, 4:139, 6:3}` | `{2:7521, 4:747, 6:13}` |
| `frog` | `{0:5044, 2:565, 4:15, 6:1}` | `{2:5150, 4:469, 6:6}` |
| `guinea_pig` | `{0:15132, 2:981, 4:15, 6:1}` | `{2:15318, 4:805, 6:6}` |
| `bird` | `{0:9572, 2:1796, 4:75, 6:5, 8:1}` | `{2:10571, 4:864, 6:13, 8:1}` |

Degree 0 vanishes — every interior vertex now carries creases. Degree 2 is
benign: two same-type creases meeting is a straight fold passing through, which
`pleat_paths` collapses into one variable. The structurally significant jump is
**degree 4**, e.g. `lizard` 4 → 360 and `bird` 75 → 864, because each is a real
Maekawa constraint.

### `flipped_from_f2` is not always 0

It reads 1 on `bird`, `frog` and `guinea_pig` even with `global_check=None`,
where no repair loop runs. Expected 0; measured 1. Cause: `assign`'s DFS can
move a variable off F.2's seed from purely local feasibility and mirror-merge
constraints, before any global check fires. Recorded as measured rather than
forced to match the expectation.

## 4. What does not work: global layer ordering

`compile_tree(dense=True)` reaches stage `assign` and stops. On `lizard`:
`AssignFail(kind='budget', site=500000)` after **834.0 s**, having tried
**113** candidate labellings. Sparse subjects converge in 5–22.

Per-candidate cost is not the problem — measured on dense `lizard`:

| stage | time | scale |
|---|---|---|
| `to_fold` | 0.00 s | 759 edges |
| `flat_fold` | 0.01 s | 380 faces (sparse: 20) |
| `constraints_for` | 3.65 s | 53,754 face pairs |
| `layers.propagate` | 1.00 s | → contradiction (taco-tortilla) |
| `layers.certify` | 0.93 s | → REFUTED |

**These are a DIFFERENT RUN from §4b's, and are left unreconciled on purpose.**
§4b measures the same three stages on the same subject and reads
`constraint_graph` **4.047 s**, `propagate` **1.070 s**, `certify` **0.970 s**
(`dense_labelling.json`, 2026-09-26) against 3.65 / 1.00 / 0.93 here (the
original 2026-09-25 hand-instrumented run). Neither has been edited to match
the other: the gap -- up to ~11% (`constraint_graph` 10.9%, `propagate` 7.0%,
`certify` 4.3%) -- is run-to-run wall-clock variance on the same machine,
and quoting one where the other is meant would be a silent reconciliation. Cite
§4b's figures when you want a number that is regenerable from a committed
artifact; the face and edge counts in this table are identical in both runs.

⚠ **Summing that column to "about 6.4 s per candidate" is WRONG, corrected
2026-09-26.** `constraints_for` is cached and built once (`compile.py:292`);
`certify` runs once after `assign` returns (`compile.py:347`). Neither is
per-candidate. **Measured per-candidate layer cost: 1.577 s** (section 4c).
The point the table was making -- per-candidate cost is not the bottleneck --
survives and strengthens.

### Why: every rejection is new, and each clause prunes too little

Instrumenting production's own rejection path (`nogood_diagnostic.py`, with a
`debug_clause_sizes` hook recording the variable-level clause; committed as
`nogood-lizard.json`, `partial: false`):

| reading | `lizard` |
|---|---|
| rejections | **113** |
| distinct contradictions | **113 of 113** |
| most-repeated contradiction | 1× |
| no-good clause size, **creases** (`len(keys)`, what `piece_keys` returns) | min 39, median **2,069**, max 3,161 |
| no-good clause size, **solver variables** (`len(clause)`, what `assign()` stores) | min 6, median **202**, max 259 |

**The loop is learning, not spinning.** Every one of the 113 rejections is a
*distinct* contradiction; nothing recurs. So the operational picture is that
the space of distinct layer-order contradictions in a dense pattern is very
large, and a clause over ~202 of the solver's variables removes too small a
slice of it to exhaust that space within the budget tried.

**Two units, reported separately on purpose.** The diagnostic's `len(keys)`
counts implicated unit **creases**; production's actual clause is
`{var_of[idx[k]]: value[…] for k in keys …}`, a dict over **solver
variables**, strictly smaller once run-merging, pleat-path grouping and
mirror-merging have collapsed several creases onto one variable. The collapse
is large — median 2,069 creases become median 202 variables. Do not reason
from an exponent over either figure.

### The large-budget run: 10x the budget does not converge (2026-09-26)

The withdrawal below reopened the question the default run could not answer.
This run answers it. `nogood_diagnostic.py lizard ... 18000 5000000 100000` --
**10x the node budget**, rejections effectively unbounded, a 5 h wall-clock cap
set above the expected finish so the NODE budget would be what binds.
Committed as `nogood-lizard-largebudget.json` (`partial: false`).

| reading | 500k (default) | **5M (10x)** |
|---|---|---|
| outcome | `AssignFail(budget, 500000)` | **`AssignFail(budget, 5000000)`** |
| candidates refused | 113 | **584** |
| elapsed | 834.0 s | **8,865.1 s** (2 h 28 m) |
| distinct contradictions | 113 of 113 | **584 of 584** |
| most-repeated contradiction | 1x | **1x** |
| clause size, creases (median) | 2,069 | 2,117 |
| clause size, **variables** (median) | 202 | **204.5** |
| distinct creases named by any clause | -- | **4,817 of 4,868** |
| creases named exactly once | -- | **15** |
| most-frequent crease | -- | **581 of 584 clauses** |

**It ended on the node budget, not the cap** -- the outcome is directly
comparable to the default run rather than being a weaker timeout.

**Three findings, in descending order of how much they should change a plan.**

**1. Budget buys candidates SUBLINEARLY.** 10x the nodes bought 5.17x the
candidates, i.e. candidates ~ budget^**0.71**. Both per-candidate costs roughly
doubled:

| | 500k | 5M | ratio |
|---|---|---|---|
| nodes per candidate | 4,424.8 | 8,561.6 | 1.93x |
| seconds per candidate | 7.38 | 15.18 | 2.06x |

So "raise the budget" is not a route that gets cheaper with scale; it gets more
expensive per unit of progress.

⚠ **CORRECTED 2026-09-27: "roughly another 4x budget" did not follow from the
law two lines above it.** Inverting candidates ∝ budget^0.71: reaching 10x the
ORIGINAL candidate count (113 → 1,130) needs
`500,000 × 10^(1/0.71) = 500,000 × 25.61 = 12.81M` nodes, which is
**12.81M / 5M = 2.56x**, i.e. **roughly another 2.6x** on top of this run — not
4x. (10x the CURRENT count, 584 → 5,840, needs
`500,000 × 51.68^(1/0.71) = 129.5M` nodes = **25.9x** this run; also not 4x.)
The exponent itself is `log(584/113) / log(10) = log(5.168)/log(10) = 0.713`,
rounded to 0.71 above; using 0.713 unrounded gives 2.52x rather than 2.56x, so
the conclusion is insensitive to the rounding. Neither figure changes the
reading — the returns are sublinear either way — but the arithmetic is now
checkable. "4x" was wrong in both directions depending on which target it meant:
too high for 10x the original count (2.6x) and an order of magnitude too low for
10x the current one (25.9x).

**2. The learner does not self-strengthen.** Across 5.17x more experience the
clause size is flat: 202 -> 204.5 variables, 2,069 -> 2,117 creases. Learning
584 clauses teaches the solver nothing about how to state a tighter one. This
is the reading that most directly supports the minimal-unsat-core follow-on
(section 7).

**3. ⚠ WITHDRAWN 2026-09-26 -- see section 4c.** This read the slowdown as
`assign`'s unindexed no-good scan, from a per-node cost that appeared to grow
4.63x against a 5.17x clause growth. Both figures came from apportioning wall
clock with the bogus 6.4 s/candidate constant. Measured directly, the scan is
**1.28%** of total time and per-node cost is **flat**. The real reading is that
**nodes per candidate grew 1.93x** -- a learning search backtracking further as
clauses accumulate, which is correct behaviour, not a defect.

**What this run does and does not settle.** It does **not** restore "no budget
increase can converge this" -- that claim stays withdrawn, and 584 candidates
is not a proof of impossibility any more than 113 was. What it establishes is
that **convergence by budget is economically implausible**: sublinear returns,
a per-candidate cost that doubles as the store grows, and a clause that never
tightens. The gap must be closed by pruning harder or searching less, not by
paying more.

**On the crease-frequency reading, stated carefully.** A set of creases appears
in ~99.5% of all 584 clauses while the union covers essentially every crease.
That is the shape expected when `piece_keys`' dependency set is an
over-approximation that drags propagation hubs into every witness -- which is
evidence that a minimal core would be far smaller than 204 variables, and
therefore evidence the follow-on is worth specifying. It is **not** evidence
about what size core exists: high frequency is not causation, and only the core
extractor itself can separate "in every witness" from "causes every witness".

### An earlier revision of this section was wrong, twice

Recorded because both errors were in the instrument, not the system:

1. It claimed **"38 distinct contradictions of 113, one repeating 15×"** and
   concluded the loop rediscovers what it has already stored. That came from a
   throwaway probe that identified a witness by a **40-character truncated
   slice** of its `repr` (`w[w.find("faces="):w.find("faces=")+40]`), which
   ends mid-string, so distinct contradictions sharing a face triple collided
   into one bucket. The committed diagnostic hashes the full frozen `Witness`
   dataclass and reads **113 distinct of 113**.
2. It argued from "a no-good over 2,069 **variables**" — the wrong unit, as
   above, in the direction that flattered the conclusion.

**Consequence for the claim itself, stated plainly.** The earlier text said
*"no budget increase can converge this"*. That followed from the repetition
reading, which is now refuted. **What is measured is that dense layer-ordering
does not converge within 113 candidates and a 500,000-node budget — not that
it cannot converge.**

⚠ **CORRECTED 2026-09-27: the larger-budget run HAS been performed — by this
same document.** This paragraph used to end "A larger-budget run has not been
performed, and the decision not to perform one was taken while the repetition
reading was still believed. That decision is worth revisiting on this
evidence." It was revisited, and the run is reported two sections above, in
**§4's "The large-budget run: 10x the budget does not converge (2026-09-26)"**:
`lizard` at a **5,000,000-node** budget refused **584 distinct candidates of
584** over **8,865.1 s**, stopping on `AssignFail(kind='budget', site=5000000)`
(`nogood-lizard-largebudget.json`, `partial: false`). It does **not** converge
there either, and the clause does not tighten (median 202 → 204.5 variables).
The withdrawal above is untouched by that: 584 candidates is no more a proof of
impossibility than 113 was, so "no budget increase can converge this" stays
withdrawn; what §4 adds is that convergence by budget is *economically*
implausible, not that it is impossible. The spec was already corrected for this
same defect (`../../specs/2026-09-24-dense-pleats-design.md` §6.3.1, "The run
the withdrawal above called for has now been performed"); this was the last
file still denying it.

### This raises a doubt about the shipped pleat-reassignment feature

Not a finding — see §6. That feature (spec `2026-09-22`) measured its own
no-good clause at 125 of 249 **variables**, a comparable fraction to the 202
here, and it converges only because sparse subjects need 5–22 candidates, so a
weak learner is never stressed. Whether it degrades the same way at a larger
crease set is **untested**.

## 4b. The per-subject cost curve (2026-09-26)

Spec section 10 asked for `faces`, `face pairs`, verdict and certify seconds per
subject; section 11 risk 2 instructed "measure face count and `flat_fold` time
per subject and report them, not assume the pipeline reaches certification";
section 7 required an unaffordable verdict be "recorded as UNDECIDED with its
budget ... silence is not". **The original wave delivered none of these per
subject** -- faces and pairs existed for `lizard` alone, inside the stage table
above. Closed here by `dense_labelling.py`'s `cost_curve`, which runs the SAME
call sequence `compile.compile_tree` runs after `assign` returns.

Measured on the first locally-feasible dense candidate (`global_check=None`), so
no CEGAR loop is involved:

| subject | N | dense M/V | faces | face pairs | pairs/faces² | `constraint_graph` | `propagate` | `certify` | verdict | free | audit violations |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `starfish` | 4 | 104 | 56 | 1,300 | 0.41 | 0.11 s | 0.004 s | 0.004 s | REFUTED | 0 | 0 |
| `lizard` | 34 | 4,868 | 380 | 53,754 | 0.37 | 4.05 s | **1.070 s** | 0.970 s | REFUTED | 0 | 0 |
| `frog` | 38 | 6,128 | 504 | 116,196 | 0.46 | 7.11 s | 0.006 s | 0.005 s | REFUTED | 0 | 0 |
| `horse` | 46 | 9,116 | 836 | 318,102 | 0.46 | 17.59 s | 0.012 s | 0.010 s | REFUTED | 0 | 0 |
| `bird` | 54 | 12,436 | 988 | 466,682 | 0.48 | 24.38 s | 0.006 s | 0.005 s | REFUTED | 0 | 0 |
| `guinea_pig` | 64 | 17,000 | 872 | 351,500 | 0.46 | 21.07 s | 0.014 s | 0.012 s | REFUTED | 0 | 0 |
| `octopus` | 74 | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- |
| `dog` | 74 | -- | -- | -- | -- | -- | -- | -- | -- | -- | -- |

`octopus` and `dog` produce **no candidate at all** within the 300 s labelling
cap, so they have no faces to measure. Their wall is in `assign`'s local CSP,
UPSTREAM of everything the layer stage does -- no amount of layer-side work
reaches them. Recorded as a limit of this table, not as a gap to be filled by a
bigger layer budget.

**Four findings.**

**1. Spec section 11 risk 5 was BACKWARDS.** It predicted "certification cost
grows in face PAIRS" and that dense subjects "may be orders of magnitude worse"
than `dog`'s sparse 537 s. Measured: `verdict_free` is **0 on all six**, so
propagation forces every pair and `certify` has nothing to search -- it returns
in **4 to 12 milliseconds on five of six subjects; `lizard` reads 0.970 s** --
see finding 3, which is the same `lizard` outlier. (`certify_secs` from
`dense_labelling.json`: `starfish` 0.004, `frog` 0.005, `bird` 0.005, `horse`
0.010, `guinea_pig` 0.012, `lizard` **0.970**. This sentence previously said
"4 to 12 milliseconds" with no exception, which was false for the one subject
every headline in this document is measured on -- and 0.970 s is 81x the
largest of the other five, so it is not a rounding matter. Corrected
2026-09-27.) What grows in pairs is the **one-time**
`constraint_graph` build (0.11 s to 24.4 s). The certification search does not
grow because it never happens.

**2. Face pairs are a tight quadratic in faces.** The ratio holds at 0.37-0.48
across a 17x range of faces, and `constraint_graph` time tracks pairs nearly
linearly (~52 us per 1,000 pairs). This is the growth law section 10 wanted.

**3. `lizard` is the LEAST representative subject in the corpus on
`propagate`** -- 1.070 s to first contradiction against 0.004-0.014 s for the
other five, despite `bird` carrying 9x its face pairs. `propagate` exits on the
first contradiction, so it measures time-to-first-contradiction, not full
propagation. **Every headline number in this work is measured on `lizard`**,
which makes this worth stating plainly rather than burying: on this axis
`lizard` is an outlier by two orders of magnitude.

**4. Dense crease count does NOT predict face count.** `guinea_pig` is the
densest subject by creases (17,000) and only the **third** largest by face pairs
(351,500, below `bird`'s 466,682 from 12,436 creases). `N` does not order them
either -- `bird` at N=54 tops the pair count above `guinea_pig` at N=64. The CSP
searches over creases; the layer stage costs pairs; the two order the corpus
differently, so "the biggest subject" depends on which half of the pipeline is
meant.

**Local validity is now MEASURED, not argued.** Section 3 above stated it "by
construction of `assign`'s local CSP" and noted `dense_labelling.py` made no
oracle call. It does now: `cp_audit.audit_fold` reports **zero** Maekawa, zero
Kawasaki, zero arrangement violations and zero infeasible vertices on all six.

## 4c. Where dense `assign` actually spends its time (2026-09-26)

Measured, not fitted. `../2026-09-26-nogood-indexing/where_the_time_goes.py`
patches production's own `hits_nogood` in memory (asserting the diff touches
only that function's body, so it cannot measure stale or forked code) and times
dense `lizard` at the default 500,000-node budget. Artifact:
`../2026-09-26-nogood-indexing/wtg-lizard-500k.json`.

| component | seconds | share |
|---|---|---|
| `hits_nogood` (the no-good scan) | 11.88 | **1.28%** |
| `global_check` (the layer filter) | 178.15 | 19.15% |
| **remainder -- the local CSP search itself** | **740.16** | **79.57%** |
| total | 930.19 | 100% |

`hits_nogood` ran 500,831 times -- once per search node -- at 23.7 us each.
1.28% is an **upper** bound: the timer's own `perf_counter` pair is counted
inside it.

**Per-candidate layer cost: 1.577 s**, replacing the 6.4 s figure section 4
above now corrects.

**Why this section exists: it refuted a spec.** An earlier revision of section 4
apportioned wall clock between "layer check" and "search" using the 6.4 s
constant and concluded the unindexed no-good scan was the dominant, compounding
cost. A design spec was written and approved on that basis
(`../../specs/2026-09-26-nogood-indexing-design.md`) and is **WITHDRAWN
unimplemented**. Three errors, all favouring the conclusion:

1. 6.4 s/candidate summed two one-time costs into a per-candidate figure.
2. The fitted model used 1.7 us per clause per call; measured ~0.21 us.
3. It read a 4.63x per-node growth. **Per-node cost is flat** -- 1,668 us/node
   at 500k, 1,773 us/node at 5M (1.06x). Nodes/candidate grew 1.93x, secs/
   candidate 2.06x; their ratio is 1.07x, so the slowdown is **more nodes, not
   slower nodes.**

**The real picture, and what it means for the levers.** As clauses accumulate,
the search backtracks further and re-descends more, spending more nodes per
candidate. That is a learning search working, not a defect, and no index removes
it. The dominant cost is the **local CSP search at 79.57%**, which makes
**COrigami F.3 deterministic ridge assignment** -- it removes ridges from the
CSP -- the best-supported remaining lever, on measurement rather than inference.
Minimal unsat cores remain second, attacking the candidate count.

⚠ **THAT RANKING IS SUPERSEDED, 2026-09-27 -- the two levers have swapped
places, and both follow-ons have now been measured.**
`../2026-09-27-f3-rules/README.md` measured F.3's own rules and found it
*"viable but thin"*, concluding minimal unsat cores are the better-supported
lever; `../2026-09-27-nogood-core/README.md` then measured cores as a
**positive** result -- median cause **5 solver variables** where the pre-core
clause states **109** (its own 25-rejection `lizard` depth sample), with
`core_variables <= 10` on **31 of 31** rows and an observed maximum of 8. The
79.57% local-CSP reading above is unaffected and is still the correct
apportionment; what is withdrawn is only the inference *from* it that F.3
therefore ranks first. Read both follow-ons before picking a lever.

**Caveat on the subject.** This is `lizard`, whose `propagate` is ~100x slower
than the other five (section 4b, finding 3). That inflates `global_check`'s
19.15% and deflates the other two shares, so on a typical subject the local CSP
search is likely an even LARGER fraction than 79.57% -- which strengthens rather
than weakens the conclusion.

## 5. Three adjacency definitions, two refuted

F.2 assigns alternating M/V to adjacent pleat paths. That is a 2-colouring, so
it succeeds iff the path-adjacency graph is bipartite — which made "what counts
as adjacent" load-bearing. Both rejected definitions are recorded so they are
not re-proposed.

1. **Proximity** — within 1 unit orthogonally, no parallelism test. Measured
   `starfish`, `horse`, `octopus` non-bipartite with an odd cycle of length
   **exactly 3** every time: a perpendicular path crowding two parallel pleats
   closes a triangle. See `bipartite-proximity-PARTIAL.json` (a 6-of-8 run).
2. **Facing at exactly 1 unit** — parallel and aligned, distance fixed at 1.
   Produced an **empty** graph (`bird`: edges 0, isolated 76). That is a
   *vacuous* bipartite pass and the worst of the three: an edgeless graph is
   trivially 2-colourable, and F.2 over it colours every path M, which is no
   interleaving at all. Measured offsets show why — `bird`'s mode is 2 with
   **zero** pairs at offset 1; `horse`'s mode is 6 with **zero** at offset 2.
   No constant fits.
3. **Nearest parallel neighbour along a lane, no fixed distance** — shipped.

Strict alternation still fails, on dense, fully connected graphs with odd
cycles of length 5 — which is precisely why COrigami calls trap-and-release
"a critical innovation". A released path returns to the solver's pool rather
than being forced to an arbitrary colour.

## 6. What this does NOT establish

- **The conflict count is "conflicts among coloured-only merges."** A *mixed*
  variable (a released member plus coloured members) takes the released path,
  so a disagreement among its coloured members is not recorded in
  `conflict_vars`. Measured at **0 such cases** on `lizard`, `bird` and
  `horse`; the classification is correct regardless, only the label would be
  incomplete.
- **Greedy release is not a minimum odd-cycle transversal**, so release counts
  are an upper bound on how much of F.2 had to be given up.
- **No dense fold was ever emitted.** Nothing here measures the layer
  pipeline's cost at dense scale beyond the per-candidate figures in §4, and
  no dense crease pattern exists to look at.
- **The `lizard` mechanism (large, recurring no-good clauses) has only ONE
  corroborating data point, and the second attempt DISAGREES with it rather
  than failing to materialise.** `bird` was abandoned by hand after 27 minutes
  with no artifact — genuinely no second reading. `horse`, however,
  **completed** and is committed as `nogood-horse.json`: 1 rejection over
  1249.0s, clause size (creases) min/median/max **2/2/2** — three orders of
  magnitude below `lizard`'s median of 2,069 — with `outcome.kind ==
  "assign_returned"` (`AssignFail(kind='budget', site=500000)`), not a
  time-cap abort. `horse` therefore does **not** corroborate `lizard`'s
  mechanism; it shows a *different* dense failure mode: `assign()`'s own
  local-CSP node budget (500,000) exhausted almost entirely on internal
  backtracking, with the global layer-order check (`global_check`) reached
  only once in the whole run. Neither subject makes the case that this is a
  general property of dense trees rather than a `lizard`-specific one — the
  corpus now has two dense-failure readings and they point at two different
  causes.
  An earlier revision of this bullet said neither `bird` nor `horse`
  "reached even its first rejection" and that their wall-clock caps "never
  fired... because those caps are checked inside the rejection path" — both
  wrong for `horse`, which reached one rejection and produced the artifact
  above. The correct reason a cap can fail to fire is that
  `nogood_diagnostic.py`'s `spy` checks its deadline on entry to **every**
  candidate `global_check` is called on, not only inside the rejection path —
  so on `horse`, where the spy ran only once in 1249s, there was only one
  opportunity for that check to trigger, and it had not yet expired at that
  single call.
- **`octopus` and `dog` have no dense labelling at all** — they exceed the
  300 s cap, so every dense figure above excludes them.
- **"This bounds the already-shipped pleat-reassignment feature" is an
  inference, not a finding, and this section previously stated it as the
  latter.** That feature (spec `2026-09-22`) measured its own no-good clause
  size at 125 of 249 *variables*; this work's `lizard` reading is over
  *creases* until the §4 rerun's variable-level figure (now measured, see
  §4). Nothing here tested the shipped feature itself at a larger crease set
  — the comparison is between two different units on two different features,
  not a measurement of the shipped feature's own scaling. It **raises a
  doubt about** whether that feature's sparse-corpus convergence would hold
  at dense scale, not a proof that it would fail. Anyone extending that
  feature to larger crease sets should read §4 and treat this as an open
  question, not a settled bound.

## 7. The follow-on

A **minimal unsat core** for the no-good clause, in place of the whole
dependency set. Shrinking a 202-variable clause toward tens of
variables is the root-cause fix and would likely speed the shipped sparse
feature too. It needs its own spec: minimal cores are themselves expensive to
compute, so this is a research question, not a refactor.

**➜ DONE, 2026-09-27: this has been measured — see
`../2026-09-27-nogood-core/` (spec `../../specs/2026-09-27-nogood-core-design.md`,
artifact `core-sizes.json`, 31 rows).** The cause is far smaller than "tens of
variables": **median core 5 solver variables** against a pre-core median of 109
on its 25-rejection `lizard` depth sample (a 21.8x tightening), with
`core_variables <= 10` on **31 of 31** rows and maximum 8. Its pre-core median
of 109 is **not** the 202 quoted above and must not be swapped for it: 202 is
the median over all 113 rejections of the default-budget run
(`nogood-lizard.json`), while 109 is the median over the 25 `lizard` rejections
that run sampled. Same subject, same quantity, different sample of rejections.

Two cautions carry over from that document rather than being restated here: the
109 → 5 *magnitude* is single-subject (26 of its 31 rows are `lizard`) and does
not generalise, and
the pooled blamed-variable median across all 31 rows is 64, not 109. The `<=10`
band verdict is 31/31 and does not depend on the population. Extraction is still
**not** wired into the CEGAR loop — that is its own gated follow-on.

## 8. Regenerate

All commands run from `mcp_harness/`, using `../.venv/bin/python3` (the system
`python3` lacks `skeletor`):

```bash
# byte-identity, both sides (HEAD never moves)
mkdir -p /tmp/bp-base && git archive a7bb00d | tar -x -C /tmp/bp-base
(cd /tmp/bp-base/mcp_harness && PYTHONPATH=. <worktree>/.venv/bin/python3 -u \
   <worktree>/docs/superpowers/evidence/2026-09-24-dense-pleats/dump_folds.py /tmp/bp-old)
PYTHONPATH=. ../.venv/bin/python3 -u ../docs/superpowers/evidence/2026-09-24-dense-pleats/dump_folds.py /tmp/bp-new

# the labelling measurements AND the per-subject cost curve (section 4b).
# Third argument is the per-STAGE wall-clock cap for the downstream stages
# (to_fold/flat_fold/constraint_graph/propagate/certify/audit), separate from
# the dense-assign cap because those stages grow in FACE PAIRS.
#   ... dense_labelling.py <out.json> [dense_assign_cap] [stage_cap]
# RESUMABLE: a row is re-measured unless it carries cost_curve_done.
PYTHONPATH=. ../.venv/bin/python3 -u ../docs/superpowers/evidence/2026-09-24-dense-pleats/dense_labelling.py \
   ../docs/superpowers/evidence/2026-09-24-dense-pleats/dense_labelling.json

# the large-budget run (subject, output, cap, assign_budget, layer_checks)
PYTHONPATH=. ../.venv/bin/python3 -u \
    ../docs/superpowers/evidence/2026-09-24-dense-pleats/nogood_diagnostic.py \
    lizard ../docs/superpowers/evidence/2026-09-24-dense-pleats/nogood-lizard-largebudget.json \
    18000 5000000 100000

# the no-good diagnostic (subject, output, wall-clock cap in seconds) --
# records BOTH the crease-level clause size (len(keys)) and the
# variable-level clause size (len(clause), via assign()'s
# debug_clause_sizes hook). The committed nogood-lizard.json used cap 1500;
# nogood-horse.json (committed separately) used the default 1200 and
# completed within it despite reading elapsed_secs > 1200 -- see §6 for why
# that cap did not fire.
PYTHONPATH=. ../.venv/bin/python3 -u ../docs/superpowers/evidence/2026-09-24-dense-pleats/nogood_diagnostic.py \
   lizard ../docs/superpowers/evidence/2026-09-24-dense-pleats/nogood-lizard.json 1500
```

`bipartite_probe.py` regenerates the adjacency readings in §5.
