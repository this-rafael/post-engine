"""Servicos LLM do fluxo editorial V3."""
from __future__ import annotations

import json
import random
from dataclasses import dataclass
from typing import Any

from .agent_wrapper import AgentWrapper
from .editorial_flow import (
    EDITORIAL_PERSONAS,
    assign_storyboard_blocks,
    new_option_id,
)
from .editorial_preservation import (
    editorial_anchors_for_prompt,
    extract_editorial_anchors,
    format_preservation_issues,
    validate_composition_preservation,
)
from .generator import ConteudoGerado, parse_generation_payload
from .llm_config import resolve
from .llm_json_parser import extract_json_object_from_llm_output
from .prompt_registry.resolver import resolve_prompt
from .schemas import AgentResult, ToolName, TuiSessionState


class EditorialParseError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


@dataclass
class EditorialRunResult:
    ok: bool
    data: Any = None
    error: str | None = None
    agent_result: AgentResult | None = None
    prompt: str = ""


def _run_json_llm(
    agent: AgentWrapper,
    *,
    operation: str,
    prompt: str,
    tool: ToolName | None = None,
) -> EditorialRunResult:
    cfg = resolve(operation)
    tool_name = tool or cfg.provider
    result = agent.run(
        tool_name,
        prompt,
        model=cfg.model,
        agent=cfg.agent,
        reasoning_effort=cfg.reasoning_effort,
        sandbox=cfg.sandbox or "read-only",
        json_output=True,
    )
    if result.error is not None:
        return EditorialRunResult(ok=False, error=result.error, agent_result=result, prompt=prompt)
    parsed = extract_json_object_from_llm_output(result.stdout)
    if not parsed.ok or parsed.data is None:
        return EditorialRunResult(
            ok=False,
            error=parsed.error or "JSON invalido.",
            agent_result=result,
            prompt=prompt,
        )
    return EditorialRunResult(ok=True, data=parsed.data, agent_result=result, prompt=prompt)


def parse_storyboard_blocks(payload: dict[str, Any]) -> list[dict[str, str]]:
    blocks_raw = payload.get("blocks")
    if not isinstance(blocks_raw, list) or not blocks_raw:
        raise EditorialParseError("Storyboard deve conter ao menos um bloco.")
    blocks: list[dict[str, str]] = []
    for index, item in enumerate(blocks_raw, start=1):
        if not isinstance(item, dict):
            raise EditorialParseError(f"Bloco {index} invalido.")
        role = str(item.get("role", "")).strip()
        focus = str(item.get("focus", "")).strip()
        if not role or not focus:
            raise EditorialParseError(f"Bloco {index}: papel e foco obrigatorios.")
        if "\n\n" in focus:
            raise EditorialParseError(f"Bloco {index}: foco com paragrafos longos.")
        blocks.append({"role": role, "focus": focus})
    return blocks


def parse_approaches(payload: dict[str, Any]) -> list[dict[str, str]]:
    approaches_raw = payload.get("approaches")
    if not isinstance(approaches_raw, list) or len(approaches_raw) != 3:
        raise EditorialParseError("Devem existir exatamente 3 abordagens.")
    approaches: list[dict[str, str]] = []
    titles: set[str] = set()
    for index, item in enumerate(approaches_raw, start=1):
        if not isinstance(item, dict):
            raise EditorialParseError(f"Abordagem {index} invalida.")
        title = str(item.get("title", "")).strip()
        description = str(item.get("description", "")).strip()
        if not title or not description:
            raise EditorialParseError(f"Abordagem {index}: titulo e descricao obrigatorios.")
        if title in titles:
            raise EditorialParseError(f"Abordagem {index}: titulo duplicado.")
        titles.add(title)
        approaches.append({"title": title, "description": description})
    return approaches


def parse_draft_content(payload: dict[str, Any]) -> str:
    draft = payload.get("draft")
    if not isinstance(draft, dict):
        raise EditorialParseError("Campo draft obrigatorio.")
    content = str(draft.get("content", "")).strip()
    if not content:
        raise EditorialParseError("Rascunho vazio.")
    return content


