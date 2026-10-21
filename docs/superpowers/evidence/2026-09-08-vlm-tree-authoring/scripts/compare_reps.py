"""Run-to-run reproducibility of the finalized loop: sweep 1 vs sweep 2.

Identical configuration, N=1 each. Whatever differs is what N=1 costs -- and
that number is the yardstick every "not significant" claim in this spec should
have been measured against.
"""
import json, os, sys
import numpy as np, trimesh
S=os.path.dirname(os.path.abspath(__file__))
H="<repo>/mcp_harness"
sys.path.insert(0,S); sys.path.insert(0,H); sys.path.insert(0,os.path.join(H,"tests"))
os.chdir(H)
import tree_contract, loop_lib as L, reading_fidelity as RF
import hand_trees_build as B
from runner import compile_tree

KEY={"guinea_pig":"guinea pig"}
MESH=os.path.expanduser("~/Downloads/photo_meshes/meshes")
exp=json.load(open("fixtures/anatomy_expectation.json"))
_c={}
def masks(s):
    if s not in _c:
        m=trimesh.load(f"{MESH}/{s}.glb",force="mesh"); m.vertices-=m.vertices.mean(axis=0)
        _c[s]=[RF.silhouette(m,v) for v in RF.VIEWS]
    return _c[s]

def score(path, mode_filter=None):
    out={}
    for rec in json.load(open(path)):
        if mode_filter and rec.get("mode")!=mode_filter: continue
        t=rec.get("tree")
        if not t: continue
        s=rec["subject"]; e=exp[KEY.get(s,s)]["expected_feature_count"]
        nodes=L.to_tuples(t); leaves=set(B.leaves_of(nodes))
        keep=[(a,b) for p in (t.get("pairs") or []) if len(p)==2 for a,b in [p]
              if a in leaves and b in leaves]
        tn,sp,_=B.metric_tree(nodes,keep)
        st,_=compile_tree(tn,sp,timeout=60)
        pts=RF.parse_readings(t.get("readings"))
        out[s]=dict(leaves=len(leaves),exp=e,delta=len(leaves)-e,nodes=len(nodes),
                    clean=not tree_contract.check(tn,sp).get("errors"),
                    packs=(st=="ok"),
                    rf=(float(RF.distance_outside(pts,masks(s)).mean()) if pts else None))
    return out

def main():
    a=score("/tmp/run17_raw.json","none"); b=score("/tmp/run17_rep_raw.json")
    subs=sorted(set(a)&set(b))
    print(f"{'subject':11}{'exp':>4}{'run1':>6}{'run2':>6}{'same':>6}"
          f"{'rf1':>8}{'rf2':>8}")
    agree=0
    for s in subs:
        same = a[s]["leaves"]==b[s]["leaves"]; agree+=same
        print(f"{s:11}{a[s]['exp']:>4}{a[s]['leaves']:>6}{b[s]['leaves']:>6}"
              f"{('yes' if same else 'NO'):>6}"
              f"{(a[s]['rf'] if a[s]['rf'] is not None else float('nan')):>8.3f}"
              f"{(b[s]['rf'] if b[s]['rf'] is not None else float('nan')):>8.3f}")
    def agg(d):
        dd=[abs(v["delta"]) for v in d.values()]
        rf=[v["rf"] for v in d.values() if v["rf"] is not None]
        return (sum(dd)/len(dd), sum(1 for x in dd if x==0), len(dd),
                sum(1 for v in d.values() if v["clean"]),
                sum(1 for v in d.values() if v["packs"]), float(np.mean(rf)))
    for tag,d in (("run 1",a),("run 2",b)):
        mae,ex,n,cl,pk,rf=agg(d)
        print(f"\n{tag}: MAE={mae:.2f}  exact={ex}/{n}  clean={cl}/{n}  "
              f"packs={pk}/{n}  read_fid={rf:.3f}")
    print(f"\nleaf count identical on {agree}/{len(subs)} subjects "
          f"({100*agree/len(subs):.0f}%)")
    d1=np.array([abs(a[s]["delta"]) for s in subs])
    d2=np.array([abs(b[s]["delta"]) for s in subs])
    print(f"per-subject |delta| changed on {int((d1!=d2).sum())}/{len(subs)}")
    print(f"\nRUN-TO-RUN MAE SPREAD: {abs(d1.mean()-d2.mean()):.3f}")
    print("  ^ this is the noise floor. Any arm difference smaller than it")
    print("    is unreadable at N=1, no matter what its CI says.")

if __name__ == "__main__":
    main()
