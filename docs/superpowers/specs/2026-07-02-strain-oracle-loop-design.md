# Design: Closing the Strain-Oracle Loop (Pillar B)

**Status:** Approved design, ready for implementation planning.
**Date:** 2026-07-02
**Parent docs:** `2026-07-01-shaping-tracer-b1-b3-b4-design.md` (B4: the browser
p90 strain oracle, converge-or-reject), `2026-07-01-shaping-agent-wiring-b2-design.md`
(the agent shaping loop this closes), `2026-07-02-shaping-primitives-crimp-outside-design.md`
(merged as PR #23). Today the oracle's verdict dead-ends in `CADViewer` React
state; the agent never learns whether its pose survived physics.

---

## 1. Goal

Pipe the Model tab's p90 strain verdict back to the agent so a physically
unrealizable pose is retried autonomously (capped), and a passing pose is
positive context. With no browser attached (tests, headless), behavior is
unchanged.

Success demo (live, Groq scout): with a strict threshold (`IDE_STRAIN_MAX=0.05`)
the crimped dog's first pose REJECTS → the agent auto-retries with adjusted
parameters → pass (or a clean user-facing explanation at the cap). With the
default threshold, the normal pass flow shows the verdict reaching the agent.

## 2. Decisions made in this cycle

| Question | Decision |
|---|---|
| Autonomy | **Auto-retry turn**: a reject verdict automatically starts a new agent turn, capped (`IDE_ORACLE_RETRIES`, default 1). Pass verdicts inform but never start a turn. |
| Capture arming | **Auto-switch to the Model tab** when a shaped fold arrives — the GPU solver freezes offscreen (A-cycle hard lesson), so visibility = the loop actually runs. |
| Success bar | Live fail→retry→pass demo, enabled by an env-configurable strain threshold (`IDE_STRAIN_MAX`, default 0.15). |
| Architecture | **Approach A — server-orchestrated retry via a synthetic oracle message.** Rejected B (agent pulls via MCP tool: the verdict lives in the web tier; MCP runs in a separate stdio process; nothing wakes the agent) and C (hold the turn open awaiting the verdict: 30–90s+ hangs, Groq timeouts/TPM, and every browserless run breaks). |

## 3. Wire protocol changes

### Server → client: the fold frame gains two fields

```
{type: "fold", filename, json, display_json,
 id: <int, per-connection counter>,      # verdict correlation
 shaped: <bool>,                          # ops were applied to display_json
 strain_max: <float>}                     # oracle threshold (IDE_STRAIN_MAX)
```

`id` finally lands the request-id idea deferred since the tracer: verdicts
reference exactly one fold, so a slow capture of a superseded fold can never
poison the conversation. `shaped` is set by the server (it knows whether ops
were applied) so the frontend never infers it. `strain_max` makes the browser
threshold server-controlled (default 0.15, env `IDE_STRAIN_MAX`).

### Client → server: the first non-prompt message type

```
{type: "oracle_verdict", fold_id: <int>,
 verdict: "pass" | "reject",
 p90: <float>,                            # measured p90 edge strain
 reason: <string>}                        # human-readable, e.g. "converged" or
                                          # "paper strain (p90) 18.3% exceeds 5%"
                                          # or "no convergence after 12 attempts"
```

Non-strain failures (empty geometry, non-convergence at all attempts) are
`verdict: "reject"` with the reason string and the last measured `p90` (0 when
nothing was measured).

## 4. Frontend (`extraction.ts`, `CADViewer.tsx`, `App.tsx`, `chat.ts`)

- **`extraction.ts`** surfaces the measurement without changing the capture
  promise's type: `createExtractionController` gains an optional
  `onVerdict({verdict, p90, reason})` callback invoked exactly once per
  run's final outcome (resolve or reject, strain or otherwise), and
  `start(fold, maxStrain?)` accepts a per-capture threshold fed from the
  fold frame's `strain_max` (module default stays 0.15).
- **`CADViewer.tsx`** gains an `onVerdict(v)` callback prop invoked exactly
  once per capture attempt-cycle (pass or final reject), with
  `{verdict, p90, reason}`.
- **`App.tsx`** wires `onVerdict` to the ws send (attaching the current fold's
  `id`), and auto-switches to the Model tab when a fold frame with
  `shaped: true` arrives. Unshaped folds never switch tabs.
- **`chat.ts`** `Frame`/`FoldArtifact` types gain the new fold-frame fields.

## 5. Server (`web/server.py`)

- Fold frames: per-connection counter assigns `id`; `shaped` = (ops applied);
  `strain_max` from `IDE_STRAIN_MAX` (float, default 0.15).
- The ws receive loop gains an `oracle_verdict` branch (currently every
  non-prompt frame is ignored). Defensive validation: malformed frames are
  ignored; a `fold_id` that is not the latest served fold is dropped with one
  stderr note.
- A valid verdict appends a **user-role oracle message** to `messages`:
  `[STRAIN ORACLE] pose REJECTED for the current fold: paper strain (p90)
  18.3% exceeds 5% ...` (or `... pose PASSED (p90 4.2%)`), and sends a
  transcript notice frame to the browser so the user sees the verdict land.
- **Reject + latest fold is shaped + budget left** (`retries_used <
  IDE_ORACLE_RETRIES`, default 1; verdicts for unshaped folds append the
  oracle message only, never a turn): run a normal agent turn with the
  existing queue/sentinel machinery — the retry streams to the browser exactly
  like a prompt-triggered turn. **Pass** or exhausted budget: no turn.
- **Budget reset:** `retries_used` resets to 0 only when a shaped fold is
  served by a USER-initiated turn. Folds served by oracle-retry turns must
  NOT reset it — otherwise every retry refills its own budget and a
  never-passing pose loops forever.
- Timing: during a turn the server drains the agent queue and does not read
  the socket, so a verdict sent mid-turn waits in the ws buffer and is
  processed between turns by construction — no locking needed.

## 6. Agent prompt (`agent_loop.py` SYSTEM_PROMPT)

A short addition to the SHAPING section: `[STRAIN ORACLE]` messages come from
the physics simulator, not the human. On REJECTED: adjust the failing pose —
smaller theta, different fraction — and re-call `apply_shaping_ops` WITHOUT
re-asking user approval (an oracle retry refines an already-approved pose; the
approval contract for NEW poses is unchanged). If the oracle rejects again
after the retry, explain plainly to the user what failed and why. On PASSED:
no action needed. No new tools; no schema growth (Groq TPM ceiling).

## 7. Out of scope (deferred, on purpose)

- Multi-fold verdict history (only the latest fold's verdict matters).
- Verdicts for unshaped base folds (the Model tab still renders them on
  demand, but no auto-switch and verdicts for them are still sent and
  simply never trigger retries — rejects without a shaped fold get the
  oracle message only, no turn).
- Closing the loop for the 3D (vendored-sim) tab — Model tab only.
- Persisting verdicts (capture.record) for the world-model data loop.
- Folded-state-first generalization (phase 2).

## 8. Testing

- **vitest:** extraction exposes p90 on both outcomes and honors a custom
  threshold; chat.ts handles the new fold fields; App auto-switch logic
  (shaped → Model tab, unshaped → stays).
- **pytest (web, stubbed turns):** verdict frame appends the oracle message
  verbatim-prefixed `[STRAIN ORACLE]`; reject triggers exactly ONE retry turn
  then stops at the cap; pass triggers none; a second shaped fold resets the
  budget; stale `fold_id` dropped; malformed frames ignored; unshaped folds
  carry `shaped: false`; `strain_max` reflects `IDE_STRAIN_MAX`.
- **pytest (prompt pins):** `[STRAIN ORACLE]` vocabulary; the oracle-retry
  no-re-approval sentence; existing pins (incl. "ONLY AFTER THE USER
  APPROVES") pass unmodified.
- **Acceptance (manual, live Groq scout):** the §1 demo, both thresholds.
