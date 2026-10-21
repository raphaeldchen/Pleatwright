"""Unit tests for `lines.py`. Run directly, never via `pytest tests/`.

    cd docs/superpowers/evidence/2026-10-05-cross-section-oracle
    ../../../../.venv/bin/python3 -m pytest test_lines.py -v
"""
import os
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import lines                           # noqa: E402
import pytest                          # noqa: E402
from conftest import assert_import_allowlist   # noqa: E402

F = Fraction


def _seg(x0, y0, x1, y1):
    return ((F(x0), F(y0)), (F(x1), F(y1)))


def test_imports_are_allowlisted():
    """`lines.py` must depend on neither production nor `geom`.

    `geom` is deliberately absent from the allowlist: its `collinear_overlap`
    and `segs_interact` are transcriptions of production, and bundling with
    those would make the bundling common-mode, so a shared defect would make
    both arms miss the same bundles and AGREE SILENTLY.

    The checker lives in `conftest.py` with its own positive control, so this
    test states the allowlist and nothing else.
    """
    assert_import_allowlist(os.path.join(HERE, "lines.py"),
                            allowed=("fractions", "math"))


def test_line_key_equal_for_collinear_segments():
    a = lines.line_key(_seg(0, 0, 2, 0))
    b = lines.line_key(_seg(5, 0, 7, 0))
    c = lines.line_key(_seg(-3, 0, -1, 0))
    assert a == b == c


def test_line_key_differs_for_parallel_offset_lines():
    assert lines.line_key(_seg(0, 0, 2, 0)) != lines.line_key(_seg(0, 1, 2, 1))


def test_line_key_is_direction_sign_invariant():
    """A segment and its reverse are the same line."""
    assert lines.line_key(_seg(0, 0, 3, 1)) == lines.line_key(_seg(3, 1, 0, 0))


def test_line_key_is_scale_invariant():
    """Collinear segments of different lengths share one key, which requires
    the direction to be reduced to lowest terms before the offset is formed."""
    assert lines.line_key(_seg(0, 0, 2, 4)) == lines.line_key(_seg(0, 0, 1, 2))


def test_line_key_handles_fractional_coordinates():
    """Folded box-pleat coordinates are rationals with large denominators.

    The integer reduction must go through the denominators' lcm, not just
    truncate. Two collinear diagonal segments where the denominators' lcm
    differs between them must share a key. Without lcm reduction, direction
    reduction would crash: setting `m = 1` makes `int(Fraction(1,3) * 1)`
    truncate to `0`, so both direction components become zero and `gcd(0, 0)`
    raises ZeroDivisionError. Two other mutations (dropping the `gcd` reduction,
    or taking the lcm over one denominator only) do not crash but produce
    mismatched keys, caught by this fixture.
    """
    # Line: y = (1/3)x, direction (3, 1) in reduced form
    # Segment 1: (0, 0) to (3/7, 1/7), direction (3/7, 1/7)
    # lcm(7, 7) = 7, scales to (3, 1), gcd=1, reduces to (3, 1)
    # Segment 2: (6/7, 2/7) to (2, 2/3), direction (8/7, 8/21)
    # lcm(7, 21) = 21, scales to (24, 8), gcd=8, reduces to (3, 1)
    s1 = ((F(0), F(0)), (F(3, 7), F(1, 7)))
    s2 = ((F(6, 7), F(2, 7)), (F(2), F(2, 3)))
    assert lines.line_key(s1) == lines.line_key(s2)


def test_line_key_none_on_degenerate_segment():
    assert lines.line_key(_seg(2, 2, 2, 2)) is None


def test_direction_of_round_trips():
    k = lines.line_key(_seg(0, 0, 2, 4))
    assert lines.direction_of(k) == (1, 2)


def test_project_is_order_preserving_along_the_line():
    """The `project` function must return strictly increasing values along the
    line direction. If it returned a constant, coordinates would be unordered.
    """
    d = lines.direction_of(lines.line_key(_seg(0, 0, 1, 1)))
    ts = [lines.project(d, (F(t), F(t))) for t in (-2, 0, 1, 5)]
    assert all(a < b for a, b in zip(ts, ts[1:]))


