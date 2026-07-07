"""Testes de SPEC-059/060: robustez de parse_segmentos e gerador."""
from __future__ import annotations

import json
from typing import Any

import pytest

from content_engine.generator import ContentGenerator
from content_engine.schemas import AgentResult, GenerationPromptInput
from content_engine.segmentation import parse_segmentos, segmentar_slidemark
from content_engine.slidemark_validator import validate_slidemark_document
from tests.llm_fakes import AgentFakeRunMixin


class FakeAgent(AgentFakeRunMixin):
    def __init__(self, stdout: str = "", returncode: int = 0, error: str | None = None) -> None:
        self.stdout: str = stdout
        self.returncode: int = returncode
        self.error: str | None = error
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
        del reasoning_effort
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

    def run_opencode(
        self,
        prompt: str,
        *,
        model: str | None = None,
        agent: str | None = None,
        files: list[Any] | None = None,
        json_output: bool = False,
        attach_url: str | None = None,
        dangerously_skip_permissions: bool = False,
        runner: Any = None,
    ) -> AgentResult:
        self.calls.append({"prompt": prompt, "json_output": json_output})
        return AgentResult(
            tool="opencode",
            command=["opencode", "run"],
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
        "author": {"name": "Autor", "handle": "@autor"},
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
                "title": "Adapter sem mistério",
                "subtitle": "Como encaixar contratos incompatíveis sem gambiarra.",
            },
            {
                "id": "adapter-contexto",
                "type": "content.text",
                "variant": "bravo",
                "title": "O problema real",
                "body": ["Seu código espera uma interface e a lib entrega outra."],
                "highlight": {"text": "Adapter protege o core."},
            },
            {
                "id": "adapter-cta",
                "type": "closing.cta",
                "variant": "charlie",
                "title": "Use quando houver fronteira",
                "text": "Não use para esconder design ruim.",
                "cta": "Salve para revisar antes do próximo refactor.",
            },
        ],
    }


def test_spec_059_parse_segmentos_payload_sem_segmentos_levanta_value_error() -> None:
    with pytest.raises(ValueError):
        parse_segmentos({})


def test_spec_059_parse_segmentos_segmentos_string_levanta_value_error() -> None:
    with pytest.raises(ValueError):
        parse_segmentos({"segmentos": "uma string"})


def test_spec_059_parse_segmentos_item_string_na_lista_levanta_value_error() -> None:
    with pytest.raises(ValueError):
        parse_segmentos({"segmentos": ["item string"]})


def test_spec_059_parse_segmentos_campos_ausentes() -> None:
    with pytest.raises(ValueError):
        parse_segmentos({"segmentos": [{"ordem": 1, "texto": "a"}]})
    with pytest.raises(ValueError):
        parse_segmentos({"segmentos": [{"id": "s", "texto": "a"}]})
    with pytest.raises(ValueError):
        parse_segmentos({"segmentos": [{"id": "s", "ordem": 1}]})


def test_spec_059_parse_segmentos_ids_duplicados_levanta_value_error() -> None:
    payload = {
        "segmentos": [
            {"id": "x", "ordem": 1, "texto": "a"},
            {"id": "x", "ordem": 2, "texto": "b"},
        ]
    }
    with pytest.raises(ValueError):
        parse_segmentos(payload)


def test_spec_059_parse_segmentos_ordem_nao_sequencial_inicia_em_2() -> None:
    payload = {
        "segmentos": [
            {"id": "a", "ordem": 2, "texto": "a"},
            {"id": "b", "ordem": 3, "texto": "b"},
        ]
    }
    with pytest.raises(ValueError):
        parse_segmentos(payload)


def test_spec_059_parse_segmentos_ordem_com_pulo() -> None:
    payload = {
        "segmentos": [
            {"id": "a", "ordem": 1, "texto": "a"},
            {"id": "b", "ordem": 2, "texto": "b"},
            {"id": "c", "ordem": 4, "texto": "c"},
        ]
    }
    with pytest.raises(ValueError):
        parse_segmentos(payload)


def test_spec_059_parse_segmentos_ordem_zero_levanta_value_error() -> None:
    payload = {
        "segmentos": [
            {"id": "a", "ordem": 0, "texto": "a"},
        ]
    }
    with pytest.raises(ValueError):
        parse_segmentos(payload)


def test_spec_059_parse_segmentos_id_vazio_levanta_value_error() -> None:
    payload = {
        "segmentos": [
            {"id": "", "ordem": 1, "texto": "a"},
        ]
    }
    with pytest.raises(ValueError):
        parse_segmentos(payload)


