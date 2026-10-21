# What is the 79.57%? Breaking down dense `assign()`'s residual

**Status:** design, not yet planned.
**Scope:** a read-only profile across all 8 box-pleat subjects. No production code
changes; nothing under `mcp_harness/` is touched.
**Gates:** any local-CSP optimisation work, and specifically whether such work
could make dense labelling *measurable* on a subject other than `lizard`.

## 1. Why now

Gap 1's `2026-09-24-dense-pleats-design.md` §6.3 ended on a split result — dense
labelling works, dense layer-consistency does not — and six slices since have
eliminated six candidate causes. Five were negatives, each with a committed
artifact; the most recent (`2026-09-28-pleat-grid-headroom-design.md`) closed the
last geometry-side lever by measuring that `pleat_grid.fill` would inject **zero**
segments on all seven subjects it could census.

**One lever has never been attacked.** `evidence/2026-09-26-nogood-indexing/wtg-lizard-500k.json`,
on dense `lizard` at a 500,000-node budget:

| reading | value | share |
|---|---|---|
| `total_secs` | 930.19 | 100% |
| `global_check_secs` (the layer check) | 178.15 | 19.15% |
| `hits_nogood_secs` (the no-good scan) | 11.88 | **1.28%** |
| `remainder_secs` | **740.16** | **79.57%** |

That 1.28% is what withdrew the no-good indexing spec: you cannot buy back a run
by optimising 1.28% of it. The 79.57% is the largest share by far and nothing has
touched it.

**But it is a residual, not a measurement.** The profiling script defines it as
`total - global_check - hits_nogood` and glosses it as "the local CSP search
itself". Nothing has ever measured what is inside it. The same script's own
docstring records why that matters: the apportionment it replaced used a constant
of 6.4 s/candidate that "sums one per-candidate cost with two ONE-TIME costs",
and the corrected figure was 1.09 s — a difference that flipped the conclusion
from "indexing helps a lot" to "indexing helps almost not at all". A residual
glossed rather than measured is the same hazard one level down.

### 1.1 The goal is NOT convergence, and this must be stated first

`assign_budget` is a **node** budget. A cheaper node does not explore more of the
space; it explores the same nodes faster. Raising the budget is the only way to
explore more, and that is **already a measured negative**
(500,000-node column from `evidence/2026-09-24-dense-pleats/nogood-lizard.json`;
5,000,000-node column from its `-largebudget` sibling. Both columns are the same
four keys — `rejections`, `var_clause_size_median`, `distinct_witnesses`,
`elapsed_secs` — written by the same instrument at two budgets; see §12, which
records a challenge to the `834.0` and why it stands):

| | 500,000 nodes | 5,000,000 nodes |
|---|---|---|
| rejections | 113 | **584** (5.17x for 10x the budget) |
| clause median, solver variables | 202 | **204.5** — did not tighten |
| distinct witnesses | 113 of 113 | 584 of 584 |
| elapsed | 834.0 s | **8,865.1 s** (2.46 h) |
| converged | no | **no** |

So a local-CSP speedup cannot be justified as a convergence fix, and this spec
does not claim it. What it can be justified as is **measurability on more than one
subject.** `octopus` and `dog` do not finish dense labelling inside any cap this
project has used, and *every* finding across seven slices carries "this is
`lizard`" as its stated limit. At 1.48 ms/node — and see §1.2, that figure is
itself derived — a 500k run costs 15 minutes and a 5M run costs 2.5 hours, so the
generality gap and the throughput gap are the same gap.

### 1.2 A figure this spec deliberately does not trust

The 1.48 ms/node above is `remainder_secs / hits_nogood_calls` = 740.16 / 500,831.
`hits_nogood_calls` is being used as a **proxy** for node count because nothing
records the real one: `AssignFail("budget", budget)` reports the budget, not
consumption, so a run that terminates early leaves the denominator unknown. The
proxy is close here (500,831 against a 500,000 budget) but it is an assumption,
and it is the denominator of every per-node figure this spec cares about.
**Counting nodes directly is therefore a requirement, not a nicety** (§5.2).

