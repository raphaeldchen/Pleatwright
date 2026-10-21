"""The shipped arrangement algorithm, transcribed once, kernel-parameterized.

A TRANSCRIPTION, not a reimplementation: structure follows
`layer_order._cells` and its helpers statement for statement, and the only
substitutions are (a) the kernel's predicates where production compares against
an epsilon, and (b) tuples of numbers where production uses numpy arrays.
Changing the algorithm here would make a float/exact difference
uninterpretable -- it could be arithmetic, or it could be the rewrite.
"""
from __future__ import annotations


def cross(o, a, b):
    """Signed area of (o -> a) x (o -> b). layer_order's _cross, inlined."""
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _cross_d(d, v):
    """Cross of a DIRECTION with a vector (layer_order calls _cross(d, p-a))."""
    return d[0] * v[1] - d[1] * v[0]


def area(poly) -> object:
    """Signed area, matching layer_order._area's shoelace.

    Production sums with `np.sum`, which switches from a sequential loop to
    8-accumulator pairwise summation at n >= 8, differing in the last bit.
    This plain loop is bit-identical only below that size.

    ⚠ AND THE BITWISE GATE DOES NOT CATCH THAT. An earlier revision of this
    docstring claimed the fidelity gate's bitwise comparison "is what makes an
    n >= 8 cell fail loudly". It cannot: this value is consumed only through
    `K.area_nonzero` and is never written into a cell coordinate, so a
    last-bit difference is invisible to `bitwise_diff` unless it flips an
    `AREA_EPS` decision -- and that margin is 1.08e+05x, so it cannot.
    Nothing here is self-policing, which is why the condition is MEASURED
    instead: `split_convex` records the largest polygon reaching this function
    (`MarginLog.observe_max("area_vertices", ...)`, reported as
    `area_vertices_max` in the JSON). Note the population is every
    intermediate `outside`/`remaining` polygon across every clip, not only the
    26 final cells.
    """
    n = len(poly)
    s = 0
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        s = s + (x0 * y1 - x1 * y0)
    return s / 2


#: `_dedupe_ring`'s coincidence test is `np.allclose(..., atol=1e-9, rtol=0)`
#: -- a LITERAL in production (layer_order.py:259, :261), not `GEOM_EPS`, even
#: though its own docstring says "within GEOM_EPS". The two are equal today.
#: A margin has to be measured against the number the predicate really uses,
#: so it is named here and `exact_arrangement.epsilon_parity` asserts it
#: against `_dedupe_ring`'s own source rather than against the docstring.
DEDUPE_ATOL = 1e-9


def dedupe_ring(pts, K, log=None):
    """layer_order._dedupe_ring: drop consecutive duplicates incl. wrap.

    One of the two arrangement-internal `GEOM_EPS` sites. Until this logging
    existed, the `GEOM_EPS` bound was taken over the SEGMENT helpers only, and
    the verdict's claim that all three epsilons are inert did not cover the
    `same_point` decisions that build the cells. Both deltas are recorded at
    every comparison: production's `np.allclose` evaluates both coordinates,
    while this kernel's `same_point` lambda short-circuits on `and`, so
    logging both matches PRODUCTION's population and is a conservative
    superset of the lambda's -- it can only make the bound more pessimistic.
    """
    def same(p, q):
        _rec(log, K, "GEOM_EPS/dedupe_same_point", p[0] - q[0], DEDUPE_ATOL)
        _rec(log, K, "GEOM_EPS/dedupe_same_point", p[1] - q[1], DEDUPE_ATOL)
        return K.same_point(p, q)

    out = []
    for pt in pts:
        if not out or not same(pt, out[-1]):
            out.append(pt)
    if len(out) >= 2 and same(out[0], out[-1]):
        out.pop()
    return out if len(out) >= 3 else []


