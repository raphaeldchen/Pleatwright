"""Resume the missing (arm, subject) cells, persisting after EVERY cell.

Two lessons from the last attempt are encoded here:
  * run_loop is imported for its author()/one() only -- its main() is now
    guarded, so importing cannot kick off a second full sweep.
  * results are written after each cell. The previous version dumped once at
    the end, so a run that stopped early lost everything it had paid for.
"""
import asyncio, json, os, sys
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, S)
import run_loop as R
import llm_client

RAW = "/tmp/loop_raw.json"


async def with_retry(client, arm, subj, tries=4):
    rec = None
    for k in range(tries):
        rec = await R.one(client, arm, subj)
        if rec.get("tree"):
            return rec
        if "APIConnectionError" not in str(rec.get("error", "")):
            return rec
        await asyncio.sleep(15 * (k + 1))
    return rec


async def main():
    have = {(x["arm"], x["subject"]): x
            for x in json.load(open(RAW)) if x.get("tree")}
    todo = [(a, s) for a in R.ARMS for s in R.SUBJECTS if (a, s) not in have]
    print(f"have {len(have)}/27, resuming {len(todo)}: {todo}", flush=True)
    client = llm_client.LLMClient(llm_client.LLMConfig.from_env())
    sem = asyncio.Semaphore(2)
    lock = asyncio.Lock()

    async def guarded(a, s):
        async with sem:
            rec = await with_retry(client, a, s)
        t = rec.get("tree") or {}
        vr = [x for x in rec["log"] if x.get("stage") == "validate"]
        sc = [x for x in rec["log"] if x.get("stage") == "selfcheck"]
        print(f"  {a} {s:9} leaves={len(t.get('leaves') or [])!s:>3} "
              f"nodes={len(t.get('nodes') or [])!s:>3} "
              f"val_rounds={len(vr)} "
              f"final_errs={len(vr[-1]['errors']) if vr else '?'} "
              f"revised={sc[0].get('revised') if sc else '-'} "
              f"{rec.get('error','')}", flush=True)
        if rec.get("tree"):
            async with lock:                       # persist immediately
                have[(a, s)] = rec
                json.dump(list(have.values()), open(RAW, "w"), indent=2)
        return rec

    await asyncio.gather(*[guarded(a, s) for a, s in todo])
    print(f"total with trees: {len(have)}/27")
    print("done")


if __name__ == "__main__":
    asyncio.run(main())
