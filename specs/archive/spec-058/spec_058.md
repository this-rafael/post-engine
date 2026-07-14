# SPEC-058 — Testes da TUI de preview

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Cria testes para o fluxo de preview da TUI. O preview deve validar entrada, renderizar prompt com `PromptBuilder`, exibir resultado e persistir sessão.

## Plan
1. Testar validação de campos obrigatórios.
2. Testar rejeição de briefing JSON inválido.
3. Testar chamada ao `PromptBuilder`.
4. Testar persistência após preview bem-sucedido.

## Tasks
- [ ] T01 — Testar erro quando tema, plataforma ou objetivo estiverem vazios.
- [ ] T02 — Testar erro quando briefing autoral não for JSON válido.
- [ ] T03 — Testar renderização do prompt para tipo de post válido.
- [ ] T04 — Testar exibição do prompt na área read-only.
- [ ] T05 — Testar persistência automática após preview.

