"""Deterministic editorial-source safeguards for the composition stage.

The composition model remains responsible for rewriting and transitions.  This
module only identifies source details that must not be collapsed into a label
and audits the returned payload before it is persisted.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata
from typing import Any


_ARROW_RE = re.compile(r"(?P<chain>[^\n.!?]+(?:\s*(?:→|->)\s*[^\n.!?]+){2,})")
_ORDINAL_CUE_RE = re.compile(
    r"\b(?:primeiro|segundo|terceiro|quarto|quinto|sexto)\s*:", re.IGNORECASE
)
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+|\n{2,}")
_WORD_RE = re.compile(r"[a-z0-9]+")

_STOPWORDS = {
    "a",
    "ao",
    "aos",
    "as",
    "com",
    "como",
    "da",
    "das",
    "de",
    "do",
    "dos",
    "e",
    "ela",
    "ele",
    "em",
    "essa",
    "esse",
    "esta",
    "este",
    "foi",
    "ja",
    "mais",
    "na",
    "nas",
    "no",
    "nos",
    "o",
    "os",
    "ou",
    "para",
    "por",
    "que",
    "se",
    "sem",
    "so",
    "sua",
    "suo",
    "um",
    "uma",
}
_ACTION_MARKERS = ("isola", "estabil", "test", "extrai", "migra", "separa")
_CAUSAL_MARKERS = ("mudanc", "atravess", "evolu", "exig", "contrat", "deploy", "coorden")
_CONSEQUENCE_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("contratos", ("contrat",)),
    ("deploy coordenado", ("deploy", "coorden")),
    ("testes cruzados", ("test",)),
    ("incidentes/rastreabilidade", ("incident", "rastre")),
)


@dataclass(frozen=True)
class EditorialAnchor:
    """A source element whose editorial force must survive composition."""

    id: str
    block_id: str
    kind: str
    source_excerpt: str
    instruction: str
    evidence_groups: tuple[tuple[str, ...], ...]
    minimum_groups: int

    def to_prompt_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "block_id": self.block_id,
            "kind": self.kind,
            "trecho_fonte": self.source_excerpt,
            "preservar": self.instruction,
        }


@dataclass(frozen=True)
class EditorialPreservationIssue:
    anchor: EditorialAnchor
    matched_groups: int

    def describe(self) -> str:
        return (
            f"Bloco {self.anchor.block_id} perdeu {self.anchor.kind} "
            f"({self.matched_groups}/{self.anchor.minimum_groups} sinais): "
            f"{self.anchor.source_excerpt}"
        )


def extract_editorial_anchors(
    selected_drafts: list[dict[str, Any]],
) -> list[EditorialAnchor]:
    """Extract high-value details from selected drafts without an extra LLM call.

    The heuristics are intentionally narrow: only observable scenarios,
    explicit chains, methods and operational sequences become hard guards.
    Everything else remains editable source material for the model.
    """

    anchors: list[EditorialAnchor] = []
    for position, draft in enumerate(selected_drafts, start=1):
        block_id = str(draft.get("block_id") or f"draft-{position}")
        content = _clean_text(str(draft.get("content", "")))
        if not content:
            continue

        candidates = _anchors_for_draft(block_id, content)
        anchors.extend(candidates[:2])
    return anchors


def validate_composition_preservation(
    payload: dict[str, Any],
    anchors: list[EditorialAnchor],
) -> list[EditorialPreservationIssue]:
    """Return source details that were reduced below the editorial contract."""

    output_tokens = _token_set(_payload_editorial_text(payload))
    issues: list[EditorialPreservationIssue] = []
    for anchor in anchors:
        matched_groups = sum(
            1
            for group in anchor.evidence_groups
            if any(_matches_term(term, output_tokens) for term in group)
        )
        if matched_groups < anchor.minimum_groups:
            issues.append(EditorialPreservationIssue(anchor, matched_groups))
    return issues


def editorial_anchors_for_prompt(anchors: list[EditorialAnchor]) -> list[dict[str, object]]:
    return [anchor.to_prompt_dict() for anchor in anchors]


def format_preservation_issues(issues: list[EditorialPreservationIssue]) -> str:
    return "\n".join(f"- {issue.describe()}" for issue in issues)


def _anchors_for_draft(block_id: str, content: str) -> list[EditorialAnchor]:
    candidates: list[EditorialAnchor] = []
    candidates.extend(_arrow_chain_anchors(block_id, content))
    candidates.extend(_ordinal_sequence_anchors(block_id, content))
    candidates.extend(_graph_method_anchors(block_id, content))
    candidates.extend(_concrete_scenario_anchors(block_id, content))
    candidates.extend(_causal_consequence_anchors(block_id, content))
    return _unique_anchor_kinds(candidates)


def _arrow_chain_anchors(block_id: str, content: str) -> list[EditorialAnchor]:
    match = _ARROW_RE.search(content)
    if match is None:
        return []
    chain = match.group("chain").strip()
    stages = [stage.strip(" -;:\t") for stage in re.split(r"\s*(?:→|->)\s*", chain)]
    groups = tuple(tuple(_keywords(stage, limit=5)) for stage in stages)
    groups = tuple(group for group in groups if group)
    if len(groups) < 3:
        return []

    normalized_chain = _normalized_text(chain)
    operational = any(marker in normalized_chain for marker in _ACTION_MARKERS)
    causal = any(marker in normalized_chain for marker in _CAUSAL_MARKERS)
    if not operational and not causal:
        return []
    kind = "sequencia_operacional" if operational else "cadeia_causal"
    instruction = (
        "Mantenha todas as etapas e a ordem operacional; nao reduza a sequencia a uma "
        "instrucao ambigua."
        if operational
        else "Mantenha as etapas da relacao de causa e efeito, nao apenas a conclusao."
    )
    return [
        EditorialAnchor(
            id=f"{block_id}:{kind}",
            block_id=block_id,
            kind=kind,
            source_excerpt=chain,
            instruction=instruction,
            evidence_groups=groups,
            minimum_groups=len(groups),
        )
    ]


def _ordinal_sequence_anchors(block_id: str, content: str) -> list[EditorialAnchor]:
    normalized = _normalized_text(content)
    if len(_ORDINAL_CUE_RE.findall(normalized)) < 3:
        return []
    has_extraction_stages = (
        "isol" in normalized
        and "estabil" in normalized
        and any(marker in normalized for marker in ("test", "flag", "migr"))
        and "extrai" in normalized
    )
    if not has_extraction_stages:
        return []
    source_groups = (
        ("isola", "modul"),
        ("estabil", "contrat", "borda"),
        ("test", "valida", "flag", "migr"),
        ("extrai", "fisic", "servic", "process"),
    )
    if not all(any(marker in normalized for marker in group) for group in source_groups):
        return []
    excerpt = _sequence_excerpt(content)
    return [
        EditorialAnchor(
            id=f"{block_id}:sequencia-operacional",
            block_id=block_id,
            kind="sequencia_operacional",
            source_excerpt=excerpt,
            instruction=(
                "Mantenha a progressao completa: fronteira logica validada antes da "
                "extracao fisica."
            ),
            evidence_groups=source_groups,
            minimum_groups=len(source_groups),
        )
    ]


def _graph_method_anchors(block_id: str, content: str) -> list[EditorialAnchor]:
    normalized = _normalized_text(content)
    if "grafo" not in normalized or not ("centralidade" in normalized or "nos" in normalized):
        return []
    excerpt = _sentence_containing(content, ("grafo",))
    if "centralidade" not in _normalized_text(excerpt) and "nos" not in _normalized_text(excerpt):
        excerpt = _surrounding_excerpt(content, "grafo")
    return [
        EditorialAnchor(
            id=f"{block_id}:metodo-grafo",
            block_id=block_id,
            kind="metodo_autoral",
            source_excerpt=excerpt,
            instruction=(
                "Mantenha o metodo de transformar artefatos em grafo e observar "
                "nos centrais; metricas isoladas nao o substituem."
            ),
            evidence_groups=(("grafo",), ("centralidade", "nos", "central")),
            minimum_groups=2,
        )
    ]


def _concrete_scenario_anchors(block_id: str, content: str) -> list[EditorialAnchor]:
    for sentence in _sentences(content):
        words = _token_set(sentence)
        has_customer_flow = (
            _matches_term("cliente", words)
            and _matches_term("pedido", words)
            and any(_matches_term(term, words) for term in ("pagar", "pagou", "pagamento"))
        )
        has_observable_break = any(
            _matches_term(term, words) for term in ("ainda", "aparece", "nasce", "pendente", "atrasado")
        )
        if not (has_customer_flow and has_observable_break):
            continue
        terms = tuple(_keywords(sentence, limit=6))
        groups = tuple((term,) for term in terms)
        return [
            EditorialAnchor(
                id=f"{block_id}:situacao-concreta",
                block_id=block_id,
                kind="situacao_concreta",
                source_excerpt=sentence,
                instruction=(
                    "Mantenha uma situacao observavel equivalente; nao a troque apenas "
                    "pelo nome de uma categoria tecnica."
                ),
                evidence_groups=groups,
                minimum_groups=min(3, len(groups)),
            )
        ]
    return []


def _causal_consequence_anchors(block_id: str, content: str) -> list[EditorialAnchor]:
    sentences = _sentences(content)
    for index, sentence in enumerate(sentences):
        excerpt = sentence
        if index + 1 < len(sentences):
            excerpt = f"{excerpt} {sentences[index + 1]}"
        source_tokens = _token_set(excerpt)
        groups = tuple(
            terms
            for _, terms in _CONSEQUENCE_GROUPS
            if any(_matches_term(term, source_tokens) for term in terms)
        )
        if len(groups) < 3:
            continue
        return [
            EditorialAnchor(
                id=f"{block_id}:consequencias-operacionais",
                block_id=block_id,
                kind="mecanismo_causal",
                source_excerpt=excerpt,
                instruction=(
                    "Mantenha consequencias observaveis da dependencia entre as partes; "
                    "nao as reduza ao rotulo de acoplamento."
                ),
                evidence_groups=groups,
                minimum_groups=min(3, len(groups)),
            )
        ]
    return []


def _unique_anchor_kinds(candidates: list[EditorialAnchor]) -> list[EditorialAnchor]:
    unique: list[EditorialAnchor] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate.kind in seen:
            continue
        seen.add(candidate.kind)
        unique.append(candidate)
    return unique


def _payload_editorial_text(payload: dict[str, Any]) -> str:
    parts = [str(payload.get("conteudo", ""))]
    for key in ("slides",):
        raw_slides = payload.get(key)
        if isinstance(raw_slides, list):
            for slide in raw_slides:
                parts.extend(_slide_text(slide))
    slidemark = payload.get("slidemark")
    if isinstance(slidemark, dict):
        raw_slides = slidemark.get("slides")
        if isinstance(raw_slides, list):
            for slide in raw_slides:
                parts.extend(_slide_text(slide))
    return "\n".join(part for part in parts if part)


def _slide_text(raw: object) -> list[str]:
    if not isinstance(raw, dict):
        return []
    parts: list[str] = []
    for key in ("title", "subtitle", "body", "highlight", "bullets", "text", "cta", "code"):
        parts.extend(_strings_from_value(raw.get(key)))
    for key in ("left", "right"):
        column = raw.get(key)
        if isinstance(column, dict):
            parts.extend(_strings_from_value(column.get("label")))
            parts.extend(_strings_from_value(column.get("items")))
    return parts


def _strings_from_value(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [str(value.get("text", ""))] if value.get("text") else []
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            parts.extend(_strings_from_value(item))
        return parts
    return []


def _clean_text(value: str) -> str:
    return value.replace("\\n", "\n").strip()


def _normalized_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _token_set(value: str) -> set[str]:
    return set(_WORD_RE.findall(_normalized_text(value)))


def _keywords(value: str, *, limit: int) -> list[str]:
    words: list[str] = []
    for word in _WORD_RE.findall(_normalized_text(value)):
        if len(word) < 3 or word in _STOPWORDS or word in words:
            continue
        words.append(word)
        if len(words) == limit:
            break
    return words


def _matches_term(term: str, output_tokens: set[str]) -> bool:
    normalized = _normalized_text(term)
    if not normalized:
        return False
    if normalized in output_tokens:
        return True
    stem = normalized[:5] if len(normalized) >= 5 else normalized
    return any(token.startswith(stem) for token in output_tokens)


def _sentences(content: str) -> list[str]:
    return [part.strip() for part in _SENTENCE_RE.split(content) if part.strip()]


def _sentence_containing(content: str, terms: tuple[str, ...]) -> str:
    for sentence in _sentences(content):
        normalized = _normalized_text(sentence)
        if any(term in normalized for term in terms):
            return sentence
    return _first_clause(content)


def _surrounding_excerpt(content: str, term: str) -> str:
    sentences = _sentences(content)
    for index, sentence in enumerate(sentences):
        if term in _normalized_text(sentence):
            return " ".join(sentences[index : index + 2])
    return _first_clause(content)


def _sequence_excerpt(content: str) -> str:
    markers = ("isole", "estabilize", "feature flag", "migre", "extraia")
    snippets = [
        sentence
        for sentence in _sentences(content)
        if any(marker in _normalized_text(sentence) for marker in markers)
    ]
    return " ".join(snippets[:5]) or _first_clause(content)


def _first_clause(value: str) -> str:
    return re.split(r"[.!?\n]", value, maxsplit=1)[0].strip(" -;:\t")


__all__ = [
    "EditorialAnchor",
    "EditorialPreservationIssue",
    "editorial_anchors_for_prompt",
    "extract_editorial_anchors",
    "format_preservation_issues",
    "validate_composition_preservation",
]
