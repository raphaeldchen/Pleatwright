"""Is layer_order's FLOAT arrangement correct? Re-derive it exactly and compare.

`layer_certify` states the limit of its own verdict in capitals: CERTIFIED IS
NOT FLAT-FOLDABLE, because `layer_order.AREA_EPS` drops sliver cells, and
"Closing that is separate work." This is that work in its smallest useful form.

The caveat names ONE epsilon; the arrangement rests on THREE -- AREA_EPS (1e-9,
measured inert on this subject by evidence section 16), GEOM_EPS (1e-9, never
measured) and INTERIOR_EPS (1e-8, never measured, and carrying a recorded
incident: at 1e-9 it "MADE THE ORACLE FABRICATE CONSTRAINTS ON LINUX").

WHAT LICENSES EVERY NUMBER BELOW. The transcription runs first in FLOAT mode
and must reproduce production's cells BITWISE: the same number of cells, in the
same order, each with the same cover, the same vertex count, and every vertex
coordinate equal under `==` (Python floats, so `==` is the bitwise test). Only
then is the kernel swapped. One variable changes, so a difference is arithmetic.
"""
from __future__ import annotations

import inspect
import json
import math
import os
import re
import resource
import sys
import time
from itertools import combinations

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "..", "..", "mcp_harness"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import flat_fold                      # noqa: E402
import layer_certify                  # noqa: E402
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


def bitwise_diff(prod, mine):
    """First difference between production's cells and the float
    transcription's, or None. Compares IN ORDER: cell count, then per cell the
    cover, the vertex count, and each vertex coordinate by `==`.

    Valid only for float-vs-float, where `==` on Python floats is the bitwise
    test. The exact-vs-float comparison (Task 2) uses `canon_cells` instead,
    because `Fraction` and `float` polygons legitimately differ.
    """
    if len(prod) != len(mine):
        return f"cell count: production {len(prod)}, transcription {len(mine)}"
    for i, ((ppoly, pcov), (mpoly, mcov)) in enumerate(zip(prod, mine)):
        if pcov != mcov:
            only_p, only_m = sorted(pcov - mcov), sorted(mcov - pcov)
            return (f"cell {i} cover: production has {len(pcov)} faces, "
                    f"transcription {len(mcov)}; production-only "
                    f"{only_p[:8]}, transcription-only {only_m[:8]}")
        if len(ppoly) != len(mpoly):
            return (f"cell {i} vertex count: production {len(ppoly)}, "
                    f"transcription {len(mpoly)}")
        for j, (pv, mv) in enumerate(zip(ppoly, mpoly)):
            for axis, (pc, mc) in enumerate(zip(pv, mv)):
                pc, mc = float(pc), float(mc)
                if pc != mc:
                    return (f"cell {i} vertex {j} {'xy'[axis]}: production "
                            f"{pc!r}, transcription {mc!r} "
                            f"(delta {mc - pc:.3e})")
    return None


def fidelity_gate():
    """FLOAT mode must reproduce production BITWISE. Nothing else runs until
    it does."""
    _ff, polys = load()
    prod = layer_order._cells(polys)
    mine = geom.cells(as_tuples(polys, kernel.FLOAT), kernel.FLOAT)
    if not prod or not mine:
        raise SystemExit(
            f"REFUSED: an empty arrangement makes the fidelity comparison "
            f"vacuous (production {len(prod)} cells, transcription "
            f"{len(mine)}). A gate that licenses everything after it must "
            f"first assert it compared something.")
    diff = bitwise_diff(prod, mine)
    if diff is not None:
        raise SystemExit(
            f"REFUSED: the float transcription does not reproduce production "
            f"bitwise. First difference -- {diff}. Until these agree the "
            f"exact result is uninterpretable -- a difference could be "
            f"arithmetic OR a divergent rewrite.")
    return {"production_cells": len(prod), "transcription_cells": len(mine),
            "bitwise_identical": True}


def pairs_of(cells_list):
    """`_build_constraints`'s derivation: every pair inside every cover."""
    return frozenset(pr for _poly, cover in cells_list
                     for pr in combinations(sorted(cover), 2))


def max_denominator(cells_list):
    """Denominator growth is the one feasibility risk; measure it, do not assume.

    ⚠ This is a REPORT over the OUTPUT cell polygons, not a gate, and not over
    the input. Spec section 3's second assertion -- every denominator divides
    the observed grid -- is `input_grid_gate`, which runs over the input
    coordinates and refuses.
    """
    best = 1
    for poly, _cover in cells_list:
        for x, y in poly:
            best = max(best, getattr(x, "denominator", 1),
                       getattr(y, "denominator", 1))
    return best


def arrangement_result():
    _ff, polys = load()
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
        # Named for their population. `constraints.n_only_float` is a SUM over
        # three families; this one is `pairs` alone, derived from the covers.
        # The two carried the same key name under two meanings until the final
        # review named it.
        "n_pairs_only_float": len(pf - pe),
        "n_pairs_only_exact": len(pe - pf),
        "margins": log.minimums(),
        "area_vertices_max": log.sizes.get("area_vertices"),
        "max_denominator": max_denominator(ex),
        "secs": secs,
    }


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


FAMILIES = ("pairs", "eqs", "tacos")

#: Every `census` tag `build.bump` can emit. The census dict is SEEDED with a
#: zero for each one before `build` runs, so that a row reading 0 is an
#: observed zero -- `bump` was never reached, or was reached with an increment
#: of 0 -- rather than a key `dict.get` defaulted. The `vacuous` list is then
#: derived from the census itself instead of from a second hand-kept list,
#: which is what previously let five of its seven entries rest on a default
#: reported as a measurement.
CENSUS_KEYS = (
    "clip_seg_calls", "collinear_overlap_calls", "creases",
    "eq_from_spanning", "eq_from_taco_tortilla_along_flat_edge",
    "eq_from_tortilla_tortilla", "segs_interact_calls", "side_of_calls",
    "side_of_returned_0", "strictly_inside_calls", "taco_from_taco_taco",
    "tortilla_pairs", "tortillas", "unit_calls", "unit_returned_None",
)


def seeded_census(build_mod):
    """`CENSUS_KEYS` as a zeroed dict, checked against `build.py`'s sources.

    A seeded zero is only honest if the key is a tag `build` really emits, and
    the census is only COMPLETE if every tag `build` emits is seeded. Both
    directions are read off the module's own source, so a renamed tag refuses
    here instead of silently reporting 0 forever, and a tag added without a
    seed refuses instead of being left out of `vacuous`.
    """
    src = open(build_mod.__file__).read()
    found = set(re.findall(r'bump\("([^"]+)"', src))
    want = set(CENSUS_KEYS)
    if found != want:
        raise SystemExit(
            f"REFUSED: `CENSUS_KEYS` does not match the `bump` tags in "
            f"{os.path.basename(build_mod.__file__)} -- in build.py only "
            f"{sorted(found - want)}, seeded here only {sorted(want - found)}. "
            f"A seeded zero that no site writes is not a measurement, and an "
            f"unseeded site is missing from the `vacuous` list.")
    return {k: 0 for k in CENSUS_KEYS}


# --------------------------------------------------------------------------
# Spec section 4's designated comparison: the clause set `layer_certify`
# actually consumes.
#
# `pairs`, `equalities` and `tacos` are the probe's own families; the spec
# names a fourth row, "the clause set from `layer_certify.clauses(cons)` --
# the real target, consumed by `verify`, `decide` and the SAT encoder alike",
# and that is what this block builds. It is NOT a sum of the three family
# counts: `clauses` turns `equalities` and `tacos` into one `Clause` each but
# turns `covers` into one TRANSITIVITY clause per distinct face triple, and it
# never reads `pairs` at all (`pairs` are the clause VARIABLES, not clauses).
# So the clause set is a different, much larger object, and comparing it is a
# genuinely separate check rather than an arithmetic consequence of the rows
# above it.
#
# `clauses` reads exactly three fields -- `equalities`, `covers`, `tacos`
# (`layer_certify._iter_clauses`). It does NOT read `direct`, `pairs` or
# `slots`, so excluding `direct` (this probe's design, limit 5) costs the
# comparison nothing and no `direct` has to be fabricated to make it run.
# --------------------------------------------------------------------------

