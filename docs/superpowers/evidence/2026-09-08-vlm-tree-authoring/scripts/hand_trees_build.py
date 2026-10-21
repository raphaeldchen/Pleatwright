"""Turn the hand-authored trees into trees.json, part tables and 4-view sheets.

Positions are DERIVED from (parent, direction, length), never authored
separately, so a sheet cannot drift from the metric tree it draws.
"""
from __future__ import annotations
import json, math, os, sys
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hand_trees_data as H

LONGEST_LIMB_TARGET = 0.40   # mesh_to_tree.LONGEST_LIMB_TARGET
BG = (253, 253, 251)
C_EDGE, C_NODE, C_LEAF = (40, 40, 40), (200, 40, 40), (40, 60, 200)
C_NAME, C_LEN = (190, 30, 30), (20, 120, 40)


def _font(sz):
    for p in ("/System/Library/Fonts/Supplemental/Arial.ttf",
              "/System/Library/Fonts/Helvetica.ttc"):
        try:
            return ImageFont.truetype(p, sz)
        except Exception:
            pass
    return ImageFont.load_default()


def positions(nodes):
    """Walk parent->child accumulating direction*length. Requires parents to
    precede children, which is also the Metric Tree contract's own rule."""
    pos = {}
    for name, parent, d, ln in nodes:
        if parent is None:
            pos[name] = (0.0, 0.0, 0.0)
            continue
        px, py, pz = pos[parent]
        n = math.sqrt(d[0] ** 2 + d[1] ** 2 + d[2] ** 2) or 1.0
        pos[name] = (px + d[0] / n * ln, py + d[1] / n * ln, pz + d[2] / n * ln)
    return pos


def leaves_of(nodes):
    kids = {}
    for name, parent, _, _ in nodes:
        if parent:
            kids[parent] = kids.get(parent, 0) + 1
    return [n[0] for n in nodes if kids.get(n[0], 0) == 0]


PROJ = {
    "top view":  lambda p: (p[0], -p[2]),
    "side view": lambda p: (p[0], p[1]),
    "front view": lambda p: (p[2], p[1]),
    "isometric": lambda p: ((p[0] - p[2]) * 0.866,
                            p[1] + (p[0] + p[2]) * 0.5),
}


def panel(nodes, pos, proj, title, size=520, pad=0.13):
    f_small, f_tiny = _font(11), _font(10)
    pts = {n: PROJ[proj](pos[n]) for n, _, _, _ in nodes}
    xs = [p[0] for p in pts.values()]; ys = [p[1] for p in pts.values()]
    span = max(max(xs) - min(xs), max(ys) - min(ys)) or 1.0
    s = size * (1 - 2 * pad) / span
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    P = {n: (size / 2 + (p[0] - cx) * s, size / 2 - (p[1] - cy) * s)
         for n, p in pts.items()}

    img = Image.new("RGB", (size, size), BG)
    dr = ImageDraw.Draw(img)
    lf = set(leaves_of(nodes))
    for name, parent, _, ln in nodes:
        if parent is None:
            continue
        dr.line([P[parent], P[name]], fill=C_EDGE, width=2)
        mx, my = ((P[parent][0] + P[name][0]) / 2,
                  (P[parent][1] + P[name][1]) / 2)
        dr.text((mx + 3, my - 5), f"{_edge_name(name)}: {ln}",
                fill=C_LEN, font=f_tiny)
    for name, _, _, _ in nodes:
        x, y = P[name]
        r, col = (4, C_LEAF) if name in lf else (3, C_NODE)
        dr.ellipse([x - r, y - r, x + r, y + r], fill=col)
        dr.text((x + 5, y + 3), name, fill=C_NAME, font=f_tiny)
    dr.rectangle([0, 0, size - 1, size - 1], outline=(170, 170, 170))
    dr.text((7, 6), title, fill=(30, 30, 30), font=f_small)
    return img


def _edge_name(child):
    """Edges are named for the node they ENTER.

    COrigami names an edge for the body part it is ("calf_r: 5"). Here every
    node is already named for its part, so the edge into `hock_l` is `hock_l`
    and reads "the segment ending at the left hock is 4 units". A separate
    part-name table was tried and dropped: mapping child -> part needs
    subject-specific rules (a spider's `knee` is a femur, a frog's is a
    thigh), and a label that is silently wrong is worse than one that is
    merely plain.
    """
    return child


def sheet(subject, variant, nodes, out):
    pos = positions(nodes)
    imgs = [panel(nodes, pos, p, f"{subject} — {variant} — {p}")
            for p in ("top view", "side view", "front view", "isometric")]
    W = sum(i.width for i in imgs)
    s = Image.new("RGB", (W, imgs[0].height + 26), BG)
    for i, im in enumerate(imgs):
        s.paste(im, (i * im.width, 26))
    d = ImageDraw.Draw(s)
    lf = leaves_of(nodes)
    d.text((8, 7), f"{subject}  ({variant})   grid={H.SUBJECTS[subject]['grid']}"
                   f"   {len(nodes)} nodes, {len(lf)} leaves   "
                   f"HAND-AUTHORED, not extracted",
           fill=(20, 20, 20), font=_font(13))
    s.save(out)


def metric_tree(nodes, pairs):
    """Repo Metric Tree format. Lengths scale so the longest EDGE is 0.40,
    matching mesh_to_tree.LONGEST_LIMB_TARGET -- the packing regime the rest
    of this project's trees live in."""
    idx = {n[0]: i for i, n in enumerate(nodes)}
    mx = max(n[3] for n in nodes) or 1
    k = LONGEST_LIMB_TARGET / mx
    tn = [{"id": i,
           "parent_id": (idx[n[1]] if n[1] is not None else None),
           "length": round(n[3] * k, 6)}
          for i, n in enumerate(nodes)]
    return tn, [[idx[a], idx[b]] for a, b in pairs], {i: n[0] for i, n in
                                                      enumerate(nodes)}
