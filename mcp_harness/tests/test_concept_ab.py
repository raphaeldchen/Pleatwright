"""The concept-image experiment (spec docs/superpowers/specs/2026-10-16-concept-image-quality-design.md).

Every test here is offline: fakes stand in for Gemini, Hunyuan and Claude."""
import pytest

from concept_ab import arms as A


# ---- Task 3: arms, cells, checklist, ledger

def test_seventeen_subjects_no_tardigrade():
    assert len(A.SUBJECTS) == 17 and not {"tardigrade", "water bear"} & set(A.SUBJECTS)
    assert "guinea pig" in A.SUBJECTS


def test_cell_dir_layout(tmp_path):
    assert A.cell_dir(str(tmp_path), "C", "guinea pig", 2).endswith("C/guinea_pig/r2")


def test_prompts_per_arm():
    assert "3D render of a single scorpion," in A.concept_prompt_for(A.ARMS["B"], "scorpion", None)
    p = A.concept_prompt_for(A.ARMS["D"], "scorpion", "scorpion with eight walking legs")
    assert p.startswith("A full-body wildlife photograph of a single scorpion with eight walking legs,")
    assert "3D render of a single scorpion with eight" in A.concept_prompt_for(
        A.ARMS["C"], "scorpion", "scorpion with eight walking legs")


def test_anatomy_arm_without_text_is_refused():
    with pytest.raises(ValueError):
        A.concept_prompt_for(A.ARMS["C"], "scorpion", None)


def test_seeds_per_round_and_candidate():
    assert A.seed_for("B", 1) == 11 and A.seed_for("B", 2) == 22
    assert [A.seed_for("E", 1, i) for i in range(4)] == [101, 102, 103, 104]


def test_arm_e_copies_the_winner_with_four_candidates():
    e = A.arm_e("D")
    assert e.name == "E" and e.candidates == 4
    assert e.template == A.ARMS["D"].template and e.uses_anatomy


def test_checklist_covers_every_subject_with_counts():
    cl = A.load_checklist()
    assert set(cl) == set(A.SUBJECTS)
    assert all(isinstance(p["count"], int) and p["count"] > 0 for parts in cl.values() for p in parts)
    assert {p["part"] for p in cl["scorpion"]} >= {"walking legs", "pincers"}
    assert "8 walking legs" in A.checklist_text("scorpion")


def test_ledger_refuses_past_cap(tmp_path):
    L = A.Ledger(str(tmp_path / "ledger.json"), cap_usd=0.10, price_usd=0.034)
    L.charge(2, "b")
    assert round(L.spent(), 3) == 0.068
    with pytest.raises(A.BudgetExceeded):
        L.charge(1, "c")
    assert round(A.Ledger(str(tmp_path / "ledger.json"), cap_usd=0.10).spent(), 3) == 0.068


# ---- Task 4: resumable runner

import asyncio
import json
import os

from concept_ab import run as R
from test_gated_pipeline import FakeClient

EXHAUSTION = ("You have exceeded your free ZeroGPU quota (60s requested vs. 0s left). "
              "Create a free account to get 40 min of ZeroGPU quota a day")
PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 64


class FakeProvider:
    """Stands in for TwoStageProvider(reuse_concept=True): draws a FLUX concept
    only when the cell has none, then 'lifts' it."""

    def __init__(self, log, fail=None):
        self.log, self.fail = log, fail

    def generate(self, prompt, out_dir):
        self.log.append(out_dir)
        if self.fail:
            raise self.fail(out_dir)
        if not any(f.startswith("concept.") for f in os.listdir(out_dir)):
            open(os.path.join(out_dir, "concept.webp"), "wb").write(PNG)
        p = os.path.join(out_dir, "mesh.glb")
        open(p, "wb").write(b"glb")
        return p


class FakeImages:
    def __init__(self):
        self.prompts = []

    def __call__(self, prompt, out_path, *, seed=None):
        self.prompts.append(prompt)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        open(out_path, "wb").write(PNG)
        return type("G", (), {"usage": {"candidatesTokenCount": 1290}, "model": "nb", "seed": seed})()


def _run(tmp_path, arms, subjects, *, provider=None, images=None, llm=None, round_=1, **kw):
    log = []
    images = images or FakeImages()
    rep = asyncio.run(R.run_cells(
        str(tmp_path), arms, round_, subjects, llm=llm or FakeClient([]),
        image_fn=images, provider_factory=lambda seed: provider or FakeProvider(log),
        ledger=A.Ledger(str(tmp_path / "ledger.json")), **kw))
    return rep, log, images