#: The provenance string handed to every synthesised constraint. `Clause` is a
#: frozen dataclass, so `prov` participates in its `__eq__` -- but it is
#: English explaining why a clause exists, it is not geometry, `_satisfied`
#: never reads it, and this probe does not transcribe production's provenance
#: sites. Both arms get this same placeholder, so `prov` can neither mask a
#: difference nor manufacture one; the comparison below is over the clause's
#: semantic content, `(family, variables, flips)`.
CLAUSE_PROV = ""

#: Tag and arity per family, from `layer_certify._iter_clauses`. The arity is
#: asserted rather than assumed, because `clause_key`'s injectivity argument
#: rests on each family's key having a FIXED bit length.
CLAUSE_TAG = {"equality": 1, "transitivity": 2, "taco": 3}
CLAUSE_ARITY = {"equality": 2, "transitivity": 3, "taco": 4}

#: Bits per face index in a clause key. Asserted against the real indices.
CLAUSE_ID_BITS = 10


def clause_key(cl):
    """A `Clause`'s semantic content as one integer, injectively.

    4.6M clauses per arm is too many to hold as dataclass instances twice
    (`layer_certify.clauses` on this witness costs ~2 GB for ONE arm), so each
    clause is packed into an int and the two arms are compared as sets of
    those. Injectivity, which is what makes that substitution sound:

    * the key starts at `0b1<tag>`, so its bit length is fixed per family
      (equality 45, transitivity 66, taco 87) and no two families can collide;
    * within a family the face indices and flip bits occupy disjoint fixed
      fields, so distinct `(variables, flips)` give distinct keys.

    Both premises are CHECKED here, not asserted in prose: the arity against
    `CLAUSE_ARITY` and every index against `CLAUSE_ID_BITS`. `clause_keys`
    additionally reports the stream count beside the set size, so a collision
    would show up as a shortfall rather than as a silent agreement.
    """
    want = CLAUSE_ARITY[cl.family]
    if len(cl.variables) != want or len(cl.flips) != want:
        raise SystemExit(
            f"REFUSED: a {cl.family!r} clause carries {len(cl.variables)} "
            f"variables and {len(cl.flips)} flips, not {want}. `clause_key`'s "
            f"injectivity rests on a fixed arity per family, so the packing "
            f"is no longer trustworthy and the clause comparison would be "
            f"reporting a set it cannot distinguish.")
    k = 0b100 | CLAUSE_TAG[cl.family]
    for lo, hi in cl.variables:
        if not (0 <= lo < 1 << CLAUSE_ID_BITS and 0 <= hi < 1 << CLAUSE_ID_BITS):
            raise SystemExit(
                f"REFUSED: face index out of range for the clause key "
                f"({lo}, {hi} needs {CLAUSE_ID_BITS} bits). Widen "
                f"CLAUSE_ID_BITS; packing would otherwise alias two clauses.")
        k = ((k << CLAUSE_ID_BITS) | lo) << CLAUSE_ID_BITS | hi
    for f in cl.flips:
        k = (k << 1) | (1 if f else 0)
    return k


def constraints_of(pairs, eqs_ordered, tacos_ordered, cells_list):
    """A production `layer_order._Constraints` from this probe's families.

    `direct` and `slots` are empty by this probe's design (limit 5) and
    `clauses` reads neither.
    """
    return layer_order._Constraints(
        pairs=pairs,
        direct=(),
        equalities=tuple((a, b, CLAUSE_PROV) for a, b in eqs_ordered),
        tacos=tuple((a, b, CLAUSE_PROV) for a, b in tacos_ordered),
        covers=tuple(c for _poly, c in cells_list),
        slots=())


def clause_keys(cons):
    """`layer_certify.clauses(cons)` as a key set, with its per-family counts.

    Streams `layer_certify._iter_clauses` -- the generator `clauses` is a thin
    materialising wrapper over, whose own docstring states "the clause set the
    two produce is identical" -- because materialising the tuple costs ~2 GB
    per arm here and the comparison the spec asks for is set equality.
    Returns (keys, stream_count, per_family_counts).
    """
    keys, n, per = set(), 0, {}
    for cl in layer_certify._iter_clauses(cons):
        keys.add(clause_key(cl))
        per[cl.family] = per.get(cl.family, 0) + 1
        n += 1
    return keys, n, per


def clause_comparison(arms, cells):
    """Set equality over `layer_certify.clauses(cons)`, float vs exact.

    `arms[name]` is `(pairs, eqs_tuple, tacos_tuple)` in construction order and
    `cells[name]` the matching cell list. The two clause sets are compared in
    BOTH directions, never by containment.

    Cell ORDER does not have to match between the arms: `_iter_clauses`
    de-duplicates transitivity triples into a set, so the clause set is
    invariant under reordering `covers`, which is also why this is a set
    comparison and not a sequence one.
    """
    out, keysets = {}, {}
    for name in ("float", "exact"):
        pairs, eqs, tacos = arms[name]
        cons = constraints_of(pairs, eqs, tacos, cells[name])
        keysets[name], n, per = clause_keys(cons)
        out[f"clauses_{name}"] = len(keysets[name])
        out[f"clauses_{name}_streamed"] = n
        out[f"clauses_{name}_by_family"] = per
        if len(keysets[name]) != n:
            raise SystemExit(
                f"REFUSED: the {name} arm streamed {n:,} clauses but only "
                f"{len(keysets[name]):,} distinct keys. Either the clause set "
                f"carries duplicates or `clause_key` is aliasing two clauses; "
                f"either way a set comparison over these keys would report "
                f"agreement it has not established.")
    f, x = keysets["float"], keysets["exact"]
    out["clauses_identical"] = f == x
    out["clauses_only_float"] = len(f - x)
    out["clauses_only_exact"] = len(x - f)
    if f != x:
        # Keys are opaque ints, so a difference is re-streamed into readable
        # clauses. Only reached on a finding, so it costs nothing here.
        want = (f - x) | (x - f)
        sample = []
        for name in ("float", "exact"):
            pairs, eqs, tacos = arms[name]
            cons = constraints_of(pairs, eqs, tacos, cells[name])
            for cl in layer_certify._iter_clauses(cons):
                if clause_key(cl) in want:
                    sample.append(f"{name}: {cl.family} {cl.variables} "
                                  f"{cl.flips}")
                    if len(sample) >= 20:
                        break
            if len(sample) >= 20:
                break
        out["clauses_sample_differing"] = sample
    return out


def _lcm(dens):
    L = 1
    for d in dens:
        L = L * d // math.gcd(L, d)
    return L


def _dens_of(groups):
    dens = {1}
    for grp in groups:
        for P in grp:
            for x, y in P:
                dens.add(x.denominator)
                dens.add(y.denominator)
    return dens


def face_denominators(polys):
    """Denominators of the CLIPPING polygons (`_polys_of`, kernel-snapped)."""
    return _dens_of([as_tuples(polys, kernel.EXACT)])


def seg_denominators(result):
    """Denominators of the `_seg_of` source array (`folded_vertices`)."""
    import build as build_mod
    return _dens_of([build_mod._folded_of(result, kernel.EXACT)])


#: An lcm this large means `limit_denominator` RATIONALIZED NOISE instead of
#: recovering a grid, which would make the quantum argument vacuous while every
#: other gate stayed green. Three orders below `kernel.MAX_DEN` = 10**6 on
#: purpose: the point is to separate "a coarse grid" from "the cap".
GRID_DEN_CEILING = 10 ** 3


