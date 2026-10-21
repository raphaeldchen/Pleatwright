"""Mesh ratings for the app's mesh review (spec 2026-10-11 §1).

Each cached mesh folder may hold a `ratings.json` beside its `mesh.glb` and
`meta.json`: who the mesh is for (subject, provider, prompt, description, seed)
and how reviewers judged it (approvals, rejections with their feedback). A
separate file, not fields in meta.json: write_mesh_meta rewrites meta.json
whole, and provenance writing can be disabled, so counts kept there could be
lost. A new run of a subject is served its best PROVEN mesh first: at least one
approval, ranked by the Wilson score lower bound (Evan Miller, "How Not To Sort
By Average Rating"), so 9 of 10 outranks 1 of 1.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import re

RATINGS = "ratings.json"
_ARTICLE = re.compile(r"^(?:a|an|the)\s+")


def words(text: str) -> list[str]:
    """Unicode word tokens, case-folded: letters and digits of any script, so
    "Éléphant", "3d" and "狗" are words. The one tokeniser shared with
    subject_rewrite."""
    return re.findall(r"[^\W_]+", text.casefold())


def subject_key(prompt: str) -> str:
    """The prompt as a ratings key: case-folded, punctuation gone, one leading
    article dropped. "a moose", "Moose." and "the moose" share `moose`;
    "狗" and "猫" keep distinct keys."""
    return _ARTICLE.sub("", " ".join(words(prompt)))


def wilson_lower_bound(approvals: int, rejections: int, z: float = 1.96) -> float:
    n = approvals + rejections
    if n == 0:
        return 0.0
    p = approvals / n
    return ((p + z * z / (2 * n) - z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n))
            / (1 + z * z / n))


def read_ratings(key_dir: str) -> dict | None:
    try:
        with open(os.path.join(key_dir, RATINGS)) as f:
            r = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(r, dict):
        return None
    # Well-formed JSON with a wrong-typed field is as unreadable as torn JSON:
    # best_proven would crash on it at every new run. Only validated records
    # leave this function; record_verdict then starts a mistyped folder afresh.
    if "approvals" in r and (not isinstance(r["approvals"], int) or isinstance(r["approvals"], bool)):
        return None
    if "rejections" in r and not isinstance(r["rejections"], list):
        return None
    return r


def record_verdict(key_dir: str, *, approved: bool, run_id: str, subject: str,
                   provider: str, prompt: str, description: str | None = None,
                   seed: int | None = None, feedback: str = "") -> dict:
    """Count one review of the mesh in `key_dir`; return the updated record.
    Written atomically (temp file + os.replace), like the cache's meta.json."""
    r = read_ratings(key_dir) or {}
    for k, v in (("subject", subject), ("provider", provider), ("prompt", prompt),
                 ("description", description), ("seed", seed)):
        r.setdefault(k, v)
    r.setdefault("approvals", 0)
    r.setdefault("rejections", [])
    if approved:
        r["approvals"] += 1
    else:
        r["rejections"].append({"feedback": feedback, "run": run_id,
                                "utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
    path = os.path.join(key_dir, RATINGS)
    with open(path + ".tmp", "w") as f:
        json.dump(r, f, indent=1)
    os.replace(path + ".tmp", path)
    return r


def best_proven(cache_dir: str, provider: str, subject: str) -> str | None:
    """The folder of `subject`'s best proven mesh from `provider`, or None."""
    if not subject:
        return None
    try:
        names = os.listdir(cache_dir)
    except OSError:
        return None
    ranked = []
    for name in names:
        d = os.path.join(cache_dir, name)
        r = read_ratings(d)
        if not r or r.get("provider") != provider or r.get("subject") != subject:
            continue
        a, rej = int(r.get("approvals", 0)), len(r.get("rejections", []))
        glb = os.path.join(d, "mesh.glb")
        if a < 1 or not os.path.isfile(glb) or os.path.getsize(glb) == 0:
            continue
        ranked.append((wilson_lower_bound(a, rej), a, os.path.getmtime(os.path.join(d, RATINGS)), d))
    return max(ranked)[3] if ranked else None
