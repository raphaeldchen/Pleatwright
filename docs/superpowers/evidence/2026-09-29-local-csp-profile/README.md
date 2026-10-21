# What is the 79.57%? Breaking dense `assign()`'s residual into named components

**Verdict (§4.3): `OPTIMISE IT`** — `free_vars_at` is **65.13%** of `lizard`'s
remainder (a **lower** bound, and `pick`'s 32.59% an **upper** one — only their sum
is clean; read §2.3 before quoting either figure) and per-node cost scales
**5.088x** from `lizard` to `octopus`. The row is `profile.json`'s
`provisional_row_pending_4_1_1`, and the `--cprofile` sweep lets it stand. **A ceiling is not a speedup** (§6), and §4.1(1)'s
named-function limb is satisfied **structurally, not measured** (§2 below).

Spec: `docs/superpowers/specs/2026-09-29-local-csp-profile-design.md`. Every `§`
refers to it. Artifacts: `profile.json` (the ladder), `cprofile-lizard.txt` (the
completeness sweep), `profile.py` (the instrument).

**Every figure below comes from `profile.json` or `cprofile-lizard.txt` unless it
is explicitly labelled as cited from another evidence directory, which is then
named.**

---

## 1. The question

A predecessor run on dense `lizard` at a 500,000-node budget apportioned its
runtime three ways. **Cited from `../2026-09-26-nogood-indexing/wtg-lizard-500k.json`,
not measured here:**

| reading | value | share |
|---|---|---|
| `total_secs` | 930.19 | 100% |
| `global_check_secs` (the layer check) | 178.15 | 19.15% |
| `hits_nogood_secs` (the no-good scan) | 11.88 | 1.28% |
| `remainder_secs` | **740.16** | **79.57%** |

The 1.28% is why the no-good indexing spec was withdrawn. The 79.57% is the
largest share by far, and it is **a residual, not a measurement**: that script
defines it as `total - global_check - hits_nogood` and glosses it "the local CSP
search itself". Nothing had ever measured inside it. This slice does, on all
eight box-pleat subjects, with named non-overlapping components and self-time
accounting (§3.2).

### 1.1 The goal is measurability on more than one subject, NOT convergence

`assign_budget` is a **node** budget. A cheaper node does not explore more of the
space; it explores the same nodes faster. Raising the budget is the only way to
explore more, and that is already a recorded negative. **Cited from
`../2026-09-24-dense-pleats/nogood-lizard-largebudget.json`, not measured here:**
at `assign_budget` 5,000,000 that run read **584 rejections**, a solver-variable
clause median of **204.5** (so the clause did not tighten), **8,865.1 s** elapsed,
and **no convergence**. Ten times the budget bought 5.17x the rejections and no
answer.

So nothing below may be read as a convergence fix. What a local-CSP speedup can
be justified as is **measurability**: `octopus` and `dog` have never produced a
dense labelling inside any cap this project has used, and every finding across
seven slices carries "this is `lizard`" as its stated limit.

### 1.2 Read this before any figure below: every row is a fixed 20,000-node WINDOW

**These are not completed searches, and they are not scaled-down copies of the
500k run.**

* **7 of 8 rows are windows cut off by the budget.** They read
  `assign_outcome: "AssignFail(kind='budget', site=20000)"` with `nodes: 20001`.
  Only `starfish` terminated, and it terminated by **accepting** an assignment at
  6,806 nodes.