def grid_gate(base_dens, also_dens, base_name, also_name):
    """Spec section 3's SECOND assertion: the denominators divide the grid.

    `kernel._snap` asserts the first half -- no snap moved a coordinate by more
    than `SNAP_TOL`. That alone does not establish a grid: `limit_denominator`
    will return 731/999983 for a coordinate it barely moves, and the quantum
    argument in section 3 of the README rests entirely on the denominators
    being small AND SHARED. This is that assertion, and it refuses.

    It is deliberately NOT `L = lcm(everything); assert everything divides L`,
    which is true by construction and would assert nothing. The grid is taken
    over ONE population (the clipping polygons) and every denominator of a
    SECOND population (the `_seg_of` vertices the segment helpers read) is
    required to divide it. Two populations, one grid -- falsifiable, and the
    reason the final review could point at it: had this existed, asking "which
    population?" would have surfaced the THIRD one it does not cover
    (`QUANTUM_EXCLUDES`), which is where the run's tightest margin lives.
    """
    require_nonempty(**{base_name: len(base_dens), also_name: len(also_dens)})
    L = _lcm(base_dens)
    stray = sorted({d for d in also_dens if L % d})
    if stray:
        raise SystemExit(
            f"REFUSED: {len(stray)} denominator(s) in {also_name} do not "
            f"divide the grid observed on {base_name} (L={L}): {stray[:12]}. "
            f"The two populations are then on different grids, so the 1/L^2 "
            f"cross-product floor the README derives does not apply to the "
            f"predicates that read the second one.")
    if L > GRID_DEN_CEILING:
        raise SystemExit(
            f"REFUSED: the observed grid denominator L={L} exceeds "
            f"GRID_DEN_CEILING={GRID_DEN_CEILING}. A grid this fine means "
            f"`limit_denominator` rationalized float noise rather than "
            f"recovering a coarse grid, so 1/L^2 is no longer a floor worth "
            f"stating and the structural argument is vacuous.")
    return {"grid_denominator": L, "ceiling": GRID_DEN_CEILING,
            "grid_from": base_name, "checked_against": also_name,
            "distinct_denominators_grid": sorted(base_dens),
            "distinct_denominators_checked": sorted(also_dens)}


def input_grid_gate():
    """`grid_gate` over this probe's two INPUT coordinate populations."""
    ff, polys = load()
    return grid_gate(face_denominators(polys), seg_denominators(ff),
                     "clipping polygons (`_polys_of`)",
                     "`_seg_of` vertices (`folded_vertices`)")


def grid_gate_refuses():
    """Required-fail control for `grid_gate`'s stray-denominator branch."""
    try:
        grid_gate({68}, {999983}, "control grid", "control population")
    except SystemExit as exc:
        return {"refused": True, "message": str(exc)}
    raise SystemExit(
        "REFUSED: `grid_gate` accepted a population whose denominator does "
        "not divide the grid, so spec section 3's second assertion is inert.")


#: Which populations the 1/L grid argument COVERS. These are the coordinates
#: `grid_gate` certifies onto one grid, so a cross product of their differences
#: really is a multiple of 1/L^2 and an area a multiple of 1/(2L^2).
QUANTUM_COVERS = (
    "the clipping polygons `_polys_of` returns -- read by `clip_half`, "
    "`dedupe_ring` and `side_of`",
    "the `_seg_of` vertices in `folded_vertices` -- read by the segment "
    "helpers",
)

#: ...and which it does NOT. Both are derived quantities computed FROM the
#: grid, not points on it, so the structural argument supplies no floor for
#: them at all and their margins are MEASURED ONLY. The first carries the whole
#: `INTERIOR_EPS` population and this run's tightest margin.
QUANTUM_EXCLUDES = (
    "`build.spanning`'s `mid` (build.py:119-121) -- the clipped span's "
    "MIDPOINT, which is off the 1/L grid. `strictly_inside` is evaluated "
    "there and nowhere else, so INTERIOR_EPS has NO derived floor. Its "
    "observed `#kept` minimum is 1/(2L^2), exactly half the cross quantum, "
    "and that halving is the midpoint's own -- it coincides with the AREA "
    "quantum, whose halving comes from the shoelace, by accident.",
    "`clip_seg`'s span parameter `t = -num/denom` for a genuinely clipped "
    "span -- a ratio of two grid multiples is an arbitrary rational with no "
    "bounded denominator.",
)

#: Per `#kept` margin site: which floor, if any, the grid DERIVES for it. An
#: earlier revision of the README asserted the 1/L^2 cross floor for every
#: tolerance comparison in the probe. Of the 11 `#kept` rows this run produces,
#: it holds for 4 as cross products of grid coordinates, and 1 more gets the
#: coarser 1/L as a plain coordinate difference; the two unsuffixed AREA_EPS
#: rows get 1/(2L^2). The remaining 6 are lengths, norm-normalized values, span
#: parameters or off-grid midpoints: for those the margin is a MEASUREMENT and
#: nothing derives it. (Before `clip_half` and `dedupe_ring` were instrumented
#: there were 9 `#kept` rows -- 3 derived, 6 measured-only.)
QUANTUM_CLASSIFICATION = {
    "derived_cross_quantum_1_over_L2": [
        "GEOM_EPS/clip_half_signed_dist#kept",
        "GEOM_EPS/clip_seg_denom#kept",
        "GEOM_EPS/clip_seg_parallel_num#kept",
        "GEOM_EPS/segs_interact_o#kept",
    ],
    "derived_coordinate_quantum_1_over_L": [
        "GEOM_EPS/dedupe_same_point#kept",
    ],
    "derived_area_quantum_1_over_2L2": [
        "AREA_EPS/intersection",
        "AREA_EPS/outside",
    ],
    "measured_only": {
        "INTERIOR_EPS/strictly_inside#kept":
            "evaluated at `build.spanning`'s off-grid midpoint; no derived "
            "floor exists (QUANTUM_EXCLUDES)",
        "GEOM_EPS/clip_seg_span#kept":
            "a difference of span PARAMETERS t, not of coordinates; a clipped "
            "t is an arbitrary rational",
        "GEOM_EPS/unit_length#kept":
            "a norm -- irrational in general, so off the grid",
        "GEOM_EPS/overlap_length#kept":
            "a norm -- irrational in general, so off the grid",
        "GEOM_EPS/overlap_span#kept":
            "a norm-normalized projection minus a length",
        "GEOM_EPS/side_of#kept":
            "a cross product against a norm-NORMALIZED direction",
    },
}


def coord_quantum(result, polys):
    """The grid, and the floors it does and does not derive.

    `grid_gate` certifies that two input populations lie on one grid of
    denominator L: the clipping polygons and the `_seg_of` vertices
    (`QUANTUM_COVERS`). A cross product of differences of coordinates ON that
    grid is a multiple of 1/L^2 and a shoelace area a multiple of 1/(2L^2), so
    each such comparison is either a bit-exact 0 -- where float and exact agree
    -- or at least that quantum, orders above any epsilon here.

    ⚠ THAT COVERS SOME OF THE PREDICATES, NOT ALL OF THEM, and the run's
    tightest margin is at one it does not cover. `QUANTUM_EXCLUDES` names the
    two derived quantities that are off the grid -- `spanning`'s midpoint,
    where the whole `INTERIOR_EPS` population lives, and a clipped span's `t`
    -- and `QUANTUM_CLASSIFICATION` files every `#kept` row as derived (and by
    which floor) or as measured-only. Returns (L, 1/L^2, 1/(2L^2)).
    """
    L = _lcm(face_denominators(polys) | seg_denominators(result))
    return L, 1.0 / (L * L), 1.0 / (2 * L * L)


