from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from content_engine.interview.extraction import append_answer, append_extraction, extract_signals, signals_have_evidence
from content_engine.interview.schemas import SelectedQuestion, criar_estado_inicial


def test_FR_005_original_answer_immutable() -> None:
    state = criar_estado_inicial("arquitetura orientada a eventos")
    question = SelectedQuestion(question="O que voce viveu sobre esse tema?", candidate_id="q-1")
    original = "  Eu implementei isso em producao.\nAprendi com um incidente.  "
    answer = append_answer(state, question, original)
    result = extract_signals(answer)
    append_extraction(state, result)

    assert answer.original == original
    assert answer.normalized != answer.original
    assert state.answers[0].original == original
    assert all(evidence.text.strip() in original for evidence in state.evidence_ledger)
    with pytest.raises(FrozenInstanceError):
        answer.original = "alterado"  # type: ignore[misc]


def test_FR_006_every_signal_has_evidence() -> None:
    state = criar_estado_inicial("decisoes tecnicas")
    answer = append_answer(
        state,
        SelectedQuestion(question="Que decisao voce tomou?", candidate_id="q-1"),
        "Eu escolhi reduzir o acoplamento porque o incidente afetou tres equipes.",
    )
    result = extract_signals(answer)
    append_extraction(state, result)

    assert state.signals
    assert signals_have_evidence(state.signals, state.evidence_ledger)
    assert all(signal.evidence_ids for signal in state.signals)
