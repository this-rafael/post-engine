"""Conversao de conteudo final editado para documento SlideMark JSON v1."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from .agent_wrapper import AgentWrapper
from .generator import _parse_slidemark
from .llm_json_parser import extract_json_object_from_llm_output
from .prompt_builder import RULES_FILES_POR_TIPO
from .prompt_loader import load_prompt
from .schemas import AgentResult, SandboxPolicy, TipoDePost, ToolName
from .slidemark_contract import OFFICIAL_THEMES, SLIDEMARK_LLM_CONTRACT
from .slidemark_validator import (
    normalize_slidemark_document,
    validate_slidemark_export_document,
)
from .template_renderer import render_template
from .trilhas import TRILHA_ESTRUTURAS, is_trilha_visual

AUTHOR_NAME = "Rafael Pereira"
AUTHOR_HANDLE = "@this-rafael-pereira"
_DEFAULT_THEME = "rafael-io-executive-dark"
_TECH_THEME = "diffvision-dracula"


def _regras_para_tipo(tipo_de_post: TipoDePost) -> str:
    key = RULES_FILES_POR_TIPO.get(tipo_de_post, "generator.rules_short_carousel")
    return load_prompt(key)


def _serializar_json(value: object) -> str:
    if value is None:
        return "null"
    return json.dumps(value, ensure_ascii=False, indent=2)


def _extrair_slidemark(payload: dict[str, Any]) -> dict[str, Any] | None:
    nested = payload.get("slidemark")
    if isinstance(nested, dict):
        parsed = _parse_slidemark(nested)
        if parsed is not None:
            return parsed
    return _parse_slidemark(payload)


def _conteudo_tem_codigo(texto: str) -> bool:
    if "```" in texto:
        return True
    return bool(re.search(r"\b(def |class |import |function |const |let |var )\b", texto))


def _aplicar_defaults_autor(slidemark: dict[str, Any], tema: str, conteudo_final: str) -> None:
    author = slidemark.get("author")
    if not isinstance(author, dict):
        author = {}
        slidemark["author"] = author
    if not str(author.get("name", "")).strip():
        author["name"] = AUTHOR_NAME
    handle = str(author.get("handle", "")).strip()
    if not handle.startswith("@"):
        author["handle"] = AUTHOR_HANDLE

    theme = slidemark.get("theme")
    if isinstance(theme, dict):
        theme = theme.get("id")
    if theme not in OFFICIAL_THEMES:
        slidemark["theme"] = (
            _TECH_THEME if _conteudo_tem_codigo(conteudo_final) else _DEFAULT_THEME
        )

    slidemark.setdefault("version", "1.0.0")
    slidemark.setdefault("canvas", {"width": 1080, "height": 1080})

    document = slidemark.get("document")
    if not isinstance(document, dict):
        document = {}
        slidemark["document"] = document
    if not str(document.get("title", "")).strip():
        document["title"] = tema or "SlideMark"
    if not str(document.get("description", "")).strip():
        document["description"] = document["title"]
    document.setdefault("language", "pt-BR")

    settings = slidemark.get("settings")
    if not isinstance(settings, dict):
        settings = {}
        slidemark["settings"] = settings
    settings.setdefault("showAuthor", True)
    settings.setdefault("showPageNumber", True)
    settings.setdefault("showSwipeHint", True)
    settings.setdefault("swipeHintText", "Deslize")

    export = slidemark.get("export")
    if not isinstance(export, dict):
        export = {}
        slidemark["export"] = export
    if not str(export.get("fileName", "")).strip():
        slug = re.sub(r"[^a-z0-9]+", "-", (tema or "slide").lower()).strip("-")
        export["fileName"] = slug or "slide"
    export.setdefault("formats", ["png", "zip", "pdf"])
    export.setdefault(
        "pdf",
        {"pageMode": "square", "source": "rendered-images"},
    )


def _combinar_sugestoes_imagem(
    segmentos: list[dict[str, Any]] | None,
    sugestoes_imagem: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Keep edited segment suggestions ahead of the generation-level list."""
    combinadas = [dict(item) for item in sugestoes_imagem or [] if isinstance(item, dict)]
    for segmento in segmentos or []:
        if not isinstance(segmento, dict):
            continue
        sugestao = segmento.get("sugestaoImagem")
        if sugestao is None:
            sugestao = segmento.get("sugestao_imagem")
        if not isinstance(sugestao, dict):
            continue
        item = dict(sugestao)
        if segmento.get("id"):
            item["slideId"] = segmento["id"]
        if segmento.get("ordem"):
            item["numero"] = segmento["ordem"]
        combinadas.append(item)
    return combinadas


