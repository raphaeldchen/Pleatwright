"""Where does dense `assign()` actually spend its time? Measure, do not fit.

WHY THIS EXISTS. `2026-09-26-nogood-indexing-design.md` section 1 apportioned
the 500k and 5M runs' wall clock between "layer check" and "search" using a
constant of 6.4 s/candidate, taken from the dense-pleats spec section 6 and its
evidence README section 4 ("About 6.4 s per candidate"). That constant is WRONG:
it sums one per-candidate cost with two ONE-TIME costs. `constraint_graph` is
cached in `compile._check`'s `graph_cell` and built once (`compile.py:292`), and
`certify` runs once after `assign` returns, outside the CEGAR loop
(`compile.py:347`). The true per-candidate layer cost on `lizard` is
`to_fold + flat_fold + propagate + piece_keys` ~= 1.09 s, not 6.4 s.

The apportionment is brutally sensitive to that constant -- at 6.4 s the
per-node cost appears to grow 4.63x between the two runs (near-proportional to
the 5.17x clause growth, which is what a linear scan would predict), but at the
corrected 1.09 s it grows only ~1.16x, which predicts almost no benefit from
indexing. A two-point fit with a free constant can be made to say either thing,
so this script measures the split directly instead.

WHAT IT MEASURES, per run:
  * `total_secs`            -- the whole `assign()` call
  * `global_check_secs`     -- summed inside the spy: the real per-candidate
                               layer cost (to_fold + flat_fold + propagate +
                               piece_keys), timed from the caller, no estimate
  * `hits_nogood_secs`      -- summed INSIDE `hits_nogood`, plus its call count
  * `remainder_secs`        -- total - global_check - hits_nogood, i.e. the
                               local CSP search itself
Each is reported as a fraction of total. `hits_nogood_secs / total_secs` is the
ceiling on what indexing can remove; if it is small, the indexing spec's premise
is refuted and should be withdrawn rather than implemented.

HOW IT INSTRUMENTS WITHOUT FORKING PRODUCTION. A committed copy of `assign.py`
would drift from production silently. Instead this script READS the real
`box_pleat/assign.py`, applies two textual patches (an accumulator around
`hits_nogood`'s body, and a module-level dict to report it), writes the result
to a temp module, imports that, and -- critically -- ASSERTS that the diff
against production consists only of the lines it added. The patch either applies
to today's source or the script fails loudly; it cannot quietly measure stale
code.

NON-VACUITY. The script refuses to report unless `hits_nogood` was called at
least once and at least one rejection occurred -- a zero-nogood run would
apportion 0% to the scan and "prove" indexing worthless for the wrong reason.

Run from mcp_harness:
  PYTHONPATH=. ../.venv/bin/python3 -u \\
      ../docs/superpowers/evidence/2026-09-26-nogood-indexing/where_the_time_goes.py \\
      lizard <out.json> [budget] [time_cap_secs]
"""
import importlib.util
import json
import os
import pathlib
import statistics
import sys
import time

import flat_fold

from box_pleat import emit
from box_pleat import layers as L
from box_pleat.compile import compile_tree

SUBJECT = sys.argv[1]
OUT = sys.argv[2]
BUDGET = int(sys.argv[3]) if len(sys.argv) > 3 else 500_000
TIME_CAP_SECS = float(sys.argv[4]) if len(sys.argv) > 4 else 3600.0
RULE6 = os.path.join("..", "docs", "superpowers", "evidence",
                     "2026-09-08-vlm-tree-authoring", "data", "rule6_serve.json")

ASSIGN_SRC = pathlib.Path("box_pleat/assign.py")

#: The exact production text of `hits_nogood`, as of 2026-09-26. If this no
#: longer matches, the function has changed and this measurement must be
#: re-derived rather than silently applied to different code.
_ORIG = '''    def hits_nogood() -> bool:
        return any(all(value.get(var) == val for var, val in g.items())
                   for g in nogoods)
'''

#: Same function, wrapped in a timer. `perf_counter` twice per call adds real
#: overhead (~0.1-0.2 us), which INFLATES the measured share -- so the result is
#: an UPPER BOUND on hits_nogood's true cost, which is the safe direction for
#: deciding whether to optimise it.
_PATCHED = '''    def hits_nogood() -> bool:
        _t0 = _perf()
        try:
            return any(all(value.get(var) == val for var, val in g.items())
                       for g in nogoods)
        finally:
            _PROBE["hits_secs"] += _perf() - _t0
            _PROBE["hits_calls"] += 1
'''

#: APPENDED, not prepended: `assign.py` opens with `from __future__ import
#: annotations`, which must be the first statement in the file. `hits_nogood`
#: resolves `_perf` and `_PROBE` as module globals at CALL time, so defining
#: them at the end of the module is correct.
_HEADER = '''

from time import perf_counter as _perf
_PROBE = {"hits_secs": 0.0, "hits_calls": 0}
'''


