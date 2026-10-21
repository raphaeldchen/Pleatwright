# Gate Recalibration — Cover the Mesh Region

**Date:** 2026-06-24
**Status:** Design approved, pending implementation plan
**Component:** `mcp_harness/feasibility/` (tree_generator, build_dataset, corpus, gate)
**Sub-project:** A of two. B (the runtime data loop) is a separate later spec.

## Problem

The Tier 2.5 feasibility gate is trained on a synthetic corpus of random/archetype
Metric Trees. The mesh→tree path (`auto_mesh_to_metric_tree`) produces trees in a
thin, structured slice of feature space the corpus never populates, so **every real
mesh reads as OOD** (`compile_anyway`). Proven 2026-06-23: all 5 mesh fixtures
(quadruped, humanoid, fish, bird, insect) resolved as `compile_anyway`. For real
meshes the gate is therefore decorative — it never filters (`infeasible` never
fires) and its `p_pack` ranking is uncalibrated.

**Root cause.** The gate's OOD distance uses 7 features: `n_nodes, n_leaves,
max_degree, edge_mean, edge_max, edge_min, n_sym_pairs`. The corpus samples each
edge length *independently* in `[0.12, 0.55]` and never normalizes
(`tree_generator.py`). But `mesh_to_tree.to_metric_tree` **normalizes the longest
edge to `LONGEST_LIMB_TARGET = 0.40`** and scales the rest to anatomical
proportions, with small post-prune node counts. Mesh trees thus occupy a slice
(one edge pinned near 0.40, others proportionally smaller, small sizes) the random
sampler almost never hits.

## Goal

Make mesh-derived trees **in-distribution** so the gate can actually filter/shield
real-mesh inputs. Concretely: after recalibration, the 5 real fixtures must score
`ood == False` and must not be rejected as `infeasible`.

### Non-goals (explicitly out of scope)

- **The runtime data loop** (capture serve-time trees → periodic retrain). That is
  sub-project B, its own brainstorm → spec → plan.
- **Fixing auto_mesh faithfulness / the interim `SEARCH_K=4` + `PRUNE_GRID` cap.**
  That tension is inherent (the gate ranks by *packability*; a compact 2-pair tree
  genuinely packs more easily than a faithful 3-pair one). Recalibration does NOT
  change packability ranking; fixing faithfulness means changing the *selection
  criterion* in `auto_mesh`, a separate concern. Recalibration's payoff is "the
  gate stops being decorative and actually shields," not "the search gets simpler."

## Approach: hybrid (synthetic volume + real validation anchors)

Real meshes alone cannot populate a corpus (5 meshes, even swept into ~100
correlated variants, are too few and too narrow for a RandomForest + k-NN OOD).
Synthetic-only is unverifiable (invented proportions may not match real output).
So: a synthetic `mesh_like` generator family supplies volume, and the 5 real
fixtures are a **held-out validation set** with a hard pass criterion that proves
the synthetic slice generalizes to real extraction output.

## Components

### 1. The `mesh_like` generator family (`tree_generator.py`)

A new generator producing trees in the mesh slice. The OOD gap is mostly
*normalization + small size*, so it reuses small anatomy topologies (spine-with-
limbs / radial) and applies the same post-processing `to_metric_tree` does:

```
mesh_like(rng):
    nodes, pairs = <small spine-with-limbs or radial>   # 4–8 leaves, bilateral pairs
    normalize longest edge -> LONGEST_LIMB_TARGET (0.40); others scale proportionally
    return nodes, pairs
```

Three properties together define the slice:

- **Longest edge pinned to 0.40**, the rest proportionally smaller (vs. the
  corpus's independent `[0.12, 0.55]` draws) — the dominant OOD driver.
- **Node count capped to the mesh range** (~5–10 nodes, 4–8 leaves).
- **Bilateral pairs** present (native to the archetypes).

**Frontier-straddling requirement.** The family MUST produce a *mix* of pack /
no-pack cases (vary leaf count and proportion spread, including the over-crowded
regime — e.g. many limbs near 0.40). If every mesh-like tree packs, the classifier
learns nothing discriminative in the slice and the gate would rubber-stamp
`feasible` for all mesh inputs — useless for shielding.

It is mixed into the corpus at a guaranteed fraction via a `mesh_like_frac`
parameter on `generate`, alongside the existing anchored/random split, so the slice
has enough rows for k-NN neighbors and classifier signal.

### 2. Validation harness (the success gate)

- **Stored mesh-tree fixtures.** Generate the 5 confirmed trees once (constants:
  quadruped 96/0.55, humanoid 96/0.20, fish 64/0.40, bird 96/0.25, insect 96/0.55)
  and store as a JSON fixture `name → {nodes, pairs}`, so the validation test loads
  instantly and deterministically (no skeletonization in-test).
- **Pass criterion (headline metric):** with the gate trained from the *updated*
  corpus, `gate.predict` on each stored tree must give:
  - **`ood == False`** for every fixture — they are now in-distribution (the exact
    property that was false before). This is the measure recalibration worked.
  - **`verdict != "infeasible"`** — firm requirement (never reject a tree that
    genuinely packs). "All 5 `feasible`" is the strong-success signal, checked and
    tuned toward via the block threshold, not necessarily a hard-fail initially.
- **Before/after baseline.** Record each fixture's `ood_score` under old vs. new
  gate; assert the new scores cross below `ood_threshold`; document the deltas.
- **Held-out, not trained on.** The fixtures are validation only — never training
  data — so passing genuinely demonstrates generalization (not circularity).

### 3. Pipeline wiring (`build_dataset.py`, corpus, gate)

- **Append, don't regenerate.** `build_dataset.py` generates a `mesh_like` batch
  and **appends** it to `corpus_wide.jsonl` (ids offset past the current max),
  preserving existing labeled data. Each tree is labeled normally (real compile →
  pack/no-pack), so the slice carries true labels. Target ~a few hundred mesh-like
  rows — enough for signal without dwarfing the corpus.
- **Updated committed artifacts.** The updated `corpus_wide.jsonl` is committed (it
  is the on-demand training source via `_default_gate`). `gate.joblib` stays
  gitignored and is retrained automatically. `train_model.fit` returns
  `val_recall_feasible` / `compile_save_rate` / thresholds; record before/after and
  assert **no regression** on the existing distribution.

## Testing

- **Fast unit** — `mesh_like` output valid: longest edge `== 0.40`, 4–8 leaves,
  structurally valid (root `parent_id=None`; each child id > parent id), pairs
  reference distinct leaves; and across seeds the family yields *both* pack and
  no-pack cases (frontier-straddling).
- **Fast unit** — `generate(..., mesh_like_frac=x)` emits the expected fraction of
  mesh-like trees.
- **Validation/integration (headline)** — gate trained from the updated corpus
  classifies all 5 stored fixtures `ood == False` and `verdict != "infeasible"`,
  plus a regression check that `val_recall_feasible` did not drop versus the
  pre-mesh-like corpus.

## Sequencing note

The validation test passes only *after* the corpus is rebuilt with mesh-like rows,
so build-and-commit-corpus is part of this deliverable. The plan orders it:
add `mesh_like` → unit-test it → append batch + commit corpus → confirm the
validation test goes green.
