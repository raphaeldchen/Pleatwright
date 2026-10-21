"""How small is the ACTUAL cause of a CEGAR rejection?

Spec: `../../specs/2026-09-27-nogood-core-design.md`.

The clause `assign` learns is a median of 109 solver variables and prunes almost
nothing. But every measured contradiction is a `taco_tortilla` among exactly
THREE faces, while the recorded cause is a median of 172 FOLD edges, because
`witness.creases` comes from `layer_order`'s `exc.deps` -- the whole derivation
chain, a dependency CONE rather than a CUT. This script measures the gap.

THE ORACLE. `layers.propagate(graph, labels, only=S)` contradicts iff the creases
in S, at this candidate's own labels, are ALONE sufficient. Monotone in S:
seeding more slots only adds constraints, and a contradictory system stays
contradictory under added constraints. Monotonicity is QuickXplain's
precondition, so it is VERIFIED on every rejection (`_checks`), not trusted.

SOUNDNESS. Every candidate core is tested, so a too-small core cannot be
produced. That matters more than size: a clause that is too small forbids
assignments that are not contradictory, prunes valid labellings, and can make the
search report unsat when a solution exists.

SAMPLING is breadth AND depth, because `lizard` misleads in both directions: its
`propagate` costs 1.07s against 0.004-0.014s on the other five subjects, so a
lizard-only cost figure overstates extraction ~100x -- yet lizard is the only
subject whose CEGAR loop yields many rejections cheaply.
  * breadth: one rejection on each labelling-capable subject, from
    `assign(global_check=None)` (no CEGAR loop needed).
  * depth: `DEPTH` rejections on lizard.

Run from mcp_harness:
  PYTHONPATH=. ../.venv/bin/python3 -u \\
      ../docs/superpowers/evidence/2026-09-27-nogood-core/core_measure.py \\
      ../docs/superpowers/evidence/2026-09-27-nogood-core/core-sizes.json [depth]
"""
import collections
import difflib
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

OUT = sys.argv[1]
DEPTH = int(sys.argv[2]) if len(sys.argv) > 2 else 25
RULE6 = os.path.join("..", "docs", "superpowers", "evidence",
                     "2026-09-08-vlm-tree-authoring", "data", "rule6_serve.json")
BREADTH = ["starfish", "lizard", "frog", "horse", "bird", "guinea_pig"]
ASSIGN_SRC = pathlib.Path("box_pleat/assign.py")

_ORIG = """    nodes = budget
    frames: list = []          # [variable, value order, next value index]
"""
_PATCHED = """    _PROBE["var_of"] = dict(var_of)
    _PROBE["idx"] = dict(idx)
    nodes = budget
    frames: list = []          # [variable, value order, next value index]
"""
_FOOTER = "\n\n_PROBE = {}\n"


def build_instrumented():
    """Patch `assign.py` in memory to expose `var_of` and `idx`; verify; import.

    `var_of` and `idx` are locals inside `assign`, and the clause's VARIABLE
    count -- the headline of this measurement -- cannot be computed without them.
    Patched in memory rather than forked: a committed copy would drift silently.
    Loaded under a dotted name so `assign.py`'s relative imports resolve, and
    appended rather than prepended because `assign.py` opens with
    `from __future__ import annotations`.
    """
    src = ASSIGN_SRC.read_text()
    if src.count(_ORIG) != 1:
        raise SystemExit("REFUSING TO MEASURE: assign.py's DFS setup no longer "
                         "matches this script's anchor text exactly once. "
                         "Re-derive the patch against today's source.")
    patched = src.replace(_ORIG, _PATCHED) + _FOOTER
    removed = [l[1:] for l in difflib.unified_diff(
        src.splitlines(), patched.splitlines(), lineterm="", n=0)
        if l.startswith("-") and not l.startswith("---")]
    if removed:
        raise SystemExit(f"REFUSING TO MEASURE: patch removed lines: {removed}")
    out = pathlib.Path(os.environ.get("TMPDIR", "/tmp")) / "_assign_core.py"
    out.write_text(patched)
    import box_pleat  # noqa: F401 - must be in sys.modules for relative imports
    name = "box_pleat._assign_core"
    spec = importlib.util.spec_from_file_location(name, out)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------
# QuickXplain (Junker, AAAI 2004; formal treatment arXiv:2001.01835)
# --------------------------------------------------------------------------
def quickxplain(candidates, holds, counter):
    """An IRREDUCIBLE subset of `candidates` for which `holds` is still true.

    `holds(frozenset)` must be MONOTONE: true for a set implies true for every
    superset. `counter` is a one-element list incremented per oracle call.

    Irreducible, not globally minimum: a smallest core is NP-hard and is not
    attempted, matching the greedy-vs-minimum ruling already taken for
    `interleave`'s odd-cycle release.

    Candidates are consumed in the DETERMINISTIC order given. QuickXplain's
    result depends on how it splits, so an unordered input would return a
    different irreducible core run to run and make every reported figure
    unreproducible. Which core is found is not canonical; finding the same one
    again must be.
    """
    def oracle(s):
        counter[0] += 1
        return holds(s)

    def qx(background, cand):
        if oracle(background):
            return frozenset()
        if len(cand) == 1:
            return frozenset(cand)
        k = len(cand) // 2
        c1, c2 = cand[:k], cand[k:]
        d1 = qx(background | set(c1), c2)
        d2 = qx(background | d1, c1)
        return d1 | d2

    return qx(frozenset(), list(candidates))


