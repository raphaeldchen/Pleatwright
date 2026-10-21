"""TwoStageProvider: text -> concept image -> 3D mesh.

WHY THIS PROVIDER EXISTS (measured 2026-08-22, all figures reproducible):

The five fixtures the whole pipeline is tuned and scored against are
hand-modelled low-poly assets -- quadruped 576 faces, bird 608, insect 2000,
humanoid 4672. The three live prompts that produced badly wrong trees are
Shap-E marching-cubes output -- lizard 9848 faces, water_bear 98956, octopus
102308, up to 178x denser and fragmented into as many as 17 disconnected
bodies. The separation is perfect: every scorecard subject is hand-modelled,
every failure is generated. Extraction was calibrated on an object class the
live path never produces.

Shap-E (2023) is the last NATIVE text-to-3D Space still running; the field
moved to multi-view diffusion + reconstruction, which is image-to-3D. So a
better generator necessarily means two stages. That is not a new architecture:
CLAUDE.md section 5 Step 1 already specifies a "Concept Art Phase
(Text-to-Image)"; the shipped implementation skipped it.

EVERY TEST HERE RUNS OFFLINE against an injected client factory. That is not
merely for speed -- both stages are ZeroGPU Spaces, and the account quota has
been 0s throughout development, so an injected client is the only way any of
this is falsifiable at all.
"""
import os

import pytest

import mesh_acquire


# ---------------------------------------------------------------------------
# fakes
# ---------------------------------------------------------------------------

class _FakeClient:
    """Records every predict() call so ORDER and ARGUMENTS are assertable."""

    def __init__(self, space_id, token, results, log):
        self.space_id = space_id
        self.token = token
        self._results = results
        self._log = log

    def predict(self, *args, **kwargs):
        self._log.append({"space": self.space_id, "args": args,
                          "api_name": kwargs.get("api_name")})
        out = self._results[self.space_id]
        if isinstance(out, Exception):
            raise out
        return out(*args) if callable(out) else out


def _factory(results, log):
    def make(space_id, token):
        if space_id not in results:
            raise AssertionError(f"unexpected space {space_id!r}")
        return _FakeClient(space_id, token, results, log)
    return make


@pytest.fixture()
def png(tmp_path):
    path = tmp_path / "concept.png"
    # a real 1x1 PNG: the provider copies bytes, so a truthy non-empty file is
    # what matters, but a valid one keeps the fixture honest if that changes.
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00"
        b"\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82")
    return str(path)


@pytest.fixture()
def glb(tmp_path):
    path = tmp_path / "out.glb"
    path.write_bytes(b"glTF\x02\x00\x00\x00" + b"\x00" * 64)
    return str(path)


def _file_arg(path):
    """What a gradio `filepath` input must look like ON THE WIRE.

    Not decoration: passing the bare path makes gradio_client raise
    "gradio.data_classes.FileData() argument after ** must be a mapping, not
    str" -- client-side, before any request -- and it raises it as an AppError,
    which the provider used to read as GPU quota exhaustion. A serialization
    bug of ours was reported as the account being out of budget.
    """
    from gradio_client import handle_file
    return handle_file(path)


def _provider(results, log, **kw):
    return mesh_acquire.TwoStageProvider(
        image_space="img/space", image_api="/infer",
        mesh_space="mesh/space", mesh_api="/image_to_3d",
        client_factory=_factory(results, log), sleep=lambda _s: None, **kw)


# ---------------------------------------------------------------------------
# the two stages, in order, with the image actually carried between them
# ---------------------------------------------------------------------------

