"""Does the symmetry AXIS set a structural ceiling on corner occupancy?

Claim to test: a paired leaf can only take a corner whose mirror image is also
a corner. About the DIAGONAL (45), (1,0)<->(0,1) is such a pair but (0,0) and
(1,1) lie ON the axis -- usable by unpaired axial leaves only. So a diagonal
tree has TWO pairable corners. About BOOK (0), the mirror is horizontal:
(0,0)<->(0,1) and (1,0)<->(1,1), so ALL FOUR corners are pairable.

If true, the 8-of-8 corner failures on the production templates are not a
property of corner pinning -- they are a property of pinning more corners than
the DIAGONAL axis can supply, and the remedy is the axis, not the policy.

Measured AT THE OPTIMIZER ONLY -- run_scale_optimization then read locations,
never build_and_export -- because the projection re-symmetrizes about y=x
regardless of angle and destroys or silently corrupts every non-45 build (the
49-cell sweep). Coverage is therefore the LEAF-HULL area, computed here, not
paper_coverage's exported-fold reading.
"""
import json, os, subprocess, sys

HERE = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..", "..", "mcp_harness"))
sys.path.insert(0, os.path.join(HERE, "tests"))
sys.path.insert(0, HERE)
import cases            # noqa: E402
import paper_coverage   # noqa: E402  (reuse _hull/_area, not hull_coverage)

CHILD = r"""
import json, sys
sys.path.insert(0, %r)
import headless_treemaker as ht

d = json.loads(sys.stdin.read())
out = {"status": "?", "scale": None, "locs": None, "err": None}
try:
    e = ht.HeadlessTreemaker()
    e.init_paper(1.0, 1.0)
    e.build_tree_from_json(json.dumps(d["nodes"]))
    if d.get("angle") is not None:
        e.set_symmetry_angle(float(d["angle"]))
    for a, b in d.get("pairs") or []:
        e.apply_symmetry(int(a), int(b))
    for nid, x, y in (d.get("pins") or []):
        e.set_node_at(int(nid), float(x), float(y))
    out["scale"] = e.run_scale_optimization()
    out["locs"] = [[float(p[-2]), float(p[-1])] for p in e.leaf_node_locations()]
    out["status"] = "OPT"          # optimizer only; projection never runs
except Exception as exc:
    out["status"] = "FAIL"
    out["err"] = ("%%s: %%s" %% (type(exc).__name__, exc))[:100]
print("@@" + json.dumps(out))
""" % (HERE,)


def run(nodes, pairs, pins, angle, timeout=300):
    payload = json.dumps({"nodes": nodes, "pairs": pairs, "pins": pins,
                          "angle": angle})
    try:
        p = subprocess.run([sys.executable, "-c", CHILD], input=payload,
                           capture_output=True, text=True, timeout=timeout,
                           env={**os.environ, "PYTHONPATH": HERE})
    except subprocess.TimeoutExpired:
        return {"status": "TIMEO", "scale": None, "locs": None,
                "err": "timeout"}
    for line in p.stdout.splitlines():
        if line.startswith("@@"):
            return json.loads(line[2:])
    return {"status": "CRASH", "scale": None, "locs": None,
            "err": (p.stderr or "")[-100:]}


def summarize(locs):
    """(leaf-hull area, corners occupied, leaves on boundary)."""
    pts = [(x, y) for x, y in locs]
    area = paper_coverage._area(paper_coverage._hull(pts))
    nc = nb = 0
    for x, y in pts:
        ex = min(abs(x), abs(x - 1.0)) < 1e-6
        ey = min(abs(y), abs(y - 1.0)) < 1e-6
        nc += ex and ey
        nb += ex or ey
    return area, nc, nb


# Diagonal-axis corner classes: (1,0)<->(0,1) mirror pair; (0,0),(1,1) on axis.
# Book-axis corner classes: (0,0)<->(0,1) and (1,0)<->(1,1) -- two mirror pairs.
DIAG_PAIR = [(1.0, 0.0), (0.0, 1.0)]
BOOK_PAIR_A = [(0.0, 0.0), (0.0, 1.0)]
BOOK_PAIR_B = [(1.0, 0.0), (1.0, 1.0)]

SUBJECTS = [("star-4-sym", cases.symmetric_pairs_star(4)),
            ("QUADRUPED", cases.TEMPLATE_QUADRUPED),
            ("BIRD", cases.TEMPLATE_BIRD),
            ("HUMANOID", cases.TEMPLATE_HUMANOID),
            ("INSECT", cases.TEMPLATE_INSECT)]

ARMS = []
for name, (nodes, pairs) in SUBJECTS:
    p0, p1 = pairs[0], (pairs[1] if len(pairs) > 1 else None)
    ARMS.append((f"{name:10} diag45  free", nodes, pairs, [], 45.0))
    ARMS.append((f"{name:10} book0   free", nodes, pairs, [], 0.0))
    # ONE pair to the axis's legal corner pair
    ARMS.append((f"{name:10} diag45  1 pair->2 corners", nodes, pairs,
                 [(p0[0], *DIAG_PAIR[0]), (p0[1], *DIAG_PAIR[1])], 45.0))
    ARMS.append((f"{name:10} book0   1 pair->2 corners", nodes, pairs,
                 [(p0[0], *BOOK_PAIR_A[0]), (p0[1], *BOOK_PAIR_A[1])], 0.0))
    if p1:
        # TWO pairs -> 4 corners. Only book supplies four pairable corners.
        ARMS.append((f"{name:10} diag45  2 pairs->4 corners", nodes, pairs,
                     [(p0[0], 1.0, 0.0), (p0[1], 0.0, 1.0),
                      (p1[0], 0.0, 0.0), (p1[1], 1.0, 1.0)], 45.0))
        ARMS.append((f"{name:10} book0   2 pairs->4 corners", nodes, pairs,
                     [(p0[0], *BOOK_PAIR_A[0]), (p0[1], *BOOK_PAIR_A[1]),
                      (p1[0], *BOOK_PAIR_B[0]), (p1[1], *BOOK_PAIR_B[1])], 0.0))

print("AT THE OPTIMIZER ONLY (build_and_export never called)")
print(f"{'arm':40} {'st':5} {'scale':>9} {'leafhull':>9} {'cnr':>3} {'bnd':>3}")
print("-" * 76)
for label, nodes, pairs, pins, angle in ARMS:
    r = run(nodes, pairs, pins, angle)
    if r["status"] != "OPT":
        print(f"{label:40} {r['status'][:5]:5} "
              f"{'-':>9} {'-':>9} {'-':>3} {'-':>3}  {r.get('err', '')}")
        continue
    area, nc, nb = summarize(r["locs"])
    print(f"{label:40} {'OPT':5} {r['scale']:9.6f} {area:9.6f} "
          f"{nc:3d} {nb:3d}")
