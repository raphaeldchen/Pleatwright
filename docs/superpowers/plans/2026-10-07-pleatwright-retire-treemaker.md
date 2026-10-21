# Pleatwright: retire TreeMaker and the Lang box-pleat compiler — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Main keeps only text → image → mesh → VLM tree (human review) → Pleatwright (formerly `corigami/`) → folded model, behind a `python -m pleatwright` CLI. TreeMaker, the Lang `box_pleat/` compiler, the MCP agent and the web app move to an archive branch.

**Architecture:** First decouple the authoring path (`gated_pipeline`) from packing. Then rename `corigami/` → `pleatwright/` and move into it the certification modules it uses. Add the CLI. Then delete everything outside the import closure of the survivors. Finally rewrite CI, requirements and CLAUDE.md. Pleatwright's outputs must stay byte-identical throughout.

**Tech Stack:** Python 3.14, pytest, numpy, matplotlib, python-sat, trimesh, Pillow, openai (OpenAI-compatible Anthropic endpoint), gradio_client.

**Spec:** `docs/superpowers/specs/2026-10-07-pleatwright-retire-treemaker-design.md`

## Global Constraints

- Branch: `claude/pleatwright-retire-treemaker`, stacked on PR #197 (`claude/corigami-tree-model-pipeline-4e5b12`, head `fa99c7d0`).
- Archive branch name: `archive/treemaker-box-pleat`, cut from `fa99c7d0`.
- Package name `pleatwright`, display name "Pleatwright". Docstrings that cite the paper keep "COrigami" as a citation; anything naming our pipeline says Pleatwright.
- Pleatwright outputs are byte-identical before and after. All 153 SVGs (and the 51 overview PNGs) must match `~/Desktop/origami_samples_artifact_trees`.
- Trees in tests and probes: ONLY the 51 artifact trees in `mcp_harness/fixtures/full17_v3_sticks/` (owner instruction). Never author a new tree for a test.
- `docs/` is history: do not delete or rewrite it. The only exceptions are header notes and the run commands listed in Task 5.
- Run commands from `mcp_harness/` with `PYTHONPATH=.:tests`. Interpreter: `<repo>/mcp_harness/.venv/bin/python` (CI-pinned; matplotlib installed). Below it is written `$PY`.
- Commits end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## File map

| file | change |
|---|---|
| `mcp_harness/gated_pipeline.py` | remove the pack/rescue/repair step; draw the authored tree |
| `mcp_harness/tree_contract.py` | remove the two TreeMaker-packing warnings |
| `mcp_harness/mesh_acquire.py` | remove the `mesh_to_tree` import and demo |
| `mcp_harness/corigami/` → `mcp_harness/pleatwright/` | rename |
| `mcp_harness/pleatwright/certify/` | new home of `layers.py` (trimmed), `sat_order.py`, `layer_certify.py`, `layer_order.py`, `flat_fold.py`, `cp_audit.py` |
| `mcp_harness/pleatwright/pipeline.py` | `run()` accepts a tree-file path; `title_of` handles roll-less names |
| `mcp_harness/pleatwright/__main__.py` | new: CLI `author` / `fold` / `run` |
| `mcp_harness/tests/test_pleatwright.py` | renamed from `test_corigami_pipeline.py` |
| `mcp_harness/tests/test_cli.py` | new |
| `mcp_harness/tests/test_certify_*.py` | moved certification tests |
| `.github/workflows/ci.yml`, `Makefile`, `requirements.txt`, `.gitignore` | rewritten for the survivors |
| `CLAUDE.md`, `AGENTS.md` | rewritten |
| everything else outside the survivors' import closure | deleted (lives on the archive branch) |

---

### Task 0: Archive branch

**Files:** `ARCHIVED.md` (on the archive branch only)

- [ ] **Step 1: Create the archive branch from PR #197's head**

```bash
cd <repo>
git fetch origin
git worktree add -b archive/treemaker-box-pleat /tmp/archive-tb fa99c7d0
```

- [ ] **Step 2: Write `ARCHIVED.md` at the archive worktree's root**

```markdown
# Archived: TreeMaker, the Lang box-pleat compiler, the MCP agent and the web IDE

This branch freezes the repository as of PR #197 (`fa99c7d0`, 2026-10-06), the last
state in which TreeMaker and the Lang Ch. 13 `box_pleat/` compiler were on `main`.

**Why it was retired:** see `docs/superpowers/specs/2026-10-07-pleatwright-retire-treemaker-design.md`
on `main`. In short, the box-pleated pipeline now called Pleatwright folds all 51 artifact
trees, while `box_pleat` emits 7/51; and TreeMaker creases only the leaf hull, where a box-pleated
base tiles the whole square. `main` now keeps only text -> image -> mesh -> tree -> Pleatwright.

**What is here and how to run it**
- TreeMaker engine: `mcp_harness/treemaker/`, `TreemakerWrapper.cpp`; build with `make build`
  (clang++, pybind11, a JDK for the Oriedita linter). See `treemaker_documentation.md`.
- MCP agent: `mcp_harness/server.py`, `agent_loop.py`, `linter_server.py`.
- Web IDE: `web/` (see `web/README.md`).
- Lang box-pleat compiler: `mcp_harness/box_pleat/` (`compile.compile_tree`).
- Tests: `make test` (the fast tier takes 4-6 h on CI because of `test_box_pleat_e2e.py`).
```

- [ ] **Step 3: Commit and push the archive branch**

```bash
cd /tmp/archive-tb
git add ARCHIVED.md
git commit -m "archive: freeze TreeMaker, box_pleat, the MCP agent and the web IDE

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git push -u origin archive/treemaker-box-pleat
cd - && git worktree remove /tmp/archive-tb
```
Expected: `* [new branch] archive/treemaker-box-pleat -> archive/treemaker-box-pleat`.

---

### Task 1: Decouple the authoring path from packing

**Files:**
- Modify: `mcp_harness/gated_pipeline.py`
- Modify: `mcp_harness/tree_contract.py`
- Modify: `mcp_harness/mesh_acquire.py`
- Test: `mcp_harness/tests/test_gated_pipeline.py`, `mcp_harness/tests/test_tree_contract.py`

**Interfaces:**
- Produces:
  - `gated_pipeline.start(mesh_path, *, client, out_dir) -> dict`
  - `gated_pipeline.resume(state, verdict, feedback="", *, client, out_dir) -> dict`
  - The state keys are `status, round, mesh_path, subject_guess, tree, metric_tree, sheet_png, summary, history, note, revisions_authored`. There is no `packing` or `fold`.
  - `gated_pipeline.summarise(tree, leaf_names, *, splits=None, unscored_pairs=None, dropped_pairs=None, figure_note=None) -> str`

- [ ] **Step 1: Rewrite the tests first**

