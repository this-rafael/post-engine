from __future__ import annotations

import json

import pytest

from content_engine.persistence import carregar_sessao, carregar_sessao_de_payload, salvar_sessao
from content_engine.schemas import TuiSessionState


def test_v4_interview_state_round_trip(tmp_path) -> None:
    state = TuiSessionState(
        tema="decisoes de arquitetura",
        interview_state={"schema_version": "4.0", "progress_state": "EXPLORANDO"},
        evidence_ledger=[{"id": "ev-1", "text": "trecho literal"}],
        gateway_result={"approved": False, "gateway_type": "REPROVADO"},
    )
    path = tmp_path / "v4-session.json"
    salvar_sessao(state, path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    restored = carregar_sessao(path)

    assert payload["schema_version"] == "4.0"
    assert restored.interview_state == state.interview_state
    assert restored.evidence_ledger == state.evidence_ledger
    assert restored.gateway_result == state.gateway_result
    assert restored.fases_liberadas == ["entrada_inicial"]


def test_v4_rejects_explicit_older_schema() -> None:
    with pytest.raises(ValueError, match="schema_version"):
        carregar_sessao_de_payload({"schema_version": "3.0", "tema": "antiga"})


def test_v4_missing_schema_is_treated_as_fresh_payload(tmp_path) -> None:
    path = tmp_path / "partial.json"
    path.write_text(json.dumps({"tema": "novo tema"}), encoding="utf-8")
    restored = carregar_sessao(path)
    assert restored.tema == ""
