"""Score all 27 wired-loop trees and render them in the hand-authored views."""
import json, os, sys
S = os.path.dirname(os.path.abspath(__file__))
H = "<repo>/mcp_harness"
sys.path.insert(0, S); sys.path.insert(0, H); sys.path.insert(0, os.path.join(H, "tests"))
os.chdir(H)
from runner import compile_tree
import tree_contract, loop_lib as L
import hand_trees_build as B

OUT = os.path.expanduser("~/Downloads/photo_meshes/llm_trees_v2")
SUBJ = ["dog", "cat", "horse", "lizard", "frog", "bird",
        "starfish", "spider", "octopus"]


def main():
    for d in ("sheets",):
        os.makedirs(f"{OUT}/{d}", exist_ok=True)
    raw = {(x["arm"], x["subject"]): x
           for x in json.load(open("/tmp/loop_raw.json")) if x.get("tree")}
    exp = json.load(open(f"{H}/fixtures/anatomy_expectation.json"))
    res, rows = {}, []
    for arm in "ABC":
        for s in SUBJ:
            r = raw.get((arm, s))
            if not r:
                continue
            t = r["tree"]
            nodes = L.to_tuples(t)
            pairs = [(a, b) for p in (t.get("pairs") or [])
                     if len(p) == 2 for a, b in [p]]
            names = {n[0] for n in nodes}
            leaves = set(B.leaves_of(nodes))
            keep = [(a, b) for a, b in pairs
                    if a in leaves and b in leaves]
            tn, sp, labels = B.metric_tree(nodes, keep)
            rep = tree_contract.check(tn, sp)
            st, payload = compile_tree(tn, sp, timeout=60)
            e = exp[s]["expected_feature_count"]
            n = len(leaves)
            sc = [x for x in r["log"] if x.get("stage") == "selfcheck"]
            rec = {"arm": arm, "subject": s, "subject_guess": t.get("subject_guess"),
                   "leaf_count": n, "expected": e, "delta": n - e,
                   "n_nodes": len(nodes), "pairs_kept": len(keep),
                   "pairs_dropped": len(pairs) - len(keep),
                   "revised_by_selfcheck": (sc[0].get("revised") if sc else None),
                   "contract_errors": rep.get("errors", []),
                   "attempt0": st,
                   "readings": t.get("readings"), "notes": t.get("notes"),
                   "tree_nodes": tn, "symmetric_pairs": sp,
                   "labels": {str(i): nm for i, nm in labels.items()},
                   "length_grid": {n_[0]: n_[3] for n_ in nodes},
                   "directions": {n_[0]: n_[2] for n_ in nodes}}
            res[f"{arm}/{s}"] = rec
            rows.append(rec)
            L.sheet(nodes, f"{OUT}/sheets/{arm}_{s}.png",
                    f"{s} — LLM arm {arm} — {n} leaves (expected {e})")
    json.dump(res, open(f"{OUT}/trees.json", "w"), indent=2)

    print(f"{'arm':4}{'subject':10}{'leaves':>7}{'exp':>5}{'d':>4}"
          f"{'nodes':>6}{'revised':>9}{'contract':>10}{'pack':>6}")
    for r in rows:
        print(f"{r['arm']:4}{r['subject']:10}{r['leaf_count']:>7}{r['expected']:>5}"
              f"{r['delta']:>+4}{r['n_nodes']:>6}"
              f"{str(r['revised_by_selfcheck']):>9}"
              f"{('OK' if not r['contract_errors'] else 'ERR'):>10}"
              f"{r['attempt0']:>6}")
    print()
    for arm in "ABC":
        a = [r for r in rows if r["arm"] == arm]
        if not a:
            continue
        e = [abs(r["delta"]) for r in a]
        print(f"arm {arm}: n={len(a)}  MAE={sum(e)/len(e):.2f}  "
              f"exact={sum(1 for x in e if x == 0)}/{len(a)}  "
              f"contract_clean={sum(1 for r in a if not r['contract_errors'])}/{len(a)}  "
              f"packs={sum(1 for r in a if r['attempt0'] == 'ok')}/{len(a)}  "
              f"revised={sum(1 for r in a if r['revised_by_selfcheck'])}/{len(a)}")


if __name__ == "__main__":
    main()
