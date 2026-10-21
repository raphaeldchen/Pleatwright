import asyncio
import json
import os
import shutil

import pytest

import mesh_acquire
from artifact_trees import authored
from pleatwright.__main__ import ConfigError
import pleatwright_app.tools as T
from pleatwright_app.guided import Manager, Refused, phase
from pleatwright_app.runs import RunStore
from test_gated_pipeline import FakeClient

BIRD = authored("bird_1")


class LoopRecordingClient(FakeClient):
    """Records the event loop of every VLM call (the #198 one-loop lesson)."""
    def __init__(self, payloads):
        super().__init__(payloads)
        self.loops = []

    async def run_turn(self, system, messages, tools):
        self.loops.append(id(asyncio.get_running_loop()))
        return await super().run_turn(system, messages, tools)


async def _until_packing(log, timeout=60):
    async def poll():
        while not any(e["type"] == "stage_started" and e["stage"] == "packing"
                      for e in log.events):
            await asyncio.sleep(0.05)
    await asyncio.wait_for(poll(), timeout)


def test_a_whole_guided_run(offline):
    client = LoopRecordingClient([BIRD, BIRD])

    async def main():
        m = Manager(RunStore(str(offline / "runs")), lambda model: client, certify_global=False)
        rid = await m.create("a bird")
        await approve_first_mesh(m, rid)
        log = m.store.log(rid)
        assert phase(log) == {"phase": "review", "stage": "tree", "can_approve": True}
        await m.message(rid, "make the tail longer")
        await m.wait_idle()
        await m.approve(rid)
        await m.wait_idle()
        return m, rid
    m, rid = asyncio.run(main())
    log = m.store.log(rid)
    assert log.last["type"] == "run_finished"
    assert [e["text"] for e in log.events if e["type"] == "user_message"] == \
        ["a bird", "Approve", "make the tail longer", "Approve"]   # mesh, then tree
    assert len(client.calls) == 2 and len(set(client.loops)) == 1


def test_config_error_refuses_before_any_run_or_mesh(offline):
    def factory(model):
        raise ConfigError("provider 'claude' requires an API key; set ANTHROPIC_API_KEY")

    async def main():
        m = Manager(RunStore(str(offline / "runs")), factory)
        with pytest.raises(Refused, match="API key"):
            await m.create("a bird")
        return m
    m = asyncio.run(main())
    assert m.store.list() == []
    assert not os.path.exists(offline / "meshes")


def test_one_active_run_at_a_time(offline):
    async def main():
        m = Manager(RunStore(str(offline / "runs")), lambda model: FakeClient([BIRD, BIRD]))
        await m.create("a bird")
        with pytest.raises(Refused, match="already running"):
            await m.create("a crab")
        await m.wait_idle()
    asyncio.run(main())


def test_messages_outside_review_are_refused(offline):
    async def main():
        m = Manager(RunStore(str(offline / "runs")), lambda model: FakeClient([None]))
        rid = await m.create("a bird")
        await approve_first_mesh(m, rid)             # the tree round failed: nothing to approve
        with pytest.raises(Refused, match="nothing to approve"):
            await m.approve(rid)
    asyncio.run(main())


def test_cancel_during_the_fold_logs_cancelled_with_retry(offline):
    async def main():
        m = Manager(RunStore(str(offline / "runs")), lambda model: FakeClient([BIRD]))
        rid = await m.create("a bird")
        await approve_first_mesh(m, rid)
        await m.approve(rid)
        log = m.store.log(rid)
        await _until_packing(log)
        await m.cancel(rid)
        await m.wait_idle()
        return log
    last = asyncio.run(main()).last
    assert last["type"] == "stage_failed" and last["reason"] == "cancelled"
    assert last["retry"] == "fold"


def test_retry_runs_the_failed_stage_again(offline):
    async def main():
        m = Manager(RunStore(str(offline / "runs")), lambda model: FakeClient([BIRD]),
                    certify_global=False)
        rid = await m.create("a bird")
        await approve_first_mesh(m, rid)
        await m.approve(rid)
        log = m.store.log(rid)
        await _until_packing(log)
        await m.cancel(rid)
        await m.wait_idle()
        await m.retry(rid)
        await m.wait_idle()
        return log
    assert asyncio.run(main()).last["type"] == "run_finished"


def test_recover_marks_interrupted_runs_and_keeps_paused_reviews(offline):
    store = RunStore(str(offline / "runs"))
    a = store.create("a bird")
    store.log(a).append("stage_started", stage="mesh")
    b = store.create("a crab")
    store.log(b).append("awaiting_review", round=0, can_approve=True)
    Manager(store, lambda model: None).recover()
    la, lb = store.log(a).last, store.log(b).last
    assert la["type"] == "stage_failed" and la["reason"] == "interrupted"
    assert la["stage"] == "mesh" and la["retry"] == "make_mesh"
    assert lb["type"] == "awaiting_review"


