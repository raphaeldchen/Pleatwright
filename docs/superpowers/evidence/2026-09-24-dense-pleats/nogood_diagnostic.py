"""Is the dense CEGAR negative lizard-specific? Run the SAME diagnostic on ANY
subject (Task 8 Step 2).

The subject is `argv[1]`, so this script is not scoped to one animal. Its title
said "on `bird`" until 2026-09-27, which was the plan's intent, not the
script's behaviour and not what was run: `bird` was abandoned by hand after 27
minutes and produced no artifact, and the committed artifacts from this script
are `nogood-lizard.json`, `nogood-lizard-largebudget.json` and
`nogood-horse.json`. See `README.md` §6 for why `horse` does not corroborate
`lizard`.

Production's own layer-order filter lives as a closure (`_check`) inside
`box_pleat.compile.compile_tree` and is not importable on its own, so this
script reconstructs the identical call sequence `_check` makes --
`emit.to_fold` -> `flat_fold.flat_fold` -> `box_pleat.layers.constraint_graph`
(once) -> `box_pleat.layers.propagate` (per candidate) ->
`box_pleat.layers.piece_keys` (on a rejection) -- wrapped with instrumentation
that records, per rejection: the number of implicated creases (`len(keys)`,
the unit-piece decomposition `piece_keys` returns -- the same quantity
`assign()` turns into a no-good clause) and the witness's identity (the
`Witness` dataclass itself: frozen, and every field -- `kind`, the `creases`
frozenset, the `faces` tuple, the `prov` string -- is hashable, so two
rejections that are genuinely the same recurring contradiction hash equal).
This is not a second implementation of the layer-order logic, only of the
one-line spy wrapper `compile.py`'s `_check` does not expose.

Reference figures from `lizard` at the DEFAULT budget, as committed in
`nogood-lizard.json` (`partial: false`): 113 candidates refused over 834.0s,
node budget exhausted at 500,000 (`AssignFail(kind='budget', site=500000)`);
clause size min 39 / median 2,069 / max 3,161 implicated creases; **113
distinct witnesses of 113 rejections, top witness 1x**.

An earlier revision of this docstring said "38 distinct witnesses of 113; top
witness repeated 15 times". That is WITHDRAWN: it came from a throwaway probe
that keyed a witness by a 40-character truncated slice of its `repr`, so
distinct contradictions sharing a face triple collided. This script hashes the
full frozen `Witness` and is the instrument that refuted it. The conclusion
that rested on the repetition -- "no budget increase can converge this" -- is
withdrawn with it, which is the reason the `budget`/`layer_checks` arguments
below exist.

The clause-size figures above are CREASE (unit-piece) counts -- `len(keys)`, the quantity `piece_keys` returns. Production's actual
no-good clause is over SOLVER VARIABLES (`assign()`'s own
`{var_of[idx[k]]: value[...] for k in keys ...}`), which is strictly smaller
once run-merging, pleat-path grouping and mirror-merging have collapsed
several creases onto one variable -- and that variable-level size was, until
this script's `debug_clause_sizes` hook, never measured at all. This script
now records both: `clause_size_*` (creases, as before) and
`var_clause_size_*` (variables, via `assign(..., debug_clause_sizes=...)`),
in lockstep -- one entry of each per rejection, since `assign()` builds the
variable-level clause immediately after calling this script's `spy`, before
doing anything else with the result.

DEFAULTS ARE `compile_tree`'s OWN (`assign_budget=500_000`,
`layer_checks=200`) so a default run stays comparable with
`nogood-lizard.json`. Both are overridable on the command line for a
large-budget run; a run that overrides them records the values it used in its
own output, so no artifact is ambiguous about which budget produced it.

A wall-clock hard cap (`TIME_CAP_SECS`) is enforced from inside the spy --
`assign()` has no wall-clock budget of its own, only node-count and
rejection-count budgets. Reaching the cap is recorded as its own outcome,
distinct from exhausting a budget, and is NOT a statement about the crease
set.

`core_*` / `crease_freq_top` answer a question the default run left open: do
the clauses concentrate on a small set of creases (a core a minimal-unsat-core
extractor could target) or keep reaching fresh ones (a wandering search)?
Tracked at CREASE granularity because that is what the spy receives; since
creases collapse onto variables many-to-one, a crease-level core implies a
variable-level one.

Run from mcp_harness:
  PYTHONPATH=. ../.venv/bin/python3 -u \
      ../docs/superpowers/evidence/2026-09-24-dense-pleats/nogood_diagnostic.py \
      SUBJECT OUT.json [TIME_CAP_SECS [BUDGET [LAYER_CHECKS]]]
"""
import json
import os
import statistics
import sys
import time

import flat_fold

from box_pleat import assign as A
from box_pleat import emit
from box_pleat import layers as L
from box_pleat.compile import compile_tree

SUBJECT = sys.argv[1]
OUT = sys.argv[2]
TIME_CAP_SECS = float(sys.argv[3]) if len(sys.argv) > 3 else 1200.0
BUDGET = int(sys.argv[4]) if len(sys.argv) > 4 else 500_000
LAYER_CHECKS = int(sys.argv[5]) if len(sys.argv) > 5 else 200
RULE6 = os.path.join("..", "docs", "superpowers", "evidence",
                     "2026-09-08-vlm-tree-authoring", "data", "rule6_serve.json")


class TimeCapReached(Exception):
    pass


