"""Diagnostico LLM das lacunas que impedem a aprovacao do gateway."""
from __future__ import annotations

import json
from typing import Any

from ..prompt_registry.resolver import resolve_prompt
from ..schemas import AgentResult
from .schemas import InterviewState

DEFAULT_FALLBACK = (
    "Ainda falta material autoral concreto para atingir o minimo do gateway."
)


def _invoke_runner(runner: Any, tool: str, prompt: str, **kwargs: Any) -> AgentResult:
    if callable(runner) and not hasattr(runner, "run"):
        result = runner(prompt)
    else:
        result = runner.run(tool, prompt, **kwargs)
    if isinstance(result, AgentResult):
        return result
    if isinstance(result, str):
        return AgentResult(tool=tool, command=[tool], returncode=0, stdout=result, stderr="")  # type: ignore[arg-type]
    raise RuntimeError("runner de diagnostico de lacunas retornou um contrato invalido")


def build_fallback_diagnosis(state: InterviewState) -> str:
    parts: list[str] = []
    gateway = state.gateway_result
    if gateway and gateway.justification:
        parts.append(gateway.justification.rstrip("."))
    if gateway and gateway.weak_dimensions:
        parts.append(
            "Dimensoes ainda fracas: " + ", ".join(gateway.weak_dimensions) + "."
        )
    if gateway and gateway.vetoes:
        parts.append("Vetos ativos: " + ", ".join(gateway.vetoes) + ".")
    if state.llm_assessment and state.llm_assessment.weaknesses:
        parts.append(
            "Fraquezas apontadas: " + "; ".join(state.llm_assessment.weaknesses[:3]) + "."
        )
    critical = [gap for gap in state.gaps if gap.critical or gap.reason]
    for gap in critical[:4]:
        label = gap.dimension or gap.type or "lacuna"
        reason = gap.reason or "precisa de mais evidencia autoral"
        parts.append(f"Em {label}, {reason.rstrip('.')}.")
    text = " ".join(part.strip() for part in parts if part.strip())
    return text or DEFAULT_FALLBACK


def build_gap_diagnosis_prompt(
    state: InterviewState,
    *,
    provider: str | None = None,
    model: str | None = None,
) -> str:
    gateway = state.gateway_result
    llm = state.llm_assessment
    gaps_payload = [gap.to_dict() for gap in state.gaps]
    return resolve_prompt(
        "interview_gap_diagnosis",
        {
            "theme": state.context.tema,
            "format": state.context.formato,
            "question_count": str(state.question_count),
            "max_questions": str(state.max_questions),
            "global_score": str(gateway.global_score if gateway else 0),
            "gateway_justification": gateway.justification if gateway else "",
            "weak_dimensions": ", ".join(gateway.weak_dimensions) if gateway else "",
            "vetoes": ", ".join(gateway.vetoes) if gateway else "",
            "llm_weaknesses": ", ".join(llm.weaknesses) if llm else "",
            "gaps_json": json.dumps(gaps_payload, ensure_ascii=False),
        },
        provider=provider,
        model=model,
    ).resolved_content


def generate_gap_diagnosis(
    runner: Any,
    state: InterviewState,
    *,
    tool: str = "opencode",
    model: str | None = None,
    reasoning_effort: str | None = None,
    sandbox: str | None = None,
    force: bool = False,
) -> str:
    if state.gap_diagnosis and not force:
        return state.gap_diagnosis
    fallback = build_fallback_diagnosis(state)
    if not runner:
        state.gap_diagnosis = fallback
        return fallback
    try:
        prompt = build_gap_diagnosis_prompt(state, provider=tool, model=model)
        run_kwargs: dict[str, Any] = {"model": model}
        if reasoning_effort:
            run_kwargs["reasoning_effort"] = reasoning_effort
        if sandbox:
            run_kwargs["sandbox"] = sandbox
        result = _invoke_runner(runner, tool, prompt, **run_kwargs)
        if not result.ok:
            state.gap_diagnosis = fallback
            return fallback
        text = (result.stdout or "").strip()
        if not text:
            state.gap_diagnosis = fallback
            return fallback
        state.gap_diagnosis = text
        return text
    except Exception:  # noqa: BLE001
        state.gap_diagnosis = fallback
        return fallback


__all__ = [
    "DEFAULT_FALLBACK",
    "build_fallback_diagnosis",
    "build_gap_diagnosis_prompt",
    "generate_gap_diagnosis",
]
