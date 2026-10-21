"""Pleatwright's nested packer for branching hub graphs (spec
docs/superpowers/specs/2026-10-10-branching-hub-packer-design.md).

Every tree is an artifact tree or a named edit of one
(tests/test_pack_chain.py), per the owner rule (CLAUDE.md §5)."""
import dataclasses
import json
import os

import pytest

from artifact_trees import artifact_tree
from pleatwright import base as B
from pleatwright import nest as NE
from pleatwright import pack as PK
from pleatwright import pipeline as PL
from pleatwright import shape as SH
from pleatwright import stick as ST
from test_pack_chain import _toe, antlered, lopsided, odd_antlers, toed

#: pipeline._run's packing ladder: (rung, scale, symmetric)
LADDER = (("symmetric", 1.0, True), ("asymmetric", 1.0, False), ("symmetric x2", 2.0, True))


def _first_certified(tree, max_candidates=400):
    """The pipeline's packing ladder on an in-memory tree: the first layout
    base.build certifies, as (rung, layout, contracted tree, base), or None."""
    tried = 0
    for rung, scale, symmetric in LADDER:
        sf = ST.load_tree(tree, scale)
        con = ST.contract(sf)
        sigma = SH.choose_sigma(sf, con)
        n_max = max(2 * PK.grid_init(con), PK.grid_init(con) + 60)
        for lay in PK.candidates(con, symmetric=symmetric, N_max=n_max):
            tried += 1
            b = B.build(lay, con, sigma)
            if not b.errors:
                return rung, lay, con, b
            if tried >= max_candidates:
                return None
    return None


def test_region_rects_default_to_its_one_rectangle():
    assert PK.Region(0, (0, 0, 2, 2), [], [], "flap", 1).rects == [(0, 0, 2, 2)]
    assert PK.Layout(4, [], [], [], []).pockets == []


def test_a_region_of_several_rectangles_builds_like_one_rectangle():
    """A nested river band is ONE Region of several rectangles (spec §1):
    base.build must own every rectangle's cells and draw no hinge where two
    rectangles of one region meet. Splitting a certified river in two must
    change nothing."""
    _, lay, con, base = _first_certified(artifact_tree("dog_0"))
    i, r = next((i, r) for i, r in enumerate(lay.regions) if r.kind == "river")
    x0, y0, x1, y1 = r.rect
    xm = (x0 + x1) // 2
    split = dataclasses.replace(r, rect=(x0, y0, xm, y1), more=[(xm, y0, x1, y1)])
    lay2 = dataclasses.replace(lay, regions=lay.regions[:i] + [split] + lay.regions[i + 1:])
    b2 = B.build(lay2, con, base.sigma)
    assert b2.errors == []
    assert b2.boundary_edges == base.boundary_edges
    assert {k: v["kind"] for k, v in b2.creases.items()} == \
        {k: v["kind"] for k, v in base.creases.items()}


def _antler_items():
    """antler_L's two flaps (beam, palm: length 3), unmirrored, as nest packs them."""
    con = ST.contract(ST.load_tree(antlered("dog_0"), 1.0))
    return PK._items(con, "antler_L", False)


def test_span_rows_tile_an_off_axis_pocket_with_its_hinge_side_on_a_hinge_line():
    """The antler_L pocket of the certified antlered dog: [0, 29] x [0, 3], paper
    on top and left, hinge (its river band) on the bottom and right."""
    items = _antler_items()
    sols = PK._row_concrete_span(items, 0, 29, "paper", "hinge", 3, "paper", "hinge", 0, 1,
                                 limit=50)
    assert sols
    for sol in sols:
        spans = [(s[1], s[2]) for s in sol]
        assert spans[0][0] == 0 and spans[-1][1] == 29
        assert all(a[1] == b[0] for a, b in zip(spans, spans[1:]))
        regs = PK._row_regions(62, 0, 3, sol, "paper", "hinge")
        assert all(abs(PK._max_d(r) - r.L) < 1e-9 and PK._parity_ok(r) for r in regs)
        assert 29 in max(regs, key=lambda r: r.rect[2]).vlines
        assert max(v for r in regs for v in r.vlines) <= 29      # nothing past the hinge side


