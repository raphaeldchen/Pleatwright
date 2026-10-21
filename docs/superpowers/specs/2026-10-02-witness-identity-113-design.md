# Witness identity on the 113-rejection arm

**Status:** design approved 2026-10-02. Predecessors:
`2026-09-27-nogood-core-design.md`, `2026-09-27-core-in-loop-design.md`,
`2026-09-28-witness-identity-design.md`.

**Goal.** Record *which* obstruction each dense `lizard` rejection names, on the
arm that produces **113** of them, and read the result against two bars that are
pre-registered here: one about the solver (reused verbatim from the predecessor),
one about the geometry (new, written below before any data exists).

**One sentence on why.** Every artifact to date stores the *size* of a rejection's
cause. The 2026-09-28 run stored identity, but only on the 3-rejection arm, where
its own README calls the result weak in exactly the terms that matter: *"three
distinct is consistent with new territory each time and equally consistent with a
loop that would begin repeating at rejection 20."* The arm with 37.7x the
observations has no identity instrument, because the record sits inside the
extraction branch.

---

## 0. Prior art (CLAUDE.md §0)

### Adopted, unchanged

**Junker, QuickXplain (AAAI 2004).** Already the extraction algorithm in
`mcp_harness/box_pleat/cores.py`. This slice adds **no code** to that module and
calls `cores.shrink` exactly as the existing control path does. Junker's call
bound `2k*log2(n/k)+2k` is used here only to **estimate cost** (§7), never to
gate anything.

**Soerensson & Biere (SAT 2009), clause minimization in MiniSat.** Already cited
by `cores.py`. Its subsumption question — does minimizing a learned clause make
it coincide with one already stored? — is the question §5.3's `core_keys`
counterfactual asks. The *question* is adapted; none of the mechanism is.

**Lang & Demaine, *Facet Ordering and Crease Assignment in Uniaxial Bases*
(Origami⁴, 2006).** Already load-bearing in CLAUDE.md §1.1. Named here because
their facet-ordering conditions are what the G3 branch's complete encoding would
encode, and because the G1 branch's "act upstream on the crease set" is a claim
about the same object.

**"MILP M/V"**, already on this project's adapt-list
(`origami-landscape-survey` in memory). The G3 branch's recommended successor.

### Found and consciously rejected

**MUS enumeration — Liffiton & Sakallah's MARCO, *Enumerating Infeasibility*
(JAR 2016); Previti & Marques-Silva.** This is the canonical machinery for "is
there one cause or many," and it is the right prior art to name. It is **rejected
for this slice** because it answers a different question: MUS enumeration finds
*all* minimal causes of **one** unsatisfiable instance, at a cost superlinear in
their number. Here there are **113 instances**, each already yielding one
irreducible core for ~87 oracle calls. Asking whether those 113 cores repeat is
strictly cheaper and is the question that forks gap 1. If **G1** fires, MARCO
becomes the natural follow-up — enumerating the full MUS set of a *single*
rejection would then say whether the localised site is the only cause or merely
the one QuickXplain's split order reaches first.

**Chao1 species-richness estimation (Chao, 1984).** `S_obs + f1^2/(2*f2)` from
the singleton and doubleton counts estimates how many classes a sample did not
see — genuinely the right tool for "how many obstructions exist, given 113
draws," and the multiplicity table in §5.4 already contains `f1` and `f2`. It is
**reported as a reference figure and is not a bar level**, because Chao1 assumes
independent sampling and these 113 rejections are outputs of one search. This
mirrors the predecessor README's treatment of its own chance baseline: *"an
expectation for independent labellings offered as a reference point, not a claim
about these three."*

### Within-project, adapted

From `2026-09-28-witness-identity/`: the reproduction-guard discipline, the
`distinct`/`repeats`/`serialise` script shape, the `--selftest`, and the
commitment to state an n-limitation whichever way the run falls. Its two
self-recorded instrument defects are fixed in the successor script (§6.3).

**Consciously rejected: editing `identity.py`.** That run's README §2 states the
instrument was not modified at any point during or after the run, which is what
makes its result byte-identically reproducible. Editing it now would retroactively
falsify a published claim. The successor is a new file.