def test_a_failure_while_approving_is_blamed_on_the_tree_and_retries_without_the_vlm(
        offline, monkeypatch):
    client = FakeClient([BIRD])
    real = T.tree_file
    calls = []

    def flaky(state, prompt):
        calls.append(1)
        if len(calls) == 1:
            raise OSError("disk full")
        return real(state, prompt)
    monkeypatch.setattr(T, "tree_file", flaky)

    async def main():
        m = Manager(RunStore(str(offline / "runs")), lambda model: client, certify_global=False)
        rid = await m.create("a bird")
        await approve_first_mesh(m, rid)
        await m.approve(rid)
        await m.wait_idle()
        failed = dict(m.store.log(rid).last)
        n = len(client.calls)
        await m.retry(rid)
        await m.wait_idle()
        return m, rid, failed, n
    m, rid, failed, n = asyncio.run(main())
    assert failed["type"] == "stage_failed" and failed["stage"] == "tree"
    assert failed["retry"] == "approve_tree"
    assert m.store.log(rid).last["type"] == "run_finished"
    assert len(client.calls) == n


def test_authoring_actions_are_refused_without_an_llm_and_log_nothing(offline):
    def factory(model):
        raise ConfigError("provider 'claude' requires an API key; set ANTHROPIC_API_KEY")

    async def main():
        store = RunStore(str(offline / "runs"))
        first = Manager(store, lambda model: FakeClient([BIRD]))
        rid = await first.create("a bird")
        await approve_first_mesh(first, rid)         # paused at the tree review
        bad = store.create("a crab")
        store.log(bad).append("stage_failed", stage="mesh", error="x", reason="error",
                              retry="make_mesh")
        m = Manager(store, factory)                  # a restart with no key
        before = (list(store.log(rid).events), list(store.log(bad).events))
        with pytest.raises(Refused, match="authoring is disabled"):
            await m.message(rid, "longer tail")
        with pytest.raises(Refused, match="authoring is disabled"):
            await m.retry(bad)
        assert (list(store.log(rid).events), list(store.log(bad).events)) == before
        assert m.busy() is None
    asyncio.run(main())


def test_recover_blames_an_interrupted_approval_on_the_tree(offline):
    store = RunStore(str(offline / "runs"))
    rid = store.create("a bird")
    store.log(rid).append("awaiting_review", round=0, can_approve=True)
    store.log(rid).append("user_message", text="Approve")
    author = store.dir(rid) + "/author"
    os.makedirs(author)
    open(author + "/mesh.glb", "wb").close()
    with open(author + "/state.json", "w") as f:
        f.write('{"status": "approved"}')
    Manager(store, lambda model: None).recover()
    last = store.log(rid).last
    assert last["type"] == "stage_failed" and last["reason"] == "interrupted"
    assert last["stage"] == "tree" and last["retry"] == "approve_tree"


def _stage_tree_run(store, prompt="a bird"):
    """A run whose last event is `stage_started tree`, with a TORN author/state.json."""
    rid = store.create(prompt)
    store.log(rid).append("stage_started", stage="tree")
    author = store.dir(rid) + "/author"
    os.makedirs(author)
    open(author + "/mesh.glb", "wb").close()
    with open(author + "/state.json", "w") as f:
        f.write('{"status": "awaiting_rev')           # the server died mid-write
    return rid


def test_recover_survives_a_torn_state_json(offline):
    store = RunStore(str(offline / "runs"))
    rid = _stage_tree_run(store)
    Manager(store, lambda model: None).recover()
    last = store.log(rid).last
    assert last["type"] == "stage_failed" and last["reason"] == "interrupted"
    assert last["stage"] == "tree" and last["retry"] == "author_tree"


def test_one_bad_run_does_not_stop_recovery_of_the_next(offline, monkeypatch, caplog):
    store = RunStore(str(offline / "runs"))
    a = store.create("a bird")
    store.log(a).append("stage_started", stage="mesh")
    b = store.create("a crab")
    store.log(b).append("stage_started", stage="mesh")
    real = T.retry_for

    def flaky(stage, run_dir):
        if os.path.basename(run_dir) == a:
            raise RuntimeError("boom")
        return real(stage, run_dir)
    monkeypatch.setattr(T, "retry_for", flaky)
    Manager(store, lambda model: None).recover()          # must not raise
    assert store.log(a).last["type"] == "stage_started"
    assert store.log(b).last["type"] == "stage_failed" and store.log(b).last["retry"] == "make_mesh"
    assert any("boom" in (r.exc_text or "") for r in caplog.records)


