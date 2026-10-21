"""Can `pleat_grid.fill` inject anything at all? A headroom census.

Spec: `../../specs/2026-09-28-pleat-grid-headroom-design.md`. **Read its §9
first** -- it corrects the coverage figures this slice was originally built on.

Gap 1's component 1 (`pleat_grid.py`, COrigami F.1.1 step 5) is the one piece of
the dense-pleats architecture never built, and it is the leading untested
hypothesis for why dense layer-ordering does not converge. This script does not
build it. It measures whether it CAN ACT, and a pre-registered bar (§6) decides
whether the build is worth a slice.

WHY A CENSUS IS EXACT AND NOT AN ESTIMATE (spec §4). Component 1's contract
forbids invented elevations: a segment is injected only where its endpoints'
elevations determine it uniquely. That predicate requires BOTH endpoints to
already be known, so injecting one segment makes no new point known and cannot
unlock another -- ONE PASS IS THE FIXPOINT. And a point's elevation is
single-valued, so no injection can invalidate another -- the result is
ORDER-INDEPENDENT. So this census is not an approximation of what `fill` would
inject; it IS what `fill` would inject, which is what makes a small number
decisive rather than merely suggestive. Both properties are tested in
`_selftest`, not merely argued here.

WHY `slope` IS THE HEADLINE (spec §3). A contour is a level line carrying ONE
elevation (`contours.py`: segments "each carrying an elevation"; within a face
"the elevation is linear and its contours are parallel"). A segment whose
endpoints sit at DIFFERENT elevations is not a level line anywhere, at any
elevation. `fill` does not decline to invent a value for it -- there is nothing
there to find. If the gap is mostly `slope`, COrigami's fully contiguous grid is
UNREACHABLE from an elevation field, which is an architectural consequence of
consciously rejecting F.1.1 steps 1-4, not a defect.

WHY `hinge` IS ITS OWN BUCKET (spec §10). `contours.py:233-234` refuses a
contour on a hinge (`len(_seg_owners(k, owner, N)) > 1`), so a hinge segment is
STRUCTURALLY INELIGIBLE for injection whatever its endpoints say -- COrigami's
step 5 asks for "structurally **valid** non-intersecting segments", and a
hinge segment fails that validity test before elevation enters into it at all.
It is a separate bucket rather than folded into `slope`, because `slope` must
keep meaning exactly "endpoints known but unequal"; a hinge segment can have
endpoints that are EQUAL, so merging it into `slope` would blur that meaning.
And the choice is conservative: hinge segments stay in the gap denominator
(`total - occupied`, spec §6), so carving this bucket out can only LOWER the
fraction that selects BUILD, never inflate it.

WHY HEADROOM MIGHT BE NON-ZERO. Contours stop on the paper edge or on an
existing contour of the same elevation, a contour on a hinge is a refusal, and
each (point, direction) is traced at most once. So a level line can terminate
early and leave its continuation unoccupied while both endpoints stay known.
Whether that happens often is the empirical question.

WHAT THIS CANNOT SAY (spec §7). Nothing here tests whether higher coverage makes
dense layer-ordering converge. A BUILD verdict licenses building `fill`; it does
not predict convergence.

TWO GUARDS, AND THEY REFUSE RATHER THAN WARN (spec §5). Both realistic failure
modes produce a confident wrong number rather than an error. (1) A reimplemented
sorted-endpoint key would make every lookup miss and read `occupied` as 0 --
a spectacular false positive for BUILD -- so `contours._key` and
`contours.is_boundary_seg` are REUSED, and the enumeration is proved to cover
the field the subject holds. (2) The occupied count is calibrated against two
figures recorded by slices that had no coverage number in view. If either guard
fails, NO bucket and NO verdict may be claimed, in either direction.

Run from mcp_harness:
  PYTHONPATH=. ../.venv/bin/python3 -u \\
      ../docs/superpowers/evidence/2026-09-28-pleat-grid-headroom/headroom.py \\
      --selftest
  PYTHONPATH=. ../.venv/bin/python3 -u \\
      ../docs/superpowers/evidence/2026-09-28-pleat-grid-headroom/headroom.py \\
      ../docs/superpowers/evidence/2026-09-28-pleat-grid-headroom/headroom.json
"""
import datetime
import json
import os
import signal
import subprocess
import sys
import time
from fractions import Fraction