def clip_half(poly, a, b, K, log=None):
    """layer_order._clip_half: clip convex poly to the half-plane left of a->b.

    The other arrangement-internal `GEOM_EPS` site, and the one that decides
    the 26 cells and therefore `covers`, `pairs` and 97.8% of the clause set.

    ONE tag covers BOTH of its predicates, and that is exact rather than
    convenient. `side_keep` reads `s[i]`; `strict_cross` reads `s[i]` and
    `s[(i+1) % n]`. Over the loop those are the same multiset -- the whole of
    `s` -- and both predicates compare their arguments against +-GEOM_EPS
    only, so float and exact can disagree at either one only when some `s`
    value has |s| < GEOM_EPS. Logging `s` once per vertex therefore bounds
    both decisions, with no double counting:

      * `side_keep`: float keeps iff `sp >= -EPS`, exact iff `sp >= 0`, so
        they differ only for `sp` in [-EPS, 0).
      * `strict_cross`: float needs both values past +-EPS with opposite
        signs, exact needs opposite strict signs, so they differ only when one
        of the two lies in (-EPS, 0) u (0, EPS).

    Either way |s| >= EPS forces agreement, which is what `#kept` records, and
    0 < |s| < EPS is the whole risk band, which is what `#absorbed` records.
    """
    d = (b[0] - a[0], b[1] - a[1])
    n = len(poly)
    s = [_cross_d(d, (poly[i][0] - a[0], poly[i][1] - a[1])) for i in range(n)]
    for v in s:
        _rec(log, K, "GEOM_EPS/clip_half_signed_dist", v, GEOM_EPS)
    out = []
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        sp, sq = s[i], s[(i + 1) % n]
        if K.side_keep(sp):
            out.append(p)
        if K.strict_cross(sp, sq):
            t = sp / (sp - sq)
            out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    return dedupe_ring(out, K, log)


def split_convex(subject, clip, K, log=None):
    """layer_order._split_convex: (intersection_or_None, outside_pieces)."""
    pieces = []
    remaining = subject
    n = len(clip)
    for i in range(n):
        a, b = clip[i], clip[(i + 1) % n]
        if len(remaining) < 3:
            break
        outside = clip_half(remaining, b, a, K, log)   # right of a->b
        if len(outside) >= 3:
            ar = area(outside)
            if log is not None and K.name == "float":
                log.observe_max("area_vertices", len(outside))
                log.record("AREA_EPS/outside", float(ar), AREA_EPS)
            if K.area_nonzero(ar):
                pieces.append(outside)
        remaining = clip_half(remaining, a, b, K, log)
    inter = None
    if len(remaining) >= 3:
        ar = area(remaining)
        if log is not None and K.name == "float":
            log.observe_max("area_vertices", len(remaining))
            log.record("AREA_EPS/intersection", float(ar), AREA_EPS)
        if K.area_nonzero(ar):
            inter = remaining
    return inter, pieces


def cells(polys, K, log=None):
    """layer_order._cells: arrangement cells as (polygon, cover frozenset)."""
    if not polys:
        return []
    xs = [pt[0] for p in polys for pt in p]
    ys = [pt[1] for p in polys for pt in p]
    one = K.conv(1.0)
    lo = (min(xs) - one, min(ys) - one)
    hi = (max(xs) + one, max(ys) + one)
    box = [(lo[0], lo[1]), (hi[0], lo[1]), (hi[0], hi[1]), (lo[0], hi[1])]
    acc = [(box, frozenset())]
    for fi, poly in enumerate(polys):
        new = []
        for cpoly, cover in acc:
            inter, outs = split_convex(cpoly, poly, K, log)
            if inter is None:
                new.append((cpoly, cover))
                continue
            new.append((inter, cover | frozenset({fi})))
            new.extend((o, cover) for o in outs)
        acc = new
    return [(cpoly, cover) for cpoly, cover in acc if cover]


