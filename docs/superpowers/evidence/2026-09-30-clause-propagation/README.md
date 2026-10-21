# What could the learned clauses have pruned during descent, and don't?

Spec: `../../specs/2026-09-30-clause-propagation-design.md`. Script: `probe.py`.
Artifact: `probe.json` (all six arms, each arm's raw counters verbatim under
`raw`). **Every measured figure in this file is read back from `probe.json`
after the process exited** — nothing is transcribed from the stdout that was
watched while it ran, which is the discipline
`../2026-09-27-core-in-loop/README.md` records and the `share_of_remainder`
rounding incident is what it cost to learn. Figures cited from elsewhere are
attributed inline; figures obtained by arithmetic on the artifact show that
arithmetic where they appear.

```
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -u \
  ../docs/superpowers/evidence/2026-09-30-clause-propagation/probe.py \
  ../docs/superpowers/evidence/2026-09-30-clause-propagation/probe.json
```

Run 2026-10-01, launched in the background, **exit 0**. Wall clock: the six arm
records sum to 209.2 + 68.2 + 11.3 + 24.9 + 5.4 + 31.9 = **350.9 s (5 m 51 s)**,
of which the two primary arms are 209.2 + 68.2 = 277.4 s. `run_completed` is
`true` and no arm is `truncated`.

**Unlike the predecessor, run metadata is in the artifact itself.**
`../2026-09-27-core-in-loop/README.md` had to record date, commit and exit
status in prose because `ab.py` wrote neither a timestamp nor a commit into its
JSON, and it asked a successor script to record both there. `probe.py` does:
`measured_utc` `2026-10-01T07:16:16.654527+00:00` (written when the run
started), `commit` `98d27f2587bf319875b00d49d87d7fbb3371e742`, `run_completed`
`true`, and `dirty` `false` with an empty `dirty_paths` — so the figures were
produced by a committed runner, not an uncommitted edit. `loadavg_at_start` is
`[1.846, 2.155, 2.556]` and every row carries its own `loadavg`; the highest
1-minute reading on any arm is 3.739 (arm B). Those four load figures are
rounded to 3 decimals here from the artifact's full binary values
(`1.84619140625`, `2.15478515625`, `2.5556640625` and `3.73876953125`). The only
CPU-bound process during the run was the probe itself, and the 1-minute load
never approached the ~4 at which the plan says to wait.

---

## 1. The identity gate — before any headline

`identity.checked_arms` = **2**, `identity.passed` = **true**,
`identity.failures` = **empty**.

| | arm A (`core_extraction=False`) | arm B (`core_extraction=True`) |
|---|---|---|
| rejections, control (`../2026-09-27-core-in-loop/ab.json`) | 113 | 3 |
| rejections, measured | **113** | **3** |
| clause-size multiset, control | min 6 / median 202 / max 259 | {5, 8, 8} |
| clause-size multiset, measured | min 6 / median 202 / max 259 | **[5, 8, 8]** |
| terminal outcome, control | `AssignFail(kind='budget', site=500000)` | same |
| terminal outcome, measured | `kind='budget'`, `site='500000'` | `kind='budget'`, `site='500000'` |
| nodes observed by the instrument | 500000, exactly the budget | 500000, exactly the budget |
| nodes per rejection | 500000/113 = **4424.8** | 500000/3 = **166666.7** |

The last row is a free cross-check: the control records `nodes_per_rejection`
4424.8 and 166666.7, and the measured node counts reproduce both.

The gate also required, as of the Task 4 hardening, that the instrument
*produced figures* rather than merely that the solver was unchanged:
`instrument_ok` is `true` on all six rows with `instrument_missing` empty, so
no fraction below is a defaulted zero standing in for a dead instrument.

