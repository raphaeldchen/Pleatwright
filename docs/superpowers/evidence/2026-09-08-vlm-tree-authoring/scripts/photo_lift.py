"""Photo -> Hunyuan3D-2 -> .glb -> metric tree.

Bypasses stage 1 (FLUX) by pre-seeding the run directory with the user's photo
as `concept.<ext>` and driving TwoStageProvider with reuse_concept=True. That
seam already exists because stage-2 retries must never repay for a concept
draw (mesh_acquire.py, "stage 0"), so no code change is needed to feed a real
photograph instead of a generated one.

    python photo_lift.py <label> <photo> [<label> <photo> ...] --out DIR
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
import traceback

HARNESS = "<repo>/mcp_harness"
sys.path.insert(0, HARNESS)

import env_config
env_config.load_env()

import mesh_acquire
import mesh_to_tree
import probe_mesh_bakeoff as bo


def slug(s):
    return "".join(c if c.isalnum() else "_" for c in s.lower()).strip("_")


def lift(label, photo, out_root, extract=True):
    run_dir = os.path.join(out_root, slug(label))
    os.makedirs(run_dir, exist_ok=True)
    ext = os.path.splitext(photo)[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".webp"):
        raise ValueError(f"{label}: unsupported photo extension {ext!r}")
    concept = os.path.join(run_dir, "concept" + ext)
    if not os.path.exists(concept):
        shutil.copyfile(photo, concept)

    rec = {"label": label, "photo": photo, "concept": concept,
           "run_dir": run_dir}
    glb = os.path.join(run_dir, "mesh.glb")
    t0 = time.time()
    if os.path.isfile(glb) and os.path.getsize(glb) > 0:
        rec["lift"] = "CACHED"
    else:
        provider = mesh_acquire.TwoStageProvider(
            token=os.environ.get("HF_TOKEN") or None,
            mesh_kwargs=dict(mesh_acquire.HUNYUAN_SHAPE_KWARGS),
            attempts=bo.BAKEOFF_ATTEMPTS, backoff=bo.BAKEOFF_BACKOFF,
            reuse_concept=True,          # <- the whole trick: skip FLUX
        )
        try:
            glb = provider.generate(label, run_dir)
            rec["lift"] = "OK"
        except Exception as e:
            rec["lift"] = "FAILED"
            rec["error"] = f"{type(e).__name__}: {e}"
            rec["traceback"] = traceback.format_exc()
            return rec
    rec["lift_seconds"] = round(time.time() - t0, 1)
    rec["glb"] = glb
    rec["mesh"] = bo.measure_mesh(glb)

    if extract:
        t1 = time.time()
        try:
            r = mesh_to_tree.auto_mesh_to_metric_tree(glb)
            rec["tree"] = {
                "confirmed": bool(r.confirmed),
                "n_nodes": len(r.nodes),
                "n_pairs": len(r.pairs),
                "voxel_res": r.voxel_res,
                "prune_fraction": r.prune_fraction,
                "fidelity": r.fidelity,
                "reference_count": r.reference_count,
                "stub_flaps": r.stub_flaps,
                "repaired": r.repaired,
                "leaf_labels": {str(k): v.get("label") if isinstance(v, dict) else v
                                for k, v in (r.leaf_labels or {}).items()},
            }
            rec["extract_seconds"] = round(time.time() - t1, 1)
        except Exception as e:
            rec["tree"] = {"error": f"{type(e).__name__}: {e}"}
            rec["traceback"] = traceback.format_exc()
    return rec


def main(argv):
    out_root = "photo_runs"
    if "--out" in argv:
        i = argv.index("--out")
        out_root = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    extract = "--no-extract" not in argv
    argv = [a for a in argv if a != "--no-extract"]
    pairs = list(zip(argv[0::2], argv[1::2]))
    os.makedirs(out_root, exist_ok=True)
    rows = []
    for label, photo in pairs:
        print(f"=== {label}  <-  {photo}", flush=True)
        rec = lift(label, photo, out_root, extract=extract)
        rows.append(rec)
        print(json.dumps({k: v for k, v in rec.items() if k != "traceback"},
                         indent=2), flush=True)
        if rec.get("traceback"):
            print(rec["traceback"], flush=True)
        with open(os.path.join(out_root, "results.json"), "w") as f:
            json.dump(rows, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
