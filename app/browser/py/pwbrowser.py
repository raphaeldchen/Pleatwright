"""The manager worker's Python side in the browser build (spec: browser build §4.1).

The run manager (`guided.Manager`) runs here over an in-memory runs folder.
`boot` fills that folder from browser storage, `handle` runs the UI's commands,
and one pump per run posts each event to the UI and copies the run's new or
changed files back to storage. A pack or fold job runs in a fresh job worker
(`BrowserJob`, run there by `jobchild.run_job`), not in a spawned process.

`bridge` is the JS side: `post(msg)`, `async put_files(run_id, {rel: bytes})`,
`async run_ids()`, `async hydrate(run_id) -> {rel: bytes}`,
`start_job(job_id, kind, out_dir, files, kwargs)`,
`async next_job_message(job_id) -> list` and `cancel_job(job_id)`.
Pyodide has no threads, so nothing here may use them (no `asyncio.to_thread`).
"""
from __future__ import annotations

import asyncio
import inspect
import io
import logging
import os
import uuid
import zipfile

import pleatwright_app  # noqa: F401  -- puts mcp_harness on sys.path
from pleatwright.__main__ import ConfigError
from pleatwright_app import foldproc
from pleatwright_app.guided import Manager, Refused
from pleatwright_app.runs import RunStore

import mirror

#: what a job's failure says when its worker died (most often out of memory)
DEAD_WORKER = "too large to fold in this browser"
NO_LLM = "Design your own arrives with sign-in"

_log = logging.getLogger(__name__)
_bridge = None
_manager: Manager | None = None
_pumps: dict[str, "_Pump"] = {}


def _no_client(model):
    raise ConfigError(NO_LLM)


def _py(x):
    """A value from JS as Python (a Pyodide JsProxy has `to_py`); Python values pass through."""
    return x.to_py() if hasattr(x, "to_py") else x


def _write_files(root: str, files: dict) -> None:
    """Write {path relative to root: bytes} under root; a path that leaves root is skipped."""
    root = os.path.normpath(root)
    for rel, data in files.items():
        dest = os.path.normpath(os.path.join(root, rel))
        if os.path.commonpath([dest, root]) != root or dest == root:
            _log.warning("skipping %r: not inside %s", rel, root)
            continue
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(bytes(data))


def _tree_before_layouts(run_dir: str) -> None:
    """Make tree.json older than every layout/ file. Storage returns a run's files in key
    order, so tree.json is written after layout/options.json, and `tools.saved_options`
    (options strictly newer than the tree) would pack again and re-ask the layout card.
    Here a run's tree.json is written once, by `fold_tree`, before anything is packed, so
    its stored layouts were packed from it."""
    tree = os.path.join(run_dir, "tree.json")
    layout = os.path.join(run_dir, "layout")
    if not os.path.isfile(tree):
        return
    times = [os.stat(os.path.join(d, n)).st_mtime_ns for d, _, names in os.walk(layout) for n in names]
    if times:
        ns = min(times) - 1_000_000                # 1 ms: coarser clocks still order them
        os.utime(tree, ns=(ns, ns))


def _read(root: str, rels) -> dict:
    out = {}
    for rel in rels:
        with open(os.path.join(root, rel), "rb") as f:
            out[rel] = f.read()
    return out


class BrowserJob:
    """`foldproc.JOB_FACTORY` in the browser: the job runs in a job worker that
    gets the run's tree.json and layout/ and writes at the same absolute
    out_dir, so the paths in its messages stay valid here."""

    def __init__(self, kind: str, tree_path: str, out_dir: str, **kw):
        self.kind, self.tree_path, self.out_dir, self.kw = kind, tree_path, out_dir, kw
        self.job_id = uuid.uuid4().hex
        self._closed = False

    def start(self) -> None:
        with open(self.tree_path, "rb") as f:
            files = {"tree.json": f.read()}
        layout = os.path.join(self.out_dir, foldproc.LAYOUT_DIR)
        files.update(_read(self.out_dir, (f"{foldproc.LAYOUT_DIR}/{rel}"
                                          for rel in mirror.snapshot(layout))))
        _bridge.start_job(self.job_id, self.kind, self.out_dir, files, dict(self.kw))

    async def messages(self):
        while True:
            msg = list(_py(await _bridge.next_job_message(self.job_id)))
            kind, stage, info = msg[:3]
            if kind == "dead":
                yield ("failed", None, DEAD_WORKER)
                return
            files = (msg[3] if len(msg) > 3 else None) or {}       # JS null too
            _write_files(self.out_dir, files)
            if self.kind == "fold" and (kind, stage) == ("stage", "shaping") \
                    and "model.fold" not in files:
                # the job worker unlinked it and its export failed (foldproc._child)
                try:
                    os.unlink(os.path.join(self.out_dir, "model.fold"))
                except FileNotFoundError:
                    pass
            yield (kind, stage, info)
            if kind in ("done", "failed"):
                return

    async def aclose(self) -> None:
        if self._closed:
            return
        self._closed = True
        r = _bridge.cancel_job(self.job_id)
        if inspect.isawaitable(r):
            await r


