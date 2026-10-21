"""`sat_order`: the ADK clause set as CNF, checked against `layer_certify`.

Spec: `docs/superpowers/specs/2026-10-02-sat-layer-stage-design.md` §3.3, §8.

No geometry and no compile in this file -- every fixture is a hand-built
`layer_order._Constraints`, so the encoder is tested against the project's own
clause semantics rather than against a folded state.

THE LOAD-BEARING TEST is `test_cnf_models_equal_verify_accepted_exactly`. It
enumerates every assignment of a small instance and requires the CNF's
satisfying set to EQUAL the set `layer_certify.verify` accepts -- both
directions. Every other test here localises a failure the equivalence check
would also catch, EXCEPT the label-link test, which the equivalence check
cannot catch at all: the label variables are free there, so they adapt to
whatever the order variables do and never restrict the order projection.
"""
import dataclasses
import itertools
import math

from pleatwright.certify import layer_certify
import pytest
from pleatwright.certify.layer_order import _Constraints, DirectSlot, Prov, _lit

from pleatwright.certify import layers, sat_order

PROV = Prov(text="synthetic", creases=((0, 1),), faces=(0, 1))


def _cons(*, covers, equalities=(), tacos=(), slots=(), direct=()):
    """A `_Constraints` whose `pairs` is exactly the pairs its covers induce."""
    pairs = frozenset(pr for c in covers
                      for pr in itertools.combinations(sorted(c), 2))
    return _Constraints(pairs=pairs, direct=direct, equalities=equalities,
                        tacos=tacos, covers=tuple(covers), slots=tuple(slots))


def ALL_FAMILIES():
    """4 faces in one cover, one equality, one taco, one slot.

    Measured 2026-10-02: `layer_certify.clauses` yields equality 1,
    transitivity 4, taco 1, and `verify` accepts exactly 8 of the 64
    relations over its 6 pairs.
    """
    return _cons(
        covers=[frozenset({0, 1, 2, 3})],
        equalities=((_lit(0, 1), _lit(2, 3), PROV),),
        tacos=(((0, 1), (2, 3), PROV),),
        slots=(DirectSlot(edge=(10, 11), lit=_lit(0, 1), sign=1,
                          faces=(0, 1)),),
    )


def _encode(cons):
    cl = []
    st = sat_order.encode(cons, cons.slots, cl.append)
    # `EncodeStats.clauses` is the figure the compile stage reports and
    # measures against MAX_CLAUSES. A missing clause shows up as extra models
    # in the equivalence test; a DOUBLE-COUNT would not, so pin it here.
    assert st.clauses == len(cl), (st.clauses, len(cl))
    return cl, st


def _models_over(cl, order_var):
    """Every assignment of the ORDER variables the CNF admits.

    Enumerated rather than taken from the solver, so this is the CNF's own
    satisfying set projected onto the order variables -- label variables are
    existentially quantified by being left free.
    """
    from pysat.solvers import Solver
    out = set()
    keys = sorted(order_var)
    with Solver(name=sat_order.SOLVER, bootstrap_with=cl) as s:
        for bits in itertools.product([False, True], repeat=len(keys)):
            ass = [order_var[k] if b else -order_var[k]
                   for k, b in zip(keys, bits)]
            if s.solve(assumptions=ass):
                out.add(bits)
    return out


def _verify_accepted(cons):
    """Every relation `layer_certify.verify` accepts."""
    keys = sorted(cons.pairs)
    out = set()
    for bits in itertools.product([False, True], repeat=len(keys)):
        rel = dict(zip(keys, bits))
        if layer_certify.verify(cons, rel).violation is None:
            out.add(bits)
    return out


