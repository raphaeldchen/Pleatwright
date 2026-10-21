# CHECKPOINT — b5-front-dof Phase D (mid-slice user gate)

> **DECISION (raphaeldchen, 2026-07-13): Option A APPROVED — Phase S Wave S0
> (re-composed excitation wave, §3) proceeds, in a NEW session.** Phase D
> ships as this PR. Handoff notes for the S0 session: (1) fresh-worktree env
> copy list is `.venv` symlink + `headless_treemaker*.so` +
> `oriedita/*.jar` + `OrieditaValidator.class` + `web/frontend/dist` +
> `probe_dog_coupling.out.jsonl`; (2) `probe_front_flex.out.json` (w\*
> support, D2 ranking — S0's recipe inputs) is uncommitted BY DESIGN:
> regenerate it by re-running `probe_front_flex.py` (sim-free, seconds,
> deterministic, refuses on any anchor drift); (3) deferred minors ledger
> in this worktree's `.superpowers/sdd/progress.md` (m2/m5-m7/m9-m14);
> (4) kick-hardening trigger is pre-armed: if a front-pair recipe parks
> asymmetrically, HALT per spec §5.

**Date:** 2026-07-13 · **Branch:** `feat/b5-front-dof` · **Spec:**
`docs/superpowers/specs/2026-07-12-b5-front-dof-diagnosis-design.md` · **Plan:**
`docs/superpowers/plans/2026-07-12-b5-front-dof-phase-d.md`
**Probe outputs (uncommitted):** `mcp_harness/probe_front_flex.out.json`,
`mcp_harness/probe_front_pilot.out.json{,l}`, `mcp_harness/probe_folding_dof.out.json`.

## 1. Confirmed verdict

**SEARCH GAP at first order — reachability UNCONFIRMED (pilot inconclusive
as composed).**

Two-part statement, both halves measured:

- **The front-moving freedom EXISTS.** The served/squared dog's 3-dimensional
  first-order flex space contains a direction with front-selectivity
  **r\* = 1.76** (front tips move 1.76× as much as back+head combined) — well
  above the ≥ 1.0 search-gap bar and nowhere near the ≤ 0.2 structural bar.
  The instrument is **calibrated against reality**: the D2 cross-validation
  was non-vacuous (signature-matrix cond 0.126 < 0.2). **Correction (applied
  after the original run, following the whole-branch review):** a full-rank-3
  projection is vacuous by construction — three independent signature
  vectors span all of R^3 at any finite conditioning, so that projection
  captures 1.000 unconditionally and cannot fail. The corrected calibration
  instead projects onto the conditioning-truncated span (the left-singular
  directions with sv ≥ VACUITY_COND·smax; here effective rank 2, dropping
  the near-zero third direction) and measures **captured = 0.904 ≥ 0.8 →
  PASS**, which is genuinely falsifiable (a mode lying along the dropped
  direction now correctly reads FAIL — pinned by a new test). The D1
  verdict never depended on D2; this correction changes D2's calibration
  story, not the search-gap finding. The structural-lock hypothesis for the
  crease pattern itself is **refuted**: B5-prime's front ceiling is not a
  property of the mechanism's first-order kinematics.
- **The pilot did not confirm reachability, and per the pinned rule its
  formal verdict is "structural for practical purposes" — but with a
  material composition caveat.** The flex direction's crease support maps
  overwhelmingly to the FRONT HUB (context weight 2.33 vs ≤ 0.24 for all
  others), and every candidate the mechanical menu generated for that
  dominant context (`reverse_deep` at beyond-grid depth frac 2.0, both front
  sites) was **refused by the shaping layer** — so the predicted direction
  was never actually excited. Six of eight recipes refused, one parked
  (back_v12, the known kick-degenerate site), and the single scored recipe
  (`back_v16|outside|30|0.5`) moved front −5.21° (away), back +48.1°,
  head +23.8° — i.e., it reproduced the familiar global rank-1 mode at an
  off-grid θ, further confirming D2's model but saying nothing about the
  front direction. A refusal wave is evidence about *op parameterizations*,
  not about the direction.

Honest-outcome framing: Phase D succeeded at its job — the question
"search gap or structural lock?" is answered **search gap, at first order,
with high instrument confidence**; what remains open is narrower and
cheaper: *which applicable op vocabulary couples to the now-explicitly-known
direction* (or, failing that, whether the first-order flex extends finitely).

## 2. Gate-by-gate record

**Gate D0 (PASS).** Instrument anchors 4/4 (deg-4 dof==2; ρ=π reproduces
flat_fold on star-4; g(0)==0; star-4 dof≥1). Dog-squared reads **dof 3 /
rank 35 / creases 38** (matches the recorded regression, now pinned as a
test). Coupling table reconciles exactly: 162 gate-1 rows = 114 scored +
12 refused + 36 parked + 0 error. NamedBase grouping == recorded B5-prime
grouping, ambiguity 0. Full suite green at the gate: **592 passed /
4 skipped** (baseline 557 + 28 new Phase-D tests + 6 promoted instrument
tests + 1 regression pin).

**Gate D1 (SEARCH-GAP).** r\* = **1.76272** (front_rms 0.0505004,
backhead_rms 0.0286491), not unbounded, not degenerate. Dual step-size
guard (h 1e-5 vs 1e-6, rtol 1e-4) clean on all 3 flex directions × 7
tracked vertices. Verdict rule (pinned before measurement): ≥ 1.0
search-gap / ≤ 0.2 structural / else gray.

**Gate D2 (PASS, non-vacuous).** Measured dominant mode
[−0.1011, 0.8764, 0.4708] over (front, back, head) — the rank-1 mode
measured over the coupling table's 114 scored rows — rank-1 share 0.915
(reproduces the B5-prime recorded value from the same data). **Correction
(applied after the original run, following the whole-branch review):** the
originally reported captured fraction of 1.000 was a projection onto the
full numerical-rank-3 span, which is vacuous by construction (any 3
independent signature vectors span all of R^3, so that projection always
captures 1.000 — it could not have failed, regardless of conditioning).
The corrected calibration projects onto the conditioning-truncated span
instead (left-singular directions with sv ≥ VACUITY_COND·smax; effective
rank 2 here, dropping the near-zero third direction) and measures
**captured = 0.904** ≥ 0.8 → PASS; conditioning 0.126 — below the 0.2
vacuity bar. This version is genuinely falsifiable: a mode lying along the
dropped (near-zero) direction now correctly reads FAIL, pinned by a new
test. The mode/share/ranking numbers below are unchanged — only the
captured/status semantics changed. Search-gap readout (measured rows
ranked by |cos| against the predicted front-direction signature):
`head_v25|reverse|142.5|0.65` 0.972, `head_v25|reverse|105|0.35` 0.958,
`front_v13|reverse_deep|170|0.5` 0.912, `head_v25|reverse|105|0.65` 0.910,
`front_v13|reverse|142.5|0.35` 0.908.

**Gate D3 (fired; no confirmation; 16/40 reads).** Baseline ×3 scored
(front 65.98 / back 27.80 / head 34.52; fox front target 134.83 → toward =
+1). Contexts from w\*'s support (energy rule 0.9/cap 10):
hub_front **2.326**, hub_rear 0.236, back_v12 0.200, back_v16 0.167.
Recipe outcomes:

| recipe | outcome |
|---|---|
| front_v13\|reverse_deep\|105\|2 | refused (shaping layer) |
| front_v18\|reverse_deep\|105\|2 | refused |
| tail_v14\|reverse_deep\|105\|2 | refused |
| back_v12\|reverse_deep\|105\|2 | refused |
| back_v12\|sink\|1.25 | refused |
| back_v12\|outside\|30\|0.5 | parked 3/3 (known kick-degenerate site) |
| back_v16\|sink\|1.25 | refused |
| back_v16\|outside\|30\|0.5 | scored: Δfront −5.21 (away), back +48.1, head +23.8 |

Pinned no-confirmation rule fired → formal D3 verdict "structural for
practical purposes; closure-solve escalation goes on the checkpoint table."

**Measured findings beyond the gates:**

1. **Kick asymmetry, third strong datum:** back_v12 parked 3/3 again
   (persistent-park), exactly reproducing the B5-prime tripwire on a novel
   op. Kick-hardening's case keeps strengthening.
2. **D2's model generalizes off-grid:** the one scored novel op (θ=30,
   never in any prior grid) produced the same back+head global mode the
   model predicts — the instrument's world-model held on unseen input.
