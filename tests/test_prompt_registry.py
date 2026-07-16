from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from content_engine.prompt_registry.api import PromptRegistryApi
from content_engine.prompt_registry.conditions import InvalidPromptCondition, applies
from content_engine.prompt_registry.diagnostics import run_diagnostics
from content_engine.prompt_registry.importer import import_legacy_prompts
from content_engine.prompt_registry.repository import PromptRegistryError, PromptRegistryRepository
from content_engine.prompt_registry.resolver import PromptResolutionError, resolve_prompt


_CONSUMER_MODULES = (
    "generator.py",
    "segmentation.py",
    "adjust_segment.py",
    "adjust_segments_bulk.py",
    "post_evaluation.py",
    "slidemark_converter.py",
    "editorial_generation.py",
    "interview/exploration.py",
    "interview/validation.py",
    "interview/llm_evaluation.py",
)


@pytest.fixture
def registry_path(tmp_path: Path) -> Path:
    path = tmp_path / "prompt-registry.sqlite3"
    import_legacy_prompts(path, write_inventory_file=False)
    return path


def _generation_context(content_type: str = "post") -> dict[str, object]:
    return {
        "tema": "decisões de arquitetura",
        "plataforma": "linkedin",
        "objetivoDoPost": "explicar um critério",
        "tipoDePost": content_type,
        "personalidade": "direta",
        "restricoesDeGeracao": "[]",
        "briefingAutoral": "{}",
        "gatewayResult": "{}",
        "interviewContext": "{}",
        "evidenceLedger": "[]",
        "authorialSignals": "[]",
        "authorialDimensions": "{}",
        "interviewGaps": "[]",
        "content_type": content_type,
        "is_visual_track": content_type in {"short_carousel", "long_slide"},
    }


def test_importa_operacoes_e_composicoes_ativas(registry_path: Path) -> None:
    from content_engine.llm_config import LLM_OPERATIONS

    with PromptRegistryRepository(registry_path) as repository:
        operations = repository.list_operations()
        assert {item.key for item in operations} == set(LLM_OPERATIONS)
        assert all(item.consumer_symbol for item in operations)
        assert all(repository.get_active_composition(item.key) for item in operations)
        assert repository.active_version("policy.anti_ia") is not None
        assert repository.active_version("contract.slidemark") is not None


def test_resolve_composicao_condicional_e_registra_somente_metadados(registry_path: Path) -> None:
    resolution = resolve_prompt("post_generate", _generation_context(), path=registry_path, provider="codex", model="test")
    assert "DevInterlocutorPost" in resolution.resolved_content
    assert "VOICE_01" in resolution.resolved_content
    assert resolution.template_hash != resolution.resolved_hash
    with PromptRegistryRepository(registry_path) as repository:
        execution = repository.list_execution_references("post_generate")[0]
    assert execution["provider"] == "codex"
    assert "resolved_content" not in execution
    assert execution["artifact_versions"]


def test_renderer_falha_sem_variavel_obrigatoria(registry_path: Path) -> None:
    context = _generation_context()
    del context["tema"]
    with pytest.raises(PromptResolutionError, match="tema"):
        resolve_prompt("post_generate", context, path=registry_path)


def test_condicoes_sao_limitadas() -> None:
    assert applies({"field": "is_visual_track", "operator": "IS_TRUE"}, {"is_visual_track": True})
    with pytest.raises(InvalidPromptCondition):
        applies({"field": "__import__", "operator": "EQUALS", "value": "os"}, {})


def test_versao_ativa_e_rollback_sao_transacionais(registry_path: Path) -> None:
    with PromptRegistryRepository(registry_path) as repository:
        current = repository.active_version("generator.segment")
        assert current is not None
        draft = repository.create_version(
            "generator.segment", current.content + "\n# versão nova",
            expected_variables=current.expected_variables,
            required_variables=current.required_variables,
            change_reason="teste",
        )
        repository.activate_version("generator.segment", draft.version)
        assert repository.active_version("generator.segment").version == draft.version  # type: ignore[union-attr]
        rollback = repository.rollback_version("generator.segment", current.version)
        assert rollback.version > draft.version
        assert rollback.content == current.content
        assert repository.active_version("generator.segment").version == rollback.version  # type: ignore[union-attr]
        with pytest.raises(sqlite3.IntegrityError):
            repository.connection.execute(
                "UPDATE prompt_artifact_versions SET content = 'mutado' WHERE id = ?", (current.id,)
            )


def test_preview_sanitiza_contexto_e_diagnosticos_mantem_orfao(registry_path: Path) -> None:
    api = PromptRegistryApi(registry_path)
    preview = api.preview("interview_questions", {"candidate_count": 2, "context_json": "segredo pessoal"})
    assert "segredo pessoal" not in preview["content"]
    assert "<redacted:context_json>" in preview["content"]
    assert any(item.code == "ORPHAN_ARTIFACT" for item in run_diagnostics(registry_path))


def test_observatory_catalog_ordena_fases_e_edita_com_lock(registry_path: Path) -> None:
    api = PromptRegistryApi(registry_path)
    catalog = api.catalog()
    assert [phase["order"] for phase in catalog["phases"]] == list(range(1, 13))
    assert catalog["phases"][9]["operations"] == ["adjust_segment", "adjust_segments_bulk"]
    artifact = api.artifact("generator.segment")
    assert artifact is not None
    active = artifact["active"]
    created = api.create_version("generator.segment", {
        "content": active["content"] + "\n# observatory draft",
        "expected_active_version": active["version"],
        "expected_active_hash": active["content_hash"],
    })
    assert created["status"] == "DRAFT"
    with pytest.raises(PromptRegistryError, match="Conflito"):
        api.create_version("generator.segment", {
            "content": active["content"] + "\n# conflito",
            "expected_active_version": active["version"] + 1,
            "expected_active_hash": active["content_hash"],
        })


def test_consumidores_nao_podem_reintroduzir_fontes_operacionais_legadas() -> None:
    root = Path(__file__).resolve().parents[1] / "src" / "content_engine"
    forbidden = ("prompt_loader", "load_prompt(", "ANTI_IA_POLICIES", "SLIDEMARK_LLM_CONTRACT")
    for relative in _CONSUMER_MODULES:
        source = (root / relative).read_text(encoding="utf-8")
        assert not any(token in source for token in forbidden), relative


def test_interview_gap_diagnosis_seed_is_resolvable(registry_path: Path) -> None:
    with PromptRegistryRepository(registry_path) as repository:
        assert repository.get_artifact("interview.gap_diagnosis") is not None
        assert repository.active_version("interview.gap_diagnosis") is not None
        assert repository.get_operation("interview_gap_diagnosis") is not None
        assert repository.get_active_composition("interview_gap_diagnosis") is not None

    resolution = resolve_prompt(
        "interview_gap_diagnosis",
        {
            "theme": "observabilidade",
            "format": "post",
            "question_count": "12",
            "max_questions": "12",
            "global_score": "40",
            "gateway_justification": "Material generico",
            "weak_dimensions": "experiencia_vivida",
            "vetoes": "GENERICIDADE",
            "llm_weaknesses": "Pouca concretude",
            "gaps_json": "[]",
        },
        path=registry_path,
        provider="codex",
        model="test",
    )
    assert "o que ainda falta" in resolution.resolved_content.lower()
    assert "observabilidade" in resolution.resolved_content
    assert "experiencia_vivida" in resolution.resolved_content
    assert {item["key"] for item in resolution.artifact_versions} >= {
        "interview.gap_diagnosis"
    }
