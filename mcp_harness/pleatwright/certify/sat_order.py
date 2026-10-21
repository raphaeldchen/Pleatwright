"""The complete layer-ordering query as SAT: does ANY labelling order?

Spec: `docs/superpowers/specs/2026-10-02-sat-layer-stage-design.md`.

`layer_certify` already decides ONE labelling completely (Akitaya, Demaine &
Ku, OSME 2024: verifying a facewise order is in P, finding one is NP). This
module asks the JOINT question -- is there a labelling of this crease set that
admits a valid order -- which `layer_certify` cannot, because its `cons.direct`
pins the labelling before it starts.

WHAT IS NOT RE-DERIVED. The clause set is `layer_certify._iter_clauses`
TRANSLATED. This module reads no geometry and reimplements no predicate, so its
CNF cannot disagree with the shipped verifier about what the constraints are.
`layer_certify._satisfied` is the authority for all three families and the
translations below quote it.

TWO VARIABLE FAMILIES. One Boolean per canonical face pair, exactly
`layer_order._lit`'s convention -- a literal is `(pair, flip)` whose value is
`rel[pair] != flip`. And one per crease edge, linked to the order variables by
the `DirectSlot` biconditionals. The second family is what makes the query
joint, and it is sound because `layer_order.constraints_for` documents that
"everything except `_Constraints.direct` depends on the folded geometry alone,
which `flat_fold` derives from the crease SET": M and V both reflect across a
crease, so they give identical folded positions and differ only in which side
lands above. Measured on dense `lizard`: max folded-position difference
EXACTLY 0.0 (evidence `2026-10-02-witness-identity-113/README.md` section 15.1).

THIS MODULE NEVER TOUCHES A FOLD. `solve` returns a labelling and a relation;
`compile.py` owns the rewrite. That keeps the encoder testable against a
hand-built `_Constraints` with no geometry at all.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from math import comb

from . import layer_certify
from pysat.formula import IDPool
from pysat.solvers import Solver

#: Refuse before `layer_certify._iter_clauses` allocates. Dense `lizard`'s
#: bound is 31,314,680 against the 4,511,932 triples it dedupes to, so this is
#: ~3.2x that instance. NOT tuned: it exists to admit the one measured
#: instance with headroom and refuse what would exhaust memory.
MAX_RAW_TRIPLES = 100_000_000

#: The streaming ceiling. Dense `lizard` emits 9,678,554, so this is ~2.1x.
MAX_CLAUSES = 20_000_000

SOLVER = "cadical153"


class SatOrderError(Exception):
    """This module could not honour its own contract.

    Deliberately subclasses `Exception` and NOT
    `ValueError`/`RuntimeError`/`KeyError`: those three are what the
    `except (ValueError, RuntimeError, KeyError)` handler around the
    `assign(...)` call in the archived Lang compiler's `compile_tree` caught,
    folding them into an indistinguishable `AssignFail("error")`. Every condition raised here is a
    defect in this encoder -- an unknown clause family, a clause budget
    crossed, or a model the project's own verifier rejects -- and none is a
    fact about the tree being compiled. Matching `cores.CoreExtractionError`'s
    reasoning for the same choice.
    """


class ClauseBudgetExceeded(SatOrderError):
    """`encode`'s streaming clause counter crossed `max_clauses`.

    A distinct TYPE rather than a message substring, because `solve` must tell
    this size refusal apart from every other `SatOrderError` (an encoder
    defect). `SatOrderError` escapes a broad `except (ValueError, ...)`
    handler on purpose, so a reworded message that stopped matching a
    substring test would turn every oversize-by-streaming instance from an
    OVERSIZE verdict into an uncaught exception. `pleatwright.solve` catches
    this type by name.

    `emitted` is the count AT the crossing (`max_clauses + 1`: the counter is
    incremented before it is compared), carried here so `solve` reports what
    the run measured instead of re-deriving it or echoing the budget.
    """

    def __init__(self, message: str, emitted: int):
        super().__init__(message)
        self.emitted = emitted


# `eq=False`, not `frozen=True`: the three dict fields make a generated
# `__hash__` raise TypeError and make the freeze shallow (`order_var` stays
# mutable) anyway. Nothing hashes or mutates an `EncodeStats`; identity
# equality is the honest contract for a bag of solver facts.
@dataclass(eq=False)
class EncodeStats:
    order_var: dict      # (lo, hi) -> DIMACS variable
    label_var: dict      # crease edge -> DIMACS variable
    clauses: int
    families: dict       # family -> clauses of that family SEEN (not emitted)


@dataclass(frozen=True)
class SatVerdict:
    """CERTIFIED / REFUTED / OVERSIZE, with the solver's own facts.

    Deliberately NOT a `layer_certify.Verdict`. That type carries `nodes` and
    `free` -- search-node counts from `decide`'s branch-and-propagate -- and
    this stage runs no search, so both would have to be filled with a
    defaulted zero. A defaulted number read as a measurement is this project's
    named recurring failure, so the type differs instead. `kind` keeps the same
    vocabulary, so a caller reading `.kind` still works.

    `violation` is ALWAYS `None`, by construction: the only condition that
    could populate it (`layer_certify.verify` rejecting the model) raises
    `SatOrderError` instead of returning a verdict. A `None` there is not the
    report "a violation was looked for and none found"; the field is kept
    only because the spec types it.
    """
    kind: str
    violation: object
    order_vars: int
    label_vars: int
    clauses: int
    build_secs: float
    solve_secs: float


@dataclass(frozen=True)
class SatResult:
    sat: bool
    labels: dict | None      # {(v_lo, v_hi): "M" | "V"}
    relation: dict | None    # {(lo, hi): bool}, COMPLETE
    verdict: SatVerdict


def raw_triple_bound(cons) -> int:
    """An upper bound on the transitivity triples, with no allocation.

    `sum(C(|cover|, 3))` over the arrangement cells, which over-counts because
    overlapping covers share triples -- 31,314,680 against dense `lizard`'s
    4,511,932, a factor of 6.94.

    Loose on purpose. The exact count needs the dedup set that lives INSIDE
    `layer_certify._iter_clauses`, and by the time that exists the memory is
    already spent, so an exact pre-check is impossible without editing a module
    this spec leaves alone. This only has to separate "fine" from "will exhaust
    memory", and the streaming counter in `encode` is the exact backstop.
    """
    return sum(comb(len(c), 3) for c in cons.covers)


def encode(cons, slots, sink, *, max_clauses: int = MAX_CLAUSES) -> EncodeStats:
    """Emit this constraint system's CNF into `sink`, one clause at a time.

    `sink` is required rather than optional so there is no dual return mode:
    tests pass `list.append`, `compile.py` passes `Solver.add_clause`. Nothing
    materialises 9.7 million Python lists.

    `cons.direct` is deliberately IGNORED: it is the set of order relations
    forced by one particular M/V labelling, and here the labelling is a
    variable -- the `slots` biconditionals over `label_var` replace it, so
    honouring `direct` would silently re-pin the labelling being searched.

    Raises `ClauseBudgetExceeded` (a `SatOrderError`) the moment the emitted
    count crosses `max_clauses`, so an instance that slipped
    `raw_triple_bound` still never materialises. Raises plain
    `SatOrderError` if `slots` names a face pair absent from `cons.pairs`.
    """
    pool = IDPool()
    order_var = {p: pool.id(("rel", p)) for p in sorted(cons.pairs)}
    label_var = {s.edge: pool.id(("lab", s.edge)) for s in slots}

    def lit(pair, flip):
        v = order_var.get(pair)
        if v is None:
            # `slots` is a separate parameter from `cons`, so they can come
            # from different `_Constraints`. A bare KeyError here is one of
            # the three exceptions a broad handler (the archived
            # `compile_tree`'s) collapses into a generic failure -- what
            # `SatOrderError` prevents.
            raise SatOrderError(
                f"face pair {pair!r} is referenced by a clause or slot but "
                f"is not in `cons.pairs`: `cons` and `slots` disagree, so "
                f"they were not built from the same `_Constraints`.")
        return -v if flip else v

    n = 0
    fam = {"equality": 0, "transitivity": 0, "taco": 0}

    def emit(clause):
        nonlocal n
        n += 1
        if n > max_clauses:
            raise ClauseBudgetExceeded(
                f"this instance emits more than max_clauses={max_clauses:,} "
                f"CNF clauses. `raw_triple_bound` read "
                f"{raw_triple_bound(cons):,} and did not refuse, so the loose "
                f"bound was not loose enough for this shape; the streaming "
                f"counter is the exact backstop. Raise max_clauses only "
                f"against a measured peak-RSS figure.", emitted=n)
        sink(clause)

    for c in layer_certify._iter_clauses(cons):
        ls = [lit(p, f) for p, f in zip(c.variables, c.flips)]
        if c.family == "equality":
            # `_satisfied`: vals[0] == vals[1]  ->  L0 <-> L1
            emit([-ls[0], ls[1]])
            emit([ls[0], -ls[1]])
        elif c.family == "transitivity":
            # `_satisfied`: not (rab == rbc and rac != rab). The two cyclic
            # states (T,T,F) and (F,F,T) are the only forbidden assignments.
            a, b, d = ls
            emit([-a, -b, d])
            emit([a, b, -d])
        elif c.family == "taco":
            # `_satisfied`: (L0 != L1) == (L2 != L3), i.e. the 4-way XOR is
            # EVEN. Forbid every odd-parity assignment: 8 clauses. Chosen over
            # a Tseitin auxiliary variable per XOR -- 8 clauses x 74,602
            # tacos is cheaper for a CDCL solver at this scale than 74,602
            # extra variables (spec section 0).
            for m in range(16):
                bits = [(m >> i) & 1 for i in range(4)]
                if sum(bits) % 2 == 1:
                    emit([(-ls[i] if bits[i] else ls[i]) for i in range(4)])
        else:
            raise SatOrderError(
                f"unknown clause family {c.family!r}. "
                f"`layer_certify._satisfied` raises on it too; encoding it as "
                f"anything here would silently admit a family nobody checks.")
        fam[c.family] += 1

    for s in slots:
        # `layers._seed`: val = (label == "V") == (sign == 1). With Lv meaning
        # "this crease is V", the DirectSlot's constraint is
        #   (rel[pair] != flip) == (sign == 1 ? Lv : not Lv)
        pair, flip = s.lit
        o = lit(pair, flip)
        lv = label_var[s.edge]
        rhs = lv if s.sign == 1 else -lv
        emit([-o, rhs])
        emit([o, -rhs])

    return EncodeStats(order_var=order_var, label_var=label_var,
                       clauses=n, families=fam)


def solve(cons, slots, *, max_raw_triples: int = MAX_RAW_TRIPLES,
          max_clauses: int = MAX_CLAUSES, solver: str = SOLVER) -> SatResult:
    """Is there a labelling of this crease set admitting a valid layer order?

    SAT means yes, with a witness. UNSAT is a PROOF that none exists -- over
    the crease set `cons` was built from, which fixes the F set. OVERSIZE means
    the instance was too big to decide and says nothing about either.

    The verdict on a SAT model comes from `layer_certify.verify`, not from
    `layer_certify.decide`: the model already assigns every order variable, so
    a complete relation is in hand and searching for one again would cost
    15-50 s (measured, evidence `2026-10-02-witness-identity-113` section 16.1)
    for an answer we have. `verify` checks every clause `clauses(cons)`
    generates against the relation, which is what CERTIFIED claims -- but only
    when that relation is COMPLETE, and `verify` documents that "a CERTIFIED
    verdict requires `skipped == 0`". That rests on `encode`'s `lit()` raising
    on any clause naming a pair outside `cons.pairs` while the relation spans
    every pair of `cons.pairs`; this function does not rely on that coupling
    silently and refuses on `skipped > 0` itself.
    """
    bound = raw_triple_bound(cons)
    if bound > max_raw_triples:
        return SatResult(
            sat=False, labels=None, relation=None,
            verdict=SatVerdict(
                kind="OVERSIZE", violation=None, order_vars=len(cons.pairs),
                label_vars=len({sl.edge for sl in slots}), clauses=0,
                build_secs=0.0, solve_secs=0.0))

    # Bound inside the `try` so a construction failure of any exception type
    # reaches `finally`; `s` starts None so `finally` never deletes an
    # unbound solver.
    s = None
    try:
        s = Solver(name=solver)
        t0 = time.perf_counter()
        st = encode(cons, slots, s.add_clause, max_clauses=max_clauses)
        build = round(time.perf_counter() - t0, 3)

        t1 = time.perf_counter()
        sat = s.solve()
        model = s.get_model() if sat else None
        solve_secs = round(time.perf_counter() - t1, 3)
    except ClauseBudgetExceeded as exc:
        # Clause generation DID run for `build_secs` before the budget
        # tripped, and `exc.emitted` is the count at the crossing. `solve_secs`
        # is honestly 0.0: the solver never started.
        return SatResult(
            sat=False, labels=None, relation=None,
            verdict=SatVerdict(
                kind="OVERSIZE", violation=None, order_vars=len(cons.pairs),
                label_vars=len({sl.edge for sl in slots}),
                clauses=exc.emitted,
                build_secs=round(time.perf_counter() - t0, 3),
                solve_secs=0.0))
    finally:
        if s is not None:
            s.delete()

    base = dict(order_vars=len(st.order_var), label_vars=len(st.label_var),
                clauses=st.clauses, build_secs=build, solve_secs=solve_secs)

    if not sat:
        return SatResult(sat=False, labels=None, relation=None,
                         verdict=SatVerdict(kind="REFUTED", violation=None,
                                            **base))

    true = {l for l in model if l > 0}
    relation = {p: (v in true) for p, v in st.order_var.items()}
    labels = {e: ("V" if v in true else "M")
              for e, v in st.label_var.items()}

    vr = layer_certify.verify(cons, relation)
    if vr.skipped:
        raise SatOrderError(
            f"`layer_certify.verify` SKIPPED {vr.skipped} clause(s) it could "
            f"not evaluate against this module's SAT model, so the check was "
            f"partial and CERTIFIED would be a false claim (`verify`: a "
            f"CERTIFIED verdict requires skipped == 0). The relation does not "
            f"decide every pair a clause names, so `encode` and `solve` have "
            f"drifted apart. This is a defect in `sat_order`, never a fact "
            f"about the tree.")
    if vr.violation is not None:
        raise SatOrderError(
            f"`layer_certify.verify` REJECTS this module's own SAT model: "
            f"{vr.violation}. The CNF admitted a relation the project's "
            f"verifier calls invalid, so this encoder is under-constrained. "
            f"This is a defect in `sat_order`, never a fact about the tree, "
            f"which is why it raises instead of returning a verdict.")

    return SatResult(sat=True, labels=labels, relation=relation,
                     verdict=SatVerdict(kind="CERTIFIED", violation=None,
                                        **base))
