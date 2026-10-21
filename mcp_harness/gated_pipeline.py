"""The mesh -> tree pipeline, paused at a human.

WHY THE PAUSE IS A RETURN VALUE. Every other human-in-the-loop point in this
repository is prompt discipline: the agent is told to propose and wait, and
nothing checks that it did. Two defect classes have reached a finished-looking
tree here -- inverted limbs and fused limbs -- and BOTH were caught by a person
looking at a picture after every numeric metric passed. A gate that matters
cannot be a sentence in a prompt, so `start()` stops and returns, and `resume()`
carries the human's answer back in.

That also makes the whole loop testable with a fake client and no human, which
prompt discipline never is.

NOTHING IS COMPILED BEFORE REVIEW. The tree goes to Pleatwright only AFTER the
human approves it: `start()` authors a tree, draws it and stops; `resume(...,
"approve")` is a state change and returns the approved tree for the compiler to
take from there.

⚠ ONLY ONE OF THOSE TWO DEFECTS IS VISIBLE IN THE PICTURE. An inverted tree is
obvious the moment it is drawn. A FUSED pair is not: the horse whose hind legs
"only separate at the hoof" draws as a plausible horse and lists the same six
flaps as a correct one. So the fused case is disclosed in WORDS, by
`summarise()`, from `pair_fusion`'s validated ranking -- see C1 there.
"""
from __future__ import annotations

import json
import os

import tree_authoring as TA
import tree_contract
import vlm_render

#: Rounds of `validate_tree` repair inside ONE authoring attempt.
#:
#: ⚠ BILLED TURNS ARE NOT ROUNDS. One round spends between one and
#: MAX_VALIDATE + 1 = 3 authoring calls, and each re-uploads the mesh render
#: (this endpoint has no prompt caching). Rounds are not capped: the human
#: decides when to stop revising (the 3-revision cap was removed 2026-10-11).
MAX_VALIDATE = 2

#: Spec §7, and NOT a guess. Measured 2026-09-09 on this corpus: the bat
#: truncated at EXACTLY 32,000 completion tokens and returned no tree, then
#: finished in 31,059 on a re-run -- these trees sit on that ceiling. The
#: parent spec measured the cost of the 4096 default directly:
#: "LLM_MAX_TOKENS 4096 -> 32000 | 6/27 -> 27/27 cells produced a tree".
#: `llm_client.LLMConfig.from_env` defaults to 4096, so an operator running
#: `start()` in a plain environment would lose roughly three subjects in four
#: to a truncation whose note never named the cause.
REQUIRED_MAX_TOKENS = 64000


def limb_splits(tree_nodes, symmetric_pairs, names) -> tuple[list, list]:
    """Every declared pair's branch fraction, WORST FIRST, under its own name.

    Returns `(rows, unscored)` where a row is `(name_a, name_b, fraction)`.

    ⚠ THIS IS THE GATE'S ONLY CHANNEL FOR THE FUSED-LIMB DEFECT. `pair_fusion`
    ships a ranking validated against the three subjects the owner flagged by
    eye, and its own module docstring says verbatim: "The human approval gate
    looks at the worst-ranked pairs." This is that gate. Measured on the
    committed `horse` against a fused copy of it, everything else the human
    sees is IDENTICAL -- same six flaps, same figure -- while the ranking moves
    0.6364 -> 0.0714.

    ⚠ NO THRESHOLD, ON PURPOSE. `pair_fusion` shipped without one because a
    first draft's `FUSED_BELOW = 0.5` scored TP 3 / FP 6 on this corpus, and
    fitting a cutoff to three labelled positives is this project's named
    recurring failure mode. The ORDER is what was validated, so the order is
    what is reported.
    """
    import pair_fusion
    f = pair_fusion.score_fusion(tree_nodes, symmetric_pairs)
    rows = [(names.get(r["pair"][0], r["pair"][0]),
             names.get(r["pair"][1], r["pair"][1]),
             r["branch_fraction"]) for r in f["pairs"]]
    unscored = [[names.get(i, i) for i in p] for p in f["unscored"]]
    return rows, unscored


