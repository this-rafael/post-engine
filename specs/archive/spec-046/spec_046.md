# SPEC-046 — Limpeza de saída

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Implementa a ação `Limpar` para limpar resultados de execução sem apagar o prompt renderizado. A sessão deve ser persistida depois da limpeza.

## Plan
1. Limpar stdout, stderr, eventos, returncode e JSON extraído.
2. Preservar campos de entrada e prompt renderizado.
3. Atualizar estado visual da TUI.
4. Persistir sessão limpa.

## Tasks
- [ ] T01 — Implementar handler do botão `Limpar`.
- [ ] T02 — Limpar apenas campos de saída e parse.
- [ ] T03 — Preservar prompt renderizado e briefing atual.
- [ ] T04 — Atualizar estado persistido após limpeza.
- [ ] T05 — Testar que limpar não apaga entrada nem prompt.

