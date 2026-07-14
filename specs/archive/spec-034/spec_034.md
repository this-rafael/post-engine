# SPEC-034 — Avaliação do conteúdo gerado

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Avalia o conteúdo gerado após a segmentação, sem bloquear a etapa de segmentar. A avaliação mede experiência, opinião, sentimento, aprendizado, personalidade, fidelidade e naturalidade.

## Plan
1. Receber tema, conteúdo gerado e material autoral original.
2. Chamar avaliador LLM com critérios de 0 a 100.
3. Validar retorno em `ScoreDoPost` e listas de pontos fortes/fracos.
4. Expor resultado como suporte de revisão, não como bloqueio rígido no MVP.

## Tasks
- [ ] T01 — Implementar serviço de avaliação do post gerado.
- [ ] T02 — Garantir execução apenas após geração e preferencialmente após segmentação.
- [ ] T03 — Validar scores de 0 a 100 e calcular total.
- [ ] T04 — Retornar pontos fortes, pontos fracos e sugestões de melhoria.
- [ ] T05 — Testar avaliação válida, JSON inválido e conteúdo que inventa fatos.

