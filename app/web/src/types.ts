export const STAGES = ["image", "mesh", "tree", "packing", "solve", "shape", "model"] as const;
export type StageId = (typeof STAGES)[number];
export type StageStatus = "todo" | "running" | "done" | "waiting" | "failed" | "skipped";

export interface PwEvent {
  seq: number;
  t: string;
  type: string;
  stage?: StageId;
  [k: string]: unknown;
}

export interface Output {
  key: string;                 // `${stage}` or `tree:${round}`
  stage: StageId;
  round?: number;
  files: string[];
  summary: Record<string, unknown>;
  seq: number;
}

export type ChatItem =
  | { kind: "user"; text: string; seq: number }
  | { kind: "assistant"; text: string; seq: number }
  | { kind: "output"; key: string; seq: number }
  | { kind: "failed"; stage: StageId; error: string; reason: string; retry: string | null; seq: number };

export interface LayoutOption {
  id: "smaller" | "symmetric"; label: string; grid: number; recommended: boolean;
  pros: string[]; cons: string[];
}
/** The packing stage's question: which of two layouts to fold (server: tools.present_layout). */
export interface LayoutCard { question: string; options: LayoutOption[] }

export interface Review {
  round: number; canApprove: boolean; stage: StageId;
  /** Packing review only. `explanation` and `note` are untrusted text: render as text nodes. */
  card?: LayoutCard; explanation?: string; note?: string | null;
}

export interface RunView {
  id: string;
  prompt: string;
  lastSeq: number;
  stages: Record<StageId, StageStatus>;
  startedAt: Partial<Record<StageId, string>>;
  outputs: Output[];
  chat: ChatItem[];
  review: Review | null;
  finished: Record<string, unknown> | null;
  failure: { stage: StageId; reason: string; retry: string | null } | null;
  running: boolean;
  selected: string | null;
  followLatest: boolean;
}

export type Action =
  | { type: "event"; event: PwEvent }
  | { type: "select"; key: string }
  | { type: "follow" };

export interface RunSummary {
  id: string; prompt: string; subject: string; created: string;
  status: "new" | "running" | "waiting" | "done" | "failed";
}
export interface ModelOption { key: string; id: string; label: string }
export interface Status {
  llm_ok: boolean; llm_error: string | null; busy: string | null;
  default_model?: string; models?: ModelOption[];
}

/** "01" … "07": a stage's position in STAGES. */
export const stageNum = (s: StageId): string => String(STAGES.indexOf(s) + 1).padStart(2, "0");

/** "01 IMAGE" … "07 MODEL" ("packing" shows as PACK); shared by the stepper and the chat. */
export const stageLabel = (s: StageId): string =>
  `${stageNum(s)} ${(s === "packing" ? "pack" : s).toUpperCase()}`;
