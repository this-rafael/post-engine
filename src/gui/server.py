"""HTTP server for the React GUI mode.

The GUI intentionally reuses the Textual app orchestration layer so both modes
operate on the same persisted session shape.
"""
from __future__ import annotations

import json
import mimetypes
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import RLock
from typing import Any
from urllib.parse import parse_qs, urlparse

from content_engine import adjust_segment as _adjust_segment
from content_engine import adjust_segments_bulk as _adjust_segments_bulk
from content_engine import exporter as _exporter
from content_engine import persistence as _persistence
from content_engine import slidemark_converter as _slidemark_converter
from content_engine.llm_config import (
    LLM_OPERATIONS,
    OPERATION_LABELS,
    LlmOperationConfig,
    ensure_default_config_file,
    list_operations,
    list_providers,
    load_global_config,
    provider_status,
    resolve_all,
    save_global_config,
)
from content_engine.prompt_registry.api import PromptRegistryApi
from content_engine.prompt_registry.repository import PromptRegistryError
from content_engine.prompt_registry.resolver import PromptResolutionError
from content_engine.schemas import (
    FERRAMENTAS_VALIDAS,
    SANDBOXES_VALIDOS,
    migrate_tipo_de_post,
)
from content_engine.editorial_flow import derive_editorial_status, normalize_editorial_flow
from content_engine.interview.ui import build_interview_ui
from content_engine.phase_progress import PHASE_TO_STAGE as PROGRESS_PHASE_TO_STAGE
from content_engine.phase_progress import phase_progress, released_phases
from content_engine.trilhas import SELECT_OPCOES, is_trilha_visual
from content_engine.session_controller import (
    PHASE_AVALIACAO,
    PHASE_BRIEFING,
    PHASE_ENTRADA,
    PHASE_ENTREVISTA,
    PHASE_EXECUCAO,
    PHASE_EXPORTACAO,
    PHASE_PROMPT,
    PHASE_SEGMENTACAO,
    SessionController,
    SCORE_AVALIACAO_ASPECTOS,
)


STATIC_DIR = Path(__file__).with_name("static")
DIST_DIR = STATIC_DIR / "dist"

PHASE_LABELS: dict[str, str] = {
    PHASE_ENTRADA: "Entrada",
    PHASE_ENTREVISTA: "Entrevista",
    PHASE_BRIEFING: "Briefing",
    PHASE_PROMPT: "Prompt",
    PHASE_EXECUCAO: "Execucao",
    PHASE_SEGMENTACAO: "Segmentacao",
    PHASE_AVALIACAO: "Avaliacao",
    PHASE_EXPORTACAO: "Exportacao",
}

PHASES: tuple[str, ...] = tuple(PHASE_LABELS)

STAGE_LABELS: dict[str, str] = {
    "agents": "Agentes",
    "entry": "Entrada",
    "interview": "Entrevista",
    "briefing": "Briefing",
    "storyboard": "Storyboard",
    "drafts": "Rascunhos",
    "composition": "Composicao",
    "prompt": "Prompt",
    "execution": "Execucao",
    "segmentation": "Segmentacao",
    "evaluation": "Avaliacao",
    "export": "Exportacao",
}

PHASE_TO_STAGE: dict[str, str] = {
    PHASE_ENTRADA: "entry",
    PHASE_ENTREVISTA: "interview",
    PHASE_BRIEFING: "briefing",
    PHASE_PROMPT: "prompt",
    PHASE_EXECUCAO: "execution",
    PHASE_SEGMENTACAO: "segmentation",
    PHASE_AVALIACAO: "evaluation",
    PHASE_EXPORTACAO: "export",
}

PLATFORM_OPTIONS: tuple[dict[str, str], ...] = (
    {"label": "LinkedIn", "value": "linkedin"},
    {"label": "Instagram", "value": "instagram"},
    {"label": "TikTok", "value": "tiktok"},
    {"label": "YouTube", "value": "youtube"},
    {"label": "Blog", "value": "blog"},
)

EDITABLE_FIELDS: set[str] = {
    "tema",
    "plataforma",
    "objetivo_do_post",
    "personalidade",
    "tipo_de_post",
    "tool",
    "model",
    "sandbox",
    "conteudo_gerado",
    "segmentos",
    "briefing_autoral",
    "restricoes_de_geracao",
}


