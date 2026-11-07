"""Exact geometry of one Pythagorean-stretch gadget (a GOPS), in rationals.

A Pythagorean stretch resolves a diagonal flap-flap overlap whose circles
touch (sx^2 + sy^2 >= d^2) although their squares do not, by a tilted
parallelogram "piece" whose axis is a Pythagorean triple (3-4-5 at its
smallest).  This module is pure geometry: it knows nothing of the packer, the
tiling or the crease pattern.  It is a port of BP Studio's GOPS, read at
MuTsunTsai/box-pleating-studio commit 0496ad070ba4f4aeba3a018fd3b70e8213797aa1
(MIT licence), as text only:

* `src/core/math/gops.ts` -- the search: for an overlap ox x oy of even area,
  u runs down from floor(sqrt(ox*oy/2)) and each divisor pair gives (u, v) and
  (v, u), the lower Kamiya rank first (`gops`, `rank`).
* `src/core/design/layout/pattern/piece.ts` -- the four corners
  (0,0), (u,ox+u), (oy+u+v,ox+u+v), (oy+v,v), clockwise from the lower left,
  and the axis-parallel direction (oy(ox+u), ox(oy+v)) (`piece`, `axis`).
* `src/core/design/layout/junction/junction.ts` -- the validity test and the
  sign vector (`junction`).
* `src/core/design/layout/pattern/positioners/singleJunctionPositioner.ts` --
  a lone GOPS is centred: offset = floor((sx - width) / 2) (`junction`).

Every GOPS axis is a Pythagorean triple: with a = oy(ox+u), b = ox(oy+v) and
c = ox*oy + oy*u + ox*v, a^2 + b^2 - c^2 = ox*oy*(ox*oy - 2uv), which vanishes
exactly when uv = ox*oy/2, the half-area factorisation `gops` enumerates.

Departures from BP Studio, all recorded here:

* `gops` returns BP Studio's order stably sorted by (rank, span).  gops.ts
  already orders each divisor pair by rank and span never decreases along its
  search, but its list is not globally rank-sorted; callers here want the
  lowest-rank piece first.
* A ridge has the slope of an arbitrary box-pleat gadget edge (3 and 1/2 in the
  minimal example), so a `Line` (exact2d.py) need not have a Pythagorean
  normal.  Only `h`, `dist` and `along`, which need sqrt(a^2 + b^2), raise
  ValueError then.
* `junction` ignores the leaf lengths: like BP Studio's `createJunction`, the
  geometry depends only on the tree distance d.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import gcd, isqrt

from .exact2d import Q2, Line, primitive, sign


def reflect(line: Line, mirror: Line) -> Line:
    """The reflection of `line` across `mirror`, exactly (the hinge-tracing
    step).  A tested geometric API (tests/test_stretch.py); the pipeline does
    not use it (`kamiya` builds its gadget lines directly)."""
    ma, mb, mc = mirror.a, mirror.b, mirror.c
    mm = Fraction(ma * ma + mb * mb)

    def mirror_point(x: Fraction, y: Fraction) -> Q2:
        t = 2 * (ma * x + mb * y - mc) / mm
        return x - t * ma, y - t * mb

    # A point of `line`, and its normal reflected as a vector (a linear map).
    n2 = line.a * line.a + line.b * line.b
    px, py = Fraction(line.a) * line.c / n2, Fraction(line.b) * line.c / n2
    dot = 2 * (ma * line.a + mb * line.b) / mm
    a, b = primitive(line.a - dot * ma, line.b - dot * mb)
    qx, qy = mirror_point(px, py)
    return Line(a, b, a * qx + b * qy)


@dataclass(frozen=True)
class Gops:
    """One GOPS piece of an ox x oy overlap: u*v = ox*oy/2."""

    u: int
    v: int
    rank: int   # Kamiya rank; the lower the better (3 at the very best)
    span: int   # u + v + oy, the width of the piece


def _rank(ox: int, oy: int, u: int, v: int) -> int:
    """gops.ts `rank`: the larger reduced numerator of (oy+v)/oy and (ox+u)/ox."""
    n1, n2 = oy + v, ox + u
    return max(n1 // gcd(n1, oy), n2 // gcd(n2, ox))


def gops(ox: int, oy: int) -> list[Gops]:
    """Every GOPS of an ox x oy overlap, lowest rank first (then narrowest).

    Empty when ox and oy are both odd (odd area has no half-area factorisation)."""
    if ox <= 0 or oy <= 0 or (ox % 2 and oy % 2):
        return []
    half = ox * oy // 2
    found: list[Gops] = []
    for u in range(isqrt(half), 0, -1):
        if half % u:
            continue
        v = half // u
        pair = [(u, v)] if u == v else [(u, v), (v, u)]
        pair = [Gops(p, q, _rank(ox, oy, p, q), oy + p + q) for p, q in pair]
        if len(pair) == 2 and pair[0].rank > pair[1].rank:
            pair.reverse()
        found.extend(pair)
    return sorted(found, key=lambda g: (g.rank, g.span))


def piece(ox: int, oy: int, u: int, v: int) -> list[Q2]:
    """The corners of the piece, clockwise from the lower left (piece.ts `_points`)."""
    pts = [(0, 0), (u, ox + u), (oy + u + v, ox + u + v), (oy + v, v)]
    return [(Fraction(x), Fraction(y)) for x, y in pts]


def axis(ox: int, oy: int, u: int, v: int) -> tuple[int, int, int]:
    """The axis-parallel direction (a, b) and its length c: a^2 + b^2 = c^2."""
    return oy * (ox + u), ox * (oy + v), ox * oy + oy * u + ox * v


@dataclass
class Junction:
    """A valid diagonal junction resolved by one lone GOPS (lowest rank)."""

    tip_a: Q2
    tip_b: Q2
    d: int
    ox: int
    oy: int
    g: Gops
    corners: list[Q2]       # the piece's corners in sheet coordinates
    ridges: list[Line]      # ridges[i] joins corners[i] to corners[i + 1]
    axis: Line              # the axis-parallel pleat through corners[0]


def junction(tip_a: Q2, L_a: int, tip_b: Q2, L_b: int, d: int) -> Junction | None:
    """Resolve the overlap of flaps A and B (tip-to-tip tree distance d) or None.

    Valid per junction.ts when the tips are offset diagonally by integers
    1 <= sx, sy < d with sx^2 + sy^2 >= d^2; a gadget also needs an overlap of
    even area, and room: the piece must be no wider than sx (gops.ts's `sx`
    filter).  The lowest-rank piece is slid floor((sx - width) / 2) along the
    45-degree diagonal from tip A and mirrored by the sign vector of B - A.
    `L_a` and `L_b` are accepted for the caller's convenience; as in BP Studio
    only d matters.
    """
    dx, dy = tip_b[0] - tip_a[0], tip_b[1] - tip_a[1]
    if dx.denominator != 1 or dy.denominator != 1:
        return None
    sx, sy = abs(int(dx)), abs(int(dy))
    if sx < 1 or sy < 1 or max(sx, sy) >= d or sx * sx + sy * sy < d * d:
        return None
    ox, oy = d - sx, d - sy
    fits = [g for g in gops(ox, oy) if g.span <= sx]
    if not fits:
        return None
    g = fits[0]
    off = (sx - g.span) // 2
    fx, fy = sign(dx), sign(dy)
    corners = [
        (tip_a[0] + fx * (x + off), tip_a[1] + fy * (y + off))
        for x, y in piece(ox, oy, g.u, g.v)
    ]
    ridges = [Line.through(corners[i], corners[(i + 1) % 4]) for i in range(4)]
    a, b, _ = axis(ox, oy, g.u, g.v)
    along = (corners[0][0] + fx * a, corners[0][1] + fy * b)
    return Junction(tip_a, tip_b, d, ox, oy, g, corners, ridges,
                    Line.through(corners[0], along))