In `tests/test_gated_pipeline.py`:
1. Delete these tests and helpers, whose subject is the pack/serve/repair step:
   - `fake_pack_ok`, `fake_pack_collapses_neck`, `TwoToolClient`, `_repair_calls`, `_author_calls`, `_leaf_count`;
   - `test_pack_reports_an_unchanged_serve_as_such`, `test_pack_names_a_reorder_as_invisible`, `test_pack_reports_a_failure_without_pretending`;
   - `test_the_summary_SHOUTS_when_the_engine_invented_flaps`, `test_the_summary_says_so_when_nothing_packed_and_still_shows_the_tree`;
   - `test_start_draws_the_served_tree_not_the_authored_one`, `test_the_tree_sheet_is_never_a_tool_the_model_sees` (its subject, `agent_loop`, is retired);
   - `test_an_unpackable_tree_still_reaches_the_human`;
   - `test_a_length_moving_rescue_is_never_reported_as_unchanged`, `test_a_structural_repair_is_named_rather_than_hidden`, `test_an_unregistered_stage_says_it_does_not_know`, `test_every_stage_in_the_ladders_vocabulary_is_handled`, `test_the_stub_flatten_and_placement_branches_say_what_they_did`;
   - `test_flatten_without_a_recorded_node_list_does_not_crash`, `test_flatten_with_no_actual_shrinkage_says_nothing_changed`;
   - `test_pack_prefers_the_serve_records_stage_over_the_marker_parse`, `test_pack_falls_back_to_the_marker_when_no_record_was_written`;
   - `test_an_unrecorded_node_list_reads_as_unknown_not_as_the_authored_tree`, `test_an_empty_served_list_is_not_silently_replaced`;
   - `test_the_default_pack_fn_never_destroys_a_previous_serve_record`, `test_the_default_pack_fn_refuses_a_stale_record`;
   - `test_a_crashing_packer_degrades_to_a_state_not_an_exception`, `test_the_served_sheet_labels_edges_in_the_models_own_grid_units`;
   - `test_pack_keeps_the_detail_payload_off_the_full_error_string`, `test_pack_detail_is_none_when_the_error_has_no_payload`, `test_pack_detail_is_none_on_a_served_tree`;
   - `test_the_summary_appends_the_repair_block_only_when_a_repair_record_exists`;
   - `test_a_bare_error_never_reaches_the_model`, `test_a_full_envelope_spends_exactly_one_repair_turn_and_the_merge_packs`, `test_a_paired_name_is_refused_and_the_original_is_shown`, `test_a_decline_keeps_the_original_and_quotes_the_reason`, `test_prose_with_no_tool_call_is_refused`, `test_a_merge_that_still_fails_shows_the_repaired_tree`, `test_a_tree_that_packs_has_no_repair_and_an_unchanged_summary`, `test_a_crash_inside_the_repair_path_is_a_refusal_not_an_exception`.
2. In every remaining test, remove the keyword argument `pack_fn=...` from `GP.start(...)` and `GP.resume(...)` calls:
   ```bash
   cd mcp_harness && python3 - <<'EOF'
   import re
   p = 'tests/test_gated_pipeline.py'; s = open(p).read()
   s = re.sub(r',\s*pack_fn=[A-Za-z_]+', '', s)
   open(p, 'w').write(s)
   EOF
   ```
3. Replace `test_approve_keeps_the_fold_and_does_not_recompile` with:
   ```python
   def test_approve_returns_the_tree_and_calls_nothing(tmp_path, monkeypatch):
       """Approving is a state change only: no authoring turn, no compile."""
       st, c = _started(tmp_path, monkeypatch, [DOG])
       out = asyncio.run(GP.resume(st, "approve", client=c, out_dir=str(tmp_path)))
       assert out["status"] == "approved"
       assert out["tree"] == st["tree"]
       assert "fold" not in out and "packing" not in out
       assert len(c.calls) == 1
   ```
4. Change every `GP.summarise(tree, packing_dict, leaves, ...)` call to `GP.summarise(tree, leaves, ...)` (drop the second positional argument).
5. Add:
   ```python
   def test_the_summary_says_nothing_about_packing():
       s = GP.summarise(_tree(), ["head", "tail", "paw_L", "paw_R"])
       assert "Packing" not in s and "pack" not in s.lower()

   def test_the_sheet_draws_the_authored_tree_in_grid_units(tmp_path, monkeypatch):
       monkeypatch.setattr(GP.vlm_render, "render_mesh_views",
                           lambda *a, **k: _fake_mesh_views(tmp_path))
       drawn = {}
       real = GP.vlm_render.render_tree_sheet
       def spy(nodes, out_path, **kw):
           drawn["nodes"] = nodes
           return real(nodes, out_path, **kw)
       monkeypatch.setattr(GP.vlm_render, "render_tree_sheet", spy)
       st = asyncio.run(GP.start("fake.glb", client=FakeClient([DOG_WITH_PASSTHROUGH_NECK]),
                                 out_dir=str(tmp_path)))
       assert st["status"] == "awaiting_review"
       assert {n[0] for n in drawn["nodes"]} == {"spine", "neck", "head", "tail"}
       assert {n[0]: n[3] for n in drawn["nodes"]}["neck"] == 3
   ```
6. In `test_the_sheet_is_topologically_sorted_before_it_is_drawn`, remove the `child_first` packer. The test then pins `_topo` on the authored tree, which is already parent-first, so add a direct check instead:
   ```python
   def test_topo_sorts_a_child_first_list():
       draw = [("head", "neck", [1, 0, 0], 2), ("neck", "spine", [1, 0, 0], 3),
               ("spine", None, None, 0)]
       assert [t[0] for t in GP._topo(draw)] == ["spine", "neck", "head"]
   ```
   and delete the old `test_the_sheet_is_topologically_sorted_before_it_is_drawn`.

