# SPEC-008 — Avaliação consolidada do gateway

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Implementa `avaliar_gateway`, a decisão central entre aprovado equilibrado, aprovado desequilibrado e reprovado. A função deve devolver tipo de gateway, tipo de autoria, restrições ou próximas lacunas sem chamar LLM.

## Plan
1. Avaliar primeiro o gateway equilibrado usando score normalizado.
2. Avaliar depois o gateway desequilibrado usando score bruto.
3. Para aprovação desequilibrada, classificar autoria e gerar restrições.
4. Para reprovação, devolver lacunas autorais que orientem próximas perguntas.

## Tasks
- [ ] T01 — Implementar `avaliar_gateway(scores)`.
- [ ] T02 — Retornar `tipo_autoria="hibrida"` e restrições vazias para gateway equilibrado.
- [ ] T03 — Integrar classificação e restrições no gateway desequilibrado.
- [ ] T04 — Integrar `identificar_lacunas` no caso reprovado.
- [ ] T05 — Testar precedência do equilibrado sobre o desequilibrado e todos os caminhos de retorno.