from box_pleat import contours as C
from box_pleat.compile import compile_tree

RULE6 = os.path.join("..", "docs", "superpowers", "evidence",
                     "2026-09-08-vlm-tree-authoring", "data", "rule6_serve.json")

SUBJECTS = ("starfish", "lizard", "frog", "horse",
            "bird", "guinea_pig", "octopus", "dog")

BUCKETS = ("occupied", "level_injectable", "slope", "unreached", "hinge")

# Spec §5.2. COUNTS, not percentages: a count has no denominator to disagree
# about, and both were recorded by slices that had no coverage figure in view.
# lizard 4,488 = ../2026-09-27-pleat-filter/README.md's dense-candidate count.
# bird 11,534  = 2026-09-24-dense-pleats-design.md §2's dense free-variable figure.
OCCUPIED_EXPECTED = {"lizard": 4488, "bird": 11534}

# Spec §5 / §8.3.
CAP_SECS = 300

# Spec §6 thresholds, as fractions OF THE GAP (total - occupied). Fractions of
# the gap are self-normalising, so §9's correction to the gap's size does not
# move them.
BUILD_AT = 0.25
NO_BUILD_BELOW = 0.05


# --------------------------------------------------------------------------
# pure classifier
# --------------------------------------------------------------------------
def half_grid_segments(N: int) -> set:
    """Every in-paper unit segment on the integer half-grid [0, 2N].

    A unit segment steps by 1 in exactly one axis (verified 2026-09-28: lizard's
    4,488 contour segments have deltas {(1,0), (0,1)} and nothing else).
    Segments lying ALONG the paper boundary are excluded via production's own
    `contours.is_boundary_seg`, because `contours.py` never registers there
    ("nothing is ever registered on the paper boundary"); measured 2026-09-28,
    zero contour segments are boundary segments on starfish, lizard or bird.
    Keys come from `contours._key`, never a local reimplementation -- see §5.1.
    """
    L = 2 * N
    out = set()
    for x in range(L + 1):
        for y in range(L + 1):
            if x + 1 <= L:
                out.add(C._key((x, y), (x + 1, y)))
            if y + 1 <= L:
                out.add(C._key((x, y), (x, y + 1)))
    return {k for k in out if not C.is_boundary_seg(k, N)}


def known_elevations(contours: dict, boundary_elev: dict) -> dict:
    """point -> elevation, from every source the field records.

    A contour segment's two endpoints each carry the segment's elevation (a
    contour is a level line), and `layout.boundary_elev` carries the paper-edge
    points AND the level-stretch points (`contours.py:593-596` also writes
    those there; a level stretch need not lie on the paper edge). Where both
    sources name a point they agree, because the field is single-valued --
    `contours.py` raises ContourFail("collision") otherwise -- so the merge
    order cannot matter.
    """
    known: dict = dict(boundary_elev)
    for (a, b), elev in contours.items():
        known[a] = elev
        known[b] = elev
    return known


def classify(N: int, contours: dict, boundary_elev: dict, owner: dict,
            enumerated: set) -> dict:
    """bucket name -> set of SegKey. The five buckets partition the total.

    `level_injectable` is exactly component 1's contract: both endpoints known
    AND equal AND not a hinge -- `contours.py:233-234` refuses a contour on a
    hinge (`ContourFail("contour_on_hinge")`) because a segment whose adjacent
    cells have different owners can never legitimately carry a contour, so a
    would-be-injectable segment there is structurally ineligible, not merely
    unclaimed. `hinge` holds exactly those segments -- both endpoints known and
    equal, but rejected on owner grounds -- via production's own
    `contours._seg_owners`, never a local reimplementation. `slope` is
    endpoints known but UNEQUAL -- structurally not a level segment at any
    elevation (§3), never a limitation of `fill`, and its meaning is
    unaffected by the hinge check (a slope segment was never eligible for
    injection regardless of ownership). `enumerated` is the segment set to
    classify -- pass `half_grid_segments(N)`, computed once by the caller and
    shared with `guards` so the two cannot disagree about the denominator.
    """
    known = known_elevations(contours, boundary_elev)
    out = {b: set() for b in BUCKETS}
    for key in enumerated:
        if key in contours:
            out["occupied"].add(key)
            continue
        a, b = key
        ea, eb = known.get(a), known.get(b)
        if ea is None or eb is None:
            out["unreached"].add(key)
        elif ea == eb:
            if len(C._seg_owners(key, owner, N)) > 1:
                out["hinge"].add(key)
            else:
                out["level_injectable"].add(key)
        else:
            out["slope"].add(key)
    return out


