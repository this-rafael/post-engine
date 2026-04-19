"""Teste de integracao: agente nao consegue ler arquivos do projeto.

Simula um CLI falso que tenta ler um arquivo conhecido do projeto
e confirma que esse arquivo nao existe no workspace de execucao.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from content_engine.agent_wrapper import AgentWrapper
from content_engine.codex_llm_client import CodexLlmClient
from content_engine.llm_workspace import LlmExecutionWorkspace


def _ok(stdout: str = "", stderr: str = "", returncode: int = 0) -> SimpleNamespace:
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def test_agent_wrapper_workspace_is_not_project_root(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "secret.txt").write_text("SECRET_DATA")
    (project / ".env").write_text("API_KEY=xxx")
    (project / ".git").mkdir()
    (project / ".git" / "HEAD").write_text("ref")
    (project / "src").mkdir()
    (project / "src" / "main.py").write_text("code")

    ws = LlmExecutionWorkspace.create(
        "integration_test",
        project_root=project,
        base_tmp_dir=tmp_path,
    )
    try:
        wrapper = AgentWrapper(
            workspace=ws.path,
            project_root=project,
            operation="integration_test",
        )
        assert wrapper.workspace != project
        assert wrapper.workspace != wrapper.project_root
        assert not (wrapper.workspace / "secret.txt").exists()
        assert not (wrapper.workspace / ".env").exists()
        assert not (wrapper.workspace / ".git").exists()
        assert not (wrapper.workspace / "src").exists()
        assert list(wrapper.workspace.iterdir()) == []
    finally:
        ws.destroy()


def test_agent_wrapper_subprocess_receives_isolated_cwd(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "secret.txt").write_text("SECRET")

    ws = LlmExecutionWorkspace.create(
        "test_op",
        project_root=project,
        base_tmp_dir=tmp_path,
    )
    try:
        captured: dict = {}

        def runner(*args, **kwargs):
            captured["cwd"] = kwargs.get("cwd")
            return _ok(stdout="ok")

        wrapper = AgentWrapper(
            workspace=ws.path,
            project_root=project,
            operation="test_op",
        )
        wrapper.run_codex("prompt", runner=runner)
        assert captured["cwd"] == str(ws.path)
        assert captured["cwd"] != str(project)
    finally:
        ws.destroy()


def test_codex_llm_client_creates_isolated_workspace(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "secret.txt").write_text("SECRET")

    captured: dict = {}

    def runner(*args, **kwargs):
        captured["cwd"] = kwargs.get("cwd")
        captured["cmd"] = args[0]
        return _ok(stdout='{"ok": true}')

    client = CodexLlmClient(
        project_root=project,
        runner=runner,
    )
    try:
        assert client.workspace is not None
        assert client.workspace != project
        assert not (client.workspace / "secret.txt").exists()
        from content_engine.codex_llm_client import LlmRequest
        client.complete(LlmRequest(user_prompt="test"))
        assert captured["cwd"] == str(client.workspace)
        assert captured["cwd"] != str(project)
        cmd = captured["cmd"]
        assert "--cd" in cmd
        i = cmd.index("--cd")
        assert cmd[i + 1] == str(client.workspace)
    finally:
        client.close()


def test_workspace_isolation_prevents_traversal_in_destination(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    allowed_file = project / "input.txt"
    allowed_file.write_text("data")

    ws = LlmExecutionWorkspace.create(
        "test_op",
        project_root=project,
        base_tmp_dir=tmp_path,
    )
    try:
        dest = ws._copy_allowed(allowed_file)
        assert dest.parent == ws.path
        assert dest.exists()
        assert not (ws.path / ".." / "outside.txt").exists()
    finally:
        ws.destroy()


def test_full_isolation_chain(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "config.yml").write_text("key: value")
    (project / ".env").write_text("SECRET=1")
    (project / ".git").mkdir()
    (project / "tests").mkdir()
    (project / "tests" / "test_main.py").write_text("test")

    ws = LlmExecutionWorkspace.create(
        "full_chain",
        project_root=project,
        base_tmp_dir=tmp_path,
    )
    try:
        wrapper = AgentWrapper(
            workspace=ws.path,
            project_root=project,
            operation="full_chain",
        )
        assert wrapper.workspace == ws.path
        assert wrapper.project_root == project
        assert wrapper.workspace != wrapper.project_root
        ws_contents = set(p.name for p in wrapper.workspace.iterdir())
        assert ws_contents == set()
        log_dict = ws.to_log_dict()
        assert log_dict["execution_workspace"] == str(ws.path)
        assert log_dict["project_root"] == str(project)
        assert log_dict["isolation_mode"] == "ephemeral"
    finally:
        ws.destroy()
