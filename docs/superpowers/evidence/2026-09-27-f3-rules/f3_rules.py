"""Do F.3's rules determine our ridge variables? Measured, rule-by-rule.

F.3: "Y-shape anchors; X-shape same, parallel opposite, perpendicular same"
(recorded in `../../specs/2026-09-24-dense-pleats-design.md` section 3).

`../2026-09-27-f3-anchors/` established that ANCHORS are adequate: the ridge
graph has 1-2 components and reach is 100% on five of eight subjects. It also
established that the remaining two rules cannot be applied at PIECE level -- at a
degree-2 vertex the two ridge pieces are collinear, so "parallel opposite" would
alternate M/V along one straight ridge. So the rules must act on VARIABLES, and
this script tests whether they can.

THREE THINGS MEASURED, in increasing order of how badly each would kill F.3:

1. ORIENTATION COHERENCE OF A VARIABLE. `assign` mirror-merges a ridge with its
   mirror-image partner into ONE variable, and a diagonal ridge's mirror runs the
   OTHER diagonal. If merged variables routinely span two orientation classes,
   then "parallel" and "perpendicular" are not even well defined between
   variables, and F.3's rules cannot be stated at this level at all. Reported as
   `vars_spanning_multiple_orientations`.

2. RULE COVERAGE. Two ridge variables meeting at a vertex can be parallel,
   perpendicular, or OBLIQUE (45 degrees apart -- e.g. an axis-aligned ridge
   against a diagonal one). F.3 says nothing about an oblique pair, so every
   such pair is a relationship the rules do not govern. Reported as
   `pairs_oblique`.

3. CONSISTENCY. "Parallel opposite, perpendicular same" is a set of binary
   constraints -- differ / agree -- so the system is satisfiable iff no cycle
   carries an odd number of "differ" edges. That is a parity problem, the same
   shape as `interleave`'s 2-colouring and `layer_certify.collapse`'s parity
   quotient. Checked with a parity union-find; a conflict means F.3's rules
   CONTRADICT each other on our geometry regardless of where anchors sit.

Measured on a SPARSE assign: ridge variables exist in both labelling modes and
`var_of` does not depend on `dense`, so this stays cheap and reaches every
subject. `var_of` is read from production via the in-memory patch technique
(`../2026-09-26-gap1-phase0/phase0.py` established it): patch, verify the diff
touches only what we intended, import -- never a committed fork.

Run from mcp_harness:
  PYTHONPATH=. ../.venv/bin/python3 -u \
      ../docs/superpowers/evidence/2026-09-27-f3-rules/f3_rules.py \
      ../docs/superpowers/evidence/2026-09-27-f3-rules/f3-rules.json
"""
import collections
import difflib
import importlib.util
import itertools
import json
import math
import os
import pathlib
import sys
import time

from box_pleat.compile import compile_tree

OUT = sys.argv[1]
RULE6 = os.path.join("..", "docs", "superpowers", "evidence",
                     "2026-09-08-vlm-tree-authoring", "data", "rule6_serve.json")
ORDER = ["starfish", "lizard", "frog", "horse", "bird", "guinea_pig",
         "octopus", "dog"]
ASSIGN_SRC = pathlib.Path("box_pleat/assign.py")

_ORIG = """    nodes = budget
    frames: list = []          # [variable, value order, next value index]
"""
_PATCHED = """    _PROBE["var_of"] = dict(var_of)
    nodes = budget
    frames: list = []          # [variable, value order, next value index]
"""
_FOOTER = "\n\n_PROBE = {}\n"


def build_instrumented():
    src = ASSIGN_SRC.read_text()
    if src.count(_ORIG) != 1:
        raise SystemExit("REFUSING TO MEASURE: assign.py's DFS setup no longer "
                         "matches this script's expected text exactly once.")
    patched = src.replace(_ORIG, _PATCHED) + _FOOTER
    removed = [l[1:] for l in difflib.unified_diff(
        src.splitlines(), patched.splitlines(), lineterm="", n=0)
        if l.startswith("-") and not l.startswith("---")]
    if removed:
        raise SystemExit(f"REFUSING TO MEASURE: patch removed lines: {removed}")
    out = pathlib.Path(os.environ.get("TMPDIR", "/tmp")) / "_assign_f3.py"
    out.write_text(patched)
    import box_pleat  # noqa: F401 - needed in sys.modules for relative imports
    name = "box_pleat._assign_f3"
    spec = importlib.util.spec_from_file_location(name, out)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def direction_class(p):
    """The piece's undirected direction, reduced: (1,0) (0,1) (1,1) or (1,-1).

    `d` and `-d` are the same class, so the representative is normalised to a
    positive leading component.
    """
    dx, dy = p.b[0] - p.a[0], p.b[1] - p.a[1]
    g = math.gcd(abs(dx), abs(dy)) or 1
    dx, dy = dx // g, dy // g
    if (dx, dy) < (0, 0) or (dx == 0 and dy < 0) or dx < 0:
        dx, dy = -dx, -dy
    return (dx, dy)


def relation(c1, c2):
    """"parallel", "perpendicular", or "oblique" for two direction classes."""
    if c1 == c2:
        return "parallel"
    if c1[0] * c2[0] + c1[1] * c2[1] == 0:
        return "perpendicular"
    return "oblique"


