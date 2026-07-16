"""Stable V4 projection consumed by the GUI and API clients."""
from __future__ import annotations

from typing import Any

from .heuristic import DIMENSION_CATALOG
from .schemas import InterviewState


_UNOBSERVED = {"NAO_OBSERVADA", "NAO_APLICAVEL"}


def _as_state(raw: object) -> InterviewState | None:
    if isinstance(raw, InterviewState):
        return raw
    if not isinstance(raw, dict) or not raw:
        return None
    try:
        return InterviewState.from_dict(raw)
    except (TypeError, ValueError, KeyError):
        return None


def build_interview_ui(raw: object) -> dict[str, Any]:
    """Return one flat dimension model for list, detail and chart views.

    Groups are intentionally absent. A dimension can be rendered in any view
    without allowing an editorial grouping to become a chart axis.
    """
    state = _as_state(raw)
    if state is None:
        return {}

    evidence_by_id = {item.id: item.to_dict() for item in state.evidence_ledger}
    signals_by_dimension: dict[str, list[dict[str, Any]]] = {}
    for signal in state.signals:
        target_dimensions = [
            definition.id
            for definition in DIMENSION_CATALOG
            if signal.type in definition.signal_types
        ]
        for dimension_id in target_dimensions:
            signals_by_dimension.setdefault(dimension_id, []).append(signal.to_dict())
    gaps_by_dimension: dict[str, list[dict[str, Any]]] = {}
    for gap in state.gaps:
        gaps_by_dimension.setdefault(gap.dimension, []).append(gap.to_dict())

    definitions = {item.id: item for item in DIMENSION_CATALOG}

    dimensions: list[dict[str, Any]] = []
    for dimension_id, definition in definitions.items():
        score = state.dimensions.get(dimension_id)
        label = definition.label if definition else dimension_id
        essential = definition.essential if definition else True
        critical = definition.critical if definition else False
        item = score.to_dict() if score else {
            "dimension_id": dimension_id,
            "id": dimension_id,
            "score": 0,
            "state": "NAO_OBSERVADA",
            "evidence_ids": [],
            "rules_triggered": [],
            "rationale": "Nenhuma evidencia observada.",
            "essential": essential,
            "critical": critical,
        }
        evidence_ids = list(item.get("evidence_ids", []))
        dimensions.append(
            {
                "id": dimension_id,
                "label": label,
                "description": f"Dimensao autoral: {label}.",
                "score": int(item.get("score", 0) or 0),
                "state": str(item.get("state", "NAO_OBSERVADA")),
                "covered": str(item.get("state", "NAO_OBSERVADA")) not in _UNOBSERVED,
                "essential": bool(item.get("essential", essential)),
                "critical": bool(item.get("critical", critical)),
                "evidence_ids": evidence_ids,
                "evidence": [evidence_by_id[key] for key in evidence_ids if key in evidence_by_id],
                "signals": signals_by_dimension.get(dimension_id, []),
                "rules_triggered": list(item.get("rules_triggered", [])),
                "rationale": str(item.get("rationale", "")),
                "gaps": gaps_by_dimension.get(dimension_id, []),
            }
        )

    gateway = state.gateway_result.to_dict() if state.gateway_result else None
    covered = sum(1 for item in dimensions if item["covered"])
    applicable = sum(1 for item in dimensions if item["state"] != "NAO_APLICAVEL")
    scores = [item["score"] for item in dimensions if item["state"] != "NAO_APLICAVEL"]
    return {
        "schema_version": state.schema_version,
        "progress_state": state.progress_state,
        "question_count": state.question_count,
        "max_questions": state.max_questions,
        "current_question": state.current_question.to_dict() if state.current_question else None,
        "dimensions": dimensions,
        "chart_series": [
            {"id": item["id"], "label": item["label"], "score": item["score"]}
            for item in dimensions
        ],
        "counter": {
            "covered": covered,
            "observed": covered,
            "total": applicable,
            "denominator": applicable,
            "percent": round(covered / applicable * 100, 1) if applicable else 0.0,
        },
        "evidence": [item.to_dict() for item in state.evidence_ledger],
        "signals": [item.to_dict() for item in state.signals],
        "gaps": [item.to_dict() for item in state.gaps],
        "answers": [item.to_dict() for item in state.answers],
        "history": [
            {
                "question": item.question,
                "answer": item.original,
                "answer_id": item.id,
            }
            for item in state.answers
        ],
        "gateway": gateway,
        "quality": {
            "global_score": gateway.get("global_score", 0) if gateway else round(sum(scores) / len(scores)) if scores else 0,
            "llm_approved": state.llm_assessment.llm_approved if state.llm_assessment else False,
            "heuristic_approved": state.deterministic_assessment.approved if state.deterministic_assessment else False,
        },
        "closure_reason": state.closure_reason,
        "gap_diagnosis": state.gap_diagnosis,
        "extension_batches_completed": state.extension_batches_completed,
        "pending_batch": [item.to_dict() for item in state.pending_batch],
    }


__all__ = ["build_interview_ui"]
