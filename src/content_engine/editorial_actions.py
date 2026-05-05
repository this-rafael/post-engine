"""Orquestracao das actions editoriais V3."""
from __future__ import annotations

import time
from typing import Any, Callable, Protocol

from .editorial_flow import (
    assign_storyboard_blocks,
    clear_downstream_if_editorial_origin,
    compute_briefing_fingerprint,
    compute_selection_fingerprint,
    empty_editorial_flow,
    invalidate_drafts_and_composition,
    normalize_editorial_flow,
)
from .editorial_generation import (
    BlockDraftGenerator,
    EditorialComposer,
    StoryboardGenerator,
    build_draft_options,
    collect_selected_drafts,
)
from .generator import ConteudoGerado
from .llm_config import resolve
from .schemas import TuiSessionState


class EditorialHost(Protocol):
    state: TuiSessionState

    def _persistir(self) -> None: ...
    def _log_event(self, event_type: str, operation: str, payload: dict[str, Any] | None = None) -> None: ...


AgentFactory = Callable[[], Any]


def _ensure_flow(state: TuiSessionState) -> dict[str, Any]:
    if not state.editorial_flow:
        state.editorial_flow = empty_editorial_flow()
    return normalize_editorial_flow(state.editorial_flow)


def _sync_briefing_fingerprint(host: EditorialHost) -> None:
    flow = _ensure_flow(host.state)
    current = compute_briefing_fingerprint(host.state)
    if flow.get("briefing_fingerprint") and flow["briefing_fingerprint"] != current:
        invalidate_drafts_and_composition(flow)
        flow["storyboard"] = {"version": 0, "status": "obsolete", "blocks": []}
        clear_downstream_if_editorial_origin(host.state)
    flow["briefing_fingerprint"] = current
    host.state.editorial_flow = flow


def action_generate_storyboard(host: EditorialHost, agent_factory: AgentFactory) -> None:
    _sync_briefing_fingerprint(host)
    flow = _ensure_flow(host.state)
    started = time.monotonic()
    generator = StoryboardGenerator(agent_factory())
    run = generator.gerar(host.state, flow)
    cfg = resolve("storyboard_generate")
    if not run.ok:
        flow["storyboard"] = {"version": flow.get("storyboard", {}).get("version", 0), "status": "failed", "blocks": []}
        host.state.error = run.error
        host._log_event(
            "llm_response",
            "editorial.storyboard.generate",
            {
                "status": "failed",
                "error": run.error,
                "provider": cfg.provider,
                "model": cfg.model,
                "duration_ms": int((time.monotonic() - started) * 1000),
            },
        )
    else:
        blocks = run.data
        version = int(flow.get("storyboard", {}).get("version", 0)) + 1
        invalidate_drafts_and_composition(flow)
        flow["storyboard"] = {"version": version, "status": "available", "blocks": blocks}
        flow["drafts"]["storyboard_version"] = version
        host.state.error = None
        host._log_event(
            "llm_response",
            "editorial.storyboard.generate",
            {
                "status": "available",
                "block_count": len(blocks),
                "provider": cfg.provider,
                "model": cfg.model,
                "duration_ms": int((time.monotonic() - started) * 1000),
            },
        )
    host.state.editorial_flow = flow
    host._persistir()


def action_update_storyboard(host: EditorialHost, blocks: list[dict[str, Any]]) -> None:
    _sync_briefing_fingerprint(host)
    flow = _ensure_flow(host.state)
    version = int(flow.get("storyboard", {}).get("version", 0)) + 1
    assigned = assign_storyboard_blocks(blocks, version=version)
    invalidate_drafts_and_composition(flow)
    clear_downstream_if_editorial_origin(host.state)
    flow["storyboard"] = {"version": version, "status": "available", "blocks": assigned}
    flow["drafts"]["storyboard_version"] = version
    host.state.editorial_flow = flow
    host.state.error = None
    host._persistir()


