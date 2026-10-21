"""The authoring contract: what the model is told, and what it may return.

MOVED INTO PRODUCTION 2026-09-10 (S5). These lived in
`docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/scripts/loop_lib.py`,
whose README says "Do not import" -- so nothing shippable could author a tree.
The text is copied VERBATIM rather than retyped: every clause in it was bought
with a measured run, and a silent transcription drift would be invisible.

WHAT EACH LOAD-BEARING CLAUSE COST
  "FLIP THE SIGN"            3 of 17 trees came back with their limbs in the
                             air, scoring EXACT on every numeric metric.
  "EACH SIDE IS ITS OWN CHAIN"  3 of 17 authored one leg ending in a forked
                             foot -- the horse's hind pair 2 units of 22 apart.
  "READ BEFORE YOU DERIVE"   the rule that makes fabrication visible in the
                             artifact instead of detectable only by re-measuring.
  "LEAF CONVENTION"          the counting RULE rides here; the expected COUNT
                             never does. Feeding the count closes the loop that
                             §7 scores against.
  "WHICH PANEL IS THE PROFILE"  (2026-09-13) bat #2 of full17 came back rotated
                             90 degrees: the render called the mesh's XY plane
                             "side view" and the bat's wingspan runs along X.
                             Panels are now named by axis and the model says
                             where the head is before it reads.
  "FOLDED FLAT"              (2026-09-13) full17_v2 authored the bird wingless
                             3/3 and the rabbit tailless 3/3: the head's
                             "only when it protrudes" test was being applied to
                             anything flush with the trunk. Wings and tails
                             count regardless.
  (reverted) "A JOINT IS A READING"  Tried 2026-09-13 in full17_v2: joints
                             10.2 -> 2.3 per tree, flatten serves 7 -> 2, but
                             the owner wants expressive, jointed limbs in the
                             tree and accepts the flatten rung as the price.
                             Rule 5 mandates named joints again.
"""
from __future__ import annotations

#: The longest-edge length `metric_tree` normalizes to: the packing regime
#: every TreeMaker-era tree in this project was compiled in (formerly
#: mesh_to_tree.LONGEST_LIMB_TARGET, archived). A tree built at another scale
#: is not comparable to any number measured in that regime.
LONGEST_LIMB_TARGET = 0.40


