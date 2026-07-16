"""Repositorio transacional do Prompt Registry.

Este modulo concentra SQL; consumidores de LLM usam apenas o resolver.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from .database import connect, transaction
from .migrations import initialize_database
from .models import (
    ArtifactStatus,
    PromptArtifact,
    PromptArtifactVersion,
    PromptComposition,
    PromptCompositionItem,
    PromptExecutionReference,
    PromptOperation,
    RolloutMode,
    VersionStatus,
)
from .renderer import PromptRenderError, extract_placeholders, render, validate_placeholder_syntax


class PromptRegistryError(RuntimeError):
    """Erro de integridade ou de operacao do registry."""


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _json_list(value: str | None) -> tuple[str, ...]:
    try:
        raw = json.loads(value or "[]")
    except json.JSONDecodeError:
        return ()
    return tuple(str(item) for item in raw) if isinstance(raw, list) else ()


class PromptRegistryRepository:
    def __init__(
        self,
        path: str | Path | sqlite3.Connection | None = None,
    ) -> None:
        self._owns_connection = not isinstance(path, sqlite3.Connection)
        if isinstance(path, sqlite3.Connection):
            self.connection = path
        else:
            initialize_database(path)
            self.connection = connect(path)

    def close(self) -> None:
        if self._owns_connection:
            self.connection.close()

    def __enter__(self) -> "PromptRegistryRepository":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @staticmethod
    def content_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _artifact(row: sqlite3.Row) -> PromptArtifact:
        return PromptArtifact(
            id=int(row["id"]), key=str(row["key"]), title=str(row["title"]),
            description=str(row["description"]), artifact_type=str(row["artifact_type"]),
            status=str(row["status"]), source_origin=str(row["source_origin"]),
            legacy_source_path=row["legacy_source_path"], created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    @staticmethod
    def _version(row: sqlite3.Row) -> PromptArtifactVersion:
        return PromptArtifactVersion(
            id=int(row["id"]), artifact_id=int(row["artifact_id"]), version=int(row["version"]),
            content=str(row["content"]), content_hash=str(row["content_hash"]),
            expected_variables=_json_list(row["expected_variables"]),
            required_variables=_json_list(row["required_variables"]), status=str(row["status"]),
            change_reason=str(row["change_reason"]), created_by=str(row["created_by"]),
            created_at=str(row["created_at"]), activated_at=row["activated_at"],
            supersedes_version_id=row["supersedes_version_id"],
        )

    @staticmethod
    def _operation(row: sqlite3.Row) -> PromptOperation:
        return PromptOperation(
            id=int(row["id"]), key=str(row["key"]), label=str(row["label"]),
            description=str(row["description"]), phase=str(row["phase"]),
            phase_group=str(row["phase_group"]), phase_order=int(row["phase_order"]),
            consumer_symbol=str(row["consumer_symbol"]), is_conditional=bool(row["is_conditional"]),
            retry_policy=str(row["retry_policy"]), fallback_policy=str(row["fallback_policy"]),
            rollout_mode=str(row["rollout_mode"]), created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    @staticmethod
    def _composition(row: sqlite3.Row) -> PromptComposition:
        return PromptComposition(
            id=int(row["id"]), operation_id=int(row["operation_id"]), version=int(row["version"]),
            status=str(row["status"]), description=str(row["description"]),
            created_at=str(row["created_at"]), activated_at=row["activated_at"],
            created_by=str(row["created_by"]),
        )

    @staticmethod
    def _item(row: sqlite3.Row) -> PromptCompositionItem:
        raw_value = row["condition_value"]
        try:
            value = json.loads(raw_value) if raw_value is not None else None
        except json.JSONDecodeError:
            value = raw_value
        return PromptCompositionItem(
            id=int(row["id"]), composition_id=int(row["composition_id"]), artifact_id=int(row["artifact_id"]),
            position=int(row["position"]), required=bool(row["required"]), separator=str(row["separator"]),
            condition_type=row["condition_type"], condition_field=row["condition_field"],
            condition_operator=row["condition_operator"], condition_value=value,
            runtime_slot=row["runtime_slot"],
        )

    def get_artifact(self, key: str) -> PromptArtifact | None:
        row = self.connection.execute("SELECT * FROM prompt_artifacts WHERE key = ?", (key,)).fetchone()
        return self._artifact(row) if row else None

    def list_artifacts(self, *, status: str | None = None) -> list[PromptArtifact]:
        query = "SELECT * FROM prompt_artifacts"
        params: tuple[object, ...] = ()
        if status is not None:
            query += " WHERE status = ?"
            params = (status,)
        query += " ORDER BY key"
        return [self._artifact(row) for row in self.connection.execute(query, params)]

    def create_artifact(
        self, *, key: str, title: str, description: str = "", artifact_type: str,
        status: str = ArtifactStatus.DRAFT, source_origin: str = "", legacy_source_path: str | None = None,
    ) -> PromptArtifact:
        existing = self.get_artifact(key)
        if existing is not None:
            return existing
        now = _now()
        with transaction(self.connection):
            cursor = self.connection.execute(
                """INSERT INTO prompt_artifacts
                (key, title, description, artifact_type, status, source_origin, legacy_source_path, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (key, title, description, str(artifact_type), str(status), source_origin, legacy_source_path, now, now),
            )
        return self.get_artifact(key) or self._artifact(self.connection.execute("SELECT * FROM prompt_artifacts WHERE id = ?", (cursor.lastrowid,)).fetchone())

    def update_artifact_status(self, key: str, status: str) -> PromptArtifact:
        artifact = self.get_artifact(key)
        if artifact is None:
            raise PromptRegistryError(f"Artefato inexistente: {key}")
        with transaction(self.connection):
            self.connection.execute("UPDATE prompt_artifacts SET status = ?, updated_at = ? WHERE id = ?", (str(status), _now(), artifact.id))
        return self.get_artifact(key)  # type: ignore[return-value]

    def list_versions(self, artifact_key: str) -> list[PromptArtifactVersion]:
        artifact = self.get_artifact(artifact_key)
        if artifact is None:
            return []
        rows = self.connection.execute(
            "SELECT * FROM prompt_artifact_versions WHERE artifact_id = ? ORDER BY version", (artifact.id,)
        )
        return [self._version(row) for row in rows]

    def active_version(self, artifact_key: str) -> PromptArtifactVersion | None:
        artifact = self.get_artifact(artifact_key)
        if artifact is None:
            return None
        row = self.connection.execute(
            "SELECT * FROM prompt_artifact_versions WHERE artifact_id = ? AND status = 'ACTIVE'", (artifact.id,)
        ).fetchone()
        return self._version(row) if row else None

    def create_version(
        self, artifact_key: str, content: str, *, expected_variables: Iterable[str] = (),
        required_variables: Iterable[str] = (), status: str = VersionStatus.DRAFT,
        change_reason: str = "", created_by: str = "system", supersedes_version_id: int | None = None,
        expected_active_version: int | None = None, expected_active_hash: str | None = None,
        allow_duplicate: bool = False,
    ) -> PromptArtifactVersion:
        artifact = self.get_artifact(artifact_key)
        if artifact is None:
            raise PromptRegistryError(f"Artefato inexistente: {artifact_key}")
        inferred = extract_placeholders(content)
        expected = tuple(dict.fromkeys(expected_variables)) or inferred
        required = tuple(dict.fromkeys(required_variables)) or inferred
        self.validate_version_content(content, expected_variables=expected, required_variables=required)
        digest = self.content_hash(content)
        now = _now()
        with transaction(self.connection):
            active = self.connection.execute(
                "SELECT * FROM prompt_artifact_versions WHERE artifact_id = ? AND status = 'ACTIVE'", (artifact.id,)
            ).fetchone()
            if expected_active_version is not None and (active is None or int(active["version"]) != expected_active_version):
                raise PromptRegistryError("Conflito: versao ativa mudou")
            if expected_active_hash is not None and (active is None or str(active["content_hash"]) != expected_active_hash):
                raise PromptRegistryError("Conflito: hash da versao ativa mudou")
            existing = self.connection.execute(
                "SELECT * FROM prompt_artifact_versions WHERE artifact_id = ? AND content_hash = ? ORDER BY version DESC LIMIT 1",
                (artifact.id, digest),
            ).fetchone()
            if existing is not None and not allow_duplicate:
                return self._version(existing)
            latest = self.connection.execute(
                "SELECT COALESCE(MAX(version), 0) FROM prompt_artifact_versions WHERE artifact_id = ?", (artifact.id,)
            ).fetchone()[0]
            cursor = self.connection.execute(
                """INSERT INTO prompt_artifact_versions
                (artifact_id, version, content, content_hash, expected_variables, required_variables, status,
                 change_reason, created_by, created_at, supersedes_version_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (artifact.id, int(latest) + 1, content, digest, _json(sorted(expected)),
                 _json(sorted(required)), str(status), change_reason, created_by, now, supersedes_version_id),
            )
        row = self.connection.execute("SELECT * FROM prompt_artifact_versions WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return self._version(row)

    def get_version(self, artifact_key: str, version: int) -> PromptArtifactVersion | None:
        artifact = self.get_artifact(artifact_key)
        if artifact is None:
            return None
        row = self.connection.execute(
            "SELECT * FROM prompt_artifact_versions WHERE artifact_id = ? AND version = ?",
            (artifact.id, version),
        ).fetchone()
        return self._version(row) if row else None

    @staticmethod
    def validate_version_content(
        content: str, *, expected_variables: Iterable[str] = (), required_variables: Iterable[str] = (),
    ) -> None:
        if not content.strip():
            raise PromptRegistryError("Conteudo de versao vazio")
        try:
            validate_placeholder_syntax(content)
        except PromptRenderError as exc:
            raise PromptRegistryError(str(exc)) from exc
        found = set(extract_placeholders(content))
        expected = set(expected_variables)
        required = set(required_variables)
        if expected and not found.issubset(expected):
            raise PromptRegistryError(f"Placeholders nao declarados: {', '.join(sorted(found - expected))}")
        if not required.issubset(expected or found):
            raise PromptRegistryError(f"Variaveis obrigatorias nao declaradas: {', '.join(sorted(required - (expected or found)))}")
        fixtures = {name: f"fixture:{name}" for name in found}
        try:
            render(content, fixtures, expected_variables=expected or found, required_variables=required or found)
        except PromptRenderError as exc:
            raise PromptRegistryError(f"Fixture de renderizacao invalida: {exc}") from exc

    def activate_version(
        self, artifact_key: str, version: int, *, expected_active_version: int | None = None,
        expected_active_hash: str | None = None,
    ) -> PromptArtifactVersion:
        artifact = self.get_artifact(artifact_key)
        if artifact is None:
            raise PromptRegistryError(f"Artefato inexistente: {artifact_key}")
        target = self.connection.execute(
            "SELECT * FROM prompt_artifact_versions WHERE artifact_id = ? AND version = ?", (artifact.id, version)
        ).fetchone()
        if target is None:
            raise PromptRegistryError(f"Versao inexistente: {artifact_key}@{version}")
        now = _now()
        with transaction(self.connection):
            active = self.connection.execute(
                "SELECT * FROM prompt_artifact_versions WHERE artifact_id = ? AND status = 'ACTIVE'", (artifact.id,)
            ).fetchone()
            if expected_active_version is not None and (active is None or int(active["version"]) != expected_active_version):
                raise PromptRegistryError("Conflito: versao ativa mudou")
            if expected_active_hash is not None and (active is None or str(active["content_hash"]) != expected_active_hash):
                raise PromptRegistryError("Conflito: hash da versao ativa mudou")
            self.connection.execute(
                "UPDATE prompt_artifact_versions SET status = 'ARCHIVED' WHERE artifact_id = ? AND status = 'ACTIVE' AND id != ?",
                (artifact.id, target["id"]),
            )
            self.connection.execute(
                "UPDATE prompt_artifact_versions SET status = 'ACTIVE', activated_at = ? WHERE id = ?", (now, target["id"])
            )
            self.connection.execute("UPDATE prompt_artifacts SET status = 'ACTIVE', updated_at = ? WHERE id = ?", (now, artifact.id))
        return self.active_version(artifact_key)  # type: ignore[return-value]

    def rollback_version(self, artifact_key: str, version: int) -> PromptArtifactVersion:
        target = self.get_version(artifact_key, version)
        active = self.active_version(artifact_key)
        if target is None:
            raise PromptRegistryError(f"Versao inexistente: {artifact_key}@{version}")
        if active is None:
            raise PromptRegistryError(f"Artefato sem versao ativa: {artifact_key}")
        restored = self.create_version(
            artifact_key,
            target.content,
            expected_variables=target.expected_variables,
            required_variables=target.required_variables,
            change_reason=f"Rollback de versao {version}",
            created_by="gui-rollback",
            supersedes_version_id=active.id,
            allow_duplicate=True,
        )
        return self.activate_version(artifact_key, restored.version)

    def get_active_content(self, artifact_key: str) -> str:
        version = self.active_version(artifact_key)
        if version is None:
            raise PromptRegistryError(f"Artefato sem versao ativa: {artifact_key}")
        return version.content

    def upsert_operation(
        self, *, key: str, label: str, description: str = "", phase: str = "",
        phase_group: str = "", phase_order: int = 999,
        consumer_symbol: str = "", is_conditional: bool = False, retry_policy: str = "",
        fallback_policy: str = "", rollout_mode: str = RolloutMode.REGISTRY_ONLY,
    ) -> PromptOperation:
        existing = self.get_operation(key)
        if existing is not None:
            return existing
        now = _now()
        with transaction(self.connection):
            self.connection.execute(
                """INSERT INTO prompt_operations
                (key, label, description, phase, phase_group, phase_order, consumer_symbol, is_conditional, retry_policy, fallback_policy, rollout_mode, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (key, label, description, phase, phase_group, phase_order, consumer_symbol, int(is_conditional), retry_policy, fallback_policy, str(rollout_mode), now, now),
            )
        return self.get_operation(key)  # type: ignore[return-value]

    def get_operation(self, key: str) -> PromptOperation | None:
        row = self.connection.execute("SELECT * FROM prompt_operations WHERE key = ?", (key,)).fetchone()
        return self._operation(row) if row else None

    def list_operations(self) -> list[PromptOperation]:
        return [self._operation(row) for row in self.connection.execute("SELECT * FROM prompt_operations ORDER BY phase_order, key")]

    def update_operation_metadata(
        self, key: str, *, phase: str, phase_group: str, phase_order: int,
        label: str, consumer_symbol: str, is_conditional: bool, retry_policy: str,
    ) -> PromptOperation:
        operation = self.get_operation(key)
        if operation is None:
            raise PromptRegistryError(f"Operacao inexistente: {key}")
        with transaction(self.connection):
            self.connection.execute(
                """UPDATE prompt_operations SET label = ?, phase = ?, phase_group = ?, phase_order = ?,
                   consumer_symbol = ?, is_conditional = ?, retry_policy = ?, updated_at = ? WHERE id = ?""",
                (label, phase, phase_group, phase_order, consumer_symbol, int(is_conditional), retry_policy, _now(), operation.id),
            )
        return self.get_operation(key)  # type: ignore[return-value]

    def set_rollout_mode(self, key: str, mode: str) -> PromptOperation:
        if str(mode) not in {item.value for item in RolloutMode}:
            raise PromptRegistryError(f"Modo de rollout invalido: {mode}")
        operation = self.get_operation(key)
        if operation is None:
            raise PromptRegistryError(f"Operacao inexistente: {key}")
        with transaction(self.connection):
            self.connection.execute("UPDATE prompt_operations SET rollout_mode = ?, updated_at = ? WHERE id = ?", (str(mode), _now(), operation.id))
        return self.get_operation(key)  # type: ignore[return-value]

    def create_composition(
        self, operation_key: str, *, description: str = "", status: str = VersionStatus.DRAFT,
        created_by: str = "system", items: Iterable[dict[str, Any]] = (),
    ) -> PromptComposition:
        operation = self.get_operation(operation_key)
        if operation is None:
            raise PromptRegistryError(f"Operacao inexistente: {operation_key}")
        latest = self.connection.execute("SELECT COALESCE(MAX(version), 0) FROM prompt_compositions WHERE operation_id = ?", (operation.id,)).fetchone()[0]
        now = _now()
        with transaction(self.connection):
            cursor = self.connection.execute(
                "INSERT INTO prompt_compositions(operation_id, version, status, description, created_at, created_by) VALUES (?, ?, ?, ?, ?, ?)",
                (operation.id, int(latest) + 1, str(status), description, now, created_by),
            )
            composition_id = int(cursor.lastrowid)
            for item in items:
                artifact = self.get_artifact(str(item["artifact_key"]))
                if artifact is None:
                    raise PromptRegistryError(f"Artefato inexistente na composicao: {item['artifact_key']}")
                condition = item.get("condition") or {}
                self.connection.execute(
                    """INSERT INTO prompt_composition_items
                    (composition_id, artifact_id, position, required, separator, condition_type, condition_field, condition_operator, condition_value, runtime_slot)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (composition_id, artifact.id, int(item["position"]), int(item.get("required", True)), item.get("separator", "\n\n"),
                     condition.get("type"), condition.get("field"), condition.get("operator"),
                     _json(condition["value"]) if "value" in condition else None, item.get("runtime_slot")),
                )
        row = self.connection.execute("SELECT * FROM prompt_compositions WHERE id = ?", (composition_id,)).fetchone()
        return self._composition(row)

    def get_active_composition(self, operation_key: str) -> PromptComposition | None:
        row = self.connection.execute(
            """SELECT c.* FROM prompt_compositions c JOIN prompt_operations o ON o.id = c.operation_id
            WHERE o.key = ? AND c.status = 'ACTIVE'""", (operation_key,)
        ).fetchone()
        return self._composition(row) if row else None

    def list_compositions(self, operation_key: str) -> list[PromptComposition]:
        return [self._composition(row) for row in self.connection.execute(
            """SELECT c.* FROM prompt_compositions c JOIN prompt_operations o ON o.id = c.operation_id
            WHERE o.key = ? ORDER BY c.version""", (operation_key,)
        )]

    def composition_items(self, composition_id: int) -> list[PromptCompositionItem]:
        return [self._item(row) for row in self.connection.execute(
            "SELECT * FROM prompt_composition_items WHERE composition_id = ? ORDER BY position", (composition_id,)
        )]

    def activate_composition(self, operation_key: str, version: int) -> PromptComposition:
        operation = self.get_operation(operation_key)
        if operation is None:
            raise PromptRegistryError(f"Operacao inexistente: {operation_key}")
        target = self.connection.execute(
            "SELECT * FROM prompt_compositions WHERE operation_id = ? AND version = ?", (operation.id, version)
        ).fetchone()
        if target is None:
            raise PromptRegistryError(f"Composicao inexistente: {operation_key}@{version}")
        now = _now()
        with transaction(self.connection):
            self.connection.execute("UPDATE prompt_compositions SET status = 'ARCHIVED' WHERE operation_id = ? AND status = 'ACTIVE' AND id != ?", (operation.id, target["id"]))
            self.connection.execute("UPDATE prompt_compositions SET status = 'ACTIVE', activated_at = ? WHERE id = ?", (now, target["id"]))
        return self.get_active_composition(operation_key)  # type: ignore[return-value]

    def resolve_item_artifact(self, item: PromptCompositionItem) -> tuple[PromptArtifact, PromptArtifactVersion | None]:
        row = self.connection.execute("SELECT * FROM prompt_artifacts WHERE id = ?", (item.artifact_id,)).fetchone()
        if row is None:
            raise PromptRegistryError(f"Artefato ausente no item {item.id}")
        artifact = self._artifact(row)
        version_row = self.connection.execute(
            "SELECT * FROM prompt_artifact_versions WHERE artifact_id = ? AND status = 'ACTIVE'", (artifact.id,)
        ).fetchone()
        return artifact, self._version(version_row) if version_row else None

    def record_execution(self, reference: PromptExecutionReference) -> None:
        with transaction(self.connection):
            self.connection.execute(
                """INSERT OR REPLACE INTO prompt_execution_references
                (execution_id, operation_key, composition_id, composition_version, artifact_versions, template_hash, resolved_hash,
                 provider, model, resolved_at, resolution_source, error, rollout_mode, used_fallback, placeholders)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (reference.execution_id, reference.operation_key, reference.composition_id, reference.composition_version,
                 _json(reference.artifact_versions), reference.template_hash, reference.resolved_hash, reference.provider,
                 reference.model, reference.resolved_at, reference.resolution_source, reference.error, reference.rollout_mode,
                 int(reference.used_fallback), _json(reference.placeholders)),
            )

    def list_execution_references(self, operation_key: str | None = None, *, limit: int | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM prompt_execution_references"
        params: tuple[object, ...] = ()
        if operation_key:
            query += " WHERE operation_key = ?"
            params = (operation_key,)
        query += " ORDER BY resolved_at DESC"
        if limit is not None:
            query += " LIMIT ?"
            params += (max(1, min(limit, 200)),)
        result: list[dict[str, Any]] = []
        for row in self.connection.execute(query, params):
            item = dict(row)
            for field in ("artifact_versions", "placeholders"):
                item[field] = json.loads(item[field] or "[]")
            item["used_fallback"] = bool(item["used_fallback"])
            result.append(item)
        return result


__all__ = ["PromptRegistryError", "PromptRegistryRepository"]
