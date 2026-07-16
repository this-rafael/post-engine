export type StageId =
  | "agents"
  | "entry"
  | "interview"
  | "briefing"
  | "storyboard"
  | "drafts"
  | "composition"
  | "prompt"
  | "execution"
  | "segmentation"
  | "evaluation"
  | "export";

export type Phase =
  | "idle"
  | "interviewing"
  | "compiling"
  | "generating"
  | "segmenting"
  | "evaluating"
  | "success"
  | "error";

export interface PhaseProgressItem {
  id: string;
  label: string;
  stage: StageId;
  status: "released" | "active" | "pending";
}

export interface PhaseProgress {
  released: string[];
  pending: string[];
  latest_released: string;
  phases: PhaseProgressItem[];
}

export type ProviderId = "codex" | "opencode" | "cursor";

export interface OperationConfig {
  id: string;
  label: string;
  provider: ProviderId;
  model: string;
  agent?: string;
  reasoning?: string;
  sandbox: "read-only" | "workspace-write" | "danger-full";
  timeoutSeconds?: number;
}

export interface AxisCoverage {
  key: string;
  label: string;
  dimension: Dimension;
  covered: number;
  total: number;
}

export type InterviewDimensionState =
  | "NAO_OBSERVADA"
  | "FRACA"
  | "PARCIAL"
  | "SUFICIENTE"
  | "FORTE"
  | "EXCEPCIONAL"
  | "CONFLITANTE"
  | "NAO_APLICAVEL";

export interface InterviewEvidence {
  id: string;
  text: string;
  origin?: string;
  source_answer_id?: string;
  type?: string;
}

export interface InterviewSignal {
  id?: string;
  type: string;
  summary: string;
  confidence?: number;
  origin?: string;
  evidence_ids?: string[];
  status?: "CONFIRMADO" | "INFERIDO" | "INCERTO" | "CONFLITANTE" | string;
}

export interface InterviewDimensionUi {
  id: string;
  label: string;
  description?: string;
  score?: number;
  state?: InterviewDimensionState | string;
  covered?: boolean;
  essential?: boolean;
  critical?: boolean;
  evidence_ids?: string[];
  evidence?: InterviewEvidence[];
  signals?: InterviewSignal[];
  rules_triggered?: string[];
  rationale?: string;
  gaps?: Array<Record<string, unknown>>;
}

export type Dimension = string;

export interface Question {
  id: string;
  axis: string;
  category: string;
  prompt: string;
  rationale: string;
  answer: string;
  covered?: boolean;
  roundTitle?: string;
}

export interface ImageSuggestion {
  modo: "descricao" | "link";
  descricao: string;
  url?: string;
  fonte?: string;
}

export interface Segment {
  id: string;
  index: number;
  text: string;
  ghost?: string;
  pendingRequest?: string;
  pendingVersion?: string;
  role?: string;
  imageSuggestion?: ImageSuggestion;
}

export interface EvalDimension {
  key: string;
  score: number;
  diagnosis: string;
  problem?: string;
  direction?: string;
  segmentRef?: number;
}

export interface WeakSegmentItem {
  index: number;
  order: number;
  text: string;
  problem: string;
  direction: string;
  severidade?: string;
}

export interface RunEvent {
  id: string;
  t: number;
  kind: string;
  label: string;
}

export interface EditorialBlock {
  id: string;
  order: number;
  role: string;
  focus: string;
  revision: number;
}

export interface EditorialDraftOption {
  id: string;
  approach: { title: string; description: string };
  persona_id: string;
  persona_name: string;
  content: string;
  status: string;
  obsolete?: boolean;
  error?: string | null;
}

export interface EditorialStatus {
  storyboard_available: boolean;
  drafts_partial: boolean;
  drafts_available: boolean;
  selection_incomplete: boolean;
  selection_complete: boolean;
  composition_stale: boolean;
  composition_available: boolean;
  can_compose: boolean;
}
