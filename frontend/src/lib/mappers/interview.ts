import type { AxisCoverage, EvalDimension, Question, Segment, WeakSegmentItem } from "../pe-types";

export interface InterviewDimension {
  id: string;
  label: string;
  description?: string;
  score?: number;
  state?: string;
  covered?: boolean;
  essential?: boolean;
  critical?: boolean;
  evidence_ids?: string[];
  evidence?: Array<Record<string, unknown>>;
  signals?: Array<Record<string, unknown>>;
  rules_triggered?: string[];
  rationale?: string;
  gaps?: Array<Record<string, unknown>>;
}

export interface InterviewUi {
  schema_version?: string;
  progress_state?: string;
  question_count?: number;
  max_questions?: number;
  dimensions?: InterviewDimension[];
  counter?: {
    covered?: number;
    observed?: number;
    total?: number;
    denominator?: number;
    percent?: number;
  };
  evidence?: Array<Record<string, unknown>>;
  signals?: Array<Record<string, unknown>>;
  answers?: Array<Record<string, unknown>>;
  history?: Array<Record<string, unknown>>;
  gaps?: Array<Record<string, unknown>>;
  gateway?: Record<string, unknown> | null;
  quality?: Record<string, unknown>;
  closure_reason?: string;
  current_question?: Record<string, unknown> | null;
  chart_series?: Array<{
    id: string;
    label: string;
    score?: number;
  }>;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

function asRecords(value: unknown): Array<Record<string, unknown>> {
  return Array.isArray(value) ? value.map(asRecord).filter((item) => Object.keys(item).length > 0) : [];
}

function normalizeDimension(value: unknown, index: number): InterviewDimension {
  const item = asRecord(value);
  const id = String(item.id ?? item.dimension_id ?? item.dimension ?? `dimension-${index}`);
  const state = String(item.state ?? "NAO_OBSERVADA");
  return {
    id,
    label: String(item.label ?? id),
    description: item.description ? String(item.description) : undefined,
    score: Number(item.score ?? 0),
    state,
    covered: item.covered != null ? Boolean(item.covered) : !["NAO_OBSERVADA", "NAO_APLICAVEL"].includes(state),
    essential: item.essential == null ? undefined : Boolean(item.essential),
    critical: item.critical == null ? undefined : Boolean(item.critical),
    evidence_ids: Array.isArray(item.evidence_ids) ? item.evidence_ids.map(String) : [],
    evidence: asRecords(item.evidence),
    signals: asRecords(item.signals),
    rules_triggered: Array.isArray(item.rules_triggered) ? item.rules_triggered.map(String) : [],
    rationale: item.rationale ? String(item.rationale) : undefined,
    gaps: asRecords(item.gaps),
  };
}

/** Normalize the API's one-dimensional V4 projection. */
export function mapInterview(raw: unknown): InterviewUi {
  const source = asRecord(raw);
  const rawDimensions = Array.isArray(source.dimensions)
    ? source.dimensions
    : Object.entries(asRecord(source.dimensions)).map(([id, value]) => ({ ...asRecord(value), id }));
  const dimensions = rawDimensions.map(normalizeDimension);
  const applicable = dimensions.filter((item) => item.state !== "NAO_APLICAVEL");
  const covered = applicable.filter((item) => item.covered).length;
  const counter = {
    covered,
    observed: covered,
    total: applicable.length,
    denominator: applicable.length,
    percent: applicable.length ? Math.round((covered / applicable.length) * 1000) / 10 : 0,
  };
  return {
    ...source as InterviewUi,
    schema_version: String(source.schema_version ?? "4.0"),
    progress_state: String(source.progress_state ?? "EXPLORANDO"),
    dimensions,
    chart_series: dimensions.map((item) => ({
      id: item.id,
      label: item.label,
      score: item.score ?? 0,
    })),
    counter,
  };
}

export function axesFromInterviewUi(interviewUi: InterviewUi | undefined): AxisCoverage[] {
  const dimensions = interviewUi?.dimensions ?? [];
  return dimensions.map((dimension) => ({
    key: dimension.id,
    label: dimension.label,
    dimension: dimension.label as AxisCoverage["dimension"],
    covered: dimension.covered ? 1 : 0,
    total: 1,
  }));
}

export function questionsFromInterview(ui: InterviewUi | undefined): Question[] {
  const current = ui?.current_question;
  if (current) {
    const prompt = String(current.question ?? current.text ?? "").trim();
    if (prompt) {
      return [{
        id: String(current.id ?? "v4-current"),
        axis: "entrevista",
        category: "v4",
        prompt,
        rationale: String(current.why_now ?? ""),
        answer: "",
        covered: false,
      }];
    }
  }
  const history = ui?.history ?? [];
  const questions: Question[] = [];
  history.forEach((item, index) => {
    const prompt = String(item.question ?? "").trim();
    if (prompt) {
      questions.push({
        id: String(item.answer_id ?? `v4-q-${index}`),
        axis: "entrevista",
        category: "v4",
        prompt,
        rationale: "",
        answer: String(item.answer ?? ""),
        covered: Boolean(String(item.answer ?? "").trim()),
      });
    }
  });
  return questions;
}

export function buildEditorialFeedback(interviewUi: InterviewUi | undefined): string | null {
  const gateway = asRecord(interviewUi?.gateway);
  const justification = String(gateway.justification ?? "").trim();
  if (justification) return justification;
  const gaps = interviewUi?.gaps ?? [];
  if (gaps.length > 0) return "Ainda ha lacunas autorais a explorar.";
  return null;
}

export function segmentsFromState(
  segmentos: Array<Record<string, unknown>>,
  segmentoReescrito: string,
  segmentIndex: number,
  pendingByIndex: Record<number, { request: string; version: string }>,
): Segment[] {
  return segmentos.map((seg, index) => {
    const pending = pendingByIndex[index];
    const isSelected = index === segmentIndex;
    const rawSugestao = seg.sugestaoImagem ?? seg.sugestao_imagem;
    let imageSuggestion: Segment["imageSuggestion"];
    if (rawSugestao && typeof rawSugestao === "object") {
      const s = rawSugestao as Record<string, unknown>;
      const descricao = String(s.descricao || "").trim();
      if (descricao) {
        imageSuggestion = {
          modo: String(s.modo || "descricao") === "link" ? "link" : "descricao",
          descricao,
          url: s.url ? String(s.url) : undefined,
          fonte: s.fonte ? String(s.fonte) : undefined,
        };
      }
    }
    return {
      id: String(seg.id ?? `seg-${index}`),
      index,
      text: String(seg.texto || ""),
      ghost: isSelected && segmentoReescrito ? String(seg.texto || "") : undefined,
      pendingRequest: pending?.request,
      pendingVersion: isSelected && segmentoReescrito ? segmentoReescrito : pending?.version,
      role: String(seg.papel_interno || seg.papelInterno || ""),
      imageSuggestion,
    };
  });
}

const EVAL_KEYS = [
  ["tese", "Tese"],
  ["progressao", "Progressão"],
  ["concretude", "Concretude"],
  ["precisao_tecnica", "Precisão Técnica"],
  ["retencao", "Retenção"],
  ["autoridade", "Autoridade"],
  ["autoria", "Autoria"],
  ["slidemark", "SlideMark"],
  ["revisao_textual", "Revisão Textual"],
] as const;

function parseScoreValue(raw: string): number {
  const match = raw.match(/(\d+(?:\.\d+)?)/);
  if (!match) return 0;
  const value = Number(match[1]);
  return value <= 10 ? Math.round(value * 10) : Math.round(value);
}

export function evaluationFromUi(
  avaliacaoUi: Record<string, unknown> | undefined,
  avaliacaoPost?: Record<string, unknown>,
): { evaluation: EvalDimension[] | null; evalScore: number | null } {
  if (!avaliacaoUi?.valida) return { evaluation: null, evalScore: null };

  const scoreObj = (avaliacaoPost?.score ?? {}) as Record<string, number>;
  const trechos = (avaliacaoUi.trechos_fracos ?? []) as Array<Record<string, unknown>>;
  const diagnostico = (avaliacaoPost?.diagnostico ?? {}) as Record<string, string>;

  const evaluation: EvalDimension[] = EVAL_KEYS.map(([key, label]) => {
    const trecho = trechos.find((t) => String(t.trecho ?? "") === String(
      EVAL_KEYS.findIndex(([k]) => k === key) + 1,
    ));
    const rawScore = scoreObj[key];
    const score = typeof rawScore === "number" ? Math.round(rawScore * 10) : parseScoreValue(
      String((avaliacaoUi.scores as Record<string, string> | undefined)?.[key] ?? "0"),
    );
    return {
      key: label,
      score,
      diagnosis: diagnostico[key] || String((avaliacaoUi.scores as Record<string, string>)?.[key] ?? ""),
      problem: trecho ? String(trecho.problema ?? "") : undefined,
      direction: trecho ? String(trecho.motivo ?? "") : undefined,
      segmentRef: trecho?.trecho !== undefined ? Number(trecho.trecho) - 1 : undefined,
    };
  });

  const totalRaw = scoreObj.total ?? parseScoreValue(String((avaliacaoUi.scores as Record<string, string>)?.total ?? "0")) / 10;
  const evalScore = typeof scoreObj.total === "number"
    ? Math.round(scoreObj.total * 10)
    : parseScoreValue(String((avaliacaoUi.scores as Record<string, string>)?.total ?? "0"));

  return { evaluation, evalScore: evalScore || Math.round(Number(totalRaw) * 10) || null };
}

export function trechoToSegmentIndex(trechoRaw: unknown, segmentCount: number): number | null {
  const trecho = Number(trechoRaw);
  if (!Number.isFinite(trecho) || segmentCount <= 0) return null;
  const index = trecho >= 1 ? trecho - 1 : trecho === 0 ? 0 : -1;
  if (index < 0 || index >= segmentCount) return null;
  return index;
}

export function weakSegmentsFromEvaluation(
  avaliacaoUi: Record<string, unknown> | undefined,
  segments: Segment[],
): WeakSegmentItem[] {
  if (!avaliacaoUi?.valida) return [];
  const trechos = (avaliacaoUi.trechos_fracos ?? []) as Array<Record<string, unknown>>;
  const merged = new Map<number, WeakSegmentItem>();

  for (const entry of trechos) {
    const index = trechoToSegmentIndex(entry.trecho, segments.length);
    if (index === null) continue;
    const segment = segments[index];
    if (!segment) continue;

    const problema = String(entry.problema ?? "").trim();
    const motivo = String(entry.motivo ?? "").trim();
    const severidade = String(entry.severidade ?? "").trim() || undefined;
    const existing = merged.get(index);

    if (!existing) {
      merged.set(index, {
        index,
        order: index + 1,
        text: segment.text,
        problem: problema,
        direction: motivo,
        severidade,
      });
      continue;
    }

    merged.set(index, {
      ...existing,
      problem: [existing.problem, problema].filter(Boolean).join("\n"),
      direction: [existing.direction, motivo].filter(Boolean).join("\n"),
    });
  }

  return Array.from(merged.values()).sort((a, b) => a.index - b.index);
}

export function briefingCardsFromState(
  briefing: Record<string, unknown> | undefined,
  serialized: string | undefined,
): Array<{ k: string; v: string }> {
  if (!briefing || Object.keys(briefing).length === 0) {
    if (serialized?.trim()) {
      return [{ k: "briefing", v: serialized.slice(0, 2000) }];
    }
    return [];
  }

  const cards: Array<{ k: string; v: string }> = [];
  const theme = String(briefing.theme ?? "").trim();
  const objective = String(briefing.objective ?? "").trim();
  const evidence = Array.isArray(briefing.evidence) ? briefing.evidence : [];
  const signals = Array.isArray(briefing.signals) ? briefing.signals : [];
  const gateway = asRecord(briefing.gateway);

  if (theme) cards.push({ k: "tema", v: theme });
  if (objective) cards.push({ k: "objetivo", v: objective });
  if (evidence.length) cards.push({ k: "evidencias", v: `${evidence.length} trechos literais` });
  if (signals.length) cards.push({ k: "sinais", v: `${signals.length} sinais autorais` });
  if (gateway.justification) cards.push({ k: "gateway", v: String(gateway.justification) });

  if (cards.length === 0) {
    cards.push({ k: "briefing", v: JSON.stringify(briefing, null, 2).slice(0, 3000) });
  }
  return cards;
}
