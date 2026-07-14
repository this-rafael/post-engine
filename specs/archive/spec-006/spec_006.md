# SPEC-006 — Classificação do tipo de autoria

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Classifica o tipo de autoria quando o gateway desequilibrado é aprovado. A classificação orienta a geração para o eixo mais fiel ao material coletado, evitando que o texto assuma uma base narrativa inexistente.

## Plan
1. Retornar `hibrida` quando experiência, opinião e aprendizado forem fortes.
2. Mapear experiência, opinião, sentimento e aprendizado para tipos de autoria.
3. Escolher a categoria principal dominante pelo score bruto.
4. Tratar empates de forma previsível e documentada.

## Tasks
- [ ] T01 — Implementar `classificar_tipo_autoria(score_bruto)`.
- [ ] T02 — Mapear `experiencia` para `experiencial`, `opiniao` para `opinativa`, `sentimento` para `emocional` e `aprendizado` para `reflexiva`.
- [ ] T03 — Retornar `hibrida` quando experiência, opinião e aprendizado forem `>= 100`.
- [ ] T04 — Definir regra determinística para empate entre categorias dominantes.
- [ ] T05 — Testar cada tipo possível, incluindo caso híbrido.

