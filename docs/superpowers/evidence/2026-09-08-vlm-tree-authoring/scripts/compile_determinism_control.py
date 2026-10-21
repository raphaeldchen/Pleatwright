"""Is compile_tree deterministic? Rules out 'the packer is random' as the
explanation for the pack-set churn."""
import json, os, sys
R="<repo>"
H=f"{R}/mcp_harness"; E=f"{R}/docs/superpowers/evidence/2026-09-08-vlm-tree-authoring"
sys.path.insert(0,f"{E}/scripts"); sys.path.insert(0,H); sys.path.insert(0,f"{H}/tests")
os.chdir(H)
from runner import compile_tree
import loop_lib as L, hand_trees_build as B

def main():
    D=f"{E}/data"
    recs={r["subject"]:r for r in json.load(open(f"{D}/run17_raw.json")) if r["mode"]=="none"}
    for s in ("bird","elephant","dog","spider"):
        t=recs[s]["tree"]; nodes=L.to_tuples(t); lset=set(B.leaves_of(nodes))
        keep=[(a,b) for p in (t.get("pairs") or []) if len(p)==2
              for a,b in [p] if a in lset and b in lset]
        tn,sp,_=B.metric_tree(nodes,keep)
        outs=[compile_tree(tn,sp,timeout=60)[0] for _ in range(3)]
        print(f"  {s:10} {outs}  {'DETERMINISTIC' if len(set(outs))==1 else 'VARIES'}")

if __name__=="__main__":
    main()
