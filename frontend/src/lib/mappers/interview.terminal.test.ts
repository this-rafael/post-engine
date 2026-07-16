/**
 * Focused contract tests for interview terminal mapper.
 * Run: node --experimental-strip-types --test src/lib/mappers/interview.terminal.test.ts
 */
import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  deriveInterviewTerminal,
  questionsFromInterview,
  type InterviewUi,
} from "./interview.ts";

function terminalUi(overrides: Partial<InterviewUi> = {}): InterviewUi {
  return {
    progress_state: "CONCLUIDA",
    question_count: 12,
    max_questions: 12,
    closure_reason: "LIMITE_DE_PERGUNTAS_ATINGIDO",
    gateway: { approved: false },
    gap_diagnosis: "Falta episodio concreto.",
    extension_batches_completed: 0,
    history: [
      { question: "Pergunta antiga?", answer: "resposta antiga", answer_id: "h1" },
    ],
    ...overrides,
  };
}

describe("questionsFromInterview", () => {
  it("prefers pending_batch as the active round", () => {
    const ui = terminalUi({
      progress_state: "APROFUNDANDO",
      closure_reason: "",
      pending_batch: [
        { question: "Q1 lote?", id: "b1" },
        { question: "Q2 lote?", id: "b2" },
      ],
      current_question: { question: "nao deve usar" },
    });
    const questions = questionsFromInterview(ui);
    assert.equal(questions.length, 2);
    assert.equal(questions[0]?.prompt, "Q1 lote?");
    assert.equal(questions[0]?.answer, "");
    assert.equal(questions[1]?.prompt, "Q2 lote?");
  });

  it("does not remount history as round when CONCLUIDA", () => {
    const questions = questionsFromInterview(terminalUi());
    assert.deepEqual(questions, []);
  });

  it("still exposes current_question when present without pending_batch", () => {
    const ui = terminalUi({
      progress_state: "APROFUNDANDO",
      closure_reason: "",
      current_question: { question: "Atual?", id: "c1", why_now: "porque" },
      history: [{ question: "hist", answer: "a" }],
    });
    const questions = questionsFromInterview(ui);
    assert.equal(questions.length, 1);
    assert.equal(questions[0]?.prompt, "Atual?");
    assert.equal(questions[0]?.rationale, "porque");
  });
});

describe("deriveInterviewTerminal", () => {
  it("marks limit/unapproved state as terminal with only extend CTA", () => {
    const terminal = deriveInterviewTerminal(terminalUi());
    assert.equal(terminal.isTerminal, true);
    assert.equal(terminal.canExtend, true);
    assert.equal(terminal.canForceFinish, false);
    assert.equal(terminal.canRestart, false);
    assert.equal(terminal.gapDiagnosis, "Falta episodio concreto.");
    assert.deepEqual(terminal.counts, {
      questionCount: 12,
      maxQuestions: 12,
      extensionBatchesCompleted: 0,
    });
  });

  it("enables Finalizar/Reiniciar only after extension_batches_completed >= 1", () => {
    const before = deriveInterviewTerminal(terminalUi({ extension_batches_completed: 0 }));
    assert.equal(before.canForceFinish, false);
    assert.equal(before.canRestart, false);

    const after = deriveInterviewTerminal(terminalUi({ extension_batches_completed: 1 }));
    assert.equal(after.isTerminal, true);
    assert.equal(after.canExtend, true);
    assert.equal(after.canForceFinish, true);
    assert.equal(after.canRestart, true);
  });

  it("is not terminal while a pending_batch is active", () => {
    const terminal = deriveInterviewTerminal(
      terminalUi({
        progress_state: "APROFUNDANDO",
        pending_batch: [{ question: "Q1?" }],
      }),
    );
    assert.equal(terminal.isTerminal, false);
    assert.equal(terminal.canExtend, false);
    assert.equal(terminal.canForceFinish, false);
  });
});
