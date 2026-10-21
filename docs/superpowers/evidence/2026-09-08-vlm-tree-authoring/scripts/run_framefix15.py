"""Re-author the FIFTEEN subjects that never saw the corrected frame prompt.

WHY. The 17-subject `none` run (2026-09-08) predates commit 9209d07, which put
the two-frames warning into `loop_lib.SYSTEM`. Only `dog` and `rabbit` -- the
two the owner spotted -- were re-run against it, so the committed corpus was
TWO prompt configurations wearing one label. Reviewing the sheets on 09-09
found a third inverted tree, the DOLPHIN: its readings are right (dorsal base
v=7, tip v=1, matching the mesh) and every vertical component of its emitted
directions is sign-flipped. It scores EXACT on leaf count, clean on the
contract, and 0.28 on reading fidelity. No metric in this repo sees it.

SCOPE. Exactly one thing changes: the system prompt. Same arm-C renders, same
`none` mode, same MAX_VALIDATE, same model. `dog` and `rabbit` are NOT re-run --
they already carry the fixed prompt, and re-rolling them would buy nothing but
noise.
"""
from __future__ import annotations
import asyncio, json, os, sys

S = os.path.dirname(os.path.abspath(__file__))
H = "<repo>/mcp_harness"
sys.path.insert(0, S); sys.path.insert(0, H); sys.path.insert(0, os.path.join(H, "tests"))
os.chdir(H)
import env_config; env_config.load_env()
import llm_client, tree_contract
import loop_lib as L
import hand_trees_build as B

SUBJECTS = ["cat", "horse", "guinea_pig", "elephant", "lizard", "frog", "bird",
            "bat", "dolphin", "starfish", "octopus", "crab", "spider",
            "scorpion", "ant"]   # every subject EXCEPT dog and rabbit

MODES = ["none"]   # replicate of the finalized loop only
ARM = "C"
RAW = os.path.expanduser("~/Desktop/AI-Driven-Origami-IDE/.claude/worktrees/silly-tereshkova-7d463f/docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/data/frame_fix15_raw.json")
WORK = f"{S}/run17rep_out"
MAX_VALIDATE = 2

REVIEW = ("Review the tree you just submitted against the mesh render above. "
          "If a limb points the wrong way, a proportion is off, or the figure "
          "would not read as the animal, re-submit a CORRECTED tree via "
          "submit_tree. If it is right, re-submit it unchanged.")
REVIEW_VISUAL = ("This is YOUR tree, drawn from the lengths and directions you "
                 "gave, in four views (top / side / front / isometric). " + REVIEW)


def _asst(c):
    return {"role":"assistant","content":None,"tool_calls":[
        {"id":c.id,"type":"function","function":{"name":c.function.name,
         "arguments":c.function.arguments}}]}
def _tres(c): return {"role":"tool","tool_call_id":c.id,"content":"received"}
def _add(acc, u):
    if not u: return
    for k in ("prompt_tokens","completion_tokens","total_tokens"):
        acc[k] = acc.get(k,0) + int(u.get(k) or 0)
    acc["calls"] = acc.get("calls",0) + 1


