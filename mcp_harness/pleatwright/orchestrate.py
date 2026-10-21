"""COrigami §3.6 (LLM-orchestrated shaping) and §3.8 (VLM feedback).

COrigami fine-tunes Gemini 2.5 Flash Lite with RL to emit, in ONE step, the
tool-use parameters for all flaps (simple folds, narrowing) on top of the
heuristic tree shaping; the reward is the VLM single-model score with a
validity penalty:

    r = -1                         if no tool call / not flat-foldable /
                                      simulation error
    r = score/10 + min(n/10, 1)*0.6   otherwise (n = successful tool calls)

Fine-tuning a frontier model is not available here, so this module runs the
same generation step at inference time (the paper's "standard prompting"
arm, which it reports replicates the heuristic baseline) and uses the same
reward as a SELECTION criterion over K proposals plus the heuristic baseline
-- the paper's other use of the VLM score (§3.8, "primary selection
criterion within the pipeline").  Both the policy and the judge are Claude
models over the project's Anthropic key (`env_config` / `.env`).

The prompts paraphrase App. I's structure (role, appendage count, topology,
proportion, differentiation, aesthetics; reasoning first, score as <n>).
"""
from __future__ import annotations

import base64
import io
import json
import os
import re
from dataclasses import dataclass, field

TOOLS = [
    {"name": "simple_fold",
     "description": "Bend one stick: an extra simple fold across the folded flap at a fraction "
                    "of its length, rotating everything beyond it by angle_deg about the axis "
                    "across the paper (positive = valley).",
     "parameters": {"type": "object", "properties": {
         "stick": {"type": "string"}, "position": {"type": "number", "minimum": 0, "maximum": 1},
         "angle_deg": {"type": "number", "minimum": -170, "maximum": 170}},
         "required": ["stick", "position", "angle_deg"]}},
    {"name": "narrow",
     "description": "Narrow a terminal flap with the clip-pattern algorithm. template 'asym2' "
                    "halves its width (Fig. 13d), 'asym4' quarters it. Costs about one unit of "
                    "length per halving.",
     "parameters": {"type": "object", "properties": {
         "stick": {"type": "string"}, "template": {"type": "string", "enum": ["asym2", "asym4"]}},
         "required": ["stick", "template"]}},
]

POLICY_PROMPT = """You are orchestrating shaping tools for a box-pleated origami model.
The flat base has already been shaped by the tree-shaping algorithm so that every stick of
the stick figure below points in its stick-figure direction; every flap is a strip one grid
unit wide. Your job is to refine it so it reads more like a real {subject}: narrow
appendages that should be thin (legs, antennae, tails, beaks) and add bends where the real
animal's limbs bend.

Stick figure (lengths in grid units, angles in degrees, +Y up):
{stick_json}

Terminal sticks (narrowable): {leaves}

Available tools (JSON schemas):
{tools}

Example output:
[{{"tool": "narrow", "stick": "leg_front_L_foot", "template": "asym2"}},
 {{"tool": "simple_fold", "stick": "tail", "position": 0.5, "angle_deg": 30}}]

Output ONLY a JSON list of tool calls, for all flaps at once."""

JUDGE_PROMPT = """You are a strict judge of a 3-D simulated origami fold, judging anatomy
and proportion rather than colour or texture (it is one sheet of monochrome paper).
Target object: "{subject}". The images show the folded model from seven viewpoints;
some views may be uninformative, so weight the views that show the form most clearly.

Work through: (1) the features you can see; (2) against a real {subject}: the number of
appendages, whether they leave the body where they should, their proportions, whether
head / body / limbs are distinguishable, and the neatness and symmetry of the folds;
(3) structural failures -- tangled or overlapping flaps hiding the anatomy, an
undifferentiated body mass, intersecting or crumpled geometry, severe asymmetry.

Score 0-10: 0 unrecognisable; 2 vague mass without distinct parts; 4 recognisable attempt
with major deformities or missing parts; 6 right class but wrong limb count or badly
skewed proportions; 8 strong resemblance, correct parts, somewhat blocky; 10 anatomically
accurate in count, shape and proportion.

Give your reasoning, then the score in angle brackets, e.g. <6>."""


