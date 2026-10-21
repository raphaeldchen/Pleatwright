"""Gap 1 Phase 0: is the dense crease SET the blocker, or is the SEARCH?

Two diagnostics, both cheap, that discriminate between the two candidate root
causes of "no dense candidate ever certifies":

  ROOT CAUSE 1 -- the crease set is over-constrained. `pleat_paths(dense=True)`
  makes EVERY `axial`/`elev` piece a crease (its own docstring: "removes that
  label filter"). COrigami F.1.1 steps 3-4 are a SELECTION FILTER -- "retain
  only segments strictly perpendicular to an intersecting hinge, or passing
  through an X-shape vertex (four intersecting ridges)", then "selectively
  re-introduce segments meeting the outer border where they share a vertex with
  both a ridge and an established pleat". `2026-09-24-dense-pleats-design.md`
  section 3 rejected "F.1.1 steps 1-4" as a BUNDLE, on the true grounds that
  `contours.py` already supplies the elevation field steps 1-2 would build --
  but steps 3-4 are not about elevations, and nothing replaced them. The spec
  recorded the cost of that rejection as too LITTLE coverage (54.7% of the
  half-grid, a statement about steps 1-2) and never as too MANY creases.

  ROOT CAUSE 2 -- the set is fine and the search cannot find the labelling,
  which is what F.3 ridge determinism and minimal unsat cores address.

PART A -- variable census by role. How many dense CSP variables are pleats,
ridges, hinges, centre column? Nobody has measured this, and it SIZES F.3's
leverage. Pieces are NOT variables: run-merging, pleat-path grouping and
mirror-merging collapse thousands of creases onto a few hundred variables, so a
census over piece roles would be the wrong denominator. Read from production's
own `var_of` via the in-memory patch technique `where_the_time_goes.py`
established (patch, verify the diff, import -- never a committed fork).

PART B -- the F.1.1 steps 3-4 predicate, as a CLASSIFIER before it is a filter.
Applied to a real dense candidate, reporting how many pieces each reading
retains.

WHY SEVERAL READINGS, AND NOT ONE. The paper's prose leaves "intersecting"
and the step-4 clause genuinely ambiguous, and this project has already burned
three definitions of `interleave.adjacency` -- one of which passed every
hand-built unit test while producing an EMPTY graph on all real data, a vacuous
pass that looked like success. The lesson recorded in memory
(`throwaway-probes-need-real-rigour`) is to enumerate the readings up front and
measure them all, so a degenerate one is visible immediately rather than after
it has shaped a design. Every variant therefore carries a non-vacuity check:
a variant retaining 0 pieces, or ALL of them, is reported as DEGENERATE.

This script CHANGES NOTHING. It classifies and counts. Wiring the chosen
predicate into `pleat_paths` is Phase A and needs its own spec.

Run from mcp_harness:
  PYTHONPATH=. ../.venv/bin/python3 -u \\
      ../docs/superpowers/evidence/2026-09-26-gap1-phase0/phase0.py \\
      <out.json> [subject ...]
"""
import collections
import difflib
import importlib.util
import json
import os
import pathlib
import signal
import sys
import time

from box_pleat.compile import compile_tree

OUT = sys.argv[1]
SUBJECTS = sys.argv[2:] or ["starfish", "lizard", "frog", "horse", "bird",
                            "guinea_pig"]
DENSE_CAP_SECS = 300
RULE6 = os.path.join("..", "docs", "superpowers", "evidence",
                     "2026-09-08-vlm-tree-authoring", "data", "rule6_serve.json")

ASSIGN_SRC = pathlib.Path("box_pleat/assign.py")

_ORIG = """    nodes = budget
    frames: list = []          # [variable, value order, next value index]
"""
_PATCHED = """    _PROBE["var_of"] = dict(var_of)
    _PROBE["n_pieces"] = len(pieces)
    nodes = budget
    frames: list = []          # [variable, value order, next value index]
"""
_FOOTER = """

_PROBE = {}
"""


