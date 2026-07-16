"""Helpers para anexar metadados sanitizados a resultados de agentes."""
from __future__ import annotations

from typing import Any

from .resolver import PromptResolution


def resolution_metadata(resolution: PromptResolution) -> dict[str, Any]:
    """Retorna somente ids, versoes e hashes; nunca o prompt ou o contexto."""
    return {
        "execution_id": resolution.execution_id,
        "operation": resolution.operation,
        "composition_id": resolution.composition_id,
        "composition_version": resolution.composition_version,
        "artifact_versions": list(resolution.artifact_versions),
        "template_hash": resolution.template_hash,
        "resolved_hash": resolution.resolved_hash,
        "rollout_mode": resolution.rollout_mode,
        "resolution_source": resolution.resolution_source,
        "placeholders": list(resolution.variables_used),
        "diagnostics": list(resolution.diagnostics),
    }


__all__ = ["resolution_metadata"]
