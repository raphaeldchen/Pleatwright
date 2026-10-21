"""Did dense `lizard`'s 113 rejections name 113 obstructions, or a few?

Spec: `../../specs/2026-10-02-witness-identity-113-design.md`.

Arm A's configuration plus `core_record=True`: the search receives the same
unshrunk cone keys it always has, so the committed 113-rejection baseline is
preserved, while the record gains the true minimal cause.

TWO BARS, both pre-registered in the spec before this file existed. The solver
bar is the predecessor's (`../2026-09-28-witness-identity/`) VERBATIM -- only
the population changes, 3 -> 113 -- because that run's outcome is now known
and a bar re-chosen with that knowledge is not a bar. The geometry bar is new.

`--selftest` runs every bar row, both bars' precedence, invalidity conditions
1 to 4 (1 and 2 through the guard, 3 the malformed-record NO VERDICT, 4 the
population floors), and the mutations the spec pre-registers. Condition 5 is an
external pre-flight gate that lives in a separate test file and is NOT testable
here. Run it before the real
run; a bar nobody has exercised is not a bar either.
"""
from __future__ import annotations

import os
import sys

# ---------------------------------------------------------------- constants

# The committed arm-A baseline this run must reproduce, from
# `../2026-09-27-core-in-loop/ab.json` `arms[0]`. Structure only: wall clock
# has drifted 0.82x-1.26x across replays of UNCHANGED code, so guarding it
# would fail the experiment for reasons unrelated to the instrument.
ARM_A = {
    "source": "../2026-09-27-core-in-loop/ab.json arms[0]",
    "rejections": 113,
    "layers_tried": 113,
    "failure": "AssignFail(kind='budget', site=500000)",
    "clause_vars_min": 6,
    "clause_vars_median": 202,
    "clause_vars_max": 259,
}

EXPECTED_REJECTIONS = 113

# Pre-registered thresholds (spec 5.4). DO NOT change these to fit the data.
FACES_LOCALISED = 10
CORE_LOCALISED = 20
CORE_BOUNDED = 40
MIN_CORE_POPULATION = 90

# Levels reported. `core_keys` carries NO bar row (spec 5.3) and `kind` and
# `faces` carry none alone (spec 5.4); all four are still reported.
LEVELS = ("candidate", "witness", "core", "signed", "keys", "core_keys",
          "faces", "kind")

# The solver bar's rows, in evaluation order, with the level each reads.
SOLVER_ROWS = (("1 ENFORCEMENT DEFECT", "candidate"),
               ("2 LATE ENFORCEMENT", "signed"),
               ("3 GRANULARITY CEILING", "keys"))


# ------------------------------------------------------------- accessors

def value_at(row, level):
    """The value of `level` in one record.

    `faces` and `kind` live on the witness rather than at the top level, and
    are reached here rather than by every caller, so a future level added to
    `LEVELS` has exactly one place to be taught about.
    """
    if level == "faces":
        return row["witness"].faces
    if level == "kind":
        return row["witness"].kind
    return row[level]


def population(rows, level):
    """The rows at which `level` actually has a value.

    A record whose extraction refused carries `core`, `signed` and
    `core_keys` as `None`. Those rows are NOT members of those levels'
    populations: counting `None` as a distinct value would fabricate one
    shared identity across every refused rejection, which understates
    distinctness exactly where the geometry bar reads it.
    """
    return [r for r in rows if value_at(r, level) is not None]


# ---------------------------------------------------------------- counting

def multiplicity(rows, level) -> dict:
    """value -> how many rows carry it, over `population(rows, level)`."""
    out = {}
    for r in population(rows, level):
        v = value_at(r, level)
        out[v] = out.get(v, 0) + 1
    return out


def distinct(rows, level) -> int:
    return len(multiplicity(rows, level))


def repeats(rows, level) -> dict:
    """value -> the row indices carrying it, for values carried more than once.

    Indices are into `rows` as given, not into the filtered population, so a
    reported index can be looked up in the artifact directly.
    """
    seen = {}
    for i, r in enumerate(rows):
        v = value_at(r, level)
        if v is None:
            continue
        seen.setdefault(v, []).append(i)
    return {v: idx for v, idx in seen.items() if len(idx) > 1}


def chao1(mult: dict):
    """Chao (1984) lower-bound estimate of the number of classes not seen.

    `S_obs + f1^2/(2*f2)`. REFERENCE FIGURE ONLY, never a bar level: Chao1
    assumes independent sampling and these rejections are outputs of one
    search. Returns `None` when `f2` is 0, where the estimator is undefined --
    not 0.0, and not `S_obs`, either of which would read as a measurement.
    """
    counts = list(mult.values())
    f1 = sum(1 for c in counts if c == 1)
    f2 = sum(1 for c in counts if c == 2)
    if f2 == 0:
        return None
    return len(counts) + (f1 * f1) / (2.0 * f2)


