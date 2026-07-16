"""Unica camada permitida para resolver prompts operacionais."""
from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .conditions import applies
from .models import PromptExecutionReference
from .renderer import PromptRenderError, render
from .repository import PromptRegistryError, PromptRegistryRepository


class PromptResolutionError(PromptRegistryError):
    pass


@dataclass(frozen=True)
class PromptResolution:
    execution_id: str
    operation: str
    composition_id: int
    composition_version: int
    artifact_versions: tuple[dict[str, Any], ...]
    template_content: str
    resolved_content: str
    template_hash: str
    resolved_hash: str
    variables_used: tuple[str, ...]
    diagnostics: tuple[str, ...]
    resolution_source: str
    rollout_mode: str
    composition_items: tuple[dict[str, Any], ...] = ()
    slots: tuple[str, ...] = ()


def _hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _condition_from_item(item: Any) -> dict[str, Any] | None:
    if not item.condition_operator:
        return None
    return {
        "type": item.condition_type,
        "field": item.condition_field,
        "operator": item.condition_operator,
        "value": item.condition_value,
    }


class PromptResolver:
    def __init__(self, path: str | Path | None = None, *, auto_initialize: bool = True) -> None:
        self.path = path
        self.auto_initialize = auto_initialize

    def resolve(
        self, operation: str, context: dict[str, Any] | None = None, *,
        provider: str | None = None, model: str | None = None, execution_id: str | None = None,
        record_execution: bool = True,
        artifact_version_overrides: dict[str, int] | None = None,
    ) -> PromptResolution:
        if self.auto_initialize:
            # Importacao e uma migration idempotente. Apos o primeiro bootstrap a
            # chamada abaixo nao le fontes legadas; apenas consulta SQLite.
            from .importer import ensure_registry_initialized
            ensure_registry_initialized(self.path)
        supplied = dict(context or {})
        try:
            with PromptRegistryRepository(self.path) as repository:
                operation_record = repository.get_operation(operation)
                if operation_record is None:
                    raise PromptResolutionError(f"Operacao nao registrada: {operation}")
                composition = repository.get_active_composition(operation)
                if composition is None:
                    raise PromptResolutionError(f"Operacao sem composicao ativa: {operation}")
                parts: list[str] = []
                slots: dict[str, str] = {}
                artifacts: list[dict[str, Any]] = []
                item_results: list[dict[str, Any]] = []
                diagnostics: list[str] = []
                for item in repository.composition_items(composition.id):
                    condition = _condition_from_item(item)
                    applied = applies(condition, supplied)
                    item_result = {
                        "position": item.position, "artifact": None, "required": item.required,
                        "separator": item.separator, "condition": condition,
                        "runtime_slot": item.runtime_slot, "applied": applied,
                    }
                    if not applied:
                        item_results.append(item_result)
                        continue
                    artifact, version = repository.resolve_item_artifact(item)
                    if artifact_version_overrides and artifact.key in artifact_version_overrides:
                        version = repository.get_version(artifact.key, artifact_version_overrides[artifact.key])
                        if version is None:
                            raise PromptResolutionError(f"Versao de preview inexistente: {artifact.key}")
                    item_result["artifact"] = artifact.key
                    item_result["version"] = version.version if version else None
                    if artifact.status in {"LEGACY", "ORPHAN", "REFERENCE_ONLY"}:
                        raise PromptResolutionError(f"Artefato nao operacional usado: {artifact.key}")
                    if version is None:
                        if item.required:
                            raise PromptResolutionError(f"Artefato sem versao ativa: {artifact.key}")
                        diagnostics.append(f"Artefato opcional sem versao ativa: {artifact.key}")
                        item_results.append(item_result)
                        continue
                    artifacts.append({"key": artifact.key, "version": version.version, "hash": version.content_hash})
                    if item.runtime_slot:
                        slots[item.runtime_slot] = version.content
                        item_results.append(item_result)
                        continue
                    if parts:
                        parts.append(item.separator)
                    parts.append(version.content)
                    item_results.append(item_result)
                if not parts:
                    raise PromptResolutionError(f"Composicao sem artefatos aplicaveis: {operation}")
                template = "".join(parts)
                full_context = {**supplied, **slots}
                execution = execution_id or uuid.uuid4().hex
                try:
                    rendered = render(template, full_context)
                except PromptRenderError as exc:
                    if record_execution:
                        repository.record_execution(PromptExecutionReference(
                            execution_id=execution, operation_key=operation,
                            composition_id=composition.id, composition_version=composition.version,
                            artifact_versions=tuple(artifacts), template_hash=_hash(template),
                            resolved_hash="", provider=provider, model=model,
                            resolved_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                            resolution_source="registry", error=str(exc),
                            rollout_mode=operation_record.rollout_mode,
                            placeholders=(),
                        ))
                    raise PromptResolutionError(str(exc)) from exc
                resolved = PromptResolution(
                    execution_id=execution, operation=operation, composition_id=composition.id,
                    composition_version=composition.version, artifact_versions=tuple(artifacts),
                    template_content=template, resolved_content=rendered.content,
                    template_hash=_hash(template), resolved_hash=_hash(rendered.content),
                    variables_used=rendered.variables_used, diagnostics=tuple([*diagnostics, *rendered.diagnostics]),
                    resolution_source="registry", rollout_mode=operation_record.rollout_mode,
                    composition_items=tuple(item_results), slots=tuple(sorted(slots)),
                )
                if record_execution:
                    repository.record_execution(PromptExecutionReference(
                        execution_id=resolved.execution_id, operation_key=operation,
                        composition_id=composition.id, composition_version=composition.version,
                        artifact_versions=resolved.artifact_versions, template_hash=resolved.template_hash,
                        resolved_hash=resolved.resolved_hash, provider=provider, model=model,
                        resolved_at=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                        resolution_source="registry", rollout_mode=operation_record.rollout_mode,
                        placeholders=resolved.variables_used,
                    ))
                return resolved
        except PromptRegistryError:
            raise
        except Exception as exc:  # pragma: no cover - defensive database boundary
            raise PromptResolutionError(f"Falha ao resolver {operation}: {exc}") from exc


def resolve_prompt(
    operation: str, context: dict[str, Any] | None = None, *, path: str | Path | None = None,
    provider: str | None = None, model: str | None = None,
) -> PromptResolution:
    return PromptResolver(path).resolve(operation, context, provider=provider, model=model)


__all__ = ["PromptResolution", "PromptResolutionError", "PromptResolver", "resolve_prompt"]
