# Query → Rough 3D Mesh Acquisition Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a standalone module that turns a text query into a rough 3D `.glb` via a hosted text-to-3D API (Meshy), then chains it into the existing `auto_mesh_to_metric_tree` pipeline to produce a `MeshTreeResult`.

**Architecture:** A new `mcp_harness/mesh_acquire.py` exposes a swappable `MeshProvider` protocol (mirroring the `LLM_PROVIDER` registry pattern in `llm_client.py`). A `MeshyProvider` does async submit→poll→download over stdlib `urllib`; a `FakeMeshProvider` returns a committed fixture `.glb` for offline tests. `acquire_mesh()` adds a prompt-hash content cache; `query_to_metric_tree()` chains acquisition into the already-built `mesh_to_tree.auto_mesh_to_metric_tree`. Not wired into the agent/MCP.

**Tech Stack:** Python 3.14, stdlib `urllib`/`hashlib`/`shutil`, pytest, existing `mesh_to_tree.py` chain.

## Global Constraints

- Standalone module only — **do NOT** wire into `agent_loop.py` or the MCP server.
- **No new dependencies.** Use stdlib `urllib.request` for HTTP (`requests` is not installed).
- Provider selected by env var `MESH_PROVIDER` (default `"meshy"`); Meshy key in `MESHY_API_KEY`.
- Generated/cached meshes go under `mcp_harness/generated_meshes/` (gitignored), overridable by env `MESH_OUTPUT_DIR`.
- Fail loud with specific messages (match the `mesh_to_tree.py` convention); **no** silent fallback to a fake mesh in the live path.
- Tests live in `mcp_harness/tests/`, run with `mcp_harness/.venv/bin/python -m pytest`.
- All commits run from inside `mcp_harness/` or repo root; current branch is `feat/mesh-acquisition`.

---

### Task 1: MeshProvider protocol + FakeMeshProvider

**Files:**
- Create: `mcp_harness/mesh_acquire.py`
- Test: `mcp_harness/tests/test_mesh_acquire.py`

**Interfaces:**
- Consumes: nothing (new module).
- Produces:
  - `MeshProvider` (typing.Protocol) with `generate(self, prompt: str, out_dir: str) -> str` (returns absolute path to a `.glb`).
  - `FakeMeshProvider(fixture_path: str = DEFAULT_FIXTURE)` implementing `MeshProvider`; copies the fixture into `out_dir` and returns the new path.
  - `DEFAULT_FIXTURE` — absolute path to `mcp_harness/fixtures/quadruped.glb`.

- [ ] **Step 1: Write the failing test**

```python
# mcp_harness/tests/test_mesh_acquire.py
import os

import mesh_acquire as ma


def test_fake_provider_writes_glb_into_out_dir(tmp_path):
    provider = ma.FakeMeshProvider()
    out = provider.generate("a quadruped", str(tmp_path))
    assert os.path.isfile(out)
    assert out.endswith(".glb")
    assert os.path.dirname(out) == str(tmp_path)
    assert os.path.getsize(out) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_mesh_acquire.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'mesh_acquire'`

- [ ] **Step 3: Write minimal implementation**

```python
# mcp_harness/mesh_acquire.py
"""Query -> rough 3D mesh acquisition (sub-project A).

Turns a text prompt into a rough .glb via a hosted text-to-3D API (Meshy),
behind a swappable MeshProvider protocol, then chains it into the existing
mesh_to_tree.auto_mesh_to_metric_tree pipeline. Standalone: NOT wired into the
agent or MCP. See docs/superpowers/specs/2026-06-24-mesh-acquisition-design.md.
"""
from __future__ import annotations

import os
import shutil
from typing import Protocol

_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_FIXTURE = os.path.join(_HERE, "fixtures", "quadruped.glb")


class MeshProvider(Protocol):
    """Turns a text prompt into a .glb on disk and returns its path."""

    def generate(self, prompt: str, out_dir: str) -> str: ...


class FakeMeshProvider:
    """Test/offline provider: copies a committed fixture .glb into out_dir.

    Any valid mesh exercises the downstream chain deterministically; we reuse a
    committed fixture instead of paying a real API or pinning a Meshy artifact.
    """

    def __init__(self, fixture_path: str = DEFAULT_FIXTURE):
        self.fixture_path = fixture_path

    def generate(self, prompt: str, out_dir: str) -> str:
        os.makedirs(out_dir, exist_ok=True)
        dest = os.path.join(out_dir, "mesh.glb")
        shutil.copyfile(self.fixture_path, dest)
        return dest
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_mesh_acquire.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/mesh_acquire.py mcp_harness/tests/test_mesh_acquire.py
git commit -m "feat(mesh): MeshProvider protocol + FakeMeshProvider"
```

