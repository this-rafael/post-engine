# SPEC-035 — Prompt de avaliação do post

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Define o template que avalia o post contra o briefing autoral. O prompt deve identificar se o conteúdo respeitou vivências, opinião, sentimento, aprendizado, personalidade, fidelidade e naturalidade.

## Plan
1. Montar prompt com tema, conteúdo gerado e briefing/material autoral original.
2. Exigir avaliação numérica por critério.
3. Pedir pontos fortes, pontos fracos e sugestões acionáveis.
4. Reforçar que fidelidade penaliza invenção de fatos não informados.

## Tasks
- [ ] T01 — Criar template Markdown de avaliação do post.
- [ ] T02 — Definir contrato JSON com `score`, `pontosFortes`, `pontosFracos` e `sugestoesDeMelhoria`.
- [ ] T03 — Incluir critérios de fidelidade e naturalidade além dos cinco aspectos autorais.
- [ ] T04 — Incluir instrução para penalizar falsa vivência e exagero de personalidade.
- [ ] T05 — Testar validação do contrato com campos ausentes e score fora do intervalo.

