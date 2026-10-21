"""The pre-registered bar for layer certification, measured.

Run from `mcp_harness/`:
  PYTHONPATH=. ../.venv/bin/python \
    ../docs/superpowers/evidence/2026-09-20-box-pleat/oracle-census/certify_corpus.py OUT.json

~15.7 min: dog 537 s and guinea_pig 285 s dominate, as they do for every
probe on this corpus. Rows are written after each subject so the fast ones
land while the big ones run.
"""
from __future__ import annotations
import json, sys, time

from box_pleat.compile import compile_tree

RULE6 = ("../docs/superpowers/evidence/2026-09-08-vlm-tree-authoring"
         "/data/rule6_serve.json")
OUT = sys.argv[1]
ORDER = ["starfish", "bird", "lizard", "horse", "octopus", "frog",
         "guinea_pig", "dog"]


def main():
    entries = {e["subject"]: e for e in json.load(open(RULE6))}
    rows = []
    for s in ORDER:
        t0 = time.time()
        res = compile_tree(entries[s]["requested"], entries[s]["pairs"])
        v = res.verdict
        rows.append({"subject": s, "stage_reached": res.stage_reached,
                     "kind": None if v is None else v.kind,
                     "nodes": None if v is None else v.nodes,
                     "free": None if v is None else v.free,
                     "tried": res.layers_tried,
                     "secs": round(time.time() - t0, 1)})
        json.dump(rows, open(OUT, "w"), indent=1)
        print(f"{s:11s} {res.stage_reached:8s} "
              f"{rows[-1]['kind']} free={rows[-1]['free']} "
              f"nodes={rows[-1]['nodes']} {rows[-1]['secs']}s", flush=True)


main()
