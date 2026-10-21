"""Partial layer order of a flat-folded state (folded-state-first
slice 2): which face is forced above which by the non-crossing
conditions (crease direction, taco-tortilla, tortilla-tortilla,
taco-taco), propagated to fixpoint. Forced relations are facts;
anything else is honestly None / AmbiguousStack — no search, no
invented tie-breaks.

The constraint families follow Akitaya, Demaine & Ku, "Computing
Flat-Folded States" (OSME 2024): antisymmetry (structural here — one
canonical variable per unordered face pair, see _lit), transitivity,
tortilla-tortilla, taco-tortilla, taco-taco. This module derives FORCED
relations only; it does NOT decide whether a total order exists, so
"no contradiction" is weaker than ADK's satisfiability result.

⚠ The error direction is deliberate and load-bearing: every family is
gated on membership in `pairs`, which comes from the arrangement cells,
and AREA_EPS drops sliver cells. A dropped cell REMOVES constraints and
can never manufacture one, so this oracle UNDER-refutes. A refutation
that survives it is therefore strong evidence; a pass is not a proof.

Spec: docs/superpowers/specs/2026-07-04-layer-order-slice2-design.md
      docs/superpowers/specs/2026-08-06-mv-symmetrize-design.md §2 (S2′a,
      the tortilla families this module used to drop with its F filter)
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import cmp_to_key
from itertools import combinations
from typing import Callable

import numpy as np

from .flat_fold import FlatFoldResult

#: ⚠ MEASURED ON SIX SUBJECTS AND DELIBERATELY LEFT ALONE (U20, 2026-08-17).
#: #128 named this constant the suspect for the sigma-search's remaining
#: cross-platform divergence -- min cell areas of 1.07e-09..1.75e-09 against a
#: 1e-9 threshold, "under a 2x margin" -- and deferred it for want of the
#: multi-base study. The study was run (`probe_sigma_platform.py`, six
#: subjects, macOS/arm64 vs linux/amd64) and it CLEARS this constant:
#:
#:   * it really does straddle. Minimum cell areas land at 1.02e-09..1.75e-09,
#:     and the CELL COUNT differs wildly by platform -- hshape 4 vs 17,
#:     two-level-tree 2 vs 5, template-quadruped 19 vs 34, star-6 26 vs 45.
#:   * but the straddle is causally INERT, for a structural reason. Every
#:     constraint family is gated on `pairs`, and `pairs` is a set of PAIRS
#:     drawn from cell COVERS -- a sliver's cover is a subset of the cover of
#:     the cell it was split from, so dropping it removes no pair. Measured:
#:     `pairs` is IDENTICAL across platforms on star-4-sym (28/28), star-6
#:     (190/190) AND template-bird (196/196) -- all three subjects whose
#:     search DIVERGES.
#:   * where `pairs` does move, the search AGREES: two-level-tree (56 vs 72)
#:     and template-quadruped (92 vs 98) both serve the identical symmetrized
#:     assignment on both platforms.
#:
#: So the hypothesis "a dropped cell changes `pairs`, which changes which
#: sigma-targets pass" is falsified in the strongest available way: it fires
#: HARDEST exactly where the outcome does not move, and NOT AT ALL (23/23
#: cells, min area 1.378e-06 -- a thousand times this threshold) on
#: `template-bird`, where it does. The divergence was conjunct 4; see
#: `mv_symmetrize.serve_rank`.
AREA_EPS = 1e-9   # cells/pieces smaller than this are dropped as noise
GEOM_EPS = 1e-9   # segment / clipping tolerance

#: How far inside a face's boundary a point must sit before `_strictly_inside`
#: calls it INTERIOR -- and therefore before `_spanning` emits a taco-tortilla
#: or tortilla-tortilla constraint through that face.
#:
#: ⚠ SPLIT OUT OF `GEOM_EPS` (was 1e-9) BECAUSE 1e-9 IS BELOW THIS QUANTITY'S
#: CROSS-PLATFORM NOISE FLOOR, WHICH MADE THE ORACLE FABRICATE CONSTRAINTS ON
#: LINUX. This module's stated error direction is to UNDER-refute ("a dropped
#: cell REMOVES constraints and can never manufacture one"), and at 1e-9 it
#: broke that promise in the one direction the docstring rules out.
#:
#: The scalar compared is a CROSS PRODUCT -- an AREA, |edge| x signed distance
#: -- not a distance, so it inherits the packed coordinates' roundoff
#: multiplied by an edge length. TreeMaker's ALM optimizer (archived; this
#: constant was derived on its output) emitted vertices that agree between
#: macOS/Accelerate and Linux/OpenBLAS only to ~1e-9 (project memory
#: `rigid-frozen-hash-platform-divergence`), which landed the noise ON the old
#: threshold.
#:
#: DERIVED FROM MEASUREMENT, NOT TASTE (probe_layer_margin.py, on
#: `template-quadruped`'s root-8 winner -- the exact base whose Linux
#: `oracles_ok` refusal this constant was found through). Over the 181 triples
#: `_spanning` considers:
#:
#:   * NOISE CEILING 3.238e-09 -- the largest |inside_min| among the 27 triples
#:     whose emitted-verdict differed between the two platforms. macOS computes
#:     these as exactly 0.0 or ~1e-17 (the crease genuinely runs ALONG the
#:     face's boundary); Linux computes the same degenerate configuration as
#:     1e-9..3.2e-9 and, at the old threshold, called it an interior crossing.
#:   * SIGNAL FLOOR 8.365e-04 -- the smallest |inside_min| among the 64 triples
#:     BOTH platforms agree are real interior crossings.
#:   * The gap between them is a factor of 258,000, and it is empty.
#:
#: On that base every threshold in [5e-9, 1e-4] makes the two platforms emit
#: the IDENTICAL 64-constraint set (set difference 0, one-platform-only triples
#: included).
#:
#: ⚠ AND THE UPPER HALF OF THAT WINDOW IS A LIE, BECAUSE ONE BASE IS NOT A
#: SIGNAL FLOOR. `probe_interior_window.py` re-measured over four bases: the
#: calibration base loses NOTHING at any threshold up to 1e-6 (which is exactly
#: why its gap looked empty), while the far denser `COMPOSED_NODES` root pool
#: -- 1478-2775 triples per arm against this base's 164 -- carries constraints
#: continuously from ~1e-9 upward and loses 17-95 per arm at 5e-9 alone. Code
#: review measured the consequence at 1e-6 directly: constraints at 3.21e-08,
#: 5.27e-08, 4.67e-07 and 6.41e-07 are deleted and `root_rank.oracles_ok` flips
#: refuse -> ACCEPT on 5 of 6 arms, each previously refused by a NAMED
#: contradiction. That is this gate going vacuous on macOS, the platform that
#: never had a fabrication problem -- a strictly worse bug than the one being
#: fixed.
#:
#: SO THE CONSTANT IS BOUNDED FROM BOTH SIDES BY MEASUREMENT, AND THE WINDOW IS
#: ONE ORDER WIDE, NOT FIVE:
#:
#:   lower  3.238e-09  the cross-platform noise ceiling (above)
#:   upper  3.21e-08   the smallest constraint any measured base carries that
#:                     is NOT in the degenerate band
#:
#: 1e-8 is the geometric centre of THAT window -- 3.1x above the noise, 3.2x
#: below the smallest defensible constraint. It is deliberately the SMALLEST
#: correction that closes the measured fabrication, not the most comfortable
#: one: everything it drops has a margin <= 1e-8 (smallest 1.01e-09), i.e. sits
#: in the same degenerate band whose macOS values are exactly 0.0 and 1e-17.
#:
#: ⚠ WHAT THIS DOES **NOT** FIX, STATED SO NOBODY INFERS IT. `layer_order` is
#: NOT platform-identical after this change and no epsilon here can make it so.
#: Measured in the same sweep, the number of triples `_spanning` even CONSIDERS
#: differs by platform on most arms (`template-quadruped` arm0 316 vs 308,
#: `template-bird` arm2 700 vs 688, COMPOSED arm1 2775 vs 2215) -- that is
#: `pairs` membership from `_cells` and `_clip_seg`, UPSTREAM of this test, and
#: it is driven by the packer's own ~1e-9 coordinate divergence. This constant
#: fixes one measured, attributable fabrication; it does not buy determinism.
#:
#: ⚠ THE WINDOW ABOVE IS NARROWER THAN THE CORPUS, AND THE CONSTANT SITS
#: INSIDE AN OVERLAP RATHER THAN INSIDE A GAP (U20, 2026-08-17). Re-measured
#: over EVERY `cases.py` subject plus the COMPOSED root pool -- 110,047 triples
#: across both platforms, `probe_interior_distance.py`:
#:
#:   noise ceiling   7.06e-08   (star-6, whose PACKED COORDINATES differ across
#:                               platforms by 2.58e-07, median 1.03e-07 --
#:                               where template-bird's differ by exactly 1e-09)
#:   signal floor    1.008e-08  (smallest margin both platforms agree is real)
#:
#: Those bands OVERLAP by a factor of 7. The four-base "3.238e-09 .. 3.21e-08"
#: window above is real but is not the whole corpus, and no scalar AREA
#: threshold separates star-6's noise from the constraints other bases carry.
#: 1e-8 remains the best available compromise -- it is what both platforms'
#: full suites pass on -- but it is NOT a separating threshold, and a future
#: reader must not size anything as if it were.
#:
#: ⚠ AND THE COMPARISON IS DIMENSIONALLY WRONG, WHICH BOUNDS HOW GOOD ANY
#: SCALAR HERE CAN BE. The scalar is an AREA (|edge| x distance), so the
#: EFFECTIVE clearance this constant demands scales as 1/|edge|. Measured over
#: the same corpus, the length scale `area/dist` spans 5.04e-04 (smallest) to
#: 1.53e-01 (median), i.e. at a fixed 1e-8 the effective DISTANCE threshold
#: ranges 6.55e-08 .. 1.99e-05 -- a 300x spread, and at the 1st percentile
#: (1.85e-06) it is within 1.7x of the corpus's smallest real distance signal
#: (3.2138e-06). Code review reached this independently and predicted real
#: constraints on slivery faces being dropped. MEASURED: zero of 110,047
#: triples realise it (no triple has `dist > 1e-6` while `area <= 1e-8`), so
#: the failure mode is unrealised -- but the margin is thin, not comfortable.
#:
#: ⚠ SO WHY NOT NORMALISE BY |edge| NOW? Because the scale-relative predicate's
#: window is EMPTY TOO, measured the same way (`probe_interior_predicate_ab.py`,
#: `probe_interior_window2.py`, 57 arms):
#:
#:   * clearing star-6's cross-platform noise needs a distance threshold above
#:     4.5713e-07;
#:   * at 2e-07 `root_rank.oracles_ok` ALREADY flips refuse -> ACCEPT on
#:     `read_base:COMPOSED` arm4 -- the exact anti-gaming regression #128
#:     shipped at 1e-6 and had to retract, reached one order lower.
#:
#: Normalising IS better posed (it cuts cross-platform `oracles_ok`
#: disagreements from 7 arms to 6 at 1e-7, and makes the measured window mean
#: something) and it remains the right eventual shape. It is not a fix for
#: star-6, and it cannot be adopted as one. star-6's symmetrized M/V is
#: recorded as tolerated-divergent in
#: `tests/test_mv_symmetrize.py::PLATFORM_DIVERGENT_SYMMETRIZE`.
#:
#: ⚠ ONE MORE CONSEQUENCE NOBODY WROTE DOWN: this constant is read by
#: `LayerOrder.stack_at` too, not only by `_spanning`. Every word of the
#: rationale above is about `_spanning`, but widening 1e-9 -> 1e-8 also
#: narrowed the covering set `stack_at` reports and changed when it raises
#: `AmbiguousStack`. `stack_at` is public and used by `probe_atdepth_stack.py`
#: and `probe_deep_hand.py`. Recorded rather than repaired: scoping the epsilon
#: to `_spanning`'s call site is a behaviour change to a second consumer and
#: belongs to whoever measures that consumer.
#:
#: ⚠ THIS IS THE THIRD INSTANCE OF ONE BUG CLASS IN THIS REPO, AND THE MEMORY
#: PREDICTED IT. `free_paper._TOL` (1e-7 -> 1e-5) and
#: `flex_extension.QNORM_FLOOR` (1e-10 -> 1e-9) were the same shape -- a
#: hardcoded epsilon calibrated to ONE platform's residual -- and
#: `linux-ci-3-failures-diagnosis-outcome` closes with "worth checking for a
#: third instance if more Linux-only flakes surface later". Any NEW hardcoded
#: geometric epsilon in this repo should be sized against a measured
#: cross-platform spread ON MORE THAN ONE BASE before it ships.
INTERIOR_EPS = 1e-8


class AmbiguousStack(ValueError):
    """stack_at() covering set is not totally ordered by FORCED
    relations; .free_pairs lists the genuinely unconstrained pairs."""

    def __init__(self, message: str, free_pairs: list):
        super().__init__(message)
        self.free_pairs = free_pairs


def _cross(u, v) -> float:
    return float(u[0] * v[1] - u[1] * v[0])


def _area(P: np.ndarray) -> float:
    x, y = P[:, 0], P[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def _is_convex(P: np.ndarray) -> bool:
    n = len(P)
    sign = 0
    for i in range(n):
        c = _cross(P[(i + 1) % n] - P[i], P[(i + 2) % n] - P[(i + 1) % n])
        if abs(c) < GEOM_EPS:
            continue
        s = 1 if c > 0 else -1
        if sign == 0:
            sign = s
        elif s != sign:
            return False
    return True


def _strictly_inside(p, P) -> bool:
    """p strictly interior to convex CCW polygon P (boundary excluded).

    Uses INTERIOR_EPS, not GEOM_EPS: see that constant for the measured
    cross-platform reason the two are no longer the same number. The margin
    returned by the comparison is an AREA (|edge| x distance), which is why it
    is sized against packed-vertex roundoff rather than against a coordinate.
    """
    q = np.asarray(p, dtype=float)
    n = len(P)
    return all(_cross(P[(i + 1) % n] - P[i], q - P[i]) > INTERIOR_EPS
               for i in range(n))


def _dedupe_ring(pts: list) -> np.ndarray:
    """Drop consecutive duplicate vertices (within GEOM_EPS), including the
    wrap-around pair. Degenerate zero-length edges (produced e.g. when a
    clip crossing lands exactly on an existing vertex — the normal case
    for crease-adjacent faces that share an edge) would otherwise persist
    as spurious polygon corners and, if fed into a later clip, risk a
    near-zero-length edge nearly parallel to the next clip line."""
    out = []
    for pt in pts:
        if not out or not np.allclose(pt, out[-1], atol=1e-9, rtol=0):
            out.append(pt)
    if len(out) >= 2 and np.allclose(out[0], out[-1], atol=1e-9, rtol=0):
        out.pop()
    if len(out) < 3:
        return np.empty((0, 2))
    return np.asarray(out)


def _clip_half(poly: np.ndarray, a, b) -> np.ndarray:
    """Clip a convex polygon to the closed half-plane LEFT of line a->b.

    Robust Sutherland-Hodgman: classify each vertex by its signed
    cross-distance to the line and add an intersection ONLY on a strict
    sign change (both endpoints beyond GEOM_EPS on opposite sides), using
    the stable barycentric form t = sp / (sp - sq). This never fabricates
    a crossing for a segment lying on or parallel to the clip line (where
    the distances are both ~0) — the failure mode of the earlier
    denom-based form, which on such segments produced mis-ordered or
    dropped vertices and hence non-convex / inverted output polygons."""
    d = b - a
    n = len(poly)
    s = [_cross(d, poly[i] - a) for i in range(n)]      # signed distances
    out = []
    for i in range(n):
        p, q = poly[i], poly[(i + 1) % n]
        sp, sq = s[i], s[(i + 1) % n]
        if sp >= -GEOM_EPS:
            out.append(p)
        if (sp > GEOM_EPS and sq < -GEOM_EPS) or \
           (sp < -GEOM_EPS and sq > GEOM_EPS):
            t = sp / (sp - sq)
            out.append(p + t * (q - p))
    return _dedupe_ring(out)


def _split_convex(subject: np.ndarray, clip: np.ndarray):
    """Partition convex `subject` by convex CCW `clip`: returns
    (intersection_or_None, outside_pieces). Pieces are convex and,
    together with the intersection, partition the subject (up to
    AREA_EPS slivers, which are dropped)."""
    pieces = []
    remaining = subject
    n = len(clip)
    for i in range(n):
        a, b = clip[i], clip[(i + 1) % n]
        if len(remaining) < 3:
            break
        outside = _clip_half(remaining, b, a)   # right of a->b
        if len(outside) >= 3 and abs(_area(outside)) > AREA_EPS:
            pieces.append(outside)
        remaining = _clip_half(remaining, a, b)
    inter = (remaining if len(remaining) >= 3
             and abs(_area(remaining)) > AREA_EPS else None)
    return inter, pieces


def _cells(polys: list) -> list:
    """Arrangement cells of a set of convex CCW polygons: maximal
    regions with a constant covering set, as (polygon, frozenset).

    Robust bounding-box overlay: start with ONE cell covering a box that
    contains every face (cover = empty) and cut it by each face in turn.
    Splitting a cell by a face partitions it into the part inside the
    face (cover gains fi) and the part(s) outside (cover unchanged) via a
    SINGLE `_split_convex` — so the children exactly tile the parent and
    gaps are structurally impossible. Cells disjoint from a face
    (`inter is None`) are kept WHOLE, never fragmented, which bounds the
    cell count (no cutting along a disjoint polygon's extended edge lines
    and hence no combinatorial blow-up). Exterior cells (cover stays
    empty) are dropped at the end.

    An earlier incremental variant computed the new face's uncovered
    remainder by a SEPARATE clip process (subtracting previous faces),
    independent of the intersection pieces; the two boundaries drifted by
    ~1e-16 per clip and, accumulated over dozens of faces, left thin
    sliver GAPS along the seams (the silent holes at high face counts).
    Partitioning a common parent removes that second process entirely."""
    if not polys:
        return []
    allpts = np.concatenate([np.asarray(p, dtype=float) for p in polys])
    lo = allpts.min(0) - 1.0
    hi = allpts.max(0) + 1.0
    box = np.array([[lo[0], lo[1]], [hi[0], lo[1]],
                    [hi[0], hi[1]], [lo[0], hi[1]]])
    cells: list = [(box, frozenset())]
    for fi, poly in enumerate(polys):
        new = []
        for cpoly, cover in cells:
            inter, outs = _split_convex(cpoly, poly)
            if inter is None:
                new.append((cpoly, cover))          # disjoint: keep whole
                continue
            new.append((inter, cover | frozenset({fi})))
            new.extend((o, cover) for o in outs)
        cells = new
    return [(cpoly, cover) for cpoly, cover in cells if cover]


def _orientation(T: np.ndarray) -> int:
    """+1 = face-up (even number of reflections), -1 = face-down."""
    return 1 if float(np.linalg.det(T[:2, :2])) > 0 else -1


def _lit(x: int, f: int):
    """Literal for the proposition 'face x is above face f', expressed
    over the canonical pair variable rel[(lo,hi)] = 'lo above hi'.
    Returns (pair, flip): the proposition's value is rel[pair] != flip."""
    return ((x, f), False) if x < f else ((f, x), True)


