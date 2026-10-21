"""Step 0 of the legibility calibration (SIM-FREE).

Assert the B5-prime incumbent site still binds to ITSELF on the served
reference dog, WITH a distance bound -- shaping._find_tip is unbounded
nearest-neighbour (shaping.py:123-127 computes `dist` and returns only the
vertex), so an op aimed at a vanished tip silently lands on another flap and
still reports "applied".

Also emits the exact incumbent op string so the capture step cannot drift
from the measured recipe.
"""
import json
import math
import os
import sys

HERE = "<repo>/mcp_harness"
sys.path.insert(0, HERE)

import shaping                # noqa: E402
import square_complete        # noqa: E402
import pose_base              # noqa: E402

GOLDEN = os.path.join(HERE, "tests", "goldens", "dog.fold")
REF_XY = (0.0, 0.46801304)      # server.py:2262, pinned from B5-prime
REF_THETA = 142.5               # server.py:2285
REF_FRACTION = 0.5
BIND_TOL = 1e-6                 # the bound _find_tip does not apply


def served_dog():
    with open(GOLDEN) as fh:
        raw = json.load(fh)
    sq = square_complete.complete_square(raw, 1.0, 1.0)
    served = shaping.apply_display_ops(sq, [], raw=raw)   # probe_dog_folds path
    return raw, sq, served


def bind_distance(fold, tip_xy):
    """Re-run _find_tip's own scan and RETURN the distance it discards."""
    vc = fold["vertices_coords"]
    ea = fold["edges_assignment"]
    inc = shaping._incidence(fold)
    best = None
    for v, eids in inc.items():
        kinds = [ea[e] for e in eids]
        creases = [e for e in eids if ea[e] in ("M", "V")]
        if "B" not in kinds or len(creases) != 1:
            continue
        if any(k not in ("B", "F", "M", "V") for k in kinds):
            continue
        d = math.hypot(vc[v][0] - tip_xy[0], vc[v][1] - tip_xy[1])
        if best is None or d < best[0]:
            best = (d, v, creases[0])
    return best


def main():
    raw, sq, served = served_dog()
    out = {"golden": GOLDEN, "ref_xy": REF_XY, "bind_tol": BIND_TOL}

    # --- how many tips are addressable, raw vs served
    raw_tips = pose_base.candidate_tips(raw)
    served_tips = pose_base.candidate_tips(served)
    out["n_tips_raw"] = len(raw_tips)
    out["n_tips_served"] = len(served_tips)

    # --- the binding check WITH the bound
    best = bind_distance(served, REF_XY)
    dist, vid, crease = best
    vc = served["vertices_coords"]
    out["bound_vertex"] = vid
    out["bound_xy"] = [round(vc[vid][0], 10), round(vc[vid][1], 10)]
    out["bind_distance"] = dist
    out["binds_to_itself"] = bool(dist <= BIND_TOL)

    # --- what _find_tip itself returns (must agree on the vertex)
    fv, fe = shaping._find_tip(served, REF_XY)
    out["find_tip_agrees"] = bool(fv == vid and fe == crease)

    # --- the incumbent op string, reconstructed exactly as the tool does
    ax = shaping.axial_length(served, REF_XY)
    d = REF_FRACTION * ax
    out["axial_length"] = ax
    out["d_baked"] = d
    out["incumbent_op"] = f"outside:{REF_XY[0]},{REF_XY[1]}:{d}:{REF_THETA}"

    # --- does the op actually apply on this fold (geometric refusals)?
    try:
        shaped = shaping.apply_display_ops(sq, [out["incumbent_op"]], raw=raw)
        out["op_applies"] = True
        out["shaped_n_vertices"] = len(shaped["vertices_coords"])
        out["shaped_n_edges"] = len(shaped["edges_vertices"])
        out["served_n_vertices"] = len(served["vertices_coords"])
        out["served_n_edges"] = len(served["edges_vertices"])
        # partial angles actually present?
        fa = shaped.get("edges_foldAngle") or []
        partial = [a for a in fa if abs(abs(a) - 180.0) > 1e-9 and abs(a) > 1e-9]
        out["n_partial_fold_angles"] = len(partial)
        out["partial_fold_angles"] = sorted(set(round(a, 6) for a in partial))
    except Exception as exc:                       # noqa: BLE001
        out["op_applies"] = False
        out["op_error"] = f"{type(exc).__name__}: {exc}"

    # --- the named-site view (tier-1 reference test the tool uses)
    try:
        nb = pose_base.NamedBase(raw, sq, pose_base.DOG_CONFIG)
        s18 = nb.sites.get("front_v18")
        out["named_sites"] = sorted(nb.sites)
        if s18 is not None:
            out["front_v18_xy"] = list(s18.xy)
            out["front_v18_matches_ref"] = bool(
                abs(s18.xy[0] - REF_XY[0]) < 1e-8
                and abs(s18.xy[1] - REF_XY[1]) < 1e-8)
    except Exception as exc:                       # noqa: BLE001
        out["named_error"] = f"{type(exc).__name__}: {exc}"

    print(json.dumps(out, indent=2))
    ok = out.get("binds_to_itself") and out.get("op_applies")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
