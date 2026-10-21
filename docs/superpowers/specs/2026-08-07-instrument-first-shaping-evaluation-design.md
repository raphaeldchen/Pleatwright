# Design: instrument-first shaping evaluation

**Date:** 2026-08-07
**Status:** design approved, spec pending user review
**Evidence this rests on:** `docs/superpowers/evidence/2026-08-07-legibility-calibration-{prereg,outcome}.md`
(commits `5598b12`, `78c0d64`, `87c43db`, `c412690`, `8462016`)

---

## 1. Why this, and why now

The shaping arc parked on 2026-07-17 behind five measured walls. A
pre-registered legibility calibration run today returned **FAIL** on the
question every route depended on — is a 272.49 → 119.14 `angle_error`
improvement visible? — with `k = 0` of 3 test pairs and a correctly-behaving
BASE-vs-BASE null.

Then, reviewing the sheets *after* answering, the judge identified a dog's side
view with front and hind legs in panel 6 of 7 (elevation −25°, azimuth −125°) —
in P2 row B, P3 row A, P4 row B, and the slab diagnostic. Per `BLIND_KEY.json`
those are **all and only the SHAPED condition**: three independent solver
captures plus a fourth, identified with no access to the key, zero hits on the
two BASE captures. Confirmed on an enlarged single-view render.

**The synthesis those two results force:**

> The object already carries more anatomy signal than our instruments report.
> `pose_target.angle_error` is three scalars over front/back/head; the leg
> structure lives in the projected silhouette. We have been trying to improve
> the object while measuring it with an instrument structurally unable to see
> the property we care about.

Three supporting measurements from the same session:

- **The change is not weak.** SO(3)-restricted Kabsch over the shared vertex
  prefix: noise (BASE vs BASE) max 0.0082; signal (BASE vs SHAPED) max 1.3541 —
  **55.6× SNR**, with 38 of 39 vertices moving >5% of extent.
- **The evaluator is mis-calibrated.** The bridge's 2e-4 z-lift parks a 55- and
  a 109-vertex base at *exactly* 0.0000 even at 60 s settle; 5e-3 folds
  everything. Worse, the amplitude **selects the solver's basin** — an unchanged
  fold reads maxDisplacement 1.4864 / 0.8056 / 0.9678 / 1.5295 across
  2e-4 / 1e-3 / 5e-3 / 2e-2.
- **Base quality is not the blocker.** A base compiled today through the real
  serve path (coverage 0.6810) is no more legible than the 2026-07-03 golden
  (0.6636). Uniaxiality — every flap tip on one line — is what defeats
  legibility, and neither Goal 1 (coverage) nor Goal 2 (symmetry) changes it.

## 2. Scope

**In scope:** a deterministic instrument that can see anatomy; a pre-registered
per-view re-test that both produces evidence and calibrates that instrument; a
fix to the kick that restores measurement validity; and the VLM loop sitting
inside the instrument's veto.

**Explicitly out of scope, deferred until after Goal 1's S4b₀ lands:** narrowing
implementation, any scorecard column, any quantitative shaping target, any
change to what is served.

**Why this scope is safe to build now.** Goal 1's S4b₀ is corner-forcing on
`ProjectActivePaths`; changing base geometry is its purpose (CLAUDE.md §1.1(4)
records corner constraints moving `design_scale` −11.2% to +21.2%). Every
component below is a **function of the base**, not a constant measured on one
base, so S4b₀ re-derives them rather than invalidating them. The cautionary
counter-example is the B5-prime incumbent — `outside:0.0,0.46801304:0.1239…:142.5`,
a hard-coded op string that breaks on recompilation and, because
`shaping._find_tip` is unbounded nearest-neighbour, breaks *silently*.

**Nothing here touches `TreemakerWrapper.cpp`**, the strictly-serial file that
Goal 1's S4b₀ is queued on.

## 3. Prior art (CLAUDE.md §0)

