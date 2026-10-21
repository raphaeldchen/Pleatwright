"""Secondary signal: does each mesh still author a tree that folds? (spec §2.4)

Reported, never used to decide. The authored leaf count is compared with the
subject's ARTIFACT trees, not the manifest: gated_pipeline authors with
tree_authoring's convention (a scorpion's pincers are limbs -> 11), which is
the convention those 51 trees follow, while the manifest says 9.
"""
from __future__ import annotations

import glob
import json
import os
from collections import Counter

import gated_pipeline
from concept_ab import arms as A
from concept_ab.review import cells
from pleatwright import pipeline
from pleatwright.__main__ import tree_file

_STICKS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "fixtures", "full17_v3_sticks")


def _leaves(nodes) -> int:
    parents = {n.get("parent") for n in nodes}
    return sum(1 for n in nodes if n["name"] not in parents)


def artifact_leaf_count(subject: str) -> int:
    """The most common leaf count across the subject's artifact trees."""
    counts = [_leaves(json.load(open(p))["nodes"])
              for p in sorted(glob.glob(os.path.join(_STICKS, A.slug(subject) + "_*.json")))]
    return Counter(counts).most_common(1)[0][0]


async def tree_signal(root: str, client, *, only=None) -> dict:
    """Author (no human gate) and fold each meshed cell; cells already done are skipped."""
    out = {}
    for arm, subject, r, cell in cells(root):
        cid = A.cell_id(arm, subject, r)
        dest = os.path.join(cell, "tree_signal.json")
        if (only and cid not in only) or os.path.exists(dest):
            continue
        expected = artifact_leaf_count(subject)
        sig = {"leaves": None, "expected": expected, "match": False, "folded": False,
               "failure": None}
        work = os.path.join(cell, "tree")
        os.makedirs(work, exist_ok=True)
        state = await gated_pipeline.start(os.path.join(cell, "mesh.glb"), client=client,
                                           out_dir=work)
        if state.get("status") != "awaiting_review" or not state.get("tree"):
            sig["failure"] = f"authoring: {state.get('note') or state.get('status')}"
        else:
            sig["leaves"] = _leaves(state["tree"]["nodes"])
            sig["match"] = sig["leaves"] == expected
            tree_path = os.path.join(work, "tree.json")
            with open(tree_path, "w") as f:
                json.dump(tree_file(state, subject), f, indent=1)
            try:
                rec = pipeline.run(tree_path, os.path.join(cell, "fold"), verbose=False)
                if "failure" in rec:
                    sig["failure"] = f"fold: {rec['failure']}"
                else:
                    sig["folded"] = True
            except pipeline.StageError as e:
                sig["failure"] = f"fold: {e.stage}"
        with open(dest, "w") as f:
            json.dump(sig, f, indent=1)
        out[cid] = sig
    return out
