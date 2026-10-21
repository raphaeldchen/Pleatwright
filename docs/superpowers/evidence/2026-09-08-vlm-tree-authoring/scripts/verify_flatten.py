"""Prove chain collapse preserves the metric tree, rather than assuming it.

A metric tree IS its leaf-to-leaf path lengths. If flattening changes even one
of them it is not a representation change, and the dog/packable result below
would be meaningless.
"""
import itertools, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flatten_probe import flatten


def leaf_dists(tn, labels=None):
    par = {n["id"]: n["parent_id"] for n in tn}
    ln = {n["id"]: n["length"] for n in tn}
    kids = {}
    for i, p in par.items():
        if p is not None:
            kids.setdefault(p, []).append(i)
    leaves = [i for i in par if not kids.get(i)]

    def path(i):                      # root-ward chain with cumulative length
        out, acc, c = {}, 0.0, i
        while c is not None:
            out[c] = acc; acc += ln[c] if par[c] is not None else 0.0
            c = par[c]
        return out
    P = {i: path(i) for i in leaves}
    d = {}
    for a, b in itertools.combinations(sorted(leaves), 2):
        common = set(P[a]) & set(P[b])
        d[(a, b)] = round(min(P[a][c] + P[b][c] for c in common), 6)
    return leaves, d


def main():
    b = json.load(open(os.path.expanduser(
        "~/Downloads/photo_meshes/hand_trees/trees.json")))
    worst = 0.0
    for s, e in b["subjects"].items():
        for v in ("faithful", "packable"):
            tn = e[v]["tree_nodes"]; pr = [list(p) for p in e[v]["symmetric_pairs"]]
            lab = e[v]["labels"]
            ftn, _ = flatten(tn, pr)
            # map both to LABEL keys so ids renumbering does not confuse it
            lv0, d0 = leaf_dists(tn)
            keep = [n["id"] for n in tn
                    if n["parent_id"] is None
                    or sum(1 for m in tn if m["parent_id"] == n["id"]) != 1]
            flab = {k: lab[str(o)] for k, o in enumerate(keep)}
            lv1, d1 = leaf_dists(ftn)
            n0 = {tuple(sorted((lab[str(a)], lab[str(c)]))): x
                  for (a, c), x in d0.items()}
            n1 = {tuple(sorted((flab[a], flab[c]))): x for (a, c), x in d1.items()}
            assert set(n0) == set(n1), f"{s}/{v}: leaf SET changed"
            dm = max(abs(n0[k] - n1[k]) for k in n0)
            worst = max(worst, dm)
            print(f"{s:9} {v:9} {len(n0):3d} leaf-pairs   max |delta| = {dm:.2e}")
    print(f"\nworst deviation across all 18 trees: {worst:.3e}")
    print("chain collapse is LOSSLESS" if worst < 1e-9 else "NOT lossless")


if __name__ == "__main__":
    main()
