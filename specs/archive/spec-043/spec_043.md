# SPEC-043 — Execução LLM pela TUI

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Executa o LLM pela TUI usando o prompt renderizado e o `AgentWrapper`. A execução deve ocorrer em worker/thread para preservar responsividade.

## Plan
1. Exigir prompt renderizado antes de executar.
2. Verificar bloqueio de execução concorrente.
3. Rodar `AgentWrapper` em worker/thread.
4. Exibir `stdout`, `stderr`, `returncode`, eventos e JSON parseado quando possível.

## Tasks
- [ ] T01 — Implementar handler do botão `Rodar`.
- [ ] T02 — Bloquear execução quando não houver prompt renderizado.
- [ ] T03 — Executar `AgentWrapper.run` fora da thread principal da TUI.
- [ ] T04 — Atualizar áreas de resultado com `AgentResult`.
- [ ] T05 — Persistir sessão ao finalizar execução, com sucesso ou erro.

