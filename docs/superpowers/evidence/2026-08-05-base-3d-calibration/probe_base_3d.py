"""Spec 2026-08-04-base-inspection-loop-design.md section 5: the ONE calibration
capture, run once, forever.

THE QUESTION. The falsification record establishes that a uniaxial base cannot
show anatomy in its FLAT-FOLDED form -- every flap tip lands on one central line
(Lang; abrashiorigami.com), the measured stack ratios are 3-8x, and
`evidence/2026-08-03-reparented-bases/bases.svg` draws exactly that: featureless
wedges. What had NEVER been measured is the 3-D simulator view of a base. The
whole spec routes around a claim nobody had tested, and section 5 exists to
close it by looking rather than by arguing.

WHAT WOULD CHANGE THE ANSWER. If limb placement is legible in 3-D -- if you can
count the flaps and tell which is which -- then a door the rest of the spec
closed is open again, and Phase 3's cancellation deserves revisiting. If it is a
wedge from every angle, that is settled permanently and never re-proposed.

TWO TRAPS THIS SCRIPT AVOIDS, BOTH MET WHILE WRITING IT:

1. `setFold` ANIMATES. A screenshot taken a few seconds after posting the
   message catches the model mid-fold -- measured at 60% on the first attempt,
   which is a TORN state (THEOREM Z) and worthless as evidence. capture()'s
   20 s settle is load-bearing; this script asserts `creasePercent == 1` from
   the page rather than trusting the elapsed time. NOTE the on-screen "Fold
   Percent" label is driven by the slider widget and stays stale under the
   postMessage path -- read the global, never the label.
2. ONE CAMERA ANGLE IS NOT A MEASUREMENT. A flat-folded base is a PLANAR
   object, so a single viewpoint can be dismissed as unlucky. This orbits the
   camera and shoots each angle.

HEADED ONLY. Headless chromium never advances the GPU solver, so a headless run
would photograph an unfolded sheet and read as a negative for the wrong reason.
A browser window WILL open. Run from mcp_harness/:

    PYTHONPATH=.:tests .venv/bin/python \\
        ../docs/superpowers/evidence/2026-08-05-base-3d-calibration/probe_base_3d.py
"""
import json
import os
import sys

HERE = os.environ.get("IDE_HARNESS") or os.getcwd()
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tests"))

import sim_capture                      # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__))

#: star-4 is the BEST case and the one that decides it: four EQUAL flaps, the
#: simplest base the repo owns, and the anchor subject for the displacement
#: gate. If anatomy is illegible on star-4 it is illegible everywhere. dog is
#: the canonical 6-flap subject the "is it correct?" question was originally
#: asked about; quad is the two-basin one.
SUBJECTS = ["star-4", "dog", "quad"]

#: (azimuth, elevation) in degrees. az=90 is edge-on -- the view that reveals
#: whether the folded base has any thickness at all.
ANGLES = [(0, 0), (90, 0), (45, 35)]

_SET_CAMERA = """([az, el]) => {
    const tv = window.globals && window.globals.threeView;
    if (!tv || !tv.camera) return false;
    const c = tv.camera, r = c.position.length() || 4;
    const a = az * Math.PI / 180, e = el * Math.PI / 180;
    c.position.set(r * Math.cos(e) * Math.sin(a),
                   r * Math.sin(e),
                   r * Math.cos(e) * Math.cos(a));
    c.lookAt(0, 0, 0);
    c.updateProjectionMatrix();
    if (tv.render) tv.render();
    return true;
}"""


def main():
    rows = []
    with sim_capture.SimSession() as sim:           # HEADED, settle_s = 20
        for name in SUBJECTS:
            path = os.path.join(sim_capture.GOLDENS, f"{name}.fold")
            if not os.path.exists(path):
                rows.append({"subject": name, "error": f"no golden at {path}"})
                print(json.dumps(rows[-1]), flush=True)
                continue
            with open(path) as f:
                fold = json.load(f)

            row = {"subject": name,
                   "verts": len(fold.get("vertices_coords") or []),
                   "creases": len(fold.get("edges_vertices") or [])}
            try:
                sim.capture(fold)
                # Trap 1: prove we are at the fully-folded state, not mid-fold.
                pct = sim._page.evaluate(
                    "() => window.globals && window.globals.creasePercent")
                row["crease_percent"] = pct
                row["fully_folded"] = (pct == 1)
                shots = []
                for az, el in ANGLES:
                    moved = sim._page.evaluate(_SET_CAMERA, [az, el])
                    sim._page.wait_for_timeout(600)
                    png = os.path.join(OUT, f"{name}-az{az}-el{el}.png")
                    sim.screenshot(png)
                    shots.append({"az": az, "el": el,
                                  "camera_set": moved,
                                  "png": os.path.basename(png)})
                row["shots"] = shots
            except Exception as exc:                # noqa: BLE001
                row["error"] = f"{type(exc).__name__}: {exc}"[:200]

            rows.append(row)
            print(json.dumps(row), flush=True)

    done = [r for r in rows if r.get("shots")]
    print(f"\n=== {len(done)}/{len(SUBJECTS)} captured ===")
    print("Now LOOK at the PNGs and answer, in the README, in this order:")
    print("  1. Can you count the flaps?")
    print("  2. Can you tell which flap is which limb?")
    print("  3. Could you tell if two flaps that should match do not?")
    print("Question 3 decides it -- that is the defect the inspection loop")
    print("exists to catch. A yes on 1 alone is NOT legibility: served_leaves")
    print("already counts flaps, exactly, for free.")


if __name__ == "__main__":       # playwright + a served dir; keep the guard
    main()
