# S8 gate-retrain: PRE-REGISTERED evaluation

**Written 2026-07-31 BEFORE any model was fitted.** Committed in its own commit,
ahead of the commit that adds the features, so the git history proves the order.
Nothing below may be edited after the first fit; measured results go in the
plan's verdict block and in `RESULTS` at the bottom of this file, appended only.

This document exists because this project's two worst measurement errors were the
same shape as the one available here:

* **S5** reported "achieved strain ≈ 0" as evidence of no slack. Over all edges
  `tmEdgeOptimizer` writes ONE shared strain scalar, which is a uniform rescale
  and provably redundant with scale optimisation — so ≈0 was a **tautology**,
  true by construction of the estimator, not a fact about the trees.
* **S6** scored a prompt A/B with a substring test that matched `"changed"`
  inside `"unchanged"` — the criterion separated, just not into the classes it
  named.

The available error here is bigger than both, and the brief names it: **`n_leaves`
alone is already a strong predictor.** Measured on `feasibility/corpus_wide.jsonl`
(reproduced independently 2026-07-31, see §1), the attempt-0 pack rate is monotone
across essentially the whole range. So a headline AUC that rises when structure
features are added **proves nothing**: the new features are correlated with
`n_leaves`, and a model that got better at reading `n_leaves` off them would post
the same gain. Any comparison that is not conditional on `n_leaves` measures
`n_leaves` twice.

---

## 1. Measured facts this evaluation is built on (verified, not quoted)

`feasibility/corpus_wide.jsonl`, 2600 rows, y = `attempt0_pack`. Reproduced from
the raw file; recomputing `n_leaves` from each row's raw `nodes` matches the
recorded `features.n_leaves` on **2600/2600** rows.

| k (n_leaves) | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9–12 | 13+ |
|---|---|---|---|---|---|---|---|---|---|---|
| rows | 66 | 80 | 169 | 276 | 310 | 280 | 272 | 266 | 451 | 430 |
| positives | 0 | 26 | 152 | 234 | 198 | 51 | 10 | 3 | **2** | **2** |
| rate | .000 | .325 | .899 | .848 | .639 | .182 | .037 | .011 | **.0044** | **.0047** |

* **`perturb_pack` is null on 2600 of 2600 rows.** The corpus has no ladder label.
* All 2600 rows share ONE keyset:
  `{id, source, nodes, pairs, features, attempt0_pack, failure_mode, perturb_pack}`.
  Every structure feature below is therefore backfillable offline over the whole
  corpus with **zero compiles**.
* Sources: `anchored` 1400, `random` 600, `mesh_like` 600.
* **The four positives above k=8 are k=9, 12, 16 and 17** — all `source=random`,
  all with `n_sym_pairs ≤ 1`. They are scattered across the range, not clustered
  at its bottom edge. There is no boundary there to fit.

**Consequence, fixed before fitting: the target band is k ∈ {5, 6, 7}** — 862
rows, 259 positives, rates .639 → .182 → .037. It is the only band with both a
steep gradient and a two-sided positive class. It is also where every scorecard
subject actually serves: quadruped 6, bird 5, humanoid 5, fish 7, insect 7,
dog 6 (`fixtures/scorecard_baseline.jsonl`, post-S7).

---

## 2. The estimator, and why it cannot restate `n_leaves`

**Primary statistic: WITHIN-STRATUM ROC-AUC, strata = exact `n_leaves`.**

For each k, compute AUC over only the rows with that k, using out-of-fold
predicted `p_pack`. Report per-k, with (rows, positives) printed alongside every
number so the reader sees the support.

The property that makes this the right statistic, and the reason it is primary:

> Every row inside a stratum has the **identical** value of `n_leaves`. A model
> that is a function of `n_leaves` alone therefore assigns every row in the
> stratum the **same score**, and its within-stratum AUC is **exactly 0.5** — not
> approximately, not on average, but by construction of the estimator.

So within-stratum AUC above 0.5 is, by construction, information that is not
`n_leaves`. This is the anti-tautology guarantee, and it is the whole reason this
metric was chosen over the headline AUC that S5's and S6's errors would have
survived.

Secondary (reported, never headline): pooled AUC over all rows. It is reported
**only** so a reader can see how much larger it is than the within-k numbers —
that gap IS the `n_leaves` effect, quantified.

