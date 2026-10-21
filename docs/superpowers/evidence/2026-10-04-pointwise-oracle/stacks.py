"""The pointwise oracle: does the GEOMETRY permit this layer order?

Spec: `docs/superpowers/specs/2026-10-04-pointwise-oracle-design.md` section 2.

WHAT IS INDEPENDENT HERE, AND WHAT IS NOT. This module imports no production
module, but it does NOT claim independence at the level of geometric
predicates: the clip-span and strict-interior routines this module consumes
(`geom.clip_seg`, `geom.strictly_inside`) are themselves transcriptions of the
production geometry they document (`geom.py:251`, `geom.py:277`), and this
module reuses them ON PURPOSE.
Re-transcribing them here would reopen the bitwise-fidelity risk that a
previous slice closed, and any difference would then be ambiguous between
arithmetic and a divergent rewrite. What IS independent is the CASE ANALYSIS:
production reaches the adjacency condition through five separate geometric
branches, each with its own side bookkeeping, and this module reaches the same
condition through one uniform rule. Consequently a bug inside `strictly_inside`
or `clip_seg` would be COMMON-MODE: both arms would inherit it and this
comparison could not see it. `test_stacks.py::test_imports_are_allowlisted`
pins the import surface structurally (AST allowlist), because an import
discipline resting on a convention is not one.

CALLER PRECONDITIONS.
  * Faces must be CONVEX and COUNTER-CLOCKWISE. `clip_seg` and
    `strictly_inside` are half-plane tests; on a non-convex or clockwise face
    `covering` returns False at points plainly inside it, so the oracle would
    miss intruders and ACCEPT bad orders. `is_convex` is how a caller checks;
    nothing in this module enforces it.
  * Coordinates must be RATIONAL (`fractions.Fraction`). With plain `int`
    coordinates `clip_seg`'s `-num / denom` yields a `float` and the exactness
    guarantee below is silently lost.

THE RULE, and where it comes from. A crease JOINS two faces: the paper is
continuous across it, so nothing can pass between them. Therefore, at every
point of a folded crease image, the crease's two faces must be ADJACENT in the
stack of faces covering that point. That is derived from physical connectivity,
not from Akitaya-Demaine-Ku's family taxonomy, which is what makes it an
independent reading of the same condition. It subsumes TWO of the three
families, and the third only partly -- see the collinear warning below:
  * a face between a crease's two halves IS taco-tortilla;
  * two creases interleaving IS taco-taco -- BUT ONLY WHEN THEY CROSS
    TRANSVERSALLY. ⚠ MEASURED FALSE FOR THE COLLINEAR ARM, 2026-10-05.
    When two creases lie on ONE line and share a segment, every face's
    boundary runs along that segment, so a strict-interior test returns
    False by construction and this module cannot see the configuration at
    all. Production says so itself, in `_collinear_overlap`'s docstring:
    a transversal crossing "is therefore already covered by the
    spanning-face rule, whereas a shared segment is not (each face's
    boundary runs along it, so _strictly_inside is False by
    construction)". Consequence: the `taco` family is NOT independently
    checked by this module -- 164 of 164 clauses that rejected an
    order this module admitted were tacos over a collinear-overlapping
    crease pair. The `equality` family IS checked, and agrees exactly;
  * tortilla-tortilla (a pair's order being constant across its overlap) is
    structural in the production constraint generator, which carries ONE
    variable per face pair rather than one per cell, so it cannot vary by
    construction.

WHY ONE SAMPLE PER SUB-SEGMENT IS EXHAUSTIVE. The set of faces covering a
crease changes only where some face's clip span starts or ends. `breakpoints`
returns exactly those parameter values, so the covering set is invariant on
each resulting interval and one exact rational sample decides the whole
interval. There is no sampling density parameter and no sampling error.
`test_breakpoints_bound_constant_cover` MEASURES this rather than assuming it,
and `test_coarsened_breakpoints_break_the_completeness_gate` shows the check
can fail.
"""
from dataclasses import dataclass

import geom


@dataclass(frozen=True)
class Site:
    """One sub-segment of one crease, with the faces that cover it.

    `cover` holds the candidate INTRUDERS only -- `fa` and `fb` are excluded,
    since the question is what lies between them. `t_lo`/`t_hi` are carried for
    witness reporting and take no part in the decision.
    """
    fa: int
    fb: int
    cover: frozenset
    t_lo: object
    t_hi: object


