# SPEC-001 — Modelos de domínio e contratos Python

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Define os contratos Python que sustentam entrevista, scoring, gateway, briefing, geração, segmentação, TUI e execução LLM. Esta spec deve preservar `snake_case` no domínio Python e compatibilidade com JSON LLM-facing quando houver payloads em `camelCase`.

## Plan
1. Consolidar todos os tipos do PRD como contratos estáveis e testáveis.
2. Separar modelos de domínio, geração, sessão TUI e infraestrutura sem dependências circulares.
3. Garantir que `AgentResult` e tipos de executor permaneçam genéricos, sem conhecimento de produto.
4. Validar nomes, defaults e imutabilidade onde os objetos representam contratos de entrada ou saída.

## Tasks
- [ ] T01 — Definir `Literal`s e constantes para tipos de post, aspectos autorais, gateways, autoria e ferramentas LLM.
- [ ] T02 — Implementar `TypedDicts` e `dataclasses` centrais do PRD com nomes internos em `snake_case`.
- [ ] T03 — Separar contratos de entrevista, geração, segmentação, avaliação de post, sessão TUI e `AgentWrapper`.
- [ ] T04 — Definir defaults seguros para listas, `memory_pack`, eventos e campos opcionais.
- [ ] T05 — Criar validações leves para impedir categorias ausentes, tipos inválidos e divergência entre contrato Python e JSON esperado.

