# SPEC-027 — Geração de conteúdo

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Implementa a camada de produto que usa `PromptBuilder` e `AgentWrapper` para gerar conteúdo final. Ela não faz scoring de entrevista e deve preservar stdout bruto quando o JSON do gerador falhar.

## Plan
1. Montar `GenerationPromptInput` a partir do briefing e configurações da TUI/engine.
2. Renderizar prompt final com o `PromptBuilder`.
3. Executar LLM pelo `AgentWrapper` genérico.
4. Tentar parsear JSON final sem perder saída bruta e alertas.

## Tasks
- [ ] T01 — Implementar serviço de geração de conteúdo.
- [ ] T02 — Integrar `PromptBuilder` e `AgentWrapper` sem acoplar domínio ao executor.
- [ ] T03 — Parsear JSON esperado com fallback para `stdout` bruto.
- [ ] T04 — Retornar conteúdo, metadados, alertas e dados de execução.
- [ ] T05 — Testar sucesso, JSON inválido, erro de executor e preservação de `AgentResult`.

