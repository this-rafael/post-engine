import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type {
  EditorialBlock,
  EditorialStatus,
  EvalDimension,
  OperationConfig,
  Phase,
  ProviderId,
  Question,
  RunEvent,
  Segment,
  StageId,
  WeakSegmentItem,
} from "./pe-types";
import {
  eventsFromState,
  fetchLlmConfig,
  fetchSession,
  llmConfigPayloadFromOps,
  opsFromConfig,
  patchSession,
  providersFromStatus,
  restoreSession,
  runAction,
  saveLlmConfig,
  tipoLabel,
  type ApiSnapshot,
} from "./pe-api";
import {
  axesFromInterviewUi,
  briefingCardsFromState,
  buildEditorialFeedback,
  evaluationFromUi,
  mapInterview,
  questionsFromInterview,
  segmentsFromState,
  weakSegmentsFromEvaluation,
  type InterviewUi,
} from "./mappers/interview";
import { phaseFromStage, stageFromPhase } from "./mappers/phase";
import {
  editorialFlowFromState,
  editorialStatusFromDerived,
  storyboardBlocks as blocksFromFlow,
  type EditorialFlow,
} from "./mappers/editorial";

export const PROVIDERS: { id: ProviderId; label: string; available: boolean }[] = [
  { id: "codex", label: "Codex", available: false },
  { id: "opencode", label: "OpenCode", available: false },
  { id: "cursor", label: "Cursor", available: false },
];

export interface BriefingCard {
  k: string;
  v: string;
}

interface Store {
  busy: boolean;
  error: string | null;
  statusText: string;
  stage: StageId;
  reachable: Record<StageId, boolean>;
  phase: Phase;
  ops: OperationConfig[];
  providers: Array<{ id: ProviderId; label: string; available: boolean }>;
  session: {
    theme: string;
    persona: string;
    platform: string;
    platformValue: string;
    contentType: string;
    contentTypeValue: string;
    objective: string;
    personality: string;
  };
  axes: ReturnType<typeof axesFromInterviewUi>;
  interviewUi: InterviewUi;
  editorialFeedback: string | null;
  round: Question[];
  rounds: number;
  briefingReady: boolean;
  briefingCards: BriefingCard[];
  promptRendered: boolean;
  promptText: string;
  events: RunEvent[];
  runState: "idle" | "running" | "done" | "error";
  returnCode: number | null;
  rawOutput: string;
  segments: Segment[];
  weakSegments: WeakSegmentItem[];
  bulkRewrites: Record<number, string>;
  evaluation: EvalDimension[] | null;
  evalScore: number | null;
  exportState: Record<"markdown" | "slidemark", "idle" | "running" | "done">;
  exportPath: string;
  isTrilhaVisual: boolean;
  focusSegment: number | null;
  snapshot: ApiSnapshot | null;
  /** Cópia do state interno enviado em `/api/action` (`draftRef`). */
  actionState: Record<string, unknown>;
  serialized: Record<string, string>;
  restoreText: string;
  interviewFocus: boolean;
  editorialFlow: EditorialFlow;
  editorialStatus: EditorialStatus;
  storyboardBlocks: EditorialBlock[];
  draftByBlock: Record<string, { options?: import("./pe-types").EditorialDraftOption[]; selected_option_id?: string | null; status?: string }>;

