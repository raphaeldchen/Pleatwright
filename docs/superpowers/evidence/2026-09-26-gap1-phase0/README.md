# Gap 1 Phase 0: a variable census, and F.1.1 step 3 measured as a classifier

Script: `phase0.py` · Artifact: `phase0.json` · Measured 2026-09-26

---

⚠ **WITHDRAWN 2026-09-27 — this file's headline conclusion is refuted. The
retention ARITHMETIC below stands; the CONCLUSION drawn from it does not.**

This file was titled *"the dense crease SET is the leading suspect, not the
search"* until 2026-09-27. The title was changed, rather than annotated in place
like every claim below it, because a title is the part a cross-reference quotes
and a grep surfaces — a label, not a record. The reasoning that produced it is
preserved intact in §2 and §4 beneath their own correction blocks.

Every retention figure in §2 was measured at **unit-piece** granularity, and at
that granularity it reproduces exactly (`phase0.json`: `lizard` 432 of 4,488 =
9.63%, `guinea_pig` 901 of 16,174 = 5.57%). But **a unit piece is not COrigami's
unit of selection.** The paper's step 2 splits the grid into candidate *segments*
at every intersection with hinges and ridges, so step 3 selects segments —
collinear runs of unit pieces. Measured at that unit,
`../2026-09-27-pleat-filter/README.md` reports the filter retaining **100%** of
`lizard`'s 4,488 dense candidates (365 collinear runs, 365 retained): a **no-op**,
not a 90% cut.

Below segment granularity the filter is not merely wrong but **destructive**.
Keeping one of two collinear pieces at a vertex leaves that vertex with crease
degree 1, and Maekawa's `|M − V| = 2` cannot hold at odd degree. The same source
reports **408 of 454** fully-bound interior vertices coming out odd, and
`assign(dense=True, filter_pleats=True)` failing as
`AssignFail(kind='maekawa_fixed', site=(1, 21))` before the search starts.

**So three claims below are withdrawn:** "the filter would reject about 90% of
what dense mode currently creases" (§2), "dense mode … is increasingly too dense"
(§2), and "that makes the crease set the leading suspect and Phase A (the filter)
the best-supported next build" (§4). Phase A was implemented to Task 3 and then
**HALTED 2026-09-27**; see `../2026-09-27-pleat-filter/README.md` and
`../../specs/2026-09-27-pleat-filter-design.md`.

**The class of the error, named because it is a repeat.** This is a wrong-unit
error — piece versus segment — of the same class as the crease-versus-variable
unit error in the dense-pleats wave, and it again ran in the direction that
favoured the hypothesis being tested. Nothing below has been erased: the original
text is left visible so a reader can see what was believed and why it changed.

---

**The question.** No dense candidate has ever certified. Two candidate root
causes: the crease **set** is over-constrained, or the **search** cannot find a
labelling for a sound set. Phase 0 measures both cheaply before anything is
built.

## 1. What was missing, and why nobody noticed

COrigami's construction is four pieces and is **mostly deterministic**:

| COrigami | ours |
|---|---|
| F.1.1 steps 1-2: dense orthogonal grid | `contours.py` elevation field ✅ |
| **F.1.1 steps 3-4: SELECTION FILTER** | ❌ **nothing** |
| F.2: pleats get deterministic M/V | ✅ `interleave.py` |
| **F.3: ridges get deterministic M/V** | ❌ searched |
| search: **hinges only** | searched: ridges + hinges + released pleats + centre column |

The paper is explicit (quoted in `2026-09-24-dense-pleats-design.md` section 3):
*"step 1 and step 2a are essentially deterministic and do not involve decision
making. Step 2b … is therefore combinatorial in the number of hinges."*

**The reasoning error.** That spec's section 3 rejected "F.1.1 steps 1-4" as a
BUNDLE, on the true grounds that `contours.py` already supplies the elevation
field steps 1-2 would build. But **steps 3-4 are not about elevations -- they
are a selection filter**, and nothing replaced them. The spec recorded the cost
of the rejection as too LITTLE coverage ("54.7% of the half-grid", a statement
about steps 1-2) and never considered that dropping the filter leaves too MANY
creases. `pleat_paths`' own docstring states the consequence plainly:
`dense=True` *"removes that label filter -- every `axial`/`elev` piece is a
candidate."*