def _self_test():
    """Refuse to measure unless QuickXplain is demonstrably correct here.

    The algorithm is the measurement, so a wrong implementation would not fail
    loudly -- it would return plausible small cores. Two properties: it finds
    the exact cause on a synthetic monotone oracle, and it reports the oracle
    calls it actually made.
    """
    cause = {2, 4}
    calls = [0]
    got = quickxplain(sorted([1, 2, 3, 4, 5, 6, 7, 8]),
                      lambda s: cause <= set(s), calls)
    if got != frozenset(cause):
        raise SystemExit(f"REFUSING TO MEASURE: quickxplain self-test returned "
                         f"{sorted(got)}, expected {sorted(cause)}")
    if calls[0] < 3:
        raise SystemExit(f"REFUSING TO MEASURE: quickxplain self-test made only "
                         f"{calls[0]} oracle calls -- it cannot have searched")
    print(f"quickxplain self-test OK ({calls[0]} oracle calls for a "
          f"2-of-8 cause)", flush=True)


def _checks(graph, labels, blamed, core):
    """Spec §4.2's monotonicity checks, on this rejection. All three must hold.

    Returned as a dict so a FAILURE is recorded in the artifact rather than
    crashing the run -- a violated check invalidates that row, not the corpus.
    """
    full = L.propagate(graph, labels, only=blamed) is not None
    empty = L.propagate(graph, labels, only=frozenset()) is not None
    if core:
        extra = next((c for c in sorted(blamed) if c not in core), None)
        superset = (L.propagate(graph, labels,
                                only=core | {extra}) is not None
                    if extra is not None else True)
    else:
        superset = None
    return {"full_blamed_contradicts": full,
            "empty_contradicts": empty,
            "core_plus_one_contradicts": superset,
            "all_ok": bool(full) and not empty and superset is not False}


def measure_rejection(row, graph, labels, blamed, fold, var_of, idx):
    """Extract a core for one rejection and fill `row`."""
    slot_edges = frozenset(s.edge for s in graph.slots)
    # Spec §4.1: every blamed crease must be a slot edge. A crease silently
    # dropped here would make the core look smaller than it is.
    row["blamed_not_slots"] = len(blamed - slot_edges)
    t0 = time.time()
    calls = [0]
    core = quickxplain(
        sorted(blamed),
        lambda s: L.propagate(graph, labels, only=frozenset(s)) is not None,
        calls)
    row["extract_secs"] = round(time.time() - t0, 2)
    row["oracle_calls"] = calls[0]
    row["blamed_creases"] = len(blamed)
    row["core_creases"] = len(core)

    # variable-level sizes, using assign's OWN clause expression so the two
    # cannot disagree about what a clause's variable set is
    def variables(creases):
        keys = L.piece_keys(
            L.Witness(kind="probe", creases=frozenset(creases),
                      faces=(), prov="probe"), fold)
        return {var_of[idx[k]] for k in keys if k in idx and idx[k] in var_of}

    row["blamed_variables"] = len(variables(blamed))
    row["core_variables"] = len(variables(core))
    row["checks"] = _checks(graph, labels, blamed, core)
    return core