def test_span_rows_put_a_left_hinge_on_its_line_and_respect_parity():
    items = _antler_items()
    sols = PK._row_concrete_span(items, 33, 62, "hinge", "paper", 3, "paper", "hinge", 0, 1,
                                 limit=50)
    assert sols
    for sol in sols:
        regs = PK._row_regions(62, 0, 3, sol, "paper", "hinge")
        assert 33 in min(regs, key=lambda r: r.rect[0]).vlines
        assert min(v for r in regs for v in r.vlines) >= 33
    # a hinge side off the row's parity class can carry no ridge corner
    assert PK._row_concrete_span(items, 0, 29, "paper", "hinge", 3, "paper", "hinge", 0, 0) == []


def test_pocket_solutions_take_an_injected_row_builder():
    items = _antler_items()

    def rowfn(its, hw, h, t, b, yp, p, limit=6):
        return PK._row_concrete_span(its, 0, 29, "paper", "hinge", h, t, b, yp, p, limit)
    rows = next(PK._pocket_solutions(items, 62, 0, 3, "paper", "hinge", rowfn=rowfn))
    assert all(0 <= s[1] < s[2] <= 29 for _, _, sol, _, _ in rows for s in sol)


def test_band_wraps_the_hinge_sides_of_a_box():
    """antler_L's region of the certified antlered dog: paper above and left,
    head hinges below (the head river) and right (the axis)."""
    reg, pocket = NE.band(7, 2, NE.Box(0, 0, 31, 5, "paper", "hinge", "paper", "hinge"))
    assert (reg.chain, reg.kind, reg.L) == (7, "river", 2)
    assert reg.rects == [(0, 3, 31, 5), (29, 0, 31, 3)]
    assert reg.vlines == [31] and reg.hlines == [5]
    assert pocket == NE.Box(0, 0, 29, 3, "paper", "hinge", "paper", "hinge")


def test_band_needs_a_hinge_side_and_room_for_a_pocket():
    assert NE.band(7, 2, NE.Box(0, 0, 31, 5, "paper", "paper", "paper", "paper")) is None
    assert NE.band(7, 20, NE.Box(0, 0, 31, 5, "paper", "hinge", "paper", "hinge")) is None


def test_mirror_reflects_in_the_axis_and_swaps_the_chain():
    reg, _ = NE.band(7, 2, NE.Box(0, 0, 31, 5, "paper", "hinge", "paper", "hinge"))
    m = NE.mirror(reg, 62, {7: 8})
    assert m.chain == 8 and m.rects == [(31, 3, 62, 5), (31, 0, 33, 3)]
    assert m.vlines == [31] and m.hlines == [5]