SCORPION_TEXT = {"description": "scorpion with eight walking legs, four on each side, two pincers"}


def test_runs_each_cell_once_and_skips_done(tmp_path):
    rep, log, images = _run(tmp_path, ["A", "B"], ["scorpion"])
    assert sorted(rep.done) == ["A/scorpion/r1", "B/scorpion/r1"] and rep.stopped is None
    assert len(images.prompts) == 1                       # arm A draws through FLUX, not Gemini
    rep2, log2, images2 = _run(tmp_path, ["A", "B"], ["scorpion"])
    assert sorted(rep2.skipped) == ["A/scorpion/r1", "B/scorpion/r1"]
    assert log2 == [] and images2.prompts == []


def test_anatomy_written_once_and_used_by_c_and_d(tmp_path):
    llm = FakeClient([SCORPION_TEXT])
    rep, _, images = _run(tmp_path, ["B", "C", "D"], ["scorpion"], llm=llm)
    assert len(llm.calls) == 1
    b, c, d = images.prompts
    assert "eight walking legs" not in b
    assert "eight walking legs" in c and "eight walking legs" in d
    assert open(tmp_path / "anatomy" / "scorpion.txt").read().startswith("scorpion with eight")


def test_concept_without_mesh_relifts_without_charging(tmp_path):
    cell = A.cell_dir(str(tmp_path), "B", "dog", 1)
    os.makedirs(cell)
    open(os.path.join(cell, "concept.png"), "wb").write(PNG)
    rep, log, images = _run(tmp_path, ["B"], ["dog"])
    assert rep.done == ["B/dog/r1"] and images.prompts == [] and log == [cell]
    assert A.Ledger(str(tmp_path / "ledger.json")).spent() == 0


def test_gemini_images_are_charged(tmp_path):
    _run(tmp_path, ["B"], ["dog", "cat"])
    assert A.PRICE_USD == 0.042                     # measured 2026-10-16 (gemini_image docstring)
    assert round(A.Ledger(str(tmp_path / "ledger.json")).spent(), 3) == 0.084


def test_quota_stops_run_and_rerun_resumes(tmp_path):
    def exhausted(out_dir):
        if out_dir.endswith(os.path.join("cat", "r1")):
            try:
                raise RuntimeError(EXHAUSTION)
            except RuntimeError as e:
                raise RuntimeError("mesh stage: Space 'tencent/Hunyuan3D-2' rejected the request "
                                   "-- free GPU quota exhausted") from e
        return None

    class Flaky(FakeProvider):
        def generate(self, prompt, out_dir):
            exhausted(out_dir)
            return super().generate(prompt, out_dir)

    rep, _, _ = _run(tmp_path, ["B"], ["dog", "cat", "horse"], provider=Flaky([]))
    assert rep.stopped == "hf_quota" and rep.done == ["B/dog/r1"]
    assert "B/horse/r1" not in rep.done + rep.skipped
    rep2, _, images2 = _run(tmp_path, ["B"], ["dog", "cat", "horse"])
    assert rep2.skipped == ["B/dog/r1"] and rep2.done == ["B/cat/r1", "B/horse/r1"]
    assert len(images2.prompts) == 1                      # cat's concept was kept; only horse is drawn


def test_gemini_quota_stops_run(tmp_path):
    import gemini_image

    def refused(prompt, out_path, *, seed=None):
        raise gemini_image.GeminiImageError("Gemini x answered HTTP 429: You exceeded your current quota")

    rep, _, _ = _run(tmp_path, ["B"], ["dog", "cat"], images=refused)
    assert rep.stopped == "gemini_quota" and rep.done == [] and rep.failed == {}


def test_budget_stops_run(tmp_path):
    log = []
    rep = asyncio.run(R.run_cells(
        str(tmp_path), ["B"], 1, ["dog", "cat"], llm=FakeClient([]), image_fn=FakeImages(),
        provider_factory=lambda seed: FakeProvider(log),
        ledger=A.Ledger(str(tmp_path / "ledger.json"), cap_usd=0.05)))
    assert rep.stopped == "budget" and rep.done == ["B/dog/r1"]


def test_other_failures_recorded_and_run_continues(tmp_path):
    class Broken(FakeProvider):
        def generate(self, prompt, out_dir):
            if "dog" in out_dir:
                raise RuntimeError("mesh stage: Space returned no usable glb")
            return super().generate(prompt, out_dir)

    rep, _, _ = _run(tmp_path, ["B"], ["dog", "cat"], provider=Broken([]))
    assert "no usable glb" in rep.failed["B/dog/r1"] and rep.done == ["B/cat/r1"]


