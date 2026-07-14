# SPEC-045 — Exibição de resultado bruto e JSON parseado

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Exibe resultado bruto da execução e tenta parsear JSON final sem validação rígida por schema no MVP. JSON inválido não pode ocultar stdout, stderr ou erro de parse.

## Plan
1. Receber `AgentResult` da execução.
2. Mostrar stdout, stderr, returncode e eventos sempre que existirem.
3. Tentar extrair JSON final do stdout.
4. Exibir erro de parse sem bloquear o resultado bruto.

## Tasks
- [ ] T01 — Implementar atualização das áreas de resultado bruto.
- [ ] T02 — Implementar parser tolerante para JSON final do gerador.
- [ ] T03 — Exibir JSON parseado quando possível.
- [ ] T04 — Exibir erro de parse e manter stdout visível quando inválido.
- [ ] T05 — Testar stdout válido, inválido, vazio e stderr com returncode não zero.