def is_convex(poly, K):
    """True iff `poly` is a simple, strictly counter-clockwise convex ring.

    That is EXACTLY the precondition `geom.strictly_inside` needs: it demands
    every edge cross product be strictly positive, i.e. the interior is the
    intersection of the edges' LEFT half-planes. A face that fails it is
    invisible to `covering`, so the oracle would MISS intruders and ACCEPT bad
    orders -- silent failure in the dangerous direction. (A clockwise convex
    square is the sharpest case: every cross product is negative, so
    `covering` finds nothing inside it at all.)

    Three checks, all required:
      1. at least 3 vertices;
      2. the shoelace signed area is non-degenerate (`K.area_nonzero`) and
         strictly positive. This rejects clockwise winding and an
         all-collinear ring at once;
      3. for EVERY directed edge a -> b, EVERY vertex v satisfies
         cross(b - a, v - a) >= 0. A vertex on the edge line (cross is zero
         under `K.is_zero`) is allowed, because collinear vertices are
         legitimate; one vertex strictly to the right makes the ring
         non-convex or self-intersecting.

    Check 3 is the real precondition, stated directly as the half-plane
    property rather than approximated by a turn-sign or total-turning proxy
    (which a pentagram, with all left turns, defeats). It is O(n^2), which is
    irrelevant: faces have a handful of vertices and this runs once per face.
    The zero test is `K.is_zero`, so the predicate follows the kernel rather
    than hardcoding a tolerance.
    """
    n = len(poly)
    if n < 3:
        return False
    area2 = 0
    for i in range(n):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % n]
        area2 += ax * by - bx * ay
    if not K.area_nonzero(area2 / 2) or not area2 > 0:
        return False
    for i in range(n):
        ax, ay = poly[i]
        bx, by = poly[(i + 1) % n]
        ex, ey = bx - ax, by - ay
        for vx, vy in poly:
            cross = ex * (vy - ay) - ey * (vx - ax)
            if not K.is_zero(cross) and cross < 0:
                return False
    return True


def point_at(seg, t):
    """The point at parameter `t` along `seg`."""
    (x0, y0), (x1, y1) = seg
    return (x0 + t * (x1 - x0), y0 + t * (y1 - y0))


def breakpoints(seg, polys, others, K):
    """Parameter values along `seg` at which the covering set can change.

    Returns the segment's own ends together with every in-range clip-span
    endpoint, sorted and deduplicated. See the module docstring for why this
    makes one sample per interval exhaustive.
    """
    zero, one = K.conv(0.0), K.conv(1.0)
    cuts = {zero, one}
    for x in others:
        span = geom.clip_seg(seg, polys[x], K)
        if span is None:
            continue
        for t in span:
            if zero <= t <= one:
                cuts.add(t)
    return tuple(sorted(cuts))


def covering(seg, t, polys, others, K):
    """Faces in `others` whose STRICT interior contains `point_at(seg, t)`.

    Strict, not closed: a face whose BOUNDARY runs along the crease is not
    threading the fold and so is not an intruder. Under exact rational
    arithmetic "strictly inside" has exactly one meaning, so this imports no
    epsilon choice -- the decision rests on physics, not on a tolerance.
    """
    p = point_at(seg, t)
    return frozenset(x for x in others
                     if geom.strictly_inside(p, polys[x], K))


def sites(creases, polys, subset, K):
    """Every (crease, sub-segment) pair inside `subset`, with its intruders.

    `creases` is a sequence of `(fa, fb, seg)`. A crease with a face outside
    `subset` is a REFUSAL, not a skip: a caller that filters wrongly would
    otherwise get a quietly smaller population and a vacuously clean result.

    Caller precondition: coordinates are exact rationals (`Fraction`) and the
    faces are convex (see `is_convex`). With plain `int` coordinates
    `clip_seg` divides to a `float` and exactness is silently lost.
    """
    out = []
    for fa, fb, seg in creases:
        if fa not in subset or fb not in subset:
            raise ValueError(
                f"crease ({fa}, {fb}) has a face outside the subset "
                f"{sorted(subset)}. Filter with `restrict.creases_in` before "
                f"calling `sites`; skipping it here would shrink the "
                f"population silently.")
        others = tuple(sorted(subset - {fa, fb}))
        cuts = breakpoints(seg, polys, others, K)
        for t_lo, t_hi in zip(cuts, cuts[1:]):
            mid = (t_lo + t_hi) / 2
            out.append(Site(fa, fb, covering(seg, mid, polys, others, K),
                            t_lo, t_hi))
    return tuple(out)


