"""Tools, offline: fake mesh provider, fake VLM client returning artifact tree bird_1."""
import asyncio
import json
import os

import pytest

from artifact_trees import authored
from pleatwright_app import tools as T
from pleatwright_app.events import EventLog
from test_gated_pipeline import FakeClient

BIRD = authored("bird_1")


def _ctx(tmp_path, client=None):
    loop = asyncio.get_running_loop()
    d = tmp_path / "run"
    d.mkdir(exist_ok=True)
    return T.Ctx(str(d), EventLog(str(d / "events.jsonl")), client, loop)


def _types(ctx):
    return [(e["type"], e.get("stage")) for e in ctx.log.events]


def test_make_mesh_reports_a_skipped_image_then_the_mesh(offline):
    async def main():
        ctx = _ctx(offline)
        path = await T.make_mesh(ctx, "a bird")
        return ctx, path
    ctx, path = asyncio.run(main())
    assert os.path.isfile(path) and path == os.path.join(ctx.work, "mesh.glb")
    assert _types(ctx) == [("stage_started", "image"), ("stage_output", "image"),
                           ("stage_started", "mesh"), ("stage_output", "mesh")]
    img, mesh = ctx.log.events[1], ctx.log.events[3]
    assert img["files"] == [] and img["summary"]["skipped"] is True
    assert mesh["files"] == ["author/mesh.glb"] and mesh["summary"]["provider"] == "fake"


def test_a_mesh_failure_is_logged_with_a_retry(offline, monkeypatch):
    import mesh_acquire

    def boom(*a, **k):
        raise RuntimeError("Space is down")
    monkeypatch.setattr(mesh_acquire, "acquire_mesh", boom)

    async def main():
        ctx = _ctx(offline)
        with pytest.raises(T.ToolFailed):
            await T.make_mesh(ctx, "a bird")
        return ctx
    last = asyncio.run(main()).log.last
    assert last["type"] == "stage_failed" and last["stage"] == "image"
    assert last["retry"] == "make_mesh" and "Space is down" in last["error"]


def test_author_then_revise_then_approve(offline):
    client = FakeClient([BIRD, BIRD])

    async def main():
        ctx = _ctx(offline, client)
        await T.make_mesh(ctx, "a bird")
        await T.author_tree(ctx)
        await T.revise_tree(ctx, "make the tail longer")
        path = await T.approve_tree(ctx, "a bird")
        return ctx, path
    ctx, path = asyncio.run(main())
    ev = ctx.log.events
    rounds = [e for e in ev if e["type"] == "stage_output" and e["stage"] == "tree"]
    assert [r["round"] for r in rounds] == [0, 1, 1]
    assert rounds[0]["summary"] == {"flaps": len(BIRD["leaves"]), "pairs": len(BIRD["pairs"]),
                                    "model": "sonnet"}
    assert rounds[0]["files"][0] == "author/tree_round0.png"
    assert rounds[-1]["summary"] == {"approved": True}
    assert [e["can_approve"] for e in ev if e["type"] == "awaiting_review"] == [True, True]
    assert json.load(open(path))["nodes"] == BIRD["nodes"]
    assert T.load_state(ctx.run_dir)["status"] == "approved"


def test_a_failed_round_cannot_be_approved_and_says_why(offline):
    client = FakeClient([None])                       # truncated authoring turn

    async def main():
        ctx = _ctx(offline, client)
        await T.make_mesh(ctx, "a bird")
        await T.author_tree(ctx)
        return ctx
    ctx = asyncio.run(main())
    assert ctx.log.events[-2]["type"] == "assistant_message"
    assert ctx.log.last == {**ctx.log.last, "type": "awaiting_review", "can_approve": False}


def test_review_again_re_presents_the_saved_round_without_calling_the_vlm(offline):
    client = FakeClient([BIRD])

    async def main():
        ctx = _ctx(offline, client)
        await T.make_mesh(ctx, "a bird")
        await T.author_tree(ctx)
        await T.review_again(ctx)
        return ctx
    ctx = asyncio.run(main())
    assert len(client.calls) == 1
    assert [e["type"] for e in ctx.log.events[-3:]] == ["stage_output", "assistant_message",
                                                        "awaiting_review"]


def test_retry_for(tmp_path):
    d = str(tmp_path)
    assert T.retry_for("image", d) == T.retry_for("mesh", d) == "make_mesh"
    assert T.retry_for("tree", d) == "author_tree"
    os.makedirs(tmp_path / "author")
    (tmp_path / "author" / "state.json").write_text("{}")
    assert T.retry_for("tree", d) == "review"
    (tmp_path / "author" / "state.json").write_text('{"status": "approved"}')
    assert T.retry_for("tree", d) == "approve_tree"
    for s in ("packing", "solve", "shape", "model"):
        assert T.retry_for(s, d) == "fold"


