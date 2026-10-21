"""Draw a model-authored metric tree.

The model returned no direction vectors -- only (parent, length) -- so there is
no 3-D pose to project. Drawing one would be inventing information the model
never supplied. Instead: a radial metric-tree diagram where the RADIUS of a
node is its true cumulative distance from the root, so every edge is drawn at
its authored length and the picture states exactly what the tree states.
"""
import json, math, os, sys
from PIL import Image, ImageDraw, ImageFont


def _font(sz=11):
    try:
        return ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", sz)
    except Exception:
        return ImageFont.load_default()


def layout(nodes, labels):
    kids = {}
    for n in nodes:
        if n["parent_id"] is not None:
            kids.setdefault(n["parent_id"], []).append(n["id"])
    nleaf = {}

    def count(i):
        if not kids.get(i):
            nleaf[i] = 1
        else:
            nleaf[i] = sum(count(c) for c in kids[i])
        return nleaf[i]
    root = next(n["id"] for n in nodes if n["parent_id"] is None)
    count(root)
    L = {n["id"]: n["length"] for n in nodes}
    pos, ang = {}, {}

    def place(i, a0, a1, r):
        a = (a0 + a1) / 2
        ang[i] = a
        pos[i] = (r * math.cos(a), r * math.sin(a))
        s = a0
        for c in kids.get(i, []):
            w = (a1 - a0) * nleaf[c] / nleaf[i]
            place(c, s, s + w, r + L[c])
            s += w
    place(root, -math.pi, math.pi, 0.0)
    return pos, kids


def draw(nodes, labels, grid, out, title, size=760):
    pos, kids = layout(nodes, labels)
    xs = [p[0] for p in pos.values()]; ys = [p[1] for p in pos.values()]
    sp = max(max(xs) - min(xs), max(ys) - min(ys)) or 1.0
    s = size * 0.72 / sp
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    P = {i: (size / 2 + (p[0] - cx) * s, size / 2 - (p[1] - cy) * s)
         for i, p in pos.items()}
    img = Image.new("RGB", (size, size), (253, 253, 251))
    dr = ImageDraw.Draw(img)
    ft, fs = _font(10), _font(13)
    for n in nodes:
        if n["parent_id"] is None:
            continue
        a, b = P[n["parent_id"]], P[n["id"]]
        dr.line([a, b], fill=(40, 40, 40), width=2)
        g = grid.get(labels[str(n["id"])], "")
        dr.text(((a[0] + b[0]) / 2 + 3, (a[1] + b[1]) / 2 - 5), str(g),
                fill=(20, 120, 40), font=ft)
    for n in nodes:
        i = n["id"]; x, y = P[i]
        leaf = not kids.get(i)
        r, col = (5, (40, 60, 200)) if leaf else (3, (200, 40, 40))
        dr.ellipse([x - r, y - r, x + r, y + r], fill=col)
        dr.text((x + 6, y + 3), labels[str(i)], fill=(190, 30, 30), font=ft)
    dr.text((8, 8), title, fill=(20, 20, 20), font=fs)
    dr.text((8, size - 18),
            "radius = true cumulative distance from root; green = authored "
            "grid length", fill=(90, 90, 90), font=ft)
    img.save(out)


if __name__ == "__main__":
    d = json.load(open(os.path.expanduser(
        "~/Downloads/photo_meshes/llm_trees/llm_trees.json")))
    out = os.path.expanduser("~/Downloads/photo_meshes/llm_trees/sheets")
    os.makedirs(out, exist_ok=True)
    for subj, v in d.items():
        bad = " CONTRACT ERRORS" if v["contract_errors"] else ""
        draw(v["tree_nodes"], v["labels"], v["length_grid"],
             f"{out}/{subj}.png",
             f"{subj} — LLM-authored (arm A) — {v['leaf_count']} leaves "
             f"(expected {v['expected_feature_count']}){bad}")
        print("rendered", subj)
