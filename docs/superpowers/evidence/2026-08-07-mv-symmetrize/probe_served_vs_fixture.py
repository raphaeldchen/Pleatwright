"""Post-S6: what does the serve ACTUALLY produce for bird and humanoid, and
is it my fixture?  (Guarded -- the serve spawns workers.)"""
import json, os, sys
_H = "<repo>/mcp_harness"
sys.path.insert(0, _H); sys.path.insert(0, os.path.join(_H, "tests"))
FIX = os.path.join(_H, "tests", "fixtures", "mv_symmetrize")

def main():
    import cp_audit, cp_mirror, mv_repair, mv_symmetrize, order_rank, server
    from mesh_to_tree import auto_mesh_to_metric_tree
    for subject, fixture in (("bird", "mesh-bird__seeded_3"),
                             ("humanoid", "mesh-humanoid__seeded_1")):
        res = auto_mesh_to_metric_tree(os.path.join(_H, "fixtures",
                                                    f"{subject}.glb"))
        out = server.draft_and_compile_full_base(res.nodes, res.pairs)
        if out.startswith("ERROR"):
            print(f"{subject}: DID NOT SERVE: {out[:80]}"); continue
        served = json.loads(out)
        fx = json.load(open(os.path.join(FIX, fixture + ".fold")))
        sfp, xfp = (mv_repair.fold_fingerprint(served),
                    mv_repair.fold_fingerprint(fx))
        sa = cp_audit._geometry_frame(served)["edges_assignment"]
        xa = cp_audit._geometry_frame(fx)["edges_assignment"]
        v = cp_mirror.mirror_verdict(served, axis_degrees=45.0)
        title = str(served.get("frame_title", ""))
        print(f"=== {subject}")
        print(f"  served V{len(cp_audit._geometry_frame(served)['vertices_coords'])}"
              f" E{len(cp_audit._geometry_frame(served)['edges_vertices'])}"
              f"  fingerprint {sfp}")
        print(f"  fixture({fixture}) fingerprint {xfp}")
        print(f"  GEOMETRY MATCHES FIXTURE: {sfp == xfp}"
              f"   assignments match: {sa == xa}")
        print(f"  rank marker present: {order_rank.RANK_MARKER in title}")
        print(f"  is_bijection {v['is_bijection']}  residual {v['residual']}"
              f"  mv_swapped {v['mv_swapped']}  symmetric {v['symmetric']}")
        r = mv_symmetrize.search(served, lint=False)
        print(f"  ON THE SERVED FOLD -> refusal={r.refusal} "
              f"orbits={len(r.space.orbits) if r.space else 0} "
              f"({r.space.n_swapped}/{r.space.n_preserved}/{r.space.n_fixed})"
              if r.space else f"  ON THE SERVED FOLD -> refusal={r.refusal}")
        if r.space:
            print(f"     maekawa {r.n_maekawa_clean} audit {r.n_audit_clean} "
                  f"layer {r.n_layer_consistent}")

if __name__ == "__main__":
    main()
