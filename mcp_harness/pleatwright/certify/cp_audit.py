"""Interior-soundness audit of a FOLD crease pattern (Stage 2.0/2.3).

Written for TreeMaker's raw hull export (see the package docstring's
PROVENANCE note); on main it is an independent oracle in the tests.
One instrument, four measurements, all pure Python (spawn-safe: no native or
JVM imports — usable inside worker processes and as a CLI):

  1. closure        — flat_fold reflection-cycle errors (ClosureReport);
  2. Maekawa        — per-interior-vertex |M-V| = 2;
  3. Kawasaki       — per-interior-vertex alternating sector residual;
  4. M/V arrangement — per-interior-vertex big-little-big foldability.

(1)-(3) are NECESSARY conditions only. Until Stage 2.3 that was the whole
audit, so `clean` could bless — and the 2.2 ladder could serve — a pack whose
M/V labels sit in a provably unfoldable ARRANGEMENT (a strict-minimum sector
flanked by two same-assignment creases; Oriedita calls it LITTLE_BIG_LITTLE
and the live haiku smoke run produced one). The oracle for (4) lives HERE;
the archived lint_verdict imported it, so the 2.1 verdict, the 2.2 ladder and
this CLI applied ONE interior-defect definition rather than two that can
drift.

INTERIOR-VERTEX DEFINITION (pinned; see tests/test_cp_audit.py): a vertex is
interior iff it has at least one incident crease and NO incident "B" (border)
edge. The raw TreeMaker export traced the leaf-node convex hull with B edges,
so hull-frontier vertices — the benign, documented-ACCEPT lint class — were all
boundary under this definition, and every violation this audit reports is a
REAL interior defect that no frontier argument excuses. (The alternative
paper-border-coordinate definition in probe_degree.py would count hull tips
inside the unit square as interior and drown the signal.)

KAWASAKI_TOL_DEG = 1e-3 degrees is deliberate: template-clean compiles measure
<= ~1e-6 deg at every interior vertex, while the live nudged-mesh defect class
measures ~5e-2 deg (2026-07-18 hf_dog audit) — the default sits three orders
of magnitude above clean and >1 order below the defect class.

F (flat) creases are dropped before the vertex checks, mirroring the linter's
foldability-neutral normalization; closure keeps them (flat_fold joins across
F with the identity, which is exact).

Audits the RAW `json` fold frame. The squared `display_json` frame has no
consistent flat-folded state by design — its closure numbers are meaningless.

CLI:  python -m pleatwright.certify.cp_audit <path.fold> [--json] [--kawasaki-tol-deg D]
      (from mcp_harness/)
      exit 0 = clean, 1 = violations found, 2 = unusable input.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass

from .flat_fold import CLOSURE_EPS, flat_fold

KAWASAKI_TOL_DEG = 1e-3


@dataclass(frozen=True)
class VertexAudit:
    """Audit line for one interior vertex (creases = non-F incident edges).

    arrangement_ok is the RAW per-vertex oracle result, reported for every
    vertex; AuditReport.arrangement_violations is the derived NEW-defect list
    (see its docstring for why the two differ).
    """
    vertex: int
    coords: tuple
    degree: int
    m: int
    v: int
    kawasaki_residual_deg: float
    arrangement_ok: bool

    @property
    def maekawa_defect(self) -> int:
        return abs(self.m - self.v)


@dataclass(frozen=True)
class AuditReport:
    closure_max_error: float
    closure_bad_edges: int
    vertices: tuple            # every interior vertex, audited
    kawasaki_tol_deg: float

    @property
    def interior_total(self) -> int:
        return len(self.vertices)

    @property
    def maekawa_violations(self) -> tuple:
        return tuple(va for va in self.vertices if va.maekawa_defect != 2)

    @property
    def kawasaki_violations(self) -> tuple:
        # `not (<=)`, not `>`: a NaN residual (poisoned geometry) must read as
        # a violation, exactly as lint_verdict's re-audit does. `>` is False
        # for NaN, which would let such a vertex out of BOTH this list and
        # arrangement_violations (whose "already blessed" test is `<=`).
        return tuple(va for va in self.vertices
                     if not (va.kawasaki_residual_deg
                             <= self.kawasaki_tol_deg))

    @property
    def arrangement_violations(self) -> tuple:
        """Vertices the NECESSARY conditions bless but the arrangement oracle
        rejects — the defect class this audit was blind to before 2.3.

        Vertices already listed by Maekawa/Kawasaki are excluded on purpose:
        every crimp removes one M and one V, so a reduction can only ever
        terminate at |M-V| = 2 with equal sectors, i.e. the oracle is stuck at
        EVERY parity/residual defect. Re-listing those would double-count the
        same broken vertex in the marker text, the ladder score and the 2.4
        capture rows. What is left here is exactly the new information.
        """
        return tuple(va for va in self.vertices
                     if not va.arrangement_ok
                     and va.maekawa_defect == 2
                     and va.kawasaki_residual_deg <= self.kawasaki_tol_deg)

    @property
    def clean(self) -> bool:
        return (self.closure_bad_edges == 0
                and not self.maekawa_violations
                and not self.kawasaki_violations
                and not self.arrangement_violations)

    def to_dict(self) -> dict:
        def _va(va):
            return {"vertex": va.vertex, "coords": list(va.coords),
                    "degree": va.degree, "m": va.m, "v": va.v,
                    "maekawa_defect": va.maekawa_defect,
                    "kawasaki_residual_deg": va.kawasaki_residual_deg,
                    "arrangement_ok": va.arrangement_ok}
        return {
            "closure_max_error": self.closure_max_error,
            "closure_bad_edges": self.closure_bad_edges,
            "interior_total": self.interior_total,
            "maekawa_violations": [_va(v) for v in self.maekawa_violations],
            "kawasaki_violations": [_va(v) for v in self.kawasaki_violations],
            "arrangement_violations": [_va(v)
                                       for v in self.arrangement_violations],
            "kawasaki_tol_deg": self.kawasaki_tol_deg,
            "clean": self.clean,
        }


def _geometry_frame(fold: dict) -> dict:
    """Top-level geometry, or file_frames[0] when nested (FOLD spec)."""
    if "vertices_coords" in fold and "edges_vertices" in fold:
        return fold
    frames = fold.get("file_frames")
    if (isinstance(frames, list) and frames
            and isinstance(frames[0], dict)
            and "vertices_coords" in frames[0]):
        return frames[0]
    return fold


def kawasaki_residual_deg(rays_deg: list) -> float:
    """|alternating sum of sorted angular sectors| in degrees; 0 = Kawasaki.

    Shared with lint_verdict's per-violation re-audit so the 2.1 verdict, the
    2.2 ladder audit, and this CLI apply ONE interior-defect definition.
    """
    rays = sorted(rays_deg)
    k = len(rays)
    if k < 2:
        return 0.0
    sectors = [(rays[(i + 1) % k] - rays[i]) % 360.0 for i in range(k)]
    return abs(sum(s * (1 if i % 2 == 0 else -1)
                   for i, s in enumerate(sectors)))


_kawasaki_residual_deg = kawasaki_residual_deg


def mv_arrangement_ok(sectors, asgs, eps=KAWASAKI_TOL_DEG) -> bool:
    """Single-vertex M/V-ARRANGEMENT check by greedy crimp reduction.

    Maekawa parity + Kawasaki residual are necessary but NOT sufficient for
    local flat-foldability: the big-little-big lemma also constrains WHERE the
    M/V labels sit (a strict-minimum sector flanked by two same-assignment
    creases can never fold flat — review-confirmed live: Oriedita reports
    these as LITTLE_BIG_LITTLE and the parity/residual-only re-audit blessed
    them benign, the one forbidden fail direction). sectors[i] is the angle
    between crease i and crease i+1 (cyclic); asgs[i] is crease i's M/V.
    Reduction: repeatedly crimp a locally-minimal sector whose two flanking
    creases differ, merging its neighbors; foldable iff the ring reduces to
    two equal-assignment creases with equal sectors. Greedy is sound in EXACT
    arithmetic, but the `eps` slack that admits near-tie minima also lets a
    pick-order stall a reduction that a different order would have completed
    (measured ~1/28,263 on deliberately near-tie rings) — CONSERVATIVE, not
    sound: the only observed fail direction is false-FAILED, never false-OK.
    From Stage 2.3 until the TreeMaker serve path was archived, that stall
    could also drive ladder pack SELECTION (server._search_first_clean gated
    on cp_audit.clean), pushing the ladder past a rung it should have served.

    Callers pass an ANGULAR ring, not an incidence list: see
    arrangement_ok_at_vertex, which owns that ordering step for both callers.
    """
    if len(sectors) < 2 or len(sectors) != len(asgs):
        return False
    # ring[j] = (crease j's assignment, the sector FOLLOWING crease j);
    # a crimp at sector j removes creases j and j+1 and folds sectors
    # j-1, j, j+1 into one of angle s[j-1] - s[j] + s[j+1].
    ring = list(zip(asgs, sectors))
    while len(ring) > 2:
        n = len(ring)
        pick = None
        for j in range(n):
            if ring[j][0] == ring[(j + 1) % n][0]:
                continue                      # equal flanks: crimp impossible
            if (ring[j][1] <= ring[(j - 1) % n][1] + eps
                    and ring[j][1] <= ring[(j + 1) % n][1] + eps):
                pick = j
                break
        if pick is None:
            return False                      # stuck: big-little-big violated
        a_prev = ring[(pick - 1) % n][0]
        merged = (ring[(pick - 1) % n][1] - ring[pick][1]
                  + ring[(pick + 1) % n][1])
        ring = [((a_prev, merged) if k == (pick - 1) % n else ring[k])
                for k in range(n) if k not in (pick, (pick + 1) % n)]
    if len(ring) != 2:                        # odd ring: defensive fail-safe
        return False
    (a0, s0), (a1, s1) = ring
    return a0 == a1 and abs(s0 - s1) <= eps


def arrangement_ok_at_vertex(rays_deg, assignments,
                             eps=KAWASAKI_TOL_DEG) -> bool:
    """mv_arrangement_ok for one vertex given rays in ANY order.

    The oracle needs the cyclic ring (crease, sector-after-crease); both
    callers hold rays in incidence order instead — cp_audit builds them from
    the edge list, lint_verdict from the same incidence map — so the
    sort-and-pair step belongs here, once, rather than being re-derived (and
    silently skipped) per call site. Sort key is the ray ONLY: coincident
    rays mean a zero sector regardless of pairing order (verdict-neutral over
    19,571 tie rings), and comparing `assignments` too would let a malformed
    FOLD (non-string/None assignment) raise TypeError on an ordinary tie.
    """
    order = sorted(zip(rays_deg, assignments), key=lambda t: t[0])
    n = len(order)
    if n < 2:
        return False                          # a lone crease cannot fold flat
    sectors = [(order[(j + 1) % n][0] - order[j][0]) % 360.0 for j in range(n)]
    return mv_arrangement_ok(sectors, [a for _, a in order], eps=eps)


def audit_fold(fold: dict, kawasaki_tol_deg: float = KAWASAKI_TOL_DEG
               ) -> AuditReport:
    """Audit one FOLD dict. Raises ValueError for structurally unusable input
    (missing geometry keys, empty arrays) — mirrors flat_fold's contract."""
    frame = _geometry_frame(fold)
    for key in ("vertices_coords", "edges_vertices", "edges_assignment"):
        if not frame.get(key):
            raise ValueError(f"fold is missing or has empty '{key}'")
    V = frame["vertices_coords"]
    EV = frame["edges_vertices"]
    EA = frame["edges_assignment"]
    if len(EV) != len(EA):
        raise ValueError("edges_vertices and edges_assignment lengths differ")

    # incidence over non-F edges only (F carries no fold constraint)
    inc: dict[int, list] = {}
    touches_border: set[int] = set()
    for (a, b), asg in zip(EV, EA):
        if asg == "F":
            continue
        inc.setdefault(a, []).append((b, asg))
        inc.setdefault(b, []).append((a, asg))
        if asg == "B":
            touches_border.add(a)
            touches_border.add(b)

    vertices = []
    for vi in sorted(inc):
        if vi in touches_border:
            continue
        nbrs = inc[vi]
        x0, y0 = V[vi][0], V[vi][1]
        rays = [math.degrees(math.atan2(V[nb][1] - y0, V[nb][0] - x0)) % 360.0
                for nb, _ in nbrs]
        vertices.append(VertexAudit(
            vertex=vi,
            coords=(x0, y0),
            degree=len(nbrs),
            m=sum(1 for _, a in nbrs if a == "M"),
            v=sum(1 for _, a in nbrs if a == "V"),
            kawasaki_residual_deg=_kawasaki_residual_deg(rays),
            # `rays` is INCIDENCE-ordered (edge-list order); the oracle's
            # helper sorts it into the angular ring before pairing. The
            # arrangement slack is clamped to the DEFAULT Kawasaki tolerance,
            # never the (possibly loosened) CLI one: forwarding
            # kawasaki_tol_deg straight through let a tol >= 0.1 deg bless
            # near-tie crimps and erase a REAL defect (crane v37) -- the
            # opposite of "protective".
            arrangement_ok=arrangement_ok_at_vertex(
                rays, [a for _, a in nbrs],
                eps=min(kawasaki_tol_deg, KAWASAKI_TOL_DEG)),
        ))

    closure = flat_fold(frame).closure
    return AuditReport(
        closure_max_error=closure.max_error,
        closure_bad_edges=len(closure.bad_edges),
        vertices=tuple(vertices),
        kawasaki_tol_deg=kawasaki_tol_deg,
    )


