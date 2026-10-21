"""Tests for layer_order.py (folded-state-first slice 2).

Spec: docs/superpowers/specs/2026-07-04-layer-order-slice2-design.md
Hand-derived fixtures: a 1x3 paper strip with two creases at x=1, x=2.
Both M and V reflect identically in flat_fold, so V+M and V+V strips
fold to the SAME geometry (all three unit faces stacked over [0,1]^2)
and differ only in layer order — V+M is the accordion (fully forced),
V+V leaves the outer pair genuinely free (spiral vs tuck are both
physically valid).
"""
import json
import os
from itertools import combinations

import numpy as np
import pytest

from pleatwright.certify.flat_fold import flat_fold
from pleatwright.certify.layer_order import (
    INTERIOR_EPS,
    AmbiguousStack,
    LayerOrder,
    _Constraints,
    _area,
    _cells,
    _clip_seg,
    _collinear_overlap,
    _is_convex,
    _lit,
    _orientation,
    _propagate,
    _segs_interact,
    _split_convex,
    _strictly_inside,
    constraints_for,
    layer_order,
    needs_flat_edge,
)

GOLDENS = os.path.join(os.path.dirname(__file__), "goldens")

# Measured pins (Task 3 Step 4 prints these; see plan). The probe point
# is an interior point of the deepest star-4 cell; the stack is the
# propagator's forced total order there, hand-checked pairwise.
STAR4_PROBE_POINT = (0.666667, 0.833333)
STAR4_EXPECTED_STACK = [6, 1, 5, 2, 7, 3, 4, 0]

# S2′a (2026-08-07) moved BOTH of these from honest ambiguity to a total
# order. Nothing was refuted and then accepted — the tortilla families the
# old F filter dropped link pair-variables the crease seeds never connected,
# so relations that were free became FORCED. Measured before/after over all
# 20 goldens+cases: 1315 previously-forced relations, 0 lost, 0 flipped,
# 742 newly forced. The stacks below are validated by check_order(), which
# re-derives every rule independently of layer_order's implementation.
DOG_DEEPEST_COVER = 20
DOG_DEEPEST_RESULT = ("stack", [11, 23, 10, 25, 12, 14, 16, 26, 15, 13,
                                8, 9, 3, 6, 19, 27, 7, 2, 20, 1])
QUAD_DEEPEST_COVER = 6
QUAD_DEEPEST_RESULT = ("stack", [8, 2, 3, 5, 7, 0])


def load_golden(name):
    with open(os.path.join(GOLDENS, name)) as fh:
        return json.load(fh)


def strip_fold(a1, a2):
    """1x3 strip, creases at x=1 (a1) and x=2 (a2)."""
    return {
        "vertices_coords": [[0, 0], [1, 0], [2, 0], [3, 0],
                            [3, 1], [2, 1], [1, 1], [0, 1]],
        "edges_vertices": [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5],
                           [5, 6], [6, 7], [7, 0], [1, 6], [2, 5]],
        "edges_assignment": ["B", "B", "B", "B", "B", "B", "B", "B",
                             a1, a2],
    }


def strip_split_fold(a1, a2, flat="F"):
    """1x3 strip (creases at x=1, x=2) whose MIDDLE face carries an
    UNFOLDED edge at x=1.5, splitting it into a flat pair.

    Folded (root = face [0,1]): [1,1.5] -> [0.5,1], [1.5,2] -> [0,0.5],
    [2,3] -> [0,1]. So the flat edge's image is the segment x=0.5, which
    lies strictly INSIDE both unit faces — the tortilla-tortilla
    configuration, and the ONLY new family this fixture can trip: the two
    creases fold onto x=1 and x=0, so neither shares a segment with it."""
    return {
        "vertices_coords": [[0, 0], [1, 0], [1.5, 0], [2, 0], [3, 0],
                            [3, 1], [2, 1], [1.5, 1], [1, 1], [0, 1]],
        "edges_vertices": [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5],
                           [5, 6], [6, 7], [7, 8], [8, 9], [9, 0],
                           [1, 8], [2, 7], [3, 6]],
        "edges_assignment": ["B"] * 10 + [a1, flat, a2],
    }


def strip4_fold(a1, a2, a3):
    """1x4 strip, creases at x=1 (a1), x=2 (a2), x=3 (a3). All four unit
    faces fold onto the same [0,1]^2 square, so the outer creases'
    folded segments land collinearly on the square's boundary and
    genuinely interact (taco-taco candidate) — see TestTacoTacoWiring."""
    return {
        "vertices_coords": [[0, 0], [1, 0], [2, 0], [3, 0], [4, 0],
                            [4, 1], [3, 1], [2, 1], [1, 1], [0, 1]],
        "edges_vertices": [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5],
                           [5, 6], [6, 7], [7, 8], [8, 9], [9, 0],
                           [1, 8], [2, 7], [3, 6]],
        "edges_assignment": ["B"] * 10 + [a1, a2, a3],
    }


def face_at(fold, result, p):
    """Index of the face whose FLAT polygon strictly contains p."""
    V = np.asarray([v[:2] for v in fold["vertices_coords"]], dtype=float)
    for i, f in enumerate(result.faces):
        if _strictly_inside(p, V[f]):
            return i
    raise AssertionError(f"no face contains {p}")


class TestSharedEdges:
    def test_strip_shared_edges_carry_assignments(self):
        fold = strip_fold("V", "M")
        res = flat_fold(fold)
        assert len(res.shared_edges) == 2
        by_edge = {k: (fa, fb, a) for fa, fb, k, a in res.shared_edges}
        assert set(by_edge) == {(1, 6), (2, 5)}
        assert by_edge[(1, 6)][2] == "V"
        assert by_edge[(2, 5)][2] == "M"