def test_meta_json_records_seed_prompt_model(tmp_path):
    _run(tmp_path, ["D"], ["scorpion"], llm=FakeClient([SCORPION_TEXT]), round_=2)
    meta = json.load(open(os.path.join(A.cell_dir(str(tmp_path), "D", "scorpion", 2), "meta.json")))
    assert meta["arm"] == "D" and meta["round"] == 2 and meta["seed"] == 22
    assert meta["image_model"] == A.NANO_BANANA and meta["prompt"].startswith("A full-body wildlife")
    assert meta["anatomy_text"].startswith("scorpion with eight") and meta["usage"]


def test_arm_e_lifts_only_the_picked_candidate(tmp_path):
    picked = {}

    async def pick(paths, anatomy):
        picked["paths"], picked["anatomy"] = paths, anatomy
        return {"index": 2, "none_acceptable": False, "assessments": []}

    rep, log, images = _run(tmp_path, ["E"], ["scorpion"], llm=FakeClient([SCORPION_TEXT]),
                            winner="C", pick_fn=pick)
    cell = A.cell_dir(str(tmp_path), "E", "scorpion", 1)
    assert rep.done == ["E/scorpion/r1"] and len(images.prompts) == 4 and log == [cell]
    assert [os.path.basename(p) for p in picked["paths"]] == [f"candidate_{i}.png" for i in range(4)]
    assert open(os.path.join(cell, "concept.png"), "rb").read() == PNG
    assert json.load(open(os.path.join(cell, "pick.json")))["index"] == 2
    assert round(A.Ledger(str(tmp_path / "ledger.json")).spent(), 3) == round(4 * A.PRICE_USD, 3)


def test_cli_run_exit_codes(tmp_path, monkeypatch):
    from concept_ab import __main__ as M
    monkeypatch.setattr(M, "_llm", lambda model=None: object())
    for stopped, code in ((None, 0), ("hf_quota", 4), ("gemini_quota", 4), ("budget", 5)):
        async def fake(root, arms, round_, subjects, **kw):
            assert arms == ["B", "C"] and subjects == ["dog"] and round_ == 2
            return R.RunReport(stopped=stopped)
        monkeypatch.setattr(M.run, "run_cells", fake)
        assert M.main(["--root", str(tmp_path), "run", "--arms", "B,C", "--round", "2",
                       "--subjects", "dog"]) == code


# ---- Task 5: judge

from concept_ab import judge as J


def _img(tmp_path, name="i.png"):
    p = tmp_path / name
    p.write_bytes(PNG)
    return str(p)


def _parts(*rows, extras=()):
    return {"parts": [{"part": p, "expected": e, "seen": s, "attached": a} for p, e, s, a in rows],
            "extras": list(extras)}


def test_verdict_is_computed_not_trusted(tmp_path):
    payload = _parts(("walking legs", 8, 7, True))
    payload["verdict"] = "pass"
    c = FakeClient([payload])
    r = asyncio.run(J.assess(c, _img(tmp_path), "scorpion with eight walking legs"))
    assert r["passed"] is False and r["mismatches"] == 1


def test_detached_part_fails(tmp_path):
    c = FakeClient([_parts(("tail", 1, 1, False))])
    assert asyncio.run(J.assess(c, _img(tmp_path), "scorpion with a tail"))["passed"] is False


def test_extras_fail_even_when_parts_match(tmp_path):
    c = FakeClient([_parts(("legs", 4, 4, True), extras=["floating blob above the back"])])
    r = asyncio.run(J.assess(c, _img(tmp_path), "dog with four legs"))
    assert r["passed"] is False and r["mismatches"] == 1


def test_all_parts_right_passes(tmp_path):
    c = FakeClient([_parts(("legs", 4, 4, True), ("tail", 1, 1, True))])
    r = asyncio.run(J.assess(c, _img(tmp_path), "dog with four legs and a tail"))
    assert r["passed"] is True and r["mismatches"] == 0


