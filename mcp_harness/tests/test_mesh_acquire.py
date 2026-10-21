import os

import pytest

import mesh_acquire as ma

# Captured at IMPORT time, before the autouse fixture below clears it: pytest
# imports conftest.py before any test module, so this is what the suite session
# was configured with.
_SESSION_PROVENANCE_ENV = os.environ.get("IDE_MESH_PROVENANCE")


@pytest.fixture(autouse=True)
def _provenance_enabled_for_this_module(monkeypatch):
    """conftest.py disables sidecar writing for the SUITE, so a test run never
    mutates a cache directory that may be a symlink into another checkout.

    This module is the one place where writing the sidecar IS the subject, so
    the production default is restored here. That is what keeps the suite-wide
    opt-out free of coverage cost: every write path is still exercised, just
    only by the tests that are actually about it.
    """
    monkeypatch.delenv("IDE_MESH_PROVENANCE", raising=False)


def test_fake_provider_writes_glb_into_out_dir(tmp_path):
    provider = ma.FakeMeshProvider()
    out = provider.generate("a quadruped", str(tmp_path))
    assert os.path.isfile(out)
    assert out.endswith(".glb")
    assert os.path.dirname(out) == str(tmp_path)
    assert os.path.getsize(out) > 0


def test_fake_provider_returns_absolute_path_for_relative_out_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    provider = ma.FakeMeshProvider()
    out = provider.generate("a quadruped", "relsub")
    assert os.path.isabs(out)
    assert os.path.isfile(out)


def test_get_provider_fake_selected_by_env(monkeypatch):
    monkeypatch.setenv("MESH_PROVIDER", "fake")
    assert isinstance(ma.get_provider(), ma.FakeMeshProvider)


def test_get_provider_defaults_to_fake_when_env_unset(monkeypatch):
    # C-8: unset MESH_PROVIDER must resolve to the offline 'fake' provider (no
    # spend) — not the paid 'meshy'.
    monkeypatch.delenv("MESH_PROVIDER", raising=False)
    assert isinstance(ma.get_provider(), ma.FakeMeshProvider)


def test_get_provider_unknown_raises(monkeypatch):
    monkeypatch.setenv("MESH_PROVIDER", "nope")
    with pytest.raises(ValueError, match="unknown MESH_PROVIDER"):
        ma.get_provider()


def test_get_provider_meshy_requires_key(monkeypatch):
    monkeypatch.delenv("MESHY_API_KEY", raising=False)
    with pytest.raises(ValueError, match="MESHY_API_KEY"):
        ma.get_provider("meshy")


def test_cache_key_is_stable_and_prompt_sensitive():
    a = ma.cache_key("meshy", "a fox")
    assert a == ma.cache_key("meshy", "a fox")
    assert a != ma.cache_key("meshy", "a dog")
    assert a != ma.cache_key("fake", "a fox")


class _CountingProvider:
    def __init__(self, fixture):
        self.fixture = fixture
        self.calls = 0

    def generate(self, prompt, out_dir):
        import os, shutil
        self.calls += 1
        os.makedirs(out_dir, exist_ok=True)
        dest = os.path.join(out_dir, "mesh.glb")
        shutil.copyfile(self.fixture, dest)
        return dest


def test_acquire_mesh_caches_by_prompt(tmp_path):
    prov = _CountingProvider(ma.fake_mesh_path())
    p1 = ma.acquire_mesh("a quadruped", provider=prov,
                         provider_name="fake", cache_dir=str(tmp_path))
    p2 = ma.acquire_mesh("a quadruped", provider=prov,
                         provider_name="fake", cache_dir=str(tmp_path))
    assert p1 == p2
    assert prov.calls == 1  # second call served from cache
    assert os.path.isfile(p1)


def test_acquire_mesh_distinct_injected_providers_dont_collide(tmp_path):
    # two different injected provider classes, no provider_name -> distinct cache keys
    class _PA(ma.FakeMeshProvider):
        pass
    class _PB(ma.FakeMeshProvider):
        pass
    p_a = ma.acquire_mesh("x", provider=_PA(), cache_dir=str(tmp_path))
    p_b = ma.acquire_mesh("x", provider=_PB(), cache_dir=str(tmp_path))
    assert os.path.dirname(p_a) != os.path.dirname(p_b)


def test_acquire_mesh_env_unset_defaults_to_fake(monkeypatch, tmp_path):
    # Unified with get_provider (C-8 no-spend): env unset + no provider args
    # must resolve the offline 'fake' provider, NOT the stale 'meshy' fallback
    # (which used to error on a missing MESHY_API_KEY before doing anything).
    monkeypatch.delenv("MESH_PROVIDER", raising=False)
    monkeypatch.delenv("MESHY_API_KEY", raising=False)
    path = ma.acquire_mesh("a quadruped", cache_dir=str(tmp_path))
    assert os.path.isfile(path)
    assert os.path.getsize(path) > 0


def test_acquire_mesh_raises_when_provider_returns_missing_file(tmp_path):
    class _BadProvider:
        def generate(self, prompt, out_dir):
            return os.path.join(out_dir, "does_not_exist.glb")
    with pytest.raises(RuntimeError, match="missing or empty"):
        ma.acquire_mesh("x", provider=_BadProvider(), cache_dir=str(tmp_path))


class _FakeHttp:
    """Scripted Meshy transport. `statuses` is the sequence returned by polling."""
    def __init__(self, statuses, glb_bytes=b"GLB-DATA"):
        self.statuses = list(statuses)
        self.glb_bytes = glb_bytes
        self.posted = None

    def post_json(self, url, headers, payload):
        self.posted = payload
        return {"result": "task-123"}

    def get_json(self, url, headers):
        return self.statuses.pop(0)

    def download(self, url, dest_path):
        with open(dest_path, "wb") as f:
            f.write(self.glb_bytes)


def test_meshy_provider_success(tmp_path):
    http = _FakeHttp(statuses=[
        {"status": "IN_PROGRESS"},
        {"status": "SUCCEEDED", "model_urls": {"glb": "http://x/m.glb"}},
    ])
    prov = ma.MeshyProvider("key", poll_interval=0, http=http, sleep=lambda s: None)
    out = prov.generate("a fox", str(tmp_path))
    assert os.path.isfile(out) and os.path.getsize(out) > 0
    assert http.posted["prompt"] == "a fox"


def test_meshy_provider_failed_status_raises(tmp_path):
    http = _FakeHttp(statuses=[{"status": "FAILED", "task_error": {"message": "bad"}}])
    prov = ma.MeshyProvider("key", poll_interval=0, http=http, sleep=lambda s: None)
    with pytest.raises(RuntimeError, match="bad"):
        prov.generate("a fox", str(tmp_path))


def test_meshy_provider_timeout_raises(tmp_path):
    http = _FakeHttp(statuses=[{"status": "IN_PROGRESS"}] * 5)
    prov = ma.MeshyProvider("key", poll_interval=0, timeout=0,
                            http=http, sleep=lambda s: None)
    with pytest.raises(TimeoutError, match="task-123"):
        prov.generate("a fox", str(tmp_path))


def test_meshy_provider_empty_download_raises(tmp_path):
    http = _FakeHttp(statuses=[
        {"status": "SUCCEEDED", "model_urls": {"glb": "http://x/m.glb"}},
    ], glb_bytes=b"")
    prov = ma.MeshyProvider("key", poll_interval=0, http=http, sleep=lambda s: None)
    with pytest.raises(RuntimeError, match="empty"):
        prov.generate("a fox", str(tmp_path))


@pytest.mark.parametrize("prompt,expected", [
    ("a dog", "dog"),
    ("a guinea pig", "guinea_pig"),
    ("Scorpion with raised tail", "scorpion"),
    ("a giant beetle", "ant"),
    ("a soaring eagle", "bird"),
    ("a rainbow trout", "dolphin"),
    ("a red fox", "dog"),
    ("a standing person", "dog"),
])
def test_fake_mesh_path_maps_prompts(prompt, expected):
    assert ma.fake_mesh_path(prompt) == os.path.join(ma.FAKE_MESH_DIR, expected + ".glb")


def test_every_fake_mesh_subject_and_keyword_target_is_committed():
    subjects = ma.fake_mesh_subjects()
    assert len(subjects) == 17
    for _, target in ma._FAKE_KEYWORDS:
        assert target in subjects
    assert ma.FAKE_MESH_DEFAULT in subjects
    for s in subjects:
        assert ma.fake_mesh_path(s.replace("_", " ")).endswith(f"/{s}.glb")


def test_fake_mesh_loads_as_a_mesh():
    import trimesh
    assert len(trimesh.load(ma.fake_mesh_path("a bat"), force="mesh").faces) > 0


def test_fake_provider_uses_prompt_mapping(tmp_path):
    import filecmp
    out = ma.FakeMeshProvider().generate("a giant beetle", str(tmp_path))
    assert filecmp.cmp(out, ma.fake_mesh_path("an ant"), shallow=False)


def test_fake_provider_explicit_fixture_overrides_mapping(tmp_path):
    import filecmp
    bird = ma.fake_mesh_path("a bird")
    out = ma.FakeMeshProvider(fixture_path=bird).generate("a giant beetle", str(tmp_path))
    assert filecmp.cmp(out, bird, shallow=False)   # explicit path wins over 'beetle'->insect


