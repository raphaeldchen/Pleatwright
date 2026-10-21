"""Score the UNIFORM 17: every subject authored on the corrected frame prompt.

Corpus assembly, in precedence order:
    frame_fix15_raw.json   the 15 re-run on 2026-09-09
    frame_fix_raw.json     dog + rabbit, re-run on 2026-09-08
Nothing is taken from run17_raw.json any more; that file is the PRE-FIX corpus
and is kept only so the before/after is auditable.

Also reports, per subject, the mean vertical direction of the leaf-bearing
limbs relative to the body, which is what the frame bug inverts. This is a
DESCRIPTION for the human gate, not a detector -- two attempts at an automatic
orientation test failed validation (ORIENTATION-NEGATIVE.md) and no third one
is attempted here.
"""
from __future__ import annotations
import json, os, sys
import numpy as np, trimesh

S = os.path.dirname(os.path.abspath(__file__))
R = "<repo>"
H = f"{R}/mcp_harness"
sys.path.insert(0, S); sys.path.insert(0, H); sys.path.insert(0, f"{H}/tests")
os.chdir(H)
from runner import compile_tree
import tree_contract, loop_lib as L, reading_fidelity as RF, leaf_label_accuracy as LA
import hand_trees_build as B
import vlm_render as V

D = f"{R}/docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/data"
ORDER = ["dog","cat","horse","rabbit","guinea_pig","elephant","lizard","frog","bird",
         "bat","dolphin","starfish","octopus","crab","spider","scorpion","ant"]
KEY = {"guinea_pig": "guinea pig"}
MESH = os.path.expanduser("~/Downloads/photo_meshes/meshes")


def corpus():
    out = {}
    for f in ("frame_fix_raw.json", "frame_fix15_raw.json"):
        p = f"{D}/{f}"
        if os.path.exists(p):
            for r in json.load(open(p)):
                if r.get("tree"):
                    out[r["subject"]] = r
    return out


def limb_drop(nodes):
    """Mean y of the LEAVES minus mean y of the interior nodes, in grid units.

    Negative means the tree's terminals hang BELOW its body -- feet, in a
    +y-up frame. A whole-tree sign flip reverses it. Reported, never gated on."""
    pos = V.positions(nodes)
    leaves = set(B.leaves_of(nodes))
    lo = [pos[n][1] for n in pos if n in leaves]
    hi = [pos[n][1] for n in pos if n not in leaves]
    return round(float(np.mean(lo) - np.mean(hi)), 2) if lo and hi else None


def main():
    exp = json.load(open("fixtures/anatomy_expectation.json"))
    new, old = corpus(), {r["subject"]: r for r in
                          json.load(open(f"{D}/run17_raw.json")) if r["mode"] == "none"}
    missing = [s for s in ORDER if s not in new]
    if missing:
        print("MISSING, not scored:", missing)

    rows = []
    for s in [s for s in ORDER if s in new]:
        t = new[s]["tree"]; e = exp[KEY.get(s, s)]["expected_feature_count"]
        nodes = L.to_tuples(t); leaves = B.leaves_of(nodes); lset = set(leaves)
        keep = [(a, b) for p in (t.get("pairs") or []) if len(p) == 2
                for a, b in [p] if a in lset and b in lset]
        tn, sp, _ = B.metric_tree(nodes, keep)
        rep = tree_contract.check(tn, sp); st, _ = compile_tree(tn, sp, timeout=60)
        lab = LA.score_labels(KEY.get(s, s), leaves)
        m = trimesh.load(f"{MESH}/{s}.glb", force="mesh"); m.vertices -= m.vertices.mean(axis=0)
        pts = RF.parse_readings(t.get("readings"))
        rf = float(RF.distance_outside(pts, [RF.silhouette(m, v) for v in RF.VIEWS]).mean()) if pts else None
        prev = L.to_tuples(old[s]["tree"]) if s in old else None
        rows.append(dict(subject=s, guess=t.get("subject_guess", ""),
            leaves=len(leaves), exp=e, delta=len(leaves) - e, nodes=len(nodes),
            pairs=len(sp), contract_ok=not rep.get("errors"), packs=(st == "ok"),
            label_exact=lab["exact"], coverage=lab["coverage"],
            missing=lab.get("missing"), spurious=lab.get("spurious"),
            unmatched=lab.get("unmatched_labels"), rf=rf,
            drop=limb_drop(nodes), drop_before=(limb_drop(prev) if prev else None),
            leaves_before=(len(B.leaves_of(prev)) if prev else None),
            leaf_labels=leaves))
    json.dump(rows, open(f"{D}/uniform17_scored.json", "w"), indent=1)

    d = [abs(r["delta"]) for r in rows]; n = len(rows)
    print(f"\nUNIFORM {n}: MAE {sum(d)/n:.2f}  count-exact {sum(1 for x in d if x==0)}/{n}"
          f"  label-exact {sum(1 for r in rows if r['label_exact'])}/{n}"
          f"  contract {sum(1 for r in rows if r['contract_ok'])}/{n}"
          f"  packs {sum(1 for r in rows if r['packs'])}/{n}"
          f"  cov {np.mean([r['coverage'] for r in rows]):.3f}"
          f"  rf {np.mean([r['rf'] for r in rows if r['rf'] is not None]):.3f}"
          + (f"  [rf unreadable: {[r['subject'] for r in rows if r['rf'] is None]}]"
             if any(r["rf"] is None for r in rows) else ""))
    print(f"\n  {'subject':11}{'now':>5}{'was':>5}{'exp':>5}   {'drop now':>9}{'drop was':>9}  flags")
    for r in rows:
        f = []
        if r["delta"]: f.append(f"{r['delta']:+d} leaves")
        if not r["label_exact"]: f.append("labels")
        if r["packs"]: f.append("packs")
        if r["rf"] is None: f.append("NO PARSEABLE READINGS")
        print(f"  {r['subject']:11}{r['leaves']:>5}{str(r['leaves_before']):>5}{r['exp']:>5}"
              f"   {str(r['drop']):>9}{str(r['drop_before']):>9}  {', '.join(f)}")


if __name__ == "__main__":
    main()
