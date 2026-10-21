"""Does `layer_certify`'s `taco` clause family mean what it says?

Spec: `../../specs/2026-10-05-cross-section-oracle-design.md`

Run:
    cd docs/superpowers/evidence/2026-10-05-cross-section-oracle
    ../../../../.venv/bin/python3 cross_section_oracle.py

THIS FILE IS THE ONLY ONE ALLOWED TO TOUCH PRODUCTION. `lines.py` and
`strip.py` are import-free by design and by test (spec section 2.3): the
oracle's predicates must not be transcriptions, or the comparison is a
comparison of a copy with its original. What IS shared, necessarily, is the
input geometry -- the folded coordinates and the clipping polygons both come
from production through `exact_arrangement.load()` -- and that sharing lives
here.

TWO ARRAYS, NOT ONE. `load()` returns `(ff, polys)`. Crease segments are read
PER FACE out of `ff.folded_vertices`, which are UNREVERSED; clipping and the
perpendicular clip use `polys`, which the production helper may have REVERSED
to counter-clockwise. Mixing them silently inverts windings, and a clockwise
ring makes every interior test read empty. `restrict.crease_segments` already
reads the right one.

THE COMPARISON IS ORDER-FREE ON BOTH SIDES. Neither `strip.taco_pairs` nor
`strip.pierce_pairs` takes a layer order, so the oracle's side of the
comparison is a function of the folded geometry alone, and the production side
is the `taco` clause set, likewise independent of any particular order. That is
what makes the comparison incapable of going vacuous. Two consequences:

* The certified relation (`res.relation`) is NOT a total order over all faces:
  it spans exactly `cons.pairs`, because faces whose folded footprints never
  overlap carry no order variable (`gate_relation_scope` measures this and
  refuses if the two ever disagree). That is immaterial to the verdict, since
  no order is consumed.
* Whether the certified order PASSES this oracle pointwise is a SEPARATE
  QUESTION THIS SLICE DOES NOT ASK. It is outside the spec's scope and no check
  for it is made here.
"""
import json
import os
import sys
import time
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
_EVID = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(_EVID, "2026-10-04-exact-arrangement"))
sys.path.insert(0, os.path.join(_EVID, "2026-10-04-pointwise-oracle"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "..", "mcp_harness"))
sys.path.insert(0, HERE)

import exact_arrangement               # noqa: E402
import geom                            # noqa: E402
import kernel                          # noqa: E402
import layer_certify                   # noqa: E402
import layer_order                     # noqa: E402
import lines as L                      # noqa: E402
import restrict                        # noqa: E402
import stacks                          # noqa: E402
import strip                           # noqa: E402
from box_pleat import sat_order         # noqa: E402

K = kernel.EXACT
ART = os.path.join(HERE, "cross-section-oracle.json")

#: Edge assignments that fold (a U-turn) and that stay flat (a through pair).
CREASE_KINDS = ("M", "V")
FLAT_KINDS = ("F",)

#: Bounded witness lists keep the artifact readable without hiding a
#: disagreement: the COUNT is always exact, only the examples are capped.
MAX_WITNESSES = 12

#: Crease-overlapping collinear lines on the witness. Measured independently
#: before the plan was written, with three controls. A hard-coded expectation
#: on purpose: `gate_accounting` refuses on any other value rather than
#: adopting whatever the code happens to produce.
EXPECTED_CREASE_LINES = 29


def _canon_taco(pq, rs):
    """A production taco entry as the oracle's canonical object.

    `cons.tacos` holds `((p, q), (r, s), prov)` and emits BOTH orders of each
    unordered pair (`layer_order.py:641` and `:644`). THIS FUNCTION ONLY MAPS
    ONE ENTRY TO A CANONICAL, ORDER-INSENSITIVE KEY; it does not de-duplicate.
    `load_all` stores `"tacos"` as a TUPLE, so it still holds one element per
    ordered entry. The collapse to unordered pairs happens where a `set(...)`
    is taken: in the comparison (`set(production_pairs)`) and in `taco_counts`,
    which reports both numbers (`taco_entries_ordered`,
    `taco_pairs_unordered`).
    """
    return frozenset((frozenset(pq), frozenset(rs)))


def load_all():
    """The folded state, the polygons, every shared edge with its exact folded
    segment, the bundles, the clause set and the certified relation.

    `load()` re-folds the witness and `sat_order.solve` costs roughly 30 s, so
    each runs exactly once here and the result is threaded through the gates.
    """
    ff, polys = exact_arrangement.load()
    polys_k = exact_arrangement.as_tuples(polys, K)
    polymap = {i: p for i, p in enumerate(polys_k)}

    # Creases (M/V) come from the helper that reads folded_vertices per face.
    creases = restrict.crease_segments(ff, K)
    crease_by_pair = {frozenset((fa, fb)): seg for fa, fb, seg in creases}

    # Flat edges need the same per-face read. `shared_edges` carries the
    # assignment, so one pass over it covers both kinds and keeps the segment
    # source identical for each.
    folded = [[(K.conv(float(x)), K.conv(float(y))) for x, y in P]
              for P in ff.folded_vertices]
    edges = []
    for fa, fb, k, a in ff.shared_edges:
        face = ff.faces[fa]
        i0, i1 = face.index(k[0]), face.index(k[1])
        edges.append((fa, fb, a, (folded[fa][i0], folded[fa][i1])))
    edges = tuple(edges)

    bundles_map = L.bundles(edges)
    over = L.overlapping_lines(bundles_map, kinds=CREASE_KINDS)

    cons, slots = layer_order.constraints_for(ff)
    all_clauses = layer_certify.clauses(cons)
    census = {}
    for c in all_clauses:
        census[c.family] = census.get(c.family, 0) + 1
    census["TOTAL"] = len(all_clauses)
    del all_clauses

    res = sat_order.solve(cons, slots)
    if not res.sat or res.relation is None:
        raise SystemExit(
            f"REFUSED: the SAT arm returned {res.verdict.kind!r} with no "
            f"relation, so there is no certified order to test. This probe "
            f"tests a CERTIFIED witness; without one it has no subject.")

    return {
        "ff": ff,
        "polys": polys_k,
        "polymap": polymap,
        "edges": edges,
        "creases": creases,
        "crease_by_pair": crease_by_pair,
        "bundles": bundles_map,
        "lines": over,
        "cons": cons,
        "relation": res.relation,
        "census": census,
        "tacos": tuple(_canon_taco(pq, rs) for pq, rs, _p in cons.tacos),
        "sat_kind": res.verdict.kind,
    }


