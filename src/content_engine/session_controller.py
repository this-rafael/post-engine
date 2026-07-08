"""API publica de sessao para GUI e testes (sem pacote TUI)."""
from __future__ import annotations

from typing import Any

from .session_app import PostEngineApp, SCORE_AVALIACAO_ASPECTOS
from .session_app import (
    PHASE_AVALIACAO,
    PHASE_BRIEFING,
    PHASE_ENTRADA,
    PHASE_ENTREVISTA,
    PHASE_EXECUCAO,
    PHASE_EXPORTACAO,
    PHASE_PROMPT,
    PHASE_SEGMENTACAO,
)


class SessionController(PostEngineApp):
    """Orquestrador headless — ignora refresh de widgets Textual."""

    def refresh(self, *args: Any, **kwargs: Any) -> "SessionController":
        return self

    def notify(self, *args: Any, **kwargs: Any) -> None:
        return None

    def call_after_refresh(self, callback: Any, *args: Any, **kwargs: Any) -> None:
        if callable(callback):
            callback(*args, **kwargs)

    def call_later(self, callback: Any, *args: Any, **kwargs: Any) -> None:
        if callable(callback):
            callback(*args, **kwargs)

    def set_focus(self, *args: Any, **kwargs: Any) -> None:
        return None


HeadlessPostEngineApp = SessionController

__all__ = [
    "SessionController",
    "HeadlessPostEngineApp",
    "PostEngineApp",
    "SCORE_AVALIACAO_ASPECTOS",
    "PHASE_AVALIACAO",
    "PHASE_BRIEFING",
    "PHASE_ENTRADA",
    "PHASE_ENTREVISTA",
    "PHASE_EXECUCAO",
    "PHASE_EXPORTACAO",
    "PHASE_PROMPT",
    "PHASE_SEGMENTACAO",
]
