"""CodexLlmClient: cliente LLM via Codex CLI.

Tradução fiel do CodexLlmClient Java (com.app.infrastructure.llm).

Invoca ``codex exec`` com:
- ``--skip-git-repo-check`` (permite rodar fora de um repo git);
- ``--ignore-user-config`` (isola configuração do usuário);
- prompt via stdin (``-`` como argumento posicional);
- ``-m model`` para modelo dedicado;
- ``-c model_reasoning_effort="..."`` para esforço de raciocínio;
- leitura concorrente de stdout/stderr via threads (evita deadlock);
- timeout e validação de exit code.

Compatível com o protocolo ``_LLMRunner`` do ``QuestionGenerator`` via
``run(tool, prompt, **kwargs) -> AgentResult``.
"""
from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import threading
import weakref
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from content_engine.schemas import AgentResult
from content_engine.session_log import SessionLogger

DEFAULT_TIMEOUT_SECONDS = 600
DEFAULT_REASONING_EFFORT = "medium"

_log = logging.getLogger(__name__)

SubprocessRunner = Callable[..., Any]


@dataclass(frozen=True)
class LlmRequest:
    system_prompt: str = ""
    user_prompt: str = ""
    model: str | None = None
    reasoning_effort: str = DEFAULT_REASONING_EFFORT
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LlmResponse:
    text: str
    json_data: Any = None

    @classmethod
    def from_json(cls, text: str, json_data: Any) -> "LlmResponse":
        return cls(text=text, json_data=json_data)

    @classmethod
    def from_text(cls, text: str) -> "LlmResponse":
        return cls(text=text, json_data=None)