@dataclass
class SlideMarkConvertido:
    slidemark: dict[str, Any]
    alertas: list[str] = field(default_factory=list)
    agent_result: AgentResult | None = None


class SlideMarkConverter:
    def __init__(
        self,
        agent: AgentWrapper,
        tool: ToolName,
        model: str | None = None,
        sandbox: SandboxPolicy = "read-only",
        opencode_agent: str | None = None,
        reasoning_effort: str | None = None,
    ) -> None:
        self.agent: AgentWrapper = agent
        self.tool: ToolName = tool
        self.model: str | None = model
        self.sandbox: SandboxPolicy = sandbox
        self.opencode_agent: str | None = opencode_agent
        self.reasoning_effort: str | None = reasoning_effort

    def converter(
        self,
        *,
        tema: str,
        plataforma: str,
        tipo_de_post: TipoDePost,
        conteudo_final: str,
        segmentos: list[dict[str, Any]] | None = None,
        sugestoes_imagem: list[dict[str, Any]] | None = None,
        briefing_autoral: dict[str, Any] | None = None,
        slidemark_original: dict[str, Any] | None = None,
    ) -> SlideMarkConvertido:
        if not is_trilha_visual(tipo_de_post):
            raise ValueError(
                f"tipo_de_post '{tipo_de_post}' nao e trilha visual"
            )
        conteudo = conteudo_final.strip()
        if not conteudo:
            raise ValueError("conteudo final nao pode ser vazio")

        sugestoes = _combinar_sugestoes_imagem(segmentos, sugestoes_imagem)
        template = load_prompt("generator.export_slidemark")
        prompt = render_template(
            template,
            {
                "tema": tema,
                "plataforma": plataforma,
                "tipoDePost": tipo_de_post,
                "regrasDoTipoDePost": _regras_para_tipo(tipo_de_post),
                "estruturaNarrativa": TRILHA_ESTRUTURAS.get(tipo_de_post, ""),
                "conteudoFinal": conteudo,
                "segmentosJson": _serializar_json(segmentos or []),
                "briefingAutoral": _serializar_json(briefing_autoral or {}),
                "slidemarkOriginal": _serializar_json(slidemark_original),
                "sugestoesImagem": _serializar_json(sugestoes),
                "contratoSlideMarkAtual": SLIDEMARK_LLM_CONTRACT,
            },
        )

        result: AgentResult = self.agent.run(
            self.tool,
            prompt,
            model=self.model,
            agent=self.opencode_agent,
            reasoning_effort=self.reasoning_effort,
            sandbox=self.sandbox,
            json_output=True,
        )
        if result.error is not None:
            raise RuntimeError(result.error)

        parsed = extract_json_object_from_llm_output(
            result.stdout,
            prefer_keys=("slidemark",),
        )
        if not parsed.ok or parsed.data is None:
            raise ValueError(
                f"JSON invalido: {parsed.error or 'sem objeto JSON recuperavel'}"
            )

        slidemark = _extrair_slidemark(parsed.data)
        if slidemark is None:
            raise ValueError("resposta LLM nao contem documento SlideMark v1 valido")

        _aplicar_defaults_autor(slidemark, tema, conteudo)
        normalized = normalize_slidemark_document(
            slidemark,
            image_suggestions=sugestoes,
        )
        if not isinstance(normalized, dict):
            raise ValueError("resposta LLM nao contem documento SlideMark em objeto")
        errors = validate_slidemark_export_document(normalized)
        if errors:
            raise ValueError(f"SlideMark invalido: {'; '.join(errors)}")
        return SlideMarkConvertido(
            slidemark=normalized,
            alertas=[],
            agent_result=result,
        )


__all__ = [
    "AUTHOR_HANDLE",
    "AUTHOR_NAME",
    "SlideMarkConvertido",
    "SlideMarkConverter",
]
