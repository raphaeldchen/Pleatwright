# Pleatwright

Pleatwright turns a text prompt into a folded origami model: text → concept
image → mesh → VLM-authored stick-figure tree (a human approves it) →
box-pleated base → solved crease pattern → shaped crease pattern → folded model.
It is based on COrigami (arXiv:2606.26299), with the deviations recorded in
`docs/superpowers/specs/2026-10-06-corigami-tree-to-model-pipeline.md`. The
decision that cut `main` down to this one pipeline is
`docs/superpowers/specs/2026-10-07-pleatwright-retire-treemaker-design.md`.

## 0. Development Process Requirement: Research Prior Art Before Planning

**Before developing any plan (new feature, subsystem, algorithm, or repair strategy), researching existing and adjacent work is REQUIRED — not optional.** Survey academic literature, open-source tools, and analogous systems in neighboring domains (computational origami, fabrication pipelines, text-to-CAD/EDA agent loops), and take every opportunity to draw from existing work rather than inventing from scratch. Plans must cite what was found and what was adapted or consciously rejected (with the reason).

This rule exists because it has already paid for itself twice on this project: (1) the vendored TreeMaker source was found to already contain Lang's own fixes (stub triangulation, edge optimization, placement hooks) for failures we had been attacking with home-grown jitter, and (2) adjacent-domain agent loops (RTLFixer, CADSmith, ICLR self-repair studies) had published, measured answers to reliability questions we were about to re-derive blind. See `docs/superpowers/plans/2026-07-25-perfect-base-slices.md` (its "Prior-art adaptations" table is the model for what a plan should include) and the landscape survey in project memory.

## 1. The physical invariant

**Every model this pipeline designs folds from ONE UNCUT SQUARE SHEET.** No
cutting, no gluing, no multi-sheet assembly, no rectangles unless a user
explicitly asks. The whole square is in play, and the folder receives the whole
square.

A Pleatwright base tiles the whole square: `pleatwright/base.py` `build()`
raises `tiling incomplete` if any cell of the N×N grid is uncovered, so the
leaf-hull coverage ceiling TreeMaker had (measured 0.49–0.98 on its subjects)
does not apply. The TreeMaker-era coverage, symmetry and scale measurements are
kept on `archive/treemaker-box-pleat` and in `docs/`.

## 2. Data

**The stick-figure tree is the only structure an LLM edits.** It is a JSON
object in the schema of the 51 artifact trees
(`mcp_harness/fixtures/full17_v3_sticks/*.json`), which is also what
`python -m pleatwright author` writes as `tree.json`:

* `nodes`: `[{name, parent, length, direction}]`. The root has
  `parent: null`; `length` is an integer edge length; `direction` is a 3-vector
  read off the mesh.
* `pairs`: `[[left_leaf, right_leaf], ...]`, the bilateral leaf pairs. The
  packer places each pair in mirrored columns about x = N/2
  (`pleatwright/pack.py`). The packing ladder in `pleatwright/pipeline.py`
  tries mirror-symmetric rows, then unmirrored rows, then every length
  doubled. After the ladder, `pack_options` tries beside layouts, in which a
  child hub's pocket sits beside its parent's flaps wrapped by an L, U or ring
  river, and keeps one only when its grid is below today's chosen grid
  (`docs/superpowers/specs/2026-10-19-river-routing-design.md`).
  A tree whose hubs branch is packed by `pleatwright/nest.py`, where two child
  hubs whose subtrees mirror each other through these leaf pairs
  (`pack.hub_pairs`) share a strip split at x = N/2; hub pairs are derived,
  never authored.
* `readings`: the VLM's notes on how it read the mesh views.

The VLM emits this through the `submit_tree` tool (`tree_authoring.TOOL`), and
`tree_contract.check` rejects malformed trees before a human sees them.

The output is one folder per model, `<Subject>_<grid>/` (artifact rolls:
`<Subject> roll <n>_<grid>/`), with four files in the layout of COrigami's
released samples: `packing_cp.svg`, `solving_cp.svg`, `shaping_cp.svg` and
`overview.png`. The SVGs use COrigami's semantics (`pleatwright/cp.py`): a
1000×1000 viewBox, one `<line>` per crease, red = mountain, blue = valley,
black = border, green = hinge, and `opacity` scaling a shaping crease's fold
angle.

## 3. Stages and modules

The pipeline lives in `mcp_harness/`; the app lives in `app/` (see the app row below).

| stage | modules |
|---|---|
| text → concept image → mesh | `mesh_acquire.py` (`MESH_PROVIDER=hf2`: Nano Banana 2.1 image (FLUX.1-schnell Space without `GEMINI_API_KEY`) → Hunyuan3D-2 mesh Space; `fake` for offline use), `gemini_image.py`, `mesh_ratings.py`, `subject_rewrite.py` |
| mesh → VLM tree + human review | `gated_pipeline.py`, `tree_authoring.py`, `tree_contract.py`, `vlm_render.py`, `pair_fusion.py`, `llm_client.py`, `env_config.py` |
| tree → finished model | `pleatwright/` (stick, pack, nest, base, solve, narrow, shape, orchestrate, fold, cp, render, pipeline) |
| certification | `pleatwright/certify/`: `layers.py` (`constraint_graph` and what it needs), `sat_order.py`, `layer_certify.py`, `layer_order.py`, `flat_fold.py`, `cp_audit.py` |
| front door | `pleatwright/__main__.py` |
| app | `app/server/pleatwright_app` (FastAPI: event log, tools, guided flow), `app/web` (React + three.js) |
| data | `fixtures/full17_v3_trees/`, `fixtures/full17_v3_sticks/`, the mesh/render fixtures the kept tests read, `docs/` |

