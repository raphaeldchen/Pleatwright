"""Tests for layer_certify.py.

Spec: docs/superpowers/specs/2026-09-23-layer-certify-design.md

Fixtures are the hand-derived strips already in test_layer_order.py rather
than new ones, and each test asserts NON-VACUITY before asserting a count:
`strip_fold` generates no equalities and no tacos, so a bare
`len(clauses) == len(cons.tacos)` would read 0 == 0 and prove nothing.
"""
import dataclasses
from itertools import combinations, product

import pytest

from pleatwright.certify import layer_certify
from pleatwright.certify import layer_order
from pleatwright.certify.flat_fold import flat_fold
from pleatwright.certify.layer_order import Prov, _lit, constraints_for
from test_certify_layer_order import strip4_fold, strip_fold, strip_split_fold


def cons_for(fold):
    cons, _ = constraints_for(flat_fold(fold))
    return cons


def test_our_taco_predicate_equals_adks_mod_4_form_on_all_16_assignments():
    """ADK state taco-taco as `Lik + Ljk + Lil + Ljl = 0 mod 4`; we check
    `(v0 != v1) == (v2 != v3)` over (_lit(r,p), _lit(r,q), _lit(s,p),
    _lit(s,q)). Both are the parity of the four, but the INDEX MAPPING is
    where a real bug hides, so pin it: i=p, j=q, k=r, l=s, and our four
    literals are the negations of ADK's four Lambdas.
    """
    for bits in product((True, False), repeat=4):
        L_ik, L_jk, L_il, L_jl = bits     # ADK's, True = +1
        adk_ok = (sum(1 for b in bits if b) % 2) == 0
        v0, v1, v2, v3 = (not L_ik), (not L_jk), (not L_il), (not L_jl)
        ours_ok = (v0 != v1) == (v2 != v3)
        assert ours_ok == adk_ok, (bits, ours_ok, adk_ok)


def test_taco_clauses_match_the_propagators_four_literals():
    """One clause per `cons.tacos` entry, over exactly the four literals
    `layer_order._propagate` uses."""
    cons = cons_for(strip4_fold("V", "V", "V"))
    assert len(cons.tacos) == 2, "fixture must carry real tacos"
    tacos = [c for c in layer_certify.clauses(cons) if c.family == "taco"]
    assert len(tacos) == len(cons.tacos)
    for clause, ((p, q), (r, s), _) in zip(tacos, cons.tacos):
        want = (_lit(r, p), _lit(r, q), _lit(s, p), _lit(s, q))
        assert clause.variables == tuple(li[0] for li in want)
        assert clause.flips == tuple(li[1] for li in want)


def test_equality_clauses_are_one_per_constraint_with_their_flips():
    cons = cons_for(strip_split_fold("V", "V"))
    assert len(cons.equalities) == 2, "fixture must carry real equalities"
    eqs = [c for c in layer_certify.clauses(cons) if c.family == "equality"]
    assert len(eqs) == len(cons.equalities)
    for clause, (la, lb, _) in zip(eqs, cons.equalities):
        assert clause.variables == (la[0], lb[0])
        assert clause.flips == (la[1], lb[1])


def test_transitivity_clauses_come_only_from_within_one_cover():
    """Transitivity holds only where all three faces stack over one cell."""
    cons = cons_for(strip4_fold("V", "V", "V"))
    allowed = {tri for cover in cons.covers
               for tri in combinations(sorted(cover), 3)}
    assert allowed, "fixture must have a cover of at least 3 faces"
    tris = [c for c in layer_certify.clauses(cons)
            if c.family == "transitivity"]
    assert len(tris) == len(allowed)
    for c in tris:
        faces = tuple(sorted({f for pr in c.variables for f in pr}))
        assert faces in allowed, faces


def test_transitivity_variables_are_the_three_pairs_of_the_triple():
    cons = cons_for(strip4_fold("V", "V", "V"))
    tris = [c for c in layer_certify.clauses(cons)
            if c.family == "transitivity"]
    assert tris, "no transitivity clauses -- the loop below would prove nothing"
    for c in tris:
        (a, b), (b2, cc), (a2, c2) = c.variables
        assert (a, b, cc) == (a2, b2, c2)
        assert c.flips == (False, False, False)


def test_clauses_emits_no_family_beyond_the_three():
    cons = cons_for(strip4_fold("V", "V", "V"))
    families = {c.family for c in layer_certify.clauses(cons)}
    # Not `==`: the fixture may legitimately generate no equalities, and a
    # bare subset check would pass silently on an EMPTY clause set too,
    # proving nothing about the three families actually named.
    assert families and families <= {"equality", "transitivity", "taco"}


