# Handoff: front-lever-payoff (Phase S) — outcome

**Date:** 2026-07-13 · **Branch:** `feat/front-lever-payoff` · **PR:** (opened at slice end)
**Spec:** `docs/superpowers/specs/2026-07-13-front-lever-payoff-design.md` ·
**Plan:** `docs/superpowers/plans/2026-07-13-front-lever-payoff.md` (S0.b menu of
record appended in-plan, commit `d517e8b`)
**Probe outputs (uncommitted, regenerable):** `mcp_harness/probe_front_flex.out.json`
(rerun `probe_front_flex.py`; refuses on anchor drift), `probe_front_wave.out.json(l)`
+ `probe_front_wave.s0.log` (S0 capture record), `probe_flex_extension.out.json`
(rerun `probe_flex_extension.py`, sim-free).

## 1. Slice verdict

**The B5-prime front ceiling is STRUCTURAL AT FINITE ORDER for rigid
kinematics.** Phase D's search-gap verdict is refined, not contradicted: the
front-selective first-order flex w\* (r\* = 1.76) is real at first order but
is a **second-order phantom** — its quadratic obstruction lies entirely
outside range(J) (‖(I−JJ⁺)Q(w\*,w\*)‖ = 0.0956, rel 1.0, h-stable to
9.4e-10), carried by the pattern's genuine cone vertices (v5 deg-6, v0, v1,
v4), not by squaring artifacts. No op vocabulary can excite a finite front
pose that the mechanism does not finitely have; the small real front motion
the sim shows (+6.5°, below) lives in the tolerated-strain (compliant)
regime, ~3× below the confirm bar.

Two-part evidence, both halves measured this slice:

- **Wave S0 (excitation): HALT-KICK at 13/50 reads.** The pre-armed kick
  trigger fired (`frontpair|outside|142.5|0.35` parked 3/3), after the
  mirror-twin asymmetry reappeared on a novel site: `front_v18|outside|30|0.5`
  parked 3/3 while its twin `front_v13|outside|30|0.5` scored — kick data #4
  and #5 (back_v12 precedent ×3). Before the halt, `front_v13|outside|30|0.5`
  became the **first measured op matching the predicted front-selective
  signature** (Δfront +6.52° toward target, Δback −14.33°, Δhead −1.46°) —
  right direction, 3× too weak.
