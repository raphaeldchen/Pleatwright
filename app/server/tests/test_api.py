import threading
import time

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from artifact_trees import authored
from pleatwright.__main__ import ConfigError
from pleatwright_app.api import create_app
from test_gated_pipeline import FakeClient

BIRD = authored("bird_1")


def _app(tmp, factory=None):
    return create_app(runs_dir=str(tmp / "runs"), certify_global=False,
                      allowed_hosts=["testserver", "127.0.0.1", "localhost"],
                      client_factory=factory or (lambda model: FakeClient([BIRD, BIRD])))


def _until(ws, pred):
    seen = []
    while True:
        m = ws.receive_json()
        seen.append(m)
        if pred(m):
            return seen


def test_a_whole_run_over_the_websocket_and_replay(offline):
    with TestClient(_app(offline)) as c:
        st = c.get("/status").json()
        assert {k: st[k] for k in ("llm_ok", "llm_error", "busy")} == {"llm_ok": True, "llm_error": None, "busy": None}
        assert st["default_model"] == "haiku"
        assert st["models"] == [{"key": "haiku", "id": "claude-haiku-5-5", "label": "Haiku 5.5"},
                                {"key": "sonnet", "id": "claude-sonnet-5", "label": "Sonnet 5"}]
        rid = c.post("/runs", json={"prompt": "a bird"}).json()["id"]
        with c.websocket_connect(f"/ws/runs/{rid}?after=-1") as ws:
            _until(ws, lambda m: m.get("type") == "awaiting_review")
            ws.send_json({"type": "approve"})
            _until(ws, lambda m: m.get("type") == "awaiting_review" and m.get("stage") == "tree")
            ws.send_json({"type": "message", "text": "make the tail longer"})
            _until(ws, lambda m: m.get("type") == "awaiting_review")
            ws.send_json({"type": "approve"})
            seen = _until(ws, lambda m: m.get("type") == "run_finished")
        assert any(m.get("stage") == "model" and m["type"] == "stage_output" for m in seen)
        # replay from 5 returns exactly the persisted tail
        with c.websocket_connect(f"/ws/runs/{rid}?after=5") as ws:
            first = ws.receive_json()
        assert first["seq"] == 6
        rows = c.get("/runs").json()
        assert rows[0]["id"] == rid and rows[0]["status"] == "done"
        r = c.get(f"/runs/{rid}/files/model.fold")
        assert r.status_code == 200 and r.json()["file_spec"] == 1.1


def test_files_outside_the_run_are_404(offline):
    with TestClient(_app(offline)) as c:
        rid = c.post("/runs", json={"prompt": "a bird"}).json()["id"]
        for bad in ("../../etc/passwd", "%2e%2e/%2e%2e/secret", "nope.png", "a%00b"):
            assert c.get(f"/runs/{rid}/files/{bad}").status_code == 404


def test_config_error_shows_in_status_and_refuses_new_runs(offline):
    def factory(model):
        raise ConfigError("provider 'claude' requires an API key; set ANTHROPIC_API_KEY")
    with TestClient(_app(offline, factory)) as c:
        s = c.get("/status").json()
        assert s["llm_ok"] is False and "ANTHROPIC_API_KEY" in s["llm_error"]
        r = c.post("/runs", json={"prompt": "a bird"})
        assert r.status_code == 409 and "authoring is disabled" in r.json()["detail"]


def test_foreign_origins_are_rejected(offline):
    with TestClient(_app(offline)) as c:
        rid = c.post("/runs", json={"prompt": "a bird"}).json()["id"]
        with pytest.raises(WebSocketDisconnect) as e:
            with c.websocket_connect(f"/ws/runs/{rid}", headers={"origin": "https://evil.example"}) as ws:
                ws.receive_json()
        assert e.value.code == 1008
        with c.websocket_connect(f"/ws/runs/{rid}", headers={"origin": "http://localhost:5173"}) as ws:
            assert ws.receive_json()["seq"] == 0


def test_refusals_come_back_as_error_frames_not_events(offline):
    with TestClient(_app(offline)) as c:
        rid = c.post("/runs", json={"prompt": "a bird"}).json()["id"]
        with c.websocket_connect(f"/ws/runs/{rid}") as ws:
            _until(ws, lambda m: m.get("type") == "awaiting_review")
            ws.send_json({"type": "retry"})
            err = _until(ws, lambda m: m.get("type") == "error")[-1]
        assert "nothing to retry" in err["message"]


def test_a_negative_offset_replays_from_the_start_not_the_tail(offline):
    with TestClient(_app(offline)) as c:
        rid = c.post("/runs", json={"prompt": "a bird"}).json()["id"]
        with c.websocket_connect(f"/ws/runs/{rid}?after=-5") as ws:
            assert ws.receive_json()["seq"] == 0
            _until(ws, lambda m: m.get("type") == "awaiting_review")