def components(segs) -> int:
    """Connected components over half-grid points, via union-find.

    Coverage is a count; COrigami asks for coverage AND a fully contiguous
    grid, so this is the second and independent reading (§3). Isolated points
    are not counted -- only points touched by a segment.
    """
    parent: dict = {}

    def find(p):
        parent.setdefault(p, p)
        while parent[p] != p:
            parent[p] = parent[parent[p]]
            p = parent[p]
        return p

    for a, b in segs:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    # `list(parent)` -- not `parent` -- because `find`'s path-halving rewrites
    # `parent`'s VALUES as this comprehension runs; safe today (no key is
    # added or removed), but iterating the dict directly is one edit away
    # from `RuntimeError: dictionary changed size during iteration`.
    return len({find(p) for p in list(parent)})


# --------------------------------------------------------------------------
# guards (spec §5) -- they refuse, they do not warn
# --------------------------------------------------------------------------
def guards(subject: str, N: int, contours: dict, buckets: dict,
          enumerated: set) -> tuple:
    """Returns (passed, [failure, ...]) for spec §5.1 and §5.2.

    `enumerated` is the same `half_grid_segments(N)` set `classify` was given
    -- passed in rather than recomputed here, so there is exactly one
    enumeration per subject and no way for the two to disagree about the
    denominator.
    """
    bad = []
    stray = set(contours) - enumerated
    if stray:
        bad.append(
            f"§5.1 enumeration incomplete: {len(stray)} contour keys are not in "
            f"half_grid_segments({N}); e.g. {sorted(stray)[:3]}")
    want = OCCUPIED_EXPECTED.get(subject)
    got = len(buckets["occupied"])
    if want is not None and got != want:
        bad.append(f"§5.2 occupied {got} != {want} for {subject}")
    return not bad, bad


def guard_verdict(rows: list) -> tuple:
    """Whether ANY compiled subject's guards failed -- not only lizard's.

    The module docstring states spec §5's rule without a subject qualifier:
    "If either guard fails, NO bucket and NO verdict may be claimed, in
    either direction." A §5.2 count mismatch on `bird` (the other calibrated
    subject) or a §5.1 stray-key failure on any subject is evidence the
    COUNTING METHOD is wrong, which would invalidate lizard's row too, so the
    verdict must be suppressed on any such failure, not only lizard's own.

    Returns `(ok, failing)` where `failing` is `[(subject, [message, ...]),
    ...]` for every row with `outcome == "ok"` and `guards_passed` False. A
    row that never reached "ok" (STOP, TIMEOUT, missing from the fixture) has
    no guard verdict to trust and is simply not evaluated here -- it is
    neither a pass nor a failure. Pure and independent of compiling anything,
    so it is testable on synthetic rows without running `main`.

    An `outcome == "ok"` row with NO `guards_passed` key at all is treated as
    a failure, not a pass: today `main` always sets the flag on every "ok"
    row, so this is unreachable in the current run, but "absent means fine"
    is the wrong default for a function whose entire job is to refuse. A
    future producer of rows (a fixture, a replay, a partial re-run) that
    forgets to set the flag must not be read as a silent PASS.
    """
    failing = []
    for r in rows:
        if r.get("outcome") != "ok":
            continue
        if "guards_passed" not in r:
            failing.append(
                (r["subject"], [f"guards_passed absent for {r['subject']}"]))
        elif not r["guards_passed"]:
            failing.append((r["subject"], r["guard_failures"]))
    return (not failing), failing


