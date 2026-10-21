# Where the limbs go: a diagnostic of `mesh_to_tree` on three live subjects

**Measured 2026-08-16** (read-only; nothing in the repo was modified).
**Scope:** extraction only -- `mesh_to_tree.py` and below. No compile, no serve path.
**Subjects:** the three cached live meshes under `mcp_harness/generated_meshes/<sha>/mesh.glb`
plus the five committed fixtures as controls.

> **This note reports what is broken and where. It deliberately proposes NO repair** --
> CLAUDE.md section 0 requires a prior-art survey before any repair plan.

> ⚠ **Provenance:** produced by an 18-agent read-only workflow. The working scripts lived in
> a session scratchpad that has since been cleaned; the numbers below were transcribed from
> the run before it was lost. **Every claim here is reproducible from the meshes, but the
> scripts are not on disk** -- re-derive rather than assume if a number is load-bearing.

## 1. One-paragraph answer

It is BOTH mesh and extractor, and **the split is completely different per subject**, which is
why a single "fix the extractor" or "fix the meshes" framing will be wrong for two of three.
**Water bear:** ~100% upstream -- the text-to-3D provider returned **a literal bear** (barrel
body, snout, two ears, four stubby legs, tail), so "8 legs + head" is unreachable at any
extractor setting; the extractor's own contribution is a *serve-selection* defect.
**Octopus:** ~75% extractor -- the mesh genuinely contains all eight arms and 7 of 8 are
recoverable *from this same mesh* at `voxel_res` 16-32, but the shipped grid sits entirely
inside the regime where the voxel weld has already failed. **Lizard:** ~50/50, and the two
halves fail for OPPOSITE reasons -- fore legs are detached shells the extractor discards,
hind legs are fused into the belly and never produce a skeleton branch at all.

## 2. The fate table (at the configuration actually served)

| subject | served cfg | raw comps | post-weld `:245` | skeleton comps | discarded at `:272` | served leaves | actually in the mesh |
|---|---|---|---|---|---|---|---|
| water bear | v128/p0.55 | 7 | **1** | 1 (185 nodes) | **0** | 8 | head, 4 paws, 2 ears, tail -- **not 8 legs** |
| lizard | v96/p0.20 | 8 | **5** | 5 (151 nodes) | 4 comps, **10 of 19 leaves** | 5 | head, tail, 4 legs |
| octopus | v96/p0.40 | 17 | **14** | 14 (579 nodes) | 13 comps, **54 of 94 leaves** | 4 | mantle + 8 arms |
| **5 fixtures** | -- | 576/274/3/29/138 | **1 every time** | 1 | **0 everywhere** | -- | -- |

**The control row is the whole argument that this is not merely "bad meshes."** The fixtures
start with FAR more raw fragments (quadruped **576**) and weld to one component every time.
**Fragment count does not predict the failure; the geometric GAP between sub-bodies does.**

Served-config firmness: octopus v96/p0.40 and lizard v96/p0.20 are **byte-exact** matches to
the cards. **Water bear v128/p0.55 is INFERRED, not byte-matched.**

## 3. Mechanisms, ranked

### #1 `mesh_to_tree.py:272` -- the largest-skeleton-component keep
```python
comp = max(nx.connected_components(g), key=len)
```
Fires whenever the skeleton is disconnected: **6 of 9 live configs, 0 of 15 fixture configs.**
The discards are limbs, not dust -- the lizard's four sit at ground level under the torso.
Counterfactual (stitch instead of discard): octopus v96/p0.20 goes 15 -> **9 leaves, 7 from 7
distinct discarded components**; lizard v64/p0.20 goes 5 -> **7**.

### #2 `mesh_to_tree.py:245` -- the voxel weld that does not weld (the CAUSE of #1)
The docstring's claim that voxel-remeshing *"fuses everything into one closed manifold"* is
**false for 2 of 3 live meshes**. `fill()` -> `binary_fill_holes` fills interior cavities and
**cannot bridge disjoint bodies**; the only welding force is the pitch.
**COARSER WELDS BETTER, opposite to the docstring's advice** ("finer preserves the spine"):

| voxel | arm fragments fused into the body (of 15) |
|---|---|
| 16 | **14** |
| 24 | **14** |
| 32 | 11 |
| 64 | 6 |
| **96 (shipped default)** | **1** |
| 128 | 1 |
| 256 | **0** |

