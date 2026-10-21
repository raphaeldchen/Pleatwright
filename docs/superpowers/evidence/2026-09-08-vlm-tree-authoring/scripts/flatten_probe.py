"""Is the multi-segment limb chain what the engine is rejecting?

A metric tree's semantics are the LEAF-TO-LEAF PATH LENGTHS. A degree-2
internal node adds nothing to that: `thigh 4 -> knee -> shank 4 -> hock ->
foot 3` and a single `leg 11` are the SAME metric tree. So collapsing every
degree-2 chain is LOSSLESS -- it cannot change a single leaf-to-leaf distance.

That makes it a clean controlled experiment. If the flattened trees pack and
the segmented ones do not, the anatomy is innocent and the joint chain is the
whole cause. If both fail, the chains were never the problem.

Also tried: re-rooting at each branch node, because tmTree::GetRootNode()
returns mNodes.front() and the engine's own suggested_lever names root
placement.
"""
from __future__ import annotations
import json, os, sys

H = "<repo>/mcp_harness"
sys.path.insert(0, H); sys.path.insert(0, os.path.join(H, "tests"))
os.chdir(H)
from runner import compile_tree


def flatten(tn, pairs):
    """Collapse every non-root degree-2 node, summing its length into its
    child. Leaf-to-leaf distances are provably unchanged."""
    par = {n["id"]: n["parent_id"] for n in tn}
    ln = {n["id"]: n["length"] for n in tn}
    kids = {}
    for i, p in par.items():
        if p is not None:
            kids.setdefault(p, []).append(i)
    keep = {i for i in par
            if par[i] is None or len(kids.get(i, [])) != 1}
    # re-parent each kept node to its nearest kept ancestor, summing lengths
    newpar, newlen = {}, {}
    for i in keep:
        if par[i] is None:
            newpar[i], newlen[i] = None, 0.0
            continue
        acc, p = ln[i], par[i]
        while p not in keep:
            acc += ln[p]; p = par[p]
        newpar[i], newlen[i] = p, acc
    order = [n["id"] for n in tn if n["id"] in keep]      # preserve order
    idx = {old: k for k, old in enumerate(order)}
    out = [{"id": idx[o],
            "parent_id": (None if newpar[o] is None else idx[newpar[o]]),
            "length": round(newlen[o], 6)} for o in order]
    npairs = [[idx[a], idx[b]] for a, b in pairs if a in idx and b in idx]
    return out, npairs


def reroot(tn, pairs, new_root):
    """Re-root at `new_root` and emit it FIRST -- the engine takes
    mNodes.front() as the root, so order is the mechanism."""
    par = {n["id"]: n["parent_id"] for n in tn}
    ln = {n["id"]: n["length"] for n in tn}
    adj = {}
    for i, p in par.items():
        if p is not None:
            adj.setdefault(i, []).append((p, ln[i]))
            adj.setdefault(p, []).append((i, ln[i]))
    order, newpar, newlen = [new_root], {new_root: None}, {new_root: 0.0}
    seen, stack = {new_root}, [new_root]
    while stack:
        u = stack.pop(0)
        for v, w in adj.get(u, []):
            if v not in seen:
                seen.add(v); newpar[v] = u; newlen[v] = w
                order.append(v); stack.append(v)
    idx = {o: k for k, o in enumerate(order)}
    out = [{"id": idx[o],
            "parent_id": (None if newpar[o] is None else idx[newpar[o]]),
            "length": round(newlen[o], 6)} for o in order]
    return out, [[idx[a], idx[b]] for a, b in pairs]


def main():
    b = json.load(open(os.path.expanduser(
        "~/Downloads/photo_meshes/hand_trees/trees.json")))
    rows = []
    for subject, e in b["subjects"].items():
        for var in ("faithful", "packable"):
            tn = e[var]["tree_nodes"]
            pr = [list(p) for p in e[var]["symmetric_pairs"]]
            ftn, fpr = flatten(tn, pr)
            st, payload = compile_tree(ftn, fpr, timeout=60)
            rec = {"subject": subject, "variant": var,
                   "nodes_before": len(tn), "nodes_after": len(ftn),
                   "flat_attempt0": st,
                   "err": (None if st == "ok" else payload[:90])}
            rows.append(rec)
            print(f"{subject:9} {var:9} {len(tn):3d} -> {len(ftn):3d} nodes   "
                  f"flat_attempt0={st}", flush=True)
            json.dump(rows, open("/tmp/flatten_probe.json", "w"), indent=2)


if __name__ == "__main__":
    main()
