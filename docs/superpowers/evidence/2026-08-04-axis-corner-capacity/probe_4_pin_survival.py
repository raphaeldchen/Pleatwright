"""Does ProjectActivePaths drop a boundary pin? (Slice 0 Phase A Q4, never run.)

The old spec asserts R8: the projection carries active-path rows and symmetry
rows and NOTHING ELSE, so a leaf ALM placed exactly on the boundary is free to
be moved off it -- and Combo's equalities are exact, so any displacement
violates them. That was inferred from reading the routine, never measured.

It gates S4c. Measure it directly: read leaf coords AFTER the optimizer (the
projection has not run yet) and AGAIN after build_and_export (which calls
ProjectActivePaths internally), and report the displacement of the PINNED
coordinate specifically.
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

d = json.loads(sys.stdin.read())
out = {"status": "?", "pre": None, "post": None, "iters": None, "err": None}


def locs(e):
    return {int(p[0]): (float(p[-2]), float(p[-1]))
            for p in e.leaf_node_locations()}

try:
    e = ht.HeadlessTreemaker()
    e.init_paper(1.0, 1.0)
    e.build_tree_from_json(json.dumps(d["nodes"]))
    for a, b in d.get("pairs") or []:
        e.apply_symmetry(int(a), int(b))
    for nid, axis, val in (d.get("pins") or []):
        if axis == "x":
            e.set_node_on_x(int(nid), float(val))
        elif axis == "y":
            e.set_node_on_y(int(nid), float(val))
        else:
            e.set_node_at(int(nid), float(val[0]), float(val[1]))
    e.run_scale_optimization()
    out["pre"] = {str(k): v for k, v in locs(e).items()}   # PRE-projection
    e.build_and_export()                                    # runs the projection
    out["post"] = {str(k): v for k, v in locs(e).items()}   # POST-projection
    out["status"] = "PACK"
except Exception as exc:
    out["status"] = "FAIL"
    out["err"] = ("%%s: %%s" %% (type(exc).__name__, exc))[:110]
print("@@" + json.dumps(out))
""" % (HERE,)


def run(nodes, pairs, pins, timeout=300):
    payload = json.dumps({"nodes": nodes, "pairs": pairs, "pins": pins})
    try:
        p = subprocess.run([sys.executable, "-c", CHILD], input=payload,
                           capture_output=True, text=True, timeout=timeout,
                           env={**os.environ, "PYTHONPATH": HERE})
    except subprocess.TimeoutExpired:
        return {"status": "TIMEO", "pre": None, "post": None, "err": "timeout"}
    for line in p.stdout.splitlines():
        if line.startswith("@@"):
            return json.loads(line[2:])
    return {"status": "CRASH", "pre": None, "post": None,
            "err": (p.stderr or "")[-110:]}


ARMS = [
    # (label, nodes, pairs, pins)  pins: (node_id, "x"|"y"|"at", value)
    ("star-5  4 corners (2-eq)", cases.star(5)[0], [],
     [(1, "at", (0.0, 0.0)), (2, "at", (1.0, 0.0)),
      (3, "at", (1.0, 1.0)), (4, "at", (0.0, 1.0))]),
    ("star-6  1 corner (2-eq)", cases.star(6)[0], [],
     [(1, "at", (0.0, 0.0))]),
    ("star-6  4 edges (1-eq)", cases.star(6)[0], [],
     [(1, "x", 0.0), (2, "x", 1.0), (3, "y", 0.0), (4, "y", 1.0)]),
    ("star-7  4 edges (1-eq)", cases.star(7)[0], [],
     [(1, "x", 0.0), (2, "x", 1.0), (3, "y", 0.0), (4, "y", 1.0)]),
    ("HUMANOID 4 edges (1-eq)", cases.TEMPLATE_HUMANOID[0],
     cases.TEMPLATE_HUMANOID[1],
     [(3, "x", 1.0), (4, "y", 1.0), (6, "x", 0.0), (7, "y", 0.0)]),
    ("QUADRUPED pair0 edge x=0/y=0", cases.TEMPLATE_QUADRUPED[0],
     cases.TEMPLATE_QUADRUPED[1], [(3, "x", 0.0), (4, "y", 0.0)]),
    ("BIRD    pair0 edge x=0/y=0", cases.TEMPLATE_BIRD[0],
     cases.TEMPLATE_BIRD[1], [(3, "x", 0.0), (4, "y", 0.0)]),
]

print("displacement of the PINNED coordinate, optimizer -> post-projection")
print(f"{'arm':30} {'st':5} {'node':>5} {'ax':>3} {'want':>6} "
      f"{'pre':>12} {'post':>12} {'|move|':>10}")
print("-" * 92)
for label, nodes, pairs, pins in ARMS:
    r = run(nodes, pairs, pins)
    if r["status"] != "PACK":
        print(f"{label:30} {r['status'][:5]:5}   {r.get('err', '')}")
        continue
    worst = 0.0
    for nid, axis, val in pins:
        k = str(nid)
        pre, post = r["pre"].get(k), r["post"].get(k)
        if pre is None or post is None:
            print(f"{label:30} {'PACK':5} {nid:>5} {axis:>3} "
                  f"{'?':>6} {'NOT A LEAF IN READBACK':>26}")
            continue
        for ax, want in ((("x", val),) if axis == "x" else
                         (("y", val),) if axis == "y" else
                         (("x", val[0]), ("y", val[1]))):
            j = 0 if ax == "x" else 1
            mv = abs(post[j] - want)
            worst = max(worst, mv)
            print(f"{label:30} {'PACK':5} {nid:>5} {ax:>3} {want:6.3f} "
                  f"{pre[j]:12.9f} {post[j]:12.9f} {mv:10.2e}")
    print(f"{'':30} {'':5} {'worst |post - requested|':>40}  {worst:10.2e}\n")
