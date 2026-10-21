# The judge gets a production caller — advisory, at the extraction seam

**Unit U1.** Status of this file when first committed: **PRE-REGISTRATION
ONLY.** Everything above the pre-registration line was written **before a
single billed call was made**, and the commit that contains it is the proof of
ordering. The results and the verdict are appended afterwards, in a later
commit, by a sibling unit, **without editing the bar**.

> A bar written after seeing the numbers is not a bar.

This file is the third in the judge series. Its two predecessors are
[`axis-a-verdict.md`](axis-a-verdict.md) (corigami-1: is the judge usable as a
metric at all?) and
[`corigami-2-stick-figure-rubric.md`](corigami-2-stick-figure-rubric.md) (was
it running the right rubric?). Neither is superseded. This one asks a
different question: **now that the instrument is calibrated, where does it
attach, and what may it be allowed to do?**

The short answer, and the whole design: **it attaches at the mesh→metric-tree
extraction seam, it is report-only, and the agent — not the code — decides
what to do with what it says.**

---

## 1. The seam, and why it is the only one

`server.reference_tree_from_query` (`server.py:4103`) is the **only point in
the process that holds the user's prompt and a `MeshTreeResult` at the same
time.** The prompt arrives as the function's argument; the result is bound at
`server.py:4152`:

```python
result = mesh_to_tree.auto_mesh_to_metric_tree(
    glb, reference_count=anatomy_expectation.reference_count_for(prompt))
```

and dies two lines later, at `server.py:4163`, when
`mesh_report.format_reference_report` (`mesh_report.py:622`) renders it to
prose and the object is dropped. `server.py:4154-4155`'s own comment already
records this in so many words — *"this is the ONLY point on the serve path
that holds a `MeshTreeResult`"* — which is why `_note_extraction`
(`server.py:2051`) was put there rather than anywhere downstream.

### 1.1 The serve record is the WRONG home, and this is measured, not aesthetic

The obvious alternative — hang the judge off `_LAST_SERVE`, beside every other
per-serve instrument — cannot work here, and `server.py:2071-2080` already
says why:

> `auto_mesh_to_metric_tree` compiles every candidate through
> `draft_and_compile_full_base` (`mesh_to_tree._default_compile_fn`) and
> therefore calls `_record_serve` **dozens of times** before this function
> returns.

One extraction therefore overwrites `_LAST_SERVE` dozens of times with
internal candidates nobody asked for. A judge attached there would score
whichever candidate happened to be compiled last — which is not the winner,
not the runner-up, and not anything the agent will ever see. The extraction
stash `_LAST_EXTRACTION` (`server.py:2048`) exists precisely because that
record is unusable for extraction-scoped facts; the advisory record joins it.

### 1.2 The shape

```
reference_tree_from_query(prompt)              server.py:4103
        |
        v
auto_mesh_to_metric_tree  ->  winner  +  runner_up  (U3; may be None)
        |                                mesh_to_tree.py:2545
        |
        |  IDE_JUDGE_LOOP=1 only; default OFF, byte-identical when off
        v
judge_loop.run(winner_blob, runner_up_blob, client)          (U4)
        +-- vlm_judge.judge(winner)            4 billed calls   vlm_judge.py:1684
        +-- judge_compare.compare(w, r)        2 billed calls   judge_compare.py:805
        |                                      (only if runner_up is not None)
        v
advisory record -> _LAST_EXTRACTION["judge_loop"] -> rendered into the report (U5)
        |
        v
THE AGENT reads it and decides. Nothing is re-ranked, re-searched, or rejected.
```

The two call costs are read off the modules, not assumed: `vlm_judge.N_SAMPLES
= 4` (`vlm_judge.py:445`) at `TEMPERATURE = 1.0` (`:446`), and
`judge_compare.N_SAMPLES_PER_ORDER = 1` (`judge_compare.py:334`) at
`TEMPERATURE = 0.0` (`:335`) over `ORDERINGS`' two presentations
(`compare()`, `judge_compare.py:847-851`) — 4 + 2 = **6 billed calls per
subject.**

### 1.3 The runner-up does not exist yet, and U3's job is to stop discarding it

`auto_mesh_to_metric_tree` keeps exactly one candidate, `held`, and overwrites
it in place:

```python
if (_serve_rank(candidate, anchor_r)          # mesh_to_tree.py:2958
        > _serve_rank(held, anchor_r)
        and _may_displace_a_protected_hold(candidate, held, anchor_r)):
    held = candidate                          # mesh_to_tree.py:2962
```

The displaced candidate is dropped with no reference kept. That is the
runner-up, and U3 retains it.

⚠ **THAT IS NOT THE ONLY SITE, AND A U3 THAT PATCHES ONLY IT CAPTURES A STALE
RUNNER-UP.** Found in review of this document, before U3 was written. `held` is
also reassigned inside **phase 3**: `_phase3_normalized_serve`
(`mesh_to_tree.py:2968`, defined at `:1994`) delegates to `_phase3_pass`
(`:2058`), which does its own `held = candidate` at **`mesh_to_tree.py:2154`**
under a *different* ranking key (`_p3_rank`, `:1889`, not `_serve_rank`). If
phase 3 displaces the voxel-loop winner, a runner-up captured only at `:2962`
is no longer the second-best — it is the tree that *used to be* first, and the
pairwise arm would silently be comparing the wrong pair. **U3 must capture the
displaced candidate at every site that reassigns `held`.** Phase 4
(`_phase4_admitted_serve`, `mesh_to_tree.py:2976`) is the one exception and is
documented as such in its own comment: *"It cannot displace a held serve at
all."*

⚠ **The runner-up will legitimately be `None` on some subjects, and that is a
property of the search, not a bug.** The exit that produces it is
**`mesh_to_tree.py:2932`** — the `return _confirmed(candidate)` inside `if held
is None:` (`:2905`), taken when the first compiled candidate reaches clamped
fidelity 1.0 at stage `none`. No hold was ever established, so there is nothing
to compare against. Claim 3 below is written around this.

