# Shaping composition: make `edges_foldAngle` survive an op

**Status:** design, approved 2026-08-09.
**Scope:** `mcp_harness/shaping.py`, `mcp_harness/shaping_deep.py`. Deterministic,
browser-free. **The B5-prime Gate-2 re-run is deliberately NOT in this spec** —
see §8.

## 1. The defect

`edges_foldAngle` appears in `shaping.py` and `shaping_deep.py` **exactly twice
— both writes, zero reads**:

```python
# shaping.py:313  (and shaping_deep.py:417, identical shape)
out["edges_foldAngle"] = [
    overrides.get(i, {"M": -180.0, "V": 180.0}.get(k, 0.0))
    for i, k in enumerate(ea)
]
```

Each op rebuilds the whole array from `edges_assignment` plus **its own**
overrides. Any partial angle a previous op set is not in this op's `overrides`,
so it falls back to the assignment default and is reset to full ±180.

The implemented operator is therefore `op_N ∘ flatten(everything prior)`, not a
composition. `apply_display_ops` (`shaping.py:358`) chains ops precisely this
way — each against the previous output — so the defect fires on every
multi-op call, and reaches production through `web/server.py:372`.

**Measured** (2026-08-09, `dog.fold` + the arc's incumbent recipe, then a second
op): **5 of 5 of op1's overridden angles reset, total |Δ| = 225.0°, every one
monotonically toward MORE fold.**

### Why this matters beyond correctness

B5-prime's Gate 2 measured composition as **anti-additive** — median
`|pred − meas| = 127.11°` over 7 pairs against a threshold of 15 — and recorded
that pairs **overshoot** (best-predicted pair measured 204.7 vs predicted 95.5).
That negative fired the pre-pinned descent downgrade and redirected the entire
shaping arc.

A defect that flattens all but the last op predicts **exactly monotone
overshoot**: the composed state carries more fold than either op intended, so it
moves further than the additive predictor expects. This is an *unexcluded
implementation explanation* for the arc's most consequential negative. This spec
does not test that hypothesis — it removes the confound so the hypothesis
becomes testable.

## 2. Prior art (CLAUDE.md §0)

