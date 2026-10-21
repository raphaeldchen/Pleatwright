"""Unit tests for the oracle. Run directly, never via `pytest tests/`.

    cd docs/superpowers/evidence/2026-10-04-pointwise-oracle
    ../../../../.venv/bin/python3 -m pytest test_stacks.py -v
"""
import ast
import os
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "2026-10-04-exact-arrangement"))
sys.path.insert(0, HERE)

import kernel                          # noqa: E402
import pytest                          # noqa: E402
import stacks                          # noqa: E402

K = kernel.EXACT
F = Fraction


def _square(x0, y0, x1, y1):
    """A CCW axis-aligned rectangle in exact rationals."""
    return [(F(x0), F(y0)), (F(x1), F(y0)), (F(x1), F(y1)), (F(x0), F(y1))]


def _stacks_source():
    with open(os.path.join(HERE, "stacks.py")) as fh:
        return fh.read()


def test_imports_are_allowlisted():
    """`stacks.py` must not depend on production code. The property is
    structural, so assert it on the AST rather than by substring: collect every
    module named by an import statement and require it to be a subset of an
    explicit allowlist. (`geom` is the shared, immutable predicate layer; see
    the module docstring for what that does and does not make independent.)"""
    src = _stacks_source()
    tree = ast.parse(src)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module)
    allowed = {"dataclasses", "geom"}
    assert imported <= allowed, (
        f"stacks.py imports {sorted(imported - allowed)} beyond the allowlist "
        f"{sorted(allowed)}")
    # A dynamic import would evade the AST check above.
    for dynamic in ("__import__", "importlib"):
        assert dynamic not in src, (
            f"stacks.py mentions {dynamic!r}; a dynamic import would evade "
            f"the AST allowlist")
    # Secondary check, over RAW source (docstrings included): the names that
    # would indicate a production dependency. The constraint is literal, so
    # the scan is too.
    for banned in ("layer_order", "layer_certify", "box_pleat", "flat_fold",
                   "build", "mcp_harness"):
        assert banned not in src, (
            f"stacks.py mentions {banned!r}; the oracle must not import or "
            f"name production code, or the comparison is circular")


def test_point_at_endpoints_and_midpoint():
    seg = ((F(0), F(0)), (F(4), F(2)))
    assert stacks.point_at(seg, F(0)) == (F(0), F(0))
    assert stacks.point_at(seg, F(1)) == (F(4), F(2))
    assert stacks.point_at(seg, F(1, 2)) == (F(2), F(1))


def test_breakpoints_include_ends_and_one_clip_span():
    """One face covering the middle half of the segment contributes its two
    span endpoints, and the segment's own ends are always present."""
    seg = ((F(0), F(0)), (F(4), F(0)))
    polys = {7: _square(1, -1, 3, 1)}
    cuts = stacks.breakpoints(seg, polys, (7,), K)
    assert cuts == (F(0), F(1, 4), F(3, 4), F(1)), cuts


def _cover_constant(seg, polys, others, cuts, K):
    """True only if the covering set is identical at three interior probes
    (1/4, 1/2, 3/4) of every interval in `cuts`.

    This is the completeness gate for `stacks.breakpoints`, factored out so the
    real check and its failure demonstrations run the SAME code.

    HONEST LIMITATION: three probes detect a missing cut only when the
    resulting change point lies within the middle half of the merged interval
    (between its 1/4 and 3/4 probes). A change point in the outer quarters is
    invisible to this check, so its power depends on the fixture.
    """
    for t_lo, t_hi in zip(cuts, cuts[1:]):
        w = t_hi - t_lo
        probes = [t_lo + w * F(1, 4), t_lo + w * F(1, 2),
                  t_lo + w * F(3, 4)]
        covers = {stacks.covering(seg, t, polys, others, K) for t in probes}
        if len(covers) != 1:
            return False
    return True


def _three_faces():
    seg = ((F(0), F(0)), (F(6), F(0)))
    polys = {
        7: _square(1, -1, 3, 1),
        8: _square(2, -1, 5, 1),
        9: _square(4, -1, 6, 1),
    }
    return seg, polys, (7, 8, 9)


def test_breakpoints_bound_constant_cover():
    """THE load-bearing claim (spec section 2.1): one sample per sub-segment is
    EXHAUSTIVE, not approximate, because the covering set changes only at a
    clip endpoint. Measured, not asserted: the cover must agree at three
    distinct interior points of every sub-segment."""
    seg, polys, others = _three_faces()
    cuts = stacks.breakpoints(seg, polys, others, K)
    assert len(cuts) >= 4, cuts
    assert _cover_constant(seg, polys, others, cuts, K), (
        "cover is NOT constant on some sub-segment: the breakpoint set is "
        "incomplete, so one sample per sub-segment would be a sampling "
        "approximation rather than exhaustive")