async def author(client, subject, mode, log, usage):
    png = f"{S}/gridtest/{ARM}/{subject}.png"
    msgs = [llm_client.user_message_with_images(
        "Author the metric tree for the mesh in this image.", [png])]
    tree = call = None
    for rnd in range(MAX_VALIDATE + 1):
        r = await client.run_turn(L.SYSTEM, msgs, L.TOOL); _add(usage, r.usage)
        if not r.tool_calls:
            log.append({"stage":"author","no_tool_call":True}); return tree, log
        call = r.tool_calls[0]; tree = json.loads(call.function.arguments)
        nodes = L.to_tuples(tree)
        leaves = set(B.leaves_of(nodes))
        keep = [(a,b) for p in (tree.get("pairs") or []) if len(p)==2
                for a,b in [p] if a in leaves and b in leaves]
        try:
            tn, sp, _ = B.metric_tree(nodes, keep)
            errs = tree_contract.check(tn, sp).get("errors", [])
        except Exception as e:
            errs = [f"unbuildable: {e}"]
        log.append({"stage":"validate","round":rnd,"errors":errs})
        if not errs or rnd == MAX_VALIDATE: break
        msgs += [_asst(call), _tres(call), {"role":"user","content":
            "validate_tree REJECTED that tree:\n- " + "\n- ".join(errs)
            + "\n\nFix every error and re-submit the complete tree."}]

    if tree is None or mode == "none":
        log.append({"stage":"review","mode":mode,"revised":None}); return tree, log
    if mode == "text":
        msgs += [_asst(call), _tres(call), {"role":"user","content":REVIEW}]
    else:
        os.makedirs(WORK, exist_ok=True)
        sp_png = L.sheet(L.to_tuples(tree), f"{WORK}/{subject}_draft.png",
                         f"{subject} — your draft")
        msgs += [_asst(call), _tres(call),
                 llm_client.user_message_with_images(REVIEW_VISUAL, [sp_png])]
    r2 = await client.run_turn(L.SYSTEM, msgs, L.TOOL); _add(usage, r2.usage)
    if r2.tool_calls:
        t2 = json.loads(r2.tool_calls[0].function.arguments)
        log.append({"stage":"review","mode":mode,
                    "revised": json.dumps(t2.get("nodes")) != json.dumps(tree.get("nodes"))})
        tree = t2
    else:
        log.append({"stage":"review","mode":mode,"revised":False})
    return tree, log


async def main():
    have = {}
    if os.path.exists(RAW):
        have = {(x["mode"],x["subject"]):x for x in json.load(open(RAW)) if x.get("tree")}
    todo = [(m,s) for m in MODES for s in SUBJECTS if (m,s) not in have]
    print(f"have {len(have)}/{len(MODES)*len(SUBJECTS)}, running {len(todo)}", flush=True)
    client = llm_client.LLMClient(llm_client.LLMConfig.from_env())
    sem, lock = asyncio.Semaphore(3), asyncio.Lock()
    TOTAL = {}

    async def guarded(mode, subj):
        for k in range(4):
            log, usage = [], {}
            try:
                async with sem:
                    tree, log = await author(client, subj, mode, log, usage)
                rec = {"mode":mode,"subject":subj,"tree":tree,"log":log,"usage":usage}
            except Exception as e:
                rec = {"mode":mode,"subject":subj,"log":log,"usage":usage,
                       "error":f"{type(e).__name__}: {str(e)[:200]}"}
            if rec.get("tree") or "APIConnectionError" not in str(rec.get("error","")):
                break
            await asyncio.sleep(15*(k+1))
        rv=[x for x in rec["log"] if x.get("stage")=="review"]
        async with lock:
            _add(TOTAL, {k: rec["usage"].get(k) for k in
                         ("prompt_tokens","completion_tokens","total_tokens")})
            if rec.get("tree"):
                have[(mode,subj)] = rec
                json.dump(list(have.values()), open(RAW,"w"), indent=2)
        print(f"  {mode:7}{subj:11} nodes={len((rec.get('tree') or {}).get('nodes') or [])!s:>3} "
              f"revised={rv[0].get('revised') if rv else '-'} "
              f"tok={rec['usage'].get('total_tokens',0):>6} {rec.get('error','')}", flush=True)
        return rec

    await asyncio.gather(*[guarded(m,s) for m,s in todo])
    print(f"\ntotal with trees: {len(have)}/{len(MODES)*len(SUBJECTS)}")
    print(f"MEASURED USAGE: {TOTAL.get('calls',0)} calls  "
          f"prompt {TOTAL.get('prompt_tokens',0):,}  "
          f"completion {TOTAL.get('completion_tokens',0):,}  "
          f"total {TOTAL.get('total_tokens',0):,}")
    print("done")


if __name__ == "__main__":
    asyncio.run(main())