- **Escalation (finite extension, sim-free): NON-EXTENDING** (above), through
  the consumed Codex closure kernel, anchored on degree-4 (first-order dof 2
  → finite dof 1 reproduced; extending-direction defect 1.6e-8 vs phantom
  0.336 calibrates the test's non-vacuity). Per the spec's pinned routing:
  **not** a bridge change; no HALT. *Routing note (intentional, decided at
  the HALT checkpoint by the user): the plan's literal Task-3 text routes
  only NO-CONFIRM → escalation; running the zero-read escalation after
  HALT-KICK was chosen explicitly at the in-session checkpoint ("escalation
  probe, then end") — it stops all capture spending as the trigger demands
  while buying the finite-extension answer for free.*

Honest-outcome framing: S1 never fired (nothing confirmed to compose), the
119.14 incumbent stands, and the slice ends with a clean structural verdict
plus a named prerequisite — a successful slice under the pinned rules.

## 2. Gate-by-gate record

**Preflight (PASS).** Fresh worktree env per the Phase-D recipe; regenerated
`probe_front_flex.out.json`: r\* = 1.76272, captured = 0.904, coupling
reconcile 162 = 114/12/36/0, D1 SEARCH-GAP — all anchors exact.

**Gate S0.a — pre-gate anchors (PASS).** New `pose_pregate.py` (the slice's
durable artifact): unshaped dog reproduces r\* 1.76272 / dof 3 through the
pre-gate path; B5-prime incumbent op smoke on the SHAPED pattern works
(dof_shaped 4, r\*_shaped = inf — unbounded front selectivity is a
legitimate branch); all four D3-refused `reverse_deep|105|2` recipes refuse
**sim-free** (Gate S0.a(c), 4/4).

**Gate S0.b — menu of record (committed `d517e8b` before any capture).**
Pinned 14 cells → **6 capture candidates**: 6 terminal-collision drops
(gate-1 had already measured them; 0 table-mine hits ≥ +20°) and 2 pre-gate
refusals (`front_v13/v18|sink|1.25`, "d reaches past the axial crease") at
**zero reads** — the D3 failure mode (refusals discovered only at capture
time) is retired. All 6 survivors scored r\*_shaped = inf (dof 4 tips / 5
pairs): the first-order instrument cannot discriminate among front-freeing
ops — in hindsight consistent with the phantom finding (the discriminating
physics is second-order). Defiant quota degenerated to empty (menu ≤
quota_n), correctly.

**Gate S0.c — excitation (HALT-KICK, 13/50 reads).** Baseline ×3: front
64.64 / back 36.29 / head 37.22 (whole-pose totals 272.4–273.6, matching
B5-prime's 272.49). Rows before the halt:

| recipe | outcome |
|---|---|
| front_v13\|outside\|30\|0.5 | scored: ΔF **+6.52 toward** / ΔB −14.33 / ΔH −1.46 (first front-selective signature ever measured; < bar) |
| front_v18\|outside\|30\|0.5 | parked 3/3 (vacuous-pass trap, maxDisplacement 0.0) — **mirror twin healthy → kick datum #4** |
| frontpair\|outside\|105\|0.35 | scored: ΔF −8.46 / ΔB +57.50 / ΔH +33.30 (the familiar global rank-1 mode; total 190.7) |
| frontpair\|outside\|105\|0.5 | scored: ΔF −14.12 / ΔB −2.79 / ΔH −4.85 (total 294.8) |
| frontpair\|outside\|142.5\|0.35 | parked 3/3 → **HALT-KICK (kick datum #5)** |
| frontpair\|outside\|142.5\|0.5 | not measured (halt) |

**Gates E.a/E.b — escalation (PASS / NON-EXTENDING).** New
`probe_flex_extension.py` consumes `rigid/kinematics/closure.py`
(residual + exact jacobian); convention translation solved **constructively**:
per-crease sign gauge τ (rigid_fold ρ = tree-child rotation vs kernel
outward-consistent dihedral), validated τ=(1,1,−1,−1) on degree-4 and
principal cosines [1,1,1] against rigid_fold's flex space on the dog after
handling the 12 `square_complete` artifacts (4 pure-flat vertices dropped,
8 single-M/V collinear vertices pinned f=0 in both J and Q). Kernel J:
rank 35 / nullity 3 — exact match with `rigid_fold`. ‖J·(τ⊙w\*)‖ = 1.5e-15
(the translated w\* is a genuine kernel flex). Verdict machinery calibrated
by the anchor; continuation used as corroboration; verdict **NON-EXTENDING**.

**Read ledger vs grant:** 13 of 120 (S0 13, S1 0, contingency 0, escalation
0 by construction). The kick halt stopped spending exactly as designed.

## 3. Measured findings beyond the gates

1. **Kick asymmetry now blocks the front program** (data #4/#5, same
   vacuous-pass-trap signature `maxDisplacement 0.0000 < 0.1`): the z-lift
   kick fails to break flat symmetry on some shaped front patterns, on one
   side of a mirror pair only. Kick-hardening graduates from parked
   follow-up to **prerequisite** for any front-pair (and some front-tip)
   measurement.
2. **Session drift datum:** baseline back 36.29 vs D3's 27.80 (+8.5°,
   above the ±7° band; front/head within ~1.3–2.7°). Reinforces the
   margins ≫ drift rule and same-session re-baselining (which S1 had
   pinned).
3. **The τ-gauge translation** (constructive, artifact-aware) between
   `rigid_fold` and the Codex kernel is now solved and tested — reusable
   knowledge for the planned migration of the instrument math into
   `rigid/` (its OWNERSHIP NOTE), and for any future kernel-based
   whole-pattern work. Attempt-1's fitting approach is a documented dead
   end (ill-conditioned under zero-support creases).
4. **frontpair|105|0.35's whole-pose total of 190.7** (baseline ~273) is
   another instance of the global mode improving whole-pose while moving
   front the wrong way — consistent with B5-prime, no action.

## 4. Routing verdict (per the spec: productization named in EVERY outcome)

1. **Productize the best-known stack via `ide_shape_ops` — the B5-prime
   incumbent** (`outside:0.0,0.46801304:0.12398308661620648:142.5` on
   `front_v18`, whole-pose 272.49 → 119.14). Nothing this slice beat it;
   it has never been user-visible. Suggested shape: agent-side HITL
   suggest-then-confirm (B2 pattern), display replay already works.
2. **Research follow-up — the structural branch** (spec §5): minimal
   Metric-Tree/TreeMaker intervention so the compiled+squared output has a
   front-selective direction **that extends finitely**. The pre-gate for
   candidate trees now has TWO sim-free stages: `folding_dof` + D1
   front-selectivity (Phase D) **and the second-order obstruction test**
   (`probe_flex_extension.py`'s machinery) — a candidate must pass both
   before compile-heavy iteration or capture. This upgrade is this slice's
   direct contribution to the next one.
3. **Prerequisite raised — kick-hardening** (5 data points, now blocking):
   deterministic symmetry-breaking for shaped flat equilibria (the 2e-4
   z-lift is insufficient on shaped front patterns). Should precede or be
   bundled into any slice that needs front-side captures.
4. **Explicitly NOT routed:** bridge changes (EXTENDS would have routed
   there; the verdict is NON-EXTENDING) and S1/composition work (nothing
   to compose).

## 5. Deferred minors (for the final-review triage / next session)

From task reviews, all non-blocking: (m1) no rank_menu-layer inf-vs-finite
ordering test; (m2) instrument_error > quota_n eviction unexercised; (m3)
E128 indent nit `pose_pregate.py`; (m4) `menu_only`/`run_wave_s0` duplicate
4-line preamble; (m5) CouplingTable parsed twice per driver call; (m6)
`_read` ~35-line copy of the pilot's (justified: pilot unmodifiable);
(m7) no test for preflight STOP paths; (m8) **FIXED post-PR** (CI reddened on
exactly this): the four tests hard-depending on untracked
`probe_front_flex.out.json` (both full-driver wave tests + both
`test_flex_extension` dog tests) now carry a `needs_flex_json` skipif —
CI runs them as skips (the coupling-table input cannot exist there); the
pinned local workflow still runs all four;
(m9) table-mine hit with refusing ops would raise uncaught (dormant);
(m10) **FIXED post-final-review** (`97d8338`, the review's one requested
fix): HALT-KICK now attaches/writes the partial capture summary
symmetrically with BudgetExhausted, with an e2e test (19 in the driver
file); the live S0 out.json predates the fix — its rows remain
JSONL-only, regenerable; (m11) 4B report's
h-sweep narrative overstates the committed 2-point check; (m12)
REFUSED(translation) not negatively tested; (m13) 2+-M/V collinear
vertices silently unconstrained (empty set here); (m14) missing w\* file
crashes rather than REFUSES; (m15) anchor tangent/crease-order alignment
implicit; (m16) EXTENDS/HALT path unexercised (trivial). Cosmetic: Task-2
commit subject says "16-cell" menu (stale plan text; actual 14).

## 6. Suite state

Full backend suite green at the branch HEAD (post-m10-fix), measured:
**668 passed / 4 skipped** in 9:21 (main's post-PR-#39 baseline 631 + this
slice's 37: 11 `test_pose_pregate` + 19 `test_front_wave` + 7
`test_flex_extension`). Web suite untouched: **40 passed** (1 pre-existing
warning). In CI (no regenerable probe artifacts) the same suite reads
**664 passed / 8 skipped** via the m8 `needs_flex_json` guards. Probe
outputs and suite logs uncommitted per house rules.
