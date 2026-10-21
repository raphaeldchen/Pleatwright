"""hf2 with Nano Banana 2.1 as the image stage (spec 2026-10-19-nano-banana-image-stage-design.md).

Offline: Gemini is an injected `image_fn`, the Hunyuan Space the same fake
client test_two_stage_provider.py uses.
"""
import json
import os

import pytest

import gemini_image
import mesh_acquire
from test_two_stage_provider import _factory, _file_arg

MODEL = "gemini-nano-banana-2.1"
JPEG = b"\xff\xd8\xff\xe0" + b"j" * 32
PNG = b"\x89PNG\r\n\x1a\n" + b"p" * 32
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"w" * 32


def _gerr(status, message="", details=None, err_status=""):
    body = {"error": {"code": status, "message": message, "status": err_status,
                      "details": details or []}}
    return gemini_image.GeminiImageError(f"Gemini {MODEL} answered HTTP {status}: {message}",
                                         status=status, body=body)


def _image_fn(log, data=JPEG, errors=()):
    pending = list(errors)

    def draw(prompt, out_path, *, model, seed):
        if pending:
            raise pending.pop(0)
        with open(out_path, "wb") as f:
            f.write(data)
        log.append((prompt, out_path, model, seed))
        return gemini_image.GeminiImage(path=out_path, model=model, seed=seed,
                                        mime_type="image/jpeg", usage={}, finish_reason="STOP")
    return draw


@pytest.fixture()
def glb(tmp_path):
    path = tmp_path / "out.glb"
    path.write_bytes(b"glTF\x02\x00\x00\x00" + b"\x00" * 64)
    return str(path)


def _gem(log, mlog, glb, *, data=JPEG, errors=(), sleeps=None, results=None, **kw):
    results = results if results is not None else {"mesh/space": glb}
    return mesh_acquire.TwoStageProvider(
        mesh_space="mesh/space", mesh_api="/shape_generation",
        mesh_kwargs=dict(mesh_acquire.HUNYUAN_SHAPE_KWARGS),
        prompt_template=mesh_acquire.CONCEPT_PROMPT_TEMPLATE, image_model=MODEL,
        client_factory=_factory(results, mlog),
        sleep=(sleeps.append if sleeps is not None else (lambda _s: None)),
        image_fn=_image_fn(log, data, errors), **kw)


def _concepts(d):
    return sorted(n for n in os.listdir(d) if n.startswith("concept"))


# ---- the draw and the lift ------------------------------------------------------

def test_gemini_draws_the_shipped_template_and_hunyuan_lifts_it_unchanged(tmp_path, glb):
    log, mlog = [], []
    out = _gem(log, mlog, glb, image_seed=4242).generate("a scorpion", str(tmp_path / "k"))
    assert log[0][0] == mesh_acquire.concept_prompt("a scorpion")
    assert log[0][2:] == (MODEL, 4242)
    assert out == str(tmp_path / "k" / "mesh.glb")
    [call] = mlog
    assert call["space"] == "mesh/space" and call["api_name"] == "/shape_generation"
    sent = call["args"]
    assert sent[0] is None                                     # caption
    assert sent[1] == _file_arg(str(tmp_path / "k" / "concept.jpg"))  # image, slot 2
    assert sent[2:] == tuple(v for k, v in mesh_acquire.HUNYUAN_SHAPE_KWARGS.items()
                             if k not in ("caption", "image"))  # seed 1234 survives


def test_a_description_fills_the_template_subject(tmp_path, glb):
    log = []
    _gem(log, [], glb, subject_description="desert scorpion, tail curled").generate(
        "a scorpion", str(tmp_path / "k"))
    assert log[0][0] == mesh_acquire.concept_prompt("desert scorpion, tail curled")


@pytest.mark.parametrize("data, name", [(JPEG, "concept.jpg"), (PNG, "concept.png"),
                                        (WEBP, "concept.webp")])
def test_the_concept_is_named_by_its_bytes(tmp_path, glb, data, name):
    _gem([], [], glb, data=data).generate("a scorpion", str(tmp_path / "k"))
    assert _concepts(tmp_path / "k") == [name]


