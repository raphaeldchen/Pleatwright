"""The WIRED loop: read -> author -> validate -> self-check -> re-author.

Three rungs the previous run did not have:
  * `direction` in the schema, so the tree can be DRAWN as a stick figure
  * validate_tree feedback (caught 2 zero-length edges on the horse and 10 on
    the lizard last time, and nothing acted on them)
  * a visual self-check -- the model's own tree is rendered in the same four
    views and handed BACK to it beside the mesh

The self-check image must ride as a `role == "user"` message: Anthropic's
OpenAI-compat endpoint accepts image_url only there, and a tool result is
role == "tool". That constraint is why this is an agent-loop change and not a
tool change.
"""
from __future__ import annotations
import asyncio, json, os, sys, time

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
ARMS = ["A", "B", "C"]
WORK = f"{S}/loopout"
MAX_VALIDATE = 2


def _tree_from(call):
    return json.loads(call.function.arguments)


def _assistant(call):
    return {"role": "assistant", "content": None, "tool_calls": [
        {"id": call.id, "type": "function",
         "function": {"name": call.function.name,
                      "arguments": call.function.arguments}}]}


def _toolresult(call, text):
    return {"role": "tool", "tool_call_id": call.id, "content": text}


async def author(client, arm, subject, log):
    png = f"{S}/gridtest/{arm}/{subject}.png"
    msgs = [llm_client.user_message_with_images(
        "Author the metric tree for the mesh in this image.", [png])]
    tree, call = None, None

    for rnd in range(MAX_VALIDATE + 1):
        r = await client.run_turn(L.SYSTEM, msgs, L.TOOL)
        if not r.tool_calls:
            log.append({"round": rnd, "stage": "author", "no_tool_call": True,
                        "finish": r.finish_reason})
            return tree, msgs, log
        call = r.tool_calls[0]
        tree = _tree_from(call)
        nodes = L.to_tuples(tree)
        try:
            tn, pairs, *_ = B.metric_tree(
                nodes, [(a, b) for a, b in (tree.get("pairs") or [])
                        if len(_ := (a, b)) == 2])
        except Exception as e:
            tn, pairs = [], []
        rep = tree_contract.check(tn, pairs) if tn else {"errors": ["unbuildable"]}
        errs = rep.get("errors", [])
        log.append({"round": rnd, "stage": "validate", "errors": errs})
        if not errs:
            break
        if rnd == MAX_VALIDATE:
            break
        msgs += [_assistant(call), _toolresult(call, "received"),
                 {"role": "user", "content":
                  "validate_tree REJECTED that tree:\n- " + "\n- ".join(errs)
                  + "\n\nFix every error and re-submit the complete tree via "
                    "submit_tree. Rule 6: every non-root length is a positive "
                    "integer. Rule 7: pairs join two LEAVES only."}]

    if tree is None:
        return None, msgs, log

    # ---- visual self-check ------------------------------------------------
    try:
        os.makedirs(f"{WORK}/{arm}", exist_ok=True)
        sp = L.sheet(L.to_tuples(tree), f"{WORK}/{arm}/{subject}_draft.png",
                     f"{subject} — your draft")
    except Exception as e:
        log.append({"stage": "selfcheck", "render_error": str(e)[:200]})
        return tree, msgs, log

    msgs += [_assistant(call), _toolresult(call, "received"),
             llm_client.user_message_with_images(
                 "This is YOUR tree, drawn from the lengths and directions you "
                 "gave, in four views (top / side / front / isometric). Compare "
                 "it against the mesh render above. If a limb points the wrong "
                 "way, a proportion is off, or the figure does not read as the "
                 "animal, re-submit a CORRECTED tree via submit_tree. If it is "
                 "right, re-submit it unchanged.", [sp])]
    r2 = await client.run_turn(L.SYSTEM, msgs, L.TOOL)
    if r2.tool_calls:
        t2 = _tree_from(r2.tool_calls[0])
        changed = json.dumps(t2.get("nodes")) != json.dumps(tree.get("nodes"))
        log.append({"stage": "selfcheck", "revised": changed})
        tree = t2
    else:
        log.append({"stage": "selfcheck", "revised": False,
                    "no_tool_call": True})
    return tree, msgs, log


async def one(client, arm, subject):
    t0, log = time.time(), []
    try:
        tree, _, log = await author(client, arm, subject, log)
    except Exception as e:
        return {"arm": arm, "subject": subject, "log": log,
                "error": f"{type(e).__name__}: {str(e)[:250]}"}
    return {"arm": arm, "subject": subject, "tree": tree, "log": log,
            "seconds": round(time.time() - t0, 1)}


async def main():
    cfg = llm_client.LLMConfig.from_env()
    client = llm_client.LLMClient(cfg)
    print(f"model={cfg.model} max_tokens={cfg.max_tokens} "
          f"arms={ARMS} subjects={len(SUBJECTS)}", flush=True)
    sem = asyncio.Semaphore(3)

    async def guarded(a, s):
        async with sem:
            rec = await one(client, a, s)
        t = rec.get("tree") or {}
        vr = [x for x in rec["log"] if x.get("stage") == "validate"]
        sc = [x for x in rec["log"] if x.get("stage") == "selfcheck"]
        print(f"  {a} {s:9} leaves={len(t.get('leaves') or [])!s:>3} "
              f"nodes={len(t.get('nodes') or [])!s:>3} "
              f"val_rounds={len(vr)} final_errs="
              f"{len(vr[-1]['errors']) if vr else '?'} "
              f"revised={sc[0].get('revised') if sc else '-'} "
              f"{rec.get('error','')}", flush=True)
        return rec

    out = list(await asyncio.gather(*[guarded(a, s)
                                      for a in ARMS for s in SUBJECTS]))
    json.dump(out, open("/tmp/loop_raw.json", "w"), indent=2)
    print("done")


if __name__ == "__main__":
    asyncio.run(main())
