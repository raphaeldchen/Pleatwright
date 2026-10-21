"""Is there a COMPLETE layer order for this folded state, and does it
satisfy every constraint?

`layer_order` derives FORCED relations only. Its own docstring says it
"does NOT decide whether a total order exists, so 'no contradiction' is
weaker than ADK's satisfiability result." This module closes that gap for
the box-pleat compiler, by checking Akitaya-Demaine-Ku's families as
CLAUSES against a complete relation (`verify`) and searching for one where
propagation leaves variables undecided (`decide`).

Akitaya, Demaine & Ku, "Computing Flat-Folded States" (OSME 2024) prove a
facewise layer order is verified in O(min{n^2 p, n^2 + m p^2}) = O(n^3) --
verifying is in P, finding one is in NP. Their O(n^3 + sum t_i^3 2^t_i)
algorithm enumerates ALL folded states; we need ONE, which is why `decide`
branches instead of enumerating.

⚠ CERTIFIED IS NOT FLAT-FOLDABLE. `layer_order.AREA_EPS` drops sliver
arrangement cells before `cons.pairs` is built, and a dropped cell REMOVES
constraints and can never add one. So CERTIFIED means "certified against
the constraint set that survived AREA_EPS", which is strictly weaker than
a proof. Closing that is separate work.

⚠ THIS MODULE DOES NOT EDIT `layer_order.py`, BY DESIGN. When it was
written, four TreeMaker serve-path callers read that module --
`mv_symmetrize._LayerGate`, `mv_repair`, `root_rank` and `server.py`'s serve
gate, all now on archive/treemaker-box-pleat -- and every serve-path reading
on record, including quadruped's contradiction -> consistent from the root
wave, was taken with the propagation-only rule.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from itertools import combinations

from . import layer_order
from .layer_order import Prov, _lit

#: Search nodes `decide` may spend before returning UNDECIDED. Basis,
#: measured 2026-09-23: `starfish` is the only corpus subject on which this
#: can bind (the other seven leave 0 or 2 free variables) and one
#: `layer_order.propagate` there costs 2.31 ms, so this bounds the
#: PROPAGATION-only worst case at roughly 115 s -- below costs this corpus
#: already carries (guinea_pig 295 s, dog 578 s). Each node also runs
#: `verify` over every leaf clause once its relation completes, and that
#: per-leaf cost is ADDITIONAL to the 115 s figure, not included in it --
#: the 115 s basis counts propagation calls only. A search needing more
#: than this on 114 variables will not finish at 500,000 either, so it is a
#: give-up threshold, not a tuning knob -- the role `layer_budget` plays in
#: the CEGAR loop.
CERTIFY_BUDGET = 50_000


@dataclass(frozen=True)
class Clause:
    """One ADK constraint, as a CHECK over canonical pair-variables.

    `variables[i]` is a canonical `(lo, hi)` face pair and `flips[i]` the
    matching flip bit from `layer_order._lit`, so the literal's value is
    `rel[variables[i]] != flips[i]`. `family` selects the predicate in
    `_satisfied`."""
    family: str          # equality | transitivity | taco
    variables: tuple
    flips: tuple
    prov: str


def _value(rel: dict, pair, flip: bool) -> bool:
    """A literal's value: `layer_order`'s own rule, one copy."""
    return rel[pair] != flip


def _iter_clauses(cons):
    """ADK's families from `cons`, as checks rather than writes -- yielded
    rather than collected, so a caller that only needs to walk them once
    (`verify`) is not forced to hold every one in memory at once. On a
    180-face cover, `combinations(sorted(cover), 3)` alone is roughly
    C(180,3) ~= 953,000 triples, i.e. that many `Clause` objects if
    materialised.

    Emits NOTHING `cons` does not already carry -- this changes direction,
    not coverage (design doc section 4.1). Antisymmetry is absent on
    purpose: `_lit` gives one canonical variable per unordered pair, so
    "Lij = -Lji" is unrepresentable-as-violated rather than checked.

    A triple can be witnessed by more than one cover; its constraint is the
    same constraint either way, so triples are de-duplicated."""
    for la, lb, prov in cons.equalities:
        yield Clause("equality", (la[0], lb[0]), (la[1], lb[1]), str(prov))
    seen = set()
    for cover in cons.covers:
        for a, b, c in combinations(sorted(cover), 3):
            if (a, b, c) in seen:
                continue
            seen.add((a, b, c))
            yield Clause("transitivity", ((a, b), (b, c), (a, c)),
                        (False, False, False), f"transitivity {a},{b},{c}")
    for (p, q), (r, s), prov in cons.tacos:
        lits = (_lit(r, p), _lit(r, q), _lit(s, p), _lit(s, q))
        yield Clause("taco", tuple(li[0] for li in lits),
                    tuple(li[1] for li in lits), str(prov))


def clauses(cons) -> tuple:
    """ADK's families from `cons`, as checks rather than writes.

    A thin wrapper over `_iter_clauses` that materialises the whole set --
    kept for callers (tests, mainly) that want to slice, count or
    re-iterate the clause set, none of which a generator supports. `verify`
    below uses `_iter_clauses` directly instead, since it only ever walks
    the set once. The clause set the two produce is identical."""
    return tuple(_iter_clauses(cons))


@dataclass(frozen=True)
class Violation:
    """A clause a complete relation does not satisfy.

    On a relation `layer_order.propagate` accepted, this is a FINDING:
    propagation was wrong on that input. Per the standing ruling, the
    caller refuses rather than emitting.

    The shape of `variables` depends on `family`:
    - For `"equality"`, `"transitivity"`, and `"taco"`: canonical `(lo, hi)`
      face **pairs** -- the clause's variables that the check evaluated.
    - For `"propagate"`: face **indices** that the contradiction's provenance
      named, because this violation reports something `layer_order`'s
      propagation already decided rather than a clause anyone can evaluate."""
    family: str
    variables: tuple
    values: tuple
    prov: str


@dataclass(frozen=True)
class VerifyResult:
    violation: Violation | None
    checked: int         # clauses fully evaluated
    skipped: int         # clauses an undecided variable made unevaluable


def _satisfied(family: str, vals: tuple) -> bool:
    """`rel[(lo, hi)] is True` means `lo` above `hi`, so the two cyclic
    states of a sorted triple are (T, T, F) and (F, F, T)."""
    if family == "equality":
        return vals[0] == vals[1]
    if family == "transitivity":
        rab, rbc, rac = vals
        return not (rab == rbc and rac != rab)
    if family == "taco":
        return (vals[0] != vals[1]) == (vals[2] != vals[3])
    raise ValueError(
        f"layer_certify._satisfied: unknown family {family!r} -- add its "
        f"predicate rather than let it fall through to a default, which "
        f"would silently certify a family nobody checks")


def verify(cons, rel: dict) -> VerifyResult:
    """Every clause from `clauses(cons)`, checked against `rel`.

    A clause naming a pair `rel` does not decide cannot be evaluated; it is
    SKIPPED and counted, and `skipped` is returned beside the violation so
    no caller can mistake a partial check for a complete one. A CERTIFIED
    verdict requires `skipped == 0`. Polynomial, no search -- ADK prove this
    direction is O(n^3) and in P.

    Enforces every clause `clauses(cons)` would generate, and nothing more:
    `cons.direct` (the crease-direction seeds) generates no clause of its
    own, so `verify` alone will accept a relation that inverts a crease's
    M/V sense. Inside `decide` this is covered anyway, because
    `layer_order._propagate` seeds `direct` first and raises
    `LayerContradiction` on a conflict before `verify` ever runs -- but a
    caller that calls `verify` directly, on a relation `propagate` did not
    build, is not protected by that and should not read a clean `verify`
    result as also having checked `direct`."""
    checked = skipped = 0
    for c in _iter_clauses(cons):
        if any(pr not in rel for pr in c.variables):
            skipped += 1
            continue
        vals = tuple(_value(rel, pr, fl)
                     for pr, fl in zip(c.variables, c.flips))
        checked += 1
        if not _satisfied(c.family, vals):
            return VerifyResult(
                Violation(c.family, c.variables, vals, c.prov),
                checked, skipped)
    return VerifyResult(None, checked, skipped)


class _ParityDSU:
    """Union-find carrying a parity bit per element.

    `find` returns `(root, parity_to_root)`; `union(a, b, parity)` returns
    False when the edge contradicts the existing parity, i.e. an odd
    cycle."""

    def __init__(self):
        self._parent: dict = {}
        self._par: dict = {}

    def find(self, x):
        if x not in self._parent:
            self._parent[x], self._par[x] = x, False
            return x, False
        if self._parent[x] == x:
            return x, False
        root, up = self.find(self._parent[x])
        self._parent[x], self._par[x] = root, self._par[x] != up
        return root, self._par[x]

    def union(self, a, b, parity: bool) -> bool:
        ra, pa = self.find(a)
        rb, pb = self.find(b)
        if ra == rb:
            return (pa != pb) == parity
        self._parent[ra] = rb
        self._par[ra] = (pa != pb) != parity
        return True


def collapse(cons, free):
    """Quotient the free variables by the equality constraints' parity.

    Returns `(classes, odd_cycle)`. `classes` maps every element of `free`
    to its class representative; `decide` branches on representatives, so
    the search space is the quotient rather than `free` itself (measured
    2026-09-23: starfish 252 -> 114, bird and lizard 8 -> 2).

    `odd_cycle` is a `Violation` when the parity graph contains one, else
    None: an odd cycle is unsatisfiable, and propagation does not find it,
    so `decide` turns it straight into REFUTED with no search.

    Only equalities whose BOTH variables are in `free` can merge: one
    forced side means the value is already known, and there is nothing to
    quotient.

    This does NOT rewrite the CSP. `decide` seeds only a representative and
    lets `layer_order._propagate`'s existing equality rule fill the rest of
    the class, so there is one implementation of the equality semantics,
    not two."""
    dsu = _ParityDSU()
    for pr in free:
        dsu.find(pr)
    for la, lb, prov in cons.equalities:
        if la[0] in free and lb[0] in free:
            if not dsu.union(la[0], lb[0], la[1] != lb[1]):
                return ({pr: dsu.find(pr)[0] for pr in free},
                        Violation("equality", (la[0], lb[0]), (), str(prov)))
    return {pr: dsu.find(pr)[0] for pr in free}, None


@dataclass(frozen=True)
class Verdict:
    """CERTIFIED: a complete layer order exists and satisfies every clause
    `clauses` generates -- which is NOT the same as flat-foldable, see this
    module's docstring on AREA_EPS.

    REFUTED: no complete order exists. `violation`, when set, names the
    cause. A `family="propagate"` violation means `layer_order.propagate`
    itself raised a contradiction on that branch -- the search never
    finished building a relation there, so neither `collapse` nor `verify`
    ran. A `"transitivity"` / `"taco"` violation, or an `"equality"`
    violation that came from `verify`, means propagation completed a
    relation clean but that relation fails one of ADK's clauses on a
    relation propagation itself ACCEPTED -- a finding about propagation's
    own correctness on that input, not just about the folded state. An
    `"equality"` violation can also come from `collapse`'s own odd-cycle
    check, before any relation is complete: an odd parity cycle among free
    variables is unsatisfiable however they are assigned, so it refutes
    without a branch ever reaching `verify`. `violation` is `None` when no
    single clause is responsible: the search exhausted every branch
    without any one of them surviving to be blamed, so REFUTED-with-`None`
    is a statement about the whole space, not a pointer into it. When the
    root itself contradicted before any free count was taken, `free` is
    left at its initial `0` -- so a caller reading `free == 0` on a
    REFUTED verdict must check whether `violation is not None and
    violation.family == "propagate"` before concluding the relation was
    ever complete enough to count.

    UNDECIDED: the budget ran out. This says nothing about the folded
    state, only about this search's cost -- the same distinction the
    archived Lang compiler's `LayerFail` drew between "no_labelling" and
    "budget".

    `free` is the number of independent variables at the ROOT, after the
    equality quotient -- CLASSES, not unforced pairs. `bird` reads 2, not
    the 8 pairs the census counts."""
    kind: str
    violation: Violation | None
    nodes: int
    free: int


class _Exhausted(Exception):
    """Internal: the node budget ran out mid-search."""


def decide(cons, *, budget: int = CERTIFY_BUDGET) -> Verdict:
    """Does a complete, valid facewise layer order exist for `cons`?

    Branch and propagate. `layer_order.propagate` is reused as the
    propagation step rather than reimplemented, so the two can never
    disagree about what a constraint means. Every completed relation is
    run through `verify` before it may certify: propagation is the thing
    being audited, so the search must never certify on its word alone.

    ADK's O(n^3 + sum t_i^3 2^t_i) algorithm enumerates ALL folded states.
    This wants ONE, which is why starfish's single 114-variable component
    is reachable at all. The corpus aligns favourably: the subjects
    needing a search are the ones where a single propagate is cheapest
    (starfish 38 faces at 2.31 ms, lizard 20), while the expensive ones
    (dog 298 faces, horse 166) leave zero free variables and need none.
    That is a measured property of this corpus, not a theorem, which is
    why `budget` exists."""
    counter = [0]
    root_free = [0]

    def search(extra: tuple):
        if counter[0] >= budget:
            raise _Exhausted
        counter[0] += 1
        root = not extra
        c = (cons if root
             else dataclasses.replace(cons, direct=cons.direct + extra))
        try:
            rel = layer_order.propagate(c)
        except layer_order.LayerContradiction as exc:
            return None, Violation("propagate", tuple(exc.prov.faces), (),
                                    str(exc))
        free = set(c.pairs) - set(rel)
        if not free:
            if root:
                root_free[0] = 0
            out = verify(c, rel)
            # `free == 0` means `rel` covers every pair in `c.pairs`, and
            # every clause `clauses` emits draws its variables from
            # `c.pairs` (see `clauses`'s own body), so nothing verify()
            # looks up can be missing from `rel` -- `skipped` must be 0.
            # Asserted rather than merely relied on: if this ever fired, a
            # REFUTED verdict below would be claiming no complete order
            # exists when the check that found the "violation" was
            # actually partial, which is exactly the false claim `verify`'s
            # own `skipped` field exists to prevent.
            assert out.skipped == 0
            if out.violation is None and out.skipped == 0:
                return rel, None
            return None, out.violation
        classes, odd = collapse(c, free)
        if root:
            root_free[0] = len({classes[pr] for pr in free})
        if odd is not None:
            return None, odd
        pick = sorted({classes[pr] for pr in free})[0]
        last = None
        for val in (True, False):
            seed = ((pick, False), val,
                    Prov(f"certify decision {pick}={val}", faces=pick))
            got, vio = search(extra + (seed,))
            if got is not None:
                return got, None
            last = vio if vio is not None else last
        return None, last

    try:
        rel, vio = search(())
    except (_Exhausted, RecursionError):
        # `search` recurses once per decision (depth <= the number of free
        # classes -- 114 measured on starfish, against Python's ~1000
        # default limit). On an instance with roughly 1000+ free classes
        # the interpreter's recursion limit can bind before `budget`
        # (50,000 nodes) does, and `RecursionError` is a `RuntimeError`
        # subclass that would otherwise escape a caller's
        # `except (ValueError, RuntimeError, KeyError)` (the archived Lang
        # compiler had exactly that handler) instead of returning the
        # UNDECIDED the budget promises. Caught here rather
        # than left to propagate, on the same terms as `_Exhausted`: this
        # search stopped, and says nothing about whether a labelling
        # exists. If this is ever observed, the real fix is converting
        # `search` to an explicit stack rather than raising the limit.
        return Verdict("UNDECIDED", None, counter[0], root_free[0])
    if rel is not None:
        return Verdict("CERTIFIED", None, counter[0], root_free[0])
    return Verdict("REFUTED", vio, counter[0], root_free[0])
