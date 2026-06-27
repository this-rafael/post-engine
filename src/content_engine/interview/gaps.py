"""Lacunas derivadas de sinais observados, nunca do catalogo isoladamente."""
from __future__ import annotations

from typing import Any, Iterable

from .schemas import (
    AuthorialSignal,
    DeepeningDecision,
    DimensionScore,
    Gap,
    GatewayResult,
    InterviewState,
)


def _signal(value: object) -> AuthorialSignal:
    return value if isinstance(value, AuthorialSignal) else AuthorialSignal.from_dict(value)


def _dimension(value: object) -> DimensionScore:
    return value if isinstance(value, DimensionScore) else DimensionScore.from_dict(value)


def identify_gaps(
    signals: Iterable[AuthorialSignal | dict[str, Any]] | InterviewState,
    dimensions: dict[str, DimensionScore | dict[str, Any]] | None = None,
    *,
    evidence_count: int | None = None,
    formato: str = "post",
) -> list[Gap]:
    if isinstance(signals, InterviewState):
        state = signals
        signal_list = list(state.signals)
        dimension_map = dict(state.dimensions)
        evidence_total = len(state.evidence_ledger)
    else:
        signal_list = [_signal(item) for item in signals]
        dimension_map = {
            key: _dimension(value) for key, value in (dimensions or {}).items()
        }
        evidence_total = evidence_count if evidence_count is not None else 0

    types = {item.type for item in signal_list}
    gaps: list[Gap] = []

    def add(gap: Gap) -> None:
        if not any(existing.type == gap.type for existing in gaps):
            gaps.append(gap)

    if not signal_list or evidence_total == 0:
        add(
            Gap(
                type="MATERIAL_HUMANO_AUSENTE",
                dimension="experiencia_vivida",
                relevance="high",
                expected_gain="high",
                critical=True,
                reason="Ainda nao existe evidencia literal suficiente da resposta do autor.",
            )
        )
        return gaps

    if "posicao_propria" in types and "concretude" not in types:
        add(
            Gap(
                type="LACUNA_DE_CONCRETUDE",
                dimension="concretude",
                relevance="high",
                expected_gain="high",
                critical=True,
                reason="Existe opiniao, mas nenhum caso ou detalhe concreto a sustenta.",
                suggested_question="Qual situacao concreta fez voce chegar a essa conclusao?",
            )
        )
    if "experiencia_vivida" in types and "aprendizado" not in types:
        add(
            Gap(
                type="LACUNA_DE_REFLEXAO",
                dimension="aprendizado",
                relevance="high",
                expected_gain="high",
                critical=False,
                reason="Existe experiencia, mas ainda nao apareceu o que ela mudou ou ensinou.",
                suggested_question="O que essa experiencia mudou na forma como voce pensa ou age?",
            )
        )
    if "posicao_propria" in types and "tensao" not in types:
        add(
            Gap(
                type="LACUNA_DE_TENSAO",
                dimension="tensao",
                relevance="medium",
                expected_gain="high",
                critical=False,
                reason="Existe uma tese, mas ainda nao apareceu seu limite ou contradicao.",
                suggested_question="Em que situacao essa posicao deixa de funcionar?",
            )
        )
    if "experiencia_vivida" in types and "mecanismo" not in types and formato in {"article", "long_slide"}:
        add(
            Gap(
                type="LACUNA_DE_CLAREZA",
                dimension="aplicabilidade",
                relevance="medium",
                expected_gain="high",
                critical=True,
                reason="A historia foi mencionada, mas seu mecanismo ainda esta pouco claro para o formato.",
                suggested_question="Como isso funcionou na pratica, passo a passo?",
            )
        )

    for dimension_id, dimension in dimension_map.items():
        if dimension.state in {"FRACA", "PARCIAL", "CONFLITANTE"} and dimension.evidence_ids:
            add(
                Gap(
                    type=f"DIMENSAO_FRACA_{dimension_id.upper()}",
                    dimension=dimension_id,
                    relevance="medium" if dimension.state != "CONFLITANTE" else "high",
                    expected_gain="high" if dimension.state == "CONFLITANTE" else "medium",
                    critical=dimension.critical or dimension.state == "CONFLITANTE",
                    reason=dimension.rationale,
                )
            )
    return gaps


def decide_deepening(
    gaps: Iterable[Gap | dict[str, Any]],
    gateway: GatewayResult | dict[str, Any] | None = None,
    *,
    question_count: int = 0,
    max_questions: int = 12,
    user_requested_end: bool = False,
) -> DeepeningDecision:
    gap_list = [item if isinstance(item, Gap) else Gap.from_dict(item) for item in gaps]
    gateway_result = (
        gateway
        if isinstance(gateway, GatewayResult)
        else GatewayResult.from_dict(gateway)
        if isinstance(gateway, dict)
        else None
    )
    if user_requested_end:
        return DeepeningDecision(
            should_ask=False,
            reason="O usuario solicitou encerramento.",
            marginal_gain="low",
            closure_reason="USUARIO_SOLICITOU_ENCERRAMENTO",
        )
    if question_count >= max_questions:
        return DeepeningDecision(
            should_ask=False,
            reason="O limite de perguntas foi atingido.",
            marginal_gain="low",
            closure_reason="LIMITE_DE_PERGUNTAS_ATINGIDO",
        )
    if gateway_result is not None and gateway_result.approved and not any(gap.critical for gap in gap_list):
        return DeepeningDecision(
            should_ask=False,
            reason="O gateway ja aprovou o material; lacunas opcionais nao prolongam a entrevista.",
            marginal_gain="low",
            closure_reason="GATEWAY_APROVADO_SEM_LACUNA_CRITICA",
        )

    candidates = [
        gap
        for gap in gap_list
        if gap.relevance == "high" or gap.expected_gain == "high" or gap.critical
    ]
    if not candidates:
        if (
            gateway_result is not None
            and not gateway_result.approved
            and question_count < max_questions
        ):
            return DeepeningDecision(
                should_ask=True,
                reason="O gateway ainda nao aprovou; continue a exploracao aberta.",
                marginal_gain="medium",
            )
        return DeepeningDecision(
            should_ask=False,
            reason="Nao existe lacuna com ganho esperado alto.",
            marginal_gain="low",
            closure_reason="GANHO_MARGINAL_BAIXO",
        )
    selected = sorted(
        candidates,
        key=lambda item: (item.critical, item.expected_gain == "high", item.relevance == "high"),
        reverse=True,
    )[0]
    return DeepeningDecision(
        should_ask=True,
        reason=f"A lacuna {selected.type} ainda reduz a qualidade do material.",
        selected_gap=selected,
        why_now=selected.reason,
        marginal_gain="high",
    )


def explain_decision(decision: DeepeningDecision) -> str:
    if decision.should_ask:
        return f"Pergunta de aprofundamento: {decision.why_now or decision.reason}"
    return f"Entrevista encerrada: {decision.closure_reason or decision.reason}"


__all__ = ["identify_gaps", "decide_deepening", "explain_decision"]