**The entire shipped `VOXEL_GRID = [96, 64, 128]` sits in the failed regime for the octopus.**

### #3 `mesh_to_tree.py:313` -- the prune loop, and it RATCHETS
`longest` is recomputed every round and **rises**, because `_contract_degree2` welds the chain
left by a pruned twig into one longer edge -- so the absolute cutoff grows and eats branches
that survived the previous round. Water bear at the served config: cutoff 30.04 prunes **24 of
29** skeleton leaves in round 0, 2 more in round 1. **Nowhere is any of this recorded.**

⚠ **#1 and #3 are SERIALLY REDUNDANT at the shipped prune values.** Keeping every component and
re-running `simplify_to_tree` at v96/p0.40 yields **4 leaves, byte-identical**. A repair naming
only one of them does nothing.

### #4 The search-control gates -- they lose no limbs, they discard better candidates
| site | measured |
|---|---|
| `:1621` early return on `fid >= 1.0 and stage == "none"` | **Decisive for the octopus.** Scores fidelity 1.000 against a self-derived R=4 and returns inside the FIRST voxel -- **voxel 64 is never built**, where p0.40/p0.45 both yield 9 leaves. |
| `:1317` `if held is not None and not admit_wide_when_served()` | **Decisive for the water bear.** 13 admitted candidates abandoned uncompiled, incl. **v64/p0.45 -> 9 leaves, 4 pairs, 7 of 8 anatomical slots, ZERO spurious**. No trace row is written for a candidate refused here. |
| `:1496` admission window 9..12 | water bear drops 9 configs (13-20 leaves), octopus 7 (14-30) -- **precisely the candidates carrying the most anatomy**. |
| `:1805` `reference_feature_count` | **THE CLOSED LOOP.** R is voted over the ALREADY-MUTILATED skeleton: octopus reads **R=4 at v96**, 9 at v64, 30 at v128. |
| `:1822` `r_eff = min(max(R, 4), 8)` | water bear R=11 -> `r_eff=8`, so an 8-leaf serve reads fidelity **exactly 1.000** while its skeleton carried 29 leaves. |
| `_phase4_admitted_serve:1272` | *"AN ADMITTED CANDIDATE MAY NEVER DISPLACE A HELD SERVE"*, justified as **"the absence of a trustworthy yardstick."** So `IDE_ADMIT_WIDE=1` buys DATA only -- it does not free the better tree. |

**The loop:** R is derived from what extraction kept -> throwing away half the animal RAISES the
score -> the search stops early -> and the same untrustworthy R is the stated reason a better
candidate may never be promoted.

## 4. REFUTED -- do not re-chase these

1. **`sk.pre.fix_mesh(remove_disconnected=5)` drops limbs -- REFUTED, universally.** It drops
   vertex components of **<= 5 vertices**. **0 vertices dropped in all 9 live + 15 fixture
   configs.** Inert. Dead. Stop looking at it.
2. **The voxel weld merges adjacent arms -- REFUTED.** At voxel 16 the weld fuses 14 of 15
   fragments AND the skeleton still resolves 7 of 8 distinct arms. Attachment and separability
   coexist at 16-32.
3. **Wavefront ring contraction welds across limbs -- REFUTED.** 0 skeleton nodes span more
   than one mesh component, all 9 configs.
4. **`nx.minimum_spanning_tree` at `:301` loses limbs -- reported REFUTED but the supporting
   detail is THIN. Re-derive before relying on it.**
5. **"A long tail raises the cutoff and eats the legs" -- CONFIRMED as a mechanism, REFUTED as
   the lizard's cause.** At the served p0.20 the cutoff is 8.17 and kills six twigs of 2.5-7.6
   units; the legs were already deleted at `:272`. The prompt said "long tail" and the story
   was too neat to be true.
6. **Fixing `:272` alone rescues the octopus -- REFUTED** (see the serial-sufficiency note).
7. **`:1481`'s bare `except` eats label payloads -- REFUTED (dormant), 0 firings in 72/72.**
8. **`pair_reconcile.py:370` invents or loses leaves -- REFUTED, 0 lost / 0 invented, 72/72.**
9. **Fragment count predicts the failure -- REFUTED** (quadruped 576 -> 1; octopus 17 -> 14).

## 5. Is it recoverable by tuning?