def test_save_is_atomic_and_leaves_no_tmp(offline, monkeypatch):
    replaced = []
    real_replace = os.replace
    monkeypatch.setattr(T.os, "replace", lambda a, b: (replaced.append((a, b)), real_replace(a, b)))
    store = RunStore(str(offline / "runs"))
    rid = store.create("a bird")
    ctx = T.Ctx(store.dir(rid), store.log(rid), None, None)
    os.makedirs(ctx.work)
    T._save(ctx, {"status": "awaiting_review", "round": 0})
    assert [os.path.basename(a) for a, _ in replaced] == ["state.json.tmp"]
    assert sorted(os.listdir(ctx.work)) == ["state.json"]
    import json
    assert json.load(open(ctx.work + "/state.json")) == {"status": "awaiting_review", "round": 0}
    assert T.load_state(store.dir(rid))["round"] == 0


def test_load_state_returns_none_for_a_torn_file(offline):
    store = RunStore(str(offline / "runs"))
    rid = _stage_tree_run(store)
    assert T.load_state(store.dir(rid)) is None


def test_the_runner_still_logs_a_terminal_event_when_its_bookkeeping_raises(offline, monkeypatch):
    async def boom(ctx, prompt):
        raise RuntimeError("mesh exploded")

    def bad_retry(stage, run_dir):
        raise ValueError("state unreadable")
    monkeypatch.setattr(T, "first_mesh", boom)
    monkeypatch.setattr(T, "retry_for", bad_retry)

    async def main():
        m = Manager(RunStore(str(offline / "runs")), lambda model: FakeClient([BIRD]))
        rid = await m.create("a bird")
        await m.wait_idle()
        return m.store.log(rid).last
    last = asyncio.run(main())
    assert last["type"] == "stage_failed" and last["retry"] is None
    assert "mesh exploded" in last["error"] and last["stage"] == "image"


def test_sonnet_is_the_default_and_each_authoring_action_can_pick_haiku(offline):
    asked = []

    def factory(model):
        asked.append(model)
        return FakeClient([BIRD])

    async def main():
        m = Manager(RunStore(str(offline / "runs")), factory, certify_global=False)
        rid = await m.create("a bird")                         # no model: the default
        await approve_first_mesh(m, rid)
        await m.message(rid, "make the tail longer", model="haiku")
        await m.wait_idle()
        return m, rid
    m, rid = asyncio.run(main())
    assert asked == ["claude-sonnet-5", "claude-haiku-5-5"]    # one client per model, built once
    log = m.store.log(rid)
    trees = [e for e in log.events if e["type"] == "stage_output" and e["stage"] == "tree"]
    assert [t["summary"]["model"] for t in trees] == ["sonnet", "haiku"]
    assert [e.get("model") for e in log.events if e["type"] == "user_message" and e["text"] != "Approve"] == ["sonnet", "haiku"]


def test_an_unknown_model_is_refused_before_a_run_exists(offline):
    async def main():
        m = Manager(RunStore(str(offline / "runs")), lambda model: FakeClient([BIRD]))
        with pytest.raises(Refused, match="unknown model"):
            await m.create("a bird", model="gpt-9")
        return m
    m = asyncio.run(main())
    assert m.store.list() == []


def test_an_antlered_tree_goes_straight_to_packing(offline):
    """A tree whose branch points branch (forked antlers on the head) is no
    longer flagged or refused: approving it folds it (spec 2026-10-10 §3)."""
    from test_pack_chain import antlered
    t = antlered()
    payload = {k: t[k] for k in ("subject_guess", "nodes", "pairs", "readings", "leaves")}

    async def main():
        m = Manager(RunStore(str(offline / "runs")), lambda model: FakeClient([payload]),
                    certify_global=False)
        rid = await m.create("a dog with antlers")
        await approve_first_mesh(m, rid)
        await m.approve(rid)
        await m.wait_idle()
        return m, rid
    m, rid = asyncio.run(main())
    log = m.store.log(rid)
    tree_out = next(e for e in log.events if e["type"] == "stage_output" and e["stage"] == "tree")
    assert "packable" not in tree_out["summary"]
    assert any(e["type"] == "stage_output" and e["stage"] == "packing" for e in log.events)
    assert log.last["type"] == "run_finished"


def test_a_run_can_be_deleted_but_not_while_it_is_running(offline):
    async def main():
        m = Manager(RunStore(str(offline / "runs")), lambda model: FakeClient([BIRD, BIRD]),
                    certify_global=False)
        old = await m.create("a bird")
        await m.wait_idle()                       # waiting for review: idle, deletable
        await m.delete(old)
        assert m.store.list() == []
        rid = await m.create("a crab")            # its flow is still running
        with pytest.raises(Refused, match="cancel it first"):
            await m.delete(rid)
        await m.wait_idle()
        return m, rid
    m, rid = asyncio.run(main())
    assert [r["id"] for r in m.store.list()] == [rid]


