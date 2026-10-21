"""App server tests. Trees come only from the 51 artifact trees (owner rule)."""
import os
import sys

import pytest

os.environ.setdefault("IDE_MESH_PROVENANCE", "0")   # never write into sibling caches
_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
for p in (os.path.join(_REPO, "app", "server"), os.path.join(_REPO, "mcp_harness"),
          os.path.join(_REPO, "mcp_harness", "tests")):
    if p not in sys.path:
        sys.path.insert(0, p)


@pytest.fixture
def offline(tmp_path, monkeypatch):
    """Fake mesh provider into tmp, fake mesh-view renderer (as tests/test_cli.py)."""
    import gated_pipeline as GP
    import mesh_acquire
    from test_gated_pipeline import _fake_mesh_views
    monkeypatch.setenv("MESH_PROVIDER", "fake")
    # a developer's .env may set it, and create_app's load_env leaks .env into
    # os.environ for the rest of the session; library tests set their own
    monkeypatch.delenv("MESH_LIBRARY_DIR", raising=False)
    # ...and a GEMINI_API_KEY there would switch hf2's image stage (spec 2026-10-19)
    for v in ("GEMINI_API_KEY", "MESH_IMAGE_BACKEND", "GEMINI_IMAGE_MODEL"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setattr(mesh_acquire, "output_dir", lambda: str(tmp_path / "meshes"))
    monkeypatch.setattr(GP.vlm_render, "render_mesh_views",
                        lambda *a, **k: _fake_mesh_views(tmp_path))
    return tmp_path


def pytest_configure(config):
    # third-party: starlette's TestClient nags about httpx (pinned in requirements)
    config.addinivalue_line(
        "filterwarnings", "ignore:Using `httpx` with `starlette.testclient`:UserWarning")
