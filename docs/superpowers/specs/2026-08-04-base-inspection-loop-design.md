# The base inspection loop — letting the agent see what it built

**Date:** 2026-08-04
**Status:** design, revised 2026-08-04 after codebase review — **ready for
implementation planning**
**Author:** brainstorming session (Claude + raphaeldchen)
**Supersedes:** `2026-08-02-visual-feedback-loop-design.md` (merged in PR #71,
never reviewed). §1.2 itemises what carries over and what is withdrawn.

**Rebased.** The first two commits of this spec were written against main
`78a141c`; it now sits on `1c9abe0`, 22 commits later. The gap matters, and not
only for line numbers: **PR #72 shipped path reconciliation, which deliberately
re-parents flaps.** A metric keyed on parent pointers would have read that
feature as a defect on every reconciled pair. §3.3.1 is the result.

**What the revision changed** (each item is a codebase finding, not a
preference):

| § | Was | Now | Because |
|---|---|---|---|
| 3.3.1 | `reparented` + per-edge `length_drift`, keyed on node id | leaf-to-leaf path matrix on the free tree | three shipped anatomy-preserving paths change parent pointers; `pair_reconcile.py:177-186` already names the correct metric, and it is the packer's own constraint variable |
| 3.3.2 | `shadow_diff(requested, served)` | `shadow_diff(requested, served, locs)` | a stub flap is structurally absent from every Python node list — clause 2b is unmeasurable without `locs` |
| 3.3.4 | oracle discipline, no suppression list | five named suppressions + the unexplained-drift rule | [ANATOMY]'s own docstring: an oracle firing on the unfixable trains the agent to chase it |
| 3.4 | add `anat_pos` to tree nodes, guarded as a side channel | read the existing `leaf_labels[nid]["position"]` | the field was never built and is not needed; the data already lives off the node list |
| 3.5 | control = a re-parented limb | control = two packing basins for one tree | Phase 1 now catches re-parenting, so it cannot test whether looking adds anything |
| 3.5 | null = two node-order variants | null = two serves in the *same* basin, asserted | node order is the lever that moves the basin — the old null was the new clear-gap |

---

## 1. The question, and what changed

**Asked:** the user can open the 2-D crease-pattern panel, the 3-D simulator,
or the model view and inspect what the pipeline produced. The agent cannot.
Give the agent that ability, so it can look at a base it just built, notice
that a limb is wrong, and fix it.

**Answered:** the ability is worth building, but almost none of it is a
picture, and the one picture that matters is not the one anybody reaches for.

Three findings decide the design:

