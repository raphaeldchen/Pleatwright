"""A run's history: `events.jsonl`, one JSON object per line, append-only
(spec §3.2). The chat, stepper, filmstrip and sidebar are all views of it.

Append only from the event loop's thread; worker threads hop over with
`loop.call_soon_threadsafe`, so subscribers see events in `seq` order."""
from __future__ import annotations

import asyncio
import glob
import json
import os
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


class CorruptLog(Exception):
    """A line before the last one in `events.jsonl` is unreadable. The file is left
    as it is (a copy is saved beside it); the run is unreadable, not truncated."""


def _parses(raw: bytes) -> dict | None:
    try:
        ev = json.loads(raw)
    except ValueError:
        return None
    return ev if isinstance(ev, dict) else None


def _back_up(path: str) -> str:
    with open(path, "rb") as f:
        data = f.read()
    for old in glob.glob(glob.escape(path) + ".corrupt-*"):       # one copy per distinct damage
        with open(old, "rb") as f:
            if f.read() == data:
                return old
    dest = f"{path}.corrupt-{datetime.now(timezone.utc):%Y%m%dT%H%M%S%fZ}"
    with open(dest, "wb") as f:
        f.write(data)
    return dest


class EventLog:
    def __init__(self, path: str):
        self.path = path
        self.events: list[dict] = []
        if os.path.exists(path):
            self._load()
        self._subs: set[asyncio.Queue] = set()

    def _load(self) -> None:
        with open(self.path, "rb") as f:
            data = f.read()
        lines = data.split(b"\n")
        tail = lines.pop()                 # b"" when the file ends with a newline
        for i, raw in enumerate(lines):
            if not raw.strip():
                continue
            ev = _parses(raw)
            if ev is None:
                backup = _back_up(self.path)
                raise CorruptLog(f"{self.path}: line {i + 1} is not a JSON event "
                                 f"(the file is untouched; a copy is at {backup})")
            self.events.append(ev)
        if tail.strip():                   # no trailing newline: the server died mid-write
            ev = _parses(tail)
            if ev is not None:             # complete, only its newline is missing: repair
                self.events.append(ev)
                with open(self.path, "ab") as f:
                    f.write(b"\n")
            else:                          # a torn tail: drop only that final line
                with open(self.path, "r+b") as f:
                    f.truncate(len(data) - len(tail))
        elif tail:                         # trailing whitespace only
            with open(self.path, "r+b") as f:
                f.truncate(len(data) - len(tail))

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
