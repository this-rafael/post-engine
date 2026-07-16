"""Focused tests for interview terminal / extension-batch backend."""
from __future__ import annotations

import pytest

from content_engine.interview.controller import InterviewController
from content_engine.interview.gap_diagnosis import build_fallback_diagnosis, generate_gap_diagnosis
from content_engine.interview.schemas import (
    Gap,
    GatewayResult,
    InterviewState,
    LlmAssessment,
    SelectedQuestion,
    ThemeContext,
    UserAnswer,
)
from content_engine.interview.ui import build_interview_ui


def _terminal_state(**kwargs: object) -> InterviewState:
    base = {
        "context": ThemeContext("observabilidade", formato="post"),
        "progress_state": "CONCLUIDA",
        "question_count": 12,
        "max_questions": 12,
        "closure_reason": "LIMITE_DE_PERGUNTAS_ATINGIDO",
        "gaps": [
            Gap(
                type="falta_experiencia",
                dimension="experiencia_vivida",
                critical=True,
                reason="Falta um episodio concreto.",
            )
        ],
        "gateway_result": GatewayResult(
            approved=False,
            gateway_type="REPROVADO",
            weak_dimensions=("experiencia_vivida",),
            vetoes=("GENERICIDADE",),
            justification="Material generico sem episodio vivido.",
        ),
        "llm_assessment": LlmAssessment(
            approved=False,
            weaknesses=("Pouca concretude",),
        ),
    }
    base.update(kwargs)
    return InterviewState(**base)  # type: ignore[arg-type]


def test_interview_state_persists_terminal_fields() -> None:
    state = _terminal_state(
        extension_batches_completed=1,
        pending_batch=[SelectedQuestion(question="O que aconteceu na fila?")],
        pending_answers={"q1": "cresceu"},
        gap_diagnosis="Falta um caso concreto.",
    )
    restored = InterviewState.from_dict(state.to_dict())
    assert restored.extension_batches_completed == 1
    assert restored.pending_batch[0].question == "O que aconteceu na fila?"
    assert restored.pending_answers == {"q1": "cresceu"}
    assert restored.gap_diagnosis == "Falta um caso concreto."


def test_build_interview_ui_exposes_terminal_fields() -> None:
    state = _terminal_state(
        extension_batches_completed=2,
        pending_batch=[SelectedQuestion(question="Pergunta A")],
        gap_diagnosis="Precisa de trade-off real.",
    )
    ui = build_interview_ui(state)
    assert ui["gap_diagnosis"] == "Precisa de trade-off real."
    assert ui["extension_batches_completed"] == 2
    assert ui["pending_batch"][0]["question"] == "Pergunta A"
    assert ui["max_questions"] == 12
    assert ui["closure_reason"] == "LIMITE_DE_PERGUNTAS_ATINGIDO"
    assert ui["gateway"]["approved"] is False


def test_fallback_gap_diagnosis_uses_gateway_and_gaps() -> None:
    state = _terminal_state()
    text = build_fallback_diagnosis(state)
    assert "Material generico" in text
    assert "experiencia_vivida" in text


def test_generate_gap_diagnosis_is_idempotent_without_force() -> None:
    state = _terminal_state(gap_diagnosis="Diagnostico existente.")
    assert generate_gap_diagnosis(None, state) == "Diagnostico existente."
    assert generate_gap_diagnosis(None, state, force=True) != "Diagnostico existente."


def test_start_extension_batch_bumps_max_and_fills_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _terminal_state(gap_diagnosis="Falta concreto.")
    controller = InterviewController(state, question_runner=object())

    created: list[SelectedQuestion] = []

    def fake_generate(self: InterviewController, *, extension_mode: bool = False) -> SelectedQuestion:
        assert extension_mode is True
        q = SelectedQuestion(question=f"Q{len(created) + 1}")
        state.questions.append(q)
        state.question_count += 1
        state.current_question = q
        created.append(q)
        return q

    monkeypatch.setattr(InterviewController, "generate_next_question", fake_generate)

    batch = controller.start_extension_batch(count=5)
    assert len(batch) == 5
    assert state.max_questions == 17
    assert state.question_count == 17
    assert len(state.pending_batch) == 5
    assert state.current_question is None
    assert state.progress_state == "APROFUNDANDO"


def test_start_extension_batch_rejects_when_approved() -> None:
    state = _terminal_state(
        gateway_result=GatewayResult(approved=True, gateway_type="EQUILIBRADO"),
    )
    controller = InterviewController(state, question_runner=object())
    with pytest.raises(ValueError, match="aprovou"):
        controller.start_extension_batch()


