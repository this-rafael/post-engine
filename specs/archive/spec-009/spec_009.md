# SPEC-009 — Identificação de lacunas autorais

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Identifica o que ainda falta para a entrevista atingir qualidade autoral suficiente. A saída deve ajudar a próxima pergunta a buscar material humano sem insistir em categorias já saturadas.

## Plan
1. Comparar score normalizado com os requisitos do gateway equilibrado.
2. Comparar score bruto com oportunidades de gateway desequilibrado.
3. Priorizar lacunas que desbloqueiam aprovação ou melhoram honestidade narrativa.
4. Produzir mensagens legíveis para logs, prompt recursivo e depuração.

## Tasks
- [ ] T01 — Implementar `identificar_lacunas(scores)`.
- [ ] T02 — Gerar lacunas para categorias normalizadas abaixo de 100.
- [ ] T03 — Gerar oportunidades para total bruto, personalidade e categoria dominante do gateway desequilibrado.
- [ ] T04 — Evitar recomendar mais perguntas para categoria já saturada sem motivo.
- [ ] T05 — Testar lacunas equilibradas, oportunidades desequilibradas e combinação das duas.