def line_partition(d, key, bundle):
    """The partition of one collinear line AND the face set read over it.

    SHARED BY `walk_line` AND `gate_constancy`, ON PURPOSE. The constancy gate
    exists to defend the partition `walk_line` samples, so it must read the same
    breakpoints and the same faces. They used to compute their own, and the face
    sets differed (bundle-edge faces only, versus bundle-edge faces plus every
    face the line clips): the gate then could not observe a `THROUGH` strand at
    all. One derivation means the two cannot drift apart.

    The breakpoints are every edge-span boundary AND every face-span boundary
    on this line: a face can start or stop meeting the line without any crease
    endpoint being there, and omitting those would let a sub-segment contain a
    configuration change -- which is exactly the property the single-sample
    argument rests on.

    Returns a dict: `direction`, `w` (the perpendicular), `anchor`, `faces`
    (the full face set, sorted), `faces_via_edges` (the count attached to the
    bundle's own edges), `bps` (breakpoints) and `samples` (one per
    sub-segment).
    """
    direction = L.direction_of(key)
    w = strip.perpendicular(direction)
    anchor = bundle[0][3][0]

    intervals = [L.span(direction, e[3]) for e in bundle]
    faces_here = set()
    for e in bundle:
        faces_here.add(e[0])
        faces_here.add(e[1])
    faces_via_edges = len(faces_here)

    # A face contributes breakpoints exactly where its intersection WITH THIS
    # LINE starts and ends, so the quantity to clip is the bundle line itself,
    # not the perpendicular. `line_clip` returns the parameter u along
    # `direction` measured from `anchor`, and `project` advances by
    # `|direction|^2` per unit of u, so u converts to projection units by
    #     t = project(direction, anchor) + u * (dx^2 + dy^2).
    #
    # Getting this wrong in the other direction is the dangerous one: a test
    # that EXCLUDES a face which does meet the line shrinks the oracle arm,
    # and a shrunken oracle arm reads as agreement.
    dx, dy = direction
    scale = dx * dx + dy * dy
    t_anchor = L.project(direction, anchor)
    for f, poly in d["polymap"].items():
        hit = strip.line_clip(poly, anchor, direction)
        if hit is None:
            continue
        u_lo, u_hi = hit
        intervals.append((t_anchor + u_lo * scale, t_anchor + u_hi * scale))
        faces_here.add(f)

    bps = strip.breakpoints(intervals)
    return {"direction": direction, "w": w, "anchor": anchor,
            "faces": sorted(faces_here), "faces_via_edges": faces_via_edges,
            "bps": bps, "samples": strip.sub_segment_samples(bps)}


def walk_line(d, key, bundle):
    """One collinear line, walked exhaustively.

    The partition and the face set come from `line_partition`, which
    `gate_constancy` shares.

    THE LINE-CLIP BRANCH HAS TWO SEPARATE CONTRIBUTIONS, MEASURED SEPARATELY.
    It adds breakpoints (to `intervals`) and it adds FACES (to the face set
    `sides_at` is evaluated over). On this witness it adds zero new
    breakpoints, but the faces are what `strip.pierce_pairs` consumes as
    `THROUGH` strands, so a branch that added no faces would leave
    `pierce_pairs` empty. The result therefore reports, per line,
    `faces_via_bundle_edges` (faces attached to the bundle's own edges),
    `faces_added_by_line_clip` (faces reached ONLY by the clip, not already
    counted) and `through_samples` (samples at which at least one face is
    `THROUGH`). `gate_face_contribution` aggregates them.
    """
    part = line_partition(d, key, bundle)
    direction, w, anchor = part["direction"], part["w"], part["anchor"]
    faces_here = part["faces"]
    faces_via_edges = part["faces_via_edges"]
    faces_via_line_clip = len(faces_here) - faces_via_edges
    bps, samples = part["bps"], part["samples"]

    tacos, pierces, anomalies = set(), set(), []
    through_samples = 0
    for t in samples:
        p = strip.point_at(direction, anchor, t)
        sides = strip.sides_at(d["polymap"], faces_here, p, w)
        if any(s == strip.THROUGH for s in sides.values()):
            through_samples += 1
        creases_at = strip.edges_at(bundle, direction, t, CREASE_KINDS)
        uturns, anom = strip.uturns_at(creases_at, sides)
        anomalies.extend((str(key), str(t)) + tuple(map(str, a))
                         for a in anom)
        tacos |= strip.taco_pairs(uturns)
        pierces |= strip.pierce_pairs(uturns, sides)

    return {
        "samples": len(samples),
        "sub_segments": len(bps) - 1 if bps else 0,
        "faces_via_bundle_edges": faces_via_edges,
        "faces_added_by_line_clip": faces_via_line_clip,
        "through_samples": through_samples,
        "taco_pairs": tacos,
        "pierce_pairs": pierces,
        "anomalies": tuple(anomalies),
    }