def summarise(tree, leaf_names, *, splits=None, unscored_pairs=None,
              dropped_pairs=None, figure_note=None) -> str:
    """What the human reads beside the figure.

    Written for a person, not a log. One clause carries the disclosure burden,
    because it has no other channel:

    * the LIMB SEPARATION ranking -- a fused pair draws as a plausible animal
      and lists the correct flaps, so the figure cannot show it.

    `splits` / `unscored_pairs` come from `limb_splits()`; `dropped_pairs` from
    `tree_authoring.leaf_pairs()`. All three default to None meaning "the
    caller did not look", which reads differently from `[]` meaning "the caller
    looked and there were none" -- the summary must never imply a check that
    nobody ran.
    """
    guess = tree.get("subject_guess") or "this mesh"
    n = len(leaf_names)
    lines = [f"Read as: {guess}",
             f"{n} flap{'' if n == 1 else 's'}: " + ", ".join(leaf_names)]

    if splits:
        shown = ", ".join(f"{a}/{b} {v:.2f}" for a, b, v in splits[:3])
        of = f" of {len(splits)}" if len(splits) > 3 else ""
        lines.append(
            f"Limb separation, lowest first ({min(3, len(splits))}{of}): "
            + shown
            + " -- 0.00 means the pair is ONE limb that forks at the tip, "
              "1.00 means two independent limbs. This is a ranking, not a "
              "test: there is no pass mark, so read the lowest one against "
              "the animal.")
    elif splits is not None and not unscored_pairs and not dropped_pairs:
        lines.append("No symmetric pairs were declared, so no left/right limb "
                     "was checked for being one forked limb.")
    if unscored_pairs:
        lines.append(
            f"{len(unscored_pairs)} declared pair(s) could NOT be scored for "
            "limb separation: "
            + ", ".join("/".join(str(x) for x in p) for p in unscored_pairs)
            + ". That is a gap in the check, not a pass.")
    if dropped_pairs:
        lines.append(
            f"WARNING: {len(dropped_pairs)} declared symmetric pair(s) were "
            "DROPPED because they do not join two flaps: "
            + ", ".join("/".join(str(x) for x in p) for p in dropped_pairs)
            + ". The compiler receives NO mirror constraint for them.")

    if figure_note:
        lines.append(f"WARNING: {figure_note} You are being asked about a tree "
                     "you cannot see; the lines above are all there is.")
    lines.append("Does this read as the animal? Reply 'yes' to continue, or "
                 "say what is wrong with it.")
    return "\n".join(lines)


def _blank_state(mesh_path) -> dict:
    return {"status": "failed", "round": 0, "mesh_path": mesh_path,
            "subject_guess": None, "tree": None, "metric_tree": None,
            "sheet_png": None, "summary": "", "history": [], "note": None,
            "revisions_authored": 0}


def _fail(state, note) -> dict:
    """Mark this round failed and drop every artefact of the PREVIOUS one.

    ⚠ FOUND IN REVIEW 2026-09-10: a revision whose authoring truncated left
    `status="failed"` and `round=1` sitting beside round 0's `tree`,
    `sheet_png` and summary -- and `resume(that_state, "approve")` then
    returned `approved`, SHIPPING THE PREVIOUS ROUND'S TREE for a revision that
    never happened. Two things close that: everything derived
    from a tree is cleared here so `round` and `sheet_png` cannot disagree, and
    `resume()` refuses to approve a failed state at all.

    `tree` itself is KEPT, and that is the one deliberate exception: the only
    sensible recovery is another `revise`, which needs the last tree that
    authored successfully to build on. `status == "failed"` is what says it
    belongs to an earlier round.
    """
    state.update({"status": "failed", "note": note, "metric_tree": None,
                  "sheet_png": None, "summary": ""})
    return state


def _assistant_tool_call(call) -> dict:
    """The assistant turn that SUBMITTED the rejected tree, replayed verbatim."""
    return {"role": "assistant", "content": None,
            "tool_calls": [{"id": call.id, "type": "function",
                            "function": {"name": call.function.name,
                                         "arguments": call.function.arguments}}]}


