"""What could the learned clauses have pruned during descent, and don't?

Spec: `../../specs/2026-09-30-clause-propagation-design.md`.

THE DEFECT. `assign`'s `hits_nogood()` is
`any(all(value.get(var) == val ...) for g in nogoods)`, so a clause with ANY
unbound variable reads `None` for it and is inert -- it can only fire when its
LAST variable is bound to the forbidden value. The solver has clause learning
and NO propagation.

WHY THE TWO OBVIOUS EXPLANATIONS DO NOT APPLY. Dense non-convergence is not
speed: the local CSP was 79.57% of runtime and the vertex index made the dense
corpus 5.740x faster with identity 8/8, and dense still does not converge
(`../2026-09-29-vertex-index/`). It is not clause width either: core
extraction narrowed the median clause 25.2x, 202 -> 8 solver variables, and
both arms still end on `AssignFail(kind='budget', site=500000)`
(`../2026-09-27-core-in-loop/`). What is left is that the clauses are applied
too LATE.

IDENTITY BEFORE ANY FIGURE (spec 8.2). Arm A must reproduce 113 rejections and
arm B 3, both ending on the node budget, against the committed control. A
figure from an arm that failed identity is not a measurement -- the arm solved
a different problem. `verdict()` refuses to name a band when identity failed.

EVERY HEADLINE IS A LOWER BOUND, twice over: only clauses ALREADY unit are
considered, and the cascade is ONE step, never a fixpoint. `dead_node_fraction`
is therefore never a predicted speedup -- a real propagator would change the
search path, so the node count it would reach is not derivable from here.

THE BREADTH BUDGET IS PESSIMISTIC BY CONSTRUCTION. Clause availability grows
with nodes, so the 50,000-node breadth arms UNDERSTATE it. A null breadth
result is weaker evidence than a positive one, and the README must say so.
"""
from __future__ import annotations

import datetime
import json
import os
import pathlib
import signal
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4] / "mcp_harness"))

from box_pleat.compile import compile_tree            # noqa: E402

RULE6 = (pathlib.Path(__file__).resolve().parents[4] / "docs" / "superpowers"
         / "evidence" / "2026-09-08-vlm-tree-authoring" / "data"
         / "rule6_serve.json")

#: Dense `lizard` at the real budget, both arms -- like-for-like with
#: `../2026-09-27-core-in-loop/`, whose figures are the control.
PRIMARY = "lizard"
PRIMARY_BUDGET = 500_000

#: The primary arms of the run plan, `core_extraction` per arm: A is extraction
#: off, B is extraction on. `main` builds the primary plan from this tuple and
#: `identity` requires one CHECKED row per entry, so the number of arms the
#: gate demands is the number the plan runs and cannot drift from it.
PRIMARY_ARMS = (False, True)

#: Arm A only, reduced budget. `octopus` and `dog` are excluded although they
#: too reach `assign` in dense: neither completed the dense labelling audit
#: (`../2026-09-24-dense-pleats/dense_labelling.json` carries no `dense_mv`
#: for either), so there is no dense control to compare a reading against.
BREADTH = ("frog", "horse", "bird", "guinea_pig")
BREADTH_BUDGET = 50_000

#: Spec 8.3. An unbounded run is why the pleat-filter halt table still has no
#: committed script. On expiry the arm records `truncated` and keeps the
#: partial measurement -- which survives because `ClauseIndex` writes into the
#: caller's dict every node rather than returning a summary at the end.
ARM_CAP_SECS = 1800.0

#: The committed control, `../2026-09-27-core-in-loop/ab.json`, keyed by
#: `core_extraction`. Arm A's 113 rejections reproduce the baseline exactly
#: there; arm B's clause-variable multiset is {5, 8, 8}.
BASELINE = {
    False: {"rejections": 113},
    True: {"rejections": 3, "clause_sizes": [5, 8, 8]},
}

#: Spec 4, fixed before any data existed. Descending thresholds.
BANDS = ((0.50, "PROPAGATION IS THE LEVER"),
         (0.05, "REAL BUT PARTIAL"),
         (0.00, "PROPAGATION REFUTED"))

#: Spec 4's attribution guard.
UNIT_GUARD = 0.01


class ArmTimeout(Exception):
    """The per-arm wall-clock cap expired.

    Subclasses `Exception` and NOT `RuntimeError`, so it escapes
    `compile_tree`'s `except (ValueError, RuntimeError, KeyError)`: a
    truncation must be recorded as a truncation, never folded into
    `AssignFail("error")`.
    """