def _clip_seg(seg, poly: np.ndarray):
    """Parametric span (t0,t1) of the segment inside a convex CCW
    polygon, or None when the intersection is empty/degenerate."""
    p0 = np.asarray(seg[0], dtype=float)
    d = np.asarray(seg[1], dtype=float) - p0
    t0, t1 = 0.0, 1.0
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        e = b - a
        denom = _cross(e, d)
        num = _cross(e, p0 - a)          # >0: p0 on the inside of edge
        if abs(denom) < GEOM_EPS:
            if num < -GEOM_EPS:
                return None              # parallel and fully outside
            continue
        t = -num / denom
        if denom > 0:
            t0 = max(t0, t)
        else:
            t1 = min(t1, t)
    return (t0, t1) if t1 - t0 > GEOM_EPS else None


def _segs_interact(s1, s2) -> bool:
    """True when the segments properly cross, or are collinear with
    overlapping interiors (endpoint-touching does not count)."""
    p, q = np.asarray(s1[0], float), np.asarray(s1[1], float)
    r, s = np.asarray(s2[0], float), np.asarray(s2[1], float)
    d1, d2 = q - p, s - r
    o1, o2 = _cross(d1, r - p), _cross(d1, s - p)
    o3, o4 = _cross(d2, p - r), _cross(d2, q - r)
    if all(abs(o) < GEOM_EPS for o in (o1, o2, o3, o4)):
        length = float(np.hypot(*d1))
        if length < GEOM_EPS:
            return False
        u = d1 / length
        b0, b1 = sorted((float(np.dot(r - p, u)), float(np.dot(s - p, u))))
        return min(length, b1) - max(0.0, b0) > GEOM_EPS
    strad1 = (o1 > GEOM_EPS and o2 < -GEOM_EPS) or \
             (o1 < -GEOM_EPS and o2 > GEOM_EPS)
    strad2 = (o3 > GEOM_EPS and o4 < -GEOM_EPS) or \
             (o3 < -GEOM_EPS and o4 > GEOM_EPS)
    return strad1 and strad2


