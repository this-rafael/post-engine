"""Fakes LLM compartilhados para os testes de integrações."""
from __future__ import annotations

import json
from typing import Any

from content_engine.schemas import AgentResult


class AgentFakeRunMixin:
    def run(self, tool: str, prompt: str, **kwargs: Any) -> AgentResult:
        if tool == "opencode":
            opencode_kwargs = {
                key: kwargs[key]
                for key in (
                    "model",
                    "agent",
                    "files",
                    "json_output",
                    "attach_url",
                    "dangerously_skip_permissions",
                    "runner",
                )
                if key in kwargs
            }
            return self.run_opencode(prompt, **opencode_kwargs)
        codex_kwargs = {
            key: kwargs[key]
            for key in (
                "model",
                "reasoning_effort",
                "sandbox",
                "json_output",
                "extra_context",
                "ephemeral",
                "ignore_user_config",
                "runner",
            )
            if key in kwargs
        }
        return self.run_codex(prompt, **codex_kwargs)


def fake_v4_llm_run(tool: str, prompt: str, **kwargs: Any) -> AgentResult:
    """Deterministic boundary fake for open exploration and authorship review."""
    del kwargs
    if "candidatas" in prompt or "Gere exatamente 2" in prompt or "Gere de 3 a 6" in prompt:
        stdout = json.dumps(
            {
                "candidatas": [
                    {
                        "pergunta": "Que caso concreto mudou sua forma de trabalhar sobre esse tema?",
                        "direcao": "experiencia",
                        "por_que_agora": "Ainda falta material situado.",
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
                "justificativa": "Material humano verificavel.",
                "integridade_epistemica": "alta",
            }
        )
    return AgentResult(
        tool=tool,  # type: ignore[arg-type]
        command=[tool],
        returncode=0,
        stdout=stdout,
        stderr="",
        events=[],
        error=None,
    )
