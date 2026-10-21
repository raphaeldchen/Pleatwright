# The [FIDELITY] tripwire, observed firing

Follow-up 2 from [PR #75](https://github.com/raphaeldchen/origami-design-ide/pull/75).
Run 2026-08-05. **Outcome: the tripwire fires. It is no longer unobserved.**

## The gap this closes

`path_drift_max` read **0.0 on all five scorecard subjects** and the oracle
fired on none. That was never a defect — the stages those subjects reach
(`stub`, `placement`, `order`) *provably cannot* move a leaf-to-leaf path:
`_STAGE_INTEGRITY` calls order/placement proportion-preserving, and a stub adds
a flap without touching a requested length. Only `jitter`, `composed` and
`normalize` can, and **no corpus subject reaches one.**

So the instrument was correct by construction, pinned by mutation test, and
never once seen to work. This repo has a recorded case of a gate staying green
while its production call site was gutted; an unobserved instrument is one bad
refactor from being exactly that.

## Measured

Progressively tighter stars, compiled through the real serve path
(`server.draft_and_compile_full_base`), then read back through `read_base()`.

| subject | stage | can move a path | path_drift_max | scale | fired | reason |
|---|---|---|---|---|---|---|
| star5 len 0.62 | none | no | 0.0 | 0.5219 | no | no-drift |
| star6 len 0.60 | none | no | 0.0 | 0.5008 | no | no-drift |
| star6 len 0.66 | none | no | 0.0 | 0.4528 | no | no-drift |
| **star7 len 0.55** | **jitter** | **yes** | **0.1476** | 0.4886 | ✅ **yes** | unexplained path drift 0.1476 of span |
| **star7 len 0.62** | **jitter** | **yes** | **0.1476** | 0.4362 | ✅ **yes** | unexplained path drift 0.1476 of span |
| star8 len 0.52 | none | no | 0.0 | 0.4878 | no | no-drift |
| star8 len 0.58 | none | no | 0.0 | 0.4374 | no | no-drift |

**2 of 7 reached a path-moving stage. Both fired.** Zero false fires on the
five that did not — every one stood down with `no-drift`, which is the correct
verdict for a proportion-preserving serve.

## Three things this run also establishes

1. **The parent-path plumbing works end to end.** `scale` is non-null on
   **7/7**. It read `null` on every parent-path serve until 2026-08-05, because
   `_worker_full_base` computed it into a local and then discarded it.
2. **`invented` is measured, not proxied.** `invented_source` reads `"locs"` on
   **7/7** — the json_id `-1` convention — rather than the rung's stub *budget*,
   which is only an upper bound on what the engine was permitted to invent.
3. **The oracle's suppressions hold under real load.** Five proportion-
   preserving serves, five correct stand-downs. Firing on those would have been
   the `anatomy_oracle.py` failure mode: training the agent to chase repairs for
   transformations it was already told about.

## A detail worth not losing

Both jitter serves report drift of essentially the same magnitude — 0.1476145
against 0.1476145 — despite different requested flap lengths (0.55 vs 0.62).
That is the jitter rung applying a *proportional* nudge, so the drift
normalised by span lands in the same place. Consistent with `_STAGE_INTEGRITY`
placing jitter at 0, "lengths were nudged off the request."

## What this does NOT establish

- **The oracle still has zero repair budget, and should keep it.** Firing
  correctly on a synthetic tight star is not evidence that an autonomous repair
  driven by that firing would improve anything. Its false-fire rate on
  known-good bases is the measurement that would earn a budget, and it has not
  been run.
- **No scorecard subject still reaches a path-moving stage.** The corpus was not
  changed. `[FIDELITY]` remains silent on all five committed subjects, correctly.
  These stars are probes, not fixtures.
