"""Network-free unit tests for the pluggable LLM client (config + conversion).

Every test here is offline.
"""
import sys
sys.path.insert(0, "tests")

from types import SimpleNamespace
import pytest
import llm_client
from llm_client import PROVIDERS, LLMConfig, tools_to_openai


def test_from_env_defaults_to_claude(monkeypatch):
    for v in ("LLM_PROVIDER", "LLM_MODEL", "LLM_BASE_URL",
              "LLM_MAX_TOKENS", "LLM_TEMPERATURE"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    cfg = LLMConfig.from_env()
    assert cfg.provider == "claude"
    assert cfg.base_url == PROVIDERS["claude"]["base_url"]
    assert cfg.model == PROVIDERS["claude"]["default_model"]
    assert cfg.api_key == "sk-test"
    assert cfg.max_tokens == 4096
    assert cfg.temperature is None


def test_claude_preset_defaults_to_sonnet_and_an_explicit_model_beats_llm_model(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    assert LLMConfig.from_env().model == "claude-sonnet-5"
    monkeypatch.setenv("LLM_MODEL", "claude-haiku-5-5")
    assert LLMConfig.from_env().model == "claude-haiku-5-5"
    assert LLMConfig.from_env("claude-sonnet-5").model == "claude-sonnet-5"


def test_from_env_groq_resolves_preset(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test")
    # A stray LLM_MODEL / LLM_BASE_URL (from a developer .env or shell) would
    # shadow the preset and flake the full-suite run -- pin them absent.
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    cfg = LLMConfig.from_env()
    assert cfg.base_url == "https://api.groq.com/openai/v1"
    assert cfg.model == "llama-3.3-70b-versatile"
    assert cfg.api_key == "gsk-test"


def test_from_env_model_and_base_url_overrides(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test")
    monkeypatch.setenv("LLM_MODEL", "some-other-model")
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:9999/v1")
    cfg = LLMConfig.from_env()
    assert cfg.model == "some-other-model"
    assert cfg.base_url == "http://localhost:9999/v1"


def test_from_env_ollama_needs_no_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    cfg = LLMConfig.from_env()
    assert cfg.base_url == "http://localhost:11434/v1"
    assert cfg.api_key == "ollama"          # dummy non-empty key for the SDK


def test_from_env_unknown_provider_raises(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "nope")
    with pytest.raises(ValueError, match="unknown LLM_PROVIDER"):
        LLMConfig.from_env()


def test_from_env_missing_key_raises_naming_var(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        LLMConfig.from_env()


def test_tools_to_openai_shape():
    mcp_tool = SimpleNamespace(
        name="add_node", description="Add a node",
        inputSchema={"type": "object", "properties": {"id": {"type": "integer"}}})
    out = tools_to_openai([mcp_tool])
    assert out == [{
        "type": "function",
        "function": {
            "name": "add_node",
            "description": "Add a node",
            "parameters": {"type": "object",
                           "properties": {"id": {"type": "integer"}}},
        },
    }]


def test_tools_to_openai_handles_missing_description():
    mcp_tool = SimpleNamespace(name="t", description=None, inputSchema={"type": "object"})
    out = tools_to_openai([mcp_tool])
    assert out[0]["function"]["description"] == ""


import asyncio
from llm_client import LLMClient, TurnResult


def _make_client():
    # Construct without env (AsyncOpenAI construction makes no network call).
    cfg = LLMConfig(provider="groq", model="m",
                    base_url="http://x/v1", api_key="k")
    return LLMClient(cfg)


def _fake_response(content, tool_calls, finish_reason):
    msg = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=msg,
                                                    finish_reason=finish_reason)])


class _FakeCompletions:
    def __init__(self, resp):
        self._resp = resp
        self.last_kwargs = None

    async def create(self, **kwargs):
        self.last_kwargs = kwargs
        return self._resp


def _install_fake(client, resp):
    client._client = SimpleNamespace(
        chat=SimpleNamespace(completions=_FakeCompletions(resp)))
    return client._client.chat.completions


_A_TOOL = [{"type": "function",
            "function": {"name": "noop", "description": "d",
                         "parameters": {"type": "object", "properties": {}}}}]


def test_run_turn_plain_text():
    # Passes a REAL tool: `tool_choice` is only sent when tools exist (the
    # endpoint 400s on the pair), so asserting it below requires one. This test
    # is about the plain-text return path; the empty-tools case is covered by
    # test_no_tool_choice_when_there_are_no_tools.
    client = _make_client()
    fake = _install_fake(client, _fake_response("hello", None, "stop"))
    result = asyncio.run(client.run_turn("SYS", [{"role": "user", "content": "hi"}],
                                         _A_TOOL))
    assert isinstance(result, TurnResult)
    assert result.text == "hello"
    assert result.tool_calls == []
    assert result.finish_reason == "stop"
    # system prepended, model + sampling params forwarded.
    assert fake.last_kwargs["messages"][0] == {"role": "system", "content": "SYS"}
    assert fake.last_kwargs["model"] == "m"
    assert fake.last_kwargs["max_tokens"] == 4096
    assert "temperature" not in fake.last_kwargs
    # A turn offered tools MUST answer with one (2026-10-11: on "auto", Haiku
    # sometimes answered a tree revision in prose and the round was lost).
    assert fake.last_kwargs["tool_choice"] == "required"


def test_no_tool_choice_when_there_are_no_tools():
    """REQUIRED-FAIL INPUT. Sending `tool_choice` without `tools` is rejected:

        400 invalid_request_error --
        "'tool_choice' is only allowed when 'tools' are specified"

    Measured 2026-08-16 against api.anthropic.com/v1/ while wiring the anatomy
    judge, which was this repo's first tool-less caller of run_turn. Every
    prior caller (the since-archived agent loop) passed real tools, so the bug
    could not fire and
    the plain-text test above pinned `tool_choice == "auto"` with `tools=[]`
    incidentally -- a shape the endpoint would have refused. That assertion now
    passes a real tool, which is the case it was actually about.

    Both falsy forms must be covered: the judge passes None, and a caller that
    computed an empty list is equally invalid.
    """
    for empty in (None, []):
        client = _make_client()
        fake = _install_fake(client, _fake_response("ok", None, "stop"))
        asyncio.run(client.run_turn("SYS", [{"role": "user", "content": "hi"}],
                                    empty))
        assert "tool_choice" not in fake.last_kwargs, empty
        assert not fake.last_kwargs.get("tools"), empty


def test_from_env_temperature_when_set(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "x")
    monkeypatch.setenv("LLM_TEMPERATURE", "0.7")
    cfg = LLMConfig.from_env()
    assert cfg.temperature == 0.7


def test_run_turn_includes_temperature_when_set():
    cfg = LLMConfig(provider="groq", model="m",
                    base_url="http://x/v1", api_key="k", temperature=0.5)
    client = LLMClient(cfg)
    fake = _install_fake(client, _fake_response("hi", None, "stop"))
    asyncio.run(client.run_turn("SYS", [], []))
    assert fake.last_kwargs["temperature"] == 0.5


def test_run_turn_extracts_tool_calls():
    client = _make_client()
    tc = SimpleNamespace(id="call_1",
                         function=SimpleNamespace(name="add_node",
                                                  arguments='{"id": 1}'))
    _install_fake(client, _fake_response(None, [tc], "tool_calls"))
    result = asyncio.run(client.run_turn("SYS", [], []))
    assert result.text == ""               # None content normalized to ""
    assert result.finish_reason == "tool_calls"
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].id == "call_1"
    assert result.tool_calls[0].function.name == "add_node"
    assert result.tool_calls[0].function.arguments == '{"id": 1}'


import httpx
import openai
from llm_client import _transient_tpm_delay


def _status_error(body, headers=None, status=413):
    req = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    resp = httpx.Response(status, headers=headers or {}, request=req)
    return openai.APIStatusError("err", response=resp, body=body)


def test_tpm_delay_detects_transient_and_uses_retry_after():
    exc = _status_error(
        {"error": {"code": "rate_limit_exceeded", "type": "tokens"}},
        headers={"retry-after": "5"})
    assert _transient_tpm_delay(exc) == 5.0


def test_tpm_delay_defaults_when_no_header():
    exc = _status_error({"error": {"code": "rate_limit_exceeded", "type": "tokens"}})
    assert _transient_tpm_delay(exc, default=60.0) == 60.0


def test_tpm_delay_accepts_flat_body():
    exc = _status_error({"code": "rate_limit_exceeded", "type": "tokens"})
    assert _transient_tpm_delay(exc, default=42.0) == 42.0


def test_tpm_delay_none_for_context_overflow():
    exc = _status_error({"error": {"code": "context_length_exceeded", "type": "tokens"}})
    assert _transient_tpm_delay(exc) is None


def test_tpm_delay_none_for_request_rate_limit():
    # rate_limit_exceeded but type "requests" (RPM, not TPM) -> not our case.
    exc = _status_error({"error": {"code": "rate_limit_exceeded", "type": "requests"}})
    assert _transient_tpm_delay(exc) is None


def test_tpm_delay_none_for_missing_body():
    req = httpx.Request("POST", "http://x")
    exc = openai.APIStatusError("err", response=httpx.Response(413, request=req), body=None)
    assert _transient_tpm_delay(exc) is None


def test_tpm_delay_default_on_unparseable_header():
    exc = _status_error(
        {"error": {"code": "rate_limit_exceeded", "type": "tokens"}},
        headers={"retry-after": "Wed, 21 Oct 2099 07:28:00 GMT"})
    assert _transient_tpm_delay(exc, default=60.0) == 60.0


class _FlakyCompletions:
    """Raises queued exceptions in order, then returns `resp` for every later call."""

    def __init__(self, raises, resp):
        self._raises = list(raises)
        self._resp = resp
        self.calls = 0

    async def create(self, **kwargs):
        self.calls += 1
        if self._raises:
            exc = self._raises.pop(0)
            if exc is not None:
                raise exc
        return self._resp


def _install_flaky(client, raises, resp):
    comp = _FlakyCompletions(raises, resp)
    client._client = SimpleNamespace(chat=SimpleNamespace(completions=comp))
    return comp


def test_run_turn_retries_transient_tpm_then_succeeds(monkeypatch):
    slept = []

    async def fake_sleep(seconds):
        slept.append(seconds)

    monkeypatch.setattr(llm_client.asyncio, "sleep", fake_sleep)

    client = _make_client()
    tpm = _status_error(
        {"error": {"code": "rate_limit_exceeded", "type": "tokens"}},
        headers={"retry-after": "1"})
    comp = _install_flaky(client, [tpm], _fake_response("ok", None, "stop"))

    result = asyncio.run(client.run_turn("SYS", [], []))
    assert result.text == "ok"
    assert comp.calls == 2          # one failure + one success
    assert slept == [1.0]           # honored retry-after


def test_run_turn_reraises_context_overflow_without_sleeping(monkeypatch):
    slept = []
    monkeypatch.setattr(llm_client.asyncio, "sleep",
                        lambda s: slept.append(s))  # never awaited
    client = _make_client()
    overflow = _status_error({"error": {"code": "context_length_exceeded",
                                        "type": "tokens"}})
    _install_flaky(client, [overflow], _fake_response("never", None, "stop"))

    with pytest.raises(openai.APIStatusError):
        asyncio.run(client.run_turn("SYS", [], []))
    assert slept == []


def test_run_turn_gives_up_after_three_attempts(monkeypatch):
    async def fake_sleep(seconds):
        pass

    monkeypatch.setattr(llm_client.asyncio, "sleep", fake_sleep)
    client = _make_client()
    tpm = _status_error({"error": {"code": "rate_limit_exceeded", "type": "tokens"}})
    comp = _install_flaky(client, [tpm, tpm, tpm], _fake_response("x", None, "stop"))

    with pytest.raises(openai.APIStatusError):
        asyncio.run(client.run_turn("SYS", [], []))
    assert comp.calls == 3          # capped at 3 attempts


# ---------------------------------------------------------------------------
# The text path must not move a byte.
#
# llm_client carries every VLM authoring turn (`gated_pipeline` calls
# `run_turn`). The image work below is additive, but "additive" is a claim,
# not a fact, so the text-only request body is pinned literally: both as the
# exact kwargs dict and as a hash of its canonical serialisation. If either
# fails, the request body changed -- which is only ever discovered on a paid
# run otherwise.
# ---------------------------------------------------------------------------

import hashlib
import json

#: sha256 of json.dumps(kwargs, sort_keys=True) for the text-only turn built
#: below. NOT taken from the post-change code and asserted to match itself:
#: the same payload was built against `git show HEAD:mcp_harness/llm_client.py`
#: (commit 29dbb5a, before any of this slice's edits) and against the modified
#: file, and both printed this hash. The text path is unmoved by construction
#: -- run_turn's body is untouched -- and by measurement.
_TEXT_ONLY_PAYLOAD_SHA256 = (
    "59abeaa1ed407fb637514acc86e09579d86a89b22d44b9498a4d3b0f0caedfc9")


def _text_only_kwargs():
    """The kwargs run_turn hands the SDK for a representative text-only turn."""
    cfg = LLMConfig(provider="claude", model="claude-sonnet-4-6",
                    base_url="https://api.anthropic.com/v1/", api_key="k")
    client = LLMClient(cfg)
    fake = _install_fake(client, _fake_response("ok", None, "stop"))
    tools = tools_to_openai([SimpleNamespace(
        name="add_node", description="Add a node",
        inputSchema={"type": "object",
                     "properties": {"id": {"type": "integer"}}})])
    asyncio.run(client.run_turn(
        "SYSTEM PROMPT",
        [{"role": "user", "content": "design a dog"},
         {"role": "assistant", "content": "on it"}],
        tools))
    return fake.last_kwargs


def test_text_only_request_payload_is_byte_identical():
    kwargs = _text_only_kwargs()
    assert kwargs == {
        "model": "claude-sonnet-4-6",
        "messages": [
            {"role": "system", "content": "SYSTEM PROMPT"},
            {"role": "user", "content": "design a dog"},
            {"role": "assistant", "content": "on it"},
        ],
        "tools": [{
            "type": "function",
            "function": {
                "name": "add_node",
                "description": "Add a node",
                "parameters": {"type": "object",
                               "properties": {"id": {"type": "integer"}}},
            },
        }],
        "tool_choice": "required",
        "max_tokens": 4096,
    }


def test_text_only_request_payload_hash_is_frozen():
    blob = json.dumps(_text_only_kwargs(), sort_keys=True).encode()
    assert hashlib.sha256(blob).hexdigest() == _TEXT_ONLY_PAYLOAD_SHA256


def test_text_only_content_is_still_a_bare_string_not_parts():
    # The whole risk of content-parts support is a helper leaking into the text
    # path and turning every `content` into a list.
    for msg in _text_only_kwargs()["messages"]:
        assert isinstance(msg["content"], str)


# ---------------------------------------------------------------------------
# Image content parts
# ---------------------------------------------------------------------------

import base64
from llm_client import (
    image_data_uri, image_part, sniff_media_type, text_part,
    user_message_with_images,
)

_PNG = b"\x89PNG\r\n\x1a\n" + b"fake png body"
_JPEG = b"\xff\xd8\xff\xe0" + b"fake jpeg body"


def test_sniff_media_type_known_formats():
    assert sniff_media_type(_PNG) == "image/png"
    assert sniff_media_type(_JPEG) == "image/jpeg"
    assert sniff_media_type(b"GIF89a....") == "image/gif"
    assert sniff_media_type(b"GIF87a....") == "image/gif"
    assert sniff_media_type(b"RIFF\x00\x01\x02\x03WEBPvp8 ") == "image/webp"


def test_sniff_media_type_refuses_to_guess():
    with pytest.raises(ValueError, match="unrecognised image format"):
        sniff_media_type(b"not an image at all")
    # RIFF alone is not enough -- a .wav must not be called an image.
    with pytest.raises(ValueError, match="unrecognised image format"):
        sniff_media_type(b"RIFF\x00\x01\x02\x03WAVEfmt ")


def test_image_data_uri_from_bytes_round_trips():
    uri = image_data_uri(_PNG)
    assert uri.startswith("data:image/png;base64,")
    assert base64.b64decode(uri.split(",", 1)[1]) == _PNG


def test_image_data_uri_from_path(tmp_path):
    p = tmp_path / "fig.png"
    p.write_bytes(_PNG)
    # str and Path forms must agree, and both must read the FILE (not encode
    # the path string).
    assert image_data_uri(p) == image_data_uri(str(p)) == image_data_uri(_PNG)


def test_image_data_uri_explicit_media_type_wins():
    assert image_data_uri(_PNG, "image/webp").startswith("data:image/webp;base64,")


def test_image_data_uri_rejects_empty():
    with pytest.raises(ValueError, match="empty image"):
        image_data_uri(b"")


def test_image_part_shape():
    part = image_part(_PNG)
    assert part == {"type": "image_url",
                    "image_url": {"url": image_data_uri(_PNG)}}
    # `detail` is documented as IGNORED by the compat layer; never emit it.
    assert "detail" not in part["image_url"]


def test_text_part_shape():
    assert text_part("hi") == {"type": "text", "text": "hi"}


def test_user_message_with_images_orders_text_first():
    msg = user_message_with_images("how many circles?", [_PNG, _JPEG])
    assert msg["role"] == "user"
    assert [p["type"] for p in msg["content"]] == [
        "text", "image_url", "image_url"]
    assert msg["content"][0]["text"] == "how many circles?"
    assert msg["content"][1]["image_url"]["url"].startswith("data:image/png")
    assert msg["content"][2]["image_url"]["url"].startswith("data:image/jpeg")


def test_user_message_sniffs_each_image_and_takes_no_media_type_override():
    """A broadcast media_type would label a JPEG as a PNG. There isn't one."""
    import inspect
    assert "media_type" not in inspect.signature(
        user_message_with_images).parameters
    msg = user_message_with_images("q", [_JPEG, _PNG])
    assert msg["content"][1]["image_url"]["url"].startswith("data:image/jpeg")
    assert msg["content"][2]["image_url"]["url"].startswith("data:image/png")


def test_user_message_with_no_images_is_still_a_parts_list():
    msg = user_message_with_images("plain", [])
    assert msg == {"role": "user", "content": [{"type": "text", "text": "plain"}]}


def test_user_message_rejects_a_bare_image():
    # bytes/str are iterable; silently iterating one would produce a message
    # with one content part per BYTE.
    with pytest.raises(TypeError, match="SEQUENCE"):
        user_message_with_images("x", _PNG)
    with pytest.raises(TypeError, match="SEQUENCE"):
        user_message_with_images("x", "/path/to/fig.png")


def test_run_turn_forwards_image_parts_verbatim():
    """The point of the additive design: run_turn needs no image awareness."""
    client = _make_client()
    fake = _install_fake(client, _fake_response("three", None, "stop"))
    msg = user_message_with_images("how many circles?", [_PNG])
    result = asyncio.run(client.run_turn("SYS", [msg], []))
    assert result.text == "three"
    sent = fake.last_kwargs["messages"]
    assert sent[0] == {"role": "system", "content": "SYS"}
    assert sent[1] is msg            # forwarded, not rebuilt
    assert sent[1]["content"][1]["image_url"]["url"].startswith(
        "data:image/png;base64,")


@pytest.mark.parametrize("model", ["claude-opus-5-5", "claude-sonnet-5-5", "claude-fable-5-1",
                                   "claude-mythos-5-1"])
def test_models_that_refuse_forced_tool_use_get_auto(model):
    """Measured 2026-10-16 on api.anthropic.com/v1/: claude-opus-5-5 and
    claude-fable-5-1 answer 400 'tool_choice: type "tool" and "any" are not
    supported for this model' to "required". They get "auto"; callers already
    repair a prose answer (subject_rewrite, concept_ab.judge)."""
    client = _make_client()
    client.model = model
    fake = _install_fake(client, _fake_response("x", None, "stop"))
    asyncio.run(client.run_turn("S", [{"role": "user", "content": "hi"}], _A_TOOL))
    assert fake.last_kwargs["tool_choice"] == "auto"


@pytest.mark.parametrize("model", ["claude-haiku-5-5", "claude-sonnet-5", "m"])
def test_other_models_keep_required(model):
    client = _make_client()
    client.model = model
    fake = _install_fake(client, _fake_response("x", None, "stop"))
    asyncio.run(client.run_turn("S", [{"role": "user", "content": "hi"}], _A_TOOL))
    assert fake.last_kwargs["tool_choice"] == "required"
