"""Projection of the V4 evidence ledger for content generation."""
from __future__ import annotations

from typing import Any

from .schemas import InterviewState


def build_briefing(state: InterviewState) -> dict[str, Any]:
    return {
        "schema_version": state.schema_version,
        "theme": state.context.tema,
        "objective": state.context.objetivo,
        "format": state.context.formato,
        "personality": state.context.personalidade,
        "progress_state": state.progress_state,
        "answers": [answer.to_dict() for answer in state.answers],
        "evidence": [item.to_dict() for item in state.evidence_ledger],
        "signals": [item.to_dict() for item in state.signals],
        "dimensions": {key: item.to_dict() for key, item in state.dimensions.items()},
        "gateway": state.gateway_result.to_dict() if state.gateway_result else None,
        "gaps": [item.to_dict() for item in state.gaps],
        "closure_reason": state.closure_reason,
    }


__all__ = ["build_briefing"]
