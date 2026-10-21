"""Symbolic pre-execution contract check for a metric tree.

Slice 7. The prompt used to carry this as prose the model had to remember and
apply ("each node needs `parent_id` (not `parent`)", "every other node names a
parent that appears earlier in the list", "a node missing parent_id builds a
malformed tree that crashes the engine, which no retry can recover"). Prose
cannot be enforced; a function can. Prior art: symbolic pre-execution contract
checking in EDA agent loops (arXiv 2604.18834) took multi-step pass rate from
30% to 84% and halved tool calls by rejecting malformed calls before the
expensive backend ever saw them.

TWO SEVERITIES, AND THE SPLIT IS THE WHOLE DESIGN
--------------------------------------------------
`errors`   the tree is MALFORMED: the engine would crash, hang, or reject it
           on definition rather than on packing. These are facts about the
           data structure, not predictions about geometry.
`warnings` the tree is well-formed but carries a MEASURED risk factor. Never
           blocking, and every one quotes the measurement it rests on.

Nothing here predicts packability. Pleatwright's packer
(`pleatwright/pack.py`) decides that, and its ladder ends at doubled lengths.

★ WHY THERE IS NO ROOT-DEGREE ERROR, AND WHY THAT IS A CORRECTION

The retired prompt asserted, as template rule (1), that "a root carrying
four-plus branches reliably fails (POLYS_MULTIPLE_IBPS, a topology degeneracy
no length change can fix)". The repo's OWN committed evidence falsifies both
halves. `fixtures/s5_engine_repair_evidence.json -> packability_control`
(now on archive/treemaker-box-pleat) is the TreeMaker compile rate of a k-leaf
STAR -- which is precisely a root with k children -- under length jitter:

    k=4  3/3 at 0% jitter, 2/20 at 1%, 20/20 at 30%
    k=5  3/3 at 0%,                    16/20 at 30%
    k=6  3/3 at 0%,                    15/20 at 30%
    k=7  0/3 at 0%,  15/20 at 1%,      10/20 at 30%
    k=8  3/3 at 0%,                     7/20 at 30%

Four-, five-, six- and eight-child roots all pack 3/3 at equal lengths, so
"reliably fails" is false; and k=4 moves 3/3 -> 2/20 -> 20/20 while k=7 moves
0/3 -> 15/20 purely by CHANGING LENGTHS, so "no length change can fix" is
false in the exact opposite direction. The one k that fails at equal lengths
is 7, which the rule does not single out.

This is not a theoretical objection. A captured live agent turn
(docs/superpowers/evidence/2026-07-25-cp-audit-smoke/haiku45-frames.jsonl,
frame 22) quotes the rule verbatim -- 'violates the KNOWN-GOOD RULE #1: "a
root carrying four-plus branches reliably fails"' -- to REFUSE the measured
reference candidate for the dog and demand a template redesign, concluding
"This reference tree will not pack cleanly on a unit square regardless of
edge-length tuning." S3 then served that same dog at 6/6 leaves, both pairs,
zero proportion drift, via placement seeding. The prompt's own guardrail
forbids exactly that move ("PROPORTIONS ... are MEASURED -- do NOT rescale
them or re-invent the symmetry to force a pack"), and a falsified rule
overrode it.

So coding the cap as an ERROR would freeze a refuted number into a tool and
make the harm harder to see, not easier. `structural_prefilter`'s
MAX_ROOT_CHILDREN (archived with the skeleton extractor) had its own separate
job -- ranking EXTRACTOR candidates, where it was a cheap heuristic among many
and no agent read it as doctrine.
Here the root degree is reported only as an OBSERVATION
(`observations["root_children"]`): no error and no warning, because the
measurements above show no root-degree threshold worth either.
"""
from __future__ import annotations

import math
from typing import Any


def _is_num(v: Any) -> bool:
    """A real, finite number. NaN and +/-Infinity are excluded DELIBERATELY.

    `json.loads` accepts the bare tokens NaN / Infinity, so a model's tool
    arguments can carry one, and `nan <= 0` is False -- so a plain positivity
    check waves it straight through to the engine while the prompt says
    "ok:true with warnings is fine to compile". (Adversarial review.)
    """
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return False
    return math.isfinite(v)