def _collinear_overlap(s1, s2) -> bool:
    """True when both segments lie on ONE line and their interiors overlap.

    The collinear branch of _segs_interact, split out because the tortilla
    families need it ALONE: a transversal crossing puts part of each
    segment strictly inside the other's faces and is therefore already
    covered by the spanning-face rule, whereas a shared segment is not
    (each face's boundary runs along it, so _strictly_inside is False by
    construction)."""
    p, q = np.asarray(s1[0], float), np.asarray(s1[1], float)
    r, s = np.asarray(s2[0], float), np.asarray(s2[1], float)
    d1, d2 = q - p, s - r
    o = (_cross(d1, r - p), _cross(d1, s - p),
         _cross(d2, p - r), _cross(d2, q - r))
    if any(abs(x) >= GEOM_EPS for x in o):
        return False
    length = float(np.hypot(*d1))
    if length < GEOM_EPS:
        return False
    u = d1 / length
    b0, b1 = sorted((float(np.dot(r - p, u)), float(np.dot(s - p, u))))
    return min(length, b1) - max(0.0, b0) > GEOM_EPS


def _side_of(poly: np.ndarray, a: np.ndarray, u: np.ndarray) -> int:
    """Which side of the unit-direction line through `a` a CONVEX polygon
    sits on: +1 left, -1 right, 0 when its centroid lands ON the line.

    CONTRACT: only ever asked about a polygon that has this line's segment
    as one of its OWN edges, so it lies wholly on one side and the
    centroid's signed distance is a sound witness. (Called on a face that
    straddles the line it would answer confidently and wrongly — every
    call site below picks its faces from a shared edge for that reason.)
    0 means degenerate and the caller drops the constraint: the module's
    error direction is to UNDER-refute, never to guess a side."""
    c = np.mean(poly, axis=0)
    d = _cross(u, c - a)
    return 0 if abs(d) < GEOM_EPS else (1 if d > 0 else -1)


