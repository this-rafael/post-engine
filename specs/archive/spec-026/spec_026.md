# SPEC-026 — Prompt gerador base

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Implementa o template base do gerador de conteúdo autoral. O prompt transforma briefing em conteúdo final preservando voz, limites narrativos, scores, restrições e contrato JSON.

## Plan
1. Criar template com entrada, persona ativa, regras do formato, scores, restrições e briefing.
2. Incluir regras globais contra invenção de experiência, emoção, aprendizado ou autoridade.
3. Exigir JSON válido com `conteudo`, `metadados` e `alertas`.
4. Garantir que o template não contenha blocos condicionais por formato.

## Tasks
- [ ] T01 — Criar `prompts/generator/base.md`.
- [ ] T02 — Incluir placeholders para tema, plataforma, objetivo, tipo, personalidade, gateway e autoria.
- [ ] T03 — Incluir regras globais de honestidade narrativa do PRD.
- [ ] T04 — Definir contrato JSON de saída com metadados e alertas.
- [ ] T05 — Testar renderização com restrições baixas e briefing completo.