  generateStoryboard: () => Promise<void>;
  updateStoryboard: (blocks: Array<{ id: string; role: string; focus: string; revision?: number }>) => Promise<void>;
  generateBlockDrafts: (blockId: string) => Promise<void>;
  generateAllBlockDrafts: () => Promise<void>;
  retryBlockDraft: (blockId: string, optionId: string) => Promise<void>;
  selectBlockDraft: (blockId: string, optionId: string) => Promise<void>;
  composeEditorial: () => Promise<void>;
  goto: (s: StageId) => Promise<void>;
  setInterviewFocus: (v: boolean) => void;
  setPhase: (p: Phase) => void;
  updateOp: (id: string, patch: Partial<OperationConfig>) => void;
  saveOps: () => Promise<void>;
  setSession: (patch: Partial<Store["session"]>) => void;
  saveSession: () => Promise<void>;
  reload: () => Promise<void>;
  continueToInterview: () => Promise<void>;
  answerQuestion: (id: string, text: string) => void;
  submitRound: () => Promise<void>;
  nextInterviewQuestion: () => Promise<void>;
  buildBriefing: () => Promise<void>;
  renderPrompt: () => Promise<void>;
  runGeneration: () => Promise<void>;
  clearOutput: () => Promise<void>;
  segment: () => Promise<void>;
  requestAdjust: (index: number, request: string) => Promise<void>;
  applyAdjust: (index: number) => void;
  discardAdjust: (index: number) => void;
  requestBulkAdjust: (ajustes: Array<{ index: number; pedido: string }>) => Promise<void>;
  applyBulkAdjust: (index: number) => Promise<void>;
  applyAllBulkAdjust: () => Promise<void>;
  discardBulkAdjust: () => Promise<void>;
  reBulkAdjustItem: (index: number, pedido: string) => Promise<void>;
  evaluate: () => Promise<void>;
  doExport: (kind: "markdown" | "slidemark") => Promise<void>;
  focus: (index: number | null) => void;
  resetContext: () => Promise<void>;
  restore: () => Promise<void>;
  setRestoreText: (text: string) => void;
  setExportPath: (path: string) => void;
}

const Ctx = createContext<Store | null>(null);

const BASE_REACHABLE: Record<StageId, boolean> = {
  agents: true,
  entry: true,
  interview: false,
  briefing: false,
  storyboard: false,
  drafts: false,
  composition: false,
  prompt: false,
  execution: false,
  segmentation: false,
  evaluation: false,
  export: false,
};

function isStageId(value: unknown): value is StageId {
  return typeof value === "string" && [
    "agents",
    "entry",
    "interview",
    "briefing",
    "storyboard",
    "drafts",
    "composition",
    "prompt",
    "execution",
    "segmentation",
    "evaluation",
    "export",
  ].includes(value);
}

function computeReachable(
  state: Record<string, unknown>,
  derived: Record<string, unknown>,
  briefingReady: boolean,
): Record<StageId, boolean> {
  const editorial = editorialStatusFromDerived(derived);
  const hasContent = Boolean(String(state.conteudo_gerado ?? "").trim());
  const hasSegments = Array.isArray(state.segmentos) && state.segmentos.length > 0;
  const hasEval = Boolean(state.avaliacao_post && Object.keys(state.avaliacao_post as object).length > 0);
  const phase = String(state.current_phase ?? "");
  return {
    agents: true,
    entry: true,
    interview: phase !== "entrada_inicial" || briefingReady,
    briefing: briefingReady || ["briefing_autoral", "prompt_renderizado", "execucao_llm", "segmentacao_editavel", "avaliacao_conteudo", "exportacao_final"].includes(phase),
    storyboard: briefingReady,
    drafts: editorial.storyboard_available,
    composition: editorial.drafts_available || editorial.selection_complete,
    prompt: false,
    execution: false,
    segmentation: hasContent,
    evaluation: hasSegments,
    export: hasEval || hasContent,
  };
}

function draftFromState(state: Record<string, unknown>): Record<string, unknown> {
  return { ...state };
}