---

## 1. What exists today

`compile_tree` already takes `debug_witness_cores` and appends, per rejection,
five fields of identity: `candidate`, `witness`, `core`, `signed`, `keys`
(`compile.py:391-399`). The parameter was built and run on 2026-09-28.

The append sits **below** this early return (`compile.py:359`):

```python
if not core_extraction:
    return _layers.piece_keys(w, fold), w
```

so it is unreachable whenever extraction is off. The predecessor spec states the
consequence deliberately: *"It stays empty when `core_extraction` is `False`,
because the core is the thing being identified and there is none."*

The two committed arms (`2026-09-27-core-in-loop/ab.json`):

| | arm A (`core_extraction=False`) | arm B (`True`) |
|---|---|---|
| rejections | **113** | 3 |
| `layers_tried` | 113 | 3 |
| `secs` | 1052.0 | 954.9 |
| clause vars min/median/max | **6 / 202 / 259** | 5 / 8 / 8 |
| `failure` | `AssignFail(kind='budget', site=500000)` | same |
| `core_rows` | absent | `[[44,8,31,5.069],[361,5,47,9.789],[65,8,43,6.847]]` |

Identity was recorded on the right-hand column only.

## 2. The problem with the obvious fix

Moving the append above the early return records `candidate`, `witness` and
`keys` on arm A, and that is **not sufficient for the geometry question**.

With extraction off, a witness's identity is the dependency **cone**, not the
cause. `cores.py`'s own docstring measures the cone over 31 rejections at a median
of **172 FOLD edges / 109 solver variables, spanning 6-245**, against an
irreducible cause of **4-8**. Two rejections sharing one underlying obstruction
can carry different cones. So "113 distinct cones" would not refute "a few
repeated obstructions"; the negative would be an artifact of the instrument.

This is the same failure shape as reading a count as an identity: a field that
looks like identity but is not the identity the question needs.

## 3. Design: diagnostic-only extraction

Separate **what the search uses** from **what the run records**, with a new
keyword-only parameter `core_record` independent of `core_extraction`:

| `core_extraction` | `core_record` | keys handed to `assign` | core recorded | |
|---|---|---|---|---|
| `False` | `False` | full cone | no | today's arm A, unchanged |
| `True` | ignored | **narrowed** | yes | today's arm B, unchanged |
| `False` | **`True`** | **full cone** | **yes** | **the new arm** |

The new arm's `keys` expression is the *same expression* arm A uses today, so the
non-interference claim is checkable by reading one line.

### 3.1 Why the search is expected to be unperturbed

`layers.propagate` builds a fresh constraint object per call —
`dataclasses.replace(graph.cons, direct=direct)` (`layers.py:146`) — and reads
`graph.slots` and `labels` without writing either.

`replace` is **shallow**, so a mutation of a nested field inside
`layer_order.propagate` is not excluded by inspection. This design therefore does
**not** rest on that argument. Non-interference is established empirically, by
§6.1's A/A test and §5.5's guard.

### 3.2 `core_extraction=True` is unaffected

When extraction is on, `core_record` is ignored and the existing behaviour is
reproduced exactly, including the **uncaught** propagation of
`cores.CoreExtractionError`.

**Amended in pre-flight review, 2026-10-02.** This section originally called for
a **separate, duplicated call site** for the diagnostic extraction, so that the
control path's code stayed byte-for-byte what it is today. That was overruled
before implementation began, for a reason internal to the design rather than a
matter of taste: §5.1's record is also shared between the two paths via one
constructor, so the control path's *code* changes regardless, and declining a
second shared helper to protect a property the design had already given up was
inconsistent.

Both paths therefore call **one** extraction helper whose single `catch`
parameter is the only difference between them — `False` on the control path,
where the exception propagates uncaught, and `True` on the diagnostic path,
where it is recorded. The claim this design makes about the control path is
therefore **behaviour-identical and pinned by tests**, not code-untouched, and
the tests that pin it are named in §6.2.

