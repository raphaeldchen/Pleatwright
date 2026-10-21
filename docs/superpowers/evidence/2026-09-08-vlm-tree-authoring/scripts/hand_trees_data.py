"""HAND-AUTHORED metric trees for the nine photo-derived meshes.

Every length here was READ off a 24-unit grid laid over orthographic renders of
the mesh it describes (scratchpad/measure/<subject>.png), not computed by any
extractor and not copied from a body-plan template. Where a reading was
ambiguous the anatomically consistent value was chosen over the posed one:
a metric tree encodes PROPORTION, so a trotting horse's four legs get equal
lengths even though the render shows them at four different phases.

FRAME: +x forward (toward the head), +y up, +z to the animal's left.
Directions are drawing hints only. The tree is (parent, length); direction
places the node so a sheet can be drawn, and never affects the metric.

CONVENTION, and where the two references disagree:
  * STRUCTURE follows COrigami -- a body spine of internal nodes rather than a
    single hub, and multi-segment limbs with named joints
    (thigh -> knee -> shank -> hock -> foot).
  * LEAF COUNTING for the `packable` variant follows this repo's shipped
    oracle (fixtures/anatomy_expectation.json): one leaf per terminal
    appendage; ears, antennae and digits are sub-flap detail and do not count.
  * The `faithful` variant follows COrigami instead, which DOES give ears and
    eyestalks their own leaves (see the jerboa's ear_tip_l/ear_tip_r).
That disagreement is the whole reason there are two trees per subject.
"""
from __future__ import annotations

# (name, parent, direction, length)  -- length 0 marks the root
Q_ORDER_NOTE = ("quadruped order: hubs and legs first, head and tail LAST -- "
                "body_plans.py records that as the measured-to-pack ordering, "
                "and the engine seeds placement from list position")

D = dict  # readability


def _quadruped(*, neck, head, ear, body_f, body_r,
               fore=(4, 6, 2), hind=(4, 4, 3), tail=(3, 3),
               ear_dir=(0.2, 1.0, 0.45), head_dir=(1, -0.15, 0),
               tail_dir=(-1, 0.55, 0)):
    """Shared quadruped skeleton. Every caller passes its OWN measured numbers;
    this only fixes the topology and the node order, both of which are shared
    across dog/cat/horse and are exactly the parts that are not measurements."""
    fu, fl, fp = fore
    th, sh, hp = hind
    t1, t2 = tail
    nodes = [
        ("body_c",      None,        None,             0),
        ("shoulders",   "body_c",    (1, 0.05, 0),     body_f),
        ("hips",        "body_c",    (-1, 0.05, 0),    body_r),
        # --- legs, before head and tail (see Q_ORDER_NOTE) ---
        ("elbow_l",     "shoulders", (0.1, -1, 0.35),  fu),
        ("elbow_r",     "shoulders", (0.1, -1, -0.35), fu),
        ("wrist_l",     "elbow_l",   (0, -1, 0.05),    fl),
        ("wrist_r",     "elbow_r",   (0, -1, -0.05),   fl),
        ("fore_paw_l",  "wrist_l",   (0.5, -1, 0),     fp),
        ("fore_paw_r",  "wrist_r",   (0.5, -1, 0),     fp),
        ("stifle_l",    "hips",      (0.1, -1, 0.35),  th),
        ("stifle_r",    "hips",      (0.1, -1, -0.35), th),
        ("hock_l",      "stifle_l",  (-0.3, -1, 0.05), sh),
        ("hock_r",      "stifle_r",  (-0.3, -1, -0.05), sh),
        ("hind_paw_l",  "hock_l",    (0.4, -1, 0),     hp),
        ("hind_paw_r",  "hock_r",    (0.4, -1, 0),     hp),
        # --- head chain ---
        ("head_base",   "shoulders", (1, 0.25, 0),     neck),
        ("nose",        "head_base", head_dir,         head),
        ("ear_tip_l",   "head_base", ear_dir,          ear),
        ("ear_tip_r",   "head_base", (ear_dir[0], ear_dir[1], -ear_dir[2]), ear),
        # --- tail chain ---
        ("tail_mid",    "hips",      tail_dir,         t1),
        ("tail_tip",    "tail_mid",  (-1, 0.15, 0),    t2),
    ]
    pairs = [("fore_paw_l", "fore_paw_r"), ("hind_paw_l", "hind_paw_r"),
             ("ear_tip_l", "ear_tip_r")]
    return nodes, pairs