def _unit(seg):
    d = np.asarray(seg[1], float) - np.asarray(seg[0], float)
    n = float(np.hypot(*d))
    return None if n < GEOM_EPS else d / n


def needs_flat_edge(provenance) -> bool:
    """True for a constraint that exists only because an UNFOLDED (F)
    shared edge does — i.e. one of the three families this module used to
    drop wholesale via `if a not in ("M","V"): continue`.

    Every such provenance names a "flat edge"; the pre-existing families
    name a "crease ... through face". Exposed rather than re-grepped by
    callers so the required-fail test can isolate the new families as the
    CAUSE of a refutation instead of merely observing one."""
    return "flat edge" in str(provenance)


@dataclass(frozen=True)
class Prov:
    """Why a relation is forced. `text` is the message this module has
    always produced -- every site interpolates provenance into an f-string,
    so __str__ keeps those byte-identical -- and `creases`/`faces` carry the
    same facts structurally, so a caller can build a no-good clause without
    parsing English."""
    text: str
    creases: tuple = ()
    faces: tuple = ()

    def __str__(self) -> str:
        return self.text


@dataclass(frozen=True)
class DirectSlot:
    """Where an M/V label enters the system: one per creased shared edge
    whose faces overlap. `val = (label == "V") == (sign == 1)`."""
    edge: tuple
    lit: tuple
    sign: int
    faces: tuple


