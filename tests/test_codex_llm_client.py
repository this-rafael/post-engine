"""Testes do CodexLlmClient: invocação do codex exec via stdin com --skip-git-repo-check."""
from __future__ import annotations

import json
import subprocess
from types import SimpleNamespace

import pytest

from content_engine.codex_llm_client import (
    CodexLlmClient,
    LlmRequest,
    LlmResponse,
)
from content_engine.schemas import AgentResult


def _ok(stdout: str = "", stderr: str = "", returncode: int = 0) -> SimpleNamespace:
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def _capture_runner(captured: dict) -> object:
    def _runner(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return _ok(stdout="resposta", stderr="")

    return _runner


def test_llm_request_defaults() -> None:
    req = LlmRequest(user_prompt="ola")
    assert req.user_prompt == "ola"
    assert req.system_prompt == ""
    assert req.model is None
    assert req.reasoning_effort == "medium"
    assert req.metadata == {}


def test_llm_response_from_json() -> None:
    resp = LlmResponse.from_json('{"a":1}', {"a": 1})
    assert resp.text == '{"a":1}'
    assert resp.json_data == {"a": 1}


def test_llm_response_from_text() -> None:
    resp = LlmResponse.from_text("texto puro")
    assert resp.text == "texto puro"
    assert resp.json_data is None


def test_build_prompt_concatena_system_e_user() -> None:
    client = CodexLlmClient()
    req = LlmRequest(system_prompt="SYSTEM", user_prompt="USER")
    assert client._build_prompt(req) == "SYSTEM\n\nUSER"


def test_build_prompt_ignora_vazios() -> None:
    client = CodexLlmClient()
    req = LlmRequest(system_prompt="  ", user_prompt="USER")
    assert client._build_prompt(req) == "USER"


def test_execute_codex_monta_comando_com_skip_git_e_stdin() -> None:
    captured: dict = {}
    client = CodexLlmClient(workspace="/tmp/ws", runner=_capture_runner(captured))
    client._execute_codex("prompt", "gpt-5.5", "xhigh")
    cmd = captured["args"][0]
    assert cmd[0] == "codex"
    assert "exec" in cmd
    assert "--skip-git-repo-check" in cmd
    assert "--ignore-user-config" in cmd
    assert "--ephemeral" in cmd
    assert "-m" in cmd
    i = cmd.index("-m")
    assert cmd[i + 1] == "gpt-5.5"
    assert "-c" in cmd
    j = cmd.index("-c")
    assert 'model_reasoning_effort="xhigh"' in cmd[j + 1]
    assert cmd[-1] == "-"
    assert captured["kwargs"]["input"] == "prompt"
    assert captured["kwargs"]["text"] is True
    assert captured["kwargs"]["check"] is False


def test_execute_codex_sem_model_nao_adiciona_flag_m() -> None:
    captured: dict = {}
    client = CodexLlmClient(workspace="/tmp/ws", runner=_capture_runner(captured))
    client._execute_codex("prompt", None, "medium")
    cmd = captured["args"][0]
    assert "-m" not in cmd
    assert "--model" not in cmd


def test_execute_codex_inclui_cd_workspace() -> None:
    captured: dict = {}
    client = CodexLlmClient(workspace="/tmp/ws", runner=_capture_runner(captured))
    client._execute_codex("prompt", None, "medium")
    cmd = captured["args"][0]
    assert "--cd" in cmd
    i = cmd.index("--cd")
    assert cmd[i + 1] == "/tmp/ws"


def test_execute_codex_sem_workspace_cria_workspace_isolado() -> None:
    captured: dict = {}
    client = CodexLlmClient(runner=_capture_runner(captured))
    try:
        client._execute_codex("prompt", None, "medium")
        cmd = captured["args"][0]
        assert "--cd" in cmd
        i = cmd.index("--cd")
        ws_path = cmd[i + 1]
        assert "llm-codex.exec" in ws_path
        assert client.workspace is not None
        assert str(client.workspace) == ws_path
    finally:
        client.close()


def test_complete_retorna_json_quando_valido() -> None:
    payload = '{"perguntas": [{"pergunta": "q?"}]}'
    runner = lambda *a, **k: _ok(stdout=payload, stderr="")  # noqa: E731
    client = CodexLlmClient(workspace="/tmp/ws", runner=runner)
    resp = client.complete(LlmRequest(user_prompt="p", model="gpt-5.5"))
    assert resp.json_data == json.loads(payload)
    assert resp.text == payload


def test_complete_retorna_texto_quando_json_invalido() -> None:
    runner = lambda *a, **k: _ok(stdout="texto nao json", stderr="")  # noqa: E731
    client = CodexLlmClient(workspace="/tmp/ws", runner=runner)
    resp = client.complete(LlmRequest(user_prompt="p"))
    assert resp.json_data is None
    assert resp.text == "texto nao json"


def test_execute_codex_erro_exit_code_nao_zero_levanta_runtime_error() -> None:
    runner = lambda *a, **k: _ok(stdout="", stderr="modelo invalido", returncode=2)  # noqa: E731
    client = CodexLlmClient(workspace="/tmp/ws", runner=runner)
    with pytest.raises(RuntimeError, match="exit code 2"):
        client._execute_codex("prompt", "invalido", "medium")


def test_execute_codex_filenotfound_levanta_runtime_error() -> None:
    def _raise_fnf(*a, **k):
        raise FileNotFoundError("nope")

    client = CodexLlmClient(workspace="/tmp/ws", runner=_raise_fnf)
    with pytest.raises(RuntimeError, match="Falha ao executar codex"):
        client._execute_codex("prompt", None, "medium")


def test_execute_codex_timeout_levanta_runtime_error() -> None:
    def _raise_timeout(*a, **k):
        raise subprocess.TimeoutExpired(cmd=["codex"], timeout=600)

    client = CodexLlmClient(workspace="/tmp/ws", timeout_seconds=600, runner=_raise_timeout)
    with pytest.raises(RuntimeError, match="Timeout"):
        client._execute_codex("prompt", None, "medium")


def test_run_retorna_agent_result_ok_em_sucesso() -> None:
    payload = '{"perguntas": [{"pergunta": "q?"}]}'
    runner = lambda *a, **k: _ok(stdout=payload, stderr="")  # noqa: E731
    client = CodexLlmClient(workspace="/tmp/ws", runner=runner)
    result = client.run("codex", "prompt", model="gpt-5.5", sandbox="read-only", json_output=False)
    assert isinstance(result, AgentResult)
    assert result.ok is True
    assert result.stdout == payload
    assert result.error is None


def test_run_retorna_agent_result_erro_em_falha() -> None:
    runner = lambda *a, **k: _ok(stdout="", stderr="modelo nao suportado", returncode=2)  # noqa: E731
    client = CodexLlmClient(workspace="/tmp/ws", runner=runner)
    result = client.run("codex", "prompt", model="invalido", sandbox="read-only")
    assert result.ok is False
    assert result.returncode == 1
    assert "exit code 2" in (result.error or "")


def test_run_passa_model_do_kwargs_para_o_comando() -> None:
    captured: dict = {}
    runner = _capture_runner(captured)
    client = CodexLlmClient(workspace="/tmp/ws", runner=runner)
    client.run("codex", "prompt", model="gpt-5.5", sandbox="read-only", json_output=False)
    cmd = captured["args"][0]
    i = cmd.index("-m")
    assert cmd[i + 1] == "gpt-5.5"


def test_run_sem_model_herde_do_cli() -> None:
    captured: dict = {}
    runner = _capture_runner(captured)
    client = CodexLlmClient(workspace="/tmp/ws", runner=runner)
    client.run("codex", "prompt", model=None, sandbox="read-only", json_output=False)
    cmd = captured["args"][0]
    assert "-m" not in cmd
    assert "--model" not in cmd
