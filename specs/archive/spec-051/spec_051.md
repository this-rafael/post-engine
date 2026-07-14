# SPEC-051 — Renderização de templates

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Implementa renderização genérica de templates Markdown. A solução pode ser simples, mas precisa ser previsível, testável e segura para JSON serializado.

## Plan
1. Definir sintaxe de placeholder usada pelos prompts.
2. Renderizar valores sem executar código ou expressões arbitrárias.
3. Preservar caracteres especiais e JSON serializado.
4. Detectar placeholders ausentes quando o template exigir valor.

## Tasks
- [ ] T01 — Implementar função `render_template(template, context)`.
- [ ] T02 — Definir padrão de placeholders aceito.
- [ ] T03 — Evitar interpolação insegura ou execução dinâmica.
- [ ] T04 — Preservar JSON, acentos e quebras de linha.
- [ ] T05 — Testar renderização completa, placeholder ausente e caracteres especiais.