class TestGeometry:
    def test_split_convex_partitions_area(self):
        sq = np.array([[0.0, 0], [2, 0], [2, 2], [0, 2]])
        off = np.array([[1.0, 1], [3, 1], [3, 3], [1, 3]])
        inter, pieces = _split_convex(sq, off)
        assert inter is not None
        total = abs(_area_of(inter)) + sum(abs(_area_of(p)) for p in pieces)
        assert abs(total - 4.0) < 1e-9          # partitions the subject
        assert abs(abs(_area_of(inter)) - 1.0) < 1e-9

    def test_split_convex_disjoint(self):
        sq = np.array([[0.0, 0], [1, 0], [1, 1], [0, 1]])
        far = np.array([[5.0, 5], [6, 5], [6, 6], [5, 6]])
        inter, pieces = _split_convex(sq, far)
        assert inter is None
        assert sum(abs(_area_of(p)) for p in pieces) == pytest.approx(1.0)

    def test_cells_identical_stack(self):
        # V+M strip folds all three faces onto [0,1]^2: exactly one cell
        res = flat_fold(strip_fold("V", "M"))
        polys = [_ccw(np.asarray(P)) for P in res.folded_vertices]
        cells = _cells(polys)
        assert len(cells) == 1
        assert cells[0][1] == frozenset({0, 1, 2})

    def test_cells_partial_overlap(self):
        a = np.array([[0.0, 0], [2, 0], [2, 2], [0, 2]])
        b = np.array([[1.0, 1], [3, 1], [3, 3], [1, 3]])
        cells = _cells([a, b])
        covers = sorted(tuple(sorted(c)) for _, c in cells)
        assert covers.count((0, 1)) == 1
        assert sum(abs(_area_of(p)) for p, c in cells if c == frozenset({0, 1})) \
            == pytest.approx(1.0)
        total = sum(abs(_area_of(p)) for p, _ in cells)
        assert total == pytest.approx(7.0)      # union area, disjoint cells

    def test_cells_cover_membership_is_consistent(self):
        # every cell's centroid must lie strictly inside exactly its cover
        res = flat_fold(load_golden("quad.fold"))
        polys = [_ccw(np.asarray(P)) for P in res.folded_vertices]
        cells = _cells(polys)
        for poly, cover in cells:
            if abs(_area_of(poly)) < 1e-6:
                continue     # sliver cells: centroid too close to
                             # boundaries for a 1e-9-tolerance check
            centroid = np.mean(poly, axis=0)
            inside = {i for i, fp in enumerate(polys)
                      if _strictly_inside(centroid, fp)}
            assert inside == set(cover)

    def test_split_convex_shared_edge_shapes(self):
        # crease-adjacent folded faces share an edge exactly; clipping
        # must not fabricate vertices (reviewer's quad.fold counterexample)
        fold = load_golden("quad.fold")
        res = flat_fold(fold)
        polys = [_ccw(np.asarray(P)) for P in res.folded_vertices]
        inter, pieces = _split_convex(polys[1], polys[0])
        probe = np.array([0.3277, 0.5629])
        containers = [p for p in ([inter] if inter is not None else []) + pieces
                      if _covers(probe, p)]
        assert len(containers) == 1

    @pytest.mark.parametrize("fixture,seed,samples", [
        ("quad", 0, 2000),
        # bear-base is the high-face-count case (44 convex folded faces)
        # that surfaced the chained-clip sliver-gap regression (~5.8% holes
        # before fix wave 2). Non-convex faces are out of contract, excluded.
        ("bear", 1, 4000),
    ])
    def test_cells_have_no_holes(self, fixture, seed, samples):
        # every sampled point interior to some face must be covered by a
        # returned cell (no HOLES) and by a cell naming exactly the
        # containing faces (no WRONG-COVER). Both are asserted separately.
        polys = _convex_folded_polys(fixture)
        cells = _cells(polys)
        rng = np.random.default_rng(seed)
        lo = np.min([p.min(0) for p in polys], axis=0)
        hi = np.max([p.max(0) for p in polys], axis=0)
        holes = 0
        wrong = 0
        checked = 0
        for _ in range(samples):
            pt = lo + rng.random(2) * (hi - lo)
            inside = {i for i, fp in enumerate(polys)
                      if _strictly_inside(pt, fp)}
            if not inside:
                continue
            checked += 1
            hits = [c for p, c in cells if _covers(pt, p)]
            if not hits:
                holes += 1
            elif inside not in [set(h) for h in hits]:
                wrong += 1
        assert checked > 200          # the sample actually exercised the union
        assert holes / checked < 0.02     # no silent holes
        assert wrong / checked < 0.02     # covers name the right faces


def _convex_folded_polys(fixture):
    """Convex CCW folded faces of a fixture (non-convex faces excluded:
    they are out of _cells's contract)."""
    res = flat_fold(load_golden(f"{fixture}-base.fold" if fixture == "bear"
                                else f"{fixture}.fold"))
    polys = []
    for P in res.folded_vertices:
        Q = _ccw(np.asarray(P, dtype=float))
        if _is_convex(Q):
            polys.append(Q)
    return polys


def _area_of(P):
    x, y = P[:, 0], P[:, 1]
    return 0.5 * float(np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y))


def _ccw(P):
    return P if _area_of(P) > 0 else P[::-1]


def _covers(p, P, eps=1e-7):
    n = len(P)
    q = np.asarray(p, dtype=float)
    return all((P[(i + 1) % n][0] - P[i][0]) * (q[1] - P[i][1])
               - (P[(i + 1) % n][1] - P[i][1]) * (q[0] - P[i][0]) >= -eps
               for i in range(n))


def _constraints_for(fold):
    """Delegates to the public `constraints_for` so this helper and the
    production entry point cannot drift apart (Task 3)."""
    res = flat_fold(fold)
    cons, _slots = constraints_for(res)
    return res, cons


def test_prov_str_is_the_old_message():
    from pleatwright.certify.layer_order import Prov
    p = Prov("taco-tortilla crease (3, 7)", creases=((3, 7),), faces=(1, 2))
    assert str(p) == "taco-tortilla crease (3, 7)"
    assert f"{p} through face 9" == "taco-tortilla crease (3, 7) through face 9"


class TestLit:
    def test_lit_canonicalization(self):
        assert _lit(2, 5) == ((2, 5), False)   # "2 above 5" is rel itself
        assert _lit(5, 2) == ((2, 5), True)    # "5 above 2" is NOT rel


