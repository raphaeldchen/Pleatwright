"""Fold the example trees into the browser site's gallery: one run folder per
roll, written by the app's own run manager (same event log, same files the UI
renders), and gallery/index.json, the rows the site lists. The examples are the
demo trees in gallery_trees/, then the artifact rolls but the starfish.

    python app/browser/build_gallery.py OUT_DIR [--rolls dog_0,ant_1|all] [--jobs N] [--heap PATH]

--heap PATH is a JSON object roll -> peak heap in MB (the Pyodide fold spike's
measurement); a roll above HEAP_LIMIT_MB is shown but not offered "Fold it here".
Exit status is 1 when any roll failed to fold.
"""
from __future__ import annotations

import argparse
import asyncio
import glob
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, os.path.join(_REPO, "app", "server"))

from pleatwright_app import guided, runs, tools  # noqa: E402  (puts mcp_harness on sys.path)
from pleatwright.__main__ import ConfigError  # noqa: E402

FIXTURES = os.path.join(_REPO, "mcp_harness", "fixtures", "full17_v3_sticks")
#: demo trees, listed first: demo_scorpion is the tree of the owner's 2026-10-12 scorpion
#: run (approved after one revision; grid 40, CERTIFIED)
DEMOS_DIR = os.path.join(_HERE, "gallery_trees")
#: artifact subjects the owner took out of the gallery (2026-11-07)
OMITTED_SUBJECTS = {"starfish"}


def _names(directory: str) -> list[str]:
    return sorted(os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(directory, "*.json")))


DEMOS = _names(DEMOS_DIR)
ROLLS = DEMOS + [r for r in _names(FIXTURES) if r.rpartition("_")[0] not in OMITTED_SUBJECTS]
#: a fold that peaked above this in Pyodide does not fit a browser tab
HEAP_LIMIT_MB = 3500


def run_id(roll: str) -> str:
    return f"gallery-{roll}"


def label(roll: str) -> str:
    """The sidebar label: "dog roll 0" for dog_0, "demo scorpion" for demo_scorpion."""
    if roll in DEMOS:
        return roll.replace("_", " ")
    subject, _, n = roll.rpartition("_")
    return f"{subject.replace('_', ' ')} roll {n}"


def tree_path(roll: str) -> str:
    return os.path.join(DEMOS_DIR if roll in DEMOS else FIXTURES, f"{roll}.json")


def _no_client(_model: str):
    raise ConfigError("the gallery build uses no VLM")


async def _fold_one(store: runs.RunStore, roll: str) -> None:
    """Fold `roll`'s raw tree, answering the layout card with the rule's
    recommendation as a user's choice (as the app logs it)."""
    with open(tree_path(roll)) as f:
        tree = json.load(f)
    rid = run_id(roll)
    if os.path.exists(os.path.join(store.root, rid)):
        shutil.rmtree(os.path.join(store.root, rid))              # a rebuild replaces it
    mgr = guided.Manager(store, _no_client)
    await mgr.fold_tree(tree, label(roll), run_id=rid)
    await mgr.wait_idle()
    log = store.log(rid)
    ph = guided.phase(log)
    if ph["phase"] == "review" and ph.get("stage") == "packing":
        choice = (tools.layout_summary(store.dir(rid)) or {}).get("recommended")
        if choice is None:
            raise RuntimeError("the layout card has no recommended layout")
        await mgr.approve(rid, choice=choice)
        await mgr.wait_idle()


def index_rows(out_dir: str, rolls: list[str], heap: dict[str, float] | None = None) -> list[dict]:
    """The gallery rows of `rolls`' run folders in `out_dir`, in `rolls` order."""
    by_id = {row["id"]: row for row in runs.RunStore(out_dir).list()}
    rows = []
    for roll in rolls:
        row = by_id.get(run_id(roll))
        if row is None:
            continue
        foldable = heap is None or roll not in heap or heap[roll] <= HEAP_LIMIT_MB
        rows.append({**row, "kind": "gallery", "browser_foldable": foldable})
    return rows


