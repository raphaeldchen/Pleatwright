"""Driver: both arms, both comparisons, every gate, one artifact.

Spec: `docs/superpowers/specs/2026-10-04-pointwise-oracle-design.md`.

    cd docs/superpowers/evidence/2026-10-04-pointwise-oracle
    ../../../../.venv/bin/python3 pointwise_oracle.py --selftest
    ../../../../.venv/bin/python3 pointwise_oracle.py

READ SECTION 9 OF THE SPEC BEFORE CITING ANYTHING THIS PRINTS.

THE HEADLINE IS THE TRIPLE COMPARISON (spec section 4A), not the order-set
comparison. The subset sampling that section 5.1 runs over was measured VACUOUS
by the Task 2 review -- `candidate_subsets` grows a subset from faces sharing a
cell with the seed, which satisfies production's `(x,fa) in pairs and
(x,fb) in pairs` guard (`layer_order.py:555-558`) BY CONSTRUCTION, i.e. it steers
away from the one structural gap the probe exists to expose. The triple
comparison is exhaustive over all faces and all creases instead, so there is
nothing to steer. The order-set comparison is retained and reported, SECOND,
because it tests a different thing: not whether production emitted a constraint
where the geometry has one, but whether the clause SEMANTICS admit the same
orders the geometry does.

MEASURED, AND IT IS NOT WHAT THE SPEC EXPECTED. The triple comparison agrees
exactly; the order-set comparison DISAGREES on every sampled subset, in ONE
direction -- the restricted clause set admits strictly fewer orders than the
oracle, and the oracle rejects no order production admits. The gap localises
entirely to the `taco` family (`equality` alone is identical on every subset),
and the mechanism is the ORACLE's: a taco-taco configuration is two creases
folding back along a COLLINEAR overlap, and `covering` uses strict interiors,
which by design exclude a face whose boundary runs along the crease. So
`stacks.py`'s claim that the uniform rule "subsumes all three families" holds
for taco-tortilla but NOT for the collinear taco-taco case that production's
fifth branch (`layer_order.py:633-646`) reaches through `_segs_interact`'s
collinear arm. Production says so itself, in `_collinear_overlap`'s docstring
(`layer_order.py:415`): a shared segment is NOT covered by the spanning-face
rule, "each face's boundary runs along it, so _strictly_inside is False by
construction". Measured here, not inferred: every clause that rejects an
only-oracle witness is a `taco-taco`, and every one of their crease pairs is
collinear-overlapping. The artifact's `secondary_diagnosis` carries the counts;
the README carries the argument.

A clean result does NOT make dense `lizard` flat-foldable. Foldability does not
compose upward from subsets; `transitivity` -- 97.8% of the full clause set --
is vacuous on a total order and therefore not under test here; and the
geometric predicates are shared with production on purpose (spec section 2.2),
so a defect inside them is common-mode and invisible to this comparison.
"""
import argparse
import json
import os
import platform
import sys
import time
from fractions import Fraction

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "..", "..", "..", "mcp_harness"))
sys.path.insert(0, os.path.join(_HERE, "..", "2026-10-04-exact-arrangement"))
sys.path.insert(0, _HERE)

import enumerate_orders                # noqa: E402
import exact_arrangement               # noqa: E402
import geom                            # noqa: E402
import kernel                          # noqa: E402
import layer_certify                   # noqa: E402
import layer_order                     # noqa: E402
import restrict                        # noqa: E402
import stacks                          # noqa: E402
from box_pleat import sat_order        # noqa: E402

K = kernel.EXACT

#: Subset size cap for the SECONDARY order-set comparison. 8 gives 40,320
#: orders, which the factored enumeration (exact arithmetic once per subset,
#: integer comparison per order) handles in seconds. Raising it is a factorial
#: cost, not a linear one. It does not touch the headline triple comparison,
#: which is exhaustive and takes no size parameter.
MAX_SUBSET = 8

#: Subsets per population in the secondary comparison. The populations answer
#: different questions, so they are capped independently and both counts are
#: reported -- an agreement is only as broad as its population.
PER_POPULATION = 25

#: Witnesses carried into the artifact per difference set. The counts are
#: always reported in full; only the listings are truncated.
WITNESS_CAP = 10


