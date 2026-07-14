# SPEC-060 — Testes de contrato da geração

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Cria testes para validar o contrato esperado do JSON de saída do gerador. O MVP pode exibir JSON incompleto, mas o contrato esperado deve ser testado para orientar implementação e revisão.

## Plan
1. Validar campos mínimos `conteudo`, `metadados` e `alertas`.
2. Validar metadados de autoria, formato, plataforma, persona, gateway e restrições.
3. Validar sinalização de primeira pessoa e base narrativa principal.
4. Testar comportamento quando o JSON é inválido ou incompleto.

## Tasks
- [ ] T01 — Testar presença de `conteudo`, `metadados` e `alertas`.
- [ ] T02 — Testar metadados `tipoDePost`, `plataforma`, `personaUsada`, `tipoAutoria` e `tipoGateway`.
- [ ] T03 — Testar `usoDePrimeiraPessoa`, `baseNarrativaPrincipal` e `restricoesAplicadas`.
- [ ] T04 — Testar fallback de exibição quando JSON estiver inválido.
- [ ] T05 — Testar alertas quando restrições de geração impedirem narrativa pessoal forte.

