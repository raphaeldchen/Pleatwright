"""How many minimal causes does ONE dense rejection have?

`order_probe.py` showed that reversing `cores.shrink`'s consumption order returns
a DIFFERENT irreducible core on all 113 rejections, disjoint from the first on
112 of them. Two orders found two disjoint minimal causes. This asks how many
there are, because that decides whether eliminating an obstruction upstream can
work at all: a contradiction with many disjoint minimal causes is not removed by
fixing any one of them.

Prior art. MARCO (Liffiton & Sakallah, *Enumerating Infeasibility*, CPAIOR 2013 /
JAR 2016) is the standard MUS enumerator; it keeps the explored power set as a
Boolean "map" and needs a SAT solver for it. **No SAT solver is installed here**
(pysat, pycosat, z3, ortools all absent), so MARCO's map is unavailable and this
probe uses two arms that need no solver:

  ARM 1 -- COMPLETE, by exhaustion. Rejection 14's cone is **6** creases, so all
  2^6 = 64 subsets are testable. That yields the EXACT set of MUSes for one real
  rejection, with no heuristic, plus an exhaustive check of the MONOTONICITY
  assumption QuickXplain's soundness rests on -- which `cores.py` calls "an
  empirical finding, not a theorem".

  ARM 2 -- LOWER BOUND, by randomised consumption order. QuickXplain returns an
  irreducible core that depends on candidate order, so shuffling the order
  samples the MUS family. Distinct cores found is a LOWER bound on the family's
  size, never an estimate of it.

**Arm 2 is validated against arm 1.** Rejection 14 is in both, so the sampler's
recall is measured against ground truth before any of its numbers elsewhere are
read. A sampler that misses MUSes on the one case we can check completely is not
evidence about the cases we cannot.

RIGOUR. This project has had two throwaway probes drive wrong conclusions, one
because it printed its verdict unconditionally. So: the capture is asserted to
have happened; each captured oracle is checked live against its own precondition;
every MUS reported is re-verified to contradict and to be minimal (each proper
subset must NOT contradict); arm 2's recall against arm 1 is printed; and no
verdict is printed unless all of that passed.
"""
from __future__ import annotations

import itertools
import json
import random
import sys
import time

sys.path.insert(0, ".")

from box_pleat import cores
from box_pleat.compile import compile_tree

RULE6 = ("../docs/superpowers/evidence/2026-09-08-vlm-tree-authoring"
         "/data/rule6_serve.json")

# Rejection indices to capture, chosen by cone size from the committed run
# (`../2026-10-02-witness-identity-113/identity113.json`): 6, 42, 42, 44, 30
# creases respectively. 14 is the only cone small enough to exhaust.
TARGETS = (0, 7, 10, 14, 15)
EXHAUSTIVE = 14
EXHAUSTIVE_MAX_UNIVERSE = 20          # 2^20 calls is the hard refusal line
SHUFFLES = 200
SEED = 20261002


class _Captured(Exception):
    """Abort the compile once every target rejection has been captured.

    Deliberately NOT ValueError/RuntimeError/KeyError, the three
    `compile_tree` catches around `assign(...)`, so it propagates out
    uncaught instead of being typed into an indistinguishable
    `AssignFail("error")`.
    """


def capture_oracles():
    """Run the dense compile until every target rejection's oracle is in hand.

    `cores.shrink` builds `holds` as a closure over `graph` and `labels` and
    passes it to `_core`. Patching `_core` therefore captures a REUSABLE
    oracle -- the closure keeps the graph and that rejection's labels alive
    after the compile has been abandoned -- plus the candidate universe. No
    production code changes, and the captured oracle is the exact one the
    committed run used.
    """
    captured: dict[int, tuple[list, object]] = {}
    real = cores._core
    seen = [0]

    def cap(candidates, holds, counter=None):
        i = seen[0]
        seen[0] += 1
        if i in TARGETS:
            captured[i] = (list(candidates), holds)
        if i >= max(TARGETS):
            raise _Captured
        return real(candidates, holds, counter)

    cores._core = cap
    try:
        with open(RULE6) as fh:
            e = next(x for x in json.load(fh) if x["subject"] == "lizard")
        t0 = time.perf_counter()
        try:
            compile_tree(e["requested"], e["pairs"], dense=True,
                         assign_budget=500_000, core_extraction=False,
                         core_record=True, debug_witness_cores=[])
        except _Captured:
            pass
        secs = round(time.perf_counter() - t0, 1)
    finally:
        cores._core = real

    missing = [t for t in TARGETS if t not in captured]
    if missing:
        raise SystemExit(
            f"REFUSED: rejections {missing} were never captured (the compile "
            f"produced {seen[0]} rejections). Nothing below would be measuring "
            f"what it claims to.")
    print(f"captured {len(captured)} oracles in {secs}s "
          f"(rejections {sorted(captured)}); cone sizes "
          f"{ {k: len(v[0]) for k, v in sorted(captured.items())} }")
    return captured


