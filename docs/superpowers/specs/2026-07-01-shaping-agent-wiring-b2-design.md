# Design: Shaping Agent Wiring (Pillar B — B2)

**Status:** Approved design, ready for implementation planning.
**Date:** 2026-07-01
**Parent docs:** `2026-06-30-finished-model-view-research.md` (Pillar B) and
`2026-07-01-shaping-tracer-b1-b3-b4-design.md` (the tracer this cycle promotes).
The tracer (PR #20, merged) proved B1+B3+B4: `shaping.reverse_fold` as a pure FOLD
transform applied at the display boundary, selected by the `IDE_SHAPE_OP` env var,
validated by the browser-side p90 strain oracle.

---

## 1. Goal

Replace the env-var placeholder with the real B2 loop: the agent maps **anatomy to
shaping ops** via a new MCP tool, with human-in-the-loop suggest-then-confirm, and
the confirmed ops travel with the fold to the display boundary.

Success demo (live, Groq llama): compile the dog; user says "bend its head down";
the agent proposes a plan in plain language; user confirms; the agent calls
`apply_shaping_ops`; the Model tab renders the posed base as thick lit paper. With
no shaping requested, and with `IDE_SHAPE_OP` unset, behavior is byte-identical to
today.

## 2. Decisions made in this cycle

| Question | Decision |
|---|---|
| Success bar | Live chat demo on Groq (plus the test suite). |
| Oracle loop | **Open loop.** The agent's feedback is the tool's geometric pre-validation (per-op verdicts from the real `reverse_fold` gate). The browser strain oracle stays a display-side guard; a browser→agent channel is a later cycle. |
| Op scope | **Multiple ops, applied in sequence**, each precondition-checked against the output of the previous. One primitive (reverse fold) only. |
| Transport | **Approach A:** ops ride alongside the fold in the tool result; the display boundary applies them. Rejected B (tool returns the shaped fold as the artifact — breaks the provenance contract; the shaped file is not flat-foldable) and C (session-level op registry — hidden state, stale ops apply to new compiles). |

## 3. Architecture & data flow

```
agent: draft_and_compile_full_base → base compiles, user asks for a pose
agent: proposes plan in chat (flaps, fraction, theta) → user CONFIRMS
agent: apply_shaping_ops(tree_nodes, symmetric_pairs, targets)
         │  recompile (spawn) → fold + leaf_node_locations
         │  node_id → tip (x,y);  d = fraction × axial-crease length
         │  pre-validate: square(fold) → reverse_fold per op, in sequence
         └─ returns {status, fold, ide_shape_ops, verdicts}
web/server.py: sniffs fold AND ops from the tool output
         display_json = apply_display_ops( square(fold), ops )
frontend Model tab (unchanged): fold → capture → strain oracle → thick paper
```

The provenance contract is untouched: `json` stays the raw linted hull; ops never
enter the FOLD dict (foreign keys inside a fold trip Oriedita — the perturb-
annotation lesson); shaping remains a derived display view.

## 4. The MCP tool: `apply_shaping_ops`

```
apply_shaping_ops(
    tree_nodes: list[dict],
    symmetric_pairs: list[list[int]] | None,
    targets: list[dict],          # [{node_id, fraction?, theta}, ...]
    paper_width=1.0, paper_height=1.0) -> str  # JSON
```

- **Recompile via spawn** (same pattern and reason as `suggest_flap_for_region`);
  the compile worker is extended to also return `leaf_node_locations()` so the
  tool can map each `node_id` to its leaf's paper coordinate.
- **`fraction` (default 0.5), not `d`:** the fold point sits at
  `fraction × axial-crease-length` from the tip, measured on the actual squared
  fold. The agent chooses intent ("bend halfway down"), never paper-unit
  arithmetic. `theta` in degrees, `0 < theta ≤ 180`, magnitude only — bend
  direction follows the flap's axial crease assignment (documented limitation).
- **Sequential pre-validation with the real geometry:** square the fold
  (`complete_square`), then run `shaping.reverse_fold` for each target in order,
  each against the output of the previous — a later op's precondition disc must
  see the earlier op's wedge creases, or display-time application could diverge
  from what the tool promised.
- **Per-target verdicts:** `applied` or `refused: <reason>` (the tracer's
  precondition-gate messages verbatim). A refused or malformed target (unknown
  `node_id`, bad theta) never aborts the batch — remaining targets are still
  attempted against the last successfully shaped state.
- **Single source of truth:** the returned `ide_shape_ops` list contains ONLY the
  applied ops, in application order, as `reverse:<x>,<y>:<d>:<theta>` strings —
  the same grammar `parse_op` already accepts. Agent report, verdicts, and
  display all derive from this one list.

Return JSON: `{"status": "shaped" | "no_ops_applied", "fold": <recompiled fold>,
"ide_shape_ops": [...], "verdicts": [{"node_id", "status", "reason"?}, ...]}`,
or `"ERROR: ..."` if the base tree itself fails to compile.

## 5. Serve plumbing (`web/fold.py`, `web/server.py`, `mcp_harness/shaping.py`)

- **`web/fold.py`** gains `extract_shape_ops(output) -> list[str] | None`: when
  the tool-result JSON carries an `ide_shape_ops` list adjacent to the fold,
  return it (validated: list of strings). Defensive like `extract_fold` — any
  malformation returns `None`.
- **`shaping.apply_display_op` generalizes to
  `apply_display_ops(fold, ops: list[str]) -> dict`:** sequential, defensive
  per-op — a failing op is skipped with a stderr note and the remaining ops
  continue from the last good state; the stream is never broken. Empty/None ops
  ⇒ identity (same object, byte-identical path). The single-op wrapper is kept
  or inlined at the call sites' convenience.
- **`web/server.py` fold frame:**

  ```python
  ops = extract_shape_ops(output)
  if not ops:
      env_op = os.environ.get("IDE_SHAPE_OP")
      ops = [env_op] if env_op else []
  display_json = shaping.apply_display_ops(_square_for_display(fold), ops)
  ```

  Precedence: tool-provided ops win; `IDE_SHAPE_OP` survives only as the debug
  fallback for folds that arrive without ops.

## 6. HITL prompt wiring (`agent_loop.py` SYSTEM_PROMPT)

A new section mirroring A-9's contract in style and force:

- After a base compiles, if the user asks for a pose ("bend the head down",
  "make it stand"), the agent PROPOSES in plain language — which flaps (by tree
  node name), roughly where along each flap (fraction), what angle — and calls
  `apply_shaping_ops` **only after the user approves**.
- On `refused` verdicts, report the geometric reason to the user and suggest
  adjusted `fraction`/`theta`; re-confirm before retrying.
- State the limitation: bend direction follows the axial crease's M/V family;
  theta is magnitude only.
- Shaping is optional polish — never required for a base to be complete.

## 7. Out of scope (deferred, on purpose)

- Closing the strain-oracle loop (browser→agent verdict channel).
- Additional primitives (crimp, narrow-flap, squash/sink). The `targets` schema
  (`node_id`/`fraction`/`theta`) is deliberately primitive-agnostic so they slot
  in later without breaking callers.
- Folded-state-first generalization (Python flat-folding engine) — phase 2.
- Bend-direction control (choosing M vs V family per op).
- Persisting ops as a first-class artifact (download of the shaped file).

## 8. Testing

- **pytest (joins the existing suite):**
  - Tool-level through the real engine on a compiling fixture tree: two-target
    sequence → both `applied`, `ide_shape_ops` length 2, ops parse via
    `parse_op`; an overrunning `fraction` → that target `refused`, the other
    still `applied`; unknown `node_id` → per-target error verdict, no crash;
    non-compiling tree → `"ERROR: ..."`.
  - `apply_display_ops` units: sequence of two valid ops; second op invalid →
    first still applied; empty list → identity object.
  - `extract_shape_ops` units: present, absent, malformed (non-list, non-string
    entries) → `None`.
  - Existing tracer tests (including the fixture drift tripwire) untouched.
- **vitest:** none — the frontend contract is unchanged.
- **Acceptance (manual, live):** the §1 demo on Groq; plus the two identity
  paths (no ops requested; `IDE_SHAPE_OP` fallback still works).
