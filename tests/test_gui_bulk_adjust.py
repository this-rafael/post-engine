"""Testes das acoes de ajuste em lote da GUI."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from gui.server import GuiController


@pytest.fixture()
def controller(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> GuiController:
    config_path = tmp_path / "agent-config.yml"
    session_path = tmp_path / "session.json"
    monkeypatch.setattr("content_engine.llm_config.CONFIG_FILE", config_path)
    monkeypatch.setattr("content_engine.llm_config.DATA_DIR", tmp_path)
    return GuiController(session_path=session_path)


def _seed_segments(controller: GuiController) -> None:
    controller.app.state.segmentos = [
        {"id": "seg-1", "ordem": 1, "texto": "Primeiro segmento.", "papel_interno": "abertura"},
        {"id": "seg-2", "ordem": 2, "texto": "Segundo segmento.", "papel_interno": "desenvolvimento"},
        {"id": "seg-3", "ordem": 3, "texto": "Terceiro segmento.", "papel_interno": "fechamento"},
    ]
    controller.app.state.avaliacao_post = {
        "score": {"total": 6},
        "trechos_fracos": [
            {
                "trecho": 2,
                "problema": "Pouco concreto",
                "severidade": "media",
                "motivo": "Adicionar exemplo",
            },
            {
                "trecho": 3,
                "problema": "Fechamento fraco",
                "severidade": "alta",
                "motivo": "Reforcar tese",
            },
        ],
    }


def test_rewrite_segments_bulk_populates_snapshot(
    controller: GuiController,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_segments(controller)

    payload = {
        "segmentosReescritos": [
            {"id": "seg-2", "ordem": 2, "segmentoReescrito": "Segundo reescrito."},
            {"id": "seg-3", "ordem": 3, "segmentoReescrito": "Terceiro reescrito."},
        ]
    }

    class FakeAgent:
        def run(self, *args: object, **kwargs: object) -> object:
            from content_engine.schemas import AgentResult

            return AgentResult(
                tool="codex",
                command=["codex"],
                returncode=0,
                stdout=json.dumps(payload),
                stderr="",
            )

    monkeypatch.setattr(controller.app, "_agent_factory", lambda: FakeAgent())

    result = controller.action(
        "rewrite_segments_bulk",
        {
            "ajustes": [
                {"index": 1, "pedido": "Torne mais concreto."},
                {"index": 2, "pedido": "Reforce a tese."},
            ],
        },
    )

    reescritos = result["derived"]["segmentos_reescritos"]
    assert reescritos["1"] == "Segundo reescrito."
    assert reescritos["2"] == "Terceiro reescrito."


def test_apply_segments_bulk_updates_segment_text(
    controller: GuiController,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_segments(controller)
    controller.app._segmentos_reescritos = {1: "Segundo reescrito.", 2: "Terceiro reescrito."}

    controller.action(
        "apply_segments_bulk",
        {"indices": [1, 2]},
    )

    assert controller.app.state.segmentos[1]["texto"] == "Segundo reescrito."
    assert controller.app.state.segmentos[2]["texto"] == "Terceiro reescrito."
    assert controller.app._segmentos_reescritos == {}


def test_apply_segments_bulk_accepts_textos_payload(controller: GuiController) -> None:
    _seed_segments(controller)

    controller.action(
        "apply_segments_bulk",
        {"textos": {"1": "Novo segundo."}},
    )

    assert controller.app.state.segmentos[1]["texto"] == "Novo segundo."


def test_cancel_bulk_adjust_clears_pending(controller: GuiController) -> None:
    _seed_segments(controller)
    controller.app._segmentos_reescritos = {1: "Pendente"}

    controller.action("cancel_bulk_adjust")

    assert controller.app._segmentos_reescritos == {}
