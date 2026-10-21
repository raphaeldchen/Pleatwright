"""Does AREA_EPS remove constraints on dense `lizard`, and does the witness survive?

`witness.fold` is CERTIFIED (README section 15), but `layer_certify`'s docstring
says in capitals that CERTIFIED is not flat-foldable, because
`layer_order.AREA_EPS` (1e-9) drops sliver arrangement cells before
`cons.pairs` is built and "a dropped cell REMOVES constraints and can never add
one". That is the one caveat that could still undo a POSITIVE result, so it is
measured here rather than restated.

PRIOR WORK, AND WHERE IT IS INCOMPLETE. `layer_order.py:35-62` records a
six-subject, two-platform study (U20, 2026-08-17, `probe_sigma_platform.py`)
that CLEARS the constant, on a structural argument: "a sliver's cover is a
subset of the cover of the cell it was split from, so dropping it removes no
pair", with `pairs` measured identical across platforms on star-4-sym (28/28),
star-6 (190/190) and template-bird (196/196).

Reading `_cells` and `_split_convex` shows that argument covers only HALF the
drops. `_cells` starts from one bounding-box cell and cuts it by each face:

  * an OUTSIDE piece keeps the parent's cover, so dropping it removes no pair
    -- the prior argument holds exactly here; and
  * the INTERSECTION takes cover ∪ {face}, a strict SUPERSET, and
    `_split_convex` drops it too (`layer_order.py:310-311`). Dropping THAT
    removes every pair between the new face and the parent's cover.

So the question is specifically: on dense `lizard`, does AREA_EPS drop any
INTERSECTION cell, and if the threshold is lowered does `pairs` grow and the
witness stop certifying?

THREE MEASUREMENTS.
  M1  How often the threshold fires at all, split by drop kind, with the area
      distribution and the minimum cell area actually seen. If the minimum is
      far above 1e-9, the constant is inert here by inspection.
  M2  A sweep of AREA_EPS down to 0, comparing the constraint system at each
      step -- cells, pairs, covers, equalities, tacos, transitivity triples.
  M3  The witness re-verified at every step: `propagate` and `certify`. If it
      stays CERTIFIED as the threshold goes to zero, the caveat is closed for
      this instance.

HONEST DIRECTION. Lowering the threshold can also FABRICATE constraints from
numerically degenerate slivers -- `layer_order.py:70-77` records exactly that
happening to a sibling epsilon on Linux, breaking this module's stated
under-refutation promise. So a refutation at AREA_EPS=0 is NOT automatically
damning; it has to be read against the area distribution from M1.
"""
from __future__ import annotations

import json
import sys
import time

sys.path.insert(0, ".")

import flat_fold
import layer_certify
import layer_order
import numpy as np
from box_pleat import layers as L

WITNESS = ("../docs/superpowers/evidence/2026-10-02-witness-identity-113"
           "/witness.fold")
SWEEP = (1e-9, 1e-10, 1e-11, 1e-12, 1e-14, 0.0)


def instrumented_split():
    """Wrap `_split_convex` so every AREA_EPS drop is recorded by KIND.

    Re-implements the drop test rather than reading it out of the real
    function, so the two could drift. Guarded: the wrapper asserts its own
    verdict matches what the real function actually returned for the
    intersection, and raises if they disagree.
    """
    real = layer_order._split_convex
    log = {"outside": [], "inter": [], "mismatch": 0}

    def wrapped(subject, clip):
        inter, pieces = real(subject, clip)
        eps = layer_order.AREA_EPS
        # The intersection the real function computed, before its own test:
        remaining = subject
        n = len(clip)
        for i in range(n):
            a, b = clip[i], clip[(i + 1) % n]
            if len(remaining) < 3:
                break
            outside = layer_order._clip_half(remaining, b, a)
            if len(outside) >= 3:
                ar = abs(layer_order._area(outside))
                if ar <= eps:
                    log["outside"].append(ar)
            remaining = layer_order._clip_half(remaining, a, b)
        if len(remaining) >= 3:
            ar = abs(layer_order._area(remaining))
            if ar <= eps:
                log["inter"].append(ar)
                if inter is not None:
                    log["mismatch"] += 1
            elif inter is None:
                log["mismatch"] += 1
        return inter, pieces

    layer_order._split_convex = wrapped
    return real, log


def build(ff, eps):
    """`(cons, slots)` rebuilt at a given AREA_EPS, with drop accounting."""
    old = layer_order.AREA_EPS
    layer_order.AREA_EPS = eps
    real, log = instrumented_split()
    try:
        cons, slots = layer_order.constraints_for(ff)
    finally:
        layer_order._split_convex = real
        layer_order.AREA_EPS = old
    return cons, slots, log


def triples(cons):
    from itertools import combinations
    seen = set()
    for cover in cons.covers:
        for t in combinations(sorted(cover), 3):
            seen.add(t)
    return len(seen)