def gate_face_contribution(d):
    """GATE 12. The line-clip branch of `walk_line` contributes FACES, not just
    breakpoints.

    The review found that on this witness the branch adds zero new breakpoints
    (`walk_line`'s sub-segment count equalled the old bundle-edge-only
    `gate_constancy`'s; `gate_constancy` now shares `walk_line`'s partition via
    `line_partition`). Breakpoints are not its only contribution: it also adds faces to the set `sides_at` is
    evaluated over, and those are exactly the `THROUGH` strands that
    `strip.pierce_pairs` consumes. If it added no faces, no `THROUGH` strand
    could exist, `pierce_pairs` would be empty and any cross-validation gate
    built on it would pass vacuously. So this reports both totals and REFUSES
    if the additional-face total is zero.

    The per-line figures are face INCIDENCES (a face meeting several lines is
    counted once per line), so the totals are not distinct-face counts.
    """
    lines = own = extra = through = subs = 0
    for key in d["lines"]:
        r = walk_line(d, key, d["bundles"][key])
        lines += 1
        own += r["faces_via_bundle_edges"]
        extra += r["faces_added_by_line_clip"]
        through += r["through_samples"]
        subs += r["sub_segments"]
    if extra == 0:
        raise SystemExit(
            "GATE 12 FAILED: the line-clip branch of `walk_line` added zero "
            "faces on every line, so no THROUGH strand can exist, "
            "`pierce_pairs` is empty, and any gate built on it would be "
            "vacuous.")
    return {"lines": lines,
            "faces_via_bundle_edges_total": own,
            "faces_added_by_line_clip_total": extra,
            "samples_with_a_through_face": through,
            "sub_segments": subs}


def gate_relation_scope(d):
    """GATE 11. The SAT arm's relation spans exactly the constraint builder's
    pairs, and is NOT a total order over all faces.

    `sat_order`'s relation holds only pairs that carry an order variable, which
    are the pairs in `cons.pairs`; faces whose folded footprints never overlap
    have none. Measured on this subject: 53,754 of the 72,010 possible pairs
    among 380 faces. This is why `enumerate_orders.rel_to_order` over all faces
    returns None here for a reason unrelated to the witness being cyclic.

    The measurement is kept because the SAT arm and the constraint builder
    disagreeing about WHICH pairs have an order variable would invalidate
    everything downstream, and it costs one set comparison. Refuses if they are
    not equal.
    """
    rel = set(d["relation"])
    pairs = set(d["cons"].pairs)
    n = len(d["polys"])
    equal = rel == pairs
    if not equal:
        raise SystemExit(
            f"GATE 11 FAILED: the SAT relation and cons.pairs disagree on "
            f"which pairs carry an order variable "
            f"(relation-only {len(rel - pairs)}, pairs-only "
            f"{len(pairs - rel)}). Everything downstream assumes they match.")
    return {"relation_pairs": len(rel), "cons_pairs": len(pairs),
            "possible_pairs": n * (n - 1) // 2,
            "relation_equals_cons_pairs": equal}


def taco_counts(d):
    """Both taco counts, under distinct names.

    `taco_entries_ordered` is `len(cons.tacos)`, one per ORDERED entry (the
    builder emits both orders of each unordered pair).
    `taco_pairs_unordered` is `len(set(d["tacos"]))`, the canonical unordered
    count the comparison actually works with.
    """
    return {"taco_entries_ordered": len(d["cons"].tacos),
            "taco_pairs_unordered": len(set(d["tacos"]))}


def gate_fidelity():
    """GATE 1. The transcription's arrangement cells are bitwise identical to
    production's.

    TAKES NO ARGUMENT, DELIBERATELY. It used to accept `d` and never read it:
    `exact_arrangement.fidelity_gate()` re-folds the witness through its own
    fresh `load()` (about 15 s) and certifies THAT load, not the one held in
    `d`. The load is deterministic so the verdict transfers, but a parameter
    that is ignored makes the signature claim something the code does not do,
    so the parameter was dropped rather than faked. It had no call site.

    `fidelity_gate()` RETURNS A DICT and raises `SystemExit` on failure, so a
    truthiness test on it is dead code. Assert on the figures it returns.
    """
    r = exact_arrangement.fidelity_gate()
    if not r.get("bitwise_identical"):
        raise SystemExit(f"GATE 1 FAILED: cells not bitwise identical: {r}")
    if r.get("production_cells", 0) <= 0:
        raise SystemExit(
            f"GATE 1 FAILED: zero production cells, so 'identical' is "
            f"vacuous: {r}")
    return r


def gate_faces_usable(d):
    """GATE 2. Every face is a strictly counter-clockwise convex exact ring.

    `stacks.is_convex` is the CORRECTED half-plane form: at least three
    vertices, strictly positive shoelace area, and every vertex weakly left of
    every directed edge. An earlier turn-sign version admitted a clockwise
    square, a pentagram, an all-collinear ring and an empty list -- and a
    clockwise ring makes every interior test read empty, so the oracle would
    miss intruders and accept bad orders. Silent failure in the dangerous
    direction.
    """
    bad, non_rational = [], []
    for i, poly in enumerate(d["polys"]):
        if not all(isinstance(c, Fraction) for v in poly for c in v):
            non_rational.append(i)
        if not stacks.is_convex(poly, K):
            bad.append(i)
    if bad or non_rational:
        raise SystemExit(
            f"GATE 2 FAILED: non-convex faces {bad[:MAX_WITNESSES]}, "
            f"non-rational faces {non_rational[:MAX_WITNESSES]}")
    return {"faces_checked": len(d["polys"]), "non_convex": 0,
            "non_rational": 0}


