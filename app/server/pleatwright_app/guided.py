"""Guided mode (spec §4.2): a fixed script over the tools. One run computes at
a time; every state the UI shows is derived from the run's event log, so a
restart loses nothing but the work in flight."""
from __future__ import annotations

import asyncio
import json
import logging
import os

from pleatwright.__main__ import ConfigError

from . import tools as T

_TERMINAL = ("run_finished", "stage_failed", "awaiting_review")

#: The VLMs a run may author with: key -> (model id, label). Sonnet 5 is the
#: default: it authored the 51 artifact trees and the first end-to-end run, and
#: Haiku 5.5 (cheaper, about $0.003/tree) did worse in the owner's manual tests.
MODELS = {"sonnet": ("claude-sonnet-5", "Sonnet 5"),
          "haiku": ("claude-haiku-5-5", "Haiku 5.5")}
DEFAULT_MODEL = "sonnet"
_log = logging.getLogger(__name__)
_CACHED = object()      # `_start`'s default: use the client cached for the model


def layout_failed_note(chosen: str | None, error: str | None) -> str:
    """The note on the layout card shown again after the user's chosen layout
    failed to fold.  A stretched layout that could not be certified gets the
    spec 2026-10-22 §6.4 wording: an explicit choice has no fallback."""
    import layout_explain
    if chosen == "stretched" and "StretchUncertified" in str(error):
        return layout_explain.STRETCH_FAILED_NOTE
    return f"The {chosen or 'smaller'} layout failed: {error}"


class Refused(Exception):
    """The action was not taken; the message says why (shown to the user)."""


