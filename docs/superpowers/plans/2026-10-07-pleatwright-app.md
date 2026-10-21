# Pleatwright App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A local web app, with a Claude Code-like look and feel, that runs the Pleatwright pipeline as a guided conversation. A runs sidebar, a chat panel, and an output panel (stepper, viewer, filmstrip) show the concept image, mesh, tree, crease patterns and an unfoldable 3-D model.

**Architecture:** A FastAPI server (`app/server/pleatwright_app`) runs each stage as a tool. Each tool writes into a run folder and appends events to `events.jsonl`. The browser replays and streams those events over a WebSocket. A React + three.js frontend (`app/web`) renders everything from one reducer over the events. The pipeline gains four additive hooks: per-stage CP writes with `on_stage`, the fold model returned from `shape_and_fold`, a `model.fold` exporter, and a mesh `progress` callback. None of them changes the output bytes.

**Tech Stack:** Python 3.14, FastAPI 0.138.1, uvicorn 0.49.0, websockets 16.0, multiprocessing (spawn); React 18.3.1, TypeScript 5.6.3, Vite 5.4.11, three 0.169.0, @react-three/fiber 8.18.0, @react-three/drei 9.122.0, vitest 2.1.8.

**Spec:** `docs/superpowers/specs/2026-10-07-pleatwright-app-design.md`. Read it before starting any task.

## Global Constraints

- **Output bytes are unchanged.** The four files in `<Subject>_<grid>/` (`packing_cp.svg`, `solving_cp.svg`, `shaping_cp.svg`, `overview.png`) must stay byte-identical to what `main` writes today. App-only files (`events.jsonl`, `model.fold`) sit BESIDE that folder, never inside it.
- **Owner rule:** tests and probes use ONLY the 51 artifact trees in `mcp_harness/fixtures/full17_v3_sticks/`, loaded via `mcp_harness/tests/artifact_trees.py`. NEVER use tardigrade / water bear as a test subject or prompt.
- Python deps added: `fastapi==0.138.1`, `uvicorn==0.49.0`, `websockets==16.0`. These are the versions already installed in the dev venv.
- JS deps are pinned exactly (no `^`): react 18.3.1, react-dom 18.3.1, three 0.169.0, @react-three/fiber 8.18.0, @react-three/drei 9.122.0, typescript 5.6.3, vite 5.4.11, @vitejs/plugin-react 4.3.4, vitest 2.1.8, @types/react 18.3.12, @types/react-dom 18.3.1, @types/three 0.169.0.
- The server binds `127.0.0.1` only. API keys never reach the browser. Do not edit the repo-root `.env`.
- The `LLMClient` is created and used only on the server's event loop (the lesson of the #198 duplicate-billing bug).
- The fold runs in a `multiprocessing` **spawn** child, never fork.
- Never use bare `git stash`. Every commit message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Environment (every task)

- Worktree root: `<repo>`, branch `claude/pleatwright-app`.
- `PY=<repo>/mcp_harness/.venv/bin/python`. It has CI's pins and fastapi/uvicorn/websockets.
- Pipeline tests, from `mcp_harness/`: `PYTHONPATH=.:tests $PY -m pytest <files> -q -p no:cacheprovider`
- App server tests, from `mcp_harness/`: `PYTHONPATH=.:tests:../app/server $PY -m pytest ../app/server/tests -q -p no:cacheprovider`
- Web tests, from `app/web/`: `npm test`
- Measured fold times (certify_global=True): bird_1 about 6 s (grid 40, 752 faces), dog_0 about 9 s, starfish_1 about 15 s. App tests that fold use **bird_1** with the prompt "a bird". The spec's §7 example said dog_0; bird_1 is chosen for speed.

## File Structure

```
mcp_harness/pleatwright/pipeline.py      MODIFY  per-stage CP writes, on_stage; shape_and_fold returns model + W0
mcp_harness/pleatwright/export.py        CREATE  write_model_fold: FOLD 1.1 with fold-slider frames
mcp_harness/mesh_acquire.py              MODIFY  acquire_mesh(progress=); TwoStageProvider.generate(progress=)
mcp_harness/tests/test_pipeline_hooks.py CREATE  tests for on_stage and the export
mcp_harness/tests/test_mesh_progress.py  CREATE  tests for the progress callback

app/server/pleatwright_app/__init__.py   CREATE  puts mcp_harness on sys.path
app/server/pleatwright_app/events.py     CREATE  EventLog: append-only events.jsonl + live subscribers
app/server/pleatwright_app/runs.py       CREATE  RunStore: run folders, ids, listing, status, safe file paths
app/server/pleatwright_app/tools.py      CREATE  Ctx, ToolFailed, make_mesh, author_tree, revise_tree, review_again, approve_tree, fold, TOOL_SCHEMAS
app/server/pleatwright_app/foldproc.py   CREATE  FoldJob: the fold in a spawned child, queue messages, kill on cancel
app/server/pleatwright_app/guided.py     CREATE  Manager: guided flow, one active run, retry, cancel, restart recovery
app/server/pleatwright_app/api.py        CREATE  create_app: REST, WebSocket, files, origin check, static UI
app/server/pleatwright_app/__main__.py   CREATE  `python -m pleatwright_app [--port] [--no-ui]`
app/server/record_fixture.py             CREATE  records a fake-provider run's events for the frontend tests
app/server/tests/conftest.py             CREATE  sys.path, no mesh provenance writes, `offline` fixture
app/server/tests/test_events.py, test_runs.py, test_tools.py, test_foldproc.py, test_guided.py, test_api.py   CREATE

app/web/package.json, package-lock.json, index.html, tsconfig.json, vite.config.ts   CREATE
app/web/src/main.tsx, App.tsx, styles.css                CREATE
app/web/src/types.ts                                     CREATE  event + view types
app/web/src/runStore.ts, runStore.test.ts                CREATE  events -> RunView reducer
app/web/src/api.ts                                       CREATE  REST + WebSocket client
app/web/src/fold.ts, fold.test.ts                        CREATE  FOLD -> triangles, frames, crease segments
app/web/src/usePanZoom.ts                                CREATE  shared pan/zoom hook
app/web/src/components/RunsSidebar.tsx, Chat.tsx, StageBlock.tsx, Stepper.tsx, Filmstrip.tsx,
                       Viewer.tsx, ImageView.tsx, CPView.tsx, MeshView.tsx, ModelView.tsx   CREATE
app/web/src/__fixtures__/bird_run.events.jsonl           CREATE  recorded by record_fixture.py
app/README.md                                            CREATE
Makefile, .github/workflows/ci.yml, requirements.txt, requirements-frozen.txt, CLAUDE.md   MODIFY
```

---

### Task 1: Pipeline writes each CP when its stage ends, and reports it through `on_stage`

**Files:**
- Modify: `mcp_harness/pleatwright/pipeline.py` (`run` at ~201, `_run` at ~219-322)
- Test: `mcp_harness/tests/test_pipeline_hooks.py` (create)

**Interfaces:**
- Produces: `pipeline.run(tree, out_dir, *, scale=1.0, certify_global=True, max_candidates=400, verbose=True, orchestrate=False, orchestrate_k=3, on_stage=None) -> dict`. `on_stage(stage: str, info: dict) -> None` is called, in order:
  - `"packing"`, `{"files": [<abs>/packing_cp.svg], "folder": <abs folder>, "grid": N, "rung": str, "tried": int}`
  - `"solving"`, `{"files": [<abs>/solving_cp.svg], "flat_foldable": [int, int], "global_verdict": <as solve returns it>}`
  - `"shaping"`, `{"files": [<abs>/shaping_cp.svg], "flat_foldable": [int, int], "candidate": <shape_and_fold dict>}` (the candidate is an in-process object and is not picklable)
  - `"output"`, `{"files": [<abs>/overview.png], "folder": <abs folder>}`

  An exception raised inside `on_stage` becomes `StageError(<that stage>)`.

- [ ] **Step 1: Write the failing tests**

Create `mcp_harness/tests/test_pipeline_hooks.py`:

```python
"""Hooks the app needs from the pipeline (spec 2026-10-07-pleatwright-app §4.3).
Artifact trees only (owner rule)."""
import os

import pytest

from pleatwright import pipeline as PL

FOUR = ["overview.png", "packing_cp.svg", "shaping_cp.svg", "solving_cp.svg"]
ORDER = ["packing_cp.svg", "solving_cp.svg", "shaping_cp.svg", "overview.png"]


def test_on_stage_fires_per_stage_once_that_stages_file_is_on_disk(tmp_path):
    seen = []

    def on_stage(stage, info):
        names = [os.path.basename(f) for f in info["files"]]
        assert all(os.path.isfile(f) for f in info["files"])
        # the NEXT stage's file is not written yet: files appear stage by stage
        i = ORDER.index(names[0])
        folder = os.path.dirname(info["files"][0])
        assert not any(os.path.exists(os.path.join(folder, n)) for n in ORDER[i + 1:])
        if stage == "shaping":
            assert {"model", "W0", "polys"} <= set(info["candidate"])
        seen.append((stage, names))

    rec = PL.run("bird_1", str(tmp_path), certify_global=False, verbose=False,
                 on_stage=on_stage)
    assert seen == [("packing", ["packing_cp.svg"]), ("solving", ["solving_cp.svg"]),
                    ("shaping", ["shaping_cp.svg"]), ("output", ["overview.png"])]
    assert sorted(os.listdir(rec["folder"])) == FOUR


def test_on_stage_info_carries_the_numbers_the_chat_shows(tmp_path):
    got = {}
    PL.run("bird_1", str(tmp_path), certify_global=False, verbose=False,
           on_stage=lambda s, i: got.setdefault(s, i))
    assert got["packing"]["grid"] == 40 and got["packing"]["tried"] >= 1
    assert isinstance(got["packing"]["rung"], str)
    assert len(got["solving"]["flat_foldable"]) == 2
    assert len(got["shaping"]["flat_foldable"]) == 2
    assert got["output"]["folder"] == got["packing"]["folder"]


def test_an_on_stage_error_is_reported_as_that_stage(tmp_path):
    def boom(stage, info):
        if stage == "solving":
            raise RuntimeError("callback failed")
    with pytest.raises(PL.StageError) as e:
        PL.run("bird_1", str(tmp_path), certify_global=False, verbose=False, on_stage=boom)
    assert e.value.stage == "solving"
```

- [ ] **Step 2: Run them to verify they fail**

Run: `PYTHONPATH=.:tests $PY -m pytest tests/test_pipeline_hooks.py -q -p no:cacheprovider`
Expected: 3 FAIL with `TypeError: run() got an unexpected keyword argument 'on_stage'`.

- [ ] **Step 3: Implement**

In `pipeline.py`, add `on_stage=None` as the last keyword of BOTH `run` and `_run`, and forward it from `run` (`on_stage=on_stage`). Update `run`'s docstring: "`on_stage(stage, info)`, if given, is called after each stage's file is on disk (packing, solving, shaping, output); see the app spec §4.3."

Add two helpers above `run`:

```python
def _write(folder: str, name: str, text: str) -> str:
    path = os.path.join(folder, name)
    with open(path, "w") as f:
        f.write(text)
    return path


def _emit(on_stage, stage: str, **info) -> None:
    if on_stage is not None:
        on_stage(stage, info)
```

In `_run`, move each CP write to the end of its own stage, with the same expressions and arguments as today, so the bytes do not change:

1. Directly after `rec["grid_size"] = N` (still in the packing stage):
```python
    name = title_of(sf)
    folder = os.path.join(out_dir, f"{name}_{N}")
    os.makedirs(folder, exist_ok=True)
    pcp, dots = B.packing_cp(base)
    p = _write(folder, "packing_cp.svg", _pretty(pcp.svg(packing=True, precision=0)))
    _emit(on_stage, "packing", files=[p], folder=folder, grid=N,
          rung=rec["packing_rung"], tried=tried)
```
2. Directly after `rec["solve_stats"] = ...` (before `_stage[0] = "shaping"`):
```python
    p = _write(folder, "solving_cp.svg", _pretty(sv.cp.svg(precision=5)))
    _emit(on_stage, "solving", files=[p], flat_foldable=list(sv.ff_local),
          global_verdict=sv.global_verdict)
```
3. Directly after `rec["tree_similarity"] = ...` (before `_stage[0] = "output"`):
```python
    p = _write(folder, "shaping_cp.svg", shp.cp.svg(precision=5))
    _emit(on_stage, "shaping", files=[p], flat_foldable=list(ff), candidate=cand)
```
4. The output stage keeps only the overview:
```python
    _stage[0] = "output"
    p = os.path.join(folder, "overview.png")
    R.overview(p, name=name, grid=N, stick=sf,
               packing_cp=pcp, solving_cp=sv.cp, shaping_cp=shp.cp, polys=polys,
               solving_ff=sv.ff_local, shaping_ff=rec["shaping_flat_foldable"],
               packing_dots=dots)
    _emit(on_stage, "output", files=[p], folder=folder)
    rec["folder"] = folder
    rec["total_secs"] = round(time.perf_counter() - t_all, 2)
```
Delete the old `name = ...`, `folder = ...`, `os.makedirs`, `pcp, dots = ...` and the three `open(...)` writes from the output section. `rec["folder"]` stays where it was, so the printed JSON key order is unchanged.

- [ ] **Step 4: Run the new and existing pipeline tests**

Run: `PYTHONPATH=.:tests $PY -m pytest tests/test_pipeline_hooks.py tests/test_pleatwright.py tests/test_cli.py -q -p no:cacheprovider`
Expected: all PASS. This includes the bird_1 / starfish_1 `packing_cp.svg` sha256 pins.

- [ ] **Step 5: Byte-compare all 51 artifact trees against the delivered folder (local, not CI)**

Save this as `$SCRATCH/byte51.py` (any scratch directory outside the repo) and run it from `mcp_harness/` with `PYTHONPATH=.:tests $PY $SCRATCH/byte51.py`. It takes about 15-25 minutes; run it in the background and capture its output to a file.

```python
import os, sys, tempfile, filecmp
from concurrent.futures import ProcessPoolExecutor
from artifact_trees import ROLLS
from pleatwright import pipeline as PL
DELIVERED = os.path.expanduser("~/Desktop/origami_samples_artifact_trees")
FILES = ["packing_cp.svg", "solving_cp.svg", "shaping_cp.svg", "overview.png"]

def one(roll):
    out = tempfile.mkdtemp()
    rec = PL.run(roll, out, verbose=False)
    ref = os.path.join(DELIVERED, os.path.basename(rec["folder"]))
    return roll, [f for f in FILES
                  if not filecmp.cmp(os.path.join(rec["folder"], f), os.path.join(ref, f), shallow=False)]

if __name__ == "__main__":
    with ProcessPoolExecutor(max_workers=6) as ex:
        res = list(ex.map(one, ROLLS))
    bad = [(r, d) for r, d in res if d]
    print(f"{4 * len(res) - sum(len(d) for _, d in bad)}/{4 * len(res)} identical")
    for r, d in bad:
        print("DIFF", r, d)
    sys.exit(1 if bad else 0)
```
Expected: `204/204 identical`. If ANY file differs, STOP and report NEEDS_CONTEXT with the list. A difference means a stage mutates an object after its old write point, and the write order cannot move for that file.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/pleatwright/pipeline.py mcp_harness/tests/test_pipeline_hooks.py
git commit -m "pipeline: write each CP when its stage ends and report it through on_stage

Bytes unchanged: 204/204 files identical to the delivered 51-tree folder.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: `shape_and_fold` returns its fold model; `export.write_model_fold` writes `model.fold`

**Files:**
- Modify: `mcp_harness/pleatwright/pipeline.py` (`shape_and_fold`, the return dict at ~137)
- Create: `mcp_harness/pleatwright/export.py`
- Test: `mcp_harness/tests/test_pipeline_hooks.py` (append)

**Interfaces:**
- Consumes: Task 1's `on_stage("shaping", {"candidate": cand, ...})`.
- Produces:
  - `shape_and_fold(...)` now also returns `"model": m` (a `fold.Model`) and `"W0": W0` (a 4x4 `np.ndarray`).
  - `export.FRAMES = 21`.
  - `export.write_model_fold(path: str, cand: dict, frames: int = FRAMES) -> dict` writes the file and returns the dict.
  - `export.model_fold(cand, frames=FRAMES) -> dict` is the same without writing.
  - FOLD keys: `file_spec` (1.1), `file_creator` ("pleatwright"), `file_classes` (["singleModel"]), `frame_classes` (["creasePattern"]), `frame_unit` ("unit"), `vertices_coords` (flat sheet, `[x, y]` grid units), `faces_vertices`, `edges_vertices`, `edges_assignment` (B/M/V), `edges_foldAngle` (degrees), `file_frames` (`frames` entries, each `{"frame_title": "<p>%", "frame_inherit": true, "frame_parent": 0, "frame_classes": ["foldedForm"], "vertices_coords": [[x, y, z], ...]}`), and `pleatwright:percents` (the fold percentage of each frame, 0..100).
- **Spec deviation, recorded:** spec §7 says the 0% frame is "flat (z = 0)". Every frame is carried through `W0`, so that the camera does not jump while scrubbing. The 0% frame is therefore the flat sheet moved rigidly: coplanar and congruent to the CP, but not necessarily at z = 0. The test checks coplanarity and congruence.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_pipeline_hooks.py`)

```python
import json

import numpy as np

from pleatwright import export as EX
from pleatwright import fold as F


def _candidate(roll, tmp_path):
    got = {}
    PL.run(roll, str(tmp_path), certify_global=False, verbose=False,
           on_stage=lambda s, i: got.setdefault(s, i))
    return got["shaping"]["candidate"]


@pytest.fixture(scope="module")
def bird(tmp_path_factory):
    return _candidate("bird_1", tmp_path_factory.mktemp("bird"))


def test_full_frame_reproduces_the_polygons_overview_png_draws(bird):
    doc = EX.model_fold(bird)
    X = np.array(doc["file_frames"][-1]["vertices_coords"])
    m = bird["model"]
    worst = max(float(np.linalg.norm(X[f] - P, axis=1).max())
                for f, P in zip(m.faces, bird["polys"]))
    # frames average a vertex's images over its faces; the polygons do not.
    # closure_error is the max PER-AXIS spread of those images in the paper
    # frame, so after the rigid W0 the Euclidean gap is at most sqrt(3) * it.
    assert worst <= np.sqrt(3) * bird["closure"] + 1e-9


