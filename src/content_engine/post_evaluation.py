"""SPEC-034: avaliacao autoral de um post gerado."""
from __future__ import annotations

import json
from typing import Any

from .agent_wrapper import AgentWrapper
from .llm_json_parser import extract_json_object_from_llm_output
from .prompt_registry.resolver import resolve_prompt
from .schemas import (
    AgentResult,
    AvaliacaoSlideMark,
    SandboxPolicy,
    ScoreDoPost,
    SeveridadeSlide,
    TrechoFraco,
    TipoDePost,
    ToolName,
)


_SCORE_KEYS: tuple[str, ...] = (
    "tese",
    "progressao",
    "concretude",
    "precisaoTecnica",
    "retencao",
    "autoridade",
    "autoria",
    "slidemark",
    "revisaoTextual",
)

_SCORE_FIELD_MAP: dict[str, str] = {
    "tese": "tese",
    "progressao": "progressao",
    "concretude": "concretude",
    "precisaoTecnica": "precisao_tecnica",
    "retencao": "retencao",
    "autoridade": "autoridade",
    "autoria": "autoria",
    "slidemark": "slidemark",
    "revisaoTextual": "revisao_textual",
}

_SEVERIDADES_VALIDAS: frozenset[str] = frozenset({"baixa", "media", "alta"})


def _clamp(value: int) -> int:
    if value < 0:
        return 0
    if value > 10:
        return 10
    return value


def _coerce_score(raw: Any) -> int:
    if isinstance(raw, bool):
        return 0
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float):
        return int(raw)
    return 0


def _coerce_list_str(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(item) for item in raw if isinstance(item, (str, int, float))]


def _coerce_severidade(raw: Any) -> SeveridadeSlide:
    value = str(raw).strip().lower() if raw is not None else ""
    if value in _SEVERIDADES_VALIDAS:
        return value  # type: ignore[return-value]
    return "media"


def _coerce_trecho_fraco(raw: Any) -> TrechoFraco | None:
    if not isinstance(raw, dict):
        return None
    trecho_raw = raw.get("trecho")
    trecho = _coerce_score(trecho_raw) if trecho_raw is not None else 0
    return TrechoFraco(
        trecho=trecho,
        problema=str(raw.get("problema", "") or ""),
        severidade=_coerce_severidade(raw.get("severidade")),
        motivo=str(raw.get("motivo", "") or ""),
    )


def _coerce_trechos_fracos(raw: Any) -> list[TrechoFraco]:
    if not isinstance(raw, list):
        return []
    items: list[TrechoFraco] = []
    for entry in raw:
        trecho_fraco = _coerce_trecho_fraco(entry)
        if trecho_fraco is not None:
            items.append(trecho_fraco)
    return items


def _empty_avaliacao() -> AvaliacaoSlideMark:
    score = ScoreDoPost(
        tese=0,
        progressao=0,
        concretude=0,
        precisao_tecnica=0,
        retencao=0,
        autoridade=0,
        autoria=0,
        slidemark=0,
        revisao_textual=0,
    )
    return AvaliacaoSlideMark(
        score=score,
        veredito="",
        pontos_fortes=[],
        pontos_fracos=[],
        trechos_fracos=[],
        redundancias=[],
        falhas_tecnicas=[],
        sugestoes_melhoria=[],
    )


class PostEvaluator:
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

    def avaliar(
        self,
        tema: str,
        conteudo: str,
        briefing: dict[str, Any] | None,
        *,
        tipo_de_post: TipoDePost = "post",
        interview_context: dict[str, Any] | None = None,
    ) -> AvaliacaoSlideMark:
        contexto: dict[str, object] = {
            "tema": tema,
            "conteudoGerado": conteudo,
            "briefingAutoral": json.dumps(briefing or {}, ensure_ascii=False, indent=2),
            "interviewContext": json.dumps(interview_context or {}, ensure_ascii=False, indent=2),
            "content_type": tipo_de_post,
        }
        prompt = resolve_prompt(
            "post_evaluate", contexto, provider=self.tool, model=self.model
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
        score_raw = payload.get("score")
        if not isinstance(score_raw, dict):
            raise ValueError("payload deve conter 'score' como objeto")

        scores: dict[str, int] = {}
        for key in _SCORE_KEYS:
            field_name = _SCORE_FIELD_MAP[key]
            raw_val = score_raw.get(key)
            if key == "slidemark" and raw_val is None:
                raw_val = score_raw.get("estrutura")
            scores[field_name] = _clamp(_coerce_score(raw_val))

        score = ScoreDoPost(
            tese=scores["tese"],
            progressao=scores["progressao"],
            concretude=scores["concretude"],
            precisao_tecnica=scores["precisao_tecnica"],
            retencao=scores["retencao"],
            autoridade=scores["autoridade"],
            autoria=scores["autoria"],
            slidemark=scores["slidemark"],
            revisao_textual=scores["revisao_textual"],
        )

        return AvaliacaoSlideMark(
            score=score,
            veredito=str(payload.get("veredito", "") or ""),
            pontos_fortes=_coerce_list_str(payload.get("pontosFortes")),
            pontos_fracos=_coerce_list_str(payload.get("pontosFracos")),
            trechos_fracos=_coerce_trechos_fracos(payload.get("trechosFracos")),
            redundancias=_coerce_list_str(payload.get("redundancias")),
            falhas_tecnicas=_coerce_list_str(payload.get("falhasTecnicas")),
            sugestoes_melhoria=_coerce_list_str(payload.get("sugestoesDeMelhoria")),
        )


__all__ = ["PostEvaluator", "_empty_avaliacao"]
