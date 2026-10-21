"""Mesh review: turn the reviewer's feedback into a better subject description
(spec 2026-10-11 §3).

The description fills ONLY the {subject} slot of mesh_acquire's measured
concept template; the template itself is never touched (memory: concept-prompt
A/B). Every round starts from the original subject plus ALL feedback so far,
never from the previous rewrite, so edits cannot compound (Maestro, arXiv
2509.10704). Fixes are phrased positively: text-to-image models, FLUX/T5
included, tend to draw what a prompt says to omit (arXiv 2411.17066,
2410.23054).
"""
from __future__ import annotations

import json
import re

import llm_client
from mesh_ratings import words

MAX_WORDS = 25
MAX_REPAIRS = 2
_NEGATION = re.compile(r"\b(?:no|not|without|never|none|lacking)\b|\b\w+less\b|\b\w+n['\u2019]t\b",
                       re.IGNORECASE)
_SCENE = ("background", "render", "lighting", "studio", "shadow", "camera", "view")

TOOL = [{"type": "function", "function": {
    "name": "submit_subject",
    "description": "Submit the rewritten subject description.",
    "parameters": {"type": "object", "properties": {
        "description": {"type": "string",
                        "description": "One phrase, at most 25 words: the animal and its anatomy."}},
        "required": ["description"]}}}]

SYSTEM = (
    "You improve the SUBJECT of a fixed text-to-image prompt. The prompt is a "
    "full-body 3D render template that already sets the camera view, the plain "
    "white background and the lighting; your text replaces only the subject in "
    "'A full-body 3D render of a single <subject>, ...'. The image is turned into "
    "a 3D mesh, so the anatomy must be clear.\n"
    "Write ONE phrase of at most 25 words describing the animal and its body: "
    "legs, tail, head, appendages, their shape and how they separate. Keep the "
    "subject words exactly. Phrase every fix POSITIVELY, as what should be "
    "visible ('a short stubby tail', 'four long, well-separated legs'); never use "
    "no, not, without, never, none, lacking, contractions like isn't, or words ending in -less. Do not describe the "
    "background, render, lighting, studio, shadow, camera or view. Call "
    "submit_subject with the phrase.")


class RewriteFailed(Exception):
    """No valid description after the repairs; the message says why."""


def problems(description: str, subject: str, *, max_words: int = MAX_WORDS) -> list[str]:
    """What breaks the rewrite rules, each as an instruction the model can act on."""
    have = words(description)
    own = set(words(subject))
    missing = [w for w in words(subject) if w not in have]
    errs = []
    if missing:
        errs.append(f"keep the subject words: {', '.join(missing)} must appear")
    # The subject's own words ("hairless cat", "cat with no tail") are exempt
    # from the negation, scene and length rules: no feedback could ever fix
    # a subject that the rules themselves forbid.
    neg = sorted({m.group(0).lower() for m in _NEGATION.finditer(description)
                  if not set(words(m.group(0))) <= own})
    if neg:
        errs.append("phrase every fix positively, as what should be visible; "
                    f"remove: {', '.join(neg)}")
    n = sum(1 for t in description.split() if not (words(t) and set(words(t)) <= own))
    if n > max_words:
        errs.append(f"at most {max_words} words besides the subject's own (this has {n})")
    scene = [w for w in _SCENE if w in have and w not in own]
    if scene:
        errs.append(f"describe only the animal; the template already sets {', '.join(scene)}")
    return errs


async def rewrite(client, subject: str, feedback: list[str], image_path: str | None) -> str:
    """One forced submit_subject turn, with up to MAX_REPAIRS repairs."""
    ask = (f"The subject is: {subject}\n"
           "A reviewer looked at the concept image"
           + (" (attached)" if image_path else "")
           + " and the 3D mesh drawn from it, and said, in order:\n"
           + "\n".join(f"- {f}" for f in feedback)
           + "\n\nRewrite the subject so the next draw fixes all of it.")
    return await _submit(client, SYSTEM, ask, image_path, subject, MAX_WORDS,
                         "could not rewrite the subject from that feedback")


#: The concept-image experiment (spec 2026-10-16 §1): the subject's full
#: visible anatomy, written from the subject word ALONE. It is given no leaf or
#: flap convention and names no animal, so it generalises past the test set and
#: cannot leak the scoring checklist. 40 words, not 25: a crab's ten legs, two
#: of them pincers, do not fit in the rewrite's budget.
ANATOMY_MAX_WORDS = 40

ANATOMY_SYSTEM = (
    "You write the SUBJECT of a fixed text-to-image prompt. The prompt already "
    "sets the camera view, the plain background and the lighting; your text "
    "replaces only the subject in 'A full-body 3D render of a single <subject>, "
    "...'. The image is turned into a 3D mesh, so every body part must be drawn, "
    "correctly counted and attached.\n"
    f"Write ONE phrase of at most {ANATOMY_MAX_WORDS} words describing the "
    "animal's full visible anatomy: each kind of limb with its total count and "
    "how many on each side, claws or pincers, tail, fins, wings, tentacles or "
    "arms, and the head where it is distinct from the body. Keep the subject "
    "words exactly. Phrase everything POSITIVELY, as what should be visible; "
    "never use no, not, without, never, none, lacking, contractions like isn't, "
    "or words ending in -less. Do not describe the background, render, "
    "lighting, studio, shadow, camera or view. Call submit_subject with the "
    "phrase.")


async def anatomy(client, subject: str) -> str:
    """The subject's full visible anatomy, from the subject word alone."""
    return await _submit(client, ANATOMY_SYSTEM, f"The subject is: {subject}", None,
                         subject, ANATOMY_MAX_WORDS,
                         "could not describe the subject's anatomy")


async def _submit(client, system: str, ask: str, image_path: str | None,
                  subject: str, max_words: int, failure: str) -> str:
    """One submit_subject turn, repaired up to MAX_REPAIRS times."""
    msgs = [llm_client.user_message_with_images(ask, [image_path]) if image_path
            else {"role": "user", "content": ask}]
    errs = ["no description yet"]
    for _ in range(MAX_REPAIRS + 1):
        r = await client.run_turn(system, msgs, TOOL)
        if not r.tool_calls:
            errs = ["answer by calling submit_subject with the description"]
            msgs = msgs + [{"role": "assistant", "content": r.text or ""},
                           {"role": "user", "content": errs[0]}]
            continue
        call = r.tool_calls[0]
        try:
            description = str(json.loads(call.function.arguments).get("description", "")).strip()
        except (ValueError, AttributeError):
            description = ""
        errs = (problems(description, subject, max_words=max_words) if description
                else ["the description is empty"])
        if not errs:
            return description
        msgs = msgs + [
            {"role": "assistant", "content": None,
             "tool_calls": [{"id": call.id, "type": "function",
                             "function": {"name": call.function.name,
                                          "arguments": call.function.arguments}}]},
            {"role": "tool", "tool_call_id": call.id, "content": "received"},
            {"role": "user", "content": "That description breaks the rules:\n- "
             + "\n- ".join(errs) + "\nSubmit a corrected description."}]
    raise RewriteFailed(f"{failure}: " + "; ".join(errs))