def test_zero_frame_is_the_sheet_moved_rigidly(bird):
    doc = EX.model_fold(bird)
    X0 = np.array(doc["file_frames"][0]["vertices_coords"])
    V = np.array(doc["vertices_coords"])
    Vz = np.c_[V, np.zeros(len(V))]
    # congruent: every pairwise distance on a sample of vertices is preserved
    idx = np.linspace(0, len(V) - 1, 40).astype(int)
    d_flat = np.linalg.norm(Vz[idx, None] - Vz[None, idx], axis=-1)
    d_frame = np.linalg.norm(X0[idx, None] - X0[None, idx], axis=-1)
    assert np.allclose(d_flat, d_frame, atol=1e-9)
    # coplanar: rank-2 after centring
    s = np.linalg.svd(X0 - X0.mean(axis=0), compute_uv=False)
    assert s[2] <= 1e-9 * s[0]


def test_fold_file_is_internally_consistent(bird, tmp_path):
    p = tmp_path / "model.fold"
    EX.write_model_fold(str(p), bird)
    doc = json.loads(p.read_text())
    nv = len(doc["vertices_coords"])
    assert doc["file_spec"] == 1.1 and len(doc["file_frames"]) == EX.FRAMES
    assert doc["pleatwright:percents"][0] == 0 and doc["pleatwright:percents"][-1] == 100
    assert len(doc["edges_vertices"]) == len(doc["edges_assignment"]) == len(doc["edges_foldAngle"])
    assert set(doc["edges_assignment"]) <= {"B", "M", "V"}
    assert all(0 <= i < nv for f in doc["faces_vertices"] for i in f)
    assert all(len(fr["vertices_coords"]) == nv for fr in doc["file_frames"])


def test_frames_follow_the_fold_solver_at_each_percent(bird):
    doc = EX.model_fold(bird, frames=3)
    m, W0 = bird["model"], bird["W0"]
    X = F.vertex_positions(m, F.solve_fold(m, 0.5))
    want = (np.c_[X, np.ones(len(X))] @ W0.T)[:, :3]
    assert np.allclose(np.array(doc["file_frames"][1]["vertices_coords"]), want, atol=1e-12)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `PYTHONPATH=.:tests $PY -m pytest tests/test_pipeline_hooks.py -q -p no:cacheprovider`
Expected: the 4 new tests FAIL (`ModuleNotFoundError: No module named 'pleatwright.export'`).

- [ ] **Step 3: Implement**

In `shape_and_fold`'s return dict, add `"model": m, "W0": W0,` after `"polys": polys,`.

Create `mcp_harness/pleatwright/export.py`:

```python
"""The folded model as a FOLD 1.1 file, with fold-slider frames.

`file_frames[i]` holds the 3-D vertex positions at fold percentage
`pleatwright:percents[i]`, computed by Pleatwright's own folder
(`fold.solve_fold`) and carried through the shaped world transform `W0`, so
the browser only plays frames back and there is one fold implementation.
Frame 0 is the flat sheet moved rigidly by `W0` (coplanar, congruent to the
CP, not necessarily at z = 0) so the camera does not jump while scrubbing.
"""
from __future__ import annotations

import json

import numpy as np

from . import fold as F

FRAMES = 21


def _world(X: np.ndarray, W0: np.ndarray) -> list:
    return (np.c_[X, np.ones(len(X))] @ W0.T)[:, :3].tolist()


def model_fold(cand: dict, frames: int = FRAMES) -> dict:
    m, W0 = cand["model"], cand["W0"]
    percents = [round(100 * i / (frames - 1), 6) for i in range(frames)]
    out = []
    for p in percents:
        X = F.vertex_positions(m, F.solve_fold(m, p / 100))
        out.append({"frame_title": f"{p:g}%", "frame_inherit": True, "frame_parent": 0,
                    "frame_classes": ["foldedForm"], "vertices_coords": _world(X, W0)})
    return {
        "file_spec": 1.1, "file_creator": "pleatwright",
        "file_classes": ["singleModel"], "frame_classes": ["creasePattern"],
        "frame_unit": "unit",
        "vertices_coords": np.asarray(m.vertices, float).tolist(),
        "faces_vertices": [list(map(int, f)) for f in m.faces],
        "edges_vertices": [[int(u), int(v)] for u, v in m.edges],
        "edges_assignment": list(m.assignment),
        "edges_foldAngle": [float(a) for a in m.fold_angle],
        "file_frames": out,
        "pleatwright:percents": percents,
    }


def write_model_fold(path: str, cand: dict, frames: int = FRAMES) -> dict:
    doc = model_fold(cand, frames)
    with open(path, "w") as f:
        json.dump(doc, f)
    return doc
```

- [ ] **Step 4: Run tests**

Run: `PYTHONPATH=.:tests $PY -m pytest tests/test_pipeline_hooks.py tests/test_pleatwright.py -q -p no:cacheprovider`
Expected: all PASS. If `test_zero_frame_is_the_sheet_moved_rigidly` fails on coplanarity, print `s` and check whether `solve_fold(m, 0)` returns identity matrices. If it does not, report NEEDS_CONTEXT; do not loosen the tolerance.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/pleatwright/pipeline.py mcp_harness/pleatwright/export.py mcp_harness/tests/test_pipeline_hooks.py
git commit -m "pleatwright: export the folded model as FOLD with fold-slider frames

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: `acquire_mesh(progress=)` reports the concept image, then the mesh

**Files:**
- Modify: `mcp_harness/mesh_acquire.py` (`TwoStageProvider.generate` ~685, `acquire_mesh` ~857)
- Test: `mcp_harness/tests/test_mesh_progress.py` (create)

**Interfaces:**
- Produces:
  - `acquire_mesh(prompt, *, provider=None, provider_name=None, cache_dir=None, progress=None) -> str`. `progress(kind: str, path: str | None)` is called exactly once with `"image"` (a concept path, or `None` when the provider draws none) and then exactly once with `"mesh"` (the returned path), on both the fetch and cache-hit paths.
  - `TwoStageProvider.generate(prompt, out_dir, progress=None)` calls `progress("image", concept)` as soon as the concept is written, before the mesh Space is called.
  - Providers whose `generate` has no `progress` parameter keep working; `acquire_mesh` then reports `("image", None)` after `generate` returns.

- [ ] **Step 1: Write the failing tests**

Create `mcp_harness/tests/test_mesh_progress.py`:

```python
"""acquire_mesh's optional progress callback (app spec §4.3 hook 4)."""
import os

import mesh_acquire
from test_two_stage_provider import _provider, png, glb  # noqa: F401  (fixtures)


def _record():
    calls = []
    return calls, lambda kind, path: calls.append((kind, path and os.path.basename(path)))


def test_two_stage_reports_the_concept_before_the_mesh_space_is_called(tmp_path, png, glb):
    log, (calls, progress) = [], _record()

    def mesh_space(*a):
        assert calls == [("image", "concept.png")]     # image reported BEFORE stage 2
        return glb
    prov = _provider({"img/space": png, "mesh/space": mesh_space}, log)
    out = mesh_acquire.acquire_mesh("an octopus", provider=prov, provider_name="hf2",
                                    cache_dir=str(tmp_path / "c"), progress=progress)
    assert calls == [("image", "concept.png"), ("mesh", "mesh.glb")]
    assert out.endswith("mesh.glb")


def test_cache_hit_reports_the_cached_concept_and_mesh(tmp_path, png, glb):
    prov = _provider({"img/space": png, "mesh/space": glb}, [])
    kw = dict(provider=prov, provider_name="hf2", cache_dir=str(tmp_path / "c"))
    mesh_acquire.acquire_mesh("an octopus", **kw)
    calls, progress = _record()
    mesh_acquire.acquire_mesh("an octopus", progress=progress, **kw)
    assert calls == [("image", "concept.png"), ("mesh", "mesh.glb")]


def test_a_provider_without_progress_reports_no_concept(tmp_path):
    calls, progress = _record()
    mesh_acquire.acquire_mesh("a bird", provider=mesh_acquire.FakeMeshProvider(),
                              provider_name="fake", cache_dir=str(tmp_path / "c"),
                              progress=progress)
    assert calls == [("image", None), ("mesh", "mesh.glb")]


def test_no_callback_behaves_as_before(tmp_path, png, glb):
    prov = _provider({"img/space": png, "mesh/space": glb}, [])
    out = mesh_acquire.acquire_mesh("an octopus", provider=prov, provider_name="hf2",
                                    cache_dir=str(tmp_path / "c"))
    assert os.path.isfile(out)
```

- [ ] **Step 2: Run them to verify they fail**

Run: `PYTHONPATH=.:tests $PY -m pytest tests/test_mesh_progress.py -q -p no:cacheprovider`
Expected: FAIL with `TypeError: acquire_mesh() got an unexpected keyword argument 'progress'`.

- [ ] **Step 3: Implement**

In `TwoStageProvider.generate`, change the signature to `def generate(self, prompt: str, out_dir: str, progress=None) -> str:`, and add the call at two points:
- in the `if existing:` branch, before `mesh_result = ...`: `if progress: progress("image", existing)`
- right after `shutil.copyfile(img_src, concept)`: `if progress: progress("image", concept)`

In `acquire_mesh`, add `progress=None` as the last keyword, and document it in the docstring: "`progress(kind, path)`, if given, is called with ("image", concept-or-None) and then ("mesh", glb), on the fetch and cache-hit paths alike." Then:

Add a module-level helper above `acquire_mesh`:
```python
def _cached_concept(key_dir: str) -> str | None:
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        c = os.path.join(key_dir, "concept" + ext)
        if os.path.isfile(c) and os.path.getsize(c) > 0:
            return c
    return None
```
- In the cache-hit branch, immediately before `return cached`:
```python
        if progress:
            progress("image", _cached_concept(key_dir))
            progress("mesh", cached)
```
- Replace `result = provider.generate(prompt, key_dir)` with:
```python
    import inspect
    takes_progress = "progress" in inspect.signature(provider.generate).parameters
    if progress and takes_progress:
        result = provider.generate(prompt, key_dir, progress=progress)
    else:
        result = provider.generate(prompt, key_dir)
        if progress:
            progress("image", None)
```
  Leave the existing empty-mesh check in place. After it, before `_write_mesh_meta_best_effort(...)`, add `if progress: progress("mesh", result)`.

- [ ] **Step 4: Run tests**

Run: `PYTHONPATH=.:tests $PY -m pytest tests/test_mesh_progress.py tests/test_mesh_acquire.py tests/test_two_stage_provider.py tests/test_cli.py -q -p no:cacheprovider`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/mesh_acquire.py mcp_harness/tests/test_mesh_progress.py
git commit -m "mesh_acquire: optional progress callback reports the concept image before the mesh

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: App server foundation: `EventLog` and `RunStore`

**Files:**
- Create: `app/server/pleatwright_app/__init__.py`, `events.py`, `runs.py`
- Create: `app/server/tests/conftest.py`, `test_events.py`, `test_runs.py`

**Interfaces:**
- Produces:
  - `events.EventLog(path)` exposes `.events: list[dict]`, `.append(type, **fields) -> dict` (the event `{seq, t, type, **fields}`), `.after(seq) -> list[dict]`, `.last -> dict | None`, `.subscribe() -> asyncio.Queue`, and `.unsubscribe(q)`.
  - `runs.status_of(last_event) -> "new" | "running" | "waiting" | "done" | "failed"`
  - `runs.RunStore(root)` exposes:
    - `.root`
    - `.create(prompt, now=None) -> run_id`, which appends `run_created {prompt, subject}`
    - `.dir(run_id) -> str`
    - `.log(run_id) -> EventLog` (cached per id; raises `FileNotFoundError` for an unknown or invalid id)
    - `.list() -> list[{"id", "prompt", "subject", "created", "status"}]`, newest first
    - `.file(run_id, rel) -> str`, a real path; raises `FileNotFoundError` if outside the run folder or missing
  - `runs.default_root() -> str`: `$PLEATWRIGHT_RUNS_DIR`, or `~/Pleatwright/runs`.

- [ ] **Step 1: Create the package and the test conftest**

`app/server/pleatwright_app/__init__.py`:
```python
"""The Pleatwright app server (spec docs/superpowers/specs/2026-10-07-pleatwright-app-design.md)."""
import os
import sys

_HARNESS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "mcp_harness"))
if _HARNESS not in sys.path:
    sys.path.insert(0, _HARNESS)
```

`app/server/tests/conftest.py`:
```python
"""App server tests. Trees come only from the 51 artifact trees (owner rule)."""
import os
import sys

import pytest

os.environ.setdefault("IDE_MESH_PROVENANCE", "0")   # never write into sibling caches
_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
for p in (os.path.join(_REPO, "app", "server"), os.path.join(_REPO, "mcp_harness"),
          os.path.join(_REPO, "mcp_harness", "tests")):
    if p not in sys.path:
        sys.path.insert(0, p)


@pytest.fixture
def offline(tmp_path, monkeypatch):
    """Fake mesh provider into tmp, fake mesh-view renderer (as tests/test_cli.py)."""
    import gated_pipeline as GP
    import mesh_acquire
    from test_gated_pipeline import _fake_mesh_views
    monkeypatch.setenv("MESH_PROVIDER", "fake")
    monkeypatch.setattr(mesh_acquire, "output_dir", lambda: str(tmp_path / "meshes"))
    monkeypatch.setattr(GP.vlm_render, "render_mesh_views",
                        lambda *a, **k: _fake_mesh_views(tmp_path))
    return tmp_path
```

- [ ] **Step 2: Write the failing tests**

`app/server/tests/test_events.py`:
```python
import asyncio
import json

from pleatwright_app.events import EventLog


def test_append_numbers_events_and_persists_them(tmp_path):
    p = tmp_path / "events.jsonl"
    log = EventLog(str(p))
    a = log.append("run_created", prompt="a bird", subject="bird")
    b = log.append("stage_started", stage="image")
    assert (a["seq"], b["seq"]) == (0, 1) and a["type"] == "run_created" and "t" in a
    assert [json.loads(l)["seq"] for l in p.read_text().splitlines()] == [0, 1]
    again = EventLog(str(p))
    assert again.events == log.events and again.last["stage"] == "image"
    assert [e["seq"] for e in again.after(0)] == [1] and again.after(-1) == again.events


def test_a_torn_last_line_is_ignored_on_reload(tmp_path):
    p = tmp_path / "events.jsonl"
    EventLog(str(p)).append("run_created", prompt="a bird", subject="bird")
    with open(p, "a") as f:
        f.write('{"seq": 1, "ty')            # the server died mid-write
    log = EventLog(str(p))
    assert len(log.events) == 1
    assert log.append("user_message", text="x")["seq"] == 1


def test_subscribers_receive_new_events_in_order(tmp_path):
    async def main():
        log = EventLog(str(tmp_path / "e.jsonl"))
        q = log.subscribe()
        log.append("a")
        log.append("b")
        got = [(await q.get())["type"], (await q.get())["type"]]
        log.unsubscribe(q)
        log.append("c")
        return got, q.qsize()
    assert asyncio.run(main()) == (["a", "b"], 0)
```

`app/server/tests/test_runs.py`:
```python
import datetime as dt
import os

import pytest

from pleatwright_app.runs import RunStore, status_of

NOW = dt.datetime(2026, 10, 7, 14, 12)


def test_create_names_the_folder_by_time_and_subject(tmp_path):
    s = RunStore(str(tmp_path))
    rid = s.create("a bird", now=NOW)
    assert rid == "2026-10-07-1412-bird"
    assert s.create("a bird", now=NOW) == "2026-10-07-1412-bird-2"
    assert s.log(rid).events[0]["type"] == "run_created"
    assert s.log(rid).events[0]["prompt"] == "a bird"


def test_list_reports_status_from_the_last_event_newest_first(tmp_path):
    s = RunStore(str(tmp_path))
    a = s.create("a bird", now=NOW)
    b = s.create("a crab", now=NOW + dt.timedelta(minutes=1))
    s.log(a).append("awaiting_review", round=0, can_approve=True)
    rows = s.list()
    assert [r["id"] for r in rows] == [b, a]
    assert rows[1]["status"] == "waiting" and rows[0]["status"] == "running"


@pytest.mark.parametrize("last,want", [
    (None, "new"), ({"type": "stage_started"}, "running"),
    ({"type": "awaiting_review"}, "waiting"), ({"type": "run_finished"}, "done"),
    ({"type": "stage_failed"}, "failed")])
def test_status_of(last, want):
    assert status_of(last) == want


def test_file_refuses_paths_outside_the_run(tmp_path):
    s = RunStore(str(tmp_path / "runs"))
    rid = s.create("a bird", now=NOW)
    (tmp_path / "secret.txt").write_text("x")
    os.makedirs(os.path.join(s.dir(rid), "author"))
    open(os.path.join(s.dir(rid), "author", "mesh.glb"), "wb").close()
    assert s.file(rid, "author/mesh.glb").endswith("mesh.glb")
    for bad in ("../../secret.txt", "/etc/passwd", "author/../../../secret.txt", "nope.png"):
        with pytest.raises(FileNotFoundError):
            s.file(rid, bad)
    os.symlink(str(tmp_path / "secret.txt"), os.path.join(s.dir(rid), "link.txt"))
    with pytest.raises(FileNotFoundError):
        s.file(rid, "link.txt")                     # a symlink out is refused too


def test_unknown_or_invalid_ids_are_refused(tmp_path):
    s = RunStore(str(tmp_path))
    for bad in ("nope", "..", "a/b", ""):
        with pytest.raises(FileNotFoundError):
            s.log(bad)
```

- [ ] **Step 3: Run them to verify they fail**

Run: `PYTHONPATH=.:tests:../app/server $PY -m pytest ../app/server/tests -q -p no:cacheprovider`
Expected: FAIL with `ModuleNotFoundError: No module named 'pleatwright_app.events'`.

- [ ] **Step 4: Implement**

