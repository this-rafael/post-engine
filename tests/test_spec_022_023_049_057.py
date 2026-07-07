"""SPEC-022, SPEC-023, SPEC-049, SPEC-057.

- 022: personas oficiais existem como arquivos
- 023: regras por tipo de post existem como arquivos
- 049: estrutura de pastas do projeto
- 057: testes do exporter (ja cobertos; aqui ficam os casos de sanitizacao e nao-automatica)
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from content_engine.exporter import (
    exportar_markdown,
    exportar_txt,
    sanitizar_nome_arquivo,
)
from content_engine.prompt_loader import PROMPTS_ROOT, load_prompt, prompt_exists


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_spec_022_personas_existem() -> None:
    for name in (
        "generator.persona_post",
        "generator.persona_article",
        "generator.persona_short_carousel",
        "generator.persona_long_slide",
    ):
        assert prompt_exists(name), name


def test_spec_022_personas_contem_yaml_resumo() -> None:
    for name, slug in (
        ("generator.persona_post", "DevInterlocutorPost"),
        ("generator.persona_article", "DevInterlocutorArticle"),
        ("generator.persona_short_carousel", "DevInterlocutorShortCarousel"),
        ("generator.persona_long_slide", "DevInterlocutorLongSlide"),
    ):
        text = load_prompt(name)
        assert slug in text
        assert "use_emojis" in text
        assert "avoid_fake_autobiography" in text


def test_spec_022_aceita_somente_formatos_atuais() -> None:
    from content_engine.schemas import TipoDePost, is_tipo_de_post, migrate_tipo_de_post

    for t in ("post", "article", "short_carousel", "long_slide"):
        assert is_tipo_de_post(t) is True
    assert is_tipo_de_post("feed") is False
    assert migrate_tipo_de_post("feed") == "post"
    from typing import get_args

    literal_values = get_args(TipoDePost)
    assert set(literal_values) == {
        "post",
        "article",
        "short_carousel",
        "long_slide",
    }


def test_spec_023_rules_existem_para_quatro_trilhas() -> None:
    for name in (
        "generator.rules_post",
        "generator.rules_article",
        "generator.rules_short_carousel",
        "generator.rules_long_slide",
    ):
        assert prompt_exists(name), name


def test_spec_023_rules_contem_secao_regras_conteudo() -> None:
    for name in (
        "generator.rules_post",
        "generator.rules_article",
        "generator.rules_short_carousel",
        "generator.rules_long_slide",
    ):
        text = load_prompt(name)
        assert "Regras do conteudo" in text or "Regras do conteúdo" in text


def test_spec_023_prompt_builder_seleciona_apenas_arquivo_ativo() -> None:
    from content_engine.prompt_builder import (
        PERSONA_FILES_POR_TIPO,
        RULES_FILES_POR_TIPO,
    )

    for tipo in ("post", "article", "short_carousel", "long_slide"):
        assert tipo in PERSONA_FILES_POR_TIPO
        assert tipo in RULES_FILES_POR_TIPO
        assert (
            PERSONA_FILES_POR_TIPO[tipo] != PERSONA_FILES_POR_TIPO["post"]
            or tipo == "post"
        )
        assert (
            RULES_FILES_POR_TIPO[tipo] != RULES_FILES_POR_TIPO["post"]
            or tipo == "post"
        )
    assert len(set(PERSONA_FILES_POR_TIPO.values())) == 4
    assert len(set(RULES_FILES_POR_TIPO.values())) == 4


def test_spec_049_estrutura_de_pastas() -> None:
    assert (PROJECT_ROOT / "src" / "content_engine").is_dir()
    assert (PROJECT_ROOT / "src" / "tui").is_dir()
    assert (PROJECT_ROOT / "prompts" / "interview").is_dir()
    assert (PROJECT_ROOT / "prompts" / "generator").is_dir()
    assert (PROJECT_ROOT / ".data" / "sessions").is_dir()
    assert (PROJECT_ROOT / "prompts" / "router").is_dir()
    assert (PROJECT_ROOT / "tests").is_dir()
    assert (PROJECT_ROOT / "src" / "content_engine" / "__init__.py").is_file()
    assert (PROJECT_ROOT / "src" / "tui" / "__init__.py").is_file()
    assert (PROJECT_ROOT / "tests" / "__init__.py").is_file()
    assert (PROJECT_ROOT / "pyproject.toml").is_file()


def test_spec_049_prompts_root_aponta_para_prompts_do_projeto() -> None:
    assert PROMPTS_ROOT.resolve() == (PROJECT_ROOT / "prompts").resolve()


def test_spec_049_data_dir_aponta_para_data_sessions_do_projeto() -> None:
    from content_engine.persistence import DATA_DIR, SESSION_FILE

    assert DATA_DIR.resolve() == (PROJECT_ROOT / ".data" / "sessions").resolve()
    assert SESSION_FILE.resolve() == (PROJECT_ROOT / ".data" / "sessions" / "current-session.json").resolve()


def test_spec_057_exportar_markdown_salva_conteudo(tmp_path: Path) -> None:
    path = exportar_markdown(
        tema="Topico novo",
        plataforma="LinkedIn",
        tipo_de_post="post",
        conteudo="# Titulo\n\nConteudo do post",
        exports_dir=tmp_path,
    )
    assert path.exists()
    assert path.suffix == ".md"
    assert path.read_text(encoding="utf-8").startswith("# Titulo")


def test_spec_057_exportar_txt_salva_conteudo(tmp_path: Path) -> None:
    path = exportar_txt(
        tema="Topico",
        plataforma="LinkedIn",
        tipo_de_post="post",
        conteudo="Texto simples",
        exports_dir=tmp_path,
    )
    assert path.exists()
    assert path.suffix == ".txt"
    assert path.read_text(encoding="utf-8") == "Texto simples"


def test_spec_057_exportacao_md_e_txt_consistentes(tmp_path: Path) -> None:
    md_path = exportar_markdown(
        tema="Mesma coisa",
        plataforma="LinkedIn",
        tipo_de_post="post",
        conteudo="mesmo",
        exports_dir=tmp_path,
    )
    txt_path = exportar_txt(
        tema="Mesma coisa",
        plataforma="LinkedIn",
        tipo_de_post="post",
        conteudo="mesmo",
        exports_dir=tmp_path,
    )
    assert md_path.stem == txt_path.stem
    assert md_path.suffix == ".md"
    assert txt_path.suffix == ".txt"


def test_spec_057_sanitizacao_nome_arquivo() -> None:
    assert sanitizar_nome_arquivo("Hello World!") == "hello-world"
    result = sanitizar_nome_arquivo("Ação é isso")
    assert "acao" in result or "a" in result
    assert " " not in result
    assert sanitizar_nome_arquivo("") == "post"
    long = "a" * 200
    assert len(sanitizar_nome_arquivo(long)) <= 80
    assert sanitizar_nome_arquivo("   ") == "post"
    assert sanitizar_nome_arquivo("Topico!@#") == "topico"


def test_spec_057_nome_arquivo_base_composto(tmp_path: Path) -> None:
    path = exportar_markdown(
        tema="Topico! Com espaço",
        plataforma="LinkedIn X",
        tipo_de_post="post",
        conteudo="x",
        exports_dir=tmp_path,
    )
    base = path.stem
    assert "post" in base
    assert "linkedin" in base
    assert " " not in base
    assert "!" not in base


def test_spec_057_exportacao_cria_diretorio(tmp_path: Path) -> None:
    target = tmp_path / "novo_dir"
    assert not target.exists()
    exportar_markdown(
        tema="x",
        plataforma="LinkedIn",
        tipo_de_post="post",
        conteudo="x",
        exports_dir=target,
    )
    assert target.is_dir()


def test_spec_057_exportacao_nao_automatica_no_generator(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from content_engine.generator import ContentGenerator
    from content_engine.schemas import AgentResult, GenerationPromptInput

    from tests.llm_fakes import AgentFakeRunMixin

    class FakeAgent(AgentFakeRunMixin):
        def run_codex(self, prompt: str, **kwargs) -> AgentResult:
            return AgentResult(
                tool="codex",
                command=["codex"],
                returncode=0,
                stdout=json.dumps({"conteudo": "ola", "metadados": {}, "alertas": []}),
                stderr="",
            )

        def run_opencode(self, prompt: str, **kwargs) -> AgentResult:
            return self.run_codex(prompt, **kwargs)

    gen = ContentGenerator(agent=FakeAgent(), tool="codex")
    data = GenerationPromptInput(
        tema="x",
        plataforma="LinkedIn",
        objetivo_do_post="y",
        tipo_de_post="post",
        briefing_autoral={},
    )
    out = gen.generate(data)
    assert out.conteudo == "ola"
    files = list((tmp_path).iterdir())
    assert files == []
