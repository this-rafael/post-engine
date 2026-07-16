"""Registry versionado de prompts operacionais.

Consumidores devem usar :func:`resolve_prompt`; o SQLite e os artefatos nao
sao acessados diretamente fora deste pacote.
"""
from .importer import ensure_registry_initialized, import_legacy_prompts
from .resolver import PromptResolution, PromptResolver, resolve_prompt

__all__ = [
    "PromptResolution",
    "PromptResolver",
    "ensure_registry_initialized",
    "import_legacy_prompts",
    "resolve_prompt",
]
