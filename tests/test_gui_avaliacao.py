"""Testes do snapshot de avaliacao da GUI."""
from __future__ import annotations

from pathlib import Path

import pytest

from gui.server import GuiController
from content_engine.session_controller import SCORE_AVALIACAO_ASPECTOS


@pytest.fixture()
def controller(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> GuiController:
    config_path = tmp_path / "agent-config.yml"
    session_path = tmp_path / "session.json"
    monkeypatch.setattr("content_engine.llm_config.CONFIG_FILE", config_path)
    monkeypatch.setattr("content_engine.llm_config.DATA_DIR", tmp_path)
    return GuiController(session_path=session_path)


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
        "veredito": "Publicavel com ajustes menores.",
        "pontos_fortes": ["clareza na tese"],
        "pontos_fracos": ["slide 4 redundante"],
        "trechos_fracos": [
            {
                "trecho": 4,
                "problema": "Redundante",
                "severidade": "media",
                "motivo": "Repete conclusao",
            }
        ],
        "redundancias": ["slides 2 e 3"],
        "falhas_tecnicas": ["metrica ausente"],
        "sugestoes_melhoria": ["adicionar exemplo concreto"],
        "sugestoes": ["adicionar exemplo concreto"],
    }


def test_snapshot_post_scores_usa_criterios_novos(controller: GuiController) -> None:
    controller.app.state.avaliacao_post = _avaliacao_payload()
    snapshot = controller.snapshot()
    post_scores = snapshot["derived"]["post_scores"]
    assert set(post_scores.keys()) == set(SCORE_AVALIACAO_ASPECTOS)
    assert "Tese: 8" in post_scores["tese"]
    assert "Total:" in post_scores["total"]


def test_snapshot_avaliacao_ui_completo(controller: GuiController) -> None:
    controller.app.state.avaliacao_post = _avaliacao_payload()
    ui = controller.snapshot()["derived"]["avaliacao_ui"]
    assert ui["valida"] is True
    assert set(ui["scores"].keys()) == set(SCORE_AVALIACAO_ASPECTOS)
    assert ui["veredito"] == "Publicavel com ajustes menores."
    assert "- clareza na tese" in ui["pontos_fortes"]
    assert "- slide 4 redundante" in ui["pontos_fracos"]
    assert "- adicionar exemplo concreto" in ui["sugestoes"]
    assert "- slides 2 e 3" in ui["redundancias"]
    assert "- metrica ausente" in ui["falhas_tecnicas"]
    assert ui["trechos_fracos"] == [
        {
            "trecho": 4,
            "problema": "Redundante",
            "severidade": "media",
            "motivo": "Repete conclusao",
        }
    ]


def test_snapshot_avaliacao_ui_invalida_sem_score(controller: GuiController) -> None:
    controller.app.state.avaliacao_post = {}
    ui = controller.snapshot()["derived"]["avaliacao_ui"]
    assert ui["valida"] is False
    assert ui["veredito"] == ""
    assert ui["trechos_fracos"] == []


def test_snapshot_avaliacao_ui_retrocompat_score_legado(controller: GuiController) -> None:
    controller.app.state.avaliacao_post = {"score": {"experiencia": 50}}
    ui = controller.snapshot()["derived"]["avaliacao_ui"]
    assert ui["valida"] is True


def test_reset_context_clears_session(controller: GuiController) -> None:
    controller.app.state.tema = "tema de teste"
    controller.app.state.plataforma = "linkedin"
    controller.app.state.objetivo_do_post = "objetivo"
    controller.app.state.personalidade = "autor"
    controller.app.state.briefing_autoral = {"tese": "teste"}
    controller.app.state.conteudo_gerado = "conteudo"
    controller.app.state.current_phase = "briefing"
    controller.app.state.fase_atual = "briefing"

    result = controller.action("reset_context")
    state = result["state"]

    assert state["tema"] == ""
    assert state["plataforma"] == ""
    assert state["objetivo_do_post"] == ""
    assert state["personalidade"] == ""
    assert state["briefing_autoral"] == {}
    assert state["conteudo_gerado"] == ""
    assert state["current_phase"] == "entrada_inicial"
    assert state["fase_atual"] == "entrada"
    assert "reiniciado" in state["status_operacional"].lower()