def test_the_client_is_always_built_on_the_event_loop_thread(offline):
    threads, calls = [], []

    def factory(model):
        threads.append(threading.get_ident())
        calls.append(1)
        if len(calls) == 1:                      # the lifespan's build: no key yet
            raise ConfigError("provider 'claude' requires an API key; set ANTHROPIC_API_KEY")
        return FakeClient([BIRD, BIRD])
    with TestClient(_app(offline, factory)) as c:
        assert c.get("/status").json()["llm_ok"] is True      # the user fixed .env
        assert len(calls) == 2
        assert len(set(threads)) == 1 and threads[0] != threading.get_ident()


def test_malformed_websocket_frames_get_an_error_frame_and_the_socket_lives(offline):
    with TestClient(_app(offline)) as c:
        rid = c.post("/runs", json={"prompt": "a bird"}).json()["id"]
        with c.websocket_connect(f"/ws/runs/{rid}") as ws:
            _until(ws, lambda m: m.get("type") == "awaiting_review")
            ws.send_text("not json")
            assert _until(ws, lambda m: m.get("type") == "error")[-1]["type"] == "error"
            ws.send_bytes(b"\xff\x00")
            assert _until(ws, lambda m: m.get("type") == "error")[-1]["type"] == "error"
            ws.send_json({"type": "retry"})
            err = _until(ws, lambda m: m.get("type") == "error")[-1]
            assert "nothing to retry" in err["message"]


def test_a_foreign_host_header_is_rejected(offline):
    with TestClient(_app(offline)) as c:
        assert c.get("/status").status_code == 200
        assert c.get("/status", headers={"host": "evil.example"}).status_code == 400
        assert c.post("/runs", json={"prompt": "a bird"},
                      headers={"host": "evil.example"}).status_code == 400


def test_the_runs_dir_can_come_from_the_dotenv(offline, tmp_path, monkeypatch):
    import env_config
    where = tmp_path / "from-dotenv"
    monkeypatch.delenv("PLEATWRIGHT_RUNS_DIR", raising=False)
    monkeypatch.setattr(env_config, "load_env",
                        lambda: monkeypatch.setenv("PLEATWRIGHT_RUNS_DIR", str(where)))
    create_app(certify_global=False, client_factory=lambda model: FakeClient([BIRD]))
    assert where.is_dir()


def test_the_recorded_frontend_fixture_matches_what_the_server_emits(offline):
    import json
    import pathlib
    fx = pathlib.Path(__file__).parents[2] / "web" / "src" / "__fixtures__" / "bird_run.events.jsonl"
    want = [(e["type"], e.get("stage")) for e in map(json.loads, fx.read_text().splitlines())]
    with TestClient(_app(offline)) as c:
        rid = c.post("/runs", json={"prompt": "a bird"}).json()["id"]
        with c.websocket_connect(f"/ws/runs/{rid}") as ws:
            _until(ws, lambda m: m.get("type") == "awaiting_review")
            ws.send_json({"type": "approve"})
            _until(ws, lambda m: m.get("type") == "awaiting_review" and m.get("stage") == "tree")
            ws.send_json({"type": "message", "text": "make the tail longer"})
            _until(ws, lambda m: m.get("type") == "awaiting_review")
            ws.send_json({"type": "approve"})
            _until(ws, lambda m: m.get("type") == "run_finished")
        got = [(e["type"], e.get("stage")) for e in c.app.state.manager.store.log(rid).events]
    assert got == want, "re-run app/server/record_fixture.py and commit the fixture"


def test_websocket_origins_are_limited_to_the_configured_ports(offline):
    app = create_app(runs_dir=str(offline / "runs"), certify_global=False,
                     allowed_hosts=["testserver", "127.0.0.1", "localhost"],
                     client_factory=lambda model: FakeClient([BIRD]),
                     allowed_origin_ports={8000, 5173})
    with TestClient(app) as c:
        rid = c.post("/runs", json={"prompt": "a bird"}).json()["id"]
        with pytest.raises(WebSocketDisconnect) as e:
            with c.websocket_connect(f"/ws/runs/{rid}", headers={"origin": "http://localhost:3000"}) as ws:
                ws.receive_json()
        assert e.value.code == 1008
        for ok in ("http://localhost:5173", "http://127.0.0.1:8000"):
            with c.websocket_connect(f"/ws/runs/{rid}", headers={"origin": ok}) as ws:
                assert ws.receive_json()["seq"] == 0


