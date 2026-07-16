"""Compatibilidade legada para catalogo de prompts.

Novos consumidores nao devem importar este modulo. O conteudo retornado vem
do Prompt Registry, nunca de ``prompts/`` em runtime.
"""
from __future__ import annotations

from pathlib import Path

from .prompt_registry.importer import ensure_registry_initialized
from .prompt_registry.repository import PromptRegistryRepository

PROMPTS_ROOT: Path = Path(__file__).resolve().parents[2] / "prompts"

PROMPT_PATHS: dict[str, str] = {
    "interview.explore": "interview/explore.md",
    "interview.evaluate_authorship": "interview/evaluate-authorship.md",
    "interview.deepen": "interview/deepen.md",
    "router.suggest_content_type": "router/suggest-content-type.md",
    "generator.base": "generator/base.md",
    "generator.base_short_carousel": "generator/base-short-carousel.md",
    "generator.base_long_slide": "generator/base-long-slide.md",
    "generator.rules_post": "generator/rules-post.md",
    "generator.rules_article": "generator/rules-article.md",
    "generator.rules_short_carousel": "generator/rules-short-carousel.md",
    "generator.rules_long_slide": "generator/rules-long-slide.md",
    "generator.persona_post": "generator/personas/dev-interlocutor-post.md",
    "generator.persona_article": "generator/personas/dev-interlocutor-article.md",
    "generator.persona_short_carousel": (
        "generator/personas/dev-interlocutor-short-carousel.md"
    ),
    "generator.persona_long_slide": "generator/personas/dev-interlocutor-long-slide.md",
    "generator.segment": "generator/segment.md",
    "generator.segment_slides": "generator/segment-slides.md",
    "generator.adjust_segment": "generator/adjust-segment.md",
    "generator.adjust_segments_bulk": "generator/adjust-segments-bulk.md",
    "generator.export_slidemark": "generator/export-slidemark.md",
    "generator.evaluate_post_post": "generator/evaluate-post-post.md",
    "generator.evaluate_post_article": "generator/evaluate-post-article.md",
    "generator.evaluate_post_short_carousel": (
        "generator/evaluate-post-short-carousel.md"
    ),
    "generator.evaluate_post_long_slide": "generator/evaluate-post-long-slide.md",
    "editorial.storyboard": "editorial/storyboard.md",
    "editorial.block_approaches": "editorial/block_approaches.md",
    "editorial.block_draft": "editorial/block_draft.md",
    "editorial.compose": "editorial/compose.md",
}


def _resolve_path(name: str) -> Path:
    if name in PROMPT_PATHS:
        return PROMPTS_ROOT / PROMPT_PATHS[name]
    return PROMPTS_ROOT / name


def _artifact_key(name: str) -> str | None:
    if name in PROMPT_PATHS:
        return name
    normalized = name.replace("\\", "/")
    for key, relative in PROMPT_PATHS.items():
        if normalized == relative:
            return key
    return None


def load_prompt(name: str) -> str:
    key = _artifact_key(name)
    if key is None:
        path = _resolve_path(name)
        raise FileNotFoundError(
            f"Prompt nao encontrado: '{name}' (caminho procurado: {path})"
        )
    ensure_registry_initialized()
    with PromptRegistryRepository() as repository:
        version = repository.active_version(key)
    if version is None:
        path = _resolve_path(name)
        raise FileNotFoundError(
            f"Prompt nao encontrado: '{name}' (caminho procurado: {path})"
        )
    return version.content


def prompt_exists(name: str) -> bool:
    key = _artifact_key(name)
    if key is None:
        return False
    ensure_registry_initialized()
    with PromptRegistryRepository() as repository:
        return repository.active_version(key) is not None
