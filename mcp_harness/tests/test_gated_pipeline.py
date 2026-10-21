"""The pausable pipeline. Every test runs with a FAKE client, so the whole loop
is exercised with no network, no compile and no human.
"""
from __future__ import annotations

import asyncio
import json
import os

import pytest

import gated_pipeline as GP
import tree_authoring as TA
from artifact_trees import authored, metric
from test_pair_fusion import fuse_pair, prune_to_pair

# Every tree here is an ARTIFACT tree (owner rule, 2026-10-07). A defective
# tree is an artifact tree plus a named edit -- the edits live beside the
# tests that use them (`fuse_pair`, `prune_to_pair`: tests/test_pair_fusion.py).


def _leaves(tree):
    """The flaps the gate lists for `tree` (children-based, as `_build` does)."""
    return TA.leaves_of(TA.to_tuples(tree))


def test_the_summary_leads_with_what_the_human_is_judging():
    t = authored("dog_0")
    s = GP.summarise(t, _leaves(t))
    assert t["subject_guess"] in s
    assert f"{len(_leaves(t))} flaps" in s


def test_the_summary_says_nothing_about_packing():
    t = authored("dog_0")
    s = GP.summarise(t, _leaves(t))
    assert "Packing" not in s and "pack" not in s.lower()


class FakeCall:
    def __init__(self, payload, name="submit_tree"):
        self.id = "call_1"
        self.function = type("F", (), {"name": name,
                                       "arguments": json.dumps(payload)})()


class RawCall:
    """A tool call whose `arguments` string is passed through UNSERIALISED.

    This is the OTHER face of LLM_MAX_TOKENS truncation, and the likelier one:
    an OpenAI-compatible endpoint that hits the completion cap mid-tool-call
    returns `finish_reason: "length"` WITH a partial tool call whose
    `arguments` string is cut off, rather than with no tool call at all.
    `FakeCall` can only produce well-formed JSON, so it cannot model this.
    """

    def __init__(self, raw):
        self.id = "call_1"
        self.function = type("F", (), {"name": "submit_tree",
                                       "arguments": raw})()


class Prose:
    """A turn answered in TEXT with no tool call (finish_reason "stop"): what
    Haiku did to a tree revision on 2026-10-11 while tool_choice was "auto"."""

    def __init__(self, text):
        self.text = text


class FakeResult:
    def __init__(self, payload=None, finish_reason="tool_calls", call_name="submit_tree"):
        self.text = ""
        if payload is None:
            self.tool_calls = []
        elif isinstance(payload, RawCall):
            self.tool_calls = [payload]
        else:
            self.tool_calls = [FakeCall(payload, name=call_name)]
        self.finish_reason = finish_reason
        self.usage = {"total_tokens": 100}


class FakeClient:
    """Records every prompt it is given, so a test can assert what the model saw."""

    def __init__(self, payloads):
        self._payloads = list(payloads)
        self.calls = []

    async def run_turn(self, system, messages, tools):
        self.calls.append({"system": system, "messages": messages})
        p = self._payloads.pop(0)
        if p is None:
            return FakeResult(None, "length")
        if isinstance(p, RawCall):
            return FakeResult(p, "length")
        if isinstance(p, Prose):
            r = FakeResult(None, "stop")
            r.text = p.text
            return r
        return FakeResult(p)


#: A valid authored payload: artifact tree dog_0, exactly as `submit_tree` returns it.
DOG = authored("dog_0")


def _fake_mesh_views(tmp_path):
    """A stand-in for `render_mesh_views` that writes a REAL png.

    `_author` hands the path straight to `llm_client.user_message_with_images`,
    which reads actual bytes off disk (`Path.read_bytes()`) and sniffs the
    magic bytes for a media type -- a path with nothing written to it raises
    `FileNotFoundError` before the fake client is ever reached. Minimal valid
    PNG bytes.
    """
    p = tmp_path / "mesh.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\0" * 64)
    return {"png": str(p)}


def test_start_pauses_at_awaiting_review_with_a_figure(tmp_path, monkeypatch):
    monkeypatch.setattr(GP.vlm_render, "render_mesh_views",
                        lambda *a, **k: _fake_mesh_views(tmp_path))
    c = FakeClient([DOG])
    st = asyncio.run(GP.start("fake.glb", client=c, out_dir=str(tmp_path)))
    assert st["status"] == "awaiting_review"
    assert st["round"] == 0
    assert st["subject_guess"] == DOG["subject_guess"]
    assert os.path.exists(st["sheet_png"])
    assert len(c.calls) == 1