def test_cnf_models_equal_verify_accepted_exactly():
    """THE load-bearing test: set EQUALITY, not containment.

    Containment in one direction would pass for an over-constrained encoder
    (admits too little) and in the other for an under-constrained one. Only
    equality rules out both.
    """
    cons = ALL_FAMILIES()
    cl, st = _encode(cons)
    assert st.clauses == 20, st.clauses
    assert st.families == {"equality": 1, "transitivity": 4, "taco": 1}
    accepted = _verify_accepted(cons)
    assert len(accepted) == 8, (
        f"the fixture's ground truth moved: verify accepts {len(accepted)} of "
        f"64, measured 8 on 2026-10-02. Fix the fixture, not the assertion.")
    assert _models_over(cl, st.order_var) == accepted


def test_transitivity_forbids_exactly_the_two_cyclic_states():
    """A bare 3-cover: 6 of 8 accepted, the two cyclic states excluded."""
    cons = _cons(covers=[frozenset({0, 1, 2})])
    cl, st = _encode(cons)
    assert st.families == {"equality": 0, "transitivity": 1, "taco": 0}
    accepted = _verify_accepted(cons)
    assert len(accepted) == 6, len(accepted)
    assert _models_over(cl, st.order_var) == accepted
    # The two forbidden states, in THIS test's coordinates. `_satisfied` reads
    # a transitivity clause's variables as ((a,b), (b,c), (a,c)) -- for faces
    # 0,1,2 that is (0,1), (1,2), (0,2) -- so its cyclic states (T,T,F) and
    # (F,F,T) become (T,F,T) and (F,T,F) once re-indexed into the SORTED pair
    # order these tuples use. Spelling that out because the two orders differ
    # and a tuple written in the wrong one silently tests nothing.
    assert (True, False, True) not in accepted
    assert (False, True, False) not in accepted


def test_equality_forces_its_two_literals_to_agree():
    cons = _cons(covers=[frozenset({0, 1, 2, 3})],
                 equalities=((_lit(0, 1), _lit(2, 3), PROV),))
    cl, st = _encode(cons)
    assert _models_over(cl, st.order_var) == _verify_accepted(cons)


def test_taco_forces_even_parity_over_its_four_literals():
    cons = _cons(covers=[frozenset({0, 1, 2, 3})],
                 tacos=(((0, 1), (2, 3), PROV),))
    cl, st = _encode(cons)
    assert _models_over(cl, st.order_var) == _verify_accepted(cons)


@pytest.mark.parametrize("lit,sign,label,expected", [
    (_lit(0, 1), 1, "M", False),
    (_lit(0, 1), 1, "V", True),
    (_lit(0, 1), -1, "M", True),
    (_lit(0, 1), -1, "V", False),
    (_lit(1, 0), 1, "M", True),
    (_lit(1, 0), 1, "V", False),
    (_lit(1, 0), -1, "M", False),
    (_lit(1, 0), -1, "V", True),
])
def test_label_link_forces_the_order_variable(lit, sign, label, expected):
    """The forcing table `layers._seed` implies, derived 2026-10-02.

    `_seed` is `(label == "V") == (sign == 1)` and a literal's value is
    `rel[pair] != flip`, so `rel[pair]` must be `_seed != flip`.

    THE EQUIVALENCE CHECK CANNOT CATCH THESE. There the label variables are
    free and simply follow the order variables, so dropping a biconditional
    direction or ignoring `sign` leaves the order projection untouched. This
    test pins the labels as assumptions instead, which is the only way the
    link is observable.
    """
    from pysat.solvers import Solver
    cons = _cons(covers=[frozenset({0, 1})],
                 slots=(DirectSlot(edge=(10, 11), lit=lit, sign=sign,
                                   faces=(0, 1)),))
    cl, st = _encode(cons)
    lv = st.label_var[(10, 11)]
    ov = st.order_var[lit[0]]
    with Solver(name=sat_order.SOLVER, bootstrap_with=cl) as s:
        assume = [lv if label == "V" else -lv]
        assert s.solve(assumptions=assume), "the labelling itself is unsat"
        assert not s.solve(assumptions=assume + [-ov if expected else ov]), (
            f"sign={sign} label={label} must force rel[{lit[0]}]={expected}")


