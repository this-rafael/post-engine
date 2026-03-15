"""Metadados editoriais das quatro trilhas de conteudo."""
from __future__ import annotations

from .schemas import TipoDePost

TRILHA_LABELS: dict[TipoDePost, str] = {
    "post": "Post",
    "article": "Artigo",
    "short_carousel": "Carrossel Curto",
    "long_slide": "Slide Longo",
}

TRILHA_REGRAS_MENTAIS: dict[TipoDePost, str] = {
    "post": "Uma ideia que eu quero colocar na cabeca de alguem.",
    "article": "Uma pergunta que merece ser investigada.",
    "short_carousel": "Uma ideia explicada visualmente.",
    "long_slide": "Um assunto que merece ser ensinado.",
}

TRILHA_ESTRUTURAS: dict[TipoDePost, str] = {
    "post": (
        "Ideia central -> Contexto/experiencia -> Desenvolvimento -> "
        "Insight -> Fechamento"
    ),
    "article": (
        "Problema/pergunta -> Contexto -> Tese -> Argumentos -> "
        "Contrapontos -> Evidencia -> Conclusao"
    ),
    "short_carousel": (
        "Hook -> Contexto -> Problema -> Explicacao -> Exemplo -> "
        "Insight -> Conclusao (4-8 slides, nem todos obrigatorios)"
    ),
    "long_slide": (
        "Capa -> Problema -> Contexto -> Fundamentos -> Conceitos -> "
        "Exemplos -> Implementacao -> Edge cases -> Resumo (9+ slides)"
    ),
}

TRILHA_NAO_DEVE_CONTER: dict[TipoDePost, str] = {
    "post": (
        "Tutorial completo, cinco teses diferentes, documentacao tecnica, "
        "explicacao exaustiva, conteudo fragmentado artificialmente."
    ),
    "article": (
        "Lista superficial, conteudo inflado, post de 10 mil caracteres, "
        "explicacao linear puramente didatica sem argumentacao."
    ),
    "short_carousel": (
        "Historia longa, contexto autobiografico complexo, muitas ramificacoes, "
        "investigacao profunda, 15 conceitos diferentes."
    ),
    "long_slide": (
        "Frases soltas para aumentar slides, uma ideia esticada, historia "
        "pessoal fragmentada, 20 slides de opiniao."
    ),
}

TRILHA_ASPECTOS_ENFASE: dict[TipoDePost, tuple[str, ...]] = {
    "post": ("opiniao", "experiencia", "personalidade"),
    "article": ("aprendizado", "opiniao", "experiencia"),
    "short_carousel": ("opiniao", "aprendizado"),
    "long_slide": ("aprendizado", "experiencia"),
}

SELECT_OPCOES: tuple[tuple[str, str], ...] = tuple(
    (TRILHA_LABELS[tipo], tipo) for tipo in (
        "post",
        "article",
        "short_carousel",
        "long_slide",
    )
)

TIPOS_VISUAIS: frozenset[TipoDePost] = frozenset({"short_carousel", "long_slide"})


def is_trilha_visual(tipo_de_post: TipoDePost) -> bool:
    return tipo_de_post in TIPOS_VISUAIS


__all__ = [
    "SELECT_OPCOES",
    "TIPOS_VISUAIS",
    "TRILHA_ASPECTOS_ENFASE",
    "TRILHA_ESTRUTURAS",
    "TRILHA_LABELS",
    "TRILHA_NAO_DEVE_CONTER",
    "TRILHA_REGRAS_MENTAIS",
    "is_trilha_visual",
]
