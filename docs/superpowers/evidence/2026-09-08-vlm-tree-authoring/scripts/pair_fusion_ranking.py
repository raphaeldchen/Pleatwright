import json, os, sys
R="<repo>"
H=f"{R}/mcp_harness"; E=f"{R}/docs/superpowers/evidence/2026-09-08-vlm-tree-authoring"
sys.path.insert(0,f"{E}/scripts"); sys.path.insert(0,H); sys.path.insert(0,f"{H}/tests")
os.chdir(H)
import pair_fusion as PF, loop_lib as L, hand_trees_build as B
ORDER=["dog","cat","horse","rabbit","guinea_pig","elephant","lizard","frog","bird",
       "bat","dolphin","starfish","octopus","crab","spider","scorpion","ant"]
EYE={"horse","elephant","guinea_pig"}     # what the owner flagged by eye
def main():
    D=f"{E}/data"; raw={}
    for f in ("frame_fix_raw.json","frame_fix15_raw.json"):
        for r in json.load(open(f"{D}/{f}")):
            if r.get("tree"): raw[r["subject"]]=r
    rows=[]
    for s in ORDER:
        t=raw[s]["tree"]; nodes=L.to_tuples(t); lset=set(B.leaves_of(nodes))
        keep=[(a,b) for p in (t.get("pairs") or []) if len(p)==2
              for a,b in [p] if a in lset and b in lset]
        tn,sp,names=B.metric_tree(nodes,keep)
        sc=PF.score_fusion(tn,sp)
        rows.append((s,sc["min_branch_fraction"],sc["n_fused"],len(sc["pairs"])))
    rows.sort(key=lambda r: (r[1] is None, r[1]))
    print(f"{'subject':12}{'min frac':>10}{'fused':>7}{'pairs':>7}   flagged by eye?")
    for s,mn,nf,np_ in rows:
        print(f"{s:12}{(f'{mn:.3f}' if mn is not None else 'n/a'):>10}{nf:>7}{np_:>7}"
              f"   {'YES' if s in EYE else ''}")
    flagged={s for s,mn,_,_ in rows if mn is not None and mn < PF.FUSED_BELOW}
    print(f"\nmetric flags: {sorted(flagged)}")
    print(f"eye flagged : {sorted(EYE)}")
    print(f"agreement   : TP={len(flagged&EYE)} FP={len(flagged-EYE)} FN={len(EYE-flagged)}")
    lo=[r[1] for r in rows if r[0] in EYE]; hi=[r[1] for r in rows if r[0] not in EYE and r[1] is not None]
    print(f"flagged range {min(lo):.3f}-{max(lo):.3f}   clean range {min(hi):.3f}-{max(hi):.3f}")
if __name__=="__main__": main()