def test_pick_first_pass_else_fewest_mismatches(tmp_path):
    imgs = [_img(tmp_path, f"{i}.png") for i in range(3)]
    fail2 = _parts(("legs", 8, 6, True), ("tail", 1, 0, True))
    ok = _parts(("legs", 8, 8, True), ("tail", 1, 1, True))
    r = asyncio.run(J.pick(FakeClient([fail2, ok, ok]), imgs, "x"))
    assert r["index"] == 1 and r["none_acceptable"] is False and len(r["assessments"]) == 3
    fail3 = _parts(("legs", 8, 5, True), ("tail", 1, 0, True), ("pincers", 2, 0, True))
    fail1 = _parts(("legs", 8, 7, True), ("tail", 1, 1, True))
    r = asyncio.run(J.pick(FakeClient([fail3, fail1]), imgs[:2], "x"))
    assert r["index"] == 1 and r["none_acceptable"] is True


def test_assess_sends_the_image_and_never_the_checklist_word(tmp_path):
    c = FakeClient([_parts(("legs", 4, 4, True))])
    asyncio.run(J.assess(c, _img(tmp_path), "dog with four legs"))
    sent = json.dumps(c.calls[0])
    assert "image_url" in sent and "dog with four legs" in sent
    assert "checklist" not in sent.lower()


def test_garbled_answers_give_an_error_not_an_exception(tmp_path):
    from test_gated_pipeline import Prose
    c = FakeClient([Prose("looks fine"), Prose("yes"), Prose("ok")])
    r = asyncio.run(J.assess(c, _img(tmp_path), "dog"))
    assert r["passed"] is False and "error" in r and len(c.calls) == 3


# ---- Task 6: draft scores + review page

from concept_ab import review as V


def _cell(root, arm, subject, round_=1, *, draft=None, concept="concept.png"):
    cell = A.cell_dir(str(root), arm, subject, round_)
    os.makedirs(cell, exist_ok=True)
    open(os.path.join(cell, "mesh.glb"), "wb").write(b"glb")
    open(os.path.join(cell, concept), "wb").write(PNG)
    if draft is not None:
        open(os.path.join(cell, "mesh_views.png"), "wb").write(PNG)
        json.dump(draft, open(os.path.join(cell, "draft.json"), "w"))
    return cell


def _draft(passed):
    a = {"parts": [{"part": "legs", "expected": 4, "seen": 4 if passed else 3, "attached": True}],
         "extras": [], "passed": passed, "mismatches": 0 if passed else 1}
    return {"mesh": a, "image": a}


def test_photo_cells_copied(tmp_path):
    lib = tmp_path / "lib"
    (lib / "meshes").mkdir(parents=True)
    (lib / "photos").mkdir()
    (lib / "meshes" / "guinea_pig.glb").write_bytes(b"glb")
    (lib / "photos" / "guinea_pig.png").write_bytes(PNG)
    root = tmp_path / "exp"
    V.ensure_photo_cells(str(root), str(lib))
    cell = A.cell_dir(str(root), "photo", "guinea pig", 1)
    assert open(os.path.join(cell, "mesh.glb"), "rb").read() == b"glb"
    assert open(os.path.join(cell, "concept.png"), "rb").read() == PNG


def test_draft_scores_skip_existing(tmp_path, monkeypatch):
    def fake_render(mesh, out, **k):
        open(out, "wb").write(PNG)
        return {"png": out}
    monkeypatch.setattr(V.vlm_render, "render_mesh_views", fake_render)
    cell = _cell(tmp_path, "B", "dog")
    ok = _parts(("legs", 4, 4, True), ("head", 1, 1, True), ("tail", 1, 1, True))
    c = FakeClient([ok, ok])
    assert asyncio.run(V.draft_scores(str(tmp_path), c)) == 1
    d = json.load(open(os.path.join(cell, "draft.json")))
    assert d["mesh"]["passed"] and d["image"]["passed"]
    assert "4 legs" in json.dumps(c.calls[0])           # the checklist text, for the draft
    assert asyncio.run(V.draft_scores(str(tmp_path), FakeClient([]))) == 0


def test_review_page_has_every_cell_and_prefills(tmp_path):
    _cell(tmp_path, "photo", "dog", draft=_draft(True))
    _cell(tmp_path, "B", "dog", draft=_draft(True))
    _cell(tmp_path, "C", "dog", draft=_draft(False), concept="concept.webp")
    _cell(tmp_path, "C", "dog", round_=2, draft=_draft(True))         # other round: not on the page
    page = open(V.build_review(str(tmp_path), 1)).read()
    for cid in ("photo/dog/r1", "B/dog/r1", "C/dog/r1"):
        assert cid in page
    assert "C/dog/r2" not in page
    assert '<input type="radio" name="B/dog/r1|mesh" value="pass" checked>' in page
    assert '<input type="radio" name="C/dog/r1|mesh" value="fail" checked>' in page
    assert "C/dog/r1/concept.webp" in page and "B/dog/r1/mesh_views.png" in page
    low = page.lower()
    assert not any(w in low for w in ("gemini", "flux", "banana"))
    assert 'data-part="legs"' in page                       # editable checklist