## 4. Failure handling: `CoreExtractionError` on the diagnostic path

**Control path (unchanged):** propagates uncaught out of `compile_tree`. An
unsound core reaching a clause is a soundness failure, and `cores.CoreExtractionError`
deliberately subclasses `Exception` rather than `ValueError`/`RuntimeError`/`KeyError`
so that `compile_tree`'s handlers cannot fold it into an indistinguishable
`AssignFail("error")`.

**Diagnostic path (new):** caught, recorded per-rejection in the record's
`core_error` field, counted, printed loudly, and the run continues. The reasoning,
stated because this project's reflex is "never swallow":

1. the diagnostic core reaches no clause, so no soundness property is at risk;
2. killing a ~47-minute run at rejection 50 for a diagnostic failure destroys the
   measurement it was paying for;
3. the fact cannot hide, because §5.5's invalidity condition 4 **gates the verdict
   on the count** — a partial population is named explicitly, and below 90 the
   geometry bar refuses a verdict outright.

Recorded-and-gated is not swallowing. Swallowing is wrong when it hides a fact
that changes a conclusion.

**Constraint.** The catch is `except cores.CoreExtractionError` only. The existing
`except (ValueError, RuntimeError, KeyError)` at `compile.py:236` and `:414` is
**not widened**.

## 5. The measurement

One run, one subject (`lizard`), one arm: `dense=True`, `core_extraction=False`,
`core_record=True`, `assign_budget=500_000` — arm A's configuration plus the
record.

### 5.1 Record fields

Per rejection, appended to `debug_witness_cores`:

| field | value | available without extraction |
|---|---|---|
| `candidate` | `frozenset(labels.items())` | yes |
| `witness` | the `layers.Witness` (`kind`, `creases`, `faces`, `prov`) | yes |
| `keys` | `piece_keys(w, fold)` — **the cone keys `assign` actually received** | yes |
| `core` | `cores.shrink(...)`, diagnostic only | via `core_record` |
| `signed` | `frozenset((c, labels[c]) for c in core)` | via `core_record` |
| `core_keys` | `piece_keys(replace(w, creases=core), fold)` — see §5.3 | via `core_record` |
| `core_error` | the `CoreExtractionError` message, or `None` | — |

`keys` means a **different thing** in the two arms — cone-derived here, narrowed
in arm B — and that is why both it and `core_keys` are recorded. Any cross-arm
comparison at the key level must compare `core_keys` against arm B's `keys`.

### 5.2 Bar 1 — the solver bar, reused verbatim

The 2026-09-28 spec §6.3 rows, unaltered, evaluated in order, first match wins:

| row | trigger | meaning |
|---|---|---|
| 1 ENFORCEMENT DEFECT | a `candidate` repeat | the loop checked a labelling it had already refuted |
| 2 LATE ENFORCEMENT | a `signed` repeat | a no-good re-derived from a different subtree — what `hits_nogood`'s full-binding-only pruning predicts |
| 3 GRANULARITY CEILING | a `keys` repeat | two crease-level no-goods collapsing onto one clause input |
| 4 NEW TERRITORY | no repeat at rows 1-3 | each rejection was new information |

**Not rewritten, and that is the point.** The 2026-09-28 outcome is now known; a
bar re-chosen with that knowledge is not a bar. The only change is the
population: **3 -> 113**. Row 2 becomes testable on a real population for the
first time, because `core_record` supplies `signed` without narrowing the control
path.

The predecessor's asymmetry argument carries over and now cuts the other way: a
repeat is decisive at n=1, so 113 observations make the *absence* of one
meaningfully stronger than it was at 3 — while still not a proof.

### 5.3 The `core_keys` counterfactual

The A/B's central ambiguity is that 113 -> 3 admits two opposite readings: either
narrower clauses exclude more of the space a priori, or the search spends its
budget re-deriving forbidden ground. `core_keys` is the clause input **arm B would
have built**, computed on all 113 of arm A's rejections for one extra
`piece_keys` call.

If `core_keys` repeats where `keys` does not, then narrowing **collapses distinct
rejections onto identical clause inputs** — direct evidence for the second
reading, on a 113-sample.

