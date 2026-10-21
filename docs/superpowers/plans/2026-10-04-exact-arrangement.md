# Exact-Rational Arrangement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Determine whether `layer_order`'s float arrangement and constraint build are *correct* on dense `lizard`, by re-deriving them in exact rational arithmetic and comparing the results set-for-set.

**Architecture:** One standalone evidence probe. The shipped algorithm is transcribed once, parameterized over a numeric **kernel** (float or `Fraction`). In float mode the transcription must reproduce production element-for-element — that gate runs first and licenses everything after it. Swapping the kernel to `Fraction` then changes exactly one variable, so any difference is attributable to arithmetic alone.

**Tech Stack:** Python 3.14.3, `fractions.Fraction`, numpy (float mode only), `mcp_harness/layer_order.py` and `flat_fold.py` as read-only references.

**Spec:** `docs/superpowers/specs/2026-10-04-exact-arrangement-design.md`. Read it before Task 1 — especially §3 (the fidelity rule) and §5 (the three guards).

## Global Constraints

- **Run every command from the worktree root** `<repo>`, or from `mcp_harness` where a step says so. Do **NOT** `cd` to the original repository root.
- **Python is `../.venv/bin/python3` from inside `mcp_harness`** (`.venv/bin/python3` from the worktree root).
- **Nothing under `mcp_harness/` may be modified.** Reading and importing is fine. Off-limits for editing: `layer_order.py`, `layer_certify.py`, `box_pleat/layers.py`, `box_pleat/cores.py`, `box_pleat/compile.py`, `flat_fold.py`, `cp_audit.py`, every test file. This probe lives entirely under `docs/`.
- **No production default moves.** `AREA_EPS`, `GEOM_EPS`, `INTERIOR_EPS` keep their values (1e-9, 1e-9, 1e-8).
- **Nothing enters the PR gate.** No file is added under `mcp_harness/tests/`. The probe's guards are its tests.
- **`timeout` is not available on macOS.** Do not use it.
- **Never pass `--timeout` to pytest** (not installed; exits 4). **Never run `pytest tests/`** (5,167 tests, >3 hours).
- Write commit messages to a file **outside the repo**, under `<scratch>/9681b5fb-8510-4f03-86c1-4e4b6d0a887a/scratchpad/`, and use `git commit -F <file>`. zsh mangles heredocs containing backticks. End each message with `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- **Never use bare `git stash` / `git stash pop`** — the stash stack is shared with other worktrees and live sessions.
- **Never nest a heredoc inside another heredoc** — zsh terminates the OUTER one at the inner delimiter.
- **Quote every glob passed to grep.** zsh's `nomatch` aborts the whole command. `grep -c` exits 1 on zero matches, short-circuiting `&&` chains.
- **Every figure the README states must exist in `exact-arrangement.json`.** Mark derived values as derived and show their operands.

---

## Measured Facts This Plan Relies On

Verified before the plan was written. A step whose output disagrees with these should **stop and report** rather than adapt.

| fact | value | how obtained |
|---|---|---|
| the three epsilons | `AREA_EPS` 1e-9, `GEOM_EPS` 1e-9, `INTERIOR_EPS` 1e-8 (`layer_order.py:199`) | direct import |
| CP coordinate denominators | {1, 2, 4, 17, 34, 68}, max \|float−rational\| **0.00e+00** | `limit_denominator(10**6)` over `witness.fold` |
| folded coordinate denominators | {2, 4, 17, 34, 68}, max error **2.33e-15** | same, over `flat_fold(...).folded_vertices` |
| exact clipping, 40 faces | max denominator **68**, no growth, **0.011 s** | exact Sutherland–Hodgman on the real polygons |
| arrangement size | **26 cells**, 380 faces, 53,754 pairs | evidence §16 / `_polys_of` |
| float build time | 15.6 s at shipped eps, 49.2 s at eps=0 | evidence §16 |
| `_Constraints` fields | `pairs, direct, equalities, tacos, covers, slots` | `dataclasses.fields` |
| `layer_certify.clauses` | `(cons) -> tuple` | `inspect.signature` |
| epsilon-bearing helpers | `_cross`, `_area`, `_dedupe_ring`, `_clip_half`, `_clip_seg`, `_strictly_inside`, `_unit`, `_side_of`, `_collinear_overlap`, `_segs_interact` | grep |

### The square roots are removable — read this before Task 3

Three helpers normalize by `np.hypot`, which is irrational. **Every use reduces to a rational comparison**, and an implementer who does not know this will wrongly conclude the port is impossible:

* **`_side_of`** returns `sign(cross(u, c-a))` where `u = d/|d|`. Since `|d| > 0`, the sign is unchanged by the scaling: use the raw `d`.
* **`_unit`** returns `None` when `|d| < GEOM_EPS`. Exactly, that is `d == (0, 0)`.
* **`_collinear_overlap`** ends with `min(length, b1) - max(0.0, b0) > GEOM_EPS` where `b = dot(·, u)`. Multiply through by `length > 0`: with `L2 = dot(d1, d1)` and `B = dot(·, d1)`, the test becomes `min(L2, B1) > max(0, B0)`. All rational.

---

## File Structure

| file | responsibility |
|---|---|
| `docs/superpowers/evidence/2026-10-04-exact-arrangement/kernel.py` (create) | the numeric policy: `Kernel`, `FLOAT`, `EXACT`, coordinate conversion, and the margin recorder |
| `docs/superpowers/evidence/2026-10-04-exact-arrangement/geom.py` (create) | the transcribed geometry, kernel-parameterized: `cross`, `area`, `dedupe_ring`, `clip_half`, `split_convex`, `cells`, `clip_seg`, `strictly_inside`, `side_of`, `collinear_overlap`, `segs_interact` |
| `docs/superpowers/evidence/2026-10-04-exact-arrangement/build.py` (create) | the transcribed constraint build: `build_constraints(result, polys, cells, K)` producing the same shape as `_Constraints` |
| `docs/superpowers/evidence/2026-10-04-exact-arrangement/exact_arrangement.py` (create) | the driver: fidelity gate, both runs, comparison, guards, `--selftest`, JSON |
| `docs/superpowers/evidence/2026-10-04-exact-arrangement/exact-arrangement.json` (generated) | every figure the README cites |
| `docs/superpowers/evidence/2026-10-04-exact-arrangement/README.md` (create) | method, result, limits |

Four small modules rather than one file: the kernel is the thing a reviewer must check hardest, and it should be readable without scrolling past 400 lines of transcription.

---

### Task 1: the kernel and the arrangement, with the fidelity gate

**Files:**
- Create: `docs/superpowers/evidence/2026-10-04-exact-arrangement/kernel.py`
- Create: `docs/superpowers/evidence/2026-10-04-exact-arrangement/geom.py`
- Create: `docs/superpowers/evidence/2026-10-04-exact-arrangement/exact_arrangement.py` (driver skeleton + fidelity gate only)

**Interfaces:**
- Consumes: `layer_order` and `flat_fold`, read-only.
- Produces, for Tasks 2–4: `kernel.Kernel` with fields `name, conv, area_nonzero, side_keep, strict_cross, same_point, interior_pos, seg_span_pos, is_zero, is_neg`; the instances `kernel.FLOAT` and `kernel.EXACT`; `kernel.MarginLog` with `.record(tag, value, threshold)` and `.minimums()`; and from `geom`, `cells(polys, K) -> list[tuple[poly, frozenset]]` plus the primitives listed in the File Structure.

**Why the gate comes first.** The entire probe's meaning rests on the transcription being faithful. Memory records the alternative: *"a probe that RE-IMPLEMENTS production reads 0 moved while a direct call moves octopus 4→8."* Until float mode reproduces production, nothing the exact mode says is interpretable.

- [ ] **Step 1: Write `kernel.py`**

```python
"""The numeric policy the transcription is parameterized over.

One code path, two instantiations. FLOAT must reproduce `layer_order`'s
predicates EXACTLY -- it exists to prove the transcription is faithful, and a
predicate that merely resembles production's defeats that purpose. EXACT
replaces each tolerance with the zero test the tolerance was approximating.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Callable

# Copied from layer_order, NOT imported, so the float kernel keeps reproducing
# production even if those constants are retuned. A divergence then shows up as
# a fidelity-gate failure -- loudly -- instead of silently changing the control.
AREA_EPS = 1e-9
GEOM_EPS = 1e-9
INTERIOR_EPS = 1e-8

MAX_DEN = 10 ** 6
SNAP_TOL = 1e-12


@dataclass(frozen=True)
class Kernel:
    name: str
    conv: Callable            # float -> number
    area_nonzero: Callable    # |area| counts as non-degenerate
    side_keep: Callable       # _clip_half: keep vertex p
    strict_cross: Callable    # _clip_half: (sp, sq) is a strict sign change
    same_point: Callable      # _dedupe_ring: two points coincide
    interior_pos: Callable    # _strictly_inside: cross is strictly positive
    seg_span_pos: Callable    # _clip_seg: span is non-degenerate


def _snap(x: float) -> Fraction:
    """Rationalize a folded coordinate, refusing if the snap moves it.

    The input carries <=2.33e-15 of float rounding over a 1/68 grid. A snap
    that moves a coordinate further than SNAP_TOL is rationalizing NOISE into
    a different geometry, which would mean measuring an arrangement production
    never computed.
    """
    f = Fraction(x).limit_denominator(MAX_DEN)
    if abs(float(f) - x) > SNAP_TOL:
        raise SystemExit(
            f"REFUSED: snapping {x!r} to {f} moved it by "
            f"{abs(float(f) - x):.3e}, over SNAP_TOL={SNAP_TOL:.0e}. The "
            f"rationalized input would not be the geometry production used.")
    return f


FLOAT = Kernel(
    name="float",
    conv=float,
    area_nonzero=lambda a: abs(a) > AREA_EPS,
    side_keep=lambda sp: sp >= -GEOM_EPS,
    strict_cross=lambda sp, sq: (sp > GEOM_EPS and sq < -GEOM_EPS)
                             or (sp < -GEOM_EPS and sq > GEOM_EPS),
    same_point=lambda p, q: abs(p[0] - q[0]) <= 1e-9 and abs(p[1] - q[1]) <= 1e-9,
    interior_pos=lambda c: c > INTERIOR_EPS,
    seg_span_pos=lambda d: d > GEOM_EPS,
)

EXACT = Kernel(
    name="exact",
    conv=_snap,
    area_nonzero=lambda a: a != 0,
    side_keep=lambda sp: sp >= 0,
    strict_cross=lambda sp, sq: (sp > 0 and sq < 0) or (sp < 0 and sq > 0),
    same_point=lambda p, q: p == q,
    interior_pos=lambda c: c > 0,
    seg_span_pos=lambda d: d > 0,
)


@dataclass
class MarginLog:
    """How close each float comparison came to flipping.

    An identical float/exact result is the expected outcome, and an expected
    outcome needs an EXPLANATION or it is indistinguishable from luck. The
    minimum margin per tag is that explanation.
    """
    rows: dict = field(default_factory=dict)

    def record(self, tag: str, value: float, threshold: float) -> None:
        if threshold <= 0:
            raise ValueError("a margin needs a positive threshold")
        ratio = abs(value) / threshold
        prev = self.rows.get(tag)
        if prev is None or ratio < prev[0]:
            self.rows[tag] = (ratio, abs(value), threshold)

    def minimums(self) -> dict:
        return {tag: {"closest_ratio_to_threshold": r,
                      "value": v, "threshold": t}
                for tag, (r, v, t) in sorted(self.rows.items())}
```

- [ ] **Step 2: Write `geom.py` — the arrangement half**

Transcribe `layer_order`'s `_cross`, `_area`, `_dedupe_ring`, `_clip_half`, `_split_convex`, `_cells`. Keep the structure line-for-line; the only changes are kernel predicates and tuple-of-numbers instead of `np.ndarray`.

```python
"""The shipped arrangement algorithm, transcribed once, kernel-parameterized.