## 2. Prior art (CLAUDE.md §0)

This slice **builds nothing**, so the prior art that binds it is about measurement
discipline; the CP literature below is named for the *follow-on* it would inform,
and is explicitly not adopted here.

**Adopted — Amdahl's ceiling** (Amdahl, *Validity of the single processor approach
to achieving large scale computing capabilities*, AFIPS 1967). Removing a
component entirely buys only its share of the **total**, not of the residual. A
component at 50% of the remainder is 50% x 79.57% = 39.8% of total, a **1.66x**
whole-run ceiling; the remainder itself caps everything at 4.9x, with the local
CSP running in zero time. §4 therefore requires the ceiling to be reported per
component, as a derived figure. Without it a bar could read "68% of the
remainder!" and license work whose real ceiling is 2.2x on a 2.5-hour run — a
share of a share presented as a share of the whole.

**Adopted — this project's own cautionary precedent.** `where_the_time_goes.py`
exists because an earlier apportionment was "brutally sensitive" to a constant
that conflated per-candidate and one-time costs, and it was written to *measure
the split directly instead*. Its two load-bearing properties are reused verbatim
in §5: it patches the **real** `assign.py` textually, and it **asserts the diff
against production consists only of the lines it added**, so "the patch either
applies to today's source or the script fails loudly; it cannot quietly measure
stale code."

**Named for the follow-on, NOT adopted here.** If §4 reaches row 1, the fix draws
on standard CP practice rather than invention:

* **Incremental arc consistency.** `violation(v)` (`assign.py:781`) rebuilds a
  `ring` with `_deg()` angle computations, a `free` dict and a `folded`
  comprehension **from scratch** on every call. The AC-3 → AC-4/AC-6 line
  (Mackworth 1977; Bessière & Régin) is precisely about maintaining support
  incrementally instead of re-deriving it, and is the relevant body of work.
* **Activity-based variable ordering.** Boussemart, Hemery, Lecoutre & Saïs,
  *Boosting Systematic Search by Weighting Constraints* (ECAI 2004, pp. 146-150)
  — a dynamic ordering heuristic that "exploit[s] information about previous
  states of the search process whereas traditional dynamic ones only exploit
  information about the current state." Relevant because `pick()`
  (`assign.py:881`) recomputes a most-constrained-vertex choice by scanning all
  interior vertices whenever its sticky vertex is exhausted.
* **Watched literals** (Moskewicz, Madigan, Zhao, Zhang & Malik, *Chaff*, DAC
  2001) — the canonical fix for scanning stored clauses per assignment.
  **Consciously not pursued**: that is `hits_nogood`'s job and it measures
  **1.28%**, which is why the indexing spec was withdrawn. Named here only so
  nobody re-proposes it.

## 3. What is measured

Per subject: dense `assign()` at a **fixed node budget**, with the residual broken
into **named, non-overlapping** components.

### 3.1 The components, and why each is a suspect

Read from the search loop in `mcp_harness/box_pleat/assign.py`:

| component | site | why it is a suspect |
|---|---|---|
| `pick` / `now_open` | `:901` | `any(var not in value for var in pleat_pref if var in touching)` — `pleat_pref` holds ~4,488 entries on dense `lizard`, and this runs every node. `any()` short-circuits, so it is cheap early and a full scan late. |
| `pick` / rescan | `:914-922` | when the sticky vertex is exhausted, loops **all** interior vertices (~~~454 on `lizard`~~ — see §11), each calling `eligible` → `free_vars_at`, which builds a set **and sorts it** (`:860-861`) |
| `violation` | `:781` | reached per value attempt via `retry`'s `all(feasible(w) for w in touching.get(var, ()))` (`:979`). Rebuilds `ring`, `free` and `folded` from scratch, with `_deg()` per incident piece, and may call `arrangement_ok_at_vertex`. |
| `prefer` | `:926` | the ridge branch runs a nested comprehension over `inc[q]` for both endpoints |
| `materialise` | `:989` | builds the `Assignment`; expected negligible (113 calls against 500k nodes) but measured rather than assumed |
| setup | `:613-622` | `build_pieces`, `initial_readings`, `pleat_paths`, `var_of`/`idx`/`touching` — **one-time**, and the residual contains it |