---

### Task 2: Provider selection via env (get_provider)

**Files:**
- Modify: `mcp_harness/mesh_acquire.py`
- Test: `mcp_harness/tests/test_mesh_acquire.py`

**Interfaces:**
- Consumes: `FakeMeshProvider`, `MeshProvider` from Task 1.
- Produces:
  - `get_provider(name: str | None = None) -> MeshProvider` — resolves `name` (or env `MESH_PROVIDER`, default `"meshy"`); returns `FakeMeshProvider` for `"fake"`, a `MeshyProvider` (added in Task 4) for `"meshy"`. Raises `ValueError` for unknown names. For `"meshy"`, reads `MESHY_API_KEY` and raises `ValueError` naming it if absent.

- [ ] **Step 1: Write the failing test**

```python
def test_get_provider_fake_selected_by_env(monkeypatch):
    monkeypatch.setenv("MESH_PROVIDER", "fake")
    assert isinstance(ma.get_provider(), ma.FakeMeshProvider)


def test_get_provider_unknown_raises(monkeypatch):
    monkeypatch.setenv("MESH_PROVIDER", "nope")
    import pytest
    with pytest.raises(ValueError, match="unknown MESH_PROVIDER"):
        ma.get_provider()


def test_get_provider_meshy_requires_key(monkeypatch):
    monkeypatch.delenv("MESHY_API_KEY", raising=False)
    import pytest
    with pytest.raises(ValueError, match="MESHY_API_KEY"):
        ma.get_provider("meshy")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_mesh_acquire.py -k get_provider -v`
Expected: FAIL — `AttributeError: module 'mesh_acquire' has no attribute 'get_provider'`

- [ ] **Step 3: Write minimal implementation**

Add to `mcp_harness/mesh_acquire.py`:

```python
def get_provider(name: str | None = None) -> MeshProvider:
    """Resolve a MeshProvider by name (or env MESH_PROVIDER, default 'meshy')."""
    name = name or os.environ.get("MESH_PROVIDER", "meshy")
    if name == "fake":
        return FakeMeshProvider()
    if name == "meshy":
        key = os.environ.get("MESHY_API_KEY", "")
        if not key:
            raise ValueError(
                "provider 'meshy' requires an API key; set MESHY_API_KEY")
        return MeshyProvider(api_key=key)
    raise ValueError(
        f"unknown MESH_PROVIDER {name!r}; valid: fake, meshy")
```

Add a temporary stub so the module imports before Task 4 lands (it is fully replaced in Task 4):

```python
class MeshyProvider:
    """Hosted Meshy text-to-3D provider. Filled in by Task 4."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def generate(self, prompt: str, out_dir: str) -> str:
        raise NotImplementedError("MeshyProvider.generate lands in Task 4")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_mesh_acquire.py -k get_provider -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/mesh_acquire.py mcp_harness/tests/test_mesh_acquire.py
git commit -m "feat(mesh): env-selected get_provider (fake/meshy)"
```

---

### Task 3: Prompt-hash cache + acquire_mesh

**Files:**
- Modify: `mcp_harness/mesh_acquire.py`
- Test: `mcp_harness/tests/test_mesh_acquire.py`

**Interfaces:**
- Consumes: `MeshProvider`, `get_provider` from Tasks 1–2.
- Produces:
  - `output_dir() -> str` — env `MESH_OUTPUT_DIR` or `mcp_harness/generated_meshes/`.
  - `cache_key(provider_name: str, prompt: str) -> str` — `sha256(f"{provider_name}:{prompt}")` hexdigest.
  - `acquire_mesh(prompt: str, *, provider: MeshProvider | None = None, provider_name: str | None = None, cache_dir: str | None = None) -> str` — returns a cached `.glb` if present for the key, else calls `provider.generate` into the per-key dir and returns the path. `provider` (injected) takes precedence; otherwise `get_provider(provider_name)`.

- [ ] **Step 1: Write the failing test**

