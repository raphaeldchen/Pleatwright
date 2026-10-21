"""Three grid-overlay designs, one renderer, so only the grid differs.

A  ORIGINAL   what was actually used on 2026-09-06, invented with no prior art:
              grid drawn BEHIND the mesh, every line 1 px, ticks on the top and
              left edges only.

B  SPEC       the design as the 2026-09-07 spec words it: still BEHIND, but
              line-weighted per arXiv:2608.21170 (1 px minor / 4 px major) and
              ticked on all four edges.

C  OVERLAY    what the cited papers actually describe. arXiv:2411.18270 and
              arXiv:2608.21170 are OVERLAY methods -- the grid goes ON TOP of
              the image. Behind an opaque mesh the grid is hidden exactly where
              the joints are, and the line-width finding the spec quotes cannot
              apply. Same weights as B, drawn over the mesh at partial alpha.

Everything else -- camera, projection, shading, size, tick spacing, colours --
is identical across all three by construction.
"""
from __future__ import annotations
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import trimesh

GRID = 24
BG = (252, 252, 252)
MINOR = (196, 208, 224)
MAJOR = (150, 168, 196)
TICK = (90, 110, 140)


def _font(sz=11):
    for p in ("/System/Library/Fonts/Supplemental/Arial.ttf",
              "/System/Library/Fonts/Helvetica.ttc"):
        try:
            return ImageFont.truetype(p, sz)
        except Exception:
            pass
    return ImageFont.load_default()


def _grid_layer(size, x0, y0, step, variant, ticks_all_edges, alpha=None):
    """The grid on its own transparent layer, so A/B/C differ ONLY in when and
    how it is composited."""
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    dr = ImageDraw.Draw(layer)
    a = 255 if alpha is None else alpha
    for i in range(GRID + 1):
        major = (i % 4 == 0)
        if variant == "A":
            w = 1
        else:
            w = 4 if major else 1
        col = (MAJOR if major else MINOR) + (a,)
        dr.line([(x0 + i * step, 0), (x0 + i * step, size)], fill=col, width=w)
        dr.line([(0, y0 + i * step), (size, y0 + i * step)], fill=col, width=w)
    f = _font(11)
    for i in range(0, GRID + 1, 4):
        dr.text((x0 + i * step + 2, 2), str(i), fill=TICK + (255,), font=f)
        dr.text((2, y0 + i * step + 2), str(i), fill=TICK + (255,), font=f)
        if ticks_all_edges:
            dr.text((x0 + i * step + 2, size - 14), str(i),
                    fill=TICK + (255,), font=f)
            dr.text((size - 16, y0 + i * step + 2), str(i),
                    fill=TICK + (255,), font=f)
    return layer


def panel(mesh, axes, name, variant, size=560, pad=0.08):
    h, v, d = axes
    V, F = mesh.vertices, mesh.faces
    x, y, z = V[:, h], V[:, v], V[:, d]
    span = max(np.ptp(x), np.ptp(y)) or 1.0
    s = size * (1 - 2 * pad) / span
    cx, cy = (x.min() + x.max()) / 2, (y.min() + y.max()) / 2
    px = (x - cx) * s + size / 2
    py = -(y - cy) * s + size / 2
    step = s * span / GRID
    x0 = size / 2 - (span / 2) * s
    y0 = size / 2 - (span / 2) * s

    img = Image.new("RGBA", (size, size), BG + (255,))
    grid = _grid_layer(size, x0, y0, step, variant,
                       ticks_all_edges=(variant in ("B", "C")),
                       alpha=(150 if variant == "C" else 255))

    if variant in ("A", "B"):
        img.alpha_composite(grid)              # BEHIND the mesh

    mesh_layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    dr = ImageDraw.Draw(mesh_layer)
    nd = mesh.face_normals[:, d]
    shade = np.clip(0.35 + 0.65 * np.abs(nd), 0, 1)
    for i in np.argsort(z[F].mean(axis=1)):
        a_, b_, c_ = F[i]
        g = shade[i]
        col = (int(70 + 150 * g), int(95 + 140 * g), int(125 + 115 * g), 255)
        dr.polygon([(px[a_], py[a_]), (px[b_], py[b_]), (px[c_], py[c_])],
                   fill=col)
    img.alpha_composite(mesh_layer)

    if variant == "C":
        img.alpha_composite(grid)              # ON TOP of the mesh

    out = img.convert("RGB")
    d2 = ImageDraw.Draw(out)
    d2.rectangle([0, 0, size - 1, size - 1], outline=(120, 120, 120))
    d2.text((6, size - 15), f"{name}   grid={GRID} across max extent",
            fill=(50, 50, 50), font=_font(11))
    return out


#: Panel titles. The historical arm-C set named the panels anatomically, which
#: is false whenever the mesh's longest extent is not nose-to-tail (bat, crab):
#: full17 bat #2 followed "side (XY)" literally and authored a tree rotated 90
#: degrees. "D" is arm C's grid with the panels named by mesh axis only, the
#: same words `vlm_render.PANEL_NAMES` puts on the production render.
PANEL_TITLES = {"C": ("side (XY)", "front (ZY)", "top (XZ)"),
                "D": ("XY panel", "ZY panel", "XZ panel")}


def sheet(mesh_path, out_path, label, variant):
    mesh = trimesh.load(mesh_path, force="mesh")
    mesh.vertices -= mesh.vertices.mean(axis=0)
    titles = PANEL_TITLES.get(variant, PANEL_TITLES["C"])
    grid_variant = "C" if variant == "D" else variant
    views = list(zip([(0, 1, 2), (2, 1, 0), (0, 2, 1)], titles))
    imgs = [panel(mesh, a, n, grid_variant) for a, n in views]
    W = sum(i.width for i in imgs)
    s = Image.new("RGB", (W, imgs[0].height + 20), BG)
    for i, im in enumerate(imgs):
        s.paste(im, (i * im.width, 20))
    tag = {"A": "A / original (grid behind, 1px uniform, 2-edge ticks)",
           "B": "B / spec (grid behind, 1px+4px weighted, 4-edge ticks)",
           "C": "C / overlay (grid ON TOP at alpha 150, weighted, 4-edge)",
           "D": "D / arm-C grid, panels named by mesh axis"}[variant]
    ImageDraw.Draw(s).text((6, 4), f"{label}    {tag}", fill=(20, 20, 20),
                           font=_font(12))
    s.save(out_path)
    return out_path


if __name__ == "__main__":
    src, out, label, variant = sys.argv[1:5]
    print(sheet(src, out, label, variant))