def test_a_run_stopped_at_the_old_revision_cap_can_be_revised(offline):
    """Before 2026-10-11 a fourth revision ended the run: state `exhausted` and a
    tree `stage_failed` (reason "exhausted", no retry). Such a run is back in
    review: a message revises it."""
    async def main():
        m = Manager(RunStore(str(offline / "runs")), lambda model: FakeClient([BIRD, BIRD]),
                    certify_global=False)
        rid = await m.create("a bird")
        await approve_first_mesh(m, rid)
        p = os.path.join(m.store.dir(rid), "author", "state.json")
        with open(p) as f:
            st = json.load(f)
        st.update(status="exhausted", note="3 revisions were used")
        with open(p, "w") as f:
            json.dump(st, f)
        m.store.log(rid).append("assistant_message", text=st["note"])
        m.store.log(rid).append("stage_failed", stage="tree", error=st["note"],
                                reason="exhausted", retry=None)
        assert phase(m.store.log(rid)) == {"phase": "review", "stage": "tree", "can_approve": True}
        await m.message(rid, "make the tail longer")
        await m.wait_idle()
        return m, rid
    m, rid = asyncio.run(main())
    log = m.store.log(rid)
    assert log.last["type"] == "awaiting_review" and log.last["round"] == 1


# ---- mesh review (spec 2026-10-11) -----------------------------------------------
async def approve_first_mesh(m, rid):
    """Mesh review (2026-10-11): a new run first waits on its mesh. Approving
    round 0 takes it on to the tree, as every run went before."""
    await m.wait_idle()
    await m.approve(rid)
    await m.wait_idle()


def _events(m, rid, type_, **match):
    return [e for e in m.store.log(rid).events
            if e["type"] == type_ and all(e.get(k) == v for k, v in match.items())]


def _ratings(m, rid):
    import mesh_ratings
    ms = json.load(open(os.path.join(m.store.dir(rid), "author", "mesh_state.json")))
    return mesh_ratings.read_ratings(ms["rounds"][-1]["cache_dir"])


def test_a_new_run_waits_on_its_mesh_first(offline):
    async def main():
        m = Manager(RunStore(str(offline / "runs")), lambda model: FakeClient([BIRD]))
        rid = await m.create("a bird")
        await m.wait_idle()
        return m, rid
    m, rid = asyncio.run(main())
    log = m.store.log(rid)
    assert phase(log) == {"phase": "review", "stage": "mesh", "can_approve": True}
    assert _events(m, rid, "stage_output", stage="mesh")[-1]["round"] == 0
    assert not _events(m, rid, "stage_started", stage="tree")


def test_mesh_feedback_records_a_rejection_rewrites_and_draws_round_1(offline):
    async def main():
        m = Manager(RunStore(str(offline / "runs")),
                    lambda model: FakeClient([{"description": "sparrow-sized bird, long tail"}]))
        rid = await m.create("a bird")
        await m.wait_idle()
        await m.message(rid, "the tail is too short")
        await m.wait_idle()
        return m, rid
    m, rid = asyncio.run(main())
    assert phase(m.store.log(rid)) == {"phase": "review", "stage": "mesh", "can_approve": True}
    assert [e["round"] for e in _events(m, rid, "stage_output", stage="mesh")] == [0, 1]
    ms = json.load(open(os.path.join(m.store.dir(rid), "author", "mesh_state.json")))
    assert ms["feedback"] == ["the tail is too short"]
    assert ms["rounds"][1]["description"] == "sparrow-sized bird, long tail"
    assert isinstance(ms["rounds"][1]["seed"], int)
    # the fake provider ignores description/seed: both rounds share one cache folder
    assert [x["feedback"] for x in _ratings(m, rid)["rejections"]] == ["the tail is too short"]


def test_approving_the_mesh_counts_it_and_authors_the_tree(offline):
    async def main():
        m = Manager(RunStore(str(offline / "runs")), lambda model: FakeClient([BIRD]))
        rid = await m.create("a bird")
        await approve_first_mesh(m, rid)
        return m, rid
    m, rid = asyncio.run(main())
    assert phase(m.store.log(rid)) == {"phase": "review", "stage": "tree", "can_approve": True}
    assert _ratings(m, rid)["approvals"] == 1
    assert os.path.isfile(os.path.join(m.store.dir(rid), "author", "mesh.glb"))
    approved = _events(m, rid, "stage_output", stage="mesh")[-1]
    assert approved["summary"]["approved"] is True and approved["round"] == 0


def test_a_second_run_of_the_subject_is_served_the_proven_mesh(offline, monkeypatch):
    async def main():
        m = Manager(RunStore(str(offline / "runs")), lambda model: FakeClient([BIRD, BIRD]))
        first = await m.create("a bird")
        await approve_first_mesh(m, first)
        calls = []
        monkeypatch.setattr(mesh_acquire, "acquire_mesh",
                            lambda *a, **k: calls.append(1) or (_ for _ in ()).throw(AssertionError("drew")))
        second = await m.create("A bird.")              # same subject key
        await m.wait_idle()
        return m, second, calls
    m, rid, calls = asyncio.run(main())
    assert calls == []
    mesh = _events(m, rid, "stage_output", stage="mesh")[-1]
    assert mesh["summary"]["served"] == "best_rated" and mesh["summary"]["approvals"] == 1
    assert "best-rated" in _events(m, rid, "assistant_message")[-1]["text"]