# ---------------------------------------------------------------------------
# The segment half: the helpers `_build_constraints` uses, transcribed.
#
# Three of these normalize by a norm (`_clip_seg` does not; `_unit`,
# `_side_of`, `_collinear_overlap` and `_segs_interact` do), and in every case
# the threshold the normalized value is compared against is an ABSOLUTE
# GEOM_EPS. Removing the square root -- which exact arithmetic must, a norm
# being irrational -- therefore changes the PREDICATE, not just its
# representation: the scaled and unscaled forms agree only when the threshold
# is 0. So these branch on `K.name`, exactly as kernel's module docstring
# sanctions: the float branch reproduces production verbatim, `np.hypot`,
# `np.mean` and `np.dot` included, because it is the control and must match;
# the exact branch uses the rational form, where the threshold is 0 and the
# scaling is sound (a positive factor cannot change a sign or a `> 0`).
#
# NOTE the plan brief's Step-2 draft asserted the reduction for `_side_of` on
# the grounds that "sign is scale-invariant". The SIGN is; the `abs(d) <
# GEOM_EPS` test that precedes it is not, and that draft is one of the reasons
# its float arm missed production's equality count.
# ---------------------------------------------------------------------------

# numpy, not the stdlib: production's `np.hypot`, `np.mean` and `np.dot` are
# not guaranteed bit-identical to `math.hypot` and a hand-written sum, and the
# float arm is a BITWISE control.
import numpy as np                                       # noqa: E402

from kernel import AREA_EPS, GEOM_EPS, INTERIOR_EPS      # noqa: E402


def _rec(log, K, tag, value, threshold):
    """Record a float-mode comparison against its epsilon, split by OUTCOME.

    A single minimum of |value|/threshold measures nothing here. Every one of
    these predicates asks "is x zero?", and float and exact can only disagree
    in two distinct ways, on two distinct populations:

      * x is TRULY zero but float rounding pushed |x| up to or past the
        epsilon -- then float keeps a constraint exact drops. The margin is the
        epsilon's HEADROOM over the worst rounding noise it had to absorb,
        `threshold / max|x|` over the absorbed population.
      * x is truly non-zero but |x| fell below the epsilon -- then float drops
        a constraint exact keeps. The margin is `min|x| / threshold` over the
        kept population.

    Both want to be >> 1, and together they say how far the epsilon could move
    in either direction without changing a single decision. MarginLog keeps a
    MINIMUM per tag, so the absorbed case is recorded with the arguments
    swapped -- that is what makes its minimum the tightest (largest-noise)
    case. Its row therefore reads `value` = the epsilon and `threshold` = the
    noise; the `#absorbed` suffix is what says so.

    A bit-exact 0.0 is in neither population: both kernels read it as zero, so
    it carries no risk and no margin. Those get their own tag, where the row's
    presence is the information.

    No split is applied at the AREA_EPS sites in `split_convex`: those are
    Task 2's, reviewed, and recorded no absorbed or zero comparison at all
    (their minimum is 1.081e-04, i.e. 1.08e+05x the epsilon).
    """
    if log is None or K.name != "float":
        return
    v = abs(float(value))
    if v == 0.0:
        log.record(tag + "#exact-zero", 0.0, threshold)
    elif v < threshold:
        log.record(tag + "#absorbed", threshold, v)
    else:
        log.record(tag + "#kept", v, threshold)


def clip_seg(seg, poly, K, log=None):
    """layer_order._clip_seg (:367-388): parametric span of seg inside poly."""
    p0 = seg[0]
    d = (seg[1][0] - p0[0], seg[1][1] - p0[1])
    t0, t1 = K.conv(0.0), K.conv(1.0)
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        e = (b[0] - a[0], b[1] - a[1])
        denom = _cross_d(e, d)
        num = _cross_d(e, (p0[0] - a[0], p0[1] - a[1]))
        _rec(log, K, "GEOM_EPS/clip_seg_denom", denom, GEOM_EPS)
        if K.is_zero(denom):                 # abs(denom) < GEOM_EPS
            _rec(log, K, "GEOM_EPS/clip_seg_parallel_num", num, GEOM_EPS)
            if K.is_neg(num):                # num < -GEOM_EPS
                return None                  # parallel and fully outside
            continue
        t = -num / denom
        if denom > 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
    _rec(log, K, "GEOM_EPS/clip_seg_span", t1 - t0, GEOM_EPS)
    return (t0, t1) if K.seg_span_pos(t1 - t0) else None


