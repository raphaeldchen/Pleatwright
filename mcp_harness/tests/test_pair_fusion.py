"""The fused-limb ranking: a defect class three metrics were blind to.

Found by the owner reading a tree sheet on 2026-09-09 -- the horse's and the
elephant's legs "only separate into right and left at the foot". Those trees
scored 6/6 exact on leaf count, exact on leaf labels, clean on the contract,
and correct on reading fidelity.

Every tree here is an ARTIFACT tree (owner rule, 2026-10-07). The defective
shapes are produced by the named edits below, each applied to an artifact
tree; the metric trees are DERIVED from the edited tree by the production
path (`artifact_trees.metric`).
"""
from __future__ import annotations

import pytest

import pair_fusion as PF
from artifact_trees import artifact_tree, metric


# --------------------------------------------------------------------------- #
# Defect edits (each applied to an artifact tree, never to a hand-made one)   #
# --------------------------------------------------------------------------- #
def _by_name(tree):
    return {n["name"]: n for n in tree["nodes"]}


def _ancestors(tree, name):
    """[name, parent, grandparent, ..., root]."""
    by, out = _by_name(tree), []
    while name is not None:
        out.append(name)
        name = by[name]["parent"]
    return out


def _dist_down(tree, top, name):
    """Authored length of the path from ancestor `top` down to `name`."""
    by, d = _by_name(tree), 0
    while name != top:
        d += by[name]["length"]
        name = by[name]["parent"]
    return d


def fuse_pair(tree, a, b):
    """DEFECT: a bilateral pair authored as ONE limb that forks at the tip.

    The exact shape prompt rule 6 names as WRONG and the owner found on the
    horse and the elephant (2026-09-09): instead of each side being its own
    chain from the body, `b`'s private chain is deleted and `b` hangs off
    `a`'s last joint. `b`'s own distance from the branch point is preserved, so
    every flap keeps its authored length from the body -- only WHERE the pair
    branches changes. Returns the edited tree (`tree` is modified in place).
    """
    up_a, up_b = _ancestors(tree, a), _ancestors(tree, b)
    lca = next(x for x in up_a if x in up_b)
    private_b = set(up_b[1:up_b.index(lca)])        # b's own joints
    pa = _by_name(tree)[a]["parent"]
    new_len = _dist_down(tree, lca, b) - _dist_down(tree, lca, pa)
    assert pa != lca and new_len > 0, "pair already branches at its tip"
    tree["nodes"] = [n for n in tree["nodes"] if n["name"] not in private_b]
    nb = _by_name(tree)[b]
    nb["parent"], nb["length"] = pa, new_len
    return tree


def prune_to_pair(tree, a, b):
    """DEFECT: a tree whose ONLY two flaps are the declared pair `a`/`b`.

    Every node not on the root path of `a` or `b` is deleted, and the pair is
    the only one declared. Used where the pair branches AT THE ROOT, so the
    root keeps degree 2 and is not itself a (third) degree-1 leaf. Returns the
    edited tree (modified in place).
    """
    keep = set(_ancestors(tree, a)) | set(_ancestors(tree, b))
    tree["nodes"] = [n for n in tree["nodes"] if n["name"] in keep]
    tree["pairs"] = [[a, b]]
    tree["leaves"] = [a, b]
    return tree


def reroot_at(tree_nodes, new_root):
    """TRANSFORM (not a defect): the same free tree, re-rooted at `new_root`.

    What the archived serve path did to the rabbit (at its TAIL). Each edge
    keeps its length; parent pointers along the old-root path are reversed, and
    the list is emitted parents-first from the new root.
    """
    adj = {n["id"]: [] for n in tree_nodes}
    for n in tree_nodes:
        if n["parent_id"] is not None:
            adj[n["id"]].append((n["parent_id"], n["length"]))
            adj[n["parent_id"]].append((n["id"], n["length"]))
    out, seen, frontier = [{"id": new_root, "parent_id": None, "length": 0.0}], \
        {new_root}, [new_root]
    while frontier:
        cur = frontier.pop(0)
        for nxt, ln in adj[cur]:
            if nxt not in seen:
                seen.add(nxt)
                frontier.append(nxt)
                out.append({"id": nxt, "parent_id": cur, "length": ln})
    return out


#: horse_1's front legs: withers -> shoulder -> knee -> fetlock -> hoof, per side.
HORSE, FRONT = "horse_1", ("hoof_L", "hoof_R")


def forked():
    """horse_1 with its front pair FUSED: root .. withers -> shoulder_L ->
    knee_L -> fetlock_L -> {hoof_L, hoof_R}. The horse's real 2026-09-09
    defect: one limb that forks at the very tip. Returns (nodes, pairs, ids)."""
    return metric(fuse_pair(artifact_tree(HORSE), *FRONT))


def separate_limbs():
    """horse_1 as authored: the same flap lengths, each front leg its own chain
    from the withers."""
    return metric(artifact_tree(HORSE))


