"""COrigami §3.7 / App. H: the purely geometric folding simulator.

Port of the COrigami Visualiser's ``findFaces`` / ``cleanTopology`` /
``solveFold`` / ``getSkeletonVertices`` / ``computeAxialStrain``:

1. parse the crease pattern into vertices, edges and faces (PSLG face walk,
   CCW faces only, dangling elements dropped);
2. breadth-first traversal of the face-adjacency graph from the face nearest
   the centroid; each newly reached face gets the global 4x4 transform
   ``T(p1) R(axis, angle) T(-p1) M_parent`` where the axis is the shared edge
   in the parent's folded frame and ``angle`` its signed fold angle;
3. a vertex's 3-D position is the average of its images over every face
   containing it;
4. mean axial strain = mean over vertices of the mean |L3d - L2d| / L2d of
   their incident edges.
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

import numpy as np


@dataclass
class Model:
    vertices: np.ndarray        # (n, 2) flat coordinates
    faces: list                 # list of vertex-index lists (CCW in y-down svg sense reversed)
    edges: list                 # list of (u, v)
    assignment: list            # per edge
    fold_angle: list            # per edge, degrees


def find_faces(V: np.ndarray, edges) -> list:
    n = len(V)
    adj = [[] for _ in range(n)]
    for u, v in edges:
        adj[u].append(v)
        adj[v].append(u)
    for v in range(n):
        if adj[v]:
            x0, y0 = V[v]
            adj[v].sort(key=lambda a: math.atan2(V[a][1] - y0, V[a][0] - x0))
    nxt = {}
    for v in range(n):
        nb = adj[v]
        k = len(nb)
        for i, u in enumerate(nb):
            nxt[(u, v)] = nb[(i - 1) % k]
    faces, visited = [], set()
    for key in list(nxt.keys()):
        if key in visited:
            continue
        u, v = key
        face = [u, v]
        visited.add((u, v))
        start = u
        w = nxt.get((u, v))
        broken, count = False, 0
        while w != start:
            if w is None:
                broken = True
                break
            face.append(w)
            visited.add((v, w))
            u, v = v, w
            w = nxt.get((u, v))
            count += 1
            if count > 100000:
                broken = True
                break
        if broken or len(face) < 3:
            continue
        visited.add((face[-1], face[0]))
        a = 0.0
        for i in range(len(face)):
            p1, p2 = V[face[i]], V[face[(i + 1) % len(face)]]
            a += p1[0] * p2[1] - p2[0] * p1[1]
        if a > 1e-12:
            faces.append(face[::-1])
    return faces


def build_model(V, raw_edges) -> Model:
    """raw_edges: iterable of (u, v, assignment, fold_angle_deg)."""
    V = np.asarray(V, float)
    emap = {}
    for u, v, asg, fa in raw_edges:
        emap[(min(u, v), max(u, v))] = (asg, fa)
    faces = find_faces(V, [(u, v) for u, v, _, _ in raw_edges])
    active = sorted({i for f in faces for i in f})
    o2n = {o: i for i, o in enumerate(active)}
    Vc = V[active]
    Fc = [[o2n[i] for i in f] for f in faces]
    seen, E, A, FA = set(), [], [], []
    for f in Fc:
        for i in range(len(f)):
            u, v = f[i], f[(i + 1) % len(f)]
            k = (min(u, v), max(u, v))
            if k in seen:
                continue
            seen.add(k)
            ok = (min(active[u], active[v]), max(active[u], active[v]))
            asg, fa = emap.get(ok, ("B", 0.0))
            E.append((u, v))
            A.append(asg)
            FA.append(fa)
    return Model(Vc, Fc, E, A, FA)


def central_face(m: Model) -> int:
    c = m.vertices.mean(axis=0)
    best, bd = 0, float("inf")
    for i, f in enumerate(m.faces):
        fc = m.vertices[f].mean(axis=0)
        d = float(((fc - c) ** 2).sum())
        if d < bd:
            best, bd = i, d
    return best


def _rot(axis, ang):
    x, y, z = axis
    c, s = math.cos(ang), math.sin(ang)
    C = 1 - c
    return np.array([[c + x * x * C, x * y * C - z * s, x * z * C + y * s],
                     [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
                     [z * x * C - y * s, z * y * C + x * s, c + z * z * C]])


def solve_fold(m: Model, percent: float = 1.0, start: int | None = None,
               angles=None) -> list:
    """Return one 4x4 matrix per face (BFS over shared edges)."""
    if start is None:
        start = central_face(m)
    e2f: dict = {}
    for fi, f in enumerate(m.faces):
        for i in range(len(f)):
            k = (min(f[i], f[(i + 1) % len(f)]), max(f[i], f[(i + 1) % len(f)]))
            e2f.setdefault(k, []).append(fi)
    eidx = {(min(u, v), max(u, v)): i for i, (u, v) in enumerate(m.edges)}
    fa = m.fold_angle if angles is None else angles
    M = [None] * len(m.faces)
    M[start] = np.eye(4)
    q = deque([start])
    while q:
        cf = q.popleft()
        cm = M[cf]
        f = m.faces[cf]
        for i in range(len(f)):
            a, b = f[i], f[(i + 1) % len(f)]
            k = (min(a, b), max(a, b))
            for nf in e2f.get(k, ()):
                if nf == cf or M[nf] is not None:
                    continue
                ang = fa[eidx[k]] * percent if k in eidx else 0.0
                p1 = cm @ np.array([*m.vertices[a], 0.0, 1.0])
                p2 = cm @ np.array([*m.vertices[b], 0.0, 1.0])
                ax = p2[:3] - p1[:3]
                L = np.linalg.norm(ax)
                if L < 1e-12:
                    M[nf] = cm.copy()
                else:
                    R = np.eye(4)
                    R[:3, :3] = _rot(ax / L, math.radians(ang))
                    T, Ti = np.eye(4), np.eye(4)
                    T[:3, 3] = p1[:3]
                    Ti[:3, 3] = -p1[:3]
                    M[nf] = T @ R @ Ti @ cm
                q.append(nf)
    for i in range(len(M)):
        if M[i] is None:
            M[i] = np.eye(4)
    return M


def vertex_positions(m: Model, mats) -> np.ndarray:
    acc = np.zeros((len(m.vertices), 3))
    cnt = np.zeros(len(m.vertices))
    for fi, f in enumerate(m.faces):
        P = np.c_[m.vertices[f], np.zeros(len(f)), np.ones(len(f))] @ mats[fi].T
        acc[f] += P[:, :3]
        cnt[f] += 1
    out = np.c_[m.vertices, np.zeros(len(m.vertices))].astype(float)
    nz = cnt > 0
    out[nz] = acc[nz] / cnt[nz, None]
    return out


def face_positions(m: Model, mats) -> list:
    """Per-face 3-D polygons (each face transformed rigidly)."""
    out = []
    for fi, f in enumerate(m.faces):
        P = np.c_[m.vertices[f], np.zeros(len(f)), np.ones(len(f))] @ mats[fi].T
        out.append(P[:, :3])
    return out


def axial_strain(m: Model, X3: np.ndarray) -> float:
    err = np.zeros(len(m.vertices))
    cnt = np.zeros(len(m.vertices))
    for u, v in m.edges:
        L2 = np.linalg.norm(m.vertices[u] - m.vertices[v])
        if L2 > 1e-9:
            s = abs(np.linalg.norm(X3[u] - X3[v]) - L2) / L2
            err[u] += s
            err[v] += s
            cnt[u] += 1
            cnt[v] += 1
    nz = cnt > 0
    return float((err[nz] / cnt[nz]).mean()) if nz.any() else 0.0


def closure_error(m: Model, mats) -> float:
    """Max distance between a vertex's images in different faces (0 = the
    fold angles are globally consistent; this is what averaging hides)."""
    acc: dict = {}
    for fi, f in enumerate(m.faces):
        P = np.c_[m.vertices[f], np.zeros(len(f)), np.ones(len(f))] @ mats[fi].T
        for k, vi in enumerate(f):
            acc.setdefault(vi, []).append(P[k, :3])
    worst = 0.0
    for pts in acc.values():
        if len(pts) > 1:
            A = np.array(pts)
            worst = max(worst, float(np.ptp(A, axis=0).max()))
    return worst


def fold(V, raw_edges, percent: float = 1.0):
    m = build_model(V, raw_edges)
    mats = solve_fold(m, percent)
    X = vertex_positions(m, mats)
    return m, mats, X
