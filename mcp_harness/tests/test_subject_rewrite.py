"""The mesh review's feedback rewrite (spec 2026-10-11 §3)."""
import asyncio
import json

import pytest

import subject_rewrite as SR
from test_gated_pipeline import FakeClient, Prose


@pytest.mark.parametrize("text,needle", [
    ("bull elk, long legs", "moose"),                        # subject words kept
    ("moose with no tail", "remove: no"),                    # negation
    ("tailless moose", "tailless"),
    ("moose, " + "very " * 30 + "tall", "at most 25 words"),
    ("moose on a white background", "background"),           # scene words belong to the template
])
def test_problems_name_the_rule_broken(text, needle):
    errs = SR.problems(text, "moose")
    assert errs and needle in " ".join(errs)


@pytest.mark.parametrize("text,word", [
    ("moose whose legs shouldn't be fused", "shouldn't"),
    ("moose whose legs aren't fused", "aren't"),
    ("moose whose legs doesn\u2019t touch", "doesn\u2019t"),
    ("moose lacking a tail", "lacking"),
])
def test_contractions_and_lacking_are_negations(text, word):
    errs = SR.problems(text, "moose")
    assert errs and f"remove: {word}" in " ".join(errs)


@pytest.mark.parametrize("subject,good", [
    ("hairless cat", "hairless cat, smooth bare skin, four slim legs"),
    ("cat with no tail", "cat with no tail, rounded rump, four slim legs"),
    ("3d dog", "3d dog, four separate legs, floppy ears"),
    ("t rex 2", "t rex 2, two strong legs, long thick tail"),
    ("studio cat", "studio cat, four slim legs"),
])
def test_a_subjects_own_words_never_trip_the_rules(subject, good):
    assert SR.problems(good, subject) == []


def test_a_long_subject_still_caps_the_extra_words_at_25():
    subject = " ".join(f"s{i}" for i in range(30))
    assert SR.problems(subject + " " + "long " * 25, subject) == []
    assert any("at most 25" in e for e in SR.problems(subject + " " + "long " * 26, subject))


def test_a_good_description_has_no_problems():
    assert SR.problems("bull moose, four long well-separated legs, short stubby tail", "moose") == []
    assert SR.problems("Bull Moose with broad palmate antlers", "bull moose") == []


def test_rewrite_returns_the_description_from_one_forced_tool_call():
    c = FakeClient([{"description": "bull moose, four long well-separated legs"}])
    got = asyncio.run(SR.rewrite(c, "moose", ["the legs are fused"], None))
    assert got == "bull moose, four long well-separated legs"
    sent = json.dumps(c.calls[0]["messages"])
    assert "the legs are fused" in sent and "moose" in sent


def test_every_round_sends_the_original_subject_and_all_feedback():
    c = FakeClient([{"description": "moose, short stubby tail"}])
    asyncio.run(SR.rewrite(c, "moose", ["legs fused", "no tail"], None))
    sent = json.dumps(c.calls[0]["messages"])
    assert "legs fused" in sent and "no tail" in sent


def test_a_negated_rewrite_gets_a_repair_that_names_the_word():
    """Review focus 1: "no tail" must come back phrased positively."""
    c = FakeClient([{"description": "moose with no tail"}, {"description": "moose, short stubby tail"}])
    assert asyncio.run(SR.rewrite(c, "moose", ["no tail"], None)) == "moose, short stubby tail"
    repair = json.dumps(c.calls[1]["messages"][-1])
    assert "remove: no" in repair


def test_a_prose_answer_is_repaired_too():
    c = FakeClient([Prose("Sure! A moose with long legs."), {"description": "moose, long legs"}])
    assert asyncio.run(SR.rewrite(c, "moose", ["legs too short"], None)) == "moose, long legs"


def test_three_bad_answers_raise_rewrite_failed():
    c = FakeClient([{"description": "no"}] * 3)
    with pytest.raises(SR.RewriteFailed, match="could not rewrite"):
        asyncio.run(SR.rewrite(c, "moose", ["x"], None))
    assert len(c.calls) == 3


# ---- anatomy(): the concept-image experiment's anatomy text (spec 2026-10-16 §1)

def test_anatomy_returns_valid_description():
    c = FakeClient([{"description": "scorpion with eight walking legs, four on each side, two large "
                                     "pincers, and a segmented tail curving up to a stinger"}])
    out = asyncio.run(SR.anatomy(c, "scorpion"))
    assert out.startswith("scorpion with eight walking legs")
    prompt = json.dumps(c.calls[0]).lower()
    assert "scorpion" in prompt and "convention" not in prompt and "leaf" not in prompt


def test_anatomy_allows_40_words_rewrite_still_25():
    assert SR.problems("crab " + "big " * 30, "crab", max_words=40) == []
    assert any("at most 25 words" in e for e in SR.problems("crab " + "big " * 30, "crab"))


def test_anatomy_repairs_a_negation():
    c = FakeClient([{"description": "dolphin with no legs"},
                    {"description": "dolphin with two pectoral flippers, a dorsal fin and a tail fluke"}])
    assert "flippers" in asyncio.run(SR.anatomy(c, "dolphin"))
    assert len(c.calls) == 2
