# Tree-Feasibility Data Pipeline (Tier 2.5, Phase 1)

**Date:** 2026-06-16
**Status:** Design approved, pending spec review
**Scope:** The synthetic-tree **generator + brute-force labeler + dataset format**
that bootstraps training data for the eventual `predict_tree_feasibility`
heuristic "World Model" described in CLAUDE.md §6.

## Goal & Non-Goals

**Goal.** Produce a resumable pipeline that generates synthetic Metric Trees,
brute-force labels each one through the existing deterministic compiler, and
writes a streamable dataset whose class-mix proves the data is worth modeling.

**Non-goals (deferred to later phases).**
- Training the heuristic model (XGBoost / NN).
- The `predict_tree_feasibility(tree_json)` MCP tool.
- Feature *engineering* for the model (we record a few trivial features now, but
  do not optimize the feature set for predictive power).

The deliverable of this phase is **the pipeline + a small validation corpus**,
not a trained model.

## Why This Is Worth Building

The packable region of Metric-Tree space is **knife-edge / non-monotonic** (the
`POLYS_MULTIPLE_IBPS` finding): a tree that fails at one set of edge lengths
often packs a few percent away, and there is no closed-form predictor. That is
precisely the regime where a learned surrogate earns its keep — and also why the
dataset must densely sample the frontier rather than the trivial interior.

## Existing Building Blocks (reused, not rebuilt)

- **`tests/runner.compile_tree(nodes, pairs, timeout)`** — runs one compile in
  its own spawn-safe subprocess and returns
  `("ok", fold_json) | ("err", msg) | ("CRASH", info) | ("HANG", "")`. SIGSEGVs
  and infinite loops become *verdicts*, never harness crashes. This is the
  labeler primitive.
- **`server.draft_and_compile_full_base(nodes, pairs)`** — the live `±10%×12`
  perturb-and-retry path. Used only for the sampled perturb label.
- **`benchmark_templates.py`** — the 4 body-plan templates. Retained as
  *validation fixtures* (see Testing), NOT as the generator's anchor source.

## Components

Four small, single-purpose files in a new `mcp_harness/feasibility/` package.

### 1. `tree_generator.py` — hybrid sampler (procedural archetypes + random)

The anchored half of the corpus is produced by **parameterized archetype
families**, not a fixed template list, so the realistic-but-varied region
between named body plans is densely populated.

- `archetype(rng)` — pick a family and sample its structural parameters:
  - `radial(n_limbs, sym)` → star / insect / many-tentacle.
  - `spine_with_limbs(n_hubs, limbs_per_hub, ...)` → quadruped / centipede /
    humanoid all fall out as parameter settings.
  - `branching(depth, fanout)` → antlers / fractal-ish.
  Structural parameters (limb count, spine segments, per-edge length
  distribution, symmetry) are drawn from sampled ranges. The 4 existing
  templates are specific points inside these families.
- `random_tree(rng)` — unstructured: random node count, random parent
  assignment (parent index < child index by construction), random edge weights,
  random symmetry pairs. Whole-space coverage.
- `generate(n, anchored_frac=0.7, seed)` — deterministic stream of
  `(nodes, pairs)`; `anchored_frac` from `archetype`, the remainder from
  `random_tree`. "Anchored vs random" is thus a clean structured→unstructured
  spectrum, not two hardcoded body-plan paths.

Every emitted tree is structurally valid by construction: root has
`parent_id=None`, each child's parent precedes it, symmetry pairs reference real
leaf nodes.

### 2. `tree_labeler.py` — thin wrapper over `compile_tree`

- `label(nodes, pairs)` → `(attempt0_pack: bool, failure_mode: str)` from a
  single `compile_tree` call. `failure_mode ∈ {pack, no_pack_ibps,
  not_connectable, build_failed, crash, hang}`, parsed from the `(status, msg)`
  return (`POLYS_MULTIPLE_IBPS` → `no_pack_ibps`;
  `NOT_LOCAL_ROOT_CONNECTABLE` → `not_connectable`; "could not build" →
  `build_failed`; `CRASH`/`HANG` map directly). `attempt0_pack = (status ==
  "ok")`.
- `perturb_label(nodes, pairs)` → `bool` via
  `server.draft_and_compile_full_base`. Called **only on the sampled subset**
  (the attempt-0 failures) to measure how often retry rescues a knife-edge
  tree. Not run per-tree (it costs ~12× a single compile).

### 3. `dataset.py` — JSONL writer/reader

One row per tree:

```json
{
  "id": 0,
  "source": "anchored" | "random",
  "nodes": [...], "pairs": [...],
  "features": {"n_nodes": ..., "n_leaves": ..., "max_degree": ...,
               "edge_mean": ..., "edge_max": ..., "edge_min": ...,
               "n_sym_pairs": ...},
  "attempt0_pack": true,
  "failure_mode": "pack",
  "perturb_pack": true | false | null
}
```

`features` are trivial-to-compute topological stats recorded from data we
already hold — free to capture, they make the corpus inspectable immediately
and seed later feature engineering. **JSONL** is chosen for append-friendly,
crash-resumable, streamable writes.

### 4. `build_dataset.py` — CLI orchestrator

`generate → label (parallel) → append JSONL → sampled perturb pass → class-mix
report`.

- **Parallelism:** a `multiprocessing` pool under the **spawn** context fans
  trees out to workers. Because `compile_tree` *already* isolates each compile
  in its own subprocess, a worker death cannot corrupt the run.
- **Resumability:** on start, read existing ids from the JSONL and skip them;
  generation is seed-deterministic, so a re-run continues rather than repeats.
- **Class-mix report** (the generator health check): % pack, per-failure-mode
  counts, anchored-vs-random split, and rescue rate over the sampled perturb
  subset.

## Data Flow

```
build_dataset.py(n, seed)
  └─ tree_generator.generate(n, anchored_frac, seed)      # (nodes, pairs) stream
       └─ pool[spawn] → tree_labeler.label                # 1 compile/tree (isolated)
            └─ dataset.append(row)                         # JSONL
  └─ tree_labeler.perturb_label over sampled failures     # rescue-rate stat
  └─ class-mix report
```

## This Iteration's Run

Validate the pipeline with **~2k trees** and read the class mix. **Healthy** =
a non-trivial pack / no-pack split with frontier cases present across both
`anchored` and `random` sources (not ~99% a single class). If the mix is
degenerate, tune `anchored_frac` and the archetype parameter ranges before
scaling. The pipeline scales unchanged toward the CLAUDE.md §6 six-figure
target in a later phase.

## Testing

- **Generator:** emitted trees are structurally valid (root, parent-precedes-
  child, symmetry pairs reference real leaves); deterministic under a fixed
  seed; `anchored_frac` respected; each archetype family reproduces its
  intended shape (e.g. `radial(6)` yields 6 leaves off one hub).
- **Labeler:** a known-packing template (from `benchmark_templates`) →
  `pack`; a known-overlap / known-fail tree → the expected `no_pack_*` mode;
  every real error string in the vocabulary parses to a taxonomy member.
- **Dataset:** a row round-trips through write→read; resume skips ids already
  present in the JSONL.

## Open Risks

- **Labeler throughput.** A single compile is seconds; even 2k trees × isolated
  subprocess is non-trivial wall-clock. Parallelism mitigates; the six-figure
  target will need either more cores or a faster in-process compile path,
  evaluated when we scale (out of scope here).
- **Archetype coverage vs realism.** Parameter ranges are an initial guess; the
  class-mix report is the feedback loop for tuning them.
