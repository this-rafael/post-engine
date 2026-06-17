"""Exploracao aberta e selecao fail-closed de perguntas."""
from __future__ import annotations

import json
import hashlib
from typing import Any, Iterable

from ..llm_json_parser import extract_json_object_from_llm_output
from ..schemas import AgentResult
from .schemas import (
    AuthorialSignal,
    InterviewState,
    QuestionCandidate,
    SelectedQuestion,
    ThemeContext,
)
from .validation import validate_question


class QuestionGenerationError(RuntimeError):
    """Falha na LLM ou no contrato de candidatas; nenhuma pergunta e exibida."""


# Quantas candidatas a exploracao pede e consome por rodada.
CANDIDATE_COUNT = 2


def _context(value: ThemeContext | InterviewState | dict[str, Any]) -> ThemeContext:
    if isinstance(value, ThemeContext):
        return value
    if isinstance(value, InterviewState):
        return value.context
    return ThemeContext.from_dict(value)


def _as_signal_summary(signals: Iterable[AuthorialSignal | dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in signals:
        signal = item if isinstance(item, AuthorialSignal) else AuthorialSignal.from_dict(item)
        result.append(
            {
                "type": signal.type,
                "summary": signal.summary,
                "status": signal.status,
            }
        )
    return result


def build_exploration_prompt(
    context: ThemeContext | InterviewState | dict[str, Any],
    *,
    previous_questions: Iterable[str] = (),
    signals: Iterable[AuthorialSignal | dict[str, Any]] = (),
    directions_explored: Iterable[str] = (),
    constraints: Iterable[str] = (),
) -> str:
    """Constroi o prompt inicial sem estrutura editorial ou evidencia esperada."""
    theme = _context(context)
    previous = [str(item).strip() for item in previous_questions if str(item).strip()]
    directions = [str(item).strip() for item in directions_explored if str(item).strip()]
    restrictions = list(theme.restricoes) + [str(item).strip() for item in constraints if str(item).strip()]
    payload = {
        "tema": theme.tema,
        "objetivo_geral": theme.objetivo,
        "formato": theme.formato,
        "personalidade": theme.personalidade,
        "perguntas_anteriores": previous,
        "sinais_extraidos": _as_signal_summary(signals),
        "direcoes_ja_exploradas": directions,
        "restricoes_explicitas": restrictions,
    }
    return (
        "Voce conduz uma entrevista aberta para descobrir material humano autoral.\n"
        f"Gere exatamente {CANDIDATE_COUNT} perguntas independentes e respondiveis sobre o tema.\n"
        "Nao presuma experiencia, opiniao, resultado ou conclusao do autor.\n"
        "Varie as direcoes internas entre as duas: experiencia, opiniao, memoria, erro, decisao, "
        "mudanca de crenca, contradicao, incomodo, caso concreto e limite.\n"
        "Nao transforme essas direcoes em checklist e nao repita perguntas anteriores.\n"
        "Retorne somente JSON no formato {\"candidatas\": [{\"pergunta\": \"...\", "
        "\"direcao\": \"...\", \"por_que_agora\": \"...\"}]}.\n\n"
        f"Contexto: {json.dumps(payload, ensure_ascii=False)}"
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
    raise QuestionGenerationError("runner de perguntas retornou um contrato invalido")


def _candidate_items(payload: object) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("candidatas", "candidates", "perguntas", "questions"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    if any(key in payload for key in ("pergunta", "question", "text")):
        return [payload]
    return []


def generate_candidates(
    runner: Any,
    context: ThemeContext | InterviewState | dict[str, Any],
    *,
    previous_questions: Iterable[str] = (),
    signals: Iterable[AuthorialSignal | dict[str, Any]] = (),
    directions_explored: Iterable[str] = (),
    constraints: Iterable[str] = (),
    tool: str = "codex",
    model: str | None = None,
    reasoning_effort: str | None = None,
    sandbox: str | None = None,
    validate_tool: str = "codex",
    validate_model: str | None = None,
    validate_reasoning_effort: str | None = None,
    validate_sandbox: str | None = None,
) -> list[QuestionCandidate]:
    prompt = build_exploration_prompt(
        context,
        previous_questions=previous_questions,
        signals=signals,
        directions_explored=directions_explored,
        constraints=constraints,
    )
    run_kwargs: dict[str, Any] = {"model": model, "json_output": True}
    if reasoning_effort:
        run_kwargs["reasoning_effort"] = reasoning_effort
    if sandbox:
        run_kwargs["sandbox"] = sandbox
    result = _invoke_runner(runner, tool, prompt, **run_kwargs)
    if not result.ok:
        raise QuestionGenerationError(result.error or result.stderr or "falha ao gerar perguntas")
    parsed = extract_json_object_from_llm_output(
        result.stdout,
        prefer_evaluation_shape=False,
        prefer_keys=("candidatas", "candidates", "perguntas"),
    )
    if not parsed.ok or parsed.data is None:
        raise QuestionGenerationError(parsed.error or "JSON de candidatas invalido")

    theme = _context(context)
    previous = list(previous_questions)
    candidates: list[QuestionCandidate] = []
    for raw in _candidate_items(parsed.data)[:CANDIDATE_COUNT]:
        base = QuestionCandidate.from_dict(raw)
        if not base.text.strip():
            continue
        validation = validate_question(
            runner,
            base.text,
            theme=theme.tema,
            previous_questions=previous,
            tool=validate_tool,
            model=validate_model,
            reasoning_effort=validate_reasoning_effort,
            sandbox=validate_sandbox,
        )
        candidates.append(
            QuestionCandidate(
                text=base.text,
                direction=base.direction,
                risk_scores={**base.risk_scores, **validation.risk_scores},
                relation_score=validation.relation_score,
                discovery_score=base.discovery_score,
                answerability_score=validation.answerability_score,
                accepted=validation.accepted,
                issues=validation.issues,
                source=base.source,
                why_now=base.why_now,
            )
        )
    return candidates


def _candidate_rank(candidate: QuestionCandidate) -> float:
    risks = candidate.risk_scores
    return (
        candidate.relation_score * 3
        + candidate.discovery_score * 2
        + candidate.answerability_score * 2
        - risks.get("induction", 0) * 4
        - risks.get("repetition", 0) * 3
        - risks.get("compound", 0) * 3
    )


def select_question(
    runner: Any,
    candidates: Iterable[QuestionCandidate | dict[str, Any]],
    *,
    theme: str = "",
    previous_questions: Iterable[str] = (),
    tool: str = "codex",
    model: str | None = None,
    reasoning_effort: str | None = None,
    sandbox: str | None = None,
) -> SelectedQuestion | None:
    """Escolhe a melhor candidata por rank; nao descarta por ``accepted``.

    A validacao LLM (quando ja feita em ``generate_candidates``) so informa o
    ranking. ``runner``/``tool``/``model`` permanecem na assinatura por
    compatibilidade, mas nao disparam uma segunda rodada de validacao.
    """
    del runner, theme, previous_questions, tool, model, reasoning_effort, sandbox
    pool: list[QuestionCandidate] = []
    for raw in candidates:
        candidate = raw if isinstance(raw, QuestionCandidate) else QuestionCandidate.from_dict(raw)
        if not candidate.text.strip():
            continue
        pool.append(candidate)
    if not pool:
        return None
    chosen = max(pool, key=_candidate_rank)
    return SelectedQuestion(
        question=chosen.text,
        why_now=chosen.why_now or "Esta pergunta explora uma direcao ainda nao observada.",
        source=chosen.source,
        direction=chosen.direction,
        candidate_id=f"candidate-{hashlib.sha1(chosen.text.encode('utf-8')).hexdigest()[:10]}",
    )


def generate_next_question(
    runner: Any,
    state: InterviewState,
    *,
    tool: str = "codex",
    model: str | None = None,
    reasoning_effort: str | None = None,
    sandbox: str | None = None,
    validate_tool: str = "codex",
    validate_model: str | None = None,
    validate_reasoning_effort: str | None = None,
    validate_sandbox: str | None = None,
) -> SelectedQuestion | None:
    previous = [item.question for item in state.questions]
    directions = [item.direction for item in state.questions if item.direction]
    candidates = generate_candidates(
        runner,
        state,
        previous_questions=previous,
        signals=state.signals,
        directions_explored=directions,
        tool=tool,
        model=model,
        reasoning_effort=reasoning_effort,
        sandbox=sandbox,
        validate_tool=validate_tool,
        validate_model=validate_model,
        validate_reasoning_effort=validate_reasoning_effort,
        validate_sandbox=validate_sandbox,
    )
    state.candidates = candidates
    selected = select_question(
        runner,
        candidates,
        theme=state.context.tema,
        previous_questions=previous,
        tool=validate_tool,
        model=validate_model,
        reasoning_effort=validate_reasoning_effort,
        sandbox=validate_sandbox,
    )
    if selected is not None:
        state.questions.append(selected)
        state.question_count += 1
        state.current_question = selected
    return selected


__all__ = [
    "CANDIDATE_COUNT",
    "QuestionGenerationError",
    "build_exploration_prompt",
    "generate_candidates",
    "select_question",
    "generate_next_question",
]
