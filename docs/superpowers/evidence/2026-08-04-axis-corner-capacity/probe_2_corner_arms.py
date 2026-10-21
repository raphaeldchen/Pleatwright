"""Round 2: is the star-5 corner win real, general, or a basin lottery?

Round 1 found star-5 4-corner-pinned at scale 0.353553 / coverage 1.000000
versus unconstrained 0.323556 / 0.703897 -- both axes UP, and those are Lang's
own 0.323 / 0.353 numbers with the labels reversed from how the record reads
them. Round 2 tests generality (k sweep), dose-response (1..4 corners), the
brief's actual star-4 case (PAIRED, which round 1 did not build), and the
production templates.
"""
import json, os, subprocess, sys

HERE = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "..", "..", "mcp_harness"))
sys.path.insert(0, os.path.join(HERE, "tests"))
import cases  # noqa: E402

CHILD = r"""
import json, sys
sys.path.insert(0, %r)
import headless_treemaker as ht
import paper_coverage

d = json.loads(sys.stdin.read())
out = {"status": "?", "scale": None, "coverage": None, "bbox": None,
       "corners": None, "err": None}
try:
    e = ht.HeadlessTreemaker()
    e.init_paper(1.0, 1.0)
    e.build_tree_from_json(json.dumps(d["nodes"]))
    if d.get("angle") is not None:
        e.set_symmetry_angle(float(d["angle"]))
    for a, b in d.get("pairs") or []:
        e.apply_symmetry(int(a), int(b))
    for nid, (x, y) in (d.get("pins") or []):
        e.set_node_at(int(nid), float(x), float(y))
    out["scale"] = e.run_scale_optimization()
    fold_str = e.build_and_export()
    out["status"] = "PACK"
    got = paper_coverage.hull_coverage(json.loads(fold_str))
    if got is not None:
        out["coverage"] = round(got["coverage"], 6)
        out["bbox"] = round(got["bbox_area"], 6)
    # corner occupancy: leaves within 1e-6 of a paper corner
    locs = e.leaf_node_locations()
    n = 0
    for p in locs:
        x, y = float(p[-2]), float(p[-1])
        if min(abs(x), abs(x - 1.0)) < 1e-6 and min(abs(y), abs(y - 1.0)) < 1e-6:
            n += 1
    out["corners"] = n
except Exception as exc:
    out["status"] = "FAIL"
    out["err"] = ("%%s: %%s" %% (type(exc).__name__, exc))[:120]
print("@@" + json.dumps(out))
""" % (HERE,)


def run(nodes, pairs=None, pins=None, angle=None, timeout=300):
    payload = json.dumps({"nodes": nodes, "pairs": pairs or [],
                          "pins": pins or [], "angle": angle})
    try:
        p = subprocess.run([sys.executable, "-c", CHILD], input=payload,
                           capture_output=True, text=True, timeout=timeout,
                           env={**os.environ, "PYTHONPATH": HERE})
    except subprocess.TimeoutExpired:
        return {"status": "TIMEO", "scale": None, "coverage": None,
                "bbox": None, "corners": None, "err": "timeout"}
    for line in p.stdout.splitlines():
        if line.startswith("@@"):
            return json.loads(line[2:])
    return {"status": "CRASH", "scale": None, "coverage": None, "bbox": None,
            "corners": None, "err": (p.stderr or "")[-120:]}


C = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
ARMS = []

# -- the brief's actual star-4 case: PAIRED (round 1 built the unpaired star)
s4p_nodes, s4p_pairs = cases.symmetric_pairs_star(4)
ARMS += [("star-4-sym  free", s4p_nodes, s4p_pairs, [], None),
         # (1,0) and (0,1) are mirror images about y=x; a legal pair pinning
         ("star-4-sym  pair->(1,0)/(0,1)", s4p_nodes, s4p_pairs,
          [(1, C[1]), (2, C[3])], None),
         ("star-4-sym  4 corners", s4p_nodes, s4p_pairs,
          [(i + 1, C[i]) for i in range(4)], None)]

# -- dose-response and k sweep on the equal-flap stars
for k in (5, 6, 7, 8):
    nodes = cases.star(k)[0]
    ARMS.append((f"star-{k}     free", nodes, [], [], None))
    for nc in (1, 2, 4):
        ARMS.append((f"star-{k}     {nc} corner(s)", nodes, [],
                     [(i + 1, C[i]) for i in range(nc)], None))

# -- determinism re-run of the round-1 winner
ARMS.append(("star-5     4 corners (rerun)", cases.star(5)[0], [],
             [(i + 1, C[i]) for i in range(4)], None))

# -- production templates: free, then the legal mirror-pair corner pinning
for name, case in [("QUADRUPED", cases.TEMPLATE_QUADRUPED),
                   ("BIRD", cases.TEMPLATE_BIRD),
                   ("HUMANOID", cases.TEMPLATE_HUMANOID),
                   ("INSECT", cases.TEMPLATE_INSECT)]:
    nodes, pairs = case
    ARMS.append((f"{name:9}  free", nodes, pairs, [], None))
    a, b = pairs[0]
    ARMS.append((f"{name:9}  pair0->(1,0)/(0,1)", nodes, pairs,
                 [(a, C[1]), (b, C[3])], None))
    if len(pairs) > 1:
        c, d = pairs[1]
        ARMS.append((f"{name:9}  2 pairs->4 corners", nodes, pairs,
                     [(a, C[1]), (b, C[3]), (c, C[0]), (d, C[2])], None))

hdr = f"{'arm':34} {'st':5} {'scale':>9} {'cover':>9} {'bbox':>8} {'cnr':>3}"
print(hdr)
print("-" * len(hdr))
def fmt(v, w):
    return f"{v:{w}.6f}" if isinstance(v, float) else f"{'-':>{w}}"


for label, nodes, pairs, pins, angle in ARMS:
    r = run(nodes, pairs, pins, angle)
    cnr = r["corners"] if r["corners"] is not None else "-"
    print(f"{label:34} {r['status'][:5]:5} {fmt(r['scale'], 9)} "
          f"{fmt(r['coverage'], 9)} {fmt(r['bbox'], 8)} {cnr:>3}"
          + (f"  {r['err']}" if r.get("err") else ""))
