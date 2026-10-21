"""Branching-packer probe (spec 2026-10-10 §4): every branching named edit
through the full pipeline. Run from mcp_harness/:

    PYTHONPATH=.:tests $PY ../docs/superpowers/evidence/2026-10-10-branching-packer/probe_branching.py OUT

Writes the model folders under OUT/<edit>_<roll>/ and one JSON line per tree
to records.jsonl beside this script. Trees: named edits of the 51 artifact
trees only (CLAUDE.md §5)."""
import glob
import json
import os
import sys
import time

from artifact_trees import ROLLS, artifact_tree
from pleatwright import pack as PK
from pleatwright import pipeline as PL
from pleatwright import stick as ST
from test_pack_chain import antlered, lopsided, toed

HERE = os.path.dirname(os.path.abspath(__file__))
DELIVERED = os.path.expanduser("~/Desktop/origami_samples_artifact_trees")
EDITS = (("antlered", antlered), ("toed", toed), ("lopsided", lopsided))


def branching(tree):
    _, nb = PK._hub_graph(ST.contract(ST.load_tree(tree, 1.0)))
    return any(len(v) > 2 for v in nb.values())


def unedited_grid(roll):
    """The grid of the delivered model of the unedited roll."""
    title = PL.title_of(ST.load_tree(artifact_tree(roll), 1.0))
    hits = [p for p in glob.glob(os.path.join(DELIVERED, glob.escape(title) + "_*"))
            if os.path.isdir(p)]
    return int(hits[0].rsplit("_", 1)[1]) if len(hits) == 1 else None


def main(out):
    with open(os.path.join(HERE, "records.jsonl"), "w") as rec_f:
        for edit, fn in EDITS:
            for roll in ROLLS:
                try:
                    tree = fn(roll)
                except (KeyError, ValueError, StopIteration):
                    continue                     # the edit does not apply to this roll
                if not branching(tree):
                    continue
                d = os.path.join(out, f"{edit}_{roll}")
                os.makedirs(d, exist_ok=True)
                path = os.path.join(d, "tree.json")
                with open(path, "w") as f:
                    json.dump(tree, f)
                t0 = time.perf_counter()
                row = {"edit": edit, "roll": roll, "unedited_grid": unedited_grid(roll)}
                try:
                    rec = PL.run(path, d, certify_global=True, verbose=False)
                    row.update({k: rec.get(k) for k in (
                        "failure", "packing_rung", "grid_size", "pack_tried", "pack_secs",
                        "solving_flat_foldable", "global_verdict", "tree_similarity", "folder")})
                except PL.StageError as e:
                    row.update({"failure": e.stage, "error": str(e)})
                row["secs"] = round(time.perf_counter() - t0, 1)
                rec_f.write(json.dumps(row) + "\n")
                rec_f.flush()
                print(edit, roll, row.get("failure") or row.get("grid_size"), flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
