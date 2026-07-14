# SPEC-044 — Bloqueio de gerações concorrentes

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Impede múltiplas gerações concorrentes no MVP. O controle reduz conflitos de estado, duplicação de chamadas LLM e inconsistência na sessão persistida.

## Plan
1. Manter flag de execução ativa no estado da TUI.
2. Bloquear novo clique em `Rodar` durante execução.
3. Refletir estado no botão e em mensagem operacional.
4. Liberar bloqueio em sucesso, erro ou cancelamento controlado.

## Tasks
- [ ] T01 — Adicionar estado `is_running` ou equivalente na TUI.
- [ ] T02 — Desabilitar/bloquear botão `Rodar` durante execução.
- [ ] T03 — Impedir dupla chamada mesmo com eventos rápidos de teclado/mouse.
- [ ] T04 — Restaurar estado ao finalizar worker/thread.
- [ ] T05 — Testar tentativa de execução concorrente e liberação após erro.

