"""Unit tests for `strip.py`. Run directly, never via `pytest tests/`.

    cd docs/superpowers/evidence/2026-10-05-cross-section-oracle
    ../../../../.venv/bin/python3 -m pytest test_strip.py -v
"""
import os
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import lines                           # noqa: E402
import pytest                          # noqa: E402
import strip                           # noqa: E402
from conftest import assert_import_allowlist   # noqa: E402

F = Fraction

#: The x axis, as a bundle direction and its perpendicular.
XDIR = (1, 0)
XPERP = strip.perpendicular(XDIR)       # (0, 1)


def _ccw_rect(x0, y0, x1, y1):
    """A strictly counter-clockwise axis-aligned rectangle, exact."""
    return [(F(x0), F(y0)), (F(x1), F(y0)), (F(x1), F(y1)), (F(x0), F(y1))]


def test_imports_are_allowlisted():
    """`strip.py` must depend on neither production nor `geom`.

    `side_of` (`geom.py:311`) derives the side from the polygon CENTROID,
    which is exactly the derivation `side_at` has to reach independently, and
    `clip_seg` (`geom.py:250`) clamps to [0, 1] where this module needs the
    unclamped interval of an infinite line. Importing either would make the
    oracle's side determination common-mode with production.

    The checker lives in `conftest.py` with its own positive control.
    """
    assert_import_allowlist(os.path.join(HERE, "strip.py"),
                            allowed=("fractions", "lines"))


def test_perpendicular_is_the_left_normal():
    assert strip.perpendicular((1, 0)) == (0, 1)
    assert strip.perpendicular((0, 1)) == (-1, 0)
    assert strip.perpendicular((2, 3)) == (-3, 2)


def test_line_clip_through_a_rectangle():
    """The vertical line x = 1 crosses the rectangle y in [-2, 3]."""
    poly = _ccw_rect(0, -2, 4, 3)
    got = strip.line_clip(poly, (F(1), F(0)), XPERP)
    assert got == (F(-2), F(3))


def test_line_clip_misses_a_rectangle():
    poly = _ccw_rect(0, -2, 4, 3)
    assert strip.line_clip(poly, (F(9), F(0)), XPERP) is None


def test_line_clip_is_one_sided_for_a_face_above_the_line():
    """A face sitting entirely above y = 0 clips to a span with lo == 0."""
    poly = _ccw_rect(0, 0, 4, 5)
    assert strip.line_clip(poly, (F(1), F(0)), XPERP) == (F(0), F(5))


def test_line_clip_refuses_an_unbounded_reading():
    """A degenerate ring can leave an end unbounded; a bounded convex polygon
    cannot, so that is a refusal rather than a half-open interval a caller
    would misread as a side.

    A ONE-VERTEX ring is the real case. Its single zero-length edge gives
    `den == 0` and `num == 0`, which the parallel-and-inside branch skips, so
    neither end is ever bounded. (A two-point "ring" does NOT work: both its
    edges bound t and the clip returns (0, 0) -- a single-point touch, not an
    unbounded reading.)
    """
    degenerate = [(F(0), F(0))]                    # one vertex: not a ring
    with pytest.raises(ValueError, match="unbounded"):
        strip.line_clip(degenerate, (F(0), F(0)), XPERP)


def test_side_at_reads_through_pos_neg():
    p = (F(1), F(0))
    assert strip.side_at(_ccw_rect(0, -2, 4, 3), p, XPERP) == strip.THROUGH
    assert strip.side_at(_ccw_rect(0, 0, 4, 5), p, XPERP) == strip.SIDE_POS
    assert strip.side_at(_ccw_rect(0, -5, 4, 0), p, XPERP) == strip.SIDE_NEG


def test_side_at_none_when_the_point_is_outside():
    assert strip.side_at(_ccw_rect(5, 0, 9, 5), (F(1), F(0)), XPERP) is None


