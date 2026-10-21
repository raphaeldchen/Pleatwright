# HuggingFace Mesh Provider (free text-to-3D) — Design

**Date:** 2026-06-25
**Branch:** `feat/huggingface-mesh-provider`
**Status:** approved (brainstorm), pending spec review

---

## 1. Purpose

Add a free text-to-3D backend so the prompt→mesh→tree pipeline can generate
meshes for *novel* subjects without paying a hosted vendor (Meshy). The provider
is a drop-in third `MeshProvider` that calls a Gradio ZeroGPU Space (free, GPU-time
quota) and returns a `.glb`, identical in contract to the existing providers.

Context: Meshy requires a paid subscription. Claude/Gemini chat plans do not offer
programmatic text-to-3D. Hugging Face ZeroGPU Spaces host open text-to-3D models
(e.g. Hunyuan3D) callable for free (~2 min GPU/day anonymous, ~5 min/day with a
free HF token), which is ample for one mesh per query.

## 2. Background: the existing provider seam

`mesh_acquire.py` already abstracts mesh generation behind a `MeshProvider`
protocol (`generate(prompt, out_dir) -> glb_path`), with `get_provider(name)`
resolving by name / `MESH_PROVIDER` env. Current providers: `FakeMeshProvider`
(offline fixtures, default for tests/CI), `MeshyProvider` (hosted REST, opt-in).
`MeshyProvider` establishes the patterns this slice reuses:

- network call wrapped to raise `RuntimeError` with the prompt on failure;
- result downloaded/copied to `out_dir/mesh.glb`;
- empty/missing output rejected loudly;
- an injection seam (`http=`) so unit tests run offline; one opt-in live smoke.

Nothing downstream of `generate` changes: `acquire_mesh` caches by
`(provider_name, prompt)`, and `query_to_metric_tree` /
`reference_tree_from_query` consume the `.glb` unchanged.

## 3. Why a Gradio Space (not plain REST)

ZeroGPU Spaces use a queue + Server-Sent-Events protocol (POST to start, stream
events, download a returned file handle), not Meshy's plain request/poll REST.
Reimplementing that protocol with stdlib `urllib` is brittle; the supported client
(`gradio_client`) handles queue, auth, and file download in a few calls. **Decision
(user-approved): use `gradio_client`**, accepting it as a new dependency. It is a
moderate pure-Python dep (pulls `huggingface_hub`, `httpx`), not heavy like the
existing `torch`/`skeletor`/`sklearn` stack.

## 4. Component: `HuggingFaceProvider`

In `mesh_acquire.py`, a sibling to `MeshyProvider`:

```python
class HuggingFaceProvider:
    def __init__(self, *, space_id=DEFAULT_HF_SPACE, api_name=DEFAULT_HF_API,
                 token=None, client_factory=None): ...
    def generate(self, prompt: str, out_dir: str) -> str: ...
```

Behavior of `generate`:
1. Build a client via `client_factory(space_id, token)` (default factory wraps
   `gradio_client.Client(space_id, hf_token=token)`; `gradio_client` is a **lazy
   import inside the default factory** so `fake`/`meshy`/CI paths never import it).
2. Call the text-to-3D endpoint (`client.predict(prompt, api_name=api_name)`),
   yielding a local temp `.glb` path (gradio_client downloads the result file).
3. `os.makedirs(out_dir)`, copy the temp file to `out_dir/mesh.glb`, return it.

Configuration:
- `space_id` — default `DEFAULT_HF_SPACE` (a Hunyuan3D text-to-3D Space),
  overridable via env `HF_SPACE_ID`. Spaces are community-hosted and can go
  down/change, so this is config, not a hardcode.
- `api_name` — the Gradio endpoint name for the text→mesh function, default
  `DEFAULT_HF_API`, overridable via env `HF_API_NAME`. The exact value is confirmed
  at implementation time via `gradio_client`'s `.view_api()` against the live Space.
- `token` — from env `HF_TOKEN`, optional. Present → authenticated ~5 min/day
  ZeroGPU quota; absent → anonymous shared pool. Both function.

The provider codes to **one** Space's signature (YAGNI — single user, single
default). A differently-shaped Space set via `HF_SPACE_ID` may need an `api_name`
override or a small code tweak; this is documented, not abstracted into a generic
multi-Space adapter.

## 5. Wiring & configuration

- `get_provider`: add an `"hf"` branch returning `HuggingFaceProvider()` (reading
  `HF_SPACE_ID`/`HF_API_NAME`/`HF_TOKEN` from env). Extend the unknown-name error
  message to list `fake, meshy, hf`.
- `acquire_mesh` already names the cache dir by provider; `hf` caches under its own
  key automatically — no change.
- `fake` remains the default for `MESH_PROVIDER` everywhere (tests, CI, the MCP
  tool's offline default). `hf` is opt-in via `MESH_PROVIDER=hf`, mirroring `meshy`.
- `reference_demo.py` and the `reference_tree_from_query` MCP tool already read
  `MESH_PROVIDER`; no code change, only documentation of `MESH_PROVIDER=hf`.

## 6. Error handling (fail loud, per project convention)

`generate` wraps the client interaction and raises `RuntimeError` naming the prompt
and `space_id` when:
- the client cannot be built or the Space call raises (unreachable, Space error,
  quota exhausted);
- the result is not a usable file path (unexpected return shape);
- the produced `.glb` is missing or zero bytes.

`acquire_mesh`'s existing empty-file guard is the backstop. No silent fallbacks: an
`hf` failure surfaces, it does not quietly drop to `fake`.

## 7. Testing

- **Offline unit tests** (new, in `tests/test_mesh_acquire.py`, mirroring the Meshy
  tests):
  - inject a fake `client_factory` whose `predict` returns a committed fixture
    `.glb`; assert `generate` copies it to `out_dir/mesh.glb` and returns that path;
  - error paths: client/predict raises → `RuntimeError`; predict returns a missing
    or empty file → `RuntimeError`;
  - `get_provider("hf")` returns a `HuggingFaceProvider`;
  - the unknown-provider error lists `hf`.
- **One opt-in live smoke** gated by an env flag (e.g. `RUN_HF_SMOKE=1`), skipped by
  default like the existing meshy smoke: real Space call → non-empty `.glb`. This is
  the check that a live Space exists and the `api_name` is correct.
- Determinism/CI: all default-run tests stay offline; no new network or GPU cost in
  the suite. Current suite is 182 passed / 2 skipped; expect roughly +5 tests and
  +1 skip.
- Dependency: add `gradio_client` to the project requirements file.

## 8. Out of scope

- Concept-art / image-to-3D (Option 3) — not now.
- Any change to mesh extraction, the feasibility gate, or the agent prompt.
- A generic multi-Space adapter framework.
- Making `hf` the default provider — `fake` stays default; `hf` is opt-in.

## 9. Constraints carried over

- Tests in `mcp_harness/tests/`, run from inside `mcp_harness/` via
  `.venv/bin/python -m pytest`.
- Fail loud with specific messages.
- Extraction/agent-side fixes only; TreeMaker/Oriedita engine behavior is fixed.
- Secrets (`HF_TOKEN`) live in the shell env, never committed.

## 10. Implementation-time verification (not design unknowns)

- Confirm the default Space's text-to-3D endpoint `api_name` and argument order via
  `gradio_client.Client(space_id).view_api()`.
- Confirm the default Space is currently live; if not, pick a live equivalent and
  set `DEFAULT_HF_SPACE` / `DEFAULT_HF_API` accordingly. The env overrides and the
  smoke test exist precisely to absorb Space churn.
