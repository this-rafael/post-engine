# SPEC-053 — Testes de gateway

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Cria testes para gateway equilibrado, desequilibrado e reprovado. A cobertura deve proteger os critérios autorais que determinam quando a geração pode acontecer.

## Plan
1. Testar completude normalizada do gateway equilibrado.
2. Testar total bruto, personalidade e categoria principal no gateway desequilibrado.
3. Testar que personalidade não conta como dominante principal.
4. Testar retorno consolidado de `avaliar_gateway`.

## Tasks
- [ ] T01 — Testar gateway equilibrado aprovado e reprovado.
- [ ] T02 — Testar gateway desequilibrado aprovado com bruto concentrado válido.
- [ ] T03 — Testar reprovação por total bruto insuficiente.
- [ ] T04 — Testar reprovação por personalidade insuficiente.
- [ ] T05 — Testar reprovação quando apenas personalidade é dominante.

