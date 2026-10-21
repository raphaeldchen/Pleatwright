"""Is crease (135,136)'s dominance a QuickXplain SPLIT-ORDER artifact?

`cores.shrink` consumes candidates in `sorted(creases)` order and returns an
IRREDUCIBLE core, not a minimum one -- so which irreducible set comes back
depends on the consumption order. `layer_order._propagate` is also not
confluent. Measured on the committed 500,000-node run
(`evidence/2026-10-02-witness-identity-113/identity113.json`), (135,136) is a
load-bearing element of the minimal core in **106 of 113** rejections, and it
sits a median 31% through the sorted cone -- so it is not merely being consumed
first. That weakens the artifact hypothesis without closing it.

This probe closes it: the same compile, the same 113 rejections, extraction
consuming candidates in REVERSED order. The core is diagnostic-only
(`core_record=True`), so the search cannot be perturbed by which core is found,
and the guard proves the search reproduced.

RIGOUR, because this project has twice had a throwaway probe drive a wrong
conclusion -- one printed its verdict unconditionally, one used a truncated
repr as an object identity:

  1. The reversal is verified LIVE before the real run (a synthetic oracle
     whose two irreducible cores differ by order), and the wrapper counts its
     own calls -- so "no change" can never be confused with "patch inert".
  2. The 113 cones are compared PAIRWISE against the committed run. If any
     differs, the two runs did not see the same rejections and the comparison
     is refused.
  3. The guard reproduces arm A's published structure, or no verdict.
  4. Nothing is printed as a verdict unless every check above passed.
"""
from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, ".")

from box_pleat import cores
from box_pleat.compile import compile_tree

HERE = os.path.dirname(os.path.abspath(__file__))
RULE6 = os.path.join("..", "docs", "superpowers", "evidence",
                     "2026-09-08-vlm-tree-authoring", "data",
                     "rule6_serve.json")
COMMITTED = os.path.join(
    "..", "docs", "superpowers", "evidence",
    "2026-10-02-witness-identity-113", "identity113.json")

TARGET = (135, 136)
EXPECTED = {"rejections": 113, "layers_tried": 113,
            "failure": "AssignFail(kind='budget', site=500000)",
            "clause_vars_min": 6, "clause_vars_median": 202,
            "clause_vars_max": 259}

_calls = [0]


def install_reversed_order():
    """Wrap `cores._core` so candidates arrive in DESCENDING order.

    `shrink` passes `sorted(creases)`; this reverses that list before
    `_core` splits it. `_core`'s own precondition / empty / postcondition
    guards still run, so soundness is unchanged -- only which irreducible
    set the recursion converges on can differ.

    `cores.shrink`'s fixed order is deliberate and documented (a core found
    twice must be the same core), so it is NOT edited: this patch is local to
    this probe's process.
    """
    real = cores._core

    def reversed_core(candidates, holds, counter=None):
        _calls[0] += 1
        return real(list(candidates)[::-1], holds, counter)

    cores._core = reversed_core


def verify_patch_is_live():
    """Prove the reversal changes which irreducible core comes back.

    Oracle: a set "holds" iff it contains 'a' or it contains 'z'. Both {'a'}
    and {'z'} are irreducible. Ascending consumption returns one, descending
    the other -- so if the patched call returns the same core as the unpatched
    one, the patch is inert and this probe would silently measure nothing.
    """
    def holds(s):
        return ("a" in s) or ("z" in s)

    cand = ["a", "m", "z"]
    unpatched = cores.quickxplain(cand, holds)
    before = _calls[0]
    patched = cores._core(cand, holds)
    if _calls[0] != before + 1:
        raise SystemExit("REFUSED: the _core wrapper was not called; the "
                         "monkeypatch is not installed")
    if patched == unpatched:
        raise SystemExit(
            f"REFUSED: patched core {set(patched)} equals unpatched "
            f"{set(unpatched)}, so reversing the candidate order changed "
            f"nothing even on a case built to be order-sensitive. A null "
            f"result from the real run would be uninterpretable.")
    print(f"patch live: ascending -> {set(unpatched)}, "
          f"descending -> {set(patched)}")


def key(x):
    """A recorded serialised crease list -> a comparable frozenset of tuples."""
    return frozenset(tuple(e) for e in x)