def strictly_inside(p, poly, K, log=None):
    """layer_order._strictly_inside (:235-247) -- where INTERIOR_EPS lives.

    Production writes the loop as `all(...)` over a generator, which
    short-circuits; this loop does too, so the margin log sees exactly the
    comparisons production evaluates and no more.
    """
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        c = _cross_d((b[0] - a[0], b[1] - a[1]), (p[0] - a[0], p[1] - a[1]))
        _rec(log, K, "INTERIOR_EPS/strictly_inside", c, INTERIOR_EPS)
        if not K.interior_pos(c):            # not (c > INTERIOR_EPS)
            return False
    return True


def unit(seg, K, log=None):
    """layer_order._unit (:456-459).

    Its only consumer is `side_of`, whose `abs(_cross(u, c - a)) < GEOM_EPS`
    reads an absolute DISTANCE -- so the normalization sets that threshold's
    meaning and the float arm must keep it. In exact the threshold is 0, where
    dividing by a positive length cannot change `== 0` or a sign, so the raw
    direction is the same predicate and is rational.
    """
    p0, p1 = seg[0], seg[1]
    d = (p1[0] - p0[0], p1[1] - p0[1])
    if K.name == "exact":
        return None if (d[0] == 0 and d[1] == 0) else d
    n = float(np.hypot(d[0], d[1]))
    _rec(log, K, "GEOM_EPS/unit_length", n, GEOM_EPS)
    return None if n < GEOM_EPS else (d[0] / n, d[1] / n)


def side_of(poly, a, u, K, log=None):
    """layer_order._side_of (:437-453): +1 left, -1 right, 0 degenerate."""
    if K.name == "exact":
        n = len(poly)
        cx = sum((pt[0] for pt in poly), K.conv(0.0)) / n
        cy = sum((pt[1] for pt in poly), K.conv(0.0)) / n
        c = (cx, cy)
    else:
        c = np.mean(np.asarray(poly, dtype=float), axis=0)
    v = _cross_d(u, (c[0] - a[0], c[1] - a[1]))
    _rec(log, K, "GEOM_EPS/side_of", v, GEOM_EPS)
    if K.is_zero(v):                         # abs(v) < GEOM_EPS
        return 0
    return 1 if v > 0 else -1


def _overlap_tail(p, d1, r, s, K, log=None):
    """The shared tail of `_collinear_overlap` (:432-435) and the collinear
    branch of `_segs_interact` (:401-405): do the two collinear segments'
    interiors overlap along d1?

    Float: verbatim, including the unit projection and the GEOM_EPS threshold.
    Exact: multiply through by length > 0 -- L2 = dot(d1,d1), B = dot(., d1) --
    which is faithful because the threshold is 0.
    """
    if K.name == "exact":
        L2 = d1[0] * d1[0] + d1[1] * d1[1]
        if L2 == 0:
            return False
        B0 = (r[0] - p[0]) * d1[0] + (r[1] - p[1]) * d1[1]
        B1 = (s[0] - p[0]) * d1[0] + (s[1] - p[1]) * d1[1]
        if B0 > B1:
            B0, B1 = B1, B0
        return min(L2, B1) > max(K.conv(0.0), B0)
    length = float(np.hypot(d1[0], d1[1]))
    _rec(log, K, "GEOM_EPS/overlap_length", length, GEOM_EPS)
    if length < GEOM_EPS:
        return False
    d1a = np.asarray(d1, dtype=float)
    u = d1a / length
    rp = np.asarray((r[0] - p[0], r[1] - p[1]), dtype=float)
    sp = np.asarray((s[0] - p[0], s[1] - p[1]), dtype=float)
    b0, b1 = sorted((float(np.dot(rp, u)), float(np.dot(sp, u))))
    span = min(length, b1) - max(0.0, b0)
    _rec(log, K, "GEOM_EPS/overlap_span", span, GEOM_EPS)
    return span > GEOM_EPS


