"""A/B: does dense layer-ordering converge when the clause is its actual cause?

Spec: `../../specs/2026-09-27-core-in-loop-design.md` section 7.

ONE boolean changes between the arms. Arm A reproduces the committed baseline
(`../2026-09-24-dense-pleats/nogood-lizard.json`: 113 rejections, 834.0 s,
`AssignFail(kind='budget', site=500000)`, median clause 202 solver variables) on
THIS machine in THIS session, so the comparison is not against a quoted figure.

`lizard` is the subject because it is the only one whose loop yields many
rejections cheaply: `octopus` and `dog` do not finish dense labelling inside a
300 s cap at all, and the other subjects' first dense candidate produces a
2-crease blamed set with nothing to shrink.

WHAT THE NUMBERS CAN AND CANNOT SAY. The terminal outcome is the primary signal.
The rejection count is NOT: a run that exhausts its node budget consumes exactly
the budget, so nodes-per-rejection = budget / rejections IDENTICALLY, and the two
are one figure rather than two independent readings. Fewer rejections is the
EXPECTED signature of stronger clauses -- more of the space excluded a priori
means fewer distinct complete candidates -- but it is equally consistent with a
search wandering deeper, so it sizes the follow-on run and establishes nothing on
its own.

Extraction adds seconds per rejection BY CONSTRUCTION, so any wall-clock
comparison between the arms is confounded. Compare outcomes; report seconds as
the experiment's cost.

CoreExtractionError IS A DISTINCT OUTCOME, NOT A REFUSAL. `cores.shrink` raises
it on an unmet precondition, an empty core, or a failed postcondition, and the
class deliberately does not subclass the `ValueError`/`RuntimeError`/`KeyError`
that `compile_tree` catches around `assign`, so it propagates out of
`compile_tree` uncaught by design. Each arm catches exactly that class and
records it as its own outcome: it would mean the clauses that arm learned are
invalid, so NO verdict row may be claimed from that arm. Nothing else is caught,
and the JSON is flushed after each arm so arm A's record survives regardless.

Run from mcp_harness:
  PYTHONPATH=. ../.venv/bin/python3 -u \\
      ../docs/superpowers/evidence/2026-09-27-core-in-loop/ab.py \\
      ../docs/superpowers/evidence/2026-09-27-core-in-loop/ab.json
"""
import json
import os
import statistics
import sys
import time

from box_pleat import cores
from box_pleat.compile import compile_tree

OUT = sys.argv[1]
RULE6 = os.path.join("..", "docs", "superpowers", "evidence",
                     "2026-09-08-vlm-tree-authoring", "data", "rule6_serve.json")
BUDGET = 500_000
BASELINE = {"rejections": 113, "secs": 834.0, "clause_vars_median": 202,
            "outcome": "AssignFail(kind='budget', site=500000)",
            "source": "../2026-09-24-dense-pleats/nogood-lizard.json"}


def _clause_stats(row, clauses):
    if clauses:
        row["clause_vars_min"] = min(clauses)
        row["clause_vars_median"] = statistics.median(clauses)
        row["clause_vars_max"] = max(clauses)


def _core_stats(row, seen):
    if seen:
        row["core_rows"] = seen
        row["blamed_creases_median"] = statistics.median([r[0] for r in seen])
        row["core_creases_median"] = statistics.median([r[1] for r in seen])
        row["oracle_calls_median"] = statistics.median([r[2] for r in seen])
        row["extract_secs_total"] = round(sum(r[3] for r in seen), 1)
        row["extract_secs_median"] = statistics.median([r[3] for r in seen])


def arm(entry, core_extraction):
    clauses: list = []
    seen: list = []
    t0 = time.time()
    try:
        res = compile_tree(entry["requested"], entry["pairs"], dense=True,
                           assign_budget=BUDGET,
                           core_extraction=core_extraction,
                           debug_clause_sizes=clauses,
                           debug_cores=seen if core_extraction else None)
    except cores.CoreExtractionError as exc:
        # A DISTINCT outcome, recorded rather than allowed to abort the script.
        # Extraction refused its own pre/postcondition, so every clause this arm
        # learned is invalid and no section 7.2 row may be claimed from it.
        secs = time.time() - t0
        row = {
            "core_extraction": core_extraction,
            "assign_budget": BUDGET,
            "core_extraction_error": f"{type(exc).__name__}: {exc}",
            "rejections": len(clauses),
            "secs": round(secs, 1),
        }
        _clause_stats(row, clauses)
        _core_stats(row, seen)
        return row
    secs = time.time() - t0
    row = {
        "core_extraction": core_extraction,
        "assign_budget": BUDGET,
        "core_extraction_error": None,
        "stage_reached": res.stage_reached,
        "failure": repr(res.failure),
        "verdict": repr(res.verdict),
        "layers_tried": res.layers_tried,
        "rejections": len(clauses),
        "secs": round(secs, 1),
    }
    _clause_stats(row, clauses)
    # nodes-per-rejection is budget/rejections ONLY when the budget was
    # exhausted; if the run reached a decision it consumed fewer nodes and the
    # division would be meaningless.
    exhausted = "kind='budget'" in row["failure"]
    row["budget_exhausted"] = exhausted
    row["nodes_per_rejection"] = (
        round(BUDGET / len(clauses), 1) if exhausted and clauses else None)
    if core_extraction:
        _core_stats(row, seen)
    return row


