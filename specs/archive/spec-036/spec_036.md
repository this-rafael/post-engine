# SPEC-036 — Exportação Markdown

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Implementa exportação manual do conteúdo final para `.md`. A exportação é uma ação explícita do usuário e não substitui persistência automática de sessão.

## Plan
1. Receber conteúdo final e metadados mínimos para nome do arquivo.
2. Sanitizar nome do arquivo de forma previsível.
3. Criar diretório `exports/` quando necessário.
4. Salvar somente quando o usuário acionar exportação.

## Tasks
- [ ] T01 — Implementar função `exportar_markdown`.
- [ ] T02 — Sanitizar tema, plataforma ou tipo de post para nome de arquivo seguro.
- [ ] T03 — Criar `exports/` se o diretório não existir.
- [ ] T04 — Salvar conteúdo com extensão `.md` sem disparo automático após geração.
- [ ] T05 — Testar conteúdo salvo, extensão correta, diretório criado e nome sanitizado.