def overlaps(rows, level) -> list:
    """Pairwise intersections as `(i, j, shared, |a|, |b|)` for every pair.

    `i` and `j` index into `rows` AS GIVEN -- the same convention `repeats`
    uses -- so a reported pair can be looked up in the artifact directly.
    Indexing into the filtered population instead shifts silently as soon as
    one extraction refuses, which is precisely the degraded case a reader
    would be trying to understand.

    Raises `TypeError` for a level whose values are not sets. Returning `[]`
    there would be indistinguishable from a genuine empty result -- and for a
    set-valued level with two or more members the result is never empty, since
    even disjoint pairs appear with a shared count of 0.

    Distinct is not disjoint. The predecessor's three candidates read fully
    distinct while agreeing on 677 of 745 labels, and a reader finds that
    unaided; this is what lets the report state it first.
    """
    idx = [i for i, r in enumerate(rows) if value_at(r, level) is not None]
    for i in idx:
        if not isinstance(value_at(rows[i], level), frozenset):
            raise TypeError(
                f"overlaps({level!r}): values are "
                f"{type(value_at(rows[i], level)).__name__}, not frozenset. "
                f"A pairwise intersection is meaningless for a non-set level, "
                f"and returning [] would be indistinguishable from a genuine "
                f"empty result.")
    out = []
    for x in range(len(idx)):
        for y in range(x + 1, len(idx)):
            i, j = idx[x], idx[y]
            a, b = value_at(rows[i], level), value_at(rows[j], level)
            out.append((i, j, len(a & b), len(a), len(b)))
    return out


# ------------------------------------------------------------------- guard