class CodexLlmClient:
    def __init__(
        self,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        workspace: str | Path | None = None,
        env: dict[str, str] | None = None,
        runner: SubprocessRunner | None = None,
        session_logger: SessionLogger | None = None,
        *,
        project_root: str | Path | None = None,
        operation: str = "codex.exec",
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.project_root: Path | None = (
            Path(project_root).resolve() if project_root else None
        )
        self.operation: str = operation
        self._owns_workspace: bool = False
        if workspace is not None:
            self.workspace: Path | None = Path(workspace).resolve()
        else:
            from content_engine.llm_workspace import LlmExecutionWorkspace

            self._ws = LlmExecutionWorkspace.create(
                operation,
                project_root=self.project_root,
            )
            self.workspace = self._ws.path
            self._owns_workspace = True
            weakref.finalize(self, self._cleanup_workspace, self.workspace)
        merged: dict[str, str] = dict(os.environ)
        if env is not None:
            merged.update(env)
        self.env: dict[str, str] = merged
        self._runner: SubprocessRunner | None = runner
        self.session_logger: SessionLogger | None = session_logger

    @staticmethod
    def _cleanup_workspace(path: Path | None) -> None:
        if path is not None and path.exists():
            shutil.rmtree(path, ignore_errors=True)

    def close(self) -> None:
        if self._owns_workspace and self.workspace and self.workspace.exists():
            shutil.rmtree(self.workspace, ignore_errors=True)

    def complete(self, request: LlmRequest) -> LlmResponse:
        stage = (
            str(request.metadata.get("stage", "unknown"))
            if request.metadata
            else "unknown"
        )
        model = request.model if request.model else "default"
        reasoning_effort = request.reasoning_effort
        _log.info(
            "[CodexLLM] Chamada - stage: %s, model: %s, reasoning: %s",
            stage,
            model,
            reasoning_effort,
        )

        prompt = self._build_prompt(request)
        response_text = self._execute_codex(prompt, request.model, reasoning_effort)

        try:
            json_data = json.loads(response_text)
            return LlmResponse.from_json(response_text, json_data)
        except (json.JSONDecodeError, ValueError):
            _log.debug("[CodexLLM] Resposta nao e JSON valido, retornando como texto")
            return LlmResponse.from_text(response_text)

    def _build_prompt(self, request: LlmRequest) -> str:
        parts: list[str] = []
        if request.system_prompt and request.system_prompt.strip():
            parts.append(request.system_prompt)
        if request.user_prompt and request.user_prompt.strip():
            parts.append(request.user_prompt)
        return "\n\n".join(parts).strip()

    def _execute_codex(
        self,
        prompt: str,
        model: str | None,
        reasoning_effort: str,
    ) -> str:
        command: list[str] = [
            "codex",
            "exec",
            "--ephemeral",
            "--skip-git-repo-check",
            "--ignore-user-config",
        ]
        if self.workspace is not None:
            command += ["--cd", str(self.workspace)]
        if model and model.strip():
            command += ["-m", model]
        command += ["-c", f'model_reasoning_effort="{reasoning_effort}"']
        command.append("-")

        _log.info(
            "[CodexLLM] Executando codex exec (prompt com %d chars, model: %s, "
            "reasoning: %s)...",
            len(prompt),
            model,
            reasoning_effort,
        )
        log_payload: dict[str, Any] = {
            "tool": "codex",
            "command": command,
            "prompt": prompt,
            "model": model,
            "reasoning_effort": reasoning_effort,
            "execution_workspace": str(self.workspace) if self.workspace else None,
            "isolation_mode": "ephemeral" if self._owns_workspace else "external",
            "operation": self.operation,
        }
        if self.project_root is not None:
            log_payload["project_root"] = str(self.project_root)
        self._log_session("llm_request", self.operation, log_payload)

        if self._runner is not None:
            return self._execute_via_runner(command, prompt)

        return self._execute_via_popen(command, prompt)

    def _execute_via_runner(self, command: list[str], prompt: str) -> str:
        try:
            proc = self._runner(  # type: ignore[misc]
                command,
                input=prompt,
                text=True,
                cwd=str(self.workspace) if self.workspace else None,
                env=self.env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.timeout_seconds,
                check=False,
            )
        except FileNotFoundError as exc:
            self._log_codex_response(command, "", "", 127, str(exc))
            raise RuntimeError(f"[CodexLLM] Falha ao executar codex: {exc}") from exc
        except subprocess.TimeoutExpired as exc:
            self._log_codex_response(
                command,
                "",
                str(exc),
                124,
                f"Timeout apos {self.timeout_seconds} segundos",
            )
            raise RuntimeError(
                f"[CodexLLM] Timeout apos {self.timeout_seconds} segundos"
            ) from exc

        stdout: str = (proc.stdout or "").strip()
        stderr: str = (proc.stderr or "").strip()
        exit_code = proc.returncode

        if exit_code != 0:
            _log.error(
                "[CodexLLM] Codex falhou com exit code %d. Stderr: %s",
                exit_code,
                stderr,
            )
            self._log_codex_response(
                command,
                stdout,
                stderr,
                exit_code,
                f"Codex falhou com exit code {exit_code}: {stderr}",
            )
            raise RuntimeError(
                f"[CodexLLM] Codex falhou com exit code {exit_code}: {stderr}"
            )

        _log.info("[CodexLLM] Resposta recebida (%d chars)", len(stdout))
        self._log_codex_response(command, stdout, stderr, exit_code, None)
        return stdout

    def _execute_via_popen(self, command: list[str], prompt: str) -> str:
        try:
            proc = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(self.workspace) if self.workspace else None,
                env=self.env,
            )
        except FileNotFoundError as exc:
            self._log_codex_response(command, "", "", 127, str(exc))
            raise RuntimeError(f"[CodexLLM] Falha ao executar codex: {exc}") from exc

        stdout_buf: list[str] = []
        stderr_buf: list[str] = []

        def _read_stdout() -> None:
            assert proc.stdout is not None
            try:
                for line in proc.stdout:
                    stdout_buf.append(line)
            except Exception as exc:
                _log.error("[CodexLLM] Erro ao ler stdout: %s", exc)

        def _read_stderr() -> None:
            assert proc.stderr is not None
            try:
                for line in proc.stderr:
                    stderr_buf.append(line)
                    _log.debug("[CodexLLM] stderr: %s", line.rstrip())
            except Exception as exc:
                _log.error("[CodexLLM] Erro ao ler stderr: %s", exc)

        stdout_thread = threading.Thread(target=_read_stdout, daemon=True)
        stderr_thread = threading.Thread(target=_read_stderr, daemon=True)
        stdout_thread.start()
        stderr_thread.start()

        try:
            assert proc.stdin is not None
            proc.stdin.write(prompt)
            proc.stdin.flush()
            proc.stdin.close()
        except BrokenPipeError:
            pass
        except Exception as exc:
            _log.error("[CodexLLM] Erro ao escrever stdin: %s", exc)

        try:
            exit_code = proc.wait(timeout=self.timeout_seconds)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            stdout = "".join(stdout_buf).strip()
            stderr = "".join(stderr_buf).strip()
            self._log_codex_response(
                command,
                stdout,
                stderr,
                124,
                f"Timeout apos {self.timeout_seconds} segundos",
            )
            raise RuntimeError(
                f"[CodexLLM] Timeout apos {self.timeout_seconds} segundos"
            )

        stdout_thread.join(timeout=5)
        stderr_thread.join(timeout=5)

        stdout = "".join(stdout_buf).strip()
        stderr = "".join(stderr_buf).strip()

        if exit_code != 0:
            _log.error(
                "[CodexLLM] Codex falhou com exit code %d. Stderr: %s",
                exit_code,
                stderr,
            )
            self._log_codex_response(
                command,
                stdout,
                stderr,
                exit_code,
                f"Codex falhou com exit code {exit_code}: {stderr}",
            )
            raise RuntimeError(
                f"[CodexLLM] Codex falhou com exit code {exit_code}: {stderr}"
            )

        _log.info("[CodexLLM] Resposta recebida (%d chars)", len(stdout))
        self._log_codex_response(command, stdout, stderr, exit_code, None)
        return stdout

    def _log_codex_response(
        self,
        command: list[str],
        stdout: str,
        stderr: str,
        returncode: int,
        error: str | None,
    ) -> None:
        self._log_session(
            "llm_response",
            "codex.exec",
            {
                "tool": "codex",
                "command": command,
                "returncode": returncode,
                "stdout": stdout,
                "stderr": stderr,
                "error": error,
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

    def run(self, tool: str, prompt: str, **kwargs: Any) -> AgentResult:
        """Compatível com o protocolo ``_LLMRunner`` do ``QuestionGenerator``."""
        model = kwargs.get("model")
        reasoning_effort = kwargs.get("reasoning_effort", DEFAULT_REASONING_EFFORT)
        stage = str(kwargs.get("stage", "questions"))
        request = LlmRequest(
            user_prompt=prompt,
            model=model if isinstance(model, str) else None,
            reasoning_effort=reasoning_effort,
            metadata={"stage": stage},
        )
        try:
            response = self.complete(request)
        except RuntimeError as exc:
            return AgentResult(
                tool=tool,
                command=["codex", "exec"],
                returncode=1,
                stdout="",
                stderr=str(exc),
                error=str(exc),
            )
        return AgentResult(
            tool=tool,
            command=["codex", "exec"],
            returncode=0,
            stdout=response.text,
            stderr="",
            error=None,
        )


__all__ = ["CodexLlmClient", "LlmRequest", "LlmResponse"]
