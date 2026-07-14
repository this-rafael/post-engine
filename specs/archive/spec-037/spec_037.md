# SPEC-037 — Exportação TXT

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Implementa exportação manual do conteúdo final para `.txt`, seguindo as mesmas regras da exportação Markdown. O objetivo é oferecer saída local simples no MVP.

## Plan
1. Reutilizar sanitização e criação de diretório da exportação Markdown.
2. Salvar o conteúdo final sem metadados ocultos obrigatórios.
3. Manter exportação como ação explícita do usuário.
4. Retornar caminho salvo para feedback da TUI.

## Tasks
- [ ] T01 — Implementar função `exportar_txt`.
- [ ] T02 — Reutilizar utilitário comum de sanitização de nomes.
- [ ] T03 — Criar `exports/` quando necessário.
- [ ] T04 — Salvar conteúdo com extensão `.txt`.
- [ ] T05 — Testar extensão correta, conteúdo salvo e consistência com exportação `.md`.

