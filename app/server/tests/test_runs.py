import datetime as dt
import os

import pytest

from pleatwright_app.runs import RunStore, status_of

NOW = dt.datetime(2026, 10, 7, 14, 12)


def test_create_names_the_folder_by_time_and_subject(tmp_path):
    s = RunStore(str(tmp_path))
    rid = s.create("a bird", now=NOW)
    assert rid == "2026-10-07-1412-bird"
    assert s.create("a bird", now=NOW) == "2026-10-07-1412-bird-2"
    assert s.log(rid).events[0]["type"] == "run_created"
    assert s.log(rid).events[0]["prompt"] == "a bird"


def test_list_reports_status_from_the_last_event_newest_first(tmp_path):
    s = RunStore(str(tmp_path))
    a = s.create("a bird", now=NOW)
    b = s.create("a crab", now=NOW + dt.timedelta(minutes=1))
    s.log(a).append("awaiting_review", round=0, can_approve=True)
    rows = s.list()
    assert [r["id"] for r in rows] == [b, a]
    assert rows[1]["status"] == "waiting" and rows[0]["status"] == "running"


@pytest.mark.parametrize("last,want", [
    (None, "new"), ({"type": "stage_started"}, "running"),
    ({"type": "awaiting_review"}, "waiting"), ({"type": "run_finished"}, "done"),
    ({"type": "stage_failed"}, "failed")])
def test_status_of(last, want):
    assert status_of(last) == want


def test_file_refuses_paths_outside_the_run(tmp_path):
    s = RunStore(str(tmp_path / "runs"))
    rid = s.create("a bird", now=NOW)
    (tmp_path / "secret.txt").write_text("x")
    os.makedirs(os.path.join(s.dir(rid), "author"))
    open(os.path.join(s.dir(rid), "author", "mesh.glb"), "wb").close()
    assert s.file(rid, "author/mesh.glb").endswith("mesh.glb")
    for bad in ("../../secret.txt", "/etc/passwd", "author/../../../secret.txt", "nope.png"):
        with pytest.raises(FileNotFoundError):
            s.file(rid, bad)
    os.symlink(str(tmp_path / "secret.txt"), os.path.join(s.dir(rid), "link.txt"))
    with pytest.raises(FileNotFoundError):
        s.file(rid, "link.txt")                     # a symlink out is refused too


def test_unknown_or_invalid_ids_are_refused(tmp_path):
    s = RunStore(str(tmp_path))
    for bad in ("nope", "..", "a/b", ""):
        with pytest.raises(FileNotFoundError):
            s.log(bad)


def test_list_skips_a_run_whose_log_is_corrupt(tmp_path):
    from pleatwright_app.events import CorruptLog
    s = RunStore(str(tmp_path))
    good = s.create("a bird", now=NOW)
    bad = s.create("a crab", now=NOW + dt.timedelta(minutes=1))
    path = os.path.join(s.dir(bad), "events.jsonl")
    with open(path, "w") as f:
        f.write('{"seq": 0, "type": "a"}\nnot json\n{"seq": 2, "type": "b"}\n')
    s2 = RunStore(str(tmp_path))                          # a fresh start reads the logs afresh
    assert [r["id"] for r in s2.list()] == [good]
    with pytest.raises(CorruptLog):
        s2.log(bad)


def test_delete_removes_the_run_folder_and_its_row(tmp_path):
    s = RunStore(str(tmp_path))
    a = s.create("a bird", now=NOW)
    b = s.create("a crab", now=NOW)
    s.delete(a)
    assert not os.path.exists(tmp_path / a)
    assert [r["id"] for r in s.list()] == [b]
    with pytest.raises(FileNotFoundError):     # the cached log goes with the folder
        s.log(a)


@pytest.mark.parametrize("bad", ["..", ".", "../x", "", "nope", "a/b"])
def test_delete_refuses_anything_but_a_run(tmp_path, bad):
    """Only a run folder (a valid id holding events.jsonl) can be deleted: never
    the runs root, a sibling folder, or a path that climbs out of it."""
    root = tmp_path / "runs"
    s = RunStore(str(root))
    s.create("a bird", now=NOW)
    (tmp_path / "x").mkdir()
    (tmp_path / "x" / "events.jsonl").write_text("")
    with pytest.raises(FileNotFoundError):
        s.delete(bad)
    assert (tmp_path / "x").exists() and root.exists() and len(s.list()) == 1
