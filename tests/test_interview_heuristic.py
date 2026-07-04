from __future__ import annotations

from content_engine.interview.extraction import append_answer, append_extraction, extract_signals
from content_engine.interview.heuristic import assess_dimensions
from content_engine.interview.schemas import SelectedQuestion, criar_estado_inicial


def test_FR_007_deterministic_score_is_explainable() -> None:
    state = criar_estado_inicial("sistemas distribuidos")
    answer = append_answer(
        state,
        SelectedQuestion(question="Que experiencia concreta voce teve?", candidate_id="q-1"),
        "Eu implementei o fluxo em 2024. O mecanismo reduziu o erro em tres servicos.",
    )
    append_extraction(state, extract_signals(answer))
    assessment = assess_dimensions(state)

    assert assessment.evidence_count > 0
    assert assessment.global_score > 0
    assert assessment.dimensions
    for dimension in assessment.dimensions.values():
        assert dimension.rules_triggered
        assert set(dimension.evidence_ids) <= {item.id for item in state.evidence_ledger}
