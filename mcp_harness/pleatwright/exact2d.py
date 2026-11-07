"""Exact 2-D geometry in rationals: lines, convex polygons, distances.

Shared by the Pythagorean-stretch code (`stretch.py`, `kamiya.py`) and the
builders that read its layouts (`base.py`, `efficiency.py`).  Every function is
exact (`fractions.Fraction`) and knows nothing of regions, layouts or flaps.

* `Line` is {a*x + b*y = c} with a primitive integer normal; `canon` makes one
  from any integral normal.  A ridge has the slope of an arbitrary box-pleat
  gadget edge (3 and 1/2 in the minimal example), so a `Line` need not have a
  Pythagorean normal; only `h`, `dist` and `along`, which need
  sqrt(a^2 + b^2), raise ValueError then.
* `line_list` / `line_of` and `poly_list` / `poly_of` convert to and from the
  JSON-safe entries of `Region.lines` and `Region.pieces` (pack.py).
* Polygons are vertex lists; `halves`, `cut` and `clip_le` split convex ones by
  a line, `merge` rejoins neighbours whose union stays convex.
* `elev` and `cut_lines` work on a list `fs` of (Line, |normal|): the distance
  to the nearest line, and every line where that distance can bend.
* `set_dist` and `disjoint` compare two convex sets.
"""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from fractions import Fraction
from math import gcd, isqrt

F = Fraction
Q2 = tuple[Fraction, Fraction]


def sign(x) -> int:
    return (x > 0) - (x < 0)


def primitive(x: Fraction, y: Fraction) -> tuple[int, int]:
    """The shortest integer vector in the direction of (x, y), same orientation."""
    den = x.denominator * y.denominator // gcd(x.denominator, y.denominator)
    ix, iy = int(x * den), int(y * den)
    g = gcd(ix, iy)
    return ix // g, iy // g


@dataclass(frozen=True)
class Line:
    """The line {a*x + b*y = c}, with (a, b) a primitive integer normal."""

    a: int
    b: int
    c: Fraction

    @property
    def h(self) -> int:
        """sqrt(a^2 + b^2); only defined for a Pythagorean normal."""
        s = self.a * self.a + self.b * self.b
        r = isqrt(s)
        if r * r != s:
            raise ValueError(f"normal ({self.a}, {self.b}) is not Pythagorean")
        return r

    def side(self, p: Q2) -> int:
        """Which side of the line p is on: the sign of a*x + b*y - c."""
        return sign(self.a * p[0] + self.b * p[1] - self.c)

    def dist(self, p: Q2) -> Fraction:
        """The Euclidean distance from p to the line (non-negative)."""
        return abs(self.a * p[0] + self.b * p[1] - self.c) / self.h

    def along(self, p: Q2) -> Fraction:
        """The coordinate of p along the line, (-b*x + a*y) / h."""
        return (-self.b * p[0] + self.a * p[1]) / self.h

    @staticmethod
    def through(p: Q2, q: Q2) -> "Line":
        """The line through two distinct points, normal (dy, -dx) made primitive."""
        dx, dy = q[0] - p[0], q[1] - p[1]
        if dx == 0 and dy == 0:
            raise ValueError("a line needs two distinct points")
        a, b = primitive(dy, -dx)
        return Line(a, b, a * p[0] + b * p[1])


def canon(a, b, c) -> Line:
    """The line a*x + b*y = c with a primitive normal, a > 0 (or a == 0 < b).
    The normal (a, b) must be integral (ValueError otherwise, never truncated)."""
    if F(a).denominator != 1 or F(b).denominator != 1:
        raise ValueError(f"line normal ({a}, {b}) is not integral")
    a, b = int(a), int(b)
    g = math.gcd(a, b)
    if g == 0:
        raise ValueError("degenerate line")
    a, b, c = a // g, b // g, F(c) / g
    if a < 0 or (a == 0 and b < 0):
        a, b, c = -a, -b, -c
    return Line(a, b, c)


def line_list(ln: Line) -> list:
    """`Region.lines` entry [a, b, c_num, c_den] of a line (canonical)."""
    ln = canon(ln.a, ln.b, ln.c)
    return [ln.a, ln.b, ln.c.numerator, ln.c.denominator]


def line_of(entry) -> Line:
    a, b, cn, cd = entry
    return Line(a, b, F(cn, cd))


