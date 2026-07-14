# SPEC-048 — Seleção de sandbox

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Implementa seletor de sandbox para execuções via `codex`. O código deve suportar `read-only`, `workspace-write` e `danger-full-access`, mesmo que a decisão de produto sobre exibição de `danger-full-access` permaneça aberta.

## Plan
1. Definir enum/lista de valores aceitos para sandbox.
2. Mostrar sandbox apenas quando tool for `codex`.
3. Passar valor selecionado ao `AgentWrapper`.
4. Validar valor antes da execução.

## Tasks
- [ ] T01 — Adicionar seletor de sandbox à TUI.
- [ ] T02 — Validar `read-only`, `workspace-write` e `danger-full-access`.
- [ ] T03 — Condicionar habilitação do sandbox ao executor `codex`.
- [ ] T04 — Preservar decisão aberta sobre esconder ou exibir `danger-full-access`.
- [ ] T05 — Testar valores válidos, valor inválido e comportamento com `opencode`.

