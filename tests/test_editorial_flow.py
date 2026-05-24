"""Testes do estado editorial compartilhado."""
from __future__ import annotations

import pytest

from content_engine.editorial_flow import derive_editorial_status
from content_engine.persistence import _dict_to_state, _state_to_dict
from content_engine.schemas import TuiSessionState
from gui.server import GuiController


def test_pre_v4_session_is_rejected_before_editorial_flow_is_opened() -> None:
    payload = {
        "schema_version": "2.0",
        "session_id": "s1",
        "current_phase": "entrada_inicial",
        "tema": "Tema",
    }
    with pytest.raises(ValueError, match="schema_version"):
        _dict_to_state(payload)


def test_editorial_flow_round_trip() -> None:
    state = TuiSessionState(session_id="s2")
    state.editorial_flow = {
        "schema_version": "1.0",
        "briefing_fingerprint": "abc",
        "storyboard": {"version": 1, "status": "available", "blocks": []},
    }
    restored = _dict_to_state(_state_to_dict(state))
    assert restored.editorial_flow["briefing_fingerprint"] == "abc"


def test_derive_editorial_status_defaults() -> None:
    status = derive_editorial_status({})
    assert status["storyboard_available"] is False
    assert status["selection_complete"] is False


def test_gui_snapshot_includes_editorial_derived(tmp_path) -> None:
    controller = GuiController(session_path=tmp_path / "session.json")
    snap = controller.snapshot()
    assert "editorial" in snap["derived"]
    assert isinstance(snap["state"]["editorial_flow"], dict)