def test_coarsened_breakpoints_break_the_completeness_gate():
    """The refusal demonstration for the gate above: with the interior cuts
    removed, the cover is provably NOT constant, so the gate must fail. A gate
    never shown to fail is a gate nobody has tested."""
    seg = ((F(0), F(0)), (F(6), F(0)))
    polys = {7: _square(1, -1, 3, 1)}
    assert not _cover_constant(seg, polys, (7,), (F(0), F(1)), K), (
        "the coarsened breakpoint list produced a constant cover, so this "
        "test is not exercising the failure it claims to")


def test_dropping_a_real_breakpoint_is_detected():
    """Mutation-style: take the REAL `breakpoints` output on the three-face
    fixture, delete one interior cut, and require the gate to notice. This
    shows the gate can reject a wrong output of the real function, not merely
    a hand-built coarse list."""
    seg, polys, others = _three_faces()
    cuts = stacks.breakpoints(seg, polys, others, K)
    assert _cover_constant(seg, polys, others, cuts, K)
    detected = 0
    for i in range(1, len(cuts) - 1):
        mutated = cuts[:i] + cuts[i + 1:]
        if not _cover_constant(seg, polys, others, mutated, K):
            detected += 1
    # This fixture is fixed, exact and deterministic: dropping each of the five
    # interior cuts (1/6, 1/3, 1/2, 2/3, 5/6) is detected every time, so
    # require ALL of them rather than "at least one".
    assert detected == len(cuts) - 2, (
        f"only {detected} of {len(cuts) - 2} single interior-cut drops were "
        f"detected; the gate has lost power on this fixture")


def test_covering_excludes_a_face_whose_boundary_runs_along_the_crease():
    """Strict interior, not closure: a face whose EDGE lies on the crease is
    not threading the fold, so it is not an intruder."""
    seg = ((F(0), F(0)), (F(4), F(0)))
    polys = {7: _square(0, 0, 4, 2)}          # bottom edge IS the segment
    assert stacks.covering(seg, F(1, 2), polys, (7,), K) == frozenset()


def test_sites_refuses_a_crease_with_a_face_outside_the_subset():
    seg = ((F(0), F(0)), (F(4), F(0)))
    polys = {0: _square(0, 0, 1, 1), 1: _square(0, 0, 1, 1),
             7: _square(1, -1, 3, 1)}
    with pytest.raises(ValueError, match="outside the subset"):
        stacks.sites([(0, 99, seg)], polys, frozenset({0, 1, 7}), K)


def test_violation_when_a_face_is_between_the_creases_two_faces():
    """The hand-built intruder (spec section 6.4): face 7 covers the crease
    and the order places it between faces 0 and 1."""
    seg = ((F(0), F(0)), (F(4), F(0)))
    polys = {0: _square(0, -1, 4, 1), 1: _square(0, -1, 4, 1),
             7: _square(1, -1, 3, 1)}
    s = stacks.sites([(0, 1, seg)], polys, frozenset({0, 1, 7}), K)
    act = stacks.active(s)
    assert act, "the intruder fixture produced no active site"
    assert not stacks.accepts(act, (0, 7, 1)), "7 between 0 and 1 must reject"
    assert stacks.accepts(act, (7, 0, 1)), "7 above both must be accepted"
    assert stacks.accepts(act, (0, 1, 7)), "7 below both must be accepted"
    bad = stacks.violations_for_order(act, (0, 7, 1))
    assert bad and bad[0][1] == (7,), bad


def test_active_drops_sites_with_no_candidate_intruder():
    seg = ((F(0), F(0)), (F(4), F(0)))
    polys = {0: _square(0, -1, 4, 1), 1: _square(0, -1, 4, 1)}
    s = stacks.sites([(0, 1, seg)], polys, frozenset({0, 1}), K)
    assert stacks.active(s) == ()


def _l_hexagon():
    """The reviewer's L-shaped face, CCW: a 2x2 square with the upper-right
    unit square removed. Its reflex vertex is (1, 1)."""
    return [(F(0), F(0)), (F(2), F(0)), (F(2), F(1)),
            (F(1), F(1)), (F(1), F(2)), (F(0), F(2))]


