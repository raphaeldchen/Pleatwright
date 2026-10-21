# Why the compiled dog's front flexes are totally obstructed: the flat-state cokernel theorem + universal-molecule overdetermination

**Task 6 [M1-b] mechanism note — 2026-07-14.**
Derivation-first protocol: every prediction below was written to the SDD
derivation ledger (`.superpowers/sdd/task-6-derivation-ledger.md`, timestamped)
BEFORE its numeric check ran; the prediction tables are pinned as tests in
`mcp_harness/tests/test_molecule_mechanism.py`. Verdict: **ending (a) — the
account is verified** (M1 gate: predictions held on ladder rungs of distinct
topology, then out-of-sample on the dog, 29/29).

Notation: `J` = the assembled per-interior-vertex SO(3) closure Jacobian at the
flat state (`flex_extension.assemble`); `Q(w,w)` = the central-difference
quadratic `(R(hw)+R(-hw))/h^2`; defect = `||(I-JJ+)Q||`; rel = defect/`||Q||`;
w in kernel convention unless stated.

---

## §1 The observed lock

- The served dog (squared quadruped compile, dof 3): the front-selective
  first-order flex w* (r* = 1.76272) has defect = ||Q|| = 0.095625, **rel = 1.0
  to machine precision** (h-stable to 9.4e-10). The entire quadratic lies
  outside range(J). Defect carriers: v5 (deg-6, 0.062), v0 (0.046), v1 (0.043),
  v4 (0.024), v10 (0.021), then v7, v6, v11.
  (`mcp_harness/probe_flex_extension.out.json`.)
- Uniformity: all 12 completed funnels of the 144-candidate tree-space search
  read rel_fine = rel_coarse = 1.0 to machine precision; zero near-passers
  (`mcp_harness/structural_search.out.jsonl`).
- The plan's calibration contrast — "a generic degree-4 kernel direction has
  defect 0.336, *partial*, NOT 1.0" — was a **misread** of an absolute defect:
  measured this session, that direction's rel is also exactly 1.000000000000
  (q_norm = defect = 0.336012968). There is no partial-defect regime at any
  flat state; see §2. The true anchor contrast is different: *extending*
  directions have Q = 0 identically (branch-tangent q_norm ~ 1e-10 at the
  finite-difference floor), never a nonzero Q inside range(J).

## §2 The mechanism

### 2a. Theorem Z (flat-state cokernel): rel = 1.0 is a theorem, not a dog anomaly

At the flat state every crease axis is an in-plane unit vector, so every column
of every 3-row vertex block of J is in-plane: **J's z-rows are identically
zero** (measured: exactly 0.0 on every fixture and the dog). Hence
range(J) ⊆ {z = 0 in every block}.

The residual along a straight ray, R(tw) = log Π_i exp(t w_i Â_i), expands by
BCH into nested brackets of in-plane generators. Brackets alternate planes:
[in,in] ∝ ẑ, [in,z] ∝ in-plane — so **every even t-order is purely
z-directional, every odd order purely in-plane**. The central difference kills
odd orders. Therefore, in exact arithmetic, for any first-order flex w of any
flat developable pattern:

- per genuine vertex, `Q_v(w,w) = kappa_v(w) ẑ + O(h²) ẑ`, where
  `kappa_v(w) = Σ_{i<j} w_i w_j sin(θ_j − θ_i)` over the vertex's M/V creases
  in CCW order — equal to **2× the signed area of the closed "flex polygon"**
  with edge vectors `w_i (cosθ_i, sinθ_i)` (closed because Jw = 0; the area is
  invariant to the cyclic starting crease on kernel directions);
- per pinned (squaring-artifact) block, Q_v = 0 exactly (the residual is
  linear in the lone fold angle).

Consequences, all verified quantitatively:

1. Q is z-supported and range(J) is z-free ⇒ defect ≡ ||Q|| and **rel ≡ 1.0
   for every flat pattern and every flex with kappa ≠ 0** — the dog, all 12
   funnels, the degree-4 phantom, and every ladder fixture alike. The uniform
   1.0 the search found was over-determined to happen.
2. **Second-order extension ⟺ kappa_v(w) = 0 at every genuine vertex**
   ("zero-area flex polygon everywhere"). The lock question becomes: does the
   first-order kernel contain a common zero of the per-vertex area forms?
3. The account is exact: on the dog, per-vertex signed defect components equal
   the pure-geometry kappa_v(w*) to ~1e-12, and q_norm = sqrt(Σ kappa_v²) to
   1e-11 (P0.3). Sign convention: measured z = +kappa (CCW order).