**Counter correctness is NOT established at the measured budget — stated, not
closed.** Every figure in this README is read from `ClauseIndex` counters
(`live_total`, `unit_nodes`, `dead_nodes`, the per-clause agree/contra counts),
and the identity gate above proves only that the *solver* was unchanged and
that the instrument *produced* figures. It does not prove the counters were
right. `ClauseIndex.verify()` is the one thing that catches a *compensating*
counter error (its own docstring says so), and **both measured arms ran with
`clause_prop_verify` off**: `probe.py`'s `run_arm` passes `clause_prop=prop`
alone. Where correctness *was* established is Task 3's gate arm: dense
`lizard`, **20,000 nodes**, with both `vertex_index_verify` and
`clause_prop_verify` on, completing without raising — at **10 rejections** (that
arm's own print, `nodes=20000 clauses=10 rejections=10`, in the Task 3 report,
which is untracked process scratch; the 20,000-node figure and the gate's
design are in `../../plans/2026-09-30-clause-propagation.md`, Task 3 Step 9b),
plus the wiring tests on sparse `lizard` and dense `starfish`, which also run
`verify` on. The measurement arms are **25× larger in nodes (500,000 / 20,000)
and 11.3× larger in rejections on arm A (113 / 10)**. A counter bug reachable
only after many CEGAR rounds would shift `live_total`, `unit_nodes` and
`dead_nodes` with no in-run detector, and every headline would then be
published as measured. Verification was off because `verify()` is
O(clauses × nodes) — it walks every clause on every node, the work the counters
exist to avoid — and re-running a 500,000-node arm with it on is prohibitive by
design. **What therefore is not established: that the counters were exact at
500,000 nodes and 113 rejections.** What is: that they were exact on every
smaller compile where `verify` ran, including the CEGAR reassignment path.

**This is also the 500,000-node identity evidence the vertex-index slice left
open.** That slice ran its identity pass at `assign_budget=20_000` and declined
to flip `vertex_index`'s default on that basis. Both arms here ran with
`vertex_index=True` at 500,000 nodes and reproduced the control's rejection
counts, clause sizes and terminal site exactly. **It does not flip that
default** — it stops owing one of the missing points, nothing more. No
recommendation about the default is made or implied here.

---

## 2. The headline: the arms disagree

`verdict.arms_agree` is **false**, so `verdict.band` reads, by design:

> **`ARMS DISAGREE: A=PROPAGATION REFUTED; B=REAL BUT PARTIAL`**

| arm | `dead_node_fraction` | band (thresholds fixed before the run) |
|---|---|---|
| A (`core_extraction=False`) | **0.006208** | below 0.05 → **PROPAGATION REFUTED** |
| B (`core_extraction=True`) | **0.233962** | in 0.05 – 0.50 → **REAL BUT PARTIAL** |

**The split is the headline.** `verdict.band_split.band_max_arm` is
`REAL BUT PARTIAL`, and per the artifact's own note it is recorded for
reference and is **not** the verdict; it is not quoted as one here. Neither is
arm A's band, which is equally one arm.

What the split licenses: **nothing is authorised, and no follow-on spec is
justified on this evidence alone.** `PROPAGATION IS THE LEVER` (≥ 0.50) was the
only band that would have justified a follow-on spec, and no arm reached it;
the higher arm lands in the band whose fixed instruction is "report it; wire
nothing." The two arms are the same subject and the same stage differing only
in whether rejections are narrowed to cores, so the honest reading is that the
value of descent-time propagation **depends on which clause database you
have**, and that is a finding about core extraction as much as about
propagation.

---

## 3. Attribution: arm B's high `unit_node_fraction` is clause TIGHTNESS, not clause scarcity

`verdict.attribution_guard_fired` is **false** — the guard fires only when
`unit_node_fraction < 0.01` in *both* arms, and arm B reads 0.741764. The
guard's case is therefore not the one in front of us. The case in front of us
is the one the flag does not cover: a high figure on **one** arm, carried by
**three** clauses. Spec §4's two causes still have to be separated by hand.

