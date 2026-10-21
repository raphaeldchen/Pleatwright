# Decision: anatomy ground truth is human-authored, and `anatomy_reference.json` is not it

**Date:** 2026-08-20 · **Unit:** C1 (extraction-fidelity wave) · **Decision:** D1
**Status:** ACCEPTED and **LIVE**. ✅ **Z1 flipped the flag ON, 2026-08-29** —
the default now lives in `anatomy_expectation.DEFAULT_EXTERNAL_R` (code, not
`.env`), with `IDE_EXTERNAL_R=0` as the kill switch. **Read §8 before citing
anything below as current**: §§1–7 describe the flag in its default-OFF state
and their mechanism claims are confirmed by §8's live measurement, but every
sentence of the form "behind `IDE_EXTERNAL_R=1`" or "flag ON" now describes the
DEFAULT path, not an opt-in.

---

## 1. The problem: the fidelity yardstick is the generator's own output

`mesh_to_tree.reference_feature_count` computes **R**, the anatomy-fidelity
yardstick, as *the leaf count holding the widest plateau across the prune
sweep* — read off the skeleton **that same run has already mutilated**.

That is a closed loop, and it is not a subtle one. Throwing away half the
animal **raises** the score:

| step | octopus, voxel 96 |
|---|---|
| voxel weld (`fill()` cannot bridge disjoint bodies) | leaves **14 disjoint bodies** |
| largest-component keep | discards 13 of them |
| widest prune plateau over what survived | **4 leaves** |
| `reference_feature_count` | **R = 4** |
| `fidelity_score(4, 4)` | **1.0000** |
| terminal early-exit `fid >= 1.0 and stage == "none"` | fires **inside the first voxel** — voxel 64 is never built |

A headless, four-limb tree reads as **perfect anatomy**, and every
deterministic instrument in the pipeline agreed (`status ok`, `dropped []`,
`invented 0`, `drift 0.0`, `ACCEPT True`, `lint BENIGN`).

The same untrustworthy R is then cited as the reason a better candidate may
never be promoted. `_phase4_admitted_serve`'s own docstring says it out loud:

> *"this is not caution, it is the absence of a trustworthy yardstick."*

Re-measured first-hand this session: octopus **R = 4 / 9 / 30** at voxel
96 / 64 / 128; lizard **R = 5** at all three; water bear **R = 14 / 9 / 11**.
R is not a property of the animal at all. It is a property of how badly this
run's weld failed.

## 2. Prior art (CLAUDE.md §0)

**Surveyed:** RTLFixer (LLM repair loop for RTL), CADSmith (agentic CAD
repair), and the ICLR self-repair studies — all three already in this
project's memory from the 2026-07-25 landscape survey — plus GPTeval3D
(arXiv:2401.04092) and COrigami (arXiv:2606.26299) for the
evaluator-independence framing.

**Adapted:** the one requirement they converge on — **a repair loop's oracle
must be independent of its generator.** A self-derived oracle produces
monotone-improving, meaningless scores, because every step that simplifies the
problem also simplifies the thing being scored. Adapted as
`anatomy_expectation.reference_count_for` → `mesh_to_tree.auto_mesh_to_metric_tree(reference_count=)`.

**Consciously rejected:**

- **Validating this wave against `fixtures/anatomy_reference.json`.** It looks
  like ground truth and is not — see §3. Using it would re-close the very loop
  the wave exists to open.
- **A learned or VLM-derived count as the primary oracle.** A VLM over mesh
  renders (unit A1) is a genuinely independent signal and is worth having, but
  it is not *authored*: it varies run to run and cannot be audited by reading a
  file. It belongs alongside this table, not instead of it.
- **Fuzzy / substring / stemmed prompt matching.** An oracle that always has an
  answer is the closed loop wearing a different hat. Unlisted → `None`.

## 3. `fixtures/anatomy_reference.json` is extraction-derived, not ground truth

Its own `_meta` always admitted this, in the sentence immediately after the one
that called it ground truth:

> reference_count = R, the leaf count of the widest leaf-count-vs-prune
> plateau, pinned by `tests/test_fidelity_rank.py` against recorded extraction
> curves.

So it **is** `reference_feature_count`'s own past output, pinned. And
`benchmark_subjects.py:220` scores the scorecard's `served_fidelity` against
it.

