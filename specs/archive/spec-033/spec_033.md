# SPEC-033 — Prompt de ajuste por segmento

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Define o template de reescrita parcial. O prompt deve preservar objetivo, plataforma, voz do usuário, tipo de autoria e restrições narrativas, retornando apenas `segmentoReescrito`.

## Plan
1. Incluir conteúdo completo como contexto, não como alvo de reescrita.
2. Marcar claramente o segmento atual e o pedido do usuário.
3. Reforçar limites: não inventar experiência, não contradizer o restante e não alterar outros segmentos.
4. Exigir JSON simples e validável.

## Tasks
- [ ] T01 — Criar template Markdown de ajuste por segmento.
- [ ] T02 — Incluir placeholders para conteúdo completo, segmento, pedido, personalidade e restrições.
- [ ] T03 — Incluir guardrails de coerência, fidelidade e escopo de edição.
- [ ] T04 — Definir contrato JSON com `segmentoReescrito`.
- [ ] T05 — Testar prompt com restrições de experiência baixa e personalidade baixa.

