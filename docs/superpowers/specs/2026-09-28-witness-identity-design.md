# Is the dense CEGAR loop exploring new territory, or rediscovering forbidden ground?

**Status:** design, not yet planned.
**Predecessor:** `2026-09-27-core-in-loop-design.md`, whose §7.2 row 3
(UNRESOLVED AT THIS BUDGET) this experiment follows up.
**Subject:** `lizard`, dense, `assign_budget=500_000`, `core_extraction=True`
— a replay of that spec's arm B with instrumentation added and nothing else
changed.

## 1. Why now

The core-in-loop A/B settled two things and left one open.

Settled: **the clause narrows, hard.** Arm B's median no-good fell from 202
solver variables to 8 (25.2x), and its cone-to-core narrowing ran 65 blamed
creases to 8. Settled: **extraction is not the cost.** 21.7 s of arm B's
954.9 s, 2.27%, which closed the Fleury & Biere bounded-shrinking follow-on
before it was opened.

Open: **the terminal outcome did not move.** Both arms ended
`AssignFail(kind='budget', site=500000)`. What changed was the rejection
count, 113 -> 3, and that single figure admits two opposite readings:

* **Pruning works.** Stronger clauses exclude more of the space a priori, so
  fewer distinct complete candidates survive to be checked. The 166,667 nodes
  between rejections are the local CSP grinding through a legitimately
  narrowed space, and the next lever is the local CSP — which was
  independently profiled at **79.57%** of dense `assign`'s time.
* **The search wandered.** Three rejections out of 500,000 nodes is also what
  a loop looks like when it spends its budget re-deriving ground it has
  already forbidden, or descending branches a stored clause should have cut
  earlier.

Nothing in the A/B's instruments separates these. Both are consistent with
every number it recorded. Rejection counts, clause sizes and wall clock are
all **aggregate** measurements, and the distinction is about **identity**:
were those three rejections three different facts, or one fact three times?

That question is answerable for the price of one 16-minute replay, and its
answer decides where the next slice goes. If the loop is exploring, the
clause lever is finished and the local CSP is next. If it is re-deriving, the
clause lever is not finished at all — it is being enforced too late — and the
local CSP would be the wrong thing to optimise.

## 2. Prior art (CLAUDE.md §0)

**Adapted — CEGAR's progress guarantee.** Clarke, Grumberg, Jha, Lu & Veith,
*Counterexample-guided abstraction refinement for symbolic model checking*
(CAV 2000; JACM 50(5):752-794, 2003). CEGAR terminates because each
refinement **strictly eliminates the spurious counterexample that produced
it**, so the abstract state space shrinks monotonically and no counterexample
can recur. That is precisely the property this experiment measures, and our
loop is a CEGAR loop by construction (`assign` proposes, `_check` refutes,
the witness refines). The adaptation is direct: *a refinement step that does
not eliminate its own counterexample is a loop that cannot terminate.* We
have never checked that our steps do.

**Adapted — nogood recording from restarts.** Lecoutre, Saïs, Tabary &
Vidal, *Nogood Recording from Restarts* (IJCAI 2007, pp. 131-136). Its stated
purpose is "to avoid the same situations from one run to the next" —
recording nogoods so that search does not revisit regions already explored.
The paper's framing is the one we borrow: the value of a recorded nogood is
measured by *what it stops the search from redoing*, not by its size. Our A/B
measured size (202 -> 8) and never measured redoing. This experiment supplies
the missing half.

**Consciously NOT adapted — the 1UIP asserting-clause guarantee.** In CDCL,
the standard argument that a learned clause cannot be re-learned rests on the
clause being **asserting**: derived at the first unique implication point, it
is unit under the trail after non-chronological backjumping, so it
immediately flips a literal and the same conflict cannot recur. **That
guarantee does not transfer to `assign`.** Our loop does `nogoods.append(
clause)` followed by `retry()` (`assign.py:1049-1051`), and `retry()` tests
stored clauses through `hits_nogood()` (`:967-969`), which is
`all(value.get(var) == val ...)`. An unbound variable reads `None`, which
never equals `"M"` or `"V"`, so **a stored clause prunes only at the moment
its last variable becomes bound.** It is a sound filter and a late one: it
blocks the exact offending assignment and cuts nothing on the way down. We
therefore hold no theoretical guarantee of non-recurrence and must measure
it. This rejection is the reason the experiment exists rather than being
answered from the literature.

