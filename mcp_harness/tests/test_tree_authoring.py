"""The authoring contract, moved into production.

The prompt and schema were an evidence script whose README says "Do not
import". These tests pin the clauses that were PAID FOR -- each one is in the
prompt because a measured run went wrong without it.
"""
from __future__ import annotations

import tree_authoring as TA
from artifact_trees import authored


def test_the_prompt_carries_every_clause_a_run_paid_for():
    s = TA.SYSTEM
    # the two-frames warning: 3 of 17 trees came back upside down without it
    assert "FLIP THE SIGN" in s
    assert "DOWNWARD" in s
    # rule 6: 3 of 17 authored one leg with a forked foot without it
    assert "EACH SIDE IS ITS OWN CHAIN" in s
    # the readings rule -- what makes fabrication visible in the artifact
    assert "READ BEFORE YOU DERIVE" in s
    # the counting convention rides here; the expected COUNT never does
    assert "LEAF CONVENTION" in s
    assert "expected_feature_count" not in s


def test_the_tool_schema_requires_direction_on_every_node():
    """Without `direction` there is no pose, the stick figure cannot be drawn,
    and the human gate has nothing to show. The 2026-09-07 run omitted it and
    its trees could only be drawn as dendrograms."""
    props = TA.TOOL[0]["function"]["parameters"]["properties"]
    node = props["nodes"]["items"]
    assert "direction" in node["properties"]
    assert set(node["required"]) == {"name", "parent", "length", "direction"}


def test_to_tuples_gives_the_root_a_null_direction():
    """dog_0 as authored: its root `body` has direction [0, 0, 0]; every other
    node keeps its own direction and length."""
    t = authored("dog_0")
    root, rest = t["nodes"][0], t["nodes"][1:]
    assert root["parent"] is None and not any(root["direction"])  # the precondition
    assert TA.to_tuples(t) == (
        [(root["name"], None, None, root["length"])]
        + [(n["name"], n["parent"], n["direction"], n["length"]) for n in rest])


def test_leaves_of_names_the_childless_nodes():
    """dog_0 has chained limbs (thigh -> hock -> paw), so a node that is
    neither the root nor a leaf is in the list."""
    t = authored("dog_0")
    names = {n["name"] for n in t["nodes"]}
    parents = {n["parent"] for n in t["nodes"]}
    assert TA.leaves_of(TA.to_tuples(t)) == [n["name"] for n in t["nodes"]
                                             if n["name"] not in parents]
    assert sorted(TA.leaves_of(TA.to_tuples(t))) == sorted(names - parents) \
        == sorted(t["leaves"])


def test_metric_tree_scales_the_longest_edge_to_the_packing_regime():
    """0.40 is LONGEST_LIMB_TARGET (formerly mesh_to_tree's, archived) -- the
    regime every TreeMaker-era tree in this project was compiled in. A tree
    built at a different scale is not comparable to any number measured there."""
    nodes = TA.to_tuples(authored("dog_0"))
    tn, pairs, names = TA.metric_tree(nodes, [])
    longest = max(n[3] for n in nodes)
    assert max(n["length"] for n in tn) == TA.LONGEST_LIMB_TARGET
    assert [n["length"] for n in tn] == \
        [round(n[3] * TA.LONGEST_LIMB_TARGET / longest, 6) for n in nodes]
    assert all(m["length"] == TA.LONGEST_LIMB_TARGET
               for n, m in zip(nodes, tn) if n[3] == longest)
    assert names == {i: n[0] for i, n in enumerate(nodes)}
    # concrete pins (dog_0), so a drift in the formula itself is caught too
    by_name = {names[i]: n["length"] for i, n in enumerate(tn)}
    assert (by_name["hip"], by_name["neck"], by_name["head"]) == (0.4, 0.2, 0.25)


def test_metric_tree_maps_pair_names_to_ids():
    t = authored("dog_0")
    nodes = TA.to_tuples(t)
    at = {n[0]: i for i, n in enumerate(nodes)}
    _, pairs, _ = TA.metric_tree(nodes, [tuple(p) for p in t["pairs"]])
    assert pairs == [[at[a], at[b]] for a, b in t["pairs"]]


def test_leaf_pairs_keeps_the_leaf_pairs_and_HANDS_BACK_the_dropped_ones():
    """The filter is forced -- prompt rule 7 and `tree_contract` both require a
    symmetric pair to join two leaves -- but a dropped pair means the compiler
    gets NO mirror constraint, so it must be returned rather than swallowed.
    Measured across all 17 committed subjects: nothing is dropped today, which
    is exactly why a silent filter would never be noticed if that changed.

    DEFECT edit: dog_0's two authored leaf pairs, plus three bad ones."""
    t = authored("dog_0")
    good = [tuple(p) for p in t["pairs"]]
    bad = [["thigh_L", "thigh_R"],              # internal joints: dropped
           ["paw_rear_L", "thigh_R"],           # half and half: dropped
           ["paw_rear_L"]]                      # malformed: dropped
    t["pairs"] = t["pairs"] + bad
    keep, dropped = TA.leaf_pairs(t, TA.leaves_of(TA.to_tuples(t)))
    assert keep == good                         # both leaves: kept
    assert dropped == bad


def test_leaf_pairs_reads_a_missing_pairs_field_as_none_declared():
    """DEFECT edits: dog_0 with its `pairs` field deleted, and set to null."""
    t = authored("dog_0")
    leaves = TA.leaves_of(TA.to_tuples(t))
    del t["pairs"]
    assert TA.leaf_pairs(t, leaves) == ([], [])
    t["pairs"] = None
    assert TA.leaf_pairs(t, leaves) == ([], [])


def test_rule_4_says_a_fused_head_is_trunk_not_a_flap():
    """2026-09-12: spider, crab and scorpion each authored a `head` flap the
    animal does not have as a protruding appendage, and that one flap was the
    whole difference between packing and the packer wall. Stated as anatomy,
    with no mention of packing."""
    s = TA.SYSTEM
    assert "LEAF CONVENTION" in s                          # the pinned token survives
    assert "ONLY when it protrudes" in s
    assert "cephalothorax or carapace" in s
    assert "TRUNK, not a flap" in s
    assert "the head counts one;" not in s                 # the old unconditional clause is gone
    assert "pack" not in s.split("4. LEAF CONVENTION")[1].split("5. STRUCTURE")[0].lower()


def test_rule_4_keeps_spider_pedipalps_out_but_scorpion_chelae_in():
    """2026-09-12 repair_rolls r2, spider #2: the model counted the pedipalps as
    a fifth leg pair (11 flaps) and the tree exhausted the ladder. A scorpion's
    pincers ARE its pedipalps, so the clause must exclude the small ones and
    keep the enlarged ones."""
    rule4 = TA.SYSTEM.split("4. LEAF CONVENTION")[1].split("5. STRUCTURE")[0]
    assert "pedipalps" in rule4
    assert "FOUR leg pairs, never five" in rule4
    assert "chelae of scorpions" in rule4
    assert "pack" not in rule4.lower()
