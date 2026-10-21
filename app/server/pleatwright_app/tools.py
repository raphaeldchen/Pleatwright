"""The pipeline's stages as tools (spec §4.1). Each writes files into the run
folder and appends events; an agent can later call the same functions."""
from __future__ import annotations

import asyncio
import json
import os
import random
import shutil
import threading
from dataclasses import dataclass, field

from pleatwright.__main__ import _dump, tree_file

from .foldproc import LAYOUT_DIR


class ToolFailed(Exception):
    """The tool failed; its `stage_failed` event is already in the log."""


@dataclass
class Ctx:
    run_dir: str
    log: object                     # events.EventLog
    client: object                  # llm_client.LLMClient (used on the loop only)
    loop: asyncio.AbstractEventLoop
    model: str = "sonnet"           # key of the VLM authoring in this action (guided.MODELS)
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
        state = load_state(run_dir)
        if state is None:
            return "author_tree"
        return "approve_tree" if state.get("status") == "approved" else "review"
    return "fold"


def stage_from_disk(run_dir: str) -> str:
    """The stage a run was in, read from its files, for when the event log has no
    open stage (an approval emits none until it is under way)."""
    if not os.path.exists(os.path.join(run_dir, "author", "mesh.glb")):
        return "image"
    if not os.path.exists(os.path.join(run_dir, "author", "state.json")):
        return "tree"
    if not os.path.exists(os.path.join(run_dir, "tree.json")):
        return "tree"
    return "packing"


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
    image_model = mesh_acquire.image_model_label(provider)
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
            if files and image_model:
                summary["image_model"] = image_model
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


# ---- mesh review (spec 2026-10-11) ---------------------------------------------
def load_mesh_state(run_dir: str) -> dict | None:
    try:
        with open(os.path.join(run_dir, "author", "mesh_state.json")) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _save_mesh_state(ctx: Ctx, ms: dict) -> None:
    os.makedirs(ctx.work, exist_ok=True)
    path = os.path.join(ctx.work, "mesh_state.json")
    _dump(ms, path + ".tmp")
    os.replace(path + ".tmp", path)


def _provider_name() -> str:
    return os.environ.get("MESH_PROVIDER", "fake")


def _round_provider(rec: dict) -> str:
    """The provider a round's ratings are filed under: a library mesh is not the
    current provider's work, so its votes must not make it a proven one."""
    import mesh_acquire
    return mesh_acquire.LIBRARY_PROVIDER if rec["provenance"] == "library" else _provider_name()


