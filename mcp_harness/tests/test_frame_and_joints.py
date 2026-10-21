"""2026-09-13: honest panel labels; flush wings and tails still count.

* bat #2 of full17 authored a tree rotated 90 degrees because the render
  labelled the mesh's XY plane "side view" while the bat's wingspan runs along
  X, so that panel is its FRONT. The panels are now named by mesh axis and the
  model is told the animal may face any way and must say which panel is the
  profile.
* full17_v2 authored the bird WINGLESS on 3 of 3 rolls and the rabbit TAILLESS
  on 3 of 3: rule 4's "counts only when it protrudes" was written for the head
  and the model generalised it to anything folded flat. Wings and tails now
  count regardless.
* The "a joint is a reading" rule measured in full17_v2 (joints 10.2 -> 2.3 per
  tree, flatten 7 -> 2) was REVERTED by the owner the same day: expressive,
  multi-segment limbs are wanted in the tree; the flatten rung is the accepted
  price. Rule 5 mandates named joints again.
"""
from __future__ import annotations

import numpy as np
import pytest

import tree_authoring as TA
import vlm_render as VR


# ------------------------------------------------------------ the prompt
def test_rule_5_mandates_named_joints_again():
    """Reverted 2026-09-13 at the owner's instruction after full17_v2."""
    s = TA.SYSTEM
    assert "thigh -> knee -> shank -> hock -> foot" in s
    assert "A JOINT IS A READING" not in s


def test_rule_4_counts_wings_and_tails_even_when_folded_flat():
    s = TA.SYSTEM
    assert "FOLDED FLAT" in s
    # the protrusion test stays the HEAD's test
    assert "ONLY when it protrudes" in s
    # full17_v3: elephant #1 wrote "ears count as two separate flap leaves per
    # the folded-flap rule" -- the clause must fence itself to wings and tails
    assert "WINGS AND TAILS ONLY" in s
    assert "an ear stays an ear" in s


def test_the_paid_for_clauses_survive_the_rewrite():
    s = TA.SYSTEM
    for tok in ("FLIP THE SIGN", "DOWNWARD", "EACH SIDE IS ITS OWN CHAIN",
                "READ BEFORE YOU DERIVE", "LEAF CONVENTION"):
        assert tok in s, tok


def test_the_frame_is_the_mesh_frame_and_the_animal_may_face_any_way():
    s = TA.SYSTEM
    assert "XY panel" in s and "ZY panel" in s and "XZ panel" in s
    assert "toward the head" not in s          # +x is no longer claimed anatomical
    assert "animal's LEFT" not in s
    assert "WHICH PANEL IS THE PROFILE" in s


# --------------------------------------------------------- the renderer
def test_mesh_panels_are_named_by_axis_not_anatomy():
    assert {k: VR.PANEL_NAMES[k] for k in ("side", "front", "top")} == {
        "side": "XY panel", "front": "ZY panel", "top": "XZ panel"}
    for name in VR.PANEL_NAMES.values():
        assert "view" not in name and "side" not in name and "front" not in name
    assert VR.MESH_VIEW_FRAME_NOTE.startswith("The grid's vertical axis")


def test_render_mesh_views_reports_the_axis_names(tmp_path):
    trimesh = pytest.importorskip("trimesh")
    m = trimesh.creation.box(extents=(3.0, 1.0, 2.0))
    p = tmp_path / "box.glb"
    m.export(p)
    out = VR.render_mesh_views(str(p), str(tmp_path / "sheet.png"))
    assert out["panels"] == ["XY panel", "ZY panel", "XZ panel"]
    assert out["views"] == ["side", "front", "top"]


def test_tree_sheet_top_view_matches_the_mesh_xz_panel():
    """The mesh XZ panel draws +z UPWARD (vlm_render._mesh_panel: py = -(z)).
    The tree sheet's top view used to draw +z DOWNWARD, so the two pictures a
    reviewer compares were mirrored. Now they agree."""
    assert VR._project((1.0, 0.0, 2.0), "top") == (1.0, 2.0)
