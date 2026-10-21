# Pleatwright app: design

Date: 2026-10-07. Status: approved in brainstorming, awaiting spec review.

## 1. Goal

A local app for Pleatwright that looks and feels like Claude Code. One panel is the
conversation; the other shows the outputs: concept image, mesh, tree, packing, crease
patterns, and folded model. It runs the same pipeline as `python -m pleatwright run`
(text → concept image → mesh → VLM tree, which a human approves → Pleatwright → folded
model).

### Owner decisions (brainstorming, 2026-10-07)

| question | decision |
|---|---|
| Who is on the other side of the chat | **Guided now, agent later.** v1 is a fixed pipeline script. Each stage is a tool with a JSON schema, so an agent can be put in front of the same tools later without a rewrite. |
| Platform | **Local web app.** A FastAPI server on the user's machine serves a React page at localhost. |
| History | **Sidebar of past runs.** Each run is a folder on disk. Reopening a run restores its chat and outputs, and lets you resume an unfinished review or retry a failed stage. |
| Output panel | **Layout C:** chat blocks (as in Claude Code), plus a pipeline stepper across the top of the output panel and a filmstrip of outputs along the bottom. |
| Viewers | **3-D where the output is 3-D.** The mesh and folded model are orbitable three.js views, and the model has a fold slider. Images and crease-pattern SVGs pan and zoom. |
| Tree review | **Chat feedback only**, as in the CLI: Approve, or type what is wrong and the VLM revises. The VLM stays the tree's only author. |
| Architecture | **Run folder + event log** (§3). |

## 2. Prior art (CLAUDE.md §0)

| prior art | what it does | adapted / rejected |
|---|---|---|
| Archived web IDE (`web/` on `archive/treemaker-box-pleat`) | FastAPI WebSocket server; React 18, @react-three/fiber, Vite frontend; `.fold` parser and orbit viewer (`creasePattern.ts`, `viewer.ts`); reducer tests (`chat.test.ts`, `review.test.ts`) | **Adapted:** the frontend stack, the camera-fit and orbit code, and the reducer-test pattern. **Rejected:** `web/server.py`, which imports ten or more retired modules (`agent_loop`, `anatomy_oracle`, `square_complete`, ...). |
| FOLD format (`fold` on npm) and Rabbit Ear | The standard JSON format for crease patterns and folded states, including `file_frames`. Rabbit Ear models and renders FOLD in JS. | **Adapted:** FOLD for `model.fold`, so the folded model opens in other origami tools. **Rejected for v1:** Rabbit Ear as a dependency; three.js renders the faces directly. |
| assistant-ui, Vercel's chatbot template, Open WebUI artifacts | A chat with an artifact side panel and streamed tool calls | **Adapted:** the pattern of a typed chat block that opens in a side panel. **Rejected for v1:** the libraries, which assume an LLM token stream; guided mode emits pipeline events. Revisit with the agent. |
| Zoo Text-to-CAD, CadCore | Chat history beside a 3-D view; a browser-native 3-D format; an "edit" endpoint for follow-up messages | **Adapted:** follow-up messages revise the current output (our revise loop), and the browser receives glb (mesh) and FOLD (model). |

## 3. Architecture

```
 browser (React + Vite + three.js)            local server (FastAPI, one process)
┌──────────┬────────────┬───────────────┐     ┌──────────────────────────────────────┐
│ runs     │ chat       │ stepper       │ WS  │ RunManager: one active run at a time │
│ sidebar  │ blocks ◀───┼─ viewer  ◀────┼─────┤   │                                   │
│          │ input ─────┼───────────────┼────▶│   ▼ tools (stage functions)           │
│          │            │ filmstrip     │     │   make_mesh · author_tree ·           │
└──────────┴────────────┴───────────────┘     │   revise_tree · approve_tree · fold   │
        ▲ GET /runs/<id>/files/<path>         │   each: writes files + appends events │
        └─────────────────────────────────────┤──▶ <runs>/<id>/events.jsonl           │
                                              └──────────────────────────────────────┘
```

* **Code location:** a new top-level `app/`, with `app/server/` (Python) and `app/web/`
  (React). It imports the `mcp_harness` modules and leaves their behaviour unchanged,
  apart from the four additive hooks in §4.3.
* **Starting it:** `make app` builds the UI and serves it at `http://127.0.0.1:8000`.
  `make app-dev` runs the server and Vite with hot reload.
* **Runs folder:** `~/Pleatwright/runs/`, overridden by `PLEATWRIGHT_RUNS_DIR`. One
  folder per run, named `<YYYY-MM-DD-HHMM>-<subject>`, where `<subject>` comes from
  `__main__._subject`.

