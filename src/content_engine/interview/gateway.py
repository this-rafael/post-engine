"""Gateway hibrido: LLM necessaria e heuristica deterministica necessaria."""
from __future__ import annotations

from typing import Iterable

from .heuristic import GATEWAY_PROFILES
from .schemas import (
    DeterministicAssessment,
    DimensionScore,
    Gap,
    GatewayResult,
    LlmAssessment,
)


def _coerce_heuristic(value: DeterministicAssessment | dict[str, object]) -> DeterministicAssessment:
    return value if isinstance(value, DeterministicAssessment) else DeterministicAssessment.from_dict(value)


def _coerce_llm(value: LlmAssessment | dict[str, object]) -> LlmAssessment:
    return value if isinstance(value, LlmAssessment) else LlmAssessment.from_dict(value)


def _coerce_gaps(gaps: Iterable[Gap | dict[str, object]] | None) -> tuple[Gap, ...]:
    return tuple(item if isinstance(item, Gap) else Gap.from_dict(item) for item in (gaps or ()))


def _profile(formato: str) -> dict[str, int]:
    return GATEWAY_PROFILES.get(str(formato), GATEWAY_PROFILES["post"])


def _essential(dimensions: dict[str, DimensionScore]) -> list[DimensionScore]:
    return [item for item in dimensions.values() if item.essential]


def _critical(dimensions: dict[str, DimensionScore]) -> list[DimensionScore]:
    return [item for item in dimensions.values() if item.critical]


def _balanced_gateway(assessment: DeterministicAssessment, formato: str) -> bool:
    profile = _profile(formato)
    essential = _essential(assessment.dimensions)
    return (
        bool(essential)
        and assessment.evidence_count >= profile["minimum_evidence"]
        and assessment.global_score >= profile["minimum_global"]
        and all(item.score >= profile["minimum_essential"] for item in essential)
    )


def _strong_imbalanced_gateway(assessment: DeterministicAssessment, formato: str) -> bool:
    profile = _profile(formato)
    exceptional = [
        item
        for item in assessment.dimensions.values()
        if item.state == "EXCEPCIONAL" or item.score >= 85
    ]
    critical = _critical(assessment.dimensions)
    critical_ok = all(item.score >= profile["absolute_floor"] for item in critical)
    return (
        len(exceptional) >= profile["minimum_exceptional"]
        and assessment.global_score >= profile["minimum_imbalanced_global"]
        and assessment.evidence_count >= profile["minimum_evidence"]
        and critical_ok
    )


def evaluate_gateway(
    heuristic: DeterministicAssessment | dict[str, object],
    llm: LlmAssessment | dict[str, object],
    *,
    gaps: Iterable[Gap | dict[str, object]] | None = None,
    formato: str = "post",
) -> GatewayResult:
    """Combina as duas avaliacoes sem permitir aprovacao unilateral."""
    heuristic_assessment = _coerce_heuristic(heuristic)
    llm_assessment = _coerce_llm(llm)
    balanced = _balanced_gateway(heuristic_assessment, formato)
    strong_imbalanced = _strong_imbalanced_gateway(heuristic_assessment, formato)
    heuristic_approved = bool((balanced or strong_imbalanced) and not heuristic_assessment.vetos)
    approved = bool(llm_assessment.approved and heuristic_approved)
    gateway_type = (
        "EQUILIBRADO"
        if approved and balanced
        else "DESEQUILIBRADO_FORTE"
        if approved and strong_imbalanced
        else "REPROVADO"
    )
    exceptional = tuple(
        dimension_id
        for dimension_id, item in heuristic_assessment.dimensions.items()
        if item.state == "EXCEPCIONAL" or item.score >= 85
    )
    weak = tuple(
        dimension_id
        for dimension_id, item in heuristic_assessment.dimensions.items()
        if item.state in {"NAO_OBSERVADA", "FRACA", "PARCIAL", "CONFLITANTE"}
    )
    vetoes = tuple(heuristic_assessment.vetos)
    if not llm_assessment.approved and "LLM_NAO_APROVOU" not in vetoes:
        vetoes = vetoes + ("LLM_NAO_APROVOU",)
    if not heuristic_approved and "HEURISTICA_NAO_APROVOU" not in vetoes:
        vetoes = vetoes + ("HEURISTICA_NAO_APROVOU",)

    if approved:
        path = "equilibrado" if balanced else "desequilibrado forte"
        justification = (
            f"Aprovado pelo caminho {path}: LLM aprovou e a heuristica deterministica "
            f"atingiu o limiar. {llm_assessment.justification}"
        ).strip()
    else:
        justification = (
            "Reprovado: LLM e heuristica precisam aprovar simultaneamente. "
            f"{llm_assessment.justification}"
        ).strip()

    return GatewayResult(
        approved=approved,
        gateway_type=gateway_type,  # type: ignore[arg-type]
        llm_approved=llm_assessment.approved,
        heuristic_approved=heuristic_approved,
        balanced=balanced,
        strong_imbalanced=strong_imbalanced,
        global_score=heuristic_assessment.global_score,
        exceptional_dimensions=exceptional,
        weak_dimensions=weak,
        vetoes=vetoes,
        relevant_gaps=_coerce_gaps(gaps),
        justification=justification,
        llm_confidence=llm_assessment.confidence,
    )


def gateway_equilibrado(assessment: DeterministicAssessment, formato: str = "post") -> bool:
    return _balanced_gateway(_coerce_heuristic(assessment), formato)


def gateway_desequilibrado_forte(assessment: DeterministicAssessment, formato: str = "post") -> bool:
    return _strong_imbalanced_gateway(_coerce_heuristic(assessment), formato)


__all__ = [
    "evaluate_gateway",
    "gateway_equilibrado",
    "gateway_desequilibrado_forte",
]
