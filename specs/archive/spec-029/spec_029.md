# SPEC-029 — Robustez do AgentWrapper

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Adiciona tratamento controlado para falhas de subprocesso e saídas inválidas. O objetivo é tornar a execução observável e segura para a TUI sem esconder erro técnico do usuário.

## Plan
1. Mapear falhas previsíveis: timeout, CLI inexistente, permissão, retorno não zero e saída vazia.
2. Preservar `stderr`, `stdout`, comando e código de retorno quando disponíveis.
3. Tratar JSONL inválido sem quebrar a aplicação.
4. Retornar `AgentResult` ou erro controlado com mensagem operacional.

## Tasks
- [ ] T01 — Implementar timeout configurável na execução.
- [ ] T02 — Tratar `FileNotFoundError`, `PermissionError` e `subprocess.TimeoutExpired`.
- [ ] T03 — Tratar `returncode != 0`, `stdout` vazio e `stderr` não vazio.
- [ ] T04 — Tratar eventos JSONL inválidos preservando linhas brutas quando útil.
- [ ] T05 — Testar cada falha com mocks, sem chamar ferramentas reais.