`app/server/pleatwright_app/events.py`:
```python
"""A run's history: `events.jsonl`, one JSON object per line, append-only
(spec §3.2). The chat, stepper, filmstrip and sidebar are all views of it.

Append only from the event loop's thread; worker threads hop over with
`loop.call_soon_threadsafe`, so subscribers see events in `seq` order."""
from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class EventLog:
    def __init__(self, path: str):
        self.path = path
        self.events: list[dict] = []
        if os.path.exists(path):
            with open(path) as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        self.events.append(json.loads(line))
                    except json.JSONDecodeError:
                        break                      # a torn final line: the server died mid-write
            self._rewrite_if_torn()
        self._subs: set[asyncio.Queue] = set()

    def _rewrite_if_torn(self) -> None:
        with open(self.path) as f:
            n = sum(1 for line in f if line.strip())
        if n != len(self.events):
            with open(self.path, "w") as f:
                f.writelines(json.dumps(e) + "\n" for e in self.events)

    def append(self, type: str, **fields) -> dict:
        ev = json.loads(json.dumps({"seq": len(self.events), "t": _now(), "type": type,
                                    **fields}, default=str))
        with open(self.path, "a") as f:
            f.write(json.dumps(ev) + "\n")
        self.events.append(ev)
        for q in list(self._subs):
            q.put_nowait(ev)
        return ev

    def after(self, seq: int) -> list[dict]:
        return self.events[seq + 1:]

    @property
    def last(self) -> dict | None:
        return self.events[-1] if self.events else None

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subs.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subs.discard(q)
```

`app/server/pleatwright_app/runs.py`:
```python
"""Run folders (spec §3.1): one folder per run under the runs root, in the
CLI's `--out DIR` layout plus `events.jsonl` and `model.fold`."""
from __future__ import annotations

import datetime as dt
import os
import re

from . import events as EV

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_STATUS = {"run_finished": "done", "stage_failed": "failed", "awaiting_review": "waiting"}


def default_root() -> str:
    return os.environ.get("PLEATWRIGHT_RUNS_DIR") or os.path.expanduser("~/Pleatwright/runs")


def status_of(last: dict | None) -> str:
    if last is None:
        return "new"
    return _STATUS.get(last["type"], "running")


class RunStore:
    def __init__(self, root: str):
        os.makedirs(root, exist_ok=True)
        self.root = os.path.realpath(root)
        self._logs: dict[str, EV.EventLog] = {}

    def dir(self, run_id: str) -> str:
        if not run_id or not _ID.match(run_id) or run_id in (".", ".."):
            raise FileNotFoundError(run_id)
        d = os.path.join(self.root, run_id)
        if not os.path.isfile(os.path.join(d, "events.jsonl")):
            raise FileNotFoundError(run_id)
        return d

    def log(self, run_id: str) -> EV.EventLog:
        if run_id not in self._logs:
            self._logs[run_id] = EV.EventLog(os.path.join(self.dir(run_id), "events.jsonl"))
        return self._logs[run_id]

    def create(self, prompt: str, now: dt.datetime | None = None) -> str:
        from pleatwright.__main__ import _subject
        subject = _subject(prompt, None)
        base = f"{(now or dt.datetime.now()):%Y-%m-%d-%H%M}-{subject}"
        run_id, n = base, 1
        while os.path.exists(os.path.join(self.root, run_id)):
            n += 1
            run_id = f"{base}-{n}"
        d = os.path.join(self.root, run_id)
        os.makedirs(d)
        open(os.path.join(d, "events.jsonl"), "w").close()
        self.log(run_id).append("run_created", prompt=prompt, subject=subject)
        return run_id

    def list(self) -> list[dict]:
        rows = []
        for name in os.listdir(self.root):
            try:
                log = self.log(name)
            except FileNotFoundError:
                continue
            first = log.events[0] if log.events else {}
            rows.append({"id": name, "prompt": first.get("prompt", ""),
                         "subject": first.get("subject", name), "created": first.get("t", ""),
                         "status": status_of(log.last)})
        return sorted(rows, key=lambda r: (r["created"], r["id"]), reverse=True)

    def file(self, run_id: str, rel: str) -> str:
        d = os.path.realpath(self.dir(run_id))
        p = os.path.realpath(os.path.join(d, rel))
        if os.path.commonpath([p, d]) != d or not os.path.isfile(p):
            raise FileNotFoundError(rel)
        return p
```

- [ ] **Step 5: Run tests**

Run: `PYTHONPATH=.:tests:../app/server $PY -m pytest ../app/server/tests -q -p no:cacheprovider`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add app/server
git commit -m "app: event log and run store

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Tools for the mesh, the tree review, and approval

**Files:**
- Create: `app/server/pleatwright_app/tools.py`
- Test: `app/server/tests/test_tools.py`

**Interfaces:**
- Consumes: `EventLog` (Task 4); `acquire_mesh(progress=)` (Task 3); `gated_pipeline.start/resume`; `pleatwright.__main__._dump`, `tree_file`.
- Produces:
  - `tools.ToolFailed(Exception)`: the failure is already logged as `stage_failed`.
  - `tools.Ctx(run_dir, log, client, loop)`, with `.work`, `.rel(path)`, `.emit(type, **f)`, `.emit_threadsafe(type, **f)` and `.cancelled: threading.Event`.
  - `async make_mesh(ctx, prompt) -> str`
  - `async author_tree(ctx) -> dict`
  - `async revise_tree(ctx, feedback) -> dict`
  - `async review_again(ctx) -> dict`, which re-presents the saved state (costs nothing)
  - `async approve_tree(ctx, prompt) -> str`, returning the path to tree.json
  - `load_state(run_dir) -> dict | None`
  - `present(ctx, state) -> None`
  - `retry_for(stage, run_dir) -> str`
  - `TOOL_SCHEMAS: dict[str, dict]`
- The event shapes are exactly those of spec §3.2. Tree rounds are reported as gated_pipeline's `round` (0-based); the frontend shows `round + 1`.

- [ ] **Step 1: Write the failing tests**

`app/server/tests/test_tools.py`:
```python
"""Tools, offline: fake mesh provider, fake VLM client returning artifact tree bird_1."""
import asyncio
import json
import os

import pytest

from artifact_trees import authored
from pleatwright_app import tools as T
from pleatwright_app.events import EventLog
from test_gated_pipeline import FakeClient

BIRD = authored("bird_1")


def _ctx(tmp_path, client=None):
    loop = asyncio.get_running_loop()
    d = tmp_path / "run"
    d.mkdir(exist_ok=True)
    return T.Ctx(str(d), EventLog(str(d / "events.jsonl")), client, loop)


def _types(ctx):
    return [(e["type"], e.get("stage")) for e in ctx.log.events]


def test_make_mesh_reports_a_skipped_image_then_the_mesh(offline):
    async def main():
        ctx = _ctx(offline)
        path = await T.make_mesh(ctx, "a bird")
        return ctx, path
    ctx, path = asyncio.run(main())
    assert os.path.isfile(path) and path == os.path.join(ctx.work, "mesh.glb")
    assert _types(ctx) == [("stage_started", "image"), ("stage_output", "image"),
                           ("stage_started", "mesh"), ("stage_output", "mesh")]
    img, mesh = ctx.log.events[1], ctx.log.events[3]
    assert img["files"] == [] and img["summary"]["skipped"] is True
    assert mesh["files"] == ["author/mesh.glb"] and mesh["summary"]["provider"] == "fake"


def test_a_mesh_failure_is_logged_with_a_retry(offline, monkeypatch):
    import mesh_acquire

    def boom(*a, **k):
        raise RuntimeError("Space is down")
    monkeypatch.setattr(mesh_acquire, "acquire_mesh", boom)

    async def main():
        ctx = _ctx(offline)
        with pytest.raises(T.ToolFailed):
            await T.make_mesh(ctx, "a bird")
        return ctx
    last = asyncio.run(main()).log.last
    assert last["type"] == "stage_failed" and last["stage"] == "image"
    assert last["retry"] == "make_mesh" and "Space is down" in last["error"]


def test_author_then_revise_then_approve(offline):
    client = FakeClient([BIRD, BIRD])

    async def main():
        ctx = _ctx(offline, client)
        await T.make_mesh(ctx, "a bird")
        await T.author_tree(ctx)
        await T.revise_tree(ctx, "make the tail longer")
        path = await T.approve_tree(ctx, "a bird")
        return ctx, path
    ctx, path = asyncio.run(main())
    ev = ctx.log.events
    rounds = [e for e in ev if e["type"] == "stage_output" and e["stage"] == "tree"]
    assert [r["round"] for r in rounds] == [0, 1, 1]
    assert rounds[0]["summary"] == {"flaps": len(BIRD["leaves"]), "pairs": len(BIRD["pairs"])}
    assert rounds[0]["files"][0] == "author/tree_round0.png"
    assert rounds[-1]["summary"] == {"approved": True}
    assert [e["can_approve"] for e in ev if e["type"] == "awaiting_review"] == [True, True]
    assert json.load(open(path))["nodes"] == BIRD["nodes"]
    assert T.load_state(ctx.run_dir)["status"] == "approved"


def test_a_failed_round_cannot_be_approved_and_says_why(offline):
    client = FakeClient([None])                       # truncated authoring turn

    async def main():
        ctx = _ctx(offline, client)
        await T.make_mesh(ctx, "a bird")
        await T.author_tree(ctx)
        return ctx
    ctx = asyncio.run(main())
    assert ctx.log.events[-2]["type"] == "assistant_message"
    assert ctx.log.last == {**ctx.log.last, "type": "awaiting_review", "can_approve": False}


def test_review_again_re_presents_the_saved_round_without_calling_the_vlm(offline):
    client = FakeClient([BIRD])

    async def main():
        ctx = _ctx(offline, client)
        await T.make_mesh(ctx, "a bird")
        await T.author_tree(ctx)
        await T.review_again(ctx)
        return ctx
    ctx = asyncio.run(main())
    assert len(client.calls) == 1
    assert [e["type"] for e in ctx.log.events[-3:]] == ["stage_output", "assistant_message",
                                                        "awaiting_review"]


def test_retry_for(tmp_path):
    d = str(tmp_path)
    assert T.retry_for("image", d) == T.retry_for("mesh", d) == "make_mesh"
    assert T.retry_for("tree", d) == "author_tree"
    os.makedirs(tmp_path / "author")
    (tmp_path / "author" / "state.json").write_text("{}")
    assert T.retry_for("tree", d) == "review"
    for s in ("packing", "solve", "shape", "model"):
        assert T.retry_for(s, d) == "fold"


def test_every_tool_has_a_schema():
    assert set(T.TOOL_SCHEMAS) == {"make_mesh", "author_tree", "revise_tree",
                                   "approve_tree", "fold"}
```

- [ ] **Step 2: Run to verify failure**

Run: `PYTHONPATH=.:tests:../app/server $PY -m pytest ../app/server/tests/test_tools.py -q -p no:cacheprovider`
Expected: FAIL, `cannot import name 'tools'`.

- [ ] **Step 3: Implement**

`app/server/pleatwright_app/tools.py` (the `fold` tool is added in Task 6):
```python
"""The pipeline's stages as tools (spec §4.1). Each writes files into the run
folder and appends events; an agent can later call the same functions."""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import threading
from dataclasses import dataclass, field

from pleatwright.__main__ import _dump, tree_file


class ToolFailed(Exception):
    """The tool failed; its `stage_failed` event is already in the log."""


@dataclass
class Ctx:
    run_dir: str
    log: object                     # events.EventLog
    client: object                  # llm_client.LLMClient (used on the loop only)
    loop: asyncio.AbstractEventLoop
    cancelled: threading.Event = field(default_factory=threading.Event)

    @property
    def work(self) -> str:
        return os.path.join(self.run_dir, "author")

    def rel(self, path: str) -> str:
        return os.path.relpath(path, self.run_dir)

    def emit(self, type: str, **f) -> dict:
        return self.log.append(type, **f)

    def emit_threadsafe(self, type: str, **f) -> None:
        def go():
            if not self.cancelled.is_set():
                self.log.append(type, **f)
        if not self.cancelled.is_set():
            self.loop.call_soon_threadsafe(go)


TOOL_SCHEMAS = {
    "make_mesh": {"description": "text -> concept image -> mesh",
                  "input_schema": {"type": "object", "properties": {"prompt": {"type": "string"}},
                                   "required": ["prompt"]}},
    "author_tree": {"description": "the VLM reads the mesh and drafts a stick-figure tree",
                    "input_schema": {"type": "object", "properties": {}}},
    "revise_tree": {"description": "the VLM revises the tree from the user's feedback",
                    "input_schema": {"type": "object", "properties": {"feedback": {"type": "string"}},
                                     "required": ["feedback"]}},
    "approve_tree": {"description": "approve the current tree and write tree.json",
                     "input_schema": {"type": "object", "properties": {}}},
    "fold": {"description": "tree.json -> packing, solving, shaping, folded model",
             "input_schema": {"type": "object", "properties": {}}},
}


def retry_for(stage: str, run_dir: str) -> str:
    if stage in ("image", "mesh"):
        return "make_mesh"
    if stage == "tree":
        return "review" if os.path.exists(os.path.join(run_dir, "author", "state.json")) \
            else "author_tree"
    return "fold"


def _mesh_summary(path: str, provider: str) -> dict:
    s = {"provider": provider}
    try:
        import trimesh
        s["faces"] = int(len(trimesh.load(path, force="mesh").faces))
    except Exception:                                  # noqa: BLE001 -- a count is optional
        pass
    return s


async def make_mesh(ctx: Ctx, prompt: str) -> str:
    import mesh_acquire
    os.makedirs(ctx.work, exist_ok=True)
    provider = os.environ.get("MESH_PROVIDER", "fake")
    stage = ["image"]
    ctx.emit("stage_started", stage="image")

    def progress(kind, path):                          # runs on the worker thread
        if ctx.cancelled.is_set():
            return
        if kind == "image":
            files = []
            if path:
                dest = os.path.join(ctx.work, "concept" + os.path.splitext(path)[1])
                shutil.copyfile(path, dest)
                files = [ctx.rel(dest)]
            summary = {"provider": provider} if files else \
                {"skipped": True, "note": f"no concept image ({provider})"}
            ctx.emit_threadsafe("stage_output", stage="image", files=files, summary=summary)
            ctx.emit_threadsafe("stage_started", stage="mesh")
            stage[0] = "mesh"
        elif kind == "mesh":
            dest = os.path.join(ctx.work, "mesh.glb")
            shutil.copyfile(path, dest)
            ctx.emit_threadsafe("stage_output", stage="mesh", files=[ctx.rel(dest)],
                                summary=_mesh_summary(dest, provider))

    try:
        await asyncio.to_thread(mesh_acquire.acquire_mesh, prompt, progress=progress)
    except (RuntimeError, TimeoutError, ValueError, OSError) as e:
        ctx.emit("stage_failed", stage=stage[0], error=str(e), reason="error",
                 retry="make_mesh")
        raise ToolFailed(str(e)) from e
    return os.path.join(ctx.work, "mesh.glb")


def load_state(run_dir: str) -> dict | None:
    p = os.path.join(run_dir, "author", "state.json")
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)


def _save(ctx: Ctx, state: dict) -> None:
    _dump(state, os.path.join(ctx.work, "state.json"))


def present(ctx: Ctx, state: dict) -> None:
    """Emit one review round from a gated_pipeline state (spec §4.1, §4.2)."""
    rnd = state["round"]
    if state["status"] == "awaiting_review":
        paths = (state.get("sheet_png"), os.path.join(ctx.work, "mesh_views.png"))
        files = [ctx.rel(p) for p in paths if p and os.path.exists(p)]
        tree = state.get("tree") or {}
        ctx.emit("stage_output", stage="tree", round=rnd, files=files,
                 summary={"flaps": len(tree.get("leaves") or []),
                          "pairs": len(tree.get("pairs") or [])})
        ctx.emit("assistant_message", text=state.get("summary") or "")
        ctx.emit("awaiting_review", round=rnd, can_approve=True)
    elif state["status"] == "failed":
        ctx.emit("assistant_message", text=state.get("note") or "this round failed")
        ctx.emit("awaiting_review", round=rnd, can_approve=False)
    elif state["status"] == "exhausted":
        ctx.emit("assistant_message", text=state["note"])
        ctx.emit("stage_failed", stage="tree", error=state["note"], reason="exhausted",
                 retry=None)


async def author_tree(ctx: Ctx) -> dict:
    import gated_pipeline as GP
    ctx.emit("stage_started", stage="tree")
    try:
        state = await GP.start(os.path.join(ctx.work, "mesh.glb"), client=ctx.client,
                               out_dir=ctx.work)
    except Exception as e:                             # noqa: BLE001 -- e.g. the mesh renderer
        ctx.emit("stage_failed", stage="tree", error=f"{type(e).__name__}: {e}",
                 reason="error", retry="author_tree")
        raise ToolFailed(str(e)) from e
    _save(ctx, state)
    present(ctx, state)
    return state


async def revise_tree(ctx: Ctx, feedback: str) -> dict:
    import gated_pipeline as GP
    state = load_state(ctx.run_dir)
    ctx.emit("stage_started", stage="tree")
    try:
        state = await GP.resume(state, "revise", feedback, client=ctx.client, out_dir=ctx.work)
    except Exception as e:                             # noqa: BLE001
        ctx.emit("stage_failed", stage="tree", error=f"{type(e).__name__}: {e}",
                 reason="error", retry="review")
        raise ToolFailed(str(e)) from e
    _save(ctx, state)
    present(ctx, state)
    return state


async def review_again(ctx: Ctx) -> dict:
    state = load_state(ctx.run_dir)
    present(ctx, state)
    return state


async def approve_tree(ctx: Ctx, prompt: str) -> str:
    import gated_pipeline as GP
    state = await GP.resume(load_state(ctx.run_dir), "approve", client=ctx.client,
                            out_dir=ctx.work)
    _save(ctx, state)
    path = os.path.join(ctx.run_dir, "tree.json")
    _dump(tree_file(state, prompt), path)
    sheet = os.path.join(ctx.work, f"tree_round{state['round']}.png")
    files = [ctx.rel(p) for p in (sheet, path) if os.path.exists(p)]
    ctx.emit("stage_output", stage="tree", round=state["round"], files=files,
             summary={"approved": True})
    return path
```

- [ ] **Step 4: Run tests**

Run: `PYTHONPATH=.:tests:../app/server $PY -m pytest ../app/server/tests -q -p no:cacheprovider`
Expected: all PASS. If the summary flap count differs because `BIRD["leaves"]` is not the field gated_pipeline keeps, read `state["tree"]` in the test's state.json and use that tree's `leaves`. Do NOT hard-code a number.

- [ ] **Step 5: Commit**

