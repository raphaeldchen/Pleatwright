"""acquire_mesh's optional progress callback (app spec §4.3 hook 4)."""
import os

import mesh_acquire
from test_two_stage_provider import _provider, png, glb  # noqa: F401  (fixtures)


def _record():
    calls = []
    return calls, lambda kind, path: calls.append((kind, path and os.path.basename(path)))


def test_two_stage_reports_the_concept_before_the_mesh_space_is_called(tmp_path, png, glb):
    log, (calls, progress) = [], _record()

    def mesh_space(*a):
        assert calls == [("image", "concept.png")]     # image reported BEFORE stage 2
        return glb
    prov = _provider({"img/space": png, "mesh/space": mesh_space}, log)
    out = mesh_acquire.acquire_mesh("an octopus", provider=prov, provider_name="hf2",
                                    cache_dir=str(tmp_path / "c"), progress=progress)
    assert calls == [("image", "concept.png"), ("mesh", "mesh.glb")]
    assert out.endswith("mesh.glb")


def test_cache_hit_reports_the_cached_concept_and_mesh(tmp_path, png, glb):
    prov = _provider({"img/space": png, "mesh/space": glb}, [])
    kw = dict(provider=prov, provider_name="hf2", cache_dir=str(tmp_path / "c"))
    mesh_acquire.acquire_mesh("an octopus", **kw)
    calls, progress = _record()
    mesh_acquire.acquire_mesh("an octopus", progress=progress, **kw)
    assert calls == [("image", "concept.png"), ("mesh", "mesh.glb")]


def test_a_provider_without_progress_reports_no_concept(tmp_path):
    calls, progress = _record()
    mesh_acquire.acquire_mesh("a bird", provider=mesh_acquire.FakeMeshProvider(),
                              provider_name="fake", cache_dir=str(tmp_path / "c"),
                              progress=progress)
    assert calls == [("image", None), ("mesh", "mesh.glb")]


def test_no_callback_behaves_as_before(tmp_path, png, glb):
    prov = _provider({"img/space": png, "mesh/space": glb}, [])
    out = mesh_acquire.acquire_mesh("an octopus", provider=prov, provider_name="hf2",
                                    cache_dir=str(tmp_path / "c"))
    assert os.path.isfile(out)


def test_a_provider_without_progress_reports_the_image_step_before_generating(tmp_path):
    """So the UI's image step does not spin through the whole (slow) mesh generation."""
    calls, progress = _record()

    class Slow(mesh_acquire.FakeMeshProvider):
        def generate(self, prompt, out_dir):               # no `progress` parameter
            assert calls == [("image", None)]
            return super().generate(prompt, out_dir)
    mesh_acquire.acquire_mesh("a bird", provider=Slow(), provider_name="fake",
                              cache_dir=str(tmp_path / "c"), progress=progress)
    assert calls == [("image", None), ("mesh", "mesh.glb")]
