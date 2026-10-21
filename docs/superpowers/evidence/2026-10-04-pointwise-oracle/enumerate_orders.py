"""Every total order of a subset, both verdicts per order, and the comparison.

Spec: `docs/superpowers/specs/2026-10-04-pointwise-oracle-design.md` section 5.

Imports no production code. The production entry points -- `clause_accepts` and
`order_to_rel` -- arrive as ARGUMENTS, so the injection point is explicit and
this layer stays on the independent side of the boundary.

WHY THE ENUMERATION IS AFFORDABLE. The oracle factors. Breakpoints and covering
sets depend only on geometry, so `stacks.sites` runs the exact rational
arithmetic ONCE per subset and reduces it to a list of `Site`s. Each of the
`|S|!` orders is then decided by integer index comparison. At `|S| = 8` that is
40,320 orders against a handful of sites, with no `Fraction` work in the inner
loop.
"""
from itertools import permutations

import stacks


def all_orders(subset):
    """Every total order of `subset`, top-to-bottom, each exactly once."""
    return tuple(permutations(sorted(subset)))


def rel_to_order(rel, subset):
    """A total order consistent with `rel`, or `None` if there is none.

    `rel` is expected COMPLETE over the subset's pairs, which is what
    `sat_order.SatResult.relation` documents itself to be (`:131`), so this is
    a sort rather than a search: a tournament is transitive exactly when its
    score sequence is 0, 1, ..., n-1, so counting how many faces sit above each
    face both orders them and detects a cycle (a repeated score).

    Returns `None` rather than raising, on either a cycle or a missing pair: on
    the validation reading both are findings to report with their subset, not
    reasons to abort the run.
    """
    faces = sorted(subset)
    above = {f: 0 for f in faces}
    for i, lo in enumerate(faces):
        for hi in faces[i + 1:]:
            if (lo, hi) not in rel:
                return None
            if rel[(lo, hi)]:
                above[hi] += 1
            else:
                above[lo] += 1
    scores = [above[f] for f in faces]
    if len(set(scores)) != len(scores):
        return None
    return tuple(sorted(faces, key=lambda f: above[f]))


def compare(sites_tuple, clauses_sub, subset, clause_accepts, order_to_rel):
    """The set comparison (spec section 5.1).

    Returns both counts AND both difference directions, separately. Not "do
    both say foldable": an existence-only comparison passes a wrong clause set
    whenever at least one valid order survives, and substituting a weaker
    comparison for the designated one is the error this project recorded
    against the previous slice's spec section 4.
    """
    act = stacks.active(sites_tuple)
    for s in act:
        stray = s.cover - frozenset(subset)
        if stray:
            raise ValueError(
                f"site for crease ({s.fa}, {s.fb}) has cover faces "
                f"{sorted(stray)} outside the subset {sorted(subset)}; the "
                f"order would not rank them and the comparison would be "
                f"silently partial")
    orders = all_orders(subset)
    oracle_ok, clause_ok = set(), set()
    for order in orders:
        if stacks.accepts(act, order):
            oracle_ok.add(order)
        if clause_accepts(clauses_sub, order_to_rel(order)):
            clause_ok.add(order)
    return {
        "orders": len(orders),
        "sites_total": len(sites_tuple),
        "sites_active": len(act),
        "oracle_admits": len(oracle_ok),
        "clauses_admit": len(clause_ok),
        "only_oracle": tuple(sorted(oracle_ok - clause_ok)),
        "only_clauses": tuple(sorted(clause_ok - oracle_ok)),
        "identical": oracle_ok == clause_ok,
    }
