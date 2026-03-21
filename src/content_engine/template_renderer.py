"""SPEC-051: Renderizacao simples de placeholders ``{{chave}}``.

Nao executa expressoes, nao importa o que quer que seja. Apenas substitui
``{{identificador}}`` por ``str(valor)`` do contexto. Chaves ausentes
resultam em ``KeyError`` com mensagem clara.
"""
from __future__ import annotations

import re

# Prompt files use both historical ``{chave}`` and documented ``{{chave}}``
# syntax. Match double braces first so their inner single braces are never
# rendered independently.
_PLACEHOLDER_RE = re.compile(r"\{\{(\w+)\}\}|(?<!\{)\{(\w+)\}(?!\})")


def render_template(template: str, context: dict[str, object]) -> str:
    def _replace(match: re.Match[str]) -> str:
        key = match.group(1) or match.group(2)
        if key not in context:
            raise KeyError(
                f"Placeholder '{{{{{key}}}}}' ausente no contexto de renderizacao"
            )
        return str(context[key])

    return _PLACEHOLDER_RE.sub(_replace, template)
