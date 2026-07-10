import type { StageId } from "../pe-types";

export const PHASE_TO_STAGE: Record<string, StageId> = {
  entrada_inicial: "entry",
  entrevista_gateway: "interview",
  briefing_autoral: "briefing",
  prompt_renderizado: "prompt",
  execucao_llm: "execution",
  segmentacao_editavel: "segmentation",
  avaliacao_conteudo: "evaluation",
  exportacao_final: "export",
};

export const STAGE_TO_PHASE: Record<StageId, string | null> = {
  agents: null,
  entry: "entrada_inicial",
  interview: "entrevista_gateway",
  briefing: "briefing_autoral",
  storyboard: null,
  drafts: null,
  composition: null,
  prompt: "prompt_renderizado",
  execution: "execucao_llm",
  segmentation: "segmentacao_editavel",
  evaluation: "avaliacao_conteudo",
  export: "exportacao_final",
};

export function stageFromPhase(phase: string | undefined): StageId {
  if (!phase) return "entry";
  return PHASE_TO_STAGE[phase] ?? "entry";
}

export function phaseFromStage(stage: StageId): string | null {
  return STAGE_TO_PHASE[stage];
}
