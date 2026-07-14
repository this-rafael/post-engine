# SPEC-024 — PromptBuilder

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Renderiza o prompt final de geração a partir de `GenerationPromptInput`. O `PromptBuilder` deve escolher persona e regras por `tipo_de_post` antes da chamada ao LLM, deixando o modelo focado em gerar conteúdo autoral.

## Plan
1. Receber dados estruturados do briefing e da configuração de geração.
2. Selecionar persona e regras com mapeamento determinístico por tipo de post.
3. Serializar briefing, scores e restrições de forma estável.
4. Falhar claramente em caso de `tipo_de_post` inválido.

## Tasks
- [ ] T01 — Implementar `build_generation_prompt(data: GenerationPromptInput)`.
- [ ] T02 — Criar mapeamento `tipo_de_post -> persona` e `tipo_de_post -> regras`.
- [ ] T03 — Serializar briefing, scores e restrições com JSON legível e sem corromper caracteres.
- [ ] T04 — Renderizar template base com apenas persona e regras ativas.
- [ ] T05 — Testar erro para tipo inválido e ausência de blocos concorrentes.

