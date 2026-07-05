from __future__ import annotations

import json
from pathlib import Path

from content_engine.interview.quality import (
    evaluate_corpus,
    measure_induced_answer_rate,
    measure_original_language_preservation,
)


def _corpus() -> list[dict[str, object]]:
    path = Path(__file__).parent / "fixtures" / "interview_corpus" / "corpus.json"
    return json.loads(path.read_text(encoding="utf-8"))["cases"]


def test_v4_quality_metrics_are_deterministic() -> None:
    cases = _corpus()
    induced = measure_induced_answer_rate(cases)
    preserved = measure_original_language_preservation(cases)

    assert induced.denominator == 8
    assert induced.numerator == 1
    assert preserved.denominator == 8
    assert preserved.numerator == 8


def test_v4_quality_report_contains_named_metrics() -> None:
    report = evaluate_corpus(_corpus())

    assert set(report) == {"induced_answer_rate", "original_language_preservation"}
    assert report["induced_answer_rate"]["rate"] == 0.125


def test_FR_019_induced_answer_rate_is_reported() -> None:
    assert measure_induced_answer_rate(_corpus()).name == "induced_answer_rate"


def test_FR_020_original_language_preservation_is_reported() -> None:
    assert measure_original_language_preservation(_corpus()).rate == 1.0