A TRANSCRIPTION, not a reimplementation: structure follows
`layer_order._cells` and its helpers statement for statement, and the only
substitutions are (a) the kernel's predicates where production compares against
an epsilon, and (b) tuples of numbers where production uses numpy arrays.
Changing the algorithm here would make a float/exact difference
uninterpretable -- it could be arithmetic, or it could be the rewrite.
"""
from __future__ import annotations

Point = tuple            # (x, y) of the kernel's number type


def cross(o, a, b):
    """Signed area of (o -> a) x (o -> b). layer_order's _cross, inlined."""
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _cross_d(d, v):
    """Cross of a DIRECTION with a vector (layer_order calls _cross(d, p-a))."""
    return d[0] * v[1] - d[1] * v[0]


def area(poly) -> object:
    """Twice-signed area / 2, matching layer_order._area's shoelace."""
    n = len(poly)
    s = 0
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        s = s + (x0 * y1 - x1 * y0)
    return s / 2 if not isinstance(s, int) else s / 2


def dedupe_ring(pts, K):
    """layer_order._dedupe_ring: drop consecutive duplicates incl. wrap."""
    out = []
    for pt in pts:
        if not out or not K.same_point(pt, out[-1]):
            out.append(pt)
    if len(out) >= 2 and K.same_point(out[0], out[-1]):
        out.pop()
    return out if len(out) >= 3 else []


