"""Re-test the legibility question on a base compiled by the CURRENT pipeline.

The committed golden `tests/goldens/dog.fold` was last touched 2026-07-03 --
BEFORE the perfect-base slices (S1-S8, Jul 25-31) and before goals 1 & 2. Its
source tree is recorded as unrecoverable, and perfect-base S4 recorded that it
"concealed 2 of 3 blockers". So it is a fair objection that the legibility FAIL
was measured on a stale artifact.

This compiles a fresh QUADRUPED through server.draft_and_compile_full_base --
the REAL serve path including the rescue ladder (memory: bare HeadlessTreemaker
is NOT the serve path; it has bitten this repo three times).

Real script file with a __main__ guard: this path uses spawn workers, and a
heredoc/`python -` cannot parent them (the child re-runs <stdin>).
"""
import json
import os
import sys

HERE = "<repo>/mcp_harness"
sys.path.insert(0, HERE)
OUT = os.path.dirname(os.path.abspath(__file__))


def main():
    import server
    import body_plans
    import square_complete
    import shaping
    import paper_coverage

    spec = body_plans.describe("quadruped", 1.0)
    nodes = spec["tree_nodes"]
    pairs = spec.get("symmetric_pairs")
    print(f"template quadruped: {len(nodes)} nodes, pairs={pairs}")

    fold_str = server.draft_and_compile_full_base(nodes, pairs)
    if fold_str.startswith("ERROR"):
        print("COMPILE FAILED:", fold_str[:400])
        return 1
    raw = json.loads(fold_str)
    print(f"fresh raw: {len(raw['vertices_coords'])}v "
          f"{len(raw['edges_vertices'])}e")

    # provenance / quality readouts, so we can say whether this base is
    # actually 'better' than the golden on the axes goals 1 & 2 own
    for nm, f in (("golden-dog", json.load(open(os.path.join(
                        HERE, "tests", "goldens", "dog.fold")))),
                  ("fresh-quad", raw)):
        try:
            cov = paper_coverage.paper_coverage(f)
            print(f"  {nm}: hull_coverage="
                  f"{cov.get('hull_coverage')}  source={cov.get('source')}")
        except Exception as exc:                      # noqa: BLE001
            print(f"  {nm}: coverage n/a ({type(exc).__name__}: {exc})")

    sq = square_complete.complete_square(raw, 1.0, 1.0)
    base = shaping.apply_display_ops(sq, [], raw=raw)

    # shape it: pick the LONGEST-axial front-ish tip available, same recipe
    # family as the incumbent (outside reverse, theta 142.5, half the axial)
    import pose_base
    tips = pose_base.candidate_tips(base)
    vc = base["vertices_coords"]
    best = None
    for t in tips:
        xy = (vc[t][0], vc[t][1])
        try:
            ax = shaping.axial_length(base, xy)
        except Exception:                             # noqa: BLE001
            continue
        if best is None or ax > best[0]:
            best = (ax, xy)
    if best is None:
        print("no shapeable tip on the fresh base")
        return 1
    ax, xy = best
    op = f"outside:{xy[0]},{xy[1]}:{0.5*ax}:142.5"
    print(f"fresh base tips: {len(tips)}; chosen axial {ax:.6f}\n op {op}")
    shaped = shaping.apply_display_ops(sq, [op], raw=raw)

    payload = {"op": op, "fresh_raw": raw, "captures": []}
    import sim_capture
    with sim_capture.SimSession() as sim:
        for nm, fold in (("FRESH_BASE", base), ("FRESH_SHAPED", shaped)):
            log = []
            print(f"capturing {nm} ...", flush=True)
            try:
                cap, disp = sim_capture.capture_checked(sim, fold, log,
                                                        attempts=3)
            except Exception as exc:                  # noqa: BLE001
                print(f"{nm} FAILED: {exc}", flush=True)
                continue
            print(f"{nm} ok maxDisp={disp:.4f}", flush=True)
            payload["captures"].append({
                "condition": nm, "ok": True, "maxDisplacement": disp,
                "vertices_coords": cap.get("vertices_coords"),
                "faces_vertices": cap.get("faces_vertices"),
                "flat_coords": cap.get("flat_coords")})

    with open(os.path.join(OUT, "captures_fresh.json"), "w") as fh:
        json.dump(payload, fh)
    print(f"\nwrote captures_fresh.json ({len(payload['captures'])}/2)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
