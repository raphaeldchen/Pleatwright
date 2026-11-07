"""Paper-efficiency metrics for a packed base (spec
docs/superpowers/specs/2026-10-16-packing-layout-choice-design.md section 6).

Recorded only: nothing here steers the packer.  The reference implementation is
docs/superpowers/evidence/2026-10-16-layout-choice/bp_efficiency_probe.py."""
from __future__ import annotations

import math
import statistics
from collections import defaultdict
from fractions import Fraction

from . import exact2d as E
from .base import Base, _dist, _dist_q, _hinges, merged_segments
from .pack import Layout, grid_init
from .stick import Contracted


def _clipped_ball(t, L: int, N: int) -> int:
    """Cells of the L-inf ball of radius L about `t`, clipped to the paper:
    Lang's box-pleated minimum polygon of a flap whose tip is at `t`."""
    w = min(N, t[0] + L) - max(0, t[0] - L)
    h = min(N, t[1] + L) - max(0, t[1] - L)
    return max(0, w) * max(0, h)


def _cells(rects, N: int) -> int:
    return sum(max(0, min(N, x1) - max(0, x0)) * max(0, min(N, y1) - max(0, y0))
               for x0, y0, x1, y1 in rects)


def _min_ball(reg, N: int):
    """Smallest clipped L-inf ball (radius L) over the half-integer tip points
    of the region (points at distance exactly L from a hinge line), or None."""
    x0, y0, x1, y1 = reg.rect
    best = None
    for i in range(2 * max(0, x0), 2 * min(N, x1) + 1):
        for j in range(2 * max(0, y0), 2 * min(N, y1) + 1):
            p = (i / 2, j / 2)
            if abs(_dist(reg, p) - reg.L) < 1e-9:
                a = _clipped_ball(p, reg.L, N)
                best = a if best is None else min(best, a)
    return best


# ------------------------------------------------------------ stretched layouts
# A layout with `patches` (a Pythagorean stretch, kamiya.py, spec 2026-10-22)
# has regions that own exact convex `pieces` besides their rects, and hinge
# lines that are tilted.  Areas are then exact: a region owns its rect cells
# (none of them under its pieces; `base.build` checks the tiling) plus its
# pieces.  A flap's tip ball is searched per CHAIN (a stretched flap is
# several regions: axis zones, tilted halves, notches, slack) over the
# half-unit points of the chain's flap regions at exact distance L from the
# region's nearest hinge line, tilted ones included.  The ball itself stays
# the box-pleated (L-infinity) polygon, so `slack_fraction` and
# `flap_expansion_*` are indicative on a stretched flap (spec §9.5); the areas
# in `mean_layers` and the river cells in `slack_fraction` are exact.


def _region_area(reg, N: int) -> Fraction:
    return _cells(reg.rects, N) + sum((abs(E.area2(E.poly_of(pc))) / 2 for pc in reg.pieces),
                                      Fraction(0))


def _in_convex(poly, p) -> bool:
    """p inside or on the convex polygon `poly` (exact)."""
    sgn = 0
    for i in range(len(poly)):
        (x0, y0), (x1, y1) = poly[i], poly[(i + 1) % len(poly)]
        c = (x1 - x0) * (p[1] - y0) - (y1 - y0) * (p[0] - x0)
        if c:
            if sgn and (c > 0) != (sgn > 0):
                return False
            sgn = c
    return True


def _tip_balls(reg, N: int) -> list:
    """Clipped L-inf balls about the half-unit points of `reg` (its rects and
    pieces, closed) at exact distance L from its nearest hinge line."""
    hs = _hinges(reg)
    if not hs:
        return []
    polys = [E.poly_of(pc) for pc in reg.pieces]
    boxes = [tuple(map(Fraction, r)) for r in reg.rects]
    for poly in polys:
        xs, ys = [x for x, _ in poly], [y for _, y in poly]
        boxes.append((min(xs), min(ys), max(xs), max(ys)))
    seen, out = set(), []
    for x0, y0, x1, y1 in boxes:
        for i in range(math.ceil(2 * max(0, x0)), math.floor(2 * min(N, x1)) + 1):
            for j in range(math.ceil(2 * max(0, y0)), math.floor(2 * min(N, y1)) + 1):
                if (i, j) in seen:
                    continue
                seen.add((i, j))
                p = (Fraction(i, 2), Fraction(j, 2))
                inside = any(r[0] <= p[0] <= r[2] and r[1] <= p[1] <= r[3] for r in reg.rects) \
                    or any(_in_convex(poly, p) for poly in polys)
                if inside and _dist_q(hs, p) == reg.L:
                    out.append(_clipped_ball((i / 2, j / 2), reg.L, N))
    return out