**Decision:** the file is **FROZEN** and **relabelled**. Its `_meta` now
carries `"status": "extraction-derived, NOT ground truth"`, the reason, and a
pointer to its successor. **Zero data rows changed** — every
`reference_count` / `expected_pairs` value is byte-for-byte what Slice 1 and S7
committed, and `tests/test_anatomy_reference.py` still pins each against the
recorded curve. The file remains useful as an accurate historical record of
*what the extractor voted*; it is simply not evidence about animals.

## 4. ★ The bird contradiction, settled

`anatomy_reference.json` pins **`bird: reference_count 4`**. The VLM judge,
looking at renders, wrote:

> "Four appendages where a bird needs six."
> — `fixtures/vlm_judge/replay.json`

A biologist would side with the judge. A bird has **2 wings + 2 legs + head +
tail = 6**.

**Ruling: both numbers are correct, about different things, and they were only
ever in contradiction because the file called itself ground truth.**

- **4** is a true statement about `bird.glb` at voxel 96: the widest plateau
  the extractor's prune sweep held was 4 leaves. It is a measurement of the
  *extraction*.
- **6** is a true statement about *birds*. It is the number that belongs in an
  anatomy oracle.

Consequences, all three of which are now enacted:

1. **The 4 stays, unchanged**, because it accurately records the extraction and
   `test_fidelity_rank.py` pins it against the recorded curve. Editing it to 6
   would have been a *silent falsification of a measurement* to make it agree
   with an unrelated claim — the exact failure mode the frozen-baseline rule
   exists to prevent.
2. **The 6 is authored into `fixtures/anatomy_expectation.json`** under the
   prompt key `bird`, with its derivation and citation.
3. **The disagreement is asserted, not merely described.**
   `test_the_expectation_table_is_not_a_copy_of_the_extraction_derived_one`
   fails if the two files ever agree on bird — which is the guard that stops
   the new table quietly becoming a copy of the old one.

The 4-vs-6 gap is also, usefully, the size of the defect: the bird row is a
standing, committed example of extraction losing a third of an animal while
every instrument read green.

## 5. What was built

| | |
|---|---|
| `mcp_harness/fixtures/anatomy_expectation.json` | prompt-keyed, human-authored, **one cited derivation per row**, computed from nothing |
| `mcp_harness/anatomy_expectation.py` | normalisation, lookup, the `IDE_EXTERNAL_R` gate, and `honest_fidelity` |
| `mesh_to_tree.auto_mesh_to_metric_tree(..., reference_count=None)` | **keyword-only**; `None` is byte-identically today |
| `server.reference_tree_from_query` | threads the prompt it already had and used to drop |
| `row["r_provenance"] = "external"` | stamped in its own pass **after** the annotation loop, so F4's literal cannot clobber it |

**Wired at exactly ONE of the three prompt→tree seams.** `probe_base_eval.build_blob`
was wired and the hunk was **dropped**: it is the only merge conflict in the
seven-branch wave (F2 restructured that call site into several branches, giving
a same-line modify/delete against `res = auto_mesh_to_metric_tree(mesh_path)`).
F2 adds `reference_count=` at its own call site.
`mesh_acquire.query_to_metric_tree` is F3's file and stays unwired. Both gaps
are pinned by `test_the_other_two_prompt_to_tree_seams_are_recorded_as_unwired`.

**Counting convention** (stated so the numbers are auditable): one Metric Tree
leaf per distinct **terminal appendage** — each arm/leg/wing/tentacle/ray, the
head as one, the tail as one when the animal has an external tail. Sub-flap
detail (digits, antennae, ears, fins that are not skeletal limbs) is not
counted. This is the convention the committed subjects already follow
(humanoid 2+2+head = 5; quadruped 4+head+tail = 6) — restated here from
anatomy, not inherited from an extraction run.

## 6. ★ The clamp, and what this decision deliberately does NOT do

`fidelity_score` clamps `r_eff = min(max(R, MIN_LEAVES), MAX_LEAVES)` with
`MIN/MAX_LEAVES = 4, 8`. Measured: **`fidelity_score(8, R) == 1.0` for
R ∈ {8, 9, 11, 14, 20, 29}**.

**So a truthful tardigrade R = 9 still leaves the served 8-leaf *bear* tree
scoring a perfect 1.000 and ranked first.** An external R that reported only
through the clamped score would change nothing and would ship this repo's
**fifth** vacuous metric (COORDINATION.md §4.1 lists the first four).