def main():
    with open(COMMITTED) as fh:
        old = json.load(fh)
    old_recs = old["rejection_records"]
    if len(old_recs) != EXPECTED["rejections"]:
        raise SystemExit(f"REFUSED: committed artifact has {len(old_recs)} "
                         f"records, not {EXPECTED['rejections']}")

    install_reversed_order()
    verify_patch_is_live()

    with open(RULE6) as fh:
        e = next(x for x in json.load(fh) if x["subject"] == "lizard")

    clauses, rows = [], []
    t0 = time.perf_counter()
    res = compile_tree(e["requested"], e["pairs"], dense=True,
                       assign_budget=500_000, core_extraction=False,
                       core_record=True, debug_clause_sizes=clauses,
                       debug_witness_cores=rows)
    secs = round(time.perf_counter() - t0, 1)
    print(f"stage={res.stage_reached} failure={res.failure!r} "
          f"rejections={len(clauses)} records={len(rows)} secs={secs} "
          f"extractions={_calls[0] - 1}")

    # ---- guard: same search, same structure, or no verdict ---------------
    bad = []
    if len(clauses) != EXPECTED["rejections"]:
        bad.append(f"rejections {len(clauses)}")
    if res.layers_tried != EXPECTED["layers_tried"]:
        bad.append(f"layers_tried {res.layers_tried}")
    if repr(res.failure) != EXPECTED["failure"]:
        bad.append(f"failure {res.failure!r}")
    if len(rows) != EXPECTED["rejections"]:
        bad.append(f"records {len(rows)}")
    if clauses:
        s = sorted(clauses)
        for got, k in ((s[0], "clause_vars_min"),
                       (s[len(s) // 2], "clause_vars_median"),
                       (s[-1], "clause_vars_max")):
            if got != EXPECTED[k]:
                bad.append(f"{k} {got} != {EXPECTED[k]}")
    if bad:
        raise SystemExit("REFUSED -- GUARD FAILED, no verdict: "
                         + "; ".join(bad))

    refusals = [r for r in rows if r["core_error"] is not None]
    if refusals:
        raise SystemExit(f"REFUSED: {len(refusals)} extraction(s) refused, so "
                         f"the populations are not comparable")

    # ---- equality check: did both runs see the SAME rejections? ----------
    mismatched = [i for i, (o, n) in enumerate(zip(old_recs, rows))
                  if key(o["witness"]["creases"]) != frozenset(n["witness"].creases)]
    if mismatched:
        raise SystemExit(
            f"REFUSED: {len(mismatched)} of 113 cones differ from the "
            f"committed run (first at index {mismatched[0]}), so the two runs "
            f"did not see the same rejections in the same order and no "
            f"per-rejection comparison is valid")
    print("equality check: all 113 cones identical to the committed run")

    # ---- the measurement -------------------------------------------------
    old_cores = [key(r["core"]) for r in old_recs]
    new_cores = [frozenset(r["core"]) for r in rows]

    changed = sum(1 for a, b in zip(old_cores, new_cores) if a != b)
    old_hits = sum(1 for c in old_cores if TARGET in c)
    new_hits = sum(1 for c in new_cores if TARGET in c)
    old_distinct = len(set(old_cores))
    new_distinct = len(set(new_cores))
    old_sizes = sorted(len(c) for c in old_cores)
    new_sizes = sorted(len(c) for c in new_cores)

    print()
    print("                        ascending (committed)   descending (this run)")
    print(f"  cores that differ     {'-':>20}   {changed:>21} of 113")
    print(f"  contain {TARGET}      {old_hits:>20} of 113   {new_hits:>21} of 113")
    print(f"  distinct cores        {old_distinct:>20}   {new_distinct:>21}")
    print(f"  core size min/med/max {old_sizes[0]}/{old_sizes[56]}/{old_sizes[-1]:<16}"
          f"   {new_sizes[0]}/{new_sizes[56]}/{new_sizes[-1]}")

    out = {
        "subject": "lizard", "order": "descending",
        "secs": secs, "extractions": _calls[0] - 1,
        "guard_passed": True, "cones_identical": True,
        "cores_changed": changed,
        "target": list(TARGET),
        "target_hits_ascending": old_hits,
        "target_hits_descending": new_hits,
        "distinct_ascending": old_distinct,
        "distinct_descending": new_distinct,
        "core_sizes_descending": new_sizes,
        "new_cores": [sorted(map(list, c)) for c in new_cores],
    }
    with open(sys.argv[1], "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
    print(f"\nwrote {sys.argv[1]}")

    # The verdict is printed ONLY here, after every check above passed.
    print()
    if changed == 0:
        print("VERDICT: the core is ORDER-INVARIANT on all 113 rejections -- "
              "reversing consumption changed nothing, so (135,136)'s "
              f"{new_hits}/113 is not a split-order artifact.")
    elif new_hits >= 90:
        print(f"VERDICT: STRUCTURAL. {changed} of 113 cores changed under "
              f"reversal, yet {TARGET} is still load-bearing in "
              f"{new_hits}/113. Its dominance survives a different split "
              f"order, so it is not an artifact of consumption order.")
    elif new_hits <= 30:
        print(f"VERDICT: ARTIFACT. {TARGET} falls from {old_hits}/113 to "
              f"{new_hits}/113 under reversal, so the ascending run's "
              f"dominance was an artifact of QuickXplain's split order. The "
              f"23-cause pool, not the crease, is the real object.")
    else:
        print(f"VERDICT: PARTIAL. {TARGET} reads {new_hits}/113 under "
              f"reversal against {old_hits}/113 ascending -- neither the "
              f"structural nor the artifact reading is clean, and the figure "
              f"is order-sensitive. Report both and claim neither.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: order_probe.py <out.json>")
    main()
