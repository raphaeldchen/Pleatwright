"""Validate, compile and render the trees the live model authored."""
import json, os, sys
H = "<repo>/mcp_harness"
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, H); sys.path.insert(0, os.path.join(H, "tests"))
sys.path.insert(0, S)
os.chdir(H)
from runner import compile_tree
import tree_contract
import hand_trees_build as B

LONGEST = 0.40
OUT = os.path.expanduser("~/Downloads/photo_meshes/llm_trees")


def to_metric(t):
    """Model tuples -> repo Metric Tree, preserving the model's own node order."""
    names = [n["name"] for n in t["nodes"]]
    idx = {n: i for i, n in enumerate(names)}
    mx = max(n["length"] for n in t["nodes"]) or 1
    k = LONGEST / mx
    tn = [{"id": i,
           "parent_id": (idx[n["parent"]] if n.get("parent") else None),
           "length": round(n["length"] * k, 6)}
          for i, n in enumerate(t["nodes"])]
    kids = {}
    for n in tn:
        if n["parent_id"] is not None:
            kids[n["parent_id"]] = kids.get(n["parent_id"], 0) + 1
    leaves = {names[n["id"]] for n in tn if not kids.get(n["id"])}
    # pairs: keep only those joining two ACTUAL leaves -- the model paired
    # internal joints too, which the repo's format does not model.
    pairs, dropped = [], []
    for p in (t.get("pairs") or []):
        if len(p) == 2 and p[0] in idx and p[1] in idx:
            if p[0] in leaves and p[1] in leaves:
                pairs.append([idx[p[0]], idx[p[1]]])
            else:
                dropped.append(p)
    return tn, pairs, dropped, sorted(leaves), idx


def main():
    os.makedirs(f"{OUT}/sheets", exist_ok=True)
    raw = json.load(open("/tmp/arms_raw.json"))
    exp = json.load(open(f"{H}/fixtures/anatomy_expectation.json"))
    out = {}
    print(f"{'subj':9} {'arm':3} {'leaves':>6} {'exp':>4} {'contract':>9} "
          f"{'attempt0':>9} {'pairs_kept':>10} {'pairs_dropped':>13}")
    for r in sorted([x for x in raw if x.get("tree")],
                    key=lambda x: x["subject"]):
        t = r["tree"]
        tn, pairs, dropped, leaves, idx = to_metric(t)
        rep = tree_contract.check(tn, pairs)
        st, payload = compile_tree(tn, pairs, timeout=60)
        e = exp[r["subject"]]["expected_feature_count"]
        # a sheet, using the model's own node names as labels
        nodes4 = [(n["name"], n.get("parent"), (1, 0.3, 0.2), n["length"])
                  for n in t["nodes"]]
        out[r["subject"]] = {
            "arm": r["arm"], "subject_guess": t.get("subject_guess"),
            "readings": t.get("readings"), "notes": t.get("notes"),
            "leaves": leaves, "leaf_count": len(leaves),
            "expected_feature_count": e, "delta": len(leaves) - e,
            "tree_nodes": tn, "symmetric_pairs": pairs,
            "labels": {str(v): k for k, v in idx.items()},
            "length_grid": {n["name"]: n["length"] for n in t["nodes"]},
            "pairs_dropped_not_leaf_pairs": dropped,
            "contract_errors": rep.get("errors", []),
            "contract_warnings": rep.get("warnings", []),
            "attempt0": st,
            "attempt0_error": (None if st == "ok"
                               else str(payload).split("(scale")[0][:120]),
        }
        print(f"{r['subject']:9} {r['arm']:3} {len(leaves):>6} {e:>4} "
              f"{('OK' if not rep.get('errors') else 'ERRORS'):>9} {st:>9} "
              f"{len(pairs):>10} {len(dropped):>13}")
    json.dump(out, open(f"{OUT}/llm_trees.json", "w"), indent=2)
    print(f"\nwrote {OUT}/llm_trees.json")


if __name__ == "__main__":
    main()
