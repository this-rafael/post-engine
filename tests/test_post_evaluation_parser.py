"""Testes do parser de avaliacao short_carousel (SlideMark)."""
from __future__ import annotations

import json

from content_engine.post_evaluation import PostEvaluator, _coerce_severidade
from content_engine.schemas import AvaliacaoSlideMark, ScoreDoPost
from tests.llm_fakes import AgentFakeRunMixin


class FakeAgent(AgentFakeRunMixin):
    def __init__(self, stdout: str = "") -> None:
        self.stdout = stdout

    def run(self, *args: object, **kwargs: object) -> object:
        from content_engine.schemas import AgentResult

        return AgentResult(
            tool="codex",
            command=["codex"],
            returncode=0,
            stdout=self.stdout,
            stderr="",
        )


def _payload_completo() -> dict[str, object]:
    return {
        "score": {
            "tese": 8,
            "progressao": 7,
            "concretude": 6,
            "precisaoTecnica": 7,
            "retencao": 6,
            "autoridade": 7,
            "autoria": 8,
            "slidemark": 9,
            "revisaoTextual": 8,
            "total": 99,
        },
        "veredito": "Bom carrossel.",
        "pontosFortes": ["clareza"],
        "pontosFracos": ["slide 4 fraco"],
        "trechosFracos": [
            {
                "trecho": 4,
                "problema": "Redundante",
                "severidade": "alta",
                "motivo": "Repete conclusao",
            }
        ],
        "redundancias": ["slides 2 e 3"],
        "falhasTecnicas": ["metrica ausente"],
        "sugestoesDeMelhoria": ["adicionar exemplo"],
    }


def test_parse_payload_com_todos_os_campos_novos() -> None:
    agent = FakeAgent(stdout=json.dumps(_payload_completo()))
    avaliacao = PostEvaluator(agent, "codex").avaliar(
        "tema", "conteudo", {}, tipo_de_post="short_carousel"
    )
    assert isinstance(avaliacao, AvaliacaoSlideMark)
    assert avaliacao.score.tese == 8
    assert avaliacao.veredito == "Bom carrossel."
    assert avaliacao.trechos_fracos[0].severidade == "alta"
    assert avaliacao.redundancias == ["slides 2 e 3"]
    assert avaliacao.falhas_tecnicas == ["metrica ausente"]


def test_coerce_severidade_invalida_para_media() -> None:
    assert _coerce_severidade("ALTA") == "alta"
    assert _coerce_severidade("critica") == "media"
    assert _coerce_severidade(None) == "media"


def test_total_ponderado_ignora_total_da_llm() -> None:
    payload = _payload_completo()
    payload["score"] = {
        "tese": 6,
        "progressao": 6,
        "concretude": 6,
        "precisaoTecnica": 6,
        "retencao": 6,
        "autoridade": 6,
        "autoria": 6,
        "slidemark": 6,
        "revisaoTextual": 6,
        "total": 99,
    }
    agent = FakeAgent(stdout=json.dumps(payload))
    avaliacao = PostEvaluator(agent, "codex").avaliar(
        "tema", "conteudo", {}, tipo_de_post="short_carousel"
    )
    assert avaliacao.score.total == 6.0


def test_total_cap_quando_tese_alta_e_progressao_baixa() -> None:
    score = ScoreDoPost(
        tese=9,
        progressao=3,
        concretude=10,
        precisao_tecnica=10,
        retencao=10,
        autoridade=10,
        autoria=10,
        slidemark=10,
        revisao_textual=10,
    )
    assert score.total == 7.0


def test_campos_faltantes_viram_vazios_sem_excecao() -> None:
    agent = FakeAgent(stdout=json.dumps({"score": {}}))
    avaliacao = PostEvaluator(agent, "codex").avaliar(
        "tema", "conteudo", {}, tipo_de_post="short_carousel"
    )
    assert avaliacao.score.tese == 0
    assert avaliacao.veredito == ""
    assert avaliacao.trechos_fracos == []
    assert avaliacao.redundancias == []
    assert avaliacao.falhas_tecnicas == []