def test_a_rewrite_that_never_validates_goes_back_to_mesh_review(offline):
    """Review focus 2: nothing is recorded and no round is added; the user rephrases."""
    async def main():
        m = Manager(RunStore(str(offline / "runs")),
                    lambda model: FakeClient([{"description": "no"}] * 3))
        rid = await m.create("a bird")
        await m.wait_idle()
        await m.message(rid, "no tail")
        await m.wait_idle()
        failed = m.store.log(rid).last
        await m.retry(rid)
        await m.wait_idle()
        return m, rid, failed
    m, rid, failed = asyncio.run(main())
    assert failed["type"] == "stage_failed" and failed["retry"] == "review_mesh"
    assert phase(m.store.log(rid)) == {"phase": "review", "stage": "mesh", "can_approve": True}
    assert len(_events(m, rid, "stage_output", stage="mesh")) == 1
    assert _ratings(m, rid) is None


def test_a_failed_redraw_retries_the_same_description_and_seed(offline, monkeypatch):
    """Review focus 3: the mesh Space fails; Retry redraws that round unchanged."""
    real = mesh_acquire.acquire_mesh
    seen = []

    def flaky(prompt, **k):
        seen.append((k.get("description"), k.get("seed")))
        if len(seen) == 2:
            raise RuntimeError("mesh stage: Space 'x' looks unreachable or down")
        return real(prompt, **k)

    async def main():
        m = Manager(RunStore(str(offline / "runs")),
                    lambda model: FakeClient([{"description": "bird, long tail"}]))
        monkeypatch.setattr(mesh_acquire, "acquire_mesh", flaky)
        rid = await m.create("a bird")
        await m.wait_idle()
        await m.message(rid, "longer tail")
        await m.wait_idle()
        failed = m.store.log(rid).last
        await m.retry(rid)
        await m.wait_idle()
        return m, rid, failed
    m, rid, failed = asyncio.run(main())
    assert failed["type"] == "stage_failed" and failed["retry"] == "make_mesh"
    assert seen[1] == seen[2] and seen[1][0] == "bird, long tail" and isinstance(seen[1][1], int)
    assert [e["round"] for e in _events(m, rid, "stage_output", stage="mesh")] == [0, 1]
    assert phase(m.store.log(rid))["stage"] == "mesh"


def test_approving_a_mesh_needs_the_llm(offline):
    """Review focus 5: tree authoring follows, so approval is refused without a key."""
    calls = []

    def factory(model):
        calls.append(model)
        if len(calls) > 1:
            raise ConfigError("provider 'claude' requires an API key; set ANTHROPIC_API_KEY")
        return FakeClient([BIRD])

    async def main():
        m = Manager(RunStore(str(offline / "runs")), factory)
        rid = await m.create("a bird")
        await m.wait_idle()
        m.clients.clear()                               # the key went away
        n = len(m.store.log(rid).events)
        with pytest.raises(Refused, match="authoring is disabled"):
            await m.approve(rid)
        return m, rid, n
    m, rid, n = asyncio.run(main())
    assert len(m.store.log(rid).events) == n


def test_an_old_review_without_a_stage_is_a_tree_review():
    class Log:
        last = {"type": "awaiting_review", "round": 2, "can_approve": True}
    assert phase(Log) == {"phase": "review", "stage": "tree", "can_approve": True}


def test_a_rewrite_error_goes_back_to_mesh_review_and_keeps_nothing(offline):
    """Any error in the rewrite step (an API outage, not only a failed validation)
    sends the user back to mesh review with nothing recorded: they resend."""
    class DownClient(FakeClient):
        async def run_turn(self, system, messages, tools):
            raise RuntimeError("API down")

    async def main():
        m = Manager(RunStore(str(offline / "runs")), lambda model: DownClient([]))
        rid = await m.create("a bird")
        await m.wait_idle()
        await m.message(rid, "longer tail")
        await m.wait_idle()
        failed = m.store.log(rid).last
        await m.retry(rid)
        await m.wait_idle()
        return m, rid, failed
    m, rid, failed = asyncio.run(main())
    assert failed["type"] == "stage_failed" and failed["retry"] == "review_mesh"
    assert "API down" in failed["error"]
    assert len(_events(m, rid, "stage_output", stage="mesh")) == 1
    assert _ratings(m, rid) is None
    assert phase(m.store.log(rid)) == {"phase": "review", "stage": "mesh", "can_approve": True}


# ---- reference mesh library (MESH_LIBRARY_DIR) ------------------------------
def _library(tmp_path, stem="bird"):
    lib = tmp_path / "library"
    (lib / "meshes").mkdir(parents=True)
    (lib / "photos").mkdir()
    (lib / "meshes" / f"{stem}.glb").write_bytes(open(mesh_acquire.fake_mesh_path("a bird"), "rb").read())
    (lib / "photos" / f"{stem}.png").write_bytes(b"\x89PNG\r\n\x1a\n reference photo")
    return lib


