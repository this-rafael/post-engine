"""Testes do prompt de avaliacao short_carousel."""
from __future__ import annotations

from content_engine.prompt_loader import load_prompt, prompt_exists


def test_prompt_short_carousel_existe() -> None:
    assert prompt_exists("generator.evaluate_post_short_carousel")


def test_prompt_short_carousel_contem_secoes_obrigatorias() -> None:
    template = load_prompt("generator.evaluate_post_short_carousel")
    for secao in ("AVALIE A TESE", "AVALIE A PROGRESSÃO", "SCORE"):
        assert secao in template, f"secao ausente: {secao}"
