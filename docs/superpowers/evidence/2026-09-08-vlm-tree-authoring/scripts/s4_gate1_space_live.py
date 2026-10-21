"""S4 gate 1: is the anatomy-preserving variant space LIVE?

THE QUESTION. §2f measured that two authorings of the same mesh -- both
anatomically exact -- differ enough in micro-structure to flip packability,
while `compile_tree` itself is deterministic. If that is true, packable
variants should already lie inside the anatomy-preserving neighbourhood of the
trees we have. This asks whether they do, by RANDOM sampling only: no ranking,
no guidance, no lever. That is deliberately the weakest possible search, so a
positive result is attributable to the SPACE rather than to any cleverness.

THE INVARIANT, CHECKED AND NOT ASSUMED. A variant is admissible only if it
preserves the anatomy exactly:

    * the same leaf SET (by original id), and
    * the same leaf-to-leaf distance for every leaf pair.

That is strictly stronger than the spec's wording ("no node's length changes,
no leaf added or removed") and it is the level that actually means "the same
animal". Every variant is checked before it is compiled and the run ABORTS on a
violation rather than reporting a number nobody can trust.

⚠ `rescue_ladder.contract_slivers` is therefore NOT in this space. It preserves
every surviving edge's length verbatim and never deletes a leaf -- so it passes
the spec's literal wording -- but it DISCARDS the contracted node's own length,
which shortens the leaf-to-leaf paths. That is an anatomy change wearing a
length-preservation costume, and it is exactly the kind of thing this check
exists to catch.

THE GENERATORS, all three already owned by this repository:

    order    `rescue_ladder.order_variants` -- ids and lengths untouched, only
             the list order the packer seeds placement from
    root     `rescue_ladder.rehome`         -- topologically a no-op; the edge
             length multiset is identical, only re-attributed across ids
    flatten  `tree_flatten.flatten_tree`    -- lossless degree-2 collapse,
             already verified max |delta| = 0 over 18 trees / 382 leaf pairs

plus their compositions. No fourth lever is proposed; CLAUDE.md §1.2 forbids
one without reading the structural ruling first.
"""
from __future__ import annotations
import json, os, random, sys, time

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

BUDGET = 32          # breadth-over-depth: a wide shallow sample, not a ladder
SEED = 20260909
ORDER = ["dog","cat","horse","rabbit","guinea_pig","elephant","lizard","frog","bird",
         "bat","dolphin","starfish","octopus","crab","spider","scorpion","ant"]


def signature(tn, index_map=None):
    """(leaf id set, leaf-pair distances) in ORIGINAL ids.

    `flatten_tree` renumbers, so its `index_map` (new -> old) is applied before
    comparing. Without that every flattened variant would read as a different
    animal and the check would reject the one generator we already proved
    lossless -- a false alarm that looks exactly like a real one.
    """
    d = TF.leaf_distances(tn)
    if index_map:
        # `flatten_tree`'s index_map is OLD -> NEW with STRING keys. Reading it
        # the other way round silently maps two surviving leaves onto one id and
        # reports "leaf set changed: 5 vs 6" -- which is what this probe did on
        # its first run, and it accused a tool that was behaving correctly.
        back = {int(v): int(k) for k, v in index_map.items()}
        d = {tuple(sorted((back.get(a, a), back.get(b, b)))): v
             for (a, b), v in d.items()}
    leaves = sorted({i for pair in d for i in pair})
    return tuple(leaves), {k: round(float(v), 9) for k, v in sorted(d.items())}


def admissible(base_sig, tn, index_map=None):
    lv, dd = signature(tn, index_map)
    if lv != base_sig[0]:
        return False, f"leaf set changed: {len(lv)} vs {len(base_sig[0])}"
    if dd != base_sig[1]:
        worst = max((abs(dd[k] - base_sig[1][k]) for k in base_sig[1] if k in dd),
                    default=float("inf"))
        return False, f"leaf distances changed, max |delta| = {worst:.3e}"
    return True, ""


def selftest_invariant(tn):
    """The checker must REJECT real anatomy changes, or its passes mean nothing.

    Run as a precondition of the sweep, not as an optional test, so the headline
    number can never be produced by a dead check. Three probes: a length nudged
    on one leaf, a leaf deleted, and the identity -- which must still pass.
    """
    import copy
    sig = signature(tn)
    leaves = {n["id"] for n in tn} - {n["parent_id"] for n in tn if n["parent_id"] is not None}

    nudged = copy.deepcopy(tn)
    for n in nudged:
        if n["id"] in leaves:
            n["length"] = round(float(n["length"]) * 1.10, 6)
            break
    ok, _ = admissible(sig, nudged)
    assert not ok, "checker ACCEPTED a 10% length change on a leaf"

    victim = sorted(leaves)[-1]
    pruned = [copy.deepcopy(n) for n in tn if n["id"] != victim]
    ok, _ = admissible(sig, pruned)
    assert not ok, "checker ACCEPTED a deleted leaf"

    ok, why = admissible(sig, copy.deepcopy(tn))
    assert ok, f"checker REJECTED the identity: {why}"


