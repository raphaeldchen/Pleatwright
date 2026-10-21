"""Is COrigami F.2's alternation achievable on our geometry?

F.2 assigns adjacent pleat paths alternating M/V. That is a 2-colouring, so
it is possible iff the path-adjacency graph is bipartite. This probe answers
that per subject, using the EXISTING sparse pleat_paths grouping.

That reading is NOT a lower bound on the dense one. Under the
nearest-neighbour-on-a-lane adjacency this module's `interleave.adjacency`
implements, merging two sparse groups into one dense group REMOVES the edge
between them (a group is never adjacent to itself) and changes which lane
entries are consecutive-and-differing for every other pair too -- so denser
grouping does not merely add edges, and can just as well destroy them or
flip which paths are neighbours. Sparse and dense grouping give different,
non-nested adjacency graphs: a sparse reading here neither bounds nor
predicts the dense one, and F.2's gate is only meaningful when run on the
dense grouping.

Run from mcp_harness:
  PYTHONPATH=. ../.venv/bin/python3 -u ../docs/superpowers/evidence/2026-09-24-dense-pleats/bipartite_probe.py OUT.json
"""
import json
import os
import sys
import time

from box_pleat import assign as A
from box_pleat import interleave
from box_pleat.compile import compile_tree

OUT = sys.argv[1]
RULE6 = os.path.join("..", "docs", "superpowers", "evidence",
                     "2026-09-08-vlm-tree-authoring", "data", "rule6_serve.json")
ORDER = ["starfish", "bird", "lizard", "horse", "octopus", "frog",
         "guinea_pig", "dog"]


def main():
    entries = {e["subject"]: e for e in json.load(open(RULE6))}
    rows = []
    for s in ORDER:
        t0 = time.time()
        res = compile_tree(entries[s]["requested"], entries[s]["pairs"])
        if res.stage_reached != "emit":
            print(f"{s:11s} stop@{res.stage_reached}", flush=True)
            continue
        N, pieces = res.layout.N, res.assignment.pieces
        face_list = A.faces(N, pieces)
        prof, face_of = A.profiles(N, pieces, res.contours, face_list)
        _, _, _, probe = A.initial_readings(N, pieces, res.contours, prof,
                                            face_of, dense=True)
        groups = A.pleat_paths(pieces, probe, dense=True)
        adj = interleave.adjacency(pieces, groups)
        col, odd = interleave.colour(pieces, groups)
        edges = sum(len(v) for v in adj.values()) // 2
        row = dict(subject=s, N=N, paths=len(groups), adjacency_edges=edges,
                   isolated=sum(1 for v in adj.values() if not v),
                   bipartite=odd is None,
                   odd_cycle_len=(len(odd.groups) if odd else 0),
                   secs=round(time.time() - t0, 1))
        rows.append(row)
        json.dump(rows, open(OUT, "w"), indent=1)
        print(f"{s:11s} N={N:3d} paths={len(groups):5d} edges={edges:6d} "
              f"isolated={row['isolated']:5d} bipartite={row['bipartite']} "
              f"odd_len={row['odd_cycle_len']:3d} {row['secs']}s", flush=True)


main()
