"""Fachada HTTP-friendly do Prompt Registry para o Observatory."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Iterable

from content_engine.llm_config import resolve_all

from .diagnostics import diagnostics_as_dict
from .importer import ensure_registry_initialized
from .repository import PromptRegistryError, PromptRegistryRepository
from .resolver import PromptResolutionError, PromptResolver


class PromptRegistryApi:
    def __init__(self, path: str | Path | None = None) -> None:
        self.path = path
        ensure_registry_initialized(path)

    @staticmethod
    def _version(version: Any, *, include_content: bool = False) -> dict[str, Any]:
        payload = {
            "version": version.version, "content_hash": version.content_hash,
            "expected_variables": list(version.expected_variables),
            "required_variables": list(version.required_variables), "status": version.status,
            "change_reason": version.change_reason, "created_by": version.created_by,
            "created_at": version.created_at, "activated_at": version.activated_at,
            "supersedes_version_id": version.supersedes_version_id,
        }
        if include_content:
            payload["content"] = version.content
        return payload

    @staticmethod
    def _editability(artifact: Any, active: Any, consumers: list[str]) -> str:
        if artifact.status == "ORPHAN" or not consumers:
            return "ORPHAN"
        if artifact.status == "LEGACY" or artifact.artifact_type == "LEGACY":
            return "LEGACY"
        if artifact.status == "REFERENCE_ONLY" or artifact.artifact_type == "REFERENCE":
            return "REFERENCE_ONLY"
        if active is None:
            return "READ_ONLY"
        if artifact.artifact_type in {"PROMPT_TEMPLATE", "FORMAT_RULES", "POLICY", "OUTPUT_CONTRACT", "SEGMENTATION", "EVALUATION", "RETRY_APPENDIX"}:
            return "EDITABLE_WITH_VALIDATION"
        return "EDITABLE_CONTENT"

    @staticmethod
    def _artifact_consumers(repository: PromptRegistryRepository, artifact_id: int) -> list[str]:
        rows = repository.connection.execute(
            """SELECT DISTINCT o.key FROM prompt_operations o
               JOIN prompt_compositions c ON c.operation_id = o.id
               JOIN prompt_composition_items i ON i.composition_id = c.id
               WHERE i.artifact_id = ? ORDER BY o.phase_order, o.key""", (artifact_id,)
        )
        return [str(row[0]) for row in rows]

    def _artifact_summary(self, repository: PromptRegistryRepository, artifact: Any) -> dict[str, Any]:
        active = repository.active_version(artifact.key)
        consumers = self._artifact_consumers(repository, artifact.id)
        return {
            "key": artifact.key, "title": artifact.title, "description": artifact.description,
            "type": artifact.artifact_type, "status": artifact.status,
            "source_origin": artifact.source_origin, "legacy_source_path": artifact.legacy_source_path,
            "active_version": active.version if active else None,
            "content_hash": active.content_hash if active else None,
            "editability": self._editability(artifact, active, consumers),
            "consumer_operations": consumers,
        }

    def catalog(self) -> dict[str, Any]:
        configs = resolve_all()
        with PromptRegistryRepository(self.path) as repository:
            artifacts_by_id = {artifact.id: self._artifact_summary(repository, artifact) for artifact in repository.list_artifacts()}
            executions = repository.list_execution_references(limit=200)
            latest: dict[str, dict[str, Any]] = {}
            for execution in executions:
                latest.setdefault(str(execution["operation_key"]), execution)
            operations: list[dict[str, Any]] = []
            phases: dict[tuple[int, str], dict[str, Any]] = {}
            for operation in repository.list_operations():
                composition = repository.get_active_composition(operation.key)
                items = repository.composition_items(composition.id) if composition else []
                operation_artifacts = [artifacts_by_id.get(item.artifact_id) for item in items]
                operation_artifacts = [item for item in operation_artifacts if item]
                config = configs.get(operation.key)
                record = {
                    "key": operation.key, "label": operation.label, "description": operation.description,
                    "phase": operation.phase, "phase_group": operation.phase_group, "phase_order": operation.phase_order,
                    "consumer_symbol": operation.consumer_symbol, "is_conditional": operation.is_conditional,
                    "retry_policy": operation.retry_policy, "fallback_policy": operation.fallback_policy,
                    "rollout_mode": operation.rollout_mode, "composition_version": composition.version if composition else None,
                    "artifact_count": len(items), "configured": config.to_dict() if config else None,
                    "last_execution": latest.get(operation.key),
                }
                operations.append(record)
                phase = phases.setdefault((operation.phase_order, operation.phase), {
                    "key": operation.phase, "label": operation.phase, "group": operation.phase_group,
                    "order": operation.phase_order, "operations": [], "artifact_count": 0,
                })
                phase["operations"].append(operation.key)
                phase["artifact_count"] += len(items)
            artifacts = list(artifacts_by_id.values())
            diagnostics = diagnostics_as_dict(self.path)
            return {
                "summary": {
                    "operations": len(operations), "artifacts": len(artifacts),
                    "compositions": sum(1 for op in operations if op["composition_version"] is not None),
                    "diagnostics": len(diagnostics),
                    "last_execution": max((item.get("resolved_at", "") for item in latest.values()), default=None),
                },
                "phases": [phases[key] for key in sorted(phases)], "operations": operations,
                "artifacts": artifacts, "diagnostics": diagnostics,
            }

    def operation(self, operation_key: str) -> dict[str, Any] | None:
        configs = resolve_all()
        with PromptRegistryRepository(self.path) as repository:
            operation = repository.get_operation(operation_key)
            if operation is None:
                return None
            composition = repository.get_active_composition(operation_key)
            items: list[dict[str, Any]] = []
            if composition:
                for item in repository.composition_items(composition.id):
                    artifact, version = repository.resolve_item_artifact(item)
                    items.append({
                        "position": item.position, "artifact": self._artifact_summary(repository, artifact),
                        "artifact_version": version.version if version else None,
                        "condition": {"type": item.condition_type, "field": item.condition_field,
                                      "operator": item.condition_operator, "value": item.condition_value} if item.condition_operator else None,
                        "runtime_slot": item.runtime_slot, "required": item.required, "separator": item.separator,
                    })
            return {
                "key": operation.key, "label": operation.label, "description": operation.description,
                "phase": operation.phase, "phase_group": operation.phase_group, "phase_order": operation.phase_order,
                "consumer_symbol": operation.consumer_symbol, "is_conditional": operation.is_conditional,
                "retry_policy": operation.retry_policy, "fallback_policy": operation.fallback_policy,
                "rollout_mode": operation.rollout_mode, "configured": configs.get(operation.key).to_dict() if operation.key in configs else None,
                "composition": {"id": composition.id, "version": composition.version, "status": composition.status,
                                "description": composition.description, "items": items} if composition else None,
                "executions": repository.list_execution_references(operation_key, limit=30),
                "diagnostics": [d for d in diagnostics_as_dict(self.path) if d.get("operation") == operation_key],
            }

    def artifact(self, artifact_key: str) -> dict[str, Any] | None:
        with PromptRegistryRepository(self.path) as repository:
            artifact = repository.get_artifact(artifact_key)
            if artifact is None:
                return None
            summary = self._artifact_summary(repository, artifact)
            active = repository.active_version(artifact_key)
            references = repository.connection.execute(
                """SELECT o.key AS operation_key, c.version AS composition_version, i.position, i.required,
                   i.separator, i.condition_field, i.condition_operator, i.condition_value, i.runtime_slot
                   FROM prompt_composition_items i JOIN prompt_compositions c ON c.id = i.composition_id
                   JOIN prompt_operations o ON o.id = c.operation_id WHERE i.artifact_id = ?
                   ORDER BY o.phase_order, o.key, c.version, i.position""", (artifact.id,)
            )
            summary.update({
                "active": self._version(active, include_content=True) if active else None,
                "versions": [self._version(version) for version in repository.list_versions(artifact_key)],
                "composition_references": [dict(row) for row in references],
                "impact": {"operation_count": len(summary["consumer_operations"]), "operations": summary["consumer_operations"]},
                "diagnostics": [d for d in diagnostics_as_dict(self.path) if d.get("artifact") == artifact_key],
            })
            return summary

    @staticmethod
    def _sanitize(content: str, context: dict[str, Any]) -> str:
        sanitized = content
        for key, value in sorted(context.items(), key=lambda item: len(str(item[1])), reverse=True):
            text = str(value)
            if text:
                sanitized = sanitized.replace(text, f"<redacted:{key}>")
        return sanitized

    def preview(self, operation: str, context: dict[str, Any], *, provider: str | None = None,
                model: str | None = None, version_overrides: dict[str, int] | None = None) -> dict[str, Any]:
        resolution = PromptResolver(self.path).resolve(
            operation, context, provider=provider, model=model, record_execution=False,
            artifact_version_overrides=version_overrides,
        )
        return {
            "operation": resolution.operation, "composition_id": resolution.composition_id,
            "composition_version": resolution.composition_version, "artifacts": list(resolution.artifact_versions),
            "content": self._sanitize(resolution.resolved_content, context),
            "template": self._sanitize(resolution.template_content, context),
            "variables": list(resolution.variables_used), "template_hash": resolution.template_hash,
            "resolved_hash": resolution.resolved_hash, "diagnostics": list(resolution.diagnostics),
            "items": list(resolution.composition_items), "slots": list(resolution.slots),
        }

    def create_version(self, artifact_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        content = payload.get("content")
        if not isinstance(content, str):
            raise ValueError("content obrigatorio")
        with PromptRegistryRepository(self.path) as repository:
            artifact = repository.get_artifact(artifact_key)
            if artifact is None:
                raise KeyError("artifact_not_found")
            active = repository.active_version(artifact_key)
            editability = self._editability(artifact, active, self._artifact_consumers(repository, artifact.id))
            if editability not in {"EDITABLE_CONTENT", "EDITABLE_WITH_VALIDATION"}:
                raise PromptRegistryError(f"Artefato nao editavel: {editability}")
            if active is None:
                raise PromptRegistryError("Artefato sem versao ativa")
            if repository.content_hash(content) == active.content_hash:
                raise PromptRegistryError("Nenhuma alteracao de conteudo para versionar")
            version = repository.create_version(
                artifact_key, content, expected_variables=active.expected_variables,
                required_variables=active.required_variables, change_reason=str(payload.get("reason", "")),
                created_by=str(payload.get("created_by", "gui-local")), supersedes_version_id=active.id,
                expected_active_version=int(payload.get("expected_active_version", -1)),
                expected_active_hash=str(payload.get("expected_active_hash", "")),
            )
            return self._version(version, include_content=True)

    def activate_version(self, artifact_key: str, version: int, payload: dict[str, Any]) -> dict[str, Any]:
        with PromptRegistryRepository(self.path) as repository:
            target = repository.get_version(artifact_key, version)
            if target is None:
                raise KeyError("version_not_found")
            repository.validate_version_content(target.content, expected_variables=target.expected_variables,
                                                required_variables=target.required_variables)
            activated = repository.activate_version(
                artifact_key, version, expected_active_version=int(payload.get("expected_active_version", -1)),
                expected_active_hash=str(payload.get("expected_active_hash", "")),
            )
            return self._version(activated, include_content=True)

    def rollback(self, artifact_key: str, version: int) -> dict[str, Any]:
        with PromptRegistryRepository(self.path) as repository:
            return self._version(repository.rollback_version(artifact_key, version), include_content=True)

    def diagnostics(self) -> list[dict[str, Any]]:
        return diagnostics_as_dict(self.path)

    def executions(self, operation: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        with PromptRegistryRepository(self.path) as repository:
            return repository.list_execution_references(operation, limit=limit)


def create_wsgi_app(path: str | Path | None = None) -> Callable[..., Iterable[bytes]]:
    """Adaptador mínimo mantido para integrações não-GUI."""
    api = PromptRegistryApi(path)

    def app(environ: dict[str, Any], start_response: Callable[..., Any]) -> list[bytes]:
        method, route = environ.get("REQUEST_METHOD", "GET"), environ.get("PATH_INFO", "")
        status, payload = "200 OK", None
        try:
            if method == "GET" and route == "/api/prompt-registry":
                payload = api.catalog()
            elif method == "GET" and route.startswith("/api/prompt-registry/operations/"):
                payload = api.operation(route.rsplit("/", 1)[-1])
                if payload is None: status, payload = "404 Not Found", {"error": "operation_not_found"}
            else:
                status, payload = "404 Not Found", {"error": "not_found"}
        except Exception as exc:  # pragma: no cover - adapter defensivo
            status, payload = "400 Bad Request", {"error": str(exc)}
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        start_response(status, [("Content-Type", "application/json; charset=utf-8"), ("Content-Length", str(len(encoded)))])
        return [encoded]
    return app


__all__ = ["PromptRegistryApi", "create_wsgi_app"]