**Limit, stated in the report whichever way it falls:** this is arm A's trajectory
under counterfactual narrowing, not arm B's actual trajectory. It can show that
narrowing *can* collapse; it cannot show arm B's 3 rejections *were* collapsed.
`core_keys` carries **no bar row** for this reason.

### 5.4 Bar 2 — the geometry bar (new; pre-registered here)

Evaluated in order, first match wins:

| row | trigger | what it makes the next slice |
|---|---|---|
| **G1 LOCALISED** | distinct `faces` <= 10 **and** distinct `core` <= 20 | the contradiction lives at a handful of enumerable sites -> act **upstream** on the crease set / interleaving / elevation field; publish the sites with coordinates |
| **G2 BOUNDED** | distinct `core` <= 40 | a bounded pool of causes; upstream action plausible but not pinpointed -> spatial follow-up |
| **G3 DIFFUSE** | distinct `core` > 40 | obstructions do not repeat at a rate this instrument can exploit -> stop improving the search; settle **existence** with a complete method (SAT/ILP over the layer-ordering constraints) |

**All three counts are over the SAME population: the rejections whose
extraction produced a core.** `faces` and `kind` live on the witness and are
never absent, so a refused extraction would otherwise contribute a face triple
to the site count while contributing no cause to the core count — making G1's
two conditions measurements of two different populations. A rejection with no
identified cause is a member of neither. The two coincide when N = 113, which
is exactly why a mismatch would surface only in the degraded case, where it does
the most damage: found while executing the bar against its own fixtures, where
it turned a genuine G1 into a G2.

**The G1/G2 boundary, made explicit.** Rows are evaluated in order and the first
match wins, so `core` <= 20 with `faces` > 10 selects **G2**, not G1: the causes
are few but they are not localised to few sites, which is the reading that
warrants a spatial follow-up rather than immediate upstream action. The converse
(`faces` <= 10 with `core` > 40) selects **G3**, because `faces` cannot carry a
row alone and a large core population is what G3 names.

**Threshold justification, all of it known before the run.**

* **10 on `faces`.** 31 of 31 measured rejections are `taco_tortilla` among
  exactly **3** faces (`2026-09-27-nogood-core/core-sizes.json`), against **745**
  creases in lizard's dense candidate (`2026-09-28-witness-identity/README.md`
  §3). 10 is the point where "enumerate the sites and look at them in one
  sitting" stops being possible. This is a **decision-relevance** threshold, not
  a statistical one.
* **20 and 40 on `core`.** Cores are 4-8 elements, max 8 observed, on 31 of 31.
  40 is ~35% of 113, where mean multiplicity crosses ~2.8: below it the average
  cause recurs, above it most causes are singletons. "Does the average
  obstruction recur?" is the decision boundary.

**`kind` is reported but is not a bar level.** All 31 measured rejections were
`taco_tortilla`, so distinct `kind` is very likely 1 — worth publishing as a
finding (the mechanism is singular) and useless as a discriminator. A bar row
that is guaranteed to fire measures nothing.

**`faces` cannot fire a row alone.** `layers.py:52` annotates it `# face indices
the provenance names; diagnostic only`. G1 requires `core` to agree, so `faces`
can only strengthen a row `core` already supports.

**The table published whichever row fires.** The row is the headline; this is the
deliverable, because a threshold can be wrong while the table is still decisive:

* multiplicity distribution per level — how many obstructions occur x1, x2, x3, ...
* `f1` (singletons), `f2` (doubletons), and the Chao1 reference figure of §0,
  with its independence caveat attached on every appearance
* top-5 coverage — the share of 113 held by the five most frequent `core`s and `faces`
* the full repeat map, printed entire, at every level
* pairwise overlap, as the predecessor's §3 did: distinct is not disjoint, and a
  `core` sharing 4 of 8 elements with another is a fact a reader will find
  unaided

### 5.5 Pre-registered invalidity — no verdict from either bar if any holds

1. **Guard fails:** rejections != 113, or `layers_tried` != 113, or clause sizes'
   min/median/max != **6/202/259**, or `failure` !=
   `AssignFail(kind='budget', site=500000)`.
