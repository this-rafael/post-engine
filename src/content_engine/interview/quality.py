"""Small, deterministic quality metrics for the V4 interview corpus."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable

from .schemas import UserAnswer


_STOPWORDS = {
    "a", "as", "o", "os", "e", "de", "do", "da", "dos", "das", "em", "no",
    "na", "nos", "nas", "um", "uma", "que", "qual", "como", "voce", "você",
    "se", "por", "para", "com", "ou", "isso", "essa", "esse", "sobre",
}
_WORD_RE = re.compile(r"[a-zA-ZÀ-ÿ0-9]{3,}")


@dataclass(frozen=True)
class QualityMetric:
    name: str
    numerator: int
    denominator: int

    @property
    def rate(self) -> float:
        return self.numerator / self.denominator if self.denominator else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "numerator": self.numerator,
            "denominator": self.denominator,
            "rate": round(self.rate, 4),
        }


def _record(item: object) -> dict[str, Any]:
    if isinstance(item, UserAnswer):
        return item.to_dict()
    if isinstance(item, dict):
        return item
    return {}


def _words(value: object) -> set[str]:
    return {
        word.casefold()
        for word in _WORD_RE.findall(str(value or ""))
        if word.casefold() not in _STOPWORDS
    }


def _is_induced(question: str, answer: str) -> bool:
    question_words = _words(question)
    answer_words = _words(answer)
    if not question_words or not answer_words:
        return False
    overlap = len(question_words & answer_words) / len(question_words)
    return overlap >= 0.7 and len(answer_words) <= max(8, len(question_words) + 3)


def measure_induced_answer_rate(items: Iterable[UserAnswer | dict[str, Any]]) -> QualityMetric:
    rows = [_record(item) for item in items]
    rows = [row for row in rows if row.get("question") and row.get("original", row.get("answer"))]
    induced = sum(
        _is_induced(str(row.get("question", "")), str(row.get("original", row.get("answer", ""))))
        for row in rows
    )
    return QualityMetric("induced_answer_rate", induced, len(rows))


def measure_original_language_preservation(
    items: Iterable[UserAnswer | dict[str, Any]],
) -> QualityMetric:
    rows = [_record(item) for item in items]
    rows = [row for row in rows if str(row.get("original", "")).strip()]
    preserved = sum(
        bool(str(row.get("original", "")).strip())
        and str(row.get("original", "")) == str(row.get("original_answer", row.get("original", "")))
        for row in rows
    )
    return QualityMetric("original_language_preservation", preserved, len(rows))


def evaluate_corpus(items: Iterable[UserAnswer | dict[str, Any]]) -> dict[str, dict[str, Any]]:
    rows = list(items)
    return {
        "induced_answer_rate": measure_induced_answer_rate(rows).to_dict(),
        "original_language_preservation": measure_original_language_preservation(rows).to_dict(),
    }


# Short aliases make the metrics convenient in notebooks and scripts.
induced_answer_rate = measure_induced_answer_rate
original_language_preservation = measure_original_language_preservation


__all__ = [
    "QualityMetric",
    "evaluate_corpus",
    "induced_answer_rate",
    "measure_induced_answer_rate",
    "measure_original_language_preservation",
    "original_language_preservation",
]