def check(tree_nodes: Any,
          symmetric_pairs: Any = None) -> dict:
    """Validate a metric tree. Returns a JSON-ready verdict dict.

    {
      "ok": bool,                 # no ERRORS (warnings do not block)
      "errors":   [str, ...],     # malformed: do not send this to the engine
      "warnings": [str, ...],     # well-formed but measured-risky
      "observations": {...},      # counts the agent may want
    }
    """
    errors: list[str] = []
    warnings: list[str] = []
    obs: dict = {}

    # ---- shape -----------------------------------------------------------
    if not isinstance(tree_nodes, list) or not tree_nodes:
        return {"ok": False,
                "errors": ["tree_nodes must be a non-empty list of node "
                           "dicts (see describe_tree_format)"],
                "warnings": [], "observations": {}}

    ids: list = []
    for i, n in enumerate(tree_nodes):
        if not isinstance(n, dict):
            errors.append(f"node at index {i} is {type(n).__name__}, not a "
                          "dict")
            continue
        if "id" not in n:
            errors.append(f"node at index {i} has no 'id'")
            continue
        nid = n["id"]
        if not isinstance(nid, int) or isinstance(nid, bool):
            errors.append(f"node at index {i}: id {nid!r} is not an int")
            continue
        if "parent_id" not in n:
            # The single most expensive malformation: the archived TreeMaker
            # builder did not survive it, and no retry recovered.
            errors.append(
                f"node {nid} has no 'parent_id' key. Every node needs one "
                "(the root's is null). Note the field is `parent_id`, not "
                "`parent`.")
        ids.append(nid)

    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        errors.append(f"duplicate node id(s): {dupes}")
    if errors:
        # Later checks index by id and would report cascading nonsense.
        return {"ok": False, "errors": errors, "warnings": warnings,
                "observations": {"node_count": len(tree_nodes)}}

    id_set = set(ids)
    by_id = {n["id"]: n for n in tree_nodes}
    position = {n["id"]: i for i, n in enumerate(tree_nodes)}

    # ---- root ------------------------------------------------------------
    roots = [n["id"] for n in tree_nodes if n["parent_id"] is None]
    if not roots:
        errors.append("no root: exactly one node must have parent_id null")
    elif len(roots) > 1:
        errors.append(f"{len(roots)} roots ({roots}); exactly one node may "
                      "have parent_id null")

    # ---- parents ---------------------------------------------------------
    for n in tree_nodes:
        pid = n["parent_id"]
        if pid is None:
            continue
        if pid not in id_set:
            errors.append(f"node {n['id']} names parent_id {pid!r}, which is "
                          "not a node in this list")
        elif position[pid] > position[n["id"]]:
            # Ordering was not a style rule: the archived TreeMaker engine
            # read the list in order and seeded placement from list position.
            # Parents-first stays a structural invariant of the format.
            errors.append(
                f"node {n['id']} appears at index {position[n['id']]} but "
                f"its parent {pid} is later at index {position[pid]}. Every "
                "node must appear AFTER its parent.")
        elif pid == n["id"]:
            errors.append(f"node {n['id']} is its own parent")

    # ---- reachability / cycles ------------------------------------------
    if roots and len(roots) == 1:
        seen, frontier = {roots[0]}, [roots[0]]
        children: dict = {}
        for n in tree_nodes:
            if n["parent_id"] is not None:
                children.setdefault(n["parent_id"], []).append(n["id"])
        while frontier:
            cur = frontier.pop()
            for c in children.get(cur, []):
                if c not in seen:
                    seen.add(c)
                    frontier.append(c)
        orphans = sorted(id_set - seen)
        if orphans:
            errors.append(
                f"node(s) {orphans} are not reachable from the root -- the "
                "graph has a cycle or a detached component; a metric tree "
                "must be acyclic and connected")

    # ---- lengths ---------------------------------------------------------
    for n in tree_nodes:
        if n["parent_id"] is None:
            continue                      # root length is ignored
        if "length" not in n:
            errors.append(f"node {n['id']} has no 'length'")
        elif not _is_num(n["length"]):
            errors.append(f"node {n['id']}: length {n['length']!r} is not a "
                          "finite number")
        elif n["length"] <= 0:
            errors.append(f"node {n['id']}: length {n['length']} must be > 0 "
                          "(a zero-length edge is not a flap)")

    # ---- leaves / pairs --------------------------------------------------
    leaves = [n["id"] for n in tree_nodes
              if n["parent_id"] is not None
              and all(o["parent_id"] != n["id"] for o in tree_nodes)]
    leaf_set = set(leaves)
    pairs = symmetric_pairs or []
    if not isinstance(pairs, list):
        errors.append("symmetric_pairs must be a list of [a, b] leaf id "
                      "pairs")
        pairs = []

    paired: dict = {}
    for p in pairs:
        if not isinstance(p, (list, tuple)) or len(p) != 2:
            errors.append(f"symmetric pair {p!r} must be a 2-element list "
                          "[node_a, node_b]")
            continue
        a, b = p
        for x in (a, b):
            if x not in id_set:
                errors.append(f"symmetric pair {list(p)} names {x!r}, which "
                              "is not a node in this list")
            elif x not in leaf_set:
                errors.append(f"symmetric pair {list(p)} names {x}, which is "
                              "not a LEAF (it has children). Only flap tips "
                              "can be mirrored.")
        if a == b:
            errors.append(f"symmetric pair {list(p)} pairs a node with "
                          "itself")
        for x in (a, b):
            if x in paired:
                errors.append(f"node {x} appears in more than one symmetric "
                              f"pair ({paired[x]} and {list(p)})")
            else:
                paired[x] = list(p)

    # ---- observations ----------------------------------------------------
    root = roots[0] if len(roots) == 1 else None
    root_children = ([n["id"] for n in tree_nodes if n["parent_id"] == root]
                     if root is not None else [])
    # Key the hub map by REPR, not by the raw parent_id. A tree that mixes an
    # int and a string parent (`0` and `"0"`) otherwise builds a mixed-type key
    # set, and `sorted(hubs.items())` raises TypeError comparing str to int --
    # which the tool wrapper then turns into "ERROR: '<' not supported between
    # instances of 'str' and 'int'", REPLACING the perfectly good diagnosis
    # this function had already computed ("node 2 names parent_id '0', which is
    # not a node in this list"). Observations are built before the error
    # return, so a malformed tree crashed on its way to being explained.
    # (Adversarial review.)
    hubs: dict = {}
    for n in tree_nodes:
        if n["parent_id"] is not None:
            hubs.setdefault(repr(n["parent_id"]), []).append(n["id"])
    obs = {
        "node_count": len(tree_nodes),
        "leaf_count": len(leaves),
        "leaves": leaves,
        "root": root,
        "root_children": root_children,
        "flaps_per_hub": {h: sum(1 for c in cs if c in leaf_set)
                          for h, cs in sorted(hubs.items())},
        "paired_leaves": sorted(paired),
        "unpaired_leaves": sorted(leaf_set - set(paired)),
    }

    if errors:
        return {"ok": False, "errors": errors, "warnings": warnings,
                "observations": obs}

    # ---- warnings (measured, never blocking) -----------------------------
    # No length-BAND warning. The prompt's retired "~0.3 to start, ~0.2 once
    # there are 6+ flaps" reads like a rule but is contradicted by the
    # repo's own known-good data: the quadruped carries a 0.40 head and the
    # bird two 0.40 wings, both at 6 flaps, and both pack attempt-0 exact.
    # There is no measurement here that separates a safe length from a risky
    # one, so there is no warning -- the guidance survives as advice in the
    # prompt's cheat-sheet, where it is labelled as a starting point rather
    # than enforced as a contract.

    # Unpaired leaves are NOT suspicious in general: heads, tails and abdomens
    # are midline features and every TreeMaker-era template had one or two.
    # What IS a probable missed bilateral pair is two UNPAIRED leaves that
    # share a parent AND a length -- the shape S8's pair-detection work
    # targeted. All four templates were clean under this rule; the
    # quadruped's case is still pinned in tests/test_tree_contract.py.
    missed = []
    unpaired = set(obs["unpaired_leaves"])
    for hub, kids in sorted(hubs.items()):   # repr keys: always str-comparable
        free = [k for k in kids if k in unpaired and k in leaf_set]
        by_len: dict = {}
        for k in free:
            by_len.setdefault(round(float(by_id[k]["length"]), 9), []).append(k)
        for length, group in sorted(by_len.items()):
            if len(group) >= 2:
                missed.append((sorted(group), hub, length))
    for group, hub, length in missed:
        warnings.append(
            f"leaves {group} share hub {hub} and length {length} but are in "
            "no symmetric pair -- that is the shape of a bilateral feature "
            "whose pairing was missed. Pairing it lets Pleatwright pack the "
            "two flaps as mirrored columns.")

    if not pairs and len(leaves) >= 4:
        warnings.append(
            "no symmetric_pairs given. Pleatwright packs declared pairs as "
            "mirror-symmetric columns; without them only leaves whose names "
            "differ by a left/right token are mirrored.")

    return {"ok": True, "errors": [], "warnings": warnings,
            "observations": obs}
