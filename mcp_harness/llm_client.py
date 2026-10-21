"""Provider-agnostic LLM client for the VLM tree-authoring path.

One responsibility: turn a (system, messages, tools) request into a completed,
non-streaming turn against ANY OpenAI-compatible endpoint -- Groq, Gemini,
Ollama, or Anthropic's compat endpoint. Selected by environment variable so the
project can run on a free/cheap backend. Knows nothing about origami.

IMAGE INPUT (added 2026-08-15)
------------------------------
Nothing in this repo had ever sent an image to a model. A prior design spec for
showing a vision model rendered pictures of a design listed as its precondition
#1 "verify the compat endpoint accepts `image_url` content-parts", declined to
spend a live API call on it, and the whole vision line of work sat blocked on
that UNVERIFIED note from 2026-08-04 onward. Before this change a grep for
`image` / `image_url` / `base64` across `llm_client.py`, `agent_loop.py` and
`web/server.py` returned ZERO matches.

**The answer is YES, measured, not assumed.** One live call on 2026-08-15
against `https://api.anthropic.com/v1/`, model **`claude-sonnet-5`** (what the
repo `.env` pins via `LLM_MODEL`; the preset default was then
`claude-sonnet-4-6`, which this run did NOT exercise) --
`probe_image_contentpart.py`, transcript in
`docs/superpowers/evidence/2026-08-15-image-contentpart/README.md` -- sent a
128x128 PNG containing exactly three circles as a `data:image/png;base64,...`
`image_url` content-part through `LLMClient.run_turn` unchanged, and the model
answered **3**, correctly, via a tool call. HTTP 200, `finish_reason
= 'tool_calls'`. Anthropic's own compat table agrees: for `role == "user"`,
`content` array, `type == "image_url"`, the `url` sub-field is "Fully
supported" and only `detail` is ignored.

DESIGN: PURELY ADDITIVE. `run_turn` was not touched. It already forwards
`messages` to the endpoint verbatim, so an image rides in on the message list
with no change to the request builder -- the whole feature here is four small
constructors (`image_data_uri`, `image_part`, `text_part`,
`user_message_with_images`) that produce the OpenAI content-part shape. The
text-only payload is pinned byte-identical by
`tests/test_llm_client.py::test_text_only_request_payload_is_byte_identical`,
because this file carries the entire agent loop and a silent shift in the
request body would be invisible until it cost a paid run.

CAVEATS THE COMPAT LAYER IMPOSES (Anthropic's published table, same source):
`detail` is ignored, `input_audio` and `file` content-parts are ignored, and
prompt caching is unavailable here -- so an image is re-uploaded and re-billed
on every turn it stays in the history. There is no `image` (native Anthropic
`{"type": "image", "source": {...}}`) shape on this endpoint; that belongs to
the native Messages API, which is the fallback if the compat layer ever drops
`image_url`.
"""
from __future__ import annotations

import asyncio
import base64
import os
from dataclasses import dataclass, field
from pathlib import Path
from openai import AsyncOpenAI, APIStatusError

# Preset registry. Every provider here speaks the OpenAI chat-completions API;
# only base_url / model / key env var differ. api_key_env=None means the
# provider needs no key (local Ollama).
PROVIDERS: dict[str, dict] = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "api_key_env": "GROQ_API_KEY",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "default_model": "gemini-2.0-flash",
        "api_key_env": "GEMINI_API_KEY",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "default_model": "qwen2.5:7b",
        "api_key_env": None,
    },
    "claude": {
        "base_url": "https://api.anthropic.com/v1/",
        # Haiku 5.5 since 2026-10-10: 51/51 trees folded on the 17 original meshes at
        # $0.003/tree (~/Desktop/origami_samples_haiku_work/README.md). The app offers
        # claude-sonnet-5 per action; LLM_MODEL still overrides this default.
        "default_model": "claude-haiku-5-5",
        "api_key_env": "ANTHROPIC_API_KEY",
    },
}


