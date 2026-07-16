"""Contratos do pipeline de entrevista V4.

O modulo e independente dos contratos de entrevista anteriores. O texto
original do autor fica congelado em :class:`UserAnswer`; tudo que e derivado
da resposta vive em objetos separados e aponta para evidencias literais.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


SESSION_SCHEMA_VERSION = "4.0"

ProgressState = Literal[
    "EXPLORANDO",
    "MATERIAL_HUMANO_IDENTIFICADO",
    "APROFUNDANDO",
    "MATERIAL_SUFICIENTE",
    "CONCLUIDA",
]

DimensionState = Literal[
    "NAO_OBSERVADA",
    "FRACA",
    "PARCIAL",
    "SUFICIENTE",
    "FORTE",
    "EXCEPCIONAL",
    "CONFLITANTE",
    "NAO_APLICAVEL",
]

SignalStatus = Literal["CONFIRMADO", "INFERIDO", "INCERTO", "CONFLITANTE"]
GatewayType = Literal["EQUILIBRADO", "DESEQUILIBRADO_FORTE", "REPROVADO"]


def _clean(value: object) -> str:
    return value.strip() if isinstance(value, str) else str(value or "").strip()


def _normalise(value: str) -> str:
    return " ".join(value.split())


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple, set)):
        return ()
    return tuple(_clean(item) for item in value if _clean(item))


def _dict(value: object) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _clamp_score(value: object) -> int:
    try:
        numeric = value if isinstance(value, (int, float, str)) else 0
        return max(0, min(100, int(round(float(numeric)))))
    except (TypeError, ValueError):
        return 0


@dataclass(frozen=True)
class ThemeContext:
    tema: str
    objetivo: str = ""
    formato: str = "post"
    personalidade: str = ""
    restricoes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "tema", _clean(self.tema))
        object.__setattr__(self, "objetivo", _clean(self.objetivo))
        object.__setattr__(self, "formato", _clean(self.formato) or "post")
        object.__setattr__(self, "personalidade", _clean(self.personalidade))
        object.__setattr__(self, "restricoes", _strings(self.restricoes))

    def to_dict(self) -> dict[str, Any]:
        return {
            "tema": self.tema,
            "objetivo": self.objetivo,
            "formato": self.formato,
            "personalidade": self.personalidade,
            "restricoes": list(self.restricoes),
        }

    @classmethod
    def from_dict(cls, raw: object) -> "ThemeContext":
        data = _dict(raw)
        return cls(
            tema=_clean(data.get("tema", "")),
            objetivo=_clean(data.get("objetivo", data.get("objetivo_do_post", ""))),
            formato=_clean(data.get("formato", data.get("tipo_de_post", "post"))),
            personalidade=_clean(data.get("personalidade", "")),
            restricoes=_strings(data.get("restricoes", [])),
        )


@dataclass(frozen=True)
class QuestionCandidate:
    text: str = ""
    direction: str = ""
    risk_scores: dict[str, float] = field(default_factory=dict)
    relation_score: float = 0.0
    discovery_score: float = 0.0
    answerability_score: float = 0.0
    accepted: bool = False
    issues: tuple[str, ...] = ()
    source: str = "llm"
    why_now: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "text", _clean(self.text))
        object.__setattr__(self, "direction", _clean(self.direction))
        object.__setattr__(self, "risk_scores", _dict(self.risk_scores))
        object.__setattr__(self, "issues", _strings(self.issues))
        object.__setattr__(self, "source", _clean(self.source) or "llm")
        object.__setattr__(self, "why_now", _clean(self.why_now))

    @property
    def question(self) -> str:
        return self.text

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "direction": self.direction,
            "risk_scores": dict(self.risk_scores),
            "relation_score": self.relation_score,
            "discovery_score": self.discovery_score,
            "answerability_score": self.answerability_score,
            "accepted": self.accepted,
            "issues": list(self.issues),
            "source": self.source,
            "why_now": self.why_now,
        }

    @classmethod
    def from_dict(cls, raw: object) -> "QuestionCandidate":
        data = _dict(raw)
        return cls(
            text=_clean(data.get("text", data.get("question", data.get("pergunta", "")))),
            direction=_clean(data.get("direction", data.get("direcao", ""))),
            risk_scores=_dict(data.get("risk_scores", data.get("riscos", {}))),
            relation_score=float(data.get("relation_score", data.get("relacao", 0)) or 0),
            discovery_score=float(data.get("discovery_score", data.get("descoberta", 0)) or 0),
            answerability_score=float(
                data.get("answerability_score", data.get("respondibilidade", 0)) or 0
            ),
            accepted=bool(data.get("accepted", data.get("aceita", False))),
            issues=_strings(data.get("issues", data.get("problemas", []))),
            source=_clean(data.get("source", "llm")),
            why_now=_clean(data.get("why_now", data.get("por_que_agora", ""))),
        )


@dataclass(frozen=True)
class SelectedQuestion:
    question: str = ""
    why_now: str = ""
    source: str = "llm"
    direction: str = ""
    candidate_id: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "question", _clean(self.question))
        object.__setattr__(self, "why_now", _clean(self.why_now))
        object.__setattr__(self, "source", _clean(self.source) or "llm")
        object.__setattr__(self, "direction", _clean(self.direction))
        object.__setattr__(self, "candidate_id", _clean(self.candidate_id))

    @property
    def text(self) -> str:
        return self.question

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "why_now": self.why_now,
            "source": self.source,
            "direction": self.direction,
            "candidate_id": self.candidate_id,
        }

    @classmethod
    def from_dict(cls, raw: object) -> "SelectedQuestion":
        data = _dict(raw)
        return cls(
            question=_clean(data.get("question", data.get("text", data.get("pergunta", "")))),
            why_now=_clean(data.get("why_now", data.get("por_que_agora", ""))),
            source=_clean(data.get("source", "llm")),
            direction=_clean(data.get("direction", data.get("direcao", ""))),
            candidate_id=_clean(data.get("candidate_id", data.get("id", ""))),
        )


@dataclass(frozen=True)
class UserAnswer:
    """Texto original imutavel e sua forma normalizada separada."""

    id: str = ""
    question_id: str = ""
    question: str = ""
    original: str = ""
    normalized: str = ""
    sequence: int = 0

    def __post_init__(self) -> None:
        original = self.original if isinstance(self.original, str) else str(self.original or "")
        normalized = self.normalized if isinstance(self.normalized, str) else ""
        object.__setattr__(self, "id", _clean(self.id))
        object.__setattr__(self, "question_id", _clean(self.question_id))
        object.__setattr__(self, "question", self.question if isinstance(self.question, str) else "")
        object.__setattr__(self, "original", original)
        object.__setattr__(self, "normalized", normalized or _normalise(original))
        object.__setattr__(self, "sequence", max(0, int(self.sequence or 0)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "question_id": self.question_id,
            "question": self.question,
            "original": self.original,
            "normalized": self.normalized,
            "sequence": self.sequence,
        }

    @classmethod
    def from_dict(cls, raw: object) -> "UserAnswer":
        data = _dict(raw)
        return cls(
            id=_clean(data.get("id", "")),
            question_id=_clean(data.get("question_id", data.get("pergunta_id", ""))),
            question=_clean(data.get("question", data.get("pergunta", ""))),
            original=data.get("original", data.get("resposta", ""))
            if isinstance(data.get("original", data.get("resposta", "")), str)
            else "",
            normalized=_clean(data.get("normalized", data.get("normalizada", ""))),
            sequence=int(data.get("sequence", data.get("rodada", 0)) or 0),
        )


@dataclass(frozen=True)
class Evidence:
    id: str = ""
    text: str = ""
    source_answer_id: str = ""
    signal_types: tuple[str, ...] = ()
    origin: str = "user_answer"

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _clean(self.id))
        object.__setattr__(self, "text", self.text if isinstance(self.text, str) else "")
        object.__setattr__(self, "source_answer_id", _clean(self.source_answer_id))
        object.__setattr__(self, "signal_types", _strings(self.signal_types))
        object.__setattr__(self, "origin", _clean(self.origin) or "user_answer")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text": self.text,
            "source_answer_id": self.source_answer_id,
            "signal_types": list(self.signal_types),
            "origin": self.origin,
        }

    @classmethod
    def from_dict(cls, raw: object) -> "Evidence":
        data = _dict(raw)
        return cls(
            id=_clean(data.get("id", "")),
            text=data.get("text", data.get("trecho", ""))
            if isinstance(data.get("text", data.get("trecho", "")), str)
            else "",
            source_answer_id=_clean(data.get("source_answer_id", data.get("resposta_id", ""))),
            signal_types=_strings(data.get("signal_types", data.get("types", []))),
            origin=_clean(data.get("origin", "user_answer")),
        )


@dataclass(frozen=True)
class AuthorialSignal:
    id: str = ""
    type: str = ""
    summary: str = ""
    confidence: float = 0.0
    origin: str = "user_answer"
    source_answer_id: str = ""
    evidence_ids: tuple[str, ...] = ()
    status: SignalStatus = "INFERIDO"

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _clean(self.id))
        object.__setattr__(self, "type", _clean(self.type))
        object.__setattr__(self, "summary", _clean(self.summary))
        object.__setattr__(self, "confidence", max(0.0, min(1.0, float(self.confidence or 0))))
        object.__setattr__(self, "origin", _clean(self.origin) or "user_answer")
        object.__setattr__(self, "source_answer_id", _clean(self.source_answer_id))
        object.__setattr__(self, "evidence_ids", _strings(self.evidence_ids))
        status = _clean(self.status).upper()
        object.__setattr__(
            self,
            "status",
            status if status in {"CONFIRMADO", "INFERIDO", "INCERTO", "CONFLITANTE"} else "INFERIDO",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "summary": self.summary,
            "confidence": self.confidence,
            "origin": self.origin,
            "source_answer_id": self.source_answer_id,
            "evidence_ids": list(self.evidence_ids),
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, raw: object) -> "AuthorialSignal":
        data = _dict(raw)
        return cls(
            id=_clean(data.get("id", "")),
            type=_clean(data.get("type", data.get("tipo", ""))),
            summary=_clean(data.get("summary", data.get("resumo", ""))),
            confidence=float(data.get("confidence", data.get("confianca", 0)) or 0),
            origin=_clean(data.get("origin", "user_answer")),
            source_answer_id=_clean(data.get("source_answer_id", data.get("resposta_id", ""))),
            evidence_ids=_strings(data.get("evidence_ids", data.get("evidencias", []))),
            status=_clean(data.get("status", "INFERIDO")).upper(),  # type: ignore[arg-type]
        )


@dataclass(frozen=True)
class DimensionScore:
    dimension_id: str = ""
    score: int = 0
    state: DimensionState = "NAO_OBSERVADA"
    evidence_ids: tuple[str, ...] = ()
    rules_triggered: tuple[str, ...] = ()
    rationale: str = ""
    essential: bool = True
    critical: bool = False

    @property
    def dimension(self) -> str:
        return self.dimension_id

    @property
    def id(self) -> str:
        return self.dimension_id

    def __post_init__(self) -> None:
        object.__setattr__(self, "dimension_id", _clean(self.dimension_id))
        object.__setattr__(self, "score", _clamp_score(self.score))
        state = _clean(self.state).upper()
        valid = {
            "NAO_OBSERVADA",
            "FRACA",
            "PARCIAL",
            "SUFICIENTE",
            "FORTE",
            "EXCEPCIONAL",
            "CONFLITANTE",
            "NAO_APLICAVEL",
        }
        object.__setattr__(self, "state", state if state in valid else "NAO_OBSERVADA")
        object.__setattr__(self, "evidence_ids", _strings(self.evidence_ids))
        object.__setattr__(self, "rules_triggered", _strings(self.rules_triggered))
        object.__setattr__(self, "rationale", _clean(self.rationale))

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimension_id": self.dimension_id,
            "id": self.dimension_id,
            "score": self.score,
            "state": self.state,
            "evidence_ids": list(self.evidence_ids),
            "rules_triggered": list(self.rules_triggered),
            "rationale": self.rationale,
            "essential": self.essential,
            "critical": self.critical,
        }

    @classmethod
    def from_dict(cls, raw: object) -> "DimensionScore":
        data = _dict(raw)
        return cls(
            dimension_id=_clean(data.get("dimension_id", data.get("id", data.get("dimension", "")))),
            score=_clamp_score(data.get("score", 0)),
            state=_clean(data.get("state", "NAO_OBSERVADA")).upper(),  # type: ignore[arg-type]
            evidence_ids=_strings(data.get("evidence_ids", [])),
            rules_triggered=_strings(data.get("rules_triggered", data.get("regras", []))),
            rationale=_clean(data.get("rationale", data.get("justificativa", ""))),
            essential=bool(data.get("essential", True)),
            critical=bool(data.get("critical", False)),
        )


AuthorialDimension = DimensionScore


@dataclass(frozen=True)
class DeterministicAssessment:
    dimensions: dict[str, DimensionScore] = field(default_factory=dict)
    global_score: int = 0
    vetos: tuple[str, ...] = ()
    evidence_count: int = 0
    answer_count: int = 0
    rules_triggered: tuple[str, ...] = ()

    @property
    def approved(self) -> bool:
        return not self.vetos and bool(self.evidence_count)

    @property
    def heuristic_approved(self) -> bool:
        return self.approved

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "dimensions",
            {
                str(key): value if isinstance(value, DimensionScore) else DimensionScore.from_dict(value)
                for key, value in self.dimensions.items()
            },
        )
        object.__setattr__(self, "global_score", _clamp_score(self.global_score))
        object.__setattr__(self, "vetos", _strings(self.vetos))
        object.__setattr__(self, "evidence_count", max(0, int(self.evidence_count or 0)))
        object.__setattr__(self, "answer_count", max(0, int(self.answer_count or 0)))
        object.__setattr__(self, "rules_triggered", _strings(self.rules_triggered))

    def to_dict(self) -> dict[str, Any]:
        return {
            "dimensions": {key: value.to_dict() for key, value in self.dimensions.items()},
            "global_score": self.global_score,
            "vetos": list(self.vetos),
            "evidence_count": self.evidence_count,
            "answer_count": self.answer_count,
            "rules_triggered": list(self.rules_triggered),
            "approved": self.approved,
        }

    @classmethod
    def from_dict(cls, raw: object) -> "DeterministicAssessment":
        data = _dict(raw)
        dimensions = data.get("dimensions", {})
        return cls(
            dimensions=_dict(dimensions),
            global_score=_clamp_score(data.get("global_score", data.get("score", 0))),
            vetos=_strings(data.get("vetos", [])),
            evidence_count=int(data.get("evidence_count", 0) or 0),
            answer_count=int(data.get("answer_count", 0) or 0),
            rules_triggered=_strings(data.get("rules_triggered", [])),
        )


@dataclass(frozen=True)
class LlmAssessment:
    approved: bool = False
    confidence: float = 0.0
    strengths: tuple[str, ...] = ()
    weaknesses: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    justification: str = ""
    epistemic_integrity: str = "unknown"
    parse_error: str | None = None
    source: str = "llm"

    @property
    def llm_approved(self) -> bool:
        return self.approved

    def __post_init__(self) -> None:
        object.__setattr__(self, "approved", bool(self.approved))
        object.__setattr__(self, "confidence", max(0.0, min(1.0, float(self.confidence or 0))))
        object.__setattr__(self, "strengths", _strings(self.strengths))
        object.__setattr__(self, "weaknesses", _strings(self.weaknesses))
        object.__setattr__(self, "risks", _strings(self.risks))
        object.__setattr__(self, "justification", _clean(self.justification))
        object.__setattr__(self, "epistemic_integrity", _clean(self.epistemic_integrity) or "unknown")
        object.__setattr__(self, "parse_error", _clean(self.parse_error) or None)
        object.__setattr__(self, "source", _clean(self.source) or "llm")

    def to_dict(self) -> dict[str, Any]:
        return {
            "approved": self.approved,
            "llm_approved": self.approved,
            "confidence": self.confidence,
            "strengths": list(self.strengths),
            "weaknesses": list(self.weaknesses),
            "risks": list(self.risks),
            "justification": self.justification,
            "epistemic_integrity": self.epistemic_integrity,
            "parse_error": self.parse_error,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, raw: object) -> "LlmAssessment":
        data = _dict(raw)
        return cls(
            approved=bool(data.get("approved", data.get("llm_approved", data.get("aprovou", False)))),
            confidence=float(data.get("confidence", data.get("confianca", 0)) or 0),
            strengths=_strings(data.get("strengths", data.get("forcas", []))),
            weaknesses=_strings(data.get("weaknesses", data.get("fraquezas", []))),
            risks=_strings(data.get("risks", data.get("riscos", []))),
            justification=_clean(data.get("justification", data.get("justificativa", ""))),
            epistemic_integrity=_clean(
                data.get("epistemic_integrity", data.get("integridade_epistemica", "unknown"))
            ),
            parse_error=_clean(data.get("parse_error", "")) or None,
            source=_clean(data.get("source", "llm")),
        )


@dataclass(frozen=True)
class Gap:
    type: str = ""
    dimension: str = ""
    relevance: str = "medium"
    expected_gain: str = "medium"
    critical: bool = False
    reason: str = ""
    suggested_question: str = ""

    @property
    def gap_type(self) -> str:
        return self.type

    def __post_init__(self) -> None:
        object.__setattr__(self, "type", _clean(self.type))
        object.__setattr__(self, "dimension", _clean(self.dimension))
        object.__setattr__(self, "relevance", _clean(self.relevance).lower() or "medium")
        object.__setattr__(self, "expected_gain", _clean(self.expected_gain).lower() or "medium")
        object.__setattr__(self, "critical", bool(self.critical))
        object.__setattr__(self, "reason", _clean(self.reason))
        object.__setattr__(self, "suggested_question", _clean(self.suggested_question))

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "dimension": self.dimension,
            "relevance": self.relevance,
            "expected_gain": self.expected_gain,
            "critical": self.critical,
            "reason": self.reason,
            "suggested_question": self.suggested_question,
        }

    @classmethod
    def from_dict(cls, raw: object) -> "Gap":
        data = _dict(raw)
        return cls(
            type=_clean(data.get("type", data.get("gap_type", ""))),
            dimension=_clean(data.get("dimension", "")),
            relevance=_clean(data.get("relevance", "medium")),
            expected_gain=_clean(data.get("expected_gain", "medium")),
            critical=bool(data.get("critical", False)),
            reason=_clean(data.get("reason", data.get("motivo", ""))),
            suggested_question=_clean(data.get("suggested_question", data.get("pergunta", ""))),
        )


@dataclass(frozen=True)
class DeepeningDecision:
    should_ask: bool = False
    reason: str = ""
    selected_gap: Gap | None = None
    why_now: str = ""
    marginal_gain: str = "low"
    closure_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "should_ask": self.should_ask,
            "reason": self.reason,
            "selected_gap": self.selected_gap.to_dict() if self.selected_gap else None,
            "why_now": self.why_now,
            "marginal_gain": self.marginal_gain,
            "closure_reason": self.closure_reason,
        }

    @classmethod
    def from_dict(cls, raw: object) -> "DeepeningDecision":
        data = _dict(raw)
        selected = data.get("selected_gap")
        return cls(
            should_ask=bool(data.get("should_ask", False)),
            reason=_clean(data.get("reason", "")),
            selected_gap=Gap.from_dict(selected) if isinstance(selected, dict) else None,
            why_now=_clean(data.get("why_now", "")),
            marginal_gain=_clean(data.get("marginal_gain", "low")),
            closure_reason=_clean(data.get("closure_reason", "")),
        )


@dataclass(frozen=True)
class GatewayResult:
    approved: bool = False
    gateway_type: GatewayType = "REPROVADO"
    llm_approved: bool = False
    heuristic_approved: bool = False
    balanced: bool = False
    strong_imbalanced: bool = False
    global_score: int = 0
    exceptional_dimensions: tuple[str, ...] = ()
    weak_dimensions: tuple[str, ...] = ()
    vetoes: tuple[str, ...] = ()
    relevant_gaps: tuple[Gap, ...] = ()
    justification: str = ""
    llm_confidence: float = 0.0

    @property
    def tipo_gateway(self) -> str:
        return self.gateway_type

    @property
    def gaps(self) -> tuple[Gap, ...]:
        return self.relevant_gaps

    def __post_init__(self) -> None:
        object.__setattr__(self, "approved", bool(self.approved))
        gateway_type = _clean(self.gateway_type).upper()
        aliases = {"EQUILIBRADO": "EQUILIBRADO", "DESEQUILIBRADO": "DESEQUILIBRADO_FORTE", "DESEQUILIBRADO_FORTE": "DESEQUILIBRADO_FORTE", "REPROVADO": "REPROVADO"}
        object.__setattr__(self, "gateway_type", aliases.get(gateway_type, "REPROVADO"))
        object.__setattr__(self, "llm_approved", bool(self.llm_approved))
        object.__setattr__(self, "heuristic_approved", bool(self.heuristic_approved))
        object.__setattr__(self, "balanced", bool(self.balanced))
        object.__setattr__(self, "strong_imbalanced", bool(self.strong_imbalanced))
        object.__setattr__(self, "global_score", _clamp_score(self.global_score))
        object.__setattr__(self, "exceptional_dimensions", _strings(self.exceptional_dimensions))
        object.__setattr__(self, "weak_dimensions", _strings(self.weak_dimensions))
        object.__setattr__(self, "vetoes", _strings(self.vetoes))
        object.__setattr__(self, "relevant_gaps", tuple(g if isinstance(g, Gap) else Gap.from_dict(g) for g in self.relevant_gaps))
        object.__setattr__(self, "justification", _clean(self.justification))
        object.__setattr__(self, "llm_confidence", max(0.0, min(1.0, float(self.llm_confidence or 0))))

    def to_dict(self) -> dict[str, Any]:
        return {
            "approved": self.approved,
            "gateway_type": self.gateway_type,
            "tipo_gateway": self.gateway_type,
            "llm_approved": self.llm_approved,
            "heuristic_approved": self.heuristic_approved,
            "balanced": self.balanced,
            "strong_imbalanced": self.strong_imbalanced,
            "global_score": self.global_score,
            "exceptional_dimensions": list(self.exceptional_dimensions),
            "weak_dimensions": list(self.weak_dimensions),
            "vetoes": list(self.vetoes),
            "relevant_gaps": [gap.to_dict() for gap in self.relevant_gaps],
            "justification": self.justification,
            "llm_confidence": self.llm_confidence,
        }

    @classmethod
    def from_dict(cls, raw: object) -> "GatewayResult":
        data = _dict(raw)
        gaps = data.get("relevant_gaps", data.get("gaps", []))
        return cls(
            approved=bool(data.get("approved", data.get("aprovado", False))),
            gateway_type=_clean(
                data.get("gateway_type", data.get("tipo_gateway", "REPROVADO"))
            ).upper(),  # type: ignore[arg-type]
            llm_approved=bool(data.get("llm_approved", data.get("llm_aprovou", False))),
            heuristic_approved=bool(data.get("heuristic_approved", data.get("heuristica_aprovou", False))),
            balanced=bool(data.get("balanced", data.get("gateway_equilibrado", False))),
            strong_imbalanced=bool(data.get("strong_imbalanced", data.get("gateway_desequilibrado_forte", False))),
            global_score=_clamp_score(data.get("global_score", 0)),
            exceptional_dimensions=_strings(data.get("exceptional_dimensions", data.get("dimensoes_excepcionais", []))),
            weak_dimensions=_strings(data.get("weak_dimensions", data.get("dimensoes_fracas", []))),
            vetoes=_strings(data.get("vetoes", data.get("vetos", []))),
            relevant_gaps=tuple(Gap.from_dict(item) for item in gaps if isinstance(item, dict)),
            justification=_clean(data.get("justification", data.get("justificativa", ""))),
            llm_confidence=float(data.get("llm_confidence", data.get("confianca", 0)) or 0),
        )


@dataclass
class InterviewState:
    schema_version: str = SESSION_SCHEMA_VERSION
    context: ThemeContext = field(default_factory=lambda: ThemeContext(""))
    progress_state: ProgressState = "EXPLORANDO"
    question_count: int = 0
    max_questions: int = 12
    questions: list[SelectedQuestion] = field(default_factory=list)
    candidates: list[QuestionCandidate] = field(default_factory=list)
    answers: list[UserAnswer] = field(default_factory=list)
    evidence_ledger: list[Evidence] = field(default_factory=list)
    signals: list[AuthorialSignal] = field(default_factory=list)
    dimensions: dict[str, DimensionScore] = field(default_factory=dict)
    deterministic_assessment: DeterministicAssessment | None = None
    llm_assessment: LlmAssessment | None = None
    gateway_result: GatewayResult | None = None
    gaps: list[Gap] = field(default_factory=list)
    deepening_decision: DeepeningDecision | None = None
    current_question: SelectedQuestion | None = None
    closure_reason: str = ""
    round_title: str = ""
    round_titles: dict[int, str] = field(default_factory=dict)
    extension_batches_completed: int = 0
    pending_batch: list[SelectedQuestion] = field(default_factory=list)
    pending_answers: dict[str, str] = field(default_factory=dict)
    gap_diagnosis: str = ""

    @property
    def theme(self) -> ThemeContext:
        return self.context

    @property
    def original_answers(self) -> tuple[str, ...]:
        return tuple(answer.original for answer in self.answers)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "context": self.context.to_dict(),
            "progress_state": self.progress_state,
            "question_count": self.question_count,
            "max_questions": self.max_questions,
            "questions": [item.to_dict() for item in self.questions],
            "candidates": [item.to_dict() for item in self.candidates],
            "answers": [item.to_dict() for item in self.answers],
            "evidence_ledger": [item.to_dict() for item in self.evidence_ledger],
            "signals": [item.to_dict() for item in self.signals],
            "dimensions": {key: value.to_dict() for key, value in self.dimensions.items()},
            "deterministic_assessment": self.deterministic_assessment.to_dict()
            if self.deterministic_assessment
            else None,
            "llm_assessment": self.llm_assessment.to_dict() if self.llm_assessment else None,
            "gateway_result": self.gateway_result.to_dict() if self.gateway_result else None,
            "gaps": [item.to_dict() for item in self.gaps],
            "deepening_decision": self.deepening_decision.to_dict()
            if self.deepening_decision
            else None,
            "current_question": self.current_question.to_dict() if self.current_question else None,
            "closure_reason": self.closure_reason,
            "round_title": self.round_title,
            "round_titles": self.round_titles,
            "extension_batches_completed": self.extension_batches_completed,
            "pending_batch": [item.to_dict() for item in self.pending_batch],
            "pending_answers": dict(self.pending_answers),
            "gap_diagnosis": self.gap_diagnosis,
        }

    @classmethod
    def from_dict(cls, raw: object) -> "InterviewState":
        data = _dict(raw)
        context = ThemeContext.from_dict(data.get("context", {}))
        dimensions_raw = data.get("dimensions", {})
        pending_answers_raw = data.get("pending_answers", {})
        return cls(
            schema_version=_clean(data.get("schema_version", SESSION_SCHEMA_VERSION)),
            context=context,
            progress_state=_clean(data.get("progress_state", "EXPLORANDO")).upper(),  # type: ignore[arg-type]
            question_count=max(0, int(data.get("question_count", 0) or 0)),
            max_questions=max(1, int(data.get("max_questions", 12) or 12)),
            questions=[SelectedQuestion.from_dict(item) for item in data.get("questions", []) if isinstance(item, dict)],
            candidates=[QuestionCandidate.from_dict(item) for item in data.get("candidates", []) if isinstance(item, dict)],
            answers=[UserAnswer.from_dict(item) for item in data.get("answers", []) if isinstance(item, dict)],
            evidence_ledger=[Evidence.from_dict(item) for item in data.get("evidence_ledger", []) if isinstance(item, dict)],
            signals=[AuthorialSignal.from_dict(item) for item in data.get("signals", []) if isinstance(item, dict)],
            dimensions={
                str(key): DimensionScore.from_dict(value)
                for key, value in _dict(dimensions_raw).items()
                if isinstance(value, dict)
            },
            deterministic_assessment=DeterministicAssessment.from_dict(data["deterministic_assessment"])
            if isinstance(data.get("deterministic_assessment"), dict)
            else None,
            llm_assessment=LlmAssessment.from_dict(data["llm_assessment"])
            if isinstance(data.get("llm_assessment"), dict)
            else None,
            gateway_result=GatewayResult.from_dict(data["gateway_result"])
            if isinstance(data.get("gateway_result"), dict)
            else None,
            gaps=[Gap.from_dict(item) for item in data.get("gaps", []) if isinstance(item, dict)],
            deepening_decision=DeepeningDecision.from_dict(data["deepening_decision"])
            if isinstance(data.get("deepening_decision"), dict)
            else None,
            current_question=SelectedQuestion.from_dict(data["current_question"])
            if isinstance(data.get("current_question"), dict)
            else None,
            closure_reason=_clean(data.get("closure_reason", "")),
            round_title=_clean(data.get("round_title", "")),
            round_titles={int(k): _clean(v) for k, v in _dict(data.get("round_titles", {})).items()},
            extension_batches_completed=max(0, int(data.get("extension_batches_completed", 0) or 0)),
            pending_batch=[
                SelectedQuestion.from_dict(item)
                for item in data.get("pending_batch", [])
                if isinstance(item, dict)
            ],
            pending_answers={
                str(key): _clean(value)
                for key, value in _dict(pending_answers_raw).items()
            },
            gap_diagnosis=_clean(data.get("gap_diagnosis", "")),
        )


InterviewV4Session = InterviewState


def criar_estado_inicial(
    tema: str,
    *,
    objetivo: str = "",
    formato: str = "post",
    personalidade: str = "",
    restricoes: list[str] | tuple[str, ...] = (),
    max_questions: int = 12,
) -> InterviewState:
    if not _clean(tema):
        raise ValueError("tema e obrigatorio para iniciar a entrevista")
    return InterviewState(
        context=ThemeContext(
            tema=tema,
            objetivo=objetivo,
            formato=formato,
            personalidade=personalidade,
            restricoes=tuple(restricoes),
        ),
        max_questions=max(1, int(max_questions)),
    )


create_initial_state = criar_estado_inicial


__all__ = [
    "SESSION_SCHEMA_VERSION",
    "ProgressState",
    "DimensionState",
    "SignalStatus",
    "GatewayType",
    "ThemeContext",
    "QuestionCandidate",
    "SelectedQuestion",
    "UserAnswer",
    "Evidence",
    "AuthorialSignal",
    "DimensionScore",
    "AuthorialDimension",
    "DeterministicAssessment",
    "LlmAssessment",
    "Gap",
    "DeepeningDecision",
    "GatewayResult",
    "InterviewState",
    "InterviewV4Session",
    "criar_estado_inicial",
    "create_initial_state",
]
