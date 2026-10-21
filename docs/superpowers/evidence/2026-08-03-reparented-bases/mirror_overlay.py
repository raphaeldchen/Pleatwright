"""Regenerate mirror_overlay.svg -- the S1 tripwire sheet (design spec
docs/superpowers/specs/2026-08-04-cp-mirror-metric-design.md sec6) for the
four cases that spec's own acceptance criteria pin: the two genuinely
symmetric controls (star-4 + pairs, HSHAPE) beside the two known-broken ones
(TEMPLATE_QUADRUPED, QUAD).

Added in the fix-wave that closed the gap this evidence directory had been
carrying since the file was first committed: `mirror_overlay.svg` had no
committed generator, `cp_mirror.write_overlay_sheet` had zero call sites, and
this README never mentioned the file. This script is that generator, and it
reproduces the exact one-liner `.superpowers/sdd/task-7-brief.md` Step 5 ran
by hand to originally produce the committed picture.

Reproduce: `PYTHONPATH=.:tests .venv/bin/python \\
  ../docs/superpowers/evidence/2026-08-03-reparented-bases/mirror_overlay.py`
from `mcp_harness/`. Writes `mirror_overlay.svg` into this directory.
"""
import json
import os
import sys

#: Run from mcp_harness/ (PYTHONPATH=.:tests). Resolved from the cwd so this
#: reproduces in any checkout or worktree, matching fold_and_look.py's own
#: HERE resolution beside it.
HERE = os.environ.get("IDE_HARNESS") or os.getcwd()
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tests"))

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "mirror_overlay.svg")

#: (label, attribute on tests.cases) for the four panels. star-4 + pairs and
#: HSHAPE are the design spec's positive controls; TEMPLATE_QUADRUPED and
#: QUAD are its two known-broken cases (SS11.2, SS11.4) -- the same four the
#: original hand-run one-liner rendered.
_CASES = [
    ("star-4 + pairs", lambda cases: cases.symmetric_pairs_star(4, 0.5)),
    ("HSHAPE", lambda cases: cases.HSHAPE),
    ("TEMPLATE_QUADRUPED", lambda cases: cases.TEMPLATE_QUADRUPED),
    ("QUAD", lambda cases: cases.QUAD),
]


def main():
    """Must stay under `if __name__ == "__main__":` below -- it calls
    `server.draft_and_compile_full_base`, which spawns worker processes, the
    same discipline `fold_and_look.py`'s `compile_base` follows."""
    import cases
    import cp_mirror
    import server

    panels = []
    for label, get_case in _CASES:
        nodes, pairs = get_case(cases)
        out = server.draft_and_compile_full_base(
            [dict(n) for n in nodes], [list(p) for p in pairs])
        if out.startswith("ERROR"):
            print(f"skipped {label}: did not serve "
                 f"({out.splitlines()[0][:70]})")
            continue
        panels.append((label, json.loads(out)))

    cp_mirror.write_overlay_sheet(OUT, panels)
    print(f"wrote {OUT} ({len(panels)} panels)")


if __name__ == "__main__":
    main()
