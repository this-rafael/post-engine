export const OP_UI_TO_BACKEND: Record<string, string> = {
  questions: "interview_questions",
  validate: "interview_validate",
  answers: "interview_evaluate",
  postGenerate: "post_generate",
  storyboard: "storyboard_generate",
  blockApproaches: "block_approaches_generate",
  blockDraft: "block_draft_generate",
  editorialCompose: "editorial_compose",
  segment: "segment",
  adjust: "adjust_segment",
  adjustBulk: "adjust_segments_bulk",
  evaluate: "post_evaluate",
  slidemark: "slidemark_export",
};

export const OP_BACKEND_TO_UI: Record<string, string> = Object.fromEntries(
  Object.entries(OP_UI_TO_BACKEND).map(([ui, backend]) => [backend, ui]),
);

export const OP_LABELS: Record<string, string> = {
  questions: "Exploração aberta da entrevista",
  validate: "Avaliação da qualidade das perguntas da entrevista",
  answers: "Avaliação de autoria da entrevista",
  postGenerate: "Geração de post",
  storyboard: "Storyboard narrativo",
  blockApproaches: "Abordagens de bloco",
  blockDraft: "Rascunho de bloco",
  editorialCompose: "Composição editorial",
  segment: "Segmentação",
  adjust: "Ajuste de segmento",
  adjustBulk: "Ajuste em lote de segmentos",
  evaluate: "Avaliação do post",
  slidemark: "Export SlideMark",
};

export const OP_ORDER = [
  "questions",
  "validate",
  "answers",
  "postGenerate",
  "storyboard",
  "blockApproaches",
  "blockDraft",
  "editorialCompose",
  "segment",
  "adjust",
  "adjustBulk",
  "evaluate",
  "slidemark",
] as const;
