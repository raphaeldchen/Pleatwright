"""The fold tool, on artifact tree bird_1 (about 6 s per fold)."""
import asyncio
import json
import os
import shutil
import signal

import pytest

from artifact_trees import path as artifact_path
from pleatwright_app import tools as T
from pleatwright_app.events import EventLog
from pleatwright_app.foldproc import FoldJob, PackJob


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
    with open(os.path.join(ctx.run_dir, "model.fold")) as f:
        assert json.load(f)["file_spec"] == 1.1


def test_a_failing_fold_is_logged_with_retry_fold(tmp_path):
    async def main():
        ctx = _ctx(tmp_path)
        os.remove(os.path.join(ctx.run_dir, "tree.json"))
        with pytest.raises(T.ToolFailed):
            await T.fold(ctx, certify_global=False)
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
        assert job.proc.is_alive()
        job.cancel()
        return job.proc
    proc = asyncio.run(main())
    assert not proc.is_alive() and proc.exitcode == -signal.SIGKILL


def _dying_child(tree_path, out_dir, q, certify_global, *_):   # module level: spawn pickles it
    q.put(("stage", "packing", {"files": [], "grid": 1}))
    q.close()
    q.join_thread()                      # flush the message, then die without any final one
    os._exit(7)


def _capture_jobs(monkeypatch):
    import pleatwright_app.foldproc as FP
    jobs = []
    real = FP.FoldJob

    class Spy(real):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            jobs.append(self)
    monkeypatch.setattr(FP, "FoldJob", Spy)
    return jobs


def test_cancelling_the_fold_task_propagates_and_kills_the_child(tmp_path, monkeypatch):
    jobs = _capture_jobs(monkeypatch)

    async def main():
        ctx = _ctx(tmp_path)
        shutil.copyfile(artifact_path("starfish_1"), os.path.join(ctx.run_dir, "tree.json"))
        task = asyncio.ensure_future(T.fold(ctx, certify_global=True))
        await asyncio.sleep(1.0)
        assert jobs and jobs[0].proc.is_alive()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    asyncio.run(main())
    assert not jobs[0].proc.is_alive() and jobs[0].proc.exitcode == -signal.SIGKILL


def test_a_finished_fold_leaves_no_live_child(tmp_path, monkeypatch):
    jobs = _capture_jobs(monkeypatch)

    async def main():
        ctx = _ctx(tmp_path)
        await T.fold(ctx, certify_global=False)
    asyncio.run(main())
    assert not jobs[0].proc.is_alive() and jobs[0].proc.exitcode is not None


def test_a_child_that_dies_silently_fails_the_stage_it_was_in(tmp_path, monkeypatch):
    """The synthesized 'exited with code' failure carries the last started stage."""
    import pleatwright_app.foldproc as FP

    monkeypatch.setattr(FP, "_child", _dying_child)

    async def main():
        ctx = _ctx(tmp_path)
        with pytest.raises(T.ToolFailed):
            await T.fold(ctx, certify_global=False)
        return ctx
    last = asyncio.run(main()).log.last
    assert last["type"] == "stage_failed" and last["stage"] == "solve"   # packing had finished
    assert "code 7" in last["error"]


def test_cancelling_the_job_does_not_block_the_event_loop_thread(tmp_path, monkeypatch):
    import threading
    import pleatwright_app.foldproc as FP
    where = []
    real = FP.FoldJob

    class Spy(real):
        def cancel(self):
            where.append(threading.current_thread() is threading.main_thread())
            super().cancel()
    monkeypatch.setattr(FP, "FoldJob", Spy)

    async def main():
        await T.fold(_ctx(tmp_path), certify_global=False)
    asyncio.run(main())
    assert where == [False]


def test_model_files_omits_a_model_fold_that_was_not_written(tmp_path):
    overview = "Bird roll 1_40/overview.png"
    assert T.model_files(str(tmp_path), overview) == [overview]
    (tmp_path / "model.fold").write_text("{}")
    assert T.model_files(str(tmp_path), overview) == ["model.fold", overview]


def test_a_failing_model_fold_export_is_a_warning_not_a_failed_fold(tmp_path, monkeypatch, capsys):
    """_child run in-process (it needs no spawn to be exercised)."""
    import queue
    import pleatwright_app.foldproc as FP
    from pleatwright import export as EX

    def boom(path, cand, frames=None):
        with open(path, "w") as f:
            f.write("{partial")                  # a half-written file must not survive
        raise OSError("disk full")
    monkeypatch.setattr(EX, "write_model_fold", boom)
    d = tmp_path / "run"
    d.mkdir()
    shutil.copyfile(artifact_path("bird_1"), d / "tree.json")
    q = queue.Queue()
    FP._child(str(d / "tree.json"), str(d), q, False)
    msgs = []
    while not q.empty():
        msgs.append(q.get())
    assert msgs[-1][0] == "done" and all(m[0] != "failed" for m in msgs)
    assert not (d / "model.fold").exists()
    assert "model.fold export failed" in capsys.readouterr().err


async def _drain(job):
    job.start()
    try:
        return [m async for m in job.messages()]
    finally:
        job.cancel()


def test_pack_job_saves_both_layouts_of_an_ask_tree(tmp_path):
    """dolphin_0: symmetric grid 50, unmirrored 32 (gain 1.5625): the rule asks."""
    d = tmp_path / "run"
    d.mkdir()
    shutil.copyfile(artifact_path("dolphin_0"), d / "tree.json")
    msgs = asyncio.run(_drain(PackJob(str(d / "tree.json"), str(d))))
    kind, _, summary = msgs[-1]
    assert kind == "done" and summary["verdict"] == "ask"
    assert (summary["symmetric"]["grid"], summary["smaller"]["grid"]) == (50, 32)
    for f in ("options.json", "smaller_packing_cp.svg", "symmetric_packing_cp.svg"):
        assert (d / T.LAYOUT_DIR / f).is_file()
    assert json.load(open(d / T.LAYOUT_DIR / "options.json"))["summary"] == summary


def test_pack_job_reports_a_bad_tree_as_a_packing_failure(tmp_path):
    msgs = asyncio.run(_drain(PackJob(str(tmp_path / "missing.json"), str(tmp_path))))
    assert msgs[-1][:2] == ("failed", "packing")


def test_a_fold_from_saved_options_folds_the_chosen_layout(tmp_path):
    from pleatwright import pipeline as PL
    d = tmp_path / "run"
    d.mkdir()
    shutil.copyfile(artifact_path("dolphin_0"), d / "tree.json")
    PL.save_options(PL.pack_options(str(d / "tree.json")), str(d / T.LAYOUT_DIR))

    async def main():
        ctx = T.Ctx(str(d), EventLog(str(d / "events.jsonl")), None, asyncio.get_running_loop())
        return ctx, await T.fold(ctx, certify_global=False, layout="smaller", chosen_by="user")
    ctx, fin = asyncio.run(main())
    assert fin["grid"] == 32
    packing = next(e for e in ctx.log.events if e["type"] == "stage_output" and e["stage"] == "packing")
    assert packing["summary"]["layout"]["reason"] == "user"
    assert packing["summary"]["tried"] == 1          # restored from options.json (Ruling 7)
