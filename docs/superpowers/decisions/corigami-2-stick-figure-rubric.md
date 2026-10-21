# COrigami-2 -- the stick-figure judge has been running the FOLDED-MODEL rubric

**Unit U1.** Status of this file when first committed: **PRE-REGISTRATION
ONLY.** Everything above the pre-registration line was written **before a
single billed call was made**, and the commit that contains it is the proof of
ordering. The results and the verdict are appended afterwards, in a later
commit, by a sibling unit, **without editing the bar**.

> A bar written after seeing the numbers is not a bar.

This file is the corigami-2 analogue of
[`axis-a-verdict.md`](axis-a-verdict.md), which pre-registered and then
measured the **corigami-1** rubric. That document is not superseded: its
results stand as the measured behaviour of the rubric this wave replaces, and
three of its rulings are carried forward unchanged (sections 3, 4 and 6 below
say which).

---

## 1. What is being decided

`mcp_harness/vlm_judge.py` scores a Metric Tree -- an abstract stick figure --
against the prompt or subject name that asked for it. Its five criteria
(`vlm_judge.py:153-164`) are:

```
appendage_count      primary     5/15   "Does it have the correct number of appendages?"
topology             secondary   4/15   "Do appendages emerge from the correct anatomical region?"
proportionality      tertiary    3/15   "Are the features scaled correctly relative to the real creature?"
differentiation      quaternary  2/15   "Is there a clear geometric change between head, neck and body?"
aesthetic_refinement quinary     1/15   "Are the folds sharp and the symmetry balanced?"
```

**Those are not COrigami's stick-figure criteria. They are COrigami's
folded-model criteria, lifted verbatim, ordinals and all.**

### 1.1 The finding

Paper: **COrigami: An AI Pipeline for Co-Designing Flat-Foldable Visually
Recognisable Origami**, arXiv:2606.26299v1, Google DeepMind, January 2026.
Every citation below was read out of the PDF with `pdftotext -layout` and the
page numbers are the PDF's own printed folios.

**What we shipped is Appendix I, p.30, the "Single Model Evaluation Mode
Prompt".** Its Role opens:

> "You are a Rigorous Scientific Origami Judge. Your primary objective is to
> evaluate a 3D-simulated fold based on its anatomical accuracy and biological
> proportions."

Its Input Data is:

> "**Visual Data:** Multiple 2D snapshots of the final 3D folded state from
> different angles."

And its Analysis Step 2 is, line for line, our `CRITERIA` tuple:

> "* Appendage Count: (Primary) ...
> * Topology: (Secondary) Do appendages emerge from the correct anatomical
> region (shoulders/hips)? ...
> * Proportionality: (Tertiary) ...
> * Differentiation: (Quaternary) Is there a clear geometric change between the
> head, neck, and body?
> * Aesthetic Refinement: (Quinary) Are the folds sharp and the symmetry
> balanced?"

The ordinals in `vlm_judge.CRITERIA` are that prompt's ordinals. The one-line
briefs are that prompt's sentences with the parenthetical examples stripped.
This is not an inspired-by; it is a transcription.

**COrigami's stick-figure judge is a different instrument, in a different
section, with different criteria.** Section 3.1 "Stick figure generation"
begins on p.4; its "VLM-Driven Refinement" paragraph is on **p.5**:

> "We use Gemini as a Vision-Language Model (VLM) to verify that the stick
> figure aligns with the intended target. The VLM is provided with the JSON
> description along with four 3D renderings of the stick figure from different
> viewpoints: Top, Side, Front, and Isometric. It evaluates the topology
> against four discrete criteria: **topological accuracy (validating the
> vertex/edge count against the semantic target), proportional feasibility,
> semantic recognisability, and structural complexity.** If the design score is
> too low, the LLM is asked to refine the stick figure design."

So `vlm_judge.py`'s own docstring (`:1-30`) argues at length that the stick
figure is the only artefact worth judging, ends with **"Never re-propose
showing this judge a folded base"**, and then applies the rubric written
exclusively for a folded base. The prompt contradicts its own provenance: the
criteria's Input Data line says "snapshots of the final 3D folded state", and
`SYSTEM_PROMPT` (`vlm_judge.py:243-250`) tells the judge it will never be shown
one and must not ask.

**That is the root defect. Every limitation this repo has measured on the judge
is downstream of it.**

### 1.2 The symptoms it explains

**(a) `aesthetic_refinement` is unanswerable by construction.** "Are the folds
sharp and the symmetry balanced?" -- a fold can be sharp only in a folded
model, and `SYSTEM_PROMPT` forbids showing one. `axis-a-verdict.md` section 2
recorded this and routed around it by gating on a two-criterion `anatomy`
statistic instead of `overall`; it did not remove the criterion, because
removing it was a rubric change and that unit was forbidden from making one.
1/15 of `overall` is still spent on a question the judge is told it will have
no evidence for.

**(b) `differentiation` describes a 3-D mass, not a graph.** COrigami's Role
text makes the intent explicit (Appendix I, p.30):

> "Any model that presents the body as a single, undifferentiated mass without
> clear transitions between major regions (such as Head vs. Thorax) will be
> disqualified."

A metric tree has no mass and no thickness. `build_payload`
(`vlm_judge.py:353`) exposes node ids, parentage and edge lengths -- every
internal edge is a 1-D segment. Asking whether the body reads as an
"undifferentiated mass" of a graph whose body **is one edge** is a category
error, and it carries 2/15.

**(c) `topology` is nearly unanswerable, and the reason is named joints.**
COrigami's own gloss is "the correct anatomical region **(shoulders/hips)**",
and their stick figure supplies exactly that. Appendix C.1, pp.21-22, every
stick is authored with a semantic name and **named joints**:

```json
{ "name": "front_left_leg", "start": "shoulders", "end": "front_left_paw",
  "length": 3, "azimuth_angle": 90.0, "elevation_angle": -90.0 }
```

Ours carries `{"id": 3, "parent_id": 2, "length": 0.02}`. Leaves get a
post-hoc geometric label guess; **internal nodes are anonymous integers**, and
the label's own `basis` string admits the convention is arbitrary ("the sign
convention is arbitrary and may be swapped"). The judge is asked whether a flap
emerges from the shoulder of a graph in which no node is a shoulder.