⚠ **The OTHER `return _confirmed(candidate)`, at `mesh_to_tree.py:2950`, is a
different animal and must not be confused with it** — an earlier draft of this
document cited it for the no-hold case and was wrong. It sits in the `else:`
branch, reachable **only** when `held is not None`, so at that exit a genuine
runner-up (the standing `held`) is in hand and is discarded on the way out. U3
must capture it there too; a spec that treats `:2950` as "no runner-up" would
report `None` on exactly the subjects where a second-best existed.

### 1.4 Why the trigger is RELATIVE, never an absolute threshold

Gate C **failed** and its failure is the reason. The **E2** 5×5 swap matrix on
`anatomy` — E2, not E1; §3.2.1 says why the two are not interchangeable and
what it cost an earlier draft of this document to confuse them — reproduced
offline this session from the committed corigami-2 corpus with

```
cd mcp_harness && python probe_judge_battery.py --report
```

which replays the recorded replies and bills nothing — with no arm names given,
`main()` never constructs a live client at all (`probe_judge_battery.py:1612`
is reached without passing through the `judge_live.from_env()` branch at
`:1603-1610`):

| tree \ judged as | quadruped | bird | humanoid | fish | insect |
|---|---|---|---|---|---|
| quadruped | **0.4839\*** | 0.4929 | 0.3500 | *0.5536* | 0.4161 |
| bird | 0.2714 | **0.6143\*** | 0.2179 | *0.6661* | 0.2411 |
| humanoid | 0.5982 | 0.5589 | **0.7293\*** | 0.5446 | 0.3768 |
| fish | 0.6000 | 0.5696 | 0.3214 | **0.7448\*** | 0.4768 |
| insect | 0.2500 | 0.2429 | 0.2500 | 0.2286 | **0.6243\*** |

`GATE C  diagonal 0.639310  off-diagonal 0.411339  gap +0.227971; diagonal is
row max in 3/5 rows -> FAIL`

The byte-identical quadruped tree scores **higher as a fish (0.5536) than as a
quadruped (0.4839)**. An absolute threshold placed on this number would track
subject difficulty, not tree quality. The precision bar makes it worse: the
least significant difference is **±0.169** (`axis-a-verdict.md:44-58`) while
the module emits six decimals — *"the second decimal is the last one that means
anything"*.

The comparison the calibration **does** license is within-subject pairwise, and
`judge_compare.py` implements exactly that, with COrigami §3.8's order-swap
debiasing and a refusal (`shared_subject`, `judge_compare.py:375`) on any
cross-subject pair.

**Disagreement is the one actionable signal.** When `judge_compare.compare`
names the runner-up — `winner` is `"b"` where `"a"` is the served tree
(`judge_compare.py:855`, `:885`) — the deterministic `_serve_rank`
(`mesh_to_tree.py:1850`) and the semantic reading disagree about the same two
trees under the same subject. That is reported, and never acted on.

### 1.5 The three refinement levers — and a correction to the wave's framing

COrigami §3.1's refinement instructions are printed in prose and are quoted in
this repo at `axis-a-verdict.md:1267-1271`:

> *"to adjust stick lengths for accurate proportions, correct joint angles to
> resolve geometric overlaps, enforce mirrored angles for symmetric pairs (e.g.,
> left and right limbs), and add or remove nodes to better align with the
> target topology."*

⚠ **That is four levers of which TWO are angle-valued, not one.** The handoff
that scoped this wave described them as "adjust lengths, add/remove nodes,
enforce mirrored pairs, correct joint angles" and rejected one. The paper's own
words reject two: *"correct joint angles"* **and** *"enforce mirrored
**angles**"*.

Neither applies, for the same reason. `to_metric_tree`
(`mesh_to_tree.py:1403`) emits nodes carrying `id`, `parent_id` and `length`
and nothing else (`mesh_to_tree.py:1455`, `:1459`) — **the Metric Tree has no
angle field.** The judge sees angles at all only because `build_payload`
(`vlm_judge.py:1011`) *derives* them for the payload, *"only when a frame could
be derived and the tip was measured"* (`vlm_judge.py:1021-1022`), and reports
its own shortfall in `angle_coverage` (`:1261`). A derived quantity is not an
editable one.

So the surviving three are:

| lever | maps onto | provenance |
|---|---|---|
| adjust stick lengths | each node's `length` | COrigami §3.1, transcribed |
| add or remove nodes | the node list | COrigami §3.1, transcribed |
| enforce mirrored pairs | `symmetric_pairs` — membership and length equality | **adapted, not transcribed** |

The third is an **adaptation** and the record should say so: COrigami enforces
mirrored *angles*, we have no angles, and the only mirror structure our schema
carries is the `pairs` list `to_metric_tree` returns beside the nodes and
`MeshTreeResult.pairs` (`mesh_to_tree.py:599`) carries forward. Calling it a
transcription would be the same provenance error the corigami-2 wave was
written to fix.

**No lever is executed by this wave.** They are named so the advisory text can
speak in terms the agent can act on, and so a later unit cannot invent a fourth.

---

## 2. The three rails

Each is a rule, its citation, and the executable thing that enforces it.

### 2.1 The judge ranks; it never gates

* `judge()` stamps `"authority": "advisory"` (`vlm_judge.py:1739`) and
  `compare()` stamps the same (`judge_compare.py:872`).
* `_assert_advisory_shape` (`vlm_judge.py:1649`) walks **every key at every
  depth** and raises on any of **16** names — `accept`, `accepted`, `approve`,
  `approved`, `fail`, `failed`, `gate`, `invalid`, `ok`, `pass`, `passed`,
  `reject`, `rejected`, `valid`, `verdict`, `veto`
  (`vlm_judge.py:504-509`; counted, not estimated). `judge_compare` imports it
  rather than reimplementing it (`judge_compare.py:892`).