export function PostEngineProvider({ children }: { children: ReactNode }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusText, setStatusText] = useState("");
  const [stage, setStage] = useState<StageId>("agents");
  const [phase, setPhase] = useState<Phase>("idle");
  const [ops, setOps] = useState<OperationConfig[]>([]);
  const [providers, setProviders] = useState(PROVIDERS);
  const [session, setSessionState] = useState<Store["session"]>({
    theme: "",
    persona: "",
    platform: "linkedin",
    platformValue: "linkedin",
    contentType: "",
    contentTypeValue: "post",
    objective: "",
    personality: "",
  });
  const [axes, setAxes] = useState<Store["axes"]>([]);
  const [interviewUi, setInterviewUi] = useState<InterviewUi>({});
  const [editorialFeedback, setEditorialFeedback] = useState<string | null>(null);
  const [round, setRound] = useState<Question[]>([]);
  const [rounds, setRounds] = useState(1);
  const [briefingReady, setBriefingReady] = useState(false);
  const [briefingCards, setBriefingCards] = useState<BriefingCard[]>([]);
  const [promptRendered, setPromptRendered] = useState(false);
  const [promptText, setPromptText] = useState("");
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [runState, setRunState] = useState<Store["runState"]>("idle");
  const [returnCode, setReturnCode] = useState<number | null>(null);
  const [rawOutput, setRawOutput] = useState("");
  const [segments, setSegments] = useState<Segment[]>([]);
  const [weakSegments, setWeakSegments] = useState<WeakSegmentItem[]>([]);
  const [bulkRewrites, setBulkRewrites] = useState<Record<number, string>>({});
  const [evaluation, setEvaluation] = useState<EvalDimension[] | null>(null);
  const [evalScore, setEvalScore] = useState<number | null>(null);
  const [exportState, setExportState] = useState<Store["exportState"]>({
    markdown: "idle",
    slidemark: "idle",
  });
  const [exportPath, setExportPath] = useState("");
  const [isTrilhaVisual, setIsTrilhaVisual] = useState(false);
  const [focusSegment, setFocusSegment] = useState<number | null>(null);
  const [snapshot, setSnapshot] = useState<ApiSnapshot | null>(null);
  const [serialized, setSerialized] = useState<Record<string, string>>({});
  const [restoreText, setRestoreText] = useState("");
  const [interviewFocus, setInterviewFocus] = useState(false);
  const [reachable, setReachable] = useState(BASE_REACHABLE);
  const [editorialFlow, setEditorialFlow] = useState<EditorialFlow>({});
  const [editorialStatus, setEditorialStatus] = useState<EditorialStatus>(editorialStatusFromDerived({}));
  const [storyboardBlocks, setStoryboardBlocks] = useState<EditorialBlock[]>([]);
  const [draftByBlock, setDraftByBlock] = useState<Store["draftByBlock"]>({});

  const draftRef = useRef<Record<string, unknown>>({});
  const pendingAdjustRef = useRef<Record<number, { request: string; version: string }>>({});
  const bulkRewritesRef = useRef<Record<number, string>>({});
  const phaseTimer = useRef<ReturnType<typeof setTimeout>>(undefined);

  const settle = useCallback((p: Phase, back: Phase = "idle", ms = 1400) => {
    setPhase(p);
    clearTimeout(phaseTimer.current);
    phaseTimer.current = setTimeout(() => setPhase(back), ms);
  }, []);

  const applySnapshot = useCallback((data: ApiSnapshot, keepStage?: StageId) => {
    const state = data.state ?? {};
    const derived = data.derived ?? {};
    const options = data.options ?? {};
    draftRef.current = draftFromState(state);

    const currentPhase = String(state.current_phase || "");
    if (!keepStage) {
      const derivedStage = derived.active_stage;
      setStage(isStageId(derivedStage) ? derivedStage : stageFromPhase(currentPhase));
    }

    const tipos = (options.tipos_de_post ?? []) as Array<{ label: string; value: string }>;
    const plataformas = (options.plataformas ?? []) as Array<{ label: string; value: string }>;
    const persona = String(derived.persona_ativa ?? "");
    const tipo = String(state.tipo_de_post ?? "");
    const plataforma = String(state.plataforma ?? "");

    setSessionState({
      theme: String(state.tema ?? ""),
      persona,
      platform: plataformas.find((p) => p.value === plataforma)?.label ?? plataforma,
      platformValue: plataforma,
      contentType: tipoLabel(tipo, tipos),
      contentTypeValue: tipo,
      objective: String(state.objetivo_do_post ?? ""),
      personality: String(state.personalidade ?? ""),
    });

    const ui = mapInterview(derived.interview ?? {});
    setInterviewUi(ui);
    setAxes(axesFromInterviewUi(ui));
    setEditorialFeedback(buildEditorialFeedback(ui));
    setRound(questionsFromInterview(ui));
    setRounds(Number(ui.question_count ?? 0));

    const briefing = (state.briefing_autoral ?? {}) as Record<string, unknown>;
    const briefingSerialized = String((derived.serialized as Record<string, string> | undefined)?.briefing ?? "");
    setBriefingReady(Boolean(briefing && Object.keys(briefing).length > 0));
    setBriefingCards(briefingCardsFromState(briefing, briefingSerialized));

    const flow = editorialFlowFromState(state);
    setEditorialFlow(flow);
    const edStatus = editorialStatusFromDerived(derived);
    setEditorialStatus(edStatus);
    setStoryboardBlocks(blocksFromFlow(flow));
    setDraftByBlock(flow.drafts?.by_block ?? {});
    setReachable(computeReachable(state, derived, Boolean(briefing && Object.keys(briefing).length > 0)));

    const prompt = String(state.prompt_renderizado ?? "");
    setPromptRendered(Boolean(prompt.trim()));
    setPromptText(prompt);

    const evts = eventsFromState(Array.isArray(state.events) ? state.events : []);
    setEvents(evts);
    const conteudo = String(state.conteudo_gerado ?? "");
    setRawOutput(conteudo);
    const rc = state.returncode;
    setReturnCode(rc === null || rc === undefined ? null : Number(rc));
    if (state.is_running) setRunState("running");
    else if (state.error) setRunState("error");
    else if (conteudo.trim()) setRunState("done");
    else setRunState("idle");

    const segmentoReescrito = String(derived.segmento_reescrito ?? state._segmento_reescrito ?? "");
    const segmentIndex = Number(state._segmento_index ?? 0);
    const segs = Array.isArray(state.segmentos) ? state.segmentos as Array<Record<string, unknown>> : [];
    const mappedSegments = segmentsFromState(segs, segmentoReescrito, segmentIndex, pendingAdjustRef.current);
    setSegments(mappedSegments);

    const avaliacaoUi = (derived.avaliacao_ui ?? {}) as Record<string, unknown>;
    setWeakSegments(weakSegmentsFromEvaluation(avaliacaoUi, mappedSegments));

    const rawBulk = (derived.segmentos_reescritos ?? {}) as Record<string, string>;
    const bulk: Record<number, string> = {};
    for (const [key, value] of Object.entries(rawBulk)) {
      const index = Number(key);
      if (Number.isFinite(index) && value.trim()) bulk[index] = value;
    }
    setBulkRewrites(bulk);
    bulkRewritesRef.current = bulk;

    const evalMapped = evaluationFromUi(
      avaliacaoUi,
      (state.avaliacao_post ?? {}) as Record<string, unknown>,
    );
    setEvaluation(evalMapped.evaluation);
    setEvalScore(evalMapped.evalScore);

    setExportPath(String(derived.default_export_path ?? ""));
    setIsTrilhaVisual(Boolean(derived.is_trilha_visual));
    const activeStatus = String(derived.active_status_text ?? "");
    setStatusText(activeStatus || String(state.status_operacional ?? ""));
    setError(state.error ? String(state.error) : null);

    const ser = (derived.serialized ?? {}) as Record<string, string>;
    setSerialized(ser);
    setSnapshot(data);

    const effective = (derived.effective_llm_config ?? {}) as Record<string, Record<string, unknown>>;
    if (Object.keys(effective).length > 0) {
      setOps(opsFromConfig({ operations: {}, operation_labels: {}, providers: [], provider_status: [] }, effective));
    }
    if (Array.isArray(options.provider_status)) {
      setProviders(providersFromStatus(options.provider_status as Array<{ id: string; label: string; available: boolean }>));
    }
  }, []);

  const withAction = useCallback(async (
    actionName: string,
    body: Record<string, unknown> = {},
    visualPhase?: Phase,
    keepStage?: StageId,
  ) => {
    setBusy(true);
    if (visualPhase) setPhase(visualPhase);
    try {
      const data = await runAction(actionName, {
        state: draftRef.current,
        ...body,
      });
      applySnapshot(data, keepStage ?? stage);
      settle(visualPhase ? "success" : "idle", "idle");
      return data;
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message);
      setPhase("error");
      throw err;
    } finally {
      setBusy(false);
    }
  }, [applySnapshot, phase, settle, stage]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setBusy(true);
      try {
        const [sessionData, llmData] = await Promise.all([fetchSession(), fetchLlmConfig()]);
        if (cancelled) return;
        applySnapshot(sessionData);
        setOps(opsFromConfig(llmData, (sessionData.derived.effective_llm_config ?? {}) as Record<string, Record<string, unknown>>));
        setProviders(providersFromStatus(llmData.provider_status));
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : String(err));
      } finally {
        if (!cancelled) setBusy(false);
      }
    })();
    return () => { cancelled = true; };
  }, [applySnapshot]);

  useEffect(() => {
    const map: Record<Phase, [number, number, number, number]> = {
      idle: [252, 0.04, 0.7, 0.1],
      interviewing: [168, 0.12, 0.74, 0.22],
      compiling: [268, 0.13, 0.72, 0.24],
      generating: [52, 0.16, 0.78, 0.34],
      segmenting: [22, 0.15, 0.76, 0.28],
      evaluating: [205, 0.13, 0.74, 0.26],
      success: [150, 0.15, 0.78, 0.26],
      error: [27, 0.19, 0.66, 0.32],
    };
    const [h, c, l, a] = map[phase];
    const r = document.documentElement;
    r.style.setProperty("--flux-hue", String(h));
    r.style.setProperty("--flux-chroma", String(c));
    r.style.setProperty("--flux-l", String(l));
    r.style.setProperty("--amb", String(a));
  }, [phase]);

  const goto = useCallback(async (s: StageId) => {
    if (s === "agents") {
      setStage("agents");
      return;
    }
    setStage(s);
    const targetPhase = phaseFromStage(s);
    const body = targetPhase ? { phase: targetPhase } : { stage: s };
    await withAction("navigate", body, undefined, s);
  }, [withAction]);

  const updateOp = useCallback((id: string, patch: Partial<OperationConfig>) => {
    setOps((o) => o.map((op) => (op.id === id ? { ...op, ...patch } : op)));
  }, []);

  const saveOps = useCallback(async () => {
    setBusy(true);
    setPhase("compiling");
    try {
      await saveLlmConfig(llmConfigPayloadFromOps(ops));
      settle("success", "idle");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setPhase("error");
    } finally {
      setBusy(false);
    }
  }, [ops, settle]);

  const setSession = useCallback((patch: Partial<Store["session"]>) => {
    setSessionState((s) => {
      const next = { ...s, ...patch };
      draftRef.current = {
        ...draftRef.current,
        tema: next.theme,
        plataforma: next.platformValue,
        tipo_de_post: next.contentTypeValue,
        objetivo_do_post: next.objective,
        personalidade: next.personality,
      };
      return next;
    });
  }, []);

  const syncDraftFromSession = useCallback(() => {
    draftRef.current = {
      ...draftRef.current,
      tema: session.theme,
      plataforma: session.platformValue,
      tipo_de_post: session.contentTypeValue,
      objetivo_do_post: session.objective,
      personalidade: session.personality,
    };
  }, [session]);

  const saveSession = useCallback(async () => {
    setBusy(true);
    try {
      const data = await patchSession(draftRef.current);
      applySnapshot(data, stage);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }, [applySnapshot, stage]);

  const reload = useCallback(async () => {
    setBusy(true);
    try {
      const data = await fetchSession();
      applySnapshot(data, stage);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }, [applySnapshot, stage]);

  const continueToInterview = useCallback(async () => {
    // draftRef já está atualizado pelo setSession quando o usuário muda os campos
    // Não chamar syncDraftFromSession aqui para evitar sobrescrever com valores desatualizados
    try {
      const data = await withAction("start_interview_v4", {}, "compiling");
      const interview = data?.state?.interview_state;
      const hasV4 =
        interview != null &&
        typeof interview === "object" &&
        !Array.isArray(interview) &&
        (interview as Record<string, unknown>).schema_version === "4.0";
      if (hasV4) {
        setStage("interview");
      }
      // Sem entrevista V4 (validação/erro precoce): permanece em entry; erro já vem no snapshot.
    } catch {
      // stay on entry stage if validation fails
    }
  }, [withAction]);

  const answerQuestion = useCallback((id: string, text: string) => {
    setRound((r) => r.map((q) => (q.id === id ? { ...q, answer: text } : q)));
  }, []);

  const submitRound = useCallback(async () => {
    const response = round[0]?.answer ?? "";
    await withAction("submit_v4_answer", { response }, "interviewing");
  }, [round, withAction]);

  const nextInterviewQuestion = useCallback(async () => {
    await withAction("generate_other_question", {}, "interviewing");
  }, [withAction]);

  const buildBriefing = useCallback(async () => {
    await withAction("continue_phase2", {}, "compiling");
    setStage("briefing");
  }, [withAction]);

  const generateStoryboard = useCallback(async () => {
    await withAction("generate_storyboard", {}, "generating");
    setStage("storyboard");
  }, [withAction]);

  const updateStoryboard = useCallback(async (blocks: Array<{ id: string; role: string; focus: string; revision?: number }>) => {
    await withAction("update_storyboard", { blocks }, "compiling");
  }, [withAction]);

  const generateBlockDrafts = useCallback(async (blockId: string) => {
    await withAction("generate_block_drafts", { block_id: blockId }, "generating");
  }, [withAction]);

  const generateAllBlockDrafts = useCallback(async () => {
    await withAction("generate_all_block_drafts", {}, "generating");
  }, [withAction]);

  const retryBlockDraft = useCallback(async (blockId: string, optionId: string) => {
    await withAction("retry_block_draft", { block_id: blockId, option_id: optionId }, "generating");
  }, [withAction]);

  const selectBlockDraft = useCallback(async (blockId: string, optionId: string) => {
    await withAction("select_block_draft", { block_id: blockId, option_id: optionId });
  }, [withAction]);

  const composeEditorial = useCallback(async () => {
    await withAction("compose_editorial", {}, "generating");
    setStage("segmentation");
  }, [withAction]);

  const renderPrompt = useCallback(async () => {
    await withAction("render_prompt", {}, "compiling");
  }, [withAction]);

  const runGeneration = useCallback(async () => {
    setRunState("running");
    await withAction("run", {}, "generating");
  }, [withAction]);

  const clearOutput = useCallback(async () => {
    await withAction("clear_outputs");
  }, [withAction]);

  const segment = useCallback(async () => {
    await withAction("segment", {}, "segmenting");
  }, [withAction]);

  const requestAdjust = useCallback(async (index: number, request: string) => {
    pendingAdjustRef.current[index] = { request, version: "" };
    await withAction("rewrite_segment", { index, pedido: request }, "compiling");
  }, [withAction]);

  const applyAdjust = useCallback(async (index: number) => {
    await withAction("apply_segment", { index });
    delete pendingAdjustRef.current[index];
  }, [withAction]);

  const discardAdjust = useCallback(async (_index?: number) => {
    await withAction("cancel_adjust");
    pendingAdjustRef.current = {};
  }, [withAction]);

  const requestBulkAdjust = useCallback(async (
    ajustes: Array<{ index: number; pedido: string }>,
  ) => {
    await withAction("rewrite_segments_bulk", { ajustes }, "compiling", stage);
  }, [stage, withAction]);

  const applyBulkAdjust = useCallback(async (index: number) => {
    const textos: Record<string, string> = {};
    const texto = bulkRewritesRef.current[index];
    if (texto) textos[String(index)] = texto;
    await withAction("apply_segments_bulk", { indices: [index], textos }, undefined, stage);
  }, [stage, withAction]);

  const applyAllBulkAdjust = useCallback(async () => {
    const textos: Record<string, string> = {};
    for (const [index, texto] of Object.entries(bulkRewritesRef.current)) {
      textos[String(index)] = texto;
    }
    await withAction("apply_segments_bulk", { textos }, undefined, stage);
  }, [stage, withAction]);

  const discardBulkAdjust = useCallback(async () => {
    await withAction("cancel_bulk_adjust");
    setBulkRewrites({});
  }, [withAction]);

  const reBulkAdjustItem = useCallback(async (index: number, pedido: string) => {
    const data = await withAction("rewrite_segment", { index, pedido }, "compiling", stage);
    const derived = data.derived as Record<string, unknown>;
    const reescrito = String(derived.segmento_reescrito ?? "").trim();
    if (reescrito) {
      setBulkRewrites((prev) => {
        const next = { ...prev, [index]: reescrito };
        bulkRewritesRef.current = next;
        return next;
      });
    }
  }, [stage, withAction]);

  const evaluate = useCallback(async () => {
    await withAction("evaluate", {}, "evaluating");
  }, [withAction]);

  const doExport = useCallback(async (kind: "markdown" | "slidemark") => {
    setExportState((e) => ({ ...e, [kind]: "running" }));
    setPhase(kind === "slidemark" ? "generating" : "compiling");
    try {
      const action = kind === "slidemark" ? "export_slidemark" : "export";
      await withAction(action, { path: exportPath });
      setExportState((e) => ({ ...e, [kind]: "done" }));
    } catch {
      setExportState((e) => ({ ...e, [kind]: "idle" }));
    }
  }, [exportPath, withAction]);

  const focus = useCallback((index: number | null) => {
    setFocusSegment(index);
    if (index !== null) {
      draftRef.current = { ...draftRef.current, _segmento_index: index };
    }
  }, []);

  const resetContext = useCallback(async () => {
    pendingAdjustRef.current = {};
    setBulkRewrites({});
    setExportState({ markdown: "idle", slidemark: "idle" });
    await withAction("reset_context");
    setStage("entry");
  }, [withAction]);

  const restore = useCallback(async () => {
    try {
      const parsed = JSON.parse(restoreText) as Record<string, unknown>;
      // Aceita JSON flat (persistencia) ou copia da aba PAYLOAD com `state` aninhado.
      const nested = parsed.state;
      const statePayload =
        nested && typeof nested === "object" && !Array.isArray(nested)
          ? (nested as Record<string, unknown>)
          : parsed;
      setBusy(true);
      const data = await restoreSession(statePayload);
      applySnapshot(data);
      setRestoreText("");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }, [applySnapshot, restoreText]);

  const value: Store = {
    busy, error, statusText, stage, reachable, phase, ops, providers, session,
    axes, interviewUi, editorialFeedback, round, rounds, briefingReady, briefingCards,
    promptRendered, promptText, events, runState, returnCode, rawOutput, segments,
    weakSegments, bulkRewrites, evaluation, evalScore, exportState, exportPath, isTrilhaVisual, focusSegment,
    snapshot, actionState: draftRef.current, serialized, restoreText, interviewFocus,
    editorialFlow, editorialStatus, storyboardBlocks, draftByBlock,
    goto, setPhase, setInterviewFocus, updateOp, saveOps, setSession, saveSession, reload,
    continueToInterview, answerQuestion, submitRound, nextInterviewQuestion, buildBriefing,
    generateStoryboard, updateStoryboard, generateBlockDrafts, generateAllBlockDrafts,
    retryBlockDraft, selectBlockDraft, composeEditorial,
    renderPrompt, runGeneration, clearOutput, segment, requestAdjust, applyAdjust,
    discardAdjust, requestBulkAdjust, applyBulkAdjust, applyAllBulkAdjust,
    discardBulkAdjust, reBulkAdjustItem, evaluate, doExport, focus, resetContext, restore, setRestoreText,
    setExportPath,
  };

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function usePE() {
  const c = useContext(Ctx);
  if (!c) throw new Error("usePE must be used within PostEngineProvider");
  return c;
}
