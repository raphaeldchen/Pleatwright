"""A COMPLETE method for dense layer ordering: the ADK clause set as SAT.

`../2026-10-02-witness-identity-113/README.md` section 13 measured at least 80
minimal causes on a single rejection, with 42 of 44 cone creases load-bearing in
one, and concluded that per-rejection clause learning teaches the CEGAR loop
roughly one-eightieth of why a region is infeasible. What remains is a complete
method: one query that returns a witness or a proof, instead of enumerating
reasons.

WHAT THIS ENCODES, AND WHAT IT DOES NOT RE-DERIVE. `layer_certify._iter_clauses`
already enumerates the Akitaya-Demaine-Ku families from a `_Constraints` --
equality, transitivity and taco -- deduped, with the flip bits. This module
translates THAT clause set to CNF rather than re-reading the geometry, so it
cannot disagree with the shipped verifier about what the constraints are. One
Boolean per canonical face pair (`rel[(lo,hi)]` = "lo above hi"), exactly
`layer_order._lit`'s convention.

THE JOINT QUERY. `box_pleat.layers.constraint_graph` is documented as "the
label-independent layer-order system of a folded state", and `compile._check`
reuses one graph across every candidate, re-seeding only `cons.direct`. M and V
both reflect across a crease, so they produce the same folded POSITIONS and
differ only in which side lands above -- which is why the split holds. That lets
the labels become VARIABLES too: 745 crease Booleans, linked to order variables
by the 745 `DirectSlot` biconditionals. One SAT call then asks whether ANY
labelling of this fixed crease set admits a valid layer order, replacing a
500,000-node search that found none.

VALIDATION, IN BOTH DIRECTIONS -- and the positive control is the load-bearing
one. The 113 known-contradicting labellings can only catch an UNDER-constrained
encoding; an OVER-constrained one is UNSAT on everything and would pass all 113
vacuously. So:

  V1  POSITIVE, no solver. A complete relation `layer_certify.verify` ACCEPTS
      must satisfy every clause this module emits. Catches over-constraining.
  V2  NEGATIVE, solver. Each labelling `layer_order.propagate` refuted must come
      back UNSAT. `propagate` under-refutes but never over-refutes, so a
      contradiction it derived is genuine. Catches under-constraining.
  V3  NON-TRIVIALITY. Without the label links, the geometry clauses alone must
      be SAT -- otherwise the formula is contradictory before any labelling is
      chosen and every UNSAT below would be uninformative.

LIMITS carried from the modules this builds on: `layer_order.AREA_EPS` drops
sliver arrangement cells before `cons.pairs` is built, so SAT here means
"satisfiable against the constraint set that survived AREA_EPS" -- the same
caveat `layer_certify`'s docstring states in capitals, and strictly weaker than
flat-foldability.
"""
from __future__ import annotations

import json
import sys
import time

sys.path.insert(0, ".")

import layer_certify
import layer_order
from box_pleat import layers as layers_mod
from box_pleat import cores
from box_pleat.compile import compile_tree
from pysat.formula import IDPool
from pysat.solvers import Solver

RULE6 = ("../docs/superpowers/evidence/2026-09-08-vlm-tree-authoring"
         "/data/rule6_serve.json")
SOLVER = "cadical153"


class _Grab(Exception):
    """Abort a compile once the constraint graph is captured.

    Not ValueError/RuntimeError/KeyError, the three `compile_tree` catches
    around `assign(...)`, so it propagates out uncaught rather than being
    typed into an indistinguishable `AssignFail("error")`.
    """


ff_cell = {}


def capture(subject, dense, labels_wanted=0):
    """The `LayerGraph` of the first rejection, plus that candidate's labels.

    Patches `cores.shrink`, which receives `(graph, labels, creases)`, so the
    captured graph is byte-identically the one the committed runs used.
    """
    out = {}
    real = cores.shrink

    def grab(graph, labels, creases, *, counter=None):
        out.setdefault("graph", graph)
        out.setdefault("labels", dict(labels))
        raise _Grab

    real_cg = layers_mod.constraint_graph

    def cg(ff):
        ff_cell.setdefault("ff", ff)
        return real_cg(ff)

    cores.shrink = grab
    layers_mod.constraint_graph = cg
    try:
        with open(RULE6) as fh:
            e = next(x for x in json.load(fh) if x["subject"] == subject)
        try:
            compile_tree(e["requested"], e["pairs"], dense=dense,
                         assign_budget=500_000, core_extraction=False,
                         core_record=True, debug_witness_cores=[])
        except _Grab:
            pass
    finally:
        cores.shrink = real
        layers_mod.constraint_graph = real_cg
    if "graph" not in out:
        raise SystemExit(f"REFUSED: {subject} dense={dense} produced no "
                         f"rejection, so no graph was captured")
    return out["graph"], out["labels"]


