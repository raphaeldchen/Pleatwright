import type { PrefStore } from "./theme";
import type { ModelOption } from "./types";

/** The VLM the next tree is authored with, remembered per browser. The server
 *  owns the list (GET /status `models`) and the default (`default_model`). */
export const MODEL_KEY = "pleatwright.model";

export function readModel(storage: PrefStore | null, models: ModelOption[], fallback: string): string {
  try {
    const k = storage?.getItem(MODEL_KEY);
    return k && models.some((m) => m.key === k) ? k : fallback;
  } catch {
    return fallback;
  }
}

export function nextModel(models: ModelOption[], key: string): string {
  if (models.length === 0) return key;
  const i = models.findIndex((m) => m.key === key);
  return models[(i + 1) % models.length].key;
}

export function saveModel(storage: PrefStore | null, key: string): void {
  try { storage?.setItem(MODEL_KEY, key); } catch { /* private window: lasts until reload */ }
}