def epsilon_parity():
    """`kernel`'s copied epsilons must still equal the ones production uses.

    `kernel` copies `AREA_EPS`/`GEOM_EPS`/`INTERIOR_EPS` rather than importing
    them, so the float control stays fixed while production is free to move --
    sound, and kept. What was NOT sound is the claim that a divergence would
    surface as a fidelity-gate failure. This run measures that `GEOM_EPS` can
    move 1.66e+04x down and 2.16e+05x up without changing one decision, so any
    retune inside that band leaves both fidelity gates green while the float arm
    measures a predicate production no longer uses -- and the JSON would still
    publish the probe's copies under a README table citing
    `layer_order.py:199`. Hence an explicit equality check that refuses.

    Also checked here: `_dedupe_ring`'s coincidence tolerance, which
    production writes as a LITERAL `atol=1e-9` and not as `GEOM_EPS`, read off
    its own source rather than trusted from its docstring (which says
    "within GEOM_EPS").
    """
    want = {"AREA_EPS": layer_order.AREA_EPS,
            "GEOM_EPS": layer_order.GEOM_EPS,
            "INTERIOR_EPS": layer_order.INTERIOR_EPS}
    got = {"AREA_EPS": kernel.AREA_EPS,
           "GEOM_EPS": kernel.GEOM_EPS,
           "INTERIOR_EPS": kernel.INTERIOR_EPS}
    bad = {k: (want[k], got[k]) for k in want if want[k] != got[k]}
    if bad:
        raise SystemExit(
            "REFUSED: `kernel`'s copied epsilons no longer equal "
            "`layer_order`'s -- " + "; ".join(
                f"{k}: production {w!r} vs kernel {g!r}"
                for k, (w, g) in sorted(bad.items())) +
            ". The float arm is therefore NOT reproducing production's "
            "predicates, and both fidelity gates can still pass: the measured "
            "slack around these constants is four to five orders of "
            "magnitude. Update the copies deliberately, or stop calling the "
            "float arm a control.")

    src = inspect.getsource(layer_order._dedupe_ring)
    found = sorted({float(t) for t in re.findall(r"atol=([0-9.eE+-]+)", src)})
    if not found:
        raise SystemExit(
            "REFUSED: no `atol=` literal found in `layer_order._dedupe_ring`. "
            "Its coincidence predicate has changed shape, so "
            "`geom.DEDUPE_ATOL` is measuring a threshold that no longer "
            "exists and the `dedupe_same_point` margin is meaningless.")
    if found != [geom.DEDUPE_ATOL]:
        raise SystemExit(
            f"REFUSED: `layer_order._dedupe_ring` compares against "
            f"atol={found} but `geom.DEDUPE_ATOL` is {geom.DEDUPE_ATOL!r}. "
            f"The `dedupe_same_point` margin would be a ratio against the "
            f"wrong threshold.")
    return {"production": want, "kernel_copy": got, "identical": True,
            "dedupe_atol_production": found,
            "dedupe_atol_probe": geom.DEDUPE_ATOL}


def constraint_result():
    """The constraint families, float vs exact, with the difference's DIRECTION.

    One MarginLog spans the float arrangement AND the float constraint build,
    so `margins` carries all three epsilons -- AREA_EPS from `geom.split_convex`
    (the only one previously instrumented) plus GEOM_EPS and INTERIOR_EPS from
    the decision sites this task added. Those last two are the ones the probe
    exists to measure: neither had ever been measured.
    """
    import build as build_mod
    ff, polys = load()
    log = kernel.MarginLog()
    out, secs, census = {}, {}, seeded_census(build_mod)
    arms, cells = {}, {}
    for K in (kernel.FLOAT, kernel.EXACT):
        t0 = time.perf_counter()
        pk = as_tuples(polys, K)
        lg = log if K.name == "float" else None
        cl = geom.cells(pk, K, lg)
        cen = census if K.name == "float" else None
        # `ordered=True` so the families can also be handed to
        # `layer_order._Constraints` in construction order for the clause
        # comparison below; the family rows themselves are compared as SETS,
        # which is what spec section 4 asks for and what the gate asserts.
        p, e, t = build_mod.build(ff, pk, cl, K, lg, census=cen, ordered=True)
        arms[K.name], cells[K.name] = (p, e, t), cl
        out[K.name] = dict(zip(FAMILIES, (p, frozenset(e), frozenset(t))))
        secs[K.name] = round(time.perf_counter() - t0, 2)

    f, x = out["float"], out["exact"]
    res = {"families_float": {}, "families_exact": {}}
    for fam in FAMILIES:
        a, b = f[fam], x[fam]
        res["families_float"][fam] = len(a)
        res["families_exact"][fam] = len(b)
        res[f"{fam}_identical"] = a == b
        res[f"{fam}_only_float"] = len(a - b)
        res[f"{fam}_only_exact"] = len(b - a)
        res[f"{fam}_sample_only_float"] = sorted(a - b)[:10]
        res[f"{fam}_sample_only_exact"] = sorted(b - a)[:10]

    # Spec section 4's fourth row, built rather than summed: the clause set
    # `layer_certify` consumes. Not derivable from the three rows above -- the
    # transitivity family comes from `covers` and dwarfs them.
    res.update(clause_comparison(arms, cells))

    res["n_only_float"] = sum(res[f"{fam}_only_float"] for fam in FAMILIES)
    res["n_only_exact"] = sum(res[f"{fam}_only_exact"] for fam in FAMILIES)

    # only_float = constraints the FLOAT build asserts and exact arithmetic
    # does not -> float FABRICATED them. only_exact = constraints exact finds
    # and float missed -> float UNDER-refuted, the direction the module
    # documents as its safe one.
    #
    # `direction` is the README's headline answer and the headline covers the
    # CLAUSE set too, so the clause difference is folded in here. Until the
    # final review it was the family sums alone, which would have read
    # `identical` even with `clauses_identical` false -- and the clause set's
    # dominant family comes from `covers`, not from these three.
    nf = res["n_only_float"] + res["clauses_only_float"]
    nx = res["n_only_exact"] + res["clauses_only_exact"]
    res["direction_inputs"] = {
        "covers": list(FAMILIES) + ["clauses"],
        "only_float": nf, "only_exact": nx,
        "families_only_float": res["n_only_float"],
        "families_only_exact": res["n_only_exact"],
        "clauses_only_float": res["clauses_only_float"],
        "clauses_only_exact": res["clauses_only_exact"]}
    res["direction"] = (
        "identical" if nf == 0 and nx == 0 else
        "float UNDER-refuted (exact has more): an epsilon dropped real "
        "constraints -- the direction layer_order says is safe by design"
        if nf == 0 else
        "float FABRICATED constraints (exact has fewer): the INTERIOR_EPS "
        "direction the module says is ruled out -- CERTIFIED would rest on "
        "constraints that do not exist"
        if nx == 0 else
        "BOTH directions differ: investigate per family")
    res["margins"] = log.minimums()
    res["area_vertices_max"] = log.sizes.get("area_vertices")
    res["census"] = census
    # What the agreement does NOT cover. A family whose input population is
    # empty contributes nothing, so float/exact agreeing on it is vacuous --
    # and the helper it would have exercised is untested by this probe.
    # Derived from the census, over keys SEEDED to 0 and checked against
    # build.py's own `bump` sites, so every entry is an observed zero.
    res["vacuous"] = sorted(k for k, n in census.items() if n == 0)
    L, q_cross, q_area = coord_quantum(ff, polys)
    res["coord_denominator_lcm"] = L
    res["exact_cross_quantum"] = q_cross
    res["exact_area_quantum"] = q_area
    # Which predicates the grid argument derives a floor FOR, and which it does
    # not. Published so the README's grouping has a source: an earlier revision
    # asserted the cross floor for every tolerance comparison and filed
    # `strictly_inside` under the area quantum, where it lands only by a
    # coincidence of two different halvings.
    res["quantum_scope"] = {"covers": list(QUANTUM_COVERS),
                            "excludes": list(QUANTUM_EXCLUDES),
                            "classification": QUANTUM_CLASSIFICATION}
    res["secs"] = secs
    return res