def test_lit_is_antisymmetric_only_in_the_flip_bit():
    """The spec calls antisymmetry "unrepresentable-as-violated" because
    `_lit` gives one canonical variable per unordered pair: `_lit(a, b)`
    and `_lit(b, a)` must name the SAME pair variable and differ only in
    the flip bit, for both index orders."""
    for a, b in ((0, 1), (5, 2)):
        pair_ab, flip_ab = layer_order._lit(a, b)
        pair_ba, flip_ba = layer_order._lit(b, a)
        assert pair_ab == pair_ba
        assert flip_ab != flip_ba


def test_verify_accepts_the_complete_relation_propagation_already_forces():
    """strip4 V,M,V forces all 6 pairs, so this is the hand-sized analogue
    of the five corpus subjects that leave zero free variables."""
    cons = cons_for(strip4_fold("V", "M", "V"))
    rel = layer_order.propagate(cons)
    assert set(rel) == set(cons.pairs), "fixture must be fully forced"
    out = layer_certify.verify(cons, rel)
    assert out.violation is None
    assert out.skipped == 0
    assert out.checked > 0


def test_verify_rejects_a_relation_with_a_directed_3_cycle():
    """rel[(lo,hi)] True means lo above hi, so a>b, b>c, c>a is
    rab=True, rbc=True, rac=False. Transitivity must fire."""
    cons = cons_for(strip4_fold("V", "M", "V"))
    rel = dict(layer_order.propagate(cons))
    tri = next(c for c in layer_certify.clauses(cons)
               if c.family == "transitivity")
    ab, bc, ac = tri.variables
    rel[ab], rel[bc], rel[ac] = True, True, False
    out = layer_certify.verify(cons, rel)
    assert out.violation is not None
    assert out.violation.family == "transitivity"
    assert out.violation.variables == tri.variables


def test_verify_rejects_a_relation_with_the_other_directed_3_cycle():
    """The other cyclic state a sorted triple can take: (F, F, T) --
    `_satisfied`'s docstring names both (T, T, F) and (F, F, T) as the two
    directed-cycle states, but only the first had a test."""
    cons = cons_for(strip4_fold("V", "M", "V"))
    rel = dict(layer_order.propagate(cons))
    tri = next(c for c in layer_certify.clauses(cons)
               if c.family == "transitivity")
    ab, bc, ac = tri.variables
    rel[ab], rel[bc], rel[ac] = False, False, True
    out = layer_certify.verify(cons, rel)
    assert out.violation is not None
    assert out.violation.family == "transitivity"
    assert out.violation.variables == tri.variables


def test_verify_rejects_a_broken_taco():
    """Corrupt only the taco parity, leaving transitivity satisfied, so the
    taco predicate is what fires."""
    cons = cons_for(strip4_fold("V", "M", "V"))
    rel = dict(layer_order.propagate(cons))
    taco = next(c for c in layer_certify.clauses(cons) if c.family == "taco")
    vals = [layer_certify._value(rel, pr, fl)
            for pr, fl in zip(taco.variables, taco.flips)]
    assert (vals[0] != vals[1]) == (vals[2] != vals[3]), "start satisfied"
    pr, fl = taco.variables[0], taco.flips[0]
    rel[pr] = not rel[pr]        # flip one literal -> parity breaks
    out = layer_certify.verify(cons, rel)
    assert out.violation is not None
    assert out.violation.family in ("transitivity", "taco")


def test_verify_counts_skipped_clauses_and_never_hides_a_partial_check():
    """A CERTIFIED verdict requires skipped == 0, so a partial relation
    must read as partial rather than passing quietly."""
    cons = cons_for(strip4_fold("V", "M", "V"))
    rel = dict(layer_order.propagate(cons))
    del rel[next(iter(rel))]
    out = layer_certify.verify(cons, rel)
    assert out.skipped > 0


def test_satisfied_raises_on_an_unknown_family():
    with pytest.raises(ValueError, match="unknown family"):
        layer_certify._satisfied("tortilla_surprise", (True, True))


def _doctored(cons, pairs, equalities, covers=()):
    """`cons` with a synthetic variable set, for unit-testing `collapse`
    and `decide` on shapes no hand-sized fold produces. Matches
    test_layer_order.py's own synthetic-taco practice."""
    return dataclasses.replace(cons, pairs=frozenset(pairs),
                               equalities=tuple(equalities),
                               direct=(), tacos=(), covers=tuple(covers))


