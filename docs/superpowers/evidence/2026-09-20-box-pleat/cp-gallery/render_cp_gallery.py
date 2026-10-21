"""CP + folded base after pleat reassignment, with the FLIPPED creases marked.

The crease SET is fixed by construction (spec section 2), so v1 and the
repaired labelling differ only in which creases are M and which are V. A
side-by-side of two identical geometries would hide that; instead this marks
every crease whose label moved, so the repair is what you actually see.
"""
from __future__ import annotations
import json, os, sys, time

import flat_fold
from box_pleat.compile import compile_tree
from box_pleat.assign import assign
from box_pleat.emit import to_fold

OUT = sys.argv[1]
RULE6 = os.path.join("..", "docs", "superpowers", "evidence",
                     "2026-09-08-vlm-tree-authoring", "data", "rule6_serve.json")
# fast -> slow, so the early rows land while the big ones are still running
ORDER = ["starfish", "bird", "lizard", "horse", "octopus", "frog",
         "guinea_pig", "dog"]

COL = {"M": "#c62828", "V": "#1565c0", "B": "#111"}
FLIP = "#f9a825"
S = 520


def cp_svg(fold, N, flipped):
    V = fold["vertices_coords"]
    out = [f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='-12 -12 {S+24} {S+24}' "
           f"width='{S+24}' height='{S+24}'>",
           f"<rect x='-12' y='-12' width='{S+24}' height='{S+24}' fill='#fbfaf7'/>"]
    step = S / N
    g = max(1, N // 40)
    for i in range(0, N + 1, g):
        p = i * step
        out.append(f"<line x1='{p:.2f}' y1='0' x2='{p:.2f}' y2='{S}' stroke='#e3ded2' stroke-width='0.4'/>")
        out.append(f"<line x1='0' y1='{p:.2f}' x2='{S}' y2='{p:.2f}' stroke='#e3ded2' stroke-width='0.4'/>")
    # flip halos first, so the crease itself draws on top of its marker
    for i, (a, b) in enumerate(fold["edges_vertices"]):
        if i not in flipped:
            continue
        ax, ay = V[a]; bx, by = V[b]
        out.append(f"<line x1='{ax*S:.2f}' y1='{(1-ay)*S:.2f}' x2='{bx*S:.2f}' "
                   f"y2='{(1-by)*S:.2f}' stroke='{FLIP}' stroke-width='4.5' "
                   f"stroke-opacity='0.85' stroke-linecap='round'/>")
    for i, ((a, b), lab) in enumerate(zip(fold["edges_vertices"], fold["edges_assignment"])):
        ax, ay = V[a]; bx, by = V[b]
        x1, y1, x2, y2 = ax * S, (1 - ay) * S, bx * S, (1 - by) * S
        if lab == "B":
            w, dash = 2.0, ""
        else:
            w = 1.0
            dash = " stroke-dasharray='5 3'" if lab == "V" else ""
        out.append(f"<line x1='{x1:.2f}' y1='{y1:.2f}' x2='{x2:.2f}' y2='{y2:.2f}' "
                   f"stroke='{COL.get(lab,'#888')}' stroke-width='{w}'{dash}/>")
    out.append("</svg>")
    return "\n".join(out)


def base_svg(ff):
    xs = [p[0] for F in ff.folded_vertices for p in F]
    ys = [p[1] for F in ff.folded_vertices for p in F]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    w, h = max(x1 - x0, 1e-9), max(y1 - y0, 1e-9)
    k = (S - 40) / max(w, h)
    ox, oy = 20 + (S - 40 - w * k) / 2, 20 + (S - 40 - h * k) / 2

    def pt(p):
        return f"{ox + (p[0]-x0)*k:.2f},{oy + (h - (p[1]-y0))*k:.2f}"

    out = [f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 {S} {S}' width='{S}' height='{S}'>",
           f"<rect x='0' y='0' width='{S}' height='{S}' fill='#fbfaf7'/>"]
    for F in ff.folded_vertices:
        out.append(f"<polygon points='{' '.join(pt(p) for p in F)}' fill='#3d5a80' "
                   f"fill-opacity='0.055' stroke='#3d5a80' stroke-opacity='0.5' stroke-width='0.5'/>")
    out.append("</svg>")
    return "\n".join(out)


def main():
    os.makedirs(OUT, exist_ok=True)
    entries = {e["subject"]: e for e in json.load(open(RULE6))}
    made = []
    for s in ORDER:
        e = entries[s]
        t0 = time.time()
        res = compile_tree(e["requested"], e["pairs"])
        if res.stage_reached != "emit":
            print(f"{s:11s} stop@{res.stage_reached} {res.failure}", flush=True)
            continue
        new = res.fold
        # v1's labelling: the same solver with the global check switched off
        v1a = assign(res.layout, res.ridges, res.boundary_ridges, res.contours)
        v1 = to_fold(res.layout, v1a)
        same_geom = (new["vertices_coords"] == v1["vertices_coords"]
                     and new["edges_vertices"] == v1["edges_vertices"])
        flipped = set()
        if same_geom:
            flipped = {i for i, (a, b) in enumerate(zip(new["edges_assignment"],
                                                        v1["edges_assignment"]))
                       if a != b}
        ff = flat_fold.flat_fold(new)
        N = res.layout.N
        open(os.path.join(OUT, f"{s}-cp.svg"), "w").write(cp_svg(new, N, flipped))
        open(os.path.join(OUT, f"{s}-base.svg"), "w").write(base_svg(ff))
        nm = sum(1 for a in new["edges_assignment"] if a == "M")
        nv = sum(1 for a in new["edges_assignment"] if a == "V")
        row = dict(subject=s, N=N, creases=nm + nv, M=nm, V=nv, flipped=len(flipped),
                   tries=res.layers_tried, faces=len(ff.faces),
                   same_geom=same_geom, closure=ff.closure.max_error,
                   secs=round(time.time() - t0, 1))
        made.append(row)
        json.dump(made, open(os.path.join(OUT, "index.json"), "w"), indent=1)
        print(f"{s:11s} N={N:3d} creases={nm+nv:5d} flipped={len(flipped):5d} "
              f"tries={res.layers_tried:3d} geom_same={same_geom} {row['secs']}s",
              flush=True)


main()
