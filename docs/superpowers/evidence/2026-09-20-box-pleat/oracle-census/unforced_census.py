"""How much does completing `layer_order` buy? Two DIFFERENT deficits.

(A) SEARCH WIDTH -- pairs in `cons.pairs` left unforced at the propagation
    fixpoint. These are the variables Akitaya-Demaine-Ku's satisfiability
    result decides by DFS backtracking and we leave as None. Reported per
    subject and, because the total-order requirement is per arrangement
    CELL, per cell: `max_cell_free` is the widest local search.

(B) NON-CONFLUENCE EXPOSURE -- whether the fixpoint itself depends on
    traversal order. `_close_transitively` writes a pair only when it is
    currently unknown, so two admissible chains implying opposite values
    never cross-check. This re-runs propagation under different worklist
    disciplines (LIFO is shipped; FIFO and two seeded-random orders here)
    and reports pairs whose VALUE disagrees, pairs only one order decides,
    and any VERDICT flip.

(A) is fixed by adding search. (B) is fixed by making propagation
confluent (cross-check instead of write-if-unknown) -- the fix spec
2026-09-22-pleat-reassignment-design.md §10 already names as the correct
one and defers. A subject can read 0 on (A) and still be wrong via (B),
which is why both are here.

⚠ LIMIT OF (B), and it is narrower than "confluent". The variants below
permute the transitive closure's worklist discipline and the order its
neighbour sets are walked. They do NOT permute the order `_propagate`
applies the other families (equalities, tacos), and they are three orders,
not all orders. Non-confluence is PROVEN to be live on other geometry:
spec §10 flips `mesh-humanoid` flip-set (8, 9, 21) by permuting the OLD
rule's cover order. So a 0 here means "no exposure found on box-pleat
geometry under these three orders", never "this rule is confluent".
"""
from __future__ import annotations
import json, random, sys, time
from itertools import combinations

import flat_fold
import layer_order as LO
from box_pleat.compile import compile_tree

RULE6 = "../docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/data/rule6_serve.json"
OUT = sys.argv[1]
ALL = ["starfish", "bird", "lizard", "horse", "octopus", "frog",
       "guinea_pig", "dog"]
ORDER = sys.argv[2].split(",") if len(sys.argv) > 2 else ALL

_real_close = LO._close_transitively


def _variant(mode: str, seed: int = 0):
    """`_close_transitively` with the worklist discipline swapped.

    A verbatim copy of the shipped body except for how `pending` is
    drained and (for mode='rand') the order neighbour sets are walked.
    The WRITE GUARD is untouched, so any difference this exposes is
    non-confluence of the shipped rule, not a different rule."""
    def close(rel, get, put, covers_of, up, down):
        rng = random.Random(seed)
        pending = []

        def note(x, y):
            if y in up.setdefault(x, set()):
                return
            up[x].add(y)
            down.setdefault(y, set()).add(x)
            pending.append((x, y))

        for (lo, hi), v in list(rel.items()):
            note(lo, hi) if v else note(hi, lo)
        changed = False
        while pending:
            if mode == "fifo":
                x, y = pending.pop(0)
            elif mode == "rand":
                x, y = pending.pop(rng.randrange(len(pending)))
            else:
                x, y = pending.pop()
            cx, cy = covers_of.get(x, ()), covers_of.get(y, ())
            cxy = set(cx) & set(cy)
            ups, downs = list(up.get(y, ())), list(down.get(x, ()))
            if mode == "rand":
                rng.shuffle(ups); rng.shuffle(downs)
            for z in ups:
                if covers_of.get(z, set()) & cxy and get(LO._lit(x, z)) is None:
                    changed |= put(LO._lit(x, z), True,
                                   LO.Prov(f"transitivity {x}>{y}>{z}",
                                           faces=(x, y, z)),
                                   srcs=(LO._lit(x, y), LO._lit(y, z)))
                    note(x, z)
            for w in downs:
                if covers_of.get(w, set()) & cxy and get(LO._lit(w, y)) is None:
                    changed |= put(LO._lit(w, y), True,
                                   LO.Prov(f"transitivity {w}>{x}>{y}",
                                           faces=(w, x, y)),
                                   srcs=(LO._lit(w, x), LO._lit(x, y)))
                    note(w, y)
        return changed
    return close


def run(cons, close):
    LO._close_transitively = close
    try:
        return LO.propagate(cons), None
    except LO.LayerContradiction as exc:
        return None, str(exc)
    finally:
        LO._close_transitively = _real_close


def main():
    entries = {e["subject"]: e for e in json.load(open(RULE6))}
    rows = []
    for s in ORDER:
        t0 = time.time()
        e = entries[s]
        res = compile_tree(e["requested"], e["pairs"])
        if res.stage_reached != "emit":
            print(f"{s:11s} stop@{res.stage_reached}", flush=True); continue
        ff = flat_fold.flat_fold(res.fold)
        cons, _ = LO.constraints_for(ff)

        # (A) search width, shipped LIFO order
        rel, contra = run(cons, _real_close)
        row = {"subject": s, "faces": len(ff.faces), "cells": len(cons.covers),
               "pairs": len(cons.pairs), "baseline_contradiction": contra}
        if rel is not None:
            free = set(cons.pairs) - set(rel)
            row["forced"] = len(rel)
            row["free"] = len(free)
            row["pct_free"] = round(100 * len(free) / max(len(cons.pairs), 1), 2)
            per_cell = [sum(1 for pr in combinations(sorted(c), 2) if pr in free)
                        for c in cons.covers]
            row["max_cell_free"] = max(per_cell, default=0)
            row["cells_with_free"] = sum(1 for n in per_cell if n)
            row["max_cover"] = max((len(c) for c in cons.covers), default=0)

        # (B) non-confluence exposure
        row["variants"] = {}
        for name, close in (("fifo", _variant("fifo")),
                            ("rand1", _variant("rand", 1)),
                            ("rand2", _variant("rand", 2))):
            rel2, contra2 = run(cons, close)
            v = {"contradiction": contra2}
            if rel is not None and rel2 is not None:
                both = set(rel) & set(rel2)
                v["disagree"] = sum(1 for p in both if rel[p] != rel2[p])
                v["only_shipped"] = len(set(rel) - set(rel2))
                v["only_variant"] = len(set(rel2) - set(rel))
            v["verdict_flip"] = (contra is None) != (contra2 is None)
            row["variants"][name] = v

        row["secs"] = round(time.time() - t0, 1)
        rows.append(row)
        json.dump(rows, open(OUT, "w"), indent=1)
        flips = [k for k, v in row["variants"].items() if v["verdict_flip"]]
        dis = max((v.get("disagree", 0) for v in row["variants"].values()), default=0)
        print(f"{s:11s} faces={row['faces']:5d} pairs={row['pairs']:6d} "
              f"free={row.get('free','-'):>6} ({row.get('pct_free','-')}%) "
              f"max_cell_free={row.get('max_cell_free','-')} "
              f"disagree<={dis} flips={flips or '-'} {row['secs']}s", flush=True)


main()