def gate_transversal(d):
    """GATE 7. Every taco clause is over a COLLINEAR crease pair.

    The oracle sees lines; a transversal taco is invisible to it. The scoping
    measurement found zero on this subject, and if that ever changes the probe
    must STOP rather than silently under-report its coverage.

    `collinear` (and `taco_clauses`) count ORDERED ENTRIES of `cons.tacos`,
    i.e. both orders of each unordered pair. They are therefore not comparable
    to the comparison's `production_pairs`, which is an UNORDERED count; see
    `taco_counts` for both numbers side by side.
    """
    coll, trans, missing = 0, [], []
    for pq, rs, _prov in d["cons"].tacos:
        s1 = d["crease_by_pair"].get(frozenset(pq))
        s2 = d["crease_by_pair"].get(frozenset(rs))
        if s1 is None or s2 is None:
            missing.append((tuple(pq), tuple(rs)))
            continue
        k1, k2 = L.line_key(s1), L.line_key(s2)
        if k1 == k2 and L.intervals_overlap(L.span(L.direction_of(k1), s1),
                                            L.span(L.direction_of(k1), s2)):
            coll += 1
        else:
            trans.append((tuple(pq), tuple(rs)))
    if trans or missing:
        raise SystemExit(
            f"GATE 7 FAILED: {len(trans)} transversal and {len(missing)} "
            f"unresolved taco crease pairs. The oracle cannot see transversal "
            f"pairs, so continuing would under-report coverage and call it "
            f"agreement. Witnesses: {trans[:MAX_WITNESSES]} / "
            f"{missing[:MAX_WITNESSES]}")
    if coll == 0:
        raise SystemExit(
            "GATE 7 FAILED: zero collinear taco clauses, so the comparison "
            "has no population and 'identical' would be vacuous.")
    return {"taco_clauses": len(d["cons"].tacos), "collinear": coll,
            "transversal": 0, "unresolved": 0}


def gate_sides(d):
    """GATE 8. Two measurements, neither of which the oracle relies on.

    (a) CROSS-CHECK the oracle's own bundling against the transcription
        `geom.collinear_overlap` (`geom.py:359`). This is control C2 of spec
        section 1.2 promoted to a gate. It is a CROSS-CHECK and not the
        oracle's machinery -- using that predicate to bundle would make the
        bundling common-mode, so it is called here and nowhere else.

    (b) The SAME-SIDE census behind the pre-registered prediction of spec
        section 6: `layer_order.py:633-646` applies no side test while its
        sibling `:590-611` does, so opposite-side collinear crease pairs
        should surface in `only_production`. Reported either way, so the run
        can falsify the prediction instead of explaining it afterwards.

    OUTCOME OF THE PRE-REGISTERED PREDICTION: FALSIFIED. Measured
    `same_side 74602, opposite_side 0, indeterminate 0`. The spec's rival
    hypothesis -- that the quad `pairs` guard already excludes opposite-side
    collinear crease pairs -- is the one the data support. The prediction as
    registered is recorded here unaltered, not reworded to fit the result.

    REFUSES on any `indeterminate` pair. Without that, a `ValueError` from
    `strip.sides_at` turning every pair indeterminate would leave the census
    empty while the gate returned normally and read as success.
    """
    agree = disagree = 0
    for pq, rs, _prov in d["cons"].tacos:
        s1 = d["crease_by_pair"][frozenset(pq)]
        s2 = d["crease_by_pair"][frozenset(rs)]
        k1, k2 = L.line_key(s1), L.line_key(s2)
        mine = (k1 == k2
                and L.intervals_overlap(L.span(L.direction_of(k1), s1),
                                        L.span(L.direction_of(k1), s2)))
        theirs = geom.collinear_overlap(s1, s2, K)
        if bool(mine) == bool(theirs):
            agree += 1
        else:
            disagree += 1
    if disagree:
        raise SystemExit(
            f"GATE 8 FAILED: the oracle's bundling and the transcription "
            f"`geom.collinear_overlap` disagree on {disagree} taco crease "
            f"pairs. One of the two is wrong and the comparison cannot be "
            f"read until that is resolved.")

    same = opposite = indeterminate = 0
    indeterminate_examples = []
    for pq, rs, _prov in d["cons"].tacos:
        s1 = d["crease_by_pair"][frozenset(pq)]
        s2 = d["crease_by_pair"][frozenset(rs)]
        key = L.line_key(s1)
        if key != L.line_key(s2):
            continue
        direction = L.direction_of(key)
        w = strip.perpendicular(direction)
        i1 = L.span(direction, s1)
        i2 = L.span(direction, s2)
        t = (max(i1[0], i2[0]) + min(i1[1], i2[1])) / 2
        p = strip.point_at(direction, s1[0], t)
        try:
            sides = strip.sides_at(
                d["polymap"], sorted(set(pq) | set(rs)), p, w)
        except ValueError as exc:
            indeterminate += 1
            indeterminate_examples.append(
                (tuple(pq), tuple(rs), f"ValueError: {exc}"))
            continue
        s_pq = {sides.get(f) for f in pq}
        s_rs = {sides.get(f) for f in rs}
        if len(s_pq) != 1 or len(s_rs) != 1 or None in s_pq | s_rs:
            indeterminate += 1
            indeterminate_examples.append(
                (tuple(pq), tuple(rs), (sorted(map(str, s_pq)),
                                        sorted(map(str, s_rs)))))
        elif s_pq == s_rs:
            same += 1
        else:
            opposite += 1
    if indeterminate:
        raise SystemExit(
            f"GATE 8 FAILED: {indeterminate} of {len(d['cons'].tacos)} taco "
            f"crease pairs were indeterminate (a `ValueError` from "
            f"`strip.sides_at`, or a face with no single side), so the "
            f"same-side/opposite-side census does not cover the population "
            f"and reading it as complete would be vacuous. Examples: "
            f"{indeterminate_examples[:MAX_WITNESSES]}")
    return {"bundling_cross_check_agree": agree,
            "bundling_cross_check_disagree": 0,
            "same_side": same, "opposite_side": opposite,
            "indeterminate": indeterminate}