| source | what it gives us | adopted / rejected |
|---|---|---|
| **COrigami** (arXiv 2606.26299, DeepMind + R. J. Lang, ICML 2026) | Shows its VLM **seven rendered views** of the shaped model and never the base; promotion is a **conjunction** (VLM > 0.6 AND tree_similarity > 0.9) in which the deterministic term holds veto — and their symbolic gate rejected **more** than their VLM gate (10,299 vs 7,490). | **ADOPTED**: the multi-view render, and the deterministic-veto conjunction. **REJECTED**: their shaping vocabulary and packer — grid-coupled to box-pleating, and TreeMaker's universal molecule produces irrational angles their templates cannot snap to. Also rejected: their RL, at our sample size. |
| **Lang**, *Bridges 2009* p.18; TreeMkr40 p.169 | "Last comes the shaping. There is no algorithm for this." Narrowing is the one post-base operation he gives a construction for. | **ADOPTED** as scope discipline: we are not trying to out-algorithm shaping; we are building the instrument that lets it be evaluated. Narrowing **DEFERRED** (see §9). |
| **Huang et al.** (ICLR'24); **Kamoi et al.** (TACL 2024) | GPT-4 GSM8K 95.5 → 91.5 → 89.0 under intrinsic self-correction, but 95.5 → **97.5** with a label oracle; CommonSenseQA collapses 75.8 → 38.1 intrinsic vs 89.7 with oracle. | **ADOPTED**: the standing rule, stated positively — the deterministic instrument is what makes the loop work at all, not merely what keeps the VLM honest. |
| **GamiBench** (372 origami crease patterns) | Frontier MLLM foldability signal is *anti-correlated* with truth: GPT-5 flags actually-impossible folds 8.4% of the time while flagging **valid** folds impossible 24.6–25.0%. | **ADOPTED** as a hard constraint: the VLM may **rank**, never **veto**. On-domain evidence, not a general prior. |
| **Repo precedent** — `mcp_harness/cp_mirror.py:356` `overlay_svg` | Already renders a crease pattern server-side in pure Python. | **ADOPTED** as the pattern for server-side rendering; **not reused directly** (it emits SVG of a CP, we need raster of folded 3-D geometry). |

## 4. Architecture

```
tree ─► compile ─► fold ─┬─► capture (kick-swept) ──► folded geometry ─┐
                         └─► flat_fold / rigid_fold ───────────────────┤
                                                                       ▼
                                                       projection_metric.py
                                                     (deterministic, no browser)
                                                                       │
                                          ┌──── GATE (veto) ◄──────────┤
                                          │                            ▼
                                          │                   png_render.py
                                          │                            │
                                          └──── VLM (ranks only) ◄─────┘
```

The metric consumes `{vertices_coords, faces_vertices}` — the payload
`sim_capture` returns, and also the payload `flat_fold` / `rigid_fold` produce.

⚠ **The analytic path is NOT an escape from the capture tax for shaped
geometry, and this spec must not imply otherwise.** Measured: `rigid_fold`
closes the raw dog to 7.77e-08 at all-±180, but applying the incumbent op sends
the closure residual to **1.03066**, with a 721-point and a 145×145 scan
putting the global minimum at *exactly* the fully flat state. `flat_fold`,
`rigid_fold`, `flex_extension`, `mobility_search` and `square_complete` contain
**zero** references to `edges_foldAngle`, and `flat_fold`'s folded vertices are
byte-identical for θ ∈ {75, 142.5, 180}. So:

- **unshaped, flat states** → analytic folder is valid, machine-precision, free;
- **shaped states** → the browser capture is the *only* source, and it is the
  definition of the quantity, not a convenience.

The dual input still matters — it lets the metric be unit-tested and calibrated
on analytic folds with no browser in CI — but shaped evaluation pays the full
30–90 s tax.

## 5. Component 1 — `mcp_harness/projection_metric.py`

**Interface**

```python
def silhouette_signature(vertices, faces, elev, azim) -> ViewSignature
def anatomy_score(vertices, faces, views=VIEWS) -> dict
```

**Method.** Project vertices to the camera's 2-D basis (reuse the orthographic
basis already written for the calibration renderer). Then compute a **polar
signature**:

1. Centroid of the projected vertices.
2. Bin by angle into `NBINS` equal sectors (start `NBINS = 180`, i.e. 2° bins).
3. Per bin, take the **maximum radius over projected vertices in that bin** —
   this is the outline in polar form. *No polygon boolean union is needed*, which
   matters: the repo ships no polygon-boolean library and the venv may not gain
   one (§8).
4. Smooth circularly, then count **local maxima exceeding `r_bar * (1 + K)`**,
   where `r_bar` is the signature's mean radius.

