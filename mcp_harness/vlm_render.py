"""Renders for the VLM tree-authoring loop: the ruler, and the stick figure.

Two pictures, for two different readers.

`render_mesh_views` is the RULER. It draws a mesh under a labelled grid so a
vision model can READ joint coordinates off it rather than infer geometry. This
is the mechanism the whole approach rests on: it turns a 3-D geometry problem
into a 2-D measurement problem, which is what a VLM is good at.

`render_tree_sheet` is for the HUMAN. It draws an authored tree in four views
for the approval gate. It was measured NOT to help when shown back to the model
(spec 2b/2c), and it is the only thing that has ever caught an inverted tree --
a defect invisible to every numeric metric in this project.

GRID DESIGN IS DELIBERATELY UNSPECIFIED beyond "lines, not fills". Three
designs -- 1px behind the mesh, weighted behind, weighted overlaid -- scored
IDENTICALLY on anatomy and on reading fidelity (spec 2a). Pinning a weight
would be inventing a requirement no measurement supports.

⚠ THE TWO FRAMES DISAGREE, AND CALLERS MUST SAY SO. This module draws with the
image convention: grid v increases DOWNWARD, tick 0 at the top. Authored
directions use +y UP. A model that does not flip the sign produces a tree with
its limbs in the air that still scores exact on every count-based metric --
measured on 2 of 17 trees. `MESH_VIEW_FRAME_NOTE` is the wording that fixed it
and belongs in any authoring prompt built on these renders.
"""
from __future__ import annotations

import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

GRID = 24
BG = (252, 252, 252)
MINOR, MAJOR, TICK = (196, 208, 224), (150, 168, 196), (90, 110, 140)
EDGE, NODE, LEAF = (40, 40, 40), (200, 40, 40), (40, 60, 200)
NAME_COL, LEN_COL = (190, 30, 30), (20, 120, 40)

#: (horizontal, vertical, depth) column indices per view.
VIEWS = {"side": (0, 1, 2), "front": (2, 1, 0), "top": (0, 2, 1)}
TREE_VIEWS = ("top", "side", "front", "isometric")

#: What each panel is CALLED on the sheet. Named by mesh axis, never by
#: anatomy: whether the XY plane is the animal's side or its front depends on
#: which way the mesh's longest extent runs, and the renderer cannot know.
#: Measured 2026-09-13: the bat mesh's longest extent is its wingspan, so a
#: panel titled "side view" showed its FRONT, and one of three authored trees
#: followed the title literally -- wings along +-x, rotated 90 degrees. The
#: view KEYS stay ("side"/"front"/"top") because they are column choices and
#: callers index by them; only the words a model reads have changed.
PANEL_NAMES = {"side": "XY panel", "front": "ZY panel", "top": "XZ panel",
               "isometric": "isometric"}

MESH_VIEW_FRAME_NOTE = (
    "The grid's vertical axis increases DOWNWARD: tick 0 is at the TOP of each "
    "panel and 24 at the BOTTOM, so the ground is a LARGE second number and "
    "the animal's back is a SMALL one. If you emit direction vectors in a "
    "+y-UP frame you must FLIP THE SIGN: a limb that descends on screen has a "
    "NEGATIVE dy."
)


def _font(sz=11):
    for p in ("/System/Library/Fonts/Supplemental/Arial.ttf",
              "/System/Library/Fonts/Helvetica.ttc"):
        try:
            return ImageFont.truetype(p, sz)
        except Exception:
            pass
    return ImageFont.load_default()


# --------------------------------------------------------------- the ruler
def _mesh_panel(mesh, axes, name, size, pad=0.08):
    h, v, d = axes
    V, F = np.asarray(mesh.vertices), np.asarray(mesh.faces)
    x, y, z = V[:, h], V[:, v], V[:, d]
    span = max(np.ptp(x), np.ptp(y)) or 1.0
    s = size * (1 - 2 * pad) / span
    cx, cy = (x.min() + x.max()) / 2, (y.min() + y.max()) / 2
    px = (x - cx) * s + size / 2
    py = -(y - cy) * s + size / 2
    step = s * span / GRID
    x0 = y0 = size / 2 - (span / 2) * s

    img = Image.new("RGB", (size, size), BG)
    dr = ImageDraw.Draw(img)
    f = _font(11)
    for i in range(GRID + 1):
        major = (i % 4 == 0)
        col = MAJOR if major else MINOR
        dr.line([(x0 + i * step, 0), (x0 + i * step, size)], fill=col)
        dr.line([(0, y0 + i * step), (size, y0 + i * step)], fill=col)
        if major:
            dr.text((x0 + i * step + 2, 2), str(i), fill=TICK, font=f)
            dr.text((2, y0 + i * step + 2), str(i), fill=TICK, font=f)

    nd = mesh.face_normals[:, d]
    shade = np.clip(0.35 + 0.65 * np.abs(nd), 0, 1)
    for i in np.argsort(z[F].mean(axis=1)):
        a, b, c = F[i]
        g = shade[i]
        dr.polygon([(px[a], py[a]), (px[b], py[b]), (px[c], py[c])],
                   fill=(int(70 + 150 * g), int(95 + 140 * g), int(125 + 115 * g)))
    dr.rectangle([0, 0, size - 1, size - 1], outline=(120, 120, 120))
    dr.text((6, size - 15), f"{name}   grid={GRID} across the longest extent",
            fill=(50, 50, 50), font=f)
    return img


