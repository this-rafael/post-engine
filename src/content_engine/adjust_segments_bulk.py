"""Ajuste em lote de multiplos segmentos do post em uma unica chamada LLM."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .agent_wrapper import AgentWrapper
from .llm_json_parser import extract_json_object_from_llm_output
from .prompt_registry.resolver import resolve_prompt
from .schemas import AgentResult, SandboxPolicy, SegmentoPost, ToolName


@dataclass(frozen=True)
class SegmentAdjustRequest:
    segmento: SegmentoPost
    pedido: str
    problema: str = ""
    motivo: str = ""


def trecho_to_segment_index(trecho_raw: object, segment_count: int) -> int | None:
    try:
        trecho = int(trecho_raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if segment_count <= 0:
        return None
    if trecho >= 1:
        index = trecho - 1
    elif trecho == 0:
        index = 0
    else:
        return None
    if 0 <= index < segment_count:
        return index
    return None


class SegmentBulkAdjuster:
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

    def ajustar(
        self,
        conteudo_completo: str,
        ajustes: list[SegmentAdjustRequest],
        personalidade: str | None = None,
        restricoes: list[str] | None = None,
        *,
        tipo_de_post: str | None = None,
        briefing: dict[str, Any] | None = None,
        interview_context: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        if not ajustes:
            raise ValueError("lista de ajustes nao pode ser vazia")

        segmentos_payload: list[dict[str, object]] = []
        expected_ids: set[str] = set()
        for item in ajustes:
            segmento = item.segmento
            if not segmento.id or not isinstance(segmento.id, str):
                raise ValueError("segmento precisa de 'id' nao vazio")
            if not isinstance(segmento.ordem, int) or isinstance(segmento.ordem, bool):
                raise ValueError("segmento precisa de 'ordem' inteira")
            if not isinstance(segmento.texto, str) or not segmento.texto:
                raise ValueError("segmento precisa de 'texto' nao vazio")
            if not item.pedido.strip():
                raise ValueError("pedido de ajuste nao pode ser vazio")
            expected_ids.add(segmento.id)
            segmentos_payload.append(
                {
                    "id": segmento.id,
                    "ordem": segmento.ordem,
                    "texto": segmento.texto,
                    "papelInterno": segmento.papel_interno,
                    "pedidoDoUsuario": item.pedido,
                    "problemaEditorial": item.problema,
                    "direcaoSugerida": item.motivo,
                }
            )

        restricoes_list: list[str] = restricoes if restricoes is not None else []
        contexto: dict[str, object] = {
            "conteudoCompleto": conteudo_completo,
            "segmentosParaAjustar": json.dumps(segmentos_payload, ensure_ascii=False, indent=2),
            "personalidade": personalidade if personalidade else "nao informada",
            "restricoesDeGeracao": json.dumps(restricoes_list, ensure_ascii=False),
            "tipoDePost": tipo_de_post or "post",
            "briefingAutoral": json.dumps(briefing or {}, ensure_ascii=False),
            "interviewContext": json.dumps(interview_context or {}, ensure_ascii=False),
        }
        prompt = resolve_prompt(
            "adjust_segments_bulk", contexto, provider=self.tool, model=self.model
        ).resolved_content

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

        payload: dict[str, Any] = parsed.data
        raw_items = payload.get("segmentosReescritos")
        if not isinstance(raw_items, list):
            raise ValueError("payload deve conter 'segmentosReescritos' como lista")

        reescritos: dict[str, str] = {}
        for entry in raw_items:
            if not isinstance(entry, dict):
                continue
            seg_id = str(entry.get("id", "") or "")
            reescrito = entry.get("segmentoReescrito")
            if not seg_id or not isinstance(reescrito, str) or not reescrito.strip():
                continue
            reescritos[seg_id] = reescrito.strip()

        missing = expected_ids - set(reescritos)
        if missing:
            raise ValueError(
                f"resposta incompleta: faltam segmentos {sorted(missing)}"
            )
        return reescritos


__all__ = ["SegmentAdjustRequest", "SegmentBulkAdjuster", "trecho_to_segment_index"]
