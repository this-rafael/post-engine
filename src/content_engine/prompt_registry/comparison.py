"""Comparacao deterministica para a fase temporaria de rollout."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass


def normalize_prompt(content: str) -> str:
    return re.sub(r"\s+", " ", content).strip()


@dataclass(frozen=True)
class PromptComparison:
    equivalent: bool
    legacy_hash: str
    registry_hash: str
    normalized_legacy: str
    normalized_registry: str


def compare_prompts(legacy: str, registry: str) -> PromptComparison:
    left = normalize_prompt(legacy)
    right = normalize_prompt(registry)
    return PromptComparison(
        equivalent=left == right,
        legacy_hash=hashlib.sha256(left.encode("utf-8")).hexdigest(),
        registry_hash=hashlib.sha256(right.encode("utf-8")).hexdigest(),
        normalized_legacy=left, normalized_registry=right,
    )


__all__ = ["PromptComparison", "compare_prompts", "normalize_prompt"]
