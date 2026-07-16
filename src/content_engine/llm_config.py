"""Configuração de provider/modelo por operação LLM."""
from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from .schemas import SandboxPolicy, ToolName

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

LlmOperationId = Literal[
    "interview_questions",
    "interview_validate",
    "interview_evaluate",
    "interview_round_title",
    "interview_gap_diagnosis",
    "post_generate",
    "storyboard_generate",
    "block_approaches_generate",
    "block_draft_generate",
    "editorial_compose",
    "segment",
    "adjust_segment",
    "adjust_segments_bulk",
    "post_evaluate",
    "slidemark_export",
]

LLM_OPERATIONS: tuple[LlmOperationId, ...] = (
    "interview_questions",
    "interview_validate",
    "interview_evaluate",
    "interview_round_title",
    "interview_gap_diagnosis",
    "post_generate",
    "storyboard_generate",
    "block_approaches_generate",
    "block_draft_generate",
    "editorial_compose",
    "segment",
    "adjust_segment",
    "adjust_segments_bulk",
    "post_evaluate",
    "slidemark_export",
)

OPERATION_LABELS: dict[str, str] = {
    "interview_questions": "Exploração aberta da entrevista",
    "interview_validate": "Avaliação da qualidade das perguntas da entrevista",
    "interview_evaluate": "Avaliação de autoria da entrevista",
    "interview_round_title": "Geração de título da rodada da entrevista",
    "interview_gap_diagnosis": "Diagnóstico de lacunas da entrevista",
    "post_generate": "Geração de post",
    "storyboard_generate": "Storyboard narrativo",
    "block_approaches_generate": "Abordagens de bloco",
    "block_draft_generate": "Rascunho de bloco",
    "editorial_compose": "Composição editorial",
    "segment": "Segmentação",
    "adjust_segment": "Ajuste de segmento",
    "adjust_segments_bulk": "Ajuste em lote de segmentos",
    "post_evaluate": "Avaliação do post",
    "slidemark_export": "Export SlideMark",
}

# Chaves antigas em agent-config.yml / frontend pré-V4.
LEGACY_OPERATION_ALIASES: dict[str, str] = {
    "questions": "interview_questions",
    "answer_evaluate": "interview_evaluate",
    "content_generate": "post_generate",
}

DATA_DIR: Path = Path(__file__).resolve().parents[2] / ".data"
CONFIG_FILE: Path = DATA_DIR / "agent-config.yml"

DEFAULT_OPERATION_CONFIGS: dict[str, dict[str, Any]] = {
    "interview_questions": {
        "provider": "opencode",
        "model": "opencode-go/qwen3.7-plus",
        "reasoning_effort": "max",
        "sandbox": "read-only",
    },
    "interview_validate": {
        "provider": "opencode",
        "model": "opencode-go/glm-5.2",
        "reasoning_effort": "max",
        "sandbox": "read-only",
    },
    "interview_evaluate": {
        "provider": "cursor",
        "model": "auto",
        "sandbox": "read-only",
    },
    "interview_round_title": {
        "provider": "opencode",
        "model": "opencode-go/deepseek-r1",
        "reasoning_effort": "low",
        "sandbox": "read-only",
    },
    "interview_gap_diagnosis": {
        "provider": "opencode",
        "model": "opencode-go/deepseek-r1",
        "reasoning_effort": "low",
        "sandbox": "read-only",
    },
    "post_generate": {
        "provider": "codex",
        "model": "gpt-5.5",
        "reasoning_effort": "xhigh",
        "sandbox": "read-only",
    },
    "storyboard_generate": {
        "provider": "codex",
        "model": "gpt-5.6-terra",
        "reasoning_effort": "max",
        "sandbox": "read-only",
    },
    "block_approaches_generate": {
        "provider": "codex",
        "model": "gpt-5.6-luna",
        "reasoning_effort": "medium",
        "sandbox": "read-only",
    },
    "block_draft_generate": {
        "provider": "codex",
        "model": "gpt-5.6-terra",
        "reasoning_effort": "max",
        "sandbox": "read-only",
    },
    "editorial_compose": {
        "provider": "codex",
        "model": "gpt-5.6-sol",
        "reasoning_effort": "max",
        "sandbox": "read-only",
    },
    "segment": {
        "provider": "opencode",
        "model": "opencode-go/qwen3.6-plus",
        "reasoning_effort": "medium",
        "sandbox": "read-only",
    },
    "adjust_segment": {
        "provider": "opencode",
        "model": "opencode-go/qwen3.6-plus",
        "reasoning_effort": "max",
        "sandbox": "read-only",
    },
    "adjust_segments_bulk": {
        "provider": "cursor",
        "model": "auto",
        "sandbox": "read-only",
    },
    "post_evaluate": {
        "provider": "codex",
        "model": "gpt-5.6-terra",
        "reasoning_effort": "max",
        "sandbox": "read-only",
    },
    "slidemark_export": {
        "provider": "opencode",
        "model": "opencode-go/qwen3.6-plus",
        "reasoning_effort": "max",
        "sandbox": "read-only",
    },
}

