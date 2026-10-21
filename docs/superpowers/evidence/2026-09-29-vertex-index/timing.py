"""Timing re-measurement for the vertex index: interleaved, min-of-3.

WHY THIS EXISTS. `ab.json`'s timing half was recorded under machine load
(`dog` sparse off read 902.5 s against a committed 537.3 s, load average
peaking at 12.1), from ONE non-interleaved reading per arm. Its identity half
is load-independent and valid; this script does not touch it and does not
re-check it. `ab.py` and `ab.json` are left byte-for-byte alone.

DESIGN.
  * Same subjects, same order, same fixture and same BUDGET as `ab.py`; all
    three are IMPORTED from it so they cannot drift. BUDGET is not a knob: the
    speedup grows with the budget (1.45x at 4,000 nodes vs 2.43x at 20,000 on
    dense `lizard`), so a cheaper run would understate it.
  * THREE repeats per arm, INTERLEAVED (off,on,off,on,off,on), so load drifting
    during a subject lands on both arms instead of one.
  * ESTIMATOR = MINIMUM. Interference can only make a run slower, never
    faster, so the minimum is the least contaminated reading. Every reading is
    recorded and the spread (max/min) is reported per arm so noise is visible.
  * Both clocks: wall clock of the whole `compile_tree`, and
    `Result.timings["assign"]`.
  * Every debug channel OFF (no `debug_search`): an instrumented arm cannot be
    timed.
  * Load average recorded at the start and end of every subject and at each
    reading, so contamination is visible in the artifact.
  * JSON flushed after every subject; a subject that errors is recorded and
    the corpus continues.
"""
from __future__ import annotations

import datetime
import json
import os
import pathlib
import subprocess
import sys
import time

_HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parents[3] / "mcp_harness"))

import ab                                              # noqa: E402
from box_pleat.compile import compile_tree             # noqa: E402

SUBJECTS = ab.SUBJECTS
BUDGET = ab.BUDGET
RULE6 = ab.RULE6
REPEATS = 3
ESTIMATOR = "min of 3"


def _commit() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True, check=True, cwd=_HERE).stdout.strip()


def _load():
    return [round(x, 2) for x in os.getloadavg()]


def est_min(readings):
    """The estimator: the MINIMUM of the usable readings, or None.

    Non-numeric entries (a failed repeat recorded as None) are ignored; if no
    usable reading is left the answer is None, never 0.
    """
    vals = [r for r in readings if isinstance(r, (int, float))]
    return min(vals) if vals else None


def spread(readings):
    """`max/min` of the usable readings, rounded to 3 places.

    1.0 means perfectly repeatable. None when there is no usable reading or
    the minimum is not positive (a ratio against zero is meaningless).
    """
    vals = [r for r in readings if isinstance(r, (int, float))]
    if not vals or min(vals) <= 0:
        return None
    return round(max(vals) / min(vals), 3)


def speedup(off_secs, on_secs):
    """`off / on`, or None when either side has no usable positive time."""
    for v in (off_secs, on_secs):
        if not isinstance(v, (int, float)) or isinstance(v, bool) or v <= 0:
            return None
    return round(off_secs / on_secs, 3)


def _arm_summary(readings):
    return {"readings": readings, "min": est_min(readings),
            "spread_max_over_min": spread(readings)}


def measure_mode(entry, dense: bool) -> dict:
    """REPEATS interleaved off/on pairs of one mode (dense or sparse)."""
    kw_common = {"dense": True, "assign_budget": BUDGET} if dense else {}
    wall = {"off": [], "on": []}
    assign = {"off": [], "on": []}
    stage = {"off": [], "on": []}
    load = []
    for _ in range(REPEATS):
        for label, extra in (("off", {}), ("on", {"vertex_index": True})):
            t = time.perf_counter()
            res = compile_tree(entry["requested"], entry["pairs"],
                               **kw_common, **extra)
            wall[label].append(round(time.perf_counter() - t, 2))
            assign[label].append(res.timings.get("assign"))
            stage[label].append(res.stage_reached)
            load.append({"after": f"{label}#{len(wall[label])}",
                         "loadavg": _load()})
    out = {"wall": {k: _arm_summary(v) for k, v in wall.items()},
           "assign": {k: _arm_summary(v) for k, v in assign.items()},
           "stage_reached": stage, "load_per_reading": load}
    out["wall_speedup_min"] = speedup(out["wall"]["off"]["min"],
                                      out["wall"]["on"]["min"])
    out["assign_speedup_min"] = speedup(out["assign"]["off"]["min"],
                                        out["assign"]["on"]["min"])
    return out