def _inside_even_odd(p, poly):
    """Ground truth for a point strictly inside a polygon (even-odd rule),
    independent of the half-plane predicates under test. Test points here are
    never on an edge."""
    x, y = p
    n = len(poly)
    inside = False
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        if (y0 > y) != (y1 > y):
            if x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
                inside = not inside
    return inside


def test_a_convex_rectangle_is_convex():
    assert stacks.is_convex(_square(0, 0, 4, 2), K)


def test_an_l_shaped_hexagon_is_not_convex():
    assert not stacks.is_convex(_l_hexagon(), K)


def test_collinear_vertices_do_not_break_convexity():
    """A square with three extra collinear vertices on its edges."""
    poly = [(F(0), F(0)), (F(1), F(0)), (F(2), F(0)), (F(2), F(1)),
            (F(2), F(2)), (F(1), F(2)), (F(0), F(2)), (F(0), F(1))]
    assert stacks.is_convex(poly, K)


def test_a_clockwise_convex_square_is_rejected():
    """A CW square is convex but INVISIBLE to `covering`: `strictly_inside`
    needs every edge cross product strictly positive, so a CW face reads as
    containing nothing and the oracle would accept a bad order. It must be
    rejected. The CCW twin is found by `covering`, as the control."""
    ccw = _square(0, 0, 2, 2)
    cw = list(reversed(ccw))
    seg = ((F(-1), F(1)), (F(3), F(1)))
    assert stacks.covering(seg, F(1, 2), {7: ccw}, (7,), K) == frozenset({7})
    assert stacks.covering(seg, F(1, 2), {7: cw}, (7,), K) == frozenset()
    assert stacks.is_convex(ccw, K)
    assert not stacks.is_convex(cw, K)


def test_a_pentagram_is_not_convex():
    """Self-intersecting, yet every turn is a left turn."""
    star = [(F(0), F(2)), (F(1), F(-2)), (F(-2), F(0)), (F(2), F(0)),
            (F(-1), F(-2))]
    assert not stacks.is_convex(star, K)


def test_an_all_collinear_polygon_is_not_convex():
    assert not stacks.is_convex([(F(0), F(0)), (F(1), F(0)), (F(2), F(0))], K)


def test_too_few_vertices_is_not_convex():
    assert not stacks.is_convex([], K)
    assert not stacks.is_convex([(F(0), F(0)), (F(1), F(1))], K)


def test_a_nonconvex_face_is_INVISIBLE_to_covering_which_is_why_is_convex_exists():  # noqa: E501
    """The hazard `is_convex` guards. This pins TODAY's behaviour of
    `covering` on a non-convex face, to document why the guard exists. If it
    ever fails because `covering` grew non-convex support, the correct
    response is to update this test, NOT to restore the old behaviour.

    A crease runs along the horizontal arm of
    the L; its points at t = 1/2 and t = 3/4 are plainly inside the face
    (checked against an even-odd ground truth), yet `covering` reports no
    intruder, because the half-plane predicates read the reflex vertex's two
    edges as cutting the plane. An oracle fed this face would MISS the
    intruder and ACCEPT a bad order."""
    seg = ((F(0), F(1, 2)), (F(2), F(1, 2)))
    polys = {7: _l_hexagon()}
    assert not stacks.is_convex(polys[7], K)
    for t in (F(1, 2), F(3, 4)):
        p = stacks.point_at(seg, t)
        assert _inside_even_odd(p, polys[7]), (
            f"fixture error: {p} is not inside the L")
        assert stacks.covering(seg, t, polys, (7,), K) == frozenset(), (
            f"covering found the L at {p}; the hazard this test records has "
            f"gone away, so is_convex may no longer be needed")


def _intruder_fixture():
    seg = ((F(0), F(0)), (F(4), F(0)))
    polys = {0: _square(0, -1, 4, 1), 1: _square(0, -1, 4, 1),
             7: _square(1, -1, 3, 1)}
    return seg, polys


def test_triples_finds_the_intruder_on_the_three_face_fixture():
    """Faces 0 and 1 are joined by a crease; face 7 covers its middle. The
    crease's own faces are never intruders of it, so the result is exactly the
    one triple."""
    seg, polys = _intruder_fixture()
    got = stacks.triples([(0, 1, seg)], polys, K)
    assert got == frozenset({(7, frozenset({0, 1}))}), got