* `base_verdict` never reads `judge` — *"Reads `serve` and `metrics` only.
  Never reads `judge`."* (`base_verdict.py:111`) — and stamps
  `"judge_consulted": False` (`base_verdict.py:183`).

**Binding on this wave:** every dict `judge_loop` emits passes through
`vlm_judge._assert_advisory_shape` before it is returned, and nothing in
`server.py`, `mesh_to_tree.py` or `mesh_report.py` may branch on a judge score.
`winner` is permitted (it is a ranking word, and `judge_compare.py:242` records
the reasoning); `accept` and its fifteen siblings are not.

### 2.2 The judge may never set `R`

`docs/superpowers/plans/2026-08-29-anatomy-oracle-beyond-the-table.md:76`:

> **The oracle may never read the extracted skeleton.**

and its reason, at `:78-82`: a model asked *"how many appendages does a
pangolin have?"* is independent of the generator; a model asked *"look at this
skeleton and count its limbs"* **is the closed loop wearing a better
disguise.**

This is not an analogy here, it is the same wire. `R` — `reference_count` —
enters `auto_mesh_to_metric_tree` at `server.py:4152` and is the first argument
of `fidelity_score(candidate["leaves"], anchor_r)`
(`mesh_to_tree.py:3126`), which is `_serve_rank`'s **primary key**
(`mesh_to_tree.py:1867`). So a judge that reads a served tree and proposes a
reference count would be feeding the extractor's own output back in as its
ground truth, through the one key that decides which candidate is served.

**Binding on this wave:** `judge_loop` never writes `reference_count`,
`anchor_r`, `fidelity`, or any input to them, and no advisory field it emits
may be named or shaped so a later unit could plausibly wire it there. The
advisory record is *read by the agent*; it is not an argument to anything.

### 2.3 The digest surface is untouchable

**Not claimed by this wave, and not editable by any unit in it:**
`vlm_judge.SYSTEM_PROMPT` (`vlm_judge.py:578`), `vlm_judge.CRITERIA` (`:484`),
`vlm_judge.build_payload` (`:1011`), `vlm_judge.render_user_text` (`:1273`),
`judge_compare.COMPARE_SYSTEM_PROMPT` (`judge_compare.py:447`),
`judge_compare.render_compare_text` (`:568`).

**The exact count at risk, verified by reading the three corpora this
session:**

| corpus | `rubric_version` | cases | case digests | recorded replies | provenance |
|---|---|---|---|---|---|
| `fixtures/vlm_judge/battery.json` | `corigami-2` | 35 | 35 | **140** | `recorded_with {"model": "claude-sonnet-5", "temperature": 1.0}` |
| `fixtures/vlm_judge/replay.json` | `corigami-2` | 6 | 6 | **24** | `recorded_with {"model": "claude-sonnet-5", "temperature": 1.0}` |
| `fixtures/vlm_judge/compare.json` | `corigami-compare-1` | 3 | 3 + 1 top-level `system_prompt_digest` | 4 | `"provenance": "hand-authored"` — **nobody billed for these** |
| **total** | | **44** | **45** | **168 (164 billed)** | |

So: **45 digests, and 164 billed calls to re-record.** A prompt or payload edit
anywhere on that surface moves every one of those digests, and neither rekeyer
can repair the replies — `vlm_judge.rekey_fixture` and
`probe_judge_battery.rekey_battery` **by design never touch a reply**
(`corigami-2-stick-figure-rubric.md` §5.2). The corigami-2 wave paid that bill
five days ago. This wave does not re-pay it.

⚠ Note the asymmetry recorded in the table: `compare.json`'s four replies are
**hand-authored**, not recorded, and its own `note` says so at length. Any
statement this wave makes about pairwise behaviour that rests on the offline
corpus is a statement about **plumbing**, never about the model's judgement.
`recorded_with` is the field that tells the two apart; check it before trusting
any corpus.

---

## 3. THE PRE-REGISTERED CLAIMS AND THEIR BARS

Fixed before the first billed call. Four claims. Each has a bar, and each has a
**required-fail input** per `COORDINATION.md` §4.1:

> **A metric ships with a known-bad input it is *required* to score as failing,
> asserted in a test. If you cannot construct one, the metric is vacuous and
> does not ship.**

> **A metric that only ever goes up is not a measurement.**

### 3.0 What the numbers below are measured on

Three subjects, run through the real `reference_tree_from_query` path with the
offline `fake` provider: **`a dog`**, **`a bird`**, **`a spider`** (§5). **At
most** six billed calls each — four always, plus two only when a runner-up
exists — so **≤18 total** against a cap of 40 (§4). Under §3.3's own prediction
of a runner-up on 2 of 3, the expected spend is **16**.

Scores are reported to the emitter's six decimals and **read to two**
(`axis-a-verdict.md:56-58`). `agreement` is reported beside every score
(`axis-a-verdict.md` operational rule 2). A difference below **0.169** is not a
difference.

### 3.1 Claim 1 — the loop runs on real extracted trees

The judge has only ever been shown **committed fixtures** and **hand-authored
templates**. It has never been handed a `MeshTreeResult` the extractor produced
during the same call. That this works at all is a claim, not a given:
`build_payload` returns `None` — not a half-filled payload — when the blob
carries no served tree with leaves (`vlm_judge.py:1012-1016`), and a
freshly-extracted tree reaches it through a brand-new blob builder (U2) rather
than through `probe_base_eval.build_blob`.

> **BAR.** On all **3** measured subjects: `build_payload` returns non-`None`,
> and `judge()` returns a parsed judgement with **`n_parsed >= 3`** of
> `n = 4` (`vlm_judge.py:1743`).

