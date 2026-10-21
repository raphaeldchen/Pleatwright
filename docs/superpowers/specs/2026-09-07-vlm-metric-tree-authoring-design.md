# VLM metric-tree authoring: an agent that reads a mesh the way a designer does

**Status:** design, and **S1-S3 are now MEASURED** (live run 2026-09-08,
`claude-sonnet-5`, 27 cells). Section 2a records what the measurement changed.
**Date:** 2026-09-07, revised 2026-09-08.
**Origin:** a hand-run of this process on nine photo-derived meshes
(2026-09-06/07), then a live agent run of it (2026-09-08). Every number below
is measured from those runs, not estimated.

---

## 1. The problem, stated as a measured trade

Two processes now exist for turning a mesh into a Metric Tree, and this project
has run both on the same nine meshes. They fail in opposite directions.

| | anatomy exact | mean abs. leaf error | packs (attempt-0) |
|---|---|---|---|
| `auto_mesh_to_metric_tree` (skeletoniser) | 1 / 9 | 1.78 | **8 / 9** |
| hand-authored, faithful variant | 4 / 9 | 1.00 | 1 / 9 |
| hand-authored, packable variant | 7 / 9 | 0.22 | 3 / 9 |
| **LLM agent, wired loop (2026-09-08)** | **8 / 9** | **0.11** | 3 / 9 |

Anatomy scored against `fixtures/anatomy_expectation.json`, the human-authored
cited oracle. Pack rate on the rebuilt engine.

**The skeletoniser produces packable trees that are the wrong animal. The
designer produces the right animal and it does not pack.** Neither number is a
bug; they are two different objectives, and no one has yet built a process that
holds both.

This spec proposes the second process as an agent, because it is the one whose
failure mode is *recoverable* — a correct tree that does not pack has known
levers (root rehoming, placement seeding, the composed normalizer), whereas a
tree missing the frog's legs has none.

### 1.1 The mechanism worth automating

The hand run did not analyse geometry. It **rendered each mesh under a labelled
24-unit grid and read coordinates off the picture.** That converts a 3-D
computational-geometry problem into a 2-D visual-measurement problem. The
skeletoniser finds 42 leaves on a frog because every toe is a graph branch; a
reader looking at the picture sees a frog, and toes never become flaps.

---

## 2. Prior art (CLAUDE.md §0)

Surveyed 2026-09-07. What was adapted, and what was consciously rejected.

