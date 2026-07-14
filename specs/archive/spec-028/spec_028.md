# SPEC-028 — AgentWrapper genérico

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Implementa ou consolida o `AgentWrapper` como infraestrutura genérica para `codex` e `opencode`. Ele deve montar comandos, executar subprocessos e retornar `AgentResult`, sem conhecer regras de produto.

## Plan
1. Definir interface de execução comum para ferramentas LLM CLI.
2. Montar comando conforme tool, modelo, workspace, sandbox e saída JSON.
3. Capturar `stdout`, `stderr`, `returncode`, comando e eventos JSONL.
4. Manter o wrapper reutilizável fora da TUI e da engine de produto.

## Tasks
- [ ] T01 — Implementar `AgentWrapper.run` com suporte a `codex` e `opencode`.
- [ ] T02 — Montar comandos CLI sem incluir persona, briefing, scoring ou regras de post.
- [ ] T03 — Capturar `stdout`, `stderr`, `returncode` e comando final.
- [ ] T04 — Parsear eventos JSONL quando `json_output=True`.
- [ ] T05 — Testar montagem de comandos com `subprocess.run` mockado.

