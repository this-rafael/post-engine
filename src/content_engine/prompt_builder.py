"""Build generation prompts from the V4 authorial briefing."""
from __future__ import annotations

from typing import Any

import json

from .prompt_registry.resolver import resolve_prompt
from .schemas import GenerationPromptInput
from .trilhas import is_trilha_visual


PERSONAS_POR_TIPO: dict[str, str] = {
    "post": "DevInterlocutorPost",
    "article": "DevInterlocutorArticle",
    "short_carousel": "DevInterlocutorShortCarousel",
    "long_slide": "DevInterlocutorLongSlide",
}
PERSONA_FILES_POR_TIPO: dict[str, str] = {
    "post": "generator.persona_post",
    "article": "generator.persona_article",
    "short_carousel": "generator.persona_short_carousel",
    "long_slide": "generator.persona_long_slide",
}
RULES_FILES_POR_TIPO: dict[str, str] = {
    "post": "generator.rules_post",
    "article": "generator.rules_article",
    "short_carousel": "generator.rules_short_carousel",
    "long_slide": "generator.rules_long_slide",
}
BASE_FILES_POR_TIPO: dict[str, str] = {
    "post": "generator.base",
    "article": "generator.base",
    "short_carousel": "generator.base_short_carousel",
    "long_slide": "generator.base_long_slide",
}

def _serialize(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def _authorial_projection(data: GenerationPromptInput) -> tuple[dict[str, Any], dict[str, Any]]:
    interview = dict(data.interview_context) if isinstance(data.interview_context, dict) else {}
    briefing = dict(data.briefing_autoral)
    gateway = dict(data.gateway_result) if isinstance(data.gateway_result, dict) else {}
    if not gateway and isinstance(briefing.get("gateway"), dict):
        gateway = dict(briefing["gateway"])
    return interview, gateway


def build_generation_prompt(
    data: GenerationPromptInput,
    *,
    provider: str | None = None,
    model: str | None = None,
) -> str:
    if data.tipo_de_post not in PERSONAS_POR_TIPO:
        raise ValueError(f"tipo_de_post invalido: {data.tipo_de_post}")

    interview, gateway = _authorial_projection(data)
    context: dict[str, object] = {
        "tema": data.tema,
        "plataforma": data.plataforma,
        "objetivoDoPost": data.objetivo_do_post,
        "tipoDePost": data.tipo_de_post,
        "personalidade": data.personalidade or "nao informada",
        "restricoesDeGeracao": _serialize(data.restricoes_de_geracao or []),
        "briefingAutoral": _serialize(data.briefing_autoral),
        "gatewayResult": _serialize(gateway),
        "interviewContext": _serialize(interview),
        "evidenceLedger": _serialize(interview.get("evidence_ledger", [])),
        "authorialSignals": _serialize(interview.get("signals", [])),
        "authorialDimensions": _serialize(interview.get("dimensions", {})),
        "interviewGaps": _serialize(interview.get("gaps", [])),
        "content_type": data.tipo_de_post,
        "is_visual_track": is_trilha_visual(data.tipo_de_post),
    }
    return resolve_prompt(
        "post_generate", context, provider=provider, model=model
    ).resolved_content


__all__ = [
    "BASE_FILES_POR_TIPO",
    "PERSONA_FILES_POR_TIPO",
    "PERSONAS_POR_TIPO",
    "RULES_FILES_POR_TIPO",
    "build_generation_prompt",
]