def guard(rejections, layers_tried, failure, clause_sizes, n_records):
    """Did this run reproduce arm A's STRUCTURE? Returns `(passed, mismatches)`.

    Arm B's guard compared three exact per-rejection triples in order. Arm A
    published no `core_rows`, so this guard compares a count and a
    min/median/max -- weaker, and the strongest the committed baseline
    affords. The run publishes its full 113-value clause-size population so a
    future replay can guard it exactly.
    """
    bad = []
    if rejections != ARM_A["rejections"]:
        bad.append(f"rejections {rejections} != {ARM_A['rejections']}")
    if layers_tried != ARM_A["layers_tried"]:
        bad.append(f"layers_tried {layers_tried} != {ARM_A['layers_tried']}")
    if failure != ARM_A["failure"]:
        bad.append(f"failure {failure!r} != {ARM_A['failure']!r}")
    if n_records != ARM_A["rejections"]:
        bad.append(f"records {n_records} != {ARM_A['rejections']}")
    if not clause_sizes:
        bad.append("clause_sizes is EMPTY -- nothing to compare")
    else:
        if len(clause_sizes) != ARM_A["rejections"]:
            bad.append(f"clause_sizes has {len(clause_sizes)} entries, "
                       f"not {ARM_A['rejections']}")
        s = sorted(clause_sizes)
        med = s[len(s) // 2]
        for got, key in ((s[0], "clause_vars_min"), (med, "clause_vars_median"),
                         (s[-1], "clause_vars_max")):
            if got != ARM_A[key]:
                bad.append(f"{key} {got} != {ARM_A[key]}")
    return (not bad), bad


# -------------------------------------------------------------------- bars

REQUIRED_RECORD_KEYS = ("candidate", "witness", "keys")


def malformed(rows) -> list:
    """Indices of records missing a field that EVERY recording path writes.

    `core`, `signed`, `core_keys` and `core_error` are deliberately not
    required: a refused extraction legitimately carries them as `None`. The
    three above are written on every path, so a record without one is a broken
    instrument rather than a fact about the fold -- spec section 5.5 condition
    3 makes that NO VERDICT, rather than a bare `KeyError` raised from
    `value_at` partway through an analysis that has already printed figures.
    """
    return [i for i, r in enumerate(rows)
            if any(k not in r for k in REQUIRED_RECORD_KEYS)]


def solver_bar(rows) -> dict:
    """The predecessor's bar (its spec 6.3), verbatim, on this population.

    Rows are evaluated in order and the first match wins. Rows 1 and 3 read
    levels present on every record; row 2 reads `signed`, which exists only
    where a core does, so its population can be smaller and is reported.

    Row 2 fires at ANY population size -- a repeat is decisive at n=1, which
    is the predecessor's own asymmetry argument, so a DETECTED repeat is never
    suppressed for being rare. What a small population forbids is the
    ABSENCE of a row-2 repeat supporting row 4 (spec 5.5 condition 4).
    """
    bad = malformed(rows)
    if bad:
        # SAME KEY SET as the normal return below. `None`, never `0`, for what
        # was not measured: a zero would read as a measured count of zero,
        # which is the defaulting mistake this module exists to avoid.
        return {"verdict": "NO VERDICT", "verdict_level": None,
                "signed_population": None,
                "partial": True, "malformed_records": bad,
                "note": (f"{len(bad)} of {len(rows)} records are missing one "
                         f"of {REQUIRED_RECORD_KEYS}; first ten indices "
                         f"{bad[:10]}. The instrument is broken, so no bar "
                         f"row is claimed (spec 5.5 condition 3).")}
    n_signed = len(population(rows, "signed"))
    out = {"signed_population": n_signed, "partial": False, "note": None,
           "malformed_records": []}
    for name, level in SOLVER_ROWS:
        rep = repeats(rows, level)
        if rep:
            out["verdict"] = name
            out["verdict_level"] = level
            if level == "signed" and n_signed < EXPECTED_REJECTIONS:
                out["note"] = (f"row 2 fired on a signed population of "
                               f"{n_signed}, not {EXPECTED_REJECTIONS}")
            elif level == "keys" and n_signed < EXPECTED_REJECTIONS:
                # Row 3 firing means row 2 was evaluated BEFORE it and found
                # no `signed` repeat -- over a short population. Row 1 needs
                # no such note: a candidate repeat fires before row 2 is
                # looked at, so that verdict makes no claim about `signed`.
                out["partial"] = True
                out["note"] = (
                    f"row 3 fired, so row 2 was evaluated and found no "
                    f"`signed` repeat -- but in only {n_signed} of "
                    f"{EXPECTED_REJECTIONS} rejections, so that absence is "
                    f"not a statement about {EXPECTED_REJECTIONS}")
            return out
    out["verdict_level"] = None
    if n_signed < MIN_CORE_POPULATION:
        out["verdict"] = "ROWS 1 AND 3 ONLY -- ROW 4 DECLINED"
        out["partial"] = True
        out["note"] = (
            f"no repeat at candidate or keys over {len(rows)} rejections, but "
            f"the signed population is {n_signed} < {MIN_CORE_POPULATION}, so "
            f"row 2's absence is untested and cannot support NEW TERRITORY")
        return out
    out["verdict"] = "4 NEW TERRITORY"
    if n_signed < EXPECTED_REJECTIONS:
        out["partial"] = True
        out["note"] = (f"row 4 reached with a signed population of {n_signed} "
                       f"of {EXPECTED_REJECTIONS}: PARTIAL")
    return out


def geometry_bar(rows) -> dict:
    """The new bar (spec 5.4). Rows in order, first match wins.

    G1 requires BOTH `faces` and `core` to be small: `layers.py:52` annotates
    `faces` "diagnostic only", so it may strengthen a row `core` supports and
    may never fire one alone. `core` <= CORE_LOCALISED with `faces` above its
    threshold therefore selects G2, and `faces` small with `core` above
    CORE_BOUNDED selects G3.
    """
    bad = malformed(rows)
    if bad:
        # SAME KEY SET as the normal return below. `None`, never `0`, for what
        # was not measured: a zero would read as a measured count of zero,
        # which is the defaulting mistake this module exists to avoid.
        return {"verdict": "NO VERDICT", "verdict_level": None,
                "core_population": None, "distinct_core": None,
                "distinct_faces": None, "distinct_kind": None,
                "partial": True, "malformed_records": bad,
                "note": (f"{len(bad)} of {len(rows)} records are missing one "
                         f"of {REQUIRED_RECORD_KEYS}; first ten indices "
                         f"{bad[:10]}. The instrument is broken, so no bar "
                         f"row is claimed (spec 5.5 condition 3).")}
    cored = population(rows, "core")
    n = len(cored)
    # ALL THREE counts are over `cored`, never over `rows`. `faces` and `kind`
    # live on the witness and are never `None`, so a refused extraction would
    # otherwise contribute a face triple to the site count while contributing
    # no cause to the core count -- making G1's two conditions measurements of
    # two different populations. A refused rejection has no IDENTIFIED
    # obstruction, so it is a member of neither. The two coincide when n == 113,
    # which is exactly why a mismatch here would surface only in the degraded
    # case, where it does the most damage.
    out = {"core_population": n,
           "partial": n < EXPECTED_REJECTIONS,
           "distinct_core": distinct(cored, "core"),
           "distinct_faces": distinct(cored, "faces"),
           "distinct_kind": distinct(cored, "kind"),
           "verdict_level": None,
           "malformed_records": [],
           "note": None}
    if n < MIN_CORE_POPULATION:
        out["verdict"] = "NO VERDICT"
        out["note"] = (f"core population {n} < {MIN_CORE_POPULATION}: "
                       f"extraction refused on {len(rows) - n} of "
                       f"{len(rows)} rejections")
        return out
    d_core, d_faces = out["distinct_core"], out["distinct_faces"]
    if d_faces <= FACES_LOCALISED and d_core <= CORE_LOCALISED:
        out["verdict"] = "G1 LOCALISED"
    elif d_core <= CORE_BOUNDED:
        out["verdict"] = "G2 BOUNDED"
    else:
        out["verdict"] = "G3 DIFFUSE"
        out["note"] = (
            "G3 IS THE SOFT VERDICT. `layer_order._propagate` is not "
            "confluent, so a cone is A derivation of the contradiction rather "
            "than THE cause, and distinctness may be derivational rather than "
            "geometric: 113 distinct cores are consistent with ONE "
            "obstruction reached 113 different ways. G3 licenses 'repeats are "
            "not exploitable through this instrument', NOT 'the geometry is "
            "fine'.")
    if out["partial"]:
        out["note"] = " ".join(
            x for x in (out["note"],
                        f"POPULATION IS {n}, NOT {EXPECTED_REJECTIONS}.")
            if x)
    return out


# -------------------------------------------------------------- serialiser

def serialise(v):
    """JSON-safe and order-stable. NOT type-preserving.

    A frozenset is sorted, which is what makes two runs' artifacts diffable; a
    bare `list(frozenset)` is hash-ordered and would differ run to run for
    identical content. A tuple and a frozenset BOTH serialise to a list, so the
    two are not distinguishable in the output -- a reader who needs to know
    which a field was must know it from the schema, not from the JSON.
    """
    if isinstance(v, frozenset):
        return sorted(serialise(x) for x in v)
    if isinstance(v, tuple):
        return [serialise(x) for x in v]
    if isinstance(v, (str, int, float)) or v is None:
        return v
    if hasattr(v, "kind") and hasattr(v, "creases"):
        return {"kind": v.kind, "creases": serialise(v.creases),
                "faces": serialise(v.faces), "prov": str(v.prov)}
    return str(v)


# ---------------------------------------------------------------- selftest

class _W:
    """A Witness stand-in: the bars read only `kind`, `creases`, `faces`."""

    def __init__(self, kind="taco_tortilla", faces=(1, 2, 3), creases=()):
        self.kind = kind
        self.faces = faces
        self.creases = frozenset(creases)
        self.prov = f"{kind} among {faces}"


def _row(cand, core, keys, faces=(1, 2, 3), signed=None, core_keys=None,
         err=None):
    return {"candidate": frozenset(cand), "witness": _W(faces=faces),
            "core": None if core is None else frozenset(core),
            "signed": (None if core is None
                       else frozenset(signed if signed is not None else core)),
            "keys": frozenset(keys),
            "core_keys": (None if core is None
                          else frozenset(core_keys if core_keys is not None
                                         else core)),
            "core_error": err}


def _spread(n, start=0):
    """`n` rows, all distinct at every level, with distinct face triples."""
    return [_row([("c", i)], [i], [i], faces=(i, i + 1, i + 2))
            for i in range(start, start + n)]


def selftest():
    # --- population excludes refusals rather than counting None -----------
    rows = _spread(3) + [_row([("c", 99)], None, [99], err="refused")]
    assert len(population(rows, "core")) == 3
    assert len(population(rows, "keys")) == 4
    assert distinct(rows, "core") == 3, (
        "a refused row must not join the core population")

    # --- multiplicity, repeats, chao1 -------------------------------------
    dup = _spread(3) + [_row([("c", 0)], [0], [0], faces=(0, 1, 2))]
    m = multiplicity(dup, "core")
    assert sorted(m.values()) == [1, 1, 2]
    assert repeats(dup, "core") == {frozenset([0]): [0, 3]}
    # `repeats` reports indices into `rows` AS GIVEN, like `overlaps`. A
    # refused row before the duplicate pair is what distinguishes that from
    # indices into the filtered population.
    shifted = ([_row([("c", 90)], None, [90], err="refused")]
               + _spread(3) + [_row([("c", 0)], [0], [0], faces=(0, 1, 2))])
    assert repeats(shifted, "core") == {frozenset([0]): [1, 4]}, (
        repeats(shifted, "core"))
    assert chao1({"a": 1, "b": 1, "c": 2}) == 3 + (2 * 2) / 2.0
    assert chao1({"a": 1, "b": 1}) is None, "f2=0 must be None, not 0.0"

    # --- overlaps: row indices, and a refusal to guess at non-set levels ---
    ov = overlaps([_row([("c", 0)], [1, 2, 3], [1]),
                   _row([("c", 1)], [3, 4, 5], [2])], "core")
    assert ov == [(0, 1, 1, 3, 3)], ov
    # indices are into `rows`, NOT into the filtered population
    ov2 = overlaps([_row([("c", 9)], None, [9], err="refused"),
                    _row([("c", 0)], [1, 2, 3], [1]),
                    _row([("c", 1)], [3, 4, 5, 6], [2])], "core")
    assert ov2 == [(1, 2, 1, 3, 4)], ov2
    try:
        overlaps(_spread(3), "faces")
    except TypeError as exc:
        assert "not frozenset" in str(exc)
    else:
        raise AssertionError(
            "overlaps must REFUSE a non-set level rather than return []")

    # --- guard ------------------------------------------------------------
    good = [6] + [202] * 111 + [259]
    ok, bad = guard(113, 113, ARM_A["failure"], good, 113)
    assert ok and bad == [], bad
    for args, needle in (
            ((112, 113, ARM_A["failure"], good, 113), "rejections"),
            ((113, 112, ARM_A["failure"], good, 113), "layers_tried"),
            ((113, 113, "AssignFail(kind='unsat', site=None)", good, 113),
             "failure"),
            ((113, 113, ARM_A["failure"], good, 112), "records"),
            ((113, 113, ARM_A["failure"], [], 113), "EMPTY"),
            ((113, 113, ARM_A["failure"], [7] + [202] * 111 + [259], 113),
             "clause_vars_min"),
            ((113, 113, ARM_A["failure"], [6] + [203] * 111 + [259], 113),
             "clause_vars_median"),
            ((113, 113, ARM_A["failure"], [6] + [202] * 111 + [260], 113),
             "clause_vars_max"),
            ((113, 113, ARM_A["failure"], [6] + [202] * 110 + [259], 113),
             "clause_sizes has 112 entries"),
    ):
        ok, bad = guard(*args)
        assert not ok and any(needle in b for b in bad), (args, bad)

    # --- solver bar, every row and its precedence -------------------------
    base = _spread(113)
    assert solver_bar(base)["verdict"] == "4 NEW TERRITORY"
    assert solver_bar(base)["partial"] is False

    cand_dup = _spread(112) + [_row([("c", 0)], [900], [900], faces=(9, 9, 9))]
    v = solver_bar(cand_dup)
    assert v["verdict"] == "1 ENFORCEMENT DEFECT" and v["verdict_level"] == "candidate"

    sig_dup = _spread(112) + [_row([("c", 900)], [0], [900], faces=(9, 9, 9))]
    v = solver_bar(sig_dup)
    assert v["verdict"] == "2 LATE ENFORCEMENT" and v["verdict_level"] == "signed"

    key_dup = _spread(112) + [_row([("c", 900)], [900], [0], faces=(9, 9, 9))]
    v = solver_bar(key_dup)
    assert v["verdict"] == "3 GRANULARITY CEILING" and v["verdict_level"] == "keys"
    assert solver_bar(key_dup)["partial"] is False, (
        "row 3 over a FULL signed population must not be labelled PARTIAL")
    assert solver_bar(key_dup)["note"] is None

    # precedence: signed beats keys when both repeat and candidate does not.
    # Without this a swap of rows 2 and 3 survived the whole selftest: every
    # other fixture repeats at exactly one level, or at all three.
    sig_and_key = _spread(112) + [_row([("c", 900)], [0], [0], faces=(9, 9, 9))]
    v = solver_bar(sig_and_key)
    assert v["verdict"] == "2 LATE ENFORCEMENT" and v["verdict_level"] == "signed", v

    # precedence: candidate beats signed beats keys when all three repeat
    allthree = _spread(112) + [_row([("c", 0)], [0], [0], faces=(9, 9, 9))]
    assert solver_bar(allthree)["verdict"] == "1 ENFORCEMENT DEFECT"

    # row 2 fires at ANY population -- a repeat is decisive at n=1
    tiny = ([_row([("c", i)], None, [i], faces=(i, i, i)) for i in range(111)]
            + [_row([("c", 900)], [0], [900], faces=(8, 8, 8)),
               _row([("c", 901)], [0], [901], faces=(9, 9, 9))])
    v = solver_bar(tiny)
    assert v["verdict"] == "2 LATE ENFORCEMENT", v
    assert v["signed_population"] == 2 and "not 113" in v["note"]

    # row 4 is DECLINED when the signed population is too small
    thin = ([_row([("c", i)], None, [i], faces=(i, i, i)) for i in range(60)]
            + _spread(53, start=1000))
    v = solver_bar(thin)
    assert v["verdict"] == "ROWS 1 AND 3 ONLY -- ROW 4 DECLINED", v
    assert v["partial"] is True

    # row 4 is PARTIAL when the population is short of 113 but above the floor
    short = ([_row([("c", i)], None, [i], faces=(i, i, i)) for i in range(10)]
             + _spread(103, start=1000))
    v = solver_bar(short)
    assert v["verdict"] == "4 NEW TERRITORY" and v["partial"] is True
    assert "PARTIAL" in v["note"]

    # --- row 3 over a short signed population is PARTIAL and says so ------
    # (core 900 rather than 1000: a core of [1000] would repeat the spread's
    # own signed value and fire row 2, which is not the case under test)
    k_short = ([_row([("c", i)], None, [i], faces=(i, i, i))
                for i in range(59)]
               + _spread(53, start=1000)
               + [_row([("c", 900)], [900], [1000], faces=(7, 7, 7))])
    v = solver_bar(k_short)
    assert v["verdict"] == "3 GRANULARITY CEILING", v
    assert v["signed_population"] == 54, v["signed_population"]
    assert v["partial"] is True
    assert "not a statement about 113" in v["note"]

    # --- geometry bar, every row and the G1/G2 boundary -------------------
    # G1: few sites AND few causes
    g1 = [_row([("c", i)], [i % 7], [i], faces=((i % 5), 1, 2))
          for i in range(113)]
    v = geometry_bar(g1)
    assert v["verdict"] == "G1 LOCALISED", v
    assert v["distinct_core"] == 7 and v["distinct_faces"] == 5
    # a FULL population must not be labelled PARTIAL: `n < EXPECTED_REJECTIONS`
    # mutated to `<=` is invisible to every other fixture, and would make a
    # complete run publish "PARTIAL ... POPULATION IS 113, NOT 113".
    assert geometry_bar(g1)["partial"] is False
    assert geometry_bar(g1)["note"] is None

    # G2 by the faces threshold alone: cores few, sites many
    g2 = [_row([("c", i)], [i % 7], [i], faces=(i, 1, 2)) for i in range(113)]
    v = geometry_bar(g2)
    assert v["verdict"] == "G2 BOUNDED", v
    assert v["distinct_core"] == 7 and v["distinct_faces"] == 113

    # G2 by the core threshold: 30 causes, in (CORE_LOCALISED, CORE_BOUNDED]
    g2b = [_row([("c", i)], [i % 30], [i], faces=(1, 2, 3))
           for i in range(113)]
    assert geometry_bar(g2b)["verdict"] == "G2 BOUNDED"

    # G3: many distinct causes even though every site is the same
    g3 = [_row([("c", i)], [i], [i], faces=(1, 2, 3)) for i in range(113)]
    v = geometry_bar(g3)
    assert v["verdict"] == "G3 DIFFUSE", v
    assert v["distinct_faces"] == 1 and "not exploitable" in v["note"]
    assert "confluent" in v["note"], "G3 must carry its own softness inline"

    # NO VERDICT below the floor
    nv = ([_row([("c", i)], None, [i], faces=(i, i, i)) for i in range(30)]
          + _spread(83, start=1000))
    v = geometry_bar(nv)
    assert v["verdict"] == "NO VERDICT" and v["core_population"] == 83
    assert "refused on 30 of 113" in v["note"]

    # PARTIAL above the floor but below 113
    pv = ([_row([("c", i)], None, [i], faces=(i, i, i)) for i in range(10)]
          + [_row([("c", 1000 + i)], [i % 7], [1000 + i], faces=(i % 5, 1, 2))
             for i in range(103)])
    v = geometry_bar(pv)
    assert v["verdict"] == "G1 LOCALISED" and v["partial"] is True
    assert "POPULATION IS 103, NOT 113" in v["note"]
    assert not v["note"].startswith(" "), "no stray leading space"

    # --- the three verdict thresholds are INCLUSIVE ------------------------
    # A threshold is only tested by a fixture sitting ON it: cases chosen for
    # "clearly inside" and "clearly outside" never exercise the comparison
    # operator. All three `<=` survived mutation to `<` before these existed.
    f10 = [_row([("c", i)], [i % 7], [i], faces=(i % 10, 1, 2))
           for i in range(113)]
    v = geometry_bar(f10)
    assert (v["distinct_faces"], v["distinct_core"]) == (10, 7), v
    assert v["verdict"] == "G1 LOCALISED", "faces == 10 must still be G1"

    f11 = [_row([("c", i)], [i % 7], [i], faces=(i % 11, 1, 2))
           for i in range(113)]
    v = geometry_bar(f11)
    assert v["distinct_faces"] == 11
    assert v["verdict"] == "G2 BOUNDED", "faces == 11 must fall out of G1"

    c20 = [_row([("c", i)], [i % 20], [i], faces=(i % 5, 1, 2))
           for i in range(113)]
    v = geometry_bar(c20)
    assert (v["distinct_core"], v["distinct_faces"]) == (20, 5), v
    assert v["verdict"] == "G1 LOCALISED", "core == 20 must still be G1"

    c21 = [_row([("c", i)], [i % 21], [i], faces=(i % 5, 1, 2))
           for i in range(113)]
    v = geometry_bar(c21)
    assert v["distinct_core"] == 21
    assert v["verdict"] == "G2 BOUNDED", "core == 21 must fall out of G1"

    c40 = [_row([("c", i)], [i % 40], [i], faces=(i, 1, 2))
           for i in range(113)]
    v = geometry_bar(c40)
    assert (v["distinct_core"], v["distinct_faces"]) == (40, 113), v
    assert v["verdict"] == "G2 BOUNDED", "core == 40 must still be G2"

    c41 = [_row([("c", i)], [i % 41], [i], faces=(i, 1, 2))
           for i in range(113)]
    v = geometry_bar(c41)
    assert v["distinct_core"] == 41
    assert v["verdict"] == "G3 DIFFUSE", "core == 41 must fall through to G3"

    # --- geometry reads `core`; the solver bar reads `signed` --------------
    # This is the two bars' stated independence: ONE obstruction recurring
    # under 113 different label patterns is one geometric cause and 113
    # legitimately different no-goods. `geometry_bar` reading `signed` here
    # would see 113 distinct and say G3 where `core` says G1.
    split = [_row([("c", i)], [i % 7], [i], faces=(i % 5, 1, 2),
                  signed=[(i, "M")]) for i in range(113)]
    v = geometry_bar(split)
    assert v["distinct_core"] == 7, v["distinct_core"]
    assert distinct(split, "signed") == 113
    assert v["verdict"] == "G1 LOCALISED", (
        "geometry_bar must read `core`, not `signed`")
    assert solver_bar(split)["verdict"] == "4 NEW TERRITORY", (
        "the same geometric cause under distinct label patterns is NOT a "
        "solver repeat")

    # --- distinct_kind is over the cored population and is counted ---------
    mixed = ([_row([("c", i)], [i % 7], [i], faces=(i % 5, 1, 2))
              for i in range(60)]
             + [_row([("c", 500 + i)], [i % 7], [500 + i], faces=(i % 5, 1, 2))
                for i in range(53)])
    for r in mixed[60:]:
        r["witness"].kind = "tortilla_tortilla"
    assert geometry_bar(mixed)["distinct_kind"] == 2
    assert geometry_bar(_spread(113))["distinct_kind"] == 1
    # a REFUSED row's kind must not be counted: its witness is never `None`,
    # so counting over `rows` rather than `cored` would add a kind with no
    # identified obstruction behind it
    refused_kind = _spread(112) + [_row([("c", 900)], None, [900],
                                        faces=(9, 9, 9), err="refused")]
    refused_kind[-1]["witness"].kind = "tortilla_tortilla"
    assert geometry_bar(refused_kind)["distinct_kind"] == 1, (
        "distinct_kind must be counted over the cored population")

    # --- condition 3: a malformed record is NO VERDICT from BOTH bars ------
    broken = _spread(113)
    del broken[7]["keys"]
    assert malformed(broken) == [7]
    for bar in (solver_bar, geometry_bar):
        v = bar(broken)
        assert v["verdict"] == "NO VERDICT", (bar.__name__, v)
        assert v["malformed_records"] == [7]
        assert "condition 3" in v["note"]
    assert malformed(_spread(5)) == []
    assert set(solver_bar(broken)) == set(solver_bar(_spread(113))), (
        "solver_bar's malformed path returns a different key set from its "
        "normal path, so a caller reading a field that exists on one and not "
        "the other gets a KeyError after the run has already been paid for")
    assert set(geometry_bar(broken)) == set(geometry_bar(_spread(113))), (
        "geometry_bar's malformed path returns a different key set from its "
        "normal path")
    assert solver_bar(broken)["signed_population"] is None
    assert geometry_bar(broken)["core_population"] is None
    assert geometry_bar(broken)["distinct_core"] is None
    assert solver_bar(broken)["partial"] is True
    assert geometry_bar(broken)["partial"] is True
    # every required key must be policed, not just `keys`. Iterated over a
    # LITERAL tuple: looping over REQUIRED_RECORD_KEYS itself would shrink
    # with it, so dropping a key from the constant would stay green.
    assert REQUIRED_RECORD_KEYS == ("candidate", "witness", "keys")
    for missing in ("candidate", "witness", "keys"):
        one = _spread(113)
        del one[3][missing]
        assert malformed(one) == [3], (missing, malformed(one))
        assert solver_bar(one)["verdict"] == "NO VERDICT", missing
        assert geometry_bar(one)["verdict"] == "NO VERDICT", missing
    many = _spread(113)
    for i in range(12):
        del many[i]["witness"]
    assert len(malformed(many)) == 12
    note = geometry_bar(many)["note"]
    assert "first ten indices" in note and str(list(range(10))) in note, note
    assert "10, 11]" not in note, "the note must print only the first ten"

    # --- the two floors are STRICT: exactly MIN_CORE_POPULATION verdicts --
    # `n < MIN_CORE_POPULATION` and `n <= MIN_CORE_POPULATION` differ at
    # exactly one value, so only a fixture sitting ON it can tell them apart.
    # Verified during planning: without these two cases the `<` -> `<=`
    # mutation survives the entire selftest.
    gfloor = ([_row([("c", i)], None, [i], faces=(i, i, i)) for i in range(23)]
              + [_row([("c", 1000 + i)], [i % 7], [1000 + i],
                      faces=(i % 5, 1, 2)) for i in range(90)])
    v = geometry_bar(gfloor)
    assert v["core_population"] == MIN_CORE_POPULATION, v["core_population"]
    assert v["verdict"] == "G1 LOCALISED", (
        "a core population of exactly MIN_CORE_POPULATION must still produce a "
        "verdict: the floor is `n < MIN_CORE_POPULATION`, not `<=`")

    sfloor = ([_row([("c", i)], None, [i], faces=(i, i, i)) for i in range(23)]
              + _spread(90, start=1000))
    v = solver_bar(sfloor)
    assert v["signed_population"] == MIN_CORE_POPULATION, v["signed_population"]
    assert v["verdict"] == "4 NEW TERRITORY", (
        "a signed population of exactly MIN_CORE_POPULATION must still reach "
        "row 4: the floor is `<`, not `<=`")
    assert v["partial"] is True

    # --- serialiser -------------------------------------------------------
    assert serialise(frozenset([(2, 1), (1, 2)])) == [[1, 2], [2, 1]]
    # order stability: a frozenset whose iteration order differs from sorted
    big = frozenset((i, 0) for i in range(50))
    assert serialise(big) == sorted([i, 0] for i in range(50)), (
        "a bare list() of a frozenset is hash-ordered and would differ "
        "run to run for identical content, making artifacts undiffable")
    assert serialise(_W(faces=(3, 1, 2)))["faces"] == [3, 1, 2]
    assert serialise(None) is None

    # --- the constants are the spec's ------------------------------------
    assert (FACES_LOCALISED, CORE_LOCALISED, CORE_BOUNDED,
            MIN_CORE_POPULATION, EXPECTED_REJECTIONS) == (10, 20, 40, 90, 113)
    assert ARM_A["rejections"] == EXPECTED_REJECTIONS, (
        "the guard's rejection count and the bars' expected population are "
        "the same number and must not drift apart -- the predecessor's two "
        "clause-size constants drifted exactly this way")

    # ARM_A's literals come from the committed A/B artifact. Compared only
    # with themselves they could drift from it silently, and the guard would
    # then check this run against a baseline nobody holds.
    ab = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                      "2026-09-27-core-in-loop", "ab.json")
    if os.path.exists(ab):
        import json as _j
        with open(ab) as fh:
            arm0 = _j.load(fh)["arms"][0]
        assert arm0["core_extraction"] is False, arm0["core_extraction"]
        for key in ("rejections", "layers_tried", "clause_vars_min",
                    "clause_vars_median", "clause_vars_max"):
            assert ARM_A[key] == arm0[key], (key, ARM_A[key], arm0[key])
        assert ARM_A["failure"] == arm0["failure"], (
            ARM_A["failure"], arm0["failure"])
        print(f"ARM_A pinned against {os.path.relpath(ab)}")
    else:
        print(f"WARNING: {ab} absent -- ARM_A's literals are UNPINNED")

    print("selftest OK")