This is not speculation -- it is visible in corigami-1's measured results.
`axis-a-verdict.md` R1: stripping `leaf_labels` from all arms cost `topology`
far more than `appendage_count` on **all four** good arms (quadruped -0.075,
humanoid -0.125, bird -0.137, insect **-0.426**, the only cell clearing the
0.169 noise bar), while insect's `appendage_count` went **up** without labels.
Counting flaps needs no names; deciding where a flap emerges from leans on
names the tree does not have.

**(d) Gate C failed, and the rubric has no criterion for the thing that failed
it.** corigami-1's Gate C failed its row-max clause **3 of 5**
(`axis-a-verdict.md` R2). The recorded cause is that **subject difficulty is
not normalised**: the committed bird tree (4 leaves -- one mirror pair, a head,
a tail) scored **0.6653 as a fish** against **0.4097 as a bird**, because a
fish is a far less demanding target. COrigami's stick-figure rubric has two
criteria aimed at exactly that axis -- `semantic_recognisability` and
`structural_complexity` -- and ours has neither; recognisability is left
implicit and folded into `appendage_count`.

⚠ **This is an explanation offered, not a fix asserted -- and the mechanism by
which it could reach Gate C is INDIRECT.** Gate C is computed on `anatomy`
(section 3.1), which excludes both new criteria, so neither can move a Gate C
number by being scored. The only path by which the rewrite could move Gate C
is that giving recognisability its **own** criterion may stop it leaking into
the two that are gated -- corigami-1's judge had nowhere to put "this reads as
a plausible fish" except `appendage_count`, which is inside `anatomy`.
**That is a hypothesis, and section 3.4a pre-registers the report that
measures it.** Nothing in this document claims Gate C will pass.

### 1.3 Two provenance corrections carried into this record

Both were found by reading the paper rather than the docstring, and both
correct claims currently shipped in `vlm_judge.py`.

**Correction 1 -- the ablation numbers benchmark the FOLDED-MODEL judge, on
folded meshes.** `vlm_judge.py:56-58` credits "the structured rubric" with
"+8.5 accuracy points over a naive prompt (0.715 vs 0.631)", and `:83-86`
credits "0.766 at T=1.0 with N=4 ... and N=16 is WORSE (0.741)". Those are
**Table 2, p.9**, from **section 4.1 "VLM Evaluator Benchmarking"** (p.9),
measured on

> "a curated VLM origami evaluation dataset (with 87 positive examples and 152
> negative examples)"

of **folded models**. Part B's 0.715-vs-0.631 is Rubrics vs "Rubrics, V0" at
Flash `T=0.0, N=1`; Part A's 0.766-vs-0.741 is the `N` sweep at `T=1.0`. Not
one row of Table 2 evaluates a stick-figure judge. The numbers are real and
they are evidence for a rubric-shaped prompt in general; they are **not**
validation of the criteria this repo ships at the tree stage, and the docstring
reads as if they were.

Two smaller arithmetic notes, recorded so a future reader does not re-derive
them: 0.715 - 0.631 = **0.084**, so the docstring's "+8.5 accuracy points"
should be **+8.4**; and Part C's own baseline row is 0.715, so "pairwise beats
absolute, 0.811 vs 0.766" compares Part C's `Double` at `T=1.0, N=4` against
Part A's `Rubrics` at the same settings -- a fair comparison, but across two
parts of the table, which is worth saying once.

**Correction 2 -- COrigami DEPLOYED T=0.0, N=1, and we cite a row they did
not ship.** Section 3.8 "VLM feedback", p.8:

> "we utilize a Vision-Language Model (VLM), specifically Gemini 3 Flash ...
> with temperature of 0 and no majority voting (single call)"

and p.10, closing section 4.1:

> "Since performance gains at higher parameters were negligible, we defaulted
> to T = 0.0 and N = 1 for a computationally efficient, deterministic, and
> reproducible setup."

Our `N_SAMPLES = 4` / `TEMPERATURE = 1.0` (`vlm_judge.py:145-146`) cites Table
2's best-accuracy row, which is not the configuration COrigami operated.