def _render(rep: AuditReport) -> str:
    lines = [
        f"closure: max error {rep.closure_max_error:.3e} "
        f"({rep.closure_bad_edges} bad edge(s) above {CLOSURE_EPS:.0e})",
        f"interior vertices: {rep.interior_total} "
        "(no incident B edge; hull-frontier vertices are boundary)",
    ]
    for va in rep.maekawa_violations:
        lines.append(
            f"  Maekawa v{va.vertex} ({va.coords[0]:.4f}, {va.coords[1]:.4f}):"
            f" M={va.m} V={va.v} |M-V|={va.maekawa_defect} (needs 2)")
    for va in rep.kawasaki_violations:
        lines.append(
            f"  Kawasaki v{va.vertex} ({va.coords[0]:.4f}, {va.coords[1]:.4f}):"
            f" residual {va.kawasaki_residual_deg:.4g} deg "
            f"(tol {rep.kawasaki_tol_deg:g})")
    for va in rep.arrangement_violations:
        # the necessary conditions PASS here -- say so, or the line reads as a
        # contradiction next to a Maekawa-clean vertex list.
        lines.append(
            f"  Arrangement v{va.vertex} ({va.coords[0]:.4f}, "
            f"{va.coords[1]:.4f}): M={va.m} V={va.v} |M-V|=2 and Kawasaki "
            f"{va.kawasaki_residual_deg:.4g} deg both PASS, but the M/V "
            "arrangement cannot fold flat (big-little-big)")
    lines.append("verdict: CLEAN" if rep.clean else
                 f"verdict: {len(rep.maekawa_violations)} Maekawa + "
                 f"{len(rep.kawasaki_violations)} Kawasaki + "
                 f"{len(rep.arrangement_violations)} M/V-arrangement interior "
                 f"violation(s), {rep.closure_bad_edges} bad closure edge(s)")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Interior-soundness audit of a RAW hull FOLD "
                    "(closure + interior Maekawa/Kawasaki/M-V arrangement).")
    ap.add_argument("fold_path")
    ap.add_argument("--json", action="store_true", dest="as_json",
                    help="machine-readable JSON instead of text")
    ap.add_argument("--kawasaki-tol-deg", type=float,
                    default=KAWASAKI_TOL_DEG)
    args = ap.parse_args(argv)

    try:
        with open(args.fold_path) as f:
            fold = json.load(f)
        rep = audit_fold(fold, kawasaki_tol_deg=args.kawasaki_tol_deg)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(rep.to_dict(), indent=1) if args.as_json
          else _render(rep))
    return 0 if rep.clean else 1


if __name__ == "__main__":
    sys.exit(main())
