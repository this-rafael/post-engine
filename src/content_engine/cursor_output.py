"""Parse Cursor CLI stream-json output into plain text."""
from __future__ import annotations

import json
from typing import Any


def extract_json_lines(stdout: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            events.append(parsed)
    return events


def _extract_assistant_text(event: dict[str, Any]) -> str:
    message = event.get("message") or {}
    parts: list[str] = []
    for block in message.get("content") or []:
        if isinstance(block, dict) and block.get("type") == "text":
            text = block.get("text", "")
            if text:
                parts.append(str(text))
    return "".join(parts)


def _stringify_error(*values: object, fallback: str = "cursor run failed") -> str:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and value:
            return value
        if isinstance(value, dict):
            message = value.get("message")
            if isinstance(message, str) and message:
                return message
            return json.dumps(value, ensure_ascii=False)
        return str(value)
    return fallback


def parse_cursor_output(stdout: str, stderr: str = "", *, returncode: int = 0) -> tuple[str, str | None]:
    """Return (output_text, error_message)."""
    events = extract_json_lines(stdout)
    agent_messages: list[str] = []
    output = ""
    error_msg: str | None = None

    for event in events:
        etype = event.get("type", "")
        subtype = event.get("subtype", "")

        if etype == "assistant":
            text = _extract_assistant_text(event)
            if text:
                agent_messages.append(text)
        elif etype == "result":
            if event.get("is_error") or subtype not in ("success", ""):
                error_msg = _stringify_error(
                    event.get("result"),
                    event.get("error"),
                    fallback="cursor run failed",
                )
            elif event.get("result"):
                output = str(event["result"])
        elif etype == "error":
            error_msg = _stringify_error(
                event.get("message"),
                event,
                fallback="cursor error",
            )

    if not output:
        output = "\n".join(agent_messages) if agent_messages else stdout

    if returncode != 0 and not error_msg:
        error_msg = stderr.strip() or f"cursor exited with code {returncode}"

    return output, error_msg


def resolve_cursor_model(
    model: str | None,
    reasoning_effort: str | None = None,
) -> str | None:
    resolved = model
    if not resolved or resolved == "auto":
        resolved = None

    if reasoning_effort and reasoning_effort != "auto":
        effort = reasoning_effort
        if resolved:
            if "[" not in resolved:
                resolved = f"{resolved}[effort={effort}]"
        else:
            resolved = f"auto[effort={effort}]"

    return resolved


__all__ = [
    "extract_json_lines",
    "parse_cursor_output",
    "resolve_cursor_model",
]
