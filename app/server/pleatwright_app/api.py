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
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel

from .events import CorruptLog
from .guided import DEFAULT_MODEL, MODELS, Manager, Refused
from .runs import RunStore, default_root


class NewRun(BaseModel):
    prompt: str
    model: str | None = None


VITE_PORT = 5173


def _origin_ok(origin: str | None, ports=None) -> bool:
    """A browser page may drive a run only from this server or the Vite dev server.
    `ports=None` (tests) allows any port, still on http://127.0.0.1 or localhost only."""
    if not origin:                     # not a browser: no cross-site risk
        return True
    u = urlparse(origin)
    if u.scheme != "http" or u.hostname not in ("127.0.0.1", "localhost"):
        return False
    try:
        port = u.port or 80
    except ValueError:
        return False
    return ports is None or port in ports


def create_app(*, runs_dir=None, client_factory=None, certify_global=True, static_dir=None,
               allowed_hosts=None, allowed_origin_ports=None):
    import env_config
    env_config.load_env()              # before default_root(): .env may set PLEATWRIGHT_RUNS_DIR
    if client_factory is None:
        from pleatwright.__main__ import _client as client_factory
    store = RunStore(runs_dir or default_root())
    manager = Manager(store, client_factory, certify_global=certify_global)

    @asynccontextmanager
    async def lifespan(app):
        manager.recover()
        manager.llm_error()            # builds the client HERE, on the server's loop
        yield
        if manager.busy():
            await manager.cancel(manager.busy())
            await manager.wait_idle()

    app = FastAPI(lifespan=lifespan)
    # DNS-rebinding guard: a page on another origin that resolves to 127.0.0.1 sends its own Host
    app.add_middleware(TrustedHostMiddleware,
                       allowed_hosts=allowed_hosts or ["127.0.0.1", "localhost"])
    app.state.manager = manager

    @app.get("/status")
    async def status():
        err = manager.llm_error()
        return {"llm_ok": err is None, "llm_error": err, "busy": manager.busy(),
                "default_model": DEFAULT_MODEL,
                "models": [{"key": k, "id": i, "label": label} for k, (i, label) in MODELS.items()]}

    @app.get("/runs")
    async def runs():
        return store.list()

    @app.post("/runs")
    async def new_run(body: NewRun):
        try:
            return {"id": await manager.create(body.prompt, body.model)}
        except Refused as e:
            raise HTTPException(409, str(e))

    @app.delete("/runs/{run_id}", status_code=204)
    async def delete_run(run_id: str):
        try:
            await manager.delete(run_id)
        except Refused as e:
            raise HTTPException(409, str(e))
        except FileNotFoundError:
            raise HTTPException(404, "not found")

    @app.get("/runs/{run_id}/files/{rel:path}")
    async def file(run_id: str, rel: str):
        try:
            path = store.file(run_id, rel)
            headers = {"X-Content-Type-Options": "nosniff"}
            if path.lower().endswith(".svg"):
                headers["Content-Security-Policy"] = "sandbox"   # no script if opened directly
            return FileResponse(path, headers=headers)
        except (FileNotFoundError, ValueError):     # ValueError: a NUL byte in the path
            raise HTTPException(404, "not found")

    @app.websocket("/ws/runs/{run_id}")
    async def ws_run(ws: WebSocket, run_id: str, after: int = -1):
        if not _origin_ok(ws.headers.get("origin"), allowed_origin_ports):
            await ws.close(code=1008)
            return
        try:
            log = store.log(run_id)
        except (FileNotFoundError, CorruptLog):
            await ws.close(code=1008)
            return
        await ws.accept()
        after = max(after, -1)         # a negative offset would slice from the tail
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
        def model_of(m):
            v = m.get("model")
            return v if isinstance(v, str) else None

        def choice_of(m):              # the layout picked at the packing card
            v = m.get("choice")
            return v if isinstance(v, str) else None
        actions = {"message": lambda m: manager.message(run_id, str(m.get("text", "")), model_of(m)),
                   "approve": lambda m: manager.approve(run_id, model_of(m), choice_of(m)),
                   "retry": lambda m: manager.retry(run_id, model_of(m)),
                   "cancel": lambda m: manager.cancel(run_id)}
        try:
            while True:
                try:
                    m = await ws.receive_json()
                except (ValueError, KeyError, TypeError):   # not JSON / a binary frame
                    await send({"type": "error", "message": "malformed message: expected JSON text"})
                    continue
                kind = m.get("type") if isinstance(m, dict) else None
                act = actions.get(kind)
                try:
                    if act is None:
                        raise Refused(f"unknown action {kind!r}")
                    await act(m)
                except Refused as e:
                    await send({"type": "error", "message": str(e)})
        except WebSocketDisconnect:
            pass
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            log.unsubscribe(q)

    if static_dir and os.path.isdir(static_dir):
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="ui")
    return app
