# The incremental vertex index: identity across the corpus, 1.10x–28.15x on dense

**Verdict: the mechanism is sound and the identity evidence is complete (8/8).
Dense wall time on the 8-subject corpus falls from 630.82 s to 109.90 s (5.740x
on the total, 1.095x–28.154x per subject). The claim this supports is §1.1's —
dense is now affordable to MEASURE on more subjects. It is NOT a convergence
claim, and nothing here moves a single subject from "budget-capped" to
"solved".**

## Where every figure comes from

Exactly two artifacts in this directory are quoted, and they are not
interchangeable:

| artifact | what may be quoted from it |
|---|---|
| `ab.json` | **identity** (`sparse_fold_equal`, node counts, variable-sequence digests) and the **visited-vertex** figures. Load-independent. |
| `timing.json` | **every second and every ratio.** Three interleaved repeats per arm, minimum reported, quiet machine. |

Any other number below is labelled inline with the named evidence directory it
is cited from. `ab.json`'s own `dense_secs_*` / `speedup` / `sparse_speedup`
fields are **deliberately not quoted as results** — see §4. Nor is its
top-level **`ceilings`** field: it holds `lizard`'s 1.907 and 3.492 under
subject-free key names (`free_vars_at_alone`, `pick_and_free_vars_at`), and a
ceiling is per subject — 1.362× to 112.913× across this corpus (§5).

Section map to `task-4-brief.md`: 1 = item 1, 2 = item 2, 3 = item 3, **4 = the
contamination finding (not in the brief; required)**, 5 = item 4, 6 = item 5,
7 = item 6, 8 = item 7, 9 = item 8, 10 = item 9.

---

## 1. The question

The predecessor slice (`../2026-09-29-local-csp-profile/`) broke dense
`assign()`'s previously-unmeasured residual open. Cited from that directory:
the residual is **79.57%** of dense wall time; constraint checking
(`violation`) is only **0.33%–1.07%** of total — **0.33%–1.46%** of the
*remainder*, which is where those two endpoints come from — on every
budget-capped row; and
`pick` + `free_vars_at` — variable selection — is **97.72%–99.12%** of the
remainder on the seven budget-capped rows (39.43% on `starfish`, which finishes).
Its `free_vars_at` call counts imply that **at least 90.39%** of the
per-vertex scans return an empty candidate set. `pick()` rescanned every
interior vertex at every node, and nine scans in ten found nothing.

This slice replaces that rescan with watched-literal-style incremental counts:
a vertex is visited only when an incident variable changes state.

**The goal is dense measurable on more subjects, NOT convergence (spec §1.1).**
A subject that becomes 28x cheaper does not thereby converge; it becomes
affordable to measure. Read every figure below through that sentence.

---

## 2. Identity, before any timing

**8 of 8 subjects passed. `identity_passed_count` = 8, `corpus_size` = 8, and
`identity_failures` is empty on every row.** No subject is excluded from the
timing section.

| subject | `sparse_fold_equal` | `dense_nodes_off` | `dense_nodes_on` | digest off | digest on | match | `dense_first_divergence` |
|---|---|---|---|---|---|---|---|
| starfish | true | 6806 | 6806 | `cf6909ed677827c0` | `cf6909ed677827c0` | yes | null |
| lizard | true | 20000 | 20000 | `f506e0d216db9a95` | `f506e0d216db9a95` | yes | null |
| frog | true | 20000 | 20000 | `864da07168199ab5` | `864da07168199ab5` | yes | null |
| horse | true | 20000 | 20000 | `b4bc7d2e90ca18c2` | `b4bc7d2e90ca18c2` | yes | null |
| bird | true | 20000 | 20000 | `de05a8e6f211b13c` | `de05a8e6f211b13c` | yes | null |
| guinea_pig | true | 20000 | 20000 | `45f5d4785d484d73` | `45f5d4785d484d73` | yes | null |
| octopus | true | 20000 | 20000 | `f174320207569e84` | `f174320207569e84` | yes | null |
| dog | true | 20000 | 20000 | `5f64ce2d976f18f9` | `5f64ce2d976f18f9` | yes | null |

**The digest, not the node count, is what makes this meaningful.** Node counts
alone would pass two searches that diverged and later reconverged onto the same
total: seven of the eight rows read exactly 20000/20000 because 20000 is the
*budget*, so on those rows the node count carries almost no information at all.
The digest is over the ordered sequence of chosen variables, so it is equal only
if the on arm made the same decision at every node in the same order.
`dense_first_divergence` is `null` on all eight, which is the same statement
read from the other end: there is no first index at which the two sequences
differ.