**Cross-validation.** 5-fold, stratified on the joint `(k, y)` label so every fold
holds the same class balance and approximately the same k-mix; every row gets
exactly one out-of-fold prediction. *(Approximately, not exactly: any joint class
too small to appear in every fold is collapsed into a per-y catch-all, which
preserves class balance exactly and k balance only approximately — k=9 has ONE
positive in the whole corpus, so no stratification can place it in five folds.
Measured after the collapse: 29 joint classes, none under 5 members, no sklearn
warnings, per-fold positive rate within 0.003 of overall.)* Repeated over **5 seeds** (0–4); report mean ± sd across
seeds. A single hold-out split is refused: k=7 has 10 positives in the whole
corpus and k=8 has 3, so one 20% split puts ~2 and ~0.6 positives in validation
and any number computed from that is noise.

**Arms.** All four trained by the same code path, the same
`RandomForestClassifier(n_estimators=300, class_weight="balanced")`, the same
folds, differing ONLY in the feature columns:

| arm | features |
|---|---|
| `A0_leaves_only` | `n_leaves` alone |
| `A1_shipped` | today's 7: `n_nodes, n_leaves, max_degree, edge_mean, edge_max, edge_min, n_sym_pairs` |
| `A2_shipped_plus_structure` | A1 + the 5 structure features of §3 |
| `A3_structure_only` | the 5 structure features of §3, **without** `n_leaves` |

---

## 3. The structure features (backfilled, zero compiles)

Named by the plan bullet (plan:235-238) and defined here against the code that
already owns each concept, so the feature and the ladder cannot drift apart:

1. **`root_children`** — number of children of the root. (Plan: "root-children".
   Deliberately NOT the hub bound: `rescue_ladder.py:618-623` records that
   `MAX_NORMALIZE_HUBS` is the interior-node count and explicitly *not* root
   degree, and S6 falsified a root-degree rule outright.)
2. **`n_interior`** — interior-node count, root included; i.e.
   `len(rescue_ladder._interior_ids(nodes))`. This is the exact quantity S7
   measured as the entire 9–12-leaf admission gate: **all 35 rejections were the
   hub term** (interior counts of 6–10 against a bound of 3), none was the pair
   or sliver term.
3. **`max_hub_leaves`** — max over interior nodes of that node's LEAF-child
   count. (Plan: "per-hub leaf counts", reduced to a scalar. A hub with many
   leaf children is the flap cluster the packer must satisfy at once.)
4. **`min_interior_edge_ratio`** — min over non-root INTERIOR nodes of
   `length / max(length)`. This is precisely the quantity `contract_slivers`
   thresholds at `SLIVER_RATIO = 0.08` (`rescue_ladder.py:616, 674-677`).
   **Sentinel: `1.0` when the tree has no non-root interior node** — no interior
   edge exists, so no interior sliver is possible, which is the maximally
   non-slivered value. It is a finite float, as `merge_captured.is_trainable`
   requires; a `None` or NaN would silently become NaN in `train_model._matrix`.
5. **`order_canonicality`** — agreement between the row's ACTUAL node list order
   and `rescue_ladder.canonical_order(nodes, pairs)`. Defined as
   `1 - footrule / footrule_max`, where footrule is the Spearman footrule
   distance `sum |rank_actual(i) - rank_canonical(i)|` over node ids and
   `footrule_max = floor(n^2 / 2)` is its maximum, giving a value in [0, 1] with
   1 = exactly canonical. **Sentinel: `0.0` when `canonical_order` returns None**
   (malformed / not-a-tree — the same input on which the ladder skips the rung).

   This is the thesis feature. Today's seven are all order-invariant, while S3
   measured node ORDER as the single biggest rescue lever (45.8% of attempt-0
   pack failures rescued by order restarts alone). If order carries predictive
   signal anywhere, it is here.

---

## 4. PREREQUISITE GATE, checked before any fit

`order_canonicality` can only be measured if the corpus HAS order variance. If
`tree_generator` emits every tree in one fixed construction order, the feature is
a near-constant and the order thesis is **untestable on this corpus** — which is
an answer, not a null result, and must be reported as such rather than dressed up
as "structure features did not help".

**Gate (descriptive, computed on X only, never touching y):** within the k=5–7
band, report each new feature's number of distinct values and its standard
deviation. Any feature whose within-band standard deviation is **0** is dropped
from the arms and reported as UNTESTABLE-ON-THIS-CORPUS with its constant value.

---

## 5. Two controls, in OPPOSITE directions

S6's lesson, stated exactly: *a discrimination control proves a criterion CAN
separate good from bad, it does NOT prove it is right about which is which.* One
control is therefore not enough. Both of these run through the identical harness
as the four arms:

