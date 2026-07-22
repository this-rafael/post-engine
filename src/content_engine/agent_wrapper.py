"""SPEC-028/029: wrapper de invocacao de agentes CLI (codex, opencode)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import weakref
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal

OPENCODE_PROMPT_FILE_MESSAGE = (
    "Follow the instructions in the attached prompt file exactly."
)

from content_engine.cursor_output import parse_cursor_output, resolve_cursor_model
from content_engine.schemas import AgentResult, SandboxPolicy, ToolName
from content_engine.session_log import SessionLogger

SubprocessRunner = Callable[..., Any]


def _failure_message_from_output(
    stdout: str,
    stderr: str,
    events: list[dict[str, Any]] | None,
) -> str | None:
    """Extrai mensagem util de falha de stdout JSONL/eventos ou stderr."""
    if events:
        for event in events:
            if not isinstance(event, dict):
                continue
            event_type = event.get("type")
            if event_type == "error":
                message = event.get("message")
                if isinstance(message, str) and message.strip():
                    return message.strip()
                nested = event.get("error")
                if isinstance(nested, dict):
                    data = nested.get("data")
                    if isinstance(data, dict) and isinstance(data.get("message"), str):
                        return str(data["message"]).strip()
                    if isinstance(nested.get("message"), str):
                        return str(nested["message"]).strip()
                    if isinstance(nested.get("name"), str):
                        return str(nested["name"]).strip()
            if event_type == "turn.failed":
                nested = event.get("error")
                if isinstance(nested, dict) and isinstance(nested.get("message"), str):
                    return str(nested["message"]).strip()
            item = event.get("item")
            if isinstance(item, dict) and item.get("type") == "error":
                if isinstance(item.get("message"), str):
                    return str(item["message"]).strip()
    if stderr.strip():
        return stderr.strip()
    if stdout.strip():
        return stdout.strip()[:800]
    return None


class AgentWrapper:
    def __init__(
        self,
        workspace: str | Path,
        timeout: int = 900,
        env: dict[str, str] | None = None,
        session_logger: SessionLogger | None = None,
        *,
        project_root: str | Path | None = None,
        operation: str = "",
        owns_workspace: bool = False,
    ) -> None:
        self.workspace: Path = Path(workspace).resolve()
        self.project_root: Path | None = (
            Path(project_root).resolve() if project_root else None
        )
        self.operation: str = operation
        self.timeout: int = timeout
        merged: dict[str, str] = dict(os.environ)
        if env is not None:
            merged.update(env)
        self.env: dict[str, str] = merged
        self.session_logger: SessionLogger | None = session_logger
        self._owns_workspace: bool = owns_workspace
        if owns_workspace:
            weakref.finalize(self, self._cleanup_workspace, self.workspace)

    @staticmethod
    def _cleanup_workspace(path: Path) -> None:
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)

    def close(self) -> None:
        if self._owns_workspace and self.workspace.exists():
            shutil.rmtree(self.workspace, ignore_errors=True)

    def run_codex(
        self,
        prompt: str,
        *,
        model: str | None = None,
        reasoning_effort: str | None = None,
        sandbox: SandboxPolicy = "read-only",
        json_output: bool = False,
        extra_context: str | None = None,
        ephemeral: bool = True,
        ignore_user_config: bool = True,
        runner: SubprocessRunner = subprocess.run,
    ) -> AgentResult:
        cmd: list[str] = [
            "codex",
            "exec",
            "--skip-git-repo-check",
            "--cd",
            str(self.workspace),
            "--sandbox",
            sandbox,
            "--color",
            "never",
        ]
        if ephemeral:
            cmd.append("--ephemeral")
        if ignore_user_config:
            cmd.append("--ignore-user-config")
        if model:
            cmd += ["--model", model]
        if reasoning_effort:
            cmd += ["-c", f'model_reasoning_effort="{reasoning_effort}"']
        if json_output:
            cmd.append("--json")
        cmd.append("-")
        stdin_payload = self._build_codex_stdin(prompt, extra_context)
        return self._run_subprocess(
            "codex",
            cmd,
            stdin=stdin_payload,
            parse_jsonl=json_output,
            runner=runner,
        )

    def run_opencode(
        self,
        prompt: str,
        *,
        model: str | None = None,
        agent: str | None = None,
        reasoning_effort: str | None = None,
        files: list[str | Path] | None = None,
        json_output: bool = False,
        attach_url: str | None = None,
        dangerously_skip_permissions: bool = False,
        runner: SubprocessRunner = subprocess.run,
    ) -> AgentResult:
        # Prompt goes via --file to avoid Linux MAX_ARG_STRLEN (131072) E2BIG.
        prompt_file = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".md",
            prefix="opencode-prompt-",
            delete=False,
        )
        prompt_path = Path(prompt_file.name)
        try:
            prompt_file.write(prompt)
            prompt_file.close()

            cmd: list[str] = ["opencode", "run", "--dir", str(self.workspace)]
            if model:
                cmd += ["--model", model]
            if reasoning_effort in {"medium", "max"}:
                cmd += ["--variant", reasoning_effort]
            if agent:
                cmd += ["--agent", agent]
            if json_output:
                cmd += ["--format", "json"]
            if attach_url:
                cmd += ["--attach", attach_url]
            if dangerously_skip_permissions:
                cmd.append("--dangerously-skip-permissions")
            # Message must precede --file: yargs array options greedily consume
            # following non-option args as additional file paths.
            cmd.append(OPENCODE_PROMPT_FILE_MESSAGE)
            if files:
                for file in files:
                    cmd += ["--file", str(file)]
            cmd += ["--file", str(prompt_path)]
            return self._run_subprocess(
                "opencode",
                cmd,
                parse_jsonl=json_output,
                runner=runner,
                logged_prompt=prompt,
            )
        finally:
            prompt_file.close()
            prompt_path.unlink(missing_ok=True)

    def run_cursor(
        self,
        prompt: str,
        *,
        model: str | None = None,
        reasoning_effort: str | None = None,
        runner: SubprocessRunner = subprocess.run,
    ) -> AgentResult:
        cmd: list[str] = [
            "agent",
            "--print",
            "--output-format",
            "stream-json",
            "--trust",
            "--force",
            "--approve-mcps",
            "--workspace",
            str(self.workspace),
            "--sandbox",
            "disabled",
        ]
        resolved_model = resolve_cursor_model(model, reasoning_effort)
        if resolved_model:
            cmd += ["--model", resolved_model]
        cmd.append(prompt)
        result = self._run_subprocess(
            "cursor",
            cmd,
            parse_jsonl=False,
            runner=runner,
        )
        output, error = parse_cursor_output(
            result.stdout,
            result.stderr,
            returncode=result.returncode,
        )
        events: list[dict] | None = None
        if result.stdout:
            from content_engine.cursor_output import extract_json_lines

            events = extract_json_lines(result.stdout)
        return AgentResult(
            tool="cursor",
            command=result.command,
            returncode=result.returncode,
            stdout=output,
            stderr=result.stderr,
            events=events,
            error=error if error else result.error,
        )

    def run(self, tool: ToolName, prompt: str, **kwargs: Any) -> AgentResult:
        runner = kwargs.get("runner", subprocess.run)
        if tool == "codex":
            return self.run_codex(
                prompt,
                model=kwargs.get("model"),
                reasoning_effort=kwargs.get("reasoning_effort"),
                sandbox=kwargs.get("sandbox", "read-only"),
                json_output=kwargs.get("json_output", False),
                extra_context=kwargs.get("extra_context"),
                ephemeral=kwargs.get("ephemeral", True),
                ignore_user_config=kwargs.get("ignore_user_config", True),
                runner=runner,
            )
        if tool == "opencode":
            return self.run_opencode(
                prompt,
                model=kwargs.get("model"),
                agent=kwargs.get("agent"),
                reasoning_effort=kwargs.get("reasoning_effort"),
                files=kwargs.get("files"),
                json_output=kwargs.get("json_output", False),
                attach_url=kwargs.get("attach_url"),
                dangerously_skip_permissions=kwargs.get(
                    "dangerously_skip_permissions", False
                ),
                runner=runner,
            )
        if tool == "cursor":
            return self.run_cursor(
                prompt,
                model=kwargs.get("model"),
                reasoning_effort=kwargs.get("reasoning_effort"),
                runner=runner,
            )
        raise ValueError(f"Unknown tool: {tool}")

    def _run_subprocess(
        self,
        tool: ToolName | Literal["cursor"],
        cmd: list[str],
        *,
        stdin: str | None = None,
        parse_jsonl: bool = False,
        runner: SubprocessRunner = subprocess.run,
        logged_prompt: str | None = None,
    ) -> AgentResult:
        operation = self.operation or f"{tool}.run"
        if logged_prompt is not None:
            prompt = logged_prompt
            command_for_log = list(cmd)
        else:
            prompt = cmd[-1] if cmd else ""
            if prompt == "-" and stdin is not None:
                prompt = stdin
            command_for_log = [*cmd[:-1], "<prompt>"] if cmd else []
        log_payload: dict[str, Any] = {
            "tool": tool,
            "command": command_for_log,
            "prompt": prompt,
            "stdin": stdin,
            "parse_jsonl": parse_jsonl,
            "cwd": str(self.workspace),
            "execution_workspace": str(self.workspace),
            "isolation_mode": "ephemeral",
        }
        if self.project_root is not None:
            log_payload["project_root"] = str(self.project_root)
        if self.operation:
            log_payload["operation"] = self.operation
        self._log_session("llm_request", operation, log_payload)
        try:
            proc = runner(
                cmd,
                input=stdin,
                text=True,
                cwd=str(self.workspace),
                env=self.env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.timeout,
                check=False,
            )
        except FileNotFoundError:
            result = AgentResult(
                tool=tool,
                command=cmd,
                returncode=127,
                stdout="",
                stderr="",
                error=f"CLI not found: {cmd[0]}",
            )
            self._log_agent_result(operation, result)
            return result
        except PermissionError:
            result = AgentResult(
                tool=tool,
                command=cmd,
                returncode=126,
                stdout="",
                stderr="",
                error=f"Permission denied running {cmd[0]}",
            )
            self._log_agent_result(operation, result)
            return result
        except subprocess.TimeoutExpired:
            result = AgentResult(
                tool=tool,
                command=cmd,
                returncode=124,
                stdout="",
                stderr="",
                error=f"Timeout after {self.timeout}s",
            )
            self._log_agent_result(operation, result)
            return result

        stdout: str = proc.stdout or ""
        stderr: str = proc.stderr or ""

        events: list[dict] | None = None
        if parse_jsonl and stdout:
            events = []
            for line in stdout.splitlines():
                if not line:
                    continue
                try:
                    parsed = json.loads(line)
                except json.JSONDecodeError:
                    events.append({"type": "raw", "message": line})
                else:
                    if isinstance(parsed, dict):
                        events.append(parsed)
                    else:
                        events.append({"type": "raw", "message": line})

        error: str | None = None
        if proc.returncode != 0:
            error = _failure_message_from_output(stdout, stderr, events)
        elif not stdout and stderr:
            error = "stdout vazio"

        result = AgentResult(
            tool=tool,
            command=cmd,
            returncode=proc.returncode,
            stdout=stdout,
            stderr=stderr,
            events=events,
            error=error,
        )
        self._log_agent_result(operation, result)
        return result

    @staticmethod
    def _build_codex_stdin(prompt: str, extra_context: str | None) -> str:
        context = (extra_context or "").strip()
        if not context:
            return prompt
        return f"{context}\n\n{prompt}"

    def _log_agent_result(self, operation: str, result: AgentResult) -> None:
        self._log_session(
            "llm_response",
            operation,
            {
                "tool": result.tool,
                "command": result.command,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "events": result.events,
                "error": result.error,
            },
        )

    def _log_session(
        self,
        event_type: str,
        operation: str,
        payload: dict[str, Any],
    ) -> None:
        if self.session_logger is None:
            return
        self.session_logger.safe_write(event_type, operation, payload)


__all__ = ["AgentWrapper", "SimpleNamespace"]
