# SPEC-019 — Perguntas recursivas

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Gera novas perguntas após cada rodada considerando scores, memory pack, interações recentes, lacunas e proximidade dos gateways. A próxima pergunta deve melhorar chance de aprovação sem insistir em categorias já saturadas.

## Plan
1. Priorizar categorias abaixo de 100 para gateway equilibrado.
2. Detectar quando o gateway desequilibrado está próximo e aprofundar a categoria dominante.
3. Usar `memory_pack` e últimas interações para evitar repetição.
4. Adaptar pergunta quando experiência for baixa, sem forçar vivência.

## Tasks
- [ ] T01 — Criar função ou prompt de geração recursiva de perguntas.
- [ ] T02 — Integrar `identificar_lacunas`, scores, memory pack e últimas interações.
- [ ] T03 — Definir heurística de prioridade entre lacuna fraca e dominante promissora.
- [ ] T04 — Evitar perguntas repetidas ou redundantes com o que já está no memory pack.
- [ ] T05 — Testar cenários de gateway equilibrado próximo, desequilibrado próximo e experiência baixa.

