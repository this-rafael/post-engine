from __future__ import annotations

from content_engine.interview.gaps import decide_deepening, identify_gaps
from content_engine.interview.schemas import Gap, GatewayResult


def test_identify_gaps_only_from_observed_signals() -> None:
    gaps = identify_gaps(
        [
            {
                "id": "s1",
                "type": "posicao_propria",
                "summary": "Tenho uma opiniao.",
                "evidence_ids": ["ev1"],
                "status": "CONFIRMADO",
            }
        ],
        evidence_count=1,
    )
    assert any(gap.type == "LACUNA_DE_CONCRETUDE" for gap in gaps)


def test_FR_014_optional_gaps_do_not_extend_approved_interview() -> None:
    decision = decide_deepening(
        [
            Gap(
                type="LACUNA_DE_TENSAO",
                dimension="tensao",
                relevance="medium",
                expected_gain="medium",
                critical=False,
            )
        ],
        GatewayResult(approved=True, gateway_type="EQUILIBRADO"),
        question_count=2,
    )
    assert decision.should_ask is False


def test_critical_gap_can_request_deepening() -> None:
    decision = decide_deepening(
        [
            Gap(
                type="LACUNA_DE_CLAREZA",
                dimension="aplicabilidade",
                relevance="high",
                expected_gain="high",
                critical=True,
            )
        ],
        GatewayResult(approved=True, gateway_type="EQUILIBRADO"),
        question_count=2,
    )
    assert decision.should_ask is True


def test_decision_respects_question_limit() -> None:
    decision = decide_deepening(
        [Gap(type="LACUNA", relevance="high", expected_gain="high", critical=True)],
        question_count=3,
        max_questions=3,
    )
    assert decision.should_ask is False
    assert decision.closure_reason == "LIMITE_DE_PERGUNTAS_ATINGIDO"


def test_unapproved_gateway_keeps_exploring_without_high_gaps() -> None:
    decision = decide_deepening(
        [],
        GatewayResult(approved=False, gateway_type="REPROVADO"),
        question_count=1,
        max_questions=12,
    )
    assert decision.should_ask is True
    assert decision.marginal_gain == "medium"