def _no_draws(monkeypatch):
    calls = []
    monkeypatch.setattr(mesh_acquire, "acquire_mesh",
                        lambda *a, **k: calls.append(1) or (_ for _ in ()).throw(AssertionError("drew")))
    return calls


def test_a_library_subject_is_served_its_reference_mesh_and_photo(offline, monkeypatch):
    monkeypatch.setenv("MESH_LIBRARY_DIR", str(_library(offline)))
    calls = _no_draws(monkeypatch)

    async def main():
        m = Manager(RunStore(str(offline / "runs")), lambda model: FakeClient([BIRD]))
        rid = await m.create("A bird")
        await m.wait_idle()
        return m, rid
    m, rid = asyncio.run(main())
    assert calls == []
    image = _events(m, rid, "stage_output", stage="image")[-1]
    assert image["files"] == ["author/concept_r0.png"]
    assert open(os.path.join(m.store.dir(rid), "author", "concept_r0.png"), "rb").read() == b"\x89PNG\r\n\x1a\n reference photo"
    mesh = _events(m, rid, "stage_output", stage="mesh")[-1]
    assert mesh["summary"]["served"] == "library"
    assert "reference" in _events(m, rid, "assistant_message")[-1]["text"]
    assert phase(m.store.log(rid)) == {"phase": "review", "stage": "mesh", "can_approve": True}


def test_the_library_mesh_outranks_a_proven_one_and_collects_its_own_ratings(offline, monkeypatch):
    async def main():
        m = Manager(RunStore(str(offline / "runs")), lambda model: FakeClient([BIRD, BIRD]))
        first = await m.create("a bird")              # drawn, then proven by approval
        await approve_first_mesh(m, first)
        monkeypatch.setenv("MESH_LIBRARY_DIR", str(_library(offline)))
        _no_draws(monkeypatch)
        second = await m.create("a bird")
        await approve_first_mesh(m, second)
        return m, first, second
    m, first, second = asyncio.run(main())
    assert _events(m, second, "stage_output", stage="mesh")[0]["summary"]["served"] == "library"
    lib_ratings = _ratings(m, second)
    assert lib_ratings["approvals"] == 1 and lib_ratings["provider"] == "library"
    assert _ratings(m, first)["approvals"] == 1          # the drawn mesh's count is untouched


def test_feedback_on_the_library_mesh_draws_from_the_provider(offline, monkeypatch):
    monkeypatch.setenv("MESH_LIBRARY_DIR", str(_library(offline)))

    async def main():
        m = Manager(RunStore(str(offline / "runs")),
                    lambda model: FakeClient([{"description": "sparrow-sized bird, long tail"}]))
        rid = await m.create("a bird")
        await m.wait_idle()
        await m.message(rid, "the tail is too short")
        await m.wait_idle()
        return m, rid
    m, rid = asyncio.run(main())
    ms = json.load(open(os.path.join(m.store.dir(rid), "author", "mesh_state.json")))
    assert [r["provenance"] for r in ms["rounds"]] == ["library", "drawn"]
    import mesh_ratings
    lib = mesh_ratings.read_ratings(ms["rounds"][0]["cache_dir"])
    assert [x["feedback"] for x in lib["rejections"]] == ["the tail is too short"]


def test_a_failed_library_serve_retries_from_the_library(offline, monkeypatch):
    monkeypatch.setenv("MESH_LIBRARY_DIR", str(_library(offline)))
    real = mesh_acquire.cached_files
    fail = [True]

    def flaky(d):
        if fail.pop() if fail else False:
            raise OSError("disk hiccup")
        return real(d)
    monkeypatch.setattr(mesh_acquire, "cached_files", flaky)
    _no_draws(monkeypatch)

    async def main():
        m = Manager(RunStore(str(offline / "runs")), lambda model: FakeClient([BIRD]))
        rid = await m.create("a bird")
        await m.wait_idle()
        failed = m.store.log(rid).last
        await m.retry(rid)
        await m.wait_idle()
        return m, rid, failed
    m, rid, failed = asyncio.run(main())
    assert failed["type"] == "stage_failed" and failed["retry"] == "make_mesh"
    assert _events(m, rid, "stage_output", stage="mesh")[-1]["summary"]["served"] == "library"


# ---- Nano Banana image stage (spec 2026-10-19) -------------------------------------
def _drawing_acquire(tmp_path, calls):
    """Stands in for acquire_mesh on a Gemini-like provider: a JPEG concept, then
    the fake bird mesh, from a cache folder of its own per call."""
    def acquire(prompt, *, progress=None, description=None, seed=None, **_):
        calls.append({"description": description, "seed": seed})
        d = tmp_path / f"draw{len(calls)}"
        d.mkdir()
        concept = d / "concept.jpg"
        concept.write_bytes(b"\xff\xd8\xff\xe0" + b"j" * 32)
        glb = d / "mesh.glb"
        shutil.copyfile(mesh_acquire.fake_mesh_path("a bird"), glb)
        progress("image", str(concept))
        progress("mesh", str(glb))
        return str(glb)
    return acquire