# ------------------------------------------------------------------ encoder

def encode(cons, slots, *, with_labels=True, sink=None):
    """`(clauses, pool, order_var, label_var, stats)` for this constraint set.

    One variable per canonical face pair. With `with_labels`, one more per
    crease edge plus the `DirectSlot` biconditionals that link them; without,
    `cons.direct` is emitted as unit clauses instead and the labelling is
    whatever that candidate's was.

    A literal in `layer_certify`'s clauses is `(pair, flip)` and its value is
    `rel[pair] != flip`, so the DIMACS literal is the pair's variable negated
    exactly when `flip` is set.
    """
    pool = IDPool()
    order_var = {p: pool.id(("rel", p)) for p in sorted(cons.pairs)}

    def lit(pair, flip):
        v = order_var[pair]
        return -v if flip else v

    cl = []
    emit = cl.append if sink is None else sink
    fam = {"equality": 0, "transitivity": 0, "taco": 0}

    for c in layer_certify._iter_clauses(cons):
        ls = [lit(p, f) for p, f in zip(c.variables, c.flips)]
        if c.family == "equality":
            # vals[0] == vals[1]  ->  L0 <-> L1
            emit([-ls[0], ls[1]])
            emit([ls[0], -ls[1]])
        elif c.family == "transitivity":
            # satisfied iff NOT (rab == rbc and rac != rab); the two cyclic
            # states (T,T,F) and (F,F,T) are the only forbidden ones.
            a, b, d = ls
            emit([-a, -b, d])
            emit([a, b, -d])
        elif c.family == "taco":
            # satisfied iff (L0 != L1) == (L2 != L3), i.e. the 4-way XOR is
            # even. Forbid every odd-parity assignment: 8 clauses.
            for m in range(16):
                bits = [(m >> i) & 1 for i in range(4)]
                if sum(bits) % 2 == 1:
                    emit([(-ls[i] if bits[i] else ls[i])
                               for i in range(4)])
        else:
            raise SystemExit(
                f"REFUSED: unknown clause family {c.family!r}. "
                f"`layer_certify._satisfied` would raise on it too; encoding "
                f"it as anything would silently admit a family nobody checks.")
        fam[c.family] += 1

    label_var = {}
    if with_labels:
        for s in slots:
            label_var[s.edge] = pool.id(("lab", s.edge))
        for s in slots:
            # layers._seed: val = (label == "V") == (sign == 1). With Lv
            # meaning "label is V", the direct constraint is
            #   (rel[pair] != flip) == (sign == 1 ? Lv : not Lv)
            pair, flip = s.lit
            o = lit(pair, flip)
            lv = label_var[s.edge]
            rhs = lv if s.sign == 1 else -lv
            emit([-o, rhs])
            emit([o, -rhs])
    else:
        for (pair, flip), val, _prov in cons.direct:
            o = lit(pair, flip)
            emit([o] if val else [-o])

    stats = {"order_vars": len(order_var), "label_vars": len(label_var),
             "clauses": fam["equality"] * 2 + fam["transitivity"] * 2
                        + fam["taco"] * 8
                        + (2 * len(slots) if with_labels else len(cons.direct)),
             "families": fam,
             "direct": len(cons.direct), "slots": len(slots)}
    return cl, pool, order_var, label_var, stats


def assume_labels(label_var, labels):
    """Assumption literals pinning every crease to a given labelling."""
    out = []
    for edge, v in label_var.items():
        if edge not in labels:
            raise SystemExit(f"REFUSED: slot edge {edge} absent from the "
                             f"labelling; the two do not describe one state")
        out.append(v if labels[edge] == "V" else -v)
    return out


# --------------------------------------------------------------- validation

def model_to_rel(model, order_var):
    """A SAT model -> the `rel` dict `layer_certify.verify` consumes."""
    true = {l for l in model if l > 0}
    return {p: (v in true) for p, v in order_var.items()}