class TestSegPredicates:
    def test_clip_seg_inside(self):
        sq = np.array([[0.0, 0], [1, 0], [1, 1], [0, 1]])
        span = _clip_seg((np.array([-1.0, 0.5]), np.array([2.0, 0.5])), sq)
        t0, t1 = span
        assert t0 == pytest.approx(1 / 3)
        assert t1 == pytest.approx(2 / 3)

    def test_clip_seg_outside(self):
        sq = np.array([[0.0, 0], [1, 0], [1, 1], [0, 1]])
        assert _clip_seg((np.array([2.0, 2]), np.array([3.0, 3])), sq) is None

    def test_segs_proper_cross(self):
        s1 = (np.array([0.0, 0]), np.array([2.0, 2]))
        s2 = (np.array([0.0, 2]), np.array([2.0, 0]))
        assert _segs_interact(s1, s2)

    def test_segs_collinear_overlap(self):
        s1 = (np.array([0.0, 0]), np.array([2.0, 0]))
        s2 = (np.array([1.0, 0]), np.array([3.0, 0]))
        assert _segs_interact(s1, s2)

    def test_segs_disjoint_and_touching(self):
        s1 = (np.array([0.0, 0]), np.array([1.0, 0]))
        s2 = (np.array([2.0, 0]), np.array([3.0, 0]))
        assert not _segs_interact(s1, s2)
        s3 = (np.array([1.0, 0]), np.array([2.0, 0]))   # endpoint touch
        assert not _segs_interact(s1, s3)


class TestConstraintGeneration:
    def test_strip_vm_direct_constraints(self):
        fold = strip_fold("V", "M")
        res, cons = _constraints_for(fold)
        A = face_at(fold, res, (0.5, 0.5))
        B = face_at(fold, res, (1.5, 0.5))
        C = face_at(fold, res, (2.5, 0.5))
        assert len(cons.direct) == 2
        # decode each direct constraint into canonical rel facts:
        # rel[(lo,hi)] means "lo above hi"; the stored value is the raw
        # proposition, so apply the literal's flip
        facts = {}
        for (pair, flip), value, _ in cons.direct:
            facts[pair] = (value != flip)
        ab = tuple(sorted((A, B)))
        bc = tuple(sorted((B, C)))
        # V at x=1: B above A; M at x=2 (B is face-down): C above B
        assert facts[ab] == (ab[0] == B)
        assert facts[bc] == (bc[0] == C)

    def test_strip_vv_direct_constraints_differ(self):
        fold = strip_fold("V", "V")
        res, cons = _constraints_for(fold)
        B = face_at(fold, res, (1.5, 0.5))
        C = face_at(fold, res, (2.5, 0.5))
        facts = {}
        for (pair, flip), value, _ in cons.direct:
            facts[pair] = (value != flip)
        bc = tuple(sorted((B, C)))
        # second V, reference face-down: C below B
        assert facts[bc] == (bc[0] == B)

    def test_strip_has_no_taco_constraints(self):
        # folded creases land exactly ON face boundaries (x=0 and x=1
        # edges) — strictly-inside filtering must exclude them
        _, cons = _constraints_for(strip_fold("V", "V"))
        assert cons.equalities == ()
        assert cons.tacos == ()

    def test_every_constraint_names_overlapping_pairs(self):
        res, cons = _constraints_for(load_golden("star-4.fold"))
        for (pair, _), _, _ in cons.direct:
            assert pair in cons.pairs
        for la, lb, _ in cons.equalities:
            assert la[0] in cons.pairs and lb[0] in cons.pairs
        for (p, q), (r, s), _ in cons.tacos:
            for x, f in ((r, p), (r, q), (s, p), (s, q)):
                assert tuple(sorted((x, f))) in cons.pairs