def clip_half(poly, a, b, K):
    """layer_order._clip_half: clip convex poly to the half-plane left of a->b."""
    d = (b[0] - a[0], b[1] - a[1])
    n = len(poly)
    s = [_cross_d(d, (poly[i][0] - a[0], poly[i][1] - a[1])) for i in range(n)]
    out = []
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        sp, sq = s[i], s[(i + 1) % n]
        if K.side_keep(sp):
            out.append(p)
        if K.strict_cross(sp, sq):
            t = sp / (sp - sq)
            out.append((p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])))
    return dedupe_ring(out, K)


def split_convex(subject, clip, K, log=None):
    """layer_order._split_convex: (intersection_or_None, outside_pieces)."""
    pieces = []
    remaining = subject
    n = len(clip)
    for i in range(n):
        a, b = clip[i], clip[(i + 1) % n]
        if len(remaining) < 3:
            break
        outside = clip_half(remaining, b, a, K)   # right of a->b
        if len(outside) >= 3:
            ar = area(outside)
            if log is not None and K.name == "float":
                log.record("AREA_EPS/outside", float(ar), 1e-9)
            if K.area_nonzero(ar):
                pieces.append(outside)
        remaining = clip_half(remaining, a, b, K)
    inter = None
    if len(remaining) >= 3:
        ar = area(remaining)
        if log is not None and K.name == "float":
            log.record("AREA_EPS/intersection", float(ar), 1e-9)
        if K.area_nonzero(ar):
            inter = remaining
    return inter, pieces


def cells(polys, K, log=None):
    """layer_order._cells: arrangement cells as (polygon, cover frozenset)."""
    if not polys:
        return []
    xs = [pt[0] for p in polys for pt in p]
    ys = [pt[1] for p in polys for pt in p]
    one = K.conv(1.0)
    lo = (min(xs) - one, min(ys) - one)
    hi = (max(xs) + one, max(ys) + one)
    box = [(lo[0], lo[1]), (hi[0], lo[1]), (hi[0], hi[1]), (lo[0], hi[1])]
    acc = [(box, frozenset())]
    for fi, poly in enumerate(polys):
        new = []
        for cpoly, cover in acc:
            inter, outs = split_convex(cpoly, poly, K, log)
            if inter is None:
                new.append((cpoly, cover))
                continue
            new.append((inter, cover | frozenset({fi})))
            new.extend((o, cover) for o in outs)
        acc = new
    return [(cpoly, cover) for cpoly, cover in acc if cover]
```

- [ ] **Step 3: Write the driver skeleton with the fidelity gate**

```python
"""Is layer_order's FLOAT arrangement correct? Re-derive it exactly and compare.

`layer_certify` states the limit of its own verdict in capitals: CERTIFIED IS
NOT FLAT-FOLDABLE, because `layer_order.AREA_EPS` drops sliver cells, and
"Closing that is separate work." This is that work in its smallest useful form.

The caveat names ONE epsilon; the arrangement rests on THREE -- AREA_EPS (1e-9,
measured inert on this subject by evidence section 16), GEOM_EPS (1e-9, never
measured) and INTERIOR_EPS (1e-8, never measured, and carrying a recorded
incident: at 1e-9 it "MADE THE ORACLE FABRICATE CONSTRAINTS ON LINUX").

WHAT LICENSES EVERY NUMBER BELOW. The transcription runs first in FLOAT mode
and must reproduce production's cells element for element. Only then is the
kernel swapped. One variable changes, so a difference is arithmetic.
"""
from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "..", "..", "mcp_harness"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import flat_fold                      # noqa: E402
import layer_order                    # noqa: E402
import geom                           # noqa: E402
import kernel                         # noqa: E402

WITNESS = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "2026-10-02-witness-identity-113", "witness.fold")


def load():
    ff = flat_fold.flat_fold(json.load(open(WITNESS)))
    return ff, layer_order._polys_of(ff)


def as_tuples(polys, K):
    return [[(K.conv(float(x)), K.conv(float(y))) for x, y in p] for p in polys]


def canon_cells(cells_list):
    """Compare cells by COVER multiset, not by polygon identity.

    Polygon vertex order and the cell list's order are implementation detail
    and can differ without semantic difference; the cover is what `pairs` and
    the clause set are derived from.
    """
    return sorted(tuple(sorted(cover)) for _poly, cover in cells_list)


def fidelity_gate():
    """FLOAT mode must reproduce production. Nothing else runs until it does."""
    ff, polys = load()
    prod = layer_order._cells(polys)
    mine = geom.cells(as_tuples(polys, kernel.FLOAT), kernel.FLOAT)
    p, m = canon_cells(prod), canon_cells(mine)
    if p != m:
        only_prod = [c for c in p if c not in m][:3]
        only_mine = [c for c in m if c not in p][:3]
        raise SystemExit(
            f"REFUSED: the float transcription does not reproduce production. "
            f"production {len(p)} cells, transcription {len(m)}. "
            f"production-only covers (first 3): {only_prod}; "
            f"transcription-only: {only_mine}. Until these agree the exact "
            f"result is uninterpretable -- a difference could be arithmetic "
            f"OR a divergent rewrite.")
    return {"production_cells": len(p), "transcription_cells": len(m),
            "covers_identical": True}


