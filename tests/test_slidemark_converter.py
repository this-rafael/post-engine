"""Testes do conversor SlideMark."""
from __future__ import annotations

import json
from typing import Any

import pytest

from content_engine.slidemark_converter import SlideMarkConverter
from content_engine.slidemark_validator import validate_slidemark_document
from tests.llm_fakes import AgentFakeRunMixin
from content_engine.schemas import AgentResult


class FakeAgent(AgentFakeRunMixin):
    def __init__(
        self,
        stdout: str = "",
        returncode: int = 0,
        error: str | None = None,
    ) -> None:
        self.stdout = stdout
        self.returncode = returncode
        self.error = error
        self.calls: list[dict[str, Any]] = []

    def run_codex(
        self,
        prompt: str,
        *,
        model: str | None = None,
        reasoning_effort: str | None = None,
        sandbox: str = "read-only",
        json_output: bool = False,
        extra_context: str | None = None,
        ephemeral: bool = True,
        ignore_user_config: bool = False,
        runner: Any = None,
    ) -> AgentResult:
        del model, reasoning_effort, sandbox, extra_context, ephemeral
        del ignore_user_config, runner
        self.calls.append({"prompt": prompt, "json_output": json_output})
        return AgentResult(
            tool="codex",
            command=["codex", "exec"],
            returncode=self.returncode,
            stdout=self.stdout,
            stderr="",
            events=None,
            error=self.error,
        )


def _slidemark_valido() -> dict[str, Any]:
    return {
        "version": "1.0.0",
        "document": {
            "title": "Adapter Pattern",
            "description": "Resumo visual sobre adapter pattern",
            "language": "pt-BR",
        },
        "canvas": {"width": 1080, "height": 1080},
        "theme": "diffvision-dracula",
        "author": {"name": "Rafael Pereira", "handle": "@this-rafael-pereira"},
        "settings": {
            "showAuthor": True,
            "showPageNumber": True,
            "showSwipeHint": True,
            "swipeHintText": "Desliza",
        },
        "export": {
            "fileName": "adapter-pattern",
            "formats": ["png", "zip", "pdf"],
            "pdf": {"pageMode": "square", "source": "rendered-images"},
        },
        "slides": [
            {
                "id": "adapter-cover",
                "type": "cover.hero",
                "variant": "alpha",
                "title": "Adapter sem misterio",
                "subtitle": "Como encaixar contratos incompativeis.",
            },
            {
                "id": "adapter-contexto",
                "type": "content.text",
                "variant": "bravo",
                "title": "O problema real",
                "body": ["Seu codigo espera uma interface e a lib entrega outra."],
            },
            {
                "id": "adapter-cta",
                "type": "closing.cta",
                "variant": "charlie",
                "title": "Use quando houver fronteira",
                "text": "Nao use para esconder design ruim.",
                "cta": "Salve para revisar antes do proximo refactor.",
            },
        ],
    }


def test_converter_retorna_slidemark_valido() -> None:
    payload = {"slidemark": _slidemark_valido()}
    agent = FakeAgent(stdout=json.dumps(payload))
    converter = SlideMarkConverter(agent=agent, tool="codex")
    resultado = converter.converter(
        tema="Adapter",
        plataforma="linkedin",
        tipo_de_post="short_carousel",
        conteudo_final="Slide 1\n\nSlide 2\n\nSlide 3",
        segmentos=[
            {"id": "s1", "ordem": 1, "texto": "Capa", "papel_interno": "capa"},
        ],
    )
    assert validate_slidemark_document(resultado.slidemark) == []
    assert resultado.alertas == []
    assert agent.calls[0]["json_output"] is True
    assert "Adapter" in agent.calls[0]["prompt"]


def test_converter_aplica_defaults_autor_quando_ausentes() -> None:
    doc = _slidemark_valido()
    doc["author"] = {}
    doc["theme"] = "tema-invalido"
    payload = {"slidemark": doc}
    agent = FakeAgent(stdout=json.dumps(payload))
    converter = SlideMarkConverter(agent=agent, tool="codex")
    resultado = converter.converter(
        tema="Tema",
        plataforma="linkedin",
        tipo_de_post="short_carousel",
        conteudo_final="Texto sem codigo",
    )
    assert resultado.slidemark["author"]["name"] == "Rafael Pereira"
    assert resultado.slidemark["author"]["handle"] == "@this-rafael-pereira"
    assert resultado.slidemark["theme"] == "rafael-io-executive-dark"


def test_converter_rejeita_tipo_nao_visual() -> None:
    agent = FakeAgent()
    converter = SlideMarkConverter(agent=agent, tool="codex")
    with pytest.raises(ValueError, match="nao e trilha visual"):
        converter.converter(
            tema="Tema",
            plataforma="linkedin",
            tipo_de_post="post",
            conteudo_final="conteudo",
        )


def test_converter_json_invalido_levanta_value_error() -> None:
    agent = FakeAgent(stdout="sem json")
    converter = SlideMarkConverter(agent=agent, tool="codex")
    with pytest.raises(ValueError, match="JSON invalido"):
        converter.converter(
            tema="Tema",
            plataforma="linkedin",
            tipo_de_post="long_slide",
            conteudo_final="conteudo",
        )


def test_converter_rejeita_documento_incompleto() -> None:
    doc = _slidemark_valido()
    doc["slides"] = doc["slides"][:1]
    payload = {"slidemark": doc}
    agent = FakeAgent(stdout=json.dumps(payload))
    converter = SlideMarkConverter(agent=agent, tool="codex")
    with pytest.raises(ValueError, match="ultimo slide deve ser closing.cta"):
        converter.converter(
            tema="Tema",
            plataforma="linkedin",
            tipo_de_post="short_carousel",
            conteudo_final="conteudo",
        )
