# Strain-Oracle Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pipe the Model tab's p90 strain verdict back to the agent over the websocket so a physically unrealizable pose is retried autonomously (capped) and a passing pose becomes positive context.

**Architecture:** Approach A from the spec (`docs/superpowers/specs/2026-07-02-strain-oracle-loop-design.md`): the browser sends a new `oracle_verdict` ws frame correlated to a fold `id`; `web/server.py` appends a `[STRAIN ORACLE]`-prefixed user-role message and, for rejects of shaped folds with budget left, runs a normal agent turn on the existing queue machinery. The frontend auto-switches to the Model tab on shaped folds so the GPU solver (which freezes offscreen) actually produces verdicts.

**Tech Stack:** TypeScript/React + vitest (`web/frontend`), FastAPI websocket + pytest (`web/`), prompt pin tests (`mcp_harness`).

## Global Constraints

(Verbatim from the spec; every task's requirements include these.)

- Fold frames gain exactly `id` (int, per-connection counter starting at 1), `shaped` (bool: ops were applied to display_json), `strain_max` (float from env `IDE_STRAIN_MAX`, default `0.15`, read at frame-send time).
- Client→server verdict frame: `{type: "oracle_verdict", fold_id: <int>, verdict: "pass"|"reject", p90: <float>, reason: <string>}`. Malformed frames are ignored; a `fold_id` that is not the latest served fold is dropped with one stderr note.
- Oracle message: user-role, prefixed exactly `[STRAIN ORACLE] `, appended to `messages` AND echoed to the browser as an `assistant` frame.
- Retry policy: reject + latest fold is shaped + `retries_used < IDE_ORACLE_RETRIES` (int env, default 1) → run one agent turn. Pass, unshaped fold, or exhausted budget → no turn. `retries_used` resets to 0 ONLY when a shaped fold is served by a USER-initiated turn — folds served by oracle-retry turns must NOT reset it (otherwise every retry refills its own budget and a never-passing pose loops forever).
- With no browser sending verdicts (tests, headless), behavior is byte-identical to today; the prompt path's frame flow changes only by the three new fold-frame fields.
- `extraction.ts`'s capture promise type stays `Promise<RawMesh>`; the verdict surfaces via a controller-level `onVerdict` callback; the threshold is per-`start()` (`maxStrain`, default `MAX_STRAIN` = 0.15).
- Auto-switch: the Model tab is selected when a fold frame with `shaped: true` arrives; unshaped folds never switch tabs.
- Existing prompt pins (incl. `"ONLY AFTER THE USER APPROVES"`) must pass unmodified.
- Backend/web tests: `cd <repo>/mcp_harness && .venv/bin/python -m pytest <paths> -q` and (repo root) `mcp_harness/.venv/bin/python -m pytest web/tests -q`. Frontend tests: `cd <repo>/web/frontend && npm test`.

---

### Task 1: `extraction.ts` — `onVerdict` callback + per-start `maxStrain`

**Files:**
- Modify: `web/frontend/src/extraction.ts`
- Test: `web/frontend/src/extraction.test.ts`

**Interfaces:**
- Consumes: nothing new.
- Produces (Task 2 relies on these exact names):
  - `export type OracleVerdict = { verdict: "pass" | "reject"; p90: number; reason: string }`
  - `createExtractionController(opts)` gains optional `onVerdict?: (v: OracleVerdict) => void` — invoked exactly once per run's FINAL outcome (never on intermediate high-strain re-capture attempts).
  - `start(fold: unknown, maxStrain?: number): Promise<RawMesh>` — threshold for THIS capture (default `MAX_STRAIN`).

- [ ] **Step 1: Write the failing tests**

Append to `web/frontend/src/extraction.test.ts` (and add `onVerdict` plumbing to the `make()` helper):

In `make()`, add a verdict spy — replace the helper's controller construction with:

```typescript
function make(opts: { maxAttempts?: number } = {}) {
  const post = vi.fn();
  const onVerdict = vi.fn();
  // Keep EVERY settle callback ever registered (not just the latest) so
  // a test can fire an old/stale one after a newer start() has run.
  const settleFns: Array<() => void> = [];
  const c = createExtractionController({
    post,
    settle: (fn) => { settleFns.push(fn); },
    posePercent: 90,
    onVerdict,
    ...opts,
  });
  return {
    post,
    onVerdict,
    c,
    runSettle: () => settleFns[settleFns.length - 1]?.(),
    runSettleAt: (i: number) => settleFns[i]?.(),
    settleCount: () => settleFns.length,
  };
}
```

Append a new describe block:

```typescript
describe("onVerdict", () => {
  const goodGeom = {
    type: "foldedGeometry" as const,
    vertices_coords: [[0, 0, 0], [1.01, 0, 0], [0, 1, 0]],
    faces_vertices: [[0, 1, 2]],
    flat_coords: [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
  };
  const badGeom = {
    type: "foldedGeometry" as const,
    vertices_coords: [[0, 0, 0], [2, 0, 0], [0, 1, 0]],
    faces_vertices: [[0, 1, 2]],
    flat_coords: [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
  };

  it("fires pass exactly once with the measured p90", async () => {
    const { c, onVerdict, runSettle } = make();
    const p = c.start({});
    c.receive({ type: "ready" });
    runSettle();
    c.receive(goodGeom);
    await p;
    expect(onVerdict).toHaveBeenCalledTimes(1);
    const v = onVerdict.mock.calls[0][0];
    expect(v.verdict).toBe("pass");
    expect(v.p90).toBeCloseTo(0.01, 5);
    expect(v.reason).toMatch(/converged/);
  });

  it("fires reject once at max attempts, not on intermediate retries", async () => {
    const { c, onVerdict, runSettle } = make({ maxAttempts: 2 });
    const p = c.start({});
    c.receive({ type: "ready" });
    runSettle();
    c.receive(badGeom);                       // attempt 1: re-capture, NO verdict
    expect(onVerdict).not.toHaveBeenCalled();
    runSettle();
    c.receive(badGeom);                       // attempt 2: final reject
    await expect(p).rejects.toThrow(/strain/);
    expect(onVerdict).toHaveBeenCalledTimes(1);
    const v = onVerdict.mock.calls[0][0];
    expect(v.verdict).toBe("reject");
    expect(v.p90).toBeCloseTo(1.0, 5);        // folded len 2 vs flat len 1
    expect(v.reason).toMatch(/strain/);
  });

  it("fires reject with p90 0 for non-strain failures (solver error)", async () => {
    const { c, onVerdict } = make();
    const p = c.start({});
    c.receive({ type: "error", message: "boom" });
    await expect(p).rejects.toThrow(/boom/);
    expect(onVerdict).toHaveBeenCalledWith(
      { verdict: "reject", p90: 0, reason: "boom" });
  });

  it("fires reject for empty geometry", async () => {
    const { c, onVerdict, runSettle } = make();
    const p = c.start({});
    c.receive({ type: "ready" });
    runSettle();
    c.receive({ type: "foldedGeometry", vertices_coords: [], faces_vertices: [] });
    await expect(p).rejects.toThrow(/empty/);
    expect(onVerdict).toHaveBeenCalledTimes(1);
    expect(onVerdict.mock.calls[0][0].verdict).toBe("reject");
  });

  it("start() honors a per-capture maxStrain", async () => {
    const { c, onVerdict, runSettle } = make({ maxAttempts: 1 });
    // goodGeom's p90 is 0.01 — passes the 0.15 default but must reject
    // against a stricter 0.005 threshold.
    const p = c.start({}, 0.005);
    c.receive({ type: "ready" });
    runSettle();
    c.receive(goodGeom);
    await expect(p).rejects.toThrow(/0.5%/);
    expect(onVerdict.mock.calls[0][0].verdict).toBe("reject");
  });
});
```

- [ ] **Step 2: Run to verify the new tests fail**

Run: `cd <repo>/web/frontend && npm test`
Expected: the new `onVerdict` describe block FAILS (unknown option / spy never called); all pre-existing tests still pass.

- [ ] **Step 3: Implement in `web/frontend/src/extraction.ts`**

Add the type and extend the controller. After the `MAX_CAPTURE_ATTEMPTS` export, add:

```typescript
// Final per-capture outcome for the browser->agent oracle channel (spec:
// 2026-07-02-strain-oracle-loop-design.md). Fired exactly once per run —
// intermediate high-strain re-captures are not verdicts.
export type OracleVerdict = {
  verdict: "pass" | "reject";
  p90: number;
  reason: string;
};
```

Change the `createExtractionController` opts and interface:

```typescript
export interface ExtractionController {
  start(fold: unknown, maxStrain?: number): Promise<RawMesh>;
  receive(msg: ExtractInbound): void;
}

export function createExtractionController(opts: {
  post: (m: ExtractOutbound) => void;
  settle: (fn: () => void) => void;
  posePercent: number;
  maxAttempts?: number;
  onVerdict?: (v: OracleVerdict) => void;
}): ExtractionController {
```

Inside the factory, add per-run threshold + last-measured strain state next to the existing `let` declarations:

```typescript
  let currentMaxStrain = MAX_STRAIN;
  let lastP90 = 0;
```

In `start`, set them:

```typescript
    start(fold, maxStrain) {
      runId += 1;
      const run = runId;
      currentMaxStrain = maxStrain ?? MAX_STRAIN;
      lastP90 = 0;
      return new Promise<RawMesh>((resolve, reject) => {
```

Replace the two strain-gate references to `MAX_STRAIN` in `receive` with `currentMaxStrain`, record `lastP90 = strain;` immediately after computing `strain`, and update the reject message to use the dynamic threshold:

```typescript
          const strain = edgeStrainP90(
            msg.vertices_coords, msg.flat_coords, msg.faces_vertices);
          lastP90 = strain;
          if (strain > currentMaxStrain) {
            if (attempt < maxAttempts) {
              const run = runId;
              opts.settle(() => {
                if (run !== runId) return; // stale run's timer: do nothing
                opts.post({ type: "getFoldedGeometry" });
              });
              return;
            }
            rejectMesh?.(new Error(
              `paper strain (p90) ${(strain * 100).toFixed(1)}% exceeds ` +
              `${currentMaxStrain * 100}% after ${attempt} captures — ` +
              `pose not physically realizable`));
            opts.onVerdict?.({ verdict: "reject", p90: strain,
              reason: `paper strain (p90) ${(strain * 100).toFixed(1)}% ` +
                      `exceeds ${currentMaxStrain * 100}%` });
            settleFinished();
            return;
          }
```

Fire the callback on every other terminal path — each snippet goes
immediately after the existing `rejectMesh?.(...)` / `resolveMesh?.(...)`
line of that path:

```typescript
// empty geometry path:
opts.onVerdict?.({ verdict: "reject", p90: lastP90,
  reason: "empty geometry from solver" });

// non-finite geometry path:
opts.onVerdict?.({ verdict: "reject", p90: lastP90,
  reason: "non-finite geometry from solver" });

// success path (after resolveMesh?.(...), before settleFinished()):
opts.onVerdict?.({ verdict: "pass", p90: lastP90,
  reason: `converged (${attempt} capture${attempt === 1 ? "" : "s"})` });

// solver-error path (msg.type === "error"):
opts.onVerdict?.({ verdict: "reject", p90: lastP90, reason: msg.message });
```

- [ ] **Step 4: Run the frontend suite**

Run: `cd <repo>/web/frontend && npm test`
Expected: PASS — all files, including every pre-existing extraction test unchanged.

- [ ] **Step 5: Commit**

```bash
cd <repo>
git add web/frontend/src/extraction.ts web/frontend/src/extraction.test.ts
git commit -m "feat(oracle): extraction controller emits final verdicts + per-capture threshold"
```

---

### Task 2: frontend wiring — fold-frame fields, auto-switch, verdict send

**Files:**
- Modify: `web/frontend/src/chat.ts`
- Modify: `web/frontend/src/CADViewer.tsx`
- Modify: `web/frontend/src/App.tsx`
- Test: `web/frontend/src/chat.test.ts`

**Interfaces:**
- Consumes (Task 1): `OracleVerdict`, `onVerdict` opt, `start(fold, maxStrain?)`.
- Produces: `FoldArtifact` gains `id?: number; shaped?: boolean; strainMax?: number`; `Frame`'s fold variant gains `id?: number; shaped?: boolean; strain_max?: number`; new pure helper `foldWantsModelTab(frame: Frame): boolean`; `CADViewer` prop `onVerdict?: (v: OracleVerdict) => void`. The outbound ws frame (sent by App): `{type: "oracle_verdict", fold_id, verdict, p90, reason}`.

- [ ] **Step 1: Write the failing tests**

Append to `web/frontend/src/chat.test.ts`:

```typescript
import { foldWantsModelTab } from "./chat";

describe("fold frame oracle fields", () => {
  it("applyFrame carries id/shaped/strainMax into the artifact", () => {
    const s = applyFrame(initialState, {
      type: "fold", filename: "model.fold", json: { a: 1 },
      display_json: { b: 2 }, id: 3, shaped: true, strain_max: 0.05,
    });
    expect(s.fold).toEqual({
      filename: "model.fold", json: { a: 1 }, displayJson: { b: 2 },
      id: 3, shaped: true, strainMax: 0.05,
    });
  });

  it("older fold frames without the new fields still apply", () => {
    const s = applyFrame(initialState, {
      type: "fold", filename: "model.fold", json: { a: 1 }, display_json: null,
    });
    expect(s.fold?.filename).toBe("model.fold");
    expect(s.fold?.shaped).toBeUndefined();
  });
});

describe("foldWantsModelTab", () => {
  it("true only for shaped fold frames", () => {
    expect(foldWantsModelTab({ type: "fold", filename: "f", json: {},
      display_json: {}, id: 1, shaped: true, strain_max: 0.15 })).toBe(true);
    expect(foldWantsModelTab({ type: "fold", filename: "f", json: {},
      display_json: {}, id: 1, shaped: false, strain_max: 0.15 })).toBe(false);
    expect(foldWantsModelTab({ type: "fold", filename: "f", json: {},
      display_json: {} })).toBe(false);
    expect(foldWantsModelTab({ type: "turn_end", ok: true })).toBe(false);
  });
});
```

(If `chat.test.ts` does not already import `applyFrame`/`initialState`, extend its existing import from `./chat`.)

- [ ] **Step 2: Run to verify they fail**

Run: `cd <repo>/web/frontend && npm test`
Expected: FAIL — `foldWantsModelTab` not exported; artifact lacks the new fields.

- [ ] **Step 3: Implement `chat.ts`**

Extend the fold frame variant and artifact:

```typescript
  | { type: "fold"; filename: string; json: unknown; display_json: unknown;
      id?: number; shaped?: boolean; strain_max?: number }
```

```typescript
export interface FoldArtifact {
  filename: string;
  json: unknown;         // the raw, validated hull (Download + JSON tab)
  displayJson?: unknown; // the squared copy for the 3D viewer
  id?: number;           // per-connection fold counter (oracle correlation)
  shaped?: boolean;      // shaping ops were applied to displayJson
  strainMax?: number;    // oracle threshold the server asked for
}
```

In `applyFrame`'s fold case:

```typescript
    case "fold":
      return { ...state,
        fold: { filename: frame.filename, json: frame.json,
                displayJson: frame.display_json, id: frame.id,
                shaped: frame.shaped, strainMax: frame.strain_max } };
```

Add the pure helper at the bottom:

```typescript
// A shaped fold should surface in the Model tab automatically: the GPU
// solver only runs while that tab is visible, and the oracle loop needs
// its verdict without waiting for a click (spec §2, "Capture arming").
export function foldWantsModelTab(frame: Frame): boolean {
  return frame.type === "fold" && frame.shaped === true;
}
```

- [ ] **Step 4: Implement `CADViewer.tsx` — verdict prop**

Change the component signature and thread the callback via a ref (the
controller memo is created once; the ref keeps the latest prop visible to
it):

```typescript
import {
  createExtractionController,
  type ExtractInbound,
  type ExtractOutbound,
  type OracleVerdict,
} from "./extraction";
```

```typescript
export default function CADViewer({ fold, onVerdict }: {
  fold: FoldArtifact | null;
  onVerdict?: (v: OracleVerdict) => void;
}) {
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const [shell, setShell] = useState<ShellMesh | null>(null);
  const [error, setError] = useState<string | null>(null);
  const onVerdictRef = useRef(onVerdict);
  onVerdictRef.current = onVerdict;

  const controller = useMemo(
    () =>
      createExtractionController({
        post: (m: ExtractOutbound) =>
          iframeRef.current?.contentWindow?.postMessage(m, window.location.origin),
        settle: (fn) => window.setTimeout(fn, SETTLE_MS),
        posePercent: DEFAULT_POSE_PERCENT,
        onVerdict: (v) => onVerdictRef.current?.(v),
      }),
    [],
  );
```

And pass the per-fold threshold in the extraction effect:

```typescript
    controller
      .start(data, fold.strainMax)
      .then((raw) => { if (!cancelled) setShell(buildShell(raw, THICKNESS)); })
      .catch((err: Error) => { if (!cancelled) setError(err.message); });
```

- [ ] **Step 5: Implement `App.tsx` — auto-switch + verdict send**

Import the helper and verdict type:

```typescript
import { applyFrame, initialState, foldWantsModelTab,
  type Frame, type ChatState } from "./chat";
import type { OracleVerdict } from "./extraction";
```

In the ws effect, auto-switch on shaped folds (the `setView` setter is
stable, so the empty dependency list stays correct):

```typescript
    ws.onmessage = (e) => {
      const frame = JSON.parse(e.data) as Frame;
      dispatch({ kind: "frame", frame });
      if (foldWantsModelTab(frame)) setView("model");
    };
```

Add the verdict sender (below `download()`):

```typescript
  function sendVerdict(v: OracleVerdict) {
    const id = state.fold?.id;
    if (id == null || wsRef.current?.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({
      type: "oracle_verdict", fold_id: id,
      verdict: v.verdict, p90: v.p90, reason: v.reason,
    }));
  }
```

And wire it:

```typescript
          <CADViewer fold={state.fold} onVerdict={sendVerdict} />
```

- [ ] **Step 6: Run the frontend suite + build**

Run: `cd <repo>/web/frontend && npm test && npm run build`
Expected: tests PASS; `tsc` build clean (catches prop/type slips in the two `.tsx` files the unit tests can't reach).

- [ ] **Step 7: Commit**

```bash
cd <repo>
git add web/frontend/src/chat.ts web/frontend/src/chat.test.ts \
        web/frontend/src/CADViewer.tsx web/frontend/src/App.tsx
git commit -m "feat(oracle): fold-frame oracle fields, Model-tab auto-switch, verdict send"
```

---

### Task 3: server — fold ids, verdict branch, capped retry turns

**Files:**
- Modify: `web/server.py`
- Test: `web/tests/test_server.py`

**Interfaces:**
- Consumes: the Task 2 outbound frame `{type: "oracle_verdict", fold_id, verdict, p90, reason}`.
- Produces: fold frames with `id`/`shaped`/`strain_max`; module-level `_parse_verdict(raw) -> tuple[int, str, float, str] | None`; the `[STRAIN ORACLE] ` message prefix (Task 4's prompt teaches it).

- [ ] **Step 1: Write the failing tests**

Append to `web/tests/test_server.py` (reusing the existing `_TIP_FOLD` fixture and `_shaping_client` helper conventions):

```python
_SHAPED_WRAPPER = {"status": "shaped", "fold": _TIP_FOLD,
                   "ide_shape_ops": ["reverse:1,0.5:0.2:90"], "verdicts": []}


def _oracle_client(monkeypatch, outputs, env=None):
    """Client whose stubbed agent_turn serves outputs[i] on call i and
    counts invocations. outputs entries are tool-output strings."""
    import agent_loop
    import llm_client
    from types import SimpleNamespace

    async def fake_connect(stack):
        return SimpleNamespace(sessions={}, tools=[], route={})

    monkeypatch.setattr(agent_loop, "connect_servers", fake_connect)
    monkeypatch.setattr(
        llm_client.LLMClient, "from_env",
        classmethod(lambda cls: SimpleNamespace(cfg=SimpleNamespace(
            provider="fake", model="fake"))),
    )

    calls = {"n": 0, "messages": None}

    async def fake_turn(client_, backend, messages, emit=None):
        calls["messages"] = messages
        out = outputs[min(calls["n"], len(outputs) - 1)]
        calls["n"] += 1
        emit({"type": "tool_result", "name": "apply_shaping_ops",
              "output": out, "is_error": False})

    monkeypatch.setattr(agent_loop, "agent_turn", fake_turn)
    monkeypatch.delenv("IDE_SHAPE_OP", raising=False)
    for k, v in (env or {}).items():
        monkeypatch.setenv(k, v)

    import importlib
    import web.server as server
    importlib.reload(server)
    monkeypatch.setattr(server, "_square_for_display",
                        lambda f, w=1.0, h=1.0: f)
    return TestClient(server.app), calls


def _drain_turn(ws):
    """Read frames until turn_end; return them (excluding turn_end)."""
    frames = []
    while True:
        f = ws.receive_json()
        if f["type"] == "turn_end":
            return frames
        frames.append(f)


def test_fold_frames_carry_id_shaped_and_strain_max(monkeypatch):
    client, _ = _oracle_client(
        monkeypatch, [json.dumps(_SHAPED_WRAPPER)],
        env={"IDE_STRAIN_MAX": "0.05"})
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "prompt", "text": "pose it"})
        frames = _drain_turn(ws)
    fold = next(f for f in frames if f["type"] == "fold")
    assert fold["id"] == 1
    assert fold["shaped"] is True
    assert fold["strain_max"] == 0.05


def test_unshaped_fold_is_not_marked_shaped(monkeypatch):
    client, _ = _oracle_client(monkeypatch, [json.dumps(_TIP_FOLD)])
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "prompt", "text": "make it"})
        frames = _drain_turn(ws)
    fold = next(f for f in frames if f["type"] == "fold")
    assert fold["shaped"] is False
    assert fold["strain_max"] == 0.15


def test_reject_verdict_triggers_one_capped_retry_turn(monkeypatch):
    client, calls = _oracle_client(
        monkeypatch, [json.dumps(_SHAPED_WRAPPER)])
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "prompt", "text": "pose it"})
        _drain_turn(ws)                                   # fold id 1
        ws.send_json({"type": "oracle_verdict", "fold_id": 1,
                      "verdict": "reject", "p90": 0.21,
                      "reason": "strain too high"})
        notice = ws.receive_json()                        # oracle echo
        assert notice["type"] == "assistant"
        assert notice["text"].startswith("[STRAIN ORACLE] ")
        assert "REJECTED" in notice["text"]
        frames = _drain_turn(ws)                          # the retry turn
        fold2 = next(f for f in frames if f["type"] == "fold")
        assert fold2["id"] == 2

        # second reject (for fold 2): cap (default 1) exhausted -> oracle
        # echo only, NO third turn.
        ws.send_json({"type": "oracle_verdict", "fold_id": 2,
                      "verdict": "reject", "p90": 0.20,
                      "reason": "still too high"})
        notice2 = ws.receive_json()
        assert "[STRAIN ORACLE] " in notice2["text"]

        # a fresh USER prompt serves fold 3 and resets the budget: a new
        # reject retries again.
        ws.send_json({"type": "prompt", "text": "pose it differently"})
        _drain_turn(ws)                                   # fold id 3
        ws.send_json({"type": "oracle_verdict", "fold_id": 3,
                      "verdict": "reject", "p90": 0.3, "reason": "high"})
        ws.receive_json()                                 # oracle echo
        _drain_turn(ws)                                   # retry turn 2
    assert calls["n"] == 4          # 2 prompts + 2 retries, not more
    oracle_msgs = [m for m in calls["messages"]
                   if m["role"] == "user"
                   and m["content"].startswith("[STRAIN ORACLE] ")]
    assert len(oracle_msgs) == 3    # all three verdicts entered the context


def test_pass_verdict_informs_but_never_retries(monkeypatch):
    client, calls = _oracle_client(
        monkeypatch, [json.dumps(_SHAPED_WRAPPER)])
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "prompt", "text": "pose it"})
        _drain_turn(ws)
        ws.send_json({"type": "oracle_verdict", "fold_id": 1,
                      "verdict": "pass", "p90": 0.04,
                      "reason": "converged (3 captures)"})
        notice = ws.receive_json()
        assert "PASSED" in notice["text"]
        # channel still alive and NO retry turn ran: a prompt works next.
        ws.send_json({"type": "prompt", "text": "thanks"})
        _drain_turn(ws)
    assert calls["n"] == 2          # the two prompts only
    assert any(m["content"].startswith("[STRAIN ORACLE] ")
               for m in calls["messages"] if m["role"] == "user")


def test_unshaped_fold_reject_never_retries(monkeypatch):
    client, calls = _oracle_client(monkeypatch, [json.dumps(_TIP_FOLD)])
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "prompt", "text": "make it"})
        _drain_turn(ws)
        ws.send_json({"type": "oracle_verdict", "fold_id": 1,
                      "verdict": "reject", "p90": 0.5, "reason": "bad"})
        notice = ws.receive_json()          # oracle echo only
        assert "[STRAIN ORACLE] " in notice["text"]
        ws.send_json({"type": "prompt", "text": "ok"})
        _drain_turn(ws)
    assert calls["n"] == 2


def test_stale_and_malformed_verdicts_are_ignored(monkeypatch):
    client, calls = _oracle_client(
        monkeypatch, [json.dumps(_SHAPED_WRAPPER)])
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "prompt", "text": "pose it"})
        _drain_turn(ws)                                   # fold id 1
        ws.send_json({"type": "oracle_verdict", "fold_id": 99,
                      "verdict": "reject", "p90": 0.5, "reason": "stale"})
        ws.send_json({"type": "oracle_verdict", "fold_id": 1,
                      "verdict": "explode", "p90": 0.5, "reason": "bad"})
        ws.send_json({"type": "oracle_verdict", "fold_id": 1,
                      "verdict": "reject", "p90": "not a number",
                      "reason": "bad"})
        ws.send_json({"type": "oracle_verdict"})
        # channel still alive; none of the above produced frames or turns.
        ws.send_json({"type": "prompt", "text": "ok"})
        first = ws.receive_json()
        assert first["type"] == "tool_result"             # the turn's frame
        _ = ws.receive_json()                             # fold
        assert ws.receive_json() == {"type": "turn_end", "ok": True}
    assert calls["n"] == 2
    assert not any(m["content"].startswith("[STRAIN ORACLE] ")
                   for m in calls["messages"] if m["role"] == "user")
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd <repo> && mcp_harness/.venv/bin/python -m pytest web/tests/test_server.py -q`
Expected: the new tests FAIL (fold frames lack `id`; verdict frames silently ignored so `receive_json` for the notice times out/fails). Pre-existing tests pass.

- [ ] **Step 3: Implement in `web/server.py`**

Add the parse helper at module level (after `_square_for_display`):

```python
def _parse_verdict(raw: dict):
    """(fold_id, verdict, p90, reason) from an oracle_verdict frame, or
    None when malformed. Defensive: the browser is untrusted input and a
    bad frame must never break the chat loop."""
    try:
        fold_id = raw["fold_id"]
        verdict = raw["verdict"]
        p90 = float(raw["p90"])
        reason = str(raw["reason"])
    except (KeyError, TypeError, ValueError):
        return None
    if not isinstance(fold_id, int) or isinstance(fold_id, bool):
        return None
    if verdict not in ("pass", "reject"):
        return None
    return fold_id, verdict, p90, reason
```

Change `_send_frames` to track fold serving on a per-connection dict —
signature `async def _send_frames(ws: WebSocket, event: dict, conn: dict) -> None:` —
and replace the fold-frame send with:

```python
            ops = extract_shape_ops(output)
            if ops is None:
                env_op = os.environ.get("IDE_SHAPE_OP")
                ops = [env_op] if env_op else []
            width, height = extract_paper_dims(output) or (1.0, 1.0)
            shaped = bool(ops)
            conn["fold_seq"] += 1
            conn["latest_id"] = conn["fold_seq"]
            conn["latest_shaped"] = shaped
            # A shaped fold from a USER-initiated turn opens a fresh retry
            # budget; retry-turn folds must not refill their own budget or
            # a never-passing pose loops forever (spec §5, Budget reset).
            if shaped and not conn["in_retry"]:
                conn["retries"] = 0
            await ws.send_json({"type": "fold", "filename": "model.fold",
                                "id": conn["latest_id"],
                                "shaped": shaped,
                                "strain_max": float(
                                    os.environ.get("IDE_STRAIN_MAX", "0.15")),
                                "json": fold,
                                "display_json": shaping.apply_display_ops(
                                    _square_for_display(fold, width, height),
                                    ops)})
```

Rework `ws_chat`: create the connection state, hoist the turn machinery
into a nested helper used by both the prompt branch and the verdict
branch, and add the verdict branch. The full new body after `accept()`/
error check:

```python
    messages: list[dict] = []
    conn = {"fold_seq": 0, "latest_id": None, "latest_shaped": False,
            "retries": 0, "in_retry": False}

    async def run_agent_turn() -> None:
        # agent_turn's sink is synchronous; bridge it to the async socket
        # via a queue, run the turn as a task, drain until a sentinel.
        queue: asyncio.Queue = asyncio.Queue()

        async def run() -> None:
            try:
                await agent_loop.agent_turn(
                    state.client, state.backend, messages,
                    emit=queue.put_nowait)
                queue.put_nowait({"type": "__end__"})
            except Exception as exc:  # engine/loop failure -> one error frame
                queue.put_nowait({"type": "__error__", "message": str(exc)})

        task = asyncio.create_task(run())
        try:
            while True:
                event = await queue.get()
                if event["type"] == "__end__":
                    await ws.send_json({"type": "turn_end", "ok": True})
                    break
                if event["type"] == "__error__":
                    await ws.send_json({"type": "error",
                                        "message": event["message"]})
                    break
                await _send_frames(ws, event, conn)
            await task
        except WebSocketDisconnect:
            # Client went away mid-turn: stop the detached agent work.
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
            raise

    while True:
        try:
            raw = await ws.receive_json()
        except WebSocketDisconnect:
            return

        if raw.get("type") == "oracle_verdict":
            parsed = _parse_verdict(raw)
            if parsed is None:
                continue
            fold_id, verdict, p90, reason = parsed
            if fold_id != conn["latest_id"]:
                print(f"oracle: stale verdict for fold {fold_id} "
                      f"(latest {conn['latest_id']}) ignored",
                      file=sys.stderr)
                continue
            word = "REJECTED" if verdict == "reject" else "PASSED"
            text = (f"[STRAIN ORACLE] pose {word} for the current fold "
                    f"(p90 strain {p90 * 100:.1f}%): {reason}")
            messages.append({"role": "user", "content": text})
            await ws.send_json({"type": "assistant", "text": text})
            limit = int(os.environ.get("IDE_ORACLE_RETRIES", "1"))
            if (verdict == "reject" and conn["latest_shaped"]
                    and conn["retries"] < limit):
                conn["retries"] += 1
                conn["in_retry"] = True
                try:
                    await run_agent_turn()
                except WebSocketDisconnect:
                    return
                finally:
                    conn["in_retry"] = False
            continue

        if raw.get("type") != "prompt":
            continue
        messages.append({"role": "user", "content": raw["text"]})
        try:
            await run_agent_turn()
        except WebSocketDisconnect:
            return
```

(`import sys` is already present at the top of the module.)

- [ ] **Step 4: Run the web suite**

Run: `cd <repo> && mcp_harness/.venv/bin/python -m pytest web/tests -q`
Expected: PASS — all pre-existing tests (the refactored turn helper must not change the prompt path's frame flow beyond the three new fold fields) plus the six new ones.

- [ ] **Step 5: Commit**

```bash
cd <repo>
git add web/server.py web/tests/test_server.py
git commit -m "feat(oracle): oracle_verdict ws branch — fold ids + capped auto-retry turns"
```

---

### Task 4: agent prompt — the `[STRAIN ORACLE]` contract

**Files:**
- Modify: `mcp_harness/agent_loop.py` (SHAPING section of `SYSTEM_PROMPT`)
- Test: `mcp_harness/tests/test_agent_shaping_prompt.py`

**Interfaces:**
- Consumes: the Task 3 message prefix `[STRAIN ORACLE] ` and REJECTED/PASSED wording.
- Produces: pinned prompt substrings.

- [ ] **Step 1: Write the failing pin test**

Append to `mcp_harness/tests/test_agent_shaping_prompt.py`:

```python
def test_prompt_teaches_strain_oracle_retries():
    assert "[STRAIN ORACLE]" in P
    assert "WITHOUT re-asking user approval" in P
    assert "PASSED" in P
    # oracle retries must not weaken the approval gate for NEW poses
    assert "NEW poses still require approval" in P
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd <repo>/mcp_harness && .venv/bin/python -m pytest tests/test_agent_shaping_prompt.py -q`
Expected: FAIL on the new test only.

- [ ] **Step 3: Edit the SHAPING section in `SYSTEM_PROMPT`**

In `mcp_harness/agent_loop.py`, find this exact fragment (end of the
verdict-handling sentence, start of the closing sentence):

```
fraction or theta, and re-confirm with the user before calling the tool \
again. Shaping is optional polish on a finished base -- never required, and \
never a remedy for lint or packing failures.
```

Replace it with:

```
fraction or theta, and re-confirm with the user before calling the tool \
again. Messages prefixed [STRAIN ORACLE] come from the physics simulator, \
not the human: on a REJECTED verdict, adjust the failing pose (smaller \
theta, or a different fraction) and re-call apply_shaping_ops WITHOUT \
re-asking user approval -- an oracle retry refines an already-approved \
pose; NEW poses still require approval. If the oracle rejects again after \
your retry, explain plainly to the user what failed. On PASSED, no action \
is needed. Shaping is optional polish on a finished base -- never required, \
and never a remedy for lint or packing failures.
```

- [ ] **Step 4: Run the prompt pins**

Run: `cd <repo>/mcp_harness && .venv/bin/python -m pytest tests/test_agent_shaping_prompt.py -q`
Expected: PASS — all 6 (5 existing + 1 new); `"ONLY AFTER THE USER APPROVES"` untouched.

- [ ] **Step 5: Commit**

```bash
cd <repo>
git add mcp_harness/agent_loop.py mcp_harness/tests/test_agent_shaping_prompt.py
git commit -m "feat(agent): SYSTEM_PROMPT teaches the [STRAIN ORACLE] retry contract"
```

---

### Task 5: full gates + live fail→retry→pass demo

**Files:**
- Create: `docs/b4-oracle-loop-retry.png` (evidence screenshot)
- No source changes (fix regressions only if the gates fail).

- [ ] **Step 1: Full backend suite**

Run: `cd <repo>/mcp_harness && .venv/bin/python -m pytest tests -q`
Expected: 287+ passed / 3 skipped (~10 min, real spawn compiles).

- [ ] **Step 2: Web + frontend suites and build**

Run: `cd <repo> && mcp_harness/.venv/bin/python -m pytest web/tests -q && cd web/frontend && npm test && npm run build`
Expected: web 40+ passed; vitest all green; build clean. The build step matters: the served UI is `web/frontend/dist`, so the demo needs a rebuild.

- [ ] **Step 3: Live demo — forced fail → auto-retry (manual acceptance, spec §1)**

1. Start the server with a strict threshold:
   `IDE_STRAIN_MAX=0.05 LLM_PROVIDER=groq LLM_MODEL=meta-llama/llama-4-scout-17b-16e-instruct mcp_harness/.venv/bin/python -m uvicorn web.server:app --port 8000`
2. Chat: "design a dog" → compiled base. Then: "crimp its neck so the head angles down".
3. Expect: the UI auto-switches to the Model tab; after 30–90s the oracle REJECTS (p90 ~12% > 5%); a `[STRAIN ORACLE] pose REJECTED…` line appears; the agent auto-runs a retry turn calling `apply_shaping_ops` with adjusted parameters — all without any user input. If the retried pose also rejects, the agent must explain the failure in plain language (cap = 1) — that is also a pass for this step.
4. Screenshot the transcript showing the oracle line + the autonomous retry (and the Model tab render) to `docs/b4-oracle-loop-retry.png`.
5. Restart with the default threshold (drop `IDE_STRAIN_MAX`), repeat the pose: expect a `[STRAIN ORACLE] pose PASSED…` line and no retry turn.
6. Known flakes: Groq `tool_use_failed` 400s mid-turn; retry the prompt if a turn dies.

- [ ] **Step 4: Commit the evidence**

```bash
cd <repo>
git add docs/b4-oracle-loop-retry.png
git commit -m "docs(oracle): live acceptance evidence — forced reject and autonomous retry"
```
