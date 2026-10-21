"""python -m concept_ab <command>: the concept-image experiment (spec 2026-10-16).

Results live under --root (default $CONCEPT_AB_DIR or
~/Pleatwright/experiments/2026-10-16-concept-image/), never in the repo.
Exit codes: 0 done, 4 stopped on a quota (rerun later; finished cells are
kept), 5 stopped at the spend cap.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

from concept_ab import arms as A
from concept_ab import run

DEFAULT_ROOT = os.path.expanduser("~/Pleatwright/experiments/2026-10-16-concept-image")
EXIT = {None: 0, "hf_quota": 4, "gemini_quota": 4, "budget": 5}


def _llm(model: str | None = None):
    import env_config
    import llm_client
    env_config.load_env()
    os.environ.setdefault("LLM_MAX_TOKENS", "64000")
    return llm_client.LLMClient.from_env(model)


def _subjects(arg: str | None) -> list[str]:
    if not arg:
        return list(A.SUBJECTS)
    names = [s.strip().replace("_", " ") for s in arg.split(",") if s.strip()]
    unknown = [s for s in names if s not in A.SUBJECTS]
    if unknown:
        raise SystemExit(f"unknown subject(s): {', '.join(unknown)}")
    return names


def _cmd_run(ns) -> int:
    rep = asyncio.run(run.run_cells(ns.root, ns.arms.split(","), ns.round,
                                    _subjects(ns.subjects), llm=_llm(), winner=ns.winner))
    print(f"done {len(rep.done)}, skipped {len(rep.skipped)}, failed {len(rep.failed)}")
    for cid, why in rep.failed.items():
        print(f"  FAILED {cid}: {why}")
    if rep.stopped:
        print(f"STOPPED ({rep.stopped}): {rep.stop_note}", file=sys.stderr)
    return EXIT[rep.stopped]


def _cmd_draft(ns) -> int:
    from concept_ab import judge, review
    library = os.environ.get("MESH_LIBRARY_DIR", os.path.expanduser("~/Downloads/photo_meshes"))
    review.ensure_photo_cells(ns.root, library)
    n = asyncio.run(review.draft_scores(ns.root, _llm(judge.JUDGE_MODEL)))
    print(f"drafted {n} cell(s)")
    return 0


def _cmd_review(ns) -> int:
    from concept_ab import review
    print(review.build_review(ns.root, ns.round))
    return 0


def _load_scores(ns, round_: int | None = None) -> dict:
    import json
    path = os.path.join(ns.root, f"scores_r{round_ or ns.round}.json")
    if not os.path.exists(path):
        raise SystemExit(f"no {path}: save it from the review page first")
    return json.load(open(path))


def _cmd_score(ns) -> int:
    import json
    from concept_ab import score
    r1 = os.path.join(ns.root, "scores_r1.json")
    photo = json.load(open(r1)) if ns.round != 1 and os.path.exists(r1) else None
    t = score.tally(_load_scores(ns), ns.root, photo_scores=photo)
    if t["photo_bar"] is None:
        print("photo bar unscored: mark the photo rows (round 1) before deciding good enough")
        return 3
    print(f"round {ns.round}   photo bar {t['photo_bar']}   good enough = photo bar - 1")
    for arm, row in sorted(t["by_arm"].items()):
        flag = "" if arm == "photo" else ("  good enough" if t["good_enough"][arm] else "")
        print(f"  {arm:6} {row['passed']:2}/{row['scored']:2} passed{flag}")
    if t["unscored"]:
        print("  UNSCORED: " + ", ".join(t["unscored"]))
    if t["unlifted"]:
        print("  UNLIFTED (counted as mesh fails): " + ", ".join(t["unlifted"]))
    if any(a in t["by_arm"] for a in score.SIMPLICITY):
        t["winner"] = score.winner(t)
        print(f"  winner among B-D: {t['winner']}")
    with open(os.path.join(ns.root, f"tally_r{ns.round}.json"), "w") as f:
        json.dump(t, f, indent=1)
    return 0


def _cmd_calibrate(ns) -> int:
    import json
    from concept_ab import judge, score
    r = asyncio.run(score.calibrate(ns.root, _llm(judge.JUDGE_MODEL), _load_scores(ns)))
    print(json.dumps(r))
    with open(os.path.join(ns.root, f"calibration_r{ns.round}.json"), "w") as f:
        json.dump(r, f, indent=1)
    return 0


def _cmd_trees(ns) -> int:
    from concept_ab import trees
    sigs = asyncio.run(trees.tree_signal(ns.root, _llm()))
    for cid, s in sigs.items():
        print(f"  {cid:22} leaves {s['leaves']}/{s['expected']}"
              f"{'  folded' if s['folded'] else ''}"
              f"{'  ' + s['failure'] if s['failure'] else ''}")
    print(f"{len(sigs)} cell(s) authored")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m concept_ab")
    ap.add_argument("--root", default=os.environ.get("CONCEPT_AB_DIR", DEFAULT_ROOT))
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="generate and lift the missing cells")
    r.add_argument("--arms", required=True, help="comma list, e.g. A,B,C,D")
    r.add_argument("--round", type=int, default=1)
    r.add_argument("--subjects", help="comma list; default all 17")
    r.add_argument("--winner", help="arm E only: the round-1 winner, C or D")
    r.set_defaults(fn=_cmd_run)
    sub.add_parser("draft", help="Claude's draft scores (adds the photo reference row)"
                   ).set_defaults(fn=_cmd_draft)
    v = sub.add_parser("review", help="write the blinded review page")
    v.add_argument("--round", type=int, default=1)
    v.set_defaults(fn=_cmd_review)
    for name, fn, what in (("score", _cmd_score, "tally the owner's scores"),
                           ("calibrate", _cmd_calibrate, "picker vs the owner's image labels")):
        c = sub.add_parser(name, help=what)
        c.add_argument("--round", type=int, default=1)
        c.set_defaults(fn=fn)
    sub.add_parser("trees", help="secondary signal: author a tree per mesh and fold it"
                   ).set_defaults(fn=_cmd_trees)
    ns = ap.parse_args(argv)
    return ns.fn(ns)


if __name__ == "__main__":
    import env_config
    env_config.load_env()
    sys.exit(main())