def _coerce_trechos_fracos(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    items: list[dict[str, Any]] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        items.append(
            {
                "trecho": entry.get("trecho", ""),
                "problema": str(entry.get("problema", "") or ""),
                "severidade": str(entry.get("severidade", "") or ""),
                "motivo": str(entry.get("motivo", "") or ""),
            }
        )
    return items


def _build_avaliacao_ui(app: SessionController) -> dict[str, Any]:
    avaliacao = app.state.avaliacao_post
    trechos_raw = avaliacao.get("trechos_fracos", []) if isinstance(avaliacao, dict) else []
    return {
        "valida": app._avaliacao_post_valida(),
        "scores": {
            aspecto: app._render_post_score(aspecto)
            for aspecto in SCORE_AVALIACAO_ASPECTOS
        },
        "veredito": app._render_avaliacao_texto("veredito"),
        "pontos_fortes": app._render_avaliacao_lista("pontos_fortes"),
        "pontos_fracos": app._render_avaliacao_lista("pontos_fracos"),
        "sugestoes": app._render_avaliacao_lista("sugestoes"),
        "redundancias": app._render_avaliacao_lista("redundancias"),
        "falhas_tecnicas": app._render_avaliacao_lista("falhas_tecnicas"),
        "trechos_fracos": _coerce_trechos_fracos(trechos_raw),
    }


class GuiController:
    def __init__(self, session_path: Path | None = None) -> None:
        self._lock = RLock()
        ensure_default_config_file()
        self.app = SessionController(
            session_path=session_path,
            run_sync_inline=True,
        )

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            app = self.app
            state = app.state
            active_stage = self._active_stage()
            active_label = STAGE_LABELS.get(active_stage, "Entrada")
            return {
                "state": asdict(state),
                "derived": {
                    "phase_label": PHASE_LABELS.get(state.current_phase, "Entrada"),
                    "active_stage": active_stage,
                    "active_stage_label": active_label,
                    "active_status_text": f"Fase ativa: {active_label}.",
                    "phase_order": list(PHASES),
                    "phase_labels": dict(PHASE_LABELS),
                    "phase_progress": phase_progress(state, PHASE_LABELS),
                    "jornada": app._render_jornada(),
                    "persona_ativa": app._render_persona_ativa(),
                    "interview": build_interview_ui(getattr(state, "interview_state", None)),
                    "post_scores": {
                        aspecto: app._render_post_score(aspecto)
                        for aspecto in SCORE_AVALIACAO_ASPECTOS
                    },
                    "avaliacao_ui": _build_avaliacao_ui(app),
                    "conteudo_final": app._conteudo_final(),
                    "segmento_atual": app._segmento_atual_texto(),
                    "segmento_reescrito": app._segmento_reescrito,
                    "segmentos_reescritos": {
                        str(index): texto
                        for index, texto in sorted(app._segmentos_reescritos.items())
                    },
                    "default_export_path": str(app._default_export_path("md")),
                    "is_trilha_visual": is_trilha_visual(state.tipo_de_post),
                    "has_slidemark": isinstance(
                        state.conteudo_json.get("slidemark"), dict
                    ),
                    "serialized": {
                        "briefing": app._serialize_briefing(),
                        "historico": app._serialize_historico_entrevista(),
                        "historico_recente": app._serialize_historico_recente(),
                        "conteudo_json": app._serialize_conteudo_json(),
                        "segmentos": app._serialize_segmentos(),
                        "avaliacao_post": app._serialize_avaliacao_post(),
                        "events": app._serialize_events(),
                    },
                    "effective_llm_config": {
                        op: cfg.to_dict()
                        for op, cfg in resolve_all().items()
                    },
                    "editorial": derive_editorial_status(
                        normalize_editorial_flow(state.editorial_flow)
                    ),
                },
                "options": {
                    "plataformas": list(PLATFORM_OPTIONS),
                    "tipos_de_post": [
                        {"label": label, "value": value}
                        for label, value in SELECT_OPCOES
                    ],
                    "tools": list_providers(),
                    "sandboxes": [
                        {"label": value, "value": value}
                        for value in SANDBOXES_VALIDOS
                    ],
                    "llm_operations": list_operations(),
                    "provider_status": provider_status(),
                },
            }

    def _active_stage(self) -> str:
        stage = str(getattr(self.app.state, "current_stage", "") or "")
        if stage in STAGE_LABELS:
            return stage
        return PHASE_TO_STAGE.get(self.app.state.current_phase, "entry")

    def _set_active_stage(self, stage: str, *, update_status: bool = True) -> None:
        if stage not in STAGE_LABELS:
            stage = "entry"
        self.app.state.current_stage = stage
        if update_status:
            self.app.state.status_operacional = f"Fase ativa: {STAGE_LABELS[stage]}."

    def llm_config_snapshot(self) -> dict[str, Any]:
        with self._lock:
            global_cfg = load_global_config()
            return {
                "operations": {
                    op: cfg.to_dict()
                    for op, cfg in global_cfg.items()
                },
                "operation_labels": dict(OPERATION_LABELS),
                "providers": list_providers(),
                "provider_status": provider_status(),
            }

    def update_llm_config(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            operations_raw = payload.get("operations", {})
            if not isinstance(operations_raw, dict):
                raise ValueError("operations precisa ser um objeto")
            current = load_global_config()
            updated: dict[str, LlmOperationConfig] = dict(current)
            for op, raw in operations_raw.items():
                if op not in LLM_OPERATIONS:
                    continue
                merged = LlmOperationConfig.from_dict(
                    {**current.get(op, LlmOperationConfig()).to_dict(), **raw}
                    if isinstance(raw, dict)
                    else current.get(op, LlmOperationConfig()).to_dict()
                )
                updated[op] = merged
            save_global_config(updated)
            self.app._generator = None
            self.app._generator_config = None
            return self.llm_config_snapshot()

    def update(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._apply_state_patch(payload)
            self.app._persistir()
            return self.snapshot()

    def action(self, name: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = payload or {}
        with self._lock:
            state_patch = payload.get("state")
            if isinstance(state_patch, dict):
                self._apply_state_patch(state_patch)

            try:
                self._dispatch(name, payload)
            except Exception as exc:  # noqa: BLE001
                self.app.state.error = str(exc)
                self.app.state.status_operacional = f"Erro na acao {name}: {exc}"
            finally:
                self.app._persistir()
            return self.snapshot()

    def restore(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            restored = _persistence.carregar_sessao_de_payload(payload)
            self.app._ativar_sessao_restaurada(restored)
            return self.snapshot()

    def _apply_state_patch(self, payload: dict[str, Any]) -> None:
        state = self.app.state
        for key, value in payload.items():
            if key not in EDITABLE_FIELDS:
                continue
            if key == "tipo_de_post":
                setattr(state, key, migrate_tipo_de_post(value))
            elif key == "tool":
                if value in FERRAMENTAS_VALIDAS:
                    setattr(state, key, value)
            elif key == "sandbox":
                if value in SANDBOXES_VALIDOS:
                    setattr(state, key, value)
            elif key == "model":
                text = str(value).strip() if value is not None else ""
                state.model = text or None
            elif key == "segmentos":
                state.segmentos = [
                    dict(item) for item in value if isinstance(item, dict)
                ] if isinstance(value, list) else []
            elif key == "restricoes_de_geracao":
                state.restricoes_de_geracao = [
                    str(item) for item in value
                ] if isinstance(value, list) else []
            elif key == "briefing_autoral":
                if isinstance(value, dict):
                    setattr(state, key, dict(value))
            else:
                setattr(state, key, str(value) if value is not None else "")

    def _dispatch(self, name: str, payload: dict[str, Any]) -> None:
        if name == "continue_phase1":
            self.app.action_continue_phase1()
            self._set_active_stage("interview")
        elif name == "start_interview_v4":
            self.app.action_start_interview_v4()
            self._set_active_stage("interview")
        elif name == "submit_v4_answer":
            response = payload.get("response", payload.get("answer"))
            self.app.action_submit_v4_answer(
                str(response) if response is not None else None,
                user_requested_end=bool(payload.get("user_requested_end", False)),
            )
            self._set_active_stage("interview")
        elif name == "close_v4_interview":
            self.app.action_close_interview_v4()
            self._set_active_stage("interview")
        elif name == "diagnose_interview_gaps":
            self.app.action_diagnose_interview_gaps(
                force=bool(payload.get("force", False)),
            )
            self._set_active_stage("interview")
        elif name == "start_extension_batch":
            count = payload.get("count", 5)
            self.app.action_start_extension_batch(int(count) if count is not None else 5)
            self._set_active_stage("interview")
        elif name == "submit_extension_batch":
            responses = payload.get("responses", payload.get("answers", []))
            if not isinstance(responses, list):
                responses = []
            self.app.action_submit_extension_batch(responses)
            self._set_active_stage("interview")
        elif name == "clear_phase1":
            self.app.action_clear_phase1()
        elif name == "reset_phase":
            self.app.action_reset_phase()
        elif name == "reset_context":
            self.app.action_reset_context()
            self._set_active_stage("entry", update_status=False)
        elif name == "generate_other_question":
            self.app.action_generate_other_question()
            self._set_active_stage("interview")
        elif name == "submit_round":
            response = payload.get("response", payload.get("answer"))
            self.app.action_submit_round(
                str(response) if response is not None else None
            )
            self._set_active_stage("interview")
        elif name == "continue_phase2":
            self.app.action_continue_phase2()
            self._set_active_stage("briefing")
        elif name == "render_prompt":
            self._render_prompt()
        elif name == "run":
            self._run_llm()
        elif name == "clear_outputs":
            self.app.action_clear()
        elif name == "segment":
            self.app.action_segment()
            self._set_active_stage("segmentation")
        elif name == "rewrite_segment":
            self._rewrite_segment(payload)
        elif name == "apply_segment":
            self._apply_segment(payload)
        elif name == "cancel_adjust":
            self.app._segmento_reescrito = ""
        elif name == "rewrite_segments_bulk":
            self._rewrite_segments_bulk(payload)
        elif name == "apply_segments_bulk":
            self._apply_segments_bulk(payload)
        elif name == "cancel_bulk_adjust":
            self.app._segmentos_reescritos = {}
        elif name == "set_segment_index":
            self._set_segment_index(payload)
        elif name == "evaluate":
            self.app.action_evaluate()
            self._set_active_stage("evaluation")
        elif name == "export":
            self._export(payload)
        elif name == "export_slidemark":
            self._export_slidemark(payload)
        elif name == "navigate":
            self._navigate(payload)
        elif name == "generate_storyboard":
            self.app.action_generate_storyboard()
            self._set_active_stage("storyboard")
        elif name == "update_storyboard":
            self.app.action_update_storyboard(list(payload.get("blocks", [])))
            self._set_active_stage("storyboard")
        elif name == "clear_storyboard":
            self.app.action_clear_storyboard()
            self._set_active_stage("storyboard")
        elif name == "generate_block_drafts":
            self.app.action_generate_block_drafts(str(payload.get("block_id", "")))
            self._set_active_stage("drafts")
        elif name == "generate_all_block_drafts":
            self.app.action_generate_all_block_drafts()
            self._set_active_stage("drafts")
        elif name == "retry_block_draft":
            self.app.action_retry_block_draft(
                str(payload.get("block_id", "")),
                str(payload.get("option_id", "")),
            )
            self._set_active_stage("drafts")
        elif name == "select_block_draft":
            self.app.action_select_block_draft(
                str(payload.get("block_id", "")),
                str(payload.get("option_id", "")),
            )
            self._set_active_stage("drafts")
        elif name == "compose_editorial":
            self.app.action_compose_editorial()
            self._set_active_stage("segmentation")
        else:
            raise ValueError(f"acao desconhecida: {name}")

    def _render_prompt(self) -> None:
        self.app._garantir_prompt_para_fase4()
        self.app.state.current_phase = PHASE_PROMPT
        self.app.state.fase_atual = "prompt"
        self._set_active_stage("prompt")

    def _run_llm(self) -> None:
        if not self.app.state.prompt_renderizado.strip():
            self._render_prompt()
        self.app.state.is_running = True
        self.app.state.current_phase = PHASE_EXECUCAO
        self.app.state.current_stage = "execution"
        self.app._set_status("Execucao LLM em andamento.", "execucao")
        try:
            self.app._executar_agente()
        finally:
            self.app.state.is_running = False

    def _rewrite_segment(self, payload: dict[str, Any]) -> None:
        pedido = str(payload.get("pedido", "")).strip()
        if not pedido:
            raise ValueError("pedido de ajuste nao pode ser vazio")
        index = _coerce_index(payload.get("index"), len(self.app.state.segmentos))
        self.app.state._segmento_index = index
        self.app._segmento_reescrito = ""
        item = self.app._segmento_atual_dict()
        if item is None:
            raise ValueError("nenhum segmento selecionado")
        cfg = self.app._llm_config("adjust_segment")
        adjuster = _adjust_segment.SegmentAdjuster(
            agent=self.app._agent_factory(),
            tool=cfg.provider,
            model=cfg.model,
            sandbox=cfg.sandbox or self.app.state.sandbox,
            opencode_agent=cfg.agent,
            reasoning_effort=cfg.reasoning_effort,
        )
        self.app._segmento_reescrito = adjuster.ajustar(
            conteudo_completo=self.app._conteudo_final(),
            segmento=self.app._segmento_post_from_dict(item),
            pedido=pedido,
            personalidade=self.app.state.personalidade or None,
            restricoes=list(self.app.state.restricoes_de_geracao),
        )
        self.app.state.status_operacional = "Segmento reescrito; revise antes de aplicar."

    def _apply_segment(self, payload: dict[str, Any]) -> None:
        index = _coerce_index(payload.get("index"), len(self.app.state.segmentos))
        texto = str(payload.get("texto") or self.app._segmento_reescrito).strip()
        if not texto:
            raise ValueError("texto do segmento nao pode ser vazio")
        if not self.app.state.segmentos:
            raise ValueError("nenhum segmento disponivel")
        segmento = dict(self.app.state.segmentos[index])
        segmento["texto"] = texto
        self.app.state.segmentos[index] = segmento
        self.app._segmento_reescrito = ""
        self.app.state.status_operacional = f"Segmento {index + 1} atualizado."

    def _trechos_fracos_por_indice(self) -> dict[int, dict[str, str]]:
        avaliacao = self.app.state.avaliacao_post
        raw = avaliacao.get("trechos_fracos", []) if isinstance(avaliacao, dict) else []
        if not isinstance(raw, list):
            return {}
        total = len(self.app.state.segmentos)
        merged: dict[int, dict[str, str]] = {}
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            index = _adjust_segments_bulk.trecho_to_segment_index(
                entry.get("trecho"), total
            )
            if index is None:
                continue
            problema = str(entry.get("problema", "") or "").strip()
            motivo = str(entry.get("motivo", "") or "").strip()
            if index not in merged:
                merged[index] = {"problema": problema, "motivo": motivo}
                continue
            if problema:
                existing = merged[index]["problema"]
                merged[index]["problema"] = (
                    f"{existing}\n{problema}" if existing else problema
                )
            if motivo:
                existing = merged[index]["motivo"]
                merged[index]["motivo"] = (
                    f"{existing}\n{motivo}" if existing else motivo
                )
        return merged

    def _rewrite_segments_bulk(self, payload: dict[str, Any]) -> None:
        raw_ajustes = payload.get("ajustes")
        if not isinstance(raw_ajustes, list) or not raw_ajustes:
            raise ValueError("ajustes nao pode ser vazio")
        if not self.app.state.segmentos:
            raise ValueError("nenhum segmento disponivel")

        trechos = self._trechos_fracos_por_indice()
        requests: list[_adjust_segments_bulk.SegmentAdjustRequest] = []
        indices: list[int] = []

        for entry in raw_ajustes:
            if not isinstance(entry, dict):
                continue
            pedido = str(entry.get("pedido", "")).strip()
            if not pedido:
                raise ValueError("pedido de ajuste nao pode ser vazio")
            index = _coerce_index(entry.get("index"), len(self.app.state.segmentos))
            item = self.app._segmento_atual_dict(index)
            if item is None:
                raise ValueError(f"segmento {index + 1} indisponivel")
            diag = trechos.get(index, {})
            requests.append(
                _adjust_segments_bulk.SegmentAdjustRequest(
                    segmento=self.app._segmento_post_from_dict(item),
                    pedido=pedido,
                    problema=diag.get("problema", ""),
                    motivo=diag.get("motivo", ""),
                )
            )
            indices.append(index)

        if not requests:
            raise ValueError("nenhum ajuste valido informado")

        cfg = self.app._llm_config("adjust_segments_bulk")
        adjuster = _adjust_segments_bulk.SegmentBulkAdjuster(
            agent=self.app._agent_factory(),
            tool=cfg.provider,
            model=cfg.model,
            sandbox=cfg.sandbox or self.app.state.sandbox,
            opencode_agent=cfg.agent,
            reasoning_effort=cfg.reasoning_effort,
        )
        reescritos_por_id = adjuster.ajustar(
            conteudo_completo=self.app._conteudo_final(),
            ajustes=requests,
            personalidade=self.app.state.personalidade or None,
            restricoes=list(self.app.state.restricoes_de_geracao),
            tipo_de_post=self.app.state.tipo_de_post,
            briefing=dict(self.app.state.briefing_autoral),
            interview_context=(
                dict(self.app.state.interview_state)
                if isinstance(self.app.state.interview_state, dict)
                else None
            ),
        )

        self.app._segmentos_reescritos = {}
        for index, request in zip(indices, requests):
            texto = reescritos_por_id.get(request.segmento.id, "").strip()
            if texto:
                self.app._segmentos_reescritos[index] = texto

        if not self.app._segmentos_reescritos:
            raise ValueError("nenhum segmento reescrito na resposta da LLM")

        count = len(self.app._segmentos_reescritos)
        self.app.state.status_operacional = (
            f"{count} segmento(s) reescrito(s); revise antes de aplicar."
        )

    def _apply_segments_bulk(self, payload: dict[str, Any]) -> None:
        if not self.app.state.segmentos:
            raise ValueError("nenhum segmento disponivel")

        raw_textos = payload.get("textos")
        if isinstance(raw_textos, dict):
            for key, value in raw_textos.items():
                index = _coerce_index(key, len(self.app.state.segmentos))
                texto = str(value or "").strip()
                if texto:
                    self.app._segmentos_reescritos[index] = texto

        if not self.app._segmentos_reescritos:
            raise ValueError("nenhuma reescrita pendente para aplicar")

        raw_indices = payload.get("indices")
        if raw_indices is None:
            target_indices = list(self.app._segmentos_reescritos.keys())
        elif isinstance(raw_indices, list):
            target_indices = [
                _coerce_index(value, len(self.app.state.segmentos))
                for value in raw_indices
            ]
        else:
            target_indices = [_coerce_index(raw_indices, len(self.app.state.segmentos))]

        applied = 0
        for index in target_indices:
            texto = self.app._segmentos_reescritos.get(index, "").strip()
            if not texto:
                continue
            segmento = dict(self.app.state.segmentos[index])
            segmento["texto"] = texto
            self.app.state.segmentos[index] = segmento
            del self.app._segmentos_reescritos[index]
            applied += 1

        if applied == 0:
            raise ValueError("nenhum segmento aplicado")

        remaining = len(self.app._segmentos_reescritos)
        if remaining:
            self.app.state.status_operacional = (
                f"{applied} segmento(s) aplicado(s); {remaining} pendente(s)."
            )
        else:
            self.app.state.status_operacional = f"{applied} segmento(s) atualizado(s)."

    def _export(self, payload: dict[str, Any]) -> None:
        destino_raw = str(payload.get("path") or "").strip()
        destino = Path(destino_raw).expanduser() if destino_raw else self.app._default_export_path("md")
        if destino.suffix.lower() != ".md":
            destino = destino.with_suffix(".md")
        conteudo = self.app._conteudo_final()
        if not conteudo.strip():
            raise ValueError("sem conteudo para exportar")
        slidemark_raw = self.app.state.conteudo_json.get("slidemark")
        metadados_raw = self.app.state.conteudo_json.get("metadados")
        alertas_raw = self.app.state.conteudo_json.get("alertas")
        parse_error_raw = self.app.state.conteudo_json.get("parse_error")
        arquivos = _exporter.exportar_conteudo(
            self.app.state.tema or "post",
            self.app.state.plataforma or "desconhecida",
            self.app.state.tipo_de_post,
            conteudo,
            slides=list(self.app.state.slides_gerados),
            slidemark=slidemark_raw if isinstance(slidemark_raw, dict) else None,
            metadados=metadados_raw if isinstance(metadados_raw, dict) else {},
            alertas=[str(item) for item in alertas_raw] if isinstance(alertas_raw, list) else [],
            segmentos=list(self.app.state.segmentos),
            avaliacao_post=dict(self.app.state.avaliacao_post),
            parse_error=str(parse_error_raw) if parse_error_raw else None,
            markdown_path=destino,
        )
        self.app.state.current_phase = PHASE_EXPORTACAO
        self.app._set_status(
            "Output exportado: " + ", ".join(str(path) for path in arquivos),
            "exportacao",
        )

    def _export_slidemark(self, payload: dict[str, Any]) -> None:
        if not is_trilha_visual(self.app.state.tipo_de_post):
            raise ValueError(
                "export SlideMark disponivel apenas para carrossel curto ou slide longo"
            )
        if not self.app._avaliacao_post_valida():
            raise ValueError("avaliacao valida e obrigatoria antes de exportar SlideMark")
        conteudo = self.app._conteudo_final()
        if not conteudo.strip():
            raise ValueError("sem conteudo para exportar")

        destino_raw = str(payload.get("path") or "").strip()
        destino = (
            Path(destino_raw).expanduser()
            if destino_raw
            else self.app._default_export_path("md")
        )
        if destino.suffix.lower() != ".md":
            destino = destino.with_suffix(".md")

        slidemark_original_raw = self.app.state.conteudo_json.get("slidemark")
        slidemark_original = (
            slidemark_original_raw if isinstance(slidemark_original_raw, dict) else None
        )
        briefing_raw = self.app.state.briefing_autoral
        briefing = briefing_raw if isinstance(briefing_raw, dict) else {}
        sugestoes_raw = self.app.state.conteudo_json.get("sugestoesImagem")
        sugestoes_imagem = sugestoes_raw if isinstance(sugestoes_raw, list) else None

        cfg = self.app._llm_config("slidemark_export")
        converter = _slidemark_converter.SlideMarkConverter(
            agent=self.app._agent_factory(),
            tool=cfg.provider,
            model=cfg.model,
            sandbox=cfg.sandbox or self.app.state.sandbox,
            opencode_agent=cfg.agent,
            reasoning_effort=cfg.reasoning_effort,
        )
        self.app.state.is_running = True
        self.app._set_status("Conversao SlideMark em andamento.", "exportacao")
        try:
            resultado = converter.converter(
                tema=self.app.state.tema or "post",
                plataforma=self.app.state.plataforma or "desconhecida",
                tipo_de_post=self.app.state.tipo_de_post,
                conteudo_final=conteudo,
                segmentos=list(self.app.state.segmentos),
                sugestoes_imagem=sugestoes_imagem,
                briefing_autoral=briefing,
                slidemark_original=slidemark_original,
            )
        finally:
            self.app.state.is_running = False

        conteudo_json = dict(self.app.state.conteudo_json)
        conteudo_json["slidemark"] = resultado.slidemark
        alertas_existentes = conteudo_json.get("alertas")
        alertas = (
            [str(item) for item in alertas_existentes]
            if isinstance(alertas_existentes, list)
            else []
        )
        alertas.extend(resultado.alertas)
        conteudo_json["alertas"] = alertas
        self.app.state.conteudo_json = conteudo_json

        metadados_raw = conteudo_json.get("metadados")
        metadados = metadados_raw if isinstance(metadados_raw, dict) else {}
        parse_error_raw = conteudo_json.get("parse_error")

        arquivos = _exporter.exportar_conteudo(
            self.app.state.tema or "post",
            self.app.state.plataforma or "desconhecida",
            self.app.state.tipo_de_post,
            conteudo,
            slides=list(self.app.state.slides_gerados),
            slidemark=resultado.slidemark,
            metadados=metadados,
            alertas=alertas,
            segmentos=list(self.app.state.segmentos),
            avaliacao_post=dict(self.app.state.avaliacao_post),
            parse_error=str(parse_error_raw) if parse_error_raw else None,
            markdown_path=destino,
        )
        self.app.state.current_phase = PHASE_EXPORTACAO
        status = "SlideMark exportado: " + ", ".join(str(path) for path in arquivos)
        if resultado.alertas:
            status += f" ({len(resultado.alertas)} alerta(s) de validacao)"
        self.app._set_status(status, "exportacao")

    def _navigate(self, payload: dict[str, Any]) -> None:
        stage = str(payload.get("stage", ""))
        if stage in STAGE_LABELS:
            target_phase = next(
                (phase for phase, mapped_stage in PROGRESS_PHASE_TO_STAGE.items() if mapped_stage == stage),
                None,
            )
            if target_phase is not None and target_phase not in released_phases(self.app.state):
                raise ValueError("Esta fase ainda aguarda liberacao da etapa anterior.")
            self._set_active_stage(stage)
            return
        phase = str(payload.get("phase", ""))
        if phase not in PHASE_LABELS:
            raise ValueError(f"fase ou etapa invalida: {phase or stage}")
        if phase not in released_phases(self.app.state):
            raise ValueError("Esta fase ainda aguarda liberacao da etapa anterior.")
        self._set_active_stage(PHASE_TO_STAGE.get(phase, "entry"))

    def _set_segment_index(self, payload: dict[str, Any]) -> None:
        index = _coerce_index(payload.get("index"), len(self.app.state.segmentos))
        self.app.state._segmento_index = index


def _coerce_index(value: object, total: int) -> int:
    try:
        index = int(value)
    except (TypeError, ValueError):
        index = 0
    if total <= 0:
        return 0
    return max(0, min(index, total - 1))


_CLIENT_GONE = (BrokenPipeError, ConnectionResetError, ConnectionAbortedError)


def _json_response(handler: BaseHTTPRequestHandler, payload: Any, status: int = 200) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    try:
        handler.send_response(status)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Content-Length", str(len(body)))
        handler.send_header("Cache-Control", "no-store")
        handler.end_headers()
        handler.wfile.write(body)
    except _CLIENT_GONE:
        # Browser closed/aborted the request before the response finished.
        return


def _read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0") or "0")
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("payload precisa ser um objeto JSON")
    return payload


def make_handler(controller: GuiController) -> type[BaseHTTPRequestHandler]:
    prompt_registry = PromptRegistryApi()

    class GuiRequestHandler(BaseHTTPRequestHandler):
        server_version = "PostEngineGUI/0.1"

        def log_message(self, format: str, *args: Any) -> None:
            return None

        def do_OPTIONS(self) -> None:
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "content-type")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, PUT, OPTIONS")
            self.end_headers()

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/api/session":
                _json_response(self, controller.snapshot())
                return
            if parsed.path == "/api/llm-config":
                _json_response(self, controller.llm_config_snapshot())
                return
            if parsed.path == "/api/prompt-registry":
                _json_response(self, prompt_registry.catalog())
                return
            if parsed.path == "/api/prompt-registry/diagnostics":
                _json_response(self, prompt_registry.diagnostics())
                return
            if parsed.path == "/api/prompt-registry/executions":
                query = parse_qs(parsed.query)
                limit = int(query.get("limit", ["100"])[0])
                _json_response(self, prompt_registry.executions(query.get("operation", [None])[0], limit))
                return
            if parsed.path.startswith("/api/prompt-registry/operations/"):
                payload = prompt_registry.operation(parsed.path.rsplit("/", 1)[-1])
                _json_response(self, payload or {"error": "operation_not_found"}, 200 if payload else 404)
                return
            if parsed.path.startswith("/api/prompt-registry/artifacts/"):
                payload = prompt_registry.artifact(parsed.path.rsplit("/", 1)[-1])
                _json_response(self, payload or {"error": "artifact_not_found"}, 200 if payload else 404)
                return
            if parsed.path == "/":
                dist_index = DIST_DIR / "index.html"
                if dist_index.exists():
                    self._serve_file(dist_index)
                    return
                self._serve_file(STATIC_DIR / "index.html")
                return
            if parsed.path.startswith("/assets/"):
                target = (DIST_DIR / parsed.path.removeprefix("/")).resolve()
                if DIST_DIR.resolve() in target.parents or target == DIST_DIR.resolve():
                    self._serve_file(target)
                    return
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            if parsed.path.startswith("/static/"):
                rel = parsed.path.removeprefix("/static/")
                target = (STATIC_DIR / rel).resolve()
                if STATIC_DIR.resolve() not in target.parents:
                    self.send_error(HTTPStatus.FORBIDDEN)
                    return
                self._serve_file(target)
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def do_PUT(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/api/llm-config":
                try:
                    _json_response(self, controller.update_llm_config(_read_json(self)))
                except _CLIENT_GONE:
                    return
                except Exception as exc:  # noqa: BLE001
                    _json_response(self, {"error": str(exc)}, 400)
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def do_PATCH(self) -> None:
            if urlparse(self.path).path != "/api/session":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            try:
                _json_response(self, controller.update(_read_json(self)))
            except _CLIENT_GONE:
                return
            except Exception as exc:  # noqa: BLE001
                _json_response(self, {"error": str(exc)}, 400)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            try:
                payload = _read_json(self)
                if parsed.path == "/api/action":
                    action_name = str(payload.get("action", ""))
                    _json_response(self, controller.action(action_name, payload))
                    return
                if parsed.path == "/api/restore":
                    restore_payload = payload.get("state", payload)
                    if not isinstance(restore_payload, dict):
                        raise ValueError("state precisa ser um objeto")
                    _json_response(self, controller.restore(restore_payload))
                    return
                if parsed.path == "/api/prompt-registry/preview":
                    operation = payload.get("operation")
                    context = payload.get("context", {})
                    overrides = payload.get("version_overrides")
                    if not isinstance(operation, str) or not isinstance(context, dict):
                        raise ValueError("operation e context sao obrigatorios")
                    if not isinstance(overrides, dict):
                        overrides = None
                    _json_response(self, prompt_registry.preview(
                        operation, context, provider=payload.get("provider"), model=payload.get("model"),
                        version_overrides={str(key): int(value) for key, value in overrides.items()} if overrides else None,
                    ))
                    return
                prefix = "/api/prompt-registry/artifacts/"
                if parsed.path.startswith(prefix):
                    tail = parsed.path[len(prefix):].split("/")
                    if len(tail) == 2 and tail[1] == "versions":
                        _json_response(self, prompt_registry.create_version(tail[0], payload), 201)
                        return
                    if len(tail) == 4 and tail[1] == "versions" and tail[3] == "activate":
                        _json_response(self, prompt_registry.activate_version(tail[0], int(tail[2]), payload))
                        return
                    if len(tail) == 4 and tail[1] == "versions" and tail[3] == "rollback":
                        _json_response(self, prompt_registry.rollback(tail[0], int(tail[2])))
                        return
                self.send_error(HTTPStatus.NOT_FOUND)
            except _CLIENT_GONE:
                return
            except PromptResolutionError as exc:
                _json_response(self, {"error": str(exc), "code": "resolution_failed"}, 422)
            except PromptRegistryError as exc:
                status = 409 if str(exc).startswith("Conflito:") else 422
                _json_response(self, {"error": str(exc)}, status)
            except KeyError as exc:
                _json_response(self, {"error": str(exc)}, 404)
            except Exception as exc:  # noqa: BLE001
                _json_response(self, {"error": str(exc)}, 400)

        def _serve_file(self, path: Path) -> None:
            if not path.exists() or not path.is_file():
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            body = path.read_bytes()
            try:
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except _CLIENT_GONE:
                return

    return GuiRequestHandler


def run_gui_server(
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    session_path: Path | None = None,
) -> None:
    controller = GuiController(session_path=session_path)
    handler = make_handler(controller)
    server = ThreadingHTTPServer((host, port), handler)
    url = f"http://{host}:{server.server_port}"
    print(f"GUI React disponivel em {url}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando GUI.", flush=True)
    finally:
        server.server_close()