def test_side_at_none_when_span_misses_zero_on_positive_side():
    """GAP 1: a face entirely on the +t side of the sample point.

    The perpendicular line passes through the face (line_clip returns a valid
    span), but the sample point lies OUTSIDE the face's span along the
    perpendicular. This branch distinguishes "the point is not on this face"
    (return None) from "the face touches the line only at the point" (raise).
    Conflating them would turn a correct refusal into a silent, invented strand.

    The rectangle (0, 2, 4, 5) crosses the perpendicular line x = 1 with span
    from y = 2 to y = 5. The sample point (1, 0) is at t = -2 (below y = 0),
    so lo = -2, hi = 5, and lo < 0. But we also test the hi < 0 case separately.
    Here, because the face sits at y in [2, 5] and we sample at y = 0, the span
    is entirely above the sample point -- wait, actually that's not right. Let me
    reconsider: the perpendicular at p = (F(1), F(0)) with direction XPERP = (0, 1)
    means the line is vertical at x = 1. The span is the y-interval where the
    line intersects the face. For _ccw_rect(0, 2, 4, 5), that's y in [2, 5].
    Since the sample point is at y = 0 and the span is [2, 5], we have
    lo = 2, hi = 5, so lo > 0. This is the positive-side case.
    """
    poly = _ccw_rect(0, 2, 4, 5)
    span = strip.line_clip(poly, (F(1), F(0)), XPERP)
    assert span == (F(2), F(5)), f"Expected span (2, 5), got {span}"
    # The span does not include t = 0, so side_at should return None
    assert strip.side_at(poly, (F(1), F(0)), XPERP) is None


def test_side_at_none_when_span_misses_zero_on_negative_side():
    """GAP 1: a face entirely on the -t side of the sample point.

    Similar to the positive case, but the face sits entirely on the -t side.
    For _ccw_rect(0, -5, 4, -2), the perpendicular line x = 1 intersects it
    at y in [-5, -2]. The sample point is at y = 0, so the span is entirely
    below: lo = -5, hi = -2, and hi < 0. This triggers the hi < 0 branch.
    """
    poly = _ccw_rect(0, -5, 4, -2)
    span = strip.line_clip(poly, (F(1), F(0)), XPERP)
    assert span == (F(-5), F(-2)), f"Expected span (-5, -2), got {span}"
    # The span does not include t = 0, so side_at should return None
    assert strip.side_at(poly, (F(1), F(0)), XPERP) is None


def test_side_at_refuses_a_single_point_touch():
    """A face meeting the line only at p itself has no determinable side.

    The triangle must be TANGENT to the perpendicular at p -- entirely in
    x >= 1, touching x = 1 only at the vertex (1, 0). A triangle the
    perpendicular crosses would read SIDE_POS instead, and the test would pass
    for the wrong reason.
    """
    triangle = [(F(1), F(0)), (F(3), F(-1)), (F(3), F(1))]   # CCW, tangent
    with pytest.raises(ValueError, match="single point"):
        strip.side_at(triangle, (F(1), F(0)), XPERP)


def test_sides_at_collects_only_the_faces_that_meet_the_point():
    polys = {
        7: _ccw_rect(0, -2, 4, 3),      # through
        8: _ccw_rect(0, 0, 4, 5),       # pos
        9: _ccw_rect(5, 0, 9, 5),       # off the point entirely
    }
    got = strip.sides_at(polys, (7, 8, 9), (F(1), F(0)), XPERP)
    assert got == {7: strip.THROUGH, 8: strip.SIDE_POS}


def test_edges_at_selects_by_closed_span_containment():
    edges = (
        (0, 1, "M", ((F(0), F(0)), (F(2), F(0)))),
        (2, 3, "M", ((F(5), F(0)), (F(7), F(0)))),
        (4, 5, "F", ((F(0), F(0)), (F(2), F(0)))),
    )
    got = strip.edges_at(edges, XDIR, F(1), ("M", "V"))
    assert tuple(e[:2] for e in got) == ((0, 1),)


def test_uturns_at_pairs_same_side_faces():
    sides = {0: strip.SIDE_POS, 1: strip.SIDE_POS}
    edges = ((0, 1, "M", ((F(0), F(0)), (F(2), F(0)))),)
    uturns, anomalies = strip.uturns_at(edges, sides)
    assert uturns == ((0, 1, strip.SIDE_POS),)
    assert anomalies == ()


def test_uturns_at_reports_an_opposite_side_crease_as_an_anomaly():
    """A crease's two faces lie on the SAME side -- that is what folding over
    is. An opposite-side reading is reported, never silently dropped: a silent
    drop would hide a disagreement about which pairs are interpretable."""
    sides = {0: strip.SIDE_POS, 1: strip.SIDE_NEG}
    edges = ((0, 1, "M", ((F(0), F(0)), (F(2), F(0)))),)
    uturns, anomalies = strip.uturns_at(edges, sides)
    assert uturns == ()
    assert anomalies == ((0, 1, strip.SIDE_POS, strip.SIDE_NEG),)


