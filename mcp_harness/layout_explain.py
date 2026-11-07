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

#: the SYSTEM prompt of a card without a stretched option is exactly slice 1's;
#: `system_prompt` adds the STRETCHED sentence only when T exists
_SYSTEM_HEAD = (
    "An origami tool packs a model's limbs onto one square sheet and found {n} "
    "layouts. The SYMMETRIC layout mirrors left and right limbs about the "
    "sheet's centre line but needs a larger grid, so the folded model comes out "
    "smaller. ")
_SYSTEM_STRETCHED = (
    "The STRETCHED layout also mirrors left and right limbs and needs a "
    "smaller grid than the symmetric one, but some of its creases are off the "
    "grid, at angles below 45 degrees, which makes it harder to precrease and "
    "collapse. ")
_SYSTEM_TAIL = (
    "The SMALLER layout is not mirror-symmetric but needs a smaller "
    "grid, so the same sheet folds into a larger model. The recommendation is "
    "FIXED by the numbers; do not choose and do not argue against it. Write 2 "
    "to 4 plain sentences explaining the trade-off for this particular "
    "subject: what its mirrored limbs (if any) gain from symmetry and what the "
    "extra size gives. Use only the numbers given. Call submit_explanation "
    "with the text.")
SYSTEM = _SYSTEM_HEAD.format(n="two") + _SYSTEM_TAIL


def system_prompt(summary: dict) -> str:
    if not summary.get("stretched"):
        return SYSTEM
    return (_SYSTEM_HEAD.format(n="up to three") + _SYSTEM_STRETCHED + _SYSTEM_TAIL).replace(
        "explaining the trade-off for this particular subject:",
        "explaining the trade-off for this particular subject among the layouts given:")

#: told to the user when a rule-chosen stretched layout could not be certified
#: and the plain layout was folded instead (spec 2026-10-22 §6.4)
STRETCH_FALLBACK_NOTE = ("The stretched layout could not be certified flat-foldable, "
                         "so the plain layout was folded instead.")
#: ... and when the user chose the stretched layout and it failed that way: an
#: explicit choice has no fallback, so the card is shown again with this note
STRETCH_FAILED_NOTE = ("The stretched layout could not be certified flat-foldable. "
                       "Choose another layout.")
OFF_GRID_COST = ("some creases are off the grid, at angles below 45°, so it is harder "
                 "to precrease and collapse")

LABELS = {"symmetric": "Mirror-symmetric", "stretched": "Mirror-symmetric, stretched",
          "smaller": "Smaller grid"}


def fallback_note(layout_record: dict | None) -> str | None:
    """STRETCH_FALLBACK_NOTE when a run record's `layout` block says a
    rule-chosen stretched layout failed certification and another folded."""
    r = layout_record or {}
    if r.get("reason") == "fallback" and "StretchUncertified" in str(r.get("fallback_error", "")):
        return STRETCH_FALLBACK_NOTE
    return None


def _pct(x) -> str:
    return f"{round(float(x) * 100)}%"


def _opt(summary: dict, which: str):
    o = summary.get(which)
    return o if o and o.get("metrics") is not None else None


def _grid(summary: dict, which: str):
    o = summary.get(which)
    return o["grid"] if o else None


def _gain(summary: dict, which: str) -> float | None:
    """Size gain of option `which` over the plain symmetric layout.  Without a
    stretched option the smaller layout's gain is `summary["gain"]`, as before
    this slice (byte-identical text); otherwise it is computed from the grids
    (`summary["gain"]` is None without a U)."""
    if which == "smaller" and not summary.get("stretched") and summary.get("gain") is not None:
        return float(summary["gain"])
    s, g = _grid(summary, "symmetric"), _grid(summary, which)
    return None if not s or not g else s / g


def _present(summary: dict) -> list[str]:
    return [k for k in ("symmetric", "stretched", "smaller") if summary.get(k)]


def _smaller_option(summary: dict) -> dict:
    sm, sy = summary["smaller"], _opt(summary, "symmetric")
    m, gain = sm["metrics"], _gain(summary, "smaller")
    pros = [f"the folded model is {gain:.2f}× larger from the same sheet"] if gain and gain > 1 else []
    cons = ["the crease pattern is not mirror-symmetric, so left and right sides fold differently"]
    if sy:
        a, b = m["creases"], sy["metrics"]["creases"]
        if a < b:
            pros.append(f"fewer creases ({a} against {b})")
        if m["mean_layers"] < sy["metrics"]["mean_layers"]:
            pros.append(f"fewer layers on average ({m['mean_layers']:.1f} against "
                        f"{sy['metrics']['mean_layers']:.1f})")
    return {"id": "smaller", "label": LABELS["smaller"], "grid": sm["grid"],
            "pros": pros, "cons": cons}


def _stretched_option(summary: dict) -> dict:
    t, sy = summary["stretched"], _opt(summary, "symmetric")
    gain = _gain(summary, "stretched")
    pros = ["left and right limbs still mirror each other"]
    if gain and gain > 1:
        pros.insert(0, f"a grid of {t['grid']} against {summary['symmetric']['grid']}: "
                       f"folds a model {gain:.2f}× larger than the plain symmetric layout")
    cons = [OFF_GRID_COST]
    m = t.get("metrics")
    if m and sy and m.get("creases") is not None:
        a, b = m["creases"], sy["metrics"]["creases"]
        if a > b:
            cons.append(f"more creases ({a} against {b})")
    return {"id": "stretched", "label": LABELS["stretched"], "grid": t["grid"],
            "pros": pros, "cons": cons}


