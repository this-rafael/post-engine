import { AnimatePresence, motion } from "motion/react";
import { useEffect } from "react";
import { usePE } from "@/lib/pe-store";
import { AnimatedNumber, PeButton } from "../ui";
import { StageHeader } from "./common";
import { cn } from "@/lib/utils";
import { AuthorContextCompact } from "../interview/AuthorContextCompact";
import { AuthorContextMapMode } from "../interview/AuthorContextMapMode";
import { AnalyzingState } from "../interview/AnalyzingState";
import { CoverageUpdated } from "../interview/CoverageUpdated";
import { CurrentReadMoment } from "../interview/CurrentReadMoment";
import { QuestionStage } from "../interview/QuestionStage";
import { RoundNavigator } from "../interview/RoundNavigator";
import { RoundReview } from "../interview/RoundReview";
import { TerminalGaps } from "../interview/TerminalGaps";
import { useInterviewUx } from "../interview/useInterviewUx";

export function InterviewStage() {
  const {
    round,
    axes,
    answerQuestion,
    submitRound,
    nextInterviewQuestion,
    diagnoseGaps,
    startExtensionBatch,
    submitExtensionBatch,
    forceFinishInterview,
    restartInterview,
    buildBriefing,
    rounds,
    phase,
    busy,
    interviewUi,
    editorialFeedback,
    setInterviewFocus,
  } = usePE();

  const coveredTotal = interviewUi.counter?.covered ?? axes.reduce((a, x) => a + x.covered, 0);
  const totalAxes = interviewUi.counter?.denominator ?? axes.reduce((a, x) => a + x.total, 0);
  const isExtensionRound = (interviewUi.pending_batch?.length ?? 0) > 0;

  const ux = useInterviewUx({
    round,
    axes,
    coveredTotal,
    totalAxes,
    interviewUi,
    busy,
    phase,
    editorialFeedback,
  });

  useEffect(() => {
    setInterviewFocus(ux.focusMode);
    return () => setInterviewFocus(false);
  }, [ux.focusMode, setInterviewFocus]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "f" && (e.metaKey || e.ctrlKey) && !e.shiftKey) {
        e.preventDefault();
        ux.setFocusMode((f) => !f);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [ux.setFocusMode]);

  const handleAnalyze = async () => {
    ux.beginAnalysis();
    if (isExtensionRound) {
      await submitExtensionBatch(
        round.map((q) => ({ question: q.prompt, answer: q.answer })),
      );
      return;
    }
    await submitRound();
  };

  const handleNewRound = async () => {
    await nextInterviewQuestion();
    ux.resetAfterNewRound();
  };

  const handleExtendBatch = async () => {
    await startExtensionBatch(5);
  };

  const highlightKeys = new Set(ux.newAxes.map((axis) => axis.axisId));

  const showSidebar =
    !ux.focusMode &&
    ux.uxPhase !== "map_mode" &&
    !["analyzing", "coverage_updated", "current_read", "terminal_gaps"].includes(ux.uxPhase);

  const showContextPanel = showSidebar && !ux.contextCollapsed;

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden">
      <div className="shrink-0 border-b border-hairline px-4 py-4 sm:px-8 sm:py-5">
        <StageHeader
          eyebrow={`02 / entrevista`}
          title={
            ux.uxPhase === "map_mode"
              ? "Mapa autoral"
              : "Alimentar a máquina com contexto humano"
          }
          desc={
            ux.uxPhase === "map_mode"
              ? "Explore dimensões, eixos e sinais capturados na entrevista."
              : "Responda uma pergunta por vez. Cada resposta enriquece o modelo autoral."
          }
          aside={
            ux.uxPhase === "answering" ? (
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => ux.setFocusMode((f) => !f)}
                  className={cn(
                    "rounded-md border px-2.5 py-1.5 font-mono text-[10px] uppercase tracking-wide transition-colors",
                    ux.focusMode
                      ? "border-[color-mix(in_oklab,var(--flux)_45%,transparent)] text-flux"
                      : "border-hairline text-ink-faint hover:text-ink-dim",
                  )}
                  title="Atalho: Ctrl+F"
                >
                  {ux.focusMode ? "Sair do foco" : "Focus mode"}
                </button>
                {!ux.focusMode && (
                  <button
                    type="button"
                    onClick={() => ux.setContextCollapsed((c) => !c)}
                    className="rounded-md border border-hairline px-2.5 py-1.5 font-mono text-[10px] uppercase tracking-wide text-ink-faint hover:text-ink-dim lg:hidden"
                  >
                    {ux.contextCollapsed ? "Contexto" : "Ocultar"}
                  </button>
                )}
              </div>
            ) : null
          }
        />

        {ux.uxPhase === "answering" && round.length > 0 && !ux.focusMode && (
          <div className="mt-4 space-y-3 lg:hidden">
            <RoundNavigator
              round={round}
              currentIndex={ux.currentIndex}
              roundNumber={rounds}
              onSelect={ux.goToQuestion}
            />
            <AuthorContextCompact
              coveredTotal={coveredTotal}
              totalAxes={totalAxes}
              axes={axes.map((a) => ({
                ...a,
                highlight: highlightKeys.has(a.key),
              }))}
              onExploreMap={ux.openMapMode}
            />
            {ux.allAnswered && (
              <PeButton variant="outline" className="w-full" onClick={ux.enterReview}>
                Revisar rodada →
              </PeButton>
            )}
          </div>
        )}

        {ux.uxPhase === "answering" && editorialFeedback && !ux.focusMode && (
          <motion.div
            layout
            className="mt-4 rounded-lg border border-[color-mix(in_oklab,var(--flux)_25%,transparent)] bg-[color-mix(in_oklab,var(--flux)_6%,var(--surface))] px-4 py-3"
          >
            <div className="mono-tag mb-1">leitura atual</div>
            <p className="text-[13.5px] leading-relaxed text-ink-dim">{editorialFeedback}</p>
          </motion.div>
        )}
      </div>

      <div className="flex min-h-0 flex-1 overflow-hidden">
        <div
          className={cn(
            "min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-5 sm:px-8 sm:py-6 [scrollbar-gutter:stable]",
            ux.focusMode && "flex items-start justify-center",
          )}
        >
          <div className={cn("w-full", !ux.focusMode && "max-w-3xl")}>
            <AnimatePresence mode="wait">
              {ux.uxPhase === "map_mode" ? (
                <AuthorContextMapMode
                  key="map"
                  interviewUi={interviewUi}
                  coveredTotal={coveredTotal}
                  totalAxes={totalAxes}
                  editorialFeedback={editorialFeedback}
                  onClose={ux.closeMapMode}
                />
              ) : ux.uxPhase === "round_review" ? (
                <RoundReview
                  key="review"
                  round={round}
                  roundNumber={rounds}
                  onEdit={ux.goToQuestion}
                  onBack={ux.backToAnswering}
                  onAnalyze={handleAnalyze}
                  loading={busy}
                />
              ) : ux.uxPhase === "analyzing" ? (
                <AnalyzingState
                  key="analyzing"
                  roundNumber={rounds}
                  answerCount={ux.answered}
                  phase={phase}
                  busy={busy}
                />
              ) : ux.uxPhase === "coverage_updated" ? (
                <CoverageUpdated
                  key="coverage"
                  newAxes={ux.newAxes}
                  coveredTotal={coveredTotal}
                  totalAxes={totalAxes}
                  prevCovered={ux.preSubmitCoverage?.coveredTotal ?? 0}
                  onContinue={ux.continueFromCoverage}
                />
              ) : ux.uxPhase === "current_read" && editorialFeedback ? (
                <CurrentReadMoment
                  key="read"
                  text={editorialFeedback}
                  onContinue={ux.continueFromRead}
                />
              ) : ux.uxPhase === "next_round_ready" ? (
                <NextRoundReady
                  key="next"
                  roundNumber={rounds}
                  editorialFeedback={editorialFeedback}
                  coveredTotal={coveredTotal}
                  totalAxes={totalAxes}
                  onContinue={handleNewRound}
                  onBriefing={() => buildBriefing()}
                  busy={busy}
                />
              ) : ux.uxPhase === "terminal_gaps" ? (
                <TerminalGaps
                  key="terminal"
                  terminal={ux.terminal}
                  busy={busy}
                  onDiagnose={diagnoseGaps}
                  onExtend={handleExtendBatch}
                  onForceFinish={forceFinishInterview}
                  onRestart={restartInterview}
                  onBriefing={buildBriefing}
                  gatewayApproved={Boolean(
                    interviewUi.gateway &&
                      typeof interviewUi.gateway === "object" &&
                      (interviewUi.gateway as Record<string, unknown>).approved,
                  )}
                />
              ) : round.length === 0 ? (
                <motion.div
                  key="empty"
                  className="panel grid min-h-[240px] place-items-center p-8"
                >
                  <p className="mono-tag">nenhuma pergunta V4 disponivel</p>
                  <PeButton
                    variant="flux"
                    className="mt-4"
                    onClick={handleNewRound}
                    loading={busy}
                  >
                    Gerar proxima pergunta →
                  </PeButton>
                </motion.div>
              ) : ux.currentQuestion ? (
                <QuestionStage
                  key="question"
                  question={ux.currentQuestion}
                  index={ux.currentIndex}
                  total={round.length}
                  groupLabel="Exploracao V4"
                  onAnswer={(t) => answerQuestion(ux.currentQuestion!.id, t)}
                  onPrev={ux.prevQuestion}
                  onNext={ux.nextQuestion}
                  onReview={ux.enterReview}
                  allAnswered={ux.allAnswered}
                  focusMode={ux.focusMode}
                />
              ) : null}
            </AnimatePresence>
          </div>
        </div>

        <AnimatePresence>
          {showContextPanel && round.length > 0 && (
            <motion.aside
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 280, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ type: "spring", stiffness: 300, damping: 32 }}
              className="hidden shrink-0 overflow-y-auto border-l border-hairline bg-surface/30 p-4 lg:block xl:w-[300px]"
            >
              <div className="space-y-4">
                <RoundNavigator
                  round={round}
                  currentIndex={ux.currentIndex}
                  roundNumber={rounds}
                  onSelect={ux.goToQuestion}
                />
                {ux.allAnswered && ux.uxPhase === "answering" && (
                  <PeButton variant="outline" className="w-full" onClick={ux.enterReview}>
                    Revisar rodada →
                  </PeButton>
                )}
                <AuthorContextCompact
                  coveredTotal={coveredTotal}
                  totalAxes={totalAxes}
                  axes={axes.map((a) => ({
                    ...a,
                    highlight: highlightKeys.has(a.key),
                  }))}
                  onExploreMap={ux.openMapMode}
                />
                {coveredTotal > 0 && (
                  <div className="rounded-lg border border-hairline bg-surface/50 p-3">
                    <p className="text-[11.5px] text-ink-faint">
                      Contexto suficiente? Avance quando a cobertura estiver adequada.
                    </p>
                    <PeButton
                      variant="ghost"
                      className="mt-2 w-full !text-[12px]"
                      onClick={() => buildBriefing()}
                      loading={busy}
                    >
                      Gerar briefing →
                    </PeButton>
                  </div>
                )}
              </div>
            </motion.aside>
          )}
        </AnimatePresence>
      </div>

      {ux.focusMode && round.length > 0 && ux.uxPhase === "answering" && (
        <div className="shrink-0 border-t border-hairline px-4 py-2 text-center font-mono text-[10px] text-ink-faint sm:px-8">
          {ux.answered} / {round.length} respondidas · Ctrl+F para sair do foco
        </div>
      )}
    </div>
  );
}

