"""One pack or fold job, run inside a browser worker (spec: browser build).

The worker's filesystem is not the run manager's, so every message the child
puts on its queue goes back to the manager together with the run files the job
wrote since the previous message: post([kind, stage, info, files]), `files`
being {path relative to out_dir, bytes}. out_dir is the same absolute path the
manager uses for the run, so the absolute paths in `info` stay valid there.
"""
import os

import mirror


class _Queue:
    """What foldproc's children need of a multiprocessing queue."""

    def __init__(self, out_dir, post):
        self.out_dir = out_dir
        self.post = post
        self.seen = mirror.snapshot(out_dir)   # the caller's inputs are already here

    def put(self, msg):
        kind, stage, info = msg
        paths, self.seen = mirror.changed(self.out_dir, self.seen)
        # a file the event names always travels: a same-size rewrite inside one
        # filesystem time tick would not show as changed
        if isinstance(info, dict):
            have = set(paths)
            for p in info.get("files") or ():
                rel = os.path.relpath(p, self.out_dir).replace(os.sep, "/")
                if not rel.startswith("../") and os.path.isfile(p) and rel not in have:
                    paths.append(rel)
                    have.add(rel)
        files = {}
        for rel in paths:
            with open(os.path.join(self.out_dir, rel), "rb") as f:
                files[rel] = f.read()
        self.post([kind, stage, info, files])


def run_job(kind, out_dir, kwargs, post):
    """Run `kind` ("fold" | "pack") on out_dir/tree.json, posting each message."""
    from pleatwright_app import foldproc
    child = {"fold": foldproc._child, "pack": foldproc._pack_child}[kind]
    child(os.path.join(out_dir, "tree.json"), out_dir, _Queue(out_dir, post), **kwargs)