def _drop_ears(nodes, pairs):
    """The packable reduction shared by dog/cat/horse: ears are sub-flap detail
    under the repo convention, so they stop being leaves. Nothing else moves --
    the merge is recorded so the cost is legible."""
    keep = [n for n in nodes if not n[0].startswith("ear_tip_")]
    return keep, [p for p in pairs if not p[0].startswith("ear_tip_")]


SUBJECTS: dict = {}


# ---------------------------------------------------------------- dog
_n, _p = _quadruped(neck=2, head=4, ear=3, body_f=5, body_r=4,
                    fore=(4, 6, 2), hind=(4, 4, 3), tail=(3, 3))
SUBJECTS["dog"] = D(
    grid=24, common="beagle",
    read="side view: withers x7, hip x16, ground y21.5, nose x1, tail base "
         "x17.5 curling to a tip at (20, 2.5). Foreleg 12 units shoulder to "
         "ground, hind leg 11.",
    faithful=D(nodes=_n, pairs=_p),
    packable=D(nodes=_drop_ears(_n, _p)[0], pairs=_drop_ears(_n, _p)[1]),
    merges=["ear_tip_l + ear_tip_r -> head_base (sub-flap detail under the "
            "repo convention; COrigami would keep them, and the jerboa does)"],
    order_note=Q_ORDER_NOTE,
)

# ---------------------------------------------------------------- cat
_n, _p = _quadruped(neck=2, head=3, ear=2, body_f=5, body_r=5,
                    fore=(3, 4, 2), hind=(3, 3, 3), tail=(3, 4))
SUBJECTS["cat"] = D(
    grid=24, common="ginger domestic cat",
    read="side view: nose x22.5, shoulders x17, hips x7, ground y19.5. Tail "
         "base (5,9) curling left to (1,9.5); measured along the curl, not "
         "the chord, so 7 rather than 4.",
    faithful=D(nodes=_n, pairs=_p),
    packable=D(nodes=_drop_ears(_n, _p)[0], pairs=_drop_ears(_n, _p)[1]),
    merges=["ear_tip_l + ear_tip_r -> head_base (sub-flap detail)"],
    order_note=Q_ORDER_NOTE,
    caveat="The mesh carries a thin whisker sheet across the muzzle and a "
           "stray plane spanning the flank -- the source of its 38 bodies. "
           "Neither is anatomy and neither is in this tree.",
)

# ---------------------------------------------------------------- horse
_n, _p = _quadruped(neck=5, head=5, ear=2, body_f=4, body_r=4,
                    fore=(3, 3, 3), hind=(3, 3, 3), tail=(3, 3))
SUBJECTS["horse"] = D(
    grid=24, common="chestnut horse, trotting",
    read="side view: muzzle x21, poll x17.5, withers x13, croup x4.5, ground "
         "y18. The long neck (5) against the dog's (2) is the single biggest "
         "proportional difference between the two quadrupeds. Legs read at "
         "four different phases of a trot and are authored EQUAL: a metric "
         "tree carries proportion, not pose.",
    faithful=D(nodes=_n, pairs=_p),
    packable=D(nodes=_drop_ears(_n, _p)[0], pairs=_drop_ears(_n, _p)[1]),
    merges=["ear_tip_l + ear_tip_r -> head_base (sub-flap detail)"],
    order_note=Q_ORDER_NOTE,
)