def _taco_creases(clause):
    """The two creases `(p, q)` and `(r, s)` behind a `taco` clause.

    `layer_certify._iter_clauses` emits a taco's literals in the fixed order
    `_lit(r, p), _lit(r, q), _lit(s, p), _lit(s, q)` (`:97-100`), so `r` is the
    face common to variables 0 and 1, `s` the face common to 2 and 3, and the
    leftovers are `p` and `q`. Raises rather than guesses: a taco whose
    variables do not have that shape is a structural surprise, and spec
    section 8 says refuse, never skip.
    """
    v = clause.variables
    if len(v) != 4:
        raise ValueError(f"taco clause {clause!r} has {len(v)} variables, "
                         f"expected 4")
    rr = set(v[0]) & set(v[1])
    ss = set(v[2]) & set(v[3])
    if len(rr) != 1 or len(ss) != 1:
        raise ValueError(
            f"taco clause {clause!r}: variables {v} do not have the shape "
            f"_lit(r,p), _lit(r,q), _lit(s,p), _lit(s,q)")
    (r,), (s,) = rr, ss
    p = (set(v[0]) - {r}).pop()
    q = (set(v[1]) - {r}).pop()
    return (p, q), (r, s)


def _collinear_taco(clause, crease_seg):
    """Is this `taco` clause's crease pair COLLINEAR-overlapping?

    This is the distinction `layer_order._collinear_overlap`'s own docstring
    draws, and it is the one that decides whether the oracle can see the
    configuration at all: "a transversal crossing puts part of each segment
    strictly inside the other's faces and is therefore already covered by the
    spanning-face rule, whereas a shared segment is not (each face's boundary
    runs along it, so _strictly_inside is False by construction)".

    Returns `None` when either crease is not an M/V shared edge of this
    witness, so an unclassifiable clause is reported as unclassified rather
    than silently counted as transversal.
    """
    (p, q), (r, s) = _taco_creases(clause)
    k1, k2 = frozenset((p, q)), frozenset((r, s))
    if k1 not in crease_seg or k2 not in crease_seg:
        return None
    return bool(layer_order._collinear_overlap(_as_float(crease_seg[k1]),
                                               _as_float(crease_seg[k2])))


def _merge_counts(dicts):
    """Sum a sequence of `{key: int}` counters into one."""
    out = {}
    for d in dicts:
        for k, v in d.items():
            out[k] = out.get(k, 0) + v
    return out


def _as_float(seg):
    return ((float(seg[0][0]), float(seg[0][1])),
            (float(seg[1][0]), float(seg[1][1])))


def _triple_key(t):
    """A TOTAL order on `(x, frozenset({fa, fb}))`.

    `sorted` on the raw tuples would compare the frozensets with `<`, which is
    SUBSET containment and not a total order, so the result would be
    arbitrary and unstable rather than wrong-and-loud.
    """
    x, pair = t
    return (x,) + tuple(sorted(pair))


def _triple_json(t):
    x, pair = t
    return {"face": x, "crease": sorted(pair)}


def load_all():
    """The folded state, the clipping polygons, the cells, the clause set and
    the SAT relation -- each built once.

    `exact_arrangement.load()` re-folds the witness and `sat_order.solve` costs
    roughly 30 s, so both run exactly here and the result is threaded.
    """
    ff, polys = exact_arrangement.load()
    polys_k = exact_arrangement.as_tuples(polys, K)
    cells_list = geom.cells(polys_k, K)
    cons, slots = layer_order.constraints_for(ff)     # a 2-TUPLE, not a cons
    all_clauses = layer_certify.clauses(cons)
    census = {}
    for c in all_clauses:
        census[c.family] = census.get(c.family, 0) + 1
    census["TOTAL"] = len(all_clauses)
    # Spec amendment A4: `classify` and `restricted_clauses` read only the
    # geometric families, and the full tuple is ~45x larger, so filter ONCE.
    geometric = restrict.geometric(all_clauses)
    del all_clauses
    res = sat_order.solve(cons, slots)
    if not res.sat or res.relation is None:
        raise SystemExit(
            f"REFUSED: the SAT arm returned {res.verdict.kind!r} with no "
            f"relation, so there is no certified order to validate. This "
            f"probe tests a CERTIFIED witness; without one it has no subject.")
    covers = tuple(frozenset(c) for _poly, c in cells_list)
    creases = restrict.crease_segments(ff, K)
    crease_seg = {frozenset((fa, fb)): seg for fa, fb, seg in creases}
    return {
        "ff": ff, "polys": polys_k, "cells": cells_list, "covers": covers,
        "cons": cons, "clause_census": census, "geometric": geometric,
        "rel": res.relation, "creases": creases, "crease_seg": crease_seg,
        "sat_verdict": res.verdict.kind,
    }


def gate_geometry_fidelity():
    """GATE (spec section 6.6). The arrangement this probe reads must be
    production's arrangement, so a disagreement reported below is about the
    CLAUSE SET and not about the geometry. Reuses the mechanism the
    exact-arrangement slice already established.

    `exact_arrangement.fidelity_gate` RAISES `SystemExit` on failure and
    returns a dict carrying `bitwise_identical` plus both cell counts, so the
    explicit check below is a belt-and-braces guard against that contract
    changing -- NOT the gate itself. Returning the dict puts the cell counts in
    the artifact, where a reader can see the gate compared something.
    """
    info = exact_arrangement.fidelity_gate()
    if not info.get("bitwise_identical"):
        raise SystemExit(
            f"REFUSED: the geometry fidelity gate returned {info!r} without "
            f"bitwise identity. Any clause-set difference measured on top of "
            f"a different arrangement would be uninterpretable.")
    return info


