"""COrigami §3.3 / App. D, F: mountain-valley assignment of the base.

The crease SET is fixed by the folded state (`base.build`): pleats, ridges and
the hinges that actually fold.  What remains is the M/V assignment, done as
in the paper:

1. F.2 interleaving -- pleat segments are grouped into connected paths
   (a path turns at a ridge, giving the concentric rings of a box-pleated
   flap); paths are visited breadth-first from the one nearest the origin
   and paths one grid unit apart alternate M/V;
2. F.3 ridges -- anchored at Y-shape vertices (two perpendicular ridges
   meeting one pleat tip share its fold) and at the border, then propagated:
   X-shape (four ridges) same, perpendicular ridges at an intersection same,
   parallel adjacent ridges opposite;
3. combinatorial hinge assignment -- hinge components (one per tree node)
   sorted by vertex count, each tried as interleaved (M-V-M-V) or symmetric
   (M-V-V-M) along its length (and its global flip), keeping the candidate
   with the best global score = number of locally flat-foldable vertices;
   then greedy single-crease flips while the score strictly improves
   (the paper's pleat reassignment).

Local flat-foldability is App. D's crimping test (Algorithm 1, ported
below).  Global flat-foldability (the facewise CSP of Akitaya et al. 2024 that
App. D reimplements) is decided with this repo's SAT layer-order stage
(`pleatwright.certify.sat_order`), phase-seeded with the heuristic labelling so the
certified witness stays as close to it as the solver finds; we report how
many creases the certificate had to relabel.
"""
from __future__ import annotations

import math
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field

import numpy as np

from .base import Base, merged_segments, border_edges
from .cp import CP, Edge


# ------------------------------------------------------------- App. D, Alg. 1
def crimp_flat_foldable(sectors, creases) -> bool:
    """Algorithm 1.  sectors[i] is the angle between crease i and crease
    i+1 (cyclic); creases[i] in {'M','V'}.  Sector i is bounded by
    left = creases[i], right = creases[i+1]."""
    n = len(sectors)
    if n < 2:
        return False
    th = list(sectors)
    left = [creases[i] for i in range(n)]
    right = [creases[(i + 1) % n] for i in range(n)]
    prev = [(i - 1) % n for i in range(n)]
    nxt = [(i + 1) % n for i in range(n)]
    alive = [True] * n
    size = n
    eps = 1e-3   # degrees; coordinates are snapped at 1e-7 grid units

    def is_min(s):
        if left[s] == right[s]:
            return False
        return th[s] <= th[prev[s]] + eps and th[s] <= th[nxt[s]] + eps

    Q = deque(s for s in range(n) if is_min(s))
    while Q and size > 2:
        s = Q.popleft()
        if not alive[s] or not is_min(s):
            continue
        Ls, Rs = prev[s], nxt[s]
        th[Ls] = th[Ls] - th[s] + th[Rs]
        right[Ls] = right[Rs]
        # remove s and R
        alive[s] = alive[Rs] = False
        nn = nxt[Rs]
        nxt[Ls] = nn
        prev[nn] = Ls
        size -= 2
        for x in (prev[Ls], Ls, nxt[Ls]):
            if alive[x] and is_min(x):
                Q.append(x)
    if size == 2:
        live = [i for i in range(n) if alive[i]]
        labs = {left[i] for i in live} | {right[i] for i in live}
        return len(labs) == 1 and abs(th[live[0]] - th[live[1]]) < eps
    return False


@dataclass
class Solved:
    cp: CP                      # solving CP (M/V/B), grid units
    labels: dict                # crease index -> 'M'/'V' (final, certified)
    heuristic: dict             # crease index -> label from COrigami's steps
    ff_local: tuple             # (flat-foldable vertices, all vertices)
    global_verdict: str
    relabelled: int
    stats: dict = field(default_factory=dict)


def _segments(base: Base):
    items = [(k, v["kind"]) for k, v in base.creases.items()]
    segs = merged_segments(base.N, items)
    return segs


def _incidence(segs, N):
    inc = defaultdict(list)
    for i, ((p, q), lab) in enumerate(segs):
        inc[p].append((i, q))
        inc[q].append((i, p))
    return inc


def _interior(p, N):
    return 0 < p[0] < N and 0 < p[1] < N


def vertex_ok(p, inc_p, labels) -> bool:
    rays = []
    for i, q in inc_p:
        a = math.degrees(math.atan2(q[1] - p[1], q[0] - p[0])) % 360.0
        rays.append((a, labels[i]))
    rays.sort()
    if len(rays) < 2:
        return False
    sectors = [((rays[(k + 1) % len(rays)][0] - rays[k][0]) % 360.0) or 360.0
               for k in range(len(rays))]
    return crimp_flat_foldable(sectors, [r[1] for r in rays])