def constraint_fidelity_gate():
    """FLOAT-mode `build` must reproduce production's `_build_constraints`.

    `fidelity_gate` above covers `_cells` only. This one covers the constraint
    families, and it is what distinguishes a real arithmetic finding from a
    transcription bug. The plan author's own draft passed `pairs` and failed
    both other families, then reported a spurious 18-constraint "fabrication"
    against exact arithmetic. Without this gate that claim would have shipped.
    """
    import build as build_mod
    ff, polys = load()
    cons, _slots = layer_order.constraints_for(ff)      # returns (cons, slots)
    want = {
        "pairs": cons.pairs,
        "eqs": frozenset((e[0], e[1]) for e in cons.equalities),
        "tacos": frozenset((t[0], t[1]) for t in cons.tacos),
    }
    require_nonempty(**{f"production_{k}": len(v) for k, v in want.items()})
    pk = as_tuples(polys, kernel.FLOAT)
    pf, ef, tf = build_mod.build(ff, pk, geom.cells(pk, kernel.FLOAT),
                                 kernel.FLOAT, ordered=True)
    got = {"pairs": pf, "eqs": frozenset(ef), "tacos": frozenset(tf)}
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

    # Stronger than the above, and it passes: the same constraints in the same
    # ORDER. Set equality would also be satisfied by a transcription that
    # enumerated the families differently and happened to land on the same
    # set, which is precisely the class of rewrite this gate exists to catch.
    seq_want = {"eqs": tuple((e[0], e[1]) for e in cons.equalities),
                "tacos": tuple((t[0], t[1]) for t in cons.tacos)}
    for k, seq_got in (("eqs", ef), ("tacos", tf)):
        w = seq_want[k]
        if seq_got == w:
            continue
        i = next((j for j, (x, y) in enumerate(zip(w, seq_got)) if x != y),
                 min(len(w), len(seq_got)))
        raise SystemExit(
            f"REFUSED: the float `{k}` transcription has production's SET but "
            f"not its sequence (lengths {len(w)} vs {len(seq_got)}; first "
            f"difference at index {i}: production {w[i:i + 1]}, "
            f"transcription {seq_got[i:i + 1]}). The families agree as sets, "
            f"so this is an enumeration difference rather than a predicate "
            f"one -- but it still means the transcription is not the shipped "
            f"algorithm, and the exact comparison would not be measuring it.")
    return {k: len(v) for k, v in want.items()}


# --------------------------------------------------------------------------
# Guard 3 of spec section 5, and the required-fail controls for guards 1 and 2.
#
# "Identical" is the expected outcome and expected outcomes are where vacuity
# hides. Every guard below is DEMONSTRATED to refuse, not merely written: a
# check never shown to fail is not a check.
# --------------------------------------------------------------------------

PERTURBATION = 0.05              # >> GRID_STEP, so it cannot be grid noise
GRID_STEP = 1.0 / 68             # the measured input grid (coord_quantum)


def perturbed(polys, delta=PERTURBATION):
    """`polys` with ONE coordinate moved off the grid by `delta`."""
    bad = [[[float(c) for c in pt] for pt in p] for p in polys]
    bad[0][0][0] = bad[0][0][0] + delta
    return bad


def seeded_disagreement():
    """Prove the comparison CAN fail.

    An equality check that has never been shown to fail is not a check.
    Perturb one coordinate by more than the grid resolution (1/68 ~ 0.0147)
    and confirm the comparisons report a difference. If they still report
    agreement, the comparison is inert and every other result here is void.

    Two comparisons are exercised, because the probe makes claims about both:
    `canon_cells` (the arrangement) and family set equality (`pairs`, `eqs`,
    `tacos` -- the headline). The families are run in FLOAT mode on both
    inputs, so the operator under test is exactly the one `constraint_result`
    uses for its verdict; only the geometry differs.

    Which families detect it is RECORDED, not asserted away: on this witness
    the perturbation is invisible to `pairs` and `tacos` and visible only to
    `eqs`. That is a real limit on this guard's reach and it belongs in the
    output rather than in a footnote.
    """
    import build as build_mod
    ff, polys = load()
    bad = perturbed(polys)

    pk_clean, pk_bad = as_tuples(polys, kernel.FLOAT), as_tuples(bad, kernel.FLOAT)
    cl_clean = geom.cells(pk_clean, kernel.FLOAT)
    cl_bad = geom.cells(pk_bad, kernel.FLOAT)
    cells_detected = canon_cells(cl_clean) != canon_cells(cl_bad)

    clean = build_mod.build(ff, pk_clean, cl_clean, kernel.FLOAT)
    dirty = build_mod.build(ff, pk_bad, cl_bad, kernel.FLOAT)
    fams = {}
    for fam, a, b in zip(FAMILIES, clean, dirty):
        fams[fam] = {"clean": len(a), "perturbed": len(b), "detected": a != b,
                     "only_clean": len(a - b), "only_perturbed": len(b - a)}
    detecting = sorted(f for f, v in fams.items() if v["detected"])
    blind = sorted(f for f, v in fams.items() if not v["detected"])

    if not cells_detected or not detecting:
        raise SystemExit(
            f"REFUSED: perturbing a coordinate by {PERTURBATION} "
            f"({PERTURBATION / GRID_STEP:.1f}x the 1/68 grid step) left the "
            f"comparisons UNCHANGED (cells detected: {cells_detected}; "
            f"families that detected it: {detecting or 'none'}). The "
            f"comparison cannot detect a difference, so an 'identical' verdict "
            f"from it is meaningless and every figure in this run is void.")
    return {"perturbation": PERTURBATION, "grid_step": GRID_STEP,
            "perturbation_over_grid_step": PERTURBATION / GRID_STEP,
            "cells_clean": len(cl_clean), "cells_perturbed": len(cl_bad),
            "cells_comparison_detected_it": cells_detected,
            "families": fams, "families_detecting": detecting,
            "families_blind_to_it": blind,
            "comparison_detected_it": True}


def fidelity_gate_refuses():
    """Required-fail control for guard 1: the fidelity gate CAN refuse.

    The gate is what licenses every other figure, so it is the last place to
    accept "it passed" without evidence that failing is reachable. Hand it a
    transcription that is one cell short and confirm it exits.
    """
    real = geom.cells

    def one_cell_short(polys, K, log=None):
        return real(polys, K, log)[:-1]

    geom.cells = one_cell_short
    try:
        fidelity_gate()
    except SystemExit as exc:
        return {"refused": True, "message": str(exc)}
    else:
        raise SystemExit(
            "REFUSED: `fidelity_gate` accepted a transcription with one cell "
            "removed. Guard 1 of the spec is inert, so nothing downstream of "
            "it is licensed.")
    finally:
        geom.cells = real


def nonempty_guard_refuses():
    """Required-fail control for guard 2."""
    try:
        require_nonempty(demo=0)
    except SystemExit as exc:
        return {"refused": True, "message": str(exc)}
    raise SystemExit(
        "REFUSED: require_nonempty did not refuse an empty population, so "
        "guard 2 of the spec is inert.")


def constraint_gate_refuses():
    """Required-fail control for the constraint fidelity gate.

    Not one of the spec's three guards -- Task 3 added it, and it is the one
    that caught a real transcription bug (a wrong shared-edge segment). Drop
    one taco from the float build and confirm it exits.
    """
    import build as build_mod
    real = build_mod.build

    def one_taco_short(*a, **kw):
        p, e, t = real(*a, **kw)
        return p, e, (tuple(t[:-1]) if isinstance(t, tuple)
                      else frozenset(sorted(t)[:-1]))

    build_mod.build = one_taco_short
    try:
        constraint_fidelity_gate()
    except SystemExit as exc:
        return {"refused": True, "message": str(exc)}
    else:
        raise SystemExit(
            "REFUSED: `constraint_fidelity_gate` accepted a float build with "
            "one taco removed, so the gate that licenses the constraint "
            "comparison is inert.")
    finally:
        build_mod.build = real


