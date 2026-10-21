# Follow-ups: Web UI slice + foldability frontier

Captured 2026-06-26, after the `feat/web-ui-thin-slice` branch and a live `"bear"`
run through the new UI. None of these block the web-UI slice from merging; they
are the known gaps to schedule next. Grouped by area, with rough priority.

## A. Foldability / engine (surfaced by the "bear" run)

The `"bear"` prompt ran the full pipeline (mesh-reference → feasibility gate →
TreeMaker compile → Oriedita lint → `find_free_paper`). It compiled at
`scale=0.615` and the lint returned **10 geometry/Kawasaki violations, 0
M/V-fixable**. That signature is the documented **hull-vs-square frontier**:
TreeMaker creases only the convex hull of the leaf nodes (`tmTree.cpp:2723-2734`,
per `mcp_harness/free_paper.py` docstring); paper outside the hull is uncreased,
and Oriedita reads the hull boundary as interior vertices that can't satisfy
Kawasaki. This is expected TreeMaker behavior, not an engine defect — but the
surrounding tooling handled it badly.

1. **[High] `find_free_paper` crashes when the leaf hull is fully interior.**
   `mcp_harness/free_paper.py:144-145` assumes a scale-optimized base where some
   flap tips reach the paper edge, then walks the perimeter between hull and
   sheet. The bear packed with the entire leaf hull interior to the square (no
   tip on any edge), so the perimeter walk had no anchor and it raised
   `ValueError("hull vertex ... is interior to the paper")` instead of reporting
   the free regions. The design-signal tool should handle "free paper on all four
   sides," not just corners. *Fix:* generalize the free-region computation for the
   hull-entirely-interior case (free paper = sheet minus interior hull polygon).

   **RESOLVED 2026-06-27** (branch `feat/hull-frontier-agent-fixes`). When any
   hull vertex is interior, `free_paper_regions` now returns a single
   `kind="frame"` region — the sheet minus the interior hull, exposed via a new
   `hole` field — instead of raising. The all-on-boundary perimeter-walk path
   (corner/edge-strip) is untouched; the mixed case (some tips on an edge, some
   interior) routes to the frame branch too. See
   `docs/superpowers/specs/2026-06-27-hull-frontier-fixes-design.md`.