def build_instrumented():
    """Patch production `assign.py` in memory, verify the diff, import it."""
    src = ASSIGN_SRC.read_text()
    if src.count(_ORIG) != 1:
        raise SystemExit(
            "REFUSING TO MEASURE: hits_nogood's source does not match this "
            "script's expected text exactly once. Production has changed; "
            "re-derive the patch against today's assign.py before trusting "
            "any number from it.")
    patched = src.replace(_ORIG, _PATCHED) + _HEADER

    # Prove the only differences are lines this script added.
    import difflib
    added, removed = [], []
    for line in difflib.unified_diff(src.splitlines(), patched.splitlines(),
                                     lineterm="", n=0):
        if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
            continue
        if line.startswith("+"):
            added.append(line[1:])
        elif line.startswith("-"):
            removed.append(line[1:])
    allowed_removed = set(_ORIG.splitlines())
    unexpected = [r for r in removed if r not in allowed_removed]
    if unexpected:
        raise SystemExit(f"REFUSING TO MEASURE: patch removed unexpected "
                         f"lines: {unexpected}")

    out = pathlib.Path(os.environ.get("TMPDIR", "/tmp")) / "_assign_instrumented.py"
    out.write_text(patched)
    # Loaded under the DOTTED name `box_pleat._assign_instrumented`, not as a
    # standalone module: `assign.py` uses relative imports (`from . import
    # interleave`), which resolve only when `__package__` is `box_pleat`. The
    # dotted name gives it that, and `box_pleat` is already in sys.modules from
    # this script's own imports, so nothing is written into the source tree.
    import box_pleat  # noqa: F401 - must be in sys.modules for the relative imports
    name = "box_pleat._assign_instrumented"
    spec = importlib.util.spec_from_file_location(name, out)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod, len(added), len(removed)


class TimeCapReached(Exception):
    pass


def main():
    entries = {e["subject"]: e for e in json.load(open(RULE6))}
    A, n_added, n_removed = build_instrumented()
    print(f"instrumented assign.py: +{n_added} lines, -{n_removed} lines "
          f"(only hits_nogood's body)", flush=True)

    res = compile_tree(entries[SUBJECT]["requested"], entries[SUBJECT]["pairs"])
    if res.stage_reached != "emit":
        raise SystemExit(f"sparse compile stopped@{res.stage_reached}")

    graph_cell: list = []
    gc_secs = [0.0]
    clause_sizes: list = []
    deadline = [0.0]

    def spy(cand):
        """Production `compile._check`'s call sequence, timed from outside.

        Times EVERYTHING the real filter does per candidate, including the
        one-time `constraint_graph` build on the first candidate only -- which
        is exactly how production pays for it, and the point the 6.4 s figure
        got wrong."""
        t0 = time.perf_counter()
        if time.perf_counter() > deadline[0]:
            raise TimeCapReached()
        fold = emit.to_fold(res.layout, cand)
        ff = flat_fold.flat_fold(fold)
        if not graph_cell:
            graph_cell.append(L.constraint_graph(ff))
        labels = {k: a for _, _, k, a in ff.shared_edges if a in ("M", "V")}
        w = L.propagate(graph_cell[0], labels)
        if w is None:
            gc_secs[0] += time.perf_counter() - t0
            return None
        keys = L.piece_keys(w, fold)
        clause_sizes.append(len(keys))
        gc_secs[0] += time.perf_counter() - t0
        return keys, w

    A._PROBE["hits_secs"] = 0.0
    A._PROBE["hits_calls"] = 0
    t_start = time.perf_counter()
    deadline[0] = t_start + TIME_CAP_SECS
    outcome = {}
    try:
        asg = A.assign(res.layout, res.ridges, res.boundary_ridges, res.contours,
                       dense=True, global_check=spy, layer_checks=100_000,
                       budget=BUDGET)
        outcome = {"kind": "assign_returned", "detail": repr(asg)[:120]}
    except TimeCapReached:
        outcome = {"kind": "time_cap", "detail": f"exceeded {TIME_CAP_SECS}s"}
    total = time.perf_counter() - t_start

    hits_secs = A._PROBE["hits_secs"]
    hits_calls = A._PROBE["hits_calls"]
    rejections = len(clause_sizes)

    if hits_calls == 0 or rejections == 0:
        json.dump({"subject": SUBJECT, "error": "VACUOUS",
                   "hits_calls": hits_calls, "rejections": rejections},
                  open(OUT, "w"), indent=1)
        raise SystemExit("VACUOUS RUN: hits_nogood never called, or no "
                         "rejection occurred -- apportioning 0% to the scan "
                         "here would be an artifact, not a result.")

    remainder = total - gc_secs[0] - hits_secs
    row = {
        "subject": SUBJECT,
        "assign_budget": BUDGET,
        "outcome": outcome,
        "rejections": rejections,
        "total_secs": round(total, 2),
        "global_check_secs": round(gc_secs[0], 2),
        "hits_nogood_secs": round(hits_secs, 2),
        "remainder_secs": round(remainder, 2),
        "global_check_pct": round(100 * gc_secs[0] / total, 2),
        "hits_nogood_pct": round(100 * hits_secs / total, 2),
        "remainder_pct": round(100 * remainder / total, 2),
        "hits_nogood_calls": hits_calls,
        "hits_nogood_us_per_call": round(1e6 * hits_secs / hits_calls, 3),
        "per_candidate_layer_secs": round(gc_secs[0] / rejections, 3),
        "clause_size_median_creases": (statistics.median(clause_sizes)
                                       if clause_sizes else None),
        "note": ("hits_nogood_secs is an UPPER BOUND: the two perf_counter "
                 "calls added per invocation are themselves counted inside it."),
    }
    json.dump(row, open(OUT, "w"), indent=1)
    print(json.dumps(row, indent=1), flush=True)
    print(f"\nCEILING ON INDEXING: {row['hits_nogood_pct']}% of total "
          f"(upper bound).", flush=True)
    print(f"REAL per-candidate layer cost: {row['per_candidate_layer_secs']}s "
          f"(the indexing spec assumed 6.4s).", flush=True)


main()
