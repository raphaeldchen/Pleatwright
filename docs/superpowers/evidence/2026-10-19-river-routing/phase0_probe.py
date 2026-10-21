"""Phase 0 of the river-routing slice: what can the beside family find?

For each roll, ONE real `pipeline.pack_options(roll, beside=True)` call (today's
search first, unchanged, then the two beside searches).  Today's search result
and each beside search's ticks are captured by wrapping `_pack_options_today`
and `_search_beside` in the worker; no search code is copied.  The budget is
generous (BESIDE_WORK_BUDGET=10M, BESIDE_MAX_BUILDS=400): Phase 0 measures what
the family CAN find, not the provisional budget.

usage (from mcp_harness/):
  PYTHONPATH=. python ../docs/superpowers/evidence/2026-10-19-river-routing/phase0_probe.py \
      [--workers N] [--multi | ROLL...] > phase0.jsonl

--multi selects every artifact tree whose contracted tree has more than one hub.
One JSON line per roll, flushed as it completes (order not guaranteed).
Baseline = ~/Desktop/pleatwright_baseline_4a64d1ad/records.jsonl."""
import argparse
import glob
import json
import multiprocessing as mp
import os
import sys
import time

BASELINE = os.path.expanduser("~/Desktop/pleatwright_baseline_4a64d1ad/records.jsonl")
WORK_BUDGET = 10_000_000
MAX_BUILDS = 400


def _grid(o):
    return None if o is None else o.layout.N


def _baseline(roll):
    try:
        with open(BASELINE) as f:
            for line in f:
                r = json.loads(line)
                if r.get("roll") == roll:
                    lay = r.get("layout") or {}
                    n = {"symmetric": lay.get("n_symmetric"),
                         "smaller": lay.get("n_smaller")}.get(lay.get("chosen"))
                    return {"chosen": lay.get("chosen"), "chosen_grid": n,
                            "n_symmetric": lay.get("n_symmetric"),
                            "n_smaller": lay.get("n_smaller"),
                            "grid_size": r.get("grid_size")}
    except OSError as e:
        return {"error": str(e)}
    return None


def probe(roll):
    from pleatwright import pack as PK
    from pleatwright import pipeline as PL
    PL.BESIDE_WORK_BUDGET = WORK_BUDGET
    PL.BESIDE_MAX_BUILDS = MAX_BUILDS
    out = {"roll": roll, "beside_work_budget": WORK_BUDGET, "beside_max_builds": MAX_BUILDS}
    try:
        cap, ticks = {}, {}
        orig_today, orig_search = PL._pack_options_today, PL._search_beside

        def today_wrap(*a, **k):
            cap["today"] = orig_today(*a, **k)
            return cap["today"]

        def search_wrap(con, sigma, *, symmetric, n_max):
            key = "symmetric" if symmetric else "smaller"
            try:
                return orig_search(con, sigma, symmetric=symmetric, n_max=n_max)
            finally:       # still inside pack_options' work_budget(...) block
                ticks[key] = PK.work_used()
                ticks[key + "_cap"] = n_max

        PL._pack_options_today, PL._search_beside = today_wrap, search_wrap
        t0 = time.perf_counter()
        opts = PL.pack_options(roll, beside=True)
        secs = time.perf_counter() - t0
        t = cap["today"]
        tc = PL._choose(t, "auto", "flag")[0]
        nc, _ = PL._choose(opts, "auto", "flag")
        out.update(
            today={"S": _grid(t.symmetric), "U": t.n_smaller if t.smaller is None else _grid(t.smaller),
                   "verdict": t.verdict, "C": _grid(tc), "family": tc.family if tc else None},
            baseline=_baseline(roll),
            beside=opts.beside,
            new={"S": _grid(opts.symmetric), "U": _grid(opts.smaller), "verdict": opts.verdict,
                 "C": _grid(nc), "chosen": nc.name if nc else None,
                 "family": nc.family if nc else None},
            shrank=(tc is not None and nc is not None and nc.layout.N < tc.layout.N),
            hubs=len(opts.con.hubs), seconds=round(secs, 2), ticks=ticks)
    except Exception as e:                      # recorded, never crashes the pool
        out["error"] = f"{type(e).__name__}: {e}"
    return out


def multi_hub_rolls():
    from pleatwright import pipeline as PL
    from pleatwright import stick as ST
    rolls = []
    for p in sorted(glob.glob(os.path.join(PL.STICKS, "*.json"))):
        if len(ST.contract(ST.load_roll(p, 1.0)).hubs) > 1:
            rolls.append(os.path.basename(p)[:-5])
    return rolls


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("rolls", nargs="*")
    ap.add_argument("--multi", action="store_true", help="every multi-hub artifact tree")
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args(argv)
    rolls = multi_hub_rolls() if a.multi else list(a.rolls)
    print(f"{len(rolls)} rolls selected", file=sys.stderr)
    if not rolls:
        return 1
    with mp.get_context("spawn").Pool(min(a.workers, len(rolls))) as pool:
        for rec in pool.imap_unordered(probe, rolls):
            print(json.dumps(rec), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
