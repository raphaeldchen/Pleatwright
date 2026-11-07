"""The Kamiya row: one Pythagorean stretch pair in a box-pleated layout.

Spec: docs/superpowers/specs/2026-10-22-pythagorean-stretch-design.md §4.1-4.3
and §7 (Phase 0a's exact packer-level check).  Gadget geometry is
`stretch.py` (BP Studio's GOPS, MIT, commit 0496ad07); the exact lines and
polygons it is drawn with are `exact2d.py`.

The row (drawn for end = "bottom"; "top" is its mirror in y = N/2)
------------------------------------------------------------------
A Kamiya row lies against a paper end of the sheet.  It holds an axial flap A
(length La, its tip on the end edge at x = N/2) and a mirrored pair P
(length Lp, tips on the side edges), all three on one hub, with the two
diagonal junctions A-P_L and A-P_R resolved by mirrored GOPS gadgets.  With
`RowOpts` (hs, pb, at):

* P_L: rect [0, Lp] x [yc, N], vlines [Lp], hlines [yc, yb], where yb = N + pb
  (a virtual hinge past the paper when pb = 1) and yc = yb - 2 Lp, so its tip
  is the point (0, yb - Lp).  P_R is its mirror.
* A: rect [N/2 - La, N/2 + La] x [ya, N], vlines at its sides, hline ya =
  N - La - at, so its tip is the segment x = N/2, y in [N - at, N].
* slack: [Lp, N - Lp] x [yc, ya], a second region of A's chain whose hinge
  lines are its own four sides (paper folded back at the hub, d < La).
* strip: [0, N] x [yc - hs, yc] when hs = 1, a third region of A's chain with
  hinges on its two long sides: one row of hub slack between the pocket's
  inner hinge and the pair columns, which moves the parity of the next slab.
* the two gadgets.  A's square and P_L's square overlap (N/2 < La + Lp).  The
  patch around each gadget (the bounding box of the overlap, the GOPS piece
  and its two notches, snapped outward to whole cells) is cut exactly into
  convex pieces, each owned by one region with one kind of zone:
  - the piece (parallelogram P0 P1 P2 P3, P0 near A's tip, P2 near P's) is
    split by the tilted hinge T (normal along the GOPS axis, at distance La
    from A's tip and Lp from P's); each half is a region of its flap whose
    only hinge line is T;
  - at the overlap corner C1 = (P's vertical edge, A's horizontal edge) and
    C2 = (A's vertical edge, P's horizontal edge) the hub contour bends: the
    flap on whose far side the corner lies gets a notch, the triangle
    (C, T meets the other flap's edge line, P1 or P3), a region of that flap
    whose hinge is the OTHER flap's edge line.  P1 and P3 are where three
    ridges meet (they are equidistant from T and both edge lines; checked);
  - everything else in the patch is an axis zone of its flap (the overlap
    split by the side of T) or of the slack/strip regions.
  This is the hub contour BP Studio's `trace.ts` draws by reflecting the
  hinge on the gadget's ridges, written as regions whose nearest-hinge-line
  elevation is exact on every piece (spec §4.3's fallback of naming each
  face's zone, realised by giving each zone kind its own region).  Every
  boundary between different flaps is a hinge line of both (d = 0 on both
  sides); a boundary between two regions of one flap is a ridge, where both
  give the same d.

`RowOpts` are three offsets, each 0 or 1: `pair_bottom` and `axial_top` are
virtual hinges that move the axis regions' corners onto the x + y even lattice
(`pack._parity_ok`); `hub_slack` adds the row of hub slack, which moves the
parity of the pocket's inner hinge (the plan first named it the pair columns'
top offset; a virtual top hinge would break the column's own parity, so the
offset is realised as slack, controller ruling 8).

The checker
-----------
`check(lay, con)` is the exact packer-level check of spec §7 Phase 0a: tiling
ownership (cells outside patches owned once, pieces partitioning each patch by
exact area and pairwise disjoint interiors), every flap region's elevation
(nearest of vlines, hlines and lines) at most L everywhere on its cells and
pieces, a nonempty tip set (d = L) per leaf chain, tip sets at least their
tree distance apart (Euclidean across a junction, i.e. when both chains own a
tilted-hinge piece in one patch; L-infinity otherwise), axis-corner parity,
and continuity of d along every edge two regions share (controller ruling
10): two regions of one chain give the same d there, regions of different
chains are both at a hub (d = 0, or a river's far side d = W).  It does not
verify the folded state itself (the accordion coordinate, layer order):
`base.build` does.

The search
----------
`candidates(con, N_min=, N_max=)` puts one Kamiya row at a paper end of a
path-shaped or single-hub tree and packs everything else as
`pack.candidates` does, yielding the layouts `check` accepts.

`hand_layout("dog_1")` is the documented construction behind gate 0 (the plan's
Task 3), kept as a permanent fixture of the tests (controller ruling 2).
"""
from __future__ import annotations

