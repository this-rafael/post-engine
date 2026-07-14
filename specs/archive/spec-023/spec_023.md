# SPEC-023 — Regras por tipo de post

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Define blocos de regras separados para `feed`, `article` e `slide`. O sistema deve renderizar apenas o bloco do formato ativo para reduzir ambiguidade e impedir mistura de instruções.

## Plan
1. Criar arquivos independentes de regras por formato.
2. Traduzir diferenças de ritmo, estrutura e profundidade do PRD para regras operacionais.
3. Garantir que blocos concorrentes não sejam enviados simultaneamente.
4. Preparar os arquivos para carregamento pelo loader de prompts.

## Tasks
- [ ] T01 — Criar `prompts/generator/rules-feed.md`.
- [ ] T02 — Criar `prompts/generator/rules-article.md`.
- [ ] T03 — Criar `prompts/generator/rules-slide.md`.
- [ ] T04 — Incluir limites de formato, tom, estrutura e profundidade em cada bloco.
- [ ] T05 — Testar que o `PromptBuilder` seleciona somente o arquivo do formato ativo.

