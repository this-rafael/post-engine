from __future__ import annotations

from content_engine.interview.gateway import evaluate_gateway
from content_engine.interview.schemas import (
    DeterministicAssessment,
    DimensionScore,
    LlmAssessment,
)


def _assessment(*, strong: bool = False, vetos: tuple[str, ...] = ()) -> DeterministicAssessment:
    scores = {
        "experiencia_vivida": 92 if strong else 70,
        "posicao_propria": 90 if strong else 70,
        "concretude": 92 if strong else 70,
        "aprendizado": 30 if strong else 60,
        "voz": 28 if strong else 60,
        "tensao": 20 if strong else 60,
        "aplicabilidade": 35 if strong else 60,
        "autoridade": 20 if strong else 65,
        "integridade_epistemica": 65 if strong else 70,
    }
    secondary = {"aprendizado", "voz", "tensao", "aplicabilidade"}
    dimensions = {
        key: DimensionScore(
            dimension_id=key,
            score=value,
            state="EXCEPCIONAL" if value >= 85 else "SUFICIENTE" if value >= 45 else "FRACA",
            evidence_ids=(f"ev-{key}",),
            rules_triggered=("TEST",),
            essential=key not in secondary,
            critical=key in {"experiencia_vivida", "integridade_epistemica"},
        )
        for key, value in scores.items()
    }
    return DeterministicAssessment(
        dimensions=dimensions,
        global_score=65 if strong else 67,
        vetos=vetos,
        evidence_count=3,
        answer_count=2,
        rules_triggered=("TEST",),
    )


def test_FR_008_llm_alone_cannot_approve_gateway() -> None:
    result = evaluate_gateway(
        _assessment(vetos=("MATERIAL_INSUFICIENTE_PARA_O_FORMATO",)),
        LlmAssessment(approved=True, confidence=0.95),
    )
    assert result.approved is False
    assert result.llm_approved is True


def test_FR_009_heuristic_alone_cannot_approve_gateway() -> None:
    result = evaluate_gateway(_assessment(), LlmAssessment(approved=False))
    assert result.approved is False
    assert result.heuristic_approved is True


def test_FR_010_balanced_gateway_requires_essential_dimensions() -> None:
    assessment = _assessment()
    assessment = DeterministicAssessment(
        dimensions={
            **assessment.dimensions,
            "posicao_propria": DimensionScore(
                dimension_id="posicao_propria",
                score=20,
                state="FRACA",
                evidence_ids=("ev-posicao",),
                rules_triggered=("LOW",),
                essential=True,
            ),
        },
        global_score=80,
        evidence_count=3,
        answer_count=2,
    )
    result = evaluate_gateway(assessment, LlmAssessment(approved=True))
    assert result.balanced is False
    assert result.approved is False


def test_FR_011_strong_imbalanced_gateway_rules() -> None:
    result = evaluate_gateway(_assessment(strong=True), LlmAssessment(approved=True))
    assert result.strong_imbalanced is True
    assert result.gateway_type == "DESEQUILIBRADO_FORTE"
    assert result.approved is True


def test_FR_012_absolute_vetoes_block_approval() -> None:
    result = evaluate_gateway(
        _assessment(strong=True, vetos=("CONTRADICAO_GRAVE_NAO_RESOLVIDA",)),
        LlmAssessment(approved=True),
    )
    assert result.approved is False
    assert "CONTRADICAO_GRAVE_NAO_RESOLVIDA" in result.vetoes


def test_FR_013_exceptional_story_compensates_weak_secondary() -> None:
    result = evaluate_gateway(_assessment(strong=True), LlmAssessment(approved=True))
    assert result.approved is True
    assert {"experiencia_vivida", "concretude"} <= set(result.exceptional_dimensions)
    assert "tensao" in result.weak_dimensions