`sparse_layers_tried_off` equals `sparse_layers_tried_on` on all eight rows as
well (1, 9, 22, 5, 1, 20, 2, 10), and `sparse_stage_off` = `sparse_stage_on` =
`emit` throughout, so the sparse arms agree on the search path and not merely on
the output fold.

---

## 3. What the index changed mechanically

`visited_per_node_off` is `interior` **by construction** — the off arm's loop
visits every interior vertex at every node, so its figure is not a measurement,
it is the definition of what was replaced. The measured content is entirely in
the on arm. All figures from `ab.json`.

| subject | `interior` = `visited_per_node_off` | `visited_per_node_on` | `visited_fraction_on` | `visited_per_select_on` | `select_calls_per_node_on` |
|---|---|---|---|---|---|
| starfish | 49 | 11.0 | 0.2245 | 19.5 | 0.5635 |
| lizard | 4489 | 208.6 | 0.0465 | 221.1 | 0.9437 |
| frog | 5625 | 331.6 | 0.0590 | 351.0 | 0.9447 |
| horse | 8281 | 499.9 | 0.0604 | 527.7 | 0.9474 |
| bird | 11449 | 548.2 | 0.0479 | 569.0 | 0.9634 |
| guinea_pig | 16129 | 674.3 | 0.0418 | 695.9 | 0.9689 |
| octopus | 21609 | 1104.8 | 0.0511 | 1144.6 | 0.9652 |
| dog | 21609 | 1590.0 | 0.0736 | 1690.1 | 0.9407 |

**On the seven budget-bound subjects the index visits 4.18%–7.36% of the
vertices the rescan visited, per node.** `starfish` visits 22.45%, and it is the
one subject that finishes its search (6,806 nodes, stage `emit`) rather than
hitting the 20,000 budget — with only 49 interior vertices there is little for
an index to skip.

Only `visited_per_node_on` may be compared against `visited_per_node_off` or
turned into a fraction; `visited_per_select_on` is per `select` **call**, and
`select_calls_per_node_on` < 1 on every row because `pick`'s sticky path answers
some nodes without calling `select` at all. `ab.py`'s own docstring records that
confusing the two once produced a wrong reading.

This is the mechanism's own claim, measured: the rescan was ≥90.39% empty
(cited from `../2026-09-29-local-csp-profile/`) and the index skips 92.6%–95.8%
of it on those seven rows (1 − 0.0736 and 1 − 0.0418).

---

## 4. There are two timing runs, and the first one was load-contaminated

**This is a finding, not a footnote.** `ab.json`'s timing columns were taken as
single readings on a loaded machine. `dog`'s sparse off arm read **902.5 s**
there against a committed **537.3 s** for the same subject (cited from
`../2026-09-20-box-pleat/oracle-census/certify.json`, row `dog`, `secs`), with
system load peaking at 12.1 and an unrelated `pytest` running alongside. So
`timing.py` re-ran all 8 subjects with **three interleaved repeats per arm**
(`off,on,off,on,off,on` within each mode), reporting the **minimum**, on a quiet
machine. `timing.json`'s `loadavg` went 3.46 → 1.94 over the run and its own
per-reading load stamps peaked at 10.25 during `lizard` only.

**Three checks say the machine was quiet and the dense ratios were robust:**

1. **The quietness check.** `dog`'s sparse off minimum is **503.38 s**, which is
   503.38 / 537.3 = 0.9369, i.e. **6.31% BELOW** the committed 537.3 s. A
   contaminated machine cannot beat a committed reading.
2. **Within-arm spread.** `spread_max_over_min` on wall time is **≤ 1.019** on
   every arm of every subject except `starfish`, whose four sub-second arms read
   1.014 / 1.063 / 1.083 / 1.077. The worst non-`starfish` spread is `frog`'s
   sparse off arm at 1.019.
3. **Ratio stability, DENSE ONLY.** min-of-3 dense speedup against `ab.json`'s
   single-reading dense speedup: **0.882x–1.007x** across the eight subjects
   (`dog` 5.728/6.498 = 0.882 lowest, `frog` 4.843/4.808 = 1.007 and `horse`
   3.232/3.209 = 1.007 highest).

