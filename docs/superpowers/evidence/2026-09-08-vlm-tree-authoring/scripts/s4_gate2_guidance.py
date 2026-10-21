"""S4 gate 2: does GUIDED variant choice beat random at equal budget?

PRE-REGISTRATION. The rule below was fixed by §2g's win table -- flatten+reorder
6, reorder 4, flatten 2, re-root 0 -- and by nothing else. It is written here
BEFORE the held-out set is touched, and it is not tuned afterwards. Testing it
on the uniform corpus that suggested it would be circular, so the test set is
the run-1 and run-2 authorings (`run17_raw.json` mode none, and
`run17_replicate_raw.json`): 34 trees, different authorings of the same 17
subjects, never used to pick the rule.

    THE RULE. Try variant families in this order, and within a family keep the
    enumeration order:

        1. flatten + reorder
        2. reorder alone
        3. flatten alone
        4. re-root (and flatten + re-root)

Note the rule is even better motivated than the raw counts suggest. Random
sampling draws re-root variants MOST often -- every non-root node is a
candidate, so roots are the majority of the space -- and they still won zero
times. Per draw, the flatten/reorder families beat roots by more than 6-to-0.

THE CONTROL is the same space, the same budget, the same trees; only the ORDER
of attempts differs. Both arms are deterministic given the seed. If guidance
does not beat random here, the search ships and the guidance does not.

INVARIANT. Identical to gate 1, and checked the same way: same leaf set, same
leaf-to-leaf distance for every pair, with `selftest_invariant` run as a
precondition so the numbers cannot come from a dead checker.
"""
from __future__ import annotations
import copy, json, os, random, sys, time

R = "<repo>"
H = f"{R}/mcp_harness"
E = f"{R}/docs/superpowers/evidence/2026-09-08-vlm-tree-authoring"
sys.path.insert(0, f"{E}/scripts"); sys.path.insert(0, H); sys.path.insert(0, f"{H}/tests")
os.chdir(H)
from runner import compile_tree
import rescue_ladder as RL
import tree_flatten as TF
import loop_lib as L
import hand_trees_build as B

SEED = 20260909
BUDGETS = (4, 8, 12, 16, 24, 32)


def signature(tn, index_map=None):
    d = TF.leaf_distances(tn)
    if index_map:                      # index_map is OLD -> NEW, string keys
        back = {int(v): int(k) for k, v in index_map.items()}
        d = {tuple(sorted((back.get(a, a), back.get(b, b)))): v
             for (a, b), v in d.items()}
    leaves = sorted({i for pair in d for i in pair})
    return tuple(leaves), {k: round(float(v), 9) for k, v in sorted(d.items())}


def admissible(base_sig, tn, index_map=None):
    lv, dd = signature(tn, index_map)
    return (lv == base_sig[0] and dd == base_sig[1])


def selftest_invariant(tn):
    sig = signature(tn)
    leaves = {n["id"] for n in tn} - {n["parent_id"] for n in tn
                                      if n["parent_id"] is not None}
    nudged = copy.deepcopy(tn)
    for n in nudged:
        if n["id"] in leaves:
            n["length"] = round(float(n["length"]) * 1.10, 6)
            break
    assert not admissible(sig, nudged), "checker ACCEPTED a length change"
    victim = sorted(leaves)[-1]
    assert not admissible(sig, [n for n in tn if n["id"] != victim]), \
        "checker ACCEPTED a deleted leaf"
    assert admissible(sig, copy.deepcopy(tn)), "checker REJECTED the identity"


def family(name):
    if name.startswith("flatten+order"):
        return 0
    if name.startswith("order"):
        return 1
    if name.startswith("flatten+identity"):
        return 2
    return 3                                   # root, flatten+root