def test_the_image_stage_runs_first_and_its_output_feeds_the_mesh_stage(
        tmp_path, png, glb):
    """The whole point of two stages is that stage 2 consumes stage 1's image.

    MUST-FAIL INPUT (COORDINATION.md 4.1): a provider that ignores the concept
    image and passes the raw prompt to the mesh Space would satisfy "two calls
    happened" but fail the `args[0] == png` assertion below. That is precisely
    the regression that would silently turn this back into a one-stage
    text-to-3D call wearing a two-stage costume.
    """
    log = []
    prov = _provider({"img/space": png, "mesh/space": glb}, log)
    out = prov.generate("an octopus", str(tmp_path / "cache"))

    assert [c["space"] for c in log] == ["img/space", "mesh/space"]
    assert log[0]["args"][0] == "an octopus"         # prompt into stage 1
    # the IMAGE into stage 2, wrapped as FileData because that is what a
    # gradio `filepath` input takes
    assert log[1]["args"][0] == _file_arg(png)
    assert log[0]["api_name"] == "/infer"
    assert log[1]["api_name"] == "/image_to_3d"
    assert os.path.isfile(out) and out.endswith("mesh.glb")


def test_the_concept_image_is_kept_beside_the_mesh(tmp_path, png, glb):
    """A bad mesh must be attributable to a bad IMAGE or a bad lift.

    Without the saved concept, "the generator produced a blob" is unfalsifiable
    between the two stages -- exactly the ambiguity that cost this project a
    full diagnostic wave when a water-bear prompt returned a bear and nothing
    downstream could see it.

    MUST-FAIL INPUT: dropping the concept write makes this assertion fail while
    every other test in this file still passes.
    """
    log = []
    out_dir = tmp_path / "cache"
    prov = _provider({"img/space": png, "mesh/space": glb}, log)
    prov.generate("an octopus", str(out_dir))

    concept = out_dir / "concept.png"
    assert concept.is_file(), sorted(p.name for p in out_dir.iterdir())
    assert concept.stat().st_size > 0


def test_generation_settings_reach_both_spaces(tmp_path, png, glb):
    """seed / steps / guidance must actually be SENT.

    The incumbent provider called `predict(prompt, api_name=...)` and passed
    none of them, so every mesh in project history was drawn at the Space's
    defaults -- one pinned seed, no variation, and three "fresh" draws that
    came back byte-identical. This test exists so that bug cannot recur here.

    MUST-FAIL INPUT: a provider that accepts image_kwargs/mesh_kwargs and then
    drops them on the floor -- the arg tuples below would be short.
    """
    log = []
    prov = _provider({"img/space": png, "mesh/space": glb}, log,
                     image_kwargs={"seed": 7, "num_inference_steps": 4},
                     mesh_kwargs={"seed": 11, "target_face_num": 2000})
    prov.generate("a lizard", str(tmp_path / "cache"))

    assert log[0]["args"] == ("a lizard", 7, 4)
    assert log[1]["args"] == (_file_arg(png), 11, 2000)


# ---------------------------------------------------------------------------
# failure attribution -- WHICH stage broke
# ---------------------------------------------------------------------------

def test_a_quota_error_names_the_stage_that_hit_it(tmp_path, png, glb):
    """Two GPU Spaces means two quota walls; the message must say which.

    MUST-FAIL INPUT: a shared error string that says only "quota exhausted"
    passes any is-it-a-RuntimeError check but leaves the operator unable to
    tell a dead image Space from a dead mesh Space.
    """
    quota = RuntimeError("You have exceeded your free ZeroGPU quota "
                         "(60s requested vs. 0s left)")

    log = []
    prov = _provider({"img/space": quota, "mesh/space": glb}, log)
    with pytest.raises(RuntimeError, match="image") as first:
        prov.generate("x", str(tmp_path / "a"))
    assert "quota" in str(first.value).lower()

    log = []
    prov = _provider({"img/space": png, "mesh/space": quota}, log)
    with pytest.raises(RuntimeError, match="mesh") as second:
        prov.generate("x", str(tmp_path / "b"))
    assert "quota" in str(second.value).lower()

    assert str(first.value) != str(second.value)


def test_a_quota_error_is_not_retried(tmp_path, glb):
    """Retrying an exhausted quota burns wall-clock and cannot succeed.

    MUST-FAIL INPUT: a provider that treats quota like any other transient
    error records 3 calls here instead of 1.
    """
    quota = RuntimeError("exceeded your free ZeroGPU quota (0s left)")
    log = []
    prov = _provider({"img/space": quota, "mesh/space": glb}, log, attempts=3)
    with pytest.raises(RuntimeError):
        prov.generate("x", str(tmp_path / "cache"))
    assert len(log) == 1, log


