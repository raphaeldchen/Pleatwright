"""Tallies from the owner's scores, the good-enough bar, and picker calibration (spec §2).

A cell the owner did not mark is UNSCORED and listed by id. It is never
counted as a fail, so a missed toggle cannot quietly sink an arm.
"""
from __future__ import annotations

import os

from concept_ab import arms as A
from concept_ab import judge
from concept_ab.review import cells, has_mesh
from concept_ab.run import concept_path

#: Ties go to the arm with less machinery: no anatomy text beats anatomy text,
#: and the shipped render template beats the photographic one.
SIMPLICITY = ("B", "C", "D")


def _photo_marked(marks: dict) -> bool:
    return any(c.startswith("photo/") and (m or {}).get("mesh") in ("pass", "fail")
               for c, m in marks.items())


def tally(scores: dict, root: str, photo_scores: dict | None = None) -> dict:
    """`photo_scores`: round 1's scores, whose photo marks set the bar when this
    round's file has none (the photo row is scored once, in round 1). With no
    photo marks anywhere the bar is None and no arm is declared good enough."""
    round_ = scores["round"]
    marks = dict(scores.get("cells", {}))
    if not _photo_marked(marks) and photo_scores:
        marks.update({c: m for c, m in photo_scores.get("cells", {}).items()
                      if c.startswith("photo/")})
    by_arm: dict[str, dict] = {}
    unscored, unlifted = [], []
    for arm, subject, r, cell in cells(root, round_, unlifted=True):
        cid = A.cell_id(arm, subject, r)
        if not has_mesh(cell):                   # the lift failed: a mesh fail of that arm
            unlifted.append(cid)
            row = by_arm.setdefault(arm, {"round": 1 if arm == "photo" else round_,
                                          "passed": 0, "scored": 0})
            row["scored"] += 1
        elif (marks.get(cid) or {}).get("mesh") not in ("pass", "fail"):
            unscored.append(cid)
    for cid, m in marks.items():
        if cid in unlifted:
            continue
        arm = cid.split("/")[0]
        row = by_arm.setdefault(arm, {"round": 1 if arm == "photo" else round_,
                                      "passed": 0, "scored": 0})
        if m.get("mesh") in ("pass", "fail"):
            row["scored"] += 1
            row["passed"] += m["mesh"] == "pass"
        elif cid not in unscored:
            unscored.append(cid)
    photo = by_arm.get("photo", {})
    photo_bar = photo["passed"] if photo.get("scored") else None
    good = {} if photo_bar is None else {
        arm: row["passed"] >= photo_bar - 1 for arm, row in by_arm.items() if arm != "photo"}
    return {"by_arm": by_arm, "photo_bar": photo_bar, "good_enough": good,
            "unscored": sorted(set(unscored)), "unlifted": unlifted}


def winner(t: dict) -> str:
    """The Gemini arm with the most passes; ties go to the simpler arm."""
    present = [a for a in SIMPLICITY if a in t["by_arm"]]
    return max(present, key=lambda a: (t["by_arm"][a]["passed"], -SIMPLICITY.index(a)))


async def calibrate(root: str, client, scores: dict) -> dict:
    """The picker (anatomy text only) against the owner's IMAGE labels on A-D."""
    marks = scores.get("cells", {})
    out = {"agree": 0, "total": 0, "false_reject": 0, "false_accept": 0, "skipped": 0}
    for arm, subject, r, cell in cells(root, scores["round"], unlifted=True):
        cid = A.cell_id(arm, subject, r)
        label = (marks.get(cid) or {}).get("image")
        if arm not in ("A", "B", "C", "D") or label not in ("pass", "fail"):
            continue
        text_path = os.path.join(root, "anatomy", A.slug(subject) + ".txt")
        image = concept_path(cell)
        if not (os.path.exists(text_path) and image):
            out["skipped"] += 1
            continue
        a = await judge.assess(client, image, open(text_path).read().strip())
        picker = "pass" if a["passed"] else "fail"
        out["total"] += 1
        out["agree"] += picker == label
        out["false_reject"] += label == "pass" and picker == "fail"
        out["false_accept"] += label == "fail" and picker == "pass"
    return out
