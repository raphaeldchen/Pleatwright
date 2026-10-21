"""The ONLY source of trees for tests (owner rule, CLAUDE.md §5; ruling 2026-10-07).

Every test that touches a tree starts from one of the 51 artifact trees in
`fixtures/full17_v3_sticks/` ("Bases in Triplicate III"). A test that needs a
DEFECTIVE tree (fused limbs, a malformed pair, a missing field ...) applies the
defect as an explicit, named, documented edit inside its own test file, so the
base is always an artifact tree and the deviation is visible at the call site.

This module only LOADS and DERIVES. It applies no defect.
"""
from __future__ import annotations

import copy
import functools
import json
import os

import tree_authoring as TA

STICKS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "fixtures", "full17_v3_sticks")

#: Every artifact roll name, e.g. "dog_0".
ROLLS = sorted(f[:-5] for f in os.listdir(STICKS) if f.endswith(".json"))

#: The fields a VLM `submit_tree` call returns (tree_authoring.TOOL).
AUTHORED_FIELDS = ("subject_guess", "nodes", "pairs", "readings", "leaves")


def path(roll: str) -> str:
    """The artifact tree's file on disk."""
    return os.path.join(STICKS, f"{roll}.json")


@functools.lru_cache(maxsize=None)
def _load(roll: str) -> dict:
    with open(path(roll)) as f:
        return json.load(f)


def artifact_tree(roll: str) -> dict:
    """A deep copy of `fixtures/full17_v3_sticks/<roll>.json`; safe to edit."""
    return copy.deepcopy(_load(roll))


def authored(roll: str) -> dict:
    """The authoring-tool payload subset of an artifact tree -- exactly what a
    VLM `submit_tree` call returns -- as a fresh deep copy."""
    t = artifact_tree(roll)
    return {k: t[k] for k in AUTHORED_FIELDS}


def metric(tree: dict) -> tuple[list, list, dict]:
    """DERIVE the id-based metric tree from a (possibly edited) artifact tree.

    The same three production calls `gated_pipeline._build` makes:
    `to_tuples` -> `leaf_pairs` -> `metric_tree`. Returns
    `(tree_nodes, symmetric_pairs, ids)` where `ids` maps each node NAME to
    its emitted integer id, so a test can address nodes by anatomy.
    """
    nodes = TA.to_tuples(tree)
    keep, _dropped = TA.leaf_pairs(tree, TA.leaves_of(nodes))
    tn, sp, names = TA.metric_tree(nodes, keep)
    return tn, sp, {v: k for k, v in names.items()}
