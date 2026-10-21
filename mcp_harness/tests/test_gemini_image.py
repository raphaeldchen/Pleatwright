"""The Gemini (Nano Banana) concept-image client (spec 2026-10-16 §1)."""
import base64
import json

import httpx
import pytest

import gemini_image as GI

PNG = b"\x89PNG\r\n\x1a\n" + b"x" * 20


def _ok(png=PNG, usage=None):
    return {"candidates": [{"finishReason": "STOP", "content": {"parts": [
        {"inlineData": {"mimeType": "image/png", "data": base64.b64encode(png).decode()}}]}}],
        "usageMetadata": usage or {"candidatesTokenCount": 1290}}


def test_writes_decoded_image_and_returns_usage(tmp_path):
    seen = {}

    def handler(req):
        seen["url"] = str(req.url)
        seen["key"] = req.headers["x-goog-api-key"]
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json=_ok())

    r = GI.generate_image("a scorpion", str(tmp_path / "c.png"), seed=11, api_key="k",
                          transport=httpx.MockTransport(handler))
    assert open(r.path, "rb").read() == PNG
    assert r.usage == {"candidatesTokenCount": 1290} and r.finish_reason == "STOP"
    assert r.mime_type == "image/png" and r.model == "gemini-nano-banana-2.1" and r.seed == 11
    assert seen["url"].endswith("/models/gemini-nano-banana-2.1:generateContent")
    assert seen["key"] == "k"
    assert seen["body"]["contents"][0]["parts"][0]["text"] == "a scorpion"
    assert seen["body"]["generationConfig"]["seed"] == 11
    assert seen["body"]["generationConfig"]["responseModalities"] == ["IMAGE"]


def test_seed_none_is_omitted(tmp_path):
    seen = {}

    def handler(req):
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json=_ok())

    r = GI.generate_image("x", str(tmp_path / "c.png"), api_key="k",
                          transport=httpx.MockTransport(handler))
    assert "seed" not in seen["body"]["generationConfig"] and r.seed is None


def test_no_image_part_raises_with_reason(tmp_path):
    body = {"candidates": [{"finishReason": "IMAGE_SAFETY",
                            "content": {"parts": [{"text": "cannot"}]}}]}
    with pytest.raises(GI.GeminiImageError, match="IMAGE_SAFETY.*cannot"):
        GI.generate_image("x", str(tmp_path / "c.png"), api_key="k",
                          transport=httpx.MockTransport(lambda r: httpx.Response(200, json=body)))
    assert not (tmp_path / "c.png").exists()


def test_http_error_names_status_and_message(tmp_path):
    body = {"error": {"code": 400, "message": "bad field"}}
    with pytest.raises(GI.GeminiImageError, match="400.*bad field"):
        GI.generate_image("x", str(tmp_path / "c.png"), api_key="k",
                          transport=httpx.MockTransport(lambda r: httpx.Response(400, json=body)))
    assert not (tmp_path / "c.png").exists()


