"""Conexao SQLite local e transacoes do registry."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


DEFAULT_REGISTRY_PATH = Path(__file__).resolve().parents[3] / ".data" / "prompt-registry.sqlite3"


def registry_path(path: str | Path | None = None) -> Path:
    return Path(path).expanduser().resolve() if path is not None else DEFAULT_REGISTRY_PATH


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    database = registry_path(path)
    database.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


@contextmanager
def transaction(connection: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    try:
        connection.execute("BEGIN IMMEDIATE")
        yield connection
    except Exception:
        connection.rollback()
        raise
    else:
        connection.commit()
