"""Packing layout choice (spec docs/superpowers/specs/2026-10-16-packing-layout-choice-design.md).

Every tree is one of the 51 artifact trees (CLAUDE.md §5)."""
import json
import os

import pytest

from pleatwright import base as B
from pleatwright import efficiency as EF
from pleatwright import pack as PK
from pleatwright import shape as SH
from pleatwright import stick as ST

FIX = os.path.join(os.path.dirname(__file__), "..", "fixtures", "full17_v3_sticks")


def _con(roll):
    return ST.contract(ST.load_roll(os.path.join(FIX, f"{roll}.json"), 1.0))


def test_budget_one_tick_exhausts_on_the_unmirrored_dolphin():
    con = _con("dolphin_0")
    with pytest.raises(PK.BudgetExhausted):
        with PK.work_budget(1):
            next(PK.candidates(con, symmetric=False, N_max=45))


def test_no_budget_changes_nothing():
    con = _con("dolphin_0")
    a = next(PK.candidates(con, symmetric=True, N_max=64))
    with PK.work_budget(None):
        b = next(PK.candidates(con, symmetric=True, N_max=64))
    assert (a.N, [r.rect for r in a.regions]) == (b.N, [r.rect for r in b.regions]) and a.N == 50


def test_ticks_are_deterministic():
    con = _con("dolphin_0")
    used = []
    for _ in range(2):
        with PK.work_budget(10**9):
            next(PK.candidates(con, symmetric=False, N_max=45))
            used.append(PK.work_used())
    assert used[0] == used[1] > 0


def _sigma(roll, con):
    return SH.choose_sigma(ST.load_roll(os.path.join(FIX, f"{roll}.json"), 1.0), con)


def _first_symmetric(roll):
    """The layout and base the pipeline's first rung accepts."""
    con = _con(roll)
    sigma = _sigma(roll, con)
    G = PK.grid_init(con)
    for lay in PK.candidates(con, symmetric=True, N_max=max(2 * G, G + 60)):
        base = B.build(lay, con, sigma)
        if not base.errors:
            return con, lay, base
    raise AssertionError("no symmetric layout")


@pytest.mark.parametrize("symmetric", [True, False])
def test_layout_round_trips_through_json(symmetric):
    con = _con("dolphin_0")
    sigma = _sigma("dolphin_0", con)
    G = PK.grid_init(con)
    lay = next(PK.candidates(con, symmetric=symmetric, N_max=max(2 * G, G + 60)))
    lay2 = PK.layout_from_dict(json.loads(json.dumps(PK.layout_to_dict(lay))))
    assert lay2.N == lay.N
    assert all(isinstance(r.rect, tuple) and all(isinstance(m, tuple) for m in r.more)
               for r in lay2.regions)
    assert B.build(lay2, con, sigma).creases == B.build(lay, con, sigma).creases


def test_nested_layout_round_trips_pockets():
    lay = PK.Layout(8, [PK.Region(0, (0, 0, 4, 4), [4], [4], "river", 4, more=[(4, 0, 8, 4)])],
                    ["a"], [(0, 1, 2)], [("a", 0, 8)],
                    pockets=[("a", (0, 0, 8, 8), ("paper", "hinge", "paper", "paper"))])
    lay2 = PK.layout_from_dict(json.loads(json.dumps(PK.layout_to_dict(lay))))
    assert lay2 == lay


@pytest.mark.parametrize("roll,N,pb,slack,layers,exp_max,exp_med,creases", [
    ("dolphin_0", 50, 29, 0.5916, 43.27, 5.556, 2.5, 2656),
    ("bird_1",    40, 32, 0.2887, 23.27, 3.0, 1.4185, 1768),
])
def test_metrics_match_the_baseline_probe(roll, N, pb, slack, layers, exp_max, exp_med, creases):
    con, lay, base = _first_symmetric(roll)
    m = EF.metrics(lay, con, base, 1.0)
    assert (m["grid"], m["perimeter_bound"], m["creases"]) == (N, pb, creases)
    assert m["grid_init"] == PK.grid_init(con)
    assert m["n_over_bound"] == pytest.approx(N / pb, abs=1e-4)
    assert m["slack_fraction"] == pytest.approx(slack, abs=1e-4)
    assert m["mean_layers"] == pytest.approx(layers, abs=0.01)
    assert m["flap_expansion_max"] == pytest.approx(exp_max, abs=1e-3)
    assert m["flap_expansion_median"] == pytest.approx(exp_med, abs=1e-3)
    assert m["scale"] == pytest.approx(1 / N)
    json.dumps(m)


