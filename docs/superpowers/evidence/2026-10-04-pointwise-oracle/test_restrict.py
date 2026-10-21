"""Unit tests for the production arm. Run directly, never via `pytest tests/`.

    cd docs/superpowers/evidence/2026-10-04-pointwise-oracle
    ../../../../.venv/bin/python3 -m pytest test_restrict.py -v
"""
import os
import sys
from fractions import Fraction

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "..", "mcp_harness"))
sys.path.insert(0, os.path.join(HERE, "..", "2026-10-04-exact-arrangement"))
sys.path.insert(0, HERE)

import build                           # noqa: E402
import exact_arrangement               # noqa: E402
import kernel                          # noqa: E402
import layer_certify                   # noqa: E402
import restrict                        # noqa: E402


class _C:
    """A stand-in Clause: the real one is a frozen dataclass, and these tests
    need only the three fields `restricted_clauses` and `clause_accepts` read."""

    def __init__(self, family, variables, flips):
        self.family = family
        self.variables = variables
        self.flips = flips
        self.prov = "test"


def test_restricted_clauses_keeps_only_fully_interior_clauses():
    """Both directions matter. Dropping a clause that IS interior would weaken
    the production arm and manufacture agreement; keeping one that is not would
    ask the oracle about a face it cannot see."""
    inside = _C("equality", ((0, 1), (0, 2)), (False, False))
    straddling = _C("equality", ((0, 1), (0, 9)), (False, False))
    outside = _C("equality", ((8, 9), (7, 9)), (False, False))
    got = restrict.restricted_clauses((inside, straddling, outside),
                                      frozenset({0, 1, 2}))
    assert got == (inside,), got


def test_order_to_rel_matches_layer_certifys_convention():
    """`layer_certify._satisfied` documents `rel[(lo, hi)] is True` as "lo
    above hi" (:143). `order[0]` is topmost, so above means a SMALLER index."""
    rel = restrict.order_to_rel((2, 0, 1))
    assert rel[(0, 1)] is True          # 0 precedes 1, so 0 is above 1
    assert rel[(0, 2)] is False         # 2 precedes 0, so 0 is NOT above 2
    assert rel[(1, 2)] is False
    assert set(rel) == {(0, 1), (0, 2), (1, 2)}


def test_clause_accepts_evaluates_equality_both_ways():
    """`equality` is `vals[0] == vals[1]` (layer_certify.py:145-146). With
    `_lit(x, f) = ((x, f), False) if x < f else ((f, x), True)`, the clause
    "face 2 is on the same side of 0 as of 1" is ((0, 2), True), ((1, 2), True).
    """
    c = _C("equality", ((0, 2), (1, 2)), (True, True))
    # 2 above both 0 and 1: both literals true -> equal -> satisfied
    assert restrict.clause_accepts((c,), restrict.order_to_rel((2, 0, 1)))
    # 2 between 0 and 1: one literal true, one false -> violated
    assert not restrict.clause_accepts((c,), restrict.order_to_rel((0, 2, 1)))


def test_transitivity_family_rejects_a_cyclic_relation():
    """GATE (spec section 6.2). `transitivity` is vacuous on a total order, so
    the enumeration never tests it; this is the correctly-sized substitute. The
    predicate is `not (rab == rbc and rac != rab)` (layer_certify.py:147-149).
    """
    cyc = {(0, 1): True, (1, 2): True, (0, 2): False}   # 0>1>2 but 2>0
    vals = (cyc[(0, 1)], cyc[(1, 2)], cyc[(0, 2)])
    assert not layer_certify._satisfied("transitivity", vals), (
        "a cyclic triple must violate the transitivity family")
    acyc = (True, True, True)
    assert layer_certify._satisfied("transitivity", acyc)


def test_classify_uses_the_restricted_set_not_global_membership():
    """A clause whose variables leave the subset says nothing the oracle can
    check, so a subset it touches is still population B."""
    straddling = _C("equality", ((0, 1), (0, 9)), (False, False))
    assert restrict.classify((straddling,), frozenset({0, 1, 2})) == "B"
    interior = _C("taco", ((0, 1), (0, 2), (1, 2), (0, 1)),
                  (False, False, False, True))
    assert restrict.classify((interior,), frozenset({0, 1, 2})) == "A"


def test_creases_in_filters_both_faces():
    creases = ((0, 1, "segA"), (1, 9, "segB"), (2, 3, "segC"))
    got = restrict.creases_in(creases, frozenset({0, 1, 2}))
    assert got == ((0, 1, "segA"),), got


def test_candidate_subsets_falls_back_to_an_intersecting_cover():
    """A crease whose two faces share NO cell must still produce a subset.
    Production guards cover membership with `if tuple(sorted((fa, fb))) in
    pairs` (layer_order.py:570), so such creases exist; requiring a cover to
    contain the whole seed would drop them and shrink the population in
    silence."""
    creases = ((0, 5, "seg"),)
    covers = (frozenset({0, 1, 2}), frozenset({5, 6, 7}))
    subs = restrict.candidate_subsets(creases, covers, max_size=4)
    assert subs, "the crease was dropped instead of falling back"
    s = subs[0]
    assert {0, 5} <= s and len(s) <= 4, s