def enumerate_variants(tn, sp):
    """[(name, nodes, pairs, index_map)] -- identity first, then the space."""
    out = [("identity", tn, sp, None)]

    def flat(name, nodes, pairs):
        f = TF.flatten_tree(nodes, pairs)
        if f and f.get("tree_nodes") and len(f["tree_nodes"]) < len(nodes):
            out.append((f"flatten+{name}", f["tree_nodes"], f["symmetric_pairs"],
                        f.get("index_map")))

    flat("identity", tn, sp)
    for nm, cand in RL.order_variants(tn, sp):
        out.append((f"order:{nm}", cand, sp, None))
        flat(f"order:{nm}", cand, sp)
    # Every node is a candidate root. The engine takes mNodes.front() as the
    # dangle root, so each choice is a different facet-ordering problem -- the
    # lever PRs #107-#118 measured. `normalize_variants` caps this at
    # MAX_NORMALIZE_HUBS - 1 = 2; that cap is a ladder budget, not a property
    # of the space, and this probe is measuring the space.
    for n in tn:
        if n.get("parent_id") is None:
            continue
        rh = RL.rehome(tn, n["id"])
        if rh is None:
            continue
        out.append((f"root:{n['id']}", rh, sp, None))
        flat(f"root:{n['id']}", rh, sp)
    return out


def main():
    D = f"{E}/data"
    raw = {}
    for f in ("frame_fix_raw.json", "frame_fix15_raw.json"):
        for r in json.load(open(f"{D}/{f}")):
            if r.get("tree"):
                raw[r["subject"]] = r

    rows, t0 = [], time.time()
    for s in ORDER:
        t = raw[s]["tree"]
        nodes = L.to_tuples(t); lset = set(B.leaves_of(nodes))
        keep = [(a, b) for p in (t.get("pairs") or []) if len(p) == 2
                for a, b in [p] if a in lset and b in lset]
        tn, sp, _ = B.metric_tree(nodes, keep)
        base_sig = signature(tn)
        selftest_invariant(tn)          # precondition, never optional

        variants = enumerate_variants(tn, sp)
        checked = []
        for nm, v, vp, im in variants:
            ok, why = admissible(base_sig, v, im)
            if not ok:
                raise SystemExit(f"INVARIANT VIOLATED {s}/{nm}: {why}")
            checked.append((nm, v, vp))

        base_ok = compile_tree(tn, sp, timeout=60)[0] == "ok"
        rng = random.Random(f"{SEED}:{s}")
        pool = checked[1:]                      # identity is the baseline, not a variant
        rng.shuffle(pool)
        sample = pool[:BUDGET]
        hit, hit_at, tried = None, None, 0
        for i, (nm, v, vp) in enumerate(sample, 1):
            tried = i
            if compile_tree(v, vp, timeout=60)[0] == "ok":
                hit, hit_at = nm, i
                break
        # A failure at budget K is ambiguous: it may mean the space holds no
        # packable variant, or only that K was too small. Those are completely
        # different answers -- the first is a real negative about the tree, the
        # second is a statement about our patience -- so exhaust the remainder
        # and say which. It costs a few hundred in-process compiles.
        exhausted = None
        if hit is None:
            exhausted = True
            for nm, v, vp in pool[len(sample):]:
                if compile_tree(v, vp, timeout=60)[0] == "ok":
                    exhausted = False
                    hit = f"BEYOND_BUDGET:{nm}"
                    break

        rows.append(dict(subject=s, n_nodes=len(tn), space=len(checked),
                         baseline_packs=base_ok, budget=min(BUDGET, len(pool)),
                         tried=tried, packed=(hit_at is not None),
                         first_hit=hit, hit_at=hit_at,
                         no_packable_variant_in_space=exhausted))
        if hit_at:
            verdict = f"PACKS via {hit} @{hit_at}"
        elif exhausted:
            verdict = "NO PACKABLE VARIANT (whole space exhausted)"
        else:
            verdict = f"missed at K={BUDGET}, but one exists: {hit}"
        print(f"  {s:11} space={len(checked):>4} base={'ok ' if base_ok else 'err'} "
              f"tried={tried:>3} -> {verdict}", flush=True)

    json.dump(rows, open(f"{D}/s4_gate1.json", "w"), indent=1)
    base = sum(1 for r in rows if r["baseline_packs"])
    won = sum(1 for r in rows if r["packed"])
    print(f"\nbaseline (attempt 0)        {base}/17")
    print(f"random variant search K<={BUDGET}  {won}/17")
    print(f"mean space size {sum(r['space'] for r in rows)/len(rows):.1f} variants/subject")
    hits = [r["hit_at"] for r in rows if r["hit_at"]]
    if hits:
        print(f"attempts to first pack: min {min(hits)}, median "
              f"{sorted(hits)[len(hits)//2]}, max {max(hits)}")
    ex = [r["subject"] for r in rows if r.get("no_packable_variant_in_space")]
    near = [r["subject"] for r in rows
            if not r["packed"] and r.get("no_packable_variant_in_space") is False]
    print(f"whole space exhausted, still no pack: {len(ex)}/17 {ex}")
    print(f"missed at K but a packable variant EXISTS: {len(near)}/17 {near}")
    print(f"elapsed {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