def gate_accounting(d):
    """GATE 5. Exhaustive accounting: every line visited, every edge placed.

    Reconciles the bundle contents against the total edge count, so an edge
    lost in bundling cannot shrink the oracle's arm unnoticed. A smaller
    oracle arm reads as agreement, which is why this is a gate and not a log
    line.

    Two further reconciliations: the M/V edge count from `d["edges"]` must
    equal `len(d["creases"])` (two independent extraction paths), and the
    crease-overlapping line count must equal `EXPECTED_CREASE_LINES` (29).
    """
    placed = sum(len(v) for v in d["bundles"].values())
    if placed != len(d["edges"]):
        raise SystemExit(
            f"GATE 5 FAILED: {placed} edges placed in bundles but "
            f"{len(d['edges'])} exist. A lost edge shrinks the oracle arm and "
            f"reads as agreement.")
    creases = sum(1 for e in d["edges"] if e[2] in CREASE_KINDS)
    flats = sum(1 for e in d["edges"] if e[2] in FLAT_KINDS)
    if creases != len(d["creases"]):
        raise SystemExit(
            f"GATE 5 FAILED: {creases} M/V edges in d['edges'] but "
            f"{len(d['creases'])} entries in d['creases']. The two extraction "
            f"paths disagree, so the oracle is walking a different crease set "
            f"than the one it reports.")
    if len(d["lines"]) != EXPECTED_CREASE_LINES:
        raise SystemExit(
            f"GATE 5 FAILED: {len(d['lines'])} crease-overlapping lines, "
            f"expected {EXPECTED_CREASE_LINES}. That figure was measured "
            f"independently, with three controls, before the plan was "
            f"written; it is NOT to be softened to what the code produces. "
            f"Someone must look.")
    if len(d["lines"]) == 0:
        raise SystemExit(
            "GATE 5 FAILED: zero crease-overlapping lines, so the oracle has "
            "nothing to walk and any verdict would be vacuous.")
    return {"edges": len(d["edges"]), "edges_placed": placed,
            "bundle_lines": len(d["bundles"]),
            "crease_overlapping_lines": len(d["lines"]),
            "creases": creases, "flat_edges": flats}


def gate_constancy(d):
    """GATE 3. The configuration really is constant inside a sub-segment, AND
    it really can change across a breakpoint.

    THE POSITIVE CONTROL IS THE POINT. The predecessor's version of this gate
    read "constant" because all three of its probes landed off the face, so it
    certified a fixture that proved nothing. Here the same walk must find at
    least one sub-segment boundary across which the strand set DIFFERS, or the
    constancy half is unfalsifiable and the gate refuses.

    THIS GATE READS EXACTLY WHAT `walk_line` READS. Partition and face set both
    come from `line_partition`, the helper `walk_line` uses, so the gate tests
    the partition it defends and cannot drift from it.

    WHY CONSTANCY INSIDE A SUB-SEGMENT HOLDS: FACE CONVEXITY. Gate 2 enforces
    that every face is a convex ring. A convex face meets a line in a single
    interval, so its strand class (absent / `THROUGH` / U-turn side) is constant
    on that interval's interior. The breakpoint set is the union of ALL those
    interval ends with the crease span ends, so no face's class can change
    strictly inside a sub-segment. This gate is the empirical check of that
    argument: three probes per sub-segment, over the full face set.

    CORRECTION OF AN EARLIER RATIONALE. This docstring used to say the gate was
    "STRICTLY STRONGER, not weaker" because its coarse breakpoint set (bundle
    edges only) was a subset of `walk_line`'s fine one, so each coarse
    sub-segment was a union of fine ones. That argument was WRONG AS APPLIED:
    the gate did not merely use a coarser partition, it also read a strictly
    smaller FACE set (bundle-edge faces only, where `walk_line` adds every face
    the line clips). `gate_face_contribution` showed it: over bundle-edge faces
    alone 0 of 53 samples contain a `THROUGH` face, against 25 of 53 over
    `walk_line`'s full set. The gate therefore could not observe a change in any
    `THROUGH` strand -- exactly what `strip.pierce_pairs` consumes -- so a
    mis-placed face-span boundary in `strip.line_clip` or in `walk_line`'s u->t
    conversion would have passed it unchanged. The property was true, but by
    convexity, not by the subset argument.
    """
    constant = varied = 0
    for key in d["lines"]:
        part = line_partition(d, key, d["bundles"][key])
        direction, w, anchor = part["direction"], part["w"], part["anchor"]
        faces, bps, samples = part["faces"], part["bps"], part["samples"]

        def _read(t):
            p = strip.point_at(direction, anchor, t)
            return tuple(sorted(strip.sides_at(d["polymap"], faces, p,
                                               w).items()))

        prev = None
        for i, t in enumerate(samples):
            lo, hi = bps[i], bps[i + 1]
            three = (lo + (t - lo) / 2, t, t + (hi - t) / 2)
            readings = {_read(x) for x in three}
            if len(readings) == 1:
                constant += 1
            else:
                raise SystemExit(
                    f"GATE 3 FAILED: the strand set is NOT constant inside "
                    f"sub-segment {i} of line {key}: {len(readings)} distinct "
                    f"readings. The single-sample argument does not hold and "
                    f"the oracle's exhaustiveness claim is void.")
            cur = _read(t)
            if prev is not None and cur != prev:
                varied += 1
            prev = cur
    if varied == 0:
        raise SystemExit(
            "GATE 3 FAILED (positive control): no sub-segment boundary "
            "changed the strand set anywhere. A constancy check that cannot "
            "observe a change is unfalsifiable -- which is exactly how this "
            "gate passed vacuously in the predecessor slice.")
    return {"sub_segments_constant": constant, "boundaries_that_varied": varied}


def _restricted(sides, faces):
    """`sides` cut down to exactly `faces`, so a control built on a synthetic
    order is independent of whatever else is at the sample point."""
    return {f: sides[f] for f in faces}


def _seeded_control(sides, uturns):
    """Control (a) on one sample. Returns the crossed order if `accepts`
    reports the interleaving, else None; None too if the sample cannot host
    the control (fewer than two U-turns, or opposite sides)."""
    if len(uturns) < 2:
        return None
    (a1, b1, s1), (a2, b2, s2) = uturns[0], uturns[1]
    if s1 != s2:
        return None
    crossed = {a1: 0, a2: 1, b1: 2, b2: 3}
    if strip.accepts(_restricted(sides, crossed), uturns[:2], crossed):
        return crossed
    return None


