"""Throwaway planner-side check of the CLAUDE.md 1.1(2) premise.

NOT the committed 0-alpha probe -- this only re-derives the headline numbers
the restatement leans on, so the spec cites something I observed rather than
something I was told. Isolated child per arm (the engine can SIGSEGV).
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
       "n_corner": None, "locs": None, "err": None}
try:
    e = ht.HeadlessTreemaker()
    e.init_paper(1.0, 1.0)
    e.build_tree_from_json(json.dumps(d["nodes"]))
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
    locs = e.leaf_node_locations()
    out["locs"] = [[round(float(v), 4) for v in p[-2:]] for p in locs] \
        if locs and not isinstance(locs[0], (int, float)) else str(locs)[:200]
except Exception as exc:
    out["status"] = "FAIL"
    out["err"] = ("%%s: %%s" %% (type(exc).__name__, exc))[:160]
print("@@" + json.dumps(out))
""" % (HERE,)


def run(nodes, pairs=None, pins=None, timeout=300):
    payload = json.dumps({"nodes": nodes, "pairs": pairs or [],
                          "pins": pins or []})
    p = subprocess.run([sys.executable, "-c", CHILD], input=payload,
                       capture_output=True, text=True, timeout=timeout,
                       env={**os.environ, "PYTHONPATH": HERE})
    for line in p.stdout.splitlines():
        if line.startswith("@@"):
            return json.loads(line[2:])
    return {"status": "CRASH rc=%d" % p.returncode, "scale": None,
            "coverage": None, "bbox": None,
            "err": (p.stderr or "")[-160:]}


CORNERS = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]

star4_nodes, _ = cases.star(4)
ARMS = [
    ("star-4 unconstrained", star4_nodes, [], []),
    ("star-4 4 corners pinned", star4_nodes, [],
     [(i + 1, CORNERS[i]) for i in range(4)]),
    ("star-4 1 corner pinned", star4_nodes, [], [(1, CORNERS[0])]),
    ("star-5 unconstrained", cases.star(5)[0], [], []),
    ("star-5 4 corners pinned", cases.star(5)[0], [],
     [(i + 1, CORNERS[i]) for i in range(4)]),
    ("TEMPLATE_HUMANOID unconstrained",
     cases.TEMPLATE_HUMANOID[0], cases.TEMPLATE_HUMANOID[1], []),
    ("TEMPLATE_QUADRUPED unconstrained",
     cases.TEMPLATE_QUADRUPED[0], cases.TEMPLATE_QUADRUPED[1], []),
    ("TEMPLATE_BIRD unconstrained",
     cases.TEMPLATE_BIRD[0], cases.TEMPLATE_BIRD[1], []),
    ("TEMPLATE_INSECT unconstrained",
     cases.TEMPLATE_INSECT[0], cases.TEMPLATE_INSECT[1], []),
]

print(f"{'arm':38} {'status':6} {'scale':>10} {'coverage':>10} {'bbox':>9}")
for label, nodes, pairs, pins in ARMS:
    r = run(nodes, pairs, pins)
    print(f"{label:38} {r['status']:6} "
          f"{(r['scale'] if r['scale'] is not None else float('nan')):10.6f} "
          f"{(r['coverage'] if r['coverage'] is not None else float('nan')):10.6f} "
          f"{(r['bbox'] if r['bbox'] is not None else float('nan')):9.6f}"
          + (f"   {r['err']}" if r.get('err') else ""))
