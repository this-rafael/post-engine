# SPEC-054 — Testes de scoring

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Cria testes para atualização de scores autorais. A cobertura deve garantir acumulação correta, normalização em 100 e proteção contra deltas inválidos vindos do LLM.

## Plan
1. Testar soma incremental por aspecto autoral.
2. Testar clamp do score normalizado sem limitar score bruto.
3. Testar totais bruto e normalizado.
4. Testar validação defensiva de deltas inválidos.

## Tasks
- [ ] T01 — Testar `criar_scores_iniciais`.
- [ ] T02 — Testar `atualizar_scores` com deltas válidos.
- [ ] T03 — Testar normalizado limitado em 100 por categoria.
- [ ] T04 — Testar cálculo de `total_bruto` e `total_normalizado`.
- [ ] T05 — Testar rejeição ou correção de negativos, acima de 100 e categorias ausentes.

