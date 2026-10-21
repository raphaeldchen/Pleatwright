"""S4 wiring: the A/B on the SHIPPED serve path, not on a probe.

Gates 1 and 2 were measured by a standalone search (`s4_gate1_space_live.py`,
`s4_gate2_guidance.py`). This asks the different and harder question: does
`draft_and_compile_full_base` -- the real tool, with the real ladder, the real
proportion barrier and the real annotation -- serve more of the corpus now that
the flatten stage leads?

THE CONTROL IS THE DOCUMENTED ROLLBACK VAR. `IDE_LADDER_STAGES` names the
enabled stage set, so the pre-change ladder is reproducible exactly by listing
the six stages that existed before. Both arms are the same code, the same
trees and the same corpus; only the stage set differs.

WHAT IS CHECKED BESIDES THE RATE. Every serve is read back through
`mesh_to_tree.served_stage`, because the failure mode this wiring risks is not
"no improvement" -- it is a serve that is silently MISLABELLED. An unmarked
stage falls through to STAGE_EXACT, which reads as "the tree AS REQUESTED
packed", ends the drain early and scores attempt0_pack for a restructured
tree, with nothing going red.
"""
from __future__ import annotations
import json, os, sys, time

R = "<repo>"
H = f"{R}/mcp_harness"
E = f"{R}/docs/superpowers/evidence/2026-09-08-vlm-tree-authoring"
sys.path.insert(0, f"{E}/scripts"); sys.path.insert(0, H); sys.path.insert(0, f"{H}/tests")
os.chdir(H)

BEFORE = "order,placement,normalize,jitter,composed,stub"   # the pre-S4/2g ladder
ORDER = ["dog","cat","horse","rabbit","guinea_pig","elephant","lizard","frog","bird",
         "bat","dolphin","starfish","octopus","crab","spider","scorpion","ant"]


def build(raw, s):
    import loop_lib as L, hand_trees_build as B
    t = raw[s]["tree"]
    nodes = L.to_tuples(t); lset = set(B.leaves_of(nodes))
    keep = [(a, b) for p in (t.get("pairs") or []) if len(p) == 2
            for a, b in [p] if a in lset and b in lset]
    return B.metric_tree(nodes, keep)[:2]


def arm(raw, stages_env):
    import importlib
    if stages_env is None:
        os.environ.pop("IDE_LADDER_STAGES", None)
    else:
        os.environ["IDE_LADDER_STAGES"] = stages_env
    import server, mesh_to_tree as m2t
    importlib.reload(server)
    out = {}
    for s in ORDER:
        tn, sp = build(raw, s)
        fold = server.draft_and_compile_full_base(tn, sp)
        ok = isinstance(fold, str) and not fold.startswith("ERROR:")
        out[s] = (ok, m2t.served_stage(fold) if ok else None)
    return out


def main():
    D = f"{E}/data"
    raw = {}
    for f in ("frame_fix_raw.json", "frame_fix15_raw.json"):
        for r in json.load(open(f"{D}/{f}")):
            if r.get("tree"):
                raw[r["subject"]] = r

    t0 = time.time()
    before = arm(raw, BEFORE)
    after = arm(raw, None)

    print(f"{'subject':12}{'before':>22}{'after':>22}")
    for s in ORDER:
        b, a = before[s], after[s]
        print(f"  {s:12}{(str(b[1]) if b[0] else 'NOT SERVED'):>20}"
              f"{(str(a[1]) if a[0] else 'NOT SERVED'):>22}"
              + ("   <-- gained" if a[0] and not b[0] else
                 "   <-- LOST" if b[0] and not a[0] else ""))
    nb = sum(1 for s in ORDER if before[s][0])
    na = sum(1 for s in ORDER if after[s][0])
    print(f"\nserved: before {nb}/17   after {na}/17")
    lost = [s for s in ORDER if before[s][0] and not after[s][0]]
    print(f"regressions: {lost if lost else 'none'}")
    flat = [s for s in ORDER if after[s][0] and after[s][1] == "flatten"]
    print(f"served VIA the flatten stage: {len(flat)} {flat}")
    mis = [s for s in ORDER if after[s][0] and after[s][1] is None]
    print(f"serves with an unreadable stage: {mis if mis else 'none'}")
    json.dump({"before": {k: list(v) for k, v in before.items()},
               "after": {k: list(v) for k, v in after.items()}},
              open(f"{D}/s4_serve_ab.json", "w"), indent=1)
    print(f"elapsed {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
