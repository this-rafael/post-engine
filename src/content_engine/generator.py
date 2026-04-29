"""SPEC-027: servico de geracao de conteudo autoral."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .agent_wrapper import AgentWrapper
from .llm_json_parser import extract_json_object_from_llm_output
from .prompt_builder import build_generation_prompt
from .schemas import (
    AgentResult,
    GenerationPromptInput,
    SandboxPolicy,
    SlideContent,
    SugestaoImagem,
    ToolName,
)
from .slidemark_validator import (
    normalize_slidemark_document,
    validate_slidemark_document,
)


def _extrair_bullets_de_slide(slide: dict[str, Any]) -> list[str]:
    slide_type = str(slide.get("type", "")).strip()
    if slide_type == "content.bullets":
        bullets_raw = slide.get("bullets", [])
        if isinstance(bullets_raw, list):
            linhas: list[str] = []
            for item in bullets_raw:
                if isinstance(item, dict):
                    texto = str(item.get("text", "")).strip()
                    if texto:
                        linhas.append(texto)
            return linhas
    if slide_type == "content.text":
        body_raw = slide.get("body", [])
        if isinstance(body_raw, list):
            return [str(p).strip() for p in body_raw if str(p).strip()]
        if isinstance(body_raw, str) and body_raw.strip():
            return [body_raw.strip()]
    if slide_type == "content.compare":
        linhas = []
        for lado in ("left", "right"):
            coluna = slide.get(lado)
            if isinstance(coluna, dict):
                label = str(coluna.get("label") or coluna.get("title") or lado).strip()
                items = coluna.get("items", [])
                if isinstance(items, list) and items:
                    linhas.append(f"{label}: {', '.join(str(i).strip() for i in items[:3])}")
        return linhas
    if slide_type == "content.code":
        codigo = str(slide.get("code", "")).strip()
        if codigo:
            return [f"[{slide.get('language', 'code')}] {codigo.splitlines()[0][:80]}"]
    if slide_type == "closing.cta":
        linhas = []
        texto = str(slide.get("text", "")).strip()
        cta = str(slide.get("cta", "")).strip()
        if texto:
            linhas.append(texto)
        if cta:
            linhas.append(f"CTA: {cta}")
        return linhas
    if slide_type == "cover.hero":
        linhas = []
        subtitulo = str(slide.get("subtitle", "")).strip()
        if subtitulo:
            linhas.append(subtitulo)
        return linhas
    return []


def _formatar_sugestao_imagem(sugestao: SugestaoImagem) -> str:
    descricao = sugestao.descricao.strip()
    if sugestao.modo == "link" and sugestao.url:
        fonte = f" ({sugestao.fonte})" if sugestao.fonte else ""
        return f"Imagem sugerida: {descricao}{fonte} — {sugestao.url}"
    return f"Imagem sugerida: {descricao}"


def _parse_sugestao_imagem_item(raw: object) -> SugestaoImagem | None:
    if not isinstance(raw, dict):
        return None
    descricao = str(
        raw.get("descricao") or raw.get("sugestao") or raw.get("description") or ""
    ).strip()
    if not descricao:
        return None
    modo_raw = str(raw.get("modo", "descricao")).strip().lower()
    modo = "link" if modo_raw == "link" else "descricao"
    url_raw = raw.get("url")
    url = str(url_raw).strip() if isinstance(url_raw, str) and url_raw.strip() else None
    fonte_raw = raw.get("fonte")
    fonte = str(fonte_raw).strip() if isinstance(fonte_raw, str) and fonte_raw.strip() else None
    if modo == "link" and not url:
        modo = "descricao"
    return SugestaoImagem(modo=modo, descricao=descricao, url=url, fonte=fonte)


def _indexar_sugestoes_imagem(
    raw: object,
) -> tuple[dict[str, SugestaoImagem], dict[int, SugestaoImagem]]:
    por_id: dict[str, SugestaoImagem] = {}
    por_numero: dict[int, SugestaoImagem] = {}
    if not isinstance(raw, list):
        return por_id, por_numero
    for item in raw:
        sugestao = _parse_sugestao_imagem_item(item)
        if sugestao is None or not isinstance(item, dict):
            continue
        slide_id = str(item.get("slideId") or item.get("slide_id") or "").strip()
        if slide_id:
            por_id[slide_id] = sugestao
        numero_raw = item.get("numero") or item.get("ordem") or item.get("slide")
        if isinstance(numero_raw, int) and not isinstance(numero_raw, bool):
            por_numero[numero_raw] = sugestao
    return por_id, por_numero


def _resolver_sugestao_imagem(
    *,
    slide_id: str,
    numero: int,
    por_id: dict[str, SugestaoImagem],
    por_numero: dict[int, SugestaoImagem],
) -> SugestaoImagem | None:
    if slide_id and slide_id in por_id:
        return por_id[slide_id]
    return por_numero.get(numero)


def _aplicar_sugestoes_em_slides(
    slides: list[SlideContent],
    por_id: dict[str, SugestaoImagem],
    por_numero: dict[int, SugestaoImagem],
    slidemark: dict[str, Any] | None = None,
) -> list[SlideContent]:
    if not por_id and not por_numero:
        return slides
    raw_slides = (
        slidemark.get("slides")
        if isinstance(slidemark, dict) and isinstance(slidemark.get("slides"), list)
        else []
    )
    atualizados: list[SlideContent] = []
    for slide in slides:
        slide_id = ""
        if slide.numero - 1 < len(raw_slides):
            raw_slide = raw_slides[slide.numero - 1]
            if isinstance(raw_slide, dict):
                slide_id = str(raw_slide.get("id", "")).strip()
        sugestao = _resolver_sugestao_imagem(
            slide_id=slide_id,
            numero=slide.numero,
            por_id=por_id,
            por_numero=por_numero,
        )
        if sugestao is None:
            atualizados.append(slide)
            continue
        notas = _formatar_sugestao_imagem(sugestao)
        atualizados.append(
            SlideContent(
                numero=slide.numero,
                titulo=slide.titulo,
                bullets=slide.bullets,
                notas_visuais=notas,
                sugestao_imagem=sugestao,
            )
        )
    return atualizados


def _serializar_sugestoes_imagem(slides: list[SlideContent]) -> list[dict[str, Any]]:
    serializadas: list[dict[str, Any]] = []
    for slide in slides:
        if slide.sugestao_imagem is None:
            continue
        sugestao = slide.sugestao_imagem
        item: dict[str, Any] = {
            "numero": slide.numero,
            "modo": sugestao.modo,
            "descricao": sugestao.descricao,
        }
        if sugestao.url:
            item["url"] = sugestao.url
        if sugestao.fonte:
            item["fonte"] = sugestao.fonte
        serializadas.append(item)
    return serializadas


def _sugestoes_imagem_de_media(slidemark: dict[str, Any]) -> list[dict[str, Any]]:
    """Expose SlideMark media alt text to the editorial suggestion UI."""
    suggestions: list[dict[str, Any]] = []
    raw_slides = slidemark.get("slides")
    if not isinstance(raw_slides, list):
        return suggestions
    for number, raw_slide in enumerate(raw_slides, start=1):
        slide = raw_slide if isinstance(raw_slide, dict) else {}
        media = slide.get("media")
        media_dict = media if isinstance(media, dict) else {}
        description = str(media_dict.get("alt", "")).strip()
        if not description:
            continue
        item: dict[str, Any] = {
            "numero": number,
            "modo": "descricao",
            "descricao": description,
        }
        slide_id = str(slide.get("id", "")).strip()
        if slide_id:
            item["slideId"] = slide_id
        source = str(media_dict.get("src", "")).strip()
        if source.startswith(("http://", "https://")):
            item["modo"] = "link"
            item["url"] = source
        suggestions.append(item)
    return suggestions


def _slidemark_para_slide_content(
    slidemark: dict[str, Any],
    *,
    por_id: dict[str, SugestaoImagem] | None = None,
    por_numero: dict[int, SugestaoImagem] | None = None,
) -> list[SlideContent]:
    raw_slides = slidemark.get("slides")
    if not isinstance(raw_slides, list):
        return []
    por_id = por_id or {}
    por_numero = por_numero or {}
    slides: list[SlideContent] = []
    for index, item in enumerate(raw_slides, start=1):
        if not isinstance(item, dict):
            continue
        titulo = str(item.get("title", "")).strip()
        if not titulo:
            continue
        slide_id = str(item.get("id", "")).strip()
        bullets = _extrair_bullets_de_slide(item)
        sugestao = _resolver_sugestao_imagem(
            slide_id=slide_id,
            numero=index,
            por_id=por_id,
            por_numero=por_numero,
        )
        notas_visuais = _formatar_sugestao_imagem(sugestao) if sugestao else None
        slides.append(
            SlideContent(
                numero=index,
                titulo=titulo,
                bullets=bullets,
                notas_visuais=notas_visuais,
                sugestao_imagem=sugestao,
            )
        )
    return slides


def _slidemark_para_conteudo(
    slidemark: dict[str, Any],
    *,
    por_id: dict[str, SugestaoImagem] | None = None,
    por_numero: dict[int, SugestaoImagem] | None = None,
) -> str:
    slides = _slidemark_para_slide_content(
        slidemark,
        por_id=por_id,
        por_numero=por_numero,
    )
    return _slides_para_conteudo(slides)


def _parse_slidemark(raw: object) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    if raw.get("version") != "1.0.0":
        return None
    if not isinstance(raw.get("slides"), list):
        return None
    return raw


def _parse_slides(raw: object) -> list[SlideContent]:
    if not isinstance(raw, list):
        return []
    slides: list[SlideContent] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        numero_raw = item.get("numero")
        titulo = str(item.get("titulo", "")).strip()
        bullets_raw = item.get("bullets", [])
        if not isinstance(numero_raw, int) or isinstance(numero_raw, bool):
            continue
        if not titulo:
            continue
        bullets = [
            str(b).strip()
            for b in bullets_raw
            if isinstance(b, (str, int, float)) and str(b).strip()
        ] if isinstance(bullets_raw, list) else []
        notas = item.get("notasVisuais")
        if notas is None:
            notas = item.get("notas_visuais")
        notas_visuais = str(notas).strip() if isinstance(notas, str) and notas.strip() else None
        sugestao_raw = item.get("sugestaoImagem")
        if sugestao_raw is None:
            sugestao_raw = item.get("sugestao_imagem")
        sugestao = _parse_sugestao_imagem_item(sugestao_raw)
        if sugestao and not notas_visuais:
            notas_visuais = _formatar_sugestao_imagem(sugestao)
        slides.append(
            SlideContent(
                numero=numero_raw,
                titulo=titulo,
                bullets=bullets,
                notas_visuais=notas_visuais,
                sugestao_imagem=sugestao,
            )
        )
    slides.sort(key=lambda slide: slide.numero)
    return slides


def _slides_para_conteudo(slides: list[SlideContent]) -> str:
    partes: list[str] = []
    for slide in slides:
        linhas = [f"## Slide {slide.numero}: {slide.titulo}"]
        for bullet in slide.bullets:
            linhas.append(f"- {bullet}")
        if slide.notas_visuais:
            linhas.append(f"_(Imagem: {slide.notas_visuais})_")
        partes.append("\n".join(linhas))
    return "\n\n".join(partes)


@dataclass
class ConteudoGerado:
    conteudo: str
    metadados: dict[str, object]
    alertas: list[str]
    agent_result: AgentResult | None
    parse_error: str | None
    slides: list[SlideContent] = field(default_factory=list)
    slidemark: dict[str, Any] | None = None
    sugestoes_imagem: list[dict[str, Any]] = field(default_factory=list)


def parse_generation_payload(
    payload: dict[str, Any],
    *,
    agent_result: AgentResult | None = None,
) -> ConteudoGerado:
    """Converte payload JSON de geracao/composicao em ConteudoGerado."""
    raw_sugestoes = payload.get("sugestoesImagem")
    sugestoes_input = raw_sugestoes if isinstance(raw_sugestoes, list) else None
    por_id, por_numero = _indexar_sugestoes_imagem(sugestoes_input)
    slidemark = _parse_slidemark(payload.get("slidemark"))
    normalized_slidemark: dict[str, Any] | None = None
    validation_errors: list[str] = []
    if slidemark is not None:
        normalized = normalize_slidemark_document(
            slidemark,
            image_suggestions=sugestoes_input,
        )
        if isinstance(normalized, dict):
            normalized_slidemark = normalized
            validation_errors = validate_slidemark_document(normalized)
            slidemark = normalized if not validation_errors else None
        else:
            slidemark = None
            validation_errors = ["documento SlideMark nao e um objeto"]
    slides_source = slidemark or normalized_slidemark
    if slides_source is not None:
        slides = _slidemark_para_slide_content(
            slides_source,
            por_id=por_id,
            por_numero=por_numero,
        )
    else:
        slides = _parse_slides(payload.get("slides"))
        slides = _aplicar_sugestoes_em_slides(slides, por_id, por_numero)
    conteudo = str(payload.get("conteudo", "")).strip()
    if not conteudo and slides_source is not None:
        conteudo = _slidemark_para_conteudo(
            slides_source,
            por_id=por_id,
            por_numero=por_numero,
        )
    elif not conteudo and slides:
        conteudo = _slides_para_conteudo(slides)
    metadados = dict(payload.get("metadados", {}))
    alertas_raw = payload.get("alertas", [])
    alertas = [str(alerta) for alerta in alertas_raw] if isinstance(alertas_raw, list) else []
    sugestoes_imagem = _serializar_sugestoes_imagem(slides)
    if not sugestoes_imagem and slides_source is not None:
        sugestoes_imagem = _sugestoes_imagem_de_media(slides_source)
    if not sugestoes_imagem:
        if isinstance(raw_sugestoes, list):
            sugestoes_imagem = [
                dict(item)
                for item in raw_sugestoes
                if isinstance(item, dict)
            ]
    if slidemark is not None:
        metadados.setdefault("slideMarkVersion", slidemark.get("version", "1.0.0"))
        metadados.setdefault("totalSlides", len(slides))
    for error in validation_errors:
        alertas.append(f"SlideMark invalido: {error}")
    return ConteudoGerado(
        conteudo=conteudo,
        metadados=metadados,
        alertas=alertas,
        agent_result=agent_result,
        parse_error=None,
        slides=slides,
        slidemark=slidemark,
        sugestoes_imagem=sugestoes_imagem,
    )


class ContentGenerator:
    def __init__(
        self,
        agent: AgentWrapper,
        tool: ToolName,
        model: str | None = None,
        reasoning_effort: str | None = None,
        sandbox: SandboxPolicy = "read-only",
        opencode_agent: str | None = None,
    ) -> None:
        self.agent: AgentWrapper = agent
        self.tool: ToolName = tool
        self.model: str | None = model
        self.reasoning_effort: str | None = reasoning_effort
        self.sandbox: SandboxPolicy = sandbox
        self.opencode_agent: str | None = opencode_agent

    def generate(self, data: GenerationPromptInput) -> ConteudoGerado:
        prompt: str = build_generation_prompt(data)

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
            return ConteudoGerado(
                conteudo="",
                metadados={},
                alertas=[f"Falha na execucao: {result.error}"],
                agent_result=result,
                parse_error=result.error,
            )

        parsed = extract_json_object_from_llm_output(result.stdout)
        if not parsed.ok or parsed.data is None:
            return ConteudoGerado(
                conteudo=result.stdout,
                metadados={"raw": True},
                alertas=["JSON invalido, exibindo stdout bruto"],
                agent_result=result,
                parse_error=parsed.error or "Falha desconhecida ao extrair JSON.",
            )

        return parse_generation_payload(parsed.data, agent_result=result)


__all__ = [
    "ConteudoGerado",
    "ContentGenerator",
    "parse_generation_payload",
    "_formatar_sugestao_imagem",
    "_parse_slidemark",
    "_parse_slides",
    "_parse_sugestao_imagem_item",
    "_sugestoes_imagem_de_media",
    "_slides_para_conteudo",
    "_slidemark_para_conteudo",
    "_slidemark_para_slide_content",
]