def _tool_result(call) -> dict:
    return {"role": "tool", "tool_call_id": call.id, "content": "received"}


#: The top-level `submit_tree` fields the schema types as arrays. A model sometimes
#: sends a nested array as a JSON-encoded STRING: measured 2026-10-11, Haiku 5.5 did
#: it to `nodes` on 1 in 8 authoring turns, under both tool_choice settings, and the
#: string was read character by character ("'str' object has no attribute 'get'").
_ARRAY_FIELDS = ("nodes", "leaves", "pairs", "readings")


class _StringFields(Exception):
    """Array fields that arrived as strings which do not decode to arrays."""

    def __init__(self, fields):
        super().__init__(", ".join(fields))
        self.fields = fields


def _decode_string_fields(tree):
    """Decode array fields sent as JSON strings, in place. Returns the tree and
    the fields that are strings but do not decode to an array.

    The string may also carry the REST of the object after the array -- the shape
    captured live: `[...],"leaves":[...],"pairs":[...],"notes":"..."}]` inside
    `nodes`. The leading array is the field; the spilled `,"key": value` members
    are decoded as an object and fill any field the arguments lack."""
    if not isinstance(tree, dict):
        return tree, []
    dec = json.JSONDecoder()
    bad = []
    for k in _ARRAY_FIELDS:
        v = tree.get(k)
        if not isinstance(v, str):
            continue
        try:
            d, end = dec.raw_decode(v.strip())
        except ValueError:
            d, end = None, 0
        if not isinstance(d, list):
            bad.append(k)
            continue
        tree[k] = d
        rest = v.strip()[end:].lstrip()
        if rest.startswith(","):
            try:
                spilled, _ = dec.raw_decode("{" + rest[1:])
            except ValueError:
                spilled = {}
            for key, val in spilled.items() if isinstance(spilled, dict) else ():
                tree.setdefault(key, val)
    return tree, bad


