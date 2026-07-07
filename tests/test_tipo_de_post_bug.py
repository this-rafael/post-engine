"""GUI state patches preserve valid content formats."""
from __future__ import annotations

from pathlib import Path

from content_engine.schemas import migrate_tipo_de_post
from gui.server import GuiController


def test_tipo_de_post_preservado_no_state_patch(tmp_path: Path) -> None:
    controller = GuiController(session_path=tmp_path / "session.json")
    controller._apply_state_patch({"tipo_de_post": "long_slide"})
    assert controller.app.state.tipo_de_post == "long_slide"

    controller._apply_state_patch({"tipo_de_post": "short_carousel"})
    assert controller.app.state.tipo_de_post == "short_carousel"


def test_tipo_de_post_snapshot_retorna_valor_correto(tmp_path: Path) -> None:
    controller = GuiController(session_path=tmp_path / "session.json")
    controller._apply_state_patch({"tipo_de_post": "long_slide"})
    assert controller.snapshot()["state"]["tipo_de_post"] == "long_slide"


def test_migrate_tipo_de_post_aceita_somente_formatos_atuais() -> None:
    assert migrate_tipo_de_post("post") == "post"
    assert migrate_tipo_de_post("article") == "article"
    assert migrate_tipo_de_post("short_carousel") == "short_carousel"
    assert migrate_tipo_de_post("long_slide") == "long_slide"
    assert migrate_tipo_de_post("invalido") == "post"