def collinear_overlap(s1, s2, K, log=None):
    """layer_order._collinear_overlap (:413-435)."""
    p, q = s1
    r, s = s2
    d1 = (q[0] - p[0], q[1] - p[1])
    d2 = (s[0] - r[0], s[1] - r[1])
    o = (_cross_d(d1, (r[0] - p[0], r[1] - p[1])),
         _cross_d(d1, (s[0] - p[0], s[1] - p[1])),
         _cross_d(d2, (p[0] - r[0], p[1] - r[1])),
         _cross_d(d2, (q[0] - r[0], q[1] - r[1])))
    # production: `if any(abs(x) >= GEOM_EPS for x in o): return False`, which
    # SHORT-CIRCUITS -- so the log must stop where it stops, or it would report
    # margins for comparisons production never makes.
    for x in o:
        _rec(log, K, "GEOM_EPS/collinear_o", x, GEOM_EPS)
        if not K.is_zero(x):                 # abs(x) >= GEOM_EPS
            return False
    return _overlap_tail(p, d1, r, s, K, log)


def segs_interact(s1, s2, K, log=None):
    """layer_order._segs_interact (:390-411): proper crossing, or collinear
    with overlapping interiors. Endpoint-touching does not count.

    Production's `strad` expressions are literally `K.strict_cross`:
    `(o1 > GEOM_EPS and o2 < -GEOM_EPS) or (o1 < -GEOM_EPS and o2 > GEOM_EPS)`
    is the float kernel's `strict_cross(o1, o2)` term for term.
    """
    p, q = s1
    r, s = s2
    d1 = (q[0] - p[0], q[1] - p[1])
    d2 = (s[0] - r[0], s[1] - r[1])
    o1 = _cross_d(d1, (r[0] - p[0], r[1] - p[1]))
    o2 = _cross_d(d1, (s[0] - p[0], s[1] - p[1]))
    o3 = _cross_d(d2, (p[0] - r[0], p[1] - r[1]))
    o4 = _cross_d(d2, (q[0] - r[0], q[1] - r[1]))
    # production: `if all(abs(o) < GEOM_EPS for o in (...))`, short-circuiting
    # on the first non-zero, same reasoning as above.
    os_ = (o1, o2, o3, o4)
    collinear = True
    logged = 0
    for x in os_:
        _rec(log, K, "GEOM_EPS/segs_interact_o", x, GEOM_EPS)
        logged += 1
        if not K.is_zero(x):
            collinear = False
            break
    if collinear:
        return _overlap_tail(p, d1, r, s, K, log)
    # The straddle tests below compare o1..o4 against +-GEOM_EPS too, and the
    # collinear loop stopped at its first non-zero, so up to three of those
    # four values have not been logged yet. They are logged here, each exactly
    # once, so the tag covers the population the predicate evaluates rather
    # than only the prefix the collinear test reads. (This is a conservative
    # superset: `and` short-circuits, so (o3, o4) is only compared when
    # (o1, o2) straddle -- logging them anyway can only make the bound more
    # pessimistic, never optimistic.) The predicate itself is untouched.
    for x in os_[logged:]:
        _rec(log, K, "GEOM_EPS/segs_interact_o", x, GEOM_EPS)
    return K.strict_cross(o1, o2) and K.strict_cross(o3, o4)
