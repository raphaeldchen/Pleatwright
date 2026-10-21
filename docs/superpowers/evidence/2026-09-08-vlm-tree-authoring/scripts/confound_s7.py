"""Is the S7 signal accuracy, or just verbosity?

The arms that scored worst also emitted the MOST readings (text: 142 reads,
mean 0.787; none: 83 reads, mean 0.189). If mean distance rises with reading
count, the metric is ranking talkativeness, not accuracy, and its 'power'
result is an artifact.
"""
import json, os, sys
import numpy as np, trimesh
H = "<repo>/mcp_harness"
sys.path.insert(0, H); os.chdir(H)
import reading_fidelity as R

E = "../docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/data"
MESH = os.path.expanduser("~/Downloads/photo_meshes/meshes")
_c = {}
def masks(s):
    if s not in _c:
        m = trimesh.load(f"{MESH}/{s}.glb", force="mesh")
        m.vertices -= m.vertices.mean(axis=0)
        _c[s] = [R.silhouette(m, v) for v in R.VIEWS]
    return _c[s]

rows = []
for f, key in ((f"{E}/grid_arms_raw.json", "arm"), (f"{E}/ablation_raw.json", "mode")):
    for rec in json.load(open(f)):
        t = rec.get("tree")
        if not t: continue
        pts = R.parse_readings(t.get("readings"))
        if not pts: continue
        d = R.distance_outside(pts, masks(rec["subject"]))
        rows.append(dict(arm=rec[key], subject=rec["subject"], n=len(pts),
                         mean=float(d.mean()), frac_in=float((d==0).mean())))

n = np.array([r["n"] for r in rows]); mu = np.array([r["mean"] for r in rows])
r_pear = np.corrcoef(n, mu)[0,1]
print(f"per-cell n={len(rows)}   corr(n_readings, mean_distance) = {r_pear:+.3f}")

# subject is the obvious lurking variable: some animals are simply harder
print("\nmean distance BY SUBJECT (pooled over all six arms):")
for s in sorted({r["subject"] for r in rows}):
    v = [r["mean"] for r in rows if r["subject"] == s]
    print(f"   {s:9} n={len(v)}  mean={np.mean(v):.3f}  spread={np.ptp(v):.3f}")

print("\nmean distance BY ARM, after removing the subject effect")
print("(each cell minus its subject's pooled mean -- a paired comparison):")
sub_mean = {s: np.mean([r["mean"] for r in rows if r["subject"]==s])
            for s in {r["subject"] for r in rows}}
for a in ["A","B","C","none","text","visual"]:
    v = [r["mean"] - sub_mean[r["subject"]] for r in rows if r["arm"]==a]
    print(f"   {a:8} n={len(v)}  adjusted={np.mean(v):+.3f}")
adj = {a: np.mean([r["mean"]-sub_mean[r["subject"]] for r in rows if r["arm"]==a])
       for a in ["A","B","C","none","text","visual"]}
print(f"\n   adjusted spread: {max(adj.values())-min(adj.values()):.3f} grid units")
print(f"   raw spread was:  0.598")
