"""Measure the dense LABELLING stage on all 8 subjects (Task 8 Step 1).

The dense labelling stage -- COrigami F.2's pleat grouping, adjacency and
2-colouring (`box_pleat.interleave`), then `assign(dense=True)`'s own
mirror-merge reconciliation -- is the half of this plan that WORKS: it is a
one-shot local CSP with no outer CEGAR loop, so its cost does not depend on
how the outer layer-order repair loop behaves. That does NOT mean it is
uniformly fast: measured across the corpus (see `README.md` §3's "Cost does
not generalise from the cheap subjects"), it ranges from 5 ms (`starfish`) to
201.0 s (`bird`), and does not finish at all within a 300 s cap on
`octopus`/`dog`. (Those two bounds are `dense_assign_secs` 0.005 and 200.974
in the committed `dense_labelling.json`. This docstring previously said
"4 ms" and "177.6 s", which were this script's OWN output from an earlier run
that the 2026-09-26 re-run overwrote -- corrected 2026-09-27.)

This script measures it in isolation from the repair loop
by calling
`assign(..., dense=True, global_check=None)` directly: `global_check=None`
means the search returns the FIRST locally-feasible candidate and the
no-good machinery never runs (see `assign()`'s own docstring). This is
NOT the same call `compile_tree(dense=True)` makes internally (which passes
`global_check=_check`, the layer-order filter, and is what Step 2 measures
the cost of); it isolates the labelling stage's own cost and shape.

For each subject:
  1. Compile SPARSELY (`compile_tree` with no `dense` argument) to get the
     layout, ridges, boundary ridges and contours -- geometry that does not
     depend on the labelling mode -- plus the sparse Assignment for the
     sparse M/V count and sparse crease-degree histogram.
  2. Recompute the RAW dense pleat-path grouping (`assign.faces` ->
     `assign.profiles` -> `assign.initial_readings(dense=True)` ->
     `assign.pleat_paths(dense=True)` -> `interleave.colour`) exactly as
     `assign()` does internally, to read the PRE-MERGE path count and F.2's
     raw colour/release split before `assign()`'s own mirror-merge
     reconciliation changes those numbers (see `assign.py`'s Task 6 review
     comments on why post-merge counts differ from pre-merge ones -- a
     mirrored pair of dense pleat groups shares one final solver variable,
     so post-merge counts are routinely about half the raw ones).
  3. Call `assign(dense=True, global_check=None)` for the POST-merge counts
     (`pleat_vars`, `released_vars`, `conflict_vars`, `flipped_from_f2`),
     the dense M/V count, and the dense crease-degree histogram.

Written incrementally: `ROWS` is dumped to `OUT` after every subject, so a
run that stops partway leaves every completed subject's row intact.

Run from mcp_harness:
  PYTHONPATH=. ../.venv/bin/python3 -u \
      ../docs/superpowers/evidence/2026-09-24-dense-pleats/dense_labelling.py \
      ../docs/superpowers/evidence/2026-09-24-dense-pleats/dense_labelling.json

RESUMABLE: if `OUT` already exists, subjects already present in it (with no
`dense_timeout` marker) are skipped, so a run that was interrupted -- or a
subject whose dense assign was killed for exceeding `DENSE_ASSIGN_CAP_SECS`
-- can be continued without redoing the subjects that already succeeded.

`DENSE_ASSIGN_CAP_SECS` (default 300s) bounds the `assign(dense=True,
global_check=None)` call itself via `signal.alarm` -- measured necessary
2026-09-25: `bird` legitimately took 200.974s in the committed artifact
(177.6s when this note was first written; corrected 2026-09-27 against
`dense_labelling.json`, which leaves only 99 s of headroom under the 300 s cap
and so makes the cap's necessity a closer call, not a looser one -- this
module's own docstring above states the true range rather than assuming it is
uniformly cheap), and
`octopus` did not return within 72 minutes of wall clock / CPU time and was
killed by hand. A subject that times out gets a row with `"dense_timeout":
true` and no post-merge fields, rather than blocking every subject after it --
record the anomaly, do not let it silently swallow the rest of the corpus.
"""
import json
import os
import signal
import sys
import time
from collections import Counter, defaultdict

import cp_audit
import flat_fold
import layer_certify