* **`C_POS` (positive control — can the metric SEE a real signal?):** A1 plus one
  synthetic feature that is a deliberately noisy copy of the label (y XOR a
  Bernoulli(0.30) flip). Within-k AUC in the k=5–7 band **MUST rise well above
  A1**. If it does not, the harness is broken and every other number in this
  document is void.
* **`C_NEG` (negative control — is the metric FOOLED by restated `n_leaves`?):**
  A1 plus one synthetic feature that is an exact deterministic function of
  `n_leaves` (`n_leaves ** 2`). Within-k AUC **MUST NOT rise** (it is constant
  inside every stratum, so it carries exactly zero within-stratum information).
  A rise here means the estimator is leaking `n_leaves` and the primary
  comparison is invalid.

`C_NEG` is the control that S5 and S6 both lacked. It is the one that fails
loudly if the tautology reappears.

---

## 6. Decision rule, fixed in advance

**SHIP a new feature order and a new artifact only if ALL of:**

1. `C_POS` rises above A1 by ≥ 0.05 within-k AUC in the k=5–7 band, and `C_NEG`
   moves by < 0.01 in absolute value. *(Harness validity.)*
2. `A2_shipped_plus_structure` beats `A1_shipped` on the **support-weighted mean
   within-k AUC over k ∈ {5,6,7}** by **≥ 0.02**, averaged over the 5 seeds.
3. That improvement has the **same sign in at least 4 of the 5 seeds**.
4. The A2 − A1 delta is **positive at k=6 specifically** — the band's steepest
   stratum and the modal served leaf count (quadruped 6, dog 6).

**Otherwise: NEGATIVE. Ship the harness and the measurement, do NOT ship a new
artifact and do NOT change `FEATURE_ORDER`.** A negative here is the same class of
result as S4's "the composed normalizer rescues zero" and S5's "edge-opt 0 of 9
across 562 arms": those negatives are the most durable things those sessions
produced, and both were only durable because they were reported.

Predictions recorded before the fit, so misses are visible as misses:

| arm / control | prediction (k=5–7 within-k AUC vs A1) | confidence |
|---|---|---|
| `A0_leaves_only` | **exactly 0.500**, all k, all seeds | certain (construction) |
| `C_POS` | large rise, ≥ +0.15 | high |
| `C_NEG` | |Δ| < 0.01 | high |
| `A3_structure_only` | close to A1; structure substitutes for, rather than adds to, the shipped set | medium |
| **`A2` vs `A1`** | **NO SHIP — Δ < 0.02** | **medium-low.** The shipped seven already include `max_degree` and `n_nodes`, which are coarse proxies for `n_interior` and `max_hub_leaves`; the genuinely new axis is `order_canonicality`, and §4's gate may well find the corpus has no order variance to give it. |

---

## 7. What this evaluation does NOT claim

* It says nothing about k > 8. That band has 4 positives in 881 rows and is
  addressed separately, as a ceiling statement, not as a learning target.
* It says nothing about `perturb_pack` / rescue-ladder outcome. The gate trains
  `y = attempt0_pack` (`train_model.py:68`) and that is unchanged here.
* It is offline. It does not, and cannot, show that a changed gate improves
  served bases — the serve path's relationship to the gate is established
  separately in the session's blast-radius analysis.

---

## RESULTS

*(appended after the run; nothing above this line was edited afterwards — see the
git history: the commit adding everything above lands before the commit adding
this section)*

Command, reproducible verbatim:

```
cd mcp_harness && PYTHONPATH=. .venv/bin/python -m feasibility.eval_gate \
    --json-out eval_gate_s8.json
```

Run **twice, independently**; the two JSON reports are **byte-identical**
(md5 `43eba626aad0da588719acc8f408993e`). The harness is deterministic.

### R1. Prerequisite gate (§4): PASSED — the order thesis IS testable here

Within k=5–7 (862 rows), every structure feature has real variance, so none was
dropped and none is reported as untestable:

| feature | distinct | sd | min | max |
|---|---|---|---|---|
| `root_children` | 7 | 1.818 | 1 | 7 |
| `n_interior` | 11 | 2.058 | 1 | 15 |
| `max_hub_leaves` | 7 | 1.775 | 1 | 7 |
| `min_interior_edge_ratio` | 453 | 0.323 | 0.021 | 1.0 |
| **`order_canonicality`** | **89** | **0.198** | **0.25** | **1.0** |