def _alarm(signum, frame):
    raise ArmTimeout()


REPO = pathlib.Path(__file__).resolve().parents[4]


def _commit() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True, check=True, cwd=REPO).stdout.strip()


def _dirty(out_path: str) -> dict:
    """Whether the tree differs from the recorded `commit`. `commit` alone
    reads as a clean provenance even when the runner that produced the
    figures was an uncommitted edit, so the artifact states it. Untracked
    files count (a brand-new uncommitted runner is untracked), except the
    artifact's own output path, which a re-run would otherwise report as
    dirt it created itself."""
    res = subprocess.run(["git", "status", "--porcelain"], capture_output=True,
                         text=True, check=True, cwd=REPO)
    out = pathlib.Path(out_path).resolve()
    lines = []
    for ln in res.stdout.splitlines():
        if (REPO / ln[3:].strip().strip('"')).resolve() == out:
            continue
        lines.append(ln)
    return {"dirty": bool(lines), "dirty_paths": lines}


def _fail(f) -> dict | None:
    if f is None:
        return None
    return {"kind": getattr(f, "kind", None),
            "site": repr(getattr(f, "site", None))}


#: The out-dict keys `ClauseIndex.observe` writes UNCONDITIONALLY, on every
#: node it observes, so after any run that observed one node all of them are
#: present. Their absence means the instrument did not run (never constructed
#: on this path, the out-dict never passed, or `observe` never reached), and
#: nothing may default them: a defaulted `nodes` is how a dead instrument
#: becomes a `0.0` fraction, and `0.0 < 0.05` is "PROPAGATION REFUTED".
#:
#: The counters `unit_nodes`, `dead_nodes`, `unit_domain_*` and
#: `unit_var_chosen_nodes` are deliberately NOT in this tuple: `observe` creates
#: them lazily, the first time the event occurs, so a run with no unit node
#: legitimately has no `unit_nodes` key and `.get(..., 0)` is the correct read
#: for them. Whether the instrument ran is decided by the keys below.
REQUIRED_RAW = ("nodes", "live_total", "clauses_total", "probe_calls",
                "probe_secs", "observe_secs")


def instrument_gaps(prop: dict) -> list:
    """The `REQUIRED_RAW` keys absent from the index's out-dict, in order. One
    definition, called by `derived` (which records the answer on the row and
    refuses to compute a figure from absent keys) and by `identity` (which
    re-evaluates it on the row's `raw` block and does not trust the recorded
    flag, so an edited artifact cannot launder a gap)."""
    return [k for k in REQUIRED_RAW if k not in prop]


def derived(prop: dict, n_clauses: int) -> dict:
    """The spec 3.3 fractions. Computed here, not in the index: the index
    reports raw counts and is never asked what its own headline is.

    `n_clauses` is `len(debug_clause_sizes)`, the number of no-good clauses the
    solver actually stored, and it is the AUTHORITATIVE clause count: it is
    reported as `clauses_total`, and every consumer (the smoke check, `verdict`
    and the README) reads that key. The index's own `prop["clauses_total"]` is
    kept beside it as `clauses_total_observed` and is NOT interchangeable,
    because `ClauseIndex.observe` snapshots `len(self.size)` at the TOP of the
    solver's main loop, once per node. A clause learned on the LAST node --
    `nogoods.append` -> `add_clause` -> `retry()` returns False -> `return
    AssignFail("layer_unsat")` -- is appended after the final `observe` and
    never loops back to another, so the observed value can be one short. Any
    per-clause figure derived from the observed value would be inflated by
    1/n_clauses; with a handful of clauses (arm B stores 3) that is a third.
    The hook stays at the top of the loop (that is where the state a node
    inherited is visible); the discrepancy is corrected here, in the
    reporting, and left inspectable rather than hidden."""
    gaps = instrument_gaps(prop)
    out = {"instrument_ok": not gaps, "instrument_missing": gaps,
           "clauses_total": n_clauses}
    if gaps:
        # No figure from an instrument that did not report. Not zeros: absent.
        return out
    n = prop["nodes"]
    out = {
        "instrument_ok": True,
        "instrument_missing": [],
        "nodes": n,
        "unit_domain_2": prop.get("unit_domain_2", 0),
        "unit_domain_3": prop.get("unit_domain_3", 0),
        "unit_domain_other": prop.get("unit_domain_other", 0),
        "probe_calls": prop["probe_calls"],
        #: `probe_secs` = inside `probe()` only. `observe_secs` = the whole of
        #: `observe()`, including the work `probe_secs` cannot see: the
        #: OBSERVE-SIDE cost, not the total overhead (it excludes the
        #: bind/unbind/add_clause counter updates). >= `probe_secs` while
        #: probes run only through `observe`, which the runner guarantees.
        "probe_secs": round(prop["probe_secs"], 2),
        "observe_secs": round(prop["observe_secs"], 2),
        "clauses_total": n_clauses,
        "clauses_total_observed": prop["clauses_total"],
    }
    if not n:
        return out
    out["unit_node_fraction"] = round(prop.get("unit_nodes", 0) / n, 6)
    out["dead_node_fraction"] = round(prop.get("dead_nodes", 0) / n, 6)
    out["unit_var_chosen_fraction"] = round(
        prop.get("unit_var_chosen_nodes", 0) / n, 6)
    out["clause_availability"] = round(prop["live_total"] / n, 4)
    return out


