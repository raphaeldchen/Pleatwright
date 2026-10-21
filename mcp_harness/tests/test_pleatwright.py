"""Pleatwright: the tree -> folded model pipeline (mcp_harness/pleatwright),
a reimplementation of COrigami (arXiv:2606.26299).

Every tree here is one of the artifact's "Bases in Triplicate III" trees
(fixtures/full17_v3_sticks), per the owner's instruction that probes and
tests use only those trees.
"""
import itertools
import math
import os

import numpy as np
import pytest

from pleatwright import base as B
from pleatwright import fold as F
from pleatwright import pack as PK
from pleatwright import pipeline as PL
from pleatwright import shape as SH
from pleatwright import solve as SV
from pleatwright import stick as ST

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STICKS = os.path.join(HERE, "fixtures", "full17_v3_sticks")


def _build(roll, scale=1.0):
    sf = ST.load_roll(os.path.join(STICKS, f"{roll}.json"), scale)
    con = ST.contract(sf)
    sigma = SH.choose_sigma(sf, con)
    for lay in PK.candidates(con):
        b = B.build(lay, con, sigma)
        if not b.errors:
            return sf, con, sigma, lay, b
    raise AssertionError("no valid packing")


@pytest.fixture(scope="module")
def bird():
    sf, con, sigma, lay, b = _build("bird_1")
    sv = SV.solve(b, certify_global=False)
    return sf, con, sigma, lay, b, sv


def test_draw_model_ignores_matplotlib_ragged_padding(monkeypatch):
    """matplotlib 3.11 pads ragged Poly3DCollection faces with np.empty and
    add_collection3d(autolim=True) autoscales over that padding, so
    uninitialized memory nondeterministically overflows or yields NaN axis
    limits. Pin it: fill the padding with opposite-sign garbage per face and
    require a clean draw (no overflow, no NaN limits)."""
    import warnings
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import art3d
    from pleatwright import render as R

    real_empty = np.empty

    def fake_empty(shape, *a, **k):
        """Mimic matplotlib's ragged padding: opposite-sign garbage per face."""
        # Intercepts EVERY 3-D np.empty that art3d makes during the draw (not
        # only the ragged set_verts padding) and ignores dtype; the polys
        # below are float, so the garbage-filled float array stands in.
        if not isinstance(shape, tuple) or len(shape) != 3:
            return real_empty(shape, *a, **k)
        # shape = (num_faces, max_verts, 3); fill padding with alternating ±1e308
        return np.where((np.arange(shape[0]) % 2 == 0)[:, None, None],
                        -1e308, 1e308) * np.ones(shape)

    monkeypatch.setattr(art3d.np, "empty", fake_empty)

    polys = [np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]], float),
             np.array([[0, 0, 1], [1, 0, 1], [0, 1, 1]], float),
             np.array([[0, 0, 2], [1, 0, 2], [1, 1, 2], [0, 1, 2]], float)]
    fig = plt.figure()
    ax = fig.add_subplot(projection="3d")
    try:
        # STRICT only around draw_model: that is where add_collection3d
        # autoscales, the step the fix (autolim=False) guards.
        with warnings.catch_warnings():
            warnings.simplefilter("error", RuntimeWarning)
            R.draw_model(ax, polys, (20, -60))
        # NOT strict during the canvas draw: matplotlib projects EVERY face
        # slot, padding included, through np.dot and masks the padding only
        # afterwards. With this garbage, OpenBLAS (Linux CI) flags that dot as
        # an overflow while Accelerate (macOS) does not -- a harmless warning
        # on masked values, not the crash. What must hold is finite limits.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            fig.canvas.draw()
        for lo, hi in (ax.get_xlim(), ax.get_ylim(), ax.get_zlim()):
            assert np.isfinite(lo) and np.isfinite(hi) and hi > lo
    finally:
        plt.close(fig)


def test_run_has_the_keyword_signature_of_its_stages(tmp_path):
    """`run(**kw)` used to forward blindly into `_run`, so a mistyped keyword
    raised TypeError INSIDE the stage guard and came back as StageError('load'),
    which reads as a bad tree file. It must be a plain TypeError at the call."""
    import inspect
    want = {n: p.default for n, p in inspect.signature(PL._run).parameters.items()
            if p.kind is p.KEYWORD_ONLY and n != "_stage"}
    got = {n: p.default for n, p in inspect.signature(PL.run).parameters.items()
           if p.kind is p.KEYWORD_ONLY}
    assert got == want
    with pytest.raises(TypeError) as e:
        PL.run("bird_1", str(tmp_path), verbos=False)
    assert not isinstance(e.value, PL.StageError)