async def _draw_round(ctx: Ctx, prompt: str, ms: dict, *, description=None, seed=None,
                      best_dir: str | None = None, served: str = "best_rated") -> dict:
    """One mesh round: a draw, or a cached mesh served from `best_dir` (`served` is
    "library" for the subject's reference mesh, "best_rated" for its best proven
    one), copied into the run as concept_r{N}/mesh_r{N}, its record appended to
    `ms`. `ms["pending"]` holds the round's parameters until it lands, so a retry
    redraws it unchanged."""
    import mesh_acquire
    import mesh_ratings
    rnd = len(ms["rounds"])
    provider = mesh_acquire.LIBRARY_PROVIDER if best_dir and served == "library" else _provider_name()
    ms["pending"] = {"description": description, "seed": seed, "best_dir": best_dir, "served": served}
    _save_mesh_state(ctx, ms)
    # What drew the picture: a served folder's own record, else the backend drawing now.
    image_model = mesh_acquire.image_model_label(_provider_name(), best_dir)
    stage, got = ["image"], {}
    ctx.emit("stage_started", stage="image")

    def progress(kind, path):                          # runs on the worker thread
        if ctx.cancelled.is_set():
            return
        if kind == "image":
            files = []
            if path:
                dest = os.path.join(ctx.work, f"concept_r{rnd}" + os.path.splitext(path)[1])
                shutil.copyfile(path, dest)
                files = [ctx.rel(dest)]
                got["concept"] = files[0]
            summary = {"provider": provider} if files else \
                {"skipped": True, "note": f"no concept image ({provider})"}
            if files and image_model:
                summary["image_model"] = image_model
            ctx.emit_threadsafe("stage_output", stage="image", round=rnd, files=files, summary=summary)
            ctx.emit_threadsafe("stage_started", stage="mesh")
            stage[0] = "mesh"
        elif kind == "mesh":
            dest = os.path.join(ctx.work, f"mesh_r{rnd}.glb")
            shutil.copyfile(path, dest)
            got["mesh"], got["cache_dir"] = ctx.rel(dest), os.path.dirname(path)
            summary = _mesh_summary(dest, provider)
            if best_dir:
                r = mesh_ratings.read_ratings(best_dir) or {}
                summary.update(served=served, approvals=r.get("approvals", 0),
                               votes=r.get("approvals", 0) + len(r.get("rejections", [])))
            else:
                summary.update({k: v for k, v in (("description", description), ("seed", seed)) if v is not None})
            got["summary"] = summary
            ctx.emit_threadsafe("stage_output", stage="mesh", round=rnd, files=[got["mesh"]], summary=summary)

    def serve_cached():
        concept, glb = mesh_acquire.cached_files(best_dir)
        progress("image", concept)
        progress("mesh", glb)

    try:
        if best_dir:
            await asyncio.to_thread(serve_cached)
        else:
            await asyncio.to_thread(mesh_acquire.acquire_mesh, prompt, progress=progress,
                                    description=description, seed=seed)
    except (RuntimeError, TimeoutError, ValueError, OSError) as e:
        ctx.emit("stage_failed", stage=stage[0], error=str(e), reason="error", retry="make_mesh")
        raise ToolFailed(str(e)) from e
    rec = {"cache_dir": got["cache_dir"], "description": description, "seed": seed,
           "provenance": served if best_dir else "drawn", "concept": got.get("concept"),
           "mesh": got["mesh"], "summary": got["summary"]}
    ms["rounds"].append(rec)
    ms["pending"] = None
    _save_mesh_state(ctx, ms)
    return rec


def present_mesh(ctx: Ctx, ms: dict) -> None:
    rec = ms["rounds"][-1]
    if rec["provenance"] == "library":
        text = f"This is the reference {ms['subject']} mesh, made from a photograph (shown beside it)."
    elif rec["provenance"] == "best_rated":
        s = rec["summary"]
        text = (f"This is the best-rated {ms['subject']} mesh so far "
                f"({s.get('approvals', 0)} of {s.get('votes', 0)} reviews approved it).")
    elif rec["description"]:
        text = f"Redrawn as “{rec['description']}”."
    else:
        text = f"A {ms['subject']} mesh, drawn from the plain subject."
    ctx.emit("assistant_message",
             text=text + " Does it read as the animal? Approve it, or say what is wrong with it.")
    ctx.emit("awaiting_review", stage="mesh", round=len(ms["rounds"]) - 1, can_approve=True)


async def first_mesh(ctx: Ctx, prompt: str) -> dict:
    """Round 0: the subject's reference mesh from MESH_LIBRARY_DIR if it has one,
    else its best proven mesh, else a default draw."""
    import mesh_acquire
    import mesh_ratings
    ms = {"subject": mesh_ratings.subject_key(prompt), "feedback": [], "rounds": [], "pending": None}
    try:
        library = await asyncio.to_thread(mesh_acquire.library_mesh, ms["subject"])
    except OSError as e:
        ctx.emit("stage_failed", stage="image", error=str(e), reason="error", retry="make_mesh")
        raise ToolFailed(str(e)) from e
    if library:
        await _draw_round(ctx, prompt, ms, best_dir=library, served="library")
    else:
        best = mesh_ratings.best_proven(mesh_acquire.output_dir(), _provider_name(), ms["subject"])
        # A draw that does not reproduce (Gemini) gets its own label, or a second run
        # would re-serve the first run's cached, maybe already rejected, mesh.
        seed = None if best or mesh_acquire.draws_reproduce(_provider_name()) \
            else random.randrange(1, 10**7)
        await _draw_round(ctx, prompt, ms, best_dir=best, seed=seed)
    present_mesh(ctx, ms)
    return ms


