"""The numeric policy the transcription is parameterized over.

One code path, two instantiations. FLOAT must reproduce `layer_order`'s
predicates EXACTLY -- it exists to prove the transcription is faithful, and a
predicate that merely resembles production's defeats that purpose. EXACT
replaces each tolerance with the zero test the tolerance was approximating.

Two of production's predicates compare against an **absolute distance**
threshold after normalizing by a segment length (`_collinear_overlap` and
`_segs_interact` end with `min(length, b1) - max(0.0, b0) > GEOM_EPS`).
Scaling that comparison by `length` to remove the square root -- which exact
arithmetic requires, since a norm is irrational -- also removes the
threshold's meaning. The two are equivalent only when the threshold is 0.

So where scaling changes a predicate's meaning, `geom` branches on
`K.name`: the **float** branch reproduces production verbatim, square root
included, because it is the control and must match; the **exact** branch uses
the scaled rational form, where the threshold is exactly 0 and the scaling is
sound. This is the sanctioned use of `K.name`; it is not a licence to branch
wherever the exact path is inconvenient.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Callable

# Copied from layer_order, NOT imported, so the float kernel keeps reproducing
# production even if those constants are retuned: the control must stay fixed
# while the thing it controls moves.
#
# ⚠ THE COPY IS NOT SELF-POLICING. An earlier revision of this comment claimed
# a divergence "shows up as a fidelity-gate failure -- loudly". It would not,
# and this run's own margins are the refutation: `GEOM_EPS` can move 1.66e+04x
# down or 2.16e+05x up without changing ONE decision in the arrangement, so a
# retuned production constant anywhere inside that band would leave both
# fidelity gates green while the float arm measured a predicate production no
# longer uses. What closes that gap is an explicit equality check against the
# imported values -- `exact_arrangement.epsilon_parity`, which refuses on
# divergence. Keep the copies; keep the check.
AREA_EPS = 1e-9
GEOM_EPS = 1e-9
INTERIOR_EPS = 1e-8

MAX_DEN = 10 ** 6
SNAP_TOL = 1e-12


@dataclass(frozen=True)
class Kernel:
    name: str
    conv: Callable            # float -> number
    area_nonzero: Callable    # |area| counts as non-degenerate
    side_keep: Callable       # _clip_half: keep vertex p
    strict_cross: Callable    # _clip_half: (sp, sq) is a strict sign change
    same_point: Callable      # _dedupe_ring: two points coincide
    interior_pos: Callable    # _strictly_inside: cross is strictly positive
    seg_span_pos: Callable    # _clip_seg: span is non-degenerate
    # is_zero: x counts as zero. Reproduces `abs(x) < GEOM_EPS` at
    #   layer_order.py:381 (_clip_seg denom), :401 and :403 (_segs_interact
    #   all-o and length), :432 (_collinear_overlap length) and :452
    #   (_side_of d); and, negated, `abs(x) >= GEOM_EPS` at :429
    #   (_collinear_overlap, via `any`).
    is_zero: Callable
    # is_neg: x is clearly negative. Reproduces `x < -GEOM_EPS` at
    #   layer_order.py:382 (_clip_seg: parallel and fully outside), which is
    #   its ONLY use. An earlier revision of this comment also advertised it
    #   for the straddle tests at :408-411 via the mirror `is_neg(-x)`; that
    #   is arithmetically true but not what the code does -- `segs_interact`
    #   expresses those tests with `K.strict_cross(o1, o2)`, which is
    #   production's straddle expression term for term. No caller passes a
    #   negated argument.
    is_neg: Callable


def _snap(x: float) -> Fraction:
    """Rationalize a folded coordinate, refusing if the snap moves it.

    The input carries <=2.33e-15 of float rounding over a 1/68 grid. A snap
    that moves a coordinate further than SNAP_TOL is rationalizing NOISE into
    a different geometry, which would mean measuring an arrangement production
    never computed.

    This is the FIRST of the two assertions spec section 3 requires. The second
    -- that every denominator divides the observed grid -- cannot live here:
    "the observed grid" is the lcm over the whole input, which one coordinate
    cannot see. It lives in the driver, as `exact_arrangement.input_grid_gate`,
    and refuses there. A snap can be small and still land on an arbitrary
    denominator (`limit_denominator` will happily return 731/999983), which is
    exactly the case this function alone cannot catch.
    """
    f = Fraction(x).limit_denominator(MAX_DEN)
    if abs(float(f) - x) > SNAP_TOL:
        raise SystemExit(
            f"REFUSED: snapping {x!r} to {f} moved it by "
            f"{abs(float(f) - x):.3e}, over SNAP_TOL={SNAP_TOL:.0e}. The "
            f"rationalized input would not be the geometry production used.")
    return f


FLOAT = Kernel(
    name="float",
    conv=float,
    area_nonzero=lambda a: abs(a) > AREA_EPS,
    side_keep=lambda sp: sp >= -GEOM_EPS,
    strict_cross=lambda sp, sq: (sp > GEOM_EPS and sq < -GEOM_EPS)
                             or (sp < -GEOM_EPS and sq > GEOM_EPS),
    same_point=lambda p, q: abs(p[0] - q[0]) <= 1e-9 and abs(p[1] - q[1]) <= 1e-9,
    interior_pos=lambda c: c > INTERIOR_EPS,
    seg_span_pos=lambda d: d > GEOM_EPS,
    is_zero=lambda x: abs(x) < GEOM_EPS,
    is_neg=lambda x: x < -GEOM_EPS,
)

EXACT = Kernel(
    name="exact",
    conv=_snap,
    area_nonzero=lambda a: a != 0,
    side_keep=lambda sp: sp >= 0,
    strict_cross=lambda sp, sq: (sp > 0 and sq < 0) or (sp < 0 and sq > 0),
    same_point=lambda p, q: p == q,
    interior_pos=lambda c: c > 0,
    seg_span_pos=lambda d: d > 0,
    is_zero=lambda x: x == 0,
    is_neg=lambda x: x < 0,
)


@dataclass
class MarginLog:
    """How close each float comparison came to flipping.

    An identical float/exact result is the expected outcome, and an expected
    outcome needs an EXPLANATION or it is indistinguishable from luck. The
    minimum margin per tag is that explanation.
    """
    rows: dict = field(default_factory=dict)

    #: tag -> the largest SIZE seen at that site. Not a margin and not a ratio:
    #: `geom.area`'s bit-identity with production's `np.sum` depends on a
    #: polygon's VERTEX COUNT, not on how close a value sat to a threshold, so
    #: that condition is measured here rather than assumed in a docstring.
    sizes: dict = field(default_factory=dict)

    def observe_max(self, tag: str, n: int) -> None:
        if n > self.sizes.get(tag, -1):
            self.sizes[tag] = n

    def record(self, tag: str, value: float, threshold: float) -> None:
        if threshold <= 0:
            raise ValueError("a margin needs a positive threshold")
        ratio = abs(value) / threshold
        prev = self.rows.get(tag)
        if prev is None or ratio < prev[0]:
            self.rows[tag] = (ratio, abs(value), threshold)

    def minimums(self) -> dict:
        return {tag: {"closest_ratio_to_threshold": r,
                      "value": v, "threshold": t}
                for tag, (r, v, t) in sorted(self.rows.items())}
