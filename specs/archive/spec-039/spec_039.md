# SPEC-039 — Restauração de sessão

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Restaura a sessão da TUI ao abrir a aplicação. Falhas de leitura, arquivo ausente ou JSON corrompido não podem impedir o uso da interface.

## Plan
1. Tentar carregar `.data/sessions/current-session.json` na inicialização.
2. Validar parcialmente o shape do estado sem exigir schema rígido.
3. Aplicar defaults para campos ausentes.
4. Expor erro de restauração de forma observável, mas não bloqueante.

## Tasks
- [ ] T01 — Implementar `carregar_sessao`.
- [ ] T02 — Retornar estado vazio quando arquivo não existir.
- [ ] T03 — Tratar JSON inválido, permissões e campos ausentes.
- [ ] T04 — Reidratar campos da TUI sem executar LLM automaticamente.
- [ ] T05 — Testar arquivo ausente, corrompido, parcial e válido.