def test_review_page_prefers_saved_scores(tmp_path):
    _cell(tmp_path, "B", "dog", draft=_draft(True))
    json.dump({"round": 1, "cells": {"B/dog/r1": {"mesh": "fail", "image": "pass", "note": "3 legs"}}},
              open(tmp_path / "scores_r1.json", "w"))
    page = open(V.build_review(str(tmp_path), 1)).read()
    assert '<input type="radio" name="B/dog/r1|mesh" value="fail" checked>' in page and "3 legs" in page


def test_undrafted_or_failed_draft_cell_is_left_unmarked(tmp_path):
    _cell(tmp_path, "B", "dog")                                    # no draft.json at all
    _cell(tmp_path, "C", "dog", draft={"mesh": {"parts": [], "extras": [], "passed": False,
                                                "mismatches": 0, "error": "no answer"},
                                       "image": _draft(True)["image"]})
    page = open(V.build_review(str(tmp_path), 1)).read()
    assert 'name="B/dog/r1|mesh" value="pass" checked' not in page
    assert 'name="B/dog/r1|mesh" value="fail" checked' not in page
    assert 'name="C/dog/r1|mesh" value="fail" checked' not in page
    assert 'name="C/dog/r1|image" value="pass" checked' in page


# ---- Task 7: tally, good-enough, winner, calibration

from concept_ab import score as S


def _scores(round_=1, **cells):
    return {"round": round_, "cells": {k.replace("__", "/"): {"mesh": m, "image": i}
                                       for k, (m, i) in cells.items()}}


def test_unscored_cells_reported_not_failed(tmp_path):
    _cell(tmp_path, "A", "dog")
    _cell(tmp_path, "A", "cat")
    t = S.tally({"round": 1, "cells": {"A/dog/r1": {"mesh": "pass", "image": "pass"}}}, str(tmp_path))
    assert t["by_arm"]["A"] == {"round": 1, "passed": 1, "scored": 1}
    assert "A/cat/r1" in t["unscored"]


def test_null_toggle_counts_as_unscored(tmp_path):
    _cell(tmp_path, "B", "dog")
    t = S.tally({"round": 1, "cells": {"B/dog/r1": {"mesh": None, "image": "pass"}}}, str(tmp_path))
    assert t["by_arm"]["B"]["scored"] == 0 and "B/dog/r1" in t["unscored"]


def test_good_enough_is_photo_bar_minus_one(tmp_path):
    subjects = list(A.SUBJECTS)
    cells = {}
    for i, s in enumerate(subjects):
        sl = A.slug(s)
        cells[f"photo/{sl}/r1"] = {"mesh": "pass" if i < 15 else "fail", "image": "pass"}
        cells[f"B/{sl}/r1"] = {"mesh": "pass" if i < 14 else "fail", "image": "pass"}
        cells[f"C/{sl}/r1"] = {"mesh": "pass" if i < 13 else "fail", "image": "pass"}
    t = S.tally({"round": 1, "cells": cells}, str(tmp_path))
    assert t["photo_bar"] == 15
    assert t["good_enough"] == {"B": True, "C": False}


def test_winner_tie_prefers_simpler_arm():
    t = {"by_arm": {"A": {"passed": 16}, "B": {"passed": 12}, "C": {"passed": 12}, "D": {"passed": 11}}}
    assert S.winner(t) == "B"
    t["by_arm"]["D"]["passed"] = 13
    assert S.winner(t) == "D"


def test_calibrate_counts_false_rejects_and_accepts(tmp_path):
    for arm in ("A", "B", "C"):
        _cell(tmp_path, arm, "dog")
    os.makedirs(tmp_path / "anatomy")
    (tmp_path / "anatomy" / "dog.txt").write_text("dog with four legs and a tail")
    owner = {"round": 1, "cells": {"A/dog/r1": {"mesh": "pass", "image": "pass"},
                                   "B/dog/r1": {"mesh": "fail", "image": "fail"},
                                   "C/dog/r1": {"mesh": "fail", "image": "pass"}}}
    ok = _parts(("legs", 4, 4, True))
    bad = _parts(("legs", 4, 3, True))
    c = FakeClient([ok, ok, bad])                 # A agrees, B false accept, C false reject
    r = asyncio.run(S.calibrate(str(tmp_path), c, owner))
    assert r == {"agree": 1, "total": 3, "false_reject": 1, "false_accept": 1, "skipped": 0}
    assert "dog with four legs and a tail" in json.dumps(c.calls[0])