#: Models that reject tool_choice "required" (the compat endpoint maps it to
#: "any"). See LLMClient.run_turn.
NO_FORCED_TOOL_USE = frozenset({"claude-opus-5-5", "claude-sonnet-5-5",
                                "claude-fable-5-1", "claude-mythos-5-1"})


@dataclass
class LLMConfig:
    """Resolved backend selection. Build with from_env()."""

    provider: str
    model: str
    base_url: str
    api_key: str
    max_tokens: int = 4096
    temperature: float | None = None
    #: Extra HTTP headers sent on every request. Empty dict = today's behaviour
    #: byte-for-byte; `AsyncOpenAI` receives `None` rather than `{}` so the
    #: no-header path cannot differ from before this field existed.
    extra_headers: dict = field(default_factory=dict)

    @classmethod
    def from_env(cls, model: str | None = None) -> "LLMConfig":
        """`model`, when given, wins over LLM_MODEL and the preset default."""
        provider = os.environ.get("LLM_PROVIDER", "claude")
        if provider not in PROVIDERS:
            raise ValueError(
                f"unknown LLM_PROVIDER {provider!r}; "
                f"valid: {', '.join(sorted(PROVIDERS))}")
        preset = PROVIDERS[provider]
        model = model or os.environ.get("LLM_MODEL", preset["default_model"])
        base_url = os.environ.get("LLM_BASE_URL", preset["base_url"])

        key_env = preset["api_key_env"]
        if key_env is None:
            api_key = "ollama"          # local; the SDK still wants a non-empty key
        else:
            api_key = os.environ.get(key_env, "")
            if not api_key:
                raise ValueError(
                    f"provider {provider!r} requires an API key; set {key_env}")

        max_tokens = int(os.environ.get("LLM_MAX_TOKENS", "4096"))
        temperature = (
            float(os.environ["LLM_TEMPERATURE"])
            if "LLM_TEMPERATURE" in os.environ
            else None
        )
        # An IDENTITY-LINKED API key (the kind a federated / service-account
        # issue produces) is rejected on EVERY endpoint without this header:
        # `400 invalid_request_error -- anthropic-workspace-id is required when
        # authenticating with an identity-linked API key`. Measured 2026-08-29
        # against /v1/messages AND /v1/models, so it is not a Messages-API
        # quirk. A classic org key ignores the header, so sending it whenever
        # the env var is set is safe for both key kinds; the workspace id
        # cannot be discovered from the key itself (listing workspaces needs an
        # Admin key and returns 403 here), so it has to be supplied.
        headers = {}
        workspace = os.environ.get("ANTHROPIC_WORKSPACE_ID", "").strip()
        if workspace and provider == "claude":
            headers["anthropic-workspace-id"] = workspace
        return cls(provider, model, base_url, api_key, max_tokens, temperature,
                   headers)


def tools_to_openai(mcp_tools) -> list[dict]:
    """Convert discovered MCP tools to OpenAI's function-tool schema.

    Each input item has .name, .description, and .inputSchema (already JSON
    Schema, which is exactly what OpenAI's `function.parameters` expects).
    """
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": t.inputSchema,
            },
        }
        for t in mcp_tools
    ]


# ---------------------------------------------------------------------------
# Image content parts
#
# The OpenAI chat-completions shape for a multimodal user turn is a message
# whose `content` is a LIST of parts rather than a string:
#
#     {"role": "user", "content": [
#         {"type": "text", "text": "how many circles?"},
#         {"type": "image_url",
#          "image_url": {"url": "data:image/png;base64,iVBORw0KG..."}}]}
#
# `run_turn` forwards `messages` untouched, so these constructors are the whole
# feature. Nothing below is called by the existing text path.
# ---------------------------------------------------------------------------

#: Magic-byte prefixes -> IANA media type. Only the formats a rendered origami
#: figure can plausibly arrive as. Order matters only in that every prefix here
#: is unambiguous. WEBP needs a two-part check and is handled separately.
_MAGIC_PREFIXES: tuple[tuple[bytes, str], ...] = (
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
)


