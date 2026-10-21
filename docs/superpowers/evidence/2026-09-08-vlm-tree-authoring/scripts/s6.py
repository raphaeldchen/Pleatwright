"""S6: attribute the self-check, with the control the spec forgot.

The spec said "re-run one arm with render_tree_sheet disabled". That compares
2 calls against 1 and would credit the IMAGE for whatever a second turn buys on
its own. Three conditions instead, identical in every other respect:

  none    author + validate.                              1 turn.
  text    author + validate + "review your tree and re-submit".   2 turns, NO image.
  visual  author + validate + the same request WITH the tree drawn. 2 turns, image.

none vs text   = what a second turn is worth at all.
text vs visual = what SEEING the tree is worth. That is S3's actual claim.

Grid arm C throughout, since grid design measured inert (spec 2a).
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

SUBJECTS = ["dog", "cat", "horse", "lizard", "frog", "bird",
            "starfish", "spider", "octopus"]
MODES = ["none", "text", "visual"]
ARM = "C"
WORK = f"{S}/s6out"
RAW = "/tmp/s6_raw.json"
MAX_VALIDATE = 2

REVIEW = ("Review the tree you just submitted against the mesh render above. "
          "If a limb points the wrong way, a proportion is off, or the figure "
          "would not read as the animal, re-submit a CORRECTED tree via "
          "submit_tree. If it is right, re-submit it unchanged.")
REVIEW_VISUAL = ("This is YOUR tree, drawn from the lengths and directions you "
                 "gave, in four views (top / side / front / isometric). "
                 + REVIEW)


def _assistant(c):
    return {"role": "assistant", "content": None, "tool_calls": [
        {"id": c.id, "type": "function",
         "function": {"name": c.function.name, "arguments": c.function.arguments}}]}


def _toolresult(c):
    return {"role": "tool", "tool_call_id": c.id, "content": "received"}


async def author(client, subject, mode, log):
    png = f"{S}/gridtest/{ARM}/{subject}.png"
    msgs = [llm_client.user_message_with_images(
        "Author the metric tree for the mesh in this image.", [png])]
    tree = call = None
    for rnd in range(MAX_VALIDATE + 1):
        r = await client.run_turn(L.SYSTEM, msgs, L.TOOL)
        if not r.tool_calls:
            log.append({"stage": "author", "no_tool_call": True}); return tree, log
        call = r.tool_calls[0]
        tree = json.loads(call.function.arguments)
        nodes = L.to_tuples(tree)
        pairs = [(a, b) for p in (tree.get("pairs") or []) if len(p) == 2
                 for a, b in [p]]
        leaves = set(B.leaves_of(nodes))
        keep = [(a, b) for a, b in pairs if a in leaves and b in leaves]
        try:
            tn, sp, _ = B.metric_tree(nodes, keep)
            errs = tree_contract.check(tn, sp).get("errors", [])
        except Exception as e:
            errs = [f"unbuildable: {e}"]
        log.append({"stage": "validate", "round": rnd, "errors": errs})
        if not errs or rnd == MAX_VALIDATE:
            break
        msgs += [_assistant(call), _toolresult(call),
                 {"role": "user", "content":
                  "validate_tree REJECTED that tree:\n- " + "\n- ".join(errs)
                  + "\n\nFix every error and re-submit the complete tree."}]

    if tree is None or mode == "none":
        log.append({"stage": "review", "mode": mode, "revised": None})
        return tree, log

    if mode == "text":
        msgs += [_assistant(call), _toolresult(call),
                 {"role": "user", "content": REVIEW}]
    else:
        os.makedirs(WORK, exist_ok=True)
        sp_png = L.sheet(L.to_tuples(tree), f"{WORK}/{subject}_draft.png",
                         f"{subject} — your draft")
        msgs += [_assistant(call), _toolresult(call),
                 llm_client.user_message_with_images(REVIEW_VISUAL, [sp_png])]

    r2 = await client.run_turn(L.SYSTEM, msgs, L.TOOL)
    if r2.tool_calls:
        t2 = json.loads(r2.tool_calls[0].function.arguments)
        log.append({"stage": "review", "mode": mode,
                    "revised": json.dumps(t2.get("nodes")) != json.dumps(tree.get("nodes"))})
        tree = t2
    else:
        log.append({"stage": "review", "mode": mode, "revised": False})
    return tree, log


async def main():
    client = llm_client.LLMClient(llm_client.LLMConfig.from_env())
    have = {}
    if os.path.exists(RAW):
        have = {(x["mode"], x["subject"]): x
                for x in json.load(open(RAW)) if x.get("tree")}
    todo = [(m, s) for m in MODES for s in SUBJECTS if (m, s) not in have]
    print(f"have {len(have)}/27, running {len(todo)}", flush=True)
    sem, lock = asyncio.Semaphore(2), asyncio.Lock()

    async def guarded(mode, subj):
        for k in range(4):
            log = []
            try:
                async with sem:
                    tree, log = await author(client, subj, mode, log)
                rec = {"mode": mode, "subject": subj, "tree": tree, "log": log}
            except Exception as e:
                rec = {"mode": mode, "subject": subj, "log": log,
                       "error": f"{type(e).__name__}: {str(e)[:200]}"}
            if rec.get("tree") or "APIConnectionError" not in str(rec.get("error", "")):
                break
            await asyncio.sleep(15 * (k + 1))
        rv = [x for x in rec["log"] if x.get("stage") == "review"]
        print(f"  {mode:7} {subj:9} nodes={len(rec.get('tree',{}).get('nodes') or [])!s:>3} "
              f"revised={rv[0].get('revised') if rv else '-'} "
              f"{rec.get('error','')}", flush=True)
        if rec.get("tree"):
            async with lock:
                have[(mode, subj)] = rec
                json.dump(list(have.values()), open(RAW, "w"), indent=2)
        return rec

    await asyncio.gather(*[guarded(m, s) for m, s in todo])
    print(f"total {len(have)}/27"); print("done")


if __name__ == "__main__":
    asyncio.run(main())
