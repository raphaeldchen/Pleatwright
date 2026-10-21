"""Run folders (spec §3.1): one folder per run under the runs root, in the
CLI's `--out DIR` layout plus `events.jsonl` and `model.fold`."""
from __future__ import annotations

import datetime as dt
import logging
import os
import re
import shutil

from . import events as EV

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_log = logging.getLogger(__name__)
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
            except EV.CorruptLog as e:
                _log.warning("skipping unreadable run %s: %s", name, e)
                continue
            first = log.events[0] if log.events else {}
            rows.append({"id": name, "prompt": first.get("prompt", ""),
                         "subject": first.get("subject", name), "created": first.get("t", ""),
                         "status": status_of(log.last)})
        return sorted(rows, key=lambda r: (r["created"], r["id"]), reverse=True)

    def delete(self, run_id: str) -> None:
        """Remove a run's folder and everything in it. `dir` admits only a valid
        run id holding events.jsonl, so nothing else under or above the root."""
        d = self.dir(run_id)
        self._logs.pop(run_id, None)
        shutil.rmtree(d)

    def file(self, run_id: str, rel: str) -> str:
        d = os.path.realpath(self.dir(run_id))
        p = os.path.realpath(os.path.join(d, rel))
        if os.path.commonpath([p, d]) != d or not os.path.isfile(p):
            raise FileNotFoundError(rel)
        return p
