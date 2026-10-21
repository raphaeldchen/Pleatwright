# Query → Rough 3D Mesh Acquisition (Sub-project A) — Design

**Date:** 2026-06-24
**Status:** Approved (design); pending implementation plan
**Scope:** Add the missing *front* of the mesh pipeline — turn a text query into a
rough 3D mesh via a hosted text-to-3D API, then feed that mesh into the existing
`auto_mesh_to_metric_tree` chain. Standalone module (demo `__main__` + tests),
**not** wired into the agent/MCP. **Out of scope:** user-facing 3D preview, agent-
as-reference integration, agent/MCP wiring — each is its own later slice.

## Motivation

The original intent of the 3D-model idea was twofold: (1) give the **user** a rough
3D preview of what the finished origami would look like, to approve or amend before
any tree is built (CLAUDE.md Steps 1–3), and (2) give the **AI agent** a concrete
reference to measure when drafting the Metric Tree, instead of guessing anatomy
from text.

The existing mesh pipeline (`mesh_to_tree.py`, the 2026-06-16 POC) built the *back*
half of this — Stage [B] skeleton extraction + Stage [C] skeleton→tree — but only
for a **provided** mesh, with no agent and no acquisition. Stage [A] (acquire a 3D
mesh from a query) was explicitly deferred as "the heavy, swappable external
dependency."

Both original goals depend on [A]: nothing can be previewed or measured until a
model is generated. [A] is also the riskiest remaining unknown — *will a cheap
hosted text-to-3D mesh skeletonize into a foldable tree at all?* This sub-project
de-risks exactly that, headlessly, before any UI is committed.

## Pipeline decomposition

```
[A] Acquire a 3D mesh        -- text query -> rough .glb           (NEW, this slice)
[B] Extract a skeleton       -- mesh -> joints + lengths           (BUILT: mesh_to_tree.py)
[C] Map skeleton -> tree     -- topology + proportions + symmetry  (BUILT: mesh_to_tree.py)
[D] Compile -> lint -> fold   -- ALREADY BUILT
```

This slice is **[A], validated end-to-end through the existing [B]+[C]+[D]**.

## Acquisition method (chosen)

**Hosted text→3D API**, default **Meshy** (mature REST API with a text-to-3D
endpoint returning a downloadable `.glb`). Chosen over a local open model
(TripoSR / Shap-E / Hunyuan3D: heavy weights, usually GPU, and most are image→3D
not text→3D — the same overkill that ruled out RigNet in the POC) and over a
two-stage text→image→3D chain (truer to CLAUDE.md Step 1 and yields a bonus concept
image, but two external dependencies; deferred until the UI needs the image).

The fidelity bar is deliberately **low**: `load_mesh` already voxel-remeshes any
input into a single watertight manifold to tolerate fragmented real-world `.glb`
assets, so "rough" preview-quality geometry is sufficient — and is what the
skeletonizer wants. For this slice we use only Meshy's **preview** stage (rough
geometry), skipping the costlier "refine" stage.

The vendor sits behind a `MeshProvider` protocol, mirroring the existing
`LLM_PROVIDER` pattern in `agent_loop.py` (default provider, env-selected,
swappable, mockable).

## Architecture & data flow

```
query string
  -> acquire_mesh(prompt)            [NEW]   hosted text->3D (Meshy) -> rough .glb on disk
  -> auto_mesh_to_metric_tree(glb)   [BUILT] skeleton -> tree -> gate -> compile-to-FOLD
  -> MeshTreeResult                  [BUILT] confirmed tree + trace
```

`auto_mesh_to_metric_tree` already *always* returns a `MeshTreeResult`
(`confirmed=True` with a FOLD-verified tree, or `confirmed=False` best-effort with
a trace), so a valid-but-unpackable generated mesh is a normal result, not an
error.

## Components

A new standalone module `mcp_harness/mesh_acquire.py`:

```
MeshProvider (Protocol)         generate(prompt: str, out_dir: str) -> str   # glb path
MeshyProvider(MeshProvider)     submit text-to-3D job -> poll -> download .glb
FakeMeshProvider(MeshProvider)  returns a committed fixture .glb (tests/offline/CI)
get_provider()                  env-selected: MESH_PROVIDER (default "meshy"), key MESHY_API_KEY
acquire_mesh(prompt, ...)       pick provider -> cache check -> generate -> return glb path
query_to_metric_tree(prompt)    end-to-end: acquire_mesh -> auto_mesh_to_metric_tree -> MeshTreeResult
```

### Vendor detail: asynchronous generation

Meshy's text-to-3D is asynchronous. `MeshyProvider.generate` performs:

1. `POST` create preview task -> returns a task id.
2. Poll task status until `SUCCEEDED` (with a timeout and a bounded poll interval).
3. Download `model_urls.glb` to disk.

A timeout or any non-`SUCCEEDED` terminal status fails loud with the task id.

## Output & caching

`acquire_mesh` writes the `.glb` to a configurable directory (default a gitignored
`mcp_harness/generated_meshes/`, overridable by env — consistent with how the gate
artifact and `captured.jsonl` are env-gated).

A content cache avoids re-paying for identical prompts:

```
cache key = sha256(provider_name + ":" + prompt)
  hit  -> return cached .glb (no API call)
  miss -> provider.generate() -> save under cache key + out_dir -> return path
```

Plain file-existence check, no database. This makes re-runs free/instant and gives
the live smoke test a stable artifact.

## Error handling

Each failure surfaces loud and specific (matching the POC convention):

- **Missing key** — clear error naming `MESHY_API_KEY`, raised only when the live
  provider is actually selected (`FakeMeshProvider` needs no key).
- **API / network errors** — wrapped with provider + prompt context; **no** silent
  fallback to a fake mesh.
- **Job timeout / non-`SUCCEEDED` status** — explicit "generation did not complete
  in N s" including the task id.
- **Empty / corrupt download** — detected and failed before handing to the pipeline.
- **Downstream** — already handled: `auto_mesh_to_metric_tree` returns a
  `MeshTreeResult` (`confirmed=False` if nothing packs), so an unpackable mesh is a
  normal traced result, not an exception.

## Testing

- **`FakeMeshProvider` + a committed fixture `.glb`** drives the full
  `query_to_metric_tree` chain deterministically, offline, free — the bulk of
  coverage. Asserts provider selection, cache hit/miss behavior, and that the chain
  yields a `MeshTreeResult`.
- **`MeshyProvider` unit tests** mock the HTTP layer (submit -> poll -> download) so
  the async polling, timeout, and error paths are exercised without network.
- **One opt-in live smoke test**, skipped unless `MESHY_API_KEY` is set (mirrors the
  existing live Groq smoke) — validates the real vendor manually; never blocks CI.

Pin any nondeterminism; assert structural properties, not exact coordinates.

## Dependencies

An HTTP client for the Meshy REST API (`requests`, or reuse whatever the venv
already provides). No new heavy ML/geometry dependencies — Stage [B]/[C] deps
(`trimesh`, `skeletor`, `networkx`, `numpy`, `scipy`) are already installed.

## Explicitly out of scope (YAGNI)

- User-facing 3D preview / viewport (needs the not-yet-existent frontend tier).
- Agent-as-reference loop (agent measuring the generated model semantically).
- Agent / MCP-tool wiring of acquisition.
- Meshy "refine" stage / high-fidelity output.
- Two-stage text->image->3D and the concept-image artifact.
- Multi-provider support beyond the single swappable default.