def test_a_failed_mesh_stage_leaves_the_concept_image_as_evidence(
        tmp_path, png):
    """When stage 2 dies, the image stage 1 produced is the only evidence of
    how far the run got. Deleting it on failure destroys the diagnosis.

    MUST-FAIL INPUT: a cleanup handler that removes out_dir on error.
    """
    log = []
    out_dir = tmp_path / "cache"
    prov = _provider({"img/space": png,
                      "mesh/space": RuntimeError("boom")}, log, attempts=1)
    with pytest.raises(RuntimeError):
        prov.generate("an octopus", str(out_dir))
    assert (out_dir / "concept.png").is_file()


def test_an_empty_image_never_reaches_the_mesh_stage(tmp_path, glb):
    """A zero-byte concept means stage 1 failed quietly; lifting it would turn
    that into a mysterious mesh failure one stage later.

    MUST-FAIL INPUT: no emptiness check -- the mesh Space gets called with a
    0-byte file and the log below has 2 entries.
    """
    empty = tmp_path / "empty.png"
    empty.write_bytes(b"")
    log = []
    prov = _provider({"img/space": str(empty), "mesh/space": glb}, log,
                     attempts=1)
    with pytest.raises(RuntimeError, match="image"):
        prov.generate("x", str(tmp_path / "cache"))
    assert [c["space"] for c in log] == ["img/space"]


# ---------------------------------------------------------------------------
# wiring
# ---------------------------------------------------------------------------

def test_get_provider_resolves_the_two_stage_name(monkeypatch):
    monkeypatch.setenv("MESH_PROVIDER", "hf2")
    prov = mesh_acquire.get_provider()
    assert isinstance(prov, mesh_acquire.TwoStageProvider)
    assert prov.image_space and prov.mesh_space


def test_an_unknown_provider_name_still_raises_and_lists_hf2(monkeypatch):
    """MUST-FAIL INPUT: adding a provider without listing it leaves the error
    message lying about what is valid."""
    with pytest.raises(ValueError, match="hf2"):
        mesh_acquire.get_provider("no-such-provider")


def test_the_two_stage_spaces_are_overridable_by_env(monkeypatch):
    monkeypatch.setenv("MESH_PROVIDER", "hf2")
    monkeypatch.setenv("HF_IMAGE_SPACE_ID", "someone/other-image")
    monkeypatch.setenv("HF_MESH_SPACE_ID", "someone/other-mesh")
    prov = mesh_acquire.get_provider()
    assert prov.image_space == "someone/other-image"
    assert prov.mesh_space == "someone/other-mesh"


def test_the_cache_key_separates_hf2_from_hf():
    """Same prompt, different provider, MUST be a different cache entry -- or a
    two-stage draw would silently read back a Shap-E mesh (and vice versa).

    MUST-FAIL INPUT: keying the cache on the prompt alone.
    """
    assert (mesh_acquire.cache_key("hf2", "an octopus")
            != mesh_acquire.cache_key("hf", "an octopus"))


# ---------------------------------------------------------------------------
# argument PLACEMENT -- the slot, not just the value
#
# Added 2026-08-24, when Hunyuan3D-2 became the default lift. Its
# /shape_generation signature is (caption, image, mv_front, mv_back, mv_left,
# mv_right, steps, guidance_scale, seed, octree_resolution, check_box_rembg,
# num_chunks, randomize_seed): the image is SECOND, behind a caption that must
# be sent as None. Prepending -- correct for FLUX, correct for TripoSG -- puts
# the image path in the caption slot and None in the image slot, and the Space
# answers with an error that looks like anything except an argument-order bug.
# ---------------------------------------------------------------------------

