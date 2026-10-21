"""Slice 7: the tree_contract symbolic contract check.

Two things are pinned here that are easy to get wrong in opposite directions:
the ERROR set must catch every malformation before a tree reaches the human
review or Pleatwright, and the WARNING set must stay quiet on known-good
shapes -- a validator that warns on good trees teaches the model that
warnings are noise, which is worse than having none.

Every tree here is an ARTIFACT tree (owner rule, 2026-10-07): the id-based
metric tree is DERIVED from it by the production path
(`artifact_trees.metric`), and each malformation is a named edit below applied
to that derived list.
"""
import math

import pytest
import tree_contract as tc
from artifact_trees import ROLLS, artifact_tree, metric

#: The quadruped every malformation is applied to. Its root `body` has the
#: children neck, hip, shoulder_L, shoulder_R; `neck` -> `head` is a chain.
BASE = "dog_0"


def _base():
    """(tree_nodes, symmetric_pairs, ids) derived from the BASE artifact tree."""
    return metric(artifact_tree(BASE))


def _node(nodes, nid):
    return next(n for n in nodes if n["id"] == nid)


# --------------------------------------------------------------------------- #
# Malformation edits (each applied to the derived BASE metric tree)           #
# --------------------------------------------------------------------------- #
def rename_parent_id_to_parent(nodes, ids):
    """DEFECT: `neck` carries `parent` instead of `parent_id` -- the field
    name the retired prompt prose warned about."""
    n = _node(nodes, ids["neck"])
    n["parent"] = n.pop("parent_id")
    return nodes


def child_before_parent(nodes, ids):
    """DEFECT: `head` is moved to sit immediately BEFORE its parent `neck`."""
    head = _node(nodes, ids["head"])
    nodes.remove(head)
    nodes.insert(nodes.index(_node(nodes, ids["neck"])), head)
    return nodes


def duplicate_id(nodes, ids):
    """DEFECT: `neck` reuses the root's id."""
    _node(nodes, ids["neck"])["id"] = ids["body"]
    return nodes


def drop_root(nodes, ids):
    """DEFECT: the root node is deleted, so its children name a missing parent."""
    return [n for n in nodes if n["id"] != ids["body"]]


def second_root(nodes, ids):
    """DEFECT: the `hip` subtree is detached as a second root."""
    _node(nodes, ids["hip"])["parent_id"] = None
    return nodes


def _set_length(value):
    def edit(nodes, ids):
        _node(nodes, ids["head"])["length"] = value
        return nodes
    edit.__doc__ = f"DEFECT: `head`'s length is set to {value!r}."
    edit.__name__ = f"head_length_{value!r}"
    return edit


def no_length(nodes, ids):
    """DEFECT: `head` has no `length` key at all."""
    del _node(nodes, ids["head"])["length"]
    return nodes


def root_into_cycle(nodes, ids):
    """DEFECT: the root names its own child `neck` as parent -- a 2-cycle
    body <-> neck, leaving no node with a null parent."""
    _node(nodes, ids["body"])["parent_id"] = ids["neck"]
    return nodes


# --------------------------------------------------------------------------- #
# Errors: the malformations that reach (and kill) the C++ builder             #
# --------------------------------------------------------------------------- #
def test_the_base_is_clean():
    """Every error below is caused by its edit, not by the base tree."""
    tn, sp, _ = _base()
    r = tc.check(tn, sp)
    assert r["ok"] is True and r["errors"] == []


def test_missing_parent_id_is_an_error_and_names_the_field():
    """The single most expensive malformation, and the one the retired prompt
    prose warned about: `parent` instead of `parent_id`. The engine does not
    survive it and no retry recovers, so the message names the right field."""
    tn, _, ids = _base()
    r = tc.check(rename_parent_id_to_parent(tn, ids))
    assert r["ok"] is False
    assert any("parent_id" in e and "`parent`" in e for e in r["errors"])


def test_child_before_parent_is_an_error():
    """Not a style rule: the engine reads the list in order and seeds each
    node's placement from its position."""
    tn, _, ids = _base()
    r = tc.check(child_before_parent(tn, ids))
    assert r["ok"] is False
    assert any("must appear AFTER its parent" in e for e in r["errors"])


#: The two inputs that are NOT trees at all (an empty list, a string) stay as
#: literals: there is no artifact tree to start from when the defect is
#: "there is no tree".
@pytest.mark.parametrize("nodes,fragment", [
    ([], "non-empty list"),
    ("nope", "non-empty list"),
])
def test_non_tree_inputs_are_errors(nodes, fragment):
    r = tc.check(nodes)
    assert r["ok"] is False
    assert any(fragment in e for e in r["errors"]), r["errors"]


