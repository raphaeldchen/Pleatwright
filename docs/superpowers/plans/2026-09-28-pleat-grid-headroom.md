# Pleat-Grid Headroom Census Implementation Plan

> **Note added 2026-09-28, after this plan was written and executed.** The
> spec's §10 added a fifth bucket, `hinge`, and §9 corrected the coverage
> figures this plan was drafted against. The plan's embedded code below and its
> "4 buckets" language are **superseded by the committed `headroom.py`**, which
> has five buckets and reuses `contours._seg_owners` to exclude hinge segments.
> This plan is left as written, as a historical record of what was planned,
> **except** that Task 1 Step 3's expected self-test output has been corrected
> below to match the script that was actually committed and run; every other
> mention of "4 buckets" (roughly eleven of them) and the embedded code are
> left unchanged.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure whether `pleat_grid.fill` (gap 1's component 1, COrigami F.1.1 step 5) can inject anything at all, so the decision to build it rests on a number rather than on an assumption.

**Architecture:** A single read-only evidence script. Per subject it runs a sparse `compile_tree`, reads `res.contours` and `layout.boundary_elev`, and partitions every in-paper half-grid unit segment into four buckets — `occupied`, `level_injectable`, `slope`, `unreached`. Two preconditions gate any verdict. Pure functions plus a `--selftest` mode; **no production code changes at all.**

**Tech Stack:** Python 3.14, the existing `mcp_harness/box_pleat/` package. No new dependencies. No pytest file (nothing in production changes).

**Spec:** `docs/superpowers/specs/2026-09-28-pleat-grid-headroom-design.md`. Every `§` reference below is to that file. **Read its §9 first** — it corrects the figures the slice was originally built on.

## Global Constraints

* **Python is `../.venv/bin/python3`, run from `mcp_harness`.** `mcp_harness/conftest.py`'s autouse fixture imports `mesh_to_tree`, gating ALL test collection on skeletor/trimesh/networkx/numpy. Bare `python3` fails.
* **Never pass `--timeout`** to pytest (that venv has no `pytest-timeout`), and **never run `pytest tests/`** (5,167 tests, >3 h). This slice needs no pytest run.
* **Nothing under `mcp_harness/` may change.** Not `contours.py`, not `assign.py`, not `layers.py`, not the serve path. `grep -c box_pleat mcp_harness/server.py` stays 0.
* **Reuse `contours._key` and `contours.is_boundary_seg`; never reimplement them.** §5.1: a reimplemented sorted-endpoint key would make every lookup miss, read `occupied` as 0, and manufacture a BUILD verdict.
* **`Point` is `tuple[int, int]`**, an integer half-grid coordinate in `[0, 2N]`. A unit segment steps by **1**, in `(1,0)` or `(0,1)`. Verified 2026-09-28: lizard's 4,488 contour segments have deltas `{(1,0): 1668, (0,1): 2820}` and nothing else.
* **Elevations are `fractions.Fraction`.** Equality is exact. **No tolerance or epsilon anywhere** — one would be a defect, not a safeguard.
* **Guard §5.1:** `set(res.contours) <= set(half_grid_segments(N))`, else no bucket and no verdict may be reported.
* **Guard §5.2:** occupied counts must be exactly `lizard` **4,488** and `bird` **11,534**, else no bucket and no verdict may be reported.
* **Coverage is reported, never guarded.** Measured 2026-09-28: `starfish` 48.2%, `lizard` 49.3%, `bird` 49.9%.
* **There is no `starfish` control** (§9). Do not write one into the analysis.
* **Per-subject cap 300 s** on the sparse compile; a timeout is that subject's recorded outcome, never a crash.
* **Never use bare `git stash` / `git stash pop`** — the stash stack is shared with other worktrees and concurrent sessions. Use a temporary WIP commit.
* **Commit messages end with** `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`
* **Bucket names are exactly** `occupied`, `level_injectable`, `slope`, `unreached` — in that order, spelled that way, in the code, the JSON and the README.
* **Never use tardigrade / water bear as a test subject** — OWNER INSTRUCTION.

## File Structure

| File | Responsibility |
|---|---|
| `docs/superpowers/evidence/2026-09-28-pleat-grid-headroom/headroom.py` (create) | the census: pure classifier functions, the two guards, the §6 bar, JSON serialisation, and a `--selftest` mode |
| `docs/superpowers/evidence/2026-09-28-pleat-grid-headroom/headroom.json` (generated) | per-subject buckets, coverage, components, guards, verdict, run metadata |
| `docs/superpowers/evidence/2026-09-28-pleat-grid-headroom/README.md` (create) | §8.5's required contents |

Two tasks. Task 1 is the script and its self-test, reviewable on its own and gating the run. Task 2 spends the run and writes the verdict.

---

### Task 1: The census script and its self-test

**Files:**
- Create: `docs/superpowers/evidence/2026-09-28-pleat-grid-headroom/headroom.py`

**Interfaces:**
- Consumes: `box_pleat.compile.compile_tree`; `box_pleat.contours._key`, `contours.is_boundary_seg`; `res.contours` (`dict[SegKey, Fraction]`), `res.layout.N` (int), `res.layout.boundary_elev` (`dict[Point, Fraction]`).
- Produces: `half_grid_segments(N) -> set`, `known_elevations(contours, boundary_elev) -> dict`, `classify(N, contours, boundary_elev) -> dict`, `components(segs) -> int`, `guards(subject, N, contours, buckets) -> tuple[bool, list]`, `verdict(row) -> tuple[str, dict]`, `serialise(value)`. Task 2 runs this file; nothing imports it.

**Context you need:** this mirrors `docs/superpowers/evidence/2026-09-28-witness-identity/identity.py`, the house pattern for an evidence script: module docstring carrying the reasoning and the run command, the pre-registered bar encoded as code rather than prose, guards that refuse rather than warn, JSON flushed per subject, and a `--selftest` mode covering the bar on synthetic input. Read it before writing yours.

- [ ] **Step 1: Create the directory**

```bash
mkdir -p docs/superpowers/evidence/2026-09-28-pleat-grid-headroom
```

- [ ] **Step 2: Write the script**

Create `docs/superpowers/evidence/2026-09-28-pleat-grid-headroom/headroom.py`:

```python
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

BUCKETS = ("occupied", "level_injectable", "slope", "unreached")

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
    points. Where both sources name a point they agree, because the field is
    single-valued -- `contours.py` raises ContourFail("collision") otherwise --
    so the merge order cannot matter.
    """
    known: dict = dict(boundary_elev)
    for (a, b), elev in contours.items():
        known[a] = elev
        known[b] = elev
    return known


def classify(N: int, contours: dict, boundary_elev: dict) -> dict:
    """bucket name -> set of SegKey. The four buckets partition the total.

    `level_injectable` is exactly component 1's contract: both endpoints known
    AND equal, so the segment's elevation is determined without inventing one.
    `slope` is endpoints known but UNEQUAL -- structurally not a level segment
    at any elevation (§3), never a limitation of `fill`.
    """
    known = known_elevations(contours, boundary_elev)
    out = {b: set() for b in BUCKETS}
    for key in half_grid_segments(N):
        if key in contours:
            out["occupied"].add(key)
            continue
        a, b = key
        ea, eb = known.get(a), known.get(b)
        if ea is None or eb is None:
            out["unreached"].add(key)
        elif ea == eb:
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
    return len({find(p) for p in parent})


# --------------------------------------------------------------------------
# guards (spec §5) -- they refuse, they do not warn
# --------------------------------------------------------------------------
def guards(subject: str, N: int, contours: dict, buckets: dict) -> tuple:
    """Returns (passed, [failure, ...]) for spec §5.1 and §5.2."""
    bad = []
    enumerated = half_grid_segments(N)
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
    """Fractions -> strings, tuples -> lists, sets -> sorted lists.

    Sorting is what makes the artifact diffable: set iteration order is not
    stable across runs, so an unsorted dump would differ run to run for reasons
    that are not findings.
    """
    if isinstance(value, Fraction):
        return str(value)
    if isinstance(value, (set, frozenset)):
        return sorted(serialise(v) for v in value)
    if isinstance(value, tuple):
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

    # --- the four buckets, hand-counted -----------------------------------
    # occupied: (1,1)-(2,1). Its endpoints become known at elevation 0.
    # (2,1)-(3,1) then has both endpoints known only if (3,1) is known too.
    contours = {C._key((1, 1), (2, 1)): e0}
    boundary = {(3, 1): e0, (1, 3): e1, (2, 3): e0}
    b = classify(N, contours, boundary)
    assert sum(len(v) for v in b.values()) == len(segs), "buckets do not partition"
    assert b["occupied"] == {C._key((1, 1), (2, 1))}
    # (2,1) known at 0 (contour endpoint), (3,1) known at 0 (boundary) -> level
    assert C._key((2, 1), (3, 1)) in b["level_injectable"]
    # (1,3) known at 1, (2,3) known at 0 -> unequal -> slope, NOT injectable
    assert C._key((1, 3), (2, 3)) in b["slope"]
    assert C._key((1, 3), (2, 3)) not in b["level_injectable"]
    # a segment with an unknown endpoint -> unreached
    assert C._key((1, 1), (1, 2)) in b["unreached"]

    # --- §4 exactness: ONE PASS IS THE FIXPOINT ---------------------------
    inj = b["level_injectable"]
    assert inj, "selftest fixture injects nothing -- it cannot test the fixpoint"
    grown = dict(contours)
    known = known_elevations(contours, boundary)
    for k in inj:
        grown[k] = known[k[0]]
    again = classify(N, grown, boundary)
    assert again["level_injectable"] == set(), (
        "one pass is NOT the fixpoint -- spec §4's exactness argument is false")

    # --- §4 exactness: ORDER-INDEPENDENCE ---------------------------------
    f1, f2 = dict(contours), dict(contours)
    for k in sorted(inj):
        f1[k] = known[k[0]]
    for k in sorted(inj, reverse=True):
        f2[k] = known[k[0]]
    assert f1 == f2, "injection is order-DEPENDENT -- spec §4 is false"

    # --- components -------------------------------------------------------
    assert components(set()) == 0
    assert components({C._key((0, 0), (0, 1))}) == 1
    # two disjoint segments -> two components
    assert components({C._key((0, 0), (0, 1)), C._key((3, 3), (3, 4))}) == 2
    # a path of two segments sharing a point -> one component
    assert components({C._key((0, 0), (0, 1)), C._key((0, 1), (0, 2))}) == 1

    # --- guards -----------------------------------------------------------
    ok, bad = guards("lizard", N, contours, {"occupied": set(range(4488))})
    assert ok, bad
    ok, bad = guards("lizard", N, contours, {"occupied": set(range(4487))})
    assert not ok and "§5.2" in bad[0], bad
    ok, bad = guards("bird", N, contours, {"occupied": set(range(11534))})
    assert ok, bad
    # a subject with no expectation is not guarded on the count
    ok, bad = guards("frog", N, contours, {"occupied": set()})
    assert ok, bad
    # §5.1: a key outside the enumeration must refuse
    outside = {C._key((0, 0), (0, 1)): e0}          # a boundary segment
    ok, bad = guards("frog", N, outside, {"occupied": set()})
    assert not ok and "§5.1" in bad[0], bad

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

    print("selftest OK: enumeration, 4 buckets, fixpoint, order-independence, "
          "components (4), guards (5), bar (9 cases), serialise")


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
        with open(out, "w") as fh:
            json.dump(rec, fh, indent=1)

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

        if res.stage_reached != "emit":
            row["outcome"] = f"stopped at {res.stage_reached}: {res.failure!r}"
            rec["rows"].append(row)
            flush()
            print(f"{s}: STOP {res.stage_reached}", flush=True)
            continue

        N = res.layout.N
        buckets = classify(N, res.contours, res.layout.boundary_elev)
        passed, bad = guards(s, N, res.contours, buckets)
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
              f"cov={row['coverage_pct']}% -> {row['coverage_after_pct']}% "
              f"comp {row['components_before']}->{row['components_after']} "
              f"guards={'PASS' if passed else 'FAIL'}", flush=True)
        for m in bad:
            print(f"    {m}", flush=True)

    # --- the verdict, on lizard, and only if its guards passed ------------
    liz = next((r for r in rec["rows"]
                if r["subject"] == "lizard" and r.get("outcome") == "ok"), None)
    print()
    if liz is None:
        rec["verdict"] = "NO VERDICT: lizard produced no row"
        flush()
        print("NO VERDICT: lizard produced no row, so §6 cannot be evaluated.")
        return
    if not liz["guards_passed"]:
        rec["verdict"] = "GUARD FAILED"
        rec["verdict_figures"] = None
        flush()
        print("GUARD FAILED (spec §5): NO bucket and NO verdict may be claimed, "
              "in either direction.")
        for m in liz["guard_failures"]:
            print(f"  {m}")
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
```

- [ ] **Step 3: Run the self-test to verify it passes**

Run, from `mcp_harness`:

```bash
PYTHONPATH=. ../.venv/bin/python3 -u ../docs/superpowers/evidence/2026-09-28-pleat-grid-headroom/headroom.py --selftest
```

Expected (corrected 2026-09-28 to match the committed script — see the note at
the top of this plan): `selftest OK: enumeration, 5 buckets (incl. hinge),
fixpoint, order-independence (iterative filler, 2 orders), hinge exclusion,
components (4), guards (5), guard_verdict (4), bar (9 cases), serialise (incl.
list-in-dict)`, exit 0, under 2 seconds.

If an assertion fails, the classifier or the bar is wrong — fix it here, **before** Task 2 spends compile time.

- [ ] **Step 4: Verify the self-test is not vacuous — break the classifier**

Temporarily change `classify`'s `elif ea == eb:` to `elif ea != eb:` (swapping `level_injectable` and `slope`). Re-run Step 3 and confirm it now FAILS on the `slope` / `level_injectable` assertion. Then restore the line and re-run Step 3 to confirm it passes again.

Expected: fails when broken, passes when restored. A self-test that passes against a swapped classifier is worse than none — the `slope` bucket is this census's entire headline.

- [ ] **Step 5: Verify the fixpoint assertion is not vacuous**

Temporarily change the fixpoint block's `grown[k] = known[k[0]]` to `pass` (so nothing is injected). Re-run Step 3 and confirm it FAILS on the `"one pass is NOT the fixpoint"` assertion — because `again["level_injectable"]` will still be non-empty. Then restore and re-run Step 3.

Expected: fails when broken, passes when restored. Spec §4's exactness argument is what makes a small result decisive, so its test must be able to fail.

- [ ] **Step 6: Confirm nothing under `mcp_harness/` changed**

Run:

```bash
git status --porcelain mcp_harness/
grep -c box_pleat mcp_harness/server.py
```

Expected: the first prints nothing; the second prints `0`.

- [ ] **Step 7: Commit**

```bash
git add docs/superpowers/evidence/2026-09-28-pleat-grid-headroom/headroom.py
git commit -m "evidence: the pleat-grid headroom census, with its bar self-tested

Spec 2026-09-28-pleat-grid-headroom-design.md. Read-only: no production code
changes, nothing under mcp_harness/ touched.

Four buckets -- occupied / level_injectable / slope / unreached -- partitioning
every in-paper half-grid unit segment. contours._key and is_boundary_seg are
REUSED rather than reimplemented: a reimplemented sorted-endpoint key would make
every lookup miss, read occupied as 0, and manufacture a BUILD verdict.

--selftest covers the enumeration invariants, all four buckets hand-counted,
both of spec §4's exactness properties (one pass is the fixpoint;
order-independence), components, both guards in both directions, and all four
bar rows plus both threshold boundaries in exact integers. Project memory records two throwaway probes that
drove wrong conclusions in one session, one of which printed its verdict
unconditionally.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: Run the census and write the verdict

**Files:**
- Create: `docs/superpowers/evidence/2026-09-28-pleat-grid-headroom/headroom.json` (generated)
- Create: `docs/superpowers/evidence/2026-09-28-pleat-grid-headroom/README.md`

**Interfaces:**
- Consumes: `headroom.py` from Task 1.
- Produces: the artifact and the README. Nothing consumes these; they are the deliverable.

**Context you need:** eight sparse compiles. `lizard` takes roughly 6.5 s and `bird` longer; `dog` and `octopus` are the largest and each has a 300 s cap. Budget a few minutes and run it in the background rather than polling in a tight loop. **The verdict is whatever the script prints — do not adjust the bar to fit the data, and do not write the README before the run finishes.** If a guard fails, that is a correct refusal and the README reports it as the outcome; do NOT edit `headroom.py` to make a guard pass.

- [ ] **Step 1: Re-run the self-test**

```bash
PYTHONPATH=. ../.venv/bin/python3 -u ../docs/superpowers/evidence/2026-09-28-pleat-grid-headroom/headroom.py --selftest
```

Expected: `selftest OK: ...`, exit 0. Do not start Step 2 unless this passes.

- [ ] **Step 2: Run the census**

Run in the background, from `mcp_harness`:

```bash
PYTHONPATH=. ../.venv/bin/python3 -u ../docs/superpowers/evidence/2026-09-28-pleat-grid-headroom/headroom.py ../docs/superpowers/evidence/2026-09-28-pleat-grid-headroom/headroom.json
```

Expected: one line per subject with its buckets, coverage before and after, component counts and `guards=PASS`; then either a verdict or an explicit refusal.

- [ ] **Step 3: Check the run agrees with itself**

```bash
../.venv/bin/python3 -c "
import json
d = json.load(open('../docs/superpowers/evidence/2026-09-28-pleat-grid-headroom/headroom.json'))
print('commit', d['commit'], '| measured', d['measured_utc'])
print('verdict', d.get('verdict'), d.get('verdict_figures'))
for r in d['rows']:
    if r.get('outcome') != 'ok':
        print(r['subject'], '->', r.get('outcome')); continue
    tot = sum(r[b] for b in d['buckets'])
    print(f\"{r['subject']:<11} N={r['N']:<3} total={r['total']:<6} \"
          f\"sum_buckets={tot:<6} partition_ok={tot == r['total']} \"
          f\"guards={r['guards_passed']} {r['guard_failures']}\")
"
```

Expected: `partition_ok=True` on every row (the four buckets must sum to `total`), `guards=True` on `lizard` and `bird`, and a non-empty `commit`. A guard failure means the verdict is `GUARD FAILED` and Step 4 reports that as the outcome.

- [ ] **Step 4: Write the README**

Create `docs/superpowers/evidence/2026-09-28-pleat-grid-headroom/README.md`, with every figure taken from `headroom.json` rather than from this plan or the spec:

1. **The question** — one paragraph: component 1 is gap 1's unbuilt third component and the leading untested hypothesis; this measures whether it can act, not whether it helps.
2. **Both guards (§5)** — expected beside measured. §5.1 for every subject; §5.2's two counts. If either failed, the README stops here and says no bucket or verdict may be claimed.
3. **The four-bucket table** — all eight subjects: N, total, the four counts, coverage before and after. Note explicitly that `coverage_after` and the injectable fraction are the same quantity rearranged.
4. **The contiguity reading** — components before and after per subject, and whether they fell.
5. **The verdict (§6)** — which row on `lizard`, why that row and not its neighbours.
6. **Whether ~49% coverage holds across all eight** — §9 struck the `starfish` control because coverage sat in a 48.2–49.9% band across a 13× range in N. Report whether the remaining five subjects also land there. A quantity that barely moves with problem size is a finding about the elevation field.
7. **What this cannot say (§7)** — a BUILD verdict licenses building `fill`; it does not predict convergence. Also: the score-guided-vs-exhaustive divergence (§2.3) is untouched, and `layer_order._propagate`'s non-confluence is unaffected.
8. **§9's correction** — state that the coverage figures this slice was originally built on were unreproducible, give the measured values, and note the direction (real coverage lower, so the gap larger).
9. **Run metadata** — the commit and timestamp from the artifact, and that they are recorded in the JSON rather than only in prose.

- [ ] **Step 5: Check every README figure against the artifact**

Re-read the README beside `headroom.json` and confirm each number appears there. Any figure that does not must be removed or recomputed. This step exists because the core-in-loop README shipped three arguments its own instruments dissolved on review, and because §9 of this spec exists at all.

- [ ] **Step 6: Confirm the instrument was not edited**

```bash
git status --porcelain docs/superpowers/evidence/2026-09-28-pleat-grid-headroom/headroom.py
git diff --stat HEAD -- mcp_harness/
```

Expected: both print nothing. An instrument edited after its run is one whose results cannot be trusted.

- [ ] **Step 7: Commit**

```bash
git add docs/superpowers/evidence/2026-09-28-pleat-grid-headroom/
git commit -m "evidence: <the verdict, in a clause> -- pleat-grid headroom

<one paragraph: both guards' outcomes, the four-bucket headline on lizard, the
contiguity reading, the §6 row reached, and whether ~49% coverage held across
the corpus>

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage.** Every section maps to a task:

| spec section | task |
|---|---|
| §3 four buckets | Task 1 Step 2 `classify`; Task 2 Step 4 item 3 |
| §3 contiguity reading | Task 1 `components`; Task 2 Step 4 item 4 |
| §4 exactness (fixpoint + order-independence) | Task 1 Step 2 `_selftest`, and Step 5 proves the fixpoint test can fail |
| §5.1 enumeration guard | `guards()`; Task 2 Step 3 |
| §5.2 occupancy calibration | `OCCUPIED_EXPECTED`; Task 2 Step 3 |
| §6 the bar | `verdict()`, self-tested on all four rows plus boundaries |
| §7 what it cannot say | printed by `main`; Task 2 Step 4 item 7 |
| §8.1 files | File Structure table |
| §8.2 pure functions | all present with the spec's signatures |
| §8.3 error handling | 300 s cap, per-subject failure recorded, guards refuse, flush per subject |
| §8.4 testing | Task 1 Steps 3–5; seven `_selftest` groups |
| §8.5 evidence + run metadata | `main`'s `rec` carries `measured_utc` and `commit`; Task 2 Step 4 |
| §9 the correction | Global Constraints (no starfish control, the re-targeted guard); Task 2 Step 4 items 6 and 8 |
| §10 out of scope | Global Constraints forbid every file it names |

**Placeholder scan.** The only intentional placeholders are Task 2 Step 7's commit message, which cannot be written before the data exists; Step 4's nine numbered items fix exactly what the README must contain.

**Type consistency.** `BUCKETS` is the single source of the four names, used by `classify`, `guards`, `main`'s row construction and Task 2 Step 3's partition check. `classify` returns `dict[str, set]` and every consumer treats it that way; `main` converts to counts exactly once. `guards(subject, N, contours, buckets)` and `verdict(row)` are each called once, with those signatures. `serialise` is the only JSON converter. `half_grid_segments` excludes boundary segments in **one** place, so `classify` and `guards` cannot disagree about the denominator.
