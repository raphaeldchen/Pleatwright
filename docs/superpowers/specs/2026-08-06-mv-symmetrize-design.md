# S2′ — σ-symmetric M/V search on the served `.fold`. Design spec.

**Goal 2 / G2b — the M/V assignment.** Status: **specced; S2′a is a prerequisite
(§2).** Pure Python. No claim on `TreemakerWrapper.cpp`.

Owns the defect S2a proved the engine **cannot** fix: geometry mirrors exactly,
mirror-image creases carry opposite fold directions. Every M/V label is forced
by the facet ordering, and relaxing that ordering yields patterns the
non-crossing oracle refutes — so the fix must be post-hoc on the `.fold`.

> ## ⚠ TWO CORRECTIONS TO WHAT I PREVIOUSLY REPORTED
>
> **1. My "quadruped needs two flips" result is REFUTED, twice, independently.**
> I measured `{17, 27}` as mirror-symmetric and surviving `layer_order` and
> called it a valid target. **It is Maekawa-dirty** (`maekawa 1`, `cp_audit` not
> clean) and therefore cannot fold flat. Through the shipped linter it costs
> `TEMPLATE_QUADRUPED` BENIGN→MIXED and `TEMPLATE_BIRD` **PASS→FAIL-LINT[REAL]**.
> Of 186 weight≤3 and 1156 weight≤5 symmetric candidates on each, **zero** are
> cp-audit clean. **The true minimum weight is 11.** I checked `layer_order` and
> never checked `cp_audit` — which is precisely the four-conjunct lesson in §3.
>
> **2. The dog has NO valid target — a PROOF, not an exhausted budget.** I
> reported "inconclusive, 6000 of ~32,384". Both numbers were wrong: the space
> is **2^35 = 34,359,738,368**, and a σ-orbit DFS with a Maekawa freeze prune
> **exhausts it in 1.7 s / 692,867 nodes.** 49,152 Maekawa-clean → 144 also
> arrangement-clean → **0 of 144 survive `layer_order`.** See §6.

---

## 1. The search space — three axes, and getting it wrong is easy

Parameterise by **one binary variable per σ-orbit**:

| orbit kind | flip set |
|---|---|
| **preserved** pair | `{}` or `{i, j}` |
| **swapped** pair | `{i}` or `{j}` — exactly ONE member |
| **σ-fixed** crease | `{}` or `{i}` |

**Every enumerated point is mirror-symmetric by construction, so symmetry costs
nothing to enforce.** ⚠ A first attempt searched only σ-*closed* orbit flips and
returned NONE everywhere — flipping **both** members of a swapped pair preserves
the swap.

**Exhaustive DFS with a Maekawa freeze prune** (cut when a vertex's last
incident orbit is decided and `|D_v + 2S_v| ≠ 2`). **No SAT, MILP or
branch-and-bound is needed.**

| subject | orbits | space | Maekawa-clean | +audit-clean | **+layer-consistent** | min weight |
|---|---|---|---|---|---|---|
| star-4 | 5 | 2^5 | 12 | 12 | **12** | 2 |
| star-5 | 11 | 2^11 | 72 | 16 | **12** | 2 |
| two-level-tree | 8 | 2^8 | 12 | 12 | **12** | 3 |
| **template-quadruped** | 19 | 524,288 | 576 | 8 | **8** | **11** |
| **template-bird** | 19 | 524,288 | 576 | 8 | **8** | **11** |
| star-6 | 17 | 2^17 | 432 | 48 | **4** | 10 |
| star-6-sym | 15 | 2^15 | 720 | 144 | **72** | 4 |
| **mesh-insect** | 18 | 262,144 | 720 | 36 | **24** ⚠ | 4 |
| **mesh-dog** | 35 | 34,359,738,368 | 49,152 | 144 | **0** | — |

Two agents reached these integers independently, from different folds and
different implementations. **Worst case 3.5 s per subject.**

**★ The enabling fact.** `flat_fold.py:168-172` returns the **same reflection**
for `"M"` and `"V"`. So faces, transforms, folded vertices and closure are
bit-identical under any relabel, and `layer_order`'s entire constraint system
(`pairs`, `covers`, `equalities`, `tacos`) is a function of that geometry
alone. **A relabel moves only the boolean seed of each `direct` constraint** —
precompute once (280 ms), re-run `_propagate` only: **0.109 ms mean when it
refutes**, versus 318 ms for the shipped full gate.