class TestTacoTacoElimination:
    """The 1x4 strip (strip4_fold) DOES wire up a real taco-taco
    constraint (both outer creases fold their segments onto the same
    square boundary and interact), but honest experimentation across
    all 8 M/V assignment combinations shows crease-direction +
    transitivity ALREADY force every pair the taco-taco constraint
    would touch — so no strip4 assignment exercises the elimination
    arithmetic as a FORCING rule (matches the memory note that this is
    common). Per the finding, we therefore split coverage in two:
    this class asserts the constraint exists and is correctly formed
    (wiring), then unit-tests `_propagate`'s 3-of-4 elimination
    directly on a hand-built `_Constraints` (arithmetic)."""

    def test_taco_taco_constraint_wired_for_strip4(self):
        # V,V,V: measured (see finding) — outer creases (1,8) and (3,6)
        # both fold onto the unit square's boundary and interact.
        fold = strip4_fold("V", "V", "V")
        _, cons = _constraints_for(fold)
        assert len(cons.tacos) == 2   # both directions recorded
        seen = {(pq, rs) for pq, rs, _ in cons.tacos}
        assert seen == {((0, 1), (2, 3)), ((2, 3), (0, 1))}
        for (p, q), (r, s), _ in cons.tacos:
            for x, f in ((r, p), (r, q), (s, p), (s, q)):
                assert tuple(sorted((x, f))) in cons.pairs

    def test_taco_taco_redundant_with_transitivity_on_strip4(self):
        # Documents WHY the forcing-pair construction was abandoned:
        # for every assignment, removing the taco-taco constraints
        # changes nothing forced (transitivity/crease-direction alone
        # already pin everything the taco constraint could pin here).
        import dataclasses
        for combo in (("M", "M", "M"), ("M", "V", "V"), ("V", "M", "V"),
                     ("V", "V", "M"), ("V", "V", "V")):
            fold = strip4_fold(*combo)
            res, cons = _constraints_for(fold)
            assert cons.tacos    # the constraint IS present
            rel_with = _propagate(cons)
            rel_without = _propagate(dataclasses.replace(cons, tacos=()))
            assert rel_with == rel_without

    def _elim_consts(self, direct):
        # Synthetic taco: p=0,q=1 (one crease's faces), r=2,s=3
        # (another crease's faces); pairs cover exactly the four
        # cross-relations the elimination rule reads/writes.
        pairs = frozenset({(0, 2), (1, 2), (0, 3), (1, 3)})
        tacos = (((0, 1), (2, 3), "test taco"),)
        return _Constraints(pairs=pairs, direct=tuple(direct), equalities=(),
                            tacos=tacos, covers=())

    def _above(self, rel, x, f):
        pair, flip = _lit(x, f)
        v = rel.get(pair)
        return None if v is None else (v != flip)

    def test_forces_fourth_relation_straddles_true(self):
        # r straddles (p,q): r above p, r below q -> between(r) = True.
        # s above p is known; taco-taco must force s below q so that
        # between(s) also comes out True.
        cons = self._elim_consts([
            (_lit(2, 0), True, "r above p"),
            (_lit(2, 1), False, "r below q"),
            (_lit(3, 0), True, "s above p"),
        ])
        rel = _propagate(cons)
        assert self._above(rel, 3, 1) is False
        between_r = self._above(rel, 2, 0) != self._above(rel, 2, 1)
        between_s = self._above(rel, 3, 0) != self._above(rel, 3, 1)
        assert between_r == between_s is True

    def test_forces_fourth_relation_straddles_false(self):
        # r does NOT straddle (p,q): r above both -> between(r) = False.
        # s above p is known; taco-taco must force s ALSO above q so
        # between(s) comes out False too.
        cons = self._elim_consts([
            (_lit(2, 0), True, "r above p"),
            (_lit(2, 1), True, "r above q"),
            (_lit(3, 0), True, "s above p"),
        ])
        rel = _propagate(cons)
        assert self._above(rel, 3, 1) is True
        between_r = self._above(rel, 2, 0) != self._above(rel, 2, 1)
        between_s = self._above(rel, 3, 0) != self._above(rel, 3, 1)
        assert between_r == between_s is False

    def test_all_known_contradiction_raises(self):
        # All four cross-relations known but between(r) != between(s):
        # the taco-taco constraint must be violated and raise.
        cons = self._elim_consts([
            (_lit(2, 0), True, "r above p"),
            (_lit(2, 1), False, "r below q"),   # between(r) = True
            (_lit(3, 0), True, "s above p"),
            (_lit(3, 1), True, "s above q"),    # between(s) = False
        ])
        with pytest.raises(ValueError, match="contradiction"):
            _propagate(cons)


class TestHandDerivedStrips:
    def test_vm_accordion_fully_forced(self):
        # V then M = accordion/zigzag: stack C,B,A top-to-bottom.
        # THIS TEST PINS THE SIGN CONVENTION — if it fails with the
        # exact inverse stack [A,B,C], flip the convention in
        # _build_constraints once (see plan Global Constraints), never
        # this expectation.
        fold = strip_fold("V", "M")
        res = flat_fold(fold)
        layers = layer_order(res)
        A = face_at(fold, res, (0.5, 0.5))
        B = face_at(fold, res, (1.5, 0.5))
        C = face_at(fold, res, (2.5, 0.5))
        assert layers.above(B, A) is True
        assert layers.above(C, B) is True
        assert layers.above(C, A) is True          # via transitivity
        assert layers.stack_at((0.5, 0.5)) == [C, B, A]

    def test_vv_outer_pair_genuinely_free(self):
        # V then V: B above A and C below B are forced; A-vs-C is
        # genuinely free (spiral and tuck are both physically valid)
        fold = strip_fold("V", "V")
        res = flat_fold(fold)
        layers = layer_order(res)
        A = face_at(fold, res, (0.5, 0.5))
        B = face_at(fold, res, (1.5, 0.5))
        C = face_at(fold, res, (2.5, 0.5))
        assert layers.above(B, A) is True
        assert layers.above(B, C) is True
        assert layers.above(A, C) is None
        assert layers.above(C, A) is None
        with pytest.raises(AmbiguousStack) as exc:
            layers.stack_at((0.5, 0.5))
        assert exc.value.free_pairs == [tuple(sorted((A, C)))]


class TestContract:
    def test_bear_refused_with_closure_count(self):
        res = flat_fold(load_golden("bear-base.fold"))
        with pytest.raises(ValueError, match=r"15 closure-inconsistent"):
            layer_order(res)

    def test_constraints_for_refuses_the_same_input(self):
        """The public builder must refuse a closure-inconsistent state too.

        `layer_order()` (above) and `mv_symmetrize._LayerGate` both guard on
        `closure.bad_edges`; `constraints_for` is the third entry point into
        the same machinery, and a caller that skips the check would get a
        constraint system built from a folded state that has no consistent
        flat fold -- meaningless rather than merely unsatisfiable."""
        res = flat_fold(load_golden("bear-base.fold"))
        with pytest.raises(ValueError, match=r"15 closure-inconsistent"):
            constraints_for(res)

    def test_above_antisymmetry_and_nonoverlap(self):
        fold = strip_fold("V", "M")
        res = flat_fold(fold)
        layers = layer_order(res)
        A = face_at(fold, res, (0.5, 0.5))
        B = face_at(fold, res, (1.5, 0.5))
        assert layers.above(A, B) is (not layers.above(B, A))
        assert layers.above(A, A) is None      # a face vs itself: no pair

    def test_stack_at_uncovered_point(self):
        res = flat_fold(strip_fold("V", "M"))
        layers = layer_order(res)
        assert layers.stack_at((10.0, 10.0)) == []

    def test_deterministic(self):
        fold = load_golden("star-4.fold")
        res = flat_fold(fold)
        l1, l2 = layer_order(res), layer_order(res)
        pairs = sorted(l1._pairs)
        assert pairs == sorted(l2._pairs)
        assert all(l1.above(a, b) == l2.above(a, b) for a, b in pairs)

    def test_cells_property_shape(self):
        res = flat_fold(strip_fold("V", "M"))
        layers = layer_order(res)
        cells = layers.cells
        assert len(cells) == 1
        point, cover = cells[0]
        assert cover == frozenset({0, 1, 2})
        assert point.shape == (2,)