import copy
import itertools
import math
import os
from dataclasses import dataclass
from fractions import Fraction

from . import exact2d as E
from . import pack as PK
from . import stick as ST
from . import stretch as SX
from .pack import Layout, Region

F = Fraction


@dataclass(frozen=True)
class RowOpts:
    """Virtual-hinge offsets of a Kamiya row, each 0 or 1 (module docstring)."""

    hub_slack: int = 0     # rows of hub slack between the row's inner edge and the pair columns
    pair_bottom: int = 0   # the pair columns' outer hinge lies this far past the paper end
    axial_top: int = 0     # the axial region is this much deeper than La


#: all eight offsets, all zeros first, in a fixed order
ROW_OPTS: tuple = tuple(RowOpts(*t) for t in itertools.product((0, 1), repeat=3))


# ------------------------------------------------------------------ the row
def _empty_rect(x, y) -> tuple:
    return (x, y, x, y)


def _rect_minus(rect, cut) -> list:
    x0, y0, x1, y1 = rect
    a0, b0, a1, b1 = cut
    if a0 >= x1 or a1 <= x0 or b0 >= y1 or b1 <= y0:
        return [rect]
    out = []
    if b0 > y0:
        out.append((x0, y0, x1, b0))
    if b1 < y1:
        out.append((x0, b1, x1, y1))
    m0, m1 = max(y0, b0), min(y1, b1)
    if a0 > x0:
        out.append((x0, m0, a0, m1))
    if a1 < x1:
        out.append((a1, m0, x1, m1))
    return out


def _clip_rects(reg: Region, patches) -> None:
    rects = [reg.rect]
    for p in patches:
        rects = [r for rect in rects for r in _rect_minus(rect, p)]
    rects = sorted(r for r in rects if r[0] < r[2] and r[1] < r[3])
    if rects:
        reg.rect, reg.more = rects[0], rects[1:]
    else:
        reg.rect, reg.more = _empty_rect(reg.rect[0], reg.rect[1]), []


