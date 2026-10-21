# Were arm B's three rejections three different facts, or one fact three times?

Spec: `../../specs/2026-09-28-witness-identity-design.md`. Script: `identity.py`.
Artifact: `identity.json` (the guard, the distinct counts, the repeat map, and all
three per-rejection records in full).

**Every measured figure in this file is read from `identity.json`**, re-read after
the process exited rather than transcribed from the log watched while it ran.
Figures cited from earlier evidence directories are attributed inline on every
appearance. Figures obtained by arithmetic or set operations on the artifact's own
lists are marked *derived* and show their derivation. **Run metadata — date,
commit, exit status — is this README's own record and is not in the artifact**,
because `identity.py` writes neither a timestamp nor a commit into the JSON; a
successor script should record both there.

```
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -u \
    ../docs/superpowers/evidence/2026-09-28-witness-identity/identity.py \
    ../docs/superpowers/evidence/2026-09-28-witness-identity/identity.json
```

Run 2026-09-28 on `c999c71`, launched in the background, exit 0. The script's
self-test (`--selftest`) was run immediately before and passed: the bar's four
rows plus precedence, the guard's 11 cases, `repeats`, `distinct` and `serialise`.
`identity.py` was not modified at any point during or after the run.

**`cores.CoreExtractionError` was not raised** — `core_extraction_error` is `null`.
That matters for the same reason it did in the A/B: `_core` checks its own pre- and
postcondition and raises rather than returning an unsound core, so its absence is
the evidence that the three cores recorded here are the cores they claim to be. Had
it fired, `identity.py` would have printed `CORE EXTRACTION ERROR` and refused a
verdict outright.

---

## Verdict: §6.3 row 4 — NEW TERRITORY. §6.2's guard PASSED.

`verdict` = `NEW TERRITORY`, `verdict_level` = `null`. **All five identity levels
are fully distinct across the three rejections**, and `repeats` is empty at every
one of them:

```
distinct over 3 rejections: candidate=3  witness=3  core=3  signed=3  keys=3
```

**This is the weakest of the four rows the spec pre-registered, and it is reported
as weak.** See §6.4 below, which was written before the data existed and is honoured
here literally.

## 1. The question

