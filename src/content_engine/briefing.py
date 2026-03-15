"""V4 authorial briefing projection."""
from __future__ import annotations

from typing import Any

from .interview.briefing import build_briefing
from .interview.schemas import InterviewState


def montar_briefing_autoral(state: InterviewState) -> dict[str, Any]:
    """Portuguese facade kept for callers outside the interview package."""

    return build_briefing(state)


__all__ = ["build_briefing", "montar_briefing_autoral"]