def _gadget(N, La, Lp, cA, cP, tipA, tipP, nominal, band):
    """One junction's patch and its pieces, as (patch, [(Region, [poly])]) or None.

    `nominal` maps 'A', 'P' and the slack/strip keys to the row's axis regions."""
    d = La + Lp
    J = SX.junction(tipA, La, tipP, Lp, d)
    if J is None:
        return None
    P0, P1, P2, P3 = J.corners
    fx, fy = E.sign(tipP[0] - tipA[0]), E.sign(tipP[1] - tipA[1])
    a, b, c = SX.axis(J.ox, J.oy, J.g.u, J.g.v)
    # the piece sits on the diagonal between the tips, centred when it is
    # narrower than the tips' offset (spec §4.2, singleJunctionPositioner.ts):
    # P0 is o and P2 is o2 cells from their tips along the 45-degree diagonal,
    # so the axis zones give them d = La - o and Lp - o2 ("arms" of the tips)
    o, o2 = abs(P0[0] - tipA[0]), abs(P2[0] - tipP[0])
    assert abs(P0[1] - tipA[1]) == o and abs(P2[1] - tipP[1]) == o2, "piece off the tips' diagonal"
    nx, ny = fx * a, fy * b
    T = E.canon(nx, ny, nx * P0[0] + ny * P0[1] + (La - o) * c)
    sA = T.side(tipA)
    if sA == 0 or T.side(tipP) != -sA or T.dist(P0) != La - o or T.dist(P2) != Lp - o2:
        return None
    xA, yA = tipA[0] + fx * La, tipA[1] + fy * La        # A's edges facing P
    xB, yB = tipP[0] - fx * Lp, tipP[1] - fy * Lp        # P's edges facing A
    lxA, lyA, lxB, lyB = (E.Line(1, 0, xA), E.Line(0, 1, yA),
                          E.Line(1, 0, xB), E.Line(0, 1, yB))
    over = (min(xA, xB), min(yA, yB), max(xA, xB), max(yA, yB))
    notches = []
    for C, Pk, la, lb in (((xB, yA), P1, lyA, lxB), ((xA, yB), P3, lxA, lyB)):
        if not (la.dist(Pk) == lb.dist(Pk) == T.dist(Pk)):
            return None                      # P1 / P3 must be the three-ridge point
        s = T.side(C)
        if s == 0:
            continue
        owner, hinge = ("P", la) if s == sA else ("A", lb)
        X = E.meet(T, hinge)
        tri = E.ccw([C, X, Pk])
        if E.area2(tri) != 0:
            notches.append((owner, hinge, tri))
    pts = [(over[0], over[1]), (over[2], over[3]), *J.corners,
           *(p for _, _, tri in notches for p in tri)]
    px0 = max(0, math.floor(min(p[0] for p in pts)))
    px1 = min(N, math.ceil(max(p[0] for p in pts)))
    py0 = math.floor(min(p[1] for p in pts))
    py1 = math.ceil(max(p[1] for p in pts))
    if py0 < band[0]:                        # the gadget may only leave by the paper end
        return None
    patch = (px0, max(py0, 0), px1, min(py1, N))
    # cut the patch by every line a zone boundary can lie on
    cuts = {}
    rect_lines = []
    for reg in nominal.values():
        x0, y0, x1, y1 = reg.rect
        rect_lines += [E.Line(1, 0, x0), E.Line(1, 0, x1), E.Line(0, 1, y0), E.Line(0, 1, y1)]
    tri_lines = [E.Line.through(tri[i], tri[(i + 1) % 3]) for _, _, tri in notches for i in range(3)]
    for ln in [*J.ridges, T, lxA, lyA, lxB, lyB, *tri_lines, *rect_lines]:
        ln = E.canon(ln.a, ln.b, ln.c)
        cuts[(ln.a, ln.b, ln.c)] = ln
    faces = [E.rect_poly(patch)]
    for key in sorted(cuts):
        faces = E.cut(faces, cuts[key])
    para = list(J.corners)
    tilt = {"A": Region(cA, _empty_rect(*patch[:2]), [], [], "flap", La, lines=[E.line_list(T)]),
            "P": Region(cP, _empty_rect(*patch[:2]), [], [], "flap", Lp, lines=[E.line_list(T)])}
    notch_regs = []
    for owner, hinge, tri in notches:
        ch, L = (cA, La) if owner == "A" else (cP, Lp)
        vl, hl = ([hinge.c], []) if hinge.a else ([], [hinge.c])
        notch_regs.append((Region(ch, _empty_rect(*patch[:2]), [int(v) for v in vl],
                                  [int(h) for h in hl], "flap", L), tri))
    owned = {}
    for f in faces:
        q = E.centroid(f)
        if E.contains(para, q):
            reg = tilt["A" if T.side(q) == sA else "P"]
        elif any(E.contains(tri, q) for _, tri in notch_regs):
            reg = next(r for r, tri in notch_regs if E.contains(tri, q))
        elif over[0] < q[0] < over[2] and over[1] < q[1] < over[3]:
            reg = nominal["A" if T.side(q) == sA else "P"]
        else:
            hit = [r for r in nominal.values()
                   if r.rect[0] < q[0] < r.rect[2] and r.rect[1] < q[1] < r.rect[3]]
            if len(hit) != 1:
                return None
            reg = hit[0]
        owned.setdefault(id(reg), (reg, []))[1].append(f)
    out = []
    for reg in [*nominal.values(), tilt["A"], tilt["P"], *(r for r, _ in notch_regs)]:
        if id(reg) in owned:
            out.append((reg, [E.ccw(p) for p in E.merge(owned[id(reg)][1])]))
    return patch, out


def _build(N, end, axial, pair, opts, gadget=True):
    """The row's regions and patches, unchecked, or None if it cannot be drawn."""
    if end not in ("bottom", "top"):
        raise ValueError(f"end must be 'bottom' or 'top', not {end!r}")
    if N % 2 or not axial.axial or axial.single or pair.axial or len(pair.chains) != 2:
        return None
    La, Lp = axial.L, pair.L
    hw = N // 2
    yb = N + opts.pair_bottom
    yc = yb - 2 * Lp
    ytop = yc - opts.hub_slack
    ya = N - La - opts.axial_top
    if ytop < 0 or 2 * Lp >= N or hw - La < 0 or hw - La >= Lp or not yc < ya:
        return None
    cA = axial.chains[0]
    cL, cR = pair.chains
    PL = Region(cL, (0, yc, Lp, N), [Lp], [yc, yb], "flap", Lp)
    PR = Region(cR, (N - Lp, yc, N, N), [N - Lp], [yc, yb], "flap", Lp)
    A = Region(cA, (hw - La, ya, hw + La, N), [hw - La, hw + La], [ya], "flap", La)
    slack = Region(cA, (Lp, yc, N - Lp, ya), [Lp, N - Lp], [yc, ya], "flap", La)
    regions = [PL, PR, A, slack]
    if opts.hub_slack:
        regions.append(Region(cA, (0, ytop, N, yc), [], [ytop, yc], "flap", La))
    patches = []
    if gadget:
        extra = []
        for P, cP, xP in ((PL, cL, 0), (PR, cR, N)):
            nominal = {"A": A, "P": P}
            for r in regions[3:]:
                nominal[f"slack{len(nominal)}"] = r
            got = _gadget(N, La, Lp, cA, cP, (F(hw), F(N - opts.axial_top)),
                          (F(xP), F(yb - Lp)), nominal, (ytop, N))
            if got is None:
                return None
            patch, owned = got
            patches.append(patch)
            for reg, polys in owned:
                reg.pieces = reg.pieces + [E.poly_list(p) for p in polys]
                if all(reg is not r for r in regions + extra):
                    extra.append(reg)
        if patches[0][2] > patches[1][0]:
            return None                       # the two gadgets would overlap
        regions += extra
        for reg in regions:
            _clip_rects(reg, patches)
    if end == "top":
        regions = [_flip(r, N) for r in regions]
        patches = [(x0, N - y1, x1, N - y0) for x0, y0, x1, y1 in patches]
        band = (0, N - ytop)
    else:
        band = (ytop, N)
    return regions, patches, band


