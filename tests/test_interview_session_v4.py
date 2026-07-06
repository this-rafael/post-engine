from __future__ import annotations

import json
from pathlib import Path

from content_engine.schemas import AgentResult
from content_engine.session_app import PostEngineApp


class V4Agent:
    def run(self, tool: str, prompt: str, **kwargs: object) -> AgentResult:
        del kwargs
        if "candidatas" in prompt or "Gere exatamente 2" in prompt or "Gere de 3 a 6" in prompt:
            stdout = json.dumps(
                {
                    "candidatas": [
                        {
                            "pergunta": "Que caso concreto sobre observabilidade mudou sua forma de trabalhar?",
                            "direcao": "experiencia",
                            "por_que_agora": "Ainda falta uma experiencia situada.",
                        }
                    ]
                }
            )
        else:
            stdout = json.dumps(
                {
                    "aprovou": True,
                    "confianca": 0.8,
                    "forcas": ["resposta situada"],
                    "fraquezas": [],
                    "riscos": [],
                    "justificativa": "Existe material humano verificavel.",
                    "integridade_epistemica": "alta",
                }
            )
        return AgentResult(
            tool=tool,
            command=[tool],
            returncode=0,
            stdout=stdout,
            stderr="",
            events=[],
            error=None,
        )


def test_v4_actions_persist_original_answer_and_projection(tmp_path: Path) -> None:
    session_path = tmp_path / "session.json"
    app = PostEngineApp(
        agent_factory=lambda: V4Agent(),
        question_agent_factory=lambda: V4Agent(),
        session_path=session_path,
        run_sync_inline=True,
    )
    app.state.tema = "observabilidade"
    app.state.plataforma = "linkedin"
    app.state.objetivo_do_post = "explicar"
    app.state.tipo_de_post = "post"

    started = app.action_start_interview_v4()
    question = started["current_question"]["question"]
    submitted = app.action_submit_v4_answer(
        "Eu interrompi um deploy quando uma fila cresceu por duas horas."
    )

    assert submitted["answers"][0]["original"].startswith("Eu interrompi")
    assert submitted["answers"][0]["normalized"] == submitted["answers"][0]["original"]
    assert submitted["questions"][0]["question"] == question
    assert session_path.exists()
    persisted = json.loads(session_path.read_text(encoding="utf-8"))
    assert persisted["schema_version"] == "4.0"
    assert persisted["interview_state"]["answers"][0]["original"].startswith("Eu interrompi")


class FailingThenOkAgent:
    def __init__(self) -> None:
        self.calls = 0

    def run(self, tool: str, prompt: str, **kwargs: object) -> AgentResult:
        del kwargs
        self.calls += 1
        if self.calls == 1 and ("candidatas" in prompt or "Gere exatamente 2" in prompt or "Gere de 3 a 6" in prompt):
            return AgentResult(
                tool=tool,
                command=[tool],
                returncode=1,
                stdout="",
                stderr="Unexpected server error",
                events=[],
                error="Unexpected server error",
            )
        if "candidatas" in prompt or "Gere exatamente 2" in prompt or "Gere de 3 a 6" in prompt:
            stdout = json.dumps(
                {
                    "candidatas": [
                        {
                            "pergunta": "Que caso concreto sobre observabilidade mudou sua forma de trabalhar?",
                            "direcao": "experiencia",
                            "por_que_agora": "Ainda falta uma experiencia situada.",
                        }
                    ]
                }
            )
        else:
            stdout = json.dumps(
                {
                    "aprovou": True,
                    "confianca": 0.8,
                    "forcas": ["resposta situada"],
                    "fraquezas": [],
                    "riscos": [],
                    "justificativa": "Existe material humano verificavel.",
                    "integridade_epistemica": "alta",
                }
            )
        return AgentResult(
            tool=tool,
            command=[tool],
            returncode=0,
            stdout=stdout,
            stderr="",
            events=[],
            error=None,
        )


def test_start_persists_interview_when_first_question_llm_fails(tmp_path: Path) -> None:
    session_path = tmp_path / "session.json"
    agent = FailingThenOkAgent()
    app = PostEngineApp(
        agent_factory=lambda: agent,
        question_agent_factory=lambda: agent,
        session_path=session_path,
        run_sync_inline=True,
    )
    app.state.tema = "observabilidade"
    app.state.plataforma = "linkedin"
    app.state.objetivo_do_post = "explicar"
    app.state.tipo_de_post = "post"

    started = app.action_start_interview_v4()
    assert started["current_question"] is None
    assert app.state.error
    assert app._v4_state() is not None
    persisted = json.loads(session_path.read_text(encoding="utf-8"))
    assert persisted["interview_state"]["schema_version"] == "4.0"

    retried = app.action_generate_other_question()
    assert retried["current_question"] is not None
    assert app.state.error is None


def test_generate_other_question_bootstraps_missing_interview(tmp_path: Path) -> None:
    session_path = tmp_path / "session.json"
    app = PostEngineApp(
        agent_factory=lambda: V4Agent(),
        question_agent_factory=lambda: V4Agent(),
        session_path=session_path,
        run_sync_inline=True,
    )
    app.state.tema = "observabilidade"
    app.state.plataforma = "linkedin"
    app.state.objetivo_do_post = "explicar"
    app.state.tipo_de_post = "post"
    assert app.state.interview_state in (None, {})

    started = app.action_generate_other_question()
    assert started["current_question"] is not None
    assert app._v4_state() is not None