The core-in-loop A/B (`../2026-09-27-core-in-loop/`) settled that the no-good clause
narrows hard — median **202 → 8 solver variables, 25.2x**, *its* figures, not this
run's — and that extraction is not the cost. It left the terminal outcome unmoved:
both arms ended `AssignFail(kind='budget', site=500000)`. What moved was the
rejection count, **113 → 3** (again that directory's figures), and that single number
admits two opposite readings. Either stronger clauses are excluding more of the space
a priori, so fewer distinct complete candidates survive to be checked — or the search
is spending its budget re-deriving ground it has already forbidden, or descending
branches a stored clause should have cut earlier. Every instrument
the A/B carried was **aggregate**: counts, clause sizes and wall clock are all
consistent with both stories. The distinction is not about how many rejections there
were but about **whether they were the same rejection**, and that is a question about
identity. This replay adds `debug_witness_cores` — which records what each rejection
*was* at five points along the chain from candidate to clause — and changes nothing
else.

## 2. The reproduction guard (§6.2)

Arm A reproduced the committed baseline on every structural figure while drifting
1.26x on wall clock (1,052.0 s against 834.0 s — `../2026-09-27-core-in-loop/`'s
figures). So this loop is deterministic in structure and not in timing, and the
replay had to reproduce arm B's **structure** exactly or forfeit any verdict in
either direction.

`guard_passed` = `true`, `guard_mismatches` = `[]`.

| guarded value | expected (arm B) | measured, this run | |
|---|---|---|---|
| rejections | 3 | **3** | **PASS** |
| `debug_cores` rows, first three fields, **in order** | `(44, 8, 31)`, `(361, 5, 47)`, `(65, 8, 43)` | **`(44, 8, 31)`, `(361, 5, 47)`, `(65, 8, 43)`** | **PASS** |
| `failure` | `AssignFail(kind='budget', site=500000)` | **`AssignFail(kind='budget', site=500000)`** | **PASS** |
| `debug_witness_cores` records | 3 | **3** | **PASS** |
| clause sizes, full sorted population | `(5, 8, 8)` | **`(5, 8, 8)`** (recorded order `[8, 5, 8]`) | **PASS** |

Both the expected and the measured column are in the artifact: the expected values
are `arm_b` (which also carries `source`, `../2026-09-27-core-in-loop/ab.json`), and
the measured ones are `rejections`, `core_rows`, `failure`, `records` and
`clause_sizes`. The `core_rows` 4th field is wall clock and deliberately unguarded;
this run read `3.944`, `7.678`, `5.503` s. Arm B's corresponding `5.069`, `9.789`,
`6.847` are **not** in this artifact — `arm_b.core_rows` carries three fields per row
by design — and are cited from `../2026-09-27-core-in-loop/ab.json`.

**The table has five rows where the spec §6.2 lists four, and the fifth is a
different kind of number.** `records` — the `debug_witness_cores` population that
`distinct()` and `verdict()` are actually computed from — was added by the script
because `len(clause_sizes)` and `len(core_rows)` are different populations that
merely coincide with it here; `compile.py` documents that a narrowed clause can come
back empty and produce a different `AssignFail` instead of a learned no-good, so the
three counts can diverge. Its bar of 3 is **inferred**, not measured by arm B: arm B
predates the parameter and `ab.json`'s `arms[1]` carries no witness-record count at
all. The inference (`len(core_rows) == 3` plus the two append sites sitting in the
same basic block of `_check`) is sound, and `identity.py`'s `guard` docstring says so
in exactly these terms. It is recorded here rather than presented as a fifth
measurement.

**The clause-sizes row deserves the same flag.** `ab.json` does not publish a sorted
population of three clause sizes; it publishes `clause_vars_min/median/max` = 5/8/8,
and `(5, 8, 8)` above is exactly recoverable from that triple only because the
rejection count is pinned at 3 by the row above it. The table presents it as a
population for readability; arm B recorded a min/median/max, not a list.

Three further readings agree with arm B without being guarded, which is worth
recording because a guard can only fail on what it checks: `stage_reached` =
`assign`, `layers_tried` = **3** (equal to the rejection count, which is what a run
that never accepts a candidate looks like), and `layer_verdict` = `"None"` — the
string, because the script records `repr(res.verdict)`, so the layer stage produced no
verdict object at all.

## 3. The distinct-count table

Five levels, three rejections, and **`repeats` is the empty map at every level**.

| level | distinct | of rejections | repeats found |
|---|---|---|---|
| `candidate` | **3** | 3 | none |
| `witness` | **3** | 3 | none |
| `core` | **3** | 3 | none |
| `signed` | **3** | 3 | none |
| `keys` | **3** | 3 | none |

**Every repeat found, printed in full: there are none.** `identity.json`'s `repeats`
field reads `{"candidate": {}, "witness": {}, "core": {}, "signed": {}, "keys": {}}`,
and the script printed no `REPEAT at ...` line. That is the whole of this section's
positive content, and the rest of it is the part that stops the reading from being
flattering.

**Distinct is not disjoint, and at the `candidate` level it is barely distinct at
all.** *Derived* from the artifact's `rejection_records` by set intersection over the
recorded lists:

| pair | `candidate` labels shared, of 745 | `core` shared | `signed` shared | `keys` shared |
|---|---|---|---|---|
| rejection 1 & 2 | 677 (68 creases differ) | 1 | **0** | 1 |
| rejection 1 & 3 | 677 (68 creases differ) | 4 | 4 | 53 |
| rejection 2 & 3 | 657 (88 creases differ) | 2 | 2 | 25 |

All three candidates are complete labellings over the **same** 745 creases (the key
sets are identical; every value is `M` or `V`), and each pair agrees on 88.2% to
90.9% of them — 657/745 for rejections 2 & 3, and 677/745 for the other two pairs.
**For scale:** two independent labellings over 745 binary creases would be expected to
agree on about half by chance, ~372/745 — an expectation for independent labellings
offered as a reference point, not a claim about these three, which are outputs of one
search rather than independent draws. The three rejections are therefore three
different facts in the strict sense the bar asks about, and also three nearby points:
rejections 1 and 3 share 53 of their 83 and 80 `keys`, and 4 of their 8 `signed`
pairs. **Nothing in the bar is softened by that** — a `keys` set that shares 53 of 83
elements with another is still a different clause input, and the bar is about
identity, not distance. But it is the reading a reviewer would find on their own, and
it points the same way as §5: this is not a picture of a search ranging widely.

Two consistency checks that fell out of the records. All three witnesses are
`taco_tortilla`, with distinct `faces` (`[145, 186, 158]`, `[18, 19, 3]`,
`[146, 189, 133]`) and distinct `prov` strings naming distinct creases — so the
`witness` level is distinct *on its contents*, not merely on object identity, which
is the failure mode that would make a `distinct=3` reading vacuous. And
`len(witness.creases)` reads 44, 361, 65 — reproducing `core_rows`' blamed-crease
column exactly, from a different field of the artifact.

## 4. The verdict (§6.3), and why this row and not its neighbours

**Row 4, NEW TERRITORY.** The bar is evaluated in order and the first matching row
wins; rows 1 through 3 all require a repeat, and there is none:

* **Not row 1, ENFORCEMENT DEFECT.** That needs a `candidate` repeat — the loop
  checking a labelling it had already refuted. `distinct.candidate` = 3 of 3 and
  `repeats.candidate` = `{}`. Had this row fired it would have invalidated every
  interpretation that treats a rejection as new information, including the A/B's own;
  it did not fire.
* **Not row 2, LATE ENFORCEMENT.** That needs a `signed` repeat — a no-good
  re-derived from a different part of the tree, which is what `assign.hits_nogood`
  pruning only on full binding predicts. `distinct.signed` = 3 of 3, and the pairwise
  `signed` overlaps are 0, 4 and 2 of 8/5/8, so no forbidden label pattern recurs.
* **Not row 3, GRANULARITY CEILING.** That needs a `keys` repeat — two crease-level
  no-goods collapsing onto one solver-variable set. `distinct.keys` = 3 of 3, with
  sizes 83, 28 and 80. The 53-element overlap between rejections 1 and 3 is not a
  collapse: the sets are unequal, so extraction's precision did reach the clause
  input three separate times.
* **Row 4 does not require all five levels distinct**, and the spec is explicit that
  it must not: a `witness` or `core` recurrence is reported without changing the
  verdict, because one `taco_tortilla` among three faces arises under many labellings
  and the same irreducible crease set under different labels is a different no-good.
  Here the question is moot — all five read 3 — but the row would have been the same
  with a witness-only repeat, and a reader should not take `witness=3` as part of the
  evidence for the verdict.

**What it makes the next slice.** The clause lever is finished **at this budget**: on
these three observations the nodes between rejections are the local CSP working
through a legitimately narrowed space rather than re-treading forbidden ground — and
"on these three observations" is doing real work in that sentence, per §5. **That
sentence is untested in one respect this instrument cannot reach: it records the
identity of the three rejections, not what the nodes between them were doing, so
descent-time waste — a stored clause pruning only on full binding, cutting nothing on
the way down — is untested by this run and unaffected by the row-4 result.** That is
500,000 / 3 =
**166,666.7 nodes per rejection** (*derived* from `assign_budget` and `rejections`),
and it corroborates the independently measured **79.57%** local-CSP share of dense
`assign`'s time — that figure is `../2026-09-24-dense-pleats/`'s, not this run's, and
this run neither reproduces nor tests it. So §10's two gated follow-ons resolve as:
**`debug_clauses` in `assign.py` stays out of scope** (it was gated on reaching row 2
or 3, and neither fired — there is no repeat worth chasing), and **clause propagation
during descent is not closed on the merits**: row 2's gate is a `signed` repeat, and
descent-time waste produces no repeat of any kind, so the row-4 result only means the
bar's row-2 trigger did not fire, not that propagation during descent was tested and
cleared. That question stays open and would need an instrument that watches the
descent itself rather than the rejections — the local CSP is still what this run
points at, and none of this reorders §10's priorities. The negative direction is the
load-bearing one: this run's contribution is that it removes one of the two
mechanisms §1 gave "the search wandered" — the one that predicts a `candidate` or
`signed` repeat — not that it establishes a reading, and not that it clears the
mechanism this instrument cannot see.

**A note on `identity.py`'s own stdout.** The script's NEW TERRITORY branch
(`identity.py:433-440`) prints this claim without the caveat above, because that
message predates this correction: *"The clause lever is finished AT THIS BUDGET: the
166,667 nodes between rejections are the local CSP working through a legitimately
narrowed space, corroborating the independent 79.57% profile."* Anyone who reruns the
script sees only that sentence on stdout, so it must be read through this section's
caveat rather than taken as the final word. `identity.py` was deliberately left
unedited rather than patched to add the caveat inline: editing it would falsify §2's
statement that the instrument was not modified during or after the run, and would
destroy the byte-identical reproducibility that is what makes this run's claim
checkable rather than merely asserted. That is a considered trade, not an oversight.

**Limits of the instrument itself.** Two further properties of `identity.py` are
recorded here because fixing them means editing the instrument, which this correction
does not do. First, the "166,667" above is a literal inside that f-string, not
derived from the run, unlike `{n}` (the rejection count) in the same message, which
*is* interpolated — had this run produced 4 rejections and still selected row 4, the
script would still have printed 166,667, when the true figure would have been
125,000; this README's own 166,666.7 in §4 above is derived from `assign_budget` and
`rejections` and is correct for this run. Second, `identity.py`'s `ARM_B` carries both
`clause_min_median_max` (5, 8, 8) and `clause_sizes_sorted` (5, 8, 8); only the second
is compared by `guard`, the first appears only in the mismatch message, and nothing
asserts one implies the other, so a future edit to one and not the other would drift
silently. A successor script should interpolate the per-rejection figure and assert
the two clause-size constants agree.

## 5. The n=3 asymmetry (§6.4)

The spec committed, before any data existed, to stating this whichever way the run
fell, and the row it fell on is the one that needs it.

**There was no recurrence in the only three rejections this budget produced.**

That is the whole of the finding, and it is **weak**. The test is asymmetric by
construction: a single repeat at the `candidate` level would have been decisive at
n=1, because a recurrence cannot be a statistical artifact — but three distinct is
consistent with new territory each time and **equally consistent with a loop that
would begin repeating at rejection 20**. This budget produced three rejections, so
this run cannot tell those apart, and no figure in it does. The §3 observation that
the three candidates already agree on 677 of 745 labels is a reason to hold that
caveat more firmly rather than less.

**This README does not claim, and this run does not support, that the loop does not
re-derive.** It claims that in three rejections it did not, and that the 500,000-node
budget affords no fourth observation.

## 6. What these instruments cannot say (§5)

**No reading here proves a duplicate clause, and none here is a reading of a clause
at all.** The no-good `assign` stores is a `{variable: value}` map built in `assign`'s
own locals; `_check` sees neither `var_of` nor `value`. `keys` is the clause's
**input**, not the clause: two rejections with identical `keys` would still produce
different clauses if their values differed, so a `keys` repeat would have been
suggestive and a `signed` repeat strong, and **neither would have been proof**.

In the direction this run actually fell, the asymmetry runs the safe way — distinct
inputs cannot produce a duplicated clause, so "no duplicate clause among these three"
follows. But that is the only clause-level statement available, and it is available
only because there were no repeats. Proving a duplicate clause, had one been
suspected, would need a `debug_clauses` list in `assign.py`, which §10 keeps out of
scope and gated on exactly the repeat this run did not find. Relatedly, a `core`
repeat would not by itself have been a defect: the same irreducible crease set under
a different label pattern is a legitimately different no-good, which is why `core`
and `witness` carry no verdict.

**A related precision about `candidate`.** The `candidate` level recorded here is
`_check`'s derived map `labels = {k: a for _, _, k, a in ff.shared_edges if a in
("M", "V")}` (`compile.py:350`), not `assign`'s own `cand` object. `labels` is a
function of `cand`, so the direction this run fell is airtight — three distinct
`labels` imply three distinct `cand`, and `labels` is exactly what `propagate`
judges. The converse does not hold: had a `candidate` repeat fired, the step from "a
labelling was checked twice" to "`hits_nogood` should have caught it" would need one
more link, because `hits_nogood` filters `assign`'s own solver variables rather than
shared-edge labels. This does not affect this run's verdict, which needed only the
direction that holds.

## 7. Limits — every figure here is evidence about `lizard`

Unchanged from the core-in-loop spec's §9.2 and repeated because it bounds all of the
above. **26 of the 31 rows behind the core measurement were `lizard`**
(`../2026-09-27-nogood-core/`), whose `propagate` is ~100x slower than the other five
subjects' (1.070 s against 0.004–0.014 s, `../2026-09-24-dense-pleats/`) — and the
subjects that would test generality **cannot produce a dense labelling at all**, or
arrive with a blamed set of two creases and nothing to shrink. `lizard` is the subject
here for that reason and not by preference: it is the only one whose dense loop yields
rejections cheaply. There is one arm and one subject, and `subject` = `lizard` in the
artifact. Whether another subject's dense loop re-derives its no-goods is untested and
untestable by this instrument today.

The single-subject limit and the n=3 limit compound rather than overlap: this is three
observations of one subject at one budget, and nothing here licenses a statement about
dense `assign` in general.

## 8. Cost

`secs` = **786.1** (13 m 6 s), a single arm. Extraction accounted for
3.944 + 7.678 + 5.503 = **17.1 s**, **2.18%** of it (*derived* from `core_rows`'
4th field and `secs`) — so instrumented extraction is still not the cost, on the same
within-arm basis the A/B used. Oracle calls, the portable figure that does not depend
on any subject's propagation speed, read 31, 47, 43 — median **43**, total **121**
(*derived* from `core_rows`' 3rd field), which matches the A/B's count for the same
three rejections. That agreement is a **precondition** of this run having reached any
verdict at all, not independent corroboration: it is the same field §2's guard table
already compares (`debug_cores` rows' first three fields), so a mismatch here would
have failed the guard before any row of §6.3 could be claimed.

**Wall clock is not guarded, and this run is why that decision was right.** Arm B's
954.9 s (`../2026-09-27-core-in-loop/ab.json`'s figure) against this run's 786.1 s is
**0.82x** — a drift of
the same order as, and in the opposite direction from, arm A's 1.26x on a code path
that had not changed at all. Had §6.2 guarded timing, this replay would have failed
its guard for reasons with nothing to do with the instrumentation, and the experiment
would have produced no verdict. The per-rejection extraction seconds drifted the same
way (3.944/7.678/5.503 against arm B's 5.069/9.789/6.847, `../2026-09-27-core-in-loop/ab.json`'s
figures again) while the oracle counts they accompany are identical, which is the same fact
seen at row scale: **the structure reproduced, the clock did not.**
