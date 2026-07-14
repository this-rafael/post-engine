# SPEC-049 — Estrutura de pastas do projeto

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Cria a estrutura base do projeto para separar domínio, TUI, prompts, dados locais, exportações e testes. A organização deve reduzir acoplamento entre engine, interface e infraestrutura.

## Plan
1. Criar diretórios previstos pelo PRD.
2. Separar `src/content_engine`, `src/tui`, `prompts`, `.data`, `exports` e `tests`.
3. Preparar módulos para imports consistentes.
4. Evitar que TUI e infraestrutura concentrem regra de produto.

## Tasks
- [ ] T01 — Criar `src/content_engine` para domínio, prompts e geração.
- [ ] T02 — Criar `src/tui` para aplicação Textual.
- [ ] T03 — Criar `prompts/interview` e `prompts/generator`.
- [ ] T04 — Criar `.data/sessions`, `exports` e `tests`.
- [ ] T05 — Adicionar arquivos de pacote/configuração necessários para imports estáveis.

