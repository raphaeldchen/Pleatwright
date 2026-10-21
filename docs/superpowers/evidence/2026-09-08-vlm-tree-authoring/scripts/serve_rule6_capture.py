"""Run the finished pipeline on the rule-6 corpus and capture BOTH trees.

The authored tree and the tree the backend actually served come straight from
`server._LAST_SERVE`, which carries `requested` and `served` side by side. They
are not re-derived here: re-deriving would mean re-implementing the ladder's
barrier, and a probe that re-implements production is how this project has
measured the wrong object before (F1's 512-cell probe, memory
`extraction-geometry-merged-and-measured`).

⚠ WHAT "EDITED FOR PACKABILITY" ACTUALLY MEANS, PER STAGE. Most rescues change
NOTHING a picture can show:

    none        no rescue -- the authored tree packed as written
    order       the node LIST ORDER changed and the geometry did not. Every id
                keeps its own parent and its own length; the engine seeds
                initial flap placement by list position, so this hands the
                packer a different starting basin for an identical tree.
    placement   initial x/y SEEDS added; lengths and topology untouched.
    flatten     pass-through joints merged away. The only stage in this corpus
                that changes what a stick figure looks like.
"""
from __future__ import annotations
import json, os, sys, time

R = "<repo>"
H = f"{R}/mcp_harness"
E = f"{R}/docs/superpowers/evidence/2026-09-08-vlm-tree-authoring"
sys.path.insert(0, f"{E}/scripts"); sys.path.insert(0, H); sys.path.insert(0, f"{H}/tests")
os.chdir(H)
import server, mesh_to_tree as m2t
import loop_lib as L, hand_trees_build as B

ORDER = ["dog","cat","horse","rabbit","guinea_pig","elephant","lizard","frog","bird",
         "bat","dolphin","starfish","octopus","crab","spider","scorpion","ant"]


def main():
    D = f"{E}/data"
    raw = {r["subject"]: r["tree"]
           for r in json.load(open(f"{D}/rule6_raw.json")) if r.get("tree")}
    out, t0 = [], time.time()
    for s in ORDER:
        t = raw[s]
        nodes = L.to_tuples(t); lset = set(B.leaves_of(nodes))
        keep = [(a, b) for p in (t.get("pairs") or []) if len(p) == 2
                for a, b in [p] if a in lset and b in lset]
        tn, sp, names = B.metric_tree(nodes, keep)

        server._LAST_SERVE.clear()
        fold = server.draft_and_compile_full_base(tn, sp)
        ok = isinstance(fold, str) and not fold.startswith("ERROR:")
        ls = dict(server._LAST_SERVE)
        rec = {"subject": s, "served": ok,
               "stage": (m2t.served_stage(fold) if ok else None),
               "requested": ls.get("requested") if ok else [dict(n) for n in tn],
               "served_nodes": ls.get("served") if ok else None,
               "pairs": sp, "names": {str(k): v for k, v in names.items()},
               "directions": {n[0]: n[2] for n in nodes},
               "error_head": (None if ok else str(fold)[:200])}
        req, srv = rec["requested"] or [], rec["served_nodes"] or []
        rec["n_requested"], rec["n_served"] = len(req), len(srv)
        rec["order_changed"] = ([n["id"] for n in req] != [n["id"] for n in srv]
                                if srv else None)
        rec["geometry_changed"] = (
            sorted((n["id"], n["parent_id"], round(float(n["length"]), 6)) for n in req)
            != sorted((n["id"], n["parent_id"], round(float(n["length"]), 6)) for n in srv)
            if srv else None)
        out.append(rec)
        print(f"  {s:12}{'SERVED' if ok else 'not served':>12}  stage="
              f"{str(rec['stage']):>10}  nodes {rec['n_requested']}->{rec['n_served']}"
              f"  order_changed={rec['order_changed']}"
              f"  geometry_changed={rec['geometry_changed']}", flush=True)

    json.dump(out, open(f"{D}/rule6_serve.json", "w"), indent=1)
    n = sum(1 for r in out if r["served"])
    print(f"\nSERVED {n}/17")
    import collections
    print("stages:", dict(collections.Counter(
        (r["stage"] or "exact") for r in out if r["served"])))
    print("geometry actually changed:",
          [r["subject"] for r in out if r["geometry_changed"]])
    print(f"elapsed {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