def test_cli_score_writes_tally_and_names_unscored(tmp_path, capsys):
    from concept_ab import __main__ as M
    _cell(tmp_path, "B", "dog")
    _cell(tmp_path, "B", "cat")
    _cell(tmp_path, "photo", "dog")
    json.dump({"round": 1, "cells": {"B/dog/r1": {"mesh": "pass", "image": "pass"},
                                     "photo/dog/r1": {"mesh": "pass", "image": "pass"}}},
              open(tmp_path / "scores_r1.json", "w"))
    assert M.main(["--root", str(tmp_path), "score", "--round", "1"]) == 0
    out = capsys.readouterr().out
    assert "UNSCORED: B/cat/r1" in out and "winner among B-D: B" in out
    assert json.load(open(tmp_path / "tally_r1.json"))["by_arm"]["B"]["passed"] == 1


# ---- Task 8: secondary signal (authored tree + fold)

from concept_ab import trees as T


def test_artifact_leaf_count_uses_tree_convention():
    assert T.artifact_leaf_count("scorpion") == 11 and T.artifact_leaf_count("dolphin") == 5
    assert T.artifact_leaf_count("guinea pig") == 5


def test_tree_signal_records_failure_without_raising(tmp_path, monkeypatch):
    cell = _cell(tmp_path, "B", "dog")

    async def failed(mesh, *, client, out_dir):
        return {"status": "failed", "note": "authoring truncated", "tree": None}
    monkeypatch.setattr(T.gated_pipeline, "start", failed)
    r = asyncio.run(T.tree_signal(str(tmp_path), object()))
    sig = r["B/dog/r1"]
    assert sig["leaves"] is None and sig["folded"] is False and "truncated" in sig["failure"]
    assert json.load(open(os.path.join(cell, "tree_signal.json"))) == sig


def test_tree_signal_counts_leaves_and_folds(tmp_path, monkeypatch):
    _cell(tmp_path, "B", "dog")
    from test_gated_pipeline import DOG
    folded = {}

    async def ok(mesh, *, client, out_dir):
        return {"status": "awaiting_review", "tree": DOG, "subject_guess": "dog"}

    def run(tree_path, out_dir, **kw):
        folded["tree"] = json.load(open(tree_path))
        return {"folder": out_dir}
    monkeypatch.setattr(T.gated_pipeline, "start", ok)
    monkeypatch.setattr(T.pipeline, "run", run)
    sig = asyncio.run(T.tree_signal(str(tmp_path), object()))["B/dog/r1"]
    assert sig == {"leaves": 6, "expected": 6, "match": True, "folded": True, "failure": None}
    assert folded["tree"]["nodes"] == DOG["nodes"]
    assert asyncio.run(T.tree_signal(str(tmp_path), object())) == {}    # done cells are skipped


def test_cli_trees_reports_matches_and_folds(tmp_path, monkeypatch, capsys):
    from concept_ab import __main__ as M
    monkeypatch.setattr(M, "_llm", lambda model=None: object())

    async def fake(root, client, **kw):
        return {"B/dog/r1": {"leaves": 6, "expected": 6, "match": True, "folded": True, "failure": None},
                "B/cat/r1": {"leaves": None, "expected": 6, "match": False, "folded": False,
                             "failure": "authoring: truncated"}}
    monkeypatch.setattr(T, "tree_signal", fake)
    assert M.main(["--root", str(tmp_path), "trees"]) == 0
    out = capsys.readouterr().out
    assert "B/dog/r1" in out and "B/cat/r1" in out and "authoring: truncated" in out


# ---- Final-review fixes

def test_unscored_photo_bar_decides_nothing(tmp_path):
    """C1: with no photo marks the bar is unknown, not 0 -- no arm is declared good enough."""
    t = S.tally({"round": 2, "cells": {"A/dog/r2": {"mesh": "fail", "image": "fail"},
                                      "C/dog/r2": {"mesh": "fail", "image": "fail"}}}, str(tmp_path))
    assert t["photo_bar"] is None and t["good_enough"] == {}


def test_round2_takes_photo_bar_from_round1(tmp_path):
    r1 = {"round": 1, "cells": {"photo/dog/r1": {"mesh": "pass", "image": "pass"},
                                "photo/cat/r1": {"mesh": "pass", "image": "pass"}}}
    r2 = {"round": 2, "cells": {"C/dog/r2": {"mesh": "pass", "image": "pass"},
                                "C/cat/r2": {"mesh": "fail", "image": "pass"}}}
    t = S.tally(r2, str(tmp_path), photo_scores=r1)
    assert t["photo_bar"] == 2 and t["good_enough"] == {"C": True}