async def revise_mesh(ctx: Ctx, prompt: str, feedback: str) -> dict:
    """Rewrite the subject from all feedback so far; if that validates, count the
    rejection and draw the next round with a fresh seed."""
    import mesh_ratings
    import subject_rewrite
    ms = load_mesh_state(ctx.run_dir)
    rec = ms["rounds"][-1]
    ctx.emit("stage_started", stage="mesh")
    concept = os.path.join(ctx.run_dir, rec["concept"]) if rec.get("concept") else None
    try:
        description = await subject_rewrite.rewrite(ctx.client, ms["subject"],
                                                    ms["feedback"] + [feedback], concept)
    except asyncio.CancelledError:
        raise
    except Exception as e:                             # noqa: BLE001 -- RewriteFailed or an LLM/API error:
        # either way nothing was recorded; the user resends their feedback
        error = str(e) if isinstance(e, subject_rewrite.RewriteFailed) else f"{type(e).__name__}: {e}"
        ctx.emit("stage_failed", stage="mesh", error=error, reason="error", retry="review_mesh")
        raise ToolFailed(error) from e
    mesh_ratings.record_verdict(rec["cache_dir"], approved=False, feedback=feedback,
                                run_id=os.path.basename(ctx.run_dir), subject=ms["subject"],
                                provider=_round_provider(rec), prompt=prompt,
                                description=rec["description"], seed=rec["seed"])
    ms["feedback"].append(feedback)
    # Hunyuan3D-2's Space seed slider tops out at MAX_SEED = 10**7.
    await _draw_round(ctx, prompt, ms, description=description, seed=random.randrange(1, 10**7))
    present_mesh(ctx, ms)
    return ms


async def approve_mesh(ctx: Ctx, prompt: str) -> str:
    """Count the approval; the round's mesh becomes author/mesh.glb for the tree."""
    import mesh_ratings
    ms = load_mesh_state(ctx.run_dir)
    rnd, rec = len(ms["rounds"]) - 1, ms["rounds"][-1]
    mesh_ratings.record_verdict(rec["cache_dir"], approved=True,
                                run_id=os.path.basename(ctx.run_dir), subject=ms["subject"],
                                provider=_round_provider(rec), prompt=prompt,
                                description=rec["description"], seed=rec["seed"])
    path = os.path.join(ctx.work, "mesh.glb")
    shutil.copyfile(os.path.join(ctx.run_dir, rec["mesh"]), path)
    ctx.emit("stage_output", stage="mesh", round=rnd, files=[rec["mesh"]],
             summary=dict(rec["summary"], approved=True))
    return path


async def retry_mesh(ctx: Ctx, prompt: str) -> dict:
    """After a failed draw: redraw the pending round unchanged, then review again."""
    ms = load_mesh_state(ctx.run_dir)
    if ms is None:
        return await first_mesh(ctx, prompt)
    p = ms.get("pending")
    if p is not None or not ms["rounds"]:
        p = p or {}
        await _draw_round(ctx, prompt, ms, description=p.get("description"),
                          seed=p.get("seed"), best_dir=p.get("best_dir"),
                          served=p.get("served", "best_rated"))
    present_mesh(ctx, ms)
    return ms


def load_state(run_dir: str) -> dict | None:
    p = os.path.join(run_dir, "author", "state.json")
    if not os.path.exists(p):
        return None
    try:
        with open(p) as f:
            return json.load(f)
    except (ValueError, OSError):      # JSONDecodeError is a ValueError: a torn or unreadable file
        return None


def _save(ctx: Ctx, state: dict) -> None:
    """Atomic: a crash mid-write must not leave a torn state.json."""
    path = os.path.join(ctx.work, "state.json")
    tmp = path + ".tmp"
    _dump(state, tmp)
    os.replace(tmp, path)


