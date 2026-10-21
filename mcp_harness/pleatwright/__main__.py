"""Pleatwright from the command line.

    python -m pleatwright author "a dog" --out DIR [--open]
    python -m pleatwright fold DIR/tree.json --out DIR [--layout auto|symmetric|smaller]
    python -m pleatwright run "a dog" --out DIR [--open]

`author`: text -> concept image -> mesh (mesh_acquire) -> VLM tree
(gated_pipeline), paused for a human after every round. `fold`: tree ->
Pleatwright -> DIR/<Subject>_<grid>/ with the four files of COrigami's
released samples. `run`: both.

Exit codes: 0 done; 1 the review was quit (or stdin closed), or a Pleatwright
stage failed; 2 the mesh provider failed; 3 the LLM client could not be
configured (e.g. no API key) -- checked BEFORE the mesh is requested.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import shutil
import subprocess
import sys
import threading


class MeshError(Exception):
    """The mesh provider failed (quota, Space down, empty mesh, timeout)."""


class ConfigError(Exception):
    """The LLM client could not be built (no API key, unknown provider)."""


PROMPT = ("\n[a] approve   [q] quit   or type what is wrong with the tree: ")
LAYOUT_PROMPT = "\n[a] accept recommendation   [s] symmetric   [m] smaller   [q] quit: "


def _subject(prompt: str, guess: str | None) -> str:
    def words(text):
        return [w for w in re.findall(r"[a-z]+", (text or "").lower())
                if w not in ("a", "an", "the", "origami")]
    return "_".join(words(prompt)[:3]) or (words(guess) or ["tree"])[0]


def tree_file(state: dict, prompt: str) -> dict:
    """The authored tree in the artifact-fixture schema `pleatwright` reads."""
    t = state["tree"]
    subject = _subject(prompt, state.get("subject_guess"))
    return {"roll": subject, "subject": subject,
            "subject_guess": t.get("subject_guess"),
            "nodes": t["nodes"], "pairs": t.get("pairs") or [],
            "leaves": t.get("leaves") or [], "readings": t.get("readings") or [],
            "source": f"python -m pleatwright author {prompt!r}"}


def _show(state: dict, work: str, open_images: bool) -> None:
    print("\n" + (state.get("summary") or state.get("note") or ""))
    for p in (os.path.join(work, "mesh_views.png"), state.get("sheet_png")):
        if p and os.path.exists(p):
            print(f"  figure: {p}")
            if open_images and sys.platform == "darwin":
                subprocess.run(["open", p], check=False)


def _dump(obj, path: str) -> None:
    with open(path, "w") as f:
        json.dump(obj, f, indent=1)


def _client(model: str | None = None):
    import env_config
    import llm_client
    env_config.load_env()
    os.environ.setdefault("LLM_MAX_TOKENS", "64000")
    try:
        return llm_client.LLMClient.from_env(model)
    except ValueError as e:            # no API key, unknown provider, bad number
        raise ConfigError(str(e)) from e


async def _ask(ask, prompt: str) -> str:
    """`ask(prompt)` on a DAEMON thread, awaited from the review loop.

    Not `asyncio.to_thread`: its worker is non-daemon, and a worker blocked in
    input() is joined at exit, so Ctrl-C at the prompt hung until Enter was
    pressed (measured under a pty: > 6 s versus 0.06 s)."""
    loop = asyncio.get_running_loop()
    fut = loop.create_future()

    def settle(ok, value):
        if not fut.done():
            (fut.set_result if ok else fut.set_exception)(value)

    def work():
        try:
            r = ask(prompt)
        except StopIteration as e:     # cannot be set on a Future
            loop.call_soon_threadsafe(settle, False, RuntimeError(repr(e)))
        except BaseException as e:     # noqa: BLE001 -- EOFError is a quit
            loop.call_soon_threadsafe(settle, False, e)
        else:
            loop.call_soon_threadsafe(settle, True, r)
    threading.Thread(target=work, daemon=True).start()
    return await fut


def author(prompt: str, out_dir: str, *, ask=input, client=None,
           open_images: bool = False) -> str | None:
    import mesh_acquire
    client = client or _client()       # a config error surfaces before the mesh
    work = os.path.join(out_dir, "author")
    os.makedirs(work, exist_ok=True)
    try:
        glb = mesh_acquire.acquire_mesh(prompt)
    except (RuntimeError, TimeoutError, ValueError) as e:
        raise MeshError(str(e)) from e
    shutil.copyfile(glb, os.path.join(work, "mesh.glb"))
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        c = os.path.join(os.path.dirname(glb), "concept" + ext)
        if os.path.exists(c):
            shutil.copyfile(c, os.path.join(work, "concept" + ext))
    # ONE event loop for the whole review: the client's connection pool binds
    # to the first loop it is used in, and a request from a later loop fails
    # on the closed one and is silently RETRIED by the SDK -- billed twice.
    return asyncio.run(_review(prompt, out_dir, work, client=client, ask=ask,
                               open_images=open_images))


async def _review(prompt, out_dir, work, *, client, ask, open_images):
    import gated_pipeline as GP
    state = await GP.start(os.path.join(work, "mesh.glb"), client=client, out_dir=work)
    while True:
        _dump(state, os.path.join(work, "state.json"))
        _show(state, work, open_images)
        try:
            answer = (await _ask(ask, PROMPT)).strip()
            while not answer:               # an empty line spends no revision
                answer = (await _ask(ask, PROMPT)).strip()
        except EOFError:                    # stdin closed: treat as quit
            return None
        if answer.lower() in ("q", "quit"):
            return None
        if answer.lower() in ("a", "approve", "y", "yes") and state["status"] == "awaiting_review":
            state = await GP.resume(state, "approve", client=client, out_dir=work)
            _dump(state, os.path.join(work, "state.json"))
            path = os.path.join(out_dir, "tree.json")
            _dump(tree_file(state, prompt), path)
            print(f"\ntree written: {path}")
            return path
        if answer.lower() in ("a", "approve", "y", "yes"):
            print("this round failed, so there is nothing to approve; describe a fix or quit")
            continue
        state = await GP.resume(state, "revise", answer, client=client, out_dir=work)


def choose_layout(opts, explanation: str, ask=input) -> str | None:
    """Show both packed layouts and ask which to fold; None = quit (or EOF)."""
    print(f"\nTwo layouts fit this model on the sheet:\n"
          f"  symmetric: grid {opts.symmetric.layout.N}\n"
          f"  smaller:   grid {opts.smaller.layout.N}  "
          f"(folds a model {float(opts.gain):.2f}x larger from the same sheet)\n"
          f"Recommended: {opts.recommended}\n\n{explanation}")
    while True:
        try:
            answer = ask(LAYOUT_PROMPT).strip().lower()
        except EOFError:
            return None
        if answer in ("a", "y", "yes", "approve"):
            return opts.recommended
        if answer in ("s", "symmetric"):
            return "symmetric"
        if answer in ("m", "smaller"):
            return "smaller"
        if answer in ("q", "quit"):
            return None


def _layout_explanation(opts) -> str:
    """The VLM's note on the trade-off, from a FRESH client (the author's was
    bound to a closed loop; reusing it makes the SDK retry and bill twice).
    Any failure falls back to the template: it never blocks the fold."""
    import layout_explain
    summary, subject, pairs = opts.summary(), opts.sf.name, opts.sf.pairs
    try:
        client = _client()
    except ConfigError:
        return layout_explain.template_explanation(summary, subject, pairs)
    return asyncio.run(layout_explain.explain(client, summary, subject, pairs))


def fold(tree_path: str, out_dir: str, *, layout: str = "auto",
         chosen_by: str = "flag", options=None) -> int:
    from pleatwright import pipeline
    try:
        rec = pipeline.run(tree_path, out_dir, verbose=True, layout=layout,
                           chosen_by=chosen_by, options=options)
    except pipeline.StageError as e:
        c = e.__cause__ or e
        print(f"pleatwright failed at stage '{e.stage}': "
              f"{type(c).__name__}: {c}", file=sys.stderr)
        return 1
    if "failure" in rec:
        print(f"pleatwright failed at stage '{rec['failure']}'", file=sys.stderr)
        return 1
    print(f"\nmodel written: {rec['folder']}")
    return 0


def main(argv=None, *, ask=input, client=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m pleatwright")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("author", "run"):
        p = sub.add_parser(name)
        p.add_argument("prompt")
        p.add_argument("--out", required=True)
        p.add_argument("--open", action="store_true")
    p = sub.add_parser("fold")
    p.add_argument("tree")
    p.add_argument("--out", required=True)
    p.add_argument("--layout", choices=("auto", "symmetric", "smaller"), default="auto",
                   help="auto folds the smaller unmirrored layout only when it makes "
                        "the model at least 10%% larger; it never asks")
    a = ap.parse_args(argv)
    if a.cmd == "fold":
        return fold(a.tree, a.out, layout=a.layout)
    try:
        path = author(a.prompt, a.out, ask=ask, client=client, open_images=a.open)
    except MeshError as e:             # mesh provider: quota, Space down, empty mesh
        print(f"mesh generation failed: {e}", file=sys.stderr)
        return 2
    except ConfigError as e:           # LLM client: no key, unknown provider
        print(f"LLM client configuration failed: {e}", file=sys.stderr)
        return 3
    if path is None:
        return 1
    if a.cmd != "run":
        return 0
    from pleatwright import pipeline
    try:
        opts = pipeline.pack_options(path)
    except Exception as e:             # same reporting as a failed fold
        print(f"pleatwright failed at stage 'packing': {type(e).__name__}: {e}",
              file=sys.stderr)
        return 1
    if opts.verdict != "ask":
        return fold(path, a.out, options=opts)
    choice = choose_layout(opts, _layout_explanation(opts), ask=ask)
    if choice is None:
        return 1
    return fold(path, a.out, layout=choice, chosen_by="user", options=opts)


if __name__ == "__main__":
    sys.exit(main())
