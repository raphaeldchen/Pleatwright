"""COrigami §3.4-3.6 / App. G: shaping the collapsed base with simple folds.

The simple fold (§3.5).  Given a cut line, every folded face it crosses is
split; the resulting segments become shaping creases whose M/V follows from
the fold sense and the face's orientation.  Folds can be restricted to the
faces of one flap/river and its descendants ("selectively shaping subsets").

Tree shaping (§3.6, App. G.1).  Breadth-first from the root stick: the
paper of stick s_child, rigidly attached to its shaped parent, currently
points along c = F_init v1 (+-, by its direction along the strip).  The
rotation R taking c to the stick-figure direction t must be a simple fold,
i.e. its axis lies in the parent's paper plane span{v1, v2}; that fixes R
uniquely and gives the cut line.  The line passes through the joint (the
end of the hinge that keeps it on the distal side of the stick's own
layers, so nothing tears) and is applied to the stick's subtree only.

Implementation.  The base is the piecewise-isometric strip map of
`base.build` (paper triangle -> (s, w) strip coordinates, a flat 3-D frame
X = s, Y = w, Z = 0).  Every stick k contributes a rigid motion K_k (rotation
by phi_k about its cut line, in base coordinates); a paper point's world
transform is G_group = K_root_stick ... K_k composed down its stick path for
as long as the point lies on the distal side of each cut.  Every base
triangle is split by the pre-image of every cut line (the pre-images agree
along shared edges, so the subdivision is conforming); each crease's signed
fold angle is the dihedral between its two pieces' world transforms, written
as COrigami does: stroke colour = sign, opacity = |angle| / 180.
"""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np

from .base import Base
from .cp import CP, Edge

X, Y, Z = np.eye(3)


@dataclass
class FoldOp:
    stick: str
    parent: str | None
    pivot: np.ndarray       # base coords (s, w, 0)
    axis: np.ndarray        # unit, base coords (in the z = 0 plane)
    phi: float              # radians
    sigma: int
    s_joint: float
    subtree: set            # stick names rotated by this op (stick + descendants)
    distal: np.ndarray      # a base point known to be on the rotating side


@dataclass
class Shaped:
    cp: CP
    ops: list
    pieces: list            # (paper polygon, world 4x4)
    root_frame: np.ndarray
    stats: dict = field(default_factory=dict)


