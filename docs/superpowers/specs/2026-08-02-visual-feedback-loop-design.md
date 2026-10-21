# The visual feedback loop — giving the agent an instrument for "does this look right?"

**Date:** 2026-08-02
**Status:** design, awaiting review
**Author:** brainstorming session (Claude + raphaeldchen)
**Companion:** `2026-08-02-boundary-placement-conditions-design.md` (Slice 0).
Slice 0 is sequenced first and has **no dependency** on this document; this
document has no dependency on Slice 0 either. They touch disjoint files.

---

## 1. The question, and the honest answer to it

**Asked:** can the agent look at the crease pattern it designs — flat and
folded, from several angles — get a signal on how good it is, and iterate?

**Answered, after measuring:** yes, but not where the intuition points. The
picture is informative *upstream* (the anatomy, before compilation) and the
*arithmetic* is informative downstream (the compiled artifact). Rendering the
compiled crease pattern for a model to look at is measurably worse than the
deterministic auditor we already run on it.

This spec builds the two halves that measurement supports, and pre-registers
the entry condition for the third.

### 1.1 How the dog was called "correct"

For the record, since this is where the question started. The 2026-07-25
claim rested entirely on counted quantities: 6 of 6 leaves served, 2 of 2
bilateral pairs kept, 0 stub flaps, no jitter marker, flat-foldable, lint
verdict BENIGN. **No image of that model was ever produced or examined**, by
me or by the pipeline. `llm_client.py` has no image path at all
(`llm_client.py:154`, text-only `messages`), and a grep for
`screenshot|savefig|matplotlib` across `mcp_harness/` returns nothing outside
throwaway probes. The claim was true as far as it went; it just went less far
than the word "correct" implies.

---

## 2. The falsification record (measured this session — read before designing)

Four things were tried and killed. They constrain everything below, and each
is cheap to accidentally re-propose.

### 2.1 A VLM cannot validate a flat crease pattern — FALSIFIED, twice

**Test 1 (charitable).** Eight goldens, ground truth from our own instrument
(`cp_audit.py`), not from judgement: CLEAN = `quad`, `dog-repaired`,
`star-4`, `dog`; DEFECT = `hf-dog-nudged` (7 Maekawa), `bear-base` (9 Maekawa
+ 1 Kawasaki), `hf-dog-ladder-best` (5 Maekawa), `hf-crane-ladder-blb`
(2 Kawasaki + 1 arrangement). Rendered identically, anonymised A–H, **with
every interior vertex ringed** so the judge knew exactly where to look.

