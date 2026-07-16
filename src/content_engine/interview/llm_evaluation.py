"""Avaliacao semantica LLM usada como componente necessario do gateway."""
from __future__ import annotations

import json
from typing import Any, Iterable

from ..llm_json_parser import extract_json_object_from_llm_output
from ..prompt_registry.resolver import resolve_prompt
from ..schemas import AgentResult
from .schemas import AuthorialSignal, Evidence, InterviewState, LlmAssessment, ThemeContext, UserAnswer


def _text_items(items: Iterable[object]) -> list[str]:
    return [str(item).strip() for item in items if str(item).strip()]


def build_authorship_prompt(
    context: ThemeContext | InterviewState | dict[str, Any],
    answers: Iterable[UserAnswer | dict[str, Any]] | None = None,
    evidence: Iterable[Evidence | dict[str, Any]] | None = None,
    signals: Iterable[AuthorialSignal | dict[str, Any]] | None = None,
    provider: str | None = None,
    model: str | None = None,
) -> str:
    if isinstance(context, InterviewState):
        state = context
        theme = state.context
        answers = state.answers
        evidence = state.evidence_ledger
        signals = state.signals
    elif isinstance(context, ThemeContext):
        theme = context
    else:
        theme = ThemeContext.from_dict(context)

    answer_payload = []
    for raw in answers or ():
        answer = raw if isinstance(raw, UserAnswer) else UserAnswer.from_dict(raw)
        answer_payload.append(
            {
                "id": answer.id,
                "question": answer.question,
                "original": answer.original,
                "normalized": answer.normalized,
            }
        )
    evidence_payload = []
    for raw in evidence or ():
        item = raw if isinstance(raw, Evidence) else Evidence.from_dict(raw)
        evidence_payload.append(item.to_dict())
    signal_payload = []
    for raw in signals or ():
        item = raw if isinstance(raw, AuthorialSignal) else AuthorialSignal.from_dict(raw)
        signal_payload.append(item.to_dict())

    payload = {
        "context": theme.to_dict(),
        "answers": answer_payload,
        "evidence": evidence_payload,
        "signals": signal_payload,
    }
    return resolve_prompt(
        "interview_evaluate",
        {"material_json": json.dumps(payload, ensure_ascii=False)},
        provider=provider,
        model=model,
    ).resolved_content


def _invoke(runner: Any, tool: str, prompt: str, **kwargs: Any) -> AgentResult:
    if callable(runner) and not hasattr(runner, "run"):
        result = runner(prompt)
    else:
        result = runner.run(tool, prompt, **kwargs)
    if isinstance(result, AgentResult):
        return result
    if isinstance(result, str):
        return AgentResult(tool=tool, command=[tool], returncode=0, stdout=result, stderr="")  # type: ignore[arg-type]
    raise TypeError("runner de avaliacao retornou um contrato invalido")


def evaluate_authorship_llm(
    runner: Any,
    context: ThemeContext | InterviewState | dict[str, Any],
    *,
    answers: Iterable[UserAnswer | dict[str, Any]] | None = None,
    evidence: Iterable[Evidence | dict[str, Any]] | None = None,
    signals: Iterable[AuthorialSignal | dict[str, Any]] | None = None,
    tool: str = "codex",
    model: str | None = None,
    reasoning_effort: str | None = None,
    sandbox: str | None = None,
) -> LlmAssessment:
    prompt = build_authorship_prompt(
        context, answers, evidence, signals, provider=tool, model=model
    )
    run_kwargs: dict[str, Any] = {"model": model, "json_output": True}
    if reasoning_effort:
        run_kwargs["reasoning_effort"] = reasoning_effort
    if sandbox:
        run_kwargs["sandbox"] = sandbox
    try:
        result = _invoke(runner, tool, prompt, **run_kwargs)
    except Exception as exc:  # pragma: no cover - defensive boundary for providers
        return LlmAssessment(approved=False, parse_error=str(exc), source="agent_error")
    if not result.ok:
        return LlmAssessment(
            approved=False,
            parse_error=result.error or result.stderr or "falha na avaliacao LLM",
            source="agent_error",
        )
    parsed = extract_json_object_from_llm_output(
        result.stdout,
        prefer_evaluation_shape=False,
        prefer_keys=("aprovou", "approved", "justificativa", "justification"),
    )
    if not parsed.ok or parsed.data is None:
        return LlmAssessment(
            approved=False,
            parse_error=parsed.error or "JSON de avaliacao invalido",
            source="parse_error",
        )
    data = parsed.data
    approved_raw = data.get("approved", data.get("aprovou", data.get("llm_aprovou", False)))
    confidence_raw = data.get("confidence", data.get("confianca", 0))
    try:
        confidence = float(confidence_raw or 0)
        if confidence > 1:
            confidence /= 100
    except (TypeError, ValueError):
        confidence = 0.0
    return LlmAssessment(
        approved=bool(approved_raw),
        confidence=confidence,
        strengths=tuple(_text_items(data.get("strengths", data.get("forcas", [])) or [])),
        weaknesses=tuple(_text_items(data.get("weaknesses", data.get("fraquezas", [])) or [])),
        risks=tuple(_text_items(data.get("risks", data.get("riscos", [])) or [])),
        justification=str(data.get("justification", data.get("justificativa", "")) or ""),
        epistemic_integrity=str(
            data.get("epistemic_integrity", data.get("integridade_epistemica", "unknown"))
            or "unknown"
        ),
        source="llm",
    )


__all__ = ["build_authorship_prompt", "evaluate_authorship_llm"]
