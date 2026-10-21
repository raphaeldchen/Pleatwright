"""Does the SAT witness EMIT? Seed the pipeline with it and run the real tail.

`sat_encode.py` found an M/V labelling of dense `lizard`'s 745 creases that
admits a valid layer order -- SAT in 0.2 s, `layer_certify.decide` CERTIFIED,
0 Maekawa violations of 366 interior vertices, and 308+ labels away from every
one of the 113 candidates the 500,000-node CEGAR search refuted. That was a
satisfiability result. This asks for the artifact.

HOW. `compile_tree`'s tail after `assign` returns is:

    fold = to_fold(lay, asg); ff = flat_fold.flat_fold(fold)
    graph = graph_cell[0] or constraint_graph(ff)
    labels = {k: a for _, _, k, a in ff.shared_edges if a in ("M", "V")}
    res.verdict = layers.certify(graph, labels, budget=...)
    res.stage_reached = "emit"; res.fold = fold

The witness is keyed by FOLD edge, so rather than reach back through
`piece_keys` into `assign`'s variables, this rewrites `edges_assignment` on the
candidate's own fold and runs that exact tail. The result is the same object
`compile_tree` would have set as `res.fold`.

WHAT THIS DOES AND DOES NOT SETTLE. It settles whether the witness yields a
FOLD that the pipeline's own validators accept. It does NOT show `assign` could
have found it: `assign` searches a 3-valued domain (M/V/F) under local laws this
script never consults, and seeding bypasses them. So a pass here means "the
labelling is valid and emits", not "the search can reach it" -- and the
independent auditors below are what make the first claim worth anything.

IT ALSO TESTS THE ASSUMPTION THE WHOLE JOINT ENCODING RESTS ON. §14 argued
`cons` is label-independent because M and V both reflect across a crease and so
give identical folded POSITIONS. That was an argument. Here it is a measurement:
flat_fold the candidate's labelling and the witness's, and compare the folded
vertex coordinates. If they differ, §14's encoding was unsound and its SAT
result does not mean what it says.
"""
from __future__ import annotations

import json
import sys
import time

sys.path.insert(0, ".")

import cp_audit
import flat_fold
import layer_certify
import numpy as np
from box_pleat import cores
from box_pleat import layers as L
from box_pleat.compile import compile_tree
from box_pleat.emit import to_fold

RULE6 = ("../docs/superpowers/evidence/2026-09-08-vlm-tree-authoring"
         "/data/rule6_serve.json")
SAT = ("../docs/superpowers/evidence/2026-10-02-witness-identity-113"
       "/sat-dense.json")


class _Grab(Exception):
    """Abort the compile once the first candidate's fold is captured.

    Not ValueError/RuntimeError/KeyError, so `compile_tree` cannot fold it
    into an indistinguishable AssignFail("error").
    """


def capture_fold():
    """The first rejected candidate's FOLD, its `ff`, and its graph.

    `to_fold` is patched rather than `cores.shrink`, because the fold itself
    is what gets rewritten -- and it is the same fold `_check` hands to
    `flat_fold` on that candidate.
    """
    cell = {}
    real_tf = to_fold
    import box_pleat.compile as cm

    def tf(lay, cand):
        f = real_tf(lay, cand)
        cell.setdefault("fold", f)
        cell.setdefault("lay", lay)
        raise _Grab

    cm.to_fold = tf
    try:
        with open(RULE6) as fh:
            e = next(x for x in json.load(fh) if x["subject"] == "lizard")
        try:
            compile_tree(e["requested"], e["pairs"], dense=True,
                         assign_budget=500_000)
        except _Grab:
            pass
    finally:
        cm.to_fold = real_tf
    if "fold" not in cell:
        raise SystemExit("REFUSED: no candidate fold was captured")
    return cell["fold"]


