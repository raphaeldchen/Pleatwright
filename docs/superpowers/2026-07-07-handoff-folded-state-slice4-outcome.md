# Handoff — folded-state slice 4 OUTCOME (squash deferred; apex-snap + sink shipped)

**Date:** 2026-07-07. Written at the end of the slice-4 session. Supersedes
the *plan* in `docs/superpowers/plans/2026-07-06-squash-slice4.md` where they
disagree: the plan intended to ship `squash`; the de-risk gate (plan Task 2)
**failed provably**, so squash was deferred and the slice re-scoped. Branch:
`feat/squash-slice4` (off `main` d2c7229).

## What shipped

1. **Apex-snap sliver fix** (`shaping_deep._pt_on_edge` rounds to 8 dp) —
   kills the residual ~1e-9 zero-length sliver edge `reverse_deep` emitted
   when two fold-apex split requests differed by ~1.1e-9 (just past `_key`'s
   9-dp dedup). Re-pinned two slice-3 tests that sat exactly on sliver points
   (`new_edges 6→5`; a legit one-edge collapse, corroborated by those tests'
   own pre-existing docstrings). Commit `b974ccd`.
2. **`sink` = verified `reverse_deep(θ=180)` alias.** `probe_sink.py`
   hand-derives an open sink's M/V independently and confirms its crease set
   equals `reverse_deep(θ=180)` on star-4 (fully forced order) → MATCH on both
   tips. `sink:X,Y:D` wired into `parse_op`/`apply_display_op(s)` (needs `raw`,
   counts as the one deep op for ordering). Commits `a77be18`, `8aa81e2`.
3. **`probe_squash.py`** — committed as EVIDENCE of the gate-fail (commit
   `39a5a04`), not a shipped op.

Full backend suite green at branch end (was 391/3 skipped; +new sink/apex
tests). The provenance contract is intact: `web/server.py` unchanged; all
ops ride `display_json`.

## Why squash was deferred — the provable finding

The de-risk gate derived squash on star-4's `v2` flap and **proved it cannot
be a distinct op there**:

- star-4's whole base folds onto ONE triangle; `v2` is an **edge flap** whose
  two layers are exact mirror images across a spine that folds onto the
  boundary of the stacked triangle. **There is no hidden pocket to open.**
- Sweeping all 27 symmetric M/V/F labelings + a perpendicular variant: every
  flat-foldable one that opens the footprint **coincides with `reverse_fold`**
  (`(M,V,V)=reverse_fold sense+ θ>90`, `(M,V,M)=reverse_fold sense− θ<90`);
  every genuinely distinct one **breaks Maekawa** — `body=M` at the degree-8
  center `v3`, `body=F` at the new apex, the perpendicular variant makes odd
  (degree-3) vertices.

**The crisp statement: on an EDGE flap, a flat-foldable symmetric squash *is*
`reverse_fold`.** And our `tips()` signature (`B` edge + exactly one `M/V`
crease) *inherently selects edge flaps* — so a tip-anchored squash is
redundant across ALL our bases, not just star-4.

## The strategic takeaway (read before scoping the next slice)

At the **tip-local edge-flap anchor**, the primitive family is effectively
**complete**: `reverse_fold` + `reverse_deep` exhaust the distinct moves.
**Squash reduces to `reverse_fold`; sink reduces to `reverse_deep`** (both now
proven, not assumed). New folded-state territory requires leaving that anchor.

Genuine squash lives on **interior-spine pockets** (a folded spine with two
*distinct* stacked layers to spread open, revealing hidden paper). Our bases
DO contain interior fold structure the current anchor can't reach — interior
crease vertices (deg≥3, no `B`): star-4 = 1, quad = 2, **dog = 13**. But:

- **This count over-counts.** deg≥3 all-crease vertices include river/gusset
  junctions, not just openable pockets. A naive "opening reveals new area"
  probe **false-positives on star-4** (opening `v2` reveals area yet still
  reduces to `reverse_fold`). Confirming a genuine pocket requires attempting
  the flat-foldable+distinct construction — i.e. the derivation itself.
- None of star-4/quad/dog is simple enough to **hand-derive** a pocket squash
  on (dog's target cells are 4–96 free pairs). A real squash slice needs a
  **new synthetic pocket fixture** (preliminary/bird-base petal style — like
  slice-3's `pent2`/`acc4` synthetics) that is hand-checkable.

## Recommended next step (a fresh brainstorm decision, not a patch)

Two honest options — brainstorm which, do not bolt onto this slice:

1. **"Squash on interior pockets" as its own slice.** Requires: (a) a new
   anchor (interior fold vertex/spine, NOT `_find_tip`); (b) a new
   hand-checkable synthetic pocket fixture; (c) a re-run of the de-risk gate
   on THAT fixture before any impl. This is real design work.
2. **Move to B5 (target-mesh-guided shaping) instead.** If the tip-local
   primitive family is complete and interior-pocket squash is a large effort,
   B5 may deliver more user value per unit work. B5 was always LAST in the
   roadmap; this finding is a reason to weigh it now.

## Deferred / carried

- **Squash** — deferred with the provable rationale above; needs a fresh
  brainstorm (option 1) or a decision to skip toward B5 (option 2).
- **Agent/SYSTEM_PROMPT wiring** for `reverse_deep` + `sink` — still its own
  mini-PR (never built). `squash` vocabulary is moot until/unless it ships.
- Minor (final-review triage): the `sink`-without-`raw` error message reads
  "sink needs the raw base fold" (cosmetic; it's a `reverse_deep` alias).
- Process artifacts: SDD ledger `.superpowers/sdd/progress.md` (gitignored);
  probes `probe_squash.py` / `probe_sink.py` committed as evidence.