This matters more than a checkbox. The pre-registration flagged that the corpus
might have no order variance at all, in which case the order thesis would be
untestable rather than refuted. **It has variance — 89 distinct values spanning
0.25 to 1.0 — so the order thesis got a fair test, and it lost on the merits.**

### R2. Harness validity: both controls behaved, and the negative one earned its keep

| check | required | measured | |
|---|---|---|---|
| `A0_leaves_only` within-k AUC | exactly 0.500 | **0.500 at every k** | PASS |
| `C_POS_noisy_label` vs A1 | ≥ +0.05 | **+0.0907** | PASS |
| `C_NEG_leaves_squared` vs A1 | \|Δ\| < 0.01 | **−0.0006** | PASS |

**★ The A0 check also justified the aggregation choice, and it did so with a
number.** Under the PRIMARY (per-fold) aggregation, the provably-uninformative
leaves-only model returns exactly 0.500 at every stratum. Under the SECONDARY
(pooled out-of-fold) aggregation, that identical model returns **0.247 at k=8**
and 0.466 at k=3 — a large apparent signal manufactured entirely by two
fold-models disagreeing about the same `n_leaves` value. Pooling first is the
obvious implementation and it would have produced a metric that reports structure
where there is provably none. Both aggregations are in the report so the gap
stays visible.

**`C_NEG` is the control S5 and S6 both lacked.** Feeding the model `n_leaves`
squared — an exact function of the stratum, i.e. the tautology in its purest
form — moved the band figure by −0.0006. The estimator cannot be made to look
better by restating `n_leaves`.

**What that licenses, stated precisely — an earlier draft got it wrong.** It
establishes that any effect the estimator reports is **not a re-measurement of
`n_leaves`**. It establishes *nothing* about whether the +0.0053 point estimate
is distinguishable from noise, and R3/R6 say it is not. The earlier draft read
this control as licensing "a real (if small) structural effect", which both
overstates the control and contradicts R3's own "indistinguishable from zero"
two paragraphs later. Caught by the re-run statistical lens.

### R3. The arms — within-k AUC (primary), 5 seeds × 5 folds, support-weighted

| arm | k=3 | k=4 | k=5 | k=6 | k=7 | k=8 | band (5–7) | Δ vs A1 |
|---|---|---|---|---|---|---|---|---|
| `A0_leaves_only` | .500 | .500 | .500 | .500 | .500 | .500 | .5000 | −.1495 |
| `A1_shipped` | .605 | .715 | **.747** | **.513** | **.432** | .950* | .6495 | — |
| `A2_shipped_plus_structure` | .716 | .763 | .753 | .534 | .365 | .920* | .6548 | **+.0053** |
| `A3_structure_only` | .544 | .770 | .682 | .550 | .304 | .841* | .6123 | −.0372 |
| `C_POS_noisy_label` | .727 | .780 | .794 | .669 | .603 | .957* | .7402 | +.0907 |
| `C_NEG_leaves_squared` | .618 | .714 | .745 | .517 | .428 | .939* | .6489 | −.0006 |

\* k=8 has **3 positives in 266 rows**. Its AUC is not a measurement and no
conclusion here rests on it; it is printed only so its support is visible
alongside it.

Per-seed band deltas (A2 − A1): `+.0109, +.0108, −.0073, −.0044, +.0164` —
**positive in 3 of 5 seeds.**

**★ The across-seed dispersion §2 asked for, which an earlier draft of this
section omitted (caught by adversarial review):**

| | mean | sd |
|---|---|---|
| `A1_shipped` band | +0.6495 | 0.0101 |
| `A2_shipped_plus_structure` band | +0.6548 | 0.0166 |
| **A2 − A1** | **+0.0053** | **0.0104** |

**The sd of the effect is TWICE its mean.** The structure-feature delta is not
merely below the pre-registered +0.02 bar — it is statistically indistinguishable
from zero on this corpus. That is a materially stronger statement than "it missed
the bar", and it is the number the protocol asked for, so its omission from the
first draft understated the result rather than overstating it.

### R4. VERDICT: **NO SHIP** — matching the pre-registered prediction

| pre-registered check | result |
|---|---|
| harness: A0 = 0.500 | **PASS** |
| `C_POS` rises ≥ 0.05 | **PASS** |
| `C_NEG` flat < 0.01 | **PASS** |
| A2 beats A1 by ≥ 0.02 | **FAIL** (+0.0053) |
| sign-consistent in ≥4/5 seeds | **FAIL** (3/5) |
| positive at k=6 | PASS (+0.021) |

