"""Design section 7, last risk row: fold one re-parented base and LOOK at it.

The risk: a declared pair's two junctions really are ~8% of the mesh apart
along the body, and the re-parent asserts they are one point. Packing is weak
corroboration (a wrong merge should fight the packer; instead it rescued
quadruped) but it is not proof. The honest check is visual.

Renders, per subject, the crease pattern and the flat-folded base for the RAW
tree (reconciliation suppressed) beside the RECONCILED one, plus the measured
tip congruence for every declared pair. SVG so it needs no plotting library.
"""
import json
import os
import sys

#: Run from mcp_harness/ (PYTHONPATH=.:tests). Resolved from the cwd so this
#: reproduces in any checkout or worktree, not just the one it was written in.
HERE = os.environ.get("IDE_HARNESS") or os.getcwd()
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tests"))

import mesh_to_tree as m          # noqa: E402
import pair_reconcile as pr       # noqa: E402
import cp_mirror                  # noqa: E402
from flat_fold import flat_fold   # noqa: E402

PANEL, PAD = 260, 26


def raw_tree(tree, sym):
    """to_metric_tree with BOTH reconciliation steps suppressed."""
    rep, rec = pr.reparent_pairs_to_shared_hub, pr.reconcile_pairs
    pr.reparent_pairs_to_shared_hub = lambda n, p: (
        [dict(x) for x in n], [list(q) for q in p], [])
    pr.reconcile_pairs = lambda n, p, **kw: (
        [dict(x) for x in n], [list(q) for q in p], [])
    try:
        return m.to_metric_tree(tree, sym)
    finally:
        pr.reparent_pairs_to_shared_hub, pr.reconcile_pairs = rep, rec


def compile_base(nodes, pairs):
    """(fold_dict, leaf_locations) or None -- through the REAL SERVE PATH.

    ⚠ NOT a bare HeadlessTreemaker compile. That is attempt-0 for one exact
    node list, and design section 4.9 was wrong twice for exactly this reason:
    measured that way, every one of these subjects "does not pack" while the
    served product packs fine, because the serve runs the rescue ladder
    (order -> placement -> jitter -> stub). Looking at a base the user never
    receives would answer the wrong question.

    Must stay under `if __name__ == "__main__":` -- this spawns workers.
    """
    import server
    out = server.draft_and_compile_full_base(
        [dict(n) for n in nodes], [list(p) for p in pairs])
    if out.startswith("ERROR"):
        return None, out.split("\n")[0][:70]
    fold = json.loads(out)
    # leaf tip coordinates: re-derive from the served fold rather than the
    # engine handle, since the ladder may have served a VARIANT node list.
    import headless_treemaker as ht
    e = ht.HeadlessTreemaker()
    e.init_paper(1.0, 1.0)
    try:
        e.build_tree_from_json(json.dumps(nodes))
        for a, b in pairs:
            e.apply_symmetry(int(a), int(b))
        e.run_scale_optimization()
        locs = {int(n): (x, y) for n, x, y in e.leaf_node_locations()}
    except Exception:
        locs = {}
    return (fold, locs), None


def fit(points, box=PANEL):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    lo_x, hi_x, lo_y, hi_y = min(xs), max(xs), min(ys), max(ys)
    scale = (box - 2 * PAD) / max(hi_x - lo_x, hi_y - lo_y, 1e-9)

    def T(p):                       # y flipped: SVG grows downward
        return (PAD + (p[0] - lo_x) * scale,
                box - PAD - (p[1] - lo_y) * scale)
    return T


_STROKE = {"M": "#c0392b", "V": "#2471a3", "B": "#111111", "F": "#bbbbbb"}


def svg_cp(fold, ox, oy, title):
    V = [v[:2] for v in fold["vertices_coords"]]
    T = fit(V)
    out = [f'<text x="{ox + PANEL/2}" y="{oy + 16}" class="t">{title}</text>']
    for (a, b), kind in zip(fold["edges_vertices"], fold["edges_assignment"]):
        x1, y1 = T(V[a])
        x2, y2 = T(V[b])
        col = _STROKE.get(kind, "#888")
        w = 2.0 if kind == "B" else 1.1
        out.append(f'<line x1="{ox+x1:.2f}" y1="{oy+y1:.2f}" '
                   f'x2="{ox+x2:.2f}" y2="{oy+y2:.2f}" '
                   f'stroke="{col}" stroke-width="{w}"/>')
    return "\n".join(out)


