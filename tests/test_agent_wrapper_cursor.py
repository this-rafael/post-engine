"""Testes do suporte Cursor no AgentWrapper."""
from __future__ import annotations

import json
from types import SimpleNamespace

from content_engine.agent_wrapper import AgentWrapper
from content_engine.cursor_output import (
    parse_cursor_output,
    resolve_cursor_model,
)


def test_resolve_cursor_model_auto_omits_flag() -> None:
    assert resolve_cursor_model("auto", "auto") is None


def test_resolve_cursor_model_with_effort() -> None:
    assert resolve_cursor_model("composer-2.5", "high") == "composer-2.5[effort=high]"


def test_resolve_cursor_model_effort_only() -> None:
    assert resolve_cursor_model(None, "high") == "auto[effort=high]"


def test_parse_cursor_output_success() -> None:
    stdout = json.dumps(
        {
            "type": "result",
            "subtype": "success",
            "is_error": False,
            "result": "Feature spec created.",
        }
    )
    output, error = parse_cursor_output(stdout)
    assert output == "Feature spec created."
    assert error is None


def test_parse_cursor_output_assistant_fallback() -> None:
    stdout = json.dumps(
        {
            "type": "assistant",
            "message": {
                "content": [{"type": "text", "text": "Hello from assistant."}],
            },
        }
    )
    output, error = parse_cursor_output(stdout)
    assert output == "Hello from assistant."
    assert error is None


def test_parse_cursor_output_error() -> None:
    stdout = json.dumps(
        {
            "type": "result",
            "subtype": "error",
            "is_error": True,
            "result": "Authentication required",
        }
    )
    output, error = parse_cursor_output(stdout, returncode=1)
    assert error == "Authentication required"


def test_run_cursor_builds_cli_command() -> None:
    captured: dict[str, object] = {}

    def runner(cmd, **kwargs):
        captured["cmd"] = cmd
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "type": "result",
                    "subtype": "success",
                    "is_error": False,
                    "result": "ok",
                }
            ),
            stderr="",
        )

    wrapper = AgentWrapper(workspace="/tmp/ws")
    result = wrapper.run_cursor(
        "Create login flow",
        model="composer-2.5",
        reasoning_effort="high",
        runner=runner,
    )

    cmd = captured["cmd"]
    assert cmd[0] == "agent"
    assert "--print" in cmd
    assert "stream-json" in cmd
    assert "--workspace" in cmd
    assert "/tmp/ws" in cmd
    assert "--sandbox" in cmd
    assert "disabled" in cmd
    assert "composer-2.5[effort=high]" in cmd
    assert cmd[-1] == "Create login flow"
    assert result.ok
    assert result.stdout == "ok"
    assert result.tool == "cursor"


def test_run_dispatches_cursor() -> None:
    captured: dict[str, object] = {}

    def runner(cmd, **kwargs):
        captured["cmd"] = cmd
        return SimpleNamespace(
            returncode=0,
            stdout=json.dumps(
                {
                    "type": "result",
                    "subtype": "success",
                    "result": "done",
                }
            ),
            stderr="",
        )

    wrapper = AgentWrapper(workspace="/tmp/ws")
    result = wrapper.run("cursor", "prompt text", model="auto", runner=runner)
    assert result.tool == "cursor"
    assert result.stdout == "done"