def run_arm(entry, *, core_extraction: bool, budget: int) -> dict:
    """One dense arm. `vertex_index=True`: dense `lizard` measured 2.449x wall
    with identity byte-identical 8/8, so the search path is the same and the
    measurement is unaffected (`../2026-09-29-vertex-index/timing.json`)."""
    prop: dict = {}
    sizes: list = []
    row = {"subject": entry["subject"], "core_extraction": core_extraction,
           "budget": budget, "truncated": False, "loadavg": os.getloadavg()}
    signal.signal(signal.SIGALRM, _alarm)
    signal.setitimer(signal.ITIMER_REAL, ARM_CAP_SECS)
    t0 = time.perf_counter()
    try:
        res = compile_tree(entry["requested"], entry["pairs"], dense=True,
                           assign_budget=budget, vertex_index=True,
                           core_extraction=core_extraction,
                           debug_clause_sizes=sizes,
                           # clause_prop_verify is deliberately NOT set:
                           # verify() is O(clauses x nodes), prohibitive at
                           # 500,000 nodes. Counter correctness was checked
                           # only at 20,000 nodes / 10 rejections (Task 3
                           # gate), so it is NOT established at this budget
                           # (README s1 and s8).
                           clause_prop=prop)
        row["stage_reached"] = res.stage_reached
        row["assign_fail"] = _fail(res.failure)
        row["layers_tried"] = res.layers_tried
    except ArmTimeout:
        row["truncated"] = True
        row["stage_reached"] = None
        row["assign_fail"] = None
        row["layers_tried"] = None
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        row["secs"] = round(time.perf_counter() - t0, 1)
    row["rejections"] = len(sizes)
    row["clause_sizes"] = sorted(sizes)
    #: `raw` is the index's own out-dict verbatim, so `raw["clauses_total"]`
    #: is the OBSERVED value (see `derived`). Read the clause count from the
    #: row's `clauses_total`, never from `raw`.
    row["raw"] = dict(prop)
    row.update(derived(prop, len(sizes)))
    return row