def _flip(reg: Region, N: int) -> Region:
    """`reg` reflected in y = N/2 (a bottom row turned into a top row)."""
    def fr(r):
        return (r[0], N - r[3], r[2], N - r[1])
    lines = [E.line_list(E.canon(a, -b, F(cn, cd) - b * N)) for a, b, cn, cd in reg.lines]
    pieces = [E.poly_list([(x, N - y) for x, y in E.poly_of(pc)][::-1]) for pc in reg.pieces]
    return Region(reg.chain, fr(reg.rect), list(reg.vlines), sorted(N - h for h in reg.hlines),
                  reg.kind, reg.L, reg.u_line, list(reg.virtual), [fr(r) for r in reg.more],
                  lines, pieces)


def row_parts(N: int, y_end: int, end: str, axial, pair, opts: RowOpts):
    """`row`, with the row's patches and its y band: (regions, patches, (y0, y1))."""
    if y_end != (N if end == "bottom" else 0):
        raise ValueError(f"a {end} row ends at y = {N if end == 'bottom' else 0}, not {y_end}")
    got = _build(N, end, axial, pair, opts)
    if got is None:
        return None
    regions, patches, band = got
    La, Lp = axial.L, pair.L
    cA, (cL, cR) = axial.chains[0], pair.chains
    tree = {frozenset((cA, cL)): La + Lp, frozenset((cA, cR)): La + Lp,
            frozenset((cL, cR)): 2 * Lp}
    if _violations(N, regions, patches, tree, band):
        return None
    return regions, patches, band


def row(N: int, y_end: int, end: str, axial, pair, opts: RowOpts) -> list | None:
    """The regions of a Kamiya row of grid N at the paper end `end` ("bottom":
    y_end = N, "top": y_end = 0), or None when no checker-clean row exists
    with these offsets (module docstring)."""
    got = row_parts(N, y_end, end, axial, pair, opts)
    return None if got is None else got[0]


# ------------------------------------------------------------------ checker
def _dist_fns(reg: Region):
    fs = [(E.Line(1, 0, F(v)), 1) for v in reg.vlines]
    fs += [(E.Line(0, 1, F(h)), 1) for h in reg.hlines]
    for e in reg.lines:
        ln = E.line_of(e)
        fs.append((ln, ln.h))
    return fs


def _max_elev(poly, fs):
    faces = [poly]
    for ln in E.cut_lines(fs):
        faces = E.cut(faces, ln)
    return max(E.elev(fs, p) for f in faces for p in f)


def _tips(poly, fs, L) -> list:
    out = []
    for signs in itertools.product((1, -1), repeat=len(fs)):
        q = poly
        for (ln, h), s in zip(fs, signs):
            q = E.clip_le(q, -s * ln.a, -s * ln.b, -s * ln.c - L * h)
            if not q:
                break
        if q and q not in out:
            out.append(q)
    return out