def poly_list(poly) -> list:
    """`Region.pieces` entry [[x_num, x_den, y_num, y_den], ...] of a polygon."""
    return [[F(x).numerator, F(x).denominator, F(y).numerator, F(y).denominator]
            for x, y in poly]


def poly_of(entry) -> list:
    return [(F(xn, xd), F(yn, yd)) for xn, xd, yn, yd in entry]


def val(ln, p):
    return ln.a * p[0] + ln.b * p[1] - ln.c


def area2(poly) -> Fraction:
    s = F(0)
    for i in range(len(poly)):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % len(poly)]
        s += x0 * y1 - x1 * y0
    return s


def ccw(poly) -> list:
    return poly if area2(poly) >= 0 else poly[::-1]


def _dedupe(pts) -> list:
    out = []
    for p in pts:
        if not out or out[-1] != p:
            out.append(p)
    while len(out) > 1 and out[0] == out[-1]:
        out.pop()
    return out


def halves(poly, ln):
    """(part with val <= 0, part with val >= 0) of a convex polygon, closed."""
    neg, pos = [], []
    n = len(poly)
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        vp, vq = val(ln, p), val(ln, q)
        if vp <= 0:
            neg.append(p)
        if vp >= 0:
            pos.append(p)
        if (vp < 0 < vq) or (vq < 0 < vp):
            t = vp / (vp - vq)
            x = (p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1]))
            neg.append(x)
            pos.append(x)
    return _dedupe(neg), _dedupe(pos)


def cut(polys, ln) -> list:
    """Split every polygon by a line; keep the parts of positive area."""
    out = []
    for poly in polys:
        for part in halves(poly, ln):
            if len(part) >= 3 and area2(part) != 0:
                out.append(part)
    return out


def clip_le(poly, A, B, C) -> list:
    """poly ∩ {A x + B y - C <= 0}, closed; may come out a segment or a point."""
    return halves(poly, Line(A, B, C))[0] if poly else []


def contains(poly, p) -> bool:
    """p in the closed convex polygon."""
    sgn = set()
    n = len(poly)
    for i in range(n):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % n]
        c = (x1 - x0) * (p[1] - y0) - (y1 - y0) * (p[0] - x0)
        if c:
            sgn.add(c > 0)
    return len(sgn) <= 1


def centroid(poly):
    n = len(poly)
    return (sum(p[0] for p in poly) / n, sum(p[1] for p in poly) / n)


def meet(l1, l2):
    det = l1.a * l2.b - l2.a * l1.b
    if det == 0:
        return None
    return ((l1.c * l2.b - l2.c * l1.b) / det, (l1.a * l2.c - l2.a * l1.c) / det)


def rect_poly(r) -> list:
    x0, y0, x1, y1 = (F(v) for v in r)
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def convex(poly) -> bool:
    n = len(poly)
    if n < 3 or area2(poly) == 0:
        return False
    sgn = set()
    for i in range(n):
        (x0, y0), (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n], poly[(i + 2) % n]
        c = (x1 - x0) * (y2 - y1) - (y1 - y0) * (x2 - x1)
        if c:
            sgn.add(c > 0)
    return len(sgn) == 1


def merge(polys) -> list:
    """Greedily merge polygons sharing a full edge while the union stays convex."""
    polys = [list(p) for p in polys]
    merged = True
    while merged:
        merged = False
        for i, j in itertools.combinations(range(len(polys)), 2):
            u = _union(polys[i], polys[j])
            if u is not None:
                polys[i] = u
                del polys[j]
                merged = True
                break
    return polys


def _union(p, q):
    p, q = ccw(p), ccw(q)
    n, m = len(p), len(q)
    for i in range(n):
        a, b = p[i], p[(i + 1) % n]
        for j in range(m):
            if q[j] == b and q[(j + 1) % m] == a:
                loop = [p[(i + 1 + k) % n] for k in range(n)]          # b ... a
                loop += [q[(j + 2 + k) % m] for k in range(m - 2)]    # q after a ... before b
                loop = _drop_collinear(loop)
                return loop if convex(loop) else None
    return None


def _drop_collinear(poly) -> list:
    out = list(poly)
    changed = True
    while changed and len(out) > 3:
        changed = False
        for i in range(len(out)):
            a, b, c = out[i - 1], out[i], out[(i + 1) % len(out)]
            if (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0]) == 0:
                del out[i]
                changed = True
                break
    return out


