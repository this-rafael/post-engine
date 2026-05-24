"""Testes de caracterizacao do parser de payload de geracao."""
from __future__ import annotations

from typing import Any

from content_engine.generator import parse_generation_payload
from content_engine.slidemark_validator import validate_slidemark_document


def _slidemark_minimo() -> dict[str, Any]:
    return {
        "version": "1.0.0",
        "document": {
            "title": "Titulo",
            "description": "Desc",
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
            "fileName": "post",
            "formats": ["png"],
            "pdf": {"pageMode": "square", "source": "rendered-images"},
        },
        "slides": [
            {
                "id": "cover",
                "type": "cover.hero",
                "variant": "alpha",
                "title": "Capa",
                "subtitle": "Sub",
            },
        ],
    }


def test_parse_conteudo_texto_simples() -> None:
    out = parse_generation_payload(
        {
            "conteudo": "Texto do post.",
            "metadados": {"tom": "direto"},
            "alertas": ["aviso"],
        }
    )
    assert out.conteudo == "Texto do post."
    assert out.metadados == {"tom": "direto"}
    assert out.alertas == ["aviso"]
    assert out.parse_error is None
    assert out.slides == []
    assert out.slidemark is None


def test_parse_slidemark_deriva_conteudo() -> None:
    slidemark = _slidemark_minimo()
    out = parse_generation_payload({"slidemark": slidemark})
    assert out.slidemark is not None
    assert validate_slidemark_document(out.slidemark) == []
    assert "Capa" in out.conteudo
    assert len(out.slides) == 1
    assert out.metadados.get("slideMarkVersion") == "1.0.0"
    assert out.metadados.get("totalSlides") == 1


def test_parse_slides_legacy() -> None:
    out = parse_generation_payload(
        {
            "slides": [
                {"numero": 1, "titulo": "Intro", "bullets": ["Ponto A", "Ponto B"]},
            ],
        }
    )
    assert len(out.slides) == 1
    assert out.slides[0].titulo == "Intro"
    assert "Intro" in out.conteudo


def test_parse_sugestoes_imagem() -> None:
    slidemark = _slidemark_minimo()
    out = parse_generation_payload(
        {
            "slidemark": slidemark,
            "sugestoesImagem": [
                {
                    "slideId": "cover",
                    "modo": "descricao",
                    "descricao": "Foto de capa",
                },
            ],
        }
    )
    assert out.slides[0].sugestao_imagem is not None
    assert out.slides[0].sugestao_imagem.descricao == "Foto de capa"
    assert len(out.sugestoes_imagem) == 1