def _violations(N, regions, patches, tree, band=None) -> list:
    """Every violation of the layout given as parts; `tree` maps frozenset
    chain pairs to their tree distance; `band` restricts the ownership check to
    rows y0 <= y < y1 (a lone row)."""
    out = []
    y0, y1 = band if band is not None else (0, N)
    # 1. ownership
    for i, p in enumerate(patches):
        if not (0 <= p[0] < p[2] <= N and 0 <= p[1] < p[3] <= N):
            out.append(f"ownership: patch {i} {p} is not a rect on the paper")
    for i, j in itertools.combinations(range(len(patches)), 2):
        a, b = patches[i], patches[j]
        if a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]:
            out.append(f"ownership: patches {i} and {j} overlap")

    def in_patch(i, j):
        for k, (a0, b0, a1, b1) in enumerate(patches):
            if a0 <= i < a1 and b0 <= j < b1:
                return k
        return None
    owners = {}
    in_patches = {k: [] for k in range(len(patches))}
    for ri, reg in enumerate(regions):
        for x0, ry0, x1, ry1 in reg.rects:
            for i in range(max(0, x0), min(N, x1)):
                for j in range(max(y0, ry0), min(y1, ry1)):
                    k = in_patch(i, j)
                    if k is None:
                        owners[(i, j)] = owners.get((i, j), 0) + 1
                    else:
                        in_patches[k].append((ri, E.rect_poly((i, j, i + 1, j + 1))))
    twice = sorted(c for c, n in owners.items() if n > 1)
    if twice:
        out.append(f"ownership: {len(twice)} cells owned more than once, e.g. {twice[0]}")
    free = sum(1 for i in range(N) for j in range(y0, y1)
               if in_patch(i, j) is None and (i, j) not in owners)
    if free:
        out.append(f"ownership: {free} cells outside patches uncovered")
    for ri, reg in enumerate(regions):
        for pc in reg.pieces:
            poly = E.poly_of(pc)
            if not E.convex(poly):
                out.append(f"ownership: a piece of region {ri} is not a convex polygon")
                continue
            ks = [k for k, (a0, b0, a1, b1) in enumerate(patches)
                  if all(a0 <= x <= a1 and b0 <= y <= b1 for x, y in poly)]
            if not ks:
                out.append(f"ownership: a piece of region {ri} lies outside every patch")
                continue
            in_patches[ks[0]].append((ri, poly))
    for k, items in in_patches.items():
        a0, b0, a1, b1 = patches[k]
        area = sum(abs(E.area2(p)) for _, p in items) / 2
        if area != (a1 - a0) * (b1 - b0):
            out.append(f"ownership: patch {k} pieces cover area {area} of {(a1 - a0) * (b1 - b0)}")
        boxes = [(min(x for x, _ in p), min(y for _, y in p), max(x for x, _ in p),
                  max(y for _, y in p)) for _, p in items]
        for i, j in itertools.combinations(range(len(items)), 2):
            bi, bj = boxes[i], boxes[j]
            if bi[0] >= bj[2] or bj[0] >= bi[2] or bi[1] >= bj[3] or bj[1] >= bi[3]:
                continue
            if not E.disjoint(items[i][1], items[j][1]):
                out.append(f"ownership: pieces of regions {items[i][0]} and {items[j][0]} "
                           f"overlap in patch {k}")
    # 2./3. elevation and tip sets of every flap region (cells outside patches, pieces)
    polys_of = [_region_polys(N, reg, patches, (y0, y1)) for reg in regions]
    tips = {}
    for ri, reg in enumerate(regions):
        if reg.kind != "flap":
            continue
        try:
            fs = _dist_fns(reg)
        except ValueError as e:
            out.append(f"elevation: region {ri}: {e}")
            continue
        if not fs:
            out.append(f"elevation: region {ri} (chain {reg.chain}) has no hinge line")
            continue
        polys = polys_of[ri]
        if not polys:
            continue
        top = max(_max_elev(p, fs) for p in polys)
        if top > reg.L:
            out.append(f"elevation: region {ri} (chain {reg.chain}) reaches d = {top} > L = {reg.L}")
        for p in polys:
            tips.setdefault(reg.chain, [])
            for t in _tips(p, fs, reg.L):
                if t not in tips[reg.chain]:
                    tips[reg.chain].append(t)
    leaves = sorted({c for pair in tree for c in pair})
    for c in leaves:
        if not tips.get(c):
            out.append(f"tip: chain {c} has no tip (no point at d = L)")
    # 4. tip distances
    joined = set()
    for k, (a0, b0, a1, b1) in enumerate(patches):
        chains = sorted({reg.chain for reg in regions if reg.lines for pc in reg.pieces
                         if all(a0 <= x <= a1 and b0 <= y <= b1 for x, y in E.poly_of(pc))})
        joined |= {frozenset(p) for p in itertools.combinations(chains, 2)}
    for ci, cj in itertools.combinations(leaves, 2):
        D = tree.get(frozenset((ci, cj)))
        if D is None or not tips.get(ci) or not tips.get(cj):
            continue
        euclid = frozenset((ci, cj)) in joined
        got = min(E.set_dist(P, Q, euclid) for P in tips[ci] for Q in tips[cj])
        if got < (D * D if euclid else D):
            shown = f"sqrt({got})" if euclid else f"{got}"
            out.append(f"tip distance: chains {ci} and {cj} are {shown} < {D} apart "
                       f"({'euclidean' if euclid else 'L-infinity'})")
    # 5. parity
    for ri, reg in enumerate(regions):
        if not PK._parity_ok(reg):
            out.append(f"parity: region {ri} (chain {reg.chain}) has a hinge corner "
                       "off the x + y even lattice")
    # 6. continuity along every edge two regions share (controller ruling 10)
    out += _continuity(regions, polys_of)
    return out


