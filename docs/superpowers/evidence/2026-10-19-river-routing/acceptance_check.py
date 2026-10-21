"""River-routing acceptance §8.1-8.4 and the time half of §8.6, read from the
two corpus runs (no folding):

  NEW  = ~/Desktop/pleatwright_river_routing   (HEAD 22e32eb3, beside on)
  BASE = ~/Desktop/pleatwright_baseline_4a64d1ad (main 4a64d1ad)

usage:  python acceptance_check.py [NEW BASE]   (prints a JSON report)"""
import filecmp
import json
import os
import statistics
import sys

FILES = ("packing_cp.svg", "solving_cp.svg", "shaping_cp.svg", "overview.png")


#: the baseline records predate the river_corners metric; river_corners_before.py
#: recomputes it on today's chosen layout (pack_options(roll, beside=False)).
_RC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "river_corners_before.json")
BEFORE_RC = json.load(open(_RC)) if os.path.exists(_RC) else {}


def records(d):
    with open(os.path.join(d, "records.jsonl")) as f:
        return {r["roll"]: r for r in map(json.loads, f)}


def main(new, base):
    N, B = records(new), records(base)
    out = {"n_records": len(N), "failures": [r for r, x in N.items() if x.get("failure")],
           "verdicts": {}}
    for x in N.values():
        out["verdicts"][x["global_verdict"]] = out["verdicts"].get(x["global_verdict"], 0) + 1
    # §8.2 byte identity, by folder name
    same, diff, compared, orphans = 0, [], 0, []
    changed = []
    for roll, x in sorted(N.items()):
        name = os.path.basename(x["folder"])
        bdir = os.path.join(base, name)
        if os.path.isdir(bdir):
            compared += 1
            for f in FILES:
                if filecmp.cmp(os.path.join(x["folder"], f), os.path.join(bdir, f), shallow=False):
                    same += 1
                else:
                    diff.append((roll, f))
        else:
            orphans.append({"roll": roll, "folder": name, "family": x["layout"]["family"],
                            "base_folder": os.path.basename(B[roll]["folder"])})
            changed.append(roll)
    out["byte_identity"] = {"folders": compared, "identical_files": same, "different": diff,
                            "no_counterpart": orphans,
                            "all_no_counterpart_beside": all(o["family"] == "beside" for o in orphans)}
    # §8.3 changed trees
    rows = []
    for roll in changed:
        x, b = N[roll], B[roll]
        ok_v = x["global_verdict"] == "CERTIFIED" or (
            x["global_verdict"] == "OVERSIZE+LOCAL_SAT" and b["global_verdict"] == "OVERSIZE+LOCAL_SAT")
        sff, shf = x["solving_flat_foldable"], x["shaping_flat_foldable"]
        rows.append({"roll": roll, "grid_base": b["grid_size"], "grid_new": x["grid_size"],
                     "chosen": x["layout"]["chosen"], "reason": x["layout"]["reason"],
                     "beside": x["layout"]["beside"],
                     "verdict_base": b["global_verdict"], "verdict_new": x["global_verdict"],
                     "solving": sff, "shaping": shf,
                     "pass": ok_v and sff[0] == sff[1] and shf[0] == shf[1],
                     "pack_secs_base": b["pack_secs"], "pack_secs_new": x["pack_secs"]})
    out["changed"] = rows
    # §8.4 grid report on the multi-hub trees (beside outcome not no_child_hub)
    grid = []
    for roll, x in sorted(N.items()):
        if x["layout"]["beside"]["symmetric"] == "no_child_hub":
            continue
        e, eb = x["efficiency"], B[roll]["efficiency"]
        grid.append({"roll": roll, "C_before": B[roll]["grid_size"], "C_after": x["grid_size"],
                     "family": x["layout"]["family"], "beside": x["layout"]["beside"],
                     "n_over_bound": [eb["n_over_bound"], e["n_over_bound"]],
                     "slack_fraction": [eb["slack_fraction"], e["slack_fraction"]],
                     "mean_layers": [eb["mean_layers"], e["mean_layers"]],
                     "river_corners": [BEFORE_RC.get(roll), e.get("river_corners")]})
    med = {}
    for k in ("C_before", "C_after"):
        med[k] = statistics.median(g[k] for g in grid)
    for k in ("n_over_bound", "slack_fraction", "mean_layers", "river_corners"):
        vals = [[g[k][i] for g in grid if g[k][i] is not None] for i in (0, 1)]
        med[k] = [statistics.median(v) if v else None for v in vals]
    out["grid_report"] = {"n": len(grid), "rows": grid, "medians": med}
    # beside outcomes and §8.6 time
    oc = {}
    for x in N.values():
        for k, v in x["layout"]["beside"].items():
            v = v if isinstance(v, str) else "grid"
            oc[v] = oc.get(v, 0) + 1
    out["beside_outcomes"] = oc
    out["builds_outcome"] = [r for r, x in N.items() if "builds" in x["layout"]["beside"].values()]
    ps = sorted(((x["pack_secs"], r) for r, x in N.items()), reverse=True)
    out["pack_secs_top"] = ps[:6]
    out["total_secs_sum"] = round(sum(x["total_secs"] for x in N.values()), 1)
    return out


if __name__ == "__main__":
    a = sys.argv[1:] or [os.path.expanduser("~/Desktop/pleatwright_river_routing"),
                         os.path.expanduser("~/Desktop/pleatwright_baseline_4a64d1ad")]
    print(json.dumps(main(*a), indent=1))