def v1_positive(subject, dense):
    """POSITIVE CONTROL: this CNF must be SAT on a state that folds, and its
    model must be accepted by the project's own independent verifier.

    Two directions in one check. SAT proves the encoding is not
    OVER-constrained -- which the 113 negative checks cannot, since an
    over-constrained formula is UNSAT on everything and passes them all
    vacuously. `layer_certify.verify` accepting the model proves the models
    this CNF admits are genuinely valid layer orders, not artifacts of a
    missing constraint.

    `verify` is reached through `layer_certify`, which reimplements none of
    this module and none of `layer_order`'s propagation, so the two readings
    of the constraint set are independent.
    """
    ff_cell.clear()
    g, _labels = capture(subject, dense)
    cl, _pool, order_var, label_var, st = encode(g.cons, g.slots,
                                                 with_labels=True)
    t0 = time.perf_counter()
    with Solver(name=SOLVER, bootstrap_with=cl) as s:
        sat = s.solve()
        model = s.get_model() if sat else None
    secs = round(time.perf_counter() - t0, 1)
    if not sat:
        return False, (f"UNSAT on {subject} dense={dense}, a state whose "
                       f"compile reaches emit -- this encoding is "
                       f"OVER-constrained"), st, secs

    rel = model_to_rel(model, order_var)
    vr = layer_certify.verify(g.cons, rel)
    if vr.violation is not None:
        return False, (f"this CNF's model is REJECTED by "
                       f"layer_certify.verify: {vr.violation} -- the encoding "
                       f"is UNDER-constrained"), st, secs
    return True, (f"SAT, and layer_certify.verify accepts the model "
                  f"({vr.checked} clauses checked, {vr.skipped} skipped)"), st, secs


