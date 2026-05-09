"""Dominio do fluxo editorial V3: storyboard, rascunhos e composicao."""
from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from .schemas import TuiSessionState

EDITORIAL_FLOW_SCHEMA_VERSION = "1.0"

EDITORIAL_PERSONAS: list[dict[str, str]] = [
    {"id": "provocador", "name": "O Provocador"},
    {"id": "analitico", "name": "O Analitico"},
    {"id": "contador_de_historias", "name": "O Contador de Historias"},
    {"id": "observador", "name": "O Observador"},
    {"id": "cetico", "name": "O Cetico"},
    {"id": "pragmatico", "name": "O Pragmatico"},
    {"id": "filosofo", "name": "O Filosofo"},
    {"id": "contrapontista", "name": "O Contrapontista"},
    {"id": "investigador", "name": "O Investigador"},
    {"id": "sintetizador", "name": "O Sintetizador"},
]

_PERSONA_BY_ID = {p["id"]: p for p in EDITORIAL_PERSONAS}


def empty_editorial_flow() -> dict[str, Any]:
    return {
        "schema_version": EDITORIAL_FLOW_SCHEMA_VERSION,
        "briefing_fingerprint": "",
        "storyboard": {
            "version": 0,
            "status": "empty",
            "blocks": [],
        },
        "drafts": {
            "storyboard_version": 0,
            "by_block": {},
        },
        "composition": {
            "status": "empty",
            "selection_fingerprint": "",
            "conteudo": "",
            "conteudo_json": {},
        },
    }


def normalize_editorial_flow(raw: object) -> dict[str, Any]:
    if not isinstance(raw, dict) or not raw:
        return empty_editorial_flow()
    flow = empty_editorial_flow()
    flow["schema_version"] = str(raw.get("schema_version", EDITORIAL_FLOW_SCHEMA_VERSION))
    flow["briefing_fingerprint"] = str(raw.get("briefing_fingerprint", ""))

    storyboard_raw = raw.get("storyboard")
    if isinstance(storyboard_raw, dict):
        blocks_raw = storyboard_raw.get("blocks", [])
        blocks: list[dict[str, Any]] = []
        if isinstance(blocks_raw, list):
            for index, item in enumerate(blocks_raw, start=1):
                if not isinstance(item, dict):
                    continue
                role = str(item.get("role", "")).strip()
                focus = str(item.get("focus", "")).strip()
                if not role or not focus:
                    continue
                blocks.append(
                    {
                        "id": str(item.get("id") or f"blk_{uuid.uuid4().hex[:8]}"),
                        "order": int(item.get("order", index)),
                        "role": role,
                        "focus": focus,
                        "revision": int(item.get("revision", 1)),
                    }
                )
        blocks.sort(key=lambda b: b["order"])
        flow["storyboard"] = {
            "version": int(storyboard_raw.get("version", 0)),
            "status": str(storyboard_raw.get("status", "empty")),
            "blocks": blocks,
        }

    drafts_raw = raw.get("drafts")
    if isinstance(drafts_raw, dict):
        by_block: dict[str, Any] = {}
        by_block_raw = drafts_raw.get("by_block", {})
        if isinstance(by_block_raw, dict):
            for block_id, entry in by_block_raw.items():
                if isinstance(entry, dict):
                    by_block[str(block_id)] = dict(entry)
        flow["drafts"] = {
            "storyboard_version": int(drafts_raw.get("storyboard_version", 0)),
            "by_block": by_block,
        }

    composition_raw = raw.get("composition")
    if isinstance(composition_raw, dict):
        conteudo_json = composition_raw.get("conteudo_json", {})
        flow["composition"] = {
            "status": str(composition_raw.get("status", "empty")),
            "selection_fingerprint": str(composition_raw.get("selection_fingerprint", "")),
            "conteudo": str(composition_raw.get("conteudo", "")),
            "conteudo_json": dict(conteudo_json) if isinstance(conteudo_json, dict) else {},
        }

    return flow


def compute_briefing_fingerprint(state: TuiSessionState) -> str:
    payload = {
        "briefing": state.briefing_autoral,
        "tema": state.tema,
        "plataforma": state.plataforma,
        "objetivo": state.objetivo_do_post,
        "tipo": state.tipo_de_post,
        "personalidade": state.personalidade,
    }
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]


def compute_selection_fingerprint(flow: dict[str, Any]) -> str:
    storyboard = flow.get("storyboard", {})
    drafts = flow.get("drafts", {})
    blocks = storyboard.get("blocks", []) if isinstance(storyboard, dict) else []
    by_block = drafts.get("by_block", {}) if isinstance(drafts, dict) else {}
    selections: list[dict[str, str]] = []
    if isinstance(blocks, list) and isinstance(by_block, dict):
        for block in blocks:
            if not isinstance(block, dict):
                continue
            block_id = str(block.get("id", ""))
            entry = by_block.get(block_id, {})
            if isinstance(entry, dict):
                selected = str(entry.get("selected_option_id", ""))
                if selected:
                    selections.append({"block_id": block_id, "option_id": selected})
    encoded = json.dumps(
        {"version": storyboard.get("version", 0), "selections": selections},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]


