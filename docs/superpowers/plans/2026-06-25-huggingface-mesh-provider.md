# HuggingFace Mesh Provider Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a free text-to-3D `MeshProvider` (`HuggingFaceProvider`) that calls a Gradio ZeroGPU Space and returns a `.glb`, as an opt-in drop-in beside the existing Meshy provider.

**Architecture:** New `HuggingFaceProvider` class in `mesh_acquire.py`, sibling to `MeshyProvider`. It calls a Space via `gradio_client`, extracts the returned `.glb`, and copies it to `out_dir/mesh.glb` — same contract as every other provider, so nothing downstream changes. A `client_factory` injection seam keeps unit tests offline; one opt-in live smoke validates a real Space. Wired into `get_provider` under name `"hf"`; `fake` stays the default everywhere.

**Tech Stack:** Python 3.14, `gradio_client` (new dependency), pytest. All in `mcp_harness/`.

## Global Constraints

- Tests live in `mcp_harness/tests/`, run from inside `mcp_harness/` via `.venv/bin/python -m pytest`.
- Fail loud with specific error messages (include the prompt and `space_id`).
- No silent provider fallback: an `hf` failure raises, it does not drop to `fake`.
- `fake` remains the default for `MESH_PROVIDER` (tests, CI, the MCP tool); `hf` is opt-in via `MESH_PROVIDER=hf`, mirroring `meshy`.
- Secrets (`HF_TOKEN`) come from the shell env, never committed.
- There is no dependency manifest file; new deps are installed into `mcp_harness/.venv` and documented in the module docstring.
- Default-run test suite stays fully offline (no network/GPU). Current suite: 182 passed, 2 skipped.

---

### Task 1: `HuggingFaceProvider` class + offline unit tests

**Files:**
- Modify: `mcp_harness/mesh_acquire.py` (add constants, default factory, and the class after `MeshyProvider`, before `get_provider`)
- Test: `mcp_harness/tests/test_mesh_acquire.py` (append)

**Interfaces:**
- Consumes: nothing new (uses stdlib `os`, `shutil` already imported in `mesh_acquire.py`).
- Produces:
  - `DEFAULT_HF_SPACE: str`, `DEFAULT_HF_API: str` (module constants)
  - `HuggingFaceProvider(*, space_id=DEFAULT_HF_SPACE, api_name=DEFAULT_HF_API, token=None, client_factory=None)` with `.generate(prompt: str, out_dir: str) -> str` (returns path to `out_dir/mesh.glb`), and attributes `.space_id`, `.api_name`, `.token`, `.client_factory`.
  - The default `client_factory` lazily imports `gradio_client` (only used on a real call).

- [ ] **Step 1: Install the new dependency into the venv**

Run from `mcp_harness/`:
```bash
.venv/bin/pip install gradio_client
```
Expected: installs `gradio_client` (and `huggingface_hub`, `httpx`) successfully. Verify:
```bash
.venv/bin/python -c "import gradio_client; print(gradio_client.__version__)"
```
Expected: prints a version string.

- [ ] **Step 2: Write the failing tests**

Append to `mcp_harness/tests/test_mesh_acquire.py`:
```python
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
    client = _FakeGradioClient(result=ma.DEFAULT_FIXTURE)
    prov = ma.HuggingFaceProvider(client_factory=_hf_factory(client))
    out = prov.generate("a fox", str(tmp_path))
    assert os.path.isfile(out) and os.path.getsize(out) > 0
    assert out == os.path.join(str(tmp_path), "mesh.glb")
    assert client.predicted[0] == ("a fox",)          # prompt passed positionally
    assert client.predicted[1] == ma.DEFAULT_HF_API    # via api_name=


def test_hf_provider_extracts_glb_from_tuple(tmp_path):
    import filecmp
    client = _FakeGradioClient(result=("a text label", ma.DEFAULT_FIXTURE))
    prov = ma.HuggingFaceProvider(client_factory=_hf_factory(client))
    out = prov.generate("a fox", str(tmp_path))
    assert filecmp.cmp(out, ma.DEFAULT_FIXTURE, shallow=False)


def test_hf_provider_call_failure_raises(tmp_path):
    client = _FakeGradioClient(result=None, raises=True)
    prov = ma.HuggingFaceProvider(client_factory=_hf_factory(client))
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run from `mcp_harness/`:
```bash
.venv/bin/python -m pytest tests/test_mesh_acquire.py -k hf_provider -v
```
Expected: FAIL/ERROR with `AttributeError: module 'mesh_acquire' has no attribute 'HuggingFaceProvider'`.

- [ ] **Step 4: Implement the provider**

In `mcp_harness/mesh_acquire.py`, insert after the `MeshyProvider` class (and before `def get_provider`):
```python
DEFAULT_HF_SPACE = "tencent/Hunyuan3D-2"
DEFAULT_HF_API = "/generation_all"  # verify via gradio_client Client(space).view_api()