3. **reverse_deep frac 2.0 is universally refused** on this base (4/4
   sites) — the beyond-segment depth regime does not apply here; menu
   knowledge for future waves.
4. **Budget accounting caveat** (adjudicated at Task-9 review): reads count
   measure-attempts per the spec's convention; parked slots retried
   internally, so raw GPU captures exceed the 16 nominal reads. Bounded and
   consistent with B5-prime precedent.

## 3. Proposed Phase S scope (for approval — nothing below is started)

The verdict routes to the **search branch**, sharpened by the pilot's
lessons. Proposed:

**Wave S0 — re-composed excitation wave (primary ask).** Target the known
direction with ops that demonstrably APPLY, ~30–60 reads:
symmetric front-pair units (outside θ∈{105, 142.5} on both fronts as one
atomic recipe), front-tip `sink|1.25` and `outside|30` (the tip-context
menu the pilot never reached because hub_front dominated), moderated
front-tip amplitudes, and in-grid-depth `reverse_deep` (frac 0.5/1.25) at
front sites — parameters chosen by the D2 ranking (which already flags
`front_v13|reverse_deep|170|0.5` and `head_v25|reverse|142.5` cells as the
strongest measured couplings to the front direction). Gate: same pinned
CONFIRM bar (front ≥ +20° toward target, ×3). Kick-hardening trigger:
if a front-pair recipe parks asymmetrically, HALT and raise it to
prerequisite.

**Escalation (if S0 also fails to move front): closure solve.** Sim-free
finite-extension check of w\* — decide build-here vs consume Codex rigid/
kernel's R3 (prefer consume, per spec §2.4).

**Fallback (if both fail): structural branch** — minimal Metric-Tree/compile
intervention with the (now-validated) classifier as pre-gate, per spec §5.

**Budget ask:** 120 sim reads for Phase S total (S0 ≈ half), against the
~400-read slice precedent.

## 4. What is NOT decided

Phase S detail is not planned; no Phase-S code exists; the closure-solve
build-vs-consume decision is open; the budget above is an ask, not a grant.
Phase D's artifacts (instrument, probes, tests, this record) stand on their
own regardless of the Phase-S decision — both outcomes remain valid slice
endings per the honest-outcome rule.
