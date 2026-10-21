"""Spider, scorpion, crab x 3 rolls through the PRODUCTION gated pipeline, to
measure the last-resort repair turn (spec 2026-09-12-vlm-pack-repair-design §9).

Each roll is a fresh authoring (no temperature lever exists on this model), so
the headline is the 9-row table, not a single number. Expectation stated before
running: spider (10 -> 9 after a head merge) improves; crab (11 -> 10) and
scorpion (12 -> 11) mostly still fail. A DECLINE on a real appendage is a
success for this slice.

Inputs are the committed arm-C mesh renders; `vlm_render.render_mesh_views` is
stubbed to pass them through (the .glb binaries are not in-repo). Everything
downstream -- authoring, the whole rescue ladder, the repair turn, the compile
-- is the real serve path. Resumable: rows already in the output are skipped.
"""
from __future__ import annotations
import argparse, asyncio, json, os, sys, time

S = os.path.dirname(os.path.abspath(__file__))
H = "<repo>/mcp_harness"
sys.path.insert(0, H); sys.path.insert(0, os.path.join(H, "tests"))
os.chdir(H)
import env_config; env_config.load_env()
os.environ["LLM_MAX_TOKENS"] = "64000"

import llm_client, vlm_render, gated_pipeline, tree_authoring as TA

vlm_render.render_mesh_views = lambda mesh_path, out_path, **kw: {"png": mesh_path, "grid": None, "views": []}

SUBJECTS = ["spider", "scorpion", "crab"]
ALL17 = ["dog", "cat", "horse", "lizard", "frog", "bird", "starfish", "spider", "octopus",
         "dolphin", "guinea_pig", "rabbit", "bat", "elephant", "ant", "scorpion", "crab"]
OUT = os.path.join(S, "..", "data", "repair_rolls.json")     # overridden by --tag
WORK = os.path.join(S, "repair_rolls_out")


def _flaps(tree):
    return len(TA.leaves_of(TA.to_tuples(tree))) if tree else None


def _outcome(r, pk, state):
    """Precedence, most specific first (review finding: the served check ran
    first and mislabelled a merged-and-packed roll as "packed", losing the
    fact that a merge happened -- the `packed`/`stage` columns already carry
    the second pack's result, so "merged" still says everything "packed" did,
    plus the merge)."""
    if r and r.get("outcome") == "merged":
        return "merged"
    if pk.get("served"):
        return "packed"
    if state.get("status") == "failed":
        return "authoring_failed"
    if r:
        return r.get("outcome")
    return None


def _row(subject, roll, state, seconds):
    r = state.get("repair") or {}
    pk = state.get("packing") or {}
    authored = r.get("original_tree") or state.get("tree")
    leaf_names = (TA.leaves_of(TA.to_tuples(authored))
                  if isinstance(authored, dict) and "nodes" in authored else None)
    return {"subject": subject, "roll": roll, "status": state.get("status"),
            "authored_flaps": _flaps(authored), "leaf_names": leaf_names,
            "rungs_tried": r.get("rungs_tried"), "stages_tried": r.get("stages_tried"),
            "candidates": r.get("candidates"), "outcome": _outcome(r, pk, state),
            "merged_flap": r.get("merged_flap"), "removed_nodes": r.get("removed_nodes"),
            "model_reason": r.get("model_reason"),
            "refusal": r.get("refusal"), "skipped_because": r.get("skipped_because"),
            "repaired_flaps": r.get("after_flaps") if r.get("outcome") == "merged" else None,
            "packed": bool(pk.get("served")), "stage": pk.get("stage"),
            "seconds": round(seconds, 1), "note": state.get("note")}


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rolls", type=int, default=3)
    ap.add_argument("--only", default=None)
    ap.add_argument("--all", action="store_true", help="the 17-subject corpus")
    ap.add_argument("--until-packed", action="store_true",
                    help="keep rolling a subject until --rolls of its rolls PACKED "
                         "(failed rolls are kept as data); capped by --max-attempts")
    ap.add_argument("--max-attempts", type=int, default=8)
    ap.add_argument("--renders", default="C",
                    help="gridtest/<arm> render set: C = panels named side/front/top "
                         "(every run through full17), D = same grid, panels named by "
                         "mesh axis (XY/ZY/XZ) -- the 2026-09-13 frame fix")
    ap.add_argument("--tag", default=None,
                    help="write data/repair_rolls_<tag>.json and repair_rolls_out_<tag>/ "
                         "instead of resuming the default files")
    ap.add_argument("--shards", type=int, default=1,
                    help="run the subjects as N parallel child processes (each a copy of this "
                         "script with --only and --tag <tag>_<i>), then merge their rows into "
                         "data/repair_rolls_<tag>.json and their outputs into "
                         "repair_rolls_out_<tag>/. Requires --tag. Nothing is shared between "
                         "subjects -- one API call plus a CPU-bound ladder per roll -- so this "
                         "is pure wall-clock: full17_v3 ran 5 shards in 1h55 against 4h27 "
                         "sequential (2026-09-13). Subjects are dealt round-robin over a "
                         "heavy-first order so the arthropods do not share a shard.")
    a = ap.parse_args()
    global OUT, WORK
    if a.tag:
        OUT = os.path.join(S, "..", "data", f"repair_rolls_{a.tag}.json")
        WORK = os.path.join(S, f"repair_rolls_out_{a.tag}")
    subs = a.only.split(",") if a.only else (ALL17 if a.all else SUBJECTS)
    if a.shards > 1:
        if not a.tag:
            sys.exit("--shards needs --tag")
        return await _sharded(a, subs)
    os.makedirs(WORK, exist_ok=True)
    rows = json.load(open(OUT)) if os.path.exists(OUT) else []
    done = {(r["subject"], r["roll"]) for r in rows}
    cfg = llm_client.LLMConfig.from_env()
    print(f"provider={cfg.provider} model={cfg.model} max_tokens={cfg.max_tokens}", flush=True)
    client = llm_client.LLMClient(cfg)
    for s in subs:
        def _packed(subj):
            return sum(1 for r in rows if r["subject"] == subj and r.get("packed"))
        def _attempts(subj):
            return sum(1 for r in rows if r["subject"] == subj)
        k = -1
        while True:
            k += 1
            if a.until_packed:
                if _packed(s) >= a.rolls:
                    break
                if _attempts(s) >= a.max_attempts:
                    print(f"{s:9} CAP: {a.max_attempts} attempts, only {_packed(s)} packed", flush=True)
                    break
            elif k >= a.rolls:
                break
            if (s, k) in done:
                continue
            png = f"{S}/gridtest/{a.renders}/{s}.png"
            t0 = time.time()
            try:
                st = await gated_pipeline.start(png, client=client,
                                                out_dir=os.path.join(WORK, f"{s}_{k}"))
            except Exception as e:                          # noqa: BLE001
                st = {"status": "driver_error", "note": f"{type(e).__name__}: {str(e)[:300]}"}
            # Persist the roll's ARTEFACTS beside its figure: the authored tree,
            # the metric tree the compiler received, the compiled fold and the
            # gate summary. The first run (2026-09-12) saved only tree_round0.png,
            # so its crease patterns could not be shown afterwards.
            try:
                os.makedirs(os.path.join(WORK, f"{s}_{k}"), exist_ok=True)
                with open(os.path.join(WORK, f"{s}_{k}", "state.json"), "w") as fh:
                    json.dump({kk: st.get(kk) for kk in
                               ("status", "tree", "metric_tree", "packing", "repair",
                                "fold", "summary", "note", "subject_guess")}, fh, indent=1)
            except Exception as e:                          # noqa: BLE001
                print(f"  (could not save state for {s}_{k}: {e})", flush=True)
            row = _row(s, k, st, time.time() - t0)
            rows.append(row)
            done.add((s, k))
            json.dump(rows, open(OUT, "w"), indent=1)
            print(f"{s:9} roll {k}: authored={row['authored_flaps']} outcome={row['outcome']} "
                  f"merged={row['merged_flap']} packed={row['packed']} stage={row['stage']} "
                  f"rungs={row['rungs_tried']} {row['seconds']}s", flush=True)
    print(f"\n{len(rows)} rows in {OUT}")


