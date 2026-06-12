"""Validacao de perguntas via LLM para o gate de exibicao V4."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterable

from ..llm_json_parser import extract_json_object_from_llm_output
from ..schemas import AgentResult


_KNOWN_ISSUES = frozenset({
    "EMPTY",
    "EDITORIAL_DELEGATION",
    "COMPOUND_QUESTION",
    "INDUCTION_RISK",
    "NOT_RELATED_TO_THEME",
    "NOT_ANSWERABLE",
    "REPETITION_RISK",
})


@dataclass(frozen=True)
class QuestionValidation:
    accepted: bool
    issues: tuple[str, ...] = ()
    risk_scores: dict[str, float] = field(default_factory=dict)
    relation_score: float = 0.0
    answerability_score: float = 0.0

    def to_dict(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "issues": list(self.issues),
            "risk_scores": dict(self.risk_scores),
            "relation_score": self.relation_score,
            "answerability_score": self.answerability_score,
        }


def build_validation_prompt(
    text: str,
    *,
    theme: str = "",
    previous_questions: Iterable[str] = (),
) -> str:
    previous = [str(q).strip() for q in previous_questions if str(q).strip()]
    payload: dict[str, Any] = {
        "pergunta": text,
        "tema": theme,
        "perguntas_anteriores": previous,
    }
    return (
        "Voce e um revisor de qualidade de perguntas para entrevistas autoriais.\n"
        "Avalie a pergunta fornecida e retorne SOMENTE JSON no formato:\n"
        "{\n"
        '  "accepted": true ou false,\n'
        '  "issues": ["lista de problemas encontrados"],\n'
        '  "risk_scores": {"induction": 0.0-1.0, "repetition": 0.0-1.0, "compound": 0.0-1.0},\n'
        '  "relation_score": 0.0-1.0,\n'
        '  "answerability_score": 0.0-1.0\n'
        "}\n\n"
        "Criterios de avaliacao:\n"
        "- EMPTY: pergunta vazia, template ou placeholder.\n"
        "- EDITORIAL_DELEGATION: pergunta que delega decisoes editoriais "
        "(cta, titulo, headline, gancho, hook, slide, carrossel, secao, legenda, hashtag, copy, formato).\n"
        "- COMPOUND_QUESTION: pergunta composta com multiplas interrogacoes ou conjuncoes que pedem mais de uma resposta.\n"
        "- INDUCTION_RISK: pergunta indutiva que presume experiencia, opiniao, resultado "
        "ou conduz a resposta esperada (presuposicao, leading question).\n"
        "- NOT_RELATED_TO_THEME: pergunta sem relacao semantica com o tema da entrevista.\n"
        "- NOT_ANSWERABLE: pergunta muito curta, sem ponto de interrogacao, "
        "excessivamente longa ou impossivel de responder de forma concreta.\n"
        "- REPETITION_RISK: pergunta semanticamente muito similar a uma das perguntas anteriores.\n\n"
        "risk_scores deve conter valores entre 0.0 e 1.0 para induction, repetition e compound.\n"
        "relation_score mede o quanto a pergunta se relaciona com o tema (0.0 = nada, 1.0 = total).\n"
        "answerability_score mede o quanto a pergunta e respondivel de forma concreta (0.0 a 1.0).\n"
        "accepted deve ser true apenas se NENHUM issue for encontrado.\n"
        "issues deve conter apenas rotulos da lista: "
        f"{', '.join(sorted(_KNOWN_ISSUES))}.\n\n"
        f"Contexto: {json.dumps(payload, ensure_ascii=False)}"
    )


def _invoke(runner: Any, tool: str, prompt: str, **kwargs: Any) -> AgentResult:
    if callable(runner) and not hasattr(runner, "run"):
        result = runner(prompt)
    else:
        result = runner.run(tool, prompt, **kwargs)
    if isinstance(result, AgentResult):
        return result
    if isinstance(result, str):
        return AgentResult(tool=tool, command=[tool], returncode=0, stdout=result, stderr="")  # type: ignore[arg-type]
    raise TypeError("runner de validacao retornou um contrato invalido")


def _parse_validation(data: dict[str, Any]) -> QuestionValidation:
    accepted_raw = data.get("accepted", data.get("aceitou", data.get("aprovou", False)))
    issues_raw = data.get("issues", data.get("problemas", []))
    risks_raw = data.get("risk_scores", data.get("riscos", {}))
    relation_raw = data.get("relation_score", data.get("relacao", 0.0))
    answerability_raw = data.get("answerability_score", data.get("respondibilidade", 0.0))

    issues_list: list[str] = []
    if isinstance(issues_raw, list):
        for item in issues_raw:
            label = str(item).strip().upper()
            if label in _KNOWN_ISSUES:
                issues_list.append(label)

    risks: dict[str, float] = {}
    if isinstance(risks_raw, dict):
        for key in ("induction", "repetition", "compound"):
            value = risks_raw.get(key, 0.0)
            try:
                risks[key] = round(min(1.0, max(0.0, float(value))), 3)
            except (TypeError, ValueError):
                risks[key] = 0.0

    try:
        relation = round(min(1.0, max(0.0, float(relation_raw))), 3)
    except (TypeError, ValueError):
        relation = 0.0

    try:
        answerability = round(min(1.0, max(0.0, float(answerability_raw))), 3)
    except (TypeError, ValueError):
        answerability = 0.0

    accepted = bool(accepted_raw) and not issues_list
    return QuestionValidation(
        accepted=accepted,
        issues=tuple(dict.fromkeys(issues_list)),
        risk_scores=risks,
        relation_score=relation,
        answerability_score=answerability,
    )


def validate_question(
    runner: Any,
    text: str,
    *,
    theme: str = "",
    previous_questions: Iterable[str] = (),
    tool: str = "codex",
    model: str | None = None,
    reasoning_effort: str | None = None,
    sandbox: str | None = None,
) -> QuestionValidation:
    question = " ".join(text.strip().split())
    if not question:
        return QuestionValidation(
            accepted=False,
            issues=("EMPTY",),
            risk_scores={"induction": 0.0, "repetition": 0.0, "compound": 0.0},
            relation_score=0.0,
            answerability_score=0.0,
        )

    prompt = build_validation_prompt(
        question,
        theme=theme,
        previous_questions=previous_questions,
    )
    run_kwargs: dict[str, Any] = {"model": model, "json_output": True}
    if reasoning_effort:
        run_kwargs["reasoning_effort"] = reasoning_effort
    if sandbox:
        run_kwargs["sandbox"] = sandbox

    try:
        result = _invoke(runner, tool, prompt, **run_kwargs)
    except Exception:
        return QuestionValidation(
            accepted=False,
            issues=("LLM_ERROR",),
            risk_scores={"induction": 0.0, "repetition": 0.0, "compound": 0.0},
            relation_score=0.0,
            answerability_score=0.0,
        )

    if not result.ok:
        return QuestionValidation(
            accepted=False,
            issues=("LLM_ERROR",),
            risk_scores={"induction": 0.0, "repetition": 0.0, "compound": 0.0},
            relation_score=0.0,
            answerability_score=0.0,
        )

    parsed = extract_json_object_from_llm_output(
        result.stdout,
        prefer_evaluation_shape=False,
        prefer_keys=("accepted", "issues", "risk_scores", "relation_score"),
    )
    if not parsed.ok or parsed.data is None:
        return QuestionValidation(
            accepted=False,
            issues=("LLM_ERROR",),
            risk_scores={"induction": 0.0, "repetition": 0.0, "compound": 0.0},
            relation_score=0.0,
            answerability_score=0.0,
        )

    return _parse_validation(parsed.data)


def validar_pergunta(*args: object, **kwargs: object) -> QuestionValidation:
    """Alias em portugues para integracoes que usam a nomenclatura do projeto."""
    return validate_question(*args, **kwargs)  # type: ignore[arg-type]


__all__ = [
    "QuestionValidation",
    "build_validation_prompt",
    "validate_question",
    "validar_pergunta",
]