Two rulings follow:

1. **The external R reports through `unclamped_fidelity`**, which has no clamp.
   `anatomy_expectation.honest_fidelity` delegates to it — it does not
   re-implement it, because two copies of a metric drift. Sibling unit F4
   surfaces the same function in the trace and the report.
   Required-fail input, asserted in
   `test_required_fail_external_r_nine_against_an_eight_leaf_serve`: external
   R = 9, served 8 leaves ⇒ **0.888… < 1.0**, with the clamped 1.000 asserted
   alongside it so the trap cannot be silently "fixed".
2. **`MAX_LEAVES` is NOT raised and the clamp is NOT changed** (decision D3).
   The user explicitly declined to pre-authorise it. Loosening a gate to reach
   a headline is this project's named recurring failure mode, and the
   servable-band ceiling is to be **measured** on its own evidence first.

**Therefore: this decision fixes the OCTOPUS class and does NOT by itself fix
the water bear.** The octopus is fixed because a truthful R = 8 scores its
4-leaf tree 0.5, the terminal early-exit does not fire, and the voxel sweep is
no longer truncated. The water bear is *not* fixed: its served tree is a
literal bear from the provider (problem A, units A1/A2), and even with a
truthful R = 9 the clamp still scores the 8-leaf serve 1.000 in **ranking**.

⚠ **And be precise about what "reports honestly" means as shipped.**
`honest_fidelity` is supplied and asserted, but `MeshTreeResult.fidelity` is
still the clamped score and **no served report prints the unclamped number
yet** — the trace and report wiring is unit F4's hunk
(`mesh_to_tree.py:1528-1535`, `mesh_report.py`), which C1 is forbidden to
touch. So C1 changes **what the search aims at** and supplies the honest read;
F4 and Z1 are what make a user see 0.888 instead of 1.000.

Also unchanged, deliberately, because they are other units' hunks:
`_phase4_admitted_serve`'s refusal to displace a held serve (`:1287–1392`,
unowned this wave), the R pre-pass and the second terminal exit (unit C2), and
every geometry lever (units B0/B1/B2).

## 6b. ★ NO INSTRUMENT IN THIS REPO CAN DETECT A C1 FLAG-ON REGRESSION

State this before anyone reads a green run as reassurance.
`benchmark_subjects.measure` calls `auto_mesh_to_metric_tree(mesh_path)` with
**no** `reference_count`, and the five scorecard subjects are fixture meshes
with **no prompt**. The frozen scorecard is therefore **structurally inert** to
this unit — flag ON or OFF, by construction rather than by luck.

So a `--baseline` run with `IDE_EXTERNAL_R=1` that shows *no axis moved* is
**not** evidence the flag is safe; it is evidence the scorecard cannot look.
("Green has two causes" — the tell this wave has hit four times.) The live-mesh
octopus arms in §1 are the only measurement that does look at the flag-ON path,
and they cover one subject.

Pinned by `test_the_scorecard_path_cannot_see_this_unit_at_all`, which fails
the day the scorecard is wired — exactly when this caveat stops being true.

## 6c. Two cross-unit findings that bound what C1 achieves

1. **C2 structurally overrides the external R.** `_voxel_reference_count` takes
   no `reference_count` parameter and returns `reference_feature_count(...)` —
   the closed-loop vote — and `_terminal_anchor_r` takes `max()` over voxels.
   On the octopus at voxel 96 an authored 9 is discarded for a self-derived 30.
   It is *arithmetically* inert on the three live subjects only because
   `fidelity_score` clamps `r_eff` at 8 — the very trap §6 names — and it is
   **live on 10 of the 14 authored rows** (every entry at 5 or 6). **No test
   anywhere sets both flags.** C2 owns the fix and the cross-flag coverage;
   recorded here so the interaction is not rediscovered.
2. **C1 turns off C2's required-fail guard.** `_pre_pass_protected` gates on
   `held["fidelity"] >= 1.0`, which is the expression C1 rewrites: C2's octopus
   demonstration reads `fidelity_score(4, 4) = 1.0` today and
   `fidelity_score(4, 9) = 0.5` with C1's flag on. C2 owns that fix.

## 7. Handed to sibling units (found in review, not fixable inside C1's hunks)

