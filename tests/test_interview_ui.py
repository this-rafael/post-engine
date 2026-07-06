from __future__ import annotations

from content_engine.interview.schemas import (
    AuthorialSignal,
    DimensionScore,
    Evidence,
    InterviewState,
    ThemeContext,
)
from content_engine.interview.ui import build_interview_ui


def test_v4_ui_exposes_the_same_flat_dimensions_for_chart_and_list() -> None:
    state = InterviewState(
        context=ThemeContext("observabilidade", formato="post"),
        evidence_ledger=[Evidence(id="ev-1", text="Uma fila cresceu", origin="autor")],
        signals=[
            AuthorialSignal(
                type="experiencia_vivida",
                summary="Uma fila cresceu",
                confidence=0.9,
                origin="autor",
                evidence_ids=("ev-1",),
            )
        ],
        dimensions={
            "experiencia_vivida": DimensionScore(
                dimension_id="experiencia_vivida",
                score=70,
                state="FORTE",
                evidence_ids=("ev-1",),
                critical=True,
            )
        },
    )

    ui = build_interview_ui(state)
    dimension_ids = [item["id"] for item in ui["dimensions"]]
    chart_ids = [item["id"] for item in ui["chart_series"]]

    assert len(dimension_ids) == 9
    assert chart_ids == dimension_ids
    assert "groups" not in ui
    assert ui["dimensions"][0]["evidence"][0]["id"] == "ev-1"


def test_FR_016_counter_uses_the_dimension_collection() -> None:
    ui = build_interview_ui(InterviewState(context=ThemeContext("tema")))

    assert ui["counter"]["total"] == len(ui["dimensions"])
    assert ui["counter"]["observed"] == sum(item["covered"] for item in ui["dimensions"])


def test_FR_017_chart_and_list_ids_are_identical() -> None:
    ui = build_interview_ui(InterviewState(context=ThemeContext("tema")))

    assert [item["id"] for item in ui["chart_series"]] == [
        item["id"] for item in ui["dimensions"]
    ]


def test_FR_018_dimension_contains_explanation_fields() -> None:
    state = InterviewState(
        context=ThemeContext("tema"),
        dimensions={
            "concretude": DimensionScore(
                dimension_id="concretude",
                score=30,
                state="PARCIAL",
                rules_triggered=("MINIMUM_DETAIL",),
                rationale="Falta um caso observavel.",
            )
        },
    )

    item = next(item for item in build_interview_ui(state)["dimensions"] if item["id"] == "concretude")
    assert item["rules_triggered"] == ["MINIMUM_DETAIL"]
    assert item["rationale"] == "Falta um caso observavel."
