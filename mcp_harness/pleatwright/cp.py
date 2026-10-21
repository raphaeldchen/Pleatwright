"""Crease-pattern container and COrigami SVG I/O.

COrigami's crease patterns are plain SVGs on a ``viewBox="0 0 1000 1000"``
square: one ``<line>`` per crease, the stroke colour gives the assignment and
the optional ``opacity`` scales the target fold angle (COrigami Visualiser
``parseCreaseType`` / ``parseSVG``):

* ``red``   -> mountain, target -180 deg
* ``blue``  -> valley,   target +180 deg
* ``black`` -> border
* ``green`` -> hinge (unassigned in the packing CP), fold angle 0

so a shaping crease folded to 60 deg is a blue line with ``opacity="0.3333"``.
Solving-CP pleats additionally carry ``elevation="0|1"`` (their interleave
parity); we write the same attribute.

Internally a CP is a planar straight-line graph in GRID units (0..N), so box
pleated coordinates stay exact integers / dyadic rationals until written out.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

ANGLE = {"M": -180.0, "V": 180.0, "B": 0.0, "F": 0.0, "H": 0.0, "R": 0.0, "U": 0.0}
COLOR = {"M": "red", "V": "blue", "B": "black", "H": "green", "R": "red",
         "F": "green", "U": "gray"}
_PARSE = {"red": "M", "#ff0000": "M", "#f00": "M", "blue": "V", "#0000ff": "V",
          "#00f": "V", "black": "B", "#000000": "B", "#000": "B", "green": "F",
          "#00ff00": "F", "#0f0": "F", "yellow": "F", "#ffff00": "F", "#ff0": "F"}


@dataclass
class Edge:
    a: tuple            # (x, y) grid coords
    b: tuple
    kind: str           # M V B (assigned) | H hinge | R ridge | P pleat (unassigned packing) | F flat
    angle: float = 0.0  # signed target fold angle in degrees (+ valley, - mountain)
    role: str = ""      # hinge / ridge / pleat / shaping / border
    attrs: dict = field(default_factory=dict)


@dataclass
class CP:
    N: float                    # grid size (paper is [0,N]^2)
    edges: list                 # list[Edge]

    def svg(self, *, precision: int = 5, packing: bool = False) -> str:
        """Serialise in COrigami's format (viewBox 1000, y down)."""
        s = 1000.0 / self.N
        out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 1000">']
        for e in self.edges:
            if packing:
                col = {"H": "green", "R": "red", "B": "black"}.get(e.kind, "gray")
                extra = ""
            else:
                kind = e.kind
                col = COLOR.get(kind, "gray")
                extra = ""
                if kind in ("M", "V"):
                    full = ANGLE[kind]
                    frac = abs(e.angle / full) if full else 1.0
                    if abs(frac - 1.0) > 1e-7:
                        extra += f' opacity="{_fmt(frac, 7)}"'
                for k, v in e.attrs.items():
                    extra += f' {k}="{v}"'
            out.append(
                f'<line stroke="{col}" x1="{_fmt(e.a[0] * s, precision)}" '
                f'y1="{_fmt(e.a[1] * s, precision)}" x2="{_fmt(e.b[0] * s, precision)}" '
                f'y2="{_fmt(e.b[1] * s, precision)}"{extra}/>')
        out.append("</svg>")
        return "\n".join(out)


def fold_input(cp: "CP", *, split=True):
    """(vertices, raw_edges) for `fold.build_model`, in GRID units: border
    edges 'B' with angle 0, folded edges with their signed angle, unfolded
    hinges/flat lines dropped (they are not creases)."""
    V, vid, raw = [], {}, []

    def gid(p):
        k = (round(p[0], 9), round(p[1], 9))
        if k not in vid:
            vid[k] = len(V)
            V.append(k)
        return vid[k]
    for e in cp.edges:
        if e.kind not in ("B", "M", "V"):
            continue
        raw.append((gid(e.a), gid(e.b), e.kind, 0.0 if e.kind == "B" else e.angle))
    if split:
        raw = _split_collinear(V, raw, 1e-7)
    return V, raw