def check_oracle_live(universe, holds):
    """The precondition QuickXplain assumes: the whole universe contradicts.

    If this is False the oracle is not the one the committed run used, or the
    capture grabbed the wrong call, and every number below would be garbage.
    """
    if not holds(frozenset(universe)):
        raise SystemExit("REFUSED: holds(full universe) is False for a "
                         "captured oracle -- it is not a contradicting cone")


def exhaust(universe, holds):
    """EVERY minimal contradicting subset, by testing all 2^n subsets.

    Returns `(muses, verdicts, monotone_violations)`.

    Complete by construction: a subset is a MUS iff it contradicts and no
    proper subset of it does, and both halves are decided from the full table.
    No heuristic and no ordering is involved, so this is ground truth.
    """
    n = len(universe)
    if n > EXHAUSTIVE_MAX_UNIVERSE:
        raise SystemExit(f"REFUSED: universe of {n} is past the exhaustive "
                         f"limit of {EXHAUSTIVE_MAX_UNIVERSE}")
    verdicts = {}
    for k in range(n + 1):
        for sub in itertools.combinations(sorted(universe), k):
            verdicts[frozenset(sub)] = holds(frozenset(sub))

    contradicting = [s for s, v in verdicts.items() if v]
    muses = [s for s in contradicting
             if not any(t < s and verdicts[t] for t in verdicts)]

    # The monotonicity QuickXplain's soundness rests on, checked EXHAUSTIVELY:
    # holds(S) must imply holds(T) for every T superset of S.
    violations = []
    for s, v in verdicts.items():
        if not v:
            continue
        for t, w in verdicts.items():
            if s < t and not w:
                violations.append((sorted(s), sorted(t)))
    return muses, verdicts, violations


def verify_mus(mus, holds):
    """`mus` contradicts, and every proper subset of it does not."""
    if not holds(frozenset(mus)):
        return "does not contradict"
    for e in mus:
        if holds(frozenset(mus) - {e}):
            return f"not minimal: dropping {e} still contradicts"
    return None


def sample(universe, holds, shuffles, seed):
    """Distinct irreducible cores found over randomised consumption orders.

    A LOWER bound on the MUS family's size. `cores._core` is used unpatched,
    so every returned core has passed its precondition, empty and
    postcondition guards.
    """
    rnd = random.Random(seed)
    found, first_seen, calls = {}, [], [0]

    class _Count:
        def __init__(self, f):
            self.f = f

        def __call__(self, s):
            calls[0] += 1
            return self.f(s)

    counted = _Count(holds)
    order = list(universe)
    for t in range(shuffles):
        rnd.shuffle(order)
        core = cores._core(list(order), counted)
        if core not in found:
            found[core] = t
            first_seen.append(t)
    return found, first_seen, calls[0]