| | arm A | arm B |
|---|---|---|
| `clauses_total` (authoritative, `len(debug_clause_sizes)`) | **113** | **3** |
| `clause_availability` (node-weighted mean live clauses) | **3.438** | **1.624** |
| `unit_node_fraction` | **0.008238** | **0.741764** |
| clause sizes | min 6 / median 202 / max 259 | 5, 8, 8 |
| agreeing binds needed to go unit (size − 1) | 5 / **201** / 258 | **4** / 7 / 7 |

`clauses_total` is read from the row, not from `raw["clauses_total"]` — the
latter is the index's per-node snapshot taken at the top of the solver loop and
can trail the stored count by one. On this run the gap is **0 on all six rows**
(113/113, 3/3, 1/1, 1/1, 0/0, 1/1), so the distinction changed nothing here,
but the figures above are the authoritative ones regardless.

**The discriminator.** Arm B holds *fewer* live clauses per node than arm A —
`clause_availability` 1.624 against 3.438, a ratio of 1.624/3.438 = 0.472 — and
yet reaches a unit state **90.0× more often**: 0.741764/0.008238 = 90.04.
Scarcity can only *depress* a unit-node fraction; it cannot raise one. So
scarcity is not what produces arm B's 0.741764.

Normalising the fraction by the number of live clauses removes the clause-count
confound outright. Per live clause, the unit rate is

* arm A: 0.008238 / 3.438 = **0.002396**
* arm B: 0.741764 / 1.624 = **0.456751**

a factor of 0.456751/0.002396 = **190.6×**. The cause is per-clause width: a
clause of size *k* goes unit once *k* − 1 of its variables sit at their
forbidden values, so arm B's {5, 8, 8} needs 4 or 7 agreeing binds while arm
A's median 202 needs **201**. Width is **necessary, and sufficient to explain the gap *relative to arm A***
— it is consistent with spec §4's counter-hypothesis, which was stated in
advance: a core's 5–8 variables are the blamed faces of a single
`taco_tortilla` among exactly 3 faces, hence geometrically adjacent, so
`touching` and the MRV order may well bind them consecutively, and clauses may
go unit often relative to how few there are. They do. But the data does **not**
separate width from **search locality** as the cause of the *rate*. Arm B
advances 166666.7 nodes per rejection, so 3 narrow clauses could be unit at 74%
of nodes because the search is parked in one subtree where most of their
variables already sit at their forbidden values. The 4-versus-201
agreeing-binds arithmetic is independent of the counts and stands; what it
establishes is that arm A *could not* behave this way, not that width alone
produces arm B's 0.741764. Locality is the unexcluded alternative, and it
applies to the rate exactly as it applies to `dead_node_fraction`'s diversity
below.

**The two causes land on different arms and are not interchangeable:**

* **Arm A is spec §4's "too wide" cause, confirmed.** 113 clauses, 3.438 live
  per node — more clauses and more of them live than arm B — and still unit at
  only 0.82% of nodes (`unit_node_fraction` 0.008238), because 201 agreeing
  binds is not a state the search reaches. Arm A's `PROPAGATION REFUTED` is a
  statement about *clause width*, not about propagation as a mechanism.
* **Arm B is not spec §4's "too few clauses" cause** as an explanation of its
  *rate*. Scarcity is a real property of arm B — 3 clauses, with a node-weighted
  mean of 1.624 live per node (§3) — but it is not what the 0.741764 measures.

**What the data does NOT settle, and must not be read as settled.** The figure
rests on **3 clauses on one subject**, so it is a statement about three
clauses, not about a clause database. More importantly,
`dead_node_fraction` counts **nodes**, not distinct provably-dead subtrees: arm
B's 116981 dead nodes (116981/500000 = 0.233962) could be 116981 distinct dead
regions or one small region re-entered. Arm B reaches only 3 candidates in
500,000 nodes — 166666.7 nodes per rejection — so its search is barely
advancing, and a barely-advancing search re-visiting the same neighbourhood is
exactly the shape that would inflate a node-counted fraction. This instrument
cannot distinguish the two, and **the 0.233962 should not be read as
"23.4% of arm B's search is wasted in 117 thousand different dead places."**