def rewrite(fold, witness):
    """`fold` with every creased edge relabelled to the witness.

    Only edges already carrying M or V are touched: the F set and the boundary
    are the pipeline's and must not move, or this would be a different crease
    set and §14's result would not apply to it.
    """
    out = json.loads(json.dumps(fold))
    EV = out["edges_vertices"]
    EA = out["edges_assignment"]
    # `edges_foldAngle` MUST be rewritten beside `edges_assignment`. The first
    # version of this function rewrote only the assignment, so the emitted
    # witness.fold carried the REFUTED candidate's angles: 352 of 745 creases
    # contradicted the labelling the file claimed (2026-10-03). It hid because
    # the histograms nearly agree -- 388 entries at -180 against 384 `M`, 357 at
    # +180 against 361 `V` -- so a count-based check passes and only a per-edge
    # comparison finds it. Oriedita and `cp_audit` both read `edges_assignment`
    # and were unaffected (measured: inverting every angle leaves Oriedita at
    # Pass, while one flipped assignment is caught), but the Origami Simulator
    # bridge uses `edges_foldAngle` WHEN PRESENT, so the stale array folded 352
    # creases the wrong way.
    ANGLE = {"M": -180.0, "V": 180.0, "B": 0.0}   # emit.py:80, the pipeline's map
    FA = out.get("edges_foldAngle")
    hit = miss = 0
    for i, (a, b) in enumerate(EV):
        if EA[i] not in ("M", "V"):
            continue
        k = (min(a, b), max(a, b))
        if k in witness:
            EA[i] = witness[k]
            if FA is not None:
                FA[i] = ANGLE[EA[i]]
            hit += 1
        else:
            miss += 1
    if FA is not None:
        bad = [i for i, a in enumerate(EA)
               if a in ("M", "V") and FA[i] != ANGLE[a]]
        if bad:
            raise SystemExit(
                f"REFUSED: {len(bad)} creased edges have an `edges_foldAngle` "
                f"that contradicts their `edges_assignment` (first: {bad[0]}). "
                f"The fold would describe a labelling that is neither the "
                f"candidate's nor the witness's.")
    return out, hit, miss


