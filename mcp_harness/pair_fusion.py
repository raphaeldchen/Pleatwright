"""Are a bilateral pair's two limbs actually two limbs?

WHY THIS EXISTS
---------------
Found 2026-09-09 by the repository owner, reading a rendered tree sheet: the
horse's and the elephant's legs "only separate into right and left at the
foot". Measured, the horse's hind pair is **2 units of 22** apart -- one hind
leg with a forked hoof -- and the elephant's front pair is 4 of 27.

Every metric this project owns scored those trees CLEAN. Leaf count: 6/6 exact.
Leaf labels: exact. Reading fidelity: the coordinates were read off the mesh
correctly. Contract: no errors. The defect is in the TOPOLOGY -- where the pair
branches -- and nothing was looking there.

It is not cosmetic. A tree-method base (TreeMaker's then, Pleatwright's now)
packs a flap per leaf and the flap's length is measured from its branch point,
so a horse whose front legs diverge at the fetlock compiles to two 3-unit stubs
hanging off one 12-unit shared limb. That is a different animal, and it packs
like one.

WHY THE DEFINITION USES ONLY LEAF-TO-LEAF DISTANCES
---------------------------------------------------
The obvious formulation -- "how far down the path from the ROOT do they split"
-- is unusable here, because the root is not a property of the animal. The
TreeMaker-era rescue ladder's flatten and re-root stages (archived) both
changed it by design, so a root-relative score would move when the packer's
bookkeeping moved and the anatomy had not.

So this is built from the leaf-to-leaf distance matrix alone, via the standard
three-point median: for leaves a, b and a reference leaf c, the branch point m
of (a, b, c) sits at

    d(a, m) = (d_ab + d_ac - d_bc) / 2        d(c, m) = (d_ac + d_bc - d_ab) / 2

`separate` is d(a, m) -- the part of the limb that is this side's alone --
and `shared` is the smallest d(c, m) over every other leaf, i.e. how far the
branch point sits from the nearest of the rest of the animal.

That makes the score invariant under EXACTLY the transformations S4's variant
search is allowed to perform (node order, re-rooting, lossless degree-2
collapse), all of which preserve the leaf-to-leaf distances and none of which
may change the anatomy. The same number before and after a rescue is not a
coincidence; it is the point.

⚠ THIS IS A RANKING, NOT A TEST. THERE IS DELIBERATELY NO THRESHOLD.
--------------------------------------------------------------------
`branch_fraction` = separate / (separate + shared), in [0, 1]. Higher is more
independent. What is VALIDATED is the ORDER, and only the order.

Measured on the 17-subject corpus against the three subjects the owner flagged
by eye (horse, elephant, guinea pig), they come back as the three LOWEST scores
with a gap beneath the rest:

    horse 0.065 · elephant 0.143 · guinea pig 0.269 | dolphin 0.333 ... spider 0.750

A first draft of this module shipped `FUSED_BELOW = 0.5`, justified as the
statable rule "more of the limb is shared than separate". On the same corpus
that rule scored **TP 3, FP 6** -- it flagged the cat, the bat, the bird, the
dolphin, the lizard and the scorpion, all of which branch correctly at the
body. The rule sounds principled and is not: `shared` is measured to the
NEAREST OTHER LEAF, so the absolute value depends on how long the rest of the
animal's limbs are, and it does not transfer between body plans.

Fitting a threshold instead -- 0.30 separates this corpus perfectly -- would be
tuning to THREE labelled positives. This repository has done that before and
paid for it: two orientation detectors were tuned and both failed validation
(`evidence/2026-09-08-vlm-tree-authoring/ORIENTATION-NEGATIVE.md`), and the
lesson recorded there was to stop rather than tune a third signal.

So this module SORTS and REPORTS. It does not decide. The human approval gate
looks at the worst-ranked pairs; if a threshold is ever wanted, it needs a
corpus with enough labelled positives to fit and hold out.
"""
from __future__ import annotations

import itertools