def test_candidate_subsets_respects_max_size_and_contains_a_crease():
    creases = ((0, 1, "segA"), (2, 3, "segB"))
    covers = (frozenset({0, 1, 2, 3, 4, 5}), frozenset({2, 3, 6}))
    subs = restrict.candidate_subsets(creases, covers, max_size=4)
    assert subs, "no candidate subsets produced"
    for s in subs:
        assert len(s) <= 4, s
        assert any(fa in s and fb in s for fa, fb, _ in creases), s


def test_restricted_clauses_drops_a_clause_with_lo_outside_and_hi_inside():
    """The other direction of "outside": the existing test only has `hi`
    outside. A check on `hi` alone would keep this one."""
    lo_out = _C("equality", ((0, 1), (0, 2)), (False, False))
    subset = frozenset({1, 2, 3})
    assert restrict.restricted_clauses((lo_out,), subset) == ()


def test_restricted_clauses_keeps_a_wholly_interior_taco_and_drops_a_leaking_one():
    inside = _C("taco", ((0, 1), (0, 2), (1, 3), (2, 3)),
                (False, False, False, False))
    one_out = _C("taco", ((0, 1), (0, 2), (1, 3), (2, 9)),
                 (False, False, False, False))
    subset = frozenset({0, 1, 2, 3})
    got = restrict.restricted_clauses((inside, one_out), subset)
    assert got == (inside,), got


def test_clause_accepts_evaluates_taco_both_ways_including_flips():
    """`taco` is `(vals[0] != vals[1]) == (vals[2] != vals[3])`
    (layer_certify.py:150-151), and a literal's value is `rel[pair] != flip`.
    With flips (True, False, False, False) the first literal is inverted
    relative to the raw relation, so the SAME clause is satisfied by one order
    and violated by another -- which is only true if the `flips` path is live.
    """
    c = _C("taco", ((0, 1), (0, 2), (1, 2), (0, 3)),
           (True, False, False, False))
    # order (1, 0, 2, 3): rel(0,1)=False, so v0 = False != True = True;
    # rel(0,2)=True, rel(1,2)=True, rel(0,3)=True -> (T != T)=F == (T != T)=F
    sat = restrict.order_to_rel((1, 0, 2, 3))
    assert restrict.clause_accepts((c,), sat)
    # order (0, 1, 2, 3): rel(0,1)=True, so v0 = True != True = False;
    # v1 = True -> (F != T)=T, but (T != T)=F -> T != F -> violated
    viol = restrict.order_to_rel((0, 1, 2, 3))
    assert not restrict.clause_accepts((c,), viol)
    # With no flips the same two orders swap roles, pinning that flips matter.
    plain = _C("taco", c.variables, (False, False, False, False))
    assert restrict.clause_accepts((plain,), viol)
    assert not restrict.clause_accepts((plain,), sat)


def test_geometric_keeps_equality_and_taco_and_drops_transitivity():
    eq = _C("equality", ((0, 2), (1, 2)), (True, True))
    taco = _C("taco", ((0, 1), (0, 2), (1, 2), (0, 3)),
              (False, False, False, False))
    tr = _C("transitivity", ((0, 1), (1, 2), (0, 2)), (False, False, False))
    assert restrict.geometric((eq, tr, taco)) == (eq, taco)


def test_equality_triples_recovers_x_and_the_crease_pair():
    """`_lit(2, 0)` is ((0, 2), True) and `_lit(2, 1)` is ((1, 2), True), so
    the clause is variables ((0, 2), (1, 2)) with flips (True, True)."""
    c = _C("equality", ((0, 2), (1, 2)), (True, True))
    assert restrict.equality_triples((c,)) == ((2, frozenset({0, 1})),)


def test_equality_triples_ignores_other_families():
    taco = _C("taco", ((0, 1), (0, 2), (1, 2), (0, 3)),
              (False, False, False, False))
    assert restrict.equality_triples((taco,)) == ()


def test_equality_triples_refuses_pairs_that_share_no_face():
    bad = _C("equality", ((0, 1), (2, 3)), (False, False))
    with pytest.raises(ValueError, match="share"):
        restrict.equality_triples((bad,))


def test_equality_triples_refuses_identical_pairs():
    bad = _C("equality", ((0, 1), (0, 1)), (False, False))
    with pytest.raises(ValueError, match="share"):
        restrict.equality_triples((bad,))


def test_crease_segments_on_the_real_witness():
    """Pins the real folded state, because the synthetic tests above cannot
    catch the defect this function's shape exists to avoid: reading folded
    vertices out of the CLIPPING polygons instead of `folded_vertices`.
    `layer_order._polys_of` reverses negative-area faces -- 190 of 380 on this
    subject -- so indexing the wrong array is wrong on half the faces.
    """
    K = kernel.EXACT
    ff, _polys = exact_arrangement.load()
    segs = restrict.crease_segments(ff, K)
    mv = [e for e in ff.shared_edges if e[3] in ("M", "V")]
    assert len(segs) == 745
    assert len(segs) == len(mv)
    folded = build._folded_of(ff, K)
    for (fa, fb, seg), (efa, efb, k, _a) in zip(segs, mv):
        assert (fa, fb) == (efa, efb)
        face = ff.faces[fa]
        want = (folded[fa][face.index(k[0])], folded[fa][face.index(k[1])])
        assert seg == want, (fa, fb, seg, want)
        for x, y in seg:
            assert isinstance(x, Fraction) and isinstance(y, Fraction)