def _default_hf_client_factory(space_id, token):
    from gradio_client import Client  # lazy: only needed for a real hf call
    return Client(space_id, hf_token=token)


class HuggingFaceProvider:
    """Free text-to-3D via a Gradio ZeroGPU Space; downloads and returns a .glb.

    Codes to one Space's signature. Point HF_SPACE_ID/HF_API_NAME at another Space
    to switch; a differently-shaped Space may need an api_name override.
    """

    def __init__(self, *, space_id=DEFAULT_HF_SPACE, api_name=DEFAULT_HF_API,
                 token=None, client_factory=None):
        self.space_id = space_id
        self.api_name = api_name
        self.token = token
        self.client_factory = client_factory or _default_hf_client_factory

    @staticmethod
    def _candidate_paths(result):
        """Yield path-like strings from a gradio_client result (str/tuple/dict)."""
        if isinstance(result, str):
            yield result
        elif isinstance(result, (list, tuple)):
            for item in result:
                yield from HuggingFaceProvider._candidate_paths(item)
        elif isinstance(result, dict):
            for key in ("path", "name"):
                v = result.get(key)
                if isinstance(v, str):
                    yield v

    def generate(self, prompt: str, out_dir: str) -> str:
        try:
            client = self.client_factory(self.space_id, self.token)
            result = client.predict(prompt, api_name=self.api_name)
        except Exception as e:
            raise RuntimeError(
                f"HuggingFace Space {self.space_id!r} failed for prompt "
                f"{prompt!r}: {e}") from e
        cands = list(self._candidate_paths(result))
        src = next((p for p in cands if p.endswith(".glb") and os.path.isfile(p)),
                   None)
        src = src or next((p for p in cands if os.path.isfile(p)), None)
        if not src or os.path.getsize(src) == 0:
            raise RuntimeError(
                f"HuggingFace Space {self.space_id!r} returned no usable glb for "
                f"prompt {prompt!r}: {result!r}")
        os.makedirs(out_dir, exist_ok=True)
        dest = os.path.join(out_dir, "mesh.glb")
        shutil.copyfile(src, dest)
        return dest
```

- [ ] **Step 5: Run tests to verify they pass**

Run from `mcp_harness/`:
```bash
.venv/bin/python -m pytest tests/test_mesh_acquire.py -k hf_provider -v
```
Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/mesh_acquire.py mcp_harness/tests/test_mesh_acquire.py
git commit -m "feat(mesh): HuggingFaceProvider free text-to-3D via Gradio Space"
```

---

### Task 2: Wire `hf` into `get_provider` + env config

**Files:**
- Modify: `mcp_harness/mesh_acquire.py` (the `get_provider` function)
- Test: `mcp_harness/tests/test_mesh_acquire.py` (append)

**Interfaces:**
- Consumes: `HuggingFaceProvider`, `DEFAULT_HF_SPACE`, `DEFAULT_HF_API` from Task 1.
- Produces: `get_provider("hf")` / `MESH_PROVIDER=hf` returns a `HuggingFaceProvider` configured from env `HF_SPACE_ID`, `HF_API_NAME`, `HF_TOKEN`.

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_mesh_acquire.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run from `mcp_harness/`:
```bash
.venv/bin/python -m pytest tests/test_mesh_acquire.py -k "get_provider_hf or unknown_lists_hf" -v
```
Expected: FAIL — `get_provider` raises `ValueError: unknown MESH_PROVIDER 'hf'` (and the unknown-lists-hf test fails because the message lacks `hf`).

- [ ] **Step 3: Implement the wiring**

In `mcp_harness/mesh_acquire.py`, in `get_provider`, add the `hf` branch before the final `raise`, and update the error message. The function becomes:
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
    if name == "hf":
        return HuggingFaceProvider(
            space_id=os.environ.get("HF_SPACE_ID", DEFAULT_HF_SPACE),
            api_name=os.environ.get("HF_API_NAME", DEFAULT_HF_API),
            token=os.environ.get("HF_TOKEN") or None,
        )
    raise ValueError(
        f"unknown MESH_PROVIDER {name!r}; valid: fake, meshy, hf")