```bash
git add app/server
git commit -m "app: mesh, tree-review and approve tools

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: The fold in a spawned child process, and the `fold` tool

**Files:**
- Create: `app/server/pleatwright_app/foldproc.py`
- Modify: `app/server/pleatwright_app/tools.py` (append `fold`)
- Test: `app/server/tests/test_foldproc.py`

**Interfaces:**
- Consumes: `pipeline.run(on_stage=)` (Task 1); `export.write_model_fold` (Task 2); `Ctx`, `ToolFailed` (Task 5).
- Produces:
  - `foldproc.FoldJob(tree_path, out_dir, *, certify_global=True)` with `.start()`, `async .messages()`, `.cancel()` and `.proc`. `messages()` yields tuples:
    - `("stage", pipeline_stage, info)`
    - `("failed", pipeline_stage, error_text)`
    - `("done", None, {"folder", "grid", "solving_ff", "shaping_ff", "global_verdict", "secs"})`
  - `tools.fold(ctx, *, certify_global=True) -> dict` emits `packing`, `solve`, `shape` and `model` stage events, then `run_finished`. UI stage map: load/packing → packing, solving → solve, shaping → shape, output → model. `model`'s files are `["model.fold", "<Folder>/overview.png"]`.

- [ ] **Step 1: Write the failing tests**

`app/server/tests/test_foldproc.py`:
```python
"""The fold tool, on artifact tree bird_1 (about 6 s per fold)."""
import asyncio
import json
import os
import shutil

from artifact_trees import path as artifact_path
from pleatwright_app import tools as T
from pleatwright_app.events import EventLog
from pleatwright_app.foldproc import FoldJob


def _ctx(tmp_path):
    d = tmp_path / "run"
    d.mkdir()
    shutil.copyfile(artifact_path("bird_1"), d / "tree.json")
    return T.Ctx(str(d), EventLog(str(d / "events.jsonl")), None, asyncio.get_running_loop())


def test_fold_emits_each_stage_then_finishes(tmp_path):
    async def main():
        ctx = _ctx(tmp_path)
        await T.fold(ctx, certify_global=False)
        return ctx
    ctx = asyncio.run(main())
    seq = [(e["type"], e.get("stage")) for e in ctx.log.events]
    assert seq == [("stage_started", "packing"), ("stage_output", "packing"),
                   ("stage_started", "solve"), ("stage_output", "solve"),
                   ("stage_started", "shape"), ("stage_output", "shape"),
                   ("stage_started", "model"), ("stage_output", "model"),
                   ("run_finished", None)]
    out = {e["stage"]: e for e in ctx.log.events if e["type"] == "stage_output"}
    assert out["packing"]["files"] == ["Bird roll 1_40/packing_cp.svg"]
    assert out["packing"]["summary"]["grid"] == 40
    assert out["model"]["files"] == ["model.fold", "Bird roll 1_40/overview.png"]
    for e in out.values():
        for f in e["files"]:
            assert os.path.isfile(os.path.join(ctx.run_dir, f))
    fin = ctx.log.last
    assert fin["folder"] == "Bird roll 1_40" and fin["grid"] == 40
    assert json.load(open(os.path.join(ctx.run_dir, "model.fold")))["file_spec"] == 1.1


def test_a_failing_fold_is_logged_with_retry_fold(tmp_path):
    async def main():
        ctx = _ctx(tmp_path)
        os.remove(os.path.join(ctx.run_dir, "tree.json"))
        try:
            await T.fold(ctx, certify_global=False)
        except T.ToolFailed:
            pass
        return ctx
    last = asyncio.run(main()).log.last
    assert last["type"] == "stage_failed" and last["stage"] == "packing"
    assert last["retry"] == "fold" and last["reason"] == "error"


def test_cancel_kills_the_child_process(tmp_path):
    async def main():
        d = tmp_path / "run"
        d.mkdir()
        shutil.copyfile(artifact_path("starfish_1"), d / "tree.json")
        job = FoldJob(str(d / "tree.json"), str(d), certify_global=True)
        job.start()
        await asyncio.sleep(1.0)
        job.cancel()
        return job.proc
    proc = asyncio.run(main())
    assert not proc.is_alive() and proc.exitcode != 0
```

- [ ] **Step 2: Run to verify failure**

Run: `PYTHONPATH=.:tests:../app/server $PY -m pytest ../app/server/tests/test_foldproc.py -q -p no:cacheprovider`
Expected: FAIL, `No module named 'pleatwright_app.foldproc'`.

- [ ] **Step 3: Implement**

`app/server/pleatwright_app/foldproc.py`:
```python
"""The fold in a SPAWNED child process (spec §3.3): a process can be killed on
Cancel, a thread cannot, and fork deadlocks are on record in this repo. The
child's `on_stage` events come back through a multiprocessing queue."""
from __future__ import annotations

import asyncio
import json
import multiprocessing as mp
import os
import queue as _queue


def _safe(x):
    return json.loads(json.dumps(x, default=str))


def _child(tree_path: str, out_dir: str, q, certify_global: bool) -> None:
    import pleatwright_app  # noqa: F401  -- puts mcp_harness on sys.path in the child
    stage = "load"
    try:
        from pleatwright import export as EX
        from pleatwright import pipeline as PL

        def on_stage(s, info):
            nonlocal stage
            stage = s
            info = dict(info)
            cand = info.pop("candidate", None)
            if s == "shaping":
                EX.write_model_fold(os.path.join(out_dir, "model.fold"), cand)
            q.put(("stage", s, _safe(info)))
        rec = PL.run(tree_path, out_dir, certify_global=certify_global, verbose=False,
                     on_stage=on_stage)
    except Exception as e:                             # noqa: BLE001 -- reported, not raised
        cause = e.__cause__ or e
        q.put(("failed", getattr(e, "stage", stage), f"{type(cause).__name__}: {cause}"))
        return
    if "failure" in rec:
        q.put(("failed", rec["failure"],
               f"no packing candidate built a base ({rec.get('pack_tried')} tried)"))
        return
    q.put(("done", None, _safe({
        "folder": rec["folder"], "grid": rec["grid_size"],
        "solving_ff": rec["solving_flat_foldable"], "shaping_ff": rec["shaping_flat_foldable"],
        "global_verdict": rec["global_verdict"], "secs": rec["total_secs"]})))


class FoldJob:
    def __init__(self, tree_path: str, out_dir: str, *, certify_global: bool = True):
        ctx = mp.get_context("spawn")
        self.q = ctx.Queue()
        self.proc = ctx.Process(target=_child, args=(tree_path, out_dir, self.q, certify_global),
                                daemon=True)

    def start(self) -> None:
        self.proc.start()

    async def messages(self):
        while True:
            try:
                msg = await asyncio.to_thread(self.q.get, True, 0.25)
            except _queue.Empty:
                if self.proc.is_alive():
                    continue
                try:
                    msg = self.q.get_nowait()
                except _queue.Empty:
                    yield ("failed", "load", f"the fold process exited with code {self.proc.exitcode}")
                    return
            yield msg
            if msg[0] in ("done", "failed"):
                self.proc.join(5)
                return

    def cancel(self) -> None:
        if self.proc.is_alive():
            self.proc.kill()
        self.proc.join(5)
```

Append to `tools.py`:
```python
_UI_STAGE = {"load": "packing", "packing": "packing", "solving": "solve",
             "shaping": "shape", "output": "model"}
_NEXT = {"packing": "solve", "solving": "shape", "shaping": "model"}


async def fold(ctx: Ctx, *, certify_global: bool = True) -> dict:
    from .foldproc import FoldJob
    ctx.emit("stage_started", stage="packing")
    job = FoldJob(os.path.join(ctx.run_dir, "tree.json"), ctx.run_dir,
                  certify_global=certify_global)
    job.start()
    try:
        async for kind, stage, info in job.messages():
            if kind == "stage":
                files = [ctx.rel(p) for p in info.pop("files")]
                info.pop("folder", None)
                if stage == "output":
                    files = ["model.fold", *files]
                ctx.emit("stage_output", stage=_UI_STAGE[stage], files=files, summary=info)
                if stage in _NEXT:
                    ctx.emit("stage_started", stage=_UI_STAGE[_NEXT[stage]])
            elif kind == "failed":
                ctx.emit("stage_failed", stage=_UI_STAGE.get(stage, "packing"), error=info,
                         reason="error", retry="fold")
                raise ToolFailed(info)
            else:
                info["folder"] = ctx.rel(info["folder"])
                ctx.emit("run_finished", **info)
                return info
    except asyncio.CancelledError:
        job.cancel()
        raise
    raise ToolFailed("the fold ended without a result")
```

- [ ] **Step 4: Run tests**

Run: `PYTHONPATH=.:tests:../app/server $PY -m pytest ../app/server/tests -q -p no:cacheprovider`
Expected: all PASS (about 20 s).

- [ ] **Step 5: Commit**

```bash
git add app/server
git commit -m "app: fold tool in a spawned, killable child process

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Guided flow manager: one active run, retry, cancel, restart recovery

**Files:**
- Create: `app/server/pleatwright_app/guided.py`
- Test: `app/server/tests/test_guided.py`

**Interfaces:**
- Consumes: `RunStore` (Task 4); tools (Tasks 5-6).
- Produces:
  - `guided.Refused(Exception)`, the user-facing reason an action was not taken.
  - `guided.Manager(store, client_factory, *, certify_global=True)` with:
    - `.llm_error() -> str | None`, which builds the client on first success and keeps it
    - `.busy() -> str | None` (the active run id)
    - `.recover() -> None`
    - `async .create(prompt) -> run_id`
    - `async .message(run_id, text)`, `async .approve(run_id)`, `async .retry(run_id)`, `async .cancel(run_id)`
    - `async .wait_idle()`
  - `guided.phase(log) -> {"phase": "new" | "review" | "failed" | "done" | "running", "can_approve"?: bool, "retry"?: str | None}`
  - `guided.current_stage(log) -> str | None`
