"""Were arm B's three rejections three different facts, or one fact three times?

Spec: `../../specs/2026-09-28-witness-identity-design.md`.

A replay of core-in-loop arm B -- dense `lizard`, 500,000-node budget,
`core_extraction=True` -- with ONE thing added: `debug_witness_cores`, which
records the identity of each rejection rather than its size. There is no second
arm: an extraction-off rejection has no core to identify, and arm A's 113
rejections are not the population in question.

WHY IDENTITY AND NOT COUNTS. The A/B settled that the clause narrows (median 202
-> 8 solver variables, 25.2x) and that extraction is not the cost (21.7 s of
954.9 s, 2.27%). It left the terminal outcome unmoved and the rejection count
113 -> 3, which is consistent with two OPPOSITE stories: stronger clauses
excluding more of the space a priori, or a search spending its budget
re-deriving ground it has already forbidden. Every instrument the A/B carried is
aggregate. The distinction is about identity.

WHAT A REPEAT MEANS, PER LEVEL (spec section 5). `candidate` repeating is a
decisive enforcement defect -- nothing may propose a labelling it has already
refuted. `signed` repeating means the loop re-derived a no-good it already
holds: sound but wasted, and the expected signature of `assign.hits_nogood`
pruning only on FULL binding. `keys` repeating means two crease-level no-goods
collapsed to one solver-variable set, so part of the narrowing cannot reach the
clause. `witness` or `core` repeating alone is NEITHER -- one taco_tortilla
among three faces arises under many labellings, and the same crease set under
different labels is a different no-good -- so those two are reported and carry
no verdict.

WHAT THIS CANNOT SAY. Not the clause itself. The clause is `{var: value}` and
`_check` sees neither `var_of` nor `value`; `keys` is the clause's INPUT. So a
`keys` repeat is suggestive and a `signed` repeat is strong, but neither PROVES
a duplicate clause. That needs a `debug_clauses` list in `assign.py`, out of
scope and gated on this run showing a repeat worth chasing.

n = 3, AND THE TEST IS ASYMMETRIC. One repeat is decisive -- a single
recurrence cannot be a statistical artifact. Three distinct is WEAK: consistent
with new territory each time and equally consistent with a loop that would
start repeating at rejection 20. The NEW TERRITORY row must be read as "no
recurrence in the only three rejections this budget produced", never as "the
loop does not re-derive".

THE GUARD COMES FIRST. Arm A reproduced the committed baseline on every
STRUCTURAL figure while differing 1.26x on wall clock, so this loop is
deterministic in structure and not in timing. The replay must therefore
reproduce arm B's structure exactly; if it does not, the instrumentation changed
the run and NO verdict row may be claimed in either direction. Wall clock is
deliberately not guarded.

Run from mcp_harness:
  PYTHONPATH=. ../.venv/bin/python3 -u \\
      ../docs/superpowers/evidence/2026-09-28-witness-identity/identity.py \\
      --selftest
  PYTHONPATH=. ../.venv/bin/python3 -u \\
      ../docs/superpowers/evidence/2026-09-28-witness-identity/identity.py \\
      ../docs/superpowers/evidence/2026-09-28-witness-identity/identity.json
"""
import dataclasses
import json
import os
import statistics
import sys
import time

from box_pleat import cores
from box_pleat.compile import compile_tree

RULE6 = os.path.join("..", "docs", "superpowers", "evidence",
                     "2026-09-08-vlm-tree-authoring", "data", "rule6_serve.json")
BUDGET = 500_000

LEVELS = ("candidate", "witness", "core", "signed", "keys")
# Only these three carry a verdict, in this order (spec section 6.3). A repeat
# at `witness` or `core` alone is reported and changes nothing.
VERDICT_LEVELS = ("candidate", "signed", "keys")
_VERDICT = {
    "candidate": "ENFORCEMENT DEFECT",
    "signed": "LATE ENFORCEMENT",
    "keys": "GRANULARITY CEILING",
}