def test_triples_is_empty_when_no_face_covers_the_crease():
    seg = ((F(0), F(0)), (F(4), F(0)))
    polys = {0: _square(0, -1, 4, 1), 1: _square(0, -1, 4, 1)}
    got = stacks.triples([(0, 1, seg)], polys, K)
    assert got == frozenset() and isinstance(got, frozenset), got


def test_triples_honours_an_explicit_faces_argument():
    """Omitting the intruder from `faces` removes it from the enumeration,
    which shows the parameter is wired through."""
    seg, polys = _intruder_fixture()
    assert stacks.triples([(0, 1, seg)], polys, K, faces=(0, 1)) == frozenset()
    assert stacks.triples([(0, 1, seg)], polys, K, faces=(0, 1, 7)) == \
        frozenset({(7, frozenset({0, 1}))})


def test_triples_narrowing_matches_the_unnarrowed_path():
    """PARITY test guarding a COST optimisation in `stacks.triples`.

    `triples` narrows its candidate faces to those whose `geom.clip_seg` span
    against the crease is not `None` before computing breakpoints. This test
    recomputes the triples the long way -- `breakpoints` and `covering` over
    EVERY other face, no narrowing -- and requires exact equality, so an
    incorrect later "optimisation" of the narrowing fails here.

    The narrowing is sound because a `None` clip span means the segment never
    enters the face's closed region, so the face's strict interior cannot
    contain any point of it, and `covering` could never have returned that
    face. The fixture asserts the narrowing really removes a face; without
    that the test would be vacuous.
    """
    seg = ((F(0), F(0)), (F(6), F(0)))
    polys = {
        0: _square(0, -1, 6, 1),       # crease face, never an intruder
        1: _square(0, -1, 6, 1),       # crease face, never an intruder
        7: _square(1, -1, 3, 1),       # covers the crease over [1, 3]
        8: _square(2, -1, 5, 1),       # overlaps 7, covers [2, 5]
        9: _square(10, 3, 12, 5),      # far from the crease: clip_seg is None
        10: _square(1, 2, 4, 4),       # above the crease: clip_seg is None
    }
    assert len(polys) >= 4
    fa, fb = 0, 1
    others = tuple(x for x in sorted(polys) if x not in (fa, fb))

    clipping = tuple(x for x in others
                     if stacks.geom.clip_seg(seg, polys[x], K) is not None)
    assert set(clipping) < set(others), (
        "the narrowing removes nothing on this fixture, so the parity test "
        "is vacuous")
    assert clipping == (7, 8), clipping

    unnarrowed = set()
    cuts = stacks.breakpoints(seg, polys, others, K)
    for t_lo, t_hi in zip(cuts, cuts[1:]):
        mid = (t_lo + t_hi) / 2
        for x in stacks.covering(seg, mid, polys, others, K):
            unnarrowed.add((x, frozenset({fa, fb})))
    assert unnarrowed == {(7, frozenset({0, 1})), (8, frozenset({0, 1}))}

    assert stacks.triples([(fa, fb, seg)], polys, K) == frozenset(unnarrowed)


sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "..", "mcp_harness"))

import enumerate_orders                # noqa: E402
import restrict                        # noqa: E402


def test_all_orders_is_every_permutation_exactly_once():
    got = enumerate_orders.all_orders(frozenset({0, 1, 2}))
    assert len(got) == 6 and len(set(got)) == 6
    assert all(sorted(o) == [0, 1, 2] for o in got)


def test_rel_to_order_recovers_a_total_order():
    rel = restrict.order_to_rel((2, 0, 1))
    assert enumerate_orders.rel_to_order(rel, frozenset({0, 1, 2})) == (2, 0, 1)


def test_rel_to_order_returns_None_on_a_cycle():
    """A tournament is transitive iff its score sequence is 0, 1, ..., n-1, so
    a repeated score is exactly a cycle. Returns None rather than raising: a
    cyclic relation is a finding to report, not a crash."""
    cyc = {(0, 1): True, (1, 2): True, (0, 2): False}
    assert enumerate_orders.rel_to_order(cyc, frozenset({0, 1, 2})) is None


def test_rel_to_order_returns_None_on_a_missing_pair():
    assert enumerate_orders.rel_to_order({(0, 1): True},
                                         frozenset({0, 1, 2})) is None


