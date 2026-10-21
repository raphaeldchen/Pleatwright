# Pleatwright: retire TreeMaker and the Lang box-pleat compiler from main

**Owner decision (2026-10-07).** Main keeps only the text → image → mesh →
tree stages and the new tree → folded-model compiler. TreeMaker, the Lang
Ch. 13 `box_pleat/` compiler, and everything that exists only to serve them
move to an archive branch. The new compiler is renamed **Pleatwright**
(package `mcp_harness/pleatwright/`, formerly `corigami/`). It is a
reimplementation of COrigami (arXiv:2606.26299) with documented deviations,
so it gets its own name; the paper stays cited as its basis.

## Why

* **Pleatwright supersedes both compilers on the owner's trees.** On the 51
  "Bases in Triplicate III" trees it folds 51/51, while `box_pleat` emits 7/51
  (31 hit a 300 s cap; `docs/superpowers/evidence/2026-10-06-corigami-pipeline/box_pleat_baseline.jsonl`).
  TreeMaker creases only the convex hull of the leaves (CLAUDE.md §1.1(1)),
  whereas a box-pleated base creases the whole square.
* **The retired code dominates cost.** `test_box_pleat_e2e.py` alone is 73%
  of the CI test job (196 of 267 min on run 37407584963), spent confirming
  two strict xfails. Recent CI runs take 4.5–5.9 h against GitHub's 6 h job
  limit.

## Decisions (each made by the owner in the design discussion)

| question | decision |
|---|---|
| main's front door | a pipeline CLI now; an app on top of Pleatwright later, as its own project |
| tree review | two commands plus an interactive review: `author`, `fold`, and `run` chaining them |
| structure | survivors stay in `mcp_harness/`; the certification slice moves into `pleatwright/certify/` |
| docs | `docs/` is kept as history |
| name | Pleatwright |

## What stays on main

| stage | modules |
|---|---|
| text → concept image → mesh | `mesh_acquire.py` (HF provider: FLUX image Space → Hunyuan3D-2 mesh Space; `fake` provider for offline use) |
| mesh → VLM tree + human review | `gated_pipeline.py`, `tree_authoring.py`, `tree_contract.py`, `vlm_render.py`, `pair_fusion.py`, `llm_client.py`, `env_config.py` |
| tree → finished model | `pleatwright/` (stick, pack, base, solve, narrow, shape, orchestrate, fold, cp, render, pipeline) |
| certification | `pleatwright/certify/`: `layers.py` (`constraint_graph` and what it needs), `sat_order.py`, `layer_certify.py`, `layer_order.py`, `flat_fold.py`, `cp_audit.py` |
| front door | `pleatwright/__main__.py` |
| data | `fixtures/full17_v3_trees/`, `fixtures/full17_v3_sticks/`, the mesh/render fixtures the kept tests read, `docs/` |

External dependencies of the survivors, read from their imports on
2026-10-07: numpy (Pleatwright), matplotlib (render), python-sat (certify),
openai (`orchestrate`, `llm_client`), trimesh + Pillow (`vlm_render`),
gradio_client (`mesh_acquire` HF provider), python-dotenv (`env_config`).
They are re-read from the final tree when `requirements.txt` is trimmed.

## What moves to `archive/treemaker-box-pleat`

* The TreeMaker engine: `treemaker/`, `TreemakerWrapper.cpp`, `CMakeLists.txt`,
  `build.sh`, `treemaker_documentation.md`.
* `server.py` (MCP server, 24 tools), `agent_loop.py`, and `linter_server.py`
  with the Oriedita linter (`OrieditaValidator.java`, `build_linter.sh`).
* `box_pleat/`, except the slice moved to `certify/`.
* TreeMaker serve-path modules: rescue ladder, `pack_repair`, `error_recipes`,
  order/root rank, M/V repair/symmetrize, `cp_mirror`, square completion,
  free paper/flap fill, coverage, `fold_meta`/`fold_registry`, lint verdict.
* The feasibility gate (`feasibility/`), which predicts *TreeMaker* packability.
* TreeMaker-base shaping and pose (`shaping*.py`, `pose_*.py`).
* Base-eval, judge and scorecard tooling (`base_eval`, `base_verdict`,
  `base_report` and its instruments, `vlm_judge`, `judge_*`, `benchmark_*`,
  `eval_vlm_pipeline`, `mesh_report`, `anatomy_*`, and the fixture-regenerating
  probes kept in fa99c7d0).
