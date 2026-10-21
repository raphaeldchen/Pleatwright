"""Which SUBJECTS pack, run by run -- not just how many."""
import json, os, sys
R="<repo>"
H=f"{R}/mcp_harness"; E=f"{R}/docs/superpowers/evidence/2026-09-08-vlm-tree-authoring"
sys.path.insert(0,f"{E}/scripts"); sys.path.insert(0,H); sys.path.insert(0,f"{H}/tests")
os.chdir(H)
from runner import compile_tree
import loop_lib as L, hand_trees_build as B

def packs(recs):
    out={}
    for r in recs:
        t=r.get("tree")
        if not t: continue
        nodes=L.to_tuples(t); lset=set(B.leaves_of(nodes))
        keep=[(a,b) for p in (t.get("pairs") or []) if len(p)==2
              for a,b in [p] if a in lset and b in lset]
        tn,sp,_=B.metric_tree(nodes,keep)
        st,_=compile_tree(tn,sp,timeout=60)
        out[r["subject"]]=(st=="ok")
    return out

def main():
    D=f"{E}/data"
    run1=[r for r in json.load(open(f"{D}/run17_raw.json")) if r["mode"]=="none"]
    run2=json.load(open(f"{D}/run17_replicate_raw.json"))
    uni={}
    for f in ("frame_fix_raw.json","frame_fix15_raw.json"):
        for r in json.load(open(f"{D}/{f}")):
            if r.get("tree"): uni[r["subject"]]=r
    A,Bp,C = packs(run1), packs(run2), packs(list(uni.values()))
    subs=sorted(set(A)|set(Bp)|set(C))
    print(f"{'subject':12}{'run1':>6}{'run2':>6}{'unif':>6}")
    for s in subs:
        print(f"  {s:12}{str(A.get(s)):>6}{str(Bp.get(s)):>6}{str(C.get(s)):>6}")
    sa={s for s in A if A[s]}; sb={s for s in Bp if Bp[s]}; sc={s for s in C if C[s]}
    print(f"\nrun1 {sorted(sa)}\nrun2 {sorted(sb)}\nunif {sorted(sc)}")
    print(f"\ncounts: run1 {len(sa)}  run2 {len(sb)}  unif {len(sc)}")
    print(f"run1 vs run2 (SAME prompt): shared {len(sa&sb)}, symmetric diff {len(sa^sb)}")
    print(f"run2 vs unif (prompt CHANGED): shared {len(sb&sc)}, symmetric diff {len(sb^sc)}")
    json.dump({"run1":sorted(sa),"run2":sorted(sb),"uniform":sorted(sc)},
              open(os.environ["S"]+"/packsets.json","w"), indent=1)

if __name__=="__main__":
    main()