class LayerContradiction(ValueError):
    """A contradiction, with the provenance that raised it and -- when
    `propagate(deps=True)` tracked them -- the creases whose labels it
    depends on. Subclasses ValueError and formats identically, so every
    existing `except ValueError` and every message assertion still holds."""

    def __init__(self, prov, deps=None):
        super().__init__(f"layer-order contradiction via {prov}")
        self.prov = prov
        self.deps = deps


@dataclass(frozen=True)
class _Constraints:
    pairs: frozenset      # canonical overlapping face pairs
    direct: tuple         # (lit, value, provenance)
    equalities: tuple     # (litA, litB, provenance): values must be equal
    tacos: tuple          # ((p,q),(r,s), prov): between(r;p,q)==between(s;p,q)
    covers: tuple         # frozenset per cell
    slots: tuple = ()     # DirectSlot per creased shared edge in `pairs`


def _build_constraints(result: FlatFoldResult, polys: list,
                       cells: list) -> _Constraints:
    covers = tuple(c for _, c in cells)
    pairs = frozenset(pr for c in covers
                      for pr in combinations(sorted(c), 2))
    orient = [_orientation(T) for T in result.transforms]

    def _seg_of(fa, k):
        face = result.faces[fa]
        i0, i1 = face.index(k[0]), face.index(k[1])
        return (np.asarray(result.folded_vertices[fa][i0], float),
                np.asarray(result.folded_vertices[fa][i1], float))

    # A shared edge is a TACO when it folds (M/V: flat_fold reflects across
    # it, so both faces land on one side) and a TORTILLA otherwise (F, and
    # anything else flat_fold gave the identity transform to — the layer
    # order describes the state flat_fold actually built, so the two splits
    # must agree edge for edge).
    creases, tortillas = [], []
    for fa, fb, k, a in result.shared_edges:
        if a in ("M", "V"):
            creases.append((fa, fb, a, _seg_of(fa, k), k))
        else:
            tortillas.append((fa, fb, _seg_of(fa, k), k))

    direct, eqs, tacos, slots = [], [], [], []

    def _spanning(seg, fa, fb, prov):
        """A face whose INTERIOR the segment passes through cannot lie
        between the segment's two faces. With (fa,fb) a taco this is
        Justin's taco-tortilla; with (fa,fb) a flat pair it is
        tortilla-tortilla. Identical equation, so identical code."""
        for x in range(len(polys)):
            if x in (fa, fb):
                continue
            if tuple(sorted((x, fa))) not in pairs:
                continue
            if tuple(sorted((x, fb))) not in pairs:
                continue
            span = _clip_seg(seg, polys[x])
            if span is None:
                continue
            mid = seg[0] + ((span[0] + span[1]) / 2.0) * (seg[1] - seg[0])
            if not _strictly_inside(mid, polys[x]):
                continue     # segment lies ON x's boundary: no tortilla
            eqs.append((_lit(x, fa), _lit(x, fb),
                        Prov(f"{prov} through face {x}",
                             creases=prov.creases, faces=prov.faces + (x,))))

    for fa, fb, a, seg, k in creases:
        if tuple(sorted((fa, fb))) in pairs:
            # Crease direction: a V fold (toward +z, seen from the
            # face-up side) puts the neighbor ABOVE the reference face;
            # M puts it below; a face-down reference flips the sense.
            # (Sign convention pinned by the hand-derived strip test.)
            val = (a == "V") == (orient[fa] == 1)   # "fb above fa"
            direct.append((_lit(fb, fa), val,
                           Prov(f"crease {k} {a}", creases=(k,), faces=(fa, fb))))
            slots.append(DirectSlot(edge=k, lit=_lit(fb, fa),
                                    sign=orient[fa], faces=(fa, fb)))
        _spanning(seg, fa, fb, Prov(f"taco-tortilla crease {k}",
                                    creases=(k,), faces=(fa, fb)))
    for fa, fb, seg, k in tortillas:
        _spanning(seg, fa, fb, Prov(f"tortilla-tortilla flat edge {k}",
                                    faces=(fa, fb)))

    # Shared-segment families. A flat pair's two faces sit on OPPOSITE
    # sides of their edge, so they are invisible to _spanning above (each
    # one's boundary runs along the segment) and need the side bookkeeping
    # below instead.
    for fa, fb, a, seg, k in creases:
        u = _unit(seg)
        if u is None:
            continue
        sa, sb = (_side_of(polys[fa], seg[0], u),
                  _side_of(polys[fb], seg[0], u))
        if sa == 0 or sa != sb:
            continue          # not a fold-back onto one side: no taco here
        for ta, tb, tseg, tk in tortillas:
            if not _collinear_overlap(seg, tseg):
                continue
            for x in (ta, tb):
                if x in (fa, fb):
                    continue
                if _side_of(polys[x], seg[0], u) != sa:
                    continue  # the far half of the sheet: not over the taco
                if tuple(sorted((x, fa))) not in pairs:
                    continue
                if tuple(sorted((x, fb))) not in pairs:
                    continue
                eqs.append((_lit(x, fa), _lit(x, fb),
                            Prov(f"taco-tortilla crease {k} along flat edge {tk}",
                                 creases=(k,), faces=(x, fa, fb))))
    for t1, t2 in combinations(tortillas, 2):
        (a1, a2, s1, k1), (b1, b2, s2, k2) = t1, t2
        if not _collinear_overlap(s1, s2):
            continue
        u = _unit(s1)
        if u is None:
            continue
        A = {_side_of(polys[f], s1[0], u): f for f in (a1, a2)}
        B = {_side_of(polys[f], s1[0], u): f for f in (b1, b2)}
        if set(A) != {1, -1} or set(B) != {1, -1}:
            continue          # a degenerate side reading: drop, never guess
        if A[1] in (B[1], B[-1]) or A[-1] in (B[1], B[-1]):
            continue
        if any(tuple(sorted((A[s], B[s]))) not in pairs for s in (1, -1)):
            continue
        # Two uncreased sheets crossing one segment keep their order: the
        # relation on the left half equals the relation on the right.
        eqs.append((_lit(A[1], B[1]), _lit(A[-1], B[-1]),
                    Prov(f"tortilla-tortilla flat edges {k1}x{k2}",
                         faces=(A[1], B[1], A[-1], B[-1]))))
    for c1, c2 in combinations(creases, 2):
        fa1, fb1, _, s1, k1 = c1
        fa2, fb2, _, s2, k2 = c2
        if not _segs_interact(s1, s2):
            continue
        quad = ((fa2, fa1), (fa2, fb1), (fb2, fa1), (fb2, fb1))
        if any(tuple(sorted(pq)) not in pairs for pq in quad):
            continue
        tacos.append(((fa1, fb1), (fa2, fb2),
                      Prov(f"taco-taco {k1}x{k2}", creases=(k1, k2),
                           faces=(fa1, fb1, fa2, fb2))))
        tacos.append(((fa2, fb2), (fa1, fb1),
                      Prov(f"taco-taco {k2}x{k1}", creases=(k2, k1),
                           faces=(fa2, fb2, fa1, fb1))))
    return _Constraints(pairs=pairs, direct=tuple(direct),
                        equalities=tuple(eqs), tacos=tuple(tacos),
                        covers=covers, slots=tuple(slots))