def enumerate_variants(tn, sp):
    out = []

    def flat(name, nodes, pairs):
        f = TF.flatten_tree(nodes, pairs)
        if f and f.get("tree_nodes") and len(f["tree_nodes"]) < len(nodes):
            out.append((f"flatten+{name}", f["tree_nodes"], f["symmetric_pairs"],
                        f.get("index_map")))

    flat("identity", tn, sp)
    for nm, cand in RL.order_variants(tn, sp):
        out.append((f"order:{nm}", cand, sp, None))
        flat(f"order:{nm}", cand, sp)
    for n in tn:
        if n.get("parent_id") is None:
            continue
        rh = RL.rehome(tn, n["id"])
        if rh is None:
            continue
        out.append((f"root:{n['id']}", rh, sp, None))
        flat(f"root:{n['id']}", rh, sp)
    return out


def first_hit(seq, cap):
    for i, (nm, v, vp) in enumerate(seq[:cap], 1):
        if compile_tree(v, vp, timeout=60)[0] == "ok":
            return i, nm
    return None, None


def trees_from(path, mode=None):
    out = {}
    for r in json.load(open(path)):
        if r.get("tree") and (mode is None or r["mode"] == mode):
            out[r["subject"]] = r["tree"]
    return out


def main():
    D = f"{E}/data"
    sets = {"run1": trees_from(f"{D}/run17_raw.json", "none"),
            "run2": trees_from(f"{D}/run17_replicate_raw.json")}

    rows, t0 = [], time.time()
    for setname, trees in sets.items():
        for s, t in sorted(trees.items()):
            nodes = L.to_tuples(t); lset = set(B.leaves_of(nodes))
            keep = [(a, b) for p in (t.get("pairs") or []) if len(p) == 2
                    for a, b in [p] if a in lset and b in lset]
            tn, sp, _ = B.metric_tree(nodes, keep)
            base_sig = signature(tn)
            selftest_invariant(tn)

            pool = []
            for nm, v, vp, im in enumerate_variants(tn, sp):
                if not admissible(base_sig, v, im):
                    raise SystemExit(f"INVARIANT VIOLATED {setname}/{s}/{nm}")
                pool.append((nm, v, vp))

            rnd = list(pool)
            random.Random(f"{SEED}:{setname}:{s}").shuffle(rnd)
            gd = sorted(pool, key=lambda x: family(x[0]))   # stable within family

            base_ok = compile_tree(tn, sp, timeout=60)[0] == "ok"
            ri, rn = first_hit(rnd, max(BUDGETS))
            gi, gn = first_hit(gd, max(BUDGETS))
            rows.append(dict(set=setname, subject=s, space=len(pool),
                             baseline=base_ok, rand_at=ri, rand_via=rn,
                             guided_at=gi, guided_via=gn))
            print(f"  {setname} {s:11} space={len(pool):>3} base="
                  f"{'ok ' if base_ok else 'err'} rand@{str(ri):>4} "
                  f"guided@{str(gi):>4}  {gn or ''}", flush=True)

    json.dump(rows, open(f"{D}/s4_gate2.json", "w"), indent=1)
    n = len(rows)
    print(f"\nheld-out trees: {n} ({len(sets['run1'])} run1 + {len(sets['run2'])} run2)")
    print(f"baseline attempt-0: {sum(1 for r in rows if r['baseline'])}/{n}")
    print(f"\n{'K':>4}{'random':>10}{'guided':>10}")
    for K in BUDGETS:
        rr = sum(1 for r in rows if r["rand_at"] and r["rand_at"] <= K)
        gg = sum(1 for r in rows if r["guided_at"] and r["guided_at"] <= K)
        print(f"{K:>4}{rr:>7}/{n:<2}{gg:>7}/{n:<2}")
    ra = [r["rand_at"] for r in rows if r["rand_at"]]
    ga = [r["guided_at"] for r in rows if r["guided_at"]]
    if ra and ga:
        print(f"\nattempts to first pack -- random  median {sorted(ra)[len(ra)//2]}, max {max(ra)}")
        print(f"                          guided  median {sorted(ga)[len(ga)//2]}, max {max(ga)}")
    print(f"elapsed {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
