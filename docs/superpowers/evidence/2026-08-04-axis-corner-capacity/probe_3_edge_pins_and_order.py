"""Round 3: two questions round 2 raised.

Q1. set_node_at is a TWO-equality pin (x AND y). set_node_on_x / set_node_on_y
    are ONE-equality pins -- "be somewhere on this edge" -- which is what Lang
    actually means by "force a leaf to a paper edge". Both ship bound with ZERO
    callers. Round 2 killed every paired tree with the 2-equality pin; does the
    1-equality pin survive where it did not?

Q2. Is the star-5 corner win (0.323556 -> 0.353553) a NEW lever, or just a
    basin re-roll the existing order/placement restarts already reach for free?
    If a plain node-order permutation finds 0.353553 unpinned, corner pinning
    buys nothing the ladder does not already have.
"""
import itertools, json, os, subprocess, sys

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
out = {"status": "?", "scale": None, "coverage": None, "corners": None,
       "onbnd": None, "err": None}
try:
    e = ht.HeadlessTreemaker()
    e.init_paper(1.0, 1.0)
    e.build_tree_from_json(json.dumps(d["nodes"]))
    for a, b in d.get("pairs") or []:
        e.apply_symmetry(int(a), int(b))
    for nid, axis, val in (d.get("edgepins") or []):
        if axis == "x":
            e.set_node_on_x(int(nid), float(val))
        else:
            e.set_node_on_y(int(nid), float(val))
    out["scale"] = e.run_scale_optimization()
    fold_str = e.build_and_export()
    out["status"] = "PACK"
    got = paper_coverage.hull_coverage(json.loads(fold_str))
    if got is not None:
        out["coverage"] = round(got["coverage"], 6)
    nc = nb = 0
    for p in e.leaf_node_locations():
        x, y = float(p[-2]), float(p[-1])
        ex = min(abs(x), abs(x - 1.0)) < 1e-6
        ey = min(abs(y), abs(y - 1.0)) < 1e-6
        nc += ex and ey
        nb += ex or ey
    out["corners"], out["onbnd"] = nc, nb
except Exception as exc:
    out["status"] = "FAIL"
    out["err"] = ("%%s: %%s" %% (type(exc).__name__, exc))[:110]
print("@@" + json.dumps(out))
""" % (HERE,)


def run(nodes, pairs=None, edgepins=None, timeout=300):
    payload = json.dumps({"nodes": nodes, "pairs": pairs or [],
                          "edgepins": edgepins or []})
    try:
        p = subprocess.run([sys.executable, "-c", CHILD], input=payload,
                           capture_output=True, text=True, timeout=timeout,
                           env={**os.environ, "PYTHONPATH": HERE})
    except subprocess.TimeoutExpired:
        return {"status": "TIMEO", "scale": None, "coverage": None,
                "corners": None, "onbnd": None, "err": "timeout"}
    for line in p.stdout.splitlines():
        if line.startswith("@@"):
            return json.loads(line[2:])
    return {"status": "CRASH", "scale": None, "coverage": None,
            "corners": None, "onbnd": None, "err": (p.stderr or "")[-110:]}


def fmt(v, w):
    return f"{v:{w}.6f}" if isinstance(v, float) else f"{'-':>{w}}"


ARMS = []

# --- Q1: one-equality EDGE pinning on the trees the 2-equality pin destroyed.
# For a pair (a,b) mirrored about y=x: a on x=1 (right edge) and b on y=1 (top
# edge) are mirror images of each other, so the pinning is symmetry-legal.
for name, case in [("QUADRUPED", cases.TEMPLATE_QUADRUPED),
                   ("BIRD", cases.TEMPLATE_BIRD),
                   ("HUMANOID", cases.TEMPLATE_HUMANOID),
                   ("INSECT", cases.TEMPLATE_INSECT)]:
    nodes, pairs = case
    ARMS.append((f"{name:9} free", nodes, pairs, []))
    a, b = pairs[0]
    ARMS.append((f"{name:9} pair0 edge x=1/y=1", nodes, pairs,
                 [(a, "x", 1.0), (b, "y", 1.0)]))
    ARMS.append((f"{name:9} pair0 edge x=0/y=0", nodes, pairs,
                 [(a, "x", 0.0), (b, "y", 0.0)]))
    if len(pairs) > 1:
        c, d = pairs[1]
        ARMS.append((f"{name:9} 2 pairs, all 4 edges", nodes, pairs,
                     [(a, "x", 1.0), (b, "y", 1.0),
                      (c, "x", 0.0), (d, "y", 0.0)]))

# --- Q1b: same one-equality pin on the unpaired stars, for comparison
for k in (5, 6, 7, 8):
    nodes = cases.star(k)[0]
    ARMS.append((f"star-{k}    free", nodes, [], []))
    ARMS.append((f"star-{k}    4 edges (1-eq)", nodes, [],
                 [(1, "x", 0.0), (2, "x", 1.0), (3, "y", 0.0), (4, "y", 1.0)]))

print(f"{'arm':36} {'st':5} {'scale':>9} {'cover':>9} {'cnr':>3} {'bnd':>3}")
print("-" * 70)
for label, nodes, pairs, ep in ARMS:
    r = run(nodes, pairs, ep)
    print(f"{label:36} {r['status'][:5]:5} {fmt(r['scale'], 9)} "
          f"{fmt(r['coverage'], 9)} "
          f"{(r['corners'] if r['corners'] is not None else '-'):>3} "
          f"{(r['onbnd'] if r['onbnd'] is not None else '-'):>3}"
          + (f"  {r['err']}" if r.get("err") else ""))

# --- Q2: does a plain node-ORDER permutation reach star-5's 0.353553 unpinned?
print("\nQ2  star-5 node-order restarts, NO pins "
      "(does the ladder already reach 0.353553?)")
base, _ = cases.star(5)
hub, leaves = base[0], base[1:]
best = None
for i, perm in enumerate(itertools.islice(itertools.permutations(leaves), 12)):
    r = run([hub] + list(perm), [], [])
    s = r["scale"] if isinstance(r["scale"], float) else float("nan")
    best = s if best is None or (s == s and s > best) else best
    print(f"  order#{i:<2} {r['status'][:5]:5} {fmt(r['scale'], 9)} "
          f"{fmt(r['coverage'], 9)}")
print(f"  best unpinned scale over 12 orders: {best:.6f}   "
      f"(4-corner-pinned reference: 0.353553)")