`FEATURE_ORDER` does not move. No new `gate.joblib` is fitted or shipped. The
five-member lockstep is untouched. `structure_features.py` stays as the measured
evidence, with `eval_gate.py` as its live consumer — it is not dormant serve-path
code behind a flag, which is what the plan's edge-opt verdict bans.

### R4b. ★ PREDICTED vs ACTUAL — including the two MISSES

S7's rule, applied to myself: *both misses are reported as misses.* An earlier
draft of this section reported only the decision-rule PASS/FAIL and quietly
omitted that two of the five §6 predictions were wrong. Adversarial review caught
the omission.

| § 6 prediction | predicted | actual | verdict |
|---|---|---|---|
| `A0_leaves_only` exactly 0.500 | 0.500, all k, all seeds | 0.500 everywhere | **HIT** |
| `C_POS` rise | **≥ +0.15** | **+0.0907** | **MISS** |
| `C_NEG` movement | \|Δ\| < 0.01 | −0.0006 | **HIT** |
| `A3_structure_only` | "close to A1" | **−0.0372** | **MISS** |
| `A2` vs `A1` | NO SHIP, Δ < 0.02 | +0.0053, NO SHIP | **HIT** |

**Why the `C_POS` miss matters and is not a technicality.** The decision rule's
harness-validity bar was ≥ +0.05 and +0.0907 clears it, which is why the run
reports PASS — but the *prediction* was ≥ +0.15, and it was wrong by a wide
margin. The reason is informative: a feature that is 70% accurate about y still
carries far less within-stratum signal than intuition suggests once the model
must find it among seven correlated columns under class-balanced bagging. That is
a fact about how much signal this estimator can register **at all**, and it makes
the small absolute numbers elsewhere (k=6 .513) easier to read: this metric does
not hand out large values cheaply.

**The `A3` miss** points the same way — structure features alone are meaningfully
WORSE than the shipped seven (−0.0372), not "close". Whatever the shipped set is
doing at k=5, the structure block does not reproduce it.

The §6 headline prediction was **NO SHIP, medium-low confidence**, reasoned from
the shipped set already containing coarse proxies (`max_degree`, `n_nodes`) for
`n_interior` and `max_hub_leaves`. That reasoning is **half-vindicated and half
wrong**: the prediction hit, but the stated hedge — that §4 would find no order
variance — did NOT happen (R1). The order thesis was fully testable and simply
did not pay.

### R5. ★ THE FINDING THIS EVALUATION WAS NOT LOOKING FOR

**Conditional on leaf count, the shipped gate is INDISTINGUISHABLE FROM CHANCE
exactly where the product lives.**

| k | A1 within-k AUC | permutation p vs 0.5 | 95% CI | who serves here |
|---|---|---|---|---|
| 5 | **0.747** | **<0.0005** | [0.691, 0.798] | bird (5), humanoid (5) |
| 6 | **0.513** | 0.753 | [0.432, 0.589] | quadruped (6), dog (6) |
| 7 | **0.432** | 0.408 | [0.282, 0.592] | fish (7), insect (7) |

The band figure of 0.6495 is carried almost entirely by k=5 — measured, k=5 holds
60.8% of the pair weight, 69.9% of the band level, and **100.4% of the band's
excess over 0.5**. At k=6 and k=7 the gate is statistically indistinguishable
from a coin flip. Adding structure features does not repair this.

*(An earlier draft said "at or below chance" and "at k=7 it is BELOW one". The
directional word is an overclaim: with TEN positives against 262 negatives the
null sd of this statistic is 0.083, so 0.432 sits 0.8σ from chance and its CI
comfortably covers 0.5. Caught by the re-run statistical lens. The section's
actual conclusion — "very little signal, and none of it at k=6–7" — is exactly
what "indistinguishable from chance at both" supports, so the finding survives;
only the word "below" had to go.)*

This is invisible to any pooled metric. Pooled over all rows the model looks
respectable, because `n_leaves` does the work — and `n_leaves` is exactly the
thing the gate does not need a model to know. **The honest reading is that the
Tier 2.5 gate is, today, close to an `n_leaves` lookup table**, and that the
useful next question is not "which features" but "what signal exists at fixed
leaf count at all" — for which the answer on this corpus, across twelve features
including four purpose-built structural ones and one order-sensitive one, is:
very little, and none of it at k=6–7.

