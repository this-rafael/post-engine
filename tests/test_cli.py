"""Testes do CLI sem TUI."""
from __future__ import annotations

import pytest

from content_engine import __main__ as ce_main


def test_cli_without_gui_exits() -> None:
    with pytest.raises(SystemExit, match="TUI removida"):
        ce_main.main([])


def test_cli_gui_invokes_server(monkeypatch) -> None:
    called: list[dict[str, object]] = []

    def fake_run(**kwargs: object) -> None:
        called.append(kwargs)

    import gui

    monkeypatch.setattr(gui, "run_gui_server", fake_run)
    ce_main.main(["--gui", "--gui-host", "127.0.0.1", "--gui-port", "9999"])
    assert called == [{"host": "127.0.0.1", "port": 9999}]
