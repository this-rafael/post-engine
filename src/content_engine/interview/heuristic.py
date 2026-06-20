"""Pontuacao deterministica e explicavel do material autoral."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from .schemas import (
    AuthorialSignal,
    DeterministicAssessment,
    DimensionScore,
    Evidence,
    InterviewState,
    UserAnswer,
)


@dataclass(frozen=True)
class DimensionDefinition:
    id: str
    label: str
    essential: bool = True
    critical: bool = False
    signal_types: tuple[str, ...] = ()


DIMENSION_CATALOG: tuple[DimensionDefinition, ...] = (
    DimensionDefinition(
        "experiencia_vivida",
        "Experiencia vivida",
        signal_types=("experiencia_vivida",),
        critical=True,
    ),
    DimensionDefinition(
        "posicao_propria",
        "Posicao propria",
        signal_types=("posicao_propria", "criterio_proprio"),
    ),
    DimensionDefinition(
        "concretude",
        "Concretude",
        signal_types=("concretude", "mecanismo", "consequencia"),
    ),
    DimensionDefinition("aprendizado", "Aprendizado", essential=False, signal_types=("aprendizado",)),
    DimensionDefinition("voz", "Voz", essential=False, signal_types=("voz", "posicao_propria")),
    DimensionDefinition(
        "tensao",
        "Tensao",
        essential=False,
        signal_types=("tensao",),
        critical=True,
    ),
    DimensionDefinition(
        "aplicabilidade",
        "Aplicabilidade",
        essential=False,
        signal_types=("mecanismo", "criterio_proprio", "consequencia"),
    ),
    DimensionDefinition(
        "autoridade",
        "Autoridade",
        signal_types=("experiencia_vivida", "concretude", "mecanismo", "criterio_proprio"),
    ),
    DimensionDefinition(
        "integridade_epistemica",
        "Integridade epistemica",
        signal_types=("fato_declarado", "experiencia_vivida", "aprendizado"),
        critical=True,
    ),
)

DIMENSION_BY_ID = {item.id: item for item in DIMENSION_CATALOG}

GATEWAY_PROFILES: dict[str, dict[str, int]] = {
    "post": {
        "minimum_essential": 45,
        "minimum_global": 55,
        "minimum_imbalanced_global": 52,
        "minimum_exceptional": 2,
        "absolute_floor": 25,
        "minimum_evidence": 1,
    },
    "article": {
        "minimum_essential": 55,
        "minimum_global": 60,
        "minimum_imbalanced_global": 58,
        "minimum_exceptional": 2,
        "absolute_floor": 30,
        "minimum_evidence": 2,
    },
    "short_carousel": {
        "minimum_essential": 40,
        "minimum_global": 50,
        "minimum_imbalanced_global": 48,
        "minimum_exceptional": 2,
        "absolute_floor": 22,
        "minimum_evidence": 1,
    },
    "long_slide": {
        "minimum_essential": 50,
        "minimum_global": 58,
        "minimum_imbalanced_global": 55,
        "minimum_exceptional": 2,
        "absolute_floor": 28,
        "minimum_evidence": 2,
    },
}

ABSOLUTE_VETOES = (
    "NENHUMA_EVIDENCIA_DO_USUARIO",
    "EXPERIENCIA_NAO_CONFIRMADA",
    "CONTRADICAO_GRAVE_NAO_RESOLVIDA",
    "RESPOSTA_CONSTRUIDA_PELA_PERGUNTA",
    "MATERIAL_INSUFICIENTE_PARA_O_FORMATO",
    "FALHA_DE_INTEGRIDADE_EPISTEMICA",
)


def _profile(formato: str) -> dict[str, int]:
    return GATEWAY_PROFILES.get(str(formato), GATEWAY_PROFILES["post"])


def _as_signal(raw: object) -> AuthorialSignal:
    return raw if isinstance(raw, AuthorialSignal) else AuthorialSignal.from_dict(raw)


def _as_evidence(raw: object) -> Evidence:
    return raw if isinstance(raw, Evidence) else Evidence.from_dict(raw)


def _as_answer(raw: object) -> UserAnswer:
    return raw if isinstance(raw, UserAnswer) else UserAnswer.from_dict(raw)


def _state_inputs(
    signals: Iterable[AuthorialSignal] | InterviewState,
    evidence: Iterable[Evidence] | None,
    answers: Iterable[UserAnswer] | None,
) -> tuple[list[AuthorialSignal], list[Evidence], list[UserAnswer]]:
    if isinstance(signals, InterviewState):
        state = signals
        return list(state.signals), list(state.evidence_ledger), list(state.answers)
    return (
        [_as_signal(item) for item in signals],
        [_as_evidence(item) for item in (evidence or ())],
        [_as_answer(item) for item in (answers or ())],
    )


def _state_for_score(score: int, *, has_signal: bool, conflict: bool = False) -> str:
    if conflict:
        return "CONFLITANTE"
    if not has_signal:
        return "NAO_OBSERVADA"
    if score < 25:
        return "FRACA"
    if score < 45:
        return "PARCIAL"
    if score < 70:
        return "SUFICIENTE"
    if score < 85:
        return "FORTE"
    return "EXCEPCIONAL"


def _score_dimension(
    definition: DimensionDefinition,
    signals: list[AuthorialSignal],
    evidence_by_id: dict[str, Evidence],
) -> DimensionScore:
    relevant = [signal for signal in signals if signal.type in definition.signal_types]
    evidence_ids = tuple(
        dict.fromkeys(
            evidence_id
            for signal in relevant
            for evidence_id in signal.evidence_ids
            if evidence_id in evidence_by_id
        )
    )
    confirmed = sum(1 for signal in relevant if signal.status == "CONFIRMADO")
    uncertain = sum(1 for signal in relevant if signal.status == "INCERTO")
    conflicting = any(signal.status == "CONFLITANTE" for signal in relevant)
    details = sum(len(evidence_by_id[item].text) for item in evidence_ids)
    score = 0
    rules: list[str] = []
    if relevant:
        score += min(45, len(relevant) * 18)
        rules.append("SIGNAL_PRESENCE")
    if evidence_ids:
        score += min(25, len(evidence_ids) * 12)
        rules.append("EVIDENCE_TRACEABLE")
    if confirmed:
        score += min(20, confirmed * 10)
        rules.append("CONFIRMED_SIGNAL")
    if details >= 80:
        score += 10
        rules.append("DETAIL_DENSITY")
    elif details >= 35:
        score += 5
        rules.append("MINIMUM_DETAIL")
    if uncertain and definition.id == "integridade_epistemica":
        score += 10
        rules.append("HONEST_UNCERTAINTY")
    if conflicting:
        score = min(score, 35)
        rules.append("UNRESOLVED_CONTRADICTION")
    if definition.id == "experiencia_vivida" and not confirmed and relevant:
        rules.append("EXPERIENCE_NOT_CONFIRMED")
    if not relevant:
        rules.append("NO_OBSERVATION")
    score = min(100, score)
    rationale = (
        f"{len(relevant)} sinais, {len(evidence_ids)} evidencias rastreaveis; "
        f"regras: {', '.join(rules) or 'NONE'}."
    )
    return DimensionScore(
        dimension_id=definition.id,
        score=score,
        state=_state_for_score(score, has_signal=bool(relevant), conflict=conflicting),  # type: ignore[arg-type]
        evidence_ids=evidence_ids,
        rules_triggered=tuple(rules),
        rationale=rationale,
        essential=definition.essential,
        critical=definition.critical,
    )


def _question_echo(answer: UserAnswer) -> bool:
    question_tokens = set(re.findall(r"[a-zA-ZÀ-ÿ0-9]{4,}", answer.question.lower()))
    answer_tokens = set(re.findall(r"[a-zA-ZÀ-ÿ0-9]{4,}", answer.normalized.lower()))
    if not question_tokens or not answer_tokens:
        return False
    overlap = len(question_tokens & answer_tokens) / max(1, len(answer_tokens))
    return len(answer.normalized) < 120 and overlap >= 0.8


def detect_absolute_vetos(
    answers: Iterable[UserAnswer] | InterviewState,
    evidence: Iterable[Evidence] | None = None,
    signals: Iterable[AuthorialSignal] | None = None,
    *,
    formato: str = "post",
) -> list[str]:
    if isinstance(answers, InterviewState):
        state = answers
        answers_list = list(state.answers)
        evidence_list = list(state.evidence_ledger)
        signals_list = list(state.signals)
    else:
        answers_list = [_as_answer(item) for item in answers]
        evidence_list = [_as_evidence(item) for item in (evidence or ())]
        signals_list = [_as_signal(item) for item in (signals or ())]

    vetos: list[str] = []
    if not evidence_list:
        vetos.append("NENHUMA_EVIDENCIA_DO_USUARIO")

    experience = [item for item in signals_list if item.type == "experiencia_vivida"]
    if any(item.status in {"INCERTO", "CONFLITANTE"} for item in experience):
        vetos.append("EXPERIENCIA_NAO_CONFIRMADA")

    if any(item.status == "CONFLITANTE" for item in signals_list):
        vetos.append("CONTRADICAO_GRAVE_NAO_RESOLVIDA")

    if any(_question_echo(answer) for answer in answers_list):
        vetos.append("RESPOSTA_CONSTRUIDA_PELA_PERGUNTA")

    profile = _profile(formato)
    if not answers_list or sum(len(answer.normalized) for answer in answers_list) < 20:
        vetos.append("MATERIAL_INSUFICIENTE_PARA_O_FORMATO")
    elif len(evidence_list) < profile["minimum_evidence"]:
        vetos.append("MATERIAL_INSUFICIENTE_PARA_O_FORMATO")

    if any(
        item.type in {"afirmacao_sem_evidencia", "experiencia_inventada"}
        or (item.status == "INCERTO" and item.type == "experiencia_vivida")
        for item in signals_list
    ):
        vetos.append("FALHA_DE_INTEGRIDADE_EPISTEMICA")

    return list(dict.fromkeys(vetos))


def assess_dimensions(
    signals: Iterable[AuthorialSignal] | InterviewState,
    evidence: Iterable[Evidence] | None = None,
    answers: Iterable[UserAnswer] | None = None,
    *,
    formato: str = "post",
) -> DeterministicAssessment:
    signals_list, evidence_list, answers_list = _state_inputs(signals, evidence, answers)
    evidence_by_id = {item.id: item for item in evidence_list}
    dimensions = {
        definition.id: _score_dimension(definition, signals_list, evidence_by_id)
        for definition in DIMENSION_CATALOG
    }
    global_score = int(round(sum(item.score for item in dimensions.values()) / max(1, len(dimensions))))
    vetos = detect_absolute_vetos(
        answers_list,
        evidence_list,
        signals_list,
        formato=formato,
    )
    rules = tuple(
        dict.fromkeys(
            rule
            for dimension in dimensions.values()
            for rule in dimension.rules_triggered
        )
    )
    return DeterministicAssessment(
        dimensions=dimensions,
        global_score=global_score,
        vetos=tuple(vetos),
        evidence_count=len(evidence_list),
        answer_count=len(answers_list),
        rules_triggered=rules,
    )


__all__ = [
    "DimensionDefinition",
    "DIMENSION_CATALOG",
    "DIMENSION_BY_ID",
    "GATEWAY_PROFILES",
    "ABSOLUTE_VETOES",
    "assess_dimensions",
    "detect_absolute_vetos",
]