## 4. Running it

From `mcp_harness/`:

```
python -m pleatwright author "a dog" --out DIR [--open]   # mesh + VLM tree, human review loop
python -m pleatwright fold DIR/tree.json --out DIR [--layout auto|symmetric|smaller]   # tree -> DIR/<Subject>_<grid>/
python -m pleatwright run "a dog" --out DIR [--open]      # author, then fold
```

`fold` also accepts an artifact roll name (`dog_0`) in place of a path. In the
review loop `a` approves, `q` quits (exit 1, state saved in `DIR/author/`), and
any other line is revision feedback. A Pleatwright stage failure exits 1, a
mesh-provider failure exits 2, and an LLM client that cannot be configured
(e.g. no API key) exits 3, before the mesh is requested. `.env.example` lists
every variable the code reads.

* **Mesh.** `MESH_PROVIDER` selects the provider: `fake` (the offline default),
  `hf2` (concept image → Hunyuan3D-2), `hf` (a single text-to-3D Space) or
  `meshy` (paid, needs `MESHY_API_KEY`). `HF_TOKEN` is read by the HF providers.
  `hf2` draws its concept image with Nano Banana 2.1 when `GEMINI_API_KEY` is
  set (paid tier, about $0.042 an image; the free tier's image quota is 0),
  else with FLUX.1-schnell; `MESH_IMAGE_BACKEND=flux` forces FLUX. Nano Banana
  gave correct anatomy on 33/34 owner-scored meshes against FLUX's 21/34
  (`docs/superpowers/evidence/2026-10-16-concept-image/`). Its seed does not
  reproduce, so the app gives every drawn mesh round its own draw label
  (`docs/superpowers/specs/2026-10-19-nano-banana-image-stage-design.md`).
* **VLM.** `llm_client` reads `LLM_PROVIDER` (default `claude`, which needs
  `ANTHROPIC_API_KEY`) and `LLM_MODEL` (the `claude` preset defaults to
  `claude-haiku-5-5`: 51/51 trees folded on the 17 original meshes on 2026-10-10 at
  about $0.003 a tree); `env_config` loads the repo-root `.env` without overriding
  the shell. The app ignores `LLM_MODEL`: its composer's model pill picks Haiku 5.5
  (default) or Sonnet 5 (`claude-sonnet-5`) for each authoring action
  (`pleatwright_app/guided.py` `MODELS`). Authoring refuses to run with
  `LLM_MAX_TOKENS` below 64000 (`gated_pipeline.REQUIRED_MAX_TOKENS`); the CLI
  sets 64000 when it is unset. The live path needs a working `ANTHROPIC_API_KEY`;
  it was exercised end to end through the app on 2026-10-07 ("a dog": tree revised
  once, grid 54, solving 282/282 flat-foldable, global CERTIFIED), and the CLI
  `author`/`run` commands share that code path. `fold` needs no key.
* **App.** `make app` serves the app at http://127.0.0.1:8000 (see
  `app/README.md`). A new run first shows its concept image and mesh for
  review (`Approve mesh`, or feedback that the VLM turns into a better subject
  description before a fresh-seed redraw; `mcp_harness/subject_rewrite.py`).
  Each subject's meshes are rated in a `ratings.json` beside the cached mesh
  (`mcp_harness/mesh_ratings.py`), and a new run of the subject is served its
  best proven mesh first; a subject in `MESH_LIBRARY_DIR` (`meshes/<subject>.glb`
  + `photos/<subject>.png`) is served that reference mesh, with its photo, before
  either (`mesh_acquire.library_mesh`). `make test` also runs the app server tests, and CI's
  `web` job runs the UI tests and build.
* **Tests.** `make test` from the repo root (the default interpreter is
  `mcp_harness/.venv/bin/python`; override with `make PYTHON=... test`). CI
  runs the same target on Python 3.14 with the pins in
  `.github/workflows/ci.yml`. `requirements.txt` lists the dependencies;
  `requirements-frozen.txt` records the verified transitive set.

## 5. Owner rules (binding)

* Tests and probes use **only** the 51 artifact trees in
  `mcp_harness/fixtures/full17_v3_sticks/`.
* **Never** use tardigrade / water bear as a test subject.

## 6. Archive

TreeMaker, Oriedita, the Lang box-pleat compiler (`box_pleat/`), the MCP agent
(`server.py`, `agent_loop.py`) and the web IDE (`web/`, `docker/`) are on the
branch `archive/treemaker-box-pleat`. Do not reintroduce them on `main` without
an owner decision.