def test_all_51_artifact_trees_load_and_match_fixture_topology():
    import json
    names = sorted(f[:-5] for f in os.listdir(STICKS) if f.endswith(".json"))
    assert len(names) == 51
    for r in names:
        fx = json.load(open(os.path.join(HERE, "fixtures", "full17_v3_trees", f"{r}.json")))
        sf = ST.load_roll(os.path.join(STICKS, f"{r}.json"))
        par = {s.end: s.start for s in sf.sticks}
        ids = {int(k): v for k, v in fx["names"].items()}
        for n in fx["tree_nodes"]:
            if n["parent_id"] is not None:
                assert par[ids[n["id"]]] == ids[n["parent_id"]]


def test_crimp_agrees_with_repo_arrangement_oracle():
    from pleatwright.certify import cp_audit
    sets = [[0, 90, 180, 270], [0, 45, 90, 180, 270], [0, 45, 90, 225],
            [0, 90, 135, 180, 225, 270], [0, 45, 135, 180, 225, 315]]
    for angs in sets:
        k = len(angs)
        for labs in itertools.product("MV", repeat=k):
            sec = [(angs[(i + 1) % k] - angs[i]) % 360 for i in range(k)]
            assert SV.crimp_flat_foldable(sec, list(labs)) == \
                cp_audit.arrangement_ok_at_vertex([float(a) for a in angs], list(labs))


def test_base_is_a_one_unit_strip_and_folds_consistently(bird):
    sf, con, sigma, lay, b, sv = bird
    assert not b.errors
    V, raw = sv.cp.fold_input()
    m = F.build_model(np.array(V, float), raw)
    mats = F.solve_fold(m)
    assert F.closure_error(m, mats) < 1e-9
    # every base triangle maps into the strip 0 <= w <= 1
    for t in b.tris[::50]:
        for p in t.pts:
            w = t.map(p)[1]
            assert -1e-9 <= w <= 1 + 1e-9


def test_solving_cp_is_locally_flat_foldable_after_certification():
    sf, con, sigma, lay, b = _build("starfish_1")
    sv = SV.solve(b, certify_global=True)
    assert sv.global_verdict == "CERTIFIED"
    assert sv.ff_local[0] == sv.ff_local[1]


def test_tree_shaping_reaches_every_stick_direction_exactly(bird):
    sf, con, sigma, lay, b, sv = bird
    _check_directions(sf, con, b, sigma)


def _check_directions(sf, con, b, sigma):
    """Each stick's paper, folded, runs along its stick-figure direction --
    measured against the AUTHORED parent->child direction, so a stick a chain
    traverses end -> start must come out reversed along the chain."""
    ops, G, info, children, Q0 = SH.plan_folds(sf, con, b, sigma)
    rev = {n: r for c in con.chains for n, r in zip(c.sticks, c.reversed)}
    for s in sf.sticks:
        d = info[s.name]
        u = b.strip[con.chains[d["chain"]].u]
        p0 = G[s.name] @ np.array([u + d["sigma"] * d["off0"], 0.5, 0, 1.0])
        p1 = G[s.name] @ np.array([u + d["sigma"] * d["off1"], 0.5, 0, 1.0])
        v = (p1 - p0)[:3] * (-1 if rev[s.name] else 1)
        cosang = float(v @ s.direction) / np.linalg.norm(v)
        assert cosang > 1 - 1e-9, s.name


def test_sticks_traversed_end_to_start_are_reversed():
    # guinea_pig_1's authored root has degree 2, so the packing root is a
    # different hub and one chain runs through a stick backwards.
    sf, con, sigma, lay, b = _build("guinea_pig_1")
    assert any(any(c.reversed) for c in con.chains)
    _check_directions(sf, con, b, sigma)
    sv = SV.solve(b, certify_global=False)
    assert PL.similarity(sf, con, b, sigma) > 0.98


def test_shaping_cp_folds_closed_and_world_aligned(bird):
    sf, con, sigma, lay, b, sv = bird
    cand = PL.shape_and_fold(sf, con, b, sv, sigma)
    assert cand["closure"] < 1e-4
    assert cand["ff"][0] >= 0.99 * cand["ff"][1]
    # world alignment: the folded model's extent along +Y (up) matches the
    # stick figure's vertical extent within the strip width
    P = np.vstack(cand["polys"])
    tgt = np.array(list(sf.positions().values()))
    assert abs(np.ptp(P[:, 1]) - np.ptp(tgt[:, 1])) < 3.0


