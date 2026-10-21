"""Design section 4.9, third attempt: measure which (VARIANT, SCALE) pairs pack.

The section has been wrong twice, both times by treating the clamp as a
property of the TREE. It is a property of the tree crossed with the LADDER'S
SEARCH: the sweep's "packs" numbers all came from draft_and_compile_full_base,
so the clamp only ever rescued in COMPOSITION with order/placement variants --
all four rescues fail at attempt-0 even clamped.

So this measures the grid directly, with a bare engine compile per cell (that
IS attempt-0 for the given node list), enumerating variants explicitly instead
of letting the ladder do it. No conclusion about where a rung goes is drawn
here; the grid is the input to that decision.

Subjects: the four insect v64 configurations 4.9 claims as its rescues.
"""
import json
import os
import sys

#: Run from mcp_harness/ (PYTHONPATH=.:tests). Resolved from the cwd so this
#: reproduces in any checkout or worktree, not just the one it was written in.
HERE = os.environ.get("IDE_HARNESS") or os.getcwd()
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tests"))
os.chdir(HERE)

import mesh_to_tree as m           # noqa: E402
import rescue_ladder as rl         # noqa: E402

CONFIGS = [("insect", 64, p) for p in (0.3, 0.4, 0.5, 0.6)]
#: 1.00 is the unclamped tree. The rest walk down toward (and past) the clamp
#: factor, which is recomputed per tree as LONGEST_LIMB_TARGET / longest.
SCALES = [1.00, 0.98, 0.96, 0.94, 0.92, 0.90, 0.85, 0.80]


def scaled(nodes, s):
    return [dict(n, length=round((n.get("length") or 0.0) * s, 9))
            for n in nodes]


def packs(nodes, pairs):
    """True iff this EXACT node list compiles -- i.e. attempt-0 for it."""
    import headless_treemaker as ht
    e = ht.HeadlessTreemaker()
    e.init_paper(1.0, 1.0)
    try:
        e.build_tree_from_json(json.dumps(nodes))
        for a, b in pairs:
            e.apply_symmetry(int(a), int(b))
        e.run_scale_optimization()
        e.build_and_export()
        return True, None
    except Exception as exc:
        return False, str(exc)[:40]


def families(nodes, pairs):
    """[(family, variant_name, nodes)] -- exact plus every ladder variant."""
    out = [("exact", "caller", nodes)]
    for name, cand in rl.order_variants(nodes, pairs):
        out.append(("order", name, cand))
    for name, _ord, cand in rl.placement_variants(nodes, pairs):
        out.append(("placement", name, cand))
    return out


def main():
    rows = []
    for subject, voxel, prune in CONFIGS:
        mesh = m.load_mesh(os.path.join(HERE, "fixtures", f"{subject}.glb"),
                           voxel_res=voxel)
        tree = m.simplify_to_tree(m.extract_skeleton(mesh),
                                  prune_fraction=prune)
        sym = m.detect_symmetry(tree, mesh)
        nodes, pairs = m.to_metric_tree(tree, sym)
        longest = max((n.get("length") or 0.0) for n in nodes)
        clamp = m.LONGEST_LIMB_TARGET / longest if longest else 1.0
        scales = sorted({round(s, 4) for s in SCALES} | {round(clamp, 4)},
                        reverse=True)
        print(f"\n=== {subject} v{voxel} p{prune}  longest={longest:.4f}  "
              f"clamp_factor={clamp:.4f} ===", flush=True)
        for s in scales:
            sn = scaled(nodes, s)
            cells = []
            for fam, name, cand in families(sn, pairs):
                ok, err = packs(cand, pairs)
                cells.append((fam, name, ok, err))
                rows.append({"subject": subject, "voxel": voxel,
                             "prune": prune, "scale": s, "family": fam,
                             "variant": name, "packs": ok,
                             "is_clamp": abs(s - round(clamp, 4)) < 1e-9})
            wins = [f"{f}:{n}" for f, n, ok, _ in cells if ok]
            tag = "  <-- CLAMP" if abs(s - round(clamp, 4)) < 1e-9 else ""
            print(f"  scale {s:.4f}: {len(wins)}/{len(cells)} pack"
                  f"   {', '.join(wins) if wins else '(none)'}{tag}",
                  flush=True)

    dest = sys.argv[1] if len(sys.argv) > 1 else "scale_grid.json"
    json.dump(rows, open(dest, "w"), indent=1)

    print("\n=== summary: does any scale rescue at attempt-0 (exact only)? ===")
    for subject, voxel, prune in CONFIGS:
        ex = [r for r in rows if r["prune"] == prune and r["family"] == "exact"]
        won = [r["scale"] for r in ex if r["packs"]]
        print(f"  v{voxel} p{prune}: exact packs at scales {won or 'NONE'}")
    print("\n=== summary: cheapest family that packs, per (config, scale) ===")
    for subject, voxel, prune in CONFIGS:
        for s in sorted({r["scale"] for r in rows if r["prune"] == prune},
                        reverse=True):
            hit = [r for r in rows
                   if r["prune"] == prune and r["scale"] == s and r["packs"]]
            fams = sorted({r["family"] for r in hit})
            if fams:
                print(f"  v{voxel} p{prune} scale {s:.4f}: {fams}")
    print(f"\nwrote {dest}")


if __name__ == "__main__":
    main()