⚠ **The 54.7% figure quoted in this paragraph is itself WITHDRAWN as of
2026-09-28 — unreproducible, with no committed script computing it.** Measured:
≈49%, and `starfish` is 48.2% rather than the 94.4% that made it look like a
high-coverage control. See `../../specs/2026-09-24-dense-pleats-design.md` §2 and
`../2026-09-28-pleat-grid-headroom/`. This does not affect anything this file
concludes; the number is simply not one to quote forward. `phase0.py`'s own
docstring repeats it and is deliberately left unedited — it is a script whose run
is on record.

## 2. Part B: how much would F.1.1 step 3 retain?

⚠ **The percentages in this section are correct at UNIT-PIECE granularity and
withdrawn as a conclusion — see the WITHDRAWN block at the top of this file.** At
the segment granularity COrigami actually selects on, the filter retains **100%**
(`../2026-09-27-pleat-filter/README.md`), so neither "rejects about 90%" nor
"increasingly too dense" survives. Text unchanged below.

`v3` is step 3 as written (perpendicular to an intersecting hinge, **or**
through an X-shape vertex); `v4` adds step 4's border reintroduction.

| subject | N | dense candidates | **v3 retained** | **%** | v4 | X-shape vertices |
|---|---|---|---|---|---|---|
| `starfish` | 4 | 54 | 28 | 51.9% | 36 | 1 |
| `lizard` | 34 | 4,488 | 432 | **9.6%** | 432 | 0 |
| `frog` | 38 | 5,638 | 545 | **9.7%** | 549 | 0 |
| `horse` | 46 | 8,330 | 864 | **10.4%** | 872 | 0 |
| `bird` | 54 | 11,534 | 841 | **7.3%** | 843 | 1 |
| `guinea_pig` | 64 | 16,174 | 901 | **5.6%** | 905 | 0 |

**The filter would reject about 90% of what dense mode currently creases**, on
every subject but the 54-candidate toy.

**And the retained count is nearly FLAT in absolute terms** -- 432, 545, 864,
841, 901 -- while candidates grow 4,488 to 16,174. That is the structural
point: dense candidates grow with the **grid area** (O(N²)), while a filter
keyed on hinges grows with the **tree's structure**. So the over-creasing gets
monotonically worse with size: 9.6% retained on `lizard`, 5.6% on
`guinea_pig`. Dense mode is not uniformly 10x too dense; it is increasingly too
dense.

### 2.1 Two clauses of the predicate are inert -- read before building Phase A

⚠ **The F.3 doubt this section raised is REFUTED — see
`../2026-09-27-f3-anchors/`.** It rested on an anchor COUNT (2 Y-shapes vs 88
ridge variables); what governs propagation is anchor REACHABILITY, and the ridge
graph turns out to have only 1-2 components, so reach is 100% on five of eight
subjects and >=71.7% on the rest. The observation below about X-shapes stands;
the inference from it about F.3 does not.

* **`x_shape_vertices` is 0 on four of six subjects and 1 on the other two.** The
  "four intersecting ridges" clause is **effectively dead in our geometry** --
  which is why `v3` equals `v1` almost everywhere. Either our ridges never cross
  (plausible: they emanate from the skeleton) or this reading of "X-shape" is
  wrong. **Phase A must resolve which before relying on that clause.**
* **`v1` == `v2` on all six subjects** (27/27, 432/432, 545/545, 864/864,
  837/837, 901/901), so the *perpendicularity* test never discriminates: every
  candidate touching a hinge is already perpendicular to it. The effective
  predicate measured here is just "touches a hinge".

  ⚠ **Added 2026-09-27: that is a COUNT equality, not a set identity.**
  `phase0.json` stores only `retained` counts, never the sets. The inference to
  equal *sets* is sound here only because `v1` is a **subset** of `v2` by
  construction in `phase0.py`: both call the same `touches_hinge(i, ...)`, and
  its `not require_perp or ...` guard makes `require_perp=False` strictly weaker,
  so every member of `v1` is a member of `v2` and equal cardinality forces
  equality. Stated explicitly because this branch has already been burned once by
  an equality test that was not an identity (a 40-character truncated `repr` used
  as an object identity).

