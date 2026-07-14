# SPEC-020 — Loop principal da entrevista

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Implementa o fluxo completo da entrevista: criar estado, gerar perguntas, coletar respostas, avaliar, atualizar scores e memory pack, reavaliar gateway e montar briefing autoral. O loop encerra por aprovação ou `max_rodadas`.

## Plan
1. Orquestrar componentes sem colocar regra de scoring dentro dos prompts ou da TUI.
2. Processar cada resposta em sequência, atualizando estado de forma previsível.
3. Reavaliar gateway ao final de cada rodada.
4. Gerar briefing autoral mesmo quando o encerramento ocorrer por limite, deixando explícito o status do gateway.

## Tasks
- [ ] T01 — Implementar `executar_entrevista` ou orquestrador equivalente.
- [ ] T02 — Integrar criação de estado, perguntas iniciais, avaliação de resposta, scoring e memory pack.
- [ ] T03 — Integrar avaliação de gateway e geração de perguntas recursivas.
- [ ] T04 — Controlar `rodadas` e encerramento por aprovação ou `max_rodadas`.
- [ ] T05 — Testar fluxo aprovado, fluxo reprovado por limite e propagação de erros controlados.