---

## 4. Domain sizes: propagation is **not** weak by construction here

`unit_domain_2` and `unit_domain_3` count unit **clause-events** (one per unit
clause per node), not nodes — arm A records 3069 + 1068 = 4137 events over 4119
unit nodes, i.e. 4137/4119 = 1.0044 per unit node.

| row | `unit_domain_2` | `unit_domain_3` | `unit_domain_other` | 2-valued share |
|---|---|---|---|---|
| lizard arm A | **3069** | **1068** | 0 | 3069/4137 = **0.7418** |
| lizard arm B | **457592** | **0** | 0 | **1.0000** |
| frog | 17094 | 0 | 0 | 1.0000 |
| horse | 15853 | 0 | 0 | 1.0000 |
| bird | 0 | 0 | 0 | — (no clauses stored) |
| guinea_pig | 12215 | 0 | 0 | 1.0000 |

Spec §3.2 built the probe for the general case precisely because a unit clause
on a 3-valued variable (`["V", "M", "F"]`, from `prefer()`'s
`if can_be_flat(var): order = order + ["F"]`) prunes one of three values and
**forces nothing** — and warned that if most unit clauses landed there,
propagation would be weak *by construction*. **Measured, that worry does not
hold on this data:** 74.18% of arm A's unit events and **100%** of every other
row's are on 2-valued variables, where a unit clause does force the remaining
value. `unit_domain_other` is 0 everywhere, so no unit clause ever sat on a
domain of size other than 2 or 3.

This is a separate finding from the band, and it cuts the other way from the
band: wherever a clause does go unit, the inference available is almost always
a forced value rather than a one-of-three narrowing. The general-case machinery
was still necessary — arm A's 1068 three-valued events are 1068/4137 = 0.2582 of
its unit events — so the probe's design is vindicated, not made redundant.

---

## 5. `unit_var_chosen_fraction`: the search almost never works on the unit variable

`unit_var_chosen_fraction` is the share of **all** nodes at which `pick` chose a
variable that was already the free variable of some unit clause. Its complement
*within the unit nodes* is the interesting quantity: a unit clause existed and
the search went to work on something else.

| row | `unit_var_chosen_fraction` (of all nodes) | chosen / unit nodes | **not** chosen |
|---|---|---|---|
| lizard arm A | 0.00173 | 865/4119 = 0.2100 | **0.7900** |
| lizard arm B | 0.043572 | 21786/370882 = 0.0587 | **0.9413** |
| frog | 0.00754 | 377/17094 = 0.0221 | 0.9779 |
| horse | 0.00678 | 339/15853 = 0.0214 | 0.9786 |
| guinea_pig | 0.00206 | 103/12215 = 0.0084 | 0.9916 |

On arm B, at **94.13%** of the nodes where a unit clause existed, the MRV order
handed the search a different variable. That is the most direct measurement in
this artifact of the defect the slice set out to characterise: the information
is present and the search is not pointed at it.

**Spec §3.3's `unit_latency_nodes` was withdrawn during implementation** and
replaced by `unit_var_chosen_nodes`, and the spec records why: latency — nodes
elapsed from a unit event until that variable is next bound — needs cross-node
state that **goes stale on backtracking**. When the search backtracks past the
binds that made a clause unit, the pending entry survives, and the next bind of
that variable records a latency for a clause that is no longer unit. The
replacement carries the same signal with no cross-node state, as one
set-membership test against state `observe` already builds for the current
node.

---

## 6. Instrument cost

`observe_secs` is the **observe-side** cost: the whole of `observe()`, which
pays for the `sorted`, `free_var_of` and `prefer` passes that `probe_secs`
cannot see. `probe_secs` is the inside of `probe()` only.

