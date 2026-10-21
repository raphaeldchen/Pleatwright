"""Paper-efficiency metrics for a packed base (spec
docs/superpowers/specs/2026-10-16-packing-layout-choice-design.md section 6).

Recorded only: nothing here steers the packer.  The reference implementation is
docs/superpowers/evidence/2026-10-16-layout-choice/bp_efficiency_probe.py."""
from __future__ import annotations

import math
import statistics

from .base import Base, _dist
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


def river_corners(lay: Layout) -> int:
    """Corners of river bands strictly inside the paper (0 < x, y < N): the
    lattice points where 1 or 3 of a river region's cells meet, or 2 diagonal
    ones (counted twice), the rule of
    docs/superpowers/evidence/2026-10-19-river-routing/corigami_samples/regions.py
    `corners()`.  BP Studio's tidiness measure, recorded only (spec 2026-10-19 §7)."""
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


def metrics(lay: Layout, con: Contracted, base: Base, scale: float) -> dict:
    """The section-6 efficiency record of one packed layout.  `scale` is the
    length multiplier of the run (2.0 when every length was doubled), so
    `scale` in the result is in original units."""
    N = lay.N
    total = sum(c.length for c in con.chains)
    bound = math.ceil(total / 2)
    flap_cells = ball_sum = river_cells = 0
    expansion = []
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
    }