### 3.2 Self-time, because the call graph nests

`retry` calls `feasible` (→ `violation`) and `hits_nogood`; `pick` calls
`eligible` → `free_vars_at`. Accumulating naively either pushes the shares past
100% or, worse, sums to something plausible while charging a child's cost to its
parent twice.

**The contract: leaf components are measured exclusively, and every enclosing
block is reported as self-time — its own total minus its measured children.** This
is a stated requirement of the instrument, not an implementation detail, and §5.4
tests the arithmetic.

### 3.3 Why `global_check` must stay

The obvious simplification — pass `global_check=None` and profile the pure local
CSP — does not work. Without it there are no rejections, so `assign` returns on
the **first** complete candidate, and dense `lizard` reaches one in **0.76 s**
(`2026-09-24-dense-pleats-design.md` §6.3). The run would measure a few hundred
nodes rather than thousands. The CEGAR rejections are what drive the search deep,
so `global_check` stays and is subtracted, exactly as the existing harness does.

## 4. The bar, fixed before the data

### 4.1 The completeness gate, evaluated first

**No row may be claimed unless both hold:**

1. **The `cProfile` sweep names no hot function the accumulators do not cover.**
   Hand-placed accumulators can only measure what the author thought to
   instrument; a cost in `_deg`, in a tuple `__hash__`, or in a comprehension
   nobody wrapped would be charged silently to whichever enclosing block happens
   to contain it, and the residual would *move* rather than resolve. One
   `cProfile` run on `lizard` is the check. It is **not** used for shares — a
   deterministic profiler distorts many-small-call workloads, and at 23.7 µs per
   `hits_nogood` call this workload is exactly that.
2. **The measured components sum to the remainder within 5%.** A
   residual-inside-the-residual larger than that means components are missing,
   whatever `cProfile` said.

### 4.2 Per component, three figures — one measured, two derived

* `self_secs` — measured.
* `share_of_remainder` = `self_secs / remainder_secs` — derived.
* `whole_run_ceiling` = `1 / (1 - self_secs / total_secs)` — derived, and **the
  actionable one**: the whole-run speedup if this component cost nothing.

`share_of_remainder` and `whole_run_ceiling` are the same measurement rescaled,
so neither corroborates the other. Both are reported; the bar reads the ceiling.

### 4.3 The rows, evaluated in order

**"Top component" means the top PER-NODE component.** `setup` is one-time and is
evaluated separately by row 3, which is checked **first** — otherwise a run whose
residual is dominated by setup could satisfy row 1 or 2 and license per-node
optimisation of a cost that does not recur per node. Evaluate row 3, then rows 1,
2 and 4 in that order.

1. **Top per-node component ≥50% of the remainder AND per-node cost at `octopus` ≥2x
   `lizard`'s** → **OPTIMISE IT.** It is the cost *and* it is why large subjects
   cannot finish. Report its ceiling; the follow-on gets its own spec.
2. **Top per-node component ≥50% BUT per-node cost flat (`octopus` ≤1.2x `lizard`)** →
   **GENERALITY NOT REACHABLE THIS WAY.** Large subjects are blocked by node
   *count*, not node *cost*, and 10x the node budget is a recorded negative
   (§1.1). Optimising still buys wall clock on every subject equally — a real but
   lesser prize — and it does **not** unlock `octopus`.
3. **The remainder is mostly one-time setup (setup ≥50%)** → **DIFFERENT FIX.**
   Hoisting or caching, and it cannot be the generality blocker either, because a
   one-time cost does not grow with node count. **Checked before rows 1 and 2**,
   per the note above.