def test_raw_triple_bound_is_the_sum_over_covers():
    cons = _cons(covers=[frozenset(range(4)), frozenset(range(5))])
    assert sat_order.raw_triple_bound(cons) == math.comb(4, 3) + math.comb(5, 3)
    assert sat_order.raw_triple_bound(ALL_FAMILIES()) == 4


def test_encode_refuses_past_max_clauses_mid_emission():
    """The streaming counter, which fires where the loose bound cannot."""
    cons = _cons(covers=[frozenset(range(8))])
    with pytest.raises(sat_order.SatOrderError, match="max_clauses"):
        sat_order.encode(cons, cons.slots, lambda c: None, max_clauses=5)


def test_unknown_clause_family_refuses_rather_than_guessing(monkeypatch):
    """`layer_certify._satisfied` raises on an unknown family; so must this.

    Encoding an unrecognised family as anything would silently admit a
    constraint nobody checks.
    """
    class _Fake:
        family = "wormhole"
        variables = ((0, 1),)
        flips = (False,)
        prov = "synthetic"

    cons = _cons(covers=[frozenset({0, 1})])
    monkeypatch.setattr(layer_certify, "_iter_clauses",
                        lambda c: iter([_Fake()]))
    with pytest.raises(sat_order.SatOrderError, match="wormhole"):
        sat_order.encode(cons, cons.slots, lambda c: None)


def test_cons_slots_mismatch_raises_sat_order_error_not_key_error():
    """`slots` is a separate parameter from `cons`, so they can disagree.

    A slot whose pair is absent from `cons.pairs` used to hit a bare
    `KeyError` in `order_var[pair]` -- one of the three exceptions
    `compile_tree` collapses into an indistinguishable `AssignFail("error")`,
    which is exactly what `SatOrderError` exists to avoid.
    """
    cons = _cons(covers=[frozenset({5, 6})])            # pairs == {(5, 6)}
    slots = ALL_FAMILIES().slots                        # refers to pair (0, 1)
    assert (0, 1) not in cons.pairs
    with pytest.raises(sat_order.SatOrderError, match=r"\(0, 1\)") as ei:
        sat_order.encode(cons, slots, lambda c: None)
    assert not isinstance(ei.value, KeyError)
    assert "disagree" in str(ei.value)


def test_cons_direct_is_ignored_by_encode():
    """`direct` is the order relation forced by ONE fixed labelling.

    This module's query leaves the labelling free (the `slots` biconditionals
    replace `direct`), so honouring `direct` would silently re-pin it.
    Production `_Constraints` always arrive with `direct` non-empty, so the
    emitted clause set must be identical with and without it.
    """
    base = ALL_FAMILIES()
    assert base.direct == ()
    with_direct = dataclasses.replace(
        base, direct=((_lit(0, 1), True, PROV), (_lit(2, 3), False, PROV)))
    assert with_direct.direct, "the fixture must actually carry direct"
    cl0, st0 = _encode(base)
    cl1, st1 = _encode(with_direct)
    assert cl1 == cl0
    assert st1.clauses == st0.clauses == 20


def test_solve_returns_a_relation_verify_accepts():
    """SAT, and the model is a genuine layer order by the project's verifier.

    The POSITIVE control. An over-constrained encoder is UNSAT on everything
    and would pass every negative check below vacuously, so this is the one
    that cannot be substituted for.
    """
    cons = ALL_FAMILIES()
    res = sat_order.solve(cons, cons.slots)
    assert res.sat is True
    assert res.verdict.kind == "CERTIFIED"
    assert res.verdict.violation is None
    assert set(res.relation) == set(cons.pairs)
    assert set(res.labels) == {(10, 11)}
    assert res.labels[(10, 11)] in ("M", "V")
    assert layer_certify.verify(cons, res.relation).violation is None