# ---------------------------------------------------------------- pack_options
from fractions import Fraction  # noqa: E402

from pleatwright import pipeline as PL  # noqa: E402


def test_dolphin_asks():
    o = PL.pack_options("dolphin_0")
    assert (o.verdict, o.symmetric.layout.N, o.smaller.layout.N) == ("ask", 50, 32)
    assert o.gain == Fraction(50, 32) and o.recommended == "smaller"


def test_bird_keeps_symmetry_without_asking():
    o = PL.pack_options("bird_1")          # unmirrored 38 > cap 36
    assert (o.verdict, o.n_smaller, o.smaller) == ("symmetric", "none_below_cap", None)


def test_lizard_2_sits_exactly_on_the_threshold():
    o = PL.pack_options("lizard_2")        # 44 / 40 == 1.10
    assert o.verdict == "ask"


def test_starfish_has_only_the_unmirrored_layout():
    o = PL.pack_options("starfish_0")
    assert (o.verdict, o.symmetric, o.smaller.layout.N) == ("only_unmirrored", None, 44)


def test_budget_exhaustion_is_recorded():
    o = PL.pack_options("dolphin_0", work_budget=1, beside=False)
    assert (o.verdict, o.n_smaller) == ("symmetric", "budget")
    # river routing (spec 2026-10-19 §5.2): `work_budget` bounds today's
    # unmirrored search only; today then folds 50, so the beside unmirrored
    # search (its own budget, cap 48) finds the 32 today's search ran out on
    o = PL.pack_options("dolphin_0", work_budget=1)
    assert (o.verdict, o.n_smaller, o.smaller.family) == ("ask", 32, "beside")


def test_saved_options_reload_without_searching(tmp_path, monkeypatch):
    o = PL.pack_options("dolphin_0")
    paths = PL.save_options(o, str(tmp_path))
    assert sorted(os.path.basename(p) for p in paths) == [
        "options.json", "smaller_packing_cp.svg", "symmetric_packing_cp.svg"]
    monkeypatch.setattr(PL.PK, "candidates", lambda *a, **k: pytest.fail("searched"))
    r = PL.load_options("dolphin_0", str(tmp_path))
    assert r.summary() == o.summary() and r.smaller.base.creases == o.smaller.base.creases
    assert r.tried == o.tried


# The two tests below each take minutes: they search the unmirrored layout up
# to the full SMALLER_WORK_BUDGET (calibration: docs/superpowers/evidence/
# 2026-10-16-layout-choice/README.md).
def test_octopus_2_fits_the_budget():
    o = PL.pack_options("octopus_2")       # unmirrored 60 within cap 60, 3,395,895 ticks
    assert (o.verdict, o.smaller.layout.N) == ("ask", 60)


def test_scorpion_0_stops_within_the_budget():
    o = PL.pack_options("scorpion_0")
    assert o.n_smaller == "budget"


# ------------------------------------------------------------------- run
from pleatwright import pipeline as _PL  # noqa: E402


def _fold(roll, tmp_path, **kw):
    return PL.run(roll, str(tmp_path), certify_global=False, verbose=False, **kw)


def test_auto_takes_the_smaller_dolphin(tmp_path):
    rec = _fold("dolphin_0", tmp_path)
    assert rec["grid_size"] == 32 and rec["layout"]["reason"] == "rule"
    assert rec["layout"]["chosen"] == "smaller" and rec["packing_rung"] == "asymmetric"
    assert rec["folder"].endswith("_32") and rec["efficiency"]["grid"] == 32


