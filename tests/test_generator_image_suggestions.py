"""Testes de sugestoes de imagem por slide na geracao."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from content_engine.agent_wrapper import AgentWrapper
from content_engine.generator import ContentGenerator, _formatar_sugestao_imagem
from content_engine.schemas import AgentResult, GenerationPromptInput, SugestaoImagem
from content_engine.segmentation import segmentar_slidemark


class FakeAgent(AgentWrapper):
    def __init__(self, payload: AgentResult) -> None:
        super().__init__(workspace=Path("/tmp/ws"))
        self._payload = payload

    def run_codex(self, prompt: str, **kwargs: Any) -> AgentResult:
        return self._payload

    def run_opencode(self, prompt: str, **kwargs: Any) -> AgentResult:
        return self._payload


def _slidemark_minimo() -> dict[str, Any]:
    return {
        "version": "1.0.0",
        "document": {
            "title": "GraphQL",
            "description": "Guia",
            "language": "pt-BR",
        },
        "canvas": {"width": 1080, "height": 1080},
        "theme": "diffvision-dracula",
        "author": {"name": "Autor", "handle": "@autor"},
        "settings": {
            "showAuthor": True,
            "showPageNumber": True,
            "showSwipeHint": True,
            "swipeHintText": "Desliza",
        },
        "export": {
            "fileName": "graphql",
            "formats": ["png", "zip", "pdf"],
            "pdf": {"pageMode": "square", "source": "rendered-images"},
        },
        "slides": [
            {
                "id": "gql-cover",
                "type": "cover.hero",
                "variant": "alpha",
                "title": "GraphQL na pratica",
                "subtitle": "Do zero ao primeiro query",
            },
            {
                "id": "gql-cta",
                "type": "closing.cta",
                "variant": "alpha",
                "title": "Resumo",
                "cta": "Comente sua experiencia",
            },
        ],
    }


def _input() -> GenerationPromptInput:
    return GenerationPromptInput(
        tema="GraphQL",
        plataforma="LinkedIn",
        objetivo_do_post="ensinar",
        tipo_de_post="long_slide",
        briefing_autoral={},
    )


def test_parse_sugestoes_imagem_descricao() -> None:
    payload = {
        "slidemark": _slidemark_minimo(),
        "sugestoesImagem": [
            {
                "slideId": "gql-cover",
                "numero": 1,
                "modo": "descricao",
                "descricao": "Diagrama minimalista de API em fundo escuro",
            },
            {
                "slideId": "gql-cta",
                "numero": 2,
                "modo": "descricao",
                "descricao": "Icone de check verde em destaque",
            },
        ],
        "conteudo": "",
        "metadados": {},
        "alertas": [],
    }
    fake = FakeAgent(
        AgentResult(
            tool="codex",
            command=["codex"],
            returncode=0,
            stdout=json.dumps(payload),
            stderr="",
        )
    )
    out = ContentGenerator(agent=fake, tool="codex").generate(_input())
    assert out.parse_error is None
    assert len(out.slides) == 2
    assert out.slides[0].sugestao_imagem is not None
    assert out.slides[0].sugestao_imagem.modo == "descricao"
    assert "Diagrama minimalista" in (out.slides[0].notas_visuais or "")
    assert len(out.sugestoes_imagem) == 2


def test_parse_sugestoes_imagem_aceita_formato_legado_slide_e_sugestao() -> None:
    payload = {
        "slidemark": _slidemark_minimo(),
        "sugestoesImagem": [
            {
                "slide": 1,
                "sugestao": "Diagrama de consultas e dependencias do GraphQL",
            }
        ],
        "conteudo": "",
        "metadados": {},
        "alertas": [],
    }
    fake = FakeAgent(
        AgentResult(
            tool="codex",
            command=["codex"],
            returncode=0,
            stdout=json.dumps(payload),
            stderr="",
        )
    )

    out = ContentGenerator(agent=fake, tool="codex").generate(_input())

    assert out.parse_error is None
    assert out.slides[0].sugestao_imagem is not None
    assert out.slides[0].sugestao_imagem.descricao == (
        "Diagrama de consultas e dependencias do GraphQL"
    )
    assert out.sugestoes_imagem == [
        {
            "numero": 1,
            "modo": "descricao",
            "descricao": "Diagrama de consultas e dependencias do GraphQL",
        }
    ]


def test_parse_sugestoes_imagem_link() -> None:
    sugestao = SugestaoImagem(
        modo="link",
        descricao="Screenshot oficial",
        url="https://example.com/img.png",
        fonte="Docs",
    )
    texto = _formatar_sugestao_imagem(sugestao)
    assert "https://example.com/img.png" in texto
    assert "Docs" in texto


def test_segmentar_slidemark_propaga_sugestao() -> None:
    slidemark = _slidemark_minimo()
    sugestoes = [
        {
            "slideId": "gql-cover",
            "numero": 1,
            "modo": "descricao",
            "descricao": "Terminal com erro em vermelho",
        }
    ]
    segmentos = segmentar_slidemark(slidemark, sugestoes_imagem=sugestoes)
    assert segmentos[0]["sugestaoImagem"]["descricao"] == "Terminal com erro em vermelho"


def test_segmentar_slidemark_aceita_formato_legado_slide_e_sugestao() -> None:
    segmentos = segmentar_slidemark(
        _slidemark_minimo(),
        sugestoes_imagem=[
            {"slide": 2, "sugestao": "Checklist visual da chamada"}
        ],
    )

    assert segmentos[1]["sugestaoImagem"] == {
        "modo": "descricao",
        "descricao": "Checklist visual da chamada",
    }