def _rot(axis, ang):
    x, y, z = axis
    c, s = math.cos(ang), math.sin(ang)
    C = 1 - c
    return np.array([[c + x * x * C, x * y * C - z * s, x * z * C + y * s],
                     [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
                     [z * x * C - y * s, z * y * C + x * s, c + z * z * C]])


def _h(R=None, t=None):
    M = np.eye(4)
    if R is not None:
        M[:3, :3] = R
    if t is not None:
        M[:3, 3] = t
    return M


def _about_line(point, axis, ang):
    """4x4 rotation about the line through `point` along `axis`."""
    return _h(t=point) @ _h(_rot(axis, ang)) @ _h(t=-point)


# ------------------------------------------------------------- stick geometry
def stick_layout(sf, con, sigma, strip):
    """For every stick: chain, start offset, end offset, strip joint position,
    sigma, parent stick, children sticks."""
    info = {}
    for c in con.chains:
        for k, name in enumerate(c.sticks):
            off0 = c.offsets[k]
            off1 = c.offsets[k + 1] if k + 1 < len(c.sticks) else c.length
            parent = c.sticks[k - 1] if k > 0 else None
            info[name] = dict(chain=c.id, off0=off0, off1=off1, sigma=sigma[c.id],
                              s_joint=strip[c.u] + sigma[c.id] * off0, parent=parent,
                              hub=c.u if k == 0 else None)
    # parent of a chain's first stick = the stick that ends at the chain's hub
    end_at = {}
    for c in con.chains:
        end_at[c.v] = c.sticks[-1]
    for name, d in info.items():
        if d["parent"] is None and d["hub"] is not None:
            d["parent"] = end_at.get(d["hub"])     # None at the root hub
    children = defaultdict(list)
    for name, d in info.items():
        children[d["parent"]].append(name)
    return info, children


def _subtree(children, name):
    out, st = set(), [name]
    while st:
        x = st.pop()
        out.add(x)
        st += children.get(x, [])
    return out


def chain_dirs(sf, con):
    """Unit direction of every stick AS ITS CHAIN RUNS (away from the
    packing root).  A chain through the authored root can traverse a stick
    end -> start; its direction along the chain is then reversed."""
    dirs = {s.name: s.direction / np.linalg.norm(s.direction) for s in sf.sticks}
    for c in con.chains:
        for name, rev in zip(c.sticks, c.reversed or [False] * len(c.sticks)):
            if rev:
                dirs[name] = -dirs[name]
    return dirs


def choose_sigma(sf, con):
    """Direction of each contracted edge along the strip (§3.3 hinge freedom):
    the root stick runs +s; every other root branch runs +s if its first
    stick points with the root stick, else -s; descendants inherit."""
    dirs = chain_dirs(sf, con)
    rc = root_chain(con)
    t_r = dirs[con.chains[rc].sticks[0]]
    sigma = {}
    for c in con.chains:
        if c.u == con.root:
            if c.id == rc:
                sigma[c.id] = 1
            else:
                sigma[c.id] = 1 if float(dirs[c.sticks[0]] @ t_r) >= 0 else -1
    changed = True
    while changed:
        changed = False
        for c in con.chains:
            if c.id in sigma:
                continue
            par = next((p for p in con.chains if p.v == c.u), None)
            if par is not None and par.id in sigma:
                sigma[c.id] = sigma[par.id]
                changed = True
    return sigma


def root_chain(con):
    """The root stick: the river leaving the root hub if there is one (the
    body/spine), else the longest flap at the root."""
    at_root = [c for c in con.chains if c.u == con.root]
    rivers = [c for c in at_root if not c.leaf]
    if rivers:
        return max(rivers, key=lambda c: c.length).id
    return max(at_root, key=lambda c: c.length).id


def root_frame(sf, t_root, sigma_root):
    """Rotation base -> world with sigma_root * X -> t_root.  The paper
    plane normal is the direction most orthogonal to all sticks (smallest
    eigenvector of their scatter, projected off t_root), so as many sticks as
    possible lie in the paper plane and need in-plane (flat) folds only."""
    D = np.array([s.direction * s.length for s in sf.sticks])
    S = D.T @ D
    t = t_root / np.linalg.norm(t_root)
    P = np.eye(3) - np.outer(t, t)
    w, V = np.linalg.eigh(P @ S @ P + 1e-9 * np.outer(t, t) * 1e6)
    # smallest eigenvalue among directions orthogonal to t
    best = None
    for k in range(3):
        v = V[:, k]
        if abs(v @ t) > 0.5:
            continue
        if best is None or w[k] < best[0]:
            best = (w[k], v)
    n = best[1] - (best[1] @ t) * t
    n /= np.linalg.norm(n)
    e1 = sigma_root * t
    e3 = n
    e2 = np.cross(e3, e1)
    return np.c_[e1, e2, e3]          # columns = images of X, Y, Z


def _single(Q, sg, t):
    """G.1: the unique rotation with axis in the paper plane span{Q X, Q Y}
    taking c = sg Q X to t.  Returns (alpha, phi, a_base) or None."""
    u1, u2 = Q @ X, Q @ Y
    c = sg * u1
    A = sg - float(t @ u1)
    B = float(t @ u2)
    if abs(A) < 1e-9 and abs(B) < 1e-9:
        return None
    alpha = math.atan2(A, B)
    a_base = math.cos(alpha) * X + math.sin(alpha) * Y
    a_w = Q @ a_base
    cp_ = c - (c @ a_w) * a_w
    tp_ = t - (t @ a_w) * a_w
    phi = math.atan2(float(a_w @ np.cross(cp_, tp_)), float(cp_ @ tp_))
    if abs(phi) < 1e-6:
        return None
    return alpha, phi, a_base


def _span(alpha):
    s = math.sin(alpha)
    return math.inf if abs(s) < 1e-12 else abs(math.cos(alpha) / s)


def _pivot(s1, sg, alpha, w_lo=0.0, w_hi=1.0):
    """Pivot on a strip edge such that the cut stays on the distal side of
    s = s1 across the whole (current) flap width (no tear at the joint)."""
    ca, sa = math.cos(alpha), math.sin(alpha)
    if abs(ca) < 1e-9 or abs(sa) < 1e-12:
        return np.array([s1, w_lo, 0.0])
    w0 = w_lo if sg * (ca / sa) > 0 else w_hi
    return np.array([s1, w0, 0.0])


def narrowings_for(con, base, sigma, requests):
    """Turn narrowing requests [(stick, template)] into Narrowing objects.
    The adapter starts NARROW_GAP after the stick's joint (clear of the
    joint's own simple fold, whose cut spans <= 1 unit) and needs the stick
    to be long enough to hold it."""
    from .narrow import Narrowing, TEMPLATES
    out = []
    width = {}
    for name, tpl in requests:
        c = next((c for c in con.chains if name in c.sticks), None)
        if c is None or not c.leaf:
            continue
        k = c.sticks.index(name)
        off0 = c.offsets[k]
        off1 = c.offsets[k + 1] if k + 1 < len(c.sticks) else c.length
        sg = sigma[c.id]
        w_lo, w_hi = width.get(c.id, (0.0, 1.0))
        shift = sum(n.H for n in out if n.chain == c.id)
        for rep in range(TEMPLATES.get(tpl, 1)):
            H = w_hi - w_lo
            start = off0 + NARROW_GAP + rep * (H + 0.25)
            if start + H + 0.5 > off1 - shift:
                break
            s0 = base.strip[c.u] + sg * (start - shift)
            n = Narrowing(name, c.id, s0, sg, w_lo, H)
            out.append(n)
            w_lo, w_hi = n.new_width
            shift += H
        width[c.id] = (w_lo, w_hi)
    return out


NARROW_GAP = 1.75
FOLD_OFFSET = 0.4
FOLD_MARGIN = 0.1


def plan_folds(sf, con, base: Base, sigma, narrowings=(), extra=()):
    """extra: additional simple folds [(stick, fraction along it, angle_deg)]
    -- a bend of the stick's distal part about the in-plane axis across the
    strip (the RL agent's 'additional simple folds', §3.6)."""
    extra_by = defaultdict(list)
    for st_, f_, a_ in extra:
        extra_by[st_].append((float(f_), float(a_)))
    dirs = chain_dirs(sf, con)
    info, children = stick_layout(sf, con, sigma, base.strip)
    # narrowing shortens the flap beyond its adapter and halves its width
    for d in info.values():
        d["w"] = (0.0, 1.0)
    for n in narrowings:
        c = con.chains[n.chain]
        u0 = n.sigma * (n.s0 - base.strip[c.u])        # chain elevation of adapter
        for name in c.sticks:
            d = info[name]
            if d["off0"] > u0 + 1e-9:
                d["s_joint"] -= n.sigma * n.H
                d["w"] = n.new_width
    rc = root_chain(con)
    rstick = con.chains[rc].sticks[0]
    Q0 = root_frame(sf, dirs[rstick], sigma[rc])
    G = {None: _h(Q0)}
    ops = []
    order = []
    q = [n for n in children[None]]
    while q:
        n = q.pop(0)
        order.append(n)
        q += children.get(n, [])
    def fold_stick(n):
        d = info[n]
        par = d["parent"]
        Gp = G[par]
        Qp = Gp[:3, :3]
        sg = d["sigma"]
        t = dirs[n]
        G[n] = Gp
        if n == rstick:
            return
        sj = d["s_joint"]
        w_lo, w_hi = d["w"]
        W = w_hi - w_lo
        L = d["off1"] - d["off0"]
        sub = _subtree(children, n)
        distal = np.array([sj + sg * 1e3, (w_lo + w_hi) / 2, 0.0])
        one = _single(Qp, sg, t)
        if one is None:
            return
        alpha, phi, a_base = one
        # Folds sit a little past the joint (FOLD_OFFSET, off the integer and
        # half-integer contours, which run through grid vertices and ridge
        # corners) and must finish FOLD_MARGIN before the next joint, so no two
        # sticks' cut lines ever meet at one vertex.
        avail = L - FOLD_MARGIN
        need1 = _span(alpha) * W
        if need1 <= min(1.0, avail) + 1e-9:
            dlt = min(FOLD_OFFSET, max(0.0, (avail - need1) / 2))
            piv = _pivot(sj + sg * dlt, sg, alpha, w_lo, w_hi)
            K = _about_line(piv, a_base, phi)
            G[n] = Gp @ K
            ops.append(FoldOp(n, par, piv, a_base, phi, sg, sj, sub, distal))
            return
        # crimp: fold back flat across the strip, then one oblique fold on
        # the returned layers (both lines span <= 1 unit)
        G1 = Gp @ _about_line(np.array([sj, w_lo, 0.0]), Y, math.pi)
        two = _single(G1[:3, :3], sg, t)
        need2 = (_span(two[0]) * W) if two is not None else 0.0
        g2 = max(0.05, min(0.25, avail - need2))
        dlt = min(FOLD_OFFSET, max(0.0, (avail - need2 - g2) / 2))
        piv1 = np.array([sj + sg * dlt, w_lo, 0.0])
        K1 = _about_line(piv1, Y, math.pi)
        G1 = Gp @ K1
        ops.append(FoldOp(n, par, piv1, Y.copy(), math.pi, sg, sj, sub, distal))
        if two is None:
            G[n] = G1
            return
        a2, phi2, ab2 = two
        piv2 = _pivot(sj + sg * (dlt + g2), sg, a2, w_lo, w_hi)
        K2 = _about_line(piv2, ab2, phi2)
        G[n] = G1 @ K2
        ops.append(FoldOp(n, par, piv2, ab2, phi2, sg, sj + sg * (dlt + g2), sub, distal))

    for n in order:
        fold_stick(n)
        d = info[n]
        par = d["parent"]
        sg = d["sigma"]
        sj = d["s_joint"]
        w_lo, w_hi = d["w"]
        L = d["off1"] - d["off0"]
        sub = _subtree(children, n)
        distal = np.array([sj + sg * 1e3, (w_lo + w_hi) / 2, 0.0])
        for f_, a_ in sorted(extra_by.get(n, ())):
            if abs(a_) < 1e-6:
                continue
            f_ = min(max(f_, 0.0), 1.0)
            u = max(1.6, min(L - FOLD_MARGIN - 0.2, f_ * L))
            if u >= L - FOLD_MARGIN:
                continue
            pv = np.array([sj + sg * (u + 0.03), w_lo, 0.0])
            Kx = _about_line(pv, Y, math.radians(a_))
            G[n] = G[n] @ Kx
            ops.append(FoldOp(n, par, pv, Y.copy(), math.radians(a_), sg, sj, sub, distal))
    return ops, G, info, children, Q0


# ------------------------------------------------------------- splitting
def _split_poly(poly, n, c):
    """Split convex polygon (list of 2-D points) by the line n.x = c."""
    a, b = [], []
    m = len(poly)
    vals = [float(n @ p) - c for p in poly]
    for i in range(m):
        p, q = poly[i], poly[(i + 1) % m]
        vp, vq = vals[i], vals[(i + 1) % m]
        if vp >= -1e-12:
            a.append(p)
        if vp <= 1e-12:
            b.append(p)
        if (vp > 1e-12 and vq < -1e-12) or (vp < -1e-12 and vq > 1e-12):
            t = vp / (vp - vq)
            x = p + t * (q - p)
            a.append(x)
            b.append(x)
    def ok(P):
        if len(P) < 3:
            return False
        ar = 0.0
        for i in range(len(P)):
            ar += P[i][0] * P[(i + 1) % len(P)][1] - P[(i + 1) % len(P)][0] * P[i][1]
        return abs(ar) > 1e-10
    out = [P for P in (a, b) if ok(P)]
    return out if len(out) == 2 else [poly]


def flat_ops(ops):
    """Indices of 180-degree folds: their sense (+-pi) does not change the
    geometry, only which way the layers travel (and so the M/V labels)."""
    return [i for i, o in enumerate(ops) if abs(abs(o.phi) - math.pi) < 1e-9]


def _split_all(items, n_s, c_s, only=None):
    """Split every piece by the pre-image (through its own affine map) of the
    strip line n_s . (s, w) = c_s.  items: list of dicts with poly/A/b."""
    out = []
    for it in items:
        if only is not None and not only(it):
            out.append(it)
            continue
        n_p = it["A"].T @ n_s
        c_p = c_s - float(n_s @ it["b"])
        poly = it["poly"]
        vals = [float(n_p @ q) - c_p for q in poly]
        if min(vals) < -1e-12 and max(vals) > 1e-12:
            for part in _split_poly(poly, n_p, c_p):
                d = dict(it)
                d["poly"] = part
                out.append(d)
        else:
            out.append(it)
    return out


def shape(sf, con, base: Base, solved, sigma, sense=None, plan=None,
          narrowings=()) -> Shaped:
    ops, G, info, children, Q0 = plan if plan is not None else \
        plan_folds(sf, con, base, sigma, narrowings)
    if sense:
        for i, sg in sense.items():
            ops[i].phi = sg * abs(ops[i].phi)
    chain_sticks = {c.id: c for c in con.chains}

    def stick_of(t):
        c = chain_sticks[t.chain]
        d = sum(t.d) / 3.0
        for k in range(len(c.sticks) - 1, -1, -1):
            if d >= c.offsets[k] - 1e-9:
                return c.sticks[k]
        return c.sticks[0]

    path = {}
    for name in info:
        p, cur = [], name
        while cur is not None:
            p.append(cur)
            cur = info[cur]["parent"]
        path[name] = p[::-1]
    opmap = defaultdict(list)
    for o in ops:
        opmap[o.stick].append(o)
    seglab = _unit_labels(base, solved)
    Kc = {id(o): _about_line(o.pivot, o.axis, o.phi) for o in ops}
    opidx = {id(o): i for i, o in enumerate(ops)}

    # pieces start as the base triangles with their strip maps
    items = [{"poly": [np.array(p, float) for p in t.pts], "A": t.A.copy(), "b": t.b.copy(),
              "ti": ti, "chain": t.chain, "stick": stick_of(t), "hist": ()}
             for ti, t in enumerate(base.tris)]
    # narrowing (clip pattern): split the flap's faces by the template's
    # pre-images, then compose each face's map with the template isometry
    for k_nr, nr in enumerate(narrowings):
        for n_s, c_s in nr.lines():
            items = _split_all(items, n_s, c_s)
        for it in items:
            if it["chain"] != nr.chain:
                continue
            cen = np.mean(it["poly"], axis=0)
            sw = it["A"] @ cen + it["b"]
            M, tr = nr.map_at(*sw)
            it["hist"] = it["hist"] + ((k_nr, it["A"], it["b"]),)
            it["A"], it["b"] = M @ it["A"], M @ it["b"] + tr
    # simple folds: split by every cut line's pre-image
    for o in ops:
        ns = np.array([-o.axis[1], o.axis[0]])
        items = _split_all(items, ns, float(ns @ o.pivot[:2]))

    pieces = []      # (paper poly, world 4x4, base tri index, applied ops, B)
    for it in items:
        A, b = it["A"], it["b"]
        det = float(np.linalg.det(A))
        B = _h(np.array([[A[0, 0], A[0, 1], 0], [A[1, 0], A[1, 1], 0],
                         [0, 0, 1.0 if det > 0 else -1.0]]), np.array([b[0], b[1], 0.0]))
        cen = np.mean(it["poly"], axis=0)
        sw = A @ cen + b
        Gw = G[None]
        applied = []
        stop = False
        for name in path[it["stick"]]:
            for o in opmap.get(name, ()):
                ns = np.array([-o.axis[1], o.axis[0]])
                side = float(ns @ (sw - o.pivot[:2]))
                dside = float(ns @ (o.distal[:2] - o.pivot[:2]))
                if side * dside > 0:
                    Gw = Gw @ Kc[id(o)]
                    applied.append(opidx[id(o)])
                else:
                    stop = True
                    break
            if stop:
                break
        pieces.append((np.array(it["poly"]), Gw @ B, it["ti"], tuple(applied), B, it["hist"]))

    sh = Shaped(None, ops, pieces, Q0, stats={"pieces": len(pieces), "ops": len(ops),
                                               "narrowings": len(narrowings)})
    sh.G0 = G[None]
    sh.seglab = seglab
    sh.base = base
    sh.narrowings = list(narrowings)
    relabel(sh)
    return sh


def relabel(sh: "Shaped", sense=None):
    """(Re)build the shaping CP's crease edges.  `sense` maps op index ->
    +-1 for 180-degree folds: the geometry is identical either way, only the
    M/V of the creases they make (and of base creases they cross) changes."""
    if sense:
        for i, sg in sense.items():
            sh.ops[i].phi = sg * abs(sh.ops[i].phi)
    Ke = [_about_line(o.pivot, o.axis, o.phi * (1 - 1e-6)) for o in sh.ops]
    G0 = sh.G0
    cache = {}

    def ge(applied):
        if applied not in cache:
            M = G0
            for i in applied:
                M = M @ Ke[i]
            cache[applied] = M
        return cache[applied]
    pieces = [(poly, W, ti, ge(app), B, hist) for poly, W, ti, app, B, hist in sh.pieces]
    sh.cp = CP(sh.base.N, _crease_edges(sh.base, pieces, sh.seglab,
                                        getattr(sh, "narrowings", [])))
    return sh


def _unit_labels(base, solved):
    from .solve import _segments, _on_seg
    segs = _segments(base)
    out = {}
    for k in base.creases:
        p, q = k
        m = ((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
        for i, ((a, b), _) in enumerate(segs):
            if _on_seg(m, a, b, 1e-9) and _on_seg(p, a, b, 1e-9) and _on_seg(q, a, b, 1e-9):
                out[k] = solved.labels[i]
                break
    return out


def _snap(p):
    return (round(float(p[0]), 7) + 0.0, round(float(p[1]), 7) + 0.0)


def _rel_angle(W1, W2, a, b):
    """Signed fold angle (deg) of the crease a->b, as COrigami's folder reads
    it: W2 = T R(axis = W1 b - W1 a, angle) T^-1 W1."""
    pa = W1 @ np.array([a[0], a[1], 0, 1.0])
    pb = W1 @ np.array([b[0], b[1], 0, 1.0])
    u = (pb - pa)[:3]
    u /= np.linalg.norm(u)
    R = W2[:3, :3] @ W1[:3, :3].T
    cosv = max(-1.0, min(1.0, (np.trace(R) - 1) / 2))
    sinv = 0.5 * float(u @ np.array([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]]))
    return math.degrees(math.atan2(sinv, cosv))


def _crease_edges(base, pieces, seglab, narrowings=()):
    N = base.N
    emap = defaultdict(list)
    for pi, (poly, W, ti, _g, _b, _h_) in enumerate(pieces):
        P = poly
        # COrigami's face order: negative shoelace area in (x, y-down)
        ar = sum(P[i][0] * P[(i + 1) % len(P)][1] - P[(i + 1) % len(P)][0] * P[i][1]
                 for i in range(len(P)))
        if ar > 0:
            P = P[::-1]
        for i in range(len(P)):
            a, b = _snap(P[i]), _snap(P[(i + 1) % len(P)])
            if a == b:
                continue
            emap[(min(a, b), max(a, b))].append((pi, a, b))
    edges = []
    for k, lst in emap.items():
        a, b = k
        onb = (abs(a[0]) < 1e-9 and abs(b[0]) < 1e-9) or (abs(a[1]) < 1e-9 and abs(b[1]) < 1e-9) or \
              (abs(a[0] - N) < 1e-9 and abs(b[0] - N) < 1e-9) or (abs(a[1] - N) < 1e-9 and abs(b[1] - N) < 1e-9)
        if len(lst) == 1:
            if onb:
                edges.append(Edge(a, b, "B"))
            continue
        (p1, a1, b1), (p2, _, _) = lst[0], lst[1]
        W1, W2 = pieces[p1][1], pieces[p2][1]
        ang = _rel_angle(W1, W2, a1, b1)
        if abs(ang) < 1e-5:
            continue
        if abs(abs(ang) - 180) < 1e-5:
            # a 180-degree crease: its sense is the UNWRAPPED sum of the base
            # fold (solved label, or 0 where the base was flat) and the shaping
            # rotation between the two pieces' groups, seen through piece 1's
            # own layer orientation.
            blab = _label_for(a, b, seglab)
            base_ang = 0.0 if blab is None else (180.0 if blab == "V" else -180.0)
            G1, B1 = pieces[p1][3], pieces[p1][4]
            G2 = pieces[p2][3]
            delta = _rel_angle(G1 @ B1, G2 @ B1, a1, b1)
            if abs(delta) > 1.0:
                lab = "V" if delta > 0 else "M"
            elif blab is None and narrowings:
                # a narrowing-template crease: the template's own M/V,
                # swapped on layers that lie face down (clip pattern, §3.5)
                lab = None
                mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                for k_nr, A0, b0 in pieces[p1][5]:
                    sw = A0 @ np.array([mx, my]) + b0
                    tl = narrowings[k_nr].label_at(*sw)
                    if tl is not None:
                        flip = np.linalg.det(A0) < 0
                        lab = tl if not flip else ("V" if tl == "M" else "M")
                        break
                if lab is None:
                    lab = "V" if base_ang > 0 else "M"
            else:
                lab = "V" if base_ang > 0 else "M"
            edges.append(Edge(a, b, lab, angle=180.0 if lab == "V" else -180.0,
                              role="base" if abs(delta) < 1e-6 else "shaping"))
            continue
        lab = "V" if ang > 0 else "M"
        edges.append(Edge(a, b, lab, angle=ang, role="shaping"))
    return _merge_float(edges, N)


def _label_for(a, b, seglab):
    """Label of a base unit crease containing segment a-b (pieces may be
    sub-segments of a unit crease)."""
    m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    i, j = math.floor(m[0]), math.floor(m[1])
    for k in _cands(i, j):
        if k in seglab:
            p, q = k
            if _between(m, p, q):
                return seglab[k]
    return None


def _cands(i, j):
    c = (i + 0.5, j + 0.5)
    pts = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
    out = []
    for k in range(4):
        p, q = pts[k], pts[(k + 1) % 4]
        out.append((min(p, q), max(p, q)))
        out.append((min(p, c), max(p, c)))
    return out


def _between(m, p, q, eps=1e-6):
    cr = (q[0] - p[0]) * (m[1] - p[1]) - (q[1] - p[1]) * (m[0] - p[0])
    if abs(cr) > eps:
        return False
    dot = (m[0] - p[0]) * (q[0] - p[0]) + (m[1] - p[1]) * (q[1] - p[1])
    return 0 <= dot <= (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2


def _merge_float(edges, N):
    """Merge collinear consecutive edges with identical kind/angle through
    vertices touched by no other edge."""
    deg = defaultdict(int)
    for e in edges:
        deg[e.a] += 1
        deg[e.b] += 1
    groups = defaultdict(list)
    for e in edges:
        dx, dy = e.b[0] - e.a[0], e.b[1] - e.a[1]
        L = math.hypot(dx, dy)
        ux, uy = dx / L, dy / L
        if ux < -1e-9 or (abs(ux) < 1e-9 and uy < 0):
            ux, uy = -ux, -uy
        off = round(e.a[0] * uy - e.a[1] * ux, 6)
        groups[(round(ux, 6), round(uy, 6), off, e.kind, round(e.angle, 5))].append(e)
    out = []
    for (ux, uy, off, kind, ang), lst in groups.items():
        def t(p):
            return p[0] * ux + p[1] * uy
        segs = sorted(((min(t(e.a), t(e.b)), max(t(e.a), t(e.b)),
                        e.a if t(e.a) <= t(e.b) else e.b,
                        e.b if t(e.a) <= t(e.b) else e.a, e) for e in lst), key=lambda r: r[0])
        cur = None
        for s0, s1, pa, pb, e in segs:
            if cur and abs(s0 - cur[1]) < 1e-7 and deg[pa] == 2:
                cur = (cur[0], s1, cur[2], pb, cur[4])
            else:
                if cur:
                    out.append(Edge(cur[2], cur[3], kind, angle=cur[4].angle, role=cur[4].role))
                cur = (s0, s1, pa, pb, e)
        if cur:
            out.append(Edge(cur[2], cur[3], kind, angle=cur[4].angle, role=cur[4].role))
    return _dissolve_straight(out)


def _dissolve_straight(edges):
    """Remove degree-2 vertices where two edges of the same kind and angle
    continue straight on (to within snapping noise).  Splits from a line that
    only touched OTHER layers leave such points; they are not vertices of the
    crease pattern, and on very short pieces the 1e-7 snap would otherwise
    tilt them past the Kawasaki tolerance."""
    while True:
        inc = defaultdict(list)
        for i, e in enumerate(edges):
            inc[e.a].append(i)
            inc[e.b].append(i)
        dead, new = set(), []
        for v, lst in inc.items():
            if len(lst) != 2 or lst[0] in dead or lst[1] in dead:
                continue
            e1, e2 = edges[lst[0]], edges[lst[1]]
            if e1.kind != e2.kind or abs(e1.angle - e2.angle) > 1e-6 or e1.kind == "B":
                continue
            p = e1.b if e1.a == v else e1.a
            q = e2.b if e2.a == v else e2.a
            d1 = np.array([p[0] - v[0], p[1] - v[1]])
            d2 = np.array([q[0] - v[0], q[1] - v[1]])
            c = float(d1 @ d2) / (np.linalg.norm(d1) * np.linalg.norm(d2))
            if c > -1 + 1e-8:
                continue
            dead |= {lst[0], lst[1]}
            new.append(Edge(p, q, e1.kind, angle=e1.angle, role=e1.role))
        if not dead:
            return edges
        edges = [e for i, e in enumerate(edges) if i not in dead] + new


def world_at(shaped: "Shaped", p) -> np.ndarray:
    """World transform (4x4) of the shaped piece containing paper point p."""
    x, y = float(p[0]), float(p[1])
    for poly, W, *_ in shaped.pieces:
        n = len(poly)
        inside = True
        sgn = 0
        for i in range(n):
            a, b = poly[i], poly[(i + 1) % n]
            cr = (b[0] - a[0]) * (y - a[1]) - (b[1] - a[1]) * (x - a[0])
            if abs(cr) < 1e-12:
                continue
            s = 1 if cr > 0 else -1
            if sgn == 0:
                sgn = s
            elif s != sgn:
                inside = False
                break
        if inside:
            return W
    raise ValueError(f"no shaped piece contains {p}")