if __name__ == "__main__":
    t0 = time.perf_counter()
    print("fidelity gate: float transcription vs production `_cells` ...")
    g = fidelity_gate()
    print(f"  PASS -- {g['production_cells']} cells, covers identical "
          f"({time.perf_counter() - t0:.1f}s)")
```

- [ ] **Step 4: Run the fidelity gate**

Run:
```bash
cd docs/superpowers/evidence/2026-10-04-exact-arrangement && ../../../../.venv/bin/python3 exact_arrangement.py
```
Expected: `PASS -- 26 cells, covers identical`.

**If it fails, do NOT adjust the comparison to make it pass.** The gate failing means the transcription diverged from production, which is the one thing this probe cannot tolerate. Report the printed cover differences.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/evidence/2026-10-04-exact-arrangement/
git commit -F <message-file>
```

---

### Task 2: the exact arrangement and the pairs/covers comparison

**Files:**
- Modify: `docs/superpowers/evidence/2026-10-04-exact-arrangement/exact_arrangement.py`

**Interfaces:**
- Consumes: `geom.cells`, `kernel.FLOAT`, `kernel.EXACT`, `kernel.MarginLog` from Task 1.
- Produces, for Tasks 3–4: `arrangement_result() -> dict` with keys `float_cells`, `exact_cells`, `covers_identical`, `pairs_float`, `pairs_exact`, `pairs_identical`, `pairs_only_float`, `pairs_only_exact`, `margins`, `max_denominator`, `secs`.

- [ ] **Step 1: Add the exact run and the comparison**

```python
from itertools import combinations


def pairs_of(cells_list):
    """`_build_constraints`'s derivation: every pair inside every cover."""
    return frozenset(pr for _poly, cover in cells_list
                     for pr in combinations(sorted(cover), 2))


def max_denominator(cells_list):
    """Denominator growth is the one feasibility risk; measure it, do not assume."""
    best = 1
    for poly, _cover in cells_list:
        for x, y in poly:
            best = max(best, getattr(x, "denominator", 1),
                       getattr(y, "denominator", 1))
    return best


def arrangement_result():
    ff, polys = load()
    log = kernel.MarginLog()

    t0 = time.perf_counter()
    fl = geom.cells(as_tuples(polys, kernel.FLOAT), kernel.FLOAT, log)
    ex = geom.cells(as_tuples(polys, kernel.EXACT), kernel.EXACT)
    secs = round(time.perf_counter() - t0, 2)

    pf, pe = pairs_of(fl), pairs_of(ex)
    return {
        "float_cells": len(fl), "exact_cells": len(ex),
        "covers_identical": canon_cells(fl) == canon_cells(ex),
        "pairs_float": len(pf), "pairs_exact": len(pe),
        "pairs_identical": pf == pe,
        "pairs_only_float": sorted(pf - pe)[:20],
        "pairs_only_exact": sorted(pe - pf)[:20],
        "n_only_float": len(pf - pe), "n_only_exact": len(pe - pf),
        "margins": log.minimums(),
        "max_denominator": max_denominator(ex),
        "secs": secs,
    }
```

**Note the comparison is symmetric.** `pf == pe` plus both difference sets, never `pe <= pf`. A subset check passes on equality, which is the regression it would exist to catch.

- [ ] **Step 2: Add the non-empty-population guard and wire it into `__main__`**

```python
def require_nonempty(**populations):
    """Two empty sets compare equal and prove nothing.

    This project has a recorded instance of exactly that: a metric that read
    "no gap" while two whole families were missing. Assert the population
    before trusting the comparison.
    """
    empty = [name for name, n in populations.items() if not n]
    if empty:
        raise SystemExit(
            f"REFUSED: {', '.join(empty)} is empty, so the comparison over it "
            f"is vacuous -- it would report agreement having examined nothing.")
```

Append to `__main__`:

```python
    print("exact arrangement ...")
    arr = arrangement_result()
    require_nonempty(float_cells=arr["float_cells"],
                     exact_cells=arr["exact_cells"],
                     pairs_float=arr["pairs_float"],
                     pairs_exact=arr["pairs_exact"])
    print(f"  cells float {arr['float_cells']} / exact {arr['exact_cells']}  "
          f"covers identical: {arr['covers_identical']}")
    print(f"  pairs float {arr['pairs_float']:,} / exact {arr['pairs_exact']:,}  "
          f"identical: {arr['pairs_identical']}")
    print(f"  only-float {arr['n_only_float']}, only-exact {arr['n_only_exact']}")
    print(f"  max denominator {arr['max_denominator']}, {arr['secs']}s")
    for tag, m in arr["margins"].items():
        print(f"  margin {tag}: closest {m['closest_ratio_to_threshold']:.3g}x "
              f"threshold (value {m['value']:.3e})")
```

- [ ] **Step 3: Run it**

Run:
```bash
cd docs/superpowers/evidence/2026-10-04-exact-arrangement && ../../../../.venv/bin/python3 exact_arrangement.py
```
Expected: the gate passes, then 26 cells in both modes, `pairs_identical: True`, 53,754 pairs each way, `max denominator` a small integer (68 measured over 40 single cuts; **this run accumulates cuts per cell, so a larger value here is a finding to report, not a problem to fix**).

If `pairs_identical` is `False`, that is the probe working — record the counts and both difference sets and report. Do not adjust anything.

- [ ] **Step 4: Commit**

---

### Task 3: the constraint build, covering INTERIOR_EPS

**Files:**
- Create: `docs/superpowers/evidence/2026-10-04-exact-arrangement/build.py`
- Modify: `docs/superpowers/evidence/2026-10-04-exact-arrangement/geom.py` (append the segment half)
- Modify: `docs/superpowers/evidence/2026-10-04-exact-arrangement/exact_arrangement.py`

