"""The files the browser build ships as py.zip: the Python that runs in Pyodide, nothing else.

Paths are repo-relative, so that `pleatwright_app/__init__.py`'s `../../../mcp_harness`
path insert resolves unchanged inside the unzipped tree. Globs are expanded here,
at import time and sorted, so RUNTIME is a plain list of concrete files.
"""
import glob
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# the top-level mcp_harness modules the app reaches at runtime, through gated_pipeline and mesh_acquire
_HARNESS_MODULES = (
    "layout_explain", "tree_contract", "env_config", "gated_pipeline", "tree_authoring",
    "vlm_render", "pair_fusion", "llm_client", "mesh_acquire", "mesh_ratings",
    "subject_rewrite", "gemini_image",
)

_PATTERNS = (
    "mcp_harness/pleatwright/**/*.py",
    *(f"mcp_harness/{m}.py" for m in _HARNESS_MODULES),
    "app/server/pleatwright_app/*.py",
    "app/browser/py/mirror.py",
    "app/browser/py/pwbrowser.py",
    "app/browser/py/jobchild.py",
    "mcp_harness/fixtures/full17_v3_sticks/*.json",  # pipeline._source resolves a roll name from these
)


def _expand(patterns):
    out = []
    for pattern in patterns:
        hits = sorted(glob.glob(os.path.join(ROOT, pattern), recursive=True))
        if not hits:
            raise FileNotFoundError(f"runtime pattern matches nothing: {pattern}")
        out.extend(os.path.relpath(h, ROOT).replace(os.sep, "/") for h in hits)
    return out


RUNTIME: list[str] = _expand(_PATTERNS)
