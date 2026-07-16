"""Geracao de titulo curto para cada rodada da entrevista via LLM."""
from __future__ import annotations

import re
from typing import Any

from ..prompt_registry.resolver import resolve_prompt
from ..schemas import AgentResult
from .schemas import InterviewState


DEFAULT_FALLBACK = "entrevista"


def _clean_title(raw: str) -> str:
    texto = raw.strip()
    texto = texto.strip("'\"").strip()
    texto = texto.strip("'\"").strip()
    texto = re.sub(r"^rodada\s*[:\d]*\s*", "", texto, flags=re.IGNORECASE).strip()
    texto = texto.strip("'\"").strip()
    return texto[:60] if texto else DEFAULT_FALLBACK


def _invoke_runner(runner: Any, tool: str, prompt: str, **kwargs: Any) -> AgentResult:
    if callable(runner) and not hasattr(runner, "run"):
        result = runner(prompt)
    else:
        result = runner.run(tool, prompt, **kwargs)
    if isinstance(result, AgentResult):
        return result
    if isinstance(result, str):
        return AgentResult(tool=tool, command=[tool], returncode=0, stdout=result, stderr="")  # type: ignore[arg-type]
    raise RuntimeError("runner de titulo de rodada retornou um contrato invalido")


def build_round_title_prompt(
    state: InterviewState,
    *,
    provider: str | None = None,
    model: str | None = None,
) -> str:
    question = state.current_question
    question_text = question.question if question else ""
    direction = question.direction if question else ""
    round_number = state.question_count
    signals_summary = ", ".join(
        f"{s.type}: {s.summary}" for s in state.signals[-5:]
    ) if state.signals else "nenhum"
    return resolve_prompt(
        "interview_round_title",
        {
            "theme": state.context.tema,
            "format": state.context.formato,
            "round_number": str(round_number),
            "question": question_text,
            "direction": direction,
            "signals_summary": signals_summary,
        }, provider=provider, model=model,
    ).resolved_content


def generate_round_title(
    runner: Any,
    state: InterviewState,
    *,
    tool: str = "opencode",
    model: str | None = None,
    reasoning_effort: str | None = None,
    sandbox: str | None = None,
) -> str:
    if not runner:
        return DEFAULT_FALLBACK
    try:
        prompt = build_round_title_prompt(
            state, provider=tool, model=model,
        )
        run_kwargs: dict[str, Any] = {"model": model}
        if reasoning_effort:
            run_kwargs["reasoning_effort"] = reasoning_effort
        if sandbox:
            run_kwargs["sandbox"] = sandbox
        result = _invoke_runner(runner, tool, prompt, **run_kwargs)
        if not result.ok:
            return DEFAULT_FALLBACK
        title = _clean_title(result.stdout)
        if title and title != DEFAULT_FALLBACK:
            state.round_title = title
            state.round_titles[state.question_count] = title
        return title
    except Exception:  # noqa: BLE001
        return DEFAULT_FALLBACK


__all__ = [
    "DEFAULT_FALLBACK",
    "generate_round_title",
    "build_round_title_prompt",
]