async def _author(client, mesh_png, prior_tree, feedback):
    """One authoring turn, with up to MAX_VALIDATE contract repairs.

    ⚠ On a revision the model is given the previous tree AS JSON and the
    human's words -- never the rendered figure. Showing a model its own picture
    was measured WORSE than no review at all (MAE 0.53 against 0.29), so the
    only image it ever receives is the mesh render. This function must not
    become the loophole.

    ⚠ A VALIDATION FAILURE APPENDS THREE MESSAGES, NOT ONE, and the shape is
    copied from `evidence/.../scripts/run_rule6.py:87-89` -- the script that
    produced `rule6_raw.json` and every figure this branch quotes. Appending
    only the user message left the history as `['user','user','user']`: the
    model was told "validate_tree REJECTED that tree" while the tree it
    submitted was not in its context at all, so it re-authored blind instead of
    repairing, on a message shape no other call site in this repo produces.
    """
    # BEFORE the first billed call, so a misconfigured budget costs nothing.
    # Read off the CLIENT, not the environment: a test's fake client exposes no
    # `max_tokens` and must not be gated by an operator setting it never reads.
    #
    # ⚠ ALSO WORTH CLOSING (S5 follow-ups), CLOSED AS A DOCSTRING: a `client`
    # that WRAPS `llm_client.LLMClient` (rather than being one) and does not
    # forward `max_tokens` makes `getattr` return `None`, which this check
    # reads as "unknown, do not gate" -- identical to a fake test client with
    # no budget concept at all. There is no signal that the check was skipped
    # rather than passed. `llm_client.py` is outside this branch's file scope
    # (see the S5 follow-ups file list), so fixing the wrapper contract itself
    # is left for whoever adds the first such wrapper; this note is so that
    # person does not rediscover the silent skip from scratch.
    budget = getattr(client, "max_tokens", None)
    if isinstance(budget, int) and budget < REQUIRED_MAX_TOKENS:
        return None, (
            f"LLM_MAX_TOKENS is {budget}; this pipeline needs at least "
            f"{REQUIRED_MAX_TOKENS}. Measured 2026-09-09: the bat truncated at "
            "exactly 32,000 completion tokens and returned no tree. Set "
            f"LLM_MAX_TOKENS={REQUIRED_MAX_TOKENS} and run again -- no "
            "authoring turn was spent.")

    import llm_client
    ask = "Author the metric tree for the mesh in this image."
    if prior_tree is not None:
        ask = ("You previously authored this tree for the mesh in this image:\n"
               + json.dumps({"nodes": prior_tree["nodes"],
                             "pairs": prior_tree.get("pairs") or []}, indent=1)
               + "\n\nA human reviewed the stick figure and said:\n"
               + f"\"{feedback}\"\n\n"
               + "Re-author the COMPLETE tree, fixing what they described. "
                 "Keep everything they did not complain about.")
    msgs = [llm_client.user_message_with_images(ask, [mesh_png])]
    tree = note = None
    for _ in range(MAX_VALIDATE + 1):
        r = await client.run_turn(TA.SYSTEM, msgs, TA.TOOL)
        if not r.tool_calls:
            said = " ".join((getattr(r, "text", "") or "").split())
            if said:
                # Show what it said: the human can reword, or see it misread them.
                said = said if len(said) <= 240 else said[:240] + "…"
                return None, ("the model answered in text instead of submitting a tree "
                              f"(finish_reason: {r.finish_reason}): \u201c{said}\u201d")
            return None, f"the model returned no tree (finish_reason: {r.finish_reason})"
        call = r.tool_calls[0]
        try:
            tree = json.loads(call.function.arguments)
        except ValueError as e:
            # ⚠ THE OTHER FACE OF TRUNCATION, and the likelier one. An
            # OpenAI-compatible endpoint that hits the completion cap mid-tool-
            # call commonly returns finish_reason "length" WITH a partial tool
            # call whose `arguments` string is cut off, rather than with no
            # tool call at all. Unguarded, `json.loads` raised straight out of
            # `start()` -- and this module's whole contract, and spec §7, is
            # that failures come back as a state.
            return None, (
                "the model's tool call did not parse as JSON (finish_reason: "
                f"{r.finish_reason}): {e}. A truncated `arguments` string is "
                "what LLM_MAX_TOKENS truncation looks like on this endpoint.")
        tree, stringy = _decode_string_fields(tree)
        try:
            if stringy:
                raise _StringFields(stringy)
            nodes = TA.to_tuples(tree)
            keep, _dropped = TA.leaf_pairs(tree, TA.leaves_of(nodes))
            tn, sp, _ = TA.metric_tree(nodes, keep)
            errs = tree_contract.check(tn, sp).get("errors", [])
        except KeyError as e:
            # The single most common authoring failure on 2026-09-13 (4 rolls):
            # the JSON parsed but carried no `nodes` list -- typically the tree
            # wrapped one level deep, or a field renamed. The bare KeyError text
            # (`'nodes'`) told the model nothing it could act on; name the
            # field, the keys it sent, and the keys the schema requires.
            required = TA.TOOL[0]["function"]["parameters"]["required"]
            got = ", ".join(tree.keys()) if isinstance(tree, dict) else type(tree).__name__
            errs = [f"missing field {e}: the submit_tree arguments carried the keys "
                    f"[{got}] but the schema requires [{', '.join(required)}] at the "
                    "TOP LEVEL -- do not wrap the tree in another object"]
        except _StringFields as e:
            errs = [f"`{k}` must be a JSON array{' of node objects' if k == 'nodes' else ''}, "
                    "not a string -- send the array itself, not text or JSON inside a string"
                    for k in e.fields]
        except Exception as e:                              # noqa: BLE001
            errs = [f"unbuildable: {e}"]
        if not errs:
            return tree, None
        note = "; ".join(errs)
        msgs = msgs + [_assistant_tool_call(call), _tool_result(call),
                       {"role": "user", "content":
                        "validate_tree REJECTED that tree:\n- "
                        + "\n- ".join(errs)
                        + "\n\nFix every error and re-submit the complete tree."}]
    return None, f"the tree still failed validation: {note}"


