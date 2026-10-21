# Pre-registration: legibility calibration of `pose_target.angle_error`

**Written 2026-08-07, BEFORE any render exists.** Committed before the capture
step runs. Nothing below may be edited after the first image is produced; a
change of criterion after seeing data is the failure this document exists to
prevent.

## 1. The question

Every shaping route this project has costed optimises, or is judged by,
`pose_target.angle_error` — three scalars (front/back/head), compared by L1,
range [0, 540]. **Nothing in this repo connects that number to "the model looks
like the thing"**, which is the stated project goal (CLAUDE.md §5).

B5-prime measured a single op taking the served dog from **272.49 → 119.14**
(−56%, against a 144.34 pass bar). *Neither end has ever been looked at.*

> **Question: is a 153-point improvement in `angle_error` visible?**

## 2. Why this experiment and not a VLM

The acceptor-before-eyes ordering is forced, and a VLM cannot arbitrate here:
GamiBench (372 origami crease patterns) measures frontier MLLMs' foldability
signal as *anti-correlated* with truth — GPT-5 flags actually-impossible folds
8.4% of the time while flagging **valid** folds as impossible 24.6–25.0%. A VLM
judge whose target metric has never been validated cannot distinguish "the pose
is bad" from "the metric is meaningless". A human answers this once; after that
it is settled for every route.

## 3. Conditions and captures

Reference base: `mcp_harness/tests/goldens/dog.fold` → `complete_square(raw,1,1)`
→ `shaping.apply_display_ops(sq, [], raw=raw)` (the `probe_dog_folds` served
path). Step 0 verified the incumbent site binds to itself at distance 1.0e-09
(bound 1e-6) and that `front_v18` sits at its pinned reference coords.

Incumbent op, verbatim from `2026-07-12-handoff-b5-prime-outcome.md`:

```
outside:0.0,0.46801304:0.12398308661620648:142.5
```

| id | condition | n captures | why |
|---|---|---|---|
| `BASE` | unshaped served dog | **2** | one is the comparison arm; the second exists ONLY to build the null pair |
| `SHAPED` | served dog + incumbent op | **3** | shaped re-reads drift ±7°, and `front_v18` is a known park risk (it parked 3/3 at θ=30 in the front-lever wave) |

Total: **5 headed captures**, each via `capture_checked(attempts=3)` so a
parked read is retried rather than scored. A capture failing `DISP_GATE` (0.10)
is discarded, not scored — parking is a known confound, not a result.

## 4. Rendering (fixed before any image exists)

7 fixed views per capture, from the bridge's `foldedGeometry` payload
(`vertices_coords` + `faces_vertices` from one buffer, so index spaces are
self-consistent). Rendered offline with matplotlib — **zero extra browser cost**.

Every render parameter is **identical across conditions**: same 7 camera
directions, same projection, same face colour, same edge weight, same lighting,
same axis limits computed from the *union* of both conditions' bounding boxes,
no labels, no axes, no legend, no filename visible in the image. Renders differ
in geometry and in nothing else. Any render-side asymmetry would let the judge
identify the condition from an artefact rather than from the model.

## 5. Blinding

- Each capture is assigned an opaque id (`A`, `B`, `C`, …) by a seeded shuffle.
- The mapping id → condition is written to a file that is **not shown to the
  judge** until after their answers are recorded.
- Pairs are presented with left/right position randomised by the same seed.
- **Claude gives no read of the images until after the judge's answers are
  recorded**, so Claude's opinion cannot anchor the judgment.

## 6. Pairs presented

| pair | left/right contents | type |
|---|---|---|
| P1 | BASE vs SHAPED#1 | test |
| P2 | BASE vs SHAPED#2 | test |
| P3 | BASE vs SHAPED#3 | test |
| P4 | BASE vs BASE (the second capture) | **NULL** |

The null pair is the vacuity control, and it is the reason the second BASE
capture is worth a browser slot. Two captures of the *same* fold differ only by
solver drift. If the judge confidently picks one as "more dog-like" **and names
limb groups in it**, the instrument is measuring expectation, not the model.

## 7. Questions asked of the judge (fixed wording)

For each pair, in this order:

1. *"Which of these two is more dog-like — left, right, or no difference?"*
2. *"In the one you picked, name any body parts you can identify (e.g. head,
   front legs, back legs, tail). If none, say none."*
3. *"Same question for the other one."*

## 8. Outcome criteria — PINNED

Let `k` = number of **test** pairs (P1–P3) where SHAPED was picked as more
dog-like. Let `g` = number of distinct limb groups nameable in SHAPED renders
and **not** nameable in BASE renders.

| verdict | condition |
|---|---|
| **VOID** | the NULL pair (P4) is called with a confident preference **AND** limb groups named in the preferred side. The run is void regardless of P1–P3. |
| **PASS** | `k == 3` **AND** `g >= 2` |
| **SPLIT** | `k >= 2` **AND** `g < 2` |
| **FAIL** | `k <= 1` **OR** no limb group is nameable in any render of either condition |

Anything not matching a row above is reported as **INCONCLUSIVE**, not
massaged into the nearest row.

## 9. What each outcome routes to

- **PASS** → `angle_error` is a valid proxy at ~100° scale. The 119.14 pose is
  worth shipping, and the vocabulary/objective routes are worth costing because
  the ladder they climb is real.
- **SPLIT** → the proxy has *sign* but not *magnitude*. A legibility-calibrated
  acceptor must be built before any further search.
- **FAIL** → the entire measured shaping ladder is un-anchored. Routes B–E stop:
  none can be evaluated, because the number they move has no product meaning.
  The honest successor is to change *what* is shaped (narrowing — which our
  vocabulary grep-confirmably lacks) rather than how it is searched.
- **VOID** → the protocol failed, not the hypothesis. Re-run with a stronger
  blind.

## 10. Declared limitations (stated before, not after)

- **n = 3 test pairs and 1 null.** This is a screening experiment. It is
  well-powered for the FAIL case (two illegible blobs are visible at n=1) and
  **under-powered for a marginal PASS**. Bounding a null within ±0.10 would need
  n≈97 paired items; detecting 0.75-vs-chance needs n≈29. A PASS here licenses
  *further* work, never a shipped claim about legibility in general.
- **One subject** (the dog), one op, one θ. Nothing here generalises to other
  bases or to the vocabulary as a whole.
- **The same BASE render appears in all four pairs**, so the judge sees it four
  times. Order randomisation does not remove that familiarity effect. It biases
  toward the judge finding *any* difference, which makes a FAIL more meaningful
  and a PASS less so — the conservative direction for our routing.
- Shaped states are strained compliant equilibria, not rigid states (measured:
  closure residual 1.03 at the prescribed angles, global minimum only at fully
  flat). The captured geometry is solver-dependent by construction; the 3
  shaped reads exist to expose that spread.
