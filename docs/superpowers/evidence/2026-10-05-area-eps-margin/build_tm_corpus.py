"""Compile the 17 authored rule6 trees through TREEMAKER.

The box-pleat arm builds a different population: coarse rational grid, huge
AREA_EPS margins, no F edges. The AREA_EPS risk was measured on TreeMaker
geometry -- nonlinear packer output, margins 1.0-3.1x -- so the corpus that
can answer the question has to be compiled this way, with the tree recorded.
"""
import json, os, sys, time
ROOT = os.path.abspath(".")
sys.path.insert(0, os.path.join(ROOT, "mcp_harness"))
import cp_audit                                        # noqa: E402
import server                                          # noqa: E402

def main():
    """Wrapped so spawned workers do not re-run the whole loop.

    `server.py`'s compile path SPAWNS, and a spawned child re-imports
    this file as `__main__`. Without the guard below the child re-ran
    the entire corpus loop, hit multiprocessing's bootstrap check, and
    clobbered the manifest the parent had just written -- which is how
    a successful run came to report `compiled 0 of 17`.
    """
    RULE6 = ("docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/data/"
             "rule6_serve.json")
    OUT = sys.argv[1]
    os.makedirs(OUT, exist_ok=True)
    rows = []
    for e in json.load(open(RULE6)):
        subj = e["subject"]
        rec = {"subject": subj, "tree_nodes": len(e["requested"]),
               "tree_pairs": e.get("pairs") or [], "source": f"{RULE6}#{subj}"}
        t0 = time.time()
        try:
            out = server.draft_and_compile_full_base(e["requested"], e["pairs"])
            if isinstance(out, str) and out.startswith("ERROR"):
                rec["ok"] = False
                rec["error"] = out[:220]
            else:
                fold = json.loads(out) if isinstance(out, str) else out
                p = os.path.join(OUT, f"{subj}.fold")
                json.dump(fold, open(p, "w"))
                a = cp_audit.audit_fold(fold)
                mk = sum(1 for v in a.vertices if abs(v.m - v.v) != 2)
                kw = sum(1 for v in a.vertices
                         if abs(v.kawasaki_residual_deg) > a.kawasaki_tol_deg)
                ar = sum(1 for v in a.vertices if not v.arrangement_ok)
                rec.update(ok=True, fold=p,
                           verts=len(fold.get("vertices_coords", [])),
                           edges=len(fold.get("edges_vertices", [])),
                           audit={"interior": len(a.vertices), "maekawa": mk,
                                  "kawasaki": kw, "arrangement": ar,
                                  "closure_bad": a.closure_bad_edges},
                           clean=(mk == 0 and kw == 0 and ar == 0
                                  and a.closure_bad_edges == 0
                                  and len(a.vertices) > 0))
        except Exception as exc:
            rec.update(ok=False, error=f"{type(exc).__name__}: {str(exc)[:200]}")
        rec["secs"] = round(time.time() - t0, 1)
        rows.append(rec)
        print(f"TM {subj:14s} ok={rec.get('ok')} clean={rec.get('clean')} "
              f"{rec['secs']}s", flush=True)

    ok = [r for r in rows if r.get("ok")]
    clean = [r for r in ok if r.get("clean")]
    json.dump({"source": RULE6, "compiler": "treemaker", "subjects": len(rows),
               "compiled": len(ok), "cp_audit_clean": len(clean), "rows": rows},
              open(os.path.join(OUT, "manifest.json"), "w"), indent=2)
    print(json.dumps({"subjects": len(rows), "compiled": len(ok),
                      "clean": len(clean),
                      "clean_subjects": [r["subject"] for r in clean]}, indent=2))


if __name__ == "__main__":
    main()
