"""Does the S7 metric discriminate where leaf count could not?

Two questions, in order:
  1. VALIDITY  -- do real readings separate from uniform-random points? If not,
                  the metric is uninformative and nothing from it is quotable.
  2. POWER     -- does it separate the six arms that leaf count scored
                  identically (grid A/B/C, ablation none/text/visual)?
"""
import json, os, sys
import numpy as np, trimesh
H = "<repo>/mcp_harness"
sys.path.insert(0, H); os.chdir(H)
import reading_fidelity as R

E = "docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/data"
MESH = os.path.expanduser("~/Downloads/photo_meshes/meshes")
_cache = {}


def mesh(subj):
    if subj not in _cache:
        m = trimesh.load(f"{MESH}/{subj}.glb", force="mesh")
        m.vertices -= m.vertices.mean(axis=0)
        _cache[subj] = [R.silhouette(m, v) for v in R.VIEWS]
    return _cache[subj]


def cell(subj, readings, seed):
    masks = mesh(subj)
    pts = R.parse_readings(readings)
    rng = np.random.default_rng(seed)
    d = R.distance_outside(pts, masks)
    rnd = R.distance_outside(rng.uniform(0, R.GRID, size=(max(len(pts),1), 2)), masks)
    return d, rnd


def main():
    runs = {}
    for f, key in ((f"{H}/../{E}/grid_arms_raw.json", "arm"),
                   (f"{H}/../{E}/ablation_raw.json", "mode")):
        for rec in json.load(open(os.path.normpath(f))):
            t = rec.get("tree")
            if not t:
                continue
            arm = rec[key]
            runs.setdefault(arm, []).append((rec["subject"], t.get("readings")))

    print(f"{'arm':8}{'cells':>6}{'reads':>7}{'inside%':>9}{'mean_d':>8}"
          f"{'median':>8}{'p90':>7}   | {'rand_in%':>9}{'rand_mean':>10}")
    agg = {}
    for arm, cells in runs.items():
        D, RND = [], []
        for i, (subj, rd) in enumerate(sorted(cells)):
            d, r = cell(subj, rd, seed=i)
            D.append(d); RND.append(r)
        d = np.concatenate(D); r = np.concatenate(RND)
        agg[arm] = d
        print(f"{arm:8}{len(cells):>6}{len(d):>7}{100*(d==0).mean():>8.1f}%"
              f"{d.mean():>8.3f}{np.median(d):>8.3f}{np.percentile(d,90):>7.3f}"
              f"   | {100*(r==0).mean():>8.1f}%{r.mean():>10.3f}")

    all_d = np.concatenate(list(agg.values()))
    all_r = np.concatenate([cell(s, rd, seed=i)[1]
                            for arm, c in runs.items()
                            for i, (s, rd) in enumerate(sorted(c))])
    print(f"\n1. VALIDITY  model mean {all_d.mean():.3f} vs random "
          f"{all_r.mean():.3f}  ({all_r.mean()/max(all_d.mean(),1e-9):.1f}x)")
    print(f"   inside:    model {100*(all_d==0).mean():.1f}%  vs random "
          f"{100*(all_r==0).mean():.1f}%")

    print("\n2. POWER   spread across the six arms leaf count scored 8/9 each:")
    means = {a: float(v.mean()) for a, v in agg.items()}
    lo, hi = min(means, key=means.get), max(means, key=means.get)
    print(f"   best  {lo:8} {means[lo]:.3f}")
    print(f"   worst {hi:8} {means[hi]:.3f}")
    print(f"   spread {means[hi]-means[lo]:.3f} grid units")
    # bootstrap CI on the best-worst gap, since n per arm is small
    rng = np.random.default_rng(0)
    a, b = agg[lo], agg[hi]
    boot = [rng.choice(b, len(b)).mean() - rng.choice(a, len(a)).mean()
            for _ in range(4000)]
    lo95, hi95 = np.percentile(boot, [2.5, 97.5])
    print(f"   bootstrap 95% CI on that gap: [{lo95:.3f}, {hi95:.3f}]"
          f"  -> {'SEPARATES' if lo95 > 0 else 'does NOT separate'}")


if __name__ == "__main__":
    main()