def test_submit_extension_batch_requires_full_answers_and_increments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pending = [SelectedQuestion(question=f"Q{i}") for i in range(1, 6)]
    state = _terminal_state(
        max_questions=17,
        question_count=17,
        pending_batch=list(pending),
        progress_state="APROFUNDANDO",
        gap_diagnosis="antigo",
    )
    controller = InterviewController(state)

    with pytest.raises(ValueError, match="5 respostas"):
        controller.submit_extension_batch([{"question": "Q1", "answer": "a"}])

    with pytest.raises(ValueError, match="nao vazias"):
        controller.submit_extension_batch(
            [{"question": q.question, "answer": ""} for q in pending]
        )

    ingested: list[str] = []

    def fake_ingest(self: InterviewController, response: str, *, question=None) -> None:
        ingested.append(response)

    def fake_evaluate(self: InterviewController, **kwargs: object):
        state.gateway_result = GatewayResult(approved=False, gateway_type="REPROVADO")
        from content_engine.interview.schemas import DeepeningDecision

        decision = DeepeningDecision(
            should_ask=False,
            reason="limite",
            closure_reason="LIMITE_DE_PERGUNTAS_ATINGIDO",
        )
        state.deepening_decision = decision
        return decision

    def fake_diagnose(self: InterviewController, *, force: bool = False) -> str:
        state.gap_diagnosis = "novo diagnostico"
        return state.gap_diagnosis

    monkeypatch.setattr(InterviewController, "ingest_answer", fake_ingest)
    monkeypatch.setattr(InterviewController, "evaluate_material", fake_evaluate)
    monkeypatch.setattr(InterviewController, "diagnose_gaps", fake_diagnose)

    decision = controller.submit_extension_batch(
        [{"question": q.question, "answer": f"A{i}"} for i, q in enumerate(pending, start=1)]
    )
    assert decision.should_ask is False
    assert ingested == ["A1", "A2", "A3", "A4", "A5"]
    assert state.pending_batch == []
    assert state.extension_batches_completed == 1
    assert state.progress_state == "CONCLUIDA"
    assert state.gap_diagnosis == "novo diagnostico"


def test_submit_extension_batch_clears_diagnosis_when_approved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pending = [SelectedQuestion(question=f"Q{i}") for i in range(1, 6)]
    state = _terminal_state(
        max_questions=17,
        question_count=17,
        pending_batch=list(pending),
        gap_diagnosis="ainda falta",
    )
    controller = InterviewController(state)

    monkeypatch.setattr(InterviewController, "ingest_answer", lambda *a, **k: None)

    def fake_evaluate(self: InterviewController, **kwargs: object):
        state.gateway_result = GatewayResult(approved=True, gateway_type="EQUILIBRADO")
        from content_engine.interview.schemas import DeepeningDecision

        return DeepeningDecision(should_ask=False, reason="ok", closure_reason="GATEWAY")

    monkeypatch.setattr(InterviewController, "evaluate_material", fake_evaluate)

    controller.submit_extension_batch(
        [{"question": q.question, "answer": "ok"} for q in pending]
    )
    assert state.extension_batches_completed == 1
    assert state.progress_state == "MATERIAL_SUFICIENTE"
    assert state.gap_diagnosis == ""


def test_limit_unapproved_ui_is_terminal_contract() -> None:
    """UI payload for limit → terminal_gaps: history present, no active question/batch."""
    state = _terminal_state(
        answers=[
            UserAnswer(id="a1", question="antiga?", original="sim", normalized="sim"),
        ],
        current_question=None,
        pending_batch=[],
        extension_batches_completed=0,
    )
    ui = build_interview_ui(state)
    assert ui["progress_state"] == "CONCLUIDA"
    assert ui["gateway"]["approved"] is False
    assert ui["closure_reason"] == "LIMITE_DE_PERGUNTAS_ATINGIDO"
    assert ui["current_question"] is None
    assert ui["pending_batch"] == []
    assert ui["history"][0]["question"] == "antiga?"
    # FE: Finalizar/Reiniciar only when batches_completed >= 1
    assert ui["extension_batches_completed"] == 0


def test_ui_exposes_batches_completed_for_second_round_ctas() -> None:
    ui = build_interview_ui(_terminal_state(extension_batches_completed=1))
    assert ui["extension_batches_completed"] == 1
    assert ui["gateway"]["approved"] is False
    assert ui["progress_state"] == "CONCLUIDA"


def test_submit_extension_batch_reevaluates_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pending = [SelectedQuestion(question=f"Q{i}") for i in range(1, 6)]
    state = _terminal_state(
        max_questions=17,
        question_count=17,
        pending_batch=list(pending),
        progress_state="APROFUNDANDO",
    )
    controller = InterviewController(state)
    eval_calls = {"n": 0}

    monkeypatch.setattr(InterviewController, "ingest_answer", lambda *a, **k: None)

    def fake_evaluate(self: InterviewController, **kwargs: object):
        eval_calls["n"] += 1
        state.gateway_result = GatewayResult(approved=False, gateway_type="REPROVADO")
        from content_engine.interview.schemas import DeepeningDecision

        return DeepeningDecision(
            should_ask=False,
            reason="limite",
            closure_reason="LIMITE_DE_PERGUNTAS_ATINGIDO",
        )

    def fake_diagnose(self: InterviewController, *, force: bool = False) -> str:
        state.gap_diagnosis = "reavaliado"
        return state.gap_diagnosis

    monkeypatch.setattr(InterviewController, "evaluate_material", fake_evaluate)
    monkeypatch.setattr(InterviewController, "diagnose_gaps", fake_diagnose)

    controller.submit_extension_batch(
        [{"question": q.question, "answer": f"A{i}"} for i, q in enumerate(pending, start=1)]
    )
    assert eval_calls["n"] == 1
    assert state.extension_batches_completed == 1
    assert state.progress_state == "CONCLUIDA"
    assert state.gap_diagnosis == "reavaliado"