def test_start_reports_a_truncated_turn_as_failed_not_as_a_tree(tmp_path, monkeypatch):
    """LLM_MAX_TOKENS truncation returns finish_reason 'length' and no tool
    call. Measured: at 32000 the bat truncated at exactly the cap. A half-built
    tree presented as real is the worst possible outcome here."""
    monkeypatch.setattr(GP.vlm_render, "render_mesh_views",
                        lambda *a, **k: _fake_mesh_views(tmp_path))
    c = FakeClient([None])
    st = asyncio.run(GP.start("fake.glb", client=c, out_dir=str(tmp_path)))
    assert st["status"] == "failed"
    assert st["tree"] is None
    assert "length" in st["note"]


def test_state_survives_a_json_round_trip(tmp_path, monkeypatch):
    """The pause is a return value precisely so a tool, a CLI or a frontend can
    hold it between turns. A State that will not serialise cannot do that."""
    monkeypatch.setattr(GP.vlm_render, "render_mesh_views",
                        lambda *a, **k: _fake_mesh_views(tmp_path))
    st = asyncio.run(GP.start("fake.glb", client=FakeClient([DOG]),
                              out_dir=str(tmp_path)))
    assert json.loads(json.dumps(st)) == st


def _started(tmp_path, monkeypatch, payloads):
    monkeypatch.setattr(GP.vlm_render, "render_mesh_views",
                        lambda *a, **k: _fake_mesh_views(tmp_path))
    c = FakeClient(payloads)
    st = asyncio.run(GP.start("fake.glb", client=c, out_dir=str(tmp_path)))
    return st, c


def test_approve_returns_the_tree_and_calls_nothing(tmp_path, monkeypatch):
    """Approving is a state change only: no authoring turn, no compile."""
    st, c = _started(tmp_path, monkeypatch, [DOG])
    out = asyncio.run(GP.resume(st, "approve", client=c, out_dir=str(tmp_path)))
    assert out["status"] == "approved"
    assert out["tree"] == st["tree"]
    assert "fold" not in out and "packing" not in out
    assert len(c.calls) == 1


def test_three_revisions_stay_open_and_quote_the_human_verbatim(tmp_path, monkeypatch):
    st, c = _started(tmp_path, monkeypatch, [DOG, DOG, DOG, DOG])
    for i, msg in enumerate(("legs are fused", "tail too short", "head too big")):
        st = asyncio.run(GP.resume(st, "revise", msg, client=c,
                                   out_dir=str(tmp_path)))
        assert st["status"] == "awaiting_review"
        assert st["round"] == i + 1
        sent = json.dumps(c.calls[-1]["messages"])
        assert msg in sent
    assert len(c.calls) == 4          # one draft + three revisions
    assert [h["feedback"] for h in st["history"]] == \
        ["legs are fused", "tail too short", "head too big"]








def test_the_one_image_is_the_MESH_render_and_nothing_else(tmp_path, monkeypatch):
    """Showing the model the tree figure was measured WORSE than no review (MAE
    0.53 with the figure against 0.29 without). This loop must not become the
    loophole -- the ONE image is the mesh ruler, in the first turn.

    ⚠ THIS ASSERTS *WHICH* IMAGE, not how many. The previous version checked
    only `len(images) <= 1`, so swapping `mesh_png` for `sheet_png` in
    `_author` -- the precise regression it is named for -- left it green: one
    image is still one image. The comparison is against the mesh render's own
    bytes, because `user_message_with_images` embeds a base64 data URI rather
    than a path, and the two files differ (the sheet is a real rendered
    figure).
    """
    import llm_client
    mesh = _fake_mesh_views(tmp_path)["png"]
    monkeypatch.setattr(GP.vlm_render, "render_mesh_views",
                        lambda *a, **k: {"png": mesh})
    c = FakeClient([DOG, DOG])
    st = asyncio.run(GP.start("fake.glb", client=c, out_dir=str(tmp_path)))
    assert os.path.exists(st["sheet_png"])
    asyncio.run(GP.resume(st, "revise", "fix the legs", client=c,
                          out_dir=str(tmp_path)))

    want = llm_client.image_data_uri(mesh)
    sheet_uri = llm_client.image_data_uri(st["sheet_png"])
    assert want != sheet_uri, "the fixture cannot tell the two images apart"
    for call in c.calls:
        images = [part for m in call["messages"]
                  if isinstance(m.get("content"), list)
                  for part in m["content"] if part.get("type") == "image_url"]
        assert len(images) == 1, "exactly one image: the mesh ruler"
        assert images[0]["image_url"]["url"] == want, \
            "the model was shown something other than the mesh render"