# --------------------------------------------------------------------------
# the bar (spec §6) -- evaluated on lizard only
# --------------------------------------------------------------------------
def verdict(row: dict) -> tuple:
    """Spec §6, on one subject's row. Returns (verdict, figures).

    `gap` is total - occupied. The injectable fraction and coverage_after are
    THE SAME QUANTITY REARRANGED (the buckets partition the total), so both are
    reported and neither corroborates the other.
    """
    gap = row["total"] - row["occupied"]
    frac = (row["level_injectable"] / gap) if gap else 0.0
    fell = row["components_after"] < row["components_before"]
    figures = {"gap": gap, "injectable_fraction_of_gap": round(frac, 4),
               "components_fell": fell}
    if frac >= BUILD_AT and fell:
        return "BUILD", figures
    if frac >= BUILD_AT:
        return "BUILD NARROWED", figures
    if frac < NO_BUILD_BELOW:
        return "DO NOT BUILD", figures
    return "REPORT AND DECIDE", figures


def serialise(value):
    """Fractions -> strings, tuples/lists -> lists (recursively), sets ->
    sorted lists.

    Sorting is what makes the artifact diffable: set iteration order is not
    stable across runs, so an unsorted dump would differ run to run for reasons
    that are not findings.

    The `list` case matters beyond symmetry with `tuple`: every per-subject
    field in `main` lives in `rec["rows"]`, which is a `list`. Before this
    case existed, `serialise` returned a bare list's CONTENTS unrecursed (by
    identity), so a `Fraction` sitting inside a dict inside `rec["rows"]`
    would reach `json.dump` unconverted and blow up the whole run -- see the
    `serialise` cases in `_selftest` for the reproduction and the fix.
    """
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, (set, frozenset)):
        return sorted(serialise(v) for v in value)
    if isinstance(value, (tuple, list)):
        return [serialise(v) for v in value]
    if isinstance(value, dict):
        return {str(k): serialise(v) for k, v in value.items()}
    return value


# --------------------------------------------------------------------------
# selftest
# --------------------------------------------------------------------------
class _Timeout(Exception):
    pass


def _alarm(signum, frame):
    raise _Timeout()