def _grid(v):
    """A length back in GRID units, printed the way the model wrote it."""
    r = round(float(v), 2)
    return int(r) if r == int(r) else r


def _authored_tuples(nodes):
    """The authored tree, drawable: (name, parent, direction, length) tuples,
    lengths in the model's own grid units (what the human checks against the
    mesh render). `_topo` still sorts parents first before drawing."""
    return [(name, parent, direction, _grid(length))
            for name, parent, direction, length in nodes]


def _topo(draw):
    """Parents before children, stably.

    ⚠ REMOVES AN UNDOCUMENTED INVARIANT RATHER THAN RESTATING IT.
    `vlm_render.positions` reads `pos[parent]` as it walks the list, so it
    requires every parent to appear before its children -- and the authored
    list's order is whatever the model wrote. A child-first list reproduces
    `KeyError: 'neck'` out of `render_tree_sheet`. Sorting here is cheap and
    the invariant then cannot be violated.

    A node whose parent is missing, or a cycle, is left in place rather than
    dropped: the caller's guard turns the resulting failure into a state, and
    silently discarding part of the tree the human is judging would be worse
    than not drawing it.
    """
    known = {t[0] for t in draw}
    placed, out, pending = set(), [], list(draw)
    while pending:
        rest, moved = [], False
        for t in pending:
            if t[1] is None or t[1] in placed or t[1] not in known:
                out.append(t)
                placed.add(t[0])
                moved = True
            else:
                rest.append(t)
        pending = rest
        if not moved:
            out.extend(pending)
            break
    return out


def _build(tree):
    """Authored tree -> (nodes, leaf_names, dropped, tn, sp, names), for
    `_draft`. Only the pairs whose both ends are leaves reach the metric tree;
    the rest come back as `dropped` so the summary can name them."""
    nodes = TA.to_tuples(tree)
    leaf_names = TA.leaves_of(nodes)
    keep, dropped = TA.leaf_pairs(tree, leaf_names)
    tn, sp, names = TA.metric_tree(nodes, keep)
    return nodes, leaf_names, dropped, tn, sp, names


async def _draft(state, *, client, out_dir, feedback=""):
    os.makedirs(out_dir, exist_ok=True)
    mesh_png = vlm_render.render_mesh_views(
        state["mesh_path"], os.path.join(out_dir, "mesh_views.png"))["png"]

    tree, note = await _author(client, mesh_png, state.get("tree"), feedback)
    if tree is None:
        return _fail(state, note)

    try:
        nodes, leaf_names, dropped, tn, sp, names = _build(tree)
    except Exception as e:                                  # noqa: BLE001
        return _fail(state, f"the metric tree could not be built from the "
                            f"authored tree: {type(e).__name__}: {e}")

    # ⚠ NOTHING AFTER THE AUTHORING TURN MAY RAISE. An exception out of
    # `start()` loses the authored tree AND the billed authoring turn that
    # produced it, and this module's contract is that a failure comes back as
    # a state. A figure that cannot be drawn still hands over the words.
    sheet = os.path.join(out_dir, f"tree_round{state['round']}.png")
    figure_note = None
    try:
        draw = _topo(_authored_tuples(nodes))
        vlm_render.render_tree_sheet(
            draw, sheet,
            title=f"{tree.get('subject_guess', '')}  —  round {state['round']}")
    except Exception as e:                                  # noqa: BLE001
        sheet = None
        figure_note = (f"the figure could not be drawn "
                       f"({type(e).__name__}: {e}).")

    # The ranking scores the AUTHORED tree, and the figure above draws the
    # same authored tree, so the words and the picture describe one thing.
    try:
        splits, unscored = limb_splits(tn, sp, names)
    except Exception as e:                                  # noqa: BLE001
        # ⚠ ALSO WORTH CLOSING (S5 follow-ups): this used to be a single
        # synthetic entry `[[f"limb separation could not be scored: {e}"]]`
        # regardless of how many pairs were actually declared, so the summary
        # always said "1 declared pair(s) could NOT be scored" even when `sp`
        # held several. Report every declared pair by name instead -- the
        # count in the disclosure is then the true count -- and fall back to
        # the exception text only when nothing was declared at all, so a
        # crash with zero pairs is still visible rather than silently dropped.
        splits = None
        unscored = [[names.get(a, a), names.get(b, b)] for a, b in sp] or \
            [[f"limb separation could not be scored: {e}"]]

    # Counts a REVISION only once it has actually produced a tree (a truncated
    # or crashed round is not one). Round 0 (this function's call from
    # `start()`) is not a revision and must not be counted here.
    revisions_authored = state.get("revisions_authored", 0)
    if state["round"] > 0:
        revisions_authored += 1

    state.update({"status": "awaiting_review", "tree": tree,
                  "subject_guess": tree.get("subject_guess"),
                  "metric_tree": {"tree_nodes": tn, "symmetric_pairs": sp,
                                  "names": {str(k): v for k, v in names.items()}},
                  "sheet_png": sheet,
                  "summary": summarise(tree, leaf_names, splits=splits,
                                       unscored_pairs=unscored,
                                       dropped_pairs=dropped,
                                       figure_note=figure_note),
                  "revisions_authored": revisions_authored,
                  "note": None})
    return state