@pytest.mark.parametrize("edit,fragment", [
    (duplicate_id, "duplicate node id"),
    (drop_root, "not a node in this list"),
    (second_root, "2 roots"),
    (_set_length(0), "must be > 0"),
    (_set_length("x"), "is not a finite number"),
    # NaN and Infinity: json.loads accepts the bare tokens, so a model's tool
    # arguments can carry one, and `nan <= 0` is False -- a plain positivity
    # check waves it through to the engine. (Adversarial review.)
    (_set_length(math.nan), "finite"),
    (_set_length(math.inf), "finite"),
    (_set_length(-math.inf), "finite"),
    (no_length, "has no 'length'"),
], ids=lambda v: getattr(v, "__name__", v) if callable(v) else None)
def test_malformations_are_errors(edit, fragment):
    tn, _, ids = _base()
    r = tc.check(edit(tn, ids))
    assert r["ok"] is False
    assert any(fragment in e for e in r["errors"]), r["errors"]


def test_no_root_is_an_error():
    tn, _, ids = _base()
    r = tc.check(root_into_cycle(tn, ids))
    assert r["ok"] is False
    # a 2-cycle has no root; either diagnosis is correct and both are useful
    assert any("no root" in e or "not reachable" in e for e in r["errors"])


def test_pair_naming_a_non_leaf_is_an_error():
    """DEFECT edit: a pair joining the interior joint `shoulder_L` to the leaf
    `paw_front_R`."""
    tn, _, ids = _base()
    r = tc.check(tn, [[ids["shoulder_L"], ids["paw_front_R"]]])
    assert r["ok"] is False
    assert any("not a LEAF" in e for e in r["errors"])


def test_a_leaf_in_two_pairs_is_an_error():
    """DEFECT edit: the authored pairs plus a third pair that re-uses
    `paw_front_R` (already paired with paw_front_L)."""
    tn, sp, ids = _base()
    r = tc.check(tn, sp + [[ids["paw_front_R"], ids["paw_rear_L"]]])
    assert r["ok"] is False
    assert any("more than one symmetric pair" in e for e in r["errors"])


def test_errors_short_circuit_before_id_indexed_checks():
    """A duplicate/absent id makes every later by-id lookup meaningless;
    reporting cascading nonsense on top of the real fault trains the reader to
    skim past it."""
    tn, _, ids = _base()
    r = tc.check(duplicate_id(tn, ids))
    assert r["ok"] is False
    assert len(r["errors"]) == 1


# --------------------------------------------------------------------------- #
# Warnings: measured risk factors, never vetoes                               #
# --------------------------------------------------------------------------- #


def test_missed_bilateral_pair_is_warned_but_midline_flaps_are_not():
    """Two UNPAIRED leaves sharing a hub AND a length is the shape of a
    missed pair. One unpaired leaf on a hub is a head or a tail."""
    # octopus_0: eight arm flaps arm{1..4}_base_{L,R}, all length 1 on hub
    # `head`. DEFECT edit: only arms 1 and 2 are declared as pairs, so arms 3
    # and 4 are four unpaired leaves sharing that hub and length.
    tn, _, ids = metric(artifact_tree("octopus_0"))
    pairs = [[ids["arm1_base_L"], ids["arm1_base_R"]],
             [ids["arm2_base_L"], ids["arm2_base_R"]]]
    missed = sorted(ids[f"arm{k}_base_{s}"] for k in (3, 4) for s in "LR")
    r = tc.check(tn, pairs)
    hit = [w for w in r["warnings"] if "no symmetric pair" in w]
    assert hit and str(missed) in hit[0]

    # Known-good, as authored: an unpaired midline flap that shares its hub
    # AND its length with PAIRED flaps must stay silent. starfish_1's `arm_top`
    # (unpaired) sits on the disc at length 12 beside the paired arm_L,
    # arm_BL and arm_BR (also 12). The quadruped stands in for the retired
    # body_plans.template("quadruped") this test used to inline.
    for roll in ("starfish_1", BASE):
        tn, sp, ids = metric(artifact_tree(roll))
        assert not [w for w in tc.check(tn, sp)["warnings"]
                    if "no symmetric pair" in w], roll
    tn, sp, ids = metric(artifact_tree("starfish_1"))
    top = _node(tn, ids["arm_top"])
    paired = {i for p in sp for i in p}
    assert ids["arm_top"] not in paired                  # the precondition
    assert any(n["parent_id"] == top["parent_id"] and n["length"] == top["length"]
               and n["id"] in paired for n in tn)


def test_no_packing_window_warning_exists():
    """No artifact tree -- up to scorpion's 11 flaps -- draws a packing-window
    warning, even with no pairs declared."""
    for roll in ROLLS:
        tn, _, _ = metric(artifact_tree(roll))
        r = tc.check(tn)
        assert r["ok"] is True, roll
        assert not any("packable window" in w for w in r["warnings"]), roll


def test_no_pairs_at_all_is_warned():
    """DEFECT edit: BASE (six flaps) with its symmetric pairs left undeclared."""
    tn, _, _ = _base()
    r = tc.check(tn)
    assert r["ok"] is True
    assert any("no symmetric_pairs" in w for w in r["warnings"])