# --------------------------------------------------------------------------
# C1 -- the fused-limb defect, the one the picture cannot show
# --------------------------------------------------------------------------

#: The quadruped for the fused-limb tests: horse_1, whose front legs are each
#: their own chain withers -> shoulder -> knee -> fetlock -> hoof.
HORSE, FRONT = "horse_1", ("hoof_L", "hoof_R")


def _quadruped(fused: bool) -> dict:
    """horse_1 as authored, or with its FRONT pair FUSED (`fuse_pair`).

    The fused arm is the exact shape prompt rule 6 names as WRONG: one front
    chain that splits at the hoof, so the two hooves share the whole limb down
    to the fetlock instead of branching at the withers. Same six flaps, same
    figure-level anatomy -- only the branch point moves.
    """
    t = authored(HORSE)
    return fuse_pair(t, *FRONT) if fused else t


def _summary_of(tmp_path, monkeypatch, tree):
    monkeypatch.setattr(GP.vlm_render, "render_mesh_views",
                        lambda *a, **k: _fake_mesh_views(tmp_path))
    st = asyncio.run(GP.start("fake.glb", client=FakeClient([tree]),
                              out_dir=str(tmp_path)))
    return st["summary"]


def test_the_summary_RANKS_the_pairs_so_a_fused_limb_is_visible(tmp_path, monkeypatch):
    """S5 exists for two defect classes and only ONE of them is in the picture.

    Measured by the reviewer on the committed `horse` and a fused copy: the
    flap list, the flap count and the figure are
    IDENTICAL, so everything the human saw was identical. `pair_fusion`'s
    validated ranking -- whose own docstring says "The human approval gate
    looks at the worst-ranked pairs" -- moved 0.6364 -> 0.0714 on the
    TreeMaker-era committed horse; on artifact horse_1 it moves 0.5714 ->
    0.0714 (measured 2026-10-07). This asserts the gate now shows it.
    """
    import pair_fusion
    good = _summary_of(tmp_path, monkeypatch, _quadruped(fused=False))
    bad = _summary_of(tmp_path, monkeypatch, _quadruped(fused=True))

    assert "Limb separation" in good and "Limb separation" in bad
    # the pairs are named, not just counted
    fused_name = "/".join(FRONT)
    assert fused_name in bad
    for a, b in authored(HORSE)["pairs"]:
        assert f"{a}/{b}" in good

    def worst(summary):
        line = next(x for x in summary.splitlines() if x.startswith("Limb separation"))
        first = line.split("): ", 1)[1].split(",")[0]
        return float(first.split()[-1])

    assert worst(bad) < 0.20, bad
    assert worst(good) > 0.40, good
    # and the shown value IS pair_fusion's minimum for each tree
    for summary, fused in ((good, False), (bad, True)):
        tn, sp, _ = metric(_quadruped(fused))
        assert worst(summary) == round(
            pair_fusion.score_fusion(tn, sp)["min_branch_fraction"], 2)
    # and the fused pair must be the one RANKED FIRST, by name
    fused_line = next(x for x in bad.splitlines() if x.startswith("Limb separation"))
    assert fused_line.split("): ", 1)[1].startswith(fused_name)
    # deliberately no threshold: pair_fusion shipped without one (TP 3 / FP 6)
    assert "ranking, not a test" in bad


def undeclare_pairs(tree):
    """DEFECT: the author declared no symmetric pairs at all (`pairs: []`)."""
    tree["pairs"] = []
    return tree


def keep_only_flap(tree, leaf):
    """DEFECT: a one-flap tree -- every node off the root path of `leaf` is
    deleted, so `leaf` is the only childless node."""
    by = {n["name"]: n for n in tree["nodes"]}
    keep, cur = set(), leaf
    while cur is not None:
        keep.add(cur)
        cur = by[cur]["parent"]
    tree["nodes"] = [n for n in tree["nodes"] if n["name"] in keep]
    tree["pairs"], tree["leaves"] = [], [leaf]
    return tree


def test_the_summary_says_so_when_no_pairs_were_declared(tmp_path, monkeypatch):
    """`[]` from the caller means "we looked and there were none", which is a
    different statement from a summary that never mentions pairs at all.
    dog_0 with its pairs undeclared, scored the way `_draft` scores it."""
    t = undeclare_pairs(authored("dog_0"))
    _nodes, leaves, dropped, tn, sp, names = GP._build(t)
    splits, unscored = GP.limb_splits(tn, sp, names)
    assert (splits, unscored, dropped) == ([], [], [])     # the caller LOOKED
    s = GP.summarise(t, leaves, splits=splits, unscored_pairs=unscored,
                     dropped_pairs=dropped)
    assert "No symmetric pairs were declared" in s