def test_collapse_quotients_free_pairs_joined_by_an_equality():
    a, b, c = (0, 1), (1, 2), (0, 2)
    cons = _doctored(cons_for(strip_fold("V", "V")), {a, b, c},
                     [((a, False), (b, False), Prov("a==b", faces=()))])
    classes, odd = layer_certify.collapse(cons, {a, b, c})
    assert odd is None
    assert set(classes) == {a, b, c}
    assert classes[a] == classes[b]
    assert classes[c] != classes[a]
    assert len(set(classes.values())) == 2


def test_collapse_respects_the_flip_parity():
    """An equality between literals with DIFFERENT flips means the two
    pairs take OPPOSITE rel values -- still one class, and the parity is
    what makes a later odd cycle detectable."""
    a, b, c = (0, 1), (1, 2), (0, 2)
    cons = _doctored(cons_for(strip_fold("V", "V")), {a, b, c},
                     [((a, False), (b, True), Prov("a!=b", faces=()))])
    classes, odd = layer_certify.collapse(cons, {a, b, c})
    assert odd is None
    assert classes[a] == classes[b]


def test_collapse_reports_an_odd_parity_cycle():
    """a == b, b == c, a != c is unsatisfiable, and propagation does not
    find it. collapse must, without any search."""
    a, b, c = (0, 1), (1, 2), (0, 2)
    cons = _doctored(cons_for(strip_fold("V", "V")), {a, b, c},
                     [((a, False), (b, False), Prov("a==b", faces=())),
                      ((b, False), (c, False), Prov("b==c", faces=())),
                      ((a, False), (c, True), Prov("a!=c", faces=()))])
    classes, odd = layer_certify.collapse(cons, {a, b, c})
    assert odd is not None
    assert odd.family == "equality"


def test_collapse_ignores_equalities_touching_a_forced_pair():
    """Only equalities whose BOTH variables are free can merge classes; one
    forced side means the value is already known and there is nothing to
    quotient."""
    a, b, c = (0, 1), (1, 2), (0, 2)
    cons = _doctored(cons_for(strip_fold("V", "V")), {a, b, c},
                     [((a, False), (c, False), Prov("a==c", faces=()))])
    classes, odd = layer_certify.collapse(cons, {a, b})   # c is forced
    assert odd is None
    assert classes[a] != classes[b]
    assert set(classes) == {a, b}


def test_decide_certifies_a_physically_foldable_strip_with_free_variables():
    """The all-V 1x4 accordion folds in the real world, and propagation
    leaves 3 of its 6 pairs free. So `decide` must CERTIFY it.

    If this REFUTES, STOP and report it rather than adjusting the test:
    a refutation of a pattern that physically folds means `clauses` or
    `_satisfied` is wrong, which is exactly what this task is for."""
    cons = cons_for(strip4_fold("V", "V", "V"))
    rel = layer_order.propagate(cons)
    assert len(set(cons.pairs) - set(rel)) == 3, "fixture must leave 3 free"
    v = layer_certify.decide(cons)
    assert v.kind == "CERTIFIED"
    assert v.violation is None
    assert v.free == 3          # no equalities here, so classes == pairs
    assert v.nodes >= 1


def test_decide_certifies_a_fully_forced_relation_without_searching():
    """strip4 V,M,V leaves nothing free: one node, no branching."""
    cons = cons_for(strip4_fold("V", "M", "V"))
    v = layer_certify.decide(cons)
    assert v.kind == "CERTIFIED"
    assert v.free == 0
    assert v.nodes == 1


def test_decide_refutes_an_odd_cycle_without_searching():
    a, b, c = (0, 1), (1, 2), (0, 2)
    cons = _doctored(cons_for(strip_fold("V", "V")), {a, b, c},
                     [((a, False), (b, False), Prov("a==b", faces=())),
                      ((b, False), (c, False), Prov("b==c", faces=())),
                      ((a, False), (c, True), Prov("a!=c", faces=()))],
                     covers=(frozenset({0, 1, 2}),))
    v = layer_certify.decide(cons)
    assert v.kind == "REFUTED"
    assert v.nodes == 1
    # A REFUTED verdict must NAME what refuted it, or a caller cannot tell a
    # finding about the folded state from a finding about the oracle.
    assert v.violation is not None
    assert v.violation.family == "equality"