def test_live_meshy_smoke(tmp_path):
    """Opt-in: only runs when MESHY_API_KEY is set. Validates the real vendor."""
    if not os.environ.get("MESHY_API_KEY"):
        pytest.skip("MESHY_API_KEY not set; skipping live Meshy smoke")
    path = ma.acquire_mesh("a simple fox", provider_name="meshy",
                           cache_dir=str(tmp_path))
    assert os.path.isfile(path) and os.path.getsize(path) > 0


class _FakeGradioClient:
    """Scripted gradio_client.Client stand-in. `result` is what predict returns."""
    def __init__(self, result, raises=False):
        self.result = result
        self.raises = raises
        self.predicted = None

    def predict(self, *args, api_name=None):
        if self.raises:
            raise RuntimeError("space boom")
        self.predicted = (args, api_name)
        return self.result


def _hf_factory(client):
    return lambda space_id, token: client


def test_hf_provider_success(tmp_path):
    client = _FakeGradioClient(result=ma.fake_mesh_path())
    prov = ma.HuggingFaceProvider(client_factory=_hf_factory(client))
    out = prov.generate("a fox", str(tmp_path))
    assert os.path.isfile(out) and os.path.getsize(out) > 0
    assert out == os.path.join(str(tmp_path), "mesh.glb")
    assert client.predicted[0] == ("a fox",)          # prompt passed positionally
    assert client.predicted[1] == ma.DEFAULT_HF_API    # via api_name=


def test_hf_provider_extracts_glb_from_tuple(tmp_path):
    import filecmp
    client = _FakeGradioClient(result=("a text label", ma.fake_mesh_path()))
    prov = ma.HuggingFaceProvider(client_factory=_hf_factory(client))
    out = prov.generate("a fox", str(tmp_path))
    assert filecmp.cmp(out, ma.fake_mesh_path(), shallow=False)


def test_hf_provider_call_failure_raises(tmp_path):
    # sleep injected: the provider now retries transient predict failures with
    # a real-time backoff schedule that would otherwise add ~40s here.
    client = _FakeGradioClient(result=None, raises=True)
    prov = ma.HuggingFaceProvider(client_factory=_hf_factory(client),
                                  sleep=lambda s: None)
    with pytest.raises(RuntimeError, match="space boom"):
        prov.generate("a fox", str(tmp_path))


def test_hf_provider_no_usable_file_raises(tmp_path):
    client = _FakeGradioClient(result="/nope/missing.glb")
    prov = ma.HuggingFaceProvider(client_factory=_hf_factory(client))
    with pytest.raises(RuntimeError, match="no usable glb"):
        prov.generate("a fox", str(tmp_path))


def test_hf_provider_empty_file_raises(tmp_path):
    empty = tmp_path / "empty.glb"
    empty.write_bytes(b"")
    client = _FakeGradioClient(result=str(empty))
    prov = ma.HuggingFaceProvider(client_factory=_hf_factory(client))
    with pytest.raises(RuntimeError, match="no usable glb"):
        prov.generate("a fox", str(tmp_path / "out"))


def test_default_hf_client_factory_passes_token_and_timeout(monkeypatch):
    """The real factory must call gradio_client.Client with the kwarg the
    installed version accepts (`token`, not the removed `hf_token`) plus
    httpx_kwargs carrying a connect-oriented timeout with UNLIMITED read:
    Shap-E generations + the ZeroGPU queue legitimately take minutes, so a
    read timeout would kill the SSE/polling wait."""
    import gradio_client
    import httpx

    captured = {}

    class _ProbeClient:
        def __init__(self, src, token=None, httpx_kwargs=None):
            captured["src"] = src
            captured["token"] = token
            captured["httpx_kwargs"] = httpx_kwargs

    monkeypatch.setattr(gradio_client, "Client", _ProbeClient)
    ma._default_hf_client_factory("me/space", "tok")
    assert captured["src"] == "me/space"
    assert captured["token"] == "tok"
    timeout = captured["httpx_kwargs"]["timeout"]
    assert isinstance(timeout, httpx.Timeout)
    assert timeout.connect == 30.0
    assert timeout.read is None


# ---- HuggingFaceProvider hardening: retries, backoff, actionable errors ----

import gradio_client.exceptions as gc_exc  # noqa: E402 (installed; offline)


class _FlakyPredictClient:
    """predict() raises scripted exceptions in order, then returns `result`."""
    def __init__(self, raises, result=None):
        self.raises = list(raises)
        self.result = result
        self.calls = 0

    def predict(self, *args, api_name=None):
        self.calls += 1
        if self.raises:
            raise self.raises.pop(0)
        return self.result


class _FlakyFactory:
    """client_factory raising scripted exceptions before returning `client`."""
    def __init__(self, raises, client=None):
        self.raises = list(raises)
        self.client = client
        self.calls = 0

    def __call__(self, space_id, token):
        self.calls += 1
        if self.raises:
            raise self.raises.pop(0)
        return self.client


def test_hf_provider_retries_client_construction_then_succeeds(tmp_path):
    # Cold-start/queue wakeup: one construction failure, then success.
    factory = _FlakyFactory([ConnectionError("cold start")],
                            client=_FakeGradioClient(result=ma.fake_mesh_path()))
    slept = []
    prov = ma.HuggingFaceProvider(client_factory=factory, sleep=slept.append)
    out = prov.generate("a fox", str(tmp_path))
    assert os.path.isfile(out) and os.path.getsize(out) > 0
    assert factory.calls == 2
    assert slept == [10.0]                  # first retry backoff


def test_hf_provider_unreachable_actionable_after_exhausted_retries(tmp_path):
    factory = _FlakyFactory([ConnectionError("down")] * 3)
    slept = []
    prov = ma.HuggingFaceProvider(client_factory=factory, sleep=slept.append)
    with pytest.raises(RuntimeError) as ei:
        prov.generate("a fox", str(tmp_path))
    assert factory.calls == 3               # attempts=3 default
    assert slept == [10.0, 30.0]            # default backoff schedule
    msg = str(ei.value)
    assert f"https://huggingface.co/spaces/{ma.DEFAULT_HF_SPACE}" in msg
    assert "HF_SPACE_ID" in msg
    assert "MESH_PROVIDER=fake" in msg
    assert isinstance(ei.value.__cause__, ConnectionError)


@pytest.mark.parametrize("exc", [
    gc_exc.AppError("upstream Gradio app error"),
    RuntimeError("You have exceeded your free GPU quota"),
    RuntimeError("no gpu is currently available"),
])
def test_hf_provider_quota_errors_do_not_retry(tmp_path, exc):
    client = _FlakyPredictClient([exc])
    slept = []
    prov = ma.HuggingFaceProvider(client_factory=_hf_factory(client),
                                  sleep=slept.append)
    with pytest.raises(RuntimeError) as ei:
        prov.generate("a fox", str(tmp_path))
    assert client.calls == 1                # retrying quota is pointless
    assert slept == []
    msg = str(ei.value)
    assert "quota" in msg.lower()
    assert "HF_TOKEN" in msg
    assert ei.value.__cause__ is exc


def test_hf_provider_generic_predict_error_retries_then_actionable(tmp_path):
    boom = ValueError("weird payload")
    client = _FlakyPredictClient([boom, boom, boom])
    slept = []
    prov = ma.HuggingFaceProvider(client_factory=_hf_factory(client),
                                  sleep=slept.append)
    with pytest.raises(RuntimeError) as ei:
        prov.generate("a fox", str(tmp_path))
    assert client.calls == 3
    assert slept == [10.0, 30.0]
    msg = str(ei.value)
    assert "weird payload" in msg           # cause retained in the message
    assert "MESH_PROVIDER=fake" in msg      # actionable escape hatch
    assert ei.value.__cause__ is boom


def test_hf_provider_custom_attempts_and_backoff(tmp_path):
    factory = _FlakyFactory([ConnectionError("down")] * 5)
    slept = []
    prov = ma.HuggingFaceProvider(client_factory=factory, attempts=4,
                                  backoff=(1.0, 2.0), sleep=slept.append)
    with pytest.raises(RuntimeError):
        prov.generate("a fox", str(tmp_path))
    assert factory.calls == 4
    assert slept == [1.0, 2.0, 2.0]         # last backoff value repeats


def test_get_provider_hf_selected(monkeypatch):
    monkeypatch.setenv("MESH_PROVIDER", "hf")
    monkeypatch.delenv("HF_TOKEN", raising=False)
    assert isinstance(ma.get_provider(), ma.HuggingFaceProvider)


def test_get_provider_hf_reads_env(monkeypatch):
    monkeypatch.setenv("HF_SPACE_ID", "me/space")
    monkeypatch.setenv("HF_API_NAME", "/foo")
    monkeypatch.setenv("HF_TOKEN", "tok")
    prov = ma.get_provider("hf")
    assert prov.space_id == "me/space"
    assert prov.api_name == "/foo"
    assert prov.token == "tok"


def test_get_provider_hf_defaults_when_env_absent(monkeypatch):
    for var in ("HF_SPACE_ID", "HF_API_NAME", "HF_TOKEN"):
        monkeypatch.delenv(var, raising=False)
    prov = ma.get_provider("hf")
    assert prov.space_id == ma.DEFAULT_HF_SPACE
    assert prov.api_name == ma.DEFAULT_HF_API
    assert prov.token is None


