"""Rendering: crease patterns, stick figures, folded models, overview sheet.

The overview reproduces the layout of COrigami's ``overview.png`` (Fig. 4):
row 1 = (1) stick figure in four views (top / side / front / isometric),
(2) packing CP, (3) solving CP with its flat-foldable vertex count,
(4) shaping CP with its count; row 2 = the folded model in seven views.
"""
from __future__ import annotations

import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

PAPER = np.array([0.66, 0.11, 0.18])          # COrigami's crimson
CP_COL = {"M": "red", "V": "blue", "B": "black", "H": "green", "R": "red",
          "F": "#bbbbbb", "U": "gray"}

# World = the mesh's own axes (+Y up, profile in the XY panel, Z lateral).
# Plot coordinates are (x, -z, y): a proper rotation that puts +Y on
# matplotlib's vertical axis.  (elev, azim) below are in plot coordinates.
def to_plot(P):
    P = np.asarray(P, float)
    return np.stack([P[..., 0], -P[..., 2], P[..., 1]], axis=-1)


# seven model views: profile, front, top, two front obliques, rear oblique,
# low oblique (COrigami renders seven perspectives, §3.7 / §3.8)
VIEWS = [(8, -90), (8, 0), (88, -90), (28, -55), (28, -125), (25, 140), (-20, -60)]
# stick-figure views (COrigami Fig. 4: top / side / front / isometric), with
# the viewing vector written in the mesh's axes
STICK_VIEWS = [("top view", (0, 1, 0), (90, -90)), ("side view", (0, 0, 1), (0, -90)),
               ("front view", (1, 0, 0), (0, 0)), ("isometric view", (1, 1, 1), (35, -45))]


def draw_cp(ax, cp, *, packing=False, title=None, note=None, dots=None):
    N = cp.N
    order = {"F": 0, "H": 1, "R": 2, "M": 2, "V": 2, "B": 3}
    for e in sorted(cp.edges, key=lambda e: order.get(e.kind, 1)):
        if packing:
            col = {"H": "green", "R": "red", "B": "black"}.get(e.kind, "gray")
            lw = 0.8 if e.kind != "B" else 1.0
            alpha = 1.0
        else:
            col = CP_COL.get(e.kind, "gray")
            lw = 0.35 if e.kind in "MV" else 0.9
            alpha = 1.0
            if e.kind in "MV":
                alpha = max(0.25, min(1.0, abs(e.angle) / 180.0))
        ax.plot([e.a[0], e.b[0]], [e.a[1], e.b[1]], color=col, lw=lw, alpha=alpha,
                solid_capstyle="butt")
    if dots:
        xs, ys = zip(*dots)
        ax.plot(xs, ys, "o", color="red", ms=2.5)
    ax.set_xlim(-0.01 * N, 1.01 * N)
    ax.set_ylim(1.01 * N, -0.01 * N)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    if title:
        ax.set_title(title, fontsize=9)
    if note:
        ax.text(1.0, 1.005, note, transform=ax.transAxes, ha="right", va="bottom",
                fontsize=6)


def _shade(polys, light=np.array([0.3, -0.4, 0.85])):
    light = light / np.linalg.norm(light)
    cols = []
    for P in polys:
        if len(P) < 3:
            cols.append(PAPER)
            continue
        n = np.cross(P[1] - P[0], P[2] - P[0])
        k = np.linalg.norm(n)
        if k < 1e-12:
            # pick any non-degenerate triple
            for i in range(2, len(P)):
                n = np.cross(P[1] - P[0], P[i] - P[0])
                k = np.linalg.norm(n)
                if k > 1e-12:
                    break
        d = abs(float(n @ light) / k) if k > 1e-12 else 0.5
        cols.append(np.clip(PAPER * (0.55 + 0.6 * d), 0, 1))
    return cols


def _fit_box(ax, P, margin=0.06):
    """Axis limits = the data's own ranges (uniform scale via box aspect), so
    every panel is filled the way COrigami's are."""
    lo, hi = P.min(axis=0), P.max(axis=0)
    span = hi - lo
    floor = max(float(span.max()) * 0.04, 1e-6)
    span = np.maximum(span, floor)
    c = (lo + hi) / 2
    half = span / 2 * (1 + margin)
    ax.set_xlim(c[0] - half[0], c[0] + half[0])
    ax.set_ylim(c[1] - half[1], c[1] + half[1])
    ax.set_zlim(c[2] - half[2], c[2] + half[2])
    ax.set_box_aspect(tuple(half))