In `tests/test_tree_contract.py`, delete `test_leaf_count_window_warns_but_never_blocks`, and the root-children warning test if one exists (`grep -n "children" tests/test_tree_contract.py`). Add:
```python
def test_no_packing_window_warning_exists():
    r = tc.check(_root(12))
    assert r["ok"] is True
    assert not any("packable window" in w for w in r["warnings"])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `$PY -m pytest tests/test_gated_pipeline.py tests/test_tree_contract.py -q`
Expected: FAILs, e.g. `TypeError: summarise() takes 2 positional arguments`, `test_no_packing_window_warning_exists` fails, and `test_approve_returns_the_tree_and_calls_nothing` fails on `"fold" not in out`.

- [ ] **Step 3: Rewrite `gated_pipeline.py`**

- Imports: delete `import error_recipes`, `import pack_repair`, `import rescue_ladder`.
- Delete `_default_pack_fn`, `pack`, `_what_changed`, `_served_tuples`.
- Update the module docstring's second paragraph to say the tree goes to Pleatwright after approval, with no compile before review.
- `_blank_state` returns:
  ```python
  return {"status": "failed", "round": 0, "mesh_path": mesh_path,
          "subject_guess": None, "tree": None, "metric_tree": None,
          "sheet_png": None, "summary": "", "history": [], "note": None,
          "revisions_authored": 0}
  ```
- `_fail` updates `{"status": "failed", "note": note, "metric_tree": None, "sheet_png": None, "summary": ""}`.
- Add, in place of `_served_tuples`:
  ```python
  def _authored_tuples(nodes):
      """The authored tree, drawable: (name, parent, direction, length) tuples,
      lengths in the model's own grid units (what the human checks against the
      mesh render). `_topo` still sorts parents first before drawing."""
      return [(name, parent, direction, _grid(length))
              for name, parent, direction, length in nodes]
  ```
- `summarise`:
  - signature `summarise(tree, leaf_names, *, splits=None, unscored_pairs=None, dropped_pairs=None, figure_note=None)`;
  - delete the `Packing:` line, the `invents_anatomy` block and the `repair` block;
  - update the docstring: the STUB clause goes, the LIMB SEPARATION clause stays.
- `_draft(state, *, client, out_dir, feedback="")`: keep the authoring and figure code. Delete the `pack(...)` try-block and the whole `repair` block. The sheet draws `_topo(_authored_tuples(nodes))`. The final `state.update` becomes:
  ```python
  state.update({"status": "awaiting_review", "tree": tree,
                "subject_guess": tree.get("subject_guess"),
                "metric_tree": {"tree_nodes": tn, "symmetric_pairs": sp,
                                "names": {str(k): v for k, v in names.items()}},
                "sheet_png": sheet,
                "summary": summarise(tree, leaf_names, splits=splits,
                                     unscored_pairs=unscored,
                                     dropped_pairs=dropped,
                                     figure_note=figure_note),
                "revisions_authored": revisions_authored,
                "note": None})
  ```
- `start(mesh_path, *, client, out_dir)` and `resume(state, verdict, feedback="", *, client, out_dir)`: drop `pack_fn`.
  - `resume`'s docstring sentence "Approving does NOT recompile..." becomes "Approving is a state change only; the tree is compiled by Pleatwright after this returns."
  - The failed-approve error text "nothing in this round was compiled, and its fold and figure belong to an earlier round" becomes "nothing in this round was authored, and its figure belongs to an earlier round".
  - The two exhaustion notes say "nothing has been compiled" — leave them as they are, since they are still true.
- `_build`'s docstring: delete "because the repair hook has to rebuild all of it ...".

- [ ] **Step 4: Edit `tree_contract.py`**

Delete `_DEFAULT_WINDOW`, `_window()`, the `lo, hi = _window()` block, and the `len(root_children) >= 4` warning block (both are TreeMaker packing measurements). Keep every error check and the remaining warnings.

- [ ] **Step 5: Edit `mesh_acquire.py`**

- Delete `import mesh_to_tree` (line 44) and the sentence "then chains it into mesh_to_tree.auto_mesh_to_metric_tree" in the module docstring.
- Replace the `__main__` block with:
  ```python
  if __name__ == "__main__":
      import sys
      argv = sys.argv[1:]
      if argv and argv[0] == "--backfill":
          sys.exit(run_backfill_cli(argv[1:]))
      print(acquire_mesh(" ".join(argv) or "a quadruped animal"))
  ```

- [ ] **Step 6: Run the tests**

Run: `$PY -m pytest tests/test_gated_pipeline.py tests/test_tree_contract.py tests/test_mesh_acquire.py -q`
Expected: all pass. If a `test_mesh_acquire` test asserts on `auto_mesh_to_metric_tree`, delete that test: its subject (`mesh_to_tree`) is retired.

Then confirm the authoring path no longer reaches TreeMaker:
```bash
python3 <scratch>/c813ed7b-2e93-4eba-a4b9-1d7bf0bb3387/scratchpad/closure.py . gated_pipeline mesh_acquire
```
Expected: exactly `env_config gated_pipeline llm_client mesh_acquire pair_fusion tree_authoring tree_contract vlm_render`. If `closure.py` is missing, recreate it from `docs/superpowers/plans/2026-10-07-pleatwright-retire-treemaker.md` Appendix A.

- [ ] **Step 7: Commit**

```bash
git add mcp_harness/gated_pipeline.py mcp_harness/tree_contract.py mcp_harness/mesh_acquire.py mcp_harness/tests/test_gated_pipeline.py mcp_harness/tests/test_tree_contract.py mcp_harness/tests/test_mesh_acquire.py
git commit -m "gated_pipeline: drop the TreeMaker pack step; the sheet draws the authored tree

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Rename to Pleatwright and move in the certification slice

**Files:**
- Rename: `mcp_harness/corigami/` → `mcp_harness/pleatwright/`
- Move: `mcp_harness/box_pleat/layers.py`, `mcp_harness/box_pleat/sat_order.py`, `mcp_harness/layer_certify.py`, `mcp_harness/layer_order.py`, `mcp_harness/flat_fold.py`, `mcp_harness/cp_audit.py` → `mcp_harness/pleatwright/certify/`
- Rename tests:
  - `tests/test_corigami_pipeline.py` → `tests/test_pleatwright.py`
  - `tests/test_box_pleat_sat_order.py` → `tests/test_certify_sat_order.py`
  - `tests/test_layer_certify.py` → `tests/test_certify_layer_certify.py`
  - `tests/test_layer_order.py` → `tests/test_certify_layer_order.py`
  - `tests/test_flat_fold.py` → `tests/test_certify_flat_fold.py`
  - `tests/test_cp_audit.py` → `tests/test_certify_cp_audit.py`

**Interfaces:**
- Produces: `pleatwright.certify.{layers, sat_order, layer_certify, layer_order, flat_fold, cp_audit}`. `layers.constraint_graph(ff) -> LayerGraph`, `propagate`, `certify` are unchanged; `piece_keys` is removed.
- `pleatwright.solve.certify` imports `from pleatwright.certify import flat_fold, layer_certify, layers as L, sat_order`.

- [ ] **Step 1: Snapshot today's outputs for the byte-identity check**

```bash
SP=<scratch>/c813ed7b-2e93-4eba-a4b9-1d7bf0bb3387/scratchpad
ls ~/Desktop/origami_samples_artifact_trees | wc -l     # expect 51
```

- [ ] **Step 2: Move files with git**

```bash
cd mcp_harness
git mv corigami pleatwright
mkdir -p pleatwright/certify
git mv box_pleat/layers.py box_pleat/sat_order.py layer_certify.py layer_order.py flat_fold.py cp_audit.py pleatwright/certify/
printf '"""Global flat-foldability certification: layer-order constraints, the SAT\nencoding, and the independent checks it is verified against."""\n' > pleatwright/certify/__init__.py
git add pleatwright/certify/__init__.py
git mv tests/test_corigami_pipeline.py tests/test_pleatwright.py
git mv tests/test_box_pleat_sat_order.py tests/test_certify_sat_order.py
git mv tests/test_layer_certify.py tests/test_certify_layer_certify.py
git mv tests/test_layer_order.py tests/test_certify_layer_order.py
git mv tests/test_flat_fold.py tests/test_certify_flat_fold.py
git mv tests/test_cp_audit.py tests/test_certify_cp_audit.py
```

- [ ] **Step 3: Fix imports inside the moved modules**

- `pleatwright/certify/layers.py`:
  - imports become `from . import layer_certify, layer_order` (replacing `import layer_certify` / `import layer_order`);
  - delete `from . import emit` and `from .assign import _unit_pieces`;
  - delete `def piece_keys(...)` and its body (from `def piece_keys` to the end of that function).
- `sat_order.py`: `import layer_certify` → `from . import layer_certify`.
- `layer_certify.py`: `import layer_order` → `from . import layer_order`; `from layer_order import Prov, _lit` → `from .layer_order import Prov, _lit`.
- `layer_order.py`: `from flat_fold import FlatFoldResult` → `from .flat_fold import FlatFoldResult`.
- `cp_audit.py`: `from flat_fold import CLOSURE_EPS, flat_fold` → `from .flat_fold import CLOSURE_EPS, flat_fold`.
- Function-level imports in these modules: run `grep -n "^\s*import \(layer_order\|layer_certify\|flat_fold\|cp_audit\)\|^\s*from \(layer_order\|layer_certify\|flat_fold\|cp_audit\|box_pleat\)" pleatwright/certify/*.py` and convert each to the relative form above.
- `pleatwright/solve.py` `certify()`: replace its four import lines with `from pleatwright.certify import flat_fold, layer_certify, layers as L, sat_order`, and change `"file_creator": "corigami"` to `"file_creator": "pleatwright"`. That FOLD dict is internal and never written to disk.
- Every other `corigami` import inside `pleatwright/*.py`: `sed -i '' 's/from corigami/from pleatwright/; s/import corigami/import pleatwright/' pleatwright/*.py`.
- Docstrings: run `grep -n "COrigami" pleatwright/*.py`. A line that names OUR pipeline gets reworded to Pleatwright: `pipeline.py` line 1 becomes `"""Pleatwright: stick-figure tree -> finished model, end to end (COrigami §3.2-3.7).`, and `__init__.py`'s summary changes the same way. A line that CITES the paper or its released samples ("COrigami's 'Flat-foldable: k/n'", "COrigami writes packing/solving SVGs...") stays as it is.