def test_spec_060_content_generator_payload_completo() -> None:
    payload = {
        "conteudo": "post gerado aqui",
        "metadados": {"tema": "x", "plataforma": "LinkedIn"},
        "alertas": ["aviso 1"],
    }
    agent = FakeAgent(stdout=json.dumps(payload))
    generator = ContentGenerator(agent, "codex")
    data = GenerationPromptInput(
        tema="x",
        plataforma="LinkedIn",
        objetivo_do_post="autoridade",
        tipo_de_post="post",
        briefing_autoral={"tema": "x"},
    )
    resultado = generator.generate(data)
    assert resultado.conteudo == "post gerado aqui"
    assert resultado.metadados.get("tema") == "x"
    assert resultado.alertas == ["aviso 1"]
    assert resultado.parse_error is None
    assert resultado.conteudo != ""


def test_spec_060_content_generator_fallback_stdout_quando_json_invalido() -> None:
    agent = FakeAgent(stdout="texto puro sem json")
    generator = ContentGenerator(agent, "codex")
    data = GenerationPromptInput(
        tema="x",
        plataforma="LinkedIn",
        objetivo_do_post="autoridade",
        tipo_de_post="post",
        briefing_autoral={},
    )
    resultado = generator.generate(data)
    assert resultado.conteudo == "texto puro sem json"
    assert resultado.metadados.get("raw") is True
    assert resultado.parse_error is not None
    assert any("JSON invalido" in a for a in resultado.alertas)


def test_spec_060_content_generator_erro_agent_retorna_vazio_com_alerta() -> None:
    agent = FakeAgent(stdout="", returncode=1, error="cli falhou")
    generator = ContentGenerator(agent, "codex")
    data = GenerationPromptInput(
        tema="x",
        plataforma="LinkedIn",
        objetivo_do_post="autoridade",
        tipo_de_post="post",
        briefing_autoral={},
    )
    resultado = generator.generate(data)
    assert resultado.conteudo == ""
    assert resultado.parse_error == "cli falhou"
    assert any("Falha" in a for a in resultado.alertas)


def test_spec_060_content_generator_com_opencode() -> None:
    payload = {"conteudo": "ok", "metadados": {}, "alertas": []}
    agent = FakeAgent(stdout=json.dumps(payload))
    generator = ContentGenerator(agent, "opencode")
    data = GenerationPromptInput(
        tema="x",
        plataforma="LinkedIn",
        objetivo_do_post="autoridade",
        tipo_de_post="post",
        briefing_autoral={},
    )
    resultado = generator.generate(data)
    assert resultado.conteudo == "ok"
    assert agent.calls[0]["json_output"] is True


def test_slidemark_validator_aceita_documento_valido() -> None:
    assert validate_slidemark_document(_slidemark_valido()) == []


def test_content_generator_parseia_slidemark_e_alerta_invalidos() -> None:
    slidemark = _slidemark_valido()
    slidemark["slides"][1]["code"] = "\n".join(f"linha {i}" for i in range(15))
    slidemark["slides"][1]["type"] = "content.code"
    slidemark["slides"][1]["language"] = "python"
    payload = {
        "slidemark": slidemark,
        "conteudo": "",
        "metadados": {"tipoDePost": "short_carousel"},
        "alertas": [],
    }
    agent = FakeAgent(stdout=json.dumps(payload))
    generator = ContentGenerator(agent, "codex")
    data = GenerationPromptInput(
        tema="adapter",
        plataforma="LinkedIn",
        objetivo_do_post="ensinar",
        tipo_de_post="short_carousel",
        briefing_autoral={},
    )

    resultado = generator.generate(data)

    assert resultado.slidemark is not None
    assert validate_slidemark_document(resultado.slidemark) == []
    assert "highlight" not in resultado.slidemark["slides"][1]
    assert resultado.slides[0].titulo == "Adapter sem mistério"
    assert resultado.conteudo.startswith("## Slide 1")
    assert resultado.metadados["slideMarkVersion"] == "1.0.0"
    assert resultado.alertas == []


def test_segmentar_slidemark_usa_id_type_e_texto_do_slide() -> None:
    segmentos = segmentar_slidemark(_slidemark_valido())

    assert segmentos[0]["id"] == "adapter-cover"
    assert segmentos[0]["slideType"] == "cover.hero"
    assert segmentos[0]["papelInterno"] == "capa"
    assert segmentos[1]["slideType"] == "content.text"
    assert "Seu código espera" in segmentos[1]["texto"]
    assert segmentos[-1]["papelInterno"] == "conclusao"
