"""The perpendicular cross-section of a flat-folded state, and its validity
rule.

INDEPENDENT BY CONSTRUCTION: this module imports only `fractions` and
`lines.py`, which is itself import-free. In particular it does NOT use the
transcriptions in `geom.py`:

  * `side_of` (`geom.py:311`) derives the side from the polygon CENTROID --
    precisely the derivation `side_at` below has to reach independently. Using
    it would make side determination common-mode with production.
  * `clip_seg` (`geom.py:250`) clamps the parameter to [0, 1]. This module
    needs the UNCLAMPED interval of an infinite line, which production has no
    routine for at all -- so `line_clip` is a NEW computation rather than a
    re-transcription, and carries none of the bitwise-fidelity risk that
    justified reusing those transcriptions in the predecessor slice.

The design spec section 2.3 states the full boundary. What remains common-mode
is the input geometry both arms necessarily read.

THE RULE, derived in the cross-section plane with `x` the perpendicular
coordinate and `z` the layer index.

A crease whose folded image passes through the sample point is a U-TURN: an
arc at x = 0 joining its two faces' layers and sweeping every layer between
them. Its two faces lie on the SAME side, because folding over is what a
crease is. Two conditions follow, and nothing else does:

  1. no THROUGH strand may sit strictly between a U-turn's two layers -- the
     arc passes through (0, z) and the through strand already occupies it;
  2. no two U-turns on the SAME side may interleave -- arcs spanning layers
     a < c < b < d cross.

U-turns on OPPOSITE sides bulge opposite ways in x and cannot meet; that is
the geometric content of production's side bookkeeping. A flat (uncreased)
edge on the line is a through strand realized as two faces, one each side, so
it needs no third condition.

A face terminating exactly at the line is a FREE END: its endpoint lies ON the
arc but does not pierce it -- a measure-zero touch rather than a penetration,
which is why production's spanning rule requires strict interiority. That
modelling choice is SHARED with production, so this module does not test it;
design spec section 8.2 records it as a limitation.

SIDE LABELS ARE SIGNS, NOT COMPASS DIRECTIONS. `SIDE_POS` means the face
extends toward +t along the perpendicular `w`, and `SIDE_NEG` toward -t. No
claim is made about which is geometrically left: the rule is symmetric in the
two sides, so the labelling only has to be CONSISTENT, and tying it to the
sign of t makes that automatic.
"""
from fractions import Fraction

import lines

#: Strand classes. The two sides are signs along the perpendicular; THROUGH
#: means the face's interior crosses the line at the sample point.
SIDE_POS = 1
SIDE_NEG = -1
THROUGH = 0


def perpendicular(direction):
    """The exact left-normal of an integer direction. Stays integral."""
    dx, dy = direction
    return (-dy, dx)


def line_clip(poly, p, w):
    """The parametric interval of the infinite line `p + t*w` inside a
    strictly counter-clockwise convex `poly`, as `(t_lo, t_hi)`.

    `None` when the line misses the polygon. `t_lo == t_hi` is a single-point
    touch and is returned as such -- classifying it is `side_at`'s job.

    A half-plane intersection over t in (-inf, inf). For each directed edge
    a -> b of a counter-clockwise ring the interior is
    `cross(b - a, x - a) >= 0`; substituting `x = p + t*w` gives
    `num + t*den >= 0` with

        num = cross(e, p - a),  den = cross(e, w),  e = b - a

    so `den > 0` gives a lower bound on t, `den < 0` an upper bound, and
    `den == 0` (the line parallel to that edge) is satisfiable iff
    `num >= 0`.

    Refuses if either end is still unbounded after the loop. A bounded convex
    ring cannot leave one unbounded, so that reading means the ring is
    degenerate or not convex -- and returning a half-open interval would let a
    caller read it as a side.
    """
    lo = None
    hi = None
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        ex, ey = b[0] - a[0], b[1] - a[1]
        den = ex * w[1] - ey * w[0]
        num = ex * (p[1] - a[1]) - ey * (p[0] - a[0])
        if den == 0:
            if num < 0:
                return None                 # parallel and strictly outside
            continue                        # parallel and inside: no bound
        t = Fraction(-num) / den
        if den > 0:
            lo = t if lo is None else max(lo, t)
        else:
            hi = t if hi is None else min(hi, t)
    if lo is None or hi is None:
        raise ValueError(
            f"strip.line_clip: the line through {p} is unbounded inside this "
            f"polygon ({n} vertices), which a bounded convex ring cannot "
            f"produce -- the ring is degenerate or not convex. Refusing "
            f"rather than returning a half-open interval a caller would read "
            f"as a side.")
    if hi < lo:
        return None
    return (lo, hi)