def action_clear_storyboard(host: EditorialHost) -> None:
    flow = empty_editorial_flow()
    flow["briefing_fingerprint"] = compute_briefing_fingerprint(host.state)
    invalidate_drafts_and_composition(flow, mark_obsolete=False)
    clear_downstream_if_editorial_origin(host.state)
    host.state.editorial_flow = flow
    host.state.error = None
    host._persistir()


def _block_entry(flow: dict[str, Any], block_id: str) -> dict[str, Any]:
    drafts = flow.setdefault("drafts", {"storyboard_version": 0, "by_block": {}})
    by_block = drafts.setdefault("by_block", {})
    entry = by_block.get(block_id)
    if not isinstance(entry, dict):
        entry = {"status": "empty", "options": [], "selected_option_id": None}
        by_block[block_id] = entry
    return entry


def _find_block(flow: dict[str, Any], block_id: str) -> dict[str, Any]:
    blocks = flow.get("storyboard", {}).get("blocks", [])
    if not isinstance(blocks, list):
        raise ValueError("Storyboard indisponivel.")
    for block in blocks:
        if isinstance(block, dict) and block.get("id") == block_id:
            return block
    raise ValueError(f"Bloco nao encontrado: {block_id}")


def _assert_prior_blocks_selected(flow: dict[str, Any], block_id: str) -> None:
    blocks = flow.get("storyboard", {}).get("blocks", [])
    if not isinstance(blocks, list):
        raise ValueError("Storyboard indisponivel.")
    for block in blocks:
        if not isinstance(block, dict):
            continue
        current_id = str(block.get("id", ""))
        if current_id == block_id:
            return
        by_block = flow.get("drafts", {}).get("by_block", {})
        if not isinstance(by_block, dict):
            raise ValueError(f"Selecione o bloco anterior antes de gerar: {block.get('role', current_id)}")
        entry = by_block.get(current_id)
        if not isinstance(entry, dict) or not entry.get("selected_option_id"):
            raise ValueError(f"Selecione o bloco anterior antes de gerar: {block.get('role', current_id)}")
        options = entry.get("options", [])
        if not isinstance(options, list):
            raise ValueError(f"Selecione o bloco anterior antes de gerar: {block.get('role', current_id)}")
        selected_id = entry.get("selected_option_id")
        match = next(
            (o for o in options if isinstance(o, dict) and o.get("id") == selected_id),
            None,
        )
        if match is None or not str(match.get("content", "")).strip():
            raise ValueError(f"Selecione o bloco anterior antes de gerar: {block.get('role', current_id)}")


def _invalidate_downstream_drafts(flow: dict[str, Any], block_id: str) -> None:
    blocks = flow.get("storyboard", {}).get("blocks", [])
    if not isinstance(blocks, list):
        return
    drafts = flow.setdefault("drafts", {"storyboard_version": 0, "by_block": {}})
    by_block = drafts.setdefault("by_block", {})
    if not isinstance(by_block, dict):
        return
    found = False
    for block in blocks:
        if not isinstance(block, dict):
            continue
        current_id = str(block.get("id", ""))
        if current_id == block_id:
            found = True
            continue
        if found:
            by_block.pop(current_id, None)