- [ ] **Step 4: Fix imports in the moved tests**

```bash
cd mcp_harness && python3 - <<'EOF'
import re, glob
rules = [
 (r'^(\s*)from box_pleat import layers, sat_order', r'\1from pleatwright.certify import layers, sat_order'),
 (r'^(\s*)from box_pleat import layers\b', r'\1from pleatwright.certify import layers'),
 (r'^(\s*)import (layer_certify|layer_order|flat_fold|cp_audit)\b', r'\1from pleatwright.certify import \2'),
 (r'^(\s*)import layer_order as L\b', r'\1from pleatwright.certify import layer_order as L'),
 (r'^(\s*)from (layer_certify|layer_order|flat_fold|cp_audit) import', r'\1from pleatwright.certify.\2 import'),
 (r'^(\s*)from test_layer_order import', r'\1from test_certify_layer_order import'),
 (r'\bcorigami\b', 'pleatwright'),
]
for p in ['tests/test_pleatwright.py'] + glob.glob('tests/test_certify_*.py'):
    s = open(p).read()
    for a, b in rules: s = re.sub(a, b, s, flags=re.M)
    open(p, 'w').write(s)
EOF
grep -n "box_pleat\|square_complete\|test_box_pleat_tree\|RULE6\|corigami" tests/test_pleatwright.py tests/test_certify_*.py
```
Expected: only the old-compiler tests below remain. Delete them; they are integration tests of `box_pleat.compile` and `square_complete`, with numbers measured on the old compiler's output:
- `test_certify_layer_certify.py`: `test_decide_settles_bird_and_lizard_within_four_assignments`, `_subject_constraints`, `test_compile_tree_reports_a_verdict_and_leaves_the_fold_unchanged`;
- `test_certify_layer_order.py`: `test_contradiction_carries_the_creases_it_depends_on`, `test_propagate_transitivity_is_incremental`, `TestSquared...::test_squared_dog_refused` (the method using `square_complete`), and `test_layer_order_entry_point_is_unchanged` (replaced in Step 5);
- `test_certify_flat_fold.py`: `test_squaring_breaks_closure_and_is_reported`.

Then delete any `RULE6_PATH`/`RULE` constant or `test_box_pleat_tree` import left unused (`grep -n RULE tests/test_certify_*.py`). Finally, in `test_pleatwright.py`, the crimp-oracle test's `import cp_audit` becomes `from pleatwright.certify import cp_audit`.

- [ ] **Step 5: Port the entry-point equivalence test onto a Pleatwright CP**

Append to `tests/test_certify_layer_order.py`:
```python
def test_layer_order_entry_point_matches_constraints_for_on_a_pleatwright_cp():
    """constraints_for must return the system layer_order() builds; measured on
    the solved CP of artifact tree starfish_1 (globally CERTIFIED)."""
    from pleatwright import solve as SV
    from test_pleatwright import _build
    from pleatwright.certify import flat_fold as FF, layer_order as L
    sf, con, sigma, lay, b = _build("starfish_1")
    sv = SV.solve(b, certify_global=False)
    fold, _, _ = SV.to_fold(sv.cp)
    ff = FF.flat_fold(fold)
    cons, slots = L.constraints_for(ff)
    assert L.propagate(cons) == L.layer_order(ff)._rel
    assert {s.edge for s in slots} <= {k for _, _, k, a in ff.shared_edges
                                       if a in ("M", "V")}
```

- [ ] **Step 6: Update callers of the moved top-level modules**

```bash
cd mcp_harness && grep -rln "^\s*\(import\|from\) \(layer_certify\|layer_order\|flat_fold\|cp_audit\)\b\|from box_pleat import \(layers\|sat_order\)" --include=*.py . | grep -v "^./pleatwright/"
```
For each hit that survives Task 4 (gated_pipeline, mesh_acquire, tree_authoring, tree_contract, vlm_render, pair_fusion, llm_client, env_config, and their tests), switch it to the `pleatwright.certify` import. Hits in modules that Task 4 deletes need no change; Task 4's closure check will flag anything missed.

- [ ] **Step 7: Run the Pleatwright and certification tests**

Run: `$PY -m pytest tests/test_pleatwright.py tests/test_certify_*.py -q`
Expected: all pass. `test_folder_port_closes_on_corigami_released_shaping_cp` keeps its name, because it refers to COrigami's released sample.

- [ ] **Step 8: Byte-identity check on all 51 artifact trees**

```bash
cd ../docs/superpowers/evidence/2026-10-06-corigami-pipeline
sed -i '' 's/from corigami import pipeline/from pleatwright import pipeline/' batch.py
rm -rf $SP/after_rename $SP/rec_rename.jsonl
<repo>/.venv/bin/python batch.py $SP/after_rename $SP/rec_rename.jsonl 1 2400 5
sed -i '' "s|rec_after.jsonl|rec_rename.jsonl|" $SP/compare_after.py
python3 $SP/compare_after.py records.jsonl
git checkout -- records.jsonl results.md 2>/dev/null; cd -
```
Expected: `rolls ref/new: 51 51 missing: []` and `record field diffs: 0; SVGs byte-identical 153/153; overview PNGs differing in bytes: 0`. Do NOT run `summarise.py` here: it overwrites the committed `records.jsonl`/`results.md`.

- [ ] **Step 9: Commit**

```bash
git add -A mcp_harness/pleatwright mcp_harness/tests mcp_harness/box_pleat docs/superpowers/evidence/2026-10-06-corigami-pipeline/batch.py
git add -u mcp_harness
git commit -m "rename: corigami -> pleatwright; move the certification slice into pleatwright/certify

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Tree-file input and the `python -m pleatwright` CLI

**Files:**
- Modify: `mcp_harness/pleatwright/pipeline.py` (`run`, `title_of`, `__main__` block)
- Modify: `mcp_harness/pleatwright/stick.py` (`load_roll` default `roll`)
- Create: `mcp_harness/pleatwright/__main__.py`
- Test: `mcp_harness/tests/test_cli.py`

**Interfaces:**
- Consumes: `gated_pipeline.start/resume` (Task 1), `mesh_acquire.acquire_mesh(prompt) -> str` (path to `.glb`), `llm_client.LLMClient.from_env()`.
- Produces:
  - `pleatwright.pipeline.run(tree, out_dir, **same kwargs) -> dict`. `tree` is a roll name (`"dog_0"`) or a path ending in `.json`.
  - `pleatwright.__main__.main(argv, *, ask=input, client=None) -> int`.
  - `pleatwright.__main__.author(prompt, out_dir, *, ask, client, open_images=False) -> str | None` returns the `tree.json` path, or None on quit or exhaustion.
  - `pleatwright.__main__.tree_file(state, prompt) -> dict` gives the fixture schema.

- [ ] **Step 1: Write the failing tests**

`mcp_harness/tests/test_cli.py`:
```python
"""The Pleatwright CLI, offline: fake mesh provider, fake VLM client, scripted
review answers. The authored tree is an ARTIFACT tree (owner rule: tests use
only the 51 artifact trees)."""
import asyncio
import json
import os