def _selftest():
    """The classifier, the two §4 properties, the guards and the bar.

    Project memory records two throwaway probes that drove wrong conclusions in
    one session, one of which printed its verdict unconditionally. This runs in
    milliseconds and must pass before any subject is compiled.
    """
    # N=2 -> L=4. Non-boundary segments only.
    N = 2
    segs = half_grid_segments(N)
    assert all(not C.is_boundary_seg(k, N) for k in segs)
    assert all(k == C._key(*k) for k in segs), "keys are not canonical"
    # every key steps by exactly 1 in exactly one axis
    for (a, b) in segs:
        d = (b[0] - a[0], b[1] - a[1])
        assert d in ((1, 0), (0, 1)), d

    e0, e1 = Fraction(0), Fraction(1)

    # A single-owner map for every N=2 cell: no two adjacent cells ever
    # differ, so no segment used below is ever a hinge unless a test
    # deliberately overrides a cell (see the hinge-exclusion block).
    no_hinge_owner = {(c, r): ("poly", 0) for c in range(N) for r in range(N)}

    # --- the five buckets, hand-counted -------------------------------------
    # occupied: (1,1)-(2,1). Its endpoints become known at elevation 0.
    # (2,1)-(3,1) then has both endpoints known only if (3,1) is known too.
    contours = {C._key((1, 1), (2, 1)): e0}
    boundary = {(3, 1): e0, (1, 3): e1, (2, 3): e0}
    b = classify(N, contours, boundary, no_hinge_owner, segs)
    assert sum(len(v) for v in b.values()) == len(segs), "buckets do not partition"
    assert b["occupied"] == {C._key((1, 1), (2, 1))}
    # (2,1) known at 0 (contour endpoint), (3,1) known at 0 (boundary) -> level
    assert C._key((2, 1), (3, 1)) in b["level_injectable"]
    # (1,3) known at 1, (2,3) known at 0 -> unequal -> slope, NOT injectable
    assert C._key((1, 3), (2, 3)) in b["slope"]
    assert C._key((1, 3), (2, 3)) not in b["level_injectable"]
    # a segment with an unknown endpoint -> unreached
    assert C._key((1, 1), (1, 2)) in b["unreached"]
    # a hinge-free run has nothing in the fifth bucket
    assert b["hinge"] == set()

    # --- §4 exactness: ONE PASS IS THE FIXPOINT ---------------------------
    inj = b["level_injectable"]
    assert inj, "selftest fixture injects nothing -- it cannot test the fixpoint"
    grown = dict(contours)
    known = known_elevations(contours, boundary)
    for k in inj:
        grown[k] = known[k[0]]
    again = classify(N, grown, boundary, no_hinge_owner, segs)
    assert again["level_injectable"] == set(), (
        "one pass is NOT the fixpoint -- spec §4's exactness argument is false")

    # --- §4 exactness: ORDER-INDEPENDENCE, via a real iterative filler -----
    # The single-element `inj` above cannot test order-independence: reversing
    # a length-1 sequence gives the identical sequence, and `known` is fixed
    # before both loops run, so `f1 == f2` above held for ANY implementation
    # (confirmed even with a garbage elevation table). This fixture has TWO
    # level-injectable segments sharing point (3,1), so ascending and
    # descending processing orders are genuinely different sequences, and a
    # filler that (say) forgets a point once it has written through it has
    # somewhere to diverge.
    contours2 = {C._key((1, 1), (2, 1)): e0}
    boundary2 = {(3, 1): e0, (4, 1): e0, (1, 3): e1, (2, 3): e0}
    b2 = classify(N, contours2, boundary2, no_hinge_owner, segs)
    inj2 = b2["level_injectable"]
    assert len(inj2) >= 2, "fixture does not have 2+ injectable segments"
    assert sorted(inj2) != sorted(inj2, reverse=True), (
        "fixture's two orders are not genuinely different sequences -- "
        "this cannot test order-independence")

    def _iterative_fill(order):
        """The iterative filler §4 argues is unnecessary: inject one segment
        at a time, RE-DERIVING known_elevations from the growing field after
        each injection (never from a fixed snapshot), in `order`."""
        grown = dict(contours2)
        for k in order:
            known_now = known_elevations(grown, boundary2)
            a, bb = k
            ea, eb = known_now.get(a), known_now.get(bb)
            if ea is not None and eb is not None and ea == eb:
                grown[k] = ea
        return grown

    g1 = _iterative_fill(sorted(inj2))
    g2 = _iterative_fill(sorted(inj2, reverse=True))
    # This assertion is a theorem-backed TAUTOLOGY, not empirical support:
    # order-independence follows from the field being single-valued (every
    # point has exactly one elevation, enforced by contours.py's own
    # ContourFail("collision")), so no defect in THIS MODULE can make it
    # fail -- reversing the injection order cannot change a value that is
    # determined once its endpoints are known. It is kept anyway because it
    # still documents the property and would catch a future refactor that
    # made injection stateful (e.g. an order-sensitive cache). The two guards
    # immediately above (`len(inj2) >= 2` and `sorted(inj2) != sorted(inj2,
    # reverse=True)`) are what carry this test's actual power: they are what
    # caught 3 of 4 deliberately injected `known_elevations` defects (see
    # spec §4 / Finding 2), not this assertion.
    assert g1 == g2, "iterative filler is order-DEPENDENT -- spec §4 is false"
    assert (classify(N, g1, boundary2, no_hinge_owner, segs) ==
            classify(N, g2, boundary2, no_hinge_owner, segs)), (
        "the two orders classify the resulting field differently -- "
        "order-dependent")

    # --- Important 3: hinge exclusion --------------------------------------
    # (2,2)-(2,3) sits on X=2 (even) at row 1 -- a boundary between columns 0
    # and 1 -- so it touches cells (0,1) and (1,1). contours.py refuses a
    # contour whose adjacent cells have different owners
    # (`ContourFail("contour_on_hinge")`), so a segment there must never be
    # `level_injectable` even when both its endpoints are known and equal.
    hinge_owner = dict(no_hinge_owner)
    hinge_owner[(1, 1)] = ("poly", 1)          # split from (0,1)'s owner
    hinge_key = C._key((2, 2), (2, 3))
    hinge_boundary = {(2, 2): e0, (2, 3): e0}
    hb = classify(N, {}, hinge_boundary, hinge_owner, segs)
    assert hinge_key in hb["hinge"], hb["hinge"]
    assert hinge_key not in hb["level_injectable"]
    assert sum(len(v) for v in hb.values()) == len(segs), "buckets do not partition"
    # the identical segment, same owners MINUS the split, IS injectable
    hb_flat = classify(N, {}, hinge_boundary, no_hinge_owner, segs)
    assert hinge_key in hb_flat["level_injectable"]
    assert hinge_key not in hb_flat["hinge"]

    # --- components -------------------------------------------------------
    assert components(set()) == 0
    assert components({C._key((0, 0), (0, 1))}) == 1
    # two disjoint segments -> two components
    assert components({C._key((0, 0), (0, 1)), C._key((3, 3), (3, 4))}) == 2
    # a path of two segments sharing a point -> one component
    assert components({C._key((0, 0), (0, 1)), C._key((0, 1), (0, 2))}) == 1

    # --- guards -----------------------------------------------------------
    ok, bad = guards("lizard", N, contours, {"occupied": set(range(4488))}, segs)
    assert ok, bad
    ok, bad = guards("lizard", N, contours, {"occupied": set(range(4487))}, segs)
    assert not ok and "§5.2" in bad[0], bad
    ok, bad = guards("bird", N, contours, {"occupied": set(range(11534))}, segs)
    assert ok, bad
    # a subject with no expectation is not guarded on the count
    ok, bad = guards("frog", N, contours, {"occupied": set()}, segs)
    assert ok, bad
    # §5.1: a key outside the enumeration must refuse
    outside = {C._key((0, 0), (0, 1)): e0}          # a boundary segment
    ok, bad = guards("frog", N, outside, {"occupied": set()}, segs)
    assert not ok and "§5.1" in bad[0], bad

    # --- Important 2: guard_verdict suppresses on ANY subject, not only
    # lizard -------------------------------------------------------------
    ok, failing = guard_verdict([
        {"subject": "lizard", "outcome": "ok", "guards_passed": True,
         "guard_failures": []},
        {"subject": "bird", "outcome": "ok", "guards_passed": True,
         "guard_failures": []},
    ])
    assert ok and failing == [], failing
    # a non-lizard (bird) guard failure must suppress the verdict
    bird_bad = ["§5.2 occupied 1 != 11534 for bird"]
    ok, failing = guard_verdict([
        {"subject": "lizard", "outcome": "ok", "guards_passed": True,
         "guard_failures": []},
        {"subject": "bird", "outcome": "ok", "guards_passed": False,
         "guard_failures": bird_bad},
    ])
    assert not ok and failing == [("bird", bird_bad)], failing
    # a subject that never reached "ok" (STOP/TIMEOUT) is neither a pass nor
    # a failure -- it must not be silently counted as passing
    ok, failing = guard_verdict([
        {"subject": "lizard", "outcome": "ok", "guards_passed": True,
         "guard_failures": []},
        {"subject": "frog", "outcome": "stopped at pack: PackFail(...)"},
    ])
    assert ok and failing == [], failing
    # Finding 4: an "ok" row with NO guards_passed key at all must be treated
    # as a failure, not defaulted to a silent pass.
    ok, failing = guard_verdict([
        {"subject": "lizard", "outcome": "ok", "guards_passed": True,
         "guard_failures": []},
        {"subject": "horse", "outcome": "ok"},          # guards_passed absent
    ])
    assert not ok, failing
    assert failing == [("horse", ["guards_passed absent for horse"])], failing

    # --- the bar, all four rows -------------------------------------------
    def row(total, occ, inj_n, before, after):
        return {"total": total, "occupied": occ, "level_injectable": inj_n,
                "components_before": before, "components_after": after}
    assert verdict(row(100, 50, 25, 9, 4))[0] == "BUILD"
    assert verdict(row(100, 50, 25, 9, 9))[0] == "BUILD NARROWED"
    assert verdict(row(100, 50, 1, 9, 9))[0] == "DO NOT BUILD"
    assert verdict(row(100, 50, 7, 9, 9))[0] == "REPORT AND DECIDE"
    # THE BOUNDARIES, in integers so they are exact. gap = 100 in both.
    # BUILD_AT is >=, so exactly 25% builds.
    assert verdict(row(200, 100, 25, 9, 4))[0] == "BUILD"
    assert verdict(row(200, 100, 24, 9, 4))[0] == "REPORT AND DECIDE"   # 24%
    # NO_BUILD_BELOW is a strict <, so exactly 5% is NOT "DO NOT BUILD".
    assert verdict(row(200, 100, 5, 9, 9))[0] == "REPORT AND DECIDE"
    assert verdict(row(200, 100, 4, 9, 9))[0] == "DO NOT BUILD"         # 4%
    # a zero gap cannot claim BUILD
    assert verdict(row(100, 100, 0, 1, 1))[0] == "DO NOT BUILD"

    # --- serialise --------------------------------------------------------
    assert serialise(Fraction(1, 2)) == "1/2"
    assert serialise({C._key((1, 1), (2, 1))}) == [[[1, 1], [2, 1]]]
    json.dumps(serialise({"a": {Fraction(3, 4)}, "b": (1, 2)}))
    # Finding 1: a Fraction inside a list inside a dict -- the exact shape of
    # `rec["rows"]` (a list of per-subject dicts) -- must be reached. Before
    # the `list` case existed, `serialise` returned the "rows"-style list by
    # identity, unrecursed, and this call raised TypeError from json.dumps.
    nested = serialise({"rows": [{"odd": Fraction(1, 2)}]})
    assert nested == {"rows": [{"odd": "1/2"}]}, nested
    json.dumps(nested)          # must not raise

    print("selftest OK: enumeration, 5 buckets (incl. hinge), fixpoint, "
          "order-independence (iterative filler, 2 orders), hinge exclusion, "
          "components (4), guards (5), guard_verdict (4), bar (9 cases), "
          "serialise (incl. list-in-dict)")


