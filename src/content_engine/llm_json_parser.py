"""Extracao robusta de JSON de retorno de LLM (codex/opencode).

Os agentes CLI podem retornar:
- JSON puro (um unico objeto na saida).
- JSONL (uma linha por evento, a ultima ou uma especifica contem a avaliacao).
- Texto com JSON embutido (markdown, explicacoes ao redor).
- Multiplos objetos JSON concatenados.

Esta funcao aplica a estrategia sugerida na correcao do bug de parse
"Extra data: line 2 column 1" do pipeline autoral:

1. Tenta ``json.loads`` direto.
2. Tenta cada linha como JSON (JSONL), coletando objetos validos.
3. Tenta o trecho entre o primeiro ``{`` e o ultimo ``}``.
4. Tenta objetos balanceados em ordem de ocorrencia (do primeiro ao ultimo).
5. Escolhe o objeto que melhor representa a avaliacao (com ``deltas``,
   ``evidencias`` e ``lacunas``); em ultimo caso, o ultimo objeto valido.

Nenhuma excecao eh propagada: sempre retorna um :class:`ParsedLLMJson`
com ``ok=False`` e mensagem diagnostica caso nao seja possivel extrair.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ParsedLLMJson:
    ok: bool
    data: dict[str, Any] | None = None
    error: str | None = None
    raw_output: str = ""
    candidate_keys: tuple[str, ...] = ()


_EVALUATION_KEYS: tuple[str, ...] = ("deltas", "evidencias", "lacunas")
_CONTENT_KEYS: tuple[str, ...] = ("conteudo", "metadados", "alertas")
_ROUTER_KEYS: tuple[str, ...] = ("tipoDePost", "tipo_de_post")
# Chaves tipicas de eventos JSONL emitidos pelos CLIs; objetos que
# contiverem APENAS essas chaves (ou um subconjunto) nao sao o payload
# final do agente.
_CODEX_EVENT_KEYS: frozenset[str] = frozenset(
    {
        # Codex CLI (legacy)
        "type",
        "thread_id",
        "usage",
        "item",
        "id",
        "error",
        "reason",
        # OpenCode CLI
        "timestamp",
        "sessionID",
        "part",
    }
)
_BALANCED_OBJECT_RE = re.compile(r"\{", re.MULTILINE)
_MARKDOWN_JSON_FENCE_RE = re.compile(
    r"^```(?:json|JSON)?\s*\n?(.*?)\n?```\s*$",
    re.DOTALL,
)


def _try_loads(text: str) -> dict[str, Any] | None:
    try:
        parsed: Any = json.loads(text, strict=False)
    except (ValueError, json.JSONDecodeError):
        return None
    if isinstance(parsed, dict):
        return parsed
    return None


def _iter_jsonl_objects(stdout: str) -> list[dict[str, Any]]:
    objs: list[dict[str, Any]] = []
    for line in stdout.splitlines():
        linha = line.strip()
        if not linha or not linha.startswith("{"):
            continue
        try:
            parsed: Any = json.loads(linha, strict=False)
        except (ValueError, json.JSONDecodeError):
            continue
        if isinstance(parsed, dict):
            objs.append(parsed)
            # Extrair JSON aninhado em campos 'text' (Codex legacy + OpenCode)
            _extract_nested_text_json(parsed, objs)
    return objs


def _unwrap_text_payload(text: str) -> str:
    """Remove fences markdown (ex.: `` ```json ``) e devolve o payload textual."""
    cleaned = (text or "").strip()
    if not cleaned:
        return ""
    fenced = _MARKDOWN_JSON_FENCE_RE.match(cleaned)
    if fenced is not None:
        return fenced.group(1).strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json|JSON)?\s*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```\s*$", "", cleaned).strip()
    return cleaned


def _collect_event_text_fields(obj: dict[str, Any]) -> list[str]:
    """Coleta campos de texto de envelopes CLI.

    - Codex (legacy): ``item.text``
    - OpenCode: ``part.text``
    - Fallback generico: ``text`` no topo
    """
    texts: list[str] = []
    item = obj.get("item")
    if isinstance(item, dict):
        text = item.get("text")
        if isinstance(text, str) and text.strip():
            texts.append(text)
    part = obj.get("part")
    if isinstance(part, dict):
        text = part.get("text")
        if isinstance(text, str) and text.strip():
            texts.append(text)
    top = obj.get("text")
    if isinstance(top, str) and top.strip():
        texts.append(top)
    return texts


def _extract_nested_text_json(obj: dict[str, Any], objs: list[dict[str, Any]]) -> None:
    """Extrai JSON aninhado em campos 'text' de eventos CLI (Codex + OpenCode)."""
    for text in _collect_event_text_fields(obj):
        payload = _unwrap_text_payload(text)
        if not payload.startswith("{"):
            continue
        nested = _try_loads(payload)
        if nested is not None and nested not in objs:
            objs.append(nested)


def _iter_balanced_objects(stdout: str) -> list[dict[str, Any]]:
    """Varre o texto coletando objetos JSON balanceados (do primeiro ``{``)."""
    objs: list[dict[str, Any]] = []
    depth = 0
    start = -1
    in_string = False
    escape = False
    for index, char in enumerate(stdout):
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            continue
        if char == "{":
            if depth == 0:
                start = index
            depth += 1
        elif char == "}":
            if depth == 0:
                continue
            depth -= 1
            if depth == 0 and start != -1:
                snippet = stdout[start : index + 1]
                parsed = _try_loads(snippet)
                if parsed is not None:
                    objs.append(parsed)
                start = -1
    return objs


_CODEX_TEXT_JSON_RE = re.compile(
    r'"text":"(\{(?:[^{}]|\{[^{}]*\})*\})"',
    re.DOTALL,
)


def _iter_codex_text_json(stdout: str) -> list[dict[str, Any]]:
    """Extrai o JSON aninhado dentro de campos ``text`` de eventos do Codex.

    O codex CLI emite JSONL com o JSON de payload dentro do campo ``text``,
    onde as aspas duplas do JSON aninhado aparecem **nao escapadas** e o
    conteudo pode conter newlines literais, tornando o JSONL invalido para
    parsers estritos. Esta rotina usa uma heuristica regex para localizar
    o JSON aninhado e tenta parsea-lo com ``strict=False``.
    """
    objs: list[dict[str, Any]] = []
    for match in _CODEX_TEXT_JSON_RE.finditer(stdout or ""):
        raw = match.group(1)
        # Re-escapar aspas duplas internas: o codex emite \" como aspas
        # literais escapadas (uma barra + aspa) que precisam virar ".
        candidate = raw.replace('\\"', '"')
        parsed = _try_loads(candidate)
        if parsed is not None:
            objs.append(parsed)
    return objs


def _score_evaluation_payload(obj: dict[str, Any]) -> int:
    return sum(1 for key in _EVALUATION_KEYS if key in obj)


def _score_content_payload(obj: dict[str, Any]) -> int:
    return sum(1 for key in _CONTENT_KEYS if key in obj)


def _score_router_payload(obj: dict[str, Any]) -> int:
    return sum(1 for key in _ROUTER_KEYS if key in obj)


def _score_preferred_keys(obj: dict[str, Any], keys: tuple[str, ...]) -> int:
    if not keys:
        return 0
    return sum(2 for key in keys if key in obj)


def _looks_like_codex_event(obj: dict[str, Any]) -> bool:
    """Heuristica: objeto parece envelope de evento CLI (Codex/OpenCode), nao o payload."""
    if not obj:
        return True
    # Se TODAS as chaves do objeto estao no conjunto de chaves de evento
    # do CLI, e evento de envelope.
    keys = set(obj.keys())
    if keys.issubset(_CODEX_EVENT_KEYS):
        return True
    # Se a unica chave "informativa" for "type" e o valor for um evento conhecido
    if keys == {"type"} and isinstance(obj.get("type"), str):
        return True
    return False


def _is_codex_error_event(obj: dict[str, Any]) -> bool:
    """Verifica se o objeto e um evento de erro do Codex."""
    if not isinstance(obj, dict):
        return False
    # Evento direto: {"type": "error", "message": "..."}
    if obj.get("type") == "error" and isinstance(obj.get("message"), str):
        return True
    # Evento aninhado: {"type": "turn.failed", "error": {"message": "..."}}
    if obj.get("type") == "turn.failed" and isinstance(obj.get("error"), dict):
        error = obj["error"]
        if isinstance(error.get("message"), str):
            return True
    # Item de erro: {"type": "item.completed", "item": {"type": "error", "message": "..."}}
    item = obj.get("item")
    if isinstance(item, dict) and item.get("type") == "error":
        if isinstance(item.get("message"), str):
            return True
    return False


def _extract_codex_error_message(candidates: list[dict[str, Any]]) -> str | None:
    """Extrai mensagem de erro de eventos do Codex, se presente."""
    for obj in candidates:
        if not isinstance(obj, dict):
            continue
        # Evento direto
        if obj.get("type") == "error" and isinstance(obj.get("message"), str):
            return obj["message"]
        # Turn failed
        if obj.get("type") == "turn.failed" and isinstance(obj.get("error"), dict):
            error = obj["error"]
            if isinstance(error.get("message"), str):
                return error["message"]
        # Item error
        item = obj.get("item")
        if isinstance(item, dict) and item.get("type") == "error":
            if isinstance(item.get("message"), str):
                return item["message"]
    return None


def _pick_best_evaluation(
    candidates: list[dict[str, Any]],
    *,
    prefer_keys: tuple[str, ...] = (),
) -> dict[str, Any] | None:
    if not candidates:
        return None

    def _score(obj: dict[str, Any]) -> tuple[int, int, int, int]:
        eval_score = _score_evaluation_payload(obj)
        content_score = _score_content_payload(obj)
        router_score = _score_router_payload(obj)
        preferred_score = _score_preferred_keys(obj, prefer_keys)
        # Bonus para objetos que nao sao eventos do codex
        event_penalty = -100 if _looks_like_codex_event(obj) else 0
        # Bonus para objetos que tem ao menos uma chave string com valor
        # de texto (>=10 chars) - payload autoral real.
        has_real_string = sum(
            1
            for v in obj.values()
            if isinstance(v, str) and len(v) >= 10
        )
        return (
            event_penalty
            + max(eval_score, content_score, router_score, preferred_score),
            has_real_string,
            eval_score + content_score + router_score + preferred_score,
            0,
        )

    scored: list[tuple[tuple[int, int, int, int], int, dict[str, Any]]] = []
    for index, obj in enumerate(candidates):
        scored.append((_score(obj), -index, obj))
    scored.sort(key=lambda item: (item[0][0], item[0][1], item[0][2], item[1]), reverse=True)

    # Se o melhor candidato nao pontuou (sem chaves relevantes), descartar
    best = scored[0]
    if best[0][2] <= 0 and best[0][0] <= 0:
        # Sem keys conhecidas (eval/content), retorna o ultimo candidato
        # que nao seja evento do codex, ou o ultimo em ultimo caso.
        for _, _, obj in reversed(scored):
            if not _looks_like_codex_event(obj):
                return obj
        return scored[-1][2]
    return best[2]


def extract_json_object_from_llm_output(
    stdout: str,
    *,
    prefer_evaluation_shape: bool = True,
    prefer_keys: tuple[str, ...] = (),
) -> ParsedLLMJson:
    """Extrai o melhor objeto JSON de avaliacao de uma saida de LLM.

    Parametros:
        stdout: saida bruta da LLM.
        prefer_evaluation_shape: se True, prioriza objetos que contem
            ``deltas``/``evidencias``/``lacunas``; em ultimo caso, retorna
            o ultimo objeto JSON valido. Se False, retorna o primeiro.
        prefer_keys: chaves extras para priorizar na escolha do melhor
            objeto (ex.: ``("tipoDePost",)`` no roteador de trilhas).

    Retorna:
        :class:`ParsedLLMJson` com ``ok=True`` e ``data`` preenchido quando
        ha objeto JSON recuperavel; caso contrario, ``ok=False`` e ``error``
        descrevendo o motivo.
    """
    raw = stdout or ""
    if not raw.strip():
        return ParsedLLMJson(
            ok=False,
            error="stdout vazio",
            raw_output=raw,
        )

    candidatos: list[dict[str, Any]] = []

    parsed = _try_loads(raw)
    if parsed is not None:
        candidatos.append(parsed)

    for obj in _iter_jsonl_objects(raw):
        if obj not in candidatos:
            candidatos.append(obj)

    for obj in _iter_balanced_objects(raw):
        if obj not in candidatos:
            candidatos.append(obj)

    for obj in _iter_codex_text_json(raw):
        if obj not in candidatos:
            candidatos.append(obj)

    if not candidatos:
        inicio = raw.find("{")
        fim = raw.rfind("}")
        if inicio != -1 and fim != -1 and fim > inicio:
            obj = _try_loads(raw[inicio : fim + 1])
            if obj is not None:
                candidatos.append(obj)

    if not candidatos:
        return ParsedLLMJson(
            ok=False,
            error=(
                "Nenhum objeto JSON valido encontrado no stdout da LLM. "
                "Verifique logs para conteudo bruto."
            ),
            raw_output=raw,
        )

    if prefer_evaluation_shape or prefer_keys:
        escolhido = _pick_best_evaluation(candidatos, prefer_keys=prefer_keys)
        if escolhido is None:
            escolhido = candidatos[-1] if prefer_evaluation_shape else candidatos[0]
    else:
        escolhido = candidatos[0]

    # Verifica se o resultado e um evento de erro do Codex
    if _is_codex_error_event(escolhido):
        error_msg = _extract_codex_error_message(candidatos) or "Erro desconhecido do LLM"
        return ParsedLLMJson(
            ok=False,
            error=f"LLM retornou erro: {error_msg}",
            raw_output=raw,
        )

    return ParsedLLMJson(
        ok=True,
        data=escolhido,
        raw_output=raw,
        candidate_keys=tuple(sorted(escolhido.keys())),
    )


__all__ = ["ParsedLLMJson", "extract_json_object_from_llm_output"]
