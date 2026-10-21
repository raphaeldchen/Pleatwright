"""Topology or proportions? One variable at a time.

The flattened dog/packable is topologically ISOMORPHIC to body_plans'
`quadruped` -- root, two hubs, two flaps per hub, head on the front hub, tail
on the rear -- and it packs. The flattened cat and horse have the SAME
topology and fail. Same shape, different numbers, so the numbers are the
remaining suspect.

Test: hold each failing tree's topology fixed and replace the lengths with the
template regime (every flap 0.30, the head flap 0.40). If those pack, the
anatomy-faithful PROPORTIONS are what the packer rejects, and the tree
structure this whole exercise produced is sound.
"""
from __future__ import annotations
import json, os, sys

H = "<repo>/mcp_harness"
sys.path.insert(0, H); sys.path.insert(0, os.path.join(H, "tests"))
os.chdir(H)
from runner import compile_tree
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flatten_probe import flatten


def equalize(tn, value=0.30):
    return [{**n, "length": (0.0 if n["parent_id"] is None else value)}
            for n in tn]


def span(tn):
    """Longest root-to-leaf path -- the tree's reach, in the same units."""
    par = {n["id"]: n["parent_id"] for n in tn}
    ln = {n["id"]: n["length"] for n in tn}
    best = 0.0
    for i in par:
        acc, p = 0.0, i
        while par[p] is not None:
            acc += ln[p]; p = par[p]
        best = max(best, acc)
    return round(best, 4)


def ratio(tn):
    """Longest flap / shortest flap, over non-root edges."""
    e = [n["length"] for n in tn if n["parent_id"] is not None]
    return round(max(e) / min(e), 2) if e and min(e) > 0 else None


def main():
    b = json.load(open(os.path.expanduser(
        "~/Downloads/photo_meshes/hand_trees/trees.json")))
    print(f"{'subject':9} {'variant':9} {'span':>6} {'ratio':>6} "
          f"{'flat':>5} {'equalized':>10}")
    rows = []
    for subject, e in b["subjects"].items():
        for var in ("faithful", "packable"):
            tn = e[var]["tree_nodes"]
            pr = [list(p) for p in e[var]["symmetric_pairs"]]
            ftn, fpr = flatten(tn, pr)
            st_flat, _ = compile_tree(ftn, fpr, timeout=60)
            st_eq, _ = compile_tree(equalize(ftn), fpr, timeout=60)
            rec = dict(subject=subject, variant=var, span=span(ftn),
                       ratio=ratio(ftn), flat=st_flat, equalized=st_eq)
            rows.append(rec)
            print(f"{subject:9} {var:9} {rec['span']:>6} {rec['ratio']:>6} "
                  f"{st_flat:>5} {st_eq:>10}", flush=True)
            json.dump(rows, open("/tmp/equalize_probe.json", "w"), indent=2)


if __name__ == "__main__":
    main()