def main(out_path):
    captured = capture_oracles()
    for idx, (universe, holds) in sorted(captured.items()):
        check_oracle_live(universe, holds)
    print("all captured oracles pass holds(full universe)")

    rec = {"subject": "lizard", "targets": list(TARGETS),
           "shuffles": SHUFFLES, "seed": SEED,
           "cone_sizes": {str(k): len(v[0]) for k, v in captured.items()}}

    # ---------------- ARM 1: complete, by exhaustion -------------------
    uni, holds = captured[EXHAUSTIVE]
    t0 = time.perf_counter()
    muses, verdicts, violations = exhaust(uni, holds)
    arm1_secs = round(time.perf_counter() - t0, 2)

    bad = [(sorted(m), verify_mus(m, holds)) for m in muses]
    bad = [b for b in bad if b[1]]
    if bad:
        raise SystemExit(f"REFUSED: arm 1 returned non-MUSes: {bad}")

    print()
    print(f"=== ARM 1 (COMPLETE): rejection {EXHAUSTIVE}, universe "
          f"{len(uni)}, all {2 ** len(uni)} subsets, {arm1_secs}s ===")
    print(f"  contradicting subsets : "
          f"{sum(1 for v in verdicts.values() if v)} of {len(verdicts)}")
    print(f"  MUSes (exact)         : {len(muses)}")
    for m in sorted(muses, key=lambda s: (len(s), sorted(s))):
        print(f"      size {len(m)}  {sorted(m)}")
    pair = [sorted(a & b) for a, b in itertools.combinations(muses, 2)]
    print(f"  pairwise disjoint     : "
          f"{sum(1 for p in pair if not p)} of {len(pair)} MUS pairs")
    print(f"  MONOTONICITY violations: {len(violations)}"
          + ("  <-- QuickXplain's soundness assumption FAILS here"
             if violations else "  (assumption holds exhaustively)"))
    rec["arm1"] = {
        "rejection": EXHAUSTIVE, "universe": len(uni),
        "subsets_tested": len(verdicts),
        "contradicting": sum(1 for v in verdicts.values() if v),
        "mus_count_exact": len(muses),
        "muses": [sorted(map(list, m)) for m in
                  sorted(muses, key=lambda s: (len(s), sorted(s)))],
        "mus_sizes": sorted(len(m) for m in muses),
        "disjoint_pairs": sum(1 for p in pair if not p),
        "total_pairs": len(pair),
        "monotonicity_violations": violations,
        "secs": arm1_secs,
    }

    # ---------------- ARM 2: lower bound, by shuffling -----------------
    print()
    print(f"=== ARM 2 (LOWER BOUND): {SHUFFLES} randomised orders ===")
    rec["arm2"] = {}
    for idx in sorted(captured):
        uni, holds = captured[idx]
        t0 = time.perf_counter()
        found, first_seen, ncalls = sample(uni, holds, SHUFFLES, SEED + idx)
        secs = round(time.perf_counter() - t0, 1)
        sizes = sorted(len(m) for m in found)
        last_new = max(first_seen) if first_seen else -1
        rec["arm2"][str(idx)] = {
            "cone": len(uni), "distinct_muses_found": len(found),
            "mus_sizes": sizes, "last_new_at_shuffle": last_new,
            "oracle_calls": ncalls, "secs": secs,
            "muses": [sorted(map(list, m)) for m in found],
        }
        print(f"  rejection {idx:3} cone {len(uni):3}: "
              f"{len(found):3} distinct MUSes, sizes {sizes[0]}-{sizes[-1]}, "
              f"last new at shuffle {last_new + 1}/{SHUFFLES}, "
              f"{ncalls} calls, {secs}s")

    # ---------------- arm 2 validated against arm 1 --------------------
    a2 = {frozenset(map(tuple, m)) for m in rec["arm2"][str(EXHAUSTIVE)]["muses"]}
    a1 = set(muses)
    recall = len(a1 & a2) / len(a1) if a1 else None
    spurious = a2 - a1
    print()
    print(f"=== ARM 2 VALIDATED AGAINST ARM 1 (rejection {EXHAUSTIVE}) ===")
    print(f"  exact MUSes            : {len(a1)}")
    print(f"  sampler found          : {len(a2)}")
    print(f"  recall                 : "
          + ("n/a" if recall is None else f"{recall:.0%}"))
    print(f"  spurious (not real MUS): {len(spurious)}")
    rec["validation"] = {"exact": len(a1), "sampled": len(a2),
                         "recall": recall, "spurious": len(spurious)}
    if spurious:
        raise SystemExit(f"REFUSED: the sampler returned {len(spurious)} sets "
                         f"that exhaustive enumeration says are not MUSes; it "
                         f"is unsound and its other numbers are unusable")

    with open(out_path, "w") as fh:
        json.dump(rec, fh, indent=1, sort_keys=True)
    print(f"\nwrote {out_path}")

    # ---- the verdict, printed only now, after every check above -------
    print()
    counts = {k: v["distinct_muses_found"] for k, v in rec["arm2"].items()}
    worst = max(counts.values())
    if recall is not None and recall < 0.8:
        print(f"VERDICT WITHHELD: the sampler recovered only {recall:.0%} of "
              f"the MUSes exhaustive enumeration proves exist on rejection "
              f"{EXHAUSTIVE}, so its counts elsewhere are too weak to read as "
              f"lower bounds. Arm 1's exact {len(a1)} stands on its own.")
    elif worst >= 10:
        print(f"VERDICT: MANY. At least {worst} distinct minimal causes on a "
              f"single rejection. Eliminating one obstruction upstream cannot "
              f"remove a contradiction that has {worst}+ disjoint-or-"
              f"overlapping alternatives, so crease-set surgery at a site is "
              f"not a route to convergence. A COMPLETE method (SAT/ILP over "
              f"the layer-ordering constraints) is what remains.")
    elif worst <= 3:
        print(f"VERDICT: FEW. At most {worst} distinct minimal causes found "
              f"per rejection over {SHUFFLES} orders, and exhaustive "
              f"enumeration finds {len(a1)} on rejection {EXHAUSTIVE}. "
              f"Site-elimination is back on the table: the alternatives are "
              f"enumerable.")
    else:
        print(f"VERDICT: INTERMEDIATE. {worst} distinct minimal causes at most "
              f"over {SHUFFLES} orders, exact {len(a1)} on rejection "
              f"{EXHAUSTIVE}. Neither reading is clean; report both counts and "
              f"claim neither.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: mus_probe.py <out.json>")
    main(sys.argv[1])
