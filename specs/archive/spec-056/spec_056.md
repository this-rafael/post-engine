# SPEC-056 — Testes de persistência

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Cria testes para salvar e restaurar sessão da TUI. A persistência deve ser robusta, local e não bloquear o uso quando o arquivo estiver ausente ou corrompido.

## Plan
1. Testar escrita do estado mínimo.
2. Testar restauração bem-sucedida.
3. Testar defaults para schema parcial.
4. Testar falhas não bloqueantes.

## Tasks
- [ ] T01 — Testar criação de `.data/sessions/current-session.json`.
- [ ] T02 — Testar restauração de JSON válido.
- [ ] T03 — Testar comportamento com arquivo inexistente.
- [ ] T04 — Testar JSON inválido/corrompido.
- [ ] T05 — Testar schema parcial com defaults seguros.