- `client_factory()` must raise `pleatwright.__main__.ConfigError` when the client cannot be configured (the CLI's `_client` does).

- [ ] **Step 1: Write the failing tests**

`app/server/tests/test_guided.py`:
```python
import asyncio
import os

import pytest

from artifact_trees import authored
from pleatwright.__main__ import ConfigError
from pleatwright_app.guided import Manager, Refused, phase
from pleatwright_app.runs import RunStore
from test_gated_pipeline import FakeClient

BIRD = authored("bird_1")


class LoopRecordingClient(FakeClient):
    """Records the event loop of every VLM call (the #198 one-loop lesson)."""
    def __init__(self, payloads):
        super().__init__(payloads)
        self.loops = []

    async def run_turn(self, system, messages, tools):
        self.loops.append(id(asyncio.get_running_loop()))
        return await super().run_turn(system, messages, tools)


def _types(log):
    return [e["type"] for e in log.events]


def test_a_whole_guided_run(offline):
    client = LoopRecordingClient([BIRD, BIRD])

    async def main():
        m = Manager(RunStore(str(offline / "runs")), lambda: client, certify_global=False)
        rid = await m.create("a bird")
        await m.wait_idle()
        log = m.store.log(rid)
        assert phase(log) == {"phase": "review", "can_approve": True}
        await m.message(rid, "make the tail longer")
        await m.wait_idle()
        await m.approve(rid)
        await m.wait_idle()
        return m, rid
    m, rid = asyncio.run(main())
    log = m.store.log(rid)
    assert log.last["type"] == "run_finished"
    assert [e["text"] for e in log.events if e["type"] == "user_message"] == \
        ["a bird", "make the tail longer", "Approve"]
    assert len(client.calls) == 2 and len(set(client.loops)) == 1


def test_config_error_refuses_before_any_run_or_mesh(offline):
    def factory():
        raise ConfigError("provider 'claude' requires an API key; set ANTHROPIC_API_KEY")

    async def main():
        m = Manager(RunStore(str(offline / "runs")), factory)
        with pytest.raises(Refused, match="API key"):
            await m.create("a bird")
        return m
    m = asyncio.run(main())
    assert m.store.list() == []
    assert not os.path.exists(offline / "meshes")


def test_one_active_run_at_a_time(offline):
    async def main():
        m = Manager(RunStore(str(offline / "runs")), lambda: FakeClient([BIRD, BIRD]))
        await m.create("a bird")
        with pytest.raises(Refused, match="already running"):
            await m.create("a crab")
        await m.wait_idle()
    asyncio.run(main())


def test_messages_outside_review_are_refused(offline):
    async def main():
        m = Manager(RunStore(str(offline / "runs")), lambda: FakeClient([None]))
        rid = await m.create("a bird")
        await m.wait_idle()                          # a failed round: nothing to approve
        with pytest.raises(Refused, match="nothing to approve"):
            await m.approve(rid)
    asyncio.run(main())


def test_cancel_during_the_fold_logs_cancelled_with_retry(offline):
    async def main():
        m = Manager(RunStore(str(offline / "runs")), lambda: FakeClient([BIRD]))
        rid = await m.create("a bird")
        await m.wait_idle()
        await m.approve(rid)
        log = m.store.log(rid)
        while not any(e["type"] == "stage_started" and e["stage"] == "packing" for e in log.events):
            await asyncio.sleep(0.05)
        await m.cancel(rid)
        await m.wait_idle()
        return log
    last = asyncio.run(main()).last
    assert last["type"] == "stage_failed" and last["reason"] == "cancelled"
    assert last["retry"] == "fold"


def test_retry_runs_the_failed_stage_again(offline):
    async def main():
        m = Manager(RunStore(str(offline / "runs")), lambda: FakeClient([BIRD]),
                    certify_global=False)
        rid = await m.create("a bird")
        await m.wait_idle()
        await m.approve(rid)
        log = m.store.log(rid)
        while not any(e["type"] == "stage_started" and e["stage"] == "packing" for e in log.events):
            await asyncio.sleep(0.05)
        await m.cancel(rid)
        await m.wait_idle()
        await m.retry(rid)
        await m.wait_idle()
        return log
    assert asyncio.run(main()).last["type"] == "run_finished"


def test_recover_marks_interrupted_runs_and_keeps_paused_reviews(offline):
    store = RunStore(str(offline / "runs"))
    a = store.create("a bird")
    store.log(a).append("stage_started", stage="mesh")
    b = store.create("a crab")
    store.log(b).append("awaiting_review", round=0, can_approve=True)
    Manager(store, lambda: None).recover()
    la, lb = store.log(a).last, store.log(b).last
    assert la["type"] == "stage_failed" and la["reason"] == "interrupted"
    assert la["stage"] == "mesh" and la["retry"] == "make_mesh"
    assert lb["type"] == "awaiting_review"
```

- [ ] **Step 2: Run to verify failure**

Run: `PYTHONPATH=.:tests:../app/server $PY -m pytest ../app/server/tests/test_guided.py -q -p no:cacheprovider`
Expected: FAIL, `No module named 'pleatwright_app.guided'`.

- [ ] **Step 3: Implement**

`app/server/pleatwright_app/guided.py`:
```python
"""Guided mode (spec §4.2): a fixed script over the tools. One run computes at
a time; every state the UI shows is derived from the run's event log, so a
restart loses nothing but the work in flight."""
from __future__ import annotations

import asyncio

from pleatwright.__main__ import ConfigError

from . import tools as T

_TERMINAL = ("run_finished", "stage_failed", "awaiting_review")


class Refused(Exception):
    """The action was not taken; the message says why (shown to the user)."""


def phase(log) -> dict:
    last = log.last
    if last is None or last["type"] == "run_created":
        return {"phase": "new"}
    t = last["type"]
    if t == "awaiting_review":
        return {"phase": "review", "can_approve": bool(last["can_approve"])}
    if t == "stage_failed":
        return {"phase": "failed", "retry": last.get("retry")}
    if t == "run_finished":
        return {"phase": "done"}
    return {"phase": "running"}


def current_stage(log) -> str | None:
    open_ = None
    for e in log.events:
        if e["type"] == "stage_started":
            open_ = e["stage"]
        elif e["type"] in ("stage_output", "stage_failed", "awaiting_review"):
            if e.get("stage", "tree") == open_:
                open_ = None
    return open_


class Manager:
    def __init__(self, store, client_factory, *, certify_global: bool = True):
        self.store = store
        self.client_factory = client_factory
        self.certify_global = certify_global
        self.client = None
        self._active: tuple[str, asyncio.Task, T.Ctx] | None = None

    # ---- state ---------------------------------------------------------------
    def llm_error(self) -> str | None:
        if self.client is not None:
            return None
        try:
            self.client = self.client_factory()
        except ConfigError as e:
            return str(e)
        return None

    def busy(self) -> str | None:
        if self._active and not self._active[1].done():
            return self._active[0]
        return None

    def recover(self) -> None:
        for row in self.store.list():
            log = self.store.log(row["id"])
            if log.last and log.last["type"] not in _TERMINAL:
                stage = current_stage(log) or "image"
                log.append("stage_failed", stage=stage,
                           error="the server stopped while this stage was running",
                           reason="interrupted",
                           retry=T.retry_for(stage, self.store.dir(row["id"])))

    # ---- actions -------------------------------------------------------------
    async def create(self, prompt: str) -> str:
        err = self.llm_error()
        if err:
            raise Refused(f"authoring is disabled: {err}")
        self._refuse_if_busy()
        rid = self.store.create(prompt)
        self.store.log(rid).append("user_message", text=prompt)

        async def flow(ctx):
            await T.make_mesh(ctx, prompt)
            await T.author_tree(ctx)
        self._start(rid, flow)
        return rid

    async def message(self, rid: str, text: str) -> None:
        self._refuse_if_busy()
        if phase(self.store.log(rid))["phase"] != "review":
            raise Refused("the tree is not waiting for review")
        self.store.log(rid).append("user_message", text=text)
        self._start(rid, lambda ctx: T.revise_tree(ctx, text))

    async def approve(self, rid: str) -> None:
        self._refuse_if_busy()
        ph = phase(self.store.log(rid))
        if ph["phase"] != "review" or not ph["can_approve"]:
            raise Refused("there is nothing to approve: this round produced no tree")
        log = self.store.log(rid)
        log.append("user_message", text="Approve")
        prompt = log.events[0]["prompt"]

        async def flow(ctx):
            await T.approve_tree(ctx, prompt)
            await T.fold(ctx, certify_global=self.certify_global)
        self._start(rid, flow)

    async def retry(self, rid: str) -> None:
        self._refuse_if_busy()
        log = self.store.log(rid)
        ph = phase(log)
        if ph["phase"] != "failed" or not ph.get("retry"):
            raise Refused("there is nothing to retry")
        prompt = log.events[0]["prompt"]
        tool = ph["retry"]

        async def flow(ctx):
            if tool == "make_mesh":
                await T.make_mesh(ctx, prompt)
                await T.author_tree(ctx)
            elif tool == "author_tree":
                await T.author_tree(ctx)
            elif tool == "review":
                await T.review_again(ctx)
            else:
                await T.fold(ctx, certify_global=self.certify_global)
        self._start(rid, flow)

    async def cancel(self, rid: str) -> None:
        if self.busy() != rid:
            raise Refused("nothing is running in this run")
        self._active[2].cancelled.set()
        self._active[1].cancel()

    async def wait_idle(self) -> None:
        if self._active:
            await asyncio.gather(self._active[1], return_exceptions=True)

    # ---- internals -----------------------------------------------------------
    def _refuse_if_busy(self) -> None:
        b = self.busy()
        if b:
            raise Refused(f"another run is already running ({b}); wait or cancel it")

    def _start(self, rid: str, flow) -> None:
        if self.client is None:
            self.llm_error()
        ctx = T.Ctx(self.store.dir(rid), self.store.log(rid), self.client,
                    asyncio.get_running_loop())

        async def runner():
            try:
                await flow(ctx)
            except T.ToolFailed:
                pass
            except asyncio.CancelledError:
                ctx.cancelled.set()
                stage = current_stage(ctx.log) or "image"
                ctx.emit("stage_failed", stage=stage, error="cancelled", reason="cancelled",
                         retry=T.retry_for(stage, ctx.run_dir))
            except Exception as e:                     # noqa: BLE001 -- never lose a run silently
                stage = current_stage(ctx.log) or "image"
                ctx.emit("stage_failed", stage=stage, error=f"{type(e).__name__}: {e}",
                         reason="error", retry=T.retry_for(stage, ctx.run_dir))
        self._active = (rid, asyncio.create_task(runner()), ctx)
```

Note: `Ctx.cancelled` is set before `task.cancel()`, so mesh progress callbacks still arriving from the worker thread are dropped.

- [ ] **Step 4: Run tests**

Run: `PYTHONPATH=.:tests:../app/server $PY -m pytest ../app/server/tests -q -p no:cacheprovider`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add app/server
git commit -m "app: guided flow manager (one active run, retry, cancel, restart recovery)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: HTTP and WebSocket API, `python -m pleatwright_app`, and the recorded event fixture

**Files:**
- Create: `app/server/pleatwright_app/api.py`, `__main__.py`, `app/server/record_fixture.py`
- Create: `app/web/src/__fixtures__/bird_run.events.jsonl` (generated)
- Test: `app/server/tests/test_api.py`

**Interfaces:**
- Consumes: `Manager`, `Refused`, `phase` (Task 7); `RunStore`, `default_root` (Task 4).
- Produces: `api.create_app(*, runs_dir=None, client_factory=None, certify_global=True, static_dir=None) -> FastAPI`. Routes:
  - `GET /status` → `{"llm_ok": bool, "llm_error": str | null, "busy": run_id | null}`
  - `GET /runs` → `RunStore.list()` rows
  - `POST /runs {"prompt"}` → `{"id"}`; 409 `{"detail"}` when refused
  - `GET /runs/{id}/files/{path:path}` → the file; 404 outside the run or missing
  - `WS /ws/runs/{id}?after=<seq>` sends every event with `seq > after`, then live events, plus non-event `{"type": "error", "message"}` frames. It receives `{"type": "message", "text"}`, `{"type": "approve"}`, `{"type": "retry"}` and `{"type": "cancel"}`. A disallowed `Origin` is closed with code 1008.
  - The built UI is mounted at `/` when `static_dir` exists.
- The client is created in the lifespan, on the server's loop.

- [ ] **Step 1: Write the failing tests**

`app/server/tests/test_api.py`:
```python
import os

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from artifact_trees import authored
from pleatwright.__main__ import ConfigError
from pleatwright_app.api import create_app
from test_gated_pipeline import FakeClient

BIRD = authored("bird_1")


def _app(tmp, factory=None):
    return create_app(runs_dir=str(tmp / "runs"), certify_global=False,
                      client_factory=factory or (lambda: FakeClient([BIRD, BIRD])))


def _until(ws, pred):
    seen = []
    while True:
        m = ws.receive_json()
        seen.append(m)
        if pred(m):
            return seen


def test_a_whole_run_over_the_websocket_and_replay(offline):
    with TestClient(_app(offline)) as c:
        assert c.get("/status").json() == {"llm_ok": True, "llm_error": None, "busy": None}
        rid = c.post("/runs", json={"prompt": "a bird"}).json()["id"]
        with c.websocket_connect(f"/ws/runs/{rid}?after=-1") as ws:
            _until(ws, lambda m: m.get("type") == "awaiting_review")
            ws.send_json({"type": "message", "text": "make the tail longer"})
            _until(ws, lambda m: m.get("type") == "awaiting_review")
            ws.send_json({"type": "approve"})
            seen = _until(ws, lambda m: m.get("type") == "run_finished")
        assert any(m.get("stage") == "model" and m["type"] == "stage_output" for m in seen)
        # replay from 5 returns exactly the persisted tail
        with c.websocket_connect(f"/ws/runs/{rid}?after=5") as ws:
            first = ws.receive_json()
        assert first["seq"] == 6
        rows = c.get("/runs").json()
        assert rows[0]["id"] == rid and rows[0]["status"] == "done"
        r = c.get(f"/runs/{rid}/files/model.fold")
        assert r.status_code == 200 and r.json()["file_spec"] == 1.1


def test_files_outside_the_run_are_404(offline):
    with TestClient(_app(offline)) as c:
        rid = c.post("/runs", json={"prompt": "a bird"}).json()["id"]
        for bad in ("../../etc/passwd", "%2e%2e/%2e%2e/secret", "nope.png"):
            assert c.get(f"/runs/{rid}/files/{bad}").status_code == 404


def test_config_error_shows_in_status_and_refuses_new_runs(offline):
    def factory():
        raise ConfigError("provider 'claude' requires an API key; set ANTHROPIC_API_KEY")
    with TestClient(_app(offline, factory)) as c:
        s = c.get("/status").json()
        assert s["llm_ok"] is False and "ANTHROPIC_API_KEY" in s["llm_error"]
        r = c.post("/runs", json={"prompt": "a bird"})
        assert r.status_code == 409 and "authoring is disabled" in r.json()["detail"]


def test_foreign_origins_are_rejected(offline):
    with TestClient(_app(offline)) as c:
        rid = c.post("/runs", json={"prompt": "a bird"}).json()["id"]
        with pytest.raises(WebSocketDisconnect) as e:
            with c.websocket_connect(f"/ws/runs/{rid}", headers={"origin": "https://evil.example"}) as ws:
                ws.receive_json()
        assert e.value.code == 1008
        with c.websocket_connect(f"/ws/runs/{rid}", headers={"origin": "http://localhost:5173"}) as ws:
            assert ws.receive_json()["seq"] == 0


def test_refusals_come_back_as_error_frames_not_events(offline):
    with TestClient(_app(offline)) as c:
        rid = c.post("/runs", json={"prompt": "a bird"}).json()["id"]
        with c.websocket_connect(f"/ws/runs/{rid}") as ws:
            _until(ws, lambda m: m.get("type") == "awaiting_review")
            ws.send_json({"type": "retry"})
            err = _until(ws, lambda m: m.get("type") == "error")[-1]
        assert "nothing to retry" in err["message"]
```

- [ ] **Step 2: Run to verify failure**

Run: `PYTHONPATH=.:tests:../app/server $PY -m pytest ../app/server/tests/test_api.py -q -p no:cacheprovider`
Expected: FAIL, `No module named 'pleatwright_app.api'`.

- [ ] **Step 3: Implement**

`app/server/pleatwright_app/api.py`:
```python
"""HTTP + WebSocket front of the app (spec §3.2, §6). Binds 127.0.0.1 only
(see __main__); keys never reach the browser."""
from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .guided import Manager, Refused
from .runs import RunStore, default_root


class NewRun(BaseModel):
    prompt: str


def _origin_ok(origin: str | None) -> bool:
    if not origin:                     # not a browser: no cross-site risk
        return True
    u = urlparse(origin)
    return u.scheme == "http" and u.hostname in ("127.0.0.1", "localhost")


def create_app(*, runs_dir=None, client_factory=None, certify_global=True, static_dir=None):
    if client_factory is None:
        from pleatwright.__main__ import _client as client_factory
    store = RunStore(runs_dir or default_root())
    manager = Manager(store, client_factory, certify_global=certify_global)

    @asynccontextmanager
    async def lifespan(app):
        import env_config
        env_config.load_env()
        manager.recover()
        manager.llm_error()            # builds the client HERE, on the server's loop
        yield
        if manager.busy():
            await manager.cancel(manager.busy())
            await manager.wait_idle()

    app = FastAPI(lifespan=lifespan)
    app.state.manager = manager

    @app.get("/status")
    def status():
        err = manager.llm_error()
        return {"llm_ok": err is None, "llm_error": err, "busy": manager.busy()}

    @app.get("/runs")
    def runs():
        return store.list()

    @app.post("/runs")
    async def new_run(body: NewRun):
        try:
            return {"id": await manager.create(body.prompt)}
        except Refused as e:
            raise HTTPException(409, str(e))

    @app.get("/runs/{run_id}/files/{rel:path}")
    def file(run_id: str, rel: str):
        try:
            return FileResponse(store.file(run_id, rel))
        except FileNotFoundError:
            raise HTTPException(404, "not found")

    @app.websocket("/ws/runs/{run_id}")
    async def ws_run(ws: WebSocket, run_id: str, after: int = -1):
        if not _origin_ok(ws.headers.get("origin")):
            await ws.close(code=1008)
            return
        try:
            log = store.log(run_id)
        except FileNotFoundError:
            await ws.close(code=1008)
            return
        await ws.accept()
        lock = asyncio.Lock()
        q = log.subscribe()
        backlog = log.after(after)     # same tick as subscribe: no gap, no duplicate

        async def send(m):
            async with lock:
                await ws.send_json(m)

        async def pump():
            last = after
            for ev in backlog:
                await send(ev)
                last = ev["seq"]
            while True:
                ev = await q.get()
                if ev["seq"] > last:
                    await send(ev)
                    last = ev["seq"]

        task = asyncio.create_task(pump())
        actions = {"message": lambda m: manager.message(run_id, m.get("text", "")),
                   "approve": lambda m: manager.approve(run_id),
                   "retry": lambda m: manager.retry(run_id),
                   "cancel": lambda m: manager.cancel(run_id)}
        try:
            while True:
                m = await ws.receive_json()
                act = actions.get(m.get("type"))
                try:
                    if act is None:
                        raise Refused(f"unknown action {m.get('type')!r}")
                    await act(m)
                except Refused as e:
                    await send({"type": "error", "message": str(e)})
        except WebSocketDisconnect:
            pass
        finally:
            task.cancel()
            log.unsubscribe(q)

    if static_dir and os.path.isdir(static_dir):
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="ui")
    return app
```

`app/server/pleatwright_app/__main__.py`:
```python
"""python -m pleatwright_app [--port 8000] [--no-ui]  ->  http://127.0.0.1:<port>"""
import argparse
import os


def main(argv=None) -> None:
    import uvicorn

    from .api import create_app
    ap = argparse.ArgumentParser(prog="python -m pleatwright_app")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--no-ui", action="store_true", help="API only (use with `npm run dev`)")
    a = ap.parse_args(argv)
    dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "web", "dist"))
    uvicorn.run(create_app(static_dir=None if a.no_ui else dist), host="127.0.0.1", port=a.port)


if __name__ == "__main__":
    main()
```

`app/server/record_fixture.py`:
```python
"""Record a fake-provider guided run's events for the frontend tests (spec §7).

    cd mcp_harness && PYTHONPATH=.:tests:../app/server $PY ../app/server/record_fixture.py

Artifact tree bird_1 (owner rule). Writes app/web/src/__fixtures__/bird_run.events.jsonl
with timestamps kept, so the frontend replays exactly what the server emits."""
import asyncio
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, "..", "..", "mcp_harness"),
                os.path.join(HERE, "..", "..", "mcp_harness", "tests")]
os.environ.setdefault("IDE_MESH_PROVENANCE", "0")
os.environ["MESH_PROVIDER"] = "fake"

import gated_pipeline as GP                                       # noqa: E402
import mesh_acquire                                               # noqa: E402
from artifact_trees import authored                               # noqa: E402
from pleatwright_app.guided import Manager                        # noqa: E402
from pleatwright_app.runs import RunStore                         # noqa: E402
from test_gated_pipeline import FakeClient, _fake_mesh_views      # noqa: E402
import pathlib                                                    # noqa: E402

OUT = os.path.join(HERE, "..", "web", "src", "__fixtures__", "bird_run.events.jsonl")


async def main(tmp, write_fixture=True):
    mesh_acquire.output_dir = lambda: os.path.join(tmp, "meshes")
    GP.vlm_render.render_mesh_views = lambda *a, **k: _fake_mesh_views(pathlib.Path(tmp))
    bird = authored("bird_1")
    m = Manager(RunStore(os.path.join(tmp, "runs")), lambda: FakeClient([bird, bird]))
    rid = await m.create("a bird")
    await m.wait_idle()
    await m.message(rid, "make the tail longer")
    await m.wait_idle()
    await m.approve(rid)
    await m.wait_idle()
    if write_fixture:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        shutil.copyfile(os.path.join(m.store.dir(rid), "events.jsonl"), OUT)
        print("wrote", os.path.relpath(OUT))
    else:
        print("kept run", m.store.dir(rid))


if __name__ == "__main__":
    if len(sys.argv) > 1:          # keep the run to browse it: PLEATWRIGHT_RUNS_DIR=<dir>/runs
        os.makedirs(sys.argv[1], exist_ok=True)
        asyncio.run(main(sys.argv[1], write_fixture=False))
    else:
        with tempfile.TemporaryDirectory() as t:
            asyncio.run(main(t))
```

Also append a drift guard to `test_api.py`:
```python
def test_the_recorded_frontend_fixture_matches_what_the_server_emits(offline):
    import json
    import pathlib
    fx = pathlib.Path(__file__).parents[2] / "web" / "src" / "__fixtures__" / "bird_run.events.jsonl"
    want = [(e["type"], e.get("stage")) for e in map(json.loads, fx.read_text().splitlines())]
    with TestClient(_app(offline)) as c:
        rid = c.post("/runs", json={"prompt": "a bird"}).json()["id"]
        with c.websocket_connect(f"/ws/runs/{rid}") as ws:
            _until(ws, lambda m: m.get("type") == "awaiting_review")
            ws.send_json({"type": "message", "text": "make the tail longer"})
            _until(ws, lambda m: m.get("type") == "awaiting_review")
            ws.send_json({"type": "approve"})
            _until(ws, lambda m: m.get("type") == "run_finished")
        got = [(e["type"], e.get("stage")) for e in c.app.state.manager.store.log(rid).events]
    assert got == want, "re-run app/server/record_fixture.py and commit the fixture"
```

- [ ] **Step 4: Record the fixture, then run all app tests**

Run: `cd mcp_harness && PYTHONPATH=.:tests:../app/server $PY ../app/server/record_fixture.py`
Expected: `wrote ../app/web/src/__fixtures__/bird_run.events.jsonl`. The file should be about 25 lines, the last being `run_finished`.

Run: `PYTHONPATH=.:tests:../app/server $PY -m pytest ../app/server/tests -q -p no:cacheprovider`
Expected: all PASS.

- [ ] **Step 5: Smoke-start the real server**

Run, in the background, from `mcp_harness/`: `PYTHONPATH=.:../app/server $PY -m pleatwright_app --no-ui --port 8765`. Then run `curl -s http://127.0.0.1:8765/status` and stop the server.
Expected: the JSON has `"llm_ok"` and no key material. With the repo-root `.env`'s stale `ANTHROPIC_WORKSPACE_ID` still present, `llm_ok` can be `true` here, because the 404 only appears on a real call. That is acceptance Task 13's concern.

- [ ] **Step 6: Commit**

```bash
git add app/server app/web/src/__fixtures__/bird_run.events.jsonl
git commit -m "app: HTTP + WebSocket API, server entry point, recorded event fixture

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Web scaffold, event types, the `runStore` reducer, and the API client

**Files:**
- Create: `app/web/package.json`, `index.html`, `tsconfig.json`, `vite.config.ts`, `.gitignore`
- Create: `app/web/src/types.ts`, `runStore.ts`, `runStore.test.ts`, `api.ts`
- Generated: `app/web/package-lock.json`

**Interfaces:**
- Consumes: the event shapes of spec §3.2 and the recorded fixture (Task 8).
- Produces (`types.ts`, `runStore.ts`, `api.ts`), used by Tasks 10-11:
  - `STAGES: StageId[]`; `StageStatus`; `Output {key, stage, round?, files, summary, seq}`; `ChatItem`; `RunView`
  - `emptyView(id): RunView`; `reduce(view, action): RunView`, where `action` is `{type:"event", event} | {type:"select", key} | {type:"follow"}`
  - `selectedOutput(view): Output | null`; `latestByStage(view): Partial<Record<StageId, Output>>`; `summaryLine(o: Output): string`; `outputTitle(o: Output): string`
  - `api.getStatus()`, `api.listRuns()`, `api.createRun(prompt)`, `api.fileUrl(runId, rel)`, `api.connectRun(runId, onEvent, onError) -> {send(cmd), close()}`

- [ ] **Step 1: Scaffold**

`app/web/package.json`:
```json
{
  "name": "pleatwright-app",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc --noEmit && vite build",
    "test": "vitest run"
  },
  "dependencies": {
    "@react-three/drei": "9.122.0",
    "@react-three/fiber": "8.18.0",
    "react": "18.3.1",
    "react-dom": "18.3.1",
    "three": "0.169.0"
  },
  "devDependencies": {
    "@types/react": "18.3.12",
    "@types/react-dom": "18.3.1",
    "@types/three": "0.169.0",
    "@vitejs/plugin-react": "4.3.4",
    "typescript": "5.6.3",
    "vite": "5.4.11",
    "vitest": "2.1.8"
  }
}
```

`app/web/.gitignore`:
```
node_modules/
dist/
```

`app/web/index.html`:
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Pleatwright</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

`app/web/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noEmit": true,
    "skipLibCheck": true,
    "resolveJsonModule": true,
    "types": ["vite/client"]
  },
  "include": ["src"],
  "exclude": ["src/**/*.test.ts"]
}
```

`app/web/vite.config.ts`:
```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const api = "http://127.0.0.1:8000";
export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    proxy: {
      "/status": api,
      "/runs": api,
      "/ws": { target: "ws://127.0.0.1:8000", ws: true },
    },
  },
  test: { environment: "node" },
});
```

Run: `cd app/web && npm install`
Expected: creates `node_modules/` and `package-lock.json` with no errors.

- [ ] **Step 2: Write `types.ts`**

```ts
export const STAGES = ["image", "mesh", "tree", "packing", "solve", "shape", "model"] as const;
export type StageId = (typeof STAGES)[number];
export type StageStatus = "todo" | "running" | "done" | "waiting" | "failed" | "skipped";