def _region_polys(N, reg: Region, patches, band) -> list:
    """The exact polygons of `reg` in rows band[0] <= y < band[1]: its rects
    minus the patches (clipped to the paper), then its pieces."""
    y0, y1 = band
    polys = []
    for rect in reg.rects:
        parts = [rect]
        for p in patches:
            parts = [r for q in parts for r in _rect_minus(q, p)]
        for x0, ry0, x1, ry1 in parts:
            r = (max(0, x0), max(y0, ry0), min(N, x1), min(y1, ry1))
            if r[0] < r[2] and r[1] < r[3]:
                polys.append(E.rect_poly(r))
    return polys + [E.poly_of(pc) for pc in reg.pieces]


def _shared(regions, polys_of):
    """Every maximal stretch of edge two different regions' polygons share:
    [(ri, rj, line, t0, t1)], t0 < t1, in a deterministic order."""
    groups = {}
    for ri, polys in enumerate(polys_of):
        for poly in polys:
            n = len(poly)
            for i in range(n):
                p, q = poly[i], poly[(i + 1) % n]
                if p == q:
                    continue
                ln, tp, tq = E.edge_line(p, q)
                groups.setdefault((ln.a, ln.b, ln.c), (ln, []))[1].append((ri, min(tp, tq), max(tp, tq)))
    out = []
    for key in sorted(groups):
        ln, edges = groups[key]
        for (ri, a0, a1), (rj, b0, b1) in itertools.combinations(edges, 2):
            lo, hi = max(a0, b0), min(a1, b1)
            if ri != rj and lo < hi:
                out.append((min(ri, rj), max(ri, rj), ln, lo, hi))
    return out


def shared_edges(N: int, regions, patches) -> int:
    """How many stretches of edge different regions share (the continuity
    test's work).  Not used by the pipeline: tests/test_kamiya.py reads it to
    show the continuity test sees the gadget (a non-vacuity guard)."""
    return len(_shared(regions, [_region_polys(N, r, patches, (0, N)) for r in regions]))


def _at_hub(reg: Region, d) -> bool:
    """d is a hub's elevation in `reg`: 0 (a hinge), or a river's far side."""
    return d == 0 or (reg.kind == "river" and d == reg.L)


def _continuity(regions, polys_of) -> list:
    """Along every edge two regions share, two regions of one chain must give
    the same d and regions of different chains must both be at a hub
    (`_at_hub`).  Exact: d of each side is linear between its `exact2d.cut_lines`,
    so the test is made at every crossing of those lines and at both ends."""
    fns = {}
    for ri, reg in enumerate(regions):
        try:
            fs = _dist_fns(reg)
        except ValueError:
            fs = []                          # reported as an elevation violation
        fns[ri] = (fs, E.cut_lines(fs)) if fs else None
    out, bad = [], set()
    for ri, rj, ln, lo, hi in _shared(regions, polys_of):
        if (ri, rj) in bad or fns[ri] is None or fns[rj] is None:
            continue
        nn = ln.a * ln.a + ln.b * ln.b

        def at(t):
            return ((ln.a * ln.c - ln.b * t) / nn, (ln.b * ln.c + ln.a * t) / nn)
        P, Q = at(lo), at(hi)
        ss = {F(0), F(1)}
        for cut in fns[ri][1] + fns[rj][1]:
            v0, v1 = E.val(cut, P), E.val(cut, Q)
            if (v0 < 0 < v1) or (v1 < 0 < v0):
                ss.add(v0 / (v0 - v1))
        A, B = regions[ri], regions[rj]
        for sv in sorted(ss):
            x = (P[0] + sv * (Q[0] - P[0]), P[1] + sv * (Q[1] - P[1]))
            di, dj = E.elev(fns[ri][0], x), E.elev(fns[rj][0], x)
            ok = di == dj if A.chain == B.chain else (_at_hub(A, di) and _at_hub(B, dj))
            if not ok:
                bad.add((ri, rj))
                out.append(f"continuity: regions {ri} and {rj} (chains {A.chain}, {B.chain}) "
                           f"meet at ({x[0]}, {x[1]}) with d = {di} and {dj}")
                break
    return out


