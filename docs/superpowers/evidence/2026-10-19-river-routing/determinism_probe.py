"""River-routing acceptance §8.6: `pipeline.pack_options(roll).summary()` (the
production default, beside on) for all 51 artifact trees in one process, as
one JSON object {roll: summary}.  Run it twice in separate processes and
compare the dumps.  From mcp_harness/:

  PYTHONPATH=. python ../docs/superpowers/evidence/2026-10-19-river-routing/determinism_probe.py OUT.json"""
import glob
import json
import os
import sys
import time

from pleatwright import pipeline as PL

out, secs = {}, {}
for p in sorted(glob.glob(os.path.join(PL.STICKS, "*.json"))):
    roll = os.path.basename(p)[:-5]
    t0 = time.perf_counter()
    out[roll] = PL.pack_options(roll).summary()
    secs[roll] = round(time.perf_counter() - t0, 1)
    print(roll, secs[roll], flush=True, file=sys.stderr)
with open(sys.argv[1], "w") as f:
    json.dump(out, f, sort_keys=True, indent=1)
