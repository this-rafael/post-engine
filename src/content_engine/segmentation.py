"""SPEC-030: segmentacao do conteudo gerado em partes editaveis."""
from __future__ import annotations

import json
from typing import Any

from .agent_wrapper import AgentWrapper
from .llm_json_parser import extract_json_object_from_llm_output
from .prompt_loader import load_prompt, prompt_exists
from .schemas import AgentResult, SandboxPolicy, SegmentoPost, TipoDePost, ToolName
from .template_renderer import render_template
from .trilhas import is_trilha_visual


def _texto_slide_slidemark(slide: dict[str, Any]) -> str:
    linhas: list[str] = []
    title = str(slide.get("title", "")).strip()
    if title:
        linhas.append(title)
    slide_type = str(slide.get("type", "")).strip()
    if slide_type == "content.bullets":
        for bullet in slide.get("bullets", []):
            if isinstance(bullet, dict):
                text = str(bullet.get("text", "")).strip()
                if text:
                    linhas.append(f"- {text}")
    elif slide_type == "content.text":
        body = slide.get("body", [])
        if isinstance(body, list):
            linhas.extend(str(item).strip() for item in body if str(item).strip())
        elif isinstance(body, str) and body.strip():
            linhas.append(body.strip())
        highlight_raw = slide.get("highlight")
        highlight = (
            str(highlight_raw.get("text", "")).strip()
            if isinstance(highlight_raw, dict)
            else str(highlight_raw or "").strip()
        )
        if highlight:
            linhas.append(f"Destaque: {highlight}")
    elif slide_type == "content.code":
        language = str(slide.get("language", "code")).strip() or "code"
        code = str(slide.get("code", "")).strip()
        if code:
            linhas.append(f"```{language}\n{code}\n```")
    elif slide_type == "content.compare":
        for side in ("left", "right"):
            column = slide.get(side)
            if isinstance(column, dict):
                label = str(column.get("label", side)).strip()
                items = column.get("items", [])
                if isinstance(items, list):
                    joined = ", ".join(str(item).strip() for item in items if str(item).strip())
                    if joined:
                        linhas.append(f"{label}: {joined}")
    elif slide_type == "closing.cta":
        text = str(slide.get("text", "")).strip()
        cta = str(slide.get("cta", "")).strip()
        if text:
            linhas.append(text)
        if cta:
            linhas.append(f"CTA: {cta}")
    else:
        subtitle = str(slide.get("subtitle", "")).strip()
        if subtitle:
            linhas.append(subtitle)
    return "\n".join(linhas)


def _papel_slidemark(slide_type: str, index: int, total: int) -> str:
    if slide_type == "cover.hero" or index == 1:
        return "capa"
    if slide_type == "closing.cta" or index == total:
        return "conclusao"
    if slide_type == "content.code":
        return "exemplo"
    if slide_type == "content.compare":
        return "trade-off"
    if slide_type == "content.bullets":
        return "fundamentos"
    return "explicacao"


def _papeis_esperados_por_formato(tipo_de_post: TipoDePost) -> list[str]:
    if tipo_de_post == "post":
        return ["abertura", "tese", "evidencia", "fechamento"]
    if tipo_de_post == "article":
        return ["introducao", "contexto", "argumento", "evidencia", "conclusao"]
    if tipo_de_post == "short_carousel":
        return ["hook", "contexto", "tese", "evidencia", "virada", "chamada"]
    return ["capa", "problema", "fundamentos", "exemplo", "sintese", "chamada"]


def _serializar_sugestao_imagem(raw: object) -> dict[str, Any] | None:
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
    item: dict[str, Any] = {"modo": modo, "descricao": descricao}
    if url:
        item["url"] = url
    if fonte:
        item["fonte"] = fonte
    return item


def _indexar_sugestoes_segmentacao(
    sugestoes_imagem: list[dict[str, Any]] | None,
) -> tuple[dict[str, dict[str, Any]], dict[int, dict[str, Any]]]:
    por_id: dict[str, dict[str, Any]] = {}
    por_numero: dict[int, dict[str, Any]] = {}
    if not sugestoes_imagem:
        return por_id, por_numero
    for raw in sugestoes_imagem:
        if not isinstance(raw, dict):
            continue
        serializada = _serializar_sugestao_imagem(raw)
        if serializada is None:
            continue
        slide_id = str(raw.get("slideId") or raw.get("slide_id") or "").strip()
        if slide_id:
            por_id[slide_id] = serializada
        numero_raw = raw.get("numero") or raw.get("ordem") or raw.get("slide")
        if isinstance(numero_raw, int) and not isinstance(numero_raw, bool):
            por_numero[numero_raw] = serializada
    return por_id, por_numero