### 3.1 Run folder

```
<runs>/2026-10-07-1412-dog/
  events.jsonl     the run's history; the only state the app relies on
  author/          CLI layout: concept.png, mesh.glb, mesh_views.png, tree sheets, review state
  tree.json        the approved tree (the file `python -m pleatwright fold` reads)
  Dog_48/          the 4 COrigami files, byte-identical to the CLI's
  model.fold       app extra: the folded model and fold-slider frames
```

The `<Subject>_<grid>/` folder contains exactly the CLI's four files. App-only files sit
beside it, never inside. A run started in the app can be finished with
`python -m pleatwright fold DIR/tree.json --out DIR`.

### 3.2 Event log

`events.jsonl` has one JSON object per line: `{seq, t, type, ...}`, where `seq` starts
at 0 and increases by 1 and `t` is ISO-8601 UTC. The log is append-only, and recovery
appends too.

| type | fields | written when |
|---|---|---|
| `run_created` | `prompt`, `subject` | a new run starts |
| `user_message` | `text` | the user sends a message |
| `stage_started` | `stage` | a stage begins |
| `stage_output` | `stage`, `files` (paths relative to the run folder), `summary` (numbers shown in the chat block), `round` (tree only) | a stage produces an output |
| `stage_failed` | `stage`, `error`, `reason` (`error` \| `interrupted` \| `cancelled` \| `exhausted`), `retry` (the tool a Retry button calls, or `null`) | a stage fails, is cancelled, or was cut off by a restart |
| `assistant_message` | `text` | the VLM's tree summary or note, or a guided-flow message |
| `awaiting_review` | `round`, `can_approve` | the review loop pauses for the user |
| `run_finished` | `folder`, `grid`, `solving_ff`, `shaping_ff`, `global_verdict`, `secs` | the fold completes |

Stages: `image`, `mesh`, `tree`, `packing`, `solve`, `shape`, `model`.

Protocol: the browser opens `WS /ws/runs/<id>?after=<seq>`. The server sends every
event after `seq`, then streams new ones. Client→server messages are
`{type: "message", text}`, `{type: "approve"}`, `{type: "retry"}` and
`{type: "cancel"}`. `POST /runs {prompt}` creates a run, and `GET /runs` lists runs with
their status, derived from each run's last event. Reopening a run replays from `seq` 0.

### 3.3 Concurrency

* At most one run computes at a time. The fold is CPU-heavy (minutes per model) and the
  mesh providers share one GPU quota. Starting a second run while one is computing is
  refused with a message; browsing other runs is always allowed.
* The VLM review runs as tasks on uvicorn's event loop, and the `LLMClient` is created
  and used only on that loop. This is the lesson of the duplicate-billing bug fixed in
  #198: one `AsyncOpenAI` client used from more than one event loop silently retried and
  billed twice.
* `make_mesh` runs in a worker thread, because `acquire_mesh` is synchronous network I/O.
* `fold` runs in a **spawned** child process (`multiprocessing` `spawn` context, picklable
  arguments). Its `on_stage` events return to the server through a
  `multiprocessing.Queue`. A process can be killed on Cancel; a thread cannot. Fork is
  not used because of the recorded fork deadlocks in this repo.

## 4. Tools and the guided flow

### 4.1 Tools

Each tool is `async def tool(run, **args) -> dict` and has a JSON-schema description.
In v1 the schemas are documentation; they are what an agent will call later.

| tool | wraps | emits |
|---|---|---|
| `make_mesh(prompt)` | `mesh_acquire.acquire_mesh` (with `progress`, §4.3) | `image` → `author/concept.png`; `mesh` → `author/mesh.glb` |
| `author_tree()` | `gated_pipeline.start` | `tree` round 1 (sheet PNG and `mesh_views.png`), `assistant_message` (the summary or note), `awaiting_review` |
| `revise_tree(feedback)` | `gated_pipeline.resume(state, "revise", feedback)` | `tree` round n, `assistant_message`, `awaiting_review` |
| `approve_tree()` | `gated_pipeline.resume(state, "approve")` + `__main__.tree_file` | writes `tree.json` |
| `fold()` | `pleatwright.pipeline.run(tree.json, run_dir, on_stage=...)` + `export.write_model_fold` | `packing`, `solve`, `shape`, `model` (`model.fold`, `overview.png`), `run_finished` |

The review state is saved to `author/` after every round, as the CLI's `_review` does,
so a paused review survives a server restart. When a file the CLI already writes would
do, the tools reuse it rather than adding a new one.

### 4.2 Guided flow

```
prompt ─▶ make_mesh ─▶ author_tree ─▶ ⏸ review ──Approve──▶ approve_tree ─▶ fold ─▶ done
                                        ▲    │
                                        └────┘ any other message → revise_tree
```