SYSTEM = """You author Metric Trees for an origami design pipeline by READING \
orthographic renders of a 3-D mesh.

THE IMAGE holds three orthographic views of ONE mesh, named by the MESH'S OWN \
AXES: the XY panel (x across, y up), the ZY panel (z across, y up) and the XZ \
panel (x across, z up). Each sits under a labelled measurement grid; the grid \
divides the mesh's LONGEST extent into 24 units and all three panels share \
that scale.

FRAME: you write directions in that same mesh frame -- +x is rightward in the \
XY and XZ panels, +y is UP in the XY and ZY panels, +z is rightward in the ZY \
panel and UPWARD in the XZ panel. Every node carries a `direction` [dx,dy,dz] \
from its parent; it is normalised for you, so only the DIRECTION matters, never \
the magnitude. Directions are what let your tree be drawn as a stick figure -- \
a limb with the wrong direction will look wrong even when its length is right.

*** THE ANIMAL MAY FACE ANY WAY. SAY WHICH PANEL IS THE PROFILE. ***
The panels are NOT named "side" and "front", because that is not knowable from \
the axes: a dog's longest extent is nose-to-tail, so its XY panel is a profile, \
but a bat with spread wings or a wide-bodied crab is LONGEST ACROSS ITS BODY, \
and then the XY panel shows its FRONT and the ZY panel is the profile. Before \
any reading, look at all three panels, decide where the head is, and put it \
FIRST in `readings`, e.g. "head at -x: XY panel is the profile, ZY is the \
front" or "head at +z: ZY panel is the profile". Then take lengths from the \
panel that actually shows the limb in profile. Name left and right by the \
ANIMAL (`_L`/`_R`), whichever mesh axis they fall along.

*** TWO FRAMES, AND THEY DISAGREE. YOU MUST FLIP THE SIGN. ***
The GRID YOU READ FROM has its vertical axis increasing DOWNWARD: tick 0 is at \
the TOP of each panel and 24 at the BOTTOM. So the ground is a LARGE second \
number and the animal's back is a SMALL one -- "ground (7, 21.5)" is BELOW \
"withers (7, 6.5)".
The FRAME YOU WRITE IN has +y UP.
Therefore a limb that descends on screen has a NEGATIVE dy. Before you submit, \
check one leg: from hip to foot the animal goes DOWN, so that direction's dy \
must be negative. Getting this backwards puts the animal on its back with its \
legs in the air, and every other number in your answer can still be correct.

PROTOCOL, followed exactly:

1. READ BEFORE YOU DERIVE. Before writing any length, quote the grid \
coordinates you actually read, e.g. "shoulder (7.5, 9.5), ground (7, 21.5), so \
foreleg = 12". Every length must trace to a reading in `readings`.

2. CHECK YOUR READINGS AGAINST EACH OTHER. Two landmarks that share a \
coordinate assert something geometric -- identical x for the withers and the \
head/neck junction claims a perfectly VERTICAL neck. If a pair of readings \
implies an anatomically impossible geometry, re-read them.

3. PROPORTION, NOT POSE. Encode proportional limb lengths, never the pose. Four \
legs mid-stride at four different phases are still authored EQUAL.

4. LEAF CONVENTION. One leaf per terminal appendage: each limb, wing, tentacle \
or ray counts one; the tail counts one when the animal has an external tail. \
A wing or a tail counts EVEN WHEN FOLDED FLAT against the body -- a perched \
bird's wings and a crouching rabbit's tail are flaps the folder must have, and \
"folded flush with the trunk" is not a reason to drop them. That sentence is \
about WINGS AND TAILS ONLY: it does not promote sub-flap detail, and an ear \
stays an ear however large it is -- an elephant's or a rabbit's ears are part \
of the head flap, never leaves. The protrusion test below is the HEAD'S test, \
not theirs. \
The head counts one ONLY when it protrudes from the body on a neck or as a \
distinct lobe (mammals, birds, reptiles, most fish). A head fused into the \
trunk -- a cephalothorax or carapace (spiders, scorpions, crabs), or a body \
that simply tapers to a mouth -- is TRUNK, not a flap, and gets no leaf. \
Digits, toes, ears, antennae, eyes, mouthparts and the small pedipalps of \
spiders are sub-flap detail and DO NOT count as leaves -- a spider has FOUR leg \
pairs, never five. A pedipalp enlarged into a working claw (the chelae of \
scorpions, the pincers of crabs) is a limb and counts one.

5. STRUCTURE. A body spine of internal nodes (not one hub), with each limb \
attached where the mesh attaches it -- a crab's four leg pairs sit at four \
places along the carapace, not at one -- and multi-segment limbs with named \
joints -- thigh -> knee -> shank -> hock -> foot. Root at a body node with \
length 0 and direction [0,0,0]. Every non-root node names a parent appearing \
EARLIER in your list.

*** EACH SIDE IS ITS OWN CHAIN, ALL THE WAY TO THE BODY. ***
A left limb and a right limb are TWO limbs. Give each one its own joints and \
parent BOTH to a spine node:
    withers -> shoulder_L -> knee_L -> foot_L
    withers -> shoulder_R -> knee_R -> foot_R
NEVER write one shared chain that splits at the end:
    withers -> shoulder -> knee -> fetlock -> {hoof_L, hoof_R}     <-- WRONG
That says the animal has ONE front leg ending in a fork. The compiler measures \
each flap from where it branches, so the wrong version becomes one long flap \
with two stubs on it instead of two full legs, and the base will not read as \
the animal. Before you submit, check every pair: trace from one member back \
toward the body and confirm you reach a SPINE node before you meet its \
partner's chain.

6. LENGTHS ARE POSITIVE INTEGERS in grid units. Never 0 for a non-root node.

7. SYMMETRIC PAIRS join two LEAVES only -- never two internal joints.

8. LABEL INFERENCE. The grid gives endpoints and totals; splitting a limb into \
segments is anatomical inference. Say which splits were inferred in `notes`.

Answer only by calling submit_tree."""
TOOL = [{"type": "function", "function": {
    "name": "submit_tree",
    "description": "Submit the metric tree read off the render.",
    "parameters": {"type": "object", "properties": {
        "subject_guess": {"type": "string"},
        "readings": {"type": "array", "items": {"type": "string"}},
        "nodes": {"type": "array", "items": {"type": "object", "properties": {
            "name": {"type": "string"},
            "parent": {"type": ["string", "null"]},
            "length": {"type": "integer"},
            "direction": {"type": "array", "items": {"type": "number"},
                          "minItems": 3, "maxItems": 3}},
            "required": ["name", "parent", "length", "direction"]}},
        "pairs": {"type": "array",
                  "items": {"type": "array", "items": {"type": "string"}}},
        "leaves": {"type": "array", "items": {"type": "string"}},
        "notes": {"type": "string"}},
        "required": ["subject_guess", "readings", "nodes", "leaves"]}}}]