**Required-fail input.** A `MeshTreeResult` with `nodes = []` — the shape
`auto_mesh_to_metric_tree` genuinely returns when nothing survives prefilter
anywhere (`mesh_to_tree.py:2983-2987`) and the shape
`format_reference_report` already handles (`mesh_report.py:625-627`).
`judge_loop` must record **"the input was unavailable"** and bill **zero**
calls. A loop that manufactures a judgement from an empty extraction is
measuring its own defaults.

### 3.2 Claim 2 — Gate B has never been measured on an extracted tree

**Every arm that established Gate B is a hand-authored `body_plans` template.
The three subjects in this wave are the first extracted trees the judge will
ever score under a pre-registered bar.** That is the claim, and it is a first
measurement rather than a re-run.

The good arms are `E1_PLANS = body_plans.NAMES` (`probe_judge_battery.py:340`),
which is `('bird', 'humanoid', 'insect', 'quadruped')` — **four**, all built by
`body_plans.template()` (`probe_judge_battery.py:477`), the module whose own
opening line calls them *"The four known-good body-plan templates"*
(`body_plans.py:1`).

#### 3.2.1 The two experiments, labelled, so the conflation cannot recur

⚠ **E1 and E2 are different experiments and their numbers are NOT
interchangeable.** An earlier draft of this document read E2's diagonal against
Gate B's bar and concluded "zero of five clear it". **That was wrong, and the
mechanism is worth stating precisely because the repo has been here before.**
Both are reproduced offline, free, by `cd mcp_harness && python
probe_judge_battery.py --report`:

**E1 — Gate B's actual inputs** (hand-authored templates, confound-matched):

```
e1_good_bird       0.846429
e1_good_humanoid   0.755357
e1_good_insect     0.781071
e1_good_quadruped  0.882143
GATE B  median anatomy 0.813750  bar >= 0.8  ->  PASS      (labelled)
GATE B  median anatomy 0.766964  bar >= 0.8  ->  FAIL      (labels stripped)
```

**E2 — Gate C's inputs** (the committed extracted serves, verbatim). Diagonal:
quadruped **0.4839**, bird **0.6143**, humanoid **0.7293**, fish **0.7448**,
insect **0.6243**.

**So Gate B under corigami-2 PASSES at 0.813750. It did not go to zero.** The
stripped arm's 0.766964 FAIL is the known bar-crossing *inside* the noise floor
— a −0.050 move against a 0.169 LSD — not a regression.

**Why the E2 diagonal is not commensurable with that bar, read out of
`build_case` (`probe_judge_battery.py:465-495`).** It is *not* that E2 "asks a
different question": the diagonal cell asks the correct subject, exactly as E1
does. It is that **two things move at once**:

| | E1 good arms | E2 cells |
|---|---|---|
| tree | `body_plans.template()` — hand-authored (`:477`) | `copy.deepcopy(src["serve"])` from `fixtures/base_eval/` — **the extracted serve, verbatim** (`:474`) |
| `stub_flaps` | forced **0** (`_serve_block`, `:450`) | real — `quadruped` ships **3** |
| `served_fidelity` | forced **1.0** (`:452`) | real — quadruped **0.8333** |
| `leaf_labels` | synthesised on one `SHARED_BASIS` (`:442-443`) | real extractor labels and bases |
| `mesh_provider` | `"hand-authored"` (`:492`) | `"fixture"` (`:471`) |

`stub_flaps > 0` additionally fires `render_user_text`'s stub paragraph —
*"Count them against TOPOLOGICAL ACCURACY"*, `vlm_judge.py:1286-1294` — which
fires on **no** E1 arm, because E1 forces the count to 0.

**This repo already wrote the warning, and I walked into it.**
`axis-a-verdict.md:533-542`, on the same two numbers under corigami-1:

> ⚠ **That pair is NOT confound-matched and must not be quoted as if it were.**
> … The comparison is therefore between two *products*, not two trees — which
> is the honest reading for "how good is what the pipeline ships", and the
> wrong reading for "how good is the tree". Closing that gap into a clean
> tree-only comparison would need a sixth E1 arm carrying the extracted
> quadruped tree under E1's matched fields, **and it was not run.**

The measured size of the gap, corigami-1: hand-authored quadruped **0.972222**
against extracted quadruped **0.420833** — *"roughly half the range"*
(`axis-a-verdict.md:527-530`). **Claim 2 is that never-run sixth arm,
generalised to three subjects.**

#### 3.2.2 The bar, and what kind of reading it is applied to

> **BAR, reused VERBATIM from `axis-a-verdict.md`'s "Gate B — RECOGNITION"
> (under its §3 PRE-REGISTERED BARS, carried into
> `corigami-2-stick-figure-rubric.md` §3.3):**
>
> > The **median `anatomy` of the good arms must be >= 0.80**.
>
> applied to the three subjects of §3.0, on `probe_judge_battery.anatomy_score`
> (`probe_judge_battery.py:510`) over
> `ANATOMY_CRITERIA = ("topological_accuracy", "proportional_feasibility")`
> (`:259`) — the same statistic, the same arithmetic, the same 0.80.

The bar is reused word for word **so the two calibrations stay comparable**,
per `corigami-2-stick-figure-rubric.md` §3.0's *"Change the rubric or change
the bar — never both"*, applied to a change of population instead of a change
of rubric.

⚠ **The reading will be a PRODUCT reading, and it is pre-registered as such.**
The loop judges the extraction **as the pipeline actually ships it** — real
`stub_flaps`, real `served_fidelity`, real extractor labels — because that is
what a report-only advisory block must describe. So the resulting median is
commensurable with **E2's** construction, not with E1's, and **it may not be
quoted against E1's 0.813750 without repeating the sixth-arm caveat above.**
Fixing that here, before the calls, is the whole point: it is the one thing
`axis-a-verdict.md` said was missing, and it stays missing — this wave measures
the product, and says so.

