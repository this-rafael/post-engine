"""Progressao persistida das fases principais da sessao."""
from __future__ import annotations

from typing import Any


PHASE_ENTRADA = "entrada_inicial"
PHASE_ENTREVISTA = "entrevista_gateway"
PHASE_BRIEFING = "briefing_autoral"
PHASE_PROMPT = "prompt_renderizado"
PHASE_EXECUCAO = "execucao_llm"
PHASE_SEGMENTACAO = "segmentacao_editavel"
PHASE_AVALIACAO = "avaliacao_conteudo"
PHASE_EXPORTACAO = "exportacao_final"

PHASE_ORDER: tuple[str, ...] = (
    PHASE_ENTRADA,
    PHASE_ENTREVISTA,
    PHASE_BRIEFING,
    PHASE_PROMPT,
    PHASE_EXECUCAO,
    PHASE_SEGMENTACAO,
    PHASE_AVALIACAO,
    PHASE_EXPORTACAO,
)

PHASE_TO_STAGE: dict[str, str] = {
    PHASE_ENTRADA: "entry",
    PHASE_ENTREVISTA: "interview",
    PHASE_BRIEFING: "briefing",
    PHASE_PROMPT: "prompt",
    PHASE_EXECUCAO: "execution",
    PHASE_SEGMENTACAO: "segmentation",
    PHASE_AVALIACAO: "evaluation",
    PHASE_EXPORTACAO: "export",
}


def phase_index(phase: object) -> int:
    try:
        return PHASE_ORDER.index(phase)  # type: ignore[arg-type]
    except ValueError:
        return -1


def released_phases(state: Any) -> list[str]:
    """Return a contiguous, recoverable phase prefix for ``state``.

    Older session files did not keep an unlock list and could have their
    ``current_phase`` overwritten by navigation.  Durable artifacts therefore
    also count as proof that their phase has already been reached.
    """

    raw_released = getattr(state, "fases_liberadas", [])
    if not isinstance(raw_released, list):
        raw_released = []
    highest = max(
        (phase_index(item) for item in raw_released),
        default=0,
    )
    highest = max(highest, phase_index(getattr(state, "current_phase", "")))

    if isinstance(getattr(state, "interview_state", None), dict):
        highest = max(highest, phase_index(PHASE_ENTREVISTA))
    if isinstance(getattr(state, "briefing_autoral", None), dict) and getattr(
        state, "briefing_autoral", None
    ):
        highest = max(highest, phase_index(PHASE_BRIEFING))
    if str(getattr(state, "prompt_renderizado", "")).strip():
        highest = max(highest, phase_index(PHASE_PROMPT))
    if getattr(state, "is_running", False) or str(getattr(state, "stdout", "")).strip():
        highest = max(highest, phase_index(PHASE_EXECUCAO))
    if str(getattr(state, "conteudo_gerado", "")).strip():
        highest = max(highest, phase_index(PHASE_SEGMENTACAO))
    if isinstance(getattr(state, "segmentos", None), list) and getattr(state, "segmentos", None):
        highest = max(highest, phase_index(PHASE_AVALIACAO))
    if isinstance(getattr(state, "avaliacao_post", None), dict) and getattr(
        state, "avaliacao_post", None
    ):
        highest = max(highest, phase_index(PHASE_EXPORTACAO))

    return list(PHASE_ORDER[: max(0, highest) + 1])


def reconcile_phase_progress(state: Any, *, resume_at_latest: bool = False) -> list[str]:
    """Persist the unlock list and optionally resume on its newest phase."""

    released = released_phases(state)
    state.fases_liberadas = released
    latest = released[-1]
    state.current_phase = latest

    if resume_at_latest:
        current_stage = str(getattr(state, "current_stage", "") or "")
        current_stage_phase = next(
            (phase for phase, stage in PHASE_TO_STAGE.items() if stage == current_stage),
            None,
        )
        if current_stage_phase is not None and phase_index(current_stage_phase) < phase_index(latest):
            state.current_stage = PHASE_TO_STAGE[latest]
    return released


def phase_progress(state: Any, labels: dict[str, str]) -> dict[str, Any]:
    released = released_phases(state)
    latest = released[-1]
    return {
        "released": released,
        "pending": [phase for phase in PHASE_ORDER if phase not in released],
        "latest_released": latest,
        "phases": [
            {
                "id": phase,
                "label": labels.get(phase, phase),
                "stage": PHASE_TO_STAGE[phase],
                "status": "active" if phase == latest else "released" if phase in released else "pending",
            }
            for phase in PHASE_ORDER
        ],
    }


__all__ = [
    "PHASE_ORDER",
    "PHASE_TO_STAGE",
    "phase_index",
    "phase_progress",
    "reconcile_phase_progress",
    "released_phases",
]