PROVIDER_LABELS: dict[str, str] = {
    "codex": "Codex",
    "opencode": "OpenCode",
    "cursor": "Cursor",
}


@dataclass
class LlmOperationConfig:
    provider: ToolName = "codex"
    model: str | None = None
    agent: str | None = None
    reasoning_effort: str | None = None
    sandbox: SandboxPolicy | None = None
    timeout_seconds: int | None = None

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"provider": self.provider}
        if self.model is not None:
            payload["model"] = self.model
        if self.agent is not None:
            payload["agent"] = self.agent
        if self.reasoning_effort is not None:
            payload["reasoning_effort"] = self.reasoning_effort
        if self.sandbox is not None:
            payload["sandbox"] = self.sandbox
        if self.timeout_seconds is not None:
            payload["timeout_seconds"] = self.timeout_seconds
        return payload

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> "LlmOperationConfig":
        if not raw:
            return cls()
        provider_raw = raw.get("provider", raw.get("tool", "codex"))
        provider: ToolName = (
            provider_raw
            if provider_raw in {"codex", "opencode", "cursor"}
            else "codex"
        )
        sandbox_raw = raw.get("sandbox")
        sandbox: SandboxPolicy | None = (
            sandbox_raw
            if sandbox_raw in {"read-only", "workspace-write", "danger-full-access"}
            else None
        )
        timeout = raw.get("timeout_seconds")
        return cls(
            provider=provider,
            model=_optional_str(raw.get("model")),
            agent=_optional_str(raw.get("agent")),
            reasoning_effort=_optional_str(raw.get("reasoning_effort")),
            sandbox=sandbox,
            timeout_seconds=int(timeout) if isinstance(timeout, int) else None,
        )


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    return str(value)


def _merge_config(
    base: LlmOperationConfig,
    override: LlmOperationConfig | None,
) -> LlmOperationConfig:
    if override is None:
        return base
    return LlmOperationConfig(
        provider=override.provider or base.provider,
        model=override.model if override.model is not None else base.model,
        agent=override.agent if override.agent is not None else base.agent,
        reasoning_effort=(
            override.reasoning_effort
            if override.reasoning_effort is not None
            else base.reasoning_effort
        ),
        sandbox=override.sandbox if override.sandbox is not None else base.sandbox,
        timeout_seconds=(
            override.timeout_seconds
            if override.timeout_seconds is not None
            else base.timeout_seconds
        ),
    )


def _default_for_operation(operation: str) -> LlmOperationConfig:
    raw = DEFAULT_OPERATION_CONFIGS.get(operation, {"provider": "codex"})
    return LlmOperationConfig.from_dict(raw)


def list_operations() -> list[dict[str, str]]:
    return [
        {"id": op, "label": OPERATION_LABELS.get(op, op)}
        for op in LLM_OPERATIONS
    ]


def list_providers() -> list[dict[str, str]]:
    return [{"value": key, "label": label} for key, label in PROVIDER_LABELS.items()]


def check_provider_available(provider: str) -> bool:
    binary = {"codex": "codex", "opencode": "opencode", "cursor": "agent"}.get(provider)
    if not binary:
        return False
    return shutil.which(binary) is not None