def identity(rows: list) -> dict:
    """Spec 8.2. The gate is BOTH primary arms reproducing the control; one arm
    is not the gate. A truncated arm was never given the chance to reach the
    control's rejection count, so it cannot be checked -- and it is therefore a
    NAMED FAILURE, not a skip: skipping it let `checked == 1` pass on half the
    evidence. Every arm in `PRIMARY_ARMS` must be checked, or the gate fails
    and says which arm fell short and why.

    The gate also requires that the instrument PRODUCED its figures (see
    `REQUIRED_RAW`): reproducing the control proves the solver unchanged, not
    that anything was measured."""
    failures = []
    checked = set()
    for row in rows:
        if row["budget"] != PRIMARY_BUDGET:
            continue
        arm = "B" if row["core_extraction"] else "A"
        if row["truncated"]:
            failures.append(
                f"arm {arm}: truncated at the {ARM_CAP_SECS:.0f} s cap after "
                f"{row.get('nodes')} nodes, so it could not be checked "
                f"against the control; the gate needs both primary arms")
            continue
        checked.add(row["core_extraction"])
        exp = BASELINE[row["core_extraction"]]
        # The instrument must have RUN, and run to the budget. The solver
        # reproducing the control says nothing about this: it reproduces 113
        # and 3 whether or not the index was ever constructed, and a silent
        # instrument would otherwise surface as a 0.0 fraction.
        raw = row.get("raw") or {}
        gaps = instrument_gaps(raw)
        if not raw:
            failures.append(
                f"arm {arm}: the instrument wrote nothing (empty raw block), "
                f"so no figure from this arm is a measurement")
        else:
            for key in gaps:
                failures.append(
                    f"arm {arm}: the instrument never wrote the required "
                    f"counter {key!r}")
        # EXACT, no tolerance. `assign` decrements its node budget at the top
        # of the loop and calls `observe` after the budget test, so a run that
        # ends on `AssignFail('budget', B)` has observed exactly B nodes
        # (budget B admits B iterations and fails on B+1). The smoke run
        # confirms it: starfish at budget 4000 reads nodes == 4000. Anything
        # else means observe was skipped on some nodes or the arm ended
        # elsewhere.
        if "nodes" in raw and raw["nodes"] != row["budget"]:
            failures.append(
                f"arm {arm}: the instrument observed {raw['nodes']} nodes "
                f"but the arm's budget is {row['budget']}")
        site = (row["assign_fail"] or {}).get("site")
        if site != repr(row["budget"]):
            failures.append(
                f"arm {arm}: AssignFail site {site}, control says "
                f"{row['budget']!r} (a layer-budget end is also kind "
                f"'budget' and carries no node site)")
        if row["rejections"] != exp["rejections"]:
            failures.append(
                f"arm {arm}: {row['rejections']} rejections, control says "
                f"{exp['rejections']}")
        kind = (row["assign_fail"] or {}).get("kind")
        if kind != "budget":
            failures.append(
                f"arm {arm}: AssignFail kind {kind!r}, control says 'budget'")
        if "clause_sizes" in exp and row["clause_sizes"] != exp["clause_sizes"]:
            failures.append(
                f"arm {arm}: clause sizes {row['clause_sizes']}, control says "
                f"{exp['clause_sizes']}")
    for core in PRIMARY_ARMS:
        arm = "B" if core else "A"
        if core not in checked and not any(
                row["budget"] == PRIMARY_BUDGET
                and row["core_extraction"] == core for row in rows):
            failures.append(f"arm {arm}: no row at the primary budget, so it "
                            f"could not be checked against the control")
    return {"checked_arms": len(checked),
            "passed": not failures and len(checked) == len(PRIMARY_ARMS),
            "failures": failures}


def _band(dead: float) -> str:
    return next(label for thr, label in BANDS if dead >= thr)


