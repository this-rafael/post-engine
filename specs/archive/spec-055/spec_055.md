# SPEC-055 — Testes do AgentWrapper

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Cria testes unitários para montagem de comandos, execução mockada e parse de JSONL do `AgentWrapper`. Os testes não devem chamar `codex` ou `opencode` reais.

## Plan
1. Mockar `subprocess.run` ou equivalente.
2. Validar comando montado para `codex` e `opencode`.
3. Validar captura de stdout, stderr, returncode e eventos.
4. Validar tratamento de falhas sem dependência de CLI real.

## Tasks
- [ ] T01 — Testar montagem de comando para `codex`.
- [ ] T02 — Testar montagem de comando para `opencode`.
- [ ] T03 — Testar parse de eventos JSONL válidos.
- [ ] T04 — Testar JSONL inválido, timeout, CLI ausente e returncode não zero.
- [ ] T05 — Garantir que nenhum teste unitário invoque executáveis reais.