def test_stage_from_disk(tmp_path):
    d = str(tmp_path)
    assert T.stage_from_disk(d) == "image"
    os.makedirs(tmp_path / "author")
    (tmp_path / "author" / "mesh.glb").write_text("")
    assert T.stage_from_disk(d) == "tree"
    (tmp_path / "author" / "state.json").write_text("{}")
    assert T.stage_from_disk(d) == "tree"
    (tmp_path / "tree.json").write_text("{}")
    assert T.stage_from_disk(d) == "packing"


def test_approve_tree_resumes_an_already_approved_state(offline):
    client = FakeClient([BIRD])

    async def main():
        ctx = _ctx(offline, client)
        await T.make_mesh(ctx, "a bird")
        await T.author_tree(ctx)
        await T.approve_tree(ctx, "a bird")
        await T.approve_tree(ctx, "a bird")           # state is approved: must not raise
        return ctx
    ctx = asyncio.run(main())
    assert os.path.exists(os.path.join(ctx.run_dir, "tree.json"))
    assert ctx.log.last["type"] == "stage_output" and ctx.log.last["summary"] == {"approved": True}


@pytest.mark.parametrize("layout,retry", [("smaller", "layout"), ("symmetric", "layout"),
                                          ("auto", "fold")])
def test_a_failed_fold_of_a_chosen_layout_retries_back_to_the_card(tmp_path, layout, retry):
    """spec §5.2a: a failed fold of the user's choice returns to the layout card."""
    async def main():
        ctx = _ctx(tmp_path)                          # no tree.json: the fold fails at once
        with pytest.raises(T.ToolFailed):
            await T.fold(ctx, certify_global=False, layout=layout,
                         chosen_by="flag" if layout == "auto" else "user")
        return ctx
    last = asyncio.run(main()).log.last
    assert last["type"] == "stage_failed" and last["retry"] == retry


def test_every_tool_has_a_schema():
    assert set(T.TOOL_SCHEMAS) == {"make_mesh", "author_tree", "revise_tree",
                                   "approve_tree", "fold"}


def test_make_mesh_names_the_image_model(offline, monkeypatch):
    """Spec 2026-10-19 §7: the image stage says what drew the concept."""
    import shutil

    import mesh_acquire

    def acquire(prompt, *, progress=None, **_):
        d = offline / "draw"
        d.mkdir()
        (d / "concept.jpg").write_bytes(b"\xff\xd8\xff\xe0" + b"j" * 32)
        shutil.copyfile(mesh_acquire.fake_mesh_path("a bird"), d / "mesh.glb")
        progress("image", str(d / "concept.jpg"))
        progress("mesh", str(d / "mesh.glb"))
        return str(d / "mesh.glb")
    monkeypatch.setattr(mesh_acquire, "acquire_mesh", acquire)
    monkeypatch.setattr(mesh_acquire, "image_model_label", lambda name=None, key_dir=None: "m-1")

    async def main():
        ctx = _ctx(offline)
        await T.make_mesh(ctx, "a bird")
        return ctx
    img = asyncio.run(main()).log.events[1]
    assert img["files"] == ["author/concept.jpg"]
    assert img["summary"] == {"provider": "fake", "image_model": "m-1"}


def test_present_layout_explains_once_per_packing(tmp_path):
    """The explanation is cached in layout/card.json: a re-present (reload, retry,
    re-pack to the same layouts) shows the same text without a second VLM call."""
    import shutil
    from artifact_trees import path as artifact_path
    from pleatwright import pipeline as PL
    client = FakeClient([{"explanation": "first"}, {"explanation": "second"}])
    summary = PL.pack_options("dolphin_0").summary()

    async def main():
        ctx = _ctx(tmp_path, client)
        shutil.copyfile(artifact_path("dolphin_0"), os.path.join(ctx.run_dir, "tree.json"))
        await T.present_layout(ctx, summary)
        await T.present_layout(ctx, summary, note="again")
        assert len(client.calls) == 1 and ctx.log.last["explanation"] == "first"
        assert ctx.log.last["note"] == "again"
        await T.present_layout(ctx, dict(summary, gain=2.0))   # a different packing
        return ctx
    ctx = asyncio.run(main())
    assert len(client.calls) == 2 and ctx.log.last["explanation"] == "second"


def test_present_layout_without_a_client_uses_the_template(tmp_path):
    import shutil
    import layout_explain
    from artifact_trees import path as artifact_path
    from pleatwright import pipeline as PL
    summary = PL.pack_options("dolphin_0").summary()

    async def main():
        ctx = _ctx(tmp_path)
        shutil.copyfile(artifact_path("dolphin_0"), os.path.join(ctx.run_dir, "tree.json"))
        await T.present_layout(ctx, summary)
        return ctx
    ctx = asyncio.run(main())
    pairs = [list(p) for p in json.load(open(artifact_path("dolphin_0")))["pairs"]]
    assert ctx.log.last["explanation"] == layout_explain.template_explanation(
        summary, "dolphin", pairs)
