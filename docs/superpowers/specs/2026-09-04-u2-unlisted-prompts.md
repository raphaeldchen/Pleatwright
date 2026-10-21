# Spec: does `anatomy_spec` work on the prompts it exists for?

**2026-09-04. A MEASUREMENT spec. It gates U2's wiring and authorises nothing
else.**

## 1. The question

`anatomy_spec` extends the 14-row authored anatomy table to prompts the table
does not cover. That is its only purpose: `reference_count_for` already answers
listed subjects, and on a table hit the model is never consulted.

**Nobody has measured whether it answers unlisted prompts correctly.** U2 is
dormant until this returns SHIP — see
`docs/superpowers/decisions/u2-u4-dormancy.md` for why wiring first is
unacceptable.

## 2. The design — the humans already wrote the answer key

Ask the model for each of the **14 authored subjects**, with the table's answer
never shown to it, and compare against the human-authored count.

This is a genuine held-out test and it costs no new ground truth:

* `fixtures/anatomy_expectation.json` was hand-authored **2026-08-21**, one
  commit, untouched since. It predates this spec by two weeks.
* Every row carries its own `derivation` and `citation`, so the target is
  auditable rather than asserted.
* The model never sees the table, so there is no leakage to control for. This
  is not leave-one-out in the ML sense — it asks whether the model's anatomical
  judgement matches a human's.

⚠ **The table has only THREE distinct values** — 5, 6 and 9, distributed 4/6/4
across the fourteen rows. That makes a trivial baseline strong and the bar must
beat it arithmetically, not merely look good.

## 3. THE BAR — pre-registered

```
H1  ACCURACY.  >= 11 of 14 exact matches to the authored count.
    The null is the MAJORITY-CLASS baseline: always answer 6 scores 6/14 =
    0.429.  Under H0 that the model is no better than that constant,
    P(X >= 11) = 0.0074.  (k=10 gives p=0.0297, which is not a margin worth
    wiring the pipeline's primary ranking key on.)

H2  NOT A CONSTANT.  The model's answers must take at least 3 distinct values
    across the 14 subjects.  A model that always answers 6 scores 6/14 by
    construction and has learned nothing; that must be excluded arithmetically,
    not by inspection.

H3  DISCARD RATE.  <= 3 of 14 rows may be DISCARDED for missing a derivation
    or a citation.  anatomy_spec discards rather than downgrades, so a high
    discard rate means the unit answers almost nothing -- which is a failure
    even if every surviving row is right.

H4  STABILITY, and this one is why the spec exists.  K = 5 draws per subject,
    aggregated by MODE, fixed before the run.  A subject whose 5 draws contain
    no majority value counts as WRONG, not as absent.
    ⚠ U5' measured this exact model producing five opinions with no majority
    on 2 of 5 subjects, on a structurally similar task.  If R is equally
    unstable it cannot steer fidelity_score, whatever its mean accuracy.
    REPORT the per-subject majority size alongside the answer.

H5  BUDGET.  <= 70 billed calls (14 x 5 = 70).  Hard abort.

DO NOT SHIP U2 IF: H1, H2, H3 or H4 fails.
```

### What each outcome means

| outcome | decision |
|---|---|
| all four pass | **U2 may be wired**, behind a flag, default OFF, with §15's gate rebuilt first |
| H1 passes, H4 fails | **DO NOT WIRE.** An accurate-on-average but unstable R is worse than no R: it moves the terminal exit run to run |
| H2 fails | **DO NOT WIRE**, regardless of H1 — the accuracy is the baseline wearing a costume |
| H3 fails | U2 answers too little to matter; report the rate and stop |

## 4. Out of scope

Wiring. This spec measures and does not authorise integration; §15's own
acceptance gate is separately known to be vacuous (a committed test shows the
five-fixture scorecard cannot see the seam) and must be rebuilt before anything
is wired, whatever this measurement says.