def test_decide_returns_undecided_when_the_budget_is_exhausted():
    """A budget of 1 node cannot get past the root of a search that has to
    branch, and the verdict must say UNDECIDED rather than guess."""
    cons = cons_for(strip4_fold("V", "V", "V"))
    v = layer_certify.decide(cons, budget=1)
    assert v.kind == "UNDECIDED"
    assert v.nodes == 1


def test_decide_refutes_by_searching_not_at_the_root():
    """`collapse` alone cannot refute this fixture -- the equality graph on
    {a, b, c} is a tree (a==b, a!=c), so there is no odd parity cycle and
    `collapse` reports one class, `odd=None`. Root: 1 unforced class,
    so `decide` must branch to resolve it.

    Whichever value the branch picks for the free class, propagation's own
    transitive closure derives the THIRD pair from the other two (a chain
    through the shared cover {0,1,2}) before the a==b equality has a chance
    to derive it directly -- and the two derivations disagree, so
    `layer_order.propagate` itself raises `LayerContradiction` on BOTH
    branches. That is the cycle: the fixture is unsatisfiable either way,
    but the search has to try a value and propagate to discover it, so this
    reaches REFUTED through the branch-and-propagate loop, not through
    `collapse`'s root-level odd-cycle shortcut (that path is already
    covered by test_decide_refutes_an_odd_cycle_without_searching, where
    nodes == 1)."""
    a, b, c = (0, 1), (1, 2), (0, 2)
    cons = _doctored(cons_for(strip_fold("V", "V")), {a, b, c},
                     [((a, False), (b, False), Prov("a==b", faces=())),
                      ((a, False), (c, True), Prov("a!=c", faces=()))],
                     covers=(frozenset({0, 1, 2}),))
    classes, odd = layer_certify.collapse(cons, {a, b, c})
    assert odd is None, "collapse must NOT refute this fixture -- decide must"
    assert len(set(classes.values())) == 1, "one class, so decide must branch"

    v = layer_certify.decide(cons)
    assert v.kind == "REFUTED"
    assert v.nodes > 1, "proves the search branched rather than refuting at the root"
    # Observed (both branches, `budget=CERTIFY_BUDGET`): propagation itself
    # raises on both val=True and val=False, so a violation survives -- this
    # is the case Fix 1 exists for, a propagate-caused REFUTED naming its
    # cause rather than discarding it.
    assert v.violation is not None
    assert v.violation.family == "propagate"
    # Note: the provenance text is observed-and-illustrative, not guaranteed.
    # layer_order._propagate is non-confluent; its witness strings depend on
    # worklist iteration order and could change on unrelated engine updates.


def test_layers_certify_and_propagate_seed_the_same_constraints():
    """The two tiers must judge the SAME constraint set. Asserted through
    behaviour rather than through `inspect.getsource`: build a graph, seed
    it via `_seeded`, and check the `direct` tuple both tiers consume is
    identical to the one `propagate` builds for the same labels.

    This only proves DETERMINISM (two calls with the same inputs agree) --
    it never checks the seeds against `labels` itself, so a `_seeded` that
    ignored `labels` and returned the same wrong constant every time would
    also pass. Chose the direct-formula check over monkeypatching
    `layer_order.propagate` to capture `cons` from both `layers.propagate`
    and `layers.certify`: that would additionally prove the two ENTRY
    POINTS both reach `_seeded`, but it means reaching into
    `layer_order.propagate`'s internals from both call paths, which is more
    machinery, and more fragile to those paths' own signatures, than
    needed to answer "are the seeds tied to `labels`" -- which is what was
    actually missing. `_seed` is `layers.py`'s own single copy of the
    seed formula (its docstring: "the ONLY copy... both `propagate` and the
    drift guard... call this function"), so checking each seeded entry
    against a direct `_seed` call ties the produced booleans to `labels`
    without re-deriving the formula a second way."""
    from pleatwright.certify import layers
    cons = cons_for(strip4_fold("V", "M", "V"))
    graph = layers.LayerGraph(cons=cons, slots=cons.slots)
    labels = {s.edge: "V" for s in cons.slots}
    seeded = layers._seeded(graph, labels)
    assert len(seeded.direct) == len(cons.slots)
    assert seeded.pairs == cons.pairs
    # same labels, same seeds, every time -- no hidden state in either tier
    assert layers._seeded(graph, labels).direct == seeded.direct
    # NEW: the seeds are actually tied to `labels`, not just self-consistent.
    for slot, (lit, val, prov) in zip(graph.slots, seeded.direct):
        assert lit == slot.lit
        assert val == layers._seed(slot, labels[slot.edge])