---

## 2. 🛑 S2′a FIRST — `layer_order` is missing an ADK constraint family

`layer_order._build_constraints:250` does `if a not in ("M","V"): continue`,
dropping every unfolded (**F**) crease — and **tortilla-tortilla is defined on
exactly those.**

| subject | missing constraints |
|---|---|
| mesh-dog | **196** |
| mesh-insect | **76** |
| template-quadruped, star-4, star-5, two-level-tree, star-6-sym | **0** |

**The gap is not uniform, and that is the good news.** The two template subjects
have **no gap**, so their 8 targets are sound today. **`mesh-insect`'s 24 targets
are PROVISIONAL.** The dog's 0 is robust — extra constraints can only refute
more.

⇒ **S2′a: close the gap before trusting insect.** It is the only item that can
invalidate a measured result in this spec.

⚠ Also found: **`star-6`'s STOCK compile FAILS `layer_order`**
(`taco-tortilla (5,8) through face 7`) on both oracles. That does not match the
recorded *"stock passes 8/8"* — check whether star-6 was in that eight.

### 2.1 ★★★ S2′a IS DONE (2026-08-07), and it invalidated MORE than insect

`layer_order` now carries all three families the `F` filter dropped. §1's table
and §2's table are both **superseded** where they disagree with the rows below.

**The one-line filter dropped THREE families, not one.** §2 counts only
tortilla-tortilla's *spanning* form (a face whose interior the flat edge passes
through). Two more need an `F` edge and were equally absent, because a flat
pair's two faces sit on OPPOSITE sides of their own edge and so are invisible to
a strictly-inside test:

| family | Justin / ADK name | quadruped | dog | insect |
|---|---|---|---|---|
| flat pair vs a face spanning its segment | tortilla-tortilla | **0** | **196** ✅ | 186 |
| two flat pairs sharing one folded segment | tortilla-tortilla | 6 | 41 | 15 |
| a flat pair over a taco's own segment | taco-tortilla | 32 | 14 | 6 |

**⇒ §2's "the two template subjects have no gap, so their 8 targets are sound
today" is FALSE.** Quadruped's gap is 38 constraints, and closing it takes its
σ-symmetric targets **8 → 0**. Only its *first-family* count was zero.