# Spec section 6.2, from ../2026-09-27-core-in-loop/ab.json. The `debug_cores`
# 4th field (seconds) is deliberately absent: it is wall clock.
ARM_B = {
    "rejections": 3,
    "core_rows": ((44, 8, 31), (361, 5, 47), (65, 8, 43)),
    "failure": "AssignFail(kind='budget', site=500000)",
    "clause_min_median_max": (5, 8, 8),
    # The full sorted population, not the 3-number summary above: min/median/
    # max cannot distinguish a 3-element population from a 4-element one that
    # merely duplicates an existing value (see `guard()`). Same three numbers
    # for n=3, so this does not redefine arm B -- it states it more strongly.
    "clause_sizes_sorted": (5, 8, 8),
    "source": "../2026-09-27-core-in-loop/ab.json",
}


def repeats(rows, level):
    """{value: [row index, ...]} for every value of `level` seen more than once."""
    where: dict = {}
    for i, r in enumerate(rows):
        where.setdefault(r[level], []).append(i)
    return {v: idx for v, idx in where.items() if len(idx) > 1}


def distinct(rows):
    """{level: how many distinct values} across all five levels."""
    return {lv: len({r[lv] for r in rows}) for lv in LEVELS}


def verdict(rows):
    """Spec section 6.3, evaluated in order; the first matching row wins.

    Returns `(verdict, level)` -- `level` is the one that repeated, or `None`
    for NEW TERRITORY.
    """
    for lv in VERDICT_LEVELS:
        if repeats(rows, lv):
            return _VERDICT[lv], lv
    return "NEW TERRITORY", None


def guard(rejections, core_rows, failure, clauses, records):
    """Spec section 6.2. Returns `(passed, [mismatch, ...])`.

    `core_rows` is compared IN ORDER and on its first three fields only: the
    loop is deterministic in structure, so a reordering is a divergence, and
    the 4th field is wall clock, which arm A showed drifts 1.26x on an
    unchanged code path.

    `records` is `len(rows)` -- the `debug_witness_cores` population that
    `verdict()` and `distinct()` are actually computed from. `len(clauses)`
    and `len(core_rows)` are DIFFERENT populations that merely coincide with
    it in arm B: `compile.py` documents that a narrowed clause can come back
    empty and yield a different `AssignFail` instead of a learned no-good, so
    the three counts can diverge even though they all read 3 here. Without
    pinning `records` too, a `rows` population of the wrong size could still
    pass this guard while `verdict()` computes over a population that was
    never checked against arm B.

    The records bar reuses `ARM_B["rejections"]` (3), but unlike the other
    four bars it is not a figure arm B measured: arm B predates
    `debug_witness_cores`, and `../2026-09-27-core-in-loop/ab.json`'s
    `arms[1]` carries no witness-record count at all. It is INFERRED from
    `len(core_rows) == 3` plus `compile.py`'s two append sites (`"core"` and
    `"witness"`) sitting in the same basic block of `_check` -- a sound
    inference, but a different kind of number from the other four.
    """
    bad = []
    if rejections != ARM_B["rejections"]:
        bad.append(f"rejections {rejections} != {ARM_B['rejections']}")
    got = tuple(tuple(r[:3]) for r in core_rows)
    if got != ARM_B["core_rows"]:
        bad.append(f"core rows {got} != {ARM_B['core_rows']}")
    if failure != ARM_B["failure"]:
        bad.append(f"failure {failure!r} != {ARM_B['failure']!r}")
    if records != ARM_B["rejections"]:
        bad.append(f"records {records} != {ARM_B['rejections']}")
    # min/median/max is a LOSSY summary of a population: [5, 8, 8] and
    # [5, 8, 8, 8] report the same three numbers, because the extra element
    # duplicates one already present (int(median) does not rescue this either
    # -- int(8.0) == 8 too). So the actual check below compares the full
    # sorted population against ARM_B["clause_sizes_sorted"], which is
    # strictly stronger and -- unlike relying on `rejections`/`core_rows`/
    # `records` above to pin the population size -- is a property of this
    # function alone, not of how `main` happens to wire its call site.
    trip = ((min(clauses), statistics.median(clauses), max(clauses))
            if clauses else None)
    sizes = tuple(sorted(clauses))
    if sizes != ARM_B["clause_sizes_sorted"]:
        bad.append(f"clause min/median/max {trip} != "
                   f"{ARM_B['clause_min_median_max']} "
                   f"(sorted sizes {sizes} != {ARM_B['clause_sizes_sorted']})")
    return not bad, bad


