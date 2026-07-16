import { useCallback, useEffect, useRef, useState } from "react";
import type { Question } from "@/lib/pe-types";
import { deriveInterviewTerminal, type InterviewUi } from "@/lib/mappers/interview";

export type InterviewUxPhase =
  | "answering"
  | "round_review"
  | "analyzing"
  | "coverage_updated"
  | "current_read"
  | "next_round_ready"
  | "terminal_gaps"
  | "map_mode";

export interface CoverageSnapshot {
  coveredTotal: number;
  totalAxes: number;
  axes: Array<{ key: string; covered: number; total: number }>;
  coveredAxisIds: Set<string>;
}

function snapshotCoverage(
  axes: Array<{ key: string; covered: number; total: number }>,
  coveredTotal: number,
  totalAxes: number,
  interviewUi: InterviewUi,
): CoverageSnapshot {
  const ids = new Set<string>();
  for (const dimension of interviewUi.dimensions ?? []) {
    if (dimension.covered) ids.add(dimension.id);
  }
  return { coveredTotal, totalAxes, axes: axes.map((a) => ({ ...a })), coveredAxisIds: ids };
}

export interface NewAxisCapture {
  groupLabel: string;
  axisLabel: string;
  axisId: string;
}

export function deriveNewAxes(
  before: CoverageSnapshot | null,
  after: CoverageSnapshot,
  interviewUi: InterviewUi,
): NewAxisCapture[] {
  if (!before) return [];
  const added: NewAxisCapture[] = [];
  for (const dimension of interviewUi.dimensions ?? []) {
    if (dimension.covered && !before.coveredAxisIds.has(dimension.id)) {
      added.push({
        groupLabel: "Dimensoes autorais V4",
        axisLabel: dimension.label,
        axisId: dimension.id,
      });
    }
  }
  return added;
}

function resolvePostAnalysisPhase(
  interviewUi: InterviewUi,
  editorialFeedback: string | null,
  added: NewAxisCapture[],
): InterviewUxPhase {
  if (deriveInterviewTerminal(interviewUi).isTerminal) {
    return "terminal_gaps";
  }
  if (added.length > 0) return "coverage_updated";
  if (editorialFeedback) return "current_read";
  return "next_round_ready";
}

