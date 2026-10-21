"""Does [FIDELITY] ever fire on a REAL compile, or only in a unit test?

THE GAP. path_drift_max reads 0.0 on all five scorecard subjects and the oracle
fires on none. That is not a defect: the stages they reach -- stub, placement,
order -- provably CANNOT move a leaf-to-leaf path (_STAGE_INTEGRITY calls
order/placement proportion-preserving; a stub moves no requested length). Only
jitter, composed and normalize can. So the instrument is correct by
construction, pinned by unit test, and never once OBSERVED. This repo has a
recorded case of a gate staying green while its production call site was
gutted, which is exactly what an unobserved instrument risks becoming.

THIS PROBE ASKS ONE QUESTION: does any real tree, through the real serve path,
reach a stage that can move a path -- and does the oracle see it when it does?

TWO OUTCOMES, BOTH RESULTS. Either some subject lands on jitter/composed/
normalize with drift > 0 and the oracle fires (the tripwire is observed), or
none does, and the honest finding is that the corpus cannot exercise it. DO NOT
lower a threshold to manufacture a firing.

Run from mcp_harness/:

    PYTHONPATH=.:tests .venv/bin/python \\
        ../docs/superpowers/evidence/2026-08-05-fidelity-fires/probe_jitter_drift.py
"""
import json
import os
import sys

HERE = os.environ.get("IDE_HARNESS") or os.getcwd()
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tests"))

import fidelity_oracle                  # noqa: E402
import server                           # noqa: E402

#: Stages that can move a leaf-to-leaf path. Everything else is
#: proportion-preserving or adds anatomy without touching a requested length.
MOVES_A_PATH = {"jitter", "composed", "normalize"}


def _star(k, length):
    return ([{"id": 0, "parent_id": None, "length": 0.0}] +
            [{"id": i, "parent_id": 0, "length": length}
             for i in range(1, k + 1)])


#: Progressively tighter stars: at some flap count / length the exact tree
#: stops packing and the proportion-preserving rungs stop rescuing it, which is
#: where the ladder must reach for a length-moving rung.
CANDIDATES = {
    f"star{k}_len{L}": _star(k, L)
    for k, L in [(5, 0.62), (6, 0.60), (6, 0.66), (7, 0.55),
                 (7, 0.62), (8, 0.52), (8, 0.58)]
}


def main():
    rows = []
    for name, nodes in CANDIDATES.items():
        out = server.draft_and_compile_full_base(nodes, symmetric_pairs=[])
        served = not out.startswith("ERROR:")
        rb = json.loads(server.read_base()) if served else {}
        diff = rb.get("shadow_diff") or {}
        stage = rb.get("stage")
        verdict = (fidelity_oracle.decide(base_report=rb)
                   if rb.get("status") == "ok" else {})
        rows.append({
            "subject": name,
            "served": served,
            "stage": stage,
            "can_move_a_path": stage in MOVES_A_PATH,
            "path_drift_max": diff.get("path_drift_max"),
            "invented": diff.get("invented"),
            "invented_source": diff.get("invented_source"),
            "scale": rb.get("scale"),
            "fidelity_fired": verdict.get("fire"),
            "fidelity_reason": verdict.get("reason"),
        })
        print(json.dumps(rows[-1]), flush=True)

    hit = [r for r in rows if r["can_move_a_path"]]
    fired = [r for r in rows if r.get("fidelity_fired")]
    print(f"\n=== {len(hit)}/{len(rows)} reached a path-moving stage; "
          f"{len(fired)} fired ===")
    if not hit:
        print("NO SUBJECT REACHED jitter/composed/normalize. The tripwire "
              "remains UNOBSERVED in production. That is the finding -- record "
              "it. Do NOT weaken the oracle to manufacture a firing.")
    # Scale is the other half of this run: it read null on every parent-path
    # serve until 2026-08-05, so a non-null column here is the plumbing working.
    print("scale non-null on: "
          f"{sum(1 for r in rows if r.get('scale') is not None)}/{len(rows)}")


if __name__ == "__main__":       # spawns workers -- the guard is MANDATORY
    main()