def phase(log) -> dict:
    last = log.last
    if last is None or last["type"] == "run_created":
        return {"phase": "new"}
    t = last["type"]
    if t == "awaiting_review":
        return {"phase": "review", "stage": last.get("stage") or "tree",
                "can_approve": bool(last["can_approve"])}
    if t == "stage_failed" and last.get("reason") == "exhausted":
        # a run stopped at the 3-revision cap, removed 2026-10-11: back in review
        return {"phase": "review", "stage": "tree", "can_approve": True}
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
        self.clients: dict[str, object] = {}     # model key -> client, built on the loop
        self._active: tuple[str, asyncio.Task, T.Ctx] | None = None

    # ---- state ---------------------------------------------------------------
    def llm_error(self) -> str | None:
        try:
            self._client_for(DEFAULT_MODEL)
        except ConfigError as e:
            return str(e)
        return None

    def _client_for(self, key: str):
        """The client for model `key`, built once (on the calling loop) and reused."""
        if key not in self.clients:
            self.clients[key] = self.client_factory(MODELS[key][0])
        return self.clients[key]

    @staticmethod
    def _model_key(model: str | None) -> str:
        key = model or DEFAULT_MODEL
        if key not in MODELS:
            raise Refused(f"unknown model {model!r}; choose one of {', '.join(MODELS)}")
        return key

    def busy(self) -> str | None:
        if self._active and not self._active[1].done():
            return self._active[0]
        return None

    def recover(self, reason: str = "interrupted",
                error: str = "the server stopped while this stage was running") -> None:
        for row in self.store.list():
            try:
                log = self.store.log(row["id"])
                if log.last and log.last["type"] not in _TERMINAL:
                    stage = current_stage(log) or T.stage_from_disk(self.store.dir(row["id"]))
                    log.append("stage_failed", stage=stage,
                               error=error, reason=reason,
                               retry=T.retry_for(stage, self.store.dir(row["id"])))
            except Exception:                          # noqa: BLE001 -- one bad run must not stop the server
                _log.exception("could not recover run %s", row["id"])

    # ---- actions -------------------------------------------------------------
    async def create(self, prompt: str, model: str | None = None) -> str:
        key = self._model_key(model)
        self._require_llm(key)
        self._refuse_if_busy()
        rid = self.store.create(prompt)
        self.store.log(rid).append("user_message", text=prompt, model=key)

        async def flow(ctx):
            await T.first_mesh(ctx, prompt)
        self._start(rid, flow, key)
        return rid

    async def fold_tree(self, tree: dict, label: str, run_id: str | None = None) -> str:
        """Start a run from an approved `tree` (the free tier's gallery trees):
        no mesh, no authoring, so no LLM client; straight to packing and folding."""
        self._refuse_if_busy()
        rid = self.store.create(label, run_id=run_id, subject=label)
        with open(os.path.join(self.store.dir(rid), "tree.json"), "w") as f:
            json.dump(tree, f, indent=2)
        log = self.store.log(rid)
        log.append("user_message", text=label)
        log.append("stage_output", stage="tree", files=["tree.json"],
                   summary={"approved": True, "source": "gallery"})
        self._start(rid, lambda ctx: T.pack_and_fold(ctx, certify_global=self.certify_global),
                    client=None)                       # never a cached client: the card uses its template
        return rid

    def _try_client(self, key: str) -> None:
        """Build `key`'s client if it can be; without one a flow uses no VLM
        (the layout card falls back to its template explanation)."""
        try:
            self._client_for(key)
        except ConfigError:
            pass

    @staticmethod
    def _chosen_layout(log) -> str | None:
        """The layout the user chose at the current packing's card, if any. A
        choice stands only until the next card or tree approval (which packs
        again). Logs from before the `choice` field are matched by label."""
        names = {label: name for name, label in T.LAYOUT_LABELS.items()}
        for e in reversed(log.events):
            if e["type"] == "user_message" and (e.get("choice") or e.get("text") in names):
                return e.get("choice") or names[e["text"]]
            if e["type"] == "awaiting_review" and e.get("stage") == "packing":
                return None
            if e["type"] == "stage_output" and e.get("stage") == "tree" \
                    and (e.get("summary") or {}).get("approved"):
                return None
        return None

    def _require_llm(self, key: str = DEFAULT_MODEL) -> None:
        try:
            self._client_for(key)
        except ConfigError as e:
            raise Refused(f"authoring is disabled: {e}") from e

    async def message(self, rid: str, text: str, model: str | None = None) -> None:
        key = self._model_key(model)
        self._refuse_if_busy()
        self._require_llm(key)
        log = self.store.log(rid)
        ph = phase(log)
        if ph["phase"] != "review":
            raise Refused("nothing is waiting for review")
        if ph["stage"] == "packing":
            raise Refused("choose one of the layouts on the card")
        log.append("user_message", text=text, model=key)
        if ph["stage"] == "mesh":
            prompt = log.events[0]["prompt"]
            self._start(rid, lambda ctx: T.revise_mesh(ctx, prompt, text), key)
        else:
            self._start(rid, lambda ctx: T.revise_tree(ctx, text), key)

    async def approve(self, rid: str, model: str | None = None,
                      choice: str | None = None) -> None:
        """Approve the mesh, the tree, or (at the layout card) fold `choice`."""
        self._refuse_if_busy()
        log = self.store.log(rid)
        ph = phase(log)
        if ph["phase"] != "review" or not ph["can_approve"]:
            raise Refused("there is nothing to approve: this round produced no tree")
        prompt = log.events[0]["prompt"]
        if ph["stage"] == "packing":
            summary = T.layout_summary(self.store.dir(rid))
            on_card = [k for k in T.LAYOUT_LABELS if summary is None or summary.get(k)]
            if choice not in on_card:
                raise Refused("choose one of the layouts on the card")
            log.append("user_message", text=T.LAYOUT_LABELS[choice], choice=choice)
            self._start(rid, lambda ctx: T.fold(ctx, certify_global=self.certify_global,
                                                layout=choice, chosen_by="user"))
            return
        if ph["stage"] == "mesh":
            key = self._model_key(model)
            self._require_llm(key)                     # the tree is authored next
            log.append("user_message", text="Approve")

            async def mesh_flow(ctx):
                await T.approve_mesh(ctx, prompt)
                await T.author_tree(ctx)
            self._start(rid, mesh_flow, key)
            return
        key = self._model_key(model)
        self._try_client(key)                          # the layout card's explanation
        log.append("user_message", text="Approve")

        async def flow(ctx):
            await T.approve_tree(ctx, prompt)
            await T.pack_and_fold(ctx, certify_global=self.certify_global)
        self._start(rid, flow, key)

    async def retry(self, rid: str, model: str | None = None) -> None:
        key = self._model_key(model)
        self._refuse_if_busy()
        log = self.store.log(rid)
        ph = phase(log)
        if ph["phase"] != "failed" or not ph.get("retry"):
            raise Refused("there is nothing to retry")
        prompt = log.events[0]["prompt"]
        tool = ph["retry"]
        error, chosen = log.last.get("error"), self._chosen_layout(log)
        if tool in ("make_mesh", "author_tree"):
            self._require_llm(key)
        elif tool in ("approve_tree", "fold", "layout"):
            self._try_client(key)                      # the layout card may be asked again

        async def flow(ctx):
            if tool == "make_mesh":
                await T.retry_mesh(ctx, prompt)
            elif tool == "review_mesh":
                T.present_mesh(ctx, T.load_mesh_state(ctx.run_dir))
            elif tool == "author_tree":
                await T.author_tree(ctx)
            elif tool == "review":
                await T.review_again(ctx)
            elif tool == "approve_tree":
                await T.approve_tree(ctx, prompt)
                await T.pack_and_fold(ctx, certify_global=self.certify_global)
            elif tool == "layout":
                summary = T.layout_summary(ctx.run_dir)
                if summary and summary.get("verdict") == "ask":
                    await T.present_layout(ctx, summary, note=layout_failed_note(chosen, error))
                else:                                  # options.json is gone or unreadable: pack again
                    await T.pack_and_fold(ctx, certify_global=self.certify_global)
            else:                                      # fold: reuse this tree's packing
                await T.refold(ctx, choice=chosen, certify_global=self.certify_global)
        self._start(rid, flow, key)

    async def cancel(self, rid: str) -> None:
        if self.busy() != rid:
            raise Refused("nothing is running in this run")
        self._active[2].cancelled.set()
        self._active[1].cancel()

    async def delete(self, rid: str) -> None:
        """Remove a run's folder for good. The active run is refused: cancel it first."""
        if self.busy() == rid:
            raise Refused("this run is still running; cancel it first")
        self.store.delete(rid)

    async def wait_idle(self) -> None:
        if self._active:
            await asyncio.gather(self._active[1], return_exceptions=True)

    # ---- internals -----------------------------------------------------------
    def _refuse_if_busy(self) -> None:
        b = self.busy()
        if b:
            raise Refused(f"another run is already running ({b}); wait or cancel it")

    def _start(self, rid: str, flow, model: str = DEFAULT_MODEL, *, client=_CACHED) -> None:
        """`model` picks the VLM for any authoring the flow does; a flow that never
        authors (approve, fold) ignores it. `client=None` runs the flow with no VLM
        even if one is cached."""
        if client is _CACHED:
            client = self.clients.get(model)
        ctx = T.Ctx(self.store.dir(rid), self.store.log(rid), client,
                    asyncio.get_running_loop(), model=model)

        def fail(error: str, reason: str) -> None:
            """Always append a terminal event, even if working out the stage or the
            retry itself raises (e.g. an unreadable author/state.json)."""
            stage, retry = "image", None
            try:
                stage = current_stage(ctx.log) or T.stage_from_disk(ctx.run_dir)
            except Exception:                          # noqa: BLE001
                _log.exception("could not work out the stage of run %s", rid)
            try:
                retry = T.retry_for(stage, ctx.run_dir)
            except Exception:                          # noqa: BLE001
                _log.exception("could not work out the retry for run %s", rid)
            ctx.emit("stage_failed", stage=stage, error=error, reason=reason, retry=retry)

        async def runner():
            try:
                await flow(ctx)
            except T.ToolFailed:
                pass
            except asyncio.CancelledError:
                ctx.cancelled.set()
                fail("cancelled", "cancelled")
            except Exception as e:                     # noqa: BLE001 -- never lose a run silently
                fail(f"{type(e).__name__}: {e}", "error")
        self._active = (rid, asyncio.create_task(runner()), ctx)