| source | finding | adapted / rejected |
|---|---|---|
| **FOLD spec** (Ballinger, Demaine et al.), `edges_foldAngle` | Signed dihedral in **degrees**; **positive = valley, negative = mountain, 0 = flat/unassigned/border**; "the sign of `edge_foldAngle` should match `edges_assignment` if both are specified". **The spec is silent on what happens to edge attributes when an edge is subdivided.** | **Adapted:** the sign/default convention is exactly what the current fallback dict encodes, so seeding from assignments remains the correct *default*. **Consequence:** because the standard does not decide subdivision inheritance, §4 must state our rule explicitly rather than appeal to the format. |
| **Persistent-naming problem in parametric CAD** ([review](https://www.sciencedirect.com/science/article/pii/S1110016818300814), [KAIST macro-parametrics](https://academic.oup.com/jcde/article/3/2/161/5743368)) | The canonical failure is an attribute referenced on an edge that fails to survive a split — "the edge referenced by the fillet feature is split into two edges… contrary to expectations, the left edge is not rounded". Robust solutions need **topology plus geometry**, because feature re-evaluation does not preserve indices. | **Named, machinery consciously rejected.** Our bug is the same class, but `_split_edges` reuses the original index for the first fragment and only appends the rest, so indices *are* stable within a single op. Index-parallel propagation is sufficient. **This is a precondition, not a law** — §7 records it as the risk to guard. |
| **In-repo: `_split_edges` (`shaping.py:221`) `ea.append(ea[ei])`** | The module already has a working attribute-propagation idiom for `edges_assignment`. | **Adopted verbatim.** The fix is the parallel line, not a new mechanism. This is why approach B (post-hoc merge in `apply_display_ops`) was rejected: it reinvents a remap the splitter already performs. |
| **In-repo: `square_complete.py:104`** | `out = dict(fold)` shallow-copies, then replaces `edges_vertices`/`edges_assignment` with **longer** arrays and never touches `edges_foldAngle`. An input carrying fold angles therefore exits with **angles shorter than assignments**. | **Adapted as a guard.** The seed in §4 must not trust the incoming array's length. Recorded as a latent defect in a *different* module; fixing it is out of scope here (§8). |
| **In-repo: Origami Simulator `pattern.js:16`** | `foldData.edges_foldAngle = []; //target angles` — the vendored solver consumes this field as the **actuation target**, not as decoration. | **Motivates the whole fix.** A reset angle is not a cosmetic discrepancy; it changes what the simulator is asked to fold, which is what every capture in the arc measures. |
| **Project memory `shaping-legibility-calibration-outcome`** | Recorded that fixing this "needs an edge-identity remap, not a merged overrides dict". | **Partially superseded, recorded here.** The remap is real but already implicit in `_split_edges`; no new mapping structure is needed. The "not a merged overrides dict" half stands and is why approach B was rejected. |

## 3. What changes — four sites, two of them shared

`shaping_deep.py:20-21` imports `_find_tip`, `_key`, `_march_arm`, `_rot` and
`_split_edges` **from** `shaping.py`. So:

| # | site | change |
|---|---|---|
| 1 | `shaping.py:205` `_split_edges` | accept an optional fold-angle list; append `fa[ei]` on the same line that appends `ea[ei]`. **Shared by both modules.** |
| 2 | `shaping.py:109` `_find_tip` | bound the argmin; refuse beyond it. **Shared by both modules.** |
| 3 | `shaping.py:313` | seed from the incoming array; build output as `overrides.get(i, fa[i])` |
| 4 | `shaping_deep.py:417` | same as 3 |

Plus one semantic change, §5.

## 4. The angle-inheritance rule

Stated explicitly because the FOLD spec does not decide it (§2).

> **A fragment of a split edge inherits the parent edge's fold angle.**

Justification: subdividing a crease at an interior point does not change the
dihedral angle anywhere along it. This is the same reasoning that already
justifies `ea.append(ea[ei])` for the assignment.

**Seeding.** Each op derives its working array as:

- the incoming `fold["edges_foldAngle"]` when present **and** of the same length
  as `edges_assignment`;
- otherwise the assignment-derived default `{"M": -180.0, "V": 180.0}.get(k, 0.0)`.

The length check is not defensive padding — `square_complete` demonstrably
produces the mismatch (§2). A mismatched array is **discarded wholesale**, not
padded: a partially-valid angle array cannot be distinguished from a stale one,
and silently padding would attribute one model's angles to another's edges.

**Growth.** New edges appended for the wedge arms receive their angle from
`overrides`, exactly as today.

## 5. The `body_seg` semantic change

`shaping.py:294` currently reads:

```python
overrides[body_seg] = s * 180.0        # s = +1 if the axial is V, else -1
```

This forces the body-side fragment of the split axial crease to full fold. It
becomes:

```python
overrides[body_seg] = fa[axial]
```

**This is provably a no-op on every existing single-op path.** `s` is `+1`
exactly when `ea0[axial] == "V"`, and the seeded default for `V` is `+180.0`
(and `M` → `−180.0`), so `fa[axial] == s * 180.0` whenever the axial crease
carries its default. The two expressions differ only when a prior op left that
crease partially folded — which is the case this spec exists to fix.

Without it, a second op **on the same tip** still destroys the first op's work:
after op1 the tip's single remaining M/V crease is `tip_seg`, carrying op1's
partial `tip_angle`; op2 would select it as its axial and overwrite it with
±180.

Note this case does **not** arise in the Gate-2 pairs — `pose_coupling.py`
enforces at most one op per site — but `apply_display_ops` permits it and the
agent can emit it.

### `shaping_deep` needs no equivalent change, and why

`shaping_deep.py` has no `body_seg` line. It does have a structurally similar
one:

```python
# shaping_deep.py:334-335
old_angle = 180.0 if raw_ea[c.edge] == "V" else -180.0
new_angle = old_angle * (180.0 - 2.0 * theta) / 180.0
```

This derives the new angle from the **nominal** ±180 rather than from whatever
angle the crease currently carries — the same "ignore the incoming state" shape
as the main defect. It is nonetheless **correct as written**, because
`apply_display_ops` (`shaping.py:377-381`) refuses a deep op that follows any
tip-local op or a second deep op: *"at most one deep op (reverse_deep/sink), and
before tip-local ops"*. A deep op is therefore always the first shaping op to
run, so `c.edge` cannot yet carry a partial angle.

**That ordering constraint is load-bearing for this line and must not be relaxed
without revisiting it.** Recorded here so a later reader does not "fix" line 334
in isolation, and so that anyone relaxing the ordering rule finds the dependency.
The line is left unchanged by this spec.

## 6. The `_find_tip` bound

`_find_tip` computes `dist` and returns only `(vertex, axial_edge)`, discarding
it. It is an unbounded argmin: a probe at `(99, 99)` binds a tip at distance
**138.61** and reports success.

> **Refuse when the nearest qualifying tip is farther than `TIP_BIND_MAX = 0.05`
> paper units.** Raise `ShapingError` naming the requested point, the bound, and
> the distance found.

### Derivation

Measured 2026-08-09 over `mcp_harness/tests/goldens/`, counting vertices
`_find_tip`'s own predicate accepts, before and after `complete_square`:

| golden | raw → served tips | min served spacing | half |
|---|---|---|---|
| hf-dog-nudged | 11 → 7 | 0.020479 | **0.0102** |
| dog-repaired | 18 → 8 | 0.145802 | 0.0729 |
| dog | 16 → 8 | 0.174600 | 0.0873 |
| star-4 | 8 → 8 | 0.500000 | 0.2500 |
| hshape | 8 → 4 | 0.589256 | 0.2946 |
| hf-crane-ladder-blb | 7 → 2 | 0.635996 | 0.3180 |
| quad | 6 → 3 | 1.003812 | 0.5019 |
| hf-dog-ladder-best | 7 → **1** | — | — |
| bear-base | 1 → 1 | — | — |

`0.05` sits below half the minimum served spacing on **6 of the 7** goldens with
≥2 served tips, so on those a bind within the bound is provably unambiguous.

### What the bound does and does not buy

**Does:** refuse requests for tips that no longer exist. This is the case that
fires in production — `complete_square` roughly halves the addressable tip set
(dog 16→8, quad 6→3, hshape 8→4 = exactly 0.500), and `hf-dog-ladder-best` drops
to a **single** served tip, so today *every* request on that model binds to it
regardless of distance.

**Does not:** prevent binding to the wrong flap on a dense model. `hf-dog-nudged`
has served tips 0.020479 apart; no absolute bound both admits legitimate requests
and separates those. That is an ambiguity problem and this spec does not solve
it. Recorded here so a later reader does not assume coverage that was never
claimed.

`TIP_BIND_MAX` is a module constant, stated in the refusal message. It is
**not** a tuning knob: if a legitimate workflow needs a larger bound, that is a
finding about the workflow, to be recorded rather than absorbed by raising the
constant.

## 7. Error handling

- `_find_tip` raises `ShapingError` on refusal. This is already safe:
  `apply_display_op` catches every exception and returns the input fold
  unchanged, logging one line to stderr, so the fold stream never breaks.
- A length-mismatched incoming angle array is discarded silently and reseeded
  from assignments. Silent because it is `square_complete`'s normal output and
  warning on it would fire on every served base.
- No new failure mode is introduced in `_split_edges`: the appended angle is
  always read from an index that exists, because `fa` is seeded to the same
  length as `ea` before any split.

## 8. Non-goals

Each of these is deliberate, with its reason:

1. **The B5-prime Gate-2 re-run.** Its outcome is unknown, so it needs its own
   pre-registration written before any reading, and its harness
   (`probe_dog_coupling.py`) needs a headed `SimSession`. Putting an
   unknown-outcome experiment in the same plan as the code it tests is how
   iterate-to-green starts. It is the natural successor and is sequenced after
   this.
2. **`square_complete`'s length mismatch.** Real (§2) but in a different module
   with a different blast radius. Guarded against here, not fixed here.
3. **The `complete_square` tip-set halving.** Letting ops address unsquared
   geometry would roughly double the action space at near-zero cost, but it
   widens the change into the display pipeline. Quantified here (§6) so the
   decision is informed when it is taken.
4. **Wrong-flap ambiguity** (§6).
5. **`crimp`/`squash` reaching `parse_op`.** `squash` is a *decided negative* —
   `probe_squash.py` proves every closure-clean, Maekawa-valid symmetric squash
   on an edge flap is `reverse_fold` relabelled. Do not re-file it.
6. **Any new shaping primitive**, including narrowing. The vocabulary gap is
   real and is not this spec.

## 9. Testing

**The headline test** — the one-sentence pre-registerable claim:

> After `apply_display_ops(fold, [op1, op2])` with `op1` and `op2` at different
> sites, every edge `op1` overrode still carries `op1`'s angle.

**The load-bearing test** is different and more important:

> **Single-op output is byte-identical to today, on every golden.**

If this fix changes any single-op result it silently moves every committed
number in the arc, including P1's capture fixture. §5 argues the equality; the
test must *verify* it rather than assume it. **A single-op difference on any
golden is a STOP, not a re-baseline** — it means the seed or the `body_seg`
change is not the no-op this design claims, and the design is wrong.

Also:

- `_split_edges` propagates the parent angle to every fragment, including the
  index-reusing first fragment.
- A mismatched-length incoming array is discarded, not padded.
- `_find_tip` binds within `TIP_BIND_MAX` and refuses beyond it, with the
  distance in the message; the refusal reaches `apply_display_op` as an
  unchanged fold plus one stderr line.
- Same-site composition (§5) preserves op1's `tip_seg` angle.
- Both modules: `shaping_deep`'s output construction gets the same coverage as
  `shaping`'s, since they are independent code paths sharing two helpers.
- **The deep-op ordering guard holds.** A `reverse_deep:`/`sink:` op following a
  tip-local op is still refused. This is now load-bearing for `shaping_deep.py:334`
  (§5), so it needs a test that fails if the guard is relaxed — not merely a
  comment.

## 10. Risks

1. **Index stability is a precondition, not a law** (§2). If a future change
   makes `_split_edges` renumber rather than append, angle propagation breaks
   silently — the array stays the right *length* while the entries refer to the
   wrong edges. The fragment-propagation test is the tripwire; it must assert
   *which* edge carries the angle, not merely that the lengths match.
2. **This fix changes nothing P1 measured.** P1's fixture is single-op with bind
   distance 1e-9, so neither defect fired there. Anyone expecting the projection
   metric to move will be disappointed; that is not what this is for.
3. **A green Gate-2 re-run would not by itself vindicate composition.** If
   `|pred − meas|` drops below 15 after this fix, the honest claim is "the
   previously measured anti-additivity was substantially an artifact" — not
   "composition works". The additive predictor would still need its own
   validation on the corrected operator.
4. **`crimp` is the canonical victim.** It is the tool layer's only composed
   primitive, so every `crimp` call has been hitting this defect. Its shipped
   behaviour will change. That is the point, but it means `crimp`'s existing
   characterisation — including the θ=90 mis-targeting recorded in memory —
   was measured on the broken operator and must be re-read, not carried forward.

## 11. What this establishes, and what it does not

**Establishes:** that shaping ops compose — that `apply_display_ops` implements
the operator its docstring claims, verified arithmetically without a browser,
a judge, or a legibility criterion.

**Does not establish:** that composed ops produce better models, that
anti-additivity was a bug, or anything about legibility. Those need the Gate-2
re-run and its own pre-registration.
