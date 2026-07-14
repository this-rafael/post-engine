# SPEC-038 — Persistência de sessão

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Persistência automática da sessão da TUI em JSON local. Ela deve permitir retomada operacional, mas não equivale à exportação final do conteúdo.

## Plan
1. Definir contrato de `TuiSessionState`.
2. Salvar estado em `.data/sessions/current-session.json`.
3. Persistir entrada, prompt, briefing, scores, restrições, execução, conteúdo e segmentos.
4. Tratar escrita de forma robusta e testável.

## Tasks
- [ ] T01 — Implementar modelo/estrutura de estado persistido da TUI.
- [ ] T02 — Implementar `salvar_sessao` com criação de diretório `.data/sessions`.
- [ ] T03 — Serializar briefing, scores, restrições, stdout, stderr, returncode, eventos, conteúdo e segmentos.
- [ ] T04 — Disparar persistência após preview, execução, edição, limpeza e exportação.
- [ ] T05 — Testar escrita bem-sucedida e preservação dos campos mínimos.

