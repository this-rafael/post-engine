# SPEC-042 — Preview do prompt na TUI

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Implementa a ação de preview do prompt final. O usuário deve conseguir validar a renderização condicional antes de chamar o LLM.

## Plan
1. Validar campos obrigatórios e briefing JSON.
2. Montar `GenerationPromptInput` a partir da TUI.
3. Chamar `PromptBuilder`.
4. Exibir prompt renderizado e persistir sessão.

## Tasks
- [ ] T01 — Implementar handler do botão `Preview`.
- [ ] T02 — Integrar validação de entrada da SPEC-040.
- [ ] T03 — Montar input do `PromptBuilder` com briefing, scores e restrições.
- [ ] T04 — Exibir prompt renderizado em área read-only.
- [ ] T05 — Persistir sessão após preview bem-sucedido.

