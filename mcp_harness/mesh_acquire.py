"""Query -> rough 3D mesh acquisition (sub-project A).

Turns a text prompt into a rough .glb behind a swappable MeshProvider protocol.
Providers (MESH_PROVIDER):
  fake  - offline committed meshes (default; tests/CI, no spend)
  meshy - hosted Meshy text-to-3D REST (needs MESHY_API_KEY)
  hf    - free Gradio ZeroGPU Space text-to-3D (needs `pip install gradio_client`;
          configurable via HF_SPACE_ID / HF_API_NAME; optional HF_TOKEN for the
          authenticated free quota)

Every cached mesh carries a provenance sidecar (`meta.json` beside `mesh.glb`)
naming the provider, the raw prompt, the endpoint, a UTC timestamp and the
.glb's sha256 + byte size; `verify_mesh_meta` rechecks it and
`backfill_mesh_cache` attributes meshes generated before the sidecar existed
(`python mesh_acquire.py --backfill`).

⚠ SIDECARS ARE NOT COMMITTED. `generated_meshes/` is gitignored, so a fresh
checkout has no sidecar for any mesh and the cache is unattributed on disk
until someone runs `--backfill`. The durable, committed artifact is
`KNOWN_CACHE_PROMPTS` below -- the recovery TABLE, not its output.

⚠ A key directory is often a SYMLINK. Agent worktrees bootstrap
`generated_meshes/<key>` as a symlink to `<key>` in a sibling checkout, which
is the only way the live-provider meshes are reachable from a worktree. Writing
provenance through such an alias is deliberate and required -- see
`is_same_key_alias`; refusing it would silently disable the cache-hit path in
the environment where nearly all of this project's work happens.

See docs/superpowers/specs/2026-06-25-huggingface-mesh-provider-design.md.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import shutil
import tempfile
import time
import urllib.error
import urllib.request
from typing import Protocol

_HERE = os.path.dirname(os.path.abspath(__file__))

# The offline FakeMeshProvider serves committed meshes: 17 subjects that
# tencent/Hunyuan3D-2 generated from photographs (fixtures/meshes/SOURCES.md).
# A prompt naming a subject gets that subject's mesh; a few keywords map near
# misses (heuristic substrings, a test fake, not a classifier); anything else
# gets the dog.
FAKE_MESH_DIR = os.path.join(_HERE, "fixtures", "meshes")
FAKE_MESH_DEFAULT = "dog"
_FAKE_KEYWORDS = [
    (("insect", "bug", "beetle", "wasp"), "ant"),
    (("eagle", "owl", "sparrow", "hawk"), "bird"),
    (("fish", "shark", "trout", "salmon", "whale"), "dolphin"),
    (("puppy", "wolf", "fox"), "dog"),
    (("kitten",), "cat"),
    (("bunny", "hare"), "rabbit"),
    (("toad",), "frog"),
    (("pony",), "horse"),
]


def fake_mesh_subjects() -> list[str]:
    """The subjects that have a committed fake mesh (file stems)."""
    return sorted(f[:-4] for f in os.listdir(FAKE_MESH_DIR) if f.endswith(".glb"))


def fake_mesh_path(prompt: str = "") -> str:
    """Path to the committed mesh the fake provider serves for `prompt`."""
    p = prompt.lower()
    subject = next((s for s in fake_mesh_subjects()
                    if re.search(rf"\b{re.escape(s.replace('_', ' '))}", p)), None)
    if subject is None:
        subject = next((s for keywords, s in _FAKE_KEYWORDS
                        if any(k in p for k in keywords)), FAKE_MESH_DEFAULT)
    return os.path.join(FAKE_MESH_DIR, f"{subject}.glb")


class MeshProvider(Protocol):
    """Turns a text prompt into a .glb on disk and returns its path."""

    def generate(self, prompt: str, out_dir: str) -> str: ...


class FakeMeshProvider:
    """Test/offline provider: copies a committed mesh into out_dir.

    Any valid mesh exercises the downstream chain deterministically; a committed
    Hunyuan3D-2 mesh stands in for a real API draw at no cost (`fake_mesh_path`).
    """

    def __init__(self, fixture_path: str | None = None):
        # None -> choose a mesh per prompt (offline, query-specific). An
        # explicit path pins one mesh regardless of prompt (used by tests).
        self.fixture_path = fixture_path

    def generate(self, prompt: str, out_dir: str) -> str:
        out_dir = os.path.abspath(out_dir)
        os.makedirs(out_dir, exist_ok=True)
        dest = os.path.join(out_dir, "mesh.glb")
        src = self.fixture_path or fake_mesh_path(prompt)
        shutil.copyfile(src, dest)
        return dest


MESHY_BASE = "https://api.meshy.ai/openapi/v2/text-to-3d"


class _UrllibHttp:
    """Minimal stdlib HTTP transport (no `requests` dependency)."""

    def post_json(self, url, headers, payload):
        data = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data, headers={
            **headers, "Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())

    def get_json(self, url, headers):
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())

    def download(self, url, dest_path):
        with urllib.request.urlopen(url) as r, open(dest_path, "wb") as f:
            shutil.copyfileobj(r, f)


class MeshyProvider:
    """Hosted Meshy text-to-3D: submit a preview task, poll, download the .glb."""

    def __init__(self, api_key, *, base_url=MESHY_BASE, poll_interval=5.0,
                 timeout=300.0, http=None, sleep=time.sleep):
        self.api_key = api_key
        self.base_url = base_url
        self.poll_interval = poll_interval
        self.timeout = timeout
        self.http = http or _UrllibHttp()
        self.sleep = sleep

    def _headers(self):
        return {"Authorization": f"Bearer {self.api_key}"}

    def generate(self, prompt: str, out_dir: str) -> str:
        try:
            task_id = self.http.post_json(self.base_url, self._headers(), {
                "mode": "preview", "prompt": prompt, "art_style": "realistic"})["result"]
        except urllib.error.URLError as e:
            raise RuntimeError(f"Meshy request failed for prompt {prompt!r}: {e}") from e
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                status = self.http.get_json(
                    f"{self.base_url}/{task_id}", self._headers())
            except urllib.error.URLError as e:
                raise RuntimeError(f"Meshy poll failed for prompt {prompt!r}: {e}") from e
            state = status.get("status")
            if state == "SUCCEEDED":
                break
            if state == "FAILED":
                msg = (status.get("task_error") or {}).get("message", "unknown")
                raise RuntimeError(f"Meshy task {task_id} failed: {msg}")
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"Meshy task {task_id} did not complete in {self.timeout}s")
            self.sleep(self.poll_interval)

        glb_url = (status.get("model_urls") or {}).get("glb")
        if not glb_url:
            raise RuntimeError(f"Meshy task {task_id} SUCCEEDED with no glb url")
        os.makedirs(out_dir, exist_ok=True)
        dest = os.path.join(out_dir, "mesh.glb")
        try:
            self.http.download(glb_url, dest)
        except urllib.error.URLError as e:
            raise RuntimeError(f"Meshy download failed for prompt {prompt!r}: {e}") from e
        if not os.path.isfile(dest) or os.path.getsize(dest) == 0:
            raise RuntimeError(f"Meshy task {task_id} produced an empty download")
        return dest


DEFAULT_HF_SPACE = "hysts/Shap-E"   # live text-to-3D mesh Space (OpenAI Shap-E)
DEFAULT_HF_API = "/text-to-3d"      # verify via gradio_client Client(space).view_api()


def _default_hf_client_factory(space_id, token):
    from gradio_client import Client  # lazy: only needed for a real hf call
    import httpx                      # gradio_client dependency, so present
    # Connect-oriented timeout ONLY: a hung/unreachable Space fails fast, but
    # read stays UNLIMITED because Shap-E generations + the ZeroGPU queue
    # legitimately take minutes and a read timeout would kill the SSE/polling
    # wait. httpx_kwargs forwards to httpx.Client/stream/get/post
    # (gradio_client 2.5.0).
    return Client(space_id, token=token,  # gradio_client>=1.0 kwarg (was hf_token)
                  httpx_kwargs={"timeout": httpx.Timeout(30.0, read=None)})


#: ZeroGPU says "no GPU was available" when the SHARED POOL is busy. That is a
#: queue, not a budget: it clears on its own, usually within a minute, and the
#: right response is to wait and retry. It must never be read as exhaustion --
#: measured 2026-08-22, that single confusion drew 1 arm of a 12-arm bake-off
#: and marked the other 11 "UNRUN, reason quota" when none was out of quota.
_HF_CONTENTION_MARKERS = (
    "no gpu was available",
    "gpu was not available",
    "gpu is not available",
    "no gpu is available",
)


def _is_hf_gpu_contention_error(exc: Exception) -> bool:
    """The shared ZeroGPU pool was busy. TRANSIENT -- retrying is correct."""
    return any(m in str(exc).lower() for m in _HF_CONTENTION_MARKERS)


#: What the ZeroGPU scheduler ACTUALLY says when the budget is spent. Positive
#: markers only -- this predicate never infers exhaustion from an exception's
#: TYPE, which is the inference that has now been wrong twice.
_HF_EXHAUSTION_MARKERS = (
    "exceeded your free zerogpu quota",
    "exceeded your zerogpu quota",
    "gpu quota exceeded",
    "gpu task aborted",
    "0s left",
)


def _is_hf_quota_exhaustion_error(exc: Exception) -> bool:
    """The Space SAID the budget is spent, in its own words.

    Distinct from `_is_hf_quota_error` on purpose, because the two answer
    different questions and only one of them should ever stop a whole matrix:

        _is_hf_quota_error            -> "should THIS call be retried?"
        _is_hf_quota_exhaustion_error -> "is the ACCOUNT out of budget?"

    The first may reasonably answer yes for an opaque AppError (a Space that
    raised once will likely raise again). The second must not, and measured
    2026-08-24 that difference is worth a full bake-off: VAST-AI/TripoSG is
    simply BROKEN -- it returns a contentless AppError on every endpoint,
    including /run_segmentation -- and reading that as exhaustion marked nine
    innocent arms UNRUN and stopped the run. Nothing was out of quota.
    """
    msg = str(exc).lower()
    if _is_hf_gpu_contention_error(exc):
        return False
    return any(m in msg for m in _HF_EXHAUSTION_MARKERS)


def _is_hf_quota_error(exc: Exception) -> bool:
    """The account's GPU budget is spent: retrying is pointless until the free
    ZeroGPU window resets.

    ⚠ CONTENTION IS CHECKED FIRST AND WINS. Two ZeroGPU failures arrive on the
    same channel and read alike, but need OPPOSITE responses:

        "exceeded your free ZeroGPU quota (0s left)"  -> terminal, give up
        "No GPU was available after 60s"              -> busy pool, RETRY

    The second contains "gpu" and arrives as an AppError, so the previous
    `"gpu" in msg or isinstance(exc, AppError)` test claimed both. Everything
    that is not contention classifies exactly as it did before.
    """
    if _is_hf_gpu_contention_error(exc):
        return False
    if _is_hf_quota_exhaustion_error(exc):
        return True
    try:
        from gradio_client import exceptions as _gc_exc
        if isinstance(exc, _gc_exc.AppError):
            return True
    except Exception:                    # gradio_client absent: strings only
        pass
    msg = str(exc).lower()
    return "quota" in msg or "gpu" in msg


def _is_hf_unreachable_error(exc: Exception, stage: str) -> bool:
    """Space down/unreachable: construction never succeeded, or the transport
    itself failed (vs an app-level predict error)."""
    if stage == "connect":
        return True
    if isinstance(exc, (ConnectionError, TimeoutError, OSError)):
        return True
    try:
        import httpx
        return isinstance(exc, httpx.TransportError)
    except Exception:
        return False


class HuggingFaceProvider:
    """Free text-to-3D via a Gradio ZeroGPU Space; downloads and returns a .glb.

    Codes to one Space's signature. Point HF_SPACE_ID/HF_API_NAME at another Space
    to switch; a differently-shaped Space may need an api_name override.

    Transient failures (cold-start Space rebuilds, queue wakeups) get up to
    `attempts` tries with `backoff` sleeps in between; quota/GPU-exhaustion
    errors fail immediately with an actionable message (retrying cannot help).
    """

    def __init__(self, *, space_id=DEFAULT_HF_SPACE, api_name=DEFAULT_HF_API,
                 token=None, client_factory=None, attempts=3,
                 backoff=(10.0, 30.0), sleep=time.sleep):
        self.space_id = space_id
        self.api_name = api_name
        self.token = token
        self.client_factory = client_factory or _default_hf_client_factory
        self.attempts = attempts
        self.backoff = tuple(backoff)
        self.sleep = sleep

    @staticmethod
    def _candidate_paths(result):
        """Yield path-like strings from a gradio_client result (str/tuple/dict)."""
        if isinstance(result, str):
            yield result
        elif isinstance(result, (list, tuple)):
            for item in result:
                yield from HuggingFaceProvider._candidate_paths(item)
        elif isinstance(result, dict):
            # "value" is NOT optional polish. Measured 2026-08-24 against
            # tencent/Hunyuan3D-2: /shape_generation returns
            #   [{"value": "/.../white_mesh.glb", ...}, "Success", {...}, 1234.0]
            # With only ("path", "name") this function yields exactly
            # ['Success'] -- the status STRING, not the mesh -- so the provider
            # raises "returned no usable glb" while a perfectly good glb sits
            # in the result it was handed. Gradio's own FileData serialises to
            # different keys across component versions; read all three.
            for key in ("path", "name", "value"):
                v = result.get(key)
                if isinstance(v, str):
                    yield v
            # A nested FileData (e.g. {"value": {"path": ...}}) is one more
            # shape the same Space family emits; recurse rather than guess.
            inner = result.get("value")
            if isinstance(inner, (dict, list, tuple)):
                yield from HuggingFaceProvider._candidate_paths(inner)

    def _predict_with_retries(self, prompt: str):
        """One predict() with bounded retries; classified RuntimeError on the
        final failure, always chained (`from e`) to the underlying cause."""
        last_exc: Exception | None = None
        last_stage = "connect"
        for attempt in range(self.attempts):
            if attempt:  # backoff BEFORE each retry (cold Space / queue wakeup)
                self.sleep(self.backoff[min(attempt - 1, len(self.backoff) - 1)])
            stage = "connect"
            try:
                client = self.client_factory(self.space_id, self.token)
                stage = "predict"
                return client.predict(prompt, api_name=self.api_name)
            except Exception as e:
                if _is_hf_quota_error(e):
                    raise RuntimeError(
                        f"HuggingFace Space {self.space_id!r} rejected prompt "
                        f"{prompt!r}: free GPU quota exhausted ({e}). Retrying "
                        f"now is pointless -- wait for the free ZeroGPU quota "
                        f"window to reset, or set HF_TOKEN "
                        f"(https://huggingface.co/settings/tokens) for the "
                        f"larger authenticated quota. MESH_PROVIDER=fake works "
                        f"offline.") from e
                last_exc, last_stage = e, stage
        if _is_hf_gpu_contention_error(last_exc):
            # Deliberately NOT the quota wording: the budget is fine, the
            # shared pool is busy, and "retrying is pointless" would send the
            # operator to wait out a reset window that was never the problem.
            raise RuntimeError(
                f"HuggingFace Space {self.space_id!r}: the shared ZeroGPU pool "
                f"was busy on every one of {self.attempts} attempts "
                f"({last_exc}). This is a QUEUE, not your quota -- run the same "
                f"command again shortly, or raise `attempts`. HF PRO buys "
                f"queue priority.") from last_exc
        if _is_hf_unreachable_error(last_exc, last_stage):
            raise RuntimeError(
                f"HuggingFace Space {self.space_id!r} looks unreachable or "
                f"down after {self.attempts} attempts ({last_exc}). Check "
                f"https://huggingface.co/spaces/{self.space_id} in a browser "
                f"(it may be paused or rebuilding), point HF_SPACE_ID at "
                f"another text-to-3D Space, or set MESH_PROVIDER=fake for "
                f"offline meshes.") from last_exc
        raise RuntimeError(
            f"HuggingFace Space {self.space_id!r} failed for prompt {prompt!r} "
            f"after {self.attempts} attempts: {last_exc}. Retry later, verify "
            f"HF_SPACE_ID/HF_API_NAME point at a compatible Space, or set "
            f"MESH_PROVIDER=fake for offline meshes.") from last_exc

    def generate(self, prompt: str, out_dir: str) -> str:
        result = self._predict_with_retries(prompt)
        cands = list(self._candidate_paths(result))
        src = next((p for p in cands if p.endswith(".glb") and os.path.isfile(p)),
                   None)
        src = src or next((p for p in cands if os.path.isfile(p)), None)
        if not src or os.path.getsize(src) == 0:
            raise RuntimeError(
                f"HuggingFace Space {self.space_id!r} returned no usable glb for "
                f"prompt {prompt!r}: {result!r}")
        os.makedirs(out_dir, exist_ok=True)
        dest = os.path.join(out_dir, "mesh.glb")
        shutil.copyfile(src, dest)
        return dest


#: Two-stage defaults, DRAWN not merely probed (2026-08-24, "an octopus"):
#:
#:   FLUX.1-schnell   -> an unmistakable side-on octopus concept image
#:   Hunyuan3D-2 lift -> ONE connected body, largest_body_volume_frac 1.000
#:
#: against the incumbent Shap-E on the same prompt: 17 disconnected bodies,
#: largest 0.903. Extracted at the SHIPPED default (IDE_KEEP_COMPONENTS=0,
#: v96/p0.3) the Hunyuan mesh gives 7 leaves / 2 pairs where Shap-E gives
#: 4 leaves / 0 pairs and no head.
#:
#: VAST-AI/TripoSG was the first choice and is NOT usable: it answers with a
#: bare `AppError: RuntimeError` carrying no text at all. stabilityai/
#: stable-fast-3d fails the same opaque way. Both were RE-TESTED on 2026-08-24
#: after the bare-filepath bug below was fixed -- the first verdict was unsafe,
#: because a client-side gradio serialization mistake raises AppError too, and
#: `_is_hf_quota_error` was reporting all of it as quota exhaustion. Retested
#: with handle_file() applied correctly, on the same concept image Hunyuan3D-2
#: had just accepted, both still fail. Hunyuan3D-2 is the only lift measured
#: working.
DEFAULT_HF_IMAGE_SPACE = "black-forest-labs/FLUX.1-schnell"
DEFAULT_HF_IMAGE_API = "/infer"
DEFAULT_HF_MESH_SPACE = "tencent/Hunyuan3D-2"
DEFAULT_HF_MESH_API = "/shape_generation"


class _StageInput:
    """Placeholder marking WHERE a stage's primary input goes.

    gradio_client passes arguments POSITIONALLY, and Spaces disagree about the
    slot. FLUX.1-schnell takes the prompt first, so prepending is right there.
    Hunyuan3D-2's /shape_generation is
    `(caption, image, mv_front, mv_back, mv_left, mv_right, steps, ...)` -- the
    image is SECOND, behind a caption that must be sent as None. Prepending
    would put the image path in the caption slot and None in the image slot,
    and the Space would fail with an error that looks like anything but an
    argument-order bug.

    Put STAGE_INPUT anywhere in a stage's kwargs dict and the primary lands in
    exactly that slot. Omit it and the primary is prepended, which is what
    every pre-existing caller relies on.
    """

    __slots__ = ()

    def __repr__(self):                             # pragma: no cover - debug
        return "STAGE_INPUT"


#: Singleton; identity (`is`) is the test, so it can never collide with a real
#: argument value the way a magic string or None would.
STAGE_INPUT = _StageInput()


#: Hunyuan3D-2 /shape_generation, with the image in slot 2 and the seed pinned.
#: `randomize_seed` defaults to True on that Space -- left alone, two "fresh"
#: draws of the same prompt are not comparable, which is the reproducibility
#: bug already recorded against Shap-E in project memory.
HUNYUAN_SHAPE_KWARGS = {
    "caption": None,
    "image": STAGE_INPUT,
    "mv_image_front": None, "mv_image_back": None,
    "mv_image_left": None, "mv_image_right": None,
    "steps": 30, "guidance_scale": 5.0, "seed": 1234,
    "octree_resolution": 256, "check_box_rembg": True,
    "num_chunks": 8000, "randomize_seed": False,
}


#: What stage 1 actually asks FLUX for. The lift reconstructs whatever is in
#: the picture, so the picture has to be one whole animal on nothing.
#:
#: Measured 2026-10-07 on dog/whale/spider/beetle/mouse, seeds pinned and
#: shared across arms, one Hunyuan lift each:
#:
#:   bare word (the old behaviour)       0/5 usable meshes -- head-and-shoulders
#:       portraits and scenes; the sea, the web and a flower were lifted into
#:       the mesh with the animal.
#:   Hunyuan3D-1's own text_to_image suffix ", white background, 3D style,
#:       best quality"                   3/5 -- and "mouse" came back as a
#:       COMPUTER mouse on both seeds.
#:   this template                       5/5, legs and tail separated; 10/10
#:       concept images whole and isolated.
#:
#: FLUX.1-schnell is guidance-distilled and has no negative prompt, so
#: Hunyuan3D-1's negatives ("close-up, cropped, out of frame, missing legs")
#: are said positively here. "animal" is load-bearing: it is what keeps
#: "mouse" an animal.
CONCEPT_PROMPT_TEMPLATE = (
    "A full-body 3D render of a single {subject}, three-quarter side view, "
    "the entire animal in frame with every leg, the tail and all appendages "
    "clearly visible and separated from the body, centered, isolated on a "
    "plain white background, soft even studio lighting, no shadow, no props, "
    "no text")

_LEADING_ARTICLE = re.compile(r"^(?:a|an|the)\s+", re.IGNORECASE)


def concept_prompt(prompt: str, template: str = CONCEPT_PROMPT_TEMPLATE) -> str:
    """`template` around the subject named in `prompt`.

    The leading article goes, or "a dog" becomes "a single a dog". Only a
    whole word: "antelope" keeps its "an".
    """
    subject = _LEADING_ARTICLE.sub("", prompt.strip()).rstrip(" .!")
    return template.format(subject=subject)


#: FLUX.1-schnell /infer, in its positional order. `randomize_seed` defaults to
#: True on that Space, so without this two draws of "dog" differ in breed,
#: crop and background while the lift's seed is already pinned. Seed 11 is the
#: one the template was measured with.
FLUX_IMAGE_KWARGS = {
    "seed": 11, "randomize_seed": False,
    "width": 1024, "height": 1024, "num_inference_steps": 4,
}


#: Spec 2026-10-19 §5, verbatim: every free-tier key lands here (the pricing
#: page lists this model's free tier as "Not available").
GEMINI_NO_QUOTA = (
    "image stage: Gemini {model} has no image quota on this API key. The free "
    "tier's image quota is 0. Enable billing for the key's Google Cloud project "
    "(about $0.042 an image), or set MESH_IMAGE_BACKEND=flux to draw with FLUX "
    "on HuggingFace.")

_CONCEPT_EXTS = (".png", ".jpg", ".jpeg", ".webp")


def _concept_ext(head: bytes) -> str | None:
    """The file extension an image's first bytes call for, or None."""
    if head.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return ".webp"
    return None