def pairs_gate_refuses():
    """Required-fail control for the constraint gate's `pairs` row.

    `constraint_gate_refuses` above drops a TACO, and the gate's refusal fires
    on `tacos`; `fidelity_gate_refuses` aborts at the cell count, before any
    family is compared. So until this control existed the `pairs` set
    difference had never been shown to report a difference -- and `pairs` is
    the first family in the headline, and the population every other family's
    guards are filtered through. Drop one pair instead, and require the
    refusal to NAME `pairs`: a refusal arriving from some other row would
    leave the comparator just as undemonstrated.
    """
    import build as build_mod
    real = build_mod.build

    def one_pair_short(*a, **kw):
        p, e, t = real(*a, **kw)
        return frozenset(sorted(p)[:-1]), e, t

    build_mod.build = one_pair_short
    try:
        constraint_fidelity_gate()
    except SystemExit as exc:
        msg = str(exc)
        if "pairs:" not in msg:
            raise SystemExit(
                f"REFUSED: the gate refused a build with one PAIR removed, "
                f"but its message does not name `pairs` -- it reads "
                f"{msg.splitlines()[0][:150]!r}. The refusal came from some "
                f"other row, so the `pairs` comparator is still "
                f"undemonstrated.")
        return {"refused": True, "message": msg}
    else:
        raise SystemExit(
            "REFUSED: `constraint_fidelity_gate` accepted a float build with "
            "one pair removed, so the `pairs` set difference -- the first "
            "family in the headline -- has never been shown to report a "
            "difference at all.")
    finally:
        build_mod.build = real


def clause_comparator_refuses():
    """Required-fail control for the CLAUSE comparison (spec section 4's target).

    The four controls above all land on `pairs`, `eqs` or `tacos`. None of them
    touches `clause_comparison`, and an earlier revision of the README softened
    that with "which inherits its families from these three". That is wrong for
    97.8% of the set: the 4,511,932 transitivity clauses are built from
    `covers` inside `layer_certify._iter_clauses` (:90-97), not from any of the
    three families, so no amount of family-level demonstration says the clause
    set-difference operator reports a difference. The collision checks
    establish `clause_key`'s injectivity, which is a different claim.

    Two sub-cases, each a clause DROPPED from one arm only:

      * `taco`: one taco removed from the exact arm -> one taco clause fewer.
      * `transitivity`: one face removed from one arm's cover -> the triples
        that face took part in disappear. This is the sub-case that matters,
        because it is the only one exercising the family that dominates the
        set, and the only one whose clauses do not come from the three
        families at all.

    Run on SYNTHETIC arms, deliberately. `clause_comparison` is
    data-independent -- it streams `_iter_clauses`, packs each clause with
    `clause_key` and takes a two-directional set difference -- so a four-face
    pair of arms exercises exactly the code the real 4.6M-clause comparison
    runs, at no cost. Both sub-cases must report a difference IN THE RIGHT
    DIRECTION and name the right family, or this refuses.
    """
    base_pairs = frozenset({(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)})
    # one equality, as `(literal, literal)` in `layer_order._lit`'s shape
    eqs = ((((0, 1), False), ((0, 2), False)),)
    # two tacos, as `((p, q), (r, s))`, which `_iter_clauses` turns into four
    # literals each; the two orderings give two distinct clauses
    tacos = (((0, 1), (2, 3)), ((2, 3), (0, 1)))
    cover_full = [(None, frozenset({0, 1, 2, 3}))]      # 4 triples
    cover_short = [(None, frozenset({0, 1, 2}))]        # 1 of those 4

    cases = {}
    for name, arms, cells in (
        ("taco",
         {"float": (base_pairs, eqs, tacos),
          "exact": (base_pairs, eqs, tacos[:-1])},
         {"float": cover_full, "exact": cover_full}),
        ("transitivity",
         {"float": (base_pairs, eqs, tacos),
          "exact": (base_pairs, eqs, tacos)},
         {"float": cover_full, "exact": cover_short}),
    ):
        out = clause_comparison(arms, cells)
        if out["clauses_identical"] or out["clauses_only_float"] < 1:
            raise SystemExit(
                f"REFUSED: dropping a {name} clause from one arm left the "
                f"`clauses` comparison reporting identical "
                f"(float {out['clauses_float']}, exact "
                f"{out['clauses_exact']}, only-float "
                f"{out['clauses_only_float']}, only-exact "
                f"{out['clauses_only_exact']}). The clause set-difference "
                f"operator is inert, so `clauses_identical: true` on the real "
                f"arms would establish nothing -- and the transitivity family "
                f"it covers is 97.8% of that set and comes from `covers`, not "
                f"from pairs/eqs/tacos.")
        fams = {ln.split()[1] for ln in out.get("clauses_sample_differing", [])}
        if name not in fams:
            raise SystemExit(
                f"REFUSED: dropping a {name} clause produced a `clauses` "
                f"difference, but the differing clauses it reports are "
                f"{sorted(fams)} -- not {name}. The comparison detected "
                f"something other than what was removed, so it is not "
                f"demonstrated on this family.")
        cases[name] = {"clauses_float": out["clauses_float"],
                       "clauses_exact": out["clauses_exact"],
                       "clauses_identical": out["clauses_identical"],
                       "clauses_only_float": out["clauses_only_float"],
                       "clauses_only_exact": out["clauses_only_exact"],
                       "families_differing": sorted(fams)}
    return {"refused": True, "detected": True, "cases": cases,
            "message": ("the `clauses` comparison reports a dropped clause in "
                        "both the taco and the transitivity family: " +
                        "; ".join(
                            f"{k} only-float {v['clauses_only_float']}"
                            for k, v in sorted(cases.items())))}


# --------------------------------------------------------------------------
# Reading the margins as BOUNDS rather than as a list of rows.
# --------------------------------------------------------------------------

def _parse_tag(tag):
    eps, _, rest = tag.partition("/")
    site, _, suffix = rest.partition("#")
    return eps, site, suffix


def epsilon_bounds(*margin_dicts):
    """Per epsilon: how far it could move, each way, changing no decision.

    A `#kept` row is a value the tolerance KEPT, so its ratio |value|/EPS is
    how far EPS could GROW before that value would be dropped; the minimum
    over the epsilon's `#kept` rows is the grow bound. An `#absorbed` row is
    rounding noise the tolerance ABSORBED, recorded with the arguments swapped
    so its ratio is EPS/|noise|: how far EPS could SHRINK before that noise
    would be kept. `#exact-zero` rows are excluded -- float `|x| < EPS` and
    exact `x == 0` agree on a bit-exact zero, so there is no margin to report
    and including them would floor every bound at 0. An unsuffixed row (the
    AREA_EPS tags, which predate the three-way split) is a kept value.
    """
    out = {}
    for md in margin_dicts:
        for tag, m in md.items():
            eps, _site, suffix = _parse_tag(tag)
            if suffix == "exact-zero":
                continue
            kind = "shrink" if suffix == "absorbed" else "grow"
            slot = out.setdefault(eps, {"shrink": None, "grow": None})
            r = m["closest_ratio_to_threshold"]
            if slot[kind] is None or r < slot[kind]["factor"]:
                slot[kind] = {"factor": r, "site": tag,
                              "value": m["value"], "threshold": m["threshold"]}
    return out