class Unavailable(Exception):
    """The LLM/VLM endpoint cannot be used (no key, dead key, network)."""


@dataclass
class Candidate:
    name: str
    calls: list
    record: dict = field(default_factory=dict)
    images: list = field(default_factory=list)
    score: float | None = None
    reward: float | None = None
    reasoning: str = ""


def _client():
    try:
        import env_config
        env_config.load_env()
    except Exception:
        pass
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise Unavailable("ANTHROPIC_API_KEY not set")
    from openai import OpenAI
    headers = {}
    if os.environ.get("ANTHROPIC_WORKSPACE_ID"):
        headers["anthropic-workspace-id"] = os.environ["ANTHROPIC_WORKSPACE_ID"]
    return OpenAI(api_key=key, base_url="https://api.anthropic.com/v1/",
                  default_headers=headers), os.environ.get("LLM_MODEL", "claude-sonnet-5")


def _chat(messages, max_tokens=2000):
    client, model = _client()
    try:
        r = client.chat.completions.create(model=model, max_tokens=max_tokens, messages=messages)
    except Exception as exc:  # authentication / network: the caller falls back
        raise Unavailable(repr(exc)[:300])
    return r.choices[0].message.content or ""


def propose(sf, k: int = 3, chat=None) -> list:
    """Single-step tool-parameter generation (the policy).  Returns K lists of
    tool calls."""
    chat = chat or _chat
    leaves = [s.name for s in sf.sticks if not any(t.start == s.end for t in sf.sticks)]
    prompt = POLICY_PROMPT.format(subject=sf.name, stick_json=json.dumps(sf.to_corigami_json(), indent=1),
                                  leaves=", ".join(leaves), tools=json.dumps(TOOLS, indent=1))
    out = []
    for i in range(k):
        txt = chat([{"role": "user", "content": prompt}])
        m = re.search(r"\[.*\]", txt, re.S)
        try:
            calls = json.loads(m.group(0)) if m else []
        except json.JSONDecodeError:
            calls = []
        out.append([c for c in calls if isinstance(c, dict)])
    return out


def judge(subject: str, images: list, chat=None) -> tuple:
    """Single Model Evaluation Mode: 7 rendered views -> (score 0-10, text)."""
    chat = chat or _chat
    content = [{"type": "text", "text": JUDGE_PROMPT.format(subject=subject)}]
    for png in images:
        b64 = base64.b64encode(png).decode()
        content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}})
    txt = chat([{"role": "user", "content": content}], max_tokens=1500)
    m = re.findall(r"<\s*(\d+(?:\.\d+)?)\s*>", txt)
    score = float(m[-1]) if m else None
    return score, txt


def reward(score, n_calls, valid) -> float:
    """§3.6 reward: -1 if invalid, else VLM score (normalised) + diversity."""
    if not valid or score is None:
        return -1.0
    return score / 10.0 + min(n_calls / 10.0, 1.0) * 0.6


def split_calls(calls):
    narrow = [(c["stick"], c.get("template", "asym2")) for c in calls
              if c.get("tool") == "narrow" and "stick" in c]
    extra = [(c["stick"], c.get("position", 0.5), c.get("angle_deg", 0.0)) for c in calls
             if c.get("tool") == "simple_fold" and "stick" in c]
    return narrow, extra


def views_png(polys) -> list:
    """The seven model views, one PNG each (what the judge sees)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from . import render as R
    lims = R.model_limits(polys)
    out = []
    for view in R.VIEWS:
        fig = plt.figure(figsize=(4, 4), dpi=100)
        ax = fig.add_subplot(1, 1, 1, projection="3d")
        R.draw_model(ax, polys, view, lims=lims)
        fig.subplots_adjust(0, 0, 1, 1)
        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        plt.close(fig)
        out.append(buf.getvalue())
    return out