| subject | tuning alone? | best inside the shipped grid | best measured anywhere |
|---|---|---|---|
| water bear | **YES -- no tuning needed, only serve SELECTION** | **v64/p0.45: 9 leaves, 7/8 slots, 0 spurious** (already computed every run, refused at `:1317`) | v256/p0.30: 8/8 slots at 45 leaves (unpackable) |
| octopus | **NO** | v64/p0.40: 9 leaves, **4 of 8 arms** -- and `:1621` guarantees voxel 64 is never built | v24/p0.30: 9 leaves, ~6.5/8 arms (**voxel outside the grid**) |
| lizard | **NO -- hard 3-of-4 ceiling before tuning is asked** | v96/p0.20 = what was served: 5 leaves, **1 real leg counted twice** | v192/p0.10: 6 leaves, 3/4 legs (**both coords outside the grid**) |

**Octopus ceiling across all 72 cells: 7 of 8 arms, never 8**, and every 7-arm cell carries
10-34 leaves. **BAND MISMATCH: the resolutions that attach the arms (16-32) are outside
`VOXEL_GRID`; the leaf counts that carry the anatomy (13-26) are outside `MIN..MAX_LEAVES=4..8`
and `ADMIT_MAX_LEAVES=12`. The servable band and the anatomy-surviving band do not overlap.**

**The lizard's one declared pair is FABRICATED** -- served `pairs=[[4,6]]` labelled "paired fore
limb", but both members sit inside the SAME 292-vertex left-fore shell. One leg counted twice.
No voxel resolution ever holds all four legs: RF is a detached shell wanting COARSE voxels, LH
is body-fused and resolves only at 192. **Opposite voxel dependence.**

## 6. NOT established

* **No compile was run. No cell named here is verified packable or servable.** Largest gap.
* Water bear's served config is inferred, not byte-matched.
* **Untested: whether coarse voxels that fix the octopus BREAK the five fixtures.** They were
  measured only at 96/64/128.
* Untested: `IDE_ADMIT_WIDE=1` end to end (needs a compile).
* Untested: whether the provider's bear is recoverable by prompt, seed, or provider.
* Anatomical ground truth is heuristic (bbox clustering, eyeballed slot boxes) except the
  lizard's, which comes from actual detached sub-body geometry.
* `hull_coverage`, packing, symmetry and scorecard effects were **not measured at all**.

## 7. Axis A -- what exists now, and exactly how far to trust it