def gate_faces_usable(polys, faces=None):
    """GATE (spec section 6.5, added by the Task 1 review; amendment A5).

    Every face the oracle reads must be CONVEX, counter-clockwise and
    RATIONAL, because both of the predicates underneath the oracle are
    half-plane tests over exact arithmetic:

      * a non-convex or clockwise face is invisible to `covering`, so the
        oracle would miss intruders and ACCEPT bad orders -- silent failure in
        the dangerous direction, which is why this is discharged rather than
        inherited;
      * with non-`Fraction` coordinates `geom.clip_seg`'s `-num / denom`
        returns a `float` and the exactness guarantee is lost with no error.
        `stacks.py` cannot enforce either; the driver is the component that
        knows the kernel is EXACT.

    `faces` defaults to EVERY face, because the headline triple comparison is
    exhaustive over every face -- a gate scoped to the sampled subsets would
    certify less than the probe reads.
    """
    idx = list(range(len(polys))) if faces is None else sorted(faces)
    non_convex, non_rational, dup_rings = [], [], []
    for i in idx:
        poly = polys[i]
        if any(not isinstance(c, Fraction) for v in poly for c in v):
            non_rational.append(i)
        if not stacks.is_convex(poly, K):
            non_convex.append(i)
        if len(set(poly)) != len(poly):
            dup_rings.append(i)
    if non_convex or non_rational:
        raise SystemExit(
            f"REFUSED: {len(non_convex)} face(s) are not convex-CCW "
            f"{non_convex[:10]} and {len(non_rational)} carry non-rational "
            f"coordinates {non_rational[:10]}. Both break a precondition the "
            f"oracle's half-plane predicates rest on: a non-convex face is "
            f"invisible to `covering`, so the oracle would MISS intruders and "
            f"report a clean run having seen nothing.")
    return {"faces_checked": len(idx), "non_convex": 0, "non_rational": 0,
            "duplicate_vertex_rings": len(dup_rings)}


def gate_triples(state):
    """THE HEADLINE (spec section 4A): every `(x, {fa, fb})` the geometry
    gives, against every one production emits. Exhaustive over all faces and
    all creases -- no sampling, nothing to steer.

      * only-oracle -- the crease image crosses face `x`'s strict interior but
        production emitted no constraint: production MISSED one
        (completeness failure);
      * only-production -- a constraint with no geometric support
        (soundness failure).

    The `pairs`-guard census is a SEPARATE measurement, not a corollary of
    only-oracle being 0 (spec section 4A.3). It says how many oracle triples
    production's `(x,fa) in pairs and (x,fb) in pairs` guard
    (`layer_order.py:555-558`) would have discarded, which is a statement about
    production's structure in its own right.

    `stacks.triples` is handed an explicit `faces` range: `state["polys"]` is
    a LIST, and `triples`' default branch does `sorted(polys)`, which on a list
    sorts the POLYGONS rather than enumerating indices.
    """
    polys = state["polys"]
    oracle = stacks.triples(state["creases"], polys, K,
                            faces=range(len(polys)))
    prod_list = restrict.equality_triples(state["geometric"])
    prod = frozenset(prod_list)
    only_oracle = sorted(oracle - prod, key=_triple_key)
    only_prod = sorted(prod - oracle, key=_triple_key)

    pairs = state["cons"].pairs
    blocked = []
    for t in oracle:
        x, pair = t
        fa, fb = sorted(pair)
        if (tuple(sorted((x, fa))) not in pairs
                or tuple(sorted((x, fb))) not in pairs):
            blocked.append(t)
    blocked.sort(key=_triple_key)

    return {
        "oracle_triples": len(oracle),
        "production_triples": len(prod),
        "production_equality_clauses": len(prod_list),
        "only_oracle": len(only_oracle),
        "only_production": len(only_prod),
        "blocked_by_pairs_guard": len(blocked),
        "only_oracle_witnesses": [_triple_json(t)
                                  for t in only_oracle[:WITNESS_CAP]],
        "only_production_witnesses": [_triple_json(t)
                                      for t in only_prod[:WITNESS_CAP]],
        "blocked_by_pairs_guard_witnesses": [_triple_json(t)
                                             for t in blocked[:WITNESS_CAP]],
        "identical": not only_oracle and not only_prod,
    }, only_oracle


