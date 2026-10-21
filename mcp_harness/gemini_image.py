"""Text -> concept image through Google's Gemini image models ("Nano Banana").

One responsibility: a prompt goes in, an image file comes out, with the
response's usage metadata. It knows nothing about meshes or the experiment
that first used it (spec 2026-10-16-concept-image-quality-design.md). Since
2026-10-19 it is the image stage of MESH_PROVIDER=hf2 whenever GEMINI_API_KEY
is set (spec 2026-10-19-nano-banana-image-stage-design.md).

WHY GEMINI. Live meshes trailed the owner's photo-derived library meshes even
though the Hunyuan3D-2 lift was byte-for-byte the same settings: the concept
image was the gap. FLUX.1-schnell (4 steps) drew scorpions with seven legs a
side, detached tails and no head. Nano Banana 2.1 ranked #4 overall on the
Artificial Analysis text-to-image arena on 2026-10-16 at about $0.034 an image.

MEASURED ON THE LIVE PROBE (2026-10-16, paid tier, prompt = the shipped
concept template for "scorpion", seed 11, twice):
  * `seed` and `imageConfig.aspectRatio` are ACCEPTED, but the seed does not
    reproduce: two calls with seed 11 returned different images. Treat every
    draw as fresh; the seed is recorded, not relied on.
  * The image comes back as image/jpeg, 1024x1024, in ~12 s.
  * usageMetadata: 63 prompt tokens, 1,394 candidate tokens (1,120 of them
    IMAGE), 840 thinking tokens. Paid-tier prices
    (https://ai.google.dev/gemini-api/docs/pricing, read 2026-10-16): input
    $1.50/M, image output $30/M, text and thinking output $7.50/M -> about
    $0.042 an image, of which $0.0336 is the image itself.
  * An image with a finishReason other than STOP is still returned; only a
    response with no image raises.

REST over httpx, not the google-genai SDK: httpx is already a dependency, and
the one call we need is a single POST.

ERRORS (spec 2026-10-19-nano-banana-image-stage-design.md §5). A
GeminiImageError carries the HTTP status and the parsed error body, and
`no_image_quota` / `is_transient` read them, so no caller parses message text:
  * NO QUOTA, never retried: 402; 400 FAILED_PRECONDITION (billing); a 429
    whose QuotaFailure violation has quotaValue "0", or whose message says
    "limit: 0" or that prepayment credits are depleted. The pricing page lists
    the free tier of this model as "Not available", so every free-tier key lands
    here -- and its 429 still carries a RetryInfo delay that waiting never
    honours (google-gemini/gemini-cli#8437; the Google forum's image-429 thread).
  * TRANSIENT, worth a retry: no status (the request never got an answer),
    408, 429 otherwise, 500, 502, 503, 504 -- Google's troubleshooting page.
    A request that fails with 4xx/5xx is not billed (billing docs).
  * Anything else (400 bad key, 403, an answer with no image) is neither.
"""
from __future__ import annotations

import base64
import os
import re
import tempfile
from dataclasses import dataclass

import httpx

DEFAULT_MODEL = "gemini-nano-banana-2.1"
API_ROOT = "https://generativelanguage.googleapis.com/v1beta"


class GeminiImageError(RuntimeError):
    """The request failed, or the answer carried no image; the message says which.

    `status` is None when no answer came back, the HTTP status of a failed
    answer, or 200 for an answer with no image; `body` is its parsed JSON."""

    def __init__(self, message: str, *, status: int | None = None,
                 body: dict | None = None):
        super().__init__(message)
        self.status = status
        self.body = body


_TRANSIENT = frozenset({408, 429, 500, 502, 503, 504})
_LIMIT_ZERO = re.compile(r"limit:\s*0\b")


def _error(body) -> dict:
    err = body.get("error") if isinstance(body, dict) else None
    return err if isinstance(err, dict) else {}