| row | `probe_calls` | `probe_secs` | share of that arm's `secs` | `observe_secs` | share of that arm's `secs` |
|---|---|---|---|---|---|
| lizard arm A | 4119 | 0.03 | 0.03/209.2 = 0.014% | 0.2 | 0.2/209.2 = **0.096%** |
| lizard arm B | 457592 | 14.71 | 14.71/68.2 = 21.569% | 15.83 | 15.83/68.2 = **23.211%** |
| frog | 17094 | 0.32 | 0.32/11.3 = 2.832% | 0.39 | 0.39/11.3 = 3.451% |
| horse | 15853 | 0.4 | 0.4/24.9 = 1.606% | 0.47 | 0.47/24.9 = 1.888% |
| bird | 0 | 0.0 | 0.000% | 0.01 | 0.01/5.4 = 0.185% |
| guinea_pig | 12215 | 0.19 | 0.19/31.9 = 0.596% | 0.25 | 0.25/31.9 = 0.784% |

**`observe_secs` is NOT the instrument's total overhead** and the percentages
above must not be quoted as overhead. It excludes every `bind` / `unbind` /
`add_clause` counter update and `note_choice` — the per-assignment maintenance,
about 4.4 counter updates per bind on the widest arm (spec §5, from
113 × 202 = 22,826 clause-variable incidences over roughly 5,140 variables).
Task 3 measured that the bind-side is nearly all of the cost at a small budget:
of its +0.59 s total, the observe side was 0.01 s. A README that writes
"overhead N%" from `observe_secs` alone understates the cost.

**Total overhead, as a range.** The figure to quote as overhead is the
wall-clock difference between an instrumented and an uninstrumented run, which
Task 3 measured on dense `lizard` at a **20,000-node budget**
(both samples are recorded at
`../../plans/2026-09-30-clause-propagation.md:2421-2422`, in the Task 3 step of the
implementation plan; a plan, not an evidence directory):
**+0.59 s / +3.2%** in one run (18.98 s instrumented against 18.39 s
uninstrumented) and **+0.33 s / +1.2%** in an independent rerun of the same two
arms (27.42 s against 27.09 s). So: **roughly 1–3% at a 20,000-node budget — a noisy bound, not a
point estimate.** The machine was shared and the two runs' absolute times
differed by about 47% (27.09 / 18.39 − 1 = 0.473, uninstrumented arm), and
both samples were single runs. Neither sample is quoted alone, they are not
averaged, and no tighter bound is claimed than those two support.

**That ratio is a per-node property and is NOT a figure for the 500,000-node
arms** — and this run shows concretely why, which is worth more than the
warning alone. The instrument's cost is driven by probe density, and
`probe_calls` per node varies by two orders of magnitude across these rows:

* Task 3's 20,000-node gate row (`probe_calls=116`, `nodes=20000`, recorded at
  `../../specs/2026-09-30-clause-propagation-design.md:212`):
  116/20000 = 0.005800 probes per node
* lizard arm A: 4119/500000 = 0.008238 — 1.4× that
* lizard arm B: 457592/500000 = 0.915184 — **157.8×** that

Arm B's **observe-side component alone (23.211%) is an order of magnitude
larger, as a ratio, than Task 3's total overhead range**. That is not a
contradiction of Task 3's measurement; it is a demonstration that the ratio
does not transfer, because its driver — how often a clause is unit — differs by
157.8× between the two settings. Arm B's 68.2 s is therefore not a clean
timing of the solver, and no speed conclusion should be drawn from it. No
fraction in this README is affected: every one is a count of nodes divided by
`nodes`, and the instrument does not change the node count (the identity gate
in §1 is what establishes that).

---

## 7. Breadth: four more subjects, arm A only, at 50,000 nodes

