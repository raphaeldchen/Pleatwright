"""The 17-subject ablation, with its own bill attached.

SCOPE, chosen for cost. Three modes x 17 subjects = 51 cells, grid arm C only.
The grid question is NOT re-run: it was null on leaf count AND null on reading
fidelity, so three more grid arms would be 51 further cells against a
hypothesis nothing supports. The `visual` mode doubles as the full pipeline, so
this single sweep answers both live questions -- does the agent still beat the
extractor on a corpus where the extractor now scores MAE 2.00, and does the
self-check do anything once the metric has room to move.

Token usage is accumulated per cell from TurnResult.usage, which `run_turn`
discarded until today. Dollar figures are deliberately NOT computed here: the
token counts are measured, prices are not, and inventing a rate would be the
one number in this file nobody could audit.
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

SUBJECTS = ["dog","cat","horse","lizard","frog","bird","starfish","spider","octopus",
            "dolphin","guinea_pig","rabbit","bat","elephant","ant","scorpion","crab"]
MODES = ["none", "text", "visual"]
ARM = "C"
RAW = "/tmp/run17_raw.json"
WORK = f"{S}/run17out"
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
