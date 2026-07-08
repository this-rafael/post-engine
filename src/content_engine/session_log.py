"""Log estruturado por sessao em JSONL."""
from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


DEFAULT_LOG_DIR: Path = Path(__file__).resolve().parents[2] / ".data" / "sessions" / "logs"
_SAFE_SESSION_ID = re.compile(r"[^A-Za-z0-9_.-]+")


def new_session_id() -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    suffix = uuid.uuid4().hex[:8]
    return f"{timestamp}-{suffix}"


def _safe_session_id(session_id: str) -> str:
    safe = _SAFE_SESSION_ID.sub("-", session_id.strip()).strip("-")
    return safe or new_session_id()


def default_log_path(session_id: str, session_path: str | Path | None = None) -> Path:
    if session_path is None:
        base_dir = DEFAULT_LOG_DIR
    else:
        base_dir = Path(session_path).resolve().parent / "logs"
    return base_dir / f"{_safe_session_id(session_id)}.jsonl"


@dataclass(frozen=True)
class SessionLogger:
    session_id: str
    path: Path

    def write(
        self,
        event_type: str,
        operation: str,
        payload: dict[str, Any] | None = None,
    ) -> Path:
        record = {
            "ts": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "session_id": self.session_id,
            "event_type": event_type,
            "operation": operation,
            "payload": payload or {},
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False, default=str))
            file.write("\n")
        return self.path

    def safe_write(
        self,
        event_type: str,
        operation: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        try:
            self.write(event_type, operation, payload)
        except OSError:
            pass


def ensure_session_logger(
    state: Any,
    session_path: str | Path | None = None,
) -> SessionLogger:
    session_id = str(getattr(state, "session_id", "") or "").strip()
    if not session_id:
        session_id = new_session_id()
        setattr(state, "session_id", session_id)

    log_path = str(getattr(state, "session_log_path", "") or "").strip()
    if not log_path:
        log_path = str(default_log_path(session_id, session_path))
        setattr(state, "session_log_path", log_path)

    return SessionLogger(session_id=session_id, path=Path(log_path))


__all__ = [
    "DEFAULT_LOG_DIR",
    "SessionLogger",
    "default_log_path",
    "ensure_session_logger",
    "new_session_id",
]
