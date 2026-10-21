"""Root conftest: add mcp_harness/ to sys.path so the suite can import
pleatwright, llm_client, mesh_acquire, etc. when pytest is run from the
project root (`make test` runs it from mcp_harness/ and does not need this)."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "mcp_harness"))