def test_the_primary_lands_in_the_slot_the_config_marks(tmp_path, png, glb):
    """MUST-FAIL INPUT (COORDINATION.md 4.1): the pre-2026-08-24 provider,
    which always prepends. It sends ("/.../concept.png", None, STAGE_INPUT,
    30, ...) and the assertion below catches the swap that no live error
    message would have named."""
    log = []
    prov = _provider({"img/space": png, "mesh/space": glb}, log,
                     mesh_kwargs={"caption": None,
                                  "image": mesh_acquire.STAGE_INPUT,
                                  "steps": 30, "randomize_seed": False})
    prov.generate("an octopus", str(tmp_path / "cache"))

    assert log[1]["args"] == (None, _file_arg(png), 30, False)
    # and the sentinel itself must never reach the wire
    assert mesh_acquire.STAGE_INPUT not in log[1]["args"]


def test_without_the_sentinel_the_primary_is_still_prepended(
        tmp_path, png, glb):
    """The sentinel is opt-in. Every Space whose input comes first -- FLUX,
    TripoSG, Stable Fast 3D -- must keep working untouched.

    MUST-FAIL INPUT: making the sentinel mandatory silently drops the primary
    for all three of them."""
    log = []
    prov = _provider({"img/space": png, "mesh/space": glb}, log,
                     mesh_kwargs={"seed": 11, "target_face_num": 2000})
    prov.generate("a lizard", str(tmp_path / "cache"))
    assert log[1]["args"] == (_file_arg(png), 11, 2000)


def test_a_none_argument_is_not_mistaken_for_the_sentinel(
        tmp_path, png, glb):
    """Hunyuan sends a GENUINE None for `caption`. A sentinel implemented as
    None -- or as any magic value -- would fill that slot with the image and
    ship two copies of it.

    MUST-FAIL INPUT: `if v is None` in place of `if v is STAGE_INPUT`."""
    log = []
    prov = _provider({"img/space": png, "mesh/space": glb}, log,
                     mesh_kwargs={"caption": None,
                                  "image": mesh_acquire.STAGE_INPUT,
                                  "mv_image_front": None})
    prov.generate("x", str(tmp_path / "cache"))
    assert log[1]["args"] == (None, _file_arg(png), None)
    assert log[1]["args"].count(_file_arg(png)) == 1


# ---------------------------------------------------------------------------
# reading the RESULT -- Hunyuan hides the glb under "value"
# ---------------------------------------------------------------------------

def test_a_gradio_filedata_under_value_is_found(tmp_path):
    """VERBATIM from a live /shape_generation call, 2026-08-24.

    `_candidate_paths` read only ("path", "name"), so on this exact result it
    yielded ['Success'] -- the STATUS STRING -- and the provider raised "no
    usable glb" while holding a perfectly good one.

    MUST-FAIL INPUT: the two-key version. It is not a hypothetical; it is what
    shipped, and it made the default lift unwireable.
    """
    mesh = tmp_path / "white_mesh.glb"
    mesh.write_bytes(b"glTF\x02\x00\x00\x00" + b"\x00" * 64)
    result = [{"value": str(mesh), "visible": True}, "Success", {}, 1234.0]

    found = mesh_acquire.TwoStageProvider._first_existing(result, (".glb",))
    assert found == str(mesh)


def test_a_nested_filedata_under_value_is_found(tmp_path):
    """Gradio serialises FileData differently across component versions; the
    same Space family emits {"value": {"path": ...}} too."""
    mesh = tmp_path / "m.glb"
    mesh.write_bytes(b"glTF" + b"\x00" * 40)
    result = [{"value": {"path": str(mesh)}}, "Success"]
    assert mesh_acquire.TwoStageProvider._first_existing(
        result, (".glb",)) == str(mesh)


# ---------------------------------------------------------------------------
# the shipped default
# ---------------------------------------------------------------------------

def test_hf2_defaults_to_the_lift_that_was_measured_working(monkeypatch):
    """TripoSG was the first default and is DEAD -- a contentless AppError on
    every endpoint, its own /run_segmentation included. Hunyuan3D-2 is the one
    lift that has actually produced a mesh through this class."""
    monkeypatch.setenv("MESH_PROVIDER", "hf2")
    prov = mesh_acquire.get_provider()
    assert prov.mesh_space == "tencent/Hunyuan3D-2"
    assert prov.mesh_api == "/shape_generation"
    # and it must carry Hunyuan's ARGUMENT LAYOUT, not just its address
    assert prov.mesh_kwargs.get("image") is mesh_acquire.STAGE_INPUT
    assert prov.mesh_kwargs.get("randomize_seed") is False


