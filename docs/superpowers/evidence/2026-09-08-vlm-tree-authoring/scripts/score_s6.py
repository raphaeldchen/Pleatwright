"""Score the S6 ablation: none vs text vs visual."""
import json, os, sys
S = os.path.dirname(os.path.abspath(__file__))
H = "<repo>/mcp_harness"
sys.path.insert(0, S); sys.path.insert(0, H); sys.path.insert(0, os.path.join(H, "tests"))
os.chdir(H)
from runner import compile_tree
import tree_contract, loop_lib as L
import hand_trees_build as B

SUBJ = ["dog", "cat", "horse", "lizard", "frog", "bird",
        "starfish", "spider", "octopus"]
OUT = os.path.expanduser("~/Downloads/photo_meshes/s6_ablation")


def main():
    os.makedirs(OUT, exist_ok=True)
    raw = {(x["mode"], x["subject"]): x
           for x in json.load(open("/tmp/s6_raw.json")) if x.get("tree")}
    exp = json.load(open(f"{H}/fixtures/anatomy_expectation.json"))
    rows, store = [], {}
    for mode in ("none", "text", "visual"):
        for s in SUBJ:
            r = raw.get((mode, s))
            if not r:
                continue
            t = r["tree"]
            nodes = L.to_tuples(t)
            leaves = set(B.leaves_of(nodes))
            pairs = [(a, b) for p in (t.get("pairs") or []) if len(p) == 2
                     for a, b in [p]]
            keep = [(a, b) for a, b in pairs if a in leaves and b in leaves]
            tn, sp, labels = B.metric_tree(nodes, keep)
            rep = tree_contract.check(tn, sp)
            st, _ = compile_tree(tn, sp, timeout=60)
            rv = [x for x in r["log"] if x.get("stage") == "review"]
            rec = {"mode": mode, "subject": s, "leaf_count": len(leaves),
                   "expected": exp[s]["expected_feature_count"],
                   "delta": len(leaves) - exp[s]["expected_feature_count"],
                   "n_nodes": len(nodes),
                   "revised": (rv[0].get("revised") if rv else None),
                   "contract_errors": rep.get("errors", []),
                   "attempt0": st, "tree_nodes": tn, "symmetric_pairs": sp,
                   "labels": {str(i): n for i, n in labels.items()},
                   "readings": t.get("readings")}
            rows.append(rec); store[f"{mode}/{s}"] = rec
    json.dump(store, open(f"{OUT}/s6.json", "w"), indent=2)

    print(f"{'mode':8}{'subject':10}{'leaves':>7}{'exp':>5}{'d':>4}"
          f"{'revised':>9}{'contract':>10}{'pack':>6}")
    for r in rows:
        print(f"{r['mode']:8}{r['subject']:10}{r['leaf_count']:>7}{r['expected']:>5}"
              f"{r['delta']:>+4}{str(r['revised']):>9}"
              f"{('OK' if not r['contract_errors'] else 'ERR'):>10}{r['attempt0']:>6}")
    print()
    print(f"{'condition':9}{'n':>3}{'MAE':>7}{'exact':>8}{'clean':>8}"
          f"{'packs':>8}{'revised':>9}")
    agg = {}
    for mode in ("none", "text", "visual"):
        a = [r for r in rows if r["mode"] == mode]
        e = [abs(r["delta"]) for r in a]
        agg[mode] = dict(
            n=len(a), mae=sum(e)/len(e),
            exact=sum(1 for x in e if x == 0),
            clean=sum(1 for r in a if not r["contract_errors"]),
            packs=sum(1 for r in a if r["attempt0"] == "ok"),
            revised=sum(1 for r in a if r["revised"]))
        v = agg[mode]
        print(f"{mode:9}{v['n']:>3}{v['mae']:>7.2f}{v['exact']:>5}/{v['n']:<2}"
              f"{v['clean']:>5}/{v['n']:<2}{v['packs']:>5}/{v['n']:<2}"
              f"{v['revised']:>6}/{v['n']:<2}")
    print(f"\nnone -> text   (what a 2nd turn is worth): "
          f"MAE {agg['none']['mae']:.2f} -> {agg['text']['mae']:.2f}, "
          f"exact {agg['none']['exact']} -> {agg['text']['exact']}")
    print(f"text -> visual (what SEEING it is worth):  "
          f"MAE {agg['text']['mae']:.2f} -> {agg['visual']['mae']:.2f}, "
          f"exact {agg['text']['exact']} -> {agg['visual']['exact']}")


if __name__ == "__main__":
    main()
