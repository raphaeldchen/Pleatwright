"""Does an ANATOMY-PRESERVING uniform rescale rescue these trees?

Uniform scale multiplies every edge by the same k, so every proportion, every
ratio and every symmetry survives exactly -- it is the same free `scale`
parameter body_plans.template(name, s) already exposes, and it is the ONE
length change that CLAUDE.md's "do not rescale measured proportions" rule does
not forbid, because it changes no proportion at all.

Target span 0.70 = body_plans' quadruped span at scale 1.0.
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
H = "<repo>/mcp_harness"
sys.path.insert(0, H); sys.path.insert(0, os.path.join(H, "tests"))
os.chdir(H)
from runner import compile_tree
from equalize_probe import span

TARGET = 0.70


def main():
    b = json.load(open(os.path.expanduser(
        "~/Downloads/photo_meshes/hand_trees/trees.json")))
    print(f"{'subject':9} {'variant':9} {'span':>6} {'k':>6} "
          f"{'authored':>9} {'scaled':>7}")
    out = []
    for s in ["dog", "cat", "horse", "lizard", "frog", "bird",
              "starfish", "spider", "octopus"]:
        for v in ("faithful", "packable"):
            tn = [dict(n) for n in b["subjects"][s][v]["tree_nodes"]]
            pr = [list(p) for p in b["subjects"][s][v]["symmetric_pairs"]]
            sp = span(tn); k = TARGET / sp
            st0, _ = compile_tree(tn, pr, timeout=60)
            sc = [{**n, "length": round(n["length"] * k, 6)} for n in tn]
            st1, _ = compile_tree(sc, pr, timeout=60)
            out.append(dict(subject=s, variant=v, span=sp, k=round(k, 4),
                            authored=st0, scaled=st1))
            print(f"{s:9} {v:9} {sp:>6} {k:>6.3f} {st0:>9} {st1:>7}",
                  flush=True)
            json.dump(out, open("/tmp/scale_probe.json", "w"), indent=2)
    print(f"\nauthored: {sum(1 for r in out if r['authored']=='ok')}/18    "
          f"uniformly scaled: {sum(1 for r in out if r['scaled']=='ok')}/18")


if __name__ == "__main__":
    main()
