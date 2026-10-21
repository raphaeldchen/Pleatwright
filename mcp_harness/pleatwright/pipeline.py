"""Pleatwright: stick-figure tree -> finished model, end to end (COrigami §3.2-3.7).

    stick figure --pack--> packing CP --solve--> solving CP
                 --shape--> shaping CP --fold--> folded model (7 views)

`run(tree)` (a roll name or a tree.json path) executes every stage and writes one sample folder in the exact
layout of COrigami's released samples (``origami_samples/<name>_<grid>/``):

    packing_cp.svg   hinges (green) + ridges (red), unassigned
    solving_cp.svg   the flat-foldable base, M (red) / V (blue), pleats
                     carrying elevation="0|1"
    shaping_cp.svg   base + shaping creases, partial folds as opacity
    overview.png     (1) stick figure x4 views, (2)-(4) the three CPs,
                     then the folded model from seven views

A machine-readable record of every stage (scores, timings, verdicts) is
returned and can be written next to the samples by the CLI.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
import time
from dataclasses import asdict, dataclass, field
from fractions import Fraction

import numpy as np

from . import base as B
from . import efficiency as EF
from . import fold as F
from . import nest as NE
from . import pack as PK
from . import render as R
from . import shape as SH
from . import solve as SV
from . import stick as ST

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STICKS = os.path.join(HERE, "fixtures", "full17_v3_sticks")


def count_cp(cp) -> tuple:
    """COrigami's 'Flat-foldable: k/n': every CP vertex; interior vertices
    must pass the crimp test (App. D, Alg. 1) on their M/V labels, border
    vertices pass."""
    from collections import defaultdict
    inc = defaultdict(list)
    allv = set()
    for e in cp.edges:
        a, b = tuple(e.a), tuple(e.b)
        allv |= {a, b}
        if e.kind in ("M", "V"):
            inc[a].append((b, e.kind))
            inc[b].append((a, e.kind))
    N = cp.N
    good = 0
    for p in allv:
        interior = 1e-9 < p[0] < N - 1e-9 and 1e-9 < p[1] < N - 1e-9
        if not interior:
            good += 1
            continue
        rays = sorted(((math.degrees(math.atan2(q[1] - p[1], q[0] - p[0])) % 360.0, lab)
                       for q, lab in inc[p]))
        if len(rays) < 2:
            continue
        sec = [((rays[(k + 1) % len(rays)][0] - rays[k][0]) % 360.0) or 360.0
               for k in range(len(rays))]
        if SV.crimp_flat_foldable(sec, [r[1] for r in rays]):
            good += 1
    return good, len(allv)


def similarity(sf, con, base, sigma) -> float:
    """App. C.2 tree similarity: Procrustes between the stick figure's merged
    joints (hubs + leaves) and their positions in the shaped model."""
    ops, G, info, children, Q0 = SH.plan_folds(sf, con, base, sigma)
    tgt = sf.positions()
    pts_t, pts_m = [], []
    names = {con.root} | {c.v for c in con.chains}
    for c in con.chains:
        last = c.sticks[-1]
        d = info[last]
        s_end = base.strip[c.u] + d["sigma"] * d["off1"]
        pm = (G[last] @ np.array([s_end, 0.5, 0, 1.0]))[:3]
        pts_m.append(pm)
        pts_t.append(tgt[c.v])
    first = con.chains[SH.root_chain(con)]
    d = info[first.sticks[0]]
    pts_m.append((G[first.sticks[0]] @ np.array([base.strip[con.root], 0.5, 0, 1.0]))[:3])
    pts_t.append(tgt[con.root])
    A, Bm = np.array(pts_t), np.array(pts_m)
    A = A - A.mean(0)
    Bm = Bm - Bm.mean(0)
    A /= np.linalg.norm(A)
    Bm /= np.linalg.norm(Bm)
    s = np.linalg.svd(A.T @ Bm, compute_uv=False)
    return float(s.sum() ** 2)


def shape_and_fold(sf, con, base, sv, sigma, narrow=(), extra=()):
    """Shape the solved base (tree shaping + optional narrowing / extra
    simple folds), choose the senses of its 180-degree folds, and fold the
    shaping CP with the geometric folder.  Returns a candidate dict."""
    nrs = SH.narrowings_for(con, base, sigma, list(narrow)) if narrow else []
    plan = SH.plan_folds(sf, con, base, sigma, nrs, extra)
    shp = SH.shape(sf, con, base, sv, sigma, plan=plan, narrowings=nrs)
    ff = count_cp(shp.cp)
    # A 180-degree simple fold can be made in either sense with identical
    # geometry; pick senses greedily so the folds unfold rather than overfold
    # the base creases they cross (maximise shaping flat-foldability).
    sense = {i: (1 if shp.ops[i].phi > 0 else -1) for i in SH.flat_ops(shp.ops)}
    for _pass in range(2):
        improved = False
        for i in list(sense):
            if ff[0] == ff[1]:
                break
            trial = dict(sense)
            trial[i] = -trial[i]
            SH.relabel(shp, trial)
            f2 = count_cp(shp.cp)
            if f2[0] > ff[0]:
                sense, ff, improved = trial, f2, True
        SH.relabel(shp, sense)
        if not improved or ff[0] == ff[1]:
            break
    V, raw = shp.cp.fold_input()
    m = F.build_model(np.array(V, float), raw)
    mats = F.solve_fold(m)
    X3 = F.vertex_positions(m, mats)
    # COrigami's folder pins its BFS start face at the identity, i.e. in that
    # face's paper frame; carry the result into the world frame of the
    # stick figure through the start face's own shaped transform.
    start = F.central_face(m)
    W0 = SH.world_at(shp, m.vertices[m.faces[start]].mean(axis=0))
    polys = [(np.c_[P, np.ones(len(P))] @ W0.T)[:, :3] for P in F.face_positions(m, mats)]
    closure = F.closure_error(m, mats)
    return {"shaped": shp, "ff": ff, "polys": polys, "model": m, "W0": W0,
            "faces": len(m.faces),
            "closure": closure, "strain": F.axial_strain(m, X3),
            "valid": closure < 1e-3, "calls": list(narrow) + list(extra)}


def _orchestrate(sf, con, base, sv, sigma, baseline, k=3):
    """§3.6/§3.8: K single-step LLM tool-call proposals on top of tree
    shaping, judged by the VLM; keep the best (the baseline competes)."""
    from . import orchestrate as O
    orec = {}
    try:
        b_imgs = O.views_png(baseline["polys"])
        b_score, b_txt = O.judge(sf.name, b_imgs)
        best, best_score = baseline, (b_score if b_score is not None else -1)
        log = [{"candidate": "tree_shaping", "score": b_score}]
        for i, calls in enumerate(O.propose(sf, k)):
            narrow, extra = O.split_calls(calls)
            try:
                c = shape_and_fold(sf, con, base, sv, sigma, narrow, extra)
            except Exception as exc:
                log.append({"candidate": i, "calls": calls, "error": repr(exc)})
                continue
            sc, txt = O.judge(sf.name, O.views_png(c["polys"])) if c["valid"] else (None, "")
            r = O.reward(sc, len(calls), c["valid"])
            log.append({"candidate": i, "calls": calls, "score": sc, "reward": r})
            if c["valid"] and sc is not None and sc > best_score:
                best, best_score = c, sc
        orec["orchestrator"] = "llm" if best is not baseline else "tree_shaping (best by VLM)"
        orec["orchestration_log"] = log
        orec["vlm_score"] = best_score
        return best, orec
    except O.Unavailable as exc:
        orec["orchestrator"] = "tree_shaping (LLM/VLM unavailable)"
        orec["orchestration_error"] = str(exc)
        return baseline, orec


def title_of(sf) -> str:
    """'Dog roll 0' for an artifact roll; 'Dog' for a CLI-authored tree."""
    subj = sf.name.replace("_", " ")
    subj = f"{subj[0].upper()}{subj[1:]}"
    head, _, n = sf.roll.rpartition("_")
    return f"{subj} roll {n}" if head and n.isdigit() else subj


def _source(tree: str) -> str:
    """A roll name (`dog_0`, the artifact fixtures) or a path to a tree file."""
    if tree.endswith(".json"):
        if not os.path.exists(tree):
            raise FileNotFoundError(f"tree file not found: {tree}")
        return tree
    return os.path.join(STICKS, f"{tree}.json")


class StageError(RuntimeError):
    """An exception escaped a pipeline stage; `.stage` names it (load, packing,
    solving, shaping, output) and `__cause__` is the original exception."""

    def __init__(self, stage: str, cause: BaseException):
        super().__init__(f"{stage}: {type(cause).__name__}: {cause}")
        self.stage = stage


def _write(folder: str, name: str, text: str) -> str:
    path = os.path.join(folder, name)
    with open(path, "w") as f:
        f.write(text)
    return path


def _emit(on_stage, stage: str, **info) -> None:
    if on_stage is not None:
        on_stage(stage, info)


def run(tree: str, out_dir: str, *, scale: float = 1.0, certify_global: bool = True,
        max_candidates: int = 400, verbose: bool = True, orchestrate: bool = False,
        orchestrate_k: int = 3, on_stage=None, layout: str = "auto",
        chosen_by: str = "flag", options: PackOptions | None = None) -> dict:
    """Run every stage. Any exception a stage raises comes back as a
    `StageError` naming that stage. The keywords are spelled out (they are
    `_run`'s) so a mistyped one is a TypeError here, not StageError('load').
    `on_stage(stage, info)`, if given, is called after each stage's file is on
    disk (packing, solving, shaping, output); see the app spec §4.3.

    `layout` ("auto" | "symmetric" | "smaller") picks which packed layout is
    folded (spec §4, §5.1): "auto" applies the 10% rule, an explicit name folds
    that layout and records `chosen_by` ("flag" | "user") as the reason.
    `options` are the already packed layouts (`pack_options`); without them
    `run` packs `tree` itself.  `max_candidates` is kept for callers; the
    packing search uses `MAX_CANDIDATES`."""
    if layout not in ("auto", "symmetric", "smaller"):
        raise ValueError(f"layout must be auto, symmetric or smaller, not {layout!r}")
    stage = ["load"]
    try:
        return _run(tree, out_dir, _stage=stage, scale=scale,
                    certify_global=certify_global, max_candidates=max_candidates,
                    verbose=verbose, orchestrate=orchestrate,
                    orchestrate_k=orchestrate_k, on_stage=on_stage, layout=layout,
                    chosen_by=chosen_by, options=options)
    except StageError:
        raise
    except Exception as e:
        raise StageError(stage[0], e) from e


def _choose(opts: PackOptions, layout: str, chosen_by: str) -> tuple:
    """(option, reason) for a requested `layout` (spec §4, §5.1)."""
    if layout == "auto":
        if opts.verdict == "ask":
            return opts.smaller, "rule"
        if opts.verdict == "symmetric":
            return opts.symmetric, "rule"
    else:
        want = opts.option(layout)
        if want is not None:
            return want, chosen_by
    only = opts.symmetric or opts.smaller or opts.doubled
    return only, "only_option"


def _layout_record(opts: PackOptions, chosen: Option, reason: str) -> dict:
    return {"chosen": chosen.name, "reason": reason,
            "n_symmetric": None if opts.symmetric is None else opts.symmetric.layout.N,
            "n_smaller": opts.n_smaller,
            "gain": None if opts.gain is None else float(opts.gain),
            "threshold": float(GAIN_THRESHOLD),
            "family": chosen.family, "beside": opts.beside}


def _fallbacks(opts: PackOptions, chosen: Option) -> list:
    """The options `run --layout auto` folds, in order, when `chosen` fails in
    solving or shaping (§5.2a).  A beside choice falls back to today's chosen
    option and then today's own fallback (`PackOptions.today_fallback`), so a
    tree never folds on a grid larger than today's (river-routing spec §2);
    a choice of today's family keeps today's rule: the smaller layout falls
    back to the symmetric one, S', and then, when S' is a beside layout, to
    today's symmetric one."""
    if chosen.family == "beside" and opts.today_fallback:
        return list(opts.today_fallback)
    if chosen.name == "smaller" and opts.symmetric is not None:
        s = opts.symmetric
        return [s] + [o for o in opts.today_fallback
                      if (o.name, o.family, o.layout.N) != (s.name, s.family, s.layout.N)]
    return []


def _run(tree: str, out_dir: str, *, _stage: list, scale: float = 1.0, certify_global: bool = True,
        max_candidates: int = 400, verbose: bool = True, orchestrate: bool = False,
        orchestrate_k: int = 3, on_stage=None, layout: str = "auto",
        chosen_by: str = "flag", options: PackOptions | None = None) -> dict:
    t_all = time.perf_counter()
    src = _source(tree)
    if options is None:
        ST.contract(ST.load_roll(src, scale))        # a bad tree fails as "load"
    _stage[0] = "packing"
    # ---- packing (§3.2): the symmetric and the unmirrored layout, then the
    # doubled-length rung when neither builds (`pack_options`).
    t = time.perf_counter()
    opts = options if options is not None else pack_options(tree, scale=scale)
    rec = {"roll": opts.sf.roll}
    rec["pack_secs"] = round(time.perf_counter() - t, 2)
    # grid_init is the base scale's, as it was before the doubled rung existed
    rec["grid_init"] = PK.grid_init(opts.con if opts.verdict != "doubled"
                                    else _context(src, scale)[1])
    if opts.verdict == "none":
        rec["stick_figure"] = opts.sf.to_corigami_json()
        rec["pack_tried"] = max(opts.tried.values(), default=0)
        rec["failure"] = "packing"
        return rec
    chosen, reason = _choose(opts, layout, chosen_by)
    rec["layout"] = _layout_record(opts, chosen, reason)
    pre = dict(rec)
    callback_failed = []
    if on_stage is not None:
        user_hook = on_stage

        def on_stage(stage, info):          # noqa: F811 - a callback error is not a fold error
            try:
                user_hook(stage, info)
            except BaseException:
                callback_failed.append(stage)
                raise
    chain = _fallbacks(opts, chosen) if layout == "auto" else []
    try:
        _fold_option(rec, opts, chosen, out_dir, _stage, certify_global, verbose,
                     orchestrate, orchestrate_k, on_stage, t_all)
    except Exception as exc:
        # §5.2a: the layout the rule picked failed downstream; fold the next
        # one of `_fallbacks` instead.  An explicit choice is reported as is,
        # and so is an error from the on_stage callback.  The callback sees
        # the failed attempt's events (packing, and solving if shaping
        # failed), then the events of each fallback fold; its last "packing"
        # event points at the folder that was folded.  The app folds an
        # explicit choice after its layout card, and "auto" otherwise.
        errors, failed = [exc], chosen
        for opt in chain:
            if _stage[0] not in ("solving", "shaping") or callback_failed:
                break
            shutil.rmtree(os.path.join(out_dir, f"{title_of(opts.sf)}_{failed.layout.N}"),
                          ignore_errors=True)
            rec.clear()
            rec.update(pre)
            rec["layout"] = _layout_record(opts, opt, "fallback")
            rec["layout"]["fallback_error"] = f"{type(exc).__name__}: {exc}"
            if len(errors) > 1:
                rec["layout"]["fallback_errors"] = [f"{type(e).__name__}: {e}" for e in errors]
            try:
                _fold_option(rec, opts, opt, out_dir, _stage, certify_global, verbose,
                             orchestrate, orchestrate_k, on_stage, t_all)
                return rec
            except Exception as e:
                errors.append(e)
                failed = opt
        if len(errors) == 1:
            raise
        raise errors[-1]
    return rec


def _fold_option(rec, opts, opt, out_dir, _stage, certify_global, verbose, orchestrate,
                 orchestrate_k, on_stage, t_all) -> None:
    """Packing output, solving, shaping and the overview for one packed
    option; fills `rec` in place."""
    sf, con, sigma, base, lay = opts.sf, opts.con, opts.sigma, opt.base, opt.layout
    _stage[0] = "packing"
    rec["stick_figure"] = sf.to_corigami_json()
    rec["packing_rung"] = opt.rung
    rec["scale"] = opt.scale
    # a beside-chosen option reports today's count for its name: beside builds do not add to `tried`
    rec["pack_tried"] = opts.tried.get(opt.name, 0)
    rec["efficiency"] = opt.metrics
    N = lay.N
    rec["grid_size"] = N
    name = title_of(sf)
    folder = os.path.join(out_dir, f"{name}_{N}")
    os.makedirs(folder, exist_ok=True)
    pcp, dots = B.packing_cp(base)
    p = _write(folder, "packing_cp.svg", _pretty(pcp.svg(packing=True, precision=0)))
    _emit(on_stage, "packing", files=[p], folder=folder, grid=N,
          rung=rec["packing_rung"], tried=rec["pack_tried"],
          layout=rec["layout"], efficiency=rec["efficiency"])

    # ---- solving (§3.3)
    _stage[0] = "solving"
    t = time.perf_counter()
    sv = SV.solve(base, certify_global=certify_global)
    rec["solve_secs"] = round(time.perf_counter() - t, 2)
    rec["solving_flat_foldable"] = list(sv.ff_local)
    rec["solving_heuristic_local"] = list(sv.stats["heuristic_local"])
    rec["global_verdict"] = sv.global_verdict
    rec["relabelled_by_certificate"] = sv.relabelled
    rec["solve_stats"] = {k: v for k, v in sv.stats.items()}
    p = _write(folder, "solving_cp.svg", _pretty(sv.cp.svg(precision=5)))
    _emit(on_stage, "solving", files=[p], flat_foldable=list(sv.ff_local),
          global_verdict=sv.global_verdict)

    # ---- shaping (§3.4-3.6) and folding (§3.7)
    _stage[0] = "shaping"
    t = time.perf_counter()
    cand = shape_and_fold(sf, con, base, sv, sigma)
    rec["orchestrator"] = "tree_shaping"
    if orchestrate:
        cand, orec = _orchestrate(sf, con, base, sv, sigma, cand, k=orchestrate_k)
        rec.update(orec)
    shp, ff, polys = cand["shaped"], cand["ff"], cand["polys"]
    rec["shape_secs"] = round(time.perf_counter() - t, 2)
    rec["simple_folds"] = [{"stick": o.stick, "angle_deg": round(math.degrees(o.phi), 2),
                            "pivot": [round(float(v), 4) for v in o.pivot[:2]],
                            "axis": [round(float(v), 4) for v in o.axis[:2]]} for o in shp.ops]
    rec["narrowings"] = [{"stick": n.stick, "s0": n.s0, "H": n.H} for n in shp.narrowings]
    rec["shaping_flat_foldable"] = list(ff)
    rec["faces"] = cand["faces"]
    rec["closure_error"] = cand["closure"]
    rec["mean_axial_strain"] = cand["strain"]
    rec["tree_similarity"] = similarity(sf, con, base, sigma)
    p = _write(folder, "shaping_cp.svg", shp.cp.svg(precision=5))
    _emit(on_stage, "shaping", files=[p], flat_foldable=list(ff), candidate=cand)

    # ---- outputs, COrigami layout
    _stage[0] = "output"
    p = os.path.join(folder, "overview.png")
    R.overview(p, name=name, grid=N, stick=sf,
               packing_cp=pcp, solving_cp=sv.cp, shaping_cp=shp.cp, polys=polys,
               solving_ff=sv.ff_local, shaping_ff=rec["shaping_flat_foldable"],
               packing_dots=dots)
    _emit(on_stage, "output", files=[p], folder=folder)
    rec["folder"] = folder
    rec["total_secs"] = round(time.perf_counter() - t_all, 2)
    if verbose:
        print(json.dumps({k: v for k, v in rec.items() if k not in ("stick_figure", "simple_folds")}))


def _pretty(svg: str) -> str:
    """COrigami writes packing/solving SVGs one element per indented line."""
    lines = svg.split("\n")
    return "\n".join([lines[0]] + ["  " + l for l in lines[1:-1]] + [lines[-1]]) + "\n"


# ------------------------------------------------------------ layout choice
# Spec docs/superpowers/specs/2026-10-16-packing-layout-choice-design.md §4-5.
#: the unmirrored layout is offered only when it folds a model this much larger
GAIN_THRESHOLD = Fraction(11, 10)
#: packer work (pack.tick units) the unmirrored search may spend once the
#: symmetric layout is known.  Ticks are deterministic, so this is octopus_2's
#: measured 3,395,895 plus 3%: it always fits.  At about 21k ticks/s (scorpion_0
#: and octopus_2 alike) scorpion_0, which never finds a layout, is cut off after
#: about 165 s on this host under load ~6.  See
#: docs/superpowers/evidence/2026-10-16-layout-choice/README.md.
SMALLER_WORK_BUDGET = 3_500_000
MAX_CANDIDATES = 400

# Spec docs/superpowers/specs/2026-10-19-river-routing-design.md §5-6.
#: the switch for the beside searches (river routing) after today's search;
#: on since Phase 0 (spec §6): 10 of the 39 multi-hub trees shrink.
BESIDE = True
#: per beside search: packer work (pack.tick units) and `base.build` calls it
#: may spend.  Ticks are deterministic, so the work budget is scorpion_2's
#: unmirrored beside search (the most expensive WINNING one, 9,022,945 ticks)
#: plus 3%, rounded up: every Phase 0 win fits.  Every winning search built
#: once (`base.build` succeeded on its first candidate), so the build cap is
#: that 1 plus 10.  Worst case is spider_2 (both searches exhaust the budget):
#: 110 s for the whole `pack_options` call single-process on this host under
#: load 8-11 (today's own search 21 s of it).  See
#: docs/superpowers/evidence/2026-10-19-river-routing/README.md.
BESIDE_WORK_BUDGET = 9_300_000
BESIDE_MAX_BUILDS = 11


@dataclass
class Option:
    name: str            # "symmetric" | "smaller" | "doubled"
    rung: str            # the ladder rung that produced it
    scale: float         # length multiplier of the run (2x for "doubled")
    layout: PK.Layout
    base: B.Base
    metrics: dict
    family: str = "today"   # the packer family of `layout`: "today" | "beside"


@dataclass
class PackOptions:
    sf: object
    con: object
    sigma: object
    symmetric: Option | None
    smaller: Option | None
    doubled: Option | None
    n_smaller: int | None | str      # int | None | "none_below_cap" | "budget"
    gain: Fraction | None
    verdict: str                     # ask | symmetric | only_unmirrored | doubled | none
    #: candidate layouts the search tried before each option built (`run`'s
    #: `pack_tried`); without a symmetric layout the count runs on across
    #: rungs, as the old ladder's did.
    tried: dict = field(default_factory=dict)
    #: the beside searches' outcomes, {"symmetric": .., "smaller": ..}: a grid,
    #: or none_below_cap | budget | builds | no_child_hub | doubled | off.
    beside: dict = field(default_factory=dict)
    #: what `run` folds when the auto choice fails downstream and a beside
    #: layout replaced one of today's (`_fallbacks`): for a beside choice,
    #: today's chosen option, then today's symmetric one if today chose the
    #: smaller layout; for today's smaller layout with a beside S', today's
    #: symmetric one (folded after S').
    today_fallback: list = field(default_factory=list)

    @property
    def recommended(self) -> str | None:
        return "smaller" if self.verdict == "ask" else None

    def option(self, name: str) -> Option | None:
        return getattr(self, name, None) if name in ("symmetric", "smaller", "doubled") else None

    def summary(self) -> dict:
        def one(o):
            return None if o is None else {"grid": o.layout.N, "metrics": o.metrics,
                                           "family": o.family}
        return {"verdict": self.verdict,
                "gain": None if self.gain is None else round(float(self.gain), 4),
                "n_smaller": self.n_smaller,
                "symmetric": one(self.symmetric), "smaller": one(self.smaller),
                "doubled": one(self.doubled), "recommended": self.recommended,
                "beside": self.beside}


def _context(src: str, scale: float):
    sf = ST.load_roll(src, scale)
    con = ST.contract(sf)
    return sf, con, SH.choose_sigma(sf, con)


def _search(con, sigma, *, symmetric: bool, n_max: int, tried: int = 0):
    """First candidate layout whose base builds without errors, trying at most
    MAX_CANDIDATES in all (`tried` carries the count over from an earlier
    rung, as the old packing ladder did).  Returns (layout, base, tried)."""
    for lay in PK.candidates(con, symmetric=symmetric, N_max=n_max):
        tried += 1
        b = B.build(lay, con, sigma)
        if not b.errors:
            return lay, b, tried
        if tried >= MAX_CANDIDATES:
            break
    return None, None, tried


def _verdict(sym, small, doubled) -> tuple:
    """(verdict, gain) by the rule of spec §4; the comparison is exact."""
    if sym is not None:
        if small is not None:
            n_sym, n_small = sym.layout.N, small.layout.N
            gain = Fraction(n_sym, n_small)
            return ("ask" if n_sym >= GAIN_THRESHOLD * n_small else "symmetric"), gain
        return "symmetric", None
    if small is not None:
        return "only_unmirrored", None
    return ("doubled" if doubled is not None else "none"), None


class _BuildCap(Exception):
    """A beside search passed BESIDE_MAX_BUILDS candidates to `base.build`."""


def _search_beside(con, sigma, *, symmetric: bool, n_max: int):
    """First beside layout (`nest.beside_candidates`) on a grid <= n_max whose
    base builds without errors, as (layout, base), or (None, None).  Raises
    _BuildCap after BESIDE_MAX_BUILDS failed builds; spends packer ticks, so
    the caller's `pack.work_budget` bounds it."""
    builds = 0
    for lay in NE.beside_candidates(con, symmetric=symmetric, N_max=n_max):
        builds += 1
        b = B.build(lay, con, sigma)
        if not b.errors:
            return lay, b
        if builds >= BESIDE_MAX_BUILDS:
            raise _BuildCap(f"{builds} beside builds")
    return None, None


def pack_options(tree: str, *, scale: float = 1.0, work_budget: int | None = None,
                 beside: bool | None = None) -> PackOptions:
    """Pack the symmetric and the unmirrored layout of `tree` (packing only:
    no solving, nothing written) and apply the 10% rule.  The unmirrored
    search runs under a grid cap (`N_sym*10//11`) and a deterministic work
    budget when the symmetric layout exists; otherwise it is today's rung 2.

    Then, if `beside` (None: the `BESIDE` switch), two budgeted searches of
    the beside family (river routing, spec 2026-10-19 §5.2), symmetric and
    unmirrored, each on grids below today's chosen one (C - 2), may replace
    today's symmetric option and the smaller one; the rule is applied again.
    When a beside layout replaced one of today's, `today_fallback` keeps
    today's options for `run`'s fallback (§5.2a)."""
    today = _pack_options_today(tree, scale=scale, work_budget=work_budget)
    on = BESIDE if beside is None else beside
    con, sigma = today.con, today.sigma
    if not on:
        why = "off"
    elif len(con.hubs) == 1:
        why = "no_child_hub"
    elif today.verdict == "doubled":
        why = "doubled"
    else:
        why = None
    if why is not None:
        today.beside = {"symmetric": why, "smaller": why}
        return today
    if today.verdict == "none":
        G = PK.grid_init(con)
        cap = max(2 * G, G + 60)
    else:
        cap = _choose(today, "auto", "flag")[0].layout.N - 2
    outcome, found = {}, {}
    for key, symmetric in (("symmetric", True), ("smaller", False)):
        try:
            with PK.work_budget(BESIDE_WORK_BUDGET):
                lay, b = _search_beside(con, sigma, symmetric=symmetric, n_max=cap)
        except PK.BudgetExhausted:
            outcome[key] = "budget"
            continue
        except _BuildCap:
            outcome[key] = "builds"
            continue
        except Exception:           # a beside search must never kill packing
            outcome[key] = "error"
            continue
        if lay is None:
            outcome[key] = "none_below_cap"
            continue
        outcome[key] = lay.N
        found[key] = Option(key, "symmetric" if symmetric else "asymmetric", scale, lay, b,
                            EF.metrics(lay, con, b, scale), family="beside")
    sym = found.get("symmetric") or today.symmetric
    small = today.smaller
    sb = found.get("smaller")
    if sb is not None and (small is None or sb.layout.N < small.layout.N):
        small = sb
    verdict, gain = _verdict(sym, small, today.doubled)
    n_smaller = small.layout.N if small is not None else today.n_smaller
    new = PackOptions(today.sf, con, sigma, sym, small, today.doubled, n_smaller, gain,
                      verdict, today.tried, beside=outcome)
    if verdict != "none" and today.verdict != "none":
        c = _choose(new, "auto", "flag")[0]
        if c.family == "beside":
            t = _choose(today, "auto", "flag")[0]
            new.today_fallback = [t] + ([today.symmetric] if t.name == "smaller"
                                        and today.symmetric is not None else [])
        elif c.name == "smaller" and sym is not None and sym.family == "beside" \
                and today.symmetric is not None:
            new.today_fallback = [today.symmetric]
    return new


def _pack_options_today(tree: str, *, scale: float = 1.0,
                        work_budget: int | None = None) -> PackOptions:
    """Today's search (slice 1, unchanged): the symmetric rung, the capped and
    budgeted unmirrored rung, the doubled rung."""
    src = _source(tree)
    sf, con, sigma = _context(src, scale)
    n_max = max(2 * PK.grid_init(con), PK.grid_init(con) + 60)
    lay, b, tried = _search(con, sigma, symmetric=True, n_max=n_max)
    sym = small = doubled = None
    n_smaller = None
    tried_by = {}
    if b is not None:
        tried_by["symmetric"] = tried
        sym = Option("symmetric", "symmetric", scale, lay, b, EF.metrics(lay, con, b, scale))
        cap = lay.N * 10 // 11
        budget = SMALLER_WORK_BUDGET if work_budget is None else work_budget
        try:
            with PK.work_budget(budget):
                lay2, b2, tried_by["smaller"] = _search(con, sigma, symmetric=False, n_max=cap)
        except PK.BudgetExhausted:
            lay2 = None
            n_smaller = "budget"
        if lay2 is not None:
            small = Option("smaller", "asymmetric", scale, lay2, b2,
                           EF.metrics(lay2, con, b2, scale))
            n_smaller = lay2.N
        elif n_smaller is None:
            n_smaller = "none_below_cap"
    else:
        lay2, b2, tried = _search(con, sigma, symmetric=False, n_max=n_max, tried=tried)
        tried_by["smaller"] = tried
        if b2 is not None:
            small = Option("smaller", "asymmetric", scale, lay2, b2,
                           EF.metrics(lay2, con, b2, scale))
            n_smaller = lay2.N
        else:
            sf, con, sigma = _context(src, 2 * scale)
            n_max = max(2 * PK.grid_init(con), PK.grid_init(con) + 60)
            lay3, b3, tried = _search(con, sigma, symmetric=True, n_max=n_max, tried=tried)
            tried_by["doubled"] = tried
            if b3 is not None:
                doubled = Option("doubled", "symmetric x2", 2 * scale, lay3, b3,
                                 EF.metrics(lay3, con, b3, 2 * scale))
            else:
                sf, con, sigma = _context(src, scale)
    verdict, gain = _verdict(sym, small, doubled)
    return PackOptions(sf, con, sigma, sym, small, doubled, n_smaller, gain, verdict, tried_by)


def _option_dict(o: Option) -> dict:
    return {"rung": o.rung, "scale": o.scale, "metrics": o.metrics,
            "family": o.family, "layout": PK.layout_to_dict(o.layout)}


def save_options(opts: PackOptions, directory: str) -> list:
    """Write options.json (the summary, the candidates tried, each option's
    layout and, when a beside layout replaced one of today's, today's fallback options)
    and the packing CP of the symmetric and smaller layouts; return the paths."""
    os.makedirs(directory, exist_ok=True)
    doc = {"summary": opts.summary(), "tried": opts.tried, "options": {}}
    paths = []
    for name in ("symmetric", "smaller", "doubled"):
        o = opts.option(name)
        if o is None:
            continue
        doc["options"][name] = _option_dict(o)
        if name != "doubled":
            pcp, _ = B.packing_cp(o.base)
            paths.append(_write(directory, f"{name}_packing_cp.svg",
                                _pretty(pcp.svg(packing=True, precision=0))))
    if opts.today_fallback:
        doc["today_fallback"] = [_option_dict(o) | {"name": o.name} for o in opts.today_fallback]
    paths.insert(0, _write(directory, "options.json", json.dumps(doc, default=float)))
    return paths


def load_options(tree: str, directory: str) -> PackOptions:
    """Inverse of save_options: rebuild each base from its saved layout
    (`B.build`, no search)."""
    with open(os.path.join(directory, "options.json")) as f:
        doc = json.load(f)
    src = _source(tree)
    ctx: dict = {}
    opts: dict = {}

    def option(name, d):
        sc = d["scale"]
        if sc not in ctx:
            ctx[sc] = _context(src, sc)
        sf, con, sigma = ctx[sc]
        lay = PK.layout_from_dict(d["layout"])
        return Option(name, d["rung"], sc, lay, B.build(lay, con, sigma), d["metrics"],
                      family=d.get("family", "today"))

    for name, d in doc["options"].items():
        opts[name] = option(name, d)
    fallback = [option(d["name"], d) for d in doc.get("today_fallback", [])]
    sm = doc["summary"]
    first = next(iter(opts.values()), None)
    sf, con, sigma = ctx[first.scale] if first else _context(src, 1.0)
    sym, small = opts.get("symmetric"), opts.get("smaller")
    gain = Fraction(sym.layout.N, small.layout.N) if sym and small else None
    return PackOptions(sf, con, sigma, sym, small, opts.get("doubled"),
                       sm["n_smaller"], gain, sm["verdict"], doc.get("tried", {}),
                       beside=sm.get("beside", {}), today_fallback=fallback)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("rolls", nargs="*")
    ap.add_argument("--out", required=True)
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--no-certify", action="store_true")
    ap.add_argument("--record", default=None, help="append JSON lines here")
    ap.add_argument("--layout", choices=("auto", "symmetric", "smaller"), default="auto",
                    help="auto folds the smaller unmirrored layout only when it makes the "
                         "model at least 10%% larger (spec 2026-10-16-packing-layout-choice)")
    ap.add_argument("--orchestrate", action="store_true",
                    help="LLM tool-use shaping + VLM selection (needs a working Anthropic key)")
    a = ap.parse_args(argv)
    rolls = a.rolls or sorted(f[:-5] for f in os.listdir(STICKS) if f.endswith(".json"))
    for r in rolls:
        try:
            rec = run(r, a.out, scale=a.scale, certify_global=not a.no_certify,
                      orchestrate=a.orchestrate, layout=a.layout)
        except Exception as exc:  # recorded, never silently swallowed
            import traceback
            rec = {"roll": r, "failure": "exception", "error": repr(exc),
                   "trace": traceback.format_exc()[-2000:]}
            print(json.dumps({"roll": r, "failure": repr(exc)}), file=sys.stderr)
        if a.record:
            with open(a.record, "a") as f:
                f.write(json.dumps(rec, default=float) + "\n")


if __name__ == "__main__":
    main()
