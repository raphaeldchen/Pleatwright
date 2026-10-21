"""The production arm: restriction of the clause set, and subset selection.

Spec: `docs/superpowers/specs/2026-10-04-pointwise-oracle-design.md` sections
4 and 5.

This module DOES import production, deliberately: `layer_certify.clauses` is
the thing under test. `build._folded_of` is REUSED rather than retyped,
because an independently written version of exactly that step produced last
slice's defect -- it indexed `polys` where production's `_seg_of` indexes
`result.folded_vertices`, and `layer_order._polys_of` reverses any
negative-area face, which on this subject is 190 of 380.

THE PRIMARY COMPARISON IS NOT IN THIS MODULE'S SUBSET MACHINERY. It is the
exhaustive triple comparison of spec section 4A: `(x, {fa, fb})` triples from
the oracle (`stacks.triples`) against those recovered from production's
`equality` clauses (`equality_triples`). The subset functions below
(`classify`, `candidate_subsets`, `restricted_clauses`) were written for the
earlier subset-sampling design, which was measured vacuous; they now feed only
the SECONDARY order-set comparison (spec section 5.1).

Two senses of "population B" exist and must not be confused:
  * section 4A.5's population B is "subsets built around an ONLY-ORACLE
    triple": a neighbourhood where the geometry crosses a face but production
    emitted no constraint. Measured only-oracle is 0, so this population is
    EMPTY, and that is the RESULT, not a failure.
  * `classify`'s `"B"` means only "production emits no geometric constraint
    inside this subset". That is much weaker, and is NOT 4A.5's population B.

TWO DEPARTURES FROM THE ORIGINAL SPEC, both recorded in the plan:
  1. Subsets are seeded from `Clause.variables`, not from `Prov.faces`:
     `Clause.prov` is a `str` (`layer_certify.py:65`), so `layer_order.Prov`'s
     structural faces do not survive into the clause. The variables carry the
     same faces and do not depend on a message format.
  2. `classify` is defined over the RESTRICTED clause set, not over global
     face membership: a clause with one variable outside the subset says
     nothing the oracle can check. This departure is retained but is NO LONGER
     LOAD-BEARING, since the primary comparison (4A) does not use subsets at
     all.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "..", "..", "..", "mcp_harness"))
sys.path.insert(0, os.path.join(_HERE, "..", "2026-10-04-exact-arrangement"))

import build                           # noqa: E402
import layer_certify                   # noqa: E402

#: The families the enumeration ENUMERATES -- which is NOT the same as the
#: families it independently checks. `transitivity` is excluded because it is
#: vacuously satisfied by every total order (`_satisfied`'s predicate cannot
#: fail on an acyclic total relation), so it is covered instead by
#: `test_restrict.py::test_transitivity_family_rejects_a_cyclic_relation`.
#:
#: ⚠ This comment used to read "the families the enumeration can actually
#: test", which is FALSE for `taco`, measured 2026-10-05. `taco` is enumerated
#: here but NOT independently checked: the oracle decides from strict-interior
#: geometry and is blind to collinear-overlapping crease pairs, which is 164 of
#: 164 of the clauses that rejected an order the oracle admitted. See spec
#: section 9, limitation 12, and `stacks.py`'s docstring. The driver reflects
#: the distinction in its artifact: this constant is emitted as
#: `families_enumerated`, with `families_independently_checked` separate.
GEOMETRIC_FAMILIES = ("equality", "taco")


def crease_segments(result, K):
    """Every M/V shared edge as `(fa, fb, seg)`, in kernel numbers.

    The index lookup is deliberately identical to `layer_order`'s `_seg_of`
    closure (`:527-531`) and `build`'s `seg_of` (`:91-94`): folded vertices are
    read PER FACE out of `result.folded_vertices`, never out of the clipping
    polygons. The kernel conversion itself is `build._folded_of`, reused.
    """
    folded = build._folded_of(result, K)
    out = []
    for fa, fb, k, a in result.shared_edges:
        if a not in ("M", "V"):
            continue
        face = result.faces[fa]
        i0, i1 = face.index(k[0]), face.index(k[1])
        out.append((fa, fb, (folded[fa][i0], folded[fa][i1])))
    return tuple(out)


def creases_in(creases, subset):
    """The creases with BOTH faces inside `subset`."""
    return tuple((fa, fb, seg) for fa, fb, seg in creases
                 if fa in subset and fb in subset)


def geometric(all_clauses):
    """The clauses whose family carries geometric content.

    Exists for a measured reason: the full clause set on this subject is
    4,614,726 clauses, of which 4,511,932 are `transitivity`, leaving 102,794
    geometric ones. `classify` and `restricted_clauses` read only the
    geometric families, so scanning the full tuple on every call is about 45x
    wasted work; the driver filters once and passes the result down.
    """
    return tuple(c for c in all_clauses if c.family in GEOMETRIC_FAMILIES)


def equality_triples(all_clauses):
    """Each `equality` clause as `(x, frozenset({fa, fb}))`.

    An `equality` clause's two variables are `_lit(x, fa)` and `_lit(x, fb)`
    (`layer_order.py:362-366`), and `Clause.variables` holds the canonical
    PAIRS directly, not `(pair, flip)` tuples. So `x` is the single face common
    to both pairs and `{fa, fb}` is what remains.

    Refuses loudly (`ValueError` naming the clause) if the two pairs do not
    share exactly one face: silently skipping such a clause would shrink the
    production population without saying so, and the point of the comparison
    is that neither side is quietly smaller than the other.
    """
    out = []
    for c in all_clauses:
        if c.family != "equality":
            continue
        if len(c.variables) != 2:
            raise ValueError(
                f"equality clause {c!r} has {len(c.variables)} variables, "
                f"expected 2")
        p, q = c.variables
        common = set(p) & set(q)
        if len(common) != 1:
            raise ValueError(
                f"equality clause {c!r}: pairs {p} and {q} do not share "
                f"exactly one face (shared: {sorted(common)}); skipping it "
                f"would shrink the production population silently")
        (x,) = common
        out.append((x, frozenset(set(p) ^ set(q))))
    return tuple(out)


def restricted_clauses(all_clauses, subset):
    """Clauses every one of whose variables lies inside `subset`.

    Both directions are tested. Admitting a clause with a variable outside
    would ask the oracle about a face it cannot see; dropping one that is
    wholly inside would weaken the production arm and manufacture agreement.
    """
    return tuple(c for c in all_clauses
                 if all(lo in subset and hi in subset
                        for lo, hi in c.variables))


def order_to_rel(order):
    """`rel[(lo, hi)] = "lo above hi"`, from a top-to-bottom stack.

    `layer_certify._satisfied` pins the convention at `:143`: "rel[(lo, hi)] is
    True means lo above hi". `order[0]` is topmost, so "above" is a SMALLER
    index.
    """
    pos = {f: i for i, f in enumerate(order)}
    faces = sorted(order)
    return {(lo, hi): pos[lo] < pos[hi]
            for i, lo in enumerate(faces) for hi in faces[i + 1:]}


def clause_accepts(clauses_sub, rel):
    """Every restricted clause satisfied under `rel`.

    Evaluated with production's own `_satisfied`, which is the point: the
    production arm must be production's predicate, not a reimplementation of
    it. A literal's value is `rel[pair] != flip` (`Clause`'s docstring,
    `layer_certify.py:56-61`).
    """
    for c in clauses_sub:
        vals = tuple(rel[pair] != flip
                     for pair, flip in zip(c.variables, c.flips))
        if not layer_certify._satisfied(c.family, vals):
            return False
    return True


def classify(all_clauses, subset):
    """`"A"` if production emits a geometric constraint INSIDE `subset`, else
    `"B"`.

    `"B"` here means exactly one thing: "production emits no geometric
    constraint inside this subset". It is NOT spec section 4A.5's population B,
    which is "a subset built around an ONLY-ORACLE triple" (the geometry
    crosses a face but production emitted nothing).

    The two differ, and by a lot. On the real witness this function returns
    `"B"` for 337 subsets at `max_size=4`, while 4A.5's population B is EMPTY
    (only-oracle is 0). The reason is that a subset with no interior clause
    usually has no oracle site either, so `classify`'s `"B"` does not by itself
    indicate that production missed anything. Read it as "no production
    constraint here", never as "a place production should have spoken".
    """
    for c in restricted_clauses(all_clauses, subset):
        if c.family in GEOMETRIC_FAMILIES:
            return "A"
    return "B"


def candidate_subsets(creases, covers, max_size):
    """One subset per crease: its two faces, grown inside a shared cell cover.

    Seeded from a crease and grown only with faces that share a cell with the
    seed, so the additions genuinely overlap it -- padding a subset with faces
    that can never be intruders would inflate the order count without
    strengthening anything. A bare crease pair admits only two orders, which no
    set comparison can distinguish, so growth is not optional.

    Growth makes the ORDER COUNT non-trivial; it does NOT guarantee an active
    oracle site. That was measured: 0 of 19 sampled `classify`-`"B"` subsets
    had any active oracle site. The caller must therefore report the
    active-site count separately rather than assume it.

    THE COVER FALLBACK exists because production guards cover membership with
    `if tuple(sorted((fa, fb))) in pairs` (`layer_order.py:570`), so a crease
    whose two faces share no cover is POSSIBLE. Requiring a cover to contain
    the whole seed would silently drop every such crease. Covers that merely
    INTERSECT the seed still supply genuinely overlapping faces, so they are
    the correct second choice.

    It is MEASURED UNEXERCISED on the real witness: 0 creases have two faces
    sharing no cover. That measurement is subject-specific, which is why the
    fallback is kept (it is cheap) rather than deleted. This function returns
    no count of how many seeds used it; any such count is the DRIVER's to
    report, not this function's.
    """
    out, seen = [], set()
    for fa, fb, _seg in creases:
        seed = frozenset({fa, fb})
        containing = [c for c in covers if seed <= c]
        pool = containing or [c for c in covers if seed & c]
        best = max(pool, key=len, default=frozenset())
        grown = set(seed)
        for f in sorted(best - seed):
            if len(grown) >= max_size:
                break
            grown.add(f)
        s = frozenset(grown)
        if len(s) < 3 or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return tuple(out)
