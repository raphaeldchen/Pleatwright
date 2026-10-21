"""Shared pieces for the wired agent loop: schema, prompt, sheet rendering."""
import os, sys
H = "<repo>/mcp_harness"
S = os.path.dirname(os.path.abspath(__file__))
for p in (H, os.path.join(H, "tests"), S):
    sys.path.insert(0, p)
from PIL import Image, ImageDraw
import hand_trees_build as B          # positions / panel / leaves_of / metric_tree

SYSTEM = """You author Metric Trees for an origami design pipeline by READING \
orthographic renders of a 3-D mesh.

THE IMAGE holds three orthographic views of ONE mesh -- side (XY), front (ZY), \
top (XZ) -- each under a labelled measurement grid. The grid divides the mesh's \
LONGEST extent into 24 units and all three views share that scale.

FRAME: +x forward (toward the head), +y up, +z to the animal's LEFT. Every node \
carries a `direction` [dx,dy,dz] from its parent; it is normalised for you, so \
only the DIRECTION matters, never the magnitude. Directions are what let your \
tree be drawn as a stick figure -- a limb with the wrong direction will look \
wrong even when its length is right.

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
or ray counts one; the head counts one; the tail counts one when the animal has \
an external tail. Digits, toes, ears, antennae and eyes are sub-flap detail and \
DO NOT count as leaves.

5. STRUCTURE. A body spine of internal nodes (not one hub), and multi-segment \
limbs with named joints -- thigh -> knee -> shank -> hock -> foot. Root at a \
body node with length 0 and direction [0,0,0]. Every non-root node names a \
parent appearing EARLIER in your list.

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


def to_tuples(t):
    """Model nodes -> (name, parent, direction, length), the hand-authored shape."""
    out = []
    for n in t["nodes"]:
        d = n.get("direction") or [1, 0, 0]
        if not any(d):
            d = None if n.get("parent") is None else [1, 0, 0]
        out.append((n["name"], n.get("parent"), d, n["length"]))
    return out


def sheet(nodes, out_path, title):
    """The SAME four-view stick-figure sheet used for the hand-authored trees.
    hand_trees_build.sheet is keyed on its own SUBJECTS table, so the panel and
    layout code is reused directly and only the caption differs."""
    pos = B.positions(nodes)
    imgs = [B.panel(nodes, pos, p, p)
            for p in ("top view", "side view", "front view", "isometric")]
    W = sum(i.width for i in imgs)
    s = Image.new("RGB", (W, imgs[0].height + 26), (253, 253, 251))
    for i, im in enumerate(imgs):
        s.paste(im, (i * im.width, 26))
    lf = B.leaves_of(nodes)
    ImageDraw.Draw(s).text((8, 7), f"{title}   {len(nodes)} nodes, "
                                   f"{len(lf)} leaves",
                           fill=(20, 20, 20), font=B._font(13))
    s.save(out_path)
    return out_path
