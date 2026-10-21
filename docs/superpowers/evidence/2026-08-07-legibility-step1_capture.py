"""Step 1 of the legibility calibration: 5 HEADED captures.

Protocol pinned in docs/superpowers/evidence/2026-08-07-legibility-calibration-prereg.md
(committed 5598b12 BEFORE this ran).

  BASE   x2  -- one comparison arm + one for the NULL pair
  SHAPED x3  -- shaped re-reads drift +/-7 deg, and front_v18 is a park risk

Each via capture_checked(attempts=3): a read that fails DISP_GATE is retried,
not scored. Saves raw geometry to JSON so rendering + angle computation are
decoupled from the browser (tracked_points is a pure function of (fold, cap)).
"""
import json
import os
import sys

HERE = "<repo>/mcp_harness"
sys.path.insert(0, HERE)
OUT = os.path.dirname(os.path.abspath(__file__))

import shaping                # noqa: E402
import square_complete        # noqa: E402
import sim_capture            # noqa: E402

GOLDEN = os.path.join(HERE, "tests", "goldens", "dog.fold")
# verbatim from docs/superpowers/2026-07-12-handoff-b5-prime-outcome.md
INCUMBENT = "outside:0.0,0.46801304:0.12398308661620648:142.5"


def build():
    with open(GOLDEN) as fh:
        raw = json.load(fh)
    sq = square_complete.complete_square(raw, 1.0, 1.0)
    base = shaping.apply_display_ops(sq, [], raw=raw)
    shaped = shaping.apply_display_ops(sq, [INCUMBENT], raw=raw)
    return raw, base, shaped


def main():
    raw, base, shaped = build()
    print(f"BASE   {len(base['vertices_coords'])}v "
          f"{len(base['edges_vertices'])}e", flush=True)
    print(f"SHAPED {len(shaped['vertices_coords'])}v "
          f"{len(shaped['edges_vertices'])}e", flush=True)

    plan = [("BASE", base), ("BASE", base),
            ("SHAPED", shaped), ("SHAPED", shaped), ("SHAPED", shaped)]

    results = []
    with sim_capture.SimSession() as sim:          # HEADED by default
        for i, (cond, fold) in enumerate(plan):
            log = []
            print(f"[{i}] capturing {cond} ...", flush=True)
            try:
                cap, disp = sim_capture.capture_checked(sim, fold, log,
                                                        attempts=3)
            except Exception as exc:               # noqa: BLE001
                print(f"[{i}] {cond} FAILED: {type(exc).__name__}: {exc}",
                      flush=True)
                results.append({"idx": i, "condition": cond, "ok": False,
                                "error": f"{type(exc).__name__}: {exc}",
                                "attempts": log})
                continue
            print(f"[{i}] {cond} ok  maxDisp={disp:.4f}  "
                  f"verts={len(cap['vertices_coords'])}  attempts={len(log)}",
                  flush=True)
            results.append({
                "idx": i, "condition": cond, "ok": True,
                "maxDisplacement": disp, "attempts": log,
                "vertices_coords": cap.get("vertices_coords"),
                "faces_vertices": cap.get("faces_vertices"),
                "flat_coords": cap.get("flat_coords"),
            })

    payload = {
        "golden": GOLDEN,
        "incumbent_op": INCUMBENT,
        "prereg_commit": "5598b12",
        "n_ok": sum(1 for r in results if r["ok"]),
        "captures": results,
        "base_fold": base,
        "shaped_fold": shaped,
    }
    path = os.path.join(OUT, "captures.json")
    with open(path, "w") as fh:
        json.dump(payload, fh)
    print(f"\nwrote {path}  ({payload['n_ok']}/5 ok)", flush=True)
    return 0 if payload["n_ok"] == 5 else 1


if __name__ == "__main__":
    sys.exit(main())