class TwoStageProvider:
    """text --(image Space)--> concept image --(image-to-3D Space)--> .glb

    WHY TWO STAGES. `hysts/Shap-E` (2023) is the last native TEXT-to-3D Space
    still running; every current generator -- TRELLIS, Hunyuan3D, TripoSG,
    Stable Fast 3D -- is IMAGE-to-3D, because the field moved to multi-view
    diffusion plus reconstruction. So "a better generator" necessarily means a
    concept image in the middle.

    That is the blueprint, not a detour: CLAUDE.md section 5 Step 1 already
    specifies a "Concept Art Phase (Text-to-Image)". The shipped path skipped
    it and called text-to-3D directly.

    WHAT THIS IS MEANT TO FIX. Measured 2026-08-22: the five fixtures the
    scorecard tracks are hand-modelled low-poly assets (quadruped 576 faces,
    bird 608, insect 2000, humanoid 4672); the three live prompts that produced
    wrong trees are Shap-E output at 9848 / 98956 / 102308 faces, fragmented
    into up to 17 disconnected bodies. Extraction was tuned on the first class
    and only ever fed the second. The image-to-3D Spaces expose explicit
    topology control (`target_face_num` / `simplify` on TripoSG,
    `remesh_option` / `vertex_count` on Stable Fast 3D), so a mesh can be
    REQUESTED in the density band the extractor was calibrated for.

    THE PICTURE DECIDES THE MESH. Measured 2026-10-07: with the bare prompt
    0/5 lifts were usable, with CONCEPT_PROMPT_TEMPLATE 5/5 -- see that
    constant. `prompt_template` is how get_provider("hf2") applies it.
    """

    def __init__(self, *, image_space=DEFAULT_HF_IMAGE_SPACE,
                 image_api=DEFAULT_HF_IMAGE_API,
                 mesh_space=DEFAULT_HF_MESH_SPACE,
                 mesh_api=DEFAULT_HF_MESH_API,
                 token=None, client_factory=None, attempts=3,
                 backoff=(10.0, 30.0), sleep=time.sleep,
                 image_kwargs=None, mesh_kwargs=None,
                 reuse_concept=False, prompt_template=None,
                 subject_description=None, image_model=None, image_seed=None,
                 image_fn=None):
        self.image_space = image_space
        self.image_api = image_api
        self.mesh_space = mesh_space
        self.mesh_api = mesh_api
        self.token = token
        self.client_factory = client_factory or _default_hf_client_factory
        self.attempts = attempts
        self.backoff = tuple(backoff)
        self.sleep = sleep
        # dicts, because gradio_client takes these POSITIONALLY and dict order
        # is insertion order -- the caller controls the Space's signature.
        self.image_kwargs = dict(image_kwargs or {})
        self.mesh_kwargs = dict(mesh_kwargs or {})
        # Opt-in, because a silent stage-1 cache would let a stale concept
        # masquerade as a fresh draw. Worth having: stage 2 is the half that
        # keeps breaking, and every retry of it was costing a second 60-90s
        # GPU call to reproduce a concept image already sitting in out_dir.
        self.reuse_concept = reuse_concept
        # None sends the prompt to stage 1 verbatim; get_provider("hf2") sets
        # CONCEPT_PROMPT_TEMPLATE. The cache key and meta.json keep the RAW
        # prompt either way -- it is what the user asked for.
        self.prompt_template = prompt_template
        # Mesh review (2026-10-11): the VLM's rewrite of the subject, from the
        # user's feedback. It fills the template's {subject} slot in place of the
        # prompt's subject; None draws the plain subject as before.
        self.subject_description = subject_description
        # Spec 2026-10-19: a Gemini model id draws stage 1 instead of the image
        # Space. Its seed is accepted but does not reproduce, so it is a draw
        # LABEL (cache key), never a recipe. image_fn is injectable for tests.
        self.image_model = image_model
        self.image_seed = image_seed
        self.image_fn = image_fn

    @property
    def cache_settings(self) -> dict:
        """Everything that decides WHICH mesh comes back, for the cache key.

        Transport knobs (token, attempts, backoff, reuse_concept) are left out:
        they change how a mesh is fetched, not which one, and keying on them
        would turn a retry tweak into a full re-draw.
        """
        def plain(kwargs):
            return {k: ("<stage input>" if v is STAGE_INPUT else v)
                    for k, v in kwargs.items()}
        if self.image_model is not None:
            # A different SHAPE from the FLUX dict (no image_space, an
            # image_backend), so a FLUX key and a Gemini key can never collide,
            # and every existing FLUX key stays byte-identical.
            s = {"image_backend": "gemini", "image_model": self.image_model,
                 "image_seed": self.image_seed,
                 "prompt_template": self.prompt_template,
                 "mesh_space": self.mesh_space, "mesh_api": self.mesh_api,
                 "mesh_kwargs": plain(self.mesh_kwargs)}
            if self.subject_description is not None:
                s["subject_description"] = self.subject_description
            return s
        s = {"image_space": self.image_space, "image_api": self.image_api,
             "image_kwargs": plain(self.image_kwargs),
             "prompt_template": self.prompt_template,
             "mesh_space": self.mesh_space, "mesh_api": self.mesh_api,
             "mesh_kwargs": plain(self.mesh_kwargs)}
        if self.subject_description is not None:     # absent by default: keys unchanged
            s["subject_description"] = self.subject_description
        return s

    @staticmethod
    def _as_file_arg(path):
        """gradio `filepath` inputs travel as FileData, NOT as a bare string.

        Measured 2026-08-24: passing the path straight through makes
        gradio_client raise, CLIENT-SIDE and before any request is sent,

            gradio.data_classes.FileData() argument after ** must be a
            mapping, not str

        ...as a `gradio_client.exceptions.AppError`. That last detail is why
        this bug was expensive: every AppError was being read as GPU quota
        exhaustion, so a serialization mistake in OUR code was reported as the
        account being out of budget, on a Space that was working fine.
        """
        from gradio_client import handle_file
        return handle_file(path)

    def _call(self, space_id, api_name, primary, extra, stage,
              primary_is_file=False):
        """One stage, with bounded retries and STAGE-NAMED errors.

        `stage` is in every message on purpose: two GPU Spaces means two quota
        walls and two ways to be unreachable, and "quota exhausted" without a
        stage leaves the operator unable to tell which half is down.
        """
        # Explicit flag, not `os.path.isfile(primary)`: stage 1's primary is a
        # PROMPT and stage 2's is a PATH, and which is which is a property of
        # the stage, not something to sniff from the value at runtime.
        if primary_is_file:
            primary = self._as_file_arg(primary)
        values = list(extra.values())
        if any(v is STAGE_INPUT for v in values):
            args = tuple(primary if v is STAGE_INPUT else v for v in values)
        else:
            args = (primary,) + tuple(values)
        last_exc, last_stage = None, "connect"
        for attempt in range(self.attempts):
            if attempt:
                self.sleep(self.backoff[min(attempt - 1, len(self.backoff) - 1)])
            where = "connect"
            try:
                client = self.client_factory(space_id, self.token)
                where = "predict"
                return client.predict(*args, api_name=api_name)
            except Exception as e:
                if _is_hf_quota_exhaustion_error(e):
                    raise RuntimeError(
                        f"{stage} stage: Space {space_id!r} rejected the "
                        f"request -- free GPU quota exhausted ({e}). Retrying "
                        f"now is pointless; wait for the ZeroGPU window to "
                        f"reset, set HF_TOKEN for the authenticated quota, or "
                        f"use MESH_PROVIDER=fake offline.") from e
                if _is_hf_quota_error(e):
                    # App-level rejection with NO quota evidence. Still not
                    # retried -- a Space that raised will raise again -- but it
                    # must not claim a cause it cannot see. Measured
                    # 2026-08-24: this branch was saying "quota exhausted" for
                    # a CLIENT-SIDE serialization bug of ours, on a Space with
                    # quota to spare, and that false attribution is what
                    # stopped a twelve-arm matrix and got a working Space
                    # written off as dead.
                    raise RuntimeError(
                        f"{stage} stage: Space {space_id!r} rejected the "
                        f"request with an app-level error ({e}). This is NOT "
                        f"a quota reading -- the Space (or gradio_client) "
                        f"raised, and said nothing about your budget. Check "
                        f"the argument layout against "
                        f"Client({space_id!r}).view_api() before assuming the "
                        f"Space is down.") from e
                last_exc, last_stage = e, where
        if _is_hf_gpu_contention_error(last_exc):
            raise RuntimeError(
                f"{stage} stage: Space {space_id!r}: the shared ZeroGPU pool "
                f"was busy on every one of {self.attempts} attempts "
                f"({last_exc}). This is a QUEUE, not your quota -- retry "
                f"shortly.") from last_exc
        if _is_hf_unreachable_error(last_exc, last_stage):
            raise RuntimeError(
                f"{stage} stage: Space {space_id!r} looks unreachable or down "
                f"after {self.attempts} attempts ({last_exc}). Check "
                f"https://huggingface.co/spaces/{space_id} in a browser, or "
                f"point HF_{stage.upper()}_SPACE_ID at another Space."
            ) from last_exc
        raise RuntimeError(
            f"{stage} stage: Space {space_id!r} failed after "
            f"{self.attempts} attempts: {last_exc}.") from last_exc

    @staticmethod
    def _first_existing(result, suffixes=()):
        cands = list(HuggingFaceProvider._candidate_paths(result))
        for suffix in suffixes:
            hit = next((p for p in cands
                        if p.endswith(suffix) and os.path.isfile(p)), None)
            if hit:
                return hit
        return next((p for p in cands if os.path.isfile(p)), None)

    def generate(self, prompt: str, out_dir: str, progress=None) -> str:
        os.makedirs(out_dir, exist_ok=True)

        # ---- stage 0: an already-drawn concept, if we are allowed to ---------
        existing = None
        if self.reuse_concept:
            for ext in (".png", ".jpg", ".jpeg", ".webp"):
                cand = os.path.join(out_dir, "concept" + ext)
                if os.path.isfile(cand) and os.path.getsize(cand) > 0:
                    existing = cand
                    break
        if existing:
            # Straight to stage 2. `concept` is already on disk and is the same
            # file, so the failure-evidence guarantee below is unaffected.
            if progress:
                progress("image", existing)
            mesh_result = self._call(self.mesh_space, self.mesh_api, existing,
                                     self.mesh_kwargs, "mesh",
                                     primary_is_file=True)
            return self._save_mesh(mesh_result, prompt, out_dir)

        # ---- stage 1: prompt -> concept image -------------------------------
        subject = self.subject_description or prompt
        image_prompt = (concept_prompt(subject, self.prompt_template)
                        if self.prompt_template else subject)
        if self.image_model is not None:
            concept = self._draw_gemini(image_prompt, out_dir)
            if progress:
                progress("image", concept)
            mesh_result = self._call(self.mesh_space, self.mesh_api, concept,
                                     self.mesh_kwargs, "mesh",
                                     primary_is_file=True)
            return self._save_mesh(mesh_result, prompt, out_dir)
        img_result = self._call(self.image_space, self.image_api, image_prompt,
                                self.image_kwargs, "image")
        img_src = self._first_existing(img_result, (".png", ".jpg", ".webp"))
        if not img_src or os.path.getsize(img_src) == 0:
            # Refuse BEFORE stage 2. Lifting a 0-byte concept turns a quiet
            # stage-1 failure into a mysterious mesh failure one stage later --
            # the exact attribution loss this class is built to avoid.
            raise RuntimeError(
                f"image stage: Space {self.image_space!r} returned no usable "
                f"image for prompt {prompt!r}: {img_result!r}")

        concept = os.path.join(out_dir, "concept" + os.path.splitext(img_src)[1])
        shutil.copyfile(img_src, concept)
        if progress:
            progress("image", concept)

        # ---- stage 2: concept image -> mesh ---------------------------------
        # The concept is written FIRST and never cleaned up on failure: when
        # stage 2 dies it is the only evidence of how far the run got, and of
        # whether the fault is the picture or the lift.
        mesh_result = self._call(self.mesh_space, self.mesh_api, img_src,
                                 self.mesh_kwargs, "mesh",
                                 primary_is_file=True)
        return self._save_mesh(mesh_result, prompt, out_dir)

    def _draw_gemini(self, prompt: str, out_dir: str) -> str:
        """Stage 1 on Gemini: the concept, as `concept<ext>` named by its bytes.

        Retries only what Google calls transient; a key with no image quota
        fails at once (its 429 still carries a RetryInfo delay that waiting
        never honours -- spec §5)."""
        import gemini_image
        draw = self.image_fn or gemini_image.generate_image
        part = os.path.join(out_dir, ".concept.part")
        last = None
        for attempt in range(self.attempts):
            if attempt:
                self.sleep(self.backoff[min(attempt - 1, len(self.backoff) - 1)])
            try:
                draw(prompt, part, model=self.image_model, seed=self.image_seed)
                break
            except gemini_image.GeminiImageError as e:
                if gemini_image.no_image_quota(e):
                    # Gemini's own words ride along: a 400 FAILED_PRECONDITION
                    # is also how an unsupported region answers, and billing
                    # will not fix that (final review, finding 1).
                    raise RuntimeError(GEMINI_NO_QUOTA.format(model=self.image_model)
                                       + f" ({e})") from e
                if not gemini_image.is_transient(e):
                    raise RuntimeError(f"image stage: {e}") from e
                last = e
        else:
            raise RuntimeError(
                f"image stage: Gemini {self.image_model} failed after "
                f"{self.attempts} attempts: {last}") from last
        with open(part, "rb") as f:
            ext = _concept_ext(f.read(12))
        if ext is None:
            os.unlink(part)
            raise RuntimeError(
                f"image stage: Gemini {self.image_model} returned bytes that are "
                f"not JPEG, PNG or WEBP")
        # One concept per folder: an older draw's concept.png must not sit
        # beside this concept.jpg, or readers would pick whichever they test first.
        for old in _CONCEPT_EXTS:
            stale = os.path.join(out_dir, "concept" + old)
            if os.path.exists(stale):
                os.unlink(stale)
        concept = os.path.join(out_dir, "concept" + ext)
        os.replace(part, concept)
        return concept

    def _save_mesh(self, mesh_result, prompt, out_dir):
        mesh_src = self._first_existing(mesh_result, (".glb", ".obj"))
        if not mesh_src or os.path.getsize(mesh_src) == 0:
            raise RuntimeError(
                f"mesh stage: Space {self.mesh_space!r} returned no usable glb "
                f"for prompt {prompt!r}: {mesh_result!r}")

        dest = os.path.join(out_dir, "mesh.glb")
        shutil.copyfile(mesh_src, dest)
        return dest


