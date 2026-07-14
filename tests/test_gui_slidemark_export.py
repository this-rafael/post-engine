"""Testes do export SlideMark na GUI."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from content_engine.schemas import AgentResult
from gui.server import GuiController
from tests.llm_fakes import AgentFakeRunMixin


class FakeAgent(AgentFakeRunMixin):
    def __init__(self, stdout: str) -> None:
        self.stdout = stdout
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
            returncode=0,
            stdout=self.stdout,
            stderr="",
            events=None,
            error=None,
        )

    def run_opencode(self, prompt: str, **kwargs: Any) -> AgentResult:
        self.calls.append({"prompt": prompt, "json_output": kwargs.get("json_output", False)})
        return AgentResult(
            tool="opencode",
            command=["opencode", "run"],
            returncode=0,
            stdout=self.stdout,
            stderr="",
            events=None,
            error=None,
        )


def _slidemark_valido() -> dict[str, Any]:
    return {
        "version": "1.0.0",
        "document": {
            "title": "Hooks no React",
            "description": "Carrossel sobre hooks",
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
            "fileName": "hooks-react",
            "formats": ["png", "zip", "pdf"],
            "pdf": {"pageMode": "square", "source": "rendered-images"},
        },
        "slides": [
            {
                "id": "cover",
                "type": "cover.hero",
                "variant": "alpha",
                "title": "Hooks sem dor",
            },
            {
                "id": "body",
                "type": "content.text",
                "variant": "alpha",
                "title": "Por que importa",
                "body": ["Estado local precisa de regras claras."],
            },
            {
                "id": "cta",
                "type": "closing.cta",
                "variant": "alpha",
                "title": "Proximo passo",
                "cta": "Comente sua duvida",
            },
        ],
    }


def _avaliacao_payload() -> dict[str, object]:
    return {
        "score": {
            "tese": 8,
            "progressao": 7,
            "concretude": 6,
            "precisao_tecnica": 7,
            "retencao": 6,
            "autoridade": 7,
            "autoria": 8,
            "slidemark": 9,
            "revisao_textual": 8,
            "total": 7.5,
        },
        "veredito": "Publicavel.",
    }


@pytest.fixture()
def controller(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> GuiController:
    config_path = tmp_path / "agent-config.yml"
    session_path = tmp_path / "session.json"
    monkeypatch.setattr("content_engine.llm_config.CONFIG_FILE", config_path)
    monkeypatch.setattr("content_engine.llm_config.DATA_DIR", tmp_path)
    return GuiController(session_path=session_path)


def test_snapshot_is_trilha_visual(controller: GuiController) -> None:
    controller.app.state.tipo_de_post = "short_carousel"
    derived = controller.snapshot()["derived"]
    assert derived["is_trilha_visual"] is True

    controller.app.state.tipo_de_post = "post"
    derived = controller.snapshot()["derived"]
    assert derived["is_trilha_visual"] is False


def test_export_slidemark_atualiza_estado_e_grava_arquivo(
    controller: GuiController,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = FakeAgent(stdout=json.dumps({"slidemark": _slidemark_valido()}))
    controller.app._agent_factory = lambda: fake  # type: ignore[method-assign]
    monkeypatch.setattr(
        "content_engine.exporter.EXPORTS_DIR",
        tmp_path / "exports",
    )

    controller.app.state.tipo_de_post = "short_carousel"
    controller.app.state.tema = "Hooks React"
    controller.app.state.plataforma = "linkedin"
    controller.app.state.conteudo_gerado = "conteudo base"
    controller.app.state.segmentos = [
        {
            "id": "s1",
            "ordem": 1,
            "texto": "Capa editada",
            "papel_interno": "capa",
        },
        {
            "id": "s2",
            "ordem": 2,
            "texto": "Corpo editado",
            "papel_interno": "explicacao",
        },
    ]
    controller.app.state.avaliacao_post = _avaliacao_payload()

    destino = tmp_path / "saida.md"
    snapshot = controller.action(
        "export_slidemark",
        {"path": str(destino)},
    )

    slidemark = snapshot["state"]["conteudo_json"]["slidemark"]
    assert slidemark["document"]["title"] == "Hooks no React"
    assert snapshot["derived"]["has_slidemark"] is True
    assert destino.exists()
    json_path = destino.with_suffix(".slidemark.json")
    assert json_path.exists()
    assert json.loads(json_path.read_text(encoding="utf-8")) == slidemark
    assert fake.calls
    assert "Capa editada" in fake.calls[0]["prompt"]


def test_export_slidemark_rejeita_post(
    controller: GuiController,
) -> None:
    controller.app.state.tipo_de_post = "post"
    controller.app.state.conteudo_gerado = "texto"
    controller.app.state.segmentos = [
        {"id": "s1", "ordem": 1, "texto": "paragrafo", "papel_interno": "paragrafo"},
    ]
    controller.app.state.avaliacao_post = _avaliacao_payload()

    snapshot = controller.action("export_slidemark", {})
    assert "carrossel curto" in snapshot["state"]["error"]


def test_export_slidemark_nao_grava_documento_rejeitado(
    controller: GuiController,
    tmp_path: Path,
) -> None:
    documento = _slidemark_valido()
    documento["slides"] = documento["slides"][:1]
    fake = FakeAgent(stdout=json.dumps({"slidemark": documento}))
    controller.app._agent_factory = lambda: fake  # type: ignore[method-assign]
    controller.app.state.tipo_de_post = "short_carousel"
    controller.app.state.tema = "Hooks React"
    controller.app.state.plataforma = "linkedin"
    controller.app.state.conteudo_gerado = "conteudo base"
    controller.app.state.avaliacao_post = _avaliacao_payload()

    destino = tmp_path / "rejeitado.md"
    snapshot = controller.action("export_slidemark", {"path": str(destino)})

    assert "ultimo slide deve ser closing.cta" in snapshot["state"]["error"]
    assert not destino.exists()
    assert not destino.with_suffix(".slidemark.json").exists()