def present(ctx: Ctx, state: dict) -> None:
    """Emit one review round from a gated_pipeline state (spec §4.1, §4.2)."""
    rnd = state["round"]
    # `exhausted` only in a state saved before the revision cap was removed
    # (2026-10-11): it is shown, and continued, as a review.
    if state["status"] in ("awaiting_review", "exhausted"):
        paths = (state.get("sheet_png"), os.path.join(ctx.work, "mesh_views.png"))
        files = [ctx.rel(p) for p in paths if p and os.path.exists(p)]
        tree = state.get("tree") or {}
        summary = {"flaps": len(tree.get("leaves") or []),
                   "pairs": len(tree.get("pairs") or [])}
        if state.get("model"):             # the model that WROTE this round, not the
            summary["model"] = state["model"]   # one picked for the current action
        ctx.emit("stage_output", stage="tree", round=rnd, files=files, summary=summary)
        ctx.emit("assistant_message", text=state.get("summary") or "")
        ctx.emit("awaiting_review", stage="tree", round=rnd, can_approve=True)
    elif state["status"] == "failed":
        ctx.emit("assistant_message", text=state.get("note") or "this round failed")
        ctx.emit("awaiting_review", stage="tree", round=rnd, can_approve=False)


async def author_tree(ctx: Ctx) -> dict:
    import gated_pipeline as GP
    ctx.emit("stage_started", stage="tree")
    try:
        state = await GP.start(os.path.join(ctx.work, "mesh.glb"), client=ctx.client,
                               out_dir=ctx.work)
        state["model"] = ctx.model
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
        state["model"] = ctx.model
    except Exception as e:                             # noqa: BLE001
        ctx.emit("stage_failed", stage="tree", error=f"{type(e).__name__}: {e}",
                 reason="error", retry="review")
        raise ToolFailed(str(e)) from e
    _save(ctx, state)
    present(ctx, state)
    return state


async def review_again(ctx: Ctx) -> dict:
    """Show the current round again. An APPROVED tree is reopened for review, so a
    retry "review" after approval sends the human back to the tree to revise."""
    state = load_state(ctx.run_dir)
    if state["status"] == "approved":
        state["status"] = "awaiting_review"
        _save(ctx, state)
    present(ctx, state)
    return state


async def approve_tree(ctx: Ctx, prompt: str) -> str:
    import gated_pipeline as GP
    ctx.emit("stage_started", stage="tree")
    state = load_state(ctx.run_dir)
    if state["status"] != "approved":      # else an earlier attempt crashed after saving
        state = await GP.resume(state, "approve", client=ctx.client, out_dir=ctx.work)
        _save(ctx, state)
    path = os.path.join(ctx.run_dir, "tree.json")
    _dump(tree_file(state, prompt), path)
    sheet = os.path.join(ctx.work, f"tree_round{state['round']}.png")
    files = [ctx.rel(p) for p in (sheet, path) if os.path.exists(p)]
    ctx.emit("stage_output", stage="tree", round=state["round"], files=files,
             summary={"approved": True})
    return path


_UI_STAGE = {"load": "packing", "packing": "packing", "solving": "solve",
             "shaping": "shape", "output": "model"}
_NEXT = {"packing": "solve", "solving": "shape", "shaping": "model"}


def model_files(run_dir: str, *overview_rel: str) -> list[str]:
    """The model stage's files: `model.fold` only if the export wrote one (a failed
    export is a warning in the child, not a failed fold), then the overview."""
    have = os.path.isfile(os.path.join(run_dir, "model.fold"))
    return [*(["model.fold"] if have else []), *overview_rel]


async def fold(ctx: Ctx, *, certify_global: bool = True, layout: str = "auto",
               chosen_by: str = "flag", _packing_started: bool = False) -> dict:
    """Fold tree.json, from the layouts saved in `layout/` when they are there
    (`pack_and_fold`; nothing is searched twice). A failed fold of a chosen
    layout retries back to the layout card (spec 2026-10-16 §5.2a)."""
    from .foldproc import FoldJob
    if not _packing_started:
        ctx.emit("stage_started", stage="packing")
    current = "packing"                  # the UI stage last started
    options_dir = os.path.join(ctx.run_dir, LAYOUT_DIR)
    if not os.path.isfile(os.path.join(options_dir, "options.json")):
        options_dir = None
    job = FoldJob(os.path.join(ctx.run_dir, "tree.json"), ctx.run_dir,
                  certify_global=certify_global, layout=layout, chosen_by=chosen_by,
                  options_dir=options_dir)
    job.start()
    try:
        async for kind, stage, info in job.messages():
            if kind == "stage":
                files = [ctx.rel(p) for p in info.pop("files")]
                info.pop("folder", None)
                if stage == "output":
                    files = model_files(ctx.run_dir, *files)
                ctx.emit("stage_output", stage=_UI_STAGE[stage], files=files, summary=info)
                if stage in _NEXT:
                    current = _NEXT[stage]
                    ctx.emit("stage_started", stage=current)
            elif kind == "failed":
                # stage None = the child died without a message: blame the stage it was in
                ctx.emit("stage_failed", stage=_UI_STAGE.get(stage, "packing") if stage else current,
                         error=info, reason="error",
                         retry="fold" if layout == "auto" else "layout")
                raise ToolFailed(info)
            else:
                info["folder"] = ctx.rel(info["folder"])
                ctx.emit("run_finished", **info)
                return info
        raise ToolFailed("the fold ended without a result")
    finally:
        await asyncio.to_thread(job.cancel)   # idempotent; its join must not block the loop