def main():
    entries = {e["subject"]: e for e in json.load(open(RULE6))}
    e = entries[SUBJECT]

    t_sparse0 = time.time()
    res = compile_tree(e["requested"], e["pairs"])
    sparse_secs = round(time.time() - t_sparse0, 1)
    if res.stage_reached != "emit":
        json.dump({"subject": SUBJECT, "error":
                   f"sparse compile stopped@{res.stage_reached}: {res.failure!r}"},
                  open(OUT, "w"), indent=1)
        print(f"{SUBJECT} SPARSE STOP@{res.stage_reached}", flush=True)
        return

    graph_cell: list = []
    topo_cell: list = []
    rejections: list = []          # [{clause_size, witness_key}]
    witness_counts: dict = {}      # witness identity -> count
    var_clause_sizes: list = []    # filled by assign()'s debug_clause_sizes hook
    crease_freq: dict = {}         # crease key -> how many clauses named it
    trace: list = []               # per rejection: [index, elapsed, clause_size]
    deadline = [time.time() + TIME_CAP_SECS]
    t_start = time.time()
    outcome = {"kind": None}

    def flush(partial=False):
        clause_sizes = [r["clause_size"] for r in rejections]
        # var_clause_sizes is filled by assign() in lockstep with rejections
        # (one append each, same order) -- see this module's docstring.
        row = {
            "subject": SUBJECT,
            "sparse_compile_secs": sparse_secs,
            "rejections": len(rejections),
            "elapsed_secs": round(time.time() - t_start, 1),
            "clause_size_min": min(clause_sizes) if clause_sizes else None,
            "clause_size_median": (statistics.median(clause_sizes)
                                   if clause_sizes else None),
            "clause_size_max": max(clause_sizes) if clause_sizes else None,
            "var_clause_size_min": min(var_clause_sizes) if var_clause_sizes else None,
            "var_clause_size_median": (statistics.median(var_clause_sizes)
                                       if var_clause_sizes else None),
            "var_clause_size_max": max(var_clause_sizes) if var_clause_sizes else None,
            "assign_budget": BUDGET,
            "layer_checks": LAYER_CHECKS,
            "time_cap_secs": TIME_CAP_SECS,
            # Do the clauses concentrate on a core, or keep reaching fresh
            # creases? `core_distinct_creases` is the union over all clauses;
            # dividing it by `rejections` gives fresh-creases-per-rejection.
            "core_distinct_creases": len(crease_freq),
            "core_creases_named_once": sum(1 for v in crease_freq.values() if v == 1),
            "crease_freq_max": max(crease_freq.values()) if crease_freq else None,
            "crease_freq_top": sorted(crease_freq.values(), reverse=True)[:25],
            "trace": trace,
            "distinct_witnesses": len(witness_counts),
            "top_witness_count": (max(witness_counts.values())
                                  if witness_counts else None),
            "witness_count_histogram": sorted(witness_counts.values(), reverse=True),
            "outcome": outcome,
            "partial": partial,
        }
        json.dump(row, open(OUT, "w"), indent=1)
        return row

    def spy(cand):
        if time.time() > deadline[0]:
            raise TimeCapReached()
        fold = emit.to_fold(res.layout, cand)
        ff = flat_fold.flat_fold(fold)
        topo = (fold["vertices_coords"], fold["edges_vertices"])
        if not graph_cell:
            graph_cell.append(L.constraint_graph(ff))
            topo_cell.append(topo)
        else:
            assert topo == topo_cell[0], (
                "nogood_diagnostic.spy: candidate fold topology drifted "
                "from candidate 1's -- see box_pleat.compile._check's own "
                "docstring for what this means")
        labels = {k: a for _, _, k, a in ff.shared_edges if a in ("M", "V")}
        w = L.propagate(graph_cell[0], labels)
        if w is None:
            return None
        keys = L.piece_keys(w, fold)
        rejections.append({"clause_size": len(keys)})
        for k in keys:
            crease_freq[k] = crease_freq.get(k, 0) + 1
        trace.append([len(rejections), round(time.time() - t_start, 1), len(keys)])
        witness_counts[w] = witness_counts.get(w, 0) + 1
        if len(rejections) % 10 == 0:
            flush(partial=True)
            print(f"{SUBJECT} ... {len(rejections)} rejections, "
                  f"{round(time.time() - t_start, 1)}s, "
                  f"distinct_witnesses={len(witness_counts)}, "
                  f"core_creases={len(crease_freq)}", flush=True)
        return keys, w

    try:
        asg = A.assign(res.layout, res.ridges, res.boundary_ridges, res.contours,
                       dense=True, global_check=spy,
                       layer_checks=LAYER_CHECKS, budget=BUDGET,
                       debug_clause_sizes=var_clause_sizes)
        outcome["kind"] = "assign_returned"
        outcome["detail"] = ("AssignFail: " + repr(asg)
                             if isinstance(asg, A.AssignFail) else "accepted")
    except TimeCapReached:
        outcome["kind"] = "time_cap"
        outcome["detail"] = f"exceeded {TIME_CAP_SECS}s wall-clock cap"

    row = flush(partial=False)
    print(f"{SUBJECT} DONE rejections={row['rejections']} "
          f"elapsed={row['elapsed_secs']}s outcome={outcome} "
          f"clause_size(min/median/max)={row['clause_size_min']}/"
          f"{row['clause_size_median']}/{row['clause_size_max']} "
          f"var_clause_size(min/median/max)={row['var_clause_size_min']}/"
          f"{row['var_clause_size_median']}/{row['var_clause_size_max']} "
          f"distinct_witnesses={row['distinct_witnesses']} "
          f"top_witness={row['top_witness_count']}", flush=True)


main()