def test_compare_reports_both_difference_directions():
    """A comparison that only answered "do both say foldable" would pass a
    wrong clause set whenever one valid order survived. Both differences must
    come back separately."""
    seg = ((F(0), F(0)), (F(4), F(0)))
    polys = {0: _square(0, -1, 4, 1), 1: _square(0, -1, 4, 1),
             7: _square(1, -1, 3, 1)}
    subset = frozenset({0, 1, 7})
    s = stacks.sites([(0, 1, seg)], polys, subset, K)

    # A clause arm that forbids NOTHING: the oracle is strictly stricter.
    out = enumerate_orders.compare(
        s, (), subset,
        clause_accepts=lambda cl, rel: True,
        order_to_rel=restrict.order_to_rel)
    assert out["orders"] == 6
    assert out["clauses_admit"] == 6
    assert out["oracle_admits"] == 4          # the two with 7 between 0 and 1
    assert out["only_clauses"] and not out["only_oracle"]
    assert out["identical"] is False

    # A clause arm that forbids EVERYTHING: the oracle is strictly looser.
    out2 = enumerate_orders.compare(
        s, (), subset,
        clause_accepts=lambda cl, rel: False,
        order_to_rel=restrict.order_to_rel)
    assert out2["only_oracle"] and not out2["only_clauses"]


def test_compare_refuses_a_cover_face_outside_the_subset():
    seg = ((F(0), F(0)), (F(4), F(0)))
    bogus = (stacks.Site(0, 1, frozenset({42}), F(0), F(1)),)
    with pytest.raises(ValueError, match="outside the subset"):
        enumerate_orders.compare(
            bogus, (), frozenset({0, 1}),
            clause_accepts=lambda cl, rel: True,
            order_to_rel=restrict.order_to_rel)


# --- compare, driven by REAL production clauses -------------------------
# Added after the Task 3 review, which found both existing `compare` tests
# used degenerate constant clause arms (always-accept, always-reject). So
# `identical=True` -- the outcome the real run reports -- was never asserted,
# and nothing exercised a clause arm that actually agrees with the geometry.

import layer_certify                   # noqa: E402


def _intruder_subset():
    """Faces 0 and 1 joined by a crease, face 7 covering its middle."""
    seg = ((F(0), F(0)), (F(4), F(0)))
    polys = {0: _square(0, -1, 4, 1), 1: _square(0, -1, 4, 1),
             7: _square(1, -1, 3, 1)}
    subset = frozenset({0, 1, 7})
    return stacks.sites([(0, 1, seg)], polys, subset, K), subset


def test_compare_is_identical_against_the_faithful_production_clause():
    """A real `equality` clause for this geometry must admit EXACTLY the
    orders the oracle admits.

    `_lit(7, 0)` is `((0, 7), True)` and `_lit(7, 1)` is `((1, 7), True)`
    (`layer_order.py:362-366`), so this clause reads "7 is on the same side of
    0 as of 1" -- which is precisely "7 does not lie between 0 and 1", the
    oracle's own rule for this crease. Agreement here is the positive control
    the other two `compare` tests lack.
    """
    sts, subset = _intruder_subset()
    clause = layer_certify.Clause(family="equality",
                                  variables=((0, 7), (1, 7)),
                                  flips=(True, True), prov="test")
    out = enumerate_orders.compare(
        sts, (clause,), subset,
        clause_accepts=restrict.clause_accepts,
        order_to_rel=restrict.order_to_rel)
    assert out["orders"] == 6
    assert out["oracle_admits"] == 4, out
    assert out["clauses_admit"] == 4, out
    assert out["only_oracle"] == () and out["only_clauses"] == (), out
    assert out["identical"] is True, out


def test_compare_reports_BOTH_difference_sets_non_empty_at_once():
    """The two arms disagreeing in both directions simultaneously.

    The clause arm is a real `equality` on the triple (0, {1, 7}) -- "0 does
    not lie between 1 and 7" -- for which the oracle has no site at all, since
    no crease joins 1 and 7. So each arm forbids two orders the other allows,
    and neither difference set is empty. An existence-only comparison would
    call this agreement, because both arms admit four orders.
    """
    sts, subset = _intruder_subset()
    clause = layer_certify.Clause(family="equality",
                                  variables=((0, 1), (0, 7)),
                                  flips=(False, False), prov="test")
    out = enumerate_orders.compare(
        sts, (clause,), subset,
        clause_accepts=restrict.clause_accepts,
        order_to_rel=restrict.order_to_rel)
    assert out["oracle_admits"] == 4 and out["clauses_admit"] == 4, out
    assert set(out["only_oracle"]) == {(1, 0, 7), (7, 0, 1)}, out
    assert set(out["only_clauses"]) == {(0, 7, 1), (1, 7, 0)}, out
    assert out["identical"] is False, out
