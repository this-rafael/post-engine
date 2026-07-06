from __future__ import annotations

from content_engine.interview.controller import InterviewController
from content_engine.interview.schemas import LlmAssessment, SelectedQuestion, criar_estado_inicial


def test_FR_015_system_explains_question_and_closure() -> None:
    state = criar_estado_inicial("arquitetura orientada a eventos")
    state.current_question = SelectedQuestion(
        question="Que situacao concreta mudou sua forma de pensar sobre eventos?",
        why_now="Ainda falta um caso concreto.",
        candidate_id="q-1",
    )
    controller = InterviewController(state)
    decision = controller.process_answer(
        "Eu implementei esse fluxo em 2024 e aprendi que o acoplamento aparecia no retry.",
        llm_assessment=LlmAssessment(
            approved=False,
            confidence=0.8,
            justification="Ainda falta uma posicao mais explicita.",
        ),
    )
    assert state.answers[0].original.startswith("Eu implementei")
    assert state.deepening_decision is decision
    assert controller.explain_decision()
    assert state.gateway_result is not None
