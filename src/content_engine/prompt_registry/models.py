"""Contratos de dominio imutaveis do Prompt Registry."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class ArtifactType(StrEnum):
    PROMPT_TEMPLATE = "PROMPT_TEMPLATE"
    BASE = "BASE"
    PERSONA = "PERSONA"
    FORMAT_RULES = "FORMAT_RULES"
    POLICY = "POLICY"
    OUTPUT_CONTRACT = "OUTPUT_CONTRACT"
    EDITORIAL = "EDITORIAL"
    SEGMENTATION = "SEGMENTATION"
    EVALUATION = "EVALUATION"
    RETRY_APPENDIX = "RETRY_APPENDIX"
    REFERENCE = "REFERENCE"
    LEGACY = "LEGACY"


class ArtifactStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    REFERENCE_ONLY = "REFERENCE_ONLY"
    LEGACY = "LEGACY"
    ORPHAN = "ORPHAN"


class VersionStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class RolloutMode(StrEnum):
    LEGACY_ONLY = "LEGACY_ONLY"
    COMPARE = "COMPARE"
    REGISTRY_PRIMARY = "REGISTRY_PRIMARY"
    REGISTRY_ONLY = "REGISTRY_ONLY"


@dataclass(frozen=True)
class PromptArtifact:
    id: int
    key: str
    title: str
    description: str
    artifact_type: str
    status: str
    source_origin: str
    legacy_source_path: str | None
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class PromptArtifactVersion:
    id: int
    artifact_id: int
    version: int
    content: str
    content_hash: str
    expected_variables: tuple[str, ...]
    required_variables: tuple[str, ...]
    status: str
    change_reason: str
    created_by: str
    created_at: str
    activated_at: str | None
    supersedes_version_id: int | None


@dataclass(frozen=True)
class PromptOperation:
    id: int
    key: str
    label: str
    description: str
    phase: str
    phase_group: str
    phase_order: int
    consumer_symbol: str
    is_conditional: bool
    retry_policy: str
    fallback_policy: str
    rollout_mode: str
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class PromptComposition:
    id: int
    operation_id: int
    version: int
    status: str
    description: str
    created_at: str
    activated_at: str | None
    created_by: str


@dataclass(frozen=True)
class PromptCompositionItem:
    id: int
    composition_id: int
    artifact_id: int
    position: int
    required: bool
    separator: str
    condition_type: str | None
    condition_field: str | None
    condition_operator: str | None
    condition_value: Any | None
    runtime_slot: str | None


@dataclass(frozen=True)
class PromptExecutionReference:
    execution_id: str
    operation_key: str
    composition_id: int
    composition_version: int
    artifact_versions: tuple[dict[str, Any], ...]
    template_hash: str
    resolved_hash: str
    provider: str | None
    model: str | None
    resolved_at: str
    resolution_source: str
    error: str | None = None
    rollout_mode: str = RolloutMode.REGISTRY_ONLY
    used_fallback: bool = False
    placeholders: tuple[str, ...] = field(default_factory=tuple)
