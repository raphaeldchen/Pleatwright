"""The DEFENSIBLE arm only: the AREA_EPS margin per subject.

Drops the fine-threshold comparison. That arm produced 130,071 cells from 142
on `cat` -- ten orders of magnitude below a legitimate cell, i.e. clipping
debris -- so its "lost pairs" figure is an upper bound on a quantity no tool
here can pin down: exact arithmetic would arbitrate it, and TreeMaker
coordinates do not rationalize within SNAP_TOL.

What IS defensible needs only production's own threshold: every
`area_nonzero` decision, and the smallest area that SURVIVED it. That minimum
is by definition the threshold at which the first drop would occur, so
min_kept / AREA_EPS is the per-subject safety margin -- a real measurement
with no arbitrary fine threshold in it.

Writes after every subject, because the previous run died at a time limit
with its artifact unwritten.
"""
import dataclasses, json, os, sys, time
ROOT = os.path.abspath(".")
sys.path.insert(0, os.path.join(ROOT, "mcp_harness"))
sys.path.insert(0, os.path.join(ROOT, "docs/superpowers/evidence/2026-10-04-exact-arrangement"))
import flat_fold, geom, kernel, layer_order            # noqa: E402

AREA_EPS = layer_order.AREA_EPS
NOISE = 1e-14


def main():
    man = json.load(open(os.path.join(sys.argv[1], "manifest.json")))
    out_path = sys.argv[2]
    rows = []
    for m in man["rows"]:
        if not m.get("ok"):
            rows.append({"subject": m["subject"], "compiled": False})
        else:
            ff = flat_fold.flat_fold(json.load(open(m["fold"])))
            polys = [[(float(x), float(y)) for x, y in q]
                     for q in layer_order._polys_of(ff)]
            seen = []
            K = dataclasses.replace(
                kernel.FLOAT,
                area_nonzero=lambda a: (seen.append(abs(a)),
                                        abs(a) > AREA_EPS)[1])
            t0 = time.time()
            cells = geom.cells(polys, K)
            drop = [a for a in seen if a <= AREA_EPS]
            kept = [a for a in seen if a > AREA_EPS]
            rows.append({
                "subject": m["subject"], "compiled": True,
                "clean": m.get("clean"), "tree_nodes": m.get("tree_nodes"),
                "faces": len(polys), "cells": len(cells),
                "decisions": len(seen), "dropped": len(drop),
                "noise_lt_1e-14": len([a for a in drop if a < NOISE]),
                "grey_1e-14_to_1e-9":
                    len([a for a in drop if NOISE <= a <= AREA_EPS]),
                "min_kept_area": min(kept) if kept else None,
                "margin_x": (min(kept) / AREA_EPS) if kept else None,
                "secs": round(time.time() - t0, 1)})
        json.dump({"AREA_EPS": AREA_EPS, "rows": rows}, open(out_path, "w"),
                  indent=2, default=str)        # write after EVERY subject
        r = rows[-1]
        print(f"{r['subject']:12s} clean={r.get('clean')} "
              f"cells={r.get('cells')} grey={r.get('grey_1e-14_to_1e-9')} "
              f"margin={r.get('margin_x') and round(r['margin_x'], 2)}",
              flush=True)
    done = [r for r in rows if r.get("compiled")]
    print(json.dumps({
        "subjects": len(rows), "censused": len(done),
        "clean": sum(1 for r in done if r.get("clean")),
        "min_margin": min((r["margin_x"] for r in done if r["margin_x"]),
                          default=None),
        "max_margin": max((r["margin_x"] for r in done if r["margin_x"]),
                          default=None),
        "subjects_with_grey_drops":
            sum(1 for r in done if r["grey_1e-14_to_1e-9"]),
    }, indent=2))


if __name__ == "__main__":
    main()
