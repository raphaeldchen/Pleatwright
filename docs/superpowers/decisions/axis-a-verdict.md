# Axis A -- may the VLM tree judge be used as a metric?

**Unit J1.** Status of this file when first committed: **PRE-REGISTRATION ONLY.**
Everything below the pre-registration line was written **before a single billed
call was made**, and the commit that contains it is the proof of ordering. The
results and the verdict are appended afterwards, in a later commit, without
editing the bar.

> A bar written after seeing the numbers is not a bar.

---

## 1. What is being decided

`mcp_harness/vlm_judge.py` (PR #130) scores a Metric Tree against the prompt or
subject name that asked for it, using a COrigami-derived rubric at `N_SAMPLES =
4`, `TEMPERATURE = 1.0`. It is ADVISORY by construction: `authority ==
"advisory"`, `_assert_advisory_shape` refuses any gate-shaped key at any depth,
and `base_verdict` never reads it.

The extraction-fidelity wave wants to know whether it may be **steered by** --
that is, whether a score from it may be read as evidence that one tree is
better than another.

### What was already established, and what was not

Measured on three live subjects plus one fixture: octopus **0.197**, lizard
**0.427**, water bear **0.550**, quadruped fixture **0.450**.

* ESTABLISHED -- the free-text `reasons` are specific and verifiable. The judge
  named the missing hind-limb pair, the arm shortfall and the absent mantle, and
  independently rediscovered two defects the deterministic instrumentation had
  found. A constant-scorer cannot do that.
* NOT ESTABLISHED -- that it recognises a GOOD tree. Every tree ever shown to it
  was broken and every score landed below 0.6. Until a good tree is shown to it,
  a low score is not interpretable.
* NOT ESTABLISHED -- that it reads the subject at all. Holding a tree fixed and
  changing only `subject.name` had never been run.
* MEASURED BLIND SPOT -- it scored the water bear HIGHEST, and that mesh is a
  literal bear. An 8-leaf tree in four pairs genuinely IS tardigrade-shaped.
  Axis A ranks tree-level damage and cannot see mesh substitution. Nothing in
  this unit changes that; it is a permanent property of judging the tree.

### The precision bar, and why it is 0.169

`_agreement` is `1 - 2 * pstdev` (`vlm_judge.py:654-668`), so it **inverts**:
every recorded agreement carries the sample spread that produced it. At N=4 the
95% CI on a score is **+/-0.064** (agreement 0.93) to **+/-0.119** (agreement
0.87), giving a least significant difference of **0.091 (best) to 0.169
(worst)**.

**This unit uses 0.169.** Against the four previously measured subjects only
`octopus` separates from anything: water bear vs lizard (0.123), water bear vs
quadruped (0.100) and quadruped vs lizard (0.023) are all inside the noise. A
judge that always returned 0.4 would be indistinguishable from three of the four
readings. Scores are emitted to six decimals against an interval of +/-0.06 to
+/-0.12 -- roughly two orders of magnitude of false precision. Six decimals are
carried in the tables below **only** because the emitter produces them; no
claim in this document rests on more than the second.

---

## 2. The statistic the bar is set on

`CRITERIA` (`vlm_judge.py:153-164`) weights `appendage_count 5`, `topology 4`,
`proportionality 3`, `differentiation 2`, `aesthetic_refinement 1` over
`_WEIGHT_TOTAL = 15`. So **40% of `overall` is the bottom three**, and
`aesthetic_refinement` -- "Are the folds sharp and the symmetry balanced?" -- is
**unanswerable by construction**: `SYSTEM_PROMPT` tells the judge it will never
be shown a crease pattern or a folded model, which are the only artefacts in
which a fold can be sharp or a symmetry can be balanced. A bar on `overall`
therefore spends a seventh of its weight on a question the judge is forbidden
from having evidence for.

The bar is set on the **anatomy score**, the top two criteria renormalised:

```
anatomy = (5 * appendage_count + 4 * topology) / 9        # in [0, 1]
```

`overall` is reported beside it in every table, as a consequence, never as the
gate. (`probe_judge_battery.anatomy_score`.)

---

## 3. PRE-REGISTERED BARS

Fixed before the first billed call. Three gates, each independently reportable.

### Gate A -- SEPARATION (the handoff's bar, restated on the anatomy score)

> The confound-matched broken quadruped must score **below every one of the four
> confound-matched good trees by more than 0.169** on `anatomy`.

Formally: `min(anatomy of the four good arms) - anatomy(broken arm) > 0.169`.

**If Gate A fails, axis A is not usable as a metric and this session must not
steer by it.** That is the primary decision this file exists to record.

### Gate B -- RECOGNITION (the gap the handoff named, made testable)

> The **median `anatomy` of the four confound-matched good trees must be
> >= 0.80**.

Gate A alone can be met with `good = 0.45, broken = 0.20`, which would still
mean the judge never scores good work high -- and "a low score is not
interpretable" would survive the experiment intact. Gate B is the half of the
question that has never been asked.

0.80 is inherited from the handoff's proposed bar; it is moved from `overall`
to `anatomy` for the reason in section 2, which makes it **harder**, not easier,
because it removes the criterion the judge cannot answer and the two it answers
least confidently.

### Gate C -- SUBJECT SENSITIVITY (the diagnostic, run regardless of A and B)

Over the 5x5 swap matrix (5 committed trees x 5 subject names, diagonal re-run
in the same batch):

> `mean(anatomy of the 5 diagonal cells) - mean(anatomy of the 20 off-diagonal
> cells) > 0.169`, **and** the diagonal cell is the maximum of its own row for
> at least **4 of the 5 rows**.

0.169 is a per-comparison least significant difference and is therefore
**conservative** when applied to a mean over 5 or 20 cells; using it anyway is
deliberate.

A partial collapse is expected and is not a failure of the design: some
off-diagonal pairs are genuinely close (a quadruped tree read as a humanoid
shares four limbs and a head). The row-max clause is what distinguishes "reads
the subject" from "reads only tree size".

### Verdict rule -- fixed in advance

| A | B | C | verdict |
|---|---|---|---|
| pass | pass | pass | **usable as an absolute metric**, at 0.169 resolution |
| pass | fail | pass | **usable for RANKING only** -- a score may order two trees, never certify one |
| pass | * | fail | **usable for RANKING only, and only within one subject** -- it is not reading the subject |
| **fail** | * | * | **NOT USABLE.** Do not steer by it. Read the `reasons` as prose and nothing else |

In every cell of that table the `reasons` remain usable as prose: they are the
part that is established, and they are quoted verbatim in the results.

---

## 4. The confounds that would have made this uninterpretable

`build_payload` (`vlm_judge.py:353`) exposes exactly **nine** blob fields:
`subject.name`, `subject.prompt`, `serve.served_tree`,
`serve.leaf_labels[*].label`, `serve.leaf_labels[*].basis`, `serve.pairs`,
`serve.stub_flaps` (falling back to `serve.stubs`), `serve.served_leaves`,
`serve.served_fidelity`. Judged as-is, the two arms of Gate A differ in **five**
of those nine for reasons that have nothing to do with tree quality:

| field | raw good arm (`body_plans`) | raw broken arm (committed fixture) | control applied |
|---|---|---|---|
| `leaf_labels` | absent -- every leaf renders `UNLABELLED (geometry gave no name)` | present, extractor-derived | labels **synthesised** from `body_plans._PLANS[...]["labels"]` on the good arms and hand-authored on the broken arm, from one shared vocabulary, with one shared `basis` string on every arm |
| `stub_flaps` | absent | `5` -- fires an extra "count them against APPENDAGE COUNT" paragraph | forced to **0 on every arm**, so the paragraph fires nowhere |
| `served_leaves` | absent | `2` | set to the arm's own leaf count on every arm (derivable from the tree, so it leaks nothing) |
| `served_fidelity` | absent | `0.3333` | set to **1.0 on every arm, including the broken one** -- a deliberate lie in the broken arm's favour, so a low broken score cannot be read off a number instead of the tree |
| `subject.prompt` | absent | `null` | a real prompt on every arm |

Two further controls:

* **The broken arm is re-run in the same batch**, so model or temperature drift
  cannot enter as signal. No number in the Gate A table is inherited from an
  earlier run.
* **Every arm is run twice, labelled and labels-stripped.** Labels naming a
  "head" and a "tail" assert flaps the tree alone does not name. If the
  separation survives with `leaf_labels` empty on all arms, it is the tree.

The swap matrix carries its own control by construction: within one row the
tree, the labels, the pairs, the stub count and the fidelity are **byte-
identical** and only `subject.name` and `subject.prompt` move.

---

## 5. Experiment 3 -- the VISIBILITY screen (not a vacuity screen)

`prompt_digest` (`vlm_judge.py:452-458`) hashes `SYSTEM_PROMPT || \x00 ||
user_text`. Anything outside the nine visible fields renders a **byte-identical**
prompt, so a benchmark row mutating it is a tautology wearing a measurement's
clothes.

The screen requires **every benchmark mutant to move `prompt_digest`**, asserted
in this unit's own tests, at zero API cost.

**It is a VISIBILITY screen and it must not be called a vacuity screen.** It
proves a mutant is *visible*; it proves nothing about whether the score that
comes back means anything. The handoff notes the limit itself: 12th-decimal
float drift is visible (`edge_length` renders RAW while
`path_length_from_root` rounds to 6 dp, and the committed quadruped already
ships `0.33206800000000003`), so "visible" is a floor far below "meaningful".

Per COORDINATION.md section 4.1 the unit also ships **required-fail inputs it
must score as failing**:

1. `test_required_fail_an_invisible_mutant_is_reported_invisible` -- mutating
   `serve.leaf_labels[*].position` (the 3-D coordinates: the most
   anatomical-looking field in the blob) must be reported INVISIBLE. A screen
   that cannot report a failure is not a screen.
2. `test_required_fail_the_separation_gate_refuses_two_identical_arms` -- the
   Gate A evaluator, handed the same judgement as both arms, must report FAIL.
   A gate that passes on a null comparison is vacuous.

---

## 6. Settled in writing -- the bird contradiction

`fixtures/anatomy_reference.json` pins `bird: reference_count 4`, and the
committed bird blob serves exactly 4 leaves at `served_fidelity 1.0` -- perfect
by that label. The recorded judge reply says *"Four appendages where a bird
needs six"* and marks it down for missing legs.

**The judge is right and `anatomy_reference.json` is not ground truth.** A bird
has two wings, two legs, a head and a tail: six appendages. `body_plans.py`'s
own `bird` template -- hand-authored, measured to pack, and the positive
control's bird arm -- is *"2 wings + 2 legs + head + tail"*, six leaves. The
repo's two internal authorities disagree with each other, and the one that
agrees with a biologist is the judge.

`anatomy_reference.json`'s own `_meta` says what it is: `reference_count = R,
the leaf count of the widest leaf-count-vs-prune plateau`. That is
**`reference_feature_count`'s past output over the committed meshes** -- a
property of this extractor on this mesh at this voxel, not a fact about birds.
Scoring the judge against it would mark it WRONG for its most obviously correct
criticism, and would re-close the very loop this wave exists to open: a system
graded against a measure derived from its own output.

**Ruling, binding on this unit:**

1. Axis A is **never** scored against `anatomy_reference.json`. No gate in
   section 3 reads it, and `served_fidelity` -- which is derived from it -- is
   held CONSTANT across both arms of Gate A precisely so it cannot contribute.
2. The positive control's ground truth is `body_plans._PLANS`: four
   hand-authored, anatomically correct, measured-to-pack trees. Their
   correctness is a design fact, not an extractor output.
3. Sibling unit C1 owns the replacement (`fixtures/anatomy_expectation.json`,
   prompt-keyed) and the relabelling of `anatomy_reference.json` as
   "extraction-derived, NOT ground truth" (user decision D1). This unit records
   the ruling and touches neither file.
4. If a future reader wants a single sentence: **`reference_count` answers "how
   many leaves did this extractor find?", not "how many appendages does this
   animal have?" -- and axis A was asked the second question.**

---

## 7. NOTHING IS TUNED TO PLEASE THE JUDGE

Axis A was validated on the same three subjects this wave touches. Optimising
against it there would stop it being an independent check -- and that is
precisely the closed loop this wave exists to repair, rebuilt one level up.

This unit therefore changes **no** production code. `vlm_judge.py`,
`judge_live.py`, `base_report.py`, `base_eval.py`, `body_plans.py` and
`SYSTEM_PROMPT` are untouched, so the digests of the pre-existing replay corpus
cannot move. The unit adds a probe, a corpus of recorded replies, tests, and
this document. If a gate fails, the recorded outcome is "axis A is not usable";
no knob is turned to make it pass.

---

## 8. Budget, and the corrected call counts

The handoff's counts were miscounted. `N_SAMPLES = 4` and there are exactly
four body plans.

| experiment | arms | calls | note |
|---|---|---|---|
| E1 positive control, labelled | 4 good + 1 broken | 20 | handoff said "24 calls"; 4 plans x 4 samples is 16, and the broken arm re-run in the same batch makes 20 |
| E1 positive control, labels stripped | the same 5 trees | 20 | the label confound, measured rather than argued |
| E2 swap matrix | 5 trees x 5 names | 100 | handoff said "80"; that counts only the off-diagonal, and the diagonal MUST be re-run in the same batch or model drift enters as signal |
| E3 visibility screen | -- | **0** | mechanical, offline |
| **total** | | **140** | ~1.2 USD at `claude-sonnet-5` |

**Actually billed: 140, exactly as budgeted.** 4 of them were a one-arm smoke of
the transport (`--only e1_good_bird`) run minutes before the batch, on the same
model and settings, and its result was kept rather than re-billed --
`e1_good_bird` is therefore the one arm not recorded inside the contiguous E1
run. Disclosed rather than re-run: re-running an arm after seeing its number is
the shape the pre-registration exists to forbid, and 0.169 is far wider than any
drift a two-minute gap could introduce. Every other arm, including **both**
broken arms, was billed inside its own experiment's single batch.

---

## 9. Where the recorded replies live, and why not in `replay.json`

The battery's replies are recorded to **`mcp_harness/fixtures/vlm_judge/battery.json`**,
a second corpus in the directory this unit already owns exclusively. It is NOT
appended to `replay.json`, and the reason is structural rather than
preferential:

`replay.json`'s case schema carries `"blob": "<path>"`, and both
`vlm_judge.rekey_fixture` (`:871-892`) and
`test_the_replay_fixture_digests_are_current` **load that file from disk** for
every case. Appending 35 battery cases would require committing 35 blob FILES,
25 of which are the five committed `fixtures/base_eval/*.json` blobs with one
field changed. That is a worse artifact than a second corpus, and it would put a
copy of the base-eval fixtures under a second path where a future regeneration
would silently miss them.

`battery.json` instead keys each case to a **deterministic builder**
(`probe_judge_battery.build_case(name)`), so a case is reproduced from the
committed body plans and the committed base-eval blobs rather than duplicated.
It keeps every property that matters:

* `vlm_judge.ReplayClient` consumes it unchanged -- it takes a dict or a path
  and needs only `cases[].prompt_digest` and `cases[].replies`.
* Staleness is guarded the same way, by rebuilding every case and comparing
  digests (`test_the_battery_corpus_digests_are_current`).
* The sanctioned repair has an exact analogue,
  `probe_judge_battery.rekey_battery`, which rewrites digests and **never**
  touches a recorded reply -- so a prompt change cannot be laundered into a
  different score.
* `replay.json` is left byte-identical, so `vlm_judge.rekey_fixture` keeps
  working for the corpus it was written for, and every pre-existing test stays
  green untouched.

Conflict avoidance -- the reason the brief made this one unit -- is unaffected:
one unit is still the only writer anywhere in `fixtures/vlm_judge/`.

---

## 10. Prior art (CLAUDE.md section 0)

**Surveyed**

* COrigami (arXiv:2606.26299) -- rubric worth +8.5 accuracy points over a naive
  prompt; N=4 self-consistency beats N=16; a larger model was a worse judge;
  pairwise comparison beats absolute scoring (0.811 vs 0.766).
* GPTeval3D (arXiv:2401.04092) -- VLM-over-renders as a human-aligned evaluator
  of a generated asset against its prompt.
* GamiBench / ORIGAMISPACE / OrigamiBench -- frontier VLMs near 43/100 on
  crease-pattern comprehension; GPT-5 flags VALID folds impossible 24.6-25.0% of
  the time.
* Pre-registration and positive/negative controls as the standard defence
  against an LLM-judge that has only ever been shown failures.

**Adapted**

* COrigami's rubric and N=4 -> **already shipped** as `vlm_judge.CRITERIA` and
  `vlm_judge.N_SAMPLES`. This unit adds none of it and changes none of it.
* COrigami's weighting -> `probe_judge_battery.anatomy_score`, which reads the
  weights out of `vlm_judge.CRITERIA` rather than restating them, so a rubric
  edit cannot silently desynchronise the bar.
* GamiBench's false-veto rate -> the reason every gate here is a REPORT and the
  judge stays advisory; nothing in this unit can change what is served.
* Pre-registration -> section 3, committed before the first call.

**Consciously rejected**

* **Pairwise comparison**, which COrigami measures as better (0.811 vs 0.766).
  Rejected for this unit: it is a change to `vlm_judge.py`'s prompt, which would
  invalidate every replay digest in the corpus, and the question here is whether
  the SHIPPED absolute scorer is usable -- replacing it would answer a different
  question. Recorded as the obvious follow-up, exactly as `vlm_judge.py:72-76`
  already records it.
* **Raising `N_SAMPLES` to shrink the +/-0.169 interval.** COrigami measured
  N=16 as WORSE than N=4 (0.741 vs 0.766). Buying precision by contradicting the
  only measurement anyone has would be trading a known accuracy loss for an
  unmeasured variance gain.
* **Scoring axis A against `anatomy_reference.json`.** Section 6.
* **Showing the judge a folded base or a crease pattern.** Measured dead ends in
  this repo (PR #78; three independent benchmarks). Never re-propose.

---

<!-- ===================== END OF PRE-REGISTRATION ===================== -->
<!-- Everything above this line was committed before the first billed call
     as 804e561, "docs(axis-a): PRE-REGISTER the bar before any billed call".
     Nothing above this line was edited afterwards. -->

# RESULTS

Measured 2026-08-21. Model `claude-sonnet-5`, `N_SAMPLES = 4`,
`TEMPERATURE = 1.0`, text-only content on every arm. The model and temperature
are **captured in the corpus** as `recorded_with`, read off the client that did
the recording, and `run_cases` refuses to append arms billed against a different
model -- a corpus mixing two models cannot support any gate here, because every
gate compares arms to each other.

Every reply is recorded in `mcp_harness/fixtures/vlm_judge/battery.json` and
replays offline with no network and no key.

Reproduce any table with, from `mcp_harness/`:

```
PYTHONPATH=.:tests .venv/bin/python probe_judge_battery.py --report --screen
```

## R1. E1 -- POSITIVE CONTROL

`anatomy` is the gated statistic; `app` and `top` are the two criteria it is
built from; `overall` and `agr` (agreement) are reported, never gated. Every arm
parsed 4 of 4 samples.

### LABELLED (labels synthesised from `body_plans`, one shared basis)

| arm | anatomy | app | top | overall | agreement |
|---|---|---|---|---|---|
| `e1_good_quadruped` | **0.972222** | 1.000 | 0.938 | 0.878333 | 0.953 |
| `e1_good_humanoid` | **0.906944** | 0.963 | 0.838 | 0.778333 | 0.910 |
| `e1_good_bird` | **0.891667** | 0.975 | 0.787 | 0.807500 | 0.962 |
| `e1_good_insect` | **0.775000** | 0.725 | 0.838 | 0.750000 | 0.878 |
| `e1_broken_quadruped` | **0.098611** | 0.087 | 0.113 | 0.120834 | 0.951 |

* **GATE A -- PASS.** Worst good arm `e1_good_insect` 0.775000, broken 0.098611,
  separation **+0.676389** against a bar of 0.169. **Four times the least
  significant difference**, and the *narrowest* of the four good-vs-broken gaps.
* **GATE B -- PASS.** Median good `anatomy` **0.899305** against a bar of 0.80.

### LABELS STRIPPED (`leaf_labels = {}` on all five arms)

| arm | anatomy | app | top | overall | agreement |
|---|---|---|---|---|---|
| `e1_good_quadruped_nolabels` | **0.938889** | 1.000 | 0.863 | 0.791667 | 0.930 |
| `e1_good_humanoid_nolabels` | **0.837500** | 0.938 | 0.713 | 0.723333 | 0.871 |
| `e1_good_bird_nolabels` | **0.795833** | 0.912 | 0.650 | 0.720000 | 0.921 |
| `e1_good_insect_nolabels` | **0.613889** | 0.775 | 0.412 | 0.571666 | 0.917 |
| `e1_broken_quadruped_nolabels` | **0.086111** | 0.075 | 0.100 | 0.093333 | 0.976 |

* **GATE A -- PASS.** separation **+0.527778**. **The separation survives with
  no labels on any arm**, which is the strongest available evidence that it is
  the TREE being read and not the anatomical nouns attached to it.
* **GATE B -- PASS.** Median **0.816666**.

### What stripping the labels costs, per subject

| subject | labelled | stripped | delta | > LSD 0.169? |
|---|---|---|---|---|
| quadruped | 0.972222 | 0.938889 | -0.033333 | no |
| humanoid | 0.906944 | 0.837500 | -0.069444 | no |
| bird | 0.891667 | 0.795833 | -0.095834 | no |
| insect | 0.775000 | 0.613889 | -0.161111 | **no** (0.161 < 0.169, but only just) |
| broken | 0.098611 | 0.086111 | -0.012500 | no |

**No single label delta clears the noise bar**, so "the labels are doing the
work" is not supported.

One pattern in the sub-scores IS worth recording, because it is consistent
across all four good arms and one arm of it is large: **stripping labels costs
`topology` far more than `appendage_count`.**

| subject | topology labelled -> stripped | appendage_count labelled -> stripped |
|---|---|---|
| quadruped | 0.938 -> 0.863 (-0.075) | 1.000 -> 1.000 (0.000) |
| humanoid | 0.838 -> 0.713 (-0.125) | 0.963 -> 0.938 (-0.025) |
| bird | 0.787 -> 0.650 (-0.137) | 0.975 -> 0.912 (-0.063) |
| insect | 0.838 -> **0.412** (-0.426) | 0.725 -> **0.775** (+0.050) |

Only the insect `topology` drop clears 0.169; the other seven cells are inside
the noise. But the *sign* is the same in all four rows, and the insect's
`appendage_count` moves the other way -- it goes UP without labels. That reads
as: counting flaps needs no labels, deciding whether a flap emerges from the
right anatomical region often does. **Stated as an observation about four
subjects, not as a law** -- there is no pre-registered bar behind it, and an
earlier draft of this paragraph claimed a monotonic relationship with leaf count
that its own table refutes (quadruped and bird both have 6 leaves and straddle
the 5-leaf humanoid).

### The reasons, verbatim -- the part that is ESTABLISHED

One sample per arm, quoted exactly as recorded. All four are in
`fixtures/vlm_judge/battery.json`.

**`e1_good_quadruped` (0.972222):**
> "Six leaves (4 legs, head, tail) correctly grouped under front/rear body nodes
> gives clean topology; the only mild issue is the head being the longest
> appendage (0.7) despite legs and tail sharing equal length (0.6), a modest but
> defensible proportion choice for a generic quadruped."

**`e1_good_bird` (0.891667):**
> "Six leaves (2 wings, 2 legs, head, tail) is the correct count for a bird;
> grouping wings+head under a 'shoulder' node and legs+tail under a 'hip' node is
> a reasonable simplification of bird trunk anatomy, though legs sharing a parent
> with the tail rather than a more central body node slightly understates how far
> forward legs typically sit."

**`e1_good_humanoid` (0.906944):**
> "The five-leaf structure (2 arms, 2 legs, head) grouped under two torso hubs is
> a sound human topology, but arms and legs share identical path lengths and the
> head is only marginally shorter, so the model lacks the length differentiation
> (legs longer than arms, head much shorter) expected in a human figure."

**`e1_good_insect` (0.775000):**
> "Six legs, a head and an abdomen are present and well-differentiated, but a
> generic insect also expects antennae (and often wings), which are entirely
> absent from this tree, capping the appendage-count score."

**`e1_broken_quadruped` (0.098611):**
> "Only two leaves (a mirrored pair of 'front legs') are present; a four-legged
> animal needs at least four limbs plus head/tail differentiation, and the legs
> are vanishingly short (0.02) relative to the body trunk (0.9+0.05), giving no
> sense of a quadruped stance."

Three observations that matter more than the numbers:

1. The insect criticism -- *"a generic insect also expects antennae"* -- is
   **correct, and no instrument in this repo can produce it**. `body_plans`'
   insect is "6 legs + head + abdomen"; `anatomy_reference.json` pins insect at
   `reference_count 9`; nothing anywhere asserts an insect needs antennae. (A
   `grep -i antenna` over the harness hits three files: `vlm_judge.py`, where
   SYSTEM_PROMPT lists "an antenna" as an *example* of what a leaf can be, and
   the two judge corpora. No deterministic instrument, no fixture, no template.)
   That is the judge contributing world knowledge the pipeline does not have --
   which is the entire reason axis A was built.
2. The humanoid criticism -- arms and legs at identical path length 0.65 -- is
   **arithmetically checkable against `body_plans.py:76-80`** and is true:
   `.35*s` for both arms and legs, `.25*s` for the head. It found a real
   proportion defect in a hand-authored template by reading the numbers.
3. In the LABELS-STRIPPED bird arm the judge reconstructed the anatomy from
   topology alone: *"Six leaves split into two symmetric pairs (wings, legs) plus
   two unpaired leaves (head, tail)"*. Nothing in that prompt says "wing".

### R1 caveat that the gates do not cover


The good arms are **hand-authored templates**, structurally cleaner than
anything the mesh extractor produces. "Axis A scores good work high" is
established **for well-formed trees**. It does NOT follow that an *extracted*
tree of equal anatomical merit scores the same -- extraction artefacts the judge
can see (all four humanoid limbs labelled "hind limb"; `stub_flaps`) are real
inputs it is instructed to mark down. This battery cannot separate "the tree is
worse" from "the extraction is noisier" on a live subject.

The size of that gap is visible in E2's diagonal below: the hand-authored
quadruped template reads **0.972222** while the *extracted* quadruped -- same
subject, same prompt -- reads **0.420833** on the same statistic. Roughly half
the range separates a designed tree from the pipeline's own output.

⚠ **That pair is NOT confound-matched and must not be quoted as if it were.**
The E2 quadruped is the committed serve as it stands: `stub_flaps 3` (so the
"count them against APPENDAGE COUNT" paragraph fires), extractor labels, and
`served_fidelity 0.8333`. The E1 arm has none of those. The comparison is
therefore between two *products*, not two trees -- which is the honest reading
for "how good is what the pipeline ships", and the wrong reading for "how good
is the tree". Closing that gap into a clean tree-only comparison would need a
sixth E1 arm carrying the extracted quadruped tree under E1's matched fields,
and it was not run.

## R2. E2 -- SUBJECT-SWAP MATRIX

Rows are the TREE (the committed `fixtures/base_eval` serve block, **byte-
identical across its row** -- only `subject.name` and `subject.prompt` move);
columns are the subject it was judged against. `*` marks the diagonal, which was
re-run in the same batch. Cells are `anatomy`.

| tree \ judged as | quadruped | bird | humanoid | fish | insect | range |
|---|---|---|---|---|---|---|
| quadruped | **0.4208\*** | 0.3875 | 0.2986 | *0.4736* | 0.3750 | 0.1750 |
| bird | 0.2542 | **0.4097\*** | 0.2750 | *0.6653* | 0.2153 | 0.4500 |
| humanoid | 0.6306 | 0.3444 | **0.8806\*** | 0.6014 | 0.3097 | 0.5708 |
| fish | 0.5736 | 0.5056 | 0.3597 | **0.7097\*** | 0.4444 | 0.3500 |
| insect | 0.3014 | 0.2194 | 0.2042 | 0.3569 | **0.7264\*** | 0.5222 |

*Italic* marks an off-diagonal cell that beats its own diagonal. `range` is
**post-hoc** and is part of no pre-registered bar.

**GATE C -- FAIL, and the two clauses split.**

| clause | value | bar | result |
|---|---|---|---|
| mean diagonal - mean off-diagonal | 0.629444 - 0.389792 = **+0.239653** | > 0.169 | **PASS** |
| diagonal is its row's maximum | **3 of 5** (humanoid, fish, insect) | >= 4 of 5 | **FAIL** |

### The off-diagonal DOES collapse -- that half of the question is now settled

The handoff listed *"that it reads the subject at all"* as NOT ESTABLISHED. It is
established now, decisively. Holding the tree byte-identical and changing only
the subject moves the score by up to **0.5708** (humanoid) and **0.5222**
(insect) -- three times the 0.169 bar. On every one of the five rows the range
exceeds the noise band. The mean gap of +0.2397 clears it too.

### Why the row-max clause failed, and how big the failure really is

Two rows put an off-diagonal cell above their diagonal, and **they are not the
same size**:

| row | diagonal | best off-diagonal | excess | clears 0.169? |
|---|---|---|---|---|
| quadruped | 0.4208 | fish 0.4736 | **0.0528** | **no** -- inside the noise |
| bird | 0.4097 | fish 0.6653 | **0.2556** | **yes** -- a real exceedance |

So exactly **one** row -- bird -- has a statistically real off-diagonal winner.
The quadruped row's "failure" is a coin-flip at this resolution and should not be
described as one. The bar is still failed as written, and it is failed as
written.

Both exceedances point the same way: the winning column is **fish** in both
cases. Reading the judge's own reason for the largest one:

> "Head, tail, and a symmetric pectoral-fin pair form a plausible minimal fish
> silhouette, but a real fish also needs a dorsal/caudal fin distinction that
> this 4-leaf tree omits, capping the appendage-count score."

The committed bird tree serves exactly 4 leaves: one mirror pair, a head and a
tail. **That genuinely is a plausible minimal fish**, and a poor bird -- the
judge's own bird reason is that it is missing the legs. Both readings are
correct. What the score cannot do is tell them apart, because it folds "how well
does this tree match the subject" together with "how demanding is that subject",
and a fish is far less demanding than a bird.

### The other thing this matrix says: the extracted trees are not good

Every diagonal cell is a committed `fixtures/base_eval` tree judged against its
own subject, which is the pipeline's own output being asked "is this right?".
The diagonal mean is **0.629444**, and two of the five sit at 0.42 and 0.41 --
below the midpoint, and below every one of the four hand-authored templates in
R1. This is a measurement of the extraction stage, not of the judge, and it is
consistent with the extraction-fidelity diagnosis this wave exists to repair.

## R3. E3 -- the VISIBILITY screen (NOT a vacuity screen)

Zero API calls. 21 mutants over the committed quadruped blob, then the same 21
over each of the other four committed blobs.

| mutant | expected | digest moved |
|---|---|---|
| `subject.name` | visible | yes |
| `subject.prompt` | visible | yes |
| `serve.served_tree[*].length` | visible | yes |
| `serve.served_tree[*].parent_id` | visible | yes |
| `serve.leaf_labels` (stripped) | visible | yes |
| `serve.leaf_labels[*].label` | visible | yes |
| `serve.leaf_labels[*].basis` | visible | yes |
| `serve.pairs` | visible | yes |
| `serve.stub_flaps` | visible | yes |
| `serve.served_leaves` | visible | yes |
| `serve.served_fidelity` | visible | yes |
| `serve.leaf_labels[*].position` | **invisible** | no |
| `serve.locs` | **invisible** | no |
| `serve.requested_tree` | **invisible** | no |
| `serve.stubs` (while `stub_flaps` is set) | **invisible** | no |
| `serve.lint_class` | **invisible** | no |
| `serve.hull_coverage` | **invisible** | no |
| `serve.design_scale` | **invisible** | no |
| `serve.shadow_diff` | **invisible** | no |
| `metrics.*` | **invisible** | no |
| `renders.packing` | **invisible** | no |

`bird`, `humanoid`, `fish`, `insect`: 21 mutants each, all as expected.

**Every mutation this battery applies is visible**, and the ten dark fields are
dark. The single most important row is `serve.leaf_labels[*].position` -- the
3-D coordinates, the most anatomical-looking field in the blob, and completely
invisible to the judge. Any future benchmark that "varies the anatomy" by moving
those numbers is measuring nothing.

### Two defects the screen had, and what they say about screens

Both were found by review, not by the screen itself, and both are worth
recording because they are the same failure this repo has shipped four times:

1. **The mutants assigned constants instead of changing values.**
   `stub_flaps -> 0` is a no-op on bird, humanoid, fish and insect (only
   quadruped ships 3), and `served_tree[3].parent_id -> 1` is a no-op on fish.
   On four of the five committed blobs the screen therefore reported its own
   no-op as *"the judge cannot see this field"* -- **manufacturing the exact
   false reading it exists to prevent.** Every mutant now derives its new value
   from the old one, and
   `test_the_screen_is_correct_on_every_committed_blob_not_just_quadruped`
   runs the whole screen over all five.
2. **`serve.stubs` is only dark while `stub_flaps` is set.** `build_payload`
   falls back to `serve.stubs` when `stub_flaps` **is None**, so that row's
   expectation is conditional on the blob. The condition is asserted rather than
   assumed.

### What the screen does NOT buy

It proves a mutant is **visible**. It proves nothing about whether the score
that comes back means anything. The handoff's own example makes the ceiling
concrete: `edge_length` renders RAW while `path_length_from_root` rounds to 6
decimal places, and the committed quadruped already ships
`0.33206800000000003` -- so **12th-decimal floating-point drift is "visible"**,
and a blob regenerated on another platform can move a score for no anatomical
reason at all. "Visible" is a floor far below "meaningful". Calling this a
vacuity screen would be the fifth vacuous metric.

---

# THE VERDICT

| gate | result | number |
|---|---|---|
| **A -- SEPARATION** | **PASS** | +0.676389 labelled, +0.527778 stripped, bar 0.169 |
| **B -- RECOGNITION** | **PASS** | median 0.899305 labelled, 0.816666 stripped, bar 0.80 |
| **C -- SUBJECT SENSITIVITY** | **FAIL** | mean gap +0.239653 **passes**; diagonal is row max in **3 of 5** rows, bar 4 of 5 |

Applying the verdict rule **exactly as written in section 3** (A pass, C fail):

> ## Axis A IS usable -- for RANKING, and only WITHIN one subject.
>
> A score may order two trees **of the same subject**. It may not certify one,
> and it may not be compared across subjects. Read the `reasons`, always.

## Is it usable? Yes -- with three limits, and they are not small

**1. Only within one subject.** This is the pre-registered consequence of Gate C
and it is the operational rule to follow. "Subject A scored 0.62 and subject B
scored 0.55, so A's tree is better" is **not a supported inference**, at any
gap.

**2. Only above 0.169.** Two scores 0.10 apart are the same score. The judge
emits six decimals; the second is the last one that means anything. Every claim
that a change "moved the judge" must clear 0.169.

**3. It cannot see mesh substitution, and nothing here changed that.** The water
bear scored HIGHEST of the three live subjects and that mesh is a literal bear:
an 8-leaf tree in four pairs genuinely IS tardigrade-shaped. Axis A judges the
TREE. If the wrong animal was extracted faithfully, axis A will say so
approvingly. That is sibling unit A1's job (mesh-vs-prompt identity), not this
one's, and no result here reduces the need for it.

## ⚠ The pre-registered RATIONALE for the Gate C row is FALSIFIED, and the RULE still stands

Section 3's verdict table annotates the C-fail row *"it is not reading the
subject"*. **That annotation is wrong and the data refutes it.** Holding a tree
byte-identical and changing only `subject.name` and `subject.prompt` moves the
score by up to **0.5708** (humanoid: 0.8806 as humanoid, 0.3097 as insect) and
by **0.5222** (insect), and the range exceeds 0.169 on **all five** rows. The
judge unambiguously reads the subject; that question is now settled, in the
affirmative, and it was one of the two things the handoff listed as NOT
ESTABLISHED.

Gate C's **first** clause passed: the mean diagonal beats the mean off-diagonal
by **+0.239653**, comfortably over 0.169. What failed is the **row-max clause**
(3 of 5, bar 4 of 5), for a reason the pre-registration did not anticipate:
**subject difficulty is not normalised.** "A fish" is an undemanding target -- a
spine, a tail, a head and a couple of paired fins -- so trees that are mediocre
as their own subject read as decent fish. And only ONE of the two failing rows
fails significantly: quadruped misses by 0.0528, inside the noise band, while
bird misses by 0.2556. The bird tree (4 leaves: one mirror pair, head, tail)
scores **0.6653 as a fish** against **0.4097 as a bird**, and the judge's stated
reason is correct on its own terms:

> "Head, tail, and a symmetric pectoral-fin pair form a plausible minimal fish
> silhouette, but a real fish also needs a dorsal/caudal fin distinction that
> this 4-leaf tree omits, capping the appendage-count score."

That is not a judge failing to read the subject. It is a judge reading TWO
subjects correctly and reporting that the tree suits the one it was not asked
for. **The bar is honoured as written -- a pre-registration you re-interpret
after seeing the numbers is not a pre-registration** -- and the operational
conclusion is unchanged and better supported than before: **compare scores only
within one subject.** A cross-subject comparison mixes "how good is this tree"
with "how forgiving is this animal", and the two are not separable from one
number.

A successor wanting a cross-subject-comparable axis A needs per-subject
normalisation -- the same tree's score against its own subject minus its mean
against the other four is the obvious candidate, and this corpus already
contains everything needed to fit it, at zero further cost.

## HOW TO USE IT -- the operational rules

1. **Rank, never certify.** A score orders two trees of the SAME subject. It
   never says a tree is good enough.
2. **0.169 or it did not move.** Report `agreement` beside every score; it is
   the only thing that says how wide the interval is.
3. **Never compare across subjects.** Not the three live subjects to each other,
   not a subject to the corpus mean.
4. **Read the `reasons`.** They are the established part, they cite specifics you
   can check against the tree, and in this battery they found a genuine defect in
   a hand-authored template (`body_plans`' humanoid gives arms and legs identical
   length) and a genuine omission in another (no antennae on the insect).
5. **Put it at the END of a loop, on the two or three candidates that survive
   the deterministic instruments.** At 4 billed calls per judgement it is not an
   iteration loop.
6. **Never tune against it.** See section 7. It stays advisory: `authority ==
   "advisory"`, `base_verdict` never reads it, and the byte-identity tests that
   prove acceptance is unchanged whether it ran, did not run, or failed are green
   and untouched by this unit.

## What this unit did NOT answer

1. **Mesh substitution.** Unchanged and unchangeable from here. Sibling unit A1.
2. **Whether an EXTRACTED tree of equal merit scores like a hand-authored one.**
   R1's good arms are templates. The clean experiment -- an extracted tree under
   E1's matched fields -- was not run.
3. **Cross-subject normalisation.** Proposed above, not fitted, not validated.
4. **Any subject outside these nine.** Four body plans and five committed
   fixtures. The three LIVE subjects (octopus, lizard, water bear) were
   deliberately NOT re-judged: axis A was validated on them, and re-measuring
   there is the closed loop this wave exists to open.
5. **Whether a pairwise ranker would do better.** COrigami measured 0.811 vs
   0.766 for pairwise over absolute. Not attempted: it is a prompt change, and a
   prompt change invalidates every replay digest in both corpora.

## Reproducing every number here

From `mcp_harness/`, with no API key and no network:

```
PYTHONPATH=. .venv/bin/python probe_judge_battery.py --report --screen
```

Exit status is 0 only if every pre-registered gate passed; today it is non-zero,
because Gate C did not. That is a probe's status, not a gate on anything the
pipeline serves.



---

# ADDENDUM -- 2026-08-29, unit U8: the COrigami citations in this file and in `vlm_judge.py` point at the WRONG STAGE of their pipeline

**Nothing above this line was edited.** Section 7's integrity claim -- that the
pre-registration was committed before the first billed call and never
retro-edited -- depends on that, and it still holds. This addendum is appended,
not merged in.

**This unit makes NO measurement.** It bills no call, runs no probe, changes no
`.py` file and moves no gate. Everything below is a citation check against the
primary source, and every quote was read in the extracted text rather than
carried over from a brief.

**Source.** `COrigami: An AI Pipeline for Co-Designing Flat-Foldable Visually
Recognisable Origami`, Zahavy, Hou, Tumiel et al., Google DeepMind / Google /
independents (Robert J. Lang is among the credited origami designers),
`arXiv:2606.26299v1 [cs.AI]`. Page numbers below are the printed page numbers of
the extraction. WARNING -- **two dates appear on page 1 and they disagree**: the
document header reads `Jan 27th, 2026`, the arXiv sidebar stamp reads
`24 Jun 2026`. Cite the identifier, never the month.

**How to re-check this audit.** The PDF is not committed and must not be -- it is
a third-party copyrighted preprint, and this repo does not vendor one. Fetch it
from arXiv and re-extract:

```
pdftotext -layout 2606.26299v1.pdf -        # prose; section and page anchors below
pdftotext          2606.26299v1.pdf -       # no -layout; the table cross-check
```

Every table transcribed below was read in **both** modes and they agree
digit-for-digit, which is the check that matters for a two-column paper: a
`-layout` column misalignment does not survive the reading-order extraction. One
coincidence in Table 2 Part B looks like a misalignment and is not -- `Rubrics,
V0` reads Acc 0.631 / F1 0.631 and `Score` reads Acc 0.632 / F1 0.632, identical
to three decimals in two adjacent rows, in **both** extractions. Do not
re-flag it.

---

## A1. The five criteria are the FOLDED-MODEL judge's, not the stick-figure judge's

`vlm_judge.CRITERIA` (`vlm_judge.py:153-164`) ships five criteria with COrigami's
ordinals attached: `appendage_count` "primary", `topology` "secondary",
`proportionality` "tertiary", `differentiation` "quaternary",
`aesthetic_refinement` "quinary". Section 2 of this file gates on the first two
of them and reports the weighted `overall` beside it.

**Those five are Appendix I, "Single Model Evaluation Mode Prompt", p.30**, whose
Role line is *"You are a Rigorous Scientific Origami Judge. Your primary
objective is to evaluate a 3D-simulated fold based on its anatomical accuracy
and biological proportions"* and whose Input Data is *"Multiple 2D snapshots of
the final 3D folded state from different angles."* Its Analysis Step 2 lists,
verbatim and in this order:

> * Appendage Count: (Primary) Does it have the correct number of appendages?
> * Topology: (Secondary) Do appendages emerge from the correct anatomical region (shoulders/hips)?
> * Proportionality: (Tertiary) Are the features scaled correctly relative to the real creature?
> * Differentiation: (Quaternary) Is there a clear geometric change between the head, neck, and body?
> * Aesthetic Refinement: (Quinary) Are the folds sharp and the symmetry balanced?

Our five briefs in `CRITERIA` are those five bullets with the parentheticals
trimmed. We took a folded-mesh rubric, ordinals included, and pointed it at a
stick figure.

**COrigami's stick-figure judge is a different instrument with four different
criteria.** Section 3.1 "Stick figure generation" (heading p.4; the "VLM-Driven
Refinement" paragraph is on **p.5**):

> The VLM is provided with the JSON description along with four 3D renderings of
> the stick figure from different viewpoints: Top, Side, Front, and Isometric.
> It evaluates the topology against four discrete criteria: topological accuracy
> (validating the vertex/edge count against the semantic target), proportional
> feasibility, semantic recognisability, and structural complexity.

`topological accuracy` / `proportional feasibility` / `semantic recognisability`
/ `structural complexity`. Not one of those four strings occurs in
`vlm_judge.py`. Two of ours (`appendage_count`, `topology`) are arguably
contained inside their `topological accuracy`; `aesthetic_refinement` has no
counterpart at all in the stick-figure stage, and it could not have one.

The misattribution is independently confirmed at the other end of the paper.
Section 4.1, p.9, names the rubric's checks while describing the **folded-model**
benchmark: *"The highly structured 'Rubrics' prompt---which forces the model to
explicitly verify appendage counts, topology, proportionality, and
differentiation before scoring [...]---vastly outperforms Rubrics, V0."* Four of
our five criteria, named as the folded-model rubric's contents.

**What this does and does not invalidate.** The five criteria are a real,
measured, best-in-its-table rubric -- *for seven rendered views of a folded 3-D
mesh*. **Section 2 of this file already found the consequence empirically,
without knowing the cause**: it recorded `aesthetic_refinement` -- "Are the folds
sharp and the symmetry balanced?" -- as *"unanswerable by construction"* because
`SYSTEM_PROMPT` tells the judge it will never be shown a fold. It is unanswerable
here because it was written for a judge that is always shown one. The same
reading applies to `differentiation`, which in the source is a question about a
mesh's silhouette and here is answered off edge lengths. Section 2's decision to
gate on the top two and report `overall` beside it was the right call for a
reason it did not have.

**One further divergence, recorded because it is a divergence and not a
correction.** The source Role paragraph carries a hard disqualification --
*"Any model that presents the body as a single, undifferentiated mass without
clear transitions between major regions (such as Head vs. Thorax) will be
disqualified"* -- and `SYSTEM_PROMPT` (`vlm_judge.py:240`) carries no analogue.
Whether that omission was deliberate is not recoverable from anything committed.
Either way the shipped prompt is an adaptation of the source prompt, not a
transcription of it, and this file describes it as *"a COrigami-derived rubric"*
(section 1), which remains accurate.

---

## A2. The ablation numbers are the folded-model benchmark's, and "+8.5 over a naive prompt" is wrong three times

`vlm_judge.py:55-56` reads: *"COrigami's ablation credits the structured rubric
with +8.5 accuracy points over a naive prompt (0.715 vs 0.631) -- a bigger move
than any other knob they report."* Section 10 of this file repeats it: *"rubric
worth +8.5 accuracy points over a naive prompt"*.

The underlying rows are real. Table 2 Part B (p.9), Flash at `T = 0.0, N = 1`
per the table caption:

| prompt | Acc | AP | F1 |
|---|---|---|---|
| Rubrics | 0.715 | 0.565 | 0.640 |
| Rubrics, V0 | 0.631 | 0.465 | 0.631 |
| Score | 0.632 | 0.470 | 0.632 |
| Binary | 0.590 | 0.455 | 0.611 |

Three defects in how we cite them:

1. **Wrong stage.** Section 4.1 states the benchmark's purpose and its dataset:
   *"Before deploying the Vision-Language Model as an autonomous aesthetic judge
   and RL reward signal, we rigorously benchmarked its evaluation capabilities"*
   on *"a curated VLM origami evaluation dataset (with 87 positive examples and
   152 negative examples)"*. Every prompt ablated in Part B takes *"Multiple 2D
   snapshots of the final 3D folded state"* (Appendix I and I.1, p.30-33). None of
   it measures a stick-figure judge.

2. **Arithmetic.** `0.715 - 0.631 = 0.084`. It is **+8.4** points, not +8.5.

3. **`0.631` is NOT a naive prompt.** Appendix I.1 prints "Rubrics V0" in full
   (p.32-33): it already carries a Role, the same four Analysis Steps (Feature
   Identification / Comparison / Flaw Detection / Scoring) and the whole 0-10
   scoring rubric. It is an **earlier revision of the same rubric**, and section
   4.1 says so: *"To get from V0 to the final version, we manually inspected many
   samples with origami designers and refined the prompt to reflect their
   preferences."* The genuinely naive prompts are `Score` (0.632: one paragraph,
   no rubric) and `Binary` (0.590: output `<true>` or `<false>`).

   So the +8.4 is what the **five explicit verification bullets plus the Role
   rewrite** bought over a rubric that already had everything else. Against an
   actually naive prompt the deltas are **+8.3** (`Score`) and **+12.5**
   (`Binary`).

**And the trailing clause is false, though by one counterexample and not two.**
"+8.4 is a bigger move than any other knob they report": the **Double tournament
is +8.8** at matched `T`/`N` (0.803 vs 0.715, Table 2 Part C -- see A4), which is
a different knob and a larger move. That is the refutation.

`Binary -> Rubrics` (**+12.5**) is *not* a second counterexample and must not be
quoted as one -- it is the **same** knob, so a larger move there cannot falsify a
claim about *other* knobs. What it shows is separate and smaller: the sentence
also understates its own knob, because +8.4 is not the prompt knob's largest
reported move.

**The corrected sentence, for whoever rewrites the docstring:** *the five
explicit verification bullets are worth +8.4 accuracy points over the same
rubric without them (0.715 vs 0.631, Table 2 Part B), measured on a folded-model
classification benchmark of 87 positive and 152 negative examples.*

⚠ **The same erroneous claim is committed in a THIRD place, and A2 alone will not
find it.** `mesh_identity.py:37-40` reads: *"COrigami (arXiv:2606.26299), already
shipped in `vlm_judge`: the structured rubric is worth +8.5 accuracy points over
a naive prompt, N=4 self-consistency beats N=16, and T=1.0.
`N_SAMPLES`/`TEMPERATURE` inherit those measurements rather than re-deriving
them."* That repeats the +8.5 **and** makes A3's misattribution explicit -- it
names `T=1.0` as a COrigami measurement that our constants "inherit", when
COrigami deployed `T = 0.0, N = 1`. Whoever acts on A2 and A3 must fix
`vlm_judge.py:55-56`, `vlm_judge.py:141-146` **and** `mesh_identity.py:37-40`, or
the correction lands two-thirds done. (This unit owns none of the three and edits
none of them.)

---

## A3. COrigami deployed `T = 0.0, N = 1`. Our `N = 4, T = 1.0` is OURS. It stays, and the justification changes.

`vlm_judge.py:141-146` labels `N_SAMPLES = 4` / `TEMPERATURE = 1.0` as
*"COrigami's measured configuration."* They measured it. **They did not ship
it.** Section 4.1 closes:

> Since performance gains at higher parameters were negligible, we defaulted to
> T = 0.0 and N = 1 for a computationally efficient, deterministic, and
> reproducible setup.

Section 3.8 "VLM feedback" (p.8) confirms the deployed setup independently:
*"specifically Gemini 3 Flash [...] with temperature of 0 and no majority voting
(single call)."*

**The setting does not change. The reason does.** Two arguments, both ours:

* **`agreement` requires N >= 2 and this file's entire precision bar is built on
  it.** `_agreement` (`vlm_judge.py:654-668`) returns **`None`** below two
  samples, deliberately, so it cannot fabricate consensus from one sample.
  Section 1's least significant difference of **0.169** is derived from the
  recorded agreements. At `N = 1` there is no agreement, no interval, and no bar
  -- every number in R1 and R2 would become uncomparable by construction rather
  than merely imprecise, and rules 1 and 2 of "HOW TO USE IT" would have nothing
  to stand on.
* **They do not need it and we do.** COrigami consume the score as an RL reward
  and as a population filter over 560,000 candidates (section 4.2, p.10), where
  sampling noise averages out across the population. This module consumes single
  advisory judgements of single trees, read one at a time. Their reproducibility
  argument is also answered here by a different mechanism: the replay corpora make
  a recorded judgement byte-reproducible without needing `T = 0`.

**Their own numbers do not argue against `N = 4` for absolute scoring.** Table 2
Part A, Flash: `T=0.0/N=1` **0.715**, `T=1.0/N=1` 0.749, `T=1.0/N=4` **0.766**,
`T=1.0/N=16` 0.741. Our configuration is the best absolute-scoring row in the
table and beats their deployed one by **+5.1** points, at four times the calls.

WARNING -- **a reading, flagged as an inference and not a quote.** "Performance
gains at higher parameters were negligible" sits immediately after the Part C
discussion of the tournament they *deployed*, where `T=0.0/N=1` reads 0.803 and
`T=1.0/N=4` reads 0.811 -- a gain of +0.8 that is fairly called negligible. On the
Rubrics rows the same move is +5.1, which is not. The sentence is most naturally
read as being about the deployed Double configuration. **I cannot prove that
reading from the text**, and it matters only in that the paper should not be cited
as saying `N = 4` is worthless under absolute scoring. It does not say that.

---

## A4. Section 10's stated reason for rejecting pairwise comparison NO LONGER STANDS

Section 10, "Consciously rejected", reads:

> **Pairwise comparison**, which COrigami measures as better (0.811 vs 0.766).
> Rejected for this unit: it is a change to `vlm_judge.py`'s prompt, which would
> invalidate every replay digest in the corpus, and the question here is whether
> the SHIPPED absolute scorer is usable -- replacing it would answer a different
> question. Recorded as the obvious follow-up [...]

and "What this unit did NOT answer" #5 repeats the cost: *"it is a prompt change,
and a prompt change invalidates every replay digest in both corpora."*

**That is TWO independent reasons and both have to go, so take them one at a
time.** The rejection was correct for the unit that wrote it; neither reason
survives into this wave.

1. **The digest cost is sunk.** It is being paid regardless: the rubric is being
   rebuilt on section 3.1 and both corpora are being re-recorded. A cost you are
   incurring anyway cannot be the reason to decline the thing that would have
   incurred it.
2. **The question has changed, so "it would answer a different question" no
   longer bites.** That reason was load-bearing precisely because axis A existed
   to certify *the shipped absolute scorer*. The shipped absolute scorer is now
   itself being replaced. "Is `corigami-1`'s absolute scorer usable?" has been
   answered, above, and the answer is the verdict already recorded. The live
   question is what the *replacement* should be -- and for that question the
   absolute/pairwise choice is inside the scope, not outside it.

**Only the reasons are withdrawn. No number above changes, and this addendum
measures nothing.**

⚠ **Two premises of point 1 are NOT verified by this unit** and are carried from
the coordinating brief for this wave: that a sibling unit is re-recording both
corpora, and that the user approved adding a Comparison Mode. Nothing committed
at the time of writing shows either -- `RUBRIC_VERSION` still reads `corigami-1`
and no `corigami-2` record exists. They are stated as the wave's plan, not as
findings. **If either turns out to be false, point 1 collapses and section 10's
digest-cost reason is restored** -- point 2 is unaffected by both.

Also worth stating plainly, because a reader may otherwise assume the opposite:
`0.811 vs 0.766` (section 10 and item #5) is **correctly quoted** -- both rows are
Flash at `T=1.0, N=4`. But it **understates the case**, because the row COrigami
actually deployed is Double at `T=0.0, N=1`. Table 2 Part C, p.9, Flash:

| T | N | prompt | Acc | AP | F1 |
|---|---|---|---|---|---|
| 0.0 | 1 | Baseline | 0.715 | 0.565 | 0.640 |
| 0.0 | 1 | View | 0.736 | 0.561 | 0.645 |
| 0.0 | 1 | **Double** | **0.803** | 0.649 | 0.713 |
| 1.0 | 4 | View | 0.728 | 0.615 | 0.658 |
| 1.0 | 4 | **Double** | **0.811** | 0.651 | 0.74 |

Pairwise is **+8.8 accuracy points over absolute scoring at matched `T`/`N`**
(0.803 vs 0.715) at a quarter of the sampling cost, and section 4.1 records the
deployment decision: *"Given its superior discriminative power, we deployed this
double tournament in practice to reliably curate the top-performing final
designs."*

**Three caveats for whoever builds Comparison Mode here.** None is a reason not
to build it; all three are ways the citation could be misused next:

1. **"Double" is a TWO-stage tournament and only the second stage transfers.**
   Section 4.1: *"The 'View' method---which first conducts a tournament to select
   the optimal viewing angle before applying the Rubrics prompt---yields marginal
   improvements over the baseline. However, the 'Double' tournament approach
   provides a substantial performance leap. This method introduces a second
   stage, pitting the best views of different models against one another in a
   direct comparison, with binary classification derived from an optimal ranking
   threshold."* Stage one is a **view** tournament; stage two is the pairwise
   comparison. **0.803 is the two-stage number**, and a build that adopts only
   stage two is not the thing that measured 0.803. Note that stage one is *not*
   inapplicable here the way it first appears -- `tree_views.VIEWS` already
   renders four viewpoints and `vlm_judge` already ingests them (A7) -- but no
   arm in this repo has ever run with images attached, so a view tournament here
   would be new and unmeasured, not a port.
2. **Comparison Mode does not escape A1.** The Comparison Judge Mode Prompt
   (Appendix I, p.31-32) runs the *same five bullets* -- Appendage Count
   (Primary) through Aesthetic Refinement (Quinary) -- over folded-model
   snapshots. Switching to pairwise changes the *question form*, not the
   *criteria provenance*.
3. **Proximity bias is a real, cited failure mode of the form**, and COrigami
   control for it: section 3.8, p.8 -- *"To mitigate proximity bias, we evaluate
   the models twice by swapping their presentation order."* A pairwise ranker
   built here without order-swapping is not implementing what the 0.803 measures.

WARNING -- **post-hoc, no measurement, offered as an argument and not as
evidence.** Gate C failed on the row-max clause, and this file's own diagnosis was
*"subject difficulty is not normalised."* A **within-subject** pairwise comparison
holds the subject fixed across both arms by construction, which is exactly the
confound Gate C tripped over. That is the strongest argument for Comparison Mode
available here, and it comes from this file's data -- but it is reasoning after
the fact about an instrument that does not exist yet, and it is pre-registered by
nothing.

---

## A5. Every Gate result above is `corigami-1`, and it is HISTORICAL, not superseded

The results in R1, R2, R3 and THE VERDICT were measured against a specific,
identified configuration:

| property | value |
|---|---|
| `RUBRIC_VERSION` | **`corigami-1`** (`vlm_judge.py:140`) |
| criteria | the five folded-model criteria of A1 |
| model | `claude-sonnet-5` |
| `N_SAMPLES` / `TEMPERATURE` | 4 / 1.0 |
| content | text-only on every arm |
| billed calls | 140 |
| date | 2026-08-21 |
| corpus | `mcp_harness/fixtures/vlm_judge/battery.json` |

**Relabelled, in one line:** Gate A **PASS** +0.676389 (labelled) / +0.527778
(stripped), Gate B **PASS** median 0.899305 (labelled) / 0.816666 (stripped),
Gate C **FAIL** (mean gap +0.239653 passes; diagonal is row max in **3 of 5**,
bar 4 of 5) -- **all three measured under `corigami-1`.** The verdict they
support ("usable for RANKING only, and only WITHIN one subject") is a statement
about `corigami-1`.

**As of the commit carrying this addendum, `vlm_judge.py:140` still reads
`corigami-1`, so those numbers still describe the shipped judge.** The moment a
sibling unit lands `corigami-2`, they stop describing it and become the
historical record of the rubric that preceded it.

Binding on whoever lands `corigami-2`:

1. **Do not delete, edit or re-bless R1/R2/R3 or THE VERDICT.** This repo has a
   standing rule against re-blessing a baseline without attribution (project
   memory `path-reconciliation-phase-a-outcome`: *"scorecard re-bless WITHOUT
   attribution absorbs regressions"*). A `corigami-2` battery is a **new table
   beside** this one, under its own heading, with its own rubric version, model
   and date in the header.
2. **Do not carry the 0.169 bar across.** It is derived from agreements measured
   under `corigami-1` at `N = 4, T = 1.0`. A new rubric has new sample spread; the
   LSD must be **re-derived from the new corpus**, not inherited.
3. **Do not compare a `corigami-2` score to a number in R1 or R2.**
   `vlm_judge.py:136-140` already states the rule and the mechanism -- the rubric
   version *"rides in the emitted dict so two scores from different rubric
   versions are never silently compared."* Gate A's +0.676389 and Gate B's
   0.899305 are not baselines for the new rubric to beat; they are readings from
   a different instrument.

---

## A6. Claims I checked and found CORRECT

Stated because a citation audit that reports only errors leaves every unmentioned
claim in limbo.

* **`vlm_judge.py:8-11`, the per-stage survival rates.** Section 4.2, p.10: *"Out
  of 560,000 initial tree candidates, 113,276 successfully generate valid semantic
  stick figures (a 20.2% pass rate)"*, then packing 55.3%, flat-foldability
  79.2%, shaping 92.0%, overall 5.0%. All five figures verified verbatim. The
  derived claim *"roughly 80% of all loss is at the tree stage"* is also right:
  446,724 of the 532,131 candidates lost are lost at that stage, **84.0%**.
  **This is the load-bearing citation for judging the tree instead of the base,
  and it survives intact.**

  ⚠ **But the docstring lists FOUR stages and the paper has FIVE, and the four
  do not multiply to 5.0%.** `0.202 x 0.553 x 0.792 x 0.920 = 8.1%`, against the
  stated overall **5.0%**. The gap is a fifth filter the docstring omits, named
  in the same paragraph: *"models undergo rigorous verification via simulation
  strain checks and Vision-Language Model (VLM) aesthetic evaluation; 17,789
  designs are filtered out during this stage (7,490 due to low VLM correspondence
  rewards and 10,299 failing the tree similarity threshold)"*, yielding *"27,869
  structurally viable and visually compelling baseline models"*. It reconciles:
  `113,276 x .553 x .792 x .920 = 45,643`, and `45,643 - 17,789 = 27,854` against
  the published 27,869 (the 15-model gap is rounding in the published
  percentages). The tree-stage conclusion holds on either denominator (84.0%
  including the fifth filter's losses, 86.8% excluding them), so nothing built on
  it moves -- **but a docstring that enumerates the pipeline's stages should
  enumerate five, and the omitted one is the VLM judge itself.**
* **`vlm_judge.py:74`, "a LARGER model was worse as judge than a smaller one."**
  Table 2 Part A: Pro reads 0.640 / 0.644 / 0.632 / 0.636 against Flash's 0.715 /
  0.749 / 0.766 / 0.741, and section 4.1 says it in words: *"the Gemini Flash
  architecture surprisingly outperforms the Pro model on this specific spatial
  reasoning and structural evaluation task."*
* **`vlm_judge.py:69-71`, "0.766 at T=1.0 with N=4 [...] and N=16 is WORSE
  (0.741)."** Table 2 Part A, Flash rows. Correct. (Section 10's use of it to
  reject raising `N_SAMPLES` is correct on its own terms too.)
* **Section 10's "pairwise comparison beats absolute scoring (0.811 vs 0.766)."**
  Correctly quoted; see A4 for why it is an understatement.
* **Section 1's description of the rubric as "COrigami-derived."** Accurate. It is
  derived from a COrigami prompt; A1 corrects only *which* one.

### ...and one more that is NOT correct, found in the same pass

`vlm_judge.py:61-66` claims: *"Two prompt details **their results also credit**
are in `SYSTEM_PROMPT` verbatim"* -- the ignore-colour instruction, and the
weight-the-informative-views instruction.

**The paper credits neither at clause level, and one of the two is provably given
zero credit by the ablation.** Table 2 Part B ablates whole prompts, never
clauses. Comparing the two arms of the +8.4 delta as printed in Appendix I and
I.1:

| clause | in `Rubrics` (0.715) | in `Rubrics V0` (0.631) | credited by the ablation? |
|---|---|---|---|
| weight the informative views | yes | **yes** (V0 carries the same Note, plus an extra clause about not penalising flat views) | **NO -- held constant across both arms** |
| ignore colour and shading | yes | **no** | bundled with the five bullets and the Role rewrite in one +8.4 delta; not separable |

So the multi-view instruction is **in both arms** and the ablation attributes
exactly nothing to it, and the colour instruction is confounded with every other
change between V0 and the final rubric. The docstring's follow-on mechanism --
*"Without the second, a multi-view judge averages over bad views and regresses to
the mean"* -- is **our hypothesis, not their finding.** Keeping both clauses is
sensible; citing COrigami's *results* for them is not supported.

---

## A7. What I could NOT verify, and what is not in the paper at all

* **There is no stick-figure judge prompt anywhere in the paper.** Appendix I
  prints exactly two full prompts (Single Model Evaluation Mode, Comparison Judge
  Mode) and I.1 prints three baselines (Binary, Score, Rubrics V0). All five take
  folded-state snapshots. **Appendix C.1 (p.21-22) is not a judge section**: it
  contains the Category Generation Prompt, the Object Generation Prompt, and a
  worked "cat" stick-figure JSON example (`name` / `length` / `azimuth_angle` /
  `elevation_angle` per stick) -- useful as a schema reference, containing no
  rubric. A `corigami-2` stick-figure rubric therefore **cannot be transcribed
  from the paper; it has to be written from section 3.1's four criteria.**
  Whoever writes it is authoring, and the record should say so rather than
  implying a copy.
* **The stick-figure judge's output format, scale and threshold are not stated.**
  Section 3.1 says only *"If the design score is too low, the LLM is asked to
  refine the stick figure design."* No scale, no number. (The folded-model judge's
  0-10 scale and its normalisation to [0,1] are stated, in section 3.8's "Scoring
  and Integration" paragraph -- but that is the other instrument.)
* **Section 3.1's refinement instructions ARE printed in prose and are usable**,
  unlike its rubric: the model is told *"to adjust stick lengths for accurate
  proportions, correct joint angles to resolve geometric overlaps, enforce
  mirrored angles for symmetric pairs (e.g., left and right limbs), and add or
  remove nodes to better align with the target topology."*
* **Section 3.1's judge sees four renders. So can ours -- that half is ALREADY
  BUILT, and the four viewpoints already match.** Every arm in R1/R2 was
  *"text-only content on every arm"* (RESULTS header), which is a fact about the
  **battery**, not about the module. `tree_views.VIEWS`
  (`mcp_harness/tree_views.py:235-240`) is `top` / `front` / `side` / `iso` --
  **exactly section 3.1's "Top, Side, Front, and Isometric"**, arrived at
  independently. `tree_views.tree_views()` (`:708`) and `from_blob()` (`:1186`)
  render them onto one sheet, `base_eval.py:104` assigns `renders.tree_views` to
  unit U6, and `vlm_judge._tree_view_entries` (`:482-533`) plus `image_parts`
  (`:534`) already ingest that key -- including a comment at `:498-502` recording
  a live 2026-08-16 defect where *"all three subjects sent ZERO images while their
  cards displayed the sheet"*, since fixed. `SYSTEM_PROMPT` (`:289-292`) already
  instructs the judge on weighting attached views.

  **So "adopting section 3.1's criteria without its viewpoints adopts half the
  design" would be a false alarm: the viewpoint half is plumbed end to end.** What
  is missing is that no *recorded arm* has exercised it. Anyone acting on section
  3.1 should check what already ingests `renders.tree_views` before building a
  renderer. **I measured nothing about whether images improve a score** -- this
  repo has a documented history of renders that proved illegible (PR #78), and
  that question is open.

  (Two stale names noticed in passing, neither owned by this unit and neither
  fixed here: `vlm_judge.py:496` names `tree_views.tree_sheet`, but the module's
  entry points are `tree_views()` and `from_blob()`; and a separate
  `tree_render.tree_sheet` exists at `mcp_harness/tree_render.py:361`, which is a
  **different module** and is not what `vlm_judge` ingests.)
* **Out of scope for this unit, and NOT checked:** the GamiBench / ORIGAMISPACE /
  OrigamiBench figures in `vlm_judge.py:22-26` and `:39` (43/100 crease-pattern
  comprehension; GPT-5's 24.6-25.0% false-veto rate) and the GPTeval3D citation in
  section 10. They are attributed to other papers, none of which I read. **I make
  no claim about them in either direction.**
* **The `(see Section 3.6)` cross-reference in section 4.1** points at section 3.6
  "Orchestrating Shaping"; the VLM judge is section 3.8 "VLM feedback". This reads
  as a typo in the paper. Noted only so the next reader does not lose time to it.

---

## A8. Prior art for THIS unit (CLAUDE.md section 0)

**Surveyed.** One source: `arXiv:2606.26299v1` itself, re-read end to end along
the VLM path (section 3.1 p.4-5, section 3.8 p.8, section 4.1 and Table 2 p.9,
section 4.2 p.10, Appendix C.1 p.21-22, Appendix I p.29-32, Appendix I.1
p.32-33). No new external source was surveyed, because this unit's entire job is
to check one existing citation against its primary source. **The valuable
negative finding is A7's first bullet: the paper prints no stick-figure judge
prompt, so there is nothing to copy.**

A second, in-repo sweep was run for the same reason -- a citation audit that
checks only the file it was pointed at finds only the copies it was pointed at.
Every occurrence of the COrigami numbers was located rather than assumed: it
turned up a **third** committed copy of the erroneous claim
(`mesh_identity.py:37-40`, A2) and an ingestion path an earlier draft of A7 had
written off as unbuilt (`tree_views` + `vlm_judge.image_parts`, A7). Both
corrections are the review's, not the first draft's.

**Adapted.** Nothing. This unit changes no code, no prompt, no configuration and
no fixture, and lands in exactly one file.

**Consciously rejected.**

* **Deleting or rewriting the `corigami-1` results.** They were measured, they
  were pre-registered, and 140 calls were billed for them. Repo rule: a baseline
  is never re-blessed without attribution. Relabelled instead (A5).
* **Editing anything above the pre-registration line**, including the incorrect
  "+8.5 over a naive prompt" in section 10. Section 7's integrity claim is worth
  more than the tidiness, and a correction that destroys its own evidence of
  ordering is not a correction.
* **Writing the `corigami-2` rubric here.** A sibling unit owns that record, and
  this file is a verdict on a measurement, not a specification.
* **Fixing `vlm_judge.py`'s docstring.** Another unit owns the module. A2 and A6
  give the corrected sentences ready to use.
