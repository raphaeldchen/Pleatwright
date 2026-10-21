"""The fold, and the packing of both layouts before it, in a SPAWNED child
process (spec §3.3): a process can be killed on Cancel, a thread cannot, and
fork deadlocks are on record in this repo. The child's `on_stage` events come
back through a multiprocessing queue."""
from __future__ import annotations

import asyncio
import json
import multiprocessing as mp
import os
import queue as _queue
import sys

#: where the packed layouts live in a run (spec 2026-10-16 §8.1): options.json,
#: one packing CP per layout, and card.json (the question and its explanation)
LAYOUT_DIR = "layout"
_LAYOUT_FILES = ("options.json", "symmetric_packing_cp.svg", "smaller_packing_cp.svg")


def _safe(x):
    return json.loads(json.dumps(x, default=str))


def _child(tree_path: str, out_dir: str, q, certify_global: bool, layout: str = "auto",
           chosen_by: str = "flag", options_dir: str | None = None) -> None:
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
                fold_path = os.path.join(out_dir, "model.fold")
                try:
                    os.unlink(fold_path)       # never leave an earlier attempt's file behind
                except FileNotFoundError:
                    pass
                try:
                    EX.write_model_fold(fold_path, cand)
                except Exception as e:         # noqa: BLE001 -- the viewer is optional
                    print(f"warning: model.fold export failed ({type(e).__name__}: {e}); "
                          "continuing without it", file=sys.stderr)
                    try:
                        os.unlink(fold_path)
                    except OSError:
                        pass
            q.put(("stage", s, _safe(info)))
        options = PL.load_options(tree_path, options_dir) if options_dir else None
        rec = PL.run(tree_path, out_dir, certify_global=certify_global, verbose=False,
                     on_stage=on_stage, layout=layout, chosen_by=chosen_by, options=options)
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


def _pack_child(tree_path: str, out_dir: str, q) -> None:
    """Pack both layouts (`pipeline.pack_options`) into `out_dir/layout`; send
    the summary. An earlier packing's files go first, so none can outlive it."""
    import pleatwright_app  # noqa: F401  -- puts mcp_harness on sys.path in the child
    layout_dir = os.path.join(out_dir, LAYOUT_DIR)
    try:
        from pleatwright import pipeline as PL
        for name in _LAYOUT_FILES:
            try:
                os.unlink(os.path.join(layout_dir, name))
            except FileNotFoundError:
                pass
        opts = PL.pack_options(tree_path)
        if opts.verdict == "none":
            q.put(("failed", "packing", "no packing candidate built a base "
                   f"({max(opts.tried.values(), default=0)} tried)"))
            return
        PL.save_options(opts, layout_dir)
    except Exception as e:                             # noqa: BLE001 -- reported, not raised
        cause = e.__cause__ or e
        q.put(("failed", "packing", f"{type(cause).__name__}: {cause}"))
        return
    q.put(("done", None, _safe(opts.summary())))


class _Job:
    """A spawned `target(tree_path, out_dir, q, *extra)` that reports
    ("stage" | "done" | "failed", stage, info) on `q`."""
    what = "child"

    def __init__(self, target, tree_path: str, out_dir: str, *extra):
        ctx = mp.get_context("spawn")
        self.q = ctx.Queue()
        self.proc = ctx.Process(target=target, args=(tree_path, out_dir, self.q, *extra),
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
                    yield ("failed", None, f"the {self.what} process exited with code {self.proc.exitcode}")
                    return
            yield msg
            if msg[0] in ("done", "failed"):
                return

    def cancel(self) -> None:
        if self.proc.is_alive():
            self.proc.kill()
        self.proc.join(5)


class FoldJob(_Job):
    """`pipeline.run`; with `options_dir` it folds the layouts saved there
    (`load_options`, no search) instead of packing again."""
    what = "fold"

    def __init__(self, tree_path: str, out_dir: str, *, certify_global: bool = True,
                 layout: str = "auto", chosen_by: str = "flag", options_dir: str | None = None):
        super().__init__(_child, tree_path, out_dir, certify_global, layout, chosen_by,
                         options_dir)


class PackJob(_Job):
    """`pipeline.pack_options` + `save_options` into `out_dir/layout`."""
    what = "packing"

    def __init__(self, tree_path: str, out_dir: str):
        super().__init__(_pack_child, tree_path, out_dir)