⚠ **NO EXPECTATION IS PRE-REGISTERED, AND THAT IS DELIBERATE.** An earlier
draft wrote *"this bar is expected to FAIL"*, reasoning from the E2 diagonal.
With the conflation removed, that reasoning is gone: **there is no prior for an
extracted tree scored under a pre-registered bar, because it has never been
done.** Inventing one would be the same error as inventing a "good" value for
Claim 4, and the posture here is therefore identical to Claim 4's — **state the
bar, report the outcome either way.** A pass is informative; a failure is
informative; neither was predicted.

**A failure here is REPORTED, NOT REPAIRED.** Binding, and inherited verbatim
from `corigami-2-stick-figure-rubric.md` §3.7: no bar in this section may be
edited after the first billed call; not loosened, not re-scoped, not
re-interpreted. **Loosening a gate to reach a headline is this repo's named
recurring failure mode** (`CLAUDE.md` §1.1 item 4, on `mv_symmetrize.MAX_ORBITS
= 40`, which was *not* raised to admit quadruped's search). A Claim-2 failure
means the advisory text says so beside every extracted tree; it does not mean
the loop is rebuilt until the number moves, and it does not mean the judge
stops being wired in — **report-only is exactly the authority a failing bar
licenses.**

**Required-fail input.** The Gate B evaluator handed a "good" set consisting of
`fixtures/vlm_judge/broken_quadruped.json`'s judgement repeated must report
**FAIL** (`corigami-2-stick-figure-rubric.md` §4.3, carried over unchanged). A
median-over-good-arms statistic that cannot report a low median is not
measuring recognition.

### 3.3 Claim 3 — the runner-up arm exists

The pairwise half of the loop runs only when `auto_mesh_to_metric_tree` had a
second candidate to discard (§1.3). Whether it ever does on a real subject has
never been measured, because nothing ever kept one.

> **BAR — PREDICTION, STATED BEFORE MEASURING.** I expect a non-`None`
> runner-up on **2 of 3** subjects.
>
> Reasoning, so the prediction is falsifiable rather than decorative: the only
> exit that yields no runner-up is `mesh_to_tree.py:2932` (§1.3), which fires
> for a candidate reaching clamped fidelity 1.0 at stage `none` while `held is
> None` — a first-try exact pack, no hold ever established. The nearest
> committed proxy is
> `fixtures/scorecard_baseline.jsonl`'s `attempt0_pack` column, which reads
> **`bird` True, `humanoid` True, and `quadruped` / `fish` / `insect` False** —
> three of five subjects reach the serve through something other than an
> attempt-0 pack. So of my three subjects I expect `a bird` to exit early and
> `a dog` (quadruped) and `a spider` (insect) to leave a runner-up behind.
>
> ⚠ The proxy is not the predicate. `attempt0_pack` is a property of the
> **packer's** first attempt; `mesh_to_tree.py:2932` gates on the candidate's
> clamped fidelity **and** its stage **and** `held is None`. They agree in
> spirit and may disagree on a row. The prediction is mine and it is offered as
> falsifiable, not as derived.
>
> **The commitment is to report the ACTUAL fraction, whatever it is.** If it is
> **0/3**, the pairwise half of the loop is **unexercised**, and that is the
> finding — reported as such, not worked around by synthesising a second arm.
> A comparison against a tree the search never produced would measure nothing.

**Required-fail input.** `judge_compare.compare` handed the winner as **both**
arms must not report a confident winner. The module already carries the
machinery to detect it — `arms_identical` compares the two `payload_digest`s
(`judge_compare.py:881-882`) and `tie_reason == "order_flip"`
(`judge_compare.py:863`) is what a position-only judge produces. `judge_loop`
must **refuse to call** on an identical pair rather than bill for it. A
pairwise arm that reports a winner between a tree and itself is reporting
position, not quality (`corigami-2-stick-figure-rubric.md` §4.5).

### 3.4 Claim 4 — disagreement rate

How often does `judge_compare.compare` name the runner-up, against
`_serve_rank`'s choice of the winner?

> **BAR: report it. Do NOT pre-commit to a "good" value.**

The reason, stated so the absence of a bar is a decision and not an omission:
**there is no prior.** This comparison has never been run — not on a fixture,
not on a template, not once. The rate is a joint property of `_serve_rank`'s
four keys (`mesh_to_tree.py:1867-1870`) and a judge whose within-subject
ordering has never been validated against a deterministic ranker on anything.
Any number written here would be an invention, and a bar invented to be met is
the exact failure `axis-a-verdict.md`'s opening line names.

A rate of 0 and a rate of 1 are both interesting and neither is "bad": 0 says
the two instruments agree on this population, 1 says they never do. Both are
reported with N beside them, and N is at most 3.

⚠ **Reporting a rate is not licensing an action.** Even a 3-of-3 disagreement
does not re-rank anything in this wave. Acting on it would need a fresh
pre-registration with a bar that tests whether the judge's ordering is *better*
than `_serve_rank`'s — which needs a ground truth neither instrument has, and
which rail 2.2 forbids asking the judge to supply.

**Required-fail input.** The disagreement statistic, computed over a set in
which every `compare()` result carries `winner: None` (both undecided, or
order-flipped), must report **"undetermined"** and must **not** report `0.0`.
Reporting a rate of zero from pairs that produced no verdict would be
indistinguishable from perfect agreement — the same shape as the four vacuous
metrics in `COORDINATION.md` §4.1, where *the metric cannot express the defect
it is named after*.

---

## 4. Cost budget — a hard cap

| item | calls |
|---|---|
| absolute judge, 3 subjects × `N_SAMPLES = 4` | **12** |
| pairwise compare, ≤3 subjects × 2 orderings × `N_SAMPLES_PER_ORDER = 1` | **≤6** |
| **expected total** | **≤18** |
| **HARD CAP** | **40** |

A unit that bills more than 40 owes an explanation in the results section.

**Ledger, complete as of this commit: ~11 calls have been spent, and NONE of
them measured anything in §3.** The coordinator ran a temperature-deprecation
matrix and one pairwise comparison as **diagnostics against the API** before
this document existed. They are recorded here so the ledger is honest and so
nobody later mistakes them for a claim's first measurement; they are **not**
counted against the 40-call cap, because the cap governs measurement against
these bars. **Every bar in §3 remains unmeasured at the moment this file is
committed**, which is the property the pre-registration exists to establish.

**Meshes are free.** The provider is the offline `fake`
(`mesh_acquire.FakeMeshProvider`, `mesh_acquire.py:75`), which copies a
committed fixture `.glb` chosen by `_fixture_for_prompt`
(`mesh_acquire.py:61-66`); no mesh generation API is touched and
`MESH_PROVIDER` is left at its default `"fake"` (`server.py:4139`).

**The four required-fail inputs in §3 are all offline and cost zero.** That is
deliberate and it is the cheap half of §4.1's rule; it is also why the
identical-arms case is written as a *refusal to call* (§3.3) rather than as a
live self-comparison. The corigami-2 wave had to pay 8 calls for its
clause-1 required-fail input because it was gating on the ordering clause
(`corigami-2-stick-figure-rubric.md` §4.5). **This wave gates on nothing, so it
does not owe that call.** If a later unit wants the ordering clause as a gate,
it owes both the pre-registration and the 8 calls.

---

## 5. The subjects, and the substitution

The measurement runs three prompts through the real tool with the offline
provider:

| prompt | mesh | why |
|---|---|---|
| `a dog` | `quadruped.glb` | no keyword matches; falls to `DEFAULT_FIXTURE` |
| `a bird` | `bird.glb` | `"bird"` |
| `a spider` | `insect.glb` | `"spider"` |

Verified by calling `mesh_acquire._fixture_for_prompt` on each
(`mesh_acquire.py:61`).

**The fake provider distinguishes exactly five meshes.**
`_FIXTURE_KEYWORDS` (`mesh_acquire.py:52-57`) is four rows —
`(insect|bug|beetle|spider|wasp) → insect.glb`,
`(bird|eagle|owl|sparrow|hawk) → bird.glb`,
`(fish|shark|trout|salmon) → fish.glb`,
`(human|person|humanoid) → humanoid.glb` — plus `DEFAULT_FIXTURE`
`quadruped.glb` (`mesh_acquire.py:47`). Those five are **precisely** the five
scorecard fixtures, and `ls mcp_harness/fixtures/*.glb` returns exactly those
five files.

⚠ **`octopus` and `lizard` were the originally-named subjects, and both
collide.** Neither matches any keyword, so both route to `quadruped.glb`:

```
'an octopus' -> quadruped.glb
'a lizard'   -> quadruped.glb
```

Running the loop on "an octopus" under the fake provider would judge a
**quadruped mesh** against the subject name "octopus" — reproducing Gate C's
confound as the experiment rather than avoiding it. They are replaced by `a
dog` and `a spider`. **The count is unchanged (3) and the budget is unchanged
(§4).**

This is a fixture-routing fact, not a claim about the extractor: on a live
provider both prompts would produce their own meshes, and this repo has
measured the octopus extraction at length
(`extraction-fidelity-wave-12-units`). The substitution is about what the
**offline** provider can distinguish.

---

## 6. What this explicitly does NOT do

Recorded so a later reader cannot mistake the scope, and so a later unit cannot
quietly widen it:

1. **No auto re-search.** A low score, a disagreement, and a refusal all leave
   `auto_mesh_to_metric_tree` untouched. The search runs once.
2. **No auto tree edit.** The three levers in §1.5 are named for the agent's
   benefit. No code in this wave adds, removes, re-parents or re-lengths a
   node, and none touches `symmetric_pairs`.
3. **No threshold on the absolute score.** §1.4 is the reason. There is no
   number the loop compares a score against, anywhere.
4. **No change to `_serve_rank`** (`mesh_to_tree.py:1850`). Its four keys,
   their order, and `_best_possible_rank`'s matching arity
   (`mesh_to_tree.py:1873`) are untouched. U3 retains a reference to a
   candidate the ranker already rejected; it does not change the rejection.
5. **No change to what is served.** With `IDE_JUDGE_LOOP` unset — the default —
   the extraction path is **byte-identical**. With it set, the served tree is
   still `held`, the report still renders `format_reference_report`'s existing
   body, and the advisory block is **appended**.

   ⚠ **"Byte-identical" binds U3 too, and U3 is NOT behind the flag.** Raised
   in review of this document. U3 changes `auto_mesh_to_metric_tree` itself, so
   the flag cannot protect it: if the runner-up is carried as a new
   `MeshTreeResult` field (`mesh_to_tree.py:599`), every consumer that
   serialises that dataclass sees a new key — including the committed
   extraction snapshots, which `.github/workflows/ci.yml:88-93` describes as
   *"exact-match 'drift tripwires'"* and locates in
   **`test_gate_mesh_region.py`** and **`test_mesh_to_tree.py`'s body-plan
   cases**. Two constraints, pre-registered here rather than left to the
   implementing unit: the runner-up must ride a field that **defaults to
   `None`** and is **excluded from any serialised snapshot comparison**, and U3
   must show those snapshots **unchanged** before it merges. Retaining a
   reference the search already computed must cost nothing; if it cannot be
   made to, U3 says so rather than re-blessing a tripwire.
6. **No change to `base_verdict`, the scorecard, or any acceptance rule.**
   `judge_consulted` stays `False` (`base_verdict.py:183`).
7. **No edit to the digest surface** (§2.3). Zero of the 45 digests move; zero
   of the 164 billed replies are stranded.

---

## 7. Prior art (`CLAUDE.md` §0)

### Surveyed

* **COrigami (arXiv:2606.26299v1, Google DeepMind).** §3.1's VLM-Driven
  Refinement is the direct ancestor of this loop: a VLM verifies the stick
  figure against the intended target and *"if the design score is too low, the
  LLM is asked to refine the stick figure design"* (quoted at
  `corigami-2-stick-figure-rubric.md:73-82`). Its four refinement instructions
  are quoted at `axis-a-verdict.md:1267-1271`. ⚠ **The paper is not in this
  repo** — no PDF, no local copy; `find . -iname "*corigami*"` returns only our
  own three files. Every COrigami citation in this document is therefore
  **second-hand, from the two committed decision records**, both of which state
  they read the PDF with `pdftotext -layout`. Said plainly rather than implied,
  because miscrediting COrigami is the exact defect the corigami-2 wave existed
  to fix.
