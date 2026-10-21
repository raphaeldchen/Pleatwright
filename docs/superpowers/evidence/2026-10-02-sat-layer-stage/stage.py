"""The SAT layer stage, end to end on dense and sparse `lizard`.

Spec: `../../specs/2026-10-02-sat-layer-stage-design.md`.

Records the three things the spec left to measurement: peak RSS for the
9.7M-clause build (which decides whether `MAX_CLAUSES` must come down), the
stage's wall clock against the shipped dense path's 1052.0 s
(`../2026-09-27-core-in-loop/ab.json` arms[0].secs), and whether the emitted
fold passes `cp_audit`.

Prints no verdict until every figure is in hand.
"""
import json
import resource
import sys
import time

sys.path.insert(0, ".")

import cp_audit
from box_pleat import sat_order
from box_pleat.compile import compile_tree

RULE6 = ("../docs/superpowers/evidence/2026-09-08-vlm-tree-authoring"
         "/data/rule6_serve.json")


def peak_rss_mb():
    """macOS reports ru_maxrss in BYTES; Linux in kilobytes."""
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return raw / (1024 * 1024) if sys.platform == "darwin" else raw / 1024


_SEEN = []   # raw_triple_bound of every cons handed to sat_order.solve


def _recording_solve(real):
    """Pass-through wrapper: records `raw_triple_bound(cons)` and changes nothing.

    `compile_tree` builds `cons` internally and never returns it, so the only
    way to read the bound for the instance the compile actually used, without
    editing `mcp_harness/`, is to observe the call. The wrapper forwards every
    argument unchanged and returns the real result untouched.
    """
    def wrapper(cons, slots, *a, **k):
        _SEEN.append(sat_order.raw_triple_bound(cons))
        return real(cons, slots, *a, **k)
    return wrapper


sat_order.solve = _recording_solve(sat_order.solve)


def audit(fold):
    r = cp_audit.audit_fold(fold)
    if not r.vertices:
        # An empty population would return all-zero counters, which reads as a
        # clean pass. Refuse instead.
        raise SystemExit("audit refused: cp_audit returned no interior "
                         "vertices, so zero violations would be vacuous")
    return {
        "interior": len(r.vertices),
        "maekawa": sum(1 for v in r.vertices if abs(v.m - v.v) != 2),
        "kawasaki": sum(1 for v in r.vertices
                        if abs(v.kawasaki_residual_deg) > r.kawasaki_tol_deg),
        "arrangement": sum(1 for v in r.vertices if not v.arrangement_ok),
        "closure_bad_edges": r.closure_bad_edges,
        "closure_max_error": r.closure_max_error,
    }


def main(out_path):
    with open(RULE6) as fh:
        e = next(x for x in json.load(fh) if x["subject"] == "lizard")
    rec = {"subject": "lizard", "max_clauses": sat_order.MAX_CLAUSES,
           "max_raw_triples": sat_order.MAX_RAW_TRIPLES,
           "rss_before_mb": round(peak_rss_mb(), 1)}

    for tag, dense in (("sparse", False), ("dense", True)):
        _SEEN.clear()
        t0 = time.perf_counter()
        res = compile_tree(e["requested"], e["pairs"], dense=dense,
                           sat_layers=True)
        secs = round(time.perf_counter() - t0, 1)
        row = {"stage_reached": res.stage_reached, "secs": secs,
               "peak_rss_mb": round(peak_rss_mb(), 1),
               "failure": repr(res.failure)}
        if len(_SEEN) != 1:
            raise SystemExit(f"{tag}: expected exactly one sat_order.solve "
                             f"call, saw {len(_SEEN)}; raw_triple_bound would "
                             f"not be about the compiled instance")
        row["raw_triple_bound"] = _SEEN[0]
        if res.verdict is not None:
            row["verdict"] = {
                "kind": res.verdict.kind,
                "order_vars": getattr(res.verdict, "order_vars", None),
                "label_vars": getattr(res.verdict, "label_vars", None),
                "clauses": getattr(res.verdict, "clauses", None),
                "build_secs": getattr(res.verdict, "build_secs", None),
                "solve_secs": getattr(res.verdict, "solve_secs", None),
            }
        if res.fold is not None:
            row["audit"] = audit(res.fold)
            row["fold"] = {"vertices": len(res.fold["vertices_coords"]),
                           "edges": len(res.fold["edges_vertices"])}
        rec[tag] = row
        print(f"{tag}: stage={row['stage_reached']} secs={secs} "
              f"peak_rss={row['peak_rss_mb']}MB "
              f"verdict={row.get('verdict', {}).get('kind')}", flush=True)
        if "audit" in row:
            print(f"   audit {row['audit']}", flush=True)

    with open(out_path, "w") as fh:
        json.dump(rec, fh, indent=1, sort_keys=True)
    print(f"wrote {out_path}")

    d = rec["dense"]
    print()
    if d["stage_reached"] != "emit":
        print(f"VERDICT: the dense stage did NOT reach emit "
              f"({d['stage_reached']}, {d['failure']}). Report this; it "
              f"contradicts evidence 2026-10-02-witness-identity-113 section 15.")
    elif d["peak_rss_mb"] > 4096:
        print(f"VERDICT: EMITS, but peak RSS is {d['peak_rss_mb']}MB, over the "
              f"spec's ~4 GB line. MAX_CLAUSES must come down to match -- "
              f"spec section 5 requires the default to be derived from this "
              f"measurement.")
    else:
        a = d["audit"]
        print(f"VERDICT: EMITS in {d['secs']}s at {d['peak_rss_mb']}MB peak "
              f"RSS, against the shipped dense path's 1052.0s with no answer "
              f"(../2026-09-27-core-in-loop/ab.json arms[0]). cp_audit "
              f"maekawa={a['maekawa']} kawasaki={a['kawasaki']} "
              f"arrangement={a['arrangement']} of {a['interior']} interior "
              f"vertices. MAX_CLAUSES stands at "
              f"{rec['max_clauses']:,}.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: stage.py <out.json>")
    main(sys.argv[1])
