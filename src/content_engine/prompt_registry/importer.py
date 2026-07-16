"""Importador idempotente das fontes legadas para o SQLite.

Os arquivos sao lidos apenas nesta migration de bootstrap. Consumidores LLM
nunca os leem: recebem somente a resolucao persistida pelo resolver.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .inventory import write_inventory
from .models import ArtifactStatus, ArtifactType, RolloutMode, VersionStatus
from .renderer import extract_placeholders
from .repository import PromptRegistryRepository


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROMPTS_ROOT = PROJECT_ROOT / "prompts"


@dataclass(frozen=True)
class SeedArtifact:
    key: str
    path: str | None
    title: str
    artifact_type: str
    classification: str = "OPERATIONAL"
    status: str = ArtifactStatus.ACTIVE
    source_origin: str = "markdown"
    transform: str | None = None


_PERSONA_NAMES = {
    "generator.persona_post": "DevInterlocutorPost",
    "generator.persona_article": "DevInterlocutorArticle",
    "generator.persona_short_carousel": "DevInterlocutorShortCarousel",
    "generator.persona_long_slide": "DevInterlocutorLongSlide",
}


_SEEDS: tuple[SeedArtifact, ...] = (
    SeedArtifact("interview.questions", "registry-seeds/interview-questions.md", "Perguntas de entrevista", ArtifactType.PROMPT_TEMPLATE, source_origin="inline-template-migration"),
    SeedArtifact("interview.validate", "registry-seeds/interview-validate.md", "Validação de pergunta", ArtifactType.PROMPT_TEMPLATE, source_origin="inline-template-migration"),
    SeedArtifact("interview.evaluate", "registry-seeds/interview-evaluate.md", "Avaliação de autoria", ArtifactType.EVALUATION, source_origin="inline-template-migration"),
    SeedArtifact("interview.explore", "interview/explore.md", "Referência de exploração V4", ArtifactType.REFERENCE, "REFERENCE_ONLY", ArtifactStatus.REFERENCE_ONLY),
    SeedArtifact("interview.evaluate_authorship", "interview/evaluate-authorship.md", "Referência de avaliação V4", ArtifactType.REFERENCE, "REFERENCE_ONLY", ArtifactStatus.REFERENCE_ONLY),
    SeedArtifact("interview.round_title", "interview/round-title.md", "Título de rodada da entrevista", ArtifactType.PROMPT_TEMPLATE, source_origin="inline-template-migration"),
    SeedArtifact("interview.gap_diagnosis", "interview/gap-diagnosis.md", "Diagnóstico de lacunas da entrevista", ArtifactType.PROMPT_TEMPLATE, source_origin="inline-template-migration"),
    SeedArtifact("interview.deepen", "interview/deepen.md", "Aprofundamento legado", ArtifactType.REFERENCE, "REFERENCE_ONLY", ArtifactStatus.REFERENCE_ONLY),
    SeedArtifact("generator.base", "generator/base.md", "Base de geração textual", ArtifactType.BASE),
    SeedArtifact("generator.base_short_carousel", "generator/base-short-carousel.md", "Base de carrossel curto", ArtifactType.BASE),
    SeedArtifact("generator.base_long_slide", "generator/base-long-slide.md", "Base de guia visual longo", ArtifactType.BASE),
    SeedArtifact("generator.rules_post", "generator/rules-post.md", "Regras para post", ArtifactType.FORMAT_RULES),
    SeedArtifact("generator.rules_article", "generator/rules-article.md", "Regras para artigo", ArtifactType.FORMAT_RULES),
    SeedArtifact("generator.rules_short_carousel", "generator/rules-short-carousel.md", "Regras para carrossel curto", ArtifactType.FORMAT_RULES),
    SeedArtifact("generator.rules_long_slide", "generator/rules-long-slide.md", "Regras para slide longo", ArtifactType.FORMAT_RULES),
    SeedArtifact("generator.persona_post", "generator/personas/dev-interlocutor-post.md", "Persona de post", ArtifactType.PERSONA, transform="persona"),
    SeedArtifact("generator.persona_article", "generator/personas/dev-interlocutor-article.md", "Persona de artigo", ArtifactType.PERSONA, transform="persona"),
    SeedArtifact("generator.persona_short_carousel", "generator/personas/dev-interlocutor-short-carousel.md", "Persona de carrossel", ArtifactType.PERSONA, transform="persona"),
    SeedArtifact("generator.persona_long_slide", "generator/personas/dev-interlocutor-long-slide.md", "Persona de slide longo", ArtifactType.PERSONA, transform="persona"),
    SeedArtifact("policy.anti_ia", "registry-seeds/anti-ia-policy.json", "Políticas anti-IA", ArtifactType.POLICY, transform="json_pretty"),
    SeedArtifact("contract.slidemark", "registry-seeds/slidemark-contract.md", "Contrato SlideMark", ArtifactType.OUTPUT_CONTRACT),
    SeedArtifact("generator.segment", "generator/segment.md", "Segmentação textual", ArtifactType.SEGMENTATION),
    SeedArtifact("generator.segment_slides", "generator/segment-slides.md", "Segmentação visual", ArtifactType.SEGMENTATION),
    SeedArtifact("generator.adjust_segment", "generator/adjust-segment.md", "Ajuste de segmento", ArtifactType.SEGMENTATION),
    SeedArtifact("generator.adjust_segments_bulk", "generator/adjust-segments-bulk.md", "Ajuste de segmentos em lote", ArtifactType.SEGMENTATION),
    SeedArtifact("generator.export_slidemark", "generator/export-slidemark.md", "Exportação SlideMark", ArtifactType.PROMPT_TEMPLATE),
    SeedArtifact("generator.evaluate_post_post", "generator/evaluate-post-post.md", "Avaliação de post", ArtifactType.EVALUATION),
    SeedArtifact("generator.evaluate_post_article", "generator/evaluate-post-article.md", "Avaliação de artigo", ArtifactType.EVALUATION),
    SeedArtifact("generator.evaluate_post_short_carousel", "generator/evaluate-post-short-carousel.md", "Avaliação de carrossel", ArtifactType.EVALUATION),
    SeedArtifact("generator.evaluate_post_long_slide", "generator/evaluate-post-long-slide.md", "Avaliação de slide longo", ArtifactType.EVALUATION),
    SeedArtifact("editorial.storyboard", "editorial/storyboard.md", "Storyboard editorial", ArtifactType.EDITORIAL),
    SeedArtifact("editorial.block_approaches", "editorial/block_approaches.md", "Abordagens de bloco", ArtifactType.EDITORIAL),
    SeedArtifact("editorial.block_draft", "editorial/block_draft.md", "Rascunho de bloco", ArtifactType.EDITORIAL),
    SeedArtifact("editorial.compose", "editorial/compose.md", "Composição editorial", ArtifactType.EDITORIAL),
    SeedArtifact("editorial.retry_preservation", "registry-seeds/editorial-retry-preservation.md", "Apêndice de preservação", ArtifactType.RETRY_APPENDIX, source_origin="inline-template-migration"),
    SeedArtifact("generator.rules_feed", "generator/rules-feed.md", "Regras de feed legado", ArtifactType.LEGACY, "LEGACY", ArtifactStatus.LEGACY),
    SeedArtifact("generator.rules_slide", "generator/rules-slide.md", "Regras de slide legado", ArtifactType.LEGACY, "LEGACY", ArtifactStatus.LEGACY),
    SeedArtifact("generator.persona_feed", "generator/personas/dev-interlocutor-feed.md", "Persona de feed legado", ArtifactType.LEGACY, "LEGACY", ArtifactStatus.LEGACY),
    SeedArtifact("generator.persona_slide", "generator/personas/dev-interlocutor-slide.md", "Persona de slide legado", ArtifactType.LEGACY, "LEGACY", ArtifactStatus.LEGACY),
    SeedArtifact("router.suggest_content_type", None, "Router sem fonte", ArtifactType.REFERENCE, "ORPHAN", ArtifactStatus.ORPHAN),
)


_OPERATIONS: tuple[dict[str, Any], ...] = (
    {"key": "interview_questions", "label": "Exploração aberta da entrevista", "phase": "Interview / Exploration", "group": "Interview", "order": 1, "consumer": "interview.exploration.generate_candidates"},
    {"key": "interview_validate", "label": "Validação de perguntas", "phase": "Interview / Validation", "group": "Interview", "order": 2, "consumer": "interview.validation.validate_question"},
    {"key": "interview_evaluate", "label": "Avaliação de autoria", "phase": "Interview / Authorship Evaluation", "group": "Interview", "order": 3, "consumer": "interview.llm_evaluation.evaluate_authorship_llm"},
    {"key": "interview_round_title", "label": "Título da rodada", "phase": "Interview / Authorship Evaluation", "group": "Interview", "order": 3, "consumer": "interview.round_title_generator.generate_round_title"},
    {"key": "interview_gap_diagnosis", "label": "Diagnóstico de lacunas", "phase": "Interview / Terminal Gaps", "group": "Interview", "order": 3, "consumer": "interview.gap_diagnosis.generate_gap_diagnosis"},
    {"key": "post_generate", "label": "Geração de conteúdo", "phase": "Generation", "group": "Generation", "order": 4, "consumer": "generator.ContentGenerator.generate", "conditional": True},
    {"key": "storyboard_generate", "label": "Storyboard", "phase": "Editorial / Storyboard", "group": "Editorial", "order": 5, "consumer": "editorial_generation.StoryboardGenerator.gerar"},
    {"key": "block_approaches_generate", "label": "Abordagens por bloco", "phase": "Editorial / Block Approaches", "group": "Editorial", "order": 6, "consumer": "editorial_generation.BlockDraftGenerator.gerar_abordagens"},
    {"key": "block_draft_generate", "label": "Rascunho por bloco", "phase": "Editorial / Block Drafts", "group": "Editorial", "order": 7, "consumer": "editorial_generation.BlockDraftGenerator.gerar_rascunho"},
    {"key": "editorial_compose", "label": "Composição editorial", "phase": "Editorial / Compose", "group": "Editorial", "order": 8, "consumer": "editorial_generation.EditorialComposer.compose", "conditional": True, "retry": "retry_attempt=1 adiciona apêndice de preservação"},
    {"key": "segment", "label": "Segmentação", "phase": "Segmentation", "group": "Segmentation", "order": 9, "consumer": "segmentation.Segmenter.segmentar", "conditional": True},
    {"key": "adjust_segment", "label": "Ajuste de segmento", "phase": "Segmentation / Adjustment", "group": "Segmentation", "order": 10, "consumer": "adjust_segment.SegmentAdjuster.ajustar"},
    {"key": "adjust_segments_bulk", "label": "Ajuste em lote", "phase": "Segmentation / Adjustment", "group": "Segmentation", "order": 10, "consumer": "adjust_segments_bulk.SegmentBulkAdjuster.ajustar"},
    {"key": "post_evaluate", "label": "Avaliação final", "phase": "Evaluation", "group": "Evaluation", "order": 11, "consumer": "post_evaluation.PostEvaluator.avaliar", "conditional": True},
    {"key": "slidemark_export", "label": "Exportação SlideMark", "phase": "Export", "group": "Export", "order": 12, "consumer": "slidemark_converter.SlideMarkConverter.converter", "conditional": True},
)


def _item(key: str, position: int, *, slot: str | None = None, condition: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"artifact_key": key, "position": position, "runtime_slot": slot, "condition": condition or {}}


def _eq(field: str, value: Any) -> dict[str, Any]:
    return {"field": field, "operator": "EQUALS", "value": value}


def _in(field: str, values: list[Any]) -> dict[str, Any]:
    return {"field": field, "operator": "IN", "value": values}


_COMPOSITIONS: dict[str, list[dict[str, Any]]] = {
    "interview_questions": [_item("interview.questions", 1)],
    "interview_validate": [_item("interview.validate", 1)],
    "interview_evaluate": [_item("interview.evaluate", 1)],
    "interview_round_title": [_item("interview.round_title", 1)],
    "interview_gap_diagnosis": [_item("interview.gap_diagnosis", 1)],
    "post_generate": [
        _item("generator.base", 10, condition=_in("content_type", ["post", "article"])),
        _item("generator.base_short_carousel", 20, condition=_eq("content_type", "short_carousel")),
        _item("generator.base_long_slide", 30, condition=_eq("content_type", "long_slide")),
        _item("generator.persona_post", 40, slot="personaSelecionada", condition=_eq("content_type", "post")),
        _item("generator.persona_article", 50, slot="personaSelecionada", condition=_eq("content_type", "article")),
        _item("generator.persona_short_carousel", 60, slot="personaSelecionada", condition=_eq("content_type", "short_carousel")),
        _item("generator.persona_long_slide", 70, slot="personaSelecionada", condition=_eq("content_type", "long_slide")),
        _item("generator.rules_post", 80, slot="regrasDoTipoDePost", condition=_eq("content_type", "post")),
        _item("generator.rules_article", 90, slot="regrasDoTipoDePost", condition=_eq("content_type", "article")),
        _item("generator.rules_short_carousel", 100, slot="regrasDoTipoDePost", condition=_eq("content_type", "short_carousel")),
        _item("generator.rules_long_slide", 110, slot="regrasDoTipoDePost", condition=_eq("content_type", "long_slide")),
        _item("policy.anti_ia", 120, slot="politicasAntiIa"),
        _item("contract.slidemark", 130, slot="contratoSlideMarkAtual", condition=_eq("is_visual_track", True)),
    ],
    "storyboard_generate": [_item("editorial.storyboard", 1)],
    "block_approaches_generate": [_item("editorial.block_approaches", 1)],
    "block_draft_generate": [_item("editorial.block_draft", 1), _item("policy.anti_ia", 2, slot="politicasAntiIa")],
    "editorial_compose": [
        _item("editorial.compose", 1),
        _item("generator.rules_post", 10, slot="formatRules", condition=_eq("content_type", "post")),
        _item("generator.rules_article", 20, slot="formatRules", condition=_eq("content_type", "article")),
        _item("generator.rules_short_carousel", 30, slot="formatRules", condition=_eq("content_type", "short_carousel")),
        _item("generator.rules_long_slide", 40, slot="formatRules", condition=_eq("content_type", "long_slide")),
        _item("policy.anti_ia", 50, slot="politicasAntiIa"),
        _item("editorial.retry_preservation", 60, condition=_eq("retry_attempt", 1)),
    ],
    "segment": [
        _item("generator.segment", 1, condition=_eq("is_visual_track", False)),
        _item("generator.segment_slides", 2, condition=_eq("is_visual_track", True)),
    ],
    "adjust_segment": [_item("generator.adjust_segment", 1)],
    "adjust_segments_bulk": [_item("generator.adjust_segments_bulk", 1)],
    "post_evaluate": [
        _item("generator.evaluate_post_post", 1, condition=_eq("content_type", "post")),
        _item("generator.evaluate_post_article", 2, condition=_eq("content_type", "article")),
        _item("generator.evaluate_post_short_carousel", 3, condition=_eq("content_type", "short_carousel")),
        _item("generator.evaluate_post_long_slide", 4, condition=_eq("content_type", "long_slide")),
    ],
    "slidemark_export": [
        _item("generator.export_slidemark", 1),
        _item("generator.rules_short_carousel", 10, slot="regrasDoTipoDePost", condition=_eq("content_type", "short_carousel")),
        _item("generator.rules_long_slide", 20, slot="regrasDoTipoDePost", condition=_eq("content_type", "long_slide")),
        _item("contract.slidemark", 30, slot="contratoSlideMarkAtual"),
    ],
}


def _read_seed(seed: SeedArtifact) -> str | None:
    if seed.path is None:
        return None
    source = PROMPTS_ROOT / seed.path
    if not source.is_file():
        return None
    content = source.read_text(encoding="utf-8")
    if seed.transform == "persona":
        return f"{_PERSONA_NAMES[seed.key]}\n\n{content}"
    if seed.transform == "json_pretty":
        return json.dumps(json.loads(content), ensure_ascii=False, indent=2)
    return content


def _inventory_records() -> list[dict[str, Any]]:
    operations_by_artifact: dict[str, list[str]] = {}
    for operation, items in _COMPOSITIONS.items():
        for item in items:
            operations_by_artifact.setdefault(str(item["artifact_key"]), []).append(operation)
    records = []
    for seed in _SEEDS:
        records.append(
            {
                "key": seed.key,
                "source": seed.path,
                "classification": seed.classification,
                "artifact_type": str(seed.artifact_type),
                "operations": sorted(operations_by_artifact.get(seed.key, [])),
            }
        )
    referenced = {seed.path for seed in _SEEDS if seed.path}
    for path in sorted(PROMPTS_ROOT.rglob("*.md")):
        relative = str(path.relative_to(PROMPTS_ROOT))
        if relative not in referenced:
            records.append({"key": None, "source": relative, "classification": "ORPHAN", "artifact_type": "REFERENCE", "operations": []})
    return records


def import_legacy_prompts(
    path: str | Path | None = None, *, write_inventory_file: bool = True,
) -> dict[str, int]:
    """Cria somente versoes iniciais ausentes; nunca sobrescreve edicoes do usuario."""
    imported = 0
    with PromptRegistryRepository(path) as repository:
        for spec in _OPERATIONS:
            repository.upsert_operation(
                key=spec["key"], label=spec["label"], phase=spec["phase"],
                phase_group=spec["group"], phase_order=int(spec["order"]),
                consumer_symbol=spec["consumer"], is_conditional=bool(spec.get("conditional")),
                retry_policy=str(spec.get("retry", "")), rollout_mode=RolloutMode.REGISTRY_ONLY,
            )
        for seed in _SEEDS:
            artifact = repository.create_artifact(
                key=seed.key, title=seed.title, artifact_type=seed.artifact_type,
                status=seed.status, source_origin=seed.source_origin, legacy_source_path=seed.path,
            )
            content = _read_seed(seed)
            if content is None:
                continue
            version = repository.create_version(
                artifact.key, content, expected_variables=extract_placeholders(content),
                required_variables=extract_placeholders(content), status=VersionStatus.DRAFT,
                change_reason="Initial migration to Prompt Registry", created_by="system-migration",
            )
            if repository.active_version(artifact.key) is None:
                repository.activate_version(artifact.key, version.version)
                imported += 1
        for operation, items in _COMPOSITIONS.items():
            if repository.get_active_composition(operation) is None:
                composition = repository.create_composition(
                    operation, description="Initial migration to Prompt Registry", status=VersionStatus.DRAFT,
                    created_by="system-migration", items=items,
                )
                repository.activate_composition(operation, composition.version)
    if write_inventory_file:
        write_inventory(_inventory_records())
    return {"imported_versions": imported, "artifacts": len(_SEEDS), "operations": len(_OPERATIONS)}


def ensure_registry_initialized(path: str | Path | None = None) -> None:
    """Bootstrap idempotente para installations locais ainda sem banco."""
    with PromptRegistryRepository(path) as repository:
        ready = bool(repository.list_operations())
    if not ready:
        import_legacy_prompts(path)
    # Metadados de operação não são conteúdo editável. Esta reconciliação torna
    # instalações já bootstrapadas observáveis sem reler nem sobrescrever seeds.
    # Operações novas (ainda nao importadas) sao criadas via upsert.
    with PromptRegistryRepository(path) as repository:
        for spec in _OPERATIONS:
            existing = repository.get_operation(spec["key"])
            if existing is None:
                repository.upsert_operation(
                    key=spec["key"], label=spec["label"], phase=spec["phase"],
                    phase_group=spec["group"], phase_order=int(spec["order"]),
                    consumer_symbol=spec["consumer"], is_conditional=bool(spec.get("conditional")),
                    retry_policy=str(spec.get("retry", "")), rollout_mode=RolloutMode.REGISTRY_ONLY,
                )
            else:
                repository.update_operation_metadata(
                    spec["key"], phase=spec["phase"], phase_group=spec["group"],
                    phase_order=int(spec["order"]), label=spec["label"],
                    consumer_symbol=spec["consumer"], is_conditional=bool(spec.get("conditional")),
                    retry_policy=str(spec.get("retry", "")),
                )
        # Corrige classificacoes de seeds importados por versões anteriores do
        # bootstrap. Apenas metadados de referencia/legado sao ajustados; o
        # conteudo e todas as versoes do usuario permanecem intocados.
        for seed in _SEEDS:
            if seed.status in {ArtifactStatus.LEGACY, ArtifactStatus.REFERENCE_ONLY}:
                artifact = repository.get_artifact(seed.key)
                if artifact is not None and artifact.status != str(seed.status):
                    repository.update_artifact_status(seed.key, str(seed.status))


def logical_prompt_keys() -> set[str]:
    return {seed.key for seed in _SEEDS}


__all__ = ["ensure_registry_initialized", "import_legacy_prompts", "logical_prompt_keys"]