def _covers_at_probes(seg, polys, others, t_lo, t_hi, n=3):
    """The distinct covering sets at `n` evenly spaced INTERIOR probes of
    `(t_lo, t_hi)`.

    Factored out so the gate below and its refusal demonstration in
    `selftest` run the SAME arithmetic -- a demonstration that exercises
    different code from the gate does not demonstrate the gate.

    HONEST LIMITATION, the same one `test_stacks._cover_constant` records: `n`
    probes detect a missing breakpoint only when the resulting change point
    lies between the first and last probe, so the check's power depends on the
    geometry rather than being absolute.
    """
    w = t_hi - t_lo
    ts = [t_lo + w * Fraction(i + 1, n + 1) for i in range(n)]
    return {stacks.covering(seg, t, polys, others, K) for t in ts}


def gate_breakpoints_constant(state, subsets, probes_per_segment=3):
    """GATE (spec section 6.1), on REAL geometry rather than a fixture.

    One exact sample per sub-segment is only exhaustive if the covering set is
    constant across it. Measure that: at three distinct interior points of each
    sub-segment the cover must be identical.
    """
    checked = 0
    for subset in subsets:
        for fa, fb, seg in restrict.creases_in(state["creases"], subset):
            others = tuple(sorted(subset - {fa, fb}))
            cuts = stacks.breakpoints(seg, state["polys"], others, K)
            for t_lo, t_hi in zip(cuts, cuts[1:]):
                covers = _covers_at_probes(seg, state["polys"], others,
                                           t_lo, t_hi, probes_per_segment)
                checked += 1
                if len(covers) != 1:
                    raise SystemExit(
                        f"REFUSED: cover is not constant on sub-segment "
                        f"({t_lo}, {t_hi}) of crease ({fa}, {fb}): {covers}. "
                        f"The breakpoint set is incomplete, so one sample per "
                        f"sub-segment is an approximation and every result "
                        f"below would rest on sampling luck.")
    if not checked:
        raise SystemExit(
            "REFUSED: the breakpoint gate examined ZERO sub-segments, so it "
            "certifies nothing. A gate that passes vacuously is worse than no "
            "gate.")
    return checked


def _square(x0, y0, x1, y1):
    """A CCW axis-aligned rectangle in exact rationals."""
    F = Fraction
    return [(F(x0), F(y0)), (F(x1), F(y0)), (F(x1), F(y1)), (F(x0), F(y1))]


def intruder_fixture():
    """Faces 0 and 1 joined by a crease, with face 7 covering its middle.

    Built once and shared by `gate_oracle_refuses` and `selftest`, which both
    need it: two copies of a fixture in one module is two things to keep in
    step.
    """
    F = Fraction
    seg = ((F(0), F(0)), (F(4), F(0)))
    polys = {0: _square(0, -1, 4, 1), 1: _square(0, -1, 4, 1),
             7: _square(1, -1, 3, 1)}
    return stacks.active(stacks.sites([(0, 1, seg)], polys,
                                      frozenset({0, 1, 7}), K))


def gate_oracle_refuses(state, subsets, sites_by):
    """GATE (spec section 6.4). An oracle never shown to reject is an oracle
    that may be reading nothing.

    Two independent demonstrations: a SEEDED INVERSION of the certified order
    inside a real subset, and the hand-built INTRUDER fixture.
    """
    # (a) the hand-built intruder: face 7 threads a crease between 0 and 1.
    s = intruder_fixture()
    if not s or stacks.accepts(s, (0, 7, 1)):
        raise SystemExit(
            "REFUSED: the oracle ACCEPTED a face placed between a crease's "
            "two faces. It is not implementing the rule it documents.")

    # (b) a seeded inversion of the certified order, in a real subset.
    inverted = 0
    witness = None
    for subset in subsets:
        act = stacks.active(sites_by[subset])
        if not act:
            continue
        order = enumerate_orders.rel_to_order(state["rel"], subset)
        if order is None:
            continue
        if not stacks.accepts(act, order):
            continue              # reported separately as a validation failure
        for i in range(len(order) - 1):
            swapped = list(order)
            swapped[i], swapped[i + 1] = swapped[i + 1], swapped[i]
            if not stacks.accepts(act, tuple(swapped)):
                inverted += 1
                witness = {"subset": sorted(subset),
                           "certified_order": list(order),
                           "rejected_transposition": swapped}
                break
        if inverted:
            break
    if not inverted:
        raise SystemExit(
            "REFUSED: no adjacent transposition of the certified order was "
            "rejected in any sampled subset, so the oracle has not been shown "
            "to discriminate between orders on this subject's geometry.")
    return {"intruder_rejected": True, "seeded_inversion_rejected": inverted,
            "seeded_inversion_witness": witness}