_IMAGE_BACKENDS = ("auto", "gemini", "flux")


def hf2_image_backend() -> str:
    """"gemini" or "flux": what draws hf2's concept image (spec 2026-10-19 §1).

    MESH_IMAGE_BACKEND is auto (or unset/empty), gemini or flux, read stripped
    and case-folded. auto means Gemini when GEMINI_API_KEY is non-empty, FLUX
    otherwise -- so CI and offline machines keep today's behaviour. flux exists
    because the same key also serves LLM_PROVIDER=gemini, and a free-tier key
    has no image quota."""
    raw = os.environ.get("MESH_IMAGE_BACKEND", "")
    backend = raw.strip().casefold() or "auto"
    if backend not in _IMAGE_BACKENDS:
        raise ValueError(f"unknown MESH_IMAGE_BACKEND {raw!r}; valid: "
                         + ", ".join(_IMAGE_BACKENDS))
    has_key = bool(os.environ.get("GEMINI_API_KEY", "").strip())
    if backend == "auto":
        return "gemini" if has_key else "flux"
    if backend == "gemini" and not has_key:
        raise ValueError("MESH_IMAGE_BACKEND=gemini requires an API key; set "
                         "GEMINI_API_KEY (paid tier: the free tier's image quota is 0)")
    return backend