**Already closed here, not re-derived.** Sörensson & Biere, *Minimizing
Learned Clauses* (SAT 2009) and Junker's QuickXplain (AAAI 2004) were the
core-in-loop spec's prior art and are not revisited; this spec adds no
extraction mechanism.

## 3. Three corrections to the approved design

§3.1 and §3.2 were found while reading `assign.py` to write this spec — before
any data — and are recorded here rather than applied silently, on the same
grounds as the core-in-loop spec's arithmetically incoherent bar. **§3.3 was
found after the experiment ran**, and says so in its own first line, because
correcting a pre-registered document after seeing its data is a weaker position
than correcting it before and the reader is owed that distinction.

### 3.1 A repeated core is NOT by itself a defect

The approved design said: record the `Witness` and the core; *any core
repeated is a defect signal about clause enforcement*. That is wrong, for two
independent reasons.

1. **The no-good is not a set of creases. It is a `{variable: value}` map.**
   `assign` builds it as `{var_of[idx[k]]: value[var_of[idx[k]]] for k in
   keys}` (`assign.py:1025-1027`). The same core under a different label
   pattern is a **different clause**, legitimately learned, forbidding
   genuinely new territory. Core identity alone cannot distinguish the two.
2. **Even a repeated core under identical labels is the expected signature of
   a late filter**, not proof of a bug. Because `hits_nogood()` prunes only
   on full binding (§2), the same no-good can be re-derived from a different
   subtree without any enforcement error. That is a real and actionable
   finding — it points at clause *propagation* — but it is a design
   limitation, not a defect.

**The correction:** identity is measured at five levels, not one, and only
the first carries a decisive defect verdict. See §5.

### 3.2 The parameter carries a record, not a 2-tuple

The approved design said `debug_witness_cores` appends `(witness, core)`. The
chain from candidate to clause has five distinguishable links, each answering
a different question, and all five are already in `_check`'s local scope at
zero cost. Collapsing them to two throws away the readings that decide §5's
rows. The parameter therefore appends a **dict per rejection** rather than a
tuple — `debug_cores`' tuple convention does not scale to five heterogeneous
fields, and this is a diagnostics-only channel where a named field is worth
more than convention.

### 3.3 Correction made AFTER the data (2026-09-28)

**Status, stated first because it decides how to read this:** §3.1 and §3.2
above were found before the experiment ran. This one was found by the
experiment's own final review, **after** the data landed. That is a weaker
position to correct from, so the scope of what may change is narrow and is
fixed here explicitly.

**What does NOT change: the bar.** Row 4 was the row the data selected, and it
stays that. No threshold moves, no level is added to or removed from
`VERDICT_LEVELS`, and the guard is untouched. The predecessor spec's ruling
holds — a bar chosen after seeing the number is not a bar — and this correction
would be illegitimate if it touched one.

**What was wrong: two inferences attached to the bar, both unsound a priori.**

1. **Row 4's second sentence asserted something no instrument here measures.**
   It read "the 166,667 nodes between rejections are the local CSP working
   through a legitimately narrowed space". This experiment records the
   **identity of the three rejections** and nothing whatever about the nodes
   between them. §1 gave the "search wandered" reading **two** mechanisms —
   re-deriving forbidden ground, *or* descending branches a stored clause
   should have cut earlier — and only the first produces a repeat at any of the
   five levels. So row 4 removes one of two mechanisms, not the reading.

2. **§10 gated the descent follow-on on a signal that cannot detect it.** It
   made "clause propagation during descent" conditional on **row 2**, whose
   trigger is a `signed` repeat. Descent-time waste produces **no repeat at
   all** — a loop that wastefully descends subtrees a stored clause should have
   cut can still emit three perfectly distinct complete candidates. The gate
   could therefore never open, whether or not the mechanism is real.