def _covers_of(cons: _Constraints) -> dict:
    """face -> the set of cell indices whose cover contains it. Transitivity
    only holds where all three faces are stacked over ONE cell, so a
    derivation is admissible exactly when the three faces share a cover."""
    out: dict = {}
    for ci, cover in enumerate(cons.covers):
        for x in cover:
            out.setdefault(x, set()).add(ci)
    return out


def _close_transitively(rel: dict, get: Callable, put: Callable,
                        covers_of: dict, up: dict, down: dict) -> bool:
    """Worklist transitive closure, replacing a per-round enumeration of
    every ordered triple of every cover (measured 2026-09-22: 7.98 s of an
    8.00 s propagate on octopus). `up[x]` holds every y with "x above y"
    already seen and `down` its inverse; a pair only needs closing once, so
    each round processes the pairs that became true since the last one.

    NOT confluent, by design of the write guard below: both this closure and
    the triple loop it replaces write a pair only when it is currently
    unknown (`get(...) is None`), so two independently admissible derivation
    chains that imply opposite values for one pair never cross-check -- the
    fixpoint depends on traversal order (spec section 10, measured on
    mesh-humanoid). That guard is kept deliberately, so this is a pure
    traversal-order change and not also a change to the rule. On every input
    measured it lost none the old order found -- the 10 box-pleat subjects
    keep verdict AND witness, and all 6 differing mesh-humanoid flip-sets
    moved consistent -> contradiction, never the reverse -- but that is a
    measurement, not a theorem: once the rule is order-dependent, neither
    direction is ruled out a priori. A reported contradiction is entailed by
    the bedrock facts -- every step here is sound -- but "no contradiction"
    is not a proof of flat-foldability, only that this traversal found none;
    this module already documents that under-refutal for AREA_EPS-dropped
    cells, and non-confluence is a second, independent reason for it."""
    pending = []

    def note(x, y):
        if y in up.setdefault(x, set()):
            return
        up[x].add(y)
        down.setdefault(y, set()).add(x)
        pending.append((x, y))

    for (lo, hi), v in list(rel.items()):
        note(lo, hi) if v else note(hi, lo)
    changed = False
    while pending:
        x, y = pending.pop()
        cx, cy = covers_of.get(x, ()), covers_of.get(y, ())
        cxy = set(cx) & set(cy)
        for z in list(up.get(y, ())):                      # x > y > z
            if covers_of.get(z, set()) & cxy and get(_lit(x, z)) is None:
                changed |= put(_lit(x, z), True,
                               Prov(f"transitivity {x}>{y}>{z}", faces=(x, y, z)),
                               srcs=(_lit(x, y), _lit(y, z)))
                note(x, z)
        for w in list(down.get(x, ())):                    # w > x > y
            if covers_of.get(w, set()) & cxy and get(_lit(w, y)) is None:
                changed |= put(_lit(w, y), True,
                               Prov(f"transitivity {w}>{x}>{y}", faces=(w, x, y)),
                               srcs=(_lit(w, x), _lit(x, y)))
                note(w, y)
    return changed