def _generate_block_drafts_internal(
    host: EditorialHost,
    agent_factory: AgentFactory,
    block_id: str,
) -> None:
    _sync_briefing_fingerprint(host)
    flow = _ensure_flow(host.state)
    try:
        _assert_prior_blocks_selected(flow, block_id)
    except ValueError as exc:
        host.state.error = str(exc)
        host._persistir()
        return
    block = _find_block(flow, block_id)
    blocks = flow["storyboard"]["blocks"]
    position = next(
        (i for i, b in enumerate(blocks, start=1) if b.get("id") == block_id),
        1,
    )
    generator = BlockDraftGenerator(agent_factory())
    cfg_approaches = resolve("block_approaches_generate")
    cfg_draft = resolve("block_draft_generate")

    entry = _block_entry(flow, block_id)
    entry["status"] = "generating"
    entry["selected_option_id"] = None
    host.state.editorial_flow = flow
    host._persistir()

    approaches_run = generator.gerar_abordagens(
        host.state,
        flow,
        block=block,
        block_position=position,
        total_blocks=len(blocks),
    )
    if not approaches_run.ok:
        entry["status"] = "failed"
        entry["error"] = approaches_run.error
        host.state.error = approaches_run.error
        host.state.editorial_flow = flow
        host._persistir()
        return

    personas = generator.sortear_personas()
    options = build_draft_options(approaches_run.data, personas)
    entry["options"] = options
    entry["status"] = "partial"
    host.state.editorial_flow = flow
    host._persistir()

    for option in options:
        option["status"] = "generating"
        host.state.editorial_flow = flow
        host._persistir()
        draft_run = generator.gerar_rascunho(
            host.state,
            flow,
            block=block,
            block_position=position,
            total_blocks=len(blocks),
            approach=option["approach"],
            persona={"id": option["persona_id"], "name": option["persona_name"]},
        )
        if draft_run.ok:
            option["content"] = draft_run.data
            option["status"] = "available"
            option["error"] = None
            option["provider"] = cfg_draft.provider
            option["model"] = cfg_draft.model
        else:
            option["status"] = "failed"
            option["error"] = draft_run.error
        host.state.editorial_flow = flow
        host._persistir()

    failed = [o for o in options if o.get("status") == "failed"]
    available = [o for o in options if o.get("status") == "available"]
    if len(available) == 3:
        entry["status"] = "available"
        entry["error"] = None
    elif available:
        entry["status"] = "partial"
        entry["error"] = f"{len(failed)} opcao(oes) falharam."
    else:
        entry["status"] = "failed"
        entry["error"] = "Todas as opcoes falharam."
    entry["provider"] = cfg_approaches.provider
    entry["model"] = cfg_approaches.model
    flow["composition"] = {
        "status": "empty",
        "selection_fingerprint": "",
        "conteudo": "",
        "conteudo_json": {},
    }
    host.state.editorial_flow = flow
    host.state.error = entry.get("error")
    host._persistir()


def action_generate_block_drafts(
    host: EditorialHost,
    agent_factory: AgentFactory,
    *,
    block_id: str,
) -> None:
    _generate_block_drafts_internal(host, agent_factory, block_id)


def action_generate_all_block_drafts(host: EditorialHost, agent_factory: AgentFactory) -> None:
    del agent_factory
    host.state.error = "Geracao em lote desabilitada. Gere bloco a bloco em ordem."
    host._persistir()


def action_retry_block_draft(
    host: EditorialHost,
    agent_factory: AgentFactory,
    *,
    block_id: str,
    option_id: str,
) -> None:
    flow = _ensure_flow(host.state)
    try:
        _assert_prior_blocks_selected(flow, block_id)
    except ValueError as exc:
        host.state.error = str(exc)
        host._persistir()
        return
    block = _find_block(flow, block_id)
    blocks = flow["storyboard"]["blocks"]
    position = next(
        (i for i, b in enumerate(blocks, start=1) if b.get("id") == block_id),
        1,
    )
    entry = _block_entry(flow, block_id)
    options = entry.get("options", [])
    if not isinstance(options, list):
        raise ValueError("Opcoes indisponiveis.")
    option = next((o for o in options if isinstance(o, dict) and o.get("id") == option_id), None)
    if option is None:
        raise ValueError(f"Opcao nao encontrada: {option_id}")

    generator = BlockDraftGenerator(agent_factory())
    option["status"] = "generating"
    option["error"] = None
    host.state.editorial_flow = flow
    host._persistir()

    draft_run = generator.gerar_rascunho(
        host.state,
        flow,
        block=block,
        block_position=position,
        total_blocks=len(blocks),
        approach=option["approach"],
        persona={"id": option["persona_id"], "name": option["persona_name"]},
    )
    cfg = resolve("block_draft_generate")
    if draft_run.ok:
        option["content"] = draft_run.data
        option["status"] = "available"
        option["provider"] = cfg.provider
        option["model"] = cfg.model
    else:
        option["status"] = "failed"
        option["error"] = draft_run.error
        host.state.error = draft_run.error

    available = [o for o in options if isinstance(o, dict) and o.get("status") == "available"]
    entry["status"] = "available" if len(available) == 3 else "partial"
    flow["composition"] = {
        "status": "empty",
        "selection_fingerprint": "",
        "conteudo": "",
        "conteudo_json": {},
    }
    host.state.editorial_flow = flow
    host._persistir()