def _gemini_image_model() -> str:
    import gemini_image
    return os.environ.get("GEMINI_IMAGE_MODEL", "").strip() or gemini_image.DEFAULT_MODEL


def draws_reproduce(name: str | None = None) -> bool:
    """False when a fresh request of the same draw would give a different mesh:
    only hf2 on Gemini, whose seed is accepted but does not reproduce. The app
    then gives every round its own draw label. Never raises; a misconfigured
    backend surfaces from get_provider."""
    if (name or os.environ.get("MESH_PROVIDER", "fake")) != "hf2":
        return True
    try:
        return hf2_image_backend() != "gemini"
    except ValueError:
        return True


def image_model_label(name: str | None = None, key_dir: str | None = None) -> str | None:
    """What drew a concept image, for display: with `key_dir`, what that cache
    folder's meta.json settings record (image_model, else image_space, else
    None); without it, what hf2 would draw with now. Never raises."""
    if key_dir is not None:
        settings = (read_mesh_meta(key_dir) or {}).get("settings")
        if not isinstance(settings, dict):
            return None
        return settings.get("image_model") or settings.get("image_space") or None
    if (name or os.environ.get("MESH_PROVIDER", "fake")) != "hf2":
        return None
    try:
        backend = hf2_image_backend()
    except ValueError:
        return None
    if backend == "gemini":
        return _gemini_image_model()
    return os.environ.get("HF_IMAGE_SPACE_ID", DEFAULT_HF_IMAGE_SPACE)


