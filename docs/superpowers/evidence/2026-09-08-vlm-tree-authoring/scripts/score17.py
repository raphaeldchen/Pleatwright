"""Score the 17-subject ablation: anatomy, contract, packing, reading fidelity."""
import json, os, sys
import numpy as np, trimesh
S=os.path.dirname(os.path.abspath(__file__))
H="<repo>/mcp_harness"
sys.path.insert(0,S); sys.path.insert(0,H); sys.path.insert(0,os.path.join(H,"tests"))
os.chdir(H)
from runner import compile_tree
import tree_contract, loop_lib as L, reading_fidelity as RF
import hand_trees_build as B

def main():
    KEY={"guinea_pig":"guinea pig"}
    MESH=os.path.expanduser("~/Downloads/photo_meshes/meshes")
    exp=json.load(open("fixtures/anatomy_expectation.json"))
    _c={}
    def masks(s):
        if s not in _c:
            m=trimesh.load(f"{MESH}/{s}.glb",force="mesh"); m.vertices-=m.vertices.mean(axis=0)
            _c[s]=[RF.silhouette(m,v) for v in RF.VIEWS]
        return _c[s]

    rows=[]
    for rec in json.load(open("/tmp/run17_raw.json")):
        t=rec.get("tree")
        if not t: continue
        s=rec["subject"]; e=exp[KEY.get(s,s)]["expected_feature_count"]
        nodes=L.to_tuples(t); leaves=set(B.leaves_of(nodes))
        keep=[(a,b) for p in (t.get("pairs") or []) if len(p)==2 for a,b in [p]
              if a in leaves and b in leaves]
        tn,sp,_=B.metric_tree(nodes,keep)
        rep=tree_contract.check(tn,sp); st,_=compile_tree(tn,sp,timeout=60)
        pts=RF.parse_readings(t.get("readings"))
        rf=float(RF.distance_outside(pts,masks(s)).mean()) if pts else None
        rv=[x for x in rec["log"] if x.get("stage")=="review"]
        rows.append(dict(mode=rec["mode"],subject=s,leaves=len(leaves),exp=e,
            delta=len(leaves)-e, nodes=len(nodes),
            contract_ok=not rep.get("errors"), packs=(st=="ok"),
            rf=rf, revised=(rv[0].get("revised") if rv else None),
            tokens=rec.get("usage",{}).get("total_tokens",0)))
    json.dump(rows,open(f"{S}/score17.json","w"),indent=2)

    print(f"{'mode':8}{'n':>3}{'MAE':>7}{'exact':>8}{'clean':>8}{'packs':>8}"
          f"{'read_fid':>10}{'revised':>9}{'tokens':>11}")
    agg={}
    for m in ("none","text","visual"):
        a=[r for r in rows if r["mode"]==m]; d=[abs(r["delta"]) for r in a]
        rf=[r["rf"] for r in a if r["rf"] is not None]
        agg[m]=dict(mae=sum(d)/len(d),exact=sum(1 for x in d if x==0),n=len(a),
                    rf=float(np.mean(rf)))
        print(f"{m:8}{len(a):>3}{agg[m]['mae']:>7.2f}{agg[m]['exact']:>5}/{len(a):<2}"
              f"{sum(1 for r in a if r['contract_ok']):>5}/{len(a):<2}"
              f"{sum(1 for r in a if r['packs']):>5}/{len(a):<2}"
              f"{np.mean(rf):>10.3f}{sum(1 for r in a if r['revised']):>6}/{len(a):<2}"
              f"{sum(r['tokens'] for r in a):>11,}")

    # baselines on the SAME 17
    man=json.load(open(os.path.expanduser("~/Downloads/photo_meshes/manifest.json")))
    ext=[]
    for mm in man["meshes"]:
        r=mm["reference_extraction_NOT_ground_truth"]
        e=mm["anatomy_ground_truth"]["expected_feature_count"]
        ext.append(abs(r.get("delta_vs_anatomy", r["leaf_count"]-e)))
    print(f"\n{'extractor':8}{len(ext):>3}{sum(ext)/len(ext):>7.2f}"
          f"{sum(1 for x in ext if x==0):>5}/{len(ext):<2}   (auto_mesh_to_metric_tree)")

    print("\nper-subject leaf delta (visual arm) — + is over-count:")
    v={r["subject"]:r for r in rows if r["mode"]=="visual"}
    em={mm["file_stem"] if "file_stem" in mm else mm["subject"]:
        mm["reference_extraction_NOT_ground_truth"] for mm in man["meshes"]}
    print(f"  {'subject':11}{'llm':>5}{'extr':>6}{'exp':>5}")
    for s in ["dog","cat","horse","lizard","frog","bird","starfish","spider","octopus",
              "dolphin","guinea_pig","rabbit","bat","elephant","ant","scorpion","crab"]:
        if s in v:
            ex=em.get(s,{}).get("leaf_count","?")
            print(f"  {s:11}{v[s]['leaves']:>5}{ex:>6}{v[s]['exp']:>5}"
                  f"   {'LLM exact' if v[s]['delta']==0 else ''}")


if __name__ == "__main__":
    main()