def provider_status() -> list[dict[str, Any]]:
    return [
        {
            "id": provider["value"],
            "label": provider["label"],
            "available": check_provider_available(provider["value"]),
        }
        for provider in list_providers()
    ]


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_yaml_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return {}
    if yaml is None:
        raise RuntimeError("PyYAML is required to load agent-config.yml")
    loaded = yaml.safe_load(text)
    return loaded if isinstance(loaded, dict) else {}


def _dump_yaml_file(path: Path, payload: dict[str, Any]) -> None:
    _ensure_data_dir()
    if yaml is None:
        raise RuntimeError("PyYAML is required to save agent-config.yml")
    path.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _normalize_operations_raw(raw: dict[str, Any]) -> dict[str, Any]:
    """Mapeia aliases legados para ids atuais sem sobrescrever chaves novas."""
    normalized = dict(raw)
    for legacy, modern in LEGACY_OPERATION_ALIASES.items():
        if modern not in normalized and legacy in normalized:
            normalized[modern] = normalized[legacy]
    for legacy in LEGACY_OPERATION_ALIASES:
        normalized.pop(legacy, None)
    return normalized


def _config_file_needs_migration(operations_raw: dict[str, Any]) -> bool:
    return any(legacy in operations_raw for legacy in LEGACY_OPERATION_ALIASES)


def migrate_config_file_if_needed() -> bool:
    """Reescreve o YAML legado (ex.: content_generate → post_generate)."""
    if not CONFIG_FILE.exists():
        return False
    payload = _load_yaml_file(CONFIG_FILE)
    operations_raw = payload.get("operations", {})
    if not isinstance(operations_raw, dict) or not _config_file_needs_migration(operations_raw):
        return False
    normalized = _normalize_operations_raw(operations_raw)
    migrated: dict[str, dict[str, Any]] = {}
    for op in LLM_OPERATIONS:
        default = _default_for_operation(op)
        if op in normalized:
            migrated[op] = _merge_config(
                default, LlmOperationConfig.from_dict(normalized[op])
            ).to_dict()
        else:
            migrated[op] = default.to_dict()
    _dump_yaml_file(CONFIG_FILE, {"operations": migrated})
    return True


def load_global_config() -> dict[str, LlmOperationConfig]:
    migrate_config_file_if_needed()
    payload = _load_yaml_file(CONFIG_FILE)
    operations_raw = payload.get("operations", {})
    if isinstance(operations_raw, dict):
        operations_raw = _normalize_operations_raw(operations_raw)
    result: dict[str, LlmOperationConfig] = {}
    for op in LLM_OPERATIONS:
        default = _default_for_operation(op)
        if isinstance(operations_raw, dict) and op in operations_raw:
            override = LlmOperationConfig.from_dict(operations_raw[op])
            result[op] = _merge_config(default, override)
        else:
            result[op] = default
    return result


def save_global_config(config: dict[str, LlmOperationConfig]) -> Path:
    operations: dict[str, dict[str, Any]] = {}
    for op in LLM_OPERATIONS:
        cfg = config.get(op)
        if cfg is None:
            cfg = _default_for_operation(op)
        operations[op] = cfg.to_dict()
    _dump_yaml_file(CONFIG_FILE, {"operations": operations})
    return CONFIG_FILE


def ensure_default_config_file() -> Path:
    if CONFIG_FILE.exists():
        migrate_config_file_if_needed()
        return CONFIG_FILE
    save_global_config({op: _default_for_operation(op) for op in LLM_OPERATIONS})
    return CONFIG_FILE


def resolve(operation: str) -> LlmOperationConfig:
    global_cfg = load_global_config()
    return global_cfg.get(operation, _default_for_operation(operation))


def resolve_all() -> dict[str, LlmOperationConfig]:
    return {op: resolve(op) for op in LLM_OPERATIONS}


__all__ = [
    "CONFIG_FILE",
    "DEFAULT_OPERATION_CONFIGS",
    "LLM_OPERATIONS",
    "LlmOperationConfig",
    "LlmOperationId",
    "OPERATION_LABELS",
    "check_provider_available",
    "ensure_default_config_file",
    "list_operations",
    "list_providers",
    "load_global_config",
    "resolve",
    "resolve_all",
    "save_global_config",
]
