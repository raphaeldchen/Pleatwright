"""Named edits of artifact trees for the branching packer (spec
docs/superpowers/specs/2026-10-10-branching-hub-packer-design.md), and the
path-shaped precondition that keeps the 51 artifact outputs byte-identical."""
import copy

import pytest

from artifact_trees import ROLLS, artifact_tree
from pleatwright import stick as ST
from pleatwright.pack import PackError, hub_pairs, hub_path


def antlered(roll="dog_0"):
    """DEFECT (named, applied to an artifact tree): give the head two antlers that
    each fork into a beam and a palm, the shape of the 2026-10-10 'moose' run.
    `head` then joins three branch points (the body and the two antler bases)."""
    t = artifact_tree(roll)
    for side in "LR":
        t["nodes"].append({"name": f"antler_{side}", "parent": "head", "length": 2,
                           "direction": [0, 1, 1 if side == "L" else -1]})
        for tip in ("beam", "palm"):
            t["nodes"].append({"name": f"antler_{side}_{tip}", "parent": f"antler_{side}",
                               "length": 3, "direction": [0, 1, 0]})
    t["leaves"] = [x for x in t["leaves"] if x != "head"] + \
        [f"antler_{s}_{tip}" for s in "LR" for tip in ("beam", "palm")]
    t["pairs"] = t["pairs"] + [["antler_L_beam", "antler_R_beam"], ["antler_L_palm", "antler_R_palm"]]
    return t


def _toe(t):
    """DEFECT (named): each leaf of the tree's longest declared leaf pair gets an
    inner and an outer toe (length 2), paired across, so the pair's hub gains a
    mirrored pair of hub children. Pairs naming nodes the tree lacks (octopus)
    are skipped; a tree with no usable pair raises ValueError."""
    t = copy.deepcopy(t)
    length = {n["name"]: n["length"] for n in t["nodes"]}
    leaves = set(t["leaves"])
    usable = [p for p in t["pairs"] if p[0] in leaves and p[1] in leaves
              and p[0] in length and p[1] in length]
    a, b = max(usable, key=lambda p: length[p[0]])
    for leaf in (a, b):
        for toe in ("inner", "outer"):
            t["nodes"].append({"name": f"{leaf}_{toe}", "parent": leaf, "length": 2,
                               "direction": [0, -1, 0]})
    t["leaves"] = [x for x in t["leaves"] if x not in (a, b)] + \
        [f"{x}_{toe}" for x in (a, b) for toe in ("inner", "outer")]
    t["pairs"] = t["pairs"] + [[f"{a}_inner", f"{b}_inner"], [f"{a}_outer", f"{b}_outer"]]
    return t


def toed(roll="dog_0"):
    """`_toe` applied to an artifact tree."""
    return _toe(artifact_tree(roll))


def lopsided(roll="dog_0"):
    """DEFECT (named): `antlered` with the right antler's river 3 instead of 2, so
    the two antlers are NOT a hub pair (unpaired sibling hubs)."""
    t = antlered(roll)
    next(n for n in t["nodes"] if n["name"] == "antler_R")["length"] = 3
    return t


def odd_antlers(roll="dog_0"):
    """DEFECT (named): `antlered` with both antler rivers 3 (odd), still paired."""
    t = antlered(roll)
    for n in t["nodes"]:
        if n["name"] in ("antler_L", "antler_R"):
            n["length"] = 3
    return t


def _hub_pair_names(t):
    con = ST.contract(ST.load_tree(t, 1.0))
    return {(con.chains[a].v, con.chains[b].v) for a, b, _ in hub_pairs(con)}


def test_hub_pairs_are_derived_from_leaf_pairs():
    assert _hub_pair_names(antlered()) == {("antler_L", "antler_R")}
    assert _hub_pair_names(toed("dog_0")) == {("paw_front_L", "paw_front_R")}
    assert _hub_pair_names(lopsided()) == set()


def test_a_hub_pair_maps_every_chain_of_both_subtrees():
    con = ST.contract(ST.load_tree(antlered(), 1.0))
    (_, _, m), = hub_pairs(con)
    names = {con.chains[k].v: con.chains[v].v for k, v in m.items()}
    assert names == {"antler_L": "antler_R", "antler_R": "antler_L",
                     "antler_L_beam": "antler_R_beam", "antler_R_beam": "antler_L_beam",
                     "antler_L_palm": "antler_R_palm", "antler_R_palm": "antler_L_palm"}


def test_hub_pairs_ignore_pair_orientation_and_node_order():
    """Review focus 1: a VLM may list a pair right-first, or a mirrored subtree's
    children in a different order."""
    t = antlered()
    t["pairs"] = [p[::-1] for p in t["pairs"]]
    right = [n for n in t["nodes"] if n["name"].startswith("antler_R_")]
    t["nodes"] = [n for n in t["nodes"] if not n["name"].startswith("antler_R_")] + right[::-1]
    assert _hub_pair_names(t) == {("antler_L", "antler_R")}


def test_every_artifact_tree_is_path_shaped():
    """The 51 keep pack.py's band code, so their outputs stay byte-identical."""
    for r in ROLLS:
        hub_path(ST.contract(ST.load_tree(artifact_tree(r), 1.0)))


def test_hub_path_still_refuses_a_branching_hub_graph():
    """pack.candidates sends these to nest.py; hub_path itself is unchanged."""
    with pytest.raises(PackError, match="not a path"):
        hub_path(ST.contract(ST.load_tree(antlered(), 1.0)))