# --------------------------------------------------------------------------
# the run
# --------------------------------------------------------------------------
def _commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception as exc:                    # noqa: BLE001 -- metadata only
        return f"unavailable: {exc}"


def main(out):
    with open(RULE6) as fh:
        data = json.load(fh)

    # Spec §8.5: run metadata IN THE ARTIFACT. The witness-identity spec's §10
    # recorded this deferral and named the next evidence script in this
    # subproject as the place to close it. This is that script.
    rec = {
        "measured_utc": datetime.datetime.now(datetime.UTC).isoformat(
            timespec="seconds"),
        "commit": _commit(),
        "cap_secs": CAP_SECS,
        "occupied_expected": OCCUPIED_EXPECTED,
        "buckets": list(BUCKETS),
        "rows": [],
    }

    def flush():
        # `serialise` at flush time (its only caller used to be `_selftest`)
        # so the artifact is future-proofed against any field that later
        # carries a Fraction, tuple or set -- nothing currently written needs
        # it, but `json.dump` would hard-fail the whole run the day one does.
        with open(out, "w") as fh:
            json.dump(serialise(rec), fh, indent=1)

    flush()

    for s in SUBJECTS:
        entry = next((e for e in data if e["subject"] == s), None)
        if entry is None:
            rec["rows"].append({"subject": s, "outcome": "not in rule6_serve"})
            flush()
            print(f"{s}: NOT IN FIXTURE", flush=True)
            continue
        row = {"subject": s}
        t0 = time.time()
        old = signal.signal(signal.SIGALRM, _alarm)
        signal.alarm(CAP_SECS)
        try:
            res = compile_tree(entry["requested"], entry["pairs"])
        except _Timeout:
            row["outcome"] = f"sparse compile exceeded {CAP_SECS}s"
            rec["rows"].append(row)
            flush()
            print(f"{s}: TIMEOUT", flush=True)
            continue
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old)
        row["compile_secs"] = round(time.time() - t0, 1)
        # Minor 4: gate on the data the census actually needs -- `contours`
        # populated and `layout` present -- not on `stage_reached == "emit"`.
        # `compile_tree` sets `res.layout` at the pack stage and
        # `res.contours` at the contours stage, both well before "emit", so
        # a subject that stops at "assign", "layers" or later still has
        # everything this script reads. `stage_reached` is recorded either
        # way so a reader can see which subjects did not reach "emit".
        row["stage_reached"] = res.stage_reached
        if not res.contours or res.layout is None:
            row["outcome"] = f"stopped at {res.stage_reached}: {res.failure!r}"
            rec["rows"].append(row)
            flush()
            print(f"{s}: STOP {res.stage_reached}", flush=True)
            continue

        N = res.layout.N
        owner = res.layout.cell_owner()
        enumerated = half_grid_segments(N)
        buckets = classify(N, res.contours, res.layout.boundary_elev, owner,
                          enumerated)
        passed, bad = guards(s, N, res.contours, buckets, enumerated)
        total = sum(len(v) for v in buckets.values())
        occ = buckets["occupied"]
        inj = buckets["level_injectable"]
        row.update({
            "outcome": "ok",
            "N": N,
            "total": total,
            **{b: len(buckets[b]) for b in BUCKETS},
            "coverage_pct": round(100 * len(occ) / total, 1) if total else None,
            "coverage_after_pct": (round(100 * (len(occ) + len(inj)) / total, 1)
                                   if total else None),
            "components_before": components(occ),
            "components_after": components(occ | inj),
            "guards_passed": passed,
            "guard_failures": bad,
        })
        rec["rows"].append(row)
        flush()
        print(f"{s}: N={N} total={total} occupied={len(occ)} "
              f"injectable={len(inj)} slope={len(buckets['slope'])} "
              f"unreached={len(buckets['unreached'])} "
              f"hinge={len(buckets['hinge'])} "
              f"cov={row['coverage_pct']}% -> {row['coverage_after_pct']}% "
              f"comp {row['components_before']}->{row['components_after']} "
              f"guards={'PASS' if passed else 'FAIL'}", flush=True)
        for m in bad:
            print(f"    {m}", flush=True)

    # --- the verdict, on lizard, and only if EVERY subject's guards passed -
    liz = next((r for r in rec["rows"]
                if r["subject"] == "lizard" and r.get("outcome") == "ok"), None)
    print()
    if liz is None:
        rec["verdict"] = "NO VERDICT: lizard produced no row"
        flush()
        print("NO VERDICT: lizard produced no row, so §6 cannot be evaluated.")
        return

    # Important 2: the module docstring's rule ("If either guard fails, NO
    # bucket and NO verdict may be claimed, in either direction") names no
    # subject qualifier, so it is evaluated across ALL rows, not only
    # lizard's -- a §5.2 mismatch on `bird` or a §5.1 failure anywhere is
    # evidence the counting method itself is wrong, which would invalidate
    # lizard's row too.
    ok, failing = guard_verdict(rec["rows"])
    if not ok:
        rec["verdict"] = "GUARD FAILED"
        rec["verdict_figures"] = None
        flush()
        print("GUARD FAILED (spec §5): NO bucket and NO verdict may be claimed, "
              "in either direction.")
        for subj, msgs in failing:
            for m in msgs:
                print(f"  [{subj}] {m}")
        return

    v, figures = verdict(liz)
    rec["verdict"] = v
    rec["verdict_figures"] = figures
    flush()
    print(f"VERDICT (lizard): {v}")
    print(f"  gap {figures['gap']}, injectable "
          f"{100 * figures['injectable_fraction_of_gap']:.1f}% of it, "
          f"components fell: {figures['components_fell']}")
    if v == "BUILD":
        print("  Real headroom AND it buys contiguity. Component 1 is worth a "
              "slice. This does NOT predict convergence (spec §7).")
    elif v == "BUILD NARROWED":
        print("  Coverage without contiguity. Component 1's spec must state "
              "which property it claims, because the hypothesis rests on "
              "contiguity. Does NOT predict convergence (spec §7).")
    elif v == "DO NOT BUILD":
        print("  A no-op, like the pleat filter. The slope/unreached split is "
              "the finding; if slope dominates, COrigami's contiguous grid is "
              "unreachable from an elevation field (spec §3).")
    else:
        print("  Between the thresholds. §6 row 4 pre-committed to having NO "
              "rule here, so this is decided on the reported figures, not by a "
              "threshold invented after the fact.")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        main(sys.argv[1])
