"""Measure the capped unmirrored search the way pipeline.pack_options runs it.

usage (from mcp_harness/):  python budget_probe.py ROLL BUDGET
Prints one JSON line: symmetric N, cap, outcome, ticks used, seconds of the
unmirrored search alone (symmetric search excluded)."""
import json
import sys
import time

from pleatwright import pack as PK
from pleatwright import pipeline as PL

roll, budget = sys.argv[1], int(float(sys.argv[2]))
src = PL._source(roll)
sf, con, sigma = PL._context(src, 1.0)
n_max = max(2 * PK.grid_init(con), PK.grid_init(con) + 60)
t0 = time.perf_counter()
lay, b, _ = PL._search(con, sigma, symmetric=True, n_max=n_max)
t_sym = time.perf_counter() - t0
cap = lay.N * 10 // 11
out, used, n = "none_below_cap", None, None
t0 = time.perf_counter()
try:
    with PK.work_budget(budget):
        try:
            lay2, b2, _ = PL._search(con, sigma, symmetric=False, n_max=cap)
            if lay2 is not None:
                out, n = "found", lay2.N
        finally:
            used = PK.work_used()
except PK.BudgetExhausted:
    out = "budget"
secs = time.perf_counter() - t0
print(json.dumps({"roll": roll, "budget": budget, "n_sym": lay.N, "cap": cap, "outcome": out,
                  "n_smaller": n, "ticks": used, "secs": round(secs, 2),
                  "sym_secs": round(t_sym, 2), "ticks_per_sec": round(used / secs) if secs else None}))
