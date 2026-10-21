"""The shipped constraint families, transcribed, kernel-parameterized.

A TRANSCRIPTION of `layer_order._build_constraints` (:519-645) under the same
discipline as `geom`: statement for statement, substituting only the kernel's
predicates where production compares against an epsilon and tuples where
production uses numpy arrays. `constraint_fidelity_gate` is what holds that
claim honest -- the float arm must reproduce production's three families
exactly before the exact arm is allowed to mean anything.

`direct` and `slots` are deliberately absent: `direct` is the order relations
forced by ONE fixed labelling, which the joint query ignores by design, and
`slots` is derived from it. What remains -- pairs, equalities, tacos -- is
label-independent geometry, which is exactly what this probe is testing.

TWO THINGS THE PLAN BRIEF'S DRAFT GOT WRONG HERE, both load-bearing:

1. `_seg_of` (:527-531) indexes `result.folded_vertices[fa]`, NOT `polys[fa]`.
   Those two are not interchangeable: `_polys_of` (:840) reverses any face
   whose signed area is negative, which on this witness is 190 of 380 faces.
   Indexing the reversed polygon with a position taken from `result.faces[fa]`
   reads the wrong vertices for every reflected face. Hence `_folded_of` below.
2. The equality accumulator is a `list` in production (deduplicated only by
   the gate's `frozenset`), so order of construction is irrelevant -- but the
   LITERAL PAIR's order inside each entry is not, and is preserved site by
   site.
"""
from __future__ import annotations

from itertools import combinations

import numpy as np

import geom


def lit(x: int, f: int):
    """layer_order._lit (:360-364)."""
    return ((x, f), False) if x < f else ((f, x), True)


def _folded_of(result, K):
    """`result.folded_vertices`, kernel-converted, UNreversed.

    `_seg_of` reads these; `polys` (which `_polys_of` may have reversed) is
    what the clipping and side tests read. Keeping them separate is the whole
    of correction (1) in the module docstring.
    """
    out = []
    for P in result.folded_vertices:
        A = np.asarray(P, dtype=float)
        out.append([(K.conv(float(x)), K.conv(float(y))) for x, y in A])
    return out