export function useInterviewUx({
  round,
  axes,
  coveredTotal,
  totalAxes,
  interviewUi,
  busy,
  phase,
  editorialFeedback,
}: {
  round: Question[];
  axes: Array<{ key: string; covered: number; total: number; label: string }>;
  coveredTotal: number;
  totalAxes: number;
  interviewUi: InterviewUi;
  busy: boolean;
  phase: string;
  editorialFeedback: string | null;
}) {
  const [uxPhase, setUxPhase] = useState<InterviewUxPhase>("answering");
  const [currentIndex, setCurrentIndex] = useState(0);
  const [focusMode, setFocusMode] = useState(false);
  const [contextCollapsed, setContextCollapsed] = useState(false);

  const preSubmitRef = useRef<CoverageSnapshot | null>(null);
  const [newAxes, setNewAxes] = useState<NewAxisCapture[]>([]);
  const wasAnalyzingRef = useRef(false);

  const answered = round.filter((q) => q.answer.trim().length > 0).length;
  const allAnswered = round.length > 0 && answered === round.length;
  const terminal = deriveInterviewTerminal(interviewUi);

  const goToQuestion = useCallback(
    (index: number) => {
      if (!round.length) return;
      const clamped = Math.max(0, Math.min(round.length - 1, index));
      setCurrentIndex(clamped);
      if (uxPhase === "round_review" || uxPhase === "next_round_ready") {
        setUxPhase("answering");
      }
    },
    [round.length, uxPhase],
  );

  const nextQuestion = useCallback(() => {
    if (currentIndex < round.length - 1) {
      setCurrentIndex((i) => i + 1);
    } else if (allAnswered) {
      setUxPhase("round_review");
    }
  }, [currentIndex, round.length, allAnswered]);

  const prevQuestion = useCallback(() => {
    if (currentIndex > 0) setCurrentIndex((i) => i - 1);
  }, [currentIndex]);

  const enterReview = useCallback(() => {
    if (allAnswered) setUxPhase("round_review");
  }, [allAnswered]);

  const backToAnswering = useCallback(() => {
    setUxPhase("answering");
  }, []);

  const beginAnalysis = useCallback(() => {
    preSubmitRef.current = snapshotCoverage(axes, coveredTotal, totalAxes, interviewUi);
    setUxPhase("analyzing");
    wasAnalyzingRef.current = true;
  }, [axes, coveredTotal, totalAxes, interviewUi]);

  const openMapMode = useCallback(() => setUxPhase("map_mode"), []);
  const closeMapMode = useCallback(() => setUxPhase("answering"), []);

  const continueFromCoverage = useCallback(() => {
    if (deriveInterviewTerminal(interviewUi).isTerminal) {
      setUxPhase("terminal_gaps");
      return;
    }
    setUxPhase(editorialFeedback ? "current_read" : "next_round_ready");
  }, [editorialFeedback, interviewUi]);

  const continueFromRead = useCallback(() => {
    if (deriveInterviewTerminal(interviewUi).isTerminal) {
      setUxPhase("terminal_gaps");
      return;
    }
    setUxPhase("next_round_ready");
  }, [interviewUi]);

  const resetAfterNewRound = useCallback(() => {
    setCurrentIndex(0);
    setUxPhase("answering");
    setNewAxes([]);
    preSubmitRef.current = null;
    wasAnalyzingRef.current = false;
  }, []);

  const enterTerminalGaps = useCallback(() => {
    setUxPhase("terminal_gaps");
  }, []);

  useEffect(() => {
    if (uxPhase === "analyzing" && !busy && wasAnalyzingRef.current) {
      wasAnalyzingRef.current = false;
      const after = snapshotCoverage(axes, coveredTotal, totalAxes, interviewUi);
      const added = deriveNewAxes(preSubmitRef.current, after, interviewUi);
      setNewAxes(added);
      setUxPhase(resolvePostAnalysisPhase(interviewUi, editorialFeedback, added));
    }
  }, [busy, uxPhase, axes, coveredTotal, totalAxes, interviewUi, editorialFeedback]);

  useEffect(() => {
    if (uxPhase === "analyzing" && phase === "error") {
      wasAnalyzingRef.current = false;
      setUxPhase("round_review");
    }
  }, [uxPhase, phase]);

  useEffect(() => {
    if (currentIndex >= round.length && round.length > 0) {
      setCurrentIndex(round.length - 1);
    }
  }, [round.length, currentIndex]);

  // Hydrate terminal screen when snapshot is already closed without an active round.
  useEffect(() => {
    if (!terminal.isTerminal) return;
    if (busy) return;
    if (round.length > 0) return;
    if (
      uxPhase === "answering" ||
      uxPhase === "next_round_ready" ||
      (uxPhase === "current_read" && !editorialFeedback)
    ) {
      setUxPhase("terminal_gaps");
    }
  }, [terminal.isTerminal, busy, round.length, uxPhase, editorialFeedback]);

  // After extension batch generation, leave terminal and answer the new questions.
  useEffect(() => {
    if (uxPhase !== "terminal_gaps") return;
    if (round.length === 0) return;
    if (terminal.isTerminal) return;
    resetAfterNewRound();
  }, [uxPhase, round.length, terminal.isTerminal, resetAfterNewRound]);

  return {
    uxPhase,
    setUxPhase,
    currentIndex,
    currentQuestion: round[currentIndex] ?? null,
    answered,
    allAnswered,
    focusMode,
    setFocusMode,
    contextCollapsed,
    setContextCollapsed,
    goToQuestion,
    nextQuestion,
    prevQuestion,
    enterReview,
    backToAnswering,
    beginAnalysis,
    openMapMode,
    closeMapMode,
    continueFromCoverage,
    continueFromRead,
    resetAfterNewRound,
    enterTerminalGaps,
    terminal,
    newAxes,
    preSubmitCoverage: preSubmitRef.current,
  };
}