**Interfaces:**
- Consumes: everything from Tasks 1–2.
- Produces, for Task 4: `constraint_result() -> dict` with keys `clauses_float`, `clauses_exact`, `clauses_identical`, `n_only_float`, `n_only_exact`, `families_float`, `families_exact`, `direction`, `margins`.

**Read "The square roots are removable" above before starting.** `_side_of`, `_unit` and `_collinear_overlap` all normalize by `np.hypot`; all three reduce to rational comparisons, and the reductions are given there.

> ### ⚠ A constraint-level fidelity gate is MANDATORY, and this is not hypothetical
>
> Task 1's gate covers `_cells` only. **The constraint build needs its own
> gate, and the plan author's draft transcription FAILED it** — measured, not
> feared:
>
> | family | production | the failed draft |
> |---|---|---|
> | `pairs` | 53,754 | 53,754 ✅ |
> | `equalities` | **28,192** | 31,388 ❌ (+3,196) |
> | `tacos` | **74,602** | 66,624 ❌ (−7,978) |
>
> Run without that gate, the same draft then reported *"float fabricated 18
> taco constraints"* against exact arithmetic — an alarming claim about shipped
> code that was **entirely an artifact of the rewrite**. The gate is what tells
> a real arithmetic finding from a transcription bug, and it is the difference
> between this probe being evidence and being noise.
>
> ### The predicates Task 3 needs, and the one sanctioned `K.name` branch
>
> `Kernel` gained `is_zero(x)` and `is_neg(x)` during Task 1's review, because
> `_clip_seg`, `_segs_interact`, `_side_of` and `_collinear_overlap` all compare
> against `GEOM_EPS` in forms the original eight fields could not express. Use
> them; do **not** improvise compound predicates out of `strict_cross` and
> `side_keep`. The plan author did exactly that and it is part of why the draft
> below fails its gate. A straddle test's `x > GEOM_EPS` is `is_neg(-x)`.
>
> **The one place `K.name` branching is legitimate.** `_collinear_overlap` and
> `_segs_interact` end with `min(length, b1) - max(0.0, b0) > GEOM_EPS` — an
> ABSOLUTE distance threshold taken after normalizing by a segment length.
> Scaling that by `length` to remove the square root (which exact arithmetic
> requires, since a norm is irrational) also removes the threshold's meaning:
> the two forms agree only when the threshold is 0. So the **float** branch
> reproduces production verbatim, `hypot` included, because it is the control
> and must match bitwise; the **exact** branch uses the scaled rational form,
> where the threshold is exactly 0 and the scaling is sound. That is the only
> sanctioned use of `K.name` — not a licence to branch wherever exact
> arithmetic is inconvenient.
>
> **Production's three numbers above are the acceptance criterion.** They also
> appear in evidence §14 (`eq 28192 taco 74602`), so they are independently
> attested. Do not proceed to the exact run until float mode reproduces them.

- [ ] **Step 1: Write the constraint-level fidelity gate FIRST, before any transcription**

Add to the driver. Writing the gate before the code it gates is deliberate: it is the acceptance criterion for everything in this task.

```python
def constraint_fidelity_gate():
    """FLOAT-mode `build` must reproduce production's `_build_constraints`.

    Task 1's gate covers `_cells`. This one covers the constraint families, and
    it is what distinguishes a real arithmetic finding from a transcription
    bug. The plan author's own draft passed `pairs` and failed both other
    families, then reported a spurious 18-constraint "fabrication" against
    exact arithmetic. Without this gate that claim would have shipped.
    """
    import build as build_mod
    ff, polys = load()
    cons, _slots = layer_order.constraints_for(ff)      # returns (cons, slots)
    want = {
        "pairs": cons.pairs,
        "eqs": frozenset((e[0], e[1]) for e in cons.equalities),
        "tacos": frozenset((t[0], t[1]) for t in cons.tacos),
    }
    pk = as_tuples(polys, kernel.FLOAT)
    got = dict(zip(("pairs", "eqs", "tacos"),
                   build_mod.build(ff, pk, geom.cells(pk, kernel.FLOAT),
                                   kernel.FLOAT)))
    bad = {k: (len(want[k]), len(got[k]),
               len(want[k] - got[k]), len(got[k] - want[k]))
           for k in want if want[k] != got[k]}
    if bad:
        raise SystemExit(
            "REFUSED: the float constraint transcription does not reproduce "
            "production. " + "; ".join(
                f"{k}: production {w:,} vs transcription {g:,} "
                f"(only-production {op}, only-transcription {ot})"
                for k, (w, g, op, ot) in bad.items()) +
            ". Until these agree, any float/exact difference is "
            "uninterpretable -- it could be arithmetic OR the rewrite.")
    return {k: len(v) for k, v in want.items()}
```

Expected once the transcription is right: `pairs` 53,754, `eqs` 28,192, `tacos` 74,602.

- [ ] **Step 2: Append the segment helpers to `geom.py`**