def _write_index(out_dir: str, rows: list[dict]) -> None:
    tmp = os.path.join(out_dir, "index.json.tmp")
    with open(tmp, "w") as f:
        json.dump(rows, f, indent=2)
    os.replace(tmp, os.path.join(out_dir, "index.json"))


def _fold_in_subprocess(out_dir: str, roll: str) -> str | None:
    """Fold one roll in its own interpreter (fold jobs spawn processes, which a
    daemonic pool worker may not); None on success, else why it failed."""
    p = subprocess.run([sys.executable, os.path.abspath(__file__), out_dir, "--rolls", roll,
                        "--no-index"], capture_output=True, text=True)
    if p.returncode == 0:
        return None
    return (p.stderr.strip() or p.stdout.strip() or f"exit code {p.returncode}").splitlines()[-1]


def build(out_dir: str, rolls: list[str], heap: dict[str, float] | None = None,
          jobs: int = 1, *, write_index: bool = True) -> list[dict]:
    """Fold `rolls` into `out_dir/gallery-<roll>/`, write `out_dir/index.json`,
    and return one row per roll. A roll that does not fold is a row with status
    "failed" and an `error`; the others still fold. index.json lists only the
    rolls that are "done" and did not fail (a failed roll's folder may stay on
    disk, unlisted, even one that reads "done"), and covers just `rolls`: a
    partial run rewrites it with only those."""
    unknown = [r for r in rolls if r not in ROLLS]
    if unknown:
        raise ValueError(f"not a gallery roll: {', '.join(unknown)}")
    os.makedirs(out_dir, exist_ok=True)
    errors: dict[str, str] = {}
    if jobs > 1 and len(rolls) > 1:
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            for roll, err in zip(rolls, pool.map(lambda r: _fold_in_subprocess(out_dir, r), rolls)):
                if err:
                    errors[roll] = err
    else:
        store = runs.RunStore(out_dir)
        for roll in rolls:
            try:
                asyncio.run(_fold_one(store, roll))
            except Exception as e:                     # noqa: BLE001 -- one roll must not stop the rest
                errors[roll] = f"{type(e).__name__}: {e}"
    rows = index_rows(out_dir, rolls, heap)
    if write_index:
        failed = {run_id(roll) for roll in errors}
        _write_index(out_dir, [r for r in rows if r["status"] == "done" and r["id"] not in failed])
    by_id = {r["id"]: r for r in rows}
    result = []
    for roll in rolls:
        row = by_id.get(run_id(roll))
        if row is None:                                # no run folder at all
            row = {"id": run_id(roll), "prompt": label(roll), "status": "failed", "kind": "gallery"}
        if roll in errors:
            row = {**row, "status": "failed", "error": errors[roll]}
        result.append(row)
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("out_dir")
    ap.add_argument("--rolls", default="all", help="comma-separated rolls, or all")
    ap.add_argument("--jobs", type=int, default=1, help="rolls folded at once, one process each")
    ap.add_argument("--heap", help="JSON file: roll -> peak heap in MB")
    ap.add_argument("--no-index", action="store_true", help=argparse.SUPPRESS)   # a --jobs child
    args = ap.parse_args(argv)
    rolls = ROLLS if args.rolls == "all" else [r for r in args.rolls.split(",") if r]
    heap = None
    if args.heap:
        with open(args.heap) as f:
            heap = json.load(f)
    rows = build(args.out_dir, rolls, heap, args.jobs, write_index=not args.no_index)
    failed = [r for r in rows if r["status"] != "done"]
    for r in failed:
        print(f"FAILED {r['id']}: {r.get('error') or r['status']}", file=sys.stderr)
    print(f"{len(rows) - len(failed)}/{len(rows)} rolls folded into {args.out_dir}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
