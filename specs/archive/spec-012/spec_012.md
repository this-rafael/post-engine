# SPEC-012 — Atualização do memory pack

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Atualiza o `MemoryPack` com sinais autorais extraídos da resposta. O objetivo é preservar contexto relevante, reduzir repetição nas próximas rodadas e alimentar geração sem reenviar todo o histórico bruto.

## Plan
1. Receber tema, pergunta, resposta, avaliação e memory pack atual.
2. Extrair e mesclar fatos, exemplos, opiniões, sentimentos, aprendizados, personalidade, frases e tensões.
3. Remover duplicações sem apagar informação útil.
4. Impedir que opinião vire fato vivido ou que o sistema invente experiência.

## Tasks
- [ ] T01 — Implementar função de atualização de `MemoryPack`.
- [ ] T02 — Definir estratégia de merge por campo com deduplicação simples e previsível.
- [ ] T03 — Preservar frases naturais do usuário sem reescrita excessiva.
- [ ] T04 — Registrar pontos ainda fracos para orientar perguntas recursivas.
- [ ] T05 — Testar merge incremental, deduplicação e separação entre fatos, opiniões e sentimentos.

