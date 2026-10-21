"""PRE-TEST: does TREE-SIDE narrowing (Lang, TreeMkr40 p.35) make a base
anatomy-legible?

Mechanism. In the circle-river method a leaf's circle radius equals its edge
length, so a 0.3 leg gets a 0.3-radius circle and lands as a wedge about as
wide as it is long. Subdividing the limb into k segments of 0.3/k leaves the
limb the same LENGTH but drops the leaf circle to 0.3/k -- a narrower tip --
and turns the proximal segments into rivers.

No new geometry code, no C++, no serial-file claim: this is purely a Metric
Tree edit, which is exactly where CLAUDE.md section 2 says the AI may work.
Compiled through server.draft_and_compile_full_base -- the REAL serve path
with the rescue ladder.

Real script file with a __main__ guard: the serve path uses spawn workers.
"""
import json
import os
import sys

HERE = "<repo>/mcp_harness"
sys.path.insert(0, HERE)
OUT = os.path.dirname(os.path.abspath(__file__))

LEAVES = {3: "front_leg_L", 4: "front_leg_R", 5: "rear_leg_L",
          6: "rear_leg_R", 7: "head", 8: "tail"}
MIRROR = [(3, 4), (5, 6)]


def subdivide(nodes, k):
    """Split every LEAF limb into k equal segments. Preserves list order:
    each original node is emitted in place, a leaf as its whole chain.
    Returns (new_nodes, pairs, leaf_id_of_original)."""
    if k == 1:
        pairs = [[a, b] for a, b in MIRROR]
        return [dict(n) for n in nodes], pairs, {i: i for i in LEAVES}

    out, nxt = [], max(n["id"] for n in nodes) + 1
    chain = {}                      # original leaf id -> [new ids in order]
    idmap = {}                      # original id -> new id (non-leaf)
    for n in nodes:
        if n["id"] not in LEAVES:
            out.append(dict(n))
            idmap[n["id"]] = n["id"]
            continue
        seg = n["length"] / k
        parent = idmap.get(n["parent_id"], n["parent_id"])
        ids = []
        for j in range(k):
            # the LAST segment keeps the original id so anatomy labels and
            # symmetric-pair remapping stay readable
            nid = n["id"] if j == k - 1 else nxt
            if j != k - 1:
                nxt += 1
            out.append({"id": nid, "parent_id": parent, "length": seg})
            ids.append(nid)
            parent = nid
        chain[n["id"]] = ids

    # pair EVERY corresponding segment of mirrored limbs, not just the tips:
    # memory records that an unequal-length declared pair is ~unpackable and
    # that pairing genuine pairs HELPS (equal-paired 42.5% vs unpaired 30.0%).
    pairs = []
    for a, b in MIRROR:
        for ia, ib in zip(chain[a], chain[b]):
            pairs.append([ia, ib])
    return out, pairs, {i: chain[i][-1] for i in LEAVES}


def main():
    import server
    import body_plans
    import square_complete
    import shaping
    import pose_base
    import paper_coverage

    spec = body_plans.describe("quadruped", 1.0)
    base_nodes = spec["tree_nodes"]

    variants = []
    for k in (1, 2, 3):
        nodes, pairs, _ = subdivide(base_nodes, k)
        label = ("baseline (no subdivision)" if k == 1
                 else f"limbs split into {k} segments (leaf circle /{k})")
        print(f"\n=== k={k}: {label}")
        print(f"    {len(nodes)} nodes, {len(pairs)} pairs")
        fold_str = server.draft_and_compile_full_base(nodes, pairs)
        if fold_str.startswith("ERROR"):
            print(f"    COMPILE FAILED: {fold_str[:220]}")
            variants.append({"k": k, "label": label, "ok": False,
                             "error": fold_str[:400]})
            continue
        raw = json.loads(fold_str)
        cov = paper_coverage.hull_coverage(raw)
        sq = square_complete.complete_square(raw, 1.0, 1.0)
        served = shaping.apply_display_ops(sq, [], raw=raw)
        tips = pose_base.candidate_tips(served)
        print(f"    OK  {len(raw['vertices_coords'])}v  "
              f"coverage={cov['coverage']:.4f}  served_tips={len(tips)}")
        variants.append({"k": k, "label": label, "ok": True,
                         "n_nodes": len(nodes),
                         "coverage": cov["coverage"],
                         "n_tips": len(tips), "served": served})

    good = [v for v in variants if v.get("ok")]
    if not good:
        print("\nno variant compiled -- pre-test cannot run")
        return 1

    import sim_capture
    caps = []
    with sim_capture.SimSession() as sim:
        for v in good:
            log = []
            print(f"capturing k={v['k']} ...", flush=True)
            try:
                cap, disp = sim_capture.capture_checked(sim, v["served"], log,
                                                        attempts=3)
            except Exception as exc:                   # noqa: BLE001
                print(f"  k={v['k']} FAILED: {exc}", flush=True)
                continue
            print(f"  k={v['k']} ok maxDisp={disp:.4f}", flush=True)
            caps.append({"k": v["k"], "label": v["label"], "ok": True,
                         "coverage": v["coverage"], "n_tips": v["n_tips"],
                         "maxDisplacement": disp,
                         "vertices_coords": cap.get("vertices_coords"),
                         "faces_vertices": cap.get("faces_vertices"),
                         "flat_coords": cap.get("flat_coords")})

    with open(os.path.join(OUT, "captures_narrow.json"), "w") as fh:
        json.dump({"captures": caps,
                   "summary": [{kk: v[kk] for kk in
                                ("k", "label", "ok", "coverage", "n_tips")}
                               for v in good]}, fh)
    print(f"\nwrote captures_narrow.json ({len(caps)} captures)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