def side_at(poly, p, w):
    """How `poly` meets the line at `p`: THROUGH, SIDE_POS, SIDE_NEG, or None.

    Read off the sign of the clipped interval, with t = 0 at `p`:

        t_lo < 0 < t_hi  ->  THROUGH    (the interior crosses the line at p)
        t_lo = 0 < t_hi  ->  SIDE_POS
        t_lo < 0 = t_hi  ->  SIDE_NEG
        t_lo = t_hi = 0  ->  a single-point touch: REFUSE
        the interval misses t = 0  ->  None (p is not in this face)

    The single-point case is a refusal and not a guess: a face meeting the
    line in exactly the sample point has no determinable side, and choosing
    one would silently decide a constraint.
    """
    span = line_clip(poly, p, w)
    if span is None:
        return None
    lo, hi = span
    if lo > 0 or hi < 0:
        return None
    if lo == 0 and hi == 0:
        raise ValueError(
            f"strip.side_at: the line meets this polygon in the single point "
            f"{p} itself (t_lo == t_hi == 0), so its side is undetermined. "
            f"Refusing rather than guessing.")
    if lo < 0 and hi > 0:
        return THROUGH
    return SIDE_POS if lo == 0 else SIDE_NEG


def sides_at(polys, faces, p, w):
    """`face -> strand class`, for the faces in `faces` that meet `p`.

    `polys` is a mapping face -> counter-clockwise exact ring. Faces whose
    `side_at` is None are absent from the result rather than present with a
    sentinel, so a caller cannot accidentally treat "not here" as a side.
    """
    out = {}
    for f in faces:
        s = side_at(polys[f], p, w)
        if s is not None:
            out[f] = s
    return out


def edges_at(bundle_edges, direction, t, kinds):
    """The edges of `bundle_edges` with an assignment in `kinds` whose span
    along `direction` contains `t`, closed.

    Closed containment is deliberate: `t` is a sub-segment midpoint, so it
    never coincides with a span endpoint in the driver's use, and keeping the
    test closed means a hand-built test fixture can place `t` on an endpoint
    without the function quietly disagreeing with `lines.contains`.
    """
    return tuple(e for e in bundle_edges if e[2] in kinds
                 and lines.contains(lines.span(direction, e[3]), t))


def uturns_at(crease_edges, sides):
    """`(uturns, anomalies)` for the creases at a sample point.

    A uturn is `(fa, fb, side)`. An anomaly is `(fa, fb, side_a, side_b)`.

    A crease's two faces must lie on the same side and neither may be THROUGH.
    A pair that fails this is REPORTED, never silently dropped: production
    skips such a pair, and a silent skip here would hide a disagreement about
    which pairs are interpretable at all. The driver gates on the anomaly
    count so the quantity is measured rather than assumed.
    """
    uturns = []
    anomalies = []
    for edge in crease_edges:
        fa, fb = edge[0], edge[1]
        sa, sb = sides.get(fa), sides.get(fb)
        if sa is None or sb is None or sa == THROUGH or sb == THROUGH \
                or sa != sb:
            anomalies.append((fa, fb, sa, sb))
            continue
        uturns.append((fa, fb, sa))
    return tuple(uturns), tuple(anomalies)


def taco_pairs(uturns):
    """Condition 2's constraint OBJECTS -- the constraints the geometry
    IMPOSES, not the ones a given order violates.

    One canonical element per unordered pair of distinct same-side U-turns:

        frozenset({frozenset({fa1, fb1}), frozenset({fa2, fb2})})

    Order-free, which is why the comparison in design spec section 3 needs no
    candidate layer order at all -- and why it cannot go vacuous the way the
    predecessor's subset design did.
    """
    out = set()
    n = len(uturns)
    for i in range(n):
        for j in range(i + 1, n):
            if uturns[i][2] != uturns[j][2]:
                continue                   # opposite sides: arcs cannot meet
            k1 = frozenset((uturns[i][0], uturns[i][1]))
            k2 = frozenset((uturns[j][0], uturns[j][1]))
            if k1 == k2:
                continue
            out.add(frozenset((k1, k2)))
    return out


