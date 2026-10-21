"""Suite-wide isolation from the developer's Gemini settings.

`env_config.load_env` (called by the app's create_app and the CLI) copies the
repo-root .env into os.environ for the rest of a test session, and the owner's
.env has a GEMINI_API_KEY. `get_provider("hf2")` picks its image backend from
that key (spec 2026-10-19-nano-banana-image-stage-design.md §1), so without
this the FLUX assertions would flip to Gemini depending on test order. Tests
that want Gemini set these explicitly.
"""
import pytest

_GEMINI_IMAGE_ENV = ("GEMINI_API_KEY", "MESH_IMAGE_BACKEND", "GEMINI_IMAGE_MODEL")


@pytest.fixture(autouse=True)
def _no_ambient_gemini_image_env(monkeypatch):
    for name in _GEMINI_IMAGE_ENV:
        monkeypatch.delenv(name, raising=False)