# ---------------------------------------------------------------- lizard
_n = [
    ("body_c",       None,        None,                0),
    ("shoulders",    "body_c",    (1, 0.05, 0),        4),
    ("hips",         "body_c",    (-1, 0.05, 0),       4),
    ("elbow_l",      "shoulders", (0.35, -0.2, 1),     2),
    ("elbow_r",      "shoulders", (0.35, -0.2, -1),    2),
    ("wrist_l",      "elbow_l",   (0.25, -0.55, 0.8),  2),
    ("wrist_r",      "elbow_r",   (0.25, -0.55, -0.8), 2),
    ("fore_foot_l",  "wrist_l",   (0.4, -0.25, 0.6),   1),
    ("fore_foot_r",  "wrist_r",   (0.4, -0.25, -0.6),  1),
    ("knee_l",       "hips",      (-0.35, -0.2, 1),    3),
    ("knee_r",       "hips",      (-0.35, -0.2, -1),   3),
    ("ankle_l",      "knee_l",    (0.55, -0.5, 0.7),   2),
    ("ankle_r",      "knee_r",    (0.55, -0.5, -0.7),  2),
    ("hind_foot_l",  "ankle_l",   (0.5, -0.25, 0.5),   1),
    ("hind_foot_r",  "ankle_r",   (0.5, -0.25, -0.5),  1),
    ("head_base",    "shoulders", (1, 0.1, 0),         2),
    ("snout",        "head_base", (1, -0.05, 0),       3),
    ("tail_mid",     "hips",      (-1, 0, 0),          3),
    ("tail_tip",     "tail_mid",  (-1, -0.05, 0),      4),
]
_p = [("fore_foot_l", "fore_foot_r"), ("hind_foot_l", "hind_foot_r")]
SUBJECTS["lizard"] = D(
    grid=24, common="agama lizard",
    read="top view: snout x22, shoulders x17, hips x9.5, tail tip x1. Limbs "
         "SPRAWL -- they leave the body sideways before turning down, which is "
         "why the elbow/knee directions carry a large z and the shoulder-to-"
         "foot path (5) is longer than the straight-line distance (4).",
    faithful=D(nodes=_n, pairs=_p),
    packable=D(nodes=_n, pairs=_p),
    merges=[],
    identical_note="COrigami fidelity and the packable window AGREE here at 6 "
                   "leaves, so the two trees are the same object. A lizard has "
                   "no ear or crest flap to spend, and its five-toed feet are "
                   "sub-flap detail under BOTH conventions -- COrigami's "
                   "jerboa terminates a limb at one toe node, not five.",
    order_note=Q_ORDER_NOTE,
    caveat="This mesh is a flattened plaque: extents 1.961 x 0.318 x 1.027, "
           "aspect 6.2, because the photograph is a low, near-top-down view of "
           "an animal lying on a rock. The tree is authored from the animal's "
           "proportions as read in TOP view, which is the view that survives.",
)

