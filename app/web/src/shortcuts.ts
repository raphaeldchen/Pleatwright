export interface KeyLike {
  key: string; metaKey: boolean; ctrlKey: boolean; altKey: boolean; target: EventTarget | null;
}

/** Plain "N" starts a new run (Linear's single-key style; Chrome keeps ⌘N for a new window and never
 *  delivers it to the page). Never while typing in an editable element. */
export function isNewRunKey(e: KeyLike): boolean {
  if (e.key !== "n" && e.key !== "N") return false;
  if (e.metaKey || e.ctrlKey || e.altKey) return false;
  const t = e.target as { tagName?: string; isContentEditable?: boolean } | null;
  return !(t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName ?? "")));
}