import pytest

import gated_pipeline as GP
from pleatwright import __main__ as CLI
from pleatwright import pipeline as PL
from test_gated_pipeline import FakeClient, _fake_mesh_views

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIRD = json.load(open(os.path.join(HERE, "fixtures", "full17_v3_sticks", "bird_1.json")))
AUTHORED = {k: BIRD[k] for k in ("subject_guess", "nodes", "pairs", "readings", "leaves")}


@pytest.fixture
def offline(tmp_path, monkeypatch):
    import mesh_acquire
    monkeypatch.setenv("MESH_PROVIDER", "fake")
    monkeypatch.setattr(mesh_acquire, "output_dir", lambda: str(tmp_path / "meshes"))
    monkeypatch.setattr(GP.vlm_render, "render_mesh_views",
                        lambda *a, **k: _fake_mesh_views(tmp_path))
    return tmp_path


def test_tree_file_matches_the_fixture_schema():
    st = {"tree": AUTHORED, "subject_guess": AUTHORED["subject_guess"]}
    t = CLI.tree_file(st, "a bird")
    assert set(t) >= {"roll", "subject", "subject_guess", "nodes", "pairs", "readings", "source"}
    assert t["nodes"] == AUTHORED["nodes"] and t["pairs"] == AUTHORED["pairs"]
    assert t["subject"] == "bird"


def test_author_revises_once_then_approves(offline):
    answers = iter(["make the tail longer", "a"])
    client = FakeClient([AUTHORED, AUTHORED])
    path = CLI.author("a bird", str(offline / "out"), ask=lambda _: next(answers),
                      client=client)
    assert path == str(offline / "out" / "tree.json")
    assert len(client.calls) == 2
    assert "make the tail longer" in json.dumps(client.calls[1]["messages"])
    assert json.load(open(path))["nodes"] == AUTHORED["nodes"]
    assert os.path.exists(offline / "out" / "author" / "state.json")


def test_author_quit_writes_no_tree(offline):
    path = CLI.author("a bird", str(offline / "out"), ask=lambda _: "q",
                      client=FakeClient([AUTHORED]))
    assert path is None
    assert not os.path.exists(offline / "out" / "tree.json")


def test_run_produces_the_four_file_model_folder(offline):
    answers = iter(["a"])
    rc = CLI.main(["run", "a bird", "--out", str(offline / "out")],
                  ask=lambda _: next(answers), client=FakeClient([AUTHORED]))
    assert rc == 0
    folders = [d for d in os.listdir(offline / "out") if d.startswith("Bird_")]
    assert len(folders) == 1
    assert sorted(os.listdir(offline / "out" / folders[0])) == \
        ["overview.png", "packing_cp.svg", "shaping_cp.svg", "solving_cp.svg"]


def test_fold_from_a_tree_file_equals_fold_from_its_roll_name(tmp_path):
    a = PL.run("bird_1", str(tmp_path / "a"), certify_global=False, verbose=False)
    b = PL.run(os.path.join(HERE, "fixtures", "full17_v3_sticks", "bird_1.json"),
               str(tmp_path / "b"), certify_global=False, verbose=False)
    for f in ("packing_cp.svg", "solving_cp.svg", "shaping_cp.svg"):
        assert open(os.path.join(a["folder"], f)).read() == \
            open(os.path.join(b["folder"], f)).read()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `$PY -m pytest tests/test_cli.py -q`
Expected: FAIL with `ImportError: cannot import name '__main__'` (or `No module named 'pleatwright.__main__'`).

- [ ] **Step 3: Teach `pipeline.run` a tree-file path**

In `pleatwright/pipeline.py`, add above `run`:
```python
def _source(tree: str) -> str:
    """A roll name (`dog_0`, the artifact fixtures) or a path to a tree file."""
    if tree.endswith(".json") and os.path.exists(tree):
        return tree
    return os.path.join(STICKS, f"{tree}.json")
```
In `run`, rename the first parameter to `tree`, set `src = _source(tree)`, and replace both `ST.load_roll(os.path.join(STICKS, f"{roll}.json"), ...)` calls with `ST.load_roll(src, ...)`. Set `rec = {"roll": sf.roll}` after the first load. For fixtures that is the same value as before, so the records are unchanged.

Replace `title_of` with:
```python
def title_of(sf) -> str:
    """'Dog roll 0' for an artifact roll; 'Dog' for a CLI-authored tree."""
    subj = sf.name.replace("_", " ")
    subj = f"{subj[0].upper()}{subj[1:]}"
    head, _, n = sf.roll.rpartition("_")
    return f"{subj} roll {n}" if head and n.isdigit() else subj
```
In `stick.py` `load_roll`, use `d.get("roll", d.get("subject", "tree"))` where it reads `d["roll"]`.

- [ ] **Step 4: Write `pleatwright/__main__.py`**