def serialise(value):
    """frozensets -> sorted lists, tuples -> lists, dataclasses -> dicts.

    Sorting is what makes the artifact diffable: a frozenset's iteration order
    is not stable across runs, so an unsorted dump would differ run to run for
    reasons that are not findings.
    """
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {k: serialise(v)
                for k, v in dataclasses.asdict(value).items()}
    if isinstance(value, frozenset):
        return sorted(serialise(v) for v in value)
    if isinstance(value, tuple):
        return [serialise(v) for v in value]
    if isinstance(value, dict):
        return {str(k): serialise(v) for k, v in value.items()}
    return value


def _selftest():
    """The guard and the bar, exercised on synthetic rows.

    Project memory: "two throwaway probes drove wrong conclusions in one
    session; one printed its verdict unconditionally". This runs in
    milliseconds and must pass before the 16-minute replay is spent.
    """
    def row(cand, wit, core, signed, keys):
        return {"candidate": cand, "witness": wit, "core": core,
                "signed": signed, "keys": keys}

    # Values spell out their own level (candidateN/witnessN/coreN/signedN/
    # keysN) so a misreading of which field an override targets is
    # self-correcting on sight, not just correct in the assertion.
    a = row("candidate1", "witness1", "core1", "signed1", "keys1")
    b = row("candidate2", "witness2", "core2", "signed2", "keys2")
    c = row("candidate3", "witness3", "core3", "signed3", "keys3")

    # --- the bar, all four rows -------------------------------------------
    assert verdict([a, b, c]) == ("NEW TERRITORY", None)
    assert verdict([a, b, dict(c, candidate="candidate1")]) == (
        "ENFORCEMENT DEFECT", "candidate")
    assert verdict([a, b, dict(c, signed="signed1")]) == (
        "LATE ENFORCEMENT", "signed")
    assert verdict([a, b, dict(c, keys="keys1")]) == (
        "GRANULARITY CEILING", "keys")

    # --- precedence: candidate wins over signed, signed over keys ---------
    both = dict(c, candidate="candidate1", signed="signed1", keys="keys1")
    assert verdict([a, b, both]) == ("ENFORCEMENT DEFECT", "candidate")
    assert verdict([a, b, dict(c, signed="signed1", keys="keys1")]) == (
        "LATE ENFORCEMENT", "signed")

    # --- witness or core repeating alone selects NO row -------------------
    assert verdict([a, b, dict(c, witness="witness1")]) == (
        "NEW TERRITORY", None)
    assert verdict([a, b, dict(c, core="core1")]) == ("NEW TERRITORY", None)

    # --- repeats() reports WHERE, not just whether ------------------------
    assert repeats([a, b, dict(c, candidate="candidate1")], "candidate") == {
        "candidate1": [0, 2]}
    assert repeats([a, b, c], "candidate") == {}

    # --- distinct() covers all five levels -------------------------------
    assert distinct([a, b, c]) == {lv: 3 for lv in LEVELS}
    assert distinct([a, b, dict(c, core="core1")])["core"] == 2

    # --- the guard passes ONLY on arm B's exact structure -----------------
    ok_rows = [(44, 8, 31, 5.069), (361, 5, 47, 9.789), (65, 8, 43, 6.847)]
    passed, bad = guard(3, ok_rows, ARM_B["failure"], [8, 5, 8], 3)
    assert passed, bad
    # seconds are free
    passed, _ = guard(3, [(44, 8, 31, 0.0), (361, 5, 47, 0.0), (65, 8, 43, 0.0)],
                      ARM_B["failure"], [5, 8, 8], 3)
    assert passed
    # clause order is free, values are not
    assert guard(3, ok_rows, ARM_B["failure"], [5, 8, 8], 3)[0]
    assert not guard(3, ok_rows, ARM_B["failure"], [5, 8, 9], 3)[0]
    # a 4-element clause list with every OTHER argument matching arm B
    # exactly (rejections=3, records=3) must still fail: min/median/max
    # cannot tell [5, 8, 8, 8] from [5, 8, 8] (both give (5, 8, 8), even past
    # int(median)), so only comparing the full sorted population catches it.
    assert not guard(3, ok_rows, ARM_B["failure"], [5, 8, 8, 8], 3)[0]
    # core-row ORDER is not free
    assert not guard(3, [ok_rows[1], ok_rows[0], ok_rows[2]],
                     ARM_B["failure"], [8, 5, 8], 3)[0]
    # each field is actually checked
    assert not guard(4, ok_rows, ARM_B["failure"], [8, 5, 8], 3)[0]
    assert not guard(3, ok_rows[:2], ARM_B["failure"], [8, 5], 3)[0]
    assert not guard(3, ok_rows, "AssignFail(kind='layer_unsat', site=None)",
                     [8, 5, 8], 3)[0]
    assert not guard(3, ok_rows, ARM_B["failure"], [], 3)[0]
    # records is checked independently of rejections/core_rows/clauses: the
    # verdict is computed from `rows`, so a right-shaped-everything-else
    # guard call with the wrong `records` must still fail.
    assert not guard(3, ok_rows, ARM_B["failure"], [8, 5, 8], 0)[0]

    # --- serialise() is sorted, JSON-clean, and stable -------------------
    fs = frozenset({(12, 13), (2, 6), (5, 6)})
    assert serialise(fs) == [[2, 6], [5, 6], [12, 13]]
    signed = frozenset({((5, 6), "V"), ((2, 6), "M")})
    assert serialise(signed) == [[[2, 6], "M"], [[5, 6], "V"]]
    json.dumps(serialise({"core": fs, "signed": signed}))

    # --- serialise() on a dataclass (the untested branch: the real payload
    # for `witness` is `layers.Witness`, not a string or frozenset) --
    @dataclasses.dataclass(frozen=True)
    class _FakeWitness:
        kind: str
        creases: frozenset
        faces: tuple
        prov: str

    fw = _FakeWitness(kind="taco_tortilla",
                      creases=frozenset({(5, 6), (2, 6)}),
                      faces=(1, 2, 3), prov="msg")
    assert serialise(fw) == {
        "kind": "taco_tortilla", "creases": [[2, 6], [5, 6]],
        "faces": [1, 2, 3], "prov": "msg"}
    json.dumps(serialise(fw))

    # A synthetic row whose values are frozensets plus that dataclass -- not
    # strings -- so distinct()/repeats()/verdict() are proven against the
    # real payload's hashability, not just the string stand-ins above. `fw`
    # goes in the `witness` slot (that is the field it stands in for; `core`
    # gets an ordinary frozenset, like the other four fields).
    d = row(frozenset({1, 2}), fw, frozenset({3, 4}),
            frozenset({5, 6}), frozenset({7, 8}))
    assert distinct([a, b, d]) == {lv: 3 for lv in LEVELS}
    assert repeats([a, b, d], "core") == {}
    assert verdict([a, b, d]) == ("NEW TERRITORY", None)

    print("selftest OK: bar (4 rows + precedence + the two silent levels), "
          "guard (11 cases), repeats, distinct, serialise (incl. dataclass)")