def test_the_summary_is_silent_about_pairs_when_the_caller_did_not_look():
    """dog_0 DOES declare two pairs; a caller that did not score them must not
    have the summary imply that it did, either way."""
    t = authored("dog_0")
    assert t["pairs"]                                       # the precondition
    s = GP.summarise(t, _leaves(t))
    assert "Limb separation" not in s
    assert "No symmetric pairs" not in s


def test_one_flap_is_not_1_flaps():
    t = keep_only_flap(authored("dog_0"), "head")
    assert _leaves(t) == ["head"]                           # the precondition
    s = GP.summarise(t, _leaves(t))
    assert "1 flap: head" in s


def test_a_dropped_symmetric_pair_is_surfaced_not_swallowed(tmp_path, monkeypatch):
    """`_draft` filters pairs to leaf-leaf because `tree_contract` requires it.
    A dropped pair means the compiler gets NO mirror constraint, and the human
    would otherwise approve a tree whose bilateral symmetry was discarded."""
    # DEFECT edit: horse_1's hind pair is replaced by its two STIFLES --
    # internal joints -- beside the intact front hoof pair.
    t = _quadruped(fused=False)
    t["pairs"] = [list(FRONT), ["stifle_L", "stifle_R"]]
    s = _summary_of(tmp_path, monkeypatch, t)
    assert "DROPPED" in s
    assert "stifle_L/stifle_R" in s
    assert "NO mirror constraint" in s


def test_a_limb_splits_crash_reports_the_true_declared_count(tmp_path, monkeypatch):
    """Also worth closing (S5 follow-ups): when `limb_splits` raises, the
    summary used to say "1 declared pair(s) could NOT be scored" no matter how
    many pairs were actually declared. `_quadruped(fused=False)` declares TWO
    pairs; both must be named and the count must read 2, not 1."""
    def boom(tree_nodes, symmetric_pairs, names):
        raise RuntimeError("pair_fusion blew up")

    monkeypatch.setattr(GP, "limb_splits", boom)
    t = _quadruped(fused=False)
    assert len(t["pairs"]) == 2                             # the precondition
    s = _summary_of(tmp_path, monkeypatch, t)
    assert f"{len(t['pairs'])} declared pair(s) could NOT be scored" in s
    for a, b in t["pairs"]:
        assert f"{a}/{b}" in s


def _two_leaf_pair() -> dict:
    """A tree with exactly two leaves, declared as a symmetric pair:
    starfish_1 pruned to its arm_L/arm_R pair (`prune_to_pair`).

    `pair_fusion.branch_fraction` needs a THIRD leaf as a reference point to
    triangulate the branch fraction (see its module docstring's three-point
    median); with only two leaves in the whole tree, `others` is empty and it
    returns `None` -- the pair is UNSCORABLE, not fused and not separate.
    """
    return prune_to_pair(authored("starfish_1"), "arm_L", "arm_R")


def test_the_summary_discloses_an_unscorable_declared_pair(tmp_path, monkeypatch):
    """Item 2 (S5 follow-ups) -- BLIND SPOT: deleting the `unscored_pairs`
    branch in `summarise`, or making `limb_splits` always return `unscored =
    []`, left every other test in this file green. Driven here through the
    real `start()` path (not a hand-built call to `summarise`) with a tree
    that has exactly two leaves declared as a pair, so `pair_fusion` cannot
    triangulate a branch fraction for it and the pair falls out UNSCORED. The
    reviewer reproduced this exact line by hand.
    """
    s = _summary_of(tmp_path, monkeypatch, _two_leaf_pair())
    assert "1 declared pair(s) could NOT be scored" in s
    assert "arm_L/arm_R" in s
    assert "gap in the check, not a pass" in s


# --------------------------------------------------------------------------
# C3 -- nothing after the authoring turn may raise
# --------------------------------------------------------------------------

def test_topo_leaves_a_node_with_a_missing_parent_or_in_a_cycle_in_place():
    """Item 3 (S5 follow-ups) -- BLIND SPOT: `_topo`'s docstring states a
    safety property -- a node with a missing parent or caught in a cycle is
    "left in place rather than dropped", because silently discarding part of
    the tree the human is judging would be worse than a rendering glitch.
    Nothing pinned that property: injecting a real drop (see the RED/GREEN
    evidence for this item) left the whole suite green.

    dog_0's draw list with two DEFECT edits: `neck` and `head` become a
    two-node cycle (each names the other as parent), and `tail`'s parent is
    renamed to `ghost`, which never appears in the draw list at all. Both must
    survive.
    """
    def reparent(t, name, parent):
        return (t[0], parent, t[2], t[3]) if t[0] == name else t

    draw = GP._authored_tuples(TA.to_tuples(authored("dog_0")))
    draw = [reparent(reparent(reparent(t, "neck", "head"), "head", "neck"),
                     "tail", "ghost") for t in draw]
    out = GP._topo(draw)
    assert {t[0] for t in out} == {t[0] for t in draw}
    assert {"neck", "head", "tail"} <= {t[0] for t in out}
    assert len(out) == len(draw)