That is a durable negative of the same family as S4's "the composed normalizer
rescues zero" and S5's "edge-opt 0 of 9 across 562 arms". It is stated here so
the next session does not spend its budget adding a thirteenth feature.

---

## R6. ★ INDEPENDENT STATISTICAL AUDIT (adversarial, re-run after the first
## attempt died mid-response)

The lens attacking this document's central claim died with an API error on the
first review pass, and the workflow's own dead-agent detector failed to notice
(see the plan's S8 block). It was re-run rather than left as a gap. What it
found, in both directions:

### R6a. What reproduced

* **Every number in R1–R4b reproduces exactly** from `eval_gate_s8.run1.json`:
  the five variance figures, **all 36 arm-table cells**, all six band figures,
  all six deltas, the five per-seed deltas, the three mean/sd rows, the pooled-A0
  0.247/0.466 contrast, the +0.021 at k=6, and all six decision checks.
* **The exactly-0.5 guarantee holds at ELEVEN strata, not just the six printed**
  (k = 2,3,4,5,6,7,8,9,12,16,17). An independent re-implementation of the
  statistic as a pooled Mann-Whitney concordance matches the committed JSON to
  **1e-10** on every arm × stratum.
* `_fold_labels` does not leak (labels drive only the split): 29 classes, min 7
  members, no sklearn warning, per-fold positive-rate max deviation 0.0031.
* Sharing one `splits` list across arms is a **correct paired design**, and the
  `C_POS` noise stream (PCG64, seed 1000+s) is uncorrelated with the fold shuffle
  (MT19937, seed s): mean |r| 0.0165 against a 0.0196 chance level over 200 seeds.
* k=5's 0.747 is real: permutation p < 0.0005, CI [0.691, 0.798].
* "Carried almost entirely by k=5" is, if anything, **understated**.

### R6b. What did not — three overclaims, corrected above and here

1. **§2/§6 said "support-weighted" without defining the weights, and the SIGN of
   the headline delta flips with the reading.** The code uses pair counts
   (`n_pos * n_neg`); under row counts or an unweighted mean over k the A2−A1
   delta is **negative**:

   | weighting | A1 band | A2 band | A2 − A1 |
   |---|---|---|---|
   | pairs `n_pos*n_neg` (as implemented) | 0.6495 | 0.6548 | **+0.0053** |
   | rows | 0.5716 | 0.5593 | **−0.0123** |
   | positives | 0.6888 | 0.6947 | +0.0059 |
   | unweighted over k | 0.5640 | 0.5505 | **−0.0134** |

   A pre-registration exists to pin the estimator before the fit, and this one
   clause was left open. Two things limit the damage and both are checked: the
   **NO SHIP verdict is identical under all four readings** (none reaches
   +0.02), and the implemented pair-weighting is the defensible choice —
   verified numerically to equal the pooled Mann-Whitney concordance over all
   within-fold-within-stratum pairs. **But the sign of +0.0053 is a weighting
   artifact and no prose may lean on it.**
2. **"Below chance at k=7" was unsupported** — corrected in R5.
3. **R2's "a real (if small) structural effect" contradicted R3** — corrected in
   R2. The row bootstrap (scores held fixed, so a LOWER bound on true
   uncertainty) gives A2−A1 = +0.0053, CI **[−0.0197, +0.0308]**, P(>0) = 0.679.
   A3−A1 = −0.0372, CI [−0.0878, +0.0140] — so R4b's self-scored A3 "MISS" is
   itself not distinguishable from zero, and is downgraded to *directionally
   wrong, statistically silent*.

### R6c. ★ The study is underpowered relative to its own bar, and says so

The row-bootstrap SE of the headline delta is **0.0136**, so the pre-registered
+0.02 threshold sits at **1.47 SE** — a truly-zero effect had a **7.0%** chance
of clearing it. The rule's `positive_at_k6` criterion PASSED on +0.0205 with CI
[−0.035, +0.077], i.e. a coin flip. And the rule has **no k=7 check at all**,
where A2 degrades by **−0.0666 with P(>0) = 0.039** — the most nearly-significant
result in the entire study, and it points *against* the structure features.

None of this changes the verdict; all of it changes how much the verdict is
worth. **The correct summary is: structure features show no detectable benefit,
the study could not have detected a small one, and the only near-significant
signal in it is a degradation at k=7.** A future attempt needs more positives at
k=6–7, not more features — and it should fix the weighting clause before it
starts.