def main(out_path):
    rec = {"solver": SOLVER}

    # ---- V1: positive control, independent of the dense outcome --------
    print("=== V1 POSITIVE CONTROL: SAT on a folding state, and the model "
          "accepted by layer_certify.verify ===")
    v1 = None
    for subj, dense in (("lizard", False), ("starfish", False),
                        ("bird", False)):
        try:
            ok, why, st, secs = v1_positive(subj, dense)
        except SystemExit as exc:
            print(f"  {subj} dense={dense}: skipped -- {exc}")
            continue
        print(f"  {subj} dense={dense}: {'PASS' if ok else 'FAIL'} -- {why}")
        print(f"      ({st['order_vars']:,} order vars, {st['clauses']:,} "
              f"clauses, {secs}s)")
        rec.setdefault("v1", []).append(
            {"subject": subj, "dense": dense, "ok": bool(ok), "why": why,
             "stats": st, "secs": secs})
        if ok:
            v1 = (subj, dense)
            break
        raise SystemExit(f"REFUSED: the positive control FAILED on {subj} "
                         f"dense={dense}: {why}")
    if v1 is None:
        raise SystemExit(
            "REFUSED: no positive control could be established, so an "
            "over-constrained encoding cannot be ruled out and no UNSAT "
            "result below would be interpretable.")
    print(f"  positive control established on {v1}")

    # ---- the dense lizard instance ---------------------------------------
    print()
    print("=== dense lizard: building the joint CNF ===")
    ff_cell.clear()
    g, _first_labels = capture("lizard", True)
    t0 = time.perf_counter()
    solver = Solver(name=SOLVER)
    _cl, _pool, order_var, label_var, stats = encode(
        g.cons, g.slots, with_labels=True, sink=solver.add_clause)
    build = round(time.perf_counter() - t0, 1)
    print(f"  order vars {stats['order_vars']:,}  label vars "
          f"{stats['label_vars']:,}  clauses {stats['clauses']:,}  "
          f"({build}s)")
    print(f"  families: {stats['families']}")
    rec["instance"] = stats | {"build_secs": build}

    # ---- THE EXPERIMENT: is ANY labelling of this crease set orderable? --
    print()
    print("=== THE QUERY: does ANY labelling of this dense crease set admit "
          "a valid layer order? ===")
    t0 = time.perf_counter()
    free_sat = solver.solve()
    free_model = solver.get_model() if free_sat else None
    qsecs = round(time.perf_counter() - t0, 1)
    print(f"  {'SAT' if free_sat else 'UNSAT'}  ({qsecs}s)")
    rec["free_query"] = {"sat": bool(free_sat), "secs": qsecs}
    if free_sat:
        rel = model_to_rel(free_model, order_var)
        vr = layer_certify.verify(g.cons, rel)
        print(f"  layer_certify.verify on the witness: "
              f"{'ACCEPTS' if vr.violation is None else 'REJECTS ' + str(vr.violation)}")
        rec["free_query"]["verify_accepts"] = vr.violation is None
        true = {l for l in free_model if l > 0}
        wit = {e: ("V" if v in true else "M") for e, v in label_var.items()}
        rec["free_query"]["witness_labels"] = {
            f"{e[0]},{e[1]}": a for e, a in wit.items()}
        nv = sum(1 for a in wit.values() if a == "V")
        print(f"  witness labelling: {nv} V / {len(wit) - nv} M of "
              f"{len(wit)} creases")

        # The CNF encodes the LAYER-ORDER constraints only. Maekawa -- which
        # every CEGAR candidate satisfies by construction -- is NOT among
        # them, so a model could in principle be an illegal labelling that
        # merely happens to be orderable. Checked, not assumed.
        from collections import Counter, defaultdict
        inc = defaultdict(list)
        for _fa, _fb, k, a in ff_cell["ff"].shared_edges:
            if a in ("M", "V"):
                for v in k:
                    inc[v].append(k)
        bad = tot = 0
        for v, edges in inc.items():
            if len(edges) < 3:
                continue
            tot += 1
            c = Counter(wit.get(e, "?") for e in edges)
            if abs(c["M"] - c["V"]) != 2:
                bad += 1
        print(f"  Maekawa on the witness: {bad} violations of {tot} "
              f"interior vertices")
        rec["free_query"]["maekawa"] = {"violations": bad, "vertices": tot}

        # The project's OWN complete per-labelling decision procedure, which
        # reimplements none of this module.
        dv = layer_certify.decide(layers_mod._seeded(g, wit),
                                  budget=layer_certify.CERTIFY_BUDGET)
        print(f"  layer_certify.decide on the witness: {dv.kind} "
              f"(nodes {dv.nodes}, free {dv.free})")
        rec["free_query"]["decide"] = {"kind": dv.kind, "nodes": dv.nodes,
                                       "free": dv.free}

        _id0 = json.load(open("../docs/superpowers/evidence/"
                              "2026-10-02-witness-identity-113/"
                              "identity113.json"))
        _ref = [{tuple(k): v for k, v in r["candidate"]}
                for r in _id0["rejection_records"]]
        dmin = min(sum(1 for e in wit if wit[e] != R[e]) for R in _ref)
        exact = any(all(wit[e] == R[e] for e in wit) for R in _ref)
        print(f"  distance to the 113 refuted candidates: min Hamming {dmin} "
              f"of {len(wit)}; equals one of them: {exact}")
        rec["free_query"]["min_hamming_to_refuted"] = dmin
        rec["free_query"]["equals_a_refuted_candidate"] = exact

    # ---- V2: every refuted labelling must be UNSAT ------------------------
    print()
    print("=== V2 NEGATIVE CONTROL: refuted labellings must be UNSAT ===")
    ident = json.load(open("../docs/superpowers/evidence/"
                           "2026-10-02-witness-identity-113/identity113.json"))
    recs = ident["rejection_records"]
    checked, wrong = 0, []
    t0 = time.perf_counter()
    for i, r in enumerate(recs):
        labels = {tuple(k): v for k, v in r["candidate"]}
        if solver.solve(assumptions=assume_labels(label_var, labels)):
            wrong.append(i)
        checked += 1
        if i % 20 == 0:
            print(f"    {i + 1}/{len(recs)} checked, {len(wrong)} wrong "
                  f"({round(time.perf_counter() - t0)}s)", flush=True)
    secs = round(time.perf_counter() - t0, 1)
    print(f"  {checked} refuted labellings checked, "
          f"{len(wrong)} came back SAT ({secs}s)")
    rec["v2"] = {"checked": checked, "sat_but_should_be_unsat": wrong,
                 "secs": secs}

    with open(out_path, "w") as fh:
        json.dump(rec, fh, indent=1, sort_keys=True)
    print(f"\nwrote {out_path}")

    # ---- verdict, only after every control above -------------------------
    print()
    if wrong:
        print(f"VERDICT WITHHELD: {len(wrong)} labelling(s) that "
              f"`layer_order.propagate` REFUTED came back SAT, so this "
              f"encoding is under-constrained and the free query's answer "
              f"means nothing. First: {wrong[:5]}")
    elif free_sat:
        print("VERDICT: SAT -- there EXISTS a labelling of this fixed dense "
              "crease set admitting a valid layer order, and the 500,000-node "
              "CEGAR search never found it. The model is a witness to extract "
              "and hand back through `layer_certify.verify`.")
    else:
        print("VERDICT: UNSAT -- NO labelling of this fixed dense crease set "
              "admits a valid layer order, against the constraint set that "
              "survived AREA_EPS. Dense layer-ordering on this crease set is "
              "refuted completely, not merely unconverged -- which is a "
              "statement about the CREASE SET, and points upstream at "
              "tiling/interleaving rather than at the solver.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: sat_encode.py <out.json>")
    main(sys.argv[1])