class ParityDSU:
    """Union-find carrying a parity bit: `same` or `differ` per edge.

    `union(a, b, differ)` returns False when the edge CONTRADICTS what is
    already known, which is exactly an odd-parity cycle.
    """

    def __init__(self):
        self.parent = {}
        self.par = {}

    def find(self, x):
        if x not in self.parent:
            self.parent[x] = x
            self.par[x] = 0
            return x, 0
        root, acc = x, 0
        while self.parent[root] != root:
            acc ^= self.par[root]
            root = self.parent[root]
        return root, acc

    def union(self, a, b, differ):
        ra, pa = self.find(a)
        rb, pb = self.find(b)
        want = (1 if differ else 0) ^ pa ^ pb
        if ra == rb:
            return want == 0
        self.parent[ra] = rb
        self.par[ra] = want
        return True


def main():
    entries = {e["subject"]: e for e in json.load(open(RULE6))}
    A = build_instrumented()
    print("instrumented assign.py (var_of probe): diff adds 1 line + footer",
          flush=True)
    rows = []
    for s in ORDER:
        row = {"subject": s}
        t0 = time.time()
        res = compile_tree(entries[s]["requested"], entries[s]["pairs"])
        row["sparse_compile_secs"] = round(time.time() - t0, 1)
        if res.stage_reached != "emit":
            row["error"] = f"sparse compile stopped@{res.stage_reached}"
            rows.append(row); json.dump(rows, open(OUT, "w"), indent=1)
            print(f"{s}: SPARSE STOP", flush=True); continue
        N, pieces = res.layout.N, res.assignment.pieces
        row["N"] = N

        A._PROBE.clear()
        asg = A.assign(res.layout, res.ridges, res.boundary_ridges,
                       res.contours, global_check=None)
        var_of = A._PROBE.get("var_of")
        if not var_of:
            row["error"] = "var_of probe empty -- patch did not fire"
            rows.append(row); json.dump(rows, open(OUT, "w"), indent=1)
            print(f"{s}: PROBE EMPTY", flush=True); continue

        ridge_idx = [i for i, p in enumerate(pieces) if p.role == "ridge"]
        # variable -> the direction classes of its ridge pieces
        var_dirs = collections.defaultdict(set)
        var_pieces = collections.defaultdict(list)
        for i in ridge_idx:
            v = var_of.get(i)
            if v is None:
                continue
            var_dirs[v].add(direction_class(pieces[i]))
            var_pieces[v].append(i)
        row["ridge_pieces"] = len(ridge_idx)
        row["ridge_pieces_without_a_variable"] = sum(
            1 for i in ridge_idx if var_of.get(i) is None)
        row["ridge_variables"] = len(var_dirs)

        # --- MEASUREMENT 1: orientation coherence -------------------------
        multi = {v for v, ds in var_dirs.items() if len(ds) > 1}
        row["vars_spanning_multiple_orientations"] = len(multi)
        row["vars_spanning_multiple_orientations_pct"] = (
            round(100 * len(multi) / len(var_dirs), 2) if var_dirs else None)
        by_class = collections.Counter(
            tuple(sorted(ds)) for ds in var_dirs.values())
        row["orientation_class_hist"] = {
            str(k): v for k, v in by_class.most_common(6)}

        # --- MEASUREMENT 2+3: rule coverage and consistency ---------------
        at_vertex = collections.defaultdict(set)
        for i in ridge_idx:
            v = var_of.get(i)
            if v is None:
                continue
            at_vertex[pieces[i].a].add(v)
            at_vertex[pieces[i].b].add(v)

        counts = collections.Counter()
        dsu = ParityDSU()
        conflicts = 0
        skipped_incoherent = 0
        for vtx, vars_here in at_vertex.items():
            for a, b in itertools.combinations(sorted(vars_here), 2):
                if a in multi or b in multi:
                    skipped_incoherent += 1
                    continue
                rel = relation(next(iter(var_dirs[a])), next(iter(var_dirs[b])))
                counts[rel] += 1
                if rel == "oblique":
                    continue          # F.3 says nothing about this pair
                if not dsu.union(a, b, differ=(rel == "parallel")):
                    conflicts += 1
        row["pairs_parallel"] = counts["parallel"]
        row["pairs_perpendicular"] = counts["perpendicular"]
        row["pairs_oblique"] = counts["oblique"]
        row["pairs_skipped_incoherent_variable"] = skipped_incoherent
        governed = counts["parallel"] + counts["perpendicular"]
        total_pairs = governed + counts["oblique"]
        row["rule_coverage_pct"] = (round(100 * governed / total_pairs, 2)
                                    if total_pairs else None)
        row["parity_conflicts"] = conflicts
        row["consistent"] = conflicts == 0
        rows.append(row)
        json.dump(rows, open(OUT, "w"), indent=1)
        print(f"{s:11} N={N:3} ridge_vars={row['ridge_variables']:4} "
              f"multi_orient={row['vars_spanning_multiple_orientations']:4} "
              f"({row['vars_spanning_multiple_orientations_pct']}%) "
              f"pairs par/perp/obl="
              f"{counts['parallel']}/{counts['perpendicular']}/{counts['oblique']} "
              f"coverage={row['rule_coverage_pct']}% "
              f"CONFLICTS={conflicts}", flush=True)
    json.dump(rows, open(OUT, "w"), indent=1)
    print("done", flush=True)


main()
