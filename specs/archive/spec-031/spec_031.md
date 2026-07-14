# SPEC-031 — Prompt de segmentação

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Define o template que solicita ao LLM a divisão do conteúdo em segmentos editáveis. O prompt deve preservar o texto final sem títulos artificiais e retornar JSON com array de segmentos.

## Plan
1. Receber conteúdo completo do post.
2. Instruir segmentação sem adicionar títulos visíveis ou nomear seções.
3. Exigir que cada segmento faça sentido isoladamente.
4. Retornar JSON validável com `id`, `ordem`, `papelInterno` e `texto`.

## Tasks
- [ ] T01 — Criar template Markdown de segmentação.
- [ ] T02 — Definir contrato JSON com array `segmentos`.
- [ ] T03 — Incluir regra para não adicionar títulos ou rótulos ao texto final.
- [ ] T04 — Incluir regra de reescrita isolável por segmento.
- [ ] T05 — Testar prompt renderizado e validação de saída mínima.

