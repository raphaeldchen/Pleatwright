# Spec: P3 — shape, not count

**2026-09-04. Supersedes §§12, 14 and 15 of
`2026-09-01-llm-guided-extraction-design.md`.**

P3 was specified as *the LLM becomes a producer*: U5 writes candidate stick
figures, U7 critiques them, §15 wires both into the search. **Two of those three
should not be built as specified, and the third's headline gate is provably
vacuous.** What survives is real, narrower, and lands on the one axis P2 was
forced to leave inactive.

## 1. What is dead, and why

### 1a. U5's justification — Class 3 is empty

§12 rested U5 entirely on *"this is the **only** answer to Class 3. The lizard's
six flaps are provably absent from all 64 mesh cells."* **Refuted 2026-09-03 on
the very mesh the fixture records** (sha `6d1edc99…`), instrument validated
first at 0 diffs across 128 cells:

| arm | 6-leaf cells of 64 | production serve |
|---|---|---|
| default (at the time) | **0** — the fixture reproduces | 5 leaves, 1 pair |
| freeze | 2 | **6 leaves, 0 stubs, fidelity 1.0** |

`label_leaves` on that serve reads *right/left hind limb (pair 1), right/left
hind limb (pair 2), likely tail, likely head* — four legs, head, tail, **no LLM
involved.** The freeze is now the default (PR #185). Class 3 is empty.

**Octopus and water bear are not a replacement.** Their nine leaves *are*
extracted (9 of 64 cells for the octopus) and die at `MAX_LEAVES = 8` — and §15
says U5's trees enter the same queue, so U5 dies at the identical constant.

### 1b. U7's veto — structurally impossible at the ordering that argues it is safe

§14 wants the critic to reach the search as *"at most a veto flag"*, and argues
safety from its ordering: it runs **after** the serve is recorded.
`server.py:4153` completes the search; the judge is called at `:4165`. **A veto
cannot gate what has already happened.** The two halves of §14 are mutually
exclusive.

Worse, the guard protecting the advisory shape is **bypassable**:
`vlm_judge._FORBIDDEN_KEYS` polices exact key names — `'veto'` is refused,
`'blocking'` passes.

### 1c. §15's byte-identity gate — vacuous

§15 promises degradation *"pinned by test on all five committed fixtures"*.
A committed test already proves the five-fixture scorecard **cannot see the seam
P3 would wire**. A gate that cannot observe the change it gates is not a gate.

## 2. Four citation defects in the original spec, all verified against source

CLAUDE.md §0 exists because a reviewer will check. These were found by checking.

| # | claim | what the source says |
|---|---|---|
| **A1** | §14: *"their deployed judge reaches 0.715 … +7.9 points"* | COrigami deploys **two** judges and 0.715 is the weaker. §4.1 verbatim: *"we deployed this double tournament in practice"* — Table 2C `Double` = **0.803 / 0.811**, i.e. **+16.7pp**, not +7.9. The spec cited the row supporting its conclusion. **§14's conclusion still stands** — our own 0.169-LSD result and the order-flip are far stronger evidence either way — but the citation must be corrected. |
| **A2** | §12: *"COrigami measured T=1/N=4 beating T=0/N=1 … we should take the diversity"* | Table 2 lives entirely inside §4.1 **VLM Evaluator Benchmarking** and sweeps the **judge's** decoding config. COrigami reports **no temperature or sample-count ablation for the stick-figure generator anywhere.** A category transfer: an evaluator's best-of-N budget says nothing about a producer's temperature. Rest the claim on Olausson et al., who measured producers, or drop it. |
| **A3** | §4: COrigami's stick figure carries *"declared symmetry"* | **It does not.** Appendix C.1's schema has no pairs field, no symmetry field, no mirror declaration. Symmetry is prompt-*encouraged* and expressed **implicitly** through mirrored azimuths and left/right names. ⚠ **This is the most damaging of the four for P3** — see §4. |
| **A4** | §12: an LLM tree *"passes `tree_contract` as a hard gate"* | `tree_contract` has **one** production caller, `server.py:4333-4335`, inside the `validate_tree` MCP tool. **Nothing on the compile path calls it** — not `draft_and_compile_full_base`, not `auto_mesh_to_metric_tree`, not `_default_compile_fn`. It is advisory to the agent and never enforced. The search's real admission test is `structural_prefilter` (`mesh_to_tree.py:3408-3436`). |

## 3. What survives — U5′

> **Given a count the pipeline now reaches deterministically, can an LLM supply
> the SHAPE — the pairing and attachment topology the mesh gets wrong?**

The concrete case: the lizard now serves **6 leaves with 1 pair**, where four
legs should give **2**. The count is right and the shape is not. That is
checkable against a mesh which demonstrably *contains* the limbs, so it is not
the unfalsifiable "a limb is missing" claim U5 was making.

**Why this is a smaller trust surface.** U5 would inject anatomy no measurement
supports — the closed loop this design exists to escape, pointed the other way.
U5′ only **re-describes anatomy already extracted.**

## 4. ⚠ The two findings that shape U5′'s design

### 4a. `_serve_rank` is actively inverted against a correct LLM tree

`_serve_rank` (`mesh_to_tree.py:2027-2048`) is:

```
(fidelity_score(leaves, anchor_r), -stub_flaps, _STAGE_INTEGRITY[stage], len(pairs))
```

Keys 2–4 are computable for an LLM tree. **Key 1 is not safe.** `anchor_r` is
either the authored count or `reference_feature_count`'s vote **over the mesh's
own prune curve** — and for the lizard that vote reads **R = 5 across the entire
shipped grid**.

> So on an unlisted prompt, an LLM tree carrying the **correct 6 leaves** is
> scored against **R = 5** and ranked *below* the mesh tree it was meant to
> correct. §15's "ranked by the same `_serve_rank`" is not neutral; it is a
> penalty on being right.

**U5′ must therefore not enter the ranker on key 1.** It changes `len(pairs)`
(key 4) on a tree whose leaf count it does **not** touch — which is exactly the
shape that makes the existing ranker safe to reuse, because keys 1–3 are held
constant by construction.

### 4b. There is no prior art that an LLM reliably *declares* pairs

Per A3: COrigami's schema has no pairs field, and our schema **cannot express
angles** (`judge_loop.LEVERS` records this), so the mirror cannot arrive
implicitly as mirrored azimuths the way COrigami's does. It must arrive as an
explicit `symmetric_pairs` list.

**U5′ must invent that field and carry its own evidence that a model fills it
correctly. Nothing can be inherited here.** That is the single largest risk in
this spec and the bar below is aimed at it.

## 5. THE BAR — pre-registered. U5′ and U7 fail independently.

### Step zero — RUN 2026-09-04, under the real default. Two of §1.1's three classes are void.

Re-swept the 8×8 grid on **live** (current-generator) meshes with the freeze
default ON. §1.1's table was measured 2026-08-21 at git `6a2d32a`, before 25
commits touched `mesh_to_tree.py` and before the generator swap.

| subject | target | hits/64 | **in shipped grid** | §1.1 said |
|---|---|---|---|---|
| **lizard** | 6 | **13** | **7** | **0 — "Class 3, unreachable"** |
| horse | 6 | 5 | 3 | not in the table |
| bird | 6 | 6 | **1** | **1, 0 inside — "we have never looked there"** |
| spider | 9 | 4 | 1 | not in the table |
| octopus | 9 | 4 | **1** | 5, 2 inside — "Class 2, window clamp" |

* **Class 3 is not merely empty, it is emphatically so** — the lizard's target
  is reachable **seven ways inside the shipped grid**.
* **Class 1 is void.** The bird's target *is* reachable in-grid. *"We have
  never looked there"* is false.
* **Class 2's mechanism survives, its cells do not.** 9 > `MAX_LEAVES = 8`
  still stops the octopus serving, but it now has an in-grid hit.

**⚠ Cite §1.1 only with its measurement date, its flag state and the generator
that produced it. Every classification in it is now void or re-cased.**

⚠ **An earlier run of this sweep was itself stale** and is recorded here as a
caution: it executed on a branch that predated the freeze default (PR #185), so
it measured the pre-flip world while reporting "the current default". Its
conclusions all held but its **cells were wrong** — the lizard's first in-grid
cell is 64/**0.25**, not 64/0.20, which under the real default yields 8 leaves.
The error surfaced only because a later probe read 8 where every other
measurement read 6. **A sweep is only valid for the flag state it ran under;
record that state beside the numbers.**

### And U5′'s premise is confirmed on five subjects at once

At each subject's first in-grid cell, arm A is the tree as served and arm C is
the deterministic mirror rule (see `probe_u5prime.py`):

| subject | cell | leaves | pairs the anatomy wants | **A** | **C** |
|---|---|---|---|---|---|
| lizard | 64/0.25 | 6 ✓ | 2 | 1 | 0 |
| bird | 128/0.30 | 6 ✓ | 2 | 1 | 0 |
| spider | 64/0.45 | 9 ✓ | 4 | 3 | 2 |
| **horse** | 64/0.20 | 6 ✓ | 2 | **0** | 1 |
| octopus | 128/0.30 | 9 ✓ | 4 | 2 | 0 |

**Five of five reach their authored leaf count and NOT ONE has the right pair
structure — and the null producer reaches it on none either.** The count is
solved everywhere; the shape is solved nowhere; and a mechanical mirror rule
does not close the gap. That is what makes the U5′ comparison worth running.

Note arm C beats arm A on the horse, 1 pair against 0. The shipped extractor
declares **no bilateral symmetry at all** in a quadruped.

### U5′ — the producer

```
G1  THE CONFOUND ISOLATION, and it is the whole bar.  Three arms per subject:
      A  mesh tree as served today
      B  mesh tree + LLM-supplied symmetric_pairs
      C  mesh tree + pairs from a NULL producer (a deterministic rule:
         pair leaves by mirrored position about the PCA axis)
    Arm C costs nothing and is the only thing standing between P3 and a
    headline that reads "the LLM found the pairing" when what happened is
    "any mirror rule finds the pairing".
    SHIP ONLY IF B BEATS BOTH A AND C.

G2  stub_flaps must not rise on any subject.  Terminal -- stub_flaps outranks
    scale in order_rank (K1) and proportion integrity in _serve_rank.
    Invented anatomy is never traded.

G3  LEAF COUNT MUST NOT MOVE AT ALL.  U5' supplies pairing on a tree whose
    count it does not touch.  Any leaf-count change means the unit exceeded
    its scope and the run is VOID, not merely failed.

G4  net >= +3 of 10 subjects gain a correct pair, where "correct" is judged
    against the mesh's own leaf positions, NOT against anatomy_reference.json
    (frozen, extraction-derived -- grading against it re-enters the closed
    loop).  Stated as a NET so a unit helping 4 and hurting 3 does not pass.

DO NOT SHIP U5' IF:  G1 fails, G2 hit, G3 violated, or G4 unmet.
```

### U7 — the critic

```
H1  RECALL >= 0.50 over a ledger of defects a human wrote down BEFORE the
    critic ran.

H2  NOT A STUCK BELL.  On >= 3 subjects with EMPTY ledgers the critic must
    report zero defects on at least 2 of 3.  A critic that always fires fails.

H3  BEATS THE TRIVIAL BASELINE by >= 0.20 F1 absolute, against the
    pre-registered null critic `always_report(missing_appendage, every leaf)`.
    A critic that reports a defect everywhere scores recall 1.0; that is the
    exact shape of "green for the wrong reason" and must be excluded
    ARITHMETICALLY before a single call is billed.

H4  NON-REDUNDANCY -- this is the bird's-leg claim, generalised.  At least ONE
    ledger defect the critic finds must NOT already be reported by a
    deterministic channel this repo ships.  Pre-registered exclusion list:
    stub_flaps > 0, pairs == 0, unlabelled_leaves > 0, count_error > 0,
    tree_contract errors, structural_prefilter rejection.
    If every defect it names is already on a deterministic channel, U7 is a
    very expensive grep -> DO NOT SHIP.

H5  BUDGET <= 120 billed calls.  Hard abort; report partial results rather
    than raising the budget mid-run.

H6  NO VETO.  A recorded DECISION, not a deferral: section 14's veto and its
    safety argument are mutually exclusive (server.py:4153 completes the
    search; the judge runs at :4165).  Additionally, extend
    vlm_judge._FORBIDDEN_KEYS to the SEMANTIC set (blocking, defects_block,
    advisory_veto, should_reject, veto_flag, gate_flag) and add a VALUE-shaped
    check -- exact-match key policing was measured bypassable.  Static assert:
    no U7 output reaches _serve_rank, order_rank, or any queue ordering.

DO NOT SHIP U7 IF:  H1, H2, H3 or H4 fails.
```

**Run U5′ first: it costs zero billed calls, and if G1 fails the producer story
is over.**

## 6. Out of scope

`MAX_LEAVES = 8`, which caps octopus and water bear at 8 against authored
targets of 9. It is a packer-capacity question with its own spec. U5′ cannot
answer it and must not claim to.