| subject | budget | `secs` | `nodes` | `clauses_total` | `clause_availability` | `unit_node_fraction` | `dead_node_fraction` |
|---|---|---|---|---|---|---|---|
| **lizard arm A** | 500000 | 209.2 | 500000 | 113 | 3.438 | 0.008238 | **0.006208** |
| **lizard arm B** | 500000 | 68.2 | 500000 | 3 | 1.624 | 0.741764 | **0.233962** |
| frog | 50000 | 11.3 | 50000 | 1 | 0.435 | 0.34188 | **0.1653** |
| horse | 50000 | 24.9 | 50000 | 1 | 0.7505 | 0.31706 | **0.04996** |
| bird | 50000 | 5.4 | 50000 | **0** | 0.0 | 0.0 | **0.0** |
| guinea_pig | 50000 | 31.9 | 50000 | 1 | 0.3497 | 0.2443 | **0.1716** |

Every breadth arm ran to its budget — `nodes` 50000 with
`AssignFail(kind='budget', site='50000')`, none `truncated`.

**`bird`'s row is vacuous and is not a reading.** It stored **0** clauses in
50,000 nodes (`layers_tried` 0, `probe_calls` 0), so its `unit_node_fraction`
and `dead_node_fraction` of 0.0 are 0/50000 with nothing in the numerator —
the absence of any clause to go unit, not a measurement that unit clauses were
unavailable. It would read `PROPAGATION REFUTED` if banded, and it must not be
banded. It is one of the six rows and the only one where the instrument had
nothing to observe.

**The three non-vacuous breadth subjects agree with §3's tightness
mechanism, and they sharpen it** (width is necessary; §3's locality caveat
still applies to every rate quoted here). Each stored exactly **one** clause, and in
each case of size **2** — the narrowest possible, needing a single agreeing
bind to go unit — *without* core extraction. Their `unit_node_fraction` runs
0.2443 to 0.34188 on one clause apiece. So the pattern is consistent across
the **four subjects** that stored any clause (`lizard`, `frog`, `horse`,
`guinea_pig`; `bird` stored none and is excluded). That is four subjects but
five *rows* — `lizard` contributes two, arm A and arm B — and the two must not
be conflated: narrow clauses go unit readily, wide ones essentially never, and
clause count is not what drives the rate.

Their `dead_node_fraction` spans **0.04996** (`horse`) to **0.1716**
(`guinea_pig`). Note `horse` sits **just below** the 0.05 threshold — by
0.05 − 0.04996 = 0.00004 — so on the fixed bands `horse` would read REFUTED and
`frog` and `guinea_pig` REAL BUT PARTIAL. That knife-edge is reported rather
than rounded; 0.04996 is the artifact's value and it is not 0.05.

**The stated direction of bias, which makes this a weak result either way.**
Clause availability grows with nodes, so the 50,000-node breadth budget
**understates** it by construction, which makes a *null* breadth result weaker
evidence than a positive one. Here the breadth result is not null — **two** of
the four (`frog` 0.1653 and `guinea_pig` 0.1716) land in REAL BUT PARTIAL
territory, a third (`horse` 0.04996) misses it by 0.00004, and the fourth
(`bird`) is vacuous — so the bias works against the direction actually observed,
which is the more favourable case for the reading. It remains four subjects at a
tenth of the primary budget, arm A only, and the bands were not defined for
them.

**`octopus` and `dog` are excluded** although they too reach `assign` in dense.
Neither completed the dense labelling audit:
`../2026-09-24-dense-pleats/dense_labelling.json` carries no `dense_mv` for
either (independently rechecked for this README — `bird`, `lizard`, `horse`,
`frog` and `guinea_pig` all carry it; `octopus` and `dog` do not), so there is
no dense control to compare a reading against.

---

## 8. What this does NOT establish

Spec §12, adapted to the numbers actually measured.