def test_a_path_shaped_tree_never_enters_nest(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("nest.candidates called for a path-shaped hub graph")
    monkeypatch.setattr(NE, "candidates", boom)
    con = ST.contract(ST.load_tree(artifact_tree("dog_0"), 1.0))
    assert next(PK.candidates(con)) is not None


def test_antlered_dog_packs_with_mirrored_antlers():
    rung, lay, con, _ = _first_certified(antlered("dog_0"))
    assert (rung, lay.N) == ("asymmetric", 62)
    by = {con.chains[r.chain].v: r for r in lay.regions}
    for left, right in (("antler_L", "antler_R"), ("antler_L_beam", "antler_R_beam"),
                        ("antler_L_palm", "antler_R_palm")):
        a, b = by[left], by[right]
        assert NE.mirror(a, lay.N, {a.chain: b.chain}) == b
    assert by["antler_L"].more, "the antler band is one region of several rectangles"
    assert [p[0] for p in lay.pockets][:1] == [con.root]


def test_a_symmetric_rung_layout_is_its_own_mirror_image():
    rung, lay, con, _ = _first_certified(antlered("bird_1"))
    assert (rung, lay.N) == ("symmetric", 54)
    pm = {}
    for a, b in con.pairs:
        pm[a], pm[b] = b, a
    for _, _, m in PK.hub_pairs(con):
        pm.update(m)

    def sig(r):
        return (r.chain, tuple(sorted(r.rects)), tuple(r.vlines), tuple(r.hlines))
    assert {sig(NE.mirror(r, lay.N, {r.chain: pm.get(r.chain, r.chain)})) for r in lay.regions} \
        == {sig(r) for r in lay.regions}


def test_no_hinge_is_drawn_between_two_rectangles_of_one_chain():
    """The spurious-hinge regression (spec §1): a band split into separate
    Regions would put a region boundary between two cells of the SAME chain."""
    _, lay, _, base = _first_certified(antlered("dog_0"))
    owner = {}
    for r in lay.regions:
        for x0, y0, x1, y1 in r.rects:
            for i in range(max(0, x0), min(lay.N, x1)):
                for j in range(max(0, y0), min(lay.N, y1)):
                    owner[(i, j)] = r.chain
    for (x, y), (x2, y2) in base.boundary_edges:
        if y == y2:
            c0, c1 = (min(x, x2), y - 1), (min(x, x2), y)
        else:
            c0, c1 = (x - 1, min(y, y2)), (x, min(y, y2))
        assert owner[c0] != owner[c1]


@pytest.mark.parametrize("edit,rung,N", [
    ("lopsided", "symmetric", 86),               # review focus 3: unpaired sibling hubs
    ("odd_antlers", "asymmetric", 64),           # review focus 2: odd hub-pair river
    ("antlered_and_toed", "symmetric x2", 128),  # review focus 4: two branching hubs
])
def test_review_focus_shapes_pack(edit, rung, N):
    tree = {"lopsided": lambda: lopsided("dog_0"),
            "odd_antlers": lambda: odd_antlers("dog_0"),
            "antlered_and_toed": lambda: _toe(antlered("dog_0"))}[edit]()
    got = _first_certified(tree)
    assert got is not None and (got[0], got[1].N) == (rung, N)


def test_antlered_dog_folds_end_to_end(tmp_path):
    """The spec's hard gate: the moose's shape folds like the 51 artifact trees."""
    tree = tmp_path / "tree.json"
    tree.write_text(json.dumps(antlered("dog_0")))
    rec = PL.run(str(tree), str(tmp_path), certify_global=True, verbose=False)
    assert rec.get("failure") is None
    # today's family packs it unmirrored on 62; since river routing (spec
    # 2026-10-19) an unmirrored beside layout on 58 is the only option
    assert (rec["packing_rung"], rec["grid_size"]) == ("asymmetric", 58)
    assert rec["layout"]["family"] == "beside"
    ff = rec["solving_flat_foldable"]
    assert ff[0] == ff[1]
    assert rec["global_verdict"] == "CERTIFIED"
    assert sorted(os.listdir(rec["folder"])) == \
        ["overview.png", "packing_cp.svg", "shaping_cp.svg", "solving_cp.svg"]


def test_a_branching_tree_past_the_grid_cap_fails_at_packing(tmp_path, monkeypatch):
    """Review focus 5: toed crab_3 stacked strips past the pipeline's cap
    max(2G, G + 60) = 106 (it certified only at N = 108, measured 2026-10-10)
    until river routing packed it on 90 (spec 2026-10-19 §8.5,
    `test_river_routing`).  toed spider_2, the edit furthest over the cap
    (132), still packs nothing below it, beside layouts included (both beside
    searches spend their budget).  It must fail AT PACKING, cleanly; this pins
    the known limit, so a later improvement updates this test on purpose.

    The beside budget is cut to 100,000 ticks: at the calibrated 9.3M both
    searches also end in "budget" (measured 2026-10-19), and this test pins a
    clean failure, not the calibration; today's own search is 57 s of it."""
    monkeypatch.setattr(PL, "BESIDE_WORK_BUDGET", 100_000)
    tree = tmp_path / "tree.json"
    tree.write_text(json.dumps(toed("spider_2")))
    rec = PL.run(str(tree), str(tmp_path), certify_global=False, verbose=False)
    assert rec["failure"] == "packing" and rec["pack_tried"] == 0


def test_strip_orders_are_capped_and_best_first():
    """Final review: a pocket with many child strips must not enumerate every
    permutation (9 parts = 362,880 orders, each paying the heights DP at every
    N). Orders stay best-first (children against the paper) and are capped."""
    import time
    search = NE._Search(ST.contract(ST.load_tree(antlered("dog_0"), 1.0)), 62, True)
    many = [("flaps",)] + [("child", i) for i in range(8)]
    t0 = time.perf_counter()
    orders = list(search.orders(many))
    assert time.perf_counter() - t0 < 0.2
    assert 0 < len(orders) <= NE.ORDER_CAP
    few = [("flaps",), ("child", 0), ("pair", 0)]
    best = list(search.orders(few))
    assert len(best) == 6                                   # small pockets: every order
    assert best[0][0][0] != "flaps" and best[0][-1][0] != "flaps"   # children at the ends first