1. **⇒ F4 (`mesh_report.py`) — RESOLVED, by C1 setting the field itself.**
   F4 (PR #145) builds the socket: `_PROVENANCE_CAVEAT` has an `"external"`
   arm, and F4's own comment assigns the value to us — *"C1 (external table)
   and C2 (max-over-voxels) each set their own value at the site where they
   actually change R."* Neither did, initially; F4 hardcodes `"self-derived"`,
   so C1 + F4 with the flag ON would have printed an **authored** R under the
   caveat *"R IS NOT GROUND TRUTH — IT WAS VOTED OVER THIS RUN'S OWN
   EXTRACTION"* — exactly inverted, and machine-readable rather than merely
   wrong in prose. C1 now stamps `row["r_provenance"] = "external"`.
   `mesh_report.py` is untouched. **Verified by executing the merged file**,
   not by reading it: `git merge-tree` C1×F4 auto-merges clean, F4's literal
   lands inside the annotation loop and C1's override after it, and all 22 C1
   tests pass against the merged `mesh_to_tree.py`.
   Still open for F4: the prose line at `mesh_report.py:252`/`:264`/`:286`
   hardcodes *"reference feature count (widest prune-sweep plateau)"*, which
   `anatomy_oracle.reference_count` (`:65`) regex-parses.
2. **⇒ F4 (`mesh_report._full_anatomy_row`, `:191`).** Its docstring rests on
   *"R is by construction a leaf count that OCCURRED in the sweep"*, which an
   external R breaks. **This is not new** — the same thing already happens
   whenever `R > MAX_LEAVES` (fish R=10, insect R=9 today), so the branch is
   pre-existing rather than introduced here — but C1 makes it reachable on
   prompt-keyed runs, where the "MISSING FEATURES — repair plan" block can
   invite a flap fill even though a 9-leaf tree exists in `admitted`.
3. **⇒ F3 (`mesh_acquire.query_to_metric_tree`, `:343`).** There are **three**
   prompt→tree seams, not two. The third still runs the closed-loop R. Left
   unwired on purpose (F3 owns the file; its callers are probes, not the serve
   path) and pinned by
   `test_the_third_prompt_to_tree_seam_is_recorded_as_unwired` so it cannot
   change silently.
4. **⇒ F2 (`probe_base_eval`).** C1's hunk there was **dropped** — it is the
   only merge conflict in the seven-branch wave. F2 adds `reference_count=` at
   its own restructured call site. Note while doing so that `served_fidelity`
   is still scored against the frozen `anatomy_reference.json` even when
   extraction aims at the authored R; no shipped caller can hit the divergence
   today (a fixture subject has `prompt=None`; a free-text prompt gets a
   `promptN` label with no reference row, so the column nulls), but it is one
   caller away.

---

## 8. ★ Z1 CLOSING RECORD — the flag is ON, and it is on in CODE (2026-08-29)

**The status line at the top of this file is now discharged:** *"shipped behind
`IDE_EXTERNAL_R=1` (default OFF); the flag flips on in Z1"* → **the default is
ON**, in `anatomy_expectation.DEFAULT_EXTERNAL_R`. `IDE_EXTERNAL_R=0` is the
kill switch.

### 8.1 The measurement, on live `hf` meshes

Three subjects, both arms, on cached real provider meshes — not
`MESH_PROVIDER=fake`, which routes `octopus` / `lizard` / `water bear` all to
`quadruped.glb` by keyword and would have made the experiment meaningless.
Both octopus arms were run twice; **byte-identical both times** (only wall
clock differs).

| subject | arm | voxel | prune | leaves | pairs | `stub_flaps` | `rescue_stage` | R | provenance | fid (clamped) | fid (unclamped) | voxels built |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **octopus** | OFF | 96 | 0.40 | **4** | 1 | 0 | none | 4 | self-derived | **1.000000** | 1.000000 | **1** — `[96]` |
| **octopus** | **ON** | 64 | 0.55 | **6** | **3** | 0 | none | 9 | **external** | 0.750000 | **0.666667** | **3** — `[64, 96, 128]` |
| lizard | OFF | 96 | 0.20 | 5 | 1 | 0 | order | 5 | self-derived | **1.000000** | 1.000000 | 3 |
| lizard | **ON** | 96 | 0.20 | 5 | 1 | 0 | order | 6 | **external** | 0.833333 | 0.833333 | 3 |
| dog *(control)* | OFF | 96 | 0.30 | 6 | 2 | 0 | placement | 6 | self-derived | 1.000000 | 1.000000 | 3 |
| dog *(control)* | **ON** | 96 | 0.30 | 6 | 2 | 0 | placement | 6 | **external** | 1.000000 | 1.000000 | 3 |

Meshes: `hf:an octopus` (2 047 508 B), `hf:a lizard with a long tail`
(198 240 B), `hf:a dog` (874 640 B).

**§1's mechanism is CONFIRMED, not merely re-asserted.** The octopus OFF arm
reproduces the documented defect exactly — `VOXEL_GRID = [96, 64, 128]`, and
the run returns inside the first entry with 8 trace rows, because
`fidelity_score(4, 4) = 1.0000` and `stage == "none"` fire the terminal exit.
With the authored R = 9, `fidelity_score(4, 9) = 0.5`, the exit does not fire,
the search walks all three voxels (24 trace rows) and serves a **6-leaf,
3-pair** tree instead of a **4-leaf, 1-pair** one. `stub_flaps` stays 0 on both
arms, so the extra anatomy is found, not invented.

**The dog is a verified no-op, and that is a result.** External 6 == self-derived
6, and every field is identical across the two arms except `r_provenance`. Had
the dog moved, the wiring would be wrong rather than R.

**The lizard is the delicate case, and it moved the SCORE, not the SERVE.** Its
terminal exit never fired in either arm (`rescue_stage` is `order`, not
`none`), so the search already walked all three voxels; the flag's whole effect
there is that a tree carrying 5 of a lizard's 6 features stops reading
**1.0000** and starts reading **0.8333**.

⚠ **`water bear` was deliberately EXCLUDED, and the reason is worth keeping.**
Its mesh is a literal bear (`mesh_identity` 0.2125, blind-named *"pig"*) with
roughly 6 features, while the table authors a tardigrade's **9**. Measuring
that arm would have scored extraction against an animal it was never given —
a mesh-identity failure charged to the flag, and precisely the unattributable
row COORDINATION.md §1 forbids.

### 8.2 Cost, stated rather than buried

Octopus wall clock **4.7 s → 71.2 s** (re-run: 4.2 s → 68.2 s). That is not
overhead; it is the search doing the two voxels it was skipping. Lizard
(24.3 → 23.4 s) and dog (17.2 → 16.5 s) are unchanged, because neither was
exiting early. **The cost lands exactly on the subjects where the early exit
was wrong**, which is the right place for it and the reason it is acceptable.

### 8.3 ★ Why the default moved into CODE and not into `.env`

The brief proposed `IDE_EXTERNAL_R=1` in the repo-root `.env`. **Measured, that
is the worse of the two options**, for a reason specific to this repo:

`.env` is gitignored, and `env_config.load_env()` runs **at import** in
`server.py:44` — which **42 test files import** — via
`load_dotenv(override=False)`. Verified rather than assumed: importing `server`
in a clean interpreter takes `LLM_MODEL` from `None` to `'claude-sonnet-5'`. So
a `.env` line turns the flag **ON for the whole local test session and leaves
it OFF in CI**, where no `.env` exists. That is a local-vs-CI behavioural split
in the one instrument that could ever catch a regression here, and it is
invisible in the diff. On a repo whose memory records *"green has two causes"*
four separate times, shipping that would be self-inflicted.

Three practitioner sources agree with the code default, and one is decisive on
the principle:

- **The Twelve-Factor App, *Config*** (https://12factor.net/config) — *"Config
  varies substantially across deploys, code does not."* By that criterion a
  flag whose ON state is permanent and identical everywhere **is not config**.
- **Hodgson, *Feature Toggles*, martinfowler.com, 2017** — *"Managing toggle
  configuration via source control and re-deployments is preferable, if the
  nature of the feature flag allows it,"* and, on exactly our blind spot,
  *"It's most important to test the toggle configuration which you expect to
  become live in production."* It also names the carrying cost: release toggles
  *"should generally not stick around much longer than a week or two"* — this
  one was 9 days old.
- **GitLab developer docs, *Feature flags*** — the best documented industry
  instance of this exact step: enabling by default is its own reviewed change,
  tests are required *both* enabled and disabled, and flags are **enabled by
  default in tests** so the ON state is what the suite exercises.

The env var is **kept** as a kill switch, because §6b's blindness is real and
an unobservable change needs a documented way back. Parsing stays asymmetric on
purpose: unset/empty take the default; once a value is typed, only the exact
string `"1"` is ON, so `false` / `off` / `no` / `2` / a typo all read OFF. An
`!= "0"` inversion would have read `IDE_EXTERNAL_R=false` as ON — the trap the
original docstring named, and flipping the default does not license walking
into it from the other side.

### 8.4 Prior art for the flip itself (CLAUDE.md §0)

**Adapted.**

- **Beer, Ben-David, Eisner, Rodeh, *Efficient Detection of Vacuity in
  Temporal Model Checking*, FMSD 18(2):141–163, 2001** — supplies the rigorous
  name for §6b: **vacuity / antecedent failure**, a property that passes
  trivially because its precondition never occurs (*"every request is
  eventually followed by a grant"* in a system that never requests). The suite
  has been passing vacuously on this flag for nine days. Vacuity detection is a
  discipline, not an ad-hoc worry — which is why §6b is pinned by a test rather
  than footnoted.
- **Qi, Long, Achour, Rinard, *An Analysis of Patch Plausibility and
  Correctness for Generate-and-Validate Patch Generation Systems*, ISSTA
  2015** — the closest published precedent for the defect this decision exists
  to fix: under a weak oracle, most accepted GenProg/RSRepair/AE patches were
  *"equivalent to a single modification that simply deletes functionality."* A
  repair loop scoring highest by removing the thing it was meant to fix is our
  octopus, in another domain, eleven years earlier. **Cite it as precedent;
  this failure mode is not novel.**
- **Ring & Orseau, *Delusion, Survival, and Intelligent Agents*, AGI 2011** —
  the "delusion box": an agent able to modify its own percepts before they
  reach its reward channel will, because that is cheaper than solving the task.
  The sharpest one-line argument for oracle *independence* specifically, as
  opposed to oracle *quality*.
- **Deutsch, Dror, Roth, *On the Limitations of Reference-Free Evaluations of
  Generated Text*, EMNLP 2022** — reference-free metrics can be optimised at
  test time to near-best-possible scores and should be used *"as diagnostic
  tools… instead of measures of how well models perform a task."* Today's R is
  reference-free; the 14-row table is reference-based. Directly licenses the
  flip.
- **Manheim & Garrabrant, *Categorizing Variants of Goodhart's Law*, 2018** —
  ours is the **causal** variant (the optimiser can intervene on the metric's
  own input). Naming the variant is more precise than citing Goodhart
  generically. **Skalse et al., *Defining and Characterizing Reward Hacking*,
  NeurIPS 2022** gives the formal statement of "proxy and true reward rank two
  outcomes oppositely."
- **Hendrickx, Perini, Van der Plas, Meert, Davis, *Machine Learning with a
  Reject Option: A Survey*, Machine Learning, 2024** — confirms "abstain rather
  than guess" is a named pattern with a lineage back to Chow (1970), and
  classifies ours as **novelty rejection** (input outside the authored domain),
  not ambiguity rejection. **Adopted convention: report COVERAGE alongside
  quality** — the table is 14 rows, and how often it answers is part of the
  result, not a footnote.

**Consciously rejected.**

- **"Dark launching" as a description of the last nine days.** Fowler's dark
  launch means the new path *actually executes*, in parallel, with its output
  hidden — *"the recommendation does all the work it would do when it's
  released, but nobody can see that it's doing it."* A default-OFF flag never
  ran. So the nine days produced **zero evidence**, and calling it a dark
  launch would claim soak time this change never had. It is shipped-but-
  disabled code. ⚠ **The cheap thing Z1 did NOT do, recorded as owed:** compute
  both R's and log the delta on the keyed prompts without acting on the new
  one. That is the real dark launch, and it would have supplied the evidence
  the scorecard structurally cannot.
- **Canary release.** Presupposes a user population and traffic routing to
  partition. A single-operator research pipeline has no traffic to canary.
- **Learning to defer (Madras et al., NeurIPS 2018; Mozannar & Sontag, ICML
  2020) as a mechanism** — and the reason is a genuine warning about our own
  design, not a filing decision. L2D learns a rejector against a downstream
  expert *assumed better than the model*. Here the fallback on abstention is
  **the known-broken self-derived R**. Borrowing the framing would imply the
  abstain path is safe when it is precisely the unfixed path.
- **Chow-optimal reject thresholds as machinery.** They require a calibrated
  confidence score to threshold; a 14-row lookup table has none. Vocabulary and
  the coverage-reporting convention adopted, machinery not.

### 8.5 What Z1 does NOT do

1. **`MAX_LEAVES` is not raised and the clamp is not touched** (D3, unchanged).
   Re-measured live this session: `fidelity_score(8, 9) == 1.0000` against an
   unclamped `0.888889`. The octopus has **9** appendages against
   `MAX_LEAVES = 8` and **cannot be served correctly at all**; the honest
   ceiling across 72 cells is 7 of 8 arms. **The win here is that the search
   stops lying about when it is finished — not that the octopus is fixed.**
   That the served octopus reads 0.75 / 0.667 rather than 1.0 is only because
   it serves 6 leaves; an 8-leaf serve would still read a clamped 1.0000.
2. **`IDE_R_PREPASS` stays OFF** (recorded NO-GO: `bird` loses 27% of its scale
   and 0.18 of its coverage). Confirmed not enabled in any arm. §6c's
   interaction — `_terminal_anchor_r` takes a `max()` over self-derived voxel
   R's and can therefore **override** an authored one — is untouched and still
   C2's to fix. New tripwire: `test_z1_did_not_also_switch_on_the_r_prepass`,
   because two `IDE_*` flags that both mean "R" are exactly the pair a future
   reader flips together.
3. **The scorecard is still blind, and a green `--baseline` run still proves
   nothing about safety.** §6b is unchanged and its test still passes, which is
   the point: `benchmark_subjects.measure` passes a fixture mesh and no prompt,
   so all five subjects get `None` from `reference_count_for` in either flag
   state.
4. **The two unwired seams stay unwired** (§7 items 3 and 4), still pinned.

### 8.6 Required-fail inputs for Z1 (COORDINATION.md §4.1)

Z1 flips a default rather than adding a number, so its required-fail inputs are
the two ways a default-ON oracle goes wrong. Both are asserted **end-to-end
through `auto_mesh_to_metric_tree`**, not at the lookup, because the provenance
stamp lives in the extraction trace and a lookup-only assertion cannot see it.

| # | known-bad input | must score as | test |
|---|---|---|---|
| a | `"a three-legged dog"` — a real request no human has checked | `None`; fall back to self-derived R; stamp **not** `"external"` | `test_required_fail_an_unlisted_prompt_still_abstains_with_the_flag_on` |
| b | `IDE_EXTERNAL_R=0` | a **byte-identical** `MeshTreeResult` to never having shipped Z1 | `test_required_fail_the_kill_switch_restores_the_pre_z1_result` |

(b) asserts byte-identity rather than "R is 5 again" on purpose: a kill switch
that restored the reference count but left a provenance stamp or a different
served tree behind would pass the weaker check and still have changed the
serve. It also asserts the two arms **differ** on the chosen input, so the test
cannot pass because the flag does nothing there.

The positive arm is `test_a_listed_prompt_stamps_external_with_no_env_var_set`,
on an input where self-derived (5) and authored (6) genuinely disagree — the
stub mirror of the live lizard.

**Two pre-Z1 tests were rewritten rather than deleted**, so the policy change is
visible in the diff instead of quietly losing coverage:
`test_external_r_flag_parsing` (now pins the asymmetric parse and
`DEFAULT_EXTERNAL_R`) and
`test_the_seam_lookup_is_off_by_default_even_for_a_known_prompt` →
`test_the_seam_lookup_is_on_by_default_and_still_abstains`, whose kill-switch
arm keeps the old assertion verbatim in meaning.

### 8.7 Handed on

- **⇒ whoever owns the next R unit: the shadow-log Z1 skipped.** Compute both
  R's on every prompt-keyed serve and record the delta. It is the evidence §6b
  says does not exist, it costs one extra `reference_feature_count` call, and
  it needs no flag.
- **⇒ same owner: a metamorphic relation beats a lookup table on coverage.**
  *R must not increase when the intermediate skeleton is degraded* is testable
  on **all** prompts — including the ones the 14-row table abstains on, which
  is exactly where the fallback still leaves the closed loop in place. Prior
  art: Segura et al., *A Survey on Metamorphic Testing*, IEEE TSE 42(9), 2016;
  Barr et al., *The Oracle Problem in Software Testing: A Survey*, IEEE TSE
  41(5):507–525, 2015, for the partial-oracle taxonomy.