def test_redirecting_the_mesh_space_drops_hunyuans_argument_layout(monkeypatch):
    """HUNYUAN_SHAPE_KWARGS is one Space's signature and nobody else's.

    MUST-FAIL INPUT: attaching it unconditionally. An operator who points
    HF_MESH_SPACE_ID at TRELLIS then sends thirteen Hunyuan-shaped arguments to
    a Space with a different signature, and the failure names neither.
    """
    monkeypatch.setenv("MESH_PROVIDER", "hf2")
    monkeypatch.setenv("HF_MESH_SPACE_ID", "someone/other-mesh")
    prov = mesh_acquire.get_provider()
    assert prov.mesh_kwargs == {}


def test_the_image_stage_sends_a_PROMPT_and_the_mesh_stage_sends_a_FILE(
        tmp_path, png, glb):
    """The two stages take different KINDS of primary, and conflating them
    breaks whichever one you get wrong.

    Stage 1's primary is a prompt string; wrapping it in handle_file would try
    to open "an octopus" as a file. Stage 2's primary is a path; NOT wrapping
    it is the 2026-08-24 bug that made the default lift unusable and got
    reported as quota exhaustion.

    MUST-FAIL INPUT (COORDINATION.md 4.1): wrapping both, or neither.
    """
    log = []
    prov = _provider({"img/space": png, "mesh/space": glb}, log)
    prov.generate("an octopus", str(tmp_path / "cache"))

    assert log[0]["args"][0] == "an octopus"          # raw string
    assert isinstance(log[1]["args"][0], dict)        # FileData mapping
    assert log[1]["args"][0]["meta"]["_type"] == "gradio.FileData"


def test_an_app_level_error_does_not_claim_to_be_a_quota_reading(
        tmp_path, png):
    """MUST-FAIL INPUT: the pre-2026-08-24 message, which said "free GPU quota
    exhausted" for any AppError. It said exactly that for a client-side
    serialization bug on a Space with quota to spare -- and on that basis
    VAST-AI/TripoSG was written off as a dead Space."""
    from gradio_client import exceptions as gc_exc

    log = []
    prov = _provider({"img/space": png,
                      "mesh/space": gc_exc.AppError(message="boom")},
                     log, attempts=1)
    with pytest.raises(RuntimeError) as err:
        prov.generate("x", str(tmp_path / "cache"))

    msg = str(err.value)
    assert "app-level" in msg
    assert "NOT a quota reading" in msg
    assert "exhausted" not in msg
    assert "view_api" in msg          # says what to actually check


def test_an_existing_concept_skips_the_image_stage_when_asked(
        tmp_path, png, glb):
    """Stage 2 is the half that keeps failing, so retries are the common case.

    MUST-FAIL INPUT (COORDINATION.md 4.1): no reuse -- `log` carries an
    img/space call and every retry costs a second 60-90s GPU draw to reproduce
    a picture already on disk.
    """
    out_dir = tmp_path / "cache"
    out_dir.mkdir()
    (out_dir / "concept.png").write_bytes(open(png, "rb").read())

    log = []
    prov = _provider({"mesh/space": glb}, log, reuse_concept=True)
    out = prov.generate("an octopus", str(out_dir))

    assert [c["space"] for c in log] == ["mesh/space"]
    assert log[0]["args"][0] == _file_arg(str(out_dir / "concept.png"))
    assert out.endswith("mesh.glb")


def test_reuse_is_opt_in(tmp_path, png, glb):
    """Default OFF: a silent stage-1 cache would let a stale concept pass as a
    fresh draw, which is the attribution loss this provider exists to prevent."""
    out_dir = tmp_path / "cache"
    out_dir.mkdir()
    (out_dir / "concept.png").write_bytes(open(png, "rb").read())
    log = []
    prov = _provider({"img/space": png, "mesh/space": glb}, log)
    prov.generate("x", str(out_dir))
    assert [c["space"] for c in log] == ["img/space", "mesh/space"]