def test_uturns_at_reports_a_through_face_as_an_anomaly():
    sides = {0: strip.THROUGH, 1: strip.SIDE_POS}
    edges = ((0, 1, "M", ((F(0), F(0)), (F(2), F(0)))),)
    uturns, anomalies = strip.uturns_at(edges, sides)
    assert uturns == () and len(anomalies) == 1


def test_taco_pairs_emits_one_object_per_same_side_pair():
    uturns = ((0, 1, strip.SIDE_POS), (2, 3, strip.SIDE_POS))
    got = strip.taco_pairs(uturns)
    assert got == {frozenset((frozenset((0, 1)), frozenset((2, 3))))}


def test_taco_pairs_skips_opposite_side_pairs():
    """Arcs on opposite sides bulge opposite ways in x and cannot meet. This
    is the geometric content of production's side bookkeeping, and the
    pre-registered prediction of design spec section 6 rests on it."""
    uturns = ((0, 1, strip.SIDE_POS), (2, 3, strip.SIDE_NEG))
    assert strip.taco_pairs(uturns) == set()


def test_taco_pairs_is_invariant_under_uturn_permutation():
    """The emission depends on geometry alone, not the order of the U-turns.

    This tests permutation-invariance of the constraint OBJECTS themselves.
    The deeper order-freedom guarantee is structural: taco_pairs takes no
    `order` parameter at all, so it cannot depend on any layer ordering."""
    a = strip.taco_pairs(((0, 1, strip.SIDE_POS), (2, 3, strip.SIDE_POS)))
    b = strip.taco_pairs(((2, 3, strip.SIDE_POS), (0, 1, strip.SIDE_POS)))
    assert a == b


def test_pierce_pairs_emits_through_face_against_crease():
    uturns = ((0, 1, strip.SIDE_POS),)
    sides = {0: strip.SIDE_POS, 1: strip.SIDE_POS, 5: strip.THROUGH}
    assert strip.pierce_pairs(uturns, sides) == {(5, frozenset((0, 1)))}


def test_pierce_pairs_ignores_non_through_strands():
    uturns = ((0, 1, strip.SIDE_POS),)
    sides = {0: strip.SIDE_POS, 1: strip.SIDE_POS, 5: strip.SIDE_NEG}
    assert strip.pierce_pairs(uturns, sides) == set()


def test_pierced_finds_a_through_strand_between_the_layers():
    order = {0: 0, 5: 1, 1: 2}
    sides = {0: strip.SIDE_POS, 1: strip.SIDE_POS, 5: strip.THROUGH}
    assert strip.pierced((0, 1, strip.SIDE_POS), sides, order) == (5,)


def test_pierced_ignores_a_through_strand_outside_the_layers():
    order = {0: 0, 1: 1, 5: 2}
    sides = {0: strip.SIDE_POS, 1: strip.SIDE_POS, 5: strip.THROUGH}
    assert strip.pierced((0, 1, strip.SIDE_POS), sides, order) == ()


def test_interleaved_detects_crossing_arcs():
    order = {0: 0, 2: 1, 1: 2, 3: 3}          # a < c < b < d
    assert strip.interleaved((0, 1, strip.SIDE_POS),
                             (2, 3, strip.SIDE_POS), order) is True


def test_interleaved_accepts_nested_arcs():
    """A nested pleat is valid -- this is the configuration that has no thick
    realization at all, which is why the thickened route was refuted."""
    order = {0: 0, 2: 1, 3: 2, 1: 3}          # a < c < d < b
    assert strip.interleaved((0, 1, strip.SIDE_POS),
                             (2, 3, strip.SIDE_POS), order) is False


def test_interleaved_accepts_disjoint_arcs():
    order = {0: 0, 1: 1, 2: 2, 3: 3}
    assert strip.interleaved((0, 1, strip.SIDE_POS),
                             (2, 3, strip.SIDE_POS), order) is False


def test_interleaved_is_false_across_sides():
    order = {0: 0, 2: 1, 1: 2, 3: 3}
    assert strip.interleaved((0, 1, strip.SIDE_POS),
                             (2, 3, strip.SIDE_NEG), order) is False


