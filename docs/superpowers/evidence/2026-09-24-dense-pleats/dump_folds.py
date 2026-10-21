"""Byte-identity evidence (Task 8 Step 0, spec section 9): dump the SPARSE
`.fold` of all 8 emitting subjects, run under two checkouts, so the two runs'
outputs can be sha256-compared without moving HEAD.

This calls `compile_tree(entry["requested"], entry["pairs"])` with NO `dense`
argument -- the byte-identity guarantee is that adding the `dense=` feature
did not change a single byte of the SPARSE path's output. The e2e test
(`test_already_consistent_subjects_emit_byte_identical_folds`) covers only
`bird` and `starfish`, the two subjects with `layers_tried == 1` that accept
the first candidate and never enter the CEGAR relabelling loop this plan's
earlier tasks modified. This script covers the other six too:
`lizard horse octopus frog guinea_pig dog`.

Written incrementally (one file per subject, as soon as that subject's
compile finishes) so a run that is killed partway still leaves usable output
for every subject already completed.

Run from mcp_harness, against EITHER checkout (old base via `git archive`,
new worktree HEAD), writing to a DIFFERENT output directory each time:

  PYTHONPATH=. ../.venv/bin/python3 -u ../docs/superpowers/evidence/2026-09-24-dense-pleats/dump_folds.py /tmp/bp-old
  PYTHONPATH=. ../.venv/bin/python3 -u ../docs/superpowers/evidence/2026-09-24-dense-pleats/dump_folds.py /tmp/bp-new

Then, per subject:
  shasum -a 256 < /tmp/bp-old/<subject>.json
  shasum -a 256 < /tmp/bp-new/<subject>.json
and compare.
"""
import json
import os
import sys
import time

from box_pleat.compile import compile_tree

OUTDIR = sys.argv[1]
RULE6 = os.path.join("..", "docs", "superpowers", "evidence",
                     "2026-09-08-vlm-tree-authoring", "data", "rule6_serve.json")
ORDER = ["starfish", "bird", "lizard", "horse", "octopus", "frog",
         "guinea_pig", "dog"]


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    entries = {e["subject"]: e for e in json.load(open(RULE6))}
    for s in ORDER:
        t0 = time.time()
        res = compile_tree(entries[s]["requested"], entries[s]["pairs"])
        secs = round(time.time() - t0, 1)
        if res.stage_reached != "emit":
            print(f"{s:11s} STOP@{res.stage_reached} failure={res.failure!r} "
                  f"{secs}s", flush=True)
            continue
        path = os.path.join(OUTDIR, f"{s}.json")
        with open(path, "w") as f:
            f.write(json.dumps(res.fold, sort_keys=True))
        print(f"{s:11s} wrote {path} ({len(json.dumps(res.fold))} bytes) "
              f"layers_tried={res.layers_tried} {secs}s", flush=True)


main()