* **The window is not a proportional sample of the 500k run.** On `lizard`,
  `global_check_secs / total_secs` here is **17.51 / 65.31 = 26.81%**, against
  **19.15%** in the 500k run (cited above). The layer check's *per-candidate* cost
  is comparable — 17.51 s over `calls.materialise: 10` is **1.751 s per complete
  candidate**, against the 500k run's cited `per_candidate_layer_secs` of
  **1.577 s** — so what differs is the mix, not the cost: ten candidates in
  20,001 nodes is a denser rejection rate than 113 in ~500,831 nodes (both cited
  figures from that directory — and **~500,831 is that file's
  `hits_nogood_calls`, used there as a PROXY for the node count, not a counted
  node total**; spec §1.2 explicitly declines to trust it, and counting nodes
  directly rather than inferring them is this slice's own §5.2 requirement).
  A 20,000-node prefix is its own regime, and every
  share below is a share **of that window**.

### 1.3 Three rows had NO rejections and NO complete candidate at all

`bird`, `octopus` and `dog` read `global_check_secs: 0.0`, `calls.materialise: 0`,
`calls.prefer: 20000` and `calls.hits_nogood` **exactly** `20000`. Production
`assign` calls `global_check(cand)` only after `pick()` returns `None`
(`mcp_harness/box_pleat/assign.py:1012-1015`: `pk = pick()`, then
`cand = materialise()` and `verdict = global_check(cand)` inside `if pk is None:`)
— i.e. only on a **complete** candidate. So those three searches never reached a
leaf inside the window. The other four budget-capped rows reached only **1 to 10**
(`lizard` 10, `frog`/`horse`/`guinea_pig` 1 each).

**Consequences, stated rather than buried:**

* The **CEGAR regime was effectively not exercised** on this ladder. Nothing here
  speaks to the no-good scan at 500,000 nodes, to clause quality, or to what
  rejection handling costs at depth. On the seven budget-capped rows
  `hits_nogood` reads 0.0093–0.1087 s of self-time on 20,000–20,130 calls
  (`starfish`: 0.0064 s on 7,133) — consistent with the cited 1.28%, but measured
  over a window with almost no no-goods in it.
* **What it buys:** `free_vars_at`'s dominance holds in **both** regimes —
  **65.13%** on `lizard`, which had 10 rejections, and **65.17%** on `octopus`,
  which had none. The finding is therefore **not an artefact of rejection
  handling**, which strengthens it.

---

## 2. The §4.1 completeness gate

**Both limbs hold, so the §4.3 row may be claimed — but they are not the same
kind of evidence, and the README must not pretend otherwise.**

### 2.1 §4.1(1), the `cProfile` sweep: satisfied STRUCTURALLY, not measured

`cprofile-lizard.txt` records `§4.1(1) OUTCOME: no uncovered frame found`. **That
is not a measurement of completeness.** The instrument prints its own scope at the
head of that file, and it is quoted here verbatim rather than paraphrased:

> `§4.1(1) SCOPE:` `COVERED` names every function defined in the patched module
> (34/34, `ast`-counted) and the file filter excludes every other module and all
> C builtins, so the named-function limb is satisfied STRUCTURALLY, not measured
> -- an empty list here is not evidence that a sweep looked for a named gap and
> found none. What this sweep can still flag, and all it can flag, is an
> ANONYMOUS frame (`<genexpr>`, `<lambda>`) owned by `assign`'s own loop or by
> module level. KNOWN BLIND SPOT: on Python 3.14 PEP 709 inlines list/dict/set
> comprehensions, so §4.1(1)'s own example -- 'a comprehension nobody wrapped' --
> emits no cProfile frame and cannot be flagged at all. §4.1(2)'s sum-check is
> the live NUMERICAL completeness check; this limb is the structural one.

So all three of §4.1(1)'s own worked examples are out of reach of the sweep that
is supposed to catch them: the comprehension is inlined away by PEP 709 and emits
no profiler frame; `_deg` is pre-declared in `COVERED`; and a builtin or
foreign-module `__hash__` is excluded by the file filter. **Nowhere may this
README say the sweep "measured completeness".**

Two things keep this honest rather than hollow. First, every category-(B)
justification in `COVERED` — a function reached from `assign` but sitting inside
an interval some accumulator already measures — was independently verified by
call-site analysis before the run, so the narrowing costs no known detection
today: the point is honest reporting, not a suspected gap. Second, `COVERED` was
written **before** any run, which is what distinguishes it from adding names to
make a failing gate pass.

### 2.2 §4.1(2), the sum-check: the live numerical limb, and it carries the weight

This is the limb that could have failed on the data and did not. Components are
summed over `REMAINDER_COMPONENTS` (all nine except `hits_nogood`, which the
remainder's own definition subtracts out) and compared against
`remainder_secs_exact`, not the 2-dp `remainder_secs`. Tolerance `gate_sum_tol`
is 0.05.

| subject | `remainder_secs_exact` | sum over `REMAINDER_COMPONENTS` | sum / remainder | `sum_check_passed` | `gate_failures` |
|---|---|---|---|---|---|
| `starfish` | 0.28961 | 0.2858 | 98.686% | `true` | `[]` |
| `lizard` | 47.69286 | 47.6578 | 99.926% | `true` | `[]` |
| `frog` | 49.50781 | 49.4911 | 99.966% | `true` | `[]` |
| `horse` | 78.62060 | 78.5973 | 99.970% | `true` | `[]` |
| `bird` | 109.54744 | 109.5229 | 99.978% | `true` | `[]` |
| `guinea_pig` | 145.41922 | 145.3981 | 99.985% | `true` | `[]` |
| `octopus` | 242.63626 | 242.6049 | 99.987% | `true` | `[]` |
| `dog` | 193.45304 | 193.4264 | 99.986% | `true` | `[]` |

The largest shortfall is `starfish`'s 1.31% and every other row is under 0.08% —
comfortably inside the 5% tolerance. **`sum_check_passed: true` is the sum limb
only, never §4.1 itself**; each row's `gate_scope` field says so in the artifact,
and the key is deliberately not named `gate_passed`.

### 2.3 The wrapper-overhead caveat, which binds harder here than in any previous slice

Each accumulator is `_t0 = _perf()` / `try: return _p_<name>(...)` / `finally:
_PROBE[...] += _perf() - _t0`. **Both `_perf()` calls and both dict updates fall
outside the interval that invocation records**, so their cost lands in the
**enclosing** block's self-time. `free_vars_at` is reached from `eligible` inside
`pick`'s measured interval and is entered **20,858.0 times per node on `octopus`**
(`calls.free_vars_at` 417,181,743 / `nodes` 20,001).

Therefore, on every budget-capped row:

* **`pick`'s ~34% is an UPPER bound** — it absorbs `free_vars_at`'s per-call
  wrapper overhead.
* **`free_vars_at`'s ~65% is a LOWER bound.**
* **The pick/`free_vars_at` split is contaminated. Their SUM is not** — the
  overhead sits inside `pick`'s interval either way, and `pick`'s self-time is its
  own interval minus its measured children, so the pair's total is unaffected by
  where the boundary falls.

**The two bounds are ONE-DIRECTIONAL, which makes §4.3's row-1 SELECTION robust
against exactly this contamination.** The overhead can only move time *from*
`free_vars_at` *into* `pick`, never the other way, so `free_vars_at`'s share is a
floor and `pick`'s a ceiling. On every budget-capped row the floor
(64.76%–65.26%) already exceeds the ceiling (32.59%–34.05%) by about 2x, and no
redistribution of the wrapper cost can close a gap that the bounds' own directions
forbid closing. **Which component is top is therefore not an artefact of the
instrument**, even though the exact 65.13% / 32.59% split is.

**One consequence stated rather than left implied: the ABSOLUTE per-node figures
are instrument-inflated.** `remainder_secs` itself contains the wrappers' own
`_perf()` and dict-update cost across the 84.75M–417.18M `free_vars_at` calls each
subject makes, so `lizard`'s **2.3845 ms/node** (§3.1) is an instrumented cost and
**must not be quoted as a production timing**. It weakens nothing claimed here, for
two reasons. The overhead sits in **both** the numerator and the denominator of a
`share_of_remainder` — charged to `pick`'s self-time, and inside `remainder_secs`
— so the dominant pair's shares are **near-invariant** to it; not invariant,
because removing it would shrink the remainder and so raise the sub-1% components'
shares somewhat, and none of those is anywhere near `no_lever_below`'s 25%. And it
is proportional to call count, so **`scaling` is robust**: it is a ratio of two
per-node costs whose per-call overhead is the same size.

**The headline is therefore framed on the sum: `pick` + `free_vars_at` together
are 97.72–99.12% of the remainder on the seven budget-capped rows.** For scale,
`cprofile-lizard.txt` charges **9.527 s** of `tottime` to
`{built-in method time.perf_counter}` across 169,939,132 calls in its 135.779 s
sweep — **profiler-distorted seconds, not a share of anything** (§6).

---

## 3. The component table

`self_secs` and `calls` are **measured**. `share_of_remainder`
(= `self_secs / remainder_secs`) and `whole_run_ceiling`
(= `1 / (1 - self_secs / total_secs)`) are **derived**, and they are **the same
measurement rescaled, so neither corroborates the other** (§4.2). `hits_nogood`
has no `share_of_remainder` because the remainder's definition subtracts it out.

### 3.1 Shape of each run

| subject | `N` | `nodes` | `assign_outcome` | `total_secs` | `global_check_secs` | share of total | `remainder_secs_exact` | `calls.materialise` | `per_node_ms` |
|---|---|---|---|---|---|---|---|---|---|
| `starfish` | 4 | 6806 | accepted | 0.43 | 0.13 | 30.23% | 0.28961 | 6 | 0.0426 |
| `lizard` | 34 | 20001 | budget @ 20000 | 65.31 | 17.51 | 26.81% | 47.69286 | 10 | 2.3845 |
| `frog` | 38 | 20001 | budget @ 20000 | 56.80 | 7.28 | 12.82% | 49.50781 | 1 | 2.4753 |
| `horse` | 46 | 20001 | budget @ 20000 | 96.06 | 17.42 | 18.13% | 78.62060 | 1 | 3.9308 |
| `bird` | 54 | 20001 | budget @ 20000 | 109.56 | 0.00 | 0.00% | 109.54744 | 0 | 5.4771 |
| `guinea_pig` | 64 | 20001 | budget @ 20000 | 166.54 | 21.11 | 12.68% | 145.41922 | 1 | 7.2706 |
| `octopus` | 74 | 20001 | budget @ 20000 | 242.65 | 0.00 | 0.00% | 242.63626 | 0 | 12.1312 |
| `dog` | 74 | 20001 | budget @ 20000 | 193.46 | 0.00 | 0.00% | 193.45304 | 0 | 9.6722 |

`per_node_ms` is `remainder_secs_exact / nodes`, so it excludes `global_check`.
`share of total` is `global_check_secs / total_secs`, derived, and it is printed
here because **§4 below cannot be read without it.**

### 3.2 Per subject

**`starfish`** — `remainder_secs_exact` 0.28961 s, `total_secs` 0.43 s, `nodes` 6806, `global_check_secs` 0.13 s

| component | `self_secs` (measured) | `calls` (measured) | `share_of_remainder` (derived) | `whole_run_ceiling` (derived) |
|---|---|---|---|---|
| `setup` | 0.0013 | 0 | 0.46% | 1.003x |
| `pick` | 0.0377 | 6,806 | 13.02% | 1.096x |
| `now_open` | 0.0049 | 6,806 | 1.71% | 1.012x |
| `free_vars_at` | 0.0765 | 194,688 | 26.40% | 1.216x |
| `violation` | 0.1468 | 30,606 | **50.68%** | 1.519x |
| `prefer` | 0.0063 | 6,800 | 2.19% | 1.015x |
| `materialise` | 0.0001 | 6 | 0.02% | 1.000x |
| `retry` | 0.0122 | 6,805 | 4.21% | 1.029x |
| `hits_nogood` | 0.0064 | 7,133 | n/a (not part of the remainder) | 1.015x |

**`lizard`** — `remainder_secs_exact` 47.69286 s, `total_secs` 65.31 s, `nodes` 20001, `global_check_secs` 17.51 s

| component | `self_secs` (measured) | `calls` (measured) | `share_of_remainder` (derived) | `whole_run_ceiling` (derived) |
|---|---|---|---|---|
| `setup` | 0.0880 | 0 | 0.18% | 1.001x |
| `pick` | 15.5427 | 20,000 | 32.59% | 1.312x |
| `now_open` | 0.1521 | 20,000 | 0.32% | 1.002x |
| `free_vars_at` | 31.0628 | 84,754,358 | **65.13%** | 1.907x |
| `violation` | 0.6977 | 110,639 | 1.46% | 1.011x |
| `prefer` | 0.0353 | 19,990 | 0.07% | 1.001x |
| `materialise` | 0.0017 | 10 | 0.00% | 1.000x |
| `retry` | 0.0775 | 20,000 | 0.16% | 1.001x |
| `hits_nogood` | 0.1087 | 20,064 | n/a (not part of the remainder) | 1.002x |

**`frog`** — `remainder_secs_exact` 49.50781 s, `total_secs` 56.80 s, `nodes` 20001, `global_check_secs` 7.28 s

| component | `self_secs` (measured) | `calls` (measured) | `share_of_remainder` (derived) | `whole_run_ceiling` (derived) |
|---|---|---|---|---|
| `setup` | 0.1236 | 0 | 0.25% | 1.002x |
| `pick` | 16.4126 | 20,000 | 33.15% | 1.406x |
| `now_open` | 0.1570 | 20,000 | 0.32% | 1.003x |
| `free_vars_at` | 32.2145 | 106,309,978 | **65.07%** | 2.310x |
| `violation` | 0.5122 | 111,805 | 1.03% | 1.009x |
| `prefer` | 0.0197 | 19,999 | 0.04% | 1.000x |
| `materialise` | 0.0002 | 1 | 0.00% | 1.000x |
| `retry` | 0.0513 | 20,000 | 0.10% | 1.001x |
| `hits_nogood` | 0.0093 | 20,081 | n/a (not part of the remainder) | 1.000x |

**`horse`** — `remainder_secs_exact` 78.62060 s, `total_secs` 96.06 s, `nodes` 20001, `global_check_secs` 17.42 s

| component | `self_secs` (measured) | `calls` (measured) | `share_of_remainder` (derived) | `whole_run_ceiling` (derived) |
|---|---|---|---|---|
| `setup` | 0.1769 | 0 | 0.22% | 1.002x |
| `pick` | 26.4498 | 20,000 | 33.64% | 1.380x |
| `now_open` | 0.2867 | 20,000 | 0.36% | 1.003x |
| `free_vars_at` | 51.0382 | 156,928,380 | **64.92%** | 2.134x |
| `violation` | 0.5610 | 113,481 | 0.71% | 1.006x |
| `prefer` | 0.0264 | 19,999 | 0.03% | 1.000x |
| `materialise` | 0.0003 | 1 | 0.00% | 1.000x |
| `retry` | 0.0580 | 20,000 | 0.07% | 1.001x |
| `hits_nogood` | 0.0161 | 20,130 | n/a (not part of the remainder) | 1.000x |

**`bird`** — `remainder_secs_exact` 109.54744 s, `total_secs` 109.56 s, `nodes` 20001, `global_check_secs` 0.00 s

| component | `self_secs` (measured) | `calls` (measured) | `share_of_remainder` (derived) | `whole_run_ceiling` (derived) |
|---|---|---|---|---|
| `setup` | 0.2459 | 0 | 0.22% | 1.002x |
| `pick` | 37.2460 | 20,000 | 34.00% | 1.515x |
| `now_open` | 0.3628 | 20,000 | 0.33% | 1.003x |
| `free_vars_at` | 70.9417 | 220,630,779 | **64.76%** | 2.837x |
| `violation` | 0.6318 | 118,787 | 0.58% | 1.006x |
| `prefer` | 0.0307 | 20,000 | 0.03% | 1.000x |
| `materialise` | 0.0000 | 0 | 0.00% | 1.000x |
| `retry` | 0.0640 | 20,000 | 0.06% | 1.001x |
| `hits_nogood` | 0.0102 | 20,000 | n/a (not part of the remainder) | 1.000x |

**`guinea_pig`** — `remainder_secs_exact` 145.41922 s, `total_secs` 166.54 s, `nodes` 20001, `global_check_secs` 21.11 s

| component | `self_secs` (measured) | `calls` (measured) | `share_of_remainder` (derived) | `whole_run_ceiling` (derived) |
|---|---|---|---|---|
| `setup` | 0.4094 | 0 | 0.28% | 1.002x |
| `pick` | 49.1342 | 20,000 | 33.79% | 1.419x |
| `now_open` | 0.2787 | 20,000 | 0.19% | 1.002x |
| `free_vars_at` | 94.9058 | 312,583,881 | **65.26%** | 2.325x |
| `violation` | 0.5811 | 122,071 | 0.40% | 1.004x |
| `prefer` | 0.0280 | 19,999 | 0.02% | 1.000x |
| `materialise` | 0.0007 | 1 | 0.00% | 1.000x |
| `retry` | 0.0602 | 20,000 | 0.04% | 1.000x |
| `hits_nogood` | 0.0095 | 20,006 | n/a (not part of the remainder) | 1.000x |

**`octopus`** — `remainder_secs_exact` 242.63626 s, `total_secs` 242.65 s, `nodes` 20001, `global_check_secs` 0.00 s

| component | `self_secs` (measured) | `calls` (measured) | `share_of_remainder` (derived) | `whole_run_ceiling` (derived) |
|---|---|---|---|---|
| `setup` | 0.5940 | 0 | 0.24% | 1.002x |
| `pick` | 82.3652 | 20,000 | 33.95% | 1.514x |
| `now_open` | 0.5810 | 20,000 | 0.24% | 1.002x |
| `free_vars_at` | 158.1358 | 417,181,743 | **65.17%** | 2.871x |
| `violation` | 0.8148 | 127,245 | 0.34% | 1.003x |
| `prefer` | 0.0365 | 20,000 | 0.02% | 1.000x |
| `materialise` | 0.0000 | 0 | 0.00% | 1.000x |
| `retry` | 0.0776 | 20,000 | 0.03% | 1.000x |
| `hits_nogood` | 0.0103 | 20,000 | n/a (not part of the remainder) | 1.000x |

**`dog`** — `remainder_secs_exact` 193.45304 s, `total_secs` 193.46 s, `nodes` 20001, `global_check_secs` 0.00 s

| component | `self_secs` (measured) | `calls` (measured) | `share_of_remainder` (derived) | `whole_run_ceiling` (derived) |
|---|---|---|---|---|
| `setup` | 0.6200 | 0 | 0.32% | 1.003x |
| `pick` | 65.8793 | 20,000 | 34.05% | 1.516x |
| `now_open` | 0.5247 | 20,000 | 0.27% | 1.003x |
| `free_vars_at` | 125.6725 | 406,614,858 | **64.96%** | 2.854x |
| `violation` | 0.6367 | 131,144 | 0.33% | 1.003x |
| `prefer` | 0.0247 | 20,000 | 0.01% | 1.000x |
| `materialise` | 0.0000 | 0 | 0.00% | 1.000x |
| `retry` | 0.0685 | 20,000 | 0.04% | 1.000x |
| `hits_nogood` | 0.0103 | 20,000 | n/a (not part of the remainder) | 1.000x |

### 3.3 What the table says, and what it kills

* **`free_vars_at` is the top component on 7 of 8 subjects**, in a band of
  **64.76%–65.26%** of the remainder. `starfish` (N=4) is the exception; §7.
* **`pick`'s self-time is a flat 32.59%–34.05%** on the seven budget-capped rows.
  Read with §2.3, the two together are **97.72%–99.12%** and the split between
  them is the contaminated part.
* **`setup` is 0.18%–0.32%** on the budget-capped rows (0.46% on `starfish`), so
  §4.3's row 3 — "the remainder is mostly one-time setup" — is **decisively**
  refuted. That matters because row 3 is checked first.
* **Two of the spec's own named suspects are refuted.** §3.1 suspected the
  `now_open` scan over `pleat_pref`'s ~4,488 entries: it reads **0.19%–0.36%**.
  It suspected `violation`'s from-scratch `ring`/`free`/`folded` rebuild: it reads
  **0.33%–1.46%** on every budget-capped row. The AC-3/AC-4 line of prior art
  (§2 of the spec) is aimed at the wrong function.
* `prefer`, `materialise` and `retry` are each ≤0.16% of the remainder on the
  budget-capped rows.

### 3.4 The mechanism, read from production

`mcp_harness/box_pleat/assign.py`, verified for this README:

* **`free_vars_at` (`:856-861`)** builds a set comprehension over `inc[v]` and
  then **sorts** it: `return sorted(fv, key=lambda var: (var not in domain, var))`.
* **`eligible` (`:865-877`)** is `free_vars_at(v)` plus a list filter, so it calls
  `free_vars_at` exactly once per call. It is the only caller inside the search.
* **`pick` (`:881-924`)** has a **sticky-vertex fast path** — `v = current[0]`
  (`:908`), one `eligible(v)` call — and, when that yields nothing, a **full
  rescan**: `for v in interior:` (`:914`), one `eligible(v)` → one
  `free_vars_at(v)` per interior vertex, picking the most-constrained by
  `key = (fv[0] not in domain, len(fv))`.

**The call counts say the fast path is buying essentially nothing.** A node that
takes the fast path costs exactly **one** `free_vars_at` call; a node that
rescans costs `1 + |interior|`. Measured `calls.free_vars_at / nodes`:

| subject | `calls.free_vars_at` | `nodes` | calls per node |
|---|---|---|---|
| `starfish` | 194,688 | 6,806 | 28.6 |
| `lizard` | 84,754,358 | 20,001 | 4,237.5 |
| `octopus` | 417,181,743 | 20,001 | 20,858.0 |

At most one call per node can be the fast path's, so the fast path accounts for at
most `nodes / calls.free_vars_at` = **0.024% of `lizard`'s** `free_vars_at` calls
and **0.005% of `octopus`'s**. **Whether it hits or not, it cannot save a
measurable fraction of this cost** — ~100% of the calls come from the rescan loop.

**The honest limit on that reading:** the calls-per-`pick` figure is the product
`1 + f·|interior|`, where `f` is the fraction of `pick` calls that rescan, and
**the artifact records neither `|interior|` nor the search depth**, so it fixes the
product and not the factors. With `f ≤ 1` it bounds `|interior|` from below, and
the arithmetic is printed here because spec §11 quotes the same bound:

| subject | `calls.free_vars_at` | `calls.pick` | ratio | less the sticky call | interior ≥ |
|---|---|---|---|---|---|
| `lizard` | 84,754,358 | 20,000 | 4,237.7179 | 4,236.7179 | **4,237** |
| `octopus` | 417,181,743 | 20,000 | 20,859.0872 | 20,858.0872 | **20,859** |

`calls.pick` is the denominator the bound calls for — it is a per-`pick`-call
bound, and `pick` is entered 20,000 times against `nodes` 20,001 — and the count
of interior vertices is an integer, so each row rounds **up**. Dividing instead by
`nodes`, as the calls-per-node column above does because that column is a per-node
*rate*, gives the same 4,237 on `lizard` and the looser 20,858 on `octopus`; all
four are sound, and this pair is the tight one. Either way the conclusion about the
fast path's share of the calls stands, because it does not depend on the split.

> **A `cProfile` CALL-COUNT ratio, NOT a share of time — and a hand-off, not a
> measurement of this slice.** §6 and §4.1(1) bar `cProfile` numbers from appearing
> as **shares**, because what a deterministic profiler distorts is *time*. It does
> not distort *counts*, and what follows is a ratio of two counts whose denominator
> is independently committed in `profile.json`.
>
> `sorted(fv, key=lambda …)` (`:861`) applies its key **once per element**, so the
> key lambda's call count is `Σ|fv|` over every `free_vars_at` call.
> `cprofile-lizard.txt` reads the patched copy's key lambda
> (`_assign_profiled.py:878`) at **8,140,548** calls against that copy's
> `free_vars_at` (`:865`) at **84,754,358** calls, so
> `8,140,548 / 84,754,358 = 0.09605` elements per call. A non-empty `fv` has at
> least one element, so **at most 9.61% of calls can return a non-empty list, and
> therefore at least 90.39% return an empty one.**
>
> Three facts make that trustworthy. **(1)** The sweep's `free_vars_at` count is
> **identical** to `profile.json`'s `calls.free_vars_at` for `lizard`
> (84,754,358), which independently shows the sweep's *counts* are undistorted and
> that it profiled the same search. **(2)** It **replicates inside the same sweep on
> the unpatched module**: `assign.py:861(<lambda>)` 2,252,882 against
> `assign.py:856(free_vars_at)` 24,847,987 = `0.09067`, i.e. ≥ 90.93% empty — the
> sparse-phase search shows the same regime. **(3)** Only the numerator is
> sweep-only; the denominator is committed. (As a consistency check, the two copies
> together are 109,602,345 of the sweep's 110,543,704 `builtins.sorted` calls —
> 99.15% — so `sorted` in this run is essentially all `free_vars_at`.)
>
> **What it licenses:** most rescan calls build a set comprehension over one
> vertex's incident pieces, find nothing unbound, and then sort an empty list. That
> is the direct case for §6's incremental-counter remedy — a maintained count of
> unbound incident variables answers "is this vertex free at all?" without building
> or sorting anything. **What it is not:** this slice's measurement. It is a
> call-count ratio read out of a completeness sweep, it is expressed in no time
> units at all, and it is **handed off**: the follow-on spec must re-measure it with
> a real counter rather than carry this ratio forward.

---

## 4. The Amdahl reading

`whole_run_ceiling = 1 / (1 - self_secs / total_secs)` is what removing the
component **entirely** would buy on the whole run. **It is not a speedup.** No
real optimisation removes a component entirely, and §6 says so; a rewritten
`free_vars_at` that is twice as fast buys a fraction of the figures below, not the
figures below.

**`free_vars_at`'s ceiling must be read beside its row's `global_check` share, and
the spread across rows is NOT a size trend.** `total_secs` includes
`global_check_secs`, so a row where `global_check_secs` is 0.00 has nothing
diluting the share and reports a mechanically higher ceiling:

| subject | `global_check_secs` share of total | `free_vars_at` ceiling |
|---|---|---|
| `starfish` | 30.23% | 1.216x |
| `lizard` | 26.81% | 1.907x |
| `horse` | 18.13% | 2.134x |
| `frog` | 12.82% | 2.310x |
| `guinea_pig` | 12.68% | 2.325x |
| `bird` | **0.00%** | 2.837x |
| `dog` | **0.00%** | 2.854x |
| `octopus` | **0.00%** | 2.871x |

The three highest ceilings are **exactly** the three rows that had no rejections
at all (§1.3). Read as a size trend this table would claim "bigger subjects offer
more headroom", and **the data does not support that**: the ordering is the
`global_check` ordering, not the `N` ordering. **Confine ceiling comparisons to
the five rows that had rejections**, where `lizard`'s **1.907x** is the reference
figure.

**The pair, which §2.3 says is the uncontaminated quantity**, on the rows with
rejections only. Both right-hand columns are **derived here** from the artifact's
`self_secs`, `remainder_secs_exact` and `total_secs` by the same two formulas
above — the pair's ceiling is `1 / (1 - (pick + free_vars_at) / total_secs)`, and
it is not a field in `profile.json`:

| subject | `global_check_secs` | `pick` + `free_vars_at` `self_secs` | combined share of remainder | combined ceiling |
|---|---|---|---|---|
| `starfish` | 0.13 | 0.1142 | 39.43% | 1.362x |
| `lizard` | 17.51 | 46.6055 | **97.72%** | **3.492x** |
| `frog` | 7.28 | 48.6271 | 98.22% | 6.950x |
| `horse` | 17.42 | 77.4880 | 98.56% | 5.172x |
| `guinea_pig` | 21.11 | 144.0400 | 99.05% | 7.402x |

`bird`, `dog` and `octopus` are **omitted deliberately**: with
`global_check_secs = 0.00` their remainder is ~100% of total and the combined
ceiling diverges (it reads 79.837x, 101.384x and 112.913x). Those numbers are
arithmetic about a zero denominator, not headroom, and printing them as headroom
would be the §4.2 error this spec exists to prevent — a share of a share presented
as a share of the whole.

So the defensible Amdahl statement is: **on `lizard`, the only subject with a
dense convergence history, the top component prices at 1.907x and the
uncontaminated pair at 3.492x, against the remainder's own cap of 3.707x**
(= `1 / (1 - 47.69286/65.31)`). Everything else in the local CSP is worth less
than 3% of the remainder combined.

---

## 5. The per-node ladder, and §4.4's prediction

§4.4 set two hypotheses that predict **opposite shapes**:

* **`pick`-dominated** → per-node cost tracks **candidate count**.
* **`violation`-dominated** → per-node cost tracks vertex degree, which barely
  grows with `N`, so the curve should be **nearly flat**.

**The data has the `pick`-dominated shape, unambiguously.** `per_node_ms`
(= `remainder_secs_exact / nodes`, so `global_check` is excluded and the
zero-rejection rows do not distort it):

| subject | `N` | `per_node_ms` | vs `lizard` | `calls.free_vars_at` / `nodes` | vs `lizard` |
|---|---|---|---|---|---|
| `starfish` | 4 | 0.0426 | 0.018x | 28.6 | 0.007x |
| `lizard` | 34 | 2.3845 | 1.000x | 4,237.5 | 1.000x |
| `frog` | 38 | 2.4753 | 1.038x | 5,315.2 | 1.254x |
| `horse` | 46 | 3.9308 | 1.648x | 7,846.0 | 1.852x |
| `bird` | 54 | 5.4771 | 2.297x | 11,031.0 | 2.603x |
| `guinea_pig` | 64 | 7.2706 | 3.049x | 15,628.4 | 3.688x |
| `octopus` | 74 | 12.1312 | **5.088x** | 20,858.0 | **4.922x** |
| `dog` | 74 | 9.6722 | 4.056x | 20,329.7 | 4.798x |

`profile.json`'s `scaling` field is **5.088** — `octopus` per-node over `lizard`
per-node, recomputed here as `12.1312 / 2.3845 = 5.0875`. A flat curve would read
≈1.0x. It reads 5.088x, and `violation` is 0.34% of `octopus`'s remainder.

**Against candidate count.** The spec's candidate counts — `pleat_pref` entries,
**4,488 on `lizard` and 21,704 on `octopus`, a 4.8x ratio** — are **cited from
spec §3.1/§4.4 and were not re-measured by this run**; the artifact records no
variable count for any subject, so this axis exists for `lizard` and `octopus`
only. On those two the prediction holds well: 4.8x against a measured **5.088x**,
and `2.3845 × 4.8 = 11.4456` ms against a measured **12.1312** ms, 6.0% high.
§4.4's absolute figure of "roughly 7 ms" does **not** hold, and the reason is its
base: it multiplied 4.8 by **1.48 ms/node**, itself derived in spec §1.2 from the
500k run (`remainder_secs / hits_nogood_calls`, a **proxy** denominator that the
spec explicitly declined to trust), whereas this run counted nodes directly and
reads 2.3845 ms/node of remainder on a 20,000-node window.

**Two qualifications on the 5.088x, both required.**

1. **It is a per-node cost measured across differing search regimes.** `lizard`'s
   window contains 10 rejections and `octopus`'s contains none (§1.3), and the
   artifact records **no variable count and no search depth**, so the depth mix
   inside each window is unverifiable from it. The figure is "what a node costs in
   the first 20,000 nodes", not "what a node costs in a converging search".
2. **Per-node cost tracks the `free_vars_at` call rate, but not proportionally.**
   The ratio of the ms-ratio to the calls-ratio runs 0.83–1.03 across the six
   budget-capped subjects above `lizard`. The clearest gap is `dog` and `octopus`:
   **identical `N` = 74**, call rates within 2.6% of each other (20,329.7 vs
   20,858.0), yet per-node costs of **9.6722** and **12.1312** ms — a 1.254x
   difference that nothing in this artifact explains.

---

## 6. The verdict (§4.3)

**`profile.json` records the row as `provisional_row_pending_4_1_1`:**

```
"row": "OPTIMISE IT",
"why": "free_vars_at dominates and per-node cost scales 5.09x",
"subject": "lizard", "top_component": "free_vars_at",
"top_share_of_remainder": 0.6513, "setup_share_of_remainder": 0.0018,
"scaling": 5.088
```

Its `scope` field reads, in part: *"PROVISIONAL. This is `verdict()` applied to
`lizard`'s row under §4.3, computed by the self-tested function and NOT to be
re-derived by hand. It is NOT the final row: §4.1(1)'s completeness limb is not
evaluated by this invocation … §4.1 forbids claiming a row until both limbs
hold."* The run's top-level `verdict` key reads `"NO ROW CLAIMED: §4.1(2) passed
on every ok row; §4.1(1) needs the --cprofile sweep. See
provisional_row_pending_4_1_1."`

**That sweep has since run, and its outcome lets the row stand.**
`cprofile-lizard.txt` reports `§4.1(1) OUTCOME: no uncovered frame found`, so both
limbs of §4.1 hold — §2.1's limb structurally, §2.2's numerically. The row is
therefore **`OPTIMISE IT`**, taken from the artifact and not re-derived by hand:
`main()` calls the self-tested `verdict()` and records its answer with its own
`why` string, and a hand-applied table beside a self-tested function is how a
wrong row gets published.

**Why this row and not its neighbours** — the ordering §4.3 fixes, row 3 first
because `setup` is one-time and a run whose residual were dominated by setup could
satisfy row 1 while licensing per-node optimisation of a cost that does not recur
per node:

* **Row 3 (setup ≥50% → DIFFERENT FIX): not reached.**
  `setup_share_of_remainder` is **0.0018** on `lizard`, and ≤0.0046 on every row.
* **Row 1 (top ≥50% AND `octopus` per-node ≥2x `lizard`): reached.**
  `top_share_of_remainder` **0.6513** ≥ `TOP_DOMINATES` 0.50, and `scaling`
  **5.088** ≥ `SCALES` 2.0.
* **Row 2 (top ≥50% BUT per-node flat, `octopus` ≤1.2x): not reached.** 5.088 is
  4.24x `FLAT_AT_OR_BELOW`'s 1.2. Nor is this in §4.3's deliberate
  no-commitment band between 1.2x and 2.0x.
* **Row 4 (no per-node component ≥25% → NO SINGLE LEVER): not reached.**
  `free_vars_at` alone is 65.13%.

**What the row licenses, and what it does not.** §4.5's target is a dense
labelling on a subject that currently cannot produce one, inside a **1-hour** cap;
row 1 **licenses attempting that and does not promise it**. §4.2's ceiling says
how close the best case gets, and §4 above prices it: **1.907x** for
`free_vars_at` alone on `lizard`, **3.492x** for the uncontaminated
`pick` + `free_vars_at` pair, against the remainder's own cap of **3.707x**.

**The remedy the measurement makes adoptable.** §2 of the spec named CP practice
as "named, not adopted", and a measurement is what makes it adoptable: the
standard fix for a from-scratch most-constrained-variable scan is **incremental
maintenance** — per-vertex counters of unbound incident variables, updated on bind
and unbind, with a priority structure over vertices — in the AC-3 → AC-4/AC-6 and
activity-based-ordering line the spec cites. §3.4's reading is what points it at
`pick`'s rescan rather than at `violation`. **That work needs its own spec; it is
not licensed to change anything by this document, and no optimisation is in scope
here (§7).**

---

## 7. `starfish` is the lone exception, on every axis

It is reported as its own regime and **not averaged with the rest**:

* **`N` = 4**, an order of magnitude below the next subject.
* **The only subject that terminated**, and it terminated by **accepting** an
  assignment (`assign_outcome` begins `Assignment(pieces=...`) at **6,806**
  nodes, not by exhausting the budget.
* **`violation` is its top component at 50.68%**, the only row where
  `free_vars_at` is not on top (26.40%).
* **`calls.free_vars_at / nodes` is 28.6**, against 4,237.5–20,858.0 on every
  other subject.
* **`per_node_ms` 0.0426** — 56x below `lizard`.
* Its sum-check shortfall, 1.31%, is also the largest of the eight, though still
  well inside the 5% tolerance.

It is the `violation`-dominated shape §4.4 predicted for the flat case, occurring
at the one size where the rescan is cheap. It is a smoke row, not a data point on
the ladder.

---

## 8. What this cannot say (§6)

* **Nothing here addresses convergence.** The budget is in nodes, 10x it is a
  recorded negative (§1.1), and a cheaper node explores the same nodes faster. The
  row-1 verdict licenses optimisation aimed at **measurability**, never at
  convergence.
* **A ceiling is not a speedup.** §4's figures are what removing a component
  *entirely* would buy. No real optimisation removes a component entirely.
* **`lizard` remains the only subject with a dense convergence history.** This
  ladder measures per-node cost on eight subjects, which is a statement about
  cost, not about what those searches would do at a large budget.
* **`cProfile` is a completeness check, not a measurement.** No cProfile figure is
  presented as a **share of time** anywhere above. Two are quoted in **seconds**
  and labelled profiler-distorted — 135.779 s for the sweep, and 9.527 s of
  `tottime` in `time.perf_counter`. One more is quoted as a **call-count ratio**
  (§3.4's fenced block: 8,140,548 key-lambda calls over 84,754,358
  `free_vars_at` calls), which is a ratio of counts rather than of time, is
  labelled as such, is cross-checked against `profile.json`'s own
  `calls.free_vars_at`, and is explicitly **handed off** to the follow-on to
  re-measure with a real counter rather than treated as this slice's result. The
  reason time shares are barred is visible in the artifact: the sweep's frame for the patched `assign`
  reads **123.082 s** cumulative on `lizard` where the ladder's `total_secs` for
  the same subject is **65.31 s**, a 1.88x distortion on the one function whose
  shares this README is about.
* **Every row is a 20,000-node window, not a search** (§1.2), and three of the
  eight contain no rejection at all (§1.3). Nothing here speaks to the CEGAR
  regime, the no-good scan at 500,000 nodes, or clause quality.
* **The pick/`free_vars_at` split is contaminated by wrapper overhead** (§2.3);
  only their sum is clean.
* **No variable count and no search depth are recorded**, so `|interior|`, the
  rescan frequency and the depth mix are all unverifiable from this artifact.

---

## 9. Subjects that produced no row

**None.** The corpus is **8 subjects** — `starfish`, `lizard`, `frog`, `horse`,
`bird`, `guinea_pig`, `octopus`, `dog` — and **all 8 produced a row**, every one
with `outcome: "ok"` and `stage_reached: "emit"`. No subject hit the 1800 s
`cap_secs`; the slowest single dense run was `octopus` at 242.65 s. So no figure
above is generalised beyond the eight subjects that were measured, and equally,
none of the eight is missing.

`starfish` is a real row but a different regime (§7), so the ladder's claims rest
on the **seven** budget-capped rows, and the §4.3 row rests on **`lizard`**.

---

## 10. Run metadata

| field | value |
|---|---|
| `commit` | `2491d7a5e5972b80acc937801bade41360e61e52` |
| `measured_utc` | `2026-09-29T22:25:49+00:00` — the run **start**, not its end |
| `budget` | 20,000 nodes, fixed for every subject |
| `cap_secs` | 1800, set above `dog`'s committed 537.3 s sparse cost (cited from `../2026-09-20-box-pleat/oracle-census/certify.json`); never breached |
| `thresholds` | `top_dominates` 0.50, `no_lever_below` 0.25, `scales` 2.0, `flat_at_or_below` 1.2, `gate_sum_tol` 0.05 |
| instrument | `profile.py`, git blob `6e8f034013cb8ce90faf7f73e559d84c42a4bf67` |

**The instrument is unchanged from before the run.** That blob is the one
committed in `2491d7a`, which is the same SHA `profile.json` records as the commit
it ran at, and `git status` reports the evidence directory clean apart from this
README.

**Duration: 34.3 minutes for the ladder**, derived rather than estimated. The
per-subject times in `profile.json` sum to **1,126.5 s** sparse + **930.81 s**
dense = **2,057.31 s = 34.29 min**, and independently the artifact's `measured_utc`
start (17:25:49 local, UTC−5) to `profile.json`'s last write at 18:00:07 local is
**34 min 18 s**. `measured_utc` records only the start, so any duration must be
derived this way. The `--cprofile` sweep was a separate invocation, written at
18:02:44 local, and its own profiled run reads **135.779 s** — profiler-distorted
seconds.

**Nothing under `mcp_harness/` was read-modified: production was read only.**
`git diff --stat HEAD -- mcp_harness/` is empty, and
`grep -c box_pleat mcp_harness/server.py` remains 0.
