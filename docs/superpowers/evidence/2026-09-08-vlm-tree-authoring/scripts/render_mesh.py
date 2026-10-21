"""Offline three-view render of a .glb, using only the CI-pinned venv.

No matplotlib, no OpenGL, no quadric decimator -- this venv is pinned and
`pip install` is out of bounds. So: orthographic projection + painter's
algorithm + Lambertian shade, drawn with Pillow's ImageDraw.
"""
from __future__ import annotations
import os, sys
import numpy as np
from PIL import Image, ImageDraw
import trimesh

BG = (250, 250, 250)


def view(mesh, axes, flip, size=420, pad=0.06):
    """One orthographic view. `axes` = (horiz, vert, depth) column indices."""
    h, v, d = axes
    V = mesh.vertices
    F = mesh.faces
    x, y, z = V[:, h].copy(), V[:, v].copy(), V[:, d].copy()
    if flip[0]: x = -x
    if flip[1]: y = -y
    if flip[2]: z = -z

    span = max(np.ptp(x), np.ptp(y)) or 1.0
    s = size * (1 - 2 * pad) / span
    px = (x - x.mean()) * s + size / 2
    py = -(y - y.mean()) * s + size / 2          # image y grows downward

    # Lambertian shade from the camera direction, on the projected normal.
    n = mesh.face_normals
    nd = n[:, d] * (-1 if flip[2] else 1)
    shade = np.clip(0.30 + 0.70 * np.abs(nd), 0, 1)

    order = np.argsort(z[F].mean(axis=1))         # far -> near
    img = Image.new("RGB", (size, size), BG)
    draw = ImageDraw.Draw(img)
    for i in order:
        a, b, c = F[i]
        g = shade[i]
        col = (int(40 + 175 * g), int(70 + 165 * g), int(110 + 130 * g))
        draw.polygon([(px[a], py[a]), (px[b], py[b]), (px[c], py[c])],
                     fill=col)
    return img


def render(path, out, label=""):
    mesh = trimesh.load(path, force="mesh")
    mesh.vertices -= mesh.vertices.mean(axis=0)
    views = [((0, 1, 2), (False, False, False)),   # front  (XY)
             ((2, 1, 0), (False, False, False)),   # side   (ZY)
             ((0, 2, 1), (False, True, False))]    # top    (XZ)
    imgs = [view(mesh, a, f) for a, f in views]
    w = sum(i.width for i in imgs)
    sheet = Image.new("RGB", (w, imgs[0].height), BG)
    ox = 0
    for i in imgs:
        sheet.paste(i, (ox, 0))
        ox += i.width
    d = ImageDraw.Draw(sheet)
    for k, name in enumerate(("side", "front", "top")):
        d.text((k * imgs[0].width + 8, 6), name, fill=(90, 90, 90))
    if label:
        d.text((8, sheet.height - 16), label, fill=(90, 90, 90))
    sheet.save(out)
    return out


if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]
    label = sys.argv[3] if len(sys.argv) > 3 else os.path.basename(src)
    print(render(src, out, label))
