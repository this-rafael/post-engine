# SPEC-022 — Personas oficiais

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Cria personas oficiais para `feed`, `article` e `slide`. Elas devem orientar voz, ritmo, profundidade e limites narrativos, sem serem editáveis pela TUI no MVP.

## Plan
1. Criar um arquivo Markdown por persona oficial.
2. Alinhar cada persona ao formato específico do PRD.
3. Incluir guardrails contra linguagem genérica, falsa vivência e exagero de estilo.
4. Versionar personas como assets de prompt carregáveis pelo `PromptBuilder`.

## Tasks
- [ ] T01 — Criar `prompts/generator/personas/dev-interlocutor-feed.md`.
- [ ] T02 — Criar `prompts/generator/personas/dev-interlocutor-article.md`.
- [ ] T03 — Criar `prompts/generator/personas/dev-interlocutor-slide.md`.
- [ ] T04 — Incluir regras de voz, estilo, ritmo, profundidade, guardrails e limites narrativos.
- [ ] T05 — Garantir que a TUI apenas selecione personas oficiais por `tipo_de_post`, sem edição no MVP.

