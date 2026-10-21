"""Live A/B/C: three grid designs, one prompt, one model, nine meshes.

The ONLY variable is the rendered sheet. Same system prompt, same tool schema,
same model (claude-sonnet-5 via LLM_MODEL), no temperature sent, N=1.

The subject is NOT given to the model -- it identifies the animal from the
picture. Telling it "this is a dog" would inject the anatomical prior we are
trying to measure the grid's contribution to.
"""
from __future__ import annotations
import asyncio, json, os, sys, time

H = "<repo>/mcp_harness"
S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, H); os.chdir(H)
import env_config; env_config.load_env()
import llm_client

SUBJECTS = ["dog", "cat", "horse", "lizard", "frog", "bird",
            "starfish", "spider", "octopus"]
ARMS = ["A", "B", "C"]

SYSTEM = """You author Metric Trees for an origami design pipeline by READING \
orthographic renders of a 3-D mesh.

THE IMAGE holds three orthographic views of ONE mesh -- side (XY), front (ZY), \
top (XZ) -- each under a labelled measurement grid. The grid divides the mesh's \
LONGEST extent into 24 units and all three views share that scale. Tick numbers \
are printed along the edges.

PROTOCOL, followed exactly:

1. READ BEFORE YOU DERIVE. Before writing any length, quote the grid \
coordinates you actually read, e.g. "shoulder (7.5, 9.5), ground (7, 21.5), so \
foreleg = 12". Every length must trace to a reading in `readings`. A length \
with no reading behind it is a fabrication.

2. PROPORTION, NOT POSE. Encode proportional limb lengths, never the pose. If \
an animal is mid-stride with its legs at four different phases, its four legs \
are still authored EQUAL.

3. LEAF CONVENTION. One leaf per terminal appendage: each limb, wing, tentacle \
or ray counts one; the head counts one; the tail counts one when the animal has \
an external tail. Digits, toes, ears, antennae and eyes are sub-flap detail and \
DO NOT count as leaves.

4. STRUCTURE. A body spine of internal nodes (not one hub), and multi-segment \
limbs with named joints -- thigh -> knee -> shank -> hock -> foot. Root at a \
body node with length 0. Every non-root node names a parent appearing EARLIER \
in your list.

5. LABEL INFERENCE. The grid gives endpoints and totals; splitting a limb into \
segments is anatomical inference, not measurement. Say which splits were \
inferred in `notes`.

6. Lengths are positive INTEGERS in grid units.

Answer only by calling submit_tree."""

TOOL = [{"type": "function", "function": {
    "name": "submit_tree",
    "description": "Submit the metric tree read off the render.",
    "parameters": {"type": "object", "properties": {
        "subject_guess": {"type": "string",
                          "description": "what animal this mesh is"},
        "readings": {"type": "array", "items": {"type": "string"},
                     "description": "quoted grid coordinate readings"},
        "nodes": {"type": "array", "items": {"type": "object", "properties": {
            "name": {"type": "string"},
            "parent": {"type": ["string", "null"]},
            "length": {"type": "integer"}},
            "required": ["name", "parent", "length"]}},
        "pairs": {"type": "array",
                  "items": {"type": "array", "items": {"type": "string"}}},
        "leaves": {"type": "array", "items": {"type": "string"}},
        "notes": {"type": "string"}},
        "required": ["subject_guess", "readings", "nodes", "leaves"]}}}]


async def one(client, arm, subject):
    png = f"{S}/gridtest/{arm}/{subject}.png"
    msg = llm_client.user_message_with_images(
        "Author the metric tree for the mesh in this image.", [png])
    t0 = time.time()
    try:
        r = await client.run_turn(SYSTEM, [msg], TOOL)
    except Exception as e:
        return {"arm": arm, "subject": subject, "error":
                f"{type(e).__name__}: {str(e)[:300]}"}
    rec = {"arm": arm, "subject": subject, "seconds": round(time.time() - t0, 1),
           "finish": r.finish_reason, "text": (r.text or "")[:300]}
    if r.tool_calls:
        try:
            rec["tree"] = json.loads(r.tool_calls[0].function.arguments)
        except Exception as e:
            rec["parse_error"] = str(e)[:200]
            rec["raw"] = r.tool_calls[0].function.arguments[:800]
    return rec


async def main():
    cfg = llm_client.LLMConfig.from_env()
    client = llm_client.LLMClient(cfg)
    print(f"model={cfg.model}  arms={ARMS}  subjects={len(SUBJECTS)}  "
          f"calls={len(ARMS)*len(SUBJECTS)}", flush=True)
    out = []
    sem = asyncio.Semaphore(3)          # modest: avoid tripping rate limits

    async def guarded(arm, subj):
        async with sem:
            rec = await one(client, arm, subj)
        t = rec.get("tree") or {}
        print(f"  {arm} {subj:9} guess={str(t.get('subject_guess'))[:14]:14} "
              f"leaves={len(t.get('leaves') or [])!s:>3} "
              f"nodes={len(t.get('nodes') or [])!s:>3} "
              f"readings={len(t.get('readings') or [])!s:>3} "
              f"finish={rec.get('finish')} {rec.get('error','')}", flush=True)
        return rec

    tasks = [guarded(a, s) for a in ARMS for s in SUBJECTS]
    out = list(await asyncio.gather(*tasks))
    json.dump(out, open("/tmp/arms_raw.json", "w"), indent=2)
    print("done")


asyncio.run(main())
