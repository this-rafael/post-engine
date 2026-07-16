"""Diagnosticos de integridade sem expor templates ou contexto dinamico."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .conditions import validate_condition
from .repository import PromptRegistryRepository


@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: str
    message: str
    operation: str | None = None
    artifact: str | None = None
    explanation: str = ""
    recommended_action: str = ""


def run_diagnostics(path: str | Path | None = None) -> list[Diagnostic]:
    findings: list[Diagnostic] = []
    with PromptRegistryRepository(path) as repository:
        for operation in repository.list_operations():
            composition = repository.get_active_composition(operation.key)
            if composition is None:
                findings.append(Diagnostic("OPERATION_WITHOUT_ACTIVE_COMPOSITION", "error", "Operacao sem composicao ativa", operation.key, explanation="O resolver nao possui uma sequencia para montar o prompt.", recommended_action="Ative uma composicao valida."))
                continue
            items = repository.composition_items(composition.id)
            if not items:
                findings.append(Diagnostic("EMPTY_COMPOSITION", "error", "Composicao ativa sem itens", operation.key, explanation="Nenhum artefato pode produzir o prompt final.", recommended_action="Adicione itens ou ative outra composicao."))
            for item in items:
                artifact, version = repository.resolve_item_artifact(item)
                if version is None and item.required:
                    findings.append(Diagnostic("ARTIFACT_WITHOUT_ACTIVE_VERSION", "error", "Artefato requerido sem versao ativa", operation.key, artifact.key, "O item requerido nao pode ser resolvido.", "Ative uma versao valida."))
                if artifact.status in {"LEGACY", "ORPHAN", "REFERENCE_ONLY"}:
                    findings.append(Diagnostic("NON_OPERATIONAL_ARTIFACT_USED", "error", "Composicao ativa usa artefato nao operacional", operation.key, artifact.key, "Referencias, legados e orfaos nao devem integrar prompts operacionais.", "Substitua o item por um artefato operacional."))
                try:
                    validate_condition({"field": item.condition_field, "operator": item.condition_operator, "value": item.condition_value} if item.condition_operator else None)
                except ValueError as exc:
                    findings.append(Diagnostic("INVALID_CONDITION", "error", str(exc), operation.key, artifact.key, "A condicao nao pode ser avaliada pelo resolver seguro.", "Corrija campo, operador ou valor."))
                if version is not None:
                    found = set(version.expected_variables)
                    required = set(version.required_variables)
                    if not required.issubset(found):
                        findings.append(Diagnostic("REQUIRED_PLACEHOLDER_UNDECLARED", "error", "Placeholder obrigatorio nao declarado", operation.key, artifact.key, "A versao declara uma obrigatoriedade fora do contrato.", "Atualize os placeholders esperados."))
        for artifact in repository.list_artifacts(status="ORPHAN"):
            findings.append(Diagnostic("ORPHAN_ARTIFACT", "warning", "Artefato sem consumidor operacional", artifact=artifact.key, explanation="O artefato nao aparece em nenhuma composicao ativa.", recommended_action="Arquive-o ou associe-o a uma composicao."))
        for artifact in repository.list_artifacts():
            if artifact.artifact_type in {"LEGACY", "REFERENCE"} and artifact.status == "ACTIVE":
                findings.append(Diagnostic("ARTIFACT_METADATA_DIVERGENCE", "warning", "Status ativo diverge da classificacao do artefato", artifact=artifact.key, explanation="O artefato e legado ou referencia, mas esta marcado como ativo.", recommended_action="Reconciliar o status de metadados; nao use em composicoes."))
        for execution in repository.list_execution_references(limit=50):
            if execution.get("error"):
                findings.append(Diagnostic("RECENT_RESOLUTION_FAILURE", "warning", "Falha recente de resolucao", operation=str(execution["operation_key"]), explanation=str(execution["error"]), recommended_action="Revise contexto, placeholders e itens da composicao."))
    return findings


def diagnostics_as_dict(path: str | Path | None = None) -> list[dict[str, Any]]:
    return [item.__dict__ for item in run_diagnostics(path)]


__all__ = ["Diagnostic", "diagnostics_as_dict", "run_diagnostics"]
