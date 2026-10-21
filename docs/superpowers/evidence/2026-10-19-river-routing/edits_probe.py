"""River-routing acceptance §8.5: the branching named edits, packing only.

For each of the 109 branching edits of the 2026-10-10 branching-packer probe
(`antlered` on the 35 rolls with a `head`, `toed` on the 39 rolls where it
branches, `lopsided` on the same 35 as `antlered`; `tests/test_pack_chain.py`),
two real calls: `pipeline.pack_options(tree, beside=False)` (today's search)
and `pipeline.pack_options(tree, beside=True)` (production, BESIDE_WORK_BUDGET
and BESIDE_MAX_BUILDS as calibrated).  Records each call's verdict, S / U and
the grid the auto rule chooses.  No search code is copied.

usage (from mcp_harness/):
  PYTHONPATH=.:tests python ../docs/superpowers/evidence/2026-10-19-river-routing/edits_probe.py \
      [--workers N] [EDIT:ROLL ...] > edits.jsonl

One JSON line per edit, flushed as it completes (order not guaranteed).
Trees: named edits of the 51 artifact trees only (CLAUDE.md §5)."""
import argparse
import json
import multiprocessing as mp
import os
import sys
import tempfile
import time


def _grid(o):
    return None if o is None else o.layout.N


def _one(PL, path, beside):
    t0 = time.perf_counter()
    opts = PL.pack_options(path, beside=beside)
    secs = time.perf_counter() - t0
    c, reason = PL._choose(opts, "auto", "flag")
    return {"verdict": opts.verdict, "S": _grid(opts.symmetric),
            "U": opts.n_smaller if opts.smaller is None else _grid(opts.smaller),
            "C": _grid(c), "chosen": c.name if c else None, "reason": reason if c else None,
            "family": c.family if c else None, "beside": opts.beside,
            "hubs": len(opts.con.hubs), "seconds": round(secs, 2)}


def probe(job):
    edit, roll = job
    from pleatwright import pipeline as PL
    import test_pack_chain as TPC
    out = {"edit": edit, "roll": roll}
    try:
        tree = getattr(TPC, edit)(roll)
        d = tempfile.mkdtemp(prefix=f"edit_{edit}_{roll}_")
        path = os.path.join(d, "tree.json")
        with open(path, "w") as f:
            json.dump(tree, f)
        out["off"] = _one(PL, path, False)
        out["on"] = _one(PL, path, True)
        a, b = out["off"]["C"], out["on"]["C"]
        out["shrank"] = a is not None and b is not None and b < a
        out["newly_packs"] = a is None and b is not None
    except Exception as e:                      # recorded, never crashes the pool
        out["error"] = f"{type(e).__name__}: {e}"
    return out


def branching_jobs():
    """The 2026-10-10 probe's enumeration (probe_branching.py): each edit that
    applies to a roll and leaves a hub of degree > 2."""
    from artifact_trees import ROLLS
    from pleatwright import pack as PK
    from pleatwright import stick as ST
    import test_pack_chain as TPC
    jobs = []
    for edit in ("antlered", "toed", "lopsided"):
        for roll in ROLLS:
            try:
                tree = getattr(TPC, edit)(roll)
            except (KeyError, ValueError, StopIteration):
                continue
            _, nb = PK._hub_graph(ST.contract(ST.load_tree(tree, 1.0)))
            if any(len(v) > 2 for v in nb.values()):
                jobs.append((edit, roll))
    return jobs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("jobs", nargs="*", help="EDIT:ROLL (default: all branching edits)")
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args(argv)
    jobs = [tuple(j.split(":")) for j in a.jobs] if a.jobs else branching_jobs()
    counts = {}
    for e, _ in jobs:
        counts[e] = counts.get(e, 0) + 1
    print(f"{len(jobs)} edits selected {counts}", file=sys.stderr)
    if not jobs:
        return 1
    with mp.get_context("spawn").Pool(min(a.workers, len(jobs))) as pool:
        for rec in pool.imap_unordered(probe, jobs):
            print(json.dumps(rec), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