class TestStar4Center:
    def test_center_stack_is_measured_total_order(self):
        # Measured pin (plan Task 3 Step 4): the star-4 fan at a point
        # near the folded center. Sanity requirements enforced here:
        # a total order over all faces covering the point, and every
        # ADJACENT-in-stack crease-connected pair must match the
        # crease-direction rule (hand-checkable from the M/V labels).
        res = flat_fold(load_golden("star-4.fold"))
        layers = layer_order(res)
        stack = layers.stack_at(STAR4_PROBE_POINT)
        assert stack == STAR4_EXPECTED_STACK


# ---------------------------------------------------------------------
# Independent checker: validates a LayerOrder's FORCED relations against
# the constraint definitions (spec §3 stage 2) using its own primitive
# helpers — it reads layers.above() but shares none of the module's
# constraint/propagation code.

def _chk_inside(p, P):
    n = len(P)
    q = np.asarray(p, dtype=float)
    return all((P[(i + 1) % n][0] - P[i][0]) * (q[1] - P[i][1])
               - (P[(i + 1) % n][1] - P[i][1]) * (q[0] - P[i][0]) > 1e-9
               for i in range(n))


def _chk_segs_interact(s1, s2):
    """Independent reimplementation of the taco-taco segment-interaction
    predicate (proper cross OR collinear-overlap; endpoint touch does
    not count) — deliberately not importing _segs_interact so the
    checker shares no code with the module under test."""
    p, q = np.asarray(s1[0], float), np.asarray(s1[1], float)
    r, s = np.asarray(s2[0], float), np.asarray(s2[1], float)

    def cross(u, v):
        return u[0] * v[1] - u[1] * v[0]

    d1, d2 = q - p, s - r
    o1, o2 = cross(d1, r - p), cross(d1, s - p)
    o3, o4 = cross(d2, p - r), cross(d2, q - r)
    if all(abs(o) < 1e-9 for o in (o1, o2, o3, o4)):
        length = float(np.hypot(*d1))
        if length < 1e-9:
            return False
        u = d1 / length
        b0, b1 = sorted((float(np.dot(r - p, u)), float(np.dot(s - p, u))))
        return min(length, b1) - max(0.0, b0) > 1e-9
    strad1 = (o1 > 1e-9 and o2 < -1e-9) or (o1 < -1e-9 and o2 > 1e-9)
    strad2 = (o3 > 1e-9 and o4 < -1e-9) or (o3 < -1e-9 and o4 > 1e-9)
    return strad1 and strad2


def check_order(fold, layers):
    res = flat_fold(fold)
    polys = [_ccw(np.asarray(P)) for P in res.folded_vertices]
    orient = [1 if np.linalg.det(T[:2, :2]) > 0 else -1
              for T in res.transforms]
    # 1. acyclicity: forced relations admit consistent heights per cell
    for point, cover in layers.cells:
        faces = sorted(cover)
        graph = {f: {g for g in faces if layers.above(f, g) is True}
                 for f in faces}
        seen, done = set(), set()

        def dfs(u):
            seen.add(u)
            for v in graph[u]:
                assert v not in seen or v in done, \
                    f"cycle in forced order within cell at {point}"
                if v not in done:
                    dfs(v)
            done.add(u)

        for f in faces:
            if f not in done:
                dfs(f)
    # 2. crease-direction rule, independently recomputed
    for fa, fb, k, a in res.shared_edges:
        if a not in ("M", "V"):
            continue
        got = layers.above(fb, fa)
        if got is None:
            continue                      # pair may not overlap
        expected = (a == "V") == (orient[fa] == 1)
        assert got == expected, f"crease rule violated at {k} ({a})"
    # 3. taco-tortilla by sampling folded crease midpoints: any face
    # strictly containing the midpoint must not separate the pair
    for fa, fb, k, a in res.shared_edges:
        if a not in ("M", "V"):
            continue
        face = res.faces[fa]
        i0, i1 = face.index(k[0]), face.index(k[1])
        mid = (np.asarray(res.folded_vertices[fa][i0])
               + np.asarray(res.folded_vertices[fa][i1])) / 2.0
        for x in range(len(polys)):
            if x in (fa, fb) or not _chk_inside(mid, polys[x]):
                continue
            va, vb = layers.above(x, fa), layers.above(x, fb)
            if va is not None and vb is not None:
                assert va == vb, \
                    f"face {x} separates taco {k}: {va} vs {vb}"
    # 4. taco-taco, independently recomputed: for every pair of M/V
    # creases whose folded segments interact, when all four cross-pair
    # relations are forced, the two creases must straddle each other
    # consistently: between(r;p,q) == between(s;p,q)
    mv_creases = []
    for fa, fb, k, a in res.shared_edges:
        if a not in ("M", "V"):
            continue
        face = res.faces[fa]
        i0, i1 = face.index(k[0]), face.index(k[1])
        seg = (np.asarray(res.folded_vertices[fa][i0]),
               np.asarray(res.folded_vertices[fa][i1]))
        mv_creases.append((fa, fb, k, seg))
    for (p, q, k1, seg1), (r, s, k2, seg2) in combinations(mv_creases, 2):
        if not _chk_segs_interact(seg1, seg2):
            continue
        rp, rq = layers.above(r, p), layers.above(r, q)
        sp, sq = layers.above(s, p), layers.above(s, q)
        if None in (rp, rq, sp, sq):
            continue
        assert (rp != rq) == (sp != sq), \
            f"taco-taco violated between creases {k1} and {k2}"
    # 5. tortilla-tortilla by sampling folded FLAT-edge midpoints (S2′a):
    # an UNFOLDED shared edge joins two faces of ONE uncreased sheet, so a
    # face strictly containing the midpoint cannot lie between them. Same
    # sampling shape as (3), deliberately: it re-derives the rule from
    # res.shared_edges rather than trusting _build_constraints' clipping.
    for fa, fb, k, a in res.shared_edges:
        if a in ("M", "V"):
            continue
        face = res.faces[fa]
        i0, i1 = face.index(k[0]), face.index(k[1])
        mid = (np.asarray(res.folded_vertices[fa][i0])
               + np.asarray(res.folded_vertices[fa][i1])) / 2.0
        for x in range(len(polys)):
            if x in (fa, fb) or not _chk_inside(mid, polys[x]):
                continue
            va, vb = layers.above(x, fa), layers.above(x, fb)
            if va is not None and vb is not None:
                assert va == vb, \
                    f"face {x} threads flat edge {k}: {va} vs {vb}"