def _propagate(cons: _Constraints, *, deps: bool = False) -> dict:
    """Fixpoint propagation. Returns rel: {(lo,hi): bool} for FORCED
    pairs only. Raises LayerContradiction (a ValueError) on contradiction.

    With deps=True every derived literal also carries the set of creases
    whose LABELS it depends on, and a contradiction reports the union over
    the two conflicting derivations: that set is a sound no-good clause,
    because the conflict follows from exactly those label decisions."""
    rel: dict = {}
    dep: dict = {}

    def get(lit):
        pair, flip = lit
        v = rel.get(pair)
        return None if v is None else (v != flip)

    def _dep_of(prov, srcs):
        if not deps:
            return None
        out = set(prov.creases)
        for pair, _ in srcs:
            out |= dep.get(pair, frozenset())
        return frozenset(out)

    def put(lit, value, prov, srcs=()) -> bool:
        pair, flip = lit
        v = (value != flip)
        d = _dep_of(prov, srcs)
        if pair in rel:
            if rel[pair] != v:
                raise LayerContradiction(
                    prov, None if not deps else d | dep.get(pair, frozenset()))
            return False
        rel[pair] = v
        if deps:
            dep[pair] = d
        return True

    for lit, val, prov in cons.direct:
        put(lit, val, prov)
    covers_of = _covers_of(cons)
    up: dict = {}
    down: dict = {}
    changed = True
    while changed:
        changed = False
        for la, lb, prov in cons.equalities:
            va, vb = get(la), get(lb)
            if va is None and vb is not None:
                changed |= put(la, vb, prov, srcs=(lb,))
            elif vb is None and va is not None:
                changed |= put(lb, va, prov, srcs=(la,))
            elif va is not None and vb is not None and va != vb:
                raise LayerContradiction(
                    prov, None if not deps
                    else (dep.get(la[0], frozenset()) | dep.get(lb[0], frozenset())
                          | frozenset(prov.creases)))
        for (p, q), (r, s), prov in cons.tacos:
            lits = (_lit(r, p), _lit(r, q), _lit(s, p), _lit(s, q))
            vals = [get(li) for li in lits]
            known = [v is not None for v in vals]
            if all(known):
                if (vals[0] != vals[1]) != (vals[2] != vals[3]):
                    raise LayerContradiction(
                        prov, None if not deps
                        else frozenset(prov.creases).union(
                            *(dep.get(li[0], frozenset()) for li in lits)))
            elif sum(known) == 3:
                m = known.index(False)
                if m in (0, 1):
                    straddles = vals[2] != vals[3]
                    other = vals[1 - m]
                else:
                    straddles = vals[0] != vals[1]
                    other = vals[5 - m]
                changed |= put(lits[m],
                               (not other) if straddles else other,
                               prov, srcs=tuple(li for i, li in enumerate(lits)
                                                if i != m))
        changed |= _close_transitively(rel, get, put, covers_of, up, down)
    return rel