```python
def clip_seg(seg, poly, K):
    """layer_order._clip_seg: parametric span of seg inside convex poly."""
    p0 = seg[0]
    d = (seg[1][0] - p0[0], seg[1][1] - p0[1])
    t0, t1 = K.conv(0.0), K.conv(1.0)
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        e = (b[0] - a[0], b[1] - a[1])
        denom = _cross_d(e, d)
        num = _cross_d(e, (p0[0] - a[0], p0[1] - a[1]))
        if not K.strict_cross(denom, -denom) and K.side_keep(denom) \
                and K.side_keep(-denom):
            # |denom| under tolerance (float) or exactly 0 (exact): parallel
            if not K.side_keep(num):
                return None
            continue
        t = -num / denom
        if denom > 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
    return (t0, t1) if K.seg_span_pos(t1 - t0) else None


def strictly_inside(p, poly, K):
    """layer_order._strictly_inside -- where INTERIOR_EPS lives."""
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        c = _cross_d((b[0] - a[0], b[1] - a[1]), (p[0] - a[0], p[1] - a[1]))
        if not K.interior_pos(c):
            return False
    return True


def direction(seg, K):
    """layer_order._unit WITHOUT the square root.

    `_unit` normalizes and returns None below GEOM_EPS. Every consumer uses the
    result only inside a cross product whose SIGN it reads, and scaling by a
    positive length cannot change a sign -- so the raw direction is equivalent
    and exact. Degeneracy becomes the exact zero vector.
    """
    d = (seg[1][0] - seg[0][0], seg[1][1] - seg[0][1])
    if K.name == "exact":
        return None if (d[0] == 0 and d[1] == 0) else d
    import math
    return None if math.hypot(float(d[0]), float(d[1])) < 1e-9 else d


def side_of(poly, a, d, K):
    """layer_order._side_of with the raw direction (sign is scale-invariant)."""
    n = len(poly)
    cx = sum(pt[0] for pt in poly) / n
    cy = sum(pt[1] for pt in poly) / n
    v = _cross_d(d, (cx - a[0], cy - a[1]))
    if K.name == "exact":
        return 0 if v == 0 else (1 if v > 0 else -1)
    return 0 if abs(float(v)) < 1e-9 else (1 if v > 0 else -1)


def collinear_overlap(s1, s2, K):
    """layer_order._collinear_overlap, square root removed.

    Production computes `min(length, b1) - max(0, b0) > GEOM_EPS` with b the
    projection onto the UNIT direction. Multiplying through by length > 0 and
    writing L2 = dot(d1,d1), B = dot(., d1) gives min(L2, B1) > max(0, B0).
    """
    p, q = s1
    r, s = s2
    d1 = (q[0] - p[0], q[1] - p[1])
    d2 = (s[0] - r[0], s[1] - r[1])
    o = (_cross_d(d1, (r[0] - p[0], r[1] - p[1])),
         _cross_d(d1, (s[0] - p[0], s[1] - p[1])),
         _cross_d(d2, (p[0] - r[0], p[1] - r[1])),
         _cross_d(d2, (q[0] - r[0], q[1] - r[1])))
    if K.name == "exact":
        if any(x != 0 for x in o):
            return False
    else:
        if any(abs(float(x)) >= 1e-9 for x in o):
            return False
    L2 = d1[0] * d1[0] + d1[1] * d1[1]
    if K.name == "exact":
        if L2 == 0:
            return False
    elif float(L2) < 1e-18:
        return False
    B0 = (r[0] - p[0]) * d1[0] + (r[1] - p[1]) * d1[1]
    B1 = (s[0] - p[0]) * d1[0] + (s[1] - p[1]) * d1[1]
    if B0 > B1:
        B0, B1 = B1, B0
    zero = K.conv(0.0)
    return min(L2, B1) > max(zero, B0)
```

- [ ] **Step 3: Write `build.py`**

Transcribe the three constraint families from `layer_order._build_constraints` (lines 520-650): `_spanning`'s equalities, taco-tortilla, tortilla-tortilla, and taco-taco. Keep `direct` and `slots` out — the spec excludes `direct` as label-dependent, and `slots` is derived from it.

**The skeleton below has VERIFIED call-site structure but UNVERIFIED bodies.** Its `_spanning` call sites were read from source and are correct: `_spanning` runs for every crease *and* every tortilla (`layer_order.py:580-583`). But this exact code **fails the Step 1 gate** — measured at `eqs` 31,388 against production's 28,192 and `tacos` 66,624 against 74,602. Treat it as scaffolding whose bodies you must check statement-by-statement against `layer_order.py:520-650`, not as finished code. The gate is the acceptance criterion; iterate against it.

Known suspects from the author's debugging, offered as starting points and not as a diagnosis: `eqs` is accumulated here as a `set` while production builds a `list` and returns `tuple(eqs)`; `clip_seg`'s parallel branch is expressed as a compound of `strict_cross`/`side_keep` rather than an explicit zero test, and uses `<=` where production uses `<`; and `segs_interact`/`collinear_overlap` are the only helpers whose output feeds `tacos`, which is the family that diverged most.

```python
"""The shipped constraint families, transcribed, kernel-parameterized.

`direct` and `slots` are deliberately absent: `direct` is the order relations
forced by ONE fixed labelling, which the joint query ignores by design, and
`slots` is derived from it. What remains -- pairs, equalities, tacos -- is
label-independent geometry, which is exactly what this probe is testing.
"""
from __future__ import annotations

from itertools import combinations

import geom


def build(result, polys_k, cells_list, K):
    """Returns (pairs, equalities, tacos) as comparable frozensets."""
    covers = [c for _p, c in cells_list]
    pairs = frozenset(pr for c in covers for pr in combinations(sorted(c), 2))

    def seg_of(fa, k):
        face = result.faces[fa]
        i0, i1 = face.index(k[0]), face.index(k[1])
        return (polys_k[fa][i0], polys_k[fa][i1])

    creases, tortillas = [], []
    for fa, fb, k, a in result.shared_edges:
        if a in ("M", "V"):
            creases.append((fa, fb, a, seg_of(fa, k), k))
        else:
            tortillas.append((fa, fb, seg_of(fa, k), k))

    eqs = set()
    tacos = set()

    def lit(x, f):
        return ((x, f), False) if x < f else ((f, x), True)

    def spanning(seg, fa, fb):
        for x in range(len(polys_k)):
            if x in (fa, fb):
                continue
            if tuple(sorted((x, fa))) not in pairs:
                continue
            if tuple(sorted((x, fb))) not in pairs:
                continue
            span = geom.clip_seg(seg, polys_k[x], K)
            if span is None:
                continue
            mid_t = (span[0] + span[1]) / 2
            mid = (seg[0][0] + mid_t * (seg[1][0] - seg[0][0]),
                   seg[0][1] + mid_t * (seg[1][1] - seg[0][1]))
            if not geom.strictly_inside(mid, polys_k[x], K):
                continue
            eqs.add((lit(x, fa), lit(x, fb)))

    for fa, fb, _a, seg, _k in creases:
        spanning(seg, fa, fb)
    for fa, fb, seg, _k in tortillas:
        spanning(seg, fa, fb)

    for fa, fb, _a, seg, _k in creases:
        d = geom.direction(seg, K)
        if d is None:
            continue
        sa = geom.side_of(polys_k[fa], seg[0], d, K)
        sb = geom.side_of(polys_k[fb], seg[0], d, K)
        if sa == 0 or sa != sb:
            continue
        for ta, tb, tseg, _tk in tortillas:
            if not geom.collinear_overlap(seg, tseg, K):
                continue
            for x in (ta, tb):
                if x in (fa, fb):
                    continue
                if geom.side_of(polys_k[x], seg[0], d, K) != sa:
                    continue
                if tuple(sorted((x, fa))) not in pairs:
                    continue
                if tuple(sorted((x, fb))) not in pairs:
                    continue
                eqs.add((lit(x, fa), lit(x, fb)))

    for t1, t2 in combinations(tortillas, 2):
        (a1, a2, s1, _k1), (b1, b2, _s2, _k2) = t1, t2
        if not geom.collinear_overlap(s1, t2[2], K):
            continue
        d = geom.direction(s1, K)
        if d is None:
            continue
        A = {geom.side_of(polys_k[f], s1[0], d, K): f for f in (a1, a2)}
        B = {geom.side_of(polys_k[f], s1[0], d, K): f for f in (b1, b2)}
        if set(A) != {1, -1} or set(B) != {1, -1}:
            continue
        if A[1] in (B[1], B[-1]) or A[-1] in (B[1], B[-1]):
            continue
        if any(tuple(sorted((A[s], B[s]))) not in pairs for s in (1, -1)):
            continue
        eqs.add((lit(A[1], B[1]), lit(A[-1], B[-1])))

    for c1, c2 in combinations(creases, 2):
        fa1, fb1, _x1, s1, _k1 = c1
        fa2, fb2, _x2, s2, _k2 = c2
        if not geom.segs_interact(s1, s2, K):
            continue
        quad = ((fa2, fa1), (fa2, fb1), (fb2, fa1), (fb2, fb1))
        if any(tuple(sorted(pq)) not in pairs for pq in quad):
            continue
        tacos.add(((fa1, fb1), (fa2, fb2)))
        tacos.add(((fa2, fb2), (fa1, fb1)))

    return pairs, frozenset(eqs), frozenset(tacos)
```