4. **No per-node component ≥25% of the remainder** → **NO SINGLE LEVER.** The cost is
   spread; report the table and stop.

Between 1.2x and 2.0x on the scaling reading, rows 1 and 2 both require a
judgement call: report the figures and decide, with no pre-commitment. That band
is named here so the absence of a rule is deliberate rather than discovered.

### 4.4 The prediction the ladder tests

The two leading hypotheses predict **opposite shapes**, so the size ladder
discriminates between them without needing the component table:

* If `pick`'s scans dominate, per-node cost tracks **candidate count**. `octopus`
  at 21,704 against `lizard`'s 4,488 is 4.8x, so `octopus` nodes should cost
  roughly 7 ms.
* If `violation` dominates, per-node cost tracks **vertex degree**, which barely
  grows with `N`, so the curve should be nearly flat.

### 4.5 The target, stated so it can fail

A dense labelling on a subject that **currently cannot produce one**, inside a
**1-hour** cap. Row 1 licenses attempting that; it does not promise it, and
§4.2's ceiling says how close the best case gets.

⚠ **This is not §5.2's cap.** §5.2 caps *this profile's* per-subject run, and is
set above `dog`'s known 537.3 s sparse cost so the profile does not lose a subject
the way the headroom census did. The 1-hour figure here is the target for a
*future optimised dense run*, which this slice does not perform.

## 5. Method, interfaces, error handling, testing

### 5.1 Files

```
docs/superpowers/evidence/2026-09-29-local-csp-profile/
  profile.py     # extends where_the_time_goes.py's patch-and-assert harness
  profile.json   # per-subject components + run metadata
  README.md
```

Nothing under `mcp_harness/` changes. `grep -c box_pleat mcp_harness/server.py`
stays 0.

### 5.2 Requirements on the instrument

* **Count nodes directly.** §1.2: the budget is not the consumption, and node
  count is the denominator of every per-node figure. A patched counter, reported
  per subject.
* **Reuse the patch-and-assert mechanism**, including its refusal to run when a
  patch anchor is absent from today's `assign.py`.
* **Fixed node budget across subjects**, so per-node costs are comparable. The
  budget is chosen once, small enough that the largest subject completes it inside
  its cap, and recorded in the artifact.
* **Per-subject time cap set from committed readings, not borrowed.** `dog`'s
  sparse compile alone is **537.3 s**
  (`evidence/2026-09-20-box-pleat/oracle-census/certify.json`). The
  `2026-09-28-pleat-grid-headroom` census used a 300 s cap borrowed from a sibling
  slice's *dense* arm and lost `dog` to it predictably; this spec sets the cap
  above the known sparse cost so that mistake is not repeated.
* **Run metadata in the artifact** — timestamp and commit SHA, continuing what
  `2026-09-28-witness-identity-design.md` §10 asked for and the headroom census
  first delivered.

### 5.3 Error handling

A subject exceeding its cap records that as its outcome and the run continues; the
profile never raises on a subject. JSON is flushed per subject, so a partial run
leaves a record. A failed completeness gate (§4.1) sets the verdict to
`GATE FAILED` and suppresses every row, in either direction.

### 5.4 Testing

`--selftest`, on synthetic input. No pytest file, because no production code
changes.

1. **Self-time arithmetic:** a synthetic nesting with known children, asserting
   parent self-time = total − children and that the parts sum to the whole.
2. **The bar:** all four rows reachable, plus both threshold boundaries (50%, 25%)
   and both scaling boundaries (1.2x, 2.0x) in exact integers, and the
   no-commitment band between them.
3. **The ceiling arithmetic:** a component at a known share of a known total
   yields the stated whole-run speedup — including that 50% of a 79.57% remainder
   gives 1.66x, which is the figure §4.2 exists to surface.
