"""Analytic flat-folded 2D state of a compiled base (folded-state-first
slice 1): where every face of a crease pattern lands at a 100% flat
fold, by composing reflections along the face-adjacency tree (Lang's
construction). Self-consistency is REPORTED, not assumed: hull-frontier
bases (accepted Kawasaki violations) and squared display folds have no
consistent flat-folded state — flat_fold() returns their closure errors
instead of raising.

Spec:  docs/superpowers/specs/2026-07-03-flat-fold-engine-slice1-design.md
Probe: docs/superpowers/2026-07-03-probe-folded-state-findings.md
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

import numpy as np

# Non-tree shared edges whose two transform paths disagree by more than
# this (paper units) are "bad": genuine flat-fold inconsistency rather
# than float noise. Clean raw bases measure <= 1e-9; the first genuinely
# inconsistent fixtures measure >= 0.39 (probe findings §2).
CLOSURE_EPS = 1e-6


def _validate(fold: dict) -> None:
    for key in ("vertices_coords", "edges_vertices", "edges_assignment"):
        if key not in fold or fold[key] is None:
            raise ValueError(f"fold is missing '{key}'")

    # Check that arrays are not all empty
    if not fold["vertices_coords"] and not fold["edges_vertices"] and not fold["edges_assignment"]:
        raise ValueError("fold has empty arrays")

    # Check that edges_vertices and edges_assignment have the same length
    if len(fold["edges_vertices"]) != len(fold["edges_assignment"]):
        raise ValueError(
            "edges_vertices and edges_assignment lengths differ")


def _signed_area(P: np.ndarray) -> float:
    x, y = P[:, 0], P[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def _extract_faces(V: np.ndarray, edges: list) -> list[list[int]]:
    """Interior faces (CCW) of the planar straight-line graph.

    Angle-sorted rotations + half-edge walk — the same construction the
    vendored bridge gets from the FOLD JS library
    (vertices_vertices_to_faces_vertices). The outer face winds CW
    (signed area < 0) and is dropped.
    """
    nbrs: dict[int, list[int]] = {}
    for u, v in edges:
        nbrs.setdefault(u, []).append(v)
        nbrs.setdefault(v, []).append(u)
    for u in nbrs:
        nbrs[u].sort(key=lambda w: math.atan2(V[w][1] - V[u][1],
                                              V[w][0] - V[u][0]))
    limit = 2 * len(edges) + 1
    visited: set[tuple[int, int]] = set()
    interior: list[list[int]] = []
    for start in [(u, v) for u, v in edges] + [(v, u) for u, v in edges]:
        if start in visited:
            continue
        face: list[int] = []
        u, v = start
        while (u, v) not in visited:
            if len(face) > limit:
                raise ValueError("face walk failed to terminate")
            visited.add((u, v))
            face.append(u)
            ring = nbrs[v]
            u, v = v, ring[(ring.index(u) - 1) % len(ring)]
        if (u, v) != start:
            raise ValueError("face walk failed to close")
        if _signed_area(V[face]) > 0:
            interior.append(face)
    return interior


@dataclass(frozen=True)
class ClosureReport:
    """Cycle-closure errors of the reflection composition: one entry
    per non-spanning-tree shared edge, as (error_paper_units,
    (v_lo, v_hi), edge_assignment). Large errors mean the input has no
    consistent flat-folded state (hull-frontier Kawasaki violations,
    squared frames) — a reported property, not an error condition."""
    edge_errors: tuple

    @property
    def max_error(self) -> float:
        return max((e for e, _, _ in self.edge_errors), default=0.0)

    @property
    def bad_edges(self) -> tuple:
        return tuple(x for x in self.edge_errors if x[0] > CLOSURE_EPS)


@dataclass(frozen=True, eq=False)
class FlatFoldResult:
    faces: list            # interior faces, CCW vertex-index lists
    transforms: list       # per-face 3x3 homogeneous 2D (flat -> folded)
    folded_vertices: list  # per-face Nx2 arrays; [i][j] is the image of
                           # faces[i][j] (a CP vertex has one image PER
                           # face it belongs to)
    closure: "ClosureReport"
    # every shared edge as (face_a, face_b, (v_lo, v_hi), assignment) —
    # layer ordering needs M/V labels, which folded geometry alone
    # cannot recover (M and V reflect identically)
    shared_edges: tuple = ()


def _reflect(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """3x3 homogeneous reflection across the line through a and b."""
    d = b - a
    n = float(np.hypot(d[0], d[1]))
    if n < 1e-12:
        raise ValueError("degenerate zero-length crease")
    d = d / n
    R = np.eye(3)
    R[0, 0] = d[0] * d[0] - d[1] * d[1]
    R[0, 1] = R[1, 0] = 2.0 * d[0] * d[1]
    R[1, 1] = d[1] * d[1] - d[0] * d[0]
    R[:2, 2] = a - R[:2, :2] @ a
    return R


def _apply(T: np.ndarray, p: np.ndarray) -> np.ndarray:
    return T[:2, :2] @ p + T[:2, 2]


def flat_fold(fold: dict) -> FlatFoldResult:
    """Analytic flat-folded state of a FOLD crease pattern.

    Raises ValueError only for structurally unusable input; folds with
    no consistent flat-folded state return normally with large
    closure errors (see ClosureReport).
    """
    _validate(fold)
    V = np.asarray([v[:2] for v in fold["vertices_coords"]], dtype=float)
    edges = [tuple(e) for e in fold["edges_vertices"]]
    for u, v in edges:
        if float(np.hypot(*(V[u] - V[v]))) < 1e-12:
            raise ValueError("degenerate zero-length edge")
    faces = _extract_faces(V, edges)
    if not faces:
        raise ValueError("crease pattern has no interior faces")
    assign = {tuple(sorted(e)): a
              for e, a in zip(edges, fold["edges_assignment"])}

    # face adjacency across shared edges (an edge bounds <= 2 faces)
    edge_faces: dict[tuple[int, int], list[int]] = {}
    for fi, f in enumerate(faces):
        for j in range(len(f)):
            k = tuple(sorted((f[j], f[(j + 1) % len(f)])))
            edge_faces.setdefault(k, []).append(fi)
    adj: dict[int, list] = {i: [] for i in range(len(faces))}
    shared = []
    for k, fs in edge_faces.items():
        if len(fs) == 2:
            shared.append((fs[0], fs[1], k))
            adj[fs[0]].append((fs[1], k))
            adj[fs[1]].append((fs[0], k))

    def edge_transform(k: tuple[int, int]) -> np.ndarray:
        # M/V creases reflect at a 100% flat fold; F (facet) edges join
        # faces that fold together; B never bounds two faces.
        return (_reflect(V[k[0]], V[k[1]])
                if assign.get(k, "F") in ("M", "V") else np.eye(3))

    # deterministic root: largest interior face, ties to lowest index
    root = max(range(len(faces)),
               key=lambda i: (abs(_signed_area(V[faces[i]])), -i))
    T: list = [None] * len(faces)
    T[root] = np.eye(3)
    tree: set = set()
    q = deque([root])
    while q:
        fi = q.popleft()
        for fj, k in adj[fi]:
            if T[fj] is None:
                T[fj] = T[fi] @ edge_transform(k)
                tree.add((min(fi, fj), max(fi, fj), k))
                q.append(fj)
    if any(t is None for t in T):
        raise ValueError("face-adjacency graph is disconnected")

    errors = []
    for fa, fb, k in shared:
        if (min(fa, fb), max(fa, fb), k) in tree:
            continue
        expect = T[fa] @ edge_transform(k)
        err = max(float(np.linalg.norm(_apply(expect, V[p])
                                       - _apply(T[fb], V[p])))
                  for p in k)
        errors.append((err, k, assign.get(k, "F")))

    folded = [np.asarray([_apply(T[i], V[p]) for p in f])
              for i, f in enumerate(faces)]
    return FlatFoldResult(faces=faces, transforms=T,
                          folded_vertices=folded,
                          closure=ClosureReport(edge_errors=tuple(errors)),
                          shared_edges=tuple(
                              (fa, fb, k, assign.get(k, "F"))
                              for fa, fb, k in shared))
