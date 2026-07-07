"""Testes de SPEC-050 (loader de prompts) e SPEC-051 (render de templates)."""
from __future__ import annotations

import json
import re

import pytest

from content_engine.prompt_loader import (
    PROMPTS_ROOT,
    load_prompt,
    prompt_exists,
)
from content_engine.template_renderer import render_template


def test_prompts_root_aponta_para_diretorio_prompts() -> None:
    assert PROMPTS_ROOT.name == "prompts"
    assert PROMPTS_ROOT.is_dir()
    assert (PROMPTS_ROOT / "interview").is_dir()
    assert (PROMPTS_ROOT / "generator").is_dir()
    assert (PROMPTS_ROOT / "generator" / "personas").is_dir()


def test_load_prompt_generator_base_retorna_string_nao_vazia() -> None:
    content = load_prompt("generator.base")
    assert isinstance(content, str)
    assert content.strip() != ""


def test_load_prompt_avaliacao_autoria_v4() -> None:
    content = load_prompt("interview.evaluate_authorship")
    assert "autoria" in content or "experiencia" in content
    assert "Avalie" in content


def test_load_prompt_desconhecido_levanta_file_not_found() -> None:
    with pytest.raises(FileNotFoundError) as excinfo:
        load_prompt("nao.existe.de.jeito.nenhum")
    mensagem = str(excinfo.value)
    assert "nao.existe.de.jeito.nenhum" in mensagem
    assert str(PROMPTS_ROOT) in mensagem


def test_load_prompt_caminho_relativo_direto() -> None:
    content = load_prompt("interview/explore.md")
    assert "tema" in content
    assert "candidatas" in content


def test_prompt_exists_para_nomes_conhecidos() -> None:
    assert prompt_exists("generator.base") is True
    assert prompt_exists("interview.evaluate_authorship") is True
    assert prompt_exists("generator.persona_post") is True
    assert prompt_exists("generator.persona_article") is True
    assert prompt_exists("generator.persona_short_carousel") is True


def test_prompt_exists_para_nomes_desconhecidos() -> None:
    assert prompt_exists("nao.existe") is False
    assert prompt_exists("nope/missing.md") is False


def test_load_prompt_todos_os_nomes_logicos_resolvem() -> None:
    nomes = [
        "interview.explore",
        "interview.evaluate_authorship",
        "interview.deepen",
        "generator.base",
        "generator.rules_post",
        "generator.rules_article",
        "generator.rules_short_carousel",
        "generator.persona_post",
        "generator.persona_article",
        "generator.persona_short_carousel",
        "generator.segment",
        "generator.adjust_segment",
        "generator.evaluate_post_post",
        "generator.evaluate_post_article",
        "generator.evaluate_post_short_carousel",
        "generator.evaluate_post_long_slide",
    ]
    for nome in nomes:
        assert prompt_exists(nome), nome
        conteudo = load_prompt(nome)
        assert isinstance(conteudo, str)
        assert conteudo.strip() != ""


def test_render_template_substitui_placeholders_simples() -> None:
    template = "Olá {nome}, você tem {idade} anos."
    resultado = render_template(template, {"nome": "Ana", "idade": 30})
    assert resultado == "Olá Ana, você tem 30 anos."


def test_render_template_substitui_placeholders_com_chaves_duplas_atomicamente() -> None:
    resultado = render_template("Olá {{nome}}.", {"nome": "Ana"})
    assert resultado == "Olá Ana."
    assert "{" not in resultado


def test_render_template_chave_dupla_ausente_levanta_keyerror_sem_renderizar_a_chave_interna() -> None:
    with pytest.raises(KeyError) as excinfo:
        render_template("Faltando {{chave}} aqui.", {})
    assert "chave" in str(excinfo.value)


def test_render_template_chave_ausente_levanta_keyerror() -> None:
    template = "Faltando {chave} aqui."
    with pytest.raises(KeyError) as excinfo:
        render_template(template, {})
    assert "chave" in str(excinfo.value)


def test_render_template_preserva_json() -> None:
    payload = {
        "fatosVividos": ["trabalhei na Globo", "liderei migração"],
        "opiniao": ["acredito que"],
    }
    template = "Material: {dados} e {nome}."
    resultado = render_template(
        template, {"dados": json.dumps(payload, ensure_ascii=False), "nome": "x"}
    )
    assert json.dumps(payload, ensure_ascii=False) in resultado


def test_render_template_preserva_acentos_e_quebras_de_linha() -> None:
    template = """Linha 1: {titulo}
Linha 2: ação, ção, não.
Linha 3: {corpo}"""
    ctx = {"titulo": "Tópico", "corpo": "Corpo\ncom\nquebras"}
    resultado = render_template(template, ctx)
    assert "Tópico" in resultado
    assert "ação, ção, não." in resultado
    assert "\n" in resultado


def test_render_template_nao_avalia_expressoes() -> None:
    template = "Expressao literal: {1+1} deve permanecer textual."
    resultado = render_template(template, {})
    assert resultado == "Expressao literal: {1+1} deve permanecer textual."


def test_render_template_nao_avalia_aritmetica_com_chave_valida() -> None:
    template = "Soma: {valor}"
    resultado = render_template(template, {"valor": "1+1"})
    assert resultado == "Soma: 1+1"


def test_render_template_converte_valores_nao_strings() -> None:
    template = "Total: {n} itens, ativo: {flag}"
    resultado = render_template(template, {"n": 42, "flag": True})
    assert resultado == "Total: 42 itens, ativo: True"


def test_render_template_sem_placeholders_retorna_original() -> None:
    template = "Texto puro sem placeholders."
    assert render_template(template, {"x": 1}) == template


def test_render_template_padrao_regex_somente_identificadores() -> None:
    template = "JSON literal: { \"a\": 1 } e {valido} mas {nao valido} fica."
    resultado = render_template(template, {"valido": "OK"})
    assert "{ \"a\": 1 }" in resultado
    assert "OK" in resultado
    assert "{nao valido}" in resultado


def test_render_template_chaves_repetidas_sao_substituidas() -> None:
    template = "{x} e {x} novamente."
    assert render_template(template, {"x": "A"}) == "A e A novamente."


def test_render_template_chave_com_unicode_permanece_literal() -> None:
    template = "Mantem {não-ascii} intacto."
    assert re.search(r"\{não-ascii\}", template) is not None
    resultado = render_template(template, {})
    assert "{não-ascii}" in resultado
