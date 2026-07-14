# SPEC-025 — Contrato do PromptBuilder

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Define critérios de aceite do `PromptBuilder`. A regra central é que o prompt renderizado contenha somente a persona e as regras do tipo ativo, nunca condicionais concorrentes para outros formatos.

## Plan
1. Converter os critérios do PRD em testes de contrato.
2. Validar presença da persona correta para feed, article e slide.
3. Validar ausência das personas e regras dos formatos inativos.
4. Validar presença de briefing, restrições e contrato JSON.

## Tasks
- [ ] T01 — Criar testes de contrato para `feed`, `article` e `slide`.
- [ ] T02 — Verificar que `feed` contém apenas `DevInterlocutorFeed`.
- [ ] T03 — Verificar que `article` contém apenas `DevInterlocutorArticle`.
- [ ] T04 — Verificar que `slide` contém apenas `DevInterlocutorSlide`.
- [ ] T05 — Verificar que o prompt não contém condicionais textuais como “se for feed”.