def test_cli_score_round2_uses_round1_photo_marks_and_refuses_without(tmp_path, capsys):
    from concept_ab import __main__ as M
    _cell(tmp_path, "C", "dog", round_=2)
    json.dump({"round": 2, "cells": {"C/dog/r2": {"mesh": "pass", "image": "pass"}}},
              open(tmp_path / "scores_r2.json", "w"))
    assert M.main(["--root", str(tmp_path), "score", "--round", "2"]) == 3
    assert "photo bar unscored" in capsys.readouterr().out
    json.dump({"round": 1, "cells": {"photo/dog/r1": {"mesh": "pass", "image": "pass"}}},
              open(tmp_path / "scores_r1.json", "w"))
    assert M.main(["--root", str(tmp_path), "score", "--round", "2"]) == 0


def test_round2_review_prefills_photo_rows_from_round1(tmp_path):
    _cell(tmp_path, "photo", "dog")
    _cell(tmp_path, "C", "dog", round_=2)
    json.dump({"round": 1, "cells": {"photo/dog/r1": {"mesh": "fail", "image": "pass", "note": "tail"}}},
              open(tmp_path / "scores_r1.json", "w"))
    page = open(V.build_review(str(tmp_path), 2)).read()
    assert 'name="photo/dog/r1|mesh" value="fail" checked' in page


SCORPION_PARTS = [{"part": "walking legs", "count": 8}, {"part": "pincers", "count": 2},
                  {"part": "tail", "count": 1}]


def test_checklist_parts_set_expected_and_omissions_fail(tmp_path):
    """I1: the model misreads 8 as 7 and omits pincers and tail -- it must not pass."""
    c = FakeClient([_parts(("walking legs", 7, 7, True))])
    r = asyncio.run(J.assess(c, _img(tmp_path), "scorpion: 8 walking legs", expected_parts=SCORPION_PARTS))
    assert r["passed"] is False and r["mismatches"] == 3
    by = {p["part"]: p for p in r["parts"]}
    assert by["walking legs"]["expected"] == 8 and by["pincers"]["seen"] == 0


def test_checklist_parts_match_case_and_plural_insensitively(tmp_path):
    c = FakeClient([_parts(("Walking Legs", 8, 8, True), ("pincer", 2, 2, True), ("Tail", 1, 1, True))])
    r = asyncio.run(J.assess(c, _img(tmp_path), "x", expected_parts=SCORPION_PARTS))
    assert r["passed"] is True
    assert "walking legs" in json.dumps(c.calls[0])        # the exact names are given to the model


def test_zero_reported_parts_fail(tmp_path):
    r = asyncio.run(J.assess(FakeClient([_parts()]), _img(tmp_path), "dog with four legs"))
    assert r["passed"] is False


def test_draft_scores_use_checklist_parts(tmp_path, monkeypatch):
    def fake_render(mesh, out, **k):
        open(out, "wb").write(PNG)
        return {"png": out}
    monkeypatch.setattr(V.vlm_render, "render_mesh_views", fake_render)
    _cell(tmp_path, "B", "scorpion")
    only_legs = _parts(("walking legs", 8, 8, True))
    asyncio.run(V.draft_scores(str(tmp_path), FakeClient([only_legs, only_legs])))
    d = json.load(open(A.cell_dir(str(tmp_path), "B", "scorpion", 1) + "/draft.json"))
    assert d["mesh"]["passed"] is False and d["image"]["passed"] is False


def _unlifted(root, arm, subject, round_=1):
    cell = A.cell_dir(str(root), arm, subject, round_)
    os.makedirs(cell, exist_ok=True)
    open(os.path.join(cell, "concept.png"), "wb").write(PNG)
    json.dump({"arm": arm, "subject": subject, "round": round_}, open(os.path.join(cell, "meta.json"), "w"))
    return cell


def test_unlifted_cell_counts_as_a_mesh_fail(tmp_path):
    """I2: a concept Hunyuan could not lift is a failure of that arm, not a smaller denominator."""
    _cell(tmp_path, "B", "dog")
    _unlifted(tmp_path, "B", "cat")
    t = S.tally({"round": 1, "cells": {"B/dog/r1": {"mesh": "pass", "image": "pass"},
                                       "B/cat/r1": {"mesh": None, "image": "pass"}}}, str(tmp_path))
    assert t["by_arm"]["B"] == {"round": 1, "passed": 1, "scored": 2}
    assert t["unlifted"] == ["B/cat/r1"] and "B/cat/r1" not in t["unscored"]


