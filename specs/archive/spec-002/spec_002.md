# SPEC-002 — Inicialização do estado da entrevista

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Implementa a criação do estado inicial da entrevista autoral a partir de `InicioEntrevista`. O estado deve começar reprovado, com scores zerados, `memory_pack` vazio e dados obrigatórios validados antes de qualquer chamada ao LLM.

## Plan
1. Validar a entrada mínima exigida pelo produto: tema, plataforma, objetivo e tipo de post.
2. Criar scores brutos e normalizados zerados para todos os aspectos autorais.
3. Inicializar gateway como `reprovado`, sem restrições e com lacunas vazias.
4. Retornar um `EstadoEntrevista` pronto para o loop principal, com `max_rodadas` configurável.

## Tasks
- [ ] T01 — Implementar validação de campos obrigatórios e `tipo_de_post` permitido.
- [ ] T02 — Criar função `criar_scores_iniciais` com todas as categorias em zero.
- [ ] T03 — Criar `ResultadoGateway` inicial reprovado e sem aprovação implícita.
- [ ] T04 — Inicializar `MemoryPack`, interações, contador de rodadas e `max_rodadas`.
- [ ] T05 — Cobrir casos de entrada vazia, tipo inválido e estado inicial completo em testes.