* **This repo's own two judge records**, `axis-a-verdict.md` (corigami-1
  pre-registration and its 140-call measurement) and
  `corigami-2-stick-figure-rubric.md` (the rubric rewrite). Source of the 0.169
  LSD, Gate B's bar, the confound controls, and the "recorded, never repaired"
  discipline.
* **`docs/superpowers/plans/2026-08-29-anatomy-oracle-beyond-the-table.md`** —
  the closed-loop rule that rail 2.2 is an instance of.
* **RTLFixer (NVIDIA, DAC'24, arXiv 2311.16543)**, **CADSmith (arXiv
  2603.26512)** and **"Is Self-Repair a Silver Bullet?" (ICLR'24, arXiv
  2306.09896)** — already adapted in this repo at
  `docs/superpowers/plans/2026-07-25-perfect-base-slices.md:36-38`, and named
  together at `2026-08-29-anatomy-oracle-beyond-the-table.md:80-82` as reducing to the one
  rule in 2.2.
* **Critic-agent loop practice, 2026** (surveyed this session). The pattern
  this design matches is the one that literature converges on independently: a
  critic model judges rather than redoes, its critique is machine-readable so a
  caller can branch, and the refine loop is capped with an honest escalation
  rather than run to convergence. Where the survey and this design part company
  is *who* branches: the published loops branch in code. Here the branch is the
  agent's, because §1.4's measured confound says the code has no threshold it
  could honestly branch on.