def test_a_forced_3_cycle_is_unsatisfiable_so_transitivity_is_encoded():
    """Transitivity is really in the CNF -- and is only escapable via labels.

    With three independent label variables the cycle is avoidable, so `solve`
    returns SAT here; the REFUTED branch is covered by
    `test_solve_reports_a_genuinely_unsat_instance_as_refuted` below. What this
    test proves is the other half: FORCE the three pair variables into the
    cyclic state and the system becomes unsatisfiable, which fails if
    transitivity is not being emitted.
    """
    slots = tuple(DirectSlot(edge=(100 + i, 101 + i), lit=l, sign=1,
                             faces=(0, 1))
                  for i, l in enumerate((_lit(0, 1), _lit(1, 2), _lit(2, 0))))
    cons = _cons(covers=[frozenset({0, 1, 2})], slots=slots)

    # Labels free: the cycle is avoidable, so the instance is satisfiable.
    res = sat_order.solve(cons, cons.slots)
    assert res.sat is True

    # Labels irrelevant: pin the order variables cyclically and it is not.
    from pysat.solvers import Solver
    cl = []
    st = sat_order.encode(cons, cons.slots, cl.append)
    forced = []
    for l in (_lit(0, 1), _lit(1, 2), _lit(2, 0)):
        v = st.order_var[l[0]]
        forced.append(-v if l[1] else v)
    with Solver(name=sat_order.SOLVER, bootstrap_with=cl) as s:
        assert not s.solve(assumptions=forced), (
            "the cyclic state must be unsatisfiable; if it is not, "
            "transitivity is not being encoded")


def test_solve_refuses_an_oversize_instance_without_allocating():
    """Stage 1 of the guard: the loose bound, before `_iter_clauses` runs."""
    cons = _cons(covers=[frozenset(range(40))])
    res = sat_order.solve(cons, cons.slots, max_raw_triples=10)
    assert res.sat is False
    assert res.verdict.kind == "OVERSIZE"
    assert res.verdict.clauses == 0, "nothing may be emitted after OVERSIZE"
    assert res.labels is None and res.relation is None


def test_solve_refuses_when_the_streaming_counter_crosses():
    """Stage 2: slips the loose bound, caught during emission.

    `max_raw_triples` is set high enough to pass stage 1 and `max_clauses`
    low enough that stage 2 must fire, so neither test can pass by the
    other's mechanism.
    """
    cons = _cons(covers=[frozenset(range(8))])
    assert sat_order.raw_triple_bound(cons) == math.comb(8, 3)
    res = sat_order.solve(cons, cons.slots,
                          max_raw_triples=10 ** 9, max_clauses=4)
    assert res.sat is False
    assert res.verdict.kind == "OVERSIZE"
    assert res.labels is None and res.relation is None


def _two_slots_one_edge_in_a_big_cover():
    """`len(slots) == 2` but only ONE distinct edge, inside an 8-face cover
    big enough to trip a small clause budget."""
    lit = _lit(0, 1)
    slots = (DirectSlot(edge=(10, 11), lit=lit, sign=1, faces=(0, 1)),
             DirectSlot(edge=(10, 11), lit=lit, sign=-1, faces=(0, 1)))
    cons = _cons(covers=[frozenset(range(8))], slots=slots)
    assert len(cons.slots) == 2 and len({s.edge for s in cons.slots}) == 1
    return cons


@pytest.mark.parametrize("budget", [4, 7])
def test_stage_two_oversize_clauses_is_the_measured_crossing_count(budget):
    """The emitter increments THEN compares, so the count at refusal is
    `budget + 1`. Two budgets, so the value is seen to follow the run rather
    than being one constant the code writes."""
    cons = _two_slots_one_edge_in_a_big_cover()
    res = sat_order.solve(cons, cons.slots,
                          max_raw_triples=10 ** 9, max_clauses=budget)
    assert res.verdict.kind == "OVERSIZE"
    assert res.verdict.clauses == budget + 1