**Why this is a correction and not a post-hoc rescue.** Both errors are
derivable from this document alone, with no data: §2 already established that
`hits_nogood()` prunes only when a clause's last variable becomes bound and
"cuts nothing on the way down" — that *is* mechanism 2 — and §2 is the section
that justifies the experiment's existence. The spec identified the mechanism,
then row 4 and §10 assumed it away. Declining to fix that because the data has
now landed would leave this document asserting something that was never true,
which is a worse failure than correcting it late.

**What replaces them** is marked inline at §6.3 row 4 and at §10, with the
original wording struck rather than deleted so the record of what was
pre-registered survives. The measured outcome and its argument are in
`docs/superpowers/evidence/2026-09-28-witness-identity/README.md` §4.

## 4. Interfaces

### `compile_tree` (modified signature)

```python
def compile_tree(nodes, pairs, *, max_N=None, pack_budget=200_000,
                 assign_budget=500_000, layer_budget=200,
                 certify_budget=layer_certify.CERTIFY_BUDGET,
                 dense: bool = False,
                 core_extraction: bool = False,
                 debug_cores: list | None = None,
                 debug_clause_sizes: list | None = None,
                 debug_witness_cores: list | None = None) -> Result:
```

One new keyword-only parameter, defaulting to `None`. Every existing caller
is unchanged, and with it `None` the function is byte-for-byte what it is
today.

`debug_witness_cores`, when a list, receives one dict per **rejection that
reached extraction** — i.e. one per `core_extraction=True` rejection, the
same population `debug_cores` records. It stays empty when
`core_extraction` is `False`, because the core is the thing being
identified and there is none.

```python
{
  "candidate": frozenset,   # labels.items() -- the COMPLETE candidate labelling
  "witness":   layers.Witness,   # the frozen contradiction object
  "core":      frozenset,   # crease keys, cores.shrink's result
  "signed":    frozenset,   # (crease, label) pairs over the core
  "keys":      frozenset,   # piece keys handed to assign; its clause input
}
```

### The `_check` change

Inside the existing `core_extraction` branch of `compile.py`'s `_check`,
after `core` is computed and alongside the existing `debug_cores` append:

```python
        keys = _layers.piece_keys(replace(w, creases=core), fold)
        if debug_witness_cores is not None:
            debug_witness_cores.append({
                "candidate": frozenset(labels.items()),
                "witness": w,
                "core": core,
                # `labels[c]` cannot KeyError: a core is a subset of
                # `w.creases`, which `layers.propagate` fills from
                # `exc.deps` -- the SEEDED slot edges -- and `_seeded`
                # seeds only keys present in `labels`.
                "signed": frozenset((c, labels[c]) for c in core),
                "keys": keys,
            })
        return keys, w
```

`keys` is lifted into a local so the recorded object is **the same frozenset
the loop actually uses**, not a recomputation that could diverge. This is the
only structural change: the existing `return` becomes `return keys, w`.

The ~20-line comment block that currently sits between `debug_cores.append`
and that `return` — on why the witness stays unshrunk, and on the empty-clause
outcomes a narrowed core can produce — **must be preserved verbatim**. It
documents the `layer_unfixable`/`layer_bad_witness` reasoning that no other
file records, and the new append goes after it rather than in place of it.
No new imports: `replace` and `time` are already imported in `compile.py`.

No change to `assign.py`, `layers.py`, `cores.py`, `layer_order.py`, or the
serve path. `grep -c box_pleat mcp_harness/server.py` stays 0.

## 5. What the instruments can and cannot say

The five levels form a chain, each strictly downstream of the last:

> complete candidate -> contradiction found -> irreducible core -> signed core -> piece keys -> clause

A repeat at any level is only meaningful relative to the level above it,
which is why all five are recorded.