def no_image_quota(e: GeminiImageError) -> bool:
    """The key cannot draw at all on its tier; waiting will not help."""
    err = _error(e.body)
    if e.status == 402:
        return True
    if e.status == 400:
        return err.get("status") == "FAILED_PRECONDITION"
    if e.status != 429:
        return False
    message = str(err.get("message", "")).casefold()
    if _LIMIT_ZERO.search(message):
        return True
    if "prepayment credits" in message and "depleted" in message:
        return True
    for detail in err.get("details") or []:
        for v in (detail.get("violations") or []) if isinstance(detail, dict) else []:
            if isinstance(v, dict) and v.get("quotaValue") in ("0", 0):
                return True
    return False


def is_transient(e: GeminiImageError) -> bool:
    """A retry may succeed."""
    if e.status is None:
        return True
    return e.status in _TRANSIENT and not no_image_quota(e)


@dataclass
class GeminiImage:
    path: str
    model: str
    seed: int | None
    mime_type: str
    usage: dict
    finish_reason: str


def _request_body(prompt: str, seed: int | None) -> dict:
    config = {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "1:1"}}
    if seed is not None:
        config["seed"] = seed
    return {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": config}


def _json_or_none(resp: httpx.Response) -> dict | None:
    try:
        body = resp.json()
    except ValueError:
        return None
    return body if isinstance(body, dict) else None


def _error_message(resp: httpx.Response) -> str:
    return _error(_json_or_none(resp)).get("message") or resp.text[:300]


def _image_from(data: dict | None, model: str) -> tuple[bytes, str, str]:
    """(image bytes, mime type, finishReason) from a 200 answer. A well-formed
    answer with no image raises GeminiImageError; a malformed one raises
    whatever its shape trips, for the caller to wrap."""
    if data is None:
        raise ValueError("not a JSON object")
    cand = (data.get("candidates") or [{}])[0]
    finish = cand.get("finishReason", "")
    parts = (cand.get("content") or {}).get("parts") or []
    inline = next((p["inlineData"] for p in parts if p.get("inlineData")), None)
    if inline is None:
        text = " ".join(p.get("text", "") for p in parts).strip()
        block = (data.get("promptFeedback") or {}).get("blockReason", "")
        raise GeminiImageError(f"Gemini {model} returned no image (finishReason "
                               f"{finish or block or 'unknown'}): {text or 'no text'}",
                               status=200, body=data)
    return (base64.b64decode(inline["data"], validate=True),
            inline.get("mimeType", ""), finish)


def generate_image(prompt: str, out_path: str, *, model: str = DEFAULT_MODEL,
                   seed: int | None = None, api_key: str | None = None,
                   transport: httpx.BaseTransport | None = None,
                   timeout: float = 120.0) -> GeminiImage:
    """Draw `prompt` and write the image to `out_path` (atomically)."""
    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise GeminiImageError("no Gemini API key: set GEMINI_API_KEY in the repo-root .env")
    url = f"{API_ROOT}/models/{model}:generateContent"
    with httpx.Client(transport=transport, timeout=timeout) as client:
        try:
            resp = client.post(url, headers={"x-goog-api-key": key},
                               json=_request_body(prompt, seed))
        except httpx.HTTPError as e:
            raise GeminiImageError(f"Gemini request to {model} failed: {e}") from e
    if resp.status_code != 200:
        raise GeminiImageError(f"Gemini {model} answered HTTP {resp.status_code}: "
                               f"{_error_message(resp)}",
                               status=resp.status_code, body=_json_or_none(resp))
    data = _json_or_none(resp)
    try:
        image, mime_type, finish = _image_from(data, model)
    except GeminiImageError:
        raise
    except (ValueError, KeyError, TypeError, AttributeError, IndexError) as e:
        # A 200 of an unexpected shape must still be a GeminiImageError: callers
        # (the app's failed-stage handling) catch RuntimeError, not KeyError.
        raise GeminiImageError(f"Gemini {model} answered 200 with an unreadable "
                               f"body ({type(e).__name__}: {e})",
                               status=200, body=data) from e
    out_dir = os.path.dirname(os.path.abspath(out_path))
    os.makedirs(out_dir, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=out_dir, suffix=".part")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(image)
        os.replace(tmp, out_path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
    return GeminiImage(path=out_path, model=model, seed=seed, mime_type=mime_type,
                       usage=data.get("usageMetadata") or {}, finish_reason=finish)