**The judge runs** (PR #130): `base_report.py --judge` scores the TREE against the PROMPT
using world knowledge. It is ADVISORY -- `authority` is the literal string "advisory" and a
test asserts the acceptance decision is byte-identical whether it ran, did not run, or failed.

Measured on these same three subjects: octopus **0.197**, lizard **0.427**, water bear
**0.550** (and the quadruped fixture 0.450).

### ⚠ Read the error bars before quoting any of those numbers

`_agreement` is defined as `1 - 2*pstdev` (`vlm_judge.py:654-668`), so it **inverts**: every
recorded agreement carries the sample spread that produced it.

| agreement | population sd | SEM (N=4) | 95% CI on `score` |
|---|---|---|---|
| 0.93 | 0.0350 | 0.0202 | **+/-0.064** |
| 0.87 | 0.0650 | 0.0375 | **+/-0.119** |

**Least significant difference between two scores: 0.091 (best case) to 0.169 (worst).**
Against the four measured subjects, **only `octopus` separates from anything.**
water bear vs lizard (0.123), water bear vs quadruped (0.100) and quadruped vs lizard
(0.023) are ALL inside the noise.

⚠ **An earlier revision of this note said "correct severity order". That was an over-reading
and is retracted.** The ordering among lizard / quadruped / water bear is not supported at
N=4. Sharpest statement of the problem: **a judge that always returned 0.4 would be
indistinguishable from three of the four readings.**

**USE 0.169 AS THE BAR.** Any claim that a change "moved the judge" must clear it. Scores are
emitted to 6 decimals against an interval of +/-0.06 to +/-0.12 -- roughly two orders of
magnitude of false precision.

### What IS established, and what is not

* **ESTABLISHED: the free-text `reasons` are specific and verifiable.** It named the missing
  hind-limb pair, the arm shortfall and the absent mantle, and independently rediscovered the
  over-long arm and the same-side orphan pair that the instrumentation above found. A
  constant-scorer cannot produce those. **Read the reasons, not just the score.**
* **NOT ESTABLISHED: that it recognises a GOOD tree.** Every tree ever shown to it was broken
  and every score landed below 0.6. "It catches bad work" is proven; "it scores good work
  high" has **never been tested**. Until it is, a low score is not interpretable.
* **NOT ESTABLISHED: that it reads the subject at all.** Holding a tree fixed and changing
  only `subject.name` has never been run. If the score does not collapse when a quadruped
  tree is judged as "an octopus", the judge is not using world knowledge.
* **BLIND SPOT, measured: mesh substitution.** It scored the water bear HIGHEST, and that mesh
  is a literal bear -- an 8-leaf tree in four pairs genuinely IS tardigrade-shaped. Axis A
  ranks tree-level damage and cannot see that the source mesh was the wrong animal.

### Run this BEFORE relying on it -- ~30 minutes, ~$1

1. **POSITIVE CONTROL (24 calls, $0.21).** `body_plans.py` already holds four hand-authored,
   anatomically CORRECT, measured-to-pack trees (quadruped, bird with legs, humanoid with arms
   distinguished from legs, insect). Wrap each as a blob and judge it. Pre-register the bar:
   **median >= 0.80, and every good tree beating every broken one by more than 0.169.**
   **If this fails, axis A is not usable as a metric and this session must not steer by it.**
2. **SUBJECT-SWAP MATRIX (80 calls, $0.70).** Judge each of the 5 committed blobs under each
   of the 5 subject names. The diagonal is the anchor; the 20 off-diagonal cells are trees
   judged against the wrong animal. A score that does not collapse off-diagonal means the
   judge is not reading the subject.

### Building a benchmark: the vacuity trap, and the free screen

The judge's visible surface is **exactly NINE blob fields**: `subject.name`, `subject.prompt`,
`serve.served_tree`, `serve.leaf_labels[*].label`, `serve.leaf_labels[*].basis`, `serve.pairs`,
`serve.stub_flaps`, `serve.served_leaves`, `serve.served_fidelity`.

**Everything else is dark.** Mutating an invisible field renders a BYTE-IDENTICAL prompt and
returns the same score -- a benchmark row that looks like a measurement and is a tautology.
Confirmed invisible: `serve.leaf_labels[*].position` (the 3-D coordinates -- the most
anatomical-looking field in the blob), `serve.locs`, `serve.requested_tree`, all of
`metrics.*`, `renders.packing`, `lint_class`, `hull_coverage`, `design_scale`, `shadow_diff`,
and **`serve.stubs`** (invisible whenever `stub_flaps` is set, which is every committed blob).

**THE SCREEN IS FREE: require every mutant to move `prompt_digest`, and assert it in the
battery's own test.** Vacuity is then detected mechanically, with zero API calls. This repo has
shipped four vacuous metrics; this is the first check available before the measurement.

Also live: `edge_length` renders RAW while `path_length_from_root` rounds to 6 dp, so
12th-decimal float drift IS visible to the judge -- the committed quadruped already ships
`0.33206800000000003`. Blobs regenerated on another platform can move scores for no
anatomical reason.

### ⚠ A contradiction to settle IN WRITING before the first call

`fixtures/anatomy_reference.json` pins bird at `reference_count: 4` / `expected_pairs: 2`, and
the committed bird blob serves exactly 4 leaves at `served_fidelity 1.0` -- perfect by that
label. The recorded judge reply says *"Four appendages where a bird needs six"* and marks it
down for missing legs. **The repo's own ground truth and the judge disagree on the cleanest
subject in the corpus, and the judge is the one a biologist would side with.** Score axis A
against `anatomy_reference.json` and it is recorded as WRONG for its most obviously correct
criticism. Pick a side and write it down.

### ⚠ NEVER TUNE AGAINST IT

Axis A was validated on the same three subjects this work will touch. Optimising against it
there stops it being an independent check -- and note precisely what that would be:
**a system improving its score against a measure derived from its own output, which is the
closed loop (section 3, #4) this work exists to repair.** Rebuilding that pattern one level up
while fixing it below is an easy mistake, because every step feels like progress.

Controls: hold subjects out and validate on prompts the judge has not seen; keep the cheap
deterministic instruments (leaf counts, component fate, pair checks) in the inner loop and put
the judge at the END, on the two or three candidates that survive. At 4 billed calls per
subject it is not an iteration loop anyway.