| Level | A repeat means | Verdict |
|---|---|---|
| `candidate` | the identical complete labelling was checked twice | **decisive defect.** Nothing in the loop may propose a candidate it has already refuted; `hits_nogood()` blocks exactly this. |
| `witness` | the same contradiction, possibly from a different candidate | expected and harmless on its own — one `taco_tortilla` among three faces can arise under many labellings |
| `core` | the same irreducible crease set | **not a defect** (§3.1). Informative only beside `signed`. |
| `signed` | the same forbidden label pattern, re-derived | the loop re-derived a no-good it already holds. Sound, but wasted work, and the signature of §2's late filter. **Actionable, not a bug.** |
| `keys` | two different crease-level no-goods collapsed to one solver-variable set | extraction's precision is finer than the granularity the solver can use — part of the 25.2x narrowing cannot reach the clause |

**The one thing these instruments cannot do is identify the clause itself.**
The clause is `{var: value}`, and `_check` sees neither `var_of` nor `value`
— they are `assign`'s locals. `keys` is the clause's *input*; two rejections
with identical `keys` still produce different clauses if the values differ.
So a `keys` repeat is suggestive and a `signed` repeat is strong, but
**neither proves a duplicate clause.** Proving that needs a `debug_clauses`
list in `assign.py`, deliberately out of scope (§9) and gated on this run
showing a repeat worth chasing.

## 6. The experiment

### 6.1 Protocol

A replay of core-in-loop arm B with exactly one thing added:

* subject `lizard`, from `rule6_serve.json`, the same entry the A/B used
* `dense=True`, `assign_budget=500_000`, `core_extraction=True`
* `debug_cores`, `debug_clause_sizes` **and** `debug_witness_cores` all
  collected
* one arm. There is no A arm: extraction-off rejections have no core to
  identify, and arm A's 113 rejections are not the population in question.
* expected ~16 minutes, from arm B's measured 954.9 s

`lizard` is the subject for the reason the A/B gave: it is the only one whose
dense loop yields rejections cheaply. `octopus` and `dog` do not finish dense
labelling at all, and the other subjects' first dense candidate blames two
creases with nothing to shrink.

### 6.2 The reproduction guard, fixed before the data

Arm A reproduced the committed baseline on **every structural figure** — 113
rejections, clause 6/202/259, identical failure repr — while differing on
wall clock (1052.0 s vs 834.0 s, 1.26x). So the loop is deterministic in
structure and not in timing.

**The replay must therefore reproduce arm B's structure exactly:**

* 3 rejections
* `debug_cores` rows `(44, 8, 31, *)`, `(361, 5, 47, *)`, `(65, 8, 43, *)` —
  blamed creases, core creases and oracle calls all matching; the seconds
  field is free
* `AssignFail(kind='budget', site=500000)`
* clause sizes min/median/max = 5/8/8. These are the only three
  `debug_clause_sizes` statistics the A/B recorded, so the guard is on the
  triple, not on a per-rejection ordering the artifact never captured.

**If any of these differs, the instrumentation changed the run, and NO row of
§6.3 may be claimed in either direction.** The guard is not a formality: the
`_check` change lifts `keys` into a local and builds a frozenset per
rejection, and a run that diverges after that is a run measuring something
other than arm B.

Wall clock is explicitly **not** guarded — arm A's own 1.26x drift on an
unchanged code path establishes that timing is not reproducible on this
machine, so guarding it would fail for reasons unrelated to the experiment.

### 6.3 The bar, fixed before the data

Evaluated in order; the first row that matches is the verdict.

1. **`candidate` repeats.** **DECISIVE ENFORCEMENT DEFECT.** The loop checked
   a labelling it had already refuted. Stop this experiment line and fix
   `hits_nogood`/`retry`. This does not invalidate the A/B's *numbers* — the
   clause really did narrow 25.2x — but it invalidates every interpretation
   that treats a rejection as new information, including §1's "pruning
   works" reading.
