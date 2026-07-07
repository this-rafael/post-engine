"""Testes de SPEC-030..037: segmentacao, ajuste, avaliacao e exportacao."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from content_engine.adjust_segment import SegmentAdjuster
from content_engine.exporter import (
    exportar_conteudo,
    exportar_markdown,
    exportar_txt,
    nome_arquivo_base,
    sanitizar_nome_arquivo,
)
from content_engine.post_evaluation import PostEvaluator
from content_engine.prompt_loader import load_prompt
from content_engine.schemas import AgentResult, AvaliacaoSlideMark, SegmentoPost
from content_engine.segmentation import Segmenter, parse_segmentos
from tests.llm_fakes import AgentFakeRunMixin


class FakeAgent(AgentFakeRunMixin):
    def __init__(self, stdout: str = "", returncode: int = 0, error: str | None = None) -> None:
        self.stdout: str = stdout
        self.returncode: int = returncode
        self.error: str | None = error
        self.calls: list[dict[str, Any]] = []

    def run_codex(
        self,
        prompt: str,
        *,
        model: str | None = None,
        reasoning_effort: str | None = None,
        sandbox: str = "read-only",
        json_output: bool = False,
        extra_context: str | None = None,
        ephemeral: bool = True,
        ignore_user_config: bool = False,
        runner: Any = None,
    ) -> AgentResult:
        del reasoning_effort
        self.calls.append(
            {
                "prompt": prompt,
                "model": model,
                "sandbox": sandbox,
                "json_output": json_output,
            }
        )
        return AgentResult(
            tool="codex",
            command=["codex", "exec"],
            returncode=self.returncode,
            stdout=self.stdout,
            stderr="",
            events=None,
            error=self.error,
        )

    def run_opencode(
        self,
        prompt: str,
        *,
        model: str | None = None,
        agent: str | None = None,
        files: list[Any] | None = None,
        json_output: bool = False,
        attach_url: str | None = None,
        dangerously_skip_permissions: bool = False,
        runner: Any = None,
    ) -> AgentResult:
        self.calls.append(
            {
                "prompt": prompt,
                "model": model,
                "json_output": json_output,
            }
        )
        return AgentResult(
            tool="opencode",
            command=["opencode", "run"],
            returncode=self.returncode,
            stdout=self.stdout,
            stderr="",
            events=None,
            error=self.error,
        )


def _payload_segmentos_valido() -> dict[str, Any]:
    return {
        "segmentos": [
            {
                "id": "seg_1",
                "ordem": 1,
                "papelInterno": "abertura",
                "texto": "Primeiro parágrafo.",
            },
            {
                "id": "seg_2",
                "ordem": 2,
                "papel_interno": "argumento",
                "texto": "Segundo parágrafo.",
            },
            {
                "id": "seg_3",
                "ordem": 3,
                "texto": "Terceiro parágrafo.",
            },
        ]
    }


def test_spec_030_parse_segmentos_valido_retorna_lista() -> None:
    resultado = parse_segmentos(_payload_segmentos_valido())
    assert isinstance(resultado, list)
    assert len(resultado) == 3
    assert all(isinstance(s, SegmentoPost) for s in resultado)
    assert resultado[0].id == "seg_1"
    assert resultado[0].ordem == 1
    assert resultado[0].texto == "Primeiro parágrafo."
    assert resultado[0].papel_interno == "abertura"
    assert resultado[1].papel_interno == "argumento"
    assert resultado[2].papel_interno == ""


def test_spec_030_parse_segmentos_aceita_id_ordem_texto_ausentes_com_erro() -> None:
    payload = {
        "segmentos": [
            {"id": "seg_1", "ordem": 1},
        ]
    }
    with pytest.raises(ValueError):
        parse_segmentos(payload)


def test_spec_030_parse_segmentos_ids_duplicados_levanta_value_error() -> None:
    payload = {
        "segmentos": [
            {"id": "seg_1", "ordem": 1, "texto": "a"},
            {"id": "seg_1", "ordem": 2, "texto": "b"},
        ]
    }
    with pytest.raises(ValueError) as excinfo:
        parse_segmentos(payload)
    msg = str(excinfo.value).lower()
    assert "ids" in msg or "unicos" in msg


def test_spec_030_parse_segmentos_ordem_nao_sequencial_levanta_value_error() -> None:
    payload = {
        "segmentos": [
            {"id": "seg_1", "ordem": 1, "texto": "a"},
            {"id": "seg_2", "ordem": 3, "texto": "b"},
        ]
    }
    with pytest.raises(ValueError) as excinfo:
        parse_segmentos(payload)
    assert "ordem" in str(excinfo.value).lower()


def test_spec_030_parse_segmentos_segmentos_nao_lista_levanta_value_error() -> None:
    with pytest.raises(ValueError):
        parse_segmentos({"segmentos": "nope"})


def test_spec_030_parse_segmentos_item_nao_dict_levanta_value_error() -> None:
    with pytest.raises(ValueError):
        parse_segmentos({"segmentos": ["string aqui"]})


def test_spec_030_parse_segmentos_ordem_zero_levanta_value_error() -> None:
    payload = {
        "segmentos": [
            {"id": "seg_1", "ordem": 0, "texto": "a"},
        ]
    }
    with pytest.raises(ValueError):
        parse_segmentos(payload)


def test_spec_030_segmenter_segmentar_retorna_lista_segmentos() -> None:
    agent = FakeAgent(stdout=json.dumps(_payload_segmentos_valido()))
    segmenter = Segmenter(agent, "codex")
    resultado = segmenter.segmentar("conteudo base do post")
    assert len(resultado) == 3
    assert resultado[0].id == "seg_1"
    assert agent.calls, "agent deve ter sido chamado"
    call = agent.calls[0]
    assert call["json_output"] is True
    assert "conteudo base do post" in call["prompt"]


def test_spec_030_segmenter_segmentar_erro_do_agent_levanta_runtime_error() -> None:
    agent = FakeAgent(stdout="", returncode=0, error="cli indisponivel")
    segmenter = Segmenter(agent, "codex")
    with pytest.raises(RuntimeError) as excinfo:
        segmenter.segmentar("x")
    assert "cli indisponivel" in str(excinfo.value)


def test_spec_030_segmenter_segmentar_json_invalido_levanta_value_error() -> None:
    agent = FakeAgent(stdout="nao e json nenhum")
    segmenter = Segmenter(agent, "codex")
    with pytest.raises(ValueError) as excinfo:
        segmenter.segmentar("x")
    assert "JSON invalido" in str(excinfo.value)


def test_spec_030_segmenter_com_opencode() -> None:
    agent = FakeAgent(stdout=json.dumps(_payload_segmentos_valido()))
    segmenter = Segmenter(agent, "opencode", model="m-x")
    resultado = segmenter.segmentar("conteudo")
    assert len(resultado) == 3
    assert agent.calls[0]["json_output"] is True


def test_spec_031_load_prompt_generator_segment_contem_placeholder() -> None:
    template = load_prompt("generator.segment")
    assert template.strip() != ""
    assert "{{conteudoDoPost}}" in template


def test_spec_032_segment_adjuster_ajustar_retorna_string_reescrita() -> None:
    segmento = SegmentoPost(
        id="seg_2", ordem=2, texto="texto original", papel_interno="argumento"
    )
    payload = {"segmentoReescrito": "texto novo e melhor"}
    agent = FakeAgent(stdout=json.dumps(payload))
    adjuster = SegmentAdjuster(agent, "codex")
    resultado = adjuster.ajustar(
        conteudo_completo="conteudo do post inteiro",
        segmento=segmento,
        pedido="deixe mais curto",
    )
    assert resultado == "texto novo e melhor"
    assert agent.calls[0]["json_output"] is True
    assert "conteudo do post inteiro" in agent.calls[0]["prompt"]


def test_spec_032_segment_adjuster_segmento_none_levanta_value_error() -> None:
    agent = FakeAgent()
    adjuster = SegmentAdjuster(agent, "codex")
    with pytest.raises(ValueError):
        adjuster.ajustar("conteudo", None, "pedido")


def test_spec_032_segment_adjuster_segmento_invalido_sem_id_levanta_value_error() -> None:
    invalido = SegmentoPost(id="", ordem=1, texto="x", papel_interno="")
    agent = FakeAgent()
    adjuster = SegmentAdjuster(agent, "codex")
    with pytest.raises(ValueError):
        adjuster.ajustar("conteudo", invalido, "pedido")


def test_spec_032_segment_adjuster_segmento_texto_vazio_levanta_value_error() -> None:
    invalido = SegmentoPost(id="s", ordem=1, texto="", papel_interno="")
    agent = FakeAgent()
    adjuster = SegmentAdjuster(agent, "codex")
    with pytest.raises(ValueError):
        adjuster.ajustar("conteudo", invalido, "pedido")


def test_spec_032_segment_adjuster_erro_agent_levanta_runtime_error() -> None:
    segmento = SegmentoPost(id="s", ordem=1, texto="x", papel_interno="")
    agent = FakeAgent(stdout="", returncode=0, error="kaboom")
    adjuster = SegmentAdjuster(agent, "codex")
    with pytest.raises(RuntimeError) as excinfo:
        adjuster.ajustar("c", segmento, "p")
    assert "kaboom" in str(excinfo.value)


def test_spec_032_segment_adjuster_json_invalido_levanta_value_error() -> None:
    segmento = SegmentoPost(id="s", ordem=1, texto="x", papel_interno="")
    agent = FakeAgent(stdout="sem json")
    adjuster = SegmentAdjuster(agent, "codex")
    with pytest.raises(ValueError):
        adjuster.ajustar("c", segmento, "p")


def test_spec_032_segment_adjuster_payload_sem_segmento_reescrito_levanta_value_error() -> None:
    segmento = SegmentoPost(id="s", ordem=1, texto="x", papel_interno="")
    agent = FakeAgent(stdout=json.dumps({"outra": "chave"}))
    adjuster = SegmentAdjuster(agent, "codex")
    with pytest.raises(ValueError):
        adjuster.ajustar("c", segmento, "p")


def test_spec_032_segment_adjuster_retorna_apenas_segmento_reescrito_nao_conteudo() -> None:
    segmento = SegmentoPost(id="s", ordem=1, texto="x", papel_interno="")
    payload = {"segmentoReescrito": "so o segmento"}
    agent = FakeAgent(stdout=json.dumps(payload))
    adjuster = SegmentAdjuster(agent, "codex")
    resultado = adjuster.ajustar("todo o post", segmento, "ajuste")
    assert resultado == "so o segmento"
    assert "todo o post" not in resultado


def test_spec_033_load_prompt_adjust_segment_contem_placeholders() -> None:
    template = load_prompt("generator.adjust_segment")
    for placeholder in (
        "{{conteudoCompleto}}",
        "{{segmentoAtual}}",
        "{{ajusteDoUsuario}}",
        "{{personalidade}}",
        "{{restricoesDeGeracao}}",
    ):
        assert placeholder in template, f"placeholder ausente: {placeholder}"


def _payload_avaliacao_short_carousel(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
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
        },
        "veredito": "Publicavel com ajustes menores.",
        "pontosFortes": ["forte 1", "forte 2"],
        "pontosFracos": ["fraco 1"],
        "trechosFracos": [
            {
                "trecho": 3,
                "problema": "Redundante",
                "severidade": "media",
                "motivo": "Repete a tese",
            }
        ],
        "redundancias": ["slide 2 e 3"],
        "falhasTecnicas": ["comparacao antes/depois incompleta"],
        "sugestoesDeMelhoria": ["sug 1", "sug 2"],
    }
    base.update(overrides)
    return base


def test_spec_034_post_evaluator_avaliar_retorna_score_e_listas() -> None:
    payload = _payload_avaliacao_short_carousel()
    agent = FakeAgent(stdout=json.dumps(payload))
    evaluator = PostEvaluator(agent, "codex")
    briefing = {"tema": "tema x", "autor": "eu"}
    avaliacao = evaluator.avaliar(
        tema="tema x", conteudo="conteudo", briefing=briefing, tipo_de_post="short_carousel"
    )
    assert isinstance(avaliacao, AvaliacaoSlideMark)
    assert avaliacao.score.tese == 8
    assert avaliacao.score.progressao == 7
    assert avaliacao.score.concretude == 6
    assert avaliacao.score.precisao_tecnica == 7
    assert avaliacao.score.retencao == 6
    assert avaliacao.score.autoridade == 7
    assert avaliacao.score.autoria == 8
    assert avaliacao.score.slidemark == 9
    assert avaliacao.score.revisao_textual == 8
    assert avaliacao.veredito == "Publicavel com ajustes menores."
    assert avaliacao.pontos_fortes == ["forte 1", "forte 2"]
    assert avaliacao.pontos_fracos == ["fraco 1"]
    assert len(avaliacao.trechos_fracos) == 1
    assert avaliacao.trechos_fracos[0].trecho == 3
    assert avaliacao.redundancias == ["slide 2 e 3"]
    assert avaliacao.falhas_tecnicas == ["comparacao antes/depois incompleta"]
    assert avaliacao.sugestoes_melhoria == ["sug 1", "sug 2"]


def test_spec_034_post_evaluator_calcula_total_quando_ausente() -> None:
    payload = _payload_avaliacao_short_carousel()
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
    }
    agent = FakeAgent(stdout=json.dumps(payload))
    evaluator = PostEvaluator(agent, "codex")
    avaliacao = evaluator.avaliar("tema", "conteudo", {}, tipo_de_post="short_carousel")
    assert avaliacao.score.total == 6.0


def test_spec_034_post_evaluator_clamp_scores_fora_do_intervalo() -> None:
    payload = _payload_avaliacao_short_carousel()
    payload["score"] = {
        "tese": 20,
        "progressao": -5,
        "concretude": 15,
        "precisaoTecnica": 0,
        "retencao": 11,
        "autoridade": 10,
        "autoria": -1,
        "slidemark": 100,
        "revisaoTextual": 7,
    }
    agent = FakeAgent(stdout=json.dumps(payload))
    evaluator = PostEvaluator(agent, "codex")
    avaliacao = evaluator.avaliar("tema", "conteudo", {}, tipo_de_post="short_carousel")
    assert avaliacao.score.tese == 10
    assert avaliacao.score.progressao == 0
    assert avaliacao.score.concretude == 10
    assert avaliacao.score.precisao_tecnica == 0
    assert avaliacao.score.retencao == 10
    assert avaliacao.score.autoridade == 10
    assert avaliacao.score.autoria == 0
    assert avaliacao.score.slidemark == 10
    assert avaliacao.score.revisao_textual == 7


def test_spec_034_post_evaluator_erro_agent_levanta_runtime_error() -> None:
    agent = FakeAgent(stdout="", error="falhou")
    evaluator = PostEvaluator(agent, "codex")
    with pytest.raises(RuntimeError):
        evaluator.avaliar("tema", "conteudo", {})


def test_spec_034_post_evaluator_json_invalido_levanta_value_error() -> None:
    agent = FakeAgent(stdout="sem json")
    evaluator = PostEvaluator(agent, "codex")
    with pytest.raises(ValueError):
        evaluator.avaliar("tema", "conteudo", {})


def test_spec_034_post_evaluator_score_nao_dict_levanta_value_error() -> None:
    agent = FakeAgent(stdout=json.dumps({"score": "nao"}))
    evaluator = PostEvaluator(agent, "codex")
    with pytest.raises(ValueError):
        evaluator.avaliar("tema", "conteudo", {})


def test_spec_035_load_prompt_evaluate_post_contem_placeholders() -> None:
    for chave in (
        "generator.evaluate_post_post",
        "generator.evaluate_post_article",
        "generator.evaluate_post_short_carousel",
        "generator.evaluate_post_long_slide",
    ):
        template = load_prompt(chave)
        for token in ("{tema}", "{conteudoGerado}", "{briefingAutoral}"):
            assert token in template, f"token ausente em {chave}: {token}"


def test_spec_036_exportar_markdown_cria_arquivo_md(tmp_path: Path) -> None:
    destino = exportar_markdown(
        tema="Meu Tema!",
        plataforma="LinkedIn",
        tipo_de_post="post",
        conteudo="Ola mundo",
        exports_dir=tmp_path,
    )
    assert destino.exists()
    assert destino.suffix == ".md"
    assert destino.read_text(encoding="utf-8") == "Ola mundo"
    assert destino.parent == tmp_path


def test_spec_036_exportar_markdown_cria_diretorio_se_nao_existe(tmp_path: Path) -> None:
    novo_dir = tmp_path / "sub" / "exports"
    assert not novo_dir.exists()
    destino = exportar_markdown(
        tema="T",
        plataforma="P",
        tipo_de_post="article",
        conteudo="c",
        exports_dir=novo_dir,
    )
    assert novo_dir.is_dir()
    assert destino.exists()


def test_spec_036_exportar_markdown_sanitiza_nome() -> None:
    nome = nome_arquivo_base("Cafe com Pao!", "LinkedIn DEV", "post")
    assert nome == "cafe-com-pao-linkedin-dev-post"


def test_spec_036_exportar_markdown_usa_dir_padrao_se_nao_informado(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import content_engine.exporter as exporter_mod

    monkeypatch.setattr(exporter_mod, "EXPORTS_DIR", Path("/tmp/ce-test-default-md"))
    caminho = exporter_mod.EXPORTS_DIR
    caminho.mkdir(parents=True, exist_ok=True)
    for f in caminho.iterdir():
        if f.is_file():
            f.unlink()
    destino = exportar_markdown("tema", "plataforma", "post", "abc")
    assert destino.parent == caminho
    assert destino.suffix == ".md"
    assert destino.exists()
    assert destino.read_text(encoding="utf-8") == "abc"


def test_spec_037_exportar_txt_cria_arquivo_txt(tmp_path: Path) -> None:
    destino = exportar_txt(
        tema="Tema",
        plataforma="Twitter",
        tipo_de_post="short_carousel",
        conteudo="conteudo do post",
        exports_dir=tmp_path,
    )
    assert destino.suffix == ".txt"
    assert destino.read_text(encoding="utf-8") == "conteudo do post"


def test_spec_037_exportar_txt_reutiliza_sanitizacao() -> None:
    base = nome_arquivo_base("Aula #1", "Plataforma X", "article")
    assert base == "aula-1-plataforma-x-article"


def test_exportar_conteudo_gera_md_e_json_para_post(tmp_path: Path) -> None:
    arquivos = exportar_conteudo(
        tema="Tema",
        plataforma="LinkedIn",
        tipo_de_post="post",
        conteudo="conteudo final",
        metadados={"origem": "teste"},
        segmentos=[{"id": "seg-1", "ordem": 1, "texto": "conteudo final"}],
        avaliacao_post={"score": {"total": 10}},
        exports_dir=tmp_path,
    )
    md_path, json_path = arquivos

    assert md_path.suffix == ".md"
    assert json_path.suffix == ".json"
    assert md_path.stem == json_path.stem
    assert md_path.read_text(encoding="utf-8") == "conteudo final"
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["conteudo"] == "conteudo final"
    assert payload["metadados"] == {"origem": "teste"}
    assert payload["alertas"] == []
    assert payload["slides"] == []
    assert payload["segmentos"][0]["id"] == "seg-1"
    assert payload["avaliacao_post"]["score"]["total"] == 10
    assert payload["parse_error"] is None


def test_exportar_conteudo_slidemark_gera_json_puro_com_sufixo(tmp_path: Path) -> None:
    slidemark = {
        "version": "1.0.0",
        "slides": [
            {"id": "cover", "type": "cover.hero", "title": "Hook"},
            {"id": "cta", "type": "closing.cta", "title": "Fim", "cta": "Comente"},
        ],
    }
    arquivos = exportar_conteudo(
        tema="Tema",
        plataforma="LinkedIn",
        tipo_de_post="short_carousel",
        conteudo="resumo",
        slidemark=slidemark,
        exports_dir=tmp_path,
    )
    md_path, json_path = arquivos

    assert md_path.suffix == ".md"
    assert json_path.name.endswith(".slidemark.json")
    assert json.loads(json_path.read_text(encoding="utf-8")) == slidemark


def test_sanitizar_nome_arquivo_basico() -> None:
    assert sanitizar_nome_arquivo("Ola Mundo!") == "ola-mundo"
    assert sanitizar_nome_arquivo("   ") == "post"
    assert sanitizar_nome_arquivo("---abc---") == "abc"
    assert len(sanitizar_nome_arquivo("a" * 200)) == 80
    assert sanitizar_nome_arquivo("---") == "post"
    assert sanitizar_nome_arquivo("") == "post"