def _selftest():
    # MIN, NOT MEAN. One contaminated outlier: mean 40.0, min 10.0. A
    # mean-based estimator returns 40.0 and fails the first assertion.
    r = [10.0, 10.0, 100.0]
    assert est_min(r) == 10.0, est_min(r)
    assert est_min(r) != sum(r) / len(r), "estimator is the mean"
    assert sum(r) / len(r) == 40.0            # the case really distinguishes
    # Order-independence: the minimum is not "the first reading".
    assert est_min([30.0, 10.0, 20.0]) == 10.0
    assert est_min([10.0, 20.0, 30.0]) == 10.0
    # A single reading is its own minimum and spread is exactly 1.
    assert est_min([7.5]) == 7.5
    assert spread([7.5]) == 1.0
    # No usable reading -> None, never 0.
    assert est_min([]) is None and spread([]) is None
    assert est_min([None, None]) is None
    # A failed repeat (None) is ignored, not coerced.
    assert est_min([None, 4.0, 6.0]) == 4.0
    assert spread([None, 4.0, 6.0]) == 1.5
    # Spread is max/min.
    assert spread([10.0, 10.0, 100.0]) == 10.0
    assert spread([2.0, 3.0]) == 1.5
    assert spread([0.0, 5.0]) is None, "spread divided by a zero minimum"
    # Speedup, and its refusals.
    assert speedup(10.0, 5.0) == 2.0
    assert speedup(10.0, 0) is None
    assert speedup(0, 5.0) is None
    assert speedup(-1.0, 5.0) is None
    assert speedup(10.0, -5.0) is None
    assert speedup(None, 5.0) is None
    assert speedup(10.0, None) is None
    assert speedup(True, 5.0) is None, "a bool was accepted as a duration"
    # A min-based speedup differs from a mean-based one on contaminated data,
    # so a swap to the mean would move this number.
    off, on = [10.0, 10.0, 100.0], [5.0, 5.0, 5.0]
    assert speedup(est_min(off), est_min(on)) == 2.0
    assert speedup(sum(off) / 3, sum(on) / 3) == 8.0
    # Shared constants come from ab.py rather than being re-derived.
    assert SUBJECTS == ("starfish", "lizard", "frog", "horse", "bird",
                        "guinea_pig", "octopus", "dog")
    assert BUDGET == 20_000
    assert RULE6.exists(), RULE6
    print("selftest OK: est_min (10 incl. mean-vs-min and single reading), "
          "spread (6), speedup (10 incl. mean-vs-min), constants (3)")


def main(out_path):
    entries = {e["subject"]: e for e in json.load(open(RULE6))}
    rec = {
        "measured_utc": datetime.datetime.now(datetime.UTC).isoformat(
            timespec="seconds"),
        "commit": _commit(),
        "budget": BUDGET,
        "repeats": REPEATS,
        "estimator": ESTIMATOR,
        "interleaving": "off,on,off,on,off,on within each mode of each subject",
        "fixture": str(RULE6.relative_to(_HERE.parents[3])),
        "debug_channels": "all off (no debug_search)",
        "loadavg_at_start": _load(),
        "rows": [],
    }

    def flush():
        with open(out_path, "w") as fh:
            json.dump(rec, fh, indent=1)

    flush()
    for s in SUBJECTS:
        row = {"subject": s, "loadavg_start": _load()}
        # Separate guards: a dense failure must not cost the sparse arm.
        for mode in ("dense", "sparse"):
            try:
                row[mode] = measure_mode(entries[s], dense=(mode == "dense"))
            except Exception as exc:                   # noqa: BLE001
                row[f"{mode}_error"] = f"{type(exc).__name__}: {exc}"[:400]
        row["loadavg_end"] = _load()
        rec["rows"].append(row)
        flush()
        parts = []
        for mode in ("dense", "sparse"):
            m = row.get(mode)
            if m is None:
                parts.append(f"{mode} ERROR {row.get(mode + '_error')}")
            else:
                parts.append(
                    f"{mode} wall min {m['wall']['off']['min']} -> "
                    f"{m['wall']['on']['min']} ({m['wall_speedup_min']}x), "
                    f"assign {m['assign']['off']['min']} -> "
                    f"{m['assign']['on']['min']} ({m['assign_speedup_min']}x)")
        print(f"{s}: " + " | ".join(parts)
              + f" | load {row['loadavg_start']} -> {row['loadavg_end']}",
              flush=True)
    rec["loadavg_at_end"] = _load()
    flush()


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    elif len(sys.argv) < 2:
        print("usage: timing.py <out.json> | timing.py --selftest",
              file=sys.stderr)
        raise SystemExit(1)
    else:
        main(sys.argv[1])
