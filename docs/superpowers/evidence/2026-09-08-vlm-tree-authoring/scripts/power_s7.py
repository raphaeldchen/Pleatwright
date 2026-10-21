"""Do the arm differences survive the subject effect? Paired by subject.

Nine subjects, six arms, every subject seen by every arm -- so the correct
comparison is PAIRED (per-subject differences), not pooled. Pooling lets the
starfish, whose readings vary by 4.055 grid units across arms, dominate.
"""
import json, os, sys, itertools
import numpy as np, trimesh
H = "<repo>/mcp_harness"
sys.path.insert(0, H); os.chdir(H)
import reading_fidelity as R
E = "../docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/data"
MESH = os.path.expanduser("~/Downloads/photo_meshes/meshes")
_c={}
def masks(s):
    if s not in _c:
        m=trimesh.load(f"{MESH}/{s}.glb",force="mesh"); m.vertices-=m.vertices.mean(axis=0)
        _c[s]=[R.silhouette(m,v) for v in R.VIEWS]
    return _c[s]

cell={}
for f,key in ((f"{E}/grid_arms_raw.json","arm"),(f"{E}/ablation_raw.json","mode")):
    for rec in json.load(open(f)):
        t=rec.get("tree")
        if not t: continue
        pts=R.parse_readings(t.get("readings"))
        if not pts: continue
        cell[(rec[key],rec["subject"])]=float(R.distance_outside(pts,masks(rec["subject"])).mean())

SUBJ=sorted({s for _,s in cell})
def paired(a,b):
    d=[cell[(a,s)]-cell[(b,s)] for s in SUBJ if (a,s) in cell and (b,s) in cell]
    d=np.array(d); rng=np.random.default_rng(0)
    boot=[rng.choice(d,len(d)).mean() for _ in range(10000)]
    lo,hi=np.percentile(boot,[2.5,97.5])
    return d.mean(),lo,hi,len(d)

print("PAIRED comparisons (mean difference in grid units, bootstrap 95% CI)")
print("negative = first arm has MORE accurate readings\n")
for grp,name in (( ["A","B","C"],"grid design"),
                 (["none","text","visual"],"self-check ablation")):
    print(f"--- {name} ---")
    for a,b in itertools.combinations(grp,2):
        m,lo,hi,n=paired(a,b)
        sig = "SIGNIFICANT" if (lo>0 or hi<0) else "not significant"
        print(f"  {a:6} vs {b:6}  n={n}  diff={m:+.3f}  CI[{lo:+.3f},{hi:+.3f}]  {sig}")
    print()
print("per-subject mean distance, by arm:")
print(f"{'subject':10}" + "".join(f"{a:>9}" for a in ["A","B","C","none","text","visual"]))
for s in SUBJ:
    print(f"{s:10}" + "".join(
        f"{cell.get((a,s),float('nan')):>9.3f}" for a in ["A","B","C","none","text","visual"]))