2. `len(records)` != 113.
3. Any record missing `candidate`, `witness` or `keys`.
4. **Cores obtained < 113:** the geometry bar names its population explicitly
   ("of N, not of 113") and is labelled **PARTIAL**; below N = 90 it refuses a
   verdict outright.

   **This also binds the solver bar, asymmetrically across its rows.** Rows 1 and
   3 read `candidate` and `keys`, which are present on all 113 regardless, so
   they are unaffected. **Row 2 reads `signed`, which exists only where a core
   does** — so with N < 113 row 2 is evaluated over N and must be reported as
   "no `signed` repeat in N of 113", never as a statement about 113. A **row 4
   NEW TERRITORY** verdict reached under N < 113 is therefore itself **PARTIAL**,
   because row 4 is the absence of a repeat and one of its three triggers was
   tested on a smaller population than the other two.

   **Row 2 is still evaluated at any N, and still fires on a repeat.** A repeat
   is decisive at n=1 — that is the predecessor's own asymmetry argument — so
   suppressing a *detected* `signed` repeat because its population is small would
   discard the strongest observation this instrument can make. What N < 90 forbids
   is the **absence** of a row-2 repeat supporting row 4. So: row 2 fires at any
   N, with its population named alongside it; row 4 requires N >= 90.

   Without this clause a partial core population would silently weaken row 4
   while it continued to print as a full verdict — the predecessor's row 4 already
   over-claimed once, and a shrunken population is a second way for the same row
   to say more than it measured.
5. §6.1's A/A pre-flight did not pass.

Any of these reports **NO VERDICT** and why — never "mostly reproduced."

Condition 4's shape is the direct lesson of the clause-propagation slice, whose
gate would have published "PROPAGATION REFUTED" from a silent instrument because
its `derived()` read every counter with `.get(..., 0)`. Defaults are how a
missing measurement becomes a conclusion. The population is **required and
named**, never defaulted.

### 5.6 Guard strength, stated honestly

Arm B's guard compared three exact per-rejection triples **in order**. Arm A
published no `core_rows`, so this guard can compare only a **count** and a
**min/median/max**. That is weaker, and it is the strongest guard the committed
baseline affords.

The run therefore **publishes the full 113-value clause-size population** so that
a future replay can guard it exactly. Fixing the guard forward is part of the
deliverable.

## 6. Testing

### 6.1 The A/A non-interference test — the decisive one

Arm A at `assign_budget=20_000`, twice: `core_record=False`, then `True`.
Assert **identical** rejection count and **identical full clause-size
population**.

The entire design rests on "diagnostic extraction does not change the search,"
which is a claim about shallow-copy aliasing that cannot be settled by reading
code. At 20,000 nodes this costs minutes; if aliasing leaks, it fails here
instead of invalidating a ~47-minute run.

This is the inverse of the clause slice's near-miss, where a gate would have
passed on a *silent* instrument. This gate's job is to catch a **noisy** one — an
instrument that perturbs what it measures.

### 6.2 Behavioural tests

* diagnostic path populates `core`, `signed`, `core_keys`; `keys` equals the cone keys
* `core_record=False` leaves the list empty and behaviour unchanged
* `core_extraction=True` preserves the **uncaught** raise, under a monkeypatched
  `cores.shrink`
* diagnostic path records a monkeypatched raise in `core_error`, increments the
  count, and continues
* every bar row, both bars, including precedence
* all five invalidity conditions, each producing NO VERDICT

### 6.3 Pre-registered mutations, each required to go red

The clause slice shipped a headline whose own mutant survived 52 tests, and a
vacuous fixture is how that happened.

* each threshold moved wide: 10, 20, 40, 90
* `and` -> `or` in G1
* `distinct` computed over a different population than the one reported
* the guard's `113` -> any value
* condition 4's `< 113` -> `<= 113`

Every bar fixture must make the **wrong** row reachable — a G3 fixture needs more
than 40 genuinely distinct cores, or the threshold is untested.

### 6.4 Instrument defects inherited and fixed