def get_provider(name: str | None = None, *, description: str | None = None,
                 seed: int | None = None) -> MeshProvider:
    """Resolve a MeshProvider by name (or env MESH_PROVIDER, default 'fake').

    'fake' is the offline, no-spend default everywhere; a networked provider
    is opt-in via MESH_PROVIDER=meshy/hf/hf2.

    `description` and `seed` (hf2 only; fake and the others ignore them) make a
    fresh draw of the same subject: see TwoStageProvider.subject_description.
    With neither, the provider and its cache key are exactly the default ones.

    hf2's image stage is Nano Banana 2.1 when GEMINI_API_KEY is set, else
    FLUX.1-schnell (hf2_image_backend). On Gemini the seed only labels the draw
    -- Hunyuan keeps HUNYUAN_SHAPE_KWARGS' seed 1234, the setup the concept-image
    experiment measured 33/34 with -- and reuse_concept is on, so a lift retry
    lifts the picture already paid for (spec 2026-10-19 §4)."""
    name = name or os.environ.get("MESH_PROVIDER", "fake")
    if name == "fake":
        return FakeMeshProvider()
    if name == "meshy":
        key = os.environ.get("MESHY_API_KEY", "")
        if not key:
            raise ValueError(
                "provider 'meshy' requires an API key; set MESHY_API_KEY")
        return MeshyProvider(api_key=key)
    if name == "hf2" and hf2_image_backend() == "gemini":
        mesh_space = os.environ.get("HF_MESH_SPACE_ID", DEFAULT_HF_MESH_SPACE)
        return TwoStageProvider(
            mesh_space=mesh_space,
            mesh_api=os.environ.get("HF_MESH_API", DEFAULT_HF_MESH_API),
            token=os.environ.get("HF_TOKEN") or None,
            prompt_template=CONCEPT_PROMPT_TEMPLATE,
            mesh_kwargs=(dict(HUNYUAN_SHAPE_KWARGS)
                         if mesh_space == DEFAULT_HF_MESH_SPACE else None),
            subject_description=description,
            image_model=_gemini_image_model(), image_seed=seed,
            reuse_concept=True,
        )
    if name == "hf2":
        # Same rule as mesh_kwargs below: FLUX's slots, FLUX's Space only.
        image_kwargs = (dict(FLUX_IMAGE_KWARGS)
                        if os.environ.get("HF_IMAGE_SPACE_ID",
                                          DEFAULT_HF_IMAGE_SPACE)
                        == DEFAULT_HF_IMAGE_SPACE else None)
        # Only when the mesh stage IS the default Space: an operator who
        # redirects HF_MESH_SPACE_ID gets a bare prepended image, because
        # this argument layout is Hunyuan's signature and nobody else's.
        mesh_kwargs = (dict(HUNYUAN_SHAPE_KWARGS)
                       if os.environ.get("HF_MESH_SPACE_ID",
                                         DEFAULT_HF_MESH_SPACE)
                       == DEFAULT_HF_MESH_SPACE else None)
        if seed is not None:          # a fresh draw: both stages take this seed, still pinned
            for kw in (image_kwargs, mesh_kwargs):
                if kw is not None:
                    kw["seed"] = seed
        return TwoStageProvider(
            image_space=os.environ.get("HF_IMAGE_SPACE_ID",
                                       DEFAULT_HF_IMAGE_SPACE),
            image_api=os.environ.get("HF_IMAGE_API", DEFAULT_HF_IMAGE_API),
            mesh_space=os.environ.get("HF_MESH_SPACE_ID",
                                      DEFAULT_HF_MESH_SPACE),
            mesh_api=os.environ.get("HF_MESH_API", DEFAULT_HF_MESH_API),
            token=os.environ.get("HF_TOKEN") or None,
            prompt_template=CONCEPT_PROMPT_TEMPLATE,
            image_kwargs=image_kwargs, mesh_kwargs=mesh_kwargs,
            subject_description=description,
        )
    if name == "hf":
        return HuggingFaceProvider(
            space_id=os.environ.get("HF_SPACE_ID", DEFAULT_HF_SPACE),
            api_name=os.environ.get("HF_API_NAME", DEFAULT_HF_API),
            token=os.environ.get("HF_TOKEN") or None,
        )
    raise ValueError(
        f"unknown MESH_PROVIDER {name!r}; valid: fake, meshy, hf, hf2")


def output_dir() -> str:
    return os.environ.get("MESH_OUTPUT_DIR", os.path.join(_HERE, "generated_meshes"))


_SLUG_MAX = 40


def cache_key(provider_name: str, prompt: str,
              settings: dict | None = None) -> str:
    """The cache directory name for one request.

    Without `settings`: sha256("provider:prompt"), the legacy key every
    existing entry and KNOWN_CACHE_PROMPTS is filed under.

    With `settings` (a provider's `cache_settings`): "<slug>-<digest>", the
    digest covering provider, prompt AND settings. The legacy key named the
    prompt only, so after hf2's concept template or seed changed, a cached
    "a dog" kept being served and the new template never ran. The slug is for
    a human reading the directory listing; the digest is what identifies.
    """
    if settings is None:
        return hashlib.sha256(f"{provider_name}:{prompt}".encode()).hexdigest()
    blob = json.dumps([provider_name, prompt, settings], sort_keys=True,
                      separators=(",", ":"))
    slug = re.sub(r"[^a-z0-9]+", "-", prompt.lower()).strip("-")
    slug = slug[:_SLUG_MAX].rstrip("-") or "mesh"
    return f"{slug}-{hashlib.sha256(blob.encode()).hexdigest()[:16]}"


# ---------------------------------------------------------------------------
# Provenance sidecar (F3)
#
# The cache used to be completely unattributable: generated_meshes/<sha>/ held
# mesh.glb and nothing else -- no prompt, no provider, no parameters, no
# timestamp, no checksum. Working out which cached mesh answered which live
# prompt meant brute-forcing sha256 over a dictionary of candidate prompt
# strings. `meta.json` beside the .glb ends that.
#
# Prior art (CLAUDE.md 0), adapted:
#   * in-toto Attestation Statement v1 / SLSA Build Provenance (v1.2 current) --
#     a provenance predicate is bound to a `subject` carrying the artifact's
#     digest, and subjects are "matched purely by digest". Hence: the digest is
#     what makes the record checkable, and it is recorded in lowercase hex.
#   * Nix binary-cache `.narinfo` -- an INPUT-addressed store path plus a
#     separate CONTENT hash (NarHash) and size (NarSize) of the bytes. Exactly
#     our split: the directory name is sha256(provider:prompt) (input), while
#     glb_sha256/glb_bytes describe the bytes (content). Both are checked,
#     because they fail differently.
#   * PEP 376 / wheel RECORD -- the (path, hash, size) triple; sha256 or better,
#     md5/sha1 not permitted. Our (glb, glb_sha256, glb_bytes) is that triple.
#   * DVC `.dvc` / git-annex -- a per-file text sidecar is the mainstream design
#     for large binaries; git-annex even embeds the byte size beside the hash.
#     Tools rejected (new dependency; `pip install` is forbidden here), and
#     DVC's md5 rejected outright in favour of sha256.
#   * W3C PROV-DM (Rec. 2013) entity/activity/agent -- the record names all
#     three: AGENT `provider` (+ `space_id`/`api_name`), ACTIVITY `prompt` +
#     `generated_utc`, ENTITY `glb` + `glb_sha256` + `glb_bytes`.
#   * C2PA 2.4 AI/ML guidance -- prompt as an `inputTo` ingredient, the model as
#     an ingredient, and a data-hash assertion as the hard binding to the asset:
#     independent confirmation that prompt + generator + byte hash belong in ONE
#     record. Format rejected: C2PA manifests are JUMBF/CBOR with COSE signing
#     and `c2pa-python` is a Rust-backed wheel -- not reachable from stdlib.
#
# Rejected: a single index (sqlite/manifest) at the cache root. These key
# directories get COPIED between checkouts and worktrees, which is the regime
# where a central index fails -- a live sqlite file is explicitly unsafe to
# copy without its journal (sqlite.org/howtocorrupt.html), consolidated
# metadata goes stale the moment entries appear out of band (zarr's
# `.zmetadata`), and Nix's own narinfo sqlite cache goes stale against the real
# narinfo. The per-directory convention (cf. CACHEDIR.TAG) keeps a directory
# self-describing when it moves. A sidecar travels with the bytes; an index
# does not. If an index is ever added it must be derived and rebuildable from
# the sidecars, never authoritative.
#
# Rejected as an overclaim: "Datasheets for Datasets" (Gebru et al., CACM 2021)
# and "Model Cards" (Mitchell et al., FAT* 2019). Both are corpus/model-level
# documentation genres with no digest, no artifact binding and no verifier;
# they would describe the HF Space, not this record.
#
# Two invariants make the record checkable rather than decorative:
#   1. the recorded sha256 + byte size must match mesh.glb on disk; and
#   2. cache_key(provider, prompt) must reproduce the directory name.
# (2) is what makes an attribution PROVABLE instead of a claim -- it is the
# same check the brute-force recovery ran, frozen into the record. Both are
# enforced by verify_mesh_meta(), which is required to score a swapped or
# corrupted mesh as MISMATCH (COORDINATION.md 4.1).
#
# Unknown fields stay null. Never fill an unknown with today's default: a
# provenance field that reads plausible but was invented is worse than absent.
# ---------------------------------------------------------------------------