def test_bytes_that_are_no_known_image_fail_the_image_stage(tmp_path, glb):
    mlog = []
    with pytest.raises(RuntimeError, match=r"^image stage: .*not JPEG, PNG or WEBP"):
        _gem([], mlog, glb, data=b"<html>nope</html>").generate("a scorpion", str(tmp_path / "k"))
    assert mlog == [] and _concepts(tmp_path / "k") == []
    assert not any(n.endswith(".part") for n in os.listdir(tmp_path / "k"))


def test_a_new_concept_replaces_any_other_concept_file(tmp_path, glb):
    k = tmp_path / "k"
    k.mkdir()
    (k / "concept.png").write_bytes(PNG)                      # an older FLUX draw
    _gem([], [], glb).generate("a scorpion", str(k))
    assert _concepts(k) == ["concept.jpg"]


def test_progress_reports_the_jpeg_concept(tmp_path, glb):
    seen = []
    _gem([], [], glb).generate("a scorpion", str(tmp_path / "k"),
                               progress=lambda kind, p: seen.append((kind, p)))
    assert seen == [("image", str(tmp_path / "k" / "concept.jpg"))]


def test_a_lift_retry_reuses_the_drawn_concept(tmp_path, glb):
    log, results = [], {"mesh/space": RuntimeError("Connection refused")}
    p = _gem(log, [], glb, results=results, reuse_concept=True)
    with pytest.raises(RuntimeError, match=r"^mesh stage:"):
        p.generate("a scorpion", str(tmp_path / "k"))
    results["mesh/space"] = glb
    assert p.generate("a scorpion", str(tmp_path / "k")).endswith("mesh.glb")
    assert len(log) == 1                                      # one picture bought, not two


# ---- errors ---------------------------------------------------------------------

FREE_429 = dict(message="Quota exceeded for metric: generativelanguage.googleapis.com/"
                "generate_content_free_tier_requests, limit: 0, model: gemini-nano-banana-2.1. "
                "Please retry in 11.89s.", err_status="RESOURCE_EXHAUSTED")


def test_no_quota_fails_at_once_with_the_spec_message(tmp_path, glb):
    sleeps, mlog = [], []
    with pytest.raises(RuntimeError) as ei:
        _gem([], mlog, glb, sleeps=sleeps, errors=[_gerr(429, **FREE_429)]).generate(
            "a scorpion", str(tmp_path / "k"))
    assert str(ei.value).startswith(mesh_acquire.GEMINI_NO_QUOTA.format(model=MODEL))
    assert str(ei.value).startswith(
        "image stage: Gemini gemini-nano-banana-2.1 has no image quota on this API key. "
        "The free tier's image quota is 0. Enable billing for the key's Google Cloud "
        "project (about $0.042 an image), or set MESH_IMAGE_BACKEND=flux to draw with "
        "FLUX on HuggingFace.")
    assert sleeps == [] and mlog == []


def test_the_no_quota_message_keeps_geminis_own_words(tmp_path, glb):
    """Review finding: a region-blocked key is a 400 FAILED_PRECONDITION too, and
    "enable billing" will not fix it -- the user must see what Gemini said."""
    err = _gerr(400, "User location is not supported for the API use.",
                err_status="FAILED_PRECONDITION")
    with pytest.raises(RuntimeError) as ei:
        _gem([], [], glb, errors=[err]).generate("a scorpion", str(tmp_path / "k"))
    assert str(ei.value) == (mesh_acquire.GEMINI_NO_QUOTA.format(model=MODEL)
                             + f" ({err})")
    assert "User location is not supported" in str(ei.value)


def test_transient_errors_are_retried_then_named(tmp_path, glb):
    sleeps = []
    with pytest.raises(RuntimeError,
                       match=r"^image stage: Gemini gemini-nano-banana-2\.1 failed after 3 attempts"):
        _gem([], [], glb, sleeps=sleeps, errors=[_gerr(503, "busy")] * 3).generate(
            "a scorpion", str(tmp_path / "k"))
    assert sleeps == [10.0, 30.0]


def test_a_transient_error_then_success_draws_once(tmp_path, glb):
    log, sleeps = [], []
    out = _gem(log, [], glb, sleeps=sleeps, errors=[_gerr(503, "busy")]).generate(
        "a scorpion", str(tmp_path / "k"))
    assert out.endswith("mesh.glb") and len(log) == 1 and sleeps == [10.0]