def test_unlifted_cell_is_on_the_review_page_with_image_toggle_only(tmp_path):
    _unlifted(tmp_path, "C", "dog")
    page = open(V.build_review(str(tmp_path), 1)).read()
    assert "C/dog/r1" in page and 'name="C/dog/r1|image"' in page
    assert 'name="C/dog/r1|mesh"' not in page and "no mesh" in page


def test_draft_scores_skip_unlifted_mesh_but_draft_its_image(tmp_path):
    _unlifted(tmp_path, "B", "dog")
    ok = _parts(("legs", 4, 4, True), ("head", 1, 1, True), ("tail", 1, 1, True))
    assert asyncio.run(V.draft_scores(str(tmp_path), FakeClient([ok]))) == 1
    d = json.load(open(A.cell_dir(str(tmp_path), "B", "dog", 1) + "/draft.json"))
    assert d["mesh"] is None and d["image"]["passed"] is True


def test_cli_score_lists_unlifted(tmp_path, capsys):
    from concept_ab import __main__ as M
    _cell(tmp_path, "photo", "dog")
    _unlifted(tmp_path, "B", "cat")
    json.dump({"round": 1, "cells": {"photo/dog/r1": {"mesh": "pass", "image": "pass"}}},
              open(tmp_path / "scores_r1.json", "w"))
    assert M.main(["--root", str(tmp_path), "score", "--round", "1"]) == 0
    assert "UNLIFTED (counted as mesh fails): B/cat/r1" in capsys.readouterr().out


def test_default_provider_is_the_fixed_lift():
    """I3: the experiment rests on this -- the lift is identical for every arm and round."""
    import mesh_acquire
    p = R.default_provider(22)
    assert p.reuse_concept is True
    assert p.mesh_kwargs == mesh_acquire.HUNYUAN_SHAPE_KWARGS and p.mesh_kwargs["seed"] == 1234
    assert p.prompt_template == mesh_acquire.CONCEPT_PROMPT_TEMPLATE
    assert p.image_kwargs == {**mesh_acquire.FLUX_IMAGE_KWARGS, "seed": 22}
    assert p.mesh_space == mesh_acquire.DEFAULT_HF_MESH_SPACE


def test_judge_is_a_model_that_sees_a_detached_tail():
    """Measured 2026-10-16 on A/scorpion/r1 (tail floating free): claude-sonnet-5
    reported it attached and passed it; claude-opus-5-5 and claude-fable-5-1 failed
    it, and all three passed the photo mesh."""
    assert J.JUDGE_MODEL == "claude-opus-5-5"


# ---- Owner rule 2026-10-18: small floating specks and slivers do not fail a mesh

def test_small_artifacts_do_not_fail(tmp_path):
    payload = _parts(("legs", 4, 4, True), ("head", 1, 1, True), ("tail", 1, 1, True))
    payload["artifacts"] = ["two tiny floating specks above the back"]
    r = asyncio.run(J.assess(FakeClient([payload]), _img(tmp_path), "dog"))
    assert r["passed"] is True and r["artifacts"] == ["two tiny floating specks above the back"]
    assert r["mismatches"] == 0


def test_anatomy_extras_still_fail(tmp_path):
    payload = _parts(("legs", 4, 4, True), ("head", 1, 1, True), extras=["a long rat-like tail"])
    payload["artifacts"] = []
    r = asyncio.run(J.assess(FakeClient([payload]), _img(tmp_path), "guinea pig"))
    assert r["passed"] is False


def test_judge_prompt_states_the_owner_rule():
    s = J.SYSTEM.lower()
    assert "artifacts" in s and "speck" in s and "base or stand" in s


def test_review_page_lists_artifacts_without_failing_and_states_the_rule(tmp_path):
    a = {"parts": [{"part": "legs", "expected": 4, "seen": 4, "attached": True}], "extras": [],
         "artifacts": ["tiny speck by the head"], "passed": True, "mismatches": 0}
    _cell(tmp_path, "B", "dog", draft={"mesh": a, "image": a})
    page = open(V.build_review(str(tmp_path), 1)).read()
    assert "tiny speck by the head" in page
    assert 'name="B/dog/r1|mesh" value="pass" checked' in page
    assert "small floating specks" in page.lower()