def _new_run(m, prompt="a bird"):
    async def main():
        rid = await m.create(prompt)
        await m.wait_idle()
        return rid
    return asyncio.run(main())


def test_a_first_draw_gets_a_fresh_label_when_draws_do_not_reproduce(offline, monkeypatch):
    calls = []
    monkeypatch.setattr(mesh_acquire, "draws_reproduce", lambda name=None: False)
    monkeypatch.setattr(mesh_acquire, "acquire_mesh", _drawing_acquire(offline, calls))
    m = Manager(RunStore(str(offline / "runs")), lambda model: FakeClient([BIRD]))
    _new_run(m), _new_run(m)
    seeds = [c["seed"] for c in calls]
    assert len(seeds) == 2 and all(isinstance(s, int) for s in seeds) and seeds[0] != seeds[1]


def test_a_first_draw_has_no_label_when_draws_reproduce(offline):
    m = Manager(RunStore(str(offline / "runs")), lambda model: FakeClient([BIRD]))
    rid = _new_run(m)
    ms = json.load(open(os.path.join(m.store.dir(rid), "author", "mesh_state.json")))
    assert ms["rounds"][0]["seed"] is None


def test_the_image_stage_names_the_model_that_drew_it(offline, monkeypatch):
    seen = []
    monkeypatch.setattr(mesh_acquire, "acquire_mesh", _drawing_acquire(offline, []))
    monkeypatch.setattr(mesh_acquire, "image_model_label",
                        lambda name=None, key_dir=None: seen.append(key_dir) or "m-1")
    m = Manager(RunStore(str(offline / "runs")), lambda model: FakeClient([BIRD]))
    rid = _new_run(m)
    image = _events(m, rid, "stage_output", stage="image")[-1]
    assert image["summary"] == {"provider": "fake", "image_model": "m-1"}
    assert seen == [None]                                  # a draw: the current backend


def test_no_image_model_key_when_the_label_is_unknown(offline, monkeypatch):
    monkeypatch.setattr(mesh_acquire, "acquire_mesh", _drawing_acquire(offline, []))
    m = Manager(RunStore(str(offline / "runs")), lambda model: FakeClient([BIRD]))
    rid = _new_run(m)                                      # fake provider: label None
    assert _events(m, rid, "stage_output", stage="image")[-1]["summary"] == {"provider": "fake"}


def test_a_jpeg_concept_lands_as_concept_r0_jpg(offline, monkeypatch):
    monkeypatch.setattr(mesh_acquire, "acquire_mesh", _drawing_acquire(offline, []))
    m = Manager(RunStore(str(offline / "runs")), lambda model: FakeClient([BIRD]))
    rid = _new_run(m)
    ms = json.load(open(os.path.join(m.store.dir(rid), "author", "mesh_state.json")))
    assert ms["rounds"][0]["concept"].endswith("concept_r0.jpg")
    assert os.path.isfile(os.path.join(m.store.dir(rid), ms["rounds"][0]["concept"]))


def test_a_best_rated_round_is_labelled_from_its_own_folder(offline, monkeypatch):
    seen = []
    m = Manager(RunStore(str(offline / "runs")), lambda model: FakeClient([BIRD, BIRD]))

    async def first():
        rid = await m.create("a bird")
        await approve_first_mesh(m, rid)
    asyncio.run(first())
    monkeypatch.setattr(mesh_acquire, "image_model_label",
                        lambda name=None, key_dir=None: seen.append(key_dir) or "flux/space")
    _new_run(m)
    assert seen and seen[-1] is not None                   # read from the served folder


# ---- the packing layout card (spec 2026-10-16 §7, §8.1) ------------------------
DOLPHIN = authored("dolphin_0")     # symmetric grid 50, unmirrored 32: the rule asks


async def _at_the_card(m, prompt="a dolphin"):
    rid = await m.create(prompt)
    await approve_first_mesh(m, rid)
    await m.approve(rid)                          # the tree: pack both layouts, then ask
    await m.wait_idle()
    return rid


def _dolphin_manager(offline, client):
    return Manager(RunStore(str(offline / "runs")), lambda model: client, certify_global=False)