from box_pleat import assign as A
from box_pleat import emit
from box_pleat import interleave
from box_pleat import layers as L
from box_pleat.compile import compile_tree

OUT = sys.argv[1]
DENSE_ASSIGN_CAP_SECS = int(sys.argv[2]) if len(sys.argv) > 2 else 300
#: Each DOWNSTREAM stage (to_fold / flat_fold / constraint_graph / propagate /
#: certify / audit) gets its own independent wall-clock cap. Separate from
#: DENSE_ASSIGN_CAP_SECS because these stages grow in FACE PAIRS, not in the
#: CSP's variable count: sparse `dog` already reads 298 faces -> 30,697 pairs
#: -> 537 s to certify, and a dense subject's face count is an order of
#: magnitude larger. A stage that exceeds its cap is recorded by NAME with the
#: cap that stopped it, so a blow-up costs that one stage rather than the run.
STAGE_CAP_SECS = int(sys.argv[3]) if len(sys.argv) > 3 else 900
RULE6 = os.path.join("..", "docs", "superpowers", "evidence",
                     "2026-09-08-vlm-tree-authoring", "data", "rule6_serve.json")
ORDER = ["starfish", "bird", "lizard", "horse", "octopus", "frog",
         "guinea_pig", "dog"]


class _DenseAssignTimeout(Exception):
    pass


def _alarm(signum, frame):
    raise _DenseAssignTimeout()


class _StageTimeout(Exception):
    pass


def _stage_alarm(signum, frame):
    raise _StageTimeout()


def capped(row, name, fn):
    """Run `fn()` under STAGE_CAP_SECS, recording `<name>_secs` either way.

    Returns `(value, ok)`. On timeout or exception, writes `<name>_error` and
    returns `(None, False)` so the caller can stop the chain for this subject
    while keeping every field measured before the failure. `signal.alarm` is
    used rather than a subprocess because these stages need the in-process
    objects (`LayerGraph`, `FlatFoldResult`) the previous stage produced.

    Note `signal.alarm` can only interrupt a stage that returns to the Python
    interpreter; a stage blocked inside a single long C call (a large numpy
    operation) will overrun its cap. The recorded `<name>_secs` is therefore
    the truth about how long it took, and the cap is a best effort, not a
    guarantee -- which is why the cap is reported in the row."""
    t = time.time()
    old_handler = signal.signal(signal.SIGALRM, _stage_alarm)
    signal.alarm(STAGE_CAP_SECS)
    try:
        val = fn()
    except _StageTimeout:
        row[f"{name}_secs"] = round(time.time() - t, 3)
        row[f"{name}_error"] = f"exceeded {STAGE_CAP_SECS}s stage cap"
        print(f"    {name} TIMEOUT after {STAGE_CAP_SECS}s", flush=True)
        return None, False
    except Exception as exc:                      # noqa: BLE001 - recorded, not swallowed
        row[f"{name}_secs"] = round(time.time() - t, 3)
        row[f"{name}_error"] = f"{type(exc).__name__}: {exc}"
        print(f"    {name} FAILED {type(exc).__name__}: {exc}", flush=True)
        return None, False
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
    row[f"{name}_secs"] = round(time.time() - t, 3)
    return val, True


