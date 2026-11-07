// The service worker answers a browser run's file URLs (sw.ts), so a page it does not
// control shows none of them. A first visit is taken over by the new worker's clients.claim()
// during its activation; a page loaded with Shift+Reload never is (the worker is already
// active, and claims only once). Such a page reloads once, normally. A session-storage flag
// makes that one reload at most: a page still uncontrolled after it (or with no session
// storage to hold the flag) stays as it is, and examples still load (their files are static).

export const RELOAD_FLAG = "pleatwright-sw-reload";

interface WorkerLike extends EventTarget { state: string }

export interface ControlDeps {
  container: EventTarget & { ready: Promise<{ active: WorkerLike | null }>; controller: unknown };
  storage: Pick<Storage, "getItem" | "setItem" | "removeItem"> | null;
  reload: () => void;
  /** How long to wait for a claim after the worker is active. */
  graceMs?: number;
}

/** Resolves once `sw` has finished activating (its claim() has run by then). */
const activated = (sw: WorkerLike | null) =>
  new Promise<void>((resolve) => {
    if (!sw || sw.state === "activated" || sw.state === "redundant") return resolve();
    const on = () => {
      if (sw.state !== "activated" && sw.state !== "redundant") return;
      sw.removeEventListener("statechange", on);
      resolve();
    };
    sw.addEventListener("statechange", on);
  });

export async function ensureControlled(deps: ControlDeps): Promise<"controlled" | "reloaded" | "gave_up"> {
  const { container, storage } = deps;
  const reg = await container.ready;
  if (!container.controller) {
    // claim()'s controllerchange can land just after the "activated" statechange: a short grace.
    await new Promise<void>((resolve) => {
      container.addEventListener("controllerchange", () => resolve(), { once: true });
      void activated(reg.active).then(() => setTimeout(resolve, deps.graceMs ?? 1000));
    });
  }
  if (container.controller) {
    try { storage?.removeItem(RELOAD_FLAG); } catch { /* no session storage */ }
    return "controlled";
  }
  try {
    if (!storage || storage.getItem(RELOAD_FLAG)) return "gave_up";
    storage.setItem(RELOAD_FLAG, "1");
  } catch {
    return "gave_up";
  }
  deps.reload();
  return "reloaded";
}