META_FILENAME = "meta.json"
META_VERSION = 1

# (provider_name, prompt) pairs for the meshes that already existed when the
# sidecar shipped, recovered 2026-08-20 by brute-forcing sha256 over candidate
# prompt strings -- the state of the art in this repo before this change. Each
# pair is verified against the directory it claims (cache_key must reproduce
# the name), so a wrong entry can only fail to match; it can never mis-attribute
# a mesh. tests/test_mesh_acquire.py pins the 20 digests these produce.
#
# DO NOT re-run the brute force to extend this table. It was re-run 2026-08-21
# over 72,534 prompt strings harvested from this repo x 9 provider names
# (652,806 candidates) against the 10 keys still unattributed in the local
# cache: ZERO matches. Those 10 are all `fake` draws whose mesh.glb is
# byte-identical to a committed fixture (8x quadruped.glb, 1x bird.glb,
# 1x insect.glb), so their mesh identity is known even though their prompts are
# not, and every REAL provider draw in the cache is attributed. Recovery does
# not scale -- that is the whole reason this sidecar exists.
KNOWN_CACHE_PROMPTS = (
    ("hf", "an octopus"),
    ("hf", "a water bear"),
    ("hf", "a lizard with a long tail"),
    ("hf", "a dog"),
    ("hf", "dog"),
    ("hf", "a deer"),
    ("fake", "a dog"),
    ("fake", "dog"),
    ("fake", "a horse"),
    ("fake", "horse"),
    ("fake", "bear"),
    ("fake", "a water bear"),
    ("fake", "a quadruped"),
    ("fake", "a red fox"),
    ("fake", "a beetle"),
    ("fake", "beetle"),
    ("fake", "a giant beetle"),
    ("fake", "a bird"),
    ("fake", "a fish"),
    ("fake", "a person"),
)


