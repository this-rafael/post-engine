"""Workspace isolado por execucao LLM.

Cria um diretorio temporario por chamada, copia apenas artefatos
explicitamente declarados, rejeita caminhos fora da allowlist,
impede symlinks e travessia (``..``), e limpa o diretorio ao final.
"""
from __future__ import annotations

import shutil
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

_DENYLIST_DIRNAMES: frozenset[str] = frozenset({
    ".git",
    ".data",
    ".venv",
    "__pycache__",
    "node_modules",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
})

_DENYLIST_FILENAMES: frozenset[str] = frozenset({
    ".env",
    ".env.local",
    ".env.production",
})


class WorkspaceIsolationError(Exception):
    """Erro de violacao de isolamento do workspace LLM."""


@dataclass(frozen=True)
class WorkspaceManifest:
    operation: str
    allowed_files: tuple[Path, ...] = ()
    extra_metadata: dict[str, Any] = field(default_factory=dict)

    def to_log_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "allowed_files": [str(f) for f in self.allowed_files],
            "metadata": dict(self.extra_metadata),
        }


def _validate_path(candidate: Path, *, base: Path) -> Path:
    resolved = candidate.resolve()
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise WorkspaceIsolationError(
            f"Caminho fora do workspace: {candidate}"
        ) from exc
    if candidate.is_symlink():
        raise WorkspaceIsolationError(
            f"Symlinks nao permitidos: {candidate}"
        )
    parts = resolved.parts
    for part in parts:
        if part == "..":
            raise WorkspaceIsolationError(
                f"Travessia de diretorio nao permitida: {candidate}"
            )
    return resolved


def _is_denied(path: Path) -> bool:
    if path.name in _DENYLIST_FILENAMES:
        return True
    for parent in (path, *path.parents):
        if parent.name in _DENYLIST_DIRNAMES:
            return True
    return False


@dataclass
class LlmExecutionWorkspace:
    """Diretorio temporario isolado para execucao de um agente LLM.

    Use :meth:`create` para construir e :meth:`destroy` para limpar.
    Ou use o context manager :func:`isolated_workspace`.
    """

    path: Path
    operation: str
    manifest: WorkspaceManifest
    project_root: Path | None = None
    _persistent: bool = False

    @classmethod
    def create(
        cls,
        operation: str,
        *,
        allowed_files: list[Path] | None = None,
        project_root: Path | None = None,
        persistent: bool = False,
        base_tmp_dir: Path | None = None,
    ) -> LlmExecutionWorkspace:
        files = list(allowed_files or [])
        manifest = WorkspaceManifest(
            operation=operation,
            allowed_files=tuple(files),
        )
        parent = str(base_tmp_dir) if base_tmp_dir else None
        tmp_dir = Path(tempfile.mkdtemp(prefix=f"llm-{operation}-", dir=parent))
        ws = cls(
            path=tmp_dir,
            operation=operation,
            manifest=manifest,
            project_root=project_root,
            _persistent=persistent,
        )
        for src in files:
            ws._copy_allowed(src)
        return ws

    def destroy(self) -> None:
        if self._persistent:
            return
        if self.path.exists():
            shutil.rmtree(self.path, ignore_errors=True)

    def _copy_allowed(self, source: Path) -> Path:
        source = Path(source)
        if not source.exists():
            raise WorkspaceIsolationError(
                f"Arquivo permitido nao existe: {source}"
            )
        if _is_denied(source):
            raise WorkspaceIsolationError(
                f"Arquivo na denylist: {source}"
            )
        if source.is_symlink():
            raise WorkspaceIsolationError(
                f"Symlinks nao permitidos: {source}"
            )
        dest = self.path / source.name
        dest_resolved = dest.resolve()
        try:
            dest_resolved.relative_to(self.path.resolve())
        except ValueError as exc:
            raise WorkspaceIsolationError(
                f"Caminho de destino fora do workspace: {dest}"
            ) from exc
        if source.is_file():
            shutil.copy2(str(source), str(dest))
        elif source.is_dir():
            shutil.copytree(
                str(source),
                str(dest),
                symlinks=False,
                ignore=shutil.ignore_patterns(*_DENYLIST_DIRNAMES),
            )
        return dest

    def to_log_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "execution_workspace": str(self.path),
            "isolation_mode": "persistent" if self._persistent else "ephemeral",
        }
        result.update(self.manifest.to_log_dict())
        if self.project_root is not None:
            result["project_root"] = str(self.project_root)
        return result


@contextmanager
def isolated_workspace(
    operation: str,
    *,
    allowed_files: list[Path] | None = None,
    project_root: Path | None = None,
    persistent: bool = False,
    base_tmp_dir: Path | None = None,
) -> Iterator[LlmExecutionWorkspace]:
    ws = LlmExecutionWorkspace.create(
        operation,
        allowed_files=allowed_files,
        project_root=project_root,
        persistent=persistent,
        base_tmp_dir=base_tmp_dir,
    )
    try:
        yield ws
    finally:
        ws.destroy()


OPERATION_ALLOWED_FILES: dict[str, frozenset[str]] = {
    "interview_exploration": frozenset(),
    "interview_validation": frozenset(),
    "interview_evaluation": frozenset(),
    "post_generate": frozenset(),
    "post_evaluate": frozenset(),
    "segment": frozenset(),
    "adjust_segment": frozenset(),
    "adjust_segments_bulk": frozenset(),
    "editorial_storyboard": frozenset(),
    "editorial_block_draft": frozenset(),
    "editorial_compose": frozenset(),
    "slidemark_convert": frozenset(),
}


def allowed_files_for_operation(operation: str) -> list[Path]:
    return []


__all__ = [
    "LlmExecutionWorkspace",
    "WorkspaceIsolationError",
    "WorkspaceManifest",
    "isolated_workspace",
    "allowed_files_for_operation",
    "OPERATION_ALLOWED_FILES",
]