def test_a_client_error_is_not_retried(tmp_path, glb):
    sleeps = []
    with pytest.raises(RuntimeError, match=r"^image stage: .*API key not valid"):
        _gem([], [], glb, sleeps=sleeps,
             errors=[_gerr(400, "API key not valid.", err_status="INVALID_ARGUMENT")]).generate(
            "a scorpion", str(tmp_path / "k"))
    assert sleeps == []


# ---- the cache key --------------------------------------------------------------

def test_gemini_cache_settings_shape(glb):
    s = _gem([], [], glb).cache_settings
    assert s["image_backend"] == "gemini" and s["image_model"] == MODEL and s["image_seed"] is None
    assert "image_space" not in s and "image_kwargs" not in s
    assert s["prompt_template"] == mesh_acquire.CONCEPT_PROMPT_TEMPLATE
    assert s["mesh_kwargs"]["seed"] == 1234 and s["mesh_kwargs"]["image"] == "<stage input>"
    assert "subject_description" not in s
    json.dumps(s)


def test_the_image_model_and_seed_move_the_key(glb):
    def key(**kw):
        p = _gem([], [], glb, **kw)
        return mesh_acquire.cache_key("hf2", "a scorpion", p.cache_settings)
    a = key()
    p_other = _gem([], [], glb)
    p_other.image_model = "gemini-other"
    assert len({a, key(image_seed=7), key(subject_description="x"),
                mesh_acquire.cache_key("hf2", "a scorpion", p_other.cache_settings)}) == 4


def test_hunyuan_needs_rembg_for_a_jpeg_concept():
    """A JPEG has no alpha. Hunyuan3D-2 runs rembg only when check_box_rembg is
    set or the image is RGB, and its gradio input makes every upload RGBA
    (gradio_app.py, hy3dgen/rembg.py), so this flag is load-bearing for Gemini
    concepts."""
    assert mesh_acquire.HUNYUAN_SHAPE_KWARGS["check_box_rembg"] is True


# ---- get_provider("hf2") picks the backend (spec §1) ------------------------------

_HF_ENV = ("HF_IMAGE_SPACE_ID", "HF_MESH_SPACE_ID", "HF_IMAGE_API", "HF_MESH_API")


def _env(monkeypatch, backend=None, key=None):
    for v in _HF_ENV:
        monkeypatch.delenv(v, raising=False)
    for name, value in (("MESH_IMAGE_BACKEND", backend), ("GEMINI_API_KEY", key)):
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)


@pytest.mark.parametrize("backend, key, expect", [
    (None, "k", "gemini"), ("auto", "k", "gemini"), ("", "k", "gemini"),
    (None, None, "flux"), (None, "", "flux"), ("auto", None, "flux"),
    ("flux", "k", "flux"), ("gemini", "k", "gemini"),
])
def test_the_selection_table(monkeypatch, backend, key, expect):
    _env(monkeypatch, backend, key)
    assert mesh_acquire.hf2_image_backend() == expect
    assert (mesh_acquire.get_provider("hf2").image_model is not None) == (expect == "gemini")


def test_gemini_without_a_key_is_a_value_error(monkeypatch):
    _env(monkeypatch, "gemini", None)
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        mesh_acquire.get_provider("hf2")


def test_an_unknown_backend_names_the_valid_values(monkeypatch):
    _env(monkeypatch, "dalle", "k")
    with pytest.raises(ValueError) as ei:
        mesh_acquire.get_provider("hf2")
    assert all(v in str(ei.value) for v in ("auto", "gemini", "flux", "dalle"))


def test_backend_value_is_case_and_space_insensitive(monkeypatch):
    _env(monkeypatch, " Gemini ", "k")
    assert mesh_acquire.hf2_image_backend() == "gemini"
    _env(monkeypatch, "FLUX", "k")
    assert mesh_acquire.hf2_image_backend() == "flux"


def test_flux_is_unchanged_even_with_a_key_when_forced(monkeypatch):
    _env(monkeypatch, "flux", "k")
    p = mesh_acquire.get_provider("hf2")
    assert mesh_acquire.cache_key("hf2", "moose", p.cache_settings) == "moose-0ea544523bcf6966"
    seeded = mesh_acquire.get_provider("hf2", seed=48213)
    assert seeded.image_kwargs["seed"] == seeded.mesh_kwargs["seed"] == 48213
    assert seeded.reuse_concept is False


