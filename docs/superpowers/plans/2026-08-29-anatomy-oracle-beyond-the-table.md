# The anatomy oracle beyond the table

**Status: NOT BUILT. Documented 2026-08-29 so the ceiling is on the record.**
Z1 (PR #162) switched on `IDE_EXTERNAL_R` and measured it. This note states what
that fix does *not* cover, and what a scaling version would have to preserve.

## What shipped, and its ceiling

`fixtures/anatomy_expectation.json` is a hand-authored table of **14 rows**:

    water bear · tardigrade · octopus · lizard · lizard with a long tail
    bird · dog · cat · horse · frog · spider · starfish · human · person

Matching is deliberately strict — lowercase, trim, collapse internal whitespace,
strip surrounding quotes and one trailing `.`/`!`/`?`, drop one leading article.
**No stemming, no substring match, no fuzzy match, no synonym expansion.**

So `"a pangolin"`, `"golden retriever"` and `"a three-legged dog"` all return
`None`, fall back to the self-derived `R`, and **the closed loop is fully intact
for them**. For any subject outside those 14 rows, Z1 does nothing at all.

That is a real ceiling on a system whose premise (CLAUDE.md §1) is that a user
dictates *an arbitrary anatomical concept*. The table cannot be extended by
enumeration — the domain is open.

## Why the strictness is correct anyway

From the fixture's own `key_normalisation` note:

> *An unknown prompt returns None — an oracle that always has an answer is the
> closed loop wearing a different hat.*

Fuzzy-matching `pangolin` onto `lizard` would replace a self-derived wrong
answer with a confidently-wrong external one, which is strictly worse: the
self-derived value at least carries `r_provenance: "self-derived"` and the
report's "R IS NOT GROUND TRUTH" caveat. **Returning nothing is the right
failure.** Do not relax the matcher to raise coverage.

## The reusable asset is the CONVENTION, not the counts

The 14 numbers are disposable. This is not:

> One Metric Tree leaf per distinct **terminal appendage**: each arm, leg, wing,
> tentacle or ray counts one; the head counts one; the tail counts one when the
> animal has an external tail. Sub-flap detail (digits, antennae, ears, eyes,
> fins that are not skeletal limbs) is **not** counted — it is not a uniaxial-base
> flap at this scale.

*"How many legs does a spider have"* is trivia any model knows. *"Does the head
count? Do antennae?"* is where counts stop being comparable, and that judgement
is written down once and applies to every animal that will ever be asked for.
Any automated oracle must be given this convention verbatim, or its counts are
not commensurable with the committed rows.

## The proposed ladder (unbuilt)

Cheapest and most trustworthy first; each rung falls through to the next:

1. **Table hit** → use it. Cited, human-checked, free.
2. **Table miss** → ask a model for a count *from the prompt alone*, given the
   convention above. One cheap call, before any mesh is drawn.
3. **Model uncertain / unusual subject** → ask the user. This is a
   human-in-the-loop IDE (CLAUDE.md §5 Step 1); asking once is cheap.
4. **Nothing** → self-derived `R`, stamped `r_provenance: "self-derived"` and
   reported loudly. Today's behaviour, unchanged.

**The seam already exists and is in the right place.** `server.py:3857` resolves
the count from the *prompt* before a mesh exists:

    auto_mesh_to_metric_tree(glb, reference_count=anatomy_expectation.reference_count_for(prompt))

Rungs 2–4 slot in behind that one call. Nothing downstream changes.

## The invariant that must survive every rung

**The oracle may never read the extracted skeleton.**

A model asked *"how many appendages does a pangolin have?"* is independent of the
generator. A model asked *"look at this skeleton and count its limbs"* is the
closed loop again, wearing a better disguise. RTLFixer, CADSmith and the ICLR
self-repair studies all reduce to this one rule; it is why `anatomy_reference.json`
was frozen and relabelled (it was `reference_feature_count`'s own past output
wearing a ground-truth filename).

This is also why rung 2 is **not** what the judge's authority rule forbids.
Asking a model for a fact about an animal is *recall*. Asking it whether a design
is good is *judgement*. Only the second is vetoed, and for measured reasons
(`vlm_judge.py`, authority rule; `docs/superpowers/decisions/axis-a-verdict.md`).

## What rung 2 must not skip

A model-based counter can be confidently wrong, and **a wrong HIGH count is worse
than no count** — it pushes the search past good candidates chasing limbs the
animal does not have. So rung 2 ships under the same discipline as everything
else here (`COORDINATION.md` §4.1):

- a **required-fail input** it must score as failing, asserted in a test —
  suggested: a subject whose true count the model reliably overstates;
- a **measurement across subjects, both arms**, before any default flips —
  the Z1 shape: a subject where it should change the serve, one where it should
  change only the score, and a **control where it must be a no-op**;
- `r_provenance` extended to distinguish `model` from `external` and
  `self-derived`, so a reader can always tell which rung answered.

## What none of this fixes

`fidelity_score` clamps to `r_eff = min(max(R, 4), 8)`. An 8-leaf serve of a
9-appendage animal reads **exactly 1.0000 even against a correct R of 9**, and 9
appendages do not fit an 8-flap window at all. A better oracle makes the search
stop lying about when it is done; it does not raise the servable ceiling. That is
the `MAX_LEAVES` question and it is separate — **measure that ceiling on its own
evidence, do not move the constant to reach a headline** (CLAUDE.md §1.1).
