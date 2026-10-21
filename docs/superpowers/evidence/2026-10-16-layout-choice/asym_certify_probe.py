"""Throwaway probe: run the FULL pipeline (pack, solve + global certify, shape,
fold) with the symmetric rungs disabled, so the unmirrored rung wins. Compares
against the committed 2026-10-06 records. Usage (from mcp_harness/):
    python asym_certify_probe.py OUT_JSONL OUT_DIR roll [roll ...]
"""
import json
import sys
import traceback

from pleatwright import pipeline as PL

orig = PL.PK.candidates


def no_symmetric(con, symmetric=True, **kw):
    if symmetric:
        return iter(())
    return orig(con, symmetric=False, **kw)


PL.PK.candidates = no_symmetric

out_jsonl, out_dir, *rolls = sys.argv[1:]
for r in rolls:
    try:
        rec = PL.run(r, out_dir, verbose=False)
    except Exception as e:
        rec = {"roll": r, "failure": repr(e), "trace": traceback.format_exc()[-1500:]}
    keep = {k: rec.get(k) for k in ("roll", "packing_rung", "grid_size", "pack_tried",
                                    "solving_flat_foldable", "global_verdict",
                                    "shaping_flat_foldable", "closure_error",
                                    "tree_similarity", "total_secs", "failure", "trace")}
    with open(out_jsonl, "a") as f:
        f.write(json.dumps(keep, default=float) + "\n")
    print(json.dumps({k: v for k, v in keep.items() if k != "trace"}), flush=True)