def test_the_fuse_edit_is_what_it_claims():
    """Guards the edit itself: same flaps, same root distances, new branch point."""
    good, bad = artifact_tree(HORSE), fuse_pair(artifact_tree(HORSE), *FRONT)
    root = good["nodes"][0]["name"]
    assert sorted(good["leaves"]) == sorted(bad["leaves"])
    for leaf in good["leaves"]:
        assert _dist_down(good, root, leaf) == _dist_down(bad, root, leaf)
    assert _by_name(bad)["hoof_R"]["parent"] == _by_name(bad)["hoof_L"]["parent"]


def test_a_forked_tip_ranks_far_below_two_real_limbs():
    """The ONLY claim this module makes: the order."""
    tn, sp, _ = forked()
    bad = PF.score_fusion(tn, sp)["min_branch_fraction"]
    tn, sp, _ = separate_limbs()
    good = PF.score_fusion(tn, sp)["min_branch_fraction"]
    assert bad < good


def test_the_module_ships_no_threshold_and_no_verdict():
    """A first draft shipped FUSED_BELOW = 0.5 and scored TP 3 / FP 6 on the
    corpus. Fitting one instead would tune to three labelled positives, which
    is what ORIENTATION-NEGATIVE.md exists to warn against."""
    assert not hasattr(PF, "FUSED_BELOW")
    tn, sp, _ = forked()
    out = PF.score_fusion(tn, sp)
    assert "fused" not in out and "any_fused" not in out
    assert all("fused" not in row for row in out["pairs"])


def test_pairs_come_back_worst_first():
    """horse_1 with its HIND pair fused, declared AFTER the clean front pair,
    so a correct result must reorder them."""
    tree = fuse_pair(artifact_tree(HORSE), "hoof_hind_L", "hoof_hind_R")
    tn, _, ids = metric(tree)
    clean = [ids["hoof_L"], ids["hoof_R"]]                 # a clean pair
    fork = [ids["hoof_hind_L"], ids["hoof_hind_R"]]       # a forked pair
    out = PF.score_fusion(tn, [clean, fork])
    fr = [r["branch_fraction"] for r in out["pairs"]]
    assert fr == sorted(fr)
    assert out["pairs"][0]["pair"] == tuple(fork)


# --------------------------------------------------------------------------- #
# blind spots are reported, never swallowed                                   #
# --------------------------------------------------------------------------- #
def test_a_pair_naming_a_non_leaf_is_reported_as_unscored():
    """DEFECT edit: the pair names shoulder_L and knee_L -- two interior
    joints of the forked limb -- rather than two hooves."""
    tn, _, ids = forked()
    joints = [ids["shoulder_L"], ids["knee_L"]]
    out = PF.score_fusion(tn, [joints])
    assert out["pairs"] == []
    assert out["unscored"] == [joints]
    assert out["min_branch_fraction"] is None


def test_a_malformed_pair_is_reported_not_dropped():
    """DEFECT edit: a one-element "pair" naming only hoof_L."""
    tn, _, ids = forked()
    out = PF.score_fusion(tn, [[ids["hoof_L"]]])
    assert out["unscored"] == [[ids["hoof_L"]]]


def test_a_two_leaf_tree_has_no_reference_point():
    """With no third leaf the branch point is undefined. That must read as
    UNSCORED, never as a pass. starfish_1 pruned to its arm_L/arm_R pair,
    which branches at the disc (the root), so the root stays degree 2."""
    tn, _, ids = metric(prune_to_pair(artifact_tree("starfish_1"), "arm_L", "arm_R"))
    leaves, _ = PF.leaf_distance_matrix(tn)
    assert leaves == sorted([ids["arm_L"], ids["arm_R"]])   # the precondition
    assert PF.branch_fraction(tn, ids["arm_L"], ids["arm_R"]) is None


@pytest.mark.parametrize("roll", ["crab_3", "octopus_2", "spider_2"])
def test_a_degree_one_root_is_a_leaf(roll):
    """The serve path re-roots, and it re-rooted the rabbit AT ITS TAIL. A
    children-based leaf test then reads five leaves where the author wrote six
    and reports that the backend dropped a flap. It did not -- re-rooting is
    topologically a no-op. These artifact rolls are AUTHORED with a single-
    child root, so no edit is needed."""
    tn, _, _ = metric(artifact_tree(roll))
    root = tn[0]["id"]
    assert [n["parent_id"] for n in tn].count(root) == 1     # the precondition
    childless = [n["id"] for n in tn
                 if all(o["parent_id"] != n["id"] for o in tn)]
    leaves, _ = PF.leaf_distance_matrix(tn)
    assert leaves == sorted([root] + childless)


def test_the_score_survives_a_reroot_ONTO_A_LEAF():
    """The case `rehome` declines and the serve path performs anyway, so the
    invariance test above never exercised it. horse_1, re-rooted at its tail."""
    tn, sp, ids = separate_limbs()
    rerooted = reroot_at(tn, ids["tail"])
    assert rerooted[0]["id"] == ids["tail"] and len(rerooted) == len(tn)
    a = PF.score_fusion(tn, sp)
    b = PF.score_fusion(rerooted, sp)
    assert a["min_branch_fraction"] == b["min_branch_fraction"]
    assert PF.leaf_distance_matrix(tn)[0] == PF.leaf_distance_matrix(rerooted)[0]