```python
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
    prov = _CountingProvider(ma.DEFAULT_FIXTURE)
    p1 = ma.acquire_mesh("a quadruped", provider=prov,
                         provider_name="fake", cache_dir=str(tmp_path))
    p2 = ma.acquire_mesh("a quadruped", provider=prov,
                         provider_name="fake", cache_dir=str(tmp_path))
    assert p1 == p2
    assert prov.calls == 1  # second call served from cache
    assert os.path.isfile(p1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_mesh_acquire.py -k "cache or acquire" -v`
Expected: FAIL — `AttributeError: module 'mesh_acquire' has no attribute 'cache_key'`

- [ ] **Step 3: Write minimal implementation**

Add to `mcp_harness/mesh_acquire.py` (add `import hashlib` at top):

```python
def output_dir() -> str:
    return os.environ.get("MESH_OUTPUT_DIR", os.path.join(_HERE, "generated_meshes"))


def cache_key(provider_name: str, prompt: str) -> str:
    return hashlib.sha256(f"{provider_name}:{prompt}".encode()).hexdigest()


def acquire_mesh(prompt: str, *, provider: MeshProvider | None = None,
                 provider_name: str | None = None,
                 cache_dir: str | None = None) -> str:
    """Return a rough .glb for `prompt`, served from cache when available."""
    name = provider_name or os.environ.get("MESH_PROVIDER", "meshy")
    provider = provider or get_provider(name)
    cache_dir = cache_dir or output_dir()
    key_dir = os.path.join(cache_dir, cache_key(name, prompt))
    cached = os.path.join(key_dir, "mesh.glb")
    if os.path.isfile(cached) and os.path.getsize(cached) > 0:
        return cached
    return provider.generate(prompt, key_dir)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_mesh_acquire.py -k "cache or acquire" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/mesh_acquire.py mcp_harness/tests/test_mesh_acquire.py
git commit -m "feat(mesh): prompt-hash cache + acquire_mesh"
```

---

### Task 4: MeshyProvider (submit → poll → download)

**Files:**
- Modify: `mcp_harness/mesh_acquire.py`
- Test: `mcp_harness/tests/test_mesh_acquire.py`

**Interfaces:**
- Consumes: nothing new.
- Produces:
  - `MeshyProvider(api_key, *, base_url=MESHY_BASE, poll_interval=5.0, timeout=300.0, http=None, sleep=time.sleep)` implementing `MeshProvider`.
  - `http` is any object with `post_json(url, headers, payload) -> dict`, `get_json(url, headers) -> dict`, `download(url, dest_path) -> None`; defaults to `_UrllibHttp()`.
  - Raises `TimeoutError` on poll timeout, `RuntimeError` on `FAILED` status or empty download.

- [ ] **Step 1: Write the failing test**

```python
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
    import pytest
    with pytest.raises(RuntimeError, match="bad"):
        prov.generate("a fox", str(tmp_path))


def test_meshy_provider_timeout_raises(tmp_path):
    http = _FakeHttp(statuses=[{"status": "IN_PROGRESS"}] * 5)
    prov = ma.MeshyProvider("key", poll_interval=0, timeout=0,
                            http=http, sleep=lambda s: None)
    import pytest
    with pytest.raises(TimeoutError, match="task-123"):
        prov.generate("a fox", str(tmp_path))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_mesh_acquire.py -k meshy_provider -v`
Expected: FAIL — `NotImplementedError` (the Task 2 stub) or signature mismatch.

- [ ] **Step 3: Write minimal implementation**

In `mcp_harness/mesh_acquire.py` add imports `import json`, `import time`, `import urllib.request`, and **replace** the Task 2 `MeshyProvider` stub with:

```python
MESHY_BASE = "https://api.meshy.ai/openapi/v2/text-to-3d"


class _UrllibHttp:
    """Minimal stdlib HTTP transport (no `requests` dependency)."""

    def post_json(self, url, headers, payload):
        data = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data, headers={
            **headers, "Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())

    def get_json(self, url, headers):
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read().decode())

    def download(self, url, dest_path):
        with urllib.request.urlopen(url) as r, open(dest_path, "wb") as f:
            shutil.copyfileobj(r, f)


class MeshyProvider:
    """Hosted Meshy text-to-3D: submit a preview task, poll, download the .glb."""

    def __init__(self, api_key, *, base_url=MESHY_BASE, poll_interval=5.0,
                 timeout=300.0, http=None, sleep=time.sleep):
        self.api_key = api_key
        self.base_url = base_url
        self.poll_interval = poll_interval
        self.timeout = timeout
        self.http = http or _UrllibHttp()
        self.sleep = sleep

    def _headers(self):
        return {"Authorization": f"Bearer {self.api_key}"}

    def generate(self, prompt: str, out_dir: str) -> str:
        task_id = self.http.post_json(self.base_url, self._headers(), {
            "mode": "preview", "prompt": prompt, "art_style": "realistic"})["result"]
        deadline = time.monotonic() + self.timeout
        while True:
            status = self.http.get_json(
                f"{self.base_url}/{task_id}", self._headers())
            state = status.get("status")
            if state == "SUCCEEDED":
                break
            if state == "FAILED":
                msg = (status.get("task_error") or {}).get("message", "unknown")
                raise RuntimeError(f"Meshy task {task_id} failed: {msg}")
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    f"Meshy task {task_id} did not complete in {self.timeout}s")
            self.sleep(self.poll_interval)

        glb_url = (status.get("model_urls") or {}).get("glb")
        if not glb_url:
            raise RuntimeError(f"Meshy task {task_id} SUCCEEDED with no glb url")
        os.makedirs(out_dir, exist_ok=True)
        dest = os.path.join(out_dir, "mesh.glb")
        self.http.download(glb_url, dest)
        if not os.path.isfile(dest) or os.path.getsize(dest) == 0:
            raise RuntimeError(f"Meshy task {task_id} produced an empty download")
        return dest
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_mesh_acquire.py -k meshy_provider -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/mesh_acquire.py mcp_harness/tests/test_mesh_acquire.py
git commit -m "feat(mesh): MeshyProvider submit-poll-download over urllib"
```

---

### Task 5: query_to_metric_tree end-to-end

**Files:**
- Modify: `mcp_harness/mesh_acquire.py`
- Test: `mcp_harness/tests/test_mesh_acquire.py`

**Interfaces:**
- Consumes: `acquire_mesh` (Task 3); `mesh_to_tree.auto_mesh_to_metric_tree(path, ...) -> MeshTreeResult` (existing).
- Produces:
  - `query_to_metric_tree(prompt: str, *, provider=None, provider_name=None, cache_dir=None, **auto_kwargs) -> mesh_to_tree.MeshTreeResult` — acquires a mesh, then runs the existing auto-selection chain on it. `**auto_kwargs` forwards to `auto_mesh_to_metric_tree` (e.g. `gate`, `compile_fn`, `voxel_grid`, `prune_grid`, `k`).

- [ ] **Step 1: Write the failing test**

```python
def test_query_to_metric_tree_returns_result(monkeypatch):
    # Use the fake provider (committed fixture) + injected gate/compile_fn so the
    # chain runs with no engine and no network. Mirrors test_auto_mesh_to_tree.
    class _StubGate:
        def predict(self, nodes, pairs):
            return {"verdict": "feasible", "p_pack": 0.9}

    def _stub_compile(nodes, pairs):
        return '{"vertices_coords": []}'  # non-ERROR, contains the FOLD marker

    res = ma.query_to_metric_tree(
        "a quadruped", provider=ma.FakeMeshProvider(), provider_name="fake",
        gate=_StubGate(), compile_fn=_stub_compile)
    import mesh_to_tree as m2t
    assert isinstance(res, m2t.MeshTreeResult)
    assert res.confirmed is True
    assert len(res.nodes) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_mesh_acquire.py -k query_to_metric_tree -v`
Expected: FAIL — `AttributeError: module 'mesh_acquire' has no attribute 'query_to_metric_tree'`

- [ ] **Step 3: Write minimal implementation**

Add to `mcp_harness/mesh_acquire.py` (add `import mesh_to_tree` at top):

```python
def query_to_metric_tree(prompt: str, *, provider=None, provider_name=None,
                         cache_dir=None, **auto_kwargs):
    """End-to-end: text prompt -> rough mesh -> MeshTreeResult.

    Acquires a rough .glb for `prompt`, then runs the existing closed-loop
    auto-selection chain on it. Extra kwargs forward to auto_mesh_to_metric_tree.
    """
    glb = acquire_mesh(prompt, provider=provider, provider_name=provider_name,
                       cache_dir=cache_dir)
    return mesh_to_tree.auto_mesh_to_metric_tree(glb, **auto_kwargs)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_mesh_acquire.py -k query_to_metric_tree -v`
Expected: PASS

- [ ] **Step 5: Run the full module test file**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_mesh_acquire.py -v`
Expected: PASS (all tests from Tasks 1–5)

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/mesh_acquire.py mcp_harness/tests/test_mesh_acquire.py
git commit -m "feat(mesh): query_to_metric_tree end-to-end chain"
```