function NextRoundReady({
  roundNumber,
  editorialFeedback,
  coveredTotal,
  totalAxes,
  onContinue,
  onBriefing,
  busy,
}: {
  roundNumber: number;
  editorialFeedback: string | null;
  coveredTotal: number;
  totalAxes: number;
  onContinue: () => void;
  onBriefing: () => void;
  busy: boolean;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-1 flex-col items-center justify-center py-12 text-center"
    >
      <div className="mono-tag">rodada {String(roundNumber).padStart(2, "0")} analisada</div>
      <h2 className="mt-4 font-display text-[24px] font-semibold">Pronto para continuar</h2>
      <p className="mt-2 font-mono text-[13px] text-ink-faint">
        <AnimatedNumber value={coveredTotal} /> / {totalAxes} eixos capturados
      </p>
      {editorialFeedback && (
        <p className="mt-6 max-w-lg text-[14px] leading-relaxed text-ink-dim">{editorialFeedback}</p>
      )}
      <div className="mt-10 flex flex-wrap justify-center gap-3">
        <PeButton variant="flux" onClick={onContinue} loading={busy}>
          Continuar entrevista →
        </PeButton>
        {coveredTotal > 0 && (
          <PeButton variant="outline" onClick={onBriefing} loading={busy}>
            Gerar briefing →
          </PeButton>
        )}
      </div>
    </motion.div>
  );
}