def sniff_media_type(data: bytes) -> str:
    """Return the IANA media type of `data` from its magic bytes.

    Raises ValueError on anything unrecognised rather than guessing: a wrong
    media type is accepted by the SDK and rejected by the endpoint, which turns
    a local bug into a paid round trip.
    """
    for prefix, media_type in _MAGIC_PREFIXES:
        if data.startswith(prefix):
            return media_type
    # RIFF____WEBP -- the 4-byte length sits between the two markers.
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    raise ValueError(
        "unrecognised image format (first bytes: "
        f"{data[:8]!r}); pass media_type= explicitly if you are sure")


def _read_image(image: bytes | str | os.PathLike) -> bytes:
    """Raw bytes for `image`. `bytes` is used as-is; anything else is a PATH.

    A `str` is ALWAYS a filesystem path here, never base64 -- guessing between
    the two is exactly the kind of ambiguity that silently ships a literal
    "path/to.png" string to a paid endpoint.
    """
    if isinstance(image, bytes):
        return image
    if isinstance(image, bytearray | memoryview):
        return bytes(image)
    return Path(os.fspath(image)).read_bytes()


def image_data_uri(image: bytes | str | os.PathLike,
                   media_type: str | None = None) -> str:
    """`data:<media_type>;base64,<...>` for a PNG path or raw image bytes.

    `media_type` is sniffed from the magic bytes unless given explicitly.
    """
    data = _read_image(image)
    if not data:
        raise ValueError("empty image data")
    if media_type is None:
        media_type = sniff_media_type(data)
    return f"data:{media_type};base64,{base64.b64encode(data).decode('ascii')}"


def text_part(text: str) -> dict:
    """A `{"type": "text", ...}` content part."""
    return {"type": "text", "text": text}


def image_part(image: bytes | str | os.PathLike,
               media_type: str | None = None) -> dict:
    """An `{"type": "image_url", ...}` content part holding a data URI.

    `detail` is deliberately omitted: Anthropic's compat layer documents it as
    ignored, and sending an ignored field invites the reader to believe it does
    something.
    """
    return {"type": "image_url",
            "image_url": {"url": image_data_uri(image, media_type)}}


def user_message_with_images(text: str, images) -> dict:
    """One user message carrying `text` plus every image in `images`.

    Text first, then the images -- the order the caller reads them in. `images`
    is an iterable of paths or raw bytes; passing a bare `bytes` or `str` is a
    TypeError rather than a silently-iterated sequence of characters/ints.

    There is deliberately NO `media_type` parameter here. One media type
    broadcast across a mixed list would label a JPEG as a PNG and send it --
    exactly the failure `sniff_media_type` refuses to make locally, smuggled
    back in through the constructor callers actually reach for. Every image is
    sniffed individually; a caller who must override the type builds that one
    part with `image_part(img, media_type)` and assembles the message itself.
    """
    if isinstance(images, bytes | str | bytearray | memoryview):
        raise TypeError(
            "images must be a SEQUENCE of images, not a single image; "
            "wrap it in a list")
    parts = [text_part(text)]
    parts.extend(image_part(img) for img in images)
    return {"role": "user", "content": parts}


def _transient_tpm_delay(exc: APIStatusError, default: float = 60.0) -> float | None:
    """Seconds to wait before retrying a transient tokens-per-minute rate-limit,
    or None if `exc` is not that case (caller should re-raise).

    Groq signals a TPM limit as HTTP 413 (not 429), so we key on the response
    BODY -- code 'rate_limit_exceeded' AND type 'tokens' -- which stays correct
    across providers and distinguishes the transient TPM window from a permanent
    context-length overflow. Honors the `retry-after` header when present (and
    numeric), else falls back to `default`.
    """
    body = getattr(exc, "body", None)
    if not isinstance(body, dict):
        return None
    err = body.get("error", body)
    if not isinstance(err, dict):
        return None
    if err.get("code") != "rate_limit_exceeded" or err.get("type") != "tokens":
        return None

    retry_after = None
    resp = getattr(exc, "response", None)
    if resp is not None:
        retry_after = resp.headers.get("retry-after")
    try:
        return float(retry_after) if retry_after is not None else default
    except (TypeError, ValueError):
        return default