#: Roughly slowest-first, from the full17 / full17_v3 per-subject wall times, so
#: round-robin dealing spreads the long ladders (crab 23 min stub, bat 25 min)
#: across shards instead of stacking them.
HEAVY_FIRST = ["crab", "bat", "octopus", "scorpion", "spider", "elephant", "cat",
               "dolphin", "rabbit", "ant", "horse", "lizard", "frog", "dog",
               "guinea_pig", "bird", "starfish"]


async def _sharded(a, subs):
    order = [s for s in HEAVY_FIRST if s in subs] + [s for s in subs if s not in HEAVY_FIRST]
    groups = [order[i::a.shards] for i in range(a.shards)]
    groups = [g for g in groups if g]
    passthrough = ["--rolls", str(a.rolls), "--renders", a.renders,
                   "--max-attempts", str(a.max_attempts)]
    if a.until_packed:
        passthrough.append("--until-packed")
    procs = []
    for i, g in enumerate(groups):
        tag = f"{a.tag}_{i}"
        log = open(os.path.join(S, f"repair_rolls_{tag}.log"), "w")
        procs.append((tag, await asyncio.create_subprocess_exec(
            sys.executable, os.path.abspath(__file__), "--only", ",".join(g),
            "--tag", tag, *passthrough, stdout=log, stderr=asyncio.subprocess.STDOUT)))
        print(f"shard {i}: {','.join(g)} -> {tag}", flush=True)
    for _tag, pr in procs:
        await pr.wait()
    import shutil
    rows = []
    os.makedirs(WORK, exist_ok=True)
    for i, (tag, _pr) in enumerate(procs):
        part = os.path.join(S, "..", "data", f"repair_rolls_{tag}.json")
        if not os.path.exists(part):
            print(f"shard {i} ({tag}) wrote no rows -- see repair_rolls_{tag}.log", flush=True)
            continue
        for r in json.load(open(part)):
            r["shard"] = i
            rows.append(r)
            src = os.path.join(S, f"repair_rolls_out_{tag}", f"{r['subject']}_{r['roll']}")
            dst = os.path.join(WORK, f"{r['subject']}_{r['roll']}")
            if os.path.isdir(src) and not os.path.isdir(dst):
                shutil.copytree(src, dst)
    rows.sort(key=lambda r: (ALL17.index(r["subject"]) if r["subject"] in ALL17 else 99, r["roll"]))
    json.dump(rows, open(OUT, "w"), indent=1)
    print(f"{len(rows)} rows from {len(procs)} shards in {OUT}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