```python
"""Pleatwright from the command line.

    python -m pleatwright author "a dog" --out DIR [--open]
    python -m pleatwright fold DIR/tree.json --out DIR
    python -m pleatwright run "a dog" --out DIR [--open]

`author`: text -> concept image -> mesh (mesh_acquire) -> VLM tree
(gated_pipeline), paused for a human after every round. `fold`: tree ->
Pleatwright -> DIR/<Subject>_<grid>/ with the four files of COrigami's
released samples. `run`: both.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shutil
import subprocess
import sys

PROMPT = ("\n[a] approve   [q] quit   or type what is wrong with the tree: ")


def _subject(prompt: str, guess: str | None) -> str:
    words = re.findall(r"[a-z]+", (prompt or "").lower())
    words = [w for w in words if w not in ("a", "an", "the", "origami")]
    return "_".join(words[:3]) or (guess or "tree").split()[0].lower()


def tree_file(state: dict, prompt: str) -> dict:
    """The authored tree in the artifact-fixture schema `pleatwright` reads."""
    t = state["tree"]
    subject = _subject(prompt, state.get("subject_guess"))
    return {"roll": subject, "subject": subject,
            "subject_guess": t.get("subject_guess"),
            "nodes": t["nodes"], "pairs": t.get("pairs") or [],
            "leaves": t.get("leaves") or [], "readings": t.get("readings") or [],
            "source": f"python -m pleatwright author {prompt!r}"}


def _show(state: dict, work: str, open_images: bool) -> None:
    print("\n" + (state.get("summary") or state.get("note") or ""))
    for p in (os.path.join(work, "mesh_views.png"), state.get("sheet_png")):
        if p and os.path.exists(p):
            print(f"  figure: {p}")
            if open_images and sys.platform == "darwin":
                subprocess.run(["open", p], check=False)


def _client():
    import env_config
    import llm_client
    env_config.load_env()
    os.environ.setdefault("LLM_MAX_TOKENS", "64000")
    return llm_client.LLMClient.from_env()


def author(prompt: str, out_dir: str, *, ask=input, client=None,
           open_images: bool = False) -> str | None:
    import gated_pipeline as GP
    import mesh_acquire
    work = os.path.join(out_dir, "author")
    os.makedirs(work, exist_ok=True)
    glb = mesh_acquire.acquire_mesh(prompt)
    shutil.copyfile(glb, os.path.join(work, "mesh.glb"))
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        c = os.path.join(os.path.dirname(glb), "concept" + ext)
        if os.path.exists(c):
            shutil.copyfile(c, os.path.join(work, "concept" + ext))
    client = client or _client()
    state = asyncio.run(GP.start(os.path.join(work, "mesh.glb"), client=client, out_dir=work))
    while True:
        json.dump(state, open(os.path.join(work, "state.json"), "w"), indent=1)
        if state["status"] == "exhausted":
            print("\n" + state["note"])
            return None
        _show(state, work, open_images)
        answer = ask(PROMPT).strip()
        if answer.lower() in ("q", "quit"):
            return None
        if answer.lower() in ("a", "approve", "y", "yes") and state["status"] == "awaiting_review":
            state = asyncio.run(GP.resume(state, "approve", client=client, out_dir=work))
            json.dump(state, open(os.path.join(work, "state.json"), "w"), indent=1)
            path = os.path.join(out_dir, "tree.json")
            json.dump(tree_file(state, prompt), open(path, "w"), indent=1)
            print(f"\ntree written: {path}")
            return path
        if answer.lower() in ("a", "approve", "y", "yes"):
            print("this round failed, so there is nothing to approve; describe a fix or quit")
            continue
        state = asyncio.run(GP.resume(state, "revise", answer, client=client, out_dir=work))


def fold(tree_path: str, out_dir: str) -> int:
    from pleatwright import pipeline
    rec = pipeline.run(tree_path, out_dir, verbose=True)
    if "failure" in rec:
        print(f"pleatwright failed at stage '{rec['failure']}'", file=sys.stderr)
        return 1
    print(f"\nmodel written: {rec['folder']}")
    return 0


def main(argv=None, *, ask=input, client=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m pleatwright")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("author", "run"):
        p = sub.add_parser(name)
        p.add_argument("prompt")
        p.add_argument("--out", required=True)
        p.add_argument("--open", action="store_true")
    p = sub.add_parser("fold")
    p.add_argument("tree")
    p.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "fold":
        return fold(a.tree, a.out)
    try:
        path = author(a.prompt, a.out, ask=ask, client=client, open_images=a.open)
    except RuntimeError as e:          # mesh provider: quota, Space down, empty mesh
        print(f"mesh generation failed: {e}", file=sys.stderr)
        return 2
    if path is None:
        return 1
    return fold(path, a.out) if a.cmd == "run" else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run the tests**

Run: `$PY -m pytest tests/test_cli.py tests/test_pleatwright.py -q`
Expected: all pass. `test_run_produces_the_four_file_model_folder` folds bird_1, which takes about 10 s.

- [ ] **Step 6: Re-run the byte-identity check from Task 2 Step 8**

Expected: `record field diffs: 0; SVGs byte-identical 153/153; overview PNGs differing in bytes: 0`. Titles for `*_N` rolls are unchanged, so the PNGs match.

- [ ] **Step 7: Commit**

```bash
git add mcp_harness/pleatwright/__main__.py mcp_harness/pleatwright/pipeline.py mcp_harness/pleatwright/stick.py mcp_harness/tests/test_cli.py
git commit -m "pleatwright: CLI (author / fold / run) and tree-file input

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Delete the retired code

**Files:** everything outside the survivors' closure (computed), plus `web/`, `docker/`, `mcp_harness/treemaker/`, the Java/C++ build files, and `treemaker_documentation.md`.

- [ ] **Step 1: Compute the keep set and the delete list**

Save as `$SP/retire_plan.py` and run it from `mcp_harness/`:
```python
"""Survivors = import closure of the CLI and the stays-list, plus tests whose
project imports all survive. Prints the delete list; exits 1 if a kept test
imports a retired module (fix by deleting that test FUNCTION, then re-run)."""
import ast, os, subprocess, sys
CLOSURE = os.environ["SP"] + "/closure.py"
ENTRY = ["pleatwright.__main__", "pleatwright.pipeline", "pleatwright.orchestrate",
         "gated_pipeline", "mesh_acquire", "tree_authoring", "tree_contract",
         "vlm_render", "pair_fusion", "llm_client", "env_config"]
keep = set(subprocess.run([sys.executable, CLOSURE, "."] + ENTRY,
                          capture_output=True, text=True).stdout.split())
top = {f[:-3] for f in os.listdir(".") if f.endswith(".py")} - {"conftest"}
pkgs = {d for d in os.listdir(".") if os.path.isfile(os.path.join(d, "__init__.py"))}
def proj_imports(path):
    out = set()
    for n in ast.walk(ast.parse(open(path).read())):
        names = []
        if isinstance(n, ast.Import): names = [a.name for a in n.names]
        elif isinstance(n, ast.ImportFrom) and n.module and not n.level: names = [n.module]
        for m in names:
            if m.split(".")[0] in top | pkgs: out.add(m.split(".")[0])
    return out
retired = (top - {m.split(".")[0] for m in keep}) | (pkgs - {"pleatwright"})
helpers = {f[:-3] for f in os.listdir("tests") if f.endswith(".py") and not f.startswith("test_")}
bad = 0
dele = sorted(m + ".py" for m in top if m in retired) + sorted(p + "/" for p in pkgs if p in retired)
for f in sorted(os.listdir("tests")):
    if not f.endswith(".py"): continue
    imp = proj_imports("tests/" + f)
    dead = imp & retired
    live = imp - retired
    if dead and not (live - helpers):
        dele.append("tests/" + f)              # its subject is retired
    elif dead:
        print("MIXED", f, sorted(dead)); bad += 1
print("\n".join(dele))
sys.exit(1 if bad else 0)
```
Run: `SP=$SP python3 $SP/retire_plan.py > $SP/retire_list.txt; echo exit=$?`
For each `MIXED` line, open the test file and delete the test functions that import or exercise the retired module. Keep the functions that test a survivor. Re-run until exit=0. Expected MIXED candidates: `test_mesh_acquire.py` (a `mesh_to_tree` chain test), `test_tree_contract.py` (`body_plans`, and the "tool wrapper" section that tests `server.validate_tree`), `test_llm_client.py` (`probe_image_contentpart`, `agent_loop`), `test_vlm_render.py` if present.

- [ ] **Step 2: Check non-import references from the survivors to retired files**

```bash
cd mcp_harness && python3 - <<'EOF'
import re, os
dele = [l.strip() for l in open(os.environ["SP"] + "/retire_list.txt") if l.strip() and not l.startswith("MIXED")]
names = {os.path.basename(d).rstrip("/").removesuffix(".py") for d in dele}
pat = re.compile(r"[\"'][^\"']*\b(" + "|".join(sorted(names, key=len, reverse=True)) + r")(\.py|/)")
kept = [p for p in (["pleatwright/" + f for f in os.listdir("pleatwright") if f.endswith(".py")] +
        ["pleatwright/certify/" + f for f in os.listdir("pleatwright/certify") if f.endswith(".py")] +
        [f for f in os.listdir(".") if f.endswith(".py")] + ["tests/" + f for f in os.listdir("tests") if f.endswith(".py")])
        if not any(p == d or p.startswith(d) for d in dele)]
for p in kept:
    for i, l in enumerate(open(p), 1):
        if pat.search(l) and not l.strip().startswith("#"): print(f"{p}:{i}: {l.strip()[:140]}")
EOF
```
Expected: no output. Resolve every hit; usually it is a test reading a retired fixture, and that test goes.

- [ ] **Step 3: Delete**

```bash
cd mcp_harness
grep -v '^MIXED' $SP/retire_list.txt | xargs git rm -r -q
git rm -r -q treemaker TreemakerWrapper.cpp CMakeLists.txt build.sh build_linter.sh OrieditaValidator.java HANDOFF_*.md 2>/dev/null
cd .. && git rm -r -q web docker treemaker_documentation.md
rm -f mcp_harness/headless_treemaker*.so mcp_harness/OrieditaValidator.class && rm -rf mcp_harness/oriedita
```