export interface PwEvent {
  seq: number;
  t: string;
  type: string;
  stage?: StageId;
  [k: string]: unknown;
}

export interface Output {
  key: string;                 // `${stage}` or `tree:${round}`
  stage: StageId;
  round?: number;
  files: string[];
  summary: Record<string, unknown>;
  seq: number;
}

export type ChatItem =
  | { kind: "user"; text: string; seq: number }
  | { kind: "assistant"; text: string; seq: number }
  | { kind: "output"; key: string; seq: number }
  | { kind: "failed"; stage: StageId; error: string; reason: string; retry: string | null; seq: number };

export interface RunView {
  id: string;
  prompt: string;
  lastSeq: number;
  stages: Record<StageId, StageStatus>;
  startedAt: Partial<Record<StageId, string>>;
  outputs: Output[];
  chat: ChatItem[];
  review: { round: number; canApprove: boolean } | null;
  finished: Record<string, unknown> | null;
  failure: { stage: StageId; reason: string; retry: string | null } | null;
  running: boolean;
  selected: string | null;
  followLatest: boolean;
}

export type Action =
  | { type: "event"; event: PwEvent }
  | { type: "select"; key: string }
  | { type: "follow" };

export interface RunSummary {
  id: string; prompt: string; subject: string; created: string;
  status: "new" | "running" | "waiting" | "done" | "failed";
}
export interface Status { llm_ok: boolean; llm_error: string | null; busy: string | null }
```

- [ ] **Step 3: Write the failing reducer tests**

`app/web/src/runStore.test.ts`:
```ts
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { emptyView, latestByStage, reduce, selectedOutput, summaryLine } from "./runStore";
import type { PwEvent, RunView } from "./types";

const events: PwEvent[] = readFileSync(
  new URL("./__fixtures__/bird_run.events.jsonl", import.meta.url), "utf8")
  .trim().split("\n").map((l) => JSON.parse(l));

const replay = (n = events.length, v: RunView = emptyView("r")) =>
  events.slice(0, n).reduce((acc, e) => reduce(acc, { type: "event", event: e }), v);

const upTo = (pred: (e: PwEvent) => boolean, nth = 1) => {
  let k = 0;
  return events.findIndex((e) => pred(e) && ++k === nth) + 1;
};

describe("runStore over a recorded fake-provider run (bird_1)", () => {
  it("pauses at tree review with the first round selected", () => {
    const v = replay(upTo((e) => e.type === "awaiting_review"));
    expect(v.stages.image).toBe("skipped");          // fake provider draws no concept
    expect(v.stages.mesh).toBe("done");
    expect(v.stages.tree).toBe("waiting");
    expect(v.stages.packing).toBe("todo");
    expect(v.review).toEqual({ round: 0, canApprove: true });
    expect(selectedOutput(v)?.key).toBe("tree:0");
    expect(v.prompt).toBe("a bird");
  });

  it("a revision adds round 1 and follows it", () => {
    const v = replay(upTo((e) => e.type === "awaiting_review", 2));
    expect(v.outputs.filter((o) => o.stage === "tree").map((o) => o.round)).toEqual([0, 1]);
    expect(selectedOutput(v)?.key).toBe("tree:1");
    expect(v.chat.filter((c) => c.kind === "user").length).toBe(2);
  });

  it("approval updates round 1 in place and the fold fills every stage", () => {
    const v = replay();
    expect(v.outputs.filter((o) => o.stage === "tree").length).toBe(2);
    expect(v.stages).toEqual({ image: "skipped", mesh: "done", tree: "done", packing: "done",
                               solve: "done", shape: "done", model: "done" });
    expect(v.finished?.grid).toBe(40);
    expect(selectedOutput(v)?.stage).toBe("model");
    expect(latestByStage(v).packing?.files[0]).toMatch(/packing_cp\.svg$/);
    expect(v.running).toBe(false);
  });

  it("selecting an older output pins it until follow", () => {
    const mid = upTo((e) => e.type === "stage_output" && e.stage === "packing");
    let v = replay(mid);
    v = reduce(v, { type: "select", key: "mesh" });
    v = events.slice(mid).reduce((a, e) => reduce(a, { type: "event", event: e }), v);
    expect(selectedOutput(v)?.key).toBe("mesh");
    expect(v.followLatest).toBe(false);
    v = reduce(v, { type: "follow" });
    expect(selectedOutput(v)?.stage).toBe("model");
  });

  it("is idempotent for replayed events (reconnect overlap)", () => {
    const once = replay();
    const twice = events.reduce((a, e) => reduce(a, { type: "event", event: e }), once);
    expect(twice).toEqual(once);
  });

  it("a failure marks the stage and records the retry", () => {
    const n = upTo((e) => e.type === "stage_started" && e.stage === "packing");
    const v = reduce(replay(n), { type: "event", event: {
      seq: 999, t: "", type: "stage_failed", stage: "packing", error: "cancelled",
      reason: "cancelled", retry: "fold" } });
    expect(v.stages.packing).toBe("failed");
    expect(v.failure).toEqual({ stage: "packing", reason: "cancelled", retry: "fold" });
    expect(v.running).toBe(false);
  });

  it("summary lines", () => {
    const v = replay();
    const tree0 = v.outputs.find((o) => o.key === "tree:0")!;
    expect(summaryLine(tree0)).toMatch(/^\d+ flaps, \d+ pairs$/);
    expect(summaryLine(latestByStage(v).packing!)).toMatch(/^grid 40/);
  });
});
```

Run: `cd app/web && npm test`
Expected: FAIL with `Failed to resolve import "./runStore"`.

- [ ] **Step 4: Implement `runStore.ts`**

```ts
import { STAGES, type Action, type Output, type PwEvent, type RunView, type StageId,
         type StageStatus } from "./types";

export function emptyView(id: string): RunView {
  return {
    id, prompt: "", lastSeq: -1,
    stages: Object.fromEntries(STAGES.map((s) => [s, "todo"])) as Record<StageId, StageStatus>,
    startedAt: {}, outputs: [], chat: [], review: null, finished: null, failure: null,
    running: false, selected: null, followLatest: true,
  };
}

const keyOf = (e: PwEvent) =>
  e.stage === "tree" && typeof e.round === "number" ? `tree:${e.round}` : String(e.stage);

function applyEvent(v: RunView, e: PwEvent): RunView {
  if (e.seq <= v.lastSeq) return v;                     // replay overlap: already applied
  const n: RunView = { ...v, lastSeq: e.seq, stages: { ...v.stages },
                       startedAt: { ...v.startedAt }, outputs: [...v.outputs], chat: [...v.chat] };
  switch (e.type) {
    case "run_created":
      n.prompt = String(e.prompt ?? "");
      break;
    case "user_message":
      n.chat.push({ kind: "user", text: String(e.text ?? ""), seq: e.seq });
      n.review = null;
      n.failure = null;
      break;
    case "assistant_message":
      n.chat.push({ kind: "assistant", text: String(e.text ?? ""), seq: e.seq });
      break;
    case "stage_started":
      n.stages[e.stage!] = "running";
      n.startedAt[e.stage!] = e.t;
      n.running = true;
      n.failure = null;
      break;
    case "stage_output": {
      const o: Output = { key: keyOf(e), stage: e.stage!, files: (e.files as string[]) ?? [],
                          summary: (e.summary as Record<string, unknown>) ?? {}, seq: e.seq,
                          ...(typeof e.round === "number" ? { round: e.round } : {}) };
      const i = n.outputs.findIndex((x) => x.key === o.key);
      if (i >= 0) n.outputs[i] = o;                     // approval updates the round in place
      else {
        n.outputs.push(o);
        n.chat.push({ kind: "output", key: o.key, seq: e.seq });
      }
      n.stages[e.stage!] = o.summary.skipped ? "skipped" : "done";
      if (n.followLatest) n.selected = o.key;
      break;
    }
    case "awaiting_review":
      n.stages.tree = "waiting";
      n.review = { round: Number(e.round), canApprove: Boolean(e.can_approve) };
      n.running = false;
      break;
    case "stage_failed":
      n.stages[e.stage!] = "failed";
      n.failure = { stage: e.stage!, reason: String(e.reason), retry: (e.retry as string) ?? null };
      n.chat.push({ kind: "failed", stage: e.stage!, error: String(e.error ?? ""),
                    reason: String(e.reason), retry: (e.retry as string) ?? null, seq: e.seq });
      n.review = null;
      n.running = false;
      break;
    case "run_finished":
      for (const s of STAGES) if (n.stages[s] !== "skipped") n.stages[s] = "done";
      n.finished = { ...e };
      n.running = false;
      break;
  }
  return n;
}

export function reduce(v: RunView, a: Action): RunView {
  if (a.type === "event") return applyEvent(v, a.event);
  if (a.type === "select") return { ...v, selected: a.key, followLatest: false };
  const last = v.outputs[v.outputs.length - 1];
  return { ...v, followLatest: true, selected: last ? last.key : null };
}

export function selectedOutput(v: RunView): Output | null {
  return v.outputs.find((o) => o.key === v.selected) ?? null;
}

export function latestByStage(v: RunView): Partial<Record<StageId, Output>> {
  const m: Partial<Record<StageId, Output>> = {};
  for (const o of v.outputs) m[o.stage] = o;
  return m;
}

const ff = (x: unknown) => (Array.isArray(x) ? `${x[0]}/${x[1]} vertices flat-foldable` : "");

export function summaryLine(o: Output): string {
  const s = o.summary;
  switch (o.stage) {
    case "image": return s.skipped ? String(s.note) : String(s.provider ?? "");
    case "mesh": return [s.provider, s.faces != null ? `${Number(s.faces).toLocaleString()} faces` : ""]
      .filter(Boolean).join(" · ");
    case "tree": return s.approved ? "approved" : `${s.flaps} flaps, ${s.pairs} pairs`;
    case "packing": return `grid ${s.grid} · ${s.rung} · ${s.tried} tried`;
    case "solve": return [ff(s.flat_foldable), s.global_verdict ? `global: ${s.global_verdict}` : ""]
      .filter(Boolean).join(" · ");
    case "shape": return ff(s.flat_foldable);
    case "model": return "folded model";
  }
}

export function outputTitle(o: Output): string {
  const names: Record<StageId, string> = { image: "Concept image", mesh: "Mesh", tree: "Tree",
    packing: "Packing", solve: "Solved CP", shape: "Shaped CP", model: "Folded model" };
  return o.stage === "tree" && o.round != null ? `Tree · round ${o.round + 1}` : names[o.stage];
}
```

- [ ] **Step 5: Implement `api.ts`**

```ts
import type { PwEvent, RunSummary, Status } from "./types";

export type Command = { type: "message"; text: string } | { type: "approve" }
  | { type: "retry" } | { type: "cancel" };

export async function getStatus(): Promise<Status> {
  return (await fetch("/status")).json();
}

export async function listRuns(): Promise<RunSummary[]> {
  return (await fetch("/runs")).json();
}

export async function createRun(prompt: string): Promise<{ id: string }> {
  const r = await fetch("/runs", { method: "POST", headers: { "content-type": "application/json" },
                                   body: JSON.stringify({ prompt }) });
  const body = await r.json();
  if (!r.ok) throw new Error(body.detail ?? `HTTP ${r.status}`);
  return body;
}

export function fileUrl(runId: string, rel: string): string {
  return `/runs/${encodeURIComponent(runId)}/files/${rel.split("/").map(encodeURIComponent).join("/")}`;
}

/** Streams a run's events; reconnects after 1 s from the last seq seen. */
export function connectRun(runId: string, onEvent: (e: PwEvent) => void,
                           onError: (message: string) => void) {
  let ws: WebSocket | null = null;
  let last = -1;
  let closed = false;
  const open = () => {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    ws = new WebSocket(`${proto}://${location.host}/ws/runs/${encodeURIComponent(runId)}?after=${last}`);
    ws.onmessage = (m) => {
      const d = JSON.parse(m.data);
      if (d.type === "error" && d.seq === undefined) return onError(d.message);
      last = Math.max(last, d.seq);
      onEvent(d);
    };
    ws.onclose = () => { if (!closed) setTimeout(open, 1000); };
  };
  open();
  return {
    send(cmd: Command) { ws?.readyState === WebSocket.OPEN ? ws.send(JSON.stringify(cmd))
                                                           : onError("not connected; retrying"); },
    close() { closed = true; ws?.close(); },
  };
}
```

- [ ] **Step 6: Run tests and a type check**

Run: `cd app/web && npm test && npx tsc --noEmit`
Expected: the 7 tests PASS and the type check is clean.

- [ ] **Step 7: Commit**

```bash
git add app/web
git commit -m "app/web: scaffold, event types, runStore reducer, API client

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Layout: sidebar, chat, stepper, filmstrip, image and crease-pattern viewers

**Files:**
- Create: `app/web/src/main.tsx`, `App.tsx`, `styles.css`, `usePanZoom.ts`
- Create: `app/web/src/components/RunsSidebar.tsx`, `Chat.tsx`, `StageBlock.tsx`, `Stepper.tsx`, `Filmstrip.tsx`, `Viewer.tsx`, `ImageView.tsx`, `CPView.tsx`
- Modify: `app/web/src/runStore.test.ts` is unchanged; this task is verified by `tsc`, the build, and the browser.

**Interfaces:**
- Consumes: Task 9's `reduce`, `emptyView`, `selectedOutput`, `latestByStage`, `summaryLine`, `outputTitle`, `api.*`, `STAGES`.
- Produces:
  - `<Viewer runId output allOutputs />`, which dispatches by file extension: `.png/.jpg/.jpeg/.webp` → ImageView, `.svg` → CPView, `.glb` → MeshView, `.fold` → ModelView. MeshView and ModelView come from Task 11; in this task Viewer renders a placeholder `<div className="viewer-empty">3-D view arrives in the next task</div>` for `.glb` and `.fold`.
  - The CSS theme tokens: `--bg`, `--panel`, `--line`, `--text`, `--muted`, `--accent` (orange, "needs you"), `--ok`, `--run`, `--bad`.

- [ ] **Step 1: Write `styles.css`** (dark by default, light by system setting)

```css
:root { --bg:#1a1a1a; --panel:#141414; --raise:#222; --line:#2c2c2c; --text:#ddd; --muted:#888;
        --accent:#d08a2a; --ok:#3a3; --run:#3b82f6; --bad:#d33; --user:#2b3646;
        font:14px/1.45 -apple-system, system-ui, sans-serif; color:var(--text); background:var(--bg); }
@media (prefers-color-scheme: light) {
  :root { --bg:#fafafa; --panel:#f0f0f0; --raise:#fff; --line:#ddd; --text:#222; --muted:#666; --user:#dde6f3; }
}
* { box-sizing:border-box } body { margin:0 } button { font:inherit; cursor:pointer }
.app { display:grid; grid-template-columns:220px 400px 1fr; height:100vh; }
.sidebar { background:var(--panel); border-right:1px solid var(--line); padding:10px; overflow:auto }
.sidebar .new { width:100%; padding:7px; border:1px solid var(--line); border-radius:6px; background:none; color:var(--text) }
.sidebar .day { font-size:11px; text-transform:uppercase; color:var(--muted); margin:12px 0 4px }
.sidebar .run { display:flex; justify-content:space-between; padding:6px 8px; border-radius:6px; color:var(--muted); cursor:pointer }
.sidebar .run.on { background:var(--raise); color:var(--text) }
.dot { width:8px; height:8px; border-radius:50%; margin-top:6px; flex:none }
.dot.running { background:var(--run) } .dot.waiting { background:var(--accent) }
.dot.done { background:var(--ok) } .dot.failed { background:var(--bad) } .dot.new { background:var(--muted) }
.chat { display:flex; flex-direction:column; border-right:1px solid var(--line); min-width:0 }
.msgs { flex:1; overflow:auto; padding:14px; display:flex; flex-direction:column; gap:10px }
.user { align-self:flex-end; background:var(--user); padding:7px 11px; border-radius:10px; max-width:85% }
.assistant { white-space:pre-wrap }
.block { display:flex; gap:10px; align-items:center; border:1px solid var(--line); border-radius:8px; padding:7px 9px; cursor:pointer; font:12px ui-monospace, Menlo, monospace; background:none; color:var(--text); text-align:left }
.block.sel { border-color:var(--accent) }
.block .thumb { width:52px; height:38px; border-radius:4px; background:var(--raise); object-fit:contain; display:flex; align-items:center; justify-content:center; color:var(--muted); flex:none }
.block .muted { color:var(--muted) }
.failed { border:1px solid var(--bad); border-radius:8px; padding:8px; font-size:13px }
.composer { margin:10px; display:flex; gap:6px }
.composer textarea { flex:1; resize:none; border:1px solid var(--line); border-radius:10px; padding:10px; background:var(--raise); color:var(--text); font:inherit }
.btn { background:var(--accent); color:#111; border:none; border-radius:6px; padding:6px 14px; font-weight:600 }
.btn:disabled { opacity:.4; cursor:default }
.btn.ghost { background:none; border:1px solid var(--line); color:var(--text); font-weight:400 }
.banner { background:var(--bad); color:#fff; padding:6px 12px; font-size:13px }
.toast { position:fixed; bottom:16px; left:50%; transform:translateX(-50%); background:var(--raise); border:1px solid var(--bad); padding:8px 14px; border-radius:8px }
.out { display:flex; flex-direction:column; min-width:0 }
.stepper { display:flex; gap:6px; padding:10px 12px; border-bottom:1px solid var(--line); flex-wrap:wrap }
.step { padding:3px 10px; border-radius:12px; font-size:12px; border:none; background:var(--raise); color:var(--muted) }
.step.done { background:#1f3a24; color:#9e9 } .step.running { background:#1e2d4a; color:#9bf }
.step.waiting { background:var(--accent); color:#111; font-weight:600 } .step.failed { background:#4a1e1e; color:#f99 }
.step.skipped { text-decoration:line-through }
.viewer { flex:1; margin:10px; border-radius:8px; background:var(--raise); position:relative; overflow:hidden; min-height:0 }
.viewer-empty { display:flex; align-items:center; justify-content:center; height:100%; color:var(--muted) }
.vtools { position:absolute; top:8px; right:8px; display:flex; gap:4px; z-index:2 }
.vtools button { font-size:11px; padding:2px 8px; border-radius:5px; border:1px solid var(--line); background:var(--panel); color:var(--text) }
.vtools button.on { background:var(--accent); color:#111 }
.follow { position:absolute; top:8px; left:8px; z-index:2; font-size:11px; color:var(--muted); background:none; border:none }
.pz { width:100%; height:100%; overflow:hidden; cursor:grab }
.pz > * { transform-origin:0 0 }
.cp.no-hinges line[stroke="green"] { display:none }
.cp.mono line[stroke="red"], .cp.mono line[stroke="blue"] { stroke:#888 }
.cp svg { width:100%; height:100%; background:#fff }
.film { display:flex; gap:6px; padding:0 10px 10px; overflow-x:auto }
.frame { width:78px; height:52px; border-radius:5px; background:var(--raise); border:1px solid var(--line); font-size:10px; color:var(--muted); display:flex; align-items:flex-end; padding:3px; flex:none; overflow:hidden; position:relative }
.frame img { position:absolute; inset:0; width:100%; height:100%; object-fit:contain }
.frame span { position:relative; background:var(--panel); padding:0 3px; border-radius:3px }
.frame.on { outline:2px solid var(--accent) } .frame.none { border-style:dashed; background:none }
.empty-run { margin:auto; text-align:center; color:var(--muted) }
```