def main(out):
    with open(RULE6) as fh:
        entry = next(e for e in json.load(fh) if e["subject"] == "lizard")

    rows: list = []
    core_rows: list = []
    clauses: list = []
    res = None
    err = None
    t0 = time.time()
    try:
        res = compile_tree(entry["requested"], entry["pairs"], dense=True,
                           assign_budget=BUDGET, core_extraction=True,
                           debug_cores=core_rows, debug_clause_sizes=clauses,
                           debug_witness_cores=rows)
    except cores.CoreExtractionError as exc:
        # A DISTINCT outcome, not a crash: extraction refused its own pre- or
        # postcondition, so every clause this run learned is invalid and no
        # verdict row may be claimed. Nothing else is caught.
        err = f"{type(exc).__name__}: {exc}"
    secs = round(time.time() - t0, 1)

    rec = {
        "subject": "lizard",
        "assign_budget": BUDGET,
        "arm_b": {k: serialise(v) for k, v in ARM_B.items()},
        "core_extraction_error": err,
        "secs": secs,
        "rejections": len(clauses),
        # `debug_witness_cores` row count -- the population verdict() and
        # distinct() are actually computed from. It coincides with
        # `rejections` (len(clauses)) in arm B but is a DIFFERENT
        # population; see guard()'s docstring.
        "records": len(rows),
        "core_rows": core_rows,
        "clause_sizes": clauses,
        "stage_reached": res.stage_reached if res else None,
        "failure": repr(res.failure) if res else None,
        "layer_verdict": repr(res.verdict) if res else None,
        "layers_tried": res.layers_tried if res else None,
    }

    def flush():
        with open(out, "w") as fh:
            json.dump(rec, fh, indent=1)

    # Cheap structural fields hit disk BEFORE the rejection records are
    # serialised: `witness` holds a real `layers.Witness` dataclass here
    # (unlike the selftest's string stand-ins; `core` is a crease frozenset,
    # not a dataclass -- see `compile.py`'s `_check`), and a serialise()
    # failure on either must not cost the 16-minute compile's other numbers.
    flush()

    rec["rejection_records"] = [{lv: serialise(r[lv]) for lv in LEVELS}
                                for r in rows]
    flush()

    if err is not None:
        rec["guard_passed"] = False
        rec["verdict"] = "CORE EXTRACTION ERROR"
        flush()
        print(f"CORE EXTRACTION ERROR: {err}")
        print("cores.shrink refused its own pre/postcondition, so the clauses "
              "this run learned are invalid. NO row of section 6.3 may be "
              "claimed, in either direction.")
        return

    print(f"stage={rec['stage_reached']} failure={rec['failure']} "
          f"rejections={rec['rejections']} secs={secs}")

    passed, bad = guard(len(clauses), core_rows, rec["failure"], clauses,
                       len(rows))
    rec["guard_passed"] = passed
    rec["guard_mismatches"] = bad
    flush()

    if not passed:
        rec["verdict"] = "GUARD FAILED"
        flush()
        print("GUARD FAILED (spec section 6.2) -- the replay did not reproduce "
              "arm B's structure, so the instrumentation changed the run and "
              "this measures something other than arm B. NO row of section 6.3 "
              "may be claimed, in either direction.")
        for m in bad:
            print(f"  {m}")
        return

    print("guard PASSED: arm B's structure reproduced exactly")

    counts = distinct(rows)
    rec["distinct"] = counts
    n = len(rows)
    print(f"  distinct over {n} rejections: "
          + "  ".join(f"{lv}={counts[lv]}" for lv in LEVELS))

    rec["repeats"] = {lv: {str(serialise(v)): idx
                           for v, idx in repeats(rows, lv).items()}
                      for lv in LEVELS}
    v, level = verdict(rows)
    rec["verdict"] = v
    rec["verdict_level"] = level
    flush()

    for lv in LEVELS:
        for value, idx in repeats(rows, lv).items():
            print(f"  REPEAT at {lv}, rejections {idx}: {serialise(value)}")

    print()
    print(f"VERDICT: {v}" + (f" (at {level})" if level else ""))
    if v == "ENFORCEMENT DEFECT":
        print("A labelling was refuted twice. Stop this experiment line and fix "
              "assign's hits_nogood/retry. The A/B's numbers stand; every "
              "interpretation treating a rejection as new information does not.")
    elif v == "LATE ENFORCEMENT":
        print("The loop re-derived a no-good it already holds. Sound but "
              "wasted, and what hits_nogood pruning only on FULL binding "
              "predicts. Next lever is clause PROPAGATION during descent, not "
              "the local CSP.")
    elif v == "GRANULARITY CEILING":
        print("Two crease-level no-goods collapsed to one solver-variable set, "
              "so part of the 25.2x narrowing cannot reach the clause.")
    else:
        print(f"No recurrence in the only {n} rejections this budget produced. "
              f"The clause lever is finished AT THIS BUDGET: the 166,667 nodes "
              f"between rejections are the local CSP working through a "
              f"legitimately narrowed space, corroborating the independent "
              f"79.57% profile. This is WEAK evidence (section 6.4): it is "
              f"equally consistent with a loop that would start repeating at "
              f"rejection 20.")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        main(sys.argv[1])