def _symmetric_option(summary: dict) -> dict:
    sy, sm = summary["symmetric"], _opt(summary, "smaller")
    m = sy["metrics"]
    pros = ["left and right limbs mirror each other, so each paired step is folded the same way twice"]
    cons = []
    gains = [g for g in (_gain(summary, "stretched"), _gain(summary, "smaller")) if g]
    if gains and max(gains) > 1:
        cons.append(f"the folded model comes out {_pct(1 - 1 / max(gains))} smaller")
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
    return {"id": "symmetric", "label": LABELS["symmetric"], "grid": sy["grid"],
            "pros": pros, "cons": cons}


def card(summary: dict) -> dict:
    """The question card: the recommended option first, numbers-only pros/cons.
    Up to three options (S, T, U); each one's size gain is over S, from the grids."""
    make = {"smaller": _smaller_option, "stretched": _stretched_option,
            "symmetric": _symmetric_option}
    built = {k: make[k](summary) for k in ("smaller", "stretched", "symmetric") if summary.get(k)}
    rec = summary["recommended"]
    order = [rec] + [k for k in built if k != rec]
    return {"question": "Which layout should the model be folded from?",
            "options": [{**built[k], "recommended": k == rec} for k in order]}


def _pairs_text(pairs: list) -> str:
    if not pairs:
        return "no bilateral leaf pairs"
    return "bilateral leaf pairs: " + ", ".join(f"{a}/{b}" for a, b in pairs)


def _size_phrase(summary: dict, which: str) -> str:
    g = _gain(summary, which)
    return f"a model {g:.2f}× larger" if g and g > 1 else "no larger a model"


def template_explanation(summary: dict, subject: str, pairs: list) -> str:
    rec = summary["recommended"]
    mirror = ("its paired limbs mirror each other in the symmetric layout"
              if pairs else "it has no mirrored limb pairs to keep symmetric")
    parts = [f"For the {subject}, the symmetric layout needs a grid of {summary['symmetric']['grid']}"]
    t, u = summary.get("stretched"), summary.get("smaller")
    if t and u:
        parts.append(f", the stretched layout {t['grid']} ({_size_phrase(summary, 'stretched')}, with "
                     f"some creases off the grid) and the smaller layout {u['grid']} "
                     f"({_size_phrase(summary, 'smaller')})")
    elif t:
        parts.append(f" and the stretched layout only {t['grid']}, so the same sheet folds into "
                     f"{_size_phrase(summary, 'stretched')}, though some of its creases are off the grid")
    elif u:
        parts.append(f" and the smaller layout only {u['grid']}, so the same sheet folds into "
                     f"{_size_phrase(summary, 'smaller')}")
    parts.append(f". The {rec} layout is recommended")
    if rec == "stretched":
        parts.append("; it keeps the mirror symmetry of the paired limbs while still gaining size, "
                     "at the price of harder creases.")
    elif rec == "smaller":
        parts.append(f"; {mirror}, which is what the larger grid pays for.")
    else:
        parts.append(f"; {mirror}.")
    return "".join(parts)


def _ask(summary: dict, subject: str, pairs: list) -> str:
    if not summary.get("stretched"):
        return _ask_two(summary, subject, pairs)
    grids = "; ".join(
        f"{k} grid: {summary[k]['grid']}" +
        ("" if k == "symmetric" or not (_gain(summary, k) or 0) > 1 else
         f" (folds a model {_gain(summary, k):.2f}× larger than the symmetric layout)")
        for k in _present(summary))
    lines = [f"Subject: {subject}", _pairs_text(pairs), grids + ".",
             f"Recommendation (fixed): the {summary['recommended']} layout."]
    for which in _present(summary):
        m = (summary[which] or {}).get("metrics")
        if which == "stretched":
            # no "extra paper" for T: slack_fraction's floor (the minimum
            # flap squares) is undercut by a stretch's overlap, so it
            # undercounts what the stretch buys (spec 2026-10-22 §1, §9.5)
            if m and all(k in m for k in ("mean_layers", "creases")):
                lines.append(f"{which}: mean layers {m['mean_layers']:.1f}, "
                             f"creases {m['creases']}")
        elif m and all(k in m for k in ("slack_fraction", "mean_layers", "creases")):
            lines.append(f"{which}: extra paper {_pct(m['slack_fraction'])}, mean layers "
                         f"{m['mean_layers']:.1f}, creases {m['creases']}")
    if summary.get("stretched"):
        lines.append(f"stretched: {OFF_GRID_COST}.")
    return "\n".join(lines) + "\n\nExplain the trade-off for this subject."


def _ask_two(summary: dict, subject: str, pairs: list) -> str:
    """Slice 1's prompt, byte for byte (no stretched option)."""
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
            client.run_turn(system_prompt(summary), [{"role": "user", "content": _ask(summary, subject, pairs)}], TOOL),
            timeout=EXPLAIN_TIMEOUT_S)
        if not r.tool_calls:
            return fallback
        text = str(json.loads(r.tool_calls[0].function.arguments).get("explanation", "")).strip()
    except Exception:
        return fallback
    return text[:MAX_CHARS].strip() or fallback