class _Pump:
    """Forwards one run's events: put the run files that changed since the
    last put (plus events.jsonl and the files the event names, which a
    same-size rewrite could hide from `mirror`) into storage, then post the
    event to the UI."""

    def __init__(self, rid: str, snap: dict, after: int):
        self.rid, self.snap = rid, snap
        self.dir = os.path.join(_manager.store.root, rid)
        self.log = _manager.store.log(rid)
        self.q = self.log.subscribe()
        for ev in self.log.after(after):          # same tick as subscribe: no gap, no duplicate
            self.q.put_nowait(ev)
        self.task = asyncio.create_task(self._run())

    async def _run(self) -> None:
        try:
            while True:
                ev = await self.q.get()
                try:
                    await self._forward(ev)
                except Exception:                  # noqa: BLE001 -- a failed put must not stop the events
                    _log.exception("could not forward event %s of run %s", ev.get("seq"), self.rid)
                finally:
                    self.q.task_done()
        finally:
            self.log.unsubscribe(self.q)

    async def _forward(self, ev: dict) -> None:
        # files first: the UI loads what an event names from storage at once
        try:
            await self._put(ev)
        finally:                                   # a failed put still delivers the event
            _bridge.post({"type": "event", "run_id": self.rid, "event": ev})

    async def _put(self, ev: dict) -> None:
        paths, snap = mirror.changed(self.dir, self.snap)
        want = set(paths) | {"events.jsonl"}
        for rel in ev.get("files") or ():
            norm = os.path.normpath(rel).replace(os.sep, "/")
            if not norm.startswith("../") and not os.path.isabs(norm):
                want.add(norm)
        rels = sorted(r for r in want if os.path.isfile(os.path.join(self.dir, r)))
        await _bridge.put_files(self.rid, _read(self.dir, rels))
        self.snap = snap                           # only once stored: a failed put is retried


def _watch(rid: str, snap: dict, after: int) -> None:
    if rid not in _pumps:
        _pumps[rid] = _Pump(rid, snap, after)


async def _drain() -> None:
    for p in list(_pumps.values()):
        await p.q.join()


async def boot(bridge, runs_root: str) -> None:
    """Write every stored run into runs_root, start the Manager over it, and
    mark the runs a closed tab left mid-stage as interrupted (`recover`)."""
    global _bridge, _manager
    os.makedirs(runs_root, exist_ok=True)
    root = os.path.realpath(runs_root)
    for rid in _py(await bridge.run_ids()):
        if not rid or "/" in rid or rid in (".", ".."):
            _log.warning("skipping stored run %r: not a run id", rid)
            continue
        _write_files(os.path.join(root, rid), _py(await bridge.hydrate(rid)))
        _tree_before_layouts(os.path.join(root, rid))
    _bridge = bridge
    _manager = Manager(RunStore(root), client_factory=_no_client)
    foldproc.JOB_FACTORY = BrowserJob
    _pumps.clear()
    for row in _manager.store.list():
        rid = row["id"]
        last = _manager.store.log(rid).last
        _watch(rid, mirror.snapshot(os.path.join(root, rid)), last["seq"] if last else -1)
    _manager.recover()                             # its events go through the pumps
    await _drain()


async def settle() -> None:
    """Return once the Manager is idle and every event has been posted and stored."""
    await _manager.wait_idle()
    await _drain()


def _check_run(rid) -> None:
    try:
        _manager.store.dir(rid)
    except FileNotFoundError:
        raise Refused(f"no such run: {rid}") from None


def _zip(rid: str) -> dict:
    """The run's output folder (`<Subject>_<grid>/`), zipped in that layout."""
    done = [e for e in _manager.store.log(rid).events if e["type"] == "run_finished"]
    if not done:
        raise Refused("this run has no finished model to download")
    folder = done[-1]["folder"]
    src = os.path.join(_manager.store.dir(rid), folder)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in sorted(mirror.snapshot(src)):
            z.write(os.path.join(src, rel), f"{folder}/{rel}")
    return {"ok": True, "name": f"{folder}.zip", "bytes": buf.getvalue()}


async def handle(cmd: dict) -> dict:
    """Run one UI command: {"ok": True, ...}, or {"ok": False, "error": ...}
    when it was not taken (`Refused`, a missing run, an unknown op). Any other
    error (a bad or missing argument, a CorruptLog) propagates as an exception
    the JS host must catch."""
    cmd = _py(cmd)
    m, op = _manager, cmd.get("op")
    try:
        if op == "status":
            return {"ok": True, "llm_ok": False, "llm_error": NO_LLM, "busy": m.busy()}
        if op == "list":
            return {"ok": True, "runs": m.store.list()}
        if op == "fold_tree":
            rid = await m.fold_tree(cmd["tree"], cmd["label"], run_id=cmd.get("run_id"))
            _watch(rid, {}, -1)                    # before the flow runs: every event is caught
            return {"ok": True, "id": rid}
        if op not in ("approve", "retry", "cancel", "delete", "after", "zip"):
            return {"ok": False, "error": f"unknown op {op!r}"}
        rid = cmd["run_id"]
        _check_run(rid)
        if op == "approve":
            await m.approve(rid, choice=cmd.get("choice"))
        elif op == "retry":
            await m.retry(rid)
        elif op == "cancel":
            await m.cancel(rid)
        elif op == "delete":
            await m.delete(rid)
            pump = _pumps.pop(rid, None)
            if pump:
                pump.task.cancel()
                await asyncio.gather(pump.task, return_exceptions=True)
        elif op == "after":
            return {"ok": True, "events": m.store.log(rid).after(max(int(cmd.get("seq", -1)), -1))}
        else:
            return _zip(rid)
        return {"ok": True}
    except Refused as e:
        return {"ok": False, "error": str(e)}