# ---------------------------------------------------------------- frog
_n = [
    ("body_c",      None,        None,                 0),
    ("shoulders",   "body_c",    (1, 0.1, 0),          2),
    ("hips",        "body_c",    (-1, 0, 0),           3),
    ("elbow_l",     "shoulders", (0.1, -1, 0.5),       3),
    ("elbow_r",     "shoulders", (0.1, -1, -0.5),      3),
    ("wrist_l",     "elbow_l",   (0.6, -0.8, 0.3),     2),
    ("wrist_r",     "elbow_r",   (0.6, -0.8, -0.3),    2),
    ("hand_l",      "wrist_l",   (1, -0.3, 0.3),       1),
    ("hand_r",      "wrist_r",   (1, -0.3, -0.3),      1),
    ("knee_l",      "hips",      (-0.9, 0.15, 0.6),    4),
    ("knee_r",      "hips",      (-0.9, 0.15, -0.6),   4),
    ("ankle_l",     "knee_l",    (0.8, -0.7, 0.35),    4),
    ("ankle_r",     "knee_r",    (0.8, -0.7, -0.35),   4),
    ("hind_foot_l", "ankle_l",   (1, -0.2, 0.25),      3),
    ("hind_foot_r", "ankle_r",   (1, -0.2, -0.25),     3),
    ("head_base",   "shoulders", (1, 0.15, 0),         2),
    ("snout",       "head_base", (1, -0.1, 0),         4),
]
_p = [("hand_l", "hand_r"), ("hind_foot_l", "hind_foot_r")]
SUBJECTS["frog"] = D(
    grid=24, common="wood frog",
    read="side view: snout x17.5, body_c x9, rump x4, ground y17. The hind "
         "limb is the whole story: 4+4+3 = 11 units of limb folded into 7 "
         "units of body length, thigh pointing BACK, shank forward-down, foot "
         "forward again. Forelimb totals 6.",
    faithful=D(nodes=_n, pairs=_p),
    packable=D(nodes=_n, pairs=_p),
    merges=[],
    identical_note="Identical at 5 leaves. An adult anuran has no tail (order "
                   "Anura, 'without tail') and no ear or crest flap, so "
                   "COrigami fidelity buys nothing the window cannot hold.",
    order_note="head LAST; there is no tail to place after it",
    caveat="The extractor read 12-42 leaves on this mesh at every one of 24 "
           "search cells and never entered the 4..8 window. The long digits "
           "are why. They are sub-flap detail here and cost 0 leaves -- the "
           "gap between 5 and 42 is the gap between a designer and a "
           "skeletoniser, not between two meshes.",
)

# ---------------------------------------------------------------- bird
_n = [
    ("body_c",       None,        None,                 0),
    ("shoulders",    "body_c",    (1, 0.15, 0),         2),
    ("hips",         "body_c",    (-0.6, -0.2, 0),      2),
    ("wing_wrist_l", "shoulders", (-0.5, 0.1, 0.7),     3),
    ("wing_wrist_r", "shoulders", (-0.5, 0.1, -0.7),    3),
    ("wing_tip_l",   "wing_wrist_l", (-1, -0.1, 0.2),   4),
    ("wing_tip_r",   "wing_wrist_r", (-1, -0.1, -0.2),  4),
    ("ankle_l",      "hips",      (-0.1, -1, 0.25),     2),
    ("ankle_r",      "hips",      (-0.1, -1, -0.25),    2),
    ("foot_l",       "ankle_l",   (0.5, -1, 0.05),      1),
    ("foot_r",       "ankle_r",   (0.5, -1, -0.05),     1),
    ("head_base",    "shoulders", (1, 0.5, 0),          3),
    ("beak",         "head_base", (1, 0.05, 0),         4),
    ("crest_tip",    "head_base", (0.05, 1, 0),         3),
    ("tail_mid",     "hips",      (-1, 0.05, 0),        5),
    ("tail_tip",     "tail_mid",  (-1, -0.05, 0),       5),
]
_p = [("wing_tip_l", "wing_tip_r"), ("foot_l", "foot_r")]
SUBJECTS["bird"] = D(
    grid=24, common="blue jay",
    read="side view: beak tip x0.5, head_base x4, body_c x8, tail base x11, "
         "tail tip x20.5 -- the tail is 10 units, longer than the bird's own "
         "body. Legs are short (3). Wing length 7 read off the folded wing's "
         "SEAM on the body surface, since the wings are not separate geometry.",
    faithful=D(nodes=_n, pairs=_p),
    packable=D(nodes=[n for n in _n if n[0] != "crest_tip"], pairs=_p),
    merges=["crest_tip -> head_base (a crest is sub-flap detail under the "
            "repo convention; COrigami keeps such things, cf. the hoopoe's "
            "fanned crest and the peacock's tail fan)"],
    order_note="wings and legs before the head chain; tail LAST",
    caveat="TWO things in this mesh are not in this tree. The PERCH lifted "
           "with the bird -- background removal kept the stump under its feet "
           "-- and it is scenery, not anatomy. And the WINGS are fused to the "
           "body, so no extractor can find them; a human can, because a human "
           "knows a blue jay has wings. That is the clearest case in this set "
           "of hand-authoring recovering what extraction structurally cannot.",
)


