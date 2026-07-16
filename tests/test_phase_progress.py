from __future__ import annotations

from content_engine.interview.schemas import criar_estado_inicial
from content_engine.persistence import carregar_sessao, salvar_sessao
from content_engine.schemas import TuiSessionState
from gui.server import GuiController


def _legacy_interview_state() -> dict[str, object]:
    return criar_estado_inicial(
        "Performance de backend",
        objetivo="Ensinar diagnostico de gargalos.",
        formato="post",
    ).to_dict()


def test_restore_recovers_interview_when_old_navigation_saved_entry(tmp_path) -> None:
    path = tmp_path / "session.json"
    salvar_sessao(
        TuiSessionState(
            current_phase="entrada_inicial",
            current_stage="entry",
            interview_state=_legacy_interview_state(),
        ),
        path,
    )

    controller = GuiController(session_path=path)
    snapshot = controller.snapshot()

    assert snapshot["state"]["current_phase"] == "entrevista_gateway"
    assert snapshot["state"]["current_stage"] == "interview"
    assert snapshot["state"]["fases_liberadas"] == [
        "entrada_inicial",
        "entrevista_gateway",
    ]
    assert snapshot["derived"]["phase_progress"]["released"] == [
        "entrada_inicial",
        "entrevista_gateway",
    ]
    assert snapshot["derived"]["phase_progress"]["pending"][0] == "briefing_autoral"
    assert carregar_sessao(path).fases_liberadas == [
        "entrada_inicial",
        "entrevista_gateway",
    ]


def test_navigation_to_previous_phase_does_not_revoke_unlock(tmp_path) -> None:
    path = tmp_path / "session.json"
    salvar_sessao(
        TuiSessionState(
            current_phase="entrevista_gateway",
            current_stage="interview",
            interview_state=_legacy_interview_state(),
        ),
        path,
    )
    controller = GuiController(session_path=path)

    controller.action("navigate", {"phase": "entrada_inicial"})
    viewed_entry = controller.snapshot()
    assert viewed_entry["state"]["current_stage"] == "entry"
    assert viewed_entry["state"]["current_phase"] == "entrevista_gateway"

    resumed = GuiController(session_path=path).snapshot()
    assert resumed["state"]["current_stage"] == "interview"
    assert resumed["derived"]["phase_progress"]["latest_released"] == "entrevista_gateway"


def test_cannot_navigate_to_phase_that_is_still_pending(tmp_path) -> None:
    controller = GuiController(session_path=tmp_path / "session.json")

    snapshot = controller.action("navigate", {"phase": "entrevista_gateway"})

    assert "aguarda liberacao" in snapshot["state"]["error"]
    assert snapshot["derived"]["phase_progress"]["released"] == ["entrada_inicial"]
