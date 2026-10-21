"""The same packing, drawn with and without the packer's own scale.

WHAT THIS SETTLES. `tree_render.packing_diagram` shipped with `scale=1.0` as a
silent keyword default and no caller that passed anything else, so every
diagram the module could produce was drawn at the wrong scale. The question
left open as follow-up 3 of PR #75 -- "give the packing diagram a fair trial on
real data, or delete it" -- could not be answered fairly until a real scale
reached it, which PR #78 made possible by emitting `scale` from the parent
serve path.

This probe draws both, from ONE serve, so the pair differs in exactly one
argument.

READ THE PNGs, NOT ONLY THIS SCRIPT'S NUMBERS. The 1.25x-2.1x oversize-radius
defect that preceded this was found by LOOKING at the image; no assertion in
the test suite caught it. star-4 is the subject that makes correctness
checkable by eye: four flaps of length 1.0 at scale 0.5 must land as four
quarter-discs, one per corner, tangent at the edge midpoints. Gaps or overlaps
there mean the scale is wrong.

Run:
    cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python \\
        ../docs/superpowers/evidence/2026-08-06-packing-diagram-verdict/probe_scaled_vs_unscaled.py
"""
import json
import os
import sys

_HARNESS = os.environ.get("IDE_HARNESS") or os.getcwd()
sys.path.insert(0, _HARNESS)
sys.path.insert(0, os.path.join(_HARNESS, "tests"))

import server                                              # noqa: E402
import tree_render                                         # noqa: E402
from cases import CASES_BY_NAME                            # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__))

#: star-4 is the eye-checkable control (see the module docstring);
#: template-insect is the anatomy-bearing subject with the most flaps.
SUBJECTS = ["star-4", "template-insect"]


def go(name):
    nodes, pairs = CASES_BY_NAME[name]
    served = server.draft_and_compile_full_base(nodes, symmetric_pairs=pairs)
    if isinstance(served, str) and served.startswith("ERROR:"):
        return {"subject": name, "error": served.splitlines()[0][:120]}

    rb = json.loads(server.read_base())
    locs, scale = server.last_serve_locs(), rb.get("scale")
    tree = rb.get("served_tree")            # SERVED, never requested

    a = tree_render.packing_diagram(
        locs, tree, os.path.join(OUT, f"{name}-scaled.png"), scale=scale)
    b = tree_render.packing_diagram(
        locs, tree, os.path.join(OUT, f"{name}-unscaled.png"))

    ra = max(c["r"] for c in a["circles"] if c["r"])
    rb_ = max(c["r"] for c in b["circles"] if c["r"])
    return {
        "subject": name,
        "stage": rb.get("stage"),
        "scale": scale,
        "n_circles": len(a["circles"]),
        "scaled_reports_true": a["scaled"],
        "unscaled_reports_false": b["scaled"],
        # How many times too big the old silent default drew every disc.
        "oversize_factor": round(rb_ / ra, 3),
        "stamp_when_unscaled": b["stamp"].replace("\n", " | "),
    }


def main():
    for name in SUBJECTS:
        print(json.dumps(go(name)), flush=True)
    print(f"\n=== wrote scaled/unscaled pairs to {OUT} ===")


if __name__ == "__main__":       # spawns workers -- the guard is MANDATORY
    main()