def _utc(ts: float | None = None) -> str:
    when = (datetime.datetime.fromtimestamp(ts, datetime.timezone.utc)
            if ts is not None
            else datetime.datetime.now(datetime.timezone.utc))
    return when.strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: str, _chunk: int = 1 << 20) -> str:
    """sha256 of a file's bytes (streamed; a .glb can be a few MB)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(_chunk), b""):
            h.update(block)
    return h.hexdigest()


def meta_path(key_dir: str) -> str:
    return os.path.join(key_dir, META_FILENAME)


def has_mesh_meta(key_dir: str) -> bool:
    """Whether a sidecar FILE exists, parseable or not.

    Deliberately distinct from `read_mesh_meta(...) is not None`: a corrupted
    sidecar is still a sidecar. The CACHE-HIT path and `backfill_mesh_cache`
    key their never-overwrite rule on this, so a malformed record is preserved
    for the audit instead of being silently replaced by a thinner one.

    The GENERATE path deliberately does NOT consult it: it has just produced
    new bytes, so any existing record describes a mesh that no longer exists
    and must be replaced, not preserved.
    """
    return os.path.exists(meta_path(key_dir))


def read_mesh_meta(key_dir: str) -> dict | None:
    """Parse the sidecar in `key_dir`, or None when absent/unreadable."""
    try:
        with open(meta_path(key_dir)) as f:
            meta = json.load(f)
    except (OSError, ValueError):
        return None
    return meta if isinstance(meta, dict) else None


def write_mesh_meta(key_dir: str, *, provider: str, prompt: str,
                    provenance: str, space_id: str | None = None,
                    api_name: str | None = None,
                    generated_utc: str | None = None,
                    glb: str = "mesh.glb",
                    settings: dict | None = None) -> dict:
    """Write `key_dir/meta.json` describing the .glb beside it; return the record.

    `provenance` says how the prompt was learned, and therefore how much of the
    rest to trust:
      generated - this process called the provider; the endpoint is recorded.
      cache_hit - served from cache, so the prompt is exact but the endpoint
                  that produced the bytes is NOT knowable (today's HF_SPACE_ID
                  is not necessarily the one that ran) -> null.
      backfill  - recovered from KNOWN_CACHE_PROMPTS and proven by hash; the
                  endpoint and the generation time are unrecoverable -> null.

    `glb_mtime_utc` is the filesystem mtime AT RECORD TIME. It is the best
    available proxy for when a backfilled mesh was produced, but it is not
    preserved by a plain `cp`, so treat it as weak evidence -- `glb_sha256` is
    the field that binds this record to those bytes.

    Written atomically (temp file + os.replace) inside `key_dir`, so a reader --
    or one of several checkouts sharing a cache -- never sees a partial record.
    """
    glb_path = resolve_cached_glb(key_dir, glb)
    meta = {
        "meta_version": META_VERSION,
        "provenance": provenance,
        "provider": provider,
        "prompt": prompt,
        "cache_key": cache_key(provider, prompt, settings),
        "space_id": space_id,
        "api_name": api_name,
        "glb": glb,
        "glb_sha256": sha256_file(glb_path),
        "glb_bytes": os.path.getsize(glb_path),
        "glb_mtime_utc": _utc(os.path.getmtime(glb_path)),
        "generated_utc": generated_utc,
        "recorded_utc": _utc(),
    }
    if settings is not None:
        # Only when keyed on them: a legacy record keeps its old shape.
        meta["settings"] = settings
    dest = meta_path(key_dir)
    # mkstemp, not a pid-keyed name: a threaded caller (the archived MCP
    # server dispatched tools on a threadpool) gives two threads acquiring the
    # same prompt one pid, and they would truncate each other's partial record
    # before os.replace publishes it. The temp file is created inside key_dir so the replace is atomic
    # (same filesystem) and nothing is ever written outside the cache.
    fd, tmp = tempfile.mkstemp(dir=key_dir, prefix=f".{META_FILENAME}.",
                               suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(meta, f, indent=2, sort_keys=True)
            f.write("\n")
        os.replace(tmp, dest)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise
    return meta


def _meta_glb_name(meta: dict) -> str | None:
    """The artifact name a sidecar declares, or None if it is not a plain
    basename. Everything in a sidecar is untrusted input: `glb` is joined onto
    key_dir, so an absolute or traversing value would make the verifier read --
    and vouch for -- a file outside the cache entirely."""
    name = meta.get("glb")
    if not isinstance(name, str) or not name or name in (os.curdir, os.pardir):
        return None
    if os.path.isabs(name) or os.path.basename(name) != name:
        return None
    return name


# Reasons that mean THE BYTES CHANGED rather than the record was damaged.
# `--repair` must never rewrite a record failing any of these: that record is
# not broken, it is intact provenance correctly reporting a swapped or
# corrupted mesh, and rewriting it would launder the swap into a green audit.
BYTE_REASONS = frozenset({"glb", "glb_bytes", "glb_sha256"})


def resolve_cached_glb(key_dir: str, name: str) -> str:
    """Absolute path of `name` inside `key_dir`, refusing to leave the entry.

    The name is validated as a plain basename elsewhere, but every read of it
    (isfile/getsize/sha256_file) FOLLOWS symlinks -- so a `mesh.glb` that is
    itself a link out of the cache would otherwise be hashed and positively
    attributed, which is exactly what the name check exists to prevent.
    """
    glb_path = os.path.join(key_dir, name)
    root = os.path.realpath(key_dir)
    resolved = os.path.realpath(glb_path)
    if os.path.dirname(resolved) != root:
        raise ValueError(
            f"{name!r} in {key_dir!r} resolves outside the cache entry "
            f"({resolved!r}); refusing to vouch for it")
    return glb_path


def verify_mesh_meta(key_dir: str) -> dict:
    """Check a key directory's sidecar against the bytes it claims to describe.

    Returns {"key", "status", "reasons", "meta"} where status is one of:
      NO_MESH  - no sidecar and no mesh.glb (nothing to attribute)
      NO_META  - mesh.glb present, no sidecar
      MISMATCH - the sidecar disagrees with the bytes on disk, with the
                 directory name, or names bytes that are not there. REQUIRED
                 for a swapped, corrupted or unprovable mesh; a record that
                 cannot detect one is decoration, not provenance.
      OK       - artifact name, digest, size and cache_key all reproduce.
    `reasons` names the fields that disagreed. This always returns a status --
    a malformed sidecar is a finding, never an exception.
    """
    key = os.path.basename(os.path.normpath(key_dir))
    meta = read_mesh_meta(key_dir)
    if meta is None:
        if has_mesh_meta(key_dir):
            # Present but unparseable: corruption, not absence. Calling that
            # NO_META reads as "never recorded" and hides the damage behind a
            # status the audit is entitled to ignore.
            return {"key": key, "status": "MISMATCH", "reasons": ["meta"],
                    "meta": None}
        glb_path = os.path.join(key_dir, "mesh.glb")
        has_glb = os.path.isfile(glb_path) and os.path.getsize(glb_path) > 0
        return {"key": key, "status": "NO_META" if has_glb else "NO_MESH",
                "reasons": [], "meta": None}

    reasons = []
    name = _meta_glb_name(meta)
    if name is None:
        reasons.append("glb")
        glb_path = None
    else:
        try:
            glb_path = resolve_cached_glb(key_dir, name)
        except ValueError:
            glb_path = None
            reasons.append("glb")
        if glb_path is not None and (
                not os.path.isfile(glb_path)
                or os.path.getsize(glb_path) == 0):
            # A record describing bytes that are not there is a stale record,
            # not "nothing to attribute" -- scoring it NO_MESH would let the
            # audit under-report a deleted or renamed mesh.
            reasons.append("glb")
            glb_path = None

    provider, prompt = meta.get("provider"), meta.get("prompt")
    settings = meta.get("settings")
    if (not isinstance(provider, str) or not isinstance(prompt, str)
            or not (settings is None or isinstance(settings, dict))):
        reasons.append("cache_key")
    else:
        derived = cache_key(provider, prompt, settings)
        # Both bindings, because they fail differently: `key` catches a record
        # filed in the wrong directory, `cache_key` catches a record whose own
        # stored digest was edited to match a swapped prompt.
        if derived != key or derived != meta.get("cache_key"):
            reasons.append("cache_key")

    if glb_path is not None:
        # Size is checked first (Nix/git-annex/OCI all carry it beside the
        # hash) but deliberately does NOT short-circuit the digest: a .glb is a
        # few MB, and naming both failed fields tells a corrupted mesh from a
        # swapped one.
        if meta.get("glb_bytes") != os.path.getsize(glb_path):
            reasons.append("glb_bytes")
        if meta.get("glb_sha256") != sha256_file(glb_path):
            reasons.append("glb_sha256")
    else:
        reasons += ["glb_bytes", "glb_sha256"]

    status = "MISMATCH" if reasons else "OK"
    return {"key": key, "status": status, "reasons": reasons, "meta": meta}


def is_same_key_alias(key_dir: str) -> bool:
    """Whether a SYMLINKED key directory points at a directory carrying the
    same cache key -- i.e. an alias for this entry rather than a redirect.

    THIS REPO RUNS IN THAT REGIME ALMOST EXCLUSIVELY. An agent worktree's
    generated_meshes/<key> is a symlink to <key> in a sibling checkout (that is
    how the live meshes are reachable from a worktree at all), so a blanket
    "never write through a symlink" rule would disable provenance in the only
    environment where the work actually happens -- silently, which is worse
    than refusing loudly.

    Same basename is exactly the right test, and it is not cosmetic: a record
    is bound to its directory's NAME (verify_mesh_meta recomputes
    cache_key(provider, prompt) against it). When link and target share the
    key, the sidecar verifies OK read from EITHER path. When they do not, a
    record written through the link would read MISMATCH from the target's own
    path -- so we decline, rather than plant a record that contradicts itself
    depending on how it is reached.
    """
    key_dir = os.path.normpath(key_dir)
    if not os.path.islink(key_dir):
        return False
    target = os.path.realpath(key_dir)
    # A DANGLING link also "resolves" to a same-named path, so the directory
    # check is load-bearing: sibling worktrees get auto-cleaned, and an alias
    # into a deleted one is a broken entry, not an alias for anything.
    if not os.path.isdir(target):
        return False
    return os.path.basename(target) == os.path.basename(key_dir)


def provenance_enabled() -> bool:
    """IDE_MESH_PROVENANCE=0 turns sidecar writing off entirely.

    Default ON -- recording provenance IS this module's job, and a flag that
    defaults to not doing it would reproduce the unattributable cache. The
    switch exists because a serve legitimately writes into cache directories
    that may be aliases into another checkout (see `is_same_key_alias`), and
    anyone who does not want that needs a way to say so. Read per call.
    """
    return os.environ.get("IDE_MESH_PROVENANCE", "").strip() != "0"


def may_write_provenance(key_dir: str) -> bool:
    """Whether a sidecar may be written for `key_dir`: a real directory, or a
    symlink that is a same-key alias for one."""
    return not os.path.islink(os.path.normpath(key_dir)) or \
        is_same_key_alias(key_dir)


def _write_mesh_meta_best_effort(key_dir, *, respect_alias_rule: bool,
                                 **kwargs) -> dict | None:
    """Record provenance without ever failing an acquisition over it.

    Provenance is a record, not a gate: a read-only cache, a full disk or a
    race with another process must not turn a served mesh into an error.

    `respect_alias_rule` applies `may_write_provenance` -- set on the CACHE-HIT
    path, where a renaming symlink is a redirect we would otherwise plant a
    self-contradicting record behind. It is deliberately NOT set on the
    generate path: there, provider.generate has already written a multi-MB
    mesh.glb through that same symlink, and declining the record would leave
    foreign bytes with no statement of what they are -- the worst of both.
    Guard the write we can avoid; attribute the one we cannot.
    """
    if not provenance_enabled():
        return None
    if respect_alias_rule and not may_write_provenance(key_dir):
        return None
    try:
        return write_mesh_meta(key_dir, **kwargs)
    except OSError:
        return None


def backfill_mesh_cache(cache_dir: str | None = None, *,
                        follow_symlinks: bool = False,
                        aliases: bool = True, write: bool = True,
                        repair: bool = False) -> list[dict]:
    """One-shot: attribute the meshes that already exist, and audit the rest.

    Walks every key directory in `cache_dir`, matches its name against
    cache_key(provider, prompt) over KNOWN_CACHE_PROMPTS, and writes a sidecar
    for the ones it can prove. Never guesses: a key the table cannot reproduce
    is reported `unattributed` and gets NO sidecar, so "meta.json present"
    keeps meaning "attributed" -- and a later cache hit, which does know the
    prompt, can still fill it in.

    An existing sidecar is never overwritten; it is verified and its status
    reported, so this doubles as the cache audit. Writes only inside
    `cache_dir` -- or, for a same-key alias symlink, inside the entry it names
    (see `is_same_key_alias`; that is the normal worktree layout here, and
    refusing it would mean the backfill never attributes anything in a
    worktree). `follow_symlinks=True` additionally writes through a RENAMING
    symlink, whose record will not verify from the target's own path. Returns one record per key directory, sorted by key.

    One unreadable or unwritable key directory is recorded as `error` and the
    walk continues: these caches are shared between checkouts, so a read-only
    or concurrently-modified directory is the expected failure, and aborting
    would discard every row already collected.
    """
    cache_dir = cache_dir or output_dir()
    if not os.path.isdir(cache_dir):
        return []
    known = {cache_key(p, q): (p, q) for p, q in KNOWN_CACHE_PROMPTS}

    report = []
    for key in sorted(os.listdir(cache_dir)):
        key_dir = os.path.join(cache_dir, key)
        is_link = os.path.islink(key_dir)
        if not os.path.isdir(key_dir):
            # isdir() FOLLOWS the link, so a key aliased into a sibling
            # worktree that has since been cleaned lands here. Report it --
            # dropping the row would make the audit silent about a cache entry
            # that has lost its bytes.
            if is_link:
                lost_p, lost_q = known.get(key, (None, None))
                report.append({"key": key, "provider": lost_p,
                               "prompt": lost_q, "action": "dangling_symlink",
                               "status": "ERROR", "error":
                               f"key dir points at a missing target: "
                               f"{os.readlink(key_dir)!r}"})
            continue
        provider, prompt = known.get(key, (None, None))
        row = {"key": key, "provider": provider, "prompt": prompt,
               "action": None, "status": None, "error": None}
        allowed = (may_write_provenance(key_dir) if aliases
                   else not is_link) or follow_symlinks
        try:
            seen = verify_mesh_meta(key_dir)
            # Repair fixes a DAMAGED RECORD (unparseable, or claiming a prompt
            # that does not hash to this key). It must never touch a record
            # whose digest or size disagrees: that record is not broken, it is
            # intact provenance correctly reporting that the BYTES changed, and
            # rewriting it would restate a swapped mesh as the real one and
            # turn the audit permanently green.
            repairable = (repair and seen["status"] == "MISMATCH"
                          and provider is not None
                          and not (set(seen["reasons"]) & BYTE_REASONS))
            if has_mesh_meta(key_dir) and not repairable:
                # Never overwrite an existing sidecar -- including a corrupted
                # one, which is evidence and reads MISMATCH rather than being
                # repaired out from under the audit. `repair=True` is the
                # explicit, opt-in way out of that state.
                row["action"], row["status"] = "kept", seen["status"]
            elif seen["status"] == "NO_MESH" and not has_mesh_meta(key_dir):
                row["action"], row["status"] = "no_mesh", "NO_MESH"
            elif provider is None:
                row["action"], row["status"] = "unattributed", "NO_META"
            elif not allowed:
                row["action"], row["status"] = "skipped_symlink", "NO_META"
            elif not (write and provenance_enabled()):
                row["action"] = "would_write"
                row["status"] = seen["status"]
            else:
                write_mesh_meta(key_dir, provider=provider, prompt=prompt,
                                provenance="backfill")
                row["action"] = "repaired" if repairable else "written"
                row["status"] = verify_mesh_meta(key_dir)["status"]
        except (OSError, ValueError) as e:
            # ValueError: the entry's mesh.glb resolves outside the cache
            # entry (resolve_cached_glb) -- a finding, not a crash.
            row["action"], row["status"] = "error", "ERROR"
            row["error"] = str(e)
        report.append(row)
    return report


def run_backfill_cli(argv: list[str]) -> int:
    """`mesh_acquire.py --backfill [cache_dir] [flags]`; returns an exit code.

    Flags: --audit (report only, write nothing) - --repair (replace sidecars
    that FAIL verification, where the key is provable) - --no-aliases (refuse
    to write through a same-key alias into another checkout) -
    --follow-symlinks (also write through a RENAMING symlink).

    Exit 0 clean - 1 a key dir failed verification or could not be read/written
    - 2 the cache directory does not exist, which is NOT a clean audit: a
    typo'd path, an unset MESH_OUTPUT_DIR and a never-bootstrapped worktree
    would otherwise all read as success.
    """
    known_flags = {"--audit", "--repair", "--no-aliases", "--follow-symlinks"}
    flags = {a for a in argv if a.startswith("--")}
    # Reject rather than ignore: a mistyped read-only flag (--dry-run,
    # --no-write) would otherwise fall through to the WRITING default, which
    # through a same-key alias mutates another checkout's cache.
    unknown = sorted(flags - known_flags)
    if unknown:
        print(f"unknown flag(s): {' '.join(unknown)}")
        print(f"usage: mesh_acquire.py --backfill [cache_dir] "
              f"[{' '.join(sorted(known_flags))}]")
        return 2
    rest = [a for a in argv if not a.startswith("--")]
    where = rest[0] if rest else output_dir()
    if not os.path.isdir(where):
        print(f"no such cache directory: {where}")
        return 2
    rows = backfill_mesh_cache(
        where, follow_symlinks="--follow-symlinks" in flags,
        aliases="--no-aliases" not in flags, write="--audit" not in flags,
        repair="--repair" in flags)
    print(f"cache: {where}  ({len(rows)} key dirs)")
    for r in rows:
        who = (f"{r['provider']}:{r['prompt']}"
               if r["provider"] is not None else "<unrecovered>")
        if r["error"]:
            who = f"{who}  [{r['error']}]"
        print(f"  {r['key'][:12]}  {r['action']:<17} {r['status']:<9} {who}")
    counts = {}
    for r in rows:
        counts[r["action"]] = counts.get(r["action"], 0) + 1
    print("  " + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    if any(r["status"] == "MISMATCH" for r in rows) and "--repair" not in flags:
        print("  MISMATCH rows are preserved as evidence; re-run with "
              "--repair to rewrite the ones whose key is provable.")
    return backfill_exit_code(rows)


def backfill_exit_code(report: list[dict]) -> int:
    """1 when any key dir failed verification or could not be read/written.

    Separated from the CLI so the gate is testable: an audit that exits 0 on a
    MISMATCH cannot gate anything, which is how a metric ends up vacuous.
    """
    return int(any(r.get("status") in ("MISMATCH", "ERROR") for r in report))


def _cached_concept(key_dir: str) -> str | None:
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        c = os.path.join(key_dir, "concept" + ext)
        if os.path.isfile(c) and os.path.getsize(c) > 0:
            return c
    return None


def cached_files(key_dir: str) -> tuple[str | None, str]:
    """A cache folder's concept image (None if it has none) and its mesh.glb."""
    return _cached_concept(key_dir), os.path.join(key_dir, "mesh.glb")


