"""Testes de configuracao LLM por operacao."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from content_engine.llm_config import (
    LLM_OPERATIONS,
    LlmOperationConfig,
    ensure_default_config_file,
    load_global_config,
    resolve,
    resolve_all,
    save_global_config,
)


@pytest.fixture()
def isolated_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    config_path = tmp_path / "agent-config.yml"
    monkeypatch.setattr("content_engine.llm_config.CONFIG_FILE", config_path)
    monkeypatch.setattr("content_engine.llm_config.DATA_DIR", tmp_path)
    return config_path


def test_resolve_uses_defaults_without_files(isolated_config: Path) -> None:
    cfg = resolve("interview_questions")
    assert (cfg.provider, cfg.model, cfg.reasoning_effort) == (
        "opencode",
        "opencode-go/qwen3.7-plus",
        "max",
    )


def test_requested_operation_defaults(isolated_config: Path) -> None:
    expected = {
        "interview_questions": ("opencode", "opencode-go/qwen3.7-plus", "max"),
        "interview_validate": ("opencode", "opencode-go/glm-5.2", "max"),
        "interview_evaluate": ("cursor", "auto", None),
        "storyboard_generate": ("codex", "gpt-5.6-terra", "max"),
        "block_approaches_generate": ("codex", "gpt-5.6-luna", "medium"),
        "block_draft_generate": ("codex", "gpt-5.6-terra", "max"),
        "editorial_compose": ("codex", "gpt-5.6-sol", "max"),
        "segment": ("opencode", "opencode-go/qwen3.6-plus", "medium"),
        "adjust_segment": ("opencode", "opencode-go/qwen3.6-plus", "max"),
        "adjust_segments_bulk": ("cursor", "auto", None),
        "post_evaluate": ("codex", "gpt-5.6-terra", "max"),
        "slidemark_export": ("opencode", "opencode-go/qwen3.6-plus", "max"),
    }
    for operation, values in expected.items():
        cfg = resolve(operation)
        assert (cfg.provider, cfg.model, cfg.reasoning_effort) == values


def test_legacy_yaml_keys_map_to_interview_ops(isolated_config: Path) -> None:
    isolated_config.write_text(
        "operations:\n"
        "  questions:\n"
        "    provider: opencode\n"
        "    model: qwen-3.6-plus\n"
        "  answer_evaluate:\n"
        "    provider: cursor\n"
        "    model: auto\n",
        encoding="utf-8",
    )
    assert resolve("interview_questions").provider == "opencode"
    assert resolve("interview_questions").model == "qwen-3.6-plus"
    assert resolve("interview_evaluate").provider == "cursor"
    assert resolve("interview_evaluate").model == "auto"


def test_content_generate_migrates_to_post_generate(isolated_config: Path) -> None:
    isolated_config.write_text(
        "operations:\n"
        "  content_generate:\n"
        "    provider: cursor\n"
        "    model: cursor-max\n"
        "    reasoning_effort: high\n"
        "    sandbox: workspace-write\n"
        "    agent: writer\n",
        encoding="utf-8",
    )
    cfg = resolve("post_generate")
    assert cfg.provider == "cursor"
    assert cfg.model == "cursor-max"
    assert cfg.reasoning_effort == "high"
    assert cfg.sandbox == "workspace-write"
    assert cfg.agent == "writer"

    payload = yaml.safe_load(isolated_config.read_text(encoding="utf-8"))
    assert "content_generate" not in payload["operations"]
    assert "post_generate" in payload["operations"]


def test_content_generate_no_longer_exists(isolated_config: Path) -> None:
    resolved = resolve_all()
    assert "content_generate" not in resolved
    assert "content_generate" not in LLM_OPERATIONS


def test_post_generate_default(isolated_config: Path) -> None:
    cfg = resolve("post_generate")
    assert cfg.provider == "codex"
    assert cfg.model == "gpt-5.5"
    assert cfg.reasoning_effort == "xhigh"


def test_editorial_operations_have_independent_defaults(isolated_config: Path) -> None:
    assert resolve("storyboard_generate").reasoning_effort == "max"
    assert resolve("block_approaches_generate").reasoning_effort == "medium"
    assert resolve("block_draft_generate").reasoning_effort == "max"
    assert resolve("editorial_compose").reasoning_effort == "max"


def test_editorial_operations_resolve_independently(isolated_config: Path) -> None:
    save_global_config(
        {
            "storyboard_generate": LlmOperationConfig(
                provider="opencode",
                model="qwen-3.6-plus",
                reasoning_effort="low",
            ),
            "editorial_compose": LlmOperationConfig(
                provider="cursor",
                model="auto",
                reasoning_effort="xhigh",
                agent="composer",
            ),
            "block_draft_generate": LlmOperationConfig(
                provider="codex",
                model="gpt-5.4-mini",
            ),
            "block_approaches_generate": LlmOperationConfig(
                provider="codex",
                model="gpt-5.5",
                reasoning_effort="medium",
            ),
        }
    )
    storyboard = resolve("storyboard_generate")
    compose = resolve("editorial_compose")
    draft = resolve("block_draft_generate")
    approaches = resolve("block_approaches_generate")

    assert storyboard.provider == "opencode"
    assert storyboard.model == "qwen-3.6-plus"
    assert compose.provider == "cursor"
    assert compose.model == "auto"
    assert compose.agent == "composer"
    assert draft.model == "gpt-5.4-mini"
    assert approaches.reasoning_effort == "medium"
    assert draft.model != approaches.model or draft.reasoning_effort != approaches.reasoning_effort


def test_changing_storyboard_does_not_change_compose(isolated_config: Path) -> None:
    save_global_config(
        {
            "storyboard_generate": LlmOperationConfig(provider="codex", model="gpt-5.5"),
            "editorial_compose": LlmOperationConfig(provider="codex", model="gpt-5.5"),
        }
    )
    save_global_config(
        {
            **load_global_config(),
            "storyboard_generate": LlmOperationConfig(
                provider="opencode",
                model="qwen-3.6-plus",
            ),
        }
    )
    assert resolve("storyboard_generate").model == "qwen-3.6-plus"
    assert resolve("editorial_compose").model == "gpt-5.5"


def test_changing_block_draft_does_not_change_approaches(isolated_config: Path) -> None:
    current = load_global_config()
    current["block_draft_generate"] = LlmOperationConfig(
        provider="cursor",
        model="cursor-fast",
    )
    current["block_approaches_generate"] = LlmOperationConfig(
        provider="codex",
        model="gpt-5.5",
        reasoning_effort="high",
    )
    save_global_config(current)

    current = load_global_config()
    current["block_draft_generate"] = LlmOperationConfig(
        provider="opencode",
        model="deepseek-r2",
    )
    save_global_config(current)

    assert resolve("block_draft_generate").model == "deepseek-r2"
    assert resolve("block_approaches_generate").provider == "codex"
    assert resolve("block_approaches_generate").model == "gpt-5.5"


def test_slidemark_export_operation_default(isolated_config: Path) -> None:
    cfg = resolve("slidemark_export")
    assert cfg.provider == "opencode"
    assert cfg.model == "opencode-go/qwen3.6-plus"
    assert cfg.reasoning_effort == "max"
    assert "slidemark_export" in resolve_all()


def test_global_yaml_overrides_defaults(isolated_config: Path) -> None:
    save_global_config(
        {
            "interview_questions": LlmOperationConfig(provider="codex", model="gpt-5.4-mini"),
        }
    )
    cfg = resolve("interview_questions")
    assert cfg.provider == "codex"
    assert cfg.model == "gpt-5.4-mini"


def test_resolve_all_returns_all_operations(isolated_config: Path) -> None:
    resolved = resolve_all()
    assert "interview_questions" in resolved
    assert "post_generate" in resolved
    assert "storyboard_generate" in resolved
    assert "block_approaches_generate" in resolved
    assert "block_draft_generate" in resolved
    assert "editorial_compose" in resolved
    assert resolved["interview_evaluate"].provider == "cursor"
    for op in LLM_OPERATIONS:
        assert op in resolved


def test_ensure_default_config_file_creates_yaml(isolated_config: Path) -> None:
    path = ensure_default_config_file()
    assert path.exists()
    cfg = load_global_config()
    assert cfg["post_generate"].model == "gpt-5.5"
    assert "content_generate" not in cfg