**This wave KEEPS N=4 and T=1.0, and the reason is ours, not theirs.**
`_agreement` (`vlm_judge.py:654-668`) returns `None` below two samples by
deliberate design -- "one sample cannot disagree with itself" -- and the
cross-sample spread it reports is load-bearing three ways: it is the emitted
uncertainty estimate, it is what the **0.169** precision bar in section 3 is
derived from, and `axis-a-verdict.md` rule 2 requires it beside every quoted
score. At `N=1` there is no agreement, no interval, and no bar. Keeping N=4
buys an uncertainty estimate at a measured accuracy cost of nothing (0.766 is
Part A's best row anyway); it is **not** a claim that COrigami recommends it.

A third correction, smaller, belongs to the handoff that scoped this wave
rather than to the shipped code: the order-swap debiasing that Gate D adopts is
stated in **section 3.8, p.9**, not in Appendix I --

> "To mitigate proximity bias, we evaluate the models twice by swapping their
> presentation order. Refer to Section I for the prompt templates used in both
> modes."

Appendix I (p.31) carries the Comparison Judge Mode **prompt**; the swap
protocol is in the body text.

---

## 2. The new rubric

`CRITERIA` becomes COrigami section 3.1's four, in the order the paper lists
them, with weights **descending and distinct**, total **10**:

| # | key | weight | what it asks of a stick figure |
|---|---|---|---|
| 1 | `topological_accuracy` | **4**/10 | Does the vertex/edge count match what this subject needs, and does each appendage hang off the right part of the graph? |
| 2 | `proportional_feasibility` | **3**/10 | Are the edge lengths plausible proportions for this creature? |
| 3 | `semantic_recognisability` | **2**/10 | Shown this stick figure and nothing else, would a person name the subject? |
| 4 | `structural_complexity` | **1**/10 | Is the figure's complexity appropriate -- neither degenerate nor gratuitously detailed for the subject? |

### 2.1 Nothing is lost by dropping `appendage_count`

`appendage_count` is not deleted; it is **absorbed**, by COrigami's own
definition of the criterion that absorbs it. Their words for
`topological_accuracy` are "**validating the vertex/edge count against the
semantic target**" (section 3.1, p.5). Counting leaves against what the subject
needs *is* the vertex count against the semantic target. corigami-1's separate
`topology` -- "do appendages emerge from the correct anatomical region" -- is
the edge half of the same sentence.

So two criteria become one, and the one that survives is the one the artefact
can actually answer: a metric tree **is** a vertex/edge count. The 5+4 = 9/15 =
60% of `overall` that corigami-1 spent on the pair becomes 4/10 = 40% on the
merged criterion, with the freed weight going to two criteria that ask
something a stick figure can answer, rather than to two that ask about mass and
sharpness.

### 2.2 What the weights are, and are not

**COrigami assigns no weights and no ordinals to the four section-3.1
criteria.** The sentence lists them; it does not rank them. The ordering here
is the paper's listing order; **the weights are ours**, adapted from the
Appendix I prompt's primary/secondary/tertiary/quaternary/quinary structure and
from corigami-1's principle that *the weight IS the priority*, so that a later
criterion can never rescue an earlier failure. Descending and distinct is what
makes that principle enforceable: with 4/3/2/1 no combination of the bottom two
can outvote the top one.

That the weights total 10 and COrigami's own output scale is "a discrete
numerical score ranging from 0 to 10" (p.9) is a **coincidence**. It is
recorded here so no future reader infers a derivation that does not exist.

### 2.3 The five sites that must change together

⚠ **`CRITERIA` is NOT the only place the old criteria are written down, and
this is the single most expensive mistake available to the implementing unit.**
Only the numbered rubric list is generated from `CRITERIA`, by
`_rubric_block()` (`vlm_judge.py:232-238`). **Four other sites hardcode
corigami-1 criterion names in prose or in a key list**, and a unit that edits
`CRITERIA` alone ships a prompt whose rubric asks for four criteria and whose
required-output JSON demands five. `parse_sample` (`vlm_judge.py:609`, raising at
`:639`) then fails with `missing criterion 'topological_accuracy'` on every
reply, `aggregate` raises `no parseable samples`, and **all 212 billed calls in
section 5.2 buy nothing.**

The complete inventory, pre-registered so the failure cannot happen quietly:

| # | site | what is hardcoded |
|---|---|---|
| 1 | `CRITERIA` (`vlm_judge.py:153-164`) | the five `(key, ordinal, weight, brief)` tuples |
| 2 | `SYSTEM_PROMPT`'s OUTPUT block (`vlm_judge.py:294-305`) | the five literal JSON keys the reply must carry |
| 3 | `SYSTEM_PROMPT`'s stub-flap paragraph (`vlm_judge.py:285-288`) | "Count them against **APPENDAGE COUNT**" |
| 4 | `render_user_text`'s stub note (`vlm_judge.py:431-438`) | the same sentence again, in the **user** turn, fired whenever `stub_flaps > 0` |
| 5 | `probe_judge_battery.ANATOMY_CRITERIA` (`:164`), read by `anatomy_score` (`:333-345`) | `("appendage_count", "topology")` -- the two criteria the gated statistic is built from |

Sites 3 and 4 matter beyond the mechanical rename. Gate A forces `stub_flaps`
to 0 on every arm (section 3.2), so site 4 fires nowhere in the battery -- but
it fires on **real serves**: `fixtures/base_eval/quadruped.json` ships
`stub_flaps: 3`. Left unedited it would instruct a live judge to score against
a criterion corigami-2 has removed. Both sentences are re-pointed at
`TOPOLOGICAL ACCURACY`, which is the criterion that absorbs the count (section
2.1).

### 2.4 What is kept verbatim, and one divergence recorded rather than fixed

Two prompt details are **kept unchanged**, because COrigami's Table 2 Part B is
the only evidence anyone has about prompt shape and both come from the winning
variant:

1. "IGNORE COLOUR AND SHADING ENTIRELY ... single sheet of monochrome paper."
2. "SOME VIEWS WILL BE UNINFORMATIVE ... weight the views that most clearly
   show the correspondence."

The labels-are-guesses paragraph is kept too. It is this repo's own addition,
has no COrigami analogue, and is load-bearing for exactly the reason section
1.2(c) gives -- our labels are geometric guesses where COrigami's are authored.

⚠ **One divergence from COrigami is recorded here and deliberately NOT
fixed.** COrigami's prompts end "Provide your reasoning first, then the final
score as a number inside angle brackets" (Appendix I, p.30). Our
`SYSTEM_PROMPT` OUTPUT block (`vlm_judge.py:296-305`) does the opposite: the
numeric fields come first and `notes` last, and no instruction anywhere tells
the judge to reason before scoring. That is a real departure from the winning
variant and it may cost accuracy. **It stays as it is in this wave**, because
changing it would be a second simultaneous prompt-shape change and would make
corigami-1 and corigami-2 differ in two ways instead of one -- the confound
this document's whole bar-transfer argument (section 3.0) exists to avoid.
Recorded as a follow-up, with its own A/B, after corigami-2 is measured.

### 2.5 The advisory shape does not move

**Unchanged and non-negotiable**: `authority == "advisory"`,
`_assert_advisory_shape` (`vlm_judge.py:696`) refuses any gate-shaped key at
any depth, and `base_verdict` never reads the judge. Nothing in this wave may
put a model opinion on the acceptance path.

---

## 3. PRE-REGISTERED BARS

Fixed before the first billed call. Four gates, each independently reportable.

### 3.0 The bars are corigami-1's, verbatim, and that is the point

Gates A, B and C reuse `axis-a-verdict.md` section 3 **word for word**,
including the **0.169** least-significant-difference and the **0.80**
recognition bar. The reason is methodological, not lazy:

> **Change the rubric or change the bar -- never both.** corigami-1 and
> corigami-2 are two rubrics measured by the same experiment against the same
> numbers. If the bars moved too, a pass under corigami-2 would say nothing
> about whether the rewrite helped, because the two calibrations would not be
> comparable as decisions.

0.169 is inherited with its derivation intact: `_agreement` is `1 - 2*pstdev`
(`vlm_judge.py:654-668`), so at N=4 the 95% CI on a score runs +/-0.064
(agreement 0.93) to +/-0.119 (agreement 0.87), giving a least significant
difference of 0.091 (best) to **0.169 (worst)**. This document uses the worst
case, as corigami-1 did. Scores are emitted to six decimals against an interval
of +/-0.06 to +/-0.12; **the second decimal is the last one that means
anything**, and six are carried in tables only because the emitter produces
them.

⚠ **The bars are comparable. The SCORES are not.** corigami-1's `anatomy`
covered 9/15 = 60% of the rubric's weight; corigami-2's covers 7/10 = 70%, over
different criteria, elicited by a different prompt. A corigami-2 `anatomy` of
0.85 is **not** "better than" corigami-1's 0.80 on the same tree. That is
exactly what `RUBRIC_VERSION` exists to prevent (`vlm_judge.py:137-140`: "two
scores from different rubric versions are never silently compared"), and
section 5 makes the refusal executable.

### 3.1 The statistic the bars are set on

corigami-1 gated on the top two criteria renormalised:
`anatomy = (5*appendage_count + 4*topology)/9` (`probe_judge_battery.anatomy_score:333-345`).

**corigami-2 gates on the same shape, over its own top two:**

```
anatomy = (4 * topological_accuracy + 3 * proportional_feasibility) / 7   # in [0, 1]
```

**This is fixed now, before any number is seen.** The rationale, stated in full
because a pre-registration that hides its reasoning is a bar chosen later:

* **It is the same construction as corigami-1's** -- top two by weight,
  renormalised -- so the experiment is unchanged and the bar transfer in 3.0 is
  honest.
* **The reason for excluding the rest has CHANGED, and the change is worth
  recording.** corigami-1 excluded `differentiation` and `aesthetic_refinement`
  because the judge *cannot have evidence for them*. corigami-2 excludes
  `semantic_recognisability` and `structural_complexity` for a different
  reason: they are answerable, and they are **not about anatomical
  correctness**. `structural_complexity` measures a design's ambition, and a
  simple correct tree must not be marked down as anatomy for being simple.
* **`semantic_recognisability` is deliberately kept OUT of the gated
  statistic**, and this is the one choice a reader is most likely to challenge.
  It is the criterion most exposed to the confound that failed Gate C in
  corigami-1: "how recognisable is this?" folds together "how good is this
  tree" and "how forgiving is this subject", and a bird tree that reads as a
  plausible fish is the measured example. Putting it inside the bar would build
  the known cross-subject confound into the bar. It is scored and reported in
  every table -- it is simply not gated on.
* `overall` is reported beside `anatomy` in every table, as a consequence,
  never as a gate.

⚠ **The direct consequence, stated plainly so nobody has to discover it in the
results: every gate below is computed on `anatomy`, so
`semantic_recognisability` and `structural_complexity` contribute EXACTLY ZERO
to Gates A, B and C.** The two criteria added by the rewrite cannot move a
gated number. Section 3.4a adds a **reported** diagnostic over
`semantic_recognisability` so the hypothesis in 1.2(d) is measurable without
inventing a bar after the fact; it is a report, it gates nothing, and it is
fixed here rather than chosen later.

### 3.2 Gate A -- SEPARATION

> The confound-matched broken quadruped must score **below every one of the
> FOUR confound-matched good trees by more than 0.169** on `anatomy`.

Formally: `min(anatomy of the four good arms) - anatomy(broken arm) > 0.169`.

⚠ **The arm set is part of the bar and is pinned here.** The four good arms are
the four hand-authored `body_plans._PLANS` templates -- **quadruped, bird,
humanoid, insect** -- and nothing else. `fish` has no body plan and appears in
this wave only as a row and column of Gate C's 5x5 matrix. Admitting it to
Gate A or B would change Gate B's median set and void the "same experiment,
same bar" comparability section 3.0 rests on; it is the exact re-scope section
3.7 item 1 forbids. corigami-1's ground truth ruling carries over with it:
the positive control's correctness is a design fact about `body_plans._PLANS`,
never a reading of `fixtures/anatomy_reference.json`
(`axis-a-verdict.md` section 6).

**If Gate A fails, the corigami-2 rubric is not usable as a metric and this
wave must not steer by it.** That is the primary decision this file exists to
record, and a Gate A failure is a valid, publishable outcome: corigami-1 passed
Gate A at +0.676389, so a corigami-2 failure would be a measured regression and
would be recorded as one, not repaired by editing the prompt.

The confound controls are `axis-a-verdict.md` section 4's, **unchanged**:
labels synthesised from one shared vocabulary with one shared `basis` on every
arm; `stub_flaps` forced to 0 everywhere so the "count them against APPENDAGE
COUNT" paragraph fires nowhere; `served_leaves` set to each arm's own leaf
count; `served_fidelity` forced to **1.0 on every arm including the broken
one** (a deliberate lie in the broken arm's favour); a real prompt on every
arm; the broken arm re-run in the same batch; and every arm run twice, labelled
and labels-stripped.

### 3.3 Gate B -- RECOGNITION

> The **median `anatomy` of the same four good arms must be >= 0.80**.

Gate A alone is satisfiable by `good = 0.45, broken = 0.20`, which would mean
the judge never scores good work high -- and "a low score is not interpretable"
would survive the rewrite intact. Gate B is the half of the question corigami-1
asked and passed (median 0.899305 labelled, 0.816666 stripped); corigami-2 must
clear the same bar or the rewrite bought separation by lowering everything.

### 3.4 Gate C -- SUBJECT SENSITIVITY

Over the 5x5 swap matrix (5 committed trees x 5 subject names, diagonal re-run
in the same batch, tree bytes identical across each row so only `subject.name`
and `subject.prompt` move):

> `mean(anatomy of the 5 diagonal cells) - mean(anatomy of the 20 off-diagonal
> cells) > 0.169`, **and** the diagonal cell is the maximum of its own row for
> at least **4 of the 5 rows**.

Both clauses are corigami-1's, unedited, and the evaluator is corigami-1's
(`probe_judge_battery.gate_c:395-415`). corigami-1 split them: the mean clause
**passed** (+0.239653) and the row-max clause **failed** (3 of 5). The row-max
clause is the one this rewrite could conceivably move, by the indirect
mechanism in 1.2(d), and it is therefore the one that must not be softened.

⚠ **A property of the carried-over evaluator, recorded because section 4.4
depends on it.** The row-max clause is **non-strict**: `gate_c` scores a row as
a hit when `cells[(t, t)] == max(row.values())` (`probe_judge_battery.py:410`),
so a diagonal cell that merely **ties** its row counts as a hit. That is
corigami-1's behaviour, it is not edited here, and section 4.4's required-fail
input is written against it rather than against an idealised strict version.

⚠ **A note the corigami-1 record earned the hard way.** Its verdict table
annotated the C-fail row *"it is not reading the subject"*, and its own data
**falsified that annotation** -- holding a tree byte-identical and changing only
the subject moved the score by up to 0.5708. The rule survived; the rationale
did not. The same discipline binds here: if Gate C fails again, the recorded
outcome is the failure, and any explanation offered is post-hoc and labelled as
such.

### 3.4a Report C-R -- the same two clauses over `semantic_recognisability`

**REPORTED, NEVER GATED. Fixed here, before any call, so it cannot be chosen
after seeing the numbers.**

Over the same 5x5 swap matrix and the same 100 calls -- zero additional cost --
recompute both Gate C clauses on the raw `semantic_recognisability` score
instead of on `anatomy`, and report:

* `mean(diagonal) - mean(off-diagonal)` on `semantic_recognisability`;
* the row-max count on `semantic_recognisability`;
* per-row, the same two figures on `anatomy`, side by side.

The question it answers is 1.2(d)'s hypothesis, and only that question: **does
the criterion COrigami added for recognisability separate subjects better than
the anatomy criteria do?** A large C-R gap beside a small Gate C gap would say
the rewrite put the subject signal somewhere the bar cannot see, which is
useful and actionable. A C-R gap no larger than Gate C's would say the new
criterion adds nothing on this axis.

**No verdict in section 3.6 reads C-R.** It changes no cell of that table, it
may not be cited as a gate passing, and a future unit that wants it gated owes
a fresh pre-registration with its own bar.

### 3.5 Gate D -- COMPARISON MODE (new)

corigami-2 adds COrigami's **Comparison Judge Mode** (section 3.8, p.8;
prompt template Appendix I, p.31) alongside absolute scoring. Gate D is its
bar, and unlike A/B/C it has no corigami-1 predecessor -- **the bar is ours**,
and it is fixed here.

**The input set, fixed now.** Five pairs, one per committed
`fixtures/base_eval` subject (quadruped, bird, humanoid, fish, insect). Each
pair is that subject's committed served tree (arm **G**) against a
**deterministically degraded copy of itself** (arm **B**), degraded in the
shape the committed `broken_quadruped.json` fixture already carries. The pair
is **within one subject** by construction, which is corigami-1's standing
operational rule (never compare across subjects) applied to the experiment
rather than argued around it. Both arms carry Gate A's confound controls.

**The degradation rule, stated so that two implementers produce byte-identical
arm-B trees.** "Delete a mirror pair" is not deterministic on its own -- four
of the five subjects have more than one pair. The rule is:

1. Take `serve.pairs`, sort each pair's two ids ascending, then sort the
   resulting list. Keep only pairs **both of whose members are leaves**.
2. **Delete the first pair in that ordering** -- both leaves, and any internal
   node left childless by the deletion.
3. Multiply **every surviving leaf edge's `length` by 0.05**, rounded to 6
   decimal places, reproducing `broken_quadruped.json`'s second, independent
   defect (limbs at roughly 1/47th of the trunk they hang from).

Measured on the committed blobs, that rule selects: **bird `[2, 4]`, fish
`[5, 9]`, humanoid `[3, 4]`, insect `[1, 11]`, quadruped `[3, 4]`** -- a unique
answer on all five, with no subject falling through for want of a leaf-only
pair. Those five pairs are part of the pre-registration; an implementation that
selects differently is not running this gate.

**Clause 1 -- ordering.** For each pair, pool the samples from both
presentation orders and take the majority winner. **A tie counts as a
disagreement**, not as a pass.

> The pooled winner must be arm **G** on **>= 4 of the 5** pairs.

**Clause 2 -- order-swap consistency.** COrigami evaluates every comparison
twice with the presentation order reversed to mitigate proximity bias (section
3.8, p.9). Each pair is therefore judged in both orders at `N_SAMPLES = 4`,
giving 5 x 2 x 4 = **40 calls**. Let `p_AB` be the fraction of the four
AB-order samples that choose arm G and `p_BA` the same for the four BA-order
samples. Per-pair consistency is `1 - |p_AB - p_BA|`.

> The **mean** per-pair consistency over the 5 pairs must be **>= 0.80**.

Both clauses must hold for Gate D to pass, and the reason is that **pooling
hides exactly what clause 2 is for**. A purely position-biased judge pools to a
4-4 tie, which clause 1 already scores as a disagreement -- so clause 1 catches
the extreme case on its own. What it cannot catch is the *partial* case: a
judge that is right most of the time and drifts by one or two votes when the
order flips reads as a clean win after pooling, and the drift is invisible.
Clause 2 measures it before the pooling averages it away. In the other
direction, clause 2 without clause 1 would accept a judge that is perfectly
consistent and consistently wrong.

### 3.6 Verdict rule -- fixed in advance

| A | B | C | D | verdict |
|---|---|---|---|---|
| pass | pass | pass | pass | **usable as an absolute metric**, at 0.169 resolution, by absolute score **and** by Comparison Mode |
| pass | pass | pass | fail | **usable as an absolute metric**, at 0.169 resolution. Comparison Mode is NOT usable and must not be wired into any loop |
| pass | fail | pass | pass | **usable for RANKING only** -- a score may order two trees, never certify one. Comparison Mode is the preferred ranker |
| pass | fail | pass | fail | **usable for RANKING only**, absolute score only |
| pass | * | fail | pass | **usable for RANKING only, and only within one subject** by absolute score; Comparison Mode is usable, and is within-subject by construction |
| pass | * | fail | fail | **usable for RANKING only, and only within one subject.** Identical to corigami-1's shipped verdict -- the rewrite bought nothing on this axis |
| **fail** | * | * | * | **NOT USABLE.** Do not steer by it. Read the `reasons` as prose and nothing else |

⚠ **No cell of that table licenses comparing two DIFFERENT subjects' scores,
including the all-pass row.** Gate C's row-max clause is a statement *within* a
row -- one tree scored highest against its own subject name -- and says nothing
about whether the quadruped's 0.7 and the fish's 0.7 mean the same thing.
corigami-1's operational rule 3 ("never compare across subjects") therefore
stands until a unit pre-registers a bar that actually tests commensurability.
Its own suggestion is on the record and still unfitted: a tree's score against
its own subject minus its mean against the other four.

In every cell of that table the free-text `reasons` remain usable as prose.
That is the part corigami-1 **established** -- the judge named a missing
hind-limb pair, an absent mantle, a real proportion defect in a hand-authored
template (`body_plans`' humanoid gives arms and legs identical path length) and
a genuine omission (no antennae on the insect) that no deterministic instrument
in this repo can produce. A rubric change cannot take that away.

### 3.7 A failed gate is recorded, never repaired

This wave, unlike corigami-1's, **does** change production code -- that is its
whole purpose -- so `axis-a-verdict.md` section 7's "this unit changes no
production code" cannot be reused as the guarantee. The equivalent commitment,
binding on every unit in this wave:

1. **No bar in section 3 may be edited after the first billed call.** Not
   loosened, not re-scoped, not re-interpreted.
2. **The rubric text is not iterated until a gate passes.** One recorded
   rubric, one recorded measurement. If corigami-2 fails a gate corigami-1
   passed, that is the result, and the shipped rubric reverts or ships failing
   and labelled -- a decision for the results section, made after the numbers,
   about what to do, never about what the bar was.
3. **Loosening a gate to reach a headline is this repo's named recurring
   failure mode** (`CLAUDE.md` section 1.1, item 4, on
   `mv_symmetrize.MAX_ORBITS = 40`, which was *not* raised to admit
   quadruped's search). It is named here so nobody has to rediscover it.

---

## 4. The required-fail input for every gate

`COORDINATION.md` section 4.1, standing rule:

> **A metric ships with a known-bad input it is *required* to score as failing,
> asserted in a test. If you cannot construct one, the metric is vacuous and
> does not ship.**

The rule has caught four vacuous metrics in this repo, all the same shape --
*the metric cannot express the defect it is named after*. Five inputs, one per
gate plus one for the rubric itself:

### 4.1 The rubric -- `fixtures/vlm_judge/broken_quadruped.json`

The existing Gate A required-fail input, committed, 3117 bytes. Read as
follows:

* `subject.name = "quadruped"`, `subject.prompt = null`,
  `subject.source = "synthetic:broken-quadruped"`.
* `served_tree` is **5 nodes with 2 leaves** -- ids 3 and 4, both members of
  `pairs [[3, 4]]`, both labelled a "fore limb (pair 1)". A quadruped served
  with one pair of front legs, no hind pair, no head, no tail.
* The proportions are the second defect and they are independent of the first:
  the two surviving leaves are **`length 0.02`** against a trunk of
  `0.9 + 0.05`. A limb 1/47th the length of the body it hangs from.
* `requested_tree` had a sixth node (id 5, `length 0.2`) that did not survive;
  `shadow_diff.dropped = [1]`, `shadow_diff.invented = 5`.
* The honesty fields all read broken: `served_leaves 2`, `served_fidelity
  0.3333`, `stub_flaps 5`, `stubs 5`, `lint_class "MIXED"`,
  `invents_anatomy true`, `hull_coverage 0.44`.

⚠ **Under Gate A's controls those honesty fields are neutralised** (section
3.2): `stub_flaps -> 0`, `served_leaves -> the arm's own count`,
`served_fidelity -> 1.0`, a real prompt supplied. **The arm is broken only in
the tree.** A judge that scores it low must be reading the two-leaf,
0.02-length graph, because every number that would have given the answer away
has been set to the value a perfect serve would carry.

**Required to fail:** `anatomy(broken_quadruped) < min(anatomy of the good
arms) - 0.169`, under corigami-2 as under corigami-1.

### 4.2 Gate A -- two identical arms

The Gate A evaluator, handed the **same judgement** as both the good and the
broken arm, must report **FAIL**. A separation gate that passes on a null
comparison is vacuous. (corigami-1 ships this as
`test_required_fail_the_separation_gate_refuses_two_identical_arms`; it carries
over unchanged.)

### 4.3 Gate B -- a good set built from broken arms

The Gate B evaluator, handed a "good" set consisting of the broken arm
repeated, must report **FAIL**. A median-over-good-arms gate that cannot
report a low median is not measuring recognition.

### 4.4 Gate C -- a constant scorer

The Gate C evaluator, handed a 5x5 matrix in which **every cell carries the
same score**, must report **FAIL**. A subject-sensitivity gate that a constant
scorer passes measures nothing. This one matters more than it looks:
corigami-1's precision analysis observed that *"a judge that always returned
0.4 would be indistinguishable from three of the four readings"* it had at the
time.

⚠ **The assertion is on `passed`, and it is deliberately NOT a per-clause
assertion.** As section 3.4 records, the carried-over row-max clause is
non-strict (`cells[(t, t)] == max(row.values())`,
`probe_judge_battery.py:410`), so a constant matrix ties every row and reads
`row_max_hits == 5` -- the row-max clause **passes** on a constant scorer. The
existing suite already pins that behaviour
(`tests/test_vlm_judge.py:995` asserts `row_max_hits == 5` on a tied partial
matrix). The gate as a whole still fails, on the mean clause: `gap == 0.0`,
which is not `> 0.169`.

**The mean clause is therefore the one carrying Gate C's vacuity guard, and the
row-max clause is not a vacuity guard at all** -- it is a sharper instrument
that a constant scorer sails through. Recording that is the honest option;
making the clause strict would edit a bar section 3.0 transfers verbatim and
would break comparability with corigami-1's measured "3 of 5". **Do not make it
strict in this wave.** A future unit that wants a per-clause guard owes a
separate pre-registration.

### 4.5 Gate D -- a position-only judge, and a LIVE self-comparison

Two, because Gate D has two clauses, and they are **not the same kind of
test**.

**Clause 2 -- offline, free, and genuinely conclusive.** Handed synthetic
replies in which the judge always chooses the **second-presented** arm, the
consistency clause must report **FAIL** (`p_AB = 0`, `p_BA = 1`, consistency
0.0 on every pair). That is the exact proximity bias COrigami's order swap
exists to detect (section 3.8, p.9); a consistency statistic that cannot detect
it is decoration. The synthesis is legitimate here because the clause is a pure
function of vote fractions and the required-fail input **is** a vote-fraction
pattern.

**Clause 1 -- LIVE, and it has to be.** Handed a pair in which arm B **is arm
G** (byte-identical), the ordering clause must report **FAIL**: a pairwise
ranker that picks a confident winner between a tree and itself is reporting
position, not quality.

⚠ **This one cannot be synthesised, and an earlier draft of this section said
it could.** The clause-1 evaluator sees only per-order vote fractions, so
feeding it synthesised replies asserts nothing about the judge -- write "G wins
4 of 4 in both orders" and clause 1 passes on identical arms, which is the
tautology COORDINATION.md section 4.1 exists to catch. The required-fail input
is therefore a **live self-comparison**: one extra pair (`quadruped` G vs
`quadruped` G), both presentation orders, `N_SAMPLES = 4` -- **8 billed calls**,
included in section 5.2's budget.

Its bar, fixed here: over the 8 pooled samples, **no arm may take more than 6**.
A 7-of-8 or 8-of-8 preference between byte-identical trees is position bias and
**FAILS**. (An exact 4-4 split is not required -- at N=4 per order a 5-3 or 6-2
pooled split is inside the sampling noise the 0.169 bar is derived from.)

**Cost: four of the five required-fail inputs are offline and free. The fifth
costs 8 calls,** and pretending otherwise would make it the sixth vacuous
metric in COORDINATION.md section 4.1's table.

---

## 5. Versioning -- why both corpora are RE-RECORDED, not re-keyed

`RUBRIC_VERSION` moves `"corigami-1"` -> `"corigami-2"`
(`vlm_judge.py:137-140`).

### 5.1 The corigami-1 corpora are frozen, not deleted

| corpus | cases | recorded replies | recorded with |
|---|---|---|---|
| `fixtures/vlm_judge/replay.json` | 6 | **24** | (unstamped -- predates `recorded_with`) |
| `fixtures/vlm_judge/battery.json` | 35 | **140** | `{"model": "claude-sonnet-5", "temperature": 1.0}` |

They are the measured behaviour of the rubric this wave replaces, and
`axis-a-verdict.md`'s entire results section is derived from them. **Deleting
them would delete the only evidence that the rewrite was needed.** They keep
their `rubric_version: "corigami-1"` stamp, and **no reply in either is ever
edited, moved into a corigami-2 corpus, or re-keyed onto a corigami-2 prompt.**

### 5.2 Why a re-key is not enough

The two corpora have **two different rekeyers**, and it matters for the
argument. `vlm_judge.rekey_fixture` (`:871-892`) recomputes each case's
`prompt_digest` from `case["blob"]` on disk -- so it works for `replay.json`
and **raises `KeyError: 'blob'`** on `battery.json`, whose cases carry only
`name` / `prompt_digest` / `replies` and are rebuilt from a deterministic
builder instead. The battery's rekeyer is
`probe_judge_battery.rekey_battery` (`:603-618`), which
`axis-a-verdict.md` section 9 introduced for exactly that reason. Both share
the property that decides this section: **neither ever touches a recorded
reply**, deliberately, so that a prompt change cannot be laundered into a
different score.

That property, which is exactly right for a payload-builder refactor, is what
makes both the wrong tool here:

> A rubric change alters `SYSTEM_PROMPT`, so **all 41 case digests** across the
> two corpora move. Re-keying would produce corpora whose digests are current
> and whose **164 replies answer five criteria that no longer exist**,
> elicited by a prompt that now asks four. The staleness tests would go green
> over a corpus that is a lie.

Hence a re-**record**:

| what | calls |
|---|---|
| `replay.json`, 6 cases x N=4 | **24** |
| `battery.json`, 35 cases x N=4 (E1 40 + E2 100) | **140** |
| Gate D, 5 pairs x 2 orders x N=4 | **40** |
| Gate D clause-1 required-fail, 1 live self-comparison pair x 2 orders x N=4 (section 4.5) | **8** |
| **total** | **212** |

**212 billed calls** is the number this pre-registration commits to; a unit
that bills more owes an explanation in the results section. Report C-R (section
3.4a) is computed from E2's existing 100 and costs nothing.

### 5.3 The freeze must be executable, not a comment

Whatever file layout the implementing unit chooses (archived corigami-1 copies
beside re-recorded corigami-2 files, or new corigami-2 paths beside the
existing ones), one invariant is pre-registered here and must be asserted in a
test:

> **`ReplayClient` must REFUSE a corpus whose `rubric_version` is PRESENT and
> disagrees with `vlm_judge.RUBRIC_VERSION`** -- loudly, naming both versions
> -- rather than falling through to a `FixtureMiss` or, worse, replaying a
> corigami-1 reply against a corigami-2 prompt that happens to digest the same
> way.

⚠ **"Present and different", not "different or missing", and the distinction is
load-bearing in both directions.** `ReplayClient.__init__` accepts a bare dict
as well as a path, and existing callers construct corpora with **no**
`rubric_version` key at all -- `tests/test_vlm_judge.py:693` builds one inline,
and `probe_judge_battery.py:744` passes an in-memory `doc`. Implemented as
`doc.get("rubric_version") != RUBRIC_VERSION`, every one of those callers
starts raising and the change lands as a test-suite break with no bearing on
the freeze. But implemented as the loose check alone, an archived corigami-1
corpus with its stamp stripped would replay silently, which is the exact
failure this rule exists to prevent. Both horns are closed by pairing the
runtime check with a **second, separate assertion**:

> **Every corpus file committed under `mcp_harness/fixtures/vlm_judge/` must
> carry a `rubric_version` key**, asserted by a test that walks the directory
> rather than a hardcoded list of filenames -- so a corpus added later cannot
> arrive unstamped.

In-memory dicts stay exempt; files on disk cannot. Without both halves the
freeze is a convention two units have to remember, which is precisely the
argument `_assert_advisory_shape` already makes about the authority rule
(`vlm_judge.py:696-700`): put the refusal in the code.

---

## 6. Prior art (`CLAUDE.md` section 0, `AGENTS.md`)

### Surveyed

* **COrigami (arXiv:2606.26299v1)**, read in full rather than from this repo's
  summary of it. The load-bearing new reading is that the paper describes
  **two** VLM judges at **two** pipeline stages -- section 3.1 (stick figure,
  four criteria, four renderings, refine-or-accept) and sections 3.8 + Appendix
  I (folded model, five ordinal criteria, seven views, aesthetic reward) -- and
  that this repo shipped the second one at the first one's stage.
* **`axis-a-verdict.md`** (this repo, 2026-08-21), the corigami-1
  pre-registration and its 140-call measurement. Source of every bar in section
  3, of the confound controls in 3.2, and of four of the symptoms in 1.2.
* **GamiBench / ORIGAMISPACE / OrigamiBench** -- frontier VLMs near 43/100 on
  crease-pattern comprehension; GPT-5 flags valid folds impossible 24.6-25.0%
  of the time.
* **GPTeval3D (arXiv:2401.04092)** -- VLM-over-renders as a human-aligned
  evaluator of a generated asset against its prompt.
* This repo's measured dead ends: PR #78 (the folded base is illegible in 3-D
  at every camera angle), `base-inspection-loop-supersedes-judge` (the packing
  diagram is the only anatomy-legible view).

### Adapted -- and into which module

| adapted from | into |
|---|---|
| COrigami section 3.1's four criteria, in the paper's listing order | `vlm_judge.CRITERIA`, and through `_rubric_block` into `SYSTEM_PROMPT` |
| COrigami section 3.1's definition of `topological_accuracy` ("vertex/edge count against the semantic target") | the absorption argument in 2.1 -- why dropping `appendage_count` loses nothing |
| COrigami section 3.8 / p.9 order-swap debiasing | Gate D clause 2, and the Comparison Mode prompt |
| COrigami Appendix I's ordinal structure (weight IS priority) | the descending-and-distinct 4/3/2/1 weights in section 2 |
| COrigami Table 2 Part B's kept prompt details (ignore colour; weight the informative views) | `SYSTEM_PROMPT`, verbatim, unchanged from corigami-1 |
| `axis-a-verdict.md` sections 3 and 4 (bars, 0.169, confound controls) | sections 3.0-3.4 here, reused word for word |
| `COORDINATION.md` section 4.1 | section 4 here, five required-fail inputs |
| GamiBench's false-veto rate | the unchanged advisory rule in 2.3 -- nothing here can change what is served |

### Consciously rejected

* **COrigami Appendix C.1's NAMED joints and two angles**
  (`"start": "shoulders"`, `azimuth_angle`, `elevation_angle`). This is the
  root cause of symptom 1.2(c) and it is **not fixed in this wave**: naming
  internal nodes is a change to the Metric Tree schema, the mesh extractor and
  `body_plans`, none of which `vlm_judge.py` owns, and it would invalidate
  every committed fixture in the repo, not just the two judge corpora.
  Recorded as **the next lever**, and as the reason `topological_accuracy` is
  expected to remain the harder half of the `anatomy` statistic.
* **Adopting COrigami's deployed `T = 0.0, N = 1`.** It would make `_agreement`
  `None` on every judgement, which removes the uncertainty estimate, the
  derivation of the 0.169 bar, and the "report agreement beside every score"
  rule in one move. Rejected with the reason stated in 1.3 rather than
  miscredited to a row of Table 2.
* **Raising `N_SAMPLES` to 16** to shrink the interval. Table 2 Part A measures
  N=16 as **worse** (0.741 vs 0.766). Trading a measured accuracy loss for an
  unmeasured variance gain.
* **Replacing absolute scoring with pairwise ranking outright.** COrigami's
  double tournament is their best row (0.811, p.10, "deployed ... in practice")
  but a pairwise ranker **cannot certify a single tree**, and the absolute
  score is what `base_report` and the scorecard read. Gate D therefore **adds**
  Comparison Mode beside the absolute scorer instead of replacing it.
* **Showing the judge a folded base or a crease pattern.** Three measured dead
  ends. The irony is now on the record -- the rubric we shipped at the tree
  stage was written for exactly the artefact we proved unreadable -- and it
  changes nothing: never re-propose it.
* **Scoring against `fixtures/anatomy_reference.json`.**
  `axis-a-verdict.md` section 6's ruling is carried forward unchanged:
  `reference_count` answers "how many leaves did this extractor find?", not
  "how many appendages does this animal have?", and grading the judge against
  it re-closes the loop this whole arc exists to open.

### ⚠ One rejection from corigami-1 that NO LONGER APPLIES

`axis-a-verdict.md` section 10 rejected pairwise comparison with this reason:

> "Rejected for this unit: it is a change to `vlm_judge.py`'s prompt, which
> would invalidate every replay digest in the corpus"

**That cost is being paid anyway.** The corigami-2 rubric change invalidates
every digest in both corpora on its own (section 5.2), so pairwise mode is now
**free** on the axis that made it expensive. The rejection's premise is gone,
and Gate D exists because of it. The *other* half of that section's reasoning
-- "replacing the absolute scorer would answer a different question" -- still
holds, and is why Gate D adds a mode rather than swapping one.

---

<!-- ===================== END OF PRE-REGISTRATION ===================== -->
<!-- Everything above this line was committed before the first billed call.
     A sibling unit appends measured gate outcomes BELOW this line and must
     not edit a single character above it. -->

# RESULTS

**Everything above this line was committed before the first billed call.**

*Empty. Unit U3 appends the measured gate outcomes here.*
