"""Claude reads an image against an anatomy description, part by part (spec §2).

Two uses, one function:
  * the DRAFT score of a mesh sheet or concept image against the checklist,
    which the owner then confirms or corrects (the owner's reading is final);
  * arm E's PICKER, which sees only the subject's anatomy text, never the
    checklist, so it would work on a subject outside the test set.

The model answers per part and never gives a verdict: VLMs are unreliable at
counting parts (frontier models ~60% on leaflets, NeurIPS 2026), so pass/fail
is computed here from the counts it reports, and the picker is calibrated
against the owner before arm E is scored. Per-part yes/no checks follow
CADCodeVerify (ICLR'25).
"""
from __future__ import annotations

import json

import llm_client

#: Measured 2026-10-16 on A/scorpion/r1, whose tail floats free of the body:
#: claude-sonnet-5 called it attached and passed the mesh; claude-opus-5-5 and
#: claude-fable-5-1 both failed it, and all three passed the photo mesh. Opus,
#: not Fable: it caught the case at a lower price. Needs "auto" tool choice
#: (llm_client.NO_FORCED_TOOL_USE).
JUDGE_MODEL = "claude-opus-5-5"
MAX_REPAIRS = 2

TOOL = [{"type": "function", "function": {
    "name": "submit_assessment",
    "description": "Report what is visible, part by part.",
    "parameters": {"type": "object", "properties": {
        "parts": {"type": "array", "items": {"type": "object", "properties": {
            "part": {"type": "string"},
            "expected": {"type": "integer", "description": "how many the description names"},
            "seen": {"type": "integer", "description": "how many are visible"},
            "attached": {"type": "boolean", "description": "every one visible is joined to the body"}},
            "required": ["part", "expected", "seen", "attached"]}},
        "extras": {"type": "array", "items": {"type": "string"},
                   "description": "anatomy that should not be there: an extra limb, a "
                                  "large detached chunk, a base, a second animal"},
        "artifacts": {"type": "array", "items": {"type": "string"},
                      "description": "small stray specks, slivers or thin strands that "
                                     "are not limb-like"}},
        "required": ["parts", "extras", "artifacts"]}}}]

SYSTEM = (
    "You check one picture of an animal (a photo, a rendered image, or three "
    "views of a grey 3D model) against a description of its anatomy.\n"
    "1. List every body part the description names, with how many it names.\n"
    "2. For each part, count how many the animal HAS in the picture, and say "
    "whether every one of them is attached to the body. A part floating free "
    "of the body, or broken off, is not attached. When the picture shows "
    "several views of one model, use them all: a leg hidden behind its "
    "partner in the side view still counts when the front or top view shows "
    "it. Count the model's parts once, not once per view.\n"
    "3. Under extras, list only what does not belong to a whole, correctly "
    "formed animal: a limb or tail beyond what the animal has, a large "
    "detached chunk that could be read as a body part, a second animal, a "
    "base or stand. Real small anatomy the description does not mention "
    "(ears, antennae, mouthparts, pedipalps, toes, spines, fins) is NOT an "
    "extra. Leave extras empty when there is none.\n"
    "4. Under artifacts, list small stray geometry: a tiny floating speck or "
    "blob, a thin sliver or strand that is hard to see and does not look like "
    "a limb. Artifacts are noted but do not count against the animal.\n"
    "Report counts only; do not judge the picture overall. Call "
    "submit_assessment.")


def _score(parts: list[dict], extras: list[str], artifacts: list[str] = ()) -> dict:
    """Artifacts never fail a cell (owner, 2026-10-18): small stray specks and
    slivers don't matter as long as the anatomy is all there and attached."""
    bad = [p for p in parts
           if int(p.get("seen", -1)) != int(p.get("expected", -2)) or not p.get("attached")]
    # No parts reported is no evidence, not a pass.
    return {"parts": parts, "extras": extras, "artifacts": list(artifacts),
            "passed": bool(parts) and not bad and not extras,
            "mismatches": len(bad) + len(extras)}


def _norm(name: str) -> str:
    return " ".join(w.rstrip("s") for w in str(name).lower().split())


def _against(expected_parts: list[dict], reported: list[dict]) -> list[dict]:
    """The checklist decides which parts and how many; the model only says what it SAW.
    A checklist part the model did not report counts as seen 0 (final review I1)."""
    by = {_norm(p["part"]): p for p in reported}
    out = []
    for e in expected_parts:
        r = by.get(_norm(e["part"]))
        out.append({"part": e["part"], "expected": int(e["count"]),
                    "seen": r["seen"] if r else 0, "attached": r["attached"] if r else False})
    return out


async def assess(client, image_path: str, anatomy: str, *,
                 expected_parts: list[dict] | None = None) -> dict:
    """Per-part counts for one picture; pass/fail computed from them.

    `expected_parts` (the checklist, for drafts): the parts and counts come from
    it, not from the model's reading of `anatomy`. Without it (the picker, which
    sees only anatomy text), a reply naming no parts fails."""
    ask = f"The anatomy description is:\n{anatomy}\n\nCheck the attached picture against it."
    if expected_parts:
        ask += ("\nReport exactly these parts, using these names: "
                + ", ".join(p["part"] for p in expected_parts) + ".")
    msgs = [llm_client.user_message_with_images(ask, [image_path])]
    err = "no answer"
    for _ in range(MAX_REPAIRS + 1):
        r = await client.run_turn(SYSTEM, msgs, TOOL)
        if not r.tool_calls:
            err = "answer by calling submit_assessment"
            msgs = msgs + [{"role": "assistant", "content": r.text or ""},
                           {"role": "user", "content": err}]
            continue
        call = r.tool_calls[0]
        try:
            a = json.loads(call.function.arguments)
            parts = [dict(p) for p in a["parts"]]
            for p in parts:
                p["expected"], p["seen"], p["attached"] = (int(p["expected"]), int(p["seen"]),
                                                           bool(p["attached"]))
            if expected_parts:
                parts = _against(expected_parts, parts)
            return _score(parts, [str(x) for x in a.get("extras") or []],
                          [str(x) for x in a.get("artifacts") or []])
        except (ValueError, KeyError, TypeError, AttributeError) as e:
            err = f"the assessment could not be read ({type(e).__name__}: {e})"
            msgs = msgs + [
                {"role": "assistant", "content": None,
                 "tool_calls": [{"id": call.id, "type": "function",
                                 "function": {"name": call.function.name,
                                              "arguments": call.function.arguments}}]},
                {"role": "tool", "tool_call_id": call.id, "content": "received"},
                {"role": "user", "content": err + "; submit it again with every field."}]
    return {"parts": [], "extras": [], "passed": False, "mismatches": 0, "error": err}


async def pick(client, image_paths: list[str], anatomy: str) -> dict:
    """The first passing image; with none, the fewest mismatches, flagged."""
    assessments = [await assess(client, p, anatomy) for p in image_paths]
    for i, a in enumerate(assessments):
        if a["passed"]:
            return {"index": i, "none_acceptable": False, "assessments": assessments}
    usable = [i for i, a in enumerate(assessments) if "error" not in a] or list(range(len(assessments)))
    best = min(usable, key=lambda i: assessments[i]["mismatches"])
    return {"index": best, "none_acceptable": True, "assessments": assessments}