Instrument corollaries (calibration facts for anyone using
`obstruction_verdict` near the zero cone): on a kappa = 0 direction the
straight-ray probe still picks up the *fourth*-order z-term, q_norm ≈ |c₄|h²,
giving the signature scaling `q_norm(h=1e-3)/q_norm(h=1e-4) = 100.00`
(measured exactly on full-precision witnesses); rel stays 1.0 even in that
regime (z-parity), so EXTENDING can only ever be read via the q-norm floor.
Witness directions must be supplied at full precision — truncating to 6
decimals reintroduces kappa ≈ 2.6e-7 which dominates the read.

### 2b. Where the area forms come from in the universal-molecule construction

The interior vertices of a compiled UM pattern come in exactly the types tmPoly
builds (`tmPoly::BuildPolyContents`, tmPoly.cpp:663–1155; crease creation at
:995–1105):

- **Hub nodes** (deg-6+): triangle polys inset to the incenter
  (tmPoly.cpp:697–711), quads to the first skeleton event (:713–995) — ridge
  spokes meet hinge tops. Sector signature: adjacent equal pairs
  ([44,44,66.9,66.9,69.1,69.1] at the dog's v5). Restricted to a *single
  molecule's* kernel the hub area form has signature **(1,3)** — one positive
  direction, three negative — measured identically on the rabbit-ear incenter
  and both gusset hubs.
- **Hinge-top ridge crossings** (deg-4): every axial-path vertex projects onto
  every reachable ridgeline (`ProjectPtoQ` + `GetOrMakeCrease(...,
  UNFOLDED_HINGE)`, tmPoly.cpp:1035–1040), creating flat-foldable deg-4
  vertices along ridges (dog v0/v1/v6/v7; indefinite (1,1) restricted forms).
- **Axial feet / T-germs** (deg-4, sectors [90,90,90,90]): hinges from the two
  polys sharing an axial path meet at the same tree-node foot. Closure forces
  the two collinear pairs equal (w₃ = w₁, w₄ = w₂) and the area form
  **factorizes: kappa_T = 2 w_axial w_hinge** — a pure hyperbolic (±λ) product
  germ. Second order forces `w_axial · w_hinge = 0`: at every foot, a flex must
  *shut off* either the axial line or the hinge (measured on the composite:
  eigs exactly ±0.410831; z at T = 2w₁w₂ to 2e-12).
- **3-active-crease vertices**: where the global kernel supports only 3 of a
  vertex's 4 creases, the local flex is 1-dimensional and its kappa is a
  nonzero constant ⇒ the restricted form is **rank-1 sign-definite**
  (λ(u·c)²) — a linear shut-off hyperplane (dog v4, v10: eigs [0,0,+0.048],
  [0,0,+0.042]).

### 2c. Why single molecules flex but the compiled network locks

Counting at the flat state: each genuine vertex contributes at most 2 to
rank(J) (its z-row is trivial), each crease one unknown.

- **Raw single molecules are underdetermined at second order.** Rabbit ear:
  6 creases − rank 2 = kernel dim 4, ONE area form. Since range(J) at a lone
  vertex covers the full in-plane R², the implicit function theorem reduces the
  local variety to {g = 0} for a single scalar g on the kernel with Hess g =
  kappa|ker: nondegenerate indefinite (1,3) ⇒ by Morse, **every zero-area
  direction is tangent to a genuine finite fold**. Measured: designated flexes
  with kappa ≠ 0 die (rel 1.0), while every witness on the zero cone
  continues to the amplitude cap (max_fold ≈ 0.5). Same story for the gusset
  (dim 7, 2 forms) and the composite (dim 8, 3 forms): joint zeros abound.
- **The compiled + squared network is overdetermined.** The dog: 38 creases,
  15 genuine vertices + 8 pins ⇒ rank 35 ⇒ **kernel dim 3**, with **8 active
  area forms** restricted to it (the other 7 vertices are kappa-dead: the
  kernel routes around the T-germs/ridge crossings v2/v3/v8/v9 and never
  activates a folding pair at the spine vertices v22/v23/v24). Eight quadrics
  on a projective plane, including two rank-1 *definite* germs (v4, v10 —
  hyperplane conditions) and two near-definite hub cones (v5: eigs
  [−0.0011, 0, +0.078]; v11: [−0.0004, 0, +0.084] — thin cones): the joint
  real zero set is **empty**. Dense sphere sweep + refinement:
  `min over the unit kernel sphere of ||kappa|| = 0.0225875` — bounded away
  from zero — so **the ENTIRE 3-dim flex space is second-order locked**, not
  just w*. (Out-of-sample D4: instrument-measured defects of the three
  designated dog flexes, the minimizer, and 25 random kernel directions all
  equal their analytic predictions to 6 digits; all NON_EXTENDING.)

In one sentence: **flatness forces every second-order obstruction into the
cokernel (rel = 1.0 exactly, Theorem Z), and the universal-molecule network —
hubs + hinge-top crossings + T-germ feet chained by TreeMaker's construction —
collapses the first-order kernel to dimension 3 while leaving 8 active vertex
area forms on it, two of them sign-definite, so no first-order flex has
zero-area polygons everywhere and every flex (front-selective or not) dies at
second order.**

## §3 The ladder: predict → measure

All predictions were ledgered before measurement (ledger sections R1/R2/R3/D4
with timestamps). Cumulative score: **26/26 kappa ≠ 0 designated flexes
matched to 6 printed digits** (defect, q_norm, rel = 1.000000000, carrier sets
in order, signed per-vertex values, coarse/fine ratio 1.000, verdict
NON_EXTENDING); 3/3 exact-ray flexes and 5/5 full-precision witnesses in the
predicted small-q regimes; 3/3 witness continuations reached the amplitude cap.

| rung / instance | kernel dim (pred=meas) | forms (pred=meas) | designated flexes | witnesses |
|---|---|---|---|---|
| rabbit_ear scalene | 4 | incenter (1,3): eigs [−0.4537, −0.4143, −0.2808, +0.8567] | 4/4 NON_EXT, defects .397342/.339374/.779551/.334885, carrier {incenter}, signs −,−,+,− | zero-cone w0: q_fine 2.4e-11, ratio 100.00, continuation to cap |
| rabbit_ear equilateral | 4 | (1,3): [−0.4330, −0.4330, −0.2887, +0.8660] | 3 NON_EXT (.126991/.131499/.030186) + flex_3 exact ray (q = 3.5e-17, EXTENDING via floor) | — |
| gusset_quad trapezoid | 7 | hubs (1,3): [−0.4182, −0.3595, −0.1816, +0.5760] and [−0.4491, −0.3193, −0.1306, +0.5877] | 6/6 NON_EXT, two-hub carriers in predicted order/signs (e.g. flex_0: v1 −0.324594, v3 −0.014732) + flex_6 exact joint ray (q = 1.5e-16) | joint zero of both hubs: q_fine 7.5e-11, ratio 100.000, continuation to cap |
| gusset_quad square (preliminary base) | 6 | center (1,5): [−0.5, −0.5, −0.25, −0.25, −0.2071, +1.2071] | 6/6 NON_EXT (.165776/.015575/.396527/.286891/.156829/.083333) | q_fine 8.0e-11, ratio 100.000 |
| composite_two scalene | 8 | twin hubs identical (1,3): [−0.4417, −0.3335, −0.2113, +0.7195]; T hyperbolic ±0.410831 | 8/8 NON_EXT incl. 3-vertex localization and the single-carrier flex_7 ({v1}, 0.015763); T product identity z = 2w₁w₂ to 2e-12 | joint zero of 3 forms: q_fine 1.8e-11, ratio 100.000, continuation to cap |
| composite_two equilateral | 8 | hubs (1,3): [−0.4330, −0.3576, −0.2040, +0.7420]; T ±0.408248 | 7/7 NON_EXT + flex_7 exact ray (1.2e-16) | q_fine 1.3e-11, ratio 100.000 |
| **dog (out-of-sample)** | 3 | 8 active forms; v4/v10 rank-1 definite; hubs near-definite; v22/23/24 exactly dead | flex_0/1/2: defects .075276/.105324/.117578, carriers/signs exact; front-cluster (v5,v0,v1) vs back-cluster (v11,v7,v6) factorization with ~1e-4 leakage | **no witness exists**: min ‖kappa‖ = 0.0225875 measured at the predicted minimizer; 25/25 random directions match analytic; whole kernel locked |

One sub-prediction failed and was diagnosed (ledger R1): the ratio-100 law was
first tested on a 6-decimal-truncated witness, whose kappa (2.597e-7) exactly
equaled the measured q_norm — input truncation, not an account error. The
revised statement (full-precision witnesses; ratio law conditional on the
4th-order regime) held on rungs 2–3 with zero further revision.

## §4 What would break the lock

The lock has two independent factors; a remedy must break the second (the
first is unbreakable at flat):

- (unbreakable) Theorem Z: at a flat state, obstructions live in the cokernel.
  No tree reweighting, node reordering, or jitter touches this — which is
  exactly why the 144-candidate search was structurally incapable of finding a
  near-passer (12/12 funnels rel = 1.0 was forced).
- (breakable) The joint area-form system on the kernel has no zero: an
  overdetermination + definiteness property of the compiled network.

Three move families, in decreasing directness:

1. **Kernel inflation at the definite germs (crease augmentation).** The
   sharpest levers are the rank-1 definite vertices (dog v4, v10) and the
   near-definite hubs (v5, v11). Adding one M/V crease at such a vertex
   (splitting a hinge into a crimp pair through the vertex, or restoring the
   "missing" fourth/sixth crease where the kernel supports only 3) adds one
   kernel dimension while adding **zero** new closure rows, and converts the
   local germ from definite to hyperbolic/indefinite (a flat vertex needs ≥ 4
   *active* creases to admit a zero-area flex; T-germs show the hyperbolic
   normal form). Success metric, checkable sim-free with this note's
   machinery: after augmentation, `min over the kernel sphere of ||kappa|| = 0`
   with the zero-cone direction having front-group support.
2. **Hub splitting (molecule-level move).** Replace incenter hubs by gusset
   pairs (triangle poly → quad poly with a forced gusset, tmPoly.cpp:800–880):
   the trapezoid rung shows the two-hub form pair still leaves a large joint
   zero set (dim-7 kernel, 2 forms). In tree terms this is realizable by
   moving from degenerate triangle polys to quads (edge-weight/strain design
   so the packing produces quad polys at the front cluster). This grows kernel
   dim faster than it grows active forms.
3. **Leave the flat state (state move, no crease change).** Theorem Z is a
   *flat-state* theorem: at any finitely folded serve state, J's columns
   acquire z-components, range(J) tilts out of the z-hyperplane, and rel = 1.0
   is no longer forced — obstructions become regular, solvable systems. This
   is the rigorous generalization of the z-lift lesson (flat-equilibrium root
   cause) and of Phase-S's routing: pose work on compiled bases should target
   folded states / shaping ops, not flat-state rigid flexes.

What will NOT work (ruled out by the mechanism): more tree-space search over
reweights/orders/jitters (the 12/12 uniformity is a theorem + open-condition
robustness of the germ signs, not bad luck); scaling paper or global affine
tweaks (kappa is scale-covariant, zeros are scale-invariant); relabeling M/V
(the instrument treats M and V identically as fold parameters).

## §5 Scope honesty

**Established (measured, predict-then-verify):**
- Theorem Z and the kappa pairing, exact on every substrate touched (degree-4
  anchor, 6 ladder instances, served dog): the derivation is general for flat
  developable patterns under this instrument (`assemble`'s genuine + pinned
  reductions).
- The dog-class claim: for THIS served/squared quadruped compile, the entire
  3-dim flex space is second-order locked (min defect 0.0226 ≈ 236× the
  verdict tolerance), carriers confined to the two hub clusters, front and
  back cluster modes factorized.
- Single UM molecules (rabbit ear, gusset, preliminary base, composite pair)
  are NOT locked: their zero-area cones are real and continuation-foldable.

**Not established / open:**
- No theorem that every UM-compiled multi-molecule pattern is fully locked.
  The counting (kernel collapse to dim 3 vs 8 active forms) was *measured* on
  the dog, and the 12 funnels share only the rel = 1.0 signature (their full
  kernels were not swept). A compile with a larger kernel or fewer active
  forms could in principle escape; the mechanism gives the checkable
  criterion, not a universal verdict. (Hence remedies are NOT built to fail:
  ending (a), not (b).)
- Second-order extension is necessary, not sufficient, for finite
  foldability: witnesses were continued to amplitude 0.5 rad without layer /
  self-intersection checks.
- The instrument reads EXTENDING only via the q-norm floor; on the zero cone
  its NON_EXTENDING verdicts are 4th-order reads, not second-order physics
  (§2a caveats; obstruction_verdict remains trustworthy-or-refusing for its
  designed go/no-go use).
- v2/v3/v8/v9's kappa-deadness on the dog is numerical (≤ 4.3e-9, compiled
  coordinate noise), unlike the exact spine deadness (≤ 1e-16); the carrier
  confinement claim uses the 1e-7 bound.

**Artifacts:** predictions + timestamps in
`.superpowers/sdd/task-6-derivation-ledger.md` (uncommitted, session);
measured tables pinned in `mcp_harness/tests/test_molecule_mechanism.py`;
instruments in `mcp_harness/flex_extension.py` (additive helpers
`flat_area_forms` / `defect_z_split` / `cokernel_basis`, commit 0d990ff) and
`mcp_harness/molecule_fixtures.py` (Task 5).