def _rejecting_clauses(only_oracle, clauses_sub, crease_seg):
    """The MINIMAL WITNESS for a disagreement (spec section 8): which clauses
    actually reject an order the oracle admits, and what geometry they came
    from.

    Takes the FIRST only-oracle order (a disagreement reported without naming
    the clause that caused it is a disagreement nobody can adjudicate), checks
    every restricted clause against it with production's own predicate, and
    classifies each rejecting clause by family and -- for a `taco` -- by
    whether its crease pair is collinear-overlapping or transversal. That
    split is the one that decides whether the ORACLE could have seen the
    configuration at all.
    """
    if not only_oracle:
        return None
    order = only_oracle[0]
    rel = restrict.order_to_rel(order)
    fam, collinear, provs = {}, {}, []
    for c in clauses_sub:
        vals = tuple(rel[pair] != flip
                     for pair, flip in zip(c.variables, c.flips))
        if layer_certify._satisfied(c.family, vals):
            continue
        fam[c.family] = fam.get(c.family, 0) + 1
        if len(provs) < 3:
            provs.append(c.prov)
        if c.family == "taco":
            key = {True: "collinear", False: "transversal",
                   None: "unclassified"}[_collinear_taco(c, crease_seg)]
            collinear[key] = collinear.get(key, 0) + 1
    return {"witness_order": list(order), "by_family": fam,
            "taco_crease_pairs": collinear, "sample_provs": provs}


def cover_fallback_seeds(creases, covers):
    """How many `candidate_subsets` seeds take the INTERSECTING-cover fallback.

    `candidate_subsets` does not return this (its docstring says so explicitly
    and assigns the count to the driver), and without it a reader cannot tell
    whether the fallback branch ran at all. A crease whose two faces share no
    cell cover is possible, because production guards cover membership with
    `if tuple(sorted((fa, fb))) in pairs` (`layer_order.py:570`).
    """
    n = 0
    for fa, fb, _seg in creases:
        seed = frozenset({fa, fb})
        if not any(seed <= c for c in covers):
            n += 1
    return n


def shared_edge_census(ff):
    """`shared_edges` by assignment, which is WHY spec section 9.11 holds.

    Two of production's three equality branches run over `tortillas`, and
    `_build_constraints` puts a shared edge there only when its assignment is
    neither `M` nor `V`. No `F` edges means those two branches cannot fire, so
    the triple comparison is silent about them.
    """
    out = {}
    for _fa, _fb, _k, a in ff.shared_edges:
        out[a] = out.get(a, 0) + 1
    out["TOTAL"] = len(ff.shared_edges)
    return out


def face_census(ff):
    out = {}
    for f in ff.faces:
        out[str(len(f))] = out.get(str(len(f)), 0) + 1
    out["TOTAL"] = len(ff.faces)
    return out


