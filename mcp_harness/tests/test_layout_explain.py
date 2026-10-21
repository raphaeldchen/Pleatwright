"""The layout question's card text and VLM explanation (spec 2026-10-16 §7, §8.1)."""
import asyncio
import json

import layout_explain as LE
from test_gated_pipeline import FakeClient, Prose

SYM = {"grid": 50, "grid_init": 50, "perimeter_bound": 40, "n_over_bound": 1.25,
       "scale": 0.02, "slack_fraction": 0.5916, "flap_expansion_max": 3.0,
       "flap_expansion_median": 2.0, "mean_layers": 43.27, "creases": 2656}
#: dolphin_0's unmirrored option, built by hand.
SMALL = {"grid": 32, "grid_init": 32, "perimeter_bound": 40, "n_over_bound": 0.8,
         "scale": 0.03125, "slack_fraction": 0.3, "flap_expansion_max": 2.0,
         "flap_expansion_median": 1.5, "mean_layers": 30.1, "creases": 1400}
SUMMARY = {"verdict": "ask", "gain": 1.5625, "n_smaller": 32,
           "symmetric": {"grid": 50, "metrics": SYM},
           "smaller": {"grid": 32, "metrics": SMALL},
           "recommended": "smaller"}
PAIRS = [["left_flipper", "right_flipper"]]


def test_card_recommends_first_with_the_gain():
    card = LE.card(SUMMARY)
    first, second = card["options"]
    assert first["id"] == "smaller" and first["recommended"] and first["grid"] == 32
    assert "1.56×" in " ".join(first["pros"])
    assert second["id"] == "symmetric" and not second["recommended"] and second["grid"] == 50
    assert card["question"]


def test_card_text_cites_only_numbers_from_the_summary():
    card = LE.card(SUMMARY)
    smaller, symmetric = (" ".join(o["pros"] + o["cons"]) for o in card["options"])
    assert "1400" in smaller and "2656" in smaller and "30.1" in smaller and "43.3" in smaller
    assert "mirror" in smaller and "mirror" in symmetric
    assert "36%" in symmetric and "59%" in symmetric


def test_card_can_recommend_symmetric_without_inventing_pros():
    s = {**SUMMARY, "recommended": "symmetric"}
    assert [o["id"] for o in LE.card(s)["options"]] == ["symmetric", "smaller"]


def test_explain_uses_the_tool_text():
    c = FakeClient([{"explanation": "Dolphins read fine either way."}])
    got = asyncio.run(LE.explain(c, SUMMARY, "dolphin", PAIRS))
    assert got == "Dolphins read fine either way."
    sent = json.dumps(c.calls[0]["messages"])
    assert "50" in sent and "32" in sent and "1.56" in sent and "dolphin" in sent
    assert "left_flipper" in sent and "smaller" in c.calls[0]["system"]


def test_explain_says_when_there_are_no_pairs():
    c = FakeClient([{"explanation": "ok"}])
    asyncio.run(LE.explain(c, SUMMARY, "dolphin", []))
    assert "no bilateral" in json.dumps(c.calls[0]["messages"])


def test_explain_falls_back_on_a_refusal():
    assert asyncio.run(LE.explain(FakeClient([None]), SUMMARY, "dolphin", PAIRS)) \
        == LE.template_explanation(SUMMARY, "dolphin", PAIRS)


def test_explain_falls_back_on_prose():
    assert asyncio.run(LE.explain(FakeClient([Prose("Sure!")]), SUMMARY, "dolphin", PAIRS)) \
        == LE.template_explanation(SUMMARY, "dolphin", PAIRS)


def test_explain_falls_back_on_empty_text_and_on_an_exception():
    t = LE.template_explanation(SUMMARY, "dolphin", PAIRS)
    assert asyncio.run(LE.explain(FakeClient([{"explanation": "   "}]), SUMMARY, "dolphin", PAIRS)) == t

    class Boom:
        async def run_turn(self, *a):
            raise RuntimeError("down")
    assert asyncio.run(LE.explain(Boom(), SUMMARY, "dolphin", PAIRS)) == t


def test_explain_falls_back_when_the_model_call_hangs(monkeypatch):
    monkeypatch.setattr(LE, "EXPLAIN_TIMEOUT_S", 0.05)

    class Slow:
        async def run_turn(self, *a):
            await asyncio.sleep(5)
    assert asyncio.run(LE.explain(Slow(), SUMMARY, "dolphin", PAIRS)) \
        == LE.template_explanation(SUMMARY, "dolphin", PAIRS)


def test_explain_caps_length():
    c = FakeClient([{"explanation": "x" * 2000}])
    assert len(asyncio.run(LE.explain(c, SUMMARY, "dolphin", PAIRS))) <= 600


def test_template_explanation_names_the_numbers():
    t = LE.template_explanation(SUMMARY, "dolphin", PAIRS)
    assert "dolphin" in t and "1.56" in t and "50" in t and "32" in t
