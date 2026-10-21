"""river_corners of today's chosen layout (the baseline's: `pack_options(roll,
beside=False)`, auto rule) for every multi-hub artifact tree; the baseline
records predate the metric.  Also returns the chosen grid, to check it equals
the baseline's.  From mcp_harness/:

  PYTHONPATH=. python ../docs/superpowers/evidence/2026-10-19-river-routing/river_corners_before.py

Writes river_corners_before.json (roll -> corners) and prints roll, grid, corners."""
import glob
import json
import os

from pleatwright import efficiency as EF
from pleatwright import pipeline as PL
from pleatwright import stick as ST

HERE = os.path.dirname(os.path.abspath(__file__))
out = {}
for p in sorted(glob.glob(os.path.join(PL.STICKS, "*.json"))):
    roll = os.path.basename(p)[:-5]
    if len(ST.contract(ST.load_roll(p, 1.0)).hubs) < 2:
        continue
    opts = PL.pack_options(roll, beside=False)
    c = PL._choose(opts, "auto", "flag")[0]
    out[roll] = EF.river_corners(c.layout)
    print(roll, c.layout.N, out[roll], flush=True)
with open(os.path.join(HERE, "river_corners_before.json"), "w") as f:
    json.dump(out, f, indent=1, sort_keys=True)