def main(out_path):
    fold = json.load(open(WITNESS))
    ff = flat_fold.flat_fold(fold)
    witness = {k: a for _, _, k, a in ff.shared_edges if a in ("M", "V")}
    print(f"witness.fold: {len(fold['vertices_coords'])} vertices, "
          f"{len(fold['edges_vertices'])} edges, {len(witness)} creases")
    rec = {"sweep": {}, "shipped_area_eps": layer_order.AREA_EPS}

    base = None
    for eps in SWEEP:
        t0 = time.perf_counter()
        cons, slots, log = build(ff, eps)
        tri = triples(cons)
        cover_total = sum(len(c) for c in cons.covers)
        row = {
            "cells": len(cons.covers), "pairs": len(cons.pairs),
            "cover_total": cover_total, "equalities": len(cons.equalities),
            "tacos": len(cons.tacos), "triples": tri,
            "dropped_outside": len(log["outside"]),
            "dropped_intersection": len(log["inter"]),
            "wrapper_mismatch": log["mismatch"],
            "min_dropped_area": (min(log["outside"] + log["inter"])
                                 if (log["outside"] or log["inter"]) else None),
            "max_dropped_area": (max(log["outside"] + log["inter"])
                                 if (log["outside"] or log["inter"]) else None),
            "build_secs": round(time.perf_counter() - t0, 1),
        }
        if log["mismatch"]:
            raise SystemExit(
                f"REFUSED: the drop-accounting wrapper disagreed with "
                f"`_split_convex` on {log['mismatch']} intersection(s) at "
                f"eps={eps}; its counts cannot be trusted.")

        graph = L.LayerGraph(cons=cons, slots=slots)
        w = L.propagate(graph, witness)
        row["propagate"] = None if w is None else w.kind
        t1 = time.perf_counter()
        v = L.certify(graph, witness, budget=layer_certify.CERTIFY_BUDGET)
        row["certify"] = v.kind
        row["certify_nodes"] = v.nodes
        row["certify_free"] = v.free
        row["certify_secs"] = round(time.perf_counter() - t1, 1)

        if base is None:
            base = row
            row["pairs_delta_vs_shipped"] = 0
        else:
            row["pairs_delta_vs_shipped"] = row["pairs"] - base["pairs"]

        rec["sweep"][repr(eps)] = row
        print(f"  eps={eps:<8g} cells {row['cells']:>3} pairs "
              f"{row['pairs']:>6} (Δ{row['pairs_delta_vs_shipped']:+d}) "
              f"tri {tri:>9,} eq {row['equalities']:>6} taco "
              f"{row['tacos']:>6} | dropped out/int "
              f"{row['dropped_outside']}/{row['dropped_intersection']} | "
              f"propagate {row['propagate']} certify {row['certify']} "
              f"({row['certify_secs']}s)", flush=True)

    # ---- the minimum cell area actually present, at eps = 0 -------------
    cons0, _s0, _l0 = build(ff, 0.0)
    print()
    print("=== M1: how close does dense lizard come to the threshold? ===")
    # `cons` carries covers, not polygons, so the cell polygons come from
    # re-running the same two calls `constraints_for` makes.
    polys = layer_order._polys_of(ff)
    cells = layer_order._cells(polys)
    areas = sorted(abs(layer_order._area(np.asarray(p, float)))
                   for p, _c in cells)
    print(f"  arrangement cells at the shipped eps: {len(areas)}")
    print(f"  cell areas: min {areas[0]:.6e}  "
          f"p10 {areas[len(areas)//10]:.6e}  median "
          f"{areas[len(areas)//2]:.6e}")
    print(f"  margin of the smallest cell over AREA_EPS=1e-9: "
          f"{areas[0]/1e-9:.1f}x")
    rec["cell_areas"] = {"count": len(areas), "min": areas[0],
                         "median": areas[len(areas) // 2],
                         "margin_over_eps": areas[0] / 1e-9}

    with open(out_path, "w") as fh:
        json.dump(rec, fh, indent=1, sort_keys=True)
    print(f"\nwrote {out_path}")

    # ---- verdict, after every row --------------------------------------
    rows = list(rec["sweep"].values())
    pairs_moved = len({r["pairs"] for r in rows}) > 1
    all_certified = all(r["certify"] == "CERTIFIED" for r in rows)
    any_inter = any(r["dropped_intersection"] for r in rows)
    print()
    if not pairs_moved and not any_inter and all_certified:
        print(f"VERDICT: THE CAVEAT IS INERT HERE. Across AREA_EPS from "
              f"{SWEEP[0]:g} down to 0 the constraint system does not move "
              f"(`pairs` constant at {rows[0]['pairs']}), no INTERSECTION "
              f"cell is ever dropped, and the witness stays CERTIFIED at "
              f"every step. On dense `lizard` the smallest arrangement cell "
              f"clears the threshold by {rec['cell_areas']['margin_over_eps']:.0f}x, "
              f"so AREA_EPS removes nothing and section 15's result does not "
              f"depend on it.")
    elif all_certified:
        print(f"VERDICT: THE SYSTEM MOVES BUT THE VERDICT DOES NOT. `pairs` "
              f"ranges over {sorted({r['pairs'] for r in rows})} across the "
              f"sweep and {sum(r['dropped_intersection'] for r in rows)} "
              f"intersection cell(s) are dropped in total, so AREA_EPS does "
              f"remove constraints here -- but the witness stays CERTIFIED at "
              f"every threshold down to 0. The caveat is real and does not "
              f"bite on this witness.")
    else:
        bad = [e for e, r in rec["sweep"].items() if r["certify"] != "CERTIFIED"]
        print(f"VERDICT: THE CAVEAT BITES. The witness stops certifying at "
              f"eps={bad}. Read this against M1's area distribution before "
              f"concluding section 15 is undone: lowering the threshold can "
              f"FABRICATE constraints from degenerate slivers, which "
              f"`layer_order.py:70-77` records happening to a sibling epsilon "
              f"on Linux.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: area_eps.py <out.json>")
    main(sys.argv[1])