- [ ] **Step 4: Delete orphaned fixtures, goldens and test data**

```bash
cd mcp_harness && python3 - <<'EOF'
import os, re, subprocess
kept_text = "\n".join(open(p).read() for p in subprocess.run(
    ["git", "ls-files", "*.py", "pleatwright/*.py"], capture_output=True, text=True).stdout.split())
for root in ("fixtures", "tests/fixtures", "tests/goldens", "tests/data"):
    if not os.path.isdir(root): continue
    for e in sorted(os.listdir(root)):
        stem = re.sub(r"\.\w+$", "", e)
        if e not in kept_text and not re.search(r"\b" + re.escape(stem) + r"\b", kept_text):
            print(os.path.join(root, e))
EOF
```
Review the list. Then `git rm -r` every entry EXCEPT `fixtures/full17_v3_trees`, `fixtures/full17_v3_sticks`, and `fixtures/SOURCES.md` (provenance). Also `git rm tests/baseline_verdicts.json tests/bless.py tests/cases.py tests/runner.py tests/verdict_baseline.py` if Step 1 retired every test that uses them (`grep -l "import cases\|import runner\|verdict_baseline" tests/*.py` returns nothing).

- [ ] **Step 5: Static verification**

```bash
cd mcp_harness
$PY - <<'EOF'
import importlib, os
mods = [f[:-3] for f in os.listdir(".") if f.endswith(".py") and f != "conftest.py"]
mods += ["pleatwright." + f[:-3] for f in os.listdir("pleatwright") if f.endswith(".py") and f != "__init__.py"]
mods += ["pleatwright.certify." + f[:-3] for f in os.listdir("pleatwright/certify") if f.endswith(".py") and f != "__init__.py"]
bad = [m for m in mods if not __import__("importlib").util.find_spec(m) or not importlib.import_module(m)]
print(len(mods), "modules import; failures:", bad)
EOF
PYTHONPATH=.:tests $PY -m pytest tests/ --collect-only -q | tail -2
ls
```
Expected: `failures: []`, collection has no errors, and `ls` shows only `conftest.py env_config.py gated_pipeline.py llm_client.py mesh_acquire.py pair_fusion.py tree_authoring.py tree_contract.py vlm_render.py pleatwright fixtures tests` plus `generated_meshes` (gitignored) and `.gitignore`.

- [ ] **Step 6: Run the whole suite**

Run: `PYTHONPATH=.:tests $PY -m pytest tests/ -q -p no:cacheprovider`
Expected: all pass, in minutes, not hours. Any failure is investigated, never deleted to make the run green, unless its subject is retired code that Step 1 missed.

- [ ] **Step 7: Commit**

```bash
cd .. && git add -A mcp_harness web docker treemaker_documentation.md
git commit -m "retire: TreeMaker, Oriedita, the Lang box_pleat compiler, the MCP agent and the web IDE

All of it lives on archive/treemaker-box-pleat (fa99c7d0 + ARCHIVED.md).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: CI, requirements, CLAUDE.md, AGENTS.md, doc pointers

**Files:**
- Rewrite: `.github/workflows/ci.yml`, `Makefile`, `requirements.txt`, `CLAUDE.md`, `AGENTS.md`
- Modify: `.gitignore`, `docs/superpowers/specs/2026-10-06-corigami-tree-to-model-pipeline.md`, `docs/superpowers/evidence/2026-10-06-corigami-pipeline/README.md`, `mcp_harness/conftest.py`
- Delete: `requirements-frozen.txt` if it only pins retired packages (check with `grep -ciE "pybind11|mcp|scikit|skeletor" requirements-frozen.txt`)

- [ ] **Step 1: Read the survivors' external imports**

```bash
cd mcp_harness && grep -rhoE "^\s*(import|from) [a-zA-Z_]+" --include=*.py . | awk '{print $2}' | sort -u
```
Expected third-party set: `dotenv gradio_client matplotlib numpy openai PIL pysat pytest trimesh` (plus `httpx`/`pydantic` only if imported directly). Use exactly this set below; add any extra name it prints.

- [ ] **Step 2: `requirements.txt`**

```text
# Pleatwright pipeline: text -> image -> mesh -> VLM tree -> box-pleated folded model.
pytest                 # 9.x
numpy
matplotlib             # 3.11.2 -- overview renders
python-sat==1.9.dev15  # pleatwright.certify SAT layer order
trimesh                # vlm_render: mesh views for the VLM
Pillow                 # vlm_render / concept images
openai                 # llm_client: OpenAI-compatible Anthropic endpoint
gradio_client          # mesh_acquire: HF text->image->mesh Spaces
python-dotenv          # env_config: repo-root .env
```

- [ ] **Step 3: `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
  workflow_dispatch:

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python 3.14
        uses: actions/setup-python@v5
        with:
          python-version: "3.14"
      - name: Cache pip
        uses: actions/cache@v4
        with:
          path: ~/.cache/pip
          key: pip-${{ runner.os }}-${{ hashFiles('requirements.txt', '.github/workflows/ci.yml') }}
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          python -m pip install "pytest==9.0.3" "numpy==2.4.3" "matplotlib==3.11.2" \
            "python-sat==1.9.dev15" "trimesh==4.12.2" "pillow==12.2.0" \
            "openai==2.43.0" "gradio_client==2.5.0" "python-dotenv"
      - name: Test
        run: make PYTHON=python test
```

- [ ] **Step 4: `Makefile`**

```make
# Build + test entry points. CI runs `make PYTHON=python test`.
PYTHON ?= .venv/bin/python
HARNESS := mcp_harness

.PHONY: test clean

test: ## Run the full suite (minutes).
	cd $(HARNESS) && PYTHONPATH=.:tests $(PYTHON) -m pytest tests/ -q

clean:
	rm -rf $(HARNESS)/__pycache__ $(HARNESS)/tests/__pycache__ $(HARNESS)/.pytest_cache