def segmentar_slidemark(
    slidemark: dict[str, Any],
    sugestoes_imagem: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    raw_slides = slidemark.get("slides")
    if not isinstance(raw_slides, list):
        return []
    segmentos: list[dict[str, Any]] = []
    total = len(raw_slides)
    por_id, por_numero = _indexar_sugestoes_segmentacao(sugestoes_imagem)
    for index, raw_slide in enumerate(raw_slides, start=1):
        if not isinstance(raw_slide, dict):
            continue
        slide_type = str(raw_slide.get("type", "")).strip()
        slide_id = str(raw_slide.get("id") or f"slide-{index}").strip()
        sugestao = por_id.get(slide_id) or por_numero.get(index)
        segmento: dict[str, Any] = {
            "id": slide_id,
            "ordem": index,
            "slideType": slide_type,
            "texto": _texto_slide_slidemark(raw_slide),
            "papelInterno": _papel_slidemark(slide_type, index, total),
        }
        if sugestao is not None:
            segmento["sugestaoImagem"] = sugestao
        segmentos.append(segmento)
    return segmentos


def parse_segmentos(payload: dict[str, Any]) -> list[SegmentoPost]:
    raw_segmentos = payload.get("segmentos")
    if not isinstance(raw_segmentos, list):
        raise ValueError("payload deve conter 'segmentos' como lista")

    parsed: list[SegmentoPost] = []
    for index, item in enumerate(raw_segmentos):
        if not isinstance(item, dict):
            raise ValueError(f"segmento na posicao {index} nao e um objeto")

        id_value = item.get("id")
        ordem_value = item.get("ordem")
        texto_value = item.get("texto")
        if not isinstance(id_value, str) or not id_value:
            raise ValueError(f"segmento na posicao {index} sem 'id' (str nao vazio)")
        if not isinstance(ordem_value, int) or isinstance(ordem_value, bool):
            raise ValueError(
                f"segmento '{id_value}' sem 'ordem' (int nao vazio)"
            )
        if not isinstance(texto_value, str):
            raise ValueError(f"segmento '{id_value}' sem 'texto' (str)")

        papel_interno_raw = item.get("papelInterno")
        if papel_interno_raw is None:
            papel_interno_raw = item.get("papel_interno", "")
        if not isinstance(papel_interno_raw, str):
            raise ValueError(
                f"segmento '{id_value}' possui 'papelInterno' que nao e str"
            )

        parsed.append(
            SegmentoPost(
                id=id_value,
                ordem=ordem_value,
                texto=texto_value,
                papel_interno=papel_interno_raw,
            )
        )

    ids = [s.id for s in parsed]
    if len(set(ids)) != len(ids):
        raise ValueError("ids de segmentos devem ser unicos")

    ordens = [s.ordem for s in parsed]
    for i, ordem in enumerate(ordens):
        if ordem != i + 1:
            raise ValueError(
                f"ordem deve ser sequencial a partir de 1; recebido {ordens}"
            )

    return parsed


class Segmenter:
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

    def segmentar(
        self,
        conteudo: str,
        *,
        tipo_de_post: TipoDePost = "post",
        briefing: dict[str, Any] | None = None,
        interview_context: dict[str, Any] | None = None,
    ) -> list[SegmentoPost]:
        if is_trilha_visual(tipo_de_post) and prompt_exists("generator.segment_slides"):
            template = load_prompt("generator.segment_slides")
        else:
            template = load_prompt("generator.segment")
        prompt: str = render_template(
            template,
            {
                "conteudoDoPost": conteudo,
                "tipoDePost": tipo_de_post,
                "briefingAutoral": json.dumps(briefing or {}, ensure_ascii=False, indent=2),
                "interviewContext": json.dumps(interview_context or {}, ensure_ascii=False, indent=2),
                "papeisEsperados": ", ".join(_papeis_esperados_por_formato(tipo_de_post)),
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

        parsed = extract_json_object_from_llm_output(result.stdout)
        if not parsed.ok or parsed.data is None:
            raise ValueError(
                f"JSON invalido: {parsed.error or 'sem objeto JSON recuperavel'}"
            )

        return parse_segmentos(parsed.data)


__all__ = ["Segmenter", "parse_segmentos", "segmentar_slidemark"]