The predecessor README records two against itself, both fixed in the successor
script: a per-rejection node figure **hard-coded** in an f-string rather than
interpolated (it would have printed 166,667 for a 4-rejection run), and two
clause-size constants that nothing asserts agree. The successor interpolates
every figure it prints and asserts its constants against each other in
`--selftest`.

## 7. Cost

| component | figure | source |
|---|---|---|
| arm A baseline | 1052.0 s | `ab.json` `arms[0].secs` |
| per-oracle-call cost | ~0.18 s | *derived* from arm B's 5.069/31, 9.789/47, 6.847/43 |
| calls per rejection | ~87 | Junker's bound at k=8, n=172 |
| extraction, 113 rejections | ~1770 s | *derived*, 113 x 87 x 0.18 |
| **total** | **~47 min** | |

An **estimate, not a measurement**: it combines arm B's per-call cost with the
31-row cone-size distribution, two different populations. Wall clock has drifted
0.82x-1.26x across replays of unchanged code, so the honest band is ~35-70 min.
Nothing is guarded on time.

## 8. Limits

**One subject.** `lizard`, as in every predecessor, for the same measured reason:
26 of the 31 core rows were lizard, and the subjects that would test generality
either cannot produce a dense labelling at all or arrive with two blamed creases
and nothing to shrink. Lizard's `propagate` is ~100x slower than the other five
subjects' (1.070 s against 0.004-0.014 s, `2026-09-24-dense-pleats/`); it is the
subject here because its dense loop yields rejections cheaply, not by preference.

**One arm, one budget.** Nothing here licenses a statement about dense `assign`
in general.

**The geometry bar is asymmetric, and the asymmetry runs opposite to the
predecessor's.** `layer_order._propagate` is **not confluent**, so a witness cone
is *a* derivation of the contradiction, not *the* cause: a different propagation
order can blame different creases for the same underlying geometric conflict.
Therefore:

* **G1 LOCALISED is robust.** If the same minimal core recurs, it recurs;
  non-confluence cannot manufacture a coincidence.
* **G3 DIFFUSE is soft.** Distinctness may be **derivational** rather than
  geometric. 113 distinct cores are consistent with one obstruction reached 113
  different ways.

So a G3 does **not** license "the geometry is fine, go build a SAT encoding." It
licenses "repeats are not exploitable *through this instrument*." This appears in
the G3 verdict row itself, not in a footnote — otherwise the weakest verdict
reads as the strongest conclusion, which is how the predecessor's row 4 came to
assert something about nodes it never observed.

**What no verdict here can say.** `assign`'s no-good is a `{variable: value}` map
built in `assign`'s own locals; `_check` sees neither `var_of` nor `value`. `keys`
is the clause's **input**, not the clause. A `keys` repeat is suggestive and a
`signed` repeat strong; neither is proof of a duplicated clause. Proving one would
need a `debug_clauses` list in `assign.py`, which stays out of scope.

## 9. Files

| file | change |
|---|---|
| `mcp_harness/box_pleat/compile.py` | `core_record` parameter; record append moved above the `core_extraction` early return; separate guarded diagnostic call site; `core_keys` and `core_error` fields |
| `mcp_harness/box_pleat/cores.py` | **none** — no code added to a soundness-critical path |
| `docs/superpowers/evidence/2026-09-28-witness-identity/identity.py` | **none** — see §0 |
| `docs/superpowers/evidence/2026-10-02-witness-identity-113/identity113.py` | new: guard, both bars, multiplicity and overlap tables, Chao1 reference, serialiser, `--selftest` |
| `mcp_harness/tests/test_box_pleat_witness_record.py` | new: §6.1-6.3 |

## 10. Out of scope

* `debug_clauses` in `assign.py` (§8).
* MUS enumeration per rejection — gated on **G1** firing (§0).
* Any second subject or second budget (§8).
* Any change to `cores.py`, to `identity.py`, or to the predecessor's bar (§5.2).
* Acting on whichever branch the geometry bar selects. This slice measures; the
  upstream fix and the complete encoding are each their own spec.
