# SPEC-003 — Scoring autoral

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Atualiza scores autorais a partir da avaliação de cada resposta. O score bruto acumula volume autoral e pode passar de 100; o normalizado aplica teto de 100 por aspecto para sustentar o gateway equilibrado.

## Plan
1. Tratar o LLM como fonte principal de deltas, mas validar defensivamente o payload.
2. Somar deltas válidos ao score bruto de cada aspecto autoral.
3. Recalcular normalizado com `min(valor, 100)` e totais brutos/normalizados.
4. Rejeitar ou normalizar deltas inválidos antes de alterar o estado.

## Tasks
- [ ] T01 — Implementar validação de deltas para aspectos obrigatórios, inteiros e intervalo permitido.
- [ ] T02 — Implementar `atualizar_scores` preservando imutabilidade do score anterior.
- [ ] T03 — Calcular `total_bruto` e `total_normalizado` a partir das categorias oficiais.
- [ ] T04 — Garantir clamp do normalizado sem limitar o bruto.
- [ ] T05 — Testar soma incremental, clamp, categorias ausentes, negativos e valores acima de 100.

