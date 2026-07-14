# SPEC-052 — Testes do PromptBuilder

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Cria testes automatizados para garantir que o `PromptBuilder` renderize somente o formato ativo. Esses testes protegem a decisão de produto de não delegar roteamento determinístico ao LLM.

## Plan
1. Testar uma renderização por tipo de post.
2. Verificar presença da persona ativa e ausência das inativas.
3. Verificar briefing, restrições, scores e contrato JSON.
4. Testar falha explícita para tipo inválido.

## Tasks
- [ ] T01 — Criar testes para `feed`, `article` e `slide`.
- [ ] T02 — Garantir que cada prompt contenha apenas a persona correta.
- [ ] T03 — Garantir que regras de formatos inativos não apareçam no prompt.
- [ ] T04 — Verificar presença de briefing serializado, scores, restrições e saída JSON.
- [ ] T05 — Testar `tipo_de_post` inválido gerando erro.