```

- [ ] **Step 4: Run tests to verify they pass**

Run from `mcp_harness/`:
```bash
.venv/bin/python -m pytest tests/test_mesh_acquire.py -k "get_provider or unknown" -v
```
Expected: all pass (the existing `test_get_provider_unknown_raises` still matches `"unknown MESH_PROVIDER"`).

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/mesh_acquire.py mcp_harness/tests/test_mesh_acquire.py
git commit -m "feat(mesh): wire hf provider into get_provider with env config"
```

---

### Task 3: Opt-in live smoke + docs

**Files:**
- Modify: `mcp_harness/mesh_acquire.py` (module docstring — document providers + the `gradio_client` dependency)
- Modify: `mcp_harness/reference_demo.py` (docstring — add `MESH_PROVIDER=hf` usage)
- Test: `mcp_harness/tests/test_mesh_acquire.py` (append the smoke)

**Interfaces:**
- Consumes: `acquire_mesh(prompt, provider_name="hf", cache_dir=...)` (existing), Task 2 wiring.
- Produces: a skipped-by-default live test gated on `RUN_HF_SMOKE`.

- [ ] **Step 1: Write the smoke test**

Append to `mcp_harness/tests/test_mesh_acquire.py`:
```python
def test_live_hf_smoke(tmp_path):
    """Opt-in: runs only when RUN_HF_SMOKE is set. Validates a real Space."""
    if not os.environ.get("RUN_HF_SMOKE"):
        pytest.skip("RUN_HF_SMOKE not set; skipping live HuggingFace smoke")
    path = ma.acquire_mesh("a simple fox", provider_name="hf",
                           cache_dir=str(tmp_path))
    assert os.path.isfile(path) and os.path.getsize(path) > 0
```

- [ ] **Step 2: Verify it skips by default**

Run from `mcp_harness/`:
```bash
.venv/bin/python -m pytest tests/test_mesh_acquire.py::test_live_hf_smoke -v
```
Expected: 1 skipped (reason: "RUN_HF_SMOKE not set ...").

- [ ] **Step 3: Document the provider + dependency**

In `mcp_harness/mesh_acquire.py`, replace the module docstring's first paragraph so it lists the providers and the dependency. New docstring top:
```python
"""Query -> rough 3D mesh acquisition (sub-project A).

Turns a text prompt into a rough .glb behind a swappable MeshProvider protocol,
then chains it into mesh_to_tree.auto_mesh_to_metric_tree. Providers (MESH_PROVIDER):
  fake  - offline committed fixtures (default; tests/CI, no spend)
  meshy - hosted Meshy text-to-3D REST (needs MESHY_API_KEY)
  hf    - free Gradio ZeroGPU Space text-to-3D (needs `pip install gradio_client`;
          configurable via HF_SPACE_ID / HF_API_NAME; optional HF_TOKEN for the
          authenticated free quota)
See docs/superpowers/specs/2026-06-25-huggingface-mesh-provider-design.md.
"""
```

- [ ] **Step 4: Document the demo usage**

In `mcp_harness/reference_demo.py`, add an `hf` example line to the usage block in the module docstring, after the `meshy` example:
```python
    # free real generation (Gradio Space; needs gradio_client; HF_TOKEN optional):
    MESH_PROVIDER=hf .venv/bin/python reference_demo.py "a simple fox"
```

- [ ] **Step 5: Run the full suite**

Run from `mcp_harness/`:
```bash
.venv/bin/python -m pytest -q
```
Expected: no failures. Baseline was 182 passed / 2 skipped; now ~191 passed / 3 skipped (the new hf smoke adds the one extra skip). Confirm against the printed summary.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/mesh_acquire.py mcp_harness/reference_demo.py mcp_harness/tests/test_mesh_acquire.py
git commit -m "test(mesh): opt-in live hf smoke + provider/dep docs"
```

---

## Post-implementation (manual, by the user — not a task)

Verifying a live Space requires the network and is the user's call (free, but uses their HF quota). To run the live smoke and confirm the default Space + `api_name`:
```bash
cd mcp_harness
RUN_HF_SMOKE=1 HF_TOKEN=<your_token> .venv/bin/python -m pytest tests/test_mesh_acquire.py::test_live_hf_smoke -v -s
```
If the default Space/api_name is stale, point `HF_SPACE_ID`/`HF_API_NAME` at a live text-to-3D Space (confirm its endpoint with `python -c "from gradio_client import Client; Client('<space>').view_api()"`). End-to-end through the agent tool:
```bash
MESH_PROVIDER=hf HF_TOKEN=<your_token> .venv/bin/python reference_demo.py "a red fox"
```