4. **The patch assertion refuses on altered source:** feed the patcher a source
   string with an anchor removed and confirm it **raises** rather than measuring
   something else. This is the harness's one load-bearing safety property, so its
   test must be able to fail.
5. **The completeness gate can fail:** a synthetic component set summing to 80% of
   a stated remainder must set `GATE FAILED`, not a row.

### 5.5 Evidence

`README.md` states, in order: §4.1's gate with both its readings; the component
table per subject with `self_secs`, `share_of_remainder` and `whole_run_ceiling`,
with the last two labelled derived; the per-node scaling across the ladder and
whether §4.4's prediction held; the §4.3 row reached and why that row and not its
neighbours; and §6's limits.

## 6. What this cannot say

* **Nothing here addresses convergence.** §1.1: the budget is in nodes, 10x it is
  a recorded negative, and a cheaper node explores the same nodes faster. A row-1
  verdict licenses optimisation work aimed at *measurability*, never at
  convergence.
* **A ceiling is not a speedup.** §4.2's figure is what removing a component
  *entirely* would buy. No real optimisation removes a component entirely.
* **`lizard` remains the only subject with a dense convergence history.** The
  ladder measures per-node cost on eight subjects, which is a statement about
  cost, not about what those subjects' searches would do at a large budget.
* **`cProfile` is a completeness check, not a measurement.** Its numbers must not
  appear in the README as shares.

## 7. Out of scope

* **Any optimisation.** Gated on §4.3 row 1, with its own spec.
* **Raising `assign_budget`.** A recorded negative (§1.1); this slice must not be
  read as preparing one.
* **No-good indexing / watched literals.** Withdrawn at 1.28%; named in §2 only to
  prevent re-proposal.
* **Any change to `assign.py`, `layers.py`, `cores.py`, `contours.py`,
  `layer_order.py`, or the serve path.** The instrument patches a **temp copy**;
  production is read, never written.
* **Descent-time clause propagation** — the other open lever
  (`2026-09-28-witness-identity-design.md` §10). Its own question, untouched here.
* **`2026-09-24-dense-pleats-design.md` §10's dense-beside-sparse CP gallery.**
  Still owed by gap 1, still gated on dense converging.

---

## 11. Dated correction, 2026-09-29 (POST-data): §3.1's interior-vertex count

**§3.1's table said the `:914-922` rescan loops "~454 interior vertices on
`lizard`". That figure is struck: the measurement this spec asked for refutes
it, and the real count is at least 4,237 — roughly 9× larger.**

The derivation uses only committed data and production call sites. `free_vars_at`
is called from `eligible` alone (`assign.py:876`), and `eligible` from `pick`
alone (`:910` sticky, `:915` in the rescan loop), so one `pick()` call makes at
most `1 + |interior|` `free_vars_at` calls. From
`evidence/2026-09-29-local-csp-profile/profile.json`, dense `lizard` reads
`calls.free_vars_at = 84,754,358` against `calls.pick = 20,000`, so
`84,754,358 / 20,000 = 4,237.7179` per `pick` call; less the one sticky-path call
that is `4,236.7179`, and the count of interior vertices is an integer, so
`|interior| >= 4,237` on `lizard`. The same arithmetic on `octopus`
(`417,181,743 / 20,000 = 20,859.0872`) gives `|interior| >= 20,859`.

**Corrected 2026-09-29, second pass (figure discipline, not a result).** This
paragraph first printed `>= 4,236` and `>= 20,857`, having divided by `nodes`
(20,001) rather than by `calls.pick` (20,000), while
`evidence/2026-09-29-local-csp-profile/README.md` §3.4 printed the per-node pair
`>= 4,237` and `>= 20,858`. All four are sound lower bounds and no conclusion
turned on the difference — but one bound printed two ways across two documents is
exactly the drift this section exists to record. Both documents now carry the
tight pair **4,237 / 20,859**, derived per `pick` call as above, and the README
§3.4 shows the same arithmetic in a table.