def _intruder_control(sides, uturn):
    """Control (b) on one sample: True if `accepts` reports the synthetic
    `THROUGH` face (id -1) sitting between `uturn`'s two layers."""
    a1, b1, s1 = uturn
    fake_sides = _restricted(sides, (a1, b1))
    fake_sides[-1] = strip.THROUGH
    fake_order = {a1: 0, -1: 1, b1: 2}
    return bool(strip.accepts(fake_sides, ((a1, b1, s1),), fake_order))


def gate_refuses(d):
    """GATE 4. The oracle rejects what it must. Both controls required.

    (a) SEEDED INTERLEAVING: take a real line with two same-side U-turns and
        reorder the four faces so their arcs cross. `accepts` must report it.
    (b) INTRUDER: place a THROUGH strand between a real U-turn's layers.
        `accepts` must report it.

    A probe that accepts everything passes every other gate in this file, so
    without these two the run proves nothing.

    THESE ARE EXISTENCE CONTROLS, NOT A CENSUS. The loops `break` after the
    first line on which both controls have fired, so the result reports
    "at least one" of each, never a total. The returned keys say so
    (`*_at_least_one`).

    THE CONTROLS ARE DELIBERATELY EVALUATED ON A RESTRICTED `sides`. Each is
    handed a `sides` dict containing exactly the faces named in its synthetic
    order (`_restricted`), never the sample's full dict. `strip.pierced`
    evaluates `order[f]` for EVERY `THROUGH` face in `sides`, so passing the
    real dict alongside an order that covers only three or four faces raises
    `KeyError` the moment the sample has a real `THROUGH` face. Restricting
    makes each control test what it claims and independent of the sample's
    other faces.
    """
    seeded = intruder = 0
    witness = None
    for key in d["lines"]:
        bundle = d["bundles"][key]
        direction = L.direction_of(key)
        w = strip.perpendicular(direction)
        anchor = bundle[0][3][0]
        intervals = [L.span(direction, e[3]) for e in bundle]
        for t in strip.sub_segment_samples(strip.breakpoints(intervals)):
            p = strip.point_at(direction, anchor, t)
            faces = sorted({f for e in bundle for f in (e[0], e[1])})
            sides = strip.sides_at(d["polymap"], faces, p, w)
            uturns, _a = strip.uturns_at(
                strip.edges_at(bundle, direction, t, CREASE_KINDS), sides)
            if len(uturns) < 2 or uturns[0][2] != uturns[1][2]:
                continue
            crossed = _seeded_control(sides, uturns)
            if crossed is not None:
                seeded += 1
                (a1, b1, _s1), (a2, b2, _s2) = uturns[0], uturns[1]
                witness = {"line": str(key), "t": str(t),
                           "uturns": [[a1, b1], [a2, b2]],
                           "crossed_order": {str(k): v
                                             for k, v in crossed.items()}}
            if _intruder_control(sides, uturns[0]):
                intruder += 1
            if seeded and intruder:
                break
        if seeded and intruder:
            break
    if not seeded:
        raise SystemExit(
            "GATE 4 FAILED: no seeded interleaving was rejected. An oracle "
            "that accepts a crossing cannot distinguish a valid order from an "
            "invalid one, so every other figure in this run is meaningless.")
    if not intruder:
        raise SystemExit(
            "GATE 4 FAILED: the intruder control was not rejected.")
    return {"seeded_interleaving_rejected_at_least_one": bool(seeded),
            "intruder_rejected_at_least_one": bool(intruder),
            "seeded_witness": witness}


def gate_untouched():
    """GATE 10. Production is untouched.

    Asserted in code rather than left to a reviewer's eye, because every slice
    in this arc carries the same standing constraint and a diff that appears
    between a review and a push would otherwise go unnoticed.
    """
    import subprocess
    root = os.path.join(HERE, "..", "..", "..", "..")
    diff = subprocess.run(
        ["git", "-C", root, "diff", "origin/main", "--stat", "--",
         "mcp_harness/"],
        capture_output=True, text=True, check=True).stdout.strip()
    if diff:
        raise SystemExit(
            f"GATE 10 FAILED: mcp_harness/ differs from origin/main:\n{diff}")
    with open(os.path.join(root, "mcp_harness", "server.py")) as fh:
        hits = fh.read().count("box_pleat")
    if hits != 0:
        raise SystemExit(
            f"GATE 10 FAILED: server.py mentions box_pleat {hits} times; the "
            f"standing constraint is 0.")
    return {"mcp_harness_diff_empty": True, "server_box_pleat_mentions": 0}


def compare(oracle_pairs, production_pairs):
    """The set comparison of spec section 3, in both directions.

    Order-free on both sides: the oracle's elements come from geometry alone
    and production's from `cons.tacos`, so no candidate layer order enters.
    That is what makes this comparison incapable of going vacuous the way the
    predecessor's subset design did -- there is no sampled population to be
    empty.

    `only_oracle` non-empty  -> production's taco branch is INCOMPLETE.
    `only_production` non-empty -> production OVER-CONSTRAINS.
    """
    o, p = set(oracle_pairs), set(production_pairs)
    only_o, only_p = o - p, p - o

    def _w(s):
        return [sorted(sorted(x) for x in pair)
                for pair in sorted(s, key=lambda q: sorted(sorted(x)
                                                           for x in q))
                ][:MAX_WITNESSES]

    return {
        "oracle_pairs": len(o),
        "production_pairs": len(p),
        "identical": only_o == set() and only_p == set(),
        "only_oracle": len(only_o),
        "only_production": len(only_p),
        "only_oracle_witnesses": _w(only_o),
        "only_production_witnesses": _w(only_p),
    }