CONSISTENT_FIXTURES = ["quad.fold", "hshape.fold", "dog.fold",
                       "star-4.fold"]


class TestSelfConsistency:
    @pytest.mark.parametrize("name", CONSISTENT_FIXTURES)
    def test_forced_relations_satisfy_constraints(self, name):
        fold = load_golden(name)
        layers = layer_order(flat_fold(fold))
        check_order(fold, layers)

    def test_strips_pass_checker_too(self):
        for a1, a2 in (("V", "M"), ("V", "V"), ("M", "M"), ("M", "V")):
            fold = strip_fold(a1, a2)
            check_order(fold, layer_order(flat_fold(fold)))


class TestFixturePins:
    # Measured drift tripwires (Task 4 Step 3 prints these): the stack
    # or honest ambiguity at the deepest cell of each real fixture.
    def test_dog_deepest_cell(self):
        layers = layer_order(flat_fold(load_golden("dog.fold")))
        point, cover = max(layers.cells, key=lambda c: len(c[1]))
        assert len(cover) == DOG_DEEPEST_COVER
        try:
            stack = layers.stack_at(point)
            assert DOG_DEEPEST_RESULT == ("stack", stack)
        except AmbiguousStack as e:
            assert DOG_DEEPEST_RESULT == ("free", len(e.free_pairs))

    def test_quad_deepest_cell(self):
        layers = layer_order(flat_fold(load_golden("quad.fold")))
        point, cover = max(layers.cells, key=lambda c: len(c[1]))
        assert len(cover) == QUAD_DEEPEST_COVER
        try:
            stack = layers.stack_at(point)
            assert QUAD_DEEPEST_RESULT == ("stack", stack)
        except AmbiguousStack as e:
            assert QUAD_DEEPEST_RESULT == ("free", len(e.free_pairs))


# --------------------------------------------------------------------- #
# S2′a — the constraint families the old `if a not in ("M","V")` filter   #
# dropped.  Spec: docs/superpowers/specs/2026-08-06-mv-symmetrize-        #
# design.md §2; formulation: Akitaya, Demaine & Ku, "Computing            #
# Flat-Folded States" (OSME 2024).                                        #
# --------------------------------------------------------------------- #
def _flip(fold, indices):
    """A COMMITTED golden with some M/V labels swapped. flat_fold maps M
    and V to the SAME reflection, so the folded geometry — and therefore
    every cell, pair and taco — is bit-identical; only the boolean seed of
    each `direct` constraint moves. Golden edge indices are stable because
    the file is committed (a recompiled fold's are not)."""
    out = dict(fold)
    a = list(fold["edges_assignment"])
    for i in indices:
        assert a[i] in ("M", "V"), f"edge {i} is {a[i]}, not a crease"
        a[i] = "V" if a[i] == "M" else "M"
    out["edges_assignment"] = a
    return out


def _pre_s2a(cons):
    """The same constraint object with every flat-edge family removed —
    i.e. exactly the oracle that shipped before S2′a."""
    return _Constraints(
        pairs=cons.pairs, direct=cons.direct,
        equalities=tuple(e for e in cons.equalities
                         if not needs_flat_edge(e[2])),
        tacos=cons.tacos, covers=cons.covers)


class TestTortillaWiring:
    """Hand-derived: the 1x3 strip whose middle face carries a flat edge."""

    def test_flat_edge_yields_exactly_the_two_spanning_equalities(self):
        res, cons = _constraints_for(strip_split_fold("V", "V"))
        # faces: 0=[0,1] 1=[1,1.5] 2=[1.5,2] 3=[2,3]; folded, the flat
        # edge lands on x=0.5, strictly inside both unit faces 0 and 3.
        assert len(res.faces) == 4
        assert all(needs_flat_edge(p) for _, _, p in cons.equalities)
        got = {(la, lb) for la, lb, _ in cons.equalities}
        assert got == {(_lit(0, 1), _lit(0, 2)), (_lit(3, 1), _lit(3, 2))}
        # the two creases fold onto x=1 and x=0, so no SHARED-segment
        # family can fire here: this fixture isolates one family.
        assert not any("along flat edge" in str(p) or "flat edges" in str(p)
                       for _, _, p in cons.equalities)

    def test_flat_pair_faces_do_not_overlap_each_other(self):
        # 1 and 2 are the two halves of one uncreased sheet: they tile,
        # they never stack, so (1,2) is not a pair variable at all.
        _, cons = _constraints_for(strip_split_fold("V", "V"))
        assert (1, 2) not in cons.pairs

    @pytest.mark.parametrize("a1,a2", [("V", "V"), ("V", "M"),
                                       ("M", "V"), ("M", "M")])
    def test_split_strip_is_orderable_for_every_assignment(self, a1, a2):
        fold = strip_split_fold(a1, a2)
        check_order(fold, layer_order(flat_fold(fold)))