2. **`candidate` distinct, `signed` repeats.** **LATE ENFORCEMENT.** The loop
   re-derived a no-good it already holds, from a different part of the tree.
   Sound but wasted, and exactly what §2's `hits_nogood()` analysis predicts.
   The next lever is clause **propagation**, not the local CSP: watch the
   clause during descent instead of only at full binding. This is lazy clause
   generation's territory and would get its own spec.
3. **`signed` distinct, `keys` repeats.** **GRANULARITY CEILING.** Two
   different crease-level no-goods produced the same solver-variable set, so
   part of extraction's narrowing cannot reach the clause at all. Report the
   fraction; it bounds what any further extraction work could buy.
4. **No repeat at `candidate`, `signed` or `keys`.** **NEW TERRITORY.** Each
   rejection is a different fact. ~~The clause lever is finished: the 166,667
   nodes between rejections are the local CSP working through a legitimately
   narrowed space~~ — **struck 2026-09-28, see §3.3.** This instrument records
   the identity of the rejections, never what the nodes between them were
   doing. What the row establishes is that the **first** of §1's two mechanisms
   did not occur; the second — descent-time waste — is untested by it and
   unaffected by it. The independent 79.57% profile still points at the local
   CSP as the next slice, on its own evidence rather than on this row's.

**Repeats at `witness` or `core` alone do not select a row.** §5 gives the
reason: one `taco_tortilla` among three faces arises under many labellings,
and the same irreducible crease set under different labels is a different
no-good. Row 4 is therefore stated over the three levels that carry a
verdict, and a `witness` or `core` recurrence beneath it is **reported in the
distinct-count table without changing the verdict**. This is deliberate — an
earlier draft of this bar required "all five distinct" for row 4, which left
a witness-only repeat matching no row at all and the run with no verdict.

### 6.4 The honest limit

**n = 3.** The test is **asymmetric**, and the spec commits to saying so in
the evidence README whichever way it falls:

* **One repeat is decisive.** A single recurrence at the `candidate` level is
  a defect regardless of sample size — it cannot be a statistical artifact.
* **Three distinct is weak.** It is consistent with "new territory each time"
  and equally consistent with a loop that would start repeating at rejection
  20. Row 4 must be reported as *"no recurrence in the only three rejections
  this budget produced"*, never as *"the loop does not re-derive"*.

This asymmetry is the reason the experiment is worth 16 minutes despite n=3:
the cheap outcome is the one that closes a line of work, and the expensive
outcome is the one that cannot be reached at this budget anyway.

## 7. Testing

Three tests in a new `mcp_harness/tests/test_box_pleat_witness_identity.py`,
all on the small fixtures the existing core tests use — none runs a dense
`lizard` compile.

1. **The parameter is collected and shaped.** A compile with
   `core_extraction=True, debug_witness_cores=[]` on the smallest fixture
   that produces a rejection yields one dict per rejection, with exactly the
   five keys of §4, and `len(list) == len(debug_cores)`.
2. **`core`, `signed` and `keys` agree with each other.** For every recorded
   row: `{c for c, _ in row["signed"]} == row["core"]`, every label is `"M"`
   or `"V"`, `row["core"] <= row["witness"].creases`, and `row["keys"]` is
   non-empty. This pins the §4 claim that `labels[c]` cannot KeyError by
   exercising it rather than asserting it in a comment.
3. **`None` is byte-identical.** The same compile with
   `debug_witness_cores=None` and with `=[]` returns `Result`s that compare
   equal on `stage_reached`, `repr(failure)`, `layers_tried`, and identical
   `debug_cores` and `debug_clause_sizes` lists. The instrumentation must not
   perturb the run — which is §6.2's guard in miniature, at a size that runs
   in seconds.

Run as full named files, never a `-k` subset:

```bash
PYTHONPATH=. ../.venv/bin/python3 -m pytest tests/test_box_pleat_witness_identity.py tests/test_box_pleat_cores.py tests/test_box_pleat_core_in_loop.py -q
```

`../.venv/bin/python3` is mandatory (`mcp_harness/conftest.py`'s autouse
fixture imports `mesh_to_tree`, gating all collection on
skeletor/trimesh/networkx/numpy), and `--timeout` must never be passed —
that venv has no `pytest-timeout`.

