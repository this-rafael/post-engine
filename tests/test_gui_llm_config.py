"""Testes dos endpoints de configuracao LLM da GUI."""
from __future__ import annotations

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


def test_llm_config_snapshot(controller: GuiController) -> None:
    payload = controller.llm_config_snapshot()
    assert "operations" in payload
    assert payload["operations"]["interview_questions"]["provider"] == "opencode"
    assert "content_generate" not in payload["operations"]
    assert "post_generate" in payload["operations"]
    assert "interview_validate" in payload["operations"]
    assert "storyboard_generate" in payload["operations"]
    assert "block_approaches_generate" in payload["operations"]
    assert "block_draft_generate" in payload["operations"]
    assert "editorial_compose" in payload["operations"]
    assert payload["operation_labels"]["post_generate"] == "Geração de post"
    assert payload["operation_labels"]["interview_validate"] == "Avaliação da qualidade das perguntas da entrevista"
    assert "provider_status" in payload


def test_update_llm_config(controller: GuiController) -> None:
    updated = controller.update_llm_config(
        {
            "operations": {
                "interview_questions": {"provider": "codex", "model": "gpt-5.4-mini"},
                "storyboard_generate": {
                    "provider": "opencode",
                    "model": "qwen-3.6-plus",
                    "agent": "storyboarder",
                },
                "editorial_compose": {
                    "provider": "cursor",
                    "model": "auto",
                },
            }
        }
    )
    assert updated["operations"]["interview_questions"]["provider"] == "codex"
    assert updated["operations"]["interview_questions"]["model"] == "gpt-5.4-mini"
    assert updated["operations"]["storyboard_generate"]["provider"] == "opencode"
    assert updated["operations"]["storyboard_generate"]["agent"] == "storyboarder"
    assert updated["operations"]["editorial_compose"]["provider"] == "cursor"
    assert updated["operations"]["editorial_compose"]["model"] == "auto"


def test_session_snapshot_includes_effective_config(controller: GuiController) -> None:
    snapshot = controller.snapshot()
    effective = snapshot["derived"]["effective_llm_config"]
    assert "effective_llm_config" in snapshot["derived"]
    assert effective["interview_evaluate"]["provider"] == "cursor"
    assert effective["interview_validate"]["provider"] == "opencode"
    assert "post_generate" in effective
    assert "content_generate" not in effective
    assert "storyboard_generate" in effective
    assert "editorial_compose" in effective