def test_a_figure_that_cannot_be_drawn_still_returns_a_state(tmp_path, monkeypatch):
    monkeypatch.setattr(GP.vlm_render, "render_mesh_views",
                        lambda *a, **k: _fake_mesh_views(tmp_path))

    def cannot_draw(*a, **k):
        raise OSError("no space left on device")

    monkeypatch.setattr(GP.vlm_render, "render_tree_sheet", cannot_draw)
    st = asyncio.run(GP.start("fake.glb", client=FakeClient([DOG]),
                              out_dir=str(tmp_path)))
    assert st["status"] == "awaiting_review"
    assert st["sheet_png"] is None
    assert "could not be drawn" in st["summary"]
    assert "no space left" in st["summary"]
    assert json.loads(json.dumps(st)) == st


def test_topo_sorts_a_child_first_list():
    """dog_0's draw list REVERSED (edit), so every child precedes its parent;
    `_topo` must hand back the same nodes, parents first."""
    draw = list(reversed(GP._authored_tuples(TA.to_tuples(authored("dog_0")))))
    out = GP._topo(draw)
    assert sorted(out, key=str) == sorted(draw, key=str)
    at = {t[0]: i for i, t in enumerate(out)}
    assert all(t[1] is None or at[t[1]] < at[t[0]] for t in out)
    # the root -> head chain comes out in that exact order
    chain = [t[0] for t in out if t[0] in ("body", "neck", "head")]
    assert chain == ["body", "neck", "head"]


# --------------------------------------------------------------------------
# M3 -- one unit system on the figure, and it is GRID units
# --------------------------------------------------------------------------

def test_the_sheet_draws_the_authored_tree_in_grid_units(tmp_path, monkeypatch):
    monkeypatch.setattr(GP.vlm_render, "render_mesh_views",
                        lambda *a, **k: _fake_mesh_views(tmp_path))
    drawn = {}
    real = GP.vlm_render.render_tree_sheet

    def spy(nodes, out_path, **kw):
        drawn["nodes"] = nodes
        return real(nodes, out_path, **kw)

    monkeypatch.setattr(GP.vlm_render, "render_tree_sheet", spy)
    # dog_0 as authored has a pass-through (degree-2) `neck`: body -> neck -> head.
    neck = next(n for n in DOG["nodes"] if n["name"] == "neck")
    assert [n["parent"] for n in DOG["nodes"]].count("neck") == 1   # the precondition
    st = asyncio.run(GP.start("fake.glb", client=FakeClient([DOG]),
                              out_dir=str(tmp_path)))
    assert st["status"] == "awaiting_review"
    assert {n[0] for n in drawn["nodes"]} == {n["name"] for n in DOG["nodes"]}
    # GRID units: the authored length, not the metric tree's rescaled one
    metric_neck = st["metric_tree"]["tree_nodes"][DOG["nodes"].index(neck)]["length"]
    assert metric_neck != neck["length"]                    # the two differ here
    assert {n[0]: n[3] for n in drawn["nodes"]}["neck"] == neck["length"]



# --------------------------------------------------------------------------
# I1 / I5 / I2 -- the authoring turn
# --------------------------------------------------------------------------

def zero_length_edge(tree, name):
    """DEFECT: node `name` authored with length 0 -- a zero-length edge is not
    a flap, and `tree_contract` rejects it ("must be > 0")."""
    next(n for n in tree["nodes"] if n["name"] == name)["length"] = 0
    return tree


BAD_DOG = zero_length_edge(authored("dog_0"), "head")