### Adapted — and into which module

| adapted from | into |
|---|---|
| COrigami §3.1's refine-or-accept loop at the stick-figure stage | the whole design: judge at the tree, never at a base or CP |
| COrigami §3.1's *"adjust stick lengths"* and *"add or remove nodes"* | §1.5's levers 1 and 2, named in the advisory text (U5) |
| COrigami §3.1's *"enforce mirrored angles"*, **degraded onto a schema with no angles** | §1.5's lever 3 — `symmetric_pairs` membership and length equality |
| COrigami §3.8's order-swap debiasing | already shipped in `judge_compare.compare`; this wave is its first caller |
| CADSmith's inner-loop / outer-loop split, with a separate judge role | `judge_loop` as a module the extractor does not import: the search runs, then the judge speaks, and the search never hears the answer |
| RTLFixer's error→recipe table shape | rejected here, and the rejection is below |
| `axis-a-verdict.md`'s "Gate B — RECOGNITION" bar (0.80 on `anatomy`) and its 0.169 LSD | §3.2, reused verbatim so the two calibrations stay comparable |
| `corigami-2-stick-figure-rubric.md` §3.7 ("a failed gate is recorded, never repaired") | §3.2's binding paragraph |
| `COORDINATION.md` §4.1 | the four required-fail inputs in §3 |

### Consciously rejected

* **An absolute score threshold.** §1.4: the same tree scores higher as a fish
  than as a quadruped, and the diagonal is row max in only 3 of 5. A threshold
  would encode subject difficulty. Rejected on measured evidence, not taste.
* **Automatic re-search on a low score** — the shape RTLFixer and CADSmith both
  use. Their loops have a *deterministic* error signal (a compiler diagnostic, a
  kernel measurement); ours would have a model opinion with a ±0.169 interval
  driving a search whose primary key is `fidelity_score`. That is rail 2.2's
  closed loop with extra steps. The deterministic half of that pattern is
  already shipped here as the rescue ladder and `error_recipes`.
* **Gating the serve on the judge.** Forbidden by rail 2.1 and by
  `axis-a-verdict.md`'s standing verdict — *usable for ranking, within one
  subject.* Wiring it as a gate would require all four measurements
  `vlm_judge.py`'s authority-rule section names, and none has been made.
* **Gating on `semantic_recognisability`, despite it being the live lead.**
  Report C-R measured it at **row max 4/5 — Gate C's own bar** — against
  `anatomy`'s 3/5 (reproduced offline this session). It is the most promising
  number in the corpus and it is deliberately **not** used here:
  `probe_judge_battery.py:264` names it `REPORTED_CRITERION` precisely so the
  reported/gated boundary is one editable line, and
  `corigami-2-stick-figure-rubric.md` §3.4a says gating it *"owes a fresh
  pre-registration with its own bar."* This wave does not write that
  pre-registration, and it does not sneak the criterion in through an advisory
  side door either.
* **Hanging the loop off `_LAST_SERVE`.** §1.1: one extraction overwrites it
  dozens of times with internal candidates. Measured behaviour, documented in
  `server.py:2071-2080` before this wave existed.
* **Synthesising a runner-up when the search produces none.** §3.3: a
  comparison against a tree the search never produced measures nothing. `0/3`
  is a finding; a fabricated second arm is not.
* **Showing the judge a folded base or a crease pattern.** Three measured dead
  ends (PR #78; `base-inspection-loop-supersedes-judge`;
  three independent CP-comprehension benchmarks near 43/100). Never
  re-proposed.

---

<!-- ===================== END OF PRE-REGISTRATION ===================== -->
<!-- Everything above this line was committed before the first billed call.
     A sibling unit appends measured outcomes BELOW this line and must
     not edit a single character above it. -->

# RESULTS

**Everything above this line was committed before the first billed call.**

