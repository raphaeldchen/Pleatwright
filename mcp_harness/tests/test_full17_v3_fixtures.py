"""Integrity of the committed full17_v3 corpus (spec 2026-09-16 §3): the 51
packed 'Bases in Triplicate III' trees, copied from the untracked roll
directory so a corpus number can be claimed against bytes in the repo."""
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(HERE, "..", "fixtures", "full17_v3_trees")
EXPECTED = 51
ROLL_FILES = sorted(glob.glob(os.path.join(CORPUS, "*_[0-9].json")))


def _leaf_ids(nodes):
    deg = {int(n["id"]): 0 for n in nodes}
    for n in nodes:
        if n.get("parent_id") is not None:
            deg[int(n["id"])] += 1
            deg[int(n["parent_id"])] += 1
    return {i for i, d in deg.items() if d == 1}


def test_corpus_has_51_rolls_and_a_matching_index():
    assert len(ROLL_FILES) == EXPECTED
    with open(os.path.join(CORPUS, "index.json")) as f:
        idx = json.load(f)
    assert idx["count"] == EXPECTED
    assert [r["roll"] for r in idx["rolls"]] == \
        [os.path.basename(p)[:-5] for p in ROLL_FILES]
    assert len({r["subject"] for r in idx["rolls"]}) == 17


def test_every_roll_is_well_formed():
    for path in ROLL_FILES:
        with open(path) as f:
            rec = json.load(f)
        roll = os.path.basename(path)[:-5]
        assert rec["roll"] == roll
        assert rec["subject"] == roll.rsplit("_", 1)[0]
        ids = [int(n["id"]) for n in rec["tree_nodes"]]
        assert len(ids) == len(set(ids))
        leaves = _leaf_ids(rec["tree_nodes"])
        for a, b in rec["symmetric_pairs"]:
            assert int(a) in leaves and int(b) in leaves, (roll, a, b)
        assert rec["names"][str(ids[0])]
        assert rec["leaves"]
