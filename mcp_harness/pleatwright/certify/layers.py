"""A candidate M/V labelling -> a global layer-order verdict
(spec 2026-09-22-pleat-reassignment §4.1).

⚠ Under-refutation, inherited from `layer_order` (this module re-exports its
answer, it does not strengthen it): a `None` verdict means no contradiction
was FOUND, never a proof of flat-foldability, for two independent reasons —
`layer_order._propagate` is not confluent (spec §10), and the module
under-refutes further via `AREA_EPS`-dropped sliver cells (its own module
docstring). Only the positive direction (a witness) is sound.

`layer_order` decides whether a folded state has a consistent layer order,
to the extent the above allows.
Everything it derives except the `direct` facts comes from folded geometry,
which `flat_fold` builds from the crease SET alone -- so the expensive part
is built once per crease set (`constraint_graph`) and every candidate
labelling only re-propagates (`propagate`). Measured 2026-09-22: building
costs 1.7-2.2 s, propagating costs milliseconds.

A contradiction comes back as a `Witness` whose `creases` are the label
decisions it followed from -- a sound no-good clause, not a guess.

This module deliberately does NOT reimplement `layer_order.constraints_for`
or `mv_symmetrize._LayerGate`'s geometry build (plan amendment 2026-09-22,
"adapt `mv_symmetrize._LayerGate`"): `constraint_graph` below delegates the
whole build to `layer_order.constraints_for`, which already does exactly
what `_LayerGate.__init__` open-codes. `_LayerGate` itself is left
untouched -- it was on the TreeMaker serve path (now archived) and
soft-failed where this module raises, so the two were not merged.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass

from . import layer_certify, layer_order

_KIND = (("taco-tortilla", "taco_tortilla"),
         ("tortilla-tortilla", "tortilla_tortilla"),
         ("taco-taco", "taco_taco"),
         ("transitivity", "transitivity"),
         ("crease", "direct"))


@dataclass(frozen=True)
class Witness:
    kind: str            # taco_tortilla | tortilla_tortilla | taco_taco | transitivity | direct
    creases: frozenset   # FOLD edge keys (v_lo, v_hi) whose LABELS caused it
    faces: tuple         # face indices the provenance names; diagnostic only
    prov: str            # layer_order's message, unchanged


@dataclass(frozen=True)
class LayerGraph:
    cons: object         # layer_order._Constraints, label-independent part
    slots: tuple         # layer_order.DirectSlot per creased shared edge


def _kind_of(text: str) -> str:
    for needle, kind in _KIND:
        if text.startswith(needle):
            return kind
    raise ValueError(
        f"layers._kind_of: unrecognized provenance {text!r} -- add its "
        f"prefix to _KIND rather than let it fall through to a guessed "
        f"kind (the old fallback silently returned 'direct', a real kind, "
        f"for any future layer_order provenance family)")


def _seed(slot, label: str) -> bool:
    """The DirectSlot + label -> boolean rule that seeds `direct`.

    This is the ONLY copy of the formula in this module: both `propagate`
    (the hot path, called per candidate) and the drift guard in
    `constraint_graph` below call this function rather than each inlining
    their own copy of `(label == "V") == (slot.sign == 1)`. A prior version
    inlined it twice, so the guard was checking a copy of the formula that
    was not the one actually used per candidate -- it could not detect
    drift in `propagate`'s own copy. Routing both through one function
    makes the two unrepresentable as different things, rather than merely
    checked to currently agree."""
    return (label == "V") == (slot.sign == 1)


def constraint_graph(ff) -> LayerGraph:
    """The label-independent layer-order system of a folded state.

    Delegates the whole build to `layer_order.constraints_for`, which
    raises `ValueError` when `ff` is closure-inconsistent (no consistent
    flat fold exists to order layers in). That is propagated here, not
    swallowed: a caller that hands this module a closure-inconsistent
    folded state gets a loud refusal rather than a plausible-looking empty
    graph, matching `layer_order.constraints_for`'s own stated reason for
    refusing (plan amendment "correction for Task 4").

    Carries the drift guard the plan requires (amendment "correction for
    Task 4"): `layer_order._build_constraints` computes each `direct`
    entry's boolean as `(a == "V") == (orient[fa] == 1)` while building
    `cons.direct`; `_seed` above is this module's copy of that same rule,
    and it is the copy `propagate` actually calls per candidate. So this
    is a round-trip check on the formula that runs, not a separate one:
    rebuild `direct` from `slots` under the folded state's OWN labels via
    `_seed` and assert it reproduces `cons.direct` element for element. It
    fires if `_seed` drifts from `_build_constraints`'s rule, if `sign`
    stops meaning `orient[fa]`, or if slot ordering stops matching
    `direct`'s. Deliberately a one-time check here rather than inside
    `propagate`, which Task 7 calls per candidate."""
    cons, slots = layer_order.constraints_for(ff)
    own_labels = {k: a for _, _, k, a in ff.shared_edges if a in ("M", "V")}
    rebuilt = tuple(
        (s.lit, _seed(s, own_labels[s.edge]))
        for s in slots)
    shipped = tuple((lit, val) for lit, val, _ in cons.direct)
    assert rebuilt == shipped, (
        "layers.constraint_graph: direct-seed round-trip disagrees with "
        "layer_order._build_constraints -- the two copies of the seed "
        "formula have drifted apart")
    return LayerGraph(cons=cons, slots=slots)


def _seeded(graph: LayerGraph, labels: dict, only=None):
    """`graph.cons` with `direct` seeded from `labels`.

    The ONLY place the seeding happens: both `propagate` (the per-candidate
    filter) and `certify` (once, on the accepted candidate) go through it,
    so the two tiers cannot end up judging different constraint sets.

    `only`, when not `None`, is a set of edge keys: ONLY those slots are
    seeded and every other slot is left unconstrained. `None` seeds every
    slot, which is the behaviour every existing caller gets. Extra keys in
    `only` that are not slot edges are ignored, so a caller may pass a
    superset (spec `2026-09-27-nogood-core-design.md` §4.1: the core
    oracle's candidate set comes from a witness, whose creases are not
    guaranteed to all be slots).
    """
    slots = (graph.slots if only is None
             else tuple(s for s in graph.slots if s.edge in only))
    direct = tuple(
        (s.lit, _seed(s, labels[s.edge]),
         layer_order.Prov(f"crease {s.edge} {labels[s.edge]}",
                          creases=(s.edge,), faces=s.faces))
        for s in slots)
    return dataclasses.replace(graph.cons, direct=direct)


def propagate(graph: LayerGraph, labels: dict, *, only=None) -> Witness | None:
    """None when no contradiction was FOUND for `labels` (not a proof that a
    consistent layer order exists -- see the under-refutation caveat in this
    module's docstring), else the witness.

    This is the CEGAR loop's per-candidate filter and stays deliberately
    cheap: ~300 ms on horse, and sound in the only direction the loop needs
    (a contradiction is a valid no-good clause). `certify` below is the
    expensive tier and runs once, on the candidate the loop accepts.

    `labels` maps every slot's edge key to "M" or "V".
    `only`, when not `None`, seeds ONLY those edge keys, so a contradiction
    it reports is forced by THOSE creases alone. This is the minimal-core
    oracle of spec `2026-09-27-nogood-core-design.md` §4. `None` -- the
    default, and what every production call site passes -- seeds every slot
    and is the pre-existing behaviour exactly.
    """
    try:
        layer_order.propagate(_seeded(graph, labels, only), deps=True)
    except layer_order.LayerContradiction as exc:
        return Witness(kind=_kind_of(exc.prov.text),
                       creases=frozenset(exc.deps or ()),
                       faces=tuple(exc.prov.faces), prov=str(exc))
    return None


def certify(graph: LayerGraph, labels: dict, *,
            budget: int = layer_certify.CERTIFY_BUDGET):
    """Does a complete, valid layer order exist for `labels`?

    The answer `propagate` above cannot give. Runs ONCE per compile, on the
    candidate the CEGAR loop accepted -- never per candidate, which would
    multiply the per-rejection cost that already dominates `dog` (578 s)
    and leaves `rabbit` unresolved.

    Returns a `layer_certify.Verdict`. CERTIFIED is still not a proof of
    flat-foldability: see `layer_certify`'s module docstring on
    AREA_EPS-dropped cells."""
    return layer_certify.decide(_seeded(graph, labels), budget=budget)

