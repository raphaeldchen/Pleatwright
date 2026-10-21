"""Does the incremental vertex index preserve the search, and what does it buy?

Spec: `../../specs/2026-09-29-vertex-index-design.md`.

IDENTITY FIRST, ALWAYS (spec section 4.4). A correct index selects the same
vertex, so a speedup measured on an arm that failed identity is not a result
-- the two arms solved different problems. Every subject therefore gets an
IDENTITY pass before a TIMING pass, and `verdict()` refuses to report a
speedup for any subject whose identity failed.

TWO PASSES, NOT ONE. The identity pass appends one entry per node to
`debug_search["vars"]` and records the pool figures; you cannot time an
instrumented arm, so the timing pass runs with every debug channel off.

A CEILING IS NOT A SPEEDUP. `CEILINGS` below are the predecessor's Amdahl
bounds for removing a component ENTIRELY, which no real optimisation
achieves. They are printed beside every realised figure so the gap is
visible, and Task 4's README is required to name it.

NO FIGURE FROM A REDUCED BUDGET MAY BE EXTRAPOLATED. The speedup GROWS
with the node budget: measured on dense `lizard`, 1.45x at 4,000 nodes
against 2.43x at 20,000. The reason is structural -- deeper in the search
more variables are bound, so more vertices are empty and the index skips more
of them, which means the saving compounds with depth rather than holding a
constant ratio. So `BUDGET` below is NOT a knob to trim when a run is slow: a
smaller budget produces a different and systematically PESSIMISTIC figure,
and Task 4's README may quote only figures taken at the real `BUDGET`.

NOT A CONVERGENCE FIX. The ceiling caps this at 3.492x on `lizard`. Dense
still will not converge. The goal is dense measurable on MORE SUBJECTS.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[4] / "mcp_harness"))

from box_pleat.compile import compile_tree            # noqa: E402

#: The same eight subjects and the same fixture the predecessor's ladder used,
#: so the off arm's dense numbers are comparable with
#: `../2026-09-29-local-csp-profile/profile.json`.
SUBJECTS = ("starfish", "lizard", "frog", "horse", "bird", "guinea_pig",
            "octopus", "dog")

#: The predecessor's node budget, unchanged, so per-node figures compare.
BUDGET = 20_000

#: From `../2026-09-29-local-csp-profile/profile.json`, `lizard`'s row:
#: `whole_run_ceiling["free_vars_at"]` and the pair
#: (free_vars_at + pick) recomputed as 1/(1 - (pick+free_vars_at)/total).
#: Quoted as that directory's figures, never recomputed here.
CEILINGS = {"free_vars_at_alone": 1.907, "pick_and_free_vars_at": 3.492}

RULE6 = (pathlib.Path(__file__).resolve().parents[4] / "docs" / "superpowers"
         / "evidence" / "2026-09-08-vlm-tree-authoring" / "data"
         / "rule6_serve.json")


def _commit() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                          text=True, check=True).stdout.strip()


def digest(vars_seq) -> str:
    """A stable digest of the chosen-variable sequence (spec section 4.3).

    The sequence is what makes identity meaningful: node counts alone would
    pass two searches that diverged and then reconverged to the same total,
    while this differs as soon as one choice differs. Length is folded in so
    a prefix cannot collide with its own extension.
    """
    h = hashlib.sha256()
    h.update(str(len(vars_seq)).encode())
    for v in vars_seq:
        h.update(b"|")
        h.update(str(v).encode())
    return h.hexdigest()[:16]


def speedup(off_secs, on_secs):
    """`off / on`, or None when either arm has no usable time.

    Refuses rather than dividing by zero, and refuses a negative or zero
    duration, which would mean the clock was misread rather than that the
    code was infinitely fast.
    """
    if not off_secs or not on_secs or off_secs <= 0 or on_secs <= 0:
        return None
    return round(off_secs / on_secs, 3)


def first_divergence(a, b):
    """The index of the first differing element, or None if equal.

    Reported because WHERE two searches diverge localises the defect: an
    early index points at the selection key or the tie-break, a late one at
    a missing `unbind`.
    """
    if a == b:
        return None
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i
    return min(len(a), len(b))


def visited(pool_total, pool_calls, nodes, interior):
    """Vertices the index actually looked at: per SELECT CALL and per NODE.

    THESE ARE TWO DIFFERENT QUANTITIES and confusing them is a ~5% error in
    the headline figure. `select` does not run at every node: `pick`'s sticky
    fast path returns before it whenever the previously chosen vertex still
    has an eligible variable. So `pool_total / pool_calls` is vertices per
    `select` CALL, while `pool_total / nodes` is vertices per NODE -- and only
    the per-node one is comparable with `interior`, which is per node by
    construction, because the off arm's loop visits every interior vertex at
    every node. Measured on dense `lizard` at 4,000 nodes: `pool_total`
    942,563, `pool_calls` 3,794, `nodes` 4,000, so 248.4 per select against
    235.6 per node, with `select` skipped on 5.15% of nodes. Against
    `interior` = 4,489 that is a fraction of 0.0525 the right way and 0.0553
    the wrong way. Every comparison and every fraction below therefore uses
    the PER-NODE figure; the per-select one is recorded because it is the
    figure `select`'s own cost attaches to, under a name that says so.

    Both lag by at most one `select` call: `assign` records `pool_calls` and
    `pool_total` at the TOP of its loop, before that node's `pick` has run
    (stated at the recording site). Immaterial at 20,000 nodes, and
    immaterial to the distinction above, which is about 5% not 0.005%.

    Every field is `None` rather than 0 when its input is missing, so a
    dropped debug channel reads as absent instead of as a measurement.
    """
    keys = ("visited_per_select_on", "visited_per_node_on",
            "visited_fraction_on", "select_calls_per_node_on")
    if pool_total is None:
        return dict.fromkeys(keys)
    per_select = round(pool_total / pool_calls, 1) if pool_calls else None
    per_node = round(pool_total / nodes, 1) if nodes else None
    return {
        "visited_per_select_on": per_select,
        "visited_per_node_on": per_node,
        "visited_fraction_on": (round(per_node / interior, 4)
                                if per_node and interior else None),
        "select_calls_per_node_on": (round(pool_calls / nodes, 4)
                                     if pool_calls is not None and nodes
                                     else None),
    }


def identity_verdict(row):
    """(passed, [failure, ...]) for one subject. Spec section 4.

    Every check is stated as a positive requirement so a missing field fails
    rather than passing vacuously -- a `row.get(...)` that returns None must
    not read as agreement.
    """
    bad = []
    if row.get("sparse_fold_equal") is not True:
        bad.append(f"sparse FOLD not byte-identical "
                   f"(off stage {row.get('sparse_stage_off')!r}, "
                   f"on stage {row.get('sparse_stage_on')!r})")
    if row.get("dense_nodes_off") is None or row.get("dense_nodes_on") is None:
        bad.append("a dense arm recorded no node count")
    elif row["dense_nodes_off"] != row["dense_nodes_on"]:
        bad.append(f"dense node counts differ: {row['dense_nodes_off']} "
                   f"vs {row['dense_nodes_on']}")
    elif row["dense_nodes_off"] == 0:
        bad.append("dense ran zero nodes, so identity is vacuous")
    if row.get("dense_digest_off") is None or row.get("dense_digest_on") is None:
        bad.append("a dense arm recorded no variable-sequence digest")
    elif row["dense_digest_off"] != row["dense_digest_on"]:
        bad.append(f"chosen-variable sequences differ, first at index "
                   f"{row.get('dense_first_divergence')}")
    return not bad, bad


def _sparse_pair(entry):
    off = compile_tree(entry["requested"], entry["pairs"])
    on = compile_tree(entry["requested"], entry["pairs"], vertex_index=True)
    return off, on


def identity_pass(entry) -> dict:
    """Both arms, sparse and dense, with `debug_search` on. Never timed."""
    row: dict = {}
    off, on = _sparse_pair(entry)
    row["sparse_stage_off"] = off.stage_reached
    row["sparse_stage_on"] = on.stage_reached
    row["sparse_fold_equal"] = (off.fold == on.fold)
    row["sparse_layers_tried_off"] = off.layers_tried
    row["sparse_layers_tried_on"] = on.layers_tried

    a: dict = {}
    b: dict = {}
    d_off = compile_tree(entry["requested"], entry["pairs"], dense=True,
                         assign_budget=BUDGET, debug_search=a)
    d_on = compile_tree(entry["requested"], entry["pairs"], dense=True,
                        assign_budget=BUDGET, vertex_index=True, debug_search=b)
    row["dense_stage_off"] = d_off.stage_reached
    row["dense_stage_on"] = d_on.stage_reached
    row["dense_nodes_off"] = a.get("nodes")
    row["dense_nodes_on"] = b.get("nodes")
    row["dense_digest_off"] = digest(a.get("vars", []))
    row["dense_digest_on"] = digest(b.get("vars", []))
    row["dense_first_divergence"] = first_divergence(a.get("vars", []),
                                                     b.get("vars", []))
    # Spec 5.2: visited vertices per node. The off arm's figure is `interior`
    # BY CONSTRUCTION -- its loop visits everything -- so the comparison's
    # content is entirely in the on arm. `visited()` records the per-node and
    # the per-select figure under separate names and explains why they differ;
    # `visited_per_node_on` is the only one that may be compared against
    # `visited_per_node_off` or turned into a fraction.
    row["interior"] = b.get("interior")
    row["visited_per_node_off"] = b.get("interior")
    row["select_calls_on"] = b.get("pool_calls")
    row.update(visited(b.get("pool_total"), b.get("pool_calls"),
                       b.get("nodes"), b.get("interior")))
    return row


def timing_pass(entry) -> dict:
    """Both arms, dense only, every debug channel OFF. This is the only pass
    whose seconds mean anything.

    TWO CLOCKS, both recorded. The wall clock spans the whole `compile_tree`
    -- tree, pack, skeleton, contours, assign, layers, emit -- while
    `Result.timings["assign"]` is the `assign` stage alone, written by
    `compile.py`'s `tick("assign")` on both the success and the failure path.
    `assign` is the unit the predecessor's ceilings attach to, so it is the
    honest denominator for any speedup quoted against them (spec 5.2). On
    dense `lizard` the two nearly coincide -- `assign` 16.67 s of a 16.72 s
    compile -- but "nearly" is a measurement, not a property, and it will not
    hold for a subject whose packing or emit dominates. Record both rather
    than assume.
    """
    out: dict = {}
    for label, kw in (("off", {}), ("on", {"vertex_index": True})):
        t = time.perf_counter()
        res = compile_tree(entry["requested"], entry["pairs"], dense=True,
                           assign_budget=BUDGET, **kw)
        out[f"dense_secs_{label}"] = round(time.perf_counter() - t, 2)
        out[f"dense_assign_secs_{label}"] = res.timings.get("assign")
    out["speedup"] = speedup(out["dense_secs_off"], out["dense_secs_on"])
    out["assign_speedup"] = speedup(out["dense_assign_secs_off"],
                                    out["dense_assign_secs_on"])
    for label, kw in (("off", {}), ("on", {"vertex_index": True})):
        t = time.perf_counter()
        res = compile_tree(entry["requested"], entry["pairs"], **kw)
        out[f"sparse_secs_{label}"] = round(time.perf_counter() - t, 2)
        out[f"sparse_assign_secs_{label}"] = res.timings.get("assign")
    out["sparse_speedup"] = speedup(out["sparse_secs_off"],
                                    out["sparse_secs_on"])
    out["sparse_assign_speedup"] = speedup(out["sparse_assign_secs_off"],
                                           out["sparse_assign_secs_on"])
    return out


def _selftest():
    assert digest([]) != digest([1]), "empty and one-element digests collide"
    assert digest([1, 2]) == digest([1, 2])
    assert digest([1, 2]) != digest([2, 1]), "digest ignores order"
    assert digest([1, 2]) != digest([1, 2, 3]), "a prefix collides"
    # SAME LENGTH, so the length prefix cannot do the work: without the
    # separator both hash "2" + "1" + "23" and "2" + "12" + "3" == "2123".
    # An earlier version of this assertion used `[12]` vs `[1, 2]`, which
    # passes with the separator REMOVED because the length prefix already
    # differs -- a check that could not fail, verified by mutation.
    assert digest([1, 23]) != digest([12, 3]), "separator missing"

    assert speedup(10.0, 5.0) == 2.0
    assert speedup(10.0, 0) is None
    assert speedup(0, 5.0) is None
    assert speedup(-1.0, 5.0) is None
    assert speedup(None, 5.0) is None

    assert first_divergence([1, 2, 3], [1, 2, 3]) is None
    assert first_divergence([1, 2, 3], [1, 9, 3]) == 1
    assert first_divergence([1, 2], [1, 2, 3]) == 2, "prefix not reported"

    ok_row = {"sparse_fold_equal": True, "dense_nodes_off": 20001,
              "dense_nodes_on": 20001, "dense_digest_off": "a",
              "dense_digest_on": "a"}
    ok, bad = identity_verdict(ok_row)
    assert ok and not bad, bad
    ok, bad = identity_verdict({**ok_row, "sparse_fold_equal": False})
    assert not ok and "byte-identical" in bad[0], bad
    ok, bad = identity_verdict({**ok_row, "dense_nodes_on": 19000})
    assert not ok and "node counts differ" in bad[0], bad
    ok, bad = identity_verdict({**ok_row, "dense_digest_on": "b"})
    assert not ok and "sequences differ" in bad[0], bad
    # a zero-node run must FAIL rather than pass vacuously
    ok, bad = identity_verdict({**ok_row, "dense_nodes_off": 0,
                                "dense_nodes_on": 0})
    assert not ok and "vacuous" in bad[0], bad
    # a MISSING field must fail, not read as agreement
    ok, bad = identity_verdict({"dense_nodes_off": 1, "dense_nodes_on": 1,
                                "dense_digest_off": "a", "dense_digest_on": "a"})
    assert not ok, "a missing sparse_fold_equal passed"
    ok, bad = identity_verdict({**ok_row, "dense_digest_on": None})
    assert not ok and "no variable-sequence digest" in bad[0], bad

    # THE PER-NODE / PER-SELECT CONFUSION (review FIX E). `select` is skipped
    # on every node `pick`'s sticky path answers, so `pool_calls != nodes` and
    # the two figures genuinely differ. These are the MEASURED dense `lizard`
    # readings at 4,000 nodes. An earlier `ab.py` computed
    # `pool_total / pool_calls` and stored it as `visited_per_node_on`, then
    # compared it against `interior`, which is per node -- so it read 248.4
    # and a fraction of 0.0553 where the honest per-node figures are 235.6 and
    # 0.0525. Under that formula the first two assertions below fail.
    v = visited(pool_total=942_563, pool_calls=3_794, nodes=4_000,
                interior=4_489)
    assert v["visited_per_select_on"] == 248.4, v
    assert v["visited_per_node_on"] == 235.6, v
    assert v["visited_per_node_on"] != v["visited_per_select_on"], \
        ("the two figures collapsed -- this case no longer distinguishes "
         "per-node from per-select, so it cannot catch the confusion")
    assert v["select_calls_per_node_on"] == 0.9485, v
    # the fraction must be built from the PER-NODE figure, not the other one
    assert v["visited_fraction_on"] == round(235.6 / 4_489, 4), v
    assert v["visited_fraction_on"] != round(248.4 / 4_489, 4), \
        "the fraction was built from the per-select figure"
    # a missing channel reads as None everywhere, never as 0
    assert all(x is None for x in visited(None, None, None, None).values())
    assert visited(100, 0, 0, 10)["visited_per_node_on"] is None
    assert visited(100, 0, 5, 10)["visited_per_select_on"] is None

    print("selftest OK: digest (5), speedup (5), first_divergence (3), "
          "identity_verdict (7 incl. vacuous-zero and two missing fields), "
          "visited (9 incl. the per-node/per-select confusion case)")


def main(out_path):
    entries = {e["subject"]: e for e in json.load(open(RULE6))}
    rec = {
        "measured_utc": datetime.datetime.now(datetime.UTC).isoformat(
            timespec="seconds"),
        "commit": _commit(),
        "budget": BUDGET,
        "ceilings": CEILINGS,
        "note": ("Identity is established BEFORE any speedup is quoted "
                 "(spec 4.4). The identity and timing passes are separate "
                 "runs because the identity pass instruments the search."),
        "rows": [],
    }

    def flush():
        with open(out_path, "w") as fh:
            json.dump(rec, fh, indent=1)

    flush()
    for s in SUBJECTS:
        row = {"subject": s}
        try:
            row.update(identity_pass(entries[s]))
            ok, bad = identity_verdict(row)
            row["identity_passed"] = ok
            row["identity_failures"] = bad
            if ok:
                row.update(timing_pass(entries[s]))
            else:
                row["timing_skipped"] = (
                    "identity failed, so a speedup would be meaningless "
                    "(spec 4.4)")
        except Exception as exc:                       # noqa: BLE001
            # Per-subject, so one engine failure does not lose the corpus.
            # `VertexIndexError` lands here too and is recorded as an
            # identity failure, which is what it is.
            row["outcome"] = f"{type(exc).__name__}: {exc}"[:400]
            row["identity_passed"] = False
        rec["rows"].append(row)
        flush()
        if not row.get("identity_passed"):
            print(f"{s}: IDENTITY FAILED -- "
                  f"{row.get('identity_failures') or row.get('outcome')}",
                  flush=True)
            continue
        print(f"{s}: identity OK | dense {row['dense_secs_off']}s -> "
              f"{row['dense_secs_on']}s ({row['speedup']}x); assign "
              f"{row['dense_assign_secs_off']}s -> "
              f"{row['dense_assign_secs_on']}s ({row['assign_speedup']}x) "
              f"| sparse {row['sparse_secs_off']}s -> "
              f"{row['sparse_secs_on']}s ({row['sparse_speedup']}x) "
              f"| visited/NODE {row['visited_per_node_off']} -> "
              f"{row['visited_per_node_on']} "
              f"({row['visited_fraction_on']}); per select "
              f"{row['visited_per_select_on']} on "
              f"{row['select_calls_per_node_on']} select/node", flush=True)

    passed = [r for r in rec["rows"] if r.get("identity_passed")]
    rec["identity_passed_count"] = len(passed)
    rec["corpus_size"] = len(SUBJECTS)
    flush()
    print()
    print(f"identity: {len(passed)} of {len(SUBJECTS)} subjects")
    print(f"ceilings (that directory's figures, for removing a component "
          f"ENTIRELY): {CEILINGS}")
    print("A ceiling is NOT a speedup. Task 4 must print the realised "
          "figure beside it and name the gap.")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    elif len(sys.argv) < 2:
        print("usage: ab.py <out.json> | ab.py --selftest", file=sys.stderr)
        raise SystemExit(1)
    else:
        main(sys.argv[1])