def test_a_rejected_tree_is_repaired_not_re_authored_blind(tmp_path, monkeypatch):
    """The measured run (`scripts/run_rule6.py:87-89`, the script that produced
    `rule6_raw.json` and every figure the eval reproduces) appends THREE
    messages on a validation failure: the assistant tool call, the tool result,
    then the rejection. Appending only the user message left the history as
    ['user','user','user'] -- the model was told "validate_tree REJECTED that
    tree" while the tree it submitted was not in its context at all, so it
    re-authored blind instead of repairing."""
    monkeypatch.setattr(GP.vlm_render, "render_mesh_views",
                        lambda *a, **k: _fake_mesh_views(tmp_path))
    c = FakeClient([BAD_DOG, DOG])
    st = asyncio.run(GP.start("fake.glb", client=c, out_dir=str(tmp_path)))
    assert st["status"] == "awaiting_review"      # the re-author SUCCEEDED
    assert len(c.calls) == 2

    msgs = c.calls[-1]["messages"]
    assert [m["role"] for m in msgs] == ["user", "assistant", "tool", "user"]
    # the REJECTED tree itself is back in front of the model
    call = msgs[1]["tool_calls"][0]
    assert json.loads(call["function"]["arguments"]) == BAD_DOG
    assert msgs[2]["tool_call_id"] == call["id"]
    assert "validate_tree REJECTED" in msgs[3]["content"]


def test_a_truncated_tool_call_argument_is_a_state_not_a_traceback(tmp_path, monkeypatch):
    """An OpenAI-compatible endpoint that hits the completion cap mid-tool-call
    commonly returns finish_reason 'length' WITH a partial tool call whose
    `arguments` string is cut off -- the bat case is likelier to land here than
    on the no-tool-call branch. `json.loads` used to raise straight out of
    `start()`."""
    monkeypatch.setattr(GP.vlm_render, "render_mesh_views",
                        lambda *a, **k: _fake_mesh_views(tmp_path))
    # DEFECT edit: DOG's own arguments string, cut off two characters into the
    # first node's name -- the shape a completion cap leaves behind.
    raw = json.dumps(DOG)
    cut = raw.index('"name": "') + len('"name": "') + 2
    c = FakeClient([RawCall(raw[:cut])])
    st = asyncio.run(GP.start("fake.glb", client=c, out_dir=str(tmp_path)))
    assert st["status"] == "failed"
    assert st["tree"] is None
    assert "did not parse as JSON" in st["note"]
    assert "LLM_MAX_TOKENS" in st["note"]


class BudgetClient(FakeClient):
    """A client that exposes `max_tokens`, as `llm_client.LLMClient` does."""

    def __init__(self, payloads, max_tokens):
        super().__init__(payloads)
        self.max_tokens = max_tokens


def test_a_too_small_token_budget_is_refused_by_name_before_any_call(tmp_path, monkeypatch):
    """Spec §7: LLM_MAX_TOKENS must be >= 64000, and `llm_client` defaults to
    4096. The parent spec measured the cost: 4096 -> 32000 took 6/27 cells
    producing a tree to 27/27. Guessing is worse than saying so, and naming it
    costs no authoring turn."""
    monkeypatch.setattr(GP.vlm_render, "render_mesh_views",
                        lambda *a, **k: _fake_mesh_views(tmp_path))
    c = BudgetClient([DOG], 4096)
    st = asyncio.run(GP.start("fake.glb", client=c, out_dir=str(tmp_path)))
    assert st["status"] == "failed"
    assert "LLM_MAX_TOKENS is 4096" in st["note"]
    assert "64000" in st["note"]
    assert c.calls == [], "the refusal must cost no authoring turn"


def test_an_adequate_token_budget_is_not_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(GP.vlm_render, "render_mesh_views",
                        lambda *a, **k: _fake_mesh_views(tmp_path))
    c = BudgetClient([DOG], GP.REQUIRED_MAX_TOKENS)
    st = asyncio.run(GP.start("fake.glb", client=c, out_dir=str(tmp_path)))
    assert st["status"] == "awaiting_review"
    assert len(c.calls) == 1


# --------------------------------------------------------------------------
# I3 -- terminal states are terminal, and a failed round keeps nothing stale
# --------------------------------------------------------------------------

def test_an_approved_state_cannot_be_quietly_un_approved(tmp_path, monkeypatch):
    st, c = _started(tmp_path, monkeypatch, [DOG, DOG])
    ok = asyncio.run(GP.resume(st, "approve", client=c, out_dir=str(tmp_path)))
    with pytest.raises(ValueError, match="cannot resume a approved state"):
        asyncio.run(GP.resume(ok, "revise", "actually no", client=c,
                              out_dir=str(tmp_path)))
    assert len(c.calls) == 1




