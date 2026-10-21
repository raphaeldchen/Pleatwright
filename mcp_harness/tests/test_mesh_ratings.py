"""Mesh ratings (spec 2026-10-11 §1): a subject key, Wilson ranking, and a
ratings.json beside each cached mesh."""
import json
import os

import pytest

import mesh_ratings as R


@pytest.mark.parametrize("prompt,key", [
    ("a moose", "moose"), ("Moose.", "moose"), ("the moose", "moose"),
    ("  A Moose!! ", "moose"), ("bull moose", "bull moose"), ("an antelope", "antelope"),
    ("can you make a fox", "can you make a fox")])
def test_subject_key(prompt, key):
    assert R.subject_key(prompt) == key


def test_non_latin_subjects_get_distinct_keys():
    assert R.subject_key("狗") and R.subject_key("猫")
    assert R.subject_key("狗") != R.subject_key("猫")
    assert R.subject_key("Éléphant") == "éléphant"
    assert R.words("T-Rex 2!") == ["t", "rex", "2"]


def test_best_proven_of_an_empty_subject_is_none(tmp_path):
    _entry(tmp_path, "a", **_r(3, subject=""))
    assert R.best_proven(str(tmp_path), "hf2", "") is None


def test_wilson_ranks_many_approvals_above_one():
    assert R.wilson_lower_bound(0, 0) == 0.0
    assert R.wilson_lower_bound(9, 1) > R.wilson_lower_bound(1, 0)
    assert abs(R.wilson_lower_bound(1, 0) - 0.2065) < 1e-3


def _entry(root, name, glb=b"glTF", **ratings):
    d = root / name
    d.mkdir()
    if glb is not None:
        (d / "mesh.glb").write_bytes(glb)
    if ratings:
        (d / "ratings.json").write_text(json.dumps(ratings))
    return str(d)


def _r(approvals, rejections=0, provider="hf2", subject="moose"):
    return dict(subject=subject, provider=provider, prompt=subject, description=None,
                seed=None, approvals=approvals,
                rejections=[{"feedback": "x", "run": "r", "utc": "t"}] * rejections)


def test_record_verdict_counts_and_keeps_the_identity(tmp_path):
    d = _entry(tmp_path, "moose-1")
    R.record_verdict(d, approved=False, run_id="run-a", subject="moose", provider="hf2",
                     prompt="a moose", description="bull moose", seed=7, feedback="legs fused")
    r = R.record_verdict(d, approved=True, run_id="run-b", subject="moose", provider="hf2",
                         prompt="a moose", description="bull moose", seed=7)
    assert r["approvals"] == 1 and [x["feedback"] for x in r["rejections"]] == ["legs fused"]
    assert r["subject"] == "moose" and r["seed"] == 7 and r["description"] == "bull moose"
    assert R.read_ratings(d) == r
    assert not [f for f in os.listdir(d) if f.endswith(".tmp")]        # written atomically


def test_best_proven_ranks_by_wilson_then_approvals(tmp_path):
    _entry(tmp_path, "one-of-one", **_r(1, 0))
    best = _entry(tmp_path, "nine-of-ten", **_r(9, 1))
    _entry(tmp_path, "unrated")
    _entry(tmp_path, "rejected-only", **_r(0, 3))
    assert R.best_proven(str(tmp_path), "hf2", "moose") == best


def test_best_proven_needs_an_approval_and_matches_provider_and_subject(tmp_path):
    _entry(tmp_path, "fake-one", **_r(5, 0, provider="fake"))
    _entry(tmp_path, "elk-one", **_r(5, 0, subject="elk"))
    _entry(tmp_path, "no-votes", **_r(0, 0))
    assert R.best_proven(str(tmp_path), "hf2", "moose") is None
    assert R.best_proven(str(tmp_path / "missing"), "hf2", "moose") is None


def test_best_proven_skips_a_missing_or_empty_mesh(tmp_path):
    """Review focus 4: a proven folder whose mesh.glb is gone or empty is never served."""
    _entry(tmp_path, "gone", glb=None, **_r(9, 0))
    _entry(tmp_path, "empty", glb=b"", **_r(9, 0))
    ok = _entry(tmp_path, "ok", **_r(1, 0))
    assert R.best_proven(str(tmp_path), "hf2", "moose") == ok


def test_an_unreadable_ratings_file_is_ignored(tmp_path):
    d = _entry(tmp_path, "torn")
    (tmp_path / "torn" / "ratings.json").write_text("{not json")
    assert R.read_ratings(d) is None
    assert R.best_proven(str(tmp_path), "hf2", "moose") is None


def test_a_mistyped_ratings_file_is_ignored(tmp_path):
    """Valid JSON with a wrong-typed field must not crash best_proven (every new
    run calls it); the folder is skipped, and a new verdict starts it afresh."""
    bad = [
        {"approvals": 1, "rejections": 5},
        {"approvals": None, "rejections": []},
        {"approvals": "x", "rejections": []},
        {"approvals": True, "rejections": []},
    ]
    for i, ratings in enumerate(bad):
        d = _entry(tmp_path, f"bad-{i}")
        (tmp_path / f"bad-{i}" / "ratings.json").write_text(
            json.dumps(dict(provider="hf2", subject="moose", **ratings)))
        assert R.read_ratings(d) is None
    assert R.best_proven(str(tmp_path), "hf2", "moose") is None

    d = str(tmp_path / "bad-0")
    r = R.record_verdict(d, approved=True, run_id="run-c", subject="moose",
                         provider="hf2", prompt="a moose")
    assert r["approvals"] == 1 and r["rejections"] == []
    assert R.read_ratings(d) == r
    assert R.best_proven(str(tmp_path), "hf2", "moose") == d
