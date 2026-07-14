# SPEC-005 — Gateway desequilibrado

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Implementa aprovação desequilibrada para entrevistas com forte material autoral concentrado. O objetivo é permitir conteúdo opinativo, reflexivo, emocional ou experiencial sem transformar falta de experiência em falsa vivência.

## Plan
1. Usar score bruto para medir volume autoral acumulado.
2. Exigir total bruto mínimo de 600 e personalidade mínima de 80.
3. Exigir pelo menos uma categoria principal com 200 pontos ou mais.
4. Impedir que personalidade seja usada como categoria dominante principal.

## Tasks
- [ ] T01 — Implementar `passou_gateway_desequilibrado(score_bruto)`.
- [ ] T02 — Calcular total bruto usando todos os aspectos autorais.
- [ ] T03 — Calcular categoria dominante apenas entre experiência, opinião, sentimento e aprendizado.
- [ ] T04 — Validar personalidade como sustentação de autoria, não como eixo principal.
- [ ] T05 — Testar total insuficiente, personalidade insuficiente, dominante insuficiente e aprovação válida.