@dataclass
class TurnResult:
    """One model turn. tool_calls items are OpenAI SDK tool-call objects, each
    with .id and .function.{name, arguments}; arguments is a JSON string."""

    text: str
    tool_calls: list
    finish_reason: str
    #: Token counts as the endpoint reported them, or None if it reported none.
    #: `run_turn` used to DISCARD `resp.usage`, which meant nothing in this
    #: repo could say what a run cost -- an image-heavy loop on an endpoint
    #: with no prompt caching re-uploads and re-bills every picture on every
    #: turn it stays in history, and none of that was observable. Additive and
    #: defaulted, so every existing construction and the pinned request payload
    #: are untouched.
    usage: dict | None = None


class LLMClient:
    """Non-streaming chat-completions client over any OpenAI-compatible endpoint."""

    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg
        self.model = cfg.model
        self.max_tokens = cfg.max_tokens
        self.temperature = cfg.temperature
        self._client = AsyncOpenAI(base_url=cfg.base_url, api_key=cfg.api_key,
                                   default_headers=cfg.extra_headers or None)

    @classmethod
    def from_env(cls, model: str | None = None) -> "LLMClient":
        return cls(LLMConfig.from_env(model))

    async def run_turn(self, system, messages, tools) -> TurnResult:
        """Run one turn. `messages` is OpenAI-format history (no system message --
        we prepend it here). Returns the assistant text, any tool calls, and the
        finish reason."""
        kwargs: dict = dict(
            model=self.model,
            messages=[{"role": "system", "content": system}] + messages,
            tools=tools,
            max_tokens=self.max_tokens,
        )
        # Only when there is something to choose from. The endpoint rejects the
        # pair outright -- 400 "'tool_choice' is only allowed when 'tools' are
        # specified" -- and a tool-less caller is legitimate: the anatomy judge
        # wants prose-wrapped JSON and offering it a tool surface invites it to
        # call something instead of answering. Latent until 2026-08-16 because
        # every prior caller passed real tools.
        #
        # "required", not "auto": a turn offered tools must answer with one.
        # On "auto" the endpoint may answer in prose instead, and the tree
        # author (gated_pipeline._author, the one caller that passes tools)
        # lost a revision that way on 2026-10-11 (Haiku 5.5, the moose run).
        # Checked live: api.anthropic.com/v1/ accepts "required" and returns
        # the tool call.
        #
        # EXCEPT the models that refuse forced tool use outright -- measured
        # 2026-10-16: claude-opus-5-5 and claude-fable-5-1 answer 400 'tool_choice:
        # type "tool" and "any" are not supported for this model'. They get
        # "auto"; every caller that offers tools already repairs a prose answer.
        if tools:
            kwargs["tool_choice"] = ("auto" if self.model in NO_FORCED_TOOL_USE
                                     else "required")
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature

        # Groq's free tier enforces a 12K tokens/MINUTE cap and signals it as a
        # transient HTTP 413. Retry only that case (waiting for the window to
        # reset), capped so a permanent oversize request still fails cleanly. The
        # SDK's max_retries does not cover 413 and backs off far less than 60s.
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                resp = await self._client.chat.completions.create(**kwargs)
                break
            except APIStatusError as exc:
                delay = _transient_tpm_delay(exc)
                if delay is None or attempt == max_attempts:
                    raise
                await asyncio.sleep(delay)

        choice = resp.choices[0]
        msg = choice.message
        u = getattr(resp, "usage", None)
        return TurnResult(
            text=msg.content or "",
            tool_calls=list(msg.tool_calls or []),
            finish_reason=choice.finish_reason,
            usage=(u.model_dump() if hasattr(u, "model_dump")
                   else (dict(u) if u else None)),
        )
