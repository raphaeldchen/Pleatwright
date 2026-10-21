# Design: deep-shaping agent wiring (reverse_deep + sink) — mini-PR

**Status:** Approved design, ready for implementation planning.
**Date:** 2026-07-07
**Parent docs:** `2026-07-05-atdepth-reverse-fold-slice3-design.md` (reverse_deep),
`2026-07-06-squash-slice4-design.md` (sink = verified reverse_deep(180) alias),
`2026-07-07-handoff-folded-state-slice4-outcome.md` (this wiring named as the
carried mini-PR). Sequenced before B5 slice 1
(`2026-07-07-b5-pose-search-slice1-design.md`).

---

## 1. Goal

Expose the deep primitives shipped in slices 3–4 (`reverse_deep`, `sink`) to
the agent. Today they exist only at the engine + display layers; the agent's
sole shaping surface — the `apply_shaping_ops` MCP tool — whitelists kinds
`("reverse", "outside", "crimp")` and refuses everything else, so prompt text
alone cannot wire anything. Tool + prompt + tests; no engine changes, no
web-tier changes.

**Key finding from context exploration:** the display boundary
(`web/server.py`, the `apply_display_ops(..., raw=fold)` call) already passes
the raw fold through, so once the tool emits `reverse_deep:`/`sink:` op
strings, the display path re-applies them with zero changes.

## 2. Tool changes (`mcp_harness/server.py`, `apply_shaping_ops`)

Two new target kinds, mirroring the rules `shaping.apply_display_ops`
already enforces and `parse_op` already parses:

- **`"reverse_deep"`** — `{node_id, kind, fraction, theta}`. Validated like
  `reverse` (`fraction` in (0,1), `theta` in (0,180]); dispatches
  `shaping_deep.reverse_deep(current, raw_fold, (x, y), d, theta)` where
  `d = fraction * axial_length`.
- **`"sink"`** — `{node_id, kind, fraction}`. No theta (any supplied theta
  is ignored); dispatches `reverse_deep` at the pinned θ=180 (the alias
  verified by `probe_sink.py`).
- **Ordering rule, enforced at the tool:** at most ONE deep target per
  batch, and it must be the FIRST target. A second deep target, or a deep
  target after any tip-local target, is `refused` (same rationale as
  `apply_display_ops`: deep-first is the pinned composition order). Because
  deep runs first, `current` is still the freshly squared base — exactly
  matching `reverse_deep`'s contract (squared display fold + raw fold,
  shared CP coordinates).
- **Recorded op strings:** `reverse_deep:{x},{y}:{d}:{theta}` and
  `sink:{x},{y}:{d}` — byte-compatible with `parse_op`, so
  `ide_shape_ops` round-trips through the display boundary unchanged.
- **Refusals:** `shaping_deep.ShapingError` messages (e.g. the forced
  layer trap: "face X is forced strictly between through-face ... ")
  surface verbatim in the target's verdict, per the existing pattern. A
  refused deep target never aborts the batch; tip-local targets after a
  refused deep target still apply (nothing was consumed).

## 3. Prompt changes (`mcp_harness/agent_loop.py`, SHAPING section)

A compact addition (Groq TPM ceiling — keep it tight):

- `"reverse_deep"` folds the flap THROUGH its stacked layers at the fold
  point (tucks it between layers); plain `"reverse"` folds around them.
- `"sink"` (no theta) tucks the tip inside the base — an open sink.
- At most one deep target per call, and it must be listed FIRST.
- A "forced layer trap" refusal is GEOMETRIC, not tunable: report the
  reason verbatim, then either pick a different fraction or drop the deep
  op — do NOT retry with a different theta.

## 4. Testing

- **`tests/test_shaping_tool.py`:** sink and reverse_deep targets apply on
  a base whose layer order is forced (star-4-family tree); recorded op
  strings re-parse via `parse_op` exactly; ordering refusals (second deep
  target; deep after tip-local); sink works without theta; a trap refusal
  surfaces its reason and does not abort the batch.
- **`tests/test_agent_shaping_prompt.py`:** pins for the new kind
  vocabulary, the deep-first rule, and the trap-is-not-theta-tunable
  sentence; all existing pins pass unmodified.
- Full backend suite (`cd mcp_harness && .venv/bin/python -m pytest tests
  -q`) stays green.

## 5. Out of scope

- Squash (deferred in slice 4 with the provable rationale — moot until an
  interior-pocket slice exists).
- Any B5 / pose-search machinery.
- Web-tier or frontend changes (none needed — §1 key finding).
- A live Groq smoke (manual, optional, not gating this PR).
