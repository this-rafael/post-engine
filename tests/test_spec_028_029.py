"""Testes de SPEC-028/029: AgentWrapper (codex, opencode) e tratamento de subprocess."""
from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from content_engine.agent_wrapper import OPENCODE_PROMPT_FILE_MESSAGE, AgentWrapper
from content_engine.schemas import AgentResult


def _ok(stdout: str = "", stderr: str = "", returncode: int = 0) -> SimpleNamespace:
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def _capture_runner(captured: dict) -> object:
    def _runner(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        cmd = args[0] if args else None
        if (
            isinstance(cmd, list)
            and cmd
            and cmd[0] == "opencode"
            and OPENCODE_PROMPT_FILE_MESSAGE in cmd
        ):
            file_indexes = [i for i, part in enumerate(cmd) if part == "--file"]
            assert file_indexes, "opencode cmd must include --file for prompt"
            message_index = cmd.index(OPENCODE_PROMPT_FILE_MESSAGE)
            assert message_index < file_indexes[0], (
                "message must precede --file so yargs does not treat it as a path"
            )
            prompt_path = Path(cmd[file_indexes[-1] + 1])
            captured["prompt_file"] = str(prompt_path)
            captured["prompt_file_text"] = prompt_path.read_text(encoding="utf-8")
            assert len(OPENCODE_PROMPT_FILE_MESSAGE.encode("utf-8")) < 131072
            assert max(len(part.encode("utf-8")) for part in cmd) < 131072
        return _ok(stdout="ok", stderr="")

    return _runner


def _assert_opencode_prompt_via_file(captured: dict, expected_prompt: str) -> list[str]:
    cmd = captured["args"][0]
    assert cmd[0] == "opencode"
    assert OPENCODE_PROMPT_FILE_MESSAGE in cmd
    assert "--file" in cmd
    assert cmd.index(OPENCODE_PROMPT_FILE_MESSAGE) < cmd.index("--file")
    assert captured["prompt_file_text"] == expected_prompt
    assert not Path(captured["prompt_file"]).exists()
    return cmd

def test_codex_command_assembly_all_params() -> None:
    captured: dict = {}
    runner = _capture_runner(captured)
    wrapper = AgentWrapper(workspace=Path("/tmp/ws"), timeout=120)
    result = wrapper.run_codex(
        "do the thing",
        model="gpt-x",
        sandbox="workspace-write",
        json_output=True,
        extra_context="ctx",
        ephemeral=True,
        ignore_user_config=True,
        runner=runner,
    )
    assert result.ok is True
    cmd = captured["args"][0]
    assert cmd[0] == "codex"
    assert cmd[1:4] == ["exec", "--skip-git-repo-check", "--cd"]
    assert cmd[4] == "/tmp/ws"
    assert "--sandbox" in cmd
    assert "workspace-write" in cmd
    assert "--color" in cmd and "never" in cmd
    assert "--ephemeral" in cmd
    assert "--ignore-user-config" in cmd
    assert "--model" in cmd and "gpt-x" in cmd
    assert "--json" in cmd
    assert cmd[-1] == "-"
    kwargs = captured["kwargs"]
    assert kwargs["input"] == "ctx\n\ndo the thing"
    assert kwargs["text"] is True
    assert kwargs["cwd"] == "/tmp/ws"
    assert kwargs["timeout"] == 120
    assert kwargs["check"] is False
    assert kwargs["stdout"] is subprocess.PIPE
    assert kwargs["stderr"] is subprocess.PIPE


def test_codex_command_default_ephemeral_only() -> None:
    captured: dict = {}
    runner = _capture_runner(captured)
    wrapper = AgentWrapper(workspace="/tmp/ws")
    wrapper.run_codex("hello", runner=runner)
    cmd = captured["args"][0]
    assert cmd[:8] == [
        "codex",
        "exec",
        "--skip-git-repo-check",
        "--cd",
        "/tmp/ws",
        "--sandbox",
        "read-only",
        "--color",
    ]
    assert cmd[8] == "never"
    assert "--ephemeral" in cmd
    assert "--ignore-user-config" in cmd
    assert "--json" not in cmd
    assert cmd[-1] == "-"
    assert captured["kwargs"]["input"] == "hello"


def test_codex_no_ephemeral_and_no_ignore_user_config() -> None:
    captured: dict = {}
    runner = _capture_runner(captured)
    wrapper = AgentWrapper(workspace="/tmp/ws")
    wrapper.run_codex("p", ephemeral=False, ignore_user_config=False, runner=runner)
    cmd = captured["args"][0]
    assert "--ephemeral" not in cmd
    assert "--ignore-user-config" not in cmd


def test_opencode_command_assembly_all_params() -> None:
    captured: dict = {}
    runner = _capture_runner(captured)
    wrapper = AgentWrapper(workspace="/tmp/ws")
    result = wrapper.run_opencode(
        "go",
        model="m1",
        agent="build",
        reasoning_effort="max",
        files=["/a.txt", Path("/b/c.md")],
        json_output=True,
        attach_url="http://x",
        dangerously_skip_permissions=True,
        runner=runner,
    )
    assert result.ok is True
    cmd = _assert_opencode_prompt_via_file(captured, "go")
    assert cmd[:4] == ["opencode", "run", "--dir", "/tmp/ws"]
    assert "--model" in cmd and "m1" in cmd
    assert cmd[cmd.index("--variant") + 1] == "max"
    assert "--agent" in cmd and "build" in cmd
    assert "--format" in cmd and "json" in cmd
    assert "--attach" in cmd and "http://x" in cmd
    assert "--dangerously-skip-permissions" in cmd
    assert cmd[cmd.index("--file") + 1] == "/a.txt"
    assert cmd[cmd.index("--file") + 3] == "/b/c.md"
    assert cmd[-2:] == ["--file", captured["prompt_file"]]


def test_opencode_command_minimal() -> None:
    captured: dict = {}
    runner = _capture_runner(captured)
    wrapper = AgentWrapper(workspace="/tmp/ws")
    wrapper.run_opencode("solo", runner=runner)
    cmd = _assert_opencode_prompt_via_file(captured, "solo")
    assert cmd[:4] == ["opencode", "run", "--dir", "/tmp/ws"]
    assert cmd[-3:] == [
        OPENCODE_PROMPT_FILE_MESSAGE,
        "--file",
        captured["prompt_file"],
    ]


def test_opencode_command_uses_medium_variant() -> None:
    captured: dict = {}
    wrapper = AgentWrapper(workspace="/tmp/ws")
    wrapper.run_opencode(
        "solo", reasoning_effort="medium", runner=_capture_runner(captured)
    )
    cmd = _assert_opencode_prompt_via_file(captured, "solo")
    assert cmd == [
        "opencode",
        "run",
        "--dir",
        "/tmp/ws",
        "--variant",
        "medium",
        OPENCODE_PROMPT_FILE_MESSAGE,
        "--file",
        captured["prompt_file"],
    ]


def test_opencode_command_ignores_codex_only_reasoning_levels() -> None:
    captured: dict = {}
    wrapper = AgentWrapper(workspace="/tmp/ws")
    wrapper.run_opencode(
        "solo", reasoning_effort="high", runner=_capture_runner(captured)
    )
    assert "--variant" not in captured["args"][0]
    _assert_opencode_prompt_via_file(captured, "solo")


def test_opencode_large_prompt_stays_below_max_arg_strlen() -> None:
    captured: dict = {}
    large_prompt = "x" * 200_000
    wrapper = AgentWrapper(workspace="/tmp/ws")
    result = wrapper.run_opencode(large_prompt, runner=_capture_runner(captured))
    assert result.ok is True
    cmd = _assert_opencode_prompt_via_file(captured, large_prompt)
    assert max(len(part.encode("utf-8")) for part in cmd) < 131072


def test_both_include_workspace_in_cwd_and_kwarg() -> None:
    for prompt_kw in [
        {"prompt": "p", "runner": _capture_runner({})},
    ]:
        pass

    captured_codex: dict = {}
    captured_opencode: dict = {}
    wrapper = AgentWrapper(workspace=Path("/var/proj"))
    wrapper.run_codex("p", runner=_capture_runner(captured_codex))
    wrapper.run_opencode("p", runner=_capture_runner(captured_opencode))
    assert captured_codex["kwargs"]["cwd"] == "/var/proj"
    assert captured_opencode["kwargs"]["cwd"] == "/var/proj"
    assert "/var/proj" in captured_codex["args"][0]
    assert "/var/proj" in captured_opencode["args"][0]


def test_prompt_preserved_as_last_element_both() -> None:
    captured_codex: dict = {}
    captured_opencode: dict = {}
    wrapper = AgentWrapper(workspace="/tmp/ws")
    wrapper.run_codex(
        "PROMPT-CODEX",
        model="m",
        json_output=True,
        runner=_capture_runner(captured_codex),
    )
    wrapper.run_opencode(
        "PROMPT-OPENCODE",
        model="m",
        files=["f"],
        runner=_capture_runner(captured_opencode),
    )
    assert captured_codex["args"][0][-1] == "-"
    assert captured_codex["kwargs"]["input"] == "PROMPT-CODEX"
    cmd = _assert_opencode_prompt_via_file(captured_opencode, "PROMPT-OPENCODE")
    assert cmd[-2:] == ["--file", captured_opencode["prompt_file"]]
    assert OPENCODE_PROMPT_FILE_MESSAGE in cmd


def test_run_dispatches_to_codex_and_opencode() -> None:
    captured_codex: dict = {}
    captured_opencode: dict = {}
    wrapper = AgentWrapper(workspace="/tmp/ws")
    wrapper.run("codex", "p1", runner=_capture_runner(captured_codex))
    wrapper.run("opencode", "p2", runner=_capture_runner(captured_opencode))
    assert captured_codex["args"][0][0] == "codex"
    assert captured_opencode["args"][0][0] == "opencode"


def test_run_raises_value_error_on_unknown_tool() -> None:
    wrapper = AgentWrapper(workspace="/tmp/ws")
    with pytest.raises(ValueError):
        wrapper.run("claude", "p")


def test_workspace_path_resolved_in_init() -> None:
    wrapper = AgentWrapper(workspace="/tmp/ws")
    assert isinstance(wrapper.workspace, Path)
    assert wrapper.workspace.is_absolute()


def test_env_merged_with_os_environ() -> None:
    wrapper = AgentWrapper(workspace="/tmp/ws", env={"FOO": "bar"})
    assert wrapper.env["FOO"] == "bar"
    for key in ("PATH",):
        assert key in wrapper.env


def test_instantiation_does_not_execute() -> None:
    AgentWrapper(workspace="/tmp/ws", timeout=10, env={"X": "1"})


def test_jsonl_events_parsed_when_json_output() -> None:
    stdout = (
        '{"type":"message","text":"hi"}\n'
        '{"type":"done"}\n'
    )
    def runner(*_args: object, **_kwargs: object):
        return _ok(stdout=stdout, stderr="")

    wrapper = AgentWrapper(workspace="/tmp/ws")
    res = wrapper.run_codex("p", json_output=True, runner=runner)
    assert res.ok is True
    assert res.events is not None
    assert res.events == [
        {"type": "message", "text": "hi"},
        {"type": "done"},
    ]


def test_jsonl_raw_fallback_for_invalid_lines() -> None:
    stdout = (
        '{"type":"ok"}\n'
        'not json line\n'
        '{"type":"done"}\n'
    )
    def runner(*_args: object, **_kwargs: object):
        return _ok(stdout=stdout, stderr="")

    wrapper = AgentWrapper(workspace="/tmp/ws")
    res = wrapper.run_opencode("p", json_output=True, runner=runner)
    assert res.events == [
        {"type": "ok"},
        {"type": "raw", "message": "not json line"},
        {"type": "done"},
    ]


def test_jsonl_empty_lines_skipped() -> None:
    stdout = '{"a":1}\n\n\n{"b":2}\n'
    def runner(*_args: object, **_kwargs: object):
        return _ok(stdout=stdout, stderr="")

    wrapper = AgentWrapper(workspace="/tmp/ws")
    res = wrapper.run_codex("p", json_output=True, runner=runner)
    assert res.events == [{"a": 1}, {"b": 2}]


def test_jsonl_not_parsed_when_json_output_false() -> None:
    def runner(*_args: object, **_kwargs: object):
        return _ok(stdout='{"a":1}', stderr="")

    wrapper = AgentWrapper(workspace="/tmp/ws")
    res = wrapper.run_codex("p", json_output=False, runner=runner)
    assert res.events is None


def test_subclass_overriding_run_subprocess() -> None:
    class FakeWrapper(AgentWrapper):
        def __init__(self) -> None:
            super().__init__(workspace="/tmp/ws")
            self.calls: list[list[str]] = []

        def _run_subprocess(
            self,
            tool: str,
            cmd: list[str],
            *,
            stdin: str | None = None,
            parse_jsonl: bool = False,
            runner=subprocess.run,
            logged_prompt: str | None = None,
        ) -> AgentResult:
            del logged_prompt
            self.calls.append(cmd)
            return AgentResult(
                tool=tool,
                command=cmd,
                returncode=0,
                stdout="x",
                stderr="",
            )

    fw = FakeWrapper()
    res = fw.run_codex("p")
    assert res.stdout == "x"
    assert fw.calls[0][0] == "codex"
    res2 = fw.run_opencode("p")
    assert fw.calls[1][0] == "opencode"
    assert res2.stdout == "x"


def test_filenotfound_returns_127_with_message() -> None:
    def _raise_fnf(*a, **k):
        raise FileNotFoundError("nope")

    wrapper = AgentWrapper(workspace="/tmp/ws")
    res = wrapper.run_codex("p", runner=_raise_fnf)
    assert res.returncode == 127
    assert res.error == "CLI not found: codex"
    assert res.ok is False


def test_permissionerror_returns_126_with_message() -> None:
    def _raise_perm(*a, **k):
        raise PermissionError("denied")

    wrapper = AgentWrapper(workspace="/tmp/ws")
    res = wrapper.run_opencode("p", runner=_raise_perm)
    assert res.returncode == 126
    assert res.error is not None
    assert "Permission denied" in res.error
    assert "opencode" in res.error
    assert res.ok is False


def test_timeoutexpired_returns_124_with_message() -> None:
    def _raise_timeout(*a, **k):
        raise subprocess.TimeoutExpired(cmd=["codex"], timeout=900)

    wrapper = AgentWrapper(workspace="/tmp/ws", timeout=900)
    res = wrapper.run_codex("p", runner=_raise_timeout)
    assert res.returncode == 124
    assert res.error is not None
    assert "Timeout" in res.error
    assert "900" in res.error
    assert res.ok is False


def test_nonzero_returncode_captured_in_result() -> None:
    def runner(*_args: object, **_kwargs: object):
        return _ok(stdout="oops", stderr="bad", returncode=2)

    wrapper = AgentWrapper(workspace="/tmp/ws")
    res = wrapper.run_codex("p", runner=runner)
    assert res.returncode == 2
    assert res.stdout == "oops"
    assert res.stderr == "bad"
    assert res.ok is False


def test_empty_stdout_nonempty_stderr_sets_error() -> None:
    def runner(*_args: object, **_kwargs: object):
        return _ok(stdout="", stderr="warning", returncode=0)

    wrapper = AgentWrapper(workspace="/tmp/ws")
    res = wrapper.run_codex("p", runner=runner)
    assert res.returncode == 0
    assert res.stdout == ""
    assert res.stderr == "warning"
    assert res.error == "stdout vazio"
    assert res.ok is False


def test_success_with_both_streams_populated() -> None:
    def runner(*_args: object, **_kwargs: object):
        return _ok(stdout="out", stderr="info", returncode=0)

    wrapper = AgentWrapper(workspace="/tmp/ws")
    res = wrapper.run_codex("p", runner=runner)
    assert res.ok is True
    assert res.error is None


def test_jsonl_invalid_line_preserved_as_raw_event_in_subprocess_path() -> None:
    def runner(*_args: object, **_kwargs: object):
        return _ok(
            stdout='garbage line\n{"real":true}\n',
            stderr="",
            returncode=0,
        )

    wrapper = AgentWrapper(workspace="/tmp/ws")
    res = wrapper.run_codex("p", json_output=True, runner=runner)
    assert res.ok is True
    assert res.events is not None
    assert {"type": "raw", "message": "garbage line"} in res.events
    assert {"real": True} in res.events


def test_no_real_codex_or_opencode_invocation() -> None:
    captured_codex: dict = {}
    captured_opencode: dict = {}
    wrapper = AgentWrapper(workspace="/tmp/ws")
    wrapper.run_codex("p", runner=_capture_runner(captured_codex))
    wrapper.run_opencode("p", runner=_capture_runner(captured_opencode))
    assert captured_codex["args"], "codex runner should have been invoked"
    assert captured_opencode["args"], "opencode runner should have been invoked"
    assert captured_codex["args"][0][0] == "codex"
    assert captured_opencode["args"][0][0] == "opencode"
