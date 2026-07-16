"""Schema versionado e backup seguro antes de migrations estruturais."""
from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

from .database import connect, registry_path, transaction


SCHEMA_VERSION = 3

_SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prompt_artifacts (
    id INTEGER PRIMARY KEY,
    key TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    artifact_type TEXT NOT NULL,
    status TEXT NOT NULL,
    source_origin TEXT NOT NULL DEFAULT '',
    legacy_source_path TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prompt_artifact_versions (
    id INTEGER PRIMARY KEY,
    artifact_id INTEGER NOT NULL REFERENCES prompt_artifacts(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    content TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    expected_variables TEXT NOT NULL DEFAULT '[]',
    required_variables TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL,
    change_reason TEXT NOT NULL DEFAULT '',
    created_by TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    activated_at TEXT,
    supersedes_version_id INTEGER REFERENCES prompt_artifact_versions(id),
    UNIQUE(artifact_id, version)
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_prompt_artifact_one_active
ON prompt_artifact_versions(artifact_id) WHERE status = 'ACTIVE';

CREATE TABLE IF NOT EXISTS prompt_operations (
    id INTEGER PRIMARY KEY,
    key TEXT NOT NULL UNIQUE,
    label TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    phase TEXT NOT NULL DEFAULT '',
    consumer_symbol TEXT NOT NULL DEFAULT '',
    is_conditional INTEGER NOT NULL DEFAULT 0,
    retry_policy TEXT NOT NULL DEFAULT '',
    fallback_policy TEXT NOT NULL DEFAULT '',
    rollout_mode TEXT NOT NULL DEFAULT 'REGISTRY_ONLY',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS prompt_compositions (
    id INTEGER PRIMARY KEY,
    operation_id INTEGER NOT NULL REFERENCES prompt_operations(id) ON DELETE CASCADE,
    version INTEGER NOT NULL,
    status TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    activated_at TEXT,
    created_by TEXT NOT NULL DEFAULT '',
    UNIQUE(operation_id, version)
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_prompt_composition_one_active
ON prompt_compositions(operation_id) WHERE status = 'ACTIVE';

CREATE TABLE IF NOT EXISTS prompt_composition_items (
    id INTEGER PRIMARY KEY,
    composition_id INTEGER NOT NULL REFERENCES prompt_compositions(id) ON DELETE CASCADE,
    artifact_id INTEGER NOT NULL REFERENCES prompt_artifacts(id),
    position INTEGER NOT NULL,
    required INTEGER NOT NULL DEFAULT 1,
    separator TEXT NOT NULL DEFAULT '\n\n',
    condition_type TEXT,
    condition_field TEXT,
    condition_operator TEXT,
    condition_value TEXT,
    runtime_slot TEXT,
    UNIQUE(composition_id, position)
);

CREATE TABLE IF NOT EXISTS prompt_execution_references (
    execution_id TEXT PRIMARY KEY,
    operation_key TEXT NOT NULL,
    composition_id INTEGER,
    composition_version INTEGER,
    artifact_versions TEXT NOT NULL DEFAULT '[]',
    template_hash TEXT,
    resolved_hash TEXT,
    provider TEXT,
    model TEXT,
    resolved_at TEXT NOT NULL,
    resolution_source TEXT NOT NULL,
    error TEXT,
    rollout_mode TEXT NOT NULL DEFAULT 'REGISTRY_ONLY',
    used_fallback INTEGER NOT NULL DEFAULT 0,
    placeholders TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS ix_prompt_execution_operation
ON prompt_execution_references(operation_key, resolved_at DESC);
"""

_SCHEMA_V2 = """
CREATE TRIGGER IF NOT EXISTS prevent_prompt_version_content_mutation
BEFORE UPDATE OF content, content_hash, expected_variables, required_variables, version, artifact_id
ON prompt_artifact_versions
BEGIN
    SELECT RAISE(ABORT, 'prompt artifact versions are immutable');
END;
"""

_SCHEMA_V3 = """
ALTER TABLE prompt_operations ADD COLUMN phase_group TEXT NOT NULL DEFAULT '';
ALTER TABLE prompt_operations ADD COLUMN phase_order INTEGER NOT NULL DEFAULT 999;
CREATE INDEX IF NOT EXISTS ix_prompt_operations_phase_order
ON prompt_operations(phase_order, key);
"""

_MIGRATIONS: tuple[tuple[int, str], ...] = ((1, _SCHEMA_V1), (2, _SCHEMA_V2), (3, _SCHEMA_V3))


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def backup_database(path: str | Path | None = None) -> Path | None:
    database = registry_path(path)
    if not database.exists():
        return None
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    target = database.with_name(f"{database.stem}.{stamp}.bak{database.suffix}")
    shutil.copy2(database, target)
    return target


def initialize_database(path: str | Path | None = None) -> Path:
    database = registry_path(path)
    existed = database.exists()
    connection = connect(database)
    try:
        has_migrations = bool(
            connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
            ).fetchone()
        )
        applied = (
            {row[0] for row in connection.execute("SELECT version FROM schema_migrations")}
            if has_migrations
            else set()
        )
        missing = [(version, statement) for version, statement in _MIGRATIONS if version not in applied]
        if missing:
            if existed and has_migrations:
                backup_database(database)
            with transaction(connection):
                for version, statement in missing:
                    connection.executescript(statement)
                    connection.execute(
                        "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                        (version, _now()),
                    )
    finally:
        connection.close()
    return database


__all__ = ["SCHEMA_VERSION", "backup_database", "initialize_database"]
