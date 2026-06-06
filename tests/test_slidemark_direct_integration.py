"""Integration coverage against the current SlideMark schema and renderer."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

from content_engine.schemas import AgentResult
from content_engine.slidemark_converter import SlideMarkConverter
from content_engine.slidemark_validator import validate_slidemark_export_document
from tests.llm_fakes import AgentFakeRunMixin


class FakeAgent(AgentFakeRunMixin):
    def __init__(self, stdout: str) -> None:
        self.stdout = stdout
        self.calls: list[dict[str, Any]] = []

    def run_codex(self, prompt: str, **kwargs: Any) -> AgentResult:
        self.calls.append({"prompt": prompt, "json_output": kwargs.get("json_output")})
        return AgentResult(
            tool="codex",
            command=["codex", "exec"],
            returncode=0,
            stdout=self.stdout,
            stderr="",
            events=None,
            error=None,
        )


def _documento_llm_legado() -> dict[str, Any]:
    return {
        "version": "1.0.0",
        "document": {
            "title": "Adapters sem acoplamento",
            "description": "Carrossel tecnico completo sobre fronteiras de integracao.",
            "language": "pt-BR",
        },
        "canvas": {"width": 1080, "height": 1080},
        "theme": {"id": "diffvision-dracula"},
        "author": {"name": "Rafael Pereira", "handle": "@this-rafael-pereira"},
        "settings": {
            "showAuthor": True,
            "showPageNumber": True,
            "showSwipeHint": True,
            "swipeHintText": "Desliza",
        },
        "export": {
            "fileName": "adapters-sem-acoplamento",
            "formats": ["png", "zip", "pdf"],
            "pdf": {"pageMode": "square", "source": "rendered-images"},
        },
        "slides": [
            {
                "id": "cover",
                "type": "cover.hero",
                "variant": "alpha",
                "title": "Adapters protegem o dominio",
            },
            {
                "id": "contexto",
                "type": "content.text",
                "variant": "bravo",
                "title": "O SDK nao e a regra",
                "body": ["O dominio nao deve depender de detalhes do fornecedor."],
                "highlight": "A fronteira certa reduz o custo de trocar dependencias.",
            },
            {
                "id": "codigo",
                "type": "content.code",
                "variant": "alpha",
                "title": "Contrato do dominio",
                "language": "typescript",
                "code": "type Gateway = {\n  charge(input: Charge): Promise<Result>;\n};",
                "highlight": "Campo proibido neste template",
            },
            {
                "id": "bullets",
                "type": "content.bullets",
                "variant": "charlie",
                "title": "Sinais de acoplamento",
                "bullets": [
                    "SDK no caso de uso",
                    {"text": "Teste depende da rede", "description": "O contrato vaza."},
                ],
            },
            {
                "id": "compare",
                "type": "content.compare",
                "variant": "bravo",
                "title": "Antes e depois",
                "left": {"title": "Acoplado", "items": ["Regra conhece o SDK"]},
                "right": {"label": "Isolado", "items": ["Dominio conhece a porta"]},
            },
            {
                "id": "imagem",
                "type": "content.image",
                "variant": "bravo",
                "title": "Fronteira visivel",
                "description": "O adapter fica na borda da aplicacao.",
            },
            {
                "id": "screenshot",
                "type": "content.screenshot",
                "variant": "alpha",
                "title": "Contrato em codigo",
                "frame": "editor",
                "annotations": [
                    {"type": "box", "x": 80, "y": 90, "width": 300, "height": 80, "label": "porta"}
                ],
            },
            {
                "id": "cta",
                "type": "closing.cta",
                "variant": "charlie",
                "title": "Isole integracoes",
                "text": "Trate dependencias externas como detalhes substituiveis.",
                "cta": "Salve para usar no proximo refactor",
                "media": {
                    "type": "image",
                    "src": "@placeholderImage",
                    "alt": "Placeholder sem sugestao nao pode sobreviver",
                },
            },
        ],
    }


def _slidemark_root() -> Path:
    configured = os.environ.get("SLIDEMARK_ROOT")
    root = Path(configured) if configured else Path(__file__).resolve().parents[3] / "Typescript" / "SlideMark"
    if not (root / "src/core/schema/slidemark.schema.ts").is_file():
        pytest.skip("checkout SlideMark nao encontrado; defina SLIDEMARK_ROOT")
    return root


@pytest.mark.slidemark_integration
def test_exportacao_gera_json_importavel_e_renderizavel_no_slidemark() -> None:
    agent = FakeAgent(stdout=json.dumps({"slidemark": _documento_llm_legado()}))
    converter = SlideMarkConverter(agent=agent, tool="codex")
    resultado = converter.converter(
        tema="Adapters",
        plataforma="linkedin",
        tipo_de_post="short_carousel",
        conteudo_final="Conteudo editorial final sobre adapters.",
        sugestoes_imagem=[
            {
                "slideId": "cover",
                "numero": 1,
                "modo": "descricao",
                "descricao": "Diagrama abstrato de uma fronteira entre dominio e SDK",
            },
            {
                "slide": 6,
                "sugestao": "Diagrama de portas e adapters em fundo escuro",
            },
            {
                "slide": 7,
                "modo": "link",
                "sugestao": "Editor exibindo a interface Gateway",
                "url": "https://example.com/gateway-editor.png",
            },
        ],
        segmentos=[
            {
                "id": "cover",
                "ordem": 1,
                "sugestaoImagem": {
                    "modo": "descricao",
                    "descricao": "Diagrama revisado da fronteira do dominio",
                },
            }
        ],
    )

    document = resultado.slidemark
    assert agent.calls and len(agent.calls) == 1
    assert validate_slidemark_export_document(document) == []
    assert document["slides"][0]["variant"] == "bravo"
    assert document["slides"][0]["media"] == {
        "type": "image",
        "src": "@placeholderImage",
        "alt": "Diagrama revisado da fronteira do dominio",
        "fit": "contain",
    }
    assert document["slides"][1]["highlight"] == {
        "text": "A fronteira certa reduz o custo de trocar dependencias."
    }
    assert "highlight" not in document["slides"][2]
    assert "media" not in document["slides"][2]
    assert document["slides"][5]["media"]["src"] == "@placeholderImage"
    assert document["slides"][5]["media"]["alt"] == "Diagrama de portas e adapters em fundo escuro"
    assert document["slides"][6]["media"]["src"] == "https://example.com/gateway-editor.png"
    assert document["slides"][6]["media"]["alt"] == "Editor exibindo a interface Gateway"
    assert "media" not in document["slides"][7]

    root = _slidemark_root()
    runner = root / "node_modules/.bin/tsx"
    if not runner.is_file():
        pytest.skip("tsx do SlideMark nao encontrado")
    bridge = Path(__file__).with_name("fixtures") / "validate_and_render_slidemark.mts"
    completed = subprocess.run(
        [str(runner), str(bridge), str(root)],
        input=json.dumps(document),
        text=True,
        capture_output=True,
        check=False,
        cwd=root,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    rendered = json.loads(completed.stdout)
    assert rendered["success"] is True
    assert [item["type"] for item in rendered["rendered"]] == [
        slide["type"] for slide in document["slides"]
    ]
    assert all(item["htmlLength"] > 0 for item in rendered["rendered"])