def test_get_provider_unknown_lists_hf(monkeypatch):
    monkeypatch.setenv("MESH_PROVIDER", "nope")
    with pytest.raises(ValueError, match="hf"):
        ma.get_provider()


def test_live_hf_smoke(tmp_path):
    """Opt-in: runs only when RUN_HF_SMOKE is set. Validates a real Space."""
    if not os.environ.get("RUN_HF_SMOKE"):
        pytest.skip("RUN_HF_SMOKE not set; skipping live HuggingFace smoke")
    path = ma.acquire_mesh("a simple fox", provider_name="hf",
                           cache_dir=str(tmp_path))
    assert os.path.isfile(path) and os.path.getsize(path) > 0


# ---------------------------------------------------------------------------
# F3 -- provider provenance sidecar (meta.json) + one-shot backfill
#
# The cache was completely unattributable: generated_meshes/<sha>/ held only
# mesh.glb, so identifying which cached mesh answered which live prompt needed
# a brute-force sha256 sweep over candidate prompt strings. These tests pin the
# sidecar, its two write paths (generate AND cache hit), and -- per
# COORDINATION.md 4.1 -- the inputs the verifier is REQUIRED to score as
# failing:
#
#   test_required_fail_a_swapped_glb_must_be_reported_mismatch
#       -- mesh.glb replaced with different bytes after meta.json was written.
#          A provenance record that cannot detect a swapped mesh is decoration.
#   test_required_fail_a_meta_whose_prompt_does_not_hash_to_its_key_is_mismatch
#       -- meta.json claims a prompt that does not reproduce the directory
#          name. Attribution is only trustworthy when it is hash-provable.
#
# Both have a passing control in the same module
# (test_verify_scores_ok_for_a_freshly_written_sidecar) so neither can pass by
# the verifier simply never returning OK.
# ---------------------------------------------------------------------------

import json      # noqa: E402
import hashlib   # noqa: E402


def _read_meta(glb_path):
    with open(os.path.join(os.path.dirname(glb_path), ma.META_FILENAME)) as f:
        return json.load(f)


def test_generate_path_writes_a_sidecar_beside_the_glb(tmp_path):
    glb = ma.acquire_mesh("a red fox", provider_name="fake",
                          cache_dir=str(tmp_path))
    meta = _read_meta(glb)
    assert meta["provider"] == "fake"
    assert meta["prompt"] == "a red fox"
    assert meta["provenance"] == "generated"
    assert meta["cache_key"] == ma.cache_key("fake", "a red fox")
    assert meta["glb"] == "mesh.glb"
    assert meta["glb_bytes"] == os.path.getsize(glb)
    with open(glb, "rb") as f:
        assert meta["glb_sha256"] == hashlib.sha256(f.read()).hexdigest()
    assert meta["generated_utc"] and meta["generated_utc"].endswith("Z")
    assert meta["recorded_utc"] and meta["recorded_utc"].endswith("Z")


def test_cache_hit_backfills_the_sidecar_when_it_is_absent(tmp_path):
    """THE POINT OF THIS UNIT. acquire_mesh returns on a cache hit BEFORE it
    ever reaches provider.generate, so a sidecar written only in the fetch path
    attaches to future fetches and never to the meshes that already exist --
    i.e. it would not attribute the very meshes it exists for."""
    prov = _CountingProvider(ma.fake_mesh_path())
    glb = ma.acquire_mesh("a quadruped", provider=prov, provider_name="fake",
                          cache_dir=str(tmp_path))
    os.remove(os.path.join(os.path.dirname(glb), ma.META_FILENAME))

    glb2 = ma.acquire_mesh("a quadruped", provider=prov, provider_name="fake",
                           cache_dir=str(tmp_path))
    assert glb2 == glb
    assert prov.calls == 1                    # genuinely the cache-hit path
    meta = _read_meta(glb2)
    assert meta["prompt"] == "a quadruped"
    assert meta["provider"] == "fake"
    assert meta["provenance"] == "cache_hit"
    assert ma.verify_mesh_meta(os.path.dirname(glb2))["status"] == "OK"


def test_cache_hit_does_not_rewrite_an_existing_sidecar(tmp_path):
    prov = _CountingProvider(ma.fake_mesh_path())
    glb = ma.acquire_mesh("a quadruped", provider=prov, provider_name="fake",
                          cache_dir=str(tmp_path))
    first = _read_meta(glb)
    assert first["provenance"] == "generated"
    ma.acquire_mesh("a quadruped", provider=prov, provider_name="fake",
                    cache_dir=str(tmp_path))
    assert _read_meta(glb) == first           # untouched, still 'generated'


def test_sidecar_records_the_raw_prompt_verbatim(tmp_path):
    """cache_key hashes the raw prompt with no strip/casefold/normalisation, so
    the recorded prompt must round-trip byte-for-byte or the record cannot be
    checked against the directory name it sits in."""
    prompt = "  An Octopus (eight arms)  "
    glb = ma.acquire_mesh(prompt, provider_name="fake", cache_dir=str(tmp_path))
    meta = _read_meta(glb)
    assert meta["prompt"] == prompt
    assert ma.cache_key(meta["provider"], meta["prompt"]) == \
        os.path.basename(os.path.dirname(glb))


def test_sidecar_records_the_provider_name_actually_used(tmp_path):
    """provider_name falls back to type(provider).__name__, so the same prompt
    can key twice. The record must name the key it was actually filed under."""
    class _PA(ma.FakeMeshProvider):
        pass
    glb = ma.acquire_mesh("x", provider=_PA(), cache_dir=str(tmp_path))
    meta = _read_meta(glb)
    assert meta["provider"] == "_PA"
    assert ma.verify_mesh_meta(os.path.dirname(glb))["status"] == "OK"


def test_sidecar_records_the_hf_endpoint_that_was_actually_called(tmp_path,
                                                                  monkeypatch):
    monkeypatch.setenv("HF_SPACE_ID", "me/other-space")
    monkeypatch.setenv("HF_API_NAME", "/some-endpoint")
    monkeypatch.delenv("HF_TOKEN", raising=False)
    prov = ma.get_provider("hf")
    prov.client_factory = _hf_factory(_FakeGradioClient(result=ma.fake_mesh_path()))
    glb = ma.acquire_mesh("a fox", provider=prov, provider_name="hf",
                          cache_dir=str(tmp_path))
    meta = _read_meta(glb)
    assert meta["space_id"] == "me/other-space"
    assert meta["api_name"] == "/some-endpoint"


def test_cache_hit_sidecar_leaves_the_endpoint_unknown(tmp_path, monkeypatch):
    """On a cache hit the current HF_SPACE_ID is NOT the endpoint that produced
    the bytes -- recording it would fabricate provenance. Unknown must read as
    null, not as today's default."""
    prov = _CountingProvider(ma.fake_mesh_path())
    glb = ma.acquire_mesh("a fox", provider=prov, provider_name="hf",
                          cache_dir=str(tmp_path))
    os.remove(os.path.join(os.path.dirname(glb), ma.META_FILENAME))
    monkeypatch.setenv("HF_SPACE_ID", "me/space-that-did-not-make-this")
    ma.acquire_mesh("a fox", provider=prov, provider_name="hf",
                    cache_dir=str(tmp_path))
    meta = _read_meta(glb)
    assert meta["provenance"] == "cache_hit"
    assert meta["space_id"] is None
    assert meta["api_name"] is None
    assert meta["generated_utc"] is None


def test_a_sidecar_write_failure_never_breaks_acquisition(tmp_path):
    """Provenance is a record, not a gate: an unwritable cache must still
    serve the mesh."""
    glb = ma.acquire_mesh("a red fox", provider_name="fake",
                          cache_dir=str(tmp_path))
    key_dir = os.path.dirname(glb)
    os.remove(os.path.join(key_dir, ma.META_FILENAME))
    os.chmod(key_dir, 0o500)                  # r-x: cannot create a new file
    try:
        again = ma.acquire_mesh("a red fox", provider_name="fake",
                                cache_dir=str(tmp_path))
        assert again == glb and os.path.isfile(again)
        assert not os.path.exists(os.path.join(key_dir, ma.META_FILENAME))
    finally:
        os.chmod(key_dir, 0o700)


def test_verify_scores_ok_for_a_freshly_written_sidecar(tmp_path):
    """Control for the two required-fail tests below: OK is reachable, so a
    MISMATCH verdict is discriminating rather than constant."""
    glb = ma.acquire_mesh("a red fox", provider_name="fake",
                          cache_dir=str(tmp_path))
    v = ma.verify_mesh_meta(os.path.dirname(glb))
    assert v["status"] == "OK"
    assert v["reasons"] == []
    assert v["key"] == ma.cache_key("fake", "a red fox")


def test_required_fail_a_swapped_glb_must_be_reported_mismatch(tmp_path):
    """COORDINATION.md 4.1 required-fail input. Key directory whose mesh.glb
    sha256 disagrees with its meta.json: the bytes were swapped after the
    record was written. This MUST read MISMATCH, never be silently trusted --
    four metrics have shipped vacuous in this repo."""
    glb = ma.acquire_mesh("a red fox", provider_name="fake",
                          cache_dir=str(tmp_path))
    key_dir = os.path.dirname(glb)
    assert ma.verify_mesh_meta(key_dir)["status"] == "OK"   # before the swap

    bird = ma.fake_mesh_path("a bird")
    import shutil
    shutil.copyfile(bird, glb)                              # swap the bytes

    v = ma.verify_mesh_meta(key_dir)
    assert v["status"] == "MISMATCH"
    assert "glb_sha256" in v["reasons"]