**`K` is derived, not fitted.** It is fixed as a geometric quantity before any
calibration run — the initial value is `K = 0.35`, chosen because a limb that
protrudes less than 35% beyond the mean radius is not something a viewer would
call a limb. It is **not** to be adjusted to make the calibration pass; if
calibration fails at the pinned `K`, that is the result (§5 criteria).

Report per view: protrusion count, per-protrusion aspect ratio (peak radius ÷
angular width), radius variance, and compactness (area / perimeter²). Aggregate
across views by reporting the per-view vector plus max and mean — never a single
scalar, because the whole finding motivating this design is that a one-camera
signal washes out when views are averaged (§6).

Rationale: "how many things stick out, and how long and thin are they" is what
the judge's eye did in view 6, and it is exactly the property Lang says a
narrowed base has ("long, skinny, connected sticks").

**Calibration criteria — NON-NEGOTIABLE, and the real deliverable.** This
repo's recurring failure mode is the vacuous gate: a metric that reads the same
on everything (`mv_swapped == 0` scoring 8/8 on stock input; `path_drift_max`
0.0 on all five subjects; `pose_pregate` returning identical dof/r\* for six
different θ). On the captures already committed, the metric MUST:

1. score **SHAPED > BASE at view 5** (the flagged camera),
2. **NOT** separate **BASE#1 from BASE#2** at any view — the null,
3. read approximately equal at views where the judge reported nothing.

If it fails any of the three, it is vacuous and the finding is reported as such.
No tuning the threshold until it passes; the threshold is fixed before the run
and a failure is a result.

## 6. Component 2 — the per-view re-test

Zero new captures; the geometry is on disk. Each of the 7 views judged
**separately** and blinded — BASE vs SHAPED at that camera, plus a
**BASE-vs-BASE null at the same camera**. Criterion pinned before rendering, in
its own prereg document, same discipline as `5598b12`.

Serves double duty: it converts the post-hoc observation into pre-registered
evidence, and it is the ground truth §5's calibration measures against.

