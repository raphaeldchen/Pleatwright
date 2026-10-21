"""River routing: a child hub's pocket beside its parent's flaps (spec
docs/superpowers/specs/2026-10-19-river-routing-design.md).

Every tree is an artifact tree or a named edit of one
(tests/test_pack_chain.py), per the owner rule (CLAUDE.md §5)."""
import hashlib
import itertools
import json
import os

import pytest

from pleatwright import base as B
from pleatwright import efficiency as EF
from pleatwright import nest as NE
from pleatwright import pack as PK
from pleatwright import pipeline as PL
from pleatwright import shape as SH
from pleatwright import stick as ST
from test_pack_chain import antlered, toed

FIX = os.path.join(os.path.dirname(__file__), "..", "fixtures", "full17_v3_sticks")


def _hub_items(roll, symmetric=True):
    """(con, hub, items) of the artifact tree's hub with the most pairs."""
    con = ST.contract(ST.load_roll(os.path.join(FIX, roll + ".json"), 1.0))
    hub = max(con.hubs, key=lambda h: sum(1 for it in PK._items(con, h, True) if not it.axial))
    return con, hub, PK._items(con, hub, symmetric)


@pytest.mark.parametrize("roll", ["dog_0", "bird_1", "cat_1"])
def test_sym_span_rows_tile_the_span_mirror_symmetrically(roll):
    con, hub, items = _hub_items(roll)
    pairs = [it for it in items if not it.axial][:2]
    found = 0
    N = 2 * max(30, 3 * sum(it.L for it in pairs))
    for x0 in range(0, N // 2 - 1):
        for side in ("paper", "hinge"):
            for h in range(1, 2 * max(it.L for it in pairs) + 2):
                for p in (0, 1):
                    for sol in PK._row_concrete_sym_span(pairs, x0, N - x0, side, h,
                                                         "hinge", "hinge", 0, p):
                        found += 1
                        spans = sorted((a, b) for _, a, b, _, _ in sol)
                        assert spans[0][0] == x0 and spans[-1][1] == N - x0
                        assert all(b1 == a2 for (_, b1), (a2, _) in zip(spans, spans[1:]))
                        mirrored = {(N - b, N - a) for a, b in spans}
                        assert mirrored == set(spans)
                        if side == "hinge":
                            lines = {v for e in sol for v in e[4][1][1]}
                            assert x0 in lines and N - x0 in lines
                        regs = PK._row_regions(N, 0, h, sol, "hinge", "hinge")
                        assert all(abs(PK._max_d(r) - r.L) < 1e-9 for r in regs)
    assert found > 0


def test_sym_span_rejects_two_axial_items():
    a = PK.Item((0,), 3, True)
    b = PK.Item((1,), 3, True)
    assert PK._row_concrete_sym_span([a, b], 4, 36, "hinge", 6, "hinge", "hinge", 0, 0) == []


@pytest.mark.parametrize("roll", ["dog_0", "bird_1", "cat_1"])
def test_sym_span_with_an_axial_item_centres_it(roll):
    con, hub, items = _hub_items(roll)
    pairs = [it for it in items if not it.axial][:1]
    axial = [it for it in items if it.axial][:1]
    if not axial:
        axial = [PK.Item((max(c.id for c in con.chains) + 1,), 2, True)]
    row = pairs + axial
    N = 2 * max(30, 3 * sum(it.L for it in row))
    found = 0
    for x0 in range(0, N // 2 - 1):
        for side in ("paper", "hinge"):
            for h in range(1, 2 * max(it.L for it in row) + 2):
                for p in (0, 1):
                    for sol in PK._row_concrete_sym_span(row, x0, N - x0, side, h,
                                                         "hinge", "hinge", 0, p):
                        found += 1
                        spans = sorted((a, b) for _, a, b, _, _ in sol)
                        assert spans[0][0] == x0 and spans[-1][1] == N - x0
                        assert all(b1 == a2 for (_, b1), (a2, _) in zip(spans, spans[1:]))
                        assert {(N - b, N - a) for a, b in spans} == set(spans)
                        ax = [e for e in sol if e[0].axial]
                        assert len(ax) == 1 and ax[0][1] + ax[0][2] == N
                        regs = PK._row_regions(N, 0, h, sol, "hinge", "hinge")
                        assert all(abs(PK._max_d(r) - r.L) < 1e-9 for r in regs)
    assert found > 0


MULTI = ["dog_0", "bird_1", "ant_0", "lizard_1", "crab_1"]


def _con(roll, scale=1.0):
    return ST.contract(ST.load_roll(os.path.join(FIX, roll + ".json"), scale))


def _today_n(roll):
    return {"dog_0": 46, "bird_1": 40, "ant_0": 102, "lizard_1": 64, "crab_1": 50,
            "lizard_2": 44}[roll]


@pytest.mark.parametrize("roll", MULTI)
def test_unmirrored_beside_layouts_tile_and_build(roll):
    con = _con(roll)
    sigma = SH.choose_sigma(ST.load_roll(os.path.join(FIX, roll + ".json"), 1.0), con)
    got = list(itertools.islice(NE.beside_candidates(con, symmetric=False,
                                                     N_max=_today_n(roll) + 20), 5))
    assert got, "some unmirrored beside layout exists within today's N + 20"
    for lay in got:
        assert lay.family == "beside"
        assert not B.build(lay, con, sigma).errors


def test_beside_rivers_bend():
    """Some beside layout of dog_0 has a river band that is an L, U or ring, not a straight band."""
    con = _con("dog_0")
    lay = next(NE.beside_candidates(con, symmetric=False, N_max=66))
    bent = [r for r in lay.regions if r.kind == "river" and r.more and r.vlines]
    assert bent, "a river band with a side arm (a vline), not only top and bottom arms"


def test_beside_off_changes_nothing():
    """nest.candidates (beside off) on the antlered dog: the 2026-10-10 pin."""
    con = ST.contract(ST.load_tree(antlered("dog_0"), 1.0))
    lay = next(NE.candidates(con, symmetric=False, N_max=62))
    assert lay.family == "today" and lay.N == 62


def test_single_hub_tree_has_no_beside_layouts():
    assert next(NE.beside_candidates(_con("octopus_0"), symmetric=False, N_max=40), None) is None


def test_beside_skips_boxes_too_small_for_the_band():
    con = _con("dog_0")
    s = NE._Search(con, 20, False, beside=True)
    river = next(c for c in con.chains if not c.leaf and c.u == con.root)
    flank = (PK._items(con, con.root, False)[0].chains,)
    tiny = NE.Box(0, 0, 2 * river.length, 4, "paper", "hinge", "paper", "paper")
    assert list(s.part(con.root, ("beside", river.id, flank), tiny, False)) == []


def test_beside_candidates_are_deterministic():
    con = _con("dog_0")              # crab_1 until 2026-10-19: 4x the time
    run = lambda: [PK.layout_to_dict(l) for l in itertools.islice(
        NE.beside_candidates(con, symmetric=False, N_max=66), 3)]
    assert run() == run()


def test_family_survives_json_and_defaults_to_today():
    lay = next(NE.beside_candidates(_con("dog_0"), symmetric=False, N_max=66))
    d = PK.layout_to_dict(lay)
    assert PK.layout_from_dict(json.loads(json.dumps(d))).family == "beside"
    d.pop("family")
    assert PK.layout_from_dict(d).family == "today"


#: sha256 over the first 30 nest.candidates layouts (N_max=80, beside off) at
#: afbe447e, before symmetric beside strips; antlered dog_0 has no symmetric
#: nest layout at N <= 80 (its rung is asymmetric), so that pin is the empty hash
BESIDE_OFF_PINS = {
    ("antlered", "dog_0", True): "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    ("antlered", "dog_0", False): "6e31f852034b0be01c1f453a054f9d8bc403bd2f563e07f33b78f9ae03bfc72f",
    ("antlered", "bird_1", True): "a97f580789e463f7c6251dbaf058830e7b0c33dc2a1be9fa213fcd23183bc0bb",
    ("antlered", "bird_1", False): "d4e453ff8602f5f9d31340bf694c5c611d762b69097deb2882a40560379fe034",
    ("toed", "crab_1", True): "9a3e168ed749527324663d9cfa18589dca1b56d65d1ec45a0ac1501e04371a32",
    ("toed", "crab_1", False): "14436d496fb4be97288a3556701045c443227dfb319b346eec644780098b3b1d",
}


def test_beside_off_fingerprints_are_unchanged():
    edits = {"antlered": antlered, "toed": toed}
    got = {}
    for (edit, roll, sym) in BESIDE_OFF_PINS:
        con = ST.contract(ST.load_tree(edits[edit](roll), 1.0))
        h = hashlib.sha256()
        for lay in itertools.islice(NE.candidates(con, symmetric=sym, N_max=80), 30):
            h.update(json.dumps(PK.layout_to_dict(lay), sort_keys=True).encode())
            h.update(b"\n")
        got[(edit, roll, sym)] = h.hexdigest()
    assert got == BESIDE_OFF_PINS


@pytest.mark.parametrize("roll", ["dog_0", "bird_1", "cat_1"])
@pytest.mark.parametrize("top,bot", [("paper", "hinge"), ("hinge", "paper")])
def test_sym_span_rows_against_paper_are_mirror_symmetric(roll, top, bot):
    """A centred child pocket's first or last row touches paper (Task 2 only
    exercised hinge-hinge rows with y_paper 0)."""
    con, hub, items = _hub_items(roll)
    pairs = [it for it in items if not it.axial][:2]
    N = 2 * max(30, 3 * sum(it.L for it in pairs))
    found = 0
    for x0 in range(1, N // 2 - 1):
        for h in range(1, 2 * max(it.L for it in pairs) + 2):
            yp = 0 if top == "paper" else h
            for p in (0, 1):
                for sol in PK._row_concrete_sym_span(pairs, x0, N - x0, "hinge", h,
                                                     top, bot, yp, p):
                    found += 1
                    spans = sorted((a, b) for _, a, b, _, _ in sol)
                    assert spans[0][0] == x0 and spans[-1][1] == N - x0
                    assert {(N - b, N - a) for a, b in spans} == set(spans)
                    regs = PK._row_regions(N, 0, h, sol, top, bot)
                    assert all(abs(PK._max_d(r) - r.L) < 1e-9 for r in regs)
    assert found > 0


def _pair_map(con):
    pm = {}
    for a, b in con.pairs:
        pm[a], pm[b] = b, a
    for _, _, m in PK.hub_pairs(con):
        pm.update(m)
    return pm


def _sig(r):
    return (r.chain, tuple(sorted(r.rects)), tuple(r.vlines), tuple(r.hlines))


#: lizard_1 replaced by lizard_2: lizard_1's root (shoulder) has no mirrored
#: flap pair and its other hub (hip) has no child, so no symmetric beside
#: strip can exist for it
MULTI_SYM = ["dog_0", "bird_1", "ant_0", "lizard_2", "crab_1"]


@pytest.mark.parametrize("roll", MULTI_SYM)
def test_symmetric_beside_layouts_are_their_own_mirror_image(roll):
    """N_max is today's N + 50, not + 20: a centred child pocket has hinges on
    both sides, so each pair member in it is an inner column (2L wide, not L
    against paper); dog_0's first symmetric beside layout is N = 94 and
    bird_1's N = 62."""
    con = _con(roll)
    sigma = SH.choose_sigma(ST.load_roll(os.path.join(FIX, roll + ".json"), 1.0), con)
    pm = _pair_map(con)
    got = list(itertools.islice(NE.beside_candidates(con, symmetric=True,
                                                     N_max=_today_n(roll) + 50), 3))
    assert got
    for lay in got:
        assert lay.family == "beside"
        assert {_sig(NE.mirror(r, lay.N, {r.chain: pm.get(r.chain, r.chain)}))
                for r in lay.regions} == {_sig(r) for r in lay.regions}
        assert not B.build(lay, con, sigma).errors


def test_a_symmetric_beside_river_is_a_u_or_ring():
    """N_max 96, not 66: dog_0's first symmetric beside layout is N = 94."""
    con = _con("dog_0")
    lay = next(NE.beside_candidates(con, symmetric=True, N_max=96))
    bent = [r for r in lay.regions if r.kind == "river" and r.more]
    assert bent and all(len(r.vlines) == 2 for r in bent)   # both side arms


def test_axial_only_hub_has_no_symmetric_beside():
    """Axial flaps never flank (spec 2026-10-19 §4.2).  The positive control: on
    dog_0's whole paper at N = 94 (its first symmetric beside grid) the mirrored
    pair flank yields; the axial flank on the same box yields nothing, and no
    beside part of the root's strip lists holds an axial flap."""
    con = _con("dog_0")
    s = NE._Search(con, 94, True, beside=True)
    river = next(c for c in con.chains if not c.leaf and c.u == con.root)
    items = PK._items(con, con.root, True)
    axial = next(it for it in items if it.axial)       # dog_0's root has one
    pair = next(it for it in items if not it.axial)
    box = NE.Box(0, 0, 94, 94, "paper", "paper", "paper", "paper")
    assert list(itertools.islice(s.part(con.root, ("beside", river.id, (pair.chains,)),
                                        box, True), 1))
    assert list(s.part(con.root, ("beside", river.id, (axial.chains,)), box, True)) == []
    besides = [p for lst in s.part_lists(con.root, True) for p in lst if p[0] == "beside"]
    assert besides
    axials = {it.chains for it in items if it.axial}
    assert not any(ch in axials for p in besides for ch in p[2])


def test_ant_0_symmetric_beside_beats_todays_symmetric_grid():
    """ant_0's symmetric grid is 102 today (2026-10-06); a centred beside strip
    packs it on a smaller one."""
    lay = next(NE.beside_candidates(_con("ant_0"), symmetric=True, N_max=_today_n("ant_0")))
    assert lay.N < _today_n("ant_0")


# ------------------------------------------------- pack_options (Task 5)
@pytest.mark.parametrize("roll", ["dolphin_0", "bird_1", "starfish_0"])
def test_beside_off_is_todays_pack_options(roll):
    off = PL.pack_options(roll, beside=False).summary()
    assert off["beside"] == {"symmetric": "off", "smaller": "off"}
    off.pop("beside")
    for k in ("symmetric", "smaller"):
        if off[k]:
            assert off[k].pop("family") == "today"
    # today's slice-1 expectations still hold
    assert {"dolphin_0": ("ask", 50), "bird_1": ("symmetric", 40),
            "starfish_0": ("only_unmirrored", None)}[roll] == \
        (off["verdict"], off["symmetric"] and off["symmetric"]["grid"])


def _chosen_grid(o):
    opt, _ = PL._choose(o, "auto", "flag")
    return opt.layout.N


@pytest.mark.parametrize("roll", ["dog_0", "bird_1", "lizard_1", "crab_1"])
def test_beside_never_grows_the_chosen_grid(roll):
    today, new = PL.pack_options(roll, beside=False), PL.pack_options(roll, beside=True)
    assert _chosen_grid(new) <= _chosen_grid(today)
    for k in ("symmetric", "smaller"):
        v = new.beside[k]
        assert isinstance(v, str) or v <= _chosen_grid(today) - 2


def test_single_hub_tree_skips_beside():
    o = PL.pack_options("octopus_0", beside=True)
    assert o.beside == {"symmetric": "no_child_hub", "smaller": "no_child_hub"}


def test_beside_budget_exhaustion_keeps_today(monkeypatch):
    monkeypatch.setattr(PL, "BESIDE_WORK_BUDGET", 1)
    today = PL.pack_options("dog_0", beside=False)
    o = PL.pack_options("dog_0", beside=True)
    assert o.beside == {"symmetric": "budget", "smaller": "budget"}
    assert _chosen_grid(o) == _chosen_grid(today)


def test_pre_slice_options_json_loads(tmp_path):
    o = PL.pack_options("dolphin_0", beside=False)
    PL.save_options(o, str(tmp_path))
    p = tmp_path / "options.json"
    doc = json.loads(p.read_text())
    for d in doc["options"].values():
        d.pop("family")
        d["layout"].pop("family")
    doc["summary"].pop("beside")
    p.write_text(json.dumps(doc))
    r = PL.load_options("dolphin_0", str(tmp_path))
    assert r.symmetric.family == "today" and r.beside == {}



def _todays_family_as_beside(con, *, symmetric, N_max, **kw):
    """A stand-in for nest.beside_candidates: today's candidates, tagged beside
    (it exercises how pack_options combines a found beside option)."""
    for lay in PK.candidates(con, symmetric=symmetric, N_max=N_max):
        lay.family = "beside"
        yield lay


def test_a_beside_unmirrored_option_that_loses_the_rule_keeps_todays_choice(monkeypatch):
    """bird_1: today symmetric 40, no unmirrored below the cap 36.  An
    unmirrored layout on 38 (= C - 2) is 40/38 < 1.10 smaller: the rule keeps
    the symmetric 40, and n_smaller records the 38 (spec 2026-10-19 §5.2)."""
    monkeypatch.setattr(PL.NE, "beside_candidates", _todays_family_as_beside)
    o = PL.pack_options("bird_1", beside=True)
    assert o.beside["smaller"] == 38 and isinstance(o.beside["symmetric"], str)
    assert (o.verdict, o.n_smaller, o.smaller.family, o.smaller.rung) == \
        ("symmetric", 38, "beside", "asymmetric")
    opt, _ = PL._choose(o, "auto", "flag")
    assert (opt.layout.N, opt.family) == (40, "today")
    assert o.summary()["smaller"]["family"] == "beside"


def test_beside_build_cap_is_recorded(monkeypatch):
    monkeypatch.setattr(PL.NE, "beside_candidates", _todays_family_as_beside)
    monkeypatch.setattr(PL, "BESIDE_MAX_BUILDS", 2)
    real = PL.B.build
    calls = []

    def build(lay, con, sigma):
        b = real(lay, con, sigma)
        if lay.family == "beside":
            calls.append(lay.N)
            b.errors = b.errors or ["forced"]
        return b

    monkeypatch.setattr(PL.B, "build", build)
    o = PL.pack_options("bird_1", beside=True)
    # bird_1 has fewer than 2 symmetric candidates below 38, so only the
    # unmirrored search reaches the cap
    assert o.beside == {"symmetric": "none_below_cap", "smaller": "builds"}
    assert calls and all(n <= 38 for n in calls)
    assert (o.verdict, o.symmetric.layout.N, o.smaller) == ("symmetric", 40, None)

# ---------------------------------------------------- river_corners (Task 5b)
def _first_symmetric_layout(roll):
    """The layout and base the pipeline's first rung accepts
    (test_layout_choice._first_symmetric)."""
    con = _con(roll)
    sigma = SH.choose_sigma(ST.load_roll(os.path.join(FIX, roll + ".json"), 1.0), con)
    G = PK.grid_init(con)
    for lay in PK.candidates(con, symmetric=True, N_max=max(2 * G, G + 60)):
        base = B.build(lay, con, sigma)
        if not base.errors:
            return con, lay, base
    raise AssertionError("no symmetric layout")


def test_river_corners_counts_only_interior_bends():
    straight = PK.Region(0, (0, 10, 62, 12), [], [10], "river", 2)
    reg, _ = NE.band(7, 2, NE.Box(0, 0, 31, 5, "paper", "hinge", "paper", "hinge"))
    ring, _ = NE.band(8, 2, NE.Box(10, 10, 30, 30, "hinge", "hinge", "hinge", "hinge"))
    mk = lambda rs: PK.Layout(62, rs, [], [], [])
    assert EF.river_corners(mk([straight])) == 0
    assert EF.river_corners(mk([reg])) == 2          # L: outer (31,5) and inner (29,3)
    assert EF.river_corners(mk([ring])) == 8


def test_metrics_carry_river_corners():
    con, lay, base = _first_symmetric_layout("dolphin_0")
    assert EF.metrics(lay, con, base, 1.0)["river_corners"] == 0


# ---- calibration (docs/superpowers/evidence/2026-10-19-river-routing/README.md)
# scorpion_2 is the budget anchor: its unmirrored beside search is the most
# expensive WINNING one (9,022,945 ticks, one build), so the budget is those
# ticks plus 3%.  Ticks are deterministic, so it always fits.
@pytest.fixture(scope="module")
def scorpion_2_beside():
    return PL.pack_options("scorpion_2", beside=True)


def test_scorpion_2_fits_the_beside_budget(scorpion_2_beside):
    o = scorpion_2_beside            # Phase 0: S_b 82 (2.85M ticks), U_b 64 (9.02M ticks)
    assert o.beside == {"symmetric": 82, "smaller": 64}
    assert (o.verdict, o.symmetric.layout.N, o.smaller.layout.N) == ("ask", 82, 64)
    assert (o.smaller.family, _chosen_grid(o)) == ("beside", 64)      # today: 86


def test_beside_ticks_are_deterministic(elephant_1_beside):
    """Two pack_options calls give the same summary.  elephant_1 (both beside
    searches find a layout, 8 s) instead of a second 95 s scorpion_2 call."""
    again = PL.pack_options("elephant_1", beside=True)
    assert again.summary() == elephant_1_beside.summary()


# ------------------------------------------- switched on (Task 8, spec §8)
# Phase 0 grids: docs/superpowers/evidence/2026-10-19-river-routing/phase0.jsonl.
def test_beside_is_on_by_default():
    assert PL.BESIDE is True


def test_bat_3_folds_on_a_smaller_beside_grid(tmp_path):
    """bat_3: today symmetric 44 (baseline CERTIFIED, 7.5 s); Phase 0 U_b 40,
    44/40 = 1.10, so the rule picks the beside layout."""
    rec = PL.run("bat_3", str(tmp_path), certify_global=True, verbose=False)
    assert rec["layout"]["family"] == "beside" and rec["layout"]["chosen"] == "smaller"
    assert rec["layout"]["beside"] == {"symmetric": "none_below_cap", "smaller": 40}
    assert rec["grid_size"] == 40 and rec["folder"].endswith("_40")
    assert rec["global_verdict"] == "CERTIFIED"
    ff = rec["solving_flat_foldable"]
    assert ff[0] == ff[1]
    ff = rec["shaping_flat_foldable"]
    assert ff[0] == ff[1]


@pytest.fixture(scope="module")
def elephant_1_beside():
    return PL.pack_options("elephant_1")


def test_elephant_1_symmetric_beside_replaces_todays_symmetric(elephant_1_beside):
    """elephant_1: today symmetric 72, nothing unmirrored below the cap.
    Phase 0: S_b 64 and U_b 64, so S' = S_b and 64/64 < 1.10 keeps it."""
    o = elephant_1_beside
    assert o.beside == {"symmetric": 64, "smaller": 64}
    assert (o.symmetric.family, o.symmetric.layout.N, o.symmetric.rung) == \
        ("beside", 64, "symmetric")
    assert o.verdict == "symmetric"
    opt, reason = PL._choose(o, "auto", "flag")
    assert opt is o.symmetric and reason == "rule"
    # what `run` folds if the beside layout fails downstream: today's choice
    assert [(f.name, f.layout.N, f.family) for f in o.today_fallback] == \
        [("symmetric", 72, "today")]


@pytest.fixture(scope="module")
def bat_3_beside():
    return PL.pack_options("bat_3")


def _solve_fails_at(monkeypatch, *grids):
    real = PL.SV.solve

    def solve(base, **kw):
        if base.layout.N in grids:
            raise RuntimeError(f"boom {base.layout.N}")
        return real(base, **kw)

    monkeypatch.setattr(PL.SV, "solve", solve)


def test_a_failed_beside_smaller_layout_folds_todays_choice(tmp_path, monkeypatch,
                                                            bat_3_beside):
    """§5.2a with river routing (Ruling 11): the beside layout bat_3's rule
    picks (40) fails in solving; the fold lands on today's grid, 44."""
    _solve_fails_at(monkeypatch, 40)
    rec = PL.run("bat_3", str(tmp_path), certify_global=False, verbose=False,
                 options=bat_3_beside)
    assert rec["grid_size"] == 44 and rec["packing_rung"] == "symmetric"
    lay = rec["layout"]
    assert (lay["reason"], lay["chosen"], lay["family"]) == ("fallback", "symmetric", "today")
    assert lay["fallback_error"] == "RuntimeError: boom 40" and "fallback_errors" not in lay
    assert not [d for d in os.listdir(tmp_path) if d.endswith("_40")]


def test_a_failed_symmetric_beside_layout_folds_todays_choice(tmp_path, monkeypatch,
                                                            elephant_1_beside):
    """The beside winner is the symmetric option S' (elephant_1, 64).  Today's
    rule has no fallback for a symmetric choice; a beside one falls back to
    today's choice (symmetric 72), never to a grid above today's."""
    _solve_fails_at(monkeypatch, 64)
    rec = PL.run("elephant_1", str(tmp_path), certify_global=False, verbose=False,
                 options=elephant_1_beside)
    assert rec["grid_size"] == 72
    lay = rec["layout"]
    assert (lay["reason"], lay["chosen"], lay["family"]) == ("fallback", "symmetric", "today")
    assert lay["fallback_error"] == "RuntimeError: boom 64"
    assert not [d for d in os.listdir(tmp_path) if d.endswith("_64")]


def test_the_fallback_chain_is_todays_choice_then_todays_symmetric(tmp_path, monkeypatch):
    """elephant_0: today asks (S 80, U 72 = 1.11) and folds U 72; Phase 0 S_b 64
    and U_b 64, so the rule now picks S_b 64.  If 64 fails, today's 72; if
    that fails too, today's own fallback, the symmetric 80."""
    o = PL.pack_options("elephant_0")
    assert (o.verdict, o.symmetric.family, o.symmetric.layout.N) == ("symmetric", "beside", 64)
    assert [(f.name, f.layout.N, f.family) for f in o.today_fallback] == \
        [("smaller", 72, "today"), ("symmetric", 80, "today")]
    folded = []

    def fold(rec, opts, opt, out_dir, _stage, *a):
        folded.append(opt.layout.N)
        rec["grid_size"] = opt.layout.N
        _stage[0] = "solving"
        if opt.layout.N != 80:
            raise RuntimeError(f"boom {opt.layout.N}")

    monkeypatch.setattr(PL, "_fold_option", fold)
    rec = PL.run("elephant_0", str(tmp_path), verbose=False, options=o)
    assert folded == [64, 72, 80] and rec["grid_size"] == 80
    assert (rec["layout"]["reason"], rec["layout"]["chosen"]) == ("fallback", "symmetric")
    assert rec["layout"]["fallback_error"] == "RuntimeError: boom 64"
    assert rec["layout"]["fallback_errors"] == ["RuntimeError: boom 64", "RuntimeError: boom 72"]


def test_the_last_fallback_failure_is_raised(tmp_path, monkeypatch, bat_3_beside):
    _solve_fails_at(monkeypatch, 40, 44)
    with pytest.raises(PL.StageError) as e:
        PL.run("bat_3", str(tmp_path), certify_global=False, verbose=False,
               options=bat_3_beside)
    assert e.value.stage == "solving" and "boom 44" in str(e.value)


def test_an_explicit_beside_choice_is_not_masked(tmp_path, monkeypatch, bat_3_beside):
    _solve_fails_at(monkeypatch, 40)
    with pytest.raises(PL.StageError) as e:
        PL.run("bat_3", str(tmp_path), certify_global=False, verbose=False,
               layout="smaller", chosen_by="user", options=bat_3_beside)
    assert e.value.stage == "solving"


def test_todays_fallback_survives_saved_options(tmp_path, monkeypatch, bat_3_beside):
    """The app folds "auto" from options.json (`load_options`); today's
    fallback must come back with it."""
    o = bat_3_beside
    PL.save_options(o, str(tmp_path / "layout"))
    r = PL.load_options("bat_3", str(tmp_path / "layout"))
    assert [(f.name, f.layout.N, f.family) for f in r.today_fallback] == \
        [("symmetric", 44, "today")]
    assert r.today_fallback[0].base.creases == o.today_fallback[0].base.creases
    _solve_fails_at(monkeypatch, 40)
    rec = PL.run("bat_3", str(tmp_path), certify_global=False, verbose=False, options=r)
    assert rec["grid_size"] == 44 and rec["layout"]["reason"] == "fallback"


def test_todays_fallback_is_not_saved_when_today_is_chosen(tmp_path):
    PL.save_options(PL.pack_options("dolphin_0"), str(tmp_path))
    assert "today_fallback" not in json.loads((tmp_path / "options.json").read_text())


def test_toed_crab_3_packs_past_todays_grid_cap(tmp_path, monkeypatch):
    """toed crab_3 packs nothing today below the cap max(2G, G + 60) = 106
    (`test_nest`); both beside searches then run up to that cap (spec §5.2),
    and the symmetric one finds 90."""
    tree = tmp_path / "tree.json"
    tree.write_text(json.dumps(toed("crab_3")))
    # the symmetric beside search reaches 90 after 4,382,560 ticks (measured
    # 2026-10-19); a budget just above it keeps both outcomes of the
    # calibrated 9.3M (the unmirrored search still spends it) in 85 s, not 122
    monkeypatch.setattr(PL, "BESIDE_WORK_BUDGET", 4_400_000)
    o = PL.pack_options(str(tree))
    assert o.beside == {"symmetric": 90, "smaller": "budget"}
    assert (o.verdict, o.symmetric.family, o.symmetric.layout.N, o.smaller) == \
        ("symmetric", "beside", 90, None)
    assert o.today_fallback == []           # today has no choice to fall back to


def _symmetric_beside_above_the_cap(con, *, symmetric, N_max, **kw):
    """A stand-in for nest.beside_candidates: today's symmetric candidates up
    to the full grid cap, tagged beside; no unmirrored ones."""
    if symmetric:
        yield from _todays_family_as_beside(con, symmetric=True, N_max=200)


def test_todays_smaller_choice_falls_back_past_a_beside_symmetric(tmp_path, monkeypatch):
    """dolphin_0 asks (S 50, U 32) and folds U 32.  With a beside S' (here a
    stand-in on 50), today's rule falls back to S'; if S' fails too, the
    chain ends on today's own symmetric layout, as today would fold."""
    monkeypatch.setattr(PL.NE, "beside_candidates", _symmetric_beside_above_the_cap)
    o = PL.pack_options("dolphin_0")
    assert (o.verdict, o.symmetric.family, o.smaller.family) == ("ask", "beside", "today")
    assert [(f.name, f.layout.N, f.family) for f in o.today_fallback] == \
        [("symmetric", 50, "today")]
    chosen, _ = PL._choose(o, "auto", "flag")
    assert [(f.family, f.layout.N) for f in PL._fallbacks(o, chosen)] == \
        [("beside", 50), ("today", 50)]
    folded = []

    def fold(rec, opts, opt, out_dir, _stage, *a):
        folded.append((opt.family, opt.layout.N))
        _stage[0] = "shaping"
        if folded[-1] != ("today", 50):
            raise RuntimeError(f"boom {folded[-1]}")

    monkeypatch.setattr(PL, "_fold_option", fold)
    rec = PL.run("dolphin_0", str(tmp_path), verbose=False, options=o)
    assert folded == [("today", 32), ("beside", 50), ("today", 50)]
    assert (rec["layout"]["reason"], rec["layout"]["family"]) == ("fallback", "today")
    assert len(rec["layout"]["fallback_errors"]) == 2


def test_todays_smaller_choice_with_todays_symmetric_folds_it_once(tmp_path, monkeypatch):
    """No beside S': the chain is today's, the symmetric layout once."""
    o = PL.pack_options("dolphin_0")
    chosen, _ = PL._choose(o, "auto", "flag")
    assert o.today_fallback == []
    assert [(f.family, f.layout.N) for f in PL._fallbacks(o, chosen)] == [("today", 50)]


def test_beside_search_error_keeps_todays_options(monkeypatch):
    """Anti-goal: a beside search that raises (a BaseError from base.build, a
    bug in the nest code on an unusual tree) ends only that search; today's
    options are kept."""
    def boom(*a, **k):
        raise RuntimeError("beside search blew up")
    monkeypatch.setattr(PL, "_search_beside", boom)
    o = PL.pack_options("dog_0", beside=True)
    assert o.beside == {"symmetric": "error", "smaller": "error"}
    assert _chosen_grid(o) == _chosen_grid(PL.pack_options("dog_0", beside=False))