def test_the_gemini_provider_is_wired_as_designed(monkeypatch):
    _env(monkeypatch, None, "k")
    p = mesh_acquire.get_provider("hf2")
    assert p.image_model == MODEL and p.image_seed is None and p.reuse_concept is True
    assert p.prompt_template == mesh_acquire.CONCEPT_PROMPT_TEMPLATE
    assert p.mesh_kwargs == mesh_acquire.HUNYUAN_SHAPE_KWARGS
    assert (p.mesh_space, p.mesh_api) == (mesh_acquire.DEFAULT_HF_MESH_SPACE,
                                          mesh_acquire.DEFAULT_HF_MESH_API)
    d = mesh_acquire.get_provider("hf2", seed=48213, description="bull scorpion")
    assert d.image_seed == 48213 and d.mesh_kwargs["seed"] == 1234
    assert d.subject_description == "bull scorpion"


def test_a_redirected_mesh_space_drops_hunyuans_layout_on_gemini_too(monkeypatch):
    _env(monkeypatch, None, "k")
    monkeypatch.setenv("HF_MESH_SPACE_ID", "someone/else")
    p = mesh_acquire.get_provider("hf2")
    assert p.mesh_space == "someone/else" and p.mesh_kwargs == {}


def test_gemini_image_model_env_overrides_the_model(monkeypatch):
    _env(monkeypatch, None, "k")
    monkeypatch.setenv("GEMINI_IMAGE_MODEL", "gemini-nano-banana-pro")
    assert mesh_acquire.get_provider("hf2").image_model == "gemini-nano-banana-pro"


def test_flux_and_gemini_default_keys_differ_for_every_subject(monkeypatch):
    from artifact_trees import ROLLS
    subjects = sorted({r.rsplit("_", 1)[0].replace("_", " ") for r in ROLLS})
    assert len(subjects) == 17
    _env(monkeypatch, "flux", "k")
    flux = mesh_acquire.get_provider("hf2").cache_settings
    _env(monkeypatch, "gemini", "k")
    gem = mesh_acquire.get_provider("hf2").cache_settings
    for s in subjects:
        assert mesh_acquire.cache_key("hf2", s, flux) != mesh_acquire.cache_key("hf2", s, gem)


def test_draws_reproduce(monkeypatch):
    _env(monkeypatch, None, "k")
    assert mesh_acquire.draws_reproduce("fake") is True
    assert mesh_acquire.draws_reproduce("hf2") is False
    monkeypatch.setenv("MESH_PROVIDER", "hf2")
    assert mesh_acquire.draws_reproduce() is False
    _env(monkeypatch, "flux", "k")
    assert mesh_acquire.draws_reproduce("hf2") is True
    _env(monkeypatch, "dalle", "k")
    assert mesh_acquire.draws_reproduce("hf2") is True          # get_provider raises later


def _meta(d, settings):
    d.mkdir()
    (d / "meta.json").write_text(json.dumps({"settings": settings}))
    return str(d)


def test_image_model_label(monkeypatch, tmp_path):
    _env(monkeypatch, None, "k")
    assert mesh_acquire.image_model_label("hf2") == MODEL
    assert mesh_acquire.image_model_label("fake") is None
    _env(monkeypatch, "flux", "k")
    assert mesh_acquire.image_model_label("hf2") == mesh_acquire.DEFAULT_HF_IMAGE_SPACE
    _env(monkeypatch, "dalle", "k")
    assert mesh_acquire.image_model_label("hf2") is None        # never raises
    assert mesh_acquire.image_model_label("hf2", _meta(tmp_path / "a", {"image_model": "m"})) == "m"
    assert mesh_acquire.image_model_label("hf2", _meta(tmp_path / "b", {"image_space": "s"})) == "s"
    assert mesh_acquire.image_model_label("hf2", _meta(tmp_path / "c", {"glb_sha256": "x"})) is None
    (tmp_path / "d").mkdir()
    assert mesh_acquire.image_model_label("hf2", str(tmp_path / "d")) is None