def to_tuples(tree: dict) -> list:
    """Model output -> (name, parent, direction, length) tuples.

    A root with an all-zero direction becomes `None`, which is what
    `vlm_render.positions` reads as "this node is the origin".
    """
    out = []
    for n in tree["nodes"]:
        d = n.get("direction") or [1, 0, 0]
        if not any(d):
            d = None if n.get("parent") is None else [1, 0, 0]
        out.append((n["name"], n.get("parent"), d, n["length"]))
    return out


def leaves_of(nodes) -> list:
    """Names of the nodes with no children -- the flaps the base will pack."""
    kids: dict = {}
    for name, parent, _, _ in nodes:
        if parent:
            kids[parent] = kids.get(parent, 0) + 1
    return [n[0] for n in nodes if kids.get(n[0], 0) == 0]


def leaf_pairs(tree, leaf_names) -> tuple[list, list]:
    """Split a model's declared `pairs` into the usable ones and the DROPPED ones.

    Returns `(keep, dropped)`. `keep` is `[(a, b), ...]` of pairs joining two
    leaves; `dropped` is `[[...], ...]` of everything else -- malformed entries
    and pairs naming an internal joint.

    ⚠ THE DROPPED LIST IS RETURNED RATHER THAN DISCARDED. The filter itself is
    forced, not stylistic: prompt rule 7 and `tree_contract` both require a
    symmetric pair to join two leaves, so an internal-joint pair fails
    validation for the whole tree. But dropping one is not free -- the compiler
    then gets NO mirror constraint for that limb, and a human at the gate would
    approve a tree whose bilateral symmetry had been silently thrown away.
    Measured 2026-09-10 across all 17 committed subjects: nothing is dropped
    today, which is precisely why a silent filter would never be noticed if
    that changed.

    Extracted here because this exact comprehension was written out three times
    -- `gated_pipeline._author`, `gated_pipeline._draft` and
    `eval_vlm_pipeline.score_corpus` -- and three copies of a filter is three
    places for the definition of "usable pair" to drift apart.
    """
    leaves = set(leaf_names)
    keep, dropped = [], []
    for p in (tree.get("pairs") or []):
        if len(p) == 2 and p[0] in leaves and p[1] in leaves:
            keep.append((p[0], p[1]))
        else:
            dropped.append(list(p))
    return keep, dropped


def metric_tree(nodes, pairs):
    """(name, parent, direction, length) tuples -> the repo Metric Tree format.

    Returns (tree_nodes, symmetric_pairs, names). Lengths are scaled so the
    longest EDGE is LONGEST_LIMB_TARGET; `names` maps the emitted integer ids
    back to the model's own labels, which is what lets a report say "front
    hoof" instead of "node 14".
    """
    idx = {n[0]: i for i, n in enumerate(nodes)}
    mx = max(n[3] for n in nodes) or 1
    k = LONGEST_LIMB_TARGET / mx
    tn = [{"id": i,
           "parent_id": (idx[n[1]] if n[1] is not None else None),
           "length": round(n[3] * k, 6)}
          for i, n in enumerate(nodes)]
    return (tn,
            [[idx[a], idx[b]] for a, b in pairs],
            {i: n[0] for i, n in enumerate(nodes)})