def test_required_fail_a_single_flipped_byte_is_caught_by_the_digest_alone(
        tmp_path):
    """COORDINATION.md 4.1, and the one input that isolates `glb_sha256`.

    Every other byte-mismatch test here also changes the file SIZE, so an
    implementation that only ever reported a digest failure ALONGSIDE a size
    failure would pass the whole suite -- the digest check would be riding on
    the cheap one. Flip a single byte in place: size is unchanged, so the
    digest is the only thing that can catch it."""
    glb = ma.acquire_mesh("a red fox", provider_name="fake",
                          cache_dir=str(tmp_path))
    key_dir = os.path.dirname(glb)
    size_before = os.path.getsize(glb)

    with open(glb, "r+b") as f:
        f.seek(size_before // 2)
        original = f.read(1)
        f.seek(size_before // 2)
        f.write(bytes([original[0] ^ 0xFF]))
    assert os.path.getsize(glb) == size_before      # size genuinely unchanged

    v = ma.verify_mesh_meta(key_dir)
    assert v["status"] == "MISMATCH"
    assert v["reasons"] == ["glb_sha256"]           # the digest, and only it


def test_required_fail_a_truncated_glb_must_be_reported_mismatch(tmp_path):
    """Same rule, corruption rather than substitution: a byte-size change with
    the recorded digest left in place."""
    glb = ma.acquire_mesh("a red fox", provider_name="fake",
                          cache_dir=str(tmp_path))
    with open(glb, "rb") as f:
        head = f.read(1024)
    with open(glb, "wb") as f:
        f.write(head)
    v = ma.verify_mesh_meta(os.path.dirname(glb))
    assert v["status"] == "MISMATCH"
    assert "glb_bytes" in v["reasons"] and "glb_sha256" in v["reasons"]


def test_required_fail_a_meta_whose_prompt_does_not_hash_to_its_key_is_mismatch(
        tmp_path):
    """COORDINATION.md 4.1 required-fail input. A record claiming a prompt that
    does not reproduce the directory name is unprovable attribution -- exactly
    the guess the brute-force recovery had to avoid making."""
    glb = ma.acquire_mesh("a red fox", provider_name="fake",
                          cache_dir=str(tmp_path))
    key_dir = os.path.dirname(glb)
    meta_path = os.path.join(key_dir, ma.META_FILENAME)
    meta = _read_meta(glb)
    meta["prompt"] = "a completely different animal"
    with open(meta_path, "w") as f:
        json.dump(meta, f)

    v = ma.verify_mesh_meta(key_dir)
    assert v["status"] == "MISMATCH"
    assert "cache_key" in v["reasons"]


def test_required_fail_an_unparseable_sidecar_is_mismatch_not_no_meta(tmp_path):
    """COORDINATION.md 4.1. A present-but-garbage meta.json is corruption, not
    absence. Scoring it NO_META reads as 'never recorded' and hides the damage
    from the audit -- and NO_META is a status the audit is allowed to ignore."""
    glb = ma.acquire_mesh("a red fox", provider_name="fake",
                          cache_dir=str(tmp_path))
    key_dir = os.path.dirname(glb)
    for junk in ("{not json", "", "[]", "null", '"a string"'):
        with open(os.path.join(key_dir, ma.META_FILENAME), "w") as f:
            f.write(junk)
        v = ma.verify_mesh_meta(key_dir)
        assert v["status"] == "MISMATCH", junk
        assert "meta" in v["reasons"], junk


def test_a_malformed_sidecar_is_never_silently_overwritten(tmp_path):
    """backfill_mesh_cache promises it never overwrites an existing sidecar.
    The cache-hit path must honour the same rule, or the next serve quietly
    replaces a corrupted -- or a richer 'generated' -- record with a thin
    'cache_hit' one and the corruption is gone before anyone audits it."""
    prov = _CountingProvider(ma.fake_mesh_path())
    glb = ma.acquire_mesh("a quadruped", provider=prov, provider_name="fake",
                          cache_dir=str(tmp_path))
    key_dir = os.path.dirname(glb)
    meta_path = os.path.join(key_dir, ma.META_FILENAME)
    with open(meta_path, "w") as f:
        f.write("{corrupted")

    ma.acquire_mesh("a quadruped", provider=prov, provider_name="fake",
                    cache_dir=str(tmp_path))
    with open(meta_path) as f:
        assert f.read() == "{corrupted"        # preserved, not papered over
    assert ma.verify_mesh_meta(key_dir)["status"] == "MISMATCH"

    report = ma.backfill_mesh_cache(str(tmp_path))
    assert [r["action"] for r in report] == ["kept"]
    assert [r["status"] for r in report] == ["MISMATCH"]
    assert ma.backfill_exit_code(report) == 1


def test_verify_reports_no_meta_and_no_mesh_distinctly(tmp_path):
    empty = tmp_path / "deadbeef"
    empty.mkdir()
    assert ma.verify_mesh_meta(str(empty))["status"] == "NO_MESH"
    (empty / "mesh.glb").write_bytes(b"GLB")
    assert ma.verify_mesh_meta(str(empty))["status"] == "NO_META"


def _tamper(key_dir, **fields):
    path = os.path.join(key_dir, ma.META_FILENAME)
    with open(path) as f:
        meta = json.load(f)
    meta.update(fields)
    with open(path, "w") as f:
        json.dump(meta, f)


def test_required_fail_a_meta_naming_a_file_outside_the_key_dir_is_mismatch(
        tmp_path):
    """COORDINATION.md 4.1. `glb` is joined onto key_dir, so a traversing or
    absolute value would make the verifier hash a file it was never meant to
    see -- and then report OK about bytes outside the cache. It must be scored
    MISMATCH, and the outside file must not be what gets hashed."""
    outside = tmp_path / "outside.glb"
    outside.write_bytes(b"NOT-THE-CACHED-MESH")
    glb = ma.acquire_mesh("a red fox", provider_name="fake",
                          cache_dir=str(tmp_path))
    key_dir = os.path.dirname(glb)
    for bad in ("../outside.glb", str(outside), "sub/mesh.glb", "..", ""):
        _tamper(key_dir, glb=bad)
        v = ma.verify_mesh_meta(key_dir)
        assert v["status"] == "MISMATCH", bad
        assert "glb" in v["reasons"], bad


def test_verify_scores_a_garbled_meta_field_rather_than_crashing(tmp_path):
    """A status function must return a status. read_mesh_meta only proves the
    JSON is a dict, so every field it hands on is untrusted input."""
    glb = ma.acquire_mesh("a red fox", provider_name="fake",
                          cache_dir=str(tmp_path))
    key_dir = os.path.dirname(glb)
    for bad in (5, None, ["mesh.glb"], {"name": "mesh.glb"}):
        _tamper(key_dir, glb=bad)
        assert ma.verify_mesh_meta(key_dir)["status"] == "MISMATCH", bad
    _tamper(key_dir, glb="mesh.glb", glb_bytes="not-a-number",
            glb_sha256=None, provider=7, prompt=None)
    v = ma.verify_mesh_meta(key_dir)
    assert v["status"] == "MISMATCH"
    assert set(v["reasons"]) >= {"cache_key", "glb_bytes", "glb_sha256"}


def test_required_fail_a_meta_whose_recorded_glb_is_missing_is_mismatch(
        tmp_path):
    """A record describing bytes that are not there is not 'nothing to
    attribute' -- it is a record that no longer matches its directory. Scoring
    it NO_MESH would let the audit under-report a deleted or renamed mesh."""
    glb = ma.acquire_mesh("a red fox", provider_name="fake",
                          cache_dir=str(tmp_path))
    key_dir = os.path.dirname(glb)
    _tamper(key_dir, glb="renamed.glb")
    v = ma.verify_mesh_meta(key_dir)
    assert v["status"] == "MISMATCH"
    assert "glb" in v["reasons"]


# ---- the one-shot backfill over the meshes that already exist --------------

def test_backfill_table_reproduces_the_recovered_cache_digests():
    """KNOWN_CACHE_PROMPTS is not a guess: every entry must hash to the
    directory it claims. These 20 digests were recovered by brute-forcing
    sha256 over candidate prompt strings; this test is what makes that
    recovery permanent and checkable instead of a session artefact.

    It also pins cache_key itself -- changing the hashing rule would orphan
    every cached mesh, so this fails loudly if anyone touches it."""
    expected = {
        "5a47333a863186404fbb897460b42136eb611474dcd512897bf846d1958b7d4e":
            ("hf", "an octopus"),
        "02712c4c92c9c379740d16134a6cefe82c88c969d3558c2089a2ea66d79c654a":
            ("hf", "a water bear"),
        "1cae117188c2b5afb9c9ce3e3142fadc197ab3d50e1cd83168c9356c17d0ae9b":
            ("hf", "a lizard with a long tail"),
        "36f4aec6a1074973058f1d5d487375e27cd37c55cd458331ecf9d0e1e0fedb09":
            ("hf", "a dog"),
        "d61e21fc8bd8044a2919b2c68554bfc02fbfc94bb00784a68dfdeb3e89ff1403":
            ("hf", "dog"),
        "625014299f54674b8f4c1f67d3e0955643190d7751cb06d3de825eeb996f7a0c":
            ("hf", "a deer"),
        "819194497ac34d8f0af1e03a2a0555649a6e311e85d7f5c287554cb60d662133":
            ("fake", "a dog"),
        "16ddddfd7b273482f73feffad76cc65e005c44097a9d3c53b931340249618eff":
            ("fake", "dog"),
        "016325abe3795fc0cf045b703b99355a601cf320ba96012c0fce4a7503af1a23":
            ("fake", "a horse"),
        "69563d6dbb858b8bb2aeac349de93574e718d0be507a665861a1eed83b29838d":
            ("fake", "horse"),
        "99423baa55fc2acefb86569195749af73073da359aeb83ec15554bed843e74b2":
            ("fake", "bear"),
        "d3f94b18621ead8a55120b39c77f5136da45197700c4c78672bc33cc0dbdbdd5":
            ("fake", "a water bear"),
        "e56fa03a5357a6231627c2d9c7883112a298bd83acdfaef59a7c7e4e8bdeba83":
            ("fake", "a quadruped"),
        "a96870690e3e21bad425bc77e135ac6fb84caac98c27e10630528ac59507c47e":
            ("fake", "a red fox"),
        "5a135a5dc5be5875b75cd37544f574337deb54b473fa6bc30fda426ded85c58b":
            ("fake", "a beetle"),
        "904abbe7198cfdfc74f296781498f679ee6af7a0c938c849331886dca04d8d16":
            ("fake", "beetle"),
        "f602fc8b7417cb66a2ad8d5932f5ea5ff282b127f0e9ec6d84ae05dad0bab601":
            ("fake", "a giant beetle"),
        "6cc8bad2fc3d7018ab3ea2a86d86508eb0b8d6651f3d25afc30847a2ac44edfa":
            ("fake", "a bird"),
        "8f8a0e7036872128eede09d4b113e7526cf441cf173e86f57f57d0e559190e84":
            ("fake", "a fish"),
        "30dd8184f3aee8e654b95820c0cd0035cc3ebc97a22d0be8cc65c7e37b2fb7b5":
            ("fake", "a person"),
    }
    derived = {ma.cache_key(p, q): (p, q) for p, q in ma.KNOWN_CACHE_PROMPTS}
    assert derived == expected


def _seed_key_dir(cache_dir, provider, prompt, blob=b"GLB-BYTES"):
    key_dir = os.path.join(str(cache_dir), ma.cache_key(provider, prompt))
    os.makedirs(key_dir, exist_ok=True)
    with open(os.path.join(key_dir, "mesh.glb"), "wb") as f:
        f.write(blob)
    return key_dir


def test_backfill_attributes_known_keys_and_writes_a_verifiable_sidecar(tmp_path):
    key_dir = _seed_key_dir(tmp_path, "hf", "an octopus")
    report = ma.backfill_mesh_cache(str(tmp_path))
    assert [r["action"] for r in report] == ["written"]
    meta = json.load(open(os.path.join(key_dir, ma.META_FILENAME)))
    assert meta["provider"] == "hf"
    assert meta["prompt"] == "an octopus"
    assert meta["provenance"] == "backfill"
    # The endpoint that produced the 2026-08-16 live meshes is not recoverable,
    # so it stays null: unknown must never be filled in with today's default.
    assert meta["space_id"] is None and meta["api_name"] is None
    assert meta["generated_utc"] is None
    assert ma.verify_mesh_meta(key_dir)["status"] == "OK"


def test_backfill_reports_unknown_keys_without_writing_a_sidecar(tmp_path):
    """meta.json present must mean 'attributed'. A key the table cannot prove
    gets reported, never a null-prompt placeholder -- which would also block
    the cache-hit path from ever upgrading it."""
    unknown = tmp_path / ("0" * 64)
    unknown.mkdir()
    (unknown / "mesh.glb").write_bytes(b"GLB")
    report = ma.backfill_mesh_cache(str(tmp_path))
    assert [r["action"] for r in report] == ["unattributed"]
    assert report[0]["prompt"] is None
    assert not (unknown / ma.META_FILENAME).exists()


def test_backfill_is_idempotent_and_keeps_an_existing_sidecar(tmp_path):
    _seed_key_dir(tmp_path, "hf", "an octopus")
    first = ma.backfill_mesh_cache(str(tmp_path))
    assert [r["action"] for r in first] == ["written"]
    second = ma.backfill_mesh_cache(str(tmp_path))
    assert [r["action"] for r in second] == ["kept"]
    assert [r["status"] for r in second] == ["OK"]


def test_backfill_surfaces_a_mismatched_sidecar_rather_than_overwriting_it(
        tmp_path):
    key_dir = _seed_key_dir(tmp_path, "hf", "an octopus")
    ma.backfill_mesh_cache(str(tmp_path))
    with open(os.path.join(key_dir, "mesh.glb"), "wb") as f:
        f.write(b"DIFFERENT-BYTES")
    report = ma.backfill_mesh_cache(str(tmp_path))
    assert report[0]["action"] == "kept"
    assert report[0]["status"] == "MISMATCH"


def test_backfill_never_writes_through_a_symlinked_key_dir(tmp_path):
    """This repo's worktree bootstrap fills generated_meshes/ with per-key
    symlinks into SIBLING worktrees. Writing through one mutates another
    checkout's data, so a symlinked key dir is reported and skipped."""
    real = tmp_path / "elsewhere"
    real.mkdir()
    (real / "mesh.glb").write_bytes(b"GLB-BYTES")
    cache = tmp_path / "cache"
    cache.mkdir()
    link = cache / ma.cache_key("hf", "an octopus")
    os.symlink(str(real), str(link))

    report = ma.backfill_mesh_cache(str(cache))
    assert [r["action"] for r in report] == ["skipped_symlink"]
    assert not (real / ma.META_FILENAME).exists()

    forced = ma.backfill_mesh_cache(str(cache), follow_symlinks=True)
    assert [r["action"] for r in forced] == ["written"]
    assert (real / ma.META_FILENAME).exists()


def test_cache_hit_does_not_write_through_a_renaming_symlink(tmp_path):
    """A key dir symlinked to a target with a DIFFERENT name is a redirect we
    cannot vouch for: a record written there would be bound to the link's name
    and read as MISMATCH from the target's own path. Skipped."""
    real = tmp_path / "elsewhere"
    real.mkdir()
    import shutil
    shutil.copyfile(ma.fake_mesh_path(), str(real / "mesh.glb"))
    cache = tmp_path / "cache"
    cache.mkdir()
    os.symlink(str(real), str(cache / ma.cache_key("fake", "a quadruped")))

    prov = _CountingProvider(ma.fake_mesh_path())
    glb = ma.acquire_mesh("a quadruped", provider=prov, provider_name="fake",
                          cache_dir=str(cache))
    assert prov.calls == 0                     # served from the symlinked cache
    assert os.path.isfile(glb)
    assert not (real / ma.META_FILENAME).exists()


def _same_key_alias(tmp_path, provider, prompt, blob=None):
    """The regime this repo actually runs in: an agent worktree's
    generated_meshes/<key> is a symlink to <key> -- the SAME key name -- in a
    sibling checkout. Returns (cache_dir, link_path, target_path)."""
    key = ma.cache_key(provider, prompt)
    store = tmp_path / "sibling_checkout" / "generated_meshes"
    target = store / key
    target.mkdir(parents=True)
    if blob is None:
        import shutil
        shutil.copyfile(ma.fake_mesh_path(), str(target / "mesh.glb"))
    else:
        (target / "mesh.glb").write_bytes(blob)
    cache = tmp_path / "worktree" / "generated_meshes"
    cache.mkdir(parents=True)
    link = cache / key
    os.symlink(str(target), str(link))
    return str(cache), str(link), str(target)


def test_cache_hit_writes_through_a_SAME_KEY_alias_symlink(tmp_path):
    """THE REGIME THIS UNIT EXISTS FOR, and the one it originally missed.

    Every key directory in an agent worktree is a symlink into a sibling
    checkout -- that is how the three live meshes are reachable at all. A blanket
    "never write through a symlink" guard meant the cache-hit path, the whole
    point of this unit, fired ZERO times in the only environment where the work
    happens, and the 'the shared cache is unchanged' safety check was
    unfalsifiable because the write was skipped rather than performed and found
    harmless.

    A same-key alias is not a redirect: link and target carry the SAME cache
    key, so the record is valid read from either path. Write it."""
    cache, link, target = _same_key_alias(tmp_path, "fake", "a quadruped")
    prov = _CountingProvider(ma.fake_mesh_path())
    glb = ma.acquire_mesh("a quadruped", provider=prov, provider_name="fake",
                          cache_dir=cache)
    assert prov.calls == 0                          # genuinely the cache hit
    assert os.path.isfile(glb)
    assert os.path.isfile(os.path.join(target, ma.META_FILENAME)), \
        "the cache-hit write is still guarded off in the worktree regime"
    meta = json.load(open(os.path.join(target, ma.META_FILENAME)))
    assert meta["provenance"] == "cache_hit"
    assert meta["prompt"] == "a quadruped"
    # Valid read from BOTH paths -- that is what makes the alias safe to write.
    assert ma.verify_mesh_meta(link)["status"] == "OK"
    assert ma.verify_mesh_meta(target)["status"] == "OK"


def test_backfill_writes_through_a_SAME_KEY_alias_symlink(tmp_path):
    cache, link, target = _same_key_alias(tmp_path, "hf", "an octopus")
    report = ma.backfill_mesh_cache(cache)
    assert [r["action"] for r in report] == ["written"]
    assert os.path.isfile(os.path.join(target, ma.META_FILENAME))
    assert ma.verify_mesh_meta(target)["status"] == "OK"


def test_backfill_writes_nothing_outside_the_cache_dir(tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    _seed_key_dir(cache, "fake", "a bird")
    sentinel = tmp_path / "outside.txt"
    sentinel.write_text("untouched")
    before = sorted(p.name for p in tmp_path.iterdir())
    ma.backfill_mesh_cache(str(cache))
    assert sorted(p.name for p in tmp_path.iterdir()) == before
    assert sentinel.read_text() == "untouched"
    assert sorted(os.listdir(cache / ma.cache_key("fake", "a bird"))) == \
        ["mesh.glb", ma.META_FILENAME]


def test_backfill_on_a_missing_cache_dir_is_an_empty_report(tmp_path):
    assert ma.backfill_mesh_cache(str(tmp_path / "nope")) == []


def test_backfill_cli_separates_a_missing_cache_from_a_clean_one(tmp_path):
    """An audit that cannot tell 'nothing to check' from 'everything checks
    out' reports a typo'd path, an unset MESH_OUTPUT_DIR and a never-
    bootstrapped worktree all as success."""
    _seed_key_dir(tmp_path, "fake", "a bird")
    assert ma.run_backfill_cli([str(tmp_path)]) == 0            # clean
    assert ma.run_backfill_cli([str(tmp_path / "nope")]) == 2   # no cache


def test_backfill_reports_a_dangling_key_symlink_instead_of_dropping_it(
        tmp_path):
    """Sibling worktrees get auto-cleaned, so a key dir symlinked into one
    becomes dangling as a matter of course. os.path.isdir() follows the link
    and reports False, which would drop the row entirely -- the audit would
    say nothing at all about a cache entry that has lost its bytes."""
    cache = tmp_path / "cache"
    cache.mkdir()
    os.symlink(str(tmp_path / "gone"),
               str(cache / ma.cache_key("hf", "an octopus")))
    report = ma.backfill_mesh_cache(str(cache))
    assert [r["action"] for r in report] == ["dangling_symlink"]
    # ERROR, not NO_MESH: an entry whose bytes have vanished must not read as a
    # clean audit -- see test_a_dangling_alias_still_reports_what_the_table_knows.
    assert [r["status"] for r in report] == ["ERROR"]
    assert report[0]["error"]
    assert not ma.is_same_key_alias(str(cache / ma.cache_key("hf", "an octopus")))


def test_audit_mode_reports_without_writing_anything(tmp_path):
    """Cache directories here are aliases into other checkouts, so 'tell me
    what is unattributed' must not require mutating them."""
    key_dir = _seed_key_dir(tmp_path, "hf", "an octopus")
    report = ma.backfill_mesh_cache(str(tmp_path), write=False)
    assert [r["action"] for r in report] == ["would_write"]
    assert not os.path.exists(os.path.join(key_dir, ma.META_FILENAME))


def test_alias_writes_can_be_refused(tmp_path):
    """Writing through a same-key alias is the default because it is the only
    way a worktree attributes anything -- but it does mutate another checkout,
    so there has to be a way to say no."""
    cache, link, target = _same_key_alias(tmp_path, "hf", "an octopus")
    report = ma.backfill_mesh_cache(cache, aliases=False)
    assert [r["action"] for r in report] == ["skipped_symlink"]
    assert not os.path.exists(os.path.join(target, ma.META_FILENAME))


def test_repair_is_the_documented_way_out_of_a_corrupted_sidecar(tmp_path):
    """Preserving corruption as evidence is right; leaving no exit from it is
    not. Repair is opt-in, only touches records that FAIL verification, and
    only where the key is provable."""
    key_dir = _seed_key_dir(tmp_path, "hf", "an octopus")
    ma.backfill_mesh_cache(str(tmp_path))
    good = open(os.path.join(key_dir, ma.META_FILENAME)).read()
    with open(os.path.join(key_dir, ma.META_FILENAME), "w") as f:
        f.write("{corrupted")

    assert [r["action"] for r in ma.backfill_mesh_cache(str(tmp_path))] == \
        ["kept"]                                     # default never repairs
    report = ma.backfill_mesh_cache(str(tmp_path), repair=True)
    assert [r["action"] for r in report] == ["repaired"]
    assert [r["status"] for r in report] == ["OK"]
    assert ma.backfill_exit_code(report) == 0

    # A record that VERIFIES is never rewritten, even under --repair.
    before = open(os.path.join(key_dir, ma.META_FILENAME)).read()
    assert [r["action"] for r in
            ma.backfill_mesh_cache(str(tmp_path), repair=True)] == ["kept"]
    assert open(os.path.join(key_dir, ma.META_FILENAME)).read() == before
    assert json.loads(before)["prompt"] == json.loads(good)["prompt"]


def test_required_fail_repair_must_not_launder_a_swapped_mesh(tmp_path):
    """COORDINATION.md 4.1, and the sharpest edge on this whole unit.

    --repair exists so a DAMAGED RECORD is not a dead end. It must never touch
    a record whose digest disagrees, because that is not a damaged record --
    it is intact provenance correctly reporting that the BYTES changed.
    Rewriting it would restate the swapped mesh as `hf:an octopus`, turn the
    audit permanently green, and destroy the only evidence of the swap: the
    exact failure this module exists to prevent."""
    key_dir = _seed_key_dir(tmp_path, "hf", "an octopus")
    ma.backfill_mesh_cache(str(tmp_path))
    with open(os.path.join(key_dir, "mesh.glb"), "wb") as f:
        f.write(b"A-COMPLETELY-DIFFERENT-MESH")

    report = ma.backfill_mesh_cache(str(tmp_path), repair=True)
    assert [r["action"] for r in report] == ["kept"]
    assert [r["status"] for r in report] == ["MISMATCH"]
    assert ma.backfill_exit_code(report) == 1        # still gates, still red
    meta = json.load(open(os.path.join(key_dir, ma.META_FILENAME)))
    assert meta["glb_bytes"] != os.path.getsize(os.path.join(key_dir,
                                                             "mesh.glb"))
    assert ma.run_backfill_cli([str(tmp_path), "--repair"]) == 1


def test_repair_still_fixes_a_record_whose_bytes_are_intact(tmp_path):
    """The control for the test above: repair must remain reachable, or the
    refusal is just a broken feature rather than a safety rule."""
    key_dir = _seed_key_dir(tmp_path, "hf", "an octopus")
    ma.backfill_mesh_cache(str(tmp_path))
    _tamper(key_dir, prompt="a prompt that does not hash to this key")
    assert ma.verify_mesh_meta(key_dir)["reasons"] == ["cache_key"]
    report = ma.backfill_mesh_cache(str(tmp_path), repair=True)
    assert [r["action"] for r in report] == ["repaired"]
    assert [r["status"] for r in report] == ["OK"]
    assert json.load(open(os.path.join(key_dir,
                                       ma.META_FILENAME)))["prompt"] == \
        "an octopus"


def test_required_fail_a_mesh_symlinked_out_of_the_cache_is_not_vouched_for(
        tmp_path):
    """COORDINATION.md 4.1. The `glb` NAME is validated as a plain basename,
    but every read of it follows symlinks -- so a `mesh.glb` that is itself a
    link to a file outside the cache would be hashed and positively attributed,
    which is precisely what the name check exists to prevent."""
    outside = tmp_path / "outside.glb"
    outside.write_bytes(b"BYTES-THAT-ARE-NOT-IN-THE-CACHE")
    key_dir = os.path.join(str(tmp_path), ma.cache_key("hf", "an octopus"))
    os.makedirs(key_dir)
    os.symlink(str(outside), os.path.join(key_dir, "mesh.glb"))

    report = ma.backfill_mesh_cache(str(tmp_path))
    assert [r["action"] for r in report] == ["error"]
    assert not os.path.exists(os.path.join(key_dir, ma.META_FILENAME))
    assert ma.backfill_exit_code(report) == 1

    ma.write_mesh_meta.__wrapped__ if False else None
    with pytest.raises(ValueError, match="outside"):
        ma.write_mesh_meta(key_dir, provider="hf", prompt="an octopus",
                           provenance="backfill")


def test_backfill_cli_rejects_an_unrecognised_flag(tmp_path):
    """A mistyped read-only flag must not fall through to the WRITING default
    -- which, through a same-key alias, mutates another checkout."""
    key_dir = _seed_key_dir(tmp_path, "fake", "a bird")
    assert ma.run_backfill_cli([str(tmp_path), "--dry-run"]) == 2
    assert not os.path.exists(os.path.join(key_dir, ma.META_FILENAME))
    assert ma.run_backfill_cli([str(tmp_path), "--audit"]) == 0
    assert not os.path.exists(os.path.join(key_dir, ma.META_FILENAME))


def test_a_dangling_alias_still_reports_what_the_table_knows(tmp_path):
    """The row exists so the audit is not silent about an entry that lost its
    bytes; reporting it as unattributable throws away the one thing we do
    know, and leaves an automated gate green."""
    cache = tmp_path / "cache"
    cache.mkdir()
    os.symlink(str(tmp_path / "gone"),
               str(cache / ma.cache_key("hf", "an octopus")))
    report = ma.backfill_mesh_cache(str(cache))
    assert report[0]["action"] == "dangling_symlink"
    assert report[0]["provider"] == "hf"
    assert report[0]["prompt"] == "an octopus"
    assert ma.backfill_exit_code(report) == 1     # a lost mesh is not "clean"


def test_two_writes_in_one_process_never_share_a_temp_path(tmp_path):
    """A threaded caller (the archived MCP server dispatched tools on a
    threadpool) makes a pid-keyed temp name NOT call-unique: two threads
    acquiring the same prompt would truncate each other's partial record and
    os.replace could publish it."""
    seen = []
    real_replace = os.replace

    def spy(src, dst):
        seen.append(src)
        return real_replace(src, dst)

    key_dir = _seed_key_dir(tmp_path, "fake", "a bird")
    import unittest.mock as mock
    with mock.patch.object(ma.os, "replace", spy):
        ma.write_mesh_meta(key_dir, provider="fake", prompt="a bird",
                           provenance="backfill")
        ma.write_mesh_meta(key_dir, provider="fake", prompt="a bird",
                           provenance="backfill")
    assert len(seen) == 2
    assert seen[0] != seen[1], "temp path is not unique per call"
    assert all(os.path.dirname(p) == key_dir for p in seen)   # still in-cache
    # sorted(): os.listdir returns filesystem order, which is hash order on
    # ext4 -- an unsorted compare is a Linux-CI-only flake.
    assert sorted(os.listdir(key_dir)) == sorted(["mesh.glb", ma.META_FILENAME])


def test_conftest_disables_provenance_writing_for_the_whole_suite():
    """A test run must not mutate state outside its own worktree.

    Five call sites acquire without a `cache_dir` (tests/test_square_complete.py
    :170, probe_spike_kawasaki.py:21, probe_dangling.py:22,
    probe_square_lint.py:25, probe_base_eval.py:225), and in a worktree those
    keys resolve through symlinks into ANOTHER CHECKOUT -- so the suite would
    quietly write sidecars there. Correct and gitignored, but exactly the kind
    of cross-checkout surprise that costs an hour of phantom debugging later.

    conftest.py uses setdefault, so an explicit IDE_MESH_PROVENANCE=1 in the
    environment still wins for anyone who wants to exercise the real path."""
    assert _SESSION_PROVENANCE_ENV == "0", (
        "mcp_harness/conftest.py must disable sidecar writing for the suite; "
        f"session value was {_SESSION_PROVENANCE_ENV!r}")
    # And the module-scoped fixture must have restored it for these tests.
    assert ma.provenance_enabled()


def test_provenance_writing_can_be_switched_off_by_env(tmp_path, monkeypatch):
    """Escape hatch for anyone who does not want a serve touching the cache at
    all -- the suite's own probes acquire without a cache_dir."""
    monkeypatch.setenv("IDE_MESH_PROVENANCE", "0")
    glb = ma.acquire_mesh("a red fox", provider_name="fake",
                          cache_dir=str(tmp_path))
    assert os.path.isfile(glb)
    assert not os.path.exists(os.path.join(os.path.dirname(glb),
                                           ma.META_FILENAME))


def test_backfill_keeps_auditing_after_an_unwritable_key_dir(tmp_path):
    """One bad directory must not discard the whole audit. These caches are
    shared between checkouts, so a read-only or racing key dir is the expected
    failure, not the exotic one."""
    bad = _seed_key_dir(tmp_path, "hf", "an octopus")
    good = _seed_key_dir(tmp_path, "fake", "a bird")
    os.chmod(bad, 0o500)
    try:
        report = ma.backfill_mesh_cache(str(tmp_path))
    finally:
        os.chmod(bad, 0o700)
    by_key = {r["key"]: r for r in report}
    assert len(report) == 2
    assert by_key[os.path.basename(bad)]["action"] == "error"
    assert by_key[os.path.basename(bad)]["error"]
    assert by_key[os.path.basename(good)]["action"] == "written"
    assert os.path.isfile(os.path.join(good, ma.META_FILENAME))


def test_backfill_reads_the_glb_name_from_the_sidecar(tmp_path):
    """A provider whose generate() returned a differently-named file records
    that name; the audit must use it rather than assuming mesh.glb and
    reporting a perfectly good key dir as no_mesh."""
    key_dir = os.path.join(str(tmp_path), ma.cache_key("fake", "a bird"))
    os.makedirs(key_dir)
    with open(os.path.join(key_dir, "other.glb"), "wb") as f:
        f.write(b"GLB-BYTES")
    ma.write_mesh_meta(key_dir, provider="fake", prompt="a bird",
                       provenance="generated", glb="other.glb")
    report = ma.backfill_mesh_cache(str(tmp_path))
    assert [r["action"] for r in report] == ["kept"]
    assert [r["status"] for r in report] == ["OK"]


def test_backfill_exit_code_gates_on_mismatch(tmp_path):
    """--backfill is documented as the cache audit; an audit that exits 0 on a
    MISMATCH cannot gate anything."""
    assert ma.backfill_exit_code([]) == 0
    assert ma.backfill_exit_code(
        [{"status": "OK"}, {"status": "NO_META"}]) == 0
    assert ma.backfill_exit_code([{"status": "OK"}, {"status": "MISMATCH"}]) == 1
    assert ma.backfill_exit_code([{"status": "ERROR"}]) == 1


def test_generating_into_a_symlinked_key_dir_still_records_provenance(tmp_path):
    """The symlink guard exists so a CACHE HIT never mutates a sibling
    checkout. It must not extend to the generate path: provider.generate has
    already written a multi-MB mesh.glb through that same symlink, and leaving
    those bytes unattributed is the worst of both -- foreign data written, no
    record of what it is."""
    real = tmp_path / "elsewhere"
    real.mkdir()
    cache = tmp_path / "cache"
    cache.mkdir()
    key_dir = cache / ma.cache_key("fake", "a quadruped")
    os.symlink(str(real), str(key_dir))

    prov = _CountingProvider(ma.fake_mesh_path())
    glb = ma.acquire_mesh("a quadruped", provider=prov, provider_name="fake",
                          cache_dir=str(cache))
    assert prov.calls == 1                        # empty target -> real fetch
    assert os.path.isfile(glb)
    assert (real / ma.META_FILENAME).exists()
    # Verified through the CACHE path, not the resolved target: the record is
    # bound to the key directory's NAME, and 'elsewhere' is not that name.
    assert ma.verify_mesh_meta(str(key_dir))["status"] == "OK"
    assert ma.verify_mesh_meta(str(real))["status"] == "MISMATCH"


# ---------------------------------------------------------------------------
# settings fingerprint (2026-10-07)
#
# cache_key(provider, prompt) named the prompt and nothing else. Once hf2's
# stage 1 gained a prompt TEMPLATE and a pinned SEED, a cached "a dog" made
# under one template was served after the template changed -- silently, with
# the new template never run. A provider that declares `cache_settings` is now
# keyed on them too, as "<readable slug>-<digest>". Providers that declare
# nothing keep the legacy key, so every existing entry and KNOWN_CACHE_PROMPTS
# still reproduce.
# ---------------------------------------------------------------------------

class _SettingsProvider(_CountingProvider):
    def __init__(self, fixture, settings):
        super().__init__(fixture)
        self.cache_settings = settings


def test_a_settings_key_is_readable_and_deterministic():
    k = ma.cache_key("hf2", "a dog", {"seed": 11})
    assert k == ma.cache_key("hf2", "a dog", {"seed": 11})
    slug, digest = k.rsplit("-", 1)
    assert slug == "a-dog"
    assert len(digest) == 16 and int(digest, 16) >= 0


@pytest.mark.parametrize("prompt, slug", [
    ("  An Octopus (eight arms)  ", "an-octopus-eight-arms"),
    ("!!!", "mesh"),
    ("x" * 200, "x" * 40),
])
def test_the_slug_is_filesystem_safe_and_bounded(prompt, slug):
    assert ma.cache_key("hf2", prompt, {}).rsplit("-", 1)[0] == slug


def test_every_input_moves_a_settings_key():
    """MUST-FAIL INPUT: hashing the prompt alone (the slug alone would match)."""
    base = ma.cache_key("hf2", "a dog", {"seed": 11, "template": "T"})
    assert base != ma.cache_key("hf2", "a dog", {"seed": 22, "template": "T"})
    assert base != ma.cache_key("hf2", "a dog", {"seed": 11, "template": "U"})
    assert base != ma.cache_key("hf", "a dog", {"seed": 11, "template": "T"})
    assert base != ma.cache_key("hf2", "dog", {"seed": 11, "template": "T"})
    # key order is not a setting
    assert base == ma.cache_key("hf2", "a dog", {"template": "T", "seed": 11})


def test_no_settings_keeps_the_legacy_key():
    """The 20 recovered digests are pinned elsewhere in this module; this is
    the direct statement that they cannot move."""
    import hashlib as _h
    assert ma.cache_key("hf", "a dog") == \
        _h.sha256(b"hf:a dog").hexdigest()


def test_changed_settings_are_a_cache_miss_not_a_stale_hit(tmp_path):
    """THE BUG. MUST-FAIL INPUT: the pre-fingerprint acquire_mesh, which
    returns the first mesh for the second call and never calls generate."""
    prov = _SettingsProvider(ma.fake_mesh_path(), {"seed": 11})
    a = ma.acquire_mesh("a dog", provider=prov, provider_name="hf2",
                        cache_dir=str(tmp_path))
    prov.cache_settings = {"seed": 22}
    b = ma.acquire_mesh("a dog", provider=prov, provider_name="hf2",
                        cache_dir=str(tmp_path))
    assert prov.calls == 2
    assert os.path.dirname(a) != os.path.dirname(b)
    # ...and unchanged settings still hit
    ma.acquire_mesh("a dog", provider=prov, provider_name="hf2",
                    cache_dir=str(tmp_path))
    assert prov.calls == 2


def test_a_settings_entry_records_its_settings_and_verifies(tmp_path):
    prov = _SettingsProvider(ma.fake_mesh_path(), {"seed": 11})
    glb = ma.acquire_mesh("a dog", provider=prov, provider_name="hf2",
                          cache_dir=str(tmp_path))
    meta = _read_meta(glb)
    assert meta["settings"] == {"seed": 11}
    assert os.path.basename(os.path.dirname(glb)) == meta["cache_key"]
    assert ma.verify_mesh_meta(os.path.dirname(glb))["status"] == "OK"


def test_a_cache_hit_backfill_records_the_settings_too(tmp_path):
    prov = _SettingsProvider(ma.fake_mesh_path(), {"seed": 11})
    glb = ma.acquire_mesh("a dog", provider=prov, provider_name="hf2",
                          cache_dir=str(tmp_path))
    os.remove(os.path.join(os.path.dirname(glb), ma.META_FILENAME))
    ma.acquire_mesh("a dog", provider=prov, provider_name="hf2",
                    cache_dir=str(tmp_path))
    meta = _read_meta(glb)
    assert meta["provenance"] == "cache_hit"
    assert meta["settings"] == {"seed": 11}
    assert ma.verify_mesh_meta(os.path.dirname(glb))["status"] == "OK"


def test_required_fail_editing_the_recorded_settings_is_a_mismatch(tmp_path):
    """A record whose settings were changed after the fact no longer names the
    bytes beside it. MUST-FAIL INPUT: a verifier that ignores `settings`."""
    prov = _SettingsProvider(ma.fake_mesh_path(), {"seed": 11})
    glb = ma.acquire_mesh("a dog", provider=prov, provider_name="hf2",
                          cache_dir=str(tmp_path))
    key_dir = os.path.dirname(glb)
    meta = _read_meta(glb)
    meta["settings"] = {"seed": 22}
    with open(os.path.join(key_dir, ma.META_FILENAME), "w") as f:
        json.dump(meta, f)
    v = ma.verify_mesh_meta(key_dir)
    assert v["status"] == "MISMATCH" and "cache_key" in v["reasons"]


@pytest.mark.parametrize("bad", ["seed=11", [11], 11])
def test_a_garbled_settings_field_is_scored_not_raised(tmp_path, bad):
    prov = _SettingsProvider(ma.fake_mesh_path(), {"seed": 11})
    glb = ma.acquire_mesh("a dog", provider=prov, provider_name="hf2",
                          cache_dir=str(tmp_path))
    key_dir = os.path.dirname(glb)
    meta = _read_meta(glb)
    meta["settings"] = bad
    with open(os.path.join(key_dir, ma.META_FILENAME), "w") as f:
        json.dump(meta, f)
    assert ma.verify_mesh_meta(key_dir)["status"] == "MISMATCH"


def test_a_legacy_record_has_no_settings_field(tmp_path):
    """Records for providers without settings stay byte-for-byte the old
    shape, so nothing reading them has to learn a new field."""
    glb = ma.acquire_mesh("a red fox", provider_name="fake",
                          cache_dir=str(tmp_path))
    assert "settings" not in _read_meta(glb)


def test_default_hf2_draws_keep_todays_cache_key(monkeypatch):
    """The live cache entry for "moose" (drawn 2026-10-11) must stay reachable:
    adding description/seed must not move any default key."""
    for v in ("HF_IMAGE_SPACE_ID", "HF_MESH_SPACE_ID", "HF_IMAGE_API", "HF_MESH_API"):
        monkeypatch.delenv(v, raising=False)
    p = ma.get_provider("hf2")
    assert ma.cache_key("hf2", "moose", p.cache_settings) == "moose-0ea544523bcf6966"


def test_a_seed_or_a_description_gets_its_own_cache_key(monkeypatch):
    for v in ("HF_IMAGE_SPACE_ID", "HF_MESH_SPACE_ID", "HF_IMAGE_API", "HF_MESH_API"):
        monkeypatch.delenv(v, raising=False)
    plain = ma.get_provider("hf2")
    seeded = ma.get_provider("hf2", seed=48213)
    assert seeded.image_kwargs["seed"] == seeded.mesh_kwargs["seed"] == 48213
    assert seeded.image_kwargs["randomize_seed"] is False
    assert seeded.mesh_kwargs["randomize_seed"] is False
    described = ma.get_provider("hf2", description="bull moose")
    keys = {ma.cache_key("hf2", "moose", p.cache_settings)
            for p in (plain, seeded, described)}
    assert len(keys) == 3


def test_the_fake_provider_ignores_description_and_seed(tmp_path):
    a = ma.acquire_mesh("a bird", provider_name="fake", cache_dir=str(tmp_path))
    b = ma.acquire_mesh("a bird", provider_name="fake", cache_dir=str(tmp_path),
                        description="a sparrow", seed=7)
    assert a == b


def test_cached_files_names_the_concept_and_the_mesh(tmp_path):
    (tmp_path / "mesh.glb").write_bytes(b"glTF")
    assert ma.cached_files(str(tmp_path)) == (None, str(tmp_path / "mesh.glb"))
    (tmp_path / "concept.webp").write_bytes(b"RIFF")
    assert ma.cached_files(str(tmp_path))[0] == str(tmp_path / "concept.webp")


# ---- reference mesh library (MESH_LIBRARY_DIR) ------------------------------


def _library(tmp_path, *stems, photo=True):
    lib = tmp_path / "library"
    (lib / "meshes").mkdir(parents=True)
    (lib / "photos").mkdir()
    for stem in stems:
        (lib / "meshes" / f"{stem}.glb").write_bytes(open(ma.fake_mesh_path("a bird"), "rb").read())
        if photo:
            (lib / "photos" / f"{stem}.png").write_bytes(b"\x89PNG photo of " + stem.encode())
    return lib


def test_library_is_off_without_the_env_var(tmp_path, monkeypatch):
    _library(tmp_path, "dog")
    monkeypatch.delenv("MESH_LIBRARY_DIR", raising=False)
    assert ma.library_mesh("dog", cache_dir=str(tmp_path / "cache")) is None


def test_library_matches_the_subject_key_with_underscores_as_spaces(tmp_path, monkeypatch):
    lib = _library(tmp_path, "dog", "guinea_pig")
    monkeypatch.setenv("MESH_LIBRARY_DIR", str(lib))
    cache = str(tmp_path / "cache")
    d = ma.library_mesh("guinea pig", cache_dir=cache)
    assert d is not None and os.path.dirname(d) == cache
    concept, glb = ma.cached_files(d)
    assert open(glb, "rb").read() == (lib / "meshes" / "guinea_pig.glb").read_bytes()
    assert open(concept, "rb").read() == b"\x89PNG photo of guinea_pig"
    assert ma.library_mesh("cat", cache_dir=cache) is None
    assert ma.library_mesh("a dog", cache_dir=cache) is None   # keys, not prompts


def test_library_folder_is_reused_and_its_sidecar_verifies(tmp_path, monkeypatch):
    lib = _library(tmp_path, "dog")
    monkeypatch.setenv("MESH_LIBRARY_DIR", str(lib))
    cache = str(tmp_path / "cache")
    d = ma.library_mesh("dog", cache_dir=cache)
    assert ma.library_mesh("dog", cache_dir=cache) == d
    assert os.listdir(cache) == [os.path.basename(d)]           # no temp folder left behind
    v = ma.verify_mesh_meta(d)
    assert v["status"] == "OK" and v["meta"]["provenance"] == "library"


def test_a_changed_library_mesh_gets_a_new_folder(tmp_path, monkeypatch):
    lib = _library(tmp_path, "dog")
    monkeypatch.setenv("MESH_LIBRARY_DIR", str(lib))
    cache = str(tmp_path / "cache")
    first = ma.library_mesh("dog", cache_dir=cache)
    (lib / "meshes" / "dog.glb").write_bytes(open(ma.fake_mesh_path("a fox"), "rb").read())
    assert ma.library_mesh("dog", cache_dir=cache) != first


def test_a_library_mesh_without_a_photo_has_no_concept(tmp_path, monkeypatch):
    lib = _library(tmp_path, "dog", photo=False)
    monkeypatch.setenv("MESH_LIBRARY_DIR", str(lib))
    concept, glb = ma.cached_files(ma.library_mesh("dog", cache_dir=str(tmp_path / "cache")))
    assert concept is None and os.path.getsize(glb) > 0
