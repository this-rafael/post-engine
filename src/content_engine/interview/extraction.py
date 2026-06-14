"""Extracao deterministica de evidencias e sinais autorais."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Iterable

from .schemas import AuthorialSignal, Evidence, InterviewState, SelectedQuestion, UserAnswer


_SENTENCE_RE = re.compile(r"[^.!?\n]+(?:[.!?](?=\s|$)|$)", re.UNICODE)
_SIGNAL_PATTERNS: tuple[tuple[str, re.Pattern[str], str], ...] = (
    (
        "experiencia_vivida",
        re.compile(r"\b(?:trabalhei|usei|implementei|construi|vivi|passei|participei|projeto|sistema|equipe|cliente)\b", re.I),
        "A resposta menciona uma experiencia ou situacao vivida.",
    ),
    (
        "posicao_propria",
        re.compile(r"\b(?:acho|acredito|defendo|discordo|concordo|para mim|na minha opiniao|considero|entendo que)\b", re.I),
        "A resposta apresenta uma posicao propria.",
    ),
    (
        "concretude",
        re.compile(r"(?:\b\d+\b|\b(?:em|no|na)\s+[A-ZÀ-Ý][\wÀ-ÿ-]+|\b(?:segunda|terca|quarta|quinta|sexta|janeiro|fevereiro)\b|\b(?:exemplo|caso|trecho|log|erro|versao)\b)", re.I),
        "A resposta contem detalhe verificavel ou exemplo concreto.",
    ),
    (
        "aprendizado",
        re.compile(r"\b(?:aprendi|aprendizado|percebi|descobri|mudei|mudou|passei a|desde entao|licao)\b", re.I),
        "A resposta explicita aprendizado ou mudanca de entendimento.",
    ),
    (
        "criterio_proprio",
        re.compile(r"\b(?:porque|por isso|criterio|escolho|prefiro|evito|quando vale|depende|priorizo|decidi)\b", re.I),
        "A resposta fornece um criterio ou justificativa propria.",
    ),
    (
        "tensao",
        re.compile(r"\b(?:mas|porem|por[eé]m|embora|limite|contrad|ao mesmo tempo|nem sempre|falhou|erro)\b", re.I),
        "A resposta revela tensao, limite, contraste ou conflito.",
    ),
    (
        "consequencia",
        re.compile(r"\b(?:resultado|consequ|impact|por causa|por isso|levou a|evitou|reduziu|aumentou)\w*\b", re.I),
        "A resposta menciona uma consequencia ou efeito.",
    ),
    (
        "mecanismo",
        re.compile(r"\b(?:processo|fluxo|mecanismo|funciona|etapa|passo|causa|depende de|configur|arquitetura|tecnico)\w*\b", re.I),
        "A resposta descreve mecanismo, processo ou detalhe tecnico.",
    ),
    (
        "voz",
        re.compile(r"\b(?:eu|meu|minha|comigo|nao aceito|eu diria|o que me incomoda)\b", re.I),
        "A resposta preserva linguagem em primeira pessoa ou uma formulacao caracteristica.",
    ),
)
_UNCERTAINTY_RE = re.compile(
    r"\b(?:nao sei|não sei|nao posso afirmar|não posso afirmar|talvez|nao tenho experiencia|não tenho experiência|nunca fiz)\b",
    re.I,
)
_CONTRADICTION_RE = re.compile(r"\b(?:mas|porem|por[eé]m|ao mesmo tempo|contrad)\w*\b", re.I)


@dataclass(frozen=True)
class ExtractionResult:
    answer: UserAnswer
    evidence: tuple[Evidence, ...]
    signals: tuple[AuthorialSignal, ...]

    @property
    def evidences(self) -> tuple[Evidence, ...]:
        return self.evidence

    def __iter__(self):
        yield list(self.evidence)
        yield list(self.signals)

    def to_dict(self) -> dict[str, object]:
        return {
            "answer": self.answer.to_dict(),
            "evidence": [item.to_dict() for item in self.evidence],
            "signals": [item.to_dict() for item in self.signals],
        }


def _answer_id(state: InterviewState, explicit: str | None) -> str:
    if explicit and explicit.strip():
        return explicit.strip()
    return f"answer-{len(state.answers) + 1}"


def append_answer(
    state: InterviewState,
    question: SelectedQuestion | str | None = None,
    response: str | None = None,
    *,
    answer_id: str | None = None,
) -> UserAnswer:
    """Adiciona uma resposta sem jamais substituir seu texto original."""
    if response is None:
        response = ""
    selected = question if isinstance(question, SelectedQuestion) else None
    question_text = selected.question if selected else str(question or "")
    question_id = selected.candidate_id if selected and selected.candidate_id else f"question-{len(state.questions) + 1}"
    answer = UserAnswer(
        id=_answer_id(state, answer_id),
        question_id=question_id,
        question=question_text,
        original=response,
        sequence=len(state.answers) + 1,
    )
    state.answers.append(answer)
    state.question_count = max(state.question_count, len(state.answers))
    return answer


def _sentence_spans(text: str) -> list[str]:
    spans = [match.group(0).strip() for match in _SENTENCE_RE.finditer(text) if match.group(0).strip()]
    return spans or ([text.strip()] if text.strip() else [])


def _evidence_id(answer_id: str, index: int, text: str) -> str:
    digest = hashlib.sha1(f"{answer_id}:{index}:{text}".encode("utf-8")).hexdigest()[:12]
    return f"ev:{answer_id}:{digest}"


def _signal_id(answer_id: str, signal_type: str, index: int) -> str:
    return f"signal:{answer_id}:{signal_type}:{index}"


def _status_for_sentence(sentence: str, signal_type: str) -> str:
    if _UNCERTAINTY_RE.search(sentence):
        return "INCERTO"
    if signal_type == "tensao" or _CONTRADICTION_RE.search(sentence):
        return "CONFIRMADO"
    return "CONFIRMADO" if signal_type in {"experiencia_vivida", "concretude", "posicao_propria"} else "INFERIDO"


def extract_signals(answer: UserAnswer | str, *, answer_id: str | None = None) -> ExtractionResult:
    """Extrai sinais apenas de trechos que foram preservados como evidencias."""
    if isinstance(answer, str):
        answer = UserAnswer(id=answer_id or "answer-1", original=answer)
    source_id = answer.id or answer_id or "answer-1"
    sentences = _sentence_spans(answer.original)
    evidences: list[Evidence] = []
    signals: list[AuthorialSignal] = []

    for index, sentence in enumerate(sentences, start=1):
        evidence_id = _evidence_id(source_id, index, sentence)
        matched: list[tuple[str, str]] = [
            (signal_type, summary)
            for signal_type, pattern, summary in _SIGNAL_PATTERNS
            if pattern.search(sentence)
        ]
        if not matched:
            matched = [("fato_declarado", "A resposta contem uma declaracao do autor.")]
        types = tuple(signal_type for signal_type, _ in matched)
        evidences.append(
            Evidence(
                id=evidence_id,
                text=sentence,
                source_answer_id=source_id,
                signal_types=types,
            )
        )
        for signal_type, summary in matched:
            status = _status_for_sentence(sentence, signal_type)
            confidence = 0.9 if status == "CONFIRMADO" else 0.65
            if status == "INCERTO":
                confidence = 0.85
            signals.append(
                AuthorialSignal(
                    id=_signal_id(source_id, signal_type, index),
                    type=signal_type,
                    summary=f"{summary} Trecho: {sentence}",
                    confidence=confidence,
                    source_answer_id=source_id,
                    evidence_ids=(evidence_id,),
                    status=status,  # type: ignore[arg-type]
                )
            )

    return ExtractionResult(answer=answer, evidence=tuple(evidences), signals=tuple(signals))


def append_extraction(state: InterviewState, result: ExtractionResult) -> None:
    """Persiste uma extracao no ledger V4, evitando duplicatas por id."""
    known_evidence = {item.id for item in state.evidence_ledger}
    known_signals = {item.id for item in state.signals}
    state.evidence_ledger.extend(item for item in result.evidence if item.id not in known_evidence)
    state.signals.extend(item for item in result.signals if item.id not in known_signals)
    if state.answers:
        state.progress_state = "MATERIAL_HUMANO_IDENTIFICADO"


def signals_have_evidence(signals: Iterable[AuthorialSignal], evidence: Iterable[Evidence]) -> bool:
    evidence_ids = {item.id for item in evidence}
    return all(signal.evidence_ids and set(signal.evidence_ids) <= evidence_ids for signal in signals)


__all__ = [
    "ExtractionResult",
    "append_answer",
    "extract_signals",
    "append_extraction",
    "signals_have_evidence",
]
