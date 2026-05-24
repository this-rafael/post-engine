"""Testes do ajuste em lote de segmentos."""
from __future__ import annotations

import json

import pytest

from content_engine.adjust_segments_bulk import (
    SegmentAdjustRequest,
    SegmentBulkAdjuster,
    trecho_to_segment_index,
)
from content_engine.prompt_loader import load_prompt
from content_engine.schemas import SegmentoPost
from tests.llm_fakes import AgentFakeRunMixin


class FakeAgent(AgentFakeRunMixin):
    def __init__(self, stdout: str = "", *, returncode: int = 0, error: str | None = None) -> None:
        self.stdout = stdout
        self.returncode = returncode
        self.error = error

    def run(self, *args: object, **kwargs: object) -> object:
        from content_engine.schemas import AgentResult

        return AgentResult(
            tool="codex",
            command=["codex"],
            returncode=self.returncode,
            stdout=self.stdout,
            stderr="",
            error=self.error,
        )


def test_trecho_to_segment_index_one_based() -> None:
    assert trecho_to_segment_index(2, 5) == 1
    assert trecho_to_segment_index(5, 5) == 4


def test_trecho_to_segment_index_zero_based() -> None:
    assert trecho_to_segment_index(0, 5) == 0


def test_trecho_to_segment_index_invalid() -> None:
    assert trecho_to_segment_index(9, 5) is None
    assert trecho_to_segment_index(-1, 5) is None
    assert trecho_to_segment_index(1, 0) is None


def test_bulk_adjuster_returns_all_segments() -> None:
    payload = {
        "segmentosReescritos": [
            {"id": "seg-1", "ordem": 1, "segmentoReescrito": "texto um"},
            {"id": "seg-2", "ordem": 2, "segmentoReescrito": "texto dois"},
        ]
    }
    agent = FakeAgent(stdout=json.dumps(payload))
    adjuster = SegmentBulkAdjuster(agent, "codex")
    requests = [
        SegmentAdjustRequest(
            segmento=SegmentoPost(id="seg-1", ordem=1, texto="a", papel_interno="p"),
            pedido="melhore",
            problema="fraco",
            motivo="detalhar",
        ),
        SegmentAdjustRequest(
            segmento=SegmentoPost(id="seg-2", ordem=2, texto="b", papel_interno="p"),
            pedido="concretize",
        ),
    ]
    result = adjuster.ajustar("conteudo completo", requests)
    assert result == {"seg-1": "texto um", "seg-2": "texto dois"}


def test_bulk_adjuster_raises_on_incomplete_response() -> None:
    payload = {
        "segmentosReescritos": [
            {"id": "seg-1", "ordem": 1, "segmentoReescrito": "texto um"},
        ]
    }
    agent = FakeAgent(stdout=json.dumps(payload))
    adjuster = SegmentBulkAdjuster(agent, "codex")
    requests = [
        SegmentAdjustRequest(
            segmento=SegmentoPost(id="seg-1", ordem=1, texto="a", papel_interno="p"),
            pedido="melhore",
        ),
        SegmentAdjustRequest(
            segmento=SegmentoPost(id="seg-2", ordem=2, texto="b", papel_interno="p"),
            pedido="concretize",
        ),
    ]
    with pytest.raises(ValueError, match="incompleta"):
        adjuster.ajustar("conteudo completo", requests)


def test_load_prompt_adjust_segments_bulk_contem_placeholders() -> None:
    template = load_prompt("generator.adjust_segments_bulk")
    for placeholder in (
        "{{conteudoCompleto}}",
        "{{segmentosParaAjustar}}",
        "{{personalidade}}",
        "{{restricoesDeGeracao}}",
    ):
        assert placeholder in template, f"placeholder ausente: {placeholder}"