def test_interleaved_is_symmetric_in_uturn_arguments():
    """GAP 2: the second disjunct (c < a < d < b) is untested.

    The interleaved predicate has two disjuncts: (a < c < b < d) or
    (c < a < d < b). All existing tests pass the U-turns in one order
    (i < j in accepts), so only the first disjunct fires. This test verifies
    that calling interleaved with the arguments reversed also detects the
    crossing, exercising the second disjunct. This is critical because a
    mutant deleting the second disjunct would drop a genuine same-side
    crossing, losing a constraint, which in the oracle's comparison reads as
    agreement -- a silent, structural failure.
    """
    # Use the same crossing configuration as test_interleaved_detects_crossing_arcs
    order = {0: 0, 2: 1, 1: 2, 3: 3}  # a < c < b < d (0 < 2 < 1 < 3)
    u1 = (0, 1, strip.SIDE_POS)
    u2 = (2, 3, strip.SIDE_POS)
    # Forward: u1 first, u2 second -> (a < c < b < d)
    assert strip.interleaved(u1, u2, order) is True
    # Reverse: u2 first, u1 second -> (c < a < d < b)
    assert strip.interleaved(u2, u1, order) is True


def test_accepts_is_empty_on_a_valid_nested_strip():
    order = {0: 0, 2: 1, 3: 2, 1: 3}
    sides = {f: strip.SIDE_POS for f in (0, 1, 2, 3)}
    uturns = ((0, 1, strip.SIDE_POS), (2, 3, strip.SIDE_POS))
    assert strip.accepts(sides, uturns, order) == ()


def test_accepts_reports_an_interleaving():
    order = {0: 0, 2: 1, 1: 2, 3: 3}
    sides = {f: strip.SIDE_POS for f in (0, 1, 2, 3)}
    uturns = ((0, 1, strip.SIDE_POS), (2, 3, strip.SIDE_POS))
    v = strip.accepts(sides, uturns, order)
    assert len(v) == 1 and v[0][0] == "interleaved"


def test_accepts_reports_a_pierce():
    order = {0: 0, 5: 1, 1: 2}
    sides = {0: strip.SIDE_POS, 1: strip.SIDE_POS, 5: strip.THROUGH}
    v = strip.accepts(sides, ((0, 1, strip.SIDE_POS),), order)
    assert len(v) == 1 and v[0][0] == "pierced"


def test_accepts_reports_interleaving_with_reversed_uturn_order():
    """GAP 2: the second disjunct (c < a < d < b) is tested in accepts.

    The accepts function iterates U-turn pairs with i < j, so each pair is
    tested in a fixed order. This test reverses the pair ordering in the
    input uturns tuple to verify the crossing is still detected. This
    exercises the second disjunct of interleaved and proves that a mutant
    deleting it would lose a genuine same-side crossing -- a constraint loss
    that reads as agreement in the comparison, making it a critical gap.
    """
    order = {0: 0, 2: 1, 1: 2, 3: 3}  # a < c < b < d (0 < 2 < 1 < 3)
    sides = {f: strip.SIDE_POS for f in (0, 1, 2, 3)}
    # Forward order: ((0, 1), (2, 3))
    v_forward = strip.accepts(sides, ((0, 1, strip.SIDE_POS), (2, 3, strip.SIDE_POS)), order)
    assert len(v_forward) == 1 and v_forward[0][0] == "interleaved"

    # Reversed order: ((2, 3), (0, 1)) - puts the second pair first
    v_reversed = strip.accepts(sides, ((2, 3, strip.SIDE_POS), (0, 1, strip.SIDE_POS)), order)
    assert len(v_reversed) == 1 and v_reversed[0][0] == "interleaved"


def test_breakpoints_are_sorted_and_deduplicated():
    got = strip.breakpoints([(F(2), F(5)), (F(0), F(2)), (F(0), F(5))])
    assert got == (F(0), F(2), F(5))


def test_sub_segment_samples_land_strictly_inside():
    bps = (F(0), F(2), F(5))
    got = strip.sub_segment_samples(bps)
    assert got == (F(1), F(7, 2))
    for i, t in enumerate(got):
        assert bps[i] < t < bps[i + 1]


def test_sub_segment_samples_empty_for_fewer_than_two_breakpoints():
    assert strip.sub_segment_samples((F(3),)) == ()
    assert strip.sub_segment_samples(()) == ()


def test_point_at_round_trips_through_project():
    d = (1, 2)
    anchor = (F(1), F(1))
    for t in (F(-3), F(0), F(5, 7)):
        p = strip.point_at(d, anchor, t)
        assert lines.project(d, p) == t


def test_point_at_stays_on_the_line():
    d = lines.direction_of(lines.line_key(((F(0), F(0)), (F(2), F(4)))))
    anchor = (F(0), F(0))
    p = strip.point_at(d, anchor, F(5))
    assert lines.line_key((anchor, p)) == lines.line_key(
        ((F(0), F(0)), (F(2), F(4))))