# -------------------------------------------------------------------- main

# The same fixture the tests use, reached the way the predecessor evidence
# script reaches it (`../2026-09-28-witness-identity/identity.py:68`): a
# self-contained path relative to `mcp_harness`, NOT an import from the test
# package. An evidence script that imports from `tests/` silently acquires that
# package's conftest and sys.path assumptions, and is then only runnable under
# pytest's path setup rather than by the command printed in its own README.
RULE6 = os.path.join("..", "docs", "superpowers", "evidence",
                     "2026-09-08-vlm-tree-authoring", "data",
                     "rule6_serve.json")


def _subject_entry():
    import json as _json
    with open(RULE6) as fh:
        return next(e for e in _json.load(fh) if e["subject"] == "lizard")


def main(out_path):
    import json as _json
    import time as _time
    from box_pleat.compile import compile_tree

    e = _subject_entry()
    clauses, core_rows, rows = [], [], []
    t0 = _time.perf_counter()
    res = compile_tree(e["requested"], e["pairs"], dense=True,
                       assign_budget=500_000, core_extraction=False,
                       core_record=True, debug_clause_sizes=clauses,
                       debug_cores=core_rows, debug_witness_cores=rows)
    secs = round(_time.perf_counter() - t0, 1)

    rec = {
        "subject": "lizard",
        "arm": "A + core_record (diagnostic-only extraction)",
        "arm_a_expected": ARM_A,
        "assign_budget": 500_000,
        "stage_reached": res.stage_reached,
        "failure": repr(res.failure),
        "layer_verdict": repr(res.verdict),
        "layers_tried": res.layers_tried,
        "rejections": len(clauses),
        "records": len(rows),
        "secs": secs,
        # The full population, so a successor can guard it EXACTLY -- the
        # weakness this guard inherits is that arm A published only a
        # min/median/max (spec 5.6).
        "clause_sizes": sorted(clauses),
        "core_rows": [list(r) for r in core_rows],
    }

    refusals = [r["core_error"] for r in rows if r["core_error"] is not None]
    rec["core_refusals"] = len(refusals)
    rec["core_refusal_messages"] = sorted(set(refusals))
    if refusals:
        print(f"!!! CORE EXTRACTION REFUSED on {len(refusals)} of "
              f"{len(rows)} rejections. The geometry bar's population is "
              f"{len(rows) - len(refusals)}, not {len(rows)}.")
        for m in sorted(set(refusals)):
            print(f"!!!   {m}")

    passed, bad = guard(rec["rejections"], rec["layers_tried"],
                        rec["failure"], clauses, rec["records"])
    rec["guard_passed"] = passed
    rec["guard_mismatches"] = bad
    print(f"stage={rec['stage_reached']} failure={rec['failure']} "
          f"rejections={rec['rejections']} records={rec['records']} "
          f"secs={secs}")
    if not passed:
        rec["solver_bar"] = {"verdict": "GUARD FAILED"}
        rec["geometry_bar"] = {"verdict": "GUARD FAILED"}
        print("GUARD FAILED -- NO VERDICT from either bar:")
        for b in bad:
            print(f"  {b}")
    else:
        rec["solver_bar"] = solver_bar(rows)
        rec["geometry_bar"] = geometry_bar(rows)
        print(f"SOLVER BAR: {rec['solver_bar']['verdict']}")
        print(f"GEOMETRY BAR: {rec['geometry_bar']['verdict']}")
        for b in (rec["solver_bar"], rec["geometry_bar"]):
            if b.get("note"):
                print(f"  note: {b['note']}")

    rec["distinct"] = {lv: distinct(rows, lv) for lv in LEVELS}
    rec["populations"] = {lv: len(population(rows, lv)) for lv in LEVELS}
    rec["repeats"] = {lv: {str(serialise(v)): idx
                           for v, idx in repeats(rows, lv).items()}
                      for lv in LEVELS}
    rec["multiplicity_histogram"] = {
        lv: _histogram(multiplicity(rows, lv)) for lv in LEVELS}
    rec["chao1_reference"] = {lv: chao1(multiplicity(rows, lv))
                              for lv in LEVELS}
    rec["top5"] = {lv: _top5(multiplicity(rows, lv), len(rows))
                   for lv in LEVELS}
    rec["overlaps"] = {lv: overlaps(rows, lv)
                       for lv in ("candidate", "core", "signed", "keys",
                                  "core_keys")}
    rec["rejection_records"] = [
        {lv: serialise(value_at(r, lv)) for lv in LEVELS}
        | {"core_error": r["core_error"]} for r in rows]

    print("distinct: " + "  ".join(
        f"{lv}={rec['distinct'][lv]}/{rec['populations'][lv]}"
        for lv in LEVELS))
    for lv in LEVELS:
        for v, idx in rec["repeats"][lv].items():
            print(f"REPEAT at {lv}: rows {idx} share {v[:120]}")

    with open(out_path, "w") as fh:
        _json.dump(rec, fh, indent=1, sort_keys=True)
    print(f"wrote {out_path}")


def _histogram(mult: dict) -> dict:
    """multiplicity -> how many values occur that many times. f1 is key "1"."""
    out = {}
    for c in mult.values():
        out[str(c)] = out.get(str(c), 0) + 1
    return out


def _top5(mult: dict, total: int) -> dict:
    """The five most frequent values and the share of `total` they cover."""
    top = sorted(mult.items(), key=lambda kv: -kv[1])[:5]
    covered = sum(c for _, c in top)
    return {"counts": [c for _, c in top],
            "values": [serialise(v)[:40] if isinstance(serialise(v), list)
                       else serialise(v) for v, _ in top],
            "covered": covered,
            "share_of_total": (None if not total
                               else round(covered / total, 4))}


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        raise SystemExit(0)
    if len(sys.argv) != 2:
        raise SystemExit(
            "usage: identity113.py <out.json> | identity113.py --selftest")
    main(sys.argv[1])
