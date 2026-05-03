from __future__ import annotations

import pytest

from content_engine.prompt_builder import build_generation_prompt
from content_engine.schemas import GenerationPromptInput


@pytest.mark.parametrize("tipo_de_post", ["post", "article", "short_carousel", "long_slide"])
def test_generation_prompt_uses_only_v4_authorial_context(tipo_de_post: str) -> None:
    prompt = build_generation_prompt(
        GenerationPromptInput(
            tema="decisoes de arquitetura",
            plataforma="linkedin",
            objetivo_do_post="explicar um criterio pratico",
            tipo_de_post=tipo_de_post,  # type: ignore[arg-type]
            briefing_autoral={"schema_version": "4.0", "objective": "explicar"},
            interview_context={
                "schema_version": "4.0",
                "evidence_ledger": [{"id": "ev-1", "text": "O deploy travou quando a fila cresceu."}],
                "signals": [{"type": "experiencia", "summary": "caso situado"}],
                "dimensions": {"experiencia_situada": {"score": 80}},
                "gaps": [],
            },
            gateway_result={"approved": True, "justification": "Material suficiente."},
        )
    )

    assert "O deploy travou quando a fila cresceu." in prompt
    assert "Material suficiente." in prompt
    assert "Contexto da entrevista V4" in prompt
    assert "Interview Pack" not in prompt