def build_instrumented():
    """Patch production `assign.py` in memory; verify the diff; import it.

    Appended, not prepended, and loaded under the dotted name
    `box_pleat._assign_probe`: `assign.py` opens with `from __future__ import
    annotations` (which must be the first statement) and uses relative imports
    (which need `__package__` to be `box_pleat`). `_PROBE` is resolved as a
    module global at call time, so defining it at the end is correct."""
    src = ASSIGN_SRC.read_text()
    if src.count(_ORIG) != 1:
        raise SystemExit("REFUSING TO MEASURE: assign.py's DFS setup does not "
                         "match this script's expected text exactly once. "
                         "Re-derive the patch against today's source.")
    patched = src.replace(_ORIG, _PATCHED) + _FOOTER
    removed = [l[1:] for l in difflib.unified_diff(
        src.splitlines(), patched.splitlines(), lineterm="", n=0)
        if l.startswith("-") and not l.startswith("---")]
    if removed:
        raise SystemExit(f"REFUSING TO MEASURE: patch removed lines: {removed}")
    out = pathlib.Path(os.environ.get("TMPDIR", "/tmp")) / "_assign_probe.py"
    out.write_text(patched)
    import box_pleat  # noqa: F401 - needed in sys.modules for relative imports
    name = "box_pleat._assign_probe"
    spec = importlib.util.spec_from_file_location(name, out)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------
# PART B: the F.1.1 steps 3-4 predicate, in four readings
# --------------------------------------------------------------------------
def orient(p):
    """'h' if the piece runs along x, 'v' if along y. Pieces are unit segments
    on the half-grid, so exactly one coordinate differs."""
    return "h" if p.a[1] == p.b[1] else "v"


def classify(pieces, N):
    """Retained-piece counts for each reading of F.1.1 steps 3-4.

    Returns {variant_name: frozenset(piece indices retained)}. Candidates are
    the `axial`/`elev` pieces -- exactly what `pleat_paths(dense=True)` takes,
    so the counts are directly comparable to today's dense variable pool.
    """
    at_vertex = collections.defaultdict(list)
    for i, p in enumerate(pieces):
        at_vertex[p.a].append(i)
        at_vertex[p.b].append(i)

    # An X-shape vertex: four intersecting RIDGES (paper's own gloss).
    x_vertex = {v for v, ids in at_vertex.items()
                if sum(1 for i in ids if pieces[i].role == "ridge") >= 4}

    cand = [i for i, p in enumerate(pieces) if p.role in ("axial", "elev")]

    def touches_hinge(i, require_perp):
        p = pieces[i]
        for v in (p.a, p.b):
            for j in at_vertex[v]:
                if pieces[j].role != "hinge":
                    continue
                if not require_perp or orient(pieces[j]) != orient(p):
                    return True
        return False

    def on_border(i):
        p = pieces[i]
        return any(c in (0, 2 * N) for v in (p.a, p.b) for c in v)

    v1 = frozenset(i for i in cand if touches_hinge(i, True))
    v2 = frozenset(i for i in cand if touches_hinge(i, False))
    v3 = frozenset(i for i in cand
                   if touches_hinge(i, True)
                   or any(v in x_vertex for v in (pieces[i].a, pieces[i].b)))
    # Step 4, one pass: a border segment sharing a vertex with BOTH a ridge and
    # an already-established (v3) pleat.
    v3_vertices = {v for i in v3 for v in (pieces[i].a, pieces[i].b)}
    v4 = frozenset(v3 | {
        i for i in cand
        if i not in v3 and on_border(i)
        and any(pieces[j].role == "ridge" for v in (pieces[i].a, pieces[i].b)
                for j in at_vertex[v])
        and any(v in v3_vertices for v in (pieces[i].a, pieces[i].b))})
    return {"v1_perp_hinge": v1,
            "v2_any_hinge_no_perp_test": v2,
            "v3_step3_full": v3,
            "v4_step3_plus_step4_border": v4}, len(cand), len(x_vertex)


class _Timeout(Exception):
    pass


def _alarm(signum, frame):
    raise _Timeout()