def gate_crossvalidate(d, pierces):
    """GATE 9. The strip's CONDITION 1 must reproduce the predecessor oracle's
    `equality` triples, on the creases it shares with them.

    This is what earns the condition-2 verdict its credibility: a brand-new
    instrument reproducing an already-established exhaustive result
    (28,192 = 28,192, zero either way) before anyone reads its new answer.

    Production's `equality` clauses carry the same information in the same
    shape, so the comparison is direct: `(through_face, {fa, fb})`.

    GATED NON-VACUOUS. The reproduced count must be > 0, or the control
    establishes nothing -- which is the failure mode this arc has hit twice.
    """
    prod = set()
    for la, lb, _prov in d["cons"].equalities:
        pa, pb = la[0], lb[0]
        shared = set(pa) & set(pb)
        if len(shared) != 1:
            continue
        x = shared.pop()
        fa = (set(pa) - {x}).pop()
        fb = (set(pb) - {x}).pop()
        prod.add((x, frozenset((fa, fb))))

    creases_on_lines = {frozenset((e[0], e[1]))
                        for key in d["lines"] for e in d["bundles"][key]
                        if e[2] in CREASE_KINDS}
    prod_here = {t for t in prod if t[1] in creases_on_lines}

    if not prod_here:
        raise SystemExit(
            "GATE 9 FAILED: production has no `equality` clause on any of the "
            "crease-overlapping lines, so the cross-validation control has an "
            "empty population and would pass vacuously.")
    if not pierces:
        raise SystemExit(
            "GATE 9 FAILED: the strip produced no condition-1 constraints on "
            "those lines while production has "
            f"{len(prod_here)}. The instrument is not reading the geometry.")

    only_o, only_p = pierces - prod_here, prod_here - pierces
    out = {
        "oracle_condition1": len(pierces),
        "production_equality_on_these_lines": len(prod_here),
        "only_oracle": len(only_o),
        "only_production": len(only_p),
        "reproduced": len(pierces & prod_here),
        "identical": not only_o and not only_p,
    }
    if not out["identical"]:
        out["only_oracle_witnesses"] = [
            [w[0], sorted(w[1])] for w in sorted(only_o)][:MAX_WITNESSES]
        out["only_production_witnesses"] = [
            [w[0], sorted(w[1])] for w in sorted(only_p)][:MAX_WITNESSES]
    return out


def _bundle_only_through(d):
    """The control for GATE 12: `walk_line` re-run with each line's face set
    restricted to the faces attached to that line's own bundle edges.

    Reports how many samples hold a `THROUGH` face WITHOUT the face-detection
    (line-clip) branch. If this is zero while the full walk's figure is not,
    the branch is load-bearing -- every `THROUGH` strand comes from it -- and
    that is a measurement, not an argument.
    """
    samples = through = subs = 0
    for key in d["lines"]:
        bundle = d["bundles"][key]
        faces = {f for e in bundle for f in (e[0], e[1])}
        d2 = dict(d, polymap={f: d["polymap"][f] for f in faces})
        r = walk_line(d2, key, bundle)
        samples += r["samples"]
        through += r["through_samples"]
        subs += r["sub_segments"]
    return {"samples": samples, "samples_with_a_through_face": through,
            "sub_segments": subs}


def _signed_area2(ring):
    """Twice the signed shoelace area; positive means counter-clockwise."""
    n = len(ring)
    return sum(ring[i][0] * ring[(i + 1) % n][1]
               - ring[(i + 1) % n][0] * ring[i][1] for i in range(n))


def input_census(d):
    """Facts about the INPUT that bound or explain the result.

    `folded_vertices` (read by `load_all` for crease segments) and `polys`
    (read for clipping) are two arrays over the same faces. Their windings are
    reported separately because mixing them silently inverts half the faces.

    `edge_assignments` reports how many edges are flat (`F`). Production's
    tortilla branches and this driver's `F` handling are exercised only if that
    count is non-zero; it is reported so the README's scope claim is read from
    the artifact rather than asserted.
    """
    ff = d["ff"]
    folded_cw = sum(1 for P in ff.folded_vertices
                    if _signed_area2([(float(x), float(y)) for x, y in P]) < 0)
    polys_non_ccw = sum(1 for P in d["polys"] if _signed_area2(P) <= 0)
    assignments = {}
    for e in d["edges"]:
        assignments[e[2]] = assignments.get(e[2], 0) + 1
    return {"faces": len(d["polys"]),
            "folded_vertices_clockwise": folded_cw,
            "polys_not_counter_clockwise": polys_non_ccw,
            "edge_assignments": assignments}


def run():
    """Every gate, then the comparison. The artifact's whole body."""
    t0 = time.time()
    d = load_all()
    gates = {
        "fidelity": gate_fidelity(),
        "faces_usable": gate_faces_usable(d),
        "accounting": gate_accounting(d),
        "transversal": gate_transversal(d),
        "sides": gate_sides(d),
        "constancy": gate_constancy(d),
        "refuses": gate_refuses(d),
        "untouched": gate_untouched(),
        "relation_scope": gate_relation_scope(d),
        "face_contribution": gate_face_contribution(d),
    }
    gates["face_contribution"]["bundle_faces_only"] = _bundle_only_through(d)

    oracle_tacos, oracle_pierces, anomalies = set(), set(), []
    per_line = []
    for key in d["lines"]:
        r = walk_line(d, key, d["bundles"][key])
        oracle_tacos |= r["taco_pairs"]
        oracle_pierces |= r["pierce_pairs"]
        anomalies.extend(r["anomalies"])
        per_line.append({"line": str(key), "samples": r["samples"],
                         "sub_segments": r["sub_segments"],
                         "taco_pairs": len(r["taco_pairs"])})

    if anomalies:
        raise SystemExit(
            f"REFUSED: {len(anomalies)} crease(s) read with faces on opposite "
            f"sides or a THROUGH face at a sample point. A crease's two faces "
            f"lie on one side by definition, so this is a disagreement about "
            f"which pairs are interpretable and must be resolved before the "
            f"comparison is read. Witnesses: {anomalies[:MAX_WITNESSES]}")

    headline = compare(oracle_tacos, d["tacos"])
    gates["crossvalidate"] = gate_crossvalidate(d, oracle_pierces)

    geometric = d["census"].get("equality", 0) + d["census"].get("taco", 0)
    return {
        "subject": "dense lizard (SAT-certified witness)",
        "kernel": "exact",
        "sat_verdict": d["sat_kind"],
        "faces": len(d["polys"]),
        "creases": len(d["creases"]),
        "edges": len(d["edges"]),
        "collinear_lines": len(d["lines"]),
        "clause_census": d["census"],
        "taco_counts": taco_counts(d),
        "input_census": input_census(d),
        "geometric_clauses": geometric,
        "taco_share_of_geometric": (round(d["census"].get("taco", 0)
                                          / geometric, 4)
                                    if geometric else None),
        "headline_comparison": headline,
        "verdict": "identical" if headline["identical"] else "DISAGREEMENT",
        "families_independently_checked": ["taco"],
        "families_cross_validated": ["equality"],
        "families_not_under_test": ["transitivity"],
        "gates": gates,
        "per_line": per_line,
        "python": ".".join(str(x) for x in sys.version_info[:3]),
        "sys_platform": sys.platform,
        "elapsed_secs": round(time.time() - t0, 1),
    }