def svg_folded(fold, locs, pairs, ox, oy, title):
    r = flat_fold(fold)
    pts = [p for face in r.folded_vertices for p in face]
    if not pts:
        return f'<text x="{ox+20}" y="{oy+40}" class="t">{title}: no faces</text>'
    T = fit(pts)
    out = [f'<text x="{ox + PANEL/2}" y="{oy + 16}" class="t">{title}</text>']
    for face in r.folded_vertices:
        d = " ".join(f"{ox+T(p)[0]:.2f},{oy+T(p)[1]:.2f}" for p in face)
        out.append(f'<polygon points="{d}" fill="#4a90d9" fill-opacity="0.16" '
                   f'stroke="#1b4f72" stroke-width="0.4" stroke-opacity="0.5"/>')

    # where the paired flap TIPS actually land
    img = {}
    for fi, fverts in enumerate(r.faces):
        for j, v in enumerate(fverts):
            img.setdefault(v, []).append(r.folded_vertices[fi][j])

    def vid(xy, tol=1e-6):
        for i, v in enumerate(fold["vertices_coords"]):
            if abs(v[0] - xy[0]) < tol and abs(v[1] - xy[1]) < tol:
                return i
        return None

    def centre(vs):
        return (sum(p[0] for p in vs) / len(vs), sum(p[1] for p in vs) / len(vs))

    colours = ["#e67e22", "#27ae60", "#8e44ad", "#c0392b", "#16a085"]
    for k, (a, b) in enumerate(pairs):
        col = colours[k % len(colours)]
        for leaf in (a, b):
            i = vid(locs.get(leaf, (9, 9)))
            if i is None or i not in img:
                continue
            cx, cy = T(centre(img[i]))
            out.append(f'<circle cx="{ox+cx:.2f}" cy="{oy+cy:.2f}" r="4.2" '
                       f'fill="none" stroke="{col}" stroke-width="2"/>')
    return "\n".join(out)


def tip_gaps(fold, locs, pairs):
    """(max gap between paired tips, span) in the FOLDED base."""
    import math
    r = flat_fold(fold)
    img = {}
    for fi, fverts in enumerate(r.faces):
        for j, v in enumerate(fverts):
            img.setdefault(v, []).append(r.folded_vertices[fi][j])

    def vid(xy, tol=1e-6):
        for i, v in enumerate(fold["vertices_coords"]):
            if abs(v[0] - xy[0]) < tol and abs(v[1] - xy[1]) < tol:
                return i
        return None

    def centre(vs):
        return (sum(p[0] for p in vs) / len(vs), sum(p[1] for p in vs) / len(vs))

    cs = [centre(v) for v in img.values()]
    span = max(math.dist(p, q) for p in cs for q in cs) if len(cs) > 1 else 1.0
    gaps = []
    for a, b in pairs:
        ia, ib = vid(locs.get(a, (9, 9))), vid(locs.get(b, (9, 9)))
        if ia is None or ib is None or ia not in img or ib not in img:
            continue
        gaps.append(math.dist(centre(img[ia]), centre(img[ib])))
    return (max(gaps) if gaps else None), span


def main():
    want = sys.argv[1:] or ["humanoid", "quadruped", "fish"]
    subjects = [(s, 64, 0.3) for s in want]
    panels, notes, row = [], [], 0

    for subject, voxel, prune in subjects:
        mesh = m.load_mesh(os.path.join(HERE, "fixtures", f"{subject}.glb"),
                           voxel_res=voxel)
        tree = m.simplify_to_tree(m.extract_skeleton(mesh),
                                  prune_fraction=prune)
        sym = m.detect_symmetry(tree, mesh)

        rn, rp = raw_tree(tree, sym)
        cn, cp_pairs = m.to_metric_tree(tree, sym)
        moved = len([e for e in m._last_pair_evidence
                     if e.get("action") == "reparented"])

        arms = [("RAW (as extracted)", rn, rp),
                (f"RECONCILED ({moved} re-parented)", cn, cp_pairs)]
        # One ROW per arm, two panels wide (crease pattern | folded base), so
        # nothing is clipped by a square thumbnailer.
        for label, nodes, pairs in arms:
            y = row * (PANEL + 10)
            got, err = compile_base(nodes, pairs)
            if got is None:
                panels.append(
                    f'<text x="{PANEL}" y="{y+PANEL/2}" class="t">'
                    f'{subject} -- {label}: DID NOT PACK</text>')
                notes.append(f"{subject:10s} {label:34s} did not pack ({err})")
                row += 1
                continue
            fold, locs = got
            v = cp_mirror.mirror_verdict(fold, axis_degrees=45.0)
            panels.append(svg_cp(fold, 0, y,
                                 f"{subject} -- {label}  "
                                 f"(symmetric {v['symmetric']}, "
                                 f"residual {v['residual']:.2e})"))
            panels.append(svg_folded(fold, locs, pairs, PANEL, y,
                                     "folded base"))
            notes.append(
                f"{subject:10s} {label:34s} verts={len(fold['vertices_coords']):3d} "
                f"creases={len(fold['edges_vertices']):3d} "
                f"symmetric={v['symmetric']!s:5s} "
                f"residual={v['residual']:.4e} "
                f"mv_swapped={v['mv_swapped']} "
                f"mv_mismatched={v['mv_mismatched']}")
            row += 1

    w, h = 2 * PANEL, row * (PANEL + 10)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
           f'viewBox="0 0 {w} {h}">'
           f'<style>.t{{font:600 12px sans-serif;fill:#333;'
           f'text-anchor:middle}}</style>'
           f'<rect width="{w}" height="{h}" fill="#ffffff"/>'
           + "\n".join(panels) + "</svg>")
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       f"reparented_{'_'.join(want)}.svg")
    open(out, "w").write(svg)
    print("\n".join(notes))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