def run():
    t0 = time.time()
    state = load_all()
    fidelity = gate_geometry_fidelity()
    faces_usable = gate_faces_usable(state["polys"])

    # --- the headline: exhaustive triple comparison (spec section 4A) -------
    triples_result, only_oracle = gate_triples(state)

    # --- the secondary order-set comparison (spec section 5.1) -------------
    # Population A: subsets around a triple both arms carry.
    # Population B: subsets around an ONLY-ORACLE triple -- empty here,
    # because only-oracle is 0, and that emptiness is the RESULT.
    cands = restrict.candidate_subsets(state["creases"], state["covers"],
                                       MAX_SUBSET)
    only_oracle_faces = {x for x, _pair in only_oracle}
    for _x, pair in only_oracle:
        only_oracle_faces |= set(pair)
    classified = {"A": 0, "B": 0}
    pops = {"A": [], "B": []}
    for s in cands:
        if not restrict.creases_in(state["creases"], s):
            continue
        label = restrict.classify(state["geometric"], s)
        classified[label] += 1
        # Section 4A.5's populations, which are NOT `classify`'s labels: a
        # subset belongs to B only if it is built around an ONLY-ORACLE
        # triple. `classify`'s "B" means merely "no production constraint
        # here", which is much weaker and must not be confused with it.
        pop = "B" if (s & only_oracle_faces) else "A"
        if len(pops[pop]) < PER_POPULATION:
            pops[pop].append(s)

    chosen = pops["A"] + pops["B"]
    sites_by = {s: stacks.sites(restrict.creases_in(state["creases"], s),
                                state["polys"], s, K) for s in chosen}
    active_by = {lab: sum(1 for s in pops[lab] if stacks.active(sites_by[s]))
                 for lab in ("A", "B")}

    # Spec amendment A2 / gate 6.3: population B is NOT required non-empty --
    # it is built from only-oracle triples, so an empty B means production
    # missed nothing, which is the probe's BEST outcome and not a failure.
    exact_arrangement.require_nonempty(
        oracle_triples=triples_result["oracle_triples"],
        production_triples=triples_result["production_triples"],
        population_A=len(pops["A"]), active_sites_A=active_by["A"])

    bp_checked = gate_breakpoints_constant(state, chosen)
    refusal = gate_oracle_refuses(state, chosen, sites_by)

    rows, disagreements, validation_failures = [], [], []
    for label in ("A", "B"):
        for subset in pops[label]:
            creases = restrict.creases_in(state["creases"], subset)
            sts = sites_by[subset]
            cl = restrict.restricted_clauses(state["geometric"], subset)
            fam = {}
            for c in cl:
                fam[c.family] = fam.get(c.family, 0) + 1
            out = enumerate_orders.compare(
                sts, cl, subset,
                clause_accepts=restrict.clause_accepts,
                order_to_rel=restrict.order_to_rel)
            # DIAGNOSTIC, not an adjustment: the same comparison against the
            # `equality` family alone. It localises any disagreement to a
            # family instead of leaving it unexplained, which spec section 8
            # requires ("reports both verdicts and the minimal witness"). The
            # row's own `identical` above is still taken over the FULL
            # restricted geometric set, so nothing here weakens the
            # designated comparison.
            eq_only = tuple(c for c in cl if c.family == "equality")
            eq_out = enumerate_orders.compare(
                sts, eq_only, subset,
                clause_accepts=restrict.clause_accepts,
                order_to_rel=restrict.order_to_rel)
            rejecting = _rejecting_clauses(out["only_oracle"], cl,
                                           state["crease_seg"])
            order = enumerate_orders.rel_to_order(state["rel"], subset)
            shipped_ok = None if order is None else stacks.accepts(
                stacks.active(sts), order)
            row = {
                "population": label,
                "subset": sorted(subset),
                "creases": len(creases),
                "clauses": len(cl),
                "clauses_by_family": fam,
                "shipped_order": None if order is None else list(order),
                "shipped_order_pointwise_ok": shipped_ok,
                **{k: v for k, v in out.items()
                   if k not in ("only_oracle", "only_clauses")},
                "only_oracle": [list(o) for o in out["only_oracle"][:5]],
                "only_clauses": [list(o) for o in out["only_clauses"][:5]],
                "equality_only": {
                    "clauses": len(eq_only),
                    "clauses_admit": eq_out["clauses_admit"],
                    "only_oracle": len(eq_out["only_oracle"]),
                    "only_clauses": len(eq_out["only_clauses"]),
                    "identical": eq_out["identical"],
                },
                "rejecting_clauses": rejecting,
            }
            rows.append(row)
            if not out["identical"]:
                disagreements.append(row)
            if shipped_ok is False:
                validation_failures.append(row)

    diagnosis = {
        "rows": len(rows),
        "rows_identical": sum(1 for r in rows if r["identical"]),
        "rows_with_only_oracle": sum(1 for r in rows if r["only_oracle"]),
        "rows_with_only_clauses": sum(1 for r in rows if r["only_clauses"]),
        "rows_oracle_admits_superset": sum(
            1 for r in rows
            if r["oracle_admits"] >= r["clauses_admit"]
            and not r["only_clauses"]),
        "rows_identical_on_equality_only": sum(
            1 for r in rows if r["equality_only"]["identical"]),
        "rejecting_clauses_by_family": _merge_counts(
            r["rejecting_clauses"]["by_family"] for r in rows
            if r["rejecting_clauses"]),
        "rejecting_taco_crease_pairs": _merge_counts(
            r["rejecting_clauses"]["taco_crease_pairs"] for r in rows
            if r["rejecting_clauses"]),
        "note": ("`only_clauses` empty on every row means the restricted "
                 "clause set is STRICTLY STRONGER than the oracle on these "
                 "subsets -- the oracle rejects no order production admits. "
                 "The gap localises entirely to the `taco` family: on "
                 "`equality` alone the two arms are identical. See README "
                 "section 'The secondary comparison disagrees'."),
    }

    headline_ok = triples_result["identical"]
    secondary_ok = not disagreements and not validation_failures
    art = {
        "subject": "dense lizard (SAT-certified witness)",
        "kernel": K.name,
        "sys_platform": sys.platform,
        "python": platform.python_version(),
        "sat_verdict": state["sat_verdict"],
        "faces": face_census(state["ff"]),
        "creases": len(state["creases"]),
        "shared_edges_by_assignment": shared_edge_census(state["ff"]),
        "clause_census": state["clause_census"],
        "geometric_clauses": len(state["geometric"]),
        "max_subset": MAX_SUBSET,
        "per_population": PER_POPULATION,
        "headline_triple_comparison": triples_result,
        "gates": {
            "geometry_fidelity": fidelity,
            "faces_usable": faces_usable,
            "sub_segments_cover_constant": bp_checked,
            "oracle_refuses": refusal,
            "candidate_subsets": len(cands),
            "classify_A": classified["A"],
            "classify_B": classified["B"],
            "cover_fallback_seeds": cover_fallback_seeds(state["creases"],
                                                         state["covers"]),
            "population_A": len(pops["A"]),
            "population_B": len(pops["B"]),
            "active_sites_A": active_by["A"],
            "active_sites_B": active_by["B"],
        },
        # A DECLARATION, derived from the enumeration's filter constant
        # `restrict.GEOMETRIC_FAMILIES` -- NOT a measurement of what was
        # independently checked. This key was named `families_under_test`
        # until 2026-10-05; that name encoded the claim spec section 9's
        # limitation 12 retracts, so a consumer reading it got exactly what
        # limitation 12 forbids.
        "families_enumerated": list(restrict.GEOMETRIC_FAMILIES),
        # MEASURED scope, and the narrower of the two. The oracle decides from
        # strict-interior geometry, so it is blind to collinear-overlapping
        # crease pairs: 164 of 164 clauses that rejected an order the oracle
        # admitted were tacos over such a pair (`secondary_diagnosis`'s
        # `rejecting_taco_crease_pairs`). `taco` is therefore enumerated above
        # but NOT independently checked. See spec section 9, limitation 12.
        "families_independently_checked": ["equality"],
        "families_not_under_test": ["transitivity"],
        "subsets": rows,
        "secondary_diagnosis": diagnosis,
        "disagreements": disagreements,
        "validation_failures": validation_failures,
        "verdict": ("identical" if headline_ok and secondary_ok
                    else "DISAGREEMENT"),
        "headline_verdict": "identical" if headline_ok else "DISAGREEMENT",
        "secondary_verdict": "identical" if secondary_ok else "DISAGREEMENT",
        "elapsed_secs": round(time.time() - t0, 1),
    }
    out_path = os.path.join(_HERE, "pointwise-oracle.json")
    with open(out_path, "w") as fh:
        json.dump(art, fh, indent=2, sort_keys=True)
    # `subsets` and `disagreements` are per-row and long; the artifact carries
    # them in full and stdout carries their counts, so the printed summary
    # stays readable without hiding that there were disagreements.
    summary = {k: v for k, v in art.items()
               if k not in ("subsets", "disagreements")}
    summary["disagreement_count"] = len(disagreements)
    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"\nwrote {out_path}")
    return art