def derive_editorial_status(flow: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_editorial_flow(flow)
    storyboard = normalized["storyboard"]
    drafts = normalized["drafts"]
    composition = normalized["composition"]

    blocks = storyboard.get("blocks", [])
    storyboard_available = (
        storyboard.get("status") == "available"
        and isinstance(blocks, list)
        and len(blocks) > 0
    )

    by_block = drafts.get("by_block", {})
    block_ids = [str(b["id"]) for b in blocks if isinstance(b, dict) and b.get("id")]
    drafts_partial = False
    drafts_available = False
    selection_complete = False

    if block_ids and isinstance(by_block, dict):
        complete_blocks = 0
        selected_blocks = 0
        for block_id in block_ids:
            entry = by_block.get(block_id)
            if not isinstance(entry, dict):
                continue
            status = str(entry.get("status", ""))
            options = entry.get("options", [])
            valid_options = (
                isinstance(options, list)
                and len([o for o in options if isinstance(o, dict) and not o.get("obsolete")])
                >= 3
            )
            if status in ("available", "partial") and valid_options:
                complete_blocks += 1
            elif status == "partial":
                drafts_partial = True
            if entry.get("selected_option_id"):
                selected_blocks += 1
        drafts_available = complete_blocks == len(block_ids) and complete_blocks > 0
        drafts_partial = drafts_partial or (
            0 < complete_blocks < len(block_ids)
        )
        selection_complete = selected_blocks == len(block_ids) and len(block_ids) > 0

    composition_stale = False
    if composition.get("status") == "available":
        current_fp = compute_selection_fingerprint(normalized)
        composition_stale = composition.get("selection_fingerprint") != current_fp

    return {
        "storyboard_available": storyboard_available,
        "drafts_partial": drafts_partial,
        "drafts_available": drafts_available,
        "selection_incomplete": storyboard_available and not selection_complete,
        "selection_complete": selection_complete,
        "composition_stale": composition_stale,
        "composition_available": composition.get("status") == "available" and not composition_stale,
        "can_compose": selection_complete and not composition_stale,
    }


def new_block_id() -> str:
    return f"blk_{uuid.uuid4().hex[:8]}"


def new_option_id() -> str:
    return f"opt_{uuid.uuid4().hex[:8]}"


def assign_storyboard_blocks(raw_blocks: list[dict[str, Any]], *, version: int) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for index, item in enumerate(raw_blocks, start=1):
        role = str(item.get("role", "")).strip()
        focus = str(item.get("focus", "")).strip()
        if not role:
            raise ValueError(f"Bloco {index}: papel obrigatorio.")
        if not focus:
            raise ValueError(f"Bloco {index}: foco obrigatorio.")
        if "\n\n" in focus:
            raise ValueError(f"Bloco {index}: foco nao pode ter paragrafos longos.")
        blocks.append(
            {
                "id": str(item.get("id") or new_block_id()),
                "order": index,
                "role": role,
                "focus": focus,
                "revision": int(item.get("revision", version)),
            }
        )
    return blocks


def invalidate_drafts_and_composition(flow: dict[str, Any], *, mark_obsolete: bool = True) -> None:
    drafts = flow.setdefault("drafts", {"storyboard_version": 0, "by_block": {}})
    if mark_obsolete and isinstance(drafts.get("by_block"), dict):
        for entry in drafts["by_block"].values():
            if isinstance(entry, dict) and isinstance(entry.get("options"), list):
                for opt in entry["options"]:
                    if isinstance(opt, dict):
                        opt["obsolete"] = True
    drafts["by_block"] = {}
    drafts["storyboard_version"] = flow.get("storyboard", {}).get("version", 0)
    flow["composition"] = {
        "status": "obsolete" if mark_obsolete else "empty",
        "selection_fingerprint": "",
        "conteudo": "",
        "conteudo_json": {},
    }


def clear_downstream_if_editorial_origin(state: TuiSessionState) -> None:
    composition = normalize_editorial_flow(state.editorial_flow).get("composition", {})
    if composition.get("status") in ("available", "obsolete"):
        state.conteudo_gerado = ""
        state.conteudo_json = {}
        state.segmentos = []
        state.avaliacao_post = {}


def persona_by_id(persona_id: str) -> dict[str, str] | None:
    return _PERSONA_BY_ID.get(persona_id)