- [ ] **Step 4: Transcribe `_segs_interact` into `geom.py`**

Read `layer_order._segs_interact` and transcribe it with the same kernel discipline, replacing its `GEOM_EPS` comparisons with `K` predicates and removing any `hypot` by the reductions above. Append it to `geom.py` as `segs_interact(s1, s2, K)`.

- [ ] **Step 5: Add `constraint_result()` to the driver**

```python
import build as build_mod


def constraint_result():
    ff, polys = load()
    out = {}
    for K in (kernel.FLOAT, kernel.EXACT):
        pk = as_tuples(polys, K)
        cl = geom.cells(pk, K)
        p, e, t = build_mod.build(ff, pk, cl, K)
        out[K.name] = {"pairs": p, "eqs": e, "tacos": t}
    f, x = out["float"], out["exact"]
    res = {}
    for fam in ("pairs", "eqs", "tacos"):
        a, b = f[fam], x[fam]
        res[f"{fam}_float"] = len(a)
        res[f"{fam}_exact"] = len(b)
        res[f"{fam}_identical"] = a == b
        res[f"{fam}_only_float"] = len(a - b)
        res[f"{fam}_only_exact"] = len(b - a)
    total_f = sum(res[f"{fam}_only_float"] for fam in ("pairs", "eqs", "tacos"))
    total_x = sum(res[f"{fam}_only_exact"] for fam in ("pairs", "eqs", "tacos"))
    res["direction"] = (
        "identical" if total_f == 0 and total_x == 0 else
        "float UNDER-refuted (exact has more): AREA_EPS/GEOM_EPS dropped real "
        "constraints -- the direction layer_order says is safe by design"
        if total_f == 0 else
        "float FABRICATED constraints (exact has fewer): the INTERIOR_EPS "
        "direction the module says is ruled out -- CERTIFIED would rest on "
        "constraints that do not exist"
        if total_x == 0 else
        "BOTH directions differ: investigate per family")
    return res
```

- [ ] **Step 6: Run it, with the non-empty guard**

Add to `__main__` before printing:

```python
    con = constraint_result()
    require_nonempty(pairs=con["pairs_float"], eqs=con["eqs_float"],
                     tacos=con["tacos_float"])
```

Run the driver. Expected: each family identical, and `direction` reading `identical`. Report the counts whatever they are. **A difference is the probe working.**

- [ ] **Step 7: Commit**

---

### Task 4: the guards, the self-test, and the evidence

**Files:**
- Modify: `docs/superpowers/evidence/2026-10-04-exact-arrangement/exact_arrangement.py`
- Create: `docs/superpowers/evidence/2026-10-04-exact-arrangement/exact-arrangement.json`
- Create: `docs/superpowers/evidence/2026-10-04-exact-arrangement/README.md`

**Interfaces:**
- Consumes: `fidelity_gate`, `arrangement_result`, `constraint_result`, `require_nonempty`.
- Produces: the evidence directory. Nothing consumes it.

- [ ] **Step 1: Add the seeded-disagreement guard**

```python
def seeded_disagreement():
    """Prove the comparison CAN fail.

    An equality check that has never been shown to fail is not a check. Perturb
    one coordinate by more than the grid resolution (1/68 ~ 0.0147) and confirm
    the arrangement comparison reports a difference. If it still reports
    agreement, the comparison is inert and every other result here is void.
    """
    ff, polys = load()
    bad = [list(map(list, p)) for p in polys]
    bad[0][0][0] = float(bad[0][0][0]) + 0.05        # >> 1/68
    fl = geom.cells(as_tuples(polys, kernel.FLOAT), kernel.FLOAT)
    pert = geom.cells(as_tuples(bad, kernel.FLOAT), kernel.FLOAT)
    if canon_cells(fl) == canon_cells(pert):
        raise SystemExit(
            "REFUSED: perturbing a coordinate by 0.05 (3.4x the 1/68 grid "
            "step) left the cell comparison UNCHANGED. The comparison cannot "
            "detect a difference, so an 'identical' verdict from it is "
            "meaningless and every figure in this run is void.")
    return {"perturbation": 0.05, "grid_step": 1.0 / 68,
            "comparison_detected_it": True}
```

