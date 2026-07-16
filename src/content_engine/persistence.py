"""Persistence for the single V4 session contract.

Session files are intentionally not migrated. A file whose schema is not
exactly 4.0 is discarded when opened from disk and rejected when supplied to
the restore API.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .editorial_flow import normalize_editorial_flow
from .phase_progress import PHASE_ORDER
from .schemas import (
    FERRAMENTAS_VALIDAS,
    SANDBOXES_VALIDOS,
    SESSION_SCHEMA_VERSION,
    TuiSessionState,
    migrate_tipo_de_post,
)


DATA_DIR: Path = Path(__file__).resolve().parents[2] / ".data" / "sessions"
SESSION_FILE: Path = DATA_DIR / "current-session.json"

_VALID_PHASES = {
    "entrada_inicial",
    "entrevista_gateway",
    "briefing_autoral",
    "prompt_renderizado",
    "execucao_llm",
    "segmentacao_editavel",
    "avaliacao_conteudo",
    "exportacao_final",
}
_VALID_STAGES = {
    "agents",
    "entry",
    "interview",
    "briefing",
    "storyboard",
    "drafts",
    "composition",
    "prompt",
    "execution",
    "segmentation",
    "evaluation",
    "export",
}


def _ensure_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _as_str(value: object, default: str = "") -> str:
    return value if isinstance(value, str) else default


def _as_dict(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _as_list(value: object) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _as_bool(value: object, default: bool = False) -> bool:
    return value if isinstance(value, bool) else default


def _as_int_or_none(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _state_to_dict(state: TuiSessionState) -> dict[str, Any]:
    return {
        "schema_version": SESSION_SCHEMA_VERSION,
        "session_id": state.session_id,
        "session_log_path": state.session_log_path,
        "current_phase": state.current_phase,
        "current_stage": state.current_stage,
        "fases_liberadas": list(state.fases_liberadas),
        "tema": state.tema,
        "plataforma": state.plataforma,
        "objetivo_do_post": state.objetivo_do_post,
        "personalidade": state.personalidade,
        "tipo_de_post": state.tipo_de_post,
        "slides_gerados": list(state.slides_gerados),
        "tool": state.tool,
        "model": state.model,
        "sandbox": state.sandbox,
        "briefing_autoral": dict(state.briefing_autoral),
        "restricoes_de_geracao": list(state.restricoes_de_geracao),
        "interview_state": (
            dict(state.interview_state) if isinstance(state.interview_state, dict) else None
        ),
        "evidence_ledger": list(state.evidence_ledger),
        "gateway_result": dict(state.gateway_result),
        "fase_atual": state.fase_atual,
        "status_operacional": state.status_operacional,
        "prompt_renderizado": state.prompt_renderizado,
        "stdout": state.stdout,
        "stderr": state.stderr,
        "returncode": state.returncode,
        "events": list(state.events),
        "error": state.error,
        "conteudo_gerado": state.conteudo_gerado,
        "conteudo_json": dict(state.conteudo_json),
        "segmentos": list(state.segmentos),
        "avaliacao_post": dict(state.avaliacao_post),
        "is_running": state.is_running,
        "_segmento_index": state._segmento_index,
        "editorial_flow": dict(state.editorial_flow),
    }


def _validate_schema(payload: dict[str, Any]) -> None:
    schema = payload.get("schema_version")
    if schema != SESSION_SCHEMA_VERSION:
        raise ValueError(
            f"schema_version invalido: esperado {SESSION_SCHEMA_VERSION!r}, recebido {schema!r}"
        )
    interview = payload.get("interview_state")
    if interview is not None:
        if not isinstance(interview, dict):
            raise ValueError("interview_state precisa ser um objeto")
        nested_schema = interview.get("schema_version")
        if nested_schema != SESSION_SCHEMA_VERSION:
            raise ValueError(
                "interview_state.schema_version precisa ser "
                f"{SESSION_SCHEMA_VERSION!r}"
            )


def _dict_to_state(payload: dict[str, Any]) -> TuiSessionState:
    _validate_schema(payload)
    phase = _as_str(payload.get("current_phase"), "entrada_inicial")
    stage = _as_str(payload.get("current_stage"), "entry")
    tool = payload.get("tool")
    sandbox = payload.get("sandbox")

    return TuiSessionState(
        session_id=_as_str(payload.get("session_id")),
        session_log_path=_as_str(payload.get("session_log_path")),
        current_phase=phase if phase in _VALID_PHASES else "entrada_inicial",
        current_stage=stage if stage in _VALID_STAGES else "entry",
        fases_liberadas=[
            item for item in _as_list(payload.get("fases_liberadas")) if item in PHASE_ORDER
        ],
        tema=_as_str(payload.get("tema")),
        plataforma=_as_str(payload.get("plataforma")),
        objetivo_do_post=_as_str(payload.get("objetivo_do_post")),
        personalidade=_as_str(payload.get("personalidade")),
        tipo_de_post=migrate_tipo_de_post(payload.get("tipo_de_post")),
        slides_gerados=[item for item in _as_list(payload.get("slides_gerados")) if isinstance(item, dict)],
        tool=tool if tool in FERRAMENTAS_VALIDAS else "codex",  # type: ignore[arg-type]
        model=payload.get("model") if isinstance(payload.get("model"), str) else None,
        sandbox=sandbox if sandbox in SANDBOXES_VALIDOS else "read-only",  # type: ignore[arg-type]
        briefing_autoral=_as_dict(payload.get("briefing_autoral")),
        restricoes_de_geracao=[
            item for item in _as_list(payload.get("restricoes_de_geracao")) if isinstance(item, str)
        ],
        interview_state=(
            _as_dict(payload.get("interview_state"))
            if isinstance(payload.get("interview_state"), dict)
            else None
        ),
        evidence_ledger=[
            item for item in _as_list(payload.get("evidence_ledger")) if isinstance(item, dict)
        ],
        gateway_result=_as_dict(payload.get("gateway_result")),
        fase_atual=_as_str(payload.get("fase_atual"), "entrada"),
        status_operacional=_as_str(
            payload.get("status_operacional"), "Aguardando entrada inicial."
        ),
        prompt_renderizado=_as_str(payload.get("prompt_renderizado")),
        stdout=_as_str(payload.get("stdout")),
        stderr=_as_str(payload.get("stderr")),
        returncode=_as_int_or_none(payload.get("returncode")),
        events=[item for item in _as_list(payload.get("events")) if isinstance(item, dict)],
        error=payload.get("error") if isinstance(payload.get("error"), str) else None,
        conteudo_gerado=_as_str(payload.get("conteudo_gerado")),
        conteudo_json=_as_dict(payload.get("conteudo_json")),
        segmentos=[item for item in _as_list(payload.get("segmentos")) if isinstance(item, dict)],
        avaliacao_post=_as_dict(payload.get("avaliacao_post")),
        is_running=_as_bool(payload.get("is_running")),
        _segmento_index=_as_int_or_none(payload.get("_segmento_index")),
        editorial_flow=normalize_editorial_flow(payload.get("editorial_flow")),
    )


def salvar_sessao(state: TuiSessionState, caminho: Path | None = None) -> Path:
    destino = Path(caminho) if caminho is not None else SESSION_FILE
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(
        json.dumps(_state_to_dict(state), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return destino


def carregar_sessao(caminho: Path | None = None) -> TuiSessionState:
    origem = Path(caminho) if caminho is not None else SESSION_FILE
    try:
        raw = origem.read_text(encoding="utf-8")
        payload = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return TuiSessionState()
    if not isinstance(payload, dict):
        return TuiSessionState()
    try:
        return _dict_to_state(payload)
    except ValueError:
        # A persisted V2/V3 session is intentionally not opened as V4 state.
        return TuiSessionState()


def carregar_sessao_de_payload(payload: dict[str, Any]) -> TuiSessionState:
    if not isinstance(payload, dict):
        raise ValueError("payload de sessao precisa ser um objeto")
    return _dict_to_state(payload)


__all__ = [
    "DATA_DIR",
    "SESSION_FILE",
    "carregar_sessao",
    "carregar_sessao_de_payload",
    "salvar_sessao",
]