def test_without_configured_ports_any_local_port_is_allowed_but_only_local_hosts(offline):
    with TestClient(_app(offline)) as c:
        rid = c.post("/runs", json={"prompt": "a bird"}).json()["id"]
        with c.websocket_connect(f"/ws/runs/{rid}", headers={"origin": "http://localhost:3000"}) as ws:
            assert ws.receive_json()["seq"] == 0
        with pytest.raises(WebSocketDisconnect):
            with c.websocket_connect(f"/ws/runs/{rid}", headers={"origin": "http://evil.example:5173"}) as ws:
                ws.receive_json()


def test_served_files_are_nosniff_and_svgs_are_sandboxed(offline):
    with TestClient(_app(offline)) as c:
        rid = c.post("/runs", json={"prompt": "a bird"}).json()["id"]
        d = c.app.state.manager.store.dir(rid)
        with open(f"{d}/x.svg", "w") as f:
            f.write('<svg xmlns="http://www.w3.org/2000/svg"><script>1</script></svg>')
        with open(f"{d}/y.json", "w") as f:
            f.write("{}")
        svg, js = c.get(f"/runs/{rid}/files/x.svg"), c.get(f"/runs/{rid}/files/y.json")
        assert svg.status_code == js.status_code == 200
        assert svg.headers["x-content-type-options"] == js.headers["x-content-type-options"] == "nosniff"
        assert svg.headers["content-security-policy"] == "sandbox"
        assert "content-security-policy" not in js.headers


def test_a_run_and_a_revision_can_choose_their_model(offline):
    asked = []

    def factory(model):
        asked.append(model)
        return FakeClient([BIRD])
    with TestClient(_app(offline, factory)) as c:
        assert c.post("/runs", json={"prompt": "a bird", "model": "nope"}).status_code == 409
        rid = c.post("/runs", json={"prompt": "a bird", "model": "sonnet"}).json()["id"]
        with c.websocket_connect(f"/ws/runs/{rid}?after=-1") as ws:
            _until(ws, lambda m: m.get("type") == "awaiting_review")
            ws.send_json({"type": "approve", "model": "sonnet"})
            _until(ws, lambda m: m.get("type") == "awaiting_review" and m.get("stage") == "tree")
            ws.send_json({"type": "message", "text": "longer tail", "model": "haiku"})
            seen = _until(ws, lambda m: m.get("type") == "awaiting_review")
    assert [m["summary"]["model"] for m in seen if m.get("type") == "stage_output"] == ["haiku"]
    assert asked == ["claude-haiku-5-5", "claude-sonnet-5"]    # haiku built at startup, sonnet on demand


def test_delete_a_run(offline):
    with TestClient(_app(offline)) as c:
        rid = c.post("/runs", json={"prompt": "a bird"}).json()["id"]
        log = c.app.state.manager.store.log(rid)
        for _ in range(600):                            # let the mesh draw land: deleting
            if log.last and log.last["type"] == "awaiting_review":   # under its writes races
                break
            time.sleep(0.05)
        c.app.state.manager.busy = lambda: rid          # the run is active: refused
        r = c.delete(f"/runs/{rid}")
        assert r.status_code == 409 and "cancel it first" in r.json()["detail"]
        c.app.state.manager.busy = lambda: None
        assert c.delete(f"/runs/{rid}").status_code == 204
        assert c.get("/runs").json() == []
        assert c.delete(f"/runs/{rid}").status_code == 404
        assert c.delete("/runs/%2e%2e").status_code == 404


def test_the_layout_card_is_answered_with_a_choice(offline):
    dolphin = authored("dolphin_0")                 # the 10% rule asks: grids 50 and 32
    app = _app(offline, lambda model: FakeClient([dolphin, {"explanation": "e"}]))
    with TestClient(app) as c:
        rid = c.post("/runs", json={"prompt": "a dolphin"}).json()["id"]
        with c.websocket_connect(f"/ws/runs/{rid}") as ws:
            _until(ws, lambda m: m.get("type") == "awaiting_review")
            ws.send_json({"type": "approve"})
            _until(ws, lambda m: m.get("type") == "awaiting_review" and m.get("stage") == "tree")
            ws.send_json({"type": "approve"})
            card = _until(ws, lambda m: m.get("type") == "awaiting_review")[-1]
            assert card["stage"] == "packing" and card["explanation"] == "e"
            ws.send_json({"type": "approve", "choice": ["smaller"]})   # not a string: no choice
            assert _until(ws, lambda m: m.get("type") == "error")[-1]["message"] == \
                "choose the smaller or the symmetric layout"
            ws.send_json({"type": "approve", "choice": "smaller"})
            fin = _until(ws, lambda m: m.get("type") == "run_finished")[-1]
        assert fin["grid"] == 32
