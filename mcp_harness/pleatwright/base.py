"""The collapsed base: packing layout -> flat-folded strip and its creases.

COrigami's solved base is "a dense, flat-folded strip of paper" (§3.4); its
measured width is exactly one grid unit (fold their Ram solving CP: a 1 x 16
unit strip).  We build that folded state analytically from the packing:

* every point p in the region of tree edge e = (u -> v) sits on the tree at
  distance d(p) from u, where d is the L-infinity distance to the region's
  hinge lines; its position ALONG the strip is s = strip(u) + sigma_e * d(p)
  (sigma_e = +-1: which way edge e runs along the strip -- the hinge
  assignment freedom of §3.3);
* its position ACROSS the strip is the accordion coordinate w = tri(x) where
  d grows vertically (pleats perpendicular to a horizontal hinge) and
  w = tri(y) where d grows horizontally, tri being the period-2 triangle
  wave.  This is exactly the "pleats share a uniform orthogonal
  orientation within each region" construction of §3.3 / F.1.1.

d, tri(x) and tri(y) are affine on each quarter of each unit cell (cells cut
by both diagonals), so the folded state is a piecewise-isometric map on that
triangulation.  `build` verifies isometry on every triangle and continuity at
every shared vertex -- a packing that fails either is rejected -- and then
reads the crease set off it: two neighbouring triangles whose maps differ by
a reflection across their shared edge meet at a crease.  Each crease is
classified as a hinge (region boundary), ridge (gradient switches: the
straight skeleton) or pleat (accordion line).
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np

from .cp import CP, Edge
from .pack import Layout


def tri(t: float) -> float:
    m = t % 2.0
    return m if m <= 1.0 else 2.0 - m


@dataclass
class Tri:
    pts: tuple              # three (x, y) grid points
    chain: int
    region: int
    zone: tuple             # ('v', line) or ('h', line): nearest hinge line
    A: np.ndarray           # 2x2 linear part of paper -> strip (s, w)
    b: np.ndarray           # translation
    d: tuple                # elevation at the three points

    def map(self, p):
        return self.A @ np.asarray(p, float) + self.b

    @property
    def det(self) -> float:
        return float(np.linalg.det(self.A))


@dataclass
class Base:
    N: int
    layout: Layout
    sigma: dict             # chain -> +1/-1
    strip: dict             # node -> strip position
    tris: list              # list[Tri]
    creases: dict           # unit segment key -> {'kind': H/R/P, 'tris': (i, j)}
    boundary_edges: set     # unit segments on region boundaries (incl. flat hinges)
    errors: list = field(default_factory=list)

    def tri_index(self):
        return {(t.pts[0], t.pts[1]): i for i, t in enumerate(self.tris)}


class BaseError(Exception):
    pass


def strip_positions(con, sigma) -> dict:
    pos = {con.root: 0.0}
    q = [con.root]
    ch = defaultdict(list)
    for c in con.chains:
        ch[c.u].append(c)
    while q:
        u = q.pop(0)
        for c in ch[u]:
            pos[c.v] = pos[u] + sigma[c.id] * c.length
            q.append(c.v)
    return pos


def build(lay: Layout, con, sigma: dict) -> Base:
    N = lay.N
    strip = strip_positions(con, sigma)
    owner = {}
    for ri, r in enumerate(lay.regions):
        for x0, y0, x1, y1 in r.rects:
            for i in range(max(0, x0), min(N, x1)):
                for j in range(max(0, y0), min(N, y1)):
                    if (i, j) in owner:
                        raise BaseError(f"cell {(i, j)} owned twice")
                    owner[(i, j)] = ri
    if len(owner) != N * N:
        raise BaseError(f"tiling incomplete: {N * N - len(owner)} cells uncovered")

    tris = []
    for (i, j), ri in owner.items():
        r = lay.regions[ri]
        c = con.chains[r.chain]
        u_pos = strip[c.u]
        sg = sigma[c.id]
        corners = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
        ctr = (i + 0.5, j + 0.5)
        for k in range(4):
            P = (corners[k], corners[(k + 1) % 4], ctr)
            cen = ((P[0][0] + P[1][0] + P[2][0]) / 3, (P[0][1] + P[1][1] + P[2][1]) / 3)
            zone = _zone(r, cen)
            ds, sw = [], []
            for p in P:
                d = _dist(r, p)
                ds.append(d)
                s = u_pos + sg * d
                w = tri(p[0]) if zone[0] == "h" else tri(p[1])
                sw.append((s, w))
            A, b = _affine(P, sw)
            tris.append(Tri(P, c.id, ri, zone, A, b, tuple(ds)))

    errors = []
    for t in tris:
        if np.abs(t.A.T @ t.A - np.eye(2)).max() > 1e-9:
            errors.append(("not_isometric", t.pts, t.chain))
            break
    # continuity
    img = defaultdict(list)
    for ti, t in enumerate(tris):
        for p in t.pts:
            img[p].append((ti, tuple(np.round(t.map(p), 9))))
    for p, lst in img.items():
        vals = {v for _, v in lst}
        if len(vals) > 1:
            errors.append(("discontinuous", p, sorted(vals)[:3]))
            if len(errors) > 20:
                break
    if errors:
        b = Base(N, lay, sigma, strip, tris, {}, set(), errors)
        return b

    # creases
    edge_tris = defaultdict(list)
    for ti, t in enumerate(tris):
        for a in range(3):
            p, q = t.pts[a], t.pts[(a + 1) % 3]
            edge_tris[_key(p, q)].append(ti)
    creases, bnd = {}, set()
    for k, lst in edge_tris.items():
        if len(lst) != 2:
            continue
        i, j = lst
        ti, tj = tris[i], tris[j]
        same = np.allclose(ti.A, tj.A, atol=1e-9) and np.allclose(ti.b, tj.b, atol=1e-9)
        diff_region = ti.region != tj.region
        if diff_region:
            bnd.add(k)
        if same:
            continue
        if diff_region:
            kind = "H"
        elif ti.zone == tj.zone:
            kind = "P"
        else:
            kind = "R"
        creases[k] = {"kind": kind, "tris": (i, j)}
    return Base(N, lay, sigma, strip, tris, creases, bnd, [])


def _key(p, q):
    return (p, q) if p <= q else (q, p)


def _dist(r, p):
    ds = [abs(p[0] - v) for v in r.vlines] + [abs(p[1] - h) for h in r.hlines]
    return min(ds)


def _zone(r, p):
    best = None
    for v in r.vlines:
        d = abs(p[0] - v)
        if best is None or d < best[0] - 1e-12:
            best = (d, ("v", v))
    for h in r.hlines:
        d = abs(p[1] - h)
        if best is None or d < best[0] - 1e-12:
            best = (d, ("h", h))
    return best[1]


def _affine(P, Q):
    M = np.array([[P[0][0], P[0][1], 1.0], [P[1][0], P[1][1], 1.0], [P[2][0], P[2][1], 1.0]])
    sol = np.linalg.solve(M, np.array(Q, float))
    A = sol[:2, :].T
    b = sol[2, :]
    return A, b


# ------------------------------------------------------------------ CP views
def merged_segments(N, keys_kinds, extra=()):
    """Merge unit segments (with a label) into maximal collinear runs that
    never pass THROUGH a vertex another drawn segment touches (so every
    crossing stays a vertex, as COrigami's face finder requires).  `extra`
    are further unit segments (e.g. the border) that count for degree."""
    deg = defaultdict(int)
    for (p, q), _ in keys_kinds:
        deg[p] += 1
        deg[q] += 1
    for p, q in extra:
        deg[p] += 1
        deg[q] += 1
    for x in range(N + 1):
        for y in (0, N):
            deg[(x, y)] += 2
            deg[(y, x)] += 2
    lines = defaultdict(list)
    for (p, q), lab in keys_kinds:
        dx, dy = q[0] - p[0], q[1] - p[1]
        g = math.gcd(int(round(2 * dx)), int(round(2 * dy))) or 1
        dirv = (round(2 * dx) // g, round(2 * dy) // g)
        if dirv < (0, 0):
            dirv = (-dirv[0], -dirv[1])
        # line id: direction + offset (cross product with direction)
        off = round(2 * (p[0] * dirv[1] - p[1] * dirv[0]), 6)
        lines[(dirv, off, lab)].append((p, q))
    out = []
    for (dirv, off, lab), segs in lines.items():
        def tpar(pt):
            return pt[0] * dirv[0] + pt[1] * dirv[1]
        iv = sorted((min(tpar(p), tpar(q)), max(tpar(p), tpar(q)), p, q) for p, q in segs)
        cur = None
        for a, b, p, q in iv:
            pa, pb = (p, q) if tpar(p) <= tpar(q) else (q, p)
            if cur and abs(a - cur[1]) < 1e-9 and deg[pa] == 2:
                cur = (cur[0], b, cur[2], pb)
            else:
                if cur:
                    out.append(((cur[2], cur[3]), lab))
                cur = (a, b, pa, pb)
        if cur:
            out.append(((cur[2], cur[3]), lab))
    return out


def border_edges(N, touch=()):
    """Paper border, split at every point where a crease meets it (COrigami's
    SVGs list the border piecewise, e.g. (0,0)-(0,133), (0,133)-(0,333))."""
    cuts = {"t": {0, N}, "b": {0, N}, "l": {0, N}, "r": {0, N}}
    for p in touch:
        x, y = p
        if abs(y) < 1e-9:
            cuts["t"].add(x)
        if abs(y - N) < 1e-9:
            cuts["b"].add(x)
        if abs(x) < 1e-9:
            cuts["l"].add(y)
        if abs(x - N) < 1e-9:
            cuts["r"].add(y)
    out = []
    for side, vals in cuts.items():
        vs = sorted(vals)
        for a, b in zip(vs, vs[1:]):
            if side == "t":
                out.append(Edge((a, 0), (b, 0), "B"))
            elif side == "b":
                out.append(Edge((a, N), (b, N), "B"))
            elif side == "l":
                out.append(Edge((0, a), (0, b), "B"))
            else:
                out.append(Edge((N, a), (N, b), "B"))
    return out


def packing_cp(base: Base) -> tuple:
    """Hinges (all region boundaries, green) + ridges (red) + border."""
    items = [(k, "H") for k in base.boundary_edges]
    items += [(k, "R") for k, v in base.creases.items() if v["kind"] == "R"]
    segs = merged_segments(base.N, items)
    edges = border_edges(base.N, [p for (a, b), _ in segs for p in (a, b)])
    for (p, q), lab in segs:
        edges.append(Edge(p, q, lab))
    # red dots: ridge junctions (>= 3 ridge segments meet)
    cnt = defaultdict(int)
    for k, v in base.creases.items():
        if v["kind"] == "R":
            cnt[k[0]] += 1
            cnt[k[1]] += 1
    dots = [p for p, n in cnt.items() if n >= 3 and 0 < p[0] < base.N and 0 < p[1] < base.N]
    return CP(base.N, edges), dots