def _json_dumps(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


def _resolve_editorial_prompt(operation: str, context: dict[str, object]) -> str:
    cfg = resolve(operation)
    return resolve_prompt(
        operation, context, provider=cfg.provider, model=cfg.model
    ).resolved_content


def _storyboard_context(state: TuiSessionState, flow: dict[str, Any]) -> dict[str, object]:
    storyboard = flow.get("storyboard", {})
    blocks = storyboard.get("blocks", []) if isinstance(storyboard, dict) else []
    return {
        "briefingAutoral": _json_dumps(state.briefing_autoral),
        "interviewContext": _json_dumps(state.interview_state or {}),
        "tema": state.tema,
        "plataforma": state.plataforma,
        "objetivoDoPost": state.objetivo_do_post,
        "tipoDePost": state.tipo_de_post,
        "personalidade": state.personalidade,
        "storyboardJson": _json_dumps(blocks),
        "content_type": state.tipo_de_post,
        "is_visual_track": state.tipo_de_post in {"short_carousel", "long_slide"},
    }


def _composition_context(
    state: TuiSessionState,
    flow: dict[str, Any],
    *,
    selected_drafts: list[dict[str, Any]],
) -> tuple[dict[str, object], list[Any]]:
    """Build a focused context where drafts outrank background interview data."""

    anchors = extract_editorial_anchors(selected_drafts)
    storyboard = flow.get("storyboard", {})
    blocks = storyboard.get("blocks", []) if isinstance(storyboard, dict) else []
    context: dict[str, object] = {
        "tema": state.tema,
        "plataforma": state.plataforma,
        "objetivoDoPost": state.objetivo_do_post,
        "tipoDePost": state.tipo_de_post,
        "personalidade": state.personalidade,
        "storyboardJson": _json_dumps(blocks),
        "compositionBriefingJson": _json_dumps(_composition_briefing(state)),
        "authorialEvidenceJson": _json_dumps(_composition_authorial_evidence(state)),
        "interviewContextJson": _json_dumps(_composition_interview_context(state)),
        "selectedDraftsJson": _json_dumps(selected_drafts),
        "editorialAnchorsJson": _json_dumps(editorial_anchors_for_prompt(anchors)),
        "content_type": state.tipo_de_post,
        "retry_attempt": 0,
    }
    return context, anchors


def _composition_briefing(state: TuiSessionState) -> dict[str, object]:
    raw = state.briefing_autoral if isinstance(state.briefing_autoral, dict) else {}
    return {
        "tema": state.tema or raw.get("theme", ""),
        "objetivo": state.objetivo_do_post or raw.get("objective", ""),
        "plataforma": state.plataforma or raw.get("platform", ""),
        "tipo_de_post": state.tipo_de_post or raw.get("content_type", ""),
        "personalidade": state.personalidade or raw.get("personality", ""),
        "restricoes_de_geracao": list(state.restricoes_de_geracao),
    }


def _composition_authorial_evidence(state: TuiSessionState) -> list[dict[str, str]]:
    """Project literal V4 evidence without synthesising another state copy."""

    ledger = state.evidence_ledger
    chosen: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in ledger:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text", "")).strip()
        normalized = " ".join(text.lower().split())
        if not text or normalized in seen:
            continue
        seen.add(normalized)
        chosen.append(
            {
                "id": str(item.get("id", "")),
                "text": text,
                "source_answer_id": str(item.get("source_answer_id", "")),
            }
        )
        if len(chosen) == 12:
            break
    return chosen


def _composition_interview_context(state: TuiSessionState) -> dict[str, object]:
    raw = state.interview_state if isinstance(state.interview_state, dict) else {}
    return {
        "tema": raw.get("context", {}).get("tema", state.tema)
        if isinstance(raw.get("context"), dict)
        else state.tema,
        "objetivo": raw.get("context", {}).get("objetivo", state.objetivo_do_post)
        if isinstance(raw.get("context"), dict)
        else state.objetivo_do_post,
        "tipo_de_post": raw.get("context", {}).get("formato", state.tipo_de_post)
        if isinstance(raw.get("context"), dict)
        else state.tipo_de_post,
        "personalidade": raw.get("context", {}).get("personalidade", state.personalidade)
        if isinstance(raw.get("context"), dict)
        else state.personalidade,
        "gateway": state.gateway_result,
        "dimensions": raw.get("dimensions", {}),
    }


class StoryboardGenerator:
    def __init__(self, agent: AgentWrapper) -> None:
        self.agent = agent

    def gerar(self, state: TuiSessionState, flow: dict[str, Any]) -> EditorialRunResult:
        prompt = _resolve_editorial_prompt(
            "storyboard_generate", _storyboard_context(state, flow)
        )
        run = _run_json_llm(self.agent, operation="storyboard_generate", prompt=prompt)
        if not run.ok:
            return run
        try:
            raw_blocks = parse_storyboard_blocks(run.data)
            run.data = assign_storyboard_blocks(
                [{"role": b["role"], "focus": b["focus"]} for b in raw_blocks],
                version=1,
            )
        except (EditorialParseError, ValueError) as exc:
            return EditorialRunResult(ok=False, error=str(exc), agent_result=run.agent_result, prompt=prompt)
        return run


class BlockDraftGenerator:
    def __init__(self, agent: AgentWrapper) -> None:
        self.agent = agent

    def sortear_personas(self) -> list[dict[str, str]]:
        return random.sample(EDITORIAL_PERSONAS, 3)

    def gerar_abordagens(
        self,
        state: TuiSessionState,
        flow: dict[str, Any],
        *,
        block: dict[str, Any],
        block_position: int,
        total_blocks: int,
    ) -> EditorialRunResult:
        previous_selected = collect_previous_selected_drafts(flow, str(block.get("id", "")))
        context = {
            **_storyboard_context(state, flow),
            "blockRole": block.get("role", ""),
            "blockFocus": block.get("focus", ""),
            "blockPosition": block_position,
            "totalBlocks": total_blocks,
            "previousSelectedDraftsJson": _json_dumps(previous_selected),
        }
        prompt = _resolve_editorial_prompt("block_approaches_generate", context)
        run = _run_json_llm(self.agent, operation="block_approaches_generate", prompt=prompt)
        if not run.ok:
            return run
        try:
            run.data = parse_approaches(run.data)
        except EditorialParseError as exc:
            return EditorialRunResult(ok=False, error=exc.message, agent_result=run.agent_result, prompt=prompt)
        return run

    def gerar_rascunho(
        self,
        state: TuiSessionState,
        flow: dict[str, Any],
        *,
        block: dict[str, Any],
        block_position: int,
        total_blocks: int,
        approach: dict[str, str],
        persona: dict[str, str],
    ) -> EditorialRunResult:
        storyboard = flow.get("storyboard", {})
        blocks = storyboard.get("blocks", []) if isinstance(storyboard, dict) else []
        other_blocks = [
            {"role": b.get("role"), "focus": b.get("focus")}
            for b in blocks
            if isinstance(b, dict) and b.get("id") != block.get("id")
        ]
        previous_selected = collect_previous_selected_drafts(flow, str(block.get("id", "")))
        context = {
            **_storyboard_context(state, flow),
            "blockRole": block.get("role", ""),
            "blockFocus": block.get("focus", ""),
            "blockPosition": block_position,
            "totalBlocks": total_blocks,
            "otherBlocksJson": _json_dumps(other_blocks),
            "previousSelectedDraftsJson": _json_dumps(previous_selected),
            "approachTitle": approach.get("title", ""),
            "approachDescription": approach.get("description", ""),
            "personaId": persona.get("id", ""),
            "personaName": persona.get("name", ""),
        }
        prompt = _resolve_editorial_prompt("block_draft_generate", context)
        run = _run_json_llm(self.agent, operation="block_draft_generate", prompt=prompt)
        if not run.ok:
            return run
        try:
            run.data = parse_draft_content(run.data)
        except EditorialParseError as exc:
            return EditorialRunResult(ok=False, error=exc.message, agent_result=run.agent_result, prompt=prompt)
        return run


class EditorialComposer:
    def __init__(self, agent: AgentWrapper) -> None:
        self.agent = agent

    def compose(
        self,
        state: TuiSessionState,
        flow: dict[str, Any],
        *,
        selected_drafts: list[dict[str, Any]],
    ) -> tuple[ConteudoGerado | None, EditorialRunResult]:
        context, anchors = _composition_context(
            state,
            flow,
            selected_drafts=selected_drafts,
        )
        prompt = _resolve_editorial_prompt("editorial_compose", context)
        run = _run_json_llm(self.agent, operation="editorial_compose", prompt=prompt)
        if not run.ok:
            return None, run

        if not isinstance(run.data, dict):
            return None, EditorialRunResult(
                ok=False,
                error="Composicao retornou um payload JSON que nao e objeto.",
                agent_result=run.agent_result,
                prompt=prompt,
            )

        issues = validate_composition_preservation(run.data, anchors)
        retried_for_preservation = False
        if issues:
            retried_for_preservation = True
            retry_prompt = _resolve_editorial_prompt(
                "editorial_compose",
                {
                    **context,
                    "retry_attempt": 1,
                    "preservation_issues": format_preservation_issues(issues),
                },
            )
            retry = _run_json_llm(
                self.agent,
                operation="editorial_compose",
                prompt=retry_prompt,
            )
            if not retry.ok:
                return None, retry
            if not isinstance(retry.data, dict):
                return None, EditorialRunResult(
                    ok=False,
                    error="Revisao editorial retornou um payload JSON que nao e objeto.",
                    agent_result=retry.agent_result,
                    prompt=retry_prompt,
                )
            remaining_issues = validate_composition_preservation(retry.data, anchors)
            if remaining_issues:
                return None, EditorialRunResult(
                    ok=False,
                    error=(
                        "A composicao descartou material editorial prioritario apos a revisao:\n"
                        f"{format_preservation_issues(remaining_issues)}"
                    ),
                    agent_result=retry.agent_result,
                    prompt=retry_prompt,
                )
            run = retry
        try:
            conteudo = parse_generation_payload(run.data, agent_result=run.agent_result)
            conteudo.metadados.setdefault(
                "editorialPreservation",
                {
                    "protectedAnchors": len(anchors),
                    "retried": retried_for_preservation,
                },
            )
            return conteudo, run
        except Exception as exc:  # noqa: BLE001
            return None, EditorialRunResult(
                ok=False,
                error=str(exc),
                agent_result=run.agent_result,
                prompt=prompt,
            )


def build_draft_options(
    approaches: list[dict[str, str]],
    personas: list[dict[str, str]],
) -> list[dict[str, Any]]:
    options: list[dict[str, Any]] = []
    for approach, persona in zip(approaches, personas, strict=True):
        options.append(
            {
                "id": new_option_id(),
                "approach": dict(approach),
                "persona_id": persona["id"],
                "persona_name": persona["name"],
                "content": "",
                "status": "pending",
                "obsolete": False,
                "error": None,
            }
        )
    return options


def _selected_draft_for_block(
    flow: dict[str, Any],
    block: dict[str, Any],
    *,
    require_selection: bool,
) -> dict[str, Any] | None:
    block_id = str(block.get("id", ""))
    by_block = flow.get("drafts", {}).get("by_block", {})
    if not isinstance(by_block, dict):
        if require_selection:
            raise ValueError(f"Bloco {block_id} sem rascunhos.")
        return None
    entry = by_block.get(block_id)
    if not isinstance(entry, dict):
        if require_selection:
            raise ValueError(f"Bloco {block_id} sem rascunhos.")
        return None
    option_id = entry.get("selected_option_id")
    if not option_id:
        if require_selection:
            raise ValueError(f"Bloco {block_id} sem selecao.")
        return None
    options = entry.get("options", [])
    if not isinstance(options, list):
        raise ValueError(f"Bloco {block_id} com opcoes invalidas.")
    match = next(
        (o for o in options if isinstance(o, dict) and o.get("id") == option_id),
        None,
    )
    if match is None or not str(match.get("content", "")).strip():
        raise ValueError(f"Bloco {block_id} com selecao invalida.")
    return {
        "block_id": block_id,
        "role": block.get("role"),
        "focus": block.get("focus"),
        "content": match.get("content"),
        "persona_id": match.get("persona_id"),
        "approach": match.get("approach"),
    }


def collect_previous_selected_drafts(flow: dict[str, Any], block_id: str) -> list[dict[str, Any]]:
    storyboard = flow.get("storyboard", {})
    blocks = storyboard.get("blocks", []) if isinstance(storyboard, dict) else []
    if not isinstance(blocks, list):
        return []
    selected: list[dict[str, Any]] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        current_id = str(block.get("id", ""))
        if current_id == block_id:
            break
        draft = _selected_draft_for_block(flow, block, require_selection=True)
        if draft is not None:
            selected.append(draft)
    return selected


def collect_selected_drafts(flow: dict[str, Any]) -> list[dict[str, Any]]:
    storyboard = flow.get("storyboard", {})
    blocks = storyboard.get("blocks", []) if isinstance(storyboard, dict) else []
    selected: list[dict[str, Any]] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        draft = _selected_draft_for_block(flow, block, require_selection=True)
        if draft is not None:
            selected.append(draft)
    return selected