def test_narrowing_adds_no_failing_vertices(bird):
    sf, con, sigma, lay, b, sv = bird
    plain = PL.shape_and_fold(sf, con, b, sv, sigma)
    leaves = [c.sticks[-1] for c in con.chains if c.leaf]
    nar = PL.shape_and_fold(sf, con, b, sv, sigma, narrow=[(n, "asym2") for n in leaves])
    assert nar["closure"] < 1e-4
    assert len(nar["shaped"].narrowings) >= 3
    fail_plain = plain["ff"][1] - plain["ff"][0]
    fail_nar = nar["ff"][1] - nar["ff"][0]
    assert fail_nar <= fail_plain


def test_svg_round_trip_through_the_svg_parser(bird, tmp_path):
    from pleatwright.cp import parse_svg
    sf, con, sigma, lay, b, sv = bird
    cand = PL.shape_and_fold(sf, con, b, sv, sigma)
    V, E = parse_svg(cand["shaped"].cp.svg(precision=5))
    m = F.build_model(np.array(V) * b.N, E)
    assert F.closure_error(m, F.solve_fold(m)) < 1e-3


def test_orchestration_selects_the_best_judged_candidate_offline(bird):
    from pleatwright import orchestrate as O
    sf, con, sigma, lay, b, sv = bird
    base = PL.shape_and_fold(sf, con, b, sv, sigma)
    scores = iter([4, 7])         # baseline judged 4, the proposal 7

    def fake_chat(messages, max_tokens=2000):
        content = messages[0]["content"]
        if isinstance(content, str):   # policy prompt
            return '[{"tool": "narrow", "stick": "head", "template": "asym2"}]'
        return f"looks fine <{next(scores)}>"
    orig_j, orig_p = O.judge, O.propose
    try:
        O.judge = lambda subj, imgs, chat=None: orig_j(subj, imgs, chat=fake_chat)
        O.propose = lambda sf_, k=3, chat=None: orig_p(sf_, 1, chat=fake_chat)
        best, rec = PL._orchestrate(sf, con, b, sv, sigma, base, k=1)
    finally:
        O.judge, O.propose = orig_j, orig_p
    assert rec["orchestrator"] == "llm"
    assert best["shaped"].narrowings and best["shaped"].narrowings[0].stick == "head"
    assert O.reward(7, 1, True) == pytest.approx(0.76)
    assert O.reward(None, 1, True) == -1.0


@pytest.mark.skipif(not os.path.isdir(os.path.expanduser("~/Desktop/origami_samples")),
                    reason="COrigami's released samples are not in the repo")
def test_folder_port_closes_on_corigami_released_shaping_cp():
    from pleatwright.cp import parse_svg
    d = os.path.expanduser("~/Desktop/origami_samples/Ram with large curled horns and sturdy legs_30/")
    V, E = parse_svg(open(d + "shaping_cp.svg").read())
    m = F.build_model(V, E)
    mats = F.solve_fold(m)
    assert F.closure_error(m, mats) < 1e-5


@pytest.mark.parametrize("roll,folder,sha", [
    ("bird_1", "Bird roll 1_40",
     "381d84d959dde76e22fc3f261b56a129ab6206add6aeb917ea7be08dd91d92bd"),
    ("starfish_1", "Starfish roll 1_48",
     "1c9a3684bf2085c00290843e9f203a607d0adbff801a79485f88e53e33bdb647"),
])
def test_packing_cp_bytes_match_the_delivered_models(tmp_path, roll, folder, sha):
    """Byte identity with the delivered folders, as a CI guard.

    Only `packing_cp.svg` is pinned. It is written at precision 0 from
    integer-grid coordinates, so its bytes do not depend on the platform's
    floating-point library. `solving_cp.svg` and `shaping_cp.svg` are written
    at precision 5 from solved/folded floats, and the overview PNG from a
    rasteriser; their bytes are not pinned across platforms (a frozen hash
    over roundoff-bearing output cannot be green on both Accelerate and
    OpenBLAS)."""
    import hashlib
    rec = PL.run(roll, str(tmp_path), certify_global=True, verbose=False)
    assert os.path.basename(rec["folder"]) == folder
    with open(os.path.join(rec["folder"], "packing_cp.svg"), "rb") as f:
        assert hashlib.sha256(f.read()).hexdigest() == sha