def active(sites_tuple):
    """Sites with at least one candidate intruder.

    A site with an empty cover can never yield a violation, so the enumeration
    skips it. `sites` still returns it, so the driver can report how much
    geometry was examined against how much of it could carry a constraint --
    an agreement is only as broad as the population it was taken over.
    """
    return tuple(s for s in sites_tuple if s.cover)


def violations_for_order(sites_tuple, order):
    """Sites where some face lies strictly between the crease's two faces.

    `order` is the stack TOP-TO-BOTTOM, so `order[0]` is topmost and "between"
    is just "index strictly between". All the geometry is already in
    `Site.cover`; this step is integer comparison, which is what lets the
    caller run it over every permutation cheaply.

    `order` must contain EVERY face in each site's `cover` plus its `fa` and
    `fb`. A missing face raises `KeyError` by design: the failure is loud,
    which is what we want, rather than a quiet skip that would read as "no
    violation".
    """
    pos = {f: i for i, f in enumerate(order)}
    out = []
    for s in sites_tuple:
        ia, ib = pos[s.fa], pos[s.fb]
        lo, hi = (ia, ib) if ia < ib else (ib, ia)
        between = tuple(sorted(x for x in s.cover if lo < pos[x] < hi))
        if between:
            out.append((s, between))
    return tuple(out)


def accepts(sites_tuple, order):
    """No site has anything between its crease's two faces."""
    return not violations_for_order(sites_tuple, order)


def triples(creases, polys, K, faces=None):
    """Every `(x, frozenset({fa, fb}))` the oracle finds: face `x` whose
    STRICT INTERIOR a crease image crosses.

    This is the exhaustive primary comparison (spec section 4A): it asks, for
    every crease and every face, whether the crease image passes through the
    face's strict interior, and it needs no subset, no cell cover and no
    adjacency guard -- geometry only. It is built from the module's OWN
    `breakpoints` and `covering`, so it applies the oracle's rule rather than a
    second approximation of it: every sub-segment of every crease is sampled
    once at its midpoint, and a face found covering any sub-segment yields the
    triple.

    `creases` is a sequence of `(fa, fb, seg)`; `polys` maps face index to
    polygon; `faces` defaults to every index in `polys`. A crease's own two
    faces are never candidate intruders of it. Returns a `frozenset`.

    One OPTIMIZATION, and why it is sound rather than heuristic: before
    computing breakpoints for a crease, the candidate faces are narrowed to
    those whose `geom.clip_seg` against that crease's segment is not `None`.
    A `None` span means the segment never enters the face's closed region, so
    the face's strict interior cannot contain any point of it, and `covering`
    could never have returned that face for any sub-segment. Narrowing
    therefore removes only faces that were certain to contribute nothing, and
    every face `breakpoints` would have used for a cut is retained (it too
    skips `None` spans). It is a pure cost reduction: on the real witness the
    enumeration drops from about 5.6 million `strictly_inside` calls to roughly
    450 thousand.

    Caller preconditions are those of `sites`: exact rational coordinates and
    convex counter-clockwise faces.
    """
    if faces is None:
        # NOT `sorted(polys)`: `polys` may be a LIST (which is what
        # `exact_arrangement.as_tuples` returns), and sorting a list
        # enumerates the POLYGONS rather than their indices. A dict yields
        # its keys; a sequence yields its index range.
        faces = polys.keys() if hasattr(polys, "keys") else range(len(polys))
    pool = tuple(sorted(faces))
    out = set()
    for fa, fb, seg in creases:
        pair = frozenset({fa, fb})
        cands = tuple(x for x in pool
                      if x != fa and x != fb
                      and geom.clip_seg(seg, polys[x], K) is not None)
        if not cands:
            continue
        cuts = breakpoints(seg, polys, cands, K)
        for t_lo, t_hi in zip(cuts, cuts[1:]):
            mid = (t_lo + t_hi) / 2
            for x in covering(seg, mid, polys, cands, K):
                out.add((x, pair))
    return frozenset(out)