def selftest():
    """Every gate demonstrated to REFUSE, not merely to be present."""
    checks = []
    F = Fraction

    # 1. `sites` refuses a crease with a face outside the subset.
    try:
        stacks.sites([(0, 99, ((F(0), F(0)), (F(1), F(0))))],
                     {0: _square(0, 0, 1, 1)}, frozenset({0}), K)
        checks.append(("sites refuses a stray face", False))
    except ValueError:
        checks.append(("sites refuses a stray face", True))

    # 2. `compare` refuses a cover face outside the subset.
    try:
        enumerate_orders.compare(
            (stacks.Site(0, 1, frozenset({42}), F(0), F(1)),), (),
            frozenset({0, 1}),
            clause_accepts=lambda cl, rel: True,
            order_to_rel=restrict.order_to_rel)
        checks.append(("compare refuses a stray cover face", False))
    except ValueError:
        checks.append(("compare refuses a stray cover face", True))

    # 3. `require_nonempty` refuses an empty population. Named
    #    `oracle_triples` rather than `population_B`: amendment A2 removed
    #    population B from this guard's arguments, and a selftest naming it
    #    would read as if the driver still asserted it.
    try:
        exact_arrangement.require_nonempty(oracle_triples=0)
        checks.append(("require_nonempty refuses an empty population", False))
    except SystemExit:
        checks.append(("require_nonempty refuses an empty population", True))

    # 4. the oracle rejects the hand-built intruder.
    s = intruder_fixture()
    checks.append(("oracle rejects an intruder between a crease's faces",
                   bool(s) and not stacks.accepts(s, (0, 7, 1))))

    # 5. the breakpoint gate's predicate fails on a COARSENED cut list: with
    #    the interior cuts at 1/6 and 1/2 removed, the whole of (0, 1) is one
    #    interval and its probes disagree. Runs `_covers_at_probes`, the gate's
    #    own arithmetic, rather than a parallel copy of it.
    seg = ((F(0), F(0)), (F(6), F(0)))
    one = {7: _square(1, -1, 3, 1)}
    checks.append(("coarsened cuts give a NON-constant cover",
                   len(_covers_at_probes(seg, one, (7,), F(0), F(1))) != 1))

    # 5b. ...and the real breakpoint list on the same geometry does NOT, so
    #     check 5 is exercising coarsening and not a broken fixture.
    real_cuts = stacks.breakpoints(seg, one, (7,), K)
    checks.append(("the real cut list gives a constant cover on every piece",
                   all(len(_covers_at_probes(seg, one, (7,), a, b)) == 1
                       for a, b in zip(real_cuts, real_cuts[1:]))))

    # 5c. the breakpoint gate refuses a VACUOUS pass -- zero sub-segments
    #     examined certifies nothing.
    try:
        gate_breakpoints_constant({"creases": (), "polys": []}, [])
        checks.append(("breakpoint gate refuses a vacuous pass", False))
    except SystemExit:
        checks.append(("breakpoint gate refuses a vacuous pass", True))

    # 6. `transitivity` rejects a cycle.
    checks.append(("transitivity rejects a cyclic triple",
                   not layer_certify._satisfied("transitivity",
                                                (True, True, False))))

    # 7. `rel_to_order` returns None on a cycle.
    checks.append(("rel_to_order detects a cycle",
                   enumerate_orders.rel_to_order(
                       {(0, 1): True, (1, 2): True, (0, 2): False},
                       frozenset({0, 1, 2})) is None))

    # 8. (amendment A5) `gate_faces_usable` refuses a CLOCKWISE face. The
    #    sharpest case: a clockwise convex square has every cross product
    #    negative, so `covering` finds nothing inside it at all and the oracle
    #    would accept bad orders while reporting clean.
    cw = list(reversed(_square(0, 0, 1, 1)))
    try:
        gate_faces_usable([_square(0, 0, 1, 1), cw])
        checks.append(("gate_faces_usable refuses a clockwise face", False))
    except SystemExit:
        checks.append(("gate_faces_usable refuses a clockwise face", True))

    # 9. (amendment A5) and it refuses non-rational coordinates, which is the
    #    silent half: `clip_seg` would divide to a float with no error.
    try:
        gate_faces_usable([[(0, 0), (1, 0), (1, 1), (0, 1)]])
        checks.append(("gate_faces_usable refuses int coordinates", False))
    except SystemExit:
        checks.append(("gate_faces_usable refuses int coordinates", True))

    # 10. and it PASSES a face that satisfies both preconditions -- a gate
    #     that refused everything would also be useless.
    ok = gate_faces_usable([_square(0, 0, 1, 1)])
    checks.append(("gate_faces_usable passes a convex CCW rational face",
                   ok == {"faces_checked": 1, "non_convex": 0,
                          "non_rational": 0, "duplicate_vertex_rings": 0}))

    # 11. `equality_triples` refuses a clause whose pairs share no face --
    #     a tortilla-tortilla equality names four faces, and spec section 9.11
    #     says it must be LOUD rather than silently dropped.
    bad = layer_certify.Clause("equality", ((0, 1), (2, 3)), (False, False),
                               "synthetic four-face equality")
    try:
        restrict.equality_triples((bad,))
        checks.append(("equality_triples refuses a four-face equality", False))
    except ValueError:
        checks.append(("equality_triples refuses a four-face equality", True))

    # 12. `_taco_creases` refuses a taco whose variables are not
    #     `_lit(r,p), _lit(r,q), _lit(s,p), _lit(s,q)`. Guessing here would
    #     mis-classify the collinear/transversal split that the secondary
    #     comparison's whole diagnosis rests on.
    try:
        _taco_creases(layer_certify.Clause(
            "taco", ((0, 1), (2, 3), (4, 5), (6, 7)),
            (False,) * 4, "synthetic disjoint taco"))
        checks.append(("_taco_creases refuses a malformed taco", False))
    except ValueError:
        checks.append(("_taco_creases refuses a malformed taco", True))

    # 13. ...and it RECOVERS the crease pair from a well-formed one, so
    #     check 12 is not passing because the helper rejects everything.
    good = layer_certify.Clause("taco", ((0, 1), (1, 5), (0, 6), (5, 6)),
                                (True, False, True, True), "synthetic taco")
    checks.append(("_taco_creases recovers (p,q) and (r,s)",
                   _taco_creases(good) == ((0, 5), (1, 6))))

    # 14. `_collinear_taco` reports UNCLASSIFIED rather than defaulting to
    #     transversal when a crease is absent from the witness.
    checks.append(("_collinear_taco returns None on an unknown crease",
                   _collinear_taco(good, {}) is None))

    for name, ok in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    bad_checks = [n for n, ok in checks if not ok]
    if bad_checks:
        raise SystemExit(
            f"\n{len(bad_checks)} selftest check(s) FAILED: {bad_checks}")
    print(f"\nselftest: {len(checks)}/{len(checks)} checks pass")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--selftest", action="store_true",
                    help="demonstrate every guard refusing, and exit")
    args = ap.parse_args()
    if args.selftest:
        selftest()
    else:
        run()


if __name__ == "__main__":
    main()
