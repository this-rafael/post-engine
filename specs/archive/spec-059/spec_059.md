# SPEC-059 — Testes de segmentação

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Cria testes para parsear e validar segmentos retornados pelo LLM. A segmentação deve ser robusta porque alimenta edição isolada, avaliação posterior e persistência de sessão.

## Plan
1. Testar JSON válido com segmentos ordenados.
2. Testar JSON inválido e campos ausentes.
3. Testar ids duplicados e ordem inválida.
4. Testar que `papel_interno` não precisa ser exibido ao usuário.

## Tasks
- [ ] T01 — Testar parse de segmentos válidos.
- [ ] T02 — Testar JSON inválido.
- [ ] T03 — Testar segmento com campos ausentes.
- [ ] T04 — Testar ids duplicados.
- [ ] T05 — Testar ordem inválida ou não sequencial.