def cost_curve(row, layout, asg):
    """Spec section 10's per-subject cost curve, on the dense candidate.

    Closes three deliverables of `2026-09-24-dense-pleats-design.md` that the
    original wave left unmeasured: section 10's `faces` / `face pairs` /
    emitted-edge columns, section 11 risk 2's explicit instruction to "measure
    face count and `flat_fold` time per subject and report them, not assume
    the pipeline reaches certification", and section 7's rule that an
    unaffordable verdict "must be recorded as UNDECIDED with its budget ...
    silence is not".

    Runs the SAME call sequence `compile.compile_tree` runs after `assign`
    returns (`to_fold` -> `flat_fold` -> `constraint_graph` -> `certify`),
    plus `propagate` and `cp_audit.audit_fold`, rather than reimplementing
    any of it -- a probe that re-implements production is a recorded trap in
    this project's memory. Each stage is capped independently.

    `audit_*` is measured rather than asserted: README section 3 states local
    validity "by construction of `assign`'s local CSP", which was reasoning,
    not a measurement. This calls the oracle."""
    fold, ok = capped(row, "to_fold", lambda: emit.to_fold(layout, asg))
    if not ok:
        return
    row["emitted_edges"] = len(fold["edges_vertices"])
    row["emitted_vertices"] = len(fold["vertices_coords"])

    ff, ok = capped(row, "flat_fold", lambda: flat_fold.flat_fold(fold))
    if not ok:
        return
    row["faces"] = len(ff.faces)

    graph, ok = capped(row, "constraint_graph", lambda: L.constraint_graph(ff))
    if not ok:
        return
    row["face_pairs"] = len(graph.cons.pairs)

    labels = {k: a for _, _, k, a in ff.shared_edges if a in ("M", "V")}
    row["creased_shared_edges"] = len(labels)

    witness, ok = capped(row, "propagate", lambda: L.propagate(graph, labels))
    if ok:
        row["propagate_contradiction"] = witness is not None
        if witness is not None:
            row["propagate_kind"] = witness.kind

    verdict, ok = capped(row, "certify", lambda: L.certify(graph, labels))
    if ok:
        # Section 7: record the verdict WITH its budget. UNDECIDED says
        # nothing about the crease set, and must not be read as REFUTED.
        row["verdict"] = verdict.kind
        row["verdict_nodes"] = verdict.nodes
        row["verdict_free"] = verdict.free
        row["certify_budget"] = layer_certify.CERTIFY_BUDGET
    else:
        row["verdict"] = "UNMEASURED"

    rep, ok = capped(row, "audit", lambda: cp_audit.audit_fold(fold))
    if ok:
        row["audit_interior_vertices"] = rep.interior_total
        row["audit_maekawa_violations"] = len(rep.maekawa_violations)
        row["audit_kawasaki_violations"] = len(rep.kawasaki_violations)
        row["audit_arrangement_violations"] = len(rep.arrangement_violations)
        row["infeasible_vertices"] = len({
            va.vertex for group in (rep.maekawa_violations,
                                    rep.kawasaki_violations,
                                    rep.arrangement_violations)
            for va in group})


def crease_degree_histogram(N, pieces, labels):
    """{degree -> count of interior vertices with that many M/V-labelled
    incident pieces}. `degree` counts ONLY pieces whose FINAL label is "M"
    or "V" -- a crease -- not "F" or "B". Mirrors `assign()`'s own `inc`
    (built over every piece, not filtered by role) and `interior` (every
    incident vertex not on a boundary row/column) exactly, so the result is
    directly comparable to the reference lizard figures in the plan brief."""
    inc: dict = defaultdict(list)
    for i, p in enumerate(pieces):
        inc[p.a].append(i)
        inc[p.b].append(i)
    hist: Counter = Counter()
    for v, ids in inc.items():
        if v[0] in (0, 2 * N) or v[1] in (0, 2 * N):
            continue
        deg = sum(1 for i in ids if labels[i] in ("M", "V"))
        hist[deg] += 1
    return dict(sorted(hist.items()))


