"""Single-session orchestration for the React GUI and the deprecated TUI.

The interview boundary is deliberately thin: this class persists and projects
the V4 state, while all interview decisions live in ``content_engine.interview``.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Input, Select, Static, TextArea

from . import exporter as _exporter
from . import generator as _generator
from . import persistence as _persistence
from . import post_evaluation as _post_evaluation
from . import segmentation as _segmentation
from . import session_log as _session_log
from .editorial_flow import normalize_editorial_flow
from .phase_progress import reconcile_phase_progress
from .interview.briefing import build_briefing
from .interview.controller import InterviewController
from .interview.schemas import InterviewState, criar_estado_inicial
from .interview.ui import build_interview_ui
from .llm_config import LlmOperationConfig, resolve
from .prompt_builder import PERSONAS_POR_TIPO, build_generation_prompt
from .schemas import (
    GenerationPromptInput,
    ScoreDoPost,
    SegmentoPost,
    TIPOS_DE_POST_VALIDOS,
    TuiSessionState,
    migrate_tipo_de_post,
)
from .trilhas import SELECT_OPCOES
from .tui_validation import validar_modelo, validar_sandbox


AgentFactory = Callable[[], Any]

PHASE_ENTRADA = "entrada_inicial"
PHASE_ENTREVISTA = "entrevista_gateway"
PHASE_BRIEFING = "briefing_autoral"
PHASE_PROMPT = "prompt_renderizado"
PHASE_EXECUCAO = "execucao_llm"
PHASE_SEGMENTACAO = "segmentacao_editavel"
PHASE_AVALIACAO = "avaliacao_conteudo"
PHASE_EXPORTACAO = "exportacao_final"
PHASES_VALIDAS = {
    PHASE_ENTRADA,
    PHASE_ENTREVISTA,
    PHASE_BRIEFING,
    PHASE_PROMPT,
    PHASE_EXECUCAO,
    PHASE_SEGMENTACAO,
    PHASE_AVALIACAO,
    PHASE_EXPORTACAO,
}

SCORE_AVALIACAO_ASPECTOS: tuple[str, ...] = (
    "tese",
    "progressao",
    "concretude",
    "precisao_tecnica",
    "retencao",
    "autoridade",
    "autoria",
    "slidemark",
    "revisao_textual",
    "total",
)


def _safe_query(app: App, selector: str) -> Any | None:
    try:
        return app.query_one(selector)
    except Exception:
        return None


def _text(widget: Any) -> str:
    if isinstance(widget, TextArea):
        return widget.text
    value = getattr(widget, "value", "")
    return value if isinstance(value, str) else ""


def _set_text(widget: Any, value: str) -> None:
    if widget is None:
        return
    if isinstance(widget, TextArea):
        widget.text = value
    elif isinstance(widget, Static):
        widget.update(value)
    else:
        try:
            widget.value = value
        except Exception:
            return


def _select_value(widget: Any) -> str:
    value = getattr(widget, "value", None)
    if value in (None, Select.NULL, Select.BLANK):
        return ""
    return str(value)


def _json(value: object) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return ""


class PostEngineApp(App):
    """Orchestrates one V4 session without compatibility interview paths."""

    DEFAULT_CSS = """
    Screen { layout: vertical; }
    #root { padding: 1; }
    Input, Select, TextArea { margin-bottom: 1; }
    #resposta_atual { height: 8; }
    """

    def __init__(
        self,
        agent_factory: AgentFactory | None = None,
        *,
        session_path: Path | None = None,
        run_sync_inline: bool = False,
        question_agent_factory: AgentFactory | None = None,
        restore_session: bool = False,
    ) -> None:
        super().__init__()
        self._session_path = session_path
        self._run_sync_inline = run_sync_inline
        self._restore_session_mode = restore_session
        self.state = _persistence.carregar_sessao(session_path)
        session_file = session_path if session_path is not None else _persistence.SESSION_FILE
        self._session_logger = _session_log.ensure_session_logger(self.state, session_file)
        self._agent_factory = agent_factory or self._build_default_agent
        self._question_agent_factory = question_agent_factory or self._agent_factory
        self._generator: _generator.ContentGenerator | None = None
        self._generator_config: tuple[Any, ...] | None = None
        self._segmento_reescrito = ""
        self._segmentos_reescritos: dict[int, str] = {}
        self._normalizar_estado_carregado()
        self._persistir()
        self._log_event("session", "app_initialized", {"session_path": str(session_file)})

    def _build_default_agent(self) -> Any:
        from .agent_wrapper import AgentWrapper
        from .llm_workspace import LlmExecutionWorkspace

        project_root = Path.cwd()
        ws = LlmExecutionWorkspace.create(
            "agent_default",
            project_root=project_root,
        )
        return AgentWrapper(
            workspace=ws.path,
            session_logger=self._session_logger,
            project_root=project_root,
            operation="agent_default",
            owns_workspace=True,
        )

    @property
    def session_path(self) -> Path | None:
        return self._session_path

    def compose(self) -> ComposeResult:
        """Keep a small TUI surface for local diagnosis; the React GUI is primary."""

        yield Vertical(
            Static("Post Engine V4", id="title"),
            Input(placeholder="Tema", id="tema"),
            Select(
                [(label, value) for label, value in SELECT_OPCOES],
                value=self.state.tipo_de_post,
                id="tipo_de_post",
            ),
            Input(placeholder="Plataforma", id="plataforma"),
            Input(placeholder="Objetivo", id="objetivo_do_post"),
            Input(placeholder="Personalidade", id="personalidade"),
            TextArea(id="resposta_atual"),
            Button("Iniciar entrevista", id="btn_iniciar_entrevista"),
            Button("Enviar resposta", id="btn_enviar_resposta"),
            Static(id="status_operacional"),
            Static(id="pergunta_atual"),
            id="root",
        )

    def on_mount(self) -> None:
        self._povoar_widgets_com_estado()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_iniciar_entrevista":
            self.action_continue_phase1()
        elif event.button.id == "btn_enviar_resposta":
            self.action_submit_round()

    def _phase(self) -> str:
        return self.state.current_phase if self.state.current_phase in PHASES_VALIDAS else PHASE_ENTRADA

    def _normalizar_estado_carregado(self) -> None:
        self.state.current_phase = self._phase()
        if not self.state.current_stage:
            self.state.current_stage = "entry"
        self.state.editorial_flow = normalize_editorial_flow(self.state.editorial_flow)
        interview = self._v4_state()
        if self.state.interview_state is not None and interview is None:
            self.state.interview_state = None
            self.state.evidence_ledger = []
            self.state.gateway_result = {}
            self.state.error = "Estado de entrevista V4 invalido; inicie uma nova entrevista."
        elif interview is not None:
            self._sync_v4_state(interview)
        reconcile_phase_progress(self.state, resume_at_latest=True)

    def _povoar_widgets_com_estado(self) -> None:
        values = {
            "#tema": self.state.tema,
            "#plataforma": self.state.plataforma,
            "#objetivo_do_post": self.state.objetivo_do_post,
            "#personalidade": self.state.personalidade,
            "#status_operacional": self.state.status_operacional,
        }
        for selector, value in values.items():
            _set_text(_safe_query(self, selector), value)
        tipo = _safe_query(self, "#tipo_de_post")
        if tipo is not None:
            try:
                tipo.value = self.state.tipo_de_post
            except Exception:
                pass
        interview = self._v4_state()
        question = interview.current_question.question if interview and interview.current_question else ""
        _set_text(_safe_query(self, "#pergunta_atual"), question)

    def _collect_form(self) -> None:
        tema = _safe_query(self, "#tema")
        plataforma = _safe_query(self, "#plataforma")
        objetivo = _safe_query(self, "#objetivo_do_post")
        personalidade = _safe_query(self, "#personalidade")
        tipo = _safe_query(self, "#tipo_de_post")
        if tema is not None:
            self.state.tema = _text(tema).strip()
        if plataforma is not None:
            self.state.plataforma = _text(plataforma).strip()
        if objetivo is not None:
            self.state.objetivo_do_post = _text(objetivo).strip()
        if personalidade is not None:
            self.state.personalidade = _text(personalidade).strip()
        if tipo is not None:
            self.state.tipo_de_post = migrate_tipo_de_post(_select_value(tipo))

    def _v4_state(self) -> InterviewState | None:
        raw = self.state.interview_state
        if not isinstance(raw, dict) or not raw:
            return None
        try:
            state = InterviewState.from_dict(raw)
        except (KeyError, TypeError, ValueError):
            return None
        if state.schema_version != "4.0":
            return None
        return state

    def _v4_controller(self, state: InterviewState) -> InterviewController:
        question_cfg = self._llm_config("interview_questions")
        evaluation_cfg = self._llm_config("interview_evaluate")
        validate_cfg = self._llm_config("interview_validate")
        title_cfg = self._llm_config("interview_round_title")
        gap_cfg = self._llm_config("interview_gap_diagnosis")
        return InterviewController(
            state,
            question_runner=self._question_agent_factory(),
            evaluation_runner=self._agent_factory(),
            title_runner=self._agent_factory(),
            gap_runner=self._agent_factory(),
            question_tool=question_cfg.provider,
            evaluation_tool=evaluation_cfg.provider,
            title_tool=title_cfg.provider,
            gap_tool=gap_cfg.provider,
            question_generation_model=question_cfg.model,
            evaluation_model=evaluation_cfg.model,
            title_model=title_cfg.model,
            gap_model=gap_cfg.model,
            question_reasoning_effort=question_cfg.reasoning_effort,
            evaluation_reasoning_effort=evaluation_cfg.reasoning_effort,
            title_reasoning_effort=title_cfg.reasoning_effort,
            gap_reasoning_effort=gap_cfg.reasoning_effort,
            question_sandbox=question_cfg.sandbox,
            evaluation_sandbox=evaluation_cfg.sandbox,
            title_sandbox=title_cfg.sandbox,
            gap_sandbox=gap_cfg.sandbox,
            validate_tool=validate_cfg.provider,
            validate_model=validate_cfg.model,
            validate_reasoning_effort=validate_cfg.reasoning_effort,
            validate_sandbox=validate_cfg.sandbox,
        )

    def _sync_v4_state(self, interview: InterviewState) -> None:
        self.state.interview_state = interview.to_dict()
        self.state.evidence_ledger = [item.to_dict() for item in interview.evidence_ledger]
        self.state.gateway_result = (
            interview.gateway_result.to_dict() if interview.gateway_result else {}
        )

    def _interview_snapshot(self, interview: InterviewState) -> dict[str, Any]:
        return interview.to_dict()

    def _validate_entry(self) -> None:
        errors: list[str] = []
        if not self.state.tema.strip():
            errors.append("tema nao pode ser vazio")
        if not self.state.plataforma.strip():
            errors.append("plataforma nao pode ser vazia")
        if not self.state.objetivo_do_post.strip():
            errors.append("objetivo nao pode ser vazio")
        if self.state.tipo_de_post not in TIPOS_DE_POST_VALIDOS:
            errors.append("tipo_de_post invalido")
        if errors:
            raise ValueError("; ".join(errors))

    def action_start_interview_v4(self) -> dict[str, Any]:
        self._collect_form()
        self._validate_entry()
        interview = criar_estado_inicial(
            self.state.tema,
            objetivo=self.state.objetivo_do_post,
            formato=self.state.tipo_de_post,
            personalidade=self.state.personalidade,
            restricoes=self.state.restricoes_de_geracao,
        )
        # Persist the V4 shell before the LLM call so a generation failure
        # still leaves an active interview that can be retried.
        self._sync_v4_state(interview)
        self.state.briefing_autoral = {}
        self.state.current_phase = PHASE_ENTREVISTA
        self.state.current_stage = "interview"
        self.state.fase_atual = "entrevista"

        controller = self._v4_controller(interview)
        question = None
        generation_error: str | None = None
        try:
            question = controller.start()
        except Exception as exc:  # noqa: BLE001 — surface to UI, keep interview alive
            generation_error = str(exc)

        self._sync_v4_state(interview)
        if generation_error:
            self.state.error = generation_error
            self.state.status_operacional = f"Falha ao gerar a primeira pergunta: {generation_error}"
        else:
            self.state.error = None
            if question is None:
                self.state.status_operacional = (
                    "Nenhuma candidata utilizavel foi gerada. Ajuste o tema e tente novamente."
                )
            else:
                self.state.status_operacional = "Entrevista iniciada; responda a pergunta atual."
        self._log_event(
            "interview",
            "interview.start",
            {
                "question_available": question is not None,
                "error": generation_error,
            },
        )
        self._persistir()
        self._povoar_widgets_com_estado()
        return self._interview_snapshot(interview)

    def action_continue_phase1(self) -> dict[str, Any]:
        return self.action_start_interview_v4()

    def _response_from_widget(self) -> str:
        return _text(_safe_query(self, "#resposta_atual")).strip()

    def action_submit_v4_answer(
        self,
        response: str | None = None,
        *,
        user_requested_end: bool = False,
    ) -> dict[str, Any]:
        interview = self._v4_state()
        if interview is None:
            raise ValueError("Nenhuma entrevista V4 ativa.")
        answer = str(response if response is not None else self._response_from_widget()).strip()
        controller = self._v4_controller(interview)
        decision = controller.run_round(answer, user_requested_end=user_requested_end)
        if decision.should_ask:
            controller.generate_next_question()
        elif not (interview.gateway_result and interview.gateway_result.approved):
            controller.diagnose_gaps(force=True)
        self._sync_v4_state(interview)
        self.state.current_phase = PHASE_ENTREVISTA
        self.state.current_stage = "interview"
        self.state.fase_atual = "entrevista"
        self.state.error = None
        if interview.gateway_result and interview.gateway_result.approved:
            self.state.status_operacional = "Material suficiente. Voce pode montar o briefing."
        elif interview.current_question is not None:
            self.state.status_operacional = controller.explain_decision()
        elif interview.pending_batch:
            self.state.status_operacional = "Lote de extensao pronto; responda as perguntas."
        else:
            self.state.status_operacional = "Entrevista encerrada sem material suficiente."
        self._log_event(
            "interview",
            "interview.submit_answer",
            {
                "answer_count": len(interview.answers),
                "should_ask": decision.should_ask,
                "approved": bool(interview.gateway_result and interview.gateway_result.approved),
            },
        )
        self._persistir()
        self._povoar_widgets_com_estado()
        return self._interview_snapshot(interview)

    def action_diagnose_interview_gaps(self, *, force: bool = False) -> dict[str, Any]:
        interview = self._v4_state()
        if interview is None:
            raise ValueError("Nenhuma entrevista V4 ativa.")
        controller = self._v4_controller(interview)
        diagnosis = controller.diagnose_gaps(force=force)
        self._sync_v4_state(interview)
        self.state.status_operacional = "Diagnostico de lacunas atualizado."
        self._log_event(
            "interview",
            "interview.diagnose_gaps",
            {"force": force, "length": len(diagnosis)},
        )
        self._persistir()
        self._povoar_widgets_com_estado()
        return self._interview_snapshot(interview)

    def action_start_extension_batch(self, count: int = 5) -> dict[str, Any]:
        interview = self._v4_state()
        if interview is None:
            raise ValueError("Nenhuma entrevista V4 ativa.")
        controller = self._v4_controller(interview)
        batch = controller.start_extension_batch(count=int(count or 5))
        self._sync_v4_state(interview)
        self.state.current_phase = PHASE_ENTREVISTA
        self.state.current_stage = "interview"
        self.state.fase_atual = "entrevista"
        self.state.error = None
        self.state.status_operacional = f"Lote de {len(batch)} perguntas gerado a partir das lacunas."
        self._log_event(
            "interview",
            "interview.start_extension_batch",
            {"count": len(batch), "max_questions": interview.max_questions},
        )
        self._persistir()
        self._povoar_widgets_com_estado()
        return self._interview_snapshot(interview)

    def action_submit_extension_batch(
        self,
        responses: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        interview = self._v4_state()
        if interview is None:
            raise ValueError("Nenhuma entrevista V4 ativa.")
        payload = list(responses or [])
        controller = self._v4_controller(interview)
        decision = controller.submit_extension_batch(payload)
        self._sync_v4_state(interview)
        self.state.current_phase = PHASE_ENTREVISTA
        self.state.current_stage = "interview"
        self.state.fase_atual = "entrevista"
        self.state.error = None
        if interview.gateway_result and interview.gateway_result.approved:
            self.state.status_operacional = "Material suficiente apos lote de extensao."
        else:
            self.state.status_operacional = "Lote reavaliado; ainda sem material suficiente."
        self._log_event(
            "interview",
            "interview.submit_extension_batch",
            {
                "response_count": len(payload),
                "batches_completed": interview.extension_batches_completed,
                "approved": bool(interview.gateway_result and interview.gateway_result.approved),
                "should_ask": decision.should_ask,
            },
        )
        self._persistir()
        self._povoar_widgets_com_estado()
        return self._interview_snapshot(interview)

    def action_submit_round(self, response: str | None = None) -> dict[str, Any]:
        return self.action_submit_v4_answer(response)

    def action_register_answer(self) -> dict[str, Any]:
        return self.action_submit_v4_answer()

    def action_generate_other_question(self) -> dict[str, Any]:
        interview = self._v4_state()
        if interview is None:
            # Empty UI retry after a failed start: bootstrap a V4 interview.
            return self.action_start_interview_v4()
        if interview.current_question is not None:
            return self._interview_snapshot(interview)
        question = self._v4_controller(interview).generate_next_question()
        self._sync_v4_state(interview)
        self.state.error = None
        self.state.status_operacional = (
            "Nova pergunta pronta." if question else "Nenhuma candidata utilizavel foi gerada."
        )
        self._persistir()
        self._povoar_widgets_com_estado()
        return self._interview_snapshot(interview)

    def action_close_interview_v4(self) -> dict[str, Any]:
        interview = self._v4_state()
        if interview is None:
            raise ValueError("Nenhuma entrevista V4 ativa.")
        self._v4_controller(interview).close()
        self._sync_v4_state(interview)
        self.state.briefing_autoral = build_briefing(interview)
        self.state.current_phase = PHASE_BRIEFING
        self.state.current_stage = "briefing"
        self.state.fase_atual = "briefing"
        self.state.status_operacional = "Entrevista encerrada e briefing V4 montado."
        self._persistir()
        return self._interview_snapshot(interview)

    def action_update_gateway(self) -> dict[str, Any]:
        interview = self._v4_state()
        if interview is None or interview.gateway_result is None:
            raise ValueError("O gateway V4 e calculado ao enviar uma resposta.")
        self._sync_v4_state(interview)
        self._persistir()
        return interview.gateway_result.to_dict()

    def _garantir_briefing_para_fase3(self) -> None:
        interview = self._v4_state()
        if interview is None:
            raise ValueError("Entrevista V4 ausente.")
        if interview.gateway_result is None or not interview.gateway_result.approved:
            raise ValueError("O gateway V4 ainda nao aprovou material para geracao.")
        self.state.briefing_autoral = build_briefing(interview)

    def action_continue_phase2(self) -> None:
        self._garantir_briefing_para_fase3()
        self.state.current_phase = PHASE_BRIEFING
        self.state.current_stage = "briefing"
        self.state.fase_atual = "briefing"
        self.state.status_operacional = "Briefing V4 pronto para geracao."
        self._persistir()

    def action_clear_phase1(self) -> None:
        self.state.tema = ""
        self.state.plataforma = ""
        self.state.objetivo_do_post = ""
        self.state.personalidade = ""
        self.state.status_operacional = "Campos de entrada limpos."
        self._persistir()
        self._povoar_widgets_com_estado()

    def _clear_interview(self) -> None:
        self.state.interview_state = None
        self.state.evidence_ledger = []
        self.state.gateway_result = {}
        self.state.briefing_autoral = {}
        self.state.restricoes_de_geracao = []

    def action_reset_context(self) -> None:
        self.state = TuiSessionState()
        session_file = self._session_path if self._session_path is not None else _persistence.SESSION_FILE
        self._session_logger = _session_log.ensure_session_logger(self.state, session_file)
        self._generator = None
        self._generator_config = None
        self._segmento_reescrito = ""
        self._segmentos_reescritos = {}
        self.state.status_operacional = "Contexto reiniciado."
        self._persistir()

    def action_reset_phase(self) -> None:
        self._clear_interview()
        self.state.current_phase = PHASE_ENTRADA
        self.state.current_stage = "entry"
        self.state.fase_atual = "entrada"
        self.state.status_operacional = "Entrevista reiniciada."
        self._persistir()

    def action_back_to_phase1(self) -> None:
        self.state.current_stage = "entry"
        self.state.fase_atual = "entrada"
        self._persistir()

    def action_back_to_phase2(self) -> None:
        self.state.current_stage = "interview"
        self.state.fase_atual = "entrevista"
        self._persistir()

    def action_continue_phase3(self) -> None:
        self._garantir_prompt_para_fase4()
        self.state.current_phase = PHASE_PROMPT
        self.state.current_stage = "prompt"
        self._persistir()

    def _llm_config(self, operation: str) -> LlmOperationConfig:
        return resolve(operation)

    @staticmethod
    def _config_cache_key(config: LlmOperationConfig) -> tuple[Any, ...]:
        return (
            config.provider,
            config.model,
            config.agent,
            config.reasoning_effort,
            config.sandbox,
        )

    def _gateway_payload(self) -> dict[str, Any]:
        return dict(self.state.gateway_result) if self.state.gateway_result else {}

    def _montar_generation_input(self) -> GenerationPromptInput:
        return GenerationPromptInput(
            tema=self.state.tema,
            plataforma=self.state.plataforma,
            objetivo_do_post=self.state.objetivo_do_post,
            tipo_de_post=self.state.tipo_de_post,
            briefing_autoral=dict(self.state.briefing_autoral),
            interview_context=(
                dict(self.state.interview_state)
                if isinstance(self.state.interview_state, dict)
                else None
            ),
            gateway_result=self._gateway_payload() or None,
            restricoes_de_geracao=list(self.state.restricoes_de_geracao) or None,
            personalidade=self.state.personalidade or None,
        )

    def _garantir_prompt_para_fase4(self) -> None:
        if not self.state.briefing_autoral:
            self._garantir_briefing_para_fase3()
        erro_modelo = validar_modelo(self._llm_config("post_generate").model)
        if erro_modelo:
            raise ValueError(erro_modelo)
        config = self._llm_config("post_generate")
        erro_sandbox = validar_sandbox(
            config.sandbox or self.state.sandbox,
            config.provider,
        )
        if erro_sandbox:
            raise ValueError(erro_sandbox)
        self.state.prompt_renderizado = build_generation_prompt(self._montar_generation_input())
        self.state.current_phase = PHASE_PROMPT
        self.state.current_stage = "prompt"
        self.state.fase_atual = "prompt"
        self.state.status_operacional = "Prompt renderizado; pronto para rodar."

    def action_preview(self) -> None:
        self._garantir_prompt_para_fase4()
        self._persistir()

    def get_generator(self) -> _generator.ContentGenerator:
        config = self._llm_config("post_generate")
        key = self._config_cache_key(config)
        if self._generator is None or self._generator_config != key:
            self._generator = _generator.ContentGenerator(
                agent=self._agent_factory(),
                tool=config.provider,
                model=config.model,
                reasoning_effort=config.reasoning_effort,
                sandbox=config.sandbox or self.state.sandbox,
                opencode_agent=config.agent,
            )
            self._generator_config = key
        return self._generator

    def action_run(self) -> None:
        if not self.state.prompt_renderizado.strip():
            self._garantir_prompt_para_fase4()
        self.state.is_running = True
        self.state.current_phase = PHASE_EXECUCAO
        self.state.current_stage = "execution"
        self.state.fase_atual = "execucao"
        self.state.status_operacional = "Execucao LLM em andamento."
        try:
            self._executar_agente()
        finally:
            self.state.is_running = False
            self._persistir()

    def _executar_agente(self) -> None:
        generator = self.get_generator()
        data = self._montar_generation_input()
        self._log_event(
            "llm_request",
            "post.generate",
            {"input": asdict(data), "tool": generator.tool, "model": generator.model},
        )
        result = generator.generate(data)
        agent_result = result.agent_result
        self.state.stdout = agent_result.stdout
        self.state.stderr = agent_result.stderr
        self.state.returncode = agent_result.returncode
        self.state.events = list(agent_result.events or [])
        self.state.error = agent_result.error
        self.state.conteudo_gerado = result.conteudo
        self.state.slides_gerados = [
            {
                "numero": slide.numero,
                "titulo": slide.titulo,
                "bullets": list(slide.bullets),
                "notas_visuais": slide.notas_visuais,
                "sugestao_imagem": asdict(slide.sugestao_imagem)
                if slide.sugestao_imagem
                else None,
            }
            for slide in result.slides
        ]
        if result.parse_error:
            self.state.conteudo_json = {
                "parse_error": result.parse_error,
                "raw": agent_result.stdout,
            }
            self.state.status_operacional = "LLM finalizado com erro de parse JSON."
        else:
            payload: dict[str, Any] = {
                "conteudo": result.conteudo,
                "metadados": dict(result.metadados),
                "alertas": list(result.alertas),
                "slides": list(self.state.slides_gerados),
            }
            if result.sugestoes_imagem:
                payload["sugestoesImagem"] = list(result.sugestoes_imagem)
            if result.slidemark is not None:
                payload["slidemark"] = result.slidemark
            self.state.conteudo_json = payload
            self.state.status_operacional = (
                "LLM finalizado com sucesso." if agent_result.ok else "LLM finalizado com falha."
            )
        self._log_event(
            "llm_response",
            "post.generate",
            {"returncode": agent_result.returncode, "error": agent_result.error},
        )

    def action_clear(self) -> None:
        self.state.stdout = ""
        self.state.stderr = ""
        self.state.events = []
        self.state.error = None
        self.state.returncode = None
        self.state.conteudo_gerado = ""
        self.state.conteudo_json = {}
        self.state.segmentos = []
        self.state.avaliacao_post = {}
        self.state.status_operacional = "Saidas limpas; briefing e prompt preservados."
        self._persistir()

    def _segmentar(self, conteudo: str) -> list[dict[str, Any]]:
        slidemark = self.state.conteudo_json.get("slidemark")
        if isinstance(slidemark, dict):
            suggestions = self.state.conteudo_json.get("sugestoesImagem")
            segments = _segmentation.segmentar_slidemark(
                slidemark,
                sugestoes_imagem=suggestions if isinstance(suggestions, list) else None,
            )
            if segments:
                return segments
        config = self._llm_config("segment")
        segmenter = _segmentation.Segmenter(
            agent=self._agent_factory(),
            tool=config.provider,
            model=config.model,
            sandbox=config.sandbox or self.state.sandbox,
            opencode_agent=config.agent,
            reasoning_effort=config.reasoning_effort,
        )
        return [
            {
                "id": item.id,
                "ordem": item.ordem,
                "texto": item.texto,
                "papel_interno": item.papel_interno,
            }
            for item in segmenter.segmentar(
                conteudo,
                tipo_de_post=self.state.tipo_de_post,
                briefing=dict(self.state.briefing_autoral),
                interview_context=(
                    dict(self.state.interview_state)
                    if isinstance(self.state.interview_state, dict)
                    else None
                ),
            )
        ]

    def action_segment(self) -> None:
        if not self.state.conteudo_gerado.strip():
            raise ValueError("Sem conteudo para segmentar.")
        self.state.segmentos = self._segmentar(self.state.conteudo_gerado)
        self.state.current_phase = PHASE_SEGMENTACAO
        self.state.current_stage = "segmentation"
        self.state.fase_atual = "segmentacao"
        self.state.status_operacional = f"{len(self.state.segmentos)} segmentos disponiveis."
        self._persistir()

    def _conteudo_final(self) -> str:
        if self.state.segmentos:
            return "\n\n".join(
                str(item.get("texto", "")).strip()
                for item in self.state.segmentos
                if isinstance(item, dict) and str(item.get("texto", "")).strip()
            )
        return self.state.conteudo_gerado

    def action_evaluate(self) -> None:
        content = self._conteudo_final()
        if not content.strip():
            raise ValueError("Sem conteudo para avaliar.")
        config = self._llm_config("post_evaluate")
        evaluator = _post_evaluation.PostEvaluator(
            agent=self._agent_factory(),
            tool=config.provider,
            model=config.model,
            sandbox=config.sandbox or self.state.sandbox,
            opencode_agent=config.agent,
            reasoning_effort=config.reasoning_effort,
        )
        evaluation = evaluator.avaliar(
            self.state.tema,
            content,
            dict(self.state.briefing_autoral),
            tipo_de_post=self.state.tipo_de_post,
            interview_context=(
                dict(self.state.interview_state)
                if isinstance(self.state.interview_state, dict)
                else None
            ),
        )
        self.state.avaliacao_post = evaluation.to_dict()
        self.state.current_phase = PHASE_AVALIACAO
        self.state.current_stage = "evaluation"
        self.state.fase_atual = "avaliacao"
        self.state.status_operacional = "Avaliacao concluida."
        self._persistir()

    def _segmento_atual_dict(self, index: int | None = None) -> dict[str, Any] | None:
        if not self.state.segmentos:
            return None
        target = self.state._segmento_index if index is None else index
        target = 0 if target is None else max(0, min(target, len(self.state.segmentos) - 1))
        item = self.state.segmentos[target]
        return dict(item) if isinstance(item, dict) else None

    def _segmento_atual_texto(self) -> str:
        item = self._segmento_atual_dict()
        return str(item.get("texto", "")) if item else ""

    def _segmento_post_from_dict(self, item: dict[str, Any]) -> SegmentoPost:
        order = item.get("ordem", (self.state._segmento_index or 0) + 1)
        return SegmentoPost(
            id=str(item.get("id", f"seg-{order}")),
            ordem=int(order) if isinstance(order, int) and not isinstance(order, bool) else 1,
            texto=str(item.get("texto", "")),
            papel_interno=str(item.get("papel_interno", item.get("papelInterno", "segmento"))),
        )

    def action_rewrite_segment(self) -> None:
        raise RuntimeError("Use the GUI action rewrite_segment with an explicit request.")

    def action_apply_segment_adjustment(self) -> None:
        if not self._segmento_reescrito:
            raise ValueError("Nenhuma reescrita pendente.")
        index = self.state._segmento_index or 0
        if index >= len(self.state.segmentos):
            raise ValueError("Segmento indisponivel.")
        updated = dict(self.state.segmentos[index])
        updated["texto"] = self._segmento_reescrito
        self.state.segmentos[index] = updated
        self._segmento_reescrito = ""
        self._persistir()

    def action_export_output(self) -> None:
        content = self._conteudo_final()
        if not content.strip():
            raise ValueError("Sem conteudo para exportar.")
        target = self._default_export_path("md")
        _exporter.exportar_conteudo(
            self.state.tema or "post",
            self.state.plataforma or "desconhecida",
            self.state.tipo_de_post,
            content,
            slides=list(self.state.slides_gerados),
            slidemark=(
                self.state.conteudo_json.get("slidemark")
                if isinstance(self.state.conteudo_json.get("slidemark"), dict)
                else None
            ),
            metadados=(
                self.state.conteudo_json.get("metadados")
                if isinstance(self.state.conteudo_json.get("metadados"), dict)
                else {}
            ),
            alertas=(
                self.state.conteudo_json.get("alertas")
                if isinstance(self.state.conteudo_json.get("alertas"), list)
                else []
            ),
            segmentos=list(self.state.segmentos),
            avaliacao_post=dict(self.state.avaliacao_post),
            markdown_path=target,
        )
        self.state.current_phase = PHASE_EXPORTACAO
        self.state.current_stage = "export"
        self.state.fase_atual = "exportacao"
        self.state.status_operacional = f"Output exportado: {target}"
        self._persistir()

    def _default_export_path(self, extension: str) -> Path:
        base = _exporter.nome_arquivo_base(
            self.state.tema or "post",
            self.state.plataforma or "desconhecida",
            self.state.tipo_de_post,
        )
        return _exporter.EXPORTS_DIR / f"{base}.{extension}"

    def _avaliacao_post_valida(self) -> bool:
        score = self.state.avaliacao_post.get("score") if self.state.avaliacao_post else None
        return isinstance(score, dict) and bool(score) and not self.state.avaliacao_post.get("parse_error")

    def _post_score_payload(self) -> dict[str, Any]:
        raw = self.state.avaliacao_post.get("score") if self.state.avaliacao_post else None
        return dict(raw) if isinstance(raw, dict) else {}

    def _render_post_score(self, aspecto: str) -> str:
        labels = {
            "tese": "Tese",
            "progressao": "Progressao",
            "concretude": "Concretude",
            "precisao_tecnica": "Precisao tecnica",
            "retencao": "Retencao",
            "autoridade": "Autoridade",
            "autoria": "Autoria",
            "slidemark": "SlideMark",
            "revisao_textual": "Revisao textual",
            "total": "Total",
        }
        score = self._post_score_payload()
        value = score.get(aspecto)
        if value is None and aspecto == "total" and score:
            try:
                value = ScoreDoPost(
                    tese=int(score.get("tese", 0)),
                    progressao=int(score.get("progressao", 0)),
                    concretude=int(score.get("concretude", 0)),
                    precisao_tecnica=int(score.get("precisao_tecnica", score.get("precisaoTecnica", 0))),
                    retencao=int(score.get("retencao", 0)),
                    autoridade=int(score.get("autoridade", 0)),
                    autoria=int(score.get("autoria", 0)),
                    slidemark=int(score.get("slidemark", 0)),
                    revisao_textual=int(score.get("revisao_textual", score.get("revisaoTextual", 0))),
                ).total
            except (TypeError, ValueError):
                value = 0
        if value is None:
            value = score.get("precisaoTecnica", 0) if aspecto == "precisao_tecnica" else 0
        return f"{labels.get(aspecto, aspecto)}: {value}"

    def _render_avaliacao_texto(self, key: str) -> str:
        value = self.state.avaliacao_post.get(key) if self.state.avaliacao_post else ""
        return value if isinstance(value, str) else ""

    def _render_avaliacao_lista(self, key: str) -> str:
        raw = self.state.avaliacao_post.get(key) if self.state.avaliacao_post else []
        if raw is None and key == "sugestoes":
            raw = self.state.avaliacao_post.get("sugestoes_melhoria", [])
        return "\n".join(f"- {item}" for item in raw if isinstance(item, str)) if isinstance(raw, list) else ""

    def _render_jornada(self) -> str:
        labels = {
            PHASE_ENTRADA: "Entrada",
            PHASE_ENTREVISTA: "Entrevista",
            PHASE_BRIEFING: "Briefing",
            PHASE_PROMPT: "Prompt",
            PHASE_EXECUCAO: "Execucao",
            PHASE_SEGMENTACAO: "Segmentacao",
            PHASE_AVALIACAO: "Avaliacao",
            PHASE_EXPORTACAO: "Exportacao",
        }
        return f"Fase atual: {labels.get(self._phase(), 'Entrada')}"

    def _render_persona_ativa(self) -> str:
        return PERSONAS_POR_TIPO.get(self.state.tipo_de_post, self.state.tipo_de_post)

    def _render_score_summary(self) -> str:
        gateway = self._gateway_payload()
        return f"Qualidade V4: {gateway.get('global_score', 0)}"

    def _render_gateway_status(self) -> str:
        gateway = self._gateway_payload()
        if not gateway:
            return "Gateway V4 aguardando respostas."
        return str(gateway.get("justification", gateway.get("gateway_type", "REPROVADO")))

    def _render_gateway_status_curto(self) -> str:
        return str(self._gateway_payload().get("gateway_type", "REPROVADO"))

    def _render_total_bruto(self) -> str:
        return self._render_score_summary()

    def _render_total_normalizado(self) -> str:
        return self._render_score_summary()

    def _render_score_aspecto(self, aspecto: str) -> str:
        return f"{aspecto}: indisponivel no contrato V4"

    def _render_returncode(self) -> str:
        return "-" if self.state.returncode is None else str(self.state.returncode)

    def _build_interview_ui(self) -> dict[str, Any]:
        return build_interview_ui(self.state.interview_state)

    def _serialize_briefing(self) -> str:
        return _json(self.state.briefing_autoral) if self.state.briefing_autoral else ""

    def _serialize_events(self) -> str:
        return _json(self.state.events) if self.state.events else ""

    def _serialize_conteudo_json(self) -> str:
        return _json(self.state.conteudo_json) if self.state.conteudo_json else ""

    def _serialize_segmentos(self) -> str:
        return _json(self.state.segmentos) if self.state.segmentos else ""

    def _serialize_historico_entrevista(self) -> str:
        interview = self._v4_state()
        return _json([item.to_dict() for item in interview.answers]) if interview else ""

    def _serialize_historico_recente(self) -> str:
        interview = self._v4_state()
        return _json([item.to_dict() for item in interview.answers[-3:]]) if interview else ""

    def _serialize_avaliacao_post(self) -> str:
        return _json(self.state.avaliacao_post) if self.state.avaliacao_post else ""

    def _set_status(self, message: str, phase: str | None = None) -> None:
        self.state.status_operacional = message
        if phase is not None:
            self.state.fase_atual = phase
        _set_text(_safe_query(self, "#status_operacional"), message)

    def _log_event(
        self,
        event_type: str,
        operation: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self._session_logger.safe_write(event_type, operation, payload or {})

    def _persistir(self) -> None:
        try:
            reconcile_phase_progress(self.state)
            _persistence.salvar_sessao(self.state, self._session_path)
        except OSError:
            return

    def _ativar_sessao_restaurada(self, restored_state: TuiSessionState) -> None:
        self.state = restored_state
        self._normalizar_estado_carregado()
        session_file = self._session_path if self._session_path is not None else _persistence.SESSION_FILE
        self._session_logger = _session_log.ensure_session_logger(self.state, session_file)
        self._generator = None
        self._generator_config = None
        self._persistir()

    def action_generate_storyboard(self) -> None:
        from . import editorial_actions

        editorial_actions.action_generate_storyboard(self, self._agent_factory)

    def action_update_storyboard(self, blocks: list[dict[str, Any]]) -> None:
        from . import editorial_actions

        editorial_actions.action_update_storyboard(self, blocks)

    def action_clear_storyboard(self) -> None:
        from . import editorial_actions

        editorial_actions.action_clear_storyboard(self)

    def action_generate_block_drafts(self, block_id: str) -> None:
        from . import editorial_actions

        editorial_actions.action_generate_block_drafts(self, self._agent_factory, block_id=block_id)

    def action_generate_all_block_drafts(self) -> None:
        from . import editorial_actions

        editorial_actions.action_generate_all_block_drafts(self, self._agent_factory)

    def action_retry_block_draft(self, block_id: str, option_id: str) -> None:
        from . import editorial_actions

        editorial_actions.action_retry_block_draft(
            self,
            self._agent_factory,
            block_id=block_id,
            option_id=option_id,
        )

    def action_select_block_draft(self, block_id: str, option_id: str) -> None:
        from . import editorial_actions

        editorial_actions.action_select_block_draft(self, block_id=block_id, option_id=option_id)

    def action_compose_editorial(self) -> None:
        from . import editorial_actions

        editorial_actions.action_compose_editorial(
            self,
            self._agent_factory,
            phase_segmentacao=PHASE_SEGMENTACAO,
        )


__all__ = [
    "PHASE_AVALIACAO",
    "PHASE_BRIEFING",
    "PHASE_ENTRADA",
    "PHASE_ENTREVISTA",
    "PHASE_EXECUCAO",
    "PHASE_EXPORTACAO",
    "PHASE_PROMPT",
    "PHASE_SEGMENTACAO",
    "PostEngineApp",
    "SCORE_AVALIACAO_ASPECTOS",
]