def main():
    entry = next(e for e in json.load(open(RULE6))
                 if e["subject"] == "lizard")
    out = {"subject": "lizard", "baseline": BASELINE, "arms": []}

    def flush():
        json.dump(out, open(OUT, "w"), indent=1)

    for extraction in (False, True):
        label = "B (extraction ON)" if extraction else "A (extraction OFF)"
        print(f"=== arm {label} ===", flush=True)
        row = arm(entry, extraction)
        out["arms"].append(row)
        flush()
        if row["core_extraction_error"] is not None:
            print(f"  CORE EXTRACTION ERROR in arm {label}: "
                  f"{row['core_extraction_error']}", flush=True)
        else:
            print(f"  stage={row['stage_reached']} failure={row['failure']}",
                  flush=True)
        print(f"  rejections={row['rejections']} secs={row['secs']} "
              f"clause_vars_median={row.get('clause_vars_median')}", flush=True)
        if extraction:
            print(f"  cone->core creases: "
                  f"{row.get('blamed_creases_median')} -> "
                  f"{row.get('core_creases_median')}  "
                  f"oracle_calls_median={row.get('oracle_calls_median')}  "
                  f"extraction {row.get('extract_secs_total')}s of "
                  f"{row['secs']}s", flush=True)

    a, b = out["arms"]

    print()
    for name, r in (("A", a), ("B", b)):
        print(f"arm {name}: {r['rejections']} rejections, {r['secs']}s, "
              f"clause median {r.get('clause_vars_median')} vars, "
              f"outcome {r.get('failure') or r['core_extraction_error']}")
    print()

    # --- an extraction refusal invalidates the arm that raised it ------------
    errored = [n for n, r in (("A", a), ("B", b))
               if r["core_extraction_error"] is not None]
    if errored:
        out["clause_size_guard_passed"] = False
        out["verdict"] = "CORE EXTRACTION ERROR"
        out["core_extraction_error_arms"] = errored
        flush()
        for n in errored:
            r = a if n == "A" else b
            print(f"CORE EXTRACTION ERROR in arm {n}: "
                  f"{r['core_extraction_error']}")
        print("cores.shrink refused its own pre/postcondition, so the clauses "
              "that arm learned are invalid. NO row of section 7.2 may be "
              "claimed from it, in either direction.")
        return

    # --- the guard that decides whether ANY verdict row may be claimed -------
    guard = (b.get("clause_vars_median") is not None
             and b["clause_vars_median"] < 10)
    out["clause_size_guard_passed"] = guard

    if not guard:
        out["verdict"] = "GUARD FAILED"
        flush()
        print("GUARD FAILED (spec section 7.3): arm B's median clause did not "
              "fall below 10 solver variables, so this run measures a broken "
              "or ineffective extraction rather than a fact about convergence. "
              "NO row of section 7.2 may be claimed, in either direction.")
        return

    if b["stage_reached"] == "emit":
        out["verdict"] = "CONVERGES"
        print("CONVERGES (row 1): dense layer-ordering reached emit. Wire on "
              "for dense; dense-pleats component 1 and its section 10 gallery "
              "become reachable.")
    elif "kind='budget'" not in b["failure"]:
        out["verdict"] = "DECISION NOT TIMEOUT"
        print("DECISION, NOT TIMEOUT (row 2): the search terminated on "
              f"{b['failure']} rather than exhausting its budget. The "
              "mechanism works AND no dense labelling of THIS crease set is "
              "stackable -- which points at the crease set and dense-pleats "
              "component 1, never at dense box-pleating in general.")
    else:
        out["verdict"] = "UNRESOLVED AT THIS BUDGET"
        print("UNRESOLVED AT THIS BUDGET (row 3): the clause narrowed but the "
              "run still exhausted its node budget. Size the 5,000,000-node "
              "run from the measured per-rejection cost below, then decide "
              "whether to spend it.")
        per = (b.get("extract_secs_total", 0.0) / b["rejections"]
               if b["rejections"] else 0)
        print(f"  extraction cost {per:.2f}s per rejection; at 10x the budget "
              f"and arm B's rejection rate that is roughly "
              f"{b['secs'] * 10 / 3600:.1f}h.")

    flush()


main()