**Recount, old oracle → new** (independent re-implementation of the σ-orbit DFS;
orbits, Maekawa-clean and audit-clean columns reproduced §1 EXACTLY on eight of
nine subjects, including the dog's 49,152 → 144 → 0):

| subject | orbits | Maekawa | +audit | layer OLD | **layer NEW** | **+lint (§3's 4th)** |
|---|---|---|---|---|---|---|
| star-4 | 5 | 12 | 12 | 12 | 12 | **8** |
| star-5 | 11 | 72 | 16 | 12 | 12 | 12 |
| two-level-tree | 8 | 12 | 12 | 12 | 12 | 12 |
| **template-quadruped** | 19 | 576 | 8 | 8 | **0** | **0** |
| template-bird | 19 | 576 | 8 | 8 | 8 | **4** |
| star-6 | 17 | 432 | 48 | 4 | 4 | 4 |
| star-6-sym | 15 | 720 | 144 | 72 | 72 | 72 |
| **mesh-insect** | 28 ⚠ | 8,640 | 72 | 48 | **0** | **0** |
| **mesh-dog** | 35 | 49,152 | 144 | 0 | **0** ✅ | **0** |

★ **The last two columns count DIFFERENT things — always say which gate you
mean.** "layer NEW" is §3's first three conjuncts; the final column adds the
fourth (*the shipped Oriedita lint class is not worsened*). It only bites where
stock lints PASS, so it moves exactly two subjects: `star-4` 12 → 8 and
`template-bird` **8 → 4**. Everything else already lints `FAIL-LINT[BENIGN]`
stock, where nothing can worsen. On bird the discriminator is the single orbit
`{3,4,6,7}` — four candidates lint PASS, four `FAIL-LINT[BENIGN]`, reproducing
§3's own worked example exactly. This is what reconciles S2′a's **8** with the
planning session's **4**: both are correct, and the two implementations agree
on all 8 candidates through both the raw call and `mv_repair._layer_status`.
An unpruned control (all 524,288 points, Maekawa recomputed from scratch per
point) returns 576 → 8, so the DFS prune is sound.

⚠ **`mesh-insect` here is NOT the fold §1 measured.** Every other subject
reproduced to the integer; insect's structure did not (45 vertices / 84 edges /
48 M/V creases / **28** orbits, against §1's 18 and §2.2's 28 verts / 53 edges),
while its `mv_swapped 6`, residual `0.0`, 3 swapped pairs, `served_stage
'order'` and 8 served leaves all match the FROZEN scorecard row exactly. So the
fold measured here is the canonical served subject and §1's insect row is from
some other fold. §9's own warning applies: **pin subjects by TREE, never by
name.**

**⇒ S2′b's subject list is now bird, star-4, star-5, star-6, star-6-sym and
two-level-tree** (under §3's full four-conjunct gate: bird **4**, star-4 8,
star-5 12, star-6 4, star-6-sym 72, two-level-tree 12). Quadruped joins the dog
and insect with **no relabel-only symmetric-and-foldable target at all** — and
quadruped and bird, which §1 calls "identical combinatorics", now separate.

⚠ **`star-6`'s stock failure CONFIRMED, and it is not alone.** Measured on
stock `main` BEFORE any change: `star-6` refutes with `taco-tortilla crease
(3, 9) through face 1` (same family and subject as §2's report; the differing
offender is first-contradiction-found order between two implementations), and so
do `mesh-insect`, `template-insect` and `star-8`. **"Stock passes 8/8" is wrong
for at least two of the eight** — and it is a PRE-EXISTING reading, not
something S2′a caused: no verdict moved on any of 49 goldens, cases and
subjects.

**Direction, asserted not assumed.** Over the 20 orderable goldens/subjects:
**1,315 previously-forced relations, 0 lost, 0 flipped, 742 newly forced.** The
new families are equalities only, so they can tie variables together but never
seed a fact. What did move is *ambiguity*: `dog.fold` goes 138/284 forced →
284/284 and `template-quadruped` 96/172 → 172/172, so `stack_at` now returns a
total order where it used to raise `AmbiguousStack` (test pins updated). That is
**not** ADK's satisfiability result — this module still only propagates forced
relations and cannot decide that a total order EXISTS when one is not forced.

---

## 3. The gate — four conjuncts, and each one is load-bearing

```
cp_mirror.mirror_verdict(...).symmetric      AND
cp_audit.audit_fold(...).clean               AND
flat_fold → layer_order consistent           AND
the shipped Oriedita lint class is not worsened
```

**Required-fail input, from real data: the "2-flip" target itself.**
`template-quadruped` flips `{17, 27}` → symmetric ✅, `mv_swapped 0` ✅,
`layer_order` OK ✅ — **and `maekawa 1`, `cp_audit` NOT clean.** It cannot fold.

**Why `layer_order` alone structurally cannot catch it:** `flat_fold` is
M/V-blind (§1), so a Maekawa-violating relabel still produces a folded state
`layer_order` will happily order. **`layer_order` cannot see Maekawa.**
`mv_swapped == 0` alone remains vacuous — re-confirmed on all three bijective
subjects.

**Second required-fail — ranking, not filtering.** On `TEMPLATE_BIRD`, the only
S2′ subject whose stock lint is PASS, two winners score **identically** on
symmetry, cp_audit, layer_order and folded geometry, yet flips
`[8,9,10,13,17,24,25,26,27,40,45]` → **PASS** while
`[0,1,2,5,19,20,22,28,29,34,37]` → **FAIL-LINT[BENIGN]**. **S2′ needs a ranker,
not a first-hit** — the same lesson as slice A.

---

## 4. New module `mv_symmetrize.py` — do NOT extend `mv_repair`

Four source-verified blockers:

1. **Objective inverted.** `mv_repair.accept():335` — `if _summed(cand) >=
   _summed(base): return "reject"`. Every S2′ subject is cp-audit **clean**
   (`_summed == 0`), so **every candidate is rejected at every weight.**
2. **Two closed gates before it.** `solve_mv_repair():899` refuses
   `already_clean`; `server.py:1569` / `:422` call `_repair_and_annotate` only
   when `meta["clean"] is False`.
3. **Wrong symmetry predicate.** `Candidate.rank_key`'s `mirror_closed` wants a
   σ-**closed** flip set; a swapped pair needs exactly **one** member flipped,
   so real targets are deliberately not σ-closed.
4. **Wrong weight and wrong universe.** `MAX_TOOL_WEIGHT = 8` against measured
   minima of **11**; `search_repairs:546` restricts to creases with ≥1 audited
   endpoint, which can **split a σ-orbit**.

**Reuse verbatim:** `apply_flips` (already refuses non-M/V and
fingerprint-mismatched flips), `fold_fingerprint`, `structural_ok`,
`_edge_mirror`, LAW 1 (`D_after = D + 2S`) as the DFS prune, and
`cp_mirror.mirror_bijection` + `axis_reflector` for σ.

⚠ **Do not widen `mv_repair`'s gate** — that puts a symmetry objective inside a
defect-minimiser and changes shipped M/V on the ladder path.

---

## 5. Does a repaired pattern still fold to the same base? — YES, and it is a theorem

By §1, `flat_fold` maps both `"M"` and `"V"` to the same reflection, so **the
flat-folded base is provably invariant under any M/V relabel.** Measured to
confirm: bit-identical face transforms and folded-vertex arrays, unchanged face
counts (24 / 24 / 26) and closure error (2.27e-09 / 5.15e-10 / 1.02e-08) on
quadruped / bird / insect. **A symmetrized CP folds to the same animal.**

What *does* change is the **layer stacking** and the 3-D sim
(`sim_instrument.py:145-146` derives `foldAngle` from the assignment). That is
the point of the change, not a side effect.

⚠ **Do NOT scope this check to `leaf_node_locations`.** `server.py:200/276/347`
call it on the *packed tree*; **no call site reads `edges_assignment`.** It can
confirm invariance but can never detect a violation — the same vacuous-check
class as the Phase-2 STOP-IF.

**The one honest gap:** nobody has compared the *new* stacking to the stock one,
and nobody has asked whether relabelling **11 of 50 creases** (M11/V19 →
M16/V14 on quadruped and bird; insect unchanged at M13/V20) is acceptable to a
human folder. So: **not cosmetic** (the stacking genuinely changes), **not
anatomy-breaking** (the base is provably identical), **desirability
unmeasured.** 22% of the pattern relabelled is a visibly different crease
pattern, not a touch-up. Settle this before scoping the ship.

**QUAD is out of scope and cannot be brought in.** Its 6 offenders are M/V-vs-F;
`apply_flips` refuses non-M/V edges, and forcing F→V blows closure from 8.8e-10
to **0.717** with `mv_mismatched` still 4. Any plan listing QUAD as an S2′ target
is scoping a geometry change disguised as a relabel.

---

## 6. The dog — permanently out of scope, proven

`mesh-dog.fold`: V=50, E=99, 61 M/V creases, 5 swapped / 21 preserved / 9
σ-fixed. Space **2^35**. Exhausted in **1.7 s / 692,867 nodes**: 49,152
Maekawa-clean → 144 also arrangement-clean → **0 of 144 layer-consistent**.
Re-verified on the shipped slow path (`apply_flips → flat_fold → layer_order`)
for all 144, with zero fast-vs-slow mismatches. Seven distinct obstruction
sites, no dominant one (96× taco-tortilla `(36,41)`→face 36; 16× `(44,47)`→17;
12× `(34,35)`→11; …).

**Robust to §2's oracle gap** — adding constraints can only refute more, so 0
stays 0.

Under the weaker gate I was considering (symmetric + `layer_order`, no
`cp_audit`), 3,020,222 random symmetric samples also yielded 0 and a complete
search would cost **~43 CPU-days**. Do not pay for it; that gate admits
assignments that cannot fold flat.

⇒ **The dog's status in the first line of any S2′ PR: no relabel-only fix
exists. This is a proof.**

---

## 7. Prior art (CLAUDE.md §0)

| verdict | item | why |
|---|---|---|
| **ADOPT** | **Akitaya, Demaine & Ku, "Computing Flat-Folded States" (OSME 2024)** — five constraint families (antisymmetry, transitivity, tortilla-tortilla, taco-tortilla, taco-taco), proven equivalent to the pointwise definition, O(n³) | **The exact specification of the oracle S2′ needs**, and it is **not** in this project's landscape survey. Directly yields §2's missing family |
| **ADAPT** | `flat-folder` (Ku's reference implementation) | Browser-only, no Node/CLI. Port the missing families: ~40 lines for tortilla-tortilla bullet 1; ~200–300 for a full independent ADK implementation — which would also let us assert a total order **exists**, something `layer_order` cannot do today per its own `_layer_status` docstring |
| **REJECT** | **MILP M/V** (Chen et al., *Comp&Struct* 239:106328, 2020) | **A named item on this project's own landscape-survey adapt-list, and it is the wrong tool.** It models only *local* flat-foldability plus cycle detection, scoped to degree-4/6 tessellation vertices. On the dog it returns the 49,152 Maekawa-clean candidates and is **silent on the 144→0 step that decides the answer.** Adapt only the binary-variable idea, already present as LAW 1 |
| **REJECT** | T-join / min-flip parity | Correct for `mv_repair`'s own job. On the dog the 49,152 Maekawa-clean candidates **are** the parity-legal set, and 100% of survivors are refuted by non-crossing. **The objective cannot see the binding constraint** |
| **HONEST NEGATIVE 1** | **No published work on reflection-equivariant M/V assignment.** What exists is group-theoretic *kinematic* analysis of symmetric rigid origami on tessellations with crystallographic groups | **The σ-orbit parameterisation appears unpublished — it has no external validation to lean on.** Same posture as S2a: the vendored code and our own oracle are the only ground truth |
| **HONEST NEGATIVE 2** | A GF(2) linear check (the system minus transitivity is linear; exact in 0.03–1.3 ms) | Genuinely **incomparable** to the propagator — 26 candidates refuted on `two-level-tree` that it accepts, 14 the other way on star-4. A sound near-free tripwire but **not** a replacement. It is new code with a real back-substitution bug found this session, validated only by a 7/7 stock control. **Propose; do not ship as an oracle** |

---

## 8. Blast radius

* **Gating must change** — S2′'s targets pack **clean**, so the
  `meta["clean"] is False` short-circuit at `server.py:1569` / `:422` never
  reaches them. Name the new insertion point explicitly.
* **Flip sets are per-fold edge indices behind a sha256 fingerprint guard**
  (`mv_repair.py:198-206`: *"indices are per-fold and do not survive a
  recompile"*). **Targets must be recomputed at serve time, never committed as
  constants.**
* **RED pins to invert:** `test_cp_mirror_serve.py` asserts the defect on the
  S2′ subjects, including exact offender-edge sets.
* **Goldens:** `bless.py` regenerates `cases.GOLDEN_CASE_NAMES`. Every golden
  that moves has consumers a filename grep will not find — `test_mv_repair.py`
  (`glob`, `assert seen == 9`) and `test_paper_coverage.py` (`glob`,
  `assert len(golden_paths) == 9`, asserts `source == "boundary_cycle"`).

---

## 9. Sequencing — S2′ is NOT blocked on slice A

**The two slices operate on disjoint subject sets**, measured:

| S2′ subject | what slice A does |
|---|---|
| `TEMPLATE_QUADRUPED` | CONTROL is best on scale *and* bijection; predicate never fires. **Serve unchanged** |
| `TEMPLATE_BIRD` | CONTROL best; predicate never fires. **Serve unchanged** |
| `mesh-insect` | only `seeded_3` would pack and it is worse on every axis. **Serve unchanged** |

**Every S2′ subject has a bijective control, so A's predicate gate skips all of
them.** None of S2′'s numbers is invalidated.

What A *does* do is **create** work: `mesh-bird` converts **G2a → G2b**
(`is_bijection` False→True with `mv_swapped 4`), i.e. a *new* S2′ subject.
Since `cp_symmetric` is never gained by any of A's 154 arms, A can never
*retire* an S2′ subject.

⇒ **Recommended order: S2′a (close the `layer_order` gap) → S2′b and A in
parallel → re-run S2′'s search on `mesh-bird` after A lands.**

⚠ **Subject names are not stable across sources. Pin subjects by TREE, never by
name** — there are at least three distinct "star-4"s and two distinct
"quadruped"s in circulation (`mesh-quadruped` at scale 0.599702 via the stub
rung matches the frozen scorecard; a `quadruped` at 0.785931 via placement
matches nothing else).