def test_flag_keeps_the_symmetric_dolphin(tmp_path):
    rec = _fold("dolphin_0", tmp_path, layout="symmetric")
    assert rec["grid_size"] == 50 and rec["layout"]["reason"] == "flag"


def test_auto_bird_keeps_the_old_layout(tmp_path):
    rec = _fold("bird_1", tmp_path)
    assert rec["grid_size"] == 40 and rec["packing_rung"] == "symmetric"
    assert rec["layout"] == {"chosen": "symmetric", "reason": "rule", "n_symmetric": 40,
                             "n_smaller": "none_below_cap", "gain": None, "threshold": 1.1,
                             # river routing (spec 2026-10-19 §7): no beside layout
                             # below 38 (Phase 0)
                             "family": "today", "beside": {"symmetric": "none_below_cap",
                                                           "smaller": "none_below_cap"}}


def test_starfish_only_option(tmp_path):
    rec = _fold("starfish_0", tmp_path)
    assert rec["grid_size"] == 44 and rec["layout"]["reason"] == "only_option"


def test_failed_smaller_falls_back_to_symmetric(tmp_path, monkeypatch):
    real = PL.SV.solve

    def solve(base, **kw):
        if base.layout.N == 32:
            raise RuntimeError("boom")
        return real(base, **kw)

    monkeypatch.setattr(PL.SV, "solve", solve)
    rec = _fold("dolphin_0", tmp_path)
    assert rec["grid_size"] == 50
    assert rec["layout"]["reason"] == "fallback" and rec["layout"]["chosen"] == "symmetric"
    assert rec["layout"]["fallback_error"] == "RuntimeError: boom"
    assert not [d for d in os.listdir(tmp_path) if d.endswith("_32")]


def test_explicit_smaller_failure_is_not_masked(tmp_path, monkeypatch):
    def solve(base, **kw):
        raise RuntimeError("boom")

    monkeypatch.setattr(PL.SV, "solve", solve)
    with pytest.raises(PL.StageError) as e:
        _fold("dolphin_0", tmp_path, layout="smaller")
    assert e.value.stage == "solving"


def test_missing_requested_layout_falls_back_to_the_existing_one(tmp_path):
    rec = _fold("bird_1", tmp_path, layout="smaller")
    assert rec["grid_size"] == 40 and rec["layout"]["reason"] == "only_option"


def test_precomputed_options_are_used(tmp_path, monkeypatch):
    opts = PL.pack_options("dolphin_0")
    monkeypatch.setattr(PL.PK, "candidates", lambda *a, **k: pytest.fail("searched"))
    rec = _fold("dolphin_0", tmp_path, options=opts, layout="symmetric", chosen_by="user")
    assert rec["grid_size"] == 50 and rec["layout"]["reason"] == "user"


def _solve_fails_at_32(monkeypatch):
    real = PL.SV.solve

    def solve(base, **kw):
        if base.layout.N == 32:
            raise RuntimeError("boom")
        return real(base, **kw)

    monkeypatch.setattr(PL.SV, "solve", solve)


def test_fallback_replays_stage_events_ending_in_the_symmetric_folder(tmp_path, monkeypatch):
    _solve_fails_at_32(monkeypatch)
    events = []
    rec = _fold("dolphin_0", tmp_path, on_stage=lambda s, i: events.append((s, i)))
    assert [s for s, _ in events] == ["packing", "packing", "solving", "shaping", "output"]
    last_packing = [i for s, i in events if s == "packing"][-1]
    assert last_packing["folder"].endswith("_50") and rec["folder"].endswith("_50")
    assert all("_50" in f for f in last_packing["files"])


def test_on_stage_error_on_the_auto_smaller_fold_is_not_a_fallback(tmp_path):
    seen = []

    def hook(stage, info):
        seen.append(stage)
        if stage == "solving":
            raise RuntimeError("hook")

    with pytest.raises(PL.StageError) as e:
        _fold("dolphin_0", tmp_path, on_stage=hook)
    assert e.value.stage == "solving" and seen == ["packing", "solving"]


def test_invalid_layout_is_a_plain_value_error(tmp_path):
    with pytest.raises(ValueError):
        _fold("bird_1", tmp_path, layout="bogus")