- [ ] **Step 2: Write `usePanZoom.ts`**

```ts
import { useCallback, useRef, useState } from "react";

/** Wheel to zoom about the cursor, drag to pan, double-click to reset. */
export function usePanZoom() {
  const [t, setT] = useState({ x: 0, y: 0, k: 1 });
  const drag = useRef<{ x: number; y: number } | null>(null);
  const onWheel = useCallback((e: React.WheelEvent) => {
    const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const px = e.clientX - r.left, py = e.clientY - r.top;
    setT((p) => {
      const k = Math.min(40, Math.max(0.2, p.k * Math.exp(-e.deltaY * 0.0015)));
      return { k, x: px - ((px - p.x) * k) / p.k, y: py - ((py - p.y) * k) / p.k };
    });
  }, []);
  const onPointerDown = (e: React.PointerEvent) => {
    drag.current = { x: e.clientX, y: e.clientY };
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
  };
  const onPointerMove = (e: React.PointerEvent) => {
    if (!drag.current) return;
    const dx = e.clientX - drag.current.x, dy = e.clientY - drag.current.y;
    drag.current = { x: e.clientX, y: e.clientY };
    setT((p) => ({ ...p, x: p.x + dx, y: p.y + dy }));
  };
  const onPointerUp = () => { drag.current = null; };
  const reset = () => setT({ x: 0, y: 0, k: 1 });
  return {
    handlers: { onWheel, onPointerDown, onPointerMove, onPointerUp, onDoubleClick: reset },
    style: { transform: `translate(${t.x}px, ${t.y}px) scale(${t.k})`, width: "100%", height: "100%" },
    reset,
  };
}
```

- [ ] **Step 3: Write the viewer components**

`components/ImageView.tsx`:
```tsx
import { usePanZoom } from "../usePanZoom";

export function ImageView({ src }: { src: string }) {
  const pz = usePanZoom();
  return (
    <div className="pz" {...pz.handlers}>
      <img src={src} style={{ ...pz.style, objectFit: "contain" }} draggable={false} />
    </div>
  );
}
```

`components/CPView.tsx`:
```tsx
import { useEffect, useRef, useState } from "react";
import { usePanZoom } from "../usePanZoom";

/** A Pleatwright CP SVG, inlined so its creases can be toggled by colour
 * (COrigami semantics: red mountain, blue valley, black border, green hinge). */
export function CPView({ src }: { src: string }) {
  const host = useRef<HTMLDivElement>(null);
  const [hinges, setHinges] = useState(true);
  const [mv, setMv] = useState(true);
  const pz = usePanZoom();
  useEffect(() => {
    let live = true;
    fetch(src).then((r) => r.text()).then((text) => {
      if (!live || !host.current) return;
      const doc = new DOMParser().parseFromString(text, "image/svg+xml");
      const svg = doc.documentElement;
      if (svg.nodeName !== "svg") return;
      svg.querySelectorAll("script, foreignObject").forEach((n) => n.remove());
      host.current.replaceChildren(document.importNode(svg, true));
    });
    return () => { live = false; };
  }, [src]);
  return (
    <>
      <div className="vtools">
        <button className={hinges ? "on" : ""} onClick={() => setHinges(!hinges)}>hinges</button>
        <button className={mv ? "on" : ""} onClick={() => setMv(!mv)}>M/V colours</button>
      </div>
      <div className="pz" {...pz.handlers}>
        <div ref={host} style={pz.style}
             className={`cp${hinges ? "" : " no-hinges"}${mv ? "" : " mono"}`} />
      </div>
    </>
  );
}
```

`components/Viewer.tsx`:
```tsx
import { useState } from "react";
import { fileUrl } from "../api";
import type { Output } from "../types";
import { CPView } from "./CPView";
import { ImageView } from "./ImageView";

const ext = (f: string) => f.slice(f.lastIndexOf(".")).toLowerCase();
const IMG = [".png", ".jpg", ".jpeg", ".webp"];

export function Viewer({ runId, output, allOutputs, onSelect }: {
  runId: string; output: Output | null; allOutputs: Output[]; onSelect: (key: string) => void;
}) {
  const [fileIx, setFileIx] = useState(0);
  if (!output) return <div className="viewer-empty">Outputs appear here as each stage finishes.</div>;
  const files = output.files.filter((f) => ext(f) !== ".json");
  if (files.length === 0)
    return <div className="viewer-empty">{String(output.summary.note ?? "nothing to show")}</div>;
  const f = files[Math.min(fileIx, files.length - 1)];
  const url = fileUrl(runId, f);
  const rounds = allOutputs.filter((o) => o.stage === "tree");
  return (
    <>
      <div className="vtools">
        {output.stage === "tree" && rounds.map((o) => (
          <button key={o.key} className={o.key === output.key ? "on" : ""}
                  onClick={() => onSelect(o.key)}>round {(o.round ?? 0) + 1}</button>))}
        {files.length > 1 && files.map((x, i) => (
          <button key={x} className={x === f ? "on" : ""} onClick={() => setFileIx(i)}>
            {x.split("/").pop()}</button>))}
      </div>
      {IMG.includes(ext(f)) && <ImageView key={url} src={url} />}
      {ext(f) === ".svg" && <CPView key={url} src={url} />}
      {(ext(f) === ".glb" || ext(f) === ".fold") &&
        <div className="viewer-empty">3-D view arrives in the next task</div>}
    </>
  );
}
```

- [ ] **Step 4: Write the chat-side components**

`components/StageBlock.tsx`:
```tsx
import { fileUrl } from "../api";
import { outputTitle, summaryLine } from "../runStore";
import type { Output } from "../types";

export function StageBlock({ runId, o, selected, onClick }: {
  runId: string; o: Output; selected: boolean; onClick: () => void;
}) {
  const img = o.files.find((f) => /\.(png|jpe?g|webp|svg)$/i.test(f));
  return (
    <button className={`block${selected ? " sel" : ""}`} onClick={onClick}>
      {img ? <img className="thumb" src={fileUrl(runId, img)} />
           : <span className="thumb">{o.stage === "mesh" || o.stage === "model" ? "3D" : "—"}</span>}
      <span><b>{outputTitle(o)}</b><br /><span className="muted">{summaryLine(o)}</span></span>
    </button>
  );
}
```

`components/Chat.tsx`:
```tsx
import { useEffect, useRef, useState } from "react";
import type { Command } from "../api";
import type { RunView } from "../types";
import { StageBlock } from "./StageBlock";

export function Chat({ view, send, onSelect, onNewRun, canStart, onStart }: {
  view: RunView | null; send: (c: Command) => void; onSelect: (k: string) => void;
  onNewRun: () => void; canStart: boolean; onStart: (prompt: string) => void;
}) {
  const [text, setText] = useState("");
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => end.current?.scrollIntoView({ block: "end" }), [view?.lastSeq]);

  if (!view) {
    const go = () => { if (text.trim()) { onStart(text.trim()); setText(""); } };
    return (
      <div className="chat">
        <div className="msgs"><div className="empty-run"><h3>What should we fold?</h3>
          <p>Describe an animal or object, e.g. “a dog”.</p></div></div>
        <div className="composer">
          <textarea rows={2} value={text} disabled={!canStart} placeholder="a dog"
                    onChange={(e) => setText(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); go(); } }} />
          <button className="btn" disabled={!canStart || !text.trim()} onClick={go}>Fold</button>
        </div>
      </div>
    );
  }
  const ended = !!view.finished || view.failure?.reason === "exhausted";
  const reviewing = !!view.review && !view.running;
  const submit = () => {
    if (!text.trim() || !reviewing) return;
    send({ type: "message", text: text.trim() });
    setText("");
  };
  return (
    <div className="chat">
      <div className="msgs">
        {view.chat.map((c) => {
          if (c.kind === "user") return <div key={c.seq} className="user">{c.text}</div>;
          if (c.kind === "assistant") return <div key={c.seq} className="assistant">{c.text}</div>;
          if (c.kind === "failed") return (
            <div key={c.seq} className="failed">
              <b>{c.stage} {c.reason === "error" ? "failed" : c.reason}</b>: {c.error}
              {c.retry && view.failure && c.seq === Math.max(...view.chat.filter((x) => x.kind === "failed").map((x) => x.seq)) &&
                <div style={{ marginTop: 6 }}><button className="btn" onClick={() => send({ type: "retry" })}>Retry</button></div>}
            </div>);
          const o = view.outputs.find((x) => x.key === c.key)!;
          return <StageBlock key={c.seq} runId={view.id} o={o} selected={view.selected === o.key}
                             onClick={() => onSelect(o.key)} />;
        })}
        {reviewing && (
          <div>
            <button className="btn" disabled={!view.review!.canApprove}
                    onClick={() => send({ type: "approve" })}>Approve</button>
            <span className="muted" style={{ marginLeft: 8, color: "var(--muted)" }}>
              or type what is wrong with the tree ↓</span>
          </div>)}
        <div ref={end} />
      </div>
      {ended ? (
        <div className="composer"><button className="btn" onClick={onNewRun}>＋ New run</button></div>
      ) : (
        <div className="composer">
          <textarea rows={2} value={text} disabled={!reviewing}
                    placeholder={reviewing ? "Describe what is wrong with the tree…" : view.running ? "Working…" : ""}
                    onChange={(e) => setText(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }} />
          {view.running
            ? <button className="btn ghost" onClick={() => send({ type: "cancel" })}>Cancel</button>
            : <button className="btn" disabled={!reviewing || !text.trim()} onClick={submit}>Send</button>}
        </div>
      )}
    </div>
  );
}
```

`components/Stepper.tsx`:
```tsx
import { useEffect, useState } from "react";
import { latestByStage } from "../runStore";
import { STAGES, type RunView } from "../types";

const ICON = { done: "✓ ", running: "", waiting: "⏸ ", failed: "✕ ", skipped: "", todo: "" };

export function Stepper({ view, onSelect }: { view: RunView; onSelect: (k: string) => void }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (!view.running) return;
    const i = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(i);
  }, [view.running]);
  const latest = latestByStage(view);
  return (
    <div className="stepper">
      {STAGES.map((s) => {
        const st = view.stages[s];
        const since = view.startedAt[s];
        const secs = st === "running" && since ? Math.max(0, Math.round((now - Date.parse(since)) / 1000)) : null;
        return (
          <button key={s} className={`step ${st}`} disabled={!latest[s]}
                  onClick={() => latest[s] && onSelect(latest[s]!.key)}>
            {ICON[st]}{s}{secs != null ? ` ${secs}s` : ""}
          </button>);
      })}
    </div>
  );
}
```

`components/Filmstrip.tsx`:
```tsx
import { fileUrl } from "../api";
import { latestByStage } from "../runStore";
import { STAGES, type RunView } from "../types";

export function Filmstrip({ view, onSelect }: { view: RunView; onSelect: (k: string) => void }) {
  const latest = latestByStage(view);
  return (
    <div className="film">
      {STAGES.map((s) => {
        const o = latest[s];
        const img = o?.files.find((f) => /\.(png|jpe?g|webp|svg)$/i.test(f));
        return (
          <div key={s} className={`frame${!o ? " none" : ""}${o && o.key === view.selected ? " on" : ""}`}
               onClick={() => o && onSelect(o.key)}>
            {img && <img src={fileUrl(view.id, img)} />}
            <span>{s}</span>
          </div>);
      })}
    </div>
  );
}
```

`components/RunsSidebar.tsx`:
```tsx
import type { RunSummary } from "../types";

const day = (iso: string) => {
  const d = new Date(iso), t = new Date();
  const y = new Date(t); y.setDate(t.getDate() - 1);
  if (d.toDateString() === t.toDateString()) return "Today";
  if (d.toDateString() === y.toDateString()) return "Yesterday";
  return d.toLocaleDateString();
};

export function RunsSidebar({ runs, current, onOpen, onNew }: {
  runs: RunSummary[]; current: string | null; onOpen: (id: string) => void; onNew: () => void;
}) {
  let lastDay = "";
  return (
    <div className="sidebar">
      <button className="new" onClick={onNew}>＋ New run</button>
      {runs.map((r) => {
        const d = day(r.created);
        const head = d !== lastDay ? <div className="day">{(lastDay = d)}</div> : null;
        return (
          <div key={r.id}>
            {head}
            <div className={`run${r.id === current ? " on" : ""}`} onClick={() => onOpen(r.id)} title={r.prompt}>
              <span>{r.subject}</span><span className={`dot ${r.status}`} />
            </div>
          </div>);
      })}
    </div>
  );
}
```

- [ ] **Step 5: Write `App.tsx` and `main.tsx`**

`App.tsx`:
```tsx
import { useEffect, useReducer, useRef, useState } from "react";
import { connectRun, createRun, getStatus, listRuns, type Command } from "./api";
import { Chat } from "./components/Chat";
import { Filmstrip } from "./components/Filmstrip";
import { RunsSidebar } from "./components/RunsSidebar";
import { Stepper } from "./components/Stepper";
import { Viewer } from "./components/Viewer";
import { emptyView, reduce, selectedOutput } from "./runStore";
import type { Action, RunSummary, RunView, Status } from "./types";

const hashRun = () => new URLSearchParams(location.hash.slice(1)).get("run");

function viewReducer(v: RunView | null, a: Action | { type: "reset"; id: string | null }) {
  if (a.type === "reset") return a.id ? emptyView(a.id) : null;
  return v ? reduce(v, a) : v;
}

export function App() {
  const [status, setStatus] = useState<Status | null>(null);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [runId, setRunId] = useState<string | null>(hashRun());
  const [view, dispatch] = useReducer(viewReducer, runId ? emptyView(runId) : null);
  const [toast, setToast] = useState<string | null>(null);
  const sock = useRef<ReturnType<typeof connectRun> | null>(null);

  const refresh = () => { getStatus().then(setStatus); listRuns().then(setRuns); };
  useEffect(() => { refresh(); const i = setInterval(refresh, 3000); return () => clearInterval(i); }, []);
  useEffect(() => {
    const on = () => setRunId(hashRun());
    addEventListener("hashchange", on);
    return () => removeEventListener("hashchange", on);
  }, []);
  useEffect(() => {
    dispatch({ type: "reset", id: runId });
    sock.current?.close();
    sock.current = runId ? connectRun(runId, (event) => dispatch({ type: "event", event }), flash) : null;
    return () => sock.current?.close();
  }, [runId]);

  function flash(m: string) { setToast(m); setTimeout(() => setToast(null), 4000); }
  const open = (id: string | null) => { location.hash = id ? `run=${id}` : ""; setRunId(id); };
  const send = (c: Command) => sock.current?.send(c);
  const start = async (prompt: string) => {
    try { const { id } = await createRun(prompt); open(id); refresh(); }
    catch (e) { flash((e as Error).message); }
  };
  const select = (key: string) => dispatch({ type: "select", key });

  return (
    <>
      {status && !status.llm_ok &&
        <div className="banner">Authoring is disabled: {status.llm_error}</div>}
      <div className="app" style={status && !status.llm_ok ? { height: "calc(100vh - 30px)" } : undefined}>
        <RunsSidebar runs={runs} current={runId} onOpen={open} onNew={() => open(null)} />
        <Chat view={view} send={send} onSelect={select} onNewRun={() => open(null)}
              canStart={!!status?.llm_ok && !status?.busy} onStart={start} />
        <div className="out">
          {view && <Stepper view={view} onSelect={select} />}
          <div className="viewer">
            {view && !view.followLatest &&
              <button className="follow" onClick={() => dispatch({ type: "follow" })}>● follow latest</button>}
            {view
              ? <Viewer key={selectedOutput(view)?.key ?? "none"} runId={view.id}
                        output={selectedOutput(view)} allOutputs={view.outputs} onSelect={select} />
              : <div className="viewer-empty">Start a run to see its outputs.</div>}
          </div>
          {view && <Filmstrip view={view} onSelect={select} />}
        </div>
      </div>
      {toast && <div className="toast">{toast}</div>}
    </>
  );
}
```

`main.tsx`:
```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./styles.css";

createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);
```

- [ ] **Step 6: Type check, test and build**

Run: `cd app/web && npx tsc --noEmit && npm test && npm run build`
Expected: no type errors, 7 tests PASS, and `dist/` built.

- [ ] **Step 7: Check it in the browser with the fake providers**