---

### Task 6: gitignore, demo `__main__`, opt-in live smoke test

**Files:**
- Modify: `.gitignore`
- Modify: `mcp_harness/mesh_acquire.py`
- Test: `mcp_harness/tests/test_mesh_acquire.py`

**Interfaces:**
- Consumes: `query_to_metric_tree` (Task 5).
- Produces: a `__main__` block printing the result summary for a prompt; a live smoke test skipped unless `MESHY_API_KEY` is set.

- [ ] **Step 1: Add the generated-mesh dir to .gitignore**

Append to `.gitignore`:

```
# Generated meshes (text-to-3D output / cache — never commit)
mcp_harness/generated_meshes/
```

- [ ] **Step 2: Write the opt-in live smoke test**

Add to `mcp_harness/tests/test_mesh_acquire.py`:

```python
def test_live_meshy_smoke(tmp_path):
    """Opt-in: only runs when MESHY_API_KEY is set. Validates the real vendor."""
    import pytest
    if not os.environ.get("MESHY_API_KEY"):
        pytest.skip("MESHY_API_KEY not set; skipping live Meshy smoke")
    path = ma.acquire_mesh("a simple fox", provider_name="meshy",
                           cache_dir=str(tmp_path))
    assert os.path.isfile(path) and os.path.getsize(path) > 0
```

- [ ] **Step 3: Run the test file to confirm the smoke test skips cleanly**

Run: `cd mcp_harness && .venv/bin/python -m pytest tests/test_mesh_acquire.py -v`
Expected: PASS, with `test_live_meshy_smoke` reported as SKIPPED.

- [ ] **Step 4: Add the demo `__main__`**

Append to `mcp_harness/mesh_acquire.py`:

```python
if __name__ == "__main__":
    import sys
    prompt = " ".join(sys.argv[1:]) or "a quadruped animal"
    result = query_to_metric_tree(prompt)
    print(f"prompt: {prompt!r}")
    print(f"confirmed: {result.confirmed}")
    print(f"nodes: {len(result.nodes)}  pairs: {len(result.pairs)}")
    print(f"voxel_res: {result.voxel_res}  prune_fraction: {result.prune_fraction}")
```

- [ ] **Step 5: Run the full repo suite to confirm no regressions**

Run: `cd mcp_harness && .venv/bin/python -m pytest -q`
Expected: PASS (existing suite + new `test_mesh_acquire.py`); only `test_live_meshy_smoke` SKIPPED.

- [ ] **Step 6: Commit**

```bash
git add .gitignore mcp_harness/mesh_acquire.py mcp_harness/tests/test_mesh_acquire.py
git commit -m "feat(mesh): gitignore generated meshes, demo main, live smoke test"
```

---

## Self-Review

**Spec coverage:**
- Acquisition method (Meshy, hosted, swappable) → Tasks 2, 4. ✓
- `MeshProvider` protocol + `MeshyProvider` + `FakeMeshProvider` → Tasks 1, 2, 4. ✓
- Env selection `MESH_PROVIDER`/`MESHY_API_KEY` → Task 2. ✓
- Async submit→poll→download with timeout → Task 4. ✓
- Output dir `generated_meshes/` (gitignored, env-overridable) → Tasks 3, 6. ✓
- Prompt-hash cache → Task 3. ✓
- `query_to_metric_tree` end-to-end → Task 5. ✓
- Error handling (missing key, API/timeout/FAILED, empty download, no silent fallback) → Tasks 2, 4. ✓
- Testing: FakeMeshProvider full-chain, MeshyProvider mocked HTTP, opt-in live smoke → Tasks 1/3/5, 4, 6. ✓
- No new deps (stdlib urllib) → Task 4. ✓
- Not wired into agent/MCP → respected throughout. ✓

**Placeholder scan:** No TBD/TODO; every code step has full code; the Task 2 `MeshyProvider` stub is explicitly a placeholder that Task 4 replaces in full (called out in both tasks). ✓

**Type consistency:** `generate(prompt, out_dir) -> str` consistent across `FakeMeshProvider`, `MeshyProvider`, `_CountingProvider`. `acquire_mesh`/`query_to_metric_tree` signatures match their callers in tests. `MeshTreeResult` fields (`confirmed`, `nodes`, `pairs`, `voxel_res`, `prune_fraction`) match `mesh_to_tree.py`. ✓
