# SPEC-057 — Testes do exporter

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Cria testes para exportação `.md` e `.txt`. A cobertura deve garantir que exportação seja explícita, salve conteúdo correto e use nomes seguros.

## Plan
1. Testar criação automática do diretório `exports/`.
2. Testar sanitização do nome do arquivo.
3. Testar conteúdo salvo em Markdown e TXT.
4. Testar extensão e retorno de caminho.

## Tasks
- [ ] T01 — Testar exportação Markdown com conteúdo final.
- [ ] T02 — Testar exportação TXT com conteúdo final.
- [ ] T03 — Testar sanitização de nomes com espaços, acentos e caracteres especiais.
- [ ] T04 — Testar criação do diretório de exportação.
- [ ] T05 — Testar que exportação não acontece automaticamente após geração.

