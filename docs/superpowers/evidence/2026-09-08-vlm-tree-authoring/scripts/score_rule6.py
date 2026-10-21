"""Score the rule-6 corpus, and put FUSION beside the metrics that missed it.

Reports the previous corpus's value for every column, because the question is
not "is this good" but "did rule 6 fix the fusion WITHOUT costing anything
else". A prompt change that fixes limb topology and loses two leaf counts is
not a win, and only a paired table shows that.
"""
from __future__ import annotations
import json, os, sys
import numpy as np, trimesh

S = os.path.dirname(os.path.abspath(__file__))
R = "<repo>"
H = f"{R}/mcp_harness"
E = f"{R}/docs/superpowers/evidence/2026-09-08-vlm-tree-authoring"
sys.path.insert(0, S); sys.path.insert(0, H); sys.path.insert(0, f"{H}/tests")
os.chdir(H)
from runner import compile_tree
import tree_contract, loop_lib as L, reading_fidelity as RF
import leaf_label_accuracy as LA, pair_fusion as PF, vlm_render as V
import hand_trees_build as B

D = f"{E}/data"
ORDER = ["dog","cat","horse","rabbit","guinea_pig","elephant","lizard","frog","bird",
         "bat","dolphin","starfish","octopus","crab","spider","scorpion","ant"]
KEY = {"guinea_pig": "guinea pig"}
MESH = os.path.expanduser("~/Downloads/photo_meshes/meshes")


def corpus(files):
    out = {}
    for f in files:
        p = f"{D}/{f}"
        if os.path.exists(p):
            for r in json.load(open(p)):
                if r.get("tree"):
                    out[r["subject"]] = r["tree"]
    return out


def limb_drop(nodes):
    pos = V.positions(nodes); leaves = set(B.leaves_of(nodes))
    lo = [pos[n][1] for n in pos if n in leaves]
    hi = [pos[n][1] for n in pos if n not in leaves]
    return round(float(np.mean(lo) - np.mean(hi)), 2) if lo and hi else None


def measure(t, subject, exp, want_compile=True):
    nodes = L.to_tuples(t); leaves = B.leaves_of(nodes); lset = set(leaves)
    keep = [(a, b) for p in (t.get("pairs") or []) if len(p) == 2
            for a, b in [p] if a in lset and b in lset]
    tn, sp, names = B.metric_tree(nodes, keep)
    fus = PF.score_fusion(tn, sp)
    rep = tree_contract.check(tn, sp)
    st = compile_tree(tn, sp, timeout=60)[0] if want_compile else None
    lab = LA.score_labels(KEY.get(subject, subject), leaves)
    return dict(leaves=len(leaves), exp=exp, delta=len(leaves) - exp,
                nodes=len(nodes), pairs=len(sp),
                contract_ok=not rep.get("errors"), packs=(st == "ok"),
                label_exact=lab["exact"], coverage=lab["coverage"],
                min_fusion=fus["min_branch_fraction"],
                fusion=[(names.get(r["pair"][0]), names.get(r["pair"][1]),
                         r["branch_fraction"]) for r in fus["pairs"]],
                drop=limb_drop(nodes), leaf_labels=leaves)


def main():
    exp = json.load(open("fixtures/anatomy_expectation.json"))
    new = corpus(["rule6_raw.json"])
    old = corpus(["frame_fix_raw.json", "frame_fix15_raw.json"])

    rows = []
    for s in ORDER:
        e = exp[KEY.get(s, s)]["expected_feature_count"]
        n = measure(new[s], s, e)
        o = measure(old[s], s, e) if s in old else None
        m = trimesh.load(f"{MESH}/{s}.glb", force="mesh")
        m.vertices -= m.vertices.mean(axis=0)
        pts = RF.parse_readings(new[s].get("readings"))
        n["rf"] = (float(RF.distance_outside(
            pts, [RF.silhouette(m, v) for v in RF.VIEWS]).mean()) if pts else None)
        n["subject"] = s; n["prev"] = o
        rows.append(n)
    json.dump(rows, open(f"{D}/rule6_scored.json", "w"), indent=1)

    d = [abs(r["delta"]) for r in rows]; N = len(rows)
    fus_new = [r["min_fusion"] for r in rows if r["min_fusion"] is not None]
    fus_old = [r["prev"]["min_fusion"] for r in rows
               if r["prev"] and r["prev"]["min_fusion"] is not None]
    print(f"RULE-6 {N}: MAE {sum(d)/N:.2f}  count-exact {sum(1 for x in d if x==0)}/{N}"
          f"  label-exact {sum(1 for r in rows if r['label_exact'])}/{N}"
          f"  contract {sum(1 for r in rows if r['contract_ok'])}/{N}"
          f"  packs {sum(1 for r in rows if r['packs'])}/{N}"
          f"  cov {np.mean([r['coverage'] for r in rows]):.3f}"
          f"  rf {np.mean([r['rf'] for r in rows if r['rf'] is not None]):.3f}")
    print(f"  worst-3 fusion now {sorted(fus_new)[:3]}   before {sorted(fus_old)[:3]}")
    print(f"\n  {'subject':11}{'leaves':>8}{'exp':>5}{'fusion now':>12}{'was':>8}"
          f"{'packs':>7}{'drop':>7}")
    for r in rows:
        p = r["prev"]
        now = f'{r["min_fusion"]:.3f}' if r["min_fusion"] is not None else "n/a"
        was = (f'{p["min_fusion"]:.3f}'
               if p and p["min_fusion"] is not None else "n/a")
        flag = ""
        if r["min_fusion"] is not None and p and p["min_fusion"] is not None:
            if p["min_fusion"] < 0.30 <= r["min_fusion"]:
                flag = "  <-- fusion FIXED"
            elif r["min_fusion"] < 0.30 <= p["min_fusion"]:
                flag = "  <-- fusion BROKE"
        print(f"  {r['subject']:11}{r['leaves']:>8}{r['exp']:>5}{now:>12}{was:>8}"
              f"{('Y' if r['packs'] else 'n'):>7}{r['drop']:>7}{flag}")

if __name__ == "__main__":
    main()
