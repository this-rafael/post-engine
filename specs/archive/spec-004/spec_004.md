# SPEC-004 — Gateway equilibrado

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Implementa o gateway equilibrado: aprovação somente quando todos os aspectos autorais normalizados atingem 100. Esse caminho indica material suficiente para um conteúdo completo, narrativo, humano e fiel ao usuário.

## Plan
1. Usar exclusivamente scores normalizados para a regra equilibrada.
2. Exigir completude em experiência, opinião, sentimento, aprendizado e personalidade.
3. Manter a função pura para facilitar testes e uso dentro de `avaliar_gateway`.
4. Cobrir bordas onde total alto não compensa categoria incompleta.

## Tasks
- [ ] T01 — Implementar `passou_gateway_equilibrado(score_normalizado)`.
- [ ] T02 — Usar a lista oficial `ASPECTOS_AUTORAIS` como única fonte de categorias.
- [ ] T03 — Garantir que todas as categorias precisem estar `>= 100`.
- [ ] T04 — Testar aprovação com cinco categorias completas.
- [ ] T05 — Testar reprovação com uma categoria abaixo de 100, mesmo com total alto.