def main():
    _self_test()
    entries = {e["subject"]: e for e in json.load(open(RULE6))}
    A = build_instrumented()
    rows = []

    def flush():
        json.dump(rows, open(OUT, "w"), indent=1)

    # ---- BREADTH: one rejection per subject --------------------------------
    for s in BREADTH:
        row = {"subject": s, "sample": "breadth"}
        res = compile_tree(entries[s]["requested"], entries[s]["pairs"])
        if res.stage_reached != "emit":
            row["error"] = f"sparse compile stopped@{res.stage_reached}"
            rows.append(row); flush(); print(f"{s}: SPARSE STOP", flush=True)
            continue
        A._PROBE.clear()
        asg = A.assign(res.layout, res.ridges, res.boundary_ridges,
                       res.contours, dense=True, global_check=None)
        if isinstance(asg, A.AssignFail):
            row["error"] = f"dense assign failed: {asg!r}"
            rows.append(row); flush(); print(f"{s}: DENSE FAIL", flush=True)
            continue
        var_of, idx = A._PROBE["var_of"], A._PROBE["idx"]
        fold = emit.to_fold(res.layout, asg)
        ff = flat_fold.flat_fold(fold)
        graph = L.constraint_graph(ff)
        labels = {k: a for _, _, k, a in ff.shared_edges if a in ("M", "V")}
        w = L.propagate(graph, labels)
        if w is None:
            row["note"] = "first dense candidate did not contradict"
            rows.append(row); flush(); print(f"{s}: NO CONTRADICTION", flush=True)
            continue
        row["witness_kind"] = w.kind
        row["witness_faces"] = len(w.faces)
        measure_rejection(row, graph, labels, w.creases, fold, var_of, idx)
        rows.append(row); flush()
        print(f"{s:11} blamed {row['blamed_creases']:4}cr/"
              f"{row['blamed_variables']:4}var -> CORE "
              f"{row['core_creases']:3}cr/{row['core_variables']:3}var "
              f"({row['oracle_calls']} calls, {row['extract_secs']}s) "
              f"checks_ok={row['checks']['all_ok']}", flush=True)

    # ---- DEPTH: many rejections on lizard ---------------------------------
    res = compile_tree(entries["lizard"]["requested"], entries["lizard"]["pairs"])
    cell = {}
    topo_cell = []
    seen = [0]

    class Stop(Exception):
        pass

    def spy(cand):
        """Controller amendment 1: same cache-plus-topology-drift guard as
        `compile._check` (mcp_harness/box_pleat/compile.py, ~lines 262-307,
        docstring 'The topology-drift guard'). The cached `cell["graph"]` is
        indexed by candidate 1's FOLD vertex ids (`DirectSlot.edge`,
        `Prov.creases`, `Witness.creases`), which are only meaningful for a
        fold sharing candidate 1's own `vertices_coords`/`edges_vertices`. In
        DENSE mode an F<->creased flip on a centre-column piece between
        candidates adds or removes an edge and shifts vertex ids, so without
        this guard a later candidate would either raise a bare `KeyError` out
        of `labels[s.edge]` inside `layers.propagate`, or silently resolve to
        different vertices and hand back a verdict -- and therefore a
        core -- for a pattern that was never actually checked, corrupting
        every depth row after the drift with no failure to flag it.
        """
        if seen[0] >= DEPTH:
            raise Stop()
        fold = emit.to_fold(res.layout, cand)
        ff = flat_fold.flat_fold(fold)
        topo = (fold["vertices_coords"], fold["edges_vertices"])
        if "graph" not in cell:
            cell["graph"] = L.constraint_graph(ff)
            topo_cell.append(topo)
        else:
            assert topo == topo_cell[0], (
                "core_measure.spy: this candidate's fold topology drifted "
                "from candidate 1's -- the cached constraint_graph is indexed "
                "by candidate 1's FOLD vertex ids and is invalid for a "
                "candidate whose F set (and therefore crease set) moved; same "
                "guard as compile._check's 'topology-drift guard' "
                "(mcp_harness/box_pleat/compile.py, ~lines 262-307)")
        labels = {k: a for _, _, k, a in ff.shared_edges if a in ("M", "V")}
        w = L.propagate(cell["graph"], labels)
        if w is None:
            return None
        seen[0] += 1
        row = {"subject": "lizard", "sample": "depth",
               "witness_kind": w.kind, "witness_faces": len(w.faces)}
        measure_rejection(row, cell["graph"], labels, w.creases, fold,
                          A._PROBE["var_of"], A._PROBE["idx"])
        rows.append(row); flush()
        print(f"  lizard#{seen[0]:<3} blamed {row['blamed_creases']:4}cr/"
              f"{row['blamed_variables']:4}var -> CORE "
              f"{row['core_creases']:3}cr/{row['core_variables']:3}var "
              f"({row['oracle_calls']} calls, {row['extract_secs']}s) "
              f"checks_ok={row['checks']['all_ok']}", flush=True)
        return L.piece_keys(w, fold), w

    A._PROBE.clear()
    try:
        A.assign(res.layout, res.ridges, res.boundary_ridges, res.contours,
                 dense=True, global_check=spy, layer_checks=100000,
                 budget=5_000_000)
    except Stop:
        pass

    # ---- refuse to report a vacuous run ----------------------------------
    good = [r for r in rows if "core_variables" in r]
    if not good:
        flush()
        raise SystemExit("VACUOUS RUN: no rejection produced a core. Reporting "
                         "cores of size 0 here would look like success.")
    bad = [r for r in good if not r["checks"]["all_ok"]]
    cv = [r["core_variables"] for r in good]
    bv = [r["blamed_variables"] for r in good]
    print()
    print(f"rejections measured: {len(good)}  monotonicity FAILURES: {len(bad)}")
    print(f"blamed variables : median {statistics.median(bv)}  max {max(bv)}")
    print(f"CORE   variables : median {statistics.median(cv)}  max {max(cv)}")
    print(f"tightening ratio : {statistics.median(bv) / max(statistics.median(cv), 1):.1f}x")
    flush()


main()
