"""Grouping folded edge images into collinear bundles, in exact rationals.

INDEPENDENT BY CONSTRUCTION: this module imports only `fractions` and `math`.

It deliberately does NOT use the transcriptions in `geom.py` --
`collinear_overlap` (`geom.py:359`) and `segs_interact` (`geom.py:379`) are
copies of production's predicates. Bundling with those would make the bundling
common-mode with production: a defect shared by both arms would make them miss
the same bundles and AGREE SILENTLY, which is the worst failure available to a
comparison. The design spec section 2.3 states the whole boundary.

The bundling test here is an EQUALITY on exact rationals, not a tolerance
comparison: two segments lie on one line exactly when their canonical line
keys are equal. There is no epsilon anywhere in this file.
"""
from fractions import Fraction
from math import gcd, lcm


def _integer_direction(dx, dy):
    """`(dx, dy)` as a sign-canonical integer direction in lowest terms.

    Returns None for the zero vector. The reduction has to happen before the
    line offset is formed: scaling a direction scales the offset identically,
    so only the reduced pair is unique per line.
    """
    fx, fy = Fraction(dx), Fraction(dy)
    if fx == 0 and fy == 0:
        return None
    m = lcm(fx.denominator, fy.denominator)
    ix, iy = int(fx * m), int(fy * m)
    g = gcd(abs(ix), abs(iy))
    ix, iy = ix // g, iy // g
    if ix < 0 or (ix == 0 and iy < 0):
        ix, iy = -ix, -iy
    return (ix, iy)


def line_key(seg):
    """A canonical exact identifier for the infinite line through `seg`.

    `(dx, dy, c)` where `(dx, dy)` is the reduced sign-canonical integer
    direction and `c = dx * y0 - dy * x0` is the line's offset in those same
    units. Two segments lie on one line iff their keys are equal.

    Returns None on a zero-length segment -- a caller that needs a refusal
    should raise it; this predicate reports, it does not decide.
    """
    (x0, y0), (x1, y1) = seg
    d = _integer_direction(x1 - x0, y1 - y0)
    if d is None:
        return None
    dx, dy = d
    return (dx, dy, dx * Fraction(y0) - dy * Fraction(x0))


def direction_of(key):
    """The reduced integer direction a `line_key` carries."""
    return (key[0], key[1])


def project(direction, point):
    """`point`'s coordinate along `direction`, as an exact rational.

    This is the dot product with the (unnormalised) direction, so the absolute
    scale is arbitrary. That is harmless and deliberate: every comparison made
    with it is between two projections taken on the SAME line with the SAME
    direction, and the map is strictly order-preserving along that line.
    Avoiding normalisation keeps the value rational.
    """
    dx, dy = direction
    return dx * Fraction(point[0]) + dy * Fraction(point[1])


def span(direction, seg):
    """`seg`'s closed interval `(lo, hi)` along `direction`, with `lo <= hi`."""
    a, b = project(direction, seg[0]), project(direction, seg[1])
    return (a, b) if a <= b else (b, a)


def intervals_overlap(i1, i2):
    """True iff two closed intervals share MORE THAN a single point.

    Strict, matching production's own reading: two segments meeting at one
    endpoint are not an overlap. That degenerate neighbour is recorded as a
    limitation in the design spec section 8.7 rather than handled here.
    """
    return min(i1[1], i2[1]) - max(i1[0], i2[0]) > 0


def contains(interval, t):
    """Closed containment. The endpoints belong to the interval."""
    return interval[0] <= t <= interval[1]


def bundles(edges):
    """`line_key -> tuple of edges on that line`, over every line.

    `edges` holds 4-tuples `(fa, fb, assignment, seg)`. Every line with at
    least one edge appears; filtering to the interesting ones is
    `overlapping_lines`' job, kept separate so each is testable alone.

    A degenerate segment is a REFUSAL, not a drop: a zero-length folded edge
    image means the folded state itself is degenerate, and a caller that
    silently loses the edge would under-report the comparison and call it
    agreement.
    """
    out = {}
    for edge in edges:
        key = line_key(edge[3])
        if key is None:
            raise ValueError(
                f"lines.bundles: edge {edge[0]}-{edge[1]} has a degenerate "
                f"(zero-length) folded segment {edge[3]}. Refusing: a "
                f"zero-length folded edge image means the folded state is "
                f"degenerate, and dropping it would under-report the "
                f"comparison.")
        out.setdefault(key, []).append(edge)
    return {k: tuple(v) for k, v in out.items()}


def overlapping_lines(bundles_map, kinds=("M", "V")):
    """The line keys carrying two edges of `kinds` whose spans overlap.

    Sorted for determinism. `kinds` defaults to the creases, because a pair of
    flat edges is a tortilla-tortilla configuration rather than a taco and
    must not by itself mark a line as crease-overlapping.
    """
    out = []
    for key, edges in bundles_map.items():
        d = direction_of(key)
        spans = [span(d, e[3]) for e in edges if e[2] in kinds]
        found = False
        for i in range(len(spans)):
            for j in range(i + 1, len(spans)):
                if intervals_overlap(spans[i], spans[j]):
                    found = True
                    break
            if found:
                break
        if found:
            out.append(key)
    return tuple(sorted(out))