def draw_model(ax, polys, view, *, lims=None):
    polys = [to_plot(P) for P in polys]
    # matplotlib 3.11 autoscales over uninitialized ragged padding; we set
    # limits explicitly in _fit_box below, so disable autolim
    ax.add_collection3d(Poly3DCollection(polys, facecolors=_shade(polys),
                                         edgecolors="none", linewidths=0),
                        autolim=False)
    _fit_box(ax, np.vstack(polys))
    ax.view_init(elev=view[0], azim=view[1])
    ax.set_proj_type("ortho")
    ax.set_axis_off()


def model_limits(polys):
    P = to_plot(np.vstack(polys))
    lo, hi = P.min(axis=0), P.max(axis=0)
    c = (lo + hi) / 2
    r = float((hi - lo).max()) / 2 * 1.02 + 1e-9
    return tuple(c), r


def draw_stick(ax, stick, title, view):
    """3-D stick figure in COrigami's style: black sticks with a green
    'name: length' label, blue joints with a red 'j_name' label."""
    P = {k: to_plot(v) for k, v in stick.positions().items()}
    for s in stick.sticks:
        a, b = P[s.start], P[s.end]
        ax.plot([a[0], b[0]], [a[1], b[1]], [a[2], b[2]], color="black", lw=1.2)
        m = (a + b) / 2
        ax.text(m[0], m[1], m[2], f"{s.name}: {s.length:g}", color="green", fontsize=5.5)
    for name, p in P.items():
        ax.scatter([p[0]], [p[1]], [p[2]], color="blue", s=6, depthshade=False)
        if name != stick.root:
            ax.text(p[0], p[1], p[2], f" j_{name}", color="red", fontsize=4.8)
    _fit_box(ax, np.array(list(P.values())), margin=0.12)
    ax.view_init(elev=view[0], azim=view[1])
    ax.set_proj_type("ortho")
    ax.set_axis_off()
    ax.set_title(title, fontsize=6, bbox=dict(facecolor="white", edgecolor="black", lw=0.6))


def overview(path, *, name, grid, stick, packing_cp, solving_cp, shaping_cp,
             polys, solving_ff, shaping_ff, packing_dots=None):
    fig = plt.figure(figsize=(22.42, 7.535), dpi=200)
    fig.suptitle(f"{name} (grid_size={grid})", fontsize=10, y=0.985)
    W = 7
    for i, (vname, vec, view) in enumerate(STICK_VIEWS):
        ax = fig.add_subplot(2, W, i + 1, projection="3d")
        draw_stick(ax, stick, f"{name} ({vname}\n{vec}) | complexity={stick.complexity}", view)
        ax.text2D(0.5, -0.06, f"View {i + 1}", transform=ax.transAxes, ha="center", fontsize=8)
    fig.text(0.29, 0.92, "(1) Stick Figure", ha="center", fontsize=8)
    ax = fig.add_subplot(2, W, 5)
    draw_cp(ax, packing_cp, packing=True, title="(2) Packing CP", dots=packing_dots)
    ax.text(0.5, -0.12, "View 5", transform=ax.transAxes, ha="center", fontsize=8)
    ax = fig.add_subplot(2, W, 6)
    draw_cp(ax, solving_cp, title="(3) Solving CP",
            note=f"Flat-foldable: {solving_ff[0]}/{solving_ff[1]}")
    ax.text(0.5, -0.12, "View 6", transform=ax.transAxes, ha="center", fontsize=8)
    ax = fig.add_subplot(2, W, 7)
    draw_cp(ax, shaping_cp, title="(4) Shaping CP",
            note=f"Flat-foldable: {shaping_ff[0]}/{shaping_ff[1]}")
    ax.text(0.5, -0.12, "View 7", transform=ax.transAxes, ha="center", fontsize=8)
    lims = model_limits(polys)
    for i, view in enumerate(VIEWS):
        ax = fig.add_subplot(2, W, W + i + 1, projection="3d")
        draw_model(ax, polys, view, lims=lims)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.9, bottom=0.02, wspace=0.08, hspace=0.12)
    fig.savefig(path, dpi=200)
    plt.close(fig)


def model_sheet(path, polys, title=""):
    fig = plt.figure(figsize=(28, 4.2), dpi=100)
    lims = model_limits(polys)
    for i, view in enumerate(VIEWS):
        ax = fig.add_subplot(1, 7, i + 1, projection="3d")
        draw_model(ax, polys, view, lims=lims)
    if title:
        fig.suptitle(title)
    fig.subplots_adjust(left=0, right=1, top=0.92, bottom=0, wspace=0)
    fig.savefig(path, dpi=100)
    plt.close(fig)
