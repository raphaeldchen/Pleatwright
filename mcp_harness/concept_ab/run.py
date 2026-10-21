"""Generate and lift every cell of the experiment, resumably (spec §1, §3).

A cell is one (arm, subject, round): `<root>/<arm>/<slug>/r<n>/` holding
`concept.*`, `mesh.glb` and `meta.json`. A cell with a mesh is done and is
skipped; a cell with a concept but no mesh is only re-lifted, so a quota stop
never re-buys an image. The lift is always mesh_acquire's TwoStageProvider with
`reuse_concept=True` and HUNYUAN_SHAPE_KWARGS, so it is identical for every arm:
arm A's provider draws its own FLUX concept first, the Gemini arms write theirs
before calling it.
"""
from __future__ import annotations

import json
import os
import shutil
import time
from dataclasses import dataclass, field

import gemini_image
import mesh_acquire
import subject_rewrite
from concept_ab import arms as A


@dataclass
class RunReport:
    done: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)
    #: None, or why the run stopped early: "hf_quota", "gemini_quota", "budget".
    stopped: str | None = None
    stop_note: str = ""


class QuotaStop(Exception):
    def __init__(self, kind: str, note: str):
        super().__init__(note)
        self.kind = kind


def default_provider(seed: int):
    """The fixed lift; `seed` only feeds arm A's FLUX stage (Hunyuan stays 1234)."""
    return mesh_acquire.TwoStageProvider(
        image_kwargs={**mesh_acquire.FLUX_IMAGE_KWARGS, "seed": seed},
        mesh_kwargs=dict(mesh_acquire.HUNYUAN_SHAPE_KWARGS),
        prompt_template=mesh_acquire.CONCEPT_PROMPT_TEMPLATE,
        token=os.environ.get("HF_TOKEN") or None, reuse_concept=True)


def concept_path(cell: str) -> str | None:
    for ext in (".png", ".webp", ".jpg", ".jpeg"):
        p = os.path.join(cell, "concept" + ext)
        if os.path.isfile(p) and os.path.getsize(p) > 0:
            return p
    return None


def _hf_quota(e: BaseException) -> bool:
    return any(x is not None and mesh_acquire._is_hf_quota_exhaustion_error(x)
               for x in (e, e.__cause__))


def _gemini_quota(e: BaseException) -> bool:
    return isinstance(e, gemini_image.GeminiImageError) and "HTTP 429" in str(e)


async def _anatomy(root: str, subject: str, llm) -> str:
    path = os.path.join(root, "anatomy", A.slug(subject) + ".txt")
    if os.path.exists(path):
        return open(path).read().strip()
    text = await subject_rewrite.anatomy(llm, subject)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)
    return text


def _write_meta(cell: str, meta: dict) -> None:
    meta["utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(os.path.join(cell, "meta.json"), "w") as f:
        json.dump(meta, f, indent=1)


async def _default_pick(paths, anatomy):
    import llm_client
    from concept_ab import judge
    client = llm_client.LLMClient.from_env(judge.JUDGE_MODEL)
    return await judge.pick(client, paths, anatomy)


async def run_cells(root: str, arms: list[str], round_: int, subjects: list[str], *,
                    llm=None, image_fn=gemini_image.generate_image,
                    provider_factory=default_provider, ledger: A.Ledger | None = None,
                    winner: str | None = None, pick_fn=None) -> RunReport:
    """Make every missing cell. Stops early on a quota or the spend cap."""
    ledger = ledger or A.Ledger(os.path.join(root, "ledger.json"))
    pick_fn = pick_fn or _default_pick
    rep = RunReport()
    for arm_name in arms:
        arm = A.get_arm(arm_name, winner)
        for subject in subjects:
            cid = A.cell_id(arm_name, subject, round_)
            cell = A.cell_dir(root, arm_name, subject, round_)
            if os.path.isfile(os.path.join(cell, "mesh.glb")):
                rep.skipped.append(cid)
                continue
            os.makedirs(cell, exist_ok=True)
            try:
                await _make_cell(root, cell, cid, arm, subject, round_, llm=llm,
                                 image_fn=image_fn, provider_factory=provider_factory,
                                 ledger=ledger, pick_fn=pick_fn)
                rep.done.append(cid)
            except A.BudgetExceeded as e:
                rep.stopped, rep.stop_note = "budget", str(e)
                return rep
            except Exception as e:                               # noqa: BLE001
                if _hf_quota(e):
                    rep.stopped, rep.stop_note = "hf_quota", f"{cid}: {e}"
                    return rep
                if _gemini_quota(e):
                    rep.stopped, rep.stop_note = "gemini_quota", f"{cid}: {e}"
                    return rep
                rep.failed[cid] = f"{type(e).__name__}: {e}"
    return rep


async def _make_cell(root, cell, cid, arm, subject, round_, *, llm, image_fn,
                     provider_factory, ledger, pick_fn):
    seed = A.seed_for(arm.name, round_)
    meta_path = os.path.join(cell, "meta.json")
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else None
    if meta is None:
        anatomy = await _anatomy(root, subject, llm) if arm.uses_anatomy else None
        prompt = A.concept_prompt_for(arm, subject, anatomy)
        meta = {"arm": arm.name, "subject": subject, "round": round_, "seed": seed,
                "prompt": prompt, "anatomy_text": anatomy, "image_model": arm.image_model,
                "usage": None}
    if concept_path(cell) is None and arm.image_model != A.FLUX:
        if arm.candidates == 1:
            ledger.ensure(1, cid)
            g = image_fn(meta["prompt"], os.path.join(cell, "concept.png"), seed=seed)
            ledger.charge(1, cid)
            ledger.record_usage(cid, g.usage)
            meta["usage"] = g.usage
        else:
            await _best_of(cell, cid, arm, meta, image_fn=image_fn, ledger=ledger,
                           pick_fn=pick_fn)
    _write_meta(cell, meta)      # before the lift: a quota stop still leaves the record
    provider_factory(seed).generate(subject, cell)


async def _best_of(cell, cid, arm, meta, *, image_fn, ledger, pick_fn):
    paths, usage = [], []
    for i in range(arm.candidates):
        p = os.path.join(cell, f"candidate_{i}.png")
        if not os.path.isfile(p):
            ledger.ensure(1, f"{cid} candidate {i}")
            g = image_fn(meta["prompt"], p, seed=A.seed_for("E", meta["round"], i))
            ledger.charge(1, f"{cid} candidate {i}")
            ledger.record_usage(f"{cid}#{i}", g.usage)
            usage.append(g.usage)
        paths.append(p)
    choice = await pick_fn(paths, meta["anatomy_text"])
    with open(os.path.join(cell, "pick.json"), "w") as f:
        json.dump(choice, f, indent=1)
    shutil.copyfile(paths[choice["index"]], os.path.join(cell, "concept.png"))
    meta.update(usage=usage, candidates=[os.path.basename(p) for p in paths],
                picked=choice["index"], none_acceptable=choice.get("none_acceptable", False))