def test_stage_two_oversize_build_secs_is_measured_not_defaulted(monkeypatch):
    """Clause generation ran before the budget tripped, so `build_secs` is a
    real elapsed time. A fake clock advancing 1.0 per read makes the elapsed
    value exact (`encode` does not read the clock; `solve` reads it at `t0`
    and once at the refusal)."""
    class _Clock:
        t = 0.0

        @classmethod
        def perf_counter(cls):
            cls.t += 1.0
            return cls.t

    monkeypatch.setattr(sat_order, "time", _Clock)
    cons = _two_slots_one_edge_in_a_big_cover()
    res = sat_order.solve(cons, cons.slots,
                          max_raw_triples=10 ** 9, max_clauses=4)
    assert res.verdict.kind == "OVERSIZE"
    assert res.verdict.build_secs == 1.0
    assert res.verdict.solve_secs == 0.0


def test_oversize_label_vars_counts_distinct_edges_on_both_paths():
    """`label_vars` means distinct crease EDGES on every branch (the decided
    paths use `len(st.label_var)`). Two slots share one edge here, so
    `len(slots) == 2` and the two readings differ."""
    cons = _two_slots_one_edge_in_a_big_cover()
    stage1 = sat_order.solve(cons, cons.slots, max_raw_triples=10)
    stage2 = sat_order.solve(cons, cons.slots,
                             max_raw_triples=10 ** 9, max_clauses=4)
    assert stage1.verdict.kind == stage2.verdict.kind == "OVERSIZE"
    assert stage1.verdict.label_vars == 1
    assert stage2.verdict.label_vars == 1
    # The quantity the decided paths report, taken from the encoder itself.
    decided = sat_order.encode(cons, cons.slots, lambda c: None)
    assert stage1.verdict.label_vars == len(decided.label_var)
    assert stage2.verdict.label_vars == len(decided.label_var)


def test_solve_raises_when_verify_rejects_its_own_model(monkeypatch):
    """An under-constrained encoder must CRASH, not refuse.

    Every `LayerFail` kind reads as a fact about the tree. `verify` rejecting
    this module's model means the CNF admitted something the project's
    verifier calls invalid -- an encoder defect. Typing that as a per-tree
    refusal would publish a bug as a geometric finding.
    """
    class _Bad:
        violation = "synthetic violation"
        checked = 1
        skipped = 0

    monkeypatch.setattr(layer_certify, "verify", lambda c, r: _Bad())
    cons = ALL_FAMILIES()
    with pytest.raises(sat_order.SatOrderError, match="verify"):
        sat_order.solve(cons, cons.slots)


def test_solve_label_matches_the_relation_it_returns():
    """The M/V decode is the one thing `verify` cannot check.

    `verify` reads only the relation, so inverting the "V"/"M" decode of the
    model leaves it green while `compile.py` would rewrite every crease to the
    opposite assignment. Pin the decode to `layers._seed`:
    `(label == "V") == (sign == 1)` is the value of the slot's literal.
    """
    cons = ALL_FAMILIES()
    res = sat_order.solve(cons, cons.slots)
    assert res.sat is True
    for s in cons.slots:
        pair, flip = s.lit
        lit_value = res.relation[pair] != flip
        # `layers._seed` is the ONLY copy of this formula (see its docstring:
        # an inlined copy cannot detect drift in the one `compile.py` uses).
        assert lit_value == layers._seed(s, res.labels[s.edge])