def test_a_failed_revision_can_never_ship_the_previous_rounds_figure(tmp_path, monkeypatch):
    """The row that matters. A revision whose authoring truncated left
    `round=1` beside round 0's `sheet_png` and summary, and
    `resume(.., "approve")` then returned `approved` on a tree for a revision
    that never happened."""
    st, c = _started(tmp_path, monkeypatch, [DOG, None])
    round0_sheet = st["sheet_png"]

    st = asyncio.run(GP.resume(st, "revise", "fix the legs", client=c,
                               out_dir=str(tmp_path)))
    assert st["status"] == "failed"
    assert st["round"] == 1
    # nothing from round 0 may survive as if it described round 1
    assert st["sheet_png"] is None
    assert st["metric_tree"] is None
    assert st["summary"] == ""
    assert round0_sheet is not None

    with pytest.raises(ValueError, match="cannot approve a failed state"):
        asyncio.run(GP.resume(st, "approve", client=c, out_dir=str(tmp_path)))


def test_a_failed_round_is_recoverable_by_revising_again(tmp_path, monkeypatch):
    """Allowed ON PURPOSE and the only thing a terminal status permits: the
    tree that last authored successfully is still in the state, so re-authoring
    from it with the human's words is the obvious recovery. Made explicit here
    rather than left as a side effect."""
    st, c = _started(tmp_path, monkeypatch, [DOG, None, DOG])
    st = asyncio.run(GP.resume(st, "revise", "fix the legs", client=c,
                               out_dir=str(tmp_path)))
    assert st["status"] == "failed" and st["tree"] is not None
    st = asyncio.run(GP.resume(st, "revise", "try again", client=c,
                               out_dir=str(tmp_path)))
    assert st["status"] == "awaiting_review"
    assert st["round"] == 2
    assert st["sheet_png"] is not None
    # the previous tree was carried into the retry, not thrown away
    sent = json.dumps(c.calls[-1]["messages"])
    assert all(n["name"] in sent for n in DOG["nodes"])


def test_an_unknown_verdict_is_refused():
    st = GP._blank_state("fake.glb")
    st["status"] = "awaiting_review"
    with pytest.raises(ValueError, match="verdict must be"):
        asyncio.run(GP.resume(st, "maybe", client=None, out_dir="/tmp"))


# --------------------------------------------------------------------------
# The authoring turn: a malformed tool call is told what it got wrong
# --------------------------------------------------------------------------

def test_a_tool_call_without_nodes_is_told_which_keys_it_sent(tmp_path, monkeypatch):
    """`unbuildable: 'nodes'` was the single most common authoring failure on
    2026-09-13 (horse, bat, scorpion, cat -- 4 rolls): the tool-call JSON parsed
    but had no `nodes` list, and the model was told only the bare KeyError text
    `'nodes'`, which it cannot act on inside the repair loop. The rejection now
    names the missing field, the keys it DID send, and the required ones."""
    monkeypatch.setattr(GP.vlm_render, "render_mesh_views",
                        lambda *a, **k: _fake_mesh_views(tmp_path))
    # DEFECT edit: DOG's nodes and leaves wrapped one level deep under "tree".
    wrapped = {"subject_guess": DOG["subject_guess"], "readings": DOG["readings"],
               "tree": {"nodes": DOG["nodes"], "leaves": DOG["leaves"]}}
    c = FakeClient([wrapped, DOG])
    st = asyncio.run(GP.start("fake.glb", client=c, out_dir=str(tmp_path)))
    assert st["status"] == "awaiting_review"      # the re-author SUCCEEDED
    rejection = c.calls[-1]["messages"][3]["content"]
    assert "missing field 'nodes'" in rejection
    assert "subject_guess, readings, tree" in rejection      # what it sent
    assert "subject_guess, readings, nodes, leaves" in rejection  # what is required
    assert "unbuildable: 'nodes'" not in rejection


def test_review_does_not_warn_about_branching(tmp_path, monkeypatch):
    """Branching hub graphs pack (nest.py), so a forked-antler tree reaches
    review with no packing warning (spec 2026-10-10 §3)."""
    from test_pack_chain import antlered
    monkeypatch.setattr(GP.vlm_render, "render_mesh_views",
                        lambda *a, **k: _fake_mesh_views(tmp_path))
    t = antlered()
    payload = {k: t[k] for k in ("subject_guess", "nodes", "pairs", "readings", "leaves")}
    st = asyncio.run(GP.start("fake.glb", client=FakeClient([payload]), out_dir=str(tmp_path)))
    assert st["status"] == "awaiting_review"
    assert "pack_problem" not in st
    assert "cannot pack" not in st["summary"]


