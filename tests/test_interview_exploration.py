from __future__ import annotations

import json

from content_engine.interview.exploration import build_exploration_prompt, select_question
from content_engine.interview.schemas import QuestionCandidate, ThemeContext
from content_engine.interview.validation import validate_question
from content_engine.schemas import AgentResult


class _MockValidationRunner:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response

    def run(self, tool: str, prompt: str, **kwargs: object) -> AgentResult:
        return AgentResult(
            tool=tool,  # type: ignore[arg-type]
            command=[tool],
            returncode=0,
            stdout=json.dumps(self.response),
            stderr="",
        )


def _make_runner(
    accepted: bool = True,
    issues: list[str] | None = None,
    induction: float = 0.0,
    repetition: float = 0.0,
    compound: float = 0.0,
    relation: float = 1.0,
    answerability: float = 1.0,
) -> _MockValidationRunner:
    return _MockValidationRunner(
        {
            "accepted": accepted,
            "issues": issues or [],
            "risk_scores": {
                "induction": induction,
                "repetition": repetition,
                "compound": compound,
            },
            "relation_score": relation,
            "answerability_score": answerability,
        }
    )


def test_FR_001_initial_prompt_excludes_editorial_structure() -> None:
    prompt = build_exploration_prompt(
        ThemeContext("arquitetura event-driven", objetivo="explicar uma decisao", formato="post")
    )
    lowered = prompt.lower()
    assert "expected_evidence" not in lowered
    assert "need_id" not in lowered
    assert "cta" not in lowered
    assert "estrutura do post" not in lowered
    assert "gere exatamente 2" in lowered


def test_select_question_picks_best_of_two_even_if_not_accepted() -> None:
    candidates = [
        QuestionCandidate(
            text="Escreva o CTA e a conclusao do post.",
            direction="editorial",
            accepted=False,
            relation_score=0.1,
            answerability_score=0.1,
        ),
        QuestionCandidate(
            text="Que situacao concreta mudou sua forma de pensar sobre eventos?",
            direction="experiencia",
            discovery_score=0.9,
            answerability_score=1.0,
            relation_score=0.8,
            accepted=False,
        ),
    ]
    selected = select_question(_make_runner(accepted=False), candidates, theme="arquitetura event-driven")
    assert selected is not None
    assert "situacao concreta" in selected.question
    assert "CTA" not in selected.question.upper()


def test_FR_002_question_does_not_presuppose_answer() -> None:
    runner = _make_runner(
        accepted=False,
        issues=["INDUCTION_RISK"],
        induction=0.8,
    )
    validation = validate_question(
        runner,
        "Como voce conseguiu resolver o incidente?",
        theme="arquitetura event-driven",
    )
    assert validation.accepted is False
    assert "INDUCTION_RISK" in validation.issues


def test_FR_003_compound_question_blocked() -> None:
    runner = _make_runner(
        accepted=False,
        issues=["COMPOUND_QUESTION"],
        compound=1.0,
    )
    validation = validate_question(
        runner,
        "O que aconteceu e o que voce mudou depois?",
        theme="arquitetura event-driven",
    )
    assert validation.accepted is False
    assert "COMPOUND_QUESTION" in validation.issues


def test_FR_004_best_ranked_candidate_is_displayed() -> None:
    candidates = [
        QuestionCandidate(
            text="Escreva o CTA e a conclusao do post.",
            direction="editorial",
            accepted=False,
            relation_score=0.0,
        ),
        QuestionCandidate(
            text="Que situacao concreta mudou sua forma de pensar sobre eventos?",
            direction="experiencia",
            discovery_score=0.9,
            answerability_score=1.0,
            relation_score=1.0,
            accepted=True,
        ),
    ]
    runner = _make_runner(accepted=True)
    selected = select_question(runner, candidates, theme="arquitetura event-driven")
    assert selected is not None
    assert "CTA" not in selected.question.upper()
    assert "situacao concreta" in selected.question


def test_validate_question_empty_returns_empty_issue() -> None:
    runner = _make_runner()
    validation = validate_question(runner, "")
    assert validation.accepted is False
    assert "EMPTY" in validation.issues


def test_validate_question_llm_error_returns_llm_error_issue() -> None:
    class _FailingRunner:
        def run(self, tool: str, prompt: str, **kwargs: object) -> AgentResult:
            return AgentResult(
                tool=tool,  # type: ignore[arg-type]
                command=[tool],
                returncode=1,
                stdout="",
                stderr="error",
                error="falha",
            )

    validation = validate_question(_FailingRunner(), "Uma pergunta valida?")
    assert validation.accepted is False
    assert "LLM_ERROR" in validation.issues


class _QuestionRunner:
    def run(self, tool: str, prompt: str, **kwargs: object):
        return AgentResult(
            tool=tool,  # type: ignore[arg-type]
            command=[tool],
            returncode=0,
            stdout=json.dumps(
                {
                    "candidatas": [
                        {
                            "pergunta": "Que situacao concreta mudou sua forma de pensar sobre eventos?",
                            "direcao": "experiencia",
                            "por_que_agora": "Ainda falta um caso concreto.",
                        }
                    ]
                }
            ),
            stderr="",
        )