class TestRequiredFailInputs:
    """COORDINATION §4.1: every metric ships with an input it MUST fail.

    Each case is a relabel of a COMMITTED golden that the pre-S2′a oracle
    accepts and one specific new family refutes — so the family is shown
    to be the CAUSE, not merely present when something else fires."""

    @pytest.mark.parametrize("golden,flips,family", [
        # taco-taco. The pre-S2'a oracle's fixed order used to reach the
        # tortilla-tortilla family first; the incremental worklist closure
        # in `_propagate` (2026-09-22, spec section 10) reaches its fixpoint
        # in a single round on this relabel, so its taco-taco contradiction
        # (round 2's taco loop) surfaces a whole round earlier than the old
        # loop's tortilla-tortilla one (round 3's equality loop) would have.
        # Same verdict (contradiction), different family reported first --
        # an accepted discovery-order change, not a regression.
        ("hshape.fold", [3, 6, 10], r"taco-taco \(2, 3\)x\(3, 10\)"),
        # tortilla-tortilla, two flat pairs sharing one folded segment
        ("quad.fold", [13], r"tortilla-tortilla flat edges \(8, 9\)x\(9, 12\)"),
        # taco-tortilla, a flat pair sharing a crease's folded segment
        ("quad.fold", [2],
         r"taco-tortilla crease \(5, 7\) along flat edge \(3, 5\)"),
        # ...and the strongest form: cp_audit-CLEAN, so the other three
        # conjuncts of the S2′ gate all pass it and only this one refutes.
        # (The three above are audit-dirty — a cheaper oracle would also
        # reject them, which is why this row exists. Weight 4 is its
        # measured minimum over dog-repaired's 33 M/V creases.)
        ("dog-repaired.fold", [0, 6, 13, 38],
         r"taco-tortilla crease \(2, 3\) along flat edge \(17, 26\)"),
    ])
    def test_accepted_before_s2a_and_refuted_after(self, golden, flips,
                                                   family):
        fold = _flip(load_golden(golden), flips)
        _, cons = _constraints_for(fold)
        _propagate(_pre_s2a(cons))            # pre-S2′a: no contradiction
        with pytest.raises(ValueError, match=family):
            _propagate(cons)
        with pytest.raises(ValueError, match=family):
            layer_order(flat_fold(fold))      # and through the real entry

    def test_unflipped_goldens_are_still_accepted(self):
        # the controls for the inputs above: the refutations are properties
        # of the relabels, not of the goldens carrying them.
        for name in ("hshape.fold", "quad.fold", "dog-repaired.fold"):
            layer_order(flat_fold(load_golden(name)))

    def test_audit_clean_input_survives_the_other_gate_conjuncts(self):
        # pins WHY the dog-repaired row is the strongest of the four: the
        # S2′ gate is symmetry AND cp_audit AND layer_order, and this input
        # is refuted by layer_order ALONE. If a future change made it
        # audit-dirty the row would quietly weaken to match the others.
        from pleatwright.certify import cp_audit
        fold = _flip(load_golden("dog-repaired.fold"), [0, 6, 13, 38])
        assert cp_audit.audit_fold(fold).clean

    def test_tortilla_tortilla_flat_edge_family_is_the_cause_on_hshape(self):
        """§4.1 requires a pin showing the SPANNING tortilla-tortilla family
        (`_spanning`'s "tortilla-tortilla flat edge (" provenance,
        layer_order.py:583) is itself load-bearing. The hshape row above no
        longer supplies that: the closure now surfaces a taco-taco witness
        first on that relabel, and the witness string is traversal-order
        dependent (this very commit changed it once already), so pinning a
        family by its witness regex is fragile. Pin it STRUCTURALLY instead,
        the way `_pre_s2a` isolates a family by provenance rather than by
        which error message happens to surface: with only this family's
        equalities removed, the same relabel is consistent; with the full
        constraint set it still raises."""
        fold = _flip(load_golden("hshape.fold"), [3, 6, 10])
        _, cons = _constraints_for(fold)
        without_family = _Constraints(
            pairs=cons.pairs, direct=cons.direct,
            equalities=tuple(
                e for e in cons.equalities
                if not str(e[2]).startswith("tortilla-tortilla flat edge (")),
            tacos=cons.tacos, covers=cons.covers)
        _propagate(without_family)            # family removed: no contradiction
        with pytest.raises(ValueError):
            _propagate(cons)                  # family present: contradiction


class TestTortillaMonotonicity:
    """The new families may only refute MORE. Measured over every golden:
    no relation the pre-S2′a system forced is lost or flipped."""

    @pytest.mark.parametrize("name", CONSISTENT_FIXTURES)
    def test_no_forced_relation_is_lost_or_flipped(self, name):
        _, cons = _constraints_for(load_golden(name))
        before = _propagate(_pre_s2a(cons))
        after = _propagate(cons)
        for pair, value in before.items():
            assert pair in after, f"{name}: relation {pair} was LOST"
            assert after[pair] == value, f"{name}: relation {pair} FLIPPED"

    def test_new_families_are_equalities_only(self):
        # a `direct` seed or a `tacos` entry could assert a NEW fact and so
        # could in principle unforce nothing but mis-force something; an
        # equality can only tie two existing variables together.
        for name in CONSISTENT_FIXTURES + ["dog-repaired.fold"]:
            _, cons = _constraints_for(load_golden(name))
            assert not any(needs_flat_edge(p) for _, _, p in cons.direct)
            assert not any(needs_flat_edge(p) for _, _, p in cons.tacos)

    def test_star4_has_no_flat_edges_and_so_no_new_constraints(self):
        # the vacuity guard in the other direction: a fixture with no F
        # shared edge must gain nothing, or "flat edge" is matching noise.
        res, cons = _constraints_for(load_golden("star-4.fold"))
        assert all(a in ("M", "V") for _, _, _, a in res.shared_edges)
        assert not any(needs_flat_edge(p) for _, _, p in cons.equalities)


class TestCollinearOverlap:
    def test_shared_segment_is_collinear_overlap(self):
        s1 = ((0.0, 0.0), (2.0, 0.0))
        s2 = ((1.0, 0.0), (3.0, 0.0))
        assert _collinear_overlap(s1, s2)
        assert _segs_interact(s1, s2)

    def test_proper_crossing_is_not_collinear_overlap(self):
        # a transversal crossing puts part of each segment strictly inside
        # the other's faces, so the SPANNING rule already covers it —
        # counting it again here would double-count, not add coverage.
        s1 = ((0.0, 0.0), (2.0, 0.0))
        s2 = ((1.0, -1.0), (1.0, 1.0))
        assert not _collinear_overlap(s1, s2)
        assert _segs_interact(s1, s2)

    def test_endpoint_touching_is_not_overlap(self):
        assert not _collinear_overlap(((0.0, 0.0), (1.0, 0.0)),
                                      ((1.0, 0.0), (2.0, 0.0)))

    def test_parallel_but_offset_is_not_overlap(self):
        assert not _collinear_overlap(((0.0, 0.0), (2.0, 0.0)),
                                      ((0.0, 1.0), (2.0, 1.0)))