**Correction to the framing "contamination moved absolute seconds, not ratios":
that is true of the dense ratios and FALSE of the sparse ones.** The same
comparison on sparse spans **0.572x–1.600x** — `dog` 10.577/18.486 = 0.572,
`octopus` 6.028/3.767 = 1.600, `guinea_pig` 30.515/20.383 = 1.497. Load moved
`dog`'s sparse **off** arm (902.5 → 503.38) and `guinea_pig`'s and `octopus`'s
sparse **on** arms (16.51 → 9.08 and 11.05 → 5.76), and both directions change
the ratio. The sparse figures in §6 are therefore the re-run's, and `ab.json`'s
sparse speedups should not be quoted at all.

Consequence: **§§5–7 take every second and every ratio from `timing.json`.**
Identity (§2) and the visited-vertex figures (§3) stay on `ab.json` — identity
is load-independent, so it needed no re-run.

---

## 5. The realised dense speedup, beside its ceiling

Seconds and speedups from `timing.json` (`dense.wall.{off,on}.min`,
`dense.wall_speedup_min`). **The two ceiling columns are cited from
`../2026-09-29-local-csp-profile/`** and recomputed here from its
`profile.json` by its own two formulas:
`1 / (1 - free_vars_at / total_secs)` and
`1 / (1 - (pick + free_vars_at) / total_secs)`.

| subject | off (s) | on (s) | **realised** | `free_vars_at` ceiling | **pair ceiling** | `global_check` % of total | realised / pair ceiling |
|---|---|---|---|---|---|---|---|
| starfish | 0.69 | 0.63 | **1.095x** | 1.216x | 1.362x | 30.23% | 0.80 |
| lizard | 43.51 | 17.77 | **2.449x** | 1.907x | 3.492x | 26.81% | 0.70 |
| frog | 41.84 | 8.64 | **4.843x** | 2.310x | 6.950x | 12.82% | 0.70 |
| horse | 69.93 | 21.64 | **3.232x** | 2.134x | 5.172x | 18.13% | 0.62 |
| bird | 69.26 | 2.46 | **28.154x** | 2.837x | (79.837x) | **0.00%** | (0.35) |
| guinea_pig | 120.55 | 26.29 | **4.585x** | 2.325x | 7.402x | 12.68% | 0.62 |
| octopus | 132.38 | 5.82 | **22.746x** | 2.871x | (112.913x) | **0.00%** | (0.20) |
| dog | 152.66 | 26.65 | **5.728x** | 2.854x | (101.384x) | **0.00%** | (0.06) |
| **total** | **630.82** | **109.90** | **5.740x** | — | — | — | — |

**The spec's "caps at 3.492x" is `lizard`'s ceiling, not the slice's.** Ceilings
are per subject and they span 1.362x (`starfish`) to 112.913x (`octopus`). The mechanism is the
predecessor's own finding: `bird`, `octopus` and `dog` read
`global_check_secs: 0.0` because they never reached a complete candidate inside
20,000 nodes, so ~99% of their total time **is** the `pick`/`free_vars_at` pair
with no layer-check time to floor the ratio. The five subjects that did reject
carry 12.68%–30.23% of total in `global_check`, which caps them at 1.362x–7.402x.

**The three bracketed ceilings are parenthesised on purpose.** Their share of
total is 0.9875, 0.9911 and 0.9901, so `1/(1-x)` is dividing by ~0.01 and the
figure is arithmetic about a near-zero denominator rather than headroom. The
predecessor omitted them from its own headroom table for exactly this reason,
and this README reproduces its values (79.837x, 101.384x, 112.913x) only so that
the *shape* is visible: two orders of magnitude, not a number to plan against.
Treat them as "unfloored", not as that much available headroom.

**Every realised figure is inside its own subject's pair ceiling — all eight.**
`starfish` 1.095 < 1.362, `lizard` 2.449 < 3.492, `frog` 4.843 < 6.950, `horse`
3.232 < 5.172, `guinea_pig` 4.585 < 7.402, and the three unfloored rows are far
inside. That is the check the ceiling exists to support, and it passes.

**Naming the gap.** Realised sits at 0.62–0.80 of the ceiling on the five
floored subjects. A gap must exist: **a ceiling prices removing a component
ENTIRELY, and no real optimisation does that** (spec §5.3). The index does not
delete variable selection; it makes each selection visit 4.18%–7.36% of the
vertices it used to (§3) while still paying index maintenance on every bind and
unbind. Realised at 62–80% of a bound that is unreachable by construction is a
strong result, and **a ceiling is still not a speedup.**

