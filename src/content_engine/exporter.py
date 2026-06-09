"""SPEC-036/037: exportacao do conteudo gerado."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .schemas import TipoDePost


EXPORTS_DIR: Path = Path(__file__).resolve().parents[2] / "exports"


_SLUG_INVALIDO = re.compile(r"[^a-z0-9_-]+")
_SLUG_HIFENS = re.compile(r"-{2,}")


def sanitizar_nome_arquivo(texto: str) -> str:
    lowered = texto.lower()
    trocado = _SLUG_INVALIDO.sub("-", lowered)
    colapsado = _SLUG_HIFENS.sub("-", trocado).strip("-")
    if not colapsado:
        return "post"
    if len(colapsado) > 80:
        colapsado = colapsado[:80].rstrip("-")
    return colapsado or "post"


def nome_arquivo_base(tema: str, plataforma: str, tipo_de_post: TipoDePost) -> str:
    return (
        f"{sanitizar_nome_arquivo(tema)}-"
        f"{sanitizar_nome_arquivo(plataforma)}-"
        f"{sanitizar_nome_arquivo(tipo_de_post)}"
    )


def _resolver_dir(exports_dir: Path | None) -> Path:
    if exports_dir is None:
        return EXPORTS_DIR
    return Path(exports_dir)


def _resolver_markdown_path(
    tema: str,
    plataforma: str,
    tipo_de_post: TipoDePost,
    exports_dir: Path | None,
    markdown_path: Path | None,
) -> Path:
    if markdown_path is not None:
        destino = Path(markdown_path)
        if destino.suffix.lower() != ".md":
            destino = destino.with_suffix(".md")
        return destino
    base = nome_arquivo_base(tema, plataforma, tipo_de_post)
    return _resolver_dir(exports_dir) / f"{base}.md"


def _write_text(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def montar_payload_json_exportacao(
    tema: str,
    plataforma: str,
    tipo_de_post: TipoDePost,
    conteudo: str,
    *,
    metadados: dict[str, Any] | None = None,
    alertas: list[str] | None = None,
    slides: list[dict[str, Any]] | None = None,
    segmentos: list[dict[str, Any]] | None = None,
    avaliacao_post: dict[str, Any] | None = None,
    parse_error: str | None = None,
) -> dict[str, Any]:
    return {
        "tema": tema,
        "plataforma": plataforma,
        "tipo_de_post": tipo_de_post,
        "conteudo": conteudo,
        "metadados": dict(metadados or {}),
        "alertas": list(alertas or []),
        "slides": list(slides or []),
        "segmentos": list(segmentos or []),
        "avaliacao_post": dict(avaliacao_post or {}),
        "parse_error": parse_error,
    }


def exportar_markdown(
    tema: str,
    plataforma: str,
    tipo_de_post: TipoDePost,
    conteudo: str,
    exports_dir: Path | None = None,
) -> Path:
    destino = _resolver_markdown_path(
        tema, plataforma, tipo_de_post, exports_dir, markdown_path=None
    )
    return _write_text(destino, conteudo)


def exportar_json(
    tema: str,
    plataforma: str,
    tipo_de_post: TipoDePost,
    payload: dict[str, Any],
    exports_dir: Path | None = None,
) -> Path:
    base = nome_arquivo_base(tema, plataforma, tipo_de_post)
    destino = _resolver_dir(exports_dir) / f"{base}.json"
    return _write_json(destino, payload)


def exportar_conteudo(
    tema: str,
    plataforma: str,
    tipo_de_post: TipoDePost,
    conteudo: str,
    *,
    slides: list[dict[str, Any]] | None = None,
    slidemark: dict[str, Any] | None = None,
    metadados: dict[str, Any] | None = None,
    alertas: list[str] | None = None,
    segmentos: list[dict[str, Any]] | None = None,
    avaliacao_post: dict[str, Any] | None = None,
    parse_error: str | None = None,
    exports_dir: Path | None = None,
    markdown_path: Path | None = None,
) -> list[Path]:
    md_path = _resolver_markdown_path(
        tema, plataforma, tipo_de_post, exports_dir, markdown_path
    )
    json_path = (
        md_path.with_suffix(".slidemark.json")
        if slidemark
        else md_path.with_suffix(".json")
    )
    payload = slidemark or montar_payload_json_exportacao(
        tema,
        plataforma,
        tipo_de_post,
        conteudo,
        metadados=metadados,
        alertas=alertas,
        slides=slides,
        segmentos=segmentos,
        avaliacao_post=avaliacao_post,
        parse_error=parse_error,
    )
    return [
        _write_text(md_path, conteudo),
        _write_json(json_path, payload),
    ]


def exportar_txt(
    tema: str,
    plataforma: str,
    tipo_de_post: TipoDePost,
    conteudo: str,
    exports_dir: Path | None = None,
) -> Path:
    base = nome_arquivo_base(tema, plataforma, tipo_de_post)
    target_dir = _resolver_dir(exports_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    destino = target_dir / f"{base}.txt"
    destino.write_text(conteudo, encoding="utf-8")
    return destino


__all__ = [
    "EXPORTS_DIR",
    "exportar_conteudo",
    "exportar_json",
    "exportar_markdown",
    "exportar_txt",
    "montar_payload_json_exportacao",
    "nome_arquivo_base",
    "sanitizar_nome_arquivo",
]
