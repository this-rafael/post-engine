"""Testes unitarios para LlmExecutionWorkspace."""
from __future__ import annotations

from pathlib import Path

import pytest

from content_engine.llm_workspace import (
    LlmExecutionWorkspace,
    WorkspaceIsolationError,
    WorkspaceManifest,
    allowed_files_for_operation,
    isolated_workspace,
)


def test_create_creates_temp_directory(tmp_path: Path) -> None:
    ws = LlmExecutionWorkspace.create("test_op", base_tmp_dir=tmp_path)
    try:
        assert ws.path.exists()
        assert ws.path.is_dir()
        assert ws.operation == "test_op"
        assert ws.path.name.startswith("llm-test_op-")
    finally:
        ws.destroy()


def test_destroy_removes_directory(tmp_path: Path) -> None:
    ws = LlmExecutionWorkspace.create("test_op", base_tmp_dir=tmp_path)
    path = ws.path
    assert path.exists()
    ws.destroy()
    assert not path.exists()


def test_destroy_persistent_keeps_directory(tmp_path: Path) -> None:
    ws = LlmExecutionWorkspace.create(
        "test_op", base_tmp_dir=tmp_path, persistent=True
    )
    path = ws.path
    ws.destroy()
    assert path.exists()
    import shutil
    shutil.rmtree(path)


def test_copy_allowed_file(tmp_path: Path) -> None:
    src = tmp_path / "input.txt"
    src.write_text("hello")
    ws = LlmExecutionWorkspace.create(
        "test_op",
        allowed_files=[src],
        base_tmp_dir=tmp_path,
    )
    try:
        copied = ws.path / "input.txt"
        assert copied.exists()
        assert copied.read_text() == "hello"
    finally:
        ws.destroy()


def test_copy_denied_file_raises(tmp_path: Path) -> None:
    src = tmp_path / ".env"
    src.write_text("SECRET=1")
    with pytest.raises(WorkspaceIsolationError, match="denylist"):
        LlmExecutionWorkspace.create(
            "test_op",
            allowed_files=[src],
            base_tmp_dir=tmp_path,
        )


def test_copy_from_denied_directory_raises(tmp_path: Path) -> None:
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    src = git_dir / "config"
    src.write_text("data")
    with pytest.raises(WorkspaceIsolationError, match="denylist"):
        LlmExecutionWorkspace.create(
            "test_op",
            allowed_files=[src],
            base_tmp_dir=tmp_path,
        )


def test_symlink_rejected(tmp_path: Path) -> None:
    real = tmp_path / "real.txt"
    real.write_text("data")
    link = tmp_path / "link.txt"
    link.symlink_to(real)
    with pytest.raises(WorkspaceIsolationError, match="Symlinks"):
        LlmExecutionWorkspace.create(
            "test_op",
            allowed_files=[link],
            base_tmp_dir=tmp_path,
        )


def test_nonexistent_file_raises(tmp_path: Path) -> None:
    with pytest.raises(WorkspaceIsolationError, match="nao existe"):
        LlmExecutionWorkspace.create(
            "test_op",
            allowed_files=[tmp_path / "nope.txt"],
            base_tmp_dir=tmp_path,
        )


def test_isolated_workspace_context_manager(tmp_path: Path) -> None:
    with isolated_workspace("op", base_tmp_dir=tmp_path) as ws:
        path = ws.path
        assert path.exists()
        assert ws.operation == "op"
    assert not path.exists()


def test_isolated_workspace_cleanup_on_exception(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError):
        with isolated_workspace("op", base_tmp_dir=tmp_path) as ws:
            path = ws.path
            raise RuntimeError("boom")
    assert not path.exists()


def test_manifest_to_log_dict() -> None:
    manifest = WorkspaceManifest(
        operation="post_generate",
        allowed_files=(Path("/a.txt"),),
        extra_metadata={"key": "val"},
    )
    d = manifest.to_log_dict()
    assert d["operation"] == "post_generate"
    assert d["allowed_files"] == ["/a.txt"]
    assert d["metadata"] == {"key": "val"}


def test_workspace_to_log_dict(tmp_path: Path) -> None:
    ws = LlmExecutionWorkspace.create(
        "op",
        project_root=Path("/project"),
        base_tmp_dir=tmp_path,
    )
    try:
        d = ws.to_log_dict()
        assert d["operation"] == "op"
        assert d["isolation_mode"] == "ephemeral"
        assert d["project_root"] == "/project"
        assert "execution_workspace" in d
    finally:
        ws.destroy()


def test_workspace_persistent_log_mode(tmp_path: Path) -> None:
    ws = LlmExecutionWorkspace.create(
        "op",
        persistent=True,
        base_tmp_dir=tmp_path,
    )
    try:
        d = ws.to_log_dict()
        assert d["isolation_mode"] == "persistent"
    finally:
        ws.destroy()
        import shutil
        if ws.path.exists():
            shutil.rmtree(ws.path)


def test_allowed_files_for_operation_returns_empty_list() -> None:
    result = allowed_files_for_operation("post_generate")
    assert result == []


def test_destroy_idempotent(tmp_path: Path) -> None:
    ws = LlmExecutionWorkspace.create("op", base_tmp_dir=tmp_path)
    ws.destroy()
    ws.destroy()


def test_copy_allowed_directory(tmp_path: Path) -> None:
    src_dir = tmp_path / "data"
    src_dir.mkdir()
    (src_dir / "file.txt").write_text("content")
    ws = LlmExecutionWorkspace.create(
        "op",
        allowed_files=[src_dir],
        base_tmp_dir=tmp_path,
    )
    try:
        copied = ws.path / "data"
        assert copied.is_dir()
        assert (copied / "file.txt").read_text() == "content"
    finally:
        ws.destroy()


def test_copy_directory_ignores_denied_subdirs(tmp_path: Path) -> None:
    src_dir = tmp_path / "data"
    src_dir.mkdir()
    (src_dir / "file.txt").write_text("content")
    (src_dir / "__pycache__").mkdir()
    (src_dir / "__pycache__" / "mod.pyc").write_text("cache")
    ws = LlmExecutionWorkspace.create(
        "op",
        allowed_files=[src_dir],
        base_tmp_dir=tmp_path,
    )
    try:
        assert (ws.path / "data" / "file.txt").exists()
        assert not (ws.path / "data" / "__pycache__").exists()
    finally:
        ws.destroy()


def test_no_project_files_leak_into_workspace(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "secret.py").write_text("API_KEY = 'xxx'")
    (project / ".env").write_text("SECRET=val")
    (project / ".git").mkdir()
    (project / ".git" / "HEAD").write_text("ref")
    (project / "src").mkdir()
    (project / "src" / "main.py").write_text("code")
    (project / "tests").mkdir()
    (project / "tests" / "test_main.py").write_text("test")

    ws = LlmExecutionWorkspace.create("op", base_tmp_dir=tmp_path)
    try:
        assert not (ws.path / "secret.py").exists()
        assert not (ws.path / ".env").exists()
        assert not (ws.path / ".git").exists()
        assert not (ws.path / "src").exists()
        assert not (ws.path / "tests").exists()
        contents = list(ws.path.iterdir())
        assert contents == []
    finally:
        ws.destroy()