def main(out_path):
    rec = {}
    sat = json.load(open(SAT))
    if not sat["free_query"]["sat"]:
        raise SystemExit("REFUSED: the committed SAT artifact says UNSAT")
    witness = {tuple(int(x) for x in k.split(",")): v
               for k, v in sat["free_query"]["witness_labels"].items()}
    print(f"witness: {len(witness)} creases, "
          f"{sum(1 for v in witness.values() if v == 'V')} V")

    fold = capture_fold()
    fold2, hit, miss = rewrite(fold, witness)
    print(f"relabelled {hit} creased edges; {miss} creased edges absent from "
          f"the witness")
    rec["relabelled"] = hit
    rec["creased_edges_not_in_witness"] = miss
    if miss:
        raise SystemExit(
            f"REFUSED: {miss} creased edges are not in the witness, so the "
            f"witness does not describe this crease set and no verdict here "
            f"would be about it.")

    # ---- the assumption §14 rests on, measured -------------------------
    print()
    print("=== §14's load-bearing assumption: are the folded POSITIONS "
          "label-independent? ===")
    ff1 = flat_fold.flat_fold(fold)
    ff2 = flat_fold.flat_fold(fold2)
    same_faces = len(ff1.faces) == len(ff2.faces)
    maxdev = None
    if same_faces:
        devs = [float(np.max(np.abs(np.asarray(a, float) - np.asarray(b, float))))
                for a, b in zip(ff1.folded_vertices, ff2.folded_vertices)
                if np.shape(a) == np.shape(b)]
        maxdev = max(devs) if devs else None
    print(f"  faces: {len(ff1.faces)} vs {len(ff2.faces)}  "
          f"(same: {same_faces})")
    print(f"  max |folded position difference|: {maxdev}")
    rec["label_independence"] = {"faces_a": len(ff1.faces),
                                 "faces_b": len(ff2.faces),
                                 "same_face_count": same_faces,
                                 "max_position_dev": maxdev}
    if not same_faces or (maxdev is not None and maxdev > 1e-9):
        print("  *** THE ASSUMPTION FAILS -- §14's joint encoding was not "
              "sound on this instance ***")

    # ---- the real tail of compile_tree --------------------------------
    print()
    print("=== compile_tree's tail, on the rewritten fold ===")
    graph2 = L.constraint_graph(ff2)
    labels2 = {k: a for _, _, k, a in ff2.shared_edges if a in ("M", "V")}
    agree = sum(1 for k, v in labels2.items() if witness.get(k) == v)
    print(f"  labels recovered from ff2 match the witness on "
          f"{agree} of {len(labels2)}")
    rec["labels_roundtrip"] = {"matched": agree, "total": len(labels2)}
    if agree != len(labels2) or len(labels2) != len(witness):
        raise SystemExit("REFUSED: the fold does not round-trip to the "
                         "witness labelling, so the tail below would be "
                         "running on something else")

    w = L.propagate(graph2, labels2)
    print(f"  layers.propagate     : "
          f"{'None (consistent)' if w is None else 'CONTRADICTION ' + w.kind}")
    t0 = time.perf_counter()
    verdict = L.certify(graph2, labels2, budget=layer_certify.CERTIFY_BUDGET)
    print(f"  layers.certify       : {verdict.kind} (nodes {verdict.nodes}, "
          f"free {verdict.free}) in {round(time.perf_counter()-t0,1)}s")
    rec["propagate"] = None if w is None else w.kind
    rec["certify"] = {"kind": verdict.kind, "nodes": verdict.nodes,
                      "free": verdict.free}

    # ---- independent auditors -----------------------------------------
    print()
    print("=== independent auditors on the emitted fold ===")
    for name, f in (("candidate (refuted)", fold), ("WITNESS", fold2)):
        try:
            rep = cp_audit.audit_fold(f)
        except ValueError as exc:
            print(f"  {name:20}: cp_audit RAISED {exc}")
            continue
        fields = {k: v for k, v in vars(rep).items()
                  if isinstance(v, (int, float, bool, str))}
        print(f"  {name:20}: {fields}")
        rec.setdefault("cp_audit", {})[name] = fields

    # ---- the artifact --------------------------------------------------
    stem = out_path.rsplit(".", 1)[0]
    fold_path = f"{stem}.fold"
    with open(fold_path, "w") as fh:
        json.dump(fold2, fh)
    print()
    print(f"wrote {fold_path}  "
          f"({len(fold2['vertices_coords'])} vertices, "
          f"{len(fold2['edges_vertices'])} edges)")
    rec["fold_path"] = fold_path
    rec["fold_stats"] = {"vertices": len(fold2["vertices_coords"]),
                         "edges": len(fold2["edges_vertices"])}
    with open(out_path, "w") as fh:
        json.dump(rec, fh, indent=1, sort_keys=True)
    print(f"wrote {out_path}")

    print()
    if w is not None:
        print(f"VERDICT: the witness CONTRADICTS on the rewritten fold "
              f"({w.kind}). Either the rewrite is not faithful or §14's "
              f"label-independence assumption fails; no emit claim stands.")
    elif verdict.kind == "CERTIFIED":
        print("VERDICT: EMITS. The witness labelling yields a FOLD that "
              "`layers.propagate` accepts and `layers.certify` CERTIFIES, on "
              "the same crease set the 500,000-node search could not label. "
              "Read `cp_audit` above for the local laws, and §14.5's AREA_EPS "
              "caveat still binds: CERTIFIED is not flat-foldable.")
    else:
        print(f"VERDICT: PARTIAL -- propagate is clean but certify returned "
              f"{verdict.kind}, so a complete layer order was not exhibited "
              f"within the budget. That is a statement about this search, not "
              f"about the labelling.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: seed_witness.py <out.json>")
    main(sys.argv[1])