* At the pause the chat shows the VLM's summary, an **Approve** button, and the input
  box. Typed text is revision feedback. The `MAX_REVISIONS` cap and its existing
  behaviour in `gated_pipeline` apply unchanged.
* When `resume` returns `exhausted` (the cap was reached on a revise), the run ends.
  It appends the note as an `assistant_message`, then
  `stage_failed {stage: "tree", reason: "exhausted", retry: null}`.
  `gated_pipeline` refuses to approve an exhausted state, and the app does not work
  around that.
* After `run_finished` or an exhausted review, the input box is replaced by
  **＋ New run**. Guided mode does nothing after the fold.

### 4.3 Pipeline hooks (production changes, all additive, output bytes unchanged)

1. **`pipeline._run` writes each CP as soon as its stage ends**, not all at the end:
   * `packing_cp.svg` after packing;
   * `solving_cp.svg` after solving;
   * `shaping_cp.svg` after shaping;
   * `overview.png` last.

   The folder name `<Subject>_<N>` is known once packing succeeds. `run` and `_run`
   gain `on_stage: Callable[[str, dict], None] | None = None`. It is called as
   `on_stage(stage, {"files": [...], **numbers})` after each stage's file is on disk,
   with stage ∈ `packing`, `solving`, `shaping`, `output`. The file bytes are unchanged
   and only the order of writes moves.
   A stage failure mid-run now leaves a partial `<Subject>_<N>/` folder (previously no
   folder was written).
2. **`shape_and_fold` also returns `"model": m` and `"W0": W0`**, the fold model and the
   world transform its `polys` already use. Existing callers ignore the new keys.
3. **New `pleatwright/export.py`:** `write_model_fold(path, cand, frames=21)` writes a
   FOLD 1.1 file containing:
   * `vertices_coords` (the flat sheet, in grid units, as `fold_input` gives them),
     `faces_vertices`, `edges_vertices`;
   * `edges_assignment` (`B`/`M`/`V`) and `edges_foldAngle`, from the shaping CP's
     `fold_input`. That function already drops unfolded hinges and flat lines, which
     are not creases, so `CPView` (the SVG) is where hinges are shown;
   * `file_frames` at percent = 0, 0.05, ..., 1, each with `vertices_coords` from
     `fold.solve_fold(m, percent)` → `vertex_positions` → `W0`.

   The browser plays these frames back and never re-solves the fold, so there is one
   fold implementation.
4. **`mesh_acquire.acquire_mesh` and the hf2 provider gain an optional
   `progress(stage, path)` callback** (default `None`). It is called with `"image"` once
   the concept image is written and `"mesh"` once the mesh is written. On a cache hit,
   `acquire_mesh` calls `"image"` with the `concept.*` already in the cache key's folder
   (if there is one) and then `"mesh"`. Only hf2 draws a concept image. With `fake`, `hf`
   or `meshy` the `image` stage ends as `stage_output` with no file and the summary
   "no concept image (<provider>)", and the stepper marks it as skipped. The CLI does not
   pass the callback, so the CLI's behaviour is unchanged.

## 5. Frontend

Stack: React 18, TypeScript, Vite, @react-three/fiber and drei, vitest. The orbit and
camera-fit code from the archived `viewer.ts` is adapted.

| component | role |
|---|---|
| `RunsSidebar` | **＋ New run**; runs grouped by day with a status dot (running blue, waiting on you orange, done green, failed red); click to open |
| `Chat` | user bubbles; a `StageBlock` per `stage_output` (thumbnail, name, the summary numbers, click to select); `assistant_message` text; **Approve** while `awaiting_review` (disabled when `can_approve` is false); **Retry** on `stage_failed`; the input box (disabled while computing, with **Cancel** shown instead) |
| `Stepper` | the 7 stages, each done ✓, running (spinner and elapsed time), waiting ⏸, failed ✕ or not yet; click to select |
| `Filmstrip` | one frame per output; stages that have not run yet show as empty dashed frames |
| `Viewer` | picks a viewer by output kind. `ImageView`: concept, mesh views and tree sheets, with pan/zoom and a round selector for the tree. `MeshView`: GLB, orbit, reset camera. `CPView`: the inline SVG with pan/zoom, a legend, and toggles for hinges and M/V colours. `ModelView`: FOLD frames, orbit, a fold slider (0% to 100%) with ▶ play, and a toggle to `overview.png`. |
| `runStore` | one reducer from events to state: runs, blocks, stepper states, the selected output and `followLatest`. The chat, stepper and filmstrip render only from it. |