def closest_call(*margin_dicts):
    """The tightest margin any float comparison left IN EITHER DIRECTION.

    This is what distinguishes spec section 6's first outcome row from its
    second, so it must span ALL THREE epsilons -- quoting only the arrangement's
    AREA_EPS rows would let a knife-edge GEOM_EPS or INTERIOR_EPS decision pass
    unexamined while the verdict claimed all three were inert.

    ⚠ The minimum is taken over TWO INCOMMENSURABLE ratio families. A `#kept`
    row's ratio is |value|/EPS (how far the epsilon could GROW); an
    `#absorbed` row's is EPS/|noise| (how far it could SHRINK), recorded with
    the arguments swapped. Both are "factors by which a decision is clear of
    its threshold", which is why minimising across them is meaningful for the
    verdict's >1000x branch -- but the winner is not "the smallest compared
    value", and the direction it bounds depends on which suffix won. Read the
    returned `site` to know which. `epsilon_bounds` is the per-direction view.
    """
    best = None
    for md in margin_dicts:
        for tag, m in md.items():
            if _parse_tag(tag)[2] == "exact-zero":
                continue
            r = m["closest_ratio_to_threshold"]
            if best is None or r < best["factor"]:
                best = {"factor": r, "site": tag, "value": m["value"],
                        "threshold": m["threshold"]}
    return best


def witness_census():
    """The input, counted. Supports the README's claim that the tortilla
    families are unreachable HERE because the file carries no `F` edge."""
    raw = json.load(open(WITNESS))
    ff, polys = load()
    counts = {}
    for a in raw.get("edges_assignment", []):
        counts[a] = counts.get(a, 0) + 1
    # `_polys_of` reverses any face whose signed area is negative, so the
    # reversed polygons are NOT index-parallel to `result.faces`. That is the
    # one place the transcription needed judgement (`_seg_of` must read
    # `folded_vertices`, not the reversed polygons), so the count is published.
    reversed_faces = sum(
        1 for P in ff.folded_vertices
        if geom.area([(float(x), float(y)) for x, y in P]) < 0)
    return {"path": os.path.relpath(os.path.abspath(WITNESS),
                                    os.path.dirname(os.path.abspath(__file__))),
            "cp_vertices": len(raw.get("vertices_coords", [])),
            "edges": len(raw.get("edges_assignment", [])),
            "edges_by_assignment": dict(sorted(counts.items())),
            "faces_from_flat_fold": len(ff.faces),
            "faces_reversed_by_polys_of": reversed_faces,
            "folded_faces": len(ff.folded_vertices),
            "polys": len(polys),
            "shared_edges": len(ff.shared_edges)}


def selftest():
    """The guards are this probe's test suite; run them without the full build."""
    print("selftest 1/9: epsilon parity (kernel's copies == production's)")
    ep = epsilon_parity()
    print(f"  PASS -- {ep['production']}, dedupe atol "
          f"{ep['dedupe_atol_production']}")

    print("selftest 2/9: input grid gate (spec section 3's 2nd assertion)")
    gg = input_grid_gate()
    print(f"  PASS -- grid denominator {gg['grid_denominator']} from "
          f"{gg['grid_from']}, divides every denominator of "
          f"{gg['checked_against']}")

    print("selftest 3/9: the grid gate REFUSES an off-grid denominator")
    gr = grid_gate_refuses()
    print(f"  PASS -- refused: {gr['message'].splitlines()[0][:120]}")

    print("selftest 4/9: fidelity gate (float transcription == production)")
    g = fidelity_gate()
    print(f"  PASS -- {g['production_cells']} cells, bitwise identical")

    print("selftest 5/9: the fidelity gate REFUSES a corrupted transcription")
    fr = fidelity_gate_refuses()
    print(f"  PASS -- refused: {fr['message'].splitlines()[0][:120]}")

    print("selftest 6/9: seeded disagreement (the comparison can fail)")
    s = seeded_disagreement()
    print(f"  PASS -- a {s['perturbation']} perturbation "
          f"({s['perturbation_over_grid_step']:.1f}x the grid step) was "
          f"detected by the cell comparison ({s['cells_clean']} -> "
          f"{s['cells_perturbed']} cells) and by {s['families_detecting']}; "
          f"blind: {s['families_blind_to_it']}")

    print("selftest 7/9: non-empty population guard refuses an empty set")
    nr = nonempty_guard_refuses()
    print(f"  PASS -- refused: {nr['message'][:120]}")

    print("selftest 8/9: the constraint fidelity gate REFUSES a short build, "
          "and on `pairs` when a PAIR is removed")
    cr = constraint_gate_refuses()
    pr = pairs_gate_refuses()
    print(f"  PASS -- refused: {cr['message'].splitlines()[0][:110]}")
    print(f"  PASS -- refused: {pr['message'].splitlines()[0][:110]}")

    print("selftest 9/9: the CLAUSE comparison reports a dropped clause")
    cc = clause_comparator_refuses()
    print(f"  PASS -- {cc['message']}")

    return {"epsilon_parity": ep, "input_grid": gg,
            "grid_gate_refuses": gr, "fidelity": g,
            "fidelity_gate_refuses": fr,
            "seeded_disagreement": s, "nonempty_guard_refuses": nr,
            "constraint_gate_refuses": cr, "pairs_gate_refuses": pr,
            "clause_comparator_refuses": cc}