def selftest():
    """Checks on the probe itself, run before the subject is touched.

    Every one of these is a property a bug could break while leaving the
    headline looking plausible.
    """
    F = Fraction
    checks = {}

    def rect(x0, y0, x1, y1):
        return [(F(x0), F(y0)), (F(x1), F(y0)), (F(x1), F(y1)), (F(x0), F(y1))]

    # 1-3: line identity.
    checks["line_key_collinear_equal"] = (
        L.line_key(((F(0), F(0)), (F(2), F(0))))
        == L.line_key(((F(9), F(0)), (F(4), F(0)))))
    checks["line_key_offset_differs"] = (
        L.line_key(((F(0), F(0)), (F(2), F(0))))
        != L.line_key(((F(0), F(1)), (F(2), F(1)))))
    checks["line_key_none_degenerate"] = (
        L.line_key(((F(1), F(1)), (F(1), F(1)))) is None)

    # 4-6: the cross-section.
    w = strip.perpendicular((1, 0))
    checks["side_through"] = (
        strip.side_at(rect(0, -1, 2, 1), (F(1), F(0)), w) == strip.THROUGH)
    checks["side_pos"] = (
        strip.side_at(rect(0, 0, 2, 1), (F(1), F(0)), w) == strip.SIDE_POS)
    checks["side_neg"] = (
        strip.side_at(rect(0, -1, 2, 0), (F(1), F(0)), w) == strip.SIDE_NEG)

    # 7: a clockwise ring must NOT read as a usable face. This is the defect
    # that the predecessor's first is_convex missed.
    cw = list(reversed(rect(0, 0, 2, 1)))
    checks["clockwise_ring_rejected"] = not stacks.is_convex(cw, K)

    # 8-10: the two conditions.
    nested = {0: 0, 2: 1, 3: 2, 1: 3}
    crossed = {0: 0, 2: 1, 1: 2, 3: 3}
    u = ((0, 1, strip.SIDE_POS), (2, 3, strip.SIDE_POS))
    checks["nested_accepted"] = not strip.interleaved(u[0], u[1], nested)
    checks["crossed_rejected"] = strip.interleaved(u[0], u[1], crossed)
    checks["cross_side_accepted"] = not strip.interleaved(
        (0, 1, strip.SIDE_POS), (2, 3, strip.SIDE_NEG), crossed)

    # 11: the emission is order-free.
    checks["taco_pairs_order_free"] = (
        strip.taco_pairs(u) == strip.taco_pairs((u[1], u[0])))

    # 12: a pierce is found and a non-pierce is not.
    sides = {0: strip.SIDE_POS, 1: strip.SIDE_POS, 5: strip.THROUGH}
    checks["pierce_found"] = strip.pierced(
        (0, 1, strip.SIDE_POS), sides, {0: 0, 5: 1, 1: 2}) == (5,)
    checks["pierce_outside_ignored"] = strip.pierced(
        (0, 1, strip.SIDE_POS), sides, {0: 0, 1: 1, 5: 2}) == ()

    # 13-14: exhaustive sampling.
    bps = strip.breakpoints([(F(0), F(2)), (F(1), F(3))])
    checks["breakpoints_sorted_unique"] = bps == (F(0), F(1), F(2), F(3))
    checks["samples_strictly_inside"] = all(
        bps[i] < t < bps[i + 1]
        for i, t in enumerate(strip.sub_segment_samples(bps)))

    # 15: point_at inverts project.
    checks["point_at_inverts_project"] = all(
        L.project((1, 2), strip.point_at((1, 2), (F(1), F(1)), F(t))) == F(t)
        for t in (-3, 0, 4))

    # 16: `compare` is not a constant. A comparator that always reports
    # identical would reproduce this run's best outcome exactly.
    a = {frozenset((frozenset((0, 1)), frozenset((2, 3))))}
    b = {frozenset((frozenset((0, 1)), frozenset((4, 5))))}
    checks["compare_detects_difference"] = (
        not compare(a, b)["identical"]
        and compare(a, b)["only_oracle"] == 1
        and compare(a, b)["only_production"] == 1)
    checks["compare_detects_identity"] = compare(a, a)["identical"]

    failed = sorted(k for k, v in checks.items() if not v)
    if failed:
        raise SystemExit(f"SELFTEST FAILED: {failed}")
    return {"checks": len(checks), "passed": len(checks)}


def main(out_path=ART):
    st = selftest()
    print(f"selftest: {st['passed']}/{st['checks']}")
    result = run()
    result["selftest"] = st
    with open(out_path, "w") as fh:
        json.dump(result, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print(json.dumps({k: result[k] for k in
                      ("verdict", "headline_comparison", "collinear_lines",
                       "taco_share_of_geometric")},
                     indent=2, sort_keys=True))
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