| source | establishes | disposition |
|---|---|---|
| **Grid-augmented vision**, arXiv:2411.18270 | overlaying a grid measurably improves spatial understanding in multi-modal agents | **ADAPTED, then MEASURED INERT on this task** (§2a). The ruler is kept — the readings come off it — but its *design* changed nothing. |
| **Progressive Visual Scaffolds**, arXiv:2608.21170 | scaffolds worth up to **+34.0 pp**; **line grids beat colour blocks**; 1 px works, ~5 px optimal; **gains are NOT consistent across models** (Qwen2.5-VL-7B *regresses*) | **MEASURED, AND THE ANSWER IS NO DIFFERENCE HERE** (§2a). Requiring a per-model check rather than assuming the gain is exactly what caught this. The paper's own finding that gains are model-inconsistent is why the check existed; this is one more inconsistent case. |
| **Set-of-Mark**, arXiv:2310.11441 | marking segmented regions unlocks fine-grained grounding in GPT-4V | **PARTIALLY ADAPTED.** We mark *axes*, not regions. Full SoM (SAM/SEEM segmentation) **rejected**: our renders are already one object on plain ground, so segmentation buys nothing and adds a heavy dependency to a CI-pinned venv. |
| **Scenethesis**, arXiv:2505.02836 | LLM drafts a coarse plan; a **vision module refines it with visual guidance** | **ADAPTED** — this is precisely the author-then-look-at-your-own-output loop in §5. Independent confirmation the shape is right. |
| **SceneCraft**, arXiv:2403.01248 | LLM agent writes scene code and improves from **rendered feedback** | **ADAPTED** — justifies `render_tree_sheet` as a first-class tool, not a nicety. |
| **RTLFixer**, arXiv:2311.16543 (DAC '24) | compiler-error feedback + ReAct fixes **98.5%** of compile errors; **+32.3% / +10.1%** pass@1. **But: extending to logic errors yields limited improvement** | **ADAPTED** for the compile-repair rung. The limitation is load-bearing: it is why anatomy (§7) is scored **separately** and never gated on packing. A compile loop fixes syntax, not wrongness. |
| **MagicArticulate**, arXiv:2502.12135 | learned automatic skeleton generation for articulation | **REJECTED as mechanism** — a learned skeletoniser is the thing we already have and are trying not to be. **ADOPTED as a future baseline arm.** |
| **Handle-based Mesh Deformation Guided by VLM**, arXiv:2506.04562 | *standard* VLMs already give satisfactory results; fine-tuning mainly reduces hallucination | supports starting zero-shot. Fine-tuning **out of scope**. |
| **L3GO**, arXiv:2402.09052 | chain-of-3D-thoughts agent building objects part by part | noted; the part-by-part decomposition matches our body-spine-then-limbs order. |
| **COrigami**, arXiv:2606.26299 (already in project memory) | rubric-driven VLM grading; N=4 beats N=16 | supplies the **stick-figure convention** this spec targets, and the warning that more samples is not more signal. |

**What the survey changed.** Two things. Grid *design* is now specified rather
than incidental (lines, not fills). And the scaffold's benefit is treated as a
hypothesis to be measured per model, because a published result says it
regresses on at least one.

---

## 2a. What the live run changed (2026-09-08)

27 cells: 3 grid designs x 9 meshes, `claude-sonnet-5`, one prompt, N=1, the
render the only variable.

| arm | grid design | MAE | exact | contract clean | packs | self-check revised |
|---|---|---|---|---|---|---|
| A | original: behind the mesh, 1 px uniform | **0.11** | **8/9** | 9/9 | 3/9 | 4/9 |
| B | as this spec worded it: behind, 1 px + 4 px weighted | **0.11** | **8/9** | 9/9 | 1/9 | 4/9 |
| C | true overlay: grid ON TOP at alpha 150 | **0.11** | **8/9** | 9/9 | 3/9 | 5/9 |

**The grid design is inert.** Identical to three significant figures, the same
single miss in every arm (spider, 10 vs 9), the same 8 exact. On n = 9 at N = 1
the pack-rate spread (3/1/3) is not distinguishable from noise and is not
claimed as a finding.

This is a **null result on the thing the prior-art pass was most confident
about**, and it is recorded rather than buried. The papers are not wrong; the
scaffold is not the binding constraint on THIS task, where the subject is a
single object on a plain ground and the readings are coarse (whole and half
grid units). A per-model, per-task check was required before believing the
+34 pp, and the check is what produced this row.

**A prior claim in this spec is also refuted.** Section 4.2 wrote the grid
"drawn BEHIND the mesh", which contradicts the overlay papers it cites. Arm C
was built to test that. The overlay is *not worse* -- and it is not better
either. The wording is now simply arbitrary, so it is no longer specified.

### What DID do the work: the loop

Against a one-shot run of the same prompt on the same renders (2026-09-07):

| | one-shot | wired loop |
|---|---|---|
| cells producing a tree | 6 / 27 | **27 / 27** |
| contract errors | 12 (horse 2, lizard 10) | **0** |
| spider / octopus authored | neither | both |
| trees revised after seeing themselves drawn | n/a | **13 / 27** |

Three changes account for it, and all three are now requirements:

1. **`direction` in the tool schema.** Without it a tree cannot be drawn as a
   stick figure at all, so the self-check has nothing to show and the output
   cannot be compared to the hand-authored set. Its absence was a harness
   defect, not a model failure.
2. **`validate_tree` as a mandatory rung**, plus the two prompt rules that
   pre-empt what it catches (section 6, rules 6 and 7). In the live run the
   rung never had to fire: every cell passed first time. Stating the constraint
   is cheaper than repairing the violation.
3. ~~**The visual self-check.**~~ **REFUTED by S6 -- see §2b.** 13 of 27 trees
   were revised after being shown their own figure, and this was written up
   here as "the highest-value rung measured". That was wrong. The comparison
   behind it was one-shot-vs-loop, which bundled three changes at once -- the
   token ceiling, the prompt rules, and the self-check -- and credited the
   whole delta to the rung that was easiest to see. Isolated, it does nothing.

**Corrected attribution of the one-shot -> loop delta:**

| change | effect | evidence |
|---|---|---|
| `LLM_MAX_TOKENS` 4096 -> 32000 | **6/27 -> 27/27 cells produced a tree** | mechanical: the 21 lost cells returned `finish_reason: "length"` |
| prompt rules 6 and 7 made explicit | **12 -> 0 contract errors** | the `validate_tree` rung **never fired** in any cell, so the repair path cannot be the cause; only the prompt changed |
| `direction` in the schema | enables the stick-figure rendering | required for the deliverable; no measured effect on anatomy |
| the self-check | **none measurable** | §2b |

The dominant effect was a **token ceiling**, not an agent-design idea.

---

## 2b. S6: the self-check ablation (2026-09-08)

The spec's own S6 said "re-run one arm with `render_tree_sheet` disabled". That
compares 2 turns against 1 and would credit the IMAGE for whatever a second
turn buys on its own. Three conditions were run instead, identical in every
other respect (grid arm C, same prompt, same schema, same validate rung, N=1):

| condition | turns | second look sees | MAE | exact | clean | packs | revised |
|---|---|---|---|---|---|---|---|
| `none` | 1 | — | **0.11** | **8/9** | 9/9 | 4/9 | 0/9 |
| `text` | 2 | nothing (prose review request) | **0.11** | **8/9** | 9/9 | 2/9 | 5/9 |
| `visual` | 2 | its own tree drawn in 4 views | **0.11** | **8/9** | 9/9 | 3/9 | 6/9 |

**`none` -> `text`: no change. `text` -> `visual`: no change.** Neither a second
turn nor seeing the figure moves anatomy at all.

The model *does* act when asked -- it revised 5/9 and 6/9 respectively -- and
the revisions are **neutral**. Activity without improvement is precisely what
S3's kill criterion was written to detect ("an unmeasured feedback loop is
decoration"), and it fires. **S3 is killed on its own gate.**

### ⚠ But the metric is SATURATED, so read this null carefully

Across all **six** experimental arms run to date (grid A/B/C and ablation
none/text/visual), the non-exact cells are:

```
A/spider  B/spider  C/spider  none/spider  text/spider  visual/spider
```

**The spider, and only ever the spider.** With 8 of 9 subjects exact in every
arm, exactly one cell can move. No intervention can demonstrate improvement on
a metric with one degree of freedom left, and the honest reading is **"this
corpus cannot distinguish these conditions"**, not "the self-check is
worthless". The correct conclusion is that S3 is unproven and unpromoted, not
that it is refuted for all corpora.

**What to do instead of another A/B on this corpus:**

1. **Score reading accuracy against computed landmarks.** The renderer's
   world->grid map is invertible, so a landmark's true grid coordinate is
   computable (`u = 24*(x - cx + span/2)/span`). Measured on the dog: agent
   error 1.03 units, hand-run error 1.00, both under-reading the ground line by
   the same 1.0. That metric is continuous and has real headroom, where leaf
   count has one cell.
2. **Get a harder corpus.** Nine subjects of which eight are trivially exact is
   not an evaluation set. The spider is hard because 8 legs + abdomen = 9
   exceeds `MAX_LEAVES = 8`; subjects with genuinely ambiguous anatomy would
   give the metric something to do.

---

## 2c. The 17-subject run (2026-09-08) — and the decision it settled

S8 added eight subjects chosen so the NAIVE answer is wrong on each
(`docs/superpowers/decisions/2026-09-08-s8-corpus-proposal.md`), taking the
corpus from 9 to 17 and the extractor's own score from MAE 1.78 / 1-of-9 to
**2.00 / 2-of-17** — i.e. the new corpus is harder, which is what gave the
metric room to move.

51 cells, three ablation arms x 17 subjects, grid arm C, N = 1.

| arm | MAE | exact | contract | packs | read fidelity | revised | tokens |
|---|---|---|---|---|---|---|---|
| **none** | **0.29** | **13/17** | 17/17 | 4/17 | 0.244 | 0/17 | 302k |
| text | 0.29 | 13/17 | 17/17 | 2/17 | 0.225 | 12/17 | 533k |
| visual | 0.53 | 12/17 | 17/17 | 3/17 | 0.325 | 9/17 | 536k |
| `auto_mesh_to_metric_tree` | **2.00** | **2/17** | — | — | — | — | — |

**The agent beats the shipped extractor by 7x on MAE and 6.5x on exact
matches**, on the corpus built to be hard. That is the result this spec exists
to establish, and it now rests on 17 subjects rather than 9.

**The corpus validated itself through its failures.** The scorpion came back
**11 against 9** because the model counted the pedipalps — exactly the
convention-adherence failure that row was written to catch, and something no
subject in the original nine could have exposed. It has now read 11, 11, 11, 12
and 11 across five measurements: that failure is stable and real.

⚠ **An earlier revision of this paragraph called the bird "still 4 against 6:
fused wings, the one failure that has survived every configuration tried." That
claim was FALSE and was built from one cell.** The bird reads **6** in `none`,
**6** in `text`, **6** in the reproducibility replicate and **6** in the uniform
re-run — four of five measurements exact. Only the `visual` arm read 4, and that
arm has since been removed from the loop (§5). Fused wings are a real failure
mode; they are not this corpus's standing one.

**Packing did not improve: 4/17 at best.** §1's trade is intact and untouched
by any of this.

⚠ **THE TABLE ABOVE IS THE PRE-FIX CORPUS. Do not quote it as the pipeline's
output.** It was authored before commit 9209d07 put the two-frames warning into
the system prompt, and only `dog` and `rabbit` were re-run against the fix — so
these 51 cells are two prompt configurations wearing one label. The current
result is §2e.

### 2e. The uniform corpus, and a defect no metric here can see

On 2026-09-09, reading the 17 sheets to build a review page found a **third
inverted tree**, the dolphin. Its readings were correct (dorsal base v=7, tip
v=1, matching the mesh) and every vertical component of its emitted directions
was sign-flipped. It scored **exact on leaf count, clean on the contract, and
0.28 on reading fidelity** — because the readings genuinely were right. The bug
lives entirely in the transcription step between reading and emitting, and
**nothing in this repository watches that step.** Two attempts to automate a
detector both failed validation (`evidence/.../ORIENTATION-NEGATIVE.md`); a
third was not attempted.

All fifteen remaining subjects were re-authored on the corrected prompt
(`run_framefix15.py`). Scored under one identical, corrected metric:

| | pre-fix (mixed) | uniform |
|---|---|---|
| MAE | 0.29 | 0.29 |
| leaf count exact | 13/17 | 13/17 |
| leaf label exact | 13/17 | 13/17 |
| label coverage | 0.993 | **1.000** |
| tree contract | 17/17 | 17/17 |
| packs at attempt 0 | 4/17 | **3/17** |
| reading fidelity | 0.238 | 0.215 |
| **inverted trees** | **1** | **0** |

**The re-run bought orientation and uniformity, and nothing else.** Anatomy did
not move. Packing lost a cell, which at a measured MAE noise floor of 0.059 is
not a result in either direction. Per-subject stability is weaker than the
aggregate implies: the ant dropped its antennae and became exact, the crab
gained a `rostrum` and stopped being.

**Two scoring defects surfaced, both of which had made CORRECT trees look
wrong** — the direction these metrics keep failing in:

* `parse_readings` required bare `(u,v)` pairs, so the bat's `(24, z=9.5)` and
  the dolphin's `(x=8.5,y=0.5)` scored as **no readings at all**, which is
  indistinguishable from total protocol non-compliance.
* `leaf_label_accuracy` knew neither `pect_left` nor `stinger`. Closing that
  exposed the opposite hole: an unmatched label drops out of the comparison
  entirely, so the scorpion's two unrecognised `pincer_*` leaves let it score
  **EXACT at 11 against an expected 9**. `exact` now requires every leaf to be
  recognised, so a lexicon gap reads as a failure to score rather than a pass.

**This is the strongest evidence yet for the human gate (§5).** The defect was
found by a person looking at a picture, after six numeric metrics passed it.

### What it settled

The self-review turn is **removed** (§5). See that section for the numbers and
for the careful version of the claim.

### What it did not settle

Significance. Every paired comparison still crosses zero at n = 17. The corpus
is harder but n is still small and N = 1 leaves per-cell variance unmeasured.
Anything decided from these arms is decided on *direction plus cost*, never on
a significant difference.


---

## 2d. Reproducibility — the noise floor, measured at last

Two independent sweeps of the **finalized loop** (`none` mode, 17 subjects,
identical configuration, N = 1 each, 2026-09-08).

| | MAE | exact | contract | packs | read fidelity |
|---|---|---|---|---|---|
| run 1 | 0.29 | 13/17 | 17/17 | 4/17 | 0.244 |
| run 2 | 0.35 | 13/17 | 17/17 | 4/17 | 0.187 |

**Leaf count identical on 14 of 17 subjects (82%).** `exact`, `contract` and
`packs` are unchanged **as counts** — ⚠ and `packs` is unchanged *only* as a
count. The two runs' packing SETS share one subject out of four and differ on
six; see §2f, which was measured later and which voids every per-subject
packing statement in this document. The three that moved — **ant 9→8, crab 10→11,
scorpion 11→12** — are exactly the three arthropods whose true counts exceed
`MAX_LEAVES`, i.e. the hardest subjects in the corpus. Everything stable is
stable; the instability is concentrated where the anatomy is.

### ⚠ The number that reinterprets every earlier null

**Run-to-run MAE spread: 0.059.** That is what N = 1 costs, and it is the
yardstick every "not significant" verdict in §2a–§2c should have been measured
against. Re-reading them against it:

| comparison | gap | vs noise floor | honest verdict |
|---|---|---|---|
| `none` vs `text` | 0.000 | 0.0x | genuinely nil — a second turn does nothing |
| `none` vs `visual` | 0.235 | **4.0x** | **larger than noise; probably real** |
| grid A vs B vs C | 0.000 | 0.0x | genuinely nil |

So the visual self-check's apparent harm is **four times the run-to-run
spread**, even though its bootstrap CI crossed zero at n = 17. A CI over 17
paired subjects and a replicate of the whole sweep answer different questions,
and having only the first is why §2b could not tell "does not work" from
"cannot be measured". Dropping that rung (§5) is better supported than the
significance test alone suggested.

### What this is for

**The provider bake-off cannot be read without it.** DeepSeek scoring 0.35
against Sonnet's 0.29 would be *within a single run's noise* and would mean
nothing. Any cross-provider claim needs either a gap well above 0.059 or
replicates on both arms. Establishing that cost $2.64 and it is the cheapest
thing in this entire investigation.


---

## 2f. The pack-rate noise floor — and why every per-subject packing claim here is void

Measured 2026-09-09, from data already paid for: three sweeps of the `none`
loop over the same 17 meshes. Runs 1 and 2 are the reproducibility replicate
(§2d) and share **one identical configuration**; the uniform run differs only
in the corrected frame prompt.

| | packs | which subjects |
|---|---|---|
| run 1 | 4/17 | bird, elephant, frog, guinea pig |
| run 2 | 4/17 | dolphin, guinea pig, horse, starfish |
| uniform | 3/17 | bird, lizard, octopus |

**The aggregate is stable and the identity is not.** Across runs 1 and 2 — same
prompt, same corpus, same model — the packing sets share **one subject** and
differ on **six**. Runs 2 and uniform share **none**.

**Control: the packer is not the variable.** `compile_tree` returns identical
verdicts on three consecutive calls for `bird` and `elephant` (`ok`) and for
`dog` and `spider` (`err`). The churn is therefore entirely in the **tree**:
two authorings of the same mesh, both anatomically exact, differ enough in
their micro-structure to flip packability.

Three consequences, and the third is the useful one:

1. **Every per-subject packing claim in this document is void**, including its
   own earlier ones. "The elephant packs" is a statement about one roll of the
   dice, not about the elephant.
2. **Only the aggregate rate is quotable**, and its observed spread is 3–4 of
   17 over three runs — so an intervention has to clear roughly ±1/17 of pure
   noise before it means anything. This is the packing analogue of §S7's
   saturation trap: there, one cell could move and nothing could be shown; here
   almost every cell moves on its own and nothing can be attributed.
3. **But it says the packing candidates already exist.** If anatomy-preserving
   micro-variation flips packability, then for many subjects a packable variant
   lies inside the neighbourhood of the tree we already have. That makes S4 a
   **search** problem over a space this repository already owns — node order,
   node root, lossless collapse — rather than a repair problem.

Evidence: `scripts/pack_set_churn.py`, `scripts/compile_determinism_control.py`,
`data/packsets.json`.

### Prior art for S4's repair policy (CLAUDE.md §0)

| source | establishes | disposition |
|---|---|---|
| **"Is Self-Repair a Silver Bullet?"**, ICLR'24 (arXiv:2306.09896) | at a fixed budget, **many diverse initial variants with shallow repair beat deep repair ladders** | **ADOPTED**, and it is already this repo's Slice-3 ladder policy — S4 inherits it rather than re-deriving it. Our own sharpest datum agrees: `dog/packable` failed **49 sequential rungs** and then packed at attempt 0 as a *flattened variant* — a different instance, not a deeper repair. §2f is the same finding from the other side. |
| **RTLFixer**, arXiv:2311.16543 (DAC'24) | compiler-error feedback fixes **98.5%** of compile errors, but extending it to logic errors "yields limited improvement" | **ADOPTED with the limitation binding.** A pack failure is not a syntax error. Feed `suggested_lever` verbatim and expect it to fix malformedness; do **not** expect it to fix "this anatomy does not fit on a square." |
| **Internal: node ORDER (S6, PR #94) and node ROOT (PRs #107–#118)** | the only two levers ever measured to move this packer, both by handing it a **different problem instance** rather than different geometry | **ADOPTED as S4's variant space.** CLAUDE.md §1.2 closes with "before proposing any third lever, read the structural ruling in item 1." **S4 proposes no third lever.** |
| **Internal: `flatten_tree`** | lossless degree-2 collapse, max &#124;Δ&#124; = 0.000e+00 across 18 trees and 382 leaf-pairs | **ADOPTED as a rung.** Losslessness is the entire point: it changes the instance without touching the anatomy. |
| **Length equalization** | measured to move hand-authored packing from **4/18 to 11/18** — the only intervention that works | **REJECTED, permanently.** It works by destroying the measured proportions. That is §1's trade and CLAUDE.md's standing rule; it is also the reason this pipeline exists. |
| **MCTS over feasibility-checked edit moves**, IJCAI'23 (arXiv:2211.13219) | search over a foldable-by-construction action space | **DEFERRED, not rejected.** The repo already lists it as the contingency "if Slice 3+4 plateau." §2f says we have not yet spent the cheap enumerative budget, so it is premature. Revisit only if the enumeration in S4 saturates below its gate. |

---

## 2g. S4 gate 1 — the variant space is LIVE, and the search is essentially complete

Run 2026-09-09, `scripts/s4_gate1_space_live.py`. **No API calls; 25 seconds of
in-process compiles.** Pure RANDOM sampling of at most K = 32 anatomy-preserving
variants per subject — no ranking, no lever, no guidance — so a positive result
is attributable to the space and not to any cleverness.

| | packs |
|---|---|
| baseline, attempt 0 | **3/17** |
| random variant search, K ≤ 32 | **12/17** |

**Gate 1 passes**, and by a margin far outside §2f's ±1/17 noise. Two further
readings matter more than the headline:

**The search is complete, not merely lucky.** For all five failures the entire
space was exhausted and no packable variant exists: `dog`, `rabbit`, `starfish`,
`crab`, `spider`. **Zero subjects were budget-limited** — K = 32 finds every
packable variant that exists in this space. Those five are a structural fact
about those trees, not a statement about our patience.

**The budget is nonetheless load-bearing for the winners:**

| K | packs |
|---|---|
| 4 | 2/17 |
| 8 | 7/17 |
| 16 | 8/17 |
| 24 | 9/17 |
| 32 | **12/17** |

Median attempts to first pack is 8, but the tail runs to 31 (`elephant`). A
budget chosen from the median would lose a third of the wins.

**⚠ This is not "the same work, better results."** The baseline gets one
compile and the search gets up to 32. It is a fair trade only because a compile
here is ~0.07 s in-process — the same operation costs 1.10 s when spawned,
because each spawn re-imports `server` (project memory,
`pipeline-performance-review-spawn-import`). Any production wiring of this must
stay in-process or the trade reverses.

### Which generator actually wins

| family | wins |
|---|---|
| `flatten` + reorder | 6 |
| reorder alone | 4 |
| `flatten` alone | 2 |
| **re-root** | **0** |

**Re-rooting won nothing, and it is the majority of the space** — every non-root
node is a candidate, so for the larger subjects roots are most of what random
sampling draws. Zero wins from the majority class is a strong signal, and an
uncomfortable one: node ROOT is the lever CLAUDE.md §1.2 calls "the second and
last", measured to move `quadruped` coverage 0.7161 → 0.8797. ⚠ **That finding
is not contradicted here** — it was measured on *coverage and scale for trees
that already pack*, whereas this measures *whether a failing tree can be made
to pack at all.* Different question, different answer; do not let either result
be quoted as the other.

### The invariant was checked, and the checker was checked

A variant is admissible only if it preserves the same leaf SET and the same
leaf-to-leaf distance for **every** leaf pair — strictly stronger than S4's
wording, and the level that actually means "the same animal". The run aborts on
a violation rather than reporting a number nobody can trust.

Because a checker that passes everything would produce exactly this headline,
`selftest_invariant` runs as a **precondition on every subject**: it nudges one
leaf's length by 10 %, deletes a leaf, and re-checks the identity, asserting
reject / reject / accept. The sweep cannot report a number without it passing
17 times first.

⚠ `rescue_ladder.contract_slivers` is **excluded from this space.** It never
deletes a leaf and never alters a surviving edge's length — so it satisfies
S4's literal wording — but it DISCARDS the contracted node's own length, which
shortens leaf-to-leaf paths. That is an anatomy change wearing a
length-preservation costume, and it is precisely what the distance check exists
to catch.

⚠ **The checker's first run raised a false alarm against `flatten_tree`**
("leaf set changed: 5 vs 6"). `flatten_tree` was correct; the probe read its
`index_map` backwards — the map is OLD → NEW with string keys. Recorded because
the failure direction was right (refuse to proceed) and the accusation was
wrong, which is the pattern a checker must be read with.

---

## 2h. S4 gate 2 — guidance beats chance, out of sample

Run 2026-09-09, `scripts/s4_gate2_guidance.py`. The rule was **pre-registered
from §2g's win table and from nothing else**, written into the probe's docstring
before the test set was touched, and not tuned afterwards:

> Try variant families in this order, keeping enumeration order within a family:
> **1.** flatten + reorder · **2.** reorder alone · **3.** flatten alone ·
> **4.** re-root.

**The test set is held out.** Testing the rule on the uniform corpus that
suggested it would be circular, so gate 2 runs on the run-1 and run-2
authorings — **34 trees**, different authorings of the same 17 subjects, never
used to pick the rule. Same space, same budget, same trees in both arms; only
the ORDER of attempts differs.

| K | random | guided |
|---|---|---|
| 4 | 10/34 | **16/34** |
| 8 | 13/34 | **22/34** |
| 12 | 15/34 | 22/34 |
| 16 | 17/34 | 22/34 |
| 24 | 20/34 | 22/34 |
| 32 | 21/34 | **22/34** |

Baseline at attempt 0 is **8/34**. **Gate 2 passes**: guided beats random at
every budget, and its win set is a strict **superset** — nothing random found
that guidance missed, and it additionally solves `run2/scorpion`. Head to head
on the 21 both solve: guided is faster on 17, tied on 0, slower on 4. Median
attempts to first pack, random **5** (max 25); guided **3** (max 8).

**⚠ Read the shape, not just the win. Guidance buys SPEED, not coverage.** Both
arms converge to 21–22 of 34; guidance reaches its ceiling at **K = 8** where
random needs **K = 32**. The honest claim is a ~4x reduction in compile budget
for the same set of trees, plus one extra subject — not "guidance packs more
trees."

**The pre-registered ordering held out of sample.** Every one of the 22 guided
wins came from the rule's top two families — flatten+reorder **17**, reorder
**5** — and **none** from flatten-alone or re-root, even though the arm tries
both once the first two are exhausted. §2g's zero for re-rooting reproduces on
data that did not produce it.

### Where that leaves S4

Both gates are passed. **What remains is wiring, not measurement**, and §2g's
cost warning is the binding constraint on it: a compile is ~0.07 s in-process
and ~1.10 s when spawned, so a K = 8 guided search is half a second in-process
and nine seconds through the spawn path. Wiring this into the serve path
without keeping it in-process would spend the entire result.

---

## 2i. Fused limbs — a defect four metrics scored clean

Found 2026-09-09 by the owner, reading the published tree sheets: the horse's
and the elephant's legs "only separate into right and left at the foot".

Confirmed. The horse authors `front_shoulder → front_knee → front_fetlock →
{front_hoof_L, front_hoof_R}` — the two front legs share twelve units and
diverge for three. The hind pair is worse: **2 units of 22**.

**Every metric here scored those trees clean.** Leaf count 6/6 exact; leaf
labels exact; tree contract no errors; reading fidelity correct, because the
coordinates genuinely were read off the mesh. The defect is in the TOPOLOGY —
*where* the pair branches — and nothing was looking there.

It is not cosmetic. TreeMaker measures a flap from its branch point, so the
fused form compiles to one long flap with two stubs on it, and the base cannot
read as the animal.

### The measurement, and what part of it is validated

`mcp_harness/pair_fusion.py` scores each bilateral pair by how much of its limb
is its own rather than shared, built **only from leaf-to-leaf distances** —
which makes it invariant under exactly the transformations S4's variant search
performs (node order, re-root, lossless collapse). The same number before and
after a rescue is the point, not a coincidence.

Ranked worst-first over the 17:

| | | |
|---|---|---|
| **horse 0.065** | **elephant 0.143** | **guinea pig 0.269** |
| dolphin 0.333 | bat 0.353 | cat 0.409 |
| … | dog 0.618 | spider 0.750 |

**The three the owner flagged by eye are the three lowest, with a gap beneath
the rest.** That ordering is what ships.

⚠ **THE THRESHOLD DOES NOT.** A first draft shipped `FUSED_BELOW = 0.5`,
justified as the statable rule "more of the limb is shared than separate". On
this corpus that rule scores **TP 3, FP 6** — it flags the cat, bat, bird,
dolphin, lizard and scorpion, all of which branch correctly at the body. The
rule sounds principled and is not: `shared` is measured to the nearest other
leaf, so its scale depends on the rest of the animal's proportions and does not
transfer between body plans. Fitting 0.30 instead would tune to **three**
labelled positives — the mistake `ORIENTATION-NEGATIVE.md` was written to
prevent. The module therefore sorts and reports and **returns no verdict**.

### What it costs S4

§2g/§2h's invariant preserves the anatomy the tree *had*. For horse, elephant
and guinea pig that anatomy was already wrong, and both are packing winners in
§2g. So "12/17 pack with the anatomy intact" is exact as stated and narrower
than it sounds: **intact means unchanged by the search, not correct.** The
authoring fix is §6 rule 6; the search is innocent and unaltered.

---

## 2j. The wiring, measured on the shipped path — and the stage order it corrected

`scripts/s4_serve_path_ab.py`. Both arms are the real
`draft_and_compile_full_base`, the real ladder, the real barrier and the real
annotation; the control is the documented rollback var `IDE_LADDER_STAGES`
naming the six pre-existing stages. 42 minutes per arm.

| | served |
|---|---|
| before (six stages) | **11/17** |
| after (flatten added) | **12/17** |

Regressions: **none**. Serves with an unreadable stage: **none** — the marker
reaches `served_stage` end to end. Stage census of the 12: `order` 7,
attempt-0 exact 3, `placement` 1, `flatten` 1. **No jitter, no normalize, no
stub — every one of the twelve serves comes through a rung that trades no
measured proportion.**

### ⚠ The first wiring was wrong, and only the A/B said so

Flatten was placed FIRST, imported directly from §2h's finding that trying it
first reaches the packing ceiling in a quarter of the attempts. Measured, that
arm also served 12/17 with no outright regressions — and **downgraded five
subjects**. `guinea_pig`, `frog`, `dolphin`, `scorpion` and `ant` moved from a
rank-20 `order`/`placement` serve, where every id keeps its own requested
length, to a rank-15 `flatten` serve, where an edge may be a sum. Only the
horse actually gained. The pack count rose and five serves got less faithful.

**§2h was ranking a SEARCH; the ladder serves a USER.** In a search every
variant is equally admissible and the only cost is compile budget, so
fastest-first is right. On the ladder the stages are explicitly *not* equally
admissible — that is what `STAGE_HONESTY` exists to say — so the order is
by ADMISSIBILITY. Flatten now sits between `placement` and `normalize`, which
is exactly where its rank puts it, and the same rule already puts `stub` last
despite its top rank. Re-measured: all five downgrades undone, the horse's gain
kept.

`test_the_ladder_visits_stages_in_admissibility_order` now pins the rule
itself, so the next stage cannot be placed by intuition either.

### ⚠ And a baseline correction

§2g's headline is "3/17 → 12/17". That baseline is **attempt-0 only**. The
SHIPPED ladder was never at 3/17 — it was at **11/17**, because five other
rescue stages were already doing this work. **Flatten's marginal contribution
on the serve path is ONE subject.**

That also reframes §1's founding trade. "Anatomically faithful trees don't
pack" is true at attempt 0 and much weaker at the serve: 11 of 17 already
served, all through proportion-preserving rungs, before any of this slice's
work. The trade is real and it is smaller than this spec has been stating it.

---

## 2k. The finished pipeline, end to end: 17/17 served

`scripts/serve_rule6_capture.py` runs the rule-6 corpus through the real
`draft_and_compile_full_base` and captures `server._LAST_SERVE`, which carries
the `requested` and `served` node lists side by side. Neither is re-derived --
re-deriving would mean re-implementing the ladder's barrier, and a probe that
re-implements production is how this project has measured the wrong object
before.

**17/17 compiled to a base.** What the ladder actually did:

| edit | subjects |
|---|---|
| no rescue -- packed as authored | 3 (frog, bird, starfish) |
| node list reordered | 6 |
| re-rooted | 4 |
| initial x/y seeds | 1 (scorpion) |
| **joints merged (flatten)** | **2 (spider, ant)** |
| **engine ADDED flaps (stub)** | **1 (crab)** |

**Only two of seventeen look any different.** Everything else changes what the
packer is HANDED -- list order, which node is the root, where a flap starts
before optimisation -- and not what the animal is. That is the design, and it
is why a before/after picture is a weak instrument here.

⚠ **The crab's base carries flaps nobody asked for.** No rescue that preserved
its anatomy could pack it, so the stub stage ran. Its node list is
byte-identical to the request, so the picture is identical too; the invented
flaps exist only in the compiled base. **No before/after image can show this** --
the served fold's disclosure is the only thing that does, which is exactly why
`INVENTS_ANATOMY` is a separate axis from `STAGE_HONESTY`.

**Anatomy check, verified not assumed:** every served tree's leaf-to-leaf
distances were compared against the request. All 17 match exactly.

### ⚠ A false alarm, and the lens that caused it

The first run of that check reported that the RABBIT's anatomy had changed on a
serve reporting attempt-0 exact -- the silent-wrong-serve signature the ladder's
own comments warn about. It had not. The rabbit was **re-rooted at its tail**,
and a CHILDREN-based leaf test ("a node with no children") then read five leaves
where the author wrote six, because the new root has no children.

**A leaf is a degree-1 vertex of the FREE TREE.** The two definitions agree on
every ordinary tree and disagree on exactly one case -- a root with a single
child -- which the serve path produces. `pair_fusion.leaf_distance_matrix` now
uses free-tree degree; it CLAIMED root invariance (§2i) and, under the old lens,
did not have it. The test that was supposed to pin that passed only because
`rescue_ladder.rehome` declines leaf targets and so never exercised the case;
`root_rank`'s re-rooting does not decline them.

One published number moves: the **horse's limb split, 0.524 -> 0.636**, because
its authored root is degree-1 and was being dropped from its own leaf set. It
moves in the flattering direction, which is the more important reason to state
it. No aggregate changes.

⚠ `tree_flatten.leaf_distances` still uses the children-based lens. That is
correct for its own job -- flatten never moves the root, so both sides of its
losslessness comparison drop the same node -- and it is NOT correct for
comparing across a re-root. The two modules deliberately do not share it.

---

## 3. Scope

**In:** four new tools, the agent-loop image wiring, the authoring protocol, a
human gate at the tree, and an eval harness with baselines that already exist.

**Out:** fine-tuning; anything downstream of the Metric Tree (crease patterns,
folding, shaping); non-mesh input.

⚠ **An earlier revision of this list also said "replacing
`auto_mesh_to_metric_tree`" was out of scope. That contradicted §8's
owner-settled purpose** — "this pipeline is intended to replace the existing
mesh→tree pipeline" — and the contradiction sat in the document for two days.
Replacement is the **destination, not this spec's deliverable**: the slices here
build and measure the authoring path, and none of them switches the serve path
over. Reaching that switch needs work this spec does not cover — parity on the
subjects the extractor already serves, a migration for callers of
`auto_mesh_to_metric_tree`, and the packing story in S4. Say "not yet", never
"not the goal".

**The seam is narrower than the grep suggests.** `auto_mesh_to_metric_tree` is
named in ~70 places, but all but two are `probe_*.py` (as-run probes, not
production) or tests. **Production calls it exactly twice:**

| call site | what it is |
|---|---|
| `server.reference_tree_from_query` (`server.py:4152`) | the MCP tool an agent calls |
| `mesh_acquire.query_to_metric_tree` (`mesh_acquire.py:1330`) | the text -> mesh -> tree chain |

Both take a **prompt**, acquire a mesh, then extract. The VLM path substitutes
only the extract step. ⚠ **But it substitutes a pure function with one that
makes an LLM call**, and `reference_tree_from_query` is itself a tool an agent
invokes — so the replacement nests a model inside a tool call. That is a design
question this spec has not answered and must not answer by accident.

**Objective, per the acceptance decision:** anatomy is the bar; **pack rate is
measured and reported, never gated on.** This matches how the repo already
ranks `stub_flaps` above `design_scale` in `order_rank.rank_key`.

---

## 4. Tools

### 4.1 Already exist — use, do not rebuild

`describe_tree_format`, `validate_tree`, `get_template`,
`predict_tree_feasibility`, `draft_and_compile_full_base`.

`validate_tree` is already the RTLFixer-style symbolic pre-execution check, and
its docstring already says what it does and does not predict. `get_template`
already carries the node-order constraint in-band.

### 4.2 To build

```python
render_mesh_views(mesh_path: str, grid: int = 24,
                  views: tuple = ("side", "front", "top"),
                  zoom: str | None = None) -> dict
    # {"png": path, "extent_xyz": [...], "grid": 24,
    #  "note": "grid divides the LONGEST extent; all three views share it"}
```
The ruler. Line-based, ticks every 4 units, no colour fills.
**Weight and compositing order are deliberately UNSPECIFIED**: 1 px behind,
weighted behind, and weighted on top were measured identical (§2a), so
pinning one would be inventing a requirement. `zoom` re-renders one named
region larger for a second look — the hand run needed exactly that for the
frog's folded hind limb.

```python
render_tree_sheet(nodes: list, pairs: list) -> dict     # {"png": path}
```
⚠ **NOT a model-facing self-check. Build it for the HUMAN GATE only.** S6
(§2b) isolated the self-review turn and found no effect; the 17-subject run
(§2c) found it trending worse and costing 1.8x the tokens, and it was removed
from the loop on 2026-09-08 (§5). What this tool draws is the figure a person
approves before a tree becomes a base. Takes
`(name, parent, direction, length)` tuples, derives positions, draws
top/side/front/isometric. Positions **must** be derived, never passed in, so
the drawing cannot disagree with the tree. `tree_render.py` already exists with
sheet helpers and **zero production callers** — closer to wiring than writing.

> **The authoring tool's schema MUST carry `direction` per node.** Without it
> there is no pose, this tool has nothing to draw, and the self-check rung
> cannot exist at all. The 2026-09-07 run omitted it, so its trees could only
> be drawn as dendrograms — which read as the model producing worse trees when
> it was the harness producing worse pictures.

```python
anatomy_expectation(subject: str) -> dict
    # {expected_feature_count, derivation, citation, convention}
```
The oracle, keyed by the fixture's own normalisation rules. ⚠ **A SCORING
tool, not a model-facing one** — see §5 "The oracle is not an input". Returns `None` for
an unknown subject — *an oracle that always has an answer is the closed loop
wearing a different hat* (the fixture's own words).

```python
flatten_tree(nodes: list, pairs: list) -> dict
    # {"nodes": [...], "pairs": [...], "collapsed": int}
```
Lossless degree-2 collapse. Earned its place: it packs `dog/packable` at
attempt 0 **after the serve path failed the same tree across 49 rungs**.
Verified lossless — max |Δ| = 0.000e+00 across all 18 trees and 382 leaf-pairs.

### 4.3 The protocol constraint that decides the architecture

`llm_client.py` can already send images — four constructors, and a **live
verified call** (2026-08-15, `claude-sonnet-5`, HTTP 200, correct answer via
tool call). But `agent_loop.py` contains **zero** references to them, and no
MCP tool returns an image.

And on Anthropic's OpenAI-compat endpoint, `image_url` is supported **only for
`role == "user"`**. MCP tool results arrive as `role == "tool"`.

> **Therefore `render_mesh_views` cannot return its picture through its own
> return value.** It returns a *path*; the agent loop must detect that and emit
> the image as a **follow-up user message**. This is an agent-loop change, not
> a tool change, and it is the piece most likely to be missed by someone who
> reads "the image plumbing already exists".

**Cost.** The same compat layer has **no prompt caching**, so every image is
re-uploaded and re-billed on every turn it remains in history. Required policy:
**at most two mesh renders live in history at once**; older ones are replaced by
their already-extracted textual readings, which is lossless for our purpose
because the readings are the artifact.

---

## 5. The loop

**ADOPTED 2026-09-08: the model's self-review turn is REMOVED.** The loop is
one authoring turn plus validation. `render_tree_sheet` still exists and is
still built — but it draws the figure a HUMAN approves at the gate, and is no
longer shown back to the model.

```
  render_mesh_views(mesh) ──► [user-message image]
            │
            ▼
  READ: model quotes coordinates verbatim          ← gate: no reading, no length
            │
  ✗ anatomy_expectation is NOT called here — see "The oracle is not an
    input" below. The COUNTING CONVENTION rides in the system prompt;
    the expected COUNT never reaches the model.
            │
            ▼
  AUTHOR: (name, parent, direction, length) tuples
            │
  validate_tree ──► errors: fix and re-validate, never compile
            │
            ▼
  render_tree_sheet ──► a figure for the HUMAN, not for the model
            │
  ══════ HUMAN GATE: approve the stick figure ══════
            │
            ▼
  predict_tree_feasibility → draft_and_compile_full_base
            │
            └─ fail → feed `code` + `suggested_lever` back VERBATIM,
                      plus flatten_tree as a rung. Max 3 repair rounds.
                      NEVER rescale measured proportions. (§6)
```

### The oracle is not an input

⚠ **CORRECTED 2026-09-08.** An earlier revision of this diagram had
`anatomy_expectation(subject)` feeding the model "expected leaf count +
convention". That is a **closed loop**: §7 scores leaf count against
`anatomy_expectation.json`, so a model told the answer scores perfectly while
measuring nothing — the same trap as scoring fidelity against a self-derived R,
which this project has already been burned by twice.

The split is:

* the **counting convention** (one leaf per terminal appendage; ears, digits
  and antennae excluded) is a RULE and rides in the system prompt, §6.3;
* the **expected count for this subject** is the ANSWER and never reaches the
  model.

Every measurement in §2a–§2c was collected this way — `loop_lib.py` and
`run17.py` contain no reference to the oracle, and the model identifies each
subject from the picture. The numbers are sound; the diagram was not.

`anatomy_expectation` therefore stays a **scoring** tool. If a future
production build wants to hand the model prior knowledge for a known subject,
that is a legitimate but DIFFERENT configuration, and it must be run with the
oracle off to be evaluated at all.

### Why the second turn is gone

Measured over 17 subjects (§2c), holding everything else fixed:

| arm | MAE | exact | read fidelity | tokens | Sonnet 5 cost |
|---|---|---|---|---|---|
| **`none` — one turn** | **0.29** | **13/17** | **0.244** | **302k** | **$2.64** |
| `text` — review, no image | 0.29 | 13/17 | 0.225 | 533k | $4.28 |
| `visual` — review with the figure | 0.53 | 12/17 | 0.325 | 536k | $4.10 |

The cheapest arm is the best arm. A second turn buys nothing on anatomy, the
visual variant trends worse on both metrics, and either costs **~1.8x** the
tokens. Removing it is a 3x saving that also removes the pipeline's one measured
regression.

⚠ **It is removed as UNPAID-FOR, not as refuted.** No paired comparison reaches
significance even at n = 17 (§2c), so the honest claim is "this has never once
shown a benefit across two corpora and three metrics, and it costs 80% more" —
not "showing a model its own work cannot help". If a future corpus or a weaker
model changes that, the rung is one message to re-add.

The human gate stays. It sits at the tree because that is where an error is
cheapest to catch and most expensive to miss, and CLAUDE.md §5 already puts a
human-in-the-loop checkpoint at exactly this step ("The Reality Check").

---

## 6. The prompt contract

Five rules. The first did most of the work in the hand run.

1. **Read before you derive.** Quote coordinates before emitting any length —
   *"shoulder (7.5, 9.5), ground (7, 21.5), so foreleg = 12"* — and persist that
   string in the tree's `how_measured` field. A fabricated length has no reading
   behind it, which makes fabrication **visible in the artifact** rather than
   detectable only by re-measuring.
2. **Proportion, not pose.** Ship the horse as the worked example: photographed
   mid-trot, four legs at four phases, authored equal.
3. **Declare the convention.** Ears are leaves under COrigami and not under this
   repo. An undeclared convention is chosen silently and inconsistently.
4. **Never rescale measured proportions to force a pack.** Already CLAUDE.md's
   rule, and the one an eager agent breaks first: equalising lengths moves the
   hand-authored set 4/18 → 11/18 and looks like a triumph. Uniform scale is the
   sole permitted length change, because it alters no proportion — and it is
   **measured inert** (4/18 → 3/18), so it is permitted, not recommended.
5. **Segmentation is a prior, not a measurement.** The grid gives endpoints and
   totals; splitting a limb into `4 + 6 + 2` is anatomical knowledge. Require the
   split to be **labelled as inferred**, so the two sources stay separable.
6. **Each side is its own chain, all the way to the body.** Added 2026-09-09,
   after the owner read a tree sheet and saw that the horse's and the
   elephant's legs "only separate into right and left at the foot". Measured:
   the horse's hind pair is **2 units of 22** apart and the elephant's front
   pair 4 of 27 — one leg with a forked hoof, in three subjects of seventeen.
   The compiler measures each flap from where it branches, so the fused form
   compiles to one long flap carrying two stubs. **Every one of those trees
   scored 6/6 exact on leaf count, exact on leaf labels, clean on the contract
   and correct on reading fidelity** — the defect is in the topology and
   nothing was looking there.

---

### ⚠ Two defect classes, both found by a person looking at a picture

Orientation (§2e) and limb fusion (§2i) were each invisible to every numeric
metric this project owns, and each was caught by the owner reading a rendered
sheet. Neither was found by a test, a score, or a review of the JSON.

That is now a pattern rather than an anecdote, and it has a design consequence:
**§5's human gate is not a formality and `render_tree_sheet` is not a
convenience.** They are the only mechanism that has ever caught either class.
Any plan that proposes to run this pipeline unattended has to say what replaces
them.

---

## 7. Evaluation

**Corpus:** the nine photo-derived meshes in `~/Downloads/photo_meshes/`.
Generated by `tencent/Hunyuan3D-2` at a pinned seed, so reproducible.

**Primary — anatomy.** Per subject, |leaf_count − expected_feature_count|
against `anatomy_expectation.json`. ⚠ **Valid only when the run is BLIND to
the oracle** (§5). A run that was told the expected count cannot be scored on
this metric at all. Report **mean absolute error** and
**exact-match count**. Baselines, both already measured:

| arm | MAE | exact | status |
|---|---|---|---|
| skeletoniser | 1.78 | 1 / 9 | baseline |
| hand-authored, faithful | 1.00 | 4 / 9 | baseline |
| hand-authored, packable | 0.22 | 7 / 9 | baseline |
| **LLM agent, wired loop** | **0.11** | **8 / 9** | **measured 2026-09-08** |

**Gate was: beat MAE 1.78 / exact 1-of-9. PASSED**, and the aspiration
(0.22 / 7-of-9, the hand run) was passed too. The remaining miss is the spider
in all three arms (10 vs 9).

⚠ **Two cautions on that number.** It is N = 1 per cell, so per-subject
variance is unmeasured; COrigami's own finding that N = 4 beats N = 16 argues
for a small N, not for N = 1. And the agent's win over the hand run comes
partly from NOT applying `MAX_LEAVES` (§1) — it is a better anatomist and an
equally bad packer, which the primary metric is designed to reward and the
secondary metric is designed to expose.

**Secondary — packing, reported not gated.** attempt-0 and serve-path rates
against the hand-authored 3/9 and 6/9 (packable variants).

**Tertiary — reading fidelity.** For a held-out subset, compare the agent's
quoted coordinates against the hand run's recorded readings. This is the only
metric that tests the *premise* rather than the outcome, and it is the S1 gate.

**Anti-metric.** Do **not** score fidelity using any reference count the
pipeline derives from its own output. That closed loop is documented in the
fixture's own `_meta`, and it is why the skeletoniser reports `fidelity 1.0` on
a horse that lost its tail.

---

## 8. Slices, each with a kill criterion

**S1 — the ruler. DONE, and its grid-design question is CLOSED.**
`render_mesh_views` + agent-loop image wiring, built and run. The kill
criterion (readings within ±2 grid units) passed: on the dog's checkable
landmarks the agent's error was 1.03 units against the hand run's 1.00, and
both under-read the ground line by the same 1.0 — a bias in the render, not in
either reader. **The grid-design sub-question is answered and needs no further
slice: all three designs scored identically (section 2a).**

**S2 — authoring. DONE.** `anatomy_expectation` + the §6 protocol +
`validate_tree`. Gate was "beat MAE 1.78"; measured **0.11, exact 8/9**, and
0 contract errors across 27 cells.

**S3 — the self-check. DONE, and KILLED on its own gate.** Gate was "reduce
MAE relative to S2". S6 isolated it against both a no-second-turn and a
second-turn-without-image control: **0.11 / 8-of-9 in all three**, no movement
whatever (§2b). The model revises when asked (5/9 and 6/9) and the revisions
are neutral — activity without improvement, which is exactly what this gate
exists to catch. Build the tool for the human-review deliverable; do not claim
it buys accuracy. ⚠ Qualified by saturation: the metric had one movable cell,
so this is "unproven", not "worthless".

**S4 — packing. GATES PASSED AND WIRED 2026-09-09 (§2g, §2h, §2j).**
The flatten stage ships in the serve path at its admissibility position;
11/17 → 12/17 served, no regressions, all twelve through proportion-preserving
rungs. ⚠ Read §2j's baseline correction before quoting §2g's 3/17.
Baseline 3/17 at attempt 0 → **12/17** by random variant search (§2g), and on a
held-out 34-tree set 8/34 → **22/34** by the pre-registered guided search, at a
quarter of random's budget (§2h). The five subjects that still fail had their
entire space exhausted: no packable variant exists for `dog`, `rabbit`,
`starfish`, `crab`, `spider`. The remaining work is putting the search on the
serve path **in-process**, per §2h's cost note. Amended 2026-09-09 to carry a
kill criterion; §2f is its premise.

⚠ **An earlier revision of this entry said "Report only; no kill criterion, by
§3." That was a misreading of §3 and it made S4 unfalsifiable.** §3 forbids
gating **the pipeline's acceptance** on pack rate — anatomy is the bar. It says
nothing about whether S4's own machinery earns its place. A slice that cannot
fail cannot tell anyone when to stop, and this project's named recurring
failure mode is loosening a gate to reach a headline.

**Shape, per the prior art in §2f: a breadth search, not a repair ladder.**
Enumerate anatomy-preserving variants of the authored tree — `order_variants`,
`normalize_variants`, `rehome` (root), `flatten_tree` — compile each, and keep
the first that packs. `suggested_lever` is fed back verbatim for *malformed*
trees only, per RTLFixer's own limitation.

**The invariant, non-negotiable:** no variant may change any node's `length` or
add or remove a leaf. Every lever above changes the instance handed to the
packer, never the anatomy. A run that violates this has not passed S4, it has
changed the subject.

**Kill criterion, two gates, both on the uniform 17:**

* **The space must be live.** A random-variant search at budget *K* must beat
  the unaided **3–4/17** baseline by more than its ±1/17 spread. If enumerating
  the whole anatomy-preserving neighbourhood cannot pack materially more than
  chance already does, the variant space is inert and **S4 dies here** — the
  answer would be that these trees are unpackable as authored, which is a real
  and publishable result.
* **Guidance must beat chance.** Ranked or lever-guided variant choice must beat
  the random-variant control **at equal budget K**. If it does not, the search
  ships and the guidance does not. This is the same control discipline
  `reading_fidelity` already enforces by always reporting `random` and `jitter`
  alongside the model.

**Cost: no API calls.** S4 operates on trees already authored and paid for; it
spends compile time only. That is a reason to run it before the provider
bake-off, not after.

**S5 — the gate and the harness.** HITL approval, consolidated eval, one
reproducible command.

**S6 — the self-check ablation. DONE (§2b).** Run with the control the
original wording omitted: a `text` arm giving a second turn *without* the
image, so `none→text` measures the turn and `text→visual` measures the picture.
Both null. Its real yield was not the ablation but the **saturation finding** —
six arms, one movable cell — which invalidates further A/B on this corpus.

**S7 — a metric with headroom. HALF DONE (`mcp_harness/reading_fidelity.py`,
11 tests).** The metric exists and is validated; the corpus is still the
blocker.

*Purpose settled 2026-09-08 by the owner:* this pipeline is intended to
**replace the existing mesh→tree pipeline, with anatomy ranked above
packability** — "a tree that packs but looks nothing like the intended design
is useless; a tree that is anatomically correct but doesn't pack can be
altered." That is §1's argument, and it makes pack rate a later problem rather
than a gate.

**Validity: yes.** Model readings score 0.369 grid units from the mesh
silhouette against uniform-random 1.127 — **3.0×** — and the verbosity confound
is ruled out (`corr(n_readings, mean) = +0.124`).

**Power: still no.** All six paired comparisons — grid A/B/C and ablation
none/text/visual — have bootstrap 95% CIs crossing zero at n = 9. The variance
is outlier-dominated, so the corpus remains the binding constraint; it has
simply moved from *saturation* to *variance*.

**What it does buy, today:** per-cell diagnosis that leaf count is blind to. The
starfish scores 5/5 exact on anatomy in **every** arm while one arm's readings
sat 3.4 grid units off the object — a right answer reached without reading
anything. A radially symmetric subject makes that easy, and only this metric
sees it.

**S8 — a corpus that can discriminate.** NOW the sole blocker on every design
question. Nine subjects of which eight are trivially exact is not an evaluation
set, and n = 9 cannot resolve the effect sizes involved. Needs subjects with
genuinely contested anatomy, and enough of them. `anatomy_expectation.json`
holds 14 rows, of which we use 9; extending it is **human work by contract**
("nothing here is computed, measured, or read off any extraction") — every new
row needs a derivation and a citation.

### Operational requirements found the hard way

These cost real money and real runs; they are requirements, not trivia.

* **`LLM_MAX_TOKENS` must be raised.** The default 4096 truncates the tool call
  mid-emission: 24 of 27 cells returned `finish_reason: "length"` and no tree.
  Rule 1 ("quote every reading") roughly triples output length, so the rule that
  makes fabrication visible is also what blows the ceiling. 32000 was ample.
  A **uniform failure across all arms looks like a null result** — the tell was
  that the only survivor was the SMALLEST tree, not the clearest picture.
* **Persist after every cell.** A run that dumps only at the end loses
  everything it has paid for when it stops early. One run lost 14 completed
  cells this way.
* **Guard module entry points.** A bare `asyncio.run(main())` with no
  `if __name__ == "__main__"` meant importing the runner for one helper
  silently re-ran the entire 27-cell sweep.
* **`tools: []` is a 400 on this endpoint** ("List should have at least 1 item").
  `run_turn` guards `tool_choice` for the tool-less case but not `tools`, and
  its own docstring says a tool-less caller is legitimate.
* **`APIConnectionError` is transient; a credit-exhaustion 400 is not.** Both
  arrive as exceptions and only the message distinguishes them. Retry the first,
  stop on the second, and **read the message rather than the type** — project
  memory already records this exact trap costing a working Space.

---

## 9. Risks

**~~The premise may be carried by context, not by the grid.~~ ADDRESSED
2026-09-08.** The agent had none of the hand run's context — no COrigami
samples, no extractor output, no repo conventions beyond the prompt, and it was
never told which animal it was looking at (it identified each from the picture).
It still scored 0.11 / 8-of-9. On the checkable landmarks its reading error
(1.03 units on the dog's nose) matched the hand run's (1.00). The premise holds
without the context.

**The grid is not where the value is.** Measured inert across three designs
(§2a). The value is in the loop — validation, and above all the visual
self-check. A future version should spend its effort there, not on the ruler.

**Anatomical priors cut both ways.** They put wings on a wingless mesh —
correctly. They will also put a tail on a Manx cat. The prior is doing real
work and it is not always right; §6.5 keeps it labelled so it stays auditable.

**Cost.** No prompt caching on the compat endpoint. Budget per subject before
S1, not after.

**The trade in §1 may be irreducible.** It is entirely possible that
anatomically faithful trees simply do not pack, and that the honest output of
this work is a *measured statement of that*, not a pipeline. That would be a
result, and the eval is built so it can be reported as one rather than hidden
behind a tuned metric.