def verdict(rows: list, ident: dict) -> dict:
    """Spec 4. Refuses to name a band unless identity passed. The refusal is
    first, before any figure is read; and a truncated arm never contributes a
    band-deciding figure even then (it cannot while the gate passes, since a
    truncated primary arm fails the gate -- this keeps that true by
    construction rather than by the gate's behaviour).

    BOTH primary arms must have contributed a `dead_node_fraction`, and each is
    banded on its own. The overall band is the maximum, as before, but it is
    never stated unqualified when the arms disagree: a band decided by one arm
    alone is exactly what a clause-scarcity artifact looks like (the 4,000-node
    smoke read arm B at `unit_node_fraction` 0.501 on 3 clauses against arm
    A's 0.0035), so the split is surfaced here, in the artifact, instead of
    being left for the README to walk back. No arm is picked as the winner."""
    if not ident["passed"]:
        return {"band": None,
                "reason": "identity gate failed -- no band may be claimed",
                "identity_failures": ident["failures"]}
    primary = {("B" if r["core_extraction"] else "A"): r for r in rows
               if r["budget"] == PRIMARY_BUDGET and not r["truncated"]}
    names = ["B" if core else "A" for core in PRIMARY_ARMS]
    missing = [a for a in names
               if primary.get(a, {}).get("dead_node_fraction") is None
               or primary.get(a, {}).get("unit_node_fraction") is None]
    if missing:
        return {"band": None,
                "reason": ("no band: primary arm(s) " + ", ".join(missing)
                           + " produced no dead_node_fraction / "
                           "unit_node_fraction; both arms must contribute")}
    deads = {a: primary[a]["dead_node_fraction"] for a in names}
    best = max(deads.values())
    per_arm = {a: {"dead_node_fraction": deads[a], "band": _band(deads[a])}
               for a in names}
    agree = len({v["band"] for v in per_arm.values()}) == 1
    out = {"band_per_arm": per_arm, "arms_agree": agree,
           "dead_node_fraction_max": best,
           "dead_node_fraction_per_arm": deads}
    if agree:
        out["band"] = _band(best)
    else:
        out["band"] = ("ARMS DISAGREE: " + "; ".join(
            f"{a}={per_arm[a]['band']}" for a in names))
        out["band_split"] = {
            "note": ("the two primary arms fall in different bands; the "
                     "maximum-arm band is recorded below for reference and is "
                     "NOT the verdict. Read clauses_total and "
                     "clause_availability per arm before attributing."),
            "band_max_arm": _band(best),
            "per_arm": [{"arm": a,
                         "clauses_total": primary[a].get("clauses_total"),
                         "clause_availability":
                             primary[a].get("clause_availability"),
                         "unit_node_fraction":
                             primary[a].get("unit_node_fraction")}
                        for a in names],
        }
    units = {a: primary[a]["unit_node_fraction"] for a in names}
    guard = all(u < UNIT_GUARD for u in units.values())
    out["attribution_guard_fired"] = guard
    if guard:
        out["attribution"] = {
            "note": ("clauses essentially never go unit in EITHER arm; "
                     "clause_availability and clauses_total decide whether "
                     "the clauses are too wide or too few"),
            "per_arm": [{"core_extraction": primary[a]["core_extraction"],
                         "clauses_total": primary[a].get("clauses_total"),
                         "clause_availability":
                             primary[a].get("clause_availability"),
                         "unit_node_fraction": units[a]}
                        for a in names],
        }
    return out


def main(out_path: str, *, smoke: bool = False) -> int:
    entries = {e["subject"]: e for e in json.load(open(RULE6))}
    art = {
        "measured_utc": datetime.datetime.now(datetime.UTC).isoformat(),
        "commit": _commit(),
        **_dirty(out_path),
        "run_completed": False,
        "loadavg_at_start": os.getloadavg(),
        "config": {
            "primary": PRIMARY,
            "primary_budget": PRIMARY_BUDGET,
            "breadth": list(BREADTH),
            "breadth_budget": BREADTH_BUDGET,
            "arm_cap_secs": ARM_CAP_SECS,
            "vertex_index": True,
            "smoke": smoke,
        },
        "rows": [],
    }

    def flush():
        with open(out_path, "w") as fh:
            json.dump(art, fh, indent=1, sort_keys=True)

    if smoke:
        # Reduced budget, reduced breadth. Proves the runner works; produces
        # NO quotable figure, which is why `config.smoke` is recorded and the
        # identity gate is skipped (its control is the real budget's).
        art["config"]["primary_budget"] = 4_000
        art["config"]["breadth"] = ["starfish"]
        art["config"]["breadth_budget"] = 4_000
        plan = [(PRIMARY, False, 4_000), (PRIMARY, True, 4_000),
                ("starfish", False, 4_000)]
    else:
        plan = [(PRIMARY, core, PRIMARY_BUDGET) for core in PRIMARY_ARMS]
        plan += [(s, False, BREADTH_BUDGET) for s in BREADTH]

    for subject, core, budget in plan:
        print(f"-> {subject} core_extraction={core} budget={budget}", flush=True)
        row = run_arm(entries[subject], core_extraction=core, budget=budget)
        art["rows"].append(row)
        flush()                      # after EVERY arm, so a crash keeps what ran
        print(f"   {row['secs']}s nodes={row.get('nodes')} "
              f"rejections={row['rejections']} "
              f"unit={row.get('unit_node_fraction')} "
              f"dead={row.get('dead_node_fraction')} "
              f"truncated={row['truncated']}", flush=True)

    art["identity"] = ({"checked_arms": 0, "passed": False,
                        "failures": ["smoke run: identity is not gated at a "
                                     "reduced budget"]}
                       if smoke else identity(art["rows"]))
    art["verdict"] = verdict(art["rows"], art["identity"])
    art["run_completed"] = True
    flush()

    print("\nidentity:", art["identity"])
    print("verdict:", art["verdict"])
    return 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--smoke"]
    sys.exit(main(args[0], smoke="--smoke" in sys.argv[1:]))