# ---------------------------------------------------------------- starfish
# Pentaradial, so the bilateral machinery does not apply and is not forced.
# A regular pentagon has FIVE mirror planes; picking one names arm0 as axial
# and pairs (1,4) and (2,3) across it. That is the only pairing a uniaxial
# base can use, and it is a CHOICE of plane, not a discovered fact.
import math as _math
_n = [("disc_c", None, None, 0)]
for k in range(5):
    a = _math.radians(90 + 72 * k)
    dx, dy = _math.cos(a), _math.sin(a)
    _n.append((f"arm{k}_mid", "disc_c", (dx, dy, 0), 5))
    _n.append((f"arm{k}_tip", f"arm{k}_mid", (dx, dy, 0), 6))
SUBJECTS["starfish"] = D(
    grid=24, common="red-knobbed sea star",
    read="face-on view: disc centred (11,12) with radius 3; the five arm tips "
         "sit at (11.5,0.5) (0.5,11) (21.5,9.5) (17.5,21.5) (5.5,21.5), all "
         "10.5-11.6 units from centre. Authored equal at 11 = 5 + 6.",
    faithful=D(nodes=_n, pairs=[("arm1_tip", "arm4_tip"),
                                ("arm2_tip", "arm3_tip")]),
    packable=D(nodes=_n, pairs=[("arm1_tip", "arm4_tip"),
                                ("arm2_tip", "arm3_tip")]),
    merges=[],
    identical_note="Identical at 5 leaves. Every leaf is an arm; there is no "
                   "head and no tail to add or drop, so the two conventions "
                   "cannot disagree.",
    order_note="arm0 (the axial arm) FIRST, then the two mirror pairs "
               "outward, so the axis is seeded before the paired flaps",
    symmetry_note="arm0 is axial and UNPAIRED by construction. Do not read "
                  "its lack of a partner as a lost mirror twin -- odd radial "
                  "symmetry cannot pair every ray.",
)

# ---------------------------------------------------------------- spider
_LEGS = [  # (name, direction family with z>0, (femur, tibia, tarsus))
    ("l1", (0.85, 0.25, 0.53), (4, 3, 3)),
    ("l2", (0.30, 0.25, 0.95), (4, 3, 2)),
    ("l3", (-0.25, 0.25, 0.97), (4, 3, 2)),
    ("l4", (-0.70, 0.25, 0.71), (4, 4, 3)),
]


def _spider_legs():
    out, pairs = [], []
    for tag, (dx, dy, dz), (fe, ti, ta) in _LEGS:
        for side, sz in (("l", 1), ("r", -1)):
            out += [
                (f"knee_{tag}{side}",  "cephalothorax",
                 (dx, dy, dz * sz), fe),
                (f"tibia_{tag}{side}", f"knee_{tag}{side}",
                 (dx, -0.55, dz * sz), ti),
                (f"foot_{tag}{side}",  f"tibia_{tag}{side}",
                 (dx * 0.7, -0.5, dz * sz * 0.7), ta),
            ]
        pairs.append((f"foot_{tag}l", f"foot_{tag}r"))
    return out, pairs


_legs, _lpairs = _spider_legs()
_abdomen = [("abdomen_c",  "cephalothorax", (-1, 0.05, 0), 3),
            ("abdomen_tip", "abdomen_c",    (-1, 0, 0),    5)]