def tree_distances(con: ST.Contracted) -> dict:
    """{frozenset((leaf chain i, leaf chain j)): tip-to-tip tree distance}."""
    adj = {}
    for c in con.chains:
        adj.setdefault(c.u, []).append((c.v, c.length))
        adj.setdefault(c.v, []).append((c.u, c.length))
    leaves = [c for c in con.chains if c.leaf]
    out = {}
    for a in leaves:
        dist, st = {a.v: 0}, [a.v]
        while st:
            u = st.pop()
            for v, L in adj[u]:
                if v not in dist:
                    dist[v] = dist[u] + L
                    st.append(v)
        for b in leaves:
            if b.id != a.id:
                out[frozenset((a.id, b.id))] = dist[b.v]
    return out


def check(lay: Layout, con: ST.Contracted) -> list:
    """The violations of `lay` (module docstring), [] if none."""
    return _violations(lay.N, lay.regions, lay.patches, tree_distances(con))


# ------------------------------------------------------------------ search
def candidates(con: ST.Contracted, *, N_min: int, N_max: int, per_N: int = 60):
    """Stretched layouts (family "stretched") of a path-shaped or single-hub
    tree, at most `per_N` per even grid N_min <= N <= N_max, N ascending.

    Each has one Kamiya row (`row_parts`) at the paper end of an end slab of
    `pack.hub_path(con)`: the bottom slab's bottom end first, then the top
    slab's top end (a single hub: its bottom end).  The row holds an axial
    item and an equal-length mirrored pair of that hub (`pack._items_sym`
    order, axials outer, pairs inner; `ROW_OPTS` order).  The rest of that
    slab (the hub's other items, between the slab's far side and the row's
    inner hinge) and every other slab and river band are packed as
    `pack.candidates` packs them, by the same code: the slab-height programme
    `pack.slab_heights`, `pack.slab_solutions` per pocket, the
    `pack.regions_ok` filter on the regions today's row builder makes.  Only
    one hub order is tried: the row's paper end picks it.  The Kamiya row's own
    regions are not given that filter (its slack regions stay below L by
    design and its piece-only regions have empty rects); the whole layout
    must pass `check` instead.  A branching hub graph yields nothing.

    `pack.tick()` is spent per row option, per pocket-row assignment (inside
    `_pocket_solutions`) and per combination of pocket solutions, so
    `pack.work_budget` bounds the search.  No set or dict decides an order."""
    _, nb = PK._hub_graph(con)
    if any(len(v) > 2 for v in nb.values()):
        return
    order = PK.hub_path(con)
    k = len(order)
    by_hubs = {}
    for c in con.chains:
        if not c.leaf:
            by_hubs[frozenset((c.u, c.v))] = c
    rivers = [by_hubs[frozenset((order[i], order[i + 1]))] for i in range(k - 1)]
    items = [PK._items_sym(con, h) for h in order]
    sides = [("paper" if i == 0 else "hinge", "paper" if i == k - 1 else "hinge")
             for i in range(k)]
    ends = (("bottom", k - 1), ("top", 0)) if k > 1 else (("bottom", 0),)
    tree = tree_distances(con)
    G = max(N_min, 2)
    G += G % 2
    for N in range(G, N_max + 1, 2):
        yield from itertools.islice(
            _layouts_at(N, order, rivers, items, sides, ends, tree), per_N)


def _layouts_at(N, order, rivers, items, sides, ends, tree):
    """Every checked stretched layout of grid N (`candidates`), in order."""
    for end, ki in ends:
        axials = [it for it in items[ki] if it.axial]
        pairs = [it for it in items[ki] if not it.axial and len(it.chains) == 2]
        for axial in axials:
            for pair in pairs:
                rest = [it for it in items[ki] if it is not axial and it is not pair]
                for opts in ROW_OPTS:
                    PK.tick()
                    got = row_parts(N, N if end == "bottom" else 0, end, axial, pair, opts)
                    if got is not None:
                        yield from _complete(N, order, rivers, items, sides, ki, end, rest,
                                             got, tree)


