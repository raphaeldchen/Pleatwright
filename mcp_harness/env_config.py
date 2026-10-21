"""Load environment variables from the repo-root .env file (if present).

The VLM authoring path and the mesh providers read their API keys and
configuration straight from os.environ -- see llm_client.PROVIDERS and
mesh_acquire.get_provider. This module loads a repo-root `.env` into os.environ
ONCE, as early as possible, so running the app no longer requires manually
exporting every key.

Design:
  * python-dotenv is an OPTIONAL import. If it isn't installed (e.g. a minimal
    CI job that only runs the offline suite), loading is a silent no-op instead
    of a hard failure -- nothing here is required for correctness, only for
    convenience. Install it with `pip install python-dotenv`.
  * Real environment variables WIN. load_dotenv(override=False) never clobbers a
    value already exported in the shell, so
    `ANTHROPIC_API_KEY=... python -m pleatwright author ...` still overrides the .env, and the test suite's env stays immune to a stray
    .env on disk.
"""
from __future__ import annotations

import os

# Repo root is the parent of this package directory (mcp_harness/).
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ENV_PATH = os.path.join(_REPO_ROOT, ".env")

_LOADED = False


def load_env() -> bool:
    """Load the repo-root .env into os.environ once.

    Returns True if a .env was found and loaded, False otherwise (dotenv
    missing or no .env file). Idempotent: safe to call from every entry point.
    """
    global _LOADED
    if _LOADED:
        return True
    _LOADED = True  # set first so a failed import never retries on every call

    try:
        from dotenv import load_dotenv
    except ImportError:
        return False

    if os.path.exists(_ENV_PATH):
        load_dotenv(_ENV_PATH, override=False)
        return True
    return False