def test_missing_key_raises_before_request(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    calls = []

    def handler(req):
        calls.append(req)
        return httpx.Response(200, json=_ok())

    with pytest.raises(GI.GeminiImageError, match="GEMINI_API_KEY"):
        GI.generate_image("x", str(tmp_path / "c.png"), transport=httpx.MockTransport(handler))
    assert calls == []


# ---- error classification (spec 2026-10-19 §5) --------------------------------
# Bodies modelled on the 429s people have pasted (gemini-cli #8437, the Google
# forum's image-429 thread): a free-tier image 429 says "limit: 0" AND carries a
# RetryInfo delay that waiting will never honour.

def _err(status, message="", details=None, err_status=""):
    return {"error": {"code": status, "message": message, "status": err_status,
                      "details": details or []}}


FREE_429 = _err(
    429, "Quota exceeded for metric: generativelanguage.googleapis.com/"
    "generate_content_free_tier_requests, limit: 0, model: gemini-nano-banana-2.1. "
    "Please retry in 11.89s.", err_status="RESOURCE_EXHAUSTED",
    details=[{"@type": "type.googleapis.com/google.rpc.QuotaFailure", "violations": [
        {"quotaMetric": "generativelanguage.googleapis.com/generate_content_free_tier_requests",
         "quotaId": "GenerateRequestsPerMinutePerProjectPerModel-FreeTier"}]},
             {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "11s"}])
RATE_429 = _err(429, "Resource has been exhausted (e.g. check quota).",
                err_status="RESOURCE_EXHAUSTED")


def _fail(status, body, tmp_path):
    t = httpx.MockTransport(lambda req: httpx.Response(status, json=body))
    with pytest.raises(GI.GeminiImageError) as ei:
        GI.generate_image("x", str(tmp_path / "c.jpg"), api_key="k", transport=t)
    return ei.value


def test_an_http_error_carries_its_status_and_body(tmp_path):
    e = _fail(429, FREE_429, tmp_path)
    assert e.status == 429 and e.body == FREE_429


@pytest.mark.parametrize("status, body", [
    (429, FREE_429),
    (429, _err(429, "x", details=[{"@type": "type.googleapis.com/google.rpc.QuotaFailure",
                                   "violations": [{"quotaValue": "0"}]}])),
    (429, _err(429, "Your prepayment credits are depleted.")),
    (402, _err(402, "payment required")),
    (400, _err(400, "billing not enabled", err_status="FAILED_PRECONDITION")),
])
def test_no_image_quota_is_recognised_and_not_transient(tmp_path, status, body):
    e = _fail(status, body, tmp_path)
    assert GI.no_image_quota(e) and not GI.is_transient(e)


@pytest.mark.parametrize("status", [408, 500, 502, 503, 504])
def test_server_errors_are_transient(tmp_path, status):
    e = _fail(status, _err(status, "boom"), tmp_path)
    assert GI.is_transient(e) and not GI.no_image_quota(e)


def test_a_plain_rate_limit_is_transient(tmp_path):
    e = _fail(429, RATE_429, tmp_path)
    assert GI.is_transient(e) and not GI.no_image_quota(e)


def test_a_limit_of_ten_is_not_a_limit_of_zero(tmp_path):
    e = _fail(429, _err(429, "Quota exceeded ..., limit: 10, model: m"), tmp_path)
    assert GI.is_transient(e) and not GI.no_image_quota(e)


@pytest.mark.parametrize("status, body", [
    (400, _err(400, "API key not valid.", err_status="INVALID_ARGUMENT")),
    (403, _err(403, "denied", err_status="PERMISSION_DENIED")),
])
def test_client_errors_are_neither(tmp_path, status, body):
    e = _fail(status, body, tmp_path)
    assert not GI.is_transient(e) and not GI.no_image_quota(e)


def test_a_transport_failure_is_transient_with_no_status(tmp_path):
    def boom(req):
        raise httpx.ConnectError("down")
    with pytest.raises(GI.GeminiImageError) as ei:
        GI.generate_image("x", str(tmp_path / "c.jpg"), api_key="k",
                          transport=httpx.MockTransport(boom))
    assert ei.value.status is None and GI.is_transient(ei.value)


def test_an_answer_without_an_image_is_status_200_and_not_transient(tmp_path):
    body = {"candidates": [{"finishReason": "IMAGE_SAFETY", "content": {"parts": []}}]}
    e = _fail(200, body, tmp_path)
    assert e.status == 200 and not GI.is_transient(e) and not GI.no_image_quota(e)


def test_a_non_json_error_body_is_none(tmp_path):
    t = httpx.MockTransport(lambda req: httpx.Response(503, text="<html>down</html>"))
    with pytest.raises(GI.GeminiImageError) as ei:
        GI.generate_image("x", str(tmp_path / "c.jpg"), api_key="k", transport=t)
    assert ei.value.status == 503 and ei.value.body is None and GI.is_transient(ei.value)


@pytest.mark.parametrize("respond", [
    lambda req: httpx.Response(200, text="<html>not json</html>"),
    lambda req: httpx.Response(200, json=["not", "an", "object"]),
    lambda req: httpx.Response(200, json={"candidates": ["x"]}),
    lambda req: httpx.Response(200, json={"candidates": [{"content": {"parts": [{"inlineData": {}}]}}]}),
    lambda req: httpx.Response(200, json={"candidates": [{"content": {"parts": [
        {"inlineData": {"data": "!!not base64!!"}}]}}]}),
])
def test_a_malformed_answer_is_a_gemini_error(tmp_path, respond):
    """Review finding: an odd 200 must not escape as KeyError/TypeError, which the
    app does not catch -- no failed stage, no retry button."""
    with pytest.raises(GI.GeminiImageError) as ei:
        GI.generate_image("x", str(tmp_path / "c.jpg"), api_key="k",
                          transport=httpx.MockTransport(respond))
    assert ei.value.status == 200 and not GI.is_transient(ei.value)
    assert not (tmp_path / "c.jpg").exists()