def main(out_path):
    t0 = time.perf_counter()
    rec = {"subject": "dense lizard, the SAT-certified witness",
           "platform": {"sys_platform": sys.platform,
                        "python": sys.version.split()[0]},
           "witness": witness_census()}

    print("epsilon parity: kernel's copied constants vs layer_order's ...")
    rec["epsilon_parity"] = epsilon_parity()
    print(f"  PASS -- {rec['epsilon_parity']['production']}; "
          f"`_dedupe_ring` atol {rec['epsilon_parity']['dedupe_atol_production']}")

    print("input grid gate: spec section 3's second assertion ...")
    rec["input_grid"] = input_grid_gate()
    print(f"  PASS -- grid denominator {rec['input_grid']['grid_denominator']} "
          f"(ceiling {rec['input_grid']['ceiling']}); every denominator of "
          f"{rec['input_grid']['checked_against']} divides it")

    print("fidelity gate: float transcription vs production `_cells` ...")
    rec["fidelity"] = fidelity_gate()
    print(f"  PASS -- {rec['fidelity']['production_cells']} cells, bitwise "
          f"identical ({time.perf_counter() - t0:.1f}s)")

    print("seeded disagreement: can the comparison fail at all? ...")
    rec["seeded_disagreement"] = seeded_disagreement()
    sd = rec["seeded_disagreement"]
    print(f"  PASS -- {sd['perturbation']} off-grid perturbation detected; "
          f"cells {sd['cells_clean']} -> {sd['cells_perturbed']}, families "
          f"detecting {sd['families_detecting']}, blind "
          f"{sd['families_blind_to_it']}")

    # The required-fail controls run in the FULL run too, not only in
    # `--selftest`, so the committed record carries each guard's refusal
    # message rather than leaving it in a transient stdout.
    print("required-fail controls: every guard must be able to refuse ...")
    rec["guards"] = {"fidelity_gate_refuses": fidelity_gate_refuses(),
                     "nonempty_guard_refuses": nonempty_guard_refuses(),
                     "constraint_gate_refuses": constraint_gate_refuses(),
                     "pairs_gate_refuses": pairs_gate_refuses(),
                     "grid_gate_refuses": grid_gate_refuses(),
                     "clause_comparator_refuses": clause_comparator_refuses()}
    for name, r in rec["guards"].items():
        print(f"  {name}: {r['message'].splitlines()[0][:110]}")

    print("exact arrangement ...")
    arr = rec["arrangement"] = arrangement_result()
    require_nonempty(float_cells=arr["float_cells"],
                     exact_cells=arr["exact_cells"],
                     pairs_float=arr["pairs_float"],
                     pairs_exact=arr["pairs_exact"])
    print(f"  cells float {arr['float_cells']} / exact {arr['exact_cells']}  "
          f"covers identical: {arr['covers_identical']}")
    print(f"  pairs float {arr['pairs_float']:,} / exact {arr['pairs_exact']:,}  "
          f"identical: {arr['pairs_identical']}")
    print(f"  only-float {arr['n_pairs_only_float']}, only-exact "
          f"{arr['n_pairs_only_exact']}")
    print(f"  max denominator {arr['max_denominator']}, largest polygon "
          f"reaching `area` {arr['area_vertices_max']} vertices "
          f"(production's np.sum switches to pairwise summation at 8), "
          f"{arr['secs']}s")
    for tag, m in arr["margins"].items():
        print(f"  margin {tag}: closest {m['closest_ratio_to_threshold']:.3g}x "
              f"threshold (value {m['value']:.3e})")

    print("constraint fidelity gate: float `build` vs production "
          "`_build_constraints` ...")
    rec["constraint_fidelity"] = constraint_fidelity_gate()
    print("  PASS -- " + ", ".join(f"{k} {v:,}"
                                   for k, v in rec["constraint_fidelity"].items()))

    print("exact constraint build ...")
    con = rec["constraints"] = constraint_result()
    require_nonempty(pairs=con["families_float"]["pairs"],
                     eqs=con["families_float"]["eqs"],
                     tacos=con["families_float"]["tacos"],
                     clauses=con["clauses_float"])
    for fam in FAMILIES:
        print(f"  {fam}: float {con['families_float'][fam]:,} / exact "
              f"{con['families_exact'][fam]:,}  identical: "
              f"{con[f'{fam}_identical']}  only-float "
              f"{con[f'{fam}_only_float']}, only-exact "
              f"{con[f'{fam}_only_exact']}")
    print(f"  layer_certify.clauses: float {con['clauses_float']:,} / exact "
          f"{con['clauses_exact']:,}  identical: {con['clauses_identical']}  "
          f"only-float {con['clauses_only_float']}, only-exact "
          f"{con['clauses_only_exact']}")
    print(f"    by family (float): {con['clauses_float_by_family']}")
    print(f"  direction: {con['direction']} (over "
          f"{con['direction_inputs']['covers']})")
    print(f"  input grid: all coordinates have denominator | "
          f"{con['coord_denominator_lcm']}, so every cross product OF THOSE "
          f"COORDINATES is 0 or >= {con['exact_cross_quantum']:.3e} and every "
          f"area 0 or >= {con['exact_area_quantum']:.3e}")
    print(f"  NOT covered by that floor "
          f"({len(con['quantum_scope']['classification']['measured_only'])} "
          f"of the `#kept` sites are measured only): "
          f"{sorted(con['quantum_scope']['classification']['measured_only'])}")
    print(f"  secs {con['secs']}")
    print(f"  census: {con['census']}")
    print(f"  VACUOUS (empty population, so agreement proves nothing there): "
          f"{con['vacuous']}")
    for tag, m in con["margins"].items():
        if tag.endswith("#absorbed"):
            # MarginLog keeps a minimum, so absorbed rows are recorded with
            # the arguments swapped (geom._rec): `value` is the EPSILON and
            # `threshold` is the worst noise it absorbed.
            print(f"  margin {tag}: headroom "
                  f"{m['closest_ratio_to_threshold']:.3g}x -- epsilon "
                  f"{m['value']:.3e} absorbs worst noise "
                  f"{m['threshold']:.3e}")
        else:
            print(f"  margin {tag}: closest "
                  f"{m['closest_ratio_to_threshold']:.3g}x threshold "
                  f"(value {m['value']:.3e}, "
                  f"threshold {m['threshold']:.0e})")

    # The PROBE's copies. They are published under this name because the float
    # arm's predicates use them -- `epsilon_parity` above is what establishes
    # that they still equal production's, and it is the row to cite when the
    # README attributes a value to `layer_order`.
    rec["epsilons"] = {"AREA_EPS": kernel.AREA_EPS,
                       "GEOM_EPS": kernel.GEOM_EPS,
                       "INTERIOR_EPS": kernel.INTERIOR_EPS,
                       "source": "kernel.py copies, asserted equal to "
                                 "layer_order's by `epsilon_parity`"}
    rec["area_vertices_max"] = con["area_vertices_max"]
    rec["rationalization"] = {"max_denominator_limit": kernel.MAX_DEN,
                              "snap_tol": kernel.SNAP_TOL}
    rec["epsilon_bounds"] = epsilon_bounds(arr["margins"], con["margins"])
    rec["closest_call"] = closest_call(arr["margins"], con["margins"])
    rec["total_secs"] = round(time.perf_counter() - t0, 2)
    # Peak RSS, so the second-subject cost hazard in the README is a
    # measurement. macOS `ru_maxrss` is BYTES (Linux reports kilobytes), and
    # this run is darwin-only -- `platform.sys_platform` is the field to check
    # before reading this number on another host.
    rec["peak_rss_mb"] = round(
        resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6, 1)

    with open(out_path, "w") as fh:
        json.dump(rec, fh, indent=1, sort_keys=True, default=str)
    print(f"\nwrote {out_path}")

    print("\nepsilon bounds (no decision in this run changes inside them):")
    for eps, b in sorted(rec["epsilon_bounds"].items()):
        sh = (f"{b['shrink']['factor']:.3g}x ({b['shrink']['site']})"
              if b["shrink"] else "no absorbed comparison to bound it")
        gr = (f"{b['grow']['factor']:.3g}x ({b['grow']['site']})"
              if b["grow"] else "no kept comparison to bound it")
        print(f"  {eps}: shrink {sh}; grow {gr}")

    # `covers_identical` is gated here although spec section 4 lists the cover
    # multiset as "reported, not gated". Deliberate and conservative: a cover
    # difference is what a `pairs` difference would be DOWNSTREAM of, so a run
    # that disagreed on covers while agreeing on pairs should not print the
    # unqualified verdict. It does not affect this run's outcome -- every flag
    # it ands over is true.
    allsame = (arr["pairs_identical"] and arr["covers_identical"] and
               con["clauses_identical"] and
               all(con[f"{fam}_identical"] for fam in FAMILIES))
    cc = rec["closest_call"]
    worst = cc["factor"] if cc else None
    print()
    if allsame and worst is not None and worst > 1000:
        print(f"VERDICT: THE FLOAT PATH IS CORRECT HERE, AND NOT BY LUCK. "
              f"Exact and float agree on pairs, equalities and tacos "
              f"({con['n_only_float']} only-float and {con['n_only_exact']} "
              f"only-exact) and on the {con['clauses_float']:,}-clause set "
              f"`layer_certify.clauses` derives from them "
              f"({con['clauses_only_float']} only-float, "
              f"{con['clauses_only_exact']} only-exact), and the tightest "
              f"margin any float comparison left in either direction was "
              f"{worst:.3g}x its threshold ({cc['site']}). On dense `lizard` "
              f"the three epsilons are inert and CERTIFIED is not weakened by "
              f"them. One subject, box-pleat only -- see the README's limits.")
    elif allsame:
        print(f"VERDICT: IDENTICAL, BUT ON A KNIFE EDGE. The sets agree, yet "
              f"the tightest margin any float comparison left in either "
              f"direction was {worst:.3g}x its threshold ({cc['site']}). "
              f"Agreement here is not robust and a production exact path is "
              f"warranted.")
    else:
        print(f"VERDICT: THE FLOAT PATH AND EXACT ARITHMETIC DISAGREE. "
              f"{con['direction']}. Clause set: only-float "
              f"{con['clauses_only_float']}, only-exact "
              f"{con['clauses_only_exact']}; covers identical: "
              f"{arr['covers_identical']}.")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        raise SystemExit(0)
    main(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "exact-arrangement.json"))