CP.fold_input = fold_input


def _fmt(v: float, p: int) -> str:
    r = round(float(v), p)
    if r == int(r):
        return str(int(r))
    return f"{r:.{p}f}".rstrip("0").rstrip(".")


def parse_svg(text: str):
    """Parse a COrigami SVG -> (vertices[0..1], edges[(i,j,assign,foldAngle)]).

    Faithful port of the visualiser's ``parseSVG``: merge vertices within
    tolerance, keep the highest-precedence assignment per vertex pair
    (M=V > F > B), split edges at T-junction vertices, normalise to [0,1].
    """
    vb = re.search(r'viewBox="([^"]+)"', text)
    xmin, ymin, w, h = (0.0, 0.0, 1000.0, 1000.0)
    if vb:
        xmin, ymin, w, h = (float(t) for t in vb.group(1).split())
    scale = max(w, h)
    tol = 1e-3
    verts: list = []
    vidx: dict = {}

    def vid(x, y):
        key = (round(x / tol), round(y / tol))
        for dk in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            k = (key[0] + dk[0], key[1] + dk[1])
            if k in vidx:
                i = vidx[k]
                if math.hypot(verts[i][0] - x, verts[i][1] - y) < tol:
                    return i
        verts.append((x, y))
        vidx[key] = len(verts) - 1
        return len(verts) - 1

    prec = {"M": 3, "V": 3, "F": 2, "B": 1, "U": 0}
    raw: dict = {}
    lines = []
    for m in re.finditer(r"<line\s([^>]*?)/?>", text):
        a = dict(re.findall(r'([\w-]+)="([^"]*)"', m.group(1)))
        col = a.get("stroke", "").strip().lower().replace(" ", "")
        asg = _PARSE.get(col, "U")
        if col.startswith("rgb(255,0,0)"):
            asg = "M"
        elif col.startswith("rgb(0,0,255)"):
            asg = "V"
        op = float(a.get("opacity", a.get("stroke-opacity", "1")))
        lines.append((asg, float(a.get("x1", 0)), float(a.get("y1", 0)),
                      float(a.get("x2", 0)), float(a.get("y2", 0)), op))
    for target in ("B", "M", "V", "F"):
        for asg, x1, y1, x2, y2, op in lines:
            if asg != target:
                continue
            if math.hypot(x1 - x2, y1 - y2) < 1e-5:
                continue
            fa = ANGLE.get(asg, 0.0) * op
            i, j = vid(x1, y1), vid(x2, y2)
            k = (min(i, j), max(i, j))
            if k not in raw or prec[asg] > prec[raw[k][2]]:
                raw[k] = (i, j, asg, fa)
    edges = _split_collinear(verts, list(raw.values()), tol)
    uniq: dict = {}
    for e in edges:
        k = (min(e[0], e[1]), max(e[0], e[1]))
        if k not in uniq or prec[e[2]] > prec[uniq[k][2]]:
            uniq[k] = e
    V = [((x - xmin) / scale, (y - ymin) / scale) for x, y in verts]
    return V, list(uniq.values())


def _split_collinear(verts, edges, tol):
    """Split every edge at any vertex lying strictly inside it (T-junctions)."""
    import numpy as np
    P = np.asarray(verts, float)
    out = []
    stack = list(edges)
    while stack:
        i, j, asg, fa = stack.pop()
        a, b = P[i], P[j]
        ab = b - a
        L2 = float(ab @ ab)
        if L2 < 1e-8:
            continue
        av = P - a
        cross = np.abs(ab[0] * av[:, 1] - ab[1] * av[:, 0]) / math.sqrt(L2)
        dot = av @ ab
        lim = tol * math.sqrt(L2)
        hit = np.where((cross < tol) & (dot > lim) & (dot < L2 - lim))[0]
        hit = [h for h in hit if h != i and h != j]
        if not hit:
            out.append((i, j, asg, fa))
            continue
        # split at the nearest interior vertex to a
        h = min(hit, key=lambda h: dot[h])
        stack.append((i, int(h), asg, fa))
        stack.append((int(h), j, asg, fa))
    return out
