"""The Pleatwright CLI, offline: fake mesh provider, fake VLM client, scripted
review answers. The authored tree is an ARTIFACT tree (owner rule: tests use
only the 51 artifact trees)."""
import json
import os

import pytest

import gated_pipeline as GP
from pleatwright import __main__ as CLI
from pleatwright import pipeline as PL
from artifact_trees import authored, path as artifact_path
from test_gated_pipeline import FakeClient, _fake_mesh_views

AUTHORED = authored("bird_1")


@pytest.fixture(autouse=True, scope="module")
def _no_beside():
    """These tests pin the CLI, not packing: the beside searches (river
    routing, tests/test_river_routing.py) are switched off to save their
    seconds on every fold."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(PL, "BESIDE", False)
        yield


@pytest.fixture
def offline(tmp_path, monkeypatch):
    import mesh_acquire
    monkeypatch.setenv("MESH_PROVIDER", "fake")
    monkeypatch.setattr(mesh_acquire, "output_dir", lambda: str(tmp_path / "meshes"))
    monkeypatch.setattr(GP.vlm_render, "render_mesh_views",
                        lambda *a, **k: _fake_mesh_views(tmp_path))
    return tmp_path


def test_tree_file_matches_the_fixture_schema():
    st = {"tree": AUTHORED, "subject_guess": AUTHORED["subject_guess"]}
    t = CLI.tree_file(st, "a bird")
    assert set(t) >= {"roll", "subject", "subject_guess", "nodes", "pairs", "readings", "source"}
    assert t["nodes"] == AUTHORED["nodes"] and t["pairs"] == AUTHORED["pairs"]
    assert t["subject"] == "bird"


def test_author_revises_once_then_approves(offline):
    answers = iter(["make the tail longer", "a"])
    client = FakeClient([AUTHORED, AUTHORED])
    path = CLI.author("a bird", str(offline / "out"), ask=lambda _: next(answers),
                      client=client)
    assert path == str(offline / "out" / "tree.json")
    assert len(client.calls) == 2
    assert "make the tail longer" in json.dumps(client.calls[1]["messages"])
    assert json.load(open(path))["nodes"] == AUTHORED["nodes"]
    assert os.path.exists(offline / "out" / "author" / "state.json")


def test_author_quit_writes_no_tree(offline):
    path = CLI.author("a bird", str(offline / "out"), ask=lambda _: "q",
                      client=FakeClient([AUTHORED]))
    assert path is None
    assert not os.path.exists(offline / "out" / "tree.json")


def test_run_produces_the_four_file_model_folder(offline):
    answers = iter(["a"])
    rc = CLI.main(["run", "a bird", "--out", str(offline / "out")],
                  ask=lambda _: next(answers), client=FakeClient([AUTHORED]))
    assert rc == 0
    folders = [d for d in os.listdir(offline / "out") if d.startswith("Bird_")]
    assert len(folders) == 1
    assert sorted(os.listdir(offline / "out" / folders[0])) == \
        ["overview.png", "packing_cp.svg", "shaping_cp.svg", "solving_cp.svg"]


def test_fold_from_a_tree_file_equals_fold_from_its_roll_name(tmp_path):
    a = PL.run("bird_1", str(tmp_path / "a"), certify_global=False, verbose=False)
    b = PL.run(artifact_path("bird_1"),
               str(tmp_path / "b"), certify_global=False, verbose=False)
    for f in ("packing_cp.svg", "solving_cp.svg", "shaping_cp.svg"):
        assert open(os.path.join(a["folder"], f)).read() == \
            open(os.path.join(b["folder"], f)).read()


def _answers(*a):
    it = iter(a)
    return lambda _: next(it)


def test_a_mesh_provider_failure_exits_2(offline, monkeypatch, capsys):
    import mesh_acquire

    def boom(prompt, **k):
        raise RuntimeError("quota")
    monkeypatch.setattr(mesh_acquire, "acquire_mesh", boom)
    rc = CLI.main(["run", "a bird", "--out", str(offline / "out")],
                  ask=_answers("a"), client=FakeClient([AUTHORED]))
    assert rc == 2
    assert "mesh generation failed: quota" in capsys.readouterr().err


def test_non_mesh_errors_are_not_reported_as_mesh_failures(offline, monkeypatch):
    class Boom(FakeClient):
        async def run_turn(self, *a, **k):
            raise RuntimeError("llm down")
    with pytest.raises(RuntimeError, match="llm down"):
        CLI.main(["author", "a bird", "--out", str(offline / "out")],
                 ask=_answers("a"), client=Boom([]))


def test_author_quit_exits_1(offline):
    rc = CLI.main(["author", "a bird", "--out", str(offline / "out")],
                  ask=_answers("q"), client=FakeClient([AUTHORED]))
    assert rc == 1


def test_eof_on_the_prompt_is_a_quit(offline):
    def eof(_):
        raise EOFError
    assert CLI.author("a bird", str(offline / "out"), ask=eof,
                      client=FakeClient([AUTHORED])) is None


def test_an_empty_answer_reprompts_and_spends_no_revision(offline):
    client = FakeClient([AUTHORED])
    path = CLI.author("a bird", str(offline / "out"), ask=_answers("", "  ", "a"),
                      client=client)
    assert path and len(client.calls) == 1


def test_a_failed_round_cannot_be_approved(offline):
    client = FakeClient([None, AUTHORED])
    path = CLI.author("a bird", str(offline / "out"),
                      ask=_answers("a", "fix it", "a"), client=client)
    assert path == str(offline / "out" / "tree.json")
    assert len(client.calls) == 2
    assert json.load(open(path))["nodes"] == AUTHORED["nodes"]




def test_fold_names_the_stage_that_failed(tmp_path, monkeypatch, capsys):
    from pleatwright import solve as SV

    def boom(*a, **k):
        raise ValueError("no solution")
    monkeypatch.setattr(SV, "solve", boom)
    rc = CLI.main(["fold", artifact_path("bird_1"),
                   "--out", str(tmp_path / "out")])
    assert rc == 1
    err = capsys.readouterr().err
    assert "stage 'solving'" in err and "ValueError: no solution" in err


def test_fold_of_a_missing_tree_file_names_the_typed_path(tmp_path, capsys):
    typed = str(tmp_path / "nope.json")
    rc = CLI.main(["fold", typed, "--out", str(tmp_path / "out")])
    assert rc == 1
    err = capsys.readouterr().err
    assert "stage 'load'" in err and typed in err
    with pytest.raises(FileNotFoundError, match="nope.json"):
        PL._source(typed)


def test_the_concept_image_is_copied_next_to_the_mesh(offline, monkeypatch):
    import mesh_acquire
    prov = offline / "provider"
    prov.mkdir()
    (prov / "mesh.glb").write_bytes(b"glb")
    (prov / "concept.png").write_bytes(b"png")
    monkeypatch.setattr(mesh_acquire, "acquire_mesh", lambda prompt, **k: str(prov / "mesh.glb"))
    CLI.author("a bird", str(offline / "out"), ask=_answers("q"),
               client=FakeClient([AUTHORED]))
    assert (offline / "out" / "author" / "concept.png").read_bytes() == b"png"


def test_the_whole_review_runs_in_one_event_loop(offline, monkeypatch):
    """The LLM client's connection pool binds to the FIRST event loop it is
    used in. Driving start and each resume through separate asyncio.run()
    calls made every later request fail on a closed loop and be silently
    RETRIED by the SDK, so the server saw (and billed) it twice. Every call
    must therefore run in one loop. The loop OBJECTS are kept, not just their
    ids, so a closed loop cannot be freed and its id recycled by the next."""
    import asyncio
    loops = []

    class LoopClient(FakeClient):
        async def run_turn(self, system, messages, tools):
            loops.append(asyncio.get_running_loop())
            return await super().run_turn(system, messages, tools)

    for name in ("start", "resume"):
        real = getattr(GP, name)

        def wrap(real):
            async def entry(*a, **k):
                loops.append(asyncio.get_running_loop())
                return await real(*a, **k)
            return entry
        monkeypatch.setattr(GP, name, wrap(real))

    client = LoopClient([AUTHORED, AUTHORED])
    path = CLI.author("a bird", str(offline / "out"),
                      ask=_answers("make the tail longer", "a"), client=client)
    assert path and len(client.calls) == 2
    assert len(loops) == 5            # start + run_turn, resume + run_turn, approve
    assert len({id(lp) for lp in loops}) == 1


def test_the_prompt_runs_on_a_daemon_thread(offline):
    """A blocked input() on a non-daemon worker (asyncio.to_thread) makes
    Ctrl-C at the review prompt hang until Enter is pressed: the interpreter
    joins the worker on exit. Measured under a pty: to_thread hung > 6 s, a
    daemon thread exited in 0.06 s."""
    import threading
    seen = []

    def ask(_):
        seen.append(threading.current_thread().daemon)
        return "a"
    assert CLI.author("a bird", str(offline / "out"), ask=ask,
                      client=FakeClient([AUTHORED]))
    assert seen == [True]


def test_an_llm_config_error_exits_3_before_any_mesh_call(offline, monkeypatch, capsys):
    """A missing key must surface at once, not as a traceback after a
    multi-minute mesh generation."""
    import env_config
    import mesh_acquire
    monkeypatch.setattr(env_config, "load_env", lambda: False)   # no repo .env
    monkeypatch.setenv("LLM_PROVIDER", "claude")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MAX_TOKENS", raising=False)

    def never(prompt, **k):
        raise AssertionError("the mesh was requested before the LLM client was built")
    monkeypatch.setattr(mesh_acquire, "acquire_mesh", never)
    rc = CLI.main(["run", "a bird", "--out", str(offline / "out")], ask=_answers("a"))
    assert rc == 3
    err = capsys.readouterr().err
    assert "ANTHROPIC_API_KEY" in err and "Traceback" not in err


@pytest.mark.parametrize("prompt,guess,want", [
    ("", "a dog", "dog"),
    ("!!!", "The Origami Crane", "crane"),
    ("", "an", "tree"),
    ("", None, "tree"),
    ("a big dog", "a cat", "big_dog"),
])
def test_subject_filters_stopwords_from_the_guess_too(prompt, guess, want):
    assert CLI._subject(prompt, guess) == want


def test_a_fourth_revision_is_authored_then_approved(offline):
    """No revision cap (2026-10-11): the fourth revision authors a round."""
    client = FakeClient([AUTHORED] * 5)
    path = CLI.author("a bird", str(offline / "out"),
                      ask=_answers("r1", "r2", "r3", "r4", "a"), client=client)
    assert path == str(offline / "out" / "tree.json")
    assert len(client.calls) == 5


DOLPHIN = authored("dolphin_0")


def test_fold_layout_flag(tmp_path):
    rc = CLI.main(["fold", "dolphin_0", "--out", str(tmp_path), "--layout", "symmetric"])
    assert rc == 0
    assert "Dolphin roll 0_50" in os.listdir(tmp_path)


def test_choose_layout_accepts_and_overrides(capsys):
    from pleatwright.pipeline import PackOptions
    from types import SimpleNamespace as NS

    def option(n):
        return NS(layout=NS(N=n))
    opts = PackOptions(sf=None, con=None, sigma=None, symmetric=option(50),
                       smaller=option(32), doubled=None, n_smaller=32,
                       gain=__import__("fractions").Fraction(50, 32), verdict="ask")

    def pick(*answers):
        seen = []
        it = iter(answers)

        def ask(prompt):
            seen.append(prompt)
            r = next(it)
            if isinstance(r, BaseException):
                raise r
            return r
        return CLI.choose_layout(opts, "why", ask=ask), seen

    assert pick("a")[0] == "smaller"
    assert pick("yes")[0] == "smaller"
    assert pick("s")[0] == "symmetric"
    assert pick("x", "m") == ("smaller", [CLI.LAYOUT_PROMPT] * 2)
    assert pick("q")[0] is None
    assert pick(EOFError())[0] is None
    out = capsys.readouterr().out
    assert "50" in out and "32" in out and "1.56" in out and "why" in out


def test_run_asks_for_the_dolphin_layout(offline, monkeypatch):
    clients = iter([FakeClient([DOLPHIN]), FakeClient([{"explanation": "x"}])])
    built = []

    def fresh():
        built.append(next(clients))
        return built[-1]
    monkeypatch.setattr(CLI, "_client", fresh)
    runs = []
    real = PL.run
    monkeypatch.setattr(PL, "run", lambda *a, **k: runs.append(k) or real(*a, **k))
    answers = iter(["a", "m"])          # approve the tree, then take the smaller layout
    rc = CLI.main(["run", "a dolphin", "--out", str(offline / "out")],
                  ask=lambda _: next(answers))
    assert rc == 0
    assert runs[0]["layout"] == "smaller" and runs[0]["chosen_by"] == "user"
    assert runs[0]["options"] is not None
    assert len(built) == 2 and len(built[1].calls) == 1       # a fresh explanation client
    assert [d for d in os.listdir(offline / "out") if d.endswith("_32")] == ["Dolphin_32"]


def test_run_quits_at_the_layout_question(offline, monkeypatch):
    clients = iter([FakeClient([DOLPHIN]), FakeClient([{"explanation": "x"}])])
    monkeypatch.setattr(CLI, "_client", lambda: next(clients))
    answers = iter(["a", "q"])
    rc = CLI.main(["run", "a dolphin", "--out", str(offline / "out")],
                  ask=lambda _: next(answers))
    assert rc == 1
    assert not [d for d in os.listdir(offline / "out") if d.startswith("Dolphin_")]
