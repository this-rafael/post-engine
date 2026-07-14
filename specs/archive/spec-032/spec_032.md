# SPEC-032 — Ajuste por segmento

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Permite reescrever apenas um segmento do post a partir de um pedido do usuário. A operação deve preservar coerência com o conteúdo completo e nunca inventar novas experiências.

## Plan
1. Receber conteúdo completo, segmento atual, pedido, personalidade e restrições.
2. Renderizar prompt de ajuste parcial.
3. Chamar LLM e validar retorno com apenas o segmento reescrito.
4. Substituir somente o segmento alvo, preservando os demais.

## Tasks
- [ ] T01 — Implementar serviço de ajuste por segmento.
- [ ] T02 — Validar existência do segmento alvo antes da execução.
- [ ] T03 — Enviar restrições de geração e contexto completo ao prompt.
- [ ] T04 — Aplicar resultado somente ao segmento solicitado.
- [ ] T05 — Testar alteração isolada, segmento inexistente e tentativa de reescrever o post inteiro.