def pierce_pairs(uturns, sides):
    """Condition 1's constraint objects, in the predecessor's own triple shape
    `(through_face, frozenset({fa, fb}))`.

    Also order-free. The driver uses this for the cross-validation gate: these
    must reproduce the predecessor oracle's `equality` triples on the same
    creases, which makes the new instrument prove itself against an
    already-established result before its condition-2 verdict is believed.
    """
    out = set()
    through = [f for f, s in sides.items() if s == THROUGH]
    for fa, fb, _side in uturns:
        pair = frozenset((fa, fb))
        for f in through:
            if f in pair:
                continue
            out.add((f, pair))
    return out


def pierced(uturn, sides, order):
    """Condition 1 against an order: the THROUGH faces strictly between a
    U-turn's two layers, sorted.

    `order` maps face -> layer index. Only BETWEENNESS is read, so which
    direction the index counts in is irrelevant.
    """
    fa, fb, _side = uturn
    lo, hi = sorted((order[fa], order[fb]))
    return tuple(sorted(f for f, s in sides.items()
                        if s == THROUGH and f not in (fa, fb)
                        and lo < order[f] < hi))


def interleaved(u1, u2, order):
    """Condition 2 against an order: do two U-turns' arcs cross?

    Arcs spanning layers a < c < b < d interleave. Opposite sides are False by
    the rule above. A shared layer reads False, which is the conservative
    direction: a shared layer is a contact, not a crossing.
    """
    if u1[2] != u2[2]:
        return False
    a, b = sorted((order[u1[0]], order[u1[1]]))
    c, d = sorted((order[u2[0]], order[u2[1]]))
    return (a < c < b < d) or (c < a < d < b)


def accepts(sides, uturns, order):
    """Both conditions at one sample point. The violations, empty iff valid.

    Each violation is `("pierced", frozenset({fa, fb}), through_face)` or
    `("interleaved", frozenset({fa, fb}), frozenset({fc, fd}))`.
    """
    out = []
    for u in uturns:
        for f in pierced(u, sides, order):
            out.append(("pierced", frozenset((u[0], u[1])), f))
    n = len(uturns)
    for i in range(n):
        for j in range(i + 1, n):
            if interleaved(uturns[i], uturns[j], order):
                out.append(("interleaved",
                            frozenset((uturns[i][0], uturns[i][1])),
                            frozenset((uturns[j][0], uturns[j][1]))))
    return tuple(out)


def breakpoints(intervals):
    """The sorted, de-duplicated boundaries of a collection of intervals.

    These are the only projections along a line at which the configuration can
    change: between two consecutive boundaries no span starts or ends, so both
    the set of edges containing the point and the set of faces meeting it are
    constant.
    """
    vals = set()
    for lo, hi in intervals:
        vals.add(lo)
        vals.add(hi)
    return tuple(sorted(vals))


def sub_segment_samples(bps):
    """One exact rational midpoint per open sub-segment between consecutive
    breakpoints.

    EXHAUSTIVE BY CONSTRUCTION, which is the whole reason there is no
    sampling-density parameter anywhere in this slice: no configuration change
    can occur strictly inside a sub-segment, so one sample decides all of it.
    """
    return tuple((bps[i] + bps[i + 1]) / 2 for i in range(len(bps) - 1))


def point_at(direction, anchor, t):
    """The point on `anchor`'s line whose projection along `direction` is `t`.

    `lines.project` is the dot product with `direction`, so moving by
    `s * direction` changes the projection by `s * (dx^2 + dy^2)`. Hence from
    `anchor`, whose projection is `t0`, the point at `t` is
    `anchor + ((t - t0) / (dx^2 + dy^2)) * direction`.
    """
    dx, dy = direction
    t0 = lines.project(direction, anchor)
    s = Fraction(t - t0) / (dx * dx + dy * dy)
    return (Fraction(anchor[0]) + s * dx, Fraction(anchor[1]) + s * dy)