These are recorded prominently because this project has already burned three
definitions of `interleave.adjacency`, one of which passed every hand-built unit
test while producing an **empty** graph on real data -- a vacuous pass that
looked like success. Enumerating the readings up front and reporting the inert
ones is that lesson applied before a design depends on it, not after.

## 3. Part A: the variable census -- the number that sizes F.3

Read from production's own `var_of` (in-memory patch, diff verified). **Pieces
are not variables**: run-merging, pleat-path grouping and mirror-merging
collapse thousands of creases onto hundreds of variables, so a census over
piece roles would use the wrong denominator.

| subject | total variables | **axial** | elev | hinge | ridge | **ridge share** | elev share |
|---|---|---|---|---|---|---|---|
| `starfish` | 49 | **5** | 16 | 10 | 18 | 36.7% | 32.7% |
| `lizard` | 429 | 0 | 229 | 112 | 88 | 20.5% | **53.4%** |
| `frog` | 541 | 0 | 273 | 154 | 114 | 21.1% | **50.5%** |
| `horse` | 878 | **102** | 374 | 220 | 182 | 20.7% | **42.6%** |
| `bird` | 1,024 | **92** | 466 | 228 | 238 | 23.2% | **45.5%** |
| `guinea_pig` | 929 | 0 | 477 | 248 | 204 | 22.0% | **51.3%** |

The **`axial` column was added 2026-09-27** (it is in `phase0.json` all along, as
`variables_by_role["axial"]`). Without it three rows do not add up — `starfish`
16+10+18 = 44 of 49, `horse` 374+220+182 = 776 of 878, `bird` 466+228+238 = 932 of
1,024 — and the earlier table showed no such column and no note. A `0` here means
the key is absent from that subject's `variables_by_role`; with the column, all
four roles sum to the stated total on all six rows.

* **F.3 would remove ~20-23% of all variables** -- stable across the corpus.
  Meaningful for a DFS (2^88 fewer combinations on `lizard` in the worst case)
  but not the dominant block.
* **`elev` variables are the largest block at 43-53%**, and they are exactly
  what the missing filter would cut.
* Together the two missing COrigami pieces target **63-74% of the CSP's
  variables** (`elev` + `ridge` over `total_variables`, per subject: `horse`
  63.3%, `bird` 68.8%, `starfish` 69.4%, `frog` 71.5%, `guinea_pig` 73.3%,
  `lizard` 73.9%). *Corrected 2026-09-27: this read "~65-75%", which excluded
  `horse`'s 63.3% at the bottom of the band.*

## 4. What this does and does not establish

⚠ **The "Establishes" paragraph below is WITHDRAWN 2026-09-27 — see the block at
the top of this file.** The "10-18x more pieces than F.1.1 step 3 would retain"
ratio is a unit-piece ratio; at COrigami's own unit (a segment) the ratio is
**1x** and the filter is a no-op, so the crease set is **not** the leading
suspect and Phase A was HALTED rather than completed
(`../2026-09-27-pleat-filter/README.md`). The variable-census half of the
sentence (the filter and F.3 between them governing ~63-74% of CSP variables)
still holds as arithmetic; what it supported does not. Text unchanged below.

**Establishes:** dense mode creases 10-18x more `axial`/`elev` pieces than
COrigami's own F.1.1 step 3 would retain, the excess grows with subject size,
and the two missing pieces of the paper's construction (the filter and F.3)
between them govern ~70% of the CSP's variables. That makes **the crease set the
leading suspect** and Phase A (the filter) the best-supported next build.

**Does NOT establish that filtering makes anything fold.** No filtered pattern
has been built or certified. The retained counts are a classifier's output, not
a folded result, and section 2.1's two inert clauses mean the predicate itself
is not yet settled. Anyone citing this file for "the filter fixes gap 1" is
citing it wrongly.

## 5. Regenerate

```bash
# from mcp_harness
PYTHONPATH=. ../.venv/bin/python3 -u \
    ../docs/superpowers/evidence/2026-09-26-gap1-phase0/phase0.py \
    ../docs/superpowers/evidence/2026-09-26-gap1-phase0/phase0.json
```