def test_solve_reports_a_genuinely_unsat_instance_as_refuted():
    """The REFUTED branch, reached through `solve` itself.

    Two slots on ONE edge with opposite signs over the same literal demand
    `rel == Lv` and `rel == not Lv` together: unsatisfiable however the order
    variables fall. The brief's UNSAT test above only proves transitivity by
    calling the solver directly and never exercises `solve`'s REFUTED return.
    """
    lit = _lit(0, 1)
    slots = (DirectSlot(edge=(10, 11), lit=lit, sign=1, faces=(0, 1)),
             DirectSlot(edge=(10, 11), lit=lit, sign=-1, faces=(0, 1)))
    cons = _cons(covers=[frozenset({0, 1})], slots=slots)
    res = sat_order.solve(cons, cons.slots)
    assert res.sat is False
    assert res.verdict.kind == "REFUTED"
    assert res.verdict.violation is None
    assert res.labels is None and res.relation is None
    # Measured from the encoder, not defaulted: 4 slot clauses, no transitivity
    # (a 2-cover has no triple), and the counts must reflect that.
    assert res.verdict.clauses == 4
    assert res.verdict.order_vars == 1 and res.verdict.label_vars == 1


def test_solve_oversize_stage_one_never_enters_clause_generation(monkeypatch):
    """`verdict.clauses == 0` is written unconditionally on the OVERSIZE path,
    so asserting it proves nothing about allocation. Make allocation fatal."""
    def _boom(c):
        raise AssertionError("clause generation ran after the loose bound")

    monkeypatch.setattr(layer_certify, "_iter_clauses", _boom)
    cons = _cons(covers=[frozenset(range(40))])
    res = sat_order.solve(cons, cons.slots, max_raw_triples=10)
    assert res.verdict.kind == "OVERSIZE"


def test_solve_does_not_launder_other_encoder_errors_into_oversize(monkeypatch):
    """Only the clause-budget error is a size refusal. An unknown family is an
    encoder defect and must still raise through `solve`."""
    class _Fake:
        family = "wormhole"
        variables = ((0, 1),)
        flips = (False,)
        prov = "synthetic"

    cons = _cons(covers=[frozenset({0, 1})])
    monkeypatch.setattr(layer_certify, "_iter_clauses",
                        lambda c: iter([_Fake()]))
    with pytest.raises(sat_order.SatOrderError, match="wormhole"):
        sat_order.solve(cons, cons.slots)


def test_solve_refuses_to_certify_a_partial_verify(monkeypatch):
    """`CERTIFIED` requires `skipped == 0` (`layer_certify.verify`'s own
    docstring). A violation-free result that skipped clauses is a partial
    check and must raise, never be written as CERTIFIED."""
    class _Partial:
        violation = None
        checked = 3
        skipped = 2

    monkeypatch.setattr(layer_certify, "verify", lambda c, r: _Partial())
    cons = ALL_FAMILIES()
    with pytest.raises(sat_order.SatOrderError, match="SKIPPED 2"):
        sat_order.solve(cons, cons.slots)


def test_clause_budget_is_a_typed_sat_order_error():
    """The budget trip is its own type (a `SatOrderError`, so it still escapes
    `compile_tree`'s handler) and carries the crossing count."""
    cons = _cons(covers=[frozenset(range(8))])
    with pytest.raises(sat_order.ClauseBudgetExceeded) as ei:
        sat_order.encode(cons, cons.slots, lambda c: None, max_clauses=4)
    assert isinstance(ei.value, sat_order.SatOrderError)
    assert not isinstance(ei.value, (ValueError, RuntimeError, KeyError))
    assert ei.value.emitted == 5


def test_solve_dispatches_the_budget_refusal_on_type_not_message(monkeypatch):
    """A reworded message must still be an OVERSIZE verdict. Substring
    dispatch would let it escape as an uncaught exception."""
    def _encode(cons, slots, sink, *, max_clauses):
        raise sat_order.ClauseBudgetExceeded("worded differently", emitted=42)

    monkeypatch.setattr(sat_order, "encode", _encode)
    cons = ALL_FAMILIES()
    res = sat_order.solve(cons, cons.slots)
    assert res.verdict.kind == "OVERSIZE"
    assert res.verdict.clauses == 42
