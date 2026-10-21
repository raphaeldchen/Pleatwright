"""Build results.md + records.jsonl from a batch record file.

    python summarise.py <rec.jsonl>
"""
import json, sys, os, statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
rows = [json.loads(l) for l in open(sys.argv[1])]
rows.sort(key=lambda r: r["roll"])
keep = ("roll", "packing_rung", "scale", "grid_init", "grid_size", "pack_tried", "pack_secs", "solve_secs",
        "solving_flat_foldable", "solving_heuristic_local", "global_verdict",
        "relabelled_by_certificate", "shape_secs", "shaping_flat_foldable", "faces",
        "closure_error", "mean_axial_strain", "tree_similarity", "orchestrator",
        "orchestration_error", "total_secs", "failure", "error", "folder", "simple_folds",
        "narrowings", "stick_figure")
with open(os.path.join(HERE, "records.jsonl"), "w") as f:
    for r in rows:
        f.write(json.dumps({k: r[k] for k in keep if k in r}, default=float) + "\n")
ok = [r for r in rows if not r.get("failure")]
lines = ["| roll | grid | solving FF | global | shaping FF | closure | strain | similarity | secs |",
         "|---|---|---|---|---|---|---|---|---|"]
for r in rows:
    if r.get("failure"):
        lines.append(f"| {r['roll']} | — | FAILED: {r.get('failure')} {r.get('error','')[:60]} | | | | | | |")
        continue
    s, h = r["solving_flat_foldable"], r["shaping_flat_foldable"]
    lines.append(f"| {r['roll']} | {r['grid_size']} | {s[0]}/{s[1]} | {r['global_verdict']} | "
                 f"{h[0]}/{h[1]} | {r['closure_error']:.1e} | {r['mean_axial_strain']:.1e} | "
                 f"{r['tree_similarity']:.3f} | {r['total_secs']:.0f} |")
summ = {
    "trees": len(rows), "completed": len(ok),
    "solving_all_vertices_flat_foldable": sum(1 for r in ok if r["solving_flat_foldable"][0] == r["solving_flat_foldable"][1]),
    "globally_certified": sum(1 for r in ok if r["global_verdict"] == "CERTIFIED"),
    "shaping_all_vertices_flat_foldable": sum(1 for r in ok if r["shaping_flat_foldable"][0] == r["shaping_flat_foldable"][1]),
    "max_closure_error": max((r["closure_error"] for r in ok), default=None),
    "median_tree_similarity": st.median(r["tree_similarity"] for r in ok) if ok else None,
    "min_tree_similarity": min((r["tree_similarity"] for r in ok), default=None),
    "grid_range": [min(r["grid_size"] for r in ok), max(r["grid_size"] for r in ok)] if ok else None,
    "total_minutes": round(sum(r.get("total_secs", 0) for r in ok) / 60, 1),
}
open(os.path.join(HERE, "results.md"), "w").write(
    "# COrigami pipeline on the 51 Bases-in-Triplicate-III trees\n\n```json\n"
    + json.dumps(summ, indent=1) + "\n```\n\n" + "\n".join(lines) + "\n")
print(json.dumps(summ, indent=1))