class TestInteriorEpsIsCalibratedToPlatformNoise:
    """`INTERIOR_EPS` is a MEASURED constant with a required-fail input on
    BOTH sides, not an epsilon widened until CI went green.

    It was found through a Linux-only CI failure: `_spanning` emits a
    taco-tortilla constraint whenever `_strictly_inside` calls the crease
    midpoint interior to a third face, and at the old shared `GEOM_EPS = 1e-9`
    Linux/OpenBLAS emitted 91 constraints on `template-quadruped`'s root-8
    winner where macOS/Accelerate emitted 64 -- 27 of them fabricated out of
    packed-vertex roundoff, on creases that geometrically run ALONG a face's
    boundary. That inverts the module docstring's load-bearing promise to
    UNDER-refute, and it refused a base the ranking had already chosen
    identically on both platforms.

    The two bounds below are the measurement (probe_layer_margin.py):

      * NOISE CEILING 3.238e-09 -- largest margin among the triples whose
        verdict differed by platform;
      * SIGNAL FLOOR 8.365e-04 -- smallest margin among the 64 crossings both
        platforms agree are real.

    Narrowing the constant back toward the noise breaks the second test;
    widening it into the signal breaks the first. That is what makes this a
    calibration rather than a preference.
    """

    #: Unit CCW square. Its edges have length 1, so `_strictly_inside`'s cross
    #: product equals the point's DISTANCE to each edge -- which is what lets
    #: these cases be read directly in the units the measurement reports.
    SQUARE = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])

    #: Measured on template-quadruped root 8, macOS vs linux/amd64.
    NOISE_CEILING = 3.238e-09

    #: ⚠ NOT THAT BASE'S 8.365e-04. That number is what its OWN smallest real
    #: crossing reads, and using it as a signal floor is what let the constant
    #: first ship at 1e-6 -- which code review then measured deletes real
    #: constraints and flips `oracles_ok` refuse -> accept on 5 of 6
    #: `COMPOSED_NODES` arms. Re-measured across four bases
    #: (`probe_interior_window.py`), the smallest constraint a denser base
    #: carries outside the degenerate band is 3.21e-08, and THAT is the bound
    #: the constant has to sit under.
    SIGNAL_FLOOR = 3.21e-08

    def test_a_genuine_interior_crossing_is_still_interior(self):
        """The signal side, and the bound that keeps this gate from going
        vacuous. A point as far in as the smallest constraint any MEASURED base
        carries outside the degenerate band must still read INTERIOR -- at
        1e-6 it did not, and `root_rank.oracles_ok` flipped refuse -> accept on
        5 of 6 `COMPOSED_NODES` arms that a named contradiction had refused."""
        assert _strictly_inside((self.SIGNAL_FLOOR, 0.5), self.SQUARE)
        # ...and comfortably inside points, a fortiori.
        assert _strictly_inside((0.5, 0.5), self.SQUARE)

    @pytest.mark.parametrize("d", [0.0, 1e-17, 1e-9, 3.238e-09])
    def test_a_boundary_riding_point_is_NOT_interior(self, d):
        """THE REQUIRED-FAIL INPUT, and the regression this constant closes.

        Every one of these offsets is a crease lying ON the face boundary as
        far as the packer's real precision can say. macOS computes them as
        exactly 0.0 or ~1e-17 and Linux as 1e-9..3.2e-9 for the SAME
        configuration; both must read NOT-interior, or the two platforms
        disagree about what the crease pattern is.

        At the old `GEOM_EPS = 1e-9` the 3.238e-09 row FAILS.
        """
        assert not _strictly_inside((d, 0.5), self.SQUARE)

    def test_the_constant_stays_inside_the_measured_safe_window(self):
        """A future edit must move the MEASUREMENT, not just the number.

        ⚠ THE MARGINS DEMANDED HERE ARE 3x, NOT 100x, AND THAT IS THE HONEST
        READING OF THE DATA. An earlier version of this test demanded two
        orders on each side, which was only satisfiable because the upper bound
        came from a single base that loses nothing at any threshold. Measured
        across four bases the real window is ONE ORDER WIDE -- noise 3.238e-09
        below, a real 3.21e-08 constraint above -- so a 100x margin cannot be
        had, and pretending otherwise is what shipped 1e-6.
        """
        assert INTERIOR_EPS >= self.NOISE_CEILING * 3, (
            "INTERIOR_EPS has been narrowed toward the cross-platform noise "
            "floor; layer_order will fabricate taco-tortilla constraints")
        assert INTERIOR_EPS <= self.SIGNAL_FLOOR / 3, (
            "INTERIOR_EPS has been widened into the measured signal; "
            "layer_order will start dropping real constraints and "
            "root_rank.oracles_ok goes vacuous")


def test_layer_order_entry_point_matches_constraints_for_on_a_pleatwright_cp():
    """constraints_for must return the system layer_order() builds; measured on
    the solved CP of artifact tree starfish_1 (globally CERTIFIED)."""
    from pleatwright import solve as SV
    from test_pleatwright import _build
    from pleatwright.certify import flat_fold as FF, layer_order as L
    sf, con, sigma, lay, b = _build("starfish_1")
    sv = SV.solve(b)
    assert sv.global_verdict.startswith("CERTIFIED"), sv.global_verdict
    fold, _, _ = SV.to_fold(sv.cp)
    ff = FF.flat_fold(fold)
    cons, slots = L.constraints_for(ff)
    assert L.propagate(cons) == L.layer_order(ff)._rel
    assert {s.edge for s in slots} <= {k for _, _, k, a in ff.shared_edges
                                       if a in ("M", "V")}