Add `.claude/launch.json` if absent (not committed; `.claude/` is untracked):
```json
{ "version": "0.0.1", "configurations": [
  { "name": "pleatwright-app", "runtimeExecutable": "bash",
    "runtimeArgs": ["-c", "cd mcp_harness && MESH_PROVIDER=fake PLEATWRIGHT_RUNS_DIR=/tmp/pw-seed/runs PYTHONPATH=.:../app/server <repo>/mcp_harness/.venv/bin/python -m pleatwright_app --port 8000"],
    "port": 8000 } ] }
```
Use `preview_start {name: "pleatwright-app"}` and confirm:
1. The sidebar, chat and output panel render, and the console has no errors.
2. There is no live LLM in this check. Seed a finished run first, with `cd mcp_harness && PYTHONPATH=.:tests:../app/server $PY ../app/server/record_fixture.py /tmp/pw-seed` (this keeps the run and does not touch the committed fixture). Then reload and open the run. Confirm the chat shows the blocks, the stepper is all done (image skipped), the tree view has the round 1 and round 2 buttons, and the packing, solve and shape SVGs pan and zoom with working toggles.

Take a screenshot as proof.

- [ ] **Step 8: Commit**

```bash
git add app/web
git commit -m "app/web: sidebar, chat, stepper, filmstrip, image and crease-pattern viewers

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: 3-D viewers: the mesh and the folded model with a fold slider

**Files:**
- Create: `app/web/src/fold.ts`, `fold.test.ts`, `components/MeshView.tsx`, `components/ModelView.tsx`
- Modify: `app/web/src/components/Viewer.tsx` (replace the placeholder)

**Interfaces:**
- Consumes: `model.fold` (Task 2 format), `fileUrl` (Task 9).
- Produces:
  - `fold.ts` exports `FoldFile`, `triangulate(faces): Uint32Array` (fan), `framePositions(fold, i): Float32Array`, `frameIndex(fold, percent0to100): number`, `creaseSegments(fold, i, kind: "M" | "V"): Float32Array`, and `bounds(positions): {center: [number, number, number], radius: number}`.
  - `<MeshView src />` and `<ModelView foldSrc overviewSrc />`.

- [ ] **Step 1: Write the failing tests**

`app/web/src/fold.test.ts` uses a two-triangle unit square folded along its diagonal. It is a crease pattern, not a tree, so the tree rule does not apply.
```ts
import { describe, expect, it } from "vitest";
import { bounds, creaseSegments, frameIndex, framePositions, triangulate, type FoldFile } from "./fold";

const sq: FoldFile = {
  vertices_coords: [[0, 0], [1, 0], [1, 1], [0, 1]],
  faces_vertices: [[0, 1, 2], [0, 2, 3]],
  edges_vertices: [[0, 1], [1, 2], [2, 3], [3, 0], [0, 2]],
  edges_assignment: ["B", "B", "B", "B", "V"],
  edges_foldAngle: [0, 0, 0, 0, 180],
  file_frames: [
    { vertices_coords: [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]] },
    { vertices_coords: [[0, 0, 0], [1, 0, 0], [1, 1, 0], [1, 0, 0]] },
  ],
  "pleatwright:percents": [0, 100],
};

describe("fold.ts", () => {
  it("fan-triangulates faces", () => {
    expect(Array.from(triangulate([[0, 1, 2, 3]]))).toEqual([0, 1, 2, 0, 2, 3]);
  });
  it("flattens a frame to xyz", () => {
    expect(Array.from(framePositions(sq, 1)).slice(9)).toEqual([1, 0, 0]);
  });
  it("maps a slider percent to the nearest frame", () => {
    expect(frameIndex(sq, 0)).toBe(0);
    expect(frameIndex(sq, 49)).toBe(0);
    expect(frameIndex(sq, 51)).toBe(1);
    expect(frameIndex(sq, 100)).toBe(1);
  });
  it("emits segments for one crease kind", () => {
    expect(Array.from(creaseSegments(sq, 0, "V"))).toEqual([0, 0, 0, 1, 1, 0]);
    expect(creaseSegments(sq, 0, "M").length).toBe(0);
  });
  it("bounds", () => {
    const b = bounds(framePositions(sq, 0));
    expect(b.center).toEqual([0.5, 0.5, 0]);
    expect(b.radius).toBeCloseTo(Math.SQRT2 / 2);
  });
});
```

Run: `cd app/web && npm test`
Expected: FAIL, `Failed to resolve import "./fold"`.

- [ ] **Step 2: Implement `fold.ts`**

```ts
export interface FoldFile {
  vertices_coords: number[][];
  faces_vertices: number[][];
  edges_vertices: number[][];
  edges_assignment: string[];
  edges_foldAngle: number[];
  file_frames: { vertices_coords: number[][]; frame_title?: string }[];
  "pleatwright:percents": number[];
}

export function triangulate(faces: number[][]): Uint32Array {
  const out: number[] = [];
  for (const f of faces) for (let i = 1; i + 1 < f.length; i++) out.push(f[0], f[i], f[i + 1]);
  return new Uint32Array(out);
}

export function framePositions(fold: FoldFile, i: number): Float32Array {
  const V = fold.file_frames[i].vertices_coords;
  const out = new Float32Array(V.length * 3);
  V.forEach((v, j) => { out[3 * j] = v[0]; out[3 * j + 1] = v[1]; out[3 * j + 2] = v[2] ?? 0; });
  return out;
}

export function frameIndex(fold: FoldFile, percent: number): number {
  const ps = fold["pleatwright:percents"];
  let best = 0;
  for (let i = 1; i < ps.length; i++) if (Math.abs(ps[i] - percent) < Math.abs(ps[best] - percent)) best = i;
  return best;
}

export function creaseSegments(fold: FoldFile, i: number, kind: "M" | "V"): Float32Array {
  const P = framePositions(fold, i);
  const out: number[] = [];
  fold.edges_vertices.forEach(([a, b], k) => {
    if (fold.edges_assignment[k] !== kind) return;
    out.push(P[3 * a], P[3 * a + 1], P[3 * a + 2], P[3 * b], P[3 * b + 1], P[3 * b + 2]);
  });
  return new Float32Array(out);
}

export function bounds(P: Float32Array): { center: [number, number, number]; radius: number } {
  const lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
  for (let i = 0; i < P.length; i += 3)
    for (let k = 0; k < 3; k++) { lo[k] = Math.min(lo[k], P[i + k]); hi[k] = Math.max(hi[k], P[i + k]); }
  const center = [0, 1, 2].map((k) => (lo[k] + hi[k]) / 2) as [number, number, number];
  const radius = Math.hypot(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]) / 2;
  return { center, radius };
}
```

Run: `npm test`. Expected: all PASS.

- [ ] **Step 3: Implement `MeshView.tsx`**

```tsx
import { Bounds, Center, OrbitControls, useGLTF } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { Suspense } from "react";

function Model({ src }: { src: string }) {
  const { scene } = useGLTF(src);
  return <Center><primitive object={scene} /></Center>;
}

export function MeshView({ src }: { src: string }) {
  return (
    <Canvas camera={{ position: [2, 1.5, 2.5], fov: 40 }}>
      <ambientLight intensity={0.7} />
      <directionalLight position={[3, 5, 4]} intensity={1.4} />
      <Suspense fallback={null}>
        <Bounds fit clip observe margin={1.2}><Model src={src} /></Bounds>
      </Suspense>
      <OrbitControls makeDefault />
    </Canvas>
  );
}
```

- [ ] **Step 4: Implement `ModelView.tsx`**

```tsx
import { OrbitControls } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { useEffect, useMemo, useState } from "react";
import * as THREE from "three";
import { bounds, creaseSegments, frameIndex, framePositions, triangulate, type FoldFile } from "../fold";
import { ImageView } from "./ImageView";

function Paper({ fold, frame }: { fold: FoldFile; frame: number }) {
  const index = useMemo(() => new THREE.BufferAttribute(triangulate(fold.faces_vertices), 1), [fold]);
  const geo = useMemo(() => {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(framePositions(fold, frame), 3));
    g.setIndex(index);
    g.computeVertexNormals();
    return g;
  }, [fold, frame, index]);
  const lines = (kind: "M" | "V") => {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(creaseSegments(fold, frame, kind), 3));
    return g;
  };
  const m = useMemo(() => lines("M"), [fold, frame]);
  const v = useMemo(() => lines("V"), [fold, frame]);
  return (
    <group>
      <mesh geometry={geo}><meshStandardMaterial color="#f4efe6" side={THREE.FrontSide} flatShading /></mesh>
      <mesh geometry={geo}><meshStandardMaterial color="#d08a2a" side={THREE.BackSide} flatShading /></mesh>
      <lineSegments geometry={m}><lineBasicMaterial color="#d33" /></lineSegments>
      <lineSegments geometry={v}><lineBasicMaterial color="#36f" /></lineSegments>
    </group>
  );
}

export function ModelView({ foldSrc, overviewSrc }: { foldSrc: string; overviewSrc?: string }) {
  const [fold, setFold] = useState<FoldFile | null>(null);
  const [pct, setPct] = useState(100);
  const [playing, setPlaying] = useState(false);
  const [overview, setOverview] = useState(false);
  useEffect(() => { fetch(foldSrc).then((r) => r.json()).then(setFold); }, [foldSrc]);
  useEffect(() => {
    if (!playing) return;
    const i = setInterval(() => setPct((p) => (p >= 100 ? 0 : Math.min(100, p + 2))), 60);
    return () => clearInterval(i);
  }, [playing]);
  if (!fold) return <div className="viewer-empty">loading model…</div>;
  const frame = frameIndex(fold, pct);
  const b = bounds(framePositions(fold, fold.file_frames.length - 1));
  const d = b.radius * 2.6;
  return (
    <>
      <div className="vtools">
        {overviewSrc && <button className={overview ? "on" : ""} onClick={() => setOverview(!overview)}>overview.png</button>}
      </div>
      {overview && overviewSrc ? <ImageView src={overviewSrc} /> : (
        <>
          <Canvas camera={{ position: [b.center[0] + d, b.center[1] - d, b.center[2] + d], up: [0, 0, 1], fov: 40,
                            near: b.radius / 100, far: b.radius * 100 }}>
            <ambientLight intensity={0.6} />
            <directionalLight position={[b.center[0] + d, b.center[1] - d, b.center[2] + 2 * d]} intensity={1.3} />
            <Paper fold={fold} frame={frame} />
            <OrbitControls makeDefault target={b.center} />
          </Canvas>
          <div style={{ position: "absolute", left: 12, right: 12, bottom: 10, display: "flex", gap: 8, alignItems: "center" }}>
            <button className="btn ghost" onClick={() => setPlaying(!playing)}>{playing ? "❚❚" : "▶"}</button>
            <input type="range" min={0} max={100} value={pct} style={{ flex: 1 }}
                   onChange={(e) => { setPlaying(false); setPct(Number(e.target.value)); }} />
            <span style={{ width: 44, textAlign: "right" }}>{pct}%</span>
          </div>
        </>
      )}
    </>
  );
}
```

- [ ] **Step 5: Wire them into `Viewer.tsx`**

Replace the placeholder line with:
```tsx
      {ext(f) === ".glb" && <MeshView key={url} src={url} />}
      {ext(f) === ".fold" && (
        <ModelView key={url} foldSrc={url}
                   overviewSrc={output.files.find((x) => x.endsWith("overview.png")) &&
                                fileUrl(runId, output.files.find((x) => x.endsWith("overview.png"))!)} />)}
```
Add the imports `import { MeshView } from "./MeshView";` and `import { ModelView } from "./ModelView";`. For `model` outputs, show the `.fold` file by default: change the `files` line so a model output lists only `model.fold`, since ModelView offers the overview through its own toggle:
```tsx
  const files = output.files.filter((f) => ext(f) !== ".json" &&
    !(output.stage === "model" && f.endsWith("overview.png")));
```

- [ ] **Step 6: Type check, test, build, and look at it**

Run: `cd app/web && npx tsc --noEmit && npm test && npm run build`
Expected: clean, all tests PASS, built.

In the browser (the Task 10 launch config, with a seeded finished run), open the mesh output and confirm it orbits. Open the model: the slider at 0% shows a flat sheet, at 100% the folded bird, and ▶ plays. The overview toggle shows `overview.png`. Take a screenshot at 100% and at about 40% as proof.

- [ ] **Step 7: Commit**

```bash
git add app/web
git commit -m "app/web: orbitable mesh and folded model with fold slider

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 12: `make app`, CI, requirements, and docs

**Files:**
- Modify: `Makefile`, `.github/workflows/ci.yml`, `requirements.txt`, `requirements-frozen.txt`, `CLAUDE.md`
- Create: `app/README.md`

- [ ] **Step 1: Makefile**

Replace the file with:
```make
# Build + test entry points. CI runs `make PYTHON=python test`.
PYTHON ?= .venv/bin/python
HARNESS := mcp_harness

.PHONY: test test-app app app-dev clean

test: ## Run the full suite (minutes): pipeline, then the app server.
	cd $(HARNESS) && PYTHONPATH=.:tests $(PYTHON) -m pytest tests/ -q
	$(MAKE) test-app

test-app: ## App server tests only.
	cd $(HARNESS) && PYTHONPATH=.:tests:../app/server $(PYTHON) -m pytest ../app/server/tests -q -p no:cacheprovider

app: ## Build the UI and serve the app at http://127.0.0.1:8000
	cd app/web && npm ci && npm run build
	cd $(HARNESS) && PYTHONPATH=.:../app/server $(PYTHON) -m pleatwright_app

app-dev: ## API on :8000 + Vite with hot reload on :5173
	trap 'kill 0' INT TERM; \
	(cd $(HARNESS) && PYTHONPATH=.:../app/server $(PYTHON) -m pleatwright_app --no-ui) & \
	(cd app/web && npm run dev) & wait

clean:
	rm -rf $(HARNESS)/__pycache__ $(HARNESS)/tests/__pycache__ $(HARNESS)/.pytest_cache app/web/dist
```

- [ ] **Step 2: requirements**

Append to `requirements.txt`:
```
fastapi                # app server (app/server/pleatwright_app)
uvicorn                # app server
websockets             # app server: WebSocket transport for uvicorn
```
Add to `requirements-frozen.txt` the exact versions from the dev venv for fastapi and everything it, uvicorn and websockets pull in that is not already listed. Run `$PY -m pip freeze | grep -iE '^(fastapi|starlette|uvicorn|websockets|pydantic|pydantic[-_]core|annotated[-_]types|typing[-_]inspection|h11|click|anyio)=='`. Add only the missing lines and keep the file's sort order. Do not change any existing line.

- [ ] **Step 3: CI**

In `.github/workflows/ci.yml`, add the following to the `pip install` line: `"fastapi==0.138.1" "uvicorn==0.49.0" "websockets==16.0"`. Then add a second job:
```yaml
  web:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    defaults:
      run:
        working-directory: app/web
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: npm
          cache-dependency-path: app/web/package-lock.json
      - run: npm ci
      - run: npm test
      - run: npm run build
```

- [ ] **Step 4: Docs**

Create `app/README.md`:
````markdown
# Pleatwright app

A local web app for the Pleatwright pipeline. The conversation is on the left and the outputs (concept image, mesh, tree, crease patterns, folded model) on the right. Design: `docs/superpowers/specs/2026-10-07-pleatwright-app-design.md`.

```bash
make app        # build the UI, serve http://127.0.0.1:8000
make app-dev    # API on :8000 + Vite hot reload on http://127.0.0.1:5173
make test-app   # server tests;  cd app/web && npm test  for the UI
```

* Runs are stored in `~/Pleatwright/runs/` (`PLEATWRIGHT_RUNS_DIR` overrides). Each is the CLI's `--out DIR` layout plus `events.jsonl` (the run's history) and `model.fold` (the folded model, with fold-slider frames). `python -m pleatwright fold DIR/tree.json --out DIR` works on any app run.
* Keys and providers come from the repo-root `.env`, as for the CLI (`.env.example`). Without a usable LLM configuration the app shows a banner and refuses new runs; past runs stay browsable.
* The server listens on 127.0.0.1 only.
````

In `CLAUDE.md` §3, add a table row `| app | app/server/pleatwright_app (FastAPI: event log, tools, guided flow), app/web (React + three.js) |`. In §4, add a short "App" bullet: "`make app` serves the app at http://127.0.0.1:8000 (see `app/README.md`); `make test` also runs the app server tests, and CI's `web` job runs the UI tests and build."

- [ ] **Step 5: Run everything once**

Run, from the repo root: `make PYTHON=$PY test` (about 6-9 minutes; run it in the background and capture the output to a file), and `cd app/web && npm ci && npm test && npm run build`.
Expected: everything PASS. The pipeline suite was 464 passed / 2 skipped before this plan, plus the new tests.

- [ ] **Step 6: Commit**

```bash
git add Makefile .github/workflows/ci.yml requirements.txt requirements-frozen.txt CLAUDE.md app/README.md
git commit -m "app: make targets, CI web job, requirements, docs

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 13: Acceptance (spec §9)

This task is run by the controller (not a subagent), because it includes a live, billed run.

- [ ] **Step 1:** Confirm the Task 1 byte check result (204/204) is recorded in the Task 1 commit message.
- [ ] **Step 2: Fake-provider run in the app.** `make app` has no fake LLM, so the fake-provider run is the seeded one: `record_fixture.py /tmp/pw-seed`, then start the app with `PLEATWRIGHT_RUNS_DIR=/tmp/pw-seed/runs`. Open the run and check the chat, stepper, filmstrip, every viewer and the fold slider (0% to 100%, ▶). Take screenshots.
- [ ] **Step 3: Restart replay.** Stop and restart the server. Reopen the same run and confirm the chat and outputs are identical. Also confirm a run that was interrupted mid-stage (start a fold, kill the server) shows "interrupted" with **Retry**, and that Retry completes it.
- [ ] **Step 4: Live run.** Prerequisite: the owner has removed the stale `ANTHROPIC_WORKSPACE_ID` from the repo-root `.env` (it returns 404 "Workspace not found" with the new key). Check with `GET /v1/models` returning 200 when the headers `llm_client` would send are passed. Then, with `MESH_PROVIDER=hf2`, run `make app`, open http://127.0.0.1:8000 and type "a dog". Review the tree as a human would: approve it, or revise once. Wait for `run_finished`. Record the concept image, the tree rounds, grid, flat-foldability, time per stage, and the number of VLM calls. Take screenshots of the tree review and the folded model.
- [ ] **Step 5:** Update project memory (the corigami-pipeline memory file) with the outcome. Then finish the branch with superpowers:finishing-a-development-branch.