def _complete(N, order, rivers, items, sides, ki, end, rest, row_got, tree):
    """The layouts that put the Kamiya row `row_got` (`row_parts`) in slab
    `ki` and pack the rest as `pack.candidates` does (`pack.slab_heights`,
    `pack.stack`, `pack.slab_solutions`, `pack.regions_ok`)."""
    row_regs, patches, (ry0, ry1) = row_got
    rowH = ry1 - ry0
    k = len(order)

    def rest_pocket(y, H):
        """The rest of slab ki, starting at y with height H: (y0, y1, top, bot)."""
        if end == "bottom":
            return y, y + H - rowH, sides[ki][0], "hinge"
        return y + rowH, y + H, "hinge", sides[ki][1]

    def feasible(i, y, H):
        if i == ki:
            if not rest:
                return H == rowH
            if H - rowH < 1:
                return False
            g = PK._pocket_solutions(rest, N, *rest_pocket(y, H), limit=1)
            return next(g, None) is not None
        if not items[i]:
            return True
        g = PK._pocket_solutions(items[i], N, y, y + H, *sides[i], limit=1)
        return next(g, None) is not None

    for heights in PK.slab_heights(N, [r.length for r in rivers], feasible):
        slabs, bands = PK.stack(order, heights, rivers)
        pocket_sols = []
        for i in range(k):
            hub, a_, b_ = slabs[i]
            if i == ki:
                pocket_sols.append(PK.slab_solutions(rest, N, rest_pocket(a_, b_ - a_)))
            else:
                pocket_sols.append(PK.slab_solutions(items[i], N, (a_, b_, *sides[i])))
        for combo in itertools.product(*pocket_sols):
            PK.tick()
            per_slab = [PK.solution_regions(N, rows) for rows in combo]
            if not all(PK.regions_ok(regs) for regs in per_slab):
                continue
            regs = []
            for i in range(k):
                if i == ki:
                    kam = copy.deepcopy(row_regs)
                    regs += per_slab[i] + kam if end == "bottom" else kam + per_slab[i]
                else:
                    regs += per_slab[i]
                if i < k - 1:
                    _, a_, b_ = bands[i]
                    regs.append(PK.river_region(N, rivers[i], a_, b_, rivers[i].u == order[i]))
            if _violations(N, regs, patches, tree):
                continue
            lay = Layout(N, regs, list(order), bands, slabs, family="stretched",
                         patches=list(patches))
            lay.score = PK._score(lay)
            yield lay


# ------------------------------------------------------------------ by hand
_STICKS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "fixtures", "full17_v3_sticks")

#: roll -> (Kamiya hub, grid, offsets).  dog_1 (head 16 axial, forelegs 19,
#: withers -- river 3 -- hips): the gadget needs the tip offsets sx, sy odd
#: (d = 35 odd, an overlap side even), which with the head's tip at x = N/2
#: forces N/2 odd; then the hips row (hindlegs 16 paired, tail 8 axial,
#: half-width N/2 odd) packs only when its hinge row is odd, i.e. with one row
#: of hub slack under the river (hub_slack = 1).  pair_bottom = 1 and
#: axial_top = 1 put the forelegs' and head's hinge corners on the even
#: lattice.  N = 62 (today 72; the no-tiling Kamiya bound 58).
HAND = {"dog_1": ("withers", 62, RowOpts(1, 1, 1))}


def hand_layout(roll: str, gadget: bool = True) -> Layout:
    """The hand-built stretched layout of `roll` (HAND): today's slab and river
    for the other hub, the Kamiya hub's slab as one Kamiya row at the bottom.
    `gadget=False` keeps the overlapping squares without the gadgets (a layout
    `check` must reject)."""
    if roll not in HAND:
        raise ValueError(f"no hand-built Kamiya layout for {roll!r}")
    hub, N, opts = HAND[roll]
    con = ST.contract(ST.load_roll(os.path.join(_STICKS, f"{roll}.json"), 1.0))
    order = PK.hub_path(con)
    if len(order) != 2:
        raise ValueError("hand_layout builds two-hub trees only")
    if order[-1] != hub:
        order = order[::-1]
    items = PK._items_sym(con, hub)
    axial = next(i for i in items if i.axial)
    pair = next(i for i in items if not i.axial)
    got = _build(N, "bottom", axial, pair, opts, gadget)
    if got is None:
        raise ValueError(f"no Kamiya row for {roll} at N = {N} with {opts}")
    regions, patches, band = got
    river = next(c for c in con.chains if not c.leaf and {c.u, c.v} == set(order))
    yr = band[0]
    H = yr - river.length
    other = None
    for rows in PK._pocket_solutions(PK._items_sym(con, order[0]), N, 0, H, "paper", "hinge"):
        regs = PK.solution_regions(N, rows)
        if PK.regions_ok(regs):
            other = regs
            break
    if other is None:
        raise ValueError(f"{order[0]} does not pack in {N} x {H}")
    band_reg = PK.river_region(N, river, H, yr, river.u == order[0])
    lay = Layout(N, other + regions + [band_reg], order, [(river.id, H, yr)],
                 [(order[0], 0, H), (hub, yr, N)], family="stretched", patches=patches)
    lay.score = PK._score(lay)
    return lay
