# SPEC-047 — Seleção de executor LLM

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Permite selecionar `codex` ou `opencode` na TUI. A seleção deve configurar modelo e parâmetros compatíveis, mantendo anexos do OpenCode fora do MVP.

## Plan
1. Expor seletor de tool com valores oficiais.
2. Permitir modelo opcional conforme tool.
3. Condicionar campos específicos, como sandbox para `codex`.
4. Impedir anexos no `opencode` durante o MVP.

## Tasks
- [ ] T01 — Adicionar seletor `tool` com `codex` e `opencode`.
- [ ] T02 — Adicionar campo de modelo opcional.
- [ ] T03 — Mapear seleção para parâmetros do `AgentWrapper`.
- [ ] T04 — Ocultar ou desabilitar opções incompatíveis por executor.
- [ ] T05 — Testar seleção de tool e montagem correta do comando sem chamar CLI real.

