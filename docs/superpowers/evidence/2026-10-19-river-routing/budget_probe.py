"""Task 7 of the river-routing slice: calibrate the beside budget and build cap.

One real `pipeline.pack_options(roll, beside=True)` call per roll, at the given
BESIDE_WORK_BUDGET / BESIDE_MAX_BUILDS (default: Phase 0's generous 10M / 400).
`_search_beside` and `base.build` are wrapped (not copied) to record, per beside
search: packer ticks, `base.build` calls made, outcome and seconds of the
search alone.  Also the seconds of the whole call and the host load average.

usage (from mcp_harness/):
  PYTHONPATH=. python ../docs/superpowers/evidence/2026-10-19-river-routing/budget_probe.py \
      [--budget 10e6] [--max-builds 400] ROLL... > out.jsonl
Run ONE roll at a time (single process) for honest seconds."""
import argparse
import json
import os
import sys
import time


def probe(roll, budget, max_builds):
    from pleatwright import base as B
    from pleatwright import pack as PK
    from pleatwright import pipeline as PL
    PL.BESIDE_WORK_BUDGET = budget
    PL.BESIDE_MAX_BUILDS = max_builds
    out = {"roll": roll, "budget": budget, "max_builds": max_builds,
           "load_before": os.getloadavg()[0]}
    searches, state = {}, {"builds": 0}
    orig_build, orig_search, orig_today = B.build, PL._search_beside, PL._pack_options_today

    def build_wrap(*a, **k):
        state["builds"] += 1
        return orig_build(*a, **k)

    def search_wrap(con, sigma, *, symmetric, n_max):
        key = "symmetric" if symmetric else "smaller"
        state["builds"] = 0
        t0, res = time.perf_counter(), "none_below_cap"
        try:
            r = orig_search(con, sigma, symmetric=symmetric, n_max=n_max)
            if r[0] is not None:
                res = r[0].N
            return r
        except PK.BudgetExhausted:
            res = "budget"
            raise
        except PL._BuildCap:
            res = "builds"
            raise
        finally:
            searches[key] = {"cap": n_max, "outcome": res, "builds": state["builds"],
                             "ticks": PK.work_used(), "secs": round(time.perf_counter() - t0, 2)}

    t_today = {}

    def today_wrap(*a, **k):
        t0 = time.perf_counter()
        try:
            return orig_today(*a, **k)
        finally:
            t_today["secs"] = round(time.perf_counter() - t0, 2)

    B.build, PL._search_beside, PL._pack_options_today = build_wrap, search_wrap, today_wrap
    try:
        t0 = time.perf_counter()
        opts = PL.pack_options(roll, beside=True)
        secs = time.perf_counter() - t0
        nc, _ = PL._choose(opts, "auto", "flag")
        out.update(searches=searches, today_secs=t_today.get("secs"), call_secs=round(secs, 2),
                   beside=opts.beside, verdict=opts.verdict,
                   chosen_grid=nc.layout.N if nc else None,
                   chosen_family=nc.family if nc else None,
                   S=opts.symmetric.layout.N if opts.symmetric else None,
                   U=opts.smaller.layout.N if opts.smaller else None)
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"
    out["load_after"] = os.getloadavg()[0]
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("rolls", nargs="+")
    ap.add_argument("--budget", type=float, default=10e6)
    ap.add_argument("--max-builds", type=int, default=400)
    a = ap.parse_args(argv)
    for roll in a.rolls:
        print(json.dumps(probe(roll, int(a.budget), a.max_builds)), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
