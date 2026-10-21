"""S2'b measurement harness -- produces every number in the report."""
import json
import os
import random
import sys

_H = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "mcp_harness")
sys.path.insert(0, _H)
sys.path.insert(0, os.path.join(_H, "tests"))

import cp_audit          # noqa: E402
import cp_mirror         # noqa: E402
import flat_fold         # noqa: E402
import mv_repair         # noqa: E402
import mv_symmetrize     # noqa: E402

FIX = os.path.join(_H, "tests", "fixtures", "mv_symmetrize")
NAMES = ["mesh-humanoid__seeded_1", "mesh-bird__seeded_3",
         "template-bird__CONTROL", "template-quadruped__CONTROL",
         "mesh-insect__CONTROL"]
LINT = os.environ.get("LINT", "0") == "1"


def load(n):
    with open(os.path.join(FIX, n + ".fold")) as fh:
        return json.load(fh)


print("=" * 78)
print("1. SPACE-SIZE ASSERTION  -- every enumerated point must be symmetric")
print("=" * 78)
print(f"{'subject':32s} {'orbits(sw/pr/fx)':18s} {'space':>12s} "
      f"{'walked':>8s} {'symmetric':>10s}  mode")
for name in NAMES:
    fold = load(name)
    sp = mv_symmetrize.orbit_space(fold)
    n = len(sp.orbits)
    if sp.size <= 8192:
        pts, mode = list(sp.flip_sets()), "EXHAUSTIVE"
        assert len(pts) == sp.size and len(set(pts)) == sp.size
    else:
        rng = random.Random(20260807)
        ch = [tuple(rng.randrange(2) for _ in sp.orbits) for _ in range(2046)]
        ch += [(0,) * n, (1,) * n]
        pts, mode = [sp.flips_for(c) for c in ch], "SAMPLED(2048)"
    ok = sum(1 for f in pts
             if cp_mirror.mirror_verdict(mv_repair.apply_flips(fold, f),
                                         axis_degrees=45.0)["symmetric"])
    flag = "OK" if ok == len(pts) else "*** FAIL ***"
    print(f"{name:32s} {n:2d} ({sp.n_swapped}/{sp.n_preserved}/{sp.n_fixed})"
          f"{'':7s} 2^{n:<10d} {len(pts):8d} {ok:10d}  {mode} {flag}")
    assert sp.size == 1 << n, "space is not exactly 2**n"

print()
print("=" * 78)
print("2. TARGET COUNTS, WITH INTERMEDIATES")
print("=" * 78)
print(f"{'subject':32s} {'space':>12s} {'maekawa':>8s} {'audit':>7s} "
      f"{'layer':>6s} {'lint':>5s} {'nodes':>9s} {'s':>7s} {'mism':>5s}")
results = {}
for name in NAMES:
    fold = load(name)
    r = mv_symmetrize.search(fold, lint=LINT, verify_slow_path=True,
                             deadline_s=3600)
    results[name] = r
    print(f"{name:32s} 2^{len(r.space.orbits):<10d} "
          f"{r.n_maekawa_clean:8d} {r.n_audit_clean:7d} "
          f"{r.n_layer_consistent:6d} "
          f"{(r.n_lint_ok if LINT else '-'):>5} {r.nodes:9d} "
          f"{r.elapsed_s:7.2f} {r.slow_path_mismatches:5d}"
          f"{'' if r.exhausted else '  NOT EXHAUSTED'}")
    for note in r.notes:
        print(f"{'':34s} note: {note}")

print()
print("=" * 78)
print("3. REQUIRED-FAIL INPUT -- template-quadruped flips {17, 27}")
print("=" * 78)
fold = load("template-quadruped__CONTROL")
cand = mv_repair.apply_flips(fold, (17, 27))
v = cp_mirror.mirror_verdict(cand, axis_degrees=45.0)
rep = cp_audit.audit_fold(cand)
g = mv_symmetrize.gate(fold, (17, 27))
print(f"  conjunct 1  mirror_verdict.symmetric = {v['symmetric']}   "
      f"(mv_swapped {v['mv_swapped']}, mv_mismatched {v['mv_mismatched']})")