def main():
    entries = {e["subject"]: e for e in json.load(open(RULE6))}
    rows = []
    done = set()
    if os.path.exists(OUT):
        rows = json.load(open(OUT))
        # `cost_curve_done` is required, not just the absence of a timeout:
        # rows written before the cost curve existed are complete by the OLD
        # contract and must still be re-measured under the new one.
        done = {r["subject"] for r in rows
                if not r.get("dense_timeout") and r.get("cost_curve_done")}
        print(f"resuming: {sorted(done)} already recorded", flush=True)

    def flush():
        with open(OUT, "w") as f:
            json.dump(rows, f, indent=1)

    for s in ORDER:
        if s in done:
            continue
        rows = [r for r in rows if r["subject"] != s]  # drop a stale timeout row
        row = {"subject": s}
        t0 = time.time()
        res = compile_tree(entries[s]["requested"], entries[s]["pairs"])
        row["sparse_compile_secs"] = round(time.time() - t0, 1)
        if res.stage_reached != "emit":
            row["error"] = f"sparse compile stopped@{res.stage_reached}: {res.failure!r}"
            rows.append(row)
            flush()
            print(f"{s:11s} SPARSE STOP@{res.stage_reached} {row['error']}", flush=True)
            continue

        N = res.layout.N
        pieces = res.assignment.pieces
        sparse_labels = res.assignment.labels
        row["N"] = N
        row["total_pieces"] = len(pieces)
        row["sparse_mv"] = sum(1 for l in sparse_labels if l in ("M", "V"))
        row["sparse_crease_degree_hist"] = crease_degree_histogram(N, pieces, sparse_labels)
        row["sparse_interior_vertices"] = sum(row["sparse_crease_degree_hist"].values())

        # --- raw (pre-merge) dense grouping, reproducing assign()'s own
        # pipeline exactly, so these numbers are what F.2 itself produced
        # before assign()'s mirror-merge reconciliation folds pairs together.
        face_list = A.faces(N, pieces)
        prof, face_of = A.profiles(N, pieces, res.contours, face_list,
                                   getattr(res.layout, "boundary_elev", None))
        _, _, _, probe = A.initial_readings(N, pieces, res.contours, prof,
                                            face_of, dense=True)
        groups = A.pleat_paths(pieces, probe, dense=True)
        f2_colour, f2_released = interleave.colour(pieces, groups)
        row["pleat_paths_raw"] = len(groups)
        row["coloured_raw"] = len(f2_colour)
        row["released_raw"] = len(f2_released)

        # --- post-merge: assign(dense=True, global_check=None) -- the first
        # locally-feasible candidate, no CEGAR loop. Capped at
        # DENSE_ASSIGN_CAP_SECS wall-clock: assign() itself has only a
        # NODE budget (500_000 by default), which does not bound wall time
        # when a single node's own work (e.g. `violation`'s itertools.product
        # over free variables at a heavily-shared vertex) is expensive.
        t1 = time.time()
        old_alarm = signal.signal(signal.SIGALRM, _alarm)
        signal.alarm(DENSE_ASSIGN_CAP_SECS)
        try:
            asg = A.assign(res.layout, res.ridges, res.boundary_ridges, res.contours,
                           dense=True, global_check=None)
        except _DenseAssignTimeout:
            row["dense_assign_secs"] = round(time.time() - t1, 3)
            row["dense_timeout"] = True
            row["error"] = (f"dense assign(global_check=None) did not return "
                            f"within {DENSE_ASSIGN_CAP_SECS}s wall-clock cap")
            rows.append(row)
            flush()
            print(f"{s:11s} DENSE ASSIGN TIMEOUT after {DENSE_ASSIGN_CAP_SECS}s",
                  flush=True)
            continue
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_alarm)
        row["dense_assign_secs"] = round(time.time() - t1, 3)
        if isinstance(asg, A.AssignFail):
            row["error"] = f"dense assign failed: {asg!r}"
            rows.append(row)
            flush()
            print(f"{s:11s} DENSE ASSIGN FAILED {row['error']}", flush=True)
            continue

        row["dense_mv"] = sum(1 for l in asg.labels if l in ("M", "V"))
        row["coloured_final"] = len(asg.pleat_vars)
        row["released_final"] = len(asg.released_vars)
        row["released_by_conflict"] = len(asg.conflict_vars)
        row["released_by_odd_cycle"] = len(asg.released_vars) - len(asg.conflict_vars)
        row["flipped_from_f2"] = len(asg.flipped_from_f2)
        row["dense_crease_degree_hist"] = crease_degree_histogram(N, pieces, asg.labels)
        row["dense_interior_vertices"] = sum(row["dense_crease_degree_hist"].values())

        # spec section 10's cost curve, on this candidate (see cost_curve's
        # docstring for the three deliverables it closes)
        row["stage_cap_secs"] = STAGE_CAP_SECS
        cost_curve(row, res.layout, asg)
        row["cost_curve_done"] = True

        rows.append(row)
        flush()
        print(f"{s:11s} N={N:3d} sparse_mv={row['sparse_mv']:5d} "
              f"dense_mv={row['dense_mv']:5d} paths={row['pleat_paths_raw']:5d} "
              f"coloured={row['coloured_raw']:5d} released={row['released_raw']:5d} "
              f"conflict={row['released_by_conflict']:4d} flipped={row['flipped_from_f2']:4d} "
              f"dense_assign={row['dense_assign_secs']}s "
              f"sparse_compile={row['sparse_compile_secs']}s", flush=True)


main()