def elev(fs, p):
    return min(abs(val(ln, p)) / h for ln, h in fs)


def cut_lines(fs) -> list:
    """Every line where d (the nearest of `fs`) can bend: the hinge lines and
    their pairwise bisectors.  d is linear between them."""
    cuts = [ln for ln, _ in fs]
    for (li, hi), (lj, hj) in itertools.combinations(fs, 2):
        for s in (1, -1):
            A, B = li.a * hj - s * lj.a * hi, li.b * hj - s * lj.b * hi
            if A or B:
                cuts.append(canon(A, B, li.c * hj - s * lj.c * hi))
    return cuts


def _segs(P):
    if len(P) == 1:
        return [(P[0], P[0])]
    return [(P[i], P[(i + 1) % len(P)]) for i in range(len(P))]


def _d2_point_seg(v, s):
    p, q = s
    ex, ey = q[0] - p[0], q[1] - p[1]
    dx, dy = v[0] - p[0], v[1] - p[1]
    ee = ex * ex + ey * ey
    t = F(0) if ee == 0 else min(F(1), max(F(0), (dx * ex + dy * ey) / ee))
    rx, ry = dx - t * ex, dy - t * ey
    return rx * rx + ry * ry


def _linf_point_seg(v, s):
    p, q = s
    ex, ey = q[0] - p[0], q[1] - p[1]
    dx, dy = v[0] - p[0], v[1] - p[1]
    ts = {F(0), F(1)}
    for num, den in ((dx, ex), (dy, ey), (dx - dy, ex - ey), (dx + dy, ex + ey)):
        if den:
            t = F(num) / den
            if 0 <= t <= 1:
                ts.add(t)
    return min(max(abs(dx - t * ex), abs(dy - t * ey)) for t in ts)


def _orient(p, q, r):
    return sign((q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]))


def _seg_meet(s, t) -> bool:
    """Two closed segments (possibly points) share a point."""
    (p, q), (r, u) = s, t
    o1, o2, o3, o4 = _orient(p, q, r), _orient(p, q, u), _orient(r, u, p), _orient(r, u, q)
    if o1 * o2 < 0 and o3 * o4 < 0:
        return True

    def on(a, b, c):                     # c on the closed segment ab, given collinear
        return min(a[0], b[0]) <= c[0] <= max(a[0], b[0]) and \
            min(a[1], b[1]) <= c[1] <= max(a[1], b[1])
    return (o1 == 0 and on(p, q, r)) or (o2 == 0 and on(p, q, u)) or \
        (o3 == 0 and on(r, u, p)) or (o4 == 0 and on(r, u, q))


def set_dist(P, Q, euclid: bool):
    """Exact distance between two convex sets (vertex lists); squared if euclid."""
    if (len(P) >= 3 and any(contains(P, v) for v in Q)) or \
            (len(Q) >= 3 and any(contains(Q, v) for v in P)):
        return F(0)
    if any(_seg_meet(s, t) for s in _segs(P) for t in _segs(Q)):
        return F(0)                      # edges cross (no vertex of either inside the other)
    f = _d2_point_seg if euclid else _linf_point_seg
    return min(min(f(v, s) for v in P for s in _segs(Q)),
               min(f(v, s) for v in Q for s in _segs(P)))


def disjoint(P, Q) -> bool:
    """Convex polygons with disjoint interiors (a separating edge line exists)."""
    for poly in (P, Q):
        n = len(poly)
        for i in range(n):
            p, q = poly[i], poly[(i + 1) % n]

            def side(x):
                return (q[0] - p[0]) * (x[1] - p[1]) - (q[1] - p[1]) * (x[0] - p[0])
            a, b = [side(x) for x in P], [side(x) for x in Q]
            if (max(a) <= 0 <= min(b)) or (max(b) <= 0 <= min(a)):
                return True
    return False


def edge_line(p, q):
    """(canonical line through p != q, t(p), t(q)) with t = -b x + a y the
    coordinate along the line."""
    a, b = q[1] - p[1], p[0] - q[0]
    m = math.lcm(F(a).denominator, F(b).denominator)
    ln = canon(a * m, b * m, (a * p[0] + b * p[1]) * m)
    return ln, -ln.b * p[0] + ln.a * p[1], -ln.b * q[0] + ln.a * q[1]