def render_mesh_views(mesh_path: str, out_path: str, *, label: str = "",
                      views=("side", "front", "top"), size: int = 560) -> dict:
    """Draw a mesh under a labelled measurement grid. Returns metadata."""
    import trimesh
    mesh = trimesh.load(mesh_path, force="mesh")
    mesh.vertices = mesh.vertices - mesh.vertices.mean(axis=0)
    imgs = [_mesh_panel(mesh, VIEWS[v], PANEL_NAMES[v], size) for v in views]
    sheet = Image.new("RGB", (sum(i.width for i in imgs), size + 20), BG)
    for i, im in enumerate(imgs):
        sheet.paste(im, (i * im.width, 20))
    ImageDraw.Draw(sheet).text((6, 4), label or os.path.basename(mesh_path),
                               fill=(20, 20, 20), font=_font(12))
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    sheet.save(out_path)
    e = mesh.extents
    return {"png": out_path, "grid": GRID, "views": list(views),
            "panels": [PANEL_NAMES[v] for v in views],
            "extent_xyz": [round(float(t), 4) for t in e],
            "max_extent": round(float(e.max()), 4),
            "frame_note": MESH_VIEW_FRAME_NOTE}


# ---------------------------------------------------------- the stick figure
def positions(nodes) -> dict:
    """Derive node positions from (name, parent, direction, length).

    Positions are DERIVED, never passed in, so a drawn sheet cannot disagree
    with the tree it claims to draw."""
    pos = {}
    for name, parent, d, ln in nodes:
        if parent is None or d is None:
            pos[name] = (0.0, 0.0, 0.0)
            continue
        px, py, pz = pos[parent]
        n = math.sqrt(sum(c * c for c in d)) or 1.0
        pos[name] = (px + d[0] / n * ln, py + d[1] / n * ln, pz + d[2] / n * ln)
    return pos


def leaves_of(nodes) -> list:
    kids = {}
    for name, parent, _, _ in nodes:
        if parent:
            kids[parent] = kids.get(parent, 0) + 1
    return [n[0] for n in nodes if kids.get(n[0], 0) == 0]


def _project(p, view):
    if view == "isometric":
        return ((p[0] - p[2]) * 0.866, p[1] + (p[0] + p[2]) * 0.5)
    # Every panel is drawn with its vertical column UP, exactly as `_mesh_panel`
    # draws the mesh -- so the top view has +z upward, and the sheet a reviewer
    # holds next to the mesh render is not mirrored against it (it was, until
    # 2026-09-13).
    h, v, _ = VIEWS[view]
    return (p[h], p[v])


def _tree_panel(nodes, pos, view, size, pad=0.13):
    pts = {n[0]: _project(pos[n[0]], view) for n in nodes}
    xs = [p[0] for p in pts.values()]; ys = [p[1] for p in pts.values()]
    span = max(max(xs) - min(xs), max(ys) - min(ys)) or 1.0
    s = size * (1 - 2 * pad) / span
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    P = {n: (size / 2 + (p[0] - cx) * s, size / 2 - (p[1] - cy) * s)
         for n, p in pts.items()}
    img = Image.new("RGB", (size, size), (253, 253, 251))
    dr = ImageDraw.Draw(img)
    ft = _font(10)
    lf = set(leaves_of(nodes))
    for name, parent, _, ln in nodes:
        if parent is None:
            continue
        dr.line([P[parent], P[name]], fill=EDGE, width=2)
        mx = (P[parent][0] + P[name][0]) / 2; my = (P[parent][1] + P[name][1]) / 2
        dr.text((mx + 3, my - 5), f"{name}: {ln}", fill=LEN_COL, font=ft)
    for name, _, _, _ in nodes:
        x, y = P[name]
        r, col = (4, LEAF) if name in lf else (3, NODE)
        dr.ellipse([x - r, y - r, x + r, y + r], fill=col)
        dr.text((x + 5, y + 3), name, fill=NAME_COL, font=ft)
    dr.rectangle([0, 0, size - 1, size - 1], outline=(170, 170, 170))
    dr.text((7, 6), PANEL_NAMES[view], fill=(30, 30, 30), font=_font(11))
    return img


def render_tree_sheet(nodes, out_path: str, *, title: str = "",
                      size: int = 520) -> dict:
    """Draw an authored tree in four views, for the HUMAN approval gate."""
    pos = positions(nodes)
    imgs = [_tree_panel(nodes, pos, v, size) for v in TREE_VIEWS]
    sheet = Image.new("RGB", (sum(i.width for i in imgs), size + 26),
                      (253, 253, 251))
    for i, im in enumerate(imgs):
        sheet.paste(im, (i * im.width, 26))
    lf = leaves_of(nodes)
    ImageDraw.Draw(sheet).text(
        (8, 7), f"{title}   {len(nodes)} nodes, {len(lf)} leaves",
        fill=(20, 20, 20), font=_font(13))
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    sheet.save(out_path)
    return {"png": out_path, "views": list(TREE_VIEWS),
            "n_nodes": len(nodes), "leaves": lf}