**`dog` is an outlier and it is NOT explained here.** It has
`global_check_secs: 0.0` and an unfloored ceiling like `bird` and `octopus`, yet
it realises only **5.728x** where `bird` gets 28.154x and `octopus` 22.746x. Its
`assign`-only speedup is **24.405x** (`dense.assign_speedup_min`), so the
`assign` phase did move like its siblings and the wall figure is diluted by
something outside `assign` — 152.66 − 131.38 = 21.28 s off-arm and
26.65 − 5.38 = 21.27 s on-arm of non-`assign` wall time, essentially unchanged
by the index. **That is an observation, not a mechanism.** It was not
investigated and no cause is claimed.

---

## 6. Sparse

Sparse cost is what gates corpus size, so it was measured rather than assumed.
All from `timing.json` (`sparse.wall.{off,on}.min`, `sparse.wall_speedup_min`).

| subject | off (s) | on (s) | speedup |
|---|---|---|---|
| starfish | 0.12 | 0.13 | **0.923x** |
| lizard | 6.80 | 0.41 | 16.585x |
| frog | 54.31 | 2.24 | 24.246x |
| horse | 14.40 | 7.25 | 1.986x |
| bird | 3.47 | 1.77 | 1.960x |
| guinea_pig | 277.08 | 9.08 | 30.515x |
| octopus | 34.72 | 5.76 | 6.028x |
| dog | 503.38 | 47.59 | 10.577x |
| **total** | **894.28** | **74.23** | **12.047x** |

**Sparse was expected to be small and it is not: 0.923x to 30.515x.** Two things
must be said plainly.

**`starfish` gets SLOWER: 0.923x.** A real negative, not noise in sign — the
wall arms are 0.12 s off against 0.13 s on, and `sparse.assign_speedup_min` is
0.997x, i.e. the `assign` phase is a wash and the loss is index construction.
Building the index is not free on a subject whose whole sparse compile is
0.13 s. The absolute cost is 0.01 s.

**The large sparse speedups are structural, and the UNEVENNESS is not
explained.** Structural part: sparse has far fewer variables over the same
interior vertex set — on `lizard`, **476** sparse M/V variables against **4,868**
dense (cited from `../2026-09-24-dense-pleats/dense_labelling.json`, row
`lizard`, `sparse_mv` / `dense_mv`) over `interior` = 4,489 vertices. Almost
every vertex is empty, the index skips nearly all of them, and the off arm still
visits all 4,489 at every node. That accounts for *large*. It does **not**
account for why `guinea_pig` reads 30.515x and `horse` 1.986x, and **no
explanation for the unevenness is offered here.** Note also that the sparse arms
all reach stage `emit` with equal `layers_tried`, so they are not comparing
different amounts of work.

---

## 7. What this buys, concretely

This is the slice's actual claim, and it is §1.1's goal: **dense measurable on
more subjects.**

* **The 8-subject dense corpus cost 630.82 s and now costs 109.90 s** — a
  **5.740x** reduction in total wall time. Mean per subject **78.85 s → 13.74 s**
  (630.82/8 and 109.90/8).
* **At the corpus mean, a fixed time budget fits 5.74x as many dense subjects.**
  A 600-second budget fit 600/78.85 = **7.6** subjects; it now fits
  600/13.74 = **43.7**. The wall time the old 8-subject dense arm consumed
  (630.82 s) now buys 630.82/13.74 = **45.9** subjects at the new mean.
* **A distribution-free version of the same statement**, since that mean is
  dominated by `dog` and `guinea_pig`: the most expensive dense subject now
  costs **26.65 s** (`dog`), which is less than the *second cheapest* subject
  cost before (`frog`, 41.84 s). **Five of eight dense off arms exceeded 60 s
  (69.26, 69.93, 120.55, 132.38, 152.66); zero of eight on arms do.**
* **Dense and sparse together: 1525.10 s → 184.13 s**, 8.283x — 25.4 minutes of
  corpus (1525.10/60) down to 3.1 minutes (184.13/60).

**What it does not buy.** Not one subject changed `stage_reached`: the seven
budget-bound rows still read `assign` on both arms in all three repeats, and
`starfish` still reads `emit`. The identity result in §2 guarantees this — the
search makes the *same* decisions, so it stops in the same place. The index buys
throughput on measurement, and nothing else.

---

## 8. What this cannot say