* **Following the latest output:** a new output is selected automatically. Clicking an
  older block, step or frame pins the selection until the user clicks
  "● follow latest".
* **Theme:** dark by default, light with `prefers-color-scheme: light`. Orange marks
  anything that needs the user.
* **Startup banner:** when the LLM client cannot be configured, a banner says so, and
  **New run** is disabled. The banner never shows a key.

## 6. Failures, cancelling, restarts, security

| failure | shown as | action |
|---|---|---|
| LLM config (`ConfigError`: no or invalid key settings) | startup banner; **New run** disabled. Checked at server start and before every new run, before any mesh call (the CLI's exit 3). | past runs remain browsable |
| Mesh provider (`MeshError`) | `image` or `mesh` ✕, with the provider's message | **Retry** (same prompt) |
| A VLM round fails: truncated output, an API or auth error, or an invalid tree. `gated_pipeline._draft` catches all of these and returns `status: "failed"` with a `note`. | the note as an `assistant_message`, with `can_approve: false` (`resume` refuses to approve a failed state) | type a fix (`revise` from `failed` is allowed on purpose) |
| A Pleatwright stage (`StageError(stage)` or `rec["failure"]`) | that step ✕ | **Retry fold** from `tree.json` |

* **Cancel:**
  * fold: kill the child process;
  * VLM round: `task.cancel()`;
  * mesh: mark the run cancelled and discard the result when it arrives (a remote GPU
    job cannot be aborted).

  Each case appends `stage_failed {reason: "cancelled"}`.
* **Restart recovery:** at startup, for each run whose last event is neither terminal
  (`run_finished`, `stage_failed`) nor `awaiting_review`, append
  `stage_failed {reason: "interrupted"}` with the matching retry. `awaiting_review`
  resumes from the review state in `author/`.
* **Security:**
  * the server binds `127.0.0.1` only;
  * the WebSocket checks the request's `Origin`;
  * `/runs/<id>/files/<path>` serves only paths whose resolved real path is inside the
    runs folder;
  * keys never reach the browser.

## 7. Testing

Owner rules apply: trees come only from the 51 artifact trees
(`fixtures/full17_v3_sticks/`, via `tests/artifact_trees.py`), and tardigrade / water
bear is never a test subject.

| layer | tests |
|---|---|
| Hook 1 (`_run` write order, `on_stage`) | The existing `packing_cp.svg` sha256 pins (bird_1, starfish_1) stay green. `on_stage` fires in the order packing → solving → shaping → output, and each event's files exist when it fires. **Before merge, run locally:** all 51 trees folded and compared byte for byte with `~/Desktop/origami_samples_artifact_trees` (204/204). |
| Hook 2 + `export.py` | On small artifact rolls: the 100% frame matches `cand["polys"]` within 1e-9; the 0% frame is flat (z = 0) and congruent to the CP; the FOLD required keys are present and the faces, edges and frames have consistent lengths. |
| Hook 4 | The fake provider and the hf2 provider (with stubbed Spaces) call `progress` for image and then mesh; a cache hit calls both; with no callback, behaviour is unchanged. |
| Server and tools | pytest with `MESH_PROVIDER=fake` and a fake LLM client returning `authored("dog_0")`. Drives a whole run over the WebSocket: create, mesh, tree, revise, approve, fold, `run_finished`. Checks the event sequence, the folder layout, replay from `after=<seq>`, cancelling the fold kills the child, restart recovery, path-traversal refusal, the `ConfigError` refusal before any mesh call, and one event loop across all VLM calls. |
| Frontend | vitest on `runStore`, fed event logs **recorded from a real fake-provider server run** and committed as fixtures; `tsc` and `vite build`. |
| CI | The app's Python tests join `make test`. A new Node job runs `npm ci`, vitest and `vite build`. Everything stays within the 30-minute budget. |
| Manual | A click-through in the built-in browser with the fake providers, with screenshots. |

## 8. Scope

**In v1:** everything in §3–§7, `make app` and `make app-dev`, and a README section.

**Out of v1:**
* the agent mode (the tool schemas are ready for it);
* a hosted deployment or desktop packaging;
* editing or uploading trees;
* several runs computing at once;
* `--orchestrate` (LLM shaping).

## 9. Acceptance

1. Every test in §7 passes, and the 51-tree byte comparison is 204/204.
2. A fake-provider run in the app goes from a prompt to a folded model that can be
   rotated and unfolded with the slider.
3. Reopening that run after a server restart shows the same chat and outputs.
4. **A live `"a dog"` run in the app** (real FLUX, Hunyuan3D-2 and Claude) reaches
   `run_finished`. This is also the first live end-to-end run of the pipeline on `main`.
   The Anthropic key was replaced on 2026-10-07.