- [ ] **Step 2: Add `--selftest` and the JSON writer**

```python
def selftest():
    print("selftest 1/3: fidelity gate (float transcription == production)")
    g = fidelity_gate()
    print(f"  PASS -- {g['production_cells']} cells")
    print("selftest 2/3: seeded disagreement (the comparison can fail)")
    s = seeded_disagreement()
    print(f"  PASS -- a {s['perturbation']} perturbation was detected")
    print("selftest 3/3: non-empty population guard refuses an empty set")
    try:
        require_nonempty(demo=0)
    except SystemExit:
        print("  PASS -- refused as designed")
    else:
        raise SystemExit("REFUSED: require_nonempty did not refuse an empty "
                         "population, so guard 2 of the spec is inert.")
    return {"fidelity": g, "seeded_disagreement": s,
            "nonempty_guard_refuses": True}


def main(out_path):
    rec = {}
    rec["fidelity"] = fidelity_gate()
    rec["seeded_disagreement"] = seeded_disagreement()
    rec["arrangement"] = arrangement_result()
    require_nonempty(float_cells=rec["arrangement"]["float_cells"],
                     pairs_float=rec["arrangement"]["pairs_float"])
    rec["constraints"] = constraint_result()
    require_nonempty(pairs=rec["constraints"]["pairs_float"],
                     eqs=rec["constraints"]["eqs_float"],
                     tacos=rec["constraints"]["tacos_float"])
    rec["epsilons"] = {"AREA_EPS": kernel.AREA_EPS,
                       "GEOM_EPS": kernel.GEOM_EPS,
                       "INTERIOR_EPS": kernel.INTERIOR_EPS}
    with open(out_path, "w") as fh:
        json.dump(rec, fh, indent=1, sort_keys=True, default=str)
    print(f"\nwrote {out_path}")

    a, c = rec["arrangement"], rec["constraints"]
    allsame = a["pairs_identical"] and all(
        c[f"{fam}_identical"] for fam in ("pairs", "eqs", "tacos"))
    worst = min((m["closest_ratio_to_threshold"]
                 for m in a["margins"].values()), default=None)
    print()
    if allsame and worst is not None and worst > 1000:
        print(f"VERDICT: THE FLOAT PATH IS CORRECT HERE, AND NOT BY LUCK. "
              f"Exact and float agree on pairs, equalities and tacos, and the "
              f"closest any float comparison came to its threshold was "
              f"{worst:.3g}x it. On dense `lizard` the three epsilons are "
              f"inert and CERTIFIED is not weakened by them. One subject, "
              f"box-pleat only -- see the README's limits.")
    elif allsame:
        print(f"VERDICT: IDENTICAL, BUT ON A KNIFE EDGE. The sets agree, yet "
              f"the closest float comparison sat {worst:.3g}x its threshold. "
              f"Agreement here is not robust and a production exact path is "
              f"warranted.")
    else:
        print(f"VERDICT: THE FLOAT PATH AND EXACT ARITHMETIC DISAGREE. "
              f"{c['direction']}")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        raise SystemExit(0)
    main(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "exact-arrangement.json"))
```

- [ ] **Step 3: Run the self-test, then the full run**

```bash
cd docs/superpowers/evidence/2026-10-04-exact-arrangement && ../../../../.venv/bin/python3 exact_arrangement.py --selftest
```
Expected: three PASS lines.

```bash
cd docs/superpowers/evidence/2026-10-04-exact-arrangement && ../../../../.venv/bin/python3 exact_arrangement.py
```
Expected: the gate, both comparisons, the JSON, and one of the three verdicts.

- [ ] **Step 4: Write the README**

Sections, in order: (1) why this exists, quoting `layer_certify`'s caveat and naming all three epsilons with their values; (2) method and what licenses it (the fidelity gate reproducing production); (3) the result table — cells, pairs, equalities, tacos, float vs exact, identical or not; (4) margins, the closest call per epsilon; (5) the verdict and its consequence, taken from the spec's §6 outcome table; (6) what this does not establish, copied from spec §8 — one subject, box-pleat's favourable 1/68-grid rationals, `INTERIOR_EPS` calibrated on TreeMaker bases, `direct` excluded.

**Every figure must appear in `exact-arrangement.json`.** Mark derived values as derived and show their operands. If a figure cannot be sourced, remove it.

- [ ] **Step 5: Verify every README figure against the JSON**

Write a throwaway check that asserts each number in the README appears in the JSON, and run it. Report the result.

- [ ] **Step 6: Commit**

---

## Self-Review

**1. Spec coverage.** §1 (why) → Task 4 Step 4 README section 1. §2 (scope/placement) → the File Structure, all under `docs/`. §3 (the port, the epsilon table, the fidelity rule, rationalizing input) → Task 1 Steps 1-4 and Task 3 Steps 1-3. §4 (the comparison, both directions, the direction-of-difference classification, margins) → Task 2 Step 1 and Task 3 Step 4. §5 (three guards) → Task 1 Step 3 (fidelity), Task 2 Step 2 (non-empty), Task 4 Step 1 (seeded disagreement), all three exercised by `--selftest`. §6 (outcomes) → Task 4 Step 2's three verdict branches. §7 (validation) → Task 4 Step 3. §8 (limits) → Task 4 Step 4 section 6.

**2. Placeholder scan.** No TBD/TODO. Task 3 Step 4 asks the implementer to transcribe `_segs_interact` by reading it rather than giving the code — that is deliberate and bounded: the function is short, the transcription discipline is fully specified by the five examples preceding it, and reproducing it here would be copying a function whose current text the implementer must read anyway to transcribe faithfully.

**3. Type consistency.** `Kernel`'s eight fields are defined in Task 1 and consumed by name in Tasks 1 and 3. `MarginLog.record/minimums` defined Task 1, used Tasks 2 and 4. `geom.cells(polys, K, log=None)` has the same arity at all five call sites. `build.build(result, polys_k, cells_list, K) -> (pairs, eqs, tacos)` matches its single call site. `canon_cells`, `as_tuples`, `load`, `require_nonempty` are defined once and used across Tasks 1-4 with consistent signatures.