* **Nothing about convergence.** Identity is the point: the on arm explores the
  same tree in the same order and stops at the same node. Zero subjects moved
  from budget-capped to solved. The relevant cap here is the subject's own
  ceiling (1.362x–7.402x on the five floored rows, `lizard`'s 3.492x being the
  spec's reference), and **a ceiling is not a speedup** — it prices deleting a
  component entirely.
* **Nothing about the CEGAR regime.** Cited from
  `../2026-09-29-local-csp-profile/`: the ladder had **3 of 8 subjects at zero
  rejections** (`bird`, `octopus`, `dog` — `materialise` calls 0) and the other
  five at **1–10** (`frog` 1, `horse` 1, `guinea_pig` 1, `starfish` 6, `lizard`
  10). Rejection handling was effectively not exercised, so nothing here prices
  it.
* **Nothing about other node budgets.** Every figure is at budget **20,000**.
  Within these artifacts the one subject that does not hit the budget
  (`starfish`) also has the smallest speedup, but that is confounded with its
  49 interior vertices and is not evidence of a budget trend. Earlier
  small-budget harness readings taken during development are deliberately not
  quoted: they were one subject on one machine and these runs supersede them.
  **Do not extrapolate any ratio here across budgets.**
* **Nothing about the >8-flap wall, `layer_order` confluence, or the serve
  path.** `grep -c box_pleat mcp_harness/server.py` is **0**; this slice does not
  touch the serve path.
* **Nothing about `dog`'s outlier wall ratio** (§5), which is reported and not
  diagnosed, and **nothing about why sparse speedups are so uneven** (§6).

---

## 9. The default-flip recommendation

**Recommendation: yes — flip the flag to default on. The evidence is the
identity result, not the speedup.**

The basis, and only this: **8 of 8 subjects passed identity across the whole
corpus** (§2) — `sparse_fold_equal` true everywhere, dense node counts equal
everywhere, and the variable-sequence digests equal on all eight with
`dense_first_divergence` `null` on all eight. That is the whole corpus, not a
sample, and the digest rules out divergence-and-reconvergence rather than merely
failing to detect it. A flag whose on arm provably makes the same decisions as
its off arm on every subject in the corpus is not a behavioural change to the
search; it is a change to how long the same search takes.

Two things the owner should weigh against that:

* **Leaving an optimisation permanently behind an off-by-default flag means
  paying for the work and never collecting it.** The 5.740x dense and 12.047x
  sparse corpus reductions accrue to nobody while the default is off, and a flag
  nobody sets rots.
* **A flip changes what every dense compile does**, including compiles nobody in
  this slice measured. The corpus is 8 subjects. The one measured regression is
  sparse `starfish` at **0.923x** (§6), which is 0.01 s in absolute terms but is
  a genuine sign change on short compiles, and index construction is the cost
  that will show up on any subject whose whole compile is sub-second.

**The recommendation is evidenced; the decision is the owner's.** Nothing was
adjusted to reach it.

---

## 10. Run metadata

| field | identity run (`ab.json`) | timing run (`timing.json`) |
|---|---|---|
| `measured_utc` | 2026-09-30T05:50:25+00:00 | 2026-09-30T08:07:42+00:00 |
| `commit` | `2a71cd65c8e0bf57d22fc8862f97f2a1133a172a` | `bc8f4e662d50e96db54af77e3b28aef2785d2458` |
| `budget` | 20000 | 20000 |
| estimator | single reading per arm | **min of 3**, `off,on,off,on,off,on` |
| debug channels | `debug_search` on (it instruments the search) | **all off** |
| fixture | — | `docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/data/rule6_serve.json` |
| `loadavg` start → end | not recorded; known contaminated (§4) | 3.46 → 1.94 |
| corpus | 8 subjects, `identity_passed_count` 8 | 8 subjects |

**Instrument blob hashes, unchanged from before their runs:**

* `ab.py` — `d2a7214c938e8e1631c7601f93f0b9d77a3e7270`
* `timing.py` — `fc4432900c64723163a09119b5fc684cbd231d68`

Verified in this worktree with `git hash-object`. `git diff --stat HEAD --
mcp_harness/` is empty: nothing under `mcp_harness/` was touched to produce this
README, and the two instruments and their two JSON outputs are byte-unchanged.

The identity and timing passes are separate runs because the identity pass
instruments the search — you cannot time an instrumented search. That is why
there are two `commit` values and two `measured_utc` values above, and why §4's
split of which artifact answers which question is load-bearing rather than
bookkeeping.