def build(result, polys_k, cells_list, K, log=None, ordered=False,
          census=None):
    """Returns (pairs, equalities, tacos).

    `equalities` and `tacos` come back as frozensets, which is what the
    float/exact comparison needs -- production's own `_build_constraints`
    appends them to lists in an order that is an artifact of its loop nesting,
    and `_propagate` does not depend on it.

    `ordered=True` returns them as tuples in construction order instead. Only
    the fidelity gate asks for that, and only to assert something STRONGER than
    it needs: that the float arm reproduces production element for element,
    which rules out a transcription that happens to reach the same set by a
    different enumeration.

    `census`, when a dict is passed, is filled with how often each helper was
    reached and how many constraints each sub-family contributed. An agreement
    is only as broad as the population it was taken over, and this project has
    a recorded instance of a metric reading "no gap" while two whole families
    were silently missing. The census is what stops that happening here --
    `geom.collinear_overlap` really is called ZERO times on this witness,
    because every one of its 745 shared edges is M or V, and no amount of
    float/exact agreement on the families that DID run says anything about it.
    """
    def bump(k, n=1):
        if census is not None:
            census[k] = census.get(k, 0) + n

    covers = tuple(c for _p, c in cells_list)
    pairs = frozenset(pr for c in covers
                      for pr in combinations(sorted(c), 2))
    folded = _folded_of(result, K)

    def seg_of(fa, k):
        face = result.faces[fa]
        i0, i1 = face.index(k[0]), face.index(k[1])
        return (folded[fa][i0], folded[fa][i1])

    # A shared edge is a TACO when it folds (M/V) and a TORTILLA otherwise.
    creases, tortillas = [], []
    for fa, fb, k, a in result.shared_edges:
        if a in ("M", "V"):
            creases.append((fa, fb, a, seg_of(fa, k), k))
        else:
            tortillas.append((fa, fb, seg_of(fa, k), k))

    bump("creases", len(creases))
    bump("tortillas", len(tortillas))

    eqs, tacos = [], []

    def spanning(seg, fa, fb):
        """layer_order._build_constraints._spanning (:548-566)."""
        for x in range(len(polys_k)):
            if x in (fa, fb):
                continue
            if tuple(sorted((x, fa))) not in pairs:
                continue
            if tuple(sorted((x, fb))) not in pairs:
                continue
            bump("clip_seg_calls")
            span = geom.clip_seg(seg, polys_k[x], K, log)
            if span is None:
                continue
            mid_t = (span[0] + span[1]) / 2
            mid = (seg[0][0] + mid_t * (seg[1][0] - seg[0][0]),
                   seg[0][1] + mid_t * (seg[1][1] - seg[0][1]))
            bump("strictly_inside_calls")
            if not geom.strictly_inside(mid, polys_k[x], K, log):
                continue     # segment lies ON x's boundary: no tortilla
            bump("eq_from_spanning")
            eqs.append((lit(x, fa), lit(x, fb)))

    for fa, fb, _a, seg, _k in creases:
        # production also emits `direct`/`slots` here, gated on
        # `sorted((fa,fb)) in pairs`; that gate does NOT apply to _spanning.
        spanning(seg, fa, fb)
    for fa, fb, seg, _k in tortillas:
        spanning(seg, fa, fb)

    # Shared-segment families (:592-645).
    for fa, fb, _a, seg, _k in creases:
        bump("unit_calls")
        u = geom.unit(seg, K, log)
        if u is None:
            bump("unit_returned_None")
            continue
        sa = geom.side_of(polys_k[fa], seg[0], u, K, log)
        sb = geom.side_of(polys_k[fb], seg[0], u, K, log)
        bump("side_of_calls", 2)
        bump("side_of_returned_0", (sa == 0) + (sb == 0))
        if sa == 0 or sa != sb:
            continue          # not a fold-back onto one side: no taco here
        for ta, tb, tseg, _tk in tortillas:
            bump("collinear_overlap_calls")
            if not geom.collinear_overlap(seg, tseg, K, log):
                continue
            for x in (ta, tb):
                if x in (fa, fb):
                    continue
                bump("side_of_calls")
                if geom.side_of(polys_k[x], seg[0], u, K, log) != sa:
                    continue  # the far half of the sheet: not over the taco
                if tuple(sorted((x, fa))) not in pairs:
                    continue
                if tuple(sorted((x, fb))) not in pairs:
                    continue
                bump("eq_from_taco_tortilla_along_flat_edge")
                eqs.append((lit(x, fa), lit(x, fb)))

    for t1, t2 in combinations(tortillas, 2):
        bump("tortilla_pairs")
        (a1, a2, s1, _k1), (b1, b2, s2, _k2) = t1, t2
        bump("collinear_overlap_calls")
        if not geom.collinear_overlap(s1, s2, K, log):
            continue
        bump("unit_calls")
        u = geom.unit(s1, K, log)
        if u is None:
            bump("unit_returned_None")
            continue
        bump("side_of_calls", 4)
        A = {geom.side_of(polys_k[f], s1[0], u, K, log): f for f in (a1, a2)}
        B = {geom.side_of(polys_k[f], s1[0], u, K, log): f for f in (b1, b2)}
        if set(A) != {1, -1} or set(B) != {1, -1}:
            continue          # a degenerate side reading: drop, never guess
        if A[1] in (B[1], B[-1]) or A[-1] in (B[1], B[-1]):
            continue
        if any(tuple(sorted((A[s], B[s]))) not in pairs for s in (1, -1)):
            continue
        bump("eq_from_tortilla_tortilla")
        eqs.append((lit(A[1], B[1]), lit(A[-1], B[-1])))

    for c1, c2 in combinations(creases, 2):
        fa1, fb1, _x1, s1, _k1 = c1
        fa2, fb2, _x2, s2, _k2 = c2
        bump("segs_interact_calls")
        if not geom.segs_interact(s1, s2, K, log):
            continue
        quad = ((fa2, fa1), (fa2, fb1), (fb2, fa1), (fb2, fb1))
        if any(tuple(sorted(pq)) not in pairs for pq in quad):
            continue
        bump("taco_from_taco_taco", 2)
        tacos.append(((fa1, fb1), (fa2, fb2)))
        tacos.append(((fa2, fb2), (fa1, fb1)))

    if ordered:
        return pairs, tuple(eqs), tuple(tacos)
    return pairs, frozenset(eqs), frozenset(tacos)