# ---- the packing layout choice (spec 2026-10-16 §7, §8.1) ------------------------
#: the user's words for each layout on the card (logged as their message)
LAYOUT_LABELS = {"smaller": "Smaller grid", "symmetric": "Mirror-symmetric"}


async def pack_and_fold(ctx: Ctx, *, certify_global: bool = True) -> dict:
    """Pack both layouts in a child process. When the 10% rule asks, stop at the
    layout card and return the card; otherwise fold the rule's layout and return
    its result."""
    from .foldproc import PackJob
    ctx.emit("stage_started", stage="packing")
    job = PackJob(os.path.join(ctx.run_dir, "tree.json"), ctx.run_dir)
    job.start()
    summary = None
    try:
        async for kind, _stage, info in job.messages():
            if kind == "failed":
                ctx.emit("stage_failed", stage="packing", error=info, reason="error", retry="fold")
                raise ToolFailed(info)
            if kind == "done":
                summary = info
    finally:
        await asyncio.to_thread(job.cancel)
    if summary is None:
        raise ToolFailed("packing ended without a result")
    if summary["verdict"] == "ask":
        return await present_layout(ctx, summary)
    return await fold(ctx, certify_global=certify_global, layout="auto", _packing_started=True)


def _read_json(path: str):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def layout_summary(run_dir: str) -> dict | None:
    """The saved `pack_options` summary of the run's last packing."""
    doc = _read_json(os.path.join(run_dir, LAYOUT_DIR, "options.json"))
    return doc["summary"] if doc else None


def _subject_and_pairs(run_dir: str) -> tuple[str, list]:
    t = _read_json(os.path.join(run_dir, "tree.json")) or {}
    return t.get("subject") or t.get("roll") or "tree", [list(p) for p in t.get("pairs") or []]


async def present_layout(ctx: Ctx, summary: dict, *, note: str | None = None) -> dict:
    """Ask which layout to fold: the card and its explanation, made once per
    packing and kept in layout/card.json, so a reload, a retry or a re-pack to the
    same layouts shows the same text and costs no second VLM call."""
    import layout_explain
    subject, pairs = _subject_and_pairs(ctx.run_dir)
    key = {"summary": summary, "subject": subject, "pairs": pairs}
    path = os.path.join(ctx.run_dir, LAYOUT_DIR, "card.json")
    saved = _read_json(path)
    if saved and all(saved.get(k) == v for k, v in key.items()):
        card, text = saved["card"], saved["explanation"]
    else:
        card = layout_explain.card(summary)
        if ctx.client is None:
            text = layout_explain.template_explanation(summary, subject, pairs)
        else:
            text = await layout_explain.explain(ctx.client, summary, subject, pairs)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        _dump({**key, "card": card, "explanation": text}, path + ".tmp")
        os.replace(path + ".tmp", path)
    files = [f"{LAYOUT_DIR}/{name}_packing_cp.svg" for name in ("smaller", "symmetric")]
    ctx.emit("stage_output", stage="packing", files=files,
             summary={"layout_choice": card, "explanation": text, "note": note})
    ctx.emit("awaiting_review", stage="packing", round=0, can_approve=True, card=card,
             explanation=text, note=note)
    return card