async def start(mesh_path, *, client, out_dir) -> dict:
    """Draft a tree, draw it, and STOP for a human."""
    return await _draft(_blank_state(mesh_path), client=client,
                        out_dir=out_dir)


async def resume(state, verdict, feedback="", *, client, out_dir) -> dict:
    """Carry the human's answer back into the pipeline.

    `verdict` is "approve" or "revise". Approving is a state change only; the
    tree is compiled by Pleatwright after this returns.

    ⚠ THE TERMINAL-STATE GUARDS LIVE HERE, NOT IN A CALLER. The design's whole
    stated rationale is that "the ordering is a property of the code rather
    than of a prompt", and the caller is the CLI (`python -m pleatwright`);
    delegating the guard to it would reintroduce exactly the
    prompt-discipline pattern the spec consciously rejected. Reachable nonsensical states
    were measured before these existed: `resume(approved, "revise")` silently
    un-approved, and `resume(failed, "approve")` shipped the PREVIOUS round's
    tree. A third, approving an `exhausted` state whose note still said the
    last critique was not satisfied, went with the 3-revision cap (2026-10-11):
    an `exhausted` state saved before then resumes like a review, and
    approving clears its stale note.

    `revise` from `failed` is allowed ON PURPOSE, and is the only terminal
    status that permits anything. A truncated or crashed round is recoverable
    -- the tree that last authored successfully is still in the state, and
    re-authoring from it with the human's words is the obvious next move -- so
    it is made explicit here rather than left as a side effect of an unguarded
    branch.
    """
    state = json.loads(json.dumps(state))          # never mutate the caller's
    if verdict not in ("approve", "revise"):
        raise ValueError(f"verdict must be 'approve' or 'revise', got {verdict!r}")
    # `exhausted` (a revision cap that no longer exists) is only ever read
    # from a state saved before 2026-10-11; it resumes like a review.
    if state["status"] == "approved":
        raise ValueError(f"cannot resume a {state['status']} state")
    if state["status"] == "failed" and verdict == "approve":
        raise ValueError(
            "cannot approve a failed state: nothing in this round was "
            "authored, and its figure belongs to an earlier round. "
            "Use 'revise' to re-author, or start over.")

    if verdict == "approve":
        state["status"] = "approved"
        state["note"] = None                       # an old `exhausted` note is stale now
        state["history"].append({"round": state["round"], "verdict": "approve",
                                 "feedback": feedback})
        return state

    state["history"].append({"round": state["round"], "verdict": "revise",
                             "feedback": feedback})
    state["round"] += 1
    return await _draft(state, client=client, out_dir=out_dir,
                        feedback=feedback)