**Why this matters beyond the number.** §3.1 listed the rescan as one suspect
among six. At ~454 vertices it would have been a plausible contributor; at
>= 4,237 it is the dominant cost, and the measurement agrees — `free_vars_at`
carries 64.8-65.3% of the remainder on seven of eight subjects and `pick`'s own
self-time another 32.6-34.1%, ~99% between them. The struck figure understated
the very component the slice was built to find.

**What is NOT claimed here.** This bounds `|interior|` from below; it does not
measure it. The instrument records neither `|interior|` nor the rescan
frequency, and `calls.free_vars_at / nodes` is their product — so the split
between "the rescan runs at nearly every node over ~4,237 vertices" and any
other factorisation is **not** decided by this run. `evidence/
2026-09-29-local-csp-profile/README.md` states the same limitation.

**Where the struck figure came from is not recorded**, which is itself the
finding: no committed script computes it. That is the fourth figure this branch
has withdrawn for being quoted forward without recomputation, and the first to
be refuted by its own slice's measurement.

---

## 12. Dated note, 2026-09-29 (POST-data): §1.1's `834.0 s` was CHALLENGED and STANDS

A final-review pass flagged §1.1's `| elapsed | 834.0 s | **8,865.1 s** |` row as a
fifth figure to withdraw, on the ground that the artifact recording the
500,000-node arm — `evidence/2026-09-26-nogood-indexing/wtg-lizard-500k.json` —
has **no `elapsed` field at all**. That observation about *that file* is correct:
its keys are `total_secs` (930.19), `global_check_secs`, `hits_nogood_secs`,
`remainder_secs`, `hits_nogood_calls`, `per_candidate_layer_secs` and the rest, and
no `elapsed` among them. **The inference from it is wrong**, because that file is
not where §1.1's left column comes from.

**The figure is committed, and so is every cell beside it.**
`evidence/2026-09-24-dense-pleats/nogood-lizard.json` reads `elapsed_secs = 834.0`
with `outcome.detail` = `AssignFail(kind='budget', site=500000)`,
`rejections = 113`, `var_clause_size_median = 202` and `distinct_witnesses = 113`
— **all four** of §1.1's left-column readings, from one artifact, under the same
key names its `-largebudget` sibling uses for the right column
(`elapsed_secs = 8,865.1`, `rejections = 584`, `var_clause_size_median = 204.5`,
`distinct_witnesses = 584`, `site=5000000`). Both were written by
`nogood_diagnostic.py`, whose `elapsed_secs` is `time.time() - t_start` with
`t_start` taken **after** the sparse compile (`:126`, `:137`), reported separately
as `sparse_compile_secs` (6.6 s and 6.7 s). So the two columns are the same
quantity at two budgets and the row does compare like with like. Only the
**citation** was missing; §1.1 now names both files.

**The trap that produced the false alarm is worth recording**, because it inverts
this branch's usual one. `wtg-lizard-500k.json`'s `total_secs` (930.19) is neither
the same quantity nor the same run as `nogood-lizard.json`'s `elapsed_secs`
(834.0): the former is dense `assign`'s own accumulated total in the 2026-09-26
instrument, the latter the 2026-09-24 run's dense-phase wall clock, and 834.0 is
not derivable from it (`evidence/2026-09-27-core-in-loop/README.md` records that
session-to-session wall clock on this box moved ~1.26x, which is the size of the
gap). The only `834.6` elsewhere in the corpus is an
`[index, elapsed, clause_size]` entry inside the **large-budget** file's own `trace`, i.e. a 5,000,000-node
reading, and it is a coincidence rather than a source. Searching two artifacts by
shape instead of by key name is what made a sourced figure look unsourced.

**No figure is struck here.** This is the first withdrawal proposed on this branch
that the artifacts refused; the four recorded in §11 and earlier are untouched, and
the lesson carried forward is that a withdrawal needs the *producing* artifact
identified, not merely one artifact that lacks the key.