**Design note carried forward from the failure:** the first calibration
averaged 7 views into one verdict per row, and the repo already knew legibility
here is violently view-dependent ("a triangle face-on and a single line
edge-on"). Per-view is the correction.

## 7. Component 3 — kick fix (`ide-bridge.js` + `sim_capture.py`)

**Problem, measured.** The 2e-4 z-lift parks ≥50-vertex patterns at exactly
0.0000 (unchanged at 60 s settle), and the amplitude selects the basin.

**Fix.**

1. Raise/adapt the amplitude so it does not park. Amplitude becomes a
   parameter, not a literal.
2. **Record the amplitude in every capture.** Captures are currently silent
   about a constant that determines their value.
3. Sweep K amplitudes and report the **basin spread** as explicit uncertainty.
4. **Refuse, never score**, a capture whose spread exceeds threshold — mirroring
   the existing converge-or-reject and `DISP_GATE` discipline.

**This re-baselines history, and that is the point.** 272.49, 119.14, the
144.34 bar, the ±7° drift band and the 127° pair-prediction median are all
amplitude-conditional. They are not wrong; they are conditional on a constant
nothing recorded. Any re-measurement must be attributed to this change and not
absorbed silently (COORDINATION.md §1: "a row you cannot attribute is a
FINDING, not noise").

It also closes the kick-hardening prerequisite open since 2026-07-13, correctly
reframed: two hypotheses (K.0 projection, K2.0 target-branch sign) both sought a
**directional** mechanism and both were falsified. The mechanism is **basin
selection**, which is why a per-site directional theory kept failing.

## 8. Component 4 — the VLM loop

**Plumbing** (all measured, all base-independent):

- `mcp_harness/llm_client.py` — **no change**. It passes `messages` through and
  OpenAI content-parts are already legal there.
- `mcp_harness/agent_loop.py:650-654` — widen the `type == "text"` filter, which
  currently drops an MCP `ImageContent` block silently, leaving the agent
  reading "(tool returned no text output)".
- The image cannot ride in the `role:"tool"` message (openai 2.43.0 types that
  content as text-only). It goes as an **additional `role:"user"` content-parts
  message** — the seam `web/server.py` already uses four times for
  `[CP AUDIT]` / `[ANATOMY]` / `[FIDELITY]` / `[STRAIN ORACLE]`.
- `_trim_consumed_blobs` guards `isinstance(content, str)`, so a list-content
  message is never trimmed and base64 would accumulate unbounded. Must handle
  list content.
- Tool return convention: the repo's 18 tools are uniformly `-> str`, which
  makes returning an `Image` raise a pydantic `ToolError` on MCP SDK 1.27.2.

**Rasteriser.** Vision APIs need raster; the repo ships no rasteriser; and
`mcp_harness/.venv` is a **symlink to the main repo**, so installing Pillow
would mutate the user's main environment and its CI-pinned deps. Therefore:
`mcp_harness/png_render.py` — a pure-Python PNG encoder (zlib only) plus a
scanline polygon fill, reusing the painter's-algorithm depth sort and fixed
Lambert shading already written for the calibration renderer. ~100 lines,
dependency-free.

**Gate.** The VLM **ranks**; `projection_metric` **vetoes**. No VLM output ever
changes what is served — it changes only what the agent tries next.

## 9. Deferred, with reasons

- **Narrowing** (Lang p.35 tree-side, p.140 fold-side). The pre-test run today
  shows tree-side subdivision **packs** (9 → 15 → 21 nodes all compile through
  the real serve path) and reads *slightly* better at k=2/k=3, but nothing is
  nameable, and coverage falls **0.6810 → 0.6325 → 0.5929**. Narrowing trades
  paper, which per CLAUDE.md §1.1(4) is a trade to argue explicitly. Revisit
  after S4b₀ and after the metric exists to measure it.
- **Fold-side narrowing** additionally needs inset-polygon geometry exported
  from `TreemakerWrapper.cpp` — the serial file. Blocked on scheduling
  regardless of merit.
- **Everything the calibration retired**: κ-descent (needs 22,600×, best
  measured 28.75×), off-flat serve states (no rigid off-flat state exists),
  more direction ops, Origamizer-style rewrite.

## 9a. Decomposition — this spec is THREE implementation plans, not one

Flagged in self-review: §5–§8 are separable, have different risk profiles, and
the later ones are worth nothing if the first fails. They must not be planned as
one unit.

| plan | contents | gate to proceed |
|---|---|---|
| **P1** | §6 per-view re-test → §5 `projection_metric` + calibration | **If the metric is vacuous, STOP.** P2 and P3 are pointless without an instrument that separates shaped from base. |
| **P2** | §7 kick fix + amplitude recording + basin-spread refusal | Independent of P1's outcome — it is a measurement-validity repair worth doing regardless — but sequenced second because P1 needs no new captures. |
| **P3** | §8 VLM loop + `png_render.py` | Requires P1 to have produced a working deterministic gate. Entering P3 first would invert the acceptor-before-eyes ordering the project has already paid to learn. |

Only **P1** should be planned now. P2 and P3 get their own plans after P1
reports.

## 10. Error handling

| condition | behaviour |
|---|---|
| capture below `DISP_GATE` (parked) | refuse, retry, never score |
| basin spread over threshold | refuse, report the spread |
| metric fails any calibration criterion | report vacuous; do not tune to pass |
| VLM unavailable or refuses | loop still functions; the metric alone gates |
| image block dropped by the harness | a test catches it (§11), since it is silent today |

## 11. Testing

- **Calibration test** pinned on the committed captures: SHAPED > BASE at view
  5; null not separated. Failure is a red test, not a tuning signal.
- **Kick regression:** a >50-vertex base folds (today it does not).
- **Image reaches the model:** measured end-to-end, not assumed. This is Phase
  3's never-tested first STOP IF.
- **Vacuity guards** on the metric mirroring `probe_packing_diagram`'s
  correctness trap: a deliberately-wrong input must score differently.

## 12. Risks

1. **The metric may be vacuous.** Mitigated by fixing calibration criteria in
   advance and reporting failure as a result. This is the single most likely
   outcome and the design must not hide it.
2. **n is tiny.** Five captures, one subject, one op. The per-view re-test
   raises the item count (7 views × pairs) but they are not independent. No
   PASS here licenses a general claim; bounding a null within ±0.10 needs n≈97.
3. **The kick fix re-baselines historical numbers** (§7). Attribution is
   mandatory.
4. **A hand-rolled PNG encoder is a real, non-obvious cost** and a plausible
   source of subtle bugs. Mitigated by keeping it to flat-shaded polygons and
   testing against a known-good decode.
5. **S4b₀ may change bases more than expected.** Mitigated by the
   functions-not-constants rule (§2) and by committing the pre-test trees as
   fixtures so the post-S4b₀ re-run is a controlled comparison.