def action_select_block_draft(
    host: EditorialHost,
    *,
    block_id: str,
    option_id: str,
) -> None:
    flow = _ensure_flow(host.state)
    entry = _block_entry(flow, block_id)
    options = entry.get("options", [])
    if not isinstance(options, list):
        raise ValueError("Opcoes indisponiveis.")
    if not any(isinstance(o, dict) and o.get("id") == option_id for o in options):
        raise ValueError(f"Opcao invalida: {option_id}")
    _invalidate_downstream_drafts(flow, block_id)
    entry["selected_option_id"] = option_id
    flow["composition"] = {
        "status": "empty",
        "selection_fingerprint": "",
        "conteudo": "",
        "conteudo_json": {},
    }
    clear_downstream_if_editorial_origin(host.state)
    host.state.editorial_flow = flow
    host._persistir()


def action_compose_editorial(
    host: EditorialHost,
    agent_factory: AgentFactory,
    *,
    phase_segmentacao: str,
) -> None:
    flow = _ensure_flow(host.state)
    try:
        selected = collect_selected_drafts(flow)
    except ValueError as exc:
        host.state.error = str(exc)
        host._persistir()
        return

    composer = EditorialComposer(agent_factory())
    started = time.monotonic()
    conteudo, run = composer.compose(host.state, flow, selected_drafts=selected)
    cfg = resolve("editorial_compose")
    if not run.ok or conteudo is None:
        flow["composition"] = {
            "status": "failed",
            "selection_fingerprint": compute_selection_fingerprint(flow),
            "conteudo": "",
            "conteudo_json": {},
        }
        host.state.error = run.error
        host._log_event(
            "llm_response",
            "editorial.compose",
            {"status": "failed", "error": run.error, "provider": cfg.provider, "model": cfg.model},
        )
        host.state.editorial_flow = flow
        host._persistir()
        return

    _apply_composition_result(host, flow, conteudo, phase_segmentacao)
    host._log_event(
        "llm_response",
        "editorial.compose",
        {
            "status": "available",
            "provider": cfg.provider,
            "model": cfg.model,
            "duration_ms": int((time.monotonic() - started) * 1000),
        },
    )


def _apply_composition_result(
    host: EditorialHost,
    flow: dict[str, Any],
    conteudo: ConteudoGerado,
    phase_segmentacao: str,
) -> None:
    selection_fp = compute_selection_fingerprint(flow)
    conteudo_json: dict[str, Any] = {
        "conteudo": conteudo.conteudo,
        "metadados": conteudo.metadados,
        "alertas": conteudo.alertas,
    }
    if conteudo.slidemark is not None:
        conteudo_json["slidemark"] = conteudo.slidemark
    if conteudo.sugestoes_imagem:
        conteudo_json["sugestoesImagem"] = conteudo.sugestoes_imagem
    if conteudo.slides:
        conteudo_json["slides"] = [
            {
                "numero": s.numero,
                "titulo": s.titulo,
                "bullets": s.bullets,
                "notasVisuais": s.notas_visuais,
            }
            for s in conteudo.slides
        ]

    flow["composition"] = {
        "status": "available",
        "selection_fingerprint": selection_fp,
        "conteudo": conteudo.conteudo,
        "conteudo_json": conteudo_json,
    }
    host.state.editorial_flow = flow
    host.state.conteudo_gerado = conteudo.conteudo
    host.state.conteudo_json = conteudo_json
    host.state.segmentos = []
    host.state.avaliacao_post = {}
    host.state.current_phase = phase_segmentacao
    host.state.error = None
    host.state.prompt_renderizado = ""
    host.state.stdout = conteudo.agent_result.stdout if conteudo.agent_result else ""
    host.state.returncode = conteudo.agent_result.returncode if conteudo.agent_result else 0
    host._persistir()