print(f"  conjunct 2  cp_audit.clean           = {rep.clean}  "
      f"<-- maekawa {len(rep.maekawa_violations)}, "
      f"kawasaki {len(rep.kawasaki_violations)}, "
      f"arrangement {len(rep.arrangement_violations)}")
print(f"  conjunct 3  layer_order              = "
      f"{mv_repair._layer_status(cand)}")
print(f"  GATE VERDICT                         = "
      f"{'PASSED' if g.passed else 'REJECTED'}")
for va in rep.maekawa_violations:
    print(f"    maekawa offender: vertex {va.vertex} degree {va.degree} "
          f"M={va.m} V={va.v} |M-V|={va.maekawa_defect} (Maekawa wants 2)")

print()
print("=" * 78)
print("4. BASE INVARIANCE -- bit-identical, on every surviving candidate")
print("=" * 78)
for name in NAMES:
    r = results[name]
    if not r.candidates:
        print(f"{name:32s} no candidate to check")
        continue
    fold = load(name)
    b = flat_fold.flat_fold(cp_audit._geometry_frame(fold))
    bad = 0
    for c in r.candidates:
        a = flat_fold.flat_fold(cp_audit._geometry_frame(
            mv_repair.apply_flips(fold, c.flips)))
        same = (a.faces == b.faces
                and [t.tobytes() for t in a.transforms]
                == [t.tobytes() for t in b.transforms]
                and [x.tobytes() for x in a.folded_vertices]
                == [x.tobytes() for x in b.folded_vertices]
                and a.closure.max_error == b.closure.max_error
                and a.closure.bad_edges == b.closure.bad_edges)
        bad += (not same)
    print(f"{name:32s} {len(r.candidates)} candidate(s), faces {len(b.faces)}, "
          f"closure {b.closure.max_error:.3e}  ->  "
          f"{'ALL BIT-IDENTICAL' if not bad else f'{bad} MOVED ***'}")

print()
print("=" * 78)
print("5. THE RANKED WINNER PER SUBJECT")
print("=" * 78)
for name in NAMES:
    r = results[name]
    if r.winner is None:
        print(f"{name:32s} NO TARGET  (audit {r.n_audit_clean} -> "
              f"layer {r.n_layer_consistent})")
        continue
    w = r.winner
    weights = sorted(c.weight for c in r.candidates)
    print(f"{name:32s} weight {w.weight}  lint_rank "
          f"{w.lint_rank if w.lint_rank is not None else '-'}  "
          f"(base {r.base_lint_rank if r.base_lint_rank is not None else '-'})"
          f"  weights {weights}")
    print(f"{'':34s} flips {list(w.flips)}")
    if r.rejected_by_lint:
        print(f"{'':34s} dropped by conjunct 4: "
              f"{[list(c.flips) for c in r.rejected_by_lint]}")

print()
print("=" * 78)
print("6. M/V CENSUS -- how much of the pattern the winner relabels")
print("=" * 78)
for name in NAMES:
    r = results[name]
    if r.winner is None:
        continue
    fold = load(name)
    fr = cp_audit._geometry_frame(fold)
    ea = fr["edges_assignment"]
    out = cp_audit._geometry_frame(
        mv_repair.apply_flips(fold, r.winner.flips))["edges_assignment"]
    mv = sum(1 for a in ea if a in "MV")
    print(f"{name:32s} M{ea.count('M')}/V{ea.count('V')} -> "
          f"M{out.count('M')}/V{out.count('V')}   "
          f"{r.winner.weight} of {mv} M/V creases "
          f"({100.0 * r.winner.weight / mv:.1f}%), "
          f"{len(ea)} edges total")
