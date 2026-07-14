# SPEC-021 — Montagem do briefing autoral

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Transforma o estado da entrevista em `BriefingAutoral`. O briefing deve agrupar material por aspecto autoral e carregar scores, gateway, restrições, memory pack e dados do post sem ser exportado automaticamente como arquivo.

## Plan
1. Receber `EstadoEntrevista` como fonte única.
2. Filtrar respostas por evidências em experiência, opinião, sentimento, aprendizado e personalidade.
3. Construir `GatewayAprovado` apenas quando o gateway estiver aprovado.
4. Preservar restrições e memory pack para o prompt gerador.

## Tasks
- [ ] T01 — Implementar `montar_briefing_autoral(state)`.
- [ ] T02 — Agrupar perguntas e respostas por aspecto autoral com base na avaliação.
- [ ] T03 — Incluir tema, plataforma, objetivo, tipo de post, personalidade, scores e memory pack.
- [ ] T04 — Garantir que briefing não seja salvo automaticamente como artefato separado.
- [ ] T05 — Testar briefing equilibrado, desequilibrado com restrições e estado sem aprovação.

