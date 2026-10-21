"""What the experiment compares, and where each result lives.

Spec: docs/superpowers/specs/2026-10-16-concept-image-quality-design.md §1, §3.
Hunyuan3D-2 is fixed across every arm; only the concept image varies.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, replace

import mesh_acquire

#: The 17 library subjects, in manifest order (~/Downloads/photo_meshes/manifest.json).
SUBJECTS = ("dog", "cat", "horse", "lizard", "frog", "bird", "starfish", "spider",
            "octopus", "dolphin", "guinea pig", "rabbit", "bat", "elephant", "ant",
            "scorpion", "crab")

NANO_BANANA = "gemini-nano-banana-2.1"
FLUX = "flux-schnell"

#: Arm D: the shipped template with its render/studio phrasing swapped for a
#: wildlife photograph, keeping every part the 2026-10-07 A/B found
#: load-bearing (full body, single, entire animal in frame, plain background).
PHOTO_TEMPLATE = (
    "A full-body wildlife photograph of a single {subject}, three-quarter side "
    "view, the entire animal in frame with every leg, the tail and all "
    "appendages clearly visible and separated from the body, centered, against "
    "a plain uncluttered background, natural daylight, sharp focus, no props, "
    "no text")


@dataclass(frozen=True)
class Arm:
    name: str
    image_model: str
    template: str
    uses_anatomy: bool
    candidates: int = 1


ARMS = {
    "A": Arm("A", FLUX, mesh_acquire.CONCEPT_PROMPT_TEMPLATE, False),
    "B": Arm("B", NANO_BANANA, mesh_acquire.CONCEPT_PROMPT_TEMPLATE, False),
    "C": Arm("C", NANO_BANANA, mesh_acquire.CONCEPT_PROMPT_TEMPLATE, True),
    "D": Arm("D", NANO_BANANA, PHOTO_TEMPLATE, True),
}


def arm_e(winner: str) -> Arm:
    """Best of 4: the round-1 winner among C and D, drawn four times."""
    return replace(ARMS[winner], name="E", candidates=4)


def get_arm(name: str, winner: str | None = None) -> Arm:
    if name == "E":
        if winner not in ("C", "D"):
            raise ValueError("arm E needs --winner C or D (the round-1 winner)")
        return arm_e(winner)
    return ARMS[name]


def slug(subject: str) -> str:
    return subject.lower().replace(" ", "_")


def seed_for(arm: str, round_: int, candidate: int = 0) -> int:
    """Round 1 = 11 (FLUX's shipped seed), round 2 = 22; arm E candidates 101-104."""
    if arm == "E":
        return 101 + candidate
    return 11 * round_


def cell_dir(root: str, arm: str, subject: str, round_: int) -> str:
    return os.path.join(root, arm, slug(subject), f"r{round_}")


def cell_id(arm: str, subject: str, round_: int) -> str:
    return f"{arm}/{slug(subject)}/r{round_}"


def concept_prompt_for(arm: Arm, subject: str, anatomy_text: str | None) -> str:
    """The anatomy text fills {subject}, exactly as a mesh-review description does."""
    if arm.uses_anatomy:
        if not anatomy_text:
            raise ValueError(f"arm {arm.name} needs the anatomy text for {subject!r}")
        return mesh_acquire.concept_prompt(anatomy_text, arm.template)
    return mesh_acquire.concept_prompt(subject, arm.template)


_CHECKLIST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "anatomy_checklist.json")


def load_checklist(path: str = _CHECKLIST) -> dict[str, list[dict]]:
    with open(path) as f:
        return {k: v for k, v in json.load(f).items() if not k.startswith("_")}


def checklist_text(subject: str, checklist: dict | None = None) -> str:
    """The checklist as anatomy prose the judge reads, e.g. '8 walking legs (4 per side)'."""
    parts = (checklist or load_checklist())[subject]
    items = [f"{p['count']} {p['part']}" + (f" ({p['note']})" if p.get("note") else "")
             for p in parts]
    return f"{subject}: " + "; ".join(items)


#: Measured 2026-10-16 on the live probe: 1,120 image tokens at $30/M plus ~1,114
#: text+thinking tokens at $7.50/M (thinking is billed as output) = ~$0.042 an
#: image, under the spec's stop line of 2 x $0.034 (gemini_image docstring).
PRICE_USD = 0.042


class BudgetExceeded(RuntimeError):
    """The next paid image would take the experiment past its cap."""


class Ledger:
    """Persistent spend record: Gemini images at a planning price, under a cap.

    Spec §3: cap $15. The price is the measured one, PRICE_USD."""

    def __init__(self, path: str, cap_usd: float = 15.0, price_usd: float = PRICE_USD):
        self.path, self.cap, self.price = path, cap_usd, price_usd
        self._d = {"charges": [], "usage": {}}
        if os.path.exists(path):
            with open(path) as f:
                self._d = json.load(f)

    def spent(self) -> float:
        return sum(c["usd"] for c in self._d["charges"])

    def ensure(self, n_images: int, note: str) -> None:
        """Raise BudgetExceeded if `n_images` more would pass the cap."""
        if self.spent() + n_images * self.price > self.cap + 1e-9:
            raise BudgetExceeded(f"{note}: ${self.spent():.2f} spent; {n_images} more image(s) "
                                 f"at ${self.price} would pass the ${self.cap:.2f} cap")

    def charge(self, n_images: int, note: str) -> None:
        self.ensure(n_images, note)
        usd = n_images * self.price
        self._d["charges"].append({"note": note, "images": n_images, "usd": usd,
                                   "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
        self._save()

    def record_usage(self, cell: str, usage: dict) -> None:
        self._d["usage"][cell] = usage
        self._save()

    def _save(self) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        tmp = self.path + ".part"
        with open(tmp, "w") as f:
            json.dump(self._d, f, indent=1)
        os.replace(tmp, self.path)
