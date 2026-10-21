import asyncio
import json

from pleatwright_app.events import EventLog


def test_append_numbers_events_and_persists_them(tmp_path):
    p = tmp_path / "events.jsonl"
    log = EventLog(str(p))
    a = log.append("run_created", prompt="a bird", subject="bird")
    b = log.append("stage_started", stage="image")
    assert (a["seq"], b["seq"]) == (0, 1) and a["type"] == "run_created" and "t" in a
    assert [json.loads(l)["seq"] for l in p.read_text().splitlines()] == [0, 1]
    again = EventLog(str(p))
    assert again.events == log.events and again.last["stage"] == "image"
    assert [e["seq"] for e in again.after(0)] == [1] and again.after(-1) == again.events


def test_a_torn_last_line_is_ignored_on_reload(tmp_path):
    p = tmp_path / "events.jsonl"
    EventLog(str(p)).append("run_created", prompt="a bird", subject="bird")
    with open(p, "a") as f:
        f.write('{"seq": 1, "ty')            # the server died mid-write
    log = EventLog(str(p))
    assert len(log.events) == 1
    assert log.append("user_message", text="x")["seq"] == 1


def test_subscribers_receive_new_events_in_order(tmp_path):
    async def main():
        log = EventLog(str(tmp_path / "e.jsonl"))
        q = log.subscribe()
        log.append("a")
        log.append("b")
        got = [(await q.get())["type"], (await q.get())["type"]]
        log.unsubscribe(q)
        log.append("c")
        return got, q.qsize()
    assert asyncio.run(main()) == (["a", "b"], 0)


def _write(p, text):
    with open(p, "w") as f:
        f.write(text)


def _line(seq, type="a"):
    return json.dumps({"seq": seq, "t": "x", "type": type}) + "\n"


def test_a_valid_last_line_without_a_newline_is_repaired_not_lost(tmp_path):
    p = tmp_path / "events.jsonl"
    _write(p, _line(0) + _line(1).rstrip("\n"))
    log = EventLog(str(p))
    assert [e["seq"] for e in log.events] == [0, 1]
    log.append("b")
    log.append("c")
    again = EventLog(str(p))
    assert [e["seq"] for e in again.events] == [0, 1, 2, 3]
    assert [json.loads(l)["seq"] for l in p.read_text().splitlines()] == [0, 1, 2, 3]
    assert p.read_text().endswith("\n")


def test_a_torn_final_line_is_dropped_and_appends_continue_with_the_right_seq(tmp_path):
    p = tmp_path / "events.jsonl"
    _write(p, _line(0) + _line(1) + '{"seq": 2, "ty')
    log = EventLog(str(p))
    assert [e["seq"] for e in log.events] == [0, 1]
    assert p.read_text() == _line(0) + _line(1)         # only the torn line went
    assert log.append("b")["seq"] == 2
    assert [e["seq"] for e in EventLog(str(p)).events] == [0, 1, 2]


def test_a_corrupt_middle_line_raises_with_a_backup_and_leaves_the_file_alone(tmp_path):
    import glob

    import pytest

    from pleatwright_app.events import CorruptLog
    p = tmp_path / "events.jsonl"
    text = _line(0) + "{not json}\n" + _line(2) + _line(3)
    _write(p, text)
    with pytest.raises(CorruptLog, match="events.jsonl"):
        EventLog(str(p))
    assert p.read_text() == text
    backups = glob.glob(str(p) + ".corrupt-*")
    assert len(backups) == 1 and open(backups[0]).read() == text
    with pytest.raises(CorruptLog):                      # loading again does not pile up copies
        EventLog(str(p))
    assert len(glob.glob(str(p) + ".corrupt-*")) == 1
