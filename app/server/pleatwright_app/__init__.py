"""The Pleatwright app server (spec docs/superpowers/specs/2026-10-07-pleatwright-app-design.md)."""
import os
import sys

_HARNESS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "mcp_harness"))
if _HARNESS not in sys.path:
    sys.path.insert(0, _HARNESS)