* **It cannot show that dense converges, or that it cannot.** Both primary arms
  end on a node budget — `AssignFail(kind='budget', site='500000')` with
  `nodes` 500000 — and a budget is a timeout, not a decision. The withdrawal
  recorded at `../../specs/2026-09-24-dense-pleats-design.md:510` stands: dense
  "does not converge within 113 candidates and a 500,000-node budget — **not
  that it cannot**."
* **`dead_node_fraction` is a lower bound and is not a predicted speedup.** It
  is a lower bound twice over, by construction: only clauses **already unit**
  are considered — a clause one bind short of unit is invisible to it — and the
  cascade is **one step, never a fixpoint**, so a value eliminated here is
  never propagated onward to eliminate another. And it is not a speedup: a real
  propagator would change the search path, so the node count the solver would
  actually reach is **not derivable** from this measurement. Nothing here says
  arm B would finish, or finish 23.4% sooner, or finish at all.
* **A null breadth result would be weak**, because the 50,000-node budget
  understates clause availability (§7). This result is not null, but it is four
  subjects at a tenth of the primary budget, one of them (`bird`) vacuous.
* **The headline is a split, not a verdict**, and neither arm's band may be
  quoted as the slice's answer (§2).
* **Arm B's figure rests on 3 clauses and counts nodes, not distinct dead
  subtrees** (§3), so it does not establish that arm B's wasted descent is
  diverse rather than repetitive.
* **It says nothing about the eight subjects that never reach `emit`.**
  Independently recounted from `../2026-09-20-box-pleat/results.json` for this
  README: **9 of 17** subjects read `flat_fold_ok: true`, 8 do not. Six stop at
  `contours` (`cat`, `elephant`, `bat`, `dolphin`, `scorpion`, `ant`), `crab`
  stops at `tree`, and **`rabbit` stops at `assign`** — so only `rabbit` fails
  in the stage this instrument watches, and `rabbit` is in neither the primary
  nor the breadth arm.
* **It says nothing about `vertex_index`'s default** (§1).
* **Counter correctness at the measured budget is not established** (§1).
  Both measured arms ran with `clause_prop_verify` off; `verify()` was run only
  at 20,000 nodes and 10 rejections, against 500,000 nodes and 113 rejections
  on arm A. A counter bug reachable only after many CEGAR rounds would shift
  every headline with no in-run detector.
* **§3's tightness mechanism is not separated from search locality**, and rests
  on one subject's 3 clauses. **No arm B (core extraction on) was run on any
  breadth subject**, so the mechanism has exactly one subject with
  extraction-narrowed clauses behind it.
* **Named debt: the diversity of arm B's dead nodes was a free measurement and
  was not taken.** `ClauseIndex.observe()` already computes `free_var_of` for
  every unit clause, so `len({free variable at dead nodes})`, or the count of
  distinct dead `(var, forbidden)` pairs, would have cost nothing and would
  bound the "one region re-entered" worry that §3 names as arm B's chief
  weakness. It is not built because adding it means re-running both
  500,000-node arms. **The one-line change that closes it:** in `observe()`,
  inside `if self.probe(cid):` just before `dead_nodes` is incremented, add
  `out.setdefault("dead_pairs", set()).add(self.free_var_of(cid))` (the
  `(var, forbidden)` pair; take `len(...)` of it in `derived()` so the set never
  reaches `probe.json`), then re-run arm B — the 3-clause arm, 68.2 s, is cheap,
  and arm A need not be re-run to answer this.

---

## 9. What surprised me