def test_revisions_are_not_capped(tmp_path, monkeypatch):
    """The human decides when to stop: the 3-revision cap was removed on
    2026-10-11. A fourth and a fifth revision each author a round."""
    st, c = _started(tmp_path, monkeypatch, [DOG] * 6)
    for i, msg in enumerate(("a", "b", "c", "d", "e")):
        st = asyncio.run(GP.resume(st, "revise", msg, client=c, out_dir=str(tmp_path)))
        assert st["status"] == "awaiting_review" and st["round"] == i + 1
    assert len(c.calls) == 6          # one draft + five revisions
    assert [h["feedback"] for h in st["history"]] == ["a", "b", "c", "d", "e"]


def test_a_saved_exhausted_state_resumes_like_a_review(tmp_path, monkeypatch):
    """Runs saved before the cap was removed end in `exhausted`, with the last
    authored tree kept. They continue: a revision authors, an approval approves."""
    st, c = _started(tmp_path, monkeypatch, [DOG, DOG])
    old = dict(st, status="exhausted", note="3 revisions were used and your last critique "
                                             "was not satisfied.")
    revised = asyncio.run(GP.resume(old, "revise", "longer tail", client=c,
                                    out_dir=str(tmp_path)))
    assert revised["status"] == "awaiting_review" and revised["note"] is None
    assert len(c.calls) == 2
    approved = asyncio.run(GP.resume(old, "approve", client=c, out_dir=str(tmp_path)))
    assert approved["status"] == "approved" and approved["note"] is None


def test_a_prose_answer_shows_the_human_what_the_model_said(tmp_path, monkeypatch):
    """2026-10-11 (the moose): a revision came back in prose, no tool call, and the
    note said only "the model returned no tree (finish_reason: stop)" -- the text
    was thrown away. The note now carries the start of it, capped."""
    st, c = _started(tmp_path, monkeypatch,
                     [DOG, Prose("I lowered the head and kept the neck.\n" + "x" * 2000)])
    st = asyncio.run(GP.resume(st, "revise", "head down", client=c, out_dir=str(tmp_path)))
    assert st["status"] == "failed"
    assert st["note"].startswith("the model answered in text instead of submitting a tree")
    assert "I lowered the head and kept the neck." in st["note"]
    assert len(st["note"]) < 400


def test_a_tree_field_sent_as_a_json_string_is_decoded(tmp_path, monkeypatch):
    """2026-10-11 (moose, live A/B): about 1 in 8 Haiku authoring turns sent
    `nodes` as a JSON-encoded STRING. It was read character by character and
    rejected as "unbuildable: 'str' object has no attribute 'get'" on every
    repair. It is decoded now, at no extra call, and the tree kept is the
    decoded one (the next revision is handed `prior_tree["nodes"]`)."""
    enc = dict(DOG, nodes=json.dumps(DOG["nodes"]), pairs=json.dumps(DOG["pairs"]))
    st, c = _started(tmp_path, monkeypatch, [enc])
    assert st["status"] == "awaiting_review"
    assert len(c.calls) == 1
    assert st["tree"]["nodes"] == DOG["nodes"] and st["tree"]["pairs"] == DOG["pairs"]


def test_an_undecodable_string_field_gets_a_repair_message_that_names_it(tmp_path, monkeypatch):
    bad = dict(DOG, nodes="the nodes are: body, head, legs")
    st, c = _started(tmp_path, monkeypatch, [bad, DOG])
    assert st["status"] == "awaiting_review" and len(c.calls) == 2
    repair = json.dumps(c.calls[1]["messages"][-1])
    assert "`nodes` must be a JSON array" in repair and "not a string" in repair
    assert "has no attribute" not in repair


def test_fields_spilled_into_the_nodes_string_are_recovered(tmp_path, monkeypatch):
    """The shape actually captured live (2026-10-11, Haiku 5.5, moose revision): the
    `nodes` value is a string holding the nodes array AND the rest of the object --
    `[...],"leaves":[...],"pairs":[...],"notes":"..."}]` -- so `leaves` and `pairs`
    are absent from the arguments and a plain json.loads fails ("Extra data"). The
    repairs repeated the slip, so it is recovered rather than re-asked."""
    spilled = (json.dumps(DOG["nodes"]) + ',"leaves":' + json.dumps(DOG["leaves"])
               + ',"pairs":' + json.dumps(DOG["pairs"]) + ',"notes":"head points down"}]')
    reply = {"subject_guess": DOG["subject_guess"], "readings": DOG["readings"], "nodes": spilled}
    st, c = _started(tmp_path, monkeypatch, [reply])
    assert st["status"] == "awaiting_review" and len(c.calls) == 1
    assert st["tree"]["nodes"] == DOG["nodes"]
    assert st["tree"]["leaves"] == DOG["leaves"] and st["tree"]["pairs"] == DOG["pairs"]
