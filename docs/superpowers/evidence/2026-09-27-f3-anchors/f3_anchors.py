"""Can COrigami F.3 anchor on our ridge geometry at all?

F.3 assigns ridges deterministically: "Y-shape anchors; X-shape same, parallel
opposite, perpendicular same" (as recorded in
`docs/superpowers/specs/2026-09-24-dense-pleats-design.md` section 3). So it
needs ANCHORS to start from and a connected structure to propagate along.

WHY THIS IS MEASURED RULE-AGNOSTICALLY. Phase A
(`../2026-09-27-pleat-filter/`) died because a predicate from the same appendix
was measured at the wrong granularity, and because its outcome turned out to
depend entirely on a structural mismatch between COrigami's geometry and ours.
The decisive question here is therefore posed so that it does NOT depend on how
F.3's propagation rules are read:

    A ridge variable in a connected component of the ridge graph that contains
    NO anchor vertex cannot be determined by ANY propagation rule, because no
    information ever reaches it.

That is a rule-independent UPPER BOUND on F.3's reach. If it is small, F.3
cannot determine our ridges no matter how its rules are interpreted, and no
amount of care reading the paper changes that.

WHAT IS COUNTED. Ridge pieces are unit segments; the ridge GRAPH here has one
node per ridge piece and an edge between two ridge pieces sharing a vertex.
Components are that graph's connected components.

  * `y_vertices` -- vertices with exactly 3 incident ridge pieces (Y-shape).
  * `x_vertices` -- vertices with 4 or more (X-shape).
  * `anchored_components` -- components containing at least one Y or X vertex.
  * `reach_pct` -- ridge pieces in anchored components, as a percentage. THE
    HEADLINE: F.3 cannot exceed this, under any reading of its rules.

Ridge VARIABLES (what `assign` actually solves) are fewer than ridge pieces,
because run-merging and mirror-merging collapse several pieces onto one
variable. That collapse can only ever HELP F.3 -- fewer things to determine,
and a merge can carry information across a component boundary -- so the
component-level figure is reported as the primary bound and the variable count
alongside it for scale. A merge-aware figure would be larger; this one cannot
be argued down.

Needs only a SPARSE compile (ridges do not depend on the labelling mode), so
unlike the dense measurements this reaches `octopus` and `dog` too.

Run from mcp_harness:
  PYTHONPATH=. ../.venv/bin/python3 -u \
      ../docs/superpowers/evidence/2026-09-27-f3-anchors/f3_anchors.py \
      ../docs/superpowers/evidence/2026-09-27-f3-anchors/f3-anchors.json
"""
import collections
import json
import os
import sys
import time

from box_pleat.compile import compile_tree

OUT = sys.argv[1]
RULE6 = os.path.join("..", "docs", "superpowers", "evidence",
                     "2026-09-08-vlm-tree-authoring", "data", "rule6_serve.json")
ORDER = ["starfish", "lizard", "frog", "horse", "bird", "guinea_pig",
         "octopus", "dog"]


def main():
    entries = {e["subject"]: e for e in json.load(open(RULE6))}
    rows = []
    for s in ORDER:
        row = {"subject": s}
        t0 = time.time()
        res = compile_tree(entries[s]["requested"], entries[s]["pairs"])
        row["sparse_compile_secs"] = round(time.time() - t0, 1)
        if res.stage_reached != "emit":
            row["error"] = f"sparse compile stopped@{res.stage_reached}"
            rows.append(row); json.dump(rows, open(OUT, "w"), indent=1)
            print(f"{s}: SPARSE STOP", flush=True); continue
        pieces = res.assignment.pieces
        row["N"] = res.layout.N

        at_vertex = collections.defaultdict(list)
        for i, p in enumerate(pieces):
            at_vertex[p.a].append(i)
            at_vertex[p.b].append(i)

        ridges = [i for i, p in enumerate(pieces) if p.role == "ridge"]
        row["ridge_pieces"] = len(ridges)
        ridgeset = set(ridges)

        deg = collections.Counter()
        y_vertices, x_vertices = [], []
        for v, ids in at_vertex.items():
            n = sum(1 for i in ids if i in ridgeset)
            if n:
                deg[n] += 1
            if n == 3:
                y_vertices.append(v)
            elif n >= 4:
                x_vertices.append(v)
        row["ridge_vertex_degree_hist"] = dict(sorted(deg.items()))
        row["y_vertices"] = len(y_vertices)
        row["x_vertices"] = len(x_vertices)

        # connected components of the ridge graph
        parent = {i: i for i in ridges}

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        for v, ids in at_vertex.items():
            rs = [i for i in ids if i in ridgeset]
            for j in rs[1:]:
                a, b = find(rs[0]), find(j)
                if a != b:
                    parent[a] = b
        comps = collections.defaultdict(list)
        for i in ridges:
            comps[find(i)].append(i)
        comps = list(comps.values())
        row["ridge_components"] = len(comps)
        row["component_size_hist"] = dict(
            sorted(collections.Counter(len(c) for c in comps).items()))

        anchor_vertices = set(y_vertices) | set(x_vertices)
        anchored = [c for c in comps
                    if any(v in anchor_vertices
                           for i in c for v in (pieces[i].a, pieces[i].b))]
        row["anchored_components"] = len(anchored)
        reached = sum(len(c) for c in anchored)
        row["ridge_pieces_in_anchored_components"] = reached
        row["reach_pct"] = (round(100 * reached / len(ridges), 2)
                            if ridges else None)
        rows.append(row)
        json.dump(rows, open(OUT, "w"), indent=1)
        print(f"{s:11} N={row['N']:3} ridge_pieces={len(ridges):5} "
              f"Y={row['y_vertices']:3} X={row['x_vertices']:3} "
              f"components={row['ridge_components']:4} "
              f"anchored={row['anchored_components']:4} "
              f"REACH={row['reach_pct']}%", flush=True)
    json.dump(rows, open(OUT, "w"), indent=1)
    print("done", flush=True)


main()