```

- [ ] **Step 5: `.gitignore`**

Remove the TreeMaker/Oriedita lines: `*.so`, `*.dSYM/`, `*.class`, `mcp_harness/oriedita/*.jar`, `mcp_harness/feasibility/captured.jsonl`, `build_err.log`, and any `web/` entries. Keep the Python, `.env*` (with its comment), `.DS_Store` and probe-output lines.

- [ ] **Step 6: `mcp_harness/conftest.py`**

Read it. Delete any fixture or hook that references retired modules (`grep -n "import\|mesh_to_tree\|server" mcp_harness/conftest.py`). Keep the `IDE_MESH_PROVENANCE` default and its comment (`mesh_acquire` survives).

- [ ] **Step 7: Rewrite `CLAUDE.md`**

Write `CLAUDE.md` with these sections, in this order:
1. Title and a 3-sentence summary: Pleatwright turns a text prompt into a folded origami model through text → concept image → mesh → VLM-authored stick-figure tree (human approves) → box-pleated base → solved CP → shaped CP → folded model. It is based on COrigami (arXiv:2606.26299), with the deviations in `docs/superpowers/specs/2026-10-06-corigami-tree-to-model-pipeline.md`.
2. **§0 Research prior art before planning**: copy the existing §0 verbatim.
3. **§1 The physical invariant**: keep the first paragraph of the existing §1.1 ("Every model this pipeline designs folds from ONE UNCUT SQUARE SHEET…") verbatim. Then replace items 1–4 with one paragraph: "A Pleatwright base tiles the whole square: `pleatwright/base.py` `build()` raises `tiling incomplete` if any cell of the N×N grid is uncovered, so the leaf-hull coverage ceiling TreeMaker had (measured 0.49–0.98 on its subjects) does not apply. The TreeMaker-era coverage, symmetry and scale measurements are kept on `archive/treemaker-box-pleat` and in `docs/`."
4. **§2 Data**: the stick-figure tree schema (`nodes[{name,parent,length,direction}]`, `pairs`, `readings`), which is the only structure an LLM edits. Outputs are the four-file folder (`packing_cp.svg`, `solving_cp.svg`, `shaping_cp.svg`, `overview.png`) in COrigami's SVG semantics.
5. **§3 Stages and modules**: the "What stays on main" table from the spec, with `pleatwright/certify/` included.
6. **§4 Running it**: the three CLI commands. Mesh provider env (`MESH_PROVIDER=hf|fake`). The VLM reads `LLM_PROVIDER`/`ANTHROPIC_API_KEY` and needs `LLM_MAX_TOKENS ≥ 64000`. Tests: `make test`.
7. **§5 Owner rules**: tests and probes use only the 51 artifact trees in `mcp_harness/fixtures/full17_v3_sticks/`; never use tardigrade / water bear as a test subject.
8. **§6 Archive**: TreeMaker, Oriedita, the Lang box-pleat compiler, the MCP agent and the web IDE are on `archive/treemaker-box-pleat`. Do not reintroduce them on main without an owner decision.

- [ ] **Step 8: Rewrite `AGENTS.md`**

Keep its "Required: research prior art before developing plans" section verbatim. Replace the two pointer lines at the top with: "Project architecture, stages and owner rules live in [`CLAUDE.md`](CLAUDE.md)." Delete any other line that names TreeMaker, Oriedita, MCP or the web IDE.

- [ ] **Step 9: Header notes on the 10-06 docs**

Insert directly under the H1 of `docs/superpowers/specs/2026-10-06-corigami-tree-to-model-pipeline.md` and `docs/superpowers/evidence/2026-10-06-corigami-pipeline/README.md`:
```markdown
> **2026-10-07:** this pipeline is now **Pleatwright**, package `mcp_harness/pleatwright/`
> (see `docs/superpowers/specs/2026-10-07-pleatwright-retire-treemaker-design.md`).
> The body below is the record as written on 2026-10-06.
```
In the evidence README, change `python -m corigami.pipeline dog_0 --out /tmp/out` to `python -m pleatwright fold fixtures/full17_v3_sticks/dog_0.json --out /tmp/out`. In `box_pleat_baseline_probe.py`, add a first-line comment: `# Runs only on archive/treemaker-box-pleat (box_pleat is retired on main).`

- [ ] **Step 10: Verify, then commit**

```bash
make PYTHON=<repo>/mcp_harness/.venv/bin/python test
grep -rn "treemaker\|TreeMaker\|oriedita\|corigami" CLAUDE.md AGENTS.md Makefile .github requirements.txt | grep -v "archive/treemaker-box-pleat\|corigami-tree-to-model\|corigami-pipeline\|COrigami"
```
Expected: the suite passes, and the grep prints nothing.
```bash
git add -A .github Makefile requirements.txt requirements-frozen.txt .gitignore CLAUDE.md AGENTS.md mcp_harness/conftest.py docs/superpowers/specs/2026-10-06-corigami-tree-to-model-pipeline.md docs/superpowers/evidence/2026-10-06-corigami-pipeline
git commit -m "ci, requirements, CLAUDE.md: the Pleatwright pipeline only

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Final verification and PR

- [ ] **Step 1: Byte-identity on the 51 trees through the CLI**

```bash
cd mcp_harness
rm -rf $SP/cli51 && mkdir -p $SP/cli51
for f in fixtures/full17_v3_sticks/*.json; do $PY -m pleatwright fold "$f" --out $SP/cli51 > /dev/null || echo "FAIL $f"; done
python3 - <<'EOF'
import os, hashlib
SP = os.environ["SP"]; D = os.path.expanduser("~/Desktop/origami_samples_artifact_trees")
same = diff = 0
for d in sorted(os.listdir(D)):
    for f in sorted(os.listdir(os.path.join(D, d))):
        a = hashlib.sha256(open(os.path.join(D, d, f), "rb").read()).hexdigest()
        p = os.path.join(SP, "cli51", d, f)
        b = hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else None
        same += a == b; diff += a != b
        if a != b: print("DIFF", d, f)
print(f"identical {same}/{same + diff}")
EOF
```
Expected: no `FAIL` lines, and `identical 204/204` (51 folders × 4 files).

- [ ] **Step 2: Rebase onto main if #197 has merged, then push and open the PR**

```bash
git fetch origin
git merge-base --is-ancestor fa99c7d0 origin/main && git rebase origin/main
git push -u origin claude/pleatwright-retire-treemaker
```
Open the PR against `main` (or against `claude/corigami-tree-model-pipeline-4e5b12` if #197 is still open). Use title "Pleatwright: retire TreeMaker and the Lang box-pleat compiler from main". The body:
- links the spec and the archive branch;
- lists what stays and what moved;
- gives the verification results from Task 4 Step 6, Task 6 Step 1, and CI;
- states that the live end-to-end run is blocked on the dead Anthropic key.

Then bind it with `mcp__ccd_pr__get_status` / `bind_pr`.

- [ ] **Step 3: Update memory**

- In `corigami-pipeline-replicated.md`, add a section: renamed Pleatwright; package `mcp_harness/pleatwright/`; CLI commands; TreeMaker/box_pleat archived on `archive/treemaker-box-pleat`.
- In `worktree-missing-build-artifacts.md`, add at the top: on main after this PR there is no `.so`, jar or JVM to link; only `.env` (and `generated_meshes/` for live mesh cache hits).
- Update the corresponding MEMORY.md lines.

---

## Appendix A: `closure.py`

The import-closure helper used in Tasks 1 and 4 (also at `$SP/closure.py`):
```python
import ast, os, sys
root = sys.argv[1]; entries = sys.argv[2:]
mods = {}
for dp, dn, fn in os.walk(root):
    dn[:] = [d for d in dn if d not in ('.venv', 'node_modules', 'tests', 'fixtures', '__pycache__')]
    for f in fn:
        if f.endswith('.py'):
            p = os.path.join(dp, f); rel = os.path.relpath(p, root)[:-3].replace(os.sep, '.')
            if rel.endswith('.__init__'): rel = rel[:-9]
            mods[rel] = p
def imports(p, me):
    t = ast.parse(open(p).read()); out = set()
    pkg = me if p.endswith('__init__.py') else (me.rsplit('.', 1)[0] if '.' in me else '')
    for n in ast.walk(t):
        if isinstance(n, ast.Import):
            out |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            base = n.module or ''
            if n.level:
                parts = pkg.split('.') if pkg else []
                parts = parts[:len(parts) - (n.level - 1)] if n.level > 1 else parts
                base = '.'.join(parts + ([base] if base else []))
            out.add(base); out |= {base + '.' + a.name if base else a.name for a in n.names}
    res = set()
    for m in out:
        while m:
            if m in mods: res.add(m); break
            m = m.rsplit('.', 1)[0] if '.' in m else ''
    return res
seen = set(); stack = list(entries)
while stack:
    m = stack.pop()
    if m in seen or m not in mods: continue
    seen.add(m); stack += imports(mods[m], m)
print('\n'.join(sorted(seen)))
```