def local_count(segs, labels, N):
    inc = _incidence(segs, N)
    good = total = 0
    bad = []
    for p, lst in inc.items():
        if not _interior(p, N):
            continue
        total += 1
        if vertex_ok(p, lst, labels):
            good += 1
        else:
            bad.append(p)
    return good, total, bad


# ------------------------------------------------------------- heuristic M/V
def heuristic_labels(segs, N):
    kinds = {i: lab for i, (_, lab) in enumerate(segs)}
    inc = _incidence(segs, N)
    labels = {}

    # F.2: pleat paths (connected through vertices where exactly two pleat
    # segments meet), BFS from the path nearest the origin, alternating
    # between paths one unit apart.
    pleats = [i for i, k in kinds.items() if k == "P"]
    par = {i: i for i in pleats}

    def find(x):
        while par[x] != x:
            par[x] = par[par[x]]
            x = par[x]
        return x
    for p, lst in inc.items():
        ps = [i for i, _ in lst if kinds[i] == "P"]
        if len(ps) == 2:
            a, b = find(ps[0]), find(ps[1])
            if a != b:
                par[a] = b
    paths = defaultdict(list)
    for i in pleats:
        paths[find(i)].append(i)

    def seg_dist(i, j):
        (p, q), _ = segs[i]
        (r, s), _ = segs[j]
        d1 = (q[0] - p[0], q[1] - p[1])
        d2 = (s[0] - r[0], s[1] - r[1])
        if d1[0] * d2[1] - d1[1] * d2[0] != 0:
            return None
        L = math.hypot(*d1)
        nx, ny = -d1[1] / L, d1[0] / L
        off = abs((r[0] - p[0]) * nx + (r[1] - p[1]) * ny)
        ux, uy = d1[0] / L, d1[1] / L
        a0, a1 = 0.0, L
        b0 = (r[0] - p[0]) * ux + (r[1] - p[1]) * uy
        b1 = (s[0] - p[0]) * ux + (s[1] - p[1]) * uy
        if min(a1, max(b0, b1)) - max(a0, min(b0, b1)) <= 1e-9:
            return None
        return off
    # adjacency between paths: some pair of parallel, overlapping segments at
    # distance exactly 1 with no other pleat strictly between (grid ensures).
    by_line = defaultdict(list)
    for i in pleats:
        (p, q), _ = segs[i]
        if p[0] == q[0]:
            by_line[("v", p[0])].append(i)
        else:
            by_line[("h", p[1])].append(i)
    adj = defaultdict(set)
    for (o, c), lst in by_line.items():
        for j in by_line.get((o, c + 1), []):
            for i in lst:
                if seg_dist(i, j) is not None:
                    a, b = find(i), find(j)
                    if a != b:
                        adj[a].add(b)
                        adj[b].add(a)
                    break
    roots = sorted(paths, key=lambda r: min(min(math.hypot(*segs[i][0][0]), math.hypot(*segs[i][0][1]))
                                            for i in paths[r]))
    plab = {}
    for r in roots:
        if r in plab:
            continue
        plab[r] = "M"
        q = deque([r])
        while q:
            x = q.popleft()
            for y in adj[x]:
                if y not in plab:
                    plab[y] = "V" if plab[x] == "M" else "M"
                    q.append(y)
    for r, lst in paths.items():
        for i in lst:
            labels[i] = plab[r]

    # F.3: ridges.  Anchors: Y-shape vertices (pleat tip + two perpendicular
    # ridges) take the pleat's label; border ridges default to M.
    ridges = [i for i, k in kinds.items() if k == "R"]
    rlab = {}
    for p, lst in inc.items():
        rs = [(i, q) for i, q in lst if kinds[i] == "R"]
        ps = [(i, q) for i, q in lst if kinds[i] == "P"]
        if len(rs) == 2 and len(ps) == 1 and len(lst) == 3:
            for i, _ in rs:
                rlab.setdefault(i, labels[ps[0][0]])
    for i in ridges:
        (p, q), _ = segs[i]
        if not (_interior(p, N) and _interior(q, N)) and i not in rlab:
            rlab[i] = "M"
    # propagate along ridge network
    changed = True
    while changed:
        changed = False
        for p, lst in inc.items():
            rs = [(i, q) for i, q in lst if kinds[i] == "R"]
            if len(rs) < 2:
                continue
            known = [(i, q) for i, q in rs if i in rlab]
            if not known:
                continue
            for i, q in rs:
                if i in rlab:
                    continue
                # perpendicular or X: same; collinear continuation: same
                ref, rq = known[0]
                rlab[i] = rlab[ref]
                changed = True
    for i in ridges:
        labels[i] = rlab.get(i, "M")

    # Hinges: components (connected hinge segments) sorted by vertex count;
    # each tried interleaved / symmetric x flip, keep the best local score.
    hinges = [i for i, k in kinds.items() if k == "H"]
    hpar = {i: i for i in hinges}

    def hfind(x):
        while hpar[x] != x:
            hpar[x] = hpar[hpar[x]]
            x = hpar[x]
        return x
    for p, lst in inc.items():
        hs = [i for i, _ in lst if kinds[i] == "H"]
        for a in hs[1:]:
            ra, rb = hfind(hs[0]), hfind(a)
            if ra != rb:
                hpar[ra] = rb
    comps = defaultdict(list)
    for i in hinges:
        comps[hfind(i)].append(i)
    for i in hinges:
        labels[i] = "M"
    order = sorted(comps.values(), key=lambda c: -len(c))
    for comp in order:
        verts = {pt for i in comp for pt in segs[i][0] if _interior(pt, N)}
        # parametrise each segment along its line by its midpoint coordinate
        def tpos(i):
            (p, q), _ = segs[i]
            return (p[0] + q[0]) / 2 + (p[1] + q[1]) / 2
        ts = sorted(comp, key=tpos)
        mid = (len(ts) - 1) / 2
        cands = []
        for flip in ("M", "V"):
            other = "V" if flip == "M" else "M"
            inter = {i: (flip if k % 2 == 0 else other) for k, i in enumerate(ts)}
            sym = {i: (flip if (abs(k - mid) // 1) % 2 == 0 else other) for k, i in enumerate(ts)}
            cands += [inter, sym, {i: flip for i in ts}]
        best, bs = None, -1
        for c in cands:
            trial = dict(labels)
            trial.update(c)
            sc = sum(1 for p in verts if vertex_ok(p, inc[p], trial))
            if sc > bs:
                best, bs = c, sc
        labels.update(best)

    # greedy single-crease flips (pleat reassignment) while score improves
    good, total, bad = local_count(segs, labels, N)
    for _ in range(4 * len(segs)):
        if not bad:
            break
        improved = False
        for p in list(bad):
            for i, _ in inc[p]:
                labels[i] = "V" if labels[i] == "M" else "M"
                g2 = sum(1 for v in segs[i][0] if _interior(v, N) and vertex_ok(v, inc[v], labels))
                labels[i] = "V" if labels[i] == "M" else "M"
                g1 = sum(1 for v in segs[i][0] if _interior(v, N) and vertex_ok(v, inc[v], labels))
                if g2 > g1:
                    labels[i] = "V" if labels[i] == "M" else "M"
                    improved = True
                    break
        good, total, bad = local_count(segs, labels, N)
        if not improved:
            break
    return labels


# ------------------------------------------------------------- global (SAT)
def to_fold(cp: CP) -> tuple:
    V, raw = cp.fold_input()
    N = cp.N
    fold = {"file_spec": 1.1, "file_creator": "pleatwright",
            "vertices_coords": [[x / N, y / N] for x, y in V],
            "edges_vertices": [[a, b] for a, b, _, _ in raw],
            "edges_assignment": [k for _, _, k, _ in raw],
            "edges_foldAngle": [f for *_, f in raw]}
    return fold, V, raw


def certify(cp: CP, seg_of_edge, prefs: dict, *, timeout_hint: float = 120.0):
    """Global flat-foldability via SAT over layer order + labels, phase-seeded
    with `prefs` (crease index -> label).  Returns (verdict, labels|None)."""
    from pleatwright.certify import flat_fold, layer_certify, layers as L, sat_order
    from pysat.solvers import Solver

    fold, V, raw = to_fold(cp)
    ff = flat_fold.flat_fold(fold)
    g = L.constraint_graph(ff)
    if sat_order.raw_triple_bound(g.cons) > sat_order.MAX_RAW_TRIPLES:
        return "OVERSIZE", None, {}
    s = Solver(name=sat_order.SOLVER)
    try:
        try:
            st = sat_order.encode(g.cons, g.slots, s.add_clause)
        except sat_order.ClauseBudgetExceeded:
            # the encoder's exact streaming backstop: too large to decide
            return "OVERSIZE", None, {"pairs": len(g.cons.pairs)}
        phases = []
        for k, var in st.label_var.items():
            ci = seg_of_edge.get(k)
            if ci is not None and ci in prefs:
                phases.append(var if prefs[ci] == "V" else -var)
        s.set_phases(phases)
        ok = s.solve()
        model = s.get_model() if ok else None
    finally:
        s.delete()
    info = {"pairs": len(g.cons.pairs), "label_vars": len(st.label_var), "clauses": st.clauses}
    if not ok:
        return "REFUTED", None, info
    true = {l for l in model if l > 0}
    relation = {p: (v in true) for p, v in st.order_var.items()}
    vr = layer_certify.verify(g.cons, relation)
    if vr.skipped or vr.violation is not None:
        return "VERIFY_FAILED", None, info
    labels = {}
    for k, var in st.label_var.items():
        ci = seg_of_edge.get(k)
        if ci is not None:
            lab = "V" if var in true else "M"
            if labels.get(ci, lab) != lab:
                return "SPLIT_LABEL", None, info
            labels[ci] = lab
    return "CERTIFIED", labels, info


def local_sat(segs, prefs: dict, N):
    """Labels making EVERY interior vertex pass the crimp test (App. D,
    Alg. 1), as close to `prefs` as the solver finds: each vertex forbids
    the M/V combinations of its incident creases that fail the test.  Used
    when the global layer-order query is too large to decide."""
    import itertools
    from pysat.solvers import Solver
    inc = _incidence(segs, N)
    s = Solver(name="cadical153")
    try:
        for p, lst in inc.items():
            if not _interior(p, N) or len(lst) > 12:
                continue
            rays = sorted(((math.degrees(math.atan2(q[1] - p[1], q[0] - p[0])) % 360.0, i)
                           for i, q in lst))
            sec = [((rays[(k + 1) % len(rays)][0] - rays[k][0]) % 360.0) or 360.0
                   for k in range(len(rays))]
            idx = [i for _, i in rays]
            for labs in itertools.product("MV", repeat=len(idx)):
                if not crimp_flat_foldable(sec, list(labs)):
                    # forbid this combination: V -> var true
                    s.add_clause([-(i + 1) if l == "V" else (i + 1) for i, l in zip(idx, labs)])
        s.set_phases([(i + 1) if prefs.get(i) == "V" else -(i + 1) for i in range(len(segs))])
        if not s.solve():
            return None
        model = set(x for x in s.get_model() if x > 0)
    finally:
        s.delete()
    return {i: ("V" if (i + 1) in model else "M") for i in range(len(segs))}


def solve(base: Base, *, certify_global: bool = True) -> Solved:
    N = base.N
    t0 = time.perf_counter()
    segs = _segments(base)
    heur = heuristic_labels(segs, N)
    t_heur = time.perf_counter() - t0
    hgood, htotal, _ = local_count(segs, heur, N)

    def make_cp(labels):
        edges = border_edges(N, [p for (a, b), _ in segs for p in (a, b)])
        for i, ((p, q), kind) in enumerate(segs):
            lab = labels[i]
            e = Edge(p, q, lab, angle=180.0 if lab == "V" else -180.0, role=kind)
            if kind == "P":
                e.attrs["elevation"] = "1" if lab == "M" else "0"
            edges.append(e)
        return CP(N, edges)

    cp = make_cp(heur)
    verdict, labels, info = "SKIPPED", None, {}
    t1 = time.perf_counter()
    if certify_global:
        # map fold edge keys back to crease indices
        fold, V, raw = to_fold(cp)
        vkey = {i: tuple(v) for i, v in enumerate(V)}
        seg_line = {}
        for i, ((p, q), _) in enumerate(segs):
            seg_line[i] = (p, q)
        seg_of_edge = {}
        for a, b, kind, _ in raw:
            if kind not in ("M", "V"):
                continue
            pa, pb = vkey[a], vkey[b]
            for i, (p, q) in seg_line.items():
                if _on_seg(pa, p, q) and _on_seg(pb, p, q):
                    seg_of_edge[(min(a, b), max(a, b))] = i
                    break
        verdict, labels, info = certify(cp, seg_of_edge, heur)
    t_glob = time.perf_counter() - t1
    final = labels if labels is not None else heur
    if labels is None:
        g0, t0_, _ = local_count(segs, heur, N)
        if g0 < t0_:
            loc = local_sat(segs, heur, N)
            if loc is not None:
                final = loc
                verdict = verdict + "+LOCAL_SAT"
    relab = sum(1 for i in final if final[i] != heur.get(i))
    cp = make_cp(final)
    good, total, _ = local_count(segs, final, N)
    # COrigami counts every CP vertex (border vertices pass trivially)
    allv = {p for (a, b), _ in segs for p in (a, b)} | {(x, y) for x in (0, N) for y in (0, N)}
    border_v = sum(1 for p in allv if not _interior(p, N))
    stats = dict(heuristic_local=(hgood, htotal), secs_heuristic=round(t_heur, 2),
                 secs_global=round(t_glob, 2), **info)
    return Solved(cp, final, heur, (good + border_v, total + border_v), verdict, relab, stats)


def _on_seg(p, a, b, eps=1e-7):
    cr = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
    if abs(cr) > eps:
        return False
    dot = (p[0] - a[0]) * (b[0] - a[0]) + (p[1] - a[1]) * (b[1] - a[1])
    L2 = (b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2
    return -eps <= dot <= L2 + eps