**(a) The run was several times faster than the plan budgeted, and the arms'
speed ordering flipped.** The plan
(`../../plans/2026-09-30-clause-propagation.md`, Task 5 Step 2) estimated
roughly 430 s and 390 s for the two primary arms — the control's 1052.0 s and
954.9 s divided by the vertex index's measured 2.449× — and 25–40 minutes
overall. Measured: **209.2 s and 68.2 s**, and 350.9 s for all six arms. On the
primary arms that is 430 + 390 = 820 s predicted against 277.4 s measured,
820/277.4 = **2.96×** fast; against the whole-run estimate, 25 min = 1500 s and
40 min = 2400 s against 350.9 s, i.e. 1500/350.9 = **4.3×** to
2400/350.9 = **6.8×** fast. Against the uninstrumented control that is
1052.0/209.2 = **5.03×** on arm A and 954.9/68.2 = **14.00×** on arm B, both far
beyond 2.449×. The control's arms were nearly equal (1052.0/954.9 = 1.10); here
arm A takes 209.2/68.2 = **3.07×** arm B. The 2.449× figure was measured at
`assign_budget=20_000` and **does not extrapolate to 500,000 nodes**, and the
per-arm ratio does not survive either — plausibly because arm A's 113 clauses
of median width 202 make its `hits_nogood` scan and counter maintenance far
heavier than arm B's 3 narrow ones, which is a 500,000-node effect that a
20,000-node run barely sees. Identity passed on both arms, so **the search path
is pinned and no figure in this README is affected**; only time per node
changed. The spec's §8.1 has been corrected in the same commit to record the
measured wall clocks and that the 2.449× does not extrapolate.

**(b) `unit_domain_3` is 0 on five of six rows** (`bird`'s 0 is vacuous: it stored no clauses). Spec §3.2 treats the 3-valued
case as the live risk that would make propagation weak by construction, and
built a second `feasible` sweep for it. Measured, unit clauses land on 2-valued
variables 100% of the time on the **four** rows that have a defined share (arm B,
`frog`, `horse`, `guinea_pig`) and 74.18% of the time on arm A (§4); `bird`'s
share is 0/0 and undefined, not 100%.
The machinery was still needed — arm A has 1068 three-valued events — but the
anticipated weakness is not what the data shows. Recorded in the spec in the
same commit.

**(c) The instrument's own cost reaches 23.211% of an arm's wall clock**, an
order of magnitude above Task 3's entire measured overhead range of roughly
1–3%, because arm B probes at 157.8× the density of Task 3's row (§6). Task 3's
figure is not wrong; the lesson is that the overhead ratio is governed by
unit-clause density and a budget-specific sample cannot bound it. This is the
one place where the slice's own cost became large enough to matter, and it
matters only for arm B's timing, not for any fraction.

**(d) The breadth subjects' no-goods are size 2 without core extraction.**
`frog`, `horse` and `guinea_pig` each store exactly one clause, of size 2, on
arm A — whereas `lizard` arm A's narrowest of 113 clauses is size 6 and its
median is 202. Core extraction narrowed `lizard` 25.2× (median 202 → 8; exact
ratio 202/8 = 25.25, truncated — `../2026-09-27-core-in-loop/README.md` line 39)
to reach {5, 8, 8}; these
three subjects start narrower than that without it. Nothing in the spec predicts
this and it is a single clause each, so it is recorded as an observation, not a
result.

**(e) The Task 4 smoke's shape reproduced at the real budget, and it was not an
artifact.** The smoke run — at a 4,000-node budget, explicitly not quotable,
recorded at `../../plans/2026-09-30-clause-propagation.md:2958` and `:3300` —
read arm B at `unit_node_fraction` 0.501 on 3 clauses against arm A's 0.0035, and Task 4
flagged the risk that this was clause scarcity. At 500,000 nodes the
same shape appears (0.741764 against 0.008238 on the same 3 and 113 clauses),
and §3 settles it as tightness on a normalisation the smoke could not support.
The flag was the right call and the answer went the other way from the worry.

**Nothing was adjusted to reach any of this.** `git diff --stat HEAD --
mcp_harness/` is empty and `grep -c box_pleat mcp_harness/server.py` is 0: no
production code was touched to produce this README, and `probe.json` is the
output of the committed `probe.py` on a clean tree (`dirty` `false`).