_palps = [("palp_l", "cephalothorax", (1, -0.2, 0.25), 3),
          ("palp_r", "cephalothorax", (1, -0.2, -0.25), 3)]
SUBJECTS["spider"] = D(
    grid=24, common="wolf spider",
    read="top view: cephalothorax (13,11), abdomen centre (7,11), abdomen tip "
         "x3. Leg tips read 8 to 11.4 units from the cephalothorax; legs I "
         "and IV are longest, II and III shortest, which is the real "
         "arachnid pattern and is preserved rather than averaged. Each leg "
         "rises at the femur and descends through tibia and tarsus.",
    faithful=D(nodes=[("cephalothorax", None, None, 0)] + _legs
                     + _abdomen + _palps,
               pairs=_lpairs + [("palp_l", "palp_r")]),
    packable=D(nodes=[("cephalothorax", None, None, 0)] + _legs,
               pairs=_lpairs),
    merges=[
        "palp_l + palp_r -> cephalothorax (pedipalps are sub-flap detail "
        "under the repo convention, which excludes antennae and the like)",
        "abdomen DEMOTED from flap to trunk: 8 legs + abdomen = 9 exceeds "
        "MAX_LEAVES=8 and no eighth leg can be deleted without deleting real "
        "anatomy, so the opisthosoma stops being a flap and becomes the body "
        "the legs radiate from. This is the ONLY subject where the window "
        "costs a feature the anatomy oracle counts.",
    ],
    order_note="legs in pairs front to back, then the abdomen chain; the "
               "cephalothorax roots the tree because every leg attaches there",
)

# ---------------------------------------------------------------- octopus
_ARMS = [("a1", (0.35, 0.15, 0.94), (5, 5, 4)),
         ("a2", (-0.30, 0.05, 0.95), (4, 4, 4)),
         ("a3", (-0.80, -0.10, 0.60), (4, 4, 4)),
         ("a4", (-0.97, -0.20, 0.22), (4, 3, 3))]


def _octopus_arms():
    out, pairs = [], []
    for tag, (dx, dy, dz), (b, m, t) in _ARMS:
        for side, sz in (("l", 1), ("r", -1)):
            out += [
                (f"{tag}{side}_base", "crown", (dx, dy, dz * sz), b),
                (f"{tag}{side}_mid",  f"{tag}{side}_base",
                 (dx, dy - 0.35, dz * sz), m),
                (f"{tag}{side}_tip",  f"{tag}{side}_mid",
                 (dx * 0.8, dy - 0.15, dz * sz * 1.1), t),
            ]
        pairs.append((f"{tag}l_tip", f"{tag}r_tip"))
    return out, pairs


_arms, _apairs = _octopus_arms()
_mantle = [("mantle_mid", "crown",       (1, 0.1, 0), 4),
           ("mantle_tip", "mantle_mid",  (1, 0, 0),   5)]
SUBJECTS["octopus"] = D(
    grid=24, common="common octopus",
    read="top view: arm crown (11,11), mantle running back to a tip at x20, "
         "so the mantle is 9 units. Arm tips read 10 to 14 units from the "
         "crown, the front pair longest -- the arms are NOT equal and are not "
         "authored equal.",
    faithful=D(nodes=[("crown", None, None, 0)] + _arms + _mantle,
               pairs=_apairs),
    packable=D(nodes=[("crown", None, None, 0)] + _arms, pairs=_apairs),
    merges=[
        "mantle DEMOTED from flap to trunk: 8 arms + mantle = 9 exceeds "
        "MAX_LEAVES=8. Same trade as the spider's abdomen, and the same "
        "reasoning -- an arm is not deletable, the axial mass is.",
    ],
    order_note="arms in mirror pairs front to back, then the mantle chain",
    symmetry_note="Eight arms about ONE bilateral plane give 4 clean pairs. "
                  "This is the one radial subject whose symmetry is even, so "
                  "unlike the starfish nothing is left unpaired.",
)
