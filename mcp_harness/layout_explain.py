"""The packing layout question: card text and a short VLM explanation
(spec 2026-10-16 §7, §8.1).

The numbers fix the recommendation (the smaller layout) and every number on the
card; the model only writes 2-4 sentences on the trade-off for THIS subject.
One forced single-tool turn, shaped like `subject_rewrite.rewrite`. Any
failure falls back to a template built from the same numbers: a model failure
never blocks the question or the fold.
"""
from __future__ import annotations

import asyncio
import json

MAX_CHARS = 600
EXPLAIN_TIMEOUT_S = 60      # a hung model call falls back to the template, never blocks the question

TOOL = [{"type": "function", "function": {
    "name": "submit_explanation",
    "description": "Submit the 2-4 sentence explanation of the layout trade-off.",
    "parameters": {"type": "object", "properties": {
        "explanation": {"type": "string",
                        "description": "Two to four plain sentences about this subject."}},
        "required": ["explanation"]}}}]

SYSTEM = (
    "An origami tool packs a model's limbs onto one square sheet and found two "
    "layouts. The SYMMETRIC layout mirrors left and right limbs about the "
    "sheet's centre line but needs a larger grid, so the folded model comes out "
    "smaller. The SMALLER layout is not mirror-symmetric but needs a smaller "
    "grid, so the same sheet folds into a larger model. The recommendation is "
    "FIXED by the numbers; do not choose and do not argue against it. Write 2 "
    "to 4 plain sentences explaining the trade-off for this particular "
    "subject: what its mirrored limbs (if any) gain from symmetry and what the "
    "extra size gives. Use only the numbers given. Call submit_explanation "
    "with the text.")


def _pct(x) -> str:
    return f"{round(float(x) * 100)}%"


def _opt(summary: dict, which: str):
    o = summary.get(which)
    return o if o and o.get("metrics") is not None else None


def _smaller_option(summary: dict) -> dict:
    sm, sy = summary["smaller"], _opt(summary, "symmetric")
    m, gain = sm["metrics"], float(summary["gain"])
    pros = [f"the folded model is {gain:.2f}× larger from the same sheet"]
    cons = ["the crease pattern is not mirror-symmetric, so left and right sides fold differently"]
    if sy:
        a, b = m["creases"], sy["metrics"]["creases"]
        if a < b:
            pros.append(f"fewer creases ({a} against {b})")
        if m["mean_layers"] < sy["metrics"]["mean_layers"]:
            pros.append(f"fewer layers on average ({m['mean_layers']:.1f} against "
                        f"{sy['metrics']['mean_layers']:.1f})")
    return {"id": "smaller", "label": "Smaller grid", "grid": sm["grid"],
            "pros": pros, "cons": cons}


def _symmetric_option(summary: dict) -> dict:
    sy, sm = summary["symmetric"], _opt(summary, "smaller")
    m, gain = sy["metrics"], float(summary["gain"])
    pros = ["left and right limbs mirror each other, so each paired step is folded the same way twice"]
    cons = [f"the folded model comes out {_pct(1 - 1 / gain)} smaller"]
    if sm:
        a, b = m["creases"], sm["metrics"]["creases"]
        if a > b:
            cons.append(f"more creases ({a} against {b})")
        if m["mean_layers"] > sm["metrics"]["mean_layers"]:
            cons.append(f"more layers on average ({m['mean_layers']:.1f} against "
                        f"{sm['metrics']['mean_layers']:.1f})")
        if m["slack_fraction"] > sm["metrics"]["slack_fraction"]:
            cons.append(f"{_pct(m['slack_fraction'])} of the sheet is extra paper folded into "
                        f"the flaps (against {_pct(sm['metrics']['slack_fraction'])})")
    return {"id": "symmetric", "label": "Mirror-symmetric", "grid": sy["grid"],
            "pros": pros, "cons": cons}


def card(summary: dict) -> dict:
    """The question card: the recommended option first, numbers-only pros/cons."""
    built = {"smaller": _smaller_option(summary), "symmetric": _symmetric_option(summary)}
    rec = summary["recommended"]
    order = [rec] + [k for k in built if k != rec]
    return {"question": "Which layout should the model be folded from?",
            "options": [{**built[k], "recommended": k == rec} for k in order]}


def _pairs_text(pairs: list) -> str:
    if not pairs:
        return "no bilateral leaf pairs"
    return "bilateral leaf pairs: " + ", ".join(f"{a}/{b}" for a, b in pairs)


def template_explanation(summary: dict, subject: str, pairs: list) -> str:
    gain = float(summary["gain"])
    sy, sm = summary["symmetric"]["grid"], summary["smaller"]["grid"]
    mirror = ("its paired limbs mirror each other in the symmetric layout"
              if pairs else "it has no mirrored limb pairs to keep symmetric")
    return (f"For the {subject}, the symmetric layout needs a grid of {sy} and the "
            f"smaller layout only {sm}, so the same sheet folds into a model "
            f"{gain:.2f}× larger. The smaller layout is recommended; {mirror}, "
            f"which is what the larger grid pays for.")


def _ask(summary: dict, subject: str, pairs: list) -> str:
    lines = [f"Subject: {subject}", _pairs_text(pairs),
             f"Symmetric grid: {summary['symmetric']['grid']}; smaller grid: "
             f"{summary['smaller']['grid']}; the smaller layout folds a model "
             f"{float(summary['gain']):.2f}× larger.",
             f"Recommendation (fixed): the {summary['recommended']} layout."]
    for which in ("symmetric", "smaller"):
        m = summary[which]["metrics"]
        lines.append(f"{which}: extra paper {_pct(m['slack_fraction'])}, mean layers "
                     f"{m['mean_layers']:.1f}, creases {m['creases']}")
    return "\n".join(lines) + "\n\nExplain the trade-off for this subject."


async def explain(client, summary: dict, subject: str, pairs: list) -> str:
    """One forced `submit_explanation` turn; any failure gives the template."""
    fallback = template_explanation(summary, subject, pairs)
    try:
        r = await asyncio.wait_for(
            client.run_turn(SYSTEM, [{"role": "user", "content": _ask(summary, subject, pairs)}], TOOL),
            timeout=EXPLAIN_TIMEOUT_S)
        if not r.tool_calls:
            return fallback
        text = str(json.loads(r.tool_calls[0].function.arguments).get("explanation", "")).strip()
    except Exception:
        return fallback
    return text[:MAX_CHARS].strip() or fallback
