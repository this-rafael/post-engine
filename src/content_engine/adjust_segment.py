"""SPEC-032: ajuste de um segmento individual do post."""
from __future__ import annotations

import json
from typing import Any

from .agent_wrapper import AgentWrapper
from .llm_json_parser import extract_json_object_from_llm_output
from .prompt_registry.resolver import resolve_prompt
from .schemas import AgentResult, SandboxPolicy, SegmentoPost, ToolName


class SegmentAdjuster:
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
        segmento: SegmentoPost | None,
        pedido: str,
        personalidade: str | None = None,
        restricoes: list[str] | None = None,
        *,
        tipo_de_post: str | None = None,
        briefing: dict[str, Any] | None = None,
        interview_context: dict[str, Any] | None = None,
        eixo_alvo: str | None = None,
    ) -> str:
        if segmento is None:
            raise ValueError("segmento nao pode ser None")
        if not segmento.id or not isinstance(segmento.id, str):
            raise ValueError("segmento precisa de 'id' nao vazio")
        if not isinstance(segmento.ordem, int) or isinstance(segmento.ordem, bool):
            raise ValueError("segmento precisa de 'ordem' inteira")
        if not isinstance(segmento.texto, str) or not segmento.texto:
            raise ValueError("segmento precisa de 'texto' nao vazio")

        segmento_json: str = json.dumps(
            {
                "id": segmento.id,
                "ordem": segmento.ordem,
                "texto": segmento.texto,
                "papelInterno": segmento.papel_interno,
            },
            ensure_ascii=False,
        )
        restricoes_list: list[str] = restricoes if restricoes is not None else []
        contexto: dict[str, object] = {
            "conteudoCompleto": conteudo_completo,
            "segmentoAtual": segmento_json,
            "ajusteDoUsuario": pedido,
            "personalidade": personalidade if personalidade else "nao informada",
            "restricoesDeGeracao": json.dumps(restricoes_list, ensure_ascii=False),
            "tipoDePost": tipo_de_post or "post",
            "briefingAutoral": json.dumps(briefing or {}, ensure_ascii=False),
            "interviewContext": json.dumps(interview_context or {}, ensure_ascii=False),
            "eixoAlvo": eixo_alvo or "nao informado",
        }
        prompt = resolve_prompt(
            "adjust_segment", contexto, provider=self.tool, model=self.model
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
        reescrito = payload.get("segmentoReescrito")
        if not isinstance(reescrito, str):
            raise ValueError(
                "payload deve conter 'segmentoReescrito' como string"
            )
        return reescrito


__all__ = ["SegmentAdjuster"]