## 8. Risks

1. **The guard fires and the replay diverges.** Then the experiment produces
   no verdict and the instrumentation is the suspect, not the loop. The
   recovery is §7's test 3 at fixture scale: if `None` vs `[]` is byte-
   identical there, the divergence is elsewhere and must be found before the
   16 minutes are spent again.
2. **Row 4 is the outcome and proves little.** The most likely result, and
   §6.4 is the pre-commitment that it will be reported as weak. It still
   closes the clause lever *at this budget*, which is what the next slice
   needs to know.
3. **`lizard` does not generalise.** Unchanged from the core-in-loop spec's
   §9.2: 26 of the 31 rows behind the core measurement were `lizard`, its
   `propagate` is ~100x slower than the other five subjects', and the
   subjects that would test generality cannot produce a dense labelling at
   all. Every row of §6.3 is evidence about `lizard`.
4. **Memory.** Five frozensets per rejection, one of them the complete
   candidate labelling (hundreds of entries). At 3 rejections this is
   negligible; at a 5,000,000-node budget it would not be, and any such run
   must cap or hash rather than retain. Noted so the parameter is not reused
   at scale unexamined.
5. **A `candidate` repeat would be a defect in shipped dense `assign`, found
   by a diagnostic.** If row 1 fires, it affects every dense measurement this
   project has recorded, including the A/B's rejection counts. The response
   is to fix and re-measure, not to reinterpret; and the affected records
   must be marked rather than quietly superseded.

## 9. Evidence

`docs/superpowers/evidence/2026-09-28-witness-identity/`, carrying
`identity.py`, `identity.json` (the full per-rejection records, with
frozensets serialised as sorted lists) and a README stating:

* the §6.2 reproduction guard with each of its four values, measured
* the §6.3 row reached, with the distinct-count table for all five levels
* every repeat found, printed in full
* the §6.4 asymmetry, stated explicitly whichever row was reached
* the §8.3 `lizard` limit

## 10. Out of scope

* **`debug_clauses` in `assign.py`** — the only instrument that could prove a
  duplicate *clause* (§5). Gated on this run reaching row 2 or 3.
* **Run metadata inside the evidence JSON** (a timestamp and the commit SHA the
  run was made from). Deliberately deferred for the third consecutive slice, and
  recorded here rather than in another README paragraph: the identical "a
  successor script should record both" sentence already sits in
  `../../evidence/2026-09-27-core-in-loop/README.md`, this spec's script *is*
  that successor, and it did not. Advice restated and never actioned is on its
  way to becoming permanent, so the next evidence script in this subproject
  should write both fields, and this line is the place that says so. For this
  slice the metadata is recoverable from git instead — `identity.py`'s blob is
  byte-identical at the run commit and at the branch tip, which the evidence
  README names.
* **Clause propagation during descent** — ~~the row-2 follow-on, and only if
  row 2 fires~~ — **re-gated 2026-09-28, see §3.3.** Row 2's trigger is a
  `signed` repeat, and descent-time waste produces no repeat at all, so row 2
  was never a test of it. This needs an instrument that observes the
  **descent**, not the rejections, and it needs one regardless of which row
  fired. Still out of scope for this spec — but no longer gated on a signal
  that cannot detect it, and therefore **not closed on the merits**.
* **Local-CSP optimisation** — the row-4 follow-on, already sized by the
  independent 79.57% profile. Its own spec.
* **The 5,000,000-node run.** Still gated on the core-in-loop spec's §7.2 row
  3, and now also on §8.4.
* **Enabling `core_extraction` by default.** Unchanged: a separate decision
  with its own record.
* **Any change to `assign.py`, `layers.py`, `cores.py`, `layer_order.py`, or
  the serve path.**
* **`2026-09-24-dense-pleats-design.md` component 1 (`pleat_grid.py`) and its
  §10 gallery.** Unchanged: both gated on dense converging.
