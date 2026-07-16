"""Renderizacao estrita de placeholders sem avaliacao de expressoes."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable


_PLACEHOLDER_RE = re.compile(r"\{\{([A-Za-z_][A-Za-z0-9_]*)\}\}|(?<!\{)\{([A-Za-z_][A-Za-z0-9_]*)\}(?!\})")
_DOUBLE_BRACE_RE = re.compile(r"\{\{([^{}]*)\}\}")


class PromptRenderError(ValueError):
    pass


@dataclass(frozen=True)
class RenderResult:
    content: str
    variables_used: tuple[str, ...]
    diagnostics: tuple[str, ...]


def extract_placeholders(content: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(match.group(1) or match.group(2) for match in _PLACEHOLDER_RE.finditer(content)))


def validate_placeholder_syntax(content: str) -> None:
    for match in _DOUBLE_BRACE_RE.finditer(content):
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", match.group(1)):
            raise PromptRenderError(f"Placeholder invalido: {match.group(0)}")
    if content.count("{{") != content.count("}}"):
        raise PromptRenderError("Placeholder de chaves duplas sem fechamento")


def render(
    content: str,
    context: dict[str, Any],
    *,
    expected_variables: Iterable[str] = (),
    required_variables: Iterable[str] = (),
) -> RenderResult:
    if not content.strip():
        raise PromptRenderError("Template vazio")
    validate_placeholder_syntax(content)
    variables = extract_placeholders(content)
    expected = set(expected_variables) or set(variables)
    required = set(required_variables) or set(variables)
    missing = sorted(name for name in required if name not in context or context[name] is None)
    if missing:
        raise PromptRenderError(f"Variaveis obrigatorias ausentes: {', '.join(missing)}")
    undeclared = sorted(name for name in variables if name not in expected)
    if undeclared:
        raise PromptRenderError(f"Placeholders nao declarados: {', '.join(undeclared)}")

    def replace(match: re.Match[str]) -> str:
        key = match.group(1) or match.group(2)
        if key not in context or context[key] is None:
            raise PromptRenderError(f"Placeholder sem valor: {key}")
        return str(context[key])

    rendered = _PLACEHOLDER_RE.sub(replace, content)
    remaining = extract_placeholders(rendered)
    if remaining:
        raise PromptRenderError(f"Placeholders restantes apos renderizacao: {', '.join(remaining)}")
    if not rendered.strip():
        raise PromptRenderError("Conteudo renderizado vazio")
    unknown = sorted(key for key in context if key not in expected)
    diagnostics = tuple(f"Variavel nao declarada fornecida: {key}" for key in unknown)
    return RenderResult(content=rendered, variables_used=variables, diagnostics=diagnostics)


__all__ = ["PromptRenderError", "RenderResult", "extract_placeholders", "render", "validate_placeholder_syntax"]