* `mesh_to_tree.py`, the pre-VLM skeleton extractor. Its only remaining use on
  the authoring path is the pack step removed below.
* `web/` (FastAPI backend and React frontend) and `docker/`.
* Every test, fixture and golden whose subject is one of the above.

The exact delete set is computed, not hand-listed: everything outside the
import closure of {`pleatwright.__main__`, the stays-list modules, their kept
tests}. The same reference checks as fa99c7d0 apply (string paths, subprocess
invocations, CI and config files).

The archive branch is cut from PR #197's head, which holds everything
including Pleatwright as of 2026-10-06. One commit on it adds `ARCHIVED.md`:
what lives there, why it was retired (this spec), and how to build and run it
(`make build`, `web/README.md`).

## Changes to the kept code

### `gated_pipeline.py`: drop the packing step
* Delete `pack()`, `_default_pack_fn`, the `pack_repair` turn, and every
  `rescue_ladder` / `error_recipes` / `mesh_to_tree` reference.
* `state` loses `packing` and `fold`. `summarise()` loses its packing
  paragraph and `_what_changed`. The fused-limb disclosure (`pair_fusion`)
  stays word for word.
* The tree sheet draws the AUTHORED tree; there is no served tree any more.
  `_served_tuples` becomes a plain authored-tree adapter, keeping its sorted
  order (the `KeyError: 'neck'` guard in its docstring).
* The authoring prompt (`tree_authoring.py`), the revision loop,
  `MAX_REVISIONS`, and the refusal to approve a failed state are unchanged.
* `approve` returns `status="approved"` with the tree and no compile.

### `tree_contract.py`
Drop `_window()` and the leaf-count warning it feeds (TreeMaker's measured
packable range), and the root-has-≥4-children warning (a TreeMaker packing
measurement). All structural errors stay.

### `mesh_acquire.py`
Drop the module-level `import mesh_to_tree`, which only the `__main__` demo
uses. `__main__` keeps `--backfill`; generation moves to the Pleatwright CLI.

### `pleatwright/certify/`
`git mv` the five modules plus `cp_audit.py` and fix their imports. In
`layers.py`, keep `constraint_graph` and its helpers and delete `piece_keys`,
the only user of `emit` and `assign._unit_pieces`. `pleatwright.solve` imports
from `pleatwright.certify`.

## The CLI: `python -m pleatwright`

```
python -m pleatwright author "a dog" --out DIR [--open]
python -m pleatwright fold DIR/tree.json --out DIR
python -m pleatwright run "a dog" --out DIR [--open]
```

`author`:
1. `mesh_acquire.acquire_mesh(prompt)`. Copy the mesh and, if the provider
   saved one, the concept image into `DIR/author/`.
2. `gated_pipeline.start(glb, client=llm_client, out_dir=DIR/author)`.
3. Loop while `status == "awaiting_review"`. Print the summary and the paths
   of `mesh_views.png` and `tree_roundN.png` (`--open` opens them). Read one
   line: `a` approves, `q` quits (exit 1, state saved), and anything else is
   revision feedback for `gated_pipeline.resume(state, "revise", feedback)`.
   A failed round prints its note and offers revise or quit.
4. On approval write `DIR/tree.json` in the fixture schema (`roll`,
   `subject`, `subject_guess`, `nodes[{name,parent,length,direction}]`,
   `pairs`, `readings`, `source`) and `DIR/author/state.json`.

`fold` calls `pleatwright.pipeline.run` on a tree file and writes
`DIR/<Subject>_<grid>/{packing_cp.svg, solving_cp.svg, shaping_cp.svg, overview.png}`.
`pipeline.run` currently takes a roll name; it gains a path form, and the
roll-name form stays for the fixtures.

`run` is `author` followed by `fold`.

Errors: a mesh-provider failure exits 2 with the provider's message. A failed
authoring round is recoverable in the loop. `fold` reports any exception with
the stage that raised it. The packing ladder ends at doubled lengths, so
"does not pack" is not an expected outcome.

## Renaming

