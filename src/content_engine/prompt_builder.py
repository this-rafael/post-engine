"""Build generation prompts from the V4 authorial briefing."""
from __future__ import annotations

import json
from typing import Any

from .prompt_loader import load_prompt
from .schemas import GenerationPromptInput
from .slidemark_contract import SLIDEMARK_LLM_CONTRACT
from .template_renderer import render_template


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

ANTI_IA_POLICIES: list[dict[str, object]] = [
    {
        "id": "VOICE_01",
        "rule": "Use evidence from the author and do not invent personal experience.",
        "severity": "hard",
    },
    {
        "id": "VOICE_02",
        "rule": "Prefer concrete trade-offs, details, and uncertainty over generic claims.",
        "severity": "hard",
    },
    {
        "id": "VOICE_03",
        "rule": "Do not turn a weak signal into a certainty or a strong opinion.",
        "severity": "hard",
    },
    {
        "id": "VOICE_04",
        "rule": "Keep the author's language intact when quoting or paraphrasing evidence.",
        "severity": "hard",
    },
    {
        "id": "STYLE_01",
        "nome": "Proibir travessão e ritmo de travessão",
        "rule": (
            "Não use travessão (—) nem hífen longo como pausa dramática. "
            "Não imite o ritmo do travessão com dois-pontos teatrais "
            "('adivinhar a exigência: prove ou refaça') nem com ponto-e-vírgula "
            "epigramático. Prefira frases curtas, vírgula ou ponto."
        ),
        "ban": ["—", " – ", "padrao X: Y como revelação dramatizada"],
        "severity": "hard",
    },
    {
        "id": "STYLE_02",
        "nome": "Proibir antítese-template",
        "rule": (
            "Não use a fórmula 'Não é X. É Y.', 'Questionar não é o problema. É…', "
            "'Não se trata de X, trata-se de Y', 'O problema não é A. O problema é B.', "
            "'Tom importa menos…; o critério é…'. Contra-ataque direto a uma cena "
            "concreta; não dramatize contraste em slot de copy."
        ),
        "ban": [
            "não é X, é Y",
            "não o problema é",
            "não se trata de",
            "o problema não é / o problema é",
        ],
        "severity": "hard",
    },
    {
        "id": "STYLE_03",
        "nome": "Proibir epigrama moral de fechamento",
        "rule": (
            "Não feche com máxima simétrica tipo 'O produto pede X; o ego quer Y', "
            "'a melhor review defende…', 'minha régua:…'. Termine com consequência "
            "operacional, critério testável ou cena. Sem moral da história."
        ),
        "severity": "hard",
    },
    {
        "id": "STYLE_04",
        "nome": "Proibir tríades abstratas decorativas",
        "rule": (
            "Não empilhe listas de três abstrações como estilo "
            "('risco, contrato ou comportamento'; 'critério, impacto e decisão'; "
            "'regra, fonte e custo'). Se listar, cada item precisa carregar fato, "
            "mecanismo ou exemplo; senão, corte."
        ),
        "severity": "hard",
    },
    {
        "id": "STYLE_05",
        "nome": "Proibir abertura retórica reaproveitável",
        "rule": (
            "Não abra com pergunta binária genérica ('X ou Y?'), "
            "'você já se perguntou…?', 'e se eu te dissesse…?'. "
            "Abra com atrito situacional: cena, decisão, falha ou custo observados."
        ),
        "severity": "hard",
    },
    {
        "id": "STYLE_06",
        "nome": "Evitar ensaio polido uniforme",
        "rule": (
            "Não produza parágrafos com a mesma cadência, o mesmo grau de abstração "
            "e a mesma elevação filosófica. Alterne comprimento. Deixe rugosidade: "
            "detalhe sujo, limitação, dúvida, custo. Um texto 'certo demais' e "
            "simétrico demais é falha."
        ),
        "severity": "hard",
    },
    {
        "id": "STYLE_07",
        "nome": "Proibir reformulação sem avanço",
        "rule": (
            "Cada parágrafo deve acrescentar mecanismo, evidência, consequência ou "
            "critério novo. Proibido repetir a tese em outra formulação elegante."
        ),
        "severity": "hard",
    },
    {
        "id": "STYLE_08",
        "nome": "Voz de autor técnico, não de copywriter",
        "rule": (
            "Escreva como alguém que já perdeu tempo no PR, no deploy ou na decisão, "
            "não como essayista de LinkedIn. Preferir verbos de ação e nomes concretos "
            "a substantivos abstratos e máxima moral."
        ),
        "severity": "hard",
    },
]


def _serialize(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def _authorial_projection(data: GenerationPromptInput) -> tuple[dict[str, Any], dict[str, Any]]:
    interview = dict(data.interview_context) if isinstance(data.interview_context, dict) else {}
    briefing = dict(data.briefing_autoral)
    gateway = dict(data.gateway_result) if isinstance(data.gateway_result, dict) else {}
    if not gateway and isinstance(briefing.get("gateway"), dict):
        gateway = dict(briefing["gateway"])
    return interview, gateway


def build_generation_prompt(data: GenerationPromptInput) -> str:
    if data.tipo_de_post not in PERSONAS_POR_TIPO:
        raise ValueError(f"tipo_de_post invalido: {data.tipo_de_post}")

    interview, gateway = _authorial_projection(data)
    persona = PERSONAS_POR_TIPO[data.tipo_de_post]
    template = load_prompt(BASE_FILES_POR_TIPO[data.tipo_de_post])
    context: dict[str, object] = {
        "tema": data.tema,
        "plataforma": data.plataforma,
        "objetivoDoPost": data.objetivo_do_post,
        "tipoDePost": data.tipo_de_post,
        "personalidade": data.personalidade or "nao informada",
        "personaSelecionada": f"{persona}\n\n{load_prompt(PERSONA_FILES_POR_TIPO[data.tipo_de_post])}",
        "regrasDoTipoDePost": load_prompt(RULES_FILES_POR_TIPO[data.tipo_de_post]),
        "restricoesDeGeracao": _serialize(data.restricoes_de_geracao or []),
        "politicasAntiIa": _serialize({"policies": ANTI_IA_POLICIES}),
        "briefingAutoral": _serialize(data.briefing_autoral),
        "gatewayResult": _serialize(gateway),
        "interviewContext": _serialize(interview),
        "evidenceLedger": _serialize(interview.get("evidence_ledger", [])),
        "authorialSignals": _serialize(interview.get("signals", [])),
        "authorialDimensions": _serialize(interview.get("dimensions", {})),
        "interviewGaps": _serialize(interview.get("gaps", [])),
        "contratoSlideMarkAtual": SLIDEMARK_LLM_CONTRACT,
    }
    return render_template(template, context)


__all__ = [
    "ANTI_IA_POLICIES",
    "BASE_FILES_POR_TIPO",
    "PERSONA_FILES_POR_TIPO",
    "PERSONAS_POR_TIPO",
    "RULES_FILES_POR_TIPO",
    "build_generation_prompt",
]