def leaf_distance_matrix(tree_nodes) -> tuple[list, dict]:
    """(leaf ids, {(lo, hi): path length}) for every pair of leaves."""
    par = {n["id"]: n.get("parent_id") for n in tree_nodes}
    ln = {n["id"]: float(n.get("length") or 0.0) for n in tree_nodes}

    # ⚠ A LEAF IS A DEGREE-1 VERTEX OF THE FREE TREE, NOT A NODE WITH NO
    # CHILDREN. The two agree on every ordinary tree and disagree on exactly
    # one case: a root that has a single child. It is degree 1, so it is a
    # flap, and a children-based test silently drops it.
    #
    # That case was not hypothetical -- the archived TreeMaker serve path
    # produced it. Measured
    # 2026-09-09: the rabbit was re-rooted AT ITS TAIL, and a children-based
    # reading said the served tree had five leaves against the author's six,
    # i.e. that the backend had quietly dropped a flap. It had not; all six
    # degree-1 vertices survive, because re-rooting is topologically a no-op.
    # The children-based lens invented the defect.
    #
    # This matters here specifically because this module CLAIMS root
    # invariance. With the old lens that claim was false for exactly the
    # re-roots that serve path performed, and the test that was supposed to
    # pin it passed only because `rescue_ladder.rehome` declined leaf targets
    # and therefore never exercised the case.
    deg: dict = {}
    for i, p in par.items():
        deg.setdefault(i, 0)
        if p is not None:
            deg[i] = deg.get(i, 0) + 1
            deg[p] = deg.get(p, 0) + 1
    leaves = [i for i, d in deg.items() if d == 1]

    def to_root(i):
        out, acc, c, guard = {}, 0.0, i, len(par) + 1
        while c is not None and guard >= 0:
            guard -= 1
            out[c] = acc
            acc += ln.get(c, 0.0)
            c = par.get(c)
        return out

    up = {i: to_root(i) for i in leaves}
    d = {}
    for a, b in itertools.combinations(sorted(leaves), 2):
        common = set(up[a]) & set(up[b])
        if not common:                      # disconnected: not a tree
            continue
        best = min(up[a][c] + up[b][c] for c in common)
        d[(a, b)] = best
    return sorted(leaves), d


def _d(dist, a, b):
    return dist.get((a, b), dist.get((b, a)))


def branch_fraction(tree_nodes, a, b) -> dict | None:
    """How much of this pair's limb is its own, rather than shared.

    Returns None when the pair is unscoreable -- a member is not a leaf, or the
    tree has fewer than three leaves so no reference point exists. None is not
    a pass: a caller reporting a score must say how many pairs it could not
    score.
    """
    leaves, dist = leaf_distance_matrix(tree_nodes)
    if a not in leaves or b not in leaves:
        return None
    d_ab = _d(dist, a, b)
    if d_ab is None:
        return None
    others = [c for c in leaves if c not in (a, b)]
    if not others:
        return None
    separate = None
    shared = None
    for c in others:
        d_ac, d_bc = _d(dist, a, c), _d(dist, b, c)
        if d_ac is None or d_bc is None:
            continue
        sh = (d_ac + d_bc - d_ab) / 2.0
        sep = (d_ab + d_ac - d_bc) / 2.0
        if shared is None or sh < shared:
            shared, separate = sh, sep
    if shared is None:
        return None
    total = separate + shared
    frac = 1.0 if total <= 0 else max(0.0, min(1.0, separate / total))
    return {"pair": (a, b), "separate": round(separate, 6),
            "shared": round(shared, 6), "branch_fraction": round(frac, 4)}


def score_fusion(tree_nodes, symmetric_pairs) -> dict:
    """Every pair's branch fraction, WORST FIRST, and the minimum.

    Returns no verdict and no boolean -- see the module docstring. A caller
    that wants one is choosing a threshold this corpus cannot justify, and
    should say so in its own code rather than inherit it from here.

    `unscored` is reported rather than dropped: a pair that could not be scored
    is a gap in the check, and a metric that silently ignores its own blind
    spots is how this project has been bitten before.
    """
    rows, unscored = [], []
    for p in (symmetric_pairs or []):
        if len(p) != 2:
            unscored.append(list(p))
            continue
        r = branch_fraction(tree_nodes, p[0], p[1])
        (rows if r else unscored).append(r if r else list(p))
    rows.sort(key=lambda r: r["branch_fraction"])
    fr = [r["branch_fraction"] for r in rows]
    return {"pairs": rows, "unscored": unscored,
            "min_branch_fraction": (min(fr) if fr else None)}