* `mcp_harness/corigami/` → `mcp_harness/pleatwright/`;
  `tests/test_corigami_pipeline.py` → `tests/test_pleatwright.py`.
* Code docstrings that cite the paper keep "COrigami" as a citation ("§3.3 of
  COrigami"). Docstrings and messages that name *our* pipeline say
  Pleatwright.
* `docs/superpowers/specs/2026-10-06-corigami-tree-to-model-pipeline.md` and
  the 10-06 evidence README get a header note ("this pipeline is now
  Pleatwright, `mcp_harness/pleatwright/`"), and their run commands are
  updated. Their bodies stay as written.

## CI, requirements, CLAUDE.md

* `ci.yml`: one job. Set up Python 3.14, install the pinned survivors'
  dependencies, run `pytest tests/`. Removed: clang, pybind11, the JDK and
  Oriedita cache, the TreeMaker build, mcp, scikit-learn/joblib/skeletor/
  scikit-image, and the frontend job. `docker/` is archived.
* `Makefile`: `test` runs pytest. `build`, `bless`, `test-slow` and
  `test-all` go if nothing they reference survives.
* `requirements.txt`: the survivors' dependencies only.
* `CLAUDE.md`: rewritten around the pipeline above. Keep §0 (research prior
  art first) and §1.1's one-uncut-square invariant. State that a Pleatwright
  base tiles the whole square, with its basis: `base.build` raises
  `tiling incomplete` if any cell of the N×N grid is left uncovered
  (`pleatwright/base.py`, formerly `corigami/base.py:107`), so TreeMaker's
  leaf-hull coverage ceiling (§1.1(1)) does not apply. Replace the TreeMaker/Oriedita/Simulator
  architecture (§1–§6) with this pipeline and a pointer to the archive branch
  for the TreeMaker-era measurements. `AGENTS.md` is updated to match.

## Prior art (CLAUDE.md §0)

| source | used for |
|---|---|
| COrigami (arXiv:2606.26299) and its released samples | Pleatwright's stages and output format (unchanged by this work) |
| this repo's measured baseline (`box_pleat_baseline.jsonl`) and CI logs | the evidence that the retired compilers can go and what they cost |
| fa99c7d0's cleanup method | the import-closure delete set and its reference checks |
| the archive-branch convention | keeping retired code reachable without carrying it on main; rejected alternative: a `legacy/` directory, which keeps the cost on main |

## Verification

1. **Static.** Every kept module imports. No kept file imports or references
   a deleted path. `pytest --collect-only` collects with no errors.
2. **Tests.**
   * `test_pleatwright.py`.
   * The certification tests that move with the slice (`test_sat_order`,
     `test_layer_certify`, `test_layer_order`, `test_flat_fold`,
     `test_cp_audit`, renamed from their `box_pleat`/top-level names). Seven
     of them are integration tests of the old compiler: they build inputs
     with `compile_tree` or `square_complete` and assert numbers measured on
     that output. The `constraints_for` ≡ `layer_order` entry-point check is
     ported onto the Pleatwright-solved CP of artifact tree `starfish_1`. The
     other six are deleted with the compiler.
   * `test_mesh_acquire`, `test_tree_authoring`, `test_tree_contract`,
     `test_pair_fusion`, `test_llm_client`, and `test_gated_pipeline`
     rewritten without the pack step (fake VLM client, offline).
   * New `test_cli.py`: `run` with `MESH_PROVIDER=fake` and a fake VLM
     client, one revision then approve. It must write `tree.json` and a
     four-file model folder.
3. **The 51 artifact trees.** `python -m pleatwright fold` on each fixture
   tree. Every SVG must be byte-identical to
   `~/Desktop/origami_samples_artifact_trees`. Overview PNGs must be
   identical too, since no output string contains the old name.
4. **CI** finishes in minutes, and green.
5. **Live end-to-end** (`run "a dog"` with the HF provider and the real VLM)
   is BLOCKED: the `.env` Anthropic key returns 401. It is the first check to
   run once the key is replaced. No part of this design depends on it.

## Out of scope

* A web app or viewer for Pleatwright: a later project.
* Renaming `mcp_harness/`. It no longer hosts MCP, but renaming it now
  changes every path in CI, fixtures, docs and memory for no functional gain.
* Changes to Pleatwright's algorithms. Its outputs must stay byte-identical.
