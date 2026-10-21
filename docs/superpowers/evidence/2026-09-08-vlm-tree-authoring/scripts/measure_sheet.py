"""Render a mesh under a labelled grid, so joint positions can be READ rather
than guessed.

The whole point of hand-authoring is that a person looks at the object and
writes down proportions. A person still needs a ruler. This puts one on the
mesh: the longest extent is divided into GRID units and both axes are ticked,
so "the knee sits at 7 units along the leg" is a reading, not a vibe.
"""
from __future__ import annotations
import os, sys
import numpy as np
from PIL import Image, ImageDraw
import trimesh

GRID = 24
BG = (252, 252, 252)


def panel(mesh, axes, name, size=560, pad=0.08):
    h, v, d = axes
    V, F = mesh.vertices, mesh.faces
    x, y, z = V[:, h], V[:, v], V[:, d]
    span = max(np.ptp(x), np.ptp(y)) or 1.0
    s = size * (1 - 2 * pad) / span
    cx, cy = (x.min() + x.max()) / 2, (y.min() + y.max()) / 2
    px = (x - cx) * s + size / 2
    py = -(y - cy) * s + size / 2

    img = Image.new("RGB", (size, size), BG)
    dr = ImageDraw.Draw(img)
    # grid FIRST, so the mesh sits on top of it and edges stay readable
    step = s * span / GRID
    x0 = size / 2 - (span / 2) * s
    y0 = size / 2 - (span / 2) * s
    for i in range(GRID + 1):
        c = (196, 208, 224) if i % 4 else (150, 168, 196)
        dr.line([(x0 + i * step, 0), (x0 + i * step, size)], fill=c)
        dr.line([(0, y0 + i * step), (size, y0 + i * step)], fill=c)
        if i % 4 == 0:
            dr.text((x0 + i * step + 2, 2), str(i), fill=(90, 110, 140))
            dr.text((2, y0 + i * step + 2), str(i), fill=(90, 110, 140))

    nd = mesh.face_normals[:, d]
    shade = np.clip(0.35 + 0.65 * np.abs(nd), 0, 1)
    order = np.argsort(z[F].mean(axis=1))
    for i in order:
        a, b, c_ = F[i]
        g = shade[i]
        col = (int(70 + 150 * g), int(95 + 140 * g), int(125 + 115 * g))
        dr.polygon([(px[a], py[a]), (px[b], py[b]), (px[c_], py[c_])], fill=col)
    dr.rectangle([0, 0, size - 1, size - 1], outline=(120, 120, 120))
    dr.text((6, size - 14), f"{name}   grid={GRID} across max extent",
            fill=(60, 60, 60))
    return img


def sheet(path, out, label):
    mesh = trimesh.load(path, force="mesh")
    mesh.vertices -= mesh.vertices.mean(axis=0)
    views = [((0, 1, 2), "side (XY)"), ((2, 1, 0), "front (ZY)"),
             ((0, 2, 1), "top (XZ)")]
    imgs = [panel(mesh, a, n) for a, n in views]
    W = sum(i.width for i in imgs)
    s = Image.new("RGB", (W, imgs[0].height + 18), BG)
    ox = 0
    for i in imgs:
        s.paste(i, (ox, 18)); ox += i.width
    ImageDraw.Draw(s).text((6, 4), label, fill=(30, 30, 30))
    s.save(out)
    e = mesh.extents
    return {"extent_xyz": [round(float(v), 4) for v in e],
            "max_extent": round(float(e.max()), 4)}


if __name__ == "__main__":
    src, out, label = sys.argv[1], sys.argv[2], sys.argv[3]
    print(sheet(src, out, label))
