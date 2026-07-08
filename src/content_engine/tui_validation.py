"""SPEC-040: validacoes dos formularios do TUI."""
from __future__ import annotations

import json
from numbers import Real


TIPOS_DE_POST: tuple[str, ...] = ("post", "article", "short_carousel", "long_slide")
TOOLS: tuple[str, ...] = ("codex", "opencode", "cursor")
SANDBOXES: tuple[str, ...] = ("read-only", "workspace-write", "danger-full-access")


class TuiValidationError(Exception):
    def __init__(self, field: str, message: str) -> None:
        super().__init__(f"{field}: {message}")
        self.field: str = field
        self.message: str = message


def _is_real(value: object) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool)


def _validar_scores(scores: object) -> str | None:
    if scores is None:
        return None
    if not isinstance(scores, dict):
        return "scores deve ser um objeto/dict"
    for chave, valor in scores.items():
        if isinstance(valor, dict):
            for subchave, subvalor in valor.items():
                if not _is_real(subvalor):
                    return f"scores['{chave}']['{subchave}'] deve ser numerico"
            continue
        if not _is_real(valor):
            return f"scores['{chave}'] deve ser numerico"
    return None


def _validar_restricoes(restricoes: object) -> str | None:
    if restricoes is None:
        return None
    if not isinstance(restricoes, list):
        return "restricoes deve ser uma lista"
    for indice, item in enumerate(restricoes):
        if not isinstance(item, str):
            return f"restricoes[{indice}] deve ser string"
    return None


def validar_preview(
    tema: str,
    plataforma: str,
    objetivo: str,
    tipo_de_post: str,
    briefing_texto: str,
    scores: object = None,
    restricoes: object = None,
) -> tuple[bool, list[str], dict | None, dict | None, list[str] | None]:
    errors: list[str] = []

    if not isinstance(tema, str) or not tema.strip():
        errors.append("tema nao pode ser vazio")
    if not isinstance(plataforma, str) or not plataforma.strip():
        errors.append("plataforma nao pode ser vazia")
    if not isinstance(objetivo, str) or not objetivo.strip():
        errors.append("objetivo nao pode ser vazio")
    if tipo_de_post not in TIPOS_DE_POST:
        errors.append(
            f"tipo_de_post invalido: {tipo_de_post!r}. validos: {list(TIPOS_DE_POST)}"
        )

    briefing_dict: dict | None = None
    if not isinstance(briefing_texto, str) or not briefing_texto.strip():
        errors.append("briefing_texto nao pode ser vazio")
    else:
        try:
            parsed = json.loads(briefing_texto)
        except (ValueError, TypeError) as exc:
            errors.append(f"briefing_texto nao e JSON valido: {exc}")
        else:
            if not isinstance(parsed, dict):
                errors.append("briefing_texto deve ser um objeto JSON")
            else:
                briefing_dict = parsed

    scores_dict: dict | None = None
    if scores is not None:
        erro_scores = _validar_scores(scores)
        if erro_scores is not None:
            errors.append(erro_scores)
        elif isinstance(scores, dict):
            scores_dict = {str(k): v for k, v in scores.items()}

    restricoes_list: list[str] | None = None
    if restricoes is not None:
        erro_restricoes = _validar_restricoes(restricoes)
        if erro_restricoes is not None:
            errors.append(erro_restricoes)
        elif isinstance(restricoes, list):
            restricoes_list = [item for item in restricoes if isinstance(item, str)]

    return (not errors), errors, briefing_dict, scores_dict, restricoes_list


def validar_sandbox(sandbox: str, tool: str) -> str | None:
    if tool == "opencode":
        return None
    if sandbox not in SANDBOXES:
        return (
            f"sandbox invalido para codex: {sandbox!r}. validos: {list(SANDBOXES)}"
        )
    return None


def validar_modelo(modelo: str | None) -> str | None:
    if modelo is None:
        return None
    if isinstance(modelo, str) and modelo == "":
        return "modelo nao pode ser string vazia"
    return None


__all__ = [
    "SANDBOXES",
    "TIPOS_DE_POST",
    "TOOLS",
    "TuiValidationError",
    "validar_modelo",
    "validar_preview",
    "validar_sandbox",
]