Result: κ = 0.497; **0/4** on Kawasaki and arrangement violations. Worse, the
corpus was confounded — the DEFECT patterns were also the densest (19–42
interior vertices vs 1–15), so a rule that reads nothing at all ("call the
busy ones broken") scores **8/8**. The VLM did not beat the rule that sees
nothing.

**Test 2 (density-controlled).** Take `dog.fold` (CLEAN, 15 interior
vertices) and flip the assignment of exactly one fully-interior crease.
Flipping M↔V changes |M−V| by 2 at both endpoints, converting two clean
vertices into a real Maekawa violation at a known location. The two arms then
have **identical** vertex count, edge count, geometry and layout, differing
in the colour of one line segment. Density is uninformative by construction.

Result: **zero detection** at native render resolution. Sampling more
opinions made it worse, not better — the consensus converged on invented
violations at vertices that were clean.

*(Design-integrity note: my first version of test 2 counterbalanced
presentation order but left the defective arm labelled "Q" in both arms. Only
the verified ±3px localisation requirement rules out a lexical prior. The
result stands; the design was sloppier than it should have been.)*

**Corroborated externally.** Evaluations of 15 current VLMs report that
performance is good on in-frame perception and "degrade[s] sharply when
integrating information across views", with persistent weakness in geometric
alignment ([arXiv:2512.02340](https://arxiv.org/html/2512.02340),
[arXiv:2509.06266](https://arxiv.org/html/2509.06266v1)). Maekawa's theorem
at a vertex is precisely a local geometric-alignment count.

**Consequence: the flat crease pattern is never rendered for judging.**
`cp_audit.py` extracts that information exactly, deterministically, in
milliseconds, and already does. This is not a rendering-quality problem to be
solved with a bigger canvas.

### 2.2 Silhouette IoU against a reference image — FALSIFIED

A uniaxial base is not a picture of the animal. Measured stack ratios
(Σ face area ÷ flat-folded silhouette area): dog **6.41×**, star-4 **7.99×**,
hshape **4.30×**, quad **3.02×**. The flat-folded state is an amorphous
wedge. Lang's own manual says it plainly: TreeMaker only provides a *base*.
COrigami independently reached the same conclusion — **their VLM is never
shown the collapsed base** (§4.4 below).

### 2.3 Rendering intermediate fold percentages — FALSIFIED

THEOREM Z (memory: `molecule-mobility-outcome`): compiled flat patterns are
rigidly locked, so the only self-consistent states are 0% and 100%. A probe
at 35% fold produced a tear gap of **1.947** — the mid-fold "photograph" is
of a torn sheet, and any critique of it is a critique of the tear.

### 2.4 Headless browser capture in CI — FALSIFIED (pre-existing)

`sim_capture.py:20-24` records the 2026-07-07 default-flip: headless
chromium's WebGL context never advances the GPU solver
(maxDisplacement 0.0000, tripping `DISP_GATE`), so `SimSession` defaults to
**HEADED**. Any design that needs the simulator in CI is dead on this
machine. Everything below is therefore pure Python.

---

## 3. Prior art (CLAUDE.md §0)

| Source | Finding | Adopted / rejected |
|---|---|---|
| **COrigami** ([arXiv:2606.26299](https://arxiv.org/abs/2606.26299)) §3.1, §3.8, §4.1, Table 2 | Three-tier evaluation; measured rubric and tournament ablations (§4 below) | **Adopted wholesale** — architecture, rubric shape, sampling constants, tournament, and the Procrustes similarity recipe |
| **CADSmith** (multi-agent text-to-CAD) | Outer loop "combines exact measurements from the OpenCASCADE kernel (bounding box dimensions, volume, solid validity) with holistic visual assessment from an independent vision-language model Judge". Median IoU 0.8085→0.9629; mean Chamfer 28.37→0.74; execution 95%→100% | **Adopted** — the closest adjacent-domain analogue of "VLM proposes, maths accepts", and evidence the split works |
| **CADCodeVerify** (ICLR'25) | Derive checks at draft time, answer them against the produced artifact | **Already adopted** — `anatomy_oracle.py:14-16` cites it. Extended here from counts to measured geometry |
| **"More Convincing, Not More Correct"** ([arXiv:2607.05904](https://arxiv.org/html/2607.05904v1)) | A reference-free LLM judge "scores plausibility, not correctness", leaving false-positive basins a policy learns to exploit | **Adopted as a hard constraint** — the VLM may never be the acceptor. §5.1 |
| Inference-time reward hacking ([arXiv:2506.19248](https://arxiv.org/pdf/2506.19248)); Best-of-N pessimism ([arXiv:2604.04648](https://arxiv.org/html/2604.04648)) | Proxy-gold divergence grows with optimisation pressure against a fixed proxy | **Adopted** — the equivalence-class rule (§5.4) caps that pressure structurally rather than by tuning |
| Multi-view VLM spatial reasoning ([arXiv:2512.02340](https://arxiv.org/html/2512.02340), [arXiv:2509.06266](https://arxiv.org/html/2509.06266v1)) | Cross-view integration is the measured weak axis | **Adopted as scope limit** — views are competed (best-of), never fused, exactly as COrigami does |
| Symbolic pre-execution contracts in EDA agent loops ([arXiv:2604.18834](https://arxiv.org/abs/2604.18834)) | 30%→84% multi-step pass rate, half the tool calls, by rejecting malformed calls before the backend | **Already adopted** — `tree_contract.py`. Precedent for putting the cheap check upstream |
| RTLFixer ([arXiv:2311.16543](https://arxiv.org/abs/2311.16543)); "Is Self-Repair a Silver Bullet?" (ICLR'24) | Breadth over depth at fixed budget | **Adopted** — the judge ranks an existing breadth fan; it does not open a new depth loop |
| Reference-free RL on a VLM score (COrigami §3.6) | r=−1 for invalid; else VLM aesthetic + intrinsic diversity `min(n/10,1)·0.6` | **Rejected for now** — we have ~10² subjects, not 10⁵ trajectories. RL on a 0.811-accuracy proxy at our sample size optimises the proxy's noise |
| COrigami's discrete box-pleating packer | Their Fig. 7 shows failure mass shifting into *their* packer as flap count rises | **Rejected** (same as Slice 0) — do not rewrite Tier 3 |

---

## 4. What COrigami actually does (sourced, because the details decide the design)

Three tiers, and **only two of them involve a VLM**:

| Tier | What is rendered | Views | Judge | Criteria |
|---|---|---|---|---|
| 1. Stick figure | the tree, embedded in 3D | **4** — Top, Side, Front, Isometric (Fig. 4) | VLM | topological accuracy (vertex/edge count vs the semantic target), proportional feasibility, semantic recognisability, structural complexity |
| 2. Collapsed base | **nothing** | — | none | symbolic only |
| 3. Shaped, folded model | the posed 3D model | **7** (Fig. 2) | VLM | correspondence to the prompt |

**Funnel:** 560,000 tree candidates → 113,276 valid stick figures (**20.2%**)
→ 27,869 viable models (**5.0%** overall). Their stage-1 gate discards four
candidates in five *before any geometry is computed*.

**The judge is a ranker, and only barely a classifier.** Table 2:

| Configuration | Acc | AP | F1 |
|---|---|---|---|
| Single model, T=0.0, N=1 | 0.715 | 0.565 | 0.640 |
| Single model, T=1.0, N=1 | 0.749 | 0.602 | 0.688 |
| **Single model, T=1.0, N=4** | **0.766** | **0.665** | 0.689 |
| Single model, T=1.0, N=16 | 0.741 | 0.652 | 0.669 |
| Tournament: view-selection only | 0.728 | 0.615 | 0.658 |
| **Tournament: double (view, then model)** | **0.811** | 0.651 | **0.74** |

Three things fall out, and all three are load-bearing below:

1. **N=16 is worse than N=4.** More opinions is not more signal — matching
   what our own test 2 found when consensus converged on hallucinations.
   Sample **four**.
2. **Pairwise beats absolute.** The double tournament runs two stages: first
   a tournament to pick the best *view* among the seven, then the best views
   of *different models* compared head-to-head with order swapped for
   position bias. 0.811 vs 0.766.
3. **Even at its best it is wrong roughly one time in five.** No human-
   agreement study is reported. This is a preference signal, not a verdict.

**The prompt is the largest measured lever** (§4.1 Part B, run at T=0.0/N=1).
The structured "Rubrics" prompt — which forces explicit verification of
appendage counts, topology, proportionality and differentiation *before*
scoring:

| Prompt (T=0.0, N=1) | Acc | AP | F1 | Δ vs Rubrics |
|---|---|---|---|---|
| **Rubrics** | **0.715** | 0.565 | 0.640 | — |
| Rubrics V0 | 0.631 | 0.465 | 0.631 | −0.084 |
| Score | 0.632 | 0.470 | 0.632 | −0.083 |
| Binary | 0.590 | 0.455 | 0.611 | −0.125 |

All three ablations share the **0.715** row, so the levers decompose cleanly,
each measured with the others held fixed:

| Lever | Move | Gain |
|---|---|---|
| **Prompt** (T=0.0/N=1, single) — Binary → Rubrics | 0.590 → 0.715 | **+0.125** |
| **Sampling** (Rubrics, single) — T=0.0/N=1 → T=1.0/N=4 | 0.715 → 0.766 | +0.051 |
| **Tournament** (Rubrics, T=1.0/N=4) — single → double | 0.766 → 0.811 | +0.045 |

**Prompt design is worth more than sampling and tournament combined**
(+0.125 vs +0.096). Any local re-ablation should spend its budget in that
order.

One detail inside the tournament number matters for §5.4(e). Part C's
view-selection-only variant scores **0.728** at T=1.0/N=4 — *worse* than the
0.766 single-model run at the same setting. Picking a best view among seven
does not help on its own; the gain arrives only when models are compared
**head-to-head**. The useful primitive is pairwise comparison, not view
selection.

**And the VLM never runs alone.** Their promotion filter is a conjunction:
VLM score > 0.6 **AND** `tree_similarity` > 0.9. That second term is
symbolic, and its recipe is fully reproducible: merge linear chains in the
stick figure to leave extremities and junctions; project the surviving joints
into 3D via the folding simulator; centre; normalise to unit Frobenius norm;
Procrustes-align by SVD; similarity = 1 − d².

---

## 5. Design

### 5.1 The architecture: VLM proposes, maths accepts

One rule, from which everything else follows:

> **No VLM output ever changes what is served. It changes only which of
> several already-valid candidates is preferred, or what the agent tries
> next. Acceptance is always a deterministic instrument.**

This is CADSmith's split (kernel measurements + independent VLM judge), and
it is the direct answer to the reference-free-judge failure mode: a judge
that scores plausibility cannot manufacture a false accept if it holds no
accept authority.

### 5.2 Three slices, and why in this order

| Slice | What | VLM? | Buildable today |
|---|---|---|---|
| **1. `base_fidelity`** — the tape measure | measure the *compiled artifact* against the *requested tree* | no | **yes** |
| **2. The tree eye** — 4-view stick-figure ranker | render the anatomy, rank candidates | yes | **yes** |
| **3. The model eye** — 7-view posed-model judge | COrigami's tier 3 | yes | **no** — §5.6 |

**The acceptor is built before the proposer.** Slice 2's whole safety story
is "every proposal is checked by arithmetic"; building the proposer first
would mean shipping a VLM in the loop with nothing to check it. Slice 1 also
de-risks cheaply: if it turns out the metric is vacuous (every base scores
identically), we learn that in a day rather than after a rendering stack.

### 5.3 Slice 1 — `base_fidelity`: measured proportion integrity

**The gap.** Proportion integrity is today tracked as *bookkeeping*, not
measurement. `nudge_marker` records that jitter was applied; `asymmetric`
records that a fallback fired; `served_fidelity` is a **count** (leaves
served ÷ leaves requested). Nothing anywhere measures *how far* the served
base drifted from what was asked for. `goldens/dog.fold` carries a **0.026**
mirror mismatch, and that number exists only because someone computed it by
hand once, in a test docstring.

New module `mcp_harness/base_fidelity.py`. Pure Python + numpy. Three
measurements, in increasing order of how much machinery they need:

**(a) Length drift — needs nothing but the two trees.**
```python
def proportion_drift(requested_tree, served_tree) -> dict
```
Per-edge relative drift `|L_served − L_requested| / L_requested`, its max and
mean, and per-bilateral-pair mirror mismatch `|L_a − L_b|`. This is the
number `nudge_marker` should always have been. Zero dependencies, zero engine
work, unit-testable off-line.

**(b) Folded flap-tip geometry — via `flat_fold()`, no browser.**
`flat_fold.flat_fold(fold)` is pure Python and matches the simulator to
**7e-6** (memory: `flat-fold-engine-slice1`). At ρ=π the flat-folded state is
one of the two self-consistent states THEOREM Z permits, so this is an honest
reading, not a torn intermediate. From it: realized flap lengths and the
realized tree metric between flap tips.

**Scope limit, stated up front:** `flat_fold()`'s honest domain is *raw hull
folds*. For squared or shaped folds this half returns `null`. It must never
return a fabricated number to keep a column populated.

**(c) Path-condition slack — needs one small binding.**
`get_node_locations() -> {node_id: [x, y]}` on the wrapper, exposing `tmNode`
locations after packing. The realized scale is
`s = min over leaf pairs of |loc(u)−loc(v)| / d_T(u,v)`, and per-pair slack is
`slack(u,v) = |loc(u) − loc(v)| − s·d_T(u,v)`.

**Slack is non-negative by construction** under that definition — the argmin
pair sits at exactly zero — so slack is not a feasibility test and must not be
reported as one. Two things in it *are* informative:

- **the distribution.** How many leaf pairs are near-active (slack ≈ 0, i.e.
  the pack is tight against them) versus slack ≫ 0 (paper left on the table).
  That is a graded read on how close to the packing frontier a tree sits, and
  it is the natural instrument for asking whether Slice 0's boundary rung
  actually bought room.
- **`s` versus the engine's own reported scale.** These are computed two
  different ways from the same solve; a disagreement is a genuine
  feasibility cross-check, and the only one available here.

It also yields a *paper-space* mirror residual for bilateral pairs, which is
distinct from (b)'s *folded* mirror residual — the scorecard column below is
the folded one; the paper-space figure stays internal unless (c) ships.

Sub-slice (c) is optional and separable — (a) and (b) ship without it, and
§6's Phase B′ makes entering it conditional on what they find.

**Scorecard.** `benchmark_subjects._COLS` gains two columns:
`length_drift_max` (float, from (a)) and `mirror_residual` (float or `null`,
from (b)). `nudge_marker` and `asymmetric` stay exactly as they are —
this adds measurement beside the bookkeeping, it does not replace it.

**Coupling to Slice 0, worth naming:** Slice 0's `test_boundary_symmetry`
specifies an A/B on mirror residual and explicitly warns against turning
`0.026` into a tolerance. `base_fidelity` *is* the instrument that test
needs. Whichever slice lands second gets it for free; neither blocks the
other.

### 5.4 Slice 2 — the tree eye: a 4-view ranker over candidates we already have

Five components.

**(a) The anatomical embedding — which we already compute and throw away.**

Our Metric Tree has no anatomical coordinates. `describe_tree_format`
(`server.py:2489`) defines a node as `{id, parent_id, length}` plus optional
`x`/`y` — and those are **"initial x on paper"**, i.e. *packing seeds*, not
anatomy. There is nothing to render.

But `mesh_to_tree.extract_skeleton` returns a **positioned** graph —
`pos = {node_id: np.array([x, y, z])}` from skeletor's SWC
(`mesh_to_tree.py:227`) — and `simplify_to_tree` carries `pos` on every
surviving node. `label_leaves` even serialises it, as
`{"label", "basis", "position"}` (`mesh_to_tree.py:636-642`). That structure
reaches exactly one consumer: `mesh_report.py`, which prints it as text. The
3D anatomy of every mesh-derived tree is computed, used for one report, and
discarded.

This is the **fourth** instance of the pattern CLAUDE.md §0 exists to catch
(after stub fracturing, edge optimisation, and Slice 0's boundary
conditions). The renderer's input already exists.

Add `anat_pos: [x, y, z]` (optional) to the tree:
- **mesh-derived:** plumb `tree.nodes[n]["pos"]` through `simplify_to_tree` →
  the emitted tree, for *all* nodes, not just leaves.
- **template / hand-authored:** a deterministic fallback layout from
  `body_plans.py`. Explicitly a layout, not a measurement, and labelled as
  such in the render so the judge is not told a guess is data.

**Hard rule — `anat_pos` is a display-only side channel.** It must never
reach `build_tree_from_json`, and it must never be confused with `x`/`y`,
which mean something else entirely on the very same object. This is exactly
Slice 0's rule-2 constraint, and it gets the same guard:
**attempt-0 output must be byte-identical after this slice**, by test.

**(b) The renderer — `mcp_harness/tree_render.py`, zero new dependencies.**

Verified available in the harness venv today: numpy 2.4.3, scipy 1.17.1,
**Pillow 12.2.0**, networkx 3.6.1. matplotlib is **not** installed and is not
needed — `PIL.ImageDraw` plus a numpy orthographic projection is enough for
line-and-node figures, renders in milliseconds, needs no GPU, no browser and
no display.

Four fixed orthographic views, matching COrigami exactly: **Top (xy), Side
(yz), Front (xz), Isometric**. Bones drawn as lines with thickness ∝ edge
`length`; leaves annotated with `leaf_labels` where available, including
their hedges (`label_leaves` is careful to say every label is a geometric
guess — the render must not launder that into a fact).

**Pillow must be pinned explicitly** in `ci.yml`. It is currently present
only transitively; `ci.yml:99` already documents this exact hazard for
scikit-learn ("arrive only TRANSITIVELY, via `skeletor==1.5.0 ->
scikit-learn>=0.23`"). Same reasoning, same fix.

**Never freeze a byte hash over the PNGs.** Memory
`rigid-frozen-hash-platform-divergence` records the general form of this
mistake: a frozen sha256 over roundoff-bearing artifacts cannot be green on
both macOS and Linux. Font rasterisation and PIL version differences make
image bytes strictly worse than floats here. Tests assert **structure**
(dimensions, that N bones produced N drawn segments, determinism *within* a
platform), never bytes.

**(c) An image-capable LLM client.**

`LLMClient.run_turn` (`llm_client.py:154`) is a non-streaming
`AsyncOpenAI` chat-completions call with text-only `messages`. Extend it to
accept OpenAI content-parts —
`{"type": "image_url", "image_url": {"url": "data:image/png;base64,…"}}` —
which Anthropic's OpenAI-compatible endpoint accepts. **The text-only path
must remain byte-identical**; images are additive.

Image tokens are the real budget risk here (memory:
`groq-token-limit-followups` for the 413 backoff already built;
`perfect-base-s6-outcome` for claude-sonnet-5 tokenising 44% denser than
assumed). Four views per candidate at modest resolution, with an explicit
per-turn image cap enforced in `_TurnBudget` (`agent_loop.py:95`).

**(d) The judge — `mcp_harness/tree_judge.py`.**

Every constant below is COrigami's measured optimum, not a guess:

- **Rubrics-style prompt** over their four stick-figure criteria — topological
  accuracy (vertex/edge count vs the semantic target), proportional
  feasibility, semantic recognisability, structural complexity — forcing
  explicit verification of each *before* any score. Worth **+0.125** accuracy
  over a binary prompt — the largest single lever they measured.
- **T = 1.0, N = 4.** Not N=1 (0.749), not N=16 (0.741).
- **Pairwise, order-swapped comparison** of two candidates, not absolute
  scoring (+0.045). Order swap is not optional — it is their stated control
  for position bias.
- **Only four views, and they are never fused.** Cross-view integration is
  the measured weak axis for current VLMs, and COrigami's own view-selection
  tournament *hurt* on its own (0.728 vs 0.766). We therefore present the
  four stick-figure views as a single side-by-side sheet and skip the
  view-selection stage entirely — it costs seven extra calls to buy a
  negative. Revisit only if a local ablation contradicts theirs.
- Output: a ranking plus a natural-language critique. **Never a verdict, never
  a score threshold.**

**(e) Where it plugs in — the equivalence-class rule.**

We already generate candidate fans everywhere: `reference_tree_from_query`
returns a candidate list, `mesh_to_tree`'s voxel/prune search sweeps
constants, `structural_search` enumerates, the rescue ladder fans variants.
Today every one is ranked by symbolic score alone, and ties are broken
arbitrarily.

The judge slots in as a **tie-breaker within symbolic-equivalence classes**:

1. Partition candidates by a class key built **only from discrete facts** —
   no raw floats, because equality on a continuous score is measure-zero and
   would make every class a singleton. The key is the tuple:
   `(gate_verdict, n_contract_errors, R, pairs_expected, pairs_kept, n_leaves)`.
   Every component is an integer or an enum that some existing instrument
   already emits.
2. Rank **only within** a class.
3. Never across classes.

If a later measurement shows the key is too coarse (huge classes) or too fine
(all singletons), the fix is to add or drop a discrete component — never to
introduce a float tolerance, which would reintroduce the arbitrariness the
key exists to remove.

This forecloses reward hacking *structurally* rather than by tuning: the VLM
is mechanically incapable of promoting a symbolically-worse candidate, so
there is no gradient for it to exploit. It is the strongest available reading
of "VLM proposes, maths accepts", and it is why no reward model, no
threshold, and no RL appears anywhere in this design.

### 5.5 What is deliberately never rendered

Restating §2 as a design commitment, because each of these is a natural thing
to propose later:

- the flat crease pattern, for judging (§2.1);
- the collapsed base, as a silhouette-IoU target (§2.2) — COrigami
  independently renders nothing at this tier;
- any intermediate fold percentage (§2.3).

### 5.6 Slice 3 — the model eye, and its pre-registered entry condition

COrigami's 7-view judge looks at a **shaped, posed** model. We do not have
one. `shaping.py` does tip-local reverse folds and crimps; `shaping_deep.py`
extends that at depth; `pose_base.py` names sites. There is no general pass
that takes a served base plus a pose target and returns a recognisable 3D
model, and memory records `docs/dog.fold` never folds in the simulator at
all.

Rendering seven views of a uniaxial base would be §2.2 with more pictures.

**Entry condition (pre-registered).** Slice 3 begins when a shaping pass
exists that, for at least one template, produces a folded model which:

1. folds in the simulator without tearing — `maxDisplacement ≥ DISP_GATE`,
   0 NaN (`sim_capture.check_capture`); **and**
2. reaches `tree_similarity ≥ 0.9` against its own stick figure, computed by
   COrigami's recipe (§4) using `sim_capture.tracked_points` for the 3D joint
   projection and `scipy.linalg.orthogonal_procrustes` — **verified present**
   in the venv today — for the alignment.

Until both hold, the 7 views have nothing recognisable to look at, and
COrigami's 0.811 does not transfer, because it was measured on shaped models.

---

## 6. Phasing and stopping rules

Every phase has a pre-registered stop. These are commitments, not
aspirations — Slice 0 uses the same discipline and the 2026-07-31 gate
retrain is the precedent for actually honouring one (measured, NO SHIP).

**Phase A — `proportion_drift` (§5.3a).** Half a day. Compute it across the
committed scorecard fixtures.
> **STOP IF** every served base reports drift < 1e-9. That would mean the
> metric is vacuous on our corpus and the bookkeeping was already sufficient.

**Phase B — folded geometry (§5.3b) + scorecard columns.**
> **STOP IF** `flat_fold()` returns `null` for every serving subject — the raw
> hull domain would then be too narrow to measure anything real.

**Phase B′ — path-condition slack (§5.3c), conditional.** The wrapper
binding, and the only engine work in this spec. Deliberately has no
unconditional slot: it is entered **only** if Phases A and B leave a question
that paper-space geometry would answer — for instance, drift that is real but
whose cause is ambiguous between packing pressure and jitter. If A and B are
already conclusive, B′ is not built (open question 4).

**Phase C — equivalence-class census.** Before any rendering code: measure how
often symbolic-equivalence classes have size > 1 across the fixture subjects.
> **STOP IF** classes are overwhelmingly singletons. A tie-breaker with no
> ties is dead weight, and this is a half-day question that gates a
> multi-day build.

**Phase D — renderer + image client.** `tree_render.py`, `anat_pos`
plumbing, `LLMClient` content-parts, Pillow pin, attempt-0 guard.

**Phase E — judge + measurement.** Rubric, N=4/T=1.0, tournament,
equivalence-class tie-breaker.
> **STOP IF** either tripwire fires (§7).

**Phase F — Slice 3.** Only on the §5.6 entry condition.

**Scope control for the implementation plan.** Phases A–C are one plan: they
are all cheap, all deterministic, and all three carry stopping rules that can
cancel everything downstream. Phases D–E are a **second** plan, written only
after Phase C reports. Writing one plan across all five would commit build
effort to a rendering stack that Phase C might show has no ties to break.

---

## 7. Measurement, and the two tripwires

**The split.** `benchmark_subjects`' subject list, partitioned once and
committed **before** Phase E starts: the four templates already used for
attempt-0 guards stay in the *development* half; the mesh-derived subjects
form the *held-out* half. Fixed in a fixture, not chosen at measurement time.

**Primary metric.** On the held-out half, do VLM-preferred candidates produce
equal-or-better downstream serve outcomes (rescue stage, `served_fidelity`,
`length_drift_max`) than the arbitrary tie-break they replace?

**Tripwire 1 — Goodhart.** If VLM-preferred candidates show *worse* symbolic
outcomes than the candidates they displaced, that is the proxy-gold
divergence signature. Stop and record.

**Tripwire 2 — the density lesson.** The judge must beat a **trivial
baseline** — ranking by leaf count, or by symbolic score with a fixed
tie-break — by a margin fixed *before* measuring. §2.1's confound is the
whole reason this exists: a rule that reads nothing scored 8/8 and would have
looked like success.

**Never tune the rubric on the subjects used to measure it.** Hold-out split
fixed before Phase E begins.

---

## 8. Testing

| Test | Asserts |
|---|---|
| `test_proportion_drift` | per-edge drift and mirror mismatch on hand-built trees; 0.0 for an untouched tree; symmetric under pair swap |
| `test_base_fidelity_folded` | `flat_fold`-derived flap lengths on `star-4` and `quad`; returns `null` (never a number) for a squared/shaped fold |
| `test_node_locations` | `get_node_locations` covers every node; slack ≥ 0 for a packed tree; realized scale matches the engine's within tolerance *(sub-slice c only)* |
| `test_anat_pos_side_channel` | `anat_pos` present on a mesh-derived tree; **rejected** by `build_tree_from_json`; never confused with `x`/`y` |
| `test_attempt0_unchanged` | **byte-identical** attempt-0 output for all four templates |
| `test_tree_render` | 4 views produced at fixed dimensions; N bones → N segments; deterministic within a platform; **no byte-hash assertion** |
| `test_llm_client_text_path` | text-only `run_turn` produces a byte-identical request payload to today's |
| `test_llm_client_images` | content-parts assembled correctly; per-turn image cap enforced |
| `test_equivalence_classes` | partition is exact; the judge is never consulted across classes; a singleton class skips the VLM entirely |
| `test_judge_offline` | rubric assembly, N=4 aggregation and order-swap pairing tested against a **recorded** transcript — no live API in the suite |
| `test_scorecard_columns` | `length_drift_max` and `mirror_residual` present; `mirror_residual` `null` outside the raw-hull domain; `nudge_marker`/`asymmetric` unchanged |
| Regression | full suite from the **MAIN** checkout; expect the documented 4/2124/11 shape ± re-blessed rows |

Per memory `perfect-base-s7-outcome` and `ubuntu-platform-truth`: run with
`--timeout=420` (bare `make test` never terminates on macOS), and check host
CPU for orphaned processes before timing anything — a 5-day orphan once ran a
gate 6× slow and would have manufactured timeout failures.

Per memory `worktree-borrowed-so-inflates-failures`: all builds and blesses
from the MAIN checkout. A worktree borrowing main's `.so` reports 27 baseline
failures instead of ~3.

---

## 9. Risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | The VLM ranker costs tokens every turn and buys nothing measurable | Tie-breaker only; held-out measurement; two pre-registered tripwires (§7); Phase C kills it early if there are no ties to break |
| R2 | `anat_pos` leaks into the packing path and changes attempt-0 | Hard side-channel rule; `test_attempt0_unchanged` asserts byte-identity. Same guard as Slice 0 rule 2 |
| R3 | Renders diverge across platforms (fonts, PIL version) and a frozen hash goes permanently red | Never hash the PNGs. Assert structure only. Memory `rigid-frozen-hash-platform-divergence` is the precedent |
| R4 | Pillow is transitive-only in CI and vanishes on a dependency bump | Pin it explicitly, with the reasoning `ci.yml:99` already records for scikit-learn |
| R5 | Image tokens blow the turn budget | Explicit per-turn image cap in `_TurnBudget`; 4 views, modest resolution; the 413 backoff already exists |
| R6 | The judge's critique gets treated as ground truth by the agent and drives it to chase a hallucinated defect | Critique is surfaced as *advice with provenance*, following `anatomy_oracle.py`'s suppression discipline — the file's own warning is that an oracle firing on an impossible target "trains it to chase impossible repairs" |
| R7 | `flat_fold()`'s raw-hull domain is too narrow for `mirror_residual` to populate | Phase B stopping rule; the column is `null`, never fabricated |
| R8 | Slice 3 never becomes reachable because the shaping pass never lands | Explicitly out of scope here, with a pre-registered entry condition. Slices 1–2 stand alone and deliver without it |
| R9 | We adopt COrigami's constants and they do not transfer (different VLM, different renders, different subjects) | Every constant is labelled with its source and its measured alternative, so a local re-ablation is a parameter change, not a redesign |

---

## 10. Out of scope

- Reinforcement learning on the VLM score. COrigami runs it over 10⁵
  trajectories; we have ~10² subjects, and RL against a 0.811-accuracy proxy
  at that sample size fits the proxy's noise.
- Any change to `cp_audit`, `lint_verdict`, `_audit_score`, or the acceptance
  ratchet. Those are the acceptors; this spec adds instruments beside them.
- Rewriting Tier 3 (the packer), or adopting box-pleating.
- The frontend Concept Art Board. Renders are produced as files and consumed
  by the judge; surfacing them in the UI is a separate slice.
- Slice 0's boundary conditions (its own spec).
- Concept-art image *generation* (CLAUDE.md §5 Step 1). This spec is about
  looking at what we built, not generating references.

---

## 11. Open questions

1. **Is the judge's critique surfaced to the user, or consumed only by the
   agent?** Proposed: surfaced, following the `[ANATOMY]` / `[CP AUDIT]`
   oracle pattern — but *inform-only*, never composed as a standing
   imperative, which `anatomy_oracle.py:20-24` records as a review-confirmed
   fix on the CP AUDIT side.
2. **Does the tie-breaker live in `agent_loop` or inside
   `reference_tree_from_query`?** Proposed: inside the tool that produces the
   candidate list, so the ranking is testable without an agent turn.
3. **Should `anat_pos` be persisted into served `.fold` metadata** for later
   frontend use? Proposed: no, not in this slice — it widens the artifact
   contract for a consumer that does not exist yet.
4. **Sub-slice 5.3(c) — worth the binding?** It is the only engine work in
   this spec. Proposed: defer until (a) and (b) have measured something, then
   decide on evidence.