**Measured 2026-08-30. 16 billed calls, exactly the pre-registered budget
(3 x 4 absolute + 2 x 2 pairwise on the one subject with a runner-up), against
a hard cap of 40. Model `claude-sonnet-5`. Meshes free (fake provider,
committed fixtures). Reproduce with:**

    cd mcp_harness && MESH_PROVIDER=fake PYTHONPATH=. \
        .venv/bin/python probe_judge_loop.py --live --compare-n 2

## The four claims

| claim | bar | measured | verdict |
|---|---|---|---|
| 1. the loop runs on extracted trees | 3/3 judgeable, `n_parsed >= 3` | 3/3, `n_parsed = 4` on all three | **PASS** |
| 2. Gate B on extracted trees | median `anatomy` >= 0.80 | **0.814286** | **PASS** |
| 3. a runner-up exists | report the fraction | **1 of 3** | reported |
| 4. disagreement rate | report it | **0 of 1 decidable** | reported |

## Claim 2 — the sixth arm, finally run

`anatomy_score = (4*topological_accuracy + 3*proportional_feasibility)/7`.

| subject | topo | prop | seman | struct | **anatomy** | overall |
|---|---|---|---|---|---|---|
| a dog | 0.9300 | 0.6800 | 0.7625 | 0.8450 | **0.8229** | 0.8130 |
| a bird | 0.4500 | 0.5625 | 0.5000 | 0.5125 | **0.4982** | 0.5000 |
| a spider | 0.8625 | 0.7500 | 0.7375 | 0.5625 | **0.8143** | 0.7738 |

    median anatomy, extracted   0.814286
    median anatomy, E1 templates 0.813750
    gap                          +0.000536      against an LSD of 0.169

`axis-a-verdict.md:533-542` said closing the template-vs-extracted gap "would
need a sixth E1 arm carrying the extracted quadruped tree under E1's matched
fields, **and it was not run**." It has now been run, on three subjects, and
**the judge scores real extracted trees indistinguishably from idealised
hand-authored ones** -- a gap three hundred times smaller than the noise floor.

⚠ **THREE THINGS THAT KEEP THIS HONEST.**

1. **N = 3, and it is a median of three.** The bird sits at 0.4982; dog and
   spider bracket the bar. One more bad subject moves the median a long way.
2. **The confound is PARTLY matched, not fully.** E1 forces `stub_flaps = 0`
   and `served_fidelity = 1.0` (`probe_judge_battery._serve_block`). All three
   extracted subjects genuinely carried `stub_flaps = 0`, so that half matches
   by fact rather than by assertion -- but `a bird` served `fidelity 0.8333`
   against E1's forced `1.0`. This is much closer to matched than E2 ever was;
   it is not a matched-pairs experiment.
3. **A pass inside the noise floor is not a stronger claim than a fail inside
   it.** +0.000536 says the two populations are indistinguishable at this
   resolution, not that they are equal.

## Claim 3 — one subject in three has a second arm

| subject | R | flaps | pairs | stubs | runner-up |
|---|---|---|---|---|---|
| a dog | 6 | 6 | 2 | 0 | NONE |
| a bird | 6 | 5 | 1 | 0 | **yes** (5 leaves, `order` stage) |
| a spider | 9 | 8 | 4 | 0 | NONE |

The pairwise comparison -- the loop's ONLY licensed trigger, because Gate C
forbids an absolute threshold -- can therefore run on **one subject in three**.
Nothing was tuned to change this.

## Claim 4 — the trigger fired zero times, and the reason is position bias

The one available comparison came back **undecided**:

    winner            None          tie_reason  order_flip
    order_agreement   False         margin_mean_for_a  None (refused)
    compare_order_agreement_confounded  False   <- n=2 lifted the confound

    [reference=a, candidate=b]  prefers b   margin_for_a -0.1300
                                decisive topological_accuracy
                                sample_agreement 0.93
    [reference=b, candidate=a]  prefers a   margin_for_a +0.2700
                                decisive proportional_feasibility
                                sample_agreement 0.87

**The judge preferred whichever tree was shown SECOND, both times.** That is
recency/position bias, and at `compare_n = 2` it is not sampling noise: the two
draws WITHIN each ordering agreed at 0.93 and 0.87, while the two orderings
disagreed outright. Raising `n` from 1 to 2 -- 2 extra calls -- is what
licenses that sentence; at n=1 this reading would have been unavailable.

**The order-swap debiasing did exactly its job.** A single-ordering comparison
would have reported a confident preference for the runner-up. The instrument
refused instead: `winner: None`, `margin_mean_for_a: None`. It also chose a
DIFFERENT decisive criterion in each direction, which is a second, independent
tell that the ranking was not stable.

Both arms carry identical leaf, joint and pair counts -- they differ only in
where the unclassified mid-body flap attaches, and in proportions. So the one
comparison available was also the hardest kind. That is a mitigating fact about
this instance, not a defence of the instrument.

## What the loop is actually good for, measured

The scores did not move a gate. **The prose did the work**, which is what
`axis-a-verdict.md` already called the established half. Unprompted, and
without being told the reference count:

> *"a bird needs a pair of legs as well as a pair of wings, but this tree gives
> only one unpaired 'mid-body appendage' flap alongside the wing pair, head and
> tail -- effectively a bird missing a leg"*

The extraction served **5 flaps against an authored R of 6**. The judge found
not merely that one was missing but **which one**, from the tree alone. All four
samples agreed on it.

It also caught, on `a dog`, that the fore-limb path (0.69) is double the hind
(0.34) and that the fore-limb pair is azimuthally asymmetric (7.6 vs -37.3
degrees); and on `a spider`, that `hub-3 -> hub-6 -> hub-10` is a chain of
single-child pass-through joints padding the tree with no anatomical
counterpart. Each is checkable against the tree by hand.

## The standing verdict, unchanged

**Advisory. It ranks; it never gates.** Nothing here licenses a veto: Gate C
still fails, the trigger has still never fired, and the one time it could have,
it was refused for position bias. The loop's demonstrated value is the written
feedback, not the number.