def test_a_dolphin_run_stops_at_the_layout_card(offline):
    client = LoopRecordingClient([DOLPHIN, DOLPHIN, {"explanation": "e"}])

    async def main():
        m = _dolphin_manager(offline, client)
        rid = await m.create("a dolphin")
        await approve_first_mesh(m, rid)
        await m.message(rid, "longer flippers")
        await m.wait_idle()
        await m.approve(rid)
        await m.wait_idle()
        log = m.store.log(rid)
        assert phase(log) == {"phase": "review", "stage": "packing", "can_approve": True}
        card = log.last
        assert card["card"]["options"][0]["id"] == "smaller" and card["explanation"] == "e"
        assert card["round"] == 0 and card["note"] is None
        out = log.events[-2]
        assert out["type"] == "stage_output" and out["stage"] == "packing"
        assert out["files"] == ["layout/smaller_packing_cp.svg", "layout/symmetric_packing_cp.svg"]
        assert out["summary"]["layout_choice"] == card["card"]
        for f in out["files"]:
            assert os.path.isfile(os.path.join(m.store.dir(rid), f))
        await m.approve(rid, choice="smaller")
        await m.wait_idle()
        return m, rid
    m, rid = asyncio.run(main())
    log = m.store.log(rid)
    assert log.last["type"] == "run_finished" and log.last["grid"] == 32
    assert [e["text"] for e in log.events if e["type"] == "user_message"][-1] == "Smaller grid"
    packing = [e for e in log.events if e["type"] == "stage_output" and e["stage"] == "packing"]
    assert packing[-1]["summary"]["layout"]["reason"] == "user"
    assert len(client.calls) == 3 and len(set(client.loops)) == 1


def test_approve_without_a_choice_is_refused_at_the_card(offline):
    async def main():
        m = _dolphin_manager(offline, FakeClient([DOLPHIN, {"explanation": "e"}]))
        rid = await _at_the_card(m)
        before = list(m.store.log(rid).events)
        for choice in (None, "doubled"):
            with pytest.raises(Refused, match="choose the smaller or the symmetric layout"):
                await m.approve(rid, choice=choice)
        with pytest.raises(Refused):
            await m.message(rid, "make it bigger")
        assert m.store.log(rid).events == before and m.busy() is None
    asyncio.run(main())


def test_symmetric_choice_folds_at_50(offline):
    async def main():
        m = _dolphin_manager(offline, FakeClient([DOLPHIN, {"explanation": "e"}]))
        rid = await _at_the_card(m)
        await m.approve(rid, choice="symmetric")
        await m.wait_idle()
        return m.store.log(rid)
    log = asyncio.run(main())
    assert log.last["type"] == "run_finished" and log.last["grid"] == 50
    assert [e["text"] for e in log.events if e["type"] == "user_message"][-1] == "Mirror-symmetric"


def test_a_failed_smaller_fold_retries_back_to_the_card(offline, monkeypatch):
    client = FakeClient([DOLPHIN, {"explanation": "e"}])

    async def failing_fold(ctx, **kw):
        ctx.emit("stage_failed", stage="solve", reason="error", error="RuntimeError: boom",
                 retry="layout")
        raise T.ToolFailed("RuntimeError: boom")

    async def main():
        m = _dolphin_manager(offline, client)
        rid = await _at_the_card(m)
        n = len(client.calls)
        monkeypatch.setattr(T, "fold", failing_fold)
        await m.approve(rid, choice="smaller")
        await m.wait_idle()
        assert phase(m.store.log(rid)) == {"phase": "failed", "retry": "layout"}
        await m.retry(rid)
        await m.wait_idle()
        return m.store.log(rid), n
    log, n = asyncio.run(main())
    last = log.last
    assert last["type"] == "awaiting_review" and last["stage"] == "packing"
    assert last["note"] == "The smaller layout failed: RuntimeError: boom"
    assert last["explanation"] == "e" and len(client.calls) == n


def test_retry_without_options_json_packs_again_to_a_fresh_card(offline, monkeypatch):
    client = FakeClient([DOLPHIN, {"explanation": "e"}])

    async def failing_fold(ctx, **kw):
        ctx.emit("stage_failed", stage="solve", reason="error", error="RuntimeError: boom",
                 retry="layout")
        raise T.ToolFailed("RuntimeError: boom")

    async def main():
        m = _dolphin_manager(offline, client)
        rid = await _at_the_card(m)
        monkeypatch.setattr(T, "fold", failing_fold)
        await m.approve(rid, choice="smaller")
        await m.wait_idle()
        assert phase(m.store.log(rid)) == {"phase": "failed", "retry": "layout"}
        monkeypatch.undo()
        os.remove(os.path.join(m.store.dir(rid), "layout", "options.json"))
        await m.retry(rid)
        await m.wait_idle()
        return m.store.log(rid)
    log = asyncio.run(main())
    assert log.last["type"] == "awaiting_review" and log.last["stage"] == "packing"
    assert [o["id"] for o in log.last["card"]["options"]] == ["smaller", "symmetric"]


def test_recover_keeps_a_run_paused_at_the_card(offline):
    async def main():
        m = _dolphin_manager(offline, FakeClient([DOLPHIN, {"explanation": "e"}]))
        return m.store, await _at_the_card(m)
    store, rid = asyncio.run(main())
    Manager(store, lambda model: None).recover()
    assert phase(store.log(rid)) == {"phase": "review", "stage": "packing", "can_approve": True}