def _patched_flaps(lay: Layout, N: int):
    """(flap area, river area, [(chain area, min ball | None)]) of a
    stretched layout, flaps grouped by chain."""
    flap, river = Fraction(0), Fraction(0)
    area, balls = defaultdict(Fraction), defaultdict(list)
    for reg in lay.regions:
        a = _region_area(reg, N)
        if reg.kind == "river":
            river += a
            continue
        flap += a
        area[reg.chain] += a
        balls[reg.chain] += _tip_balls(reg, N)
    return flap, river, [(area[c], min(balls[c]) if balls[c] else None) for c in area]


def _off_grid(base: Base) -> int:
    """Solving-CP vertices (the endpoints of the merged creases) off the
    half-unit lattice."""
    segs = merged_segments(base.N, [(k, v["kind"]) for k, v in base.creases.items()])
    pts = {p for (a, b), _ in segs for p in (a, b)}
    return sum(1 for x, y in pts if 2 * x != int(2 * x) or 2 * y != int(2 * y))


def river_corners(lay: Layout) -> int:
    """Corners of river bands strictly inside the paper (0 < x, y < N): the
    lattice points where 1 or 3 of a river region's cells meet, or 2 diagonal
    ones (counted twice), the rule of
    docs/superpowers/evidence/2026-10-19-river-routing/corigami_samples/regions.py
    `corners()`.  BP Studio's tidiness measure, recorded only (spec 2026-10-19 §7).
    A river region's `pieces` (a stretched layout's) are not read: their
    corners are not counted, so the value is indicative there."""
    N = lay.N
    n = 0
    for reg in lay.regions:
        if reg.kind != "river":
            continue
        rects = reg.rects

        def occ(i, j):
            return any(x0 <= i < x1 and y0 <= j < y1 for x0, y0, x1, y1 in rects)

        # a boundary vertex lies on a vertical and a horizontal rectangle edge
        xs = {v for r in rects for v in (r[0], r[2]) if 0 < v < N}
        ys = {v for r in rects for v in (r[1], r[3]) if 0 < v < N}
        for x in xs:
            for y in ys:
                c = [occ(x - 1, y - 1), occ(x, y - 1), occ(x - 1, y), occ(x, y)]
                k = sum(c)
                if k in (1, 3):
                    n += 1
                elif k == 2 and c[0] == c[3]:
                    n += 2
    return n


def metrics(lay: Layout, con: Contracted, base: Base | None, scale: float) -> dict:
    """The section-6 efficiency record of one packed layout.  `scale` is the
    length multiplier of the run (2.0 when every length was doubled), so
    `scale` in the result is in original units."""
    N = lay.N
    total = sum(c.length for c in con.chains)
    bound = math.ceil(total / 2)
    if base is None:            # a stretched layout left unbuilt (Phase 0a's search mode)
        return {"grid": N, "grid_init": grid_init(con), "perimeter_bound": bound,
                "n_over_bound": round(N / bound, 4), "scale": round(scale / N, 4),
                "slack_fraction": None, "flap_expansion_max": None,
                "flap_expansion_median": None, "mean_layers": None, "creases": None,
                "river_corners": None, "stretches": len(lay.patches),
                "off_grid_vertices": None}
    flap_cells = ball_sum = river_cells = 0
    expansion = []
    if lay.patches:
        flap_q, river_q, chains = _patched_flaps(lay, N)
        for a, ball in chains:
            if ball:
                ball_sum += ball
                expansion.append(round(float(a / ball), 3))
        flap_cells, river_cells = float(flap_q), float(river_q)
    else:
        for reg in lay.regions:
            a = _cells(reg.rects, N)
            if reg.kind == "river":
                river_cells += a
                continue
            flap_cells += a
            ball = _min_ball(reg, N)
            if ball:
                ball_sum += ball
                expansion.append(round(a / ball, 3))
    flap_len = sum(c.length for c in con.chains if c.leaf)
    return {
        "grid": N,
        "grid_init": grid_init(con),
        "perimeter_bound": bound,
        "n_over_bound": round(N / bound, 4),
        "scale": round(scale / N, 4),
        "slack_fraction": round(1 - (ball_sum + river_cells) / (N * N), 4),
        "flap_expansion_max": round(max(expansion), 4) if expansion else None,
        "flap_expansion_median": round(statistics.median(expansion), 4) if expansion else None,
        "mean_layers": round(flap_cells / flap_len, 4) if flap_len else None,
        "creases": len(base.creases),
        "river_corners": river_corners(lay),
        "stretches": len(lay.patches),           # one patch per stretch junction
        "off_grid_vertices": _off_grid(base) if lay.patches else 0,
    }