class LayerOrder:
    """Partial layer order: forced relations only (see module doc)."""

    def __init__(self, rel: dict, pairs: frozenset, cells: list,
                 polys: list):
        self._rel = rel
        self._pairs = pairs
        self._raw_cells = cells
        self._polys = polys

    @property
    def cells(self):
        return [(np.mean(poly, axis=0), cover)
                for poly, cover in self._raw_cells]

    def above(self, a: int, b: int):
        pr = (a, b) if a < b else (b, a)
        if a == b or pr not in self._pairs:
            return None
        v = self._rel.get(pr)
        if v is None:
            return None
        return v if a < b else (not v)

    def stack_at(self, p) -> list:
        cover = sorted(i for i, poly in enumerate(self._polys)
                       if _strictly_inside(p, poly))
        if not cover:
            return []
        free = [(a, b) for a, b in combinations(cover, 2)
                if self.above(a, b) is None]
        if free:
            raise AmbiguousStack(
                f"stack at {tuple(np.asarray(p))} has {len(free)} "
                f"unforced pair(s)", free)
        return sorted(cover, key=cmp_to_key(
            lambda a, b: -1 if self.above(a, b) else 1))


def _polys_of(result: FlatFoldResult) -> list:
    """Folded faces as CCW convex polygons (reflected faces wind CW)."""
    polys = []
    for i, P in enumerate(result.folded_vertices):
        P = np.asarray(P, dtype=float)
        if _area(P) < 0:
            P = P[::-1]
        if not _is_convex(P):
            raise ValueError(f"face {i} is non-convex; layer ordering "
                             f"supports convex faces only")
        polys.append(P)
    return polys


def layer_order(result: FlatFoldResult) -> LayerOrder:
    """Partial layer order of a consistent flat-folded state.

    Raises ValueError when the folded state is closure-inconsistent
    (layers only exist where the fold does), when a face is non-convex,
    or when constraint propagation derives a contradiction."""
    bad = result.closure.bad_edges
    if bad:
        raise ValueError(
            f"cannot order layers: folded state has {len(bad)} "
            f"closure-inconsistent edges (no consistent flat-fold "
            f"exists for this input)")
    polys = _polys_of(result)
    cells = _cells(polys)
    cons = _build_constraints(result, polys, cells)
    rel = _propagate(cons)
    return LayerOrder(rel, cons.pairs, cells, polys)


def constraints_for(result: FlatFoldResult):
    """The layer-order system for `result`, with the slots where M/V enters
    it. Everything except `_Constraints.direct` depends on the folded
    geometry alone, which `flat_fold` derives from the crease SET -- so a
    caller may re-propagate this same system under any other labelling of
    the same creases (spec §3). Returns (cons, slots).

    Refuses a closure-inconsistent folded state for the same reason
    `layer_order()` does: there is no consistent flat fold to order layers
    in, so the system built from it would be meaningless rather than merely
    unsatisfiable. Guarding here rather than in each caller, because both
    other entry points into this machinery already check (`layer_order`
    raises, `_LayerGate` sets `unavailable`) and a caller that forgets gets
    a plausible-looking answer."""
    bad = result.closure.bad_edges
    if bad:
        raise ValueError(
            f"cannot build a layer-order system: folded state has "
            f"{len(bad)} closure-inconsistent edges (no consistent "
            f"flat-fold exists for this input)")
    polys = _polys_of(result)
    cons = _build_constraints(result, polys, _cells(polys))
    return cons, cons.slots


def propagate(cons: _Constraints, *, deps: bool = False) -> dict:
    """Public `_propagate`: the forced relations, or LayerContradiction."""
    return _propagate(cons, deps=deps)