# ---------------------------------------------------------------------------
# Reference mesh library (MESH_LIBRARY_DIR)
#
# A folder of meshes chosen ahead of time, one per subject, each beside the
# photograph it was generated from: `meshes/<stem>.glb` and `photos/<stem>.png`
# (the layout of the photo_meshes test set). The app serves a subject's library
# mesh as its first mesh round. An entry is copied into the cache as an ordinary
# folder (mesh.glb, the photo as concept.png, meta.json), so the review's
# ratings, retries and provenance audit treat it like any other cached mesh.

LIBRARY_PROVIDER = "library"


def library_dir() -> str | None:
    return os.environ.get("MESH_LIBRARY_DIR") or None


def _library_entry(subject: str, library: str) -> tuple[str, str | None] | None:
    """(glb, photo-or-None) for the library file whose stem, `_` read as a
    space, has `subject` as its ratings key."""
    import mesh_ratings
    meshes = os.path.join(library, "meshes")
    try:
        names = sorted(os.listdir(meshes))
    except OSError:
        return None
    for name in names:
        stem, ext = os.path.splitext(name)
        if ext.lower() != ".glb" or mesh_ratings.subject_key(stem.replace("_", " ")) != subject:
            continue
        glb = os.path.join(meshes, name)
        if not os.path.isfile(glb) or os.path.getsize(glb) == 0:
            continue
        photo = None
        for pext in (".png", ".jpg", ".jpeg", ".webp"):
            p = os.path.join(library, "photos", stem + pext)
            if os.path.isfile(p) and os.path.getsize(p) > 0:
                photo = p
                break
        return glb, photo
    return None


def library_mesh(subject: str, *, cache_dir: str | None = None) -> str | None:
    """The cache folder holding `subject`'s library mesh, made on first use; None
    when MESH_LIBRARY_DIR is unset or has no mesh for `subject` (a ratings key,
    `mesh_ratings.subject_key`). The folder is keyed on the glb's digest, so an
    edited library file gets a new folder and its own ratings."""
    library = library_dir()
    entry = _library_entry(subject, library) if library and subject else None
    if entry is None:
        return None
    glb, photo = entry
    stem = os.path.splitext(os.path.basename(glb))[0]
    settings = {"glb_sha256": sha256_file(glb)}
    cache_dir = cache_dir or output_dir()
    key_dir = os.path.join(cache_dir, cache_key(LIBRARY_PROVIDER, stem, settings))
    cached = os.path.join(key_dir, "mesh.glb")
    if os.path.isfile(cached) and os.path.getsize(cached) > 0:
        return key_dir
    # Built in a temp folder and renamed into place, so a reader never sees a
    # folder with a mesh but no photo.
    os.makedirs(cache_dir, exist_ok=True)
    tmp = tempfile.mkdtemp(dir=cache_dir, prefix=".library-")
    try:
        shutil.copyfile(glb, os.path.join(tmp, "mesh.glb"))
        if photo:
            shutil.copyfile(photo, os.path.join(tmp, "concept" + os.path.splitext(photo)[1].lower()))
        _write_mesh_meta_best_effort(tmp, respect_alias_rule=False, provider=LIBRARY_PROVIDER,
                                     prompt=stem, provenance="library", settings=settings)
        try:
            os.rename(tmp, key_dir)
        except OSError:
            if not os.path.isfile(cached):     # not a race with another run: a real failure
                raise
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return key_dir


def acquire_mesh(prompt: str, *, provider: MeshProvider | None = None,
                 provider_name: str | None = None,
                 cache_dir: str | None = None, progress=None,
                 description: str | None = None,
                 seed: int | None = None) -> str:
    """Return a rough .glb for `prompt`, served from cache when available.

    Both exits record provenance in `key_dir/meta.json`. The cache hit needs it
    as much as the fetch does: this function returns from the cache BEFORE it
    ever reaches provider.generate, so a sidecar written only in the fetch path
    would attach to future fetches and never to the meshes that already exist --
    it would not attribute the very meshes it exists for.

    `progress(kind, path)`, if given, is called with ("image", concept-or-None)
    and then ("mesh", glb), on the fetch and cache-hit paths alike.
    """
    if provider_name is not None:
        name = provider_name
    elif provider is not None:
        name = type(provider).__name__
    else:
        # Same fallback as get_provider: offline 'fake' (C-8 no-spend). This
        # used to say 'meshy' and error on a missing MESHY_API_KEY when the
        # env was unset (docs/followups-web-ui-and-foldability.md item 8).
        name = os.environ.get("MESH_PROVIDER", "fake")
    provider = provider or get_provider(name, description=description, seed=seed)
    cache_dir = cache_dir or output_dir()
    settings = getattr(provider, "cache_settings", None)
    key_dir = os.path.join(cache_dir, cache_key(name, prompt, settings))
    cached = os.path.join(key_dir, "mesh.glb")
    if os.path.isfile(cached) and os.path.getsize(cached) > 0:
        # Keyed on the FILE existing, not on it parsing: a corrupted sidecar
        # must survive for the audit, not be quietly replaced by a thinner one.
        if not has_mesh_meta(key_dir):
            # The endpoint is left unknown on purpose: these bytes were
            # produced by whatever HF_SPACE_ID was set at generation time,
            # which is not necessarily the one set now.
            _write_mesh_meta_best_effort(
                key_dir, respect_alias_rule=True, provider=name, prompt=prompt,
                provenance="cache_hit", settings=settings)
        if progress:
            progress("image", _cached_concept(key_dir))
            progress("mesh", cached)
        return cached
    started = _utc()
    import inspect
    takes_progress = "progress" in inspect.signature(provider.generate).parameters
    if progress and takes_progress:
        result = provider.generate(prompt, key_dir, progress=progress)
    else:
        if progress:
            # no concept image to show, and the call below may take minutes: report the
            # image step now so it does not look like it spans the whole generation
            progress("image", None)
        result = provider.generate(prompt, key_dir)
    if not os.path.isfile(result) or os.path.getsize(result) == 0:
        raise RuntimeError(
            f"provider {name} returned a missing or empty mesh: {result!r}")
    if progress:
        progress("mesh", result)
    # space_id/api_name come off the provider object, which get_provider seeds
    # from HF_SPACE_ID/HF_API_NAME; non-hf providers simply have neither.
    _write_mesh_meta_best_effort(
        key_dir, respect_alias_rule=False, provider=name, prompt=prompt,
        provenance="generated",
        space_id=getattr(provider, "space_id", None),
        api_name=getattr(provider, "api_name", None),
        generated_utc=started, glb=os.path.basename(result),
        settings=settings)
    return result


if __name__ == "__main__":
    import sys
    argv = sys.argv[1:]
    if argv and argv[0] == "--backfill":
        sys.exit(run_backfill_cli(argv[1:]))
    print(acquire_mesh(" ".join(argv) or "a quadruped animal"))