1. **A folded base cannot show anatomy — to anyone.** A uniaxial base is
   *defined* by all flaps lying on a single axis; when flattened, "every flap's
   tip aligns along one central line"
   ([Abrashi](https://abrashiorigami.com/uniaxial-base/),
   [UMass](http://linkage.cs.umass.edu/origamiLang/origami.html)). Folding is
   the operation that destroys spatial separation between limbs. This is not a
   rendering limitation to be fixed with a better camera.
2. **But the base's *shadow* is its tree, exactly, by construction.** The same
   sources: a uniaxial base's structure "can be determined solely from the
   properties of its shadow," and that shadow is the stick figure. So
   "does the base realise the requested anatomy" reduces **completely** to tree
   arithmetic. There is no residual visual question at this tier.
3. **Anatomy is visible one step earlier, in paper space.** Circle/river packing
   gives every flap "a circular region whose radius equals the length of that
   flap" (Lang, *Origami Design Secrets* ch. 11). In the packing, each limb
   still owns its own patch of the square. That is the last moment at which a
   limb has **extent** rather than only **length**.

### 1.1 Why the agent looks, rather than a judge looking for it

The superseded spec built an independent VLM judge. This one does not, on the
user's proposal and on the evidence.

> ⚠ **Every number in this section is from published work in other domains —
> web-page and chart generation. None of it was measured on this system.** It
> is cited to justify a *direction* (acceptor before eyes), not to predict a
> magnitude here. Where a claim in this spec rests on our own measurement it
> says so and names the artifact.

The canonical experiment for "look at your own render and revise" is
**Design2Code** (484 real webpages): for strong models self-revision is net
**negative** — GPT-4o 93.0/98.2/85.5/84.1/90.4 → 92.7/98.6/84.9/83.3/90.1,
worse on four of five metrics; Claude 3 Opus flat-to-down. **ChartMimic** shows
the sign is a function of generator strength: +3.6 at GPT-4o, +2.6 at 76B,
−0.5 at 26B, −5.5 at 8B, −6.6 at 2B.

**Huang et al. (ICLR 2024)** isolates the cause. With an external oracle
stopping label, GPT-4 on GSM8K goes 95.5 → 97.5. Without one,
**95.5 → 91.5 → 89.0**. The published self-repair gains came from the oracle,
not the critique.

> **Consequence, and it sets the phase order:** an agent inspecting its own
> work with no deterministic acceptor is the configuration measured to make
> things *worse*. Phase 1 is not a safety wrapper around Phase 3 — it is the
> precondition that makes Phase 3 function at all.

Egocentric bias (models score their own output higher, MLLM-as-a-Judge) is the
main argument for an independent critic. It binds when the critic holds accept
authority. Here it holds none (§3.1). COrigami needs independence because their
VLM score is half a promotion conjunction and an RL reward; ours is a comment
in a transcript.

### 1.2 What carries over from the superseded spec, and what is withdrawn

**Carried:** the acceptance rule (§3.1); the never-render list (§2); the
byte-identity guard on attempt-0 output; the renderer choices (Pillow, no
matplotlib, never a byte hash over PNGs, pin Pillow in `ci.yml`); the
discipline of pre-registered stopping rules.

⚠ The `anat_pos` **side-channel rule** is *not* carried, and this is a
correction to the first draft of this spec, which listed it here. The rule
guarded a tree-node field that was never built and is not needed — the
coordinates already live off the node list, on `leaf_labels` (§3.4). The
byte-identity guard it travelled with is carried, because that guard was
always the part doing the work.

**Withdrawn, with reasons:**

| Withdrawn | Why |
|---|---|
| The equivalence-class tie-breaker (§5.4e) | The candidate fan it ranks does not exist. `auto_mesh_to_metric_tree` documents itself **"First FOLD wins"** (`mesh_to_tree.py:1209`) — a ranked queue that exits on first success. `reference_tree_from_query` returns one report, not a list (`server.py:2354`). Multiple compiled candidates arise only on the S2 drain, which the code calls the failure path. |
| Its class key `(gate_verdict, n_contract_errors, R, pairs_expected, pairs_kept, n_leaves)` | `R` and `pairs_expected` come from the static anatomy reference (`benchmark_subjects.py:158,163`) and are constant across a subject's candidates. `pairs_kept` is `len(res.pairs)` — **post-compile** (`:164`), so the key cannot be computed without compiling everything. No field named `gate_verdict` exists; the gate returns `verdict ∈ {feasible, infeasible, compile_anyway}` (`server.py:2338`). A `_serve_rank` tie (`mesh_to_tree.py:795`) is the partition the codebase already has. |
| `tree_similarity` / Procrustes | ≈1.0 by construction on any successful compile — the base's shadow *is* the tree. `scipy.linalg.orthogonal_procrustes` optimises over O(n), so **a base with left and right limbs swapped scores identically to the correct one**. Needs internal-node paper positions that no binding exposes. |
| Judge machinery — N=4, T=1.0, pairwise order-swap, tournament, rubric-assembly, recorded-transcript offline test | All are *judge* mechanics. With the agent looking directly they have no host. |
| `length_drift_max` as the primary new column | Measured: `nudge_marker` is **False on all five scorecard subjects**, and `_STAGE_INTEGRITY` (`mesh_to_tree.py:114`) defines `order`/`placement` as proportion-preserving. Per-edge length drift is exactly 0 everywhere. Subsumed by `path_drift` (§3.3.2), which measures the same thing on the key that survives a rehome. |
| Slice 0 coupling | Slice 0 was falsified 2026-08-03; all three of its motivations in the old spec are dead. |

---

## 2. Never rendered — the falsification record

Inherited from the superseded spec's §2, all still binding, plus one new entry.

1. **The flat crease pattern, for judging.** Falsified twice, including a
   density-controlled test (flip one fully-interior crease's M/V: identical
   geometry, zero detection; sampling more opinions made it worse).
   `cp_audit.py` extracts this exactly, in milliseconds.
2. **The collapsed base as a silhouette target.** Stack ratios dog 6.41×,
   star-4 7.99×, hshape 4.30×, quad 3.02×.
3. **Any intermediate fold percentage.** THEOREM Z: compiled flat patterns are
   rigidly locked; a 35% probe produced a tear gap of 1.947.
4. **Anything requiring the simulator in CI.** Headless chromium never advances
   the GPU solver, so `SimSession` defaults to HEADED (`sim_capture.py:64`).
5. **NEW — the folded base as an anatomy view.** Independently confirmed
   (§1 finding 1) and directly observed: `docs/superpowers/evidence/
   2026-08-03-reparented-bases/bases.svg` (commit `26513f5`) draws the
   `flat_fold` state as translucent polygons; the panels are featureless
   wedges. Its own README states the limit — *"a flat-folded silhouette shows
   layer structure, not limb placement."* Do not build a folded-base symmetry
   metric; it would measure layer stacking and read as anatomy.

**One open item, deliberately unresolved:** entries 2 and 5 are established for
the *flat-folded* state. The **3-D simulator view of a base** is unmeasured.
§5 schedules exactly one calibration capture to close it. It is not on any
critical path.

---

## 3. Design

### 3.1 The rule everything follows from

> **No VLM output ever changes what is served. It changes only what the agent
> tries next. Acceptance is always a deterministic instrument.**

Unchanged from the superseded spec. It is also what makes §1.1's evidence
apply: the deterministic acceptor is the oracle whose presence flips
self-inspection from negative to positive.

### 3.2 What "the base is right" means, completely

Because the base's shadow is its tree exactly, base correctness decomposes into
four clauses with no visual remainder:

| # | Clause | Instrument | Status |
|---|---|---|---|
| 1 | Valid folding — Maekawa, Kawasaki, faces close | `cp_audit`, Oriedita lint | shipping |
| 2a | Right number of flaps | `served_leaves` vs `R` | shipping |
| 2b | **No invented flaps** | `stub_flaps`, and `json_id == -1` in `locs` | measured, **never reaches the agent** |
| 2c | Each flap the requested length | — | **unmeasured** |
| 2d | **Right topology** — each flap attached where asked | — | **unmeasured** |

⚠ 2c and 2d are listed separately because that is how they read in English, but
they are **one measurement**, not two: both are displacements in the
leaf-to-leaf path metric, which is the quantity the packer consumes and the
quantity the base's shadow realises (§3.3.1). Any instrument that separates
them is keyed on rooting, and rooting is bookkeeping this pipeline
deliberately rewrites.
| 2e | Bilateral pairs congruent | `pair_path_gap_max` | shipping (0.0 all subjects) |
| 3 | Physically folds without tearing | `sim_capture` / `DISP_GATE` | headed-only, dev machine |
| 4 | Paper used sensibly | `hull_coverage`, packing `scale` | observed, never acted on |

Live gaps: **2b, 2c, 2d**. Phase 1 closes them.

Out of this frame by construction, and correctly so: *does the tree read as the
subject* (upstream — Phase 2/3), *will it look like the subject when shaped*
(downstream — blocked on shaping), *is it an elegant design* (no instrument).

### 3.3 Phase 1 — shadow-tree equality

**The enabler.** The served tree is currently discarded. **After a rescue,
nothing downstream knows which tree was compiled.**

⚠ **There are TWO ladder paths, and the first draft named only the secondary
one.** Corrected here before planning, because the difference changes what the
fix is:

| | **Child path** | **Parent path** |
|---|---|---|
| Entry | `_worker_compile_and_regions` | `_compile_with_perturb` (`server.py:1350`) |
| Discard site | `_run_rung` returns `(fold, (regions, scale, locs))`; the tree dies in the closure (`:372`) | `_run_rung` returns `(r, None)` (`:1388-1395`); `served` unpacks as `rung, asym, result, **_payload**` (`:1401`) — the underscore is the codebase telling us |
| Carrier out | queue payload `{fold, regions, scale, locs}` (`:392-407`) | **a bare fold string** — that is the whole return type |
| Reaches | `suggest_pose_stack`, `apply_shaping_ops`, `suggest_flap_for_region` | **`draft_and_compile_full_base` (`:1584`)** and `compile_base` (`:2420`) — i.e. the serve |

The first draft's "one field on that payload" is right for the child path and
**cannot work for the parent path**, which is the one that actually serves a
base. This is the `bare HeadlessTreemaker ≠ the serve path` failure recorded
twice already in project memory, and it is why `test_served_tree_plumbed` must
assert at `draft_and_compile_full_base` and not at the worker.

**The parent path's carrier is a parent-process serve record, not the fold.**
Stuffing the tree into the fold is closed off by measurement: `frame_title` is
"the only annotation channel Oriedita's strict parser accepts"
(`server.py:938-940`), and it is a display string the bridge already parses for
markers. So `_compile_with_perturb` — which holds both the requested `nodes`
and the winning `candidate` — records the pair in a module-level last-serve
slot in the MCP server process, and `read_base()` (an MCP tool in that same
process, §3.3.3) reads it. No fold bytes change, which makes
`test_attempt0_unchanged` true by construction rather than by care.

Both paths are plumbed; only the child path's fix is the one-line one.

#### 3.3.1 The metric is the leaf-to-leaf path matrix, not parent pointers

The first draft of this section specified `reparented` as "nodes whose parent
differs" and `length_drift` as per-edge relative drift — both keyed on node id.
**That is the wrong key, and this codebase already says so, in a comment
written by someone who hit the same edge.**

`rescue_ladder.PRESERVING_STAGES` is keyed on `(id, length)`, and `rehome` is
excluded from it *for precisely this reason*: re-rooting "is a no-op
topologically… no length is invented and none is dropped… it is only
**re-attributed across node ids** (which is exactly why a rehomed rung is not
in PRESERVING_STAGES — that set is keyed on (id, length))"
(`rescue_ladder.py:715-724`). An id-keyed diff reports every node on the
re-rooting path as re-parented and every edge on it as drifted, for a
transformation that provably changes no anatomy.

Three live paths defeat the id key, one of them shipped this week:

| Path | An id-keyed diff reports | What actually changed |
|---|---|---|
| `rehome` (`rescue_ladder.py:715`) | N re-parented, N edges drifted | **nothing** — rooting is bookkeeping, the free tree is identical |
| `contract_slivers` (`:640`) | 1 dropped, M re-parented | one sub-threshold *interior* edge; leaf set invariant by hard guard (`:710`) |
| path reconciliation (**shipped, PR #72**) | 1 re-parented, 1 edge drifted | nothing at the tip — it "grows its edge by precisely the distance travelled, **so the tip does not move at all**" (`mesh_report.py:51`) |

The rank table states the invariant outright: normalize is "every SURVIVING
edge keeps its requested length, but the graph changed… **Anatomy — the leaf
set and the pairs — is preserved by construction**" (`:116-119`). A metric that
fires there is measuring the optimiser's scratch work, not the design.

**The right instrument is the leaf-to-leaf path metric on the free (unrooted)
tree** — and this is not an invention. It is the instrument
`max_pair_path_gap` already names as the correct one:

> "⚠ NECESSARY, NOT SUFFICIENT… Two leaves equidistant from the root can still
> sit at different tree distances from a THIRD leaf, and **it is the full
> leaf-to-leaf metric that circle packing consumes**. … if one scalar ever has
> to carry the claim, prefer `max |d(sx, sy) - d(x, y)|` over leaf pairs. This
> is the cheap scalar." — `pair_reconcile.py:177-186`

It is also, literally, the compiler's input. `tmPath` is "a path from one node
to another along the tree, but a subset of the **leaf paths** also serves as
the basis of the crease pattern", and `mMinTreeLength` is "the minimum length
of this path in tree units **as specified by the tree**"
(`treemaker/Source/tmModel/tmTreeClasses/tmPath.h:36-47`). The scale optimiser
drives each leaf path's achieved paper length to at least `scale ×
MinTreeLength`. Comparing leaf-to-leaf path matrices compares exactly the
quantity the packer consumes — not an analogy for it, and not a proxy.

This is also what §1's central finding *means* operationally. If the base's
shadow is its tree, the shadow realises leaf-to-leaf tree distances as
distances in the plane. The theorem does not merely justify skipping the
renderer; it names the metric.

#### 3.3.2 The measurement

New module `mcp_harness/shadow_tree.py`, pure Python, no engine import:

```python
def shadow_diff(requested_nodes, served_nodes, locs=None) -> dict
```

⚠ **`locs` is a required input for clause 2b, not an optional extra.** The
first draft read `invented` off `served_nodes`, which cannot work: a stub flap
"is created inside the engine and is **structurally absent from any Python node
list**, so it can never inflate this count" (`anatomy_oracle.py:78-82`).
Engine-made leaves surface only through `leaf_node_locations()`, under the
`json_id = -1` convention (`server.py:415`, `TreemakerWrapper.cpp:639`).
Without `locs`, clause 2b is unmeasurable by construction.

| Field | Clause | Definition |
|---|---|---|
| `invented` | 2b | count of `json_id == -1` entries in `locs` |
| `dropped` | 2a | requested **leaf** ids absent from the served leaf set |
| `contracted` | — | requested **interior** ids absent from the served node set — bookkeeping, reported separately so a sliver merge never reads as a lost flap |
| `path_drift_max` / `path_drift_mean` | 2c + 2d | `abs(d_served(x,y) − d_requested(x,y)) / span` over every surviving leaf pair |
| `worst_pairs` | 2c + 2d | the leaf pairs attaining the max, so a finding localises to a limb |

`d` is summed over the undirected tree path; `span` is the largest requested
root-to-tip length, matching `max_pair_path_gap`'s normaliser so the two
columns are read on one scale. Clauses 2c and 2d **collapse into a single
number**, which is correct: a wrong length and a wrong attachment point are the
same defect in the metric the packer consumes, and separating them was an
artifact of the id key.

**Leaf-id matching is sound where parent-id matching is not**, and every ladder
stage is what makes it so. `contract_slivers` bans leaves and paired nodes as
victims outright and returns `None` unless `leaf_ids(out) == leaf_ids(nodes)`
(`:670-712`). `rehome` carries the mirror guard, because reversal can strand
the old root into a new leaf — "on corpus_wide row 44 … rehoming to 1 takes the
leaf count from 1 to 2" (`:766-776`). Path reconciliation states "the leaf set
is invariant" as a contract and runs its removal loop to a fixpoint to hold it
(`pair_reconcile.py:235-244`). Leaf identity survives every path; rooting does
not survive any of them.

**One clause resolves to a number rather than a zero, and that is correct.**
`contract_slivers` discards the sliver's own length rather than folding it into
its children — "DOG_REPAIRED keeps 0.221399 and 0.25626 verbatim, not
0.239992" (`:658-661`) — so a contraction genuinely shortens some leaf-to-leaf
paths. The bound is **per contraction**: each victim is under
`SLIVER_RATIO × longest = 0.08 × longest` (`:616`), and several victims can lie
on one leaf-to-leaf path, so the worst normalised drift is bounded by
`contracted × SLIVER_RATIO`, not by `SLIVER_RATIO`. Real, bounded,
explainable, and it should be reported. It is not a false positive to be tuned
away, and no tolerance should be fitted to hide it.

#### 3.3.3 The tool

`read_base()` — read-only, no recompile, no mutation. Returns the
`shadow_diff`, the rescue stage and its admissibility class
(`rescue_ladder.INVENTS_ANATOMY` alongside the honesty rank), the packing
`scale`, `cp_audit` counts, the `leaf_node_locations` table, `hull_coverage`,
and the stub inventory. ⚠ `locs` is not cached against a fold handle; the tool
must read the values already carried on the serve payload, never trigger a
fresh compile (`suggest_pose_stack` documents this cost at `server.py:2053`).

#### 3.3.4 `[FIDELITY]` is an unexplained-drift detector

Following `anatomy_oracle.py`'s discipline exactly: inform-only, **never an
imperative left standing in context**, dirty flag consumed per firing, and
`decide()` always returns *why* it stood down. It ships with **zero repair
budget** in this spec. `anatomy_oracle.py:33` is the precedent for shipping a
quiet instrument honestly: it "fires on NOTHING today, and that is the honest
state rather than a defect… a REGRESSION TRIPWIRE."

Its suppression rule falls out of §3.3.1. Every deliberate transformation in
this pipeline already announces itself — `PLACEMENT_MARKER`,
`NORMALIZE_MARKER`, `STUB_MARKER` on the served fold (`server.py:866-895`) and
`_pair_reparent_lines` in the reference report (`mesh_report.py:45`). So:

> **`[FIDELITY]` fires only on drift that no marker explains.** Explained drift
> the agent has already been told about, with evidence, by a channel that
> predates this spec. Unexplained drift is the defect class nothing catches
> today, and it is the only thing this oracle is for.

| # | Suppression | Why |
|---|---|---|
| 1 | `unknown-tree` | the incremental `compile_base` path takes no tree at all. "I do not know what was served" is not "nothing was served" — [ANATOMY]'s (1b), rated BLOCKER on adversarial review |
| 2 | `stage-stub`, on the `invented` clause only | the stub stage runs only after every anatomy-preserving rung has failed, and the fold already carries `STUB_MARKER` with the count. Firing here instructs a chase the ladder has already exhausted — the exact failure `anatomy_oracle.py:28` names |
| 3 | `sliver-contraction` | drift ≤ `SLIVER_RATIO × longest` on a `normalize` serve, already stated by `NORMALIZE_MARKER` |
| 4 | `reconciled-pairs` | drift attributable to path reconciliation's re-parenting, already itemised with evidence by `_pair_reparent_lines` |
| 5 | `no-drift` | every clause zero — stand down with the reason recorded, per [ANATOMY]'s `anatomy-complete` |

**It deliberately does not suppress on the fake provider, and the asymmetry is
load-bearing.** [ANATOMY] suppresses there (its (2)) because the fake provider
maps unrelated prompts onto the same fixture, corrupting the *reference* `R` it
grades against. `shadow_diff` grades **requested against served** — both ours,
on any provider. So `[FIDELITY]` is measurable on the committed fixtures,
offline, with no mesh stack and no network, which `[ANATOMY]` is not. Its tests
are therefore ordinary unit tests.

For the same reason it needs **neither** of [ANATOMY]'s reference-derived
suppressions — `no-mesh-report`, `no-reference-count`, `R-unservable`. It never
consults `R`. A subject above the packable window (fish at R=10, insect at
R=9) is silenced there because the *anatomy* is unreachable; `[FIDELITY]` asks
only whether the tree that was compiled is the tree that was requested, which
is a fair question at any leaf count. Stated explicitly because the obvious
move when copying an oracle is to copy its suppression list.

**Also:** print the leaf `position` coordinates in the reference report — one
line in `mesh_report._anatomy_lines`, which today reads `label` and `basis` off
`leaf_labels[nid]` and drops the third key. The coordinates already exist:
`leaf_labels` is `{leaf id → {label, basis, position}}` (`mesh_to_tree.py:197`,
written at `:776`). This is Phase 3's Gate-2 experiment and it is nearly free.

### 3.4 Phase 2 — two renderers, human-facing first

`mcp_harness/tree_render.py`. Pillow 12.2.0 + numpy, both present; matplotlib
absent and unneeded. Renders are written as files and surfaced; no model sees
them in this phase.

**(a) The packing diagram — the one view that carries anatomy.**
The unit square, one labelled circle per leaf at its packed location, radius
proportional to the flap's length, from `leaf_node_locations()`
(`mcp_harness/TreemakerWrapper.cpp:681`, already consumed in production at
`server.py:266,318`). Engine-made leaves (json_id `-1`) drawn distinctly.

Reads directly off it: two equal mirrored circles = congruent pair; a small
circle = a stunted limb; a crowded circle = a starved limb; empty square =
wasted paper.

⚠ **Rivers are not in v1.** A river's width is an internal tree edge, so
drawing one needs internal-node paper positions; the binding returns **leaf**
locations only. v1 shows limb allocation, not the body segments between limbs.
Say so on the render.

**(b) The tree sheet.** Four orthographic views — Top, Side, Front, Isometric —
of the Metric Tree, matching COrigami's tier 1. Coordinates come from
`leaf_labels[nid]["position"]` for mesh-derived trees; for template and
hand-authored trees a deterministic layout, **stamped "LAYOUT, NOT MEASURED"**
on the image so a guess is never presented as data.

⚠ **`anat_pos` does not exist and must not be created.** The superseded spec
proposed adding `anat_pos: [x, y, z]` as a new optional field *on tree nodes*,
and wrapped it in a display-only side-channel rule to keep it out of the
packer. That field was never built, and it is not needed: the coordinates
already exist as the third key of `leaf_labels`, which is
`{leaf id → {label, basis, position}}` on the `MeshTreeResult`
(`mesh_to_tree.py:197`, written at `:776`). **`leaf_labels` is a separate
object from the node list**, so the data is outside the packing path by
construction rather than by rule, and cannot be confused with the `x`/`y`
packing seeds because it never sits on the same object as them.

**What survives of that constraint:** the renderer reads `leaf_labels` and
never writes coordinates back onto a node dict. The guard is unchanged and is
the one that was always doing the work — attempt-0 output byte-identical after
this phase, by test.

**Constraints, all inherited:** never freeze a byte hash over the PNGs — assert
structure only. Pin Pillow explicitly in `ci.yml`; it is transitive-only today,
the exact hazard `ci.yml` already documents for scikit-learn.

**Why render choice is the highest-leverage decision here:** the survey's
strongest mechanical finding is that *render choice dominates prompt design* —
one study found splat renders made broken meshes look clean and the judge split
~50/50 on obvious defects, while normal-map montages made the same holes
unmistakable. Choosing the packing diagram over the folded base is worth more
than any prompt engineering downstream of it.

### 3.5 Phase 3 — the agent looks

**Channel.** The render is injected as a synthetic user message, the mechanism
`[CP AUDIT]` and `[ANATOMY]` already use (`web/server.py:146,161`). That
channel is simultaneously what the user reads and what the agent's context
holds — surfacing and signalling are **one act**, not a choice.

⚠ **Not as a tool result.** `role:"tool"` messages carry a plain string
(`agent_loop.py:815-817`), so an image cannot ride that path. "The agent calls
a tool to look" is the *blocked* route; the synthetic-message channel works
today.

**Two preconditions, ~1 minute and ~1 day:**
1. Verify the Anthropic OpenAI-compat endpoint accepts `image_url`
   content-parts (`llm_client.py:33-37`). Untested. Blocks everything here.
2. Run the Gate-2 experiment: does the labelled leaf-`position` text table answer
   the recognisability question? If yes, the picture is redundant — stop.

**Loop mechanics.**

| | Rule | Source |
|---|---|---|
| Iterations | cap **3**, enforced in `_TurnBudget`, not the prompt | ⚠ **borrowed, not measured here** — see §3.5.1 |
| Acceptance | keep an edit only if the Phase-1 arithmetic is **strictly better**; else revert to best-so-far | ReLook's hard acceptance rule |
| Regression | **never penalise** a worse revision | penalties caused reward hacking — the agent reflected less to dodge them |
| Authority | the critique is advisory; every edit re-enters the full deterministic pipeline | §3.1 |
| Budget | shares one autonomous-repair budget with `[CP AUDIT]` and `[ANATOMY]`; a fidelity round consumes their dirty flags | else the serve re-arms them (`web/server.py:436-466`) |
| Images | explicit per-turn cap in `_TurnBudget`; one tiled sheet, never a gallery | more images in one context measurably degrades judgement |

#### 3.5.1 The iteration cap is borrowed, and its provenance is thin

The cap of 3 rests on **one study in a different domain**: Sketch2Code
(sketch → webpage, a simulated reviewer inspects each render and gives
feedback) ran a 5-round budget and found "most performance gains occurred
within the first two rounds of interactions, and performance often plateaued or
even deteriorated after three to four rounds." A second cited system converges
on 2–3; it is not independently verified here and is not relied on.

**Nobody has measured the useful round count for tree-edit → recompile**, and
two things make the transfer questionable in *both* directions:

- In Sketch2Code an edit maps predictably onto the render. Here packing is
  **non-monotone** — scaling a tree by 0.9486 fails to pack while 0.96 packs —
  so an edit's effect on the artifact is not smooth. That argues for *fewer*
  useful rounds, but it is reasoning, not measurement.
- Our recompiles are expensive, so the cost side differs entirely.

The nearest thing measured **in this repo** is B5-prime's anti-additivity
result: one shaping op cut whole-pose error 272.49 → 119.14 and *no sequence
beat the single op*. Same direction — edits do not compound here — but on
shaping ops, not tree edits.

**Treated as a bound, not a finding.** A cap is cheap insurance and being wrong
by one round costs little. If Phase 3 ever runs at volume, the round-count
curve is the first thing worth measuring locally, and this section is what it
would replace.

**Measurement.** Run the control **once, as a standalone probe**, the way §2's
falsifications were run — not as a shipped judge.

⚠ **The control defect moved, and §3.3.1 is why.** The first draft used "a limb
re-parented to the wrong junction at equal path length", on the reasoning that
a dict diff misses it. The leaf-to-leaf metric does *not* miss it — a limb at a
different junction sits at a different distance from every leaf not below that
junction, even when its root-to-tip length is unchanged. Phase 1 now catches it
outright, so it can no longer test whether *looking* adds anything.

A valid control must be invisible to Phase 1's arithmetic **and** visible in
the render. §1's theorem says where the remaining ones live: if the shadow is
the tree, then nothing *anatomical* is invisible, and what is left is clause 4
— **paper allocation**, which is packing-space and has no tree-space
signature at all.

- **Clear-gap:** a **per-limb allocation defect** — one flap's circle starved
  or crowded — in a serve whose Phase-1 arithmetic is clean.

  The requirement is precise, and stating it loosely would let the probe grade
  itself: the pair must be **equal on every column the acceptor already has** —
  `shadow_diff` all-zero, and packing `scale` and `hull_coverage` equal within
  run-to-run noise — while differing visibly in *where* the paper went.

  ⚠ **`scale` alone does not qualify a pair, and an earlier draft of this
  revision wrongly assumed it did.** The two-basin result (`quad` at
  `0.717008` vs `0.714406` on the same host by node order alone, PR #70) is a
  candidate *source* of such pairs, but those two serves are already
  distinguishable by a scalar the acceptor reports. A scalar that says "these
  differ" is not the question; the render's claim is that it says **which limb**
  and **whether it matters**, and no scalar in §3.2 is per-limb —
  `hull_coverage` is global (measured: dog 0.664, quad 0.496).

  **Pre-registered, therefore:** search the basin data for a pair meeting the
  equality requirement *before* looking at any render. If none exists, the
  probe reports that and stops — "we could not construct a defect invisible to
  the acceptor" is a publishable result and is itself an argument that Phase 3
  is unnecessary. Do not relax the requirement to manufacture a pair.
- **Null:** two renders of serves that land in the **same** basin — asserted,
  not assumed, by equal packing `scale` and equal leaf positions up to the
  diagram's own symmetry. Must score ~0.5.
  ⚠ The first draft used "two node-order variants of the same tree" as the
  null. The two-basin result makes that unsound: node order is precisely the
  lever that moves the basin, so the proposed null is the proposed clear-gap.
- **Bar fixed before measuring.** Never tune the prompt on the subjects used to
  measure it.

---

## 4. Phasing and stopping rules

**Phase 1 — shadow-tree equality.**
> **STOP IF** the served tree is structurally identical to the requested tree
> on every scorecard subject — no invented flaps, no dropped leaves, and
> `path_drift_max == 0.0`. Then the engine changes nothing and there is nothing
> to report.

Known in advance not to fire: quadruped serves `stage=stub`, `stub_flaps=3`,
fidelity 0.8333 against R=6. Recorded as intent, not as a live gate. The rules
that bite are below.

⚠ **Read this rule with §3.3.4.** "Structurally identical" is the *stop*
condition for building the instrument at all. It is not the fire condition for
the oracle, which is narrower — drift no marker explains. A subject can be
non-identical (a normalize serve, a reconciled pair) and still leave
`[FIDELITY]` correctly silent.

**Phase 2 — renderers.**
> **STOP IF** `leaf_node_locations` does not survive to the serve payload for
> the scorecard subjects. Without packed positions the diagram has no input,
> and reconstructing them means a recompile per view.

**Phase 3 — the agent looks.**
> **STOP IF** the compat endpoint rejects image content-parts (hard block); or
> the leaf-`position` text table already answers the recognisability question
> (picture redundant); or the arithmetic-invisible control fails its
> pre-registered bar; or the base-vs-base null does not sit near 0.5.

**Scope control.** Phases 1 and 2 are one implementation plan — both
deterministic, both cheap. Phase 3 gets a second plan, written only after
Phase 2 reports and both preconditions pass.

---

## 5. One calibration capture, scheduled once

Add `screenshot()` to `SimSession` — the page has already loaded the fold and
run `setFold(100)` before `capture()` reads geometry (`sim_capture.py:76`), so
the base is on screen. Capture `dog` and `quadruped`, headed, commit the images
as evidence, record whether limb placement is legible in 3-D.

This is not a CI step, not a gate, and not on any critical path. It exists so
§2's open item is closed by measurement rather than by argument, once, forever.

---

## 6. Testing

| Test | Asserts |
|---|---|
| `test_shadow_diff` | invented / dropped / contracted / `path_drift` on hand-built trees; all-zero for an untouched tree |
| `test_shadow_diff_survives_rerooting` | ★ **the pin for §3.3.1.** `rehome` on a real fixture ⇒ `path_drift == 0.0` exactly and `dropped == 0`; a parent-pointer diff over the same pair is asserted **non-zero**, so the test fails if anyone re-keys the metric on rooting |
| `test_shadow_diff_contraction_bounded` | `contract_slivers` ⇒ `dropped == 0`, `contracted >= 1`, and `path_drift_max <= contracted × SLIVER_RATIO`; the drift is reported, not tolerated away. ⚠ The bound scales with the *count* — several slivers can contract on one leaf-to-leaf path — and the test asserts the bound, **not** strict positivity: an interior node with no leaf on its root side contributes zero |
| `test_shadow_diff_reconciled_pair` | path reconciliation ⇒ the moved flap's **root-to-tip** reach unchanged (its own contract) while `path_drift` is non-zero against third leaves; both facts asserted, so neither is mistaken for the other |
| `test_shadow_diff_requires_locs` | `invented` is `None`/unmeasured without `locs`, never silently 0 — the stub flap is absent from every Python node list |
| `test_served_tree_plumbed` | ★ **both paths.** `draft_and_compile_full_base` on a tree that needs a rescue leaves a last-serve record whose tree is the RESCUED candidate, not the request — asserted through the **real tool**, not the worker and not a count. Plus the child payload carries `served_tree` |
| `test_read_base_no_recompile` | `read_base` spawns no worker and mutates no session |
| `test_fidelity_oracle_quiet` | report-only; never composes an imperative; stands down with a recorded reason |
| `test_fidelity_suppressions` | each of §3.3.4's five suppressions is reachable and names itself in `reason`; **and** the fake provider is *not* among them |
| `test_fidelity_fires_on_unexplained_drift` | a marker-free mutation fires; the same drift carrying `NORMALIZE_MARKER` / `STUB_MARKER` / a reparent report line does not |
| `test_packing_diagram` | one circle per leaf; engine-made leaves distinct; radius ∝ length; deterministic within a platform; **no byte-hash assertion** |
| `test_tree_sheet` | 4 views at fixed dimensions; N bones → N segments; template renders carry the "LAYOUT, NOT MEASURED" stamp |
| `test_positions_stay_off_the_tree` | the renderer reads `leaf_labels[nid]["position"]`; **no node dict gains a coordinate key**; no `anat_pos` field is introduced anywhere |
| `test_attempt0_unchanged` | **byte-identical** attempt-0 output for all four templates |
| `test_scorecard_columns` | new columns present; existing columns unchanged |
| Regression | full suite from the **MAIN** checkout, `--timeout=420`; expect the documented shape ± re-blessed rows |

`test_shadow_diff_survives_rerooting` is the one row that must not be dropped
for cost. Its two-sided form — new metric zero, old metric non-zero, on the
same input — is what stops the id key being reintroduced by someone who reads
`reparented` as the more natural thing to compute. A one-sided assertion would
pass against a metric that returns zero for everything.

Per memory: bare `make test` never terminates on macOS; check host CPU for
orphaned processes before timing anything; a worktree borrowing main's `.so`
reports 27 baseline failures instead of ~3.

---

## 7. Risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | Phase 1 lands and clause 2d turns out never to fire | ⚠ **This risk's original mitigation is withdrawn** — clause 2d is no longer Phase 3's control defect (§3.5). It stands on the [ANATOMY] precedent instead: a tripwire that fires on nothing today is the honest state, not a defect, and `read_base` surfaces the numbers whether or not the oracle speaks |
| R1b | The opposite — `[FIDELITY]` fires constantly and the agent learns to ignore it | This is the likelier failure, and §3.3.4's unexplained-drift rule exists for it: every deliberate transformation already carries a marker, so a routine rescue is silent by construction |
| R2 | The renderer writes coordinates back onto node dicts and they reach the packer | `leaf_labels` is a separate object, so there is nothing to leak unless someone adds one; `test_positions_stay_off_the_tree` + `test_attempt0_unchanged` |
| R3 | Renders diverge across platforms and a frozen hash goes red | Never hash PNGs; assert structure |
| R4 | Pillow is transitive-only and vanishes on a bump | Pin explicitly, per `ci.yml`'s scikit-learn precedent |
| R5 | The agent chases a hallucinated defect | Strictly-better arithmetic ratchet; cap 3; advisory-only; revert-to-best |
| R6 | Image tokens blow the turn budget | Per-turn image cap; one tiled sheet; the 413 backoff already exists |
| R7 | The compat endpoint rejects images | Precondition, checked first; Phases 1–2 stand alone without it |
| R8 | Edits do not move the base predictably — packing is non-monotone (0.9486 fails, 0.96 packs) | The ratchet is on outcomes, never on the edit's expected effect; every round must move ≥1 edge or it is a deterministic no-op |
| R9 | The packing diagram without rivers misleads | Stamp the limitation on the render; rivers are named future work |
| R10 | A later change re-keys the metric on parent pointers, silently reintroducing the false-positive flood | `test_shadow_diff_survives_rerooting`'s two-sided assertion (§6), plus the §3.3.1 rationale kept **in-module**, not only in this spec — the id key is the more natural thing to reach for, so the reason it is wrong has to live where the next author reads |
| R11 | The suppression set rots as new ladder stages land, and a new stage's drift reads as unexplained | Pin the suppression set against the marker set by test, the idiom `mesh_report._HUB_DEGREE_NOTICE` already uses against the extractor's own constant |
| R12 | No qualifying clear-gap pair exists and Phase 3 has no control | Pre-registered in §3.5: report it and stop. That outcome is evidence *against* Phase 3, which is a result, not a failure of the probe |

---

## 8. Out of scope

- Shaping, and any VLM for it. COrigami's tier 3 is the right home for a visual
  judge, and it is blocked on shaping itself: a falsified pose search, a
  measured vocabulary ceiling (front group −81.6° residual), **anti-additive
  composition** (no sequence beat the best single op), and bases that do not
  fold. A per-fold "is this going the right way" check is the shape the
  anti-additivity result specifically refutes.
- Any change to `cp_audit`, `lint_verdict`, or the acceptance ratchet.
- Rewriting the packer; box-pleating.
- River rendering (needs an internal-node position binding).
- Concept-art generation.

---

## 9. Open questions

1. Does `[FIDELITY]` ever earn a repair budget? Proposed: only after its
   false-fire rate on known-good bases is measured — which §3.3.4 now makes
   cheap, since it runs offline on the fake provider — and never in this spec.
2. Should the packing diagram surface in the frontend as a panel, beside the
   CP view? Proposed: out of scope here, but it is the natural home.
3. Is `read_base()` an MCP tool the agent calls, or a block appended to the
   serve message? Proposed: a tool, so it is testable without an agent turn.
4. Do rivers justify the internal-node binding? Proposed: decide after the
   circles-only diagram has been read in anger.
5. **NEW —** should `path_drift` be reported against the requested span or the
   served one? Proposed: the **requested** span, so the denominator cannot move
   under a rescue and make drift look smaller than it is. Flagged rather than
   buried because it is the kind of normalisation choice that quietly decides a
   verdict, and §1.2 already withdraws one metric for exactly that.
6. **NEW —** does the `contracted` count belong in the scorecard, or only in
   `read_base`? Proposed: `read_base` only for now. It is bookkeeping, and a
   scorecard column invites someone to drive it to zero, which would mean
   disabling a rescue that works.

---

## 10. Outcome — the arc is closed (2026-08-06)

Every question this spec asked has been answered by measurement. Two of the
three phases shipped; the third was cancelled on its own pre-registered
evidence, twice over.

| Phase | Outcome | Where |
|---|---|---|
| 1 — shadow-tree equality | **Shipped**, and completed by PR #78: `scale` reaches the payload and `invented` is measured off the json_id `-1` convention rather than proxied off the rung's stub *budget* | PR #75, PR #78 |
| 2 — the two renderers | **Shipped.** Its STOP IF (`leaf_node_locations` must survive to the serve payload) read as unmet at the time and was met by PR #78 | PR #75, PR #78 |
| 3 — the agent looks | **Cancelled.** Gate-2 returned YES — the leaf-`position` text table already answers the recognisability question, so the picture is redundant — and both §3.5 preconditions failed | PR #75 |
| §5 — 3-D calibration | **Answered: no.** A folded base is not legible in 3-D at any camera angle. star-4 is a featureless triangle face-on and a **single line** edge-on | [evidence](../evidence/2026-08-05-base-3d-calibration/) |
| §3.3.4 — the `[FIDELITY]` oracle | **Shipped and observed firing.** 2 of 7 tight stars reach `jitter`, both fire at drift 0.1476 of span; the other five stand down `no-drift`, zero false fires | [evidence](../evidence/2026-08-05-fidelity-fires/) |

### 10.1 Follow-up 3 resolved: the packing diagram is a human debug render

The open item was *"give the packing diagram a fair trial on real data, or
delete it."* Neither. The trial ran, and it changed the shape of the question.

**The earlier trial was not fair, and now the reason is measured.**
`packing_diagram` took `scale=1.0` as a silent keyword default, and nothing in
the repository ever passed a real one — its only caller was its own test
module. Without the packer's scale the discs come out **2.00× oversize on
star-4 and 1.31× on template-insect**, bracketing the 1.25×–2.1× range of the
radius defect recorded earlier. At 2× the four star-4 discs *cross*, which
reads as "the packer overlapped its circles" — something a circle packing never
does. PR #78 is what made a fair trial possible at all, by emitting `scale`
from the parent serve path where it had read `null` on every serve until then.

**Drawn correctly, the render is provably right.** star-4 — four flaps of
length 1.0 at scale 0.5 — lands as four quarter-discs, one per corner, tangent
at the edge midpoints: Lang's canonical four-corner packing. Nothing in the
test suite asserts this. Looking does, which is also how the radius defect was
found. Same subject whose *folded* render is a single line edge-on, so the pair
is the sharpest available statement of §1's finding 3: anatomy is legible one
step earlier, in paper space.

**And Gate-2 still stands.** The corrected diagram carries information the
shadow-diff table cannot — spatial adjacency, and how much of the square
nothing was allocated to (CLAUDE.md §1.1's coverage concern, visible at a
glance). It still does not look like an insect, and nothing here re-ran the
measurement that said the agent decides better from text.

So the resolution is neither of the two options that were on the table:

> **The packing diagram is a human debugging tool for the packer, not an agent
> tool.** Its value to a human is demonstrated — twice now, for defects no
> assertion caught. Its value to the agent in-loop has never been demonstrated
> at all. It keeps that scope, and gains the entry point it never had.

What that cost: `probe_packing_diagram.py` (serve a committed subject, draw its
packing at the real scale); `server.last_serve_locs()` as the seam it reads,
deliberately **not** on `read_base()` and **not** an `@mcp.tool`, so per-leaf
coordinates stay out of the agent's context; and `scale` re-defaulted to a
`None` sentinel that stamps `UNSCALED_STAMP` on the image, so the wrong picture
can never again be produced silently. Evidence:
[2026-08-06-packing-diagram-verdict](../evidence/2026-08-06-packing-diagram-verdict/).

### 10.2 What this settles in §9

- **Q4 (do rivers justify the internal-node binding?)** — proposed answer was
  "decide after the circles-only diagram has been read in anger." It now has
  been. **No, not yet.** The empty middle is the diagram's most useful signal
  as it stands, and `RIVER_NOTE` already prevents the "no rivers drawn" ⇒ "no
  rivers exist" misreading. Drawing rivers would fill exactly the region that
  currently makes the coverage deficiency visible.
- **Q2 (frontend panel beside the CP view?)** — still open, and now the
  *only* place this render could grow. §10.1 rules out the agent path, not the
  human one, and a panel is a human surface.

### 10.3 Not part of this spec, and not blocking anything

Recorded so they are not rediscovered as surprises:

1. The **recipe path** (`_worker_compile_recipe`) still supplies no `locs` or
   `scale`; `read_base()` correctly falls back to the `rung.stubs` proxy there,
   and `last_serve_locs()` returns `None`.
2. `[FIDELITY]` has **zero repair budget and should keep it** until its
   false-fire rate on known-good bases is measured (§9 Q1). Firing correctly on
   a synthetic tight star is not evidence that an autonomous repair would help.
3. A `make test` precondition comparing the `.so` mtime against the newest
   `.cpp` — PR #78 found main's binary a week stale against its own source,
   meaning PR #75's pre-merge run tested an old compiler.

**The next move is not in this spec.** It is un-parking shaping, whose blockers
(falsified pose search, the shaping vocabulary ceiling, anti-additive
composition, bases that do not fold in the simulator) are all non-visual.