def test_line_key_offset_on_a_diagonal_off_the_origin():
    """The offset term c = dx*y0 - dy*x0 is critical for distinguishing
    parallel lines. Two segments on the same diagonal line with a non-zero
    offset must share a key. A parallel diagonal line at a different offset
    must have a different key.

    MUTATION TEST: This test catches a mutation that computes the offset from
    the raw (unreduced) direction instead of the reduced direction:
    `c = (x1-x0)*y0 - (y1-y0)*x0` instead of `c = dx*y0 - dy*x0`.
    That mutation makes the key depend on segment length, causing segments of
    different lengths on the same line to get different keys, which would split
    one line into multiple bundles and silently under-report overlaps.
    """
    # Line 1: y = 2x + 1, i.e., reduced direction (1, 2) with offset c = 1
    # Unit-step segment: (0, 1) to (1, 3), raw direction (1, 2)
    # Non-unit-step segment: (0, 1) to (2, 5), raw direction (2, 4)
    # Under the mutation: (1,2) gives c = 1*1 - 2*0 = 1
    #                    (2,4) gives c = 2*1 - 4*0 = 2 ← WRONG, different key!
    # These must share a key under the correct implementation.
    seg1_unit_step = ((F(0), F(1)), (F(1), F(3)))
    seg2_nonunit_step = ((F(0), F(1)), (F(2), F(5)))
    seg3_unit_step = ((F(2), F(5)), (F(3), F(7)))

    # Line 2: y = 2x (same slope, different offset)
    # Points: (0, 0) lies on it: c = 1*0 - 2*0 = 0
    # Segment on Line 2: (1, 2) to (2, 4)
    seg1_line2 = ((F(1), F(2)), (F(2), F(4)))

    key1_unit = lines.line_key(seg1_unit_step)
    key2_nonunit = lines.line_key(seg2_nonunit_step)
    key3_unit = lines.line_key(seg3_unit_step)
    key_line2 = lines.line_key(seg1_line2)

    assert key1_unit == key2_nonunit, "Unit-step and non-unit-step on same line should share key"
    assert key1_unit == key3_unit, "Different unit-step segments on same line should share key"
    assert key1_unit != key_line2, "Segments on parallel lines should differ"


def test_span_is_sorted():
    d = (1, 0)
    assert lines.span(d, _seg(5, 0, 1, 0)) == (F(1), F(5))


def test_intervals_overlap_needs_more_than_a_point():
    assert lines.intervals_overlap((F(0), F(2)), (F(1), F(3))) is True
    assert lines.intervals_overlap((F(0), F(1)), (F(1), F(2))) is False
    assert lines.intervals_overlap((F(0), F(1)), (F(2), F(3))) is False


def test_contains_is_closed():
    assert lines.contains((F(0), F(2)), F(0)) is True
    assert lines.contains((F(0), F(2)), F(2)) is True
    assert lines.contains((F(0), F(2)), F(3)) is False


def test_bundles_groups_by_line():
    edges = (
        (0, 1, "M", _seg(0, 0, 2, 0)),
        (2, 3, "V", _seg(1, 0, 3, 0)),
        (4, 5, "M", _seg(0, 1, 2, 1)),
    )
    b = lines.bundles(edges)
    assert len(b) == 2
    sizes = sorted(len(v) for v in b.values())
    assert sizes == [1, 2]


def test_bundles_refuses_a_degenerate_segment():
    """A zero-length folded crease image means the folded state is degenerate.
    The caller must learn that, so it is a refusal and not a silent drop."""
    edges = ((0, 1, "M", _seg(1, 1, 1, 1)),)
    with pytest.raises(ValueError, match="degenerate"):
        lines.bundles(edges)


def test_overlapping_lines_requires_two_creases_that_overlap():
    edges = (
        (0, 1, "M", _seg(0, 0, 2, 0)),      # line A, overlaps the next
        (2, 3, "V", _seg(1, 0, 3, 0)),      # line A
        (4, 5, "M", _seg(0, 1, 1, 1)),      # line B, touches only
        (6, 7, "M", _seg(1, 1, 2, 1)),      # line B
        (8, 9, "M", _seg(0, 2, 1, 2)),      # line C, alone
    )
    b = lines.bundles(edges)
    got = lines.overlapping_lines(b)
    assert got == (lines.line_key(_seg(0, 0, 2, 0)),)


def test_overlapping_lines_ignores_flat_edges_by_default():
    """`kinds` defaults to the creases. A pair of flat edges is a
    tortilla-tortilla configuration, not a taco, so it must not by itself make
    a line count as crease-overlapping."""
    edges = (
        (0, 1, "F", _seg(0, 0, 2, 0)),
        (2, 3, "F", _seg(1, 0, 3, 0)),
    )
    assert lines.overlapping_lines(lines.bundles(edges)) == ()


def test_overlapping_lines_honours_an_explicit_kinds_argument():
    edges = (
        (0, 1, "F", _seg(0, 0, 2, 0)),
        (2, 3, "F", _seg(1, 0, 3, 0)),
    )
    b = lines.bundles(edges)
    assert len(lines.overlapping_lines(b, kinds=("F",))) == 1


def test_overlapping_lines_ignores_flat_in_mixed_bundles():
    """When a line has both M (mountain) and F (flat) edges that overlap,
    the default kinds=("M", "V") ignores the F, so only one crease is present.
    This must not mark the line as crease-overlapping."""
    edges = (
        (0, 1, "M", _seg(0, 0, 2, 0)),      # M edge spans [0, 2]
        (2, 3, "F", _seg(1, 0, 3, 0)),      # F edge spans [1, 3], overlaps M
    )
    b = lines.bundles(edges)
    # With default kinds=("M", "V"), only the M edge counts; no overlap of creases
    assert lines.overlapping_lines(b) == ()
    # With kinds=("M", "F"), both count and they overlap
    assert len(lines.overlapping_lines(b, kinds=("M", "F"))) == 1