def test_an_empty_existing_concept_is_not_reused(tmp_path, png, glb):
    """A 0-byte concept is a failed stage 1, not a cache hit. Reusing it would
    lift an empty file and turn a quiet failure into a mystery one stage on --
    the same trap `test_an_empty_image_never_reaches_the_mesh_stage` guards."""
    out_dir = tmp_path / "cache"
    out_dir.mkdir()
    (out_dir / "concept.png").write_bytes(b"")
    log = []
    prov = _provider({"img/space": png, "mesh/space": glb}, log,
                     reuse_concept=True)
    prov.generate("x", str(out_dir))
    assert [c["space"] for c in log] == ["img/space", "mesh/space"]


# ---------------------------------------------------------------------------
# the concept prompt (2026-10-07)
#
# Measured: the bare word gave 0/5 usable Hunyuan meshes on dog/whale/spider/
# beetle/mouse at pinned seeds -- FLUX drew head-and-shoulders portraits and
# scenes, and the lift built the water, the web and the flower into the mesh.
# Hunyuan3D-1's own text_to_image suffix (", white background, 3D style, best
# quality") gave 3/5 and turned "mouse" into a COMPUTER mouse on both seeds.
# CONCEPT_PROMPT_TEMPLATE gave 5/5 with every leg and tail separated.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw, subject", [
    ("dog", "dog"),
    ("a dog", "dog"),
    ("An octopus", "octopus"),
    ("the whale.", "whale"),
    ("  a lizard with a long tail  ", "lizard with a long tail"),
    ("antelope", "antelope"),          # an article PREFIX, not an article
    ("theropod", "theropod"),
])
def test_concept_prompt_names_the_subject_once_without_its_article(
        raw, subject):
    """MUST-FAIL INPUT: formatting the raw prompt in, which sends "A full-body
    3D render of a single a dog" -- and stripping "an"/"the" as bare prefixes,
    which turns "antelope" into "telope"."""
    out = mesh_acquire.concept_prompt(raw)
    assert out == mesh_acquire.CONCEPT_PROMPT_TEMPLATE.format(subject=subject)


def test_the_template_asks_for_what_the_lift_and_the_tree_need():
    """The phrases that moved 0/5 to 5/5. Dropping "animal" is what let the
    suffix arm read "mouse" as a computer mouse; dropping the background is
    what put the sea into the whale."""
    t = mesh_acquire.CONCEPT_PROMPT_TEMPLATE.lower()
    for phrase in ("full-body", "single", "entire animal", "every leg",
                   "tail", "separated", "white background"):
        assert phrase in t


def test_a_template_reaches_the_image_stage_and_not_the_mesh_stage(
        tmp_path, png, glb):
    """MUST-FAIL INPUT: a template stored on the provider but never applied --
    stage 1 still receives the bare "a dog"."""
    log = []
    prov = _provider({"img/space": png, "mesh/space": glb}, log,
                     prompt_template=mesh_acquire.CONCEPT_PROMPT_TEMPLATE)
    prov.generate("a dog", str(tmp_path / "cache"))

    assert log[0]["args"][0] == mesh_acquire.concept_prompt("a dog")
    assert log[1]["args"][0] == _file_arg(png)


def test_hf2_sends_the_templated_prompt_with_a_pinned_flux_seed(monkeypatch):
    """FLUX.1-schnell /infer is (prompt, seed, randomize_seed, width, height,
    num_inference_steps) and randomize_seed defaults to TRUE: left alone, two
    draws of "dog" differ in breed, crop and background, while the lift's seed
    is already pinned at 1234.

    MUST-FAIL INPUT: the pre-2026-10-07 wiring, image_kwargs == {}.
    """
    monkeypatch.setenv("MESH_PROVIDER", "hf2")
    monkeypatch.delenv("HF_IMAGE_SPACE_ID", raising=False)
    prov = mesh_acquire.get_provider()
    assert prov.prompt_template == mesh_acquire.CONCEPT_PROMPT_TEMPLATE
    assert list(prov.image_kwargs) == ["seed", "randomize_seed", "width",
                                       "height", "num_inference_steps"]
    assert prov.image_kwargs["randomize_seed"] is False