def main():
    entries = {e["subject"]: e for e in json.load(open(RULE6))}
    A = build_instrumented()
    print("instrumented assign.py (var_of probe): diff adds 2 lines + footer",
          flush=True)
    rows = []

    for s in SUBJECTS:
        row = {"subject": s}
        t0 = time.time()
        res = compile_tree(entries[s]["requested"], entries[s]["pairs"])
        if res.stage_reached != "emit":
            row["error"] = f"sparse compile stopped@{res.stage_reached}"
            rows.append(row); json.dump(rows, open(OUT, "w"), indent=1)
            print(f"{s}: SPARSE STOP", flush=True); continue
        row["sparse_compile_secs"] = round(time.time() - t0, 1)
        N = res.layout.N
        row["N"] = N

        A._PROBE.clear()
        old = signal.signal(signal.SIGALRM, _alarm)
        signal.alarm(DENSE_CAP_SECS)
        try:
            asg = A.assign(res.layout, res.ridges, res.boundary_ridges,
                           res.contours, dense=True, global_check=None)
        except _Timeout:
            row["dense_timeout"] = True
            rows.append(row); json.dump(rows, open(OUT, "w"), indent=1)
            print(f"{s}: DENSE TIMEOUT {DENSE_CAP_SECS}s", flush=True); continue
        finally:
            signal.alarm(0); signal.signal(signal.SIGALRM, old)
        if isinstance(asg, A.AssignFail):
            row["error"] = f"dense assign failed: {asg!r}"
            rows.append(row); json.dump(rows, open(OUT, "w"), indent=1)
            print(f"{s}: DENSE FAIL", flush=True); continue

        pieces = asg.pieces
        # ---- PART A: variable census by role -------------------------------
        var_of = A._PROBE.get("var_of")
        if not var_of:
            row["part_a_error"] = "var_of probe empty -- patch did not fire"
        else:
            roles_of_var = collections.defaultdict(set)
            for i, v in var_of.items():
                roles_of_var[v].add(pieces[i].role)
            sig = collections.Counter(
                "+".join(sorted(rs)) for rs in roles_of_var.values())
            row["total_variables"] = len(roles_of_var)
            row["variables_by_role"] = dict(sorted(sig.items()))
            row["pleat_vars"] = len(asg.pleat_vars)
            row["released_vars"] = len(asg.released_vars)
            # F.3's leverage: the share of variables that are PURELY ridge.
            ridge_only = sig.get("ridge", 0)
            row["ridge_only_variables"] = ridge_only
            row["ridge_share_of_variables"] = (
                round(100 * ridge_only / len(roles_of_var), 2))

        # ---- PART B: the filter, as a classifier ---------------------------
        variants, n_cand, n_x = classify(pieces, N)
        row["dense_candidate_pieces"] = n_cand
        row["x_shape_vertices"] = n_x
        row["dense_mv_emitted"] = sum(1 for l in asg.labels if l in ("M", "V"))
        row["sparse_mv"] = sum(1 for l in res.assignment.labels
                               if l in ("M", "V"))
        row["variants"] = {}
        for name, keep in variants.items():
            degenerate = (len(keep) == 0 or len(keep) == n_cand)
            row["variants"][name] = {
                "retained": len(keep),
                "retained_pct_of_candidates": round(100 * len(keep) / n_cand, 2)
                if n_cand else None,
                "DEGENERATE": degenerate,
            }
        rows.append(row)
        json.dump(rows, open(OUT, "w"), indent=1)
        print(f"{s:11} N={N:3} cand={n_cand:6} sparse_mv={row['sparse_mv']:5} "
              f"dense_mv={row['dense_mv_emitted']:6} vars={row.get('total_variables')} "
              f"ridge_share={row.get('ridge_share_of_variables')}% "
              + " ".join(f"{k.split('_')[0]}={v['retained']}"
                         + ("!DEGEN" if v["DEGENERATE"] else "")
                         for k, v in row["variants"].items()), flush=True)

    json.dump(rows, open(OUT, "w"), indent=1)
    print("done", flush=True)


main()
