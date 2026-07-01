"""Orquestracao de uma rodada completa da entrevista V4."""
from __future__ import annotations

from typing import Any

from .extraction import append_extraction, append_answer, extract_signals
from .exploration import generate_next_question
from .gaps import decide_deepening, explain_decision, identify_gaps
from .gateway import evaluate_gateway
from .heuristic import assess_dimensions
from .llm_evaluation import evaluate_authorship_llm
from .schemas import (
    DeepeningDecision,
    InterviewState,
    LlmAssessment,
    SelectedQuestion,
)


class InterviewController:
    def __init__(
        self,
        state: InterviewState,
        runner: Any | None = None,
        *,
        question_runner: Any | None = None,
        evaluation_runner: Any | None = None,
        question_tool: str = "codex",
        evaluation_tool: str = "codex",
        question_generation_model: str | None = None,
        evaluation_model: str | None = None,
        question_reasoning_effort: str | None = None,
        evaluation_reasoning_effort: str | None = None,
        question_sandbox: str | None = None,
        evaluation_sandbox: str | None = None,
        validate_tool: str = "codex",
        validate_model: str | None = None,
        validate_reasoning_effort: str | None = None,
        validate_sandbox: str | None = None,
    ) -> None:
        self.state = state
        self.question_runner = question_runner if question_runner is not None else runner
        self.evaluation_runner = evaluation_runner if evaluation_runner is not None else runner
        self.question_tool = question_tool
        self.evaluation_tool = evaluation_tool
        self.question_generation_model = question_generation_model
        self.evaluation_model = evaluation_model
        self.question_reasoning_effort = question_reasoning_effort
        self.evaluation_reasoning_effort = evaluation_reasoning_effort
        self.question_sandbox = question_sandbox
        self.evaluation_sandbox = evaluation_sandbox
        self.validate_tool = validate_tool
        self.validate_model = validate_model
        self.validate_reasoning_effort = validate_reasoning_effort
        self.validate_sandbox = validate_sandbox

    def start(self) -> SelectedQuestion | None:
        if self.state.current_question is not None:
            return self.state.current_question
        if self.question_runner is None or self.state.question_count >= self.state.max_questions:
            return None
        return self.generate_next_question()

    def generate_next_question(self) -> SelectedQuestion | None:
        if self.question_runner is None:
            return None
        if self.state.question_count >= self.state.max_questions:
            return None
        return generate_next_question(
            self.question_runner,
            self.state,
            tool=self.question_tool,
            model=self.question_generation_model,
            reasoning_effort=self.question_reasoning_effort,
            sandbox=self.question_sandbox,
            validate_tool=self.validate_tool,
            validate_model=self.validate_model,
            validate_reasoning_effort=self.validate_reasoning_effort,
            validate_sandbox=self.validate_sandbox,
        )

    def process_answer(
        self,
        response: str,
        *,
        question: SelectedQuestion | str | None = None,
        user_requested_end: bool = False,
        llm_assessment: LlmAssessment | None = None,
    ) -> DeepeningDecision:
        if not str(response or "").strip():
            raise ValueError("resposta nao pode ser vazia")
        selected = question or self.state.current_question or ""
        if not selected:
            raise ValueError("pergunta atual nao encontrada")
        answer = append_answer(self.state, selected, response)
        extraction = extract_signals(answer)
        append_extraction(self.state, extraction)

        deterministic = assess_dimensions(self.state, formato=self.state.context.formato)
        self.state.deterministic_assessment = deterministic
        self.state.dimensions = dict(deterministic.dimensions)
        self.state.gaps = identify_gaps(self.state, formato=self.state.context.formato)

        if llm_assessment is not None:
            semantic = llm_assessment
        elif self.evaluation_runner is not None:
            semantic = evaluate_authorship_llm(
                self.evaluation_runner,
                self.state,
                tool=self.evaluation_tool,
                model=self.evaluation_model,
                reasoning_effort=self.evaluation_reasoning_effort,
                sandbox=self.evaluation_sandbox,
            )
        else:
            semantic = LlmAssessment(
                approved=False,
                parse_error="avaliacao LLM nao configurada",
                source="not_configured",
            )
        self.state.llm_assessment = semantic
        self.state.gateway_result = evaluate_gateway(
            deterministic,
            semantic,
            gaps=self.state.gaps,
            formato=self.state.context.formato,
        )
        decision = decide_deepening(
            self.state.gaps,
            self.state.gateway_result,
            question_count=self.state.question_count,
            max_questions=self.state.max_questions,
            user_requested_end=user_requested_end,
        )
        self.state.deepening_decision = decision
        self.state.current_question = None
        if decision.should_ask:
            self.state.progress_state = "APROFUNDANDO"
        elif self.state.gateway_result.approved:
            self.state.progress_state = "MATERIAL_SUFICIENTE"
            self.state.closure_reason = decision.closure_reason or "GATEWAY_APROVADO"
        else:
            self.state.progress_state = "CONCLUIDA"
            self.state.closure_reason = decision.closure_reason or "GANHO_MARGINAL_BAIXO"
        return decision

    def run_round(self, response: str, **kwargs: Any) -> DeepeningDecision:
        return self.process_answer(response, **kwargs)

    def explain_decision(self) -> str:
        if self.state.deepening_decision is None:
            return "Nenhuma decisao de entrevista registrada."
        return explain_decision(self.state.deepening_decision)

    def close(self, reason: str = "USUARIO_SOLICITOU_ENCERRAMENTO") -> None:
        self.state.current_question = None
        self.state.progress_state = "CONCLUIDA"
        self.state.closure_reason = reason


__all__ = ["InterviewController"]