def test_redirecting_the_image_space_drops_fluxs_argument_layout(monkeypatch):
    """Same rule as the mesh stage: FLUX_IMAGE_KWARGS is one Space's
    signature. The template is plain text and any text-to-image Space takes it.
    """
    monkeypatch.setenv("MESH_PROVIDER", "hf2")
    monkeypatch.setenv("HF_IMAGE_SPACE_ID", "someone/other-image")
    prov = mesh_acquire.get_provider()
    assert prov.image_kwargs == {}
    assert prov.prompt_template == mesh_acquire.CONCEPT_PROMPT_TEMPLATE


# ---------------------------------------------------------------------------
# cache_settings -- what the cache key must name (2026-10-07)
# ---------------------------------------------------------------------------

def test_hf2_declares_json_safe_cache_settings(monkeypatch):
    """STAGE_INPUT is an object; it must reach the key as a stable string or
    json.dumps raises on the first acquire."""
    import json
    monkeypatch.setenv("MESH_PROVIDER", "hf2")
    s = mesh_acquire.get_provider().cache_settings
    assert json.loads(json.dumps(s)) == s
    assert s["image_kwargs"]["seed"] == mesh_acquire.FLUX_IMAGE_KWARGS["seed"]
    assert s["prompt_template"] == mesh_acquire.CONCEPT_PROMPT_TEMPLATE
    assert s["mesh_kwargs"]["image"] == "<stage input>"


@pytest.mark.parametrize("change", [
    {"prompt_template": "a {subject}"},
    {"image_kwargs": {"seed": 22}},
    {"mesh_kwargs": {"steps": 50}},
    {"image_space": "other/img"},
    {"mesh_space": "other/mesh"},
])
def test_everything_that_shapes_the_mesh_moves_cache_settings(change):
    """MUST-FAIL INPUT: settings that omit the template or a stage's kwargs --
    the exact staleness the fingerprint exists to end."""
    base = dict(prompt_template=mesh_acquire.CONCEPT_PROMPT_TEMPLATE,
                image_kwargs={"seed": 11}, mesh_kwargs={"steps": 30})
    a = mesh_acquire.TwoStageProvider(**base)
    b = mesh_acquire.TwoStageProvider(**{**base, **change})
    assert a.cache_settings != b.cache_settings


def test_transport_knobs_do_not_move_cache_settings():
    """Retries, backoff, the token and concept reuse change how a mesh is
    fetched, not which mesh it is. Keying on them would turn a retry tweak
    into a full re-draw."""
    a = mesh_acquire.TwoStageProvider(token="t1", attempts=3)
    b = mesh_acquire.TwoStageProvider(token="t2", attempts=5,
                                      backoff=(1.0,), reuse_concept=True)
    assert a.cache_settings == b.cache_settings


def test_a_subject_description_fills_the_template_subject_slot(tmp_path, png, glb):
    """Mesh review (2026-10-11): the VLM's rewrite replaces only {subject}; the
    measured template around it is unchanged."""
    log = []
    p = _provider({"img/space": png, "mesh/space": glb}, log,
                  prompt_template=mesh_acquire.CONCEPT_PROMPT_TEMPLATE,
                  subject_description="bull moose, four long well-separated legs")
    p.generate("a moose", str(tmp_path / "out"))
    sent = log[0]["args"][0]
    assert sent == mesh_acquire.concept_prompt("bull moose, four long well-separated legs")
    assert sent.startswith("A full-body 3D render of a single bull moose, four long")


def test_the_description_enters_the_cache_settings_only_when_set(png, glb):
    plain = _provider({}, [], prompt_template=mesh_acquire.CONCEPT_PROMPT_TEMPLATE)
    assert "subject_description" not in plain.cache_settings
    d = _provider({}, [], prompt_template=mesh_acquire.CONCEPT_PROMPT_TEMPLATE,
                  subject_description="bull moose")
    assert d.cache_settings["subject_description"] == "bull moose"
