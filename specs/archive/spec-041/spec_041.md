# SPEC-041 — Tela única da TUI MVP

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Implementa a primeira interface Textual em tela única. A TUI deve operar o fluxo de geração, depurar prompt/execução e expor ações mínimas sem tentar substituir a engine de domínio.

## Plan
1. Criar layout com entrada, prompt renderizado, resultados e ações.
2. Incluir campos e seletores previstos no PRD.
3. Mostrar áreas read-only para stdout, stderr, eventos e JSON extraído.
4. Conectar botões mínimos sem bloquear a interface.

## Tasks
- [ ] T01 — Criar aplicação Textual com layout de tela única.
- [ ] T02 — Adicionar campos para tema, plataforma, objetivo, personalidade, briefing, scores e restrições.
- [ ] T03 — Adicionar seletores de tipo de post, tool, modelo e sandbox.
- [ ] T04 — Adicionar áreas de prompt, stdout, stderr, eventos e JSON parseado.
- [ ] T05 — Adicionar botões Preview, Rodar, Limpar, Segmentar, Avaliar, Exportar MD e Exportar TXT.