2. **[High] The agent misreads the hull-frontier lint signature.** On this lint
   failure the agent's summary contradicted itself ("usable as-is" *and*
   "FAILED… add flaps or accept") and it called `find_free_paper` on a
   non-scale-optimized base (triggering #1). Teach the system prompt to recognize
   *0 M/V-fixable + hull-boundary Kawasaki = expected hull frontier* and to (a)
   not invent mountain/valley remedies, (b) not call `find_free_paper` unless the
   base is scale-optimized. Relevant memory: the "Agent orchestrator (Tier 2)"
   and "Molecule topology" notes already flagged this teaching gap.

   **RESOLVED 2026-06-27** (branch `feat/hull-frontier-agent-fixes`). Reshaped by
   A-3=ACCEPT (item 3): the `SYSTEM_PROMPT` "free-paper frontier" block now leads
   with *the base folds cleanly as-is — accept is the default correct outcome*,
   keeps the "don't invent causes / don't propose remedies that can't help / don't
   spend retries" guidance, and reframes `find_free_paper` as an **optional**
   detail-flap report (now crash-proof per #1) rather than a required step. The
   self-contradiction is gone.

3. **[Medium] Open product question: accept vs. fill uncreased paper.** Uncreased
   regions are physically foldable (flat paper stays flat), so the Kawasaki
   "failures" at hull-boundary points may be Oriedita *false-negatives* for this
   class. Decide the product behavior: accept uncreased regions as valid, or fill
   them. *Best evidence:* load the base into the WebGL viewport (see B-3) and see
   whether it physically folds despite the lint complaints. Resolve this BEFORE
   investing in any corner/detail-filling engine.

   **RESOLVED 2026-06-27 → ACCEPT.** The embedded Origami Simulator viewport
   (vendored in `feat/origami-viewport-embed`) was used to fold the exact
   hull-frontier base: a deterministic, offline reproduction of the bear
   (`scale=0.615440`, perturbed) via `scripts/make_hull_frontier_fixture.py`,
   committed at `web/frontend/public/simulator/assets/ide/bear-base.fold`. Oriedita
   lints it as **10 Kawasaki violations, 0 M/V-fixable, all "geometry"** — the
   documented hull frontier. Driven to 100% fold through the bridge's real
   `loadFold`/`setFold` postMessage path, the GPU solver relaxed it to a **stable,
   bounded, genuinely 3D base** (out-of-plane extent ≈0.32 of the model size, **0
   NaN/exploded vertices, no error emitted**); see `docs/a3-bear-base-folded.png`.
   A flat sheet folding cleanly means the uncreased paper outside the leaf hull
   stays flat, so those hull-boundary Kawasaki "failures" are **Oriedita
   false-negatives** for this class. **Decision: accept uncreased regions as
   valid.** Item 5 / A-9 (generative fill) is therefore optional aesthetic polish,
   **not** a correctness fix — do not gate foldability on filling the hull frontier.

   **REFINEMENT 2026-06-27 (root-caused via a user e2e bear run).** The viewport
   shows the unfolded paper as a *polygon, not a square*. Confirmed root cause: the
   engine creases only the convex hull of the leaf nodes (`tmTree.cpp` ~2733:
   *"insuring that the convex hull of the nodes is entirely filled with valid
   polygons"*), and `TreemakerWrapper.cpp::ExportFold` faithfully emits only the
   vertices/creases TreeMaker built — so the uncreased square *corners are omitted
   from the `.fold` entirely* (committed `bear-base.fold`: border is a convex
   20-gon = 42% of the sheet; the corner 58% is absent; only 1 of 4 square corners
   is a vertex). So A-3=ACCEPT is sound for *foldability*, but the pipeline
   currently **drops** the corner paper rather than rendering it as flat uncreased
   faces — the artifact is a hull crease pattern, not a square. **Not a bug / not
   broken math** (the base is valid; a base also legitimately doesn't resemble the
   animal — shaping is out of scope). *Deferred fix direction* (user chose to
   proceed with hygiene first): enhance `ExportFold` to also emit the 4 paper
   corners + border + uncreased corner regions as flat faces (faithful, no invented
   creases; reuses the A-1 frame-region geometry). Overlaps A-9.

## B. Web UI slice (from the final whole-branch review)

4. **[Low] Unbounded `asyncio.Queue` in the bridge.** `web/server.py` drains an
   unbounded queue with no backpressure. Fine while `MAX_AGENT_STEPS` bounds a
   turn and it's single-user/local; revisit only for a hosted/multi-user
   deployment. (Mid-turn disconnect was already fixed in `bcd5a81`.)

5. **[Medium] Live end-to-end browser smoke not yet run.** Every automated test
   passes, but the real streaming-UI → live-LLM → `.fold` path has only been
   exercised once manually (the bear run above, which revealed A-1/A-2). Run the
   documented smoke in `web/README.md` with a real key against a few prompts and
   record results.

6. **[Low] `fastapi.testclient` emits a `StarletteDeprecationWarning` (httpx).**
   Third-party deprecation, not our code, but it makes `web/tests` output
   non-pristine. Pin/migrate when convenient (the warning suggests `httpx2`).

7. **[Low] `python-dotenv` is not in any dependency manifest.** `env_config.py`
   imports it optionally; it happens to be installed in the dev venv. Add it to a
   manifest (e.g. alongside `web/requirements.txt`) so a fresh `.venv` has it and
   the bring-your-own-key loading actually works.

   **RESOLVED 2026-06-27** (branch `feat/config-hygiene-c8-b7`): added
   `python-dotenv>=1.0` to `web/requirements.txt`.

## C. Config consistency (pre-existing, noticed during .env work)

8. **[Medium] `MESH_PROVIDER` default is inconsistent.** `mcp_harness/server.py:450`
   defaults to `"fake"`, but the `mcp_harness/mesh_acquire.py` factory defaults to
   `"meshy"` (a paid provider). Depending on the entry point, an unset
   `MESH_PROVIDER` behaves differently. *Fix:* unify to `"fake"` everywhere.

   **RESOLVED 2026-06-27** (branch `feat/config-hygiene-c8-b7`): `get_provider`
   now defaults to `"fake"` (code + docstring), matching `server.py`; pinned by
   `test_get_provider_defaults_to_fake_when_env_unset`.

## D. Future direction (not a bug — needs its own brainstorm)

9. **Generative anatomy-detail engine.** Make `find_free_paper` *generative*: turn
   a free-paper region into new tree nodes + edge geometry (added detail flaps),
   recompile, and re-verify — closing a detect→fill→re-verify loop. The bear shows
   the free paper is not always in the corners, so frame this as **"generative
   anatomy detail,"** not "fill corners." This is a meaty, research-y feature with
   real design questions (what flap, where, aesthetic intent); brainstorm before
   building, and only after resolving A-3 (accept vs. fill). Relevant memory:
   "Free-paper flap-filling idea."
