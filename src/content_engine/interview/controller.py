"""Orquestracao de uma rodada completa da entrevista V4."""
from __future__ import annotations

from typing import Any

from .extraction import append_extraction, append_answer, extract_signals
from .exploration import generate_next_question
from .gap_diagnosis import generate_gap_diagnosis
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
        title_runner: Any | None = None,
        gap_runner: Any | None = None,
        question_tool: str = "codex",
        evaluation_tool: str = "codex",
        title_tool: str = "opencode",
        gap_tool: str = "opencode",
        question_generation_model: str | None = None,
        evaluation_model: str | None = None,
        title_model: str | None = None,
        gap_model: str | None = None,
        question_reasoning_effort: str | None = None,
        evaluation_reasoning_effort: str | None = None,
        title_reasoning_effort: str | None = None,
        gap_reasoning_effort: str | None = None,
        question_sandbox: str | None = None,
        evaluation_sandbox: str | None = None,
        title_sandbox: str | None = None,
        gap_sandbox: str | None = None,
        validate_tool: str = "codex",
        validate_model: str | None = None,
        validate_reasoning_effort: str | None = None,
        validate_sandbox: str | None = None,
    ) -> None:
        self.state = state
        self.question_runner = question_runner if question_runner is not None else runner
        self.evaluation_runner = evaluation_runner if evaluation_runner is not None else runner
        self.title_runner = title_runner if title_runner is not None else runner
        self.gap_runner = gap_runner if gap_runner is not None else (
            evaluation_runner if evaluation_runner is not None else runner
        )
        self.question_tool = question_tool
        self.evaluation_tool = evaluation_tool
        self.title_tool = title_tool
        self.gap_tool = gap_tool
        self.question_generation_model = question_generation_model
        self.evaluation_model = evaluation_model
        self.title_model = title_model
        self.gap_model = gap_model
        self.question_reasoning_effort = question_reasoning_effort
        self.evaluation_reasoning_effort = evaluation_reasoning_effort
        self.title_reasoning_effort = title_reasoning_effort
        self.gap_reasoning_effort = gap_reasoning_effort
        self.question_sandbox = question_sandbox
        self.evaluation_sandbox = evaluation_sandbox
        self.title_sandbox = title_sandbox
        self.gap_sandbox = gap_sandbox
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

    def generate_next_question(self, *, extension_mode: bool = False) -> SelectedQuestion | None:
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
            title_runner=self.title_runner,
            title_tool=self.title_tool,
            title_model=self.title_model,
            title_reasoning_effort=self.title_reasoning_effort,
            title_sandbox=self.title_sandbox,
            extension_mode=extension_mode,
        )

    def ingest_answer(
        self,
        response: str,
        *,
        question: SelectedQuestion | str | None = None,
    ) -> None:
        if not str(response or "").strip():
            raise ValueError("resposta nao pode ser vazia")
        selected = question or self.state.current_question or ""
        if not selected:
            raise ValueError("pergunta atual nao encontrada")
        answer = append_answer(self.state, selected, response)
        extraction = extract_signals(answer)
        append_extraction(self.state, extraction)
        self.state.current_question = None

    def evaluate_material(
        self,
        *,
        user_requested_end: bool = False,
        llm_assessment: LlmAssessment | None = None,
    ) -> DeepeningDecision:
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

    def process_answer(
        self,
        response: str,
        *,
        question: SelectedQuestion | str | None = None,
        user_requested_end: bool = False,
        llm_assessment: LlmAssessment | None = None,
    ) -> DeepeningDecision:
        self.ingest_answer(response, question=question)
        return self.evaluate_material(
            user_requested_end=user_requested_end,
            llm_assessment=llm_assessment,
        )

    def run_round(self, response: str, **kwargs: Any) -> DeepeningDecision:
        return self.process_answer(response, **kwargs)

    def diagnose_gaps(self, *, force: bool = False) -> str:
        return generate_gap_diagnosis(
            self.gap_runner,
            self.state,
            tool=self.gap_tool,
            model=self.gap_model,
            reasoning_effort=self.gap_reasoning_effort,
            sandbox=self.gap_sandbox,
            force=force,
        )

    def start_extension_batch(self, count: int = 5) -> list[SelectedQuestion]:
        if count < 1:
            raise ValueError("count deve ser >= 1")
        if self.state.gateway_result is not None and self.state.gateway_result.approved:
            raise ValueError("Gateway ja aprovou; lote de extensao nao se aplica.")
        if self.state.pending_batch:
            raise ValueError("Ja existe um lote de extensao pendente.")
        if self.question_runner is None:
            raise ValueError("Geracao de perguntas nao configurada.")

        self.state.current_question = None
        self.state.max_questions += count
        batch: list[SelectedQuestion] = []
        for _ in range(count):
            question = self.generate_next_question(extension_mode=True)
            if question is None:
                break
            batch.append(question)

        if len(batch) != count:
            # Roll back partial generation into pending so the UI can still show
            # what was produced, but fail the action contract (exact count).
            self.state.pending_batch = list(batch)
            self.state.current_question = None
            raise ValueError(
                f"Nao foi possivel gerar {count} perguntas de extensao "
                f"(obtidas: {len(batch)})."
            )

        self.state.pending_batch = list(batch)
        self.state.pending_answers = {}
        self.state.current_question = None
        self.state.progress_state = "APROFUNDANDO"
        self.state.closure_reason = ""
        return list(batch)

    def submit_extension_batch(
        self,
        responses: list[dict[str, Any]] | tuple[dict[str, Any], ...],
        *,
        llm_assessment: LlmAssessment | None = None,
    ) -> DeepeningDecision:
        pending = list(self.state.pending_batch)
        if not pending:
            raise ValueError("Nenhum lote de extensao pendente.")
        if len(responses) != len(pending):
            raise ValueError(
                f"Lote exige {len(pending)} respostas; recebidas {len(responses)}."
            )

        for question, raw in zip(pending, responses, strict=True):
            if not isinstance(raw, dict):
                raise ValueError("Cada item de responses deve ser um objeto {question, answer}.")
            answer = str(raw.get("answer", raw.get("response", ""))).strip()
            if not answer:
                raise ValueError("Todas as respostas do lote devem ser nao vazias.")
            q_text = str(raw.get("question", "")).strip()
            if q_text and q_text != question.question:
                raise ValueError(f"Pergunta do lote nao confere: {q_text}")
            self.ingest_answer(answer, question=question)

        # After the extension questions were generated, question_count == max_questions,
        # so decide_deepening closes without asking again.
        decision = self.evaluate_material(
            user_requested_end=False,
            llm_assessment=llm_assessment,
        )
        self.state.pending_batch = []
        self.state.pending_answers = {}
        self.state.extension_batches_completed += 1
        if self.state.gateway_result and self.state.gateway_result.approved:
            self.state.progress_state = "MATERIAL_SUFICIENTE"
            self.state.gap_diagnosis = ""
        else:
            self.state.progress_state = "CONCLUIDA"
            self.diagnose_gaps(force=True)
        return decision

    def explain_decision(self) -> str:
        if self.state.deepening_decision is None:
            return "Nenhuma decisao de entrevista registrada."
        return explain_decision(self.state.deepening_decision)

    def close(self, reason: str = "USUARIO_SOLICITOU_ENCERRAMENTO") -> None:
        self.state.current_question = None
        self.state.progress_state = "CONCLUIDA"
        self.state.closure_reason = reason


__all__ = ["InterviewController"]
